// 町割(敷地割)の正典 — docs/Sashizu/parcels.json
//
// 【なぜここに置くか】区画のポリゴンは 2026-08-22 まで各ビルダーの C# ソースに
//   `static readonly Vector2[] OKABE = {...}` の形で直書きされていた。CLAUDE.md 絶対規則3
//   「数値は設計値ファイルにのみ置き、文章にも図にも写さない」に従い、**町割の正典はこの json** とする。
//   ビルダーは `EdoParcels.Get("okabe")` で引く。指図(python)も同じ json を読める。
//
// 【移行の途中である】全ビルダーを一度に書き換えるのは危険なので、配列を残したまま
//   `Edo/敷地割/ビルダーと突き合わせる` でドリフトを検出する。突き合わせが 0 件なら
//   json と実装は一致している。ビルダーを1本ずつ `EdoParcels.Get` へ寄せていく。
//
// 【編集】Scene ビューの `Edo/敷地割/編集モード` (EdoParcelTool) と
//   `Edo/敷地割/一覧を開く` (EdoParcelWindow)。手で json を直してもよい。
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEngine;
using UnityEditor;

public static class EdoParcels
{
    public const string RelPath = "docs/Sashizu/parcels.json";
    public const float TSUBO = 3.305785f;   // 1坪 = 400/121 m²
    public const float KEN = 1.818f;        // 江戸間 1間

    /// <summary>区画の色。EdoSketch のパレットと揃える(下書きの色が意味を持つため)。</summary>
    public static readonly Color[] Palette =
    {
        new Color(1.00f, 0.25f, 0.20f), // 0 赤   武家
        new Color(1.00f, 0.80f, 0.10f), // 1 黄   武家
        new Color(0.20f, 0.85f, 1.00f), // 2 水   武家
        new Color(0.30f, 1.00f, 0.40f), // 3 緑   寺社
        new Color(1.00f, 0.45f, 0.90f), // 4 桃   町屋
        new Color(1.00f, 1.00f, 1.00f), // 5 白   その他
        new Color(1.00f, 0.60f, 0.20f), // 6 橙   公有地・預地
        new Color(0.60f, 0.60f, 0.70f), // 7 灰   道・水
    };

    /// <summary>区画の種別。色ではなくこれで分類する(色は見やすさのための物)。</summary>
    public static readonly string[] Categories =
    { "buke", "machiya", "jisha", "kouyuu", "michi", "other" };
    public static string CategoryLabel(string c)
    {
        switch (c)
        {
            case "buke": return "武家屋敷";
            case "machiya": return "町屋・町人地";
            case "jisha": return "寺社";
            case "kouyuu": return "公有地・預地・会所";
            case "michi": return "道・水・掛";
            default: return "その他";
        }
    }

    [Serializable]
    public class Parcel
    {
        public string id = "";          // 一意。ビルダーから引くときの鍵
        public string label = "";       // 表示名(「岡部筑前守 上屋敷」)
        public string category = "other";
        public int color = 5;
        public string note = "";        // 典拠・確度など短い覚書
        public string source = "";      // 取り込み元(TypeName.FIELD)。手で引いた物は空
        public List<Vector2> pts = new List<Vector2>();

        public Vector2[] Poly { get { return pts.ToArray(); } }

        public float SignedArea
        {
            get
            {
                float a = 0f;
                for (int i = 0; i < pts.Count; i++)
                {
                    var p = pts[i]; var q = pts[(i + 1) % pts.Count];
                    a += p.x * q.y - q.x * p.y;
                }
                return 0.5f * a;
            }
        }
        public float AreaM2 { get { return Mathf.Abs(SignedArea); } }
        public float Tsubo { get { return AreaM2 / TSUBO; } }
        public float Perimeter
        {
            get
            {
                float s = 0f;
                for (int i = 0; i < pts.Count; i++) s += Vector2.Distance(pts[i], pts[(i + 1) % pts.Count]);
                return s;
            }
        }
        public Vector2 Centroid
        {
            get
            {
                if (pts.Count == 0) return Vector2.zero;
                float a = SignedArea;
                if (Mathf.Abs(a) < 1e-4f)
                {
                    var m = Vector2.zero;
                    foreach (var p in pts) m += p;
                    return m / pts.Count;
                }
                float cx = 0f, cy = 0f;
                for (int i = 0; i < pts.Count; i++)
                {
                    var p = pts[i]; var q = pts[(i + 1) % pts.Count];
                    float cr = p.x * q.y - q.x * p.y;
                    cx += (p.x + q.x) * cr; cy += (p.y + q.y) * cr;
                }
                return new Vector2(cx / (6f * a), cy / (6f * a));
            }
        }
        public Color Col { get { return Palette[Mathf.Clamp(color, 0, Palette.Length - 1)]; } }
        public Parcel Clone()
        {
            return new Parcel { id = id, label = label, category = category, color = color,
                                note = note, source = source, pts = new List<Vector2>(pts) };
        }
    }

