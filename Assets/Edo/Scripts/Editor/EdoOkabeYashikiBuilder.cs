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
//   指図の json には**入っておらず**、算出物 `docs/Sashizu/okabe_impl.json` に焼いてある
//   (`graded` / `rails` / `corners` / `base`)。これを C# へ移植すると正典が2つになって
//   黙ってドリフトするので、**2026-09-03 ユーザー裁定1=A** で焼き出しに受けさせ、ここは**読むだけ**にした
//   (スキーマは下の <see cref="IMPL"/> の注)。
//   ⛔ **焼いた生成器 `Tools/Sashizu/build_okabe_sashizu.py` はもう無い** — 2026-09-20 の生成器の共通化
//   (afb529c2)で消え、main には焼き手が一つも残らなかった。焼き直せない欄は黙って腐る:
//   実際 `corners[].deg` は 13 隅すべて符号が逆のまま半月止まっていた(EDO-0343 / EDO-0386)。
//   ⭕ いまの焼き手は `python3 Tools/Sashizu/bake_impl.py okabe --write`(器 `Tools/Sashizu/impl_okabe.py`)。
//   `rails` / `kui` / `migiwa` / `checks` は据え置き(＝未検査・規則19)── どの欄が据え置きかは `baked.carried` が正。
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
    public static void Reload() { _topLanding.Clear(); _d = null; _impl = null; _runs = null; _frame = null; _graded = null; _flat = null; _rampProf = null; }

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
    ///   "generator": "Tools/Sashizu/bake_impl.py &lt;邸&gt; --write",
    ///   "baked": { "columns": ["corners"], "carried": { "graded": "…", … } },   // 焼き直した欄 / 据え置いた欄
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
                        + "\n   焼き手が焼いていない。`python3 Tools/Sashizu/bake_impl.py okabe --write`"
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
                + "\n   `python3 Tools/Sashizu/bake_impl.py okabe --write` を回し直すこと"
                + "\n   ⛔ ただし焼けるのは corners だけ — graded/rails/base/planting/kui/migiwa/gardens に"
                + "効く欄を指図で動かしたのなら、焼き手が無い(EDO-0386)。掲示板へ起票してから建てること");
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

    /// <summary>算出物の欄が**いまの指図から焼かれていない**(`baked.carried` に名がある = 前の指図のまま据え置き)か。
    /// 案1(EDO-0502)では planting・migiwa・gardens・rails・kui・checks が据え置き。⛔ 据え置きの欄で建てない
    /// (前の配置の庭・植栽が今の棟の上に建つ)── 据えずに名を報告へ出す(規則19: 未検査であって合格ではない)。</summary>
    static bool Stale(string col)
    {
        var bk = O(Get(IMPL, "baked"));
        var car = bk == null ? null : Get(bk, "carried");
        if (car is Dictionary<string, object>) return ((Dictionary<string, object>)car).ContainsKey(col);
        var cl = car as List<object>;
        if (cl != null) foreach (var q in cl) if (S(q) == col) return true;
        return false;
    }

    /// <summary>据え置きの欄から前に建てた群を**退ける**(SetActive(false)・消さない)。焼き直したら次の流しで建て直る。</summary>
    static string RetireStaleGroup(string child, string col)
    {
        var root = GameObject.Find(GN); if (root == null) return "";
        var tr = root.transform.Find(child); if (tr == null || !tr.gameObject.activeSelf) return "";
        Group(child);                                    // 書き戻しの台帳に載せる(EDO-0282②)
        tr.gameObject.SetActive(false);
        return "(前の指図の " + child + " を退けた ── 算出物 " + col + " が据え置き)";
    }

    static float ImplTol(string key, float ifMissing)
    {
        var c = O(Get(IMPL, "checks"));
        return c != null && Has(c, key) ? F(c[key]) : ifMissing;
    }

    // =====================================================================
    // 群と地形の小物
    // =====================================================================
    /// <summary>
    /// 群を辿る(無ければ作る)。⭐ 中身は共通の一本道 <see cref="EdoYashikiPrefab.Group"/>。
    /// ルートの外側と**辿った先頭の段だけ**を解くので、触っていない段は書き戻しが飛ばせる
    /// (EDO-0282③)。⛔ ここに置き方を書かない(規則21)。
    /// </summary>
    static Transform Group(string child) { return EdoYashikiPrefab.Group(GN, child); }
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
        // ⭐ 縁の皮(Stage3b)を先に外して穴を塞ぐ ── 皮は駒の今の位置に合わせて起こす物で、造成・据え直しの後は古い(EdoBuild.ClearEdgeSkins)
        {
            var rootG = GameObject.Find(GN); var es = rootG == null ? null : rootG.transform.Find("EdgeSkin");
            if (es != null && es.childCount > 0) sb.AppendLine("縁の皮を外して塞いだ升 " + EdoBuild.ClearEdgeSkins(Group("EdgeSkin")) + "(3 の後に 3b で起こし直す)");
        }
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
        sb.Append(GradeRamps());
        return sb.ToString();
    }

    /// <summary>上がり口の段石(topStep)の背の平らの奥行[m]。【U】普請奉行の指示 2026-10-07(EDO-0502 第47巡)「背の 0〜1m を天端 −0.02 ±0.02」。
    /// ⚠ 指図 kaidans[].topStep の文はまだ長さを持たない ── 欄に入ったらそちらを読む。</summary>
    const float TOPSTEP_BACK_FLAT = 1.0f;
    /// <summary>上がり口の段石の背の平らで地形が外れてよい量[m](超える升は皮で描く)。【U】普請奉行の指示 2026-10-07「18.73±0.02」。</summary>
    const float TOPSTEP_BACK_TOL = 0.02f;
    /// <summary>上がり口の段石の背の平らの面(坂の名/石段の名 → 面)。<see cref="ProfSNodes"/> が起こし、Stage3b が皮の faces へ足す。</summary>
    static readonly Dictionary<string, EdoBuild.SkinFace> _topLanding = new Dictionary<string, EdoBuild.SkinFace>();
    /// <summary>坂の縦断 `profS`([s, y] の並び・同じ s に二つの高さ = 石段)と芯 `pts` から、均す芯の節点(世界 xz)と高さを起こす(EDO-0502 第8巡)。
    /// 石段の段差は、その坂を名指す石段(kaidans[].atRoute)の平面 a→b を芯へ射影した道のりの両端に分ける(手前 = 前の勾配の延長・奥 = 段の上の高さ)。
    /// 石段が見つからない段差は ⛔ null(発明しない)。</summary>
    static KeyValuePair<Vector2[], float[]> ProfSNodes(Dictionary<string, object> r, Frame f, out string note)
    {
        note = "";
        var line = new List<Vector2>(); foreach (var q in A(Get(r, "pts"))) { var v = A(q); line.Add(f.W(F(v[0]), F(v[1]))); }
        var prof = new List<Vector2>(); foreach (var q in A(Get(r, "profS"))) { var v = A(q); prof.Add(new Vector2(F(v[0]), F(v[1]))); }
        string nm = S(Get(r, "name"));
        var st = new List<Vector2>();   // 石段の平面の道のり [s0, s1]
        var stK = new List<Dictionary<string, object>>();
        foreach (var ko in A(Get(D, "kaidans")) ?? new List<object>())
        {
            var k = O(ko); if (k == null || S(Get(k, "atRoute")) != nm) continue;
            Vector2 ka, kb; if (!KaidanAB(k, out ka, out kb)) continue;
            float sa = EdoBuild.ArcOf(line, ka).x, sbb = EdoBuild.ArcOf(line, kb).x;
            st.Add(new Vector2(Mathf.Min(sa, sbb), Mathf.Max(sa, sbb))); stK.Add(k);
        }
        var ss = new List<float>(); var yy = new List<float>();
        for (int i = 0; i < prof.Count; i++)
        {
            bool step = i + 1 < prof.Count && Mathf.Abs(prof[i + 1].x - prof[i].x) < 0.01f;
            if (!step) { if (i > 0 && Mathf.Abs(prof[i - 1].x - prof[i].x) < 0.01f) continue; ss.Add(prof[i].x); yy.Add(prof[i].y); continue; }
            int si = st.FindIndex(z => prof[i].x >= z.x - 0.5f && prof[i].x <= z.y + 0.5f);
            if (si < 0) { note = "道のり " + prof[i].x.ToString("F2") + " の段差に石段が無い"; return default(KeyValuePair<Vector2[], float[]>); }
            float s0 = st[si].x, s1 = st[si].y;
            float y0 = prof[i].y;
            if (i > 0 && prof[i].x - prof[i - 1].x > 1e-3f) y0 = Mathf.Lerp(prof[i - 1].y, prof[i].y, (s0 - prof[i - 1].x) / (prof[i].x - prof[i - 1].x));
            ss.Add(s0); yy.Add(y0); ss.Add(s1); yy.Add(prof[i + 1].y);
            note += "段 " + s0.ToString("F2") + "〜" + s1.ToString("F2") + " ";
        }
        // 硬い(石段の踏面に土を載せない・上がり口の背に窪みを作らない ── 指図 kaidans[].topStep・2026-10-06 夕):
        //   石段の平面 [s0, s1] の下の地盤は、段鼻の線(足 yBot → 最後の踏面 yTop − 蹴上)の下に置く。⛔ 縦断 profS の直線(足 → 上の面)のままだと
        //   最後の踏面の背で地盤が踏面より 0.28 上に出る(蹴上 0.28 × 1 段ぶん)。
        //   上がり口の段石(topStep)の奥 s1 + 奥行 の地盤は「天端 − x」(欄の文)へ ── 段石の背の窪みと土の斜面を作らない。
        var keepS = new List<float>();
        for (int si = 0; si < st.Count; si++)
        {
            var k = stK[si]; if (!Has(k, "yBot") || !Has(k, "yTop") || !Has(k, "steps")) continue;
            float s0 = st[si].x, s1 = st[si].y, kb0 = F(k["yBot"]), kt = F(k["yTop"]), rz = (kt - kb0) / Mathf.Max(1, (int)F(k["steps"]));
            float yEnd = kt - rz;
            string ts = S(Get(k, "topStep"));
            // 上がり口の段石が無い石段は、最後の蹴上の上 s1 から上の面(⛔ s1 を下げると上の面の縁が蹴上ぶん窪む)── 段の中だけ段鼻の線の下へ
            for (int i = 0; i < ss.Count; i++)
                if (ss[i] > s0 + 1e-3f && ss[i] < s1 - 1e-2f) yy[i] = Mathf.Min(yy[i], Mathf.Lerp(kb0, yEnd, (ss[i] - s0) / Mathf.Max(1e-3f, s1 - s0)));
            if (ts == null) continue;
            int i1 = ss.FindIndex(z => Mathf.Abs(z - s1) < 1e-2f);
            if (i1 < 0) { int at = ss.FindIndex(z => z > s1); if (at < 0) at = ss.Count; ss.Insert(at, s1); yy.Insert(at, yEnd); i1 = at; }
            else yy[i1] = yEnd;
            keepS.Add(s1);
            note += "段の下 " + s0.ToString("F2") + "〜" + s1.ToString("F2") + " を段鼻の線へ(" + kb0.ToString("F2") + "→" + yEnd.ToString("F2") + ") ";
            var md = System.Text.RegularExpressions.Regex.Match(ts, @"奥行\s*([0-9.]+)\s*以上");
            var mb = System.Text.RegularExpressions.Regex.Match(ts, @"背の地盤は天端\s*[−\-]\s*([0-9.]+)");
            var mt = System.Text.RegularExpressions.Regex.Match(ts, @"天端は[^0-9]*([0-9]+\.[0-9]+)");
            if (!md.Success || !mb.Success || !mt.Success) { note += "★ topStep の奥行・背の地盤・天端が読めない ── 上がり口の背を均さない "; continue; }
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            float tread = (s1 - s0) / Mathf.Max(1, (int)F(k["steps"]) - 1);
            float dp = Mathf.Max(tread, float.Parse(md.Groups[1].Value, inv)), yb = float.Parse(mt.Groups[1].Value, inv) - float.Parse(mb.Groups[1].Value, inv);
            float s2 = s1 + dp;
            for (int i = ss.Count - 1; i >= 0; i--) if (ss[i] > s1 + 1e-2f && ss[i] < s2 - 1e-3f) { ss.RemoveAt(i); yy.RemoveAt(i); }
            int i2 = ss.FindIndex(z => Mathf.Abs(z - s2) < 1e-2f);
            if (i2 < 0) { int at = ss.FindIndex(z => z > s2); if (at < 0) at = ss.Count; ss.Insert(at, s2); yy.Insert(at, yb); }
            else yy[i2] = yb;
            keepS.Add(s2);
            // 段石の背の平ら(天端 − x のまま奥へ TOPSTEP_BACK_FLAT)── 背の 0〜1m を坂の勾配で上げない(2026-10-07 第47巡・普請奉行の指示
            //   「背の 0〜1m の地表を 18.73±0.02」── 1m 奥で +0.096 上がっていた)。その先の節点から坂へ戻る。
            // 平らの奥行 = 指図 kaidans[].topStepBackFlat の頭の数(2026-10-08 に欄へ上がった)── 無ければ従前の仮の定数
            float flatL = TOPSTEP_BACK_FLAT;
            { var mf = System.Text.RegularExpressions.Regex.Match(S(Get(k, "topStepBackFlat")) ?? "", @"^\s*([0-9.]+)"); if (mf.Success) flatL = float.Parse(mf.Groups[1].Value, inv); }
            float s3 = s2 + flatL;
            int iNext = ss.FindIndex(z => z > s2 + 1e-2f);
            if (iNext >= 0 && ss[iNext] > s3 + 0.5f)
            {
                ss.Insert(iNext, s3); yy.Insert(iNext, yb); keepS.Add(s3);
                // 皮が描く平らな面(Stage3b が faces へ足す)── 2m 格子の地形と返しの石垣の外形の中の「上げない」の規則では、段石の背 0.1〜0.25m が
                //   地形のまま 18.49〜18.65 で窪んだ(施主の写真の天端の前の縁の下の影の筋)。面にすれば返しの法の下も面の高さで描く。
                float wR = Has(r, "w") ? F(r["w"]) : (Has(k, "wKen") ? F(k["wKen"]) * C("ken") : 0f);
                if (wR > 0f)
                {
                    Vector2 d2, d3; var c2 = EdoBuild.ArcPoint(line, s2 - 0.05f, out d2); var c3 = EdoBuild.ArcPoint(line, s3, out d3);
                    Vector2 n2 = new Vector2(-d2.y, d2.x).normalized * (wR * 0.5f), n3 = new Vector2(-d3.y, d3.x).normalized * (wR * 0.5f);
                    _topLanding[nm + "/" + S(k["name"])] = new EdoBuild.SkinFace("TopLanding_" + S(k["name"]), new[] { c2 + n2, c3 + n3, c3 - n3, c2 - n2 }, yb, TOPSTEP_BACK_TOL);
                }
                note += "上がり口の背 " + s2.ToString("F2") + "〜" + s3.ToString("F2") + " を " + yb.ToString("F2") + " へ(topStep・平ら " + flatL.ToString("0.0#") + "m) ";
            }
            else note += "上がり口の背 " + s2.ToString("F2") + " を " + yb.ToString("F2") + " へ(topStep・⚠ 次の節点が近く平らを取れない) ";
        }
        var pts = new Vector2[ss.Count]; var ys = yy.ToArray();
        for (int i = 0; i < ss.Count; i++) { Vector2 d; pts[i] = EdoBuild.ArcPoint(line, ss[i], out d); }
        // 硬い: 坂の盛りは**平らな面(terraces)を上げない**(EDO-0502 第9巡・普請奉行の指示「坂の足は門の内の面に摺り付け、石垣と石段の前は
        //   門の内の面の高さを保つ」)。節点へ来る区間(前の節点 → この節点)が平らな面の上を通り、節点がその面より高ければ面の高さへ下げる
        //   (区間の 10〜90% を 0.5m おきに測る ── 面の縁は石垣の線にあり、節点の 0.5m 手前ではまだ縁の外のことがある)。
        //   石段は StackDownToGround で面まで積むので、口の石段は面から上る。⛔ 面より低い節点は上げない(切りは坂の設計)。
        //   当たる先: profS の坂で石段の足が平らな面に落ちる所(岡部 R_OmoteZaka の K_Dan1 の前 17.6→16.5)。
        if (_flat == null) _flat = FlatFaces(null);
        for (int i = 1; i < ss.Count; i++)
        {
            bool upper = st.Exists(z => Mathf.Abs(ss[i] - z.y) < 1e-3f) || keepS.Exists(z => Mathf.Abs(ss[i] - z) < 1e-2f);   // 石段の上の端・上がり口の背の節点は上の面の物
            if (upper) continue;
            float fy = float.NaN;
            float segL = ss[i] - ss[i - 1]; int nS = Mathf.Max(1, Mathf.CeilToInt(segL * 0.8f / 0.5f));
            for (int m = 0; m <= nS && float.IsNaN(fy); m++)
            {
                float sp = ss[i - 1] + segL * (0.1f + 0.8f * m / nS); Vector2 dd; var q = EdoBuild.ArcPoint(line, sp, out dd);
                float area = float.MaxValue;
                foreach (var fc in _flat) if (EdoGeom.PIP(fc.poly, q)) { float a = Mathf.Abs(EdoGeom.SignedArea(fc.poly)); if (a < area) { area = a; fy = fc.y; } }
            }
            if (float.IsNaN(fy) || ys[i] <= fy + 0.01f) continue;
            note += "節点 s=" + ss[i].ToString("F2") + " " + ys[i].ToString("F2") + "→面 " + fy.ToString("F2") + " ";
            ys[i] = fy;
        }
        return new KeyValuePair<Vector2[], float[]>(pts, ys);
    }

    /// <summary>指図の坂 <paramref name="r"/> の芯(世界 xz)・芯の高さ・路盤の幅を読む(GradeRamps と造成QA が同じ読みを使う)。
    /// 芯が無ければ false・note null。均さない理由があれば false・note に理由。profS から起こしたら true・note に経緯。</summary>
    static bool RampAxis(Dictionary<string, object> r, out Vector2[] pts, out float[] ys, out float width, out string note)
    {
        pts = null; ys = null; width = 0f; note = null;
        var f = Grid;
        var pl = A(Get(r, "pts")); var py = A(Get(r, "profY"));
        if (pl == null) return false;
        if (py == null || py.Count != pl.Count)
        {
            var ps = A(Get(r, "profS"));
            if (ps == null || ps.Count < 2) { note = "折れ線の芯はあるが profY も profS も無い ── ここでは均さない"; return false; }
            // 案1 の縦断 profS(道のり s・高さ)から芯の節点を起こす(EDO-0502 第8巡 ── 算出物 graded に表の坂の路盤が入っておらず、
            //   石段の奥に高さ 2.25m の土の壁が立っていた)。同じ s に二つの高さ = 石段:石段の平面(kaidans[].a→b)の両端の s に分けて置く。
            string ps0; var cp = ProfSNodes(r, f, out ps0); if (cp.Key == null) { note = ps0 + " ── 均さない"; return false; }
            pts = cp.Key; ys = cp.Value;
            note = "profS から芯の節点 " + pts.Length + " を起こした(" + ps0 + ")";
        }
        else
        {
            pts = new Vector2[pl.Count]; ys = new float[pl.Count];
            for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); pts[i] = f.W(F(q[0]), F(q[1])); ys[i] = F(py[i]); }
        }
        width = Has(r, "w") ? F(r["w"]) : F(r["wKen"]) * C("ken");
        return true;
    }

    /// <summary>**折れ線の坂の路盤**(案1・EDO-0502)。`ramps[]` のうち `pts` と `profY` を持つ坂
    /// (R_UraZaka・R_GakeZaka)は造成の算出物(impl.graded)に入っていない(sashizu_lib.ramp_y が別勘定にしている)ので、
    /// 造成の直後にここで均す。置き方は `EdoBuild.GradeSaka`。
    /// 硬い: `toeRule` を持つ坂は盛土の法尻を区画の線から 1.5m 以上内(節点で測るので一升ぶん厳しく取る)。
    /// 柔らかい: 芯は指図の `pts`(狙い)── 法尻のために途中の点を内へ寄せたら ⚠ で量を出す。端の点(門の内面・平場の角)は動かさない。
    /// ⚠ R_OmoteZaka(`profS`・切通しの石垣・石垣の段)はここで均さない ── 算出物の造成と石段の欄で受ける(報告に出す)。</summary>
    static string GradeRamps()
    {
        var sb = new System.Text.StringBuilder();
        var f = Grid; float ken = C("ken");
        float bf = C("batterFill"), bc = C("batterCut");
        var t = Terrain.activeTerrain; float cell = t.terrainData.size.x / (t.terrainData.heightmapResolution - 1);
        foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
        {
            var r = O(o); if (r == null) continue;
            string nm = S(r["name"]);
            Vector2[] pts; float[] ys; float width; string an;
            if (!RampAxis(r, out pts, out ys, out width, out an)) { if (an != null) sb.AppendLine("坂 " + nm + ": " + an); continue; }
            if (an != null) sb.AppendLine("坂 " + nm + ": " + an);
            var pin = new bool[pts.Length];
            pin[0] = true; pin[pts.Length - 1] = true;          // 門の内面・平場の角は動かさない
            bool hasToe = Has(r, "toeRule");
            // 硬い: 1.5m(指図 toeRule)。法尻は法の面と今の地盤の交わりを線で測る(EdoBuild.GradeSaka の toeLine)。節点の距離は参考に刷る
            float toe = hasToe ? 1.5f : 0f;
            // 案1 普請方の設計 `toeFix`(EDO-0502): 芯は描いた線のまま・区画線側の路肩に野面石の縁 h≤curbH・法尻=石の根。
            //   足りなければ芯を shiftMax だけ内へ(柔らかい)。数は指図の文から読む(⛔ 決め打ちしない ── 読めなければ縁を置かない)
            float curbH = 0f, shiftMax = hasToe ? 6f : 0f;
            var tf = O(Get(r, "toeFix"));
            if (tf != null)
            {
                var mh = System.Text.RegularExpressions.Regex.Match(S(Get(tf, "fix")) ?? "", @"h\s*≤\s*([0-9.]+)");
                // 「芯を X m 内へ」か「芯を内へ寄せる ── 上限 X m」(2026-10-03 普請奉行の上書きの書き方)を読む
                var ms = System.Text.RegularExpressions.Regex.Match(S(Get(tf, "soft")) ?? "", @"芯を\s*([0-9.]+)\s*m\s*内へ");
                if (!ms.Success) ms = System.Text.RegularExpressions.Regex.Match(S(Get(tf, "soft")) ?? "", @"芯を内へ[^。]*?上限\s*([0-9.]+)\s*m");
                if (mh.Success) curbH = float.Parse(mh.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
                shiftMax = ms.Success ? float.Parse(ms.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : 0f;
                if (!mh.Success) sb.AppendLine("★ 坂 " + nm + ": toeFix の縁の高さ(h≤)が読めない ── 縁を置かない");
            }
            var res = EdoBuild.GradeSaka(Poly, pts, ys, pin, width, bf, bc, toe, shiftMax, true, curbH, 1.5f);
            if (!res.ok) { sb.AppendLine("★ 坂 " + nm + ": " + res.note); continue; }
            if (!float.IsNaN(res.curbS0))
                sb.AppendLine("坂 " + nm + ": 路肩の野面石の縁 道のり " + res.curbS0.ToString("F1") + "〜" + res.curbS1.ToString("F1")
                            + "m(" + (res.curbS1 - res.curbS0).ToString("F1") + "m)・受ける丈 最大 " + res.curbHMax.ToString("F2")
                            + "m(≤ " + curbH.ToString("F2") + ")・石の根と区画の線 " + res.curbToe.ToString("F2") + "m(硬い ≥ 1.50・余裕 "
                            + (res.curbToe - 1.5f).ToString("F2") + "m)\n" + PlaceCurb(nm, res.curbLine, res.pts, ys, curbH));
            sb.AppendLine("坂 " + nm + ": 路盤を均した 節点 " + res.nodes + "|盛 " + res.fillM3.ToString("F0") + "m³(最大 "
                        + res.fillMax.ToString("F2") + "m)/ 切 " + res.cutM3.ToString("F0") + "m³(最大 " + res.cutMax.ToString("F2") + "m)"
                        + (hasToe ? "|法尻と区画の線 " + (float.IsInfinity(res.toeMin) ? "盛り無し" : res.toeMin.ToString("F2") + "m(法の面×地盤の線と**描かれた地表**の短い方 ── 描かれた法尻 " + res.toeRender.ToString("F2") + "m・締めて盛らなかった節点 " + res.unfilled + (res.toeRoad < 1.5f ? "・★ 路面の盛りが描かれて区画の線から " + res.toeRoad.ToString("F2") + "m まで下りる(路肩が線に近い ── 芯の寄せの上限は指図の toeFix)" : "") + "・≥ 1.5 ✔・余裕 "
                        + (res.toeMin - 1.5f).ToString("F2") + "m / 盛った節点の最短 " + res.toeNodeMin.ToString("F2") + "m・格子 " + cell.ToString("F2") + "m)") : "")
                        + (res.shift > 0f ? "|⚠ 法尻のため芯の途中を内へ " + res.shift.ToString("F2") + "m 寄せた(指図の芯は狙い)" : "")
                        + (res.roadUnfilled ? "|⚠ 寄せ切っても路面の盛りが線へ下りるので、区画の線の側の路肩の節点を盛らなかった(縁の石が路面を受ける・描かれた路面の盛りの最短 " + res.toeRoad.ToString("F2") + "m)" : ""));
        }
        return sb.ToString();
    }

    /// <summary>坂の路肩の野面石の縁(toeFix)を、路肩の線へ野面の乱積みで据える。天端 = 路面(芯の高さを道のりで一次)、
    /// 足元 = 路肩の外の描かれた地表。置き方は `EdoBuild.PlaceNozuraNet`(⛔ ここで駒を動かさない)。</summary>
    static string PlaceCurb(string nm, List<Vector2> line, Vector2[] pts, float[] ys, float curbH)
    {
        var grp = Group("Saka/Curb_" + nm); Clear(grp);
        if (line == null || line.Count < 2) return "  縁: 線が無い";
        var st = new float[pts.Length];
        for (int i = 1; i < pts.Length; i++) st[i] = st[i - 1] + (pts[i] - pts[i - 1]).magnitude;
        System.Func<Vector2, float> roadY = q =>
        {   // 芯の最寄りの点の道のりで芯の高さ
            float bd = float.MaxValue, bs = 0f;
            for (int k = 0; k + 1 < pts.Length; k++)
            {
                Vector2 a = pts[k], b = pts[k + 1], ab = b - a; float L2 = ab.sqrMagnitude; if (L2 < 1e-9f) continue;
                float tc = Mathf.Clamp01(Vector2.Dot(q - a, ab) / L2); float dd = (a + ab * tc - q).magnitude;
                if (dd < bd) { bd = dd; bs = st[k] + Mathf.Sqrt(L2) * tc; }
            }
            for (int k = 0; k + 1 < pts.Length; k++)
                if (bs <= st[k + 1] + 1e-5f) return Mathf.Lerp(ys[k], ys[k + 1], (bs - st[k]) / Mathf.Max(1e-5f, st[k + 1] - st[k]));
            return ys[ys.Length - 1];
        };
        // 縁の線(0.5m 刻み)を**芯の脚ごとの直線**へ間引く ── 折れ(向きが 5° を超えて変わる所)だけを節点に残す。
        //   ⛔ 細かく割らない: 区間の継ぎ目ごとに天端の勾配が「段の境」と読まれて段の駒が入り、継ぎ目に隙が出る(1.8m 割りで 0.73m の隙・2026-10-03)
        var nodes = new List<Vector2> { line[0] };
        for (int i = 1; i + 1 < line.Count; i++)
        {
            Vector2 d0 = (line[i] - nodes[nodes.Count - 1]).normalized, d1 = (line[i + 1] - line[i]).normalized;
            if (Vector2.Angle(d0, d1) > 5f && Vector2.Distance(nodes[nodes.Count - 1], line[i]) > 0.3f) nodes.Add(line[i]);
        }
        nodes.Add(line[line.Count - 1]);
        var segs = new List<EdoBuild.NozuraSeg>();
        for (int i = 0; i + 1 < nodes.Count; i++)
        {
            Vector2 a = nodes[i], b = nodes[i + 1];
            segs.Add(new EdoBuild.NozuraSeg { name = "Curb_" + nm + "_" + i, a = a, b = b,
                crestAt = sl => roadY(Vector2.Lerp(a, b, sl / Mathf.Max(1e-4f, Vector2.Distance(a, b)))) });
        }
        var heights = new List<float> { 0.30f, 0.60f, 0.90f };
        float back = 0f;
        foreach (var v in EdoBuild.BodyAt(EdoAssets.Own.SannoNozura(0.6f, 0f, 0), Vector3.zero, 0f, true)) back = Mathf.Max(back, -v.z);
        var log = new System.Text.StringBuilder();
        // 見え面を測る設計面: 縁の線より芯の側 = 路面、区画の線の側 = 路面 − 縁の丈(石が受ける側)。
        //   ⛔ 描かれた地表で測らない ── 縁の外の地盤が路面から 0.6 以内の所は両側の差が無く、見え面が路の側へ割れた(7 駒中 4)
        System.Func<Vector2, float> lineD = q => EdoGeom.DistToPolyEdge(Poly, q);
        System.Func<float, float, float> faceAt = (x, z) =>
        {
            var q = new Vector2(x, z); float best = float.MaxValue; Vector2 near = line[0];
            foreach (var c in line) { float dd = (c - q).sqrMagnitude; if (dd < best) { best = dd; near = c; } }
            return lineD(q) < lineD(near) ? roadY(near) - curbH : roadY(near);
        };
        var got = EdoBuild.PlaceNozuraNet(segs, EdoBuild.Ground, faceAt, back + 0.3f, grp,
            (h, g, i) => EdoAssets.Own.SannoNozura(h, g, i), (h, i) => EdoAssets.Own.SannoNozuraKado(h, i),
            (up, i) => EdoAssets.Own.SannoNozuraDan(up, i), (up, i) => EdoAssets.Own.SannoNozuraKiri(up, i),
            null, heights.ToArray(), new List<GameObject>(), log);
        // 硬い・区域: 駒の実メッシュが区画の外へ出ないか
        float worst = 0f;
        foreach (var kv in got)
            foreach (var v in EdoBuild.Body(kv.Key.transform, 999999))
            { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(Poly, q)) worst = Mathf.Max(worst, EdoGeom.DistToPolyEdge(Poly, q)); }
        return "  縁: 野面の乱積み " + got.Count + " 駒・区画の外へ出る量 " + worst.ToString("F3") + "m" + (worst > 0.005f ? " ⛔" : "")
             + "\n" + log.ToString().TrimEnd();
    }

    // ---------------------------------------------------------------- 造成の検査
    [MenuItem("Edo/岡部筑前守上屋敷/造成を検査 GradeQA")]
    public static void GradeQAMenu() { Debug.Log("[Okabe] " + GradeQA()); }

    /// <summary>敷地内の全セルで |地形 − 設計面| を測る。
    /// ⚠ **ハイトマップの格子の上でのみ測る。** `SampleHeight` を任意の座標で呼ぶと双一次補間が
    ///   入り、石垣の線や法面のような急な段で 0.1m のズレが 2m の差に化ける
    ///   (実測: 格子から 0.12m ずらして測っただけで 228 セルが「超過」に見えた)。</summary>
    public static string GradeQA() { return GradeQA(null); }

    class RampAx { public Vector2[] pts; public float[] ys; public float half; }
    class PadAx { public Vector2[] parcel, foot; public float y; public EdoBuild.PadRim rim; }

    /// <summary>勾配の面(指図 service[].yFrom)の上に据わった附属屋の**棟の下の均し**の範囲(足あと = EdoBuild.BodyFootWorld・高さ = 据わった躯体の底・
    /// 面 = TerracePolyAt)。Stage3(PlaceService)の LevelPad と同じ足あと・同じ面で造成QA が均しの跡を測る。</summary>
    static List<PadAx> ServicePads()
    {
        var res = new List<PadAx>();
        var root = GameObject.Find(GN); var grp = root == null ? null : root.transform.Find("Fuzoku/Service");
        if (grp == null) return res;
        var groups = new Dictionary<string, List<Vector2[]>>(); var groupY = new Dictionary<string, float>();
        foreach (var o in A(Get(D, "service")) ?? new List<object>())
        {
            var s2 = O(o); if (s2 == null || !Has(s2, "yFrom")) continue;
            var bt = grp.Find(S(s2["name"])); if (bt == null) continue;
            float du = F(s2["u1"]) - F(s2["u0"]), dv = F(s2["v1"]) - F(s2["v0"]);
            string path = AssetByKey(Has(s2, "asset") ? S(s2["asset"]) : null, Mathf.Max(du, dv), Mathf.Min(du, dv));
            var foot = EdoBuild.BodyFootWorld(bt.gameObject, path); if (foot == null) continue;
            if (Has(s2, "padGroup"))   // ⭐ 一枚の均し(Stage3 PlaceService と同じ: 凸包 EdoBuild.PadGroupFoot を組の底で)
            {
                string pg = S(s2["padGroup"]);
                if (!groups.ContainsKey(pg)) { groups[pg] = new List<Vector2[]>(); groupY[pg] = EdoBuild.RB(bt.gameObject).min.y; }
                groups[pg].Add(foot); continue;
            }
            var cq = (foot[0] + foot[2]) * 0.5f;
            res.Add(new PadAx { parcel = TerracePolyAt(cq), foot = foot, y = EdoBuild.RB(bt.gameObject).min.y, rim = PadRimAt(cq) });
        }
        foreach (var kv in groups)
        {
            var hull = EdoBuild.PadGroupFoot(kv.Value); if (hull == null) continue;
            var c = Vector2.zero; foreach (var q in hull) c += q; c /= hull.Length;
            res.Add(new PadAx { parcel = TerracePolyAt(c), foot = hull, y = groupY[kv.Key], rim = PadRimAt(c) });
        }
        return res;
    }

    /// <summary><paramref name="badAt"/> が null でなければ超過の節点(x, z, 地形−設計面)を入れて返す(測りの内訳)。</summary>
    public static string GradeQA(List<Vector3> badAt)
    {
        float TOL = ImplTol("gradeTol", 0.30f);
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        int x0, z0, w, h; Window(out x0, out z0, out w, out h);
        var H = td.GetHeights(x0, z0, w, h);
        var P = Poly;
        int bad = 0, all = 0, hole = 0, edge = 0; float mx = 0f, edgeMx = 0f; Vector2 worst = Vector2.zero;
        float cell = ts.x / (hres - 1);
        // ⭐ 縁の皮の升(Stage3b が地形に開けた穴)を囲む節点は描かれない ── 見えている面は皮が持ち、隙・浮きの表で測る。
        //   節点の4つの升が全部穴なら数えない(1つでも地形の升が残れば地形が見えるので数える)。件数は別に刷る
        // ⚠ GetHoles を窓で切って読むと返る配列が窓より小さい(2026-10-04 実測: 範囲外で穴と読み、区画の半分を「皮」と数えた)── 全面を読む
        int hr = td.holesResolution;
        var HO = td.GetHoles(0, 0, hr, hr);   // [z, x]・true = 地形の升・false = 穴
        System.Func<int, int, bool> solid = delegate(int cx, int cz)
        {
            if (cx < 0 || cz < 0 || cz >= HO.GetLength(0) || cx >= HO.GetLength(1)) return true;
            return HO[cz, cx];
        };
        int skin = 0, padN = 0, rampN = 0; float padMx = 0f, rampMx = 0f;
        float bfA = C("batterFill"), bcA = C("batterCut");
        var pads = ServicePads();
        var benches = new List<EdoBuild.BackBench>(); foreach (var kv in SodeBenches(null)) foreach (var bk in kv.Value) benches.Add(bk.Value);
        int benchN = 0; float benchMx = 0f;
        var toesQ = ToeBenches(null); int toeN = 0; float toeMx = 0f;
        var ramps = new List<RampAx>();
        foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
        {
            var r = O(o); if (r == null) continue;
            Vector2[] rpt; float[] rys; float rw; string rn;
            if (RampAxis(r, out rpt, out rys, out rw, out rn)) ramps.Add(new RampAx { pts = rpt, ys = rys, half = rw * 0.5f });
        }
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                var p = new Vector2(tp.x + (x0 + x) * ts.x / (hres - 1), tp.z + (z0 + z) * ts.z / (hres - 1));
                if (!EdoGeom.PIP(P, p)) continue;
                float y = Graded.At(p.x, p.y);
                if (float.IsNaN(y)) { hole++; continue; }
                int gx = x0 + x, gz = z0 + z;
                if (!solid(gx, gz) && !solid(gx - 1, gz) && !solid(gx, gz - 1) && !solid(gx - 1, gz - 1)) { skin++; continue; }
                all++;
                float d = Mathf.Abs((H[z, x] * ts.y + tp.y) - y);
                // ⭐ 段の縁: 設計面が地形の 1 升の内で TOL を超えて段違いになる所(段の石垣・土留めの線)は、
                //   格子の地形では描けない ── 見えている面は石垣と縁の皮(Stage3b)が描き、隙・浮きの表で測る。
                //   ⛔ 超過に混ぜず、⛔ 黙って捨てもしない ── 件数と最大を別に刷る(規則19)
                if (d > TOL)
                {
                    float lo = y, hi = y;
                    for (int k = 0; k < 4; k++)
                    {
                        float yy = Graded.At(p.x + (k == 0 ? cell : k == 1 ? -cell : 0f), p.y + (k == 2 ? cell : k == 3 ? -cell : 0f));
                        if (float.IsNaN(yy)) continue;
                        lo = Mathf.Min(lo, yy); hi = Mathf.Max(hi, yy);
                    }
                    if (hi - lo > TOL) { edge++; edgeMx = Mathf.Max(edgeMx, d); continue; }
                }
                // ⭐ 造成の後の均し(指図どおりの別の工事)の跡: 棟の下の均し(指図 service.yAt・EdoBuild.LevelPad)と坂の路盤(指図 ramps・EdoBuild.GradeSaka)。
                //   設計面(算出物 graded)はそれを知らないので、同じ式(LevelPadAt / SakaCenterAt+BatterTo)で設計面から寄せた高さと地形が合えば
                //   超過に数えず別に刷る(⛔ 黙って捨てない・規則19)。合わなければ超過のまま
                if (d > TOL)
                {
                    float gy = H[z, x] * ts.y + tp.y;
                    float ePad = y; foreach (var pd in pads) ePad = EdoBuild.LevelPadAt(pd.parcel, pd.foot, pd.y, bfA, bcA, cell, p, ePad, pd.rim);
                    if (Mathf.Abs(ePad - y) > 1e-3f && Mathf.Abs(gy - ePad) <= TOL) { padN++; padMx = Mathf.Max(padMx, d); continue; }
                    bool inRamp = false;
                    foreach (var rp in ramps)
                    {
                        float bd, bs, yr; if (!EdoBuild.SakaCenterAt(rp.pts, rp.ys, p, out bd, out bs, out yr)) continue;
                        float hh = Mathf.Max(0f, bd - rp.half); if (hh > 4f * Mathf.Max(bfA, bcA) + 2f * cell) continue;   // GradeSakaOnce の窓
                        float eR = EdoBuild.BatterTo(yr, hh, bfA, bcA, y);
                        // 路盤は芯の寄せ(⚠ 柔らかい・上限 toeFix)と描かれた法尻の締めで設計面から外れ得る ── 地形が設計面と坂の寄せの間(± TOL)なら坂の跡
                        if (Mathf.Abs(eR - y) > 1e-3f && gy >= Mathf.Min(y, eR) - TOL && gy <= Mathf.Max(y, eR) + TOL) { inRamp = true; break; }
                    }
                    if (inRamp) { rampN++; rampMx = Mathf.Max(rampMx, d); continue; }
                    float eB = EdoBuild.BackBenchesAt(benches, p, y);
                    if (Mathf.Abs(eB - y) > 1e-3f && Mathf.Abs(gy - eB) <= TOL) { benchN++; benchMx = Mathf.Max(benchMx, d); continue; }
                    float eT = y; foreach (var tk in toesQ) eT = EdoBuild.ToeBenchAt(tk, p, eT);
                    if (eT < y - 1e-3f && Mathf.Abs(gy - eT) <= TOL) { toeN++; toeMx = Mathf.Max(toeMx, d); continue; }
                }
                if (d > TOL) { bad++; if (badAt != null) badAt.Add(new Vector3(p.x, p.y, (H[z, x] * ts.y + tp.y) - y)); }
                if (d > mx) { mx = d; worst = p; }
            }
        return string.Format("造成QA 敷地内 {0} セル / 許容 {1:F2}m ｜ 超過 {2} ({3:F1}%) 最大 {4:F2}m @({5:F0},{6:F0}){7} {8}",
            all, TOL, bad, bad * 100f / Mathf.Max(1, all), mx, worst.x, worst.y,
            (hole > 0 ? " ｜ 算出物の穴 " + hole : "")
            + (padN > 0 ? string.Format(" ｜ 棟の下の均し(指図 service.yAt・LevelPad {0} 棟・超過に数えない) {1} セル 最大 {2:F2}m", pads.Count, padN, padMx) : "")
            + (rampN > 0 ? string.Format(" ｜ 坂の路盤と法(指図 ramps・GradeSaka・超過に数えない) {0} セル 最大 {1:F2}m", rampN, rampMx) : "")
            + (benchN > 0 ? string.Format(" ｜ 袖の背の小段の裏込め(指図 terraceWalls[].backfill・BackBenchAt・超過に数えない) {0} セル 最大 {1:F2}m", benchN, benchMx) : "")
            + (toeN > 0 ? string.Format(" ｜ 法尻の背の小段(指図 terraceWalls[].toeBench・ToeBenchAt・超過に数えない) {0} セル 最大 {1:F2}m", toeN, toeMx) : "")
            + (skin > 0 ? " ｜ 皮が描く升の内(数えない) " + skin + " 節点" : "") + (edge > 0 ? string.Format(" ｜ 段の縁(石垣・土留めが描く・超過に数えない) {0} セル 最大 {1:F2}m", edge, edgeMx) : ""),
            bad > 0 ? "✗" : "✔");
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
    /// <summary>区画線の上に据えた駒の頂点が float の往復で線を跨ぐ量の上限(実測 0.25mm)。測りの分解能で、狙いの緩めではない。</summary>
    const float SEAM_TOL = 0.001f;
    const float PAD_TOL = 0.02f;   // 附属屋の足あとの埋没・浮きの見逃し(測りの誤差)。硬い条件の許容0 の誤差幅で、設計値ではない
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
        EdoBuild.NaturalMode = false;      // 天端は run の seat で通す
        var kak = Group("Kakoi"); Clear(kak);

        // ---- 表長屋・表門(⭐ 練塀より**先**に据える)-----------------------
        //   隅の返し(短い練塀)は長屋の**実測の妻面**へ突き付けるので、先に据えて面を測る
        _nagayaSpan.Clear();
        string nagRep = PlaceOmoteNagaya(kak, wait);

        // ---- 隅の留め継ぎ(⭐ 練塀より**先**に据え、腕の実端面を測る)-----------
        //   ⛔ 隅は区画線の上に据わるので、run だけ犬走りへ寄せると隅が壁面より 0.76m 外へ張り出し、
        //     腕(±4.1m)が run の端と重なる(2026-09-21 実測)。⭕ 先に据えて犬走りへ寄せ、
        //     **辺の端の run の端を腕の実端面へ突き付ける**(`EdoBuild.KadoFace` / `KadoArm`・docs/oki-kata.md §2)。
        sb.AppendLine(PlaceKado(kak));
        var kadoLo = new Dictionary<int, float>();   // 辺 → 隅の壁体が s=0 側から覆う上限
        var kadoHi = new Dictionary<int, float>();   // 辺 → 隅の壁体が s=L 側から覆う下限
        sb.AppendLine(FitKado(kak, kadoLo, kadoHi));
        var edgeMinS0 = new Dictionary<int, float>(); var edgeMaxS1 = new Dictionary<int, float>();
        foreach (var r0 in Runs)
        {
            float q0;
            if (!edgeMinS0.TryGetValue(r0.edge, out q0) || r0.s0 < q0) edgeMinS0[r0.edge] = r0.s0;
            if (!edgeMaxS1.TryGetValue(r0.edge, out q0) || r0.s1 > q0) edgeMaxS1[r0.edge] = r0.s1;
        }

        // ---- 通用口(小門)を練塀より**先**に据え、脇の面(札の jamb)を袖の練塀の端に採る ----
        _komonJamb.Clear();
        sb.AppendLine(PlaceKomon());

        // ---- 練塀 ------------------------------------------------------
        int hei = 0, skipped = 0;
        foreach (var r in Runs)
        {
            if (r.Nagaya) continue;                       // 表長屋は下でまとめて据える
            if (!r.Dobei)
            { sb.AppendLine("★ run " + r.name + " の kind が未知: " + r.kind); continue; }
            Vector2 outw = OutNormal(r.edge);
            // ⭐ **隅の返し**の納め(指図「隅の納め」の章・K063 章番号で引かない)。隣が長屋の run なら、その**実測の妻面**へ突き付ける。
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
            // ⭐ 小門の脇:門構えの脇の面(札の jamb)へ突き付ける(⛔ 指図の s で止めない ── 門の柱と 0.63m 開いた・EDO-0502)
            foreach (var kj in _komonJamb)
            {
                if ((int)kj.x != r.edge) continue;
                if (Mathf.Abs(r.s1 - kj.y) < 0.60f) { wait.Add("練塀 " + r.name + ": 小門の脇の面へ s1 " + rs1.ToString("0.###") + " → " + (kj.y + KOMON_BITE).ToString("0.###")); rs1 = kj.y + KOMON_BITE; }
                if (Mathf.Abs(r.s0 - kj.z) < 0.60f) { wait.Add("練塀 " + r.name + ": 小門の脇の面へ s0 " + rs0.ToString("0.###") + " → " + (kj.z - KOMON_BITE).ToString("0.###")); rs0 = kj.z - KOMON_BITE; }
            }
            // ⭐ **辺の端の run だけ**を、隅の腕の実端面へ突き付ける(辺の途中の run は触らない)。
            //   ⛔ 呼び寸法で継がない — 腕は部材が持つ寸法で、run の端は腕が決める。
            float qa; bool cornerEnd0 = false, cornerEnd1 = false;
            if (r.s0 <= edgeMinS0[r.edge] + 1e-3f && kadoLo.TryGetValue(r.edge, out qa)) { rs0 = qa; cornerEnd0 = true; }
            if (r.s1 >= edgeMaxS1[r.edge] - 1e-3f && kadoHi.TryGetValue(r.edge, out qa)) { rs1 = qa; cornerEnd1 = true; }
            // ⭐ 辺の端の練塀が隣の辺の線へ斜めに当たる端は、端を隣の辺の線で切った駒(DobeiKiri)で納める(EDO-0502 2026-10-03)。
            //   隅の腕の無い端だけ。焼いてある角だけ(KiriEnd が null なら直角の端のまま)。
            var kiris = new List<KeyValuePair<string, Vector3>>();
            if (!cornerEnd0 && r.s0 < 0.01f) { var k0 = KiriEnd(r, true, ref rs0); if (k0.Key != null) kiris.Add(k0); }
            if (!cornerEnd1 && r.s1 > EdgeLen(r.edge) - 0.01f) { var k1 = KiriEnd(r, false, ref rs1); if (k1.Key != null) kiris.Add(k1); }
            foreach (var kn0 in _kiriNotes) wait.Add("練塀 " + kn0); _kiriNotes.Clear();
            // 切った駒だけで run が埋まる(残りの直線が 0.5 未満・隅の腕と重なる)なら、切った駒だけを据える ── 重なりは隅の腕の中へ埋める(oki-kata §4)
            bool kiriOnly = kiris.Count > 0 && rs1 - rs0 < 0.5f;
            if (kiriOnly)
                wait.Add("練塀 " + r.name + ": 切った駒の直角の端と隅の腕の実端面が " + (rs0 - rs1).ToString("F2") + "m 重なる ── 直線の駒を置かず切った駒だけ(重なりは隅の腕の中)");
            else if (rs1 - rs0 < 0.5f)
            { wait.Add("練塀 " + r.name + ": 隅の腕の実端面で挟むと長さが " + (rs1 - rs0).ToString("F2") + "m — 据えない"); continue; }
            foreach (var kk in kiris)
            {
                var kg = EdoBuild.Place(kk.Key, new Vector3(kk.Value.x, kk.Value.y, kk.Value.z), Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg, Vector3.one, kak, "Kiri_" + r.name);
                _kiriPlaced.Add(kg);
                wait.Add("練塀 " + r.name + ": 端を隣の辺の線で切った駒 " + System.IO.Path.GetFileNameWithoutExtension(kk.Key) + " を据え、残りを直角の端 s " + rs0.ToString("0.###") + "〜" + rs1.ToString("0.###") + " で継いだ");
            }
            if (cornerEnd0 || cornerEnd1)
                wait.Add("練塀 " + r.name + ": 隅の腕の実端面へ突き付けた s " + r.s0.ToString("0.###") + "〜" + r.s1.ToString("0.###")
                       + " → " + rs0.ToString("0.###") + "〜" + rs1.ToString("0.###"));
            if (kiriOnly) { hei++; continue; }
            Vector2 a = EdgePt(r.edge, rs0), b = EdgePt(r.edge, rs1);
            if (Mathf.Abs(r.seat1 - r.seat0) < 0.01f)
            {
                EdoBuild.DobeiRun(kak, a, b, outw, r.name, false, r.seat0, Vector2.zero, -1);
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
                    float sMid = Mathf.Lerp(rs0, rs1, (q + 0.5f) / nSeg);
                    EdoBuild.DobeiRun(kak, pa, pb, outw, r.name + "_" + q, false,
                                                    r.SeatAt(sMid), Vector2.zero, -1);
                }
                hei++;
            }
        }
        sb.AppendLine(nagRep);
        sb.AppendLine("練塀: " + hei + " run 据えた");

        // ---- 犬走りへ寄せる(据えた駒の実メッシュから外面を測る)----------
        sb.AppendLine(AlignInubashiri());
        // 硬い・区域(許容0・EDO-0502): 練塀の駒の壁体(屋根を除く)が隅で隣の辺を跨ぐなら、走りに沿って引いて収める
        //   (EdoBuild.KeepInsidePoly ── 犬走りの控えは動かない)。SE_Hei_0b の腰の石垣が 0.053m 出ていた。
        {
            int pulledH = 0; float worstH = 0f; string worstHN = null; var goneH = new List<string>();
            var kids = new List<Transform>(); foreach (Transform c in kak) kids.Add(c);
            foreach (var c in kids)
            {
                int ri = -1;
                for (int k = 0; k < Runs.Length; k++)
                    if (c.name.StartsWith(Runs[k].name + "_") && (ri < 0 || Runs[k].name.Length > Runs[ri].name.Length)) ri = k;
                if (ri < 0 || !Runs[ri].Dobei) continue;
                float wasH; float mv = EdoBuild.KeepInsidePoly(c.gameObject, Poly, EdgePt(Runs[ri].edge, 1f) - EdgePt(Runs[ri].edge, 0f), 0.30f, out wasH, 0.005f, SEAM_TOL);
                if (float.IsNaN(mv)) { goneH.Add(c.name + " " + wasH.ToString("F3")); continue; }
                if (mv != 0f) { pulledH++; if (wasH > worstH) { worstH = wasH; worstHN = c.name; } }
            }
            sb.AppendLine("練塀の壁体を区画の内へ走りに沿って引いた " + pulledH + " 駒(最も出ていた " + worstH.ToString("F3") + "m @" + (worstHN ?? "-") + ")"
                        + (goneH.Count > 0 ? "\n★ 0.30m 引いても区画の外: " + string.Join(" / ", goneH.ToArray()) : ""));
        }

        // ---- 端を切った練塀の駒の実測(EDO-0502)── 隣の練塀との継ぎ目の口・隣の辺の線との口・区画の外へ出る量
        foreach (var kg in _kiriPlaced)
        {
            if (kg == null) continue;
            string rn = kg.name.Substring(5); int ri = -1; for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == rn) ri = k; if (ri < 0) continue;
            var rr = Runs[ri]; Vector2 a0 = EdgePt(rr.edge, 0f), dir = (EdgePt(rr.edge, 1f) - a0).normalized;
            var kv = EdoBuild.Body(kg.transform, 999999);
            float ks0 = float.MaxValue, ks1 = float.MinValue, outMax = 0f, nearLine = float.MaxValue;
            var P2 = Poly; int n2 = P2.Length;
            bool atStart = Vector2.Dot(new Vector2(kg.transform.position.x, kg.transform.position.z) - a0, dir) < EdgeLen(rr.edge) * 0.5f;
            int ne = atStart ? (rr.edge - 1 + n2) % n2 : (rr.edge + 1) % n2;
            foreach (var v in kv)
            {
                var q = new Vector2(v.x, v.z); float sv = Vector2.Dot(q - a0, dir); ks0 = Mathf.Min(ks0, sv); ks1 = Mathf.Max(ks1, sv);
                if (!EdoGeom.PIP(P2, q)) outMax = Mathf.Max(outMax, EdoGeom.DistToPolyEdge(P2, q));
                nearLine = Mathf.Min(nearLine, EdoGeom.DistToEdge(q, P2[ne], P2[(ne + 1) % n2]));
            }
            float ps0 = float.MaxValue, ps1 = float.MinValue;
            foreach (Transform c in kak) if (c.name.StartsWith(rr.name + "_")) foreach (var v in EdoBuild.Body(c, 999999)) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - a0, dir); ps0 = Mathf.Min(ps0, sv); ps1 = Mathf.Max(ps1, sv); }
            float seam = ps0 == float.MaxValue ? float.NaN : (atStart ? ps0 - ks1 : ks0 - ps1);    // + = 口 / − = 重なり / NaN = 直線の駒なし
            sb.AppendLine("端を切った練塀 " + kg.name + ": 隣の練塀との継ぎ目 " + (float.IsNaN(seam) ? "-(直線の駒なし・隅の腕と重なる)" : seam.ToString("+0.000;-0.000") + "m") + "・隣の辺の線までの最寄り " + nearLine.ToString("F3") + "m・区画の外 " + outMax.ToString("F3") + "m"
                        + (seam > 0.005f || nearLine > 0.02f || outMax > 0.005f ? " ★" : " ✔"));
        }
        _kiriPlaced.Clear();

        // ---- 石垣基壇 --------------------------------------------------
        sb.AppendLine(PlaceIshigaki());
        // ---- 硬い・地面(浮き 0): 練塀・隅・端を切った駒を、描かれた地表と基壇の天端の高い方へ組ごと据える(EdoBuild.SinkGroupToBed)。
        //      ⛔ 指図の seat(下絵の値)を底に残さない ── 辺34 で 2.6〜2.8m 埋まった(2026-10-04 EDO-0502 第12巡)。
        sb.AppendLine(SeatHeiOnBed(kak));

        // ---- 通用口(小門)── ⭐ 練塀より先に据えた(門構えを先に・docs/oki-kata.md §2)

        // ---- 木柵 ------------------------------------------------------
        sb.AppendLine(PlaceFences());

        if (wait.Count > 0)
        {
            sb.AppendLine("── 外周で据えなかったもの " + wait.Count + " 件 ──");
            foreach (var w in wait) sb.AppendLine("  ★ " + w);
        }
        return sb.ToString();
    }

    /// <summary>**区画の角で留めた表長屋の版**(EDO-0502 2026-10-03)を引く。run の端が辺の端(頂点)に在り、隣の辺の run も長屋で、
    /// 区画の線が長屋の外へ折れる(頂点の符号付きの折れ > 0.05° ── 岡部 頂点 15〜18 = 8.93/3.60/1.59/10.06)なら、その端の妻を
    /// 二等分の面へ寝かせた版(<c>EdoAssets.Own.NagayaOmote2FKutaiMiter</c> / <c>NagayaOmoteMonKutaiMiter</c> と同じ綴り `_m{L}x{R}`)。
    /// <paramref name="sSign"/> = 据えた駒の局所 +X が s の増える向きなら +1(−X = s0 側)。焼いていなければ元のパスと ⚠。
    /// 条件: 硬い(許容0 の隙 ── 直角の妻を折れに並べると外に楔の口)。当たる先: 外周の長屋が区画の折れで継ぐ所(岡部の辺14〜18。
    /// 内へ折れる頂点 13/14/19 は直角のまま=焼いた名 m0)。</summary>
    static string MiterOf(string kutaiPath, Run r, float sSign, out string warn)
    {
        warn = null;
        if (string.IsNullOrEmpty(kutaiPath) || !kutaiPath.EndsWith("_kutai.fbx")) return kutaiPath;
        var P = Poly; int n = P.Length;
        Func<int, float> fold = v =>
        {
            Vector2 a = P[(v - 1 + n) % n], b = P[v % n], c = P[(v + 1) % n];
            Vector2 d1 = b - a, d2 = c - b;
            return Mathf.Atan2(d1.x * d2.y - d1.y * d2.x, Vector2.Dot(d1, d2)) * Mathf.Rad2Deg;
        };
        string rn = r.name;
        Func<int, bool> nagayaOn = e => { foreach (var q in Runs) if (q.Nagaya && q.edge == e && q.name != rn) return true; return false; };
        float th0 = 0f, th1 = 0f;
        if (r.s0 < 0.01f && nagayaOn((r.edge - 1 + n) % n)) { float f = fold(r.edge); if (f > 0.05f) th0 = f; }
        if (r.s1 > EdgeLen(r.edge) - 0.01f && nagayaOn((r.edge + 1) % n)) { float f = fold(r.edge + 1); if (f > 0.05f) th1 = f; }
        if (th0 == 0f && th1 == 0f) return kutaiPath;
        float thL = sSign >= 0f ? th0 : th1, thR = sSign >= 0f ? th1 : th0;
        string mp = kutaiPath.Substring(0, kutaiPath.Length - 4) + "_m" + Mathf.RoundToInt(thL * 10f) + "x" + Mathf.RoundToInt(thR * 10f) + ".fbx";
        if (AssetDatabase.LoadAssetAtPath<GameObject>(mp) != null) return mp;
        warn = r.name + ": 区画の折れ(−X " + thL.ToString("F2") + "° / +X " + thR.ToString("F2") + "°)の留めの版が焼いていない " + System.IO.Path.GetFileName(mp) + " ── 直角の妻のまま";
        return kutaiPath;
    }

    static readonly List<GameObject> _kiriPlaced = new List<GameObject>();
    static readonly List<string> _kiriNotes = new List<string>();
    /// <summary>**練塀の端を隣の辺の線で斜めに切った駒の据え場所**(EDO-0502 2026-10-03・部材の約束は <c>EdoAssets.Own.DobeiKiri</c>)。
    /// position = 犬走りへ寄せた外面の線(辺の線から INUBASHIRI 内)と隣の辺の線の交点・y = その端の座(run の SeatAt)・
    /// yaw = 外向き法線(局所 +Z)。局所 +X が角の側を向かない(手の違う)ときと、焼いていない角は据えない(null)。
    /// 据えるなら run の端 <paramref name="sEnd"/> を札の直角の端(foot の x の最小)まで退かせる。
    /// 条件: 硬い(許容0 の隙・区域侵犯 ── 直角の端は隣の辺の線との間に楔の口を残すか線を越える)。
    /// 当たる先: 辺の端の練塀で隅の腕の無い所(岡部 SE_Hei の始め=頂点 0 / S_Hei_21 の終わり=頂点 25)。他邸は未適用。</summary>
    static KeyValuePair<string, Vector3> KiriEnd(Run r, bool atStart, ref float sEnd)
    {
        var none = new KeyValuePair<string, Vector3>(null, Vector3.zero);
        var P = Poly; int n = P.Length; int e = r.edge;
        int ne = atStart ? (e - 1 + n) % n : (e + 1) % n;
        Vector2 a0 = P[e % n], dir = (P[(e + 1) % n] - a0).normalized, outw = OutNormal(e);
        Vector2 nb0 = P[ne], nbd = (P[(ne + 1) % n] - nb0).normalized;
        // ⭐ 隣の辺の角の側に長屋が据わっていれば、切る線は隣の辺の線でなく**長屋の実測の妻面**(辺に直角・_nagayaSpan = 据えた躯体の実端)
        //   (EDO-0502 第9巡 buzai6 716_L ── N_Hei_35 の終わりは表門の門長屋 N39_0 の妻で切る)
        //   どちらで切るかは**走りが正面から当たる方**(走りとなす角が直角に近い方)── 浅い折れ(辺38→39・18°)は妻へ、
        //   深い角(辺0→41・95°)は隣の辺の線へ当たる(長屋の妻は練塀の走りとほぼ平行で当たらない)。
        string cutBy = "隣の辺の線";
        System.Func<Vector2, float> degOf = v => { float a1 = Vector2.Angle(dir, v); return Mathf.Min(a1, 180f - a1); };
        foreach (var nr in Runs)
        {
            if (!nr.Nagaya || nr.edge != ne || !_nagayaSpan.ContainsKey(nr.name)) continue;
            var span = _nagayaSpan[nr.name]; Vector2 gd = OutNormal(ne);
            bool hit = (!atStart && nr.s0 < 0.30f) || (atStart && nr.s1 > EdgeLen(ne) - 0.30f);
            if (!hit || degOf(gd) <= degOf(nbd)) continue;
            nb0 = EdgePt(ne, atStart ? span.y : span.x); nbd = gd; cutBy = "長屋 " + nr.name + " の妻面"; break;
        }
        float deg = degOf(nbd);
        if (deg < 1f || deg > 89.5f) return none;
        // ⭐ 入隅(区画の内から見て 180° を超える角 ── 隣の辺が外へ折れる)は切らない(2026-10-06 EDO-0502 第36巡)。
        //   隣の辺の線を角の手前へ延ばした線で外面を切ると、外面が角の 0.61m 手前で止まり、角から先の木柵との間に口が開いた(辺24 の終わり・Kiri_S_Hei_21)。
        //   入隅では外面の線は角まで区画の内に在る ⇒ 直角の端のまま走りの端(角)まで通す。当たる先: 辺の端の練塀を切った駒で納める全邸の入隅。
        if (cutBy == "隣の辺の線" && (atStart ? Vector2.Dot(nbd, outw) < -0.05f : Vector2.Dot(nbd, outw) > 0.05f))
        {
            _kiriNotes.Add(r.name + (atStart ? " の始め" : " の終わり") + ": 入隅(隣の辺が外へ " + deg.ToString("F1") + "° 折れる)── 切らずに直角の端で角まで通す");
            return none;
        }
        // 外面の線 F(t) = a0 − outw·INUBASHIRI + dir·t と切る線の交点
        Vector2 f0 = a0 - outw * INUBASHIRI;
        float det = dir.x * (-nbd.y) - dir.y * (-nbd.x); if (Mathf.Abs(det) < 1e-5f) return none;
        Vector2 rhs = nb0 - f0; float t = (rhs.x * (-nbd.y) - rhs.y * (-nbd.x)) / det;
        Vector2 X = f0 + dir * t;
        // 局所 +X(= (cosψ, −sinψ)・ψ = 外向きの方位)が角の側を向けば素手(L)、逆なら逆手(R ── 切る端は −X)
        float psi = Mathf.Atan2(outw.x, outw.y);   // ラジアン
        Vector2 lx = new Vector2(Mathf.Cos(psi), -Mathf.Sin(psi)); Vector2 toward = atStart ? -dir : dir;
        bool rev = Vector2.Dot(lx, toward) < 0f;
        if (Mathf.Abs(Vector2.Dot(lx, toward)) < 0.5f) return none;
        string path = EdoAssets.Own.DobeiKiri(deg, true, rev);
        string tag = r.name + (atStart ? " の始め" : " の終わり") + ": " + System.IO.Path.GetFileNameWithoutExtension(path);
        if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { _kiriNotes.Add(tag + " は焼いていない ── 直角の端のまま"); return none; }
        var spc = EdoPartSpec.Get(path); if (spc == null || spc.foot == null || spc.foot.Count == 0) { _kiriNotes.Add(tag + " の札が無い ── 据えない"); return none; }
        // 硬い(区域): 切る線との交点が区画の外なら、口の原因は切る線の側(長屋の妻の位置)── 据えずに報告
        if (!EdoGeom.PIP(P, X) && EdoGeom.DistToPolyEdge(P, X) > 0.005f)
        { _kiriNotes.Add(tag + ": 外面の線と" + cutBy + "の交点が区画の線より " + EdoGeom.DistToPolyEdge(P, X).ToString("F3") + "m 外 ── 据えない(口の原因は" + cutBy + "の位置)"); return none; }
        float d = 0f; foreach (var q in spc.foot) d = Mathf.Max(d, Mathf.Abs(q.x));   // 直角の端までの走り(局所 x・素手は負・逆手は正)
        float sx = Vector2.Dot(X - a0, dir);
        sEnd = atStart ? sx + d : sx - d;
        _kiriNotes.Add(tag + "(" + (rev ? "逆手" : "素手") + "・角 " + deg.ToString("F2") + "°・切る線 = " + cutBy + ")");
        return new KeyValuePair<string, Vector3>(path, new Vector3(X.x, r.SeatAt(sEnd), X.y));
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
            // ⭐ 案1(EDO-0502): 門長屋 ── `gate.host` / `komon[].host` がこの run を名指しするなら、
            //   口を駒の中に抜いた版(NagayaOmoteMon)を引く。口の位置は**部材のローカル +X の端から**
            //   測る(生成器の `--gate <左端から>`)。どちらの端が s0 側かは据えてから実ベクトルで見る
            //   ので、ここでは s0 側から測った版を先に引き、PlaceNagayaPiece の後で向きを検めて引き直す。
            float gS, gW; string gLabel; bool hosted = HostedGate(r.name, out gS, out gW, out gLabel);
            if (hosted && (key == null || !key.Contains("NagayaOmoteMon")))
                path = EdoAssets.Own.NagayaOmoteMon(call, Mathf.Round((gS - r.s0) * 1000f) / 1000f, nikai);
            // ⭐ 躯体 = 呼び寸法の版(_kutai)を引く(EDO-0502 2026-10-03)── 継ぎ目は札の躯体の端どうしで突き付ける
            path = EdoAssets.Own.KutaiOf(path);
            if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            {
                miss++;
                wait.Add("表長屋 " + r.name + "(run " + call.ToString("0.###") + "m"
                       + (nikai ? "・二階" : "") + "): 部材が無い " + (path ?? key)
                       + " → blender --background --python Tools/Blender/build_nagaya_omote.py -- "
                       + call.ToString("0.###") + (nikai ? " --floors 2" : ""));
                continue;
            }
            // ⭐ 区画の外へ折れる角は妻を留めた版(MiterOf)── −X = s0 側と見て引き、据えた向きで検めて違えば引き直す
            string mw; path = MiterOf(path, r, 1f, out mw); if (mw != null) wait.Add(mw);
            if (PlaceNagayaPiece(kak, r.name, path, r.edge, (r.s0 + r.s1) * 0.5f,
                                 r.SeatAt((r.s0 + r.s1) * 0.5f), call, wait, ref lastH))
            {
                {
                    var tP = kak.Find(r.name);
                    if (tP != null && path.Contains("_kutai_m"))
                    {
                        Vector3 dx = tP.rotation * Vector3.right; float smid = (r.s0 + r.s1) * 0.5f;
                        Vector2 ed = (EdgePt(r.edge, smid + 1f) - EdgePt(r.edge, smid)).normalized;
                        if (dx.x * ed.x + dx.z * ed.y < 0f)
                        {
                            string mw2, p2 = MiterOf(EdoAssets.Own.KutaiOf(path.Substring(0, path.LastIndexOf("_m")) + ".fbx"), r, -1f, out mw2);
                            if (mw2 != null) wait.Add(mw2);
                            if (p2 != path) { var old = tP.gameObject; old.name = r.name + "__old"; float d0 = 0f; PlaceNagayaPiece(kak, r.name, p2, r.edge, smid, r.SeatAt(smid), call, wait, ref d0); UnityEngine.Object.DestroyImmediate(old); path = p2; }
                        }
                        sb.Append("  " + r.name + ": 留めの版 " + System.IO.Path.GetFileNameWithoutExtension(path) + "\n");
                    }
                }
                made++; if (!hosted) nagH = lastH;
                if (hosted) sb.Append(GateInNagaya(kak, r, call, nikai, gS, gW, gLabel, wait));
            }
        }

        // ---- 表門 — 長屋の躯体に門口を抜いた版(裁定12=A)
        {
            var g = O(Get(D, "gate"));
            var gp = g == null ? null : O(Get(g, "plan"));
            // 案1(EDO-0502): 門長屋(`gate.host`)の口は上の run の駒が持つ ── 別の門を据えない(二重になる)
            if (gp != null && Has(gp, "monW") && !Has(g, "host"))
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

        // ⭐ 継ぎ目は札の躯体の端どうしを**平行移動だけで**突き付ける(EdoBuild.AbutBodyAlong・2026-10-03 EDO-0502)。
        //   ⛔ 伸縮しない(docs/oki-kata.md §2「長さの固定された部材は平行移動だけ」・柱間 1.818m)。駒は躯体 = 呼び寸法の版(_kutai)で、
        //   破風は躯体の端から外へ 0.322 ずつ出て隣と重なる(埋めて隠す)。固定側 = 門長屋(口を持つ駒)、無ければ辺の最初の駒。
        //   端数は鎖の末端の練塀・隅の返し(_nagayaSpan を読む)へ流す。硬い: 継ぎ目の隙 0(< 0.001m)。
        {
            float worstSeam = 0f; string worstSeamN = null; int seams = 0, moved = 0; var cornerBack = new List<string>();
            var byEdge = new SortedDictionary<int, List<Run>>();
            foreach (var r in Runs)
            {
                if (!r.Nagaya || kak.Find(r.name) == null) continue;
                List<Run> l; if (!byEdge.TryGetValue(r.edge, out l)) byEdge[r.edge] = l = new List<Run>(); l.Add(r);
            }
            foreach (var kv in byEdge)
            {
                var rs = kv.Value; rs.Sort((x, y) => x.s0.CompareTo(y.s0));
                Vector2 o0 = EdgePt(kv.Key, 0f), ax = (EdgePt(kv.Key, 1f) - EdgePt(kv.Key, 0f)).normalized;
                int fix = 0; float a1, a2; string a3;
                for (int i = 0; i < rs.Count; i++) if (HostedGate(rs[i].name, out a1, out a2, out a3)) { fix = i; break; }
                // 固定側から外へ、前の相手の躯体の端まで
                for (int i = fix + 1; i < rs.Count; i++)
                {
                    if (Mathf.Abs(rs[i - 1].s1 - rs[i].s0) > 0.30f) continue;   // 間に門・袖が挟まる ── 鎖が切れる
                    var prev = EdoBuild.SpecBodySpanAlong(kak.Find(rs[i - 1].name).gameObject, o0, ax);
                    float d = EdoBuild.AbutBodyAlong(kak.Find(rs[i].name).gameObject, o0, ax, prev.y, true);
                    if (float.IsNaN(d)) wait.Add("長屋 " + rs[i].name + ": 札が無く躯体の端を測れない ── 据えたまま");
                    else if (Mathf.Abs(d) > 0.0005f) moved++;
                }
                for (int i = fix - 1; i >= 0; i--)
                {
                    if (Mathf.Abs(rs[i].s1 - rs[i + 1].s0) > 0.30f) continue;
                    var next = EdoBuild.SpecBodySpanAlong(kak.Find(rs[i + 1].name).gameObject, o0, ax);
                    float d = EdoBuild.AbutBodyAlong(kak.Find(rs[i].name).gameObject, o0, ax, next.x, false);
                    if (float.IsNaN(d)) wait.Add("長屋 " + rs[i].name + ": 札が無く躯体の端を測れない ── 据えたまま");
                    else if (Mathf.Abs(d) > 0.0005f) moved++;
                }
                // 硬い・区域: 隅の端の駒の腰が隣の辺を跨ぐなら、隅から走りに沿って 0.02m ずつ引く(上限 0.60m)。
                //   ⛔ 伸縮しない ── 引いた分は隣の駒の躯体と重なる(埋めて隠す)か、隅の返しの練塀が受ける。
                float L = EdgeLen(kv.Key);
                foreach (var r in rs)
                {
                    var go = kak.Find(r.name).gameObject;
                    bool cLo = r.s0 < 0.30f, cHi = r.s1 > L - 0.30f;
                    if (!cLo && !cHi) continue;
                    float was = EdoBuild.WaistOutside(go, Poly), back = 0f;
                    if (was <= SEAM_TOL) continue;
                    float dir = cHi && !cLo ? -1f : (cLo && !cHi ? 1f : 0f);
                    if (dir == 0f) { wait.Add("長屋 " + r.name + ": 両端が隅で腰が " + was.ToString("F3") + "m 区画の外 ── 平行移動では収まらない・据えたまま"); continue; }
                    while (back < 0.60f && EdoBuild.WaistOutside(go, Poly) > SEAM_TOL)
                    { go.transform.position += new Vector3(ax.x, 0f, ax.y) * (0.02f * dir); back += 0.02f; }
                    float now = EdoBuild.WaistOutside(go, Poly);
                    cornerBack.Add(r.name + " " + back.ToString("F2") + "m(腰の出 " + was.ToString("F3") + "→" + now.ToString("F3") + ")");
                    if (now > SEAM_TOL) wait.Add("長屋 " + r.name + ": 隅から 0.60m 引いても腰が " + now.ToString("F3") + "m 区画の外");
                }
                // 継ぎ目の実測(札の躯体の端どうし)
                for (int i = 1; i < rs.Count; i++)
                {
                    if (Mathf.Abs(rs[i - 1].s1 - rs[i].s0) > 0.30f) continue;
                    var p0 = EdoBuild.SpecBodySpanAlong(kak.Find(rs[i - 1].name).gameObject, o0, ax);
                    var p1 = EdoBuild.SpecBodySpanAlong(kak.Find(rs[i].name).gameObject, o0, ax);
                    float gap = p1.x - p0.y; seams++;
                    if (gap > worstSeam || worstSeamN == null) { if (gap > worstSeam) worstSeam = gap; worstSeamN = rs[i - 1].name + "|" + rs[i].name; }
                    if (gap > 0.001f) wait.Add("長屋の継ぎ目 " + rs[i - 1].name + "|" + rs[i].name + ": 躯体の隙 " + gap.ToString("F3") + "m");
                }
            }
            foreach (var r in Runs)
            {
                if (!r.Nagaya) continue; var t = kak.Find(r.name); if (t == null) continue;
                Vector2 o0 = EdgePt(r.edge, 0f), ax = EdgePt(r.edge, 1f) - EdgePt(r.edge, 0f);
                // 隅の返し(短い練塀)が突き付く区間 = **躯体の端**(⛔ 破風の端へ寄せない ── 0.322m の口が残った)
                var sp = EdoBuild.SpecBodySpanAlong(t.gameObject, o0, ax);
                if (float.IsNaN(sp.x)) sp = EdoBuild.BodySpanAlong(t.gameObject, o0, ax);
                if (!float.IsNaN(sp.x)) _nagayaSpan[r.name] = sp;
            }
            sb.Append("(長屋の継ぎ目を札の躯体の端で突き付けた: 継ぎ目 " + seams + "・最大の隙 " + worstSeam.ToString("F4") + "m @" + (worstSeamN ?? "-")
                    + "・平行移動 " + moved + " 棟" + (cornerBack.Count > 0 ? "・隅から引いた " + string.Join(" / ", cornerBack.ToArray()) : "") + ")");
        }

        // 硬い・区域(許容0・EDO-0502): 表長屋と表門は**一組のまま**(面を揃えたまま)、腰(1.2m)より下で
        //   一番外へ出ている実頂点が区画の線に収まるまで列ごと内へ寄せる(表門の腰の出が 0.051m 越えていた)。
        //   ⛔ 門だけ寄せない(長屋と面がずれる)。軒は越えてよいので腰で測る。走りの s は変わらない(_nagayaSpan はそのまま)。
        {
            var byEdge = new Dictionary<int, List<GameObject>>();
            foreach (Transform c in kak)
            {
                int ed = -1;
                foreach (var r in Runs) if (r.Nagaya && r.name == c.name) ed = r.edge;
                if (c.name == "Omotemon") { var g2 = O(Get(D, "gate")); if (g2 != null) ed = (int)F(g2["edge"]); }
                if (ed < 0) continue;
                List<GameObject> l; if (!byEdge.TryGetValue(ed, out l)) byEdge[ed] = l = new List<GameObject>(); l.Add(c.gameObject);
            }
            foreach (var kv in byEdge)
            {
                float was;
                float d = EdoBuild.InsetRunToPoly(kv.Value, Poly, -OutNormal(kv.Key), 0.50f, out was, 0.01f, SEAM_TOL, 1.2f);
                if (float.IsNaN(d)) wait.Add("表長屋・表門 辺" + kv.Key + ": 0.50m 寄せても腰が区画の外(" + was.ToString("F3") + "m)── 据えたまま");
                else if (d > 0f) sb.Append("(表長屋・表門 " + kv.Value.Count + " 棟を一組で内へ " + d.ToString("F2") + "m ── 腰が " + was.ToString("F3") + "m 出ていた)");
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
            // 案1: 門長屋(gate.host)なら、その駒の実丈で見る(⛔ 最後に据えた駒の丈で門を裁かない)
            string gh = S(Get(O(Get(D, "gate")), "host"));
            if (gh != null) { var ht = kak.Find(gh); lastH = ht != null ? EdoBuild.RB(ht.gameObject).size.y : 0f; }
            if (gp2 != null && Has(gp2, "monH") && lastH > 0.1f && Mathf.Abs(lastH - F(gp2["monH"])) > 0.15f)
                wait.Add("表門の棟高: 指図 gate.plan.monH " + F(gp2["monH"]).ToString("0.###")
                       + "m / 据えた現物の実丈 " + lastH.ToString("0.###") + "m");
        }
        sb.Append("表長屋・表門: " + made + " 棟" + (nikai ? "(二階)" : "(平屋)")
                + (miss > 0 ? " / 部材の無いもの " + miss : ""));
        return sb.ToString();
    }

    /// <summary>**門長屋の口の向きを検めて、要れば引き直す**(案1・EDO-0502)。
    /// 口の芯は部材のローカル +X で `len/2 − gc`(gc = 生成器の `--gate` の左端からの距離。
    /// 2026-10-03 に 17.68_mon5.5 / 20.07_mon16 の奥の壁の抜けで実測: 芯 +3.34 / −5.96)。
    /// 据えた駒の +X が s の増える向きなら口は s = sMid + (len/2 − gc)、減る向きなら s = sMid − (len/2 − gc)。
    /// ⭕ 指図の口の s に合う gc を実ベクトルから出し、違えばその版で据え直す(⛔ 式で向きを決め切らない)。
    /// 硬い: 口の芯のずれ ≤ 0.05m。部材が無ければ据え直さず ★ に出す。</summary>
    static string GateInNagaya(Transform kak, Run r, float call, bool nikai, float gS, float gW, string label, List<string> wait)
    {
        var t = kak.Find(r.name); if (t == null) return "";
        float sMid = (r.s0 + r.s1) * 0.5f;
        Vector3 dirXw = t.rotation * Vector3.right;
        Vector2 ed = (EdgePt(r.edge, sMid + 1f) - EdgePt(r.edge, sMid)).normalized;
        float sSign = (dirXw.x * ed.x + dirXw.z * ed.y) >= 0f ? 1f : -1f;
        // 口の芯 s = sMid + sSign·(call/2 − gc) ⇒ gc = call/2 − sSign·(gS − sMid)
        float gc = Mathf.Round((call * 0.5f - sSign * (gS - sMid)) * 1000f) / 1000f;
        string mwG, want = MiterOf(EdoAssets.Own.KutaiOf(EdoAssets.Own.NagayaOmoteMon(call, gc, nikai)), r, sSign, out mwG);
        if (mwG != null) wait.Add(mwG);
        string have = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject);
        if (have != want)
        {
            if (AssetDatabase.LoadAssetAtPath<GameObject>(want) == null)
            {
                wait.Add(label + "(門長屋 " + r.name + "): 口が s=" + gS.ToString("0.###") + " に来る版が無い " + want
                       + " → build_nagaya_omote.py -- " + call.ToString("0.###") + " --gate " + gc.ToString("0.###")
                       + " " + gW.ToString("0.###") + " <有効高>" + (nikai ? " --floors 2" : ""));
                return "";
            }
            float dummy = 0f; var tmp = new List<string>();
            // ⚠ 差し替えは Place の後に旧を消す(棟梁の memory: ownpath-float-suffix-and-destroy-before-place)
            var old = t.gameObject; old.name = r.name + "__old";
            PlaceNagayaPiece(kak, r.name, want, r.edge, sMid, r.SeatAt(sMid), call, tmp, ref dummy);
            UnityEngine.Object.DestroyImmediate(old);
            wait.AddRange(tmp);
        }
        // 口の芯の実測(札の passage を世界へ)── 硬い: 指図の s とのずれ ≤ 0.05m
        string meas = "";
        var tNow = kak.Find(r.name); var spc = EdoPartSpec.Get(want);
        if (tNow != null && spc != null && spc.passage != null && spc.passage.x1 - spc.passage.x0 > 0.1f)
        {
            Vector2 o0 = EdgePt(r.edge, 0f), ax = (EdgePt(r.edge, 1f) - o0).normalized;
            float sC = Vector2.Dot(EdoPartSpec.PassageCenterWorld(spc, tNow) - o0, ax);
            float wC = spc.passage.x1 - spc.passage.x0;
            meas = "・実測の口の芯 s=" + sC.ToString("0.###") + "(ずれ " + (sC - gS).ToString("+0.###;-0.###") + ")・口幅 " + wC.ToString("0.###");
            if (Mathf.Abs(sC - gS) > 0.05f) wait.Add(label + ": 口の芯が指図の s=" + gS.ToString("0.###") + " から " + (sC - gS).ToString("F3") + "m ずれる");
        }
        return "(" + label + ": 門長屋 " + r.name + " の口 s=" + gS.ToString("0.###") + "・幅 " + gW.ToString("0.###")
             + "m・部材 " + System.IO.Path.GetFileNameWithoutExtension(want) + meas + ")";
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
        bool kutai = path.EndsWith("_kutai.fbx");   // 躯体 = 呼び寸法の版は実長 = 呼び + 破風 0.322×2
        if (Mathf.Abs(realLen - call - (kutai ? 0.644f : 0f)) > 0.10f)
            wait.Add("長屋 " + name + ": 部材の実長(OBB)" + realLen.ToString("F3")
                   + "m が呼び " + call.ToString("0.###") + "m と食い違う"
                   + "(⚠ 呼び寸法は**破風まで含む全幅**で、隣と突き付く)");
        return true;
    }

    /// <summary>坂の路肩の野面石の縁(Stage1 の <see cref="PlaceCurb"/>・Saka/Curb_*)の段の境の継ぎ目の下を、**皮を起こした後の描かれた地表**まで
    /// 同じ駒で積み下ろす(置き方は <see cref="EdoBuild.StackDownAtNozuraSteps"/> ── 段の土留め TW_Kado_Sode と同じ型)。
    /// 縁は造成(Stage1)で皮の前の 2m 格子に据わるので、入隅の端の駒 Curb_R_UraZaka_0_004f が描かれた法から 0.153m 浮いた(2026-10-04 第14巡)。
    /// 前の巡の積み(*_tsumi*)を外してから積む(Stage3b を何度流しても同じ)。</summary>
    static string StackCurbOnSkin()
    {
        var saka = Group("Saka"); var names = new List<string>();
        foreach (Transform c in saka) if (c.name.StartsWith("Curb_")) names.Add(c.name);
        if (names.Count == 0) return "縁の積み下ろし: 縁なし";
        var dg = EdoBuild.Drawn();
        var log = new System.Text.StringBuilder(); int tot = 0; float wbA = float.NegativeInfinity, waA = float.NegativeInfinity;
        foreach (var nm in names)
        {
            var cg = Group("Saka/" + nm);
            var old = new List<GameObject>(); foreach (Transform c in cg) if (c.name.Contains("_tsumi")) old.Add(c.gameObject);
            foreach (var g in old) UnityEngine.Object.DestroyImmediate(g);
            var placed = new List<KeyValuePair<GameObject, Vector2>>();
            foreach (Transform c in cg) if (c.gameObject.activeInHierarchy) placed.Add(new KeyValuePair<GameObject, Vector2>(c.gameObject, EdoBuild.WallFace(c.gameObject)));
            float wb, wa; tot += EdoBuild.StackDownAtNozuraSteps(placed, dg.At, cg, 4, log, out wb, out wa);
            wbA = Mathf.Max(wbA, wb); waA = Mathf.Max(waA, wa);
        }
        return "縁の積み下ろし(描かれた地表へ): " + tot + " 駒・継ぎ目の駒の抜け 最悪 " + (float.IsNegativeInfinity(wbA) ? "-" : wbA.ToString("+0.000;-0.000")) + " → "
             + (float.IsNegativeInfinity(waA) ? "-" : waA.ToString("+0.000;-0.000")) + "m" + (waA > 0.005f ? " ⛔" : "") + (log.Length > 0 ? "\n" + log.ToString().TrimEnd() : "");
    }

    /// <summary>通用口(Mon の駒)を皮の後の描かれた地表へ据え直す(置き方は <see cref="EdoBuild.SeatGamaeOn"/>)。Stage2 の <c>SeatGamae</c> は
    /// 皮の前の地形で当てるので、敷居の面(溜り 12.20)を皮が描く所で門の足が 0.014 埋まった(2026-10-07 第47巡)。</summary>
    static string SeatMonOnSkin()
    {
        var dg = EdoBuild.Drawn();
        System.Func<float, float, float> bed = (x, z) => { float d = dg.At(x, z); return float.IsNaN(d) ? EdoBuild.Ground(x, z) : d; };
        var parts = new List<string>();
        foreach (Transform c in Group("Mon"))
        {
            if (!c.gameObject.activeInHierarchy) continue;
            float mv = EdoBuild.SeatGamaeOn(c.gameObject, bed);
            parts.Add(c.name + " " + (float.IsNaN(mv) ? "測れない ⛔" : mv.ToString("+0.000;-0.000") + "m"));
        }
        return "門構えを描かれた地表へ据えた: " + (parts.Count == 0 ? "門なし" : string.Join(" / ", parts.ToArray()));
    }

    /// <summary>天端の垣 DanKaki を皮の後の据わる床(描かれた地表と土留め Ishigaki・Dan の上向きの面の高い方)で据え直す
    /// (置き方は <see cref="EdoBuild.ReseatCrestFence"/>)。Stage3b の末で練塀の <see cref="SeatHeiOnBed"/> と並べて呼ぶ。</summary>
    static string SeatKakiOnBed()
    {
        var tops = new List<GameObject>();
        foreach (var gn in new[] { "Ishigaki", "Dan" })
            foreach (Transform c in Group(gn)) if (c.gameObject.activeInHierarchy) tops.Add(c.gameObject);
        var bed = new EdoBuild.Bed(tops);
        float up, dn; int n = EdoBuild.ReseatCrestFence(Group("DanKaki"), bed.At, out up, out dn);
        return "天端の垣を床へ据えた(根入れ 0.15): " + n + " 駒・最も上げた +" + up.ToString("F3") + "m / 最も下げた " + dn.ToString("F3") + "m";
    }

    /// <summary>練塀(表裏の f/b を一組)・隅 Kado_*・端を切った Kiri_* を、床 = 描かれた地表と基壇 IG_* の天端の高い方
    /// (<see cref="EdoBuild.Bed"/>)へ組ごと据える(<see cref="EdoBuild.SinkGroupToBed"/>)。長屋・門は触らない。</summary>
    static string SeatHeiOnBed(Transform kak)
    {
        var igs = new List<GameObject>();
        var igT = Group("Ishigaki"); foreach (Transform c in igT) if (c.gameObject.activeInHierarchy) igs.Add(c.gameObject);
        var bed = new EdoBuild.Bed(igs);
        var groups = new Dictionary<string, List<GameObject>>();
        foreach (Transform c in kak)
        {
            if (!c.gameObject.activeInHierarchy) continue;
            string nm = c.name, key = null;
            if (nm.StartsWith("Kado_") || nm.StartsWith("Kiri_")) key = nm;
            else
            {
                for (int k = 0; k < Runs.Length; k++)
                    if (Runs[k].Dobei && nm.StartsWith(Runs[k].name + "_")) { key = (nm.EndsWith("f") || nm.EndsWith("b")) ? nm.Substring(0, nm.Length - 1) : nm; break; }
            }
            if (key == null) continue;
            List<GameObject> L; if (!groups.TryGetValue(key, out L)) groups[key] = L = new List<GameObject>();
            L.Add(c.gameObject);
        }
        int n = 0, nan = 0; float up = 0f, dn = 0f; string upN = "-", dnN = "-";
        foreach (var kv in groups)
        {
            float mv = EdoBuild.SinkGroupToBed(kv.Value, bed.At);
            if (float.IsNaN(mv)) { nan++; continue; }
            n++;
            if (mv > up) { up = mv; upN = kv.Key; }
            if (mv < dn) { dn = mv; dnN = kv.Key; }
        }
        return "練塀・隅を床へ据えた(浮き 0): " + n + " 組(測れず " + nan + ")・最も上げた +" + up.ToString("F2") + "m @" + upN
             + " / 最も下げた " + dn.ToString("F2") + "m @" + dnN;
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

        int made = 0, seg = 0, pulled = 0, retired = 0; var miss = new List<string>(); float thin = 0f;
        var gone = new List<string>();
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
                    if (go == null) continue;
                    made++;
                    // 硬い・区域(許容0・EDO-0502): 実メッシュが区画の外へ出たら、走りに沿って引いて収める。
                    //   区間の途中の駒は重ね(0.20s)の範囲だけ。**区間の両端の駒は駒一つ分(unit)まで**引く ──
                    //   隅では控え(2.4s)が隣の辺を跨ぎ、短い区間(0.4m の返しなど)では駒が辺の先へ突き出す。
                    //   引いた端は隣の辺の駒の小口が塞ぐ(出隅は片方の面を通し、もう一方を端点へ・石垣の作法)。
                    //   それでも収まらない駒は退ける。
                    float was;
                    bool segEnd = (i == 0 || i == N - 1);
                    float mv = EdoBuild.KeepInsidePoly(go, Poly, EdgePt(r.edge, 1f) - EdgePt(r.edge, 0f),
                                                       segEnd ? unit : 0.20f * sc, out was, 0.01f, SEAM_TOL);
                    if (float.IsNaN(mv))
                    { gone.Add(go.name + " " + was.ToString("F2") + "m"); UnityEngine.Object.DestroyImmediate(go); retired++; }
                    else if (mv != 0f) pulled++;
                }
                seg++;
            }
        }
        // 門: 引き・退けの後に、残った駒を同じ実メッシュで検める(0 で無ければ退ける)
        var gate = new List<string>();
        retired += EdoBuild.RetireOutsidePoly(grp, Poly, gate, "石垣基壇", SEAM_TOL);
        var sb = new System.Text.StringBuilder();
        sb.Append("石垣基壇: " + (made - retired) + " 駒 / " + seg + " 区間");
        if (pulled > 0) sb.Append(" ｜ 区画の内へ走りに沿って引いた " + pulled + " 駒");
        if (retired > 0) sb.Append("\n★ 石垣基壇: 区画の外へ出て退けた " + retired + " 駒(硬い・区域): " + string.Join(" / ", gone.ToArray()));
        foreach (var g in gate) sb.Append("\n★ " + g);
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
    /// <summary>据えた小門の脇の面 (辺, s 低い側, s 高い側)。袖の練塀の端はここへ突き付く(Stage2 で毎回作り直す)。</summary>
    static List<Vector3> _komonJamb = new List<Vector3>();
    /// <summary>袖の練塀の端を門の脇の面へ差し込む量[m](0 = 面へ突き付け)。【U】棟梁の決め ── 隙 > めり込み の 0 側。</summary>
    const float KOMON_BITE = 0.0f;

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
            // 案1(EDO-0502): 門長屋を潜る門(`host`)は口を長屋の駒が持つ ── S2 の表長屋で据えた
            if (Has(k, "host")) { sb.AppendLine("小門 " + nm + ": 門長屋 " + S(k["host"]) + " の口として据えた(別に置かない)"); continue; }
            if (!Has(k, "w"))
            { sb.AppendLine("★ 小門 " + nm + "(" + S(k["kind"]) + "): 指図 komon[].w(門口の幅)が null ── 型と幅が未決なので据えない"); continue; }
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
            // ⭐ 門構えは札で置く(EdoBuild.PlaceGamae・docs/oki-kata.md §8)── 通り口の芯を指図の s へ・**門の正面(柱の面)**を塀の外の面
            //   (区画線から内へ犬走り)へ。⛔ 実メッシュの最大の張り出し(FaceOut)で寄せない ── 棟門の軒(札の eave 1.2m)を拾い、
            //   門柱が塀の線より 1.4m 内へ引っ込んで袖の練塀と 0.63m 開いた(2026-10-03・EDO-0502)。
            if (EdoPartSpec.Get(path) != null)
            {
                Vector2 eA = EdgePt(e, 0f), eB = EdgePt(e, 1f);
                var gm = EdoBuild.PlaceGamae(go, new List<GameObject>(), eA, eB, nrm, c, Poly, -INUBASHIRI, 0f, 1.0f);
                Vector2 al = (eB - eA).normalized;
                float sLo = gm.jLo - Vector2.Dot(eA, al), sHi = gm.jHi - Vector2.Dot(eA, al);
                _komonJamb.Add(new Vector3(e, sLo, sHi));
                EdoBuild.SeatGamae(go, 600);
                sb.AppendLine("小門 " + nm + ": 札で据えた ── 脇の面 s=" + sLo.ToString("F3") + "〜" + sHi.ToString("F3") + "・正面の残差 " + gm.faceResid.ToString("+0.000;-0.000") + "m"
                            + (gm.tuck > 0f ? "・区画の線で内へ " + gm.tuck.ToString("F3") : "") + (gm.notes.Count > 0 ? " " + string.Join(" / ", gm.notes.ToArray()) : ""));
            }
            else
            {
                float face = FaceOut(go, e);
                if (!float.IsNaN(face))
                {
                    float shift = -INUBASHIRI - face;
                    go.transform.position += new Vector3(nrm.x * shift, 0f, nrm.y * shift);
                    sb.AppendLine("⚠ 小門 " + nm + ": 札が無い ── 外面 " + face.ToString("+0.00;-0.00") + " で寄せた(軒を拾う恐れ)");
                }
            }
            made++;
        }
        sb.Append("通用口: " + made + " 基");
        return sb.ToString();
    }

    /// <summary>据えた現物の**外面**(辺 e の区画線から外向きへの最大の張り出し[m])。測れなければ NaN。
    /// ⛔ 呼び寸法や bbox の半分で代用しない — 部材を差し替えた瞬間に壊れる。測る本体は `EdoBuild.FaceOut`。</summary>
    static float FaceOut(GameObject go, int e)
    { return EdoBuild.FaceOut(go, Poly[e % Poly.Length], OutNormal(e), float.MinValue, float.MaxValue); }

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
        var byEdge = new Dictionary<int, List<GameObject>>();   // 辺 → 線の上に据えた駒(列ごと区画の内へ納める)
        var endPosts = new Dictionary<int, List<GameObject>>(); // 辺 → 区間の +X 端の杭
        System.Action<int, GameObject> keep = delegate(int ed, GameObject g0)
        { if (g0 == null) return; List<GameObject> l; if (!byEdge.TryGetValue(ed, out l)) byEdge[ed] = l = new List<GameObject>(); l.Add(g0); };
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
                    // ⭐ 置き場は EdoBuild.PlaceBest(EDO-0502 裁定・docs/oki-kata.md §4a)。
                    //   柔らかい: 指図の s(狙い)── 同じ run の上を狙いから近い順に試す。
                    //   硬い: ①見える丈 ≥ 戸の丈 k.h(法の上で戸が埋まらず開く姿になる)②腰の区画外 0。
                    //   ⛔ 法は均さない(地形に触らない)。
                    float fs0 = 0f, fs1 = 0f;
                    foreach (var fo in A(D["fences"]) ?? new List<object>())
                    { var fd0 = O(fo); if (fd0 != null && (int)F(fd0["edge"]) == e0) { fs0 = F(fd0["s0"]); fs1 = F(fd0["s1"]); } }
                    float doorH = Has(k, "h") ? F(k["h"]) : 0f;
                    var spots = new List<float>();
                    for (int q = 0; q < 2000; q++)
                    {
                        float d0 = 0.25f * ((q + 1) / 2) * (q % 2 == 0 ? 1f : -1f);
                        float sq = s + d0;
                        if (sq - w / 2f >= fs0 + w && sq + w / 2f <= fs1 - w) spots.Add(sq);
                        if (Mathf.Abs(d0) > fs1 - fs0) break;
                    }
                    var hards = new List<EdoBuild.Hard> {
                        new EdoBuild.Hard("見える丈 ≥ 戸の丈", g => { float v = EdoBuild.VisibleAboveBed(g, EdoBuild.Ground); return !float.IsNaN(v) && v >= doorH; }),
                        new EdoBuild.Hard("区域", g => EdoBuild.WaistOutside(g, Poly) <= SEAM_TOL),
                    };
                    var tally = new EdoBuild.SeiyakuTally();
                    float kIn = 0f;
                    System.Func<float, GameObject> placeK = sq =>
                    {
                        Vector2 cq = EdgePt(e0, sq);
                        var g = EdoBuild.Place(kp, new Vector3(cq.x, EdoBuild.Ground(cq.x, cq.y), cq.y), psi0, Vector3.one, gk, "Kuguri");
                        if (g == null) return null;
                        float was; kIn = EdoBuild.InsetRunToPoly(new List<GameObject> { g }, Poly, -ow, 0.50f, out was, 0.005f, SEAM_TOL);
                        if (float.IsNaN(kIn)) { kIn = 0f; return g; }   // 区域の硬い制約で退く
                        EdoBuild.SinkToBed(g, EdoBuild.Ground, 0.05f);
                        return g;
                    };
                    var go0 = EdoBuild.PlaceBest<float>(spots, spots.Count, placeK, hards, new List<EdoBuild.Soft>(), tally);
                    if (go0 == null)
                        sb.AppendLine("★ 潜り戸: 硬い制約を満たす置き場が run の上に無い ── 建てない・柵の口も開けない" + tally.Summary());
                    else
                    {
                        // 列の内寄せ(下)で柵と同じ量だけ動かすので、ここでは線の上へ戻す(芯を列と揃える)
                        go0.transform.position += new Vector3(ow.x * kIn, 0f, ow.y * kIn);
                        var cw = go0.transform.position;
                        float sGot = Vector2.Dot(new Vector2(cw.x, cw.z) - EdgePt(e0, 0f), (EdgePt(e0, 1f) - EdgePt(e0, 0f)).normalized);
                        if (Mathf.Abs(sGot - s) > 0.01f)
                            sb.AppendLine("⚠ 潜り戸: 狙い s=" + s.ToString("F2") + " → " + sGot.ToString("F2") + "(" + (sGot - s).ToString("+0.00;-0.00")
                                        + "m)── 狙いでは見える丈が戸の丈 " + doorH.ToString("F2") + "m に届かない" + tally.Summary());
                        s = sGot;
                    }
                    keep(e0, go0);
                    if (go0 != null)
                    {
                        kuguri++;
                        float kw2, kd2; ObbWD(go0, out kw2, out kd2);   // ⭕ OBB(ローカル +X = 走り)
                        openW = kw2;
                    }
                }
                // 戸が建たなければ柵に口を開けない(口だけ開けると素通しになる)
                if (kuguri > 0) gaps.Add(new float[] { e0, s - openW / 2f, s + openW / 2f });
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
                // ⭐ 板ごとに地表なりの弦へ張る(EdoBuild.ChordFenceRun・2026-10-03 EDO-0502)。
                //   ⛔ 水平の板を 1 枚ずつ地表へ下ろさない ── 斜面で隣と 2.22m の段違い・板の端が 2.30m 浮いた。
                //   硬い・区域: 線の上で一度張って列ごとの内寄せの量を測り、その線で張り直す(張り直した線の地表で据わる)。
                Vector2 a0 = EdgePt(e, sg[0]), b0 = EdgePt(e, sg[1]);
                float lat = Vector2.Dot(EdgePt(e, 0f), outw);
                Vector3 lj;
                string fnm = S(fd["name"]);
                var pcs = EdoBuild.ChordFenceRun(fpath, a0, b0, outw, lat, fen, fnm, posts, out lj);
                float wasF; float dIn = EdoBuild.InsetRunToPoly(pcs, Poly, -outw, 0.50f, out wasF, 0.005f, SEAM_TOL);
                if (float.IsNaN(dIn)) { foreach (var g0 in pcs) if (g0 != null) UnityEngine.Object.DestroyImmediate(g0); sb.AppendLine("★ 木柵 " + fnm + ": 0.50m 引いても区画の外(" + wasF.ToString("F3") + "m)── 退けた"); continue; }
                if (dIn > 0f)
                {
                    foreach (var g0 in pcs) if (g0 != null) UnityEngine.Object.DestroyImmediate(g0);
                    a0 -= outw * dIn; b0 -= outw * dIn;
                    pcs = EdoBuild.ChordFenceRun(fpath, a0, b0, outw, lat - dIn, fen, fnm, posts, out lj);
                    float was2; float d2 = EdoBuild.InsetRunToPoly(pcs, Poly, -outw, 0.20f, out was2, 0.005f, SEAM_TOL);
                    sb.AppendLine("木柵 " + fnm + ": 線から内へ " + dIn.ToString("F3") + "m の線で張り直した(外へ " + wasF.ToString("F3") + "m 出ていた" + (d2 > 0f ? "・追い " + d2.ToString("F3") : "") + ")");
                }
                sb.AppendLine("木柵 " + fnm + ": 弦に張った " + pcs.Count + " 枚・収めた後の浮き最悪 " + EdoBuild.LastChordFloat.ToString("F3") + "m・継ぎ目の最深の沈め " + EdoBuild.LastChordDeepest.ToString("F3") + "m");
                posts += pcs.Count;
                // ⛔ run の +X 端に端の杭を1本(足さないと最後の板が宙で終わる)── 高さは末の継ぎ目
                {
                    var gp2 = EdoBuild.Place(EdoAssets.Own.HoriSakuPost, new Vector3(b0.x, lj.y, b0.y),
                                             psi, Vector3.one, fen, fnm + "_Post" + posts);
                    if (gp2 != null)
                    {
                        float w0; float mv = EdoBuild.KeepInsidePoly(gp2, Poly, (b0 - a0).normalized, 0.50f, out w0, 0.01f, SEAM_TOL);
                        if (float.IsNaN(mv)) { sb.AppendLine("★ 木柵 端の杭 " + gp2.name + " が区画の外(" + w0.ToString("F3") + "m)── 退けた"); UnityEngine.Object.DestroyImmediate(gp2); }
                        else
                        {
                            var sr = EdoBuild.SinkToBed(gp2, EdoBuild.Ground, 0.05f);
                            if (!float.IsNaN(sr.hi) && sr.hi > 0.01f) sb.AppendLine("★ 木柵 " + gp2.name + ": 据えた後も浮き " + sr.hi.ToString("F3") + "m");
                            posts++;
                        }
                    }
                }
            }
            runs++;
        }
        // 硬い・区域(許容0・EDO-0502): 線の上に芯を置いた柵と潜りは外側の半分が区画の外へ出る。
        //   列ごと同じ量だけ内へ引き、引いた先の地盤で据え直す(⛔ 駒ごとに引かない ── 潜りと板の芯が食い違う)
        var inset = new System.Text.StringBuilder();
        foreach (var kv in byEdge)
        {
            float was;
            float d = EdoBuild.InsetRunToPoly(kv.Value, Poly, -OutNormal(kv.Key), 0.50f, out was, 0.005f, SEAM_TOL);
            if (float.IsNaN(d))
            {
                foreach (var g0 in kv.Value) if (g0 != null) UnityEngine.Object.DestroyImmediate(g0);
                inset.Append("\n★ 木柵 辺" + kv.Key + ": 0.50m 引いても区画の外(" + was.ToString("F3") + "m)── 退けた " + kv.Value.Count + " 駒");
                continue;
            }
            var all = new List<GameObject>(kv.Value);
            List<GameObject> ep;
            if (endPosts.TryGetValue(kv.Key, out ep))
            {
                Vector2 runDir = EdgePt(kv.Key, 1f) - EdgePt(kv.Key, 0f);
                foreach (var g0 in ep)
                {
                    if (d > 0f) g0.transform.position += new Vector3(-OutNormal(kv.Key).x * d, 0f, -OutNormal(kv.Key).y * d);
                    float w0; float mv = EdoBuild.KeepInsidePoly(g0, Poly, runDir, 0.50f, out w0, 0.01f, SEAM_TOL);
                    if (float.IsNaN(mv))
                    { inset.Append("\n★ 木柵 辺" + kv.Key + ": 端の杭 " + g0.name + " が区画の外(" + w0.ToString("F3") + "m)── 退けた"); UnityEngine.Object.DestroyImmediate(g0); continue; }
                    if (mv != 0f) inset.Append(" ｜ 端の杭 " + g0.name + " を走りに沿って " + mv.ToString("F2") + "m 引いた(隅で隣の辺を " + w0.ToString("F3") + "m 跨いでいた)");
                    all.Add(g0);
                }
            }
            // 硬い・地面(浮き 0): 杭の足(下端の当たり)を**描かれた地表**で測って据える(EdoBuild.SinkToBed)。
            //   ⛔ 設計面 Graded で据えない ── 汀では地表(2m 格子)が区画線の際で外の低い節点へ下りるので、設計面より
            //   0.4〜1.4m 低い(32/46 駒が浮いた・EDO-0502)。
            foreach (var g0 in all)
            {
                if (g0 == null) continue;
                var sr = EdoBuild.SinkToBed(g0, EdoBuild.Ground, 0.05f);
                if (float.IsNaN(sr.hi)) inset.Append("\n★ 木柵 " + g0.name + ": 足の当たりが測れない");
                else if (sr.hi > 0.01f) inset.Append("\n★ 木柵 " + g0.name + ": 据えた後も浮き " + sr.hi.ToString("F3") + "m");
            }
            if (d > 0f) inset.Append(" ｜ 辺" + kv.Key + " の列を内へ " + d.ToString("F3") + "m(外へ " + was.ToString("F3") + "m 出ていた)");
        }
        sb.Append("木柵: " + posts + " 枚 / " + runs + " run(駒の実寸 " + wMeasured.ToString("F3") + "m)" + inset);
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

    // ---------------------------------------------------------------- 隅の犬走り合わせと腕の実測
    /// <summary>据えた隅の両腕の外面を犬走りへ寄せ、腕の実端面を測る。測る本体は共通の層
    /// (`EdoBuild.KadoFace` / `KadoArm`)。<paramref name="lo"/>[辺] = その辺の s=0 側にある隅が覆う上限 /
    /// <paramref name="hi"/>[辺] = s=L 側にある隅が覆う下限。⛔ 邸にこの測りを書き写さない(規則21)。</summary>
    static string FitKado(Transform kak, Dictionary<int, float> lo, Dictionary<int, float> hi)
    {
        var list = A(Get(IMPL, "corners"));
        if (list == null) return "隅の腕: 算出物に corners が無い";
        var P = Poly; int n = P.Length;
        float wallT = C("dobeiT");
        var sb = new System.Text.StringBuilder("隅の腕(壁体・実測): ");
        var notes = new List<string>(); int fit = 0; float worstMove = 0f;
        foreach (var o in list)
        {
            var c = O(o); if (c == null || !Has(c, "part")) continue;       // PlaceKado と同じ選り分け
            string id = S(c["id"]);
            var kc = kak.Find("Kado_" + id); if (kc == null) continue;
            int e1 = ((int)F(c["vertex"]) - 1 + n) % n, e2 = (e1 + 1) % n;
            Vector2 mv; string note;
            if (!EdoBuild.KadoFace(kc, P, e1, OutNormal, -INUBASHIRI, wallT, out mv, out note))
            { notes.Add(id + ": " + note); continue; }
            if (note != null) notes.Add(id + ": " + note);
            worstMove = Mathf.Max(worstMove, mv.magnitude);
            float h, l;
            if (!EdoBuild.KadoArm(kc, P, e1, OutNormal, -INUBASHIRI, wallT, 0.10f, out h, out l))
            { notes.Add(id + ": 腕を判別できず"); continue; }
            if (!hi.ContainsKey(e1) || h < hi[e1]) hi[e1] = h;
            if (!lo.ContainsKey(e2) || l > lo[e2]) lo[e2] = l;
            sb.Append(id + " 辺" + e1 + "(s≥" + h.ToString("F2") + ")/辺" + e2 + "(s≤" + l.ToString("F2") + ") ");
            fit++;
        }
        sb.Append("｜ " + fit + " 基・最大の寄せ " + worstMove.ToString("F2") + "m");
        if (notes.Count > 0) sb.Append(" ｜ ★ " + string.Join(" / ", notes.ToArray()));
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 隅の留め継ぎ
    /// <summary>隅部材を据える。**折れ角は区画が決めるもので毎回違う**ので決め打ちしない。
    /// `impl.corners` が正典なのは頂点・部材(part)の割り付けだけ — 角度(deg)は信じない
    /// (生成器が符号を反転して焼く不具合、2026-09-21 実測・EDO-0343)。折れ角は毎回
    /// `EdoBuild.KadoDeg` で**区画の実測**から求める(規則21)。天端は各部材の実メッシュから測る。
    /// ⭕ 算出物の欄は 2026-09-22 に `bake_impl.py` で符号ごと焼き直したので、いまは実測と一致する
    ///   — が、**一致を当てにして json を読む側へ戻さない**。宣言は焼き手を入れ替えた瞬間にまた外れる。
    /// 据え: `position = 頂点 / yaw = 入りの run の走りの方位 / scale = ES`。
    /// ⚠ 直線材は `SeatBottom(seat − 0.10)` で沈めてあるので、隅も同じだけ沈める
    ///   (seat ちょうどだと 0.10m 浮いて軒の線が隅で段になる)。</summary>
    static string PlaceKado(Transform parent)
    {
        var list = A(Get(IMPL, "corners"));
        if (list == null) return "隅部材: 算出物に corners が無い(`python3 Tools/Sashizu/bake_impl.py okabe --write`)";
        var P = Poly; int n = P.Length;
        int made = 0, skip = 0; var miss = new List<string>(); var degWarn = new List<string>(); var armNote = new List<string>();
        // 腕の短い隅(EDO-0502): 同じ部材の隅が両端に立つ辺は、腕を EdoBuild.KadoArms で区画から選ぶ
        var kadoAt = new Dictionary<int, string>();
        foreach (var o in list) { var c = O(o); if (c != null && Has(c, "part")) kadoAt[((int)F(c["vertex"]) % n + n) % n] = S(c["part"]); }
        foreach (var o in list)
        {
            var c = O(o); if (c == null) continue;
            if (!Has(c, "part")) { skip++; continue; }        // 留め継ぎでない隅(当家が建てない側など)
            string part = S(c["part"]);
            if (part == "Nagaya") { skip++; continue; }       // 表長屋の隅は次巡
            // ⛔ 算出物の `deg` を信じない — 岡部の生成器は符号を反転して焼いていて、隅 8 基すべてが
            //    鏡像の部材で建っていた(2026-09-21 実測・EDO-0343)。折れ角は**区画から測る**(規則21)。
            //    ⭕ 欄そのものは 2026-09-22 に焼き直した(EDO-0386)。下の突き合わせは**二度と外れないため**に残す。
            float deg = EdoBuild.KadoDeg(Poly, (int)F(c["vertex"]));
            if (Has(c, "deg") && Mathf.Abs(Mathf.DeltaAngle(deg, F(c["deg"]))) > 0.5f)
                degWarn.Add(S(c["id"]) + " 算出物 " + F(c["deg"]).ToString("+0.0;-0.0")
                          + "° ≠ 実測 " + deg.ToString("+0.0;-0.0") + "°");
            string path = EdoAssets.Own.Kado(part, deg);
            string armArg = "";
            float full, faceDepth;
            if (EdoBuild.KadoGauge(path, out full, out faceDepth))
            {
                string pt = part; Vector2 arms; string an;
                bool ok = EdoBuild.KadoArms(P, (int)F(c["vertex"]), k => kadoAt.ContainsKey(k) && kadoAt[k] == pt, OutNormal,
                                            ES, full, faceDepth, INUBASHIRI, INUBASHIRI + C("dobeiT"), 0.05f, 0.5f, out arms, out an);
                if (an != null) armNote.Add(S(c["id"]) + ": " + an);
                if (!ok) { skip++; continue; }                // 腕が成り立たない隅は据えない(note に出る)
                path = EdoAssets.Own.Kado(part, deg, arms.x, arms.y, full);
                if (arms.x < full - 1e-3f || arms.y < full - 1e-3f)
                    armArg = " --arms " + arms.x.ToString("0.00") + "," + arms.y.ToString("0.00");
            }
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (src == null)
            {
                miss.Add(S(c["id"]) + " → " + path
                       + "(blender --background --python Tools/Blender/build_kado.py -- --part "
                       + part.ToLowerInvariant() + " --deg " + Mathf.RoundToInt(deg) + armArg + ")");
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
        if (degWarn.Count > 0)
            sb.Append("\n★ 折れ角が算出物と食い違う " + degWarn.Count
                    + " 件(区画の実測で建てた — `python3 Tools/Sashizu/bake_impl.py okabe --write` で欄を焼き直すこと EDO-0386) — "
                    + string.Join(" / ", degWarn.ToArray()));
        if (miss.Count > 0)
            sb.Append("\n★ 部材が無い " + miss.Count + " 件 — " + string.Join(" / ", miss.ToArray()));
        if (armNote.Count > 0)
            sb.Append("\n★ 隅の腕 " + armNote.Count + " 件 — " + string.Join(" / ", armNote.ToArray()));
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
        System.Predicate<MeshFilter> pickWall = mf => WallFace.Contains(mf.gameObject.name);   // 壁面のメッシュだけで測る
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
            float best = EdoBuild.FaceOut(c.gameObject, a, nrm, float.MinValue, float.MaxValue, pickWall);
            if (float.IsNaN(best)) continue;
            seen++;
            float shift = target - best;
            if (Mathf.Abs(shift) > Mathf.Abs(worst)) { worst = shift; worstName = c.name; }
            if (Mathf.Abs(shift) > 0.02f)
            { c.position += new Vector3(nrm.x * shift, 0f, nrm.y * shift); moved++; }
            // ⭐ **寄せた後にもう一度測る**(残差)。⛔ 「寄せ量」を残差と読み違えない —
            //   寄せ量が大きいのは元が外れていただけで、直ったかどうかは残差でしか分からない。
            float after = EdoBuild.FaceOut(c.gameObject, a, nrm, float.MinValue, float.MaxValue, pickWall);
            if (!float.IsNaN(after))
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
        // ⚠ **部材そのもので建つ棟**(車寄など・`ridge` を持たない)はピボットが
        //   **足跡の中心**。⛔ 部材キットで組む棟(外形の角)と同じ式で測らない
        //   (2026-09-04: 車寄が 3.28m ずれていると誤報した)。
        if (kind == "mune" && !Has(o, "ridge"))
            return Grid.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
        var g = PivotUV(u0, v0, u1, v1);
        return Grid.W(g.x, g.y);
    }

    // =====================================================================
    // Stage2b — 段の土留め(算出物 terraceWalls)と天端の垣(指図 terraceWalls[].fenceOnTop)
    // =====================================================================
    /// <summary>**段の土留めを算出物 `terraceWalls`(線・天端・口・mode)から据える**(EDO-0502 2026-10-03)。
    /// 打込接ぎ = 城の石垣(`EdoAssets.JC.CastleWall`・<see cref="EdoBuild.PlaceCrestWall"/>・出隅は <see cref="EdoBuild.PlaceRunCorners"/>)、
    /// 野面 = 野面の乱積み(<see cref="EdoBuild.PlaceNozuraNet"/>)。⛔ 置き方は EdoBuild だけ(規則21)── ここは読んで渡すだけ。
    /// <para>硬い: 天端 = 欄の top / tops(実測の最上点)、駒の底の浮き 0(見付が駒の丈 4.0 を超える城の石垣は
    /// スキル unity-modular-stonewall §3b「露出が駒の丈を超える区間は run を割る」⇒ **二段築の下段**を
    /// <see cref="EdoBuild.PlaceTierBelow"/> で据える)。line=null の欄(TW_Nishi_Kado の辺26〜27)は建てない。</para>
    /// <para>天端の垣: 型は指図 fenceOnTop.kaku の最初の名(建仁寺垣 / 四つ目垣)。⚠ 丈は指図に無い ── 在庫の焼けた丈
    /// (建仁寺垣 1.5・四つ目垣 1.2)で建て、報告に「丈は未指定」を出す。</para></summary>
    [MenuItem("Edo/岡部筑前守上屋敷/2b 段の土留め(terraceWalls・天端の垣)")]
    public static void Stage2bMenu() { Debug.Log("[Okabe] " + Stage2b_Dan()); }

    public static string Stage2b_Dan()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder("段の土留め(terraceWalls):\n");
        if (Stale("terraceWalls")) return sb + "  ⛔ 算出物 terraceWalls が前の指図のまま ── 据えない";
        var tws = A(Get(IMPL, "terraceWalls"));
        if (tws == null || tws.Count == 0) return sb + "  算出物に terraceWalls が無い";
        var grp = Group("Dan"); Clear(grp);
        var fgrp = Group("DanKaki"); Clear(fgrp);
        var runEnds = new List<EdoBuild.RunEnd>();
        var segPieces = new Dictionary<string, List<GameObject>>();
        var castle = new List<GameObject>();
        var nozSegs = new List<EdoBuild.NozuraSeg>();
        var extraPool = new List<GameObject>(); _sideCorner.Clear();   // 野面の端を突き付ける相手(両端の延長の先の台の石垣)
        var wallOf = new Dictionary<string, Dictionary<string, object>>();
        var lineOf = new Dictionary<string, List<Vector2>>();
        var topOf = new Dictionary<string, float>();
        // ⭐ 解いた口(石段の実面で詰めた・StairGaps / GapFromPieces)── 天端の垣はこの口を空ける。⛔ 紙の口(欄 gaps の s0〜s1)で空けない
        //   (第62巡: K_Dan1 の口は紙 [4.56,10.37]・解いた口 [3.13,12.83] ⇒ 差の 1.4m と 2.5m に垣の切れ端が石段の足元の地盤へ据わっていた)
        var gapOf = new Dictionary<string, List<Vector2>>();
        var log = new System.Text.StringBuilder();
        int skipped = 0;
        // ⭐ 石段を先に据える(EDO-0502 第8巡)── 口の端は据わった石段の側面の実面で決める(EdoBuild.GapFromPieces)。
        //   石段の据え(PlaceKaidans)は土留めを見ない(段石の天端=踏面・下は皮の地表まで積む)ので順を入れ替えても据えは同じ。
        var kwait = new List<string>();
        sb.AppendLine("  " + PlaceKaidans(kwait) + "(土留めより先に据えた)");
        foreach (var x in kwait) sb.AppendLine("    ★ " + x);
        var kaiRoot = GameObject.Find(GN) == null ? null : GameObject.Find(GN).transform.Find("Fuzoku/Kaidan");
        var sodeB = SodeBenches(sb); var benchAll = new List<EdoBuild.BackBench>();
        var sodeSlopeChk = new List<SodeSlopeCheck>();   // 袖の坂の硬い検め(天端と背の地盤の差)── 据えた後に測る
        // 返しと長屋の背の間の溝(BackTrenches)は長屋の実メッシュで解く ⇒ 外周(Stage2)の後に読み直す。溝は平らな面として SkinGround にも入る(FlatFaces)
        _flat = null; var trenches = BackTrenches(sb);
        foreach (var o in tws)
        {
            var w = O(o); if (w == null) continue;
            string nm = S(Get(w, "name")); string part = S(Get(w, "part"));
            var ln = A(Get(w, "line"));
            if (ln == null || ln.Count < 2) { skipped++; sb.AppendLine("  " + nm + (part != null ? "(" + part + ")" : "") + ": line=null ── 建てない(" + (S(Get(w, "unresolved")) ?? "線が無い") + ")"); continue; }
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            var tops = new List<float>();
            var tl = A(Get(w, "tops"));
            for (int i = 0; i < nodes.Count; i++) tops.Add(tl != null && i < tl.Count ? F(tl[i]) : F(Get(w, "top")));
            // ⭐ 線の先が長屋の背へ入り込むなら背から一間離して返し、高い側の妻の線で背まで閉じる(指図 terraceWalls[].return<run>・end・backOf<run>
            //   ── EDO-0502 第19巡)。溝は相手の面まで切る(地形 = CutAlongBack・皮の設計の地盤 = Stage3b が同じ BackTrenches を読む)。据えより先に。
            Func<Vector2, Vector2, Vector2> trenchHint = null;
            foreach (var tr in trenches)
            {
                if (tr.wall != nm) continue;
                nodes.Clear(); nodes.AddRange(tr.nodes);
                float t0 = tops[0]; tops.Clear(); for (int k = 0; k < nodes.Count; k++) tops.Add(t0);
                float cm, cv; int cn = EdoBuild.CutAlongBack(Poly, tr.stop, tr.far + tr.along * tr.off, tr.yard, tr.y, tr.off, 0.1f, out cm, out cv);
                AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
                sb.AppendLine("    溝(返しと " + tr.run + " の背の間)を地形で " + tr.y.ToString("F2") + " まで切った: 節点 " + cn + "・切り 最大 " + cm.ToString("F2") + "m・" + cv.ToString("F0") + "m³(2m 格子は溝を描けない ── 皮が設計の地盤で描く)");
                // 低い側: 返しと妻の閉じは溝の側(両側が地形で同じ高さに読めるので地表で決めない)・元の線は地表で測る
                var trc = tr; trenchHint = (pa, pb) =>
                {
                    Vector2 mid = (pa + pb) * 0.5f, ctr = (trc.stop + trc.far) * 0.5f + trc.yard * (trc.off * 0.5f);
                    if (Vector2.Distance(mid, ctr) < Vector2.Distance(trc.stop, trc.far) * 0.5f + trc.off + 0.5f) return (ctr - mid).normalized;
                    int v1, v2; return EdoBuild.LowSide(pa, pb, SkinGround, 3.0f, 0.05f, null, out v1, out v2);
                };
            }
            string key = nm + (part != null ? "_" + part : "");
            wallOf[key] = w; lineOf[key] = nodes; topOf[key] = tops[0];
            var gaps = new List<Vector2>();
            foreach (var g in A(Get(w, "gaps")) ?? new List<object>()) { var gd = O(g); gaps.Add(new Vector2(F(Get(gd, "s0")), F(Get(gd, "s1")))); }
            string kind = S(Get(w, "kind")) ?? "";
            if (kind.Contains("打込接ぎ"))
            {
                // 口の端 = 口を通る石段(gaps[].by の K_*)の実面。同じ口を名指す欄(K_Dan1 と R_OmoteZaka)は一つに
                var rets = new List<KeyValuePair<List<Vector2>, Vector2>>();   // 返しの線と口の内の向き
                {
                    var gl = A(Get(w, "gaps")) ?? new List<object>(); var ng = new List<Vector2>(); var seen = new List<Vector2>();
                    for (int gi = 0; gi < gl.Count; gi++)
                    {
                        var gd = O(gl[gi]); var g = new Vector2(F(Get(gd, "s0")), F(Get(gd, "s1")));
                        if (seen.Exists(z => Mathf.Abs(z.x - g.x) < 0.01f && Mathf.Abs(z.y - g.y) < 0.01f)) continue;
                        seen.Add(g);
                        string by = null;
                        foreach (var g2 in gl) { var d2 = O(g2); string b2 = S(Get(d2, "by")); if (b2 != null && b2.StartsWith("K_") && Mathf.Abs(F(Get(d2, "s0")) - g.x) < 0.01f) by = b2; }
                        Dictionary<string, object> kd = null;
                        foreach (var ko in A(D["kaidans"]) ?? new List<object>()) { var k2 = O(ko); if (k2 != null && S(Get(k2, "name")) == by) kd = k2; }
                        if (by == null || kd == null || kaiRoot == null) { ng.Add(g); sb.AppendLine("    口 " + key + " [" + g.x.ToString("F2") + "," + g.y.ToString("F2") + "]: 石段の名が無い ── 紙の口のまま ⚠"); continue; }
                        var pcs = new List<GameObject>(); foreach (Transform c in kaiRoot) if (c.name.StartsWith(by + "_")) pcs.Add(c.gameObject);
                        string gnote; var gm = EdoBuild.GapFromPieces(nodes, g, pcs, 1.0f, out gnote);
                        // 石段が紙の口より狭い端だけ石段の面へ詰める(隙 0)。広い端は石段が石垣の下へ入る(めり込み=数えない・埋めて隠す)ので紙の口のまま
                        var g1 = new Vector2(Mathf.Max(g.x, gm.x), Mathf.Min(g.y, gm.y));
                        gnote += " ⇒ 口 [" + g1.x.ToString("F2") + "," + g1.y.ToString("F2") + "]";
                        ng.Add(g1);
                        sb.AppendLine("    口 " + key + " × " + by + ": " + gnote);
                        // 返し(口の端の小口を直角に折り返す短い run)── 軸 = 石段の a→b(高い側へ向ける・測る)
                        Vector2 ka2, kb2; KaidanAB(kd, out ka2, out kb2);
                        Vector2 ax = (kb2 - ka2).normalized;
                        Vector2 dirL; Vector2 mid = EdoBuild.ArcPoint(nodes, (g1.x + g1.y) * 0.5f, out dirL);
                        float hp = SkinGround(mid.x + ax.x * 3f, mid.y + ax.y * 3f), hm = SkinGround(mid.x - ax.x * 3f, mid.y - ax.y * 3f);
                        if (!float.IsNaN(hp) && !float.IsNaN(hm) && hm > hp) ax = -ax;
                        // 返しの長さの上限 = 石段の駒の高い側への実の奥行(測る)と、口を通る坂の切通しの延長(指図 ramps[].kiritoshi.lenM)の大きい方
                        float stairDeep = 0f;
                        foreach (var pc in pcs) foreach (var v in EdoBuild.Body(pc.transform, 4000)) stairDeep = Mathf.Max(stairDeep, Vector2.Dot(new Vector2(v.x, v.z) - mid, ax));
                        float capLen = stairDeep;
                        foreach (var g2 in gl)
                        {
                            string b2 = S(Get(O(g2), "by")); if (b2 == null || Mathf.Abs(F(Get(O(g2), "s0")) - g.x) > 0.01f) continue;
                            foreach (var ro in A(Get(D, "ramps")) ?? new List<object>()) { var rd = O(ro); if (rd != null && S(Get(rd, "name")) == b2 && O(Get(rd, "kiritoshi")) != null) capLen = Mathf.Max(capLen, F(Get(O(Get(rd, "kiritoshi")), "lenM"))); }
                        }
                        foreach (float se in new[] { g1.x, g1.y })
                        {
                            Vector2 dd; Vector2 pe = EdoBuild.ArcPoint(nodes, se, out dd);
                            Vector2 inw = new Vector2(ax.y, -ax.x); if (Vector2.Dot(inw, mid - pe) < 0f) inw = -inw;
                            float rl; var line = EdoBuild.GapReturnLine(pe, ax, inw, tops[0], SkinGround, capLen, out rl);
                            sb.AppendLine("      返し @s=" + se.ToString("F2") + ": " + (line == null ? "要らない(口の床が天端に届く)" : "長さ " + rl.ToString("F2") + "m(上限 " + capLen.ToString("F2") + ")"));
                            if (line != null) rets.Add(new KeyValuePair<List<Vector2>, Vector2>(line, inw));
                        }
                    }
                    gaps = ng;
                    gapOf[key] = gaps;
                }
                var cw = new EdoBuild.CrestWall { name = key, nodes = nodes, nodeTops = tops, gaps = gaps, runAlongX = false, runLen = 2.0f, pitchMax = 1.8f,
                                                  pathOfH = EdoBuild.CastleWallOfExpose };
                if (trenchHint != null) { cw.lowHint = trenchHint; cw.lowForce = true; }   // 見付 4m 超は丈違いの駒(TW_Kado_Shumen 4.5・EDO-0502)
                float wf; int bs;
                var made = EdoBuild.PlaceCrestWall(cw, SkinGround, grp, runEnds, segPieces, log, out wf, out bs);
                castle.AddRange(made);
                // ⭐ 両端の延長(指図 terraceWalls[].ends・EDO-0502 第20巡)── 線は EndExtensions が解く(野面の枝と同じ)
                foreach (var ex in EndExtensions(nm, w, nodes, tops[0], key, sb, null))
                {
                    var ew = new EdoBuild.CrestWall { name = ex.name, nodes = new List<Vector2> { ex.pe, ex.pf }, nodeTops = new List<float> { tops[0], tops[0] }, gaps = new List<Vector2>(),
                                                      runAlongX = false, runLen = 2.0f, pitchMax = 1.8f, pathOfH = EdoBuild.CastleWallOfExpose, lowHint = (pa, pb) => ex.lowD, lowForce = true };
                    float ewf; int ebs; var em = EdoBuild.PlaceCrestWall(ew, SkinGround, grp, null, null, log, out ewf, out ebs);
                    castle.AddRange(em);
                    sb.AppendLine("    両端の延長 " + ew.name + ": 城の石垣 " + em.Count + " 駒(端の入隅は隅の駒なし)・底の浮き 最悪 "
                                + (float.IsNegativeInfinity(ewf) ? "-" : ewf.ToString("+0.000;-0.000")) + "m" + (ebs > 0 ? "・埋まり退けた " + ebs : ""));
                }
                for (int ri = 0; ri < rets.Count; ri++)
                {
                    var inw = rets[ri].Value;
                    var rw = new EdoBuild.CrestWall { name = key + "_Kaeshi" + ri, nodes = rets[ri].Key, nodeTops = new List<float> { tops[0], tops[0] }, gaps = new List<Vector2>(),
                                                      runAlongX = false, runLen = 2.0f, pitchMax = 1.8f, pathOfH = EdoBuild.CastleWallOfExpose, lowHint = (pa, pb) => inw, lowForce = true };
                    float rwf; int rbs;
                    // 返しは隅の駒を組まない(runEnds に入れない)── 口の端の小口の面と返しの見え面は同じ面(石段の脇)に揃う
                    var rm = EdoBuild.PlaceCrestWall(rw, SkinGround, grp, null, null, log, out rwf, out rbs);
                    castle.AddRange(rm);
                    sb.AppendLine("      返し " + rw.name + ": 城の石垣 " + rm.Count + " 駒" + (rbs > 0 ? "・埋まり退けた " + rbs : "") + "・底の浮き 最悪 " + (float.IsNegativeInfinity(rwf) ? "-" : rwf.ToString("+0.000;-0.000") + "m"));
                }
                sb.AppendLine("  " + key + "(" + kind + "・" + S(Get(w, "mode")) + "): 城の石垣 " + made.Count + " 駒・天端 " + tops[0].ToString("F2")
                            + "・口 " + gaps.Count + "・駒の底の浮き 最悪 " + (float.IsNegativeInfinity(wf) ? "-" : wf.ToString("+0.000;-0.000") + "m") + (bs > 0 ? "・全体が埋まり退けた " + bs : ""));
            }
            else
            {
                // ⭐ 袖の坂(指図 sodeSlope・2026-10-07 普請方)── 段にせず背の法なりの坂の一続き(SodeSlopeSegs)
                {
                    Dictionary<string, object> swS = null;
                    foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (t2 != null && S(Get(t2, "name")) == nm) swS = t2; }
                    string ssl = swS == null ? null : S(Get(swS, "sodeSlope"));
                    if (ssl != null) { sb.Append(SodeSlopeSegs(key, nodes, ssl, nozSegs, sodeSlopeChk)); continue; }
                }
                // ⭐ 袖の天端の割り(指図 top: 背の法の高さを刻みで切り上げ・run の中の背の下がり ≤ 上限)と背の小段の裏込め(backfill)は
                //   SodeBenches が解く(⛔ 算出物の tops を使わない ── 背の高さで割る)。区間ごとの run を一直線の天端で据える
                List<KeyValuePair<int, EdoBuild.BackBench>> sbk;
                if (sodeB.TryGetValue(nm, out sbk) && sbk.Count > 0)
                {
                    var cnt = new Dictionary<int, int>();
                    foreach (var kv in sbk)
                    {
                        int ci0; cnt.TryGetValue(kv.Key, out ci0); cnt[kv.Key] = ci0 + 1;
                        var bk = kv.Value; float yt = bk.top;
                        benchAll.Add(bk);
                        bool cont = sbk.Exists(o2 => o2.Value != bk && Mathf.Abs(o2.Value.top - bk.top) < 1e-3f && (Vector2.Distance(o2.Value.a, bk.b) < 0.05f || Vector2.Distance(o2.Value.b, bk.a) < 0.05f));
                        if (Vector2.Distance(bk.a, bk.b) < 0.5f && !cont) { sb.AppendLine("    袖 " + key + "_" + kv.Key + ": 長さ " + Vector2.Distance(bk.a, bk.b).ToString("F2") + "m < 0.5 ── 駒を据えない(隣の駒と隅が覆う・前と同じ)"); continue; }
                        nozSegs.Add(new EdoBuild.NozuraSeg { name = key + "_" + kv.Key + "_" + ci0, a = bk.a, b = bk.b, crestAt = sl => yt });
                        sb.AppendLine("    袖 " + key + "_" + kv.Key + "_" + ci0 + ": 長さ " + Vector2.Distance(bk.a, bk.b).ToString("F2") + "m 天端 " + yt.ToString("F2") + "(背の法を刻みで切り上げ・算出物の tops[" + kv.Key + "] = " + tops[kv.Key].ToString("F2") + ")");
                    }
                    continue;
                }
                // ⭐ 両端の決め(指図 terraceWalls[].ends・EDO-0502 第20巡)── 延ばして土羽か、妻の線で返すか(EndDecisions)。
                //   返しは主の線に入れず、妻の線までの延長(出隅・主と同じ天端)だけを主へ足す。返しの run は天端の割りと背の小段(指図 return*)ごとに
                //   SodeBenches が "<名>#ret<端>" で解き、下の袖と同じ流れで据える(第22巡)。
                {
                    List<EndReturn> rets0;
                    EndDecisions(nm, w, nodes, tops, sb, out rets0);
                    List<KeyValuePair<int, EdoBuild.BackBench>> rbk;
                    if (sodeB.TryGetValue(nm + "#ret", out rbk))
                    {
                        var cnt2 = new Dictionary<int, int>(); var prevB = new Dictionary<int, Vector2>();
                        foreach (var kv in rbk)
                        {
                            int ci0; cnt2.TryGetValue(kv.Key, out ci0); cnt2[kv.Key] = ci0 + 1;
                            var bk = kv.Value; float yt = bk.top; benchAll.Add(bk);
                            string rk = key + "#ret" + kv.Key;
                            // 上手の run の終わりより手前から始まる run(RunsByCrestGap が 1 駒に延ばして重ねた)は両端とも突き付けない(EDO-0502 第24巡)
                            Vector2 pB; bool lap = prevB.TryGetValue(kv.Key, out pB) && Vector2.Dot(pB - bk.a, (bk.b - bk.a).normalized) > 0.05f;
                            prevB[kv.Key] = bk.b;
                            var ns = new EdoBuild.NozuraSeg { name = rk + "_" + ci0, a = bk.a, b = bk.b, crestAt = sl => yt };
                            // 重ねた run の上手の端(高い run の駒の裏に埋まる)だけ突き付けない。下手の端は段の境か返しの終わり(見切り石・returnEnd)── 第32巡
                            if (lap) { ns.noAbut[0] = true; }
                            nozSegs.Add(ns);
                            if (!lineOf.ContainsKey(rk)) { wallOf[rk] = w; lineOf[rk] = new List<Vector2> { bk.a, bk.b }; topOf[rk] = yt; }
                            else lineOf[rk].Add(bk.b);
                            sb.AppendLine("    返し " + rk + "_" + ci0 + ": 長さ " + Vector2.Distance(bk.a, bk.b).ToString("F2") + "m 天端 " + yt.ToString("F2") + "(背の地盤を 0.5 刻みで切り上げ)・背の小段 幅 " + bk.w.ToString("F2"));
                        }
                    }
                }
                // ⭐ 石段の口(gaps[].by の K_*)と両端の延長(ends)── 野面の積み(施主裁定 2026-10-08「野面に揃える」・欄 kindNote・第57巡)。
                //   口の端と返しの線は StairGaps が解く(sideFace の石段 = 脇の返しの天端の線を EdoBuild.StairSideCrestLines で・
                //   無い石段 = 据わった段石の実面で口を詰め GapReturnLine)。延長は EndExtensions(城の石垣の枝と同じ線)。
                if (S(Get(w, "mode")) == "fill")
                {
                    gaps = StairGaps(key, w, nodes, tops[0], kaiRoot, nozSegs, sb);
                    gapOf[key] = gaps;
                    foreach (var ex in EndExtensions(nm, w, nodes, tops[0], key, sb, extraPool))
                        nozSegs.Add(new EdoBuild.NozuraSeg { name = ex.name + "_0", a = ex.pe, b = ex.pf, crestAt = sl => tops[0], face = ex.lowD });
                }
                // 野面: 節点ごとの区間(天端は節点の値を道のりで一次)。口で割る
                float s0 = 0f;
                for (int i = 0; i + 1 < nodes.Count; i++)
                {
                    Vector2 a = nodes[i], b = nodes[i + 1]; float L = Vector2.Distance(a, b); if (L < 0.3f) { s0 += L; continue; }
                    // 袖(mode sode)は「段違いの run・各 run 一直線」(指図 TW_Kado_Sode.top)⇒ 区間の天端 = 始まりの節点の値で水平、段は節点で。
                    //   法尻の野面石(mode toe)は節点の値を道のりで一次(天端が地盤なりに下る)
                    bool stepped = S(Get(w, "mode")) == "sode";
                    float ta = tops[i], tb = stepped ? tops[i] : tops[i + 1];
                    var cuts = new List<Vector2> { new Vector2(0f, L) };
                    foreach (var g in gaps)
                    {
                        float g0 = g.x - s0, g1 = g.y - s0; var nx = new List<Vector2>();
                        foreach (var c in cuts) { if (g1 <= c.x || g0 >= c.y) { nx.Add(c); continue; } if (g0 > c.x) nx.Add(new Vector2(c.x, g0)); if (g1 < c.y) nx.Add(new Vector2(g1, c.y)); }
                        cuts = nx;
                    }
                    int ci = 0;
                    foreach (var c in cuts)
                    {
                        Vector2 dir = (b - a) / L; Vector2 pa = a + dir * c.x, pb = a + dir * c.y;
                        // 0.5 未満は据えない ── ただし sideFace の返しの出隅に触れる残りは返しと継ぐので捨てない(捨てると返しが本線と継がらず隅の駒が立たない・第57巡)
                        if (c.y - c.x < 0.5f && !(c.y - c.x >= 0.1f && _sideCorner.Exists(q => Vector2.Distance(q, pa) < 0.05f || Vector2.Distance(q, pb) < 0.05f))) continue;
                        float ya = Mathf.Lerp(ta, tb, c.x / L), yb = Mathf.Lerp(ta, tb, c.y / L), len = c.y - c.x;
                        nozSegs.Add(new EdoBuild.NozuraSeg { name = key + "_" + i + "_" + (ci++), a = pa, b = pb,
                                    crestAt = sl => Mathf.Lerp(ya, yb, Mathf.Clamp01(sl / Mathf.Max(1e-4f, len))),
                                    face = trenchHint != null ? trenchHint(pa, pb) : Vector2.zero });   // 溝の側(返しと長屋の背の間)は地表で決めない
                    }
                    s0 += L;
                }
            }
        }
        // 城の石垣の高い区間の二段築の下段(駒の丈 4.0 を超える見付)── 区間の端の対から線と外向きを取る
        {
            var ups = new List<EdoBuild.TierUpper>();
            foreach (var kv in segPieces)
            {
                var es = runEnds.FindAll(e => e.key == kv.Key); if (es.Count != 2) continue;
                kv.Value.RemoveAll(g => g == null); if (kv.Value.Count == 0) continue;
                ups.Add(new EdoBuild.TierUpper { run = kv.Key.Split('#')[0], a = es[0].p, b = es[1].p, outw = es[0].outw, pieces = kv.Value });
            }
            var tierMade = new List<GameObject>(); var faceOf = new Dictionary<GameObject, Vector2>();
            int ng = ups.Count == 0 ? 0 : EdoBuild.PlaceTierBelow(ups, EdoAssets.JC.CastleWall, 2.0f, 1.8f, 4.0f, SkinGround, 0.6f, grp, 0.05f,
                                                                    runEnds, segPieces, faceOf, tierMade, log);
            castle.AddRange(tierMade);
            sb.AppendLine("  二段築の下段(城の石垣の底が見え面の前の地表より上に出る所だけ): " + ng + " 駒");
        }
        // 出隅(城の石垣)
        {
            var kcs = new List<GameObject>();
            // 腕の要る長さ(EdoBuild.KadoShortArm): 相手 = 先に据えた隅(43° と 37° の隅は 0.64m しか離れず腕 2.0m が当たる)。
            //   焼いた短い腕の組が無ければ素の腕のまま ⚠ で要る長さを刷る(焼く一覧の行 ── 部材方へ)
            Func<float, float, float, float, string> armOf = EdoAssets.Own.IshigakiKado;
            // 二重折れ(P4/P5 = 43° + 37°・間 0.64)は一つの駒(IshigakiKado2・腕は焼いた名のまま)── 綴りの頭だけ渡す
            Func<float, float, float, float, string> kado2Of = (d1, d2, mid, hh) => { var p2 = EdoAssets.Own.IshigakiKado2(d1, d2, mid, hh, 0f, 0f); return p2.Substring(0, p2.LastIndexOf("_A")) + ".fbx"; };
            int kn = EdoBuild.PlaceRunCorners(runEnds, segPieces, EdoAssets.Own.IshigakiKado, SkinGround, grp, 0.02f, log, kcs, kcs, armOf, kado2Of);
            castle.AddRange(kcs);
            sb.AppendLine("  城の石垣の出隅: " + kn + " 駒");
        }
        // ⭐ 端の天端上げ(指図 terraceWalls[].endRaise・EDO-0502 第37巡)── SodeBenches が解いた "<名>#raise" の小段の線で野面の区間を割り、
        //   端の側を高い天端の別の区間にする(段違いは割った点 = 駒の継ぎ目・継ぎ目の下は StackDownAtNozuraSteps が積み下ろす)。背の小段は benchAll へ(地形へ盛る)。
        //   koshiEnd(切る小段)はこの区間に当てない【硬】(endRule.koshi が raisedSegs を外す)
        var raisedSegs = new List<string>();
        foreach (var kv in sodeB)
        {
            if (!kv.Key.EndsWith("#raise")) continue;
            foreach (var pr in kv.Value)
            {
                var bk = pr.Value; var sg = nozSegs.Find(q => q.name == bk.name);
                if (sg == null) { sb.AppendLine("  ★ endRaise " + bk.name + ": 野面の区間が無い ── 上げない"); continue; }
                float yt = bk.top, yLo = sg.crestAt(0f);
                var ns = new EdoBuild.NozuraSeg { name = bk.name + "_raise", crestAt = sl => yt };
                if (Vector2.Distance(sg.b, bk.b) < 0.05f) { ns.a = bk.a; ns.b = sg.b; sg.b = bk.a; }
                else if (Vector2.Distance(sg.a, bk.b) < 0.05f) { ns.a = sg.a; ns.b = bk.a; sg.a = bk.a; }
                else { sb.AppendLine("  ★ endRaise " + bk.name + ": 小段の端が区間の端に無い ── 上げない"); continue; }
                sg.crestAt = sl => yLo;
                nozSegs.Add(ns); raisedSegs.Add(ns.name); benchAll.Add(bk);
                sb.AppendLine("  端の天端上げ " + ns.name + ": 長さ " + Vector2.Distance(ns.a, ns.b).ToString("F2") + "m・天端 " + yLo.ToString("F2") + " → " + yt.ToString("F2") + "(指図 endRaise)・背の小段 " + (yt - bk.drop).ToString("F2"));
            }
        }
        // 出隅の踊り場の背の小段(指図 sodeSlope 追記 2026-10-07・第42巡)── 切りと盛り(上限は設計面から)
        foreach (var kv in sodeB) if (kv.Key.EndsWith("#land")) foreach (var pr in kv.Value) benchAll.Add(pr.Value);
        // 石段の脇の返しの背(sideBack)と両端の延長の背(endsBack)── 第60巡・StairSideAndEndBacks
        foreach (var kv in sodeB) if (kv.Key.EndsWith("#side") || kv.Key.EndsWith("#endsBack")) foreach (var pr in kv.Value) benchAll.Add(pr.Value);
        // 袖の背の小段の裏込めを地形へ盛る(指図 backfill・EdoBuild.BackBenchWrite ── 盛るだけ・盛り ≤ 上限は設計面から)。据えより先に(皮の設計の地盤も同じ式)
        if (benchAll.Count > 0)
        {
            float bfm, bcm; int bn = EdoBuild.BackBenchWrite(benchAll, out bfm, out bcm);
            AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
            sb.AppendLine("  袖の背の小段の裏込め: run " + benchAll.Count + "・盛り/切りの節点 " + bn + "・今回の盛り 最大 " + bfm.ToString("F2") + "m・切り 最大 " + bcm.ToString("F2") + "m(上限は設計面から)");
        }
        // 野面の乱積み(城の石垣の実面へ端を突き付ける・pool)
        if (nozSegs.Count > 0)
        {
            var heights = new[] { 0.30f, 0.60f, 0.90f, 1.20f, 1.50f, 1.80f, 2.10f, 2.40f, 4.80f };
            castle.RemoveAll(g => g == null);
            var poolN = new List<GameObject>(castle);
            poolN.AddRange(extraPool);
            // 台の北の端の返しの石垣(指図 grading.omoteNagayaDai.northEnd / terraceWalls[].start が northEnd を名指す欄)── 読んで渡すだけ。
            //   線 = 名指された土留めの始まりの節点から、台の道の側の石垣(northEnd.at の run = 台の runs[0] の基壇の駒)の天端の前の面まで、
            //   その石垣の走りに直交して(= N40_2 の北の妻の線)。天端 = 台の上の長屋の座(N40_2 の据わった高さ)。土留めの始まりとは同じ網で継ぐ(出隅か入隅かは見え面から解く ── 岡部の実地は郭の側から見て入隅)
            //   (EdoBuild.PlaceNozuraNet の隅の駒)。道の側の石垣の端は「近くの駒の実面へ」── その石垣の駒だけを相手に渡す。(EDO-0502 第17巡)
            {
                var gr = O(Get(D, "grading")); var dai = gr == null ? null : O(Get(gr, "omoteNagayaDai")); var ne = dai == null ? null : O(Get(dai, "northEnd"));
                var druns = dai == null ? null : A(Get(dai, "runs"));
                string twName = null;
                foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>()) { var tw = O(o); string st = tw == null ? null : S(Get(tw, "start")); if (st != null && st.Contains("northEnd")) twName = S(Get(tw, "name")); }
                var seg0 = twName == null ? null : nozSegs.Find(q => q.name == twName + "_0_0");
                var rootN = GameObject.Find(GN); var igN = rootN == null ? null : rootN.transform.Find("Ishigaki");
                string run0 = druns != null && druns.Count > 0 ? S(druns[0]) : null;
                var seatT = rootN == null || run0 == null ? null : rootN.transform.Find("Kakoi/" + run0);
                if (ne != null && seg0 != null && igN != null && seatT != null)
                {
                    var road = new List<GameObject>(); foreach (Transform c in igN) if (c.gameObject.activeInHierarchy && c.name.StartsWith("IG_" + run0 + "_")) road.Add(c.gameObject);
                    // 道の側の石垣の走り(駒の芯の両端)と、始まりの節点からその面への向き
                    Vector2 cA = Vector2.zero, cB = Vector2.zero; float best = -1f;
                    foreach (var g1 in road) foreach (var g2 in road)
                    { var b1 = EdoBuild.RB(g1).center; var b2 = EdoBuild.RB(g2).center; float dd = (new Vector2(b1.x - b2.x, b1.z - b2.z)).sqrMagnitude; if (dd > best) { best = dd; cA = new Vector2(b1.x, b1.z); cB = new Vector2(b2.x, b2.z); } }
                    Vector2 t = (cB - cA).normalized, nrm = new Vector2(-t.y, t.x); Vector2 P0 = seg0.a;
                    if (Vector2.Dot(cA - P0, nrm) < 0f) nrm = -nrm;
                    float seat = seatT.position.y;
                    //   道の側の石垣は殻(背の面が無い)⇒ 光線でなく、天端の帯(座 − 0.4 より上)の頂点のうち返しの線の脇 1m に入る物の最も手前
                    float hit = float.NaN;
                    foreach (var g in road) foreach (var v in EdoBuild.Body(g.transform, 999999))
                    {
                        if (v.y < seat - 0.4f) continue; Vector2 r = new Vector2(v.x, v.z) - P0;
                        if (Mathf.Abs(Vector2.Dot(r, t)) > 1.0f) continue; float u = Vector2.Dot(r, nrm);
                        if (u > 0f && u < 8f && (float.IsNaN(hit) || u < hit)) hit = u;
                    }
                    if (float.IsNaN(hit)) sb.AppendLine("  返しの石垣(" + run0 + " の北の端): ⚠ 道の側の石垣の面を測れず ── 建てない");
                    else
                    {
                        Vector2 Pa = P0 + nrm * hit;
                        nozSegs.Add(new EdoBuild.NozuraSeg { name = twName + "_Kaeshi_0", a = Pa, b = P0, crestAt = sl => seat });
                        foreach (var g in road) { var rb = EdoBuild.RB(g); if (Vector2.Distance(new Vector2(rb.center.x, rb.center.z), Pa) < 4f) poolN.Add(g); }
                        sb.AppendLine("  返しの石垣(" + run0 + " の北の端 → " + twName + " の始まり): 長さ " + hit.ToString("F2") + "m・天端 " + seat.ToString("F2") + "(" + run0 + " の座)・野面で " + twName + " の始まりと継ぐ(隅の向きは見え面から PlaceNozuraNet が解く)");
                    }
                }
                else if (ne != null) sb.AppendLine("  返しの石垣: ⚠ 引けず ── 建てない(土留め " + (twName ?? "-") + "・区間 " + (seg0 != null) + "・台の run " + (run0 ?? "-") + "・基壇 " + (igN != null) + "・座 " + (seatT != null) + ")");
            }
            // 端の納め(指図 nozuraEndRule・EDO-0502 第30巡)── 塞ぐ物を読んで渡すだけ(延ばす・見切り石の型は EdoBuild.NozuraEndRule)。
            //   塞ぐ物: 区画線・長屋の背から一間(指図 TW_Minami_Koshi.ends)・据わった城の石垣と建物の実メッシュ(0.3m)
            //   ⚠ ①(延ばして打ち切り)は止めた(maxExtend 0・第30巡): 袖 TW_Kado_Sode_0_0 の始まりを 4.0m 延ばすと段の境の駒と 018f が
            //   門の内の面から 0.71〜1.19m 浮いた(許容0)。延ばす区間の足元の面と段の境の駒の取り合いを型で解くまで ②/③ だけ。
            var endRule = new EdoBuild.NozuraEndRule { mikiri = EdoAssets.Own.SannoNozuraMikiriH, maxExtend = 0f };
            // ② を隅の駒の返しへ(指図 nozuraEndRule 2026-10-06 夕「見切り石 Mikiri_H* は野面の端に使わない」)── 数は指図の文から読む(読めなければ従前の見切り石のまま ★)
            {
                string er = S(Get(D, "nozuraEndRule")) ?? ""; var inv = System.Globalization.CultureInfo.InvariantCulture;
                if (er.Contains("Kado90") && er.Contains("野面の端に使わない"))
                {
                    var mA = System.Text.RegularExpressions.Regex.Match(er, @"返しの腕は\s*([0-9.]+)\s*〜\s*([0-9.]+)");
                    var mB = System.Text.RegularExpressions.Regex.Match(er, @"背の地盤が天端\s*[−\-]\s*([0-9.]+)\s*以内");
                    var mG = System.Text.RegularExpressions.Regex.Match(er, @"下げ打ちの駒\s*[(（]\s*±\s*([0-9.]+)");
                    var mE = System.Text.RegularExpressions.Regex.Match(er, @"見付\s*([0-9.]+)\s*以下まで下げ");
                    if (mA.Success && mB.Success && mG.Success && mE.Success)
                    {
                        endRule.kadoReturn = true; endRule.mikiri = null;
                        endRule.retMin = Mathf.Max(float.Parse(mA.Groups[1].Value, inv), 0.909f); endRule.retMax = float.Parse(mA.Groups[2].Value, inv);
                        if (endRule.retMax < 1.818f && endRule.retMax > 1.79f) endRule.retMax = 1.818f;   // 「1.8」= 隅の腕 0.909 × 2
                        endRule.retBackDiff = float.Parse(mB.Groups[1].Value, inv); endRule.lowerGrade = float.Parse(mG.Groups[1].Value, inv); endRule.lowerToExpose = float.Parse(mE.Groups[1].Value, inv);
                        sb.AppendLine("  端の②: 隅の駒の返し(腕 " + endRule.retMin.ToString("F2") + "〜" + endRule.retMax.ToString("F2") + "・背 天端−" + endRule.retBackDiff.ToString("F2") + "・②' 下げ ±" + endRule.lowerGrade.ToString("F3") + " で見付 ≤ " + endRule.lowerToExpose.ToString("F1") + ")・見切り石を使わない");
                    }
                    else sb.AppendLine("  ★ nozuraEndRule ②の隅の返しの数が指図から読めない(腕 " + mA.Success + "・背 " + mB.Success + "・下げ " + mG.Success + "・見付 " + mE.Success + ")── 従前の見切り石");
                }
                // ③ を積み止めの駒で終える(指図 nozuraEndRule 追記 2026-10-07b「③になる端は積み止めの駒で終える(高さは見付+根入れ0.3以上の最も低い段)」・EDO-0502 第43巡)
                //   型は EdoBuild.PlaceNozuraTome。⛔ 根入れが読めなければ ★ を刷って当てない(③ のまま)
                if (er.Contains("積み止め"))
                {
                    var mN = System.Text.RegularExpressions.Regex.Match(er, @"見付\s*\+\s*根入れ\s*([0-9.]+)\s*以上");
                    if (mN.Success)
                    {
                        endRule.tome = EdoAssets.Own.SannoNozuraTome; endRule.tomeH = EdoAssets.Own.SannoNozuraTomeH; endRule.tomeNeiri = float.Parse(mN.Groups[1].Value, inv);
                        sb.AppendLine("  端の③: 積み止めの駒で終える(段は見付 + 根入れ " + endRule.tomeNeiri.ToString("F2") + " 以上の最も低い焼いた段)");
                    }
                    else sb.AppendLine("  ★ nozuraEndRule 追記b: 積み止めの根入れが指図から読めない ── ③ のまま");
                }
            }
            // 指図 nozuraEndRule 追記(2026-10-06・第31巡): koshiEnd = 背が法の腰の土留め(TW_Kita_Koshi・TW_Higashi_Minami・TW_Nishi_Kado)の端の背を
            //   天端 −0.05 の小段一間+法 1:1.5(切り ≤1.0・練塀の犬走り 0.3 を割らない)/ tallEnd = 見付が見切り石の最高段 2.4 を超える端は背の側へ返す(差 0.6 未満で終える)。
            //   数は指図の文の値(型の既定と同じ)── 型は EdoBuild.NozuraEndRule・CutKoshiBench
            // ⭐ 追記3(第34巡): koshiEnd は背が切土の端だけ ── 背が盛りの法尻の野面石(指図 toeBench を持つ欄)は toeEnd(toeBench で背を描き直してから②)
            var toeWalls = new List<string>(); var cutMaxOf = new Dictionary<string, float>(); string toeTxt = null;
            foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>())
            {
                var tw = O(o); if (tw == null) continue; string twn = S(Get(tw, "name"));
                if (!string.IsNullOrEmpty(S(Get(tw, "toeBench")))) { toeWalls.Add(twn); toeTxt = S(Get(tw, "toeBench")); }
                var ecm = O(Get(tw, "endCutMax")); if (ecm != null && Get(ecm, "value") != null) cutMaxOf[twn] = F(Get(ecm, "value"));
            }
            endRule.koshi = nm0 => (nm0.StartsWith("TW_Kita_Koshi") || nm0.StartsWith("TW_Higashi_Minami") || nm0.StartsWith("TW_Nishi_Kado")) && !toeWalls.Exists(w0 => nm0.StartsWith(w0 + "_"))
                                     && !raisedSegs.Contains(nm0);   // endRaise の区間には切る小段を当てない【硬】(第37巡)
            endRule.koshiCutMaxOf = nm0 => { foreach (var kv in cutMaxOf) if (nm0.StartsWith(kv.Key + "_")) return kv.Value; return float.NaN; };
            endRule.toe = nm0 => toeWalls.Exists(w0 => nm0.StartsWith(w0 + "_"));
            {
                System.Func<string, string, float> rxT = (txt, pat) => { var m = System.Text.RegularExpressions.Regex.Match(txt ?? "", pat); return m.Success ? float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : float.NaN; };
                float td0 = rxT(toeTxt, @"天端\s*[−\-]\s*([0-9.]+)"), tb0 = rxT(toeTxt, @"控えの後端\s*\+\s*([0-9.]+)"), tf0 = rxT(toeTxt, @"1\s*:\s*([0-9.]+)");
                if (toeWalls.Count > 0 && (float.IsNaN(td0) || float.IsNaN(tb0) || float.IsNaN(tf0))) { sb.AppendLine("  ★ toeEnd: 指図 toeBench から読めない ── 当てない"); endRule.toe = null; }
                else { endRule.toeDrop = td0; endRule.toeBehind = tb0; endRule.toeBatter = tf0; }
                var keepB = new List<Bounds>(); var wallB = new List<Bounds>(); var rootT = GameObject.Find(GN);
                foreach (var gname in new[] { "Kakoi", "Buildings", "Service_v3", "KachuNagaya_v3", "Ishigaki" })
                { var gt = rootT == null ? null : rootT.transform.Find(gname); if (gt != null) foreach (var mr in gt.GetComponentsInChildren<MeshRenderer>()) if (mr.gameObject.activeInHierarchy) { var bb = mr.bounds; if (gname == "Kakoi") { bb.Expand(new Vector3(2f * (0.3f + EdoBuild.HeightCell()), 0f, 2f * (0.3f + EdoBuild.HeightCell()))); wallB.Add(bb); } else keepB.Add(bb); } }   // 練塀・隅は犬走り 0.3 + 地形の一升(⛔ 外周の石垣は広げない ── 辺24 の背が切れず被りが 6→11)(床の升を切らない ── 第34巡 NW_Hei_5_0 が 0.32 下がった)
                endRule.toeKeep = (q, nw) => KeepToe(keepB, wallB, q, nw);
            }
            endRule.parcel = Poly; endRule.tallMin = 2.4f; endRule.tallReturnDiff = 0.6f;
            // 指図 nozuraEndRule 追記2(2026-10-06・第32巡): ④差し込み = 天端のまま延ばし地盤が天端 +0.1 に届く所から半駒(0.9)先で終える・上限 2 駒(3.6)/
            //   koshiEnd の改め = 小段の奥行の下限は駒の控えの後端 +0.3・狙い一間・背が切土なら const.batterCut の法・小段は端の先へ 1/20 で落とす(型は EdoBuild.CutKoshiBench)
            endRule.insertMax = 3.6f; endRule.insertReach = 0.1f; endRule.insertTail = 0.9f;
            endRule.koshiBenchBack = 0.3f; endRule.koshiBatterCut = C("batterCut"); endRule.koshiDrain = 20f;
            { var bd = EdoBuild.BaseDem(); endRule.koshiIsCut = q => { float b0 = bd(q.x, q.y), g0 = DesignY(q); return !float.IsNaN(b0) && !float.IsNaN(g0) && g0 < b0 - 0.05f; }; }
            {
                endRule.koshiKeep = new List<GameObject>();
                var rk = GameObject.Find(GN); var kk0 = rk == null ? null : rk.transform.Find("Kakoi");
                if (kk0 != null) foreach (Transform c in kk0) if (c.gameObject.activeInHierarchy && !EdoBuild.IsNagayaBody(c.gameObject)) endRule.koshiKeep.Add(c.gameObject);   // 型で(⛔ 名の頭 N は練塀 NW_Hei・N_Hei も拾う・第34巡)
            }
            {
                // 塞ぐ物(指図 nozuraEndRule 追記3・第34巡): 長屋の躯体から一間(型で見る ── EdoBuild.IsNagayaBody)/ 建物の実面 1.0 /
                //   練塀・隅・据わった城の石垣は延ばす向きを**横切る**物だけ 0.3(駒の走りの主軸 EdoBuild.RunAxis と延ばす向きの角が 30° 以内なら平行に走る ⇒ 数えない)
                var cells = new Dictionary<long, List<KeyValuePair<Vector2, Vector4>>>();   // (点, (半径, 種別 0長屋/1建物/2塀, 主軸 x, 主軸 z))
                System.Action<GameObject, float, int> addObs = (go, r, kind) =>
                {
                    var ax = kind == 2 ? EdoBuild.RunAxis(go) : Vector2.zero;
                    foreach (var v in EdoBuild.Body(go.transform, 600))
                    { long key = ((long)Mathf.FloorToInt(v.x) << 32) ^ (uint)Mathf.FloorToInt(v.z); List<KeyValuePair<Vector2, Vector4>> l;
                      if (!cells.TryGetValue(key, out l)) cells[key] = l = new List<KeyValuePair<Vector2, Vector4>>(); l.Add(new KeyValuePair<Vector2, Vector4>(new Vector2(v.x, v.z), new Vector4(r, kind, ax.x, ax.y))); }
                };
                var rootE = GameObject.Find(GN);
                var kk = rootE == null ? null : rootE.transform.Find("Kakoi");
                int nNag = 0, nHei = 0;
                if (kk != null) foreach (Transform c in kk) if (c.gameObject.activeInHierarchy) { bool nag = EdoBuild.IsNagayaBody(c.gameObject); if (nag) nNag++; else nHei++; addObs(c.gameObject, nag ? C("ken") : 0.3f, nag ? 0 : 2); }
                foreach (var gname in new[] { "Buildings", "Service_v3", "KachuNagaya_v3" })
                { var gt = rootE == null ? null : rootE.transform.Find(gname); if (gt != null) foreach (Transform c in gt) if (c.gameObject.activeInHierarchy) addObs(c.gameObject, 1.0f, 1); }
                foreach (var g in castle) if (g != null) addObs(g, 0.3f, 2);
                sb.AppendLine("  端の納めの塞ぐ物: 長屋の躯体 " + nNag + "・練塀/隅 " + nHei + "(型で分けた)・城の石垣 " + castle.Count + " ── 塀と石垣は延ばす向きを横切る物だけ");
                var polyE = Poly; float cos30 = Mathf.Cos(30f * Mathf.Deg2Rad);
                endRule.blockedDir = (q, dir) =>
                {
                    if (!EdoGeom.PIP(polyE, q)) return "区画線";
                    int cx = Mathf.FloorToInt(q.x), cz = Mathf.FloorToInt(q.y);
                    for (int dx = -2; dx <= 2; dx++) for (int dz = -2; dz <= 2; dz++)
                    {
                        List<KeyValuePair<Vector2, Vector4>> l; if (!cells.TryGetValue(((long)(cx + dx) << 32) ^ (uint)(cz + dz), out l)) continue;
                        foreach (var pv in l)
                        {
                            float r = pv.Value.x; if ((pv.Key - q).sqrMagnitude >= r * r) continue;
                            int kind = (int)pv.Value.y;
                            if (kind == 2) { var ax = new Vector2(pv.Value.z, pv.Value.w); if (ax != Vector2.zero && dir != Vector2.zero && Mathf.Abs(Vector2.Dot(ax, dir.normalized)) >= cos30) continue; }   // 平行に走る塀・基壇は数えない
                            return kind == 0 ? "長屋の躯体から一間" : kind == 1 ? "建物の実面" : "横切る塀・石垣の実面";
                        }
                    }
                    return null;
                };
                // 隅の返しの腕(指図 nozuraEndRule ②「腕は塞ぐ物の実面・長屋の背の一間・犬走り 0.3 に入れない」)── 長屋は躯体の長手の脇(背・前)だけ一間、
                //   妻の先は実面から 0.3(犬走り)。塀・建物・城の石垣は実面から 0.3。区画線の外は入れない
                var nagV = new List<List<Vector2>>(); var nagAx = new List<Vector2>(); var nagC = new List<Vector2>(); var nagR = new List<Vector2>();
                if (kk != null) foreach (Transform c in kk) if (c.gameObject.activeInHierarchy && EdoBuild.IsNagayaBody(c.gameObject))
                {
                    var vs = new List<Vector2>(); foreach (var v in EdoBuild.Body(c.transform, 600)) vs.Add(new Vector2(v.x, v.z)); if (vs.Count == 0) continue;
                    var ax = EdoBuild.RunAxis(c.gameObject); if (ax == Vector2.zero) continue; ax.Normalize();
                    Vector2 ce = Vector2.zero; foreach (var v in vs) ce += v; ce /= vs.Count;
                    float lo = float.MaxValue, hi = float.MinValue; foreach (var v in vs) { float u = Vector2.Dot(v - ce, ax); lo = Mathf.Min(lo, u); hi = Mathf.Max(hi, u); }
                    nagV.Add(vs); nagAx.Add(ax); nagC.Add(ce); nagR.Add(new Vector2(lo, hi));
                }
                float kenA = C("ken");
                endRule.armBlock = (q, dir) =>
                {
                    if (!EdoGeom.PIP(polyE, q)) return "区画線";
                    for (int i = 0; i < nagV.Count; i++)
                    {
                        float dmin = float.MaxValue; foreach (var v in nagV[i]) dmin = Mathf.Min(dmin, (v - q).sqrMagnitude); dmin = Mathf.Sqrt(dmin);
                        float u = Vector2.Dot(q - nagC[i], nagAx[i]);
                        bool beside = u >= nagR[i].x && u <= nagR[i].y;
                        if (beside && dmin < kenA) return "長屋の背・前の一間";
                        if (dmin < 0.3f) return "長屋の妻の実面から 0.3";
                    }
                    int cx = Mathf.FloorToInt(q.x), cz = Mathf.FloorToInt(q.y);
                    for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++)
                    {
                        List<KeyValuePair<Vector2, Vector4>> l; if (!cells.TryGetValue(((long)(cx + dx) << 32) ^ (uint)(cz + dz), out l)) continue;
                        foreach (var pv in l) if ((int)pv.Value.y != 0 && (pv.Key - q).sqrMagnitude < 0.09f) return (int)pv.Value.y == 1 ? "建物の実面から 0.3" : "塀・石垣の実面から 0.3";
                    }
                    return null;
                };
                // ⭐ 端ごとの型(指図 returnEnd・endKado・kadoReturnUniform・普請方の設計 2026-10-07・EDO-0502 第41巡)── 欄の文の値を読んで EdoBuild.EndSpec へ渡すだけ
                //   (型は EdoBuild.KadoReturnEnd)。⛔ 読めなければ ★ を刷って既定のまま
                {
                    var inv = System.Globalization.CultureInfo.InvariantCulture;
                    System.Func<string, string, int, float> rxv = (txt, pat, gi) => { var m = System.Text.RegularExpressions.Regex.Match(txt ?? "", pat); return m.Success ? float.Parse(m.Groups[gi].Value, inv) : float.NaN; };
                    System.Func<string, int> kanji = txt => { var m = System.Text.RegularExpressions.Regex.Match(txt ?? "", @"([一二三四五])駒"); return m.Success ? "一二三四五".IndexOf(m.Groups[1].Value) + 1 : 1; };
                    var specs = new List<KeyValuePair<Func<EdoBuild.NozuraSeg, int, bool>, EdoBuild.EndSpec>>();
                    string erT = S(Get(D, "nozuraEndRule")) ?? "";
                    float sinkEx = rxv(erT, @"見付\s*([0-9.]+)\s*以下になった所で打ち切り", 1);
                    // 腕の向き = 左右(±見え面)のうち長屋の躯体の実面から遠ざかる側(端から 0.9 先の点で、最も近い躯体の頂点までが遠い方)
                    var nagAll = new List<Vector2>(); foreach (var vs in nagV) nagAll.AddRange(vs);
                    Func<Vector2, Vector2, Vector2> awayNag = (ep, fN) =>
                    {
                        float best = float.MinValue; Vector2 bd = -fN;
                        foreach (var d in new[] { -fN, fN })
                        { Vector2 q = ep + d * 0.9f; float dm = float.MaxValue; foreach (var v in nagAll) dm = Mathf.Min(dm, (v - q).sqrMagnitude); if (dm > best) { best = dm; bd = d; } }
                        return bd;
                    };
                    var abutPool = new List<GameObject>();
                    foreach (var gname in new[] { "Kakoi", "Ishigaki" }) { var gt = rootE == null ? null : rootE.transform.Find(gname); if (gt != null) foreach (Transform c in gt) if (c.gameObject.activeInHierarchy && !EdoBuild.IsNagayaBody(c.gameObject)) abutPool.Add(c.gameObject); }
                    foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>())
                    {
                        var tw = O(o); if (tw == null) continue; string twn = S(Get(tw, "name"));
                        string reT = S(Get(tw, "returnEnd"));
                        if (reT != null && reT.Contains("積み止め"))
                        {   // 指図 returnEnd(2026-10-07): 返しの終わりは今の位置のまま積み止めで終える(段は見付 + 根入れの規則)
                            var sp = new EdoBuild.EndSpec { label = twn + ".returnEnd", tome = true };
                            string pre = twn + "#ret"; specs.Add(new KeyValuePair<Func<EdoBuild.NozuraSeg, int, bool>, EdoBuild.EndSpec>((sg, e) => sg.name.StartsWith(pre), sp));
                            sb.AppendLine("  端の型 " + sp.label + ": 今の位置のまま積み止めで終える(段は見付 + 根入れ " + endRule.tomeNeiri.ToString("F2") + " 以上)" + (endRule.tome == null ? " ★ 積み止めの口が無い(③ のまま)" : ""));
                        }
                        else if (reT != null && reT.Contains("遠ざかる側"))
                        {
                            float aMin = rxv(reT, @"腕\s*([0-9.]+)\s*〜\s*([0-9.]+)", 1), gG = rxv(reT, @"G\s*[−\-]\s*([0-9]+)", 1), sx = rxv(reT, @"見付\s*([0-9.]+)\s*で沈め", 1);
                            if (float.IsNaN(aMin) || float.IsNaN(gG) || float.IsNaN(sx)) sb.AppendLine("  ★ " + twn + ".returnEnd: 腕の下限・沈めの勾配・見付が読めない ── 既定の②");
                            else
                            {
                                var sp = new EdoBuild.EndSpec { label = twn + ".returnEnd", armDir = awayNag, armMin = aMin, noLower = true, sinkIfShort = true, sinkGrade = gG / 1000f, sinkExpose = sx, sinkMaxPieces = kanji(reT) };
                                string pre = twn + "#ret"; specs.Add(new KeyValuePair<Func<EdoBuild.NozuraSeg, int, bool>, EdoBuild.EndSpec>((sg, e) => sg.name.StartsWith(pre), sp));
                                sb.AppendLine("  端の型 " + sp.label + ": 腕は長屋の躯体から遠ざかる側・腕 ≥ " + aMin.ToString("F2") + "・足りなければ①(" + sp.sinkMaxPieces + " 駒を勾配 " + sp.sinkGrade.ToString("F2") + " で見付 " + sx.ToString("F2") + ")");
                            }
                        }
                        string ekT = S(Get(tw, "endKado"));
                        if (ekT != null && ekT.Contains("積み止め"))
                        {   // 指図 endKado(2026-10-07): 「<区間> の端<e>: 積み止めの H2400 で終える(0.07 沈め)」── 段は名指し
                            var mE = System.Text.RegularExpressions.Regex.Match(ekT, @"^(\S+?)\s*の端\s*([01])");
                            float hT = rxv(ekT, @"積み止めの\s*H\s*([0-9]{4})", 1);
                            if (!mE.Success || float.IsNaN(hT)) sb.AppendLine("  ★ " + twn + ".endKado: 積み止めの端・段が読めない ── 既定");
                            else
                            {
                                string segN = twn + "_" + mE.Groups[1].Value; int eN = int.Parse(mE.Groups[2].Value);
                                var sp = new EdoBuild.EndSpec { label = twn + ".endKado", tome = true, tomeH = hT / 1000f };
                                // 追記 2026-10-07(第45巡): 積み止めは区画の外へ 0・駒の最も外の点を塀の内面から c 以上内【硬】── 端を run に沿って内へ引く(目安・PlaceBest【柔】)
                                float tc = rxv(ekT, @"塀の内面から\s*([0-9.]+)\s*以上内", 1), ta = rxv(ekT, @"目安\s*([0-9.]+)", 1);
                                string tcNote = "";
                                if (!float.IsNaN(tc))
                                {
                                    var kak = new List<GameObject>(); var kt = rootE == null ? null : rootE.transform.Find("Kakoi");
                                    if (kt != null) foreach (Transform c in kt) if (c.gameObject.activeInHierarchy) kak.Add(c.gameObject);
                                    sp.tomeClear = tc; sp.tomePullAim = ta; sp.tomeWalls = kak; sp.tomeParcel = Poly;
                                    tcNote = "・区画の外 0 と塀の内面から " + tc.ToString("F2") + " 以上内【硬】(塀 " + kak.Count + " 駒)・端を内へ引く狙い " + (float.IsNaN(ta) ? "★読めない(0)" : ta.ToString("F1")) + "【柔】";
                                }
                                else if (ekT.Contains("塀の内面")) tcNote = " ★ 塀の内面からの離れが読めない";
                                specs.Add(new KeyValuePair<Func<EdoBuild.NozuraSeg, int, bool>, EdoBuild.EndSpec>((sg, e) => sg.name == segN && e == eN, sp));
                                sb.AppendLine("  端の型 " + sp.label + "(" + segN + " 端" + eN + "): 積み止め H" + sp.tomeH.ToString("F2") + " で終える" + tcNote + (endRule.tome == null ? " ★ 積み止めの口が無い(③ のまま)" : ""));
                            }
                        }
                        else if (ekT != null)
                        {
                            var mE = System.Text.RegularExpressions.Regex.Match(ekT, @"^(\S+?)\s*の端\s*([01])");
                            float gG = rxv(ekT, @"G\s*[−\-]\s*([0-9]+)", 1);
                            float lt = rxv(ekT, @"見付\s*[0-9.]+\s*→\s*([0-9.]+)", 1); if (float.IsNaN(lt)) lt = rxv(ekT, @"見付\s*([0-9.]+)\s*以下へ下げ", 1);
                            if (!mE.Success || float.IsNaN(gG) || float.IsNaN(lt)) { sb.AppendLine("  ★ " + twn + ".endKado: 端・下げの勾配・見付が読めない ── 既定"); continue; }
                            string segN = twn + "_" + mE.Groups[1].Value; int eN = int.Parse(mE.Groups[2].Value);
                            var sp = new EdoBuild.EndSpec { label = twn + ".endKado", lowerGrade = gG / 1000f, lowerToExpose = lt, lowerMaxPieces = kanji(ekT), armMin = rxv(ekT, @"下限\s*([0-9.]+)", 1) };
                            float ab = rxv(ekT, @"延ばす向き\s*([0-9.]+)\s*m\s*の内", 1); if (!float.IsNaN(ab)) { sp.abutAhead = ab; sp.abutPool = abutPool; }
                            if (ekT.Contains("①で沈める")) { sp.sinkIfShort = true; sp.sinkGrade = sp.lowerGrade; sp.sinkExpose = float.IsNaN(sinkEx) ? 0.15f : sinkEx; sp.sinkMaxPieces = 3; }
                            specs.Add(new KeyValuePair<Func<EdoBuild.NozuraSeg, int, bool>, EdoBuild.EndSpec>((sg, e) => sg.name == segN && e == eN, sp));
                            sb.AppendLine("  端の型 " + sp.label + "(" + segN + " 端" + eN + "): " + (float.IsNaN(sp.abutAhead) ? "" : "⓪ 先 " + sp.abutAhead.ToString("F1") + "m の実面へ突き付け → ") + "②' " + sp.lowerMaxPieces + " 駒まで勾配 " + sp.lowerGrade.ToString("F2") + " で見付 ≤ " + lt.ToString("F2")
                                        + (float.IsNaN(sp.armMin) ? "" : "・腕 ≥ " + sp.armMin.ToString("F2")) + (sp.sinkIfShort ? "・足りなければ①" : ""));
                        }
                        string kuT = S(Get(tw, "kadoReturnUniform"));
                        if (kuT != null)
                        {
                            float af = rxv(kuT, @"腕は\s*([0-9.]+)\s*の定尺", 1); if (af > 1.79f && af < 1.818f) af = 1.818f;
                            var sp = new EdoBuild.EndSpec { label = twn + ".kadoReturnUniform", armFixed = af, uniformH = kuT.Contains("H に揃え") };
                            string pre = twn + "_"; specs.Add(new KeyValuePair<Func<EdoBuild.NozuraSeg, int, bool>, EdoBuild.EndSpec>((sg, e) => sg.name.StartsWith(pre), sp));
                            sb.AppendLine("  端の型 " + sp.label + ": 腕 " + (float.IsNaN(af) ? "★読めない" : af.ToString("F3") + " の定尺一本") + (sp.uniformH ? "・隅と返しと際の H を揃える" : ""));
                        }
                    }
                    endRule.spec = (sg, e) => { foreach (var kv in specs) if (kv.Key(sg, e)) return kv.Value; return null; };
                }
            }
            // 段違いの継ぎ目を勾配の駒で斜めに流す(指図 terraceWalls[].stepJoint・返しは returnEnd が「stepJoint と同じく流す」と名指す欄)── 型は EdoBuild.FlowStepJoints
            {
                var flowW = new List<string>(); string sjT = null;
                foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>())
                {
                    var tw = O(o); if (tw == null) continue; string twn = S(Get(tw, "name"));
                    string sj = S(Get(tw, "stepJoint"));
                    if (sj != null && sj.Contains("使わない")) { sb.AppendLine("  段違いの流し(stepJoint): " + twn + " は使わない(指図 ── " + (Get(tw, "sodeSlope") != null ? "sodeSlope へ置き換え" : "欄の文") + ")"); sj = null; }
                    if (sj != null) { flowW.Add(twn + "_"); sjT = sj; }
                    string re = S(Get(tw, "returnEnd")); if (re != null && re.Contains("stepJoint")) flowW.Add(twn + "#ret");
                }
                if (flowW.Count > 0 && sjT != null)
                {
                    var choices = new List<Vector2>(); var inv = System.Globalization.CultureInfo.InvariantCulture;
                    foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(sjT, @"([0-9.]+)\s*間の\s*±\s*([0-9.]+)"))
                        choices.Add(new Vector2(float.Parse(m.Groups[1].Value, inv) * C("ken"), float.Parse(m.Groups[2].Value, inv)));
                    var mh = System.Text.RegularExpressions.Regex.Match(sjT, @"不揃い\s*±\s*([0-9.]+)");
                    if (choices.Count == 0 || !mh.Success) sb.AppendLine("  ★ stepJoint: 走りと勾配・頭の不揃いが指図から読めない ── 流さない");
                    else
                    {
                        var fl = new List<EdoBuild.NozuraSeg>(); var rest = new List<EdoBuild.NozuraSeg>();
                        foreach (var sg0 in nozSegs) (flowW.Exists(pf => sg0.name.StartsWith(pf)) ? fl : rest).Add(sg0);
                        var un = new List<string>(); var sjLog = new System.Text.StringBuilder();
                        var flowed = EdoBuild.FlowStepJoints(fl, choices, 0.5f, float.Parse(mh.Groups[1].Value, inv), un, sjLog);
                        int nFlow = 0; foreach (var q in flowed) if (q.flow) nFlow++;
                        nozSegs = rest; nozSegs.AddRange(flowed);
                        sb.AppendLine("  段違いの流し(stepJoint): 流した " + nFlow + " 区間・⚠ 取れない継ぎ目 " + un.Count + "(段のまま ── 普請方へ)");
                        sb.Append(sjLog.ToString());
                    }
                }
            }
            var got = EdoBuild.PlaceNozuraNet(nozSegs, SkinGround, SkinGround, 1.2f, grp,
                (h, g, i) => EdoAssets.Own.SannoNozura(h, g, i), (h, i) => EdoAssets.Own.SannoNozuraKado(h, i),
                (up, i) => EdoAssets.Own.SannoNozuraDan(up, i), (up, i) => EdoAssets.Own.SannoNozuraKiri(up, i),
                EdoAssets.Own.SannoNozuraMikiriH, heights, poolN, log, null, EdoAssets.Own.SannoNozuraNoriEnd,   // 入隅の可動側の端は小口を相手の法で切った駒(型は EdoBuild・EDO-0502 第16巡)
                null, endRule);
            sb.AppendLine("  野面の端の納め(nozuraEndRule): " + endRule.record.Count + " 端");
            foreach (var r0 in endRule.record) sb.AppendLine("    " + r0);
            var per = new Dictionary<string, int>();
            foreach (var kv in got) { string k = kv.Key.name; foreach (var w in wallOf.Keys) if (k.StartsWith(w + "_")) { int c0; per.TryGetValue(w, out c0); per[w] = c0 + 1; } }
            foreach (var kv in per) sb.AppendLine("  " + kv.Key + "(" + S(Get(wallOf[kv.Key], "kind")) + "・" + S(Get(wallOf[kv.Key], "mode")) + "): 野面の乱積み " + kv.Value + " 駒");
            sb.AppendLine("  野面 計 " + got.Count + " 駒(区間 " + nozSegs.Count + ")");
            // 袖の坂の硬い検め(指図 sodeSlope「天端と背の地盤の差 ≤0.3」【硬】)── 据えた駒の天端(線から背へ天端の奥行の帯の最高)と背の地盤(皮が描く地表・帯の 0.1 奥)
            foreach (var ck in sodeSlopeChk)
            {
                var pcs = new List<Vector3>(); foreach (var kv in got) if (kv.Key != null && kv.Key.name.StartsWith(ck.key + "_")) pcs.AddRange(EdoBuild.Body(kv.Key.transform, 999999));
                float worst = float.MinValue; Vector2 wAt = Vector2.zero; float wC = 0f, wB = 0f; int nOver = 0, nPt = 0;
                for (int i = 0; i < ck.line.Count; i++)
                {
                    Vector2 p = ck.line[i], n = ck.back[i], t = i + 1 < ck.line.Count ? (ck.line[i + 1] - p).normalized : (p - ck.line[i - 1]).normalized;
                    float top = float.MinValue; foreach (var v in pcs) { Vector2 r = new Vector2(v.x, v.z) - p; float u = Vector2.Dot(r, n); if (u >= 0f && u <= ck.depth && Mathf.Abs(Vector2.Dot(r, t)) < 0.15f) top = Mathf.Max(top, v.y); }
                    if (top == float.MinValue) continue;
                    Vector2 q = p + n * (ck.depth + 0.1f); float bg = SkinGround(q.x, q.y); if (float.IsNaN(bg)) continue;
                    nPt++; float d = top - bg; if (d > ck.maxDiff + 1e-3f) nOver++;
                    if (d > worst) { worst = d; wAt = p; wC = top; wB = bg; }
                }
                sb.AppendLine("  袖の坂 " + ck.key + " の天端と背の地盤の差(硬 ≤ " + ck.maxDiff.ToString("F2") + "): 最悪 " + (nPt == 0 ? "-" : worst.ToString("+0.00;-0.00")) + "m @(" + wAt.x.ToString("F1") + ", " + wAt.y.ToString("F1") + ")(天端 " + wC.ToString("F2") + "・背 " + wB.ToString("F2") + ")・超え " + nOver + "/" + nPt + " 点" + (nOver > 0 ? " ⛔" : " ⭕"));
            }
            // 段違いの継ぎ目の下を同じ積みの駒で地表まで積み下ろす(指図 TW_Kado_Sode.dropJoint・型として段の境の駒すべてへ ── EdoBuild.StackDownAtNozuraSteps)
            {
                float wb, wa;
                int nt = EdoBuild.StackDownAtNozuraSteps(got, SkinGround, grp, 4, log, out wb, out wa);
                var withField = new List<string>(); foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>()) { var tw = O(o); if (tw != null && Get(tw, "dropJoint") != null) withField.Add(S(Get(tw, "name"))); }
                sb.AppendLine("  段違いの継ぎ目の積み下ろし: " + nt + " 駒・継ぎ目の駒の抜け 最悪 " + (float.IsNegativeInfinity(wb) ? "-" : wb.ToString("+0.000;-0.000")) + " → "
                            + (float.IsNegativeInfinity(wa) ? "-" : wa.ToString("+0.000;-0.000")) + "m(欄 dropJoint: " + string.Join("・", withField.ToArray()) + ")" + (wa > 0.005f ? " ⛔" : ""));
            }
        }
        // 法尻の土留めの背の小段(指図 terraceWalls[].toeBench・EDO-0502 第33巡)── 据えた駒の実メッシュから解き、地形を切る(切るだけ・建物と塀の足あとは触らない)。
        //   皮の設計の地盤(Stage3b)と GradeQA が同じ ToeBenches を読む。【硬】天端に土を載せない(差し込んだ端の半駒は根入れ)
        {
            var tnote = new System.Text.StringBuilder(); var toes = ToeBenches(tnote);
            if (toes.Count > 0)
            {
                var keepB = new List<Bounds>(); var wallB = new List<Bounds>(); var rootT = GameObject.Find(GN);
                foreach (var gname in new[] { "Kakoi", "Buildings", "Service_v3", "KachuNagaya_v3", "Ishigaki" })
                { var gt = rootT == null ? null : rootT.transform.Find(gname); if (gt != null) foreach (var mr in gt.GetComponentsInChildren<MeshRenderer>()) if (mr.gameObject.activeInHierarchy) { var bb = mr.bounds; if (gname == "Kakoi") { bb.Expand(new Vector3(2f * (0.3f + EdoBuild.HeightCell()), 0f, 2f * (0.3f + EdoBuild.HeightCell()))); wallB.Add(bb); } else keepB.Add(bb); } }   // 練塀・隅は犬走り 0.3 + 地形の一升(⛔ 外周の石垣は広げない ── 辺24 の背が切れず被りが 6→11)(床の升を切らない ── 第34巡 NW_Hei_5_0 が 0.32 下がった)   // 部材ごとの外接(群の外接は広すぎて法を丸ごと守った ── 第33巡 1182 節点)
                int kept = 0;
                Func<Vector2, float, bool> keep = (q, nw) => { if (KeepToe(keepB, wallB, q, nw)) { kept++; return true; } return false; };
                float cm; Vector2 ca; int cn = EdoBuild.ToeBenchWrite(toes, keep, out cm, out ca);
                AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
                sb.AppendLine("  法尻の背の小段(toeBench): " + toes.Count + " 区間・切った節点 " + cn + "・切りの最大 " + cm.ToString("F2") + "m @(" + ca.x.ToString("F1") + ", " + ca.y.ToString("F1") + ")・建物/塀の足あとで切らなかった節点 " + kept);
            }
            sb.Append(tnote.ToString());
        }
        // 硬い・区域: 駒の実メッシュが区画の外へ出ないか(壁体)
        {
            float worst = 0f; string wn = null;
            foreach (Transform c in grp)
            {
                foreach (var v in EdoBuild.Body(c, 4000))
                { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(Poly, q)) { float d = EdoGeom.DistToPolyEdge(Poly, q); if (d > worst) { worst = d; wn = c.name; } } }
            }
            sb.AppendLine("  区画の外へ出る量(壁体の頂点): " + worst.ToString("F3") + "m" + (worst > 0.005f ? " ⛔ @" + wn : ""));
        }
        // 石段の段石の両端を脇の土留めの面まで伸ばす(袖を持たない石段だけ)── 土留めを据えた後
        sb.Append(ExtendKaidanEndsToWalls(grp));
        // 指図 sideFace の実測(据えた後): 各段の踏面の高さで脇の見え面 − 段の端の線(硬 = 0 ± 0.05)
        sb.Append(MeasureSideFaces(grp));
        // 石段の袖(指図 kaidans[].sode・2026-10-07)── 土留めを据えた後(上端の相手は石段が切った土留めの駒)
        sb.Append(PlaceKaidanSodes(grp));
        // 天端の垣(指図 fenceOnTop)
        sb.Append(PlaceDanKaki(fgrp, grp, wallOf, lineOf, topOf, gapOf));
        if (skipped > 0) sb.AppendLine("  建てない欄 " + skipped + "(line=null)");
        string lg = log.ToString().TrimEnd();
        if (lg.Length > 0) sb.AppendLine("  ── 据えの記録 ──\n" + lg);
        return sb.ToString();
    }


    /// <summary>**法尻の土留めの背の小段**(指図 terraceWalls[].toeBench を持つ欄 ── TW_Nishi_Kado・TW_Higashi_Minami・EDO-0502 第33巡)を、
    /// 据えた駒(Dan の「名_part_」の駒)の実メッシュから解く(型は <see cref="EdoBuild.ToeBenchOf"/>)。数は指図の文から読む(⛔ 読めなければ ★ を刷って取らない)。
    /// 背 = 設計面の高い側。差し込んだ端の判定(天端 + 届く量)と半駒は指図 nozuraEndRule ④の文の値。Stage2b(地形を切る)・Stage3b(皮の設計の地盤)・GradeQA が同じこれを読む。</summary>
    /// <summary>法尻の小段を切るとき守る節点(EDO-0502 第34巡): 建物の部材の外接の中は切らない・練塀と隅は外接を犬走り 0.3 + 地形の一升に広げた中で、
    /// 切った後の高さが塀の最も低い点より下になる節点だけ守る(塀の床の升を下げない ── NW_Hei_5_0 が 0.32 下がった)。塀より低い所の切りは床に触れない。</summary>
    static bool KeepToe(List<Bounds> keepB, List<Bounds> wallB, Vector2 q, float nw)
    {
        foreach (var bb in keepB) if (q.x >= bb.min.x && q.x <= bb.max.x && q.y >= bb.min.z && q.y <= bb.max.z) return true;
        foreach (var bb in wallB) if (q.x >= bb.min.x && q.x <= bb.max.x && q.y >= bb.min.z && q.y <= bb.max.z && nw < bb.min.y) return true;
        return false;
    }

    static List<EdoBuild.ToeBench> ToeBenches(System.Text.StringBuilder note)
    {
        var res = new List<EdoBuild.ToeBench>();
        System.Func<string, string, float> rx = (txt, pat) =>
        {
            var m = System.Text.RegularExpressions.Regex.Match(txt ?? "", pat);
            return m.Success ? float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : float.NaN;
        };
        string er = S(Get(D, "nozuraEndRule"));
        float reach = rx(er, @"天端\s*\+\s*([0-9.]+)\s*に届く"), tail = rx(er, @"半駒\s*[\(（]\s*([0-9.]+)");
        var root = GameObject.Find(GN); var dan = root == null ? null : root.transform.Find("Dan");
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null) continue; string nm = S(Get(w, "name")), part = S(Get(w, "part"));
            Dictionary<string, object> sw = null;
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
            string tb = sw == null ? null : S(Get(sw, "toeBench")); if (string.IsNullOrEmpty(tb)) continue;
            var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
            float drop = rx(tb, @"天端\s*[−\-]\s*([0-9.]+)"), behind = rx(tb, @"控えの後端\s*\+\s*([0-9.]+)"), bf = rx(tb, @"1\s*:\s*([0-9.]+)");
            var miss = new List<string>();
            if (float.IsNaN(drop)) miss.Add("toeBench の天端からの下げ"); if (float.IsNaN(behind)) miss.Add("toeBench の控えの後端からの奥行"); if (float.IsNaN(bf)) miss.Add("toeBench の法");
            if (float.IsNaN(reach)) miss.Add("nozuraEndRule ④の届く量"); if (float.IsNaN(tail)) miss.Add("nozuraEndRule ④の半駒");
            string key = nm + (part != null ? "_" + part : "");
            if (miss.Count > 0) { if (note != null) note.AppendLine("    ★ " + key + ": 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 法尻の小段を取らない"); continue; }
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            var pcs = new List<GameObject>();
            // ⛔ 積み止めの駒(名に "_tome")は数えない ── 小口の面の奥行 1.818 は背の土に埋まる駒で、数えると控えの後端が 1.16→2.76 に伸び、
            //   背の縁の石の帯が積み止めだけを拾って天端を 1.5 低く読み、盛を最大 2.55 切った(第43巡・TW_Nishi_Kado 辺24)
            if (dan != null) foreach (Transform c in dan) if (c.gameObject.activeInHierarchy && c.name.StartsWith(key + "_") && !c.name.Contains("_tome")) pcs.Add(c.gameObject);
            // 区間ごと(折れた線は区間に割る)── 駒は芯の射影が区間の内に入る物
            for (int i = 0; i + 1 < nodes.Count; i++)
            {
                Vector2 a = nodes[i], b = nodes[i + 1]; float L = Vector2.Distance(a, b); if (L < 0.3f) continue;
                Vector2 t = (b - a) / L, nrm = new Vector2(-t.y, t.x), mid = (a + b) * 0.5f;
                float yp = DesignY(mid + nrm * 3f), ym = DesignY(mid - nrm * 3f);
                Vector2 back = (!float.IsNaN(yp) && (float.IsNaN(ym) || yp >= ym)) ? nrm : -nrm;
                var mine = new List<GameObject>();
                foreach (var g in pcs)
                {
                    var c = EdoBuild.RB(g).center; float s = Vector2.Dot(new Vector2(c.x, c.z) - a, t);
                    bool first = i == 0, last = i + 2 == nodes.Count;
                    if ((s >= 0f || first) && (s <= L || last)) mine.Add(g);
                }
                var k = EdoBuild.ToeBenchOf(key + "#" + i, mine, a, b, back, drop, behind, bf, Poly, DesignY, reach, tail, note);
                if (k != null) res.Add(k);
            }
        }
        return res;
    }

    /// <summary>段の土留めの線が長屋の背へ入り込む所の返しと溝(指図 terraceWalls[].return<run> を持つ欄・EDO-0502 第19巡)。</summary>
    public class BackTrench { public string wall, run; public List<Vector2> nodes; public Vector2 stop, far, yard, along; public float off, y; }

    /// <summary>**返しの石垣と溝を解く**(Stage2b の据えと Stage3b の皮の設計の地盤が同じ答えを読む)。背の面・妻は据えた長屋の実メッシュ
    /// (FaceOut・SpecBodySpanAlong)、止める妻 = 帯の縁で地表の高い側、線の切りと返しは <see cref="EdoBuild.ReturnAlongBack"/>、
    /// 溝の高さ = 欄 lo の面(terraces[].y)。一間は柔らかい(ES)。⛔ 座標を書かない ── 毎回測る。</summary>
    static List<BackTrench> BackTrenches(System.Text.StringBuilder sb)
    {
        var res = new List<BackTrench>();
        var rootR = GameObject.Find(GN);
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null) continue; string nm = S(Get(w, "name"));
            var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
            Dictionary<string, object> twD = null;
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (t2 != null && S(Get(t2, "name")) == nm) twD = t2; }
            if (twD == null) continue;
            foreach (var kvR in twD)
            {
                if (!kvR.Key.StartsWith("return") || kvR.Key.Length <= 6) continue;
                var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
                string rn = kvR.Key.Substring(6); int ri = -1;
                for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == rn) ri = k;
                var nbT = rootR == null ? null : rootR.transform.Find("Kakoi/" + rn);
                if (ri < 0) continue;   // return<欄>(returnTop・returnFoot ほか ── 端の返しの欄)は長屋の名でない(第25巡)
                if (nbT == null) { if (sb != null) sb.AppendLine("  " + nm + " × " + rn + ": ⚠ 長屋が無い ── 返さない"); continue; }
                int e = Runs[ri].edge; Vector2 ea = EdgePt(e, 0f), ax = (EdgePt(e, 1f) - ea).normalized, yard = -OutNormal(e);
                float seatY = nbT.position.y;
                float back = EdoBuild.FaceOut(nbT.gameObject, ea, yard, seatY + 0.1f, seatY + 1.2f);
                var sp = EdoBuild.SpecBodySpanAlong(nbT.gameObject, ea, ax); if (float.IsNaN(sp.x)) sp = EdoBuild.BodySpanAlong(nbT.gameObject, ea, ax);
                if (float.IsNaN(back) || float.IsNaN(sp.x)) { if (sb != null) sb.AppendLine("  " + nm + " × " + rn + ": ⚠ 背の面を測れず ── 返さない"); continue; }
                Vector2 b0 = ea + ax * sp.x + yard * back, b1 = ea + ax * sp.y + yard * back;
                float off = ES;   // 一間(柔らかい・指図「長屋の背から一間離して」)
                // 止める妻 = 帯の縁の高い側(門の内の土を受ける側)── 造成の設計の地盤(graded)で測る(地形は溝を切った後で両側が同じに読める)
                var G = Graded;
                float g0 = G.At((b0 + yard * off).x, (b0 + yard * off).y), g1 = G.At((b1 + yard * off).x, (b1 + yard * off).y);
                Vector2 bStop = g0 >= g1 ? b0 : b1, bFar = g0 >= g1 ? b1 : b0;
                Vector2 tFar; string rnote;
                var nn = EdoBuild.ReturnAlongBack(nodes, bStop, bFar, yard, off, out tFar, out rnote);
                if (sb != null) sb.AppendLine("  " + nm + " × " + rn + "(背 " + back.ToString("F2") + "m・妻 s " + sp.x.ToString("F2") + "〜" + sp.y.ToString("F2") + "・止めの妻の設計の地盤 "
                                            + Mathf.Max(g0, g1).ToString("F2") + " / 反対 " + Mathf.Min(g0, g1).ToString("F2") + "): " + rnote);
                if (nn == null) continue;
                string loName = S(Get(w, "lo")); float loY = float.NaN;
                foreach (var o3 in A(D["terraces"]) ?? new List<object>()) { var t3 = O(o3); if (t3 != null && S(Get(t3, "name")) == loName) loY = F(Get(t3, "y")); }
                if (float.IsNaN(loY)) { if (sb != null) sb.AppendLine("    ⚠ 低い側の面 " + (loName ?? "-") + " の高さが無い ── 返さない"); continue; }
                res.Add(new BackTrench { wall = nm, run = rn, nodes = nn, stop = bStop, far = tFar, yard = yard, along = (bFar - bStop).normalized, off = off, y = loY });
            }
        }
        return res;
    }

    /// <summary>点 q が溝(背の面から off の帯・止めの妻から返しの端 + off まで)の中なら溝の高さ、外なら NaN。</summary>
    static float TrenchAt(List<BackTrench> ts, Vector2 q)
    {
        foreach (var t in ts)
        {
            float s = Vector2.Dot(q - t.stop, t.along), d = Vector2.Dot(q - t.stop, t.yard), L = Vector2.Dot(t.far - t.stop, t.along) + t.off;
            if (s >= -0.05f && s <= L && d >= -0.30f && d <= t.off) return t.y;
        }
        return float.NaN;
    }


    /// <summary>**野面の段の土留めの石段の口**(EDO-0502 第57巡・施主裁定 2026-10-08「野面に揃える」)。gaps[].by が石段(K_*)の口ごとに:
    /// ① 石段が sideFace(指図 kaidans[].sideFace)を持てば、脇の返しの天端の線を <see cref="EdoBuild.StairSideCrestLines"/> で解く ──
    ///    足元の面 = 据わった段石の天端(踏面の中ほど・同じ坂の上の石段も)と段の外の設計面、法 = 野面の駒の実測(<see cref="EdoBuild.FaceBatterOf"/>)、
    ///    口の端 = その線と本線の交点(出隅 ── PlaceNozuraNet が隅の駒で継ぐ)、返しの区間は見え面を石段の芯へ名指して nozSegs へ。
    ///    返しの長さ = 口の床が天端に届く所(<see cref="EdoBuild.GapReturnLine"/>・上限 = 石段の奥行と坂の切通しの延長の大きい方)。
    /// ② 無ければ据わった段石の実面で口を詰め(<see cref="EdoBuild.GapFromPieces"/>)、返しは GapReturnLine の線(見え面は口の内)。
    /// 返り値 = 口の道のり [s0, s1] の並び。硬い: sideFace(各段の踏面の高さで見え面 = 端の線)は据えた後に MeasureSideFaces で実測して刷る。
    /// 当たる先: 石段が切る野面の段の土留め(岡部 TW_Kado_Shumen・TW_Kado_Hokuto・TW_Higashi_Tsuyo)。</summary>
    /// <summary>**道の路盤の高さ**(石段の脇の返しの足元・EDO-0502 第58巡)── 坂の縦断(RampProfileAt)が在ればそれ、無ければ皮が描く地表。
    /// ⛔ 設計の地盤 graded で測らない ── graded は切通しの坂を持たず面の高さ 21.0 を返し、返しの駒が H0.30 に選ばれて下が 1.4m 抜けた(第57巡)。</summary>
    static float RoadGround(Vector2 q) { float rp = RampProfileAt(q); return !float.IsNaN(rp) ? rp : SkinGround(q.x, q.y); }

    /// <summary>この巡の sideFace の返しの始まり(本線の上の出隅の点)── 本線の短い残りを捨てずに返しと継ぐ(Stage2b の区間割り)。</summary>
    static List<Vector2> _sideCorner = new List<Vector2>();
    static List<Vector2> StairGaps(string key, Dictionary<string, object> w, List<Vector2> nodes, float top, Transform kaiRoot, List<EdoBuild.NozuraSeg> nozSegs, System.Text.StringBuilder sb)
    {
        var gl = A(Get(w, "gaps")) ?? new List<object>(); var ng = new List<Vector2>(); var seen = new List<Vector2>();
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        for (int gi = 0; gi < gl.Count; gi++)
        {
            var gd = O(gl[gi]); var g = new Vector2(F(Get(gd, "s0")), F(Get(gd, "s1")));
            if (seen.Exists(z => Mathf.Abs(z.x - g.x) < 0.01f && Mathf.Abs(z.y - g.y) < 0.01f)) continue;
            seen.Add(g);
            string by = null;
            foreach (var g2 in gl) { var d2 = O(g2); string b2 = S(Get(d2, "by")); if (b2 != null && b2.StartsWith("K_") && Mathf.Abs(F(Get(d2, "s0")) - g.x) < 0.01f) by = b2; }
            Dictionary<string, object> kd = null;
            foreach (var ko in A(D["kaidans"]) ?? new List<object>()) { var k2 = O(ko); if (k2 != null && S(Get(k2, "name")) == by) kd = k2; }
            if (by == null || kd == null || kaiRoot == null) { ng.Add(g); sb.AppendLine("    口 " + key + " [" + g.x.ToString("F2") + "," + g.y.ToString("F2") + "]: 石段の名が無い ── 紙の口のまま ⚠"); continue; }
            Func<string, List<GameObject>> stones = kn => { var l = new List<GameObject>(); foreach (Transform c in kaiRoot) if (c.gameObject.activeInHierarchy && c.name.StartsWith(kn + "_") && !c.name.Contains("_tsumi")) l.Add(c.gameObject); return l; };
            var pcs = stones(by);
            Vector2 ka2, kb2; KaidanAB(kd, out ka2, out kb2);
            Vector2 ax = (kb2 - ka2).normalized, foot = ka2;
            Vector2 dirL; Vector2 mid = EdoBuild.ArcPoint(nodes, (g.x + g.y) * 0.5f, out dirL);
            float hp = SkinGround(mid.x + ax.x * 3f, mid.y + ax.y * 3f), hm = SkinGround(mid.x - ax.x * 3f, mid.y - ax.y * 3f);
            if (!float.IsNaN(hp) && !float.IsNaN(hm) && hm > hp) { ax = -ax; foot = kb2; }
            float stairDeep = 0f;
            foreach (var pc in pcs) foreach (var v in EdoBuild.Body(pc.transform, 4000)) stairDeep = Mathf.Max(stairDeep, Vector2.Dot(new Vector2(v.x, v.z) - mid, ax));
            float capLen = stairDeep;
            foreach (var g2 in gl)
            {
                string b2 = S(Get(O(g2), "by")); if (b2 == null || Mathf.Abs(F(Get(O(g2), "s0")) - g.x) > 0.01f) continue;
                foreach (var ro in A(Get(D, "ramps")) ?? new List<object>()) { var rd = O(ro); if (rd != null && S(Get(rd, "name")) == b2 && O(Get(rd, "kiritoshi")) != null) capLen = Mathf.Max(capLen, F(Get(O(Get(rd, "kiritoshi")), "lenM"))); }
            }
            string sf = S(Get(kd, "sideFace"));
            if (sf != null)
            {
                // 足元の面: この石段と同じ坂(atRoute)の上の石段の段石の列(踏面の中ほど・広い列は両端)+ 段の外は芯の設計面
                string route = S(Get(kd, "atRoute"));
                var names = new List<string> { by };
                if (route != null) foreach (var ko in A(D["kaidans"]) ?? new List<object>()) { var k2 = O(ko); string n2 = S(Get(k2, "name")); if (k2 != null && n2 != by && S(Get(k2, "atRoute")) == route && S(Get(k2, "sideFace")) != null) names.Add(n2); }
                var surf = new List<Vector2>(); var spans = new List<Vector2>(); float uNose = float.MaxValue;
                foreach (var kn in names)
                {
                    var rows = new Dictionary<string, List<GameObject>>();
                    foreach (var c in stones(kn)) { if (c.name.StartsWith("Sode")) continue; string rk = c.name.Substring(0, c.name.LastIndexOf('_')); if (!rows.ContainsKey(rk)) rows[rk] = new List<GameObject>(); rows[rk].Add(c); }
                    foreach (var kv in rows)
                    {
                        float u0 = float.MaxValue, u1 = float.MinValue, yt = float.MinValue;
                        foreach (var c in kv.Value) { yt = Mathf.Max(yt, EdoBuild.RB(c).max.y); foreach (var v in EdoBuild.Body(c.transform, 4000)) { if (v.y < EdoBuild.RB(c).max.y - 0.05f) continue; float u = Vector2.Dot(new Vector2(v.x, v.z) - foot, ax); u0 = Mathf.Min(u0, u); u1 = Mathf.Max(u1, u); } }
                        if (u0 == float.MaxValue) continue;
                        spans.Add(new Vector2(u0, u1)); uNose = Mathf.Min(uNose, u0);
                        if (u1 - u0 > 0.7f) { surf.Add(new Vector2(u0 + 0.2f, yt)); surf.Add(new Vector2(u1 - 0.05f, yt)); } else surf.Add(new Vector2((u0 + u1) * 0.5f, yt));
                    }
                }
                float uWall = Vector2.Dot(mid - foot, ax);
                float rl = 0f;
                foreach (float se in new[] { g.x, g.y })
                {
                    Vector2 dd; Vector2 pe = EdoBuild.ArcPoint(nodes, se, out dd);
                    Vector2 inw = new Vector2(ax.y, -ax.x); if (Vector2.Dot(inw, mid - pe) < 0f) inw = -inw;
                    float r1; var ln = EdoBuild.GapReturnLine(pe, ax, inw, top, SkinGround, capLen, out r1); if (ln != null) rl = Mathf.Max(rl, r1);
                }
                float uEnd = uWall + Mathf.Max(rl, stairDeep);
                // 同じ坂の上の石段(K_Dan2)も脇の面を受ける ── 返しは受ける石段の最も上の列の奥まで(第57巡: 口の床で止めると K_Dan2 の脇が面なし)
                foreach (var sp in spans) uEnd = Mathf.Max(uEnd, sp.y + 0.3f);
                for (float u = 0f; u <= uEnd + 1e-3f; u += 0.5f)
                {
                    if (spans.Exists(sp => u >= sp.x - 0.3f && u <= sp.y + 0.3f)) continue;
                    var q = foot + ax * u; float gy = RoadGround(q); if (!float.IsNaN(gy)) surf.Add(new Vector2(u, gy));
                }
                var stoneOf = new System.Text.StringBuilder();
                float batter = EdoBuild.FaceBatterOf(EdoAssets.Own.SannoNozura(4.8f, 0f, 0));
                float halfW = (Has(kd, "wKen") ? F(kd["wKen"]) : 1f) * C("ken") * 0.5f;
                if (float.IsNaN(batter)) { ng.Add(g); sb.AppendLine("    ★ 口 " + key + " × " + by + ": 野面の駒の法が測れない ── 紙の口のまま(sideFace を当てない)"); continue; }
                float[] gs; string note;
                var lines = EdoBuild.StairSideCrestLines(nodes, foot, ax, halfW, top, batter, surf, uEnd, 0.02f, out gs, out note);
                if (lines[0] == null || lines[1] == null) { ng.Add(g); sb.AppendLine("    ★ 口 " + key + " × " + by + ": sideFace の線が解けない(" + note + ")── 紙の口のまま"); continue; }
                Vector2 nrm = new Vector2(-ax.y, ax.x);
                // 見え面の足元 = 段石の踏面(その走りの列の天端)── 駒の丈を踏面から測る(⛔ 段の下の地形で測ると丈が足りず踏面の上に口が開いた・第57巡の初手)
                var footOf = new List<Vector3>();   // (u0, u1, 踏面)
                foreach (var kn in names)
                {
                    var rows2 = new Dictionary<string, List<GameObject>>();
                    foreach (var c in stones(kn)) { if (c.name.StartsWith("Sode")) continue; string rk = c.name.Substring(0, c.name.LastIndexOf('_')); if (!rows2.ContainsKey(rk)) rows2[rk] = new List<GameObject>(); rows2[rk].Add(c); }
                    foreach (var kv in rows2)
                    {
                        float u0 = float.MaxValue, u1 = float.MinValue, yt = float.MinValue;
                        foreach (var c in kv.Value) { var rb = EdoBuild.RB(c); yt = Mathf.Max(yt, rb.max.y); foreach (var v in EdoBuild.Body(c.transform, 4000)) { float u = Vector2.Dot(new Vector2(v.x, v.z) - foot, ax); u0 = Mathf.Min(u0, u); u1 = Mathf.Max(u1, u); } }
                        footOf.Add(new Vector3(u0, u1, yt));
                    }
                }
                Vector2 footC = foot, axC = ax;
                Func<float, float, float> footAt = (x, z) =>
                {
                    float u = Vector2.Dot(new Vector2(x, z) - footC, axC); float y = float.NaN;
                    foreach (var f3 in footOf) if (u >= f3.x - 0.05f && u <= f3.y + 0.05f && (float.IsNaN(y) || f3.z < y)) y = f3.z;   // 段鼻の下は低い段
                    return float.IsNaN(y) ? RoadGround(new Vector2(x, z)) : y;
                };
                for (int si = 0; si < 2; si++)
                {
                    Vector2 face = si == 0 ? -nrm : nrm;   // 見え面は石段の芯へ
                    for (int k = 0; k + 1 < lines[si].Count; k++)
                        nozSegs.Add(new EdoBuild.NozuraSeg { name = key + "_Side" + si + "_" + k, a = lines[si][k], b = lines[si][k + 1], crestAt = sl => top, face = face, footAt = footAt });
                    _sideCorner.Add(lines[si][0]);
                }
                // ⭐ 脇の返しの端の延長(指図 TW_Kado_Shumen.sideEnd・普請方 2026-10-09f・第73巡)【硬】── 西の脇の返しを、口の側の始まりから返しと逆の向き
                //   (門の内の縁に沿って)へ、縁の落差(背 1m の設計の地盤 − 前 1.5m の設計の地盤)が 0.3 以下になる所まで延ばす。延ばした区間の天端は
                //   TW_Kado_Sode.sodeSlope と同じ下ろし方(SodeSlopeSegs ── 同じ欄の 2026-10-09c の固有の値は読まない)。当たる先: 欄 sideEnd を持つ段の土留め。
                {
                    string se = null; foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); string n2 = S(Get(t2, "name")); if (n2 != null && key.StartsWith(n2) && S(Get(t2, "sideEnd")) != null) se = S(Get(t2, "sideEnd")); }
                    string sodeTxt = null; foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (S(Get(t2, "name")) == "TW_Kado_Sode") sodeTxt = S(Get(t2, "sodeSlope")); }
                    if (se != null)
                    {
                        var mD = System.Text.RegularExpressions.Regex.Match(se, @"落差が\s*([0-9.]+)\s*以下");
                        bool west = se.Contains("西の脇の返し");
                        if (!mD.Success || sodeTxt == null || !se.Contains("sodeSlope と同じ下ろし方")) sb.AppendLine("    ★ " + key + " sideEnd: 指図から読めない(落差・下ろし方)── 延ばさない");
                        else
                        {
                            float dropMax = float.Parse(mD.Groups[1].Value, inv);
                            int sw = (lines[0][0].x < lines[1][0].x) == west ? 0 : 1;   // 西 = x の小さい側
                            Vector2 p0 = lines[sw][0], dS = (lines[sw][1] - lines[sw][0]).normalized, dE = -dS; Vector2 faceS = sw == 0 ? -nrm : nrm;
                            // 向きは門の内の縁(低い側の面の輪郭の最も近い辺)に沿わせる ── 返しの向きのままだと縁から離れて面へ入り込む
                            { if (_flat == null) _flat = FlatFaces(null); float bdE = float.MaxValue;
                              foreach (var ff in _flat) { if (ff.poly == null || ff.poly.Length < 3) continue; if (!se.Contains(ff.name) && ff.name != "Kadonouchi") continue;
                                for (int k = 0; k < ff.poly.Length; k++) { Vector2 a0 = ff.poly[k], b0 = ff.poly[(k + 1) % ff.poly.Length]; float d0 = EdoBuild.EdgeDistPublic(new[] { a0, b0, a0 }, p0); Vector2 ed = (b0 - a0).normalized; if (Mathf.Abs(Vector2.Dot(ed, dS)) < 0.8f) continue; if (d0 < bdE) { bdE = d0; dE = Vector2.Dot(ed, dS) < 0f ? ed : -ed; } } } }
                            float tStop = float.NaN;
                            // 止めは二つの遅い方: 縁の落差 ≤ dropMax(背 1m − 前 1.5m の設計の地盤)と、sodeSlope の低い端の届き(背の法 +0.15 ≤ 前の地表 +0.20 ── 同じ欄の
                            //   打ち切りの条件。延ばす先で SodeSlopeSegs が 6m 以内に届かず ③ で段を残した第74巡の1回目)。⛔ 届く前に止めない【硬】。
                            bool dropOk = false; float tDrop0 = float.NaN;
                            // 追記 2026-10-09h(上書き): 延長は縁の落差 ≤ dropMax で止め、sodeSlope の打ち切りの条件を当てない【硬】・低い端は坂の駒のまま打ち切り小口を沈める
                            int i9h = se.IndexOf("追記 2026-10-09h"); bool only09h = i9h >= 0 && se.Substring(i9h).Contains("打ち切りの条件");
                            float sinkH = float.NaN, cutH = float.NaN, fillH = float.NaN, alongH = float.NaN;
                            if (i9h >= 0)
                            {
                                string th = se.Substring(i9h);
                                System.Func<string, float> rh = pat => { var mm = System.Text.RegularExpressions.Regex.Match(th, pat); return mm.Success ? float.Parse(mm.Groups[1].Value, inv) : float.NaN; };
                                sinkH = rh(@"小口は\s*([0-9.]+)\s*以上沈め"); cutH = rh(@"切り\s*≤\s*([0-9.]+)"); fillH = rh(@"盛り\s*≤\s*([0-9.]+)"); alongH = rh(@"長手に\s*1\s*/\s*([0-9.]+)");
                                if (float.IsNaN(sinkH) || float.IsNaN(cutH) || float.IsNaN(fillH) || float.IsNaN(alongH)) sb.AppendLine("    ★ " + key + " sideEnd 追記 2026-10-09h: 指図から読めない(沈め・切り・盛り・長手の落とし)");
                            }
                            for (float tt = 0.25f; tt <= 25f; tt += 0.25f)
                            {
                                var q = p0 + dE * tt; float yb = DesignY(q - faceS * 1.0f), yf = DesignY(q + faceS * 1.5f);
                                if (!dropOk && !float.IsNaN(yb) && !float.IsNaN(yf) && yb - yf <= dropMax) dropOk = true;
                                float lnB = DesignY(q - faceS * 1.3f), frG = SkinGround(q.x + faceS.x * 0.5f, q.y + faceS.y * 0.5f);
                                bool reach = !float.IsNaN(lnB) && !float.IsNaN(frG) && lnB + 0.15f <= frG + 0.20f;
                                if (dropOk && float.IsNaN(tDrop0)) tDrop0 = tt;
                                if (dropOk && (only09h || reach)) { tStop = tt; break; }
                            }
                            // 届きが 25m 以内に無ければ縁の落差の止めで延ばす(⚠ 低い端は sodeSlope の ③ ── 指図の二つの止めが食い違う所・普請方へ)
                            if (float.IsNaN(tStop) && !float.IsNaN(tDrop0)) { tStop = tDrop0; sb.AppendLine("    ⚠ " + key + " sideEnd: 縁の落差 ≤ " + dropMax.ToString("F2", inv) + " は " + tDrop0.ToString("F2", inv) + "m だが、sodeSlope の打ち切り(背の法 +0.15 ≤ 前の地表 +0.20)は 25m 延ばしても届かない ── 落差の止めで延ばす(指図の二つの止めの食い違い)"); }
                            if (float.IsNaN(tStop)) sb.AppendLine("    ⚠ " + key + " sideEnd: 25m 延ばしても縁の落差が " + dropMax.ToString("F2", inv) + " 以下にならない ── 延ばさない");
                            else
                            {
                                var extN = new List<Vector2> { p0, p0 + dE * tStop }; var extSegs = new List<EdoBuild.NozuraSeg>();
                                string r0 = SodeSlopeSegs(key + "_SideEnd" + sw, extN, sodeTxt, extSegs, new List<SodeSlopeCheck>(), null, null, true, sinkH);
                                foreach (var es in extSegs) es.face = faceS;
                                nozSegs.AddRange(extSegs);
                                // ⭐ 追記 2026-10-09g【硬】: 延ばした区間の背 = 天端 − dropB の平らな小段を控えの後端 + behindB まで(幅は一間を狙う【柔】)・その先 1:bfB で今の地盤へ
                                //   擦り付け(切りも盛りも ── 石垣と法の間に谷を作らない)・水は 1/drnB で石垣から離す。駒の区間ごと 0.9m に割り、天端の高い端を b にして走りに沿って落とす。
                                int i9g = se.IndexOf("追記 2026-10-09g"); _sideEndBenches.Clear();
                                if (i9g >= 0)
                                {
                                    string tg = se.Substring(i9g);
                                    System.Func<string, float> rg = pat => { var mm = System.Text.RegularExpressions.Regex.Match(tg, pat); return mm.Success ? float.Parse(mm.Groups[1].Value, inv) : float.NaN; };
                                    float dropB = rg(@"天端\s*[−\-]\s*([0-9.]+)\s*の平らな小段"), behindB = rg(@"控えの後端\s*\+\s*([0-9.]+)"), bfB = rg(@"その先は\s*1\s*:\s*([0-9.]+)"), drnB = rg(@"水は\s*1\s*/\s*([0-9.]+)");
                                    bool ken1 = tg.Contains("幅は一間");
                                    float backB = float.NaN; { var vs = EdoBuild.BodyExRoofAt(EdoAssets.Own.SannoNozura(4.8f, 0f, 0), Vector3.zero, 0f); if (vs.Count > 0) { float yT = float.MinValue, zMin = float.MaxValue, zF = float.MinValue; foreach (var v in vs) { yT = Mathf.Max(yT, v.y); zMin = Mathf.Min(zMin, v.z); } foreach (var v in vs) if (v.y >= yT - 0.15f) zF = Mathf.Max(zF, v.z); backB = zF - zMin; } }
                                    if (float.IsNaN(dropB) || float.IsNaN(behindB) || float.IsNaN(bfB) || float.IsNaN(drnB) || float.IsNaN(backB)) sb.AppendLine("    ★ " + key + " sideEnd 追記 2026-10-09g: 指図か駒の控えが読めない ── 背の小段を描かない");
                                    else
                                    {
                                        float wB = Mathf.Max(ken1 ? C("ken") : 0f, backB + behindB);
                                        foreach (var es in extSegs)
                                        {
                                            float L = Vector2.Distance(es.a, es.b); int nC = Mathf.Max(1, Mathf.CeilToInt(L / 0.9f)); Vector2 td = (es.b - es.a) / Mathf.Max(L, 1e-4f);
                                            for (int ci = 0; ci < nC; ci++)
                                            {
                                                float s0 = L * ci / nC, s1 = L * (ci + 1) / nC; float c0 = es.crestAt(s0), c1 = es.crestAt(s1); if (float.IsNaN(c0) || float.IsNaN(c1)) continue;
                                                Vector2 pa = es.a + td * s0, pb = es.a + td * s1; if (c0 > c1) { var tq = pa; pa = pb; pb = tq; float tc = c0; c0 = c1; c1 = tc; }
                                                _sideEndBenches.Add(new EdoBuild.BackBench { name = key + "_SideEnd_back" + _sideEndBenches.Count, a = pa, b = pb, back = -faceS, top = c1, drop = dropB, w = wB, drain = 1f / drnB,
                                                    drainAlong = Mathf.Max((c1 - c0) / Mathf.Max(s1 - s0, 1e-3f), float.IsNaN(alongH) ? 0f : 1f / alongH), bf = bfB,
                                                    maxFill = float.IsNaN(fillH) ? 99f : fillH, maxCut = float.IsNaN(cutH) ? 99f : cutH, parcel = Poly, baseAt = DesignY });
                                            }
                                        }
                                        sb.AppendLine("    延長の背の小段(追記 2026-10-09g): 天端 −" + dropB.ToString("F2", inv) + "・奥行 " + wB.ToString("F2", inv) + "(控えの後端 " + backB.ToString("F2", inv) + " + " + behindB.ToString("F2", inv) + (ken1 ? "・一間を狙う" : "") + ")・1:" + bfB.ToString("0.0", inv) + "・水 1/" + drnB.ToString("F0", inv) + " ── 区間 " + _sideEndBenches.Count + (float.IsNaN(cutH) ? "(⚠ 盛り・切りの上限は欄に無い ── 上限なし)" : "・切り ≤" + cutH.ToString("F2", inv) + "・盛り ≤" + fillH.ToString("F2", inv) + "・長手 1/" + alongH.ToString("F0", inv)));
                                    }
                                }
                                sb.AppendLine("    脇の返しの端の延長 " + key + "_SideEnd" + sw + "(sideEnd): 始まり (" + p0.x.ToString("F1", inv) + ", " + p0.y.ToString("F1", inv) + ") から縁に沿って " + tStop.ToString("F2", inv) + "m で落差 ≤ " + dropMax.ToString("F2", inv) + "・駒の区間 " + extSegs.Count);
                                sb.Append(r0);
                            }
                        }
                    }
                }
                var g1 = new Vector2(Mathf.Min(gs[0], gs[1]), Mathf.Max(gs[0], gs[1])); ng.Add(g1);
                // 一段目の段鼻は本線の法尻より前へ出さない【硬】── 本線の法尻 = 天端の線から低い側へ 法 ×(天端 − 足元の面)
                float uToe = uWall - batter * (top - F(kd["yBot"]));
                sb.AppendLine("    口 " + key + " × " + string.Join("・", names.ToArray()) + "(sideFace): 半幅 " + halfW.ToString("F3") + "・法 1:" + batter.ToString("F3") + "・口 [" + g1.x.ToString("F2") + "," + g1.y.ToString("F2") + "](紙 [" + g.x.ToString("F2") + "," + g.y.ToString("F2") + "])・返しの長さ " + (uEnd - uWall).ToString("F2") + "・" + note
                            + "・一段目の段鼻 − 本線の法尻 " + (uToe - uNose).ToString("+0.00;-0.00") + "m(正 = 法尻より前" + (uToe - uNose > 0.005f ? " ⛔" : " ⭕") + ")");
                continue;
            }
            string gnote; var gm = EdoBuild.GapFromPieces(nodes, g, pcs, 1.0f, out gnote);
            var gg = new Vector2(Mathf.Max(g.x, gm.x), Mathf.Min(g.y, gm.y)); ng.Add(gg);
            sb.AppendLine("    口 " + key + " × " + by + ": " + gnote + " ⇒ 口 [" + gg.x.ToString("F2") + "," + gg.y.ToString("F2") + "]");
            int ri = 0;
            foreach (float se in new[] { gg.x, gg.y })
            {
                Vector2 dd; Vector2 pe = EdoBuild.ArcPoint(nodes, se, out dd);
                Vector2 inw = new Vector2(ax.y, -ax.x); if (Vector2.Dot(inw, mid - pe) < 0f) inw = -inw;
                float rl; var line = EdoBuild.GapReturnLine(pe, ax, inw, top, SkinGround, capLen, out rl);
                sb.AppendLine("      返し @s=" + se.ToString("F2") + ": " + (line == null ? "要らない(口の床が天端に届く)" : "長さ " + rl.ToString("F2") + "m(上限 " + capLen.ToString("F2") + ")"));
                if (line != null) nozSegs.Add(new EdoBuild.NozuraSeg { name = key + "_Kaeshi" + (ri++) + "_0", a = line[0], b = line[1], crestAt = sl => top, face = inw });
            }
        }
        return ng;
    }

    /// <summary>両端の延長(EndExtensions の答え)── 端 pe から台の石垣の面 pf まで・低い側 lowD。</summary>
    public class EndExt { public string name; public Vector2 pe, pf, lowD; public float len; }

    /// <summary>**段の土留めの両端の延長の線**(指図 terraceWalls[].ends・EDO-0502 第20巡・第57巡に城の石垣の枝から切り出し ── 野面の枝も同じ線を読む)。
    /// 低い側の面(欄 lo の terraces[].poly)の縁が線の端から折れて続くなら、その縁に沿って台の道の側の石垣(Ishigaki の駒)の実面まで。
    /// 面は実メッシュで測る(殻の駒 ⇒ 縁の線の脇 1m に入る頂点の最も手前)。⛔ 長さを決め打ちしない。<paramref name="partners"/> へ相手の駒を足す(null 可)。
    /// 硬い/柔らかい: どちらでもない(読みと実測)。当たる先: ends を持つ段の土留め(岡部 TW_Higashi_Tsuyo)。</summary>
    static List<EndExt> EndExtensions(string nm, Dictionary<string, object> w, List<Vector2> nodes, float top, string key, System.Text.StringBuilder sb, List<GameObject> partners)
    {
        var res = new List<EndExt>();
        Dictionary<string, object> twE = null;
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (t2 != null && S(Get(t2, "name")) == nm) twE = t2; }
        string loN = S(Get(w, "lo"));
        if (twE == null || Get(twE, "ends") == null || loN == null) return res;
        if (_flat == null) _flat = FlatFaces(null);
        var lf = _flat.Find(f0 => f0.name == loN);
        var igE = GameObject.Find(GN) == null ? null : GameObject.Find(GN).transform.Find("Ishigaki");
        if (lf.poly == null || igE == null) { sb.AppendLine("    両端の延長 " + key + ": ⚠ 低い側の面 " + loN + " か台の石垣が無い ── 延ばさない"); return res; }
        for (int ei = 0; ei < 2; ei++)
        {
            Vector2 pe = ei == 0 ? nodes[0] : nodes[nodes.Count - 1];
            int vi = 0; float bd = float.MaxValue; for (int k = 0; k < lf.poly.Length; k++) { float dd = Vector2.Distance(lf.poly[k], pe); if (dd < bd) { bd = dd; vi = k; } }
            if (bd > 0.5f) { sb.AppendLine("    両端の延長 " + key + " 端" + ei + ": 低い側の面の角が端から " + bd.ToString("F2") + "m ── 延ばさない"); continue; }
            Vector2 runD = (nodes[nodes.Count - 1] - nodes[0]).normalized;
            Vector2 c1 = lf.poly[(vi + 1) % lf.poly.Length] - lf.poly[vi], c2 = lf.poly[(vi - 1 + lf.poly.Length) % lf.poly.Length] - lf.poly[vi];
            Vector2 ed = Mathf.Abs(Vector2.Dot(c1.normalized, runD)) < Mathf.Abs(Vector2.Dot(c2.normalized, runD)) ? c1.normalized : c2.normalized;
            Vector2 en = new Vector2(-ed.y, ed.x);
            float hit = float.NaN; var near = new List<GameObject>();
            foreach (Transform c in igE)
            {
                if (!c.gameObject.activeInHierarchy) continue; var rb = EdoBuild.RB(c.gameObject); if (Vector2.Distance(new Vector2(rb.center.x, rb.center.z), pe) > 12f) continue;
                foreach (var v in EdoBuild.Body(c, 4000))
                {
                    // 相手の面は天端の帯(天端 −0.6〜+0.1)で測る ── 法の面の足で測ると上で口が開いた(第57巡: 小口の隙 1.5〜1.7m)。下はめり込み(埋めて隠す)
                    if (!float.IsNaN(top) && (v.y < top - 0.6f || v.y > top + 0.1f)) continue;
                    Vector2 r0 = new Vector2(v.x, v.z) - pe; if (Mathf.Abs(Vector2.Dot(r0, en)) > 1.0f) continue;
                    float u = Vector2.Dot(r0, ed); if (u > 0.3f && u < 12f && (float.IsNaN(hit) || u < hit)) { hit = u; }
                }
                near.Add(c.gameObject);
            }
            if (float.IsNaN(hit)) { sb.AppendLine("    両端の延長 " + key + " 端" + ei + ": 縁の先に台の石垣が無い ── 延ばさない"); continue; }
            Vector2 pf = pe + ed * hit; Vector2 inL = (Vector2)lf.poly[vi] + ed * (hit * 0.5f);
            Vector2 ctr = Vector2.zero; foreach (var q0 in lf.poly) ctr += q0; ctr /= lf.poly.Length;
            Vector2 lowD = Vector2.Dot(ctr - inL, en) >= 0f ? en : -en;   // 低い側 = 面の内(溜りの側)
            if (partners != null) foreach (var g in near) { var rb = EdoBuild.RB(g); if (Vector2.Distance(new Vector2(rb.center.x, rb.center.z), pf) < 4f) partners.Add(g); }
            res.Add(new EndExt { name = key + "_End" + ei, pe = pe, pf = pf, lowD = lowD, len = hit });
            sb.AppendLine("    両端の延長 " + key + "_End" + ei + ": 低い側の面 " + loN + " の縁に沿って台の石垣の面まで " + hit.ToString("F2") + "m");
        }
        return res;
    }

    /// <summary>端の返し(EndDecisions の答え)── 妻の線の点 pg(出隅)から背の線の点 pb まで。back = 返しの背(長屋の溝と逆の側)。</summary>
    public class EndReturn { public int end; public Vector2 pg, pb, back; public string nagaya; }

    /// <summary>**段の土留めの両端の決め**(指図 terraceWalls[].ends・EDO-0502 第20巡 TW_Minami_Koshi)。端ごとに、線を延ばして落差(天端 − 低い側の地表)が
    /// 0.6 未満になる所があればそこまで延ばして土羽で止める(nodes に足す)。その前に端の側の長屋の妻の線に届けば、妻の線まで延ばし(nodes に足す・出隅)、
    /// そこから長屋の側へ返して背の線で止める返しを rets に返す(長屋の背から一間の内に土を入れない)。落差・妻・背は実測(SkinGround・札の躯体)。
    /// 0.6 は指図(stop・ends)の値。lo の無い欄(腰石垣)だけ。</summary>
    static void EndDecisions(string nm, Dictionary<string, object> w, List<Vector2> nodes, List<float> tops, System.Text.StringBuilder sb, out List<EndReturn> rets)
    {
        rets = new List<EndReturn>();
        Dictionary<string, object> twK = null;
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (t2 != null && S(Get(t2, "name")) == nm) twK = t2; }
        if (twK == null || Get(twK, "ends") == null || S(Get(w, "lo")) != null || nodes.Count < 2) return;
        var kakK = GameObject.Find(GN) == null ? null : GameObject.Find(GN).transform.Find("Kakoi");
        for (int ei = 0; ei < 2 && kakK != null; ei++)
        {
            Vector2 pe = ei == 0 ? nodes[0] : nodes[nodes.Count - 1], pn = ei == 0 ? nodes[1] : nodes[nodes.Count - 2];
            Vector2 dE = (pe - pn).normalized, nL = new Vector2(dE.y, -dE.x);
            float yT = tops[ei == 0 ? 0 : tops.Count - 1];
            float gp = SkinGround(pe.x + nL.x * 2f, pe.y + nL.y * 2f), gm = SkinGround(pe.x - nL.x * 2f, pe.y - nL.y * 2f);
            Vector2 lowN = gp < gm ? nL : -nL;
            float tG = float.NaN, backD = float.NaN; Vector2 eaG = Vector2.zero, yardG = Vector2.zero; string nagN = null;
            foreach (var r in Runs)
            {
                if (!r.Nagaya) continue; var tN = kakK.Find(r.name); if (tN == null) continue;
                Vector2 ea = EdgePt(r.edge, 0f), ax = (EdgePt(r.edge, 1f) - ea).normalized, yard = -OutNormal(r.edge);
                var sp = EdoBuild.SpecBodySpanAlong(tN.gameObject, ea, ax); if (float.IsNaN(sp.x)) continue;
                float sE = Vector2.Dot(pe - ea, ax), dIn = Vector2.Dot(pe - ea, yard);
                if (sE < sp.x - 0.01f || sE > sp.y + 0.01f || dIn < 0f || dIn > 12f || Vector2.Dot(lowN, -yard) < 0.3f) continue;
                float da = Vector2.Dot(dE, ax); if (Mathf.Abs(da) < 0.2f) continue;
                float sG = da > 0f ? sp.y : sp.x; tG = (sG - sE) / da;
                float seatY = tN.position.y; backD = EdoBuild.FaceOut(tN.gameObject, ea, yard, seatY + 0.1f, seatY + 1.2f);
                eaG = ea; yardG = yard; nagN = r.name; break;
            }
            float tMax = float.IsNaN(tG) ? 12f : Mathf.Max(0f, tG);
            float tStop = float.NaN;
            for (float tt = 0f; tt <= tMax + 1e-3f; tt += 0.25f)
            { var q = pe + dE * tt + lowN * 2f; float g = SkinGround(q.x, q.y); if (!float.IsNaN(g) && yT - g < 0.6f) { tStop = tt; break; } }
            if (!float.IsNaN(tStop))
            {
                Vector2 pz = pe + dE * tStop;
                if (tStop > 0.01f) { if (ei == 0) { nodes.Insert(0, pz); tops.Insert(0, yT); } else { nodes.Add(pz); tops.Add(yT); } }
                if (sb != null) sb.AppendLine("    両端の決め " + nm + " 端" + ei + ": 延ばして落差 0.6 未満で止める(土羽)── 延長 " + tStop.ToString("F2") + "m");
            }
            else if (nagN != null && !float.IsNaN(backD))
            {
                Vector2 pg = pe + dE * Mathf.Max(0f, tG);
                float dG = Vector2.Dot(pg - eaG, yardG); Vector2 pb = pg - yardG * (dG - backD);
                // 延長は端の区間と一直線(dE = 端の外向き)── 節点を足さず端の節点を動かす(第32巡: 0.31m の区間が < 0.5 で駒を据えず、主と返しの間が切れていた)
                if (tG > 0.01f) { if (ei == 0) nodes[0] = pg; else nodes[nodes.Count - 1] = pg; }
                rets.Add(new EndReturn { end = ei, pg = pg, pb = pb, back = dE, nagaya = nagN });
                if (sb != null) sb.AppendLine("    両端の決め " + nm + " 端" + ei + ": 妻の線まで落差 0.6 未満にならない ── " + nagN + " の妻の線で長屋の側へ返す(延長 " + Mathf.Max(0f, tG).ToString("F2") + "m・返し " + (dG - backD).ToString("F2") + "m で背の線に止める)");
            }
            else if (sb != null) sb.AppendLine("    両端の決め " + nm + " 端" + ei + ": ⚠ 12m 延ばしても落差 0.6 未満にならず端の側の長屋も無い ── 延ばさない");
        }
    }

    /// <summary>天端の垣を、指図 terraceWalls[].fenceOnTop の型で据える(置き方は <see cref="EdoBuild.PlaceCrestFence"/>)。
    /// 型 = kaku の「→」の後の最初の名(建仁寺垣 / 四つ目垣 / 木柵)。⚠ 丈は指図に無い ── 焼けた丈で建てて報告する。
    /// 置く線 = 天端の前の縁から高い側へ、その土留めの駒の**天端の控えの半分**(実メッシュ・<see cref="EdoBuild.CrestToBack"/>)。
    /// 口(gaps)は空ける。at が二本を名指す欄(TW_Higashi_Hokuto・TW_Higashi_Tsuyo)は両方へ。</summary>
    static string PlaceDanKaki(Transform fgrp, Transform walls, Dictionary<string, Dictionary<string, object>> wallOf,
                               Dictionary<string, List<Vector2>> lineOf, Dictionary<string, float> topOf, Dictionary<string, List<Vector2>> gapOf)
    {
        var sb = new System.Text.StringBuilder();
        var done = new HashSet<string>();
        foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>())
        {
            var tw = O(o); if (tw == null) continue;
            var fo = O(Get(tw, "fenceOnTop")); if (fo == null) continue;
            string kaku = S(Get(fo, "kaku")) ?? "", at = S(Get(fo, "at")) ?? "";
            string body = kaku.Contains("→") ? kaku.Substring(kaku.IndexOf('→') + 1) : kaku;
            int iK = body.IndexOf("建仁寺垣"), iY = body.IndexOf("四つ目垣"), iM = body.IndexOf("木柵");
            string type = null; int best = int.MaxValue;
            if (iK >= 0 && iK < best) { best = iK; type = "建仁寺垣"; }
            if (iY >= 0 && iY < best) { best = iY; type = "四つ目垣"; }
            if (iM >= 0 && iM < best) { best = iM; type = "四つ目垣"; }   // 「木柵か四つ目垣」── 在庫に天端の木柵の駒が無いので四つ目垣(⚠ 報告)
            if (type == null) { sb.AppendLine("  天端の垣 " + S(Get(tw, "name")) + ": 型が読めない(" + kaku + ")── 建てない"); continue; }
            float h = type == "建仁寺垣" ? 1.5f : 1.2f;
            string span = type == "建仁寺垣" ? EdoAssets.Own.KenninjiGaki(h) : EdoAssets.Own.YotsumeGaki(h);
            string post = type == "建仁寺垣" ? EdoAssets.Own.KenninjiGakiPost(h) : EdoAssets.Own.YotsumeGakiPost(h);
            foreach (var key in new List<string>(lineOf.Keys))
            {
                string wn = S(Get(wallOf[key], "name"));
                if (!at.Contains(wn) || done.Contains(key)) continue;
                done.Add(key);
                // その土留めの駒(群の子で名が key で始まる)
                var pcs = new List<GameObject>(); foreach (Transform c in walls) if (c.name.StartsWith(key + "_") || c.name.StartsWith(key + "#")) pcs.Add(c.gameObject);
                var gaps = new List<Vector2>();
                if (gapOf != null && gapOf.ContainsKey(key)) gaps.AddRange(gapOf[key]);   // 解いた口(石段の実面)
                else foreach (var g in A(Get(wallOf[key], "gaps")) ?? new List<object>()) { var gd = O(g); gaps.Add(new Vector2(F(Get(gd, "s0")), F(Get(gd, "s1")))); }
                float fl; int nPost; string note;
                int n = EdoBuild.PlaceCrestFence(span, post, lineOf[key], gaps, pcs, walls, fgrp, "Kaki_" + key, out fl, out nPost, out note);
                sb.AppendLine("  天端の垣 " + key + ": " + type + "(丈 " + h.ToString("0.0") + " ⚠ 指図に丈が無い・焼けた丈)" + n + " 間・親柱 " + nPost
                            + "・足の当たりの高低差 最悪 " + (float.IsNaN(fl) ? "-" : fl.ToString("+0.000;-0.000") + "m") + (note.Length > 0 ? "・" + note : "")
                            + (kaku.Contains("木柵") ? "(⚠ 「木柵か四つ目垣」── 在庫に天端の木柵の駒が無く四つ目垣)" : "")
                            + (kaku.Contains("低い土塀") ? "(⚠ 「建仁寺垣か低い土塀」── 先の名の建仁寺垣)" : ""));
            }
        }
        return sb.ToString();
    }

    [MenuItem("Edo/岡部筑前守上屋敷/3 主郭(棟・廊下・附属屋・井戸・結界・石段)")]
    public static void Stage3Menu() { Debug.Log("[Okabe] " + Stage3_Shukaku()); }

    /// <summary>**袖の坂の硬い検めを皮の後に測り直す**(指図 sodeSlope「天端と背の地盤の差 ≤ x」【硬】・EDO-0502 第45巡)。Stage2b の検めは据えた直後に
    /// <see cref="SkinGround"/>(前の巡の皮)で測るので、背の小段を描き直した巡は古い皮を読む ⇒ Stage3b(皮)の後にこれを流す。測りは Stage2b と同じ
    /// (線の 0.25m おき・天端 = 線から背へ天端の奥行の帯・走りの ±0.15 の駒の頂点の最高・背 = 奥行 + 0.1 の描かれた地表)。読むだけ(駒も地形も触らない)。
    /// 当たる先: sodeSlope を持つ袖(岡部 TW_Kado_Sode)。</summary>
    public static string Stage3c_SodeSlopeCheck()
    {
        var sb = new System.Text.StringBuilder();
        var root = GameObject.Find(GN); var dan = root == null ? null : root.transform.Find("Dan");
        if (dan == null) return "★ Dan の群が無い";
        var dg = EdoBuild.Drawn();   // 背の地盤 = 描かれた地表(皮の在る所は皮・無ければ地形)── ⛔ SkinGround(設計面と地形の低い方)は背の小段の盛りを読まない
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null) continue; string nm = S(Get(w, "name"));
            Dictionary<string, object> sw = null;
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
            string ssl = sw == null ? null : S(Get(sw, "sodeSlope")); var ln = A(Get(w, "line")); if (ssl == null || ln == null || ln.Count < 2) continue;
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            var chk = new List<SodeSlopeCheck>(); SodeSlopeSegs(nm, nodes, ssl, new List<EdoBuild.NozuraSeg>(), chk);
            foreach (var ck in chk)
            {
                var pcs = new List<Vector3>(); foreach (Transform c in dan) if (c.gameObject.activeInHierarchy && c.name.StartsWith(ck.key + "_")) pcs.AddRange(EdoBuild.Body(c, 999999));
                float worst = float.MinValue; Vector2 wAt = Vector2.zero; float wC = 0f, wB = 0f; int nOver = 0, nPt = 0; var over = new List<string>();
                for (int i = 0; i < ck.line.Count; i++)
                {
                    Vector2 p = ck.line[i], n = ck.back[i], t = i + 1 < ck.line.Count ? (ck.line[i + 1] - p).normalized : (p - ck.line[i - 1]).normalized;
                    float top = float.MinValue; foreach (var v in pcs) { Vector2 r = new Vector2(v.x, v.z) - p; float u = Vector2.Dot(r, n); if (u >= 0f && u <= ck.depth && Mathf.Abs(Vector2.Dot(r, t)) < 0.15f) top = Mathf.Max(top, v.y); }
                    if (top == float.MinValue) continue;
                    Vector2 q = p + n * (ck.depth + 0.1f); float bg = dg.At(q.x, q.y); if (float.IsNaN(bg)) continue;
                    nPt++; float d = top - bg; if (d > ck.maxDiff + 1e-3f) { nOver++; over.Add("(" + p.x.ToString("F1") + ", " + p.y.ToString("F1") + ") " + d.ToString("+0.00")); }
                    if (d > worst) { worst = d; wAt = p; wC = top; wB = bg; }
                }
                sb.AppendLine("袖の坂 " + ck.key + " の天端と背の地盤の差(硬 ≤ " + ck.maxDiff.ToString("F2") + "・皮の後・描かれた地表): 最悪 " + (nPt == 0 ? "-" : worst.ToString("+0.00;-0.00")) + "m @(" + wAt.x.ToString("F1") + ", " + wAt.y.ToString("F1") + ")(天端 " + wC.ToString("F2") + "・背 " + wB.ToString("F2") + ")・超え " + nOver + "/" + nPt + " 点" + (nOver > 0 ? " ⛔ " + string.Join(" / ", over.ToArray()) : " ⭕"));
            }
        }
        return sb.ToString();
    }

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
        sb.AppendLine(PlaceTakegaki(wait));
        sb.AppendLine("石段: 2b(段の土留め)で先に据えた ── 口の端を石段の実面で決めるため(EDO-0502 第8巡)");
        sb.AppendLine(PlaceSando(wait));
        sb.AppendLine("── 据えなかったもの(部材待ち・欄待ち)" + wait.Count + " 件 ──");
        foreach (var w in wait) sb.AppendLine("  ★ " + w);
        return sb.ToString();
    }

    // =====================================================================
    // Stage3b — 縁の皮(EDO-0502 第5巡)
    //   ⭐ 段の石垣の駒は線から見え面の足 −0.75・天端の背 +1.40 の幅 2.15m しかなく、2m 格子の地形では足元を描けない ──
    //   上の面の節点が線の近くに落ちると、下の節点まで一次で描かれて足の前が最大 1.77m 盛り上がる(造成では消えない)。
    //   その升だけ地形に穴を開け、0.25m の皮で描く(EdoBuild.CutEdgeSkin・山王 Stage9 と同じ型)。皮の材質は地形の材質の写しに
    //   地形のスプラットを結わえた物で、塗り(Stage4 PaintSplat)を後から変えても同じ見えになる。
    //   硬い(許容0): 皮が駒の天端に被らない・皮と駒の間に隙が無い(報告 coverN / gapN)。⛔ 高さ(heightmap)は動かさない。
    //   ⚠ 造成(1)・据え直し(2・2b・3)の後は皮が古い ── 1 は冒頭で皮を外すので、流したら必ずこれを 3 の後に流し直す。
    //   当たる先: 段の石垣・土留め(算出物 terraceWalls)を持つ全邸 ── いまは山王社(Stage9)と岡部(ここ)。
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/3b 縁の皮(段の土留めの足元の升に穴を開けて皮で描く)")]
    public static void Stage3bMenu() { Debug.Log("[Okabe] " + Stage3b_Hifu()); }

    public static string Stage3b_Hifu()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder("縁の皮:\n");
        float tol = ImplTol("gradeTol", float.NaN);
        if (float.IsNaN(tol)) return sb + "  ⛔ 算出物 checks.gradeTol が無い ── 皮を起こさない(既定値で埋めない)";
        var grp = Group("EdgeSkin");
        int filled = EdoBuild.ClearEdgeSkins(grp);
        // 部材 = 段の土留め(Dan の駒)+ その口を切って上る石段(駒の外形から 2m 以内の段)
        var parts = new List<GameObject>(); var band = new List<GameObject>();
        var danB = new List<Bounds>();
        foreach (Transform c in Group("Dan")) if (c.gameObject.activeInHierarchy) { parts.Add(c.gameObject); band.Add(c.gameObject); danB.Add(EdoBuild.RB(c.gameObject)); }
        int stairN = 0, igN = 0, igOut = 0;
        var root = GameObject.Find(GN); var kai = root == null ? null : root.transform.Find("Fuzoku/Kaidan");
        // ⭐ 外周の石垣(Ishigaki)の駒のうち段の土留めの駒に接する物(外接 1m 内)も部材として渡す(2026-10-04 EDO-0502 第10巡):
        //   皮は渡された駒しか知らない ── 段の土留め 辺24 の穴の升が外周の基壇の石垣 IG_S_Hei_21 の見え面に掛かり、皮が設計の地盤
        //   (法で 7.6 → 11)を石垣の見え面の上に描いて、2m おきの土の三角(最大 +2.33m)を立てた。天端の帯で篩う(見え面の前へ皮を出さない)。
        //   当たる先: 段の土留めと外周の石垣が取り合う所(岡部の西の辺24・南の辺)。
        var ig = root == null ? null : root.transform.Find("Ishigaki");
        if (ig != null)
            foreach (Transform c in ig)
            {
                if (!c.gameObject.activeInHierarchy) continue;
                var b = EdoBuild.RB(c.gameObject); if (b.size == Vector3.zero) continue; b.Expand(1f); bool near = false;
                foreach (var db in danB) if (db.Intersects(b)) { near = true; break; }
                // ⭐ 区画の外の足元を 2m 格子が描けない外周の石垣も渡す(EdoBuild.OutsideFootExcess・2026-10-06 EDO-0502 第29巡):
                //   見え面は区画の線の外へ出て、線の内の節点(台の天端の側 16.4)から線の外の節点(12.7)まで一次で描かれ、
                //   東の長屋の台(IG_N40_2・N41)の見え面の前に高さ最大 2.9m の土の楔が鋸の歯に立った。許しは皮の描きの許し(0.10)。
                Vector2 fa;
                if (!near && EdoBuild.OutsideFootExcess(c.gameObject, Poly, EdoBuild.BaseDem(), out fa) > 0.10f) { near = true; igOut++; }
                if (near) { parts.Add(c.gameObject); band.Add(c.gameObject); igN++; }
            }
        if (kai != null)
            foreach (var r in kai.GetComponentsInChildren<MeshRenderer>())
            {
                var b = r.bounds; b.Expand(4f); bool near = false;
                foreach (var db in danB) if (db.Intersects(b)) { near = true; break; }
                if (near) { parts.Add(r.gameObject); stairN++; }
            }
        var faces = FlatFaces(sb);
        // 面の外 = 算出物 graded(法面を含む設計の地盤)。駒の下に落ちた節点は造成前の地盤(base_dem)で引く。区画の外は今の地形
        var G = Graded; var ok = new bool[G.h.Length]; for (int i = 0; i < ok.Length; i++) ok[i] = !float.IsNaN(G.h[i]);
        // ⭐ 坂の路盤(GradeRamps が造成の後に均す ramps[])は算出物 graded に入っていない ── 皮が graded のまま描くと坂の上に元の面の
        //   高さ(表の坂で 21.0)の土を被せ、返しの石垣と石段の奥を埋める(EDO-0502 第8巡)。坂の帯(芯から 幅/2 + 坂の高低差 × 切の法)の
        //   中は、GradeRamps が均した今の地形を設計の地盤とする。
        var gh = RampPatchedDesign(G, sb);
        float dx0 = G.x0, dz0 = G.z0, dstep = G.step; int dnx = G.nx, dnz = G.nz;
        // ⭐ 袖の背の小段の裏込め(Stage2b が地形へ盛る・指図 backfill)も設計の地盤へ ── 同じ式(EdoBuild.BackBenchAt)。
        //   小段の幅 1間 は算出物の 1m 格子では節点が 1 列しか乗らず、皮が部材の外の節点から引くと小段が法へ薄まる
        //   (第13巡: 1m で天端と背の地盤の差 最大 0.43・0.5m に割っても 0.43 > 硬い 0.30)── 皮の格子 0.25m まで割って(一次の面は割っても同じ)小段を節点で持たせる
        {
            var benches = new List<EdoBuild.BackBench>(); foreach (var kv in SodeBenches(null)) foreach (var bk in kv.Value) benches.Add(bk.Value);
            if (benches.Count > 0)
            {
                const int R = 4;   // 皮の格子(0.25m)まで割る
                int nx2 = (G.nx - 1) * R + 1, nz2 = (G.nz - 1) * R + 1; var h2 = new float[nx2 * nz2]; var ok2 = new bool[h2.Length]; int nb = 0;
                for (int j = 0; j < nz2; j++)
                    for (int i = 0; i < nx2; i++)
                    {
                        int i0 = Mathf.Min(i / R, G.nx - 2), j0 = Mathf.Min(j / R, G.nz - 2); float fx = (i - i0 * R) / (float)R, fz = (j - j0 * R) / (float)R;
                        float a = gh[j0 * G.nx + i0], b = gh[j0 * G.nx + i0 + 1], c = gh[(j0 + 1) * G.nx + i0], d = gh[(j0 + 1) * G.nx + i0 + 1];
                        float v = (fx < 1e-4f && fz < 1e-4f) ? a : Mathf.Lerp(Mathf.Lerp(a, b, fx), Mathf.Lerp(c, d, fx), fz);   // 一次の面は割っても同じ
                        int k = j * nx2 + i; h2[k] = v; ok2[k] = !float.IsNaN(v);
                        if (!ok2[k]) continue;
                        var q = new Vector2(G.x0 + i * G.step / R, G.z0 + j * G.step / R);
                        float nw = EdoBuild.BackBenchesAt(benches, q, v);
                        if (Mathf.Abs(nw - v) > 1e-4f) { h2[k] = nw; nb++; }
                    }
                gh = h2; ok = ok2; dstep = G.step / R; dnx = nx2; dnz = nz2;
                sb.AppendLine("  袖の背の小段の裏込めを設計の地盤へ写した節点 " + nb + "(設計の格子を " + dstep.ToString("F2") + "m に割って)");
            }
        }
        // ⭐ 坂の路盤の帯(芯から幅/2)の中は、坂の縦断(RampAxis = GradeRamps と同じ節点)を皮の格子で引く(2026-10-07 EDO-0502 施主指摘 B):
        //   今の地形(2m 格子)を写すだけだと、石段の上がり口の段石の背(天端 −0.02 の 0.45m の平ら)を描けず、皮が段石の背で 0.3〜0.85 窪んで
        //   土の斜面で立ち上がった。当たる先: 石段を名指す坂(kaidans[].atRoute)の路盤すべて。
        {
            int nr = 0; var f = Grid; float ken = C("ken");
            foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
            {
                var r = O(o); if (r == null) continue;
                bool hasK = false; foreach (var ko in A(Get(D, "kaidans")) ?? new List<object>()) { var kk = O(ko); if (kk != null && S(Get(kk, "atRoute")) == S(Get(r, "name"))) hasK = true; }
                if (!hasK) continue;   // 石段を名指す坂だけ(芯を寄せる坂 toeFix は均した地形のまま)
                Vector2[] pts; float[] ys; float width; string an;
                if (!RampAxis(r, out pts, out ys, out width, out an) || pts.Length < 2) continue;
                var line = new List<Vector2>(pts); var cum = new float[pts.Length];
                for (int m = 1; m < pts.Length; m++) cum[m] = cum[m - 1] + Vector2.Distance(pts[m - 1], pts[m]);
                for (int j = 0; j < dnz; j++)
                    for (int i = 0; i < dnx; i++)
                    {
                        int k = j * dnx + i; if (!ok[k]) continue;
                        var q = new Vector2(dx0 + i * dstep, dz0 + j * dstep);
                        var st = EdoBuild.ArcOf(line, q);
                        if (Mathf.Abs(st.y) > width * 0.5f || st.x <= 1e-3f || st.x >= cum[cum.Length - 1] - 1e-3f) continue;
                        int m0 = 0; while (m0 + 2 < cum.Length && st.x > cum[m0 + 1]) m0++;
                        float y = Mathf.Lerp(ys[m0], ys[m0 + 1], (st.x - cum[m0]) / Mathf.Max(1e-4f, cum[m0 + 1] - cum[m0]));
                        if (Mathf.Abs(y - gh[k]) < 1e-3f) continue;
                        gh[k] = y; nr++;
                    }
            }
            sb.AppendLine("  坂の路盤の帯を縦断(GradeRamps の節点)で皮の格子 " + dstep.ToString("F2") + "m に写した節点 " + nr);
            // 上がり口の段石の背の平ら(指図 kaidans[].topStep「背の地盤は天端 −0.02」【硬】)を皮の平らな面に(RampAxis が起こした物)
            //   ⭐ 第58巡: 坂の節点(RampAxis)から起こすと坂を持たない石段(K_Tsuyo)や節点の近い坂(K_Kuruwa)で面が無く、背が 0.6 窪んだ ⇒
            //   据わった上がり口の段石の実メッシュから全石段ぶん起こす(TopLandingFaces)
            foreach (var tf in TopLandingFaces(sb)) faces.Add(tf);
        }
        // ⭐ 返しの石垣と長屋の背の間の溝(Stage2b と同じ BackTrenches)も設計の地盤へ ── 溝の中は低い側の面まで下げる(⛔ 上げない)。
        //   皮が graded(門の内の面)のまま描くと、溝を N39_1 の背まで土で埋め戻す(EDO-0502 第19巡)
        {
            var trs = BackTrenches(null); int nt = 0;
            if (trs.Count > 0)
                for (int j = 0; j < dnz; j++)
                    for (int i = 0; i < dnx; i++)
                    {
                        int k = j * dnx + i; if (!ok[k]) continue;
                        float ty = TrenchAt(trs, new Vector2(dx0 + i * dstep, dz0 + j * dstep));
                        if (!float.IsNaN(ty) && ty < gh[k] - 1e-4f) { gh[k] = ty; nt++; }
                    }
            if (trs.Count > 0) sb.AppendLine("  返しと長屋の背の間の溝を設計の地盤へ写した節点 " + nt + "(溝 " + trs.Count + ")");
        }
        // ⭐ 池の岸の断面(指図 hosoku.zosei「gardens[NiwaShoin].hori」.danmen・EDO-0502 第61巡)を皮の格子で設計の地盤へ ──
        //   算出物 graded は 1m・地形は 2m 格子で、汀の外 2〜3m まで地表が水面より低く描かれ、水面が板のように浮いた(第60巡 縁の 1520/3203 点)。
        //   汀線からの符号付きの距離 d(陸 +)で: 陸は max(設計, 州浜なら 水面 + d/5 ≤ 岸・石組/乱杭なら 岸)、水の中は 型の棚と法(底 bedY で止める)。
        //   型 = 最寄りの護岸の区間(石組護岸・州浜・乱杭)の折れ線が 1.5m 以内ならその型、無ければ州浜。中島(設計 > 水面)は触らない。
        //   描くのは帯 |d| ≤ 3m(drawAreas として CutEdgeSkin に渡す)。当たる先: 算出物の汀線を持つ庭(岡部 書院の泉水)。
        var drawAreas = new List<Vector2[]>();
        {
            var GL = A(Get(IMPL, "gardens")) ?? new List<object>();
            Dictionary<string, object> hori = null;
            System.Action<object> fh = null;
            fh = o => { var d0 = o as Dictionary<string, object>; if (d0 != null) { foreach (var kv in d0) { if (kv.Key.EndsWith("].hori") && kv.Value is Dictionary<string, object>) hori = (Dictionary<string, object>)kv.Value; else if (hori == null) fh(kv.Value); } return; } var l0 = o as List<object>; if (l0 != null) foreach (var v in l0) if (hori == null) fh(v); };
            fh(D);
            System.Func<string, string, float> rx2 = (txt, pat) => { var m = System.Text.RegularExpressions.Regex.Match(txt ?? "", pat); return m.Success ? float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : float.NaN; };
            var dm = hori == null ? null : O(Get(hori, "danmen"));
            string tS = dm == null ? null : S(Get(dm, "州浜")), tI = dm == null ? null : S(Get(dm, "石組")), tR = dm == null ? null : S(Get(dm, "乱杭"));
            float bank = hori == null ? float.NaN : F(Get(hori, "bank"));
            float sLand = rx2(tS, @"陸\s*([0-9.]+)\s*m"), sLandB = rx2(tS, @"陸[^、]*1\s*:\s*([0-9.]+)"), sWat = rx2(tS, @"水中\s*([0-9.]+)\s*m"), sWatB = rx2(tS, @"水中[^、]*1\s*:\s*([0-9.]+)"), sFar = rx2(tS, @"以遠\s*1\s*:\s*([0-9.]+)");
            float iShelf = rx2(tI, @"棚\s*([0-9.]+)"), iW = rx2(tI, @"幅\s*([0-9.]+)"), iFar = rx2(tI, @"1\s*:\s*([0-9.]+)");
            float rUp = rx2(tR, @"立ち上げ\s*([0-9.]+)"), rFar = rx2(tR, @"1\s*:\s*([0-9.]+)");
            var miss = new List<string>();
            foreach (var kv in new[] { new KeyValuePair<string, float>("岸 bank", bank), new KeyValuePair<string, float>("州浜の陸の幅", sLand), new KeyValuePair<string, float>("州浜の陸の法", sLandB), new KeyValuePair<string, float>("州浜の水中の幅", sWat),
                                       new KeyValuePair<string, float>("州浜の水中の法", sWatB), new KeyValuePair<string, float>("州浜の以遠の法", sFar), new KeyValuePair<string, float>("石組の棚", iShelf), new KeyValuePair<string, float>("石組の棚の幅", iW),
                                       new KeyValuePair<string, float>("石組の法", iFar), new KeyValuePair<string, float>("乱杭の立ち上げ", rUp), new KeyValuePair<string, float>("乱杭の法", rFar) })
                if (float.IsNaN(kv.Value)) miss.Add(kv.Key);
            foreach (var o in GL)
            {
                var mg = O(o); if (!(S(Get(mg, "kind")) ?? "").StartsWith("汀線")) continue;
                if (miss.Count > 0) { sb.AppendLine("  ★ 池の岸の断面: 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 皮で描かない"); break; }
                var wl = A(Get(mg, "world")); if (wl == null || wl.Count < 3) continue;
                float wy = F(mg["y"]), bed = F(Get(mg, "bedY")); string zone = S(Get(mg, "zone"));
                var ring = new Vector2[wl.Count]; for (int i = 0; i < wl.Count; i++) { var q = A(wl[i]); ring[i] = new Vector2(F(q[0]), F(q[1])); }
                // 護岸の区間の折れ線と型(0 州浜・1 石組・2 乱杭)
                var segs = new List<KeyValuePair<int, Vector2[]>>();
                foreach (var o2 in GL)
                {
                    var g2 = O(o2); if (S(Get(g2, "zone")) != zone) continue; string k2 = S(Get(g2, "kind")) ?? "";
                    int ty = k2.StartsWith("石組護岸") ? 1 : k2.StartsWith("乱杭") ? 2 : k2.StartsWith("州浜") ? 0 : -1; if (ty < 0) continue;
                    var w2 = A(Get(g2, "world")); if (w2 == null || w2.Count < 2) continue;
                    var pl = new Vector2[w2.Count]; for (int i = 0; i < w2.Count; i++) { var q = A(w2[i]); pl[i] = new Vector2(F(q[0]), F(q[1])); }
                    segs.Add(new KeyValuePair<int, Vector2[]>(ty, pl));
                }
                System.Func<Vector2[], Vector2, bool, float> distPl = (pl, q, closed) => { float best = float.MaxValue; int n = pl.Length; for (int i = 0; i < (closed ? n : n - 1); i++) best = Mathf.Min(best, DistSeg(q, pl[i], pl[(i + 1) % n])); return best; };
                float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                foreach (var q in ring) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
                const float BANDG = 3f, STONE_IN = 0.3f; int nUp = 0, nDn = 0;   // STONE_IN: 石組の石の半幅の最小(長軸 0.45〜1.2 の半分 ≥ 0.22)より少し広く ── 石の足の下に隠れる
                int i0 = Mathf.Max(0, Mathf.FloorToInt((mnx - BANDG - dx0) / dstep)), i1 = Mathf.Min(dnx - 1, Mathf.CeilToInt((mxx + BANDG - dx0) / dstep));
                int j0 = Mathf.Max(0, Mathf.FloorToInt((mnz - BANDG - dz0) / dstep)), j1 = Mathf.Min(dnz - 1, Mathf.CeilToInt((mxz + BANDG - dz0) / dstep));
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                    {
                        int k = j * dnx + i; if (!ok[k]) continue;
                        var q = new Vector2(dx0 + i * dstep, dz0 + j * dstep);
                        float dd = distPl(ring, q, true); if (dd > BANDG) continue;
                        bool inside = EdoGeom.PIP(ring, q); float d = inside ? -dd : dd;
                        int ty = 0; float bt = 1.5f; foreach (var sg in segs) { float e = distPl(sg.Value, q, false) - Mathf.Abs(d); if (e < bt) { bt = e; ty = sg.Key; } }
                        float v = gh[k], y;
                        if (d >= 0f) y = Mathf.Max(v, ty == 0 ? Mathf.Min(bank, wy + d / sLandB) : bank);
                        else
                        {
                            if (v > wy + 0.01f) continue;   // 中島・岩島の盛りは触らない
                            float u = -d;
                            if (ty == 0) y = u <= sWat ? wy - u / sWatB : wy - sWat / sWatB - (u - sWat) / sFar;
                            else if (u <= STONE_IN) y = bank;   // 石組・乱杭: 汀の線から内へ STONE_IN は石・杭の足の下(岸の高さ ── 水面の縁を地表で囲む【硬】)
                            else if (ty == 1) y = u - STONE_IN <= iW ? iShelf : iShelf - (u - STONE_IN - iW) / iFar;
                            else y = rUp - (u - STONE_IN) / rFar;
                            y = Mathf.Max(y, bed);
                        }
                        if (Mathf.Abs(y - v) < 1e-3f) continue;
                        if (y > v) nUp++; else nDn++;
                        gh[k] = y;
                    }
                // 帯の外形(汀線の外接を BANDG 広げた矩形 ── 描くかは CutEdgeSkin が升ごとに設計と地形の差で決める)
                drawAreas.Add(new[] { new Vector2(mnx - BANDG, mnz - BANDG), new Vector2(mxx + BANDG, mnz - BANDG), new Vector2(mxx + BANDG, mxz + BANDG), new Vector2(mnx - BANDG, mxz + BANDG) });
                sb.AppendLine("  池の岸の断面 " + S(mg["name"]) + ": 汀の帯 ±" + BANDG.ToString("F0") + "m を皮の格子 " + dstep.ToString("F2") + "m で ── 上げた節点 " + nUp + "・下げた節点 " + nDn
                    + "(岸 " + bank.ToString("F2") + "・水面 " + wy.ToString("F2") + "・底 " + bed.ToString("F2") + "・型 州浜/石組/乱杭 = 護岸の区間 " + segs.Count + ")");
            }
        }
        // 背の小段(StairSideAndEndBacks の #side・#endsBack)も描く区域へ ── 小段 + 先の法(盛りの上限 ÷ 法)まで
        foreach (var kv in SodeBenches(null))
        {
            if (!(kv.Key.EndsWith("#side") || kv.Key.EndsWith("#endsBack"))) continue;
            foreach (var pr in kv.Value)
            {
                var bk = pr.Value; float L = Vector2.Distance(bk.a, bk.b); if (L < 0.05f) continue;
                Vector2 t = (bk.b - bk.a) / L; float reach = bk.w + Mathf.Min(bk.maxFill, 3f) * bk.bf, ex = bk.noEndSpill ? 0.25f : Mathf.Min(bk.maxFill, 3f) * bk.bf;
                drawAreas.Add(new[] { bk.a - t * ex, bk.b + t * ex, bk.b + t * ex + bk.back * reach, bk.a - t * ex + bk.back * reach });
            }
        }
        // ⭐ 法尻の土留めの背の小段(Stage2b が地形を切る・指図 toeBench)も設計の地盤へ ── 同じ式(EdoBuild.ToeBenchAt)。⛔ 上げない
        {
            var toes = ToeBenches(null); int ntb = 0;
            if (toes.Count > 0)
                for (int j = 0; j < dnz; j++)
                    for (int i = 0; i < dnx; i++)
                    {
                        int k = j * dnx + i; if (!ok[k]) continue;
                        var q = new Vector2(dx0 + i * dstep, dz0 + j * dstep); float nw = gh[k];
                        foreach (var tk in toes) nw = EdoBuild.ToeBenchAt(tk, q, nw);
                        if (nw < gh[k] - 1e-4f) { gh[k] = nw; ntb++; }
                    }
            if (toes.Count > 0) sb.AppendLine("  法尻の土留めの背の小段を設計の地盤へ写した節点 " + ntb + "(" + toes.Count + " 区間)");
        }
        // ⭐ 棟の下の均し(Stage3 が地形へ LevelPad で書く・指図 service[].yFrom)も設計の地盤へ ── 同じ式(EdoBuild.LevelPadAt)・同じ足あと(ServicePads)・
        //   低い順(共有する節点は高い棟が勝つ ── Stage3 と同じ順)。節点は皮の格子(dstep)・平らな縁の幅は地形の升。⛔ 写さないと縁の皮が附属屋の足元を均す前の設計の地盤で描き、
        //   厩 −0.133・薪蔵 −0.096・米蔵 −0.062 埋まった(第36巡: 地形の均しは効いても皮込みの測りは不変)。当たる先: 皮を起こす邸の、皮の縁に掛かる均した棟すべて
        {
            var pads3 = ServicePads(); pads3.Sort((x, y) => x.y.CompareTo(y.y)); int npd = 0;
            float bfP = C("batterFill"), bcP = C("batterCut");
            // ⭐ 平らに取る幅は**地形の升**(Stage3 の LevelPad と同じ・2026-10-07 第46巡)。⛔ 皮の格子(dstep 0.25)で取ると平らな縁が足あと + 0.25 しか無く、
            //   設計の格子と皮の格子のずれで縁の外の法の節点が混ざり、厩の NE の隅が皮で +0.032 埋まった(地形の節点は 0 なのに)。
            var tdP = Terrain.activeTerrain.terrainData; float padCell = tdP.size.x / (tdP.heightmapResolution - 1);
            if (pads3.Count > 0)
                for (int j = 0; j < dnz; j++)
                    for (int i = 0; i < dnx; i++)
                    {
                        int k = j * dnx + i; if (!ok[k]) continue;
                        var q = new Vector2(dx0 + i * dstep, dz0 + j * dstep); float nw = gh[k];
                        foreach (var pd in pads3) nw = EdoBuild.LevelPadAt(pd.parcel, pd.foot, pd.y, bfP, bcP, padCell, q, nw, pd.rim);
                        if (Mathf.Abs(nw - gh[k]) > 1e-4f) { gh[k] = nw; npd++; }
                    }
            if (pads3.Count > 0) sb.AppendLine("  棟の下の均しを設計の地盤へ写した節点 " + npd + "(" + pads3.Count + " 棟・升 " + dstep.ToString("F2") + "m・EdoBuild.LevelPadAt)");
        }
        // ⭐ 袖の坂の低い端の小口に土を被せる(⚠ 設計の地盤を書く最後の手 ── 溝・小段・棟の下の均しの後。盛った節点は SkinDesign.hold で法の頭打ちから外す・第49巡)(指図 sodeSlope 追記 2026-10-07「小口は高さ 0.15・長さ 0.25 の土を 1:1.5 で被せて隠す」【硬】・EDO-0502 第42巡)──
        //   据えた端の駒の小口を実メッシュで測り(走りの外へ最も出た頂点の帯 0.05)、小口の外の設計の地盤を「小口の頂(≤ 地盤 + 高さ)から 1:bf で下りる面」まで盛る。⛔ 下げない。
        //   当たる先: sodeSlope の低い端を水平の駒で終える袖(岡部 TW_Kado_Sode)。
        var buriedParts = new HashSet<GameObject>();
        var covers = new List<SodeEndCover>(); var hold = new bool[gh.Length]; var coverFace = new List<Vector4>(); var coverLat = new List<Vector2>(); var coverDu = new List<float[]>(); var coverTop = new List<float[]>(); var coverPiece = new List<GameObject>();   // (端の点 x, z, 小口の頂, 走りの外の縁 u)
        {
            foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
            {
                var w = O(o); if (w == null) continue; string nm = S(Get(w, "name"));
                Dictionary<string, object> sw = null; foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
                string ssl = sw == null ? null : S(Get(sw, "sodeSlope")); var lnS = A(Get(w, "line"));
                if (ssl == null || lnS == null || lnS.Count < 2) continue;
                var nodesS = new List<Vector2>(); foreach (var q in lnS) { var pq = A(q); nodesS.Add(new Vector2(F(pq[0]), F(pq[1]))); }
                var cv = new List<SodeEndCover>(); SodeSlopeSegs(nm, nodesS, ssl, null, null, null, cv);
                foreach (var c in cv)
                {
                    // 端の駒 = 走りの外へ最も出た頂点を持つ駒(端から 3m 以内)
                    var dan = Group("Dan"); Vector3 best = Vector3.zero; float um = float.MinValue; GameObject eg = null;
                    foreach (Transform t in dan)
                    {
                        if (!t.gameObject.activeInHierarchy || !t.name.StartsWith(nm + "_")) continue;
                        var rb = EdoBuild.RB(t.gameObject); if (Vector2.Distance(new Vector2(rb.center.x, rb.center.z), c.end) > 3f) continue;
                        foreach (var v in EdoBuild.Body(t, 999999)) { float u = Vector2.Dot(new Vector2(v.x, v.z) - c.end, c.away); if (u > um) { um = u; eg = t.gameObject; } }
                    }
                    if (eg == null) { sb.AppendLine("  ★ 小口の土 " + nm + ": 低い端の駒が無い ── 盛らない"); continue; }
                    Vector2 lat = new Vector2(-c.away.y, c.away.x); float top = float.MinValue, lmn = float.MaxValue, lmx = float.MinValue;
                    var ev = EdoBuild.Body(eg.transform, 999999);
                    foreach (var v in ev) { var r2 = new Vector2(v.x, v.z) - c.end; if (Vector2.Dot(r2, c.away) < um - 0.05f) continue; top = Mathf.Max(top, v.y); float l = Vector2.Dot(r2, lat); lmn = Mathf.Min(lmn, l); lmx = Mathf.Max(lmx, l); }
                    // ⭐ 小口の面は野面で凸凹 ⇒ **横 0.1m の帯ごとに**小口の面の位置(帯の中で走りの外へ最も出た頂点)と頂を測る(第49巡)。⛔ 最も出た 1 点(um)から
                    //   一律に法を下ろすと、引っ込んだ帯では土が 0.1〜0.2 低く、小口が見えた。帯は小口の頂から 0.4 下までの頂点(根入れの出っ張りで面を決めない)。
                    int nbn = Mathf.Max(1, Mathf.CeilToInt((lmx - lmn) / 0.1f)); var fDu = new float[nbn]; var fTop = new float[nbn];
                    for (int b = 0; b < nbn; b++) { fDu[b] = float.NaN; fTop[b] = float.NaN; }
                    foreach (var v in ev)
                    {
                        if (v.y < top - 0.4f) continue; var r2 = new Vector2(v.x, v.z) - c.end; float l = Vector2.Dot(r2, lat);
                        if (l < lmn - 1e-3f || l > lmx + 1e-3f) continue; int b = Mathf.Clamp(Mathf.FloorToInt((l - lmn) / 0.1f), 0, nbn - 1);
                        float u = Vector2.Dot(r2, c.away) - um; if (float.IsNaN(fDu[b]) || u > fDu[b]) fDu[b] = u;
                    }
                    for (int b = 1; b < nbn; b++) if (float.IsNaN(fDu[b])) fDu[b] = fDu[b - 1];
                    for (int b = nbn - 2; b >= 0; b--) if (float.IsNaN(fDu[b])) fDu[b] = fDu[b + 1];
                    foreach (var v in ev)
                    {
                        var r2 = new Vector2(v.x, v.z) - c.end; float l = Vector2.Dot(r2, lat); if (l < lmn - 1e-3f || l > lmx + 1e-3f) continue;
                        int b = Mathf.Clamp(Mathf.FloorToInt((l - lmn) / 0.1f), 0, nbn - 1); float u = Vector2.Dot(r2, c.away) - um;
                        if (u >= fDu[b] - 0.05f && (float.IsNaN(fTop[b]) || v.y > fTop[b])) fTop[b] = v.y;
                    }
                    for (int b = 0; b < nbn; b++) if (float.IsNaN(fTop[b])) fTop[b] = top;
                    int nc = 0; float mx = 0f;
                    // ⭐ 追記 2026-10-08(第53巡): 端の駒を土で完全に埋める ── 駒の足形(走り du ∈ [pIn, 0]・横 [lmn, lmx])と横の両側 burySide を平ら、頂は端の駒の天端 + buryTop を
                    //   内の端に取り、小口(東)へ水 1/drn で下げる。その外は 1:bf で下りる(前の地表・背の小段・手前の坂の駒の小口へ)。⛔ 下げない(盛るだけ)。
                    //   当たる先: sodeSlope に追記 2026-10-08 の文を持つ袖(岡部 TW_Kado_Sode)。
                    float pTop = float.MinValue, pIn = 0f, pL0 = float.MaxValue, pL1 = float.MinValue;   // 横の幅は駒全体で(⛔ 小口の帯だけで取ると見え面の側が平らから外れ −0.16 低かった)
                    foreach (var v in ev) { var rv = new Vector2(v.x, v.z) - c.end; pTop = Mathf.Max(pTop, v.y); pIn = Mathf.Min(pIn, Vector2.Dot(rv, c.away) - um); float lv = Vector2.Dot(rv, lat); pL0 = Mathf.Min(pL0, lv); pL1 = Mathf.Max(pL1, lv); }
                    bool bury = !float.IsNaN(c.buryTop);
                    for (int j = 0; bury && j < dnz; j++)
                        for (int i = 0; i < dnx; i++)
                        {
                            int k = j * dnx + i; if (!ok[k]) continue;
                            var q = new Vector2(dx0 + i * dstep, dz0 + j * dstep) - c.end; float du = Vector2.Dot(q, c.away) - um, dl = Vector2.Dot(q, lat);
                            float exU = Mathf.Max(0f, Mathf.Max(pIn - du, du)), exL = Mathf.Max(0f, Mathf.Max(pL0 - c.burySide - dl, dl - pL1 - c.burySide));
                            float ex = Mathf.Sqrt(exU * exU + exL * exL);
                            // 駒の上と横の両側 burySide は端の駒の天端 + buryTop の水平(指図 追記 2026-10-08【柔】)。水 1/drn は平らの外の擦り付けの側でとる
                            //   ── 小口の外(東・du > 0)へ下りる面を 1:bf と 1/drn の緩い方にせず、1:bf の法の頭を平らの縁から 1/drn で落としてから下ろす
                            //   (⛔ 第55巡まで頂を内の端に取り駒の上で 1/20 下げていた ── 小口の際で 0.11 下がり天端 +0.012 だった)。
                            float yTop = pTop + c.buryTop;
                            float y = yTop - (exU > 0f && du > 0f ? Mathf.Min(exU, dstep) * c.drn + Mathf.Max(0f, ex - dstep) / c.bf : ex / c.bf);
                            if (y <= gh[k] + 1e-4f) continue;
                            mx = Mathf.Max(mx, y - gh[k]); gh[k] = y; nc++; hold[k] = true;
                        }
                    if (bury) { top = pTop; buriedParts.Add(eg); }   // 検めは端の駒の天端で・埋める駒は皮の被りの検めから外す(SkinDesign.buried)
                    for (int j = 0; !bury && j < dnz; j++)
                        for (int i = 0; i < dnx; i++)
                        {
                            int k = j * dnx + i; if (!ok[k]) continue;
                            var q = new Vector2(dx0 + i * dstep, dz0 + j * dstep) - c.end; float du0 = Vector2.Dot(q, c.away) - um, dl = Vector2.Dot(q, lat);
                            // ⭐ 横は駒の幅の両側へ c.side 広げる(追記 2026-10-07d【柔】)── 広げた帯は小口の面の外(du ≥ −1 格子)だけ(駒の背・脇の小段へ回さない ── 背の小段の水を堰かない)。
                            //   広げた先は 1:bf で横へ下りる。小口の面より奥へは 1 格子だけ回り込む(背の小段へ盛りを延ばさない)。
                            float exL = Mathf.Max(lmn - dl, dl - lmx);   // 駒の幅の外へ出た量(内は負)
                            if (exL > c.side + Mathf.Min(1.5f, 3f * c.len) + dstep || du0 < -0.6f || du0 > c.flat + 1.5f + 3f * c.len) continue;
                            int b = Mathf.Clamp(Mathf.FloorToInt((dl - lmn) / 0.1f), 0, nbn - 1); float du = du0 - fDu[b], tb = fTop[b] + c.rise;
                            // 広げた帯の小口の面より奥は 1 格子だけ(小口の角を回り込んで包む ── 第51巡: 角の点が立たないと皮の双一次で角の前の土が 0.16 低い)
                            if (exL > 1e-3f && du < -dstep) continue;
                            // ⭐ 土の頂は**その帯の小口の頂**(第49巡): 前の地盤が見付の想定(c.h)より低い所(前の面の隅 16.40)でも小口を隠し切る ── 「高さ ≤ gh + c.h」で切ると
                            //   0.10 見えた。長さは 1:bf で前の地盤に届くまで(c.len は狙い・上限は 3 倍)。小口の 1 格子奥の節点(駒の外形の中)も頂へ ── 外の点が
                            //   駒の下の低い節点と混ざって小口の際が下がらないように(駒の中の点は皮の cap が天端の下へ納める)。
                            // 頂(小口の頂 + rise)から c.flat は平ら(水 c.drn で端の外へ)・その先 1:bf。横の広げの外も 1:bf
                            float yFlat = tb - c.flat * c.drn;
                            if (du < -dstep || du > c.flat + Mathf.Min(Mathf.Max(0f, yFlat - gh[k]) * c.bf, 3f * c.len) + dstep) continue;
                            float duo = Mathf.Max(0f, du);
                            float y = duo <= c.flat ? tb - duo * c.drn : yFlat - (duo - c.flat) / c.bf;
                            if (exL > c.side) y -= (exL - c.side) / c.bf;
                            if (y > gh[k] + 1e-4f) { if (EdoBuild.SkinTrace != null) EdoBuild.SkinTraceLog.AppendLine("  小口の土の節点 (" + (dx0 + i * dstep).ToString("F3") + ", " + (dz0 + j * dstep).ToString("F3") + ") du " + du.ToString("F3") + " " + gh[k].ToString("F3") + "→" + y.ToString("F3")); mx = Mathf.Max(mx, y - gh[k]); gh[k] = y; nc++; hold[k] = true; }
                        }
                    coverDu.Add(fDu); coverTop.Add(fTop); coverPiece.Add(eg);
                    coverFace.Add(new Vector4(c.end.x, c.end.y, top, um)); coverLat.Add(new Vector2(lmn, lmx)); covers.Add(c);
                    sb.AppendLine("  小口の土 " + nm + ": 端の駒 " + eg.name + "・小口の頂 " + top.ToString("F2") + "・幅 " + (lmx - lmn).ToString("F2") + "m ⇒ 設計の地盤を盛った節点 " + nc + "(最大 " + mx.ToString("F2") + "・頂 = 小口の頂 + " + c.rise.ToString("F2") + "・平ら " + c.flat.ToString("F2") + "m(水 " + (c.drn > 0f ? "1/" + (1f / c.drn).ToString("F0") : "—") + ")・横 +" + c.side.ToString("F2") + "・1:" + c.bf.ToString("0.0") + ")");
                }
            }
        }
        var crestCover = NozuraCrestCoverOf(sb, buriedParts);
        var design = new EdoBuild.SkinDesign
        {
            x0 = dx0, z0 = dz0, step = dstep, nx = dnx, nz = dnz, h = gh, ok = ok,
            batterCut = C("batterCut"), batterFill = C("batterFill"), baseAt = EdoBuild.BaseDem(), own = Poly, hold = hold, buried = buriedParts, flats = FlatFacesOf(buriedParts, sb),
            crestCover = crestCover
        };
        // ⭐ 区画の外の節点は区画の外の地盤(今の地形・区画の内と駒の下の節点は造成前)で持たせる(EDO-0502 第29巡)── 外周の石垣の見え面の前
        EdoBuild.DesignOutsideOwn(design, parts, sb);
        if (EdoBuild.SkinTrace != null)
            for (int k = 0; k < gh.Length; k++) if (hold[k]) EdoBuild.SkinTraceLog.AppendLine("  小口の土の節点 #" + k + " 皮へ渡す前 " + design.h[k].ToString("F3") + " ok " + design.ok[k]);
        // ⭐ 部材に埋まった地形の木(幹の足が土留め・石垣・石段の外形の中)は先に退ける(EdoBuild.RetireTreesInParts・硬い)──
        //   守ると穴が開かず、2m 格子が駒の下の節点を見え面の前へ描いて土の尾根が立つ(EDO-0502 第27巡 西の返し)
        {
            var tlog = new List<string>(); int tn = EdoBuild.RetireTreesInParts(Poly, parts, tlog);
            if (tn > 0) sb.AppendLine("  部材に埋まった地形の木を退けた " + tn + " 本: " + string.Join(" / ", tlog.ToArray()));
            // ⭐ 道辺から幹の芯が 2.0m 未満の地形の木も退ける(硬い・EdoBuild.RetireTreesNearRoad・2026-10-06 EDO-0502 第29巡 辺14 の proto40 1.138m)
            var rlog = new List<string>(); int rn = EdoBuild.RetireTreesNearRoad(Poly, EdoBuild.NiwaSet.TREE_KEEP, rlog);
            if (rn > 0) sb.AppendLine("  道辺から 2.0m 未満の地形の木を退けた " + rn + " 本: " + string.Join(" / ", rlog.ToArray()));
        }
        // ⛔ 地形の木の升には穴を開けない(Unity は穴の升の地形の木を黙って落とす)── 区画の中の地形の木の点を渡す
        var plant = new List<Vector2>();
        {
            var tr = EdoBuild.T(); var td = tr.terrainData; var org = tr.transform.position; var P = Poly;
            foreach (var ti in td.treeInstances)
            {
                var q = new Vector2(org.x + ti.position.x * td.size.x, org.z + ti.position.z * td.size.z);
                if (EdoGeom.PIP(P, q)) plant.Add(q);
            }
            // ⭐ 柵(Stage2 が地形に据えた木柵 Fences)の足元の升にも穴を開けない(EDO-0502 第9巡): 柵は皮より先に地形で据わる ──
            //   穴を開けると皮が設計の地盤(段の上の面 11.0)を描き、西の木柵 F_Hori_0 の端に地形より 2.3m 高い土の楔が立った。
            //   柵の駒の外接の芯と走りの両端(地表の点)を渡す。当たる先: 皮を起こす邸で、皮より先に地形へ据わる柵・杭(岡部 F_Hori)。
            var fences = root == null ? null : root.transform.Find("Fences");
            if (fences != null)
                foreach (Transform fc in fences)
                {
                    if (!fc.gameObject.activeInHierarchy) continue;
                    var fb = EdoBuild.RB(fc.gameObject); if (fb.size == Vector3.zero) continue;
                    foreach (var q in new[] { new Vector2(fb.center.x, fb.center.z), new Vector2(fb.min.x, fb.min.z), new Vector2(fb.max.x, fb.max.z) })
                        if (EdoGeom.PIP(P, q)) plant.Add(q);
                }
        }
        // ⭐ 庭の土工(池を掘り築山を盛る庭の区域)は面の縁の升に数えない(faceKeepOut・土井 EDO-0533 と同じ型)──
        //   外さないと皮が池を面の高さで埋め、築山を削る(EDO-0502 第59巡: 書院の泉水を造成へ入れた)。
        //   区域は算出物 gardens の「庭の区域」のうち、同じ zone に汀線か築山を持つもの(白洲の区域は外さない)
        var keepNiwa = new List<Vector2[]>();
        {
            var gl = A(Get(IMPL, "gardens")) ?? new List<object>(); var earth = new HashSet<string>();
            foreach (var o in gl) { var g = O(o); string k = S(Get(g, "kind")) ?? ""; if (k.StartsWith("汀線") || k.StartsWith("築山")) earth.Add(S(Get(g, "zone")) ?? ""); }
            foreach (var o in gl)
            {
                var g = O(o); if ((S(Get(g, "kind")) ?? "") != "庭の区域" || !earth.Contains(S(Get(g, "zone")) ?? "")) continue;
                var w = A(Get(g, "world")); if (w == null || w.Count < 3) continue;
                var pl = new Vector2[w.Count]; for (int i = 0; i < w.Count; i++) { var q = A(w[i]); pl[i] = new Vector2(F(q[0]), F(q[1])); }
                keepNiwa.Add(pl);
            }
            if (keepNiwa.Count > 0) sb.AppendLine("  庭の土工の区域 " + keepNiwa.Count + " を面の縁の升から外す(faceKeepOut)");
        }
        var rep = EdoBuild.CutEdgeSkin("Okabe", grp, parts, faces, tol, design: design, backfill: 0f, sealFace: true,
                                       crestBandParts: band, plantPoints: plant, faceKeepOut: keepNiwa, drawAreas: drawAreas);
        AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
        sb.AppendLine("  古い皮を外して塞いだ升 " + filled + " / 部材 " + rep.parts + "(土留め " + (band.Count - igN) + "・外周の石垣 " + igN + "(うち区画の外の足元を描けない " + igOut + ")・石段 " + stairN + ")/ 面 " + faces.Count + " / 守った地形の木 " + plant.Count);
        sb.AppendLine("  " + rep);
        sb.Append(EdoBuild.SkinGapTable(parts, faces, tol));
        // 小口の土の検め(硬): 端の駒の小口の外 0.02 の描かれた地表が小口の頂 − 0.02 に届くか(⛔ 届かなければ小口が見える)
        // ⭐ **描かれた地表(皮込み・EdoBuild.Drawn)で測る**(2026-10-07 EDO-0502 第49巡)。⛔ SkinGround は min(設計面, 地形) で、盛った小口の土も皮も読まず
        //   設計面 15.95 を拾って +0.70 の偽の ⛔ を出していた(描かれた地表は 16.41〜16.49)。
        var drawnC = EdoBuild.Drawn();
        for (int ci = 0; ci < covers.Count; ci++)
        {
            // 帯ごとに: 小口の面の 0.02 外(駒の張り出しの下なら外へ 0.02 ずつ ── 石に隠れた所は見えない)の描かれた地表が、その帯の小口の頂 − 0.02 に届くか
            var c = covers[ci]; var cf = coverFace[ci]; var fDu = coverDu[ci]; var fTop = coverTop[ci]; var pc = new List<GameObject> { coverPiece[ci] };
            Vector2 lat = new Vector2(-c.away.y, c.away.x); float worst = float.MinValue; Vector2 wAt = Vector2.zero; int n = 0;
            for (int b = 0; b < fDu.Length; b++)
            {
                float l = coverLat[ci].x + (b + 0.5f) * 0.1f; if (l > coverLat[ci].y) break;
                Vector2 q = Vector2.zero; bool free = false;
                for (float e = 0.02f; e <= 0.3f; e += 0.02f)
                {
                    q = c.end + c.away * (cf.w + fDu[b] + e) + lat * l;
                    if (float.IsNaN(EdoBuild.RayToBodies(pc, new Vector3(q.x, fTop[b] + 1f, q.y), Vector3.down, 3f))) { free = true; break; }
                }
                if (!free) continue;
                float g = drawnC.At(q.x, q.y); if (float.IsNaN(g)) continue;
                float lim = fTop[b] - g; n++; if (lim > worst) { worst = lim; wAt = q; }
            }
            // ⭐ 追記 2026-10-08【硬】: 端の駒の足形(+ 横の burySide)の上の描かれた地表 ≥ 端の駒の天端 + buryMin(板の縁を一つも見せない)── 0.05 格子で測る
            if (!float.IsNaN(c.buryTop))
            {
                var pcG = coverPiece[ci]; var evB = EdoBuild.Body(pcG.transform, 999999); float pT = float.MinValue, pI = 0f, pO = float.MinValue, lA = float.MaxValue, lB = float.MinValue;
                foreach (var v in evB) { var r2 = new Vector2(v.x, v.z) - c.end; float u = Vector2.Dot(r2, c.away), l2 = Vector2.Dot(r2, lat); pT = Mathf.Max(pT, v.y); pI = Mathf.Min(pI, u); pO = Mathf.Max(pO, u); lA = Mathf.Min(lA, l2); lB = Mathf.Max(lB, l2); }
                float wB = float.MaxValue; Vector2 wBAt = Vector2.zero; int nB = 0;
                for (float u = pI; u <= pO + 1e-3f; u += 0.05f)
                    for (float l2 = lA; l2 <= lB + 1e-3f; l2 += 0.05f)
                    {
                        var q = c.end + c.away * u + lat * l2;
                        if (float.IsNaN(EdoBuild.RayToBodies(pc, new Vector3(q.x, pT + 1f, q.y), Vector3.down, 3f))) continue;   // 駒の上だけ
                        float g = drawnC.At(q.x, q.y); if (float.IsNaN(g)) continue; nB++;
                        if (g - pT < wB) { wB = g - pT; wBAt = q; }
                    }
                sb.AppendLine("  端の駒を埋める土の検め " + c.key + ": 駒の上の描かれた地表 − 端の駒の天端 " + pT.ToString("F2") + " の最小 = " + (nB == 0 ? "-" : wB.ToString("+0.000;-0.000")) + "m @(" + wBAt.x.ToString("F1") + ", " + wBAt.y.ToString("F1") + ")・点 " + nB + "(硬 ≥ +" + c.buryMin.ToString("F2") + ")" + (nB > 0 && wB < c.buryMin ? " ⛔" : " ⭕"));
                continue;
            }
            sb.AppendLine("  小口の土の検め " + c.key + ": 帯ごとの小口の頂 − 小口の前の描かれた地表 の最大 = " + (n == 0 ? "-" : worst.ToString("+0.00;-0.00")) + "m @(" + wAt.x.ToString("F1") + ", " + wAt.y.ToString("F1") + ")・帯 " + n + "(硬 ≤ 0.02)" + (n > 0 && worst > 0.02f ? " ⛔" : " ⭕"));
        }
        if (crestCover != null) sb.AppendLine("  " + crestCover.Measure((x, z) => drawnC.At(x, z)));
        if (EdoBuild.SkinTrace != null) { sb.AppendLine("  皮の追跡:"); sb.Append(EdoBuild.SkinTraceLog.ToString()); }
        // ⭐ 皮を起こし直した後に、練塀・隅を**描かれた皮の上**で据え直す(EdoBuild.SinkGroupToBed)。Stage2 の時点の床は
        //    皮を外した 2m 格子で、皮の細かい面より 0.06〜0.40m 高い所があり、N_Hei_35_3 が 0.40m 浮いた(2026-10-04 第12巡)。
        sb.AppendLine("  皮の後に " + SeatHeiOnBed(Group("Kakoi")));
        sb.AppendLine("  皮の後に " + SeatKakiOnBed());
        sb.AppendLine("  皮の後に " + StackCurbOnSkin());
        sb.AppendLine("  皮の後に " + SeatMonOnSkin());
        // 野面の継ぎ目の段差・見え面から土が覗く所(光線・EDO-0502 第64巡)── 皮を起こし直した後でないと土の側が測れない
        { var rt = GameObject.Find(GN); var dn = rt == null ? null : rt.transform.Find("Dan");
          if (dn != null) sb.AppendLine("  " + EdoBuild.NozuraSeamReport(rt.transform, dn, rt.transform.Find("EdgeSkin")).Replace("\n", "\n  "));
          if (dn != null && rt.transform.Find("EdgeSkin") != null) sb.AppendLine("  " + EdoBuild.NozuraSkinPlaneCheck(dn, rt.transform.Find("EdgeSkin")));
          if (rt.transform.Find("EdgeSkin") != null) sb.AppendLine("  " + SteepEdgeReport(rt.transform));
          if (rt.transform.Find("EdgeSkin") != null) sb.AppendLine("  " + FlatReport(rt.transform, buriedParts)); }
        return sb.ToString();
    }

    /// <summary>**野面の石垣の天端の裏石の帯を土で覆う**型(EdoBuild.NozuraCrestCover)を、段の土留め(Dan)の野面の駒から起こす
    /// (指図 const.nozuraCrestCover・普請方の設計 2026-10-09・EDO-0502 第63巡)。数は指図の文から読む(⛔ 読めなければ ★ を刷って null ── 覆わない)。
    /// ④ 盛らない所 = 長屋の躯体の長手の脇の一間・長屋と練塀・隅(Kakoi)の実面から犬走り(外形の凸包から)。当たる先: 岡部の野面の段の土留め全部(袖・返し・腰・郭)。</summary>
    static EdoBuild.NozuraCrestCover NozuraCrestCoverOf(System.Text.StringBuilder sb, HashSet<GameObject> buried = null)
    {
        string txt = S(Get(O(D["const"]), "nozuraCrestCover")); if (txt == null) return null;
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        System.Func<string, int, float> rx = (pat, gi) => { var m = System.Text.RegularExpressions.Regex.Match(txt, pat); return m.Success ? float.Parse(m.Groups[gi].Value, inv) : float.NaN; };
        float fr = rx(@"見え面から\s*([0-9.]+)\s*〜\s*([0-9.]+)\s*の地盤", 1), bk = rx(@"見え面から\s*([0-9.]+)\s*〜\s*([0-9.]+)\s*の地盤", 2), rise = rx(@"天端より\s*([0-9.]+)\s*高く", 1),
              drn = rx(@"背へ\s*1\s*/\s*([0-9.]+)", 1), bf = rx(@"から先は\s*1\s*:\s*([0-9.]+)", 1), inu = rx(@"犬走り\s*([0-9.]+)", 1);
        bool nagIchi = txt.Contains("長屋の背の一間");
        var miss = new List<string>();
        if (float.IsNaN(fr) || float.IsNaN(bk)) miss.Add("帯(見え面から 〜)"); if (float.IsNaN(rise)) miss.Add("天端より高く"); if (float.IsNaN(drn)) miss.Add("背へ 1/"); if (float.IsNaN(bf)) miss.Add("先の法 1:"); if (float.IsNaN(inu)) miss.Add("犬走り");
        if (miss.Count > 0) { sb.AppendLine("  ★ const.nozuraCrestCover: 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 覆わない"); return null; }
        var cc = new EdoBuild.NozuraCrestCover { front = fr, back = bk, rise = rise, drain = 1f / drn, bf = bf };
        // 言い直し 2026-10-09b(皮の格子 0.25 では 0.36 の線が切れない): 見え面から fr2 より前の節点は駒の天端 − capDrop 以下【硬】・fr2〜bk は天端 + rise(+ minSoil 以上【硬】)・最高は fr2 の線
        {
            int i2 = txt.IndexOf("言い直し 2026-10-09b");
            if (i2 >= 0)
            {
                string t2 = txt.Substring(i2);
                System.Func<string, int, float> r2 = (pat, gi) => { var m = System.Text.RegularExpressions.Regex.Match(t2, pat); return m.Success ? float.Parse(m.Groups[gi].Value, inv) : float.NaN; };
                float fr2 = r2(@"見え面から\s*([0-9.]+)\s*より前の皮の節点は駒の天端\s*[−\-]\s*([0-9.]+)\s*以下", 1), cd2 = r2(@"見え面から\s*([0-9.]+)\s*より前の皮の節点は駒の天端\s*[−\-]\s*([0-9.]+)\s*以下", 2),
                      rs2 = r2(@"の節点は天端\s*\+\s*([0-9.]+)", 1), mn2 = r2(@"\+\s*([0-9.]+)\s*以上が【硬】", 1);
                if (float.IsNaN(fr2) || float.IsNaN(cd2) || float.IsNaN(rs2) || float.IsNaN(mn2)) sb.AppendLine("  ★ const.nozuraCrestCover 言い直し 2026-10-09b: 指図から読めない(前の線・天端−・+・以上)── 旧のまま");
                else { cc.front = fr2; cc.capDrop = cd2; cc.rise = rs2; cc.minSoil = mn2; fr = fr2; sb.AppendLine("  天端の裏石の帯 言い直し 2026-10-09b: 見え面から " + fr2.ToString("F2") + " より前は天端 −" + cd2.ToString("F2") + " 以下【硬】(見え面の上は真下の石 −" + cd2.ToString("F2") + ")・" + fr2.ToString("F2") + "〜" + bk.ToString("F2") + " は +" + rs2.ToString("F2") + "(≥ +" + mn2.ToString("F2") + "【硬】)"); }
            }
        }
        // 指図 terraceWalls[].kadoFace(普請方 2026-10-09・第67巡)「隅の駒の見え面より前に皮を被せない【硬】(根入れの土は除く)・被った土は前の地表まで下げる」
        //   ⇒ 全ての野面の隅の駒に効かせる(EdoBuild.NozuraCrestCover.kadoFront)。⛔ 文が読めなければ ★ で効かせない。
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
        {
            var t2 = O(o2); string kf = t2 == null ? null : S(Get(t2, "kadoFace")); if (kf == null) continue;
            if (kf.Contains("見え面より前に皮を被せない") && kf.Contains("前の地表")) { cc.kadoFront = true; sb.AppendLine("  隅の駒の見え面の前(kadoFace・" + S(Get(t2, "name")) + "): 見え面より前の皮を前の地表まで下げる【硬】── 全ての野面の隅の駒へ"); }
            else sb.AppendLine("  ★ kadoFace(" + S(Get(t2, "name")) + "): 指図から読めない ── 効かせない");
        }
        int nk = 0;
        foreach (Transform c in Group("Dan"))
        {
            if (!c.gameObject.activeInHierarchy) continue;
            var mf = c.GetComponentInChildren<MeshFilter>(); string ap = mf == null || mf.sharedMesh == null ? "" : AssetDatabase.GetAssetPath(mf.sharedMesh);
            if (!ap.Contains("Nozura")) continue;
            if (buried != null && buried.Contains(c.gameObject)) continue;   // 設計で土に埋める駒(袖の低い端)は帯を持たない
            bool kado = System.IO.Path.GetFileName(ap).Contains("_Kado"); if (kado) nk++;
            cc.Add(c.gameObject, kado);
        }
        // ④ 長屋の背の一間・犬走り(外形の凸包から測る ── 長い躯体の頂点だけで測ると壁の中ほどを見落とす)
        var cen = new List<Vector2>(); var hulls = new List<Vector2[]>(); var isNag = new List<bool>(); var axs = new List<Vector2>(); var rng = new List<Vector3>(); var boxes = new List<Vector4>();
        var root = GameObject.Find(GN); var kk = root == null ? null : root.transform.Find("Kakoi"); float ken = C("ken");
        if (kk != null)
            foreach (Transform c in kk)
            {
                if (!c.gameObject.activeInHierarchy) continue;
                var pts = new List<Vector2>(); foreach (var v in EdoBuild.Body(c, 2000)) pts.Add(new Vector2(v.x, v.z)); if (pts.Count < 3) continue;
                var h = EdoBuild.ConvexHull2(pts); if (h.Count < 3) continue;
                bool nag = EdoBuild.IsNagayaBody(c.gameObject); var ax = nag ? EdoBuild.RunAxis(c.gameObject) : Vector2.zero; if (ax != Vector2.zero) ax.Normalize();
                Vector2 ce = Vector2.zero; foreach (var p in h) ce += p; ce /= h.Count; float lo = float.MaxValue, hi = float.MinValue;
                float x0 = float.MaxValue, z0 = float.MaxValue, x1 = float.MinValue, z1 = float.MinValue;
                foreach (var p in h) { float u = Vector2.Dot(p - ce, ax); lo = Mathf.Min(lo, u); hi = Mathf.Max(hi, u); x0 = Mathf.Min(x0, p.x); z0 = Mathf.Min(z0, p.y); x1 = Mathf.Max(x1, p.x); z1 = Mathf.Max(z1, p.y); }
                hulls.Add(h.ToArray()); isNag.Add(nag && ax != Vector2.zero); axs.Add(ax); rng.Add(new Vector3(lo, hi, 0f)); boxes.Add(new Vector4(x0, z0, x1, z1)); cen.Add(ce);
            }
        int nNag = 0; foreach (var b in isNag) if (b) nNag++;
        float reach = Mathf.Max(inu, nagIchi ? ken : 0f);
        cc.keepOut = q =>
        {
            for (int i = 0; i < hulls.Count; i++)
            {
                var bx = boxes[i]; if (q.x < bx.x - reach || q.x > bx.z + reach || q.y < bx.y - reach || q.y > bx.w + reach) continue;
                if (EdoGeom.PIP(hulls[i], q)) return true;
                float d = EdoGeom.DistToPolyEdge(hulls[i], q); if (d < inu) return true;
                if (nagIchi && isNag[i] && d < ken) { float u = Vector2.Dot(q - cen[i], axs[i]); if (u >= rng[i].x && u <= rng[i].y) return true; }
            }
            return false;
        };
        sb.AppendLine("  天端の裏石の帯(const.nozuraCrestCover): 見え面から " + fr.ToString("F2") + "〜" + bk.ToString("F2") + " を天端 +" + rise.ToString("F2") + "(背へ 1/" + drn.ToString("F0") + ")・その先 1:" + bf.ToString("0.#")
                    + " ── 野面の駒 " + cc.pieces + "(うち隅 " + nk + ")・面 " + cc.faces + "・盛らない所 = 長屋 " + nNag + " の背の一間・Kakoi " + hulls.Count + " の犬走り " + inu.ToString("F2"));
        return cc;
    }

    /// <summary>算出物 graded の写しに、坂の路盤(ramps[] の芯・幅・縦断)の帯の中だけ今の地形(GradeRamps の均し)を写す(EDO-0502 第8巡)。
    /// 帯 = 芯から 幅/2 + (坂の高低差) × 切の法 batterCut(切通しの法が届きうる最大)。帯の外・区画の外は graded のまま。⛔ 地形には触らない。</summary>
    /// <summary>袖石垣(指図 terraceWalls[] の mode sode で欄 backfill を持つ物)の**天端の割りと背の小段の裏込め**を解く
    /// (指図 TW_Kado_Sode.top/backfill/backDrain・普請方の設計 2026-10-04・EDO-0502 第13巡)。数は指図の文から読む(⛔ 読めなければ null ── 決め打ちしない)。
    /// 背の法の高さ = 天端の前の線から背へ「天端の奥行(avoid.dodomeCrestDepthM[野面の乱積み])+ 0.25m」の点の**造成の設計面**(算出物 graded ──
    /// 盛った後の地形で測ると流し直しで割りが動くので、盛りの前の面で測る)。Stage2b(据えと盛り)・Stage3b(皮の設計の地盤)・GradeQA が同じこれを使う。</summary>
    /// <summary>袖の坂の硬い検め(据えた後に測る): 区間の名の頭・線・背の向き・天端と背の地盤の差の上限。</summary>
    /// <summary>指図 terraces[].edgeRetain の「縁の落差が x を超える所は全部石垣の見え面で受け、土の面を見せない【硬】」を持つ面ごとに
    /// EdoBuild.SkinSteepReport を刷る(落差は欄から・法は欄 backfill の 1:x ── ⛔ 読めなければ ★)。第72巡。当たる先: 岡部 Kadonouchi(欄を持つ面すべて)。</summary>
    static string SteepEdgeReport(Transform root)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        if (_flat == null) _flat = FlatFaces(null);
        float bf = float.NaN; foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); var mb = System.Text.RegularExpressions.Regex.Match(S(Get(t2, "backfill")) ?? "", @"法\s*1\s*:\s*([0-9.]+)"); if (mb.Success) { bf = float.Parse(mb.Groups[1].Value, inv); break; } }
        foreach (var o in A(Get(D, "terraces")) ?? new List<object>())
        {
            var t = O(o); string er = S(Get(t, "edgeRetain")); if (er == null) continue;
            var m = System.Text.RegularExpressions.Regex.Match(er, @"縁の落差が\s*([0-9.]+)\s*を超える所は全部石垣");
            if (!m.Success) continue; string nm = S(Get(t, "name")) ?? S(Get(t, "id"));
            var lf = _flat.Find(f0 => f0.name == nm); if (lf.poly == null || float.IsNaN(bf)) { sb.Append("★ " + nm + " の縁の落差: 面か法が読めない "); continue; }
            sb.Append(EdoBuild.SkinSteepReport(root, root.Find("EdgeSkin"), lf.poly, 6f, float.Parse(m.Groups[1].Value, inv), bf, nm) + " ");
        }
        return sb.Length == 0 ? "縁の落差の検め: 欄 edgeRetain に該当なし" : sb.ToString();
    }

    /// <summary>**面の平らの検め**(指図 terraces[].flat「面は y、外れ ±e【硬】」・普請方 2026-10-09f・第73巡)。描かれた皮の頂点のうち、面の輪郭の中で
    /// 部材の外形の外の物の |高さ − y| &gt; e を数える。例外(欄の文): 「小口を被せる土」= 土で埋める駒(buried)から 0.8 以内 /「Higashi_Fall への擦り付け」= 設計の地盤
    /// (算出物 graded)が y − e より低い所(東の平場の勾配の面へ下りる南東の角)。⛔ 読めなければ ★。当たる先: 欄 flat を持つ面(岡部 Kadonouchi)。</summary>
    static string FlatReport(Transform root, HashSet<GameObject> buried)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        if (_flat == null) _flat = FlatFaces(null);
        var skin = root.Find("EdgeSkin"); if (skin == null) return "面の平らの検め: 皮が無い";
        foreach (var o in A(Get(D, "terraces")) ?? new List<object>())
        {
            var t = O(o); string fl = S(Get(t, "flat")); if (fl == null) continue; string nm = S(Get(t, "name"));
            var m = System.Text.RegularExpressions.Regex.Match(fl, @"面は\s*([0-9.]+)\s*、\s*外れ\s*±\s*([0-9.]+)");
            var lf = _flat.Find(f0 => f0.name == nm);
            if (!m.Success || lf.poly == null) { sb.Append("★ " + nm + " flat: 指図か面が読めない "); continue; }
            float y0 = float.Parse(m.Groups[1].Value, inv), e = float.Parse(m.Groups[2].Value, inv);
            bool exCover = fl.Contains("小口を被せる土"), exRamp = fl.Contains("Higashi_Fall"), bandF = fl.Contains("見え面の足元までの帯");
            var mcv = System.Text.RegularExpressions.Regex.Match(fl, @"見え面から\s*([0-9.]+)\s*以内・高さ\s*([0-9.]+)\s*以内");
            float covD = mcv.Success ? float.Parse(mcv.Groups[1].Value, inv) : float.NaN, covH = mcv.Success ? float.Parse(mcv.Groups[2].Value, inv) : float.NaN;
            var hulls = new List<Vector2[]>(); var bh = new List<Vector2[]>(); var footH = bandF ? FaceFootHulls(lf.poly) : new List<Vector2[]>();
            foreach (Transform g in root) foreach (Transform c in g)
            {
                if (!c.gameObject.activeInHierarchy || c == skin) continue; var rr = c.GetComponentInChildren<Renderer>(); if (rr == null) continue;
                var bc = rr.bounds.center; var q0 = new Vector2(bc.x, bc.z); if (!EdoGeom.PIP(lf.poly, q0) && EdoBuild.EdgeDistPublic(lf.poly, q0) > 8f) continue;
                var p2 = new List<Vector2>(); foreach (var v in EdoBuild.Body(c, 4000)) p2.Add(new Vector2(v.x, v.z)); if (p2.Count < 3) continue;
                var hl = EdoBuild.ConvexHull2(p2).ToArray(); hulls.Add(hl); if (buried != null && buried.Contains(c.gameObject)) bh.Add(hl);
            }
            int n = 0, nAll = 0, nEx = 0; float worst = 0f; Vector3 wAt = Vector3.zero;
            // 穴の縁の垂れ(同じ平面の位置で下へ下りる頂点)を数えない ── 平面の位置ごとに最も高い頂点(描かれた地表)だけ
            var top = new Dictionary<long, Vector3>();
            foreach (var mf in skin.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.sharedMesh == null) continue;
                foreach (var v0 in mf.sharedMesh.vertices) { var v = mf.transform.TransformPoint(v0); long kq = ((long)Mathf.RoundToInt(v.x * 200f) << 32) ^ (uint)Mathf.RoundToInt(v.z * 200f); Vector3 o2; if (!top.TryGetValue(kq, out o2) || v.y > o2.y) top[kq] = v; }
            }
            {
                foreach (var v in top.Values)
                {
                    var q = new Vector2(v.x, v.z); bool inP = EdoGeom.PIP(lf.poly, q);
                    if (!inP)
                    {   // 追記 2026-10-09g: 縁から見え面の足元までの帯(縁から外へ 3m 以内に部材の外形がある所)
                        if (!bandF) continue; float dE = EdoBuild.EdgeDistPublic(lf.poly, q); if (dE > 3f) continue;
                        Vector2 nE = q; { float bd = float.MaxValue; for (int k = 0; k < lf.poly.Length; k++) { Vector2 a0 = lf.poly[k], b0 = lf.poly[(k + 1) % lf.poly.Length], ab = b0 - a0; float tt = Mathf.Clamp01(Vector2.Dot(q - a0, ab) / Mathf.Max(ab.sqrMagnitude, 1e-8f)); var c0 = a0 + ab * tt; float dd = (q - c0).sqrMagnitude; if (dd < bd) { bd = dd; nE = c0; } } }
                        Vector2 dir = (q - nE).sqrMagnitude > 1e-8f ? (q - nE).normalized : Vector2.zero; if (dir == Vector2.zero) continue; bool inBand = false;
                        for (float tt = 0f; tt <= 3f - dE + 1e-3f && !inBand; tt += 0.1f) { var qq = q + dir * tt; foreach (var hl in footH) if (EdoGeom.PIP(hl, qq)) { inBand = true; break; } }
                        if (!inBand) continue;
                    }
                    bool hid = false; foreach (var hl in hulls) if (EdoGeom.PIP(hl, q)) { hid = true; break; } if (hid) continue;
                    float hiL = y0 + e; if (!float.IsNaN(covD)) foreach (var hl in hulls) if (EdoBuild.EdgeDistPublic(hl, q) <= covD) { hiL = y0 + covH; break; }   // 根入れを隠す土
                    nAll++; float dv = Mathf.Abs(v.y - y0); if (v.y >= y0 - e - 1e-4f && v.y <= hiL + 1e-4f) continue;
                    bool ex = false;
                    if (exCover) foreach (var hl in bh) if (EdoGeom.PIP(hl, q) || EdoBuild.EdgeDistPublic(hl, q) <= 0.8f) { ex = true; break; }
                    if (!ex && exRamp) { float gy = DesignY(q); if (!float.IsNaN(gy) && gy < y0 - e) ex = true; }
                    if (ex) { nEx++; continue; }
                    n++; if (dv > worst) { worst = dv; wAt = v; }
                }
            }
            sb.Append(nm + " の平ら(" + y0.ToString("F2", inv) + " ±" + e.ToString("F2", inv) + "・硬): 外れ " + n + " / " + nAll + " 頂点" + (n > 0 ? "(最悪 " + worst.ToString("F2", inv) + " @(" + wAt.x.ToString("F1", inv) + ", " + wAt.y.ToString("F2", inv) + ", " + wAt.z.ToString("F1", inv) + ")) ⛔" : " ⭕") + "・例外(小口の土・Higashi_Fall)" + nEx + " ");
        }
        return sb.Length == 0 ? "面の平らの検め: 欄 flat に該当なし" : sb.ToString();
    }

    /// <summary>指図 terraces[].flat を皮の平らな面(EdoBuild.FlatFace)へ ── 面は y・外れ ±e【硬】・例外は欄の文(小口を被せる土 = 埋める駒から 0.8 以内・
    /// Higashi_Fall への擦り付け = 算出物 graded が y − e より低い所)。⛔ 読めなければ ★ で効かせない。第73巡。</summary>
    static List<EdoBuild.FlatFace> FlatFacesOf(HashSet<GameObject> buried, System.Text.StringBuilder sb)
    {
        var res = new List<EdoBuild.FlatFace>(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        if (_flat == null) _flat = FlatFaces(null);
        foreach (var o in A(Get(D, "terraces")) ?? new List<object>())
        {
            var t = O(o); string fl = S(Get(t, "flat")); if (fl == null) continue; string nm = S(Get(t, "name"));
            var m = System.Text.RegularExpressions.Regex.Match(fl, @"面は\s*([0-9.]+)\s*、\s*外れ\s*±\s*([0-9.]+)"); var lf = _flat.Find(f0 => f0.name == nm);
            if (!m.Success || lf.poly == null) { sb.AppendLine("  ★ " + nm + " flat: 指図か面が読めない ── 効かせない"); continue; }
            float y0 = float.Parse(m.Groups[1].Value, inv), e = float.Parse(m.Groups[2].Value, inv);
            var bh = new List<Vector2[]>();
            if (fl.Contains("小口を被せる土") && buried != null) foreach (var g in buried) { if (g == null) continue; var p2 = new List<Vector2>(); foreach (var v in EdoBuild.Body(g.transform, 4000)) p2.Add(new Vector2(v.x, v.z)); if (p2.Count >= 3) bh.Add(EdoBuild.ConvexHull2(p2).ToArray()); }
            bool exRamp = fl.Contains("Higashi_Fall");
            // 追記 2026-10-09g: 縁から見え面の足元までの帯も・根入れを隠す土は見え面から cd 以内・高さ ch 以内
            bool band = fl.Contains("見え面の足元までの帯");
            var mc = System.Text.RegularExpressions.Regex.Match(fl, @"見え面から\s*([0-9.]+)\s*以内・高さ\s*([0-9.]+)\s*以内");
            float cd = mc.Success ? float.Parse(mc.Groups[1].Value, inv) : float.NaN, ch = mc.Success ? float.Parse(mc.Groups[2].Value, inv) : float.NaN;
            if (band && !mc.Success) sb.AppendLine("  ★ " + nm + " flat 追記 2026-10-09g: 根入れを隠す土の範囲が読めない ── 帯は ±e のまま");
            var bandH = band ? FaceFootHulls(lf.poly) : null;
            res.Add(new EdoBuild.FlatFace { name = nm, poly = lf.poly, y = y0, e = e, band = band, coverD = cd, coverH = ch, bandHulls = bandH, exempt = q =>
            {
                foreach (var hl in bh) if (EdoGeom.PIP(hl, q) || EdoBuild.EdgeDistPublic(hl, q) <= 0.8f) return true;
                if (exRamp) { float gy = DesignY(q); if (!float.IsNaN(gy) && gy < y0 - e) return true; }
                return false;
            } });
            sb.AppendLine("  面の平ら " + nm + ": " + y0.ToString("F2", inv) + " ±" + e.ToString("F2", inv) + "(例外 小口の土 " + bh.Count + " 駒" + (exRamp ? "・Higashi_Fall の擦り付け" : "") + ")");
        }
        return res.Count == 0 ? null : res;
    }

    /// <summary>面の縁の帯を受ける部材 = 野面の石垣の駒(Dan)と石段の段石(名 K_)の外形 ── 面の輪郭から 8m 以内の物(第75巡・指図 flat 追記 2026-10-09g「石垣・石段の見え面の足元」)。</summary>
    static List<Vector2[]> FaceFootHulls(Vector2[] poly)
    {
        var res = new List<Vector2[]>(); var root = GameObject.Find(GN); if (root == null) return res;
        foreach (var t in root.GetComponentsInChildren<Transform>())
        {
            if (!t.gameObject.activeInHierarchy || t.parent == null) continue;
            bool dan = t.parent.name == "Dan", step = t.name.StartsWith("K_") && t.GetComponent<Renderer>() != null; if (!dan && !step) continue;
            var rr = t.GetComponentInChildren<Renderer>(); if (rr == null) continue; var c = rr.bounds.center; var q = new Vector2(c.x, c.z);
            if (!EdoGeom.PIP(poly, q) && EdoBuild.EdgeDistPublic(poly, q) > 8f) continue;
            var p2 = new List<Vector2>(); foreach (var v in EdoBuild.Body(t, 4000)) p2.Add(new Vector2(v.x, v.z)); if (p2.Count >= 3) res.Add(EdoBuild.ConvexHull2(p2).ToArray());
        }
        return res;
    }

    class SodeSlopeCheck { public string key; public List<Vector2> line; public List<Vector2> back; public float maxDiff, depth; public float sLo; }
    /// <summary>袖の坂の低い端の小口へ被せる土(指図 sodeSlope 追記 2026-10-07「その小口は高さ h・長さ len の土を 1:bf で被せて隠す」【硬】)。
    /// end = 線を延ばした低い端の点・away = 端の外へ向く走り。Stage3b が据えた端の駒の小口を実メッシュで測って皮の設計の地盤へ盛る(SodeEndCoverAt)。</summary>
    class SodeEndCover { public string key; public Vector2 end, away; public float h, len, bf, rise, flat, side, drn, buryTop = float.NaN, burySide, buryMin; }

    /// <summary>**袖の坂**(指図 terraceWalls[].sodeSlope・普請方の設計 2026-10-07・EDO-0502 第41〜42巡)── 袖の天端を段にせず、背の法 + off の坂の一続きの線にする
    /// (上端 cap で頭打ち)。背の法 = 天端の前の線から背へ「天端の奥行(avoid.dodomeCrestDepthM[野面の乱積み])+ 0.25」の造成の設計面(SodeBenches と同じ)。
    /// ⭐ 第42巡(追記 2026-10-07): **出隅の踊り場** ── 折れ 30° 以上の節点の ±half を水平にし(高さ = 元の坂の線が隅を通る値)、その範囲の背の法も
    /// 天端 − drop の水平に描き直す(EdoBuild.BackBench の切り・盛り ≤ 上限【硬】)。坂の線は描き直した背から引き直す(⛔ 踊り場の脇で段を作らない)。
    /// **低い端** ── 坂の駒で天端が前の地表 + reachHi に届いた所から、水平の駒(見付 fixExp・焼いた H fixH)を一駒(⛔ 傾けて沈めない)。小口の土は Stage3b。
    /// 数は指図の文から読む(⛔ 読めなければ ★ を刷って建てない)。<paramref name="nozSegs"/> が null なら据えずに踊り場の小段と小口の土だけ返す(SodeBenches・Stage3b)。
    /// 当たる先: sodeSlope を持つ袖(岡部 TW_Kado_Sode)。</summary>
    /// <summary>sideEnd の延長の背の小段(第74巡)── StairGaps(Stage2b)が作り、SodeBenches(Stage3b の設計の地盤)が読む。</summary>
    static readonly List<EdoBuild.BackBench> _sideEndBenches = new List<EdoBuild.BackBench>();
    static string SodeSlopeSegs(string key, List<Vector2> nodes, string txt, List<EdoBuild.NozuraSeg> nozSegs, List<SodeSlopeCheck> chk,
                                List<EdoBuild.BackBench> landOut = null, List<SodeEndCover> coverOut = null, bool skipOwnLanding = false, float sinkEndOverride = float.NaN)
    {
        // sinkEndOverride(第75巡・指図 sideEnd 追記 2026-10-09h【硬・上書き】): 低い端を延ばさず(打ち切りの条件を当てない)、水平の駒を置かず坂の駒のまま打ち切り、小口をこの深さ沈める
        // skipOwnLanding: 他の欄(TW_Kado_Shumen.sideEnd)が「sodeSlope と同じ下ろし方」で借りるとき、TW_Kado_Sode 固有の追記 2026-10-09c(049f・出隅の踊り場 19.80)を読まない(第73巡)
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; bool dry = nozSegs == null;
        System.Func<string, int, float> rxg = (pat, gi) => { var m = System.Text.RegularExpressions.Regex.Match(txt ?? "", pat); return m.Success ? float.Parse(m.Groups[gi].Value, inv) : float.NaN; };
        System.Func<string, float> rx = pat => rxg(pat, 1);
        float cap = rx(@"上端\s*([0-9.]+)"), off = rx(@"背の法\s*\+\s*([0-9.]+)"), maxDiff = rx(@"差\s*≤\s*([0-9.]+)");
        // 追記 2026-10-07(第42巡): 出隅の踊り場・低い端の水平の駒と小口の土
        bool landing = (txt ?? "").Contains("踊り場"), flatEnd = float.IsNaN(sinkEndOverride) && System.Text.RegularExpressions.Regex.IsMatch(txt ?? "", @"水平の\s*H\d{4}");
        float half = rx(@"隅から両側へ\s*([0-9.]+)"), lDrop = rx(@"背の法も天端\s*[−\-]\s*([0-9.]+)"), lCut = rx(@"上手の切り\s*≤\s*([0-9.]+)"), lFill = rx(@"下手の盛り\s*≤\s*([0-9.]+)");
        // 追記 2026-10-07c(第45巡): 踊り場の下手の盛りの上限を緩める(後の追記が勝つ)・低い端の水平の駒の背の小段(天端 − eDrop・控えの後端 + eBehind・背の地盤 ≥ eMin・盛り ≤ eFill・その先 1:eBf・水 1/eDrn)
        { float lf2 = rx(@"下手の盛りの上限を\s*([0-9.]+)"); if (!float.IsNaN(lf2)) lFill = lf2; }
        float eDrop = rx(@"低い端の\s*H\d{4}\s*の背は天端\s*[−\-]\s*([0-9.]+)"), eBehind = rx(@"控えの後端\s*\+\s*([0-9.]+)"), eMin = rx(@"背の地盤を\s*([0-9.]+)\s*以上"),
              eFill = rx(@"盛り最大\s*([0-9.]+)"), eBf = rx(@"その先は\s*1\s*:\s*([0-9.]+)\s*で擦り付け"), eDrn = rx(@"水は\s*1\s*/\s*([0-9.]+)");
        bool endBench = !float.IsNaN(eDrop);
        float reachLo = rxg(@"前の地表\s*\+\s*([0-9.]+)\s*〜\s*([0-9.]+)\s*に届いたら", 1), reachHi = rxg(@"前の地表\s*\+\s*([0-9.]+)\s*〜\s*([0-9.]+)\s*に届いたら", 2);
        float fixH = rx(@"水平の\s*H(\d{4})") / 1000f, fixExp = rx(@"見付\s*([0-9.]+)\s*・\s*根入れ");
        float cvH = rxg(@"高さ\s*([0-9.]+)\s*・\s*長さ\s*([0-9.]+)\s*の土を", 1), cvL = rxg(@"高さ\s*([0-9.]+)\s*・\s*長さ\s*([0-9.]+)\s*の土を", 2), cvBf = rx(@"の土を\s*1\s*:\s*([0-9.]+)");
        // 追記 2026-10-07d(第51巡): 小口の土の頂 = 小口の頂 + cvRise・小口から cvFlat は平ら(水 1/cvDrn で端の外へ)・横は駒の幅の両側へ cvSide【柔】── 無ければ 0(旧の形)
        float cvRise = rx(@"頂を小口の頂\s*\+\s*([0-9.]+)"), cvFlat = rx(@"小口から\s*([0-9.]+)\s*は平ら"), cvSide = rx(@"両側へ\s*([0-9.]+)\s*広げ"), cvDrn = rx(@"土の頂の水は\s*1\s*/\s*([0-9.]+)");
        if (float.IsNaN(cvRise)) cvRise = 0f; if (float.IsNaN(cvFlat)) cvFlat = 0f; if (float.IsNaN(cvSide)) cvSide = 0f;
        // 追記 2026-10-08(第53巡・追記d を置き換える): 低い端の水平の駒を土で完全に埋める ── 土の頂 = 端の駒の天端 + buryTop・駒の上と幅の両側 burySide は平ら【柔】・
        //   その外 1:cvBf・描かれた地表 ≥ 端の駒の天端 + buryMin【硬】。読めれば小口の土はこの形(Stage3b)。
        float buryTop = rx(@"土の頂は端の駒の天端\s*\+\s*([0-9.]+)"), burySide = rx(@"駒の幅の両側\s*([0-9.]+)\s*を平ら"), buryMin = rx(@"描かれた地表は端の駒の天端\s*\+\s*([0-9.]+)\s*以上");
        if (!float.IsNaN(buryTop) && (float.IsNaN(burySide) || float.IsNaN(buryMin))) { sb.AppendLine("  ★ " + key + " sodeSlope 追記 2026-10-08: 平らの幅か描かれた地表の下限が読めない ── 埋めない"); buryTop = float.NaN; }
        // 追記 2026-10-09(第63巡): 上端の取り付き ── 本線との取り付きから最初の駒 topLen は天端 = 上端の水平【硬】・その背に天端 − tDrop の平らな小段(幅 tW【柔】・
        //   盛り ≤ tFill)・2 つ目の駒から勾配 −tG を最優先に背の法 + off の線へ戻す・小段の水は石垣から離れる向きへ 1/tDrn。⛔ 読めなければ ★ で旧のまま
        float topLen = float.NaN, tDrop = float.NaN, tW = float.NaN, tFill = float.NaN, tG = float.NaN, tDrn = float.NaN, tFill2 = float.NaN, tWMin = float.NaN, tDrop2 = float.NaN;
        float cDrop = float.NaN, cTo = float.NaN, cLand = float.NaN, cLandFill = float.NaN;   // 追記 2026-10-09c
        {
            int i9 = (txt ?? "").IndexOf("追記 2026-10-09");
            if (i9 >= 0)
            {
                string t9 = txt.Substring(i9);
                System.Func<string, float> r9 = pat => { var m = System.Text.RegularExpressions.Regex.Match(t9, pat); return m.Success ? float.Parse(m.Groups[1].Value, inv) : float.NaN; };
                topLen = r9(@"最初の駒1つ分[(（]\s*([0-9.]+)\s*m"); tDrop = r9(@"天端\s*[−\-]\s*([0-9.]+)\s*の\s*[0-9.]+\s*で幅"); tW = r9(@"で幅\s*([0-9.]+)\s*間") * 1.818f;
                tFill = r9(@"踊り場の上限\s*([0-9.]+)"); tG = r9(@"勾配\s*[−\-]\s*([0-9.]+)\s*を最優先"); tDrn = r9(@"離れる向きへ\s*1\s*/\s*([0-9.]+)");
                var m9 = new List<string>();
                if (float.IsNaN(topLen)) m9.Add("最初の駒の長さ"); if (float.IsNaN(tDrop)) m9.Add("小段の天端−"); if (float.IsNaN(tW)) m9.Add("小段の幅"); if (float.IsNaN(tFill)) m9.Add("盛りの上限");
                if (float.IsNaN(tG)) m9.Add("2つ目の駒の勾配"); if (float.IsNaN(tDrn)) m9.Add("小段の水");
                if (m9.Count > 0) { sb.AppendLine("  ★ " + key + " sodeSlope 追記 2026-10-09: 指図から読めない(" + string.Join("・", m9.ToArray()) + ")── 上端の取り付きは旧のまま"); topLen = float.NaN; }
                // 追記 2026-10-09b(第65巡): 盛りの上限(区画の内)・詰めてよい幅・届かない区間の小段の下げ(天端 −)
                int i9b = txt.IndexOf("追記 2026-10-09b");
                if (i9b >= 0)
                {
                    string tb9 = txt.Substring(i9b);
                    System.Func<string, float> rb = pat => { var m = System.Text.RegularExpressions.Regex.Match(tb9, pat); return m.Success ? float.Parse(m.Groups[1].Value, inv) : float.NaN; };
                    tFill2 = rb(@"盛りの上限は区画の内だけ\s*[0-9.]+\s*→\s*([0-9.]+)"); tWMin = rb(@"([0-9.]+)\s*まで詰めてよい"); tDrop2 = rb(@"[(（]\s*天端\s*[−\-]\s*([0-9.]+)\s*[)）]\s*まで下げる");
                    if (float.IsNaN(tFill2) || float.IsNaN(tWMin) || float.IsNaN(tDrop2)) { sb.AppendLine("  ★ " + key + " sodeSlope 追記 2026-10-09b: 指図から読めない(盛りの上限・詰める幅・下げた小段)── 旧のまま"); tFill2 = tWMin = tDrop2 = float.NaN; }
                }
                // 追記 2026-10-09c(第66巡): 2 つ目の駒で上端から cTo まで連続に下ろす【硬】・出隅の踊り場を cLand へ上げる【硬】・踊り場の背の盛りの上限(区画の内)cLandFill【硬】
                int i9c = skipOwnLanding ? -1 : txt.IndexOf("追記 2026-10-09c");
                if (i9c >= 0)
                {
                    string tc9 = txt.Substring(i9c);
                    System.Func<string, float> rc = pat => { var m = System.Text.RegularExpressions.Regex.Match(tc9, pat); return m.Success ? float.Parse(m.Groups[1].Value, inv) : float.NaN; };
                    cDrop = rc(@"1駒で\s*([0-9.]+)\s*下ろす"); cTo = rc(@"から\s*([0-9.]+)\s*まで連続で下ろす");
                    cLand = rc(@"出隅の踊り場は\s*[0-9.]+\s*から\s*([0-9.]+)\s*へ上げる"); cLandFill = rc(@"踊り場の背の盛りの上限は区画の内に限り\s*([0-9.]+)");
                    if (float.IsNaN(cTo) || float.IsNaN(cLand) || float.IsNaN(cLandFill)) { sb.AppendLine("  ★ " + key + " sodeSlope 追記 2026-10-09c: 指図から読めない(下ろす先・踊り場の高さ・踊り場の盛りの上限)── 旧のまま"); cDrop = cTo = cLand = cLandFill = float.NaN; }
                    // 追記 2026-10-09d(第67巡): 踊り場の背の盛りの上限(区画の内)を上書き
                    int i9d = txt.IndexOf("追記 2026-10-09d");
                    if (i9d >= 0 && !float.IsNaN(cLandFill))
                    { var md = System.Text.RegularExpressions.Regex.Match(txt.Substring(i9d), @"踊り場の背の盛りの上限は区画の内に限り\s*[0-9.]+\s*→\s*([0-9.]+)");
                      if (md.Success) cLandFill = float.Parse(md.Groups[1].Value, inv); else sb.AppendLine("  ★ " + key + " sodeSlope 追記 2026-10-09d: 指図から読めない(踊り場の盛りの上限)── 旧のまま"); }
                }
            }
        }
        float frontCut = flatEnd ? reachHi : rx(@"前の地表\s*\+\s*([0-9.]+)\s*以下"), sink = flatEnd ? float.NaN : rx(@"([0-9.]+)\s*以上下へ沈め");
        if (!float.IsNaN(sinkEndOverride)) { sink = sinkEndOverride; if (float.IsNaN(frontCut)) frontCut = 0f; }
        var gs = new List<float>(); var mg = System.Text.RegularExpressions.Regex.Match(txt ?? "", @"\{([^}]*)\}");
        if (mg.Success) foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(mg.Groups[1].Value, @"([0-9.]+)")) gs.Add(float.Parse(m.Groups[1].Value, inv));
        float depth = float.NaN;
        { var av = O(Get(D, "avoid")); System.Action<object> find = null; find = o => { var d = o as Dictionary<string, object>; if (d != null) { if (d.ContainsKey("dodomeCrestDepthM")) { var dd = O(d["dodomeCrestDepthM"]); if (dd != null && dd.ContainsKey("野面の乱積み")) depth = F(dd["野面の乱積み"]); } foreach (var v in d.Values) if (float.IsNaN(depth)) find(v); return; } var l = o as List<object>; if (l != null) foreach (var v in l) if (float.IsNaN(depth)) find(v); }; find(D); }
        float bfB = float.NaN;   // 踊り場の小段の先の法 = 袖の backfill の法(1:1.5)
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (t2 != null && S(Get(t2, "sodeSlope")) == txt) { var mb = System.Text.RegularExpressions.Regex.Match(S(Get(t2, "backfill")) ?? "", @"法\s*1\s*:\s*([0-9.]+)"); if (mb.Success) bfB = float.Parse(mb.Groups[1].Value, inv); } }
        var miss = new List<string>();
        if (float.IsNaN(cap)) miss.Add("上端"); if (float.IsNaN(off)) miss.Add("背の法+"); if (float.IsNaN(maxDiff)) miss.Add("差 ≤"); if (float.IsNaN(frontCut)) miss.Add("前の地表+");
        if (!flatEnd && float.IsNaN(sink)) miss.Add("沈める深さ"); if (gs.Count == 0) miss.Add("勾配の組"); if (float.IsNaN(depth)) miss.Add("天端の奥行");
        if (landing) { if (float.IsNaN(half)) miss.Add("踊り場の幅(隅から両側へ)"); if (float.IsNaN(lDrop)) miss.Add("踊り場の背(天端−)"); if (float.IsNaN(lCut)) miss.Add("上手の切り≤"); if (float.IsNaN(lFill)) miss.Add("下手の盛り≤"); if (float.IsNaN(bfB)) miss.Add("backfill の法"); }
        if (endBench) { if (float.IsNaN(eBehind)) miss.Add("低い端の背の小段の奥行(控えの後端+)"); if (float.IsNaN(eMin)) miss.Add("低い端の背の地盤の下限"); if (float.IsNaN(eFill)) miss.Add("低い端の盛りの最大"); if (float.IsNaN(eBf)) miss.Add("低い端の小段の先の法"); if (float.IsNaN(eDrn)) miss.Add("低い端の水の勾配"); }
        if (flatEnd) { if (float.IsNaN(reachLo)) miss.Add("低い端の届く天端(前の地表+〜)"); if (float.IsNaN(fixH)) miss.Add("水平の駒の H"); if (float.IsNaN(fixExp)) miss.Add("水平の駒の見付"); if (float.IsNaN(cvH) || float.IsNaN(cvL) || float.IsNaN(cvBf)) miss.Add("小口の土(高さ・長さ・法)"); }
        if (miss.Count > 0) { sb.AppendLine("  ★ " + key + " sodeSlope: 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 建てない"); return sb.ToString(); }
        float gMax = 0f; foreach (var g in gs) gMax = Mathf.Max(gMax, g);
        float offS = depth + 0.25f, W = 1.818f;
        int m0 = nodes.Count; var segL = new List<float>(); var segT = new List<Vector2>(); var segB = new List<Vector2>(); float Lt = 0f;
        for (int i = 0; i + 1 < m0; i++)
        {
            Vector2 a = nodes[i], b = nodes[i + 1]; float L = Vector2.Distance(a, b); Vector2 t = L > 1e-4f ? (b - a) / L : Vector2.right, nr = new Vector2(-t.y, t.x), mid = (a + b) * 0.5f;
            float yp = DesignY(mid + nr * 3f), ym = DesignY(mid - nr * 3f); segL.Add(L); segT.Add(t); segB.Add(!float.IsNaN(yp) && (float.IsNaN(ym) || yp >= ym) ? nr : -nr); Lt += L;
        }
        // s(線の始まりから・負 = 始まりの先へ延ばした所・Lt 超 = 終わりの先)→ 点と背の向き
        System.Func<float, KeyValuePair<Vector2, Vector2>> pAt = s1 =>
        {
            if (s1 <= 0f) return new KeyValuePair<Vector2, Vector2>(nodes[0] + segT[0] * s1, segB[0]);
            float acc = 0f; for (int i = 0; i < segL.Count; i++) { if (s1 <= acc + segL[i] + 1e-4f) return new KeyValuePair<Vector2, Vector2>(nodes[i] + segT[i] * (s1 - acc), segB[i]); acc += segL[i]; }
            int lI = segL.Count - 1; return new KeyValuePair<Vector2, Vector2>(nodes[lI + 1] + segT[lI] * (s1 - Lt), segB[lI]);
        };
        const float STP = 0.1f; float sMin = -6.5f, sMax = Lt + 6.5f; int nS = Mathf.CeilToInt((sMax - sMin) / STP) + 1;
        // ⭐ 一続きの線は低い端から高い端へ下がらない(単調)── 0.1m おきの生の値を隣接の違反を均す回帰(PAV)で単調にする(第41巡: 出隅で背の点が飛び 0.43 落ちた)
        System.Func<System.Func<float, float>, bool, float[]> pav = (raw, lowA) =>
        {
            var mono = new float[nS]; var val = new List<float>(); var wgt = new List<int>();
            for (int i = 0; i < nS; i++)
            {
                int ii = lowA ? i : nS - 1 - i; float v = raw(sMin + ii * STP); if (float.IsNaN(v)) v = val.Count > 0 ? val[val.Count - 1] : 0f;
                val.Add(v); wgt.Add(1);
                while (val.Count > 1 && val[val.Count - 2] > val[val.Count - 1] + 1e-5f)
                { int a2 = val.Count - 2; float nv = (val[a2] * wgt[a2] + val[a2 + 1] * wgt[a2 + 1]) / (wgt[a2] + wgt[a2 + 1]); val[a2] = nv; wgt[a2] += wgt[a2 + 1]; val.RemoveAt(a2 + 1); wgt.RemoveAt(a2 + 1); }
            }
            int k = 0; for (int b = 0; b < val.Count; b++) for (int c = 0; c < wgt[b]; c++, k++) mono[lowA ? k : nS - 1 - k] = val[b];
            return mono;
        };
        System.Func<float[], float, float> lineOf = (mono, s1) => { float f = Mathf.Clamp((s1 - sMin) / STP, 0f, nS - 1.001f); int i0 = (int)f; return Mathf.Lerp(mono[i0], mono[i0 + 1], f - i0); };
        System.Func<float, float> raw0 = s1 => { var pb = pAt(s1); return Mathf.Min(cap, DesignY(pb.Key + pb.Value * offS) + off); };
        bool lowAtA = raw0(0f) <= raw0(Lt);
        var mono0 = pav(raw0, lowAtA);
        // ⭐ 出隅の踊り場(追記 2026-10-07): 折れ 30° 以上の節点ごとに、隅の両側 half の区間を高さ Lc(元の坂の線が隅を通る値)の水平にし、背の法を Lc − lDrop の水平へ
        //   描き直す(切り ≤ lCut・盛り ≤ lFill【硬】・その先は 1:bfB で今の法へ)── 区間ごとの EdoBuild.BackBench(切りと盛り)。坂の線は描き直した背から引き直す。
        var lands = new List<EdoBuild.BackBench>(); var landS = new List<Vector2>();   // (隅の s, Lc)
        float lFillC = float.IsNaN(cLandFill) ? lFill : cLandFill;   // 追記 2026-10-09c: 踊り場の背の盛りの上限(区画の内 ── BackBench.parcel で外へ盛らない)
        if (landing)
        {
            float acc = 0f;
            for (int i = 1; i + 1 < m0; i++)
            {
                acc += segL[i - 1];
                float turn = Vector2.Angle(segT[i - 1], segT[i]); if (turn < 30f) continue;
                float sc = acc, Lc = lineOf(mono0, sc);
                if (!float.IsNaN(cLand)) Lc = cLand;   // 追記 2026-10-09c【硬】: 踊り場の高さは欄の値(上端から 2 つ目の駒で下ろした先と揃える)
                landS.Add(new Vector2(sc, Lc));
                // 前の線より前(相手の区間の見え面の前)へは切り盛りを回さない
                int iA = i - 1, iB = i;
                System.Func<Vector2, bool> keep = q => { for (int j = 0; j < segL.Count; j++) if (EdoBuild.InFrontOfFace(nodes[j], nodes[j + 1], segB[j], q, 3f)) return true; return false; };
                float hA = Mathf.Min(half, segL[iA]), hB = Mathf.Min(half, segL[iB]);
                lands.Add(new EdoBuild.BackBench { name = key + "_land" + i + "a", a = nodes[i] - segT[iA] * hA, b = nodes[i], back = segB[iA], top = Lc, drop = lDrop, w = offS, drain = 0f, bf = bfB,
                                                   maxFill = lFillC, maxCut = lCut, parcel = Poly, baseAt = DesignY, keepOut = keep });
                lands.Add(new EdoBuild.BackBench { name = key + "_land" + i + "b", a = nodes[i], b = nodes[i] + segT[iB] * hB, back = segB[iB], top = Lc, drop = lDrop, w = offS, drain = 0f, bf = bfB,
                                                   maxFill = lFillC, maxCut = lCut, parcel = Poly, baseAt = DesignY, keepOut = keep });
            }
            if (landOut != null) landOut.AddRange(lands);
        }
        // ⭐ 上端の取り付き(追記 2026-10-09【硬】・第63巡): 本線との取り付き(高い端)から最初の駒 topLen は天端 = 上端の水平。その背に上端 − tDrop の平らな小段
        //   (線から offS + tW まで ── 天端の裏石の帯の先に置く・水は石垣から離れる向きへ 1/tDrn・盛り ≤ tFill・その先 1:bfB で今の法へ)。
        //   EdoBuild.BackBench(踊り場と同じ式)で "<名>#land" に入れる ── Stage2b(地形)・Stage3b(皮の設計の地盤)・坂の線の引き直しが同じ式で読む。
        //   ⛔ 見え面の前(InFrontOfFace)と高い端の先(本線の側)へは盛らない。当たる先: sodeSlope に追記 2026-10-09 の文を持つ袖(岡部 TW_Kado_Sode)。
        float sHigh = lowAtA ? Lt : 0f; EdoBuild.BackBench topBench = null; var topSet = new HashSet<EdoBuild.BackBench>();
        if (!float.IsNaN(topLen))
        {
            var pH = pAt(sHigh); var pI = pAt(lowAtA ? Lt - topLen : topLen); Vector2 alongOut = (pH.Key - pI.Key).normalized;
            System.Func<Vector2, bool> keepT = q =>
            {
                if (Vector2.Dot(q - pH.Key, alongOut) > 0f) return true;   // 高い端の先(本線の側)
                for (int j = 0; j < segL.Count; j++) if (EdoBuild.InFrontOfFace(nodes[j], nodes[j + 1], segB[j], q, 3f)) return true;
                return false;
            };
            // ⭐ 追記 2026-10-09b(【硬】・第65巡): 盛りの上限は区画の内だけ tFill2・幅は一間を狙い tWMin まで詰めてよい【柔】・それでも届かない区間だけ小段を天端 − tDrop2 へ。
            //   走りを 0.25m ごとに「一間で届く / 詰めた幅で届く / 下げた小段」の順に PlaceBest の要領で選び、同じ選びの続きを一つの BackBench にする。
            //   届く = 小段の面(線から offS〜幅)の点の盛りが設計面から上限の内。当たる先: sodeSlope に追記 2026-10-09b の文を持つ袖(岡部 TW_Kado_Sode)。
            var parts = new List<Vector3>();   // (u0, u1, 選び 0/1/2)
            float Lb0 = Vector2.Distance(pI.Key, pH.Key); Vector2 tb0 = Lb0 > 1e-4f ? (pH.Key - pI.Key) / Lb0 : Vector2.right;
            System.Func<float, float, float, bool> reach = (u, dropX, wX) =>
            {
                for (float dn = offS; dn <= wX + 1e-3f; dn += 0.25f)
                {
                    var q = pI.Key + tb0 * u + pH.Value * dn; if (!EdoGeom.PIP(Poly, q) || keepT(q)) continue; float y0 = DesignY(q); if (float.IsNaN(y0)) continue;
                    if (cap - dropX - (dn - offS) / tDrn - y0 > tFill + 1e-3f) return false;
                }
                return true;
            };
            if (!float.IsNaN(tFill2)) tFill = tFill2;
            for (float u = 0f; u <= Lb0 + 1e-3f; u += 0.25f)
            {
                int ch = reach(u, tDrop, offS + tW) ? 0 : (!float.IsNaN(tWMin) && reach(u, tDrop, offS + tWMin) ? 1 : (!float.IsNaN(tDrop2) ? 2 : 0));
                if (parts.Count > 0 && (int)parts[parts.Count - 1].z == ch) parts[parts.Count - 1] = new Vector3(parts[parts.Count - 1].x, Mathf.Min(Lb0, u + 0.125f), ch);
                else parts.Add(new Vector3(Mathf.Max(0f, u - 0.125f), Mathf.Min(Lb0, u + 0.125f), ch));
            }
            foreach (var pt in parts)
            {
                int ch = (int)pt.z;
                var bb0 = new EdoBuild.BackBench { name = key + "_top" + (parts.Count > 1 ? "_" + ch + "_" + pt.x.ToString("F2", inv) : ""), a = pI.Key + tb0 * pt.x, b = pI.Key + tb0 * pt.y, back = pH.Value, top = cap,
                                                    drop = ch == 2 ? tDrop2 : tDrop, w = offS + (ch == 0 ? tW : tWMin), drain = 1f / tDrn, bf = float.IsNaN(bfB) ? 1.5f : bfB,
                                                    maxFill = tFill, maxCut = float.IsNaN(lCut) ? 0f : lCut, parcel = Poly, baseAt = DesignY, keepOut = keepT };
                if (topBench == null) topBench = bb0; topSet.Add(bb0);
                lands.Add(bb0);
                if (landOut != null) landOut.Add(bb0);
            }
            if (parts.Count > 1 || (parts.Count == 1 && parts[0].z > 0f))
            { var pn = new List<string>(); foreach (var pt in parts) pn.Add(pt.x.ToString("F2", inv) + "〜" + pt.y.ToString("F2", inv) + ":" + (pt.z == 0f ? "一間" : pt.z == 1f ? "幅 " + tWMin.ToString("F2", inv) : "小段 " + (cap - tDrop2).ToString("F2", inv)));
              sb.AppendLine("    上端の小段(追記 2026-10-09b・盛り ≤ " + tFill.ToString("F2", inv) + "): " + string.Join(" / ", pn.ToArray())); }
        }
        float[] mono = mono0;
        if (lands.Count > 0)
        {
            System.Func<float, float> raw1 = s1 => { var pb = pAt(s1); var q = pb.Key + pb.Value * offS; float y0 = DesignY(q); if (float.IsNaN(y0)) return float.NaN; return Mathf.Min(cap, EdoBuild.BackBenchesAt(lands, q, y0) + off); };
            mono = pav(raw1, lowAtA);
        }
        System.Func<float, float> line0 = s1 => lineOf(mono, s1);
        float sgn = lowAtA ? -1f : 1f, sEnd0 = lowAtA ? 0f : Lt;
        // 低い端を延ばす: 天端 ≤ 前の地表 + frontCut になる所 E1(⛔ 区画の外へ出ない)
        float E1 = float.NaN; string why = null;
        if (!float.IsNaN(sinkEndOverride)) E1 = 0f;   // 打ち切りの条件を当てない(延ばさない)
        else if (!dry || coverOut != null || (landOut != null && endBench && flatEnd))
            for (float d = 0f; d <= 6f + 1e-3f; d += 0.1f)
            {
                float s1 = sEnd0 + sgn * d; var pb = pAt(s1);
                if (!EdoGeom.PIP(Poly, pb.Key)) { why = "区画線 " + d.ToString("F1") + "m 先"; break; }
                float fr = SkinGround(pb.Key.x - pb.Value.x * 0.5f, pb.Key.y - pb.Value.y * 0.5f);
                if (!float.IsNaN(fr) && line0(s1) <= fr + frontCut + 1e-3f) { E1 = d; break; }
            }
        bool e1Miss = float.IsNaN(E1);
        if (e1Miss) { if (!dry) sb.AppendLine("  ★ " + key + " sodeSlope: 低い端の天端が前の地表+" + frontCut.ToString("F2") + " に 6m 以内で下がらない(" + (why ?? "") + ")── 延ばさず ③"); E1 = 0f; }
        float Ext = !float.IsNaN(sinkEndOverride) ? 0f : E1 + W;   // 届いた所から一駒(水平の駒 / 旧: 最急の勾配で沈める)・上書きのときは延ばさない
        float sE1 = sEnd0 + sgn * E1, cE1 = line0(sE1);
        // 水平の駒の天端 = その駒の前の地表(走りの中ほど)+ 見付 fixExp ── 届いた天端より上げない
        float cFlat = float.NaN, frFlat = float.NaN;
        if (flatEnd)
        {
            var pm = pAt(sE1 + sgn * W * 0.5f); frFlat = SkinGround(pm.Key.x - pm.Value.x * 0.5f, pm.Key.y - pm.Value.y * 0.5f);
            cFlat = float.IsNaN(frFlat) ? cE1 : Mathf.Min(cE1, frFlat + fixExp);
        }
        // ⭐ 低い端の水平の駒の背の小段(追記 2026-10-07c【硬】)── 駒の走り(sE1 → 端)の背を、天端 − eDrop と背の地盤の下限 eMin の高い方の平らな小段へ描き直す。
        //   奥行 = 駒の控えの後端(焼いた駒の実メッシュ ── 天端の帯の前の縁から最も奥まで)+ eBehind。盛り ≤ eFill(設計面から)・その先 1:eBf。
        //   水 1/eDrn は東(+X)へ最も近く下る向き(走りの両端か背)へ落とし、落とした先でも eMin を割らない(割るなら小段を上げ、天端 −0.05 を越えるなら落とさず ⚠)。
        //   EdoBuild.BackBench(踊り場と同じ式)で "<名>#land" に入れる ── Stage2b(地形)・Stage3b(皮の設計の地盤)・GradeQA が同じ式で読む。
        string endBenchNote = null;
        if (endBench && flatEnd && landOut != null && !e1Miss)
        {
            float back = float.NaN;
            { string pth = EdoAssets.Own.SannoNozura(fixH, 0f, 0); var vs = EdoBuild.BodyExRoofAt(pth, Vector3.zero, 0f);
              if (vs.Count > 0) { float yT = float.MinValue, zMin = float.MaxValue, zF = float.MinValue; foreach (var v in vs) { yT = Mathf.Max(yT, v.y); zMin = Mathf.Min(zMin, v.z); }
                                  foreach (var v in vs) if (v.y >= yT - 0.15f) zF = Mathf.Max(zF, v.z); back = zF - zMin; } }
            if (float.IsNaN(back)) endBenchNote = "★ 低い端の駒の控えが測れない(" + EdoAssets.Own.SannoNozura(fixH, 0f, 0) + ")── 背の小段を描かない";
            else
            {
                var pO = pAt(sEnd0 + sgn * Ext); var pI = pAt(sE1); Vector2 bkN = pO.Value, al = (pO.Key - pI.Key).normalized;
                float wE = back + eBehind, yb = Mathf.Max(cFlat - eDrop, eMin);
                // 水の向き: 東(+X)へ最も近く下る ── 端の外(a = 端の外)・端の内(a = 内)・背
                Vector2 east = Vector2.right; float dOut = Vector2.Dot(al, east), dIn = -dOut, dBk = Vector2.Dot(bkN, east);
                float run = Vector2.Distance(pO.Key, pI.Key); string dName; float fall;
                Vector2 ea = pO.Key, eb = pI.Key; float drnB = 0f, drnA = 0f;
                if (dBk >= dOut && dBk >= dIn) { dName = "背"; fall = wE / eDrn; drnB = 1f / eDrn; }
                else if (dOut >= dIn) { dName = "端の外"; fall = run / eDrn; drnA = 1f / eDrn; }
                else { dName = "端の内"; fall = run / eDrn; drnA = 1f / eDrn; ea = pI.Key; eb = pO.Key; }
                if (yb - fall < eMin - 1e-4f) { float yb2 = eMin + fall; if (yb2 <= cFlat - 0.05f + 1e-4f) yb = yb2; else { drnA = 0f; drnB = 0f; dName = "⚠ 落とせない(小段を上げると天端 −0.05 を越える)"; } }
                System.Func<Vector2, bool> keepE = q => { for (int j = 0; j < segL.Count; j++) if (EdoBuild.InFrontOfFace(nodes[j], nodes[j + 1], segB[j], q, 3f)) return true; return false; };
                var eb0 = new EdoBuild.BackBench { name = key + "_lowEnd", a = ea, b = eb, back = bkN, top = cFlat, drop = cFlat - yb, w = wE, drain = drnB, drainAlong = drnA, bf = eBf,
                                                   maxFill = eFill, maxCut = 0f, parcel = Poly, baseAt = DesignY, keepOut = keepE };
                landOut.Add(eb0);
                endBenchNote = "低い端の背の小段: 駒の走り " + run.ToString("F2") + "m・高さ " + yb.ToString("F2") + "(天端 " + cFlat.ToString("F2") + " − " + eDrop.ToString("F2") + " と下限 " + eMin.ToString("F2") + " の高い方)"
                             + "・奥行 " + wE.ToString("F2") + "(控えの後端 " + back.ToString("F2") + " + " + eBehind.ToString("F2") + ")・水 1/" + eDrn.ToString("F0") + " を" + dName + "へ・盛り ≤ " + eFill.ToString("F2") + "・その先 1:" + eBf.ToString("F1");
            }
        }
        if (flatEnd && coverOut != null && !e1Miss)
        { var pe = pAt(sEnd0 + sgn * Ext); var pa = pAt(sEnd0); coverOut.Add(new SodeEndCover { key = key, end = pe.Key, away = (pe.Key - pa.Key).normalized * (Vector2.Distance(pe.Key, pa.Key) > 1e-3f ? 1f : 0f), h = cvH, len = cvL, bf = cvBf, rise = cvRise, flat = cvFlat, side = cvSide, drn = float.IsNaN(cvDrn) ? 0f : 1f / cvDrn, buryTop = buryTop, burySide = burySide, buryMin = buryMin }); }
        if (dry) { if (endBenchNote != null) sb.AppendLine("    " + endBenchNote); return sb.ToString(); }
        System.Func<float, float> crest = s1 =>
        {
            if (sgn < 0f ? s1 < sE1 : s1 > sE1) return flatEnd ? cFlat : cE1 - gMax * Mathf.Abs(s1 - sE1);
            float v = line0(s1);
            foreach (var ls in landS) if (Mathf.Abs(s1 - ls.x) <= half + 1e-3f) v = ls.y;   // 踊り場は水平(高さ = 元の坂の線が隅を通る値)
            // 上端の取り付き(追記 2026-10-09【硬】): 最初の駒は上端の水平・2 つ目の駒から一駒 tG の勾配で坂の線へ戻す(PlaceBest が tG の駒を選ぶ)
            //   ⭐ 坂の線より上へ残す量は「天端と背の地盤の差 ≤ maxDiff【硬】」の内(線 = 背 + off ⇒ 線 + (maxDiff − off − 0.05))で頭打ちし、2 駒で線へ戻しきる(線形に 0 へ)──
            //   背の法が一駒 tG より急に落ちる所は線へ早く戻す(柔の勾配より硬い差を先に守る・⛔ 坂の線より上の天端を袖の全長へ引きずらない ── 第63巡の1回目で 49/50 点が差 1.84 まで超えた)
            if (!float.IsNaN(topLen))
            {
                float dh = Mathf.Abs(s1 - sHigh);
                if (dh <= topLen + 1e-3f) v = cap;
                else if (!float.IsNaN(cTo) && landS.Count > 0)
                {
                    // 追記 2026-10-09c【硬・継ぎ目に段を作らない】: 上端の水平の先から、最も近い出隅の踊り場の縁まで cap → cTo を一直線に下ろす
                    //   (2 つ目の駒 = 勾配の駒 G−cDrop/1.818 を PlaceBest が選ぶ)。踊り場の縁より先は踊り場の水平(上で入れた v)のまま。
                    float dL = float.MaxValue; foreach (var ls in landS) dL = Mathf.Min(dL, Mathf.Abs(sHigh - ls.x) - half);
                    if (dh < dL && dL > topLen + 0.1f) v = cap + (cTo - cap) * (dh - topLen) / (dL - topLen);
                }
                else { float fade = Mathf.Clamp01(1f - (dh - topLen) / (2f * topLen)); v = Mathf.Min(cap, Mathf.Max(v, Mathf.Min(cap - tG * (dh - topLen) / topLen, v + Mathf.Max(0f, maxDiff - off - 0.05f) * fade))); }
            }
            return v;
        };
        // 区間: 低い端の区間を Ext だけ延ばす
        float acc2 = 0f; string firstName = null;
        for (int i = 0; i < segL.Count; i++)
        {
            Vector2 a = nodes[i], b = nodes[i + 1]; float sA = acc2; acc2 += segL[i];
            if (segL[i] < 0.05f) continue;
            float ext0 = (lowAtA && i == 0) ? Ext : 0f, ext1 = (!lowAtA && i == segL.Count - 1) ? Ext : 0f;
            Vector2 aa = a - segT[i] * ext0, bb = b + segT[i] * ext1; float sA0 = sA - ext0;
            var ns = new EdoBuild.NozuraSeg { name = key + "_" + i + "_0", a = aa, b = bb, crestAt = sl => crest(sA0 + sl), flow = true, face = -segB[i] };   // 坂の一続き ⇒ 区間の継ぎ目を段の境に数えない・見え面 = 背の逆(⛔ 低い端の先で背へ向けない)
            int e = (lowAtA && i == 0) ? 0 : (!lowAtA && i == segL.Count - 1) ? 1 : -1;
            if (e >= 0)
            {
                ns.noAbut[e] = true; firstName = ns.name;
                if (flatEnd) ns.fixHEnd[e] = fixH;   // 低い端の一駒は水平の焼いた H(⛔ 勾配の駒を傾けて刺さない)
                else ns.endSink[e] = sink;
            }
            // 上端の取り付き(追記 2026-10-09【硬】): 高い端の区間の高い端から topLen は水平の駒(⛔ 勾配の駒を選ばせない ── 第63巡は G−275 で 21.24→20.80 に傾き本線より 0.23 出た)
            if (!float.IsNaN(topLen)) { int eh = lowAtA ? (i == segL.Count - 1 ? 1 : -1) : (i == 0 ? 0 : -1); if (eh >= 0) ns.flatEnd[eh] = topLen; }
            nozSegs.Add(ns);
        }
        var ln = new List<Vector2>(); var bk = new List<Vector2>();
        for (float s1 = Mathf.Min(sE1, 0f); s1 <= Mathf.Max(sE1, Lt) + 1e-3f; s1 += 0.25f) { var pb = pAt(s1); ln.Add(pb.Key); bk.Add(pb.Value); }
        chk.Add(new SodeSlopeCheck { key = key, line = ln, back = bk, maxDiff = maxDiff, depth = depth });
        sb.AppendLine("  袖の坂 " + key + "(sodeSlope): 天端 = 背の法(線から " + offS.ToString("F2") + " の設計面" + (lands.Count > 0 ? "・踊り場の小段で描き直した背" : "") + ")+" + off.ToString("F2") + "・上端 " + cap.ToString("F1")
                    + "・天端 " + line0(lowAtA ? 0f : Lt).ToString("F2") + "→" + line0(lowAtA ? Lt : 0f).ToString("F2") + "(上の端 " + (line0(lowAtA ? Lt : 0f) < cap - 0.01f ? "⚠ 背の法 +" + off.ToString("F2") + " が上端 " + cap.ToString("F1") + " に届かない" : "= 上端") + ")"
                    + "・勾配の組 {" + string.Join(", ", gs.ConvertAll(g => g.ToString("0.###", inv)).ToArray()) + "} の最も近い駒(柔)");
        foreach (var ls in landS)
        {
            float mc = 0f, mf = 0f; Vector2 cAt = Vector2.zero, fAt = Vector2.zero; int nCap = 0;
            // 踊り場の背の切り・盛り(設計面から)と、上限で止まって水平に届かない点(⚠)を 0.25m で測る
            foreach (var bb in lands)
            {
                if (topSet.Contains(bb)) continue;   // 上端の取り付きの小段は下で別に刷る
                Vector2 t = (bb.b - bb.a).normalized; float Lb = Vector2.Distance(bb.a, bb.b);
                for (float u = 0f; u <= Lb + 1e-3f; u += 0.25f) for (float dn = 0.25f; dn <= offS + 1e-3f; dn += 0.25f)
                {
                    var q = bb.a + t * u + bb.back * dn; float y0 = DesignY(q); if (float.IsNaN(y0)) continue; float y1 = EdoBuild.BackBenchesAt(lands, q, y0);
                    if (y0 - y1 > mc) { mc = y0 - y1; cAt = q; } if (y1 - y0 > mf) { mf = y1 - y0; fAt = q; }
                    if (Mathf.Abs(y1 - (bb.top - bb.drop)) > 0.02f) nCap++;
                }
            }
            sb.AppendLine("    出隅の踊り場: 隅 s=" + ls.x.ToString("F2") + " ±" + half.ToString("F2") + " を天端 " + ls.y.ToString("F2") + " の水平に・背の法を " + (ls.y - lDrop).ToString("F2") + " の水平へ(切り 最大 " + mc.ToString("F2") + " @(" + cAt.x.ToString("F1") + ", " + cAt.y.ToString("F1") + ")・盛り 最大 " + mf.ToString("F2") + " @(" + fAt.x.ToString("F1") + ", " + fAt.y.ToString("F1") + ")・硬 ≤ " + lCut.ToString("F2") + "/" + lFill.ToString("F2") + ")"
                          + (nCap > 0 ? " ⚠ 上限で止まり水平に届かない点 " + nCap : ""));
        }
        { var prof = new System.Text.StringBuilder(); for (float s1 = 0f; s1 <= Lt + 1e-3f; s1 += 0.9f) prof.Append(" " + s1.ToString("F1") + ":" + line0(s1).ToString("F2") + "/" + crest(s1).ToString("F2")); sb.AppendLine("    線/天端(s:坂の線/天端):" + prof); }
        if (topBench != null)
        {
            // 上端の取り付きの小段の盛り・切り(設計面から)と、上端の天端・2 つ目の駒からの勾配
            float mc = 0f, mf = 0f; Vector2 fAt = Vector2.zero; int nCap = 0; Vector2 t = (topBench.b - topBench.a).normalized; float Lb = Vector2.Distance(topBench.a, topBench.b);
            for (float u = 0f; u <= Lb + 1e-3f; u += 0.25f) for (float dn = offS; dn <= topBench.w + 1e-3f; dn += 0.25f)
            {
                var q = topBench.a + t * u + topBench.back * dn; float y0 = DesignY(q); if (float.IsNaN(y0)) continue; float y1 = EdoBuild.BackBenchesAt(lands, q, y0);
                mc = Mathf.Max(mc, y0 - y1); if (y1 - y0 > mf) { mf = y1 - y0; fAt = q; }
                if (y1 < topBench.top - topBench.drop - (dn - offS) * topBench.drain - 0.02f) nCap++;
            }
            sb.AppendLine("    上端の取り付き(追記 2026-10-09): 高い端から " + topLen.ToString("F2") + "m は天端 " + cap.ToString("F2") + " の水平・その先は" + (!float.IsNaN(cTo) ? "(追記 2026-10-09c)踊り場の縁まで " + cap.ToString("F2") + "→" + cTo.ToString("F2") + " を一直線に・踊り場 " + cLand.ToString("F2") + "・盛り ≤ " + cLandFill.ToString("F2") + " (" : "一駒 −" + tG.ToString("F2") + " で坂の線へ(") + crest(sHigh - (lowAtA ? 1f : -1f) * (topLen * 2f)).ToString("F2") + " @2駒目の終わり)"
                          + "・背の小段 " + (cap - tDrop).ToString("F2") + "(線から " + offS.ToString("F2") + "〜" + topBench.w.ToString("F2") + "・水 1/" + tDrn.ToString("F0") + " を背へ)盛り 最大 " + mf.ToString("F2") + " @(" + fAt.x.ToString("F1") + ", " + fAt.y.ToString("F1") + ")・切り 最大 " + mc.ToString("F2") + "(硬 ≤ " + tFill.ToString("F2") + ")"
                          + (nCap > 0 ? " ⚠ 上限で止まり小段に届かない点 " + nCap : ""));
        }
        if (flatEnd)
            sb.AppendLine("    低い端: 線の端から " + E1.ToString("F2") + "m で天端 " + cE1.ToString("F2") + " ≤ 前の地表+" + reachHi.ToString("F2") + " ⇒ そこから水平の駒 H" + (fixH * 1000f).ToString("0000") + " を一駒(天端 " + cFlat.ToString("F2") + " = 前の地表 " + (float.IsNaN(frFlat) ? "—" : frFlat.ToString("F2")) + " + 見付 " + fixExp.ToString("F2") + ")・小口の土 高さ " + cvH.ToString("F2") + "・長さ " + cvL.ToString("F2") + "・1:" + cvBf.ToString("0.0") + " は Stage3b(" + firstName + ")");
        else
            sb.AppendLine("    低い端(①): 線の端から " + E1.ToString("F2") + "m で天端 " + cE1.ToString("F2") + " ≤ 前の地表+" + frontCut.ToString("F2") + " ⇒ そこから一駒(" + W.ToString("F2") + ")を勾配 " + gMax.ToString("F2") + " で沈める・小口の沈み ≥ " + sink.ToString("F2") + " を据えた後に測る(" + firstName + ")");
        return sb.ToString();
    }

    /// <summary>**石段の脇の返しの背(指図 kaidans[].sideBack)と、段の土留めの両端の延長の背(指図 terraceWalls[].endsBack)**の小段
    /// (EDO-0502 第60巡・普請方の設計 5d33ffe5 ── 第59巡の隙 62 の残り)。どちらも BackBench の型(盛るだけ)で、上限だけ欄から読む。
    /// 線は据えと同じ器で解く: 脇の返し = <see cref="StairGaps"/>(StairSideCrestLines)の _Side の区間・延長 = <see cref="EndExtensions"/>。
    /// sideBack: 小段 = 天端 − drop、奥行 = max(一間【柔】, 控えの後端 + 下限【硬】)、石段から離れる向きへ 1/x、先は 1:bf、盛り ≤ 上限【硬】、道の路盤へは盛らない【硬】。
    /// endsBack: 小段 = 絶対値(天端 − 0.15)、奥行 = 延長の見え面から長屋の妻の面(実メッシュ)+ 床下へ差し込み【柔】、走りの外へ盛らない・
    /// 道の側へ 1/x(天端と背の差 ≤ 上限【硬】が勝つ ── 勾配を緩めて ⚠)。区画の外(parcel)と前(溜りの床)は BackBenchAt が触らない。
    /// "&lt;名&gt;#side" / "&lt;名&gt;#endsBack" に入れる ── Stage2b(地形)・Stage3b(皮の設計の地盤)・GradeQA が同じ式で読む。
    /// 当たる先: sideBack/endsBack を持つ石段・段の土留め(岡部 K_Dan1・K_Dan2 × TW_Kado_Shumen、TW_Higashi_Tsuyo)。</summary>
    static void StairSideAndEndBacks(Dictionary<string, List<KeyValuePair<int, EdoBuild.BackBench>>> res, System.Text.StringBuilder note, float depth, System.Func<string, string, float> rx)
    {
        var kaiRoot = GameObject.Find(GN) == null ? null : GameObject.Find(GN).transform.Find("Fuzoku/Kaidan");
        var kakoi = GameObject.Find(GN) == null ? null : GameObject.Find(GN).transform.Find("Kakoi");
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null || S(Get(w, "mode")) != "fill") continue;
            string nm = S(Get(w, "name")); string part = S(Get(w, "part")); string key = nm + (part != null ? "_" + part : "");
            Dictionary<string, object> sw = null;
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
            var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            float top = F(Get(w, "top")); var tl = A(Get(w, "tops")); if (tl != null && tl.Count > 0) top = F(tl[0]);
            // ── sideBack(石段の欄)── この土留めの口を切る石段のどれかが持てば、その口の脇の返しの背
            string sbT = null, sbBy = null;
            foreach (var g in A(Get(w, "gaps")) ?? new List<object>())
            {
                string by = S(Get(O(g), "by")); if (by == null || !by.StartsWith("K_")) continue;
                foreach (var ko in A(D["kaidans"]) ?? new List<object>()) { var kd = O(ko); if (kd != null && S(Get(kd, "name")) == by && Get(kd, "sideBack") != null) { sbT = S(Get(kd, "sideBack")); sbBy = by; } }
            }
            if (sbT != null && kaiRoot != null)
            {
                float drop = rx(sbT, @"天端\s*[−\-]\s*([0-9.]+)"), maxFill = rx(sbT, @"盛りの上限\s*([0-9.]+)"), minBack = rx(sbT, @"控えの後端\s*\+\s*([0-9.]+)"),
                      bf = rx(sbT, @"1\s*:\s*([0-9.]+)"), drn = rx(sbT, @"1\s*/\s*([0-9.]+)");
                bool ken1 = sbT.Contains("奥行は一間");
                var miss = new List<string>();
                if (float.IsNaN(drop)) miss.Add("天端からの下げ"); if (float.IsNaN(maxFill)) miss.Add("盛りの上限"); if (float.IsNaN(minBack)) miss.Add("控えの後端からの下限");
                if (float.IsNaN(bf)) miss.Add("先の法"); if (float.IsNaN(drn)) miss.Add("水の勾配"); if (!ken1) miss.Add("奥行の狙い(一間)"); if (float.IsNaN(depth)) miss.Add("avoid.dodomeCrestDepthM[野面の乱積み]");
                if (miss.Count > 0) { if (note != null) note.AppendLine("  ★ " + sbBy + ".sideBack: 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 盛らない"); }
                else
                {
                    var keepCorner = new List<Vector2>(_sideCorner);
                    var segs = new List<EdoBuild.NozuraSeg>();
                    StairGaps(key, w, nodes, top, kaiRoot, segs, new System.Text.StringBuilder());
                    _sideCorner.Clear(); _sideCorner.AddRange(keepCorner);
                    float wT = C("ken"), wMin = depth + minBack, wUse = Mathf.Max(wT, wMin);
                    // ⭐ 本線(口を切られた土留めの線)の見え面の前へ盛らない【硬】── 脇の返しの低い端は本線の見え面に来るので、端の先の法(1:bf)が
                    //   本線の前の地盤(門の内)へ回り込む。最も近い本線の区間の低い側(設計の地盤 DesignY で測る)を篩う。
                    //   (第62巡: K_Dan1 の左の返しの背の端の法が門の内 16.50 の上に 17.2〜18.0 の土の箱を立てた ── 指図「法尻を道の面にも石段にもかけない」)
                    //   当たる先: sideBack を持つ石段の口(岡部 K_Dan1・K_Dan2)。⛔ 帯の深さで切らない(法の届く先は 盛りの上限×bf を超える)
                    var mA = new List<Vector2>(); var mB = new List<Vector2>(); var mF = new List<Vector2>();
                    for (int i = 0; i + 1 < nodes.Count; i++)
                    {
                        Vector2 pa = nodes[i], pb = nodes[i + 1]; float L0 = Vector2.Distance(pa, pb); if (L0 < 1e-3f) continue;
                        Vector2 tn = (pb - pa) / L0, nr = new Vector2(-tn.y, tn.x), md = (pa + pb) * 0.5f;
                        float hp = DesignY(md + nr * 2f), hm = DesignY(md - nr * 2f);
                        mA.Add(pa); mB.Add(pb); mF.Add(hp < hm ? nr : -nr);
                    }
                    System.Func<Vector2, bool> frontOfMain = q =>
                    {
                        float bd = float.MaxValue; bool fr = false;
                        for (int i = 0; i < mA.Count; i++)
                        {
                            Vector2 ab = mB[i] - mA[i]; float tt = Mathf.Clamp01(Vector2.Dot(q - mA[i], ab) / ab.sqrMagnitude); Vector2 c = mA[i] + ab * tt;
                            float d = Vector2.Distance(q, c); if (d < bd) { bd = d; fr = Vector2.Dot(q - c, mF[i]) > 0.05f; }
                        }
                        return fr;
                    };
                    var list = new List<KeyValuePair<int, EdoBuild.BackBench>>();
                    foreach (var sg in segs)
                    {
                        if (!sg.name.Contains("_Side")) continue;
                        var bk = new EdoBuild.BackBench
                        {
                            name = sg.name + "_sideBack", a = sg.a, b = sg.b, back = -sg.face, top = top, drop = drop, w = wUse,
                            drain = 1f / drn, bf = bf, maxFill = maxFill, parcel = Poly, baseAt = DesignY
                        };
                        bk.keepOut = q => !float.IsNaN(RampProfileAt(q)) || frontOfMain(q);   // 法尻を道の路盤へ・本線の見え面の前へかけない【硬】
                        list.Add(new KeyValuePair<int, EdoBuild.BackBench>(-1, bk));
                    }
                    if (list.Count > 0) res[key + "#side"] = list;
                    if (note != null) note.AppendLine("    sideBack " + key + " × " + sbBy + ": 脇の返しの区間 " + list.Count + "・小段 天端 " + top.ToString("F2") + " − " + drop.ToString("F2") + "・奥行 " + wUse.ToString("F2")
                        + (wUse > wT + 1e-3f ? " ⚠ 狙い一間 " + wT.ToString("F2") + " を下限(控え " + depth.ToString("F2") + " + " + minBack.ToString("F2") + ")が越える" : "(狙い一間・下限 " + wMin.ToString("F2") + ")")
                        + "・石段から離れる向きへ 1/" + drn.ToString("F0") + "・先 1:" + bf.ToString("F1") + "・盛り ≤ " + maxFill.ToString("F2") + "・道の路盤へ盛らない");
                }
            }
            // ── endsBack(土留めの欄)── 両端の延長の背
            string ebT = sw == null ? null : S(Get(sw, "endsBack"));
            if (ebT != null)
            {
                float abs = rx(ebT, @"絶対値\s*([0-9.]+)"), under = rx(ebT, @"床下へ[^(（]*[\(（]\s*([0-9.]+)"), dMax = rx(ebT, @"差\s*≤\s*([0-9.]+)"), drn = rx(ebT, @"1\s*/\s*([0-9.]+)"),
                      bfE = float.NaN;
                var miss = new List<string>();
                if (float.IsNaN(abs)) miss.Add("背の地盤の絶対値"); if (float.IsNaN(under)) miss.Add("床下への差し込み"); if (float.IsNaN(dMax)) miss.Add("天端と背の差の上限"); if (float.IsNaN(drn)) miss.Add("水の勾配");
                if (miss.Count > 0) { if (note != null) note.AppendLine("  ★ " + key + ".endsBack: 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 盛らない"); continue; }
                var exs = EndExtensions(nm, w, nodes, top, key, new System.Text.StringBuilder(), null);
                var list = new List<KeyValuePair<int, EdoBuild.BackBench>>();
                foreach (var ex in exs)
                {
                    Vector2 back = -ex.lowD, t = (ex.pe - ex.pf).normalized; float L = Vector2.Distance(ex.pe, ex.pf);
                    // 長屋の妻の面(実メッシュ・天端〜+2.0 の帯)── 延長の走りの内で背の向きに最も近い頂点
                    float gable = float.NaN; string gN = null;
                    if (kakoi != null) foreach (Transform c in kakoi)
                    {
                        if (!c.gameObject.activeInHierarchy || !EdoBuild.IsNagayaBody(c.gameObject)) continue;
                        var rb = EdoBuild.RB(c.gameObject); if (Vector2.Distance(new Vector2(rb.center.x, rb.center.z), (ex.pe + ex.pf) * 0.5f) > 40f) continue;
                        foreach (var v in EdoBuild.Body(c, 4000))
                        {
                            if (v.y < top || v.y > top + 2.0f) continue;
                            Vector2 r0 = new Vector2(v.x, v.z) - ex.pf; float s = Vector2.Dot(r0, t), d = Vector2.Dot(r0, back);
                            if (s < -0.1f || s > L + 0.1f || d < 0.05f || d > 15f) continue;
                            if (float.IsNaN(gable) || d < gable) { gable = d; gN = c.name; }
                        }
                    }
                    if (float.IsNaN(gable)) { if (note != null) note.AppendLine("  ⚠ " + ex.name + ".endsBack: 背の 15m の内に長屋の妻が無い ── 盛らない"); continue; }
                    float dAlong = Mathf.Min(1f / drn, Mathf.Max(0f, dMax - (top - abs)) / Mathf.Max(0.1f, L));   // 道の端で天端と背の差 ≤ 上限【硬】が勝つ
                    bfE = 1.5f;   // ⚠ 欄に先の法が無い ── 床下の奥(見えない所)だけに効く。sideBack と同じ 1:1.5
                    var bk = new EdoBuild.BackBench
                    {
                        name = ex.name + "_endsBack", a = ex.pf, b = ex.pe, back = back, top = abs, drop = 0f, w = gable + under, drain = 0f, drainAlong = dAlong,
                        bf = bfE, maxFill = 99f, parcel = Poly, baseAt = DesignY, noEndSpill = true
                    };
                    list.Add(new KeyValuePair<int, EdoBuild.BackBench>(-1, bk));
                    if (note != null) note.AppendLine("    endsBack " + ex.name + ": 長さ " + L.ToString("F2") + "・背 " + abs.ToString("F2") + "(絶対値)・奥行 = 妻の面 " + gable.ToString("F2") + "(" + gN + ")+ 床下 " + under.ToString("F2")
                        + "・道の側へ 1/" + (dAlong > 1e-5f ? (1f / dAlong).ToString("F1") : "∞") + (dAlong < 1f / drn - 1e-5f ? " ⚠ 指図の 1/" + drn.ToString("F0") + " では道の端で天端との差 " + (top - abs + L / drn).ToString("F2") + " > " + dMax.ToString("F2") + "【硬】⇒ 緩めた" : "")
                        + "・走りの外へ盛らない・奥の先 1:1.5 ⚠ 欄に無い(床下)");
                }
                if (list.Count > 0) res[key + "#endsBack"] = list;
            }
        }
    }

    static Dictionary<string, List<KeyValuePair<int, EdoBuild.BackBench>>> SodeBenches(System.Text.StringBuilder note)
    {
        var res = new Dictionary<string, List<KeyValuePair<int, EdoBuild.BackBench>>>();
        float depth = float.NaN;
        System.Action<object> find = null;
        find = o =>
        {
            var d = o as Dictionary<string, object>;
            if (d != null) { if (d.ContainsKey("dodomeCrestDepthM")) { var dd = O(d["dodomeCrestDepthM"]); if (dd != null && dd.ContainsKey("野面の乱積み")) depth = F(dd["野面の乱積み"]); } foreach (var v in d.Values) if (float.IsNaN(depth)) find(v); return; }
            var l = o as List<object>; if (l != null) foreach (var v in l) if (float.IsNaN(depth)) find(v);
        };
        find(D);
        System.Func<string, string, float> rx = (txt, pat) =>
        {
            var m = System.Text.RegularExpressions.Regex.Match(txt ?? "", pat);
            return m.Success ? float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : float.NaN;
        };
        if (_sideEndBenches.Count > 0) { var lse = new List<KeyValuePair<int, EdoBuild.BackBench>>(); foreach (var bk in _sideEndBenches) lse.Add(new KeyValuePair<int, EdoBuild.BackBench>(-1, bk)); res["sideEnd#land"] = lse; }
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null || S(Get(w, "mode")) != "sode") continue;   // 線と mode は算出物・文は指図
            string nm = S(Get(w, "name"));
            Dictionary<string, object> sw = null;
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
            if (sw == null || Get(sw, "backfill") == null) continue;
            // 指図 sodeSlope(2026-10-07)の袖は段に割らず坂の一続き(SodeSlopeSegs)── 天端は背の法 +0.15 なので小段の裏込めは要らない
            //   ⭐ 第42巡(追記 2026-10-07): 出隅の踊り場の背だけは水平の小段(切り・盛り)に描き直す ── "<名>#land" に入れ、Stage2b(地形)・Stage3b(皮の設計の地盤)・GradeQA が同じ式で読む
            if (Get(sw, "sodeSlope") != null)
            {
                var lnS = A(Get(w, "line")); var lands = new List<EdoBuild.BackBench>();
                if (lnS != null && lnS.Count >= 2)
                {
                    var nodesS = new List<Vector2>(); foreach (var q in lnS) { var p = A(q); nodesS.Add(new Vector2(F(p[0]), F(p[1]))); }
                    string r0 = SodeSlopeSegs(nm, nodesS, S(Get(sw, "sodeSlope")), null, null, lands, null);
                    if (note != null && r0.Length > 0) note.Append(r0);
                }
                if (lands.Count > 0) { var ll = new List<KeyValuePair<int, EdoBuild.BackBench>>(); foreach (var bk in lands) ll.Add(new KeyValuePair<int, EdoBuild.BackBench>(-1, bk)); res[nm + "#land"] = ll; }
                if (note != null) note.AppendLine("    " + nm + ": sodeSlope ── 段の割りと背の小段を取らない(坂の一続き)" + (lands.Count > 0 ? "・出隅の踊り場の背の小段 " + lands.Count : ""));
                continue;
            }
            string top = S(Get(sw, "top")), bfT = S(Get(sw, "backfill")), drT = S(Get(sw, "backDrain"));
            float step = rx(top, @"([0-9.]+)\s*刻み"), maxDrop = rx(top, @"下がる量は\s*([0-9.]+)\s*以下");
            float drop = rx(bfT, @"天端\s*[−\-]\s*([0-9.]+)"), wKen = rx(bfT, @"幅\s*([0-9.]+)\s*間"), bf = rx(bfT, @"法\s*1\s*:\s*([0-9.]+)"), maxFill = rx(bfT, @"盛りは\s*([0-9.]+)\s*以下");
            float drn = rx(drT, @"1\s*/\s*([0-9.]+)");
            var miss = new List<string>();
            if (float.IsNaN(step)) miss.Add("top の刻み"); if (float.IsNaN(maxDrop)) miss.Add("top の下がる量"); if (float.IsNaN(drop)) miss.Add("backfill の天端からの下げ");
            if (float.IsNaN(wKen)) miss.Add("backfill の幅"); if (float.IsNaN(bf)) miss.Add("backfill の法"); if (float.IsNaN(maxFill)) miss.Add("backfill の盛りの上限");
            if (float.IsNaN(drn)) miss.Add("backDrain の勾配"); if (float.IsNaN(depth)) miss.Add("avoid.dodomeCrestDepthM[野面の乱積み]");
            if (miss.Count > 0) { if (note != null) note.AppendLine("  ★ " + nm + ": 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 天端の割りと裏込めをしない"); continue; }
            var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            var list = new List<KeyValuePair<int, EdoBuild.BackBench>>();
            // 区間ごとの線・背の向き(背 = 設計面の高い側)
            var segA = new List<Vector2>(); var segT = new List<Vector2>(); var segBack = new List<Vector2>(); var segL = new List<float>();
            for (int i = 0; i + 1 < nodes.Count; i++)
            {
                Vector2 a = nodes[i], b = nodes[i + 1]; float L = Vector2.Distance(a, b);
                Vector2 t = L > 1e-4f ? (b - a) / L : Vector2.right, nrm = new Vector2(-t.y, t.x), mid = (a + b) * 0.5f;
                float yp = DesignY(mid + nrm * 3f), ym = DesignY(mid - nrm * 3f);
                segA.Add(a); segT.Add(t); segL.Add(L); segBack.Add((!float.IsNaN(yp) && (float.IsNaN(ym) || yp >= ym)) ? nrm : -nrm);
            }
            float offS = depth + 0.25f;
            string rsT = S(Get(sw, "runSplit"));
            if (!string.IsNullOrEmpty(rsT) && rsT.Contains("等高線"))
            {
                // ⭐ runSplit(指図 2026-10-06・第32巡): run の境は背の法が 0.5 刻みの等高線を横切る所(⛔ 節点で切らない)・天端は刻みの倍数だけ・
                //   0.5 未満の run は高い側へ含める(EdoBuild.RunsByContour)。run を節点の区間で切り分けて同じ天端の区間として渡す(出隅・一直線で継ぐ)
                float Ltot = 0f; foreach (var l0 in segL) Ltot += l0;
                Func<float, int> segOf = s1 => { float acc = 0f; for (int i = 0; i < segL.Count; i++) { if (s1 <= acc + segL[i] + 1e-4f) return i; acc += segL[i]; } return segL.Count - 1; };
                Func<int, float> segS0 = i1 => { float acc = 0f; for (int i = 0; i < i1; i++) acc += segL[i]; return acc; };
                Func<float, float> backAtS = s1 => { int i = segOf(s1); float u = s1 - segS0(i); return DesignY(segA[i] + segT[i] * u + segBack[i] * offS); };
                var runsC = EdoBuild.RunsByContour(Ltot, backAtS, step, 0.5f);
                if (note != null) { var tx = new List<string>(); foreach (var r in runsC) tx.Add(r.x.ToString("F2") + "〜" + r.y.ToString("F2") + "@" + r.z.ToString("F1")); note.AppendLine("    runSplit " + nm + ": 等高線で " + runsC.Count + " run(" + string.Join(" / ", tx.ToArray()) + ")"); }
                foreach (var r in runsC)
                    for (int i = 0; i < segL.Count; i++)
                    {
                        float s0 = segS0(i), x0 = Mathf.Max(r.x, s0), x1 = Mathf.Min(r.y, s0 + segL[i]);
                        if (x1 - x0 < 0.05f) continue;
                        list.Add(new KeyValuePair<int, EdoBuild.BackBench>(i, new EdoBuild.BackBench
                        {
                            name = nm + "_" + i, a = segA[i] + segT[i] * (x0 - s0), b = segA[i] + segT[i] * (x1 - s0), back = segBack[i], top = r.z, drop = drop, w = wKen * C("ken"),
                            drain = 1f / drn, bf = bf, maxFill = maxFill, parcel = Poly, baseAt = DesignY
                        }));
                    }
                res[nm] = list;
                continue;
            }
            for (int i = 0; i + 1 < nodes.Count; i++)
            {
                Vector2 a = nodes[i], b = nodes[i + 1]; float L = Vector2.Distance(a, b); if (L < 0.3f) continue;
                Vector2 t = segT[i], back = segBack[i];
                float off = offS;
                var runs = EdoBuild.RunsByBackSlope(L, sl => DesignY(a + t * sl + back * off), step, maxDrop, 0.5f);
                foreach (var r in runs)
                    list.Add(new KeyValuePair<int, EdoBuild.BackBench>(i, new EdoBuild.BackBench
                    {
                        name = nm + "_" + i, a = a + t * r.x, b = a + t * r.y, back = back, top = r.z, drop = drop, w = wKen * C("ken"),
                        drain = 1f / drn, bf = bf, maxFill = maxFill, parcel = Poly, baseAt = DesignY
                    }));
            }
            res[nm] = list;
        }
        // ⭐ 端の返し(指図 terraceWalls[].returnTop/returnBackfill/returnBackDrain・EDO-0502 第22巡 TW_Minami_Koshi)── 袖と同じ型で、
        //   出隅の駒の先から背の地盤(妻の外)で天端を割り(RunsByBackSlope・run は 1 駒より短くしない)、各 run の背に小段(BackBench)。"<名>#ret" に入れる。
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null) continue; string nm = S(Get(w, "name"));
            Dictionary<string, object> sw = null;
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
            if (sw == null || Get(sw, "returnTop") == null || Get(sw, "returnBackfill") == null) continue;
            string top = S(Get(sw, "returnTop")), bfT = S(Get(sw, "returnBackfill")), drT = S(Get(sw, "returnBackDrain")), enT = S(Get(sw, "returnEnd"));
            // 第24巡(76ce2fd6): 「天端と背の地盤の差が 0.9 を超える所で run を切る」「表の地表と背の地盤の差が 0.6 未満になった所で終える」
            //   「run の長さに下限は置かない(短い run は余りを上手へ重ねて埋める)」・returnEnd の土羽の法と 1 間
            float step = rx(top, @"([0-9.]+)\s*刻み"), maxDrop = rx(top, @"差が\s*([0-9.]+)\s*を超える"), endDiff = rx(top, @"差が\s*([0-9.]+)\s*未満");
            float bfEnd = rx(enT, @"法\s*1\s*:\s*([0-9.]+)");
            float drop = rx(bfT, @"天端\s*[−\-]\s*([0-9.]+)"), wKen = rx(bfT, @"〜\s*([0-9.]+)\s*間"), bf = rx(bfT, @"法\s*1\s*:\s*([0-9.]+)"), maxFill = rx(bfT, @"盛りは\s*([0-9.]+)\s*以下");
            float drn = rx(drT, @"1\s*/\s*([0-9.]+)");
            var miss = new List<string>();
            if (float.IsNaN(step)) miss.Add("returnTop の刻み"); if (float.IsNaN(maxDrop)) miss.Add("returnTop の天端と背の差"); if (float.IsNaN(endDiff)) miss.Add("returnTop の終える落差");
            // returnEnd は 2 書式(EDO-0502 第32巡): 旧「土羽で止める・法 1:x」/ 新(8a332b02)「見切り石で止める」── 見切り石なら土羽の法は要らず、
            //   返しは落差 0.6 未満の所で終え、終わりの端は nozuraEndRule の②(PlaceNozuraNet の endRule)が見切り石で止める
            bool retMikiri = enT != null && (enT.Contains("見切り石") || enT.Contains("nozuraEndRule ②"));   // 終わりは nozuraEndRule ②(隅の駒の返し・2026-10-06 夕)
            if (float.IsNaN(bfEnd) && !retMikiri) miss.Add("returnEnd の土羽の法"); if (float.IsNaN(drop)) miss.Add("returnBackfill の天端からの下げ");
            if (float.IsNaN(wKen)) miss.Add("returnBackfill の幅"); if (float.IsNaN(bf)) miss.Add("returnBackfill の法"); if (float.IsNaN(maxFill)) miss.Add("returnBackfill の盛りの上限");
            if (float.IsNaN(drn)) miss.Add("returnBackDrain の勾配"); if (float.IsNaN(depth)) miss.Add("avoid.dodomeCrestDepthM[野面の乱積み]");
            // returnEnd 追記(2026-10-07・EDO-0502 第45巡): 最後の run が 1 駒より短く上の run の裏に隠れるときは作らず、上の run の端で積み止め。
            //   その端の run の背は 小段(天端 − hDrop)・盛り ≤ hFill・端の手前で 1:hBf で回して下ろす(法尻 = 端の線 ── 一間の内・口へ入れない)
            bool hideLast = enT != null && enT.Contains("その run を作らず");
            float hDrop = rx(enT, @"小段\s*[0-9.]+\s*[\(（]\s*天端\s*[−\-]\s*([0-9.]+)"), hFill = rx(enT, @"盛り\s*≤\s*([0-9.]+)"), hBf = rx(enT, @"1\s*:\s*([0-9.]+)\s*で回して");
            if (hideLast) { if (float.IsNaN(hDrop)) miss.Add("returnEnd の端の小段(天端−)"); if (float.IsNaN(hFill)) miss.Add("returnEnd の端の盛り≤"); if (float.IsNaN(hBf)) miss.Add("returnEnd の回して下ろす法"); }
            if (miss.Count > 0) { if (note != null) note.AppendLine("  ★ " + nm + " の返し: 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 返しの割りと裏込めをしない"); continue; }
            var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            var tops = new List<float>(); var tl = A(Get(w, "tops")); for (int i = 0; i < nodes.Count; i++) tops.Add(tl != null && i < tl.Count ? F(tl[i]) : F(Get(w, "top")));
            List<EndReturn> rets; EndDecisions(nm, w, nodes, tops, null, out rets);
            float pieceL = 1.818f;   // 野面の駒の走り(PlaceNozuraNet の送り)── 1 駒より短い run は余りを上手へ重ねる(RunsByCrestGap)
            var list = new List<KeyValuePair<int, EdoBuild.BackBench>>();
            foreach (var rt in rets)
            {
                Vector2 a = rt.pg, b = rt.pb; float L = Vector2.Distance(a, b); if (L < 0.3f) continue;
                Vector2 t = (b - a) / L; float off = depth + 0.25f;
                Func<float, float> backAt = sl => DesignY(a + t * sl + rt.back * off), frontAt = sl => DesignY(a + t * sl - rt.back * off);
                float yMain = tops[0], sEnd;
                var hid = hideLast ? new List<Vector3>() : null;
                var runs = EdoBuild.RunsByCrestGap(L, backAt, frontAt, yMain, step, maxDrop, endDiff, pieceL, out sEnd, 0.25f, hid);
                string endNote;
                if (hid != null && hid.Count > 0)
                    endNote = "最後の run(" + hid[0].x.ToString("F2") + "〜" + hid[0].y.ToString("F2") + "m・" + (hid[0].y - hid[0].x).ToString("F2") + " < 1 駒・天端 " + hid[0].z.ToString("F2")
                            + ")は上の run の裏に隠れる ⇒ 作らず、上の run の端 " + sEnd.ToString("F2") + "m で積み止め(returnEnd 追記・returnTop の差 " + endDiff.ToString("F1") + " 未満は当てない)"
                            + "・端の背 天端 −" + hDrop.ToString("F2") + "・盛り ≤ " + hFill.ToString("F2") + "・端の手前で 1:" + hBf.ToString("F1") + " で回して下ろす";
                else if (sEnd < L - 1e-3f && retMikiri)
                    endNote = "落差 " + endDiff.ToString("F1") + " 未満で終える(" + sEnd.ToString("F2") + "m)── 終わりは見切り石(returnEnd・nozuraEndRule ②)";
                else if (sEnd < L - 1e-3f)
                {
                    // 返しの終わりから妻までは土羽(法 1:bfEnd・法尻は返しの線の上)。法尻が長屋の背から 1 間の外に取れなければ妻まで延ばす【硬】
                    float dh = Mathf.Abs(backAt(sEnd) - frontAt(sEnd)), toe = sEnd + bfEnd * dh;
                    if (L - toe < C("ken") - 1e-3f)
                    {
                        runs = EdoBuild.RunsByCrestGap(L, backAt, frontAt, yMain, step, maxDrop, -1f, pieceL, out sEnd);
                        endNote = "落差 " + dh.ToString("F2") + " で終えると土羽の法尻が長屋の背から " + (L - toe).ToString("F2") + "m(< 1 間)── 妻まで延ばした";
                    }
                    else endNote = "落差 " + dh.ToString("F2") + " で終えて土羽(法尻 " + toe.ToString("F2") + "m・長屋の背まで " + (L - toe).ToString("F2") + "m)⚠ 土羽の盛りは未実装";
                }
                else endNote = "落差 " + endDiff.ToString("F1") + " 未満の所が無い ── 妻まで";
                if (note != null) note.AppendLine("    返し " + nm + " 端" + rt.end + ": 長さ " + sEnd.ToString("F2") + "/" + L.ToString("F2") + "m・run " + runs.Count + "・" + endNote);
                for (int ri = 0; ri < runs.Count; ri++)
                {
                    var r = runs[ri]; bool tail = hid != null && hid.Count > 0 && ri == runs.Count - 1;   // 積み止めで終える端の run
                    list.Add(new KeyValuePair<int, EdoBuild.BackBench>(rt.end, new EdoBuild.BackBench
                    {
                        name = nm + "_ret" + rt.end, a = a + t * r.x, b = a + t * r.y, back = rt.back, top = Mathf.Min(yMain, r.z), drop = tail ? hDrop : drop, w = wKen * C("ken"),
                        drain = 1f / drn, bf = tail ? hBf : bf, maxFill = tail ? hFill : maxFill, parcel = Poly, baseAt = DesignY, tuckB = tail
                    }));
                }
            }
            if (list.Count > 0) res[nm + "#ret"] = list;
        }
        StairSideAndEndBacks(res, note, depth, rx);
        // ⭐ 小段の端の法は、別の土留め(袖・返し)の見え面の前の帯(3m)へ盛らない(EdoBuild.InFrontOfFace・EDO-0502 第25巡 ──
        //   TW_Kado_Sode_0 の小段の端の法が門の内の TW_Kado_Sode_1_0/3_0 の前へ回り込み 17.50 の土の箱を立てていた)。帯 = 各 run の線と背。
        {
            var fr = new List<KeyValuePair<string, EdoBuild.BackBench>>();
            foreach (var kv in res) foreach (var bk in kv.Value) fr.Add(new KeyValuePair<string, EdoBuild.BackBench>(kv.Key.Split('#')[0], bk.Value));
            foreach (var kv in res)
            {
                string own = kv.Key.Split('#')[0];
                foreach (var bk in kv.Value)
                {
                    var me = bk.Value;
                    var own0 = me.keepOut;   // 自分の篩(道の路盤など・StairSideAndEndBacks)は残して重ねる
                    me.keepOut = p => { if (own0 != null && own0(p)) return true; foreach (var o in fr) if (o.Value != me && EdoBuild.InFrontOfFace(o.Value.a, o.Value.b, o.Value.back, p, 3f)) return true; return false; };
                }
            }
        }
        // ⭐ 端の天端上げ(指図 terraceWalls[].endRaise・2026-10-06 EDO-0502 第37巡 TW_Kita_Koshi)── 端の一〜二間を高い天端の別の run に割り(EdoBuild.RaiseEndLen)、
        //   その背は切らずに盛って小段(BackBench: 天端 − drop・走りに沿って段違いの側へ 1/x・走りの外へは盛らない・盛り ≤ 上限・練塀の犬走りの内へ入れない)。
        //   "<名>#raise" に入れる ── Stage2b が区間を割って地形へ盛り、Stage3b(皮の設計の地盤)と GradeQA が同じ小段を読む(式は BackBenchAt 一つ)。
        //   ⛔ 指図から読めない値は使わない(★ で刷って上げない)。
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null) continue; string nm = S(Get(w, "name"));
            Dictionary<string, object> sw = null;
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
            var er = sw == null ? null : O(Get(sw, "endRaise")); if (er == null) continue;
            string atT = S(Get(er, "at")), ruT = S(Get(er, "rule")), bfT = S(Get(er, "backfill")), drT = S(Get(er, "drain"));
            var mSeg = System.Text.RegularExpressions.Regex.Match(atT ?? "", @"(" + System.Text.RegularExpressions.Regex.Escape(nm) + @"_(\d+)_(\d+))");
            int endIx = (atT ?? "").Contains("終わり") ? 1 : (atT ?? "").Contains("始まり") ? 0 : -1;
            float topR = Get(er, "top") == null ? float.NaN : F(Get(er, "top"));
            float thrDrop = rx(ruT, @"天端\s*[−\-]\s*([0-9.]+)"), minIn = rx(ruT, @"1\s*駒\s*[\(（]\s*([0-9.]+)\s*[\)）]");
            var mLen = System.Text.RegularExpressions.Regex.Match(ruT ?? "", @"([一二三四])間〜([一二三四])間");
            System.Func<string, float> kan = k0 => k0 == "一" ? 1f : k0 == "二" ? 2f : k0 == "三" ? 3f : k0 == "四" ? 4f : float.NaN;
            float lo = mLen.Success ? kan(mLen.Groups[1].Value) * C("ken") : float.NaN, hi = mLen.Success ? kan(mLen.Groups[2].Value) * C("ken") : float.NaN;
            float drop = rx(bfT, @"天端\s*[−\-]\s*([0-9.]+)"), maxFill = rx(bfT, @"盛りは\s*([0-9.]+)\s*以下"), inu = rx(bfT, @"犬走り\s*([0-9.]+)"), drn = rx(drT, @"1\s*/\s*([0-9.]+)");
            var miss = new List<string>();
            if (!mSeg.Success) miss.Add("at の区間名"); if (endIx < 0) miss.Add("at の端(始まり/終わり)"); if (float.IsNaN(topR)) miss.Add("top");
            if (float.IsNaN(thrDrop)) miss.Add("rule の背の閾(天端−x)"); if (float.IsNaN(minIn)) miss.Add("rule の段違いの内の下限(1 駒)"); if (float.IsNaN(lo)) miss.Add("rule の長さの狙い(〜間)");
            if (float.IsNaN(drop)) miss.Add("backfill の天端からの下げ"); if (float.IsNaN(maxFill)) miss.Add("backfill の盛りの上限"); if (float.IsNaN(inu)) miss.Add("backfill の犬走り");
            if (float.IsNaN(drn)) miss.Add("drain の勾配"); if (float.IsNaN(depth)) miss.Add("avoid.dodomeCrestDepthM[野面の乱積み]");
            if (miss.Count > 0) { if (note != null) note.AppendLine("  ★ " + nm + " の endRaise: 指図から読めない(" + string.Join("・", miss.ToArray()) + ")── 上げない"); continue; }
            var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            int si = int.Parse(mSeg.Groups[2].Value);
            if (si + 1 >= nodes.Count || mSeg.Groups[3].Value != "0" || (A(Get(w, "gaps")) ?? new List<object>()).Count > 0)
            { if (note != null) note.AppendLine("  ★ " + nm + " の endRaise: 区間 " + mSeg.Groups[1].Value + " を線から引けない(口で割れた区間は未対応)── 上げない"); continue; }
            Vector2 a0 = nodes[si], b0 = nodes[si + 1]; float L = Vector2.Distance(a0, b0);
            Vector2 t = (b0 - a0) / L, nrm = new Vector2(-t.y, t.x), mid = (a0 + b0) * 0.5f;
            float yp = DesignY(mid + nrm * 3f), ym = DesignY(mid - nrm * 3f);
            Vector2 back = (!float.IsNaN(yp) && (float.IsNaN(ym) || yp >= ym)) ? nrm : -nrm;
            Vector2 ep = endIx == 1 ? b0 : a0, inw = endIx == 1 ? -t : t;   // 端と、端から内へ向く走り
            float offS = depth + 0.25f, topLo = F(Get(w, "top"));
            float sCross; bool softMiss;
            float len = EdoBuild.RaiseEndLen(s1 => DesignY(ep + inw * s1 + back * offS), topLo - thrDrop, L, minIn, lo, hi, out sCross, out softMiss);
            if (float.IsNaN(len)) { if (note != null) note.AppendLine("  ⛔ " + nm + " の endRaise: 区間 " + L.ToString("F2") + "m に段違いを端から " + minIn.ToString("F2") + " 以上内に取れない ── 上げない"); continue; }
            // 小段の線 a → b(b = 端・高い側)。練塀・隅(長屋の躯体でない囲い)の足あと + 犬走りの内へは盛らない【硬】
            var wallB = new List<Bounds>(); var rk = GameObject.Find(GN); var kk = rk == null ? null : rk.transform.Find("Kakoi");
            if (kk != null) foreach (Transform c in kk) if (c.gameObject.activeInHierarchy && !EdoBuild.IsNagayaBody(c.gameObject))
                foreach (var mr in c.GetComponentsInChildren<MeshRenderer>())
                {
                    var bb = mr.bounds; bb.Expand(new Vector3(2f * inu, 0f, 2f * inu));
                    var cq = new Vector2(Mathf.Clamp(ep.x, bb.min.x, bb.max.x), Mathf.Clamp(ep.y, bb.min.z, bb.max.z));
                    if (Vector2.Distance(cq, ep) < len + 12f) wallB.Add(bb);   // 小段の届く所(端から 一駒の長さ + 12m)の囲いだけ ── 篩は皮の全節点で呼ばれる
                }
            var rb = new EdoBuild.BackBench
            {
                name = mSeg.Groups[1].Value, a = ep + inw * len, b = ep, back = back, top = topR, drop = drop, w = 50f, drain = 0f, bf = 1f, maxFill = maxFill,
                parcel = Poly, baseAt = DesignY, drainAlong = 1f / drn, noEndSpill = true
            };
            rb.keepOut = q => { foreach (var bb in wallB) if (q.x >= bb.min.x && q.x <= bb.max.x && q.y >= bb.min.z && q.y <= bb.max.z) return true; return false; };
            res[nm + "#raise"] = new List<KeyValuePair<int, EdoBuild.BackBench>> { new KeyValuePair<int, EdoBuild.BackBench>(si, rb) };
            if (note != null) note.AppendLine("    endRaise " + mSeg.Groups[1].Value + " 端" + endIx + ": 天端 " + topR.ToString("F2") + " の run 長さ " + len.ToString("F2") + "m(背 > " + (topLo - thrDrop).ToString("F2")
                + " が始まる所 " + (float.IsNaN(sCross) ? "無し" : sCross.ToString("F2") + "m") + (softMiss ? " ⚠ 狙い " + lo.ToString("F2") + "〜" + hi.ToString("F2") + " の外 ⇒ 最も近い長さ" : "") + ")・小段 " + (topR - drop).ToString("F2")
                + "→段違いの側へ 1/" + drn.ToString("F0") + "・盛り ≤ " + maxFill.ToString("F2") + "・犬走り " + inu.ToString("F2") + " の内と走りの外へ盛らない・練塀/隅 " + wallB.Count);
        }
        return res;
    }

    static float[] RampPatchedDesign(WGrid G, System.Text.StringBuilder sb)
    {
        var h = (float[])G.h.Clone(); var f = Grid; float ken = C("ken"), bc = C("batterCut"); int n = 0;
        foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
        {
            var r = O(o); if (r == null) continue; var pl = A(Get(r, "pts")); if (pl == null || pl.Count < 2) continue;
            var line = new List<Vector2>(); foreach (var q in pl) { var v = A(q); line.Add(f.W(F(v[0]), F(v[1]))); }
            float lo = float.MaxValue, hi = float.MinValue;
            foreach (var key in new[] { "profY", "profS" })
                foreach (var q in A(Get(r, key)) ?? new List<object>()) { var v = A(q); float y = v != null ? F(v[v.Count - 1]) : F(q); lo = Mathf.Min(lo, y); hi = Mathf.Max(hi, y); }
            if (lo > hi) continue;
            float width = Has(r, "w") ? F(r["w"]) : F(r["wKen"]) * ken;
            float band = width * 0.5f + (hi - lo) * bc;
            for (int j = 0; j < G.nz; j++)
                for (int i = 0; i < G.nx; i++)
                {
                    int k = j * G.nx + i; if (float.IsNaN(h[k])) continue;
                    float x = G.x0 + i * G.step, z = G.z0 + j * G.step;
                    if (Mathf.Abs(EdoBuild.ArcOf(line, new Vector2(x, z)).y) > band) continue;
                    // 芯の端より先(道のりの外)は帯に数えない
                    var st = EdoBuild.ArcOf(line, new Vector2(x, z)); float L = 0f; for (int m = 1; m < line.Count; m++) L += Vector2.Distance(line[m - 1], line[m]);
                    if (st.x <= 1e-3f || st.x >= L - 1e-3f) continue;
                    float g = EdoBuild.Ground(x, z); if (float.IsNaN(g) || Mathf.Abs(g - h[k]) < 0.02f) continue;
                    h[k] = g; n++;
                }
        }
        if (sb != null) sb.AppendLine("  坂の路盤を設計の地盤へ写した節点 " + n + "(算出物 graded に坂が無い所)");
        return h;
    }

    /// <summary>皮が高さを揃える**平らな面**(指図 terraces の poly を世界へ)。算出物 graded が面の中(縁から 1.5m 内)で面の高さから
    /// 0.05m を超えて外れる面(勾配の面・ramps)は除く ── 皮はそこを graded で描く。sb が null なら除いた面を刷らない。</summary>
    static List<EdoBuild.SkinFace> FlatFaces(System.Text.StringBuilder sb)
    {
        // 面 = 指図 terraces(回転間グリッドの poly を世界へ)。⭐ 平らな面だけ ── 算出物 graded が面の中で面の高さから 0.05m を超えて
        //   外れる面(勾配の面 ramps・東の平場)は皮で平らに削らず、設計の地盤(graded)として描く
        var faces = new List<EdoBuild.SkinFace>(); var f = Grid;
        foreach (var o in A(D["terraces"]) ?? new List<object>())
        {
            var t = O(o); if (t == null) continue;
            var pl = A(Get(t, "poly")); if (pl == null || pl.Count < 3) continue;
            var poly = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); poly[i] = f.W(F(q[0]), F(q[1])); }
            float y = F(Get(t, "y")), dev = 0f; int nIn = 0;
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var p in poly) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
            for (float x = Mathf.Ceil(mnx); x <= mxx; x += 1f)
                for (float z = Mathf.Ceil(mnz); z <= mxz; z += 1f)
                {
                    var q = new Vector2(x, z); if (!EdoGeom.PIP(poly, q) || EdoGeom.DistToPolyEdge(poly, q) < 1.5f) continue;
                    float g = Graded.At(x, z); if (float.IsNaN(g)) continue; nIn++; dev = Mathf.Max(dev, Mathf.Abs(g - y));
                }
            if (nIn == 0 || dev > 0.05f) { if (sb != null) sb.AppendLine("  面 " + S(Get(t, "name")) + "(" + y.ToString("F2") + "): 設計の地盤が面から最大 " + dev.ToString("F2") + "m 外れる勾配の面 ── 面にせず graded で描く"); continue; }
            faces.Add(new EdoBuild.SkinFace(S(Get(t, "name")), poly, y));
        }
        // ⭐ 返しの石垣と長屋の背の間の溝(BackTrenches・EDO-0502 第19巡)も平らな面 ── 門の内の面より小さいので入れ子の内の面として勝つ
        //   (皮は面積の小さい面を採る)。帯 = 背の面の 0.30 内(棟の下)から返しの見え面まで・止めの妻から返しの端 + 一間まで
        foreach (var tr in BackTrenches(null))
        {
            float L = Vector2.Dot(tr.far - tr.stop, tr.along) + tr.off;
            Vector2 p0 = tr.stop - tr.yard * 0.30f, p1 = p0 + tr.along * L, p2 = tr.stop + tr.along * L + tr.yard * tr.off, p3 = tr.stop + tr.yard * tr.off;
            faces.Add(new EdoBuild.SkinFace("Mizo_" + tr.run, new[] { p0, p1, p2, p3 }, tr.y));
            if (sb != null) sb.AppendLine("  面 溝 " + tr.run + "(" + tr.y.ToString("F2") + "): 返しと背の間 " + L.ToString("F2") + "×" + (tr.off + 0.30f).ToString("F2") + "m");
        }
        // ⭐ 両端の返しで三方が閉じた長屋の背の一間(指図 terraceWalls[].stripDrain・EDO-0502 第25巡)も平らな面 ── 溝の底は算出物 graded の
        //   溝の芯の中ほど(両端の返しから離れた所)の中央値。⛔ 2026-10-05 まで面が無く、graded の 1m 格子が返しの見え面の前 1〜1.5m で
        //   溝の底 19.20 から 20.5〜20.9 へ一次で上がり、皮が溝の両端に土の尾根を描いた(「溝に土を入れない」【硬】に反する)。
        //   帯 = 腰石垣の線(出隅 pg)と長屋の背(返しの終わり pb)の間・両端の返しの線の間。⚠ 1/100 の落としは graded に無い ── 平らのまま。
        //   ⛔ 再入: 返しの決め(EndDecisions)は SkinGround → FlatFaces を呼ぶ ⇒ 溝の帯を作る間は内側の呼び出しで帯を足さない。
        //   当たる先: stripDrain を持つ欄(いまは岡部 TW_Minami_Koshi)。
        if (!_inStrip)
        {
            _inStrip = true;
            try
            {
                foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
                {
                    var w = O(o); if (w == null) continue; string nm = S(Get(w, "name"));
                    Dictionary<string, object> sw = null;
                    foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var w2 = O(o2); if (w2 != null && S(Get(w2, "name")) == nm) sw = w2; }
                    if (sw == null || Get(sw, "stripDrain") == null) continue;
                    var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
                    var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
                    var tops = new List<float>(); var tl = A(Get(w, "tops")); for (int i = 0; i < nodes.Count; i++) tops.Add(tl != null && i < tl.Count ? F(tl[i]) : F(Get(w, "top")));
                    List<EndReturn> rets; EndDecisions(nm, w, nodes, tops, null, out rets);
                    EndReturn r0 = rets.Find(r => r.end == 0), r1 = rets.Find(r => r.end == 1);
                    if (r0 == null || r1 == null) { if (sb != null) sb.AppendLine("  面 一間の溝 " + nm + ": ⚠ 両端の返しが揃わない ── 面にしない"); continue; }
                    var ys = new List<float>();
                    for (float u = 0.25f; u <= 0.75f + 1e-4f; u += 0.05f)
                    {
                        Vector2 q = Vector2.Lerp((r0.pg + r0.pb) * 0.5f, (r1.pg + r1.pb) * 0.5f, u);
                        float g = DesignY(q); if (!float.IsNaN(g)) ys.Add(g);
                    }
                    if (ys.Count == 0) continue; ys.Sort(); float yS = ys[ys.Count / 2];
                    faces.Add(new EdoBuild.SkinFace("Mizo_" + nm, new[] { r0.pg, r1.pg, r1.pb, r0.pb }, yS));
                    if (sb != null) sb.AppendLine("  面 一間の溝 " + nm + "(" + yS.ToString("F2") + "・graded の溝の芯の中ほどの中央値): 両端の返しの間 " + Vector2.Distance(r0.pg, r1.pg).ToString("F2") + "m ⚠ 1/100 の落としは graded に無い");
                }
            }
            finally { _inStrip = false; }
        }
        return faces;
    }

    /// <summary>点 <paramref name="q"/> を含む**面**(指図 terraces の poly を世界へ・勾配の面も含む)のうち最も小さい物。無ければ区画。
    /// 当たる先: 棟の下の均し(EdoBuild.LevelPad)の範囲 ── 面の外(段の土留めの向こうの下の面)の節点を触らない(EDO-0502 第7巡)。</summary>
    /// <summary>棟の下の均しが面の外で触ってよい縁の節点(EdoBuild.PadRim): 区画の内・<paramref name="q"/> の建つ面(TerracePolyAt と同じ選び)以外の平らな面の外。</summary>
    static EdoBuild.PadRim PadRimAt(Vector2 q)
    {
        var all = new List<Vector2[]>(); int own = -1; float area = float.MaxValue; var f = Grid;
        foreach (var o in A(D["terraces"]) ?? new List<object>())
        {
            var t = O(o); if (t == null) continue;
            var pl = A(Get(t, "poly")); if (pl == null || pl.Count < 3) continue;
            var poly = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) { var p = A(pl[i]); poly[i] = f.W(F(p[0]), F(p[1])); }
            all.Add(poly);
            if (!EdoGeom.PIP(poly, q)) continue;
            float a = Mathf.Abs(EdoGeom.SignedArea(poly)); if (a < area) { area = a; own = all.Count - 1; }
        }
        if (own >= 0) all.RemoveAt(own);
        return new EdoBuild.PadRim { outer = Poly, keepOut = all };
    }

    static Vector2[] TerracePolyAt(Vector2 q)
    {
        Vector2[] best = null; float area = float.MaxValue; var f = Grid;
        foreach (var o in A(D["terraces"]) ?? new List<object>())
        {
            var t = O(o); if (t == null) continue;
            var pl = A(Get(t, "poly")); if (pl == null || pl.Count < 3) continue;
            var poly = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) { var p = A(pl[i]); poly[i] = f.W(F(p[0]), F(p[1])); }
            if (!EdoGeom.PIP(poly, q)) continue;
            float a = Mathf.Abs(EdoGeom.SignedArea(poly)); if (a < area) { area = a; best = poly; }
        }
        return best ?? Poly;
    }

    /// <summary>**皮が描く地表**(Stage3b の縁の皮が描く高さ)を、皮を起こす前に引く: 平らな面の中は面の高さ、外は設計の地盤 graded と
    /// 地形の低い方(区画の外・graded の無い所は地形)。⭐ 段の土留めの駒の底・見え面の前の地表はこれで測る ── 2m 格子の地形は見え面の足元で
    /// 段を描けず最大 1.77m 盛り上がる(駒の底がその盛りに載り、皮が盛りを削ると駒が浮いた・EDO-0502 第5巡)。
    /// 当たる先: 岡部 Stage2b の城の石垣・二段築の下段・出隅・野面の乱積み(皮を起こす全邸で、土留めを据える地表は皮が描く地表)。</summary>
    static float SkinGround(float x, float z)
    {
        if (_flat == null) _flat = FlatFaces(null);
        var q = new Vector2(x, z); float best = float.NaN, area = float.MaxValue;
        foreach (var fc in _flat) if (EdoGeom.PIP(fc.poly, q)) { float a = Mathf.Abs(EdoGeom.SignedArea(fc.poly)); if (a < area) { area = a; best = fc.y; } }
        if (!float.IsNaN(best)) return best;
        float rp = RampProfileAt(q); if (!float.IsNaN(rp)) return rp;   // 石段を名指す坂の路盤は縦断で(皮の設計と同じ ── 2026-10-07)
        float g = EdoBuild.Ground(x, z), d = EdoGeom.PIP(Poly, q) ? DesignY(q) : float.NaN;
        return float.IsNaN(d) ? g : Mathf.Min(d, g);
    }

    /// <summary>石段を名指す坂(kaidans[].atRoute)の路盤の帯(芯から幅/2)の中の、縦断の高さ(<see cref="RampAxis"/> の節点を道のりで一次 ──
    /// GradeRamps と皮の設計と同じ)。帯の外・坂の端の外は NaN。⭐ 2m 格子の地形は石段の上がり口の段石の背(0.45m の平ら)を描けない
    /// ので、段石の積みと皮はこの縦断で測る(2026-10-07 EDO-0502 施主指摘 B)。</summary>
    static float RampProfileAt(Vector2 q)
    {
        if (_rampProf == null)
        {
            _rampProf = new List<KeyValuePair<Vector2[], float[]>>(); _rampW = new List<float>();
            foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
            {
                var r = O(o); if (r == null) continue;
                bool hasK = false; foreach (var ko in A(Get(D, "kaidans")) ?? new List<object>()) { var kk = O(ko); if (kk != null && S(Get(kk, "atRoute")) == S(Get(r, "name"))) hasK = true; }
                if (!hasK) continue;
                Vector2[] pts; float[] ys; float width; string an;
                if (!RampAxis(r, out pts, out ys, out width, out an) || pts.Length < 2) continue;
                _rampProf.Add(new KeyValuePair<Vector2[], float[]>(pts, ys)); _rampW.Add(width);
            }
        }
        for (int ri = 0; ri < _rampProf.Count; ri++)
        {
            var pts = _rampProf[ri].Key; var ys = _rampProf[ri].Value; var line = new List<Vector2>(pts);
            var st = EdoBuild.ArcOf(line, q); if (Mathf.Abs(st.y) > _rampW[ri] * 0.5f) continue;
            float acc = 0f;
            for (int m = 0; m + 1 < pts.Length; m++)
            {
                float L = Vector2.Distance(pts[m], pts[m + 1]);
                if (st.x <= acc + L + 1e-4f) { if (st.x <= 1e-3f && m == 0) break; return Mathf.Lerp(ys[m], ys[m + 1], (st.x - acc) / Mathf.Max(1e-4f, L)); }
                acc += L;
            }
        }
        return float.NaN;
    }
    static List<KeyValuePair<Vector2[], float[]>> _rampProf; static List<float> _rampW;
    static List<EdoBuild.SkinFace> _flat;
    static bool _inStrip;   // FlatFaces が一間の溝の帯を作る間(EndDecisions → SkinGround → FlatFaces の再入を止める)

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
            //   ⛔ 切り欠きの線は**指図 `roofs[].sashikomi.kirikaki`(取り合いの食い込みの線)**が正典(K063 章番号で引かない) — 実装で決めない。
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
                                      nx, nz, iriZ, floor, roof, true, true, null, null, -1, iriX, ashimoto: true);
            if (go != null)
            {
                made++;
                // 床下の足元(縁桁・縁束・礎石)の当たり ── 硬い: 浮き ≤ 0.01m(EDO-0502)
                int an, af; string aw; float ag = EdoGotenKit.AshimotoGap(go, out an, out af, out aw);
                if (an == 0) wait.Add("棟 " + nm + ": 床下の足元の部材が無い(床高 " + floor.ToString("0.###") + " の版 EdoAssets.Goten.EnKeta が null)");
                else
                {
                    sb0.Append("\n  " + nm + " の足元 " + an + " 駒・最も浮いた当たり " + ag.ToString("+0.000;-0.000") + "m @" + aw);
                    if (af > 0) wait.Add("棟 " + nm + ": 足元の石 " + af + " 駒が浮く(最悪 " + ag.ToString("F3") + "m @" + aw + ")");
                }
            }
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
        // ⚠ **切り欠きは水平面ではなく屋根面**(2026-09-04 部材方)。玄関棟の軒先の線から
        //   奥(v ≧ atV)へ、勾配 `slope` で上がる**斜面**より上を切る。
        //   ⛔ 水平面のままだと 278 頂点を誤検出する(切り欠き済みの部材を「未実施」と報告する)。
        float slope = Has(kk, "slope") ? F(kk["slope"]) : 0.5456f;
        if (!Has(kk, "slope"))
            wait.Add("車寄の切り欠き: 指図 `kirikaki.slope` が無いので勾配 0.5456(部材方の実測)を"
                   + "当てた — 指図方が欄を足すこと");
        float ken = C("ken");
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
                if (uv.y < atV) continue;                       // 軒先の線より手前は切らない
                // ⭕ 屋根面: 面から `aboveY` + 奥行き(m)× 勾配
                float cut = aboveY + (uv.y - atV) * ken * slope;
                float above = (w.y - face) - cut;
                if (above <= 0f) continue;
                n++; maxAbove = Mathf.Max(maxAbove, above); maxV = Mathf.Max(maxV, uv.y);
            }
        }
        if (n == 0) return " / 車寄の切り欠き: 不要(食い込み 0)";
        wait.Add("車寄の切り欠き: **屋根面より上に出ている** — 玄関棟の軒先の線(v≧" + atV.ToString("0.##")
               + ")より奥で、面+" + aboveY.ToString("0.###") + "m から勾配 " + slope.ToString("0.####")
               + " で上がる屋根面より上に車寄の頂点が " + n
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
            // ---- 門長屋(案1・EDO-0502)。`Own.NagayaOmoteMon(len, 左端からの口の芯, 二階か)`。第3引数は true/false
            case "NagayaOmoteMon":
                return a0 > 0f && args.Count >= 2
                     ? EdoAssets.Own.NagayaOmoteMon(a0, a1, key.Replace(" ", "").EndsWith(",true)")) : null;
            // ---- 米蔵(案1・指図 service[Komegura].asset = `Own.Typ.Komegura`)
            case "Komegura":   return EdoAssets.Own.Typ.Komegura;
            // ---- 崖下(法尻の帯)。⚠ 引数は **間** なので足跡から引く(指図は m で書いている)
            case "ObiNagaya":  return wKen > 0f ? EdoAssets.Own.ObiNagaya(wKen, dKen) : null;
            case "ObiMonooki": return EdoAssets.Own.ObiMonooki;
            case "ObiKawaya":  return EdoAssets.Own.ObiKawaya;
            // ---- 岡部のために焼いた附属屋
            case "Umaya":      return EdoAssets.Own.Umaya;
            case "Tomomachi":  return EdoAssets.Own.Tomomachi;
            case "Tomomachi35": return EdoAssets.Own.Tomomachi35;
            case "Kura4x5":    return EdoAssets.Own.Kura4x5;
            case "Makigura":   return EdoAssets.Own.Makigura;
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
            // ---- 庭(指図 gardens.NiwaShoin の遣水の石橋 `Own.Ishibashi` ── 松江松平の庭のために新造した切石橋 2.2m)
            case "Ishibashi":        return EdoAssets.Own.Ishibashi();
            // ---- 庭(指図 gardens.NiwaShoin の木の平橋 `Own.HashiIta` ── L 8.0・W 1.82 で焼いた一本。長さは据えで scale.x ±6%)
            case "Hashi":            return EdoAssets.Own.HashiIta();
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
        // ⭕ **躯体の芯**を足跡の中心へ(EdoBuild.BodyFootprintLocal)。⛔ 軒込みの外接の中心で据えない ──
        //   軒の出が前後で違う駒(厩の吹き放ち・長屋の戸口)は躯体がずれる。躯体と屋根を分けられない駒だけ外接で測る
        Vector2 bc; float bw, bd;
        bool body = EdoBuild.BodyFootprintLocal(path, out bc, out bw, out bd);
        float haveW, haveD;
        if (body)
        {
            Vector3 off = Quaternion.Euler(0f, yaw, 0f) * new Vector3(bc.x, 0f, bc.y);
            go.transform.position = new Vector3(c.x - off.x, y, c.y - off.z);
            haveW = Mathf.Max(bw, bd); haveD = Mathf.Min(bw, bd);
        }
        else
        {
            var b0 = EdoBuild.RB(go);
            go.transform.position += new Vector3(c.x - b0.center.x, 0f, c.y - b0.center.z);
            float hw, hd; ObbWD(go, out hw, out hd);
            haveW = Mathf.Max(hw, hd); haveD = Mathf.Min(hw, hd);
        }
        var b = EdoBuild.RB(go);
        go.transform.position += new Vector3(0f, y - b.min.y, 0f);
        float wantW = wKen * C("ken"), wantD = dKen * C("ken");
        // 照合は柔らかい(据えて ⚠)。許容は ±0.5m(柱の芯と外面の差・板の厚みを呑む)
        if (Mathf.Abs(haveW - Mathf.Max(wantW, wantD)) > 0.5f ||
            Mathf.Abs(haveD - Mathf.Min(wantW, wantD)) > 0.5f)
            wait.Add("附属屋 " + nm + ": 部材の" + (body ? "躯体" : "外接(軒込み・躯体と屋根を分けられない)") + " "
                   + haveW.ToString("F2") + "×" + haveD.ToString("F2")
                   + "m が指図の足跡 " + Mathf.Max(wantW, wantD).ToString("F2") + "×" + Mathf.Min(wantW, wantD).ToString("F2")
                   + "m と合わない(据えたが寸法は合っていない)");
        return true;
    }

    /// <summary>部材ごとの**向きの規約**。⛔ 「長いほうへ +X」で一律に決めない — 部材の doc が正典。
    /// 返すのは「ローカル +X を向けるグリッドの向き」(du, dv)。</summary>
    static void OrientOf(string key, float du, float dv, out float xu, out float xv, out string note)
    {
        note = null;
        // ⛔ **括弧を先に落としてから最後の `.` を探す。**引数の小数点(`Own.NagayaOmote(21.816)` の
        //   「.816」)を族の区切りと取り違えると、部分文字列の長さが負になって例外で落ちる
        //   (2026-09-04 に S3 が `Length cannot be less than zero` で止まった)。
        string head = key ?? "";
        int lp = head.IndexOf('(');
        if (lp >= 0) head = head.Substring(0, lp);
        int dot = head.LastIndexOf('.');
        string k = dot >= 0 ? head.Substring(dot + 1) : head;
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

    /// <summary>部材の**開口の面**がローカルのどの軸か(+Z を 0° として時計回りの yaw[°])。
    /// `service[].face` はこの面を向ける向き。部材ごとの値は `EdoAssets` の doc が正典:
    /// 蔵 4×5(`Own.Kura4x5`)は **観音扉が −X の妻** ⇒ −90°。ほか(帯の長屋・厩・供待・薪蔵)は **+Z** ⇒ 0°。</summary>
    static float FrontLocalYaw(string key)
    {
        string head = key ?? "";
        int lp = head.IndexOf('('); if (lp >= 0) head = head.Substring(0, lp);
        int dot = head.LastIndexOf('.');
        string k = dot >= 0 ? head.Substring(dot + 1) : head;
        switch (k)
        {
            case "Kura4x5": return -90f;     // −X
            default: return 0f;              // +Z
        }
    }

    static string PlaceService(List<string> wait)
    {
        var grp = Group("Fuzoku/Service"); Clear(grp);
        var f = Grid;
        int made = 0, noAsset = 0, pivotOdd = 0;
        // ⭐ 棟の下の均しは全棟を据えた後に**低い順**に掛ける(2026-10-06 EDO-0502 第29巡)── 隣り合う棟(米蔵 15.77 と薪蔵 15.62・離れ 0.25m)は
        //   2m 格子の同じ節点を分け合い、後から均した低い棟が節点を切り下げて、高い棟の縁が 0.124 浮いた。低い順なら共有する節点は高い方が勝ち、
        //   低い棟の縁は埋まる(埋めて隠す・docs/oki-kata.md §4)。足元の地盤も均しの前の地形で測る(据えの順に依らない)。
        //   当たる先: 勾配の面の上で棟の下を均す全邸(LevelPad を呼ぶ附属屋・家臣長屋)。
        var pads = new List<KeyValuePair<float, System.Action>>();
        // ⭐ 一枚の均し(指図 service[].padGroup・2026-10-07 第46巡): 同じ組の棟は棟ごとに均さず、足あとの凸包(EdoBuild.PadGroupFoot)を組の yAt で一枚に均す
        var padGroups = new Dictionary<string, List<KeyValuePair<GameObject, Vector2[]>>>();
        var padGroupY = new Dictionary<string, List<float>>();
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
            // ⭕ **`face` が外を向く面を決める**(2026-09-06 指図方)。u+/u-/v+/v-。
            //   ⛔ 棟の芯に置かない — 部材のピボットが**壁の外面**なら、その面の線の上に置く。
            string face = Has(s2, "face") ? S(s2["face"]) : null;
            // ⚠ 指図は `v+` と `+v` の二書式で書く(厩・蔵2 が `+v`/`-u`)。同じ意味なので揃えて読む
            if (face != null && face.Length == 2 && (face[0] == '+' || face[0] == '-')) face = "" + face[1] + face[0];
            bool wallPivot = key.Contains("NagayaOmote");
            // 案1(EDO-0502): 棟の芯での面の高さは `yAt`(`yFrom` = 東の平場の勾配の面・棟の下の均し)。無い棟は `y`
            float sy = Has(s2, "yAt") ? F(s2["yAt"]) : F(s2["y"]);   // ピボット = 走りの中心・土台の底・壁の外面
            if (wallPivot && face == null)
            {
                pivotOdd++;
                wait.Add("家臣長屋 " + nm + "(" + S(s2["label"]) + "): 部材 " + key
                       + " は**ピボットが壁の外面**。⛔ `service[].face` が無いので据えない");
                continue;
            }
            float yaw; Vector2 c;
            if (face != null)
            {
                // 外を向く向き(グリッド)と、その面の線の上の点
                float ou = face == "u+" ? 1f : face == "u-" ? -1f : 0f;
                float ov = face == "v+" ? 1f : face == "v-" ? -1f : 0f;
                if (ou == 0f && ov == 0f)
                { wait.Add("附属屋 " + nm + ": face が知らない値 \"" + face + "\" — u+/u-/v+/v- のどれか"); continue; }
                Vector2 ow = (f.W(ou, ov) - f.W(0f, 0f)).normalized;
                // ⭕ 部材の開口の面(既定 +Z・蔵は −X の妻)を外へ。⛔ 「開口は +Z」と一律に決めない — 部材の doc が正典
                yaw = Mathf.Atan2(ow.x, ow.y) * Mathf.Rad2Deg - FrontLocalYaw(key);
                // ⭕ 壁の外面がピボットの部材は**その面の線の上**、そうでなければ足跡の中心
                float pu = wallPivot ? (ou > 0f ? u1 : ou < 0f ? u0 : (u0 + u1) * 0.5f) : (u0 + u1) * 0.5f;
                float pv = wallPivot ? (ov > 0f ? v1 : ov < 0f ? v0 : (v0 + v1) * 0.5f) : (v0 + v1) * 0.5f;
                c = f.W(pu, pv);
            }
            else
            {
                float xu, xv; string nt;
                OrientOf(key, du, dv, out xu, out xv, out nt);
                yaw = YawTo(xu, xv);
                c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
            }
            if (wallPivot)
            {
                // ⛔ 足跡の照合(PlaceBox)は中心前提なので使わない。ピボットは壁の外面・土台の底
                var go2 = EdoBuild.Place(path, new Vector3(c.x, sy, c.y), yaw, Vector3.one, grp, nm);
                if (go2 == null) { wait.Add("附属屋 " + nm + ": 据えられない " + path); continue; }
                EdoBuild.SeatBottom(go2, sy - 0.10f);
                made++;
            }
            else if (PlaceBox(grp, nm, path, c, sy, du, dv, yaw, wait))
            {
                made++;
                // 硬い・埋没/浮き 0: 勾配の面(yFrom)の上の棟は、足元を測って食い違えば棟の下を yAt で均す(EdoBuild.LevelPad)
                var bgo = grp.Find(nm).gameObject;
                var foot = Has(s2, "yFrom") ? EdoBuild.BodyFootWorld(bgo, path) : null;   // ⭐ 造成QA(ServicePads)と同じ足あと
                string pg = foot != null && Has(s2, "padGroup") ? S(s2["padGroup"]) : null;
                if (pg != null)
                {
                    if (!padGroups.ContainsKey(pg)) { padGroups[pg] = new List<KeyValuePair<GameObject, Vector2[]>>(); padGroupY[pg] = new List<float>(); }
                    padGroups[pg].Add(new KeyValuePair<GameObject, Vector2[]>(bgo, foot)); padGroupY[pg].Add(sy);
                }
                else if (foot != null)
                {
                    float lo = float.MaxValue, hi = float.MinValue;
                    foreach (var q in foot) { float g = EdoBuild.Ground(q.x, q.y); lo = Mathf.Min(lo, g); hi = Mathf.Max(hi, g); }
                    float bot = EdoBuild.RB(bgo).min.y;
                    if (hi - bot > PAD_TOL || bot - lo > PAD_TOL)   // 硬い(埋没・浮き 0): 測りの誤差 PAD_TOL だけ見逃す(旧 0.15 で厩の −0.14 が素通りした・第6巡)
                    {
                        // 面の高さは地形が決める(規則3): 足あと(四隅+芯)の造成後の地盤の中央値へ棟の底を据え、その高さで均す。
                        //   指図の yAt と ±0.25m を超えて違えば ⚠(欄の上書きは普請奉行)
                        var gs = new List<float> { lo, hi };
                        foreach (var q in foot) gs.Add(EdoBuild.Ground(q.x, q.y));
                        var cq = (foot[0] + foot[2]) * 0.5f; gs.Add(EdoBuild.Ground(cq.x, cq.y));
                        gs.RemoveRange(0, 2); gs.Sort(); float med = gs[gs.Count / 2];
                        bgo.transform.position += new Vector3(0f, med - bot, 0f);
                        var padPoly = TerracePolyAt(cq); var padRim = PadRimAt(cq); var padFoot = foot; float padY = med, padLo = lo, padHi = hi, padBot = bot, padSy = sy; string padNm = nm;
                        pads.Add(new KeyValuePair<float, System.Action>(med, () =>
                        {
                            float cm, fm; int nn = EdoBuild.LevelPad(padPoly, padFoot, padY, C("batterFill"), C("batterCut"), out cm, out fm, padRim);   // ⭐ 均しは棟の建つ面の中だけ(⛔ 区画で切ると段の土留めを越えて下の面を 2.01m 盛った・第7巡)
                            wait.Add("附属屋 " + padNm + ": 足あとの地盤 " + padLo.ToString("F2") + "〜" + padHi.ToString("F2") + " が棟の底 " + padBot.ToString("F2")
                                   + "(指図 yAt)と食い違う ⇒ 底を足元の中央値 " + padY.ToString("F2") + " へ据え、棟の下を均した(EdoBuild.LevelPad 節点 " + nn
                                   + "・切 " + cm.ToString("F2") + " / 盛 " + fm.ToString("F2") + "m)" + (Mathf.Abs(padY - padSy) > 0.25f ? " ⚠ 指図の yAt " + padSy.ToString("F2") + " と " + (padY - padSy).ToString("+0.00;-0.00") + "m(±0.25 を超える ── 欄の上書きは普請奉行)" : ""));
                        }));
                    }
                    else
                    {
                        // ⭐ 食い違わない棟も、今の底の高さで棟の下を均す組に入れる(2026-10-06 EDO-0502 第36巡)。⛔ 食い違う棟だけ均すと、
                        //   隣の棟(薪蔵 15.62 と米蔵 15.77・離れ 1.8m)が 2m 格子の同じ節点を分け合い、薪蔵の均しが米蔵の縁の節点を切って米蔵が 0.147 浮いた。
                        //   全棟を低い順に均せば、分け合う節点は高い棟が勝つ(浮き 0・低い棟の縁は埋めて隠す)。冪等(既に平らなら書く節点は 0)。
                        //   当たる先: LevelPad で棟の下を均す全邸の、離れが 2m 格子より狭い隣り合う棟。
                        var padPoly2 = TerracePolyAt((foot[0] + foot[2]) * 0.5f); var padRim2 = PadRimAt((foot[0] + foot[2]) * 0.5f); var padFoot2 = foot; float padY2 = bot;
                        pads.Add(new KeyValuePair<float, System.Action>(bot, () =>
                        { float cm, fm; EdoBuild.LevelPad(padPoly2, padFoot2, padY2, C("batterFill"), C("batterCut"), out cm, out fm, padRim2); }));
                    }
                }
            }
        }
        foreach (var kv in padGroups)
        {
            var ys = padGroupY[kv.Key]; float gy = ys[0], gyMax = ys[0];
            foreach (var v in ys) { gy = Mathf.Min(gy, v); gyMax = Mathf.Max(gyMax, v); }
            if (gyMax - gy > 1e-3f)   // 硬い: 組の yAt は等しい(指図 padCert)── 違えば一枚にしない
            { wait.Add("⚠ 一枚の均し " + kv.Key + ": 組の yAt が " + gy.ToString("F2") + "〜" + gyMax.ToString("F2") + " で等しくない ⇒ 均さない(欄の上書きは普請奉行)"); continue; }
            var feetG = new List<Vector2[]>(); foreach (var m in kv.Value) feetG.Add(m.Value);
            var hull = EdoBuild.PadGroupFoot(feetG); if (hull == null) continue;
            float lo = float.MaxValue, hi = float.MinValue;
            foreach (var q in hull) { float g = EdoBuild.Ground(q.x, q.y); lo = Mathf.Min(lo, g); hi = Mathf.Max(hi, g); }
            foreach (var m in kv.Value) m.Key.transform.position += new Vector3(0f, gy - EdoBuild.RB(m.Key).min.y, 0f);   // 組の棟の底を一枚の床面へ
            var cqG = Vector2.zero; foreach (var q in hull) cqG += q; cqG /= hull.Length;
            var polyG = TerracePolyAt(cqG); var rimG = PadRimAt(cqG); string gName = kv.Key; int gN = kv.Value.Count; float gY = gy, gLo = lo, gHi = hi;
            pads.Add(new KeyValuePair<float, System.Action>(gy, () =>
            {
                float cm, fm; int nn = EdoBuild.LevelPad(polyG, hull, gY, C("batterFill"), C("batterCut"), out cm, out fm, rimG);
                wait.Add("附属屋 一枚の均し " + gName + "(" + gN + " 棟・EdoBuild.PadGroupFoot): 凸包の地盤 " + gLo.ToString("F2") + "〜" + gHi.ToString("F2")
                       + " を " + gY.ToString("F2") + " で均した(節点 " + nn + "・切 " + cm.ToString("F2") + " / 盛 " + fm.ToString("F2") + "m)");
            }));
        }
        pads.Sort((x, y) => x.Key.CompareTo(y.Key));   // 低い順(共有する節点は後の高い棟が勝つ)
        foreach (var pd in pads) pd.Value();
        var sb = new System.Text.StringBuilder("附属屋: " + made + " 棟据えた" + (pads.Count > 0 ? "(棟の下の均し " + pads.Count + " 棟を低い順に)" : ""));
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
                // ⭕ **開口は『駒の実寸』で割る**(2026-09-06 指図方)。⛔ 開口の縁で割らない —
                //   棟門は屋根と控柱があり、開口 2.727 に対し実寸 4.627 と 1.9m も違う。
                //   ⭕ 位置は指図の `fromFit`/`toFit`(`fitShift` を織り込み済み)の中点。
                float g0 = Has(gap, "fromFit") ? F(gap["fromFit"]) : F(Get(gap, "from"));
                float g1 = Has(gap, "toFit")   ? F(gap["toFit"])   : F(Get(gap, "to"));
                float p0 = ax == "u" ? au : avv, p1 = ax == "u" ? bu : bvv;
                float declKen = Mathf.Abs(g1 - g0);
                if (Mathf.Abs(p1 - p0) > 1e-6f)
                {
                    float t0 = Mathf.Clamp01((g0 - p0) / (p1 - p0)), t1 = Mathf.Clamp01((g1 - p0) / (p1 - p0));
                    float tc = (t0 + t1) * 0.5f;
                    bool isMon = S(Get(gap, "kind")) == "中門";
                    string gk = Has(gap, "asset") ? S(gap["asset"]) : (isMon ? "Own.Munamon" : "Own.Kido");
                    float wM = Mathf.Round(declKen * ken * 100f) / 100f;      // 開口の呼び[m]
                    string gpath = AssetByKey(gk, wM, 0f);
                    // ⭕ 駒の実寸は `const.parts` が持つ(部材方の実測)。⛔ 当て推量しない
                    string partKey = gpath == null ? null : System.IO.Path.GetFileNameWithoutExtension(gpath);
                    var parts = O(Get(O(D["const"]), "parts"));
                    float realW = (parts != null && partKey != null && Has(parts, partKey))
                                ? F(parts[partKey]) : 0f;
                    Vector2 gc = f.W(Mathf.Lerp(au, bu, tc), Mathf.Lerp(avv, bvv, tc));
                    float gy = Graded.At(gc.x, gc.y); if (float.IsNaN(gy)) gy = EdoBuild.Ground(gc.x, gc.y);
                    if (gpath == null || AssetDatabase.LoadAssetAtPath<GameObject>(gpath) == null)
                        missing.Add(nm + " の" + (isMon ? "中門" : "木戸") + " " + wM.ToString("0.##") + "m");
                    else
                    {
                        var gg = EdoBuild.Place(gpath, new Vector3(gc.x, gy, gc.y), yaw, Vector3.one,
                                                grp, nm + "_Kido");
                        if (gg != null) gates++;
                    }
                    if (realW <= 0f)
                    {
                        wait.Add("結界 " + nm + ": 開口の駒の実寸が `const.parts` に無い(" + (partKey ?? "?")
                               + ")— 開口の呼び " + wM.ToString("0.##") + "m で割った(⛔ 当て推量)");
                        realW = wM;
                    }
                    float halfT = (realW / ken) * 0.5f / lenKen;
                    cuts.Add(new float[] { tc - halfT, tc + halfT });
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

    // ---------------------------------------------------------------- 法肩の竹垣
    /// <summary>**法肩の竹垣(四つ目垣)**。⚠ 2026-09-04 まで**据える処理が無かった**上、
    /// 最初に通したときは在庫の `Eg.TakeGaki`(竹の**菱格子=網代風**で四つ目垣ではない)を
    /// **非一様スケール**で伸ばしていた。⛔ どちらも誤り — 部材方の指摘で `Own.YotsumeGaki(h)` へ。
    ///
    /// 【据え】⭕ **bbox がちょうど1間**なので `scale = Vector3.one` で **1.818 で突き付ける**。
    /// ⛔ 伸縮しない(竹の太さと結びの間隔が変わる)。⛔ **`SeatBottom` を使わない** —
    /// 根入れ −0.15 のぶん浮く。`position.y = 地盤` を直に入れる。
    /// ⛔ run の +X 端に <c>YotsumeGakiPost(h)</c> を1本足す(足さないと胴縁が宙で終わる)。
    /// ⚠ 端数は**わずかに重ねて**吸う(⛔ 隙間を作らない — メモリ「門と塀の閉じは隙間>めり込み」)。
    ///
    /// 【丈】`impl.rails[].h` が持つ。焼いてあるのは 0.6 / 0.9 / 1.2 の3種で、
    /// ⛔ **無い丈は据えずに一覧へ出す**(勝手に近い丈へ寄せない — 見透しの遮蔽の計算が丈で決まる)。</summary>
    static string PlaceTakegaki(List<string> wait)
    {
        if (Stale("rails")) { wait.Add("法肩の竹垣: 算出物 rails が前の指図のまま ── 据えない"); var gr = Group("Fuzoku/Takegaki"); Clear(gr); return "竹垣: 据え置きの欄"; }
        var rails = A(Get(IMPL, "rails"));
        if (rails == null) { wait.Add("算出物に rails(法肩の竹垣)が無い"); return "竹垣: 算出物待ち"; }
        var grp = Group("Fuzoku/Takegaki"); Clear(grp);
        const float SPAN = 1.818f;
        var baked = new float[] { 0.6f, 0.9f, 1.2f };
        int made = 0, posts = 0, runs = 0; var noH = new HashSet<string>();
        foreach (var o in rails)
        {
            var r = O(o); if (r == null) continue;
            var pts = A(Get(r, "world"));
            if (pts == null || pts.Count < 2) continue;
            string nm = S(r["name"]);
            float h = Has(r, "h") ? F(r["h"]) : C("takegakiH");
            // ⛔ 焼いていない丈へ勝手に寄せない
            bool ok = false;
            foreach (var bh in baked) if (Mathf.Abs(bh - h) < 0.001f) ok = true;
            if (!ok) { noH.Add(h.ToString("0.##")); continue; }
            string span = EdoAssets.Own.YotsumeGaki(h), post = EdoAssets.Own.YotsumeGakiPost(h);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(span) == null)
            { noH.Add(h.ToString("0.##")); continue; }
            runs++;
            Vector2 last = Vector2.zero; float lastYaw = 0f; bool any = false;
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                var a1 = A(pts[i]); var b1 = A(pts[i + 1]);
                if (a1 == null || b1 == null) continue;
                Vector2 P0 = new Vector2(F(a1[0]), F(a1[1])), P1 = new Vector2(F(b1[0]), F(b1[1]));
                float len = (P1 - P0).magnitude;
                if (len < 0.05f) continue;
                // ⚠ 端数は**重ねて**吸う(⛔ 隙間を作らない)。1間ちょうどの区間で余計な1枚を足さない
                int n = Mathf.Max(1, Mathf.CeilToInt(len / SPAN - 0.02f));
                float pitch = len / n;
                Vector2 dir = (P1 - P0) / len;
                float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
                for (int k = 0; k < n; k++)
                {
                    Vector2 c = P0 + dir * (pitch * (k + 0.5f));
                    float y = Graded.At(c.x, c.y); if (float.IsNaN(y)) y = EdoBuild.Ground(c.x, c.y);
                    // ⛔ SeatBottom を使わない(根入れ −0.15 のぶん浮く)
                    var go = EdoBuild.Place(span, new Vector3(c.x, y, c.y), yaw, Vector3.one,
                                            grp, nm + "_" + made);
                    if (go != null) made++;
                }
                last = P1; lastYaw = yaw; any = true;
            }
            // ⛔ run の +X 端に親柱を1本
            if (any && AssetDatabase.LoadAssetAtPath<GameObject>(post) != null)
            {
                float y = Graded.At(last.x, last.y); if (float.IsNaN(y)) y = EdoBuild.Ground(last.x, last.y);
                var gp = EdoBuild.Place(post, new Vector3(last.x, y, last.y), lastYaw, Vector3.one,
                                        grp, nm + "_Post");
                if (gp != null) posts++;
            }
        }
        if (noH.Count > 0)
            wait.Add("法肩の竹垣: 焼いていない丈 " + string.Join(" / ", new List<string>(noH).ToArray())
                   + "m の run を据えなかった(⛔ 近い丈へ寄せない — 見透しの遮蔽が丈で決まる)"
                   + " → build_okabe_niwa.py -- yotsumegaki");
        int outR = EdoBuild.RetireOutsidePoly(grp, Poly, wait, "法肩の竹垣(算出物 rails)");   // 硬い・区域(EDO-0502)
        return "法肩の竹垣: " + made + " スパン + 親柱 " + posts + " / " + runs + " 本"
             + (outR > 0 ? "(区画の外の " + outR + " 個を退けた)" : "");
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
            if (Has(k, "a") && Has(k, "b") && Has(k, "yBot") && Has(k, "yTop"))
            { made += PlaceKaidanAB(grp, k, wait); continue; }   // 案1の書式(EDO-0502)
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

    /// <summary>**石段の袖**(指図 kaidans[].sode・普請方の設計 2026-10-07・EDO-0502)── 土留めを切って張り出す石段の両脇を袖石垣で受ける。
    /// 土留めを据えた後に呼ぶ(上端の相手 = 石段が切った土留め terraceWalls[].cuts の駒)。据えは `EdoBuild.PlaceIshidanSodeRow`
    /// (段ごとの袖の駒を段石の小口・段鼻・踏面で測って据え、上端は土留めの見え面で入隅に止め、下端は同じ駒を継いで小口を沈める)。
    /// 数は指図の文から読む:「段鼻を結ぶ線より x 上」(笠の上がりの狙い【柔】)・「小口を y 以上地中へ」【硬】(⛔ 読めなければ ★ を刷って建てない)。
    /// 駒は `EdoAssets.Own.IshidanSodeUchikomi(蹴上, 踏面, i, 丈)`(打込接ぎ・厚み 0.30・柄は i%9・丈は `IshidanSodeDepthsDeep`)。袖の名は "Sode_" で始める ──
    /// 口の端を石段の駒から測る Stage2b(by + "_" の頭)に入れない。当たる先: kaidans[].sode を持つ石段(岡部 K_Kuruwa)。</summary>
    static string PlaceKaidanSodes(Transform danGrp)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        var kai = Group("Fuzoku/Kaidan");
        foreach (var o in A(Get(D, "kaidans")) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue;
            string nm = S(Get(k, "name")), txt = S(Get(k, "sode")); if (nm == null || txt == null) continue;
            // 追記で上書きされた値は最後の物を採る(sode 追記 2026-10-08: 切石の袖・段鼻の線より 0.30 上)
            var mks = System.Text.RegularExpressions.Regex.Matches(txt, @"段鼻を結ぶ線より\s*([0-9.]+)\s*上");
            var mk = mks.Count > 0 ? mks[mks.Count - 1] : System.Text.RegularExpressions.Regex.Match(txt, @"段鼻を結ぶ線より\s*([0-9.]+)\s*上");
            // 型 = 最後の追記の節が「切石の袖」を名指せば切石(IshidanSode)・無ければ打込接ぎ(IshidanSodeUchikomi)
            int lastAdd = txt.LastIndexOf("追記"); string lastSec = lastAdd >= 0 ? txt.Substring(lastAdd) : txt;
            bool kiriishi = lastSec.Contains("切石の袖");
            // 上がり口の段石の脇には袖を立てない(sode 追記 2026-10-08「上がり口の段石の脇には袖を立てず門の内の地表で受ける」)
            bool skipTop = lastSec.Contains("上がり口の段石の脇には袖を立て");
            var ms = System.Text.RegularExpressions.Regex.Match(txt, @"小口を\s*([0-9.]+)\s*以上地中");
            if (!mk.Success || !ms.Success || !Has(k, "yTop") || !Has(k, "yBot") || !Has(k, "steps"))
            { sb.AppendLine("  ★ 石段の袖 " + nm + ": 指図から読めない(" + (mk.Success ? "" : "笠の上がり ") + (ms.Success ? "" : "小口の沈め") + ")── 建てない"); continue; }
            float kasaT = float.Parse(mk.Groups[1].Value, inv), sink = float.Parse(ms.Groups[1].Value, inv);
            float rise = (F(k["yTop"]) - F(k["yBot"])) / Mathf.Max(1, (int)F(k["steps"])), fumi = Has(k, "fumi") ? F(k["fumi"]) : 0.45f;
            // 上端の相手 = この石段が切った土留めの駒
            var walls = new List<GameObject>();
            foreach (var to in A(Get(D, "terraceWalls")) ?? new List<object>())
            {
                var tw = O(to); if (tw == null || S(Get(tw, "cuts")) != nm) continue; string twn = S(Get(tw, "name"));
                foreach (Transform c in danGrp) if (c.gameObject.activeInHierarchy && c.name.StartsWith(twn + "_")) walls.Add(c.gameObject);
            }
            // 段石の列(下から・据えた順)。段 = 名の最後の "_j" を除いた頭。⛔ 積み(_tsumi)は段でない
            var rows = new List<List<GameObject>>(); var rowKey = new List<string>();
            foreach (Transform c in kai)
            {
                if (!c.name.StartsWith(nm + "_") || c.name.Contains("_tsumi")) continue;
                int u = c.name.LastIndexOf('_'); string key = c.name.Substring(0, u);
                if (skipTop && key == nm + "_top") continue;
                int ri = rowKey.IndexOf(key); if (ri < 0) { rowKey.Add(key); rows.Add(new List<GameObject>()); ri = rows.Count - 1; }
                rows[ri].Add(c.gameObject);
            }
            if (rows.Count < 2) { sb.AppendLine("  ★ 石段の袖 " + nm + ": 段石が据わっていない ── 建てない"); continue; }
            foreach (int side in new[] { 1, -1 })
            {
                var dans = new List<GameObject>();
                foreach (var row in rows)
                {   // その側の端の段石(段石の +X の向きで最も外)
                    GameObject best = null; float bv = float.MinValue;
                    foreach (var g in row) { float v = side * Vector3.Dot(g.transform.position, row[0].transform.right); if (v > bv) { bv = v; best = g; } }
                    dans.Add(best);
                }
                var warn = new List<string>(); EdoBuild.SodeRowReport rep; float rr = rise, ff = fumi;
                var got = EdoBuild.PlaceIshidanSodeRow(dans, side, (i, d) => kiriishi ? EdoAssets.Own.IshidanSode(rr, ff, i, d) : EdoAssets.Own.IshidanSodeUchikomi(rr, ff, i, d), EdoAssets.Own.IshidanSodeDepthsDeep,
                                                       kai, "Sode_" + nm + (side > 0 ? "_R" : "_L"), kasaT, 0f, walls, sink, SkinGround, 0.05f, warn, out rep);
                sb.AppendLine("  石段の袖 " + nm + (side > 0 ? " 右" : " 左") + "(" + (kiriishi ? "切石" : "打込接ぎ") + (skipTop ? "・上がり口の脇なし" : "") + "): 段の脇 " + rep.placed + " 駒・坂下へ継いだ " + rep.ext + " 駒・退けた " + rep.refused
                            + "・笠の上がり " + rep.kasa.ToString("F3") + "(狙い " + kasaT.ToString("F2") + ")"
                            + (rep.faceHit ? "・入隅: 面の位置の天端 − 相手の天端 " + rep.atFace.ToString("+0.000;-0.000") + "・相手の中で越える " + rep.overCrest.ToString("F3") : "・上端の相手なし")
                            + "・坂下の小口の沈み " + rep.endSink.ToString("F2") + (rep.sinkOk ? "" : " ⛔") + "(相手の駒 " + walls.Count + ")");
                foreach (var w in warn) sb.AppendLine("    " + w);
            }
        }
        return sb.ToString();
    }

    static bool RouteExists(string nm)
    {
        foreach (var o in A(Get(D, "routes")) ?? new List<object>()) { var r = O(o); if (r != null && S(Get(r, "name")) == nm) return true; }
        return false;
    }

    /// <summary>石段の平面の両端(世界 xz)。坂の上の石段(`atRoute`・`atS`[m]・`planeLen`[m])は**坂の芯の道のり atS ± planeLen/2 から解く**
    /// (EDO-0502 第31巡 ── 欄の a・b は従属値で、atS・planeLen を上書きしても古いまま残り、8 段の石段が 1.8m に詰まる)。
    /// 坂を名指さない石段は欄の a・b。同じ解き方を python `build_sashizu.kaidan_ab_on_route` が持つ。
    /// 硬い/柔らかい: どちらでもない(読み)── 解けなければ false(a・b も無い)。</summary>
    static bool KaidanAB(Dictionary<string, object> k, out Vector2 a, out Vector2 b)
    {
        a = b = Vector2.zero; var f = Grid;
        string rn = S(Get(k, "atRoute"));
        if (rn != null && Has(k, "atS") && Has(k, "planeLen"))
        {
            foreach (var ro in A(Get(D, "ramps")) ?? new List<object>())
            {
                var r = O(ro); if (r == null || S(Get(r, "name")) != rn) continue;
                var line = new List<Vector2>(); foreach (var q in A(Get(r, "pts")) ?? new List<object>()) { var v = A(q); line.Add(f.W(F(v[0]), F(v[1]))); }
                if (line.Count < 2) break;
                float s = F(k["atS"]), pl = F(k["planeLen"]); Vector2 d;
                a = EdoBuild.ArcPoint(line, s - pl * 0.5f, out d); b = EdoBuild.ArcPoint(line, s + pl * 0.5f, out d);
                return true;
            }
        }
        if (!Has(k, "a") || !Has(k, "b")) return false;
        var av = A(k["a"]); var bv = A(k["b"]);
        a = f.W(F(av[0]), F(av[1])); b = f.W(F(bv[0]), F(bv[1]));
        return true;
    }

    /// <summary>案1の石段の書式 `{a, b, yBot, yTop, steps, flights?, landingKen?, fumi, wKen, planeLen}`(EDO-0502)。
    /// ⭐ **a・b のどちらが足元かは指図に無い**(K_Tsuyo は a が下、K_Kuruwa は a が上)── 造成後の地盤を
    ///   両端の 0.5m 外で測り、低い方を足元に取る(測って決める・規則21)。
    /// 踏面 = (平面長 − 踊り場) / (段数 − 段の組の数)。蹴上 = (yTop − yBot)/段数。段石の**天端を踏面の高さ**へ
    /// (段石の上面が踏む面・触れる所は上面と段の下の段石)。踊り場は最初の組の最後の蹴上の高さで敷く。
    /// ⛔ 袖(袖石垣)と段の掘割の皮はまだ据えない ── EdoBuildIshidan の組へ移すのは次の巡(報告に出す)。</summary>
    /// <summary>**石段の段石の両端を脇の土留めの見え面まで伸ばす**(EdoBuild.ExtendEndToFace・2026-10-08 EDO-0502 第53巡 施主指摘
    /// 「K_Dan1 の段の右端と袖石垣の間に黒い三角の隙」)。段の幅は指図 wKen で一定、脇の返しの石垣は法(勾配)なので、上の段ほど踏面の端と
    /// 石垣の面の間が開く(実測 6段目 0.41・上がり口 0.23)。各段の両端の段石を、踏面の天端の帯で相手の面へ光線を打って最も遠い当たりまで伸ばす
    /// (下は法の中へ入る ── 隠れる)。積み(_tsumi)は前の段の後ろに隠れるので触らない。当たりが無い端(脇が地山・面が 0.6m より遠い)は触らない。
    /// ⛔ 袖(kaidans[].sode)を持つ石段は袖が段石の小口に付くので伸ばさない。硬い(隙 0 ── 天端の帯の口)。
    /// 当たる先: 土留めを切って通る袖の無い石段(岡部 K_Dan1・K_Dan2・K_Tsuyo)。</summary>
    static string ExtendKaidanEndsToWalls(Transform walls)
    {
        var root = GameObject.Find(GN); var kai = root == null ? null : root.transform.Find("Fuzoku/Kaidan");
        if (kai == null) return "";
        var sb = new System.Text.StringBuilder();
        foreach (var o in A(D["kaidans"]) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue; string nm = S(k["name"]);
            if (Get(k, "sode") != null) continue;
            if (Get(k, "sideFace") != null) continue;   // 指図 sideFace(2026-10-08)【硬】段石は脇の面まで伸ばさない ── 見え面を段の端の線へ(StairGaps)
            var rows = new Dictionary<string, List<Transform>>();
            foreach (Transform c in kai)
            {
                if (!c.gameObject.activeInHierarchy || !c.name.StartsWith(nm + "_") || c.name.Contains("_tsumi")) continue;
                string key = c.name.Substring(0, c.name.LastIndexOf('_'));
                if (!rows.ContainsKey(key)) rows[key] = new List<Transform>(); rows[key].Add(c);
            }
            if (rows.Count == 0) continue;
            Bounds bb = new Bounds(); bool first = true;
            foreach (var r in rows.Values) foreach (var c in r) { var b = EdoBuild.RB(c.gameObject); if (first) { bb = b; first = false; } else bb.Encapsulate(b); }
            bb.Expand(new Vector3(2f, 2f, 2f));
            var mates = new List<GameObject>();
            foreach (Transform w in walls) if (w.gameObject.activeInHierarchy && EdoBuild.RB(w.gameObject).Intersects(bb)) mates.Add(w.gameObject);
            if (mates.Count == 0) continue;
            int ext = 0, none = 0; float mx = 0f, worst = 0f;
            foreach (var r in rows.Values)
            {
                var ax = r[0].right; ax.y = 0f; ax.Normalize();
                foreach (float sg in new[] { 1f, -1f })
                {
                    Transform e = null; float bv = float.MinValue;
                    foreach (var c in r) { float v = sg * Vector3.Dot(c.position, ax); if (v > bv) { bv = v; e = c; } }
                    float yTop = EdoBuild.RB(e.gameObject).max.y, spread; int hits;
                    float got = EdoBuild.ExtendEndToFace(e.gameObject, ax * sg, mates, yTop, 0.6f, out spread, out hits);
                    if (float.IsNaN(got)) { none++; continue; }
                    if (got > 1e-3f) { ext++; mx = Mathf.Max(mx, got); }
                    float gw = EdoBuild.MeasureEndGap(e.gameObject, ax * sg, mates, yTop); if (!float.IsNaN(gw)) worst = Mathf.Max(worst, gw);
                }
            }
            sb.AppendLine("  石段 " + nm + " の段石の端を脇の土留めの面へ: 伸ばした " + ext + " 端(最大 " + mx.ToString("F3") + "m)・相手の無い端 " + none + "・残る天端の口の最大 " + worst.ToString("F3") + "m" + (worst > 0.005f ? " ⛔" : " ⭕"));
        }
        return sb.ToString();
    }

    /// <summary>**sideFace の実測**(指図 kaidans[].sideFace・EDO-0502 第57巡)── 各段の列の芯から踏面の天端 +0.05 の高さで左右へ光線を打ち、
    /// 脇の土留めの見え面までの距離 − 段の半幅(= 見え面と段の端の線の差。正 = 面が外・負 = 面が段の内へ出る)と、段石の端 − 見え面(差し込み)を刷る。
    /// 硬い: |差| ≤ 0.05(野面の石の出入り)。測るだけ(⛔ 寄せない)。当たる先: sideFace を持つ石段。</summary>
    static string MeasureSideFaces(Transform walls)
    {
        var root = GameObject.Find(GN); var kai = root == null ? null : root.transform.Find("Fuzoku/Kaidan");
        if (kai == null) return "";
        var sb = new System.Text.StringBuilder(); var wl = new List<GameObject>(); foreach (Transform c in walls) if (c.gameObject.activeInHierarchy) wl.Add(c.gameObject);
        foreach (var o in A(D["kaidans"]) ?? new List<object>())
        {
            var k = O(o); if (k == null || Get(k, "sideFace") == null) continue; string nm = S(k["name"]);
            float halfW = (Has(k, "wKen") ? F(k["wKen"]) : 1f) * C("ken") * 0.5f;
            var rows = new Dictionary<string, List<Transform>>();
            foreach (Transform c in kai) { if (!c.gameObject.activeInHierarchy || !c.name.StartsWith(nm + "_") || c.name.Contains("_tsumi")) continue; string rk = c.name.Substring(0, c.name.LastIndexOf('_')); if (!rows.ContainsKey(rk)) rows[rk] = new List<Transform>(); rows[rk].Add(c); }
            float worst = 0f, insMin = float.MaxValue, wMin = float.MaxValue, wMax = float.MinValue; int n = 0, none = 0; var det = new List<string>();
            foreach (var kv in rows)
            {
                var ax = kv.Value[0].right; ax.y = 0f; ax.Normalize();
                Bounds b = EdoBuild.RB(kv.Value[0].gameObject); foreach (var c in kv.Value) b.Encapsulate(EdoBuild.RB(c.gameObject));
                float lo = float.MaxValue, hi = float.MinValue; foreach (var c in kv.Value) foreach (var v in EdoBuild.Body(c, 4000)) { float u = Vector3.Dot(v - b.center, ax); lo = Mathf.Min(lo, u); hi = Mathf.Max(hi, u); }
                wMin = Mathf.Min(wMin, hi - lo); wMax = Mathf.Max(wMax, hi - lo);
                var o3 = new Vector3(b.center.x, b.max.y + 0.05f, b.center.z); string row = kv.Key.Substring(nm.Length + 1);
                foreach (float sg in new[] { 1f, -1f })
                {
                    float h = EdoBuild.RayToBodies(wl, o3, ax * sg, halfW + 1.5f);
                    if (float.IsNaN(h)) { none++; det.Add(row + (sg > 0 ? "右" : "左") + " 面なし"); continue; }
                    float d = h - halfW, ins = (sg > 0 ? hi : -lo) - h; n++;
                    if (Mathf.Abs(d) > Mathf.Abs(worst)) worst = d; insMin = Mathf.Min(insMin, ins);
                    det.Add(row + (sg > 0 ? "右" : "左") + " " + d.ToString("+0.00;-0.00"));
                }
            }
            sb.AppendLine("  sideFace " + nm + ": 段の幅(段石の端から端)" + wMin.ToString("F3") + "〜" + wMax.ToString("F3") + "・見え面 − 端の線 最悪 " + worst.ToString("+0.000;-0.000") + "m(" + n + " 点・面なし " + none + ")"
                        + "・段石の差し込み 最小 " + (insMin == float.MaxValue ? "-" : insMin.ToString("F3")) + (Mathf.Abs(worst) > 0.05f || none > 0 ? " ⛔" : " ⭕") + "\n    " + string.Join(" / ", det.ToArray()));
        }
        return sb.ToString();
    }

    /// <summary>**上がり口の段石の背の平らな面**(指図 kaidans[].topStep「背の地盤は天端 − x」・topStepBackFlat の奥行【硬】・EDO-0502 第58巡)。
    /// 据わった上がり口の段石(名 "<石段>_top_*")の実メッシュから解く: 上がる向き = 一段目の列 → 上がり口の列、面 = 段石の奥の縁(−0.05)から
    /// 奥行ぶん奥まで・横は段石の端から端、高さ = 段石の天端 − x。皮の平らな面として渡す(Stage3b)。読めない欄は ★ を刷って起こさない。
    /// 当たる先: topStep を持つ石段すべて(岡部 K_Dan1・K_Dan2・K_Tsuyo・K_Kuruwa ── 坂の有無を問わない)。</summary>
    static List<EdoBuild.SkinFace> TopLandingFaces(System.Text.StringBuilder sb)
    {
        var res = new List<EdoBuild.SkinFace>(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        var root = GameObject.Find(GN); var kai = root == null ? null : root.transform.Find("Fuzoku/Kaidan"); if (kai == null) return res;
        foreach (var o in A(Get(D, "kaidans")) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue; string nm = S(Get(k, "name")), ts = S(Get(k, "topStep")); if (nm == null || ts == null) continue;
            var mb = System.Text.RegularExpressions.Regex.Match(ts, @"背の地盤は天端\s*[−\-]\s*([0-9.]+)");
            var mf = System.Text.RegularExpressions.Regex.Match(S(Get(k, "topStepBackFlat")) ?? "", @"^\s*([0-9.]+)");
            if (!mb.Success) { sb.AppendLine("  ★ 上がり口の背の面 " + nm + ": topStep の背の地盤が読めない ── 起こさない"); continue; }
            float drop = float.Parse(mb.Groups[1].Value, inv), flat = mf.Success ? float.Parse(mf.Groups[1].Value, inv) : TOPSTEP_BACK_FLAT;
            var tops = new List<Transform>(); var first = new List<Transform>();
            foreach (Transform c in kai) { if (!c.gameObject.activeInHierarchy) continue; if (c.name.StartsWith(nm + "_top_")) tops.Add(c); else if (c.name.StartsWith(nm + "_1_")) first.Add(c); }
            if (tops.Count == 0 || first.Count == 0) { sb.AppendLine("  ★ 上がり口の背の面 " + nm + ": 上がり口の段石が据わっていない ── 起こさない"); continue; }
            Bounds bt = EdoBuild.RB(tops[0].gameObject); foreach (var t in tops) bt.Encapsulate(EdoBuild.RB(t.gameObject));
            Bounds b1 = EdoBuild.RB(first[0].gameObject); foreach (var t in first) b1.Encapsulate(EdoBuild.RB(t.gameObject));
            Vector2 c0 = new Vector2(bt.center.x, bt.center.z), up = (c0 - new Vector2(b1.center.x, b1.center.z)).normalized, side = new Vector2(-up.y, up.x);
            float u1 = float.MinValue, l0 = float.MaxValue, l1 = float.MinValue;
            foreach (var t in tops) foreach (var v in EdoBuild.Body(t, 4000)) { Vector2 r = new Vector2(v.x, v.z) - c0; u1 = Mathf.Max(u1, Vector2.Dot(r, up)); float l = Vector2.Dot(r, side); l0 = Mathf.Min(l0, l); l1 = Mathf.Max(l1, l); }
            float y = bt.max.y - drop; Vector2 pa = c0 + up * (u1 - 0.05f), pb = c0 + up * (u1 + flat);
            res.Add(new EdoBuild.SkinFace("TopLanding_" + nm, new[] { pa + side * l1, pb + side * l1, pb + side * l0, pa + side * l0 }, y, TOPSTEP_BACK_TOL));
            sb.AppendLine("  面 TopLanding_" + nm + "(" + y.ToString("F2") + "): 上がり口の段石の背 " + flat.ToString("0.0#") + "m・幅 " + (l1 - l0).ToString("F2") + "m(据わった段石から)");
        }
        return res;
    }

    static int PlaceKaidanAB(Transform grp, Dictionary<string, object> k, List<string> wait)
    {
        var f = Grid; float ken = C("ken");
        string nm = S(k["name"]);
        Vector2 A0, B0; KaidanAB(k, out A0, out B0);
        float L = (B0 - A0).magnitude; if (L < 0.3f) { wait.Add("石段 " + nm + ": a と b が近すぎる"); return 0; }
        Vector2 dir = (B0 - A0) / L;
        float ya = Graded.At((A0 - dir * 0.5f).x, (A0 - dir * 0.5f).y), yb = Graded.At((B0 + dir * 0.5f).x, (B0 + dir * 0.5f).y);
        if (!float.IsNaN(ya) && !float.IsNaN(yb) && ya > yb) { var t0 = A0; A0 = B0; B0 = t0; dir = -dir; }
        float yBot = F(k["yBot"]), yTop = F(k["yTop"]);
        int steps = Mathf.Max(1, (int)F(k["steps"]));
        var fl = new List<int>();
        foreach (var q in A(Get(k, "flights")) ?? new List<object>()) fl.Add((int)F(q));
        if (fl.Count == 0) fl.Add(steps);
        float landing = Has(k, "landingKen") ? F(k["landingKen"]) * ken : 0f;
        float tread = (L - landing * (fl.Count - 1)) / Mathf.Max(1, steps - fl.Count);
        float rise = (yTop - yBot) / steps;
        float wid = (Has(k, "wKen") ? F(k["wKen"]) : 1f) * ken;
        // 指図 kaidans[].sideFace(2026-10-08)【硬】: 段石は脇の面まで伸ばさない ── 幅は全段一定、端は見え面の内へ x 差し込んで隠す
        //   ⇒ 段石の幅 = 段の幅 + 2x(見え面 = 段の端の線は Stage2b の StairGaps が返しの天端の線で合わせる)。読めなければ ★ で幅のまま
        {
            string sfx = S(Get(k, "sideFace"));
            if (sfx != null)
            {
                var mi = System.Text.RegularExpressions.Regex.Match(sfx, @"見え面の内へ\s*([0-9.]+)\s*差し込");
                if (mi.Success) { float ins = float.Parse(mi.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture); wid += 2f * ins; wait.Add("石段 " + nm + ": sideFace ── 段石の幅 " + (wid - 2f * ins).ToString("F3") + " + 両端 " + ins.ToString("F2") + " の差し込み = " + wid.ToString("F3") + "(全段一定)"); }
                else wait.Add("★ 石段 " + nm + ": sideFace の差し込みが指図から読めない ── 段の幅のまま");
            }
        }
        if (Has(k, "fumi") && Mathf.Abs(tread - F(k["fumi"])) > 0.02f)
            wait.Add("石段 " + nm + ": a〜b の長さ " + L.ToString("F2") + "m から出る踏面 " + tread.ToString("F3")
                   + "m が指図の fumi " + F(k["fumi"]).ToString("0.###") + " と違う(据えは a〜b に合わせた)");
        Vector2 side = new Vector2(dir.y, -dir.x);
        // 段石 = 切石(指図 danStone・EDO-0502 2026-10-06 夕)── 欄の蹴上に最も近い焼けた段石(⛔ 汐見坂の DanishiStep2m は石垣の肌)。
        //   幅と踏面は札(綴りの値)から伸縮し、据えは EdoBuild.PlaceDanStone が段鼻・小口・上面を実メッシュで測って寄せる
        Func<int, string> danOf = i => EdoAssets.Own.SannoDanNearestKeri(rise, Has(k, "fumi") ? F(k["fumi"]) : 0.45f, 1.818f, i);
        float dk0, df0, dw0;
        if (danOf(0) == null || danOf(1) == null || !EdoAssets.Own.SannoDanSpec(danOf(0), out dk0, out df0, out dw0))
        { wait.Add("石段 " + nm + ": 切石の段石が焼けていない(蹴上 " + rise.ToString("F3") + ")── 据えない"); return 0; }
        if (dk0 + 0.18f < rise - 1e-3f) wait.Add("石段 " + nm + ": 段石の丈 " + (dk0 + 0.18f).ToString("F3") + " が蹴上 " + rise.ToString("F3") + " に足りない(蹴上の面に口)");
        int across = Mathf.Max(1, Mathf.RoundToInt(wid / dw0));
        int made = 0, riser = 0, stacked = 0, seq = 0; float x = 0f;
        System.Action<float, float, float, string> lay = delegate(float xs, float len, float top, string tag)
        {
            int nAlong = Mathf.Max(1, Mathf.CeilToInt(len / Mathf.Max(0.3f, tread) - 0.01f));
            for (int a2 = 0; a2 < nAlong; a2++)
                for (int j = 0; j < across; j++)
                {
                    float tt = (j - (across - 1) * 0.5f) * (wid / across);
                    Vector2 nose = A0 + dir * (xs + len * a2 / nAlong) + side * tt;
                    string pth = danOf(seq++);
                    var go = EdoBuild.PlaceDanStone(pth, grp, nm + "_" + tag + "_" + a2 + "_" + j, nose, dir, top, wid / across, len / nAlong);
                    if (go == null) continue;
                    made++;
                    // 硬い・浮き 0: 下の面へ張り出す段は、段石の下を同じ切石で接地まで積む(EdoBuild.StackDownToGround・指図 danStone「積みも同じ切石」)
                    stacked += EdoBuild.StackDownToGround(go, pth, grp, go.name, 12, wait, SkinGround);   // 皮が描く面で測る(第6巡)
                }
        };
        for (int fi = 0; fi < fl.Count; fi++)
        {
            for (int i = 1; i <= fl[fi]; i++)
            {
                riser++;
                if (riser >= steps) break;                         // 最後の蹴上は上の面へ上がる(上がり口の段石は topStep)
                float top = yBot + rise * riser;
                if (i == fl[fi] && fi < fl.Count - 1) { lay(x, landing, top, "odoriba"); x += landing; }
                else { lay(x, tread, top, riser.ToString()); x += tread; }
            }
        }
        // 上がり口の段石(指図 kaidans[].topStep・2026-10-06 夕)【硬】: 最後の蹴上の上に、天端 = 上の面・奥行 ≥ 欄の値の段石を一段
        string ts = S(Get(k, "topStep"));
        if (ts != null)
        {
            var mt = System.Text.RegularExpressions.Regex.Match(ts, @"天端は[^0-9]*([0-9]+\.[0-9]+)");
            var md = System.Text.RegularExpressions.Regex.Match(ts, @"奥行\s*([0-9.]+)\s*以上");
            if (!mt.Success || !md.Success) wait.Add("★ 石段 " + nm + ": topStep の天端・奥行が指図から読めない ── 上がり口の段石を据えない");
            else
            {
                float yt = float.Parse(mt.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
                float dp = Mathf.Max(tread, float.Parse(md.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture));
                if (Mathf.Abs(yt - yTop) > 0.005f) wait.Add("石段 " + nm + ": topStep の天端 " + yt.ToString("F2") + " が yTop " + yTop.ToString("F2") + " と違う(topStep で据えた)");
                lay(x, dp, yt, "top");
                wait.Add("石段 " + nm + ": 上がり口の段石 天端 " + yt.ToString("F2") + "・奥行 " + dp.ToString("F2") + "(道のり " + x.ToString("F2") + "〜" + (x + dp).ToString("F2") + ")");
                x += dp;
            }
        }
        wait.Add("石段 " + nm + ": 切石の段石 " + System.IO.Path.GetFileNameWithoutExtension(danOf(0)) + "/b(蹴上 " + rise.ToString("F3") + "・踏面 " + tread.ToString("F3") + "・幅 " + (wid / across).ToString("F3") + " × " + across + ")");
        if (stacked > 0) wait.Add("石段 " + nm + ": 下の面へ張り出す段の下を同じ切石で接地まで積んだ " + stacked + " 個");
        return made;
    }

    // ---------------------------------------------------------------- 参道
    /// <summary>参道(表門の軸を通る白洲)。⭕ **屋根を架けない**(2026-08-19 ユーザー裁定 —
    /// 前庭は開けた白洲で、屋根は式台・車寄せまで)。実体は**地表の塗り**なので、
    /// ここでは物を据えず、地表の巡(スプラット)へ渡す。</summary>
    static string PlaceSando(List<string> wait)
    {
        var sd = O(Get(D, "sando"));
        if (sd == null) return "参道: 指図に sando が無い";
        // 案1(EDO-0502): 参道は `{route, wKen, layer}`(動線 routes[route] を幅 wKen 間で layer に塗る)
        wait.Add("参道(動線 " + S(Get(sd, "route")) + "・幅 " + F(Get(sd, "wKen")).ToString("0.##")
               + "間・地表 " + (S(Get(sd, "layer")) ?? "?") + "): 据える物は無い(白洲=地表の塗り)。⭕ 地表の巡で受ける"
               + (RouteExists(S(Get(sd, "route"))) ? "" : " ── ⚠ 指図の routes に " + S(Get(sd, "route")) + " が無い"));
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
        if (Stale("gardens"))
            return "庭: ⛔ 算出物 gardens が前の指図のまま(baked.carried)── 据えない" + RetireStaleGroup("Niwa", "gardens")
                 + "\n" + AnkyoReport();
        var items = A(Get(IMPL, "gardens"));
        if (items == null)
        { return "庭: 算出物に gardens が無い — ⛔ main に焼き手が無い欄(EDO-0386)。掲示板へ起票すること"; }

        var grp = Group("Niwa"); Clear(grp);
        // ⭐ 前の巡で RetireStaleGroup が退けた群(非活性)を起こす ── 非活性の下に据えると子が測れず SeatOnGround が投げる(EDO-0502 第59巡)
        if (!grp.gameObject.activeSelf) grp.gameObject.SetActive(true);
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
            // ---- 据えるのに要る値が指図に無い行(焼き手 impl_okabe.bake_gardens が `wait` を付ける)── 据えずに名乗る
            if (Has(g, "wait")) { wait.Add("庭 " + S(g["name"]) + "(" + kind + "): " + S(g["wait"])); continue; }

            // ---- 地表の塗り(スプラット)は**地表の輪**が受け持つ。ここでは据えない
            if (key != null && key.StartsWith("L_")) { splat++; continue; }
            // ---- 地形そのもの(汀線・池・築山・中島の輪郭・庭の実形)は S1 が彫った
            if (key == null) { terrainOwned++; continue; }

            // ⚠ **部材ごとに据え方が違う**(ピボットも正規化の軸も別)。⛔ 一律に置かない。
            var sub = Group("Niwa/" + kind.Replace("(", "_").Replace(")", "").Replace("・", "_"));
            int n0 = PlaceNiwaItem(sub, g, kind, key, pts, missing, wait);
            n0 -= EdoBuild.RetireOutsidePoly(sub, Poly, wait, "庭 " + kind + "(算出物 gardens)");   // 硬い・区域(EDO-0502)
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

    /// <summary>**水抜きの溝が道を通る区間(暗渠)を測る**(案1・EDO-0502・指図 gardens[].mizu.outflow.crossings)。
    /// 溝の芯(outflow.route)のうち、物資・家臣の道(routes の R_Katte・R_Kashin)の芯から道幅の半分(R_UraZaka の幅 1.5間 を
    /// 道の幅に採る ── routes は幅を持たないので、続く坂の幅)以内にある長さ。⭐ 全長を蓋にする(検図の参考・15巡)。
    /// ⛔ 蓋の切石の駒はまだ名指されていない(在庫方へ照会)ので据えず、区間と長さだけを出す。</summary>
    static string AnkyoReport()
    {
        var f = Grid; float ken = C("ken");
        Dictionary<string, object> mizu = null;
        foreach (var o in A(Get(D, "gardens")) ?? new List<object>()) { var g = O(o); var m = O(Get(g, "mizu")); if (m != null) mizu = m; }
        var of = O(Get(mizu, "outflow")); var rt = A(Get(of, "route"));
        if (rt == null) return "暗渠: 指図に outflow.route が無い";
        float half = 0f;
        foreach (var o in A(Get(D, "ramps")) ?? new List<object>()) { var r = O(o); if (r != null && S(r["name"]) == "R_UraZaka") half = (Has(r, "w") ? F(r["w"]) : F(r["wKen"]) * ken) * 0.5f; }
        var roads = new List<Vector2[]>();
        foreach (var o in A(Get(D, "routes")) ?? new List<object>())
        {
            var r = O(o); string nm = S(Get(r, "name")); if (nm != "R_Katte" && nm != "R_Kashin") continue;
            var pl = A(r["pts"]); var w = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); w[i] = f.W(F(q[0]), F(q[1])); }
            roads.Add(w);
        }
        // ⚠ 崖の区間は溝が坂(R_GakeZaka)の谷側の路肩を並んで走る(outflow.cliffDitch)── 道の下ではないので数えない。
        //   坂の下の端(芯の最後の点)と同じ溝の点から先だけを測る
        int kStart = 0;
        foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
        {
            var r = O(o); if (r == null || S(r["name"]) != "R_GakeZaka") continue;
            var gp = A(r["pts"]); var last = A(gp[gp.Count - 1]);
            for (int k = 0; k < rt.Count; k++) { var q = A(rt[k]); if (Mathf.Abs(F(q[0]) - F(last[0])) < 0.01f && Mathf.Abs(F(q[1]) - F(last[1])) < 0.01f) kStart = k; }
        }
        float tot = 0f; Vector2 a0 = Vector2.zero, a1 = Vector2.zero; bool any = false;
        for (int k = kStart; k + 1 < rt.Count; k++)
        {
            var qa = A(rt[k]); var qb = A(rt[k + 1]);
            Vector2 A0 = f.W(F(qa[0]), F(qa[1])), B0 = f.W(F(qb[0]), F(qb[1]));
            float L = (B0 - A0).magnitude; int n = Mathf.Max(1, Mathf.CeilToInt(L / 0.1f));
            for (int i = 0; i < n; i++)
            {
                Vector2 p = Vector2.Lerp(A0, B0, (i + 0.5f) / n); float bd = float.MaxValue;
                foreach (var w in roads) for (int j = 0; j + 1 < w.Length; j++) bd = Mathf.Min(bd, DistSeg(p, w[j], w[j + 1]));
                if (bd <= half) { tot += L / n; if (!any) a0 = p; a1 = p; any = true; }
            }
        }
        return "暗渠(溝が道の内を通る区間): " + tot.ToString("F1") + "m(道幅 " + (half * 2f).ToString("F2") + "m で測る・始 "
             + a0.x.ToString("F1") + "," + a0.y.ToString("F1") + " 〜 終 " + a1.x.ToString("F1") + "," + a1.y.ToString("F1")
             + ")── 全長を蓋。⛔ 蓋の切石の駒が未選定で据えない";
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
        // ⭐ **汀は地表と水面の交わり**(従属値・EDO-0502 第59巡)。指図の汀線は狙いで、描かれた地表(石組の岸の断面 + 2m 格子)では
        //   汀線の上の地表が水面より最大 0.56 低く、水面の縁が宙に浮いていた(557 点のうち 273)。⇒ 汀線を 0.5m に割り、各点を外向きの法線に沿って
        //   描かれた地表が水面 +0.02 に届く所まで出す(⛔ 内へは寄せない ── 地表が水面より高い所は水面が地表の下に隠れるので残す)。
        //   硬い: 水面の縁が地表の上に浮かない。出す量の上限 2.0m(届かなければ ⚠)。当たる先: 算出物の汀線で水面を張る全邸の池(土井・松江松平も同じ型)
        {
            var dr = EdoBuild.Drawn(); var src = wb.outline; int n0 = src.Count; float area = 0f;
            for (int i = 0; i < n0; i++) { var a = src[i]; var b = src[(i + 1) % n0]; area += a.x * b.z - b.x * a.z; }
            var dense = new List<Vector3>(); int pushed = 0, stuck = 0; float pmx = 0f;
            for (int i = 0; i < n0; i++)
            {
                Vector2 a = new Vector2(src[i].x, src[i].z), b = new Vector2(src[(i + 1) % n0].x, src[(i + 1) % n0].z);
                Vector2 t = (b - a).normalized, outN = area > 0f ? new Vector2(t.y, -t.x) : new Vector2(-t.y, t.x);   // 反時計回りなら右手が外
                int k = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude / 0.5f));
                for (int j = 0; j < k; j++)
                {
                    Vector2 p = Vector2.Lerp(a, b, j / (float)k); float o = 0f;
                    while (o <= 2.0f && dr.At(p.x + outN.x * o, p.y + outN.y * o) < wy + 0.02f) o += 0.05f;
                    if (o > 2.0f) { stuck++; o = 2.0f; }
                    if (o > 0f) { pushed++; pmx = Mathf.Max(pmx, o); }
                    dense.Add(new Vector3(p.x + outN.x * o, wy, p.y + outN.y * o));
                }
            }
            // ⛔ 継ぎの間へ点を足して外へ出す手は第61巡で外した(縁の向きが瓢箪のくびれで池の中へ折れ、水面の縁が池底を渡った)── 岸は皮が描く(Stage3b 池の岸の断面)
            {
                int nAll = 0, nLow = 0; float lowMx = 0f;
                for (int i = 0; i < dense.Count; i++)
                {
                    Vector2 a = new Vector2(dense[i].x, dense[i].z), b = new Vector2(dense[(i + 1) % dense.Count].x, dense[(i + 1) % dense.Count].z);
                    int k = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude / 0.1f));
                    for (int j = 0; j < k; j++) { var p = Vector2.Lerp(a, b, j / (float)k); float gy = dr.At(p.x, p.y); if (float.IsNaN(gy)) continue; nAll++; if (gy < wy - 0.005f) { nLow++; lowMx = Mathf.Max(lowMx, wy - gy); } }
                }
                wait.Add("水面: 縁を 0.1m で引いて地表が水面より低い点 " + nLow + "/" + nAll + "(最大 " + lowMx.ToString("F2") + "m・硬 0)");
            }
            wb.outline = dense; wb.sharp = new List<bool>(); foreach (var _ in dense) wb.sharp.Add(true);
            if (stuck > 0) wait.Add("水面: 汀の " + stuck + " 点は外へ 2.0m 出しても地表が水面に届かない(⚠ 水面の縁が浮く)");
            wait.Add("水面: 汀を描かれた地表と水面の交わりへ出した " + pushed + "/" + dense.Count + " 点(最大 " + pmx.ToString("F2") + "m・指図の汀線は狙い)");
        }
        wb.waterY = wy;
        wb.depth = depth;
        // ⛔ 地形を彫る側の設定は**触らない**(Recarve を呼ばないので効かないが、既定を明示しておく)
        wb.raiseBanks = false; wb.verticalWalls = false; wb.levelFloor = false;

        // 材質 — **この池だけの1枚**を決まったパスで持つ。
        // ⛔⛔ **他の水面から借りない。**2026-09-21 まではここが「場面で最初に見つかった水面の材質を
        //   借りる」作りで、`FindObjectsByType` の並びは**保証されない**ため、当家の池が
        //   **外堀(`Sotobori_00002`)の材質を握った**。⇒ 深さ 1.5m の濠と深さ 1.5m の庭の池が
        //   1枚を共有し、片方の見え方を直すともう片方が動く関係になっていた(EDO-0316)。
        // ⭐ 見え方の3つ(色の深さ・岸なじみ・泡)は `WaterBaker.ApplyLook` が**深さから起こす**。
        //   ⛔ 4.0 / 1.5 / 0.4 の既定を「他所と揃える」名目で持ち込まない。
        // ⚠ パスを固定するのは、Stage を流し直すたびに `… 1.mat` の孤児が溜まらないようにするため
        //   (土井の池が 8 個作った先例。`EdoDoiBuilder.Niwa.cs` の MAT と同じ作法)。
        var mr = wb.GetComponent<MeshRenderer>();
        string matPath = "Assets/Edo/Water/" + nm + ".mat";
        var pondMat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (pondMat == null)
        {
            var sh = Shader.Find("Edo/Water");
            if (sh == null) { wait.Add("シェーダ `Edo/Water` が見つからない(URP の Depth+Opaque Texture が要る)"); return "水面: 材質待ち"; }
            pondMat = new Material(sh);
            AssetDatabase.CreateAsset(pondMat, matPath);
        }
        // ⛔ 色・透け・さざ波は水域の性格なので毎回上書きしてよい(この池は庭の池の明るい水)
        pondMat.SetColor("_DeepColor", new Color(0.13f, 0.32f, 0.40f));
        pondMat.SetColor("_ShallowColor", new Color(0.28f, 0.50f, 0.55f));
        pondMat.SetFloat("_FresnelPower", 3.0f); pondMat.SetFloat("_Alpha", 0.8f);
        WaterBaker.ApplyLook(pondMat, depth);
        EditorUtility.SetDirty(pondMat);
        mr.sharedMaterial = pondMat;
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
        // ⭐ 地盤は**描かれた地表**で引く(EDO-0502 第59巡)。⛔ 設計の graded で引かない ── 地形は 2m 格子で描くので、池の岸・築山の
        //   斜面で設計と描かれた地表が食い違い、飛石・垣が浮くか埋まる(メモリ contact-must-use-drawn-surface)
        var drawn = EdoBuild.Drawn();
        System.Func<Vector2, float> GY = delegate(Vector2 c)
        { float y = drawn.At(c.x, c.y); return float.IsNaN(y) ? EdoBuild.Ground(c.x, c.y) : y; };
        int made = 0;

        // ---- 庭石(景石・岩島)。⭕ 丈 1.0 に正規化・ピボット = 芯・底
        //      露出 h を `buryRatio` 埋める ⇒ **総丈 H = h/(1−bury)**。⭐ 高さは**地面と触れる箇所**で測る(SeatNiwaStone)。
        //      ⭐ 個体は指図の `idx`(岩島は `kataAsset` の「Ishigumi(主)/(肩)」)を読む。無い行だけ名の hash で散らす
        //      ⭐ 岩島の肩石は指図の `shoulder` の点へ。⛔ 点が無ければ据えない(位置を発明しない)
        if (kind == "景石" || kind == "岩島")
        {
            float h = F(Get(g, "h"));
            float bury = Has(g, "buryRatio") ? F(g["buryRatio"]) : 0.333f;
            float sink = Has(g, "sink") ? F(g["sink"]) : 0f;
            int idv = Has(g, "idx") ? (int)F(g["idx"]) : StableHash(nm) % 5, idk = 4;
            {
                var km = System.Text.RegularExpressions.Regex.Matches(S(Get(g, "kataAsset")) ?? "", @"\((\d)\)");
                if (km.Count >= 1 && !Has(g, "idx")) idv = int.Parse(km[0].Groups[1].Value);
                if (km.Count >= 2) idk = int.Parse(km[1].Groups[1].Value);
            }
            if (load(EdoAssets.Own.Ishigumi(idv)) == null) return 0;
            float wy = Has(g, "y") ? F(g["y"]) : float.NaN;
            made += SeatNiwaStone(sub, nm, idv, P2(0), h, bury, sink, wy, StableHash(nm + "y") % 360, drawn, wait);
            if (kind == "岩島" && Has(g, "hShoulder"))
            {
                var sp = A(Get(g, "shoulder"));
                if (sp == null || sp.Count < 2) wait.Add("庭 " + nm + " の肩石: 指図に肩石の点(shoulder)が無い ── 据えない");
                else made += SeatNiwaStone(sub, nm + "_Kata", idk, new Vector2(F(sp[0]), F(sp[1])), F(g["hShoulder"]), bury, sink, wy,
                                           StableHash(nm + "s") % 360, drawn, wait);
            }
            return made;
        }

        // ---- 石橋(切石の一枚物)。⭐ 長手(局所 +X)を**遣水の流れに直交**させ、両の袂の地面と触れる箇所で据える(SeatOnGround)
        //      ⛔ 名の hash で回さない(流れに沿って架かる)
        if (kind == "石橋")
        {
            string pth = AssetByKey(key); if (load(pth) == null) return 0;
            Vector2 c = P2(0); Vector2 dir = Vector2.zero; float bd = float.MaxValue;
            foreach (var o in A(Get(IMPL, "gardens")) ?? new List<object>())
            {
                var y2 = O(o); if ((S(Get(y2, "kind")) ?? "") != "遣水" || S(Get(y2, "zone")) != S(Get(g, "zone"))) continue;
                var wl = A(Get(y2, "world")); if (wl == null) continue;
                for (int i = 1; i < wl.Count; i++)
                {
                    var qa = A(wl[i - 1]); var qb = A(wl[i]); Vector2 a2 = new Vector2(F(qa[0]), F(qa[1])), b2 = new Vector2(F(qb[0]), F(qb[1]));
                    float d = DistSeg(c, a2, b2); if (d < bd) { bd = d; dir = (b2 - a2).normalized; }
                }
            }
            if (dir == Vector2.zero) { wait.Add("庭 " + nm + ": 架ける遣水が算出物に無い ── 据えない"); return 0; }
            Vector2 px = new Vector2(-dir.y, dir.x);                     // 流れに直交
            float yaw = Mathf.Atan2(-px.y, px.x) * Mathf.Rad2Deg;          // 局所 +X → px
            var go = EdoBuild.Place(pth, new Vector3(c.x, GY(c), c.y), yaw, Vector3.one, sub, nm);
            if (go == null) return 0;
            EdoBuild.SeatOnGround(go, 0f);
            if (bd > 0.5f) wait.Add("庭 " + nm + ": 点が遣水の芯から " + bd.ToString("F2") + "m 離れている(据えた・⚠ 架かっているかレンダで見る)");
            return 1;
        }

        // ---- 木の平橋(EdoAssets.Own.HashiIta・EDO-0502 第60巡)。ピボット = 橋面の中心・敷板の天端、局所 +X = 長手。
        //      袂 = 指図の from→to の軸の上で、中ほどから両側へ描かれた地表が水面に届く所(実測)。芯 = 両の袂の中点・長さ = 袂の間を
        //      scale.x で合わせる(±6%【柔】── 外れれば最も近い倍率で ⚠)。高さ = 指図 deckY【柔】。硬い: 桁の端が袂の地表から浮かない
        //      (浮けば浮きの小さい側へ下げる)。挟み石は据えの器が未実装(waitHasami)。当たる先: 木の平橋を架ける庭(岡部 書院の泉水)
        if (kind == "橋" && key == "Hashi")
        {
            string pth = AssetByKey(key); if (load(pth) == null) return 0;
            if (pts == null || pts.Count < 2) { wait.Add("庭 " + nm + ": 橋の軸(from/to)が無い ── 据えない"); return 0; }
            float wy = float.NaN;
            foreach (var o in A(Get(IMPL, "gardens")) ?? new List<object>()) { var y2 = O(o); if ((S(Get(y2, "kind")) ?? "").StartsWith("汀線") && S(Get(y2, "zone")) == S(Get(g, "zone"))) wy = F(y2["y"]); }
            if (float.IsNaN(wy)) { wait.Add("庭 " + nm + ": 汀線の水面が算出物に無い ── 袂を測れず据えない"); return 0; }
            Vector2 pa = P2(0), pb = P2(1), mid = (pa + pb) * 0.5f, ax = (pb - pa).normalized;
            System.Func<float, float> shore = sg => { for (float s = 0f; s <= 8f; s += 0.05f) { var q = mid + ax * sg * s; if (drawn.At(q.x, q.y) >= wy) return s; } return float.NaN; };
            float sA = shore(-1f), sB = shore(1f);
            if (float.IsNaN(sA) || float.IsNaN(sB)) { wait.Add("庭 " + nm + ": 軸の上 8m の内に袂(地表 ≥ 水面 " + wy.ToString("F2") + ")が無い ── 据えない"); return 0; }
            Vector2 tA = mid - ax * sA, tB = mid + ax * sB, c = (tA + tB) * 0.5f; float span = sA + sB;
            const float L0 = 8.0f; float sx = Mathf.Clamp(span / L0, 0.94f, 1.06f);
            float deck = Has(g, "y") ? F(g["y"]) : float.NaN;
            if (float.IsNaN(deck)) { wait.Add("庭 " + nm + ": 指図に橋面の高さ(deckY)が無い ── 据えない"); return 0; }
            float yaw = Mathf.Atan2(-ax.y, ax.x) * Mathf.Rad2Deg;   // 局所 +X → ax
            var go = EdoBuild.Place(pth, new Vector3(c.x, deck, c.y), yaw, new Vector3(sx, 1f, 1f), sub, nm);
            if (go == null) return 0;
            // 桁の端(袂の地表に載る所)の浮き ── 長手の両端 0.6m の、橋面より 0.25 下の頂点の 地表との差の最小(= 当たり)
            System.Func<float> endFloat = () =>
            {
                float worst = float.MinValue;
                for (int e = -1; e <= 1; e += 2)
                {
                    float mn = float.MaxValue;
                    foreach (var v in EdoBuild.Body(go.transform, 6000))
                    {
                        float s = Vector2.Dot(new Vector2(v.x, v.z) - c, ax) * e; if (s < span * 0.5f) continue;   // 袂より陸の側
                        if (v.y > go.transform.position.y - 0.25f) continue;
                        float gy = drawn.At(v.x, v.z); if (float.IsNaN(gy)) continue; mn = Mathf.Min(mn, v.y - gy);
                    }
                    if (mn != float.MaxValue) worst = Mathf.Max(worst, mn);
                }
                return worst == float.MinValue ? float.NaN : worst;
            };
            float f0 = endFloat(), dy = 0f;
            if (!float.IsNaN(f0) && f0 > 0f) { dy = -f0; go.transform.position += new Vector3(0f, dy, 0f); }
            float f1 = endFloat();
            // 橋脚の根入れ(池床の描かれた地表 − 橋脚の底)
            float pier = float.NaN; foreach (var v in EdoBuild.Body(go.transform, 6000)) { float s = Mathf.Abs(Vector2.Dot(new Vector2(v.x, v.z) - c, ax)); if (s > 0.6f) continue; float gy = drawn.At(v.x, v.z); if (float.IsNaN(gy)) continue; pier = float.IsNaN(pier) ? gy - v.y : Mathf.Max(pier, gy - v.y); }
            wait.Add("庭 " + nm + "(据えた): 袂の間 " + span.ToString("F2") + "m ⇒ scale.x " + sx.ToString("F3") + (Mathf.Abs(span / L0 - sx) > 1e-3f ? " ⚠ ±6% の外(最も近い倍率)" : "")
                + "・芯は指図の軸の中点から " + Vector2.Distance(c, mid).ToString("F2") + "m・橋面 " + go.transform.position.y.ToString("F2") + (Mathf.Abs(dy) > 1e-3f ? "(deckY " + deck.ToString("F2") + " から袂に載るまで " + dy.ToString("F2") + " ⚠)" : "(deckY)")
                + "・桁の端の浮き " + (float.IsNaN(f1) ? "測れず ⚠" : f1.ToString("+0.00;-0.00")) + "(硬 ≤ 0)・橋脚の根入れ " + (float.IsNaN(pier) ? "測れず" : pier.ToString("F2")));
            if (Has(g, "waitHasami")) wait.Add("庭 " + nm + " の挟み石: " + S(g["waitHasami"]));
            return 1;
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
            var tyl = A(Get(g, "topY")); float[] topLo = (tyl != null && tyl.Count == 2) ? new[] { F(tyl[0]), F(tyl[1]) } : null;
            int topMiss = 0; float topWorst = 0f, topMin = float.MaxValue, topMax = float.MinValue;
            for (int i = 0; i < n; i++)
            {
                bool isYaku = yaku > 0 && (i % yaku) == 0;
                int idv = isYaku ? 3 : (StableHash(nm + i) % 3);      // 役石は塊石 3
                float w0 = IshigumiW(idv);
                float axis = Mathf.Lerp(lo, hi, (StableHash(nm + "L" + i) % 1000) / 1000f);
                float sc = axis / Mathf.Max(0.05f, w0);
                Vector2 c = PolyAt(pts, n <= 1 ? 0f : i / (float)(n - 1));
                var go = EdoBuild.Place(EdoAssets.Own.Ishigumi(idv), new Vector3(c.x, baseY, c.y),
                                        StableHash(nm + "r" + i) % 360, Vector3.one * sc, sub, nm + "_" + i);
                if (go == null) continue;
                // ⭐ 高さは**地面(汀の法・池床)と触れる箇所**で(EdoBuild.SeatBuried ── 実メッシュの丈の bury を埋める)。⛔ 水面 y から丈×bury を引いて置かない
                //   (第59巡: 汀の法が水面より低い所で 28 個が最大 0.45 浮いた)。jag は下へだけ散らす(浮かせない)
                EdoBuild.SeatBuried(go, bury);
                go.transform.position += new Vector3(0f, -((StableHash(nm + "j" + i) % 1000) / 1000f) * jag, 0f);
                // ⭐ 天端は指図 topY [lo, hi]【柔】へ(EDO-0502 第60巡 ── 汀の法の低い所に据わった石が水に沈み、天端 20.38〜21.61 だった)。
                //   ⛔ 浮かせて上げない ── 倍率を解き直して据え直す(据えは同じ SeatBuried・地面と触れる箇所)。最も近い天端へ寄せ、外れれば ⚠
                if (topLo != null)
                {
                    float tLo = topLo[0], tHi = topLo[1];
                    for (int it = 0; it < 4; it++)
                    {
                        var rb = EdoBuild.RB(go); float top = rb.max.y, gy0 = rb.min.y;
                        float want = Mathf.Clamp(top, tLo, tHi); if (Mathf.Abs(want - top) < 0.02f) break;
                        float k = Mathf.Clamp((want - gy0) / Mathf.Max(0.05f, top - gy0), 0.6f, 1.6f);
                        float sc1 = Mathf.Clamp(go.transform.localScale.x * k, sc * 0.6f, sc * 1.8f);
                        go.transform.localScale = Vector3.one * sc1;
                        EdoBuild.SeatBuried(go, bury);
                    }
                    float t1 = EdoBuild.RB(go).max.y;
                    if (t1 < tLo - 0.02f || t1 > tHi + 0.02f) { topMiss++; topWorst = Mathf.Max(topWorst, Mathf.Max(tLo - t1, t1 - tHi)); }
                    topMin = Mathf.Min(topMin, t1); topMax = Mathf.Max(topMax, t1);
                }
                made++;
            }
            if (topLo != null) wait.Add("庭 " + nm + "(据えた): 天端 " + topMin.ToString("F2") + "〜" + topMax.ToString("F2") + "(狙い " + topLo[0].ToString("F2") + "〜" + topLo[1].ToString("F2") + "【柔】)"
                + (topMiss > 0 ? " ⚠ 外れ " + topMiss + " 個・最大 " + topWorst.ToString("F2") + "m(倍率の幅 0.6〜1.8 で届かない)" : " ⭕"));
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
            // ⭐ 天端の y が指図に無ければ、部材の根(0.15・部材の doc「露出 0.35 + 根 0.15」)だけ地面と触れる箇所から沈める ──
            //   ⛔ 天端を地盤の値に置かない(第59巡: 沓脱石が地表と面一で丸ごと埋まった)
            if (go != null && !Has(g, "y")) EdoBuild.SeatOnGround(go, 0.15f * (L / 1.2f));
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

    /// <summary>庭石を一つ据える(景石・岩島・肩石)。⭐ 高さは**地面と触れる箇所**で決める(EdoBuild.SeatOnGround)── ⛔ ピボットを地盤の値へ置かない。
    /// 陸の石: 総丈 H = h/(1−bury) で置き、当たりから (H−h)+sink 沈める(斜面でも底が浮かない)。
    /// 水の石(<paramref name="waterY"/> が在る): 露出 h は**水面から**測る ── 池床に sink だけ沈めて天端が waterY+h に来る総丈へ倍率を解く
    /// (床が深ければ大きく・浅ければ bury の丈で)。硬い: 底の浮き 0(当たりで据える)。柔らかい: 天端 = waterY+h(±0.03 で ⚠)。</summary>
    static int SeatNiwaStone(Transform sub, string nm, int idv, Vector2 c, float h, float bury, float sink, float waterY,
                             float yaw, EdoBuild.DrawnGround drawn, List<string> wait)
    {
        string pth = EdoAssets.Own.Ishigumi(idv);
        float H = h / Mathf.Max(0.05f, 1f - bury);
        var go = EdoBuild.Place(pth, new Vector3(c.x, drawn.At(c.x, c.y), c.y), yaw, Vector3.one * H, sub, nm);
        if (go == null) return 0;
        if (float.IsNaN(waterY)) { EdoBuild.SeatOnGround(go, (H - h) + sink); return 1; }
        // 水の石: 当たりで池床へ据え(sink 沈め)、天端を測って倍率を解き直す(2 回)
        float top = 0f;
        for (int it = 0; it < 3; it++)
        {
            EdoBuild.SeatOnGround(go, sink);
            var b = EdoBuild.RB(go); top = b.max.y; float want = waterY + h;
            if (Mathf.Abs(top - want) <= 0.03f || it == 2) break;
            float span = top - (b.min.y);                                   // 今の丈
            float need = want - b.min.y; if (span < 1e-3f || need <= 0.05f) break;
            float k = Mathf.Max(need / span, (h / Mathf.Max(0.05f, 1f - bury)) / H);   // bury の丈より小さくしない
            H *= k; go.transform.localScale = Vector3.one * H;
        }
        if (Mathf.Abs(top - (waterY + h)) > 0.03f)
            wait.Add("庭 " + nm + ": ⚠ 狙い 天端 " + (waterY + h).ToString("F2") + " に対し " + top.ToString("F2") + "(池床で据えた)");
        return 1;
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
        "ObiNagaya — 崖下の平屋長屋 N1/N2(7.5×2.5間・桟瓦・下見板腰・水側は盲面)",
        "ObiMonooki — 物置 M1(3×1.5間)",
        "ObiKawaya — かわや K_Obi(1×1間)",
        "MarutaTesuri — 丸太の手すり(横木1段・丸太径 0.12)",
        "Kui — 汀の杭(松の丸太・径 0.12〜0.18)",
    };

    /// <summary>植栽の部材のキーを解く。**キーは指図(算出物)が持ち、ここは辞書を引くだけ。**
    /// 書式は `族.名.寸法.個体`(例 `JG.Pine.Big.2` / `Own.Jouryoku.Mid.1`)。
    /// ⛔ **どの在庫の木がどの樹種を代表するかは在庫方の判断**で、ここで決めない
    ///   — 部材の doc も「指図の parts で個体を混ぜること」と求めている。</summary>
    static string PlantByKey(string key) { return PlantByKey(key, key); }
    /// ⭐ 中身は共通の一本 <see cref="EdoBuild.PlantPathByKey"/>(EDO-0533 で移した・土井 Stage8 と共有)。
    static string PlantByKey(string key, string seedName) { return EdoBuild.PlantPathByKey(key, seedName); }

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
    static float TrunkDiameter(GameObject host, float y0, float y1) { return EdoBuild.PlantTrunkDiameter(host, y0, y1); }

    /// <summary>名前から決まる安定した非負の整数。⛔ 乱数ではない — 何度流しても同じ物が出る。
    /// (`string.GetHashCode` は .NET の版で変わるので使わない)</summary>
    static int StableHash(string s2) { return EdoBuild.PlantHash(s2); }

    /// <summary>部材の**素の丈**[m]。⭐ 中身は共通の一本 <see cref="EdoBuild.PlantNaturalHeight"/>(EDO-0533 で移した)。</summary>
    static float NaturalHeight(string path, Transform parent) { return EdoBuild.PlantNaturalHeight(path, parent); }

    [MenuItem("Edo/岡部筑前守上屋敷/5 西の斜面(林・松・帯・汀)")]
    public static void Stage5Menu() { Debug.Log("[Okabe] " + Stage5_Nishi()); }

    public static string Stage5_Nishi()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder();
        var wait = new List<string>();
        // 案1(EDO-0502): 植栽は林方の設計 `planting` から焼いた算出物(bake_planting)で建つ。丸太の手すり・杭列(kui/rails)は
        //   焼き手が無く前の指図のまま ── 欄ごとに分けて、焼けている欄だけ据える(⛔ 一つが古いからと全部を止めない)
        if (Stale("planting"))
            return "西の斜面: ⛔ 算出物 planting が前の指図のまま ── 据えない" + RetireStaleGroup("Nishi", "planting");
        // 前の巡で群ごと退けた「Nishi」を起こす(⛔ 退けたままだと植えた木が非活性で測れない ── SeatPlant が NaN)。
        //   古い欄の子(丸太の手すり)は子の群だけ退ける
        Group("Nishi").gameObject.SetActive(true);
        bool staleRails = Stale("kui") || Stale("rails") || Get(D, "nishi") == null;
        if (staleRails) { sb.Append(RetireStaleGroup("Nishi/Tesuri", "rails")); sb.Append(RetireStaleGroup("Nishi/Kui", "kui")); }
        sb.AppendLine(PlantFromImpl(wait));
        if (staleRails)
            sb.AppendLine("丸太の手すり・汀の杭列: ⛔ 算出物 kui/rails が前の指図のまま・指図に nishi の欄が無い(案1)── 据えない");
        else
        {
            sb.AppendLine(PlaceTesuri(wait));
            sb.AppendLine(PlaceKuiretsu(wait));
            sb.AppendLine(ReportNishiRest(wait));
        }
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
                   + "(planting は ⛔ main に焼き手が無い欄 — EDO-0386)。⛔ 実装側で撒き直すと、"
                   + "指図の検査(窓の樹高の上限・対岸の二層・坂と木戸の離れ)が見た配置と別物になる");
            return "植栽: 算出物待ち";
        }
        var grp = Group("Nishi/Planting"); Clear(grp);
        var f = Grid;
        // ⭐ 据えは描かれた地表(縁の皮を含む)で ── 皮は Stage3b が起こした後。⛔ 格子で据えると皮の上で浮く・埋まる(第6巡 266 本)
        var drawnG = EdoBuild.Drawn();
        int made = 0, noPart = 0, noAsset = 0, seatBad = 0; var seatBadLog = new List<string>();
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
            // ⛔ 部材が無いときに例外で Stage 全体を止めない — 記録して次へ
            if (path == null || AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            { missing.Add(key + (path == null ? "" : " → " + path)); noPart++; continue; }
            Vector2 c = f.W(F(q["u"]), F(q["v"]));
            // ⭕ 置き方は EdoBuild.PlantAtPoint(仮置き → 丈を指図の値へ → 傾け → 幹の足を点へ寄せ足の当たりで描かれた地表へ据える)
            //   ⛔ 部材の素の丈で置かない・外接の底で据えない(EDO-0533 で岡部の邸ビルダーから移した ── 姿は同じ)
            float tilt = F(Get(q, "tilt"));
            Vector2 w2 = Vector2.up;
            if (Mathf.Abs(tilt) > 0.01f)
            {
                var d2 = A(Get(q, "tiltDir"));
                Vector2 dir = (d2 != null && d2.Count == 2) ? new Vector2(F(d2[0]), F(d2[1])) : Vector2.up;
                w2 = (f.W(dir.x, dir.y) - f.W(0f, 0f)).normalized;
            }
            string lay = S(Get(q, "layer")) ?? "";
            bool seated, refused; float bu, fl;
            string goName = Has(q, "name") ? S(q["name"]) : (S(q["zone"]) + "_" + made);
            var go = EdoBuild.PlantAtPoint(path, c, F(Get(q, "h")), tilt, w2, lay, grp, goName, drawnG,
                                           out seated, out bu, out fl, out refused, 1.0f, 0.7f);
            if (refused)
            { seatBad++; if (seatBadLog.Count < 8) seatBadLog.Add(goName + " 埋没 " + bu.ToString("F2") + " 浮き " + fl.ToString("F2") + "(建てない)"); continue; }
            if (go == null) { missing.Add(key + " → " + path); noPart++; continue; }
            if (Has(q, "name")) placed[S(q["name"])] = go;
            made++;
            string z = S(Get(q, "zone")) ?? "?";
            byZone[z] = (byZone.ContainsKey(z) ? byZone[z] : 0) + 1;
        }
        // ---- 二巡目: つる(高木の幹に絡む)-------------------------------
        int vine = 0, vineSkip = 0; var vineLog = new List<string>();
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
            vineLog.Add(S(q["name"]) + " on " + hostName + " 幹径 " + dia.ToString("F3"));
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
        if (vineLog.Count > 0) sb.Append("\n  つるの幹径(実測): " + string.Join(" / ", vineLog.ToArray()));
        sb.Append(" ｜ 据え(幹の足の当たり): 埋没 ≤1.0・浮き ≤0.7 を外れて建てなかった " + seatBad + " 本(硬い ── 許容0 を破る点には建てない)"
                + (seatBadLog.Count > 0 ? "\n  ⚠ " + string.Join(" / ", seatBadLog.ToArray()) : ""));
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
            // ⭕ **焼き上がりの径へ丸める**(算出物は 0.12〜0.18 の連続値、部材は3種)。
            //   ⛔ 丸めないと合わない径が全部落ちる(2026-09-04: 242 本中 85 本しか据わらなかった)
            float dia = F(Get(k, "dia"));
            var kd = new float[] { 0.12f, 0.15f, 0.18f };
            float pick = kd[0];
            foreach (var dd in kd) if (Mathf.Abs(dd - dia) < Mathf.Abs(pick - dia)) pick = dd;
            string path = EdoAssets.Own.Kui(pick);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { missing.Add(pick.ToString("0.00")); continue; }
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
        // ⛔ 算出物の汀線が区画の外なら**建てない**(硬い・区域侵犯 許容0・EDO-0502)── 杭と貫を実メッシュで測って退ける
        int outK = EdoBuild.RetireOutsidePoly(grp, Poly, wait, "汀の杭列(算出物 kui)");
        return "汀の杭列: " + (made + nuki - outK) + " 個(杭 " + made + "・貫 " + nuki + " を据え、区画の外の " + outK + " 個を退けた)";
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
        // ⭕ **実際に引けるかで判定する**(⛔ 固定の文言を並べない — 焼けた後も「待ち」と嘘をつく)
        foreach (var s2 in NishiPartsPending)
        {
            int c2 = s2.IndexOf(' ');
            string k2 = c2 > 0 ? s2.Substring(0, c2) : s2;
            // ⚠ 径や長さが要る部材は、代表の寸法で引いて実在を見る(⛔ 引数 0 で null を貰って
            //   「待ち」と嘘をつかない — 2026-09-04 に `Kui` がそれで残った)
            string pth = k2 == "Kui" ? EdoAssets.Own.Kui(0.15f)
                       : k2 == "ObiNagaya" ? EdoAssets.Own.ObiNagaya(7.5f, 2.5f)
                       : AssetByKey(k2, 7.5f, 2.5f);
            if (pth == null || AssetDatabase.LoadAssetAtPath<GameObject>(pth) == null)
                wait.Add("部材待ち: " + s2);
        }
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

    /// <summary>run が開口の**門長屋**か(案1・EDO-0502)。指図の `gate.host` / `komon[].host` が
    /// その run を名指しし、口がその run の区間の内にあるとき true。⛔ 名指しの無い run は門長屋と見なさない。</summary>
    static bool HostsOpening(string run, int edge, float a, float b)
    {
        var g = O(Get(D, "gate"));
        if (g != null && S(Get(g, "host")) == run && (int)F(g["edge"]) == edge) return true;
        foreach (var o in A(Get(D, "komon")) ?? new List<object>())
        { var k = O(o); if (k != null && S(Get(k, "host")) == run && (int)F(k["edge"]) == edge) return true; }
        return false;
    }

    /// <summary>門長屋の口(辺 e の走り s・幅 w)。run を名指しする `gate` / `komon[]` を引く。無ければ false。</summary>
    static bool HostedGate(string run, out float s, out float w, out string label)
    {
        s = 0f; w = 0f; label = null;
        var g = O(Get(D, "gate"));
        if (g != null && S(Get(g, "host")) == run)
        {
            var gpl = O(Get(g, "plan"));
            s = F(g["s"]); w = Has(gpl, "monkuchi") ? F(gpl["monkuchi"]) : 0f; label = S(Get(g, "name")) ?? "表門";
            return true;
        }
        foreach (var o in A(Get(D, "komon")) ?? new List<object>())
        {
            var k = O(o); if (k == null || S(Get(k, "host")) != run) continue;
            s = F(k["s"]); w = F(k["w"]); label = S(Get(k, "label")) ?? S(k["name"]);
            return true;
        }
        return false;
    }

    /// <summary>指図の開口(表門・通用口)。**辺と s の区間**で返す。</summary>
    static List<float[]> Openings()
    {
        var outp = new List<float[]>();
        var g = O(Get(D, "gate"));
        if (g != null)
        {
            // 案1(EDO-0502): 門口の幅は `plan.monkuchi`(門長屋の駒の中の口)。無い旧い指図だけ monW
            var gpl = O(Get(g, "plan"));
            float w = Has(gpl, "monkuchi") ? F(gpl["monkuchi"]) : F(Get(gpl, "monW")), s = F(g["s"]);
            outp.Add(new float[] { F(g["edge"]), s - w / 2f, s + w / 2f, 0f });   // 0 = 表門
        }
        foreach (var o in A(Get(D, "komon")) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue;
            float s = F(k["s"]), w = F(k["w"]);   // ⚠ w が null(型未決)の門は幅 0 の口として数える
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
    ///   ②の「建っている物」= Kakoi・Mon・Fences・Ishigaki(基壇の石垣)の活きている駒。
    ///   ⛔ だからといって数字を出さないと「据えたつもり」が見えなくなる。</summary>
    public static string ClosureQA()
    {
        var P = Poly; int n = P.Length;
        var ops = Openings();
        var sb = new System.Text.StringBuilder("外周の閉じ\n");
        float sumDoc = 0f, sumImpl = 0f;
        // ⭐ 実装の被覆は建っている駒の実メッシュで測る(EdoBuild.CoverAlongEdge・目の高さの帯 0.3〜2.0m・辺から 1.5m 以内)
        //   (2026-10-06 EDO-0502 第29巡)── 指図の s で数えると、辺41 の通用門の柱と袖の練塀が 0.7m 重なっているのに 0.27 の切れ目と数えた
        var built = new List<GameObject>();
        {
            var rt = GameObject.Find(GN);
            if (rt != null)
                // ⭐ 基壇の石垣(Ishigaki の群)も塞ぐ物に数える(2026-10-07 EDO-0502 第47巡)── 数えないと辺23/24/41 の
                //   石垣だけで閉じている所を 0.12/0.11/0.30 の素通しと出した(検査の文言「建っている物」と集合をそろえる)
                foreach (var gn in new[] { "Kakoi", "Mon", "Fences", "Ishigaki" })
                { var g = rt.transform.Find(gn); if (g != null) foreach (Transform c in g) if (c.gameObject.activeInHierarchy) built.Add(c.gameObject); }
        }
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
                }
            if (ours)
                foreach (var cv in EdoBuild.CoverAlongEdge(P[e], P[(e + 1) % n], built, 1.5f, 0.3f, 2.0f))
                    impl.Add(new Iv { a = cv.x, b = cv.y });
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
                if (HostsOpening(r.name, e, op[1], op[2])) continue;   // 門長屋は口を自分の駒の中に抜く(案1)
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
                    // ⭐ 案1: 指図の run が s を持たない(sFrom だけ)なら s は焼き手が出す(impl_okabe.bake_base)── 算出物の s が正で、比べる相手が無い(r.s = 0)
                    if (Has(b, "s") && r.s > 0f && Mathf.Abs(F(b["s"]) - r.s) > 1e-4f)
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
        // ⭐ 据え置きの欄(前の指図のまま・Stale)は建てない ── 検めず ℹ で名指す(未検査であって合格ではない・規則19)
        if (Stale("rails")) sb.Append("  ℹ rails は据え置きの欄(前の指図のまま)── 建てないので検めない\n");
        else
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
        if (Stale("kui")) sb.Append("  ℹ kui は据え置きの欄(前の指図のまま)── 建てないので検めない\n");
        else
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
        sb.AppendLine(Stage2b_Dan());
        sb.AppendLine(Stage3_Shukaku());
        sb.AppendLine(Stage3b_Hifu());      // 皮は駒と造成が決まった後(1 が冒頭で外す)
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
        // ⭐ 芯は EdoRemapMat.Run(全邸で1本・EDO-0318)。ここに書くのは並びだけ。
        return EdoRemapMat.Run(donorDirs, modelDirs, "岡部の新造部材");
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
