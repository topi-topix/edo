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

        // ---- 練塀 ------------------------------------------------------
        int hei = 0, skipped = 0;
        foreach (var r in Runs)
        {
            if (r.Nagaya) continue;                       // 表長屋は下でまとめて据える
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
        sb.AppendLine("練塀: " + hei + " run 据えた");

        // ---- 表長屋 ----------------------------------------------------
        sb.AppendLine(PlaceOmoteNagaya(kak, wait));

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

    // ---------------------------------------------------------------- 表長屋
    /// <summary>表長屋の妻で、破風・鬼が**壁の実体より外へ出る量**[m](片側)。
    /// 松江松平が `Nagaya_Omote_36.fbx` を実測した値(全長 36.000 に対し壁は 35.360)。
    /// 妻部材は長さによらず同じなので定数。⛔ **呼び寸法をそのまま run 長に使わない理由がこれ** —
    /// run 長で頼むと隣り合う run の**壁が 0.64m 空き、軒だけが渡る**。
    /// ⚠ 据えた後に実測して食い違えば鳴らす(部材が変わったら定数は死ぬ)。</summary>
    const float NAGAYA_TSUMA_OVER = 0.32f;

    /// <summary>外周の表長屋。⭕ **2026-09-04 ユーザー裁定12=A で二階建てに確定**
    /// (`roofs.OmoteNagaya.kai` = 二階・棟 7.183)。表門は**長屋の躯体を門の上まで通し、
    /// その足元に門口を抜いた版**(`runs[].monS` が門口の芯を run の中で指す)。
    ///
    /// ⛔ **丸ごとのモジュールを並べない。**端が成り行きになって門・隅との間に隙間が空く
    /// (2026-08-29 松江松平: 門の西へ 1.66m 食い込み・東へ 0.96m の隙間が同時に出た)。
    /// ⭕ **run の長さで焼いた一本物**を据える。⚠ 呼び寸法は**壁の実体が run を覆う長さ**
    /// (run 長 + 妻の出×2)。⛔ run 長そのままで頼まない。
    /// ⚠ ピボットは**走りの中心・土台の底・壁の外面**なので、置く時点で犬走りぶん内へ寄せる。</summary>
    static string PlaceOmoteNagaya(Transform kak, List<string> wait)
    {
        // 二階かどうかは指図が決める(⛔ 実装で決め打ちしない)
        var rf = O(Get(O(Get(D, "roofs")), "OmoteNagaya"));
        bool nikai = rf != null && Has(rf, "kai") && S(rf["kai"]).Contains("二階");
        int made = 0, miss = 0; float lastH = 0f; bool anyMon = false;
        var sb = new System.Text.StringBuilder();
        foreach (var r in Runs)
        {
            if (!r.Nagaya) continue;
            float len = r.s1 - r.s0 + 2f * NAGAYA_TSUMA_OVER;
            float call = Mathf.Round(len * 100f) / 100f;
            // 門口を抜いた版か(指図が run の中で門口の芯を指す)
            float monS = 0f;
            foreach (var o in A(D["runs"]) ?? new List<object>())
            { var q = O(o); if (q != null && S(q["name"]) == r.name && Has(q, "monS")) monS = F(q["monS"]); }
            if (monS > 0f) anyMon = true;
            string path;
            if (monS > 0f)
            {
                // ⚠ 門口は**部材のローカル +X の左端から**測るが、その「左端」は run の s1 の側
                //   (見え面 +Z を外へ向ける yaw なので、ローカル +X は s の減る向きへ写る)。
                //   ⛔ 向きを式で決めない — 据えた実メッシュの穴の位置を検査で見張ること。
                float gc = Mathf.Round((r.s1 - monS + NAGAYA_TSUMA_OVER) * 100f) / 100f;
                path = EdoAssets.Own.NagayaOmoteMon(call, gc, nikai);
            }
            else path = nikai ? EdoAssets.Own.NagayaOmote2F(call) : EdoAssets.Own.NagayaOmote(call);

            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            {
                miss++;
                wait.Add("表長屋 " + r.name + "(run " + (r.s1 - r.s0).ToString("0.###") + "m → 呼び "
                       + call.ToString("0.##") + "m" + (nikai ? "・二階" : "") + "): 部材が無い " + path
                       + " → blender --background --python Tools/Blender/build_nagaya_omote.py -- "
                       + call.ToString("0.##") + (nikai ? " --floors 2" : ""));
                continue;
            }
            Vector2 outw = OutNormal(r.edge);
            float psi = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;   // 見え面 +Z を外へ
            float sMid = (r.s0 + r.s1) * 0.5f;
            // ⚠ ピボット = 壁の**外面**なので犬走りぶん内へ寄せてから置く
            Vector2 p = EdgePt(r.edge, sMid) - outw * INUBASHIRI;
            float seat = r.SeatAt(sMid);
            var go = EdoBuild.Place(path, new Vector3(p.x, seat, p.y), psi, Vector3.one, kak, r.name);
            if (go == null) { miss++; continue; }
            EdoBuild.SeatBottom(go, seat - 0.10f);
            // 妻の出の定数が部材と合っているかを、据えた実メッシュで検める
            var bb = EdoBuild.RB(go);
            Vector2 dir = (EdgePt(r.edge, r.s1) - EdgePt(r.edge, r.s0)).normalized;
            float realLen = Mathf.Abs(bb.size.x * dir.x) + Mathf.Abs(bb.size.z * dir.y);
            lastH = bb.size.y;
            if (Mathf.Abs(realLen - call) > 0.10f)
                wait.Add("表長屋 " + r.name + ": 部材の実長 " + realLen.ToString("F2")
                       + "m が呼び " + call.ToString("0.##") + "m と食い違う(妻の出の定数 "
                       + NAGAYA_TSUMA_OVER.ToString("0.##") + " が部材と合っていない疑い)");
            made++;
        }
        // 棟高の突き合わせ(指図 ⇔ **据えた現物**)。⛔ 呼び寸法や doc の数字で比べない
        if (Has(O(D["const"]), "nagayaH") && lastH > 0.1f)
        {
            float want = C("nagayaH");
            if (Mathf.Abs(lastH - want) > 0.15f)
                wait.Add("表長屋の棟高: 指図 const.nagayaH " + want.ToString("0.##")
                       + "m / 据えた現物の実丈 " + lastH.ToString("0.##") + "m"
                       + (nikai ? "(裁定12=A で二階に確定したので、指図の値が平屋のままの疑い)" : ""));
        }
        // 表門 — 裁定12=A で**長屋の躯体に門口を抜く**形になった(`runs[].monS`)
        if (!anyMon)
        {
            var gp = O(Get(O(Get(D, "gate")), "plan"));
            wait.Add("表門: どの表長屋の run も `monS`(門口の芯)を持たない — "
                   + "裁定12=A は門を**長屋の躯体に抜く**形なので、指図方が run を継いで monS を"
                   + "書くまで門口が開かない。⚠ 指図の棟高 gate.plan.monH = "
                   + (gp != null && Has(gp, "monH") ? F(gp["monH"]).ToString("0.##") : "?")
                   + "m(裁定12=A は 8.5)");
        }
        sb.Append("表長屋: " + made + " 棟" + (nikai ? "(二階)" : "(平屋)")
                + (miss > 0 ? " / 部材の無い run " + miss : ""));
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
                        var bb = EdoBuild.RB(go0);
                        Vector2 dir0 = (EdgePt(e0, s + 1f) - c0).normalized;
                        openW = Mathf.Abs(bb.size.x * dir0.x) + Mathf.Abs(bb.size.z * dir0.y);
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
        if (gaps.Count > 0) sb.Append(" ｜ 潜りの口 " + gaps.Count + " 箇所(戸 " + kuguri + " 枚)");
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
                if (!Has(m, "kirikaki") && !Has(rf, "kirikaki"))
                    wait.Add("棟 " + nm + ": **切り欠きの線が指図に無い**(裁定10=A) — "
                           + "玄関棟の屋根面へ差し込む食い込みの線を 其十九 から `kirikaki` へ。"
                           + "いまは切り欠かずに据えてあるので、背面が玄関棟の屋根と重なる");
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
        return "棟: " + made + " 棟(屋根待ち " + noRoof + " / 裁定待ちで据えず " + held + ")";
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

            // ⛔ **2026-09-04 裁定11=B: 御錠口に `Own.Jouguchi` は使わない。**
            //    廊下幅一間の建具として渡廊下の部材で通し、錠口の戸は在庫の戸を建て込む。
            //    ⚠ 指図方が `links.L_Jouguchi` を 1×1 へ書き換え中。1間になるまでは据えない。
            if (Has(l, "asset") && S(l["asset"]).EndsWith("Jouguchi"))
            {
                if (Mathf.Abs((alongU ? dv : du) - 1f) > 0.01f)
                {
                    wait.Add("御錠口 " + nm + ": 裁定11=B で**廊下幅一間**になるが、指図はまだ "
                           + du.ToString("0.##") + "×" + dv.ToString("0.##") + "間。"
                           + "⛔ `Own.Jouguchi`(3間角)は使わない — 1×1 へ書き換わるまで据えない");
                    held++; continue;
                }
                // 1間になっていれば下の渡廊下の枝で通す(asset は無視する)
            }
            // 指図が部材を名指ししているもの(御錠口以外)
            else if (Has(l, "asset"))
            {
                string path = AssetByKey(S(l["asset"]), Mathf.Max(du, dv), Mathf.Min(du, dv));
                if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
                { wait.Add("廊下 " + nm + ": 部材が引けない " + S(l["asset"])); continue; }
                Vector2 c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
                // ⚠ ピボットは**床レベル**(地盤ではない)— 部材の doc の規約
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
            if (go != null) made++;
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
            case "Kurumayose": return EdoAssets.Own.Kurumayose;
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
        float haveW = Mathf.Max(b.size.x, b.size.z), haveD = Mathf.Min(b.size.x, b.size.z);
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
                                var bb = EdoBuild.RB(gg);
                                Vector2 dir = (f.W(bu, bvv) - f.W(au, avv)).normalized;
                                float realW = Mathf.Abs(bb.size.x * dir.x) + Mathf.Abs(bb.size.z * dir.y);
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
    static string PlantByKey(string key)
    {
        if (string.IsNullOrEmpty(key)) return null;
        var t = key.Split('.');
        if (t.Length < 2) return null;
        string fam = t[0], nm = t[1];
        string size = t.Length > 2 ? t[2] : "Mid";
        int idx = 1;
        if (t.Length > 3) int.TryParse(t[3], out idx);
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
            if (nm == "Momiji")   return EdoAssets.Own.Momiji(size, idx);
            if (nm == "Ume")      return EdoAssets.Own.Ume(size, idx);
        }
        return null;
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
    /// 期待する欄は <c>impl.planting.points[]</c> =
    /// <c>{ name, zone, role, species, asset, u, v, h, tilt, tiltDir[2], ground }</c>。
    /// ・`asset` … 部材のキー(`JG.Pine.Big.2` など)。**どの在庫の木がどの樹種かは在庫方が決める**
    /// ・`h`     … 実際に置く丈[m]。⚠ 指図の `hMin`/`hMax` と窓の樹高の上限を**生成器が既に噛ませた後**の値
    /// ・`ground`… `design`(造成後の地盤)か `terrain`(現地形)
    /// ⛔ ここで丈を丸めたり、上限を当て直したりしない — 二重に判定すると図と食い違う。</summary>
    static string PlantFromImpl(List<string> wait)
    {
        var pl = O(Get(IMPL, "planting"));
        if (pl == null)
        {
            wait.Add("算出物に planting が無い — 林(高木72・中木160・低木22群・下草・つる・ヤダケ)/"
                   + "法肩の松15/榎3/ススキ の**散布点を生成器に焼かせること**"
                   + "(`--export-impl` に planting を足す)。⛔ 実装側で撒き直すと、"
                   + "指図の検査(窓の樹高の上限・対岸の二層・坂と木戸の離れ)が見た配置と別物になる");
            return "植栽: 算出物待ち";
        }
        var pts = A(Get(pl, "points"));
        if (pts == null) { wait.Add("算出物 planting.points が無い"); return "植栽: 算出物待ち"; }
        var grp = Group("Nishi/Planting"); Clear(grp);
        var f = Grid;
        int made = 0, noPart = 0, noAsset = 0;
        var byZone = new Dictionary<string, int>();
        var missing = new HashSet<string>();
        foreach (var o in pts)
        {
            var q = O(o); if (q == null) continue;
            string key = Has(q, "asset") ? S(q["asset"]) : null;
            if (key == null) { noAsset++; continue; }
            string path = PlantByKey(key);
            if (path == null) { missing.Add(key); noPart++; continue; }
            Vector2 c = f.W(F(q["u"]), F(q["v"]));
            float y = S(Get(q, "ground")) == "terrain" ? EdoBuild.Ground(c.x, c.y) : Graded.At(c.x, c.y);
            if (float.IsNaN(y)) y = EdoBuild.Ground(c.x, c.y);
            var go = EdoBuild.Place(path, new Vector3(c.x, y, c.y), 0f, Vector3.one, grp,
                                    Has(q, "name") ? S(q["name"]) : (S(q["zone"]) + "_" + made));
            if (go == null) { missing.Add(key + " → " + path); noPart++; continue; }
            // 丈を指図の値へ合わせる(⛔ 部材の素の丈で置かない — 指図の hMin/hMax が意味を失う)
            float want = F(Get(q, "h")), nat = NaturalHeight(path, grp);
            if (want > 0.1f && nat > 0.1f)
                go.transform.localScale = Vector3.one * (want / nat);
            // 水へ傾ける松など。⚠ 傾ける向きも生成器が持つ(実装で決めない)
            float tilt = F(Get(q, "tilt"));
            if (Mathf.Abs(tilt) > 0.01f)
            {
                var d2 = A(Get(q, "tiltDir"));
                Vector2 dir = (d2 != null && d2.Count == 2) ? new Vector2(F(d2[0]), F(d2[1])) : Vector2.up;
                Vector2 w2 = (f.W(dir.x, dir.y) - f.W(0f, 0f)).normalized;
                go.transform.rotation = Quaternion.AngleAxis(tilt, new Vector3(w2.y, 0f, -w2.x));
            }
            EdoBuild.SeatBottom(go, y);
            made++;
            string z = S(Get(q, "zone")) ?? "?";
            byZone[z] = (byZone.ContainsKey(z) ? byZone[z] : 0) + 1;
        }
        foreach (var k in missing)
            wait.Add("植栽の部材のキーが解けない: " + k + " — 在庫方が `impl.planting.points[].asset` の"
                   + "書式(族.名.寸法.個体)で名指しすること");
        if (noAsset > 0)
            wait.Add("散布点 " + noAsset + " 件に asset が無い — **どの在庫の木がどの樹種を代表するか**は"
                   + "在庫方の判断。⛔ 実装で見繕わない");
        var sb = new System.Text.StringBuilder("植栽: " + made + " 本据えた");
        foreach (var kv in byZone) sb.Append(" / " + kv.Key + " " + kv.Value);
        if (noPart > 0) sb.Append(" ｜ 部材が引けず据えられない " + noPart);
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
            float top = F(Get(k, "top"));                     // 頭の高さ(水面 + topMin..topMax)
            float yaw = Has(k, "yaw") ? F(k["yaw"]) : 0f;     // ⛔ 実装で振らない
            var go = EdoBuild.Place(path, new Vector3(c.x, top, c.y), yaw, Vector3.one, grp,
                                    Has(k, "name") ? S(k["name"]) : "Kui_" + made);
            if (go != null) made++;
            // 貫 — 頭から `nuki.below` 下。⚠ 指図の「杭ごと1段」は部材が数千本になるので
            //      部材方が 1間の丸太1本として出した(据えるのは杭の並びに沿って)
            if (Has(k, "nuki") && below > 0f)
            {
                var gn = EdoBuild.Place(EdoAssets.Own.KuiNuki, new Vector3(c.x, top - below, c.y),
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
            var pl = O(Get(im, "planting"));
            var pts = pl == null ? null : A(Get(pl, "points"));
            if (pts == null) ng("planting.points が無い — 林・法肩の松・榎・ススキの散布点を生成器に焼かせること");
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
                float mizu = F(tt["mizugiwaM"]);
                Vector2 a = P[e % P.Length], b = P[(e + 1) % P.Length], nrm = OutNormal(e);
                Vector2 A2 = a + nrm * mizu, B2 = b + nrm * mizu;   // 汀線 = 辺を外へ mizugiwaM 出した線
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
                    float d = DistSeg(c, A2, B2);
                    if (d > mx) mx = d;
                    if (d > 0.60f) far++;
                    float dia = F(Get(k, "dia"));
                    if (dia > 0f && (dia < dMin - 1e-4f || dia > dMax + 1e-4f)) badD++;
                }
                if (far > 0) ng(string.Format("kui {0}/{1} 本が汀線(辺{2}を外へ {3:F2}m)から 0.60m 以上離れている(最大 {4:F2}m)", far, n, e, mizu, mx));
                else ok(string.Format("kui {0} 本は汀線に載る(最大の離れ {1:F2}m)", n, mx));
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
            if (role == "takagi")
                foreach (var o in A(Get(hy, "takagi")) ?? new List<object>())
                {
                    var t = O(o);
                    if (t != null && S(t["species"]) == species) { lo = F(t["hMin"]); hi = F(t["hMax"]); return true; }
                }
            if (role == "yadake")
            { var y = O(Get(hy, "yadake")); if (y != null) { lo = F(y["hMin"]); hi = F(y["hMax"]); return true; } }
            return false;
        }
        if (zone == "hokata")
        { var hk = O(Get(n, "hokata")); if (hk != null) { lo = F(hk["hMin"]); hi = F(hk["hMax"]); return true; } return false; }
        if (zone == "hojiri")
        {
            var hj = O(Get(n, "hojiri")); if (hj == null) return false;
            if (role == "enoki")
                foreach (var o in A(Get(hj, "enoki")) ?? new List<object>())
                {
                    var t = O(o);
                    if (t != null && S(t["name"]) == name) { lo = F(t["hMin"]); hi = F(t["hMax"]); return true; }
                }
            if (role == "susuki")
            { var su = O(Get(hj, "susuki")); if (su != null) { lo = F(su["hMin"]); hi = F(su["hMax"]); return true; } }
            return false;
        }
        if (zone == "mado")
        {
            var md = O(Get(n, "mado")); if (md == null) return false;
            if (role == "susuki")
            { var su = O(Get(md, "susuki")); if (su != null) { lo = F(su["hMin"]); hi = F(su["hMax"]); return true; } }
            if (role == "matsu")
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
        string[] modelDirs = { "Assets/Edo/Models/Nagaya", "Assets/Edo/Models/Mon",
                               "Assets/Edo/Models/Maruta", "Assets/Edo/Models/Goten/Roofs",
                               "Assets/Edo/Models/Fuzokuya", "Assets/Edo/Models/Hei" };
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