    // ---- 読み書き ---------------------------------------------------------

    static List<Parcel> _all;
    static bool _dirty;

    /// <summary>データが差し替わる/書き換わるたびに増える。ツール側のキャッシュ
    /// (地形に載せた折れ線・共有点の表)はこれを見て捨てる。Load で Parcel の実体が
    /// 入れ替わるので、参照をキーにしたキャッシュは黙って外れる — 実際に外れた。</summary>
    public static int Version { get; private set; }

    public static string FullPath
    {
        get { return Path.Combine(Directory.GetParent(Application.dataPath).FullName, RelPath); }
    }

    public static List<Parcel> All
    {
        get { if (_all == null) Load(); return _all; }
    }

    public static void Load()
    {
        _all = new List<Parcel>();
        _dirty = false;
        _polyCache.Clear();
        Version++;
        try
        {
            if (!File.Exists(FullPath)) return;
            var root = EdoMiniJson.Parse(File.ReadAllText(FullPath)) as Dictionary<string, object>;
            if (root == null) return;
            var arr = root.ContainsKey("parcels") ? root["parcels"] as List<object> : null;
            if (arr == null) return;
            foreach (var o in arr)
            {
                var d = o as Dictionary<string, object>;
                if (d == null) continue;
                var p = new Parcel
                {
                    id = Str(d, "id"),
                    label = Str(d, "label"),
                    category = string.IsNullOrEmpty(Str(d, "category")) ? "other" : Str(d, "category"),
                    color = (int)Num(d, "color", 5),
                    note = Str(d, "note"),
                    source = Str(d, "source"),
                };
                var pl = d.ContainsKey("pts") ? d["pts"] as List<object> : null;
                if (pl != null)
                    foreach (var q in pl)
                    {
                        var xy = q as List<object>;
                        if (xy == null || xy.Count < 2) continue;
                        p.pts.Add(new Vector2((float)ToD(xy[0]), (float)ToD(xy[1])));
                    }
                if (!string.IsNullOrEmpty(p.id)) _all.Add(p);
            }
        }
        catch (Exception ex)
        {
            Debug.LogError("[EdoParcels] 読込失敗 " + RelPath + ": " + ex.Message);
            _all = new List<Parcel>();
        }
    }

    static string Str(Dictionary<string, object> d, string k)
    { object v; return d.TryGetValue(k, out v) && v != null ? v.ToString() : ""; }
    static double Num(Dictionary<string, object> d, string k, double dflt)
    { object v; return d.TryGetValue(k, out v) && v is double ? (double)v : dflt; }
    static double ToD(object o) { return o is double ? (double)o : 0.0; }

    public static void MarkDirty() { _dirty = true; _polyCache.Clear(); Version++; }
    public static bool IsDirty { get { return _dirty; } }

    public static void Save()
    {
        try
        {
            var ic = CultureInfo.InvariantCulture;
            var sb = new StringBuilder();
            // ⚠ 素の JSON として妥当に保つ。指図の生成器(python)がこの同じファイルを読む。
            //   文字列の中に生の改行を入れると json.load が落ちる。覚書は配列で持つ。
            sb.AppendLine("{");
            sb.AppendLine("  \"_\": [");
            sb.AppendLine("    \"町割の正典。Scene ビューの Edo/敷地割/編集モード (Cmd+Shift+K) で編集する。\",");
            sb.AppendLine("    \"pts は世界座標 [x, z] の並び。閉多角形なので最後と最初は重ねない。単位は m。\",");
            sb.AppendLine("    \"1坪 = 3.305785 m² / 江戸間 1間 = 1.818 m。\",");
            sb.AppendLine("    \"source はビルダーからの取り込み元。Edo/敷地割/ビルダーと突き合わせる で差分を見る。\"");
            sb.AppendLine("  ],");
            sb.AppendLine("  \"parcels\": [");
            var list = All.OrderBy(p => p.category).ThenBy(p => p.id, StringComparer.Ordinal).ToList();
            for (int i = 0; i < list.Count; i++)
            {
                var p = list[i];
                sb.AppendLine("    {");
                sb.AppendFormat("      \"id\": {0}, \"label\": {1},\n", Esc(p.id), Esc(p.label));
                sb.AppendFormat("      \"category\": {0}, \"color\": {1},\n", Esc(p.category), p.color);
                sb.AppendFormat("      \"source\": {0},\n", Esc(p.source));
                sb.AppendFormat("      \"note\": {0},\n", Esc(p.note));
                sb.Append("      \"pts\": [");
                for (int j = 0; j < p.pts.Count; j++)
                {
                    if (j % 4 == 0) sb.Append("\n        ");
                    sb.AppendFormat(ic, "[{0}, {1}]", F(p.pts[j].x), F(p.pts[j].y));
                    if (j < p.pts.Count - 1) sb.Append(", ");
                }
                sb.AppendLine("\n      ]");
                sb.Append(i < list.Count - 1 ? "    },\n" : "    }\n");
            }
            sb.AppendLine("  ]");
            sb.AppendLine("}");
            Directory.CreateDirectory(Path.GetDirectoryName(FullPath));
            File.WriteAllText(FullPath, sb.ToString());
            _dirty = false;
        }
        catch (Exception ex)
        {
            Debug.LogError("[EdoParcels] 保存失敗: " + ex.Message);
        }
    }

