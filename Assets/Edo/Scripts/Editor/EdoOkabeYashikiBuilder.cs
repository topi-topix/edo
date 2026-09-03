// 岡部筑前守長寛(和泉岸和田藩5万3千石・譜代・帝鑑間)上屋敷 ビルダー — 全面起こし直し(2026-09-03)
//
// 【なぜ起こし直したか】旧 v3(2026-08-14)は 2026-08-23 に**指図ごと失効**した。
//   区画が 11頂点 → 13頂点に引き直され(南辺が北へ 11〜27m)、指図は回転間グリッド
//   (grid.shukaku)へ移り、面は 6枚 → 2枚、run は 21本 → 22本で**名前の一致は 0**、
//   郭の土留めは 0本になった。旧コードは段・run・隅・棟の座標を C# の表に直書きしており、
//   新区画に対して走らせると全て誤った位置に造成・築造する。番号の付け替えでは直らないので、
//   表ごと捨てて**指図を実行時に読む器**へ作り替えた。
//
// 【正典は指図】`docs/Sashizu/okabe_sashizu.json` を**実行時に読む**。設計値を C# に写さない
//   (写した瞬間に指図とビルダーが別々に動き出す — CLAUDE.md 規則4)。
//   区画は `EdoParcels.Get("okabe")`(規則11)。アセットのパスは `EdoAssets`(規則12)。
//
// 【指図が持たない算出物は生成器が焼く】造成後の地盤・法肩の竹垣・隅の留め継ぎ・基壇の露出は、
//   指図の json には**入っておらず**、生成器 `Tools/Sashizu/build_okabe_sashizu.py` が
//   毎回算出している(`graded_y` 606行 / `auto_rails` / `corners_table` / `run_base`)。
//   これを C# へ移植すると正典が2つになって黙ってドリフトするので、
//   **2026-09-03 ユーザー裁定1=A** で生成器に焼き出させ、ここは**読むだけ**にした
//   → `docs/Sashizu/okabe_impl.json`(スキーマは下の <see cref="Impl"/> の注)。
//   ⭐ 同じ作法の先例が松江松平の植栽(`matsudaira_dewa_planting_out.json`)にある。
//
// 【この版で建つもの】2026-09-03 ユーザー裁定3=B。
//   ⭕ S1 造成(区画内の全セル)/ S2 外周のうち **練塀20本・石垣基壇・木柵・隅の留め継ぎ**
//   ⛔ 表門(長屋門)・表長屋2本・通用口(棟門)は**次巡** — 部材が未選定で、
//      指図の `gate.asset` が「要選定」のまま、表長屋の棟高も在庫と食い違っている。
//      ⚠ この版で走らせると辺12 の 96.4m が素通しのまま残る(`ClosureQA` が数字で出す)。
//
// ⚠ 地形の編集は Undo の外。走らせる前に Stage0_Backup でハイトマップを退避すること。
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class EdoOkabeYashikiBuilder
{
    public const string GN = "Edo_Yashiki_OkabeChikuzen";
    public const string SashizuRel = "docs/Sashizu/okabe_sashizu.json";
    /// <summary>生成器が焼く「実装が読む算出物」。⛔ 手で書かない・指図の代わりにしない。</summary>
    public const string ImplRel = "docs/Sashizu/okabe_impl.json";
    public const string ParcelId = "okabe";

    // =====================================================================
    // 検図関門(CLAUDE.md 規則18)
    // =====================================================================
    /// <summary>**赤の指図でも流す**明示の逃がし。⛔ 既定は止める側で、開けるのは裁定があるときだけ。
    ///
    /// 【2026-09-03 ユーザー裁定9=案B】岡部は検図・考証・庭方の三役とも `fail`(2026-09-03)だが、
    /// 「検分の輪を回し続ける」のではなく「実装の輪へ進む」と裁定された。指図側の直しは並行で走る。
    /// ⛔ この定数を無断で立てない。⛔ ユーザーへ見せる前には関門を通し直すこと。</summary>
    public const bool AllowRedReviewGate = true;
    const string RedGateReason = "2026-09-03 ユーザー裁定9=案B(赤のまま実装の輪へ進む)";

    static string ReviewGate()
    {
        var g = EdoSashizuExport.ReviewGate("okabe");
        if (g == null) return null;
        if (!AllowRedReviewGate) return g;
        Debug.LogWarning("[Okabe] 検図関門は赤だが明示の逃がしで通した — " + RedGateReason + "\n" + g);
        return null;
    }

    // =====================================================================
    // 指図と算出物の読み込み
    // =====================================================================
    static string ProjRoot { get { return Directory.GetParent(Application.dataPath).FullName; } }
    static Dictionary<string, object> _d, _impl;

    /// <summary>読み直す。指図か算出物を差し替えたら必ず呼ぶ(Unity は静的を抱え続ける)。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/指図を読み直す")]
    public static void Reload() { _d = null; _impl = null; _runs = null; _frame = null; _graded = null; }

    static Dictionary<string, object> D
    {
        get
        {
            if (_d == null)
            {
                string p = Path.Combine(ProjRoot, SashizuRel);
                if (!File.Exists(p)) throw new Exception("指図が無い: " + p);
                _d = EdoMiniJson.Parse(File.ReadAllText(p)) as Dictionary<string, object>;
                if (_d == null) throw new Exception("指図が読めない(JSON): " + p);
            }
            return _d;
        }
    }

    /// <summary>生成器が焼いた算出物。無ければ**焼き方を添えて**例外にする(黙って代用しない)。
    ///
    /// 【スキーマ】`docs/Sashizu/okabe_impl.json`
    /// <code>
    /// {
    ///   "of": "okabe_sashizu.json",
    ///   "src": { "sha256": "&lt;指図 json のバイト列の SHA-256(小文字hex)&gt;", "bytes": 348142 },
    ///   "at": "2026-09-03T21:00:00+09:00",
    ///   "generator": "Tools/Sashizu/build_okabe_sashizu.py --export-impl",
    ///   "checks": { "gradeTol": 0.30, "baseMin": 0.20 },
    ///   "graded": {            // 造成後の地盤 graded_y。**世界座標**の格子。区画の外は null
    ///     "x0": -720.0, "z0": 930.0, "step": 1.0, "nx": 321, "nz": 181,
    ///     "h": [[null, 12.34, ...], ...]        // h[iz][ix]
    ///   },
    ///   "rails": [             // 法肩の竹垣(auto_rails の出力)
    ///     { "name": "R_Sh_u-12_v66", "terrace": "Shumen",
    ///       "world": [[x,z], ...],              // 世界座標の折れ線(実装はこれを使う)
    ///       "len": 23.4, "drop": 2.1, "h": 0.90 }
    ///   ],
    ///   "corners": [           // 隅の留め継ぎ(corners_table の出力)
    ///     { "id": "P4", "vertex": 4, "world": [x,z], "deg": 41.24,
    ///       "part": "Dobei",                    // 部材の種別。留め継ぎでない隅は null
    ///       "runIn": "W_Hei_S2", "runOut": "W_Hei_C",
    ///       "seatIn": 13.08, "seatOut": 10.86, "seat": 13.08,
    ///       "yawFrom": "in", "osame": "..." }
    ///   ],
    ///   "base": [              // 基壇石垣(run_base の出力)
    ///     { "run": "S_Hei4", "s": 0.75, "cap": 3.00, "lo": 0.21, "hi": 2.83,
    ///       "segs": [[88.2, 139.856]],          // 基壇を**置く**区間(露出 ≧ baseMin)
    ///       "thin": [] }                        // 置かない区間(記録用)
    ///   ]
    /// }
    /// </code>
    /// ⚠ `graded` の格子は世界座標で持つ(回転間グリッドではない) — 地形のハイトマップが
    ///   世界軸の格子なので、回転格子だと二度の補間が入る。step は 1.0m を既定とする
    ///   (地形は 2m 格子なので、双一次の誤差は折れ目でも 0.13m ＝ 許容 0.30m の 43%)。
    /// ⚠ `src.sha256` が実際の指図と食い違ったら**古い焼き**なので走らせない。</summary>
    static Dictionary<string, object> IMPL
    {
        get
        {
            if (_impl == null)
            {
                string p = Path.Combine(ProjRoot, ImplRel);
                if (!File.Exists(p))
                    throw new Exception("⛔ 算出物が無い: " + p
                        + "\n   生成器が焼いていない。`python3 Tools/Sashizu/build_okabe_sashizu.py --export-impl`"
                        + "\n   (造成後の地盤・法肩の竹垣・隅の留め継ぎ・基壇の露出は指図の json に入っていない。"
                        + "ここへ移植すると正典が2つになるので焼き出しで受ける — 2026-09-03 裁定1=A)");
                _impl = EdoMiniJson.Parse(File.ReadAllText(p)) as Dictionary<string, object>;
                if (_impl == null) throw new Exception("算出物が読めない(JSON): " + p);
                VerifyImplFingerprint();
            }
            return _impl;
        }
    }

    /// <summary>算出物が**いまの指図**から焼かれた物か。⚠ 古い焼きで建てると、指図では直った
    /// はずの物が黙って復活する(2026-09-01 に松江松平の Stage7 で起きた型)。</summary>
    static void VerifyImplFingerprint()
    {
        var src = O(_impl.ContainsKey("src") ? _impl["src"] : null);
        if (src == null || !src.ContainsKey("sha256"))
        { Debug.LogWarning("[Okabe] 算出物に src.sha256 が無い — 指図との対応を機械で確かめられない"); return; }
        string want = Convert.ToString(src["sha256"]).ToLowerInvariant();
        string got = Sha256Hex(Path.Combine(ProjRoot, SashizuRel));
        if (want != got)
            throw new Exception("⛔ 算出物が**いまの指図から焼かれていない**"
                + "\n   指図 " + got.Substring(0, 16) + "… / 算出物が名乗る元 " + want.Substring(0, Math.Min(16, want.Length)) + "…"
                + "\n   `python3 Tools/Sashizu/build_okabe_sashizu.py --export-impl` を回し直すこと");
    }
    static string Sha256Hex(string path)
    {
        using (var sha = System.Security.Cryptography.SHA256.Create())
        using (var fs = File.OpenRead(path))
        {
            var h = sha.ComputeHash(fs);
            var sb = new System.Text.StringBuilder(h.Length * 2);
            for (int i = 0; i < h.Length; i++) sb.Append(h[i].ToString("x2"));
            return sb.ToString();
        }
    }

    // ---- json の小物 ----
    static Dictionary<string, object> O(object o) { return o as Dictionary<string, object>; }
    static List<object> A(object o) { return o as List<object>; }
    static float F(object o) { return o == null ? 0f : Convert.ToSingle(o); }
    static string S(object o) { return o == null ? null : Convert.ToString(o); }
    static bool Has(Dictionary<string, object> d, string k) { return d != null && d.ContainsKey(k) && d[k] != null; }
    static object Get(Dictionary<string, object> d, string k) { object v; return d != null && d.TryGetValue(k, out v) ? v : null; }

    /// <summary>指図の `const` の値。⛔ **無ければ例外**(発明しない・既定値で埋めない)。</summary>
    public static float C(string key)
    {
        var c = O(D["const"]);
        if (!Has(c, key)) throw new Exception("指図 const." + key + " が無い(実装が読む欄)");
        return F(c[key]);
    }

    // =====================================================================
    // 区画と辺(座標は parcels.json が正典 — 規則11)
    // =====================================================================
    public static Vector2[] Poly { get { return EdoParcels.Get(ParcelId); } }

    public static float EdgeLen(int e)
    {
        var P = Poly; int n = P.Length;
        return (P[(e + 1) % n] - P[e % n]).magnitude;
    }
    /// <summary>辺 e の始点から走り s[m] の世界座標。</summary>
    public static Vector2 EdgePt(int e, float s)
    {
        var P = Poly; int n = P.Length;
        Vector2 a = P[e % n], b = P[(e + 1) % n];
        Vector2 d = b - a; float L = d.magnitude;
        return a + d / Mathf.Max(1e-5f, L) * s;
    }
    /// <summary>辺 e の外向き単位法線。**符号付き面積から決める**ので凹みのある区画でも全辺で一貫する。
    /// ⛔ 重心で向きを決めない(松江松平で辺1 だけ反転し、塀が隣家へ 0.95m 出た — EDO-0058)。</summary>
    public static Vector2 OutNormal(int e) { return -EdoGeom.InwardNormal(Poly, e % Poly.Length); }

    // =====================================================================
    // 回転間グリッド(u+ = 北 / v+ = 西、単位は間。原点 = 表門の芯)
    // =====================================================================
    public class Frame
    {
        public float x0, z0, ux, uz, vx, vz, ken;
        public Vector2 W(float u, float v)
        { return new Vector2(x0 + (ux * u + vx * v) * ken, z0 + (uz * u + vz * v) * ken); }
        public Vector2 L(Vector2 p)
        {
            float dx = p.x - x0, dz = p.y - z0;
            return new Vector2((dx * ux + dz * uz) / ken, (dx * vx + dz * vz) / ken);
        }
    }
    static Frame _frame;
    public static Frame Grid
    {
        get
        {
            if (_frame == null)
            {
                var g = O(O(D["grid"])["shukaku"]);
                _frame = new Frame
                {
                    x0 = F(g["x0"]), z0 = F(g["z0"]),
                    ux = F(g["ux"]), uz = F(g["uz"]), vx = F(g["vx"]), vz = F(g["vz"]),
                    ken = C("ken")
                };
            }
            return _frame;
        }
    }

    // =====================================================================
    // 外周の run(指図 `runs`)
    // =====================================================================
    /// <summary>外周の囲いの一区間。**辺番号 + 辺沿いの走り s[m]** で持ち、天端は run ごとに一直線。
    /// ⚠ `seat` は `seat0`/`seat1` を持つ run では**中央の短縮記法**にすぎない。据えには使わない
    ///   (2026-08-31 四巡目: 傾いた天端の run で最大 5.09m 食い違っていた)。</summary>
    public struct Run
    {
        public string name, kind, baseKind;
        public int edge;
        public float s0, s1, seat0, seat1, s;
        public bool Dobei { get { return kind == "Dobei"; } }
        public bool Nagaya { get { return kind == "Nagaya"; } }
        public bool Ishigaki { get { return baseKind == "Ishigaki"; } }
        /// <summary>走り s における天端。seat0 → seat1 の一直線。</summary>
        public float SeatAt(float sv)
        {
            if (s1 <= s0) return seat0;
            float t = Mathf.Clamp01((sv - s0) / (s1 - s0));
            return Mathf.Lerp(seat0, seat1, t);
        }
    }
    static Run[] _runs;
    public static Run[] Runs
    {
        get
        {
            if (_runs == null)
            {
                var list = new List<Run>();
                foreach (var o in A(D["runs"]))
                {
                    var r = O(o);
                    float sa = Has(r, "seat0") ? F(r["seat0"]) : F(r["seat"]);
                    float sb = Has(r, "seat1") ? F(r["seat1"]) : F(r["seat"]);
                    list.Add(new Run
                    {
                        name = S(r["name"]), kind = S(r["kind"]),
                        baseKind = Has(r, "base") ? S(r["base"]) : null,
                        edge = (int)F(r["edge"]),
                        s0 = F(r["s0"]), s1 = F(r["s1"]),
                        seat0 = sa, seat1 = sb, s = Has(r, "s") ? F(r["s"]) : 0f
                    });
                }
                _runs = list.ToArray();
            }
            return _runs;
        }
    }

    // =====================================================================
    // 造成後の地盤 — **算出物から読むだけ**(裁定1=A)
    // =====================================================================
    class WGrid
    {
        public float x0, z0, step; public int nx, nz; public float[] h;   // NaN = null(区画の外)
        public float At(float x, float z)
        {
            float fx = (x - x0) / step, fz = (z - z0) / step;
            int i0 = Mathf.FloorToInt(fx), j0 = Mathf.FloorToInt(fz);
            float tx = fx - i0, tz = fz - j0;
            float acc = 0f, wt = 0f;
            for (int dj = 0; dj < 2; dj++)
                for (int di = 0; di < 2; di++)
                {
                    int i = i0 + di, j = j0 + dj;
                    if (i < 0 || i >= nx || j < 0 || j >= nz) continue;
                    float v = h[j * nx + i];
                    if (float.IsNaN(v)) continue;
                    float w = (di == 0 ? 1f - tx : tx) * (dj == 0 ? 1f - tz : tz);
                    acc += v * w; wt += w;
                }
            return wt > 1e-9f ? acc / wt : float.NaN;
        }
    }
    static WGrid _graded;
    static WGrid Graded
    {
        get
        {
            if (_graded == null)
            {
                var g = O(IMPL["graded"]);
                if (g == null) throw new Exception("算出物に graded が無い");
                var w = new WGrid
                {
                    x0 = F(g["x0"]), z0 = F(g["z0"]), step = F(g["step"]),
                    nx = (int)F(g["nx"]), nz = (int)F(g["nz"])
                };
                w.h = new float[w.nx * w.nz];
                var rows = A(g["h"]);
                if (rows == null || rows.Count != w.nz)
                    throw new Exception("算出物 graded.h の行数が nz と合わない");
                for (int j = 0; j < w.nz; j++)
                {
                    var row = A(rows[j]);
                    if (row == null || row.Count != w.nx)
                        throw new Exception("算出物 graded.h[" + j + "] の列数が nx と合わない");
                    for (int i = 0; i < w.nx; i++)
                        w.h[j * w.nx + i] = row[i] == null ? float.NaN : Convert.ToSingle(row[i]);
                }
                _graded = w;
            }
            return _graded;
        }
    }

    /// <summary>敷地内の一点の**造成後の高さ**[m]。区画の外は NaN。
    /// ⚠ 現況の地形を一切読まないので**冪等** — 何度流しても同じ結果になる。</summary>
    public static float DesignY(Vector2 p) { return Graded.At(p.x, p.y); }

    static float ImplTol(string key, float ifMissing)
    {
        var c = O(Get(IMPL, "checks"));
        return c != null && Has(c, key) ? F(c[key]) : ifMissing;
    }

    // =====================================================================
    // 群と地形の小物
    // =====================================================================
    static Transform Group(string child)
    {
        var r = GameObject.Find(GN);
        if (r == null) { r = new GameObject(GN); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);      // プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
        var cur = r.transform;
        if (string.IsNullOrEmpty(child)) return cur;
        foreach (var seg in child.Split('/'))
        {
            var nx = cur.Find(seg);
            if (nx == null)
            {
                var go = new GameObject(seg);
                Undo.RegisterCreatedObjectUndo(go, "grp");
                go.transform.SetParent(cur, false);
                nx = go.transform;
            }
            cur = nx;
        }
        return cur;
    }
    static void Clear(Transform t)
    { for (int i = t.childCount - 1; i >= 0; i--) UnityEngine.Object.DestroyImmediate(t.GetChild(i).gameObject); }

    static readonly string BakDir = "UserData/Backups/Okabe";
    static string BakPath { get { return Path.Combine(ProjRoot, BakDir + "/heightmap_pre.bin"); } }

    // =====================================================================
    // Stage0 — ハイトマップの退避(地形の編集は Undo の外)
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/0 ハイトマップを退避")]
    public static void Stage0Menu() { Debug.Log("[Okabe] " + Stage0_Backup()); }

    /// <summary>着工前の地形を .bin へ。**無いときだけ書く**。
    /// ⚠ 走るたび上書きすると、造成済みの(壊れた)地形がバックアップに化ける
    ///   — 旧版で実際に起きた(2026-08-16 の退避は既に造成後だった)。</summary>
    public static string Stage0_Backup()
    {
        if (File.Exists(BakPath)) return "退避: 既にある(上書きしない) " + BakDir;
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        int x0, z0, w, h; Window(out x0, out z0, out w, out h);
        var H = td.GetHeights(x0, z0, w, h);
        var dir = Path.GetDirectoryName(BakPath);
        if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
        using (var bw = new BinaryWriter(File.Open(BakPath, FileMode.Create)))
        {
            bw.Write(x0); bw.Write(z0); bw.Write(w); bw.Write(h);
            bw.Write(tp.x); bw.Write(tp.y); bw.Write(tp.z);
            bw.Write(ts.x); bw.Write(ts.y); bw.Write(ts.z); bw.Write(hres);
            for (int z = 0; z < h; z++) for (int x = 0; x < w; x++) bw.Write(H[z, x]);
        }
        return "退避 " + w + "x" + h + " → " + BakDir + "/heightmap_pre.bin";
    }

    /// <summary>造成とその検査が使う窓。**区画の外接矩形 + 余白**。
    /// ⚠ 退避と造成で窓を揃えないと、造成した外側を退避から戻せない。</summary>
    static void Window(out int x0, out int z0, out int w, out int h)
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in Poly)
        { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        const float PAD = 12f;
        Func<float, int> IX = delegate(float wx) { return Mathf.Clamp(Mathf.FloorToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1); };
        Func<float, int> IZ = delegate(float wz) { return Mathf.Clamp(Mathf.FloorToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1); };
        x0 = IX(mnx - PAD); z0 = IZ(mnz - PAD);
        int x1 = Mathf.Min(hres - 1, IX(mxx + PAD) + 1), z1 = Mathf.Min(hres - 1, IZ(mxz + PAD) + 1);
        w = x1 - x0 + 1; h = z1 - z0 + 1;
    }

    // =====================================================================
    // Stage1 — 造成(指図の面へ)
    //
    // ⚠ これは「段を作る」工事ではない。**敷地の 3/4 を江戸期の地盤へ戻す**工事でもある
    //   (指図 grading.kindaiJokyo: 近代造成の除去 33,400m³ の切土 / 35,256m³ の盛土・
    //    区画の 77.3% に及ぶ)。拝領時造成(3,733/1,722m³)はその上に乗る。
    // ⚠ 設計面は現況を一切読まないので**冪等**。多重実行に耐えるのでマーカーを置かない
    //   (旧版の `OKABE_GRADED_vNN` は「二回目以降は SKIP」で、一度壊れると自己修復しなかった)。
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/1 造成(指図の面へ)")]
    public static void Stage1Menu() { Debug.Log("[Okabe] " + Stage1_Grade()); }

    public static string Stage1_Grade()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage0_Backup());
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        int x0, z0, w, h; Window(out x0, out z0, out w, out h);
        var H = td.GetHeights(x0, z0, w, h);
        var P = Poly;
        int n = 0, hole = 0; float cmax = 0f, fmax = 0f;
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                var p = new Vector2(tp.x + (x0 + x) * ts.x / (hres - 1), tp.z + (z0 + z) * ts.z / (hres - 1));
                if (!EdoGeom.PIP(P, p)) continue;            // ⛔ 敷地の外は一切触らない
                float y = Graded.At(p.x, p.y);
                if (float.IsNaN(y)) { hole++; continue; }    // 算出物に穴 — 触らずに数える
                float cur = H[z, x] * ts.y + tp.y;
                if (y < cur) cmax = Mathf.Max(cmax, cur - y); else fmax = Mathf.Max(fmax, y - cur);
                H[z, x] = (y - tp.y) / ts.y; n++;
            }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        sb.AppendLine("造成 " + n + " セル(窓 " + w + "x" + h + ")｜今回の移動量: 下げ最大 "
                      + cmax.ToString("F2") + "m / 上げ最大 " + fmax.ToString("F2") + "m");
        if (hole > 0)
            sb.AppendLine("★ 区画の中なのに算出物が null のセルが " + hole
                          + " — `graded` の格子が区画を覆いきっていない(生成器の窓を広げること)");
        sb.AppendLine("⚠ ここに出るのは**いまの地形からの移動量**であって切盛量ではない。"
                      + "切盛の妥当性は指図の『切盛』の段別表が持つ");
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 造成の検査
    [MenuItem("Edo/岡部筑前守上屋敷/造成を検査 GradeQA")]
    public static void GradeQAMenu() { Debug.Log("[Okabe] " + GradeQA()); }

    /// <summary>敷地内の全セルで |地形 − 設計面| を測る。
    /// ⚠ **ハイトマップの格子の上でのみ測る。** `SampleHeight` を任意の座標で呼ぶと双一次補間が
    ///   入り、石垣の線や法面のような急な段で 0.1m のズレが 2m の差に化ける
    ///   (実測: 格子から 0.12m ずらして測っただけで 228 セルが「超過」に見えた)。</summary>
    public static string GradeQA()
    {
        float TOL = ImplTol("gradeTol", 0.30f);
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        int x0, z0, w, h; Window(out x0, out z0, out w, out h);
        var H = td.GetHeights(x0, z0, w, h);
        var P = Poly;
        int bad = 0, all = 0, hole = 0; float mx = 0f; Vector2 worst = Vector2.zero;
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                var p = new Vector2(tp.x + (x0 + x) * ts.x / (hres - 1), tp.z + (z0 + z) * ts.z / (hres - 1));
                if (!EdoGeom.PIP(P, p)) continue;
                float y = Graded.At(p.x, p.y);
                if (float.IsNaN(y)) { hole++; continue; }
                all++;
                float d = Mathf.Abs((H[z, x] * ts.y + tp.y) - y);
                if (d > TOL) bad++;
                if (d > mx) { mx = d; worst = p; }
            }
        return string.Format("造成QA 敷地内 {0} セル / 許容 {1:F2}m ｜ 超過 {2} ({3:F1}%) 最大 {4:F2}m @({5:F0},{6:F0}){7} {8}",
            all, TOL, bad, bad * 100f / Mathf.Max(1, all), mx, worst.x, worst.y,
            hole > 0 ? " ｜ 算出物の穴 " + hole : "", bad > 0 ? "✗" : "✔");
    }

    // =====================================================================
    // Stage2 — 外周(練塀・石垣基壇・木柵・隅の留め継ぎ)
    //
    // 【この巡で建てないもの】2026-09-03 ユーザー裁定3=B
    //   ・表門(長屋門・辺12 s6.189〜22.551)… 指図の `gate.asset` が「要選定」のまま
    //   ・表長屋 `E_Nagaya_S`/`E_Nagaya_N` … 該当長の部材が未生成。加えて指図の
    //     `const.nagayaH` 5.30 が在庫(平屋 5.509 / 二階 7.183)のどちらとも合わない
    //   ・通用口 `Tsuyodo`(辺10 s=8.0・棟門)… 型式に対応する部材が未指定
    //   ⚠ よって辺12 の 96.4m は素通しのまま残る。`ClosureQA` がその長さを数字で出す。
    //
    // 【開口は run の s が既に避けてある】表門は E_Nagaya_S/N の間、通用口は
    //   NE_Hei_F_1(〜6.65)と NE_Hei_F_2(9.35〜)の間。⛔ 実装側で開口を切り直さない
    //   — 二重に持つと指図を動かしたとき片方だけ残る。`OpeningQA` が食い違いを見張る。
    // =====================================================================
    /// <summary>犬走り = 石垣の法肩から囲いの外面まで。指図 `const.inubashiri`(1尺)。
    /// ⚠ 生成器の `_run_fp` は足跡の近似として「練塀は境界線に跨る(±dobeiT/2)」と置くが、
    ///   それだと外面が法肩より 0.575m **外**へ出て犬走りが取れず、`coping_check`
    ///   (天端に 犬走り+塀の掛かり が乗ること)とも噛み合わない。
    ///   ⭕ ここは `const.inubashiri` の定義(「石垣の法肩から囲いまで1尺」)に従う。
    ///   ⛔ 納めの一本化は指図方の宿題(報告2-④)。実装で決めない。</summary>
    public static float INUBASHIRI { get { return C("inubashiri"); } }

    /// <summary>石垣の駒の素の寸法(スケール1)。`unity-modular-stonewall` の作法。
    /// 指図は run ごとの倍率 `s` を持ち、壁高 = `const.baseUnit`×s / 天端幅 1.4s / 底厚 2.4s。</summary>
    const float IG_RUN = 2.00f;          // 駒の走り方向の実体長
    const float IG_PITCH_MAX = 1.80f;    // ピッチの上限(重なり 0.20m を必ず残す)
    /// <summary>隅部材・練塀の直線材に共通の倍率。素の部材は江戸暦の単位なので ES を掛ける。</summary>
    const float ES = 1.818f;

    /// <summary>囲いの「外面」を成す部材の名前。屋根・軒・垂木は**外面ではない**(庇は出てよい)。</summary>
    static readonly HashSet<string> WallFace = new HashSet<string> {
        "hei", "shitami", "koshi", "namako", "namako2", "n_namako", "dodai", "n_dodai", "hashira2"
    };

    [MenuItem("Edo/岡部筑前守上屋敷/2 外周(練塀・基壇・木柵・隅)")]
    public static void Stage2Menu() { Debug.Log("[Okabe] " + Stage2_Perimeter()); }

    public static string Stage2_Perimeter()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder();
        EdoNishiTameikeBuilder.NaturalMode = false;      // 天端は run の seat で通す
        var kak = Group("Kakoi"); Clear(kak);

        // ---- 練塀 ------------------------------------------------------
        int hei = 0, skipped = 0;
        foreach (var r in Runs)
        {
            if (r.Nagaya) { skipped++; continue; }        // 表長屋は次巡(裁定3=B)
            if (!r.Dobei)
            { sb.AppendLine("★ run " + r.name + " の kind が未知: " + r.kind); continue; }
            Vector2 outw = OutNormal(r.edge);
            Vector2 a = EdgePt(r.edge, r.s0), b = EdgePt(r.edge, r.s1);
            if (Mathf.Abs(r.seat1 - r.seat0) < 0.01f)
            {
                EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, r.name, false, r.seat0, Vector2.zero, -1);
                hei++;
            }
            else
            {
                // 斜面の run は天端が一直線に下るので、2m 刻みに割ってその位置の天端で据える
                // (石垣そのものは水平が正典。run 全体では階段状に下る)
                float L = (b - a).magnitude;
                int nSeg = Mathf.Max(1, Mathf.RoundToInt(L / 2.0f));
                for (int q = 0; q < nSeg; q++)
                {
                    Vector2 pa = Vector2.Lerp(a, b, q / (float)nSeg);
                    Vector2 pb = Vector2.Lerp(a, b, (q + 1) / (float)nSeg);
                    float sMid = Mathf.Lerp(r.s0, r.s1, (q + 0.5f) / nSeg);
                    EdoNishiTameikeBuilder.DobeiRun(kak, pa, pb, outw, r.name + "_" + q, false,
                                                    r.SeatAt(sMid), Vector2.zero, -1);
                }
                hei++;
            }
        }
        sb.AppendLine("練塀: " + hei + " run 据えた / 表長屋 " + skipped + " run は次巡(部材が未選定)");

        // ---- 隅の留め継ぎ ----------------------------------------------
        sb.AppendLine(PlaceKado(kak));

        // ---- 犬走りへ寄せる(据えた駒の実メッシュから外面を測る)----------
        sb.AppendLine(AlignInubashiri());

        // ---- 石垣基壇 --------------------------------------------------
        sb.AppendLine(PlaceIshigaki());

        // ---- 木柵 ------------------------------------------------------
        sb.AppendLine(PlaceFences());

        sb.AppendLine("⚠ 表門・表長屋・通用口は据えていない(裁定3=B)。閉じは ClosureQA を見ること");
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 石垣基壇
    /// <summary>基壇石垣。**run ごとの倍率 `s`** で据える(壁高 4.0s / 天端幅 1.4s / 底厚 2.4s)。
    /// 露出が `const.baseMin` を下回る区間には**置かない** — 面の縁を面の高さで通す以上、
    /// 外の地盤が面に迫る区間で基壇が消えるのは正しい(欠陥ではない)。
    /// ⚠ どの区間に置くかは生成器が `edgeProfile` と seat から算出した `impl.base[].segs` が正典。
    /// 据え: 法肩を区画線の上に置く(Castle Wall のメッシュは局所 X が −2.4〜0 で +X が外向き)。</summary>
    static string PlaceIshigaki()
    {
        var grp = Group("Ishigaki"); Clear(grp);
        var baseByRun = new Dictionary<string, Dictionary<string, object>>();
        foreach (var o in A(Get(IMPL, "base")) ?? new List<object>())
        { var e = O(o); if (e != null) baseByRun[S(e["run"])] = e; }

        int made = 0, seg = 0; var miss = new List<string>(); float thin = 0f;
        foreach (var r in Runs)
        {
            if (!r.Ishigaki) continue;
            if (!baseByRun.ContainsKey(r.name)) { miss.Add(r.name); continue; }
            var bd = baseByRun[r.name];
            float sc = Has(bd, "s") ? F(bd["s"]) : r.s;
            if (sc <= 0f) { miss.Add(r.name + "(倍率 s が 0)"); continue; }
            foreach (var q in A(Get(bd, "thin")) ?? new List<object>())
            { var t2 = A(q); if (t2 != null && t2.Count == 2) thin += F(t2[1]) - F(t2[0]); }

            Vector2 nrm = OutNormal(r.edge);
            float psi = Mathf.Atan2(-nrm.y, nrm.x) * Mathf.Rad2Deg;   // 局所 +X を外向きに
            float unit = IG_RUN * sc, pitchMax = IG_PITCH_MAX * sc, wallH = C("baseUnit") * sc;
            foreach (var q in A(Get(bd, "segs")) ?? new List<object>())
            {
                var t2 = A(q); if (t2 == null || t2.Count != 2) continue;
                float t0 = F(t2[0]), t1 = F(t2[1]), L = t1 - t0;
                if (L <= 0.01f) continue;
                int N = (L <= unit) ? 1 : Mathf.CeilToInt((L - unit) / pitchMax) + 1;
                float pitch = (N > 1) ? (L - unit) / (N - 1) : 0f;
                for (int i = 0; i < N; i++)
                {
                    float tt = t0 + pitch * i;
                    float mid = Mathf.Min(tt + unit * 0.5f, t1);
                    Vector2 p = EdgePt(r.edge, tt);
                    var go = EdoBuild.Place(EdoAssets.JC.CastleWall,
                        new Vector3(p.x, r.SeatAt(mid) - wallH, p.y), psi,
                        Vector3.one * sc, grp, "IG_" + r.name + "_" + made);
                    if (go != null) made++;
                }
                seg++;
            }
        }
        var sb = new System.Text.StringBuilder();
        sb.Append("石垣基壇: " + made + " 駒 / " + seg + " 区間");
        if (thin > 0.05f) sb.Append(" ｜ 基壇を置かない区間 " + thin.ToString("F1") + "m(露出 < baseMin)");
        if (miss.Count > 0)
            sb.Append("\n★ 算出物 base に無い run " + miss.Count + " 件: " + string.Join(" / ", miss.ToArray()));
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 木柵
    /// <summary>木柵(辺5=溜池の堤)。**基礎も整地も石垣も持たない地形なり**なので天端を持たない。
    /// ⚠ ピッチを決め打ちしない — 部材を1枚置いて実寸を測り、端から端まで敷き詰める
    ///   (2026-08-29 EDO-0053: SPAN 決め打ちに対し実寸が 0.49m 短く、駒ごとに穴が開いていた)。
    /// ⚠ 汀の柵には**見透しの潜り**(`nishi.saku.kido`)が開く。その区間は柵を置かない
    ///   (潜りの戸そのものは西の斜面の巡で据える)。</summary>
    static string PlaceFences()
    {
        var fen = Group("Fences"); Clear(fen);
        var sb = new System.Text.StringBuilder();
        // 柵に開く口(指図が持つものだけ。実装で発明しない)
        var gaps = new List<float[]>();     // {edge, s0, s1}
        var saku = O(Get(O(Get(D, "nishi")), "saku"));
        if (saku != null && Has(saku, "kido"))
        {
            var k = O(saku["kido"]);
            float s = F(k["s"]), w = F(k["w"]);
            gaps.Add(new float[] { F(saku["edge"]), s - w / 2f, s + w / 2f });
        }
        int posts = 0, runs = 0; float wMeasured = 0f;
        foreach (var o in A(D["fences"]) ?? new List<object>())
        {
            var fd = O(o); if (fd == null) continue;
            int e = (int)F(fd["edge"]);
            float s0 = F(fd["s0"]), s1 = F(fd["s1"]);
            Vector2 outw = OutNormal(e);
            float psi = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;
            float w = MeasureRunWidth(EdoAssets.Eg.Hogaki5, fen, psi);
            if (w <= 0f) { sb.AppendLine("★ 柵の部材が無い: " + EdoAssets.Eg.Hogaki5); continue; }
            wMeasured = w;
            const float OVER = 0.15f;     // 折れ角で口が開かないよう端を重ねる
            float a0 = s0 - OVER, a1 = s1 + OVER, L = a1 - a0;
            int nF = Mathf.Max(1, Mathf.CeilToInt((L - w) / Mathf.Max(0.1f, w - OVER)) + 1);
            float pitch = nF > 1 ? (L - w) / (nF - 1) : 0f;
            for (int q = 0; q < nF; q++)
            {
                float s = a0 + w * 0.5f + pitch * q;
                bool inGap = false;
                foreach (var g in gaps)
                    if ((int)g[0] == e && s + w * 0.5f > g[1] && s - w * 0.5f < g[2]) inGap = true;
                if (inGap) continue;
                Vector2 p = EdgePt(e, s);
                var go = EdoBuild.Place(EdoAssets.Eg.Hogaki5, new Vector3(p.x, 0, p.y),
                                        psi, Vector3.one, fen, S(fd["name"]) + "_" + posts);
                if (go == null) continue;
                float gy = Graded.At(p.x, p.y);
                if (float.IsNaN(gy)) gy = EdoBuild.Ground(p.x, p.y);
                EdoBuild.SeatBottom(go, gy - 0.05f);
                posts++;
            }
            runs++;
        }
        sb.Append("木柵: " + posts + " 枚 / " + runs + " run(駒の実寸 " + wMeasured.ToString("F3") + "m)");
        if (gaps.Count > 0) sb.Append(" ｜ 潜りの口 " + gaps.Count + " 箇所を空けた(戸は次巡)");
        // 指図の柵の高さと部材の実丈を突き合わせる(⛔ 合わないときに黙って据えない)
        if (Has(O(D["const"]), "fenceH"))
        {
            float want = C("fenceH");
            float got = MeasureHeight(EdoAssets.Eg.Hogaki5, fen);
            if (got > 0f && Mathf.Abs(got - want) > 0.15f)
                sb.Append("\n★ 柵の丈が指図と合わない: 指図 const.fenceH " + want.ToString("F2")
                        + "m / 部材の実丈 " + got.ToString("F2") + "m(" + EdoAssets.Eg.Hogaki5 + ")");
        }
        return sb.ToString();
    }

    /// <summary>部材を1枚置いて**走り方向の実寸**を測り、すぐ捨てる。
    /// ⛔ 決め打ちの定数に戻さない — 部材を差し替えた瞬間に穴が開く。</summary>
    static float MeasureRunWidth(string path, Transform parent, float psi)
    {
        var probe = EdoBuild.Place(path, new Vector3(0, -9999f, 0), psi, Vector3.one, parent, "__probe");
        if (probe == null) return 0f;
        var b = EdoBuild.RB(probe);
        float w = Mathf.Max(b.size.x, b.size.z);
        UnityEngine.Object.DestroyImmediate(probe);
        return w;
    }
    static float MeasureHeight(string path, Transform parent)
    {
        var probe = EdoBuild.Place(path, new Vector3(0, -9999f, 0), 0f, Vector3.one, parent, "__probe");
        if (probe == null) return 0f;
        float hgt = EdoBuild.RB(probe).size.y;
        UnityEngine.Object.DestroyImmediate(probe);
        return hgt;
    }

    // ---------------------------------------------------------------- 隅の留め継ぎ
    /// <summary>隅部材を据える。**折れ角は区画が決めるもので毎回違う**ので決め打ちしない。
    /// 角度・部材・天端は生成器が算出した `impl.corners` が正典(指図の json は持たない)。
    /// 据え: `position = 頂点 / yaw = 入りの run の走りの方位 / scale = ES`。
    /// ⚠ 直線材は `SeatBottom(seat − 0.10)` で沈めてあるので、隅も同じだけ沈める
    ///   (seat ちょうどだと 0.10m 浮いて軒の線が隅で段になる)。</summary>
    static string PlaceKado(Transform parent)
    {
        var list = A(Get(IMPL, "corners"));
        if (list == null) return "隅部材: 算出物に corners が無い(生成器の --export-impl 待ち)";
        var P = Poly; int n = P.Length;
        int made = 0, skip = 0; var miss = new List<string>();
        foreach (var o in list)
        {
            var c = O(o); if (c == null) continue;
            if (!Has(c, "part")) { skip++; continue; }        // 留め継ぎでない隅(当家が建てない側など)
            string part = S(c["part"]);
            if (part == "Nagaya") { skip++; continue; }       // 表長屋の隅は次巡
            float deg = F(c["deg"]);
            string path = EdoAssets.Own.Kado(part, deg);
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (src == null)
            {
                miss.Add(S(c["id"]) + " → " + path
                       + "(blender --background --python Tools/Blender/build_kado.py -- --part "
                       + part.ToLowerInvariant() + " --deg " + deg.ToString("F1") + ")");
                continue;
            }
            int v = (int)F(c["vertex"]);
            Vector2 b = P[v % n], a = P[(v - 1 + n) % n];
            Vector2 dIn = (b - a).normalized;                  // 入りの run の走り
            float seat = Has(c, "seat") ? F(c["seat"]) : F(c["seatIn"]);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
            Undo.RegisterCreatedObjectUndo(go, "kado");
            go.name = "Kado_" + S(c["id"]);
            go.transform.position = new Vector3(b.x, seat - 0.10f, b.y);
            go.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(dIn.x, dIn.y) * Mathf.Rad2Deg, 0);
            go.transform.localScale = Vector3.one * ES;
            made++;
        }
        var sb = new System.Text.StringBuilder("隅部材: " + made + " 基(留め継ぎでない/次巡 " + skip + ")");
        if (miss.Count > 0)
            sb.Append("\n★ 部材が無い " + miss.Count + " 件 — " + string.Join(" / ", miss.ToArray()));
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 犬走り
    /// <summary>**石垣の法肩から犬走りを残して囲いを据え直す。**
    /// 石垣は法肩を区画線の上に置いて据えるので、囲いの外面の目標は**線から内へ `inubashiri`**。
    /// ⛔ 部材の見かけ幅を決め打ちしない — **置いた駒の実メッシュから外面を測って**寄せる
    ///   (部材を差し替えた瞬間に決め打ちは壊れる。2026-08-29 EDO-0053 で全 39 run が外れていた)。</summary>
    public static string AlignInubashiri()
    {
        var kak = Group("Kakoi");
        var P = Poly;
        float target = -INUBASHIRI;
        int moved = 0, seen = 0; float worst = 0f; string worstName = null;
        for (int i = 0; i < kak.childCount; i++)
        {
            var c = kak.GetChild(i);
            int ri = -1;
            for (int k = 0; k < Runs.Length; k++)
                if (c.name.StartsWith(Runs[k].name) && (ri < 0 || Runs[k].name.Length > Runs[ri].name.Length)) ri = k;
            if (ri < 0) continue;
            var r = Runs[ri];
            Vector2 nrm = OutNormal(r.edge);
            var a = P[r.edge % P.Length];
            float best = float.MinValue;
            foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                if (!WallFace.Contains(mf.gameObject.name)) continue;
                var m = mf.transform.localToWorldMatrix;
                var vs = mf.sharedMesh.vertices;
                for (int q = 0; q < vs.Length; q++)
                {
                    var w = m.MultiplyPoint3x4(vs[q]);
                    best = Mathf.Max(best, (w.x - a.x) * nrm.x + (w.z - a.y) * nrm.y);
                }
            }
            if (best == float.MinValue) continue;
            seen++;
            float shift = target - best;
            if (Mathf.Abs(shift) > Mathf.Abs(worst)) { worst = shift; worstName = c.name; }
            if (Mathf.Abs(shift) > 0.02f)
            { c.position += new Vector3(nrm.x * shift, 0f, nrm.y * shift); moved++; }
        }
        return "犬走りへ寄せた: " + moved + " / " + seen + " 駒(最大の寄せ "
             + worst.ToString("+0.00;-0.00") + "m @" + (worstName ?? "-") + " ・目標 "
             + target.ToString("F2") + "m)";
    }

    // =====================================================================
    // 外周の検査
    // =====================================================================
    struct Iv { public float a, b; }
    static float UnionLen(List<Iv> ivs, float lo, float hi)
    {
        ivs.Sort(delegate(Iv p, Iv q) { return p.a.CompareTo(q.a); });
        float tot = 0f, cur = lo;
        foreach (var v in ivs)
        {
            float a = Mathf.Max(v.a, lo), b = Mathf.Min(v.b, hi);
            if (b <= cur) continue;
            tot += b - Mathf.Max(a, cur);
            cur = b;
        }
        return tot;
    }

    /// <summary>指図の開口(表門・通用口)。**辺と s の区間**で返す。</summary>
    static List<float[]> Openings()
    {
        var outp = new List<float[]>();
        var g = O(Get(D, "gate"));
        if (g != null)
        {
            float w = F(O(g["plan"])["monW"]), s = F(g["s"]);
            outp.Add(new float[] { F(g["edge"]), s - w / 2f, s + w / 2f, 0f });   // 0 = 表門
        }
        foreach (var o in A(Get(D, "komon")) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue;
            float s = F(k["s"]), w = F(k["w"]);
            outp.Add(new float[] { F(k["edge"]), s - w / 2f, s + w / 2f, 1f });   // 1 = 小門
        }
        return outp;
    }

    [MenuItem("Edo/岡部筑前守上屋敷/外周の閉じを検査 ClosureQA")]
    public static void ClosureQAMenu() { Debug.Log("[Okabe] " + ClosureQA()); }

    /// <summary>**外周が全周で閉じているか**を辺ごとに数字で出す。二つを別々に測る:
    ///   ① 指図の素通し … 指図の run・木柵・開口で覆えない長さ(指図そのものの穴)
    ///   ② 実装の素通し … いま**建っている**物と開口で覆えない長さ(この巡の未達)
    /// ⚠ ②が 0 でない=欠陥、ではない。表門・表長屋・通用口は裁定3=B で次巡に回してある。
    ///   ⛔ だからといって数字を出さないと「据えたつもり」が見えなくなる。</summary>
    public static string ClosureQA()
    {
        var P = Poly; int n = P.Length;
        var ops = Openings();
        var sb = new System.Text.StringBuilder("外周の閉じ\n");
        float sumDoc = 0f, sumImpl = 0f;
        for (int e = 0; e < n; e++)
        {
            float len = EdgeLen(e);
            var doc = new List<Iv>(); var impl = new List<Iv>();
            bool ours = false;
            foreach (var r in Runs)
                if (r.edge == e)
                {
                    ours = true;
                    doc.Add(new Iv { a = r.s0, b = r.s1 });
                    if (r.Dobei) impl.Add(new Iv { a = r.s0, b = r.s1 });
                }
            foreach (var o in A(Get(D, "fences")) ?? new List<object>())
            {
                var fd = O(o); if (fd == null || (int)F(fd["edge"]) != e) continue;
                ours = true;
                doc.Add(new Iv { a = F(fd["s0"]), b = F(fd["s1"]) });
                impl.Add(new Iv { a = F(fd["s0"]), b = F(fd["s1"]) });
            }
            foreach (var op in ops)
                if ((int)op[0] == e)
                { doc.Add(new Iv { a = op[1], b = op[2] }); impl.Add(new Iv { a = op[1], b = op[2] }); }
            if (!ours)
            { sb.AppendLine(string.Format("  辺{0,2} {1,7:F1}m  — 当家は建てない(隣家の持ち物)", e, len)); continue; }
            float gDoc = len - UnionLen(new List<Iv>(doc), 0f, len);
            float gImpl = len - UnionLen(new List<Iv>(impl), 0f, len);
            sumDoc += Mathf.Max(0f, gDoc); sumImpl += Mathf.Max(0f, gImpl);
            sb.AppendLine(string.Format("  辺{0,2} {1,7:F1}m  指図の素通し {2,6:F2}m {3}  実装の素通し {4,6:F2}m {5}",
                e, len, gDoc, gDoc > 0.05f ? "✗" : "✔", gImpl, gImpl > 0.05f ? "✗" : "✔"));
        }
        sb.AppendLine(string.Format("  合計  指図 {0:F2}m {1} / 実装 {2:F2}m {3}",
            sumDoc, sumDoc > 0.05f ? "✗" : "✔", sumImpl, sumImpl > 0.05f ? "✗(次巡の門・表長屋)" : "✔"));
        return sb.ToString();
    }

    [MenuItem("Edo/岡部筑前守上屋敷/開口と run の食い違いを検査 OpeningQA")]
    public static void OpeningQAMenu() { Debug.Log("[Okabe] " + OpeningQA()); }

    /// <summary>**開口の上に囲いが載っていないか。**指図は run の `s` で既に開口を避けてあるので、
    /// ここが 0 でなければ**指図か区画のどちらかが動いた**合図(実装は開口を切り直さない)。</summary>
    public static string OpeningQA()
    {
        var sb = new System.Text.StringBuilder("開口と run\n");
        int bad = 0;
        foreach (var op in Openings())
        {
            int e = (int)op[0];
            string kind = op[3] < 0.5f ? "表門" : "小門";
            float worst = 0f; string who = null;
            foreach (var r in Runs)
            {
                if (r.edge != e) continue;
                float ov = Mathf.Min(r.s1, op[2]) - Mathf.Max(r.s0, op[1]);
                if (ov > worst) { worst = ov; who = r.name; }
            }
            sb.AppendLine(string.Format("  {0} 辺{1} s={2:F3}〜{3:F3}  重なり {4:F3}m {5}",
                kind, e, op[1], op[2], Mathf.Max(0f, worst),
                worst > 0.01f ? "✗ " + who : "✔"));
            if (worst > 0.01f) bad++;
        }
        sb.Append(bad == 0 ? "  0 件 ✔" : "  ★ " + bad + " 件");
        return sb.ToString();
    }

    [MenuItem("Edo/岡部筑前守上屋敷/区画と指図の座標を突き合わせる")]
    public static void ParcelQAMenu() { Debug.Log("[Okabe] " + ParcelQA()); }

    /// <summary>**区画の正典(parcels.json)と指図の同期コピーが一致しているか。**
    /// ⚠ 一致していないと、辺の実長と run の `s1` が食い違い、隅に素通しが出るか run が辺を
    ///   はみ出す(2026-09-03 実測: P2 が 0.600m・P3 が 1.128m ずれ、辺2 で 0.830m のはみ出しと
    ///   辺3 で 0.690m の素通しになっていた)。⛔ 実装で丸めて隠さない — 指図を同期し直すこと。</summary>
    public static string ParcelQA()
    {
        var P = Poly;
        var jp = A(Get(D, "polygon"));
        var sb = new System.Text.StringBuilder("区画 ⇔ 指図の polygon\n");
        int bad = 0;
        if (jp == null) return "指図に polygon が無い";
        if (jp.Count != P.Length)
        { sb.AppendLine("  ★ 頂点数が違う 指図 " + jp.Count + " / 正典 " + P.Length); bad++; }
        int m = Mathf.Min(jp.Count, P.Length);
        for (int i = 0; i < m; i++)
        {
            var q = A(jp[i]); if (q == null || q.Count < 2) continue;
            var d = new Vector2(F(q[0]), F(q[1])) - P[i];
            if (d.magnitude > 0.005f)
            { sb.AppendLine(string.Format("  ★ P{0} が {1:F3}m ずれ(指図 {2:F3},{3:F3} / 正典 {4:F3},{5:F3})",
                i, d.magnitude, F(q[0]), F(q[1]), P[i].x, P[i].y)); bad++; }
        }
        var el = A(Get(D, "edges"));
        if (el != null)
            for (int e = 0; e < el.Count && e < P.Length; e++)
            {
                var ed = O(el[e]); if (ed == null || !Has(ed, "len")) continue;
                float d = F(ed["len"]) - EdgeLen(e);
                if (Mathf.Abs(d) > 0.005f)
                { sb.AppendLine(string.Format("  ★ 辺{0} の長さが {1:+0.000;-0.000}m ずれ(指図 {2:F3} / 実長 {3:F3})",
                    e, d, F(ed["len"]), EdgeLen(e))); bad++; }
            }
        // run の s1 が辺からはみ出す / 届かない
        foreach (var r in Runs)
        {
            float over = r.s1 - EdgeLen(r.edge);
            if (over > 0.005f)
            { sb.AppendLine(string.Format("  ★ run {0} が辺{1} を {2:F3}m はみ出す", r.name, r.edge, over)); bad++; }
        }
        sb.Append(bad == 0 ? "  0 件 ✔" : "  ★ " + bad + " 件 — 指図を parcels.json へ同期し直すこと(2026-09-03 裁定2=A)");
        return sb.ToString();
    }

    // =====================================================================
    // 通し
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/S1→S2 を通す")]
    public static void RunAllMenu() { Debug.Log("[Okabe] " + RunAll()); }

    public static string RunAll()
    {
        Reload();
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(ParcelQA());
        sb.AppendLine(Stage1_Grade());
        sb.AppendLine(GradeQA());
        sb.AppendLine(Stage2_Perimeter());
        sb.AppendLine(OpeningQA());
        sb.AppendLine(ClosureQA());
        return sb.ToString();
    }

    // =====================================================================
    // マテリアルの remap(旧版から引き継いだ2本 — 部材の作りに依存する処理なので残す)
    // =====================================================================
    /// <summary>FBX/OBJ を入れたままだと全部真っ白になるので remap する。
    /// ⚠ **隅部材は全邸で共通**(`Assets/Edo/Models/Kado` を丸ごと舐める)。岡部の下にしか
    ///   メニューが無く、松平から呼べずに隅が真っ白で建った(2026-08-30)。
    ///   → `Edo/共通/…` へも同じ処理を出した。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/隅部材のマテリアルをremap")]
    public static void RemapKadoMaterials()
    { Debug.Log("[Okabe] 隅 remap: " + RemapDir("Assets/Edo/Models/Kado") + "件 / " + BindDonorMaterials()); }

    [MenuItem("Edo/共通/隅部材のマテリアルをremap")]
    public static void RemapKadoMaterialsCommon() { RemapKadoMaterials(); }

    /// <summary>素材の**提供元**からマテリアルを直接結ぶ。
    /// ⚠ `SearchAndRemapMaterials` は**独立した .mat しか探さない**。edogoyomi の直線材
    /// (`knagaya01c.obj` / `s_hei_center.obj`)はマテリアルを .obj の中に**サブアセットとして
    /// 抱えている**ので、名前が一致していても当たらず真っ白のまま出る(2026-08-19 実測)。</summary>
    static string BindDonorMaterials()
    {
        var donors = new[] { EdoAssets.Eg.KnagayaC, EdoAssets.Eg.KnagayaL, EdoAssets.Eg.DobeiCenter };
        var byName = new Dictionary<string, Material>();
        foreach (var d in donors)
            foreach (var o in AssetDatabase.LoadAllAssetsAtPath(d))
            { var m = o as Material; if (m != null && !byName.ContainsKey(m.name)) byName[m.name] = m; }
        int n = 0;
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Edo/Models/Kado" }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(path) as ModelImporter; if (imp == null) continue;
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(path); if (go == null) continue;
            bool touched = false;
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null) continue;
                    Material donor;
                    if (!byName.TryGetValue(m.name, out donor)) continue;
                    if (donor == m) continue;
                    imp.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), m.name), donor);
                    touched = true;
                }
            if (touched) { AssetDatabase.WriteImportSettingsIfDirty(path); AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate); n++; }
        }
        AssetDatabase.SaveAssets();
        return "提供元から結んだ " + n + "件";
    }

    [MenuItem("Edo/岡部筑前守上屋敷/坂の土留めのマテリアルをremap")]
    public static void RemapSakaMaterials()
    { Debug.Log("[Okabe] 坂の土留めのマテリアル remap: " + RemapDir("Assets/Edo/Models/Ishigaki") + "件"); }

    static int RemapDir(string dir)
    {
        int n = 0;
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { dir }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var imp = AssetImporter.GetAtPath(path) as ModelImporter;
            if (imp == null) continue;
            imp.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            imp.SearchAndRemapMaterials(ModelImporterMaterialName.BasedOnMaterialName,
                                        ModelImporterMaterialSearch.Everywhere);
            AssetDatabase.WriteImportSettingsIfDirty(path);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            if (imp.GetExternalObjectMap().Count > 0) n++;
            else Debug.LogWarning("[Okabe] マテリアルが当たらなかった: " + path);
        }
        AssetDatabase.SaveAssets();
        return n;
    }
}
