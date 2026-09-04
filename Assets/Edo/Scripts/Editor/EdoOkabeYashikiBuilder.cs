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
        string want = Convert.ToString(src["sha256"]);
        string got = EdoQaVerdict.Sha256Hex(Path.Combine(ProjRoot, SashizuRel));
        if (!EdoQaVerdict.FingerprintMatches(want, got))
            throw new Exception("⛔ 算出物が**いまの指図から焼かれていない**"
                + "\n   指図 " + got.Substring(0, 16) + "… / 算出物が名乗る元 " + want.Substring(0, Math.Min(16, want.Length)) + "…"
                + "\n   `python3 Tools/Sashizu/build_okabe_sashizu.py --export-impl` を回し直すこと");
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
    //   ⭕ **通用口 `Tsuyodo` は建つ**(2026-09-04 部材方が棟門を新造・登録) — 裁定3=B で
    //     次巡に回した3件のうち、部材が揃ったこれだけ前倒しした。
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
        var wait = new List<string>();
        EdoNishiTameikeBuilder.NaturalMode = false;      // 天端は run の seat で通す
        var kak = Group("Kakoi"); Clear(kak);

        // ---- 表長屋・表門(⭐ 練塀より**先**に据える)-----------------------
        //   隅の返し(短い練塀)は長屋の**実測の妻面**へ突き付けるので、先に据えて面を測る
        _nagayaSpan.Clear();
        string nagRep = PlaceOmoteNagaya(kak, wait);

        // ---- 練塀 ------------------------------------------------------
        int hei = 0, skipped = 0;
        foreach (var r in Runs)
        {
            if (r.Nagaya) continue;                       // 表長屋は下でまとめて据える
            if (!r.Dobei)
            { sb.AppendLine("★ run " + r.name + " の kind が未知: " + r.kind); continue; }
            Vector2 outw = OutNormal(r.edge);
            // ⭐ **隅の返し**の納め(其十九)。隣が長屋の run なら、その**実測の妻面**へ突き付ける。
            //   ⛔ 呼び寸法で継がない(可動側は返し=練塀の側)。
            float rs0 = r.s0, rs1 = r.s1;
            foreach (var nr in Runs)
            {
                if (!nr.Nagaya || nr.edge != r.edge || !_nagayaSpan.ContainsKey(nr.name)) continue;
                var span = _nagayaSpan[nr.name];
                if (Mathf.Abs(nr.s1 - r.s0) < 0.30f) rs0 = span.y;   // 長屋の北 → 返しの南の小口
                if (Mathf.Abs(nr.s0 - r.s1) < 0.30f) rs1 = span.x;
            }
            if (Mathf.Abs(rs0 - r.s0) > 0.001f || Mathf.Abs(rs1 - r.s1) > 0.001f)
                wait.Add("練塀 " + r.name + ": 隣の長屋の**実測の妻面**へ寄せた s "
                       + r.s0.ToString("0.###") + "〜" + r.s1.ToString("0.###") + " → "
                       + rs0.ToString("0.###") + "〜" + rs1.ToString("0.###")
                       + "(⛔ 呼び寸法で継がない・可動側は練塀)");
            Vector2 a = EdgePt(r.edge, rs0), b = EdgePt(r.edge, rs1);
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
        sb.AppendLine(nagRep);
        sb.AppendLine("練塀: " + hei + " run 据えた");

        // ---- 隅の留め継ぎ ----------------------------------------------
        sb.AppendLine(PlaceKado(kak));

        // ---- 犬走りへ寄せる(据えた駒の実メッシュから外面を測る)----------
        sb.AppendLine(AlignInubashiri());

        // ---- 石垣基壇 --------------------------------------------------
        sb.AppendLine(PlaceIshigaki());

        // ---- 通用口(小門)----------------------------------------------
        sb.AppendLine(PlaceKomon());

        // ---- 木柵 ------------------------------------------------------
        sb.AppendLine(PlaceFences());

        if (wait.Count > 0)
        {
            sb.AppendLine("── 外周で据えなかったもの " + wait.Count + " 件 ──");
            foreach (var w in wait) sb.AppendLine("  ★ " + w);
        }
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 表長屋と表門
    /// <summary>外周の表長屋と表門。⭕ **2026-09-04 裁定12=A**(二階・棟 7.183 / 表門の棟 8.5)。
    ///
    /// ⚠⚠ **呼び寸法は run の長さ そのもの。**部材の `len` は**破風まで含む全幅**で、
    /// 隣の破風と**突き付く**。3棟の全幅の和 6.189 + 16.362 + 73.475 = 96.026 が辺12 の実長に一致する。
    /// ⛔ 「run 長 + 妻の出×2」で頼まない — 2026-09-04 に一度そう書いて指図方に正された。
    /// ⛔ 丸ごとのモジュールを並べない(端が成り行きになって門・隅に隙間が空く)。
    ///
    /// ⚠ ピボットは **走りの中心・土台の底(門は敷居)・壁の外面**。壁の外面なので、
    /// 置く時点で犬走りぶん内へ寄せる。**+Z = 見え面**を外へ向ける。
    /// ⚠ 材質は `Edo/長屋/表長屋のマテリアルをremap` を打たないと真っ白になる。</summary>
    static string PlaceOmoteNagaya(Transform kak, List<string> wait)
    {
        var rf = O(Get(O(Get(D, "roofs")), "OmoteNagaya"));
        bool nikai = rf != null && Has(rf, "kai") && S(rf["kai"]).Contains("二階");
        // ⚠ 棟高は**表長屋と表門で違う**(裁定12=A: 長屋 7.183 / 門 8.5)。
        //   ⛔ 「最後に据えた現物」と比べると門の高さで長屋を裁いてしまう(2026-09-04 に誤報)。
        int made = 0, miss = 0; float lastH = 0f, nagH = 0f;
        var sb = new System.Text.StringBuilder();

        // ---- 表長屋の run(⭕ 部材は指図の `runs[].asset` が名指しする)
        foreach (var r in Runs)
        {
            if (!r.Nagaya) continue;
            float call = Mathf.Round((r.s1 - r.s0) * 1000f) / 1000f;   // ⭕ run 長そのもの
            string key = null;
            foreach (var o in A(D["runs"]) ?? new List<object>())
            { var q = O(o); if (q != null && S(q["name"]) == r.name && Has(q, "asset")) key = S(q["asset"]); }
            string path = key != null ? AssetByKey(key, call, 0f)
                        : (nikai ? EdoAssets.Own.NagayaOmote2F(call) : EdoAssets.Own.NagayaOmote(call));
            if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            {
                miss++;
                wait.Add("表長屋 " + r.name + "(run " + call.ToString("0.###") + "m"
                       + (nikai ? "・二階" : "") + "): 部材が無い " + (path ?? key)
                       + " → blender --background --python Tools/Blender/build_nagaya_omote.py -- "
                       + call.ToString("0.###") + (nikai ? " --floors 2" : ""));
                continue;
            }
            if (PlaceNagayaPiece(kak, r.name, path, r.edge, (r.s0 + r.s1) * 0.5f,
                                 r.SeatAt((r.s0 + r.s1) * 0.5f), call, wait, ref lastH)) { made++; nagH = lastH; }
        }

        // ---- 表門 — 長屋の躯体に門口を抜いた版(裁定12=A)
        {
            var g = O(Get(D, "gate"));
            var gp = g == null ? null : O(Get(g, "plan"));
            if (gp != null && Has(gp, "monW"))
            {
                float monW = F(gp["monW"]);
                // ⚠ 門口は**部材のローカル +X の左端から**測る。門は桁行の中央に開くので monW/2。
                //   ⛔ 向きを式で決め切らない — 据えた実メッシュの穴の位置は検査で見張る
                float gc = Mathf.Round(monW / 2f * 1000f) / 1000f;
                string gpath = EdoAssets.Own.NagayaOmoteMon(Mathf.Round(monW * 1000f) / 1000f, gc, nikai);
                if (AssetDatabase.LoadAssetAtPath<GameObject>(gpath) == null)
                {
                    miss++;
                    wait.Add("表門: 部材が無い " + gpath + " → build_nagaya_omote.py -- "
                           + monW.ToString("0.###") + " --gate " + gc.ToString("0.###") + " …"
                           + (nikai ? " --floors 2" : ""));
                }
                else
                {
                    // ⚠ 門のピボットの高さは**敷居**(`gate.sill`)。⛔ 面から起こさない
                    float sill = Has(g, "sill") ? F(g["sill"]) : 0f;
                    if (PlaceNagayaPiece(kak, "Omotemon", gpath, (int)F(g["edge"]), F(g["s"]),
                                         sill, monW, wait, ref lastH)) made++;
                }
                if (Has(g, "asset") && S(g["asset"]).StartsWith("要選定"))
                    wait.Add("表門: 指図の `gate.asset` が「要選定」のまま — 裁定12=A で "
                           + "`Own.NagayaOmoteMon(" + monW.ToString("0.###") + ", " + gc.ToString("0.###")
                           + ", 二階)` に決まっているので、指図方が書き換えること");
            }
        }

        // 棟高の突き合わせ(指図 ⇔ **据えた現物**)。⛔ 呼び寸法や doc の数字で比べない
        if (Has(O(D["const"]), "nagayaH") && nagH > 0.1f)
        {
            float want = C("nagayaH");
            if (Mathf.Abs(nagH - want) > 0.15f)
                wait.Add("表長屋の棟高: 指図 const.nagayaH " + want.ToString("0.###")
                       + "m / 据えた**表長屋**の実丈 " + nagH.ToString("0.###") + "m");
            else sb.Append("(棟高 " + nagH.ToString("0.###") + "m ✔)");
        }
        // 表門の棟高は別に見る(指図 gate.plan.monH)
        {
            var gp2 = O(Get(O(Get(D, "gate")), "plan"));
            if (gp2 != null && Has(gp2, "monH") && lastH > 0.1f && Mathf.Abs(lastH - F(gp2["monH"])) > 0.15f)
                wait.Add("表門の棟高: 指図 gate.plan.monH " + F(gp2["monH"]).ToString("0.###")
                       + "m / 据えた現物の実丈 " + lastH.ToString("0.###") + "m");
        }
        sb.Append("表長屋・表門: " + made + " 棟" + (nikai ? "(二階)" : "(平屋)")
                + (miss > 0 ? " / 部材の無いもの " + miss : ""));
        return sb.ToString();
    }

    /// <summary>長屋の一本物を据える。ピボット = 走りの中心・土台の底・**壁の外面**。
    /// ⭕ 据えた実メッシュで**走り方向の実長**を測り、呼び寸法と食い違えば鳴らす。</summary>
    /// <summary>据えた長屋の**実メッシュ**が辺の上で占める区間[m](s)。
    /// 隅の返し(短い練塀)はここへ突き付けるので、⛔ 呼び寸法で継がない。</summary>
    static Dictionary<string, Vector2> _nagayaSpan = new Dictionary<string, Vector2>();

    static bool PlaceNagayaPiece(Transform kak, string name, string path, int edge, float sMid,
                                 float seat, float call, List<string> wait, ref float lastH)
    {
        Vector2 outw = OutNormal(edge);
        float psi = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;      // 見え面 +Z を外へ
        Vector2 p = EdgePt(edge, sMid) - outw * INUBASHIRI;           // 壁の外面 → 犬走りぶん内へ
        var go = EdoBuild.Place(path, new Vector3(p.x, seat, p.y), psi, Vector3.one, kak, name);
        if (go == null) return false;
        EdoBuild.SeatBottom(go, seat - 0.10f);

        // ⛔⛔ **走り方向の長さを world の AABB から出さない。**
        //   `|size.x·ux| + |size.z·uz|` は、長さ Lp・奥行 D の箱を yaw で回すと
        //   **Lp + 2·D·|ux·uz|** になり、**奥行が長さに混ざる**。辺12(世界軸から 5.71° 振れ)
        //   では長屋の奥行 4.35m が +0.862m の水増しになり、⚠ **長さに依らない項なので
        //   3棟が揃って同じ差**を出した(2026-09-04。部材は指図どおりで、測り方が誤っていた)。
        //   ⭕ **部材のローカル軸で測る**(OBB)。ローカル +X が走り。
        float mnx, mxx, mnz, mxz, mny;
        EdoBuild.ObbFootprint(go.transform, out mnx, out mxx, out mnz, out mxz, out mny);
        float realLen = mxx - mnx;
        var bb = EdoBuild.RB(go);
        lastH = bb.size.y;
        // ローカル +X が s の増える向きか減る向きかを、実際のベクトルで見る(⛔ 式で決めない)
        Vector3 dirXw = go.transform.rotation * Vector3.right;
        Vector2 edgeDir = (EdgePt(edge, sMid + 1f) - EdgePt(edge, sMid)).normalized;
        float sSign = (dirXw.x * edgeDir.x + dirXw.z * edgeDir.y) >= 0f ? 1f : -1f;
        float sA = sMid + sSign * mnx, sB = sMid + sSign * mxx;
        _nagayaSpan[name] = new Vector2(Mathf.Min(sA, sB), Mathf.Max(sA, sB));
        if (Mathf.Abs(realLen - call) > 0.10f)
            wait.Add("長屋 " + name + ": 部材の実長(OBB)" + realLen.ToString("F3")
                   + "m が呼び " + call.ToString("0.###") + "m と食い違う"
                   + "(⚠ 呼び寸法は**破風まで含む全幅**で、隣と突き付く)");
        return true;
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

    // ---------------------------------------------------------------- 通用口(小門)
    /// <summary>袋小路へ開く通用口。指図 `komon[]` の **辺・走り s・門口の幅 w・敷居 sill** が正典。
    ///
    /// 【据え】部材のピボットは**門の芯・敷居レベル**なので `sill` をそのまま y に使える
    /// (⛔ 地盤から起こさない — 敷居は設計値で、地形の擦り付けの途中に落ちることがある)。
    /// ローカル **+Z = 外**(袋小路の側)なので yaw は外向き法線の方位。
    ///
    /// ⚠ **面は据えてから実メッシュで測って寄せる**(CLAUDE.md 規則5 / 2026-08-29 EDO-0053:
    ///   門が塀の面から飛び出していると、門が壁の一部でなく前に置いた飾りに見える)。
    ///   目標は囲いと同じ「区画線から内へ `inubashiri`」。⛔ 部材の呼び寸法で置かない。</summary>
    static string PlaceKomon()
    {
        var grp = Group("Mon"); Clear(grp);
        var sb = new System.Text.StringBuilder();
        int made = 0;
        foreach (var o in A(Get(D, "komon")) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue;
            string nm = S(k["name"]);
            int e = (int)F(k["edge"]);
            float sPos = F(k["s"]), w = F(k["w"]);
            if (!Has(k, "sill")) { sb.AppendLine("★ 小門 " + nm + ": 指図に sill が無い"); continue; }
            float sill = F(k["sill"]);
            string path = AssetByKey(Has(k, "asset") ? S(k["asset"]) : "Munamon", w, 0f);
            if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { sb.AppendLine("★ 小門 " + nm + "(" + S(k["kind"]) + " 門口 " + w.ToString("0.##")
                          + "m): 部材が無い " + (path ?? "(asset の指定なし)")); continue; }
            Vector2 nrm = OutNormal(e);
            Vector2 c = EdgePt(e, sPos);
            float yaw = Mathf.Atan2(nrm.x, nrm.y) * Mathf.Rad2Deg;      // ローカル +Z を外へ
            var go = EdoBuild.Place(path, new Vector3(c.x, sill, c.y), yaw, Vector3.one, grp, nm);
            if (go == null) { sb.AppendLine("★ 小門 " + nm + ": 据えられない " + path); continue; }
            // 走りの方向の芯を開口の芯へ合わせ、外面を犬走りの位置へ寄せる
            float face = FaceOut(go, e);
            if (face != float.MinValue)
            {
                float shift = -INUBASHIRI - face;
                go.transform.position += new Vector3(nrm.x * shift, 0f, nrm.y * shift);
                sb.AppendLine("小門 " + nm + ": 外面 " + face.ToString("+0.00;-0.00") + " → "
                            + (-INUBASHIRI).ToString("F2") + "m(寄せ " + shift.ToString("+0.00;-0.00") + ")");
            }
            made++;
        }
        sb.Append("通用口: " + made + " 基");
        return sb.ToString();
    }

    /// <summary>据えた現物の**外面**(辺 e の区画線から外向きへの最大の張り出し[m])。
    /// ⛔ 呼び寸法や bbox の半分で代用しない — 部材を差し替えた瞬間に壊れる。</summary>
    static float FaceOut(GameObject go, int e)
    {
        var P = Poly; var a = P[e % P.Length]; Vector2 nrm = OutNormal(e);
        float best = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var m = mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            for (int q = 0; q < vs.Length; q++)
            {
                var w = m.MultiplyPoint3x4(vs[q]);
                best = Mathf.Max(best, (w.x - a.x) * nrm.x + (w.z - a.y) * nrm.y);
            }
        }
        return best;
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
        // 柵に開く口(指図が持つものだけ。実装で発明しない)。⭕ **潜りの戸を先に据えて実寸を測り**、
        // その幅で柵を空ける(⛔ 開口の呼び寸法で空けない — 戸の柱のぶん柵が食い込む)
        var gaps = new List<float[]>();     // {edge, s0, s1}
        var saku = O(Get(O(Get(D, "nishi")), "saku"));
        int kuguri = 0;
        if (saku != null)
        {
            var k = O(Get(saku, "kuguri")) ?? O(Get(saku, "kido"));
            if (k != null)
            {
                int e0 = (int)F(saku["edge"]);
                float s = F(k["s"]), w = F(k["w"]);
                Vector2 c0 = EdgePt(e0, s);
                Vector2 ow = OutNormal(e0);
                float psi0 = Mathf.Atan2(ow.x, ow.y) * Mathf.Rad2Deg;   // +Z = 見え面(外)
                string kp = AssetByKey(Has(k, "asset") ? S(k["asset"]) : "Own.HoriKido", w, 0f);
                float openW = w;
                if (kp != null && AssetDatabase.LoadAssetAtPath<GameObject>(kp) != null)
                {
                    var gk = Group("Fences");
                    float gy = Graded.At(c0.x, c0.y); if (float.IsNaN(gy)) gy = EdoBuild.Ground(c0.x, c0.y);
                    // ⚠ ピボット = 開口の芯・地盤レベル(底は −0.140 で沓石が地盤より下へ出る)
                    var go0 = EdoBuild.Place(kp, new Vector3(c0.x, gy, c0.y), psi0, Vector3.one,
                                             gk, "Kuguri");
                    if (go0 != null)
                    {
                        kuguri++;
                        float kw2, kd2; ObbWD(go0, out kw2, out kd2);   // ⭕ OBB(ローカル +X = 走り)
                        openW = kw2;
                    }
                }
                gaps.Add(new float[] { e0, s - openW / 2f, s + openW / 2f });
            }
        }
        int posts = 0, runs = 0; float wMeasured = 0f;
        foreach (var o in A(D["fences"]) ?? new List<object>())
        {
            var fd = O(o); if (fd == null) continue;
            int e = (int)F(fd["edge"]);
            float s0 = F(fd["s0"]), s1 = F(fd["s1"]);
            Vector2 outw = OutNormal(e);
            float psi = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;
            // ⭕ **汀の木柵は専用の部材**(2026-09-04 部材方)。⛔ 在庫の `Eg.Hogaki5` は実丈 0.79m で、
            //   指図の `const.fenceH` 1.40 に 0.6m 足りない(見透しの遮蔽の計算が天端=地盤+1.40 を前提)。
            string fpath = AssetByKey(Has(fd, "asset") ? S(fd["asset"]) : "Own.HoriSaku");
            if (fpath == null) fpath = EdoAssets.Own.HoriSaku;
            float w = MeasureRunWidth(fpath, fen, psi);
            if (w <= 0f) { sb.AppendLine("★ 柵の部材が無い: " + fpath); continue; }
            wMeasured = w;
            // ⛔ **重ねない。**bbox がちょうど1間なので 1.818 ちょうどで突き付ける
            //   (重ねると南京下見の板が z-fighting する — 部材方の申し送り)。
            //   ⚠ 潜りの口で切れた区間ごとに割り付け、**各区間の +X 端に端の杭を1本**足す。
            var segsF = new List<float[]>();
            {
                var cuts = new List<float[]>();
                foreach (var g in gaps) if ((int)g[0] == e) cuts.Add(new float[] { g[1], g[2] });
                cuts.Sort(delegate(float[] x, float[] y) { return x[0].CompareTo(y[0]); });
                float cur = s0;
                foreach (var c2 in cuts)
                { if (c2[0] > cur) segsF.Add(new float[] { cur, Mathf.Min(c2[0], s1) }); cur = Mathf.Max(cur, c2[1]); }
                if (cur < s1) segsF.Add(new float[] { cur, s1 });
            }
            foreach (var sg in segsF)
            {
                float segL = sg[1] - sg[0];
                if (segL < w * 0.5f) continue;
                int nF = Mathf.Max(1, Mathf.RoundToInt(segL / w));
                float pitch = segL / nF;                      // 端数は区間の中で均す(⛔ 重ねない)
                for (int q = 0; q < nF; q++)
                {
                    float sPos = sg[0] + pitch * (q + 0.5f);
                    Vector2 p = EdgePt(e, sPos);
                    float gy = Graded.At(p.x, p.y); if (float.IsNaN(gy)) gy = EdoBuild.Ground(p.x, p.y);
                    // ⛔ **SeatBottom で据えない** — 根入れ 0.12 のぶん浮く。`position.y = 地盤` を直に
                    var go = EdoBuild.Place(fpath, new Vector3(p.x, gy, p.y), psi, Vector3.one,
                                            fen, S(fd["name"]) + "_" + posts);
                    if (go != null) posts++;
                }
                // ⛔ run の +X 端に端の杭を1本(足さないと最後の板が宙で終わる)
                {
                    Vector2 pe = EdgePt(e, sg[1]);
                    float gy = Graded.At(pe.x, pe.y); if (float.IsNaN(gy)) gy = EdoBuild.Ground(pe.x, pe.y);
                    var gp2 = EdoBuild.Place(EdoAssets.Own.HoriSakuPost, new Vector3(pe.x, gy, pe.y),
                                             psi, Vector3.one, fen, S(fd["name"]) + "_Post" + posts);
                    if (gp2 != null) posts++;
                }
            }
            runs++;
        }
        sb.Append("木柵: " + posts + " 枚 / " + runs + " run(駒の実寸 " + wMeasured.ToString("F3") + "m)");
        if (gaps.Count > 0) sb.Append(" ｜ 潜りの口 " + gaps.Count + " 箇所(戸 " + kuguri + " 枚)");
        // 指図の柵の丈と**据えた現物の天端**を突き合わせる。
        // ⚠ 天端は **pivot(地盤)+ fenceH** に来るべき。⛔ bbox の高さで比べない —
        //   根入れ(底 −0.12)を含むので 1.52 と出て、指図の 1.40 と必ず食い違う。
        if (Has(O(D["const"]), "fenceH") && fen.childCount > 0)
        {
            float want = C("fenceH");
            float topMax = float.MinValue, baseY = 0f;
            var c0 = fen.GetChild(0);
            baseY = c0.position.y;
            foreach (var mf in c0.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                var m3 = mf.transform.localToWorldMatrix;
                var vs3 = mf.sharedMesh.vertices;
                for (int q3 = 0; q3 < vs3.Length; q3++)
                    topMax = Mathf.Max(topMax, m3.MultiplyPoint3x4(vs3[q3]).y);
            }
            if (topMax != float.MinValue)
            {
                float got = topMax - baseY;
                sb.Append("\n  柵の天端: 地盤+" + got.ToString("F3") + "m(指図 const.fenceH "
                        + want.ToString("0.##") + "m)" + (Mathf.Abs(got - want) > 0.05f ? " ★" : " ✔"));
            }
        }
        return sb.ToString();
    }

    /// <summary>部材を1枚置いて**走り方向の実寸**を測り、すぐ捨てる。
    /// ⛔ 決め打ちの定数に戻さない — 部材を差し替えた瞬間に穴が開く。</summary>
    static float MeasureRunWidth(string path, Transform parent, float psi)
    {
        var probe = EdoBuild.Place(path, new Vector3(0, -9999f, 0), psi, Vector3.one, parent, "__probe");
        if (probe == null) return 0f;
        float pw, pd; ObbWD(probe, out pw, out pd);      // ⭕ OBB。⛔ 回した AABB の max ではない
        UnityEngine.Object.DestroyImmediate(probe);
        return pw;
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
        float resid = 0f; string residName = null;
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
            // ⭐ **寄せた後にもう一度測る**(残差)。⛔ 「寄せ量」を残差と読み違えない —
            //   寄せ量が大きいのは元が外れていただけで、直ったかどうかは残差でしか分からない。
            float after = float.MinValue;
            foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null || !WallFace.Contains(mf.gameObject.name)) continue;
                var m2 = mf.transform.localToWorldMatrix;
                var vs2 = mf.sharedMesh.vertices;
                for (int q2 = 0; q2 < vs2.Length; q2++)
                {
                    var w2 = m2.MultiplyPoint3x4(vs2[q2]);
                    after = Mathf.Max(after, (w2.x - a.x) * nrm.x + (w2.z - a.y) * nrm.y);
                }
            }
            if (after != float.MinValue)
            { float rr = Mathf.Abs(after - target); if (rr > resid) { resid = rr; residName = c.name; } }
        }
        return "犬走りへ寄せた: " + moved + " / " + seen + " 駒(最大の寄せ "
             + worst.ToString("+0.00;-0.00") + "m @" + (worstName ?? "-") + " ・目標 "
             + target.ToString("F2") + "m)｜**寄せた後の残差 最大 " + resid.ToString("F3")
             + "m @" + (residName ?? "-") + "** " + (resid > 0.02f ? "★" : "✔");
    }

    // =====================================================================
    // Stage3 — 主郭(棟・渡廊下・附属屋・井戸・結界・石段・参道)
    //
    // 【この Stage の姿勢】⛔ **指図に無い値は発明しない。**据えられない物は据えず、
    //   「何の欄が足りないのか」「どの部材を焼けばよいのか」を**一覧にして返す**。
    //   ⚠ 黙って既定値で埋めると、指図方は自分の書き起こし漏れに気づけない。
    //
    // 【いま据わるもの】御殿の棟(骨組み)と渡廊下 — 部材キット `EdoGotenKit` が
    //   一間の柱割りで組む。⚠ 屋根は**棟の寸法ごとに Blender で焼く**もので、
    //   当邸の 7棟はどれも在庫に無い(骨組みだけ組んで、焼くコマンドを一覧に出す)。
    //
    // 【据わらないもの】附属屋・井戸・結界塀・石段 — いずれも**指図が部材を名指ししていない**
    //   か、**据えるのに要る欄が無い**。⛔ 在庫から見繕って据えるのは部材方・在庫方の判断で、
    //   棟梁が代わりに決めてよいものではない(CLAUDE.md 規則17)。
    // =====================================================================

    /// <summary>ローカル +X を **+u** へ向ける yaw。あわせて +Z が +v を向く。</summary>
    public static float YawU()
    { var f = Grid; return Mathf.Atan2(f.vx, f.vz) * Mathf.Rad2Deg; }
    /// <summary>ローカル +X を **+v** へ向ける yaw。あわせて +Z が −u を向く。</summary>
    public static float YawV()
    { var f = Grid; return Mathf.Atan2(-f.vz, f.vx) * Mathf.Rad2Deg; }

    /// <summary>棟・廊下の**据え付けピボット**(グリッド座標)。
    ///
    /// ⚠ 部材キットの原点は「外形の角・走りが +X」。当邸のフレームは u+ が北・v+ が西で、
    ///   松江松平とは**手前が逆**なので、松平式の (u0,v1) を当てると全棟がずれる。
    ///   ⭐ **大棟は長いほうへ架ける**(建築の一般則。⛔ 指図は棟の桁行の向きを持っていない
    ///   ので、そこは書き起こし漏れとして返してある)。
    ///   ・長辺が u … +X→+u、角は (u0, v0)
    ///   ・長辺が v … +X→+v、角は (u1, v0)</summary>
    public static bool AlongU(float du, float dv) { return du >= dv; }
    public static Vector2 PivotUV(float u0, float v0, float u1, float v1)
    { return AlongU(u1 - u0, v1 - v0) ? new Vector2(u0, v0) : new Vector2(u1, v0); }
    /// <summary>突き合わせが読む据え付け点(世界座標)。⛔ 実装と検査で式を二重に持たない。</summary>
    public static Vector2 Pivot(Dictionary<string, object> o, string kind)
    {
        float u0 = F(Get(o, "u0")), v0 = F(Get(o, "v0")), u1 = F(Get(o, "u1")), v1 = F(Get(o, "v1"));
        var g = PivotUV(u0, v0, u1, v1);
        return Grid.W(g.x, g.y);
    }

    [MenuItem("Edo/岡部筑前守上屋敷/3 主郭(棟・廊下・附属屋・井戸・結界・石段)")]
    public static void Stage3Menu() { Debug.Log("[Okabe] " + Stage3_Shukaku()); }

    public static string Stage3_Shukaku()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder();
        var wait = new List<string>();          // 部材待ち・欄待ち(据えなかったもの)
        sb.AppendLine(PlaceMunes(wait));
        sb.AppendLine(PlaceLinks(wait));
        sb.AppendLine(PlaceService(wait));
        sb.AppendLine(PlaceWells(wait));
        sb.AppendLine(PlaceKekkai(wait));
        sb.AppendLine(PlaceKaidans(wait));
        sb.AppendLine(PlaceSando(wait));
        sb.AppendLine("── 据えなかったもの(部材待ち・欄待ち)" + wait.Count + " 件 ──");
        foreach (var w in wait) sb.AppendLine("  ★ " + w);
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 棟
    /// <summary>御殿の棟。**部材キットで一間の柱割りから組む**(Village Kit の一軒家プレハブでは
    /// 入側から壁が見えて御殿にならない — 2026-08-14 ユーザー裁定)。
    ///
    /// 指図が持つようになった欄を**そのまま読む**(⛔ 推測で埋めない):
    ///   `ridge` … **大棟の向き**("u"/"v")。部材キットのローカル +X をこの向きへ向ける。
    ///             ⚠ 正方の玄関棟は「長いほうへ架ける」では決まらないので指図が決めている。
    ///   `iri`   … 入側の間数。`iriX` は**例外の辺**(入側を回さない辺の名)で、空なら四方。
    ///   `roof`  … `roofs` のキー。屋根の呼び寸法は**指図の (wKen, dKen) をそのまま渡す**
    ///             (⛔ 長辺・短辺を実装で入れ替えない。指図が長辺先で書いている)。
    /// ⚠ **屋根の外形は間数より 2.14m 大きい**(軒の出 0.90 が四周)。棟の壁面で合わせない。</summary>
    static string PlaceMunes(List<string> wait)
    {
        var grp = Group("Buildings"); Clear(grp);
        var f = Grid;
        float floor = C("gotenFloor");
        var roofs = O(Get(D, "roofs"));
        var sb0 = new System.Text.StringBuilder();
        int made = 0, noRoof = 0, held = 0;
        foreach (var o in A(D["munes"]) ?? new List<object>())
        {
            var m = O(o); if (m == null) continue;
            string nm = S(m["name"]);
            float u0 = F(m["u0"]), v0 = F(m["v0"]), u1 = F(m["u1"]), v1 = F(m["v1"]);
            var rf = roofs != null && Has(m, "roof") ? O(Get(roofs, S(m["roof"]))) : null;

            // ⛔ 裁定待ちのものは**式は書くが据えない**
            if (HeldForRuling.Contains(nm))
            {
                var gh = PivotUV(u0, v0, u1, v1); var ph = f.W(gh.x, gh.y);
                wait.Add("棟 " + nm + " は**据えない(裁定待ち)** — 部材 "
                       + (rf != null && Has(rf, "asset") ? S(rf["asset"]) : "?")
                       + " は焼けており、据え位置は世界(" + ph.x.ToString("F1") + ", " + ph.y.ToString("F1")
                       + ")・面 " + F(m["y"]).ToString("0.##")
                       + "。⚠ 車寄の棟天端 4.34 が玄関棟の軒先(地盤+3.20)より 1.14m 高く、"
                       + "背面の屋根が玄関棟の屋根面へ食い込む。姿を決めるのは普請奉行");
                held++; continue;
            }

            // ---- 部材そのもので建つ棟(車寄)。⭕ 2026-09-04 裁定10=A
            //   入母屋を架けない別種なので部材キットでは組めない。`roofs[].asset` が部材を名指しする。
            //   ⚠ **玄関棟の屋根面へ差し込む**ので、その面より内側を切り欠いて据える。
            //   ⛔ 切り欠きの線は**指図 其十九 の食い込みの線**が正典 — 実装で決めない。
            if (rf != null && Has(rf, "asset") && !Has(m, "ridge"))
            {
                string kp = AssetByKey(S(rf["asset"]), u1 - u0, v1 - v0);
                if (kp == null || AssetDatabase.LoadAssetAtPath<GameObject>(kp) == null)
                { wait.Add("棟 " + nm + ": 部材が引けない " + S(rf["asset"])); continue; }
                float xu2, xv2; string nt2;
                OrientOf(S(rf["asset"]), u1 - u0, v1 - v0, out xu2, out xv2, out nt2);
                Vector2 cc2 = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
                var gk2 = EdoBuild.Place(kp, new Vector3(cc2.x, F(m["y"]), cc2.y),
                                         YawTo(xu2, xv2), Vector3.one, grp, nm);
                if (gk2 == null) { wait.Add("棟 " + nm + ": 据えられない " + kp); continue; }
                var bb2 = EdoBuild.RB(gk2);
                gk2.transform.position += new Vector3(cc2.x - bb2.center.x, F(m["y"]) - bb2.min.y,
                                                      cc2.y - bb2.center.z);
                sb0.Append(KirikakiCheck(gk2, m, rf, wait));
                made++; continue;
            }

            // 大棟の向き。⛔ 指図が持たないときは推測しない
            string ridge = Has(m, "ridge") ? S(m["ridge"]) : null;
            if (ridge != "u" && ridge != "v")
            { wait.Add("棟 " + nm + ": 指図 munes[].ridge(大棟の向き)が \"u\"/\"v\" でない — 据えない"); continue; }
            bool alongU = ridge == "u";
            int W = Mathf.RoundToInt(alongU ? (u1 - u0) : (v1 - v0));   // 桁行(大棟の走る側)
            int Dd = Mathf.RoundToInt(alongU ? (v1 - v0) : (u1 - u0));  // 梁間

            // 入側 — `iriX` は例外の辺の名。両側とも例外なら その軸は 0
            int iri = Has(m, "iri") ? (int)F(m["iri"]) : 0;
            var exc = new HashSet<string>();
            foreach (var q in A(Get(m, "iriX")) ?? new List<object>())
            { var nmx = q as string; if (nmx != null) exc.Add(nmx); }
            string xa = alongU ? "u" : "v", za = alongU ? "v" : "u";
            int iriX = (exc.Contains(xa + "0") && exc.Contains(xa + "1")) ? 0 : iri;  // ±X(桁行の妻側)
            int iriZ = (exc.Contains(za + "0") && exc.Contains(za + "1")) ? 0 : iri;  // ±Z(梁間の平側)
            int nx = W - 2 * iriX, nz = Dd - 2 * iriZ;
            if (nx < 1 || nz < 1)
            { wait.Add("棟 " + nm + " は身舎が残らない(外形 " + W + "×" + Dd + "間 − 入側)— 別部材が要る"); continue; }

            // 屋根 — ⭕ 指図の呼び寸法をそのまま渡す
            string roof = null;
            if (rf != null && Has(rf, "asset")) roof = AssetByKey(S(rf["asset"]));
            else if (rf != null && Has(rf, "wKen"))
                roof = EdoAssets.Own.GotenRoofIrimoya((int)F(rf["wKen"]), (int)F(rf["dKen"]));
            if (roof != null && AssetDatabase.LoadAssetAtPath<GameObject>(roof) == null)
            {
                wait.Add("棟 " + nm + " の屋根が無い → blender --background --python "
                       + "Tools/Blender/build_goten_roof.py -- " + (W * C("ken")).ToString("0.###")
                       + " " + (Dd * C("ken")).ToString("0.###")
                       + " Goten_Roof_Irimoya_" + W + "x" + Dd + "ken");
                roof = null; noRoof++;
            }

            var g = PivotUV(u0, v0, u1, v1);
            Vector2 p = f.W(g.x, g.y);
            float yaw = alongU ? YawU() : YawV();
            var go = EdoGotenKit.Mune(nm, grp, new Vector3(p.x, F(m["y"]), p.y), yaw,
                                      nx, nz, iriZ, floor, roof, true, true, null, null, -1, iriX);
            if (go != null) made++;
        }
        return "棟: " + made + " 棟(屋根待ち " + noRoof + " / 裁定待ちで据えず " + held + ")" + sb0;
    }

    /// <summary>**車寄の切り欠き**(2026-09-04 裁定10=A)。指図の規則は一つ —
    /// 「玄関棟の**軒先の線**より奥(v ≧ `atV`)で、**面から** `aboveY` より上にある車寄の面を切る」。
    /// ⛔ 玄関棟の屋根は切らない(親側は無傷)。
    ///
    /// ⚠ **メッシュを実行時に切らない。**切り欠きは矩形の抜き(二つの半空間の積を除く)で、
    /// 平面1枚のクリップでは表せず、三角形を割り直す必要がある。⛔ 重心で三角形を捨てる近似は
    /// 縁がぎざぎざになって瓦が欠ける。⭕ **切り欠き済みの部材を部材方に焼いてもらう**のが筋なので、
    /// ここでは**据えた現物を測って、どれだけ食い込んでいるかを数字で出す**にとどめる。</summary>
    static string KirikakiCheck(GameObject go, Dictionary<string, object> m,
                                Dictionary<string, object> rf, List<string> wait)
    {
        var sk = O(Get(rf, "sashikomi"));
        var kk = sk == null ? null : O(Get(sk, "kirikaki"));
        if (kk == null)
        { wait.Add("棟 " + S(m["name"]) + ": 切り欠きの線が指図に無い(裁定10=A)"); return ""; }
        float atV = F(kk["atV"]), aboveY = F(kk["aboveY"]), face = F(m["y"]);
        var f = Grid;
        int n = 0; float maxAbove = 0f, maxV = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var mtx = mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            for (int i = 0; i < vs.Length; i++)
            {
                var w = mtx.MultiplyPoint3x4(vs[i]);
                var uv = f.L(new Vector2(w.x, w.z));
                if (uv.y < atV) continue;                      // 軒先の線より手前は切らない
                float above = (w.y - face) - aboveY;
                if (above <= 0f) continue;                     // 軒先の高さより下は切らない
                n++; maxAbove = Mathf.Max(maxAbove, above); maxV = Mathf.Max(maxV, uv.y);
            }
        }
        if (n == 0) return " / 車寄の切り欠き: 不要(食い込み 0)";
        wait.Add("車寄の切り欠き: **未実施** — 玄関棟の軒先の線(v≧" + atV.ToString("0.##")
               + ")より奥で、面+" + aboveY.ToString("0.###") + "m より上に車寄の頂点が " + n
               + " 点ある(最大 " + maxAbove.ToString("F2") + "m 上・v 最大 " + maxV.ToString("F2") + ")。"
               + "⛔ 実行時にメッシュを割り直さない(縁がぎざぎざになって瓦が欠ける) — "
               + "部材方へ**切り欠き済みの版**を依頼すること(規則: atV / aboveY / cutFrom=車寄・玄関棟は切らない)");
        return " / 車寄の食い込み " + n + " 点";
    }

    // ---------------------------------------------------------------- 渡廊下・御錠口
    /// <summary>渡廊下は**幅一間**(指図 `_links`)で部材キットが組む。
    /// 御錠口は専用の部材(3間角)で、指図の `asset` が名指しする。
    /// ⛔ 両端は棟の壁面へ突き付ける(離すと取り合いに隙間が出る)。</summary>
    static string PlaceLinks(List<string> wait)
    {
        var grp = Group("Buildings");
        var f = Grid;
        float floor = C("gotenFloor");
        int made = 0, held = 0;
        foreach (var o in A(D["links"]) ?? new List<object>())
        {
            var l = O(o); if (l == null) continue;
            string nm = S(l["name"]);
            float u0 = F(l["u0"]), v0 = F(l["v0"]), u1 = F(l["u1"]), v1 = F(l["v1"]);
            float du = u1 - u0, dv = v1 - v0;
            bool alongU = AlongU(du, dv);
            var g = PivotUV(u0, v0, u1, v1);
            Vector2 p = f.W(g.x, g.y);
            float yaw = alongU ? YawU() : YawV();

            // ⛔ 裁定待ちのものは**式は書くが据えない**
            if (HeldForRuling.Contains(nm))
            {
                Vector2 cc = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
                wait.Add("廊下 " + nm + "(" + S(l["kind"]) + ")は**据えない(裁定待ち)** — 部材 "
                       + (Has(l, "asset") ? S(l["asset"]) : "?") + " は焼けており、据えは"
                       + "**足跡の中心**(世界 " + cc.x.ToString("F1") + ", " + cc.y.ToString("F1")
                       + ")・**床レベル**(面 " + F(l["y"]).ToString("0.##") + " + gotenFloor "
                       + floor.ToString("0.##") + " = " + (F(l["y"]) + floor).ToString("0.##")
                       + ")・ローカル +X = 廊下の通る向き。⚠ 入母屋の棟天端が床+5.24 で"
                       + "渡廊下の大棟(床+2.503)より 2.7m 高い。姿を決めるのは普請奉行");
                held++; continue;
            }

            // ⭕ **2026-09-04 裁定11=B: 御錠口は廊下幅一間の建具。**`Own.Jouguchi`(3間角)は使わない。
            //    指図は `asset` に "EdoGotenKit.Roka + EdoAssets.Goten.Fusuma" と書くので、
            //    **Roka を名指すものは下の渡廊下の枝で通し**、Fusuma を名指すなら錠口の戸を建て込む。
            string akey = Has(l, "asset") ? S(l["asset"]) : null;
            bool wantFusuma = akey != null && akey.Contains("Fusuma");
            if (akey != null && akey.EndsWith("Jouguchi"))
            {
                wait.Add("御錠口 " + nm + ": 指図がまだ `Own.Jouguchi`(3間角)を指している — "
                       + "裁定11=B は**廊下幅一間の建具**なので使わない。指図方が書き換えるまで据えない");
                held++; continue;
            }
            if (akey != null && !akey.Contains("Roka"))
            {
                string path = AssetByKey(akey, Mathf.Max(du, dv), Mathf.Min(du, dv));
                if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
                { wait.Add("廊下 " + nm + ": 部材が引けない " + akey); continue; }
                Vector2 c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
                var go2 = EdoBuild.Place(path, new Vector3(c.x, F(l["y"]) + floor, c.y), yaw,
                                         Vector3.one, grp, nm);
                if (go2 != null) made++;
                continue;
            }

            float wide = alongU ? dv : du, runK = alongU ? du : dv;
            if (Mathf.Abs(wide - 1f) > 0.01f)
            { wait.Add("廊下 " + nm + "(" + S(l["kind"]) + ")は幅 " + wide.ToString("0.##")
                     + "間で一間ではない — 渡廊下の部材では組めない。部材か寸法の指定が要る"); continue; }
            int nx = Mathf.RoundToInt(runK);
            if (nx < 1) { wait.Add("廊下 " + nm + " の走りが 0 間"); continue; }
            // ⛔ 両端の柱は棟の柱と重なるので立てない(z-fighting)
            var go = EdoGotenKit.Roka(nm, grp, new Vector3(p.x, F(l["y"]), p.y), yaw, nx,
                                      floor, true, true, true, false, false);
            if (go == null) continue;
            made++;
            // ⭕ 錠口の戸 — 廊下の断面を塞ぐ在庫の建具(裁定11=B「錠口の建具は在庫の戸」)。
            //   ⚠ 廊下のローカルは +X = 走り / +Z = 幅一間。戸は幅を跨ぐので **Y まわり 90°**。
            if (wantFusuma)
            {
                float K = EdoAssets.Goten.Ken;
                var src = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Goten.Fusuma);
                if (src == null) wait.Add("御錠口 " + nm + ": 建具が無い " + EdoAssets.Goten.Fusuma);
                else
                {
                    var fs = (GameObject)PrefabUtility.InstantiatePrefab(src, go.transform);
                    Undo.RegisterCreatedObjectUndo(fs, "jouguchi");
                    fs.name = nm + "_Tobira";
                    fs.transform.localPosition = new Vector3(0f, floor, K * 0.5f);
                    fs.transform.localRotation = Quaternion.Euler(0f, 90f, 0f);
                }
            }
        }
        return "渡廊下: " + made + " 本(裁定待ちで据えず " + held + ")";
    }

    // ---------------------------------------------------------------- 附属屋・井戸
    /// <summary>指図が名指しした部材のキーを `EdoAssets` の実体へ解く。
    /// ⛔ **ここに無いキーを推測で足さない。**部材の選定は在庫方・部材方の仕事で、
    ///   棟梁が「たぶんこれだろう」で当てると、指図に書かれていない意匠が既成事実になる。</summary>
    static string AssetByKey(string key) { return AssetByKey(key, 0f, 0f); }

    /// <summary>指図の `asset` を `EdoAssets` の実体へ解く。
    ///
    /// 【書式】指図は **`Own.Umaya` / `Own.Matsudaira.Dozo` / `Own.NagayaOmote(21.816)` /
    /// `Own.RoofIrimoya_(11,11)`** の形で書く。族(`Own.` など)は落とし、**最後の名**で引く。
    /// 括弧の中は呼び寸法で、⭕ **指図の値をそのまま渡す**(⛔ 入れ替えない・丸めない)。
    ///
    /// 【寸法が指図に無いとき】`wKen`/`dKen` に**足跡から出した長辺・短辺[間]**が入る。
    /// ⛔ 部材の名前に寸法を書き写さない — 足跡を動かした瞬間に別の部材を引く。
    ///
    /// ⚠ **単位に注意**: `NagayaOmote` の引数は **m**、`ObiNagaya` の引数は **間**。
    ///   指図が `Own.ObiNagaya(13.635)`(=7.5間を m で書いた)と書いているので、
    ///   ObiNagaya だけは括弧の値を使わず**足跡の間数**で引く(単位の食い違いは一覧へ出す)。</summary>
    static string AssetByKey(string key, float wKen, float dKen)
    {
        if (string.IsNullOrEmpty(key)) return null;
        // 括弧の中(呼び寸法)を取り出す
        var args = new List<float>();
        string head = key;
        int lp = key.IndexOf('(');
        if (lp >= 0)
        {
            int rp = key.LastIndexOf(')');
            head = key.Substring(0, lp);
            string inner = key.Substring(lp + 1, Mathf.Max(0, (rp < 0 ? key.Length : rp) - lp - 1));
            foreach (var t in inner.Split(','))
            {
                float v;
                if (float.TryParse(t.Trim(), System.Globalization.NumberStyles.Float,
                                   System.Globalization.CultureInfo.InvariantCulture, out v)) args.Add(v);
            }
        }
        int dot = head.LastIndexOf('.');
        string k = dot >= 0 ? head.Substring(dot + 1) : head;
        float a0 = args.Count > 0 ? args[0] : 0f;
        float a1 = args.Count > 1 ? args[1] : 0f;
        switch (k)
        {
            // ---- 在庫(edogoyomi ほか)
            case "Kura":   return EdoAssets.Eg.Kura;
            case "Hogaki": return EdoAssets.Eg.Hogaki5;
            case "Itabei": return EdoAssets.Eg.Itabei5;
            case "Kabukimon": return EdoAssets.Eg.Kabukimon;
            case "TakeGaki":  return EdoAssets.Eg.TakeGaki;
            case "DanishiStep": return EdoAssets.Own.DanishiStep;
            // ---- 松江松平のために焼いた汎用の附属屋(指図が名指しで流用を決めた)
            case "Dozo": return EdoAssets.Own.Matsudaira.Dozo;
            case "Koya": return EdoAssets.Own.Matsudaira.Koya;
            case "Ido":  return EdoAssets.Own.Matsudaira.Ido;
            // ---- 表長屋(引数は **m**)
            case "NagayaOmote":   return a0 > 0f ? EdoAssets.Own.NagayaOmote(a0) : null;
            case "NagayaOmote2F": return a0 > 0f ? EdoAssets.Own.NagayaOmote2F(a0) : null;
            // ---- 崖下(法尻の帯)。⚠ 引数は **間** なので足跡から引く(指図は m で書いている)
            case "ObiNagaya":  return wKen > 0f ? EdoAssets.Own.ObiNagaya(wKen, dKen) : null;
            case "ObiMonooki": return EdoAssets.Own.ObiMonooki;
            case "ObiKawaya":  return EdoAssets.Own.ObiKawaya;
            // ---- 岡部のために焼いた附属屋
            case "Umaya":      return EdoAssets.Own.Umaya;
            case "Tomomachi":  return EdoAssets.Own.Tomomachi;
            case "NandoKoya":  return EdoAssets.Own.NandoKoya;
            case "Kurumayose":
                // ⭕ 切り欠き済みの版があればそちらを使う(裁定10=A の納め)。
                //    ⛔ 実行時にメッシュを割らない — 縁がぎざぎざになって瓦が欠ける
                return AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Own.KurumayoseCut) != null
                     ? EdoAssets.Own.KurumayoseCut : EdoAssets.Own.Kurumayose;
            case "KurumayoseCut": return EdoAssets.Own.KurumayoseCut;
            case "Jouguchi":   return EdoAssets.Own.Jouguchi;
            case "Inari15":    return EdoAssets.Own.Inari15;
            case "Torii":      return EdoAssets.Own.Torii;
            // ---- 結界(のし塀)。長さは区間から出す(指図は長さを書かない)
            case "Noshibei":   return EdoAssets.Own.Noshibei(a0 > 0f ? a0 : wKen);
            // ---- 門・木戸
            case "Munamon":    return wKen > 0f ? EdoAssets.Own.Munamon(wKen, false) : null;
            // ⚠ 木戸の**X の実寸は開口より柱2本ぶん広い**(2.727→3.197 / 2.909→3.379)。
            //    塀の run はその**実寸の外側**に取り付く(開口の値で継ぐと 0.47m 食い込む)
            case "Kido":       return (a0 > 0f ? a0 : wKen) > 0f
                                   ? EdoAssets.Own.Kido(a0 > 0f ? a0 : wKen) : null;
            case "HoriKido":   return EdoAssets.Own.HoriKido;
            // ---- 御殿の入母屋。⭕ **指図の (wKen, dKen) をそのまま渡す**(長辺先で書かれている)
            case "RoofIrimoya_":
            case "GotenRoofIrimoya":
                return args.Count >= 2 ? EdoAssets.Own.GotenRoofIrimoya((int)a0, (int)a1) : null;
            // ---- 西の斜面の丸太物
            case "MarutaTesuri":     return EdoAssets.Own.MarutaTesuri;
            case "MarutaTesuriPost": return EdoAssets.Own.MarutaTesuriPost;
            case "Kui":              return a0 > 0f ? EdoAssets.Own.Kui(a0) : null;
            case "KuiNuki":          return EdoAssets.Own.KuiNuki;
            default: return null;
        }
    }

    /// <summary>ローカル **+X** をグリッドの向き (du, dv) へ向ける yaw[°]。
    /// ⚠ 部材ごとに「+X が何を向くか」は違う(厩・供待は長手 = v / 車寄は +Z が参道の側)。
    /// ⛔ 「長いほうへ +X」で一律に決めない — 部材の doc が正典。</summary>
    public static float YawTo(float du, float dv)
    {
        var f = Grid;
        Vector2 d = (f.W(du, dv) - f.W(0f, 0f)).normalized;
        return Mathf.Atan2(-d.y, d.x) * Mathf.Rad2Deg;
    }

    /// <summary>⛔ **裁定待ちで据えない**もの。⭕ **2026-09-04 のユーザー裁定で 2件とも解けた**:
    ///   ・裁定10=A … 車寄は桟瓦のまま**玄関棟の屋根面へ差し込む**(切り欠いて据える)
    ///   ・裁定11=B … 御錠口は**廊下幅一間の建具**にする(`Own.Jouguchi` は使わない)
    /// ⚠ 空にしておく — 次に裁定待ちが出たらここへ名を入れれば据えなくなる。</summary>
    static readonly HashSet<string> HeldForRuling = new HashSet<string>();

    /// <summary>箱状の附属屋を一つ据える(足跡の中心・地盤レベル)。
    /// ⚠ 部材の実寸と指図の足跡が食い違うときは**縮めも伸ばしもしない** — 記録する。
    ///   決め打ちで潰すと、指図の寸法が意味を失う(CLAUDE.md 規則5)。</summary>
    static bool PlaceBox(Transform grp, string nm, string path, Vector2 c, float y,
                         float wKen, float dKen, float yaw, List<string> wait)
    {
        var go = EdoBuild.Place(path, new Vector3(c.x, y, c.y), yaw, Vector3.one, grp, nm);
        if (go == null) { wait.Add("附属屋 " + nm + ": 部材が読めない " + path); return false; }
        var b = EdoBuild.RB(go);
        go.transform.position += new Vector3(c.x - b.center.x, y - b.min.y, c.y - b.center.z);
        float wantW = wKen * C("ken"), wantD = dKen * C("ken");
        float hw, hd; ObbWD(go, out hw, out hd);          // ⭕ OBB
        float haveW = Mathf.Max(hw, hd), haveD = Mathf.Min(hw, hd);
        if (Mathf.Abs(haveW - Mathf.Max(wantW, wantD)) > 0.5f ||
            Mathf.Abs(haveD - Mathf.Min(wantW, wantD)) > 0.5f)
            wait.Add("附属屋 " + nm + ": 部材の実寸 " + haveW.ToString("F2") + "×" + haveD.ToString("F2")
                   + "m が指図の足跡 " + wantW.ToString("F2") + "×" + wantD.ToString("F2")
                   + "m と合わない(据えたが寸法は合っていない)");
        return true;
    }

    /// <summary>部材ごとの**向きの規約**。⛔ 「長いほうへ +X」で一律に決めない — 部材の doc が正典。
    /// 返すのは「ローカル +X を向けるグリッドの向き」(du, dv)。</summary>
    static void OrientOf(string key, float du, float dv, out float xu, out float xv, out string note)
    {
        note = null;
        int dot = key == null ? -1 : key.LastIndexOf('.');
        int lp = key == null ? -1 : key.IndexOf('(');
        string k = key == null ? "" : key.Substring(dot + 1, (lp < 0 ? key.Length : lp) - dot - 1);
        switch (k)
        {
            // 崖下の帯: +Z = 開口面(山側 = −v)⇒ +X = −u。⛔ 逆にすると盲面が山へ向く
            case "ObiNagaya": case "ObiMonooki": case "ObiKawaya":
                xu = -1f; xv = 0f; note = "+Z を山側(−v)へ"; return;
            // 稲荷の小祠: +Z = 正面(南 = −u)⇒ +X = +v
            case "Inari15":
                xu = 0f; xv = 1f; note = "+Z を南(−u)へ"; return;
            // 車寄: +X = +u / +Z = 参道の側(−v)⇒ +X = −u(⚠ いまは据えない)
            case "Kurumayose":
                xu = -1f; xv = 0f; note = "+Z を参道(−v)へ"; return;
            // 既定: 長辺へ +X(厩・供待は長手 = v / 納戸小屋は長手 = u。どちらもこれで合う)
            default:
                if (du >= dv) { xu = 1f; xv = 0f; } else { xu = 0f; xv = 1f; }
                return;
        }
    }

    static string PlaceService(List<string> wait)
    {
        var grp = Group("Fuzoku/Service"); Clear(grp);
        var f = Grid;
        int made = 0, noAsset = 0, pivotOdd = 0;
        foreach (var o in A(D["service"]) ?? new List<object>())
        {
            var s2 = O(o); if (s2 == null) continue;
            string nm = S(s2["name"]);
            float u0 = F(s2["u0"]), v0 = F(s2["v0"]), u1 = F(s2["u1"]), v1 = F(s2["v1"]);
            float du = u1 - u0, dv = v1 - v0;
            // ⚠ 呼び寸法は**足跡の長辺・短辺**で渡す
            float wKen = Mathf.Max(du, dv), dKen = Mathf.Min(du, dv);
            string key = Has(s2, "asset") ? S(s2["asset"]) : null;
            string path = AssetByKey(key, wKen, dKen);
            if (path == null)
            {
                noAsset++;
                wait.Add("附属屋 " + nm + "(" + S(s2["label"]) + " " + du.ToString("0.##")
                       + "×" + dv.ToString("0.##") + "間): 部材が引けない "
                       + (key ?? "(asset の指定なし)"));
                continue;
            }
            // ⚠ **表長屋の部材はピボットの規約が違う**(走りの中心・土台の底・**壁の外面**)。
            //   足跡の中心へ置くと梁間の半分ずれる。⛔ どちらの面を外にするかは指図が持たない。
            if (key.Contains("NagayaOmote"))
            {
                pivotOdd++;
                wait.Add("家臣長屋 " + nm + "(" + S(s2["label"]) + "): 部材 " + key
                       + " は**ピボットが壁の外面**(走りの中心・土台の底)で、足跡の中心ではない。"
                       + "⛔ **どちらの面を外に向けるか**が指図に無いので据えない — "
                       + "外周の長屋と違い自立の棟なので、向きは納めの判断(指図方・庭方へ)");
                continue;
            }
            float xu, xv; string nt;
            OrientOf(key, du, dv, out xu, out xv, out nt);
            float yaw = YawTo(xu, xv);
            Vector2 c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
            if (PlaceBox(grp, nm, path, c, F(s2["y"]), du, dv, yaw, wait)) made++;
        }
        var sb = new System.Text.StringBuilder("附属屋: " + made + " 棟据えた");
        if (noAsset > 0) sb.Append(" / " + noAsset + " 棟は部材が引けない");
        if (pivotOdd > 0) sb.Append(" / " + pivotOdd + " 棟はピボットの規約待ち");
        return sb.ToString();
    }

    static string PlaceWells(List<string> wait)
    {
        var grp = Group("Fuzoku/Ido"); Clear(grp);
        var f = Grid;
        int made = 0, noAsset = 0;
        foreach (var o in A(D["wells"]) ?? new List<object>())
        {
            var w = O(o); if (w == null) continue;
            string nm = S(w["name"]);
            string path = AssetByKey(Has(w, "asset") ? S(w["asset"]) : null);
            if (path == null)
            { noAsset++; wait.Add("井戸 " + nm + ": 部材が引けない " + (Has(w, "asset") ? S(w["asset"]) : "(指定なし)")); continue; }
            Vector2 c = f.W(F(w["u"]), F(w["v"]));
            var go = EdoBuild.Place(path, new Vector3(c.x, F(w["y"]), c.y), YawU(), Vector3.one, grp, nm);
            if (go == null) { wait.Add("井戸 " + nm + ": 部材が読めない " + path); continue; }
            var b = EdoBuild.RB(go);
            go.transform.position += new Vector3(c.x - b.center.x, F(w["y"]) - b.min.y, c.y - b.center.z);
            made++;
        }
        return "井戸: " + made + " 基据えた" + (noAsset > 0 ? " / " + noAsset + " 基は部材が引けない" : "");
    }

    // ---------------------------------------------------------------- 結界の塀
    /// <summary>表向と奥向を屋外でも分ける結界の塀。**練塀ではなく「のし塀+瓦」**
    /// (屋敷の内部の仕切りなので外構より軽くする — 指図 `_kekkai`)。
    /// ⚠ のし塀の部材は在庫に無い。板塀(`Itabei5`)は別の構法なので**代用しない**。</summary>
    /// <summary>結界の塀と、その開口に建てる木戸・中門。
    ///
    /// ⚠ **開口の幅で塀を継がない。**木戸の X の実寸は開口より**方立柱2本ぶん広い**
    ///   (開口 2.727 → 実寸 3.197)。開口の値で継ぐと塀が木戸へ 0.47m 食い込む。
    ///   ⭕ **据えた駒の実メッシュから走り方向の幅を測り、その外側で塀を切る**
    ///   (CLAUDE.md 規則5「部材どうしを中心で合わせない」)。
    /// ⭕ のし塀の長さは**区間から出す**(指図は長さを書かない)。</summary>
    static string PlaceKekkai(List<string> wait)
    {
        var grp = Group("Fuzoku/Nakajikiri"); Clear(grp);
        var f = Grid;
        float ken = C("ken");
        int made = 0, gates = 0; var missing = new HashSet<string>();
        foreach (var o in A(Get(D, "kekkai")) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue;
            string nm = S(k["name"]);
            string key = Has(k, "asset") ? S(k["asset"]) : null;
            if (key == null) { wait.Add("結界 " + nm + ": 指図 kekkai[].asset が無い"); continue; }
            var av = A(Get(k, "a")); var bv = A(Get(k, "b"));
            if (av == null || bv == null) { wait.Add("結界 " + nm + ": a / b が無い"); continue; }
            float au = F(av[0]), avv = F(av[1]), bu = F(bv[0]), bvv = F(bv[1]);
            float lenKen = Mathf.Sqrt((bu - au) * (bu - au) + (bvv - avv) * (bvv - avv));
            if (lenKen < 1e-6f) continue;
            float yaw = YawTo(bu - au, bvv - avv);

            // ---- 開口(木戸・中門)。⭕ 先に**部材を据えて実寸を測り**、その外側で塀を切る
            var cuts = new List<float[]>();
            var gap = O(Get(k, "gap"));
            if (gap != null)
            {
                string ax = S(Get(gap, "axis"));
                float g0 = F(Get(gap, "from")), g1 = F(Get(gap, "to"));
                float p0 = ax == "u" ? au : avv, p1 = ax == "u" ? bu : bvv;
                float declKen = Mathf.Abs(g1 - g0);                    // from/to から出る開口[間]
                float wantKen = Has(gap, "wKen") ? F(gap["wKen"]) : declKen;  // 指図が幅を持つならそれ
                if (Mathf.Abs(p1 - p0) > 1e-6f)
                {
                    float t0 = Mathf.Clamp01((g0 - p0) / (p1 - p0)), t1 = Mathf.Clamp01((g1 - p0) / (p1 - p0));
                    float tc = (t0 + t1) * 0.5f;
                    // ⛔ **指図の中で幅が食い違うなら据えない**(2026-09-04 部材方の申し送り:
                    //    W6 は from/to の差 3.00間 / 文言 1.6間 / 塀の実長からの口 1.85間 の三つ巴)
                    if (Mathf.Abs(declKen - wantKen) > 0.01f)
                    {
                        wait.Add("結界 " + nm + " の開口は**指図の中で幅が食い違う** — from/to の差 "
                               + declKen.ToString("0.##") + "間 / 宣言 " + wantKen.ToString("0.##")
                               + "間。⛔ 一つに揃うまで木戸を据えない(塀の run もその幅で動く)");
                    }
                    else
                    {
                        // 木戸(中門は棟門)。呼び寸法は**開口の m**
                        bool isMon = S(Get(gap, "kind")) == "中門";
                        string gk = Has(gap, "asset") ? S(gap["asset"]) : (isMon ? "Own.Munamon" : "Own.Kido");
                        float wM = Mathf.Round(wantKen * ken * 100f) / 100f;
                        string gpath = AssetByKey(gk, wM, 0f);
                        Vector2 gc = f.W(Mathf.Lerp(au, bu, tc), Mathf.Lerp(avv, bvv, tc));
                        float gy = Graded.At(gc.x, gc.y); if (float.IsNaN(gy)) gy = EdoBuild.Ground(gc.x, gc.y);
                        if (gpath == null || AssetDatabase.LoadAssetAtPath<GameObject>(gpath) == null)
                        {
                            missing.Add(nm + " の" + (isMon ? "中門" : "木戸") + " " + wM.ToString("0.##") + "m");
                        }
                        else
                        {
                            var gg = EdoBuild.Place(gpath, new Vector3(gc.x, gy, gc.y), yaw, Vector3.one,
                                                    grp, nm + "_Kido");
                            if (gg != null)
                            {
                                gates++;
                                // ⭕ **実メッシュの走り方向の幅**で塀を切る(呼び寸法ではない)
                                float gw2, gd2; ObbWD(gg, out gw2, out gd2);   // ⭕ OBB(ローカル +X = 開口の走り)
                                float realW = gw2;
                                float halfT = (realW / ken) * 0.5f / lenKen;
                                cuts.Add(new float[] { tc - halfT, tc + halfT });
                            }
                        }
                        if (cuts.Count == 0)   // 木戸が据わらなくても口は空ける
                            cuts.Add(new float[] { Mathf.Min(t0, t1), Mathf.Max(t0, t1) });
                    }
                }
            }

            // ---- のし塀 — 開口で割った区間ごとに、長さを算出して引く
            var segs = new List<float[]>();
            float cur = 0f;
            foreach (var c2 in cuts) { if (c2[0] > cur) segs.Add(new float[] { cur, c2[0] }); cur = Mathf.Max(cur, c2[1]); }
            if (cur < 1f) segs.Add(new float[] { cur, 1f });
            int i = 0;
            foreach (var sg in segs)
            {
                float segLen = (sg[1] - sg[0]) * lenKen * ken;
                if (segLen < 0.3f) continue;
                float call = Mathf.Round(segLen * 100f) / 100f;
                string path = AssetByKey(key, call, 0f);
                if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
                { missing.Add(nm + " の塀 " + call.ToString("0.##") + "m"); continue; }
                float tm = (sg[0] + sg[1]) * 0.5f;
                Vector2 c = f.W(Mathf.Lerp(au, bu, tm), Mathf.Lerp(avv, bvv, tm));
                // ⚠ ピボットは**走りの中心・地盤レベル・壁の芯**(面ではない)
                float y = Graded.At(c.x, c.y); if (float.IsNaN(y)) y = EdoBuild.Ground(c.x, c.y);
                var go = EdoBuild.Place(path, new Vector3(c.x, y, c.y), yaw, Vector3.one, grp, nm + "_" + i);
                if (go != null) { EdoBuild.SeatBottom(go, y); made++; }
                i++;
            }
        }
        var sb = new System.Text.StringBuilder("結界の塀: " + made + " 本 / 木戸・中門 " + gates + " 基");
        if (missing.Count > 0)
        {
            sb.Append(" / 部材の無い寸法 " + missing.Count + " 件");
            wait.Add("結界: 焼かれていない寸法 " + string.Join(" / ", new List<string>(missing).ToArray())
                   + " → build_noshibei.py / build_kido.py");
        }
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 石段
    /// <summary>石段。⚠ **足元と天端の標高は指図が持つ**(`y0`/`y1`)。地形から推測しない —
    /// 段の縁のすぐ外は擦り付けの途中だし、門の敷居は設計面に現れない
    /// (2026-08-25 松江松平: 地形読みで段が 0.33m 浮き、別の段は落差0と誤検知した)。</summary>
    static string PlaceKaidans(List<string> wait)
    {
        var grp = Group("Fuzoku/Kaidan"); Clear(grp);
        var f = Grid;
        var mod = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Own.DanishiStep);
        if (mod == null) { wait.Add("段石の部材が無い: " + EdoAssets.Own.DanishiStep); return "石段: 0"; }
        int made = 0;
        foreach (var o in A(D["kaidans"]) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue;
            string nm = S(k["name"]);
            if (!Has(k, "y0") || !Has(k, "y1"))
            {
                wait.Add("石段 " + nm + ": 指図 kaidans[].y0 / y1(足元と天端の標高)が無い。"
                       + "落差 " + F(k["drop"]).ToString("0.##") + "m と段数 " + (int)F(k["steps"])
                       + " はあるが、どの高さから登るかは書かれていない — ⛔ 地形から推測しない");
                continue;
            }
            float y0 = F(k["y0"]), y1 = F(k["y1"]);
            float drop = F(k["drop"]), run = F(k["run"]), wid = F(k["w"]);
            int steps = Mathf.Max(1, (int)F(k["steps"]));
            if (Mathf.Abs((y1 - y0) - drop) > 0.005f)
                wait.Add("石段 " + nm + ": 指図の中で矛盾 — y1−y0=" + (y1 - y0).ToString("F2")
                       + " と drop=" + drop.ToString("F2"));
            // 登りは +v(門前面 → 主面)。u は開口の芯 gapU
            float cu = F(k["gapU"]), v0 = F(k["v0"]), v1 = F(k["v1"]);
            Vector2 up = (f.W(cu, v1) - f.W(cu, v0)).normalized;
            Vector2 side = new Vector2(up.y, -up.x);
            float yaw = Mathf.Atan2(up.x, up.y) * Mathf.Rad2Deg;
            float rise = drop / steps, tread = run / steps;
            Vector2 c0 = f.W(cu, (v0 + v1) * 0.5f);
            int across = Mathf.Max(1, Mathf.RoundToInt(wid / 1.98f));
            for (int i = 0; i < steps; i++)
            {
                float sPos = -run * 0.5f + tread * (i + 0.5f);
                float top = y0 + rise * (i + 1);
                for (int j = 0; j < across; j++)
                {
                    float t = (j - (across - 1) * 0.5f) * (wid / across);
                    Vector2 c = c0 + up * sPos + side * t;
                    var go = EdoBuild.Place(EdoAssets.Own.DanishiStep, new Vector3(c.x, top, c.y),
                                            yaw, Vector3.one, grp, nm + "_" + i + "_" + j);
                    if (go == null) continue;
                    // **天端を踏面に合わせる**(段石は上面が踏面。汐見坂と同じ据え方)
                    var bb = EdoBuild.RB(go);
                    go.transform.position += new Vector3(c.x - bb.center.x, top - bb.max.y, c.y - bb.center.z);
                    made++;
                }
            }
        }
        return "石段: " + made + " 枚";
    }

    // ---------------------------------------------------------------- 参道
    /// <summary>参道(表門の軸を通る白洲)。⭕ **屋根を架けない**(2026-08-19 ユーザー裁定 —
    /// 前庭は開けた白洲で、屋根は式台・車寄せまで)。実体は**地表の塗り**なので、
    /// ここでは物を据えず、地表の巡(スプラット)へ渡す。</summary>
    static string PlaceSando(List<string> wait)
    {
        var sd = O(Get(D, "sando"));
        if (sd == null) return "参道: 指図に sando が無い";
        wait.Add("参道(u=" + F(sd["u"]).ToString("0.##") + " / v " + F(sd["v0"]).ToString("0.##")
               + "〜" + F(sd["v1"]).ToString("0.##") + "間・幅" + F(sd["width"]).ToString("0.##")
               + "間): 据える物は無い(白洲=地表の塗り)。⭕ 地表の巡で受ける — "
               + "指図が『どの地表層で塗るか』を持っていないので、そこは欄待ち");
        return "参道: 据える物なし(地表の巡へ)";
    }

    // =====================================================================
    // Stage4 — 庭(⛔ **地形には触らない**)
    //
    // ⭐ **池の床も築山も S1 が既に彫ってある。**生成器の `graded_y` は `niwa_y`(池の放物面・
    //   築山の円錐)を段より**先に**重ねるので、`impl.graded` にそれが入っている
    //   (2026-09-04 実測: 汀線上 23.97〜24.00 / 最深 22.68(池床 22.50)/ 築山の頂の近く 27.59)。
    //   ⛔ **ここで掘り直さない。**WaterBaker の `Recarve` を呼ぶと S1 が正しく作った岬・
    //   中島・くびれが平らに戻る(メモリ「池のsnap矩形の重なり」/「Recarveで造成が消える」)。
    //   ⚠ WaterBaker の snap 矩形 320×320m は**他邸に掛かる**(松江の 6a が土井6点・岡部4点に
    //   掛かって起票になった)。当邸から呼ぶときも同じ危険がある。
    //
    // ⭕ したがって S4 の受け持ちは **① 部材を据える ② 地表と水面を次の輪へ渡す** の2つだけ。
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/4 庭(部材を据える・地形には触らない)")]
    public static void Stage4Menu() { Debug.Log("[Okabe] " + Stage4_Niwa()); }

    public static string Stage4_Niwa()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var wait = new List<string>();
        var sb = new System.Text.StringBuilder();
        var items = A(Get(IMPL, "gardens"));
        if (items == null)
        { return "庭: 算出物に gardens が無い — 生成器の --export-impl に足すこと"; }

        var grp = Group("Niwa"); Clear(grp);
        int made = 0, splat = 0, terrainOwned = 0, skipped = 0;
        var missing = new Dictionary<string, int>();
        var byKind = new Dictionary<string, int>();

        foreach (var o in items)
        {
            var g = O(o); if (g == null) continue;
            string kind = S(g["kind"]) ?? "?";
            string key = Has(g, "asset") ? S(g["asset"]) : null;
            var pts = A(Get(g, "world"));
            byKind[kind] = (byKind.ContainsKey(kind) ? byKind[kind] : 0) + 1;

            // ---- 地表の塗り(スプラット)は**地表の輪**が受け持つ。ここでは据えない
            if (key != null && key.StartsWith("L_")) { splat++; continue; }
            // ---- 地形そのもの(汀線・池・築山・中島の輪郭・庭の実形)は S1 が彫った
            if (key == null) { terrainOwned++; continue; }

            // ⚠ **部材ごとに据え方が違う**(ピボットも正規化の軸も別)。⛔ 一律に置かない。
            var sub = Group("Niwa/" + kind.Replace("(", "_").Replace(")", "").Replace("・", "_"));
            int n0 = PlaceNiwaItem(sub, g, kind, key, pts, missing, wait);
            made += n0;
            if (n0 == 0 && !missing.ContainsKey(key)) skipped++;
        }
        if (skipped > 0) sb.Append("");
        sb.Append("庭: " + made + " 点据えた / 地表の塗り " + splat + " 件は**地表の輪**へ / "
                + "地形 " + terrainOwned + " 件は **S1 が彫り済み**(⛔ 掘り直さない)");
        foreach (var kv in missing)
            wait.Add("庭の部材が EdoAssets に無い: " + kv.Key + "(" + kv.Value + " 件)");
        sb.Append('\n').Append(PlaceWaterSurface(items, wait));
        sb.Append('\n').Append(PaintSplat(items, wait));
        sb.Append('\n').Append("── 据えなかったもの " + wait.Count + " 件 ──");
        foreach (var w in wait) sb.Append("\n  ★ ").Append(w);
        return sb.ToString();
    }

    /// <summary>**池の水面だけを張る**(2026-09-04 普請奉行の裁定)。
    ///
    /// ⛔⛔ **`WaterBaker.Recarve` を呼ばない。**床は S1 が彫ってあり、Recarve は
    ///   スナップ領域(輪郭 bbox + 150m)を丸ごと書き戻すので、**S1 が作った岬・中島・くびれが
    ///   平らに戻る**(メモリ「Recarveで造成が消える」/「池のsnap矩形の重なり」)。
    ///   ⚠ `WaterBaker.Create` は末尾で `Recarve` を呼ぶので**使わない** — 器を自分で組み、
    ///   **`RebuildSurface`(水面メッシュだけ)** を呼ぶ。
    ///   ⭕ 副次の利点: `WaterBody` として場面に居るので、**他邸が Recarve したとき
    ///   `OtherWaterMask` が当家の池を守ってくれる**(掘り込みを埋められない)。
    ///
    /// ⚠ **二重に平滑しない。**`RebuildSurface` は `SmoothTagged(outline, sharp, 2)` を掛けるが、
    ///   指図の汀線は**既に Chaikin 2 回の平滑後**(65点)である。⇒ `sharp` を全 true にして
    ///   角を残す = 平滑を素通しにする。⛔ 素通しにしないと汀線が縮んで、S1 が彫った床と合わない。
    ///
    /// ⚠ 材質は**場面に既に居る水面から借りる**(松江松平の御泉水と揃える指示)。
    ///   無いときだけ `WaterBaker.Create` と同じ設定で起こす。⛔ レイヤは触らない(既定のまま)。</summary>
    static string PlaceWaterSurface(List<object> items, List<string> wait)
    {
        // 汀線(平滑後)を算出物から取る
        Dictionary<string, object> mig = null;
        foreach (var o in items)
        { var g = O(o); if (g != null && (S(g["kind"]) ?? "").StartsWith("汀線")) { mig = g; break; } }
        if (mig == null) { wait.Add("算出物に汀線(平滑後)が無い — 水面を張れない"); return "水面: 汀線待ち"; }
        var pts = A(Get(mig, "world"));
        if (pts == null || pts.Count < 3) { wait.Add("汀線の点が足りない"); return "水面: 汀線待ち"; }
        float wy = F(mig["y"]);
        float depth = Has(mig, "depthMax") ? F(mig["depthMax"]) : 1.5f;

        string nm = "P_" + (S(mig["name"]) ?? "Sensui");
        var parent = GameObject.Find("Water");
        if (parent == null) { parent = new GameObject("Water"); Undo.RegisterCreatedObjectUndo(parent, "water"); }
        var exist = parent.transform.Find(nm);
        WaterBody wb = exist != null ? exist.GetComponent<WaterBody>() : null;
        if (wb == null)
        {
            var go = new GameObject(nm, typeof(MeshFilter), typeof(MeshRenderer), typeof(WaterBody));
            Undo.RegisterCreatedObjectUndo(go, "water");
            go.transform.SetParent(parent.transform, true);
            wb = go.GetComponent<WaterBody>();
        }
        wb.outline = new List<Vector3>();
        wb.sharp = new List<bool>();
        foreach (var q in pts)
        {
            var w = A(q); if (w == null || w.Count < 2) continue;
            wb.outline.Add(new Vector3(F(w[0]), wy, F(w[1])));
            wb.sharp.Add(true);           // ⛔ 二重に平滑しない(指図の汀線は平滑後)
        }
        wb.waterY = wy;
        wb.depth = depth;
        // ⛔ 地形を彫る側の設定は**触らない**(Recarve を呼ばないので効かないが、既定を明示しておく)
        wb.raiseBanks = false; wb.verticalWalls = false; wb.levelFloor = false;

        // 材質 — 場面の他の水面から借りる(松江の御泉水と揃える)
        var mr = wb.GetComponent<MeshRenderer>();
        if (mr.sharedMaterial == null)
        {
            Material donor = null;
            foreach (var o2 in UnityEngine.Object.FindObjectsByType<WaterBody>(
                         FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (o2 == wb) continue;
                var r2 = o2.GetComponent<MeshRenderer>();
                if (r2 != null && r2.sharedMaterial != null) { donor = r2.sharedMaterial; break; }
            }
            if (donor != null) mr.sharedMaterial = donor;
            else
            {
                var sh = Shader.Find("Edo/Water");
                if (sh == null) { wait.Add("シェーダ `Edo/Water` が見つからない(URP の Depth+Opaque Texture が要る)"); return "水面: 材質待ち"; }
                var mat = new Material(sh);
                mat.SetColor("_DeepColor", new Color(0.13f, 0.32f, 0.40f));
                mat.SetColor("_ShallowColor", new Color(0.28f, 0.50f, 0.55f));
                mat.SetFloat("_FresnelPower", 3.0f); mat.SetFloat("_Alpha", 0.8f);
                AssetDatabase.CreateAsset(mat, AssetDatabase.GenerateUniqueAssetPath(
                    "Assets/Edo/Water/" + nm + ".mat"));
                mr.sharedMaterial = mat;
                wait.Add("水面の材質を**新しく起こした**(場面に借りられる水面が無かった)。"
                       + "⚠ 松江松平の御泉水と見え方が揃っているか、検証レンダで確かめること");
            }
        }
        // ⭕ **水面メッシュだけ**を焼く。⛔ Recarve は呼ばない
        WaterBaker.RebuildSurface(wb);
        return "水面: " + nm + " 汀 " + wb.outline.Count + " 点 / 水面 " + wy.ToString("F2")
             + "(⛔ 地形は彫っていない — 床は S1)";
    }

    /// <summary>**地表を塗る**(2026-09-04 指図方が `layer` を宣言した分)。
    ///
    /// ⭕ 面の**実形**(段の多角形で切った後)で塗る。⛔ json の矩形で塗らない。
    /// 混合は `layerMix` の比(例 `L_grass + L_bare` を 0.7:0.3)。
    /// ⛔ **層の番号を決め打ちしない** — `.terrainlayer` のパスで地形の層を引く
    /// (層の並びは邸ごと・時期ごとに変わる。番号を書くと黙って別の層を塗る)。
    /// ⛔⛔ **区画の外は 1 セルも塗らない。**塗った数と、外に掛かって捨てた数の両方を出す。</summary>
    static string PaintSplat(List<object> items, List<string> wait)
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        var layers = td.terrainLayers;
        // 層の名 → 地形の層の番号。⛔ 番号を書かない
        var idx = new Dictionary<string, int>();
        for (int i = 0; i < layers.Length; i++)
        {
            if (layers[i] == null) continue;
            string ap = AssetDatabase.GetAssetPath(layers[i]);
            if (string.IsNullOrEmpty(ap)) continue;
            idx[System.IO.Path.GetFileNameWithoutExtension(ap)] = i;
        }
        // 塗る面を集める
        var faces = new List<object[]>();      // { Vector2[] poly, float[] weights }
        int noLayer = 0;
        foreach (var o in items)
        {
            var g = O(o); if (g == null || !Has(g, "layer")) continue;
            var pts = A(Get(g, "world"));
            if (pts == null || pts.Count < 3) { noLayer++; continue; }
            // "L_grass + L_bare" を割る
            var names = new List<string>();
            foreach (var nm in S(g["layer"]).Split('+')) names.Add(nm.Trim());
            var mix = A(Get(g, "layerMix"));
            var wts = new float[layers.Length];
            bool ok = true; float tot = 0f;
            for (int i = 0; i < names.Count; i++)
            {
                if (!idx.ContainsKey(names[i]))
                { wait.Add("地形に層 " + names[i] + " が無い(面 " + S(g["name"]) + ")"); ok = false; break; }
                float w = (mix != null && i < mix.Count) ? F(mix[i]) : 1f / names.Count;
                wts[idx[names[i]]] += w; tot += w;
            }
            if (!ok || tot <= 0f) continue;
            for (int i = 0; i < wts.Length; i++) wts[i] /= tot;
            var poly = new List<Vector2>();
            foreach (var q in pts) { var w2 = A(q); if (w2 != null && w2.Count >= 2) poly.Add(new Vector2(F(w2[0]), F(w2[1]))); }
            faces.Add(new object[] { poly.ToArray(), wts });
        }
        if (faces.Count == 0) return "地表の塗り: 塗る面が無い";

        // 敷地の外接矩形だけを読む(⛔ 全域は重い)
        var P = Poly;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in P) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        Vector3 tp = t.transform.position, ts = td.size;
        int aw = td.alphamapWidth, ah = td.alphamapHeight, L = td.alphamapLayers;
        System.Func<float, int> AX = delegate(float wx) { return Mathf.Clamp(Mathf.FloorToInt((wx - tp.x) / ts.x * aw), 0, aw - 1); };
        System.Func<float, int> AZ = delegate(float wz) { return Mathf.Clamp(Mathf.FloorToInt((wz - tp.z) / ts.z * ah), 0, ah - 1); };
        int x0 = AX(mnx), x1 = AX(mxx), z0 = AZ(mnz), z1 = AZ(mxz);
        int w3 = x1 - x0 + 1, h3 = z1 - z0 + 1;
        var A3 = td.GetAlphamaps(x0, z0, w3, h3);
        int painted = 0, outside = 0;
        for (int zz = 0; zz < h3; zz++)
            for (int xx = 0; xx < w3; xx++)
            {
                var p = new Vector2(tp.x + (x0 + xx + 0.5f) / aw * ts.x, tp.z + (z0 + zz + 0.5f) / ah * ts.z);
                float[] wts = null;
                foreach (var f2 in faces)
                { if (EdoGeom.PIP((Vector2[])f2[0], p)) { wts = (float[])f2[1]; break; } }
                if (wts == null) continue;
                // ⛔⛔ **区画の外は塗らない**(面が区画を跨いでいても切る)
                if (!EdoGeom.PIP(P, p)) { outside++; continue; }
                for (int l = 0; l < L && l < wts.Length; l++) A3[zz, xx, l] = wts[l];
                painted++;
            }
        td.SetAlphamaps(x0, z0, A3);
        var sb = new System.Text.StringBuilder("地表の塗り: " + painted + " セル / 面 " + faces.Count + " 件");
        sb.Append(outside > 0 ? "(⛔ 区画の外に掛かった " + outside + " セルは塗らずに捨てた ✔)"
                              : "(区画の外に掛かるセルは無し ✔)");
        if (noLayer > 0) wait.Add("layer を持つが輪郭の点が足りない面 " + noLayer + " 件");
        return sb.ToString();
    }

    /// <summary>庭の一節を据える。**部材ごとに据え方が違う**ので種別で分ける。
    /// ⛔ 一律に「点へ置いて底を地盤に合わせる」としない — 石は埋まり、飛石はピボットが天端、
    /// 垣は1間で突き付け、乱杭はピボットが頭。部材の doc が正典。</summary>
    static int PlaceNiwaItem(Transform sub, Dictionary<string, object> g, string kind, string key,
                             List<object> pts, Dictionary<string, int> missing, List<string> wait)
    {
        string nm = S(g["name"]);
        System.Func<string, GameObject> load = delegate(string pth)
        {
            if (pth == null || AssetDatabase.LoadAssetAtPath<GameObject>(pth) == null)
            { missing[key] = (missing.ContainsKey(key) ? missing[key] : 0) + 1; return null; }
            return AssetDatabase.LoadAssetAtPath<GameObject>(pth);
        };
        System.Func<int, Vector2> P2 = delegate(int i)
        { var w = A(pts[i]); return new Vector2(F(w[0]), F(w[1])); };
        System.Func<Vector2, float> GY = delegate(Vector2 c)
        { float y = Graded.At(c.x, c.y); return float.IsNaN(y) ? EdoBuild.Ground(c.x, c.y) : y; };
        int made = 0;

        // ---- 庭石(景石・岩島)。⭕ 丈 1.0 に正規化・ピボット = 芯・底
        //      露出 h を `buryRatio` 埋めるなら **総丈 H = h/(1−bury)**、y = 地盤 − (H−h)
        if (kind == "景石" || kind == "岩島")
        {
            float h = F(Get(g, "h"));
            float bury = Has(g, "buryRatio") ? F(g["buryRatio"]) : 0.333f;
            float sink = Has(g, "sink") ? F(g["sink"]) : 0f;
            int idv = StableHash(nm) % 5;
            var src = load(EdoAssets.Own.Ishigumi(idv)); if (src == null) return 0;
            Vector2 c = P2(0);
            float H = h / Mathf.Max(0.05f, 1f - bury);
            float y = (Has(g, "y") ? F(g["y"]) : GY(c)) - (H - h) - sink;
            var go = EdoBuild.Place(EdoAssets.Own.Ishigumi(idv), new Vector3(c.x, y, c.y),
                                    StableHash(nm + "y") % 360, Vector3.one * H, sub, nm);
            if (go != null) made++;
            // 岩島は肩石を1つ添える
            if (kind == "岩島" && Has(g, "hShoulder"))
            {
                float hs = F(g["hShoulder"]);
                float Hs = hs / Mathf.Max(0.05f, 1f - bury);
                var go2 = EdoBuild.Place(EdoAssets.Own.Ishigumi(4),
                    new Vector3(c.x + 0.9f, (Has(g, "y") ? F(g["y"]) : GY(c)) - (Hs - hs) - sink, c.y + 0.5f),
                    StableHash(nm + "s") % 360, Vector3.one * Hs, sub, nm + "_Kata");
                if (go2 != null) made++;
            }
            return made;
        }

        // ---- 石組護岸。折れ線に沿って `stones` 個。⭕ **長軸**で指定されるので scale = 長軸/W_i
        if (kind.StartsWith("石組護岸"))
        {
            int n = Has(g, "stones") ? (int)F(g["stones"]) : 20;
            float lo = F(Get(g, "lenMin")), hi = F(Get(g, "lenMax"));
            float bury = Has(g, "buryRatio") ? F(g["buryRatio"]) : 0.333f;
            float jag = Has(g, "jag") ? F(g["jag"]) : 0f;
            int yaku = Has(g, "yakuEvery") ? (int)F(g["yakuEvery"]) : 0;
            float baseY = Has(g, "y") ? F(g["y"]) : 0f;
            for (int i = 0; i < n; i++)
            {
                bool isYaku = yaku > 0 && (i % yaku) == 0;
                int idv = isYaku ? 3 : (StableHash(nm + i) % 3);      // 役石は塊石 3
                float w0 = IshigumiW(idv);
                float axis = Mathf.Lerp(lo, hi, (StableHash(nm + "L" + i) % 1000) / 1000f);
                float sc = axis / Mathf.Max(0.05f, w0);
                Vector2 c = PolyAt(pts, n <= 1 ? 0f : i / (float)(n - 1));
                float y = baseY - sc * bury + ((StableHash(nm + "j" + i) % 1000) / 1000f - 0.5f) * 2f * jag;
                var go = EdoBuild.Place(EdoAssets.Own.Ishigumi(idv), new Vector3(c.x, y, c.y),
                                        StableHash(nm + "r" + i) % 360, Vector3.one * sc, sub, nm + "_" + i);
                if (go != null) made++;
            }
            return made;
        }

        // ---- 飛石・沢飛石。⭕ **長軸 1.0 に正規化・ピボット = 天端の芯**(石は −Y へ垂れる)
        //      ⚠ 沢飛石は必ず個体 2(厚 0.95)。0/1 は薄くて水中に浮く
        if (kind == "沢飛石" || kind == "飛石")
        {
            bool sawa = kind == "沢飛石";
            int n = Has(g, "n") ? (int)F(g["n"]) : pts.Count;
            float lo = Has(g, "rMin") ? F(g["rMin"]) : 0.55f;
            float hi = Has(g, "rMax") ? F(g["rMax"]) : 0.62f;
            for (int i = 0; i < n; i++)
            {
                int idv = sawa ? 2 : (StableHash(nm + i) % 2);
                var src = load(EdoAssets.Own.Tobiishi(idv)); if (src == null) return made;
                Vector2 c = (n == pts.Count) ? P2(i) : PolyAt(pts, n <= 1 ? 0f : i / (float)(n - 1));
                float axis = Mathf.Lerp(lo, hi, (StableHash(nm + "L" + i) % 1000) / 1000f);
                // ⭕ y は**天端**を直に(⛔ 底を地盤に合わせない)
                float y = Has(g, "y") ? F(g["y"]) : GY(c) + 0.04f;
                var go = EdoBuild.Place(EdoAssets.Own.Tobiishi(idv), new Vector3(c.x, y, c.y),
                                        StableHash(nm + "r" + i) % 360, Vector3.one * axis, sub, nm + "_" + i);
                if (go != null) made++;
            }
            return made;
        }

        // ---- 沓脱石。⭕ 一様スケール L/1.2・ピボット = 天端の芯
        if (kind == "沓脱石")
        {
            if (load(EdoAssets.Own.Kutsunugi) == null) return 0;
            Vector2 c = P2(0);
            float L = Has(g, "L") ? F(g["L"]) : 1.2f;
            float y = Has(g, "y") ? F(g["y"]) : GY(c);
            var go = EdoBuild.Place(EdoAssets.Own.Kutsunugi, new Vector3(c.x, y, c.y),
                                    0f, Vector3.one * (L / 1.2f), sub, nm);
            return go != null ? 1 : 0;
        }

        // ---- 垣(四つ目・建仁寺)。⭕ **1.818 ちょうどで突き付け**・+X 端に親柱・y = 地盤
        //      ⛔ SeatBottom を使わない(根入れ −0.15 のぶん浮く)
        if (kind.StartsWith("垣"))
        {
            bool kenninji = kind.Contains("建仁寺");
            float h = Has(g, "h") ? F(g["h"]) : (kenninji ? 1.5f : 1.2f);
            string span = kenninji ? EdoAssets.Own.KenninjiGaki(h) : EdoAssets.Own.YotsumeGaki(h);
            string post = kenninji ? EdoAssets.Own.KenninjiGakiPost(h) : EdoAssets.Own.YotsumeGakiPost(h);
            if (load(span) == null) return 0;
            const float SPAN = 1.818f;
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a2 = P2(i - 1), b2 = P2(i);
                float len = (b2 - a2).magnitude;
                if (len < SPAN * 0.5f) continue;
                int nS = Mathf.Max(1, Mathf.RoundToInt(len / SPAN));
                float pitch = len / nS;
                float yaw = Mathf.Atan2(b2.x - a2.x, b2.y - a2.y) * Mathf.Rad2Deg;
                for (int k = 0; k < nS; k++)
                {
                    Vector2 c = Vector2.Lerp(a2, b2, (k + 0.5f) / nS);
                    var go = EdoBuild.Place(span, new Vector3(c.x, GY(c), c.y), yaw,
                                            new Vector3(pitch / SPAN, 1f, 1f), sub, nm + "_" + i + "_" + k);
                    if (go != null) made++;
                }
                if (i == pts.Count - 1 && load(post) != null)
                {
                    var gp = EdoBuild.Place(post, new Vector3(b2.x, GY(b2), b2.y), yaw, Vector3.one, sub, nm + "_Post");
                    if (gp != null) made++;
                }
            }
            return made;
        }

        // ---- 灯籠。⭕ 在庫の雪見灯籠(edogoyomi)。ES 倍・ピボット = 足元
        if (kind == "灯籠")
        {
            if (load(EdoAssets.Eg.ToroYukimi) == null) return 0;
            Vector2 c = P2(0);
            float y = Has(g, "y") ? F(g["y"]) : GY(c);
            var go = EdoBuild.Place(EdoAssets.Eg.ToroYukimi, new Vector3(c.x, y, c.y),
                                    StableHash(nm) % 360, Vector3.one * ES, sub, nm);
            if (go != null) EdoBuild.SeatBottom(go, y);
            return go != null ? 1 : 0;
        }

        // ---- 乱杭。⭕ ピボット = 頭の芯・傾 4° は +X へ焼込 ⇒ yaw で方位が散る
        if (kind == "乱杭")
        {
            int n = Has(g, "n") ? (int)F(g["n"]) : pts.Count;
            float lo = Has(g, "rMin") ? F(g["rMin"]) : 0.034f;
            float hi = Has(g, "rMax") ? F(g["rMax"]) : 0.052f;
            float topY = Has(g, "y") ? F(g["y"]) : 0f;
            var dias = new float[] { 0.034f, 0.043f, 0.052f };
            for (int i = 0; i < n; i++)
            {
                float d = Mathf.Lerp(lo, hi, (StableHash(nm + i) % 1000) / 1000f);
                float best = dias[0];
                foreach (var dd in dias) if (Mathf.Abs(dd - d) < Mathf.Abs(best - d)) best = dd;
                string pth = EdoAssets.Own.Rangui(best);
                if (load(pth) == null) return made;
                Vector2 c = PolyAt(pts, n <= 1 ? 0f : i / (float)(n - 1));
                var go = EdoBuild.Place(pth, new Vector3(c.x, topY, c.y),
                                        StableHash(nm + "r" + i) % 360, Vector3.one, sub, nm + "_" + i);
                if (go != null) made++;
            }
            return made;
        }

        // ---- それ以外(1点物)
        {
            string pth = AssetByKey(key);
            if (load(pth) == null) return 0;
            Vector2 c = P2(0);
            float y = Has(g, "y") ? F(g["y"]) : GY(c);
            var go = EdoBuild.Place(pth, new Vector3(c.x, y, c.y), StableHash(nm) % 360, Vector3.one, sub, nm);
            if (go != null) { SeatByBury(go, g, y); return 1; }
            return 0;
        }
    }

    /// <summary>庭石の個体 i の、丈 1.000 のときの平面の幅 W(X)[m](部材の doc の実測値)。
    /// 護岸石のように**長軸**で指定される石の倍率を出すのに使う。</summary>
    static float IshigumiW(int i)
    {
        switch (i)
        {
            case 0: return 0.839f;   // 立石(板状) — 長軸は Z
            case 1: return 0.889f;   // 立石(やや太い)
            case 2: return 2.161f;   // 臥石(低く広い)
            case 3: return 1.536f;   // 塊石
            default: return 1.363f;  // 小塊
        }
    }

    /// <summary>折れ線 `pts`(世界座標)の走り比 t(0〜1)の点。</summary>
    static Vector2 PolyAt(List<object> pts, float t)
    {
        var v = new List<Vector2>();
        foreach (var q in pts) { var w = A(q); if (w != null && w.Count >= 2) v.Add(new Vector2(F(w[0]), F(w[1]))); }
        if (v.Count == 0) return Vector2.zero;
        if (v.Count == 1) return v[0];
        float tot = 0f;
        for (int i = 1; i < v.Count; i++) tot += (v[i] - v[i - 1]).magnitude;
        float want = Mathf.Clamp01(t) * tot, acc = 0f;
        for (int i = 1; i < v.Count; i++)
        {
            float seg = (v[i] - v[i - 1]).magnitude;
            if (acc + seg >= want) return Vector2.Lerp(v[i - 1], v[i], seg < 1e-6f ? 0f : (want - acc) / seg);
            acc += seg;
        }
        return v[v.Count - 1];
    }

    /// <summary>石を「丈の `buryRatio` だけ埋めて」据える。⛔ 底を地盤に合わせない —
    /// 石組は**埋まっているのが常法**で、置いただけだと乗っているように見える。</summary>
    static void SeatByBury(GameObject go, Dictionary<string, object> g, float groundY)
    {
        var b = EdoBuild.RB(go);
        float bury = Has(g, "buryRatio") ? F(g["buryRatio"]) : 0f;
        float sink = Has(g, "sink") ? F(g["sink"]) : 0f;
        go.transform.position += new Vector3(0f, groundY - b.min.y - b.size.y * bury - sink, 0f);
    }

    // =====================================================================
    // Stage5 — 西の斜面(林・法肩の松・榎・崖下の帯・勝手の坂・汀の柵と杭・葭・蓮)
    //
    // 【散布は生成器が撒く。ここは据えるだけ】⛔ **実装が撒き直さない。**
    //   指図の検査(見透しの窓の樹高の上限・対岸から見た二層・松が坂を貫かないか・
    //   木戸から `gateClearKen` の内に芯を置かない…)は、**生成器が撒いた点**に対して掛かっている。
    //   ここで別の乱数で撒くと、**検査を通った配置とシーンの配置が別物**になる
    //   (2026-09-02 岡部の言:「検査と散布を別々に書くと、検査が通って実装で 0 本になる」。
    //    松江松平はこの型を踏んで `planting_out.json` の焼き出しへ移した)。
    //   → 散布点は `okabe_impl.json` の `planting` から読む(裁定1=A の延長)。
    //
    // 【部材】崖下の帯の棟・丸太の手すり・汀の杭は**部材方が新造・登録中**(2026-09-04)。
    //   ⛔ 在庫で見繕って代用しない — 登録されるまでは据えずに一覧へ出す。
    // =====================================================================

    /// <summary>⚠ **部材方が新造・登録中**(2026-09-04)。登録されたら <see cref="AssetByKey"/> に
    /// 1行ずつ足す。⛔ それまで在庫の別物で代用しない(代用は在庫方の判断であって棟梁のではない)。</summary>
    static readonly string[] NishiPartsPending = {
        "ObiNagaya(len)  — 崖下の平屋長屋 N1/N2(7.5×2.5間・桟瓦・下見板腰・水側は盲面)",
        "ObiMonooki      — 物置 M1(3×1.5間)",
        "ObiKawaya       — かわや K_Obi(1×1間)",
        "MarutaTesuri    — 丸太の手すり(横木1段・丸太径 0.12)",
        "Kui(dia)        — 汀の杭(松の丸太・径 0.12〜0.18)",
    };

    /// <summary>植栽の部材のキーを解く。**キーは指図(算出物)が持ち、ここは辞書を引くだけ。**
    /// 書式は `族.名.寸法.個体`(例 `JG.Pine.Big.2` / `Own.Jouryoku.Mid.1`)。
    /// ⛔ **どの在庫の木がどの樹種を代表するかは在庫方の判断**で、ここで決めない
    ///   — 部材の doc も「指図の parts で個体を混ぜること」と求めている。</summary>
    static string PlantByKey(string key) { return PlantByKey(key, key); }
    static string PlantByKey(string key, string seedName)
    {
        if (string.IsNullOrEmpty(key)) return null;
        var t = key.Split('.');
        if (t.Length < 2) return null;
        string fam = t[0], nm = t[1];
        string size = t.Length > 2 ? t[2] : "Mid";
        // ⚠ 個体は `1` か `1-3`(範囲)で来る。⛔ **1本の層を1個体で埋めない**(部材の doc)ので、
        //   範囲なら **名前から決まる**個体を選ぶ(乱数ではないので何度流しても同じ)。
        //   ⭕ 個体を指図で決めたいときは範囲でなく単一の番号を書けばそちらが勝つ。
        int idx = 1;
        if (t.Length > 3)
        {
            string it = t[3];
            int dash = it.IndexOf('-');
            if (dash > 0)
            {
                int lo2, hi2;
                if (int.TryParse(it.Substring(0, dash), out lo2) &&
                    int.TryParse(it.Substring(dash + 1), out hi2) && hi2 >= lo2)
                    idx = lo2 + (StableHash(seedName) % (hi2 - lo2 + 1));
            }
            else int.TryParse(it, out idx);
        }
        if (idx < 1) idx = 1;
        if (fam == "JG")
        {
            if (nm == "Pine")    return EdoAssets.JG.Pine(size, idx);
            if (nm == "Bamboo")  return EdoAssets.JG.Bamboo(size, idx);   // ヤダケの代用(丈で縮める)
            if (nm == "Boxwood") return EdoAssets.JG.Boxwood(idx);
            if (nm == "Fern")    return EdoAssets.JG.Fern(idx);
        }
        else if (fam == "Own")
        {
            if (nm == "Jouryoku") return EdoAssets.Own.Jouryoku(size, idx);
            // ⚠ **同じ "Mid" でも樹種で樹高が違う**(エノキ13.5 / ムクノキ12 / ケヤキ14.5)。
            //    ⛔ 寸法の呼びを樹種を跨いで揃えない — 指図の h で倍率を掛けるので姿が崩れる
            if (nm == "Enoki")    return EdoAssets.Own.Enoki(size, idx);
            if (nm == "Mukunoki") return EdoAssets.Own.Mukunoki(size, idx);
            if (nm == "Keyaki")   return EdoAssets.Own.Keyaki(size, idx);
            // つる3種。⚠ 寸法の呼びを持たず**個体だけ**(`Own.TsuruFuji.1-3` の形で来る)
            if (nm == "TsuruFuji")   return EdoAssets.Own.TsuruFuji(idx);
            if (nm == "TsuruTeika")  return EdoAssets.Own.TsuruTeika(idx);
            if (nm == "TsuruKizuta") return EdoAssets.Own.TsuruKizuta(idx);
            if (nm == "Momiji")   return EdoAssets.Own.Momiji(size, idx);
            if (nm == "Ume")      return EdoAssets.Own.Ume(size, idx);
        }
        return null;
    }

    /// <summary>据えた現物の**ローカル軸での幅(+X)と奥行(+Z)**[m]。
    /// ⛔⛔ **world の AABB から出さない。**回した箱の AABB を走り方向へ射影すると
    /// `Lp + 2·D·|ux·uz|` になり、**奥行が長さに混ざる**(2026-09-04 に岡部の表長屋で
    /// +0.862m の水増しが出た。⚠ **長さに依らない項なので、複数の部材が揃って同じ差**を出す
    /// — それが「測り方の項」の合図)。⭕ 部材のローカル軸で測る(OBB)。</summary>
    static void ObbWD(GameObject go, out float wLocal, out float dLocal)
    {
        float mnx, mxx, mnz, mxz, mny;
        EdoBuild.ObbFootprint(go.transform, out mnx, out mxx, out mnz, out mxz, out mny);
        wLocal = mxx - mnx; dLocal = mxz - mnz;
        if (wLocal < 0f) wLocal = 0f;
        if (dLocal < 0f) dLocal = 0f;
    }

    /// <summary>据えた木の**幹径**[m]。根元の少し上(`y0`〜`y1` m)の帯で、幹の芯からの
    /// 半径の **90 分位**を取って 2 倍する。⚠ 最大だと低い枝や葉のカードを拾う。
    /// ⛔ 既定値で埋めない — つるを絡めてよい木かどうかがこの値で決まる。</summary>
    static float TrunkDiameter(GameObject host, float y0, float y1)
    {
        var b = EdoBuild.RB(host);
        float baseY = b.min.y;
        Vector2 axis = new Vector2(host.transform.position.x, host.transform.position.z);
        var rs = new List<float>();
        foreach (var mf in host.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null) continue;
            var m = mf.transform.localToWorldMatrix;
            var vs = mf.sharedMesh.vertices;
            for (int i = 0; i < vs.Length; i++)
            {
                var w = m.MultiplyPoint3x4(vs[i]);
                float dy = w.y - baseY;
                if (dy < y0 || dy > y1) continue;
                rs.Add((new Vector2(w.x, w.z) - axis).magnitude);
            }
        }
        if (rs.Count == 0) return 0f;
        rs.Sort();
        return 2f * rs[Mathf.Clamp(Mathf.RoundToInt(rs.Count * 0.90f) - 1, 0, rs.Count - 1)];
    }

    /// <summary>名前から決まる安定した非負の整数。⛔ 乱数ではない — 何度流しても同じ物が出る。
    /// (`string.GetHashCode` は .NET の版で変わるので使わない)</summary>
    static int StableHash(string s2)
    {
        int h = 17;
        if (s2 != null) for (int i = 0; i < s2.Length; i++) h = unchecked(h * 31 + s2[i]);
        return h < 0 ? -h : h;
    }

    /// <summary>部材の**素の丈**[m]。丈を指図の値へ合わせる倍率を出すのに使う。一度測って覚える。</summary>
    static Dictionary<string, float> _plantH = new Dictionary<string, float>();
    static float NaturalHeight(string path, Transform parent)
    {
        float h;
        if (_plantH.TryGetValue(path, out h)) return h;
        var probe = EdoBuild.Place(path, new Vector3(0, -9999f, 0), 0f, Vector3.one, parent, "__probe");
        h = probe == null ? 0f : EdoBuild.RB(probe).size.y;
        if (probe != null) UnityEngine.Object.DestroyImmediate(probe);
        _plantH[path] = h;
        return h;
    }

    [MenuItem("Edo/岡部筑前守上屋敷/5 西の斜面(林・松・帯・汀)")]
    public static void Stage5Menu() { Debug.Log("[Okabe] " + Stage5_Nishi()); }

    public static string Stage5_Nishi()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder();
        var wait = new List<string>();
        sb.AppendLine(PlantFromImpl(wait));
        sb.AppendLine(PlaceTesuri(wait));
        sb.AppendLine(PlaceKuiretsu(wait));
        sb.AppendLine(ReportNishiRest(wait));
        sb.AppendLine("── 据えなかったもの(部材待ち・欄待ち)" + wait.Count + " 件 ──");
        foreach (var w in wait) sb.AppendLine("  ★ " + w);
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 植栽
    /// <summary>**生成器が撒いた散布点を据えるだけ。**
    /// 期待する欄は <c>impl.planting[]</c>(素の配列。`{points:[…]}` でも受ける)=
    /// <c>{ name, zone, role, species, asset, u, v, h, tilt, tiltDir[2], ground }</c>。
    /// ・`asset` … 部材のキー(`JG.Pine.Big.2` など)。**どの在庫の木がどの樹種かは在庫方が決める**
    /// ・`h`     … 実際に置く丈[m]。⚠ 指図の `hMin`/`hMax` と窓の樹高の上限を**生成器が既に噛ませた後**の値
    /// ・`ground`… `design`(造成後の地盤)か `terrain`(現地形)
    /// ⛔ ここで丈を丸めたり、上限を当て直したりしない — 二重に判定すると図と食い違う。</summary>
    static string PlantFromImpl(List<string> wait)
    {
        // ⚠ 算出物は**素の配列**で来る(`{points:[…]}` ではない)。両方受ける
        var pts = A(Get(IMPL, "planting"));
        if (pts == null) { var pl0 = O(Get(IMPL, "planting")); pts = pl0 == null ? null : A(Get(pl0, "points")); }
        if (pts == null)
        {
            wait.Add("算出物に planting が無い — 林(高木72・中木160・低木22群・下草・つる・ヤダケ)/"
                   + "法肩の松15/榎3/ススキ の**散布点を生成器に焼かせること**"
                   + "(`--export-impl` に planting を足す)。⛔ 実装側で撒き直すと、"
                   + "指図の検査(窓の樹高の上限・対岸の二層・坂と木戸の離れ)が見た配置と別物になる");
            return "植栽: 算出物待ち";
        }
        var grp = Group("Nishi/Planting"); Clear(grp);
        var f = Grid;
        int made = 0, noPart = 0, noAsset = 0;
        var byZone = new Dictionary<string, int>();
        var missing = new HashSet<string>();
        // ⭐ **二巡する。**つるは絡む相手(`onTree`)の**据えた現物から幹径を測る**ので、
        //   一巡目で高木を据え、二巡目でつるを絡める。⛔ 順番を混ぜると宿主がまだ居ない。
        var placed = new Dictionary<string, GameObject>();
        var vines = new List<Dictionary<string, object>>();
        foreach (var o in pts)
        {
            var q = O(o); if (q == null) continue;
            string key = Has(q, "asset") ? S(q["asset"]) : null;
            if (key == null) { noAsset++; continue; }
            if (key.Contains("Tsuru")) { vines.Add(q); continue; }
            string path = PlantByKey(key, Has(q, "name") ? S(q["name"]) : key);
            if (path == null) { missing.Add(key); noPart++; continue; }
            Vector2 c = f.W(F(q["u"]), F(q["v"]));
            float y = S(Get(q, "ground")) == "terrain" ? EdoBuild.Ground(c.x, c.y) : Graded.At(c.x, c.y);
            if (float.IsNaN(y)) y = EdoBuild.Ground(c.x, c.y);
            var go = EdoBuild.Place(path, new Vector3(c.x, y, c.y), 0f, Vector3.one, grp,
                                    Has(q, "name") ? S(q["name"]) : (S(q["zone"]) + "_" + made));
            if (go == null) { missing.Add(key + " → " + path); noPart++; continue; }
            // 丈を指図の値へ合わせる(⛔ 部材の素の丈で置かない — 指図の hMin/hMax が意味を失う)
            float want = F(Get(q, "h")), nat = NaturalHeight(path, grp);
            if (want > 0.1f && nat > 0.1f) go.transform.localScale = Vector3.one * (want / nat);
            float tilt = F(Get(q, "tilt"));
            if (Mathf.Abs(tilt) > 0.01f)
            {
                var d2 = A(Get(q, "tiltDir"));
                Vector2 dir = (d2 != null && d2.Count == 2) ? new Vector2(F(d2[0]), F(d2[1])) : Vector2.up;
                Vector2 w2 = (f.W(dir.x, dir.y) - f.W(0f, 0f)).normalized;
                go.transform.rotation = Quaternion.AngleAxis(tilt, new Vector3(w2.y, 0f, -w2.x));
            }
            EdoBuild.SeatBottom(go, y);
            if (Has(q, "name")) placed[S(q["name"])] = go;
            made++;
            string z = S(Get(q, "zone")) ?? "?";
            byZone[z] = (byZone.ContainsKey(z) ? byZone[z] : 0) + 1;
        }
        // ---- 二巡目: つる(高木の幹に絡む)-------------------------------
        int vine = 0, vineSkip = 0;
        foreach (var q in vines)
        {
            string key = S(q["asset"]);
            string path = PlantByKey(key, Has(q, "name") ? S(q["name"]) : key);
            if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { missing.Add(key); noPart++; continue; }
            string hostName = Has(q, "onTree") ? S(q["onTree"]) : null;
            GameObject host = null;
            if (hostName == null || !placed.TryGetValue(hostName, out host))
            { vineSkip++; wait.Add("つる " + S(q["name"]) + ": 絡む高木 " + (hostName ?? "(onTree が無い)")
                                 + " が据わっていない — 据えない"); continue; }
            // ⭕ **幹径は宿主の据えた現物から測る**(⛔ 既定値で埋めない)。
            //   根元の少し上(0.30〜0.80m)の帯で、幹の芯からの半径の 90 分位を取る
            //   (⚠ 最大だと低い枝や葉のカードを拾う)。
            float dia = TrunkDiameter(host, 0.30f, 0.80f);
            float tmin = Has(q, "trunkMin") ? F(q["trunkMin"]) : 0.40f;
            float tmax = Has(q, "trunkMax") ? F(q["trunkMax"]) : 0.85f;
            if (dia < tmin || dia > tmax)
            {
                vineSkip++;
                wait.Add("つる " + S(q["name"]) + "(" + S(Get(q, "species")) + "): 宿主 " + hostName
                       + " の幹径 " + dia.ToString("F3") + "m が指図の " + tmin.ToString("0.##") + "〜"
                       + tmax.ToString("0.##") + "m の外 — ⛔ **据えない**(細い木に太いつるを巻かない)");
                continue;
            }
            float tref = Has(q, "trunkRef") ? F(q["trunkRef"]) : 0.60f;
            float ys = Has(q, "yScatter") ? F(q["yScatter"]) : 0.25f;
            // 位置は宿主の足元(算出物の world / u,v はその点)
            Vector2 c2 = f.W(F(q["u"]), F(q["v"]));
            float y2 = S(Get(q, "ground")) == "terrain" ? EdoBuild.Ground(c2.x, c2.y) : Graded.At(c2.x, c2.y);
            if (float.IsNaN(y2)) y2 = EdoBuild.Ground(c2.x, c2.y);
            // ⭕ yaw は**算出物が持つ**(種で決めた値)。⛔ 実装で振らない
            var gv = EdoBuild.Place(path, new Vector3(c2.x, y2, c2.y), F(Get(q, "yaw")),
                                    Vector3.one, grp, S(q["name"]));
            if (gv == null) { noPart++; continue; }
            float natv = NaturalHeight(path, grp), wantv = F(Get(q, "h"));
            float sy = 1f;
            if (wantv > 0.1f && natv > 0.1f) sy = Mathf.Clamp(wantv / natv, 1f - ys, 1f + ys);
            // ⛔ 一様スケールにしない — XZ は幹径へ、Y は丈へ別々に合わせる
            gv.transform.localScale = new Vector3(dia / tref, sy, dia / tref);
            EdoBuild.SeatBottom(gv, y2);
            vine++;
        }
        if (vine + vineSkip > 0)
            byZone["つる"] = vine;

        foreach (var k in missing)
            wait.Add("植栽の部材のキーが解けない: " + k + " — 在庫方が `impl.planting.points[].asset` の"
                   + "書式(族.名.寸法.個体)で名指しすること");
        if (noAsset > 0)
            wait.Add("散布点 " + noAsset + " 件に asset が無い — **どの在庫の木がどの樹種を代表するか**は"
                   + "在庫方の判断。⛔ 実装で見繕わない");
        var sb = new System.Text.StringBuilder("植栽: " + made + " 本据えた");
        foreach (var kv in byZone) sb.Append(" / " + kv.Key + " " + kv.Value);
        if (noPart > 0) sb.Append(" ｜ 部材が引けず据えられない " + noPart);
        if (vineSkip > 0) sb.Append(" ｜ つる 据えず " + vineSkip);
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 丸太の手すり
    /// <summary>勝手の道が**法肩の竹垣の外(池側)を通る区間**の落下止め
    /// (2026-09-03 ユーザー裁定1=A)。⛔ 竹垣にしない — 丸太の横木1段で、垣ではない
    /// (法肩の竹垣と読み違えると、宣言した「垣の外を通る区間」の意味が消える)。</summary>
    static string PlaceTesuri(List<string> wait)
    {
        Dictionary<string, object> orl = null;
        foreach (var o in A(Get(D, "routes")) ?? new List<object>())
        { var r = O(o); if (r != null && Has(r, "outsideRail")) orl = O(r["outsideRail"]); }
        if (orl == null) return "丸太の手すり: 指図に routes[].outsideRail が無い";
        var ts = O(Get(orl, "tesuri"));
        if (ts == null) return "丸太の手すり: outsideRail.tesuri が無い";
        // 部材方が**この区間のために**焼いた物(部材の doc が routes.R_Katte.outsideRail.tesuri を名指し)
        string path = AssetByKey(Has(ts, "asset") ? S(ts["asset"]) : "Own.MarutaTesuri");
        string post = EdoAssets.Own.MarutaTesuriPost;
        if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
        { wait.Add("丸太の手すり: 部材が引けない " + (path ?? "?")); return "丸太の手すり: 部材待ち"; }

        var grp = Group("Nishi/Tesuri"); Clear(grp);
        var f = Grid;
        float uF = F(orl["uFrom"]), uT = F(orl["uTo"]), v = F(orl["v"]);
        float pitch = F(ts["postPitchKen"]);                     // 芯々[間]
        int n = Mathf.Max(1, Mathf.RoundToInt(Mathf.Abs(uT - uF) / Mathf.Max(0.1f, pitch)));
        int made = 0;
        // ⚠ ピボットは**スパンの中心**で柱は −X 端に立つ。⇒ 各スパンの中点へ据える
        for (int i = 0; i < n; i++)
        {
            float u = Mathf.Lerp(uF, uT, (i + 0.5f) / n);
            Vector2 c = f.W(u, v);
            float y = Graded.At(c.x, c.y); if (float.IsNaN(y)) y = EdoBuild.Ground(c.x, c.y);
            var go = EdoBuild.Place(path, new Vector3(c.x, y, c.y), YawTo(uT - uF, 0f), Vector3.one,
                                    grp, "Tesuri_" + i);
            if (go != null) { EdoBuild.SeatBottom(go, y); made++; }
        }
        // ⛔ run の +X 端に柱を1本足す(足さないと最後の横木が宙で終わる — 部材の doc)
        {
            Vector2 c = f.W(uT, v);
            float y = Graded.At(c.x, c.y); if (float.IsNaN(y)) y = EdoBuild.Ground(c.x, c.y);
            var go = EdoBuild.Place(post, new Vector3(c.x, y, c.y), YawTo(uT - uF, 0f), Vector3.one,
                                    grp, "Tesuri_EndPost");
            if (go != null) { EdoBuild.SeatBottom(go, y); made++; }
        }
        return "丸太の手すり: " + made + " 点(スパン " + n + " + 端柱1)";
    }

    // ---------------------------------------------------------------- 汀の杭列
    /// <summary>汀線に沿う松の丸太杭。⭐ **本数は汀線の実長から算出する**(⛔ 辺5の長さを流用しない
    /// — 2026-09-03 庭方4巡目)。汀線・径・頭の高さ・傾きの方位は**生成器が `impl.kui` へ焼く**。
    /// ⚠ ピボットは**頭の芯**で杭は −Y へ 1.55 垂れるので、`y` に頭の高さを直に入れる。
    /// 傾き 5° は +X へ焼き込んであるので、**yaw を振れば傾きの方位が散る**。
    /// ⛔ 実装で乱数を振らない — 図と食い違う。</summary>
    static string PlaceKuiretsu(List<string> wait)
    {
        var kr = O(Get(O(Get(D, "nishi")), "kuiretsu"));
        if (kr == null) return "汀の杭列: 指図に nishi.kuiretsu が無い";
        var pts = A(Get(IMPL, "kui"));
        if (pts == null)
        {
            var tt0 = O(Get(O(Get(D, "nishi")), "tsutsumi"));
            wait.Add("算出物に kui が無い — 汀線(堤の天端から法 1:"
                   + (tt0 != null ? F(tt0["batter"]).ToString("0.##") : "?") + " で水面 "
                   + (tt0 != null ? F(tt0["waterY"]).ToString("0.##") : "?")
                   + "m まで)と、その実長に沿う杭の**位置・径・頭の高さ・傾きの方位**を"
                   + "生成器に焼かせること(指図は諸元の範囲だけを持ち、本数は算出値)");
            return "汀の杭列: 算出物待ち";
        }
        var grp = Group("Nishi/Kui"); Clear(grp);
        var f = Grid;
        int made = 0, nuki = 0; var missing = new HashSet<string>();
        float below = F(Get(O(Get(kr, "nuki")), "below"));
        foreach (var o in pts)
        {
            var k = O(o); if (k == null) continue;
            var w = A(Get(k, "world"));
            Vector2 c;
            if (w != null && w.Count >= 2) c = new Vector2(F(w[0]), F(w[1]));
            else if (Has(k, "u")) c = f.W(F(k["u"]), F(k["v"]));
            else continue;
            float dia = F(Get(k, "dia"));
            string path = EdoAssets.Own.Kui(dia);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { missing.Add(dia.ToString("0.00")); continue; }
            float top = Has(k, "topY") ? F(k["topY"]) : F(Get(k, "top"));   // 頭の高さ
            // ⚠ 傾き 5° は部材の **+X へ焼き込んである**ので、yaw を振れば傾きの方位が散る。
            //   算出物が yaw を持たないので**名前から決まる向き**を使う(⛔ 乱数ではない)。
            float yaw = Has(k, "yaw") ? F(k["yaw"]) : (StableHash(S(Get(k, "name"))) % 360);
            var go = EdoBuild.Place(path, new Vector3(c.x, top, c.y), yaw, Vector3.one, grp,
                                    Has(k, "name") ? S(k["name"]) : "Kui_" + made);
            if (go != null) made++;
            // 貫 — 頭から `nuki.below` 下。⚠ 指図の「杭ごと1段」は部材が数千本になるので
            //      部材方が 1間の丸太1本として出した(据えるのは杭の並びに沿って)
            if (Has(k, "nukiY") || (Has(k, "nuki") && below > 0f))
            {
                float ny = Has(k, "nukiY") ? F(k["nukiY"]) : top - below;
                var gn = EdoBuild.Place(EdoAssets.Own.KuiNuki, new Vector3(c.x, ny, c.y),
                                        yaw, Vector3.one, grp, "Nuki_" + nuki);
                if (gn != null) nuki++;
            }
        }
        if (missing.Count > 0)
            wait.Add("汀の杭: 焼かれていない径 " + string.Join(" / ", new List<string>(missing).ToArray())
                   + " → build_maruta.py -- kui");
        return "汀の杭列: " + made + " 本(貫 " + nuki + ")";
    }

    // ---------------------------------------------------------------- 残り(地表・部材待ち)
    /// <summary>西の斜面のうち、**据える物が無い**か**部材待ち**のものを一覧に出す。
    /// ⛔ 黙って落とすと「S5 は通った」のに何も無い、という状態が見えなくなる。</summary>
    static string ReportNishiRest(List<string> wait)
    {
        var n = O(Get(D, "nishi"));
        if (n == null) return "西の斜面: 指図に nishi が無い";
        // 崖下の帯の棟 — 行は service[] にあるので据えるのは S3。ここでは部材の要件だけ渡す
        var obi = O(Get(n, "obi"));
        if (obi != null)
        {
            var rf = O(Get(O(Get(D, "roofs")), "ObiNagaya"));
            wait.Add("崖下の帯の棟(N1・N2・M1・かわや)は `service[]` の行なので据えるのは S3。"
                   + "部材の要件: " + (rf == null ? "roofs.ObiNagaya が無い"
                     : S(rf["kawara"]) + "・" + S(rf["kai"]) + "・腰は" + S(rf["koshi"])
                     + "・軒高 " + F(rf["eaveH"]).ToString("0.##") + "・棟高 " + F(rf["ridgeH"]).ToString("0.##")
                     + "・水側(西)は盲面")
                   + " / 軒の出 " + F(Get(obi, "nokiOut")).ToString("0.##") + "m");
        }
        // 見透しの窓・葭・蓮・坂の路面 — いずれも地表の塗りと草
        var mado = O(Get(n, "mado"));
        if (mado != null)
            wait.Add("見透しの窓の地表(" + S(Get(mado, "ground")) + ")は**地表の巡**で塗る。"
                   + "⛔ どの地表層で塗るかが指図に無い(窓・法尻の草地・勝手の坂の土の道の3つとも)");
        var tt = O(Get(n, "tsutsumi"));
        if (tt != null)
            wait.Add("葭(幅 " + F(O(tt["yoshi"])["wMin"]).ToString("0.##") + "〜"
                   + F(O(tt["yoshi"])["wMax"]).ToString("0.##") + "m)と蓮(汀から沖へ "
                   + F(O(tt["hasu"])["fromM"]).ToString("0.##") + "〜" + F(O(tt["hasu"])["toM"]).ToString("0.##")
                   + "m)は**区画の外の水域**。地表と草の層で受けるので S5 では据えない。"
                   + "⚠ 蓮は池床が " + F(O(tt["hasu"])["bedYMin"]).ToString("0.##")
                   + "m より上であることが前提 — 溜池の普請へ渡す越境の件");
        // 勝手の坂 — 土工は S1(graded_y)に入っている。路面は地表
        foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
        {
            var r = O(o); if (r == null || S(r["name"]) != "R_SakaObi") continue;
            wait.Add("勝手の坂 R_SakaObi(幅 " + F(r["w"]).ToString("0.##") + "m・全長 "
                   + F(O(Get(r, "measured"))["len"]).ToString("0.#") + "m)は**土の道で路盤は地盤なり**。"
                   + "土工は S1 の造成に入っているので、S5 で据える物は無い(路面の塗りは地表の巡)");
        }
        foreach (var s2 in NishiPartsPending)
            wait.Add("部材待ち(部材方が新造・登録中): " + s2);
        return "西の斜面: 据える物のない項目と部材待ちを一覧へ出した";
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
                    // ⭕ 2026-09-04 裁定12=A で表長屋も S2 で建つようになった。
                    //    ⛔ 練塀だけを「実装の被覆」に数えると、建っている 79.66m を素通しと報告する
                    impl.Add(new Iv { a = r.s0, b = r.s1 });
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
        // run の s1 と辺長の関係。⚠ **「はみ出し」を2つの意味で使わない**(2026-09-04 指図方):
        //   ・**めり込み**(s1 > 辺長)… 出隅で**必要**。隣の run と突き合わせず食い込ませるのが作法
        //     (メモリ『門と塀の閉じは隙間>めり込み』/ スキル `unity-modular-stonewall` §R4)。
        //     ⭕ 欠陥ではないので ★ にしない。
        //   ・**越境**(足跡が区画の外へ出る)… こちらが欠陥。⚠ s では測れない —
        //     据えた足跡で測るもので、許容は `const.kidan.cornerOutTolM`。
        {
            var mekomi = new List<string>();
            foreach (var r in Runs)
            {
                float over = r.s1 - EdgeLen(r.edge);
                if (over > 0.005f)
                    mekomi.Add(string.Format("{0} 辺{1} +{2:F3}m", r.name, r.edge, over));
            }
            if (mekomi.Count > 0)
                sb.AppendLine("  ℹ 出隅のめり込み(s1 > 辺長・**正常**)" + mekomi.Count + " 件: "
                            + string.Join(" / ", mekomi.ToArray())
                            + "\n     ⚠ 越境(区画の外へ出たか)は s では測れない — 据えた足跡で測る"
                            + "(許容 const.kidan.cornerOutTolM)");
        }
        sb.Append(bad == 0 ? "  0 件 ✔" : "  ★ " + bad + " 件 — 指図を parcels.json へ同期し直すこと(2026-09-03 裁定2=A)");
        return sb.ToString();
    }

    // =====================================================================
    // 算出物の自己検査 — **Unity の場面にも地形にも触らない**
    //
    // ⭐ 生成器が焼いた `okabe_impl.json` が、指図の宣言と噛み合っているかだけを見る。
    //   地形も現物も読まないので、**merge を待っている間でも・造成の前でも走る**。
    // ⚠ これが無いと、焼き損じ(格子が区画を覆っていない・杭が汀線から外れている・
    //   松が木戸の余裕を侵している)が**据えてみるまで分からない**。安い輪で捕まえる
    //   べきものを、高い輪(実装・ユーザーの目)に見つけさせないための関門。
    //   → `docs/verification-loops.md`(CLAUDE.md 規則19)
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/算出物を検める")]
    public static void ImplQAMenu() { Debug.Log("[Okabe] " + ImplQA()); }

    /// <summary>算出物 `okabe_impl.json` の自己検査。**場面にも地形にも触らない**ので
    /// `execute_code` からでもコマンドラインからでも同じ結果になる。
    /// 返り値は人が読む報告。⛔ 項目を足したら「何を測ったか」を文言に必ず書くこと
    /// (「共有辺」と書いて全辺を回す類の嘘を作らない — 2026-08 の検査の教訓)。</summary>
    public static string ImplQA()
    {
        Reload();
        var sb = new System.Text.StringBuilder("算出物の検め(場面・地形に触らない)\n");
        int bad = 0;
        System.Action<string> ng = delegate(string m) { sb.Append("  ★ ").Append(m).Append('\n'); bad++; };
        System.Action<string> ok = delegate(string m) { sb.Append("  ✔ ").Append(m).Append('\n'); };

        Dictionary<string, object> im;
        try { im = IMPL; }
        catch (Exception ex) { return sb.Append("  ★ ").Append(ex.Message).Append('\n').ToString(); }

        // ---- ① 指紋 --------------------------------------------------
        var src = O(Get(im, "src"));
        if (src == null || !Has(src, "sha256")) ng("src.sha256 が無い — 指図との対応を機械で確かめられない");
        else ok("src.sha256 が指図と一致(" + S(src["sha256"]).Substring(0, 12) + "…)");
        // ⚠ 不一致なら IMPL の getter が例外を投げているので、ここへ来た時点で一致している

        var P = Poly;
        var f = Grid;

        // ---- ② 造成後の地盤の格子が区画を覆うか ------------------------
        {
            var g = O(Get(im, "graded"));
            if (g == null) ng("graded が無い");
            else
            {
                float x0 = F(g["x0"]), z0 = F(g["z0"]), st = F(g["step"]);
                int nx = (int)F(g["nx"]), nz = (int)F(g["nz"]);
                float x1 = x0 + (nx - 1) * st, z1 = z0 + (nz - 1) * st;
                float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                foreach (var q in P)
                { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
                if (x0 > mnx || x1 < mxx || z0 > mnz || z1 < mxz)
                    ng(string.Format("graded の格子が区画の外接矩形を覆っていない 格子[{0:F1}〜{1:F1}, {2:F1}〜{3:F1}] / 区画[{4:F1}〜{5:F1}, {6:F1}〜{7:F1}]",
                        x0, x1, z0, z1, mnx, mxx, mnz, mxz));
                // 区画の中の節点に穴が無いか(=区画内で null を返さない)
                int hole = 0, inN = 0; Vector2 worst = Vector2.zero;
                for (int j = 0; j < nz; j++)
                    for (int i = 0; i < nx; i++)
                    {
                        var q = new Vector2(x0 + i * st, z0 + j * st);
                        if (!EdoGeom.PIP(P, q)) continue;
                        inN++;
                        if (float.IsNaN(Graded.At(q.x, q.y))) { hole++; worst = q; }
                    }
                if (hole > 0) ng(string.Format("graded に区画内の穴 {0} / {1} 節点(例 {2:F1},{3:F1})", hole, inN, worst.x, worst.y));
                else ok(string.Format("graded は区画内 {0} 節点すべてに値がある(格子 {1:F2}m)", inN, st));
            }
        }

        // ---- ③ 隅の留め継ぎが区画の頂点に一致するか --------------------
        {
            var cs = A(Get(im, "corners"));
            if (cs == null) ng("corners が無い");
            else
            {
                int n = 0; float mx = 0f; string worst = null;
                foreach (var o in cs)
                {
                    var c = O(o); if (c == null) continue;
                    int v = (int)F(c["vertex"]);
                    if (v < 0 || v >= P.Length) { ng("corner " + S(c["id"]) + " の vertex " + v + " が区画の頂点数 " + P.Length + " の外"); continue; }
                    var w = A(Get(c, "world"));
                    if (w == null || w.Count < 2) { ng("corner " + S(c["id"]) + " に world が無い"); continue; }
                    float d = (new Vector2(F(w[0]), F(w[1])) - P[v]).magnitude;
                    if (d > mx) { mx = d; worst = S(c["id"]); }
                    n++;
                }
                if (mx > 0.01f) ng(string.Format("corners の world が頂点と最大 {0:F3}m ずれ(@{1})— 指図の polygon を parcels.json へ同期し直すこと", mx, worst));
                else ok("corners " + n + " 件は区画の頂点に一致(最大 " + mx.ToString("F3") + "m)");
            }
        }

        // ---- ④ 基壇の区間が run の中か --------------------------------
        {
            var bs = A(Get(im, "base"));
            if (bs == null) ng("base が無い");
            else
            {
                var byName = new Dictionary<string, Run>();
                foreach (var r in Runs) byName[r.name] = r;
                int n = 0, outside = 0;
                foreach (var o in bs)
                {
                    var b = O(o); if (b == null) continue;
                    string nm = S(b["run"]);
                    if (!byName.ContainsKey(nm)) { ng("base の run " + nm + " が指図の runs に無い"); continue; }
                    var r = byName[nm];
                    if (Has(b, "s") && Mathf.Abs(F(b["s"]) - r.s) > 1e-4f)
                        ng("base " + nm + " の倍率 s=" + F(b["s"]).ToString("0.##") + " が指図の run の s=" + r.s.ToString("0.##") + " と違う");
                    foreach (var q in A(Get(b, "segs")) ?? new List<object>())
                    {
                        var t2 = A(q); if (t2 == null || t2.Count != 2) continue;
                        n++;
                        if (F(t2[0]) < r.s0 - 0.01f || F(t2[1]) > r.s1 + 0.01f)
                        { ng(string.Format("base {0} の区間 [{1:F2},{2:F2}] が run の [{3:F2},{4:F2}] の外", nm, F(t2[0]), F(t2[1]), r.s0, r.s1)); outside++; }
                    }
                }
                if (outside == 0) ok("base の区間 " + n + " 本はすべて run の中");
            }
        }

        // ---- ⑤ 法肩の竹垣が段の縁に載るか ------------------------------
        {
            var rs = A(Get(im, "rails"));
            if (rs == null) ng("rails が無い — 法肩の竹垣は生成器の算出値で、指図の json は持たない");
            else
            {
                float off = (C("inubashiri") + C("takegakiInset")) / C("ken");   // 縁から内へ(間)
                int n = 0, far = 0; float mx = 0f; string worst = null;
                foreach (var o in rs)
                {
                    var r = O(o); if (r == null) continue;
                    var pts = A(Get(r, "world"));
                    if (pts == null) { ng("rail " + S(r["name"]) + " に world が無い(実装は世界座標の折れ線を使う)"); continue; }
                    foreach (var q in pts)
                    {
                        var w = A(q); if (w == null || w.Count < 2) continue;
                        var uv = f.L(new Vector2(F(w[0]), F(w[1])));
                        float d = Mathf.Abs(TerraceRingDist(uv) - off);
                        n++;
                        if (d > mx) { mx = d; worst = S(r["name"]); }
                        if (d > 0.30f) far++;      // 0.30間 = 0.55m
                    }
                }
                if (far > 0) ng(string.Format("rails の折れ点 {0}/{1} が段の縁から {2:F2}間 の位置に無い(最大ずれ {3:F2}間 @{4})", far, n, off, mx, worst));
                else ok(string.Format("rails の折れ点 {0} 点は段の縁から {1:F2}間 に載る(最大ずれ {2:F2}間)", n, off, mx));
            }
        }

        // ---- ⑥ 植栽の点 ------------------------------------------------
        {
            // ⚠ 算出物は**素の配列**で来る(`{points:[…]}` ではない)。両方受ける
            var pts = A(Get(im, "planting"));
            if (pts == null) { var pl = O(Get(im, "planting")); pts = pl == null ? null : A(Get(pl, "points")); }
            if (pts == null) ng("planting が無い — 林・法肩の松・榎・ススキの散布点を生成器に焼かせること");
            else
            {
                int n = 0, outP = 0, badH = 0, noDecl = 0, gateHit = 0;
                float gateU = 0f, gateClear = 0f; bool hasGate = false;
                var hk = O(Get(O(Get(D, "nishi")), "hokata"));
                if (hk != null && Has(hk, "gateU"))
                {
                    var gu = A(hk["gateU"]);
                    if (gu != null && gu.Count > 0) { gateU = F(gu[0]); gateClear = F(hk["gateClearKen"]); hasGate = true; }
                }
                foreach (var o in pts)
                {
                    var q = O(o); if (q == null) continue;
                    n++;
                    float u = F(q["u"]), v = F(q["v"]);
                    Vector2 w = f.W(u, v);
                    if (!EdoGeom.PIP(P, w)) outP++;
                    float lo, hi;
                    if (!HeightRange(S(Get(q, "zone")), S(Get(q, "role")), S(Get(q, "species")), S(Get(q, "name")), out lo, out hi))
                        noDecl++;
                    else
                    {
                        float h = F(Get(q, "h"));
                        if (h < lo - 0.01f || h > hi + 0.01f) badH++;
                    }
                    if (hasGate && S(Get(q, "zone")) == "hokata" && Mathf.Abs(u - gateU) < gateClear - 1e-4f) gateHit++;
                }
                if (outP > 0) ng("planting の点 " + outP + " / " + n + " が区画の外");
                else ok("planting の点 " + n + " はすべて区画の中");
                if (badH > 0) ng("planting の丈 " + badH + " 件が指図の hMin〜hMax の外");
                else ok("planting の丈は宣言の範囲の中(丈の宣言が無い層 " + noDecl + " 件は測っていない)");
                if (gateHit > 0) ng(string.Format("法肩の松 {0} 本が木戸(u={1:F2})の余裕 {2:F2}間 を侵している", gateHit, gateU, gateClear));
                else if (hasGate) ok(string.Format("法肩の松は木戸(u={0:F2})から {1:F2}間 を空けている", gateU, gateClear));
            }
        }

        // ---- ⑦ 汀の杭が汀線に載るか ------------------------------------
        {
            var ks = A(Get(im, "kui"));
            var tt = O(Get(O(Get(D, "nishi")), "tsutsumi"));
            var kr = O(Get(O(Get(D, "nishi")), "kuiretsu"));
            if (ks == null) ng("kui が無い — 汀線と杭(位置・径・頭・傾き・貫)を生成器に焼かせること");
            else if (tt == null || kr == null) ng("指図に nishi.tsutsumi / kuiretsu が無い");
            else
            {
                int e = (int)F(kr["edge"]);
                // ⚠ **汀線は辺から一定の距離ではない。**堤の天端 `y0Line` は u ごとに違い、
                //   汀は「天端から法 1:batter で水面まで下った水平距離」なので、**その点の天端**で決まる。
                //   ⛔ 代表値 `mizugiwaM` の一定オフセットで測ると、天端が低い両端で数 m の偽陽性が出る
                //   (2026-09-04 に実測 36/242 本・最大 5.30m — 検査の側の誤りだった)。
                float batter = F(tt["batter"]), waterY = F(tt["waterY"]);
                var y0L = A(Get(tt, "y0Line"));
                System.Func<float, float> y0At = delegate(float u)
                {
                    // ⚠ **線形に内挿する。**最寄りの標本で代用すると、天端が急に変わる両端で
                    //   数 m の偽陽性が出る(2026-09-04 実測 51/242 本・最大 5.16m)。
                    if (y0L == null || y0L.Count == 0) return F(Get(tt, "y0"));
                    float pu = 0f, py = 0f; bool first = true;
                    foreach (var q in y0L)
                    {
                        var t3 = A(q); if (t3 == null || t3.Count < 2) continue;
                        float cu = F(t3[0]), cy = F(t3[1]);
                        if (first) { if (u <= cu) return cy; pu = cu; py = cy; first = false; continue; }
                        if (u <= cu)
                            return Mathf.Abs(cu - pu) < 1e-6f ? cy : Mathf.Lerp(py, cy, (u - pu) / (cu - pu));
                        pu = cu; py = cy;
                    }
                    return py;
                };
                Vector2 nrm = OutNormal(e);
                int n = 0, far = 0; float mx = 0f;
                float dMin = F(kr["dMin"]), dMax = F(kr["dMax"]);
                int badD = 0;
                foreach (var o in ks)
                {
                    var k = O(o); if (k == null) continue;
                    n++;
                    var w = A(Get(k, "world"));
                    Vector2 c;
                    if (w != null && w.Count >= 2) c = new Vector2(F(w[0]), F(w[1]));
                    else if (Has(k, "u")) c = f.W(F(k["u"]), F(k["v"]));
                    else { ng("kui に world も u/v も無い"); break; }
                    // その点の u における汀線 = 辺を外へ (天端 − 水面)×batter 出した点
                    var uv = f.L(c);
                    float off = Mathf.Max(0f, (y0At(uv.x) - waterY) * batter);
                    // 辺の上での最寄り点を求め、そこから法線方向へ off 出した所と比べる
                    Vector2 pa = P[e % P.Length], pb = P[(e + 1) % P.Length];
                    Vector2 dv2 = pb - pa; float L2 = dv2.sqrMagnitude;
                    float t4 = L2 < 1e-9f ? 0f : Mathf.Clamp01(Vector2.Dot(c - pa, dv2) / L2);
                    Vector2 target = pa + dv2 * t4 + nrm * off;
                    float d = (c - target).magnitude;
                    if (d > mx) mx = d;
                    if (d > 0.60f) far++;
                    float dia = F(Get(k, "dia"));
                    if (dia > 0f && (dia < dMin - 1e-4f || dia > dMax + 1e-4f)) badD++;
                }
                // ⚠ **これは合否ではない。**汀線を当方で引き直した模型との差でしかなく、
                //   ⛔ 検査が自分の模型を正典に据えてはならない — 汀線を算出するのは生成器(裁定1=A)。
                //   ⭕ 生成器が `impl.migiwa`(汀線の折れ線)を出せば、そこで初めて合否になる。
                if (A(Get(im, "migiwa")) != null)
                {
                    if (far > 0) ng(string.Format("kui {0}/{1} 本が算出物の汀線から 0.60m 以上離れている(最大 {2:F2}m)", far, n, mx));
                    else ok(string.Format("kui {0} 本は算出物の汀線に載る(最大 {1:F2}m)", n, mx));
                }
                else
                    ok(string.Format("kui {0} 本(当方の模型との差 最大 {1:F2}m・{2} 本が 0.60m 超)"
                      + " ⚠ **合否にしていない** — 汀線は生成器が算出するもので、当方は引き直せない。"
                      + "`impl.migiwa`(汀線の折れ線)を焼いてもらえば合否になる", n, mx, far));
                // ⛔ 指図は「径・芯々は不同・不等(等間隔にしない)」と明記する。⭕ 実際に散っているか測る
                {
                    float pmin = float.MaxValue, pmax = 0f; int np = 0;
                    for (int i2 = 1; i2 < ks.Count; i2++)
                    {
                        var k1 = O(ks[i2 - 1]); var k2 = O(ks[i2]);
                        var w1 = A(Get(k1, "world")); var w2 = A(Get(k2, "world"));
                        if (w1 == null || w2 == null) continue;
                        float dd3 = (new Vector2(F(w1[0]), F(w1[1])) - new Vector2(F(w2[0]), F(w2[1]))).magnitude;
                        pmin = Mathf.Min(pmin, dd3); pmax = Mathf.Max(pmax, dd3); np++;
                    }
                    if (np > 0)
                    {
                        float want = F(kr["pitchMax"]) - F(kr["pitchMin"]);
                        if (pmax - pmin < want * 0.25f)
                            ng(string.Format("kui の芯々がほぼ等間隔({0:F3}〜{1:F3}m・幅 {2:F3})— "
                              + "指図は {3:F2}〜{4:F2}m の**不等**を求めている(⛔ 等間隔にしない)",
                              pmin, pmax, pmax - pmin, F(kr["pitchMin"]), F(kr["pitchMax"])));
                        else ok(string.Format("kui の芯々は不等({0:F2}〜{1:F2}m)", pmin, pmax));
                    }
                }
                if (badD > 0) ng("kui の径 " + badD + " 本が指図の " + dMin.ToString("0.##") + "〜" + dMax.ToString("0.##") + "m の外");
            }
        }

        sb.Append(bad == 0 ? "→ 0 件 ✔ 算出物は指図と噛み合っている" : "→ ★ " + bad + " 件");
        return sb.ToString();
    }

    /// <summary>点(グリッド座標)から**段の輪郭**(外輪・抜き・keeps)までの最短距離[間]。
    /// 法肩の竹垣は縁から内へ一定量入った所に立つので、その検算に使う。</summary>
    static float TerraceRingDist(Vector2 uv)
    {
        float best = float.MaxValue;
        foreach (var o in A(D["terraces"]) ?? new List<object>())
        {
            var t = O(o); if (t == null) continue;
            best = Mathf.Min(best, RingDist(A(Get(t, "poly")), uv));
            foreach (var h in A(Get(t, "holes")) ?? new List<object>())
            { var hh = O(h); if (hh != null) best = Mathf.Min(best, RingDist(A(Get(hh, "poly")), uv)); }
            foreach (var k in A(Get(t, "keeps")) ?? new List<object>())
                best = Mathf.Min(best, RingDist(A(k), uv));
        }
        return best;
    }
    static float RingDist(List<object> ring, Vector2 p)
    {
        if (ring == null || ring.Count < 2) return float.MaxValue;
        float best = float.MaxValue;
        for (int i = 0; i < ring.Count; i++)
        {
            var a = A(ring[i]); var b = A(ring[(i + 1) % ring.Count]);
            if (a == null || b == null || a.Count < 2 || b.Count < 2) continue;
            best = Mathf.Min(best, DistSeg(p, new Vector2(F(a[0]), F(a[1])), new Vector2(F(b[0]), F(b[1]))));
        }
        return best;
    }
    static float DistSeg(Vector2 p, Vector2 a, Vector2 b)
    {
        Vector2 d = b - a; float L2 = d.sqrMagnitude;
        if (L2 < 1e-9f) return (p - a).magnitude;
        float t = Mathf.Clamp01(Vector2.Dot(p - a, d) / L2);
        return (p - (a + d * t)).magnitude;
    }

    /// <summary>指図が**宣言している丈の範囲**を引く。⛔ 宣言の無い層に既定の範囲を当てない
    /// — 当てると「検査を通った」ことになるが、実際には何も検めていない。</summary>
    static bool HeightRange(string zone, string role, string species, string name, out float lo, out float hi)
    {
        lo = hi = 0f;
        var n = O(Get(D, "nishi")); if (n == null) return false;
        if (zone == "hayashi")
        {
            var hy = O(Get(n, "hayashi")); if (hy == null) return false;
            if (role == "高木" || role == "takagi")
                foreach (var o in A(Get(hy, "takagi")) ?? new List<object>())
                {
                    var t = O(o);
                    if (t != null && S(t["species"]) == species) { lo = F(t["hMin"]); hi = F(t["hMax"]); return true; }
                }
            if (role == "ヤダケ" || role == "yadake")
            { var y = O(Get(hy, "yadake")); if (y != null) { lo = F(y["hMin"]); hi = F(y["hMax"]); return true; } }
            return false;
        }
        if (zone == "hokata")
        { var hk = O(Get(n, "hokata")); if (hk != null) { lo = F(hk["hMin"]); hi = F(hk["hMax"]); return true; } return false; }
        if (zone == "hojiri")
        {
            var hj = O(Get(n, "hojiri")); if (hj == null) return false;
            if (role == "榎" || role == "enoki")
                foreach (var o in A(Get(hj, "enoki")) ?? new List<object>())
                {
                    var t = O(o);
                    if (t != null && S(t["name"]) == name) { lo = F(t["hMin"]); hi = F(t["hMax"]); return true; }
                }
            if (role == "ススキ" || role == "susuki")
            { var su = O(Get(hj, "susuki")); if (su != null) { lo = F(su["hMin"]); hi = F(su["hMax"]); return true; } }
            return false;
        }
        if (zone == "mado")
        {
            var md = O(Get(n, "mado")); if (md == null) return false;
            if (role == "ススキ" || role == "susuki")
            { var su = O(Get(md, "susuki")); if (su != null) { lo = F(su["hMin"]); hi = F(su["hMax"]); return true; } }
            if (role == "松" || role == "matsu")
                foreach (var o in A(Get(md, "matsu")) ?? new List<object>())
                {
                    var t = O(o);
                    if (t != null && S(t["name"]) == name) { lo = hi = F(t["h"]); return true; }
                }
            return false;
        }
        return false;
    }

    // =====================================================================
    // 通し
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/S1→S5 を通す")]
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
        sb.AppendLine(Stage3_Shukaku());
        sb.AppendLine(Stage4_Niwa());
        sb.AppendLine(Stage5_Nishi());
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

    /// <summary>**当邸のために新造した部材**(崖下の長屋・棟門・丸太物・御殿の屋根)のマテリアルを、
    /// **借り先を名指しして**結び直す。
    /// ⚠ `SearchAndRemapMaterials(..., Everywhere)` はプロジェクト全体(6.9GB)を舐めるので使わない
    ///   — 2026-08-24 に実際にユーザーの PC が固まった。借り先は下の 5 フォルダだけ見る。
    /// ⚠ **同じ `Models/Nagaya` に在庫の表長屋(`Nagaya_Omote_*`)も居る**が、あれは材質を
    ///   .obj のサブアセットとして抱えているのでここでは当たらない(「借り先が見つからない材:
    ///   knagayamap」と出るのが正常)。表長屋は `Edo/長屋/表長屋のマテリアルをremap` が担当する。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap")]
    public static void RemapOkabeShinzoMenu() { Debug.Log("[Okabe] " + RemapOkabeShinzo()); }
    public static string RemapOkabeShinzo()
    {
        string[] donorDirs = {
            "Assets/Japanese Village Kit/Materials",
            "Assets/Japanese Castle/Meshes/Exterior/Materials",
            "Assets/Edo/Materials",
            // 丸太の手すり・汀の杭は NatureManufacture の丸太から切り出すので材質名は M_Wood_fence
            "Assets/NatureManufacture Assets/Meadow Environment Dynamic Nature/Fence/Models",
            // 新造の木(Own.Enoki/Keyaki/…)とつる(Own.TsuruFuji/…)は FJG の樹皮・葉の名を名乗る
            "Assets/Waldemarst/FreeJapaneseGarden/Materials",
            // 庭石・飛石・沓脱石(Own.Ishigumi/Tobiishi/Kutsunugi)は NatureManufacture の
            // photoscanned rock を切って使うので材質名は M_photoscanned_rocks_01
            "Assets/NatureManufacture Assets/Meadow Environment Dynamic Nature/Rocks/Rocks/Models/Materials",
        };
        var byName = new Dictionary<string, Material>();
        foreach (var dir in donorDirs)
        {
            if (!AssetDatabase.IsValidFolder(dir)) continue;
            foreach (var guid in AssetDatabase.FindAssets("t:Material", new[] { dir }))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
                if (m != null && !byName.ContainsKey(m.name)) byName[m.name] = m;
            }
        }
        // ⚠ **FBX を焼いたフォルダは必ずここに足す。**松江松平で、番所の材質を替えたのに
        //   remap がそのフォルダを見ておらず真っ白になった前例がある(2026-08-31)。
        // ⚠ `Models/Trees` は当邸が新造した高木3種とつる3種が居る。ここに入れないと
        //   松江松平のメニュー(`Edo/松平出羽守上屋敷/附属屋・門・木のマテリアルをremap`)を
        //   走らせない限り真っ白のままだった(2026-09-04 に部材方が発見)。
        // ⚠ `Models/Niwa` は庭の点景(庭石・飛石・沓脱石・四つ目垣・建仁寺垣・乱杭)。
        //   ⛔ 入れ忘れると石が真っ白・竹垣が真っ白になる(FBX は材質「名」しか運ばない)。
        string[] modelDirs = { "Assets/Edo/Models/Nagaya", "Assets/Edo/Models/Mon",
                               "Assets/Edo/Models/Maruta", "Assets/Edo/Models/Goten/Roofs",
                               "Assets/Edo/Models/Fuzokuya", "Assets/Edo/Models/Hei",
                               "Assets/Edo/Models/Trees", "Assets/Edo/Models/Niwa" };
        modelDirs = System.Array.FindAll(modelDirs, AssetDatabase.IsValidFolder);
        int n = 0; var miss = new List<string>();
        foreach (var guid in AssetDatabase.FindAssets("t:Model", modelDirs))
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
                    if (!byName.TryGetValue(m.name, out donor)) { if (!miss.Contains(m.name)) miss.Add(m.name); continue; }
                    if (donor == m) continue;
                    imp.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), m.name), donor);
                    touched = true;
                }
            if (touched)
            {
                AssetDatabase.WriteImportSettingsIfDirty(path);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                n++;
            }
        }
        AssetDatabase.SaveAssets();
        return "新造部材の remap " + n + " 本"
             + (miss.Count > 0 ? " / 借り先が見つからない材: " + string.Join(", ", miss.ToArray()) : "");
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