    static string F(float v)
    {
        // 1mm で丸める。区画の角に 1mm 以上の精度は無い(下書き/古地図由来)
        return ((double)Mathf.Round(v * 1000f) / 1000.0).ToString("0.###", CultureInfo.InvariantCulture);
    }
    static string Esc(string s)
    {
        if (s == null) s = "";
        return "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", " ") + "\"";
    }

    // ---- 引く ------------------------------------------------------------

    public static Parcel Find(string id)
    {
        foreach (var p in All) if (p.id == id) return p;
        return null;
    }

    // ⚠ Get はビルダーの内側ループ(地形セルごとの PIP 判定など)から呼ばれる。
    //   毎回 ToArray すると造成ステージが数万回の確保をする。ここでキャッシュする。
    static readonly Dictionary<string, Vector2[]> _polyCache = new Dictionary<string, Vector2[]>();

    /// <summary>区画のポリゴンを引く。無ければ **例外を投げずに null** を返し、警告を出す
    /// (LoadAssetAtPath と同じ作法。直書きの literal を増やさないための入口)。</summary>
    public static Vector2[] Get(string id)
    {
        Vector2[] cached;
        if (_polyCache.TryGetValue(id, out cached)) return cached;
        var p = Find(id);
        if (p == null || p.pts.Count < 3)
        {
            Debug.LogWarning("[EdoParcels] 区画 '" + id + "' が " + RelPath + " に無い。");
            return null;
        }
        cached = p.Poly;
        _polyCache[id] = cached;
        return cached;
    }

    /// <summary>json に無ければ fallback を返す。移行中のビルダー向け。</summary>
    public static Vector2[] GetOr(string id, Vector2[] fallback)
    {
        var p = Find(id);
        return (p != null && p.pts.Count >= 3) ? p.Poly : fallback;
    }

    public static Parcel Add(string id, string label, string category, int color, IEnumerable<Vector2> pts)
    {
        string uid = id; int n = 2;
        while (Find(uid) != null) uid = id + "_" + (n++);
        var p = new Parcel { id = uid, label = label, category = category, color = color, pts = new List<Vector2>(pts) };
        All.Add(p);
        MarkDirty();
        return p;
    }

    public static void Remove(Parcel p) { All.Remove(p); MarkDirty(); }

    // ---- ビルダーから取り込む(反射) --------------------------------------

    public class Harvested
    {
        public string source;      // "EdoSannoKitaBuilder.OKABE"
        public string label;       // 構造体に label があればそれ
        public Vector2[] pts;
    }

    /// <summary>エディタアセンブリの静的フィールドを走査して区画らしいポリゴンを集める。
    /// 拾うのは (a) `Vector2[]` の静的フィールド (b) 配列/List の要素が `Vector2[]` を持つ物
    /// (EdoNishiTameikeBuilder.Estates / EdoSannoJuboBuilder の Parcel[] など)。
    /// 3点未満と、極端に細長い物(道の軸線)は落とす。</summary>
    public static List<Harvested> HarvestFromBuilders()
    {
        var outp = new List<Harvested>();
        var asm = typeof(EdoParcels).Assembly;
        const BindingFlags BF = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;

        foreach (var t in asm.GetTypes())
        {
            if (!t.Name.StartsWith("Edo")) continue;
            if (t == typeof(EdoParcels) || t == typeof(EdoParcelTool)) continue;
            FieldInfo[] fields;
            try { fields = t.GetFields(BF); } catch { continue; }

            foreach (var f in fields)
            {
                object val;
                try { val = f.GetValue(null); } catch { continue; }
                if (val == null) continue;

                if (f.FieldType == typeof(Vector2[]))
                {
                    var v = (Vector2[])val;
                    if (!IsRoadName(f.Name) && Plausible(v))
                        outp.Add(new Harvested { source = t.Name + "." + f.Name, label = "", pts = v });
                    continue;
                }

                // 要素が poly を持つ配列/List
                var en = val as IEnumerable;
                if (en == null || val is string) continue;
                int idx = 0;
                foreach (var item in en)
                {
                    if (item == null) { idx++; continue; }
                    var it = item.GetType();
                    var pf = it.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                               .FirstOrDefault(x => x.FieldType == typeof(Vector2[]));
                    if (pf == null) { idx++; continue; }
                    var v = pf.GetValue(item) as Vector2[];
                    if (v != null && Plausible(v))
                    {
                        var lf = it.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                                   .FirstOrDefault(x => x.FieldType == typeof(string) &&
                                        (x.Name == "label" || x.Name == "name" || x.Name == "group"));
                        string lab = lf != null ? (lf.GetValue(item) as string ?? "") : "";
                        outp.Add(new Harvested { source = t.Name + "." + f.Name + "[" + idx + "]", label = lab, pts = v });
                    }
                    idx++;
                }
            }
        }
        return outp.OrderBy(x => x.source, StringComparer.Ordinal).ToList();
    }

    /// <summary>道の軸線・参道コリドー等、名前で区画でないと分かる物。</summary>
    static bool IsRoadName(string n)
    {
        string u = n.ToUpperInvariant();
        return u.Contains("ROAD") || u.Contains("AXIS") || u.Contains("SANDO")
            || u.EndsWith("_ST") || u == "BASE_ST";
    }

    static bool Plausible(Vector2[] v)
    {
        if (v == null || v.Length < 3) return false;
        float minx = float.MaxValue, maxx = float.MinValue, minz = float.MaxValue, maxz = float.MinValue;
        foreach (var p in v)
        {
            if (float.IsNaN(p.x) || float.IsNaN(p.y)) return false;
            minx = Mathf.Min(minx, p.x); maxx = Mathf.Max(maxx, p.x);
            minz = Mathf.Min(minz, p.y); maxz = Mathf.Max(maxz, p.y);
        }
        float w = maxx - minx, h = maxz - minz;
        if (w < 4f || h < 4f) return false;               // 軸線・帯は区画ではない
        var tmp = new Parcel { pts = new List<Vector2>(v) };
        if (tmp.AreaM2 < 150f) return false;                // 45坪未満は区画として扱わない
        // 細長すぎる物は道・帯であって区画ではない(等周比で見る)
        float peri = tmp.Perimeter;
        if (peri > 1f && tmp.AreaM2 / (peri * peri) < 0.020f) return false;
        return true;
    }

    /// <summary>取り込み済みの区画と、いまのビルダーの配列を突き合わせる。</summary>
    public static string DiffAgainstBuilders(float tol = 0.01f)
    {
        var h = HarvestFromBuilders();
        var bySource = new Dictionary<string, Harvested>();
        foreach (var x in h) bySource[x.source] = x;

        var sb = new StringBuilder();
        int same = 0, diff = 0, gone = 0, fresh = 0;

        foreach (var p in All)
        {
            if (string.IsNullOrEmpty(p.source)) continue;
            Harvested x;
            if (!bySource.TryGetValue(p.source, out x))
            { sb.AppendLine("  ✗ ビルダー側に無い: " + p.id + " (" + p.source + ")"); gone++; continue; }
            if (x.pts.Length != p.pts.Count)
            { sb.AppendLine("  ≠ 頂点数 " + p.id + ": json " + p.pts.Count + " / ビルダー " + x.pts.Length); diff++; continue; }
            float worst = 0f;
            for (int i = 0; i < x.pts.Length; i++) worst = Mathf.Max(worst, Vector2.Distance(x.pts[i], p.pts[i]));
            if (worst > tol) { sb.AppendLine("  ≠ 座標 " + p.id + ": 最大 " + worst.ToString("0.###") + " m"); diff++; }
            else same++;
        }
        var known = new HashSet<string>(All.Select(p => p.source).Where(s => !string.IsNullOrEmpty(s)));
        foreach (var x in h) if (!known.Contains(x.source)) { sb.AppendLine("  + 未取り込み: " + x.source); fresh++; }

        return string.Format("一致 {0} / 相違 {1} / 消えた {2} / 未取り込み {3}\n{4}",
                             same, diff, gone, fresh, sb.Length == 0 ? "  (差分なし)" : sb.ToString());
    }

    // ---- メニュー --------------------------------------------------------

    [MenuItem("Edo/敷地割/ビルダーと突き合わせる", false, 40)]
    public static void MenuDiff() { Debug.Log("[敷地割] 突き合わせ\n" + DiffAgainstBuilders()); }

    [MenuItem("Edo/敷地割/再読込(json を読み直す)", false, 41)]
    public static void MenuReload() { Load(); SceneView.RepaintAll(); Debug.Log("[敷地割] " + All.Count + " 区画を読み込んだ: " + RelPath); }

    [MenuItem("Edo/敷地割/保存", false, 42)]
    public static void MenuSave() { Save(); AssetDatabase.Refresh(); Debug.Log("[敷地割] 保存した: " + RelPath + " (" + All.Count + " 区画)"); }
}
