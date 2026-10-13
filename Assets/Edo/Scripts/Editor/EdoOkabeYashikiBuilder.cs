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
    public static void Reload() { _topLanding.Clear(); _d = null; _impl = null; _runs = null; _frame = null; _graded = null; _michi = null; _michiRead = false; _flat = null; _rampProf = null; }

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
    /// <summary>Stage の間だけ地形を岡部の芯の地形(北の3邸の細かい地形・2026-10-11)へ名指す(EdoBuild.TerrainFocus)。</summary>
    static IDisposable OnKita()
    {
        var P = Poly; Vector2 c = Vector2.zero; foreach (var q in P) c += q; c /= Mathf.Max(1, P.Length);
        return EdoBuild.TerrainFocus(c);
    }

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
        /// <summary>天端の切れ目(指図 runs[].seatRule・<see cref="SolveSeatRules"/> が実地形で解く)── hasStep なら s &lt; stepS は stepLo の一直線、
        /// s ≥ stepS は max(stepHi, seat0 → seat1 の一直線)。</summary>
        public bool hasStep; public float stepS, stepLo, stepHi;
        /// <summary>段の座(指図 runs[].seatBreakS【硬】・2026-10-12 第114巡)── s &lt; stepS は seat0・s ≥ stepS は seat1 の平ら(⛔ seat0→seat1 の一直線の勾配にしない)。
        /// bake_impl.rseat・sashizu_lib._tw_seat_at と同じ読み(内の帯も段どおり)。</summary>
        public bool flatStep;
        /// <summary>**天端の線**(const.heiLine・施主裁定 2026-10-12 案A・第120巡 ── <see cref="HeiLineTenba"/> が一続きの範囲で解く)── 走り lineS[k]〜lineS[k+1] は座 lineSeat[k] の平ら・
        /// その区間の線の上の通し番号 lineSec[k](頂点を跨ぐ区間は隣の run と同じ番号 ⇒ 床へ組ごと据える)。null なら従来の seat0 → seat1。</summary>
        public float[] lineS, lineSeat; public int[] lineSec;
        /// <summary>天端の線の区間の勾配(走り 1m あたり・const.heiLine.tenba 案1 の坂なり ── 座は lineS[k] の値)と、lineS[k] が段の面か(<see cref="HeiLineTenba"/>)。null = 平ら。</summary>
        public float[] lineGrade; public bool[] lineStep;
        /// <summary>天端の線の区間 k の走り s の座(勾配つき)。</summary>
        public float SeatOnRow(int k, float sv) { return lineSeat[k] + (lineGrade == null ? 0f : lineGrade[k] * (sv - lineS[k])); }
        /// <summary>走り s が天端の線の段の面か(lineS の切れ目のうち段の物 ── 0.01 以内)。</summary>
        public bool StepAtS(float sv) { if (lineS == null || lineStep == null) return false; for (int k = 0; k < lineS.Length; k++) if (lineStep[k] && Mathf.Abs(lineS[k] - sv) < 0.01f) return true; return false; }
        /// <summary>走り s の天端の線の区間の番号(<see cref="lineS"/> が無ければ −1)。</summary>
        public int LineIndexAt(float sv)
        {
            if (lineS == null) return -1;
            for (int k = 0; k + 1 < lineS.Length; k++) if (sv < lineS[k + 1] || k + 2 == lineS.Length) return k;
            return lineSeat.Length - 1;
        }
        /// <summary>走り s における天端。seat0 → seat1 の一直線(切れ目があれば上の規則・天端の線があればその区間の座)。</summary>
        public float SeatAt(float sv)
        {
            if (lineS != null) return SeatOnRow(LineIndexAt(sv), sv);
            if (hasStep && flatStep) return sv < stepS ? stepLo : stepHi;
            if (hasStep) { if (sv < stepS) return stepLo; float tt = s1 <= s0 ? 0f : Mathf.Clamp01((sv - s0) / (s1 - s0)); return Mathf.Max(stepHi, Mathf.Lerp(seat0, seat1, tt)); }
            if (s1 <= s0) return seat0;
            float t = Mathf.Clamp01((sv - s0) / (s1 - s0));
            return Mathf.Lerp(seat0, seat1, t);
        }
    }
    /// <summary>**天端の切れ目を実地形で解く**(指図 runs[].seatRule「天端 a の一直線を…通し、内の地盤が天端 +d を超える所…の run の切れ目で b へ上げる。
    /// 切れ目の位置は棟梁が実地形で決める【柔】。その西は今の…段の作法【柔】」・施主裁定 2026-10-12 案A・EDO-0502 第113巡)。
    /// 内の地盤 = 区画の線から内へ <paramref name="inOff"/> の今の地形(造成の後)。切れ目 = 走りの始めから 0.25 ごとに見て、内の地盤が a + d を最初に超える s。
    /// 切れ目から先は max(b, 欄の seat0 → seat1)(「今の段の作法」)。⟶ 報告の行(解けなければ ★)。当たる先: seatRule を持つ run(いまは岡部 S_Hei_02)。</summary>
    static string SolveSeatRules(float inOff)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var sb = new System.Text.StringBuilder(); var rs = Runs;
        for (int k = 0; k < rs.Length; k++)
        {
            // ⭐ 段の座(runs[].seatBreakS【硬】・第114巡)── 位置は指図が持つ(base_dem で解いた値)。⛔ Unity の今の地形で切れ目を解き直さない(規則13)
            if (rs[k].flatStep)
            {
                rs[k].hasStep = true; rs[k].stepLo = rs[k].seat0; rs[k].stepHi = rs[k].seat1;
                Vector2 cw0 = EdgePt(rs[k].edge, Mathf.Min(rs[k].stepS, rs[k].s1));
                sb.AppendLine("  " + rs[k].name + ".seatBreakS【硬】: 座は段 ── s " + rs[k].s0.ToString("F2", inv) + "〜" + rs[k].stepS.ToString("F2", inv) + "(x " + cw0.x.ToString("F1", inv) + ")は "
                              + rs[k].seat0.ToString("F2", inv) + " 平ら・その先 " + rs[k].s1.ToString("F2", inv) + " まで " + rs[k].seat1.ToString("F2", inv) + " 平ら(一直線の勾配にしない)");
                continue;
            }
            rs[k].hasStep = false;
            string sr = RunText(rs[k].name, "seatRule"); if (sr == null) continue;
            var m = System.Text.RegularExpressions.Regex.Match(sr, @"天端\s*([0-9.]+)\s*の一直線.*?内の地盤が天端\s*\+\s*([0-9.]+)\s*を超える所.*?で\s*([0-9.]+)\s*へ上げる");
            if (!m.Success) { sb.AppendLine("  ★ " + rs[k].name + ".seatRule が読めない ── 欄の seat0→seat1 のまま"); continue; }
            float lo = float.Parse(m.Groups[1].Value, inv), d = float.Parse(m.Groups[2].Value, inv), hi = float.Parse(m.Groups[3].Value, inv);
            Vector2 inw = -OutNormal(rs[k].edge); float cut = float.NaN, gAt = float.NaN;
            for (float s = rs[k].s0; s <= rs[k].s1 + 1e-3f; s += 0.25f)
            { var q = EdgePt(rs[k].edge, s) + inw * inOff; float g = EdoBuild.Ground(q.x, q.y); if (g > lo + d) { cut = s; gAt = g; break; } }
            if (float.IsNaN(cut)) { sb.AppendLine("  ⚠ " + rs[k].name + ".seatRule: 内の地盤(線から " + inOff.ToString("F2", inv) + " 内)が全長で天端 " + lo.ToString("F2", inv) + " + " + d.ToString("F2", inv) + " を超えない ── 全長 " + lo.ToString("F2", inv) + " の一直線"); cut = rs[k].s1 + 1f; }
            rs[k].hasStep = true; rs[k].stepS = Mathf.Round(cut * 100f) / 100f; rs[k].stepLo = lo; rs[k].stepHi = hi;
            Vector2 cw = EdgePt(rs[k].edge, Mathf.Min(cut, rs[k].s1));
            sb.AppendLine("  " + rs[k].name + ".seatRule【柔】: 天端 " + lo.ToString("F2", inv) + " の一直線を s " + rs[k].s0.ToString("F2", inv) + "〜" + rs[k].stepS.ToString("F2", inv)
                          + "(x " + cw.x.ToString("F1", inv) + ")・切れ目で " + hi.ToString("F2", inv) + " へ(内の地盤 線から " + inOff.ToString("F2", inv) + " 内 = " + (float.IsNaN(gAt) ? "-" : gAt.ToString("F2", inv)) + " > " + (lo + d).ToString("F2", inv)
                          + ")・その先は max(" + hi.ToString("F2", inv) + ", 欄の " + rs[k].seat0.ToString("F2", inv) + "→" + rs[k].seat1.ToString("F2", inv) + ")");
        }
        return sb.ToString();
    }
    /// <summary>run の区間 [a, b] を天端の段ごとに割る点(両端を含む)── 切れ目(hasStep)の前の一直線は一つ・それ以外の傾いた所は約 2m ごと。</summary>
    static List<float> SeatBreaks(Run r, float a, float b)
    {
        var l = new List<float> { a };
        if (r.lineS != null)
        {   // ⭐ 天端の線(const.heiLine)── 段は線が選んだ点だけ(⛔ 2m ごとに割らない)
            for (int k = 1; k + 1 < r.lineS.Length; k++) if (r.lineS[k] > a + 0.05f && r.lineS[k] < b - 0.05f) l.Add(r.lineS[k]);
            l.Add(b); return l;
        }
        System.Action<float, float> split = (u, v) => { int n = Mathf.Max(1, Mathf.RoundToInt((v - u) / 2.0f)); for (int q = 1; q <= n; q++) l.Add(Mathf.Lerp(u, v, q / (float)n)); };
        if (r.hasStep && r.flatStep && r.stepS > a + 0.05f && r.stepS < b - 0.05f) { l.Add(r.stepS); l.Add(b); }   // 段の座(seatBreakS)── 両側とも平ら
        else if (r.hasStep && r.flatStep) l.Add(b);
        else if (r.hasStep && r.stepS > a + 0.05f && r.stepS < b - 0.05f) { l.Add(r.stepS); split(r.stepS, b); }
        else if (r.hasStep && r.stepS >= b - 0.05f) l.Add(b);
        else if (!r.hasStep && Mathf.Abs(r.seat1 - r.seat0) < 0.01f) l.Add(b);
        else split(a, b);
        return l;
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
                        seat0 = sa, seat1 = sb, s = Has(r, "s") ? F(r["s"]) : 0f,
                        hasStep = Has(r, "seatBreakS"), flatStep = Has(r, "seatBreakS"), stepS = Has(r, "seatBreakS") ? F(r["seatBreakS"]) : 0f, stepLo = sa, stepHi = sb
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
    /// <summary>区画線の外の道の線際の帯の均した面(算出物 michiNarashi ← 指図 grading.michiNarashi・EDO-0502 施主 2026-10-11『均す』)。
    /// 帯の外は NaN。欄が無ければ null。Stage1 が区画の外のこの帯だけ min(今の地形, 面) で下げる(⛔ 盛らない【硬】)。</summary>
    static WGrid _michi; static bool _michiRead;
    static WGrid MichiNarashi
    {
        get
        {
            if (_michiRead) return _michi;
            _michiRead = true;
            var g = IMPL.ContainsKey("michiNarashi") ? O(IMPL["michiNarashi"]) : null;
            if (g == null) return null;
            var w = new WGrid { x0 = F(g["x0"]), z0 = F(g["z0"]), step = F(g["step"]), nx = (int)F(g["nx"]), nz = (int)F(g["nz"]) };
            w.h = new float[w.nx * w.nz];
            var rows = A(g["h"]);
            if (rows == null || rows.Count != w.nz) throw new Exception("算出物 michiNarashi.h の行数が nz と合わない");
            for (int j = 0; j < w.nz; j++)
            {
                var row = A(rows[j]);
                if (row == null || row.Count != w.nx) throw new Exception("算出物 michiNarashi.h[" + j + "] の列数が nx と合わない");
                for (int i = 0; i < w.nx; i++) w.h[j * w.nx + i] = row[i] == null ? float.NaN : Convert.ToSingle(row[i]);
            }
            _michi = w; return _michi;
        }
    }
    /// <summary>帯の均した面の高さ。最も近い格子点が帯の外なら NaN(帯の縁で外へにじませない ── 帯の外の道は触らない【硬】)。</summary>
    static float MichiNarashiAt(WGrid m, float x, float z)
    {
        int i = Mathf.RoundToInt((x - m.x0) / m.step), j = Mathf.RoundToInt((z - m.z0) / m.step);
        if (i < 0 || i >= m.nx || j < 0 || j >= m.nz) return float.NaN;
        if (float.IsNaN(m.h[j * m.nx + i]))
        {   // ⭐ 区画線の際(線の外 1 升以内)は、最も近い格子点が線の内(帯の外)に落ちても帯の面で取る(第105巡【硬: 盛らない】)──
            //   線の 0.08 外の地形の節点(-379.9, 1010.1)= 12.87 が帯の値を持たず残り、三べ坂の石垣の足元に +1.89 の土の歯を立てた。
            //   帯の道側の縁(4m 外)は従前どおり最も近い格子点で切る(縁の外へにじませない)。
            var q = new Vector2(x, z); if (EdoGeom.PIP(Poly, q) || EdoGeom.DistToPolyEdge(Poly, q) > m.step) return float.NaN;
        }
        return m.At(x, z);
    }
    /// <summary>**区画の外の足元を描く「造成前の地盤」**(皮・外周の石垣の足元の検め用)── base_dem に、区画の内で線から
    /// <see cref="MICHI_UNDER"/> 以内の点は、最も近い線の点の 0.3m 外の道の線際の帯の均した面(michiNarashi)との min を採る【硬: 盛らない】。
    /// ⭐ 第105巡: 三べ坂(辺41)の外周の石垣は線の内の節点(造成前の地盤 12.46〜12.70)を下に持ち、線の外の均した道(10.4)へ 2m 格子で
    /// 一次に描かれて、足から 0.3m 前の地面が道より最大 +1.89 高かった。OutsideFootExcess は線の内の節点を base_dem に置き換えて
    /// 測っていたので上がりを 0 と読み、皮に渡さなかった。帯の無い辺は base_dem のまま(従前どおり)。当たる先: 道の線際を均す邸の外周の石垣(いまは岡部 辺41)。</summary>
    const float MICHI_UNDER = 2.5f;
    static Func<float, float, float> OutsideBase()
    {
        var bd = EdoBuild.BaseDem(); var mn = MichiNarashi;
        var P = Poly;
        return (x, z) =>
        {
            float b = bd(x, z); var p = new Vector2(x, z);
            //   ⭐ 区画の外の点も道の線際の帯の均した面(michiNarashi)との min【硬: 盛らない】(第109巡)── base_dem のままだと、台の前の溝の駒
            //   (皮の部材)の周りに開けた穴を皮が造成前の三べ坂の高まり(12.2〜12.5)で描き、均した道(10.5)から縁石の作りの外の壁の上へ
            //   最大 +1.56 の土の坂を立てた(辺41 s44〜56)。帯の無い所は base_dem のまま。当たる先: 道の線際を均す邸の区画の外の皮(岡部 辺41)。
            //   帯の外で均した道(三べ坂の均し grading.michiNarashi.lineProfile ── Stage1 が地形へ写した)は今の地形が持つ ⇒ 今の地形とも min(区画の外だけ・盛らない)。
            if (!EdoGeom.PIP(P, p))
            {
                float mo = mn == null ? float.NaN : MichiNarashiAt(mn, x, z), gt = EdoBuild.Ground(x, z), r = b;
                if (!float.IsNaN(mo)) r = float.IsNaN(r) ? mo : Mathf.Min(r, mo);
                if (!float.IsNaN(gt)) r = float.IsNaN(r) ? gt : Mathf.Min(r, gt);
                return r;
            }
            if (mn == null) return b;
            float best = float.MaxValue; Vector2 c = p;
            for (int i = 0; i < P.Length; i++)
            {
                Vector2 A = P[i], B = P[(i + 1) % P.Length], ab = B - A; float L2 = ab.sqrMagnitude; if (L2 < 1e-8f) continue;
                float t = Mathf.Clamp01(Vector2.Dot(p - A, ab) / L2); var cc = A + ab * t; float d = (p - cc).sqrMagnitude;
                if (d < best) { best = d; c = cc; }
            }
            if (best > MICHI_UNDER * MICHI_UNDER || best < 1e-8f) return b;
            var o = c + (c - p).normalized * 0.3f; float m = MichiNarashiAt(mn, o.x, o.y);
            return float.IsNaN(m) ? b : (float.IsNaN(b) ? m : Mathf.Min(b, m));
        };
    }
    static WGrid Graded
    {
        get
        {
            if (_graded == null && (_graded = GradedBin()) != null) return _graded;
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

    /// <summary>何から造成の面を読んだか(報告に出す)。</summary>
    static string _gradedFrom = "";
    /// <summary>**0.25m の造成の面**(施主裁定 2026-10-11・EDO-0502)── `python3 Tools/Sashizu/impl_okabe.py --graded-bin` が焼く 2 進
    /// (<see cref="EdoAssets.Chikei.OkabeGradedBin"/>)。指図の sha256 が算出物の src と食い違えば ⚠ を出して読まない(算出物の 1m へ戻る)。</summary>
    static WGrid GradedBin()
    {
        string p = Path.Combine(ProjRoot, EdoAssets.Chikei.OkabeGradedBin);
        if (!File.Exists(p)) { _gradedFrom = "⚠ 0.25m の造成の面が無い ── 算出物の 1m で造成(`python3 Tools/Sashizu/impl_okabe.py --graded-bin`)"; return null; }
        using (var br = new BinaryReader(File.OpenRead(p)))
        {
            var mg = new string(br.ReadChars(4)); int ver = br.ReadInt32(); string sha = new string(br.ReadChars(64));
            if (mg != "EDOG" || ver != 1) { _gradedFrom = "⚠ 0.25m の造成の面の書式が違う ── 読まない"; return null; }
            string want = EdoQaVerdict.Sha256Hex(Path.Combine(ProjRoot, SashizuRel));
            if (!string.Equals(sha, want, StringComparison.OrdinalIgnoreCase)) { _gradedFrom = "⚠ 0.25m の造成の面が古い指図から焼かれている(" + sha.Substring(0, 12) + " / 今 " + want.Substring(0, 12) + ")── 算出物の 1m で造成。焼き直すこと"; return null; }
            var w = new WGrid { x0 = br.ReadSingle(), z0 = br.ReadSingle(), step = br.ReadSingle() };
            float yb = br.ReadSingle(); w.nx = br.ReadInt32(); w.nz = br.ReadInt32();
            w.h = new float[w.nx * w.nz];
            for (int k = 0; k < w.h.Length; k++) { short v = br.ReadInt16(); w.h[k] = v == short.MinValue ? float.NaN : yb + v * 0.001f; }
            _gradedFrom = "造成の面 " + EdoAssets.Chikei.OkabeGradedBin + "(" + w.nx + "×" + w.nz + "・" + w.step + "m)";
            return w;
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
    /// <summary>Stage3d が溝の下で下げた地形の節点の控え(据え直しの前に戻す)。</summary>
    static string SinkUndoPath { get { return Path.Combine(ProjRoot, BakDir + "/mizo_sink.bin"); } }
    /// <summary>Stage3d が桝の口に開けた穴の控え(据え直しの前に塞ぐ)。</summary>
    static string HoleUndoPath { get { return Path.Combine(ProjRoot, BakDir + "/masu_holes.bin"); } }
    /// <summary>Stage3d が溝の両脇の帯の地面を天端へ合わせた節点の控え(据え直しの前に戻す)。</summary>
    static string BandUndoPath { get { return Path.Combine(ProjRoot, BakDir + "/mizo_band.bin"); } }
    /// <summary>Stage3d の練塀の足の下の上げ(EdoBuild.FillUnderFoot)の控え ── 次の 3d の頭で戻す(第119巡)。</summary>
    static string FootUndoPath { get { return Path.Combine(ProjRoot, BakDir + "/hei_foot_fill.bin"); } }

    // =====================================================================
    // Stage0 — ハイトマップの退避(地形の編集は Undo の外)
    // =====================================================================
    [MenuItem("Edo/岡部筑前守上屋敷/0 ハイトマップを退避")]
    public static void Stage0Menu() { Debug.Log("[Okabe] " + Stage0_Backup()); }

    /// <summary>着工前の地形を .bin へ。**無いときだけ書く**。
    /// ⚠ 走るたび上書きすると、造成済みの(壊れた)地形がバックアップに化ける
    ///   — 旧版で実際に起きた(2026-08-16 の退避は既に造成後だった)。</summary>
    public static string Stage0_Backup() { using (OnKita()) return Stage0_Backup_(); }
    static string Stage0_Backup_()
    {
        if (File.Exists(BakPath)) return "退避: 既にある(上書きしない) " + BakDir;
        var t = EdoBuild.T(); var td = t.terrainData;
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
        var t = EdoBuild.T(); var td = t.terrainData;
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

    public static string Stage1_Grade() { using (OnKita()) return Stage1_Grade_(); }
    static string Stage1_Grade_()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Stage0_Backup());
        var t = EdoBuild.T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        int x0, z0, w, h; Window(out x0, out z0, out w, out h);
        // ⭐ 縁の皮(Stage3b)を先に外して穴を塞ぐ ── 皮は駒の今の位置に合わせて起こす物で、造成・据え直しの後は古い(EdoBuild.ClearEdgeSkins)
        {
            var rootG = GameObject.Find(GN); var es = rootG == null ? null : rootG.transform.Find("EdgeSkin");
            if (es != null && es.childCount > 0) sb.AppendLine("縁の皮を外して塞いだ升 " + EdoBuild.ClearEdgeSkins(Group("EdgeSkin")) + "(3 の後に 3b で起こし直す)");
        }
        // ⭐ 線の外の 2m 格子の写しの波及(細かい地形は大地形を写して起こした ── 線の内の高い節点から線の外 2m まで斜めに描かれる)を造成前の地盤へ戻す
        //   (const.perimeterRetain【硬】「線の外へ岡部の造成が波及していれば造成前の地盤(base_dem)へ戻す」・道の線際の均しより前に)
        if (EdoBuild.TerrainCell(t) < 1f) sb.AppendLine(RestorePerimeterSpill_(2.0f));
        var H = td.GetHeights(x0, z0, w, h);
        var P = Poly;
        var G0 = Graded; sb.AppendLine(_gradedFrom + "・地形 " + t.name + "(" + EdoBuild.TerrainCell(t).ToString("0.###") + "m)");
        int n = 0, hole = 0; float cmax = 0f, fmax = 0f;
        var mn = MichiNarashi; int nMichi = 0; float mMax = 0f;
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                var p = new Vector2(tp.x + (x0 + x) * ts.x / (hres - 1), tp.z + (z0 + z) * ts.z / (hres - 1));
                if (!EdoGeom.PIP(P, p))
                {   // ⛔ 敷地の外は触らない ── ただし道の線際の帯の均し(算出物 michiNarashi)の帯の中だけ、今の地形より低い所へ下げる【硬: 盛らない】
                    if (mn == null) continue;
                    float ym = MichiNarashiAt(mn, p.x, p.y); if (float.IsNaN(ym)) continue;
                    float curM = H[z, x] * ts.y + tp.y;
                    if (ym < curM - 1e-4f) { mMax = Mathf.Max(mMax, curM - ym); H[z, x] = (ym - tp.y) / ts.y; nMichi++; }
                    continue;
                }
                float y = Graded.At(p.x, p.y);
                if (float.IsNaN(y)) { hole++; continue; }    // 算出物に穴 — 触らずに数える
                float cur = H[z, x] * ts.y + tp.y;
                if (y < cur) cmax = Mathf.Max(cmax, cur - y); else fmax = Mathf.Max(fmax, y - cur);
                H[z, x] = (y - tp.y) / ts.y; n++;
            }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        sb.AppendLine("造成 " + n + " セル(窓 " + w + "x" + h + ")｜今回の移動量: 下げ最大 "
                      + cmax.ToString("F2") + "m / 上げ最大 " + fmax.ToString("F2") + "m");
        if (mn != null) sb.AppendLine("道の線際の帯の均し(区画の外・michiNarashi): 下げた升 " + nMichi + "・下げ最大 " + mMax.ToString("F2") + "m(盛り 0)");
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
        var t = EdoBuild.T(); float cell = t.terrainData.size.x / (t.terrainData.heightmapResolution - 1);
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
            (h, g, i) => EdoAssets.Own.Nozura2(h, g, i), (h, i) => EdoAssets.Own.SannoNozuraKado(h, i),   // 直線の駒は重ねの端の版(EDO-0502 第104巡・継ぎ目の隙と段差)
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
    public static string GradeQA(List<Vector3> badAt) { using (OnKita()) return GradeQA_(badAt); }
    static string GradeQA_(List<Vector3> badAt)
    {
        float TOL = ImplTol("gradeTol", 0.30f);
        var t = EdoBuild.T(); var td = t.terrainData;
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

    public static string Stage2_Perimeter() { using (OnKita()) return Stage2_Perimeter_(); }
    static string Stage2_Perimeter_()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder();
        var wait = new List<string>();
        EdoBuild.NaturalMode = false;      // 天端は run の seat で通す
        var kak = Group("Kakoi"); Clear(kak); _tomePlaced.Clear();
        ClearHeiLine(); _hlFootErr = 0f;

        // ---- 天端の切れ目(runs[].seatRule【柔】)を今の地形で解く ── 基壇と練塀が同じ割りで読む(第113巡)----
        sb.Append(SolveSeatRules(1.0f));
        // ---- 石垣基壇(⭐ 囲いより**先**に ── 囲いの外面 = 線から 法肩の控え c + 犬走り・c は据えた基壇の実測 const.kidan 甲の型)----
        sb.AppendLine(PlaceIshigaki());
        // ---- ⭐ 芯線(const.heiLine・第120巡)── c は据えた基壇の実測 ⇒ 基壇の後に一続きの控え d を解く(隅・長屋・練塀の外面が同じ線を読む)
        { string hf = HeiLineFace(); if (hf != null) sb.AppendLine(hf); }
        //   ⭐ 天端の線(const.heiLine.tenba・案1・第121巡)── 指図の値(決めた座・段)で一本に決める。隅を据える前に(坂の隅の勾配・段の面に掛かる腕の詰めを隅が読む)
        { string ht = HeiLineTenba(); if (ht != null) sb.AppendLine(ht); }
        //   ⭐ 台の区間と倍率を天端の線の座から(runs[].sFrom・第121巡)── 台を据え直して c を測り直し、芯線の控え d と天端の線を解き直す(座は指図の値のまま・折れ点だけ動く)
        if (_hlProfiles.Count > 0)
        {
            string hb = HeiLineBaseFromTenba(); if (hb != null) sb.AppendLine(hb);
            var keepB = new Dictionary<string, KeyValuePair<float, List<Vector2>>>(_hlBase);
            sb.AppendLine("  台を天端の線の座で据えた: " + IshigakiHead(PlaceIshigaki()));
            { string hf2 = HeiLineFace(); if (hf2 != null) sb.AppendLine("  芯線を解き直した(台の c の実測から)"); }
            { string ht2 = HeiLineTenba(); if (ht2 != null) sb.AppendLine("  天端の線を解き直した: " + ht2.Split('\n')[0]); }
            _hlBase.Clear(); foreach (var kv in keepB) _hlBase[kv.Key] = kv.Value;
        }

        // ---- 表長屋・表門(⭐ 練塀より**先**に据える)-----------------------
        //   隅の返し(短い練塀)は長屋の**実測の妻面**へ突き付けるので、先に据えて面を測る
        _nagayaSpan.Clear();
        string nagRep = PlaceOmoteNagaya(kak, wait);

        // ---- 隅の留め継ぎ(⭐ 練塀より**先**に据え、腕の実端面を測る)-----------
        //   ⛔ 隅は区画線の上に据わるので、run だけ犬走りへ寄せると隅が壁面より 0.76m 外へ張り出し、
        //     腕(±4.1m)が run の端と重なる(2026-09-21 実測)。⭕ 先に据えて犬走りへ寄せ、
        //     **辺の端の run の端を腕の実端面へ突き付ける**(`EdoBuild.KadoFace` / `KadoArm`・docs/oki-kata.md §2)。
        sb.Append(PrePlaceTomeForKado(kak));
        sb.AppendLine(PlaceKado(kak));
        var kadoLo = new Dictionary<int, float>();   // 辺 → 隅の壁体が s=0 側から覆う上限
        var kadoHi = new Dictionary<int, float>();   // 辺 → 隅の壁体が s=L 側から覆う下限
        sb.AppendLine(FitKado(kak, kadoLo, kadoHi));
        //   ⭐ 角 P0 の段の小口へ辺0 の練塀の頭を突き付ける(指図 cornerP0.hei【柔】・第109巡)── 小口の s は隅の駒の実メッシュで測った値(PlaceIshigaki)。
        //   隅の腕の端と同じ扱い(kadoLo)⇒ 切りの駒を使わず直角の端で止まる。当たる先: 角で天端を変えない段の小口に練塀が続く辺(いまは岡部 辺0)。
        if (!float.IsNaN(_p0KoguchiS)) { float q0; kadoLo[0] = kadoLo.TryGetValue(0, out q0) ? Mathf.Max(q0, _p0KoguchiS) : _p0KoguchiS; sb.AppendLine("  角 P0 の段の小口 s " + _p0KoguchiS.ToString("F3") + " へ辺0 の練塀の頭を突き付ける(cornerP0.hei)"); }
        sb.Append(ButtMissingKado(kak, kadoLo, kadoHi));
        //   ⭐ 天端の線(const.heiLine.tenba・第121巡)── 隅を両腕の先の足で線へ据え、台の石垣を同じ天端の線で据え直す(台の石垣の天端は塀の天端の線に従う)
        if (_heiLineD != null && _hlProfiles.Count > 0)
        {
            {
                sb.AppendLine(SeatHeiLineKado(kak)); var c0 = new Dictionary<string, float>(_kidanC);
                sb.AppendLine("  基壇を天端の線で据え直した: " + IshigakiHead(PlaceIshigaki()));
                foreach (var kv in c0) { float c1; if (_kidanC.TryGetValue(kv.Key, out c1) && Mathf.Abs(c1 - kv.Value) > 0.005f) sb.AppendLine("  ★ 据え直しで " + kv.Key + " の c が " + kv.Value.ToString("F3") + " → " + c1.ToString("F3") + " ── d は前の c で解いた"); }
            }
        }
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
        //   ⭐ 台の石垣(据えた基壇)の上の練塀は腰なしの駒(const.heiLine.koshi【硬】・EdoBuild.StoneBaseUnder が足の下の石の天端で決める)
        var hlStones = HeiBaseStones();
        foreach (var r in Runs)
        {
            if (r.Nagaya) continue;                       // 表長屋は下でまとめて据える
            if (!r.Dobei)
            { sb.AppendLine("★ run " + r.name + " の kind が未知: " + r.kind); continue; }
            Vector2 outw = OutNormal(r.edge);
            // ⭐ **隅の返し**の納め(指図「隅の納め」の章・K063 章番号で引かない)。隣が長屋の run なら、その**実測の妻面**へ突き付ける。
            //   ⛔ 呼び寸法で継がない(可動側は返し=練塀の側)。
            float rs0 = r.s0, rs1 = r.s1;
            bool held0 = false, held1 = false;   // 端が相手(長屋・門・柱・隅・切り)に受けられている ⇒ 端の駒を使わない
            foreach (var nr in Runs)
            {
                if (!nr.Nagaya || nr.edge != r.edge || !_nagayaSpan.ContainsKey(nr.name)) continue;
                var span = _nagayaSpan[nr.name];
                if (Mathf.Abs(nr.s1 - r.s0) < 0.30f) { rs0 = span.y; held0 = true; }   // 長屋の北 → 返しの南の小口
                if (Mathf.Abs(nr.s0 - r.s1) < 0.30f) { rs1 = span.x; held1 = true; }
            }
            if (Mathf.Abs(rs0 - r.s0) > 0.001f || Mathf.Abs(rs1 - r.s1) > 0.001f)
                wait.Add("練塀 " + r.name + ": 隣の長屋の**実測の妻面**へ寄せた s "
                       + r.s0.ToString("0.###") + "〜" + r.s1.ToString("0.###") + " → "
                       + rs0.ToString("0.###") + "〜" + rs1.ToString("0.###")
                       + "(⛔ 呼び寸法で継がない・可動側は練塀)");
            // ⭐ 小門の脇:門構えの脇の面(札の jamb)へ突き付ける(⛔ 指図の s で止めない ── 門の柱と 0.63m 開いた・EDO-0502)
            bool komon0 = false, komon1 = false;   // 門の脇 ⇒ 端の駒(棟止め)
            foreach (var kj in _komonJamb)
            {
                if ((int)kj.x != r.edge) continue;
                if (Mathf.Abs(r.s1 - kj.y) < 0.60f) { wait.Add("練塀 " + r.name + ": 小門の脇の面へ s1 " + rs1.ToString("0.###") + " → " + (kj.y + KOMON_BITE).ToString("0.###")); rs1 = kj.y + KOMON_BITE; komon1 = true; }
                if (Mathf.Abs(r.s0 - kj.z) < 0.60f) { wait.Add("練塀 " + r.name + ": 小門の脇の面へ s0 " + rs0.ToString("0.###") + " → " + (kj.z - KOMON_BITE).ToString("0.###")); rs0 = kj.z - KOMON_BITE; komon0 = true; }
            }
            // ⭐ **辺の端の run だけ**を、隅の腕の実端面へ突き付ける(辺の途中の run は触らない)。
            //   ⛔ 呼び寸法で継がない — 腕は部材が持つ寸法で、run の端は腕が決める。
            float qa; bool cornerEnd0 = false, cornerEnd1 = false;
            if (r.s0 <= edgeMinS0[r.edge] + 1e-3f && kadoLo.TryGetValue(r.edge, out qa)) { rs0 = qa; cornerEnd0 = true; }
            if (r.s1 >= edgeMaxS1[r.edge] - 1e-3f && kadoHi.TryGetValue(r.edge, out qa)) { rs1 = qa; cornerEnd1 = true; }
            // ⭐ 端を別の辺の長屋の妻の面へ突き込む(指図 runs[].join0 / join1「…端は長屋 X の妻の面へ突き込み 隙0【硬】」・施主裁定 2026-10-12 案A・第113巡)
            //   ── 長屋の実メッシュへ光線を打って面を測る(⛔ 長屋の寸法・ピボットで決めない)。当たる先: 辺の折れの先で長屋の妻が囲いを受ける練塀(いまは岡部 S_Hei_01)。
            // ⭐ 留め柱(指図 runs[].tomeBashira「東の面を長屋 X の背の面に接して立てる・練塀の端はこの柱へ突き込む(重ね ≥0.05)」・第114巡)── 柱を先に据え(固定側)、
            //   練塀の端は柱の実メッシュの面まで(可動側)。join0/join1 の長屋の妻への突き込みはこの端では打たない(柱が受ける)。
            int tomeEnd = PlaceTomeBashira(kak, r, ref rs0, ref rs1, wait);
            bool joined0 = tomeEnd == 0 || JoinEndToNagaya(kak, r, true, ref rs0, wait), joined1 = tomeEnd == 1 || JoinEndToNagaya(kak, r, false, ref rs1, wait);
            if (joined0) cornerEnd0 = true; if (joined1) cornerEnd1 = true;
            // ⭐ 辺の端の練塀が隣の辺の線へ斜めに当たる端は、端を隣の辺の線で切った駒(DobeiKiri)で納める(EDO-0502 2026-10-03)。
            //   隅の腕の無い端だけ。焼いてある角だけ(KiriEnd が null なら直角の端のまま)。
            var kiris = new List<KeyValuePair<string, Vector3>>();
            //   ⭐ 一枚物の練塀(施主裁定 2026-10-12 案1)には斜めに切った駒が無い ── 長屋の妻へ斜めに当たる端は、直角の端を妻の面へ**厚みの全幅で**突き込む
            //   (光線で妻の面の最も奥まで ── 隙0・入る角は長屋の躯体の中へ埋める・oki-kata §4)。隣の辺の線で切る端は直角のまま ⚠。
            if (!cornerEnd0 && r.s0 < 0.01f) { var k0 = KiriEnd(r, true, ref rs0); if (k0.Key != null) { rs0 = r.s0; if (JoinEndToGable(kak, r, true, ref rs0, wait)) { cornerEnd0 = true; held0 = true; } else wait.Add("練塀 " + r.name + ": 始めを斜めに切る駒が一枚物に無い ── 直角の端 ⚠"); } }
            if (!cornerEnd1 && r.s1 > EdgeLen(r.edge) - 0.01f) { var k1 = KiriEnd(r, false, ref rs1); if (k1.Key != null) { rs1 = r.s1; if (JoinEndToGable(kak, r, false, ref rs1, wait)) { cornerEnd1 = true; held1 = true; } else wait.Add("練塀 " + r.name + ": 終わりを斜めに切る駒が一枚物に無い ── 直角の端 ⚠"); } }
            foreach (var kn0 in _kiriNotes) wait.Add("練塀 " + kn0); _kiriNotes.Clear();
            //   自由端(何にも受けられない端・門の脇)は端の駒(棟止め・鬼瓦)
            //   隣の辺の長屋が端の頂点から始まる(終わる)なら、その長屋の側面が端を受ける(held)
            { int nP = Poly.Length;
              foreach (var nr in Runs)
              {
                  if (!nr.Nagaya) continue;
                  if (r.s0 < 0.01f && nr.edge == (r.edge - 1 + nP) % nP && nr.s1 > EdgeLen(nr.edge) - 0.30f) held0 = true;
                  if (r.s1 > EdgeLen(r.edge) - 0.01f && nr.edge == (r.edge + 1) % nP && nr.s0 < 0.30f) held1 = true;
              } }
            bool free0 = komon0 || (!cornerEnd0 && !held0 && tomeEnd != 0), free1 = komon1 || (!cornerEnd1 && !held1 && tomeEnd != 1);
            // 切った駒だけで run が埋まる(残りの直線が 0.5 未満・隅の腕と重なる)なら、切った駒だけを据える ── 重なりは隅の腕の中へ埋める(oki-kata §4)
            bool kiriOnly = kiris.Count > 0 && rs1 - rs0 < 0.5f;
            //   ⭐ 一枚物は腕の先も切りも断面で塞いである ⇒ 隅の腕の間は**突き付けで割り切る**(重ねない・どんな短さでも瓦の切りを倍率で合わせる)。
            //   ⛔ 旧い 0.5 の駒を腕へ重ねる納め(第115巡)は表裏 2 枚の時の物。口が 0.005 以下は閉じている扱い・負は腕どうしが重なる(隅の腕の選びの話 ⇒ ★)
            if (rs1 - rs0 <= 0.005f)
            {
                if (rs1 - rs0 < -0.005f) wait.Add("練塀 " + r.name + ": 隅の腕の実端面どうしが " + (rs0 - rs1).ToString("F3") + "m 重なる ── 直線の駒を置かない(腕の短い隅が要る)⛔");
                else wait.Add("練塀 " + r.name + ": 隅の腕の実端面どうしが突き付く(口 " + (rs1 - rs0).ToString("F3") + ")── 直線の駒は要らない");
                continue;
            }
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
            if (free0 || free1) wait.Add("練塀 " + r.name + ": 自由端" + (free0 ? (komon0 ? " 始め(門の脇)" : " 始め") : "") + (free1 ? (komon1 ? " 終わり(門の脇)" : " 終わり") : "") + " に端の駒(棟止め)");
            Vector2 a = EdgePt(r.edge, rs0), b = EdgePt(r.edge, rs1);
            if (r.lineS != null)
            {
                // ⭐ 天端の線(const.heiLine.tenba・案1)── 区間 = 段・勾配の変わる所(基壇と同じ割り SeatBreaks)・各区間は平らか坂なり(EdoBuild.NeribeiLineRun)。
                //   段の面は上下の両方に棟止め(端の柱の外面を段の面で背中合わせ)・自由端(門の脇・何にも受けられない端)も棟止め。⛔ 2m で割らない
                var brk = SeatBreaks(r, rs0, rs1);
                for (int q = 0; q + 1 < brk.Count; q++)
                {
                    float sa = brk[q], sbb = brk[q + 1]; int kq = r.LineIndexAt(0.5f * (sa + sbb));
                    var eA = q == 0 ? (free0 ? EdoBuild.HeiEnd.Free : (r.StepAtS(sa) ? EdoBuild.HeiEnd.Step : EdoBuild.HeiEnd.None)) : (r.StepAtS(sa) ? EdoBuild.HeiEnd.Step : EdoBuild.HeiEnd.None);
                    var eB = q + 2 == brk.Count ? (free1 ? EdoBuild.HeiEnd.Free : (r.StepAtS(sbb) ? EdoBuild.HeiEnd.Step : EdoBuild.HeiEnd.None)) : (r.StepAtS(sbb) ? EdoBuild.HeiEnd.Step : EdoBuild.HeiEnd.None);
                    string nt; float fe;
                    EdoBuild.NeribeiLineRun(kak, EdgePt(r.edge, sa), EdgePt(r.edge, sbb), outw, r.name + "_" + q, r.SeatOnRow(kq, sa), r.lineGrade == null ? 0f : r.lineGrade[kq], eA, eB, -0.10f, FaceIn(r.edge, 0.5f * (sa + sbb)), out nt, out fe, hlStones);
                    if (nt != null) wait.Add("練塀 " + r.name + "_" + q + ": " + nt);
                    _hlFootErr = Mathf.Max(_hlFootErr, fe);
                }
                hei++;
            }
            else if (r.hasStep)
            {
                // 天端の切れ目(seatRule)── 基壇と同じ割り(SeatBreaks)で、区間ごとにその天端で据える
                var brk = SeatBreaks(r, rs0, rs1);
                for (int q = 0; q + 1 < brk.Count; q++)
                    HeiRun(kak, EdgePt(r.edge, brk[q]), EdgePt(r.edge, brk[q + 1]), outw, r.name + "_" + q, r.SeatAt(0.5f * (brk[q] + brk[q + 1])), free0 && q == 0, free1 && q + 2 == brk.Count, wait);
                hei++;
            }
            else if (Mathf.Abs(r.seat1 - r.seat0) < 0.01f)
            {
                HeiRun(kak, a, b, outw, r.name, r.seat0, free0, free1, wait);
                hei++;
            }
            else
            {
                // 斜面の run は天端が一直線に下るので、2m 刻みに割ってその位置の天端で据える
                // (石垣そのものは水平が正典。run 全体では階段状に下る)
                float L = (b - a).magnitude;
                //   ⭐ 自由端の区間は端の駒(一枚分 ≈3.1)が入る長さにとる(第118巡 ── 2m の区間では棟止めが入らない)。残りを 2m ほどに等分
                const float END_SEG = 3.15f;
                float hA = free0 ? Mathf.Min(END_SEG, L) : 0f, hB = free1 ? Mathf.Min(END_SEG, Mathf.Max(0f, L - hA)) : 0f;
                var cuts = new List<float> { 0f }; if (hA > 0f) cuts.Add(hA);
                float mA = hA, mB = L - hB, mL = mB - mA;
                if (mL > 0.01f) { int nm = Mathf.Max(1, Mathf.RoundToInt(mL / 2.0f)); for (int q = 1; q <= nm; q++) cuts.Add(mA + mL * q / nm); }
                if (hB > 0f && cuts[cuts.Count - 1] < L - 1e-3f) cuts.Add(L);
                if (cuts[cuts.Count - 1] < L - 1e-3f) cuts.Add(L);
                int nSeg = cuts.Count - 1;
                for (int q = 0; q < nSeg; q++)
                {
                    Vector2 pa = Vector2.Lerp(a, b, cuts[q] / L);
                    Vector2 pb = Vector2.Lerp(a, b, cuts[q + 1] / L);
                    float sMid = rs0 + 0.5f * (cuts[q] + cuts[q + 1]) * (rs1 - rs0) / L;
                    HeiRun(kak, pa, pb, outw, r.name + "_" + q, r.SeatAt(sMid), free0 && q == 0, free1 && q == nSeg - 1, wait);
                }
                hei++;
            }
        }
        sb.AppendLine(nagRep);
        sb.AppendLine("練塀: " + hei + " run 据えた" + (_hlProfiles.Count > 0 ? "(天端の線の駒の足の端の線からの食い違いの最大 " + _hlFootErr.ToString("F3") + ")" : ""));
        // 留め柱への突き込みの実測(練塀の駒の実頂点の端 − 柱の遠い面)── 重ね ≥ join の b【硬】
        foreach (var tp in _tomePlaced)
        {
            if (tp.Key == null) continue; var rr = Runs[(int)tp.Value.x]; Vector2 er = EdgePt(rr.edge, 0f), dr = (EdgePt(rr.edge, 1f) - er).normalized;
            float wMin = float.MaxValue, wMax = float.MinValue;
            foreach (Transform c in kak) if (c.name.StartsWith(rr.name + "_")) foreach (var v in EdoBuild.Body(c, 999999)) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - er, dr); wMin = Mathf.Min(wMin, sv); wMax = Mathf.Max(wMax, sv); }
            float ovl = tp.Value.y < 0.5f ? tp.Value.z - wMin : wMax - tp.Value.z;
            sb.AppendLine("  留め柱 " + tp.Key.name + ": 練塀 " + rr.name + " の" + (tp.Value.y < 0.5f ? "始め" : "終わり") + "の柱の中への重ね(実頂点) " + (wMin == float.MaxValue ? "-(駒なし)" : ovl.ToString("F3") + (ovl >= 0.05f - 1e-3f ? " ⭕" : " ⛔")));
        }

        // ---- 犬走りへ寄せる(据えた駒の実メッシュから外面を測る)----------
        sb.AppendLine(AlignInubashiri());
        sb.AppendLine(SeatKadoToRuns(kak));
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
                if (ri < 0 || !Runs[ri].Dobei || OnHeiLine(Runs[ri])) continue;   // 天端の線・芯線の run は線が区画の内(d ≥ c + 犬走り)── 事後に引かない
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

        // ---- 石垣基壇 ── ⭐ 囲いより先に据えた(外面の線は基壇の法肩から)
        // ---- 硬い・地面(浮き 0): 練塀・隅・端を切った駒を、描かれた地表と基壇の天端の高い方へ組ごと据える(EdoBuild.SinkGroupToBed)。
        //      ⛔ 指図の seat(下絵の値)を底に残さない ── 辺34 で 2.6〜2.8m 埋まった(2026-10-04 EDO-0502 第12巡)。
        sb.AppendLine(SeatHeiOnBed(kak));
        // ---- ⭐ 塀の内の帯を坂なりの線に揃える(const.heiLine.tenba.band・第121巡)── 練塀を据えた後に内面を測って
        sb.AppendLine(HeiLineBand());

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

    /// <summary>**岡部の練塀の駒**(施主裁定 2026-10-12「案1」・EDO-0502 第118巡)── 一枚物の閉じた断面 <see cref="EdoBuild.NeribeiPanelRun"/>
    /// (旧 <c>EdoBuild.DobeiRun</c> の表裏 2 枚は他邸のまま)。芯は線から −0.10(旧い表裏の組の中ほど)── 外面は <see cref="AlignInubashiri"/> が実メッシュで寄せる。</summary>
    static void HeiRun(Transform kak, Vector2 a, Vector2 b, Vector2 outw, string name, float seat, bool endA, bool endB, List<string> wait) { HeiRun(kak, a, b, outw, name, seat, endA, endB, float.NaN, wait); }
    /// <summary><paramref name="faceIn"/>: 天端の線・芯線の run(const.heiLine)── 外面を線から faceIn 内へ**据える時に**実メッシュの壁面で合わせる(⛔ 後で AlignInubashiri で寄せない)。NaN = 従来(芯 −0.10・後で寄せる)。</summary>
    static void HeiRun(Transform kak, Vector2 a, Vector2 b, Vector2 outw, string name, float seat, bool endA, bool endB, float faceIn, List<string> wait)
    {
        string nt; EdoBuild.NeribeiPanelRun(kak, a, b, outw, name, seat, endA, endB, -0.10f, out nt, faceIn, float.IsNaN(faceIn) ? 0.10f : 0f);
        if (nt != null) wait.Add("練塀 " + name + ": " + nt);
    }

    /// <summary>辺の端の練塀が隣の辺の長屋の妻へ斜めに当たる端(旧い <see cref="KiriEnd"/> が長屋の妻で切った端)を、直角の端のまま妻の面へ**厚みの全幅で**突き込む
    /// (<see cref="JoinEndToNagaya"/> と同じ光線 3×7 ── 最も奥の当たり + 0.05)。相手の長屋 = 隣の辺の長屋の run で、端の頂点に接する物。
    /// 硬い(隙0 ── 入る角は長屋の躯体の中へ埋める)。当たる先: 一枚物の練塀が長屋の妻へ斜めに当たる端(いまは岡部 N_Hei_35 の終わり × N39_0)。</summary>
    static bool JoinEndToGable(Transform kak, Run r, bool atStart, ref float sEnd, List<string> wait)
    {
        int n = Poly.Length, ne = atStart ? (r.edge - 1 + n) % n : (r.edge + 1) % n;
        Transform ng = null;
        foreach (var nr in Runs)
        {
            if (!nr.Nagaya || nr.edge != ne) continue;
            bool hit = (!atStart && nr.s0 < 0.30f) || (atStart && nr.s1 > EdgeLen(ne) - 0.30f);
            if (hit) { ng = kak.Find(nr.name); if (ng != null) break; }
        }
        if (ng == null) return false;
        return JoinEndToBody(r, atStart, ng, ref sEnd, wait);
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
    /// <summary>run の端を長屋の妻の面へ突き込む(runs[].join0 / join1「長屋 X の妻の面へ突き込み 隙0」)。光線 3×7(高さ 座 +0.3/+1.0/+1.8 × 練塀の厚みの全幅)を
    /// 端の 1m 手前から走りの外へ打ち、長屋の躯体(屋根を除く)の面の最も奥の当たりまで延ばす(突き込み 0.05)。⟶ 突き込んだか(書けない・当たらないは ★ を wait へ)。</summary>
    static bool JoinEndToNagaya(Transform kak, Run r, bool atStart, ref float sEnd, List<string> wait)
    {
        string jt = RunText(r.name, atStart ? "join0" : "join1"); if (jt == null) return false;
        var m = System.Text.RegularExpressions.Regex.Match(jt, @"長屋\s*(\w+)\s*の妻の面へ突き込み");
        if (!m.Success) { wait.Add("練塀 " + r.name + ": " + (atStart ? "join0" : "join1") + " が読めない ── 端は従前"); return false; }
        var ng = kak.Find(m.Groups[1].Value); if (ng == null) { wait.Add("練塀 " + r.name + ": 長屋 " + m.Groups[1].Value + " が無い ── 端は従前"); return false; }
        return JoinEndToBody(r, atStart, ng, ref sEnd, wait);
    }
    static bool JoinEndToBody(Run r, bool atStart, Transform ng, ref float sEnd, List<string> wait)
    {
        Vector2 dir = (EdgePt(r.edge, 1f) - EdgePt(r.edge, 0f)).normalized, inw = -OutNormal(r.edge); float T = C("dobeiT");
        float sRef = atStart ? r.s0 + 1.0f : r.s1 - 1.0f; Vector2 toward = atStart ? -dir : dir; float y0 = r.SeatAt(atStart ? r.s0 : r.s1);
        float dF = FaceIn(r.edge, atStart ? r.s0 : r.s1); var bodies = new List<GameObject> { ng.gameObject };
        float far = float.NaN; int hits = 0;
        foreach (float yy in new[] { 0.3f, 1.0f, 1.8f })
            for (int li = 0; li <= 6; li++)   // 練塀の厚みの全幅(外面 −0.15 〜 内面)── 長屋の背より内へ出る所は当たらない(当たった所だけで測る)
            {
                float lat = -0.15f + (T + 0.15f) * li / 6f;
                Vector2 o2 = EdgePt(r.edge, sRef) + inw * (dF + lat);
                float t = EdoBuild.RayToBodies(bodies, new Vector3(o2.x, y0 + yy, o2.y), new Vector3(toward.x, 0f, toward.y), 4f); if (float.IsNaN(t)) continue;
                hits++; float sF = atStart ? sRef - t : sRef + t;
                far = float.IsNaN(far) ? sF : (atStart ? Mathf.Min(far, sF) : Mathf.Max(far, sF));
            }
        if (hits == 0) { wait.Add("練塀 " + r.name + ": 長屋 " + ng.name + " の妻の面に光線が当たらない(端から 4m 内)── 端は従前"); return false; }
        const float BITE = 0.05f; float was = sEnd;
        sEnd = atStart ? far - BITE : far + BITE;
        wait.Add("練塀 " + r.name + ": " + (atStart ? "始め" : "終わり") + "を長屋 " + ng.name + " の妻の面(光線 " + hits + "/9・最も奥 s " + far.ToString("F3") + ")へ " + BITE.ToString("F2") + " 突き込んだ s " + was.ToString("F3") + " → " + sEnd.ToString("F3") + "(join【硬】隙0)");
        return true;
    }

    /// <summary>練塀の留め柱の天端 = 練塀の座 + この値(EdoAssets.Goten.Column の注: 駒 s_hei_center の壁の天端 1.306 × ES・笠の下)。</summary>
    const float TOME_TOP_ABOVE_SEAT = 2.274f;
    static readonly List<KeyValuePair<GameObject, Vector3>> _tomePlaced = new List<KeyValuePair<GameObject, Vector3>>();   // 柱 → (run の番号, 端 0/1, 柱の遠い面の s)
    /// <summary>**練塀の留め柱**(指図 runs[].tomeBashira ── face「東の面を長屋 X の背の面に接して立てる【硬: 隙0】。X の妻の面を南北に d ずつ跨ぐ」・join「練塀の端はこの柱へ突き込む(重ね ≥ b)」
    /// ・h「笠の下まで」・foot「根は床 −0.05」・普請方の設計 2026-10-12・EDO-0502 第114巡)。部材 = <see cref="EdoAssets.Goten.Column"/>(ピボットは角 ⇒ 据えは実メッシュで測る)。
    /// 置き方(oki-kata の4手): ① 固定側 = 長屋 X の実メッシュ ── 背の面 = 座 +0.1〜+1.2 の帯の頂点の最も奥(<see cref="EdoBuild.FaceOut"/>・長屋の辺の内向き)、
    /// 妻の面 = 札の躯体の実端(<see cref="EdoBuild.SpecBodySpanAlong"/>)のうち練塀の端に近い方。② 柱を長屋の辺の向きに据え、柱の実頂点で 東の面 = 背の面・走りの芯 = 妻の面・天端 = 座 + 2.274。
    /// ③ 練塀の端(可動側)= 柱の遠い面 − 重ね。④ 測る: 柱と背の面の隙(光線)・跨ぎ・根と地表。⟶ 端(0 = 始め / 1 = 終わり / −1 = 柱なし)。
    /// 当たる先: 入隅で練塀の端を長屋の背の面に留める所(いまは岡部 S_Hei_01 × N41_5)。</summary>
    /// <summary>最後に据えた留め柱の (柱の s の最小, 最大, 重ね b, 端 0/1)── 練塀の辺の始めから。</summary>
    static Vector4 _tomeLast;
    /// <summary>辺 → 隅でない端(留め柱)から測った腕の先の範囲 (tMin, tMax)── <see cref="PlaceKado"/> の <c>EdoBuild.KadoArms</c> へ(第116巡)。</summary>
    static readonly Dictionary<int, Vector2> _kadoFreeEnd = new Dictionary<int, Vector2>();
    /// <summary>**留め柱を隅の駒より先に据え**、柱で止まる辺の腕の先の範囲を取る(第116巡 ── 第115巡 P2 の腕が辺1 を 0.75 越えて長屋 N41_5 の妻と柱を貫いた)。
    /// 腕の先 t(隅でない端の頂点から)∈ [柱の近い面, 柱の遠い面 − 重ね]【硬】。柱は練塀の run の据えで同じ所へ据え直す(冪等)。</summary>
    static string PrePlaceTomeForKado(Transform kak)
    {
        _kadoFreeEnd.Clear(); var w = new List<string>(); var inv = System.Globalization.CultureInfo.InvariantCulture; var sb = new System.Text.StringBuilder();
        foreach (var r in Runs)
        {
            if (!r.Dobei) continue; float a = r.s0, b = r.s1; int end = PlaceTomeBashira(kak, r, ref a, ref b, w); if (end < 0) continue;
            float L = EdgeLen(r.edge); var t = _tomeLast;
            Vector2 fe = end == 0 ? new Vector2(t.x, t.y - t.z) : new Vector2(L - t.y, L - t.x - t.z);
            _kadoFreeEnd[r.edge] = fe;
            sb.AppendLine("  留め柱を隅より先に: 辺" + r.edge + " の" + (end == 0 ? "始め" : "終わり") + " ── 隅の腕の先を柱の中 t " + fe.x.ToString("F3", inv) + "〜" + fe.y.ToString("F3", inv) + "(端の頂点から)へ【硬】");
        }
        _tomePlaced.Clear();
        return sb.ToString();
    }
    static int PlaceTomeBashira(Transform kak, Run r, ref float rs0, ref float rs1, List<string> wait)
    {
        Dictionary<string, object> rd = null; foreach (var o in A(D["runs"]) ?? new List<object>()) { var q = O(o); if (q != null && S(Get(q, "name")) == r.name) rd = q; }
        var tb = O(Get(rd, "tomeBashira")); if (tb == null) return -1;
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        string fT = S(Get(tb, "face")) ?? "", jT = S(Get(tb, "join")) ?? "";
        var mN = System.Text.RegularExpressions.Regex.Match(fT, @"(N[0-9_]+)\s*の背の面に接して");         var mB = System.Text.RegularExpressions.Regex.Match(jT, @"重ね\s*≥\s*([0-9.]+)");
        if (!mN.Success || !mB.Success) { wait.Add("練塀 " + r.name + ": tomeBashira の face(長屋 X の背の面)/ join(重ね ≥ b)が読めない ── 柱を立てない"); return -1; }
        var ng = kak.Find(mN.Groups[1].Value); int ri = -1; for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == mN.Groups[1].Value) ri = k;
        if (ng == null || ri < 0) { wait.Add("練塀 " + r.name + ": 留め柱の相手の長屋 " + mN.Groups[1].Value + " が据わっていない ── 柱を立てない"); return -1; }
        float bite = float.Parse(mB.Groups[1].Value, inv);
        int eN = Runs[ri].edge; Vector2 ea = EdgePt(eN, 0f), ax = (EdgePt(eN, 1f) - ea).normalized, inw = -OutNormal(eN);
        var bp = EdoBuild.BodyExRoof(ng, 6000); if (bp.Count == 0) { wait.Add("練塀 " + r.name + ": 長屋 " + ng.name + " の躯体が測れない ── 柱を立てない"); return -1; }
        float y0 = float.MaxValue; foreach (var v in bp) y0 = Mathf.Min(y0, v.y);
        float back = EdoBuild.FaceOut(ng.gameObject, ea, inw, y0 + 0.1f, y0 + 1.2f);
        var sp = EdoBuild.SpecBodySpanAlong(ng.gameObject, ea, ax); if (float.IsNaN(sp.x)) sp = EdoBuild.BodySpanAlong(ng.gameObject, ea, ax);
        if (float.IsNaN(back) || float.IsNaN(sp.x)) { wait.Add("練塀 " + r.name + ": 長屋 " + ng.name + " の背の面・妻の面が測れない ── 柱を立てない"); return -1; }
        // どちらの端か: 練塀の両端のうち長屋の妻に近い方
        Vector2 pA = EdgePt(r.edge, r.s0), pB = EdgePt(r.edge, r.s1);
        System.Func<Vector2, float> sN = q => Vector2.Dot(q - ea, ax);
        float gA = Mathf.Min(Mathf.Abs(sN(pA) - sp.x), Mathf.Abs(sN(pA) - sp.y)), gB = Mathf.Min(Mathf.Abs(sN(pB) - sp.x), Mathf.Abs(sN(pB) - sp.y));
        int end = gA <= gB ? 0 : 1; Vector2 pE = end == 0 ? pA : pB;
        float sG = Mathf.Abs(sN(pE) - sp.x) < Mathf.Abs(sN(pE) - sp.y) ? sp.x : sp.y;
        float seat = r.SeatAt(end == 0 ? r.s0 : r.s1), top = seat + TOME_TOP_ABOVE_SEAT;
        string path = EdoAssets.Goten.Column;
        var old = kak.Find("TomeBashira_" + r.name); if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var go = EdoBuild.Place(path, new Vector3(pE.x, top, pE.y), Mathf.Atan2(ax.x, ax.y) * Mathf.Rad2Deg, Vector3.one, kak, "TomeBashira_" + r.name);
        if (go == null) { wait.Add("練塀 " + r.name + ": 留め柱 " + path + " が据わらない"); return -1; }
        // 柱の実頂点で寄せる(⛔ ピボットで決めない ── 角が原点)
        float dMin = float.MaxValue, s0 = float.MaxValue, s1 = float.MinValue, yMx = float.MinValue, yMn = float.MaxValue;
        foreach (var v in EdoBuild.Body(go.transform, 999999)) { var q = new Vector2(v.x, v.z); dMin = Mathf.Min(dMin, Vector2.Dot(q - ea, inw)); float sv = sN(q); s0 = Mathf.Min(s0, sv); s1 = Mathf.Max(s1, sv); yMx = Mathf.Max(yMx, v.y); yMn = Mathf.Min(yMn, v.y); }
        Vector2 mv = inw * (back - dMin) + ax * (sG - 0.5f * (s0 + s1));
        go.transform.position += new Vector3(mv.x, top - yMx, mv.y);
        float yBot = yMn + (top - yMx);
        // 柱の遠い面(練塀の側)の s を練塀の辺で
        Vector2 er = EdgePt(r.edge, 0f), dr = (EdgePt(r.edge, 1f) - er).normalized; float psMin = float.MaxValue, psMax = float.MinValue, dChk = float.MaxValue;
        foreach (var v in EdoBuild.Body(go.transform, 999999)) { var q = new Vector2(v.x, v.z); float sv = Vector2.Dot(q - er, dr); psMin = Mathf.Min(psMin, sv); psMax = Mathf.Max(psMax, sv); dChk = Mathf.Min(dChk, Vector2.Dot(q - ea, inw)); }
        // 隙(光線): 柱の芯から長屋の辺の外向きへ ── 当たりまでの距離 − 芯から東の面
        var cB = EdoBuild.RB(go); float cd = Vector2.Dot(new Vector2(cB.center.x, cB.center.z) - ea, inw) - dChk; float gapMax = float.MinValue; int hit = 0;
        foreach (float yy in new[] { 0.3f, 1.0f, 1.8f })
        {
            float t = EdoBuild.RayToBodies(new List<GameObject> { ng.gameObject }, new Vector3(cB.center.x, y0 + yy, cB.center.z), new Vector3(-inw.x, 0f, -inw.y), 1.0f);
            if (float.IsNaN(t)) continue; hit++; gapMax = Mathf.Max(gapMax, t - cd);
        }
        float ov = 0f; _tomeLast = new Vector4(psMin, psMax, bite, end);
        if (end == 0) { float fs = psMax; rs0 = fs - bite; ov = bite; _tomePlaced.Add(new KeyValuePair<GameObject, Vector3>(go, new Vector3(System.Array.FindIndex(Runs, x => x.name == r.name), 0f, fs))); }
        else { float fs = psMin; rs1 = fs + bite; ov = bite; _tomePlaced.Add(new KeyValuePair<GameObject, Vector3>(go, new Vector3(System.Array.FindIndex(Runs, x => x.name == r.name), 1f, fs))); }
        float gnd = EdoBuild.Ground(cB.center.x, cB.center.z);
        wait.Add("練塀 " + r.name + ": 留め柱 " + System.IO.Path.GetFileNameWithoutExtension(path) + " を長屋 " + ng.name + " の背の面(実メッシュ 線から " + back.ToString("F3", inv) + ")へ東の面で当て(光線の隙 " + (hit > 0 ? gapMax.ToString("+0.000;-0.000", inv) : "当たらず") + (hit > 0 && Mathf.Abs(gapMax) <= 0.01f ? " ⭕" : " ⚠")
                 + ")・妻の面 s " + sG.ToString("F3", inv) + " を跨ぐ(南北に ±" + (0.5f * (s1 - s0)).ToString("F3", inv) + ")・天端 " + top.ToString("F3", inv) + "(座 " + seat.ToString("F2", inv) + " + " + TOME_TOP_ABOVE_SEAT.ToString("F3", inv) + ")・根 " + yBot.ToString("F3", inv)
                 + " / 地表 " + gnd.ToString("F2", inv) + (yBot <= gnd - 0.05f ? " ⭕(根は埋まる)" : " ⚠(根が地表 −0.05 より上)") + "・練塀の" + (end == 0 ? "始め" : "終わり") + "を柱の面 s " + (end == 0 ? psMax : psMin).ToString("F3", inv) + " から " + ov.ToString("F2", inv) + " 柱の中へ(join の重ね ≥ " + bite.ToString("F2", inv) + ")");
        return end;
    }

    /// <summary>練塀の隅の駒が焼けていない出隅(算出物 corners の part = Dobei・Kado_&lt;id&gt; が据わらない)を**突き付けで仮に納める**:
    /// 入りの run は出の run の外面の線まで(s = L − 出の辺の外面の控え)、出の run は入りの run の外面から(s = 入りの辺の外面の控え)── 外の角の点で両外面が閉じる(内は厚みの分だけ重ねて埋める)。
    /// ⚠ 仮の納め ── 隅の駒(部材方)が焼けたら外れる。40° 未満の折れは触らない(直線の継ぎ)。当たる先: 腕の短い隅が焼けていない練塀の出隅(いまは岡部 P3 の 90°)。</summary>
    static string ButtMissingKado(Transform kak, Dictionary<int, float> kadoLo, Dictionary<int, float> kadoHi)
    {
        var list = A(Get(IMPL, "corners")); if (list == null) return ""; var sb = new System.Text.StringBuilder(); int n = Poly.Length;
        foreach (var o in list)
        {
            var c = O(o); if (c == null || S(Get(c, "part")) != "Dobei") continue;
            int v = ((int)F(c["vertex"]) % n + n) % n; string id = S(c["id"]); if (kak.Find("Kado_" + id) != null) continue;
            float deg = EdoBuild.KadoDeg(Poly, v); if (deg < 40f) continue;
            int eIn = (v - 1 + n) % n, eOut = v; float fA = FaceIn(eIn, EdgeLen(eIn)), fB = FaceIn(eOut, 0f), sn = Mathf.Sin(deg * Mathf.Deg2Rad);
            if (sn < 0.3f) continue;
            kadoHi[eIn] = EdgeLen(eIn) - fB / sn; kadoLo[eOut] = fA / sn;
            sb.AppendLine("  ★ 練塀の出隅 " + id + "(" + deg.ToString("F1") + "°)の隅の駒が据わらない ── 突き付けで仮に納めた(辺" + eIn + " は辺" + eOut + " の外面の線まで s " + kadoHi[eIn].ToString("F3")
                          + "・辺" + eOut + " は辺" + eIn + " の外面から s " + kadoLo[eOut].ToString("F3") + ")── 隅の駒は部材方へ");
        }
        return sb.ToString();
    }

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
        Vector2 f0 = a0 - outw * FaceIn(r.edge, atStart ? r.s0 : r.s1);   // 外面 = 法肩の控え c + 犬走り(const.kidan)
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
                // 門長屋は口の版へ差し替えてから前の面を寄せる(⛔ 先に寄せると差し替えが寄せを捨てる ── 第101巡 N40_0 の前の下水溝の外の壁が線の外 0.191)
                if (hosted) sb.Append(GateInNagaya(kak, r, call, nikai, gS, gW, gLabel, wait));
                { var tF = kak.Find(r.name); if (tF != null) sb.Append(FrontForGutter(tF.gameObject, r)); }   // 指図 runs[].front(前の下水溝の分だけ区画の線の内へ・第95巡)
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

    /// <summary>指図 runs[] の欄 key(無ければ null)。</summary>
    static string RunText(string run, string key)
    {
        foreach (var o in A(D["runs"]) ?? new List<object>()) { var q = O(o); if (q != null && S(Get(q, "name")) == run) return S(Get(q, key)); }
        return null;
    }
    /// <summary>頂点 v の隅の駒を指図が名指していれば、その部材の名(拡張子なし・<paramref name="prefix"/> で始まる物)。runs の始めの欄(join0 / kadoStart)は辺の始点 = 頂点 e、
    /// 終わりの欄(kadoEnd / join1)は辺の終点 = 頂点 e+1 を名指す(「… = &lt;名&gt;」の綴り)。無ければ null。当たる先: 部材方が名で焼いた隅の駒(岡部 P2〜P4・第114巡)。</summary>
    static string NamedCornerPart(int v, string prefix)
    {
        int n = Poly.Length;
        foreach (var o in A(D["runs"]) ?? new List<object>())
        {
            var q = O(o); if (q == null || !Has(q, "edge")) continue; int e = (int)F(q["edge"]); float s0 = Has(q, "s0") ? F(q["s0"]) : 0f, s1 = Has(q, "s1") ? F(q["s1"]) : 0f;
            var keys = new List<string>();
            if (((e % n) + n) % n == v && s0 < 0.01f) { keys.Add("join0"); keys.Add("kadoStart"); }
            if (((e + 1) % n) == v && s1 > EdgeLen(e) - 0.01f) { keys.Add("kadoEnd"); keys.Add("join1"); }
            foreach (var k in keys)
                foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(S(Get(q, k)) ?? "", @"=\s*(" + prefix + @"[0-9A-Za-z_.]+?)(?=[\s(（、。,]|で|$)"))
                    return m.Groups[1].Value;
        }
        return null;
    }

    /// <summary>前の下水溝の駒(石組の溝 型A ── 背の雨落ち・表門脇の下水と同じ型)の実測の全幅[m](外の壁を含む)。測れなければ NaN。</summary>
    static float FrontGutterWidth()
    {
        var p = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.30f); if (p == null) return float.NaN;
        var mp = EdoBuild.MizoPieceOf(p); return mp.ok ? mp.xMax - mp.xMin : float.NaN;
    }
    const float FRONT_GUTTER_GAP = 0.01f;

    /// <summary>**長屋の前の面を、前の下水溝の分だけ区画の線の内へ**(指図 runs[].front「前の面を、区画の線から『前の下水溝+外の壁』だけ内へ寄せる」【硬】・座は変えない【硬】・
    /// 普請方 2026-10-10m・EDO-0502 第95巡)。前の面 = 躯体(屋根の材を除く実頂点)の、溝の内の壁が触れる帯(底〜+0.30・土台)の、区画の線から外への最大の張り出し(<see cref="EdoBuild.FaceOut"/>)。
    /// 寄せる量 = 溝の駒(型A)の実測の全幅 + 0.01 ── 法線の向きの平行移動だけ(<see cref="EdoBuild.AlignFace"/>)。⛔ ピボット・犬走りの定数で決めない。
    /// 二階の軒は帯の外(軒は区画の線を越えてよい・施主裁定A 2026-09-21)。条件: 硬い(区域侵犯 0 ── 溝の外の壁が区画の線の内)。
    /// 当たる先: 欄 front に「区画の線」と「下水溝」を持つ長屋すべて(岡部 N39_1)。他邸の長屋も同じ欄を持てば同じ型。</summary>
    static string FrontForGutter(GameObject go, Run r)
    {
        string fr = RunText(r.name, "front"); if (fr == null || !fr.Contains("下水溝") || !(fr.Contains("区画の線") || fr.Contains("内へ寄せる"))) return "";   // 第103巡: N40_1.front は「溝の分だけ内へ寄せる」と書く(区画の線の語が無い)
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        float W = FrontGutterWidth(); if (float.IsNaN(W)) return "  ★ " + r.name + ".front: 溝の駒(DoiMizo 型A)が測れない ── 寄せない\n";
        Vector2 ea = EdgePt(r.edge, 0f), on = OutNormal(r.edge);
        var pts = EdoBuild.BodyExRoof(go.transform, 6000); if (pts.Count == 0) return "  ★ " + r.name + ".front: 躯体が測れない ── 寄せない\n";
        float y0 = float.MaxValue; foreach (var p in pts) y0 = Mathf.Min(y0, p.y);
        // 測る帯 = 溝の内の壁が触れる所(躯体の底〜+0.30 ── 土台。一階の壁は土台より 0.04 内・第95巡の一回目は壁で測り、土台と溝の間でなく溝と区画の線の間に 0.10 の土の帯が残った)
        float before = EdoBuild.FaceOut(go, ea, on, y0 - 0.01f, y0 + 0.30f);
        float mv = EdoBuild.AlignFace(go, ea, on, -(W + FRONT_GUTTER_GAP), y0 - 0.01f, y0 + 0.30f);
        if (float.IsNaN(mv)) return "  ★ " + r.name + ".front: 前の面が測れない ── 寄せない\n";
        return "  " + r.name + ": 前の面を区画の線から " + before.ToString("+0.000;-0.000", inv) + " → " + (-(W + FRONT_GUTTER_GAP)).ToString("F3", inv) + "(前の下水溝 型A 全幅 " + W.ToString("F2", inv)
             + " + " + FRONT_GUTTER_GAP.ToString("F2", inv) + "・runs.front【硬】・座 " + go.transform.position.y.ToString("F2", inv) + " は変えない)・法線へ " + mv.ToString("+0.000;-0.000", inv) + "m\n";
    }

    static bool PlaceNagayaPiece(Transform kak, string name, string path, int edge, float sMid,
                                 float seat, float call, List<string> wait, ref float lastH)
    {
        Vector2 outw = OutNormal(edge);
        float psi = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;      // 見え面 +Z を外へ
        Vector2 p = EdgePt(edge, sMid) - outw * FaceIn(edge, sMid);   // 壁の外面 → 法肩の控え c + 犬走りぶん内へ(const.kidan)
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
    static string SeatHeiOnBed(Transform kak) { return SeatHeiOnBed(kak, false); }
    /// <summary><paramref name="withMizo"/>: 床に溝・桝の駒の上面も数える(第119巡 ── 地面を焼き切った後に据える 3d では、腰の内の縁が溝の縁石の上に掛かる)。</summary>
    static string SeatHeiOnBed(Transform kak, bool withMizo)
    {
        var igs = new List<GameObject>();
        var igT = Group("Ishigaki"); foreach (Transform c in igT) if (c.gameObject.activeInHierarchy) igs.Add(c.gameObject);
        if (withMizo) foreach (var gm in MizoGroups) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) igs.Add(c.gameObject);
        var bed = new EdoBuild.Bed(igs);
        var groups = new Dictionary<string, List<GameObject>>(); int hlKeep = 0;
        foreach (Transform c in kak)
        {
            if (!c.gameObject.activeInHierarchy) continue;
            string nm = c.name, key = null;
            //   ⭐ 天端の線(const.heiLine.tenba・第121巡)の駒と隅は据えた所のまま(線の座に実メッシュの足で据えてある ── 坂なりの駒を床へ組ごと動かすと線が割れる)。
            //   低い側の浮きは 3d の足の下の地面の上げ(FillUnderFoot)が埋める。domain reload の後も指図の範囲で判じる(OnHeiLine)
            { int vv; if (nm.StartsWith("Kado_P") && int.TryParse(nm.Substring(6), out vv) && OnHeiLineVertex(vv)) { hlKeep++; continue; } }
            { bool onL = false; for (int k = 0; k < Runs.Length; k++) if (Runs[k].Dobei && nm.StartsWith(Runs[k].name + "_") && OnHeiLine(Runs[k])) { onL = true; break; } if (onL) { hlKeep++; continue; } }
            if (nm.StartsWith("Kado_") || nm.StartsWith("Kiri_")) key = HeiLineKadoKey(nm) ?? nm;
            else
            {
                for (int k = 0; k < Runs.Length; k++)
                    if (Runs[k].Dobei && nm.StartsWith(Runs[k].name + "_")) { key = HeiLinePieceKey(Runs[k], c) ?? ((nm.EndsWith("f") || nm.EndsWith("b")) ? nm.Substring(0, nm.Length - 1) : nm); break; }
            }
            if (key == null) continue;
            List<GameObject> L; if (!groups.TryGetValue(key, out L)) groups[key] = L = new List<GameObject>();
            L.Add(c.gameObject);
        }
        int n = 0, nan = 0; float up = 0f, dn = 0f; string upN = "-", dnN = "-";
        var hlSeat = new Dictionary<string, float>();   // 天端の線の区間 → 座(heiFootSpec.order「座で据える」・浮きは足の下の地面を上げて埋める FillUnderFoot)
        foreach (var r in Runs) if (r.lineSec != null) for (int k = 0; k < r.lineSec.Length; k++) hlSeat["HL_" + r.lineSec[k]] = r.lineSeat[k];
        int hlHeld = 0;
        foreach (var kv in groups)
        {
            float st, mv;
            if (hlSeat.TryGetValue(kv.Key, out st))
            {   // ⭐ 天端の線の区間は**座に据える**(上げも下げもしない ── 段の点の外で天端の段 ≤0.01【硬】・底は基壇の天端 = 座)。高い側は根入れで埋め、低い側の浮きは
                //   3d の足の下の地面の上げ(FillUnderFoot)が埋める。⛔ SinkGroupToBed で床へ動かさない(第120巡の初回: 隅の腕の中の短い駒が床の高い所へ 0.085 上がった)
                //   駒ごとに底を座へ(⛔ 組を剛体で動かさない ── 隅は前の座で据わっているので組の最下に揃えると 0.1〜0.3 ずれて残った・第120巡の二度目)
                mv = 0f; int got = 0;
                foreach (var go in kv.Value)
                {
                    float yb = float.MaxValue; foreach (var v in EdoBuild.BodyExRoof(go.transform, 999999)) yb = Mathf.Min(yb, v.y);
                    if (yb == float.MaxValue) continue; float m1 = st - yb; go.transform.position += Vector3.up * m1; if (Mathf.Abs(m1) > Mathf.Abs(mv)) mv = m1; got++;
                }
                if (got == 0) { nan++; continue; }
                hlHeld++;
            }
            else
            {
                mv = EdoBuild.SinkGroupToBed(kv.Value, bed.At);
                if (float.IsNaN(mv)) { nan++; continue; }
            }
            n++;
            if (mv > up) { up = mv; upN = kv.Key; }
            if (mv < dn) { dn = mv; dnN = kv.Key; }
        }
        return "練塀・隅を床へ据えた(浮き 0): " + n + " 組(測れず " + nan + (hlHeld > 0 ? "・天端の線の座に据えた組 " + hlHeld : "") + (hlKeep > 0 ? "・天端の線の駒は据えたまま " + hlKeep : "") + ")・最も上げた +" + up.ToString("F2") + "m @" + upN
             + " / 最も下げた " + dn.ToString("F2") + "m @" + dnN;
    }

    /// <summary>天端の線(const.heiLine)の区間ごとに床へ**組ごと**据える鍵 ── 同じ区間の駒は一つの組で動く(⛔ 駒ごとに床へ据えると区間の中に天端の段が出る【硬 ≤0.01】)。
    /// 駒の区間 = 駒の壁体の走りの中ほど(実頂点の射影)が入る run の lineS の区間。天端の線の無い run は null(従来の鍵)。</summary>
    static string HeiLinePieceKey(Run r, Transform c)
    {
        if (r.lineS == null) return null;
        Vector2 a = EdgePt(r.edge, 0f), u = (EdgePt(r.edge, 1f) - a).normalized; float lo = float.MaxValue, hi = float.MinValue;
        foreach (var v in EdoBuild.BodyExRoof(c, 999999)) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - a, u); lo = Mathf.Min(lo, sv); hi = Mathf.Max(hi, sv); }
        if (lo > hi) return null;
        return "HL_" + r.lineSec[r.LineIndexAt(0.5f * (lo + hi))];
    }
    /// <summary>隅の駒 Kado_P{v} の天端の線の鍵 ── 頂点が区間の中(頂点で段を切らない)ならその区間、頂点が段の点なら**低い側の区間**(隅の底は腕に続く直線の低い方 ──
    /// SeatKadoToRuns と同じ決め・座で止める)。天端の線の無い頂点は null(従来どおり単独で床へ・SeatKadoToRuns)。
    /// ⚠ 第120巡の初回: 段の点の隅を単独で床へ据えたら、3d で Kado_P24 が溝の脇の低い当たりへ 1.29 落ち、P22 は SeatKadoToRuns が隣の区間の先の駒(0.5 低い)を拾った。</summary>
    static string HeiLineKadoKey(string nm)
    {
        int v; if (!nm.StartsWith("Kado_P") || !int.TryParse(nm.Substring(6), out v)) return null;
        int n = Poly.Length, eIn = (v - 1 + n) % n, eOut = v % n; int secIn = -1, secOut = -1;
        foreach (var r in Runs)
        {
            if (r.lineS == null) continue;
            if (r.edge == eIn && r.s1 >= EdgeLen(eIn) - 0.01f) secIn = r.lineSec[r.lineSec.Length - 1];
            if (r.edge == eOut && r.s0 <= 0.01f) secOut = r.lineSec[0];
        }
        if (secIn < 0 && secOut < 0) return null;
        if (secIn < 0 || secOut < 0 || secIn == secOut) return "HL_" + Mathf.Max(secIn, secOut);
        float yIn = float.NaN, yOut = float.NaN;
        foreach (var r in Runs) if (r.lineSec != null) for (int k = 0; k < r.lineSec.Length; k++) { if (r.lineSec[k] == secIn) yIn = r.lineSeat[k]; if (r.lineSec[k] == secOut) yOut = r.lineSeat[k]; }
        return "HL_" + (yOut < yIn ? secOut : secIn);
    }

    // ---------------------------------------------------------------- 石垣基壇
    /// <summary>run → 法肩の控え c[m](区画の線から天端の前の縁まで・据えた基壇の実測 ── <see cref="PlaceIshigaki"/> が埋める)。</summary>
    static readonly Dictionary<string, float> _kidanC = new Dictionary<string, float>();
    /// <summary>角 P0 の段の小口の辺0 の走り s(<see cref="PlaceIshigaki"/> が隅の駒の実メッシュで測る・NaN = 段なし)── 辺0 の練塀の頭の突き付け先(cornerP0.hei)。</summary>
    static float _p0KoguchiS = float.NaN;
    /// <summary>辺 → その辺の基壇の控えの最大(基壇の無い run の外面に使う ── const.kidan.setback「法肩は一つの辺で一直線(辺の最大の c)」)。</summary>
    static readonly Dictionary<int, float> _kidanCe = new Dictionary<int, float>();
    /// <summary>辺 e・走り s の run の法肩の控え c(基壇の無い run は辺の最大・基壇の無い辺は 0 ── 法肩が無く外面は線から犬走り)。</summary>
    static float KidanC(int e, float s)
    {
        int best = -1; float bd = float.MaxValue;
        for (int k = 0; k < Runs.Length; k++)
        {
            var r = Runs[k]; if (r.edge != e) continue;
            float d = s < r.s0 ? r.s0 - s : (s > r.s1 ? s - r.s1 : 0f);
            if (d < bd) { bd = d; best = k; }
        }
        float c;
        if (best >= 0 && _kidanC.TryGetValue(Runs[best].name, out c)) return c;
        return _kidanCe.TryGetValue(e, out c) ? c : 0f;
    }
    /// <summary>囲い(練塀・長屋・門)の外面の、区画の線から内への離れ = 法肩の控え c + 犬走り(const.kidan.faces「+c+inubashiri」)。
    /// ⭐ 天端の線・芯線(const.heiLine)を当てた辺は、一続きで一つの控え d(<see cref="HeiLineFace"/>)を先に返す。</summary>
    static float FaceIn(int e, float s) { float d; if (_heiLineD != null && _heiLineD.TryGetValue(e, out d)) return d; return KidanC(e, s) + RunInu(e, s); }
    /// <summary>天端の線・芯線(const.heiLine)を当てた辺 → 外面の控え d(<see cref="FaceIn"/> が先に引く)。null = 未適用(従来の辺ごとの c + 犬走り)。</summary>
    static Dictionary<int, float> _heiLineD;
    /// <summary>この巡で天端の線の駒の足(両端)が線から外れた量の最大(NeribeiLineRun の測り ── 倍率で駒の勾配が g/f になる分)。</summary>
    static float _hlFootErr;
    /// <summary>練塀の隅の腕の最短[m](PlaceKado が KadoArms へ渡す neri の minArm と同じ)── 段の点を隅の駒の外へ寄せる幅の元。</summary>
    const float HL_KADO_MINARM = 0.2f;
    /// <summary>練塀の腰の外面から芯まで[m](EdoAssets.Own.Neribei「腰の下端 ±0.343」)── 天端の線の地盤を引く線にだけ使う(⛔ 据えには使わない ── 外面は実メッシュで寄せる)。</summary>
    const float HEI_CORE_IN = 0.343f;
    /// <summary>台の石垣(Ishigaki の群の据えた駒)の上向きの面 ── 練塀・隅の腰の有無を決める床(<see cref="EdoBuild.StoneBaseUnder"/>・const.heiLine.koshi)。</summary>
    static EdoBuild.PartTops HeiBaseStones() { var l = new List<GameObject>(); foreach (Transform c in Group("Ishigaki")) if (c.gameObject.activeInHierarchy) l.Add(c.gameObject); return new EdoBuild.PartTops(l); }
    /// <summary>辺 e の天端の線の練塀の足の外の縁が外面の線(<see cref="FaceIn"/>)より外へ出る量[m]の最大 ── 据えた駒の実メッシュで測る(腰あり 0.137・腰なし 0)。
    /// 犬走りの面と天端の土の下げ(Stage3d)が「腰の外の縁の一升奥まで」を引く幅。練塀の駒が無い辺(長屋・門)は <paramref name="none"/>(前の巡までの腰の出 0.14)。</summary>
    static float HeiFootOut(int e, float none = 0.14f)
    {
        float best = float.NaN; Vector2 a = EdgePt(e, 0f), o = OutNormal(e); float tgt = -FaceIn(e, 0.5f * EdgeLen(e));
        foreach (var r in Runs)
        {
            if (r.edge != e || !r.Dobei) continue;
            foreach (Transform c in Group("Kakoi"))
            {
                if (!c.gameObject.activeInHierarchy || !c.name.StartsWith(r.name + "_")) continue;
                float yb = EdoBuild.RB(c.gameObject).min.y, m0 = EdoBuild.FaceOut(c.gameObject, a, o, yb - 0.01f, yb + 0.10f);
                if (!float.IsNaN(m0)) best = float.IsNaN(best) ? Mathf.Max(0f, m0 - tgt) : Mathf.Max(best, m0 - tgt);
            }
        }
        return float.IsNaN(best) ? none : best;
    }
    static void ClearHeiLine()
    {
        _heiLineD = null; _hlEdgeSet = null; var rs = Runs;
        for (int k = 0; k < rs.Length; k++) { rs[k].lineS = null; rs[k].lineSeat = null; rs[k].lineSec = null; rs[k].lineGrade = null; rs[k].lineStep = null; }
        _hlRanges.Clear(); _hlProfiles.Clear(); _hlSteps.Clear(); _hlBase.Clear();
    }
    /// <summary>天端の線・芯線を当てる辺の範囲(const.heiLine.trial の「辺 a〜b・c〜d …」── 案1 で外周全体 辺1〜11・19〜24・28〜38)。e0 &gt; e1 の範囲は 0 を跨ぐ。</summary>
    static readonly List<Vector2Int> _hlRanges = new List<Vector2Int>();
    /// <summary>範囲ごとの天端の線(<see cref="HeiLineTenba"/> が指図の値から解いた物)と、段の点(辺・走り)。</summary>
    static readonly List<EdoBuild.HeiProfile> _hlProfiles = new List<EdoBuild.HeiProfile>();
    static readonly List<EdoBuild.HeiStep> _hlSteps = new List<EdoBuild.HeiStep>();
    /// <summary>const.heiLine.trial の辺の範囲を読む(「辺1〜11・19〜24・28〜38」)。読めなければ空。</summary>
    static List<Vector2Int> HeiLineRangesFromSashizu()
    {
        var res = new List<Vector2Int>(); var hl = O(Get(O(Get(D, "const")), "heiLine")); if (hl == null) return res;
        string tr = S(Get(hl, "trial")) ?? ""; int at = tr.IndexOf("辺"); if (at < 0) return res;
        int n = Poly.Length;
        foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(tr.Substring(at), @"(\d+)\s*〜\s*(\d+)"))
        { int a = int.Parse(m.Groups[1].Value), b = int.Parse(m.Groups[2].Value); if (b < a) b += n; res.Add(new Vector2Int(a, b)); }
        return res;
    }
    static HashSet<int> _hlEdgeSet; static object _hlEdgeSetOf;
    /// <summary>天端の線を当てる辺(指図から毎回読む ── domain reload で Runs の線が消えた後の 3d でも、天端の線の駒を床へ動かさない・後合わせの規則を通さない)。</summary>
    static HashSet<int> HeiLineEdgeSet()
    {
        if (_hlEdgeSet != null && ReferenceEquals(_hlEdgeSetOf, D)) return _hlEdgeSet;
        var set = new HashSet<int>(); int n = Poly.Length;
        foreach (var r in HeiLineRangesFromSashizu()) for (int e = r.x; e <= r.y; e++) set.Add(e % n);
        _hlEdgeSet = set; _hlEdgeSetOf = D; return set;
    }
    /// <summary>**外周の練塀の芯線を一続きに決める**(指図 const.heiLine・施主裁定 2026-10-12 案A/案1)── 欄を EdoBuild へ渡すだけ(規則21):
    /// 範囲 = heiLine.trial の「辺 a〜b・…」・大きな隅 = heiLine.bigCornerDeg・c = 据えた基壇の実測(<see cref="_kidanCe"/> ⇒ <see cref="PlaceIshigaki"/> の後)・犬走り = const.inubashiri
    /// ⇒ <see cref="EdoBuild.HeiStretchSetback"/> が一続きの d を <see cref="_heiLineD"/> へ(<see cref="FaceIn"/> が先に引く ⇒ 隅・長屋の妻への突き込み・練塀が同じ線を読む)。
    /// ⟶ 報告の行(読めなければ ★ で従来のまま)。当たる先: 岡部の外周の練塀の全辺(案1)── 他邸は未適用(trial の範囲を書けば同じ道で建つ)。</summary>
    static string HeiLineFace()
    {
        _hlRanges.Clear();
        var hl = O(Get(O(D["const"]), "heiLine")); if (hl == null) return null;
        var rg = HeiLineRangesFromSashizu();
        if (rg.Count == 0) return "★ const.heiLine.trial の辺の範囲が読めない ── 天端の線・芯線を当てない(従来の辺ごと)";
        if (!Has(hl, "bigCornerDeg")) return "★ const.heiLine.bigCornerDeg が無い ── 天端の線・芯線を当てない(従来の辺ごと)";
        int n = Poly.Length; float big = F(hl["bigCornerDeg"]);
        Func<int, float> cOf = e => { float c; return _kidanCe.TryGetValue(e % n, out c) ? c : 0f; };
        //   ⭐ const.heiLine.d「塀の一続き(長屋・門・塀の自由端から、次の…)で控え d を一つ…大きな隅でも d を替えない」(第122巡)── 一続きは塀が頂点で切れない所:
        //   頂点 v の両脇の辺に練塀の run が頂点まで続き、門・小門がその辺に無い。旧い文(大きな隅で割る)なら bigCornerDeg で割る
        bool byStretch = (S(Get(hl, "d")) ?? "").Contains("塀の一続き");
        var gateE = new HashSet<int>(); { var g0 = O(Get(D, "gate")); if (g0 != null && Has(g0, "edge")) gateE.Add((int)F(g0["edge"])); foreach (var o in A(Get(D, "komon")) ?? new List<object>()) { var k0 = O(o); if (k0 != null && Has(k0, "edge")) gateE.Add((int)F(k0["edge"])); } }
        Func<int, bool> wallBreak = v =>
        {
            int eI = ((v - 1) % n + n) % n, eO = ((v % n) + n) % n; bool inEnd = false, outStart = false;
            foreach (var rr in Runs) { if (!rr.Dobei) continue; if (rr.edge == eI && rr.s1 >= EdgeLen(eI) - 0.05f) inEnd = true; if (rr.edge == eO && rr.s0 <= 0.05f) outStart = true; }
            return !(inEnd && outStart) || gateE.Contains(eI) || gateE.Contains(eO);
        };
        _heiLineD = new Dictionary<int, float>(); var sb = new System.Text.StringBuilder("芯線(const.heiLine・施主裁定 2026-10-12 案A/案1" + (byStretch ? "・d は塀の一続きで一つ(第122巡)" : "") + "):");
        foreach (var r in rg)
        {
            string n1; var d = byStretch ? EdoBuild.HeiStretchSetback(Poly, r.x, r.y, wallBreak, cOf, INUBASHIRI, out n1) : EdoBuild.HeiStretchSetback(Poly, r.x, r.y, big, cOf, INUBASHIRI, out n1);
            for (int e = r.x; e <= r.y; e++) _heiLineD[e % n] = d[e - r.x];
            _hlRanges.Add(r); sb.Append("\n  辺" + (r.x % n) + "〜" + (r.y % n) + ": " + n1);
        }
        return sb.ToString();
    }
    /// <summary>**天端の線の決めた座と段を指図から読む**(const.heiLine.tenba の SW・SE・N の文 ── 普請方の設計を普請奉行が採った値・施主裁定 2026-10-12 案1)。
    /// 読み: 「辺a s<s> <y>」= 座 / 「段k h<h> … at 辺a s<s>,<s>,辺b s<s>」= 段 / 「辺a s<s>〜辺b 終 <y> 平ら」/「辺a <y0>→<y1>」= 辺の始めと終わり /
    /// SE の欄「e<a>_<b>: y 平ら」「e<a>: y0→y1」「e<a>: y0→ 段k h at s…、s<s> で <y> → P<v> まで平ら」「e<a>_<b>: y0(…)→y1」/
    /// N「段k h: 辺a s…/辺b s…」「辺の始まりの座 e<a> y,…,終 y」。坂なりの上限は rule の「≤1/n」。読めない・数が合わない所は ★(建てない)。</summary>
    static bool ReadTenba(List<EdoBuild.HeiKnot> knots, List<EdoBuild.HeiStep> steps, out float maxGrade, List<string> notes)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; maxGrade = 0.125f; bool ok = true;
        var tb = O(Get(O(Get(O(Get(D, "const")), "heiLine")), "tenba")); if (tb == null) { notes.Add("★ const.heiLine.tenba が無い"); return false; }
        var mR = System.Text.RegularExpressions.Regex.Match(S(Get(tb, "rule")) ?? "", @"≤\s*1\s*/\s*(\d+)"); if (mR.Success) maxGrade = 1f / float.Parse(mR.Groups[1].Value, inv); else notes.Add("⚠ tenba.rule の坂なりの上限(≤1/n)が読めない ── 1/8");
        Func<string, float> Fl = t => float.Parse(t, inv);
        System.Action<string, string> stepList = (txt, hs) =>
        {   // 「辺21 s5.50,7.31,9.13,辺22 s0.90,2.72」/「s0.36,2.18」(辺は前の値)
            float h = Fl(hs); int curE = -1;
            foreach (var tok0 in txt.Split(new[] { ',', '、' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string tok = System.Text.RegularExpressions.Regex.Replace(tok0, @"[(（].*$", "").Trim();
                var mE = System.Text.RegularExpressions.Regex.Match(tok, @"辺\s*(\d+)\s*s\s*([0-9.]+)"); var mS = System.Text.RegularExpressions.Regex.Match(tok, @"^s?\s*([0-9.]+)$");
                if (mE.Success) { curE = int.Parse(mE.Groups[1].Value); steps.Add(new EdoBuild.HeiStep { edge = curE, s = Fl(mE.Groups[2].Value), h = h }); }
                else if (mS.Success && curE >= 0) steps.Add(new EdoBuild.HeiStep { edge = curE, s = Fl(mS.Groups[1].Value), h = h });
            }
        };
        System.Action<int, string, string> wantSteps = (before, kind, cnt) => { int got = steps.Count - before; if (got != int.Parse(cnt)) { notes.Add("★ tenba." + kind + " の段の数 " + cnt + " ≠ 読めた " + got); ok = false; } };
        // ---- SW(文)
        string sw = S(Get(tb, "SW"));
        if (sw != null)
        {
            string body = sw.Split('。')[0];
            foreach (var ch in body.Split('/'))
            {
                var mStep = System.Text.RegularExpressions.Regex.Match(ch, @"段\s*(\d+)\s*h\s*([0-9.]+).*?at\s*(.+)$");
                if (mStep.Success) { int b0 = steps.Count; stepList(mStep.Groups[3].Value, mStep.Groups[2].Value); wantSteps(b0, "SW", mStep.Groups[1].Value); continue; }
                var mFl = System.Text.RegularExpressions.Regex.Match(ch, @"辺\s*(\d+)\s*s\s*([0-9.]+)\s*〜\s*辺\s*(\d+)\s*終\s*([0-9.]+)\s*平ら");
                if (mFl.Success) { float y = Fl(mFl.Groups[4].Value); knots.Add(new EdoBuild.HeiKnot { edge = int.Parse(mFl.Groups[1].Value), s = Fl(mFl.Groups[2].Value), y = y }); knots.Add(new EdoBuild.HeiKnot { edge = int.Parse(mFl.Groups[3].Value), s = -1f, y = y }); continue; }
                var mE2 = System.Text.RegularExpressions.Regex.Match(ch, @"^\s*辺\s*(\d+)\s+([0-9.]+)\s*→\s*([0-9.]+)");
                if (mE2.Success) { int e = int.Parse(mE2.Groups[1].Value); knots.Add(new EdoBuild.HeiKnot { edge = e, s = 0f, y = Fl(mE2.Groups[2].Value) }); knots.Add(new EdoBuild.HeiKnot { edge = e, s = -1f, y = Fl(mE2.Groups[3].Value) }); continue; }
                int nk = 0;
                foreach (System.Text.RegularExpressions.Match mk in System.Text.RegularExpressions.Regex.Matches(ch, @"辺\s*(\d+)\s*s\s*([0-9.]+)\s+([0-9]+\.[0-9]+)"))
                { knots.Add(new EdoBuild.HeiKnot { edge = int.Parse(mk.Groups[1].Value), s = Fl(mk.Groups[2].Value), y = Fl(mk.Groups[3].Value) }); nk++; }
                if (nk == 0) { notes.Add("★ tenba.SW の「" + ch + "」が読めない"); ok = false; }
            }
        }
        else { notes.Add("★ tenba.SW が無い"); ok = false; }
        // ---- SE(欄は JSON の文字列)
        string se = S(Get(tb, "SE"));
        if (se != null)
        {
            foreach (System.Text.RegularExpressions.Match mk in System.Text.RegularExpressions.Regex.Matches(se, "\"e(\\d+)(?:_(\\d+))?\"\\s*:\\s*\"([^\"]*)\""))
            {
                int ea = int.Parse(mk.Groups[1].Value), eb = mk.Groups[2].Success ? int.Parse(mk.Groups[2].Value) : ea; string v = mk.Groups[3].Value;
                var mFlat = System.Text.RegularExpressions.Regex.Match(v, @"^\s*([0-9.]+)\s*平ら");
                var mStep = System.Text.RegularExpressions.Regex.Match(v, @"^\s*([0-9.]+)\s*→\s*段\s*(\d+)\s*h\s*([0-9.]+)\s*at\s*([s0-9.,\s]+)");
                var mTwo = System.Text.RegularExpressions.Regex.Match(v, @"^\s*([0-9.]+)[^→]*→\s*([0-9.]+)");
                if (mFlat.Success) { float y = Fl(mFlat.Groups[1].Value); knots.Add(new EdoBuild.HeiKnot { edge = ea, s = 0f, y = y }); knots.Add(new EdoBuild.HeiKnot { edge = eb, s = -1f, y = y }); }
                else if (mStep.Success)
                {
                    knots.Add(new EdoBuild.HeiKnot { edge = ea, s = 0f, y = Fl(mStep.Groups[1].Value) });
                    int b0 = steps.Count; stepList("辺" + ea + " " + mStep.Groups[4].Value.Trim(), mStep.Groups[3].Value); wantSteps(b0, "SE.e" + ea, mStep.Groups[2].Value);
                    var mEnd = System.Text.RegularExpressions.Regex.Match(v, @"s\s*([0-9.]+)\s*で\s*([0-9.]+)\s*→\s*P\s*(\d+)\s*まで平ら");
                    if (mEnd.Success) { float y = Fl(mEnd.Groups[2].Value); knots.Add(new EdoBuild.HeiKnot { edge = ea, s = Fl(mEnd.Groups[1].Value), y = y }); knots.Add(new EdoBuild.HeiKnot { edge = int.Parse(mEnd.Groups[3].Value) - 1, s = -1f, y = y }); }
                    else { notes.Add("★ tenba.SE.e" + ea + " の終わりの座(s… で y → P… まで平ら)が読めない"); ok = false; }
                }
                else if (mTwo.Success) { knots.Add(new EdoBuild.HeiKnot { edge = ea, s = 0f, y = Fl(mTwo.Groups[1].Value) }); knots.Add(new EdoBuild.HeiKnot { edge = eb, s = -1f, y = Fl(mTwo.Groups[2].Value) }); }
                else { notes.Add("★ tenba.SE.e" + mk.Groups[1].Value + " が読めない: " + v); ok = false; }
            }
        }
        else { notes.Add("★ tenba.SE が無い"); ok = false; }
        // ---- N(文)
        string nn = S(Get(tb, "N"));
        if (nn != null)
        {
            var parts = nn.Split('。');
            var mStep = System.Text.RegularExpressions.Regex.Match(parts[0], @"段\s*(\d+)\s*h\s*([0-9.]+)\s*[:：]\s*(.+)$");
            if (mStep.Success)
            {
                int b0 = steps.Count;
                foreach (var ch in mStep.Groups[3].Value.Split('/')) stepList(ch, mStep.Groups[2].Value);
                wantSteps(b0, "N", mStep.Groups[1].Value);
            }
            else { notes.Add("★ tenba.N の段が読めない"); ok = false; }
            string seats = null; foreach (var p in parts) if (p.Contains("辺の始まりの座")) seats = p;
            if (seats != null)
            {
                int lastE = -1;
                foreach (System.Text.RegularExpressions.Match mk in System.Text.RegularExpressions.Regex.Matches(seats, @"e\s*(\d+)\s+([0-9.]+)"))
                { lastE = int.Parse(mk.Groups[1].Value); knots.Add(new EdoBuild.HeiKnot { edge = lastE, s = 0f, y = Fl(mk.Groups[2].Value) }); }
                var mEnd = System.Text.RegularExpressions.Regex.Match(seats, @"終\s*([0-9.]+)");
                if (mEnd.Success && lastE >= 0) knots.Add(new EdoBuild.HeiKnot { edge = lastE, s = -1f, y = Fl(mEnd.Groups[1].Value) });
                else { notes.Add("★ tenba.N の終わりの座が読めない"); ok = false; }
            }
            else { notes.Add("★ tenba.N の辺の始まりの座が読めない"); ok = false; }
        }
        else { notes.Add("★ tenba.N が無い"); ok = false; }
        return ok;
    }
    /// <summary>**天端の線を指図の値で一本に決める**(const.heiLine.tenba・施主裁定 2026-10-12 案1)── 範囲ごとに <see cref="EdoBuild.HeiTenbaProfile"/> へ芯線の控え d・決めた座・段を渡し、
    /// <see cref="EdoBuild.HeiProfileRows"/> の区間を run の lineS/lineSeat/lineGrade/lineSec/lineStep へ。基壇(SeatBreaks/SeatAt)・練塀(<see cref="EdoBuild.NeribeiLineRun"/>)・
    /// 隅(坂の隅の駒・<see cref="SeatHeiLineKado"/>)が同じ線を読む。⛔ 棟梁は段の点を選ばない(stepAt「tenba の値に従う」)。勾配が上限を越える・読めない範囲は線を当てず ★(建てて返さない)。
    /// ⚠ 芯線(<see cref="HeiLineFace"/>)の後・隅を据える前に呼ぶ(坂の隅の駒の勾配と、段の面に掛かる腕の詰めを隅が読む)。</summary>
    static string HeiLineTenba()
    {
        _hlProfiles.Clear(); _hlSteps.Clear();
        if (_heiLineD == null || _hlRanges.Count == 0) return null;
        var inv = System.Globalization.CultureInfo.InvariantCulture; var notes = new List<string>();
        var knots = new List<EdoBuild.HeiKnot>(); var steps = new List<EdoBuild.HeiStep>(); float gMax;
        bool okR = ReadTenba(knots, steps, out gMax, notes);
        var sb = new System.Text.StringBuilder("天端の線(const.heiLine.tenba・施主裁定 2026-10-12 案1 ── 指図の値): 決めた座 " + knots.Count + "・段 " + steps.Count + "・坂なりの上限 1/" + (1f / gMax).ToString("0", inv) + (okR ? "" : " ★"));
        foreach (var t in notes) sb.Append("\n  " + t);
        int n = Poly.Length; var rs = Runs; int nr = 0;
        foreach (var r in _hlRanges)
        {
            int m = r.y - r.x + 1; var d = new float[m]; for (int k = 0; k < m; k++) d[k] = _heiLineD[(r.x + k) % n];
            var kk = knots.FindAll(q => { int e = ((q.edge % n) + n) % n; for (int x = r.x; x <= r.y; x++) if (x % n == e) return true; return false; });
            var ss = steps.FindAll(q => { int e = ((q.edge % n) + n) % n; for (int x = r.x; x <= r.y; x++) if (x % n == e) return true; return false; });
            //   段が隅の駒の中に入る所は、書かれた辺の側の「腕の最短(KadoArms の minArm 0.2)+ 棟止めの端の柱」の所へ寄せる ⚠(第121巡: 辺34 s13.45 が P35 の折れ点の 0.14 先)
            var kadoV = new HashSet<int>(); foreach (var o in A(Get(IMPL, "corners")) ?? new List<object>()) { var cc = O(o); if (cc != null && S(Get(cc, "part")) == "Dobei") kadoV.Add((((int)F(cc["vertex"])) % n + n) % n); }
            float post, tbody; EdoBuild.NeribeiTomeGauge(out post, out tbody);
            string nt; var pf = EdoBuild.HeiTenbaProfile(Poly, r.x, r.y, d, HEI_CORE_IN, kk, ss, gMax, HL_KADO_MINARM + post, v => kadoV.Contains(v), out nt);
            sb.Append("\n  " + nt);
            if (!pf.ok || !okR) { sb.Append("\n  ★ 辺" + (r.x % n) + "〜" + (r.y % n) + " は天端の線を当てない(指図の値が解けない ── 普請奉行へ返す)"); continue; }
            //   ⭐ 座 ≥ 外の地盤(const.heiLine.seatOverGround【硬】・第122巡)── 座が外(区画の外)の地盤 + m より低い所があれば、一続きの線を平行に上げる
            //   (決めた座を全部 +δ ── 段の点の位置・段の高さは変えない)。外の地盤 = base_dem の線上と線から外 0.5 の高い方(規則13)。
            {
                string sog = S(Get(O(Get(O(Get(D, "const")), "heiLine")), "seatOverGround"));
                var mM = System.Text.RegularExpressions.Regex.Match(sog ?? "", @"外の地盤\s*\+\s*([0-9.]+)\s*以上");
                if (sog != null && !mM.Success) sb.Append("\n  ★ const.heiLine.seatOverGround の余裕(外の地盤 +m 以上)が読めない ── 上げない");
                if (mM.Success)
                {
                    float marg = float.Parse(mM.Groups[1].Value, inv); var bdS = EdoBuild.BaseDem();
                    float worst = float.NegativeInfinity; string wAt = "-";
                    foreach (var sc in EdoBuild.HeiProfileRows(pf, Poly))
                    {
                        bool hasRun = false; string rn = null; foreach (var rr in rs) if (rr.Dobei && rr.edge == sc.edge) { hasRun = true; rn = rr.name; }
                        if (!hasRun) continue;
                        Vector2 o2 = OutNormal(sc.edge);
                        for (float sv = sc.s0 + 0.05f; sv < sc.s1 - 0.04f; sv += 0.25f)
                        {
                            Vector2 p0 = EdgePt(sc.edge, sv); float og = Mathf.Max(bdS(p0.x, p0.y), bdS(p0.x + o2.x * 0.5f, p0.y + o2.y * 0.5f)); if (float.IsNaN(og)) continue;
                            float def = og + marg - (sc.seat + sc.grade * (sv - sc.s0));
                            if (def > worst) { worst = def; wAt = rn + " s" + sv.ToString("F2", inv) + "(座 " + (sc.seat + sc.grade * (sv - sc.s0)).ToString("F3", inv) + "・外 " + og.ToString("F3", inv) + ")"; }
                        }
                    }
                    if (worst > 0.0005f)
                    {
                        float up = Mathf.Ceil(worst * 100f - 1e-3f) / 100f;
                        var kk2 = new List<EdoBuild.HeiKnot>(); foreach (var q in kk) kk2.Add(new EdoBuild.HeiKnot { edge = q.edge, s = q.s, y = q.y + up });
                        string nt2; var pf2 = EdoBuild.HeiTenbaProfile(Poly, r.x, r.y, d, HEI_CORE_IN, kk2, ss, gMax, HL_KADO_MINARM + post, v => kadoV.Contains(v), out nt2);
                        sb.Append("\n  ⭐ 座 ≥ 外の地盤 + " + marg.ToString("F2", inv) + "(seatOverGround【硬】): 辺" + (r.x % n) + "〜" + (r.y % n) + " の不足 最大 " + worst.ToString("F3", inv) + " @" + wAt + " ⇒ 一続きの線を +" + up.ToString("F2", inv) + " 平行に上げた(段の点・段の高さは据え置き)\n  " + nt2);
                        if (!pf2.ok) { sb.Append("\n  ★ 上げた線が解けない ── 上げずに据える"); }
                        else pf = pf2;
                    }
                    else sb.Append("\n  座 ≥ 外の地盤 + " + marg.ToString("F2", inv) + ": 辺" + (r.x % n) + "〜" + (r.y % n) + " は不足なし(余裕の最小 " + (-worst).ToString("F3", inv) + " @" + wAt + ")");
                }
            }
            _hlProfiles.Add(pf); _hlSteps.AddRange(pf.steps);
            var rows = EdoBuild.HeiProfileRows(pf, Poly);
            for (int k = 0; k < rs.Length; k++)
            {
                if (!rs[k].Dobei || !_heiLineD.ContainsKey(rs[k].edge)) continue;
                var ls = new List<float>(); var ly = new List<float>(); var lg = new List<float>(); var lc = new List<int>(); var lst = new List<bool>();
                foreach (var sc in rows) if (sc.edge == rs[k].edge) { if (ls.Count == 0) { ls.Add(sc.s0); lst.Add(sc.stepAt0); } ls.Add(sc.s1); ly.Add(sc.seat); lg.Add(sc.grade); lc.Add(sc.sec); }
                if (ly.Count == 0) continue;
                // 切れ目 k(k ≥ 1)が段か = 次の区間の始めが段
                foreach (var sc in rows) if (sc.edge == rs[k].edge) { int j = ls.FindIndex(x => Mathf.Abs(x - sc.s0) < 1e-4f); if (j > 0) { while (lst.Count <= j) lst.Add(false); lst[j] = sc.stepAt0; } }
                while (lst.Count < ls.Count) lst.Add(false);
                rs[k].lineS = ls.ToArray(); rs[k].lineSeat = ly.ToArray(); rs[k].lineGrade = lg.ToArray(); rs[k].lineSec = lc.ToArray(); rs[k].lineStep = lst.ToArray(); rs[k].hasStep = false; nr++;
                var tx = new System.Text.StringBuilder();
                for (int q = 0; q < ly.Count; q++) tx.Append((q > 0 ? (lst[q] ? " ┃段┃ " : " | ") : "") + "s " + ls[q].ToString("F2", inv) + "〜" + ls[q + 1].ToString("F2", inv) + " " + ly[q].ToString("F3", inv) + (Mathf.Abs(lg[q]) > 5e-5f ? " " + (lg[q] * 100f).ToString("+0.00;-0.00", inv) + "%" : " 平ら"));
                sb.Append("\n    " + rs[k].name + "(辺" + rs[k].edge + "): " + tx);
            }
        }
        return sb.ToString().Replace("天端の線(const", "天端の線 run " + nr + "(const");
    }
    /// <summary>天端の線の内の帯の設計の全文(普請方 2026-10-12・const.heiLine.tenba の「切盛は下の値」の元 ── 帯の幅・座からの下げ・摺り付けの勾配)。</summary>
    public const string TenbaNotesRel = "docs/Sashizu/okabe_notes/heiline_tenba_fushin_2026-10-12.json";
    /// <summary>**塀の内の帯を坂なりの線に揃える**(const.heiLine.tenba.band「塀の内の帯を均して地盤を坂なりの線に揃える・区画の外は触らない【硬】」・設計の全文 method
    /// 「帯=塀の内面から b を座−δ、先は盛 1:m/切 1:k」・water「平場 y は帯を 1/n で P v へ落とし」・施主裁定 2026-10-12 案1・第121巡)── 欄を EdoBuild へ渡すだけ:
    /// 天端の線の run の練塀と隅の実メッシュで辺ごとの内面を測り(EdoBuild.MeasureFootLines)、帯 [0, b] を 座 − δ(平場は P v へ 1/n で下る面 ── 帯は座 − δ より下げない)に、
    /// その先を盛 1:m・切 1:k で今の地面へ(EdoBuild.WriteFootBand)。heiFootSpec の辺(角 P0 の南・辺4・5 の溝の床)は 2b の帯に任せる。
    /// 区画の線から ClipIn() の外・棟・附属屋・門・段の土留め・坂・溝の外接の中は触らない。⟶ 報告の行。当たる先: 天端の線の上の練塀(岡部の外周)の内の地面。</summary>
    static string HeiLineBand()
    {
        if (_hlProfiles.Count == 0) return "  内の帯(const.heiLine.tenba.band): 天端の線が無い ── 焼かない";
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        string full = null; try { full = System.IO.File.ReadAllText(TenbaNotesRel); } catch (Exception) { }
        var mB = System.Text.RegularExpressions.Regex.Match(full ?? "", @"帯=塀の内面から\s*([0-9.]+)\s*を座\s*[−\-]\s*([0-9.]+)\s*、\s*先は盛\s*1\s*:\s*([0-9.]+)\s*/\s*切\s*1\s*:\s*([0-9.]+)");
        if (!mB.Success) return "  ★ 内の帯: 設計の全文(" + TenbaNotesRel + " の method)の帯の値が読めない ── 焼かない";
        float bw = float.Parse(mB.Groups[1].Value, inv), dn = float.Parse(mB.Groups[2].Value, inv), nF = float.Parse(mB.Groups[3].Value, inv), nC = float.Parse(mB.Groups[4].Value, inv);
        var tb = O(Get(O(Get(O(Get(D, "const")), "heiLine")), "tenba"));
        var mW = System.Text.RegularExpressions.Regex.Match(S(Get(tb, "water")) ?? "", @"平場\s*([0-9.]+)\s*は帯を\s*1\s*/\s*([0-9.]+)\s*で\s*P\s*(\d+)\s*へ落とし");
        float yW = mW.Success ? float.Parse(mW.Groups[1].Value, inv) : float.NaN, gW = mW.Success ? 1f / float.Parse(mW.Groups[2].Value, inv) : 0f; int vW = mW.Success ? int.Parse(mW.Groups[3].Value) : -1;
        int n = Poly.Length;
        // heiFootSpec の辺(2b の帯)
        var skipE = new HashSet<int>(); var spH = O(Get(O(Get(O(Get(D, "grading")), "seRoji")), "heiFootSpec"));
        foreach (var o in A(Get(spH, "runs")) ?? new List<object>()) { int k = System.Array.FindIndex(Runs, x => x.name == S(o)); if (k >= 0) skipE.Add(Runs[k].edge); }
        var mE45 = System.Text.RegularExpressions.Regex.Match(S(Get(O(Get(spH, "floor45")), "note")) ?? "", @"辺\s*([0-9・,、]+)");
        if (mE45.Success) foreach (var es in mE45.Groups[1].Value.Split(new[] { '・', ',', '、' }, StringSplitOptions.RemoveEmptyEntries)) skipE.Add(int.Parse(es.Trim()));
        var lines = new List<EdoBuild.FootLine>(); var pcs = new List<GameObject>(); var kak = Group("Kakoi"); var edges = new HashSet<int>();
        foreach (var r0 in Runs)
        {
            var r = r0; if (!OnHeiLine(r) || skipE.Contains(r.edge)) continue; var pf = ProfileOfEdge(r.edge); if (pf == null) continue;
            edges.Add(r.edge); Vector2 ea = EdgePt(r.edge, 0f); int e = r.edge;
            var L = new EdoBuild.FootLine { name = "辺" + e, a = ea, ax = (EdgePt(e, 1f) - ea).normalized, inw = -OutNormal(e), len = EdgeLen(e) };
            L.seatAt = sv => r.SeatAt(Mathf.Clamp(sv, 0f, EdgeLen(e)));
            L.yAt = sv =>
            {
                float sc = Mathf.Clamp(sv, 0f, EdgeLen(e)); float y = r.SeatAt(sc) - dn;
                int k = r.LineIndexAt(sc); bool flat = r.lineGrade == null || Mathf.Abs(r.lineGrade[k]) < 5e-5f;
                if (mW.Success && flat && Mathf.Abs(r.SeatAt(sc) - yW) < 0.005f && pf.tStart.ContainsKey(vW % n)) y = Mathf.Max(y, yW - dn + gW * Mathf.Abs(pf.tStart[vW % n] - pf.TOf(e, sc)));
                return y;
            };
            lines.Add(L);
            foreach (Transform c in kak) if (c.gameObject.activeInHierarchy && c.name.StartsWith(r.name + "_")) pcs.Add(c.gameObject);
        }
        foreach (Transform c in kak) { int v; if (c.gameObject.activeInHierarchy && c.name.StartsWith("Kado_P") && int.TryParse(c.name.Substring(6), out v) && (edges.Contains(v % n) || edges.Contains((v - 1 + n) % n)) && OnHeiLineVertex(v)) pcs.Add(c.gameObject); }
        EdoBuild.MeasureFootLines(lines, pcs);
        foreach (var L in lines) { if (L.nPts == 0) continue; L.sLo = Mathf.Max(L.sLo, 0f); L.sHi = Mathf.Min(L.sHi, L.len); }
        // 触らない所: 棟・附属屋・門・段の土留め・坂・溝(据えた駒の外接 + 0.3 ── 升の索引)
        var keep = new Dictionary<long, List<Bounds>>(); int nKeep = 0;
        var root = GameObject.Find(GN);
        foreach (var gn in new[] { "Buildings", "Fuzoku", "Mon", "Dan", "DanKaki", "Saka", "GateSteps", "KomonFumi" })
        {
            var g = root == null ? null : root.transform.Find(gn); if (g == null) continue;
            foreach (var mr in g.GetComponentsInChildren<MeshRenderer>())
            {
                var b = mr.bounds; b.Expand(new Vector3(0.6f, 0f, 0.6f)); nKeep++;
                for (int ix = Mathf.FloorToInt(b.min.x / 2f); ix <= Mathf.FloorToInt(b.max.x / 2f); ix++) for (int iz = Mathf.FloorToInt(b.min.z / 2f); iz <= Mathf.FloorToInt(b.max.z / 2f); iz++)
                { long key = ((long)ix << 32) ^ (uint)iz; List<Bounds> l; if (!keep.TryGetValue(key, out l)) keep[key] = l = new List<Bounds>(); l.Add(b); }
            }
        }
        foreach (var gm in MizoGroups) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) { var b = EdoBuild.RB(c.gameObject); b.Expand(new Vector3(0.6f, 0f, 0.6f)); nKeep++; for (int ix = Mathf.FloorToInt(b.min.x / 2f); ix <= Mathf.FloorToInt(b.max.x / 2f); ix++) for (int iz = Mathf.FloorToInt(b.min.z / 2f); iz <= Mathf.FloorToInt(b.max.z / 2f); iz++) { long key = ((long)ix << 32) ^ (uint)iz; List<Bounds> l; if (!keep.TryGetValue(key, out l)) keep[key] = l = new List<Bounds>(); l.Add(b); } }
        int nOut = 0, nHeld = 0; var PP = Poly; float clip = ClipIn();
        Func<Vector2, bool> allow = q =>
        {
            if (!EdoGeom.PIP(PP, q) || EdoBuild.EdgeDistPublic(PP, q) < clip) { nOut++; return false; }
            List<Bounds> l; long key = ((long)Mathf.FloorToInt(q.x / 2f) << 32) ^ (uint)Mathf.FloorToInt(q.y / 2f);
            if (keep.TryGetValue(key, out l)) foreach (var b in l) if (q.x >= b.min.x && q.x <= b.max.x && q.y >= b.min.z && q.y <= b.max.z) { nHeld++; return false; }
            return true;
        };
        float reach = 3.0f;
        int nw = EdoBuild.WriteFootBand(lines, 0f, bw, nF, reach, allow, nC);
        if (nw > 0) EdoBuild.T().terrainData.SyncHeightmap();
        var sb = new System.Text.StringBuilder("  内の帯(const.heiLine.tenba.band・設計の全文: 内面から " + bw.ToString("F2", inv) + " を座 −" + dn.ToString("F2", inv) + "・先は盛 1:" + nF.ToString("0.#", inv) + "/切 1:" + nC.ToString("0.#", inv)
            + (mW.Success ? "・平場 " + yW.ToString("F2", inv) + " は P" + vW + " へ 1/" + (1f / gW).ToString("0", inv) + " で下る面(帯は座 −" + dn.ToString("F2", inv) + " より下げない)" : "・⚠ tenba.water が読めない") + "・heiFootSpec の辺 " + string.Join("・", new List<int>(skipE).ConvertAll(x => x.ToString()).ToArray()) + " は 2b): 節点 " + nw
            + "・区画の外/線際で触らず " + nOut + "・棟・門・土留め・溝の外接で触らず " + nHeld + "(外接 " + nKeep + ")");
        foreach (var L in lines) sb.Append("\n    " + L.name + ": 内面 線から " + (L.nPts > 0 ? L.dIn.ToString("F3", inv) : "-") + "・帯 " + L.nBand + "・摺り付け " + L.nTap + "・盛り最大 " + L.up.ToString("F2", inv) + "・切り最大 " + L.dn.ToString("F2", inv));
        return sb.ToString();
    }
    /// <summary>天端の線の run → (台の倍率 s, 台を置く区間)── <see cref="HeiLineBaseFromTenba"/> が解く(<see cref="PlaceIshigaki"/> が算出物 base[] より先に引く)。</summary>
    static readonly Dictionary<string, KeyValuePair<float, List<Vector2>>> _hlBase = new Dictionary<string, KeyValuePair<float, List<Vector2>>>();
    /// <summary>**天端の線の run の台の石垣の区間と倍率を、天端の線の座から解く**(runs[].sFrom「天端 − 法尻の地形(棟梁が実地形から導く)」・const.baseMin / baseUnit・第121巡)。
    /// 算出物 base[](segs・s)は runs の旧い座で焼いた物 ⇒ 天端の線(案1)では見付が足りず台が浮き・台の無い辺に塀が土の上で立った。読み(焼き手 impl_okabe.bake_base と同じ):
    /// 露出 ex(s) = 座 − 区画の外の地盤の最小(道に面する辺は線から 2.0〜5.0 を 0.5 ごと・ほかは 1.0 ── 外の地盤は base_dem と道の線際の均しの低い方)・
    /// 区間 = ex ≥ baseMin を 0.5 ごとに続けた所・倍率 = 欄の s(書いてあれば)か max(0.25, 露出の最大 / baseUnit を 1/4 で切り上げ)。⟶ 報告の行(前の算出物との差)。
    /// 当たる先: 天端の線の上の練塀の台(岡部の外周)。</summary>
    static string HeiLineBaseFromTenba()
    {
        _hlBase.Clear(); if (_hlProfiles.Count == 0) return null;
        var inv = System.Globalization.CultureInfo.InvariantCulture; var cst = O(D["const"]);
        if (!Has(cst, "baseMin") || !Has(cst, "baseUnit")) return "★ const.baseMin / baseUnit が無い ── 台は算出物のまま";
        float bmin = F(cst["baseMin"]), unit = F(cst["baseUnit"]);
        var bdB = EdoBuild.BaseDem(); var mnB = MichiNarashi;
        Func<float, float, float> gOut = (x, z) => { float b0 = bdB(x, z); float m0 = mnB == null ? float.NaN : MichiNarashiAt(mnB, x, z); return float.IsNaN(m0) ? b0 : (float.IsNaN(b0) ? m0 : Mathf.Min(b0, m0)); };
        var roadE = new HashSet<int>();
        foreach (var o in A(Get(D, "edges")) ?? new List<object>()) { var ed = O(o); if (ed == null || !Has(ed, "i")) continue; string nb = S(Get(ed, "neighbor")) ?? ""; if (nb.Contains("道") || nb.Contains("街路") || nb.Contains("坂")) roadE.Add((int)F(ed["i"])); }
        var baseByRun = new Dictionary<string, Dictionary<string, object>>(); foreach (var o in A(Get(IMPL, "base")) ?? new List<object>()) { var e = O(o); if (e != null) baseByRun[S(e["run"])] = e; }
        var sb = new System.Text.StringBuilder("  台の石垣を天端の線の座から(runs[].sFrom・露出 ≥ baseMin " + bmin.ToString("F2", inv) + "・倍率 = 露出の最大 / " + unit.ToString("0.#", inv) + " を 1/4 で切り上げ): ");
        foreach (var r in Runs)
        {
            if (!r.Ishigaki || r.lineS == null) continue;
            Vector2 a = EdgePt(r.edge, 0f), u = (EdgePt(r.edge, 1f) - a).normalized, o = OutNormal(r.edge);
            var offs = new List<float>(); if (roadE.Contains(r.edge)) for (float q = 2.0f; q <= 5.0f + 1e-3f; q += 0.5f) offs.Add(q); else offs.Add(1.0f);
            Func<float, float> ex = sv => { float m = float.MaxValue; foreach (var q in offs) { var p = a + u * sv + o * q; float g = gOut(p.x, p.y); if (!float.IsNaN(g)) m = Mathf.Min(m, g); } return m == float.MaxValue ? 0f : r.SeatAt(sv) - m; };
            var segs = new List<Vector2>(); float cur = float.NaN, exMax = 0f;
            for (float sv = r.s0; sv <= r.s1 + 1e-6f; sv += 0.5f) { float e0 = ex(sv); exMax = Mathf.Max(exMax, e0); if (e0 >= bmin) { if (float.IsNaN(cur)) cur = sv; } else if (!float.IsNaN(cur)) { segs.Add(new Vector2(cur, sv)); cur = float.NaN; } }
            exMax = Mathf.Max(exMax, ex(r.s1));
            if (!float.IsNaN(cur)) segs.Add(new Vector2(cur, r.s1));
            //   駒一枚の半分(1.0)に満たない切れ端は置かない ⚠(第121巡: 0.1m の区間に駒を一つ据えると控え c の測りが上限 2.5 へ張り付き、芯線の控え d が 2.8 に化けて辺33・34 の折れ点が 10m 飛んだ)
            //   ⭐ 段の所で台を切らない(施主 2026-10-13 第123巡「段の所の台も上と下の天端の線それぞれに従い、段の面で小口を閉じて突き付ける」)──
            //   区間の間の 1.0 未満の切れ目は埋め、区間の端が段の点・run の端から 0.6 以内なら そこまで延ばす(露出の 0.5 刻みの読みで段の脇 0.5 が抜けていた・S_Hei_18 s5.50〜6.00)
            {
                var ends = new List<float> { r.s0, r.s1 }; for (int k = 0; r.lineStep != null && k < r.lineS.Length; k++) if (r.lineStep[k]) ends.Add(r.lineS[k]);
                for (int i = segs.Count - 2; i >= 0; i--) if (segs[i + 1].x - segs[i].y < 1.0f) { segs[i] = new Vector2(segs[i].x, segs[i + 1].y); segs.RemoveAt(i + 1); }
                for (int i = 0; i < segs.Count; i++)
                {
                    float x = segs[i].x, y = segs[i].y;
                    foreach (var ep in ends) { if (ep < x && x - ep <= 0.6f && (i == 0 || ep >= segs[i - 1].y)) x = ep; if (ep > y && ep - y <= 0.6f && (i == segs.Count - 1 || ep <= segs[i + 1].x)) y = ep; }
                    segs[i] = new Vector2(x, y);
                }
            }
            int nDrop = segs.RemoveAll(sg => sg.y - sg.x < 1.0f);
            string sRun = RunText(r.name, "s"); float sc;
            float sFix; if (sRun != null && float.TryParse(sRun, System.Globalization.NumberStyles.Float, inv, out sFix) && sFix > 0f) sc = sFix;
            else sc = Mathf.Max(0.25f, Mathf.Ceil(exMax / unit * 4f - 1e-6f) / 4f);
            _hlBase[r.name] = new KeyValuePair<float, List<Vector2>>(sc, segs);
            float lenNew = 0f; foreach (var sg in segs) lenNew += sg.y - sg.x;
            float lenOld = 0f, sOld = float.NaN; Dictionary<string, object> bo; if (baseByRun.TryGetValue(r.name, out bo)) { if (Has(bo, "s")) sOld = F(bo["s"]); foreach (var q in A(Get(bo, "segs")) ?? new List<object>()) { var t2 = A(q); if (t2 != null && t2.Count == 2) lenOld += F(t2[1]) - F(t2[0]); } }
            sb.Append(r.name + " s " + (float.IsNaN(sOld) ? "-" : sOld.ToString("0.##", inv)) + "→" + sc.ToString("0.##", inv) + "・区間 " + lenOld.ToString("F1", inv) + "→" + lenNew.ToString("F1", inv) + "m・露出の最大 " + exMax.ToString("F2", inv) + (nDrop > 0 ? "・1.0 未満の切れ端 " + nDrop + " を置かない ⚠" : "") + "; ");
        }
        //   ⭐ 倍率を塀の一続きで一つに(第123巡 ── run ごとの倍率で台の天端の前の縁 c と見え面が run の継ぎ目・段で食い違い、駒がばらばらに見えた・P22 の 0.25 × 0.75)。
        //   一続きの中で倍率を欄で決めていない run を、その一続きの最大へ(深い分は地中へ埋まる ── 据えは埋めて隠す)。欄の倍率(runs[].s)の run はそのまま
        {
            int n2 = Poly.Length; var txt = new List<string>();
            foreach (var rg in _hlRanges)
            {
                var es = new HashSet<int>(); for (int e = rg.x; e <= rg.y; e++) es.Add(e % n2);
                float mx = 0f; var free = new List<string>();
                foreach (var r in Runs) { KeyValuePair<float, List<Vector2>> hb; if (!es.Contains(r.edge) || !_hlBase.TryGetValue(r.name, out hb)) continue; float sF; string sRun = RunText(r.name, "s"); bool fixedS = sRun != null && float.TryParse(sRun, System.Globalization.NumberStyles.Float, inv, out sF) && sF > 0f; if (fixedS) continue; free.Add(r.name); mx = Mathf.Max(mx, hb.Key); }
                foreach (var nm in free) { var hb = _hlBase[nm]; if (hb.Key < mx) _hlBase[nm] = new KeyValuePair<float, List<Vector2>>(mx, hb.Value); }
                txt.Add("辺" + (rg.x % n2) + "〜" + (rg.y % n2) + " 倍率 " + mx.ToString("0.##", inv) + "(" + free.Count + " run)");
            }
            sb.Append("\n    倍率を塀の一続きで一つに: " + string.Join("・", txt.ToArray()));
        }
        return sb.ToString();
    }
    /// <summary>辺 e を含む天端の線(無ければ null)。</summary>
    static EdoBuild.HeiProfile ProfileOfEdge(int e) { foreach (var pf in _hlProfiles) if (pf.tStart.ContainsKey(((e % Poly.Length) + Poly.Length) % Poly.Length)) return pf; return null; }
    /// <summary>run が天端の線・芯線の上か(新しい決め方の経路 ── 後合わせの規則 AlignInubashiri・KeepInsidePoly・SeatKadoToRuns・2m 割り・床へ据える を通らない)。
    /// Stage2 の外(domain reload で線が消えた後の 3d)は指図の範囲で判じる(第121巡)。</summary>
    static bool OnHeiLine(Run r) { if (_heiLineD != null) return r.lineS != null && _heiLineD.ContainsKey(r.edge); return r.Dobei && HeiLineEdgeSet().Contains(r.edge); }
    /// <summary>**芯線の頂点の隅を天端の線へ据える**(const.heiLine.tenba・第121巡)── 隅の実メッシュの足(腰の底)を**両腕の先で**測り(腕の先 = 練塀の駒が突き付く所)、
    /// その所の線の座(<see cref="EdoBuild.HeiProfile.YAt"/>)との差の中ほどだけ上下に動かす(坂の隅は腕ごとの勾配を持つ ⇒ 両腕の先が線に乗る・⛔ ピボットで据えない)。
    /// 残る食い違い(両腕の先の差の半分)を刷る。⛔ 床・腕に続く直線の駒で後から合わせない(SeatKadoToRuns を通らない)。</summary>
    static string SeatHeiLineKado(Transform kak)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var txt = new List<string>(); int n = Poly.Length; float worst = 0f;
        foreach (Transform c in kak)
        {
            int v; if (!c.name.StartsWith("Kado_P") || !int.TryParse(c.name.Substring(6), out v) || !OnHeiLineVertex(v)) continue;
            int eI = (v - 1 + n) % n, eO = v % n; var pfI = ProfileOfEdge(eI); var pfO = ProfileOfEdge(eO);
            if (pfI == null || pfO == null) { txt.Add(c.name + " ★ 天端の線が無い"); continue; }
            Vector2 aI = Poly[eI], uI = (Poly[v % n] - Poly[eI]).normalized, uO = (Poly[(v + 1) % n] - Poly[v % n]).normalized;
            //   腕の分けは芯線の折れ点(両辺の芯線の交点)で ── 区画の頂点で分けると、控え d が辺で違う隅(P29・P32・P35)は折れ点が頂点から 1m 余り離れ、全部の頂点が片方の腕に入る
            float wO = (_heiLineD.ContainsKey(eO) ? _heiLineD[eO] : 0f) + HEI_CORE_IN; Vector2 V = Poly[v % n] + uO * pfO.sC[eO] - OutNormal(eO) * wO;
            float sInMin = float.MaxValue, sOutMax = float.MinValue; var pts = new List<Vector4>();
            foreach (var mf in c.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.gameObject.name != "ishigaki" && mf.gameObject.name != "koguchi" && mf.gameObject.name != "soko") continue; if (mf.sharedMesh == null) continue;
                foreach (var lv in mf.sharedMesh.vertices)
                {
                    var w = mf.transform.TransformPoint(lv); Vector2 q = new Vector2(w.x, w.z) - V; float tIn = -Vector2.Dot(q, uI), tOut = Vector2.Dot(q, uO);
                    bool inArm = tIn >= tOut; float sv = inArm ? Vector2.Dot(new Vector2(w.x, w.z) - aI, uI) : Vector2.Dot(new Vector2(w.x, w.z) - Poly[v % n], uO);
                    pts.Add(new Vector4(inArm ? 0f : 1f, sv, w.y, 0f));
                    if (inArm) sInMin = Mathf.Min(sInMin, sv); else sOutMax = Mathf.Max(sOutMax, sv);
                }
            }
            if (sInMin == float.MaxValue || sOutMax == float.MinValue) { txt.Add(c.name + " ★ 腕の足が測れない"); continue; }
            float yI = float.MaxValue, yO = float.MaxValue;
            foreach (var p in pts) { if (p.x < 0.5f && p.y <= sInMin + 0.03f) yI = Mathf.Min(yI, p.z); if (p.x > 0.5f && p.y >= sOutMax - 0.03f) yO = Mathf.Min(yO, p.z); }
            float yWI = pfI.YAt(eI, sInMin, -1), yWO = pfO.YAt(eO, sOutMax, +1);
            float sh = 0.5f * ((yWI - yI) + (yWO - yO)); c.position += Vector3.up * sh;
            float res = 0.5f * Mathf.Abs((yWI - yI) - (yWO - yO)); worst = Mathf.Max(worst, res);
            txt.Add(c.name + " 腕の先 入 s" + sInMin.ToString("F2", inv) + " " + yWI.ToString("F3", inv) + "・出 s" + sOutMax.ToString("F2", inv) + " " + yWO.ToString("F3", inv) + "(動かした " + sh.ToString("+0.000;-0.000", inv) + ")" + (res > 0.005f ? " ⚠ 食い違い " + res.ToString("F3", inv) : ""));
        }
        return "  芯線の隅を天端の線へ(両腕の先の足で測る・残る食い違いの最大 " + worst.ToString("F3", inv) + "): " + string.Join(" / ", txt.ToArray());
    }
    /// <summary>頂点 v の両脇の辺が芯線(const.heiLine)の上か(隅の駒を据える時に一続きの控え d で面を合わせる ── FitKado・SeatKadoToRuns を通らない)。domain reload の後は指図の範囲で判じる。</summary>
    static bool OnHeiLineVertex(int v) { int n = Poly.Length; v = ((v % n) + n) % n; if (_heiLineD != null) return _heiLineD.ContainsKey((v - 1 + n) % n) && _heiLineD.ContainsKey(v); var es = HeiLineEdgeSet(); return es.Contains((v - 1 + n) % n) && es.Contains(v); }

    /// <summary>辺 e・走り s の run の犬走り ── 既定は const.inubashiri。runs[].face が「腰の外面は基壇の法肩と同じ線…犬走り 0」と書く run は 0
    /// (岡部 S_Hei_01/01b・普請方の設計 2026-10-12・第114巡【柔・⚠ const.kidan の 0.30 から外れる】)。当たる先: face で犬走りを外す run(いまは岡部 P1 の入隅の二本)。</summary>
    static float RunInu(int e, float s)
    {
        int best = -1; float bd = float.MaxValue;
        for (int k = 0; k < Runs.Length; k++)
        {
            var r = Runs[k]; if (r.edge != e) continue;
            float d = s < r.s0 ? r.s0 - s : (s > r.s1 ? s - r.s1 : 0f);
            if (d < bd) { bd = d; best = k; }
        }
        if (best < 0) return INUBASHIRI;
        string ft = RunText(Runs[best].name, "face") ?? "";
        return System.Text.RegularExpressions.Regex.IsMatch(ft, @"法肩と同じ線.*犬走り\s*0(?![.0-9])") ? 0f : INUBASHIRI;
    }

    /// <summary>**外周の基壇**(城の石垣・const.kidan 甲の型 ── 普請方の設計 2026-10-11 を普請奉行が採った)。
    /// 置き方は <see cref="EdoBuild.PlaceCastleRun"/>(土井の外周の基壇と同じ型・EDO-0533)── ここは指図の区間を渡すだけ(規則21):
    /// 区間 = 算出物 base[].segs(露出が baseMin に満たない所は置かない)・天端 = run の座(SeatAt・斜面の run は 2m ごとの段)・倍率 = base[].s
    /// (壁高 4.0s)・見え面(法)= 区画の外【硬】・基準線 = 根石の外面を区画の線へ、前に溝を持つ run(runs[].front「溝の内の縁」)は溝の駒(型A)の
    /// 実測の全幅 +0.01 の内へ【硬 +0/−0.05】・控え c = 根石が基準線を越えない最小(実メッシュ・run ごと ── 倍率と基準線が run で違う)。
    /// ⛔ 旧い据え(Castle Wall の局所 +X = 鉛直な背を外へ・ピボットを線に)は法が全辺で内を向いていた(第106巡)。
    /// 結果の c は <see cref="_kidanC"/> へ ── 囲いの外面は線から c + 犬走り(<see cref="FaceIn"/>)。⚠ 囲いより先に呼ぶ。</summary>
    /// <summary>据え直した基壇の報告の頭の行 + 坂なり(第122巡)の行(焼いていない駒・坂の隅・出隅)。</summary>
    static string IshigakiHead(string full)
    {
        var ls = full.Split('\n'); var sb = new System.Text.StringBuilder(ls[0]);
        for (int i = 1; i < ls.Length; i++) if (ls[i].Contains("坂なり") || ls[i].Contains("出隅 IG_") || ls[i].Contains("出隅の駒")) sb.Append("\n   " + ls[i].Trim());
        return sb.ToString();
    }
    static string PlaceIshigaki()
    {
        var grp = Group("Ishigaki"); Clear(grp);
        _kidanC.Clear(); _kidanCe.Clear();
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var baseByRun = new Dictionary<string, Dictionary<string, object>>();
        foreach (var o in A(Get(IMPL, "base")) ?? new List<object>())
        { var e = O(o); if (e != null) baseByRun[S(e["run"])] = e; }
        float gutW = FrontGutterWidth();
        var secs = new List<EdoBuild.CastleSec>(); var miss = new List<string>(); float thin = 0f; var notes = new List<string>();
        foreach (var r in Runs)
        {
            if (!r.Ishigaki) continue;
            if (!baseByRun.ContainsKey(r.name)) { miss.Add(r.name); continue; }
            var bd = baseByRun[r.name];
            float sc = Has(bd, "s") ? F(bd["s"]) : r.s;
            //   ⭐ 天端の線の run(const.heiLine.tenba・第121巡)は台の区間と倍率を天端の線の座から解いた物(HeiLineBaseFromTenba ── 算出物 base[] は前の座で焼いた)
            KeyValuePair<float, List<Vector2>> hlB = default(KeyValuePair<float, List<Vector2>>); bool hasHlB = r.lineS != null && _hlBase.TryGetValue(r.name, out hlB);
            if (hasHlB) sc = hlB.Key;
            if (sc <= 0f) { miss.Add(r.name + "(倍率 s が 0)"); continue; }
            foreach (var q in A(Get(bd, "thin")) ?? new List<object>())
            { var t2 = A(q); if (t2 != null && t2.Count == 2) thin += F(t2[1]) - F(t2[0]); }
            string fr = RunText(r.name, "front") ?? "";
            float dIn = 0f;
            if (fr.Contains("溝の内の縁"))
            {
                if (float.IsNaN(gutW)) { notes.Add("★ " + r.name + ": 前の溝の駒(型A)が測れない ── 基準線を区画の線のまま"); }
                else dIn = gutW + FRONT_GUTTER_GAP;
            }
            int k = 0;
            var segList = new List<Vector2>();
            if (hasHlB) segList.AddRange(hlB.Value);
            else foreach (var q in A(Get(bd, "segs")) ?? new List<object>()) { var t2 = A(q); if (t2 != null && t2.Count == 2) segList.Add(new Vector2(F(t2[0]), F(t2[1]))); }
            foreach (var sg in segList)
            {
                float t0 = sg.x, t1 = sg.y; if (t1 - t0 <= 0.01f) continue;
                var brk = SeatBreaks(r, t0, t1);   // 天端の段ごと(切れ目 seatRule の前の一直線は一つ・傾いた所は約 2m ごと)
                for (int j = 0; j + 1 < brk.Count; j++)
                {
                    float a0 = brk[j], a1 = brk[j + 1];
                    //   ⭐ 天端の線の坂なりの区間(const.heiLine.kidanCrest【硬】・第122巡)── 台の石垣の天端は塀の座の線そのもの: 区間の座の勾配のまま一筋
                    //   (坂なりの駒 EdoAssets.Own.IshigakiChokuSaka ── PlaceCastleRun の slopePathOf)。⛔ 1.80 ごとの段に割らない(第121巡の段は塀の底と最大 1.59 の隙)
                    int kq = r.LineIndexAt(0.5f * (a0 + a1)); float gq = r.lineGrade != null && kq >= 0 ? r.lineGrade[kq] : 0f;
                    if (Mathf.Abs(gq) > 5e-5f)
                    {
                        secs.Add(new EdoBuild.CastleSec { name = "IG_" + r.name + "_" + k + "_" + j, edge = r.edge, s0 = a0, s1 = a1, crest = r.SeatOnRow(kq, a0), grade = gq, scale = sc, datumIn = dIn, insetKey = r.name });
                        continue;
                    }
                    float crest = Mathf.Round(r.SeatAt((a0 + a1) * 0.5f) * 1000f) / 1000f;
                    secs.Add(new EdoBuild.CastleSec { name = "IG_" + r.name + "_" + k + "_" + j, edge = r.edge, s0 = a0, s1 = a1, crest = crest,
                                                      scale = sc, datumIn = dIn, insetKey = r.name });
                }
                k++;
            }
        }
        var log = new System.Text.StringBuilder();
        // 区画の外の地盤の基準 = base_dem と道の線際の均し(michiNarashi)の低い方 ── Unity の今の地形を採らない(const.kidan.faces【硬】・規則13)。区画の内は今の地形(造成後)。
        var bdB = EdoBuild.BaseDem(); var mnB = MichiNarashi;
        Func<float, float, float> gB = (x, z) =>
        {
            if (EdoGeom.PIP(Poly, new Vector2(x, z))) return EdoBuild.Ground(x, z);
            float b0 = bdB(x, z); float m0 = mnB == null ? float.NaN : MichiNarashiAt(mnB, x, z);
            return float.IsNaN(m0) ? b0 : (float.IsNaN(b0) ? m0 : Mathf.Min(b0, m0));
        };
        // ⭐ 出隅 ≥ 40° は石垣の隅の駒(倍率 s の版 Ishigaki_Kado_<deg>_H0400_S075・662de3e6)で受ける(const.kidan.corner.ge40【硬】・第109巡)。
        //   両脇の天端か倍率が違う出隅は隅の駒が据わらない(PlaceRunKado の硬い条件)⇒ kadoSkip で根石の端を頂点へ(従来の突き付け)し ★ を刷る。
        //   当たる先: 外周の基壇を PlaceCastleRun で据える邸(岡部・土井)の 40° 以上の出隅すべて。
        // ⭐ 角 P0 の天端違いの納め(指図 grading.omoteNagayaDai.cornerP0.step / kado【硬】・第109巡)── 角では天端を変えない:
        //   辺0 の P0 から段の位置までの区間を辺41 の端の天端・倍率で据える仮の区間にし、隅の駒(95・倍率 0.75)を両腕 12.3 で受けさせてから、
        //   辺0 の腕を切った版(_A200x0 / _A0x200・yaw の解で選ぶ)へ差し替え、仮の区間の駒は退ける(腕の見え面と小口が段まで覆う)。
        //   段から先は基壇の無い区間(算出物 base[SE_Hei].thin)── 練塀は段の小口へ突き付ける(_p0KoguchiS → Stage2 の kadoLo)。
        //   当たる先: 両脇の天端か倍率が違う出隅を「片方の辺の頭を高い側で受けて段を辺の途中へ」納める邸(いまは岡部 P0 だけ)。
        _p0KoguchiS = float.NaN; string p0Note = null; float p0StepS = float.NaN;
        {
            var gr0 = O(Get(D, "grading")); var dai0 = gr0 == null ? null : O(Get(gr0, "omoteNagayaDai")); var cp = dai0 == null ? null : O(Get(dai0, "cornerP0"));
            var mSt = cp == null ? null : System.Text.RegularExpressions.Regex.Match(S(Get(cp, "step")) ?? "", @"辺\s*(\d+)\s*の頂点\s*P(\d+)\s*から\s*([0-9.]+).*?段\s*([0-9.]+)\s*[(（]\s*([0-9.]+)\s*→\s*([0-9.]+)");
            // ⭐ 施主裁定 2026-10-12 案A(第113巡): 「辺0 の台 P0Dan は P0→P1 で天端 12.3 の一直線【硬】。段を設けない」── 辺0 に run が無い(SE_Hei を廃した)ので、
            //   辺0 の全長を台の区間に起こす。倍率は角の高い側(辺41 の尻の区間)の倍率 ── 隅の駒(cornerP0.kado の腕を切らない版)が両腕で同じ倍率・天端で受ける。
            //   当たる先: 練塀の無い辺の全長を基壇だけで通す角(いまは岡部 P0)。
            var mDai = cp == null ? null : System.Text.RegularExpressions.Regex.Match(S(Get(cp, "step")) ?? "", @"辺\s*(\d+)\s*の台\s*(\w+)\s*は\s*P(\d+)\s*→\s*P(\d+)\s*で天端\s*([0-9.]+)\s*の一直線");
            if (mDai != null && mDai.Success)
            {
                int eD = int.Parse(mDai.Groups[1].Value); float cD = float.Parse(mDai.Groups[5].Value, inv); string nmD = mDai.Groups[2].Value;
                int eP = (eD - 1 + Poly.Length) % Poly.Length; float LP = EdgeLen(eP);
                var sHi = secs.Find(x => x.edge == eP && x.s1 >= LP - EdoBuild.VTX_TOL);
                if (sHi == null) p0Note = "★ cornerP0: 辺" + eP + " の尻の基壇の区間が無い ── 台 " + nmD + " の倍率が決まらない・建てない";
                else if (secs.Exists(x => x.edge == eD)) p0Note = "★ cornerP0: 辺" + eD + " に既に基壇の区間がある(run の base)── 台 " + nmD + " を重ねない";
                else
                {
                    secs.Add(new EdoBuild.CastleSec { name = "IG_" + nmD, edge = eD, s0 = 0f, s1 = EdgeLen(eD), crest = cD, scale = sHi.scale, datumIn = 0f, insetKey = nmD });
                    p0Note = "⭕ cornerP0: 辺" + eD + " の台 " + nmD + " を全長 " + EdgeLen(eD).ToString("F3", inv) + "m・天端 " + cD.ToString("F2", inv) + " の一直線・倍率 " + sHi.scale.ToString("0.##", inv)
                           + "(辺" + eP + " の " + sHi.insetKey + " と同じ)で起こした" + (Mathf.Abs(sHi.crest - cD) > 0.02f ? " ⚠ 辺" + eP + " の天端 " + sHi.crest.ToString("F2", inv) + " と違う(隅の駒が据わらない)" : "");
                }
                cp = null;   // 旧い段の納め(下)は通さない
            }
            if (cp != null && (mSt == null || !mSt.Success)) p0Note = "★ cornerP0.step が読めない ── 角 P0 は頂点で突き付け(従前)";
            else if (cp != null)
            {
                int eS = int.Parse(mSt.Groups[1].Value), vS = int.Parse(mSt.Groups[2].Value); float stS = float.Parse(mSt.Groups[3].Value, inv), cHi = float.Parse(mSt.Groups[5].Value, inv);
                int eP = (vS - 1 + Poly.Length) % Poly.Length; float LP = EdgeLen(eP);
                var sHi = secs.Find(x => x.edge == eP && x.s1 >= LP - EdoBuild.VTX_TOL);
                var sLo = secs.Find(x => x.edge == eS && x.s0 <= EdoBuild.VTX_TOL);
                if (eS != vS || sHi == null || sLo == null) p0Note = "★ cornerP0: 辺" + eS + " の頭か辺" + eP + " の尻の基壇の区間が無い ── 頂点で突き付け(従前)";
                else
                {
                    if (Mathf.Abs(sHi.crest - cHi) > 0.02f) p0Note = "⚠ cornerP0: 高い側の天端 欄 " + cHi.ToString("F2", inv) + " / 辺" + eP + " の座 " + sHi.crest.ToString("F2", inv) + "(座を採る)";
                    if (sLo.s1 > stS + 0.05f) secs.Add(new EdoBuild.CastleSec { name = sLo.name + "_dan", edge = sLo.edge, s0 = stS, s1 = sLo.s1, crest = sLo.crest, scale = sLo.scale, datumIn = sLo.datumIn, insetKey = sLo.insetKey });
                    sLo.s1 = stS; sLo.crest = sHi.crest; sLo.scale = sHi.scale; sLo.name = "IG_P0Dan"; sLo.insetKey = "P0Dan";
                    p0StepS = stS;
                }
            }
        }
        var kadoSkip = new HashSet<int>(); var kadoAt = new List<string>(); var kadoV = new List<int>();
        int nP0 = Poly.Length; float ar0 = 0f; for (int i = 0; i < nP0; i++) ar0 += Poly[i].x * Poly[(i + 1) % nP0].y - Poly[(i + 1) % nP0].x * Poly[i].y;
        Func<int, float> turnAt = v => { int e0 = (v - 1 + nP0) % nP0; Vector2 d1 = (Poly[v] - Poly[e0]).normalized, d2 = (Poly[(v + 1) % nP0] - Poly[v]).normalized;
                                          float tv = Mathf.Atan2(d1.x * d2.y - d1.y * d2.x, Vector2.Dot(d1, d2)) * Mathf.Rad2Deg; return ar0 < 0f ? -tv : tv; };
        for (int v = 0; v < nP0; v++)
        {
            int e0 = (v - 1 + nP0) % nP0; float L0 = (Poly[v] - Poly[e0]).magnitude;
            var sA = secs.Find(x => x.edge == e0 && x.s1 >= L0 - EdoBuild.VTX_TOL); var sB2 = secs.Find(x => x.edge == v && x.s0 <= EdoBuild.VTX_TOL);
            if (sA == null || sB2 == null) continue;
            float tv = turnAt(v); if (tv < 40f) continue;
            //   ⭐ 坂なりの区間(第122巡)── 両脇の天端は頂点の端の値で比べる(sA は尻・sB2 は頭)。線が続いていれば隅の駒(坂の隅 IshigakiKadoSaka)で受ける
            if (sA.Sloped || sB2.Sloped)
            {
                float cA = sA.CrestAt(sA.s1), cB = sB2.crest;
                if (Mathf.Abs(cA - cB) <= 0.02f && Mathf.Abs(sA.scale - sB2.scale) < 1e-3f) { kadoAt.Add("P" + v + " " + tv.ToString("F1", inv) + "°(坂なり・天端 " + cA.ToString("F3", inv) + "/" + cB.ToString("F3", inv) + ")"); kadoV.Add(v); }
                else { kadoSkip.Add(v); log.AppendLine("  ★ 城の石垣 頂点 P" + v + "(" + sA.insetKey + " × " + sB2.insetKey + "): 坂なりの出隅 " + tv.ToString("F1", inv) + "° ── 頂点の天端 " + cA.ToString("F3", inv) + "/" + cB.ToString("F3", inv) + "・倍率 " + sA.scale.ToString("0.##", inv) + "/" + sB2.scale.ToString("0.##", inv) + " が違い隅の駒が据わらない ⇒ 頂点で突き付けた"); }
                continue;
            }
            // 角では天端を変えない(cornerP0.step と同じ作法)── 坂の座の run は 2m ごとの区間の芯で天端を刻むので、頂点の両脇の区間の天端が刻みの分だけ違う。
            //   両 run の座が頂点で続く(差 ≤ 0.02)なら、頂点の両脇の区間の天端を頂点の座へ揃える(隅の駒の両腕を同じ天端に)。当たる先: 坂の座の run が出隅で折れる所(岡部 P24)。
            //   ⭐ 天端の線の run(const.heiLine.tenba・第121巡)── 両脇の区間の天端は駒の走りごとに区間の高い方で刻んである ⇒ 高い方へ揃える
            //   (塀の底は天端に載るか天端の中へ埋まる ⇒ 隙0【硬】・⛔ 頂点の座の中ほどへ下げると高い側の塀の底が天端から浮く)。差 0.10 を越えれば揃えない(★ 頂点で突き付け)
            {
                bool hlA = false, hlB = false; foreach (var rr in Runs) { if (rr.name == sA.insetKey && rr.lineS != null) hlA = true; if (rr.name == sB2.insetKey && rr.lineS != null) hlB = true; }
                if ((hlA || hlB) && Mathf.Abs(sA.crest - sB2.crest) > 1e-3f && Mathf.Abs(sA.crest - sB2.crest) <= 0.10f && Mathf.Abs(sA.scale - sB2.scale) < 1e-3f)
                {
                    float cv = Mathf.Max(sA.crest, sB2.crest);
                    log.AppendLine("  城の石垣 頂点 P" + v + ": 両脇の区間の天端 " + sA.crest.ToString("F3", inv) + "/" + sB2.crest.ToString("F3", inv) + " を高い方 " + cv.ToString("F3", inv) + " へ揃えた(天端の線・出隅の隅の駒の両腕を同じ天端に)");
                    sA.crest = cv; sB2.crest = cv;
                }
            }
            if (Mathf.Abs(sA.crest - sB2.crest) > 1e-3f && Mathf.Abs(sA.scale - sB2.scale) < 1e-3f)
            {
                Run rA2 = default(Run), rB2 = default(Run); bool hA = false, hB = false; foreach (var rr in Runs) { if (rr.name == sA.insetKey) { rA2 = rr; hA = true; } if (rr.name == sB2.insetKey) { rB2 = rr; hB = true; } }
                if (hA && hB)
                {
                    float yA = rA2.SeatAt(sA.s1), yB = rB2.SeatAt(sB2.s0);
                    if (Mathf.Abs(yA - yB) <= 0.02f)
                    {
                        float cv = Mathf.Round(0.5f * (yA + yB) * 1000f) / 1000f;
                        log.AppendLine("  城の石垣 頂点 P" + v + ": 両脇の区間の天端 " + sA.crest.ToString("F3", inv) + "/" + sB2.crest.ToString("F3", inv) + " を頂点の座 " + cv.ToString("F3", inv) + " へ揃えた(角で天端を変えない・出隅)");
                        sA.crest = cv; sB2.crest = cv;
                    }
                }
            }
            // ⭐ 指図が頂点の隅の駒を名指す(runs[].kadoEnd / kadoStart「基壇の隅の駒は Own.IshigakiKadoS(…) = <名>」)出隅は、倍率の差 ≤ 0.02 を柔(⚠)として隅の駒で受ける
            //   (岡部 P3 = S_Hei_01b 0.41 × S_Hei_01c 0.42 ── S042・第114巡)。当たる先: 倍率の近い二辺の出隅に隅の駒を名指した所。
            string namedK = NamedCornerPart(v, "Ishigaki_Kado_");
            if (namedK != null && Mathf.Abs(sA.crest - sB2.crest) <= 1e-3f && Mathf.Abs(sA.scale - sB2.scale) > 1e-3f && Mathf.Abs(sA.scale - sB2.scale) <= 0.02f + 1e-4f)
            {
                log.AppendLine("  ⚠ 城の石垣 頂点 P" + v + "(" + sA.insetKey + " × " + sB2.insetKey + "): 倍率 " + sA.scale.ToString("0.##", inv) + "/" + sB2.scale.ToString("0.##", inv) + " の差 " + Mathf.Abs(sA.scale - sB2.scale).ToString("0.###", inv)
                              + " は柔 ── 指図が名指す隅の駒 " + namedK + " で受ける(見え面の段違いは実測で下に刷る)");
                kadoAt.Add("P" + v + " " + tv.ToString("F1", inv) + "°"); kadoV.Add(v); continue;
            }
            if (Mathf.Abs(sA.crest - sB2.crest) > 1e-3f || Mathf.Abs(sA.scale - sB2.scale) > 1e-3f)
            {
                kadoSkip.Add(v);
                log.AppendLine("  ★ 城の石垣 頂点 P" + v + "(" + sA.insetKey + " × " + sB2.insetKey + "): 出隅 " + tv.ToString("F1", inv) + "° ≥ 40° ── 両脇の天端 " + sA.crest.ToString("F2", inv) + "/" + sB2.crest.ToString("F2", inv)
                              + "・倍率 " + sA.scale.ToString("0.##", inv) + "/" + sB2.scale.ToString("0.##", inv) + " が違い隅の駒が据わらない ⇒ 頂点で突き付けた(納めの欄が要る" + (v == 0 ? " ── grading.omoteNagayaDai.cornerP0 は差し戻し" : "") + ")");
            }
            else { kadoAt.Add("P" + v + " " + tv.ToString("F1", inv) + "°"); kadoV.Add(v); }
        }
        EdoBuild.CrestWall.missingSlope.Clear(); EdoBuild.SlopeKado.missing.Clear();
        var cr = EdoBuild.PlaceCastleRun(secs, Poly, gB, grp, log, 2.5f, SEAM_TOL, -1f, 40f, kadoSkip, (g, h, len) => EdoAssets.Own.IshigakiChokuSaka(g, h, len));
        // 隅の駒: 実寸の丈 hReal → 名の丈 hReal / s(倍率の版を焼いた s から引く ── 素の 1 も候補)・scale = 1 で据える(⛔ s を二重に掛けない)
        var scales = new List<float>(); foreach (var x in secs) if (!scales.Exists(q => Mathf.Abs(q - x.scale) < 1e-4f)) scales.Add(x.scale);
        string projRoot = System.IO.Directory.GetParent(Application.dataPath).FullName;
        Func<float, float, string> kadoPath = (deg, hReal) =>
        {
            foreach (var sc in scales) { string p = EdoAssets.Own.IshigakiKadoS(deg, hReal / sc, sc); if (System.IO.File.Exists(System.IO.Path.Combine(projRoot, p))) return p; }
            return EdoAssets.Own.IshigakiKadoS(deg, hReal / scales[0], scales[0]);
        };
        var kcs = new List<GameObject>();
        //   隅の駒を受けるのは 40° 以上で両脇の揃う出隅だけ(const.kidan.corner.lt40「< 40° は隅の駒なしで突き付ける」)── 端の組をその頂点の近く(3m)に絞る
        var kadoEnds = cr.ends.FindAll(en => { foreach (var kv in kadoV) if (Vector2.Distance(en.p, Poly[kv]) < 3f) return true; return false; });
        //   坂なりの出隅(第122巡)── 坂の隅の駒 Own.IshigakiKadoSaka(倍率の版を焼いた s から引く)
        Func<float, float, float, float, string> kadoSlopePath = (deg, hReal, gIn, gOut) =>
        {
            //   坂の隅は H0400 × 倍率 s(実寸の丈 4.0·s)── s は丈から
            float sK = Mathf.Round(hReal / 4f * 100f) / 100f; return EdoAssets.Own.IshigakiKadoSaka(deg, 4f, sK, gIn, gOut);
        };
        int kn = EdoBuild.PlaceRunCorners(kadoEnds, cr.segs, kadoPath, gB, grp, 0.02f, log, kcs, null, null, null, kadoSlopePath);
        foreach (var kc in kcs) cr.pieces.Add(kc);
        // 角 P0(cornerP0.kado): 隅の駒を辺0 の腕を切った版へ差し替え、仮の区間の駒を退け、小口の s を測る(練塀の突き付け先)
        if (!float.IsNaN(p0StepS))
        {
            Vector2 v0 = Poly[0], d0 = (Poly[1] - Poly[0]).normalized, o0 = OutNormal(0);
            GameObject k0 = null; float kd = 3f;
            foreach (var kc in kcs) { if (kc == null) continue; var b = EdoBuild.RB(kc); float dd = Vector2.Distance(new Vector2(b.center.x, b.center.z), v0); if (dd < kd) { kd = dd; k0 = kc; } }
            List<GameObject> tmp; int nTmp = 0;
            if (cr.bySec.TryGetValue("IG_P0Dan", out tmp)) foreach (var g in tmp) if (g != null) { cr.pieces.Remove(g); UnityEngine.Object.DestroyImmediate(g); nTmp++; }
            if (k0 == null) p0Note = "★ cornerP0: 角 P0 に隅の駒が据わらない(上の出隅の行)── 仮の区間 " + nTmp + " 駒を退けた・段の小口が無い";
            else
            {
                string ap = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(k0);
                Vector2 zArm = -new Vector2(k0.transform.forward.x, k0.transform.forward.z).normalized;   // 局所 −Z の腕の走り(build_kado.py の約束)
                bool negZIsE0 = Vector2.Dot(zArm, d0) > 0.5f;
                float degK = 0f, hK = 0f, sK2 = 0.75f;
                var mK = System.Text.RegularExpressions.Regex.Match(System.IO.Path.GetFileNameWithoutExtension(ap ?? ""), @"Kado_(\d+)_H(\d{4})_S(\d{3})");
                if (mK.Success) { degK = float.Parse(mK.Groups[1].Value, inv); hK = float.Parse(mK.Groups[2].Value, inv) / 100f; sK2 = float.Parse(mK.Groups[3].Value, inv) / 100f; }
                string cut = mK.Success ? EdoAssets.Own.IshigakiKadoS(degK, hK, sK2, negZIsE0 ? 0f : 2f, negZIsE0 ? 2f : 0f) : null;
                if (cut == null || !System.IO.File.Exists(System.IO.Path.Combine(projRoot, cut))) p0Note = "★ cornerP0: 辺0 の腕を切った版 " + (cut ?? ap) + " が焼いてない ── 素の隅のまま";
                else
                {
                    var pos = k0.transform.position; float yaw = k0.transform.eulerAngles.y; string nm = k0.name; var par = k0.transform.parent;
                    cr.pieces.Remove(k0); kcs.Remove(k0); UnityEngine.Object.DestroyImmediate(k0);
                    k0 = EdoBuild.Place(cut, pos, yaw, Vector3.one, par, nm); cr.pieces.Add(k0); kcs.Add(k0);
                    // 小口 = 辺0 の見え面の帯(線から内 1.0 まで)で、辺0 の走りの最も奥の頂点(実メッシュ)
                    float sMax = float.MinValue; foreach (var w in EdoBuild.Body(k0.transform, 999999)) { var q = new Vector2(w.x, w.z) - v0; if (Vector2.Dot(q, o0) < -1.0f) continue; sMax = Mathf.Max(sMax, Vector2.Dot(q, d0)); }
                    _p0KoguchiS = sMax;
                    p0Note = "⭕ cornerP0: 角 P0 の隅の駒を辺0 の腕を切った版 " + System.IO.Path.GetFileNameWithoutExtension(cut) + " へ(" + (negZIsE0 ? "−Z" : "+X") + " の腕が辺0)・両腕の天端 "
                           + EdoBuild.RB(k0).max.y.ToString("F3", inv) + "・仮の区間 " + nTmp + " 駒を退けた・段の小口 s " + sMax.ToString("F3", inv) + "(欄 " + p0StepS.ToString("F2", inv) + " ±0.3【柔】"
                           + (Mathf.Abs(sMax - p0StepS) <= 0.3f ? " ⭕" : " ⚠") + ")";
                }
            }
        }
        if (p0Note != null) log.AppendLine("  " + p0Note);
        //   ⭐ 40° 未満の出隅の口を裏の駒で塞ぐ(const.heiLine.faceFront【硬】「出隅で台の石が抜ける所を作らない」・第126巡 P35)
        log.AppendLine("  " + EdoBuild.FillConvexCornerSlits(secs, Poly, grp, gB, 40f));
        log.AppendLine("  ⭕ 城の石垣の出隅の駒 " + kn + " / 40° 以上で両脇の揃う出隅 " + kadoAt.Count + "(" + string.Join("・", kadoAt.ToArray()) + ")" + (kn < kadoAt.Count ? " ★ 据わらない隅あり(上の出隅の行)" : ""));
        foreach (var kv in cr.insetOf) _kidanC[kv.Key] = kv.Value;
        foreach (var r in Runs) { float c; if (_kidanC.TryGetValue(r.name, out c)) _kidanCe[r.edge] = Mathf.Max(_kidanCe.ContainsKey(r.edge) ? _kidanCe[r.edge] : 0f, c); }
        var sb = new System.Text.StringBuilder();
        float worstOut = 0f; string worstOutN = "-"; float worstIn = 0f; string worstInN = "-";
        foreach (var kv in cr.datumResid) { if (kv.Value > worstOut) { worstOut = kv.Value; worstOutN = kv.Key; } if (kv.Value < worstIn) { worstIn = kv.Value; worstInN = kv.Key; } }
        sb.Append("石垣基壇(甲の型・EdoBuild.PlaceCastleRun): " + cr.pieces.Count + " 駒 / 区間 " + secs.Count
                + (cr.buried > 0 ? "・全体が埋まり退けた " + cr.buried : "")
                + "・底の浮き 最悪 " + (float.IsNegativeInfinity(cr.worstFloat) ? "-" : cr.worstFloat.ToString("+0.000;-0.000", inv)) + "m"
                + "・区画の外 最悪 " + cr.worstOutside.ToString("F3", inv) + "m"
                + "・根石の外面 − 基準線 最大 " + worstOut.ToString("+0.000;-0.000", inv) + " @" + worstOutN + " / 最小 " + worstIn.ToString("+0.000;-0.000", inv) + " @" + worstInN
                + (worstOut > SEAM_TOL + 1e-4f || worstIn < -0.05f ? " ★(許容 +0/−0.05)" : " ✔"));
        var keys = new List<string>(cr.insetOf.Keys); keys.Sort();
        sb.Append("\n  法肩の控え c(run ごと・実測): ");
        foreach (var kk in keys) sb.Append(kk + " " + cr.insetOf[kk].ToString("F3", inv) + (cr.datumResid.ContainsKey(kk) ? "(根石 " + cr.datumResid[kk].ToString("+0.000;-0.000", inv) + ")" : "") + " / ");
        sb.Append("\n  辺の最大: "); var ek = new List<int>(_kidanCe.Keys); ek.Sort(); foreach (var e in ek) sb.Append("辺" + e + " " + _kidanCe[e].ToString("F3", inv) + " ");
        if (thin > 0.05f) sb.Append("\n  基壇を置かない区間 " + thin.ToString("F1", inv) + "m(露出 < baseMin)");
        if (miss.Count > 0) sb.Append("\n★ 算出物 base に無い run " + miss.Count + " 件: " + string.Join(" / ", miss.ToArray()));
        foreach (var nt in notes) sb.Append("\n" + nt);
        foreach (var line in log.ToString().Split('\n')) if (line.Contains("★") || line.Contains("⚠") || line.Contains("控える") || line.Contains("出隅")) sb.Append("\n" + line.TrimEnd());
        if (EdoBuild.CrestWall.missingSlope.Count > 0 || EdoBuild.SlopeKado.missing.Count > 0)
        {
            var ms = new List<string>(); foreach (var x in EdoBuild.CrestWall.missingSlope) ms.Add(System.IO.Path.GetFileNameWithoutExtension(x)); foreach (var x in EdoBuild.SlopeKado.missing) ms.Add(System.IO.Path.GetFileNameWithoutExtension(x)); ms.Sort();
            sb.Append("\n★ 台の坂なりの駒が焼いていない " + ms.Count + ": " + string.Join(" ", ms.ToArray()));
        }
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
            string assetKey = Has(k, "asset") ? S(k["asset"]) : "Munamon";
            // ⭐ 指図 komon[].sode「門の方立と短い板の袖で閉じる」なら袖つきの棟門(EdoAssets.Own.MunamonSode)── 袖の幅 = plan.bayRule の「妻の離し」(第105巡・施主 2026-10-11)。
            //   札の脇の面 jambL/R は方立の外の面 ⇒ 隣の長屋の妻をここへ突き付ける(隙 0【硬】)。当たる先: 長屋の妻の間に立つ小門(岡部 Tsuyomon)
            if (!Has(k, "asset") && (S(Get(k, "sode")) ?? "").Contains("方立と短い板の袖"))
            {
                var mB = System.Text.RegularExpressions.Regex.Match(S(Get(O(Get(k, "plan")), "bayRule")) ?? "", @"妻の離し\s*([0-9.]+)");
                if (mB.Success) assetKey = "MunamonSode(" + w.ToString(System.Globalization.CultureInfo.InvariantCulture) + "," + mB.Groups[1].Value + ")";
                else sb.AppendLine("★ 小門 " + nm + ": sode は板の袖だが plan.bayRule の妻の離しが読めない ── 素の棟門のまま");
            }
            string path = AssetByKey(assetKey, w, 0f);
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
                var gm = EdoBuild.PlaceGamae(go, new List<GameObject>(), eA, eB, nrm, c, Poly, -FaceIn(e, sPos), 0f, 1.0f);   // 門の正面 = 長屋・練塀の外面と同じ線【硬】(const.kidan)
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
                    float shift = -FaceIn(e, sPos) - face;
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
            float fi1 = FaceIn(e1, EdgeLen(e1)), fi2 = FaceIn(e2, 0f);   // 両腕の外面 = 辺ごとの法肩の控え c + 犬走り(const.kidan)
            //   ⭐ 一枚物の練塀の隅は直線の駒(AlignInubashiri)と同じ壁面のメッシュで測り、腕は二等分の線で分ける(第119巡: 腰の笠を外面と読み 0.09 内へ・入隅 P7 は 0.69)
            bool neriK = S(c["part"]) == "Dobei";
            System.Predicate<MeshFilter> pick = neriK ? (System.Predicate<MeshFilter>)(mf => WallFace.Contains(mf.gameObject.name)) : null;
            if (OnHeiLineVertex((int)F(c["vertex"]))) { mv = Vector2.zero; note = null; }   // 芯線の隅は PlaceKado が据える時に面を合わせた ── ⛔ ここで寄せない(腕の実端面だけ測る)
            else if (!EdoBuild.KadoFace(kc, P, e1, OutNormal, -fi1, -fi2, wallT, pick, out mv, out note))
            { notes.Add(id + ": " + note); continue; }
            if (note != null) notes.Add(id + ": " + note);
            worstMove = Mathf.Max(worstMove, mv.magnitude);
            float h, l;
            if (!EdoBuild.KadoArm(kc, P, e1, OutNormal, -Mathf.Max(fi1, fi2), wallT, 0.10f, out h, out l))
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

    /// <summary>**練塀の隅の駒の高さを、両腕に突き付けた直線の駒の底の低い方へ**(第119巡)。隅は直線より先に据わる(腕の端を測るため)ので、
    /// 座は算出物か run の端の座の見込みでしかない ⇒ 直線を据えた後に、腕の先に触れている直線の駒(壁体の外接が 0.3 内)の実の底を測り、隅の底をその低い方へ。
    /// 低い方 = 高い側の腕は根入れで埋まる(浮き0【硬】)・棟の段は低い側の直線と揃う(高い側は継ぎ目の段違い ── 直線どうしの段と同じ)。xz は動かさない。
    /// 硬い(浮き0)。当たる先: 練塀の留めの隅(岡部 Neribei_Kado 25 基)── 一枚物の隅を直線より先に据える邸すべて。</summary>
    static string SeatKadoToRuns(Transform kak) { return SeatKadoToRuns(kak, false); }
    /// <summary><paramref name="lowerOnly"/>: 下げるだけ(床へ据えた後 ── 上げると浮く・3d の地面の後・第119巡)。</summary>
    static string SeatKadoToRuns(Transform kak, bool lowerOnly)
    {
        var kados = new List<Transform>(); var str = new List<Transform>();
        foreach (Transform c in kak) { if (!c.gameObject.activeInHierarchy) continue; if (c.name.StartsWith("Kado_P")) kados.Add(c); else if (c.name.Contains("Hei_") && !c.name.StartsWith("TomeBashira")) str.Add(c); }
        var sbd = new Dictionary<Transform, Bounds>(); foreach (var s in str) sbd[s] = EdoBuild.RB(s.gameObject);
        int moved = 0; float worst = 0f; string worstN = null; var none = new List<string>(); var txt = new List<string>();
        foreach (var k in kados)
        {
            string pth = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(k.gameObject) ?? ""; if (!pth.Contains("Neribei_Kado")) continue;
            if (HeiLineKadoKey(k.name) != null) continue;   // 天端の線の隅は区間の組で座に据えた(SeatHeiOnBed)── ⛔ 外接の箱で隣の区間の先の駒を拾わない
            { int vk; if (k.name.StartsWith("Kado_P") && int.TryParse(k.name.Substring(6), out vk) && OnHeiLineVertex(vk)) continue; }   // domain reload で線が消えた後も(指図の範囲で判じる・第121巡)
            var kb = EdoBuild.RB(k.gameObject); var kx = kb; kx.Expand(new Vector3(0.6f, 0f, 0.6f)); kx.Expand(new Vector3(0f, 20f, 0f));
            float lo = float.NaN;
            foreach (var s in str) { if (!kx.Intersects(sbd[s])) continue; lo = float.IsNaN(lo) ? sbd[s].min.y : Mathf.Min(lo, sbd[s].min.y); }
            if (float.IsNaN(lo)) { none.Add(k.name); continue; }
            float d = lo - kb.min.y; if (lowerOnly && d > 0f) d = 0f;
            if (Mathf.Abs(d) > 0.002f) { k.position += new Vector3(0f, d, 0f); moved++; txt.Add(k.name + " " + d.ToString("+0.00;-0.00")); }
            if (Mathf.Abs(d) > Mathf.Abs(worst)) { worst = d; worstN = k.name; }
        }
        return "隅の駒の底を腕に続く直線の駒の底の低い方へ(SeatKadoToRuns): 動かした " + moved + "・最大 " + worst.ToString("+0.000;-0.000") + (worstN != null ? " @" + worstN : "")
             + (txt.Count > 0 ? "(" + string.Join(" / ", txt.ToArray()) + ")" : "") + (none.Count > 0 ? "・直線の駒が触れない " + string.Join(",", none.ToArray()) : "");
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
        int made = 0, skip = 0, nkKado = 0; EdoBuild.PartTops kStones = null; var miss = new List<string>(); var degWarn = new List<string>(); var armNote = new List<string>(); var seatNote = new List<string>();
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
            // ⭐ 練塀の隅は一枚物の留め(施主裁定 2026-10-12 案1・EDO-0502 第118巡)── Own.NeribeiKado・**実寸 scale 1**(旧 Dobei_Kado は ×ES)。腕の先は断面で塞いである(突き付け)
            bool neri = part == "Dobei";
            float kScale = neri ? 1f : ES;
            //   ⭐ 腰の有無(const.heiLine.koshi【硬】)── 両腕の足の下(折れ点から 1.2 の内)に台の石垣の天端があれば腰なしの隅(EdoBuild.StoneBaseUnder)
            bool kKoshi = true;
            if (neri)
            {
                if (kStones == null) kStones = HeiBaseStones();
                int vk = (((int)F(c["vertex"])) % n + n) % n, eIk = (vk - 1 + n) % n; float LIk = EdgeLen(eIk); int h1, h2;
                Vector2 aIk = EdgePt(eIk, 0f), uIk = (EdgePt(eIk, 1f) - aIk).normalized, aOk = EdgePt(vk, 0f), uOk = (EdgePt(vk, 1f) - aOk).normalized;
                //   座 = その腕に続く練塀の run の座(無ければ問わない)
                System.Func<int, System.Func<float, float>> seatOf = ek => { foreach (var rr in Runs) if (rr.Dobei && rr.edge == ek) { var r2 = rr; return t => r2.SeatAt(Mathf.Clamp(t, r2.s0, r2.s1)); } return null; };
                bool b1 = EdoBuild.StoneBaseUnder(kStones, aIk, uIk, OutNormal(eIk), FaceIn(eIk, LIk), Mathf.Max(0f, LIk - 1.2f), LIk, seatOf(eIk), out h1);
                bool b2 = EdoBuild.StoneBaseUnder(kStones, aOk, uOk, OutNormal(vk), FaceIn(vk, 0f), 0f, Mathf.Min(1.2f, EdgeLen(vk)), seatOf(vk), out h2);
                kKoshi = !(b1 || b2);
                if (!kKoshi) nkKado++;
            }
            string path = neri ? EdoAssets.Own.NeribeiKado(deg, 0f, 0f, kKoshi) : EdoAssets.Own.Kado(part, deg);
            string armArg = "";
            float full, faceDepth;
            if (EdoBuild.KadoGauge(path, out full, out faceDepth))
            {
                string pt = part; Vector2 arms; string an;
                //   ⭐ 辺ごとの控え(FitKado の KadoFace と同じ: 辺 e の頂点 k の側 = FaceIn(e, 端の s))── 据え点は両辺の外面の線の交点(第116巡: 深い方一つで割り P3 が 0.31 ずれた)
                System.Func<int, int, float> fiAt = (e, k) => { int ee = ((e % n) + n) % n, kk = ((k % n) + n) % n; return FaceIn(ee, kk == ee ? 0f : EdgeLen(ee)); };
                bool ok = EdoBuild.KadoArms(P, (int)F(c["vertex"]), k => kadoAt.ContainsKey(k) && kadoAt[k] == pt, OutNormal,
                                            kScale, full, faceDepth, fiAt, C("dobeiT"), 0.05f, neri ? HL_KADO_MINARM : 0.5f,
                                            e => _kadoFreeEnd.ContainsKey(((e % n) + n) % n) ? _kadoFreeEnd[((e % n) + n) % n] : new Vector2(float.NaN, float.NaN), out arms, out an);
                if (an != null) armNote.Add(S(c["id"]) + ": " + an);
                if (!ok) { skip++; continue; }                // 腕が成り立たない隅は据えない(note に出る)
                //   ⭐ 天端の線(const.heiLine.tenba・案1・第121巡)の頂点: 段の面が腕の先 + 棟止めの端の柱の内に入る腕は、
                //   棟止めの端の柱の外面が段の面へ届く所まで詰める(cm を切り上げ ⇒ 柱は段の面を ≤0.01 越えて相手の柱へ埋まる)・腕ごとに勾配を持つ坂の隅の駒(NeribeiKadoSaka)。
                //   当たる先: 天端の線の上の練塀の隅すべて(岡部 25 基)。
                int vtx = (((int)F(c["vertex"])) % n + n) % n; float gIn = 0f, gOut = 0f;
                if (neri && OnHeiLineVertex(vtx) && ProfileOfEdge(vtx) != null && ProfileOfEdge((vtx - 1 + n) % n) == ProfileOfEdge(vtx))
                {
                    var pf = ProfileOfEdge(vtx); int eI = (vtx - 1 + n) % n; float tF = pf.tStart[vtx];
                    gIn = Mathf.Round(pf.Grade(tF, -1) * 10000f) / 10000f; gOut = Mathf.Round(pf.Grade(tF, +1) * 10000f) / 10000f;
                    float post, tbody; EdoBuild.NeribeiTomeGauge(out post, out tbody);
                    foreach (var st in _hlSteps)
                    {
                        if (st.edge % n == eI) { float dist = pf.sCend[eI] - st.s; if (dist > 0f && dist < arms.x + post + 0.005f) { float a2 = Mathf.Ceil((dist - post) * 100f - 1e-3f) / 100f; armNote.Add(S(c["id"]) + " 入りの腕 " + arms.x.ToString("F2") + "→" + a2.ToString("F2") + "(段の面 辺" + eI + " s" + st.s.ToString("F2") + " まで 折れ点から " + dist.ToString("F3") + ")"); arms.x = a2; } }
                        if (st.edge % n == vtx) { float dist = st.s - pf.sC[vtx]; if (dist > 0f && dist < arms.y + post + 0.005f) { float a2 = Mathf.Ceil((dist - post) * 100f - 1e-3f) / 100f; armNote.Add(S(c["id"]) + " 出の腕 " + arms.y.ToString("F2") + "→" + a2.ToString("F2") + "(段の面 辺" + vtx + " s" + st.s.ToString("F2") + " まで 折れ点から " + dist.ToString("F3") + ")"); arms.y = a2; } }
                    }
                }
                path = neri ? (gIn != 0f || gOut != 0f ? EdoAssets.Own.NeribeiKadoSaka(deg, gIn, gOut, arms.x, arms.y, kKoshi) : EdoAssets.Own.NeribeiKado(deg, arms.x, arms.y, kKoshi)) : EdoAssets.Own.Kado(part, deg, arms.x, arms.y, full);
                if (arms.x < full - 1e-3f || arms.y < full - 1e-3f)
                    armArg = " --arms " + arms.x.ToString("0.00") + "," + arms.y.ToString("0.00");
                if (gIn != 0f || gOut != 0f) armArg += " --grade " + (gIn * 100f).ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + "," + (gOut * 100f).ToString("0.##", System.Globalization.CultureInfo.InvariantCulture);
            }
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            // ⛔ 指図が名指す練塀の隅の駒(runs の join0 / kadoEnd「= Dobei_Kado_…」)は、算出の腕の版が無くても代わりに据えない(第114巡: A226x50・Dobei_Kado_90 の腕 4.1m が
            //   3.0〜3.8m の辺を越えて長屋 N41_5・P4 の隅へ入った)── 算出の版を部材方へ(下の ★ 部材が無い)。
            if (src == null)
            {
                miss.Add(S(c["id"]) + " → " + path
                       + (neri ? "(blender --background --python Tools/Blender/build_neribei.py --" + (kKoshi ? "" : " --no-koshi") + " --kado " + (Mathf.RoundToInt(Mathf.Abs(deg)) == 0 ? (deg < 0f ? "0M" : "0") : (deg < 0f ? "-" : "") + Mathf.RoundToInt(Mathf.Abs(deg))) + armArg + ")"
                               : "(blender --background --python Tools/Blender/build_kado.py -- --part " + part.ToLowerInvariant() + " --deg " + Mathf.RoundToInt(deg) + armArg + ")"));
                continue;
            }
            int v = (int)F(c["vertex"]);
            Vector2 b = P[v % n], a = P[(v - 1 + n) % n];
            Vector2 dIn = (b - a).normalized;                  // 入りの run の走り
            float seat = Has(c, "seat") ? F(c["seat"]) : F(c["seatIn"]);
            //   ⭐ 練塀の隅の座 = 両腕に続く練塀の run の座(SolveSeatRules が今の地形で解いた値)の低い方(第119巡: 算出物の座は前の地形で焼いた値で、
            //   P3 は隣の直線より 1.14 低く・P7 は 0.08 高く据わり棟が隅で 1m 段になった/足が 0.45 浮いた)。低い方 = 高い側の腕は根入れで埋まる(浮き0【硬】)。
            //   run が無い腕(長屋・留め柱)は算出物の座のまま。当たる先: 練塀の留めの隅すべて(岡部 25 基)。
            if (neri)
            {
                int e1k = (v - 1 + n) % n, e2k = v % n; float sMin = float.NaN;
                foreach (var r in Runs)
                {
                    if (!r.Dobei) continue; float sv;
                    if (r.edge == e1k && r.s1 >= EdgeLen(e1k) - 1.5f) sv = r.SeatAt(r.s1);
                    else if (r.edge == e2k && r.s0 <= 1.5f) sv = r.SeatAt(r.s0);
                    else continue;
                    if (!float.IsNaN(sv)) sMin = float.IsNaN(sMin) ? sv : Mathf.Min(sMin, sv);
                }
                if (!float.IsNaN(sMin)) { if (Mathf.Abs(sMin - seat) > 0.005f) seatNote.Add(S(c["id"]) + " " + seat.ToString("F2") + "→" + sMin.ToString("F2")); seat = sMin; }
            }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src, parent);
            Undo.RegisterCreatedObjectUndo(go, "kado");
            go.name = "Kado_" + S(c["id"]);
            go.transform.position = new Vector3(b.x, seat - 0.10f, b.y);
            go.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(dIn.x, dIn.y) * Mathf.Rad2Deg, 0);
            go.transform.localScale = Vector3.one * kScale;
            //   ⭐ 芯線(const.heiLine)の頂点の隅は**据える時に**外面を一続きの控え d の線へ(実メッシュの壁面 WallFace・EdoBuild.KadoFace)── ⛔ 後で FitKado で寄せない(第120巡)
            if (neri && OnHeiLineVertex(v))
            {
                int e1k = (v - 1 + n) % n; Vector2 mvK; string ntK;
                if (!EdoBuild.KadoFace(go.transform, P, e1k, OutNormal, -FaceIn(e1k, EdgeLen(e1k)), -FaceIn(v % n, 0f), C("dobeiT"), mf => WallFace.Contains(mf.gameObject.name), out mvK, out ntK))
                    seatNote.Add(S(c["id"]) + " ★ 芯線の外面で据えられない(" + ntK + ")");
                else if (ntK != null) seatNote.Add(S(c["id"]) + " " + ntK);
            }
            made++;
        }
        var sb = new System.Text.StringBuilder("隅部材: " + made + " 基(留め継ぎでない/次巡 " + skip + "・腰なし " + nkKado + ")");
        if (degWarn.Count > 0)
            sb.Append("\n★ 折れ角が算出物と食い違う " + degWarn.Count
                    + " 件(区画の実測で建てた — `python3 Tools/Sashizu/bake_impl.py okabe --write` で欄を焼き直すこと EDO-0386) — "
                    + string.Join(" / ", degWarn.ToArray()));
        if (miss.Count > 0)
            sb.Append("\n★ 部材が無い " + miss.Count + " 件 — " + string.Join(" / ", miss.ToArray()));
        if (armNote.Count > 0)
            sb.Append("\n★ 隅の腕 " + armNote.Count + " 件 — " + string.Join(" / ", armNote.ToArray()));
        if (seatNote.Count > 0)
            sb.Append("\n  隅の座を両腕の run の座の低い方へ " + seatNote.Count + " 基(算出物の座 → run): " + string.Join(" / ", seatNote.ToArray()));
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
        float target = -INUBASHIRI;   // 基壇の無い辺の既定(run ごとは下で FaceIn)
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
            if (OnHeiLine(r)) continue;   // ⭐ 天端の線・芯線の run は据える時に外面を線へ合わせた(NeribeiPanelRun の faceIn)── ⛔ 後で寄せない
            target = -FaceIn(r.edge, (r.s0 + r.s1) * 0.5f);   // 外面 = 法肩の控え c + 犬走り(const.kidan・run ごと)
            Vector2 nrm = OutNormal(r.edge);
            var a = P[r.edge % P.Length];
            System.Func<float> measure = () => EdoBuild.FaceOut(c.gameObject, a, nrm, float.MinValue, float.MaxValue, pickWall);
            float best = measure();
            if (float.IsNaN(best)) continue;
            seen++;
            float shift = target - best;
            if (Mathf.Abs(shift) > Mathf.Abs(worst)) { worst = shift; worstName = c.name; }
            if (Mathf.Abs(shift) > 0.02f)
            { c.position += new Vector3(nrm.x * shift, 0f, nrm.y * shift); moved++; }
            // ⭐ **寄せた後にもう一度測る**(残差)。⛔ 「寄せ量」を残差と読み違えない —
            //   寄せ量が大きいのは元が外れていただけで、直ったかどうかは残差でしか分からない。
            float after = measure();
            if (!float.IsNaN(after))
            { float rr = Mathf.Abs(after - target); if (rr > resid) { resid = rr; residName = c.name; } }
        }
        // ⭐ 腰の外面を法肩の線へ(runs[].face「練塀の腰の外面は基壇の法肩と同じ線【硬: 法肩より外へ出さない】・犬走り 0」・第114巡)── 壁面で寄せると腰の裾(壁面の 0.1〜0.15 外)が
        //   法肩の外へ出て、床(基壇の天端)を外し地表へ 0.6 沈んだ。壁面で寄せた後、表裏の f/b を一組にして腰の帯(駒の底 〜 +0.7)の全メッシュの最も外を法肩へ寄せ直す(組の中の並びは保つ)。
        //   当たる先: 犬走り 0 の run(いまは岡部 S_Hei_01/01b)。
        string koshiNote = ""; var doneK = new HashSet<string>();
        for (int i = 0; i < kak.childCount; i++)
        {
            var c = kak.GetChild(i); int ri = -1;
            for (int k = 0; k < Runs.Length; k++) if (c.name.StartsWith(Runs[k].name) && (ri < 0 || Runs[k].name.Length > Runs[ri].name.Length)) ri = k;
            if (ri < 0 || !Runs[ri].Dobei) continue; var r = Runs[ri];
            if (RunInu(r.edge, (r.s0 + r.s1) * 0.5f) != 0f) continue;
            string key = (c.name.EndsWith("f") || c.name.EndsWith("b")) ? c.name.Substring(0, c.name.Length - 1) : c.name; if (!doneK.Add(key)) continue;
            var pair = new List<Transform>(); foreach (var sfx in new[] { "", "f", "b" }) { var t = kak.Find(key + sfx); if (t != null && !pair.Contains(t)) pair.Add(t); }
            Vector2 nrm = OutNormal(r.edge); var a = P[r.edge % P.Length]; float tgt = -FaceIn(r.edge, (r.s0 + r.s1) * 0.5f), mx = float.NaN;
            foreach (var t in pair) { float yb = EdoBuild.RB(t.gameObject).min.y, m0 = EdoBuild.FaceOut(t.gameObject, a, nrm, yb - 0.01f, yb + 0.7f); if (!float.IsNaN(m0)) mx = float.IsNaN(mx) ? m0 : Mathf.Max(mx, m0); }
            if (float.IsNaN(mx)) continue; float sh = tgt - mx;
            foreach (var t in pair) t.position += new Vector3(nrm.x * sh, 0f, nrm.y * sh);
            koshiNote += key + " " + sh.ToString("+0.000;-0.000") + " ";
        }
        return (koshiNote.Length > 0 ? "腰の外面を法肩の線へ寄せた(犬走り 0 の run・表裏一組): " + koshiNote + "\n" : "") + "犬走りへ寄せた: " + moved + " / " + seen + " 駒(最大の寄せ "
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

    public static string Stage2b_Dan() { using (OnKita()) return Stage2b_Dan_(); }
    static string Stage2b_Dan_()
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
        var deferBack = new List<BackOfFull>();   // 背の台の石垣を棟の背の全長に(backOf<棟> 追記 2026-10-10o)── 網の直前に端を解く
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
        // ⭐ 背の路地(grading.seRoji)と TW_Higashi_Se(第106巡)── 長屋の実メッシュの背から解き、路地の床を地形へ切る(切るだけ)。線は下の欄の据えへ渡す
        _seRoji = SeRojiPlanOf(); string seWall = SeRojiWallName();
        if (_seRoji.ok)
        {
            sb.Append("  " + _seRoji.log.Replace("\n", "\n  ").TrimEnd(' '));
            int cnT = 0; float cmT = 0f, cvT = 0f;
            foreach (var f in _seRoji.faces)
            {
                // 面の矩形 = [背 −0.3, 足元 +0.3] × 0.5m ── 切りは背の線から帯の幅だけ(帯の奥は 1:0.1 で地山へ)
                Vector2 a = f.poly[0], b = f.poly[1], inw = (f.poly[3] - f.poly[0]); float band = inw.magnitude; inw /= Mathf.Max(1e-4f, band);
                float cm1, cv1; cnT += EdoBuild.CutAlongBack(Poly, a, b, inw, f.y, band, 0.1f, out cm1, out cv1); cmT = Mathf.Max(cmT, cm1); cvT += cv1;
            }
            AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
            sb.AppendLine("  背の路地の床を地形で切った: 面 " + _seRoji.faces.Count + "・節点 " + cnT + "・切り 最大 " + cmT.ToString("F2") + "m・" + cvT.ToString("F0") + "m³(2m 格子は床を描けない ── 皮が面で描く)");
            sb.Append(SeRojiSouthExtend(_seRoji));
            sb.Append(SeRojiHeiFoot());
            sb.Append(SeRojiNiwaFill(_seRoji));
            // 線の外を造成前へ戻すのは床の延長と帯の後(seRoji.clipOrder【硬】・第114巡)
            if (EdoBuild.TerrainCell(EdoBuild.T()) < 1f) sb.AppendLine(RestorePerimeterSpill_(2.0f, true));
        }
        else sb.AppendLine("  ★ 背の路地が解けない: " + _seRoji.why + " ── " + (seWall ?? "TW_Higashi_Se") + " を建てない");
        foreach (var o in tws)
        {
            var w = O(o); if (w == null) continue;
            string nm = S(Get(w, "name")); string part = S(Get(w, "part"));
            var ln = A(Get(w, "line"));
            Func<Vector2, Vector2, Vector2> seFace = null;
            if ((ln == null || ln.Count < 2) && nm == seWall && _seRoji.ok)
            {   // 算出物は線を持たない(座標は書かない ── 指図 line)⇒ 解いた線・天端・口で欄を組み直して下の据えへ(野面・fill・段は節点で)
                var w2 = new Dictionary<string, object>(w); var ln2 = new List<object>(); foreach (var q in _seRoji.nodes) ln2.Add(new List<object> { (double)q.x, (double)q.y });
                var tl2 = new List<object>(); foreach (var t in _seRoji.tops) tl2.Add((double)t);
                w2["line"] = ln2; w2["tops"] = tl2; w2["top"] = (double)_seRoji.tops[0]; w2["mode"] = "fill"; w2["stepped"] = true; w2["kind"] = "石垣 野面"; w2.Remove("unresolved");
                var gl2 = new List<object>(); if (!float.IsNaN(_seRoji.gap.x)) gl2.Add(new Dictionary<string, object> { { "s0", (double)_seRoji.gap.x }, { "s1", (double)_seRoji.gap.y }, { "by", "K_Tsuyo" } });
                w2["gaps"] = gl2; w = w2; ln = ln2;
                var spl = _seRoji; seFace = (pa, pb) => { Vector2 mid = (pa + pb) * 0.5f; float d40 = Vector2.Dot(mid - spl.ea40, spl.yd40), d41 = Vector2.Dot(mid - spl.ea41, spl.yd41); return d41 > d40 ? -spl.yd40 : -spl.yd41; };
            }
            if ((ln == null || ln.Count < 2) && nm == "TW_Higashi_Minami" && _seRoji != null && _seRoji.ok)
            {
                string why; var w3 = MinamiWallOf(w, out why); sb.Append(why);
                if (w3 == null) { skipped++; continue; }
                w = w3; ln = A(Get(w, "line"));
                var spm = _seRoji; var fM = (Vector2)w3["_face"]; seFace = (pa, pb) => fM;
            }
            if (ln == null || ln.Count < 2) { skipped++; sb.AppendLine("  " + nm + (part != null ? "(" + part + ")" : "") + ": line=null ── 建てない(" + (S(Get(w, "unresolved")) ?? "線が無い") + ")"); continue; }
            var nodes = new List<Vector2>(); foreach (var q in ln) { var p = A(q); nodes.Add(new Vector2(F(p[0]), F(p[1]))); }
            var tops = new List<float>();
            var tl = A(Get(w, "tops"));
            for (int i = 0; i < nodes.Count; i++) tops.Add(tl != null && i < tl.Count ? F(tl[i]) : F(Get(w, "top")));
            // ⭐ 線の先が長屋の背へ入り込むなら背から一間離して返し、高い側の妻の線で背まで閉じる(指図 terraceWalls[].return<run>・end・backOf<run>
            //   ── EDO-0502 第19巡)。溝は相手の面まで切る(地形 = CutAlongBack・皮の設計の地盤 = Stage3b が同じ BackTrenches を読む)。据えより先に。
            Func<Vector2, Vector2, Vector2> trenchHint = seFace;
            foreach (var tr in trenches)
            {
                if (tr.wall != nm) continue;
                if (tr.standalone)
                {   // 別の棟の背の返し(return<棟>・第78巡)── 本線の節点は替えず、溝を切り、返しの区間を野面で足す(天端は本線と同じ一直線)
                    float cm2, cv2; int cn2 = EdoBuild.CutAlongBack(Poly, tr.stop, tr.far + tr.along * tr.off, tr.yard, tr.y, tr.off, 0.1f, out cm2, out cv2);
                    AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
                    float tS = tops[0];
                    for (int k = 0; k + 1 < tr.nodes.Count; k++)
                    { Vector2 fa = tr.nodes[k], fb = tr.nodes[k + 1]; Vector2 dd = (fb - fa).normalized; Vector2 nrm = new Vector2(-dd.y, dd.x); Vector2 ctr = (tr.stop + tr.far) * 0.5f + tr.yard * (tr.off * 0.5f);
                      Vector2 fc = Vector2.Dot(ctr - (fa + fb) * 0.5f, nrm) >= 0f ? nrm : -nrm;   // 見え面 = 溝の側
                      nozSegs.Add(new EdoBuild.NozuraSeg { name = nm + "_R" + tr.run + "_" + k, a = fa, b = fb, crestAt = sl => tS, face = fc }); }
                    sb.AppendLine("    返し " + nm + "_R" + tr.run + ": 区間 " + (tr.nodes.Count - 1) + "・天端 " + tS.ToString("F2") + "・溝を地形で " + tr.y.ToString("F2") + " まで切った 節点 " + cn2);
                    continue;
                }
                nodes.Clear(); nodes.AddRange(tr.nodes);
                float t0 = tops[0]; tops.Clear(); for (int k = 0; k < nodes.Count; k++) tops.Add(t0);
                float cm, cv; int cn = EdoBuild.CutAlongBack(Poly, tr.stop, tr.far + tr.along * tr.off, tr.yard, tr.y, tr.off, 0.1f, out cm, out cv);
                AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
                sb.AppendLine("    溝(返しと " + tr.run + " の背の間)を地形で " + tr.y.ToString("F2") + " まで切った: 節点 " + cn + "・切り 最大 " + cm.ToString("F2") + "m・" + cv.ToString("F0") + "m³(2m 格子は溝を描けない ── 皮が設計の地盤で描く)");
                {   // 指図 terraceWalls[].backOf<棟> 追記 2026-10-10n【硬】(第96巡): 棟の背の台の石垣を野面で建てる・天端 y 一直線・法尻は溝の底 ──
                    //   線 = 棟の背の面(BackTrench の stop → far ・実メッシュの背の面)・見え面 = 溝の側(yard)・天端の前の線を背の面に。当たる先: backOf<棟> に 10-10n の台の石垣を持つ欄(岡部 TW_Kado_Hokuto × N39_1)
                    string bo = ""; foreach (var oD in A(Get(D, "terraceWalls")) ?? new List<object>()) { var tD = O(oD); if (tD != null && S(Get(tD, "name")) == nm) bo = S(Get(tD, "backOf" + tr.run)) ?? ""; } int i10n = bo.IndexOf("追記 2026-10-10n"); string bt = i10n < 0 ? "" : bo.Substring(i10n);
                    var mC = System.Text.RegularExpressions.Regex.Match(bt, @"台の石垣を野面で建てる。天端\s*([0-9.]+)\s*一直線"); var mT = System.Text.RegularExpressions.Regex.Match(bt, @"法尻は溝の底\s*([0-9.]+)");
                    if (mC.Success && mT.Success)
                    {
                        var inv2 = System.Globalization.CultureInfo.InvariantCulture; float cB = float.Parse(mC.Groups[1].Value, inv2), fB = float.Parse(mT.Groups[1].Value, inv2);
                        var trb = tr; var boSeg = new EdoBuild.NozuraSeg { name = nm + "_BackOf" + tr.run + "_0", a = tr.stop, b = tr.far, crestAt = sl => cB, footAt = (x, z) => fB, face = trb.yard };
                        int i10o = bo.IndexOf("追記 2026-10-10o");
                        if (i10o >= 0 && bo.Substring(i10o).Contains("の背の全長に通す")) deferBack.Add(new BackOfFull { tr = tr, seg = boSeg, txt = bo.Substring(i10o), crest = cB });   // 端は網の直前に解く(BackOfFullLine)
                        else nozSegs.Add(boSeg);
                        sb.AppendLine("    " + tr.run + " の背の台の石垣(backOf" + tr.run + " 追記 2026-10-10n【硬】): 野面・天端 " + cB.ToString("F2", inv2) + " 一直線・法尻 = 溝の底 " + fB.ToString("F2", inv2) + "・線 = 背の面 " + Vector2.Distance(tr.stop, tr.far).ToString("F2", inv2) + "m・見え面 = 溝の側");
                    }
                    else if (i10n >= 0) sb.AppendLine("    ★ backOf" + tr.run + " 追記 2026-10-10n: 天端・法尻が読めない ── 建てない");
                }
                // 低い側: 返しと妻の閉じは溝の側(両側が地形で同じ高さに読めるので地表で決めない)・元の線は地表で測る
                var trc = tr; trenchHint = (pa, pb) =>
                {
                    Vector2 mid = (pa + pb) * 0.5f, ctr = (trc.stop + trc.far) * 0.5f + trc.yard * (trc.off * 0.5f);
                    // 溝に面する区間 = 中ほどが溝の帯(背 −0.5 〜 背から off + 0.3・止めの妻 −0.5 〜 反対の妻 + off + 0.5)の内(⛔ 溝の芯からの距離の円で篩わない ──
                    //   棟を 0.26 寄せて溝が動くと、円が返しに継ぐ郭の側の本線 TW_Kado_Hokuto_0_1 の区間まで入り、見え面を溝へ裏返して 0_1 × 1_0 の入隅の見立てが割れ、
                    //   急な土の面 77 → 162(EDO-0502 第95巡)。当たる先: return<棟> の溝を持つ段の土留めすべて(岡部 TW_Kado_Hokuto × N39_1)
                    float sT = Vector2.Dot(mid - trc.stop, trc.along), dT = Vector2.Dot(mid - trc.stop, trc.yard), LT = Vector2.Dot(trc.far - trc.stop, trc.along);
                    if (sT >= -0.5f && sT <= LT + trc.off + 0.5f && dT >= -0.5f && dT <= trc.off + 0.3f) return (ctr - mid).normalized;
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
                    bool stepped = S(Get(w, "mode")) == "sode" || Get(w, "stepped") != null;
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
        foreach (var kv in sodeB) if (kv.Key.EndsWith("#land") && kv.Key != "sideEnd#land") foreach (var pr in kv.Value) benchAll.Add(pr.Value);
        // ⭐ sideEnd の延長の背の小段は StairGaps(上の据え)が解き直した今の物を地形へ ── sodeB は StairGaps より先に読むので前の巡の(domain reload の後は空の)
        //   小段を持ち、地形を切らずに皮だけが小段を描いて皮の縁(地形のまま)に高さ 0.7・71° の崖が立った(第80巡)
        foreach (var bk in _sideEndBenches) benchAll.Add(bk);
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
        sb.Append(RoadEdgeSegs(nozSegs));   // 指図 Kadonouchi.roadEdge(道の側の腰石垣・第82巡)
        if (_seRoji != null && _seRoji.ok && seWall != null)
        {   // TW_Higashi_Se の見え面の足元 = 背の路地の床(⛔ 前の巡の皮で測らない ── 床は皮の前に切ったばかり)。口の脇の返しは StairGaps の足元のまま
            var spl = _seRoji; int nf = 0;
            foreach (var sg in nozSegs) if (sg.name.StartsWith(seWall + "_") && sg.footAt == null) { sg.footAt = (x, z) => { float y = spl.At(new Vector2(x, z)); return float.IsNaN(y) ? SkinGround(x, z) : y; }; nf++; }
            sb.AppendLine("  " + seWall + ": 足元 = 背の路地の床 区間 " + nf);
        }
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
            endRule.koshi = nm0 => (nm0.StartsWith("TW_Kita_Koshi") || nm0.StartsWith("TW_Nishi_Kado"))   // TW_Higashi_Minami は石垣 野面へ(施主裁定 2026-10-12 案A・nozuraEndRule の koshiEnd から外れた・第119巡)
                                     && !toeWalls.Exists(w0 => nm0.StartsWith(w0 + "_"))
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
                        // 指図 ends 追記 2026-10-10p(10-10o を置き換え)の端の型は当てない(第100巡): 「始まり(外周の隅 Kado_P24 の側)は ② の隅の返し」と「終わりは積み止め tome1 を戻し endKado の通り」が
                        //   同じ端(Kado_P24 は辺24 の南の端 = 辺24_1_0 の端1 = endKado の積み止めの端)を名指す ⇒ 欄どうしの矛盾として普請方へ戻した。端は第99巡のまま(北 ④・南 積み止め)。
                        // 旧注(第97巡): 指図 ends 追記 2026-10-10o「辺24 の run は、前の地表が天端 −0.15 に届いた所で終える(④→①)・今の tome1 は退ける」【硬】は当てない(第97巡で一度流して戻した):
                        //   設計の地盤(SkinGround・前 0.6)では両端とも前の地表が天端 −0.15 に届かず(縮めは TrimRunsBelowFront が刷る)、積み止めを退けると終わりの端が
                        //   見付 2.33 の直線の駒の小口(③⛔ ── nozuraEndRule【硬】に反する)、始まりは ④ を止めると ② の隅の返しになった。欄どうしの矛盾 ⇒ 普請方へ戻す(EDO-0502 第97巡)。
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
            // ⭐ 指図 sideEnd・sodeSlope 追記 2026-10-10d【硬】: 平らの帯の中・天端が前の地表より低い所に駒を置かない(打ち切りの駒の先に足さない)── 欄がこの文を持つ run だけ。
            //   前の地表 = 前 0.6 の点が平らな面の輪郭の内なら面の高さ・外なら皮の地表(SkinGround)。置き方は EdoBuild.TrimSegBelowFront(第87巡)。
            sb.Append(TrimRunsBelowFront(nozSegs));
            {   // const.abutOrder【硬】(第90巡): 隅の駒 → 本線 → 返し・袖・端 ── 返し(Kaeshi)・袖(sodeSlope の欄)・端(End・SideEnd)の区間を後(可動側)に
                string ao = S(Get(O(D["const"]), "abutOrder"));
                if (ao != null && ao.Contains("返し・袖・端"))
                {
                    var sodeN = new List<string>(); foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (S(Get(t2, "sodeSlope")) != null) sodeN.Add(S(Get(t2, "name")) + "_"); }
                    // ⚠ ends 追記 2026-10-10p「野面の本線(石段の背)は脇の石垣の見え面に入隅で突き付け、脇は本線の背の側へ控え +0.3 以上通す」は当てない(第100巡で一度流して戻した):
                    //   K_Tsuyo の口が本線 5.4m のうち [0.28, 5.17] を切り、本線は両端に 0.28m しか残らない ⇒ 脇(End)の通しの駒が石段の脇の返し(Side0/1)と 0.28 離れて並び、
                    //   被り 220→494・継ぎ目の口から土 259→385(TW_Higashi_Tsuyo_0_0 136・Side1_0 78・End1 の通し 175)。脇の延長の背の納めは普請方へ戻した。
                    System.Func<EdoBuild.NozuraSeg, int> rk = sg => (sg.name.Contains("_Kaeshi") || sg.name.Contains("_End") || sodeN.Exists(x => sg.name.StartsWith(x))) ? 2 : 1;
                    // 追記 2026-10-10o【硬】: 入隅は先に据える壁を角の点から後の壁の背の側へ『後の壁の控え+c』以上通して止める(EdoBuild.ApplyAbutOrder の passClear)
                    float passC = float.NaN; int i10o = ao.IndexOf("追記 2026-10-10o");
                    if (i10o >= 0) { var mP = System.Text.RegularExpressions.Regex.Match(ao.Substring(i10o), @"後の壁の控え\s*\+\s*([0-9.]+)』?\s*以上通して止める"); if (mP.Success) passC = float.Parse(mP.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture); else sb.AppendLine("  ★ const.abutOrder 追記 2026-10-10o の「後の壁の控え+c 以上通して止める」が読めない ── 入隅を通さない"); }
                    var aoLog = new System.Text.StringBuilder(); int na = EdoBuild.ApplyAbutOrder(nozSegs, rk, 1.5f, aoLog, passC);   // 1.5 = 据える側の ③ の「近くの駒」と同じ離れ
                    sb.AppendLine("  据える順(const.abutOrder【硬】): 返し・袖・端を本線の見え面へ突き付ける側にした区間 " + na + (float.IsNaN(passC) ? "" : "・入隅の通す側は角から後の壁の控え + " + passC.ToString("F2") + " 以上通す(10-10o)")); sb.Append(aoLog);
                }
            }
            sb.Append(TrimRunsToPartners(nozSegs));
            sb.Append(CutEndsMikiri(nozSegs));
            {   // 指図 roadEdge・cuts 追記 2026-10-10h【硬】: 見切り石の背の土は頭より下げる(皮が下げる)── 背の土が頭より高くても見切り石を退けない
                bool cutSoil = false; var all3 = new List<object>(A(Get(D, "terraces")) ?? new List<object>()); all3.AddRange(A(Get(D, "terraceWalls")) ?? new List<object>()); foreach (var o3 in all3) { var t3 = O(o3); foreach (var key3 in new[] { "roadEdge", "cuts" }) { string tx3 = S(Get(t3, key3)) ?? ""; if (tx3.Contains("追記 2026-10-10h") && tx3.Contains("見切り石の背の土")) cutSoil = true; } }
                EdoBuild.MikiriBackSoilCut = cutSoil;
            }
            sb.Append(BackOfFullLine(deferBack, nozSegs));   // 背の台の石垣の両端(backOf<棟> 10-10o)── 区間の最後に足す(相手の鎖が先に据わる)
            sb.Append(SodesBeforeNet(grp, nozSegs, poolN));   // 段石 → 袖 → 本線(cuts 10-10o)── 袖を網の前に据え、口の両端の本線を袖の外の面へ
            var got = EdoBuild.PlaceNozuraNet(nozSegs, SkinGround, SkinGround, 1.2f, grp,
                (h, g, i) => EdoAssets.Own.Nozura2(h, g, i), (h, i) => EdoAssets.Own.SannoNozuraKado(h, i),   // 直線の駒は重ねの端の版(EDO-0502 第104巡・継ぎ目の隙と段差)
                (up, i) => EdoAssets.Own.SannoNozuraDan(up, i), (up, i) => EdoAssets.Own.SannoNozuraKiri(up, i),
                EdoAssets.Own.SannoNozuraMikiriH, heights, poolN, log, null, EdoAssets.Own.SannoNozuraNoriEnd,   // 入隅の可動側の端は小口を相手の法で切った駒(型は EdoBuild・EDO-0502 第16巡)
                null, endRule); EdoBuild.MikiriBackSoilCut = false;
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
        { var gw = new List<string>(); sb.Append(PlaceGateSteps(gw)); foreach (var x in gw) sb.AppendLine("    ★ " + x); }   // 指図 roadEdge の門の口の踏み段(第82巡)
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
    public class BackTrench { public string wall, run; public List<Vector2> nodes; public Vector2 stop, far, yard, along; public float off, y; public bool standalone;
        /// <summary>溝の前の縁 ── 背の面から道の側へ出す量(既定 0.30)。指図 return<棟> 追記 2026-10-10k「溝の前の縁は <棟> の背の線で止め」【硬】なら 0。</summary>
        public float front = 0.30f;
        /// <summary>皮の面(溝の矩形)を止めの端から手前へ延ばす量(roadEdge 追記 2026-10-10k: 妻の面の石垣の天端の前の線まで)。地形の切り・石垣の線には効かない。</summary>
        public float pre; }

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
                bool standalone = false;
                if (nn == null)
                {
                    // ⭐ 線が背の帯へ入らない棟(指図 return<棟>「端は <別の棟> の側で return<別の棟> の返しに入隅で継いで閉じる」・第78巡 岡部 returnN39_0)──
                    //   背から off の線を棟の背の長さだけ通し、相手の返し(先に解いた溝の X→P0)の線との交わりから始め、反対の妻で背まで閉じる。returnN39_1 と同じ型の続き。
                    string rv = S(kvR.Value); var mJ = System.Text.RegularExpressions.Regex.Match(rv ?? "", @"(N[0-9_]+)\s*の側で\s*return(N[0-9_]+)\s*の返しに入隅で継いで閉じる");
                    var mate = mJ.Success ? res.Find(x => x.wall == nm && x.run == mJ.Groups[2].Value) : null;
                    var mM = System.Text.RegularExpressions.Regex.Match(rv ?? "", @"背から\s*([0-9.]+)\s*以上離す");
                    if (mate == null) { if (sb != null && mJ.Success) sb.AppendLine("    ⚠ " + nm + " × " + rn + ": 継ぐ相手の返し return" + mJ.Groups[2].Value + " が先に解けていない ── 返さない"); continue; }
                    // 相手の返しの線(X → P0)= mate.nodes の P0 の前後
                    int iP0 = mate.nodes.Count - 2; Vector2 mX = mate.nodes[iP0 - 1], mP0 = mate.nodes[iP0];
                    Vector2 bNear = Vector2.Distance(b0, mP0) <= Vector2.Distance(b1, mP0) ? b0 : b1, bFar2 = bNear == b0 ? b1 : b0;
                    Vector2 u0 = (bFar2 - bNear).normalized, o0 = bNear + yard * off, dm = (mP0 - mX).normalized;
                    float det = u0.x * dm.y - u0.y * dm.x;
                    if (Mathf.Abs(det) < 1e-3f)
                    {   // 同じ辺に並ぶ棟(背が一直線)── 相手の返しをそのまま反対の妻まで通し、相手の妻の閉じを外してこの棟の反対の妻で閉じる(一直線・途中に土の口なし)
                        float offL = Mathf.Abs(Vector2.Dot(o0 - mP0, new Vector2(-dm.y, dm.x)));
                        if (offL > 0.3f) { if (sb != null) sb.AppendLine("    ⚠ " + nm + " × " + rn + ": 相手の返しと平行だが一直線でない(" + offL.ToString("F2") + "m)── 返さない"); continue; }
                        // ⛔ 第78巡: この棟は両妻とも設計の地盤 16.50(門の内と同じ高さ)── 溝を「法尻 = 郭の面 13.10」まで切ると棟の背に 3.4 の穴が開き、
                        //   駒も 3.2 浮いた(普請方へ返す: N39_0 の背の溝の底の高さと、返しの見付)。底が読めるまで返さない。
                        if (Mathf.Min(g0, g1) > S2F(Get(w, "lo")) + 1f) { if (sb != null) sb.AppendLine("    ⛔ " + nm + " × " + rn + ": 棟の地盤 " + Mathf.Min(g0, g1).ToString("F2") + " が溝の底(郭の面)より 1m 超え高い ── 溝の底の高さが指図に無い(普請方へ)── 返さない"); continue; }
                        Vector2 oldStop = mate.nodes[mate.nodes.Count - 1];
                        mate.nodes[iP0] = bFar2 + yard * off; mate.nodes[mate.nodes.Count - 1] = bFar2;
                        if (sb != null) sb.AppendLine("    " + nm + " × " + rn + "(return" + rn + "): 背が return" + mJ.Groups[2].Value + " と一直線 ── 返しを反対の妻まで " + Vector2.Distance(mX, bFar2 + yard * off).ToString("F2") + "m 通し、妻で背まで閉じる(" + mJ.Groups[2].Value + " の妻の閉じ (" + oldStop.x.ToString("F1") + "," + oldStop.y.ToString("F1") + ") は外した)");
                        nn = new List<Vector2>(); standalone = true; bStop = bNear; tFar = bFar2;
                        string loN2 = S(Get(w, "lo")); float loY2 = float.NaN; foreach (var o3 in A(D["terraces"]) ?? new List<object>()) { var t3 = O(o3); if (t3 != null && S(Get(t3, "name")) == loN2) loY2 = F(Get(t3, "y")); }
                        if (!float.IsNaN(loY2)) res.Add(new BackTrench { wall = nm, run = rn, nodes = nn, stop = bStop, far = tFar, yard = yard, along = (tFar - bStop).normalized, off = off, y = loY2, standalone = true });
                        continue;
                    }
                    Vector2 dlt = mX - o0; float ta = (dlt.x * dm.y - dlt.y * dm.x) / det; Vector2 I = o0 + u0 * ta;
                    nn = new List<Vector2> { I, bFar2 + yard * off, bFar2 }; standalone = true;
                    if (mM.Success && off < float.Parse(mM.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) - 1e-3f && sb != null) sb.AppendLine("    ⛔ " + nm + " × " + rn + ": 背からの離れ " + off.ToString("F2") + " が下限を割る");
                    bStop = bNear; tFar = bFar2;
                    if (sb != null) sb.AppendLine("    " + nm + " × " + rn + "(return" + rn + "): 背から " + off.ToString("F2") + " の線を return" + mJ.Groups[2].Value + " の返しとの交わり (" + I.x.ToString("F2") + "," + I.y.ToString("F2") + ") から反対の妻まで " + Vector2.Distance(I, bFar2 + yard * off).ToString("F2") + "m・妻で背まで閉じる " + off.ToString("F2") + "m(入隅で継ぐ)");
                }
                string loName = S(Get(w, "lo")); float loY = float.NaN;
                foreach (var o3 in A(D["terraces"]) ?? new List<object>()) { var t3 = O(o3); if (t3 != null && S(Get(t3, "name")) == loName) loY = F(Get(t3, "y")); }
                if (float.IsNaN(loY)) { if (sb != null) sb.AppendLine("    ⚠ 低い側の面 " + (loName ?? "-") + " の高さが無い ── 返さない"); continue; }
                res.Add(new BackTrench { wall = nm, run = rn, nodes = nn, stop = bStop, far = tFar, yard = yard, along = standalone ? (tFar - bStop).normalized : (bFar - bStop).normalized, off = off, y = loY, standalone = standalone });
            }
        }
        // 指図 return<棟> 追記 2026-10-10k【硬】「溝の前の縁は <棟> の背の線で止め、それより道の側へ出さない」── 前の縁を背の線(0)へ。当たる先: return<棟> を持つ溝すべて(岡部 N39_1)
        foreach (var t in res)
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
            { var t2 = O(o2); if (t2 == null || S(Get(t2, "name")) != t.wall) continue; string rv = S(Get(t2, "return" + t.run)) ?? "";
              if (System.Text.RegularExpressions.Regex.IsMatch(rv, @"溝の前の縁は\s*" + t.run + @"\s*の背の線で止め")) t.front = 0f; }
        // roadEdge 追記 2026-10-10k【硬】: 溝の止めの妻の閉じは妻の面の石垣(天端の前の線 sCorner)── 溝の止めの端を隣の棟の妻の面からその線まで延ばす
        //   (⛔ 延ばさないと石垣の見え面と隣の妻の面の間 0.77 が溝でも面でもなく、設計の地盤 15.0 の窪みに急な土の面 ── 第94巡の二回目)
        { var rk = _road ?? RoadEdgePlanOf();
          if (rk != null && rk.ok && rk.k10 && !float.IsNaN(rk.sCorner))
              foreach (var t in res)
              {
                  if (t.run != rk.gableNb) continue; float sSt = Vector2.Dot(t.stop - rk.ea, rk.ax); if (Mathf.Abs(sSt - rk.nbFace) > 0.3f) continue;
                  t.pre = Mathf.Abs(rk.sCorner - sSt);   // ⛔ stop を動かさない ── 第94巡の三回目: stop を動かすと地形の溝の切り(2m 格子で 3.40)と返しの見え面の向きまで変わり、0_1 と 1_0 の継ぎが割れた
                  if (sb != null) sb.AppendLine("    溝 " + t.run + " の皮の面を止めの端から妻の面の石垣の天端の前の線まで " + t.pre.ToString("F2") + "m 延ばす(roadEdge 追記 2026-10-10k・地形の切りと石垣の線は替えない)");
              } }
        return res;
    }

    // =====================================================================
    // 背の路地(指図 grading.seRoji)と東の平場の縁の石垣(terraceWalls[TW_Higashi_Se])── EDO-0502 第106巡
    // =====================================================================
    /// <summary>背の路地と TW_Higashi_Se を**据えた長屋の実メッシュの背**から解いた物(Stage2b の据え・Stage3b の皮の設計の地盤・FlatFaces が同じ答えを読む)。</summary>
    public class SeRojiPlan
    {
        public bool ok; public string why = "";
        /// <summary>石垣の天端の前の縁の線(PlaceNozuraNet の線)と節点の天端(区間 i の天端 = tops[i]・段は節点で)。</summary>
        public List<Vector2> nodes = new List<Vector2>(); public List<float> tops = new List<float>();
        /// <summary>区間ごとの見え面(路地の側 = 辺の外向き)。</summary>
        public List<Vector2> faceOf = new List<Vector2>();
        /// <summary>K_Tsuyo の口の道のり(nodes の上)。無ければ NaN。</summary>
        public Vector2 gap = new Vector2(float.NaN, float.NaN);
        public Vector2 ea40, ax40, yd40, ea41, ax41, yd41; public float L40, back40, back41, foot40, foot41, crest40, crest41, s40a, s41b;
        /// <summary>床の縦断(辺ごとの (s, y)・同じ s が二つなら段)。</summary>
        public List<Vector2> f40 = new List<Vector2>(), f41 = new List<Vector2>();
        public float tamari = float.NaN, tam0 = float.NaN, tam1 = float.NaN;
        public List<EdoBuild.SkinFace> faces = new List<EdoBuild.SkinFace>();
        /// <summary>南の延長(seRoji.south・<see cref="SeRojiSouthExtend"/> が解く)── 辺41 の帯を s41b から sSouth まで延ばし、床は f41 の最後の点から southGrade で続ける(NaN = 延ばさない)。</summary>
        public float sSouth = float.NaN, southGrade = 0f;
        public string log = "";
        /// <summary>点 q の路地の床(帯の外は NaN)。帯 = 長屋の背 −0.3(棟の下)〜 見え面の足元 +0.3(石の下)。</summary>
        public float At(Vector2 q)
        {
            if (!ok) return float.NaN;
            float s40 = Vector2.Dot(q - ea40, ax40), d40 = Vector2.Dot(q - ea40, yd40), s41 = Vector2.Dot(q - ea41, ax41), d41 = Vector2.Dot(q - ea41, yd41);
            bool in40 = s40 >= s40a - 0.05f && d40 >= back40 - 0.3f && d40 <= foot40 + 0.3f && d41 >= back41 - 0.3f;
            bool in41 = s41 <= (float.IsNaN(sSouth) ? s41b : sSouth) + 0.05f && d41 >= back41 - 0.3f && d41 <= foot41 + 0.3f && d40 >= back40 - 0.3f;
            if (!in40 && !in41) return float.NaN;
            // 角は二つの帯が重なる ── 長屋 N41_0 の角の妻の線(二つの辺の二等分線・留め)で分ける: 辺40 の線に近い側が辺40
            bool use40 = in40 && (!in41 || d41 > d40);
            if (use40) return SeRojiPlan_Prof(f40, Mathf.Min(s40, L40));
            if (!float.IsNaN(tamari) && s41 > tam0 && s41 < tam1) return tamari;
            if (!float.IsNaN(sSouth) && f41.Count > 0 && s41 > f41[f41.Count - 1].x) return f41[f41.Count - 1].y + (s41 - f41[f41.Count - 1].x) * southGrade;   // 南の延長の床
            return SeRojiPlan_Prof(f41, Mathf.Max(s41, 0f));
        }
    }
    static SeRojiPlan _seRoji;
    /// <summary>この巡の解き(Stage2b が解いた物・domain reload の後は解き直す)。</summary>
    static SeRojiPlan SeRoji()
    {
        if (_seRoji == null)
        {   // domain reload の後は解き直す ── 南の延長(Stage2b の SeRojiSouthExtend が焼いた s と勾配)は SessionState から(床を焼き直さずに読む)
            _seRoji = SeRojiPlanOf();
            float ss = SessionState.GetFloat("Okabe.seRoji.sSouth", float.NaN); if (_seRoji.ok && !float.IsNaN(ss)) { _seRoji.sSouth = ss; _seRoji.southGrade = SessionState.GetFloat("Okabe.seRoji.southGrade", 0f); }
        }
        return _seRoji;
    }
    /// <summary>背の路地の奥の石垣の名(指図 seRoji.w「その先が TW_* の見え面の足元」)。</summary>
    static string SeRojiWallName() { var gr = O(Get(D, "grading")); var sr = gr == null ? null : O(Get(gr, "seRoji")); var m = System.Text.RegularExpressions.Regex.Match(S(Get(sr, "w")) ?? "", @"(TW_[A-Za-z_]+)\s*の見え面の足元"); return m.Success ? m.Groups[1].Value : null; }

    /// <summary>**背の路地と TW_Higashi_Se を解く**(指図 grading.seRoji・terraceWalls[TW_Higashi_Se]【硬】)。
    /// ① 長屋の背 = 据えた長屋の実メッシュ(<see cref="EdoBuild.FaceOut"/>・座 +0.1〜+1.2 の帯)を辺ごとに最も奥 ── 指図 line「見え面の足元を長屋の背面から 一間+犬走り 0.3」
    /// ⇒ 足元の線 = 背 + 1.818 + 0.3。② 石垣の線(PlaceNozuraNet は天端の前の縁を線へ寄せる)= 足元 + 法(野面の駒の実測 FaceBatterOf)× 辺の見付の最大
    /// (⛔ 見付ごとに線を折らない ── 段の境で線が横へずれる。最大で取るので足元は狙いより奥へ出るだけで路地は狭まらない【柔: 足元の離れ】)。
    /// ③ 天端は欄 runs[].top を behind の棟の妻の線(実メッシュの SpecBodySpanAlong)で区切る(段は節点で)。区切り2/3 の境は K_Tsuyo の口の中。
    /// ④ 北の端は TW_Higashi_Hokuto の線の端点から始め(天端一つで継ぐ ── topNote)、N40_2 の背の頭(指図 north「背の頭 2.6m」)の妻 +2.6m で足元の線へ入る。
    /// ⑤ 床の縦断は指図 floor の「s<道のり> … <高さ>」の組を読む(同じ s が二つなら段)。辺41 の南は fall「s80.812 の暗渠」・runs[].toe「12.15 から 1/100」から
    /// s65.359 12.15 → 1/100 → s80.812 → 1/100 → 南の端(読んだ値だけで組む)。溜りは tsuyo「溜り 12.20」を妻の線の間に。
    /// 当たる先: 背に路地と石垣を負う外周の長屋(岡部 辺40・41)。⛔ 座標を書かない ── 毎回測る。</summary>
    public static SeRojiPlan SeRojiPlanOf()
    {
        var P = new SeRojiPlan(); var inv = System.Globalization.CultureInfo.InvariantCulture; var lg = new System.Text.StringBuilder();
        var gr = O(Get(D, "grading")); var sr = gr == null ? null : O(Get(gr, "seRoji"));
        Dictionary<string, object> tw = null;
        foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t = O(o); if (t != null && S(Get(t, "name")) == "TW_Higashi_Se") tw = t; }
        if (sr == null || tw == null) { P.why = "指図に seRoji か TW_Higashi_Se が無い"; return P; }
        string lineTxt = S(Get(tw, "line")) ?? "";
        var mL = System.Text.RegularExpressions.Regex.Match(lineTxt, @"一間.*?\+\s*犬走り\s*([0-9.]+)");
        if (!mL.Success) { P.why = "line の『一間+犬走り』が読めない"; return P; }
        float inu = float.Parse(mL.Groups[1].Value, inv);
        var root = GameObject.Find(GN); var kak = root == null ? null : root.transform.Find("Kakoi");
        if (kak == null) { P.why = "Kakoi が無い"; return P; }
        // 天端の区切り: behind の棟 → top
        var topOf = new Dictionary<string, float>();
        foreach (var o in A(Get(tw, "runs")) ?? new List<object>())
        {
            var r = O(o); if (r == null) continue; float t = F(Get(r, "top"));
            foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(S(Get(r, "behind")) ?? "", @"N4[01]_[0-9]")) topOf[m.Value] = t;
        }
        // 長屋の背と妻
        var spanOf = new Dictionary<string, Vector2>();
        float bk40 = float.MinValue, bk41 = float.MinValue;
        P.ea40 = EdgePt(40, 0f); P.ax40 = (EdgePt(40, 1f) - P.ea40).normalized; P.yd40 = -OutNormal(40); P.L40 = EdgeLen(40);
        P.ea41 = EdgePt(41, 0f); P.ax41 = (EdgePt(41, 1f) - P.ea41).normalized; P.yd41 = -OutNormal(41);
        foreach (var kv in topOf)
        {
            var nb = kak.Find(kv.Key); if (nb == null) { P.why = "長屋 " + kv.Key + " が無い"; return P; }
            bool e40 = kv.Key.StartsWith("N40"); Vector2 ea = e40 ? P.ea40 : P.ea41, ax = e40 ? P.ax40 : P.ax41, yd = e40 ? P.yd40 : P.yd41;
            float seat = nb.position.y;
            float back = EdoBuild.FaceOut(nb.gameObject, ea, yd, seat + 0.1f, seat + 1.2f);
            var sp = EdoBuild.SpecBodySpanAlong(nb.gameObject, ea, ax); if (float.IsNaN(sp.x)) sp = EdoBuild.BodySpanAlong(nb.gameObject, ea, ax);
            if (float.IsNaN(back) || float.IsNaN(sp.x)) { P.why = kv.Key + " の背・妻を測れない"; return P; }
            spanOf[kv.Key] = sp;
            if (e40) bk40 = Mathf.Max(bk40, back); else bk41 = Mathf.Max(bk41, back);
        }
        P.back40 = bk40; P.back41 = bk41; P.foot40 = bk40 + ES + inu; P.foot41 = bk41 + ES + inu;
        // 床の縦断
        string fl = S(Get(sr, "floor")) ?? "";
        foreach (var part in System.Text.RegularExpressions.Regex.Split(fl, @"(?=辺4[01]:)"))
        {
            bool is40 = part.StartsWith("辺40"), is41 = part.StartsWith("辺41"); if (!is40 && !is41) continue;
            var lst = is40 ? P.f40 : P.f41;
            foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(part, @"s(\d+(?:\.\d+)?)((?:(?!s\d)[^/。])*?)(1[0-9]\.\d{2})(?!\d)"))
                lst.Add(new Vector2(float.Parse(m.Groups[1].Value, inv), float.Parse(m.Groups[3].Value, inv)));
            if (is40) { var mk = System.Text.RegularExpressions.Regex.Match(part, @"角\s*(1\d\.\d\d)"); if (mk.Success) lst.Add(new Vector2(P.L40, float.Parse(mk.Groups[1].Value, inv))); }
            if (is41) { var mt = System.Text.RegularExpressions.Regex.Match(part, @"溜り\s*(1\d\.\d\d)"); if (mt.Success) P.tamari = float.Parse(mt.Groups[1].Value, inv); }
            lst.Sort((a, b) => a.x.CompareTo(b.x));   // 安定でない ── 段の二点は元の順(北の値が先)を保つため下で直す
        }
        // 段(同じ s の二点)は読んだ順(北 → 南)に並べ直す
        {
            var raw = new List<Vector2>();
            foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(fl.Substring(Mathf.Max(0, fl.IndexOf("辺41:"))), @"s(\d+(?:\.\d+)?)((?:(?!s\d)[^/。])*?)(1[0-9]\.\d{2})(?!\d)"))
                raw.Add(new Vector2(float.Parse(m.Groups[1].Value, inv), float.Parse(m.Groups[3].Value, inv)));
            var idx = new List<int>(); for (int i = 0; i < raw.Count; i++) idx.Add(i);
            idx.Sort((a, b) => raw[a].x != raw[b].x ? raw[a].x.CompareTo(raw[b].x) : a.CompareTo(b));
            P.f41 = new List<Vector2>(); foreach (int i in idx) P.f41.Add(raw[i]);
        }
        // 辺41 の南(fall「s80.812 の暗渠」・toe「12.15 から 1/100」)── 読めた値だけで組む
        {
            string fall = S(Get(sr, "fall")) ?? "";
            var mA = System.Text.RegularExpressions.Regex.Match(fall, @"(\d+\.\d+)〜南の端は北へ\s*[（(]s(\d+\.\d+)\s*の暗渠");
            float sTail = P.f41.Count > 0 ? P.f41[P.f41.Count - 1].x : float.NaN, yTail = P.f41.Count > 0 ? P.f41[P.f41.Count - 1].y : float.NaN;
            float grade = float.NaN;
            foreach (var o in A(Get(tw, "runs")) ?? new List<object>()) { var r = O(o); var m = System.Text.RegularExpressions.Regex.Match(S(Get(r, "toe")) ?? "", @"([0-9.]+)\s*から\s*1/(\d+)"); if (m.Success && Mathf.Abs(float.Parse(m.Groups[1].Value, inv) - yTail) < 1e-3f) grade = 1f / float.Parse(m.Groups[2].Value, inv); }
            Vector2 sp5; float sEnd = spanOf.TryGetValue("N41_5", out sp5) ? sp5.y : float.NaN;
            if (mA.Success && !float.IsNaN(grade) && !float.IsNaN(sEnd))
            {
                float sLow = float.Parse(mA.Groups[2].Value, inv);
                float yLow = yTail - (sLow - sTail) * grade;
                P.f41.Add(new Vector2(sLow, yLow)); P.f41.Add(new Vector2(sEnd + 0.5f, yLow + (sEnd + 0.5f - sLow) * grade));
                lg.Append("  南: s" + sTail.ToString("F3", inv) + " " + yTail.ToString("F2", inv) + " → 1/" + (1f / grade).ToString("F0", inv) + " → s" + sLow.ToString("F3", inv) + " " + yLow.ToString("F3", inv) + "(暗渠)→ 1/" + (1f / grade).ToString("F0", inv) + " → 南の端\n");
            }
            else lg.Append("  ★ 南の端の床が読めない(fall の暗渠・toe の勾配)── s" + sTail.ToString("F2", inv) + " の値のまま\n");
        }
        // 溜り = 通用門の妻の線の間(N41_0 の南の妻 〜 N41_1 の北の妻)
        { Vector2 a, b; if (spanOf.TryGetValue("N41_0", out a) && spanOf.TryGetValue("N41_1", out b)) { P.tam0 = a.y; P.tam1 = b.x; } }
        // 天端の見付の最大(辺ごと)と石垣の線
        float batter = EdoBuild.FaceBatterOf(EdoAssets.Own.SannoNozura(4.8f, 0f, 0));
        if (float.IsNaN(batter)) { P.why = "野面の駒の法が測れない"; return P; }
        float h40 = 0f, h41 = 0f;
        foreach (var kv in topOf)
        {
            var sp = spanOf[kv.Key]; bool e40 = kv.Key.StartsWith("N40");
            for (float s = sp.x; s <= sp.y + 1e-3f; s += 0.5f)
            {
                float y = e40 ? SeRojiPlan_Prof(P.f40, s) : SeRojiPlan_Prof(P.f41, s);
                if (!e40 && s > P.tam0 && s < P.tam1) continue;   // 溜りは石段の口
                if (e40) h40 = Mathf.Max(h40, kv.Value - y); else h41 = Mathf.Max(h41, kv.Value - y);
            }
        }
        P.crest40 = P.foot40 + batter * h40; P.crest41 = P.foot41 + batter * h41;
        // 北の端: TW_Higashi_Hokuto の線の端点(路地の側の端)
        Vector2 hk = new Vector2(float.NaN, float.NaN);
        foreach (var o in A(Get(IMPL, "terraceWalls")) ?? new List<object>())
        {
            var w = O(o); if (w == null || S(Get(w, "name")) != "TW_Higashi_Hokuto") continue; var ln = A(Get(w, "line")); if (ln == null || ln.Count < 2) continue;
            Vector2 p0 = new Vector2(F(A(ln[0])[0]), F(A(ln[0])[1])), p1 = new Vector2(F(A(ln[ln.Count - 1])[0]), F(A(ln[ln.Count - 1])[1]));
            float s0 = Vector2.Dot(p0 - P.ea40, P.ax40), s1 = Vector2.Dot(p1 - P.ea40, P.ax40);
            hk = s0 > s1 ? p0 : p1;
        }
        Vector2 sp2 = spanOf["N40_2"]; P.s40a = sp2.x;
        Func<float, float, Vector2> W40 = (s, d) => P.ea40 + P.ax40 * s + P.yd40 * d;
        Func<float, float, Vector2> W41 = (s, d) => P.ea41 + P.ax41 * s + P.yd41 * d;
        var mN = System.Text.RegularExpressions.Regex.Match(S(Get(sr, "north")) ?? "", @"背の頭\s*([0-9.]+)m");
        float head = mN.Success ? float.Parse(mN.Groups[1].Value, inv) : 0f;
        // 角 = 二つの石垣の線の交わり
        Vector2 C = EdoGeom.LineIntersect(W40(0f, P.crest40), P.ax40, W41(0f, P.crest41), P.ax41, new Vector2(float.NaN, float.NaN));
        if (float.IsNaN(C.x)) { P.why = "角が解けない"; return P; }
        Vector2 sp5b = spanOf["N41_5"]; P.s41b = sp5b.y;
        var nodes = P.nodes; var tops = P.tops;
        float tN = topOf["N40_2"];
        if (!float.IsNaN(hk.x)) { nodes.Add(hk); tops.Add(tN); }
        nodes.Add(W40(P.s40a + head, P.crest40)); tops.Add(tN);
        nodes.Add(C); tops.Add(topOf["N41_0"]);
        // 辺41 の区切り(天端の変わる妻の線)── 口の中(K_Tsuyo)は口の芯に節点
        string[] seq = { "N41_0", "N41_1", "N41_2", "N41_3", "N41_4", "N41_5" };
        for (int i = 0; i + 1 < seq.Length; i++)
        {
            float ta = topOf[seq[i]], tb = topOf[seq[i + 1]]; if (Mathf.Abs(ta - tb) < 1e-3f) continue;
            float sB = (spanOf[seq[i]].y + spanOf[seq[i + 1]].x) * 0.5f;
            nodes.Add(W41(sB, P.crest41)); tops.Add(tb);
        }
        // 南の端 = N41_5 の南の妻(返しは端の決め ② が隅の駒で背へ折る ── nozuraEndRule)
        nodes.Add(W41(P.s41b, P.crest41)); tops.Add(tops[tops.Count - 1]);
        for (int i = 0; i + 1 < nodes.Count; i++)
        {
            Vector2 mid = (nodes[i] + nodes[i + 1]) * 0.5f; float d40 = Vector2.Dot(mid - P.ea40, P.yd40), d41 = Vector2.Dot(mid - P.ea41, P.yd41);
            P.faceOf.Add(d41 > d40 ? -P.yd40 : -P.yd41);
        }
        // 口(K_Tsuyo)= 溜りの妻の線の間を節点の道のりへ
        if (!float.IsNaN(P.tam0))
        {
            float acc = 0f; Vector2 qa = W41(P.tam0, P.crest41), qb = W41(P.tam1, P.crest41);
            for (int i = 0; i + 1 < nodes.Count; i++)
            {
                Vector2 a = nodes[i], b = nodes[i + 1]; float L = Vector2.Distance(a, b); Vector2 d = (b - a) / Mathf.Max(1e-4f, L);
                float ua = Vector2.Dot(qa - a, d), ub = Vector2.Dot(qb - a, d);
                if (ua >= -0.01f && ua <= L + 0.01f && Mathf.Abs(Vector2.Dot(qa - a, new Vector2(-d.y, d.x))) < 0.05f) P.gap = new Vector2(acc + Mathf.Min(ua, ub), acc + Mathf.Max(ua, ub));
                acc += L;
            }
        }
        // 皮の平らな面(床を 0.5m ごとの矩形に割る ── 段は面の境)
        Func<List<Vector2>, float, float> pr = SeRojiPlan_Prof;
        for (float s = P.s40a; s < P.L40 + P.foot41 + 1f; s += 0.5f)
        {
            float sm = Mathf.Min(s + 0.25f, P.L40); float y = pr(P.f40, sm);
            P.faces.Add(new EdoBuild.SkinFace("SeRoji40_" + s.ToString("F1", inv), new[] { W40(s, P.back40 - 0.3f), W40(s + 0.5f, P.back40 - 0.3f), W40(s + 0.5f, P.foot40 + 0.3f), W40(s, P.foot40 + 0.3f) }, y));
        }
        for (float s = -P.foot40 - 1f; s < P.s41b; s += 0.5f)
        {
            float sm = s + 0.25f; float y = (!float.IsNaN(P.tamari) && sm > P.tam0 && sm < P.tam1) ? P.tamari : pr(P.f41, Mathf.Max(sm, 0f));
            P.faces.Add(new EdoBuild.SkinFace("SeRoji41_" + s.ToString("F1", inv), new[] { W41(s, P.back41 - 0.3f), W41(s + 0.5f, P.back41 - 0.3f), W41(s + 0.5f, P.foot41 + 0.3f), W41(s, P.foot41 + 0.3f) }, y));
        }
        // 角の重なりは At と同じ規則で(辺40 の面は辺41 の側を、辺41 の面は辺40 の側を外す)
        P.faces.RemoveAll(f =>
        {
            Vector2 c = (f.poly[0] + f.poly[2]) * 0.5f; float d40 = Vector2.Dot(c - P.ea40, P.yd40), d41 = Vector2.Dot(c - P.ea41, P.yd41);
            bool is40 = f.name.StartsWith("SeRoji40");
            if (is40) return d41 < P.back41 - 0.3f || d41 < d40;
            return d40 < P.back40 - 0.3f || d40 <= d41 && Vector2.Dot(c - P.ea41, P.ax41) < 0f;
        });
        P.ok = true;
        lg.Insert(0, "背の路地 seRoji: 背 辺40 " + P.back40.ToString("F3", inv) + " / 辺41 " + P.back41.ToString("F3", inv) + "m(長屋の実メッシュ)・見え面の足元 +" + (ES + inu).ToString("F3", inv)
                 + "・法 " + batter.ToString("F3", inv) + " × 見付の最大 " + h40.ToString("F2", inv) + "/" + h41.ToString("F2", inv) + " ⇒ 天端の前の縁 " + P.crest40.ToString("F3", inv) + "/" + P.crest41.ToString("F3", inv)
                 + "m・節点 " + nodes.Count + "・口 K_Tsuyo [" + P.gap.x.ToString("F2", inv) + "," + P.gap.y.ToString("F2", inv) + "]・溜り " + P.tamari.ToString("F2", inv) + " s" + P.tam0.ToString("F3", inv) + "〜" + P.tam1.ToString("F3", inv) + "\n"
                 + "  床 辺40: " + SeRojiProfTxt(P.f40) + "\n  床 辺41: " + SeRojiProfTxt(P.f41) + "\n"
                 + "  北の端 = TW_Higashi_Hokuto の端点 " + (float.IsNaN(hk.x) ? "無し" : "(" + hk.x.ToString("F2", inv) + "," + hk.y.ToString("F2", inv) + ") 離れ " + Vector2.Dot(hk - P.ea40, P.yd40).ToString("F2", inv)) + "・背の頭 " + head.ToString("F1", inv) + "m で線へ\n");
        P.log = lg.ToString();
        return P;
    }
    /// <summary>**南の練塀の内の高い石垣 TW_Higashi_Minami の線を解き、検算する**(施主裁定 2026-10-12 案A・指図 terraceWalls[TW_Higashi_Minami].line / lineCheck【硬】・第119巡)。
    /// 線 = kado6(TW_Higashi_Se の南の端の出隅 ── 背の路地の線の最後の節点)の西の腕の見え面の線 = 最後の節点を通り、最後の区間に直交して背(平場)の側へ。
    /// 見え面の足 = 天端の前の縁から法(野面の駒の実の法 FaceBatterOf)×(天端 − 床)だけ見え面の外向きへ。床 = heiFootSpec.floor45 の床(帯の yAt)。
    /// 検算【硬】: 辺4・5 の練塀の内面(一枚物の実メッシュ MeasureFootLines の DInAt)から見え面の足の線までの離れ ≥ lineCheck の値。下回れば建てずに返す(⟶ null・理由は why)。
    /// 通れば欄を組み直して返す(線・天端・mode fill・段なし・見え面の向き _face)。当たる先: 出隅の腕の見え面を延ばして段の石垣の線を引く所(いまは岡部 TW_Higashi_Minami)。</summary>
    static Dictionary<string, object> MinamiWallOf(Dictionary<string, object> w, out string why)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var P = _seRoji; why = "";
        Dictionary<string, object> sw = null;   // 指図の欄(算出物の欄は線を持たない ── 文は指図にだけある)
        foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t = O(o); if (t != null && S(Get(t, "name")) == S(Get(w, "name"))) sw = t; }
        var mT = System.Text.RegularExpressions.Regex.Match(S(Get(sw, "top")) ?? "", @"^\s*([0-9.]+)\s*一直線");
        var mC = System.Text.RegularExpressions.Regex.Match(S(Get(sw, "lineCheck")) ?? "", @"内面から\s*\+\s*([0-9.]+)\s*以上");
        if (!mT.Success || !mC.Success) { why = "  ★ TW_Higashi_Minami: top(a 一直線)/ lineCheck(内面から +d 以上)が読めない ── 建てない\n"; return null; }
        float top = float.Parse(mT.Groups[1].Value, inv), need = float.Parse(mC.Groups[1].Value, inv);
        int nn = P.nodes.Count; if (nn < 2) { why = "  ★ TW_Higashi_Minami: 背の路地の線の節点が無い ── 建てない\n"; return null; }
        Vector2 pe = P.nodes[nn - 1], along = (P.nodes[nn - 1] - P.nodes[nn - 2]).normalized;   // 南へ(線の終わりの向き)
        Vector2 face0 = P.faceOf.Count >= nn - 1 ? P.faceOf[nn - 2] : -P.yd41;                  // TW_Higashi_Se の見え面(路地の側)
        Vector2 armDir = -face0.normalized; armDir = (armDir - along * Vector2.Dot(armDir, along)).normalized;   // 背(平場)の側へ・最後の区間に直交(Kado90)
        Vector2 fc = along;                                                                       // 腕の見え面 = 南(線の終わりの向き)
        float batter = EdoBuild.FaceBatterOf(EdoAssets.Own.SannoNozura(4.8f, 0f, 0)); if (float.IsNaN(batter)) { why = "  ★ TW_Higashi_Minami: 野面の駒の法が測れない ── 建てない\n"; return null; }
        if (_heiFootLines == null) { why = "  ★ TW_Higashi_Minami: 練塀の内面(heiFootSpec)が測れていない ── 建てない\n"; return null; }
        float dMin = float.MaxValue; Vector2 qMin = Vector2.zero; float tEnd = 0f; int nChk = 0; float tPass = float.NaN; var rows = new List<string>();
        foreach (var L in _heiFootLines)
        {
            if (L.name != "辺4" && L.name != "辺5" || L.nPts == 0) continue;
            for (float s = Mathf.Max(0f, L.sLo); s <= L.sHi + 1e-3f; s += 0.5f)
            {
                Vector2 q = L.a + L.ax * s + L.inw * L.DInAt(s); float yf = L.yAt != null ? L.yAt(s) : float.NaN; if (float.IsNaN(yf)) continue;
                Vector2 foot0 = pe + fc * (batter * (top - yf));   // 足の線の上の一点(腕の向きに走る)
                // q から内向き(inw)に進んで足の線に当たるまで
                float den = L.inw.x * armDir.y - L.inw.y * armDir.x; if (Mathf.Abs(den) < 1e-4f) continue;
                Vector2 r = foot0 - q; float d = (r.x * armDir.y - r.y * armDir.x) / den; float t = (r.x * L.inw.y - r.y * L.inw.x) / den;
                if (t < -0.05f) continue;   // 腕の始め(kado6)より東は石垣が無い
                nChk++; tEnd = Mathf.Max(tEnd, t);
                if (d < dMin) { dMin = d; qMin = q; }
                if (d < need && float.IsNaN(tPass)) tPass = t;
                if (Mathf.Abs(s % 5f) < 0.26f) rows.Add(L.name + " s" + s.ToString("F1", inv) + " 離れ " + d.ToString("F2", inv));
            }
        }
        string head = "  TW_Higashi_Minami(石垣 野面・施主裁定 2026-10-12 案A): 線 = kado6 の西の腕の見え面(TW_Higashi_Se の線の終わり (" + pe.x.ToString("F2", inv) + "," + pe.y.ToString("F2", inv) + ") から最後の区間に直交・腕の向き ("
                    + armDir.x.ToString("F3", inv) + "," + armDir.y.ToString("F3", inv) + ") = 東西から " + (Mathf.Atan2(armDir.y, -armDir.x) * Mathf.Rad2Deg).ToString("F1", inv) + "°)・天端 " + top.ToString("F2", inv) + "・法 " + batter.ToString("F3", inv)
                    + " ⇒ 見え面の足 − 練塀の内面(辺4・5・一枚物の実メッシュ)の離れ 最小 " + (nChk == 0 ? "-" : dMin.ToString("F2", inv)) + "(要 ≥" + need.ToString("F2", inv) + "【硬】)・測った点 " + nChk
                    + (float.IsNaN(tPass) ? "" : "・下回り始め 腕の先から " + tPass.ToString("F1", inv) + "m") + "\n    " + string.Join(" / ", rows.ToArray()) + "\n";
        if (nChk == 0 || dMin < need) { why = head + "  ★ TW_Higashi_Minami: lineCheck【硬】を下回る ── 建てない(普請方へ返す)。kado6 と TW_Higashi_Se_5 の積み止めはそのまま\n"; return null; }
        var w2 = new Dictionary<string, object>(w);
        w2["line"] = new List<object> { new List<object> { (double)pe.x, (double)pe.y }, new List<object> { (double)(pe.x + armDir.x * tEnd), (double)(pe.y + armDir.y * tEnd) } };
        w2["tops"] = new List<object> { (double)top, (double)top }; w2["top"] = (double)top; w2["mode"] = "fill"; w2["gaps"] = new List<object>(); w2.Remove("unresolved"); w2["_face"] = fc;
        why = head + "  ⭕ 検算を通った ── 線 " + tEnd.ToString("F1", inv) + "m\n";
        return w2;
    }

    /// <summary>**背の路地の南の延長**(指図 grading.seRoji.south「南の端は塞がず、路地の床のまま南の練塀(S_Hei_01 系)の内の足元まで通す【硬】・床 12.15〜12.25・北へ 1/100【柔】」
    /// ・施主裁定 2026-10-12 案A・第113巡)。帯(背 −0.3 〜 見え面の足元 +0.3)を長屋 N41_5 の南の妻から、南の練塀の内の面(据えた駒へ光線)の 0.3 先(練塀の下)まで延ばし、
    /// 床の縦断(辺41 の最後の勾配のまま南へ)へ切り盛りする(<see cref="EdoBuild.GroundToPoly"/>)。⛔ 帯の外(角の庭)は触らない。</summary>
    static string SeRojiSouthExtend(SeRojiPlan P)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var gr = O(Get(D, "grading")); var sr = gr == null ? null : O(Get(gr, "seRoji"));
        string st = S(Get(sr, "south")) ?? ""; if (!st.Contains("塞がず") || !st.Contains("内の足元まで")) return "";
        var mS = System.Text.RegularExpressions.Regex.Match(st, @"(S_Hei_\w+)\s*系");
        string pre = mS.Success ? mS.Groups[1].Value : null; if (pre == null) return "  ★ seRoji.south: 南の練塀の名(…系)が読めない ── 延ばさない\n";
        // 系 = 名の run の駒 + その辺の間の隅の駒(Kado_P*)+ 留め柱(第117巡: 隅の腕の短い版で辺1〜4 が隅の駒だけで埋まり、名の run の駒が 0 になった)
        var preEdges = new List<int>(); foreach (var r in Runs) if (r.Dobei && r.name.StartsWith(pre) && !preEdges.Contains(r.edge)) preEdges.Add(r.edge); int nP = Poly.Length;
        var walls = new List<GameObject>(); foreach (Transform c in Group("Kakoi"))
        {
            if (!c.gameObject.activeInHierarchy) continue; string nm = c.name; int v;
            if (nm.StartsWith(pre) || nm == "TomeBashira_" + pre || (nm.StartsWith("Kado_P") && int.TryParse(nm.Substring(6), out v) && preEdges.Contains((v - 1 + nP) % nP) && preEdges.Contains(v % nP))) walls.Add(c.gameObject);
        }
        if (walls.Count == 0) return "  ★ seRoji.south: 南の練塀 " + pre + "* が据わっていない ── 延ばさない\n";
        int nf = P.f41.Count; if (nf < 2) return "  ★ seRoji.south: 辺41 の床の縦断が無い\n";
        Vector2 la = P.f41[nf - 2], lb = P.f41[nf - 1]; float gS = Mathf.Abs(lb.x - la.x) < 1e-3f ? 0f : (lb.y - la.y) / (lb.x - la.x);
        System.Func<float, float> yAtS = s => s <= lb.x ? SeRojiPlan_Prof(P.f41, s) : lb.y + (s - lb.x) * gS;
        float dMid = 0.5f * (P.back41 + P.foot41), y0 = yAtS(P.s41b); Vector2 o2 = P.ea41 + P.ax41 * P.s41b + P.yd41 * dMid;
        float far = float.NaN; foreach (float dd in new[] { P.back41 + 0.1f, dMid, P.foot41 - 0.1f })
        { Vector2 q = P.ea41 + P.ax41 * P.s41b + P.yd41 * dd; float t = EdoBuild.RayToBodies(walls, new Vector3(q.x, y0 + 0.5f, q.y), new Vector3(P.ax41.x, 0f, P.ax41.y), 12f); if (!float.IsNaN(t)) far = float.IsNaN(far) ? t : Mathf.Max(far, t); }
        if (float.IsNaN(far)) return "  ★ seRoji.south: N41_5 の南の妻から 12m 内に " + pre + "* の内の面が無い ── 延ばさない\n";
        float s1 = P.s41b + far + 0.3f;
        var poly = new[] { P.ea41 + P.ax41 * (P.s41b - 0.25f) + P.yd41 * (P.back41 - 0.3f), P.ea41 + P.ax41 * s1 + P.yd41 * (P.back41 - 0.3f),
                           P.ea41 + P.ax41 * s1 + P.yd41 * (P.foot41 + 0.3f), P.ea41 + P.ax41 * (P.s41b - 0.25f) + P.yd41 * (P.foot41 + 0.3f) };
        // ⭐ 区画の線から半升(0.125)内で切る(seRoji.clipOrder【硬: 区画の外への波及 0】・第114巡)── 帯は辺41 の向きに延ばすので、角 P0 の南では辺1・2 の線を越えて樹下へ出ていた(r113 +1.15)
        float clip = ClipIn(); var PP = Poly; int nOut = 0;
        float up, dn; int nw = EdoBuild.GroundToPoly(poly, q => { if (!EdoGeom.PIP(PP, q) || EdoBuild.EdgeDistPublic(PP, q) < clip) { nOut++; return float.NaN; } return yAtS(Vector2.Dot(q - P.ea41, P.ax41)); }, out up, out dn);
        P.sSouth = s1; P.southGrade = gS; SessionState.SetFloat("Okabe.seRoji.sSouth", s1); SessionState.SetFloat("Okabe.seRoji.southGrade", gS);   // TW_Higashi_Se の足元(At)・Stage3d が同じ床を読む ── 南の端の隅の駒の足を延長の床に据える(第113巡: 旧い地盤 10.1 に据わり、駒の下を下げて路地に穴)
        return "  背の路地の南の延長(seRoji.south【硬】): N41_5 の南の妻 s " + P.s41b.ToString("F2", inv) + " から " + pre + "* の内の面(光線 " + far.ToString("F2", inv) + "m)の 0.3 先 s " + s1.ToString("F2", inv)
             + " まで・床 " + y0.ToString("F2", inv) + " → " + yAtS(s1).ToString("F2", inv) + "(辺41 の最後の勾配 1/" + (Mathf.Abs(gS) < 1e-5f ? "∞" : (1f / Mathf.Abs(gS)).ToString("F0", inv)) + " で南へ上る = 北へ下る)・節点 " + nw + "・盛り 最大 " + up.ToString("F2", inv) + "・切り 最大 " + dn.ToString("F2", inv) + "m・区画の線から " + clip.ToString("F3", inv) + " の外で切った節点 " + nOut + "(clipOrder【硬】)\n";
    }
    /// <summary>**練塀の内の足元の帯**(指図 grading.seRoji.heiFootSpec【硬】・第115巡 ── 第114巡の文の読み(heiFoot の正規表現)から構造の欄へ替えた)。
    /// runs の練塀・その間の隅の駒(内の腕)・留め柱の実頂点で辺ごとの内面を測り(EdoBuild.MeasureFootLines)、帯 [band.from, band.to](内面から・+ = 内)を
    /// y.target(≥ y.min【硬】)に、その先 feather の勾配で今の地面へ(EdoBuild.WriteFootBand)。floor45 の辺は帯の高さを溝の床の縦断(座 + 下限・東へ一方向・一升出し)に替え、
    /// e6Head の辺は床の頭から西へ上る面へ低い所だけ盛る。区画の線から ClipIn() の外は触らない。当たる先: 練塀の内の足元の床を座で受ける所(いまは岡部 角 P0 の南・辺4・5・辺6 の頭)。</summary>
    static string SeRojiHeiFoot(bool write = true)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var sr = O(Get(O(Get(D, "grading")), "seRoji")); var sp = O(Get(sr, "heiFootSpec"));
        if (sp == null) return Has(sr, "heiFoot") ? "  ★ seRoji.heiFootSpec が無い ── 帯を焼かない(文の heiFoot は読まない・第115巡)\n" : "";
        var band = O(Get(sp, "band")); var yy = O(Get(sp, "y")); var fe = O(Get(sp, "feather")); var f45 = O(Get(sp, "floor45"));
        float from = Has(band, "from") ? F(band["from"]) : float.NaN, to = Has(band, "to") ? F(band["to"]) : float.NaN, yMin = Has(yy, "min") ? F(yy["min"]) : float.NaN, yT = Has(yy, "target") ? F(yy["target"]) : float.NaN;
        var mF = System.Text.RegularExpressions.Regex.Match(S(Get(fe, "slope")) ?? "", @"1\s*/\s*([0-9.]+)");
        if (float.IsNaN(from) || float.IsNaN(to) || float.IsNaN(yMin) || float.IsNaN(yT) || !mF.Success) return "  ★ seRoji.heiFootSpec の band / y / feather が読めない ── 帯を焼かない\n";
        float nS = float.Parse(mF.Groups[1].Value, inv), yB = Mathf.Max(yMin, yT), clip = ClipIn();
        var runNames = new List<string>(); foreach (var o in A(Get(sp, "runs")) ?? new List<object>()) runNames.Add(S(o));
        var edges = new List<int>(); foreach (var rn in runNames) { int k = System.Array.FindIndex(Runs, x => x.name == rn); if (k >= 0 && !edges.Contains(Runs[k].edge)) edges.Add(Runs[k].edge); }
        // floor45: 辺 a・b の溝の床(note の「辺4・5」)── 硬「座 +d 以上・1/n 以上・一升(c)」/ 柔「1/m 狙い・埋まり lo〜hi」
        var e45 = new List<int>(); float fUp = float.NaN, gMin = float.NaN, gT = float.NaN, burHi = float.NaN, cell = 0f;
        if (f45 != null)
        {
            var mE = System.Text.RegularExpressions.Regex.Match(S(Get(f45, "note")) ?? "", @"辺\s*([0-9・,、]+)"); if (mE.Success) foreach (var es in mE.Groups[1].Value.Split(new[] { '・', ',', '、' }, System.StringSplitOptions.RemoveEmptyEntries)) e45.Add(int.Parse(es.Trim()));
            string h = S(Get(f45, "hard")) ?? "", so = S(Get(f45, "soft")) ?? "";
            var m1 = System.Text.RegularExpressions.Regex.Match(h, @"座\s*\+\s*([0-9.]+)\s*以上"); if (m1.Success) fUp = float.Parse(m1.Groups[1].Value, inv);
            var m2 = System.Text.RegularExpressions.Regex.Match(h, @"1\s*/\s*([0-9.]+)\s*以上"); if (m2.Success) gMin = 1f / float.Parse(m2.Groups[1].Value, inv);
            var m3 = System.Text.RegularExpressions.Regex.Match(h, @"一升[(（]\s*([0-9.]+)\s*[)）]"); if (m3.Success) cell = float.Parse(m3.Groups[1].Value, inv);
            var m4 = System.Text.RegularExpressions.Regex.Match(so, @"1\s*/\s*([0-9.]+)\s*狙い"); if (m4.Success) gT = 1f / float.Parse(m4.Groups[1].Value, inv);
            var m5 = System.Text.RegularExpressions.Regex.Match(so, @"埋まり\s*([0-9.]+)\s*〜\s*([0-9.]+)"); if (m5.Success) burHi = float.Parse(m5.Groups[2].Value, inv);
            if (e45.Count == 0 || float.IsNaN(fUp) || float.IsNaN(gMin)) return "  ★ seRoji.heiFootSpec.floor45 の辺・座 +d・勾配の下限が読めない ── 帯を焼かない\n";
            if (float.IsNaN(gT)) gT = gMin; if (float.IsNaN(burHi)) burHi = 0.24f;
            foreach (int e in e45) if (!edges.Contains(e)) edges.Add(e);
        }
        bool head6 = Has(sp, "e6Head"); int eHead = -1; if (head6) { var mH = System.Text.RegularExpressions.Regex.Match(S(sp["e6Head"]), @"辺\s*([0-9]+)"); if (mH.Success) { eHead = int.Parse(mH.Groups[1].Value); if (!edges.Contains(eHead)) edges.Add(eHead); } }
        edges.Sort();
        System.Func<int, float, float> seatOf = (e, sv) => { float best = float.NaN; foreach (var r in Runs) if (r.Dobei && r.edge == e && sv >= r.s0 - 0.5f && sv <= r.s1 + 0.5f) { best = r.SeatAt(Mathf.Clamp(sv, r.s0, r.s1)); break; } return best; };
        var lines = new List<EdoBuild.FootLine>(); var byE = new Dictionary<int, EdoBuild.FootLine>();
        foreach (int e in edges) { Vector2 ea = EdgePt(e, 0f); var L = new EdoBuild.FootLine { name = "辺" + e, a = ea, ax = (EdgePt(e, 1f) - ea).normalized, inw = -OutNormal(e), len = EdgeLen(e) }; int ee = e; L.seatAt = sv => seatOf(ee, sv); lines.Add(L); byE[e] = L; }
        // 駒: 帯の辺の練塀・その間と両端の隅の駒・留め柱(実メッシュで内面を測る)
        var pcs = new List<GameObject>(); var kak = Group("Kakoi"); int n = Poly.Length;
        foreach (Transform c in kak)
        {
            if (!c.gameObject.activeInHierarchy) continue; string nm = c.name; bool take = false;
            foreach (var r in Runs) if (r.Dobei && edges.Contains(r.edge) && nm.StartsWith(r.name + "_")) { take = true; break; }
            if (!take && nm.StartsWith("Kado_P")) { int v; if (int.TryParse(nm.Substring(6), out v) && edges.Contains((v - 1 + n) % n) && edges.Contains(v % n)) take = true; }
            if (!take && nm.StartsWith("TomeBashira_")) foreach (var rn in runNames) if (nm == "TomeBashira_" + rn) take = true;
            if (take) pcs.Add(c.gameObject);
        }
        EdoBuild.MeasureFootLines(lines, pcs);
        // 帯は辺の中だけ(北は留め柱の s0 まで ── 隅の駒の腕が辺の先へ出ても帯を延ばさない・第115巡 P2 の腕が P1 を 0.75 越えた)
        foreach (var L in lines) { if (L.nPts == 0) continue; L.sLo = Mathf.Max(L.sLo, 0f); L.sHi = Mathf.Min(L.sHi, L.len); }
        var sb = new System.Text.StringBuilder();
        // floor45 の縦断: u = 辺 e45[0] の始めから西へ(辺を順に足す)。区間 = 座の平らな段(一升を低い側へ出す)ごとに 勾配 g = clamp((座 + 埋まりの上限 − 頭) / 長さ, 下限, 狙い)
        System.Func<float, float> floorAt = null; float headY = float.NaN, uEnd = 0f; var uOf = new Dictionary<int, float>();
        if (e45.Count > 0)
        {
            e45.Sort(); float acc = 0f; foreach (int e in e45) { uOf[e] = acc; acc += EdgeLen(e); } uEnd = acc;
            System.Func<float, float> seatU = u => { foreach (int e in e45) if (u <= uOf[e] + EdgeLen(e) + 1e-4f) return seatOf(e, u - uOf[e]); return seatOf(e45[e45.Count - 1], EdgeLen(e45[e45.Count - 1])); };
            var us = new List<float>(); var ys = new List<float>(); float du = 0.25f; float prev = yB; us.Add(0f); ys.Add(prev);
            // 段の区間を切る
            var cuts = new List<float> { 0f }; float s0 = seatU(cell); for (float u = du; u <= uEnd + 1e-4f; u += du) { float st = seatU(Mathf.Min(uEnd, u + cell)); if (Mathf.Abs(st - s0) > 0.01f) { cuts.Add(u); s0 = st; } } cuts.Add(uEnd);
            var secTxt = new List<string>();
            for (int k = 0; k + 1 < cuts.Count; k++)
            {
                float ua = cuts[k], ub = cuts[k + 1]; float st = seatU(Mathf.Min(uEnd, ua + cell + 0.01f)); float y0 = k == 0 ? Mathf.Max(prev, st + fUp) : Mathf.Max(prev + gMin * du, st + fUp);
                float g = ub - ua > 1e-3f ? Mathf.Clamp((st + burHi - y0) / (ub - ua), gMin, gT) : gT;
                for (float u = ua + du; u <= ub + 1e-4f; u += du) { us.Add(u); ys.Add(y0 + g * (u - ua)); }
                prev = y0 + g * (ub - ua); secTxt.Add("u " + ua.ToString("F2", inv) + "〜" + ub.ToString("F2", inv) + " 座 " + st.ToString("F2", inv) + " 床 " + y0.ToString("F3", inv) + "→" + prev.ToString("F3", inv) + "(1/" + (1f / g).ToString("F0", inv) + ")");
            }
            headY = prev;
            floorAt = u => { if (u <= 0f) return ys[0]; for (int i = 0; i + 1 < us.Count; i++) if (u <= us[i + 1]) return Mathf.Lerp(ys[i], ys[i + 1], (u - us[i]) / Mathf.Max(1e-4f, us[i + 1] - us[i])); return ys[ys.Count - 1]; };
            sb.AppendLine("  辺" + string.Join("・", e45.ConvertAll(x => x.ToString()).ToArray()) + " の溝の床(heiFootSpec.floor45【硬: 座 +" + fUp.ToString("F2", inv) + " 以上・東へ一方向・1/" + (1f / gMin).ToString("F0", inv) + " 以上・段は一升 " + cell.ToString("F2", inv) + " 低い側へ出す】・柔: 1/" + (1f / gT).ToString("F0", inv) + " 狙い・埋まり ≤" + burHi.ToString("F2", inv) + "): " + string.Join(" / ", secTxt.ToArray()) + "・頭 " + headY.ToString("F3", inv));
        }
        foreach (var L in lines)
        {
            int e = int.Parse(L.name.Substring(1));
            if (e45.Contains(e)) { float u0 = uOf[e]; L.yAt = s => floorAt(u0 + s); L.noFeather = true; }   // 摺り付けは路地の側だけ(feather.side)── 溝の床は野面石との間で摺り付けない(第115巡: 小段を 1.55 削った)
            else if (e == eHead && !float.IsNaN(headY)) { L.fillOnly = true; L.noFeather = true; float g0 = float.IsNaN(gT) ? 0.01f : gT; L.yAt = s => headY + g0 * Mathf.Max(0f, s); L.sHi = Mathf.Min(L.sHi, 6f); }
            else L.yAt = s => yB;
        }
        var PP = Poly; int nOut = 0;
        _heiFrom = from; _heiTo = to;
        if (!write) { _heiFootLines = lines; _heiFootPieces = pcs; return "  練塀の内の足(heiFootSpec の駒の内面の 0.05 内の地表と比べる・測るだけ): " + EdoBuild.FootFloatReport(lines, pcs) + "\n"; }
        int nw = EdoBuild.WriteFootBand(lines, from, to, nS, 0.5f * nS, q => { if (!EdoGeom.PIP(PP, q) || EdoBuild.EdgeDistPublic(PP, q) < clip) { nOut++; return false; } return true; });
        foreach (var L in lines)
            sb.AppendLine("  練塀の内の足元の帯(heiFootSpec【硬: 浮き0】)" + L.name + ": 駒の頂点 " + L.nPts + "・内面 線から " + (L.nPts > 0 ? L.dIn.ToString("F3", inv) : "-") + "・s " + (L.nPts > 0 ? L.sLo.ToString("F2", inv) + "〜" + L.sHi.ToString("F2", inv) : "-")
                          + "・帯 内面 " + from.ToString("+0.00;-0.00", inv) + "〜" + to.ToString("+0.00;-0.00", inv) + (L.fillOnly ? "(低い所だけ盛る)" : "") + "・帯の節点 " + L.nBand + "・摺り付け(1/" + nS.ToString("0", inv) + ")" + L.nTap + "・盛り 最大 " + L.up.ToString("F2", inv) + "・切り 最大 " + L.dn.ToString("F2", inv));
        sb.AppendLine("  帯の節点 計 " + nw + "・区画の線から " + clip.ToString("F3", inv) + " の外で触らなかった " + nOut + "(clipOrder【硬】)");
        _heiFootLines = lines; _heiFootPieces = pcs;
        return sb.ToString();
    }
    static List<EdoBuild.FootLine> _heiFootLines; static List<GameObject> _heiFootPieces; static float _heiFrom = float.NaN, _heiTo = float.NaN;
    /// <summary>drains[D_MinamiHei] を引く(無ければ null)。</summary>
    static Dictionary<string, object> DrainByName(string nm) { foreach (var o in A(Get(D, "drains")) ?? new List<object>()) { var d = O(o); if (d != null && S(Get(d, "name")) == nm) return d; } return null; }
    /// <summary>**角の庭の窪みを盛る**(指図 drains[D_MinamiHei].niwa「角の庭は全面 a 以上【硬】・どの点からも庭の溝へ下り窪み無し【硬】・高い順に 足元の帯 ≥ 庭 ≥ 溝の天端」・第115巡)。
    /// 種 = 練塀の内の足元の帯(heiFootSpec の runs の辺)の内の縁の 0.3 先。広げる先は区画の中で背の路地の床(排け口)に当たるまで(EdoBuild.FillPocket)・面 = a + 1/100 × 排け口まで(帯の高さを越えない)。
    /// 盛った節点は Stage3d の駒の下の下げの下限にする(⛔ 庭の下に埋まる土留めの駒の天端で窪みを開けない)。</summary>
    static string SeRojiNiwaFill(SeRojiPlan spl)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var dr = DrainByName("D_MinamiHei"); if (dr == null || _heiFootLines == null) return "";
        var m = System.Text.RegularExpressions.Regex.Match(S(Get(dr, "niwa")) ?? "", @"全面\s*([0-9.]+)\s*以上"); if (!m.Success) return "  ★ D_MinamiHei.niwa の「全面 a 以上」が読めない ── 角の庭を盛らない\n";
        float yMin = float.Parse(m.Groups[1].Value, inv); var sp = O(Get(O(Get(O(Get(D, "grading")), "seRoji")), "heiFootSpec")); var band = O(Get(sp, "band")); float to = F(band["to"]);
        float yCap = float.NaN; var yy = O(Get(sp, "y")); if (yy != null) yCap = Mathf.Max(F(yy["min"]), F(yy["target"]));
        var seeds = new List<Vector2>();
        foreach (var L in _heiFootLines) { if (L.fillOnly || L.nPts == 0 || L.name == "辺5") continue; for (float s = L.sLo; s <= L.sHi + 1e-3f; s += 0.25f) seeds.Add(L.a + L.ax * s + L.inw * (L.dIn + to + 0.3f)); }
        var PP = Poly; float clip = ClipIn(); var filled = new List<Vector2>();
        string r = EdoBuild.FillPocket(seeds, yMin, 0.01f, 8f, 4000,
            q => !EdoGeom.PIP(PP, q) || EdoBuild.EdgeDistPublic(PP, q) < clip || (spl != null && spl.ok && !float.IsNaN(spl.At(q))),
            q => spl != null && spl.ok && !float.IsNaN(spl.At(q)), q => yCap, filled);
        var keys = new System.Text.StringBuilder(); foreach (var q in filled) keys.Append(q.x.ToString("F3", inv)).Append(',').Append(q.y.ToString("F3", inv)).Append(';');
        SessionState.SetString("Okabe.niwa.filled", keys.ToString()); SessionState.SetFloat("Okabe.niwa.yMin", yMin);
        return "  角の庭(D_MinamiHei.niwa【硬: 全面 " + yMin.ToString("F2", inv) + " 以上・窪み無し】): " + r + "\n";
    }
    /// <summary>角の庭として盛った節点(Stage2b の SeRojiNiwaFill)── Stage3d の駒の下の下げの下限。</summary>
    static HashSet<long> NiwaFilledKeys(out float yMin)
    {
        yMin = SessionState.GetFloat("Okabe.niwa.yMin", float.NaN); var hs = new HashSet<long>(); var txt = SessionState.GetString("Okabe.niwa.filled", ""); if (txt == "") return hs;
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        foreach (var it in txt.Split(new[] { ';' }, System.StringSplitOptions.RemoveEmptyEntries)) { var xy = it.Split(','); hs.Add(NodeKey(float.Parse(xy[0], inv), float.Parse(xy[1], inv))); }
        return hs;
    }
    static long NodeKey(float x, float z) { return ((long)Mathf.RoundToInt(x * 8f) << 32) ^ (uint)Mathf.RoundToInt(z * 8f); }
    /// <summary>TW_Higashi_Se の南の端の隅の駒(terraceWalls[].southKado・seRoji.southKado)の据わりを刷る: 天端・根入れ(床 − 底)・丈・見え面から 1.0 以内の床 −0.02 より低い節点。⛔ 直さない ── 測るだけ。</summary>
    static string SeRojiSouthKadoReport(SeRojiPlan spl)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; string seWall = SeRojiWallName(); if (seWall == null) return "";
        var dan = Group("Dan"); GameObject kd = null; float bestS = float.MinValue;
        foreach (Transform c in dan) { if (!c.gameObject.activeInHierarchy || !c.name.StartsWith(seWall + "_") || !c.name.Contains("_kado")) continue; var b = EdoBuild.RB(c.gameObject); float sv = Vector2.Dot(new Vector2(b.center.x, b.center.z) - spl.ea41, spl.ax41); if (sv > bestS) { bestS = sv; kd = c.gameObject; } }
        if (kd == null) return "  ★ " + seWall + " の南の端の隅の駒が無い\n";
        var kb = EdoBuild.RB(kd); float fl = float.NaN; foreach (var v in EdoBuild.Body(kd.transform, 4000)) { float y = spl.At(new Vector2(v.x, v.z)); if (!float.IsNaN(y)) fl = float.IsNaN(fl) ? y : Mathf.Min(fl, y); }
        // 見え面から 1.0 以内(駒の外接の 1.0 の内・床の帯の中)の節点で床 −0.02 より低い物
        var t = EdoBuild.T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1); int nLow = 0, nAll = 0; float worst = 0f;
        for (float x = kb.min.x - 1f; x <= kb.max.x + 1f; x += hs) for (float z = kb.min.z - 1f; z <= kb.max.z + 1f; z += hs)
        {
            int i = Mathf.RoundToInt((x - org.x) / hs), j = Mathf.RoundToInt((z - org.z) / hs); float qx = org.x + i * hs, qz = org.z + j * hs; float f = spl.At(new Vector2(qx, qz)); if (float.IsNaN(f)) continue;
            nAll++; float g = td.GetHeight(i, j) + org.y; if (g < f - 0.02f - 1e-3f) { nLow++; worst = Mathf.Max(worst, f - g); }
        }
        return "  " + seWall + " の南の端の隅の駒 " + kd.name + "(" + System.IO.Path.GetFileNameWithoutExtension(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(kd)) + "): 天端 " + kb.max.y.ToString("F3", inv) + "・底 " + kb.min.y.ToString("F3", inv) + "・丈 " + kb.size.y.ToString("F2", inv)
             + "・足元の床 " + (float.IsNaN(fl) ? "-" : fl.ToString("F2", inv)) + "・根入れ " + (float.IsNaN(fl) ? "-" : (fl - kb.min.y).ToString("F2", inv) + (fl - kb.min.y >= 0.30f - 1e-3f ? " ⭕(≥0.30)" : " ⛔")) + "(丈 ≥3.15 の隅の駒は H4.80 だけ ⇒ 根入れで埋める【柔】)"
             + "・見え面から 1.0 以内の床の帯の節点 " + nAll + " のうち 床 −0.02 より低い " + nLow + (nLow == 0 ? " ⭕" : " ⛔(最も低い 床 −" + worst.ToString("F2", inv) + ")") + "\n";
    }
    /// <summary>床・帯の多角形を区画の線から内へ切る幅(指図 grading.seRoji.clipOrder「区画の線から半升(0.125)内で切る」)。読めなければ地形の升の半分。</summary>
    static float ClipIn()
    {
        var sr = O(Get(O(Get(D, "grading")), "seRoji")); var m = System.Text.RegularExpressions.Regex.Match(S(Get(sr, "clipOrder")) ?? "", @"半升[(（]\s*([0-9.]+)\s*[)）]\s*内で切る");
        return m.Success ? float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : 0.5f * EdoBuild.TerrainCell(EdoBuild.T());
    }
    static float SeRojiPlan_Prof(List<Vector2> f, float s)
    {
        if (f.Count == 0) return float.NaN;
        if (s <= f[0].x) return f[0].y;
        for (int i = 0; i + 1 < f.Count; i++)
        {
            Vector2 a = f[i], b = f[i + 1];
            if (s < a.x || s > b.x || b.x - a.x < 1e-4f) continue;
            return Mathf.Lerp(a.y, b.y, (s - a.x) / (b.x - a.x));
        }
        return f[f.Count - 1].y;
    }
    static string SeRojiProfTxt(List<Vector2> f) { var inv = System.Globalization.CultureInfo.InvariantCulture; var l = new List<string>(); foreach (var v in f) l.Add("s" + v.x.ToString("F3", inv) + ":" + v.y.ToString("F3", inv)); return string.Join(" ", l.ToArray()); }
    [MenuItem("Edo/岡部筑前守上屋敷/検: 背の路地を解く(据えない)")]
    public static void SeRojiReportMenu() { var p = SeRojiPlanOf(); Debug.Log("[Okabe] " + (p.ok ? p.log : "★ 背の路地が解けない: " + p.why)); }
    public static string SeRojiReport() { var p = SeRojiPlanOf(); return p.ok ? p.log : "★ " + p.why; }

    /// <summary>背の台の石垣を棟の背の全長に通す欄(backOf&lt;棟&gt; 追記 2026-10-10o)の溝。</summary>
    static List<BackTrench> BackTrenchesFull()
    {
        var res = new List<BackTrench>();
        foreach (var t in BackTrenches(null))
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
            {
                var t2 = O(o2); if (t2 == null || S(Get(t2, "name")) != t.wall) continue; string bo = S(Get(t2, "backOf" + t.run)) ?? "";
                int i = bo.IndexOf("追記 2026-10-10o"); if (i >= 0 && bo.Substring(i).Contains("の背の全長に通す")) res.Add(t);
            }
        return res;
    }

    public class BackOfFull { public BackTrench tr; public EdoBuild.NozuraSeg seg; public string txt; public float crest; }

    /// <summary>**背の台の石垣を棟の背の全長に通す**(指図 terraceWalls[].backOf&lt;棟&gt; 追記 2026-10-10o【硬】・EDO-0502 第98巡)。線 = 棟の背の面(溝の stop → 背の向き)。
    /// 始まり(止めの妻の側)= 名指しの区間(「西の端は X の見え面に突き付けて止め」)の線との交わり ── 止めの駒を置かず、網の中でその区間の据わった駒の実面へ突き付ける
    /// (区間を網の最後に足すので相手の鎖が先に据わる)。終わり = 名指しの棟(「東の端は N.. の台の面に突き付けて閉じ」)の実メッシュの頂点のうち、線の帯
    /// (背の面の前 1.2・後 2.0・天端 +0.1 より下)で最も手前の物 ── 打ち切りで止める(相手は長屋で網の駒でない)。棟の背の端(躯体の頂点の最も遠い走り)を越えない。
    /// ⛔ 読めなければ ★ を刷って前の線(返しの溝の長さ)のまま。当たる先: 背の台の石垣を持つ棟の欄すべて(岡部 TW_Kado_Hokuto × N39_1)。</summary>
    static string BackOfFullLine(List<BackOfFull> list, List<EdoBuild.NozuraSeg> nozSegs)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        var root = GameObject.Find(GN);
        foreach (var bf in list)
        {
            var tr = bf.tr; var sg = bf.seg; string note = "";
            var mW = System.Text.RegularExpressions.Regex.Match(bf.txt, @"西の端は\s*(\S+?)\s*の見え面に突き付けて止め");
            var mE = System.Text.RegularExpressions.Regex.Match(bf.txt, @"東の端は\s*(N[0-9_]+)\s*の台の面に突き付けて閉じ");
            var nb = root == null ? null : root.transform.Find("Kakoi/" + tr.run);
            if (!mW.Success || !mE.Success || nb == null) { nozSegs.Add(sg); sb.AppendLine("  ★ 背の台の石垣 " + sg.name + "(backOf" + tr.run + " 10-10o): 西の相手・東の相手・棟が読めない(" + mW.Success + "・" + mE.Success + "・" + (nb != null) + ")── 前の線のまま"); continue; }
            // 棟の背の端(躯体の座 +0.1〜+1.2 の帯の頂点の最も遠い走り)
            float seat = nb.position.y, uMax = float.MinValue, uMin = float.MaxValue;
            foreach (var v in EdoBuild.Body(nb, 999999)) { if (v.y < seat + 0.1f || v.y > seat + 1.2f) continue; float u = Vector2.Dot(new Vector2(v.x, v.z) - tr.stop, tr.along); uMax = Mathf.Max(uMax, u); uMin = Mathf.Min(uMin, u); }
            // 始まり: 名指しの区間の線との交わり
            var sw = nozSegs.Find(q => q.name == tr.wall + "_" + mW.Groups[1].Value);
            float u0 = 0f;
            if (sw == null) note += "・★ 西の相手 " + tr.wall + "_" + mW.Groups[1].Value + " の区間が無い ── 止めの妻のまま";
            else
            {
                var I = EdoGeom.LineIntersect(tr.stop, tr.along, sw.a, sw.Dir, new Vector2(float.NaN, float.NaN));
                float uw = Vector2.Dot(I - sw.a, sw.Dir);
                if (float.IsNaN(I.x) || uw < -0.5f || uw > sw.Len + 0.5f) note += "・★ 西の相手 " + sw.name + " の線と交わらない ── 止めの妻のまま";
                else { u0 = Vector2.Dot(I - tr.stop, tr.along); note += "・始まり = " + sw.name + " の線との交わり(走り " + u0.ToString("F2", inv) + "・相手の線の " + uw.ToString("F2", inv) + "/" + sw.Len.ToString("F2", inv) + ")── 止めの駒なし・据わった駒の実面へ突き付け"; }
            }
            // 終わり: 名指しの棟の実メッシュ(線の帯)の最も手前
            var nE = root.transform.Find("Kakoi/" + mE.Groups[1].Value); float uE = uMax; string eNote = "棟の背の端(相手の実面が線の帯に無い)";
            if (nE == null) note += "・★ 東の相手 " + mE.Groups[1].Value + " が無い";
            else
                foreach (var v in EdoBuild.Body(nE, 999999))
                {
                    if (v.y > bf.crest + 0.1f) continue; var r = new Vector2(v.x, v.z) - tr.stop; float u = Vector2.Dot(r, tr.along), w = Vector2.Dot(r, tr.yard);
                    if (w < -2.0f || w > 1.2f || u <= u0 + 0.5f) continue;
                    if (u < uE) { uE = u; eNote = mE.Groups[1].Value + " の実面(" + v.x.ToString("F2", inv) + "," + v.z.ToString("F2", inv) + "," + v.y.ToString("F2", inv) + ")"; }
                }
            sg.a = tr.stop + tr.along * u0; sg.b = tr.stop + tr.along * uE; sg.noAbut[1] = eNote.StartsWith(mE.Groups[1].Value);   // 長屋は網の駒でない ⇒ 測った面で打ち切り
            nozSegs.Add(sg);
            sb.AppendLine("  背の台の石垣 " + sg.name + "(backOf" + tr.run + " 追記 2026-10-10o【硬】): 棟の背の全長 走り " + u0.ToString("F2", inv) + "〜" + uE.ToString("F2", inv) + " = " + (uE - u0).ToString("F2", inv)
                        + "m(前の線 " + Vector2.Distance(tr.stop, tr.far).ToString("F2", inv) + "m・棟の背 " + uMin.ToString("F2", inv) + "〜" + uMax.ToString("F2", inv) + ")" + note + "・終わり = " + eNote);
        }
        return sb.ToString();
    }

    /// <summary>点 q が溝(背の面から off の帯・止めの妻から返しの端 + off まで)の中なら溝の高さ、外なら NaN。</summary>
    static float TrenchAt(List<BackTrench> ts, Vector2 q)
    {
        foreach (var t in ts)
        {
            float s = Vector2.Dot(q - t.stop, t.along), d = Vector2.Dot(q - t.stop, t.yard), L = Vector2.Dot(t.far - t.stop, t.along) + t.off;
            if (s >= -0.05f - t.pre && s <= L && d >= -t.front && d <= t.off) return t.y;
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
                    if (!float.IsNaN(y)) return y;
                    // 段の外は道の地盤 ── ただし平らな面(門の内 16.50)の輪郭の中は面の高さが下限(第77巡: 返しの延長の低い端の駒が造成前の高い地盤で見付を取り 0.68 浮いた)
                    float rg = RoadGround(new Vector2(x, z)); if (_flat == null) _flat = FlatFaces(null);
                    foreach (var ff in _flat) if (ff.poly != null && EdoGeom.PIP(ff.poly, new Vector2(x, z)) && (float.IsNaN(rg) || ff.y < rg)) rg = ff.y;
                    return rg;
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
                                // 追記 2026-10-09j(h の低い端を改める): 勾配の駒 G−… を一駒ずつ足して前の地表 + reachJ まで下げ、袖の坂と同じ水平の駒で納める・切りの上限 cutJ
                                float[] gradesJ = null; float reachJ = float.NaN;
                                { int i9j = se.IndexOf("追記 2026-10-10a"); if (i9j < 0) i9j = se.IndexOf("追記 2026-10-09j");   // 10-10a が 09j を改める(後の追記が勝つ)
                                  if (i9j >= 0) { string tj = se.Substring(i9j); var gjl = new List<float>();
                                    // 駒は「先に G−…、次に G−…」の並び(⛔ 括弧の中の読み違いの説明の G−660 を拾わない ── 第79巡の初手で 16.10 に下がり過ぎた)
                                    string tjg = tj; { int iS = tj.IndexOf("先に"); if (iS >= 0) tjg = tj.Substring(iS); int iE = tjg.IndexOf("天端"); if (iE > 0) tjg = tjg.Substring(0, iE); }
                                    foreach (System.Text.RegularExpressions.Match mg in System.Text.RegularExpressions.Regex.Matches(tjg, @"G[−\-]([0-9]{3})")) gjl.Add(float.Parse(mg.Groups[1].Value, inv) / 1000f);
                                    var mr = System.Text.RegularExpressions.Regex.Match(tj, @"前の地表\s*\+\s*[0-9.]+\s*〜\s*\+?\s*([0-9.]+)\s*(?:まで下げる|を許す)"); var mcj = System.Text.RegularExpressions.Regex.Match(tj, @"切りの上限(?:を)?\s*([0-9.]+)");
                                    if (gjl.Count == 0 || !mr.Success) sb.AppendLine("    ★ " + key + " sideEnd 追記 2026-10-09j: 指図から読めない(勾配の駒・届く天端)── h のまま");
                                    else { gradesJ = gjl.ToArray(); reachJ = float.Parse(mr.Groups[1].Value, inv); sinkH = float.NaN; }
                                    if (mcj.Success) cutH = float.Parse(mcj.Groups[1].Value, inv); } }
                                string r0 = SodeSlopeSegs(key + "_SideEnd" + sw, extN, sodeTxt, extSegs, new List<SodeSlopeCheck>(), null, null, true, sinkH, gradesJ, reachJ);
                                // 足元 = 前の平らな面(門の内 16.50)── 段の造成前の地形(切る前の高い地盤)で見付を取ると、皮が面を描いた後に駒が 0.68 浮いた(第77巡【硬・浮き 0】)
                                if (_flat == null) _flat = FlatFaces(null); var flatsF = _flat;
                                Func<float, float, float> footF = (x, z) => { var qf = new Vector2(x, z); float best = float.NaN; foreach (var ff in flatsF) if (ff.poly != null && EdoGeom.PIP(ff.poly, qf) && (float.IsNaN(best) || ff.y < best)) best = ff.y; return best; };
                                foreach (var es in extSegs) { es.face = faceS; es.footAt = footF; }
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
                                        // ⭐ 追記 2026-10-10b【硬】: 切りの上限は小段だけ・小段の先の法(1:bfB)は上限なしで地山に交わるまで。法の行き先が建物の座・区画の線(道)に
                                        //   かかるなら延ばさない(普請方へ)── 測ってから効かせる(EdoBuild.BackBench.cutBenchOnly・SideEndSlopeHits)
                                        if (se.Contains("追記 2026-10-10b") && System.Text.RegularExpressions.Regex.IsMatch(se, @"切りの上限\s*[0-9.]+\s*は小段だけに当て"))
                                        {
                                            foreach (var bk in _sideEndBenches) bk.cutBenchOnly = true;
                                            string hit = SideEndSlopeHits(_sideEndBenches);
                                            if (hit != null) { foreach (var bk in _sideEndBenches) bk.cutBenchOnly = false; sb.AppendLine("    ⛔ " + key + " sideEnd 追記 2026-10-10b: 小段の先の法が " + hit + " にかかる ── 延ばさない(普請方へ)"); }
                                            else sb.AppendLine("    延長の背の法(追記 2026-10-10b): 切りの上限 " + (float.IsNaN(cutH) ? "-" : cutH.ToString("F2", inv)) + " は小段だけ・小段の先は 1:" + bfB.ToString("0.0", inv) + " で地山まで(建物の座・区画の線にかからない ⭕)【硬】");
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
    public static string Stage3c_SodeSlopeCheck() { using (OnKita()) return Stage3c_SodeSlopeCheck_(); }
    static string Stage3c_SodeSlopeCheck_()
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

    public static string Stage3_Shukaku() { using (OnKita()) return Stage3_Shukaku_(); }
    static string Stage3_Shukaku_()
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
    [MenuItem("Edo/岡部筑前守上屋敷/3b 溝を据え、溝の下の地面を下げる(皮は退役 2026-10-11)")]
    public static void Stage3bMenu() { Debug.Log("[Okabe] " + Stage3d_Mizo()); }

    /// <summary>**池の岸の断面**(指図 hosoku.zosei「gardens[NiwaShoin].hori」.danmen・EDO-0502 第61巡)を格子 gh(dx0/dz0/dstep・dnx×dnz)へ書く。
    /// 旧 Stage3b は皮の設計の格子へ、2026-10-11 からは Stage3d が細かい地形の節点へ(PondBankToTerrain)。⟶ 帯の外形(描く区域)。</summary>
    static List<Vector2[]> PondBankDesign(float[] gh, bool[] ok, float dx0, float dz0, float dstep, int dnx, int dnz, System.Text.StringBuilder sb)
    {
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
        return drawAreas;
    }

    /// <summary>池の岸の断面を細かい地形へ(2026-10-11・皮の代わり)。⛔ 地形の節点を読み、同じ式で書く(PondBankDesign)。</summary>
    static string PondBankToTerrain()
    {
        var sb = new System.Text.StringBuilder();
        var t = EdoBuild.T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        int x0, z0, w, h; Window(out x0, out z0, out w, out h);
        var H = td.GetHeights(x0, z0, w, h);
        var gh = new float[w * h]; var ok = new bool[w * h];
        for (int j = 0; j < h; j++) for (int i = 0; i < w; i++) { gh[j * w + i] = H[j, i] * td.size.y + org.y; ok[j * w + i] = true; }
        var old = (float[])gh.Clone();
        PondBankDesign(gh, ok, org.x + x0 * hs, org.z + z0 * hs, hs, w, h, sb);
        int n = 0; for (int k = 0; k < gh.Length; k++) if (Mathf.Abs(gh[k] - old[k]) > 1e-4f) { H[k / w, k % w] = (gh[k] - org.y) / td.size.y; n++; }
        if (n > 0) { td.SetHeights(x0, z0, H); AssetDatabase.SaveAssetIfDirty(td); }
        return sb.ToString().Replace("皮の格子", "地形の格子") + "  (地形へ書いた節点 " + n + ")\n";
    }

    /// <summary>溝・桝の群(Stage3d が据え、溝の下の地面を下げる)。</summary>
    static readonly string[] MizoGroups = { "BackMizo", "OmoteGesui", "FrontMizo", "FrontMizoKasa", "FrontAnkyo", "GateSteps", "DrainMizo", "DrainMizoKasa", "DrainMizoFuta", "SecMizo", "SecMizoKasa", "SecMizoFuta", "SeRojiAnkyo", "KomonFumi", "MinamiHeiMizo" };

    /// <summary>**小門の前の地面と踏み石**(指図 komon[].front ── 施主 2026-10-12「門の前の地面は道の面のまま・土を盛って段を作らない【硬】。踏み石二段は石の駒で据え、
    /// 石の脇と前は道の地面と面一【硬】。門の口の内(敷居の内)は 敷居 の床【硬】」・区画の外に置かない【硬】・EDO-0502 第113巡)。
    /// ① 門の間(両脇の長屋の妻の間 = 札の躯体の端)× 門の札の前の面 +0.05 〜 区画の線 の地面を、線から 0.7 外の道の地表(地際の張り出しの板の外)へ切り下げる
    ///   (<see cref="EdoBuild.GroundToPoly"/>・敷居の内は触らない)。② 踏み石 = 屋敷の中の石段の段石(<see cref="EdoAssets.Own.SannoDanNearestKeri"/>)を n 段 ──
    /// 蹴上 = (敷居 − 道) ÷ n(従属値)・踏面 = 屋敷の中の石段の既定 0.45・幅 = 門の口の内法(札 passage)。最上段の背を門の札の前の面へ、下の段は踏面ずつ道へ
    /// (<see cref="EdoBuild.PlaceDanStone"/>)・下は道か蓋石まで積む(<see cref="EdoBuild.StackDownToGround"/>)。③ 刷る: 段石の最も外 − 区画の線【硬 ≤ 0】・蹴上・踏面。
    /// 当たる先: 道の面より敷居の高い小門・棟門の前(いまは岡部 Tsuyomon)。</summary>
    static string PlaceKomonFront()
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var sb = new System.Text.StringBuilder(); var grp = Group("KomonFumi"); Clear(grp);
        var root = GameObject.Find(GN); if (root == null) return "";
        foreach (var o in A(Get(D, "komon")) ?? new List<object>())
        {
            var km = O(o); string fr = S(Get(km, "front")); if (fr == null || !fr.Contains("道の面のまま") || !fr.Contains("踏み石")) continue;
            string nm = S(Get(km, "name")); int e = (int)F(Get(km, "edge")); float sill = F(Get(km, "sill"));
            var mN = System.Text.RegularExpressions.Regex.Match(fr, @"踏み石\s*([一二三四1-4])\s*段"); var mSt = System.Text.RegularExpressions.Regex.Match(S(Get(km, "stands")) ?? "", @"長屋\s*(\w+)\s*と\s*(\w+)\s*の妻の間");
            var gT = root.transform.Find("Mon/" + nm); var spec = gT == null ? null : EdoPartSpec.Get(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(gT.gameObject));
            if (!mN.Success || !mSt.Success || gT == null || spec == null || spec.passage == null) { sb.AppendLine("  ★ 小門 " + nm + " の前: 段数・両脇の長屋・門の札が読めない ── 置かない"); continue; }
            int n = "一二三四".IndexOf(mN.Groups[1].Value) >= 0 ? "一二三四".IndexOf(mN.Groups[1].Value) + 1 : int.Parse(mN.Groups[1].Value);
            Vector2 ea = EdgePt(e, 0f), ax = (EdgePt(e, 1f) - ea).normalized, outN = OutNormal(e);
            var gA = Group("Kakoi").Find(mSt.Groups[1].Value); var gB = Group("Kakoi").Find(mSt.Groups[2].Value);
            if (gA == null || gB == null) { sb.AppendLine("  ★ 小門 " + nm + " の前: 長屋 " + mSt.Groups[1].Value + "/" + mSt.Groups[2].Value + " が無い ── 置かない"); continue; }
            Vector2 spA = EdoBuild.SpecBodySpanAlong(gA.gameObject, ea, ax), spB = EdoBuild.SpecBodySpanAlong(gB.gameObject, ea, ax);
            if (float.IsNaN(spA.x)) spA = EdoBuild.BodySpanAlong(gA.gameObject, ea, ax); if (float.IsNaN(spB.x)) spB = EdoBuild.BodySpanAlong(gB.gameObject, ea, ax);
            float sa = Mathf.Min(spA.y, spB.y), sb2 = Mathf.Max(spA.x, spB.x);   // 門の間(両脇の妻の間)
            Vector2 fC = EdoPartSpec.W(gT, 0f, spec.front), fO = EdoPartSpec.W(gT, 0f, spec.front + 1f); Vector2 gOut = (fO - fC).normalized;
            if (Vector2.Dot(gOut, outN) < 0f) { fC = EdoPartSpec.W(gT, 0f, -spec.back); gOut = -gOut; }   // 札の front は門の表(道の側)── 向きが逆の据えなら back
            float offF = Vector2.Dot(fC - ea, outN);   // 門の前の面の、区画の線からの離れ(負 = 内)
            System.Func<Vector2, float> roadAt = q => { float sq = Mathf.Clamp(Vector2.Dot(q - ea, ax), 0f, EdgeLen(e)); var r0 = ea + ax * sq + outN * 0.7f; return EdoBuild.Ground(r0.x, r0.y); };
            // ① 門の前の地面を道の面へ
            var poly = new[] { ea + ax * sa + outN * (offF + 0.05f), ea + ax * sb2 + outN * (offF + 0.05f), ea + ax * sb2 + outN * 0.01f, ea + ax * sa + outN * 0.01f };
            float up, dn; int nw = EdoBuild.GroundToPoly(poly, roadAt, out up, out dn);
            float sMid = Vector2.Dot(fC - ea, ax), road = roadAt(ea + ax * sMid), drop = sill - road;
            sb.AppendLine("  小門 " + nm + " の前の地面(front【硬】道の面のまま): 門の間 s " + sa.ToString("F2", inv) + "〜" + sb2.ToString("F2", inv) + " × 門の前の面(線から " + offF.ToString("F2", inv) + ")〜区画の線 を道の地表へ ── 節点 " + nw
                          + "・切り 最大 " + dn.ToString("F2", inv) + "・盛り 最大 " + up.ToString("F2", inv) + "m");
            if (drop < 0.05f) { sb.AppendLine("  小門 " + nm + " の前: 道 " + road.ToString("F2", inv) + " と敷居 " + sill.ToString("F2", inv) + " の差 " + drop.ToString("F2", inv) + " ── 踏み石を置かない"); continue; }
            // ② 踏み石
            const float FUMI = 0.45f;   // 屋敷の中の石段の既定の踏面(CLAUDE.md 座標系・寸法)── 指図に踏面は無い
            float keri = drop / n, wid = spec.passage.x1 - spec.passage.x0; int across = Mathf.Max(1, Mathf.RoundToInt(wid / 1.818f)); var wait = new List<string>(); int made = 0, stacked = 0;
            var lids = new List<GameObject>(); foreach (var gm in new[] { "SecMizoFuta", "SecMizo" }) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) lids.Add(c.gameObject);
            System.Func<float, float, float> bedAt = (x, z) => { float g = EdoBuild.Ground(x, z); float t = EdoBuild.RayToBodies(lids, new Vector3(x, sill + 1f, z), Vector3.down, 3f); return float.IsNaN(t) ? g : Mathf.Max(g, sill + 1f - t); };
            for (int i = 1; i <= n; i++)
            {
                float top = road + keri * i; string pth = EdoAssets.Own.SannoDanNearestKeri(keri, FUMI, 1.818f, i);
                if (pth == null) { sb.AppendLine("  ★ 小門 " + nm + " の前: 蹴上 " + keri.ToString("F3", inv) + " の段石が焼けていない ── 部材方へ"); break; }
                for (int j = 0; j < across; j++)
                {
                    float tt = (j - (across - 1) * 0.5f) * (wid / across);
                    Vector2 nose = fC + ax * tt + gOut * (FUMI * (n - i + 1));
                    var go = EdoBuild.PlaceDanStone(pth, grp, "Fumi_" + nm + "_" + i + "_" + j, nose, -gOut, top, wid / across, FUMI); if (go == null) continue; made++;
                    stacked += EdoBuild.StackDownToGround(go, pth, grp, go.name, 6, wait, bedAt);
                }
            }
            float noseOut = float.MinValue; foreach (Transform c in grp) foreach (var v in EdoBuild.Body(c, 4000)) noseOut = Mathf.Max(noseOut, Vector2.Dot(new Vector2(v.x, v.z) - ea, outN));
            sb.AppendLine("  小門 " + nm + " の踏み石(front): " + n + " 段・落差 " + drop.ToString("F2", inv) + "(道 " + road.ToString("F2", inv) + " → 敷居 " + sill.ToString("F2", inv) + ")・蹴上 " + keri.ToString("F3", inv) + "(従属値)・踏面 " + FUMI.ToString("F2", inv)
                          + "(屋敷の中の既定・欄に無い)・幅 " + wid.ToString("F2", inv) + "/" + across + "・段石 " + made + "・下の積み " + stacked + "・最も外 − 区画の線 " + (noseOut == float.MinValue ? "-" : noseOut.ToString("+0.000;-0.000", inv)) + (noseOut > 0.001f ? " ⛔" : " ⭕") + "【硬】");
            foreach (var w in wait) sb.AppendLine("    ★ " + w);
        }
        return sb.ToString();
    }

    /// <summary>**3d 溝**(施主裁定 2026-10-11・EDO-0502: 皮をやめ 0.25m の細かい地形へ移った)── Stage3b の皮を外し、皮の前に据えていた溝・桝を据え、
    /// 溝・桝の駒の下の地面を駒の底より下げる(EdoBuild.SinkGroundUnderMizo・⛔ 穴は開けない)。その後に練塀・垣・縁・門を床へ据え直す(従前 3b の末尾と同じ手)。
    /// ⛔ 地面の高さを部材の形から推し量らない ── 地面は造成の面(okabe_graded.bin)と指図どおりの均しだけ。溝の下げは溝の部材の札で決める(駒の底 − 0.03)。</summary>
    public static string Stage3d_Mizo() { using (OnKita()) return Stage3d_Mizo_(); }
    static string Stage3d_Mizo_()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder("溝(皮なし・細かい地形):\n");
        var es = GameObject.Find(GN) == null ? null : GameObject.Find(GN).transform.Find("EdgeSkin");
        if (es != null && es.childCount > 0) sb.AppendLine("  縁の皮を外した(塞いだ升 " + EdoBuild.ClearEdgeSkins(Group("EdgeSkin")) + ")");
        sb.AppendLine("  前の巡の桝の口の穴を塞いだ 升 " + EdoBuild.RestoreHoles(HoleUndoPath));
        sb.AppendLine("  前の巡で溝の下へ下げた地面を戻した 節点 " + EdoBuild.RestoreSunkGround(SinkUndoPath) + "(溝は地面で据えるので、下げたまま据え直すと沈む)");
        sb.AppendLine("  前の巡で溝の両脇を天端へ合わせた地面を戻した 節点 " + EdoBuild.RestoreSunkGround(BandUndoPath));
        sb.AppendLine("  前の巡で練塀の足の下を上げた地面を戻した 節点 " + EdoBuild.RestoreSunkGround(FootUndoPath));
        _mizoCoverTop.Clear(); _drainTopRep.Clear();
        sb.Append(PlaceOmoteGesui());
        sb.Append(PlaceBackGutters());
        sb.Append(PlaceFrontGutters());
        sb.Append(PlaceDrainFrontGutters());
        sb.Append(PlaceMizoSections());
        sb.Append(PlaceSeRojiAnkyo());
        sb.Append(PlaceMinamiHei());
        sb.Append(PondBankToTerrain());
        var pcs = new List<GameObject>();
        foreach (var gm in MizoGroups) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) pcs.Add(c.gameObject);
        {   // ⭐ 第111巡: 天端の線で据えた溝(D_N40_Mae・Mizo_*)の両脇の帯の地面を縁石の天端(蓋の下は蓋の天端)へ(指図 mizo.outerTop「幅 0.3m の帯」)
            var flush = new List<GameObject>(); foreach (var gm in new[] { "DrainMizo", "SecMizo" }) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) flush.Add(c.gameObject);
            // D_MinamiHei の型A(天端 = 地表【硬】・第115巡)は別に流す ── 区画の線の内の側を「上げるだけ」(台の石垣の根)にすると、小段・斜面の側の高い地面が
            //   下がらず板の外の縁より 0.07〜0.18(西の足元の溝は 0.4〜1.1)高く残った(第117巡)。南の練塀の内の溝は両側とも地表と面一(上げも下げも)
            var flushMH = new List<GameObject>();
            foreach (Transform c in Group("MinamiHeiMizo")) if (c.gameObject.activeInHierarchy && EdoBuild.MizoPieceOf(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(c.gameObject)).ok && System.IO.Path.GetFileName(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(c.gameObject)).StartsWith("Doi_Mizo_")) flushMH.Add(c.gameObject);
            var mzB = O(Get(O(Get(O(Get(D, "grading")), "omoteNagayaDai")), "mizo")); var mB = System.Text.RegularExpressions.Regex.Match(S(Get(mzB, "outerTop")) ?? "", @"幅\s*([0-9.]+)\s*m\s*の帯");
            if (mB.Success)
            {
                float bw = float.Parse(mB.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
                sb.AppendLine("  " + EdoBuild.FlushGroundToMizoTop(flush, _mizoCoverTop, bw, BandUndoPath, q => OutNormal(LidEdge(q))));
                sb.AppendLine("  D_MinamiHei の型A: " + EdoBuild.FlushGroundToMizoTop(flushMH, _mizoCoverTop, bw, BandUndoPath, null));
            }
            else sb.AppendLine("  ★ mizo.outerTop の帯の幅が読めない ── 溝の両脇の地面を合わせない");
            // ⭐ 型H の段落ちの両脇の帯を駒の側の天端へ(第116巡 ── 段の中で天端が段になるので縁石一つでは読めない・EdoBuild.FlushGroundToStepTop)
            { var stp = new List<GameObject>(); foreach (Transform c in Group("MinamiHeiMizo")) if (c.gameObject.activeInHierarchy) stp.Add(c.gameObject);
              if (mB.Success) sb.AppendLine("  " + EdoBuild.FlushGroundToStepTop(stp, float.Parse(mB.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture), BandUndoPath)); }
        }
        sb.Append(PlaceKomonFront());   // 通用門の前(komon[].front「道の面のまま・踏み石二段」・第113巡)── 溝の蓋石と両脇の帯の後
        sb.AppendLine("  " + SeatKakiOnBed());
        sb.AppendLine("  " + StackCurbOnSkin());
        sb.AppendLine("  " + SeatMonOnSkin());
        // ⭐ 下げは据え直しの後(練塀・垣の床は駒の下を下げる前の地面で測る ── 先に下げると法の見え面の下の節点を床と読み、垣が 1.5m 沈んだ・第110巡)
        sb.AppendLine("  " + EdoBuild.SinkGroundUnderMizo(pcs, 0.03f, SinkUndoPath, _mizoCoverTop));
        {   // 石垣・段の土留めの見え面から土を覗かせない(駒の下の地面を面より下げる・EdoBuild.SinkGroundUnderParts)
            var walls = new List<GameObject>(); var rt = GameObject.Find(GN).transform;
            foreach (var gm in new[] { "Dan", "Ishigaki" }) { var g = rt.Find(gm); if (g != null) foreach (Transform c in g) if (c.gameObject.activeInHierarchy) walls.Add(c.gameObject); }
            // ⭐ 背の路地の床(seRoji.southKado【硬】「石垣の見え面から 1.0 以内に 床 −0.02 より低い升を残さない」・第114巡)── 隅の駒 kado6 の稜の足は床の下へ埋まる
            var spl = SeRoji(); System.Func<float, float, float> fMin = null;
            float nyMin; var niwaK = NiwaFilledKeys(out nyMin);
            // ⭐ 練塀の内の足元の帯(heiFootSpec【硬: 浮き0】)の節点も下げの下限 ── 帯の下に埋まる野面石の端の駒(TW_Higashi_Minami 141f 天端 11.74)の天端で帯を掘り、隅の駒の足が 0.47 浮いた(第115巡)
            SeRojiHeiFoot(false); var hl = _heiFootLines; float hF = _heiFrom, hT = _heiTo;
            System.Func<float, float, float> bandMin = (x, z) => hl == null || float.IsNaN(hF) ? float.NaN : EdoBuild.FootBandAt(hl, new Vector2(x, z), hF, hT);
            //   下限は 路地の床 −0.02・帯 −0.02・角の庭 の高い方(帯は路地の床の南の端に重なる ── 路地を先に返すと帯を 12.13 へ掘った)
            fMin = (x, z) => { float m = float.NaN; System.Action<float> up = v => { if (!float.IsNaN(v) && (float.IsNaN(m) || v > m)) m = v; };
                if (spl != null && spl.ok) { float y = spl.At(new Vector2(x, z)); if (!float.IsNaN(y)) up(y - 0.02f); }
                float b = bandMin(x, z); if (!float.IsNaN(b)) up(b - 0.02f); if (niwaK.Contains(NodeKey(x, z))) up(nyMin); return m; };
            sb.AppendLine("  " + EdoBuild.SinkGroundUnderParts(walls, 0.05f, SinkUndoPath, fMin));
            // ⭐ 角の庭と練塀の内の足元の帯の下限を最後にもう一度(第116巡: 2b の盛りの後に段の法が庭の縁と隅 P4 の足元を 11.87 まで切り、庭の最低 < 12.30・P4 の足が 0.26 浮いた)
            //   盛った節点・帯の節点が下限より低ければ下限へ上げる(上げるだけ)。溝・桝の駒の外形の中は触らない(溝の中に土を入れない)。
            {
                var keep = new List<Bounds>(); foreach (var gm in MizoGroups) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) { var b = EdoBuild.RB(c.gameObject); b.Expand(new Vector3(0.04f, 0f, 0.04f)); keep.Add(b); }
                var tt = EdoBuild.T(); var td = tt.terrainData; var org = tt.transform.position; int Rr = td.heightmapResolution; float hs = td.size.x / (Rr - 1);
                var cand = new Dictionary<long, Vector3>();
                var txtN = SessionState.GetString("Okabe.niwa.filled", ""); var invN = System.Globalization.CultureInfo.InvariantCulture;
                foreach (var it in txtN.Split(new[] { ';' }, System.StringSplitOptions.RemoveEmptyEntries)) { var xy = it.Split(','); float x = float.Parse(xy[0], invN), z = float.Parse(xy[1], invN); cand[NodeKey(x, z)] = new Vector3(x, z, nyMin); }
                if (hl != null) foreach (var L in hl) { if (L.nPts == 0 || L.yAt == null || L.fillOnly) continue; for (float sv = L.sLo; sv <= L.sHi + 1e-3f; sv += 0.125f) for (float dd = hF; dd <= hT + 1e-3f; dd += 0.125f) { var q = L.a + L.ax * sv + L.inw * (L.DInAt(sv) + dd); float i = Mathf.Round((q.x - org.x) / hs), j = Mathf.Round((q.y - org.z) / hs); float x = org.x + i * hs, z = org.z + j * hs; float yb = EdoBuild.FootBandAt(hl, new Vector2(x, z), hF, hT); if (float.IsNaN(yb)) continue; long k = NodeKey(x, z); Vector3 o; if (!cand.TryGetValue(k, out o) || yb > o.z) cand[k] = new Vector3(x, z, yb); } }
                int nUpN = 0; float mUpN = 0f; var PPn = Poly; float clipN = ClipIn();
                foreach (var kv in cand)
                {
                    float x = kv.Value.x, z = kv.Value.y, y = kv.Value.z; if (float.IsNaN(y)) continue;
                    if (!EdoGeom.PIP(PPn, new Vector2(x, z)) || EdoBuild.EdgeDistPublic(PPn, new Vector2(x, z)) < clipN) continue;
                    bool under = false; foreach (var b in keep) if (x >= b.min.x && x <= b.max.x && z >= b.min.z && z <= b.max.z) { under = true; break; } if (under) continue;
                    int i = Mathf.RoundToInt((x - org.x) / hs), j = Mathf.RoundToInt((z - org.z) / hs); if (i < 0 || j < 0 || i >= Rr || j >= Rr) continue;
                    var H1 = td.GetHeights(i, j, 1, 1); float cur = H1[0, 0] * td.size.y + org.y; if (cur >= y - 1e-4f) continue;
                    H1[0, 0] = (y - org.y) / td.size.y; td.SetHeightsDelayLOD(i, j, H1); nUpN++; mUpN = Mathf.Max(mUpN, y - cur);
                }
                if (nUpN > 0) { td.SyncHeightmap(); AssetDatabase.SaveAssetIfDirty(td); }
                sb.AppendLine("  角の庭・足元の帯の下限を最後に(上げるだけ・溝の駒の外形の中は除く): 上げた節点 " + nUpN + "(最大 " + mUpN.ToString("F2") + ")");
            }
            if (spl != null && spl.ok) sb.Append(SeRojiSouthKadoReport(spl));
        }
        // ⭐ 練塀・隅を床へ据えるのは地面(溝・土留めの下げ・帯)を焼き切った後(指図 heiFootSpec.order「帯と床を先に焼く → 練塀を据える → 足を測る」・第119巡)。
        //   第118巡まで: 据えてから下げ、基壇の天端の上・溝の縁で足が 0.02〜0.58 浮いた(北・西の 7 か所と南)。床 = 地表・基壇・段・溝の駒の上面の高い方(下げるだけ・浮き0【硬】)
        sb.AppendLine("  地面の後に " + SeatHeiOnBed(Group("Kakoi"), true));
        sb.AppendLine("  " + SeatKadoToRuns(Group("Kakoi"), true) + "(下げるだけ)");
        {   // ⭐ 練塀の足の下(指図 heiFootSpec.order「帯と床を先に焼く → 練塀を run の座で据える(座より下げない)→ 足を測る」・第119巡)── 地面の下げ(溝・土留め)を
            //   焼き切った後に、座で据えた練塀・隅の腰(厚 0.69)の内外の縁まで、足の下の地面を足の底 +0.03 へ上げる(上げるだけ・溝の外接の中は触らない・区画の線から ClipIn の外は触らない)。
            //   第118巡: 3d が塀を床へ据えた後に地面を下げ、北・西の 7 か所で足が 0.02〜0.11 浮いた。当たる先: 細かい地形の上に座で据えた練塀(岡部 外周 158 駒・隅 25)
            var hp = new List<GameObject>(); foreach (Transform c in Group("Kakoi")) { if (!c.gameObject.activeInHierarchy) continue; string nm = c.name; if (nm.StartsWith("Kado_P") || nm.StartsWith("Kiri_") || nm.Contains("Hei_")) hp.Add(c.gameObject); }
            //   溝・桝は駒の向きの外形で除く(第122巡 ── 世界の外接の箱は斜めの北の辺で足の下まで覆い、浮きを残した)
            var keepP = new List<GameObject>(); foreach (var gm in MizoGroups) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) keepP.Add(c.gameObject);
            var PPf = Poly; float clipF = ClipIn();
            //   ⛔ 石垣・段の駒の下(駒の上面が地表より上)は触らない(基壇の天端・見え面の下へ土を盛らない)
            //   ⭐ 出隅の口の裏の駒(IG_Slit_・FillConvexCornerSlits)は足を支える石に数えない ── 天端は両脇の低い方なので隅の練塀の足より 0.01〜0.04 低く、
            //   足の下を「石が支える」と読んで上げず、内の縁が 0.01〜0.04 浮いた(第126巡 Kado_P32〜P38)
            var stones = new List<GameObject>(); foreach (var gm in new[] { "Ishigaki", "Dan" }) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy && !c.name.StartsWith("IG_Slit_")) stones.Add(c.gameObject);
            var stoneBed = new EdoBuild.Bed(stones); var stoneTops = new EdoBuild.PartTops(stones); var mizoTops = new EdoBuild.PartTops(keepP);
            //   足の下(凸包の中)は「石が足の底を支えている所」だけ触らない ── 台の石垣の継ぎ目の切り欠きの底(足を支えない石の面)は足に覆われるので土で埋める。
            //   ⛔ 台の石垣の天端の前の縁(区画の線から c)+0.05 より前は触らない(犬走り 0 の run は腰が法の上へ出る ── 見え面の前へ土を出さない)。第120巡 2026-10-12
            System.Func<Vector2, float> faceInAt = q => { int be = -1; float bd = float.MaxValue, bs = 0f; for (int e2 = 0; e2 < PPf.Length; e2++) { Vector2 a2 = PPf[e2], b2 = PPf[(e2 + 1) % PPf.Length]; float L2 = (b2 - a2).magnitude; if (L2 < 1e-4f) continue; float s2 = Mathf.Clamp(Vector2.Dot(q - a2, (b2 - a2) / L2), 0f, L2); float d2 = (a2 + (b2 - a2) / L2 * s2 - q).magnitude; if (d2 < bd) { bd = d2; be = e2; bs = s2; } } return be < 0 ? 0f : FaceIn(be, bs); };
            System.Func<Vector2, float> crestIn = q => { int be = -1; float bd = float.MaxValue, bs = 0f; for (int e2 = 0; e2 < PPf.Length; e2++) { Vector2 a2 = PPf[e2], b2 = PPf[(e2 + 1) % PPf.Length]; float L2 = (b2 - a2).magnitude; if (L2 < 1e-4f) continue; float s2 = Mathf.Clamp(Vector2.Dot(q - a2, (b2 - a2) / L2), 0f, L2); float d2 = (a2 + (b2 - a2) / L2 * s2 - q).magnitude; if (d2 < bd) { bd = d2; be = e2; bs = s2; } } return be < 0 ? 0f : KidanC(be, bs); };
            sb.AppendLine("  練塀の足(heiFootSpec.order): " + EdoBuild.FillUnderFoot(hp, 0.05f, 0.03f, EdoBuild.TerrainCell(EdoBuild.T()), null,
                q => EdoGeom.PIP(PPf, q) && EdoBuild.EdgeDistPublic(PPf, q) >= clipF && !(stoneBed.At(q.x, q.y) > EdoBuild.Ground(q.x, q.y) + 0.02f), FootUndoPath, 0.30f,
                (q, yb) => EdoGeom.PIP(PPf, q) && EdoBuild.EdgeDistPublic(PPf, q) >= Mathf.Max(clipF, crestIn(q) + 0.05f) && !(stoneBed.At(q.x, q.y) >= yb - 0.02f), keepP, 0.04f,
                //   犬走りの土(const.heiLine.kidan「控えの差は石垣の天端の露出(犬走り)の幅で吸う」・第122巡)── 縁の節点の 0.35 の内に台の天端(地表より上の石・上げる高さ −0.10 以上)が
                //   あれば、縁の上げを止めない(土は台の天端で受ける ⇒ 土の柱にならない)
                //   ⭐ 第126巡: 縁の 0.35 の内に溝・桝の駒の天端(上げる高さ −0.10 以上)があれば、土は駒の縁で受ける ⇒ 縁の上げを止めない
                //   (S_Hei_08 の足の内の縁が桝 G0 の縁の 0.05 手前 ── 縁の節点を 0.30 で止め、足の内の縁が 0.48 浮いた)
                (q, y) => { for (int k8 = 0; k8 < 8; k8++) { float an = k8 * Mathf.PI / 4f; float px = q.x + 0.35f * Mathf.Cos(an), pz = q.y + 0.35f * Mathf.Sin(an); float bt = stoneBed.At(px, pz), g8 = EdoBuild.Ground(px, pz); if (!float.IsNaN(bt) && !float.IsNaN(g8) && bt > g8 + 0.02f && bt >= y - 0.10f) return true;
                    string wm; float mt = mizoTops.Top(px, pz, out wm); if (!float.IsNaN(mt) && mt >= y - 0.10f) return true; } return false; },
                //   石が足を支える足の下の節点は石の天端 −0.02 まで上げる(台の裏の縁の一升の落ち込み ── 第125巡)。天端の前の縁 c +0.05 より前(見え面の側)は触らない
                //   ⭐ 第127巡: 塀の外面の線より奥(塀の下と裏)は上限なし ── 隅で両脇の天端が 0.01〜0.03 違い、天端 −0.02 の上限で内の縁が 0.02〜0.04 浮いた(Kado_P32〜P38)。
                //   塀の下と裏の土は外から見えない(天端に土を見せないのは犬走り = 外面の線より前)
                q => { if (!(EdoGeom.PIP(PPf, q) && EdoBuild.EdgeDistPublic(PPf, q) >= Mathf.Max(clipF, crestIn(q) + 0.05f))) return float.NaN; string w8; float tp = stoneTops.Top(q.x, q.y, out w8); if (float.IsNaN(tp)) return float.NaN;
                       return EdoBuild.EdgeDistPublic(PPf, q) >= faceInAt(q) + 0.05f ? float.PositiveInfinity : tp - 0.02f; }));
        }
        {   // ⭐ 犬走り(台の天端の前の縁 c から塀の腰の外の縁の一升奥まで)の地面を座の線と同じ高さ・勾配の一枚の面へ(施主 2026-10-13 第123巡【硬: 土の楔 0】)──
            //   座ちょうど(天端と面一)。台の無い所は線から 0 から。塀の裏・内の帯は触らない(帯の作法のまま)
            var bes = new List<EdoBuild.BandEdge>(); var PPb = Poly; float cellB = EdoBuild.TerrainCell(EdoBuild.T()); float qMaxB = 0f;
            foreach (var r0 in Runs)
            {
                var r = r0; if (!OnHeiLine(r) || r.lineS == null) continue; int e = r.edge;
                Vector2 a = EdgePt(e, 0f); var be = new EdoBuild.BandEdge { name = r.name, a = a, u = (EdgePt(e, 1f) - a).normalized, inw = -OutNormal(e), len = EdgeLen(e) };
                //   塀の足の外の縁 = 外面の線 − 足の出(実測 HeiFootOut: 腰あり 0.137・腰なし 0 ── const.heiLine.koshi 第124巡)
                float fo = HeiFootOut(e); qMaxB = Mathf.Max(qMaxB, FaceIn(e, 0.5f * EdgeLen(e)) - fo);
                be.q0 = sv => KidanC(e, sv) + 0.02f; be.q1 = sv => FaceIn(e, sv) - fo + cellB;
                be.qCap = sv => KidanC(e, sv) - 0.30f; be.capBatter = 4f;   // 城の石垣の法 1:0.25   // 見え面の肩(天端の前の縁の手前 0.30)は座より上の土だけ下げる
                //   段の脇の一升は低い側の座(0.25 格子の双一次が上の踏み面の高さから下の天端の上へ斜めに出る ── N_Hei_31 s9.90 で 0.92)
                //   ⭐ 低い側を採るのは段の点の脇だけ(第126巡: 坂なりの区間でも前後 1.5 升の低い方を採り、塀の足の外の縁の下の一升を勾配 × 0.375 だけ下げ、
                //   足が 0.01〜0.06 浮いた ── NW_Hei_1_1・1_2・S_Hei_16・NW_Hei_1_3 ほか)
                be.yAt = sv => { float L0 = EdgeLen(e); float sc0 = Mathf.Clamp(sv, 0f, L0); float y0 = r.SeatAt(sc0);
                    bool nearStep = false; if (r.lineS != null && r.lineStep != null) for (int k = 0; k < r.lineS.Length; k++) if (r.lineStep[k] && Mathf.Abs(r.lineS[k] - sc0) <= cellB * 1.5f + 1e-3f) { nearStep = true; break; }
                    return nearStep ? Mathf.Min(y0, Mathf.Min(r.SeatAt(Mathf.Clamp(sv - cellB * 1.5f, 0f, L0)), r.SeatAt(Mathf.Clamp(sv + cellB * 1.5f, 0f, L0)))) : y0; };
                bes.Add(be);
            }
            float clipB = ClipIn();
            float qMax = qMaxB + cellB + 0.01f;
            //   辺の端の先 1.5m まで(出隅の外の扇)── ただし区画の線から帯の奥行の内だけ(入隅で延ばした帯が隣の塀の裏へ入らない)
            sb.AppendLine("  " + EdoBuild.PlaneBand(bes, q => EdoGeom.PIP(PPb, q) && EdoBuild.EdgeDistPublic(PPb, q) >= clipB && EdoBuild.EdgeDistPublic(PPb, q) <= qMax, 0f, null, 1.5f));
        }
        {   // ⭐ 台の天端の上に土を載せない(const.heiLine.kidanCrest【硬】「台の天端に土の楔を見せない」・第122巡)── 足の下を上げた後に、外周の基壇の平らな天端の真上の節点を天端 −0.02 へ
            //   (0.25 格子で塀の外の縁の前と段の所に 0.3〜0.8 の土の帯が天端に載っていた)。区画の外・線際は触らない
            var igs3 = new List<GameObject>(); foreach (Transform c in Group("Ishigaki")) if (c.gameObject.activeInHierarchy) igs3.Add(c.gameObject);
            var PP3 = Poly; float clip3 = ClipIn();
            //   見える天端(犬走り)と塀の外の縁の一升だけ ── 線から 外面の控え(FaceIn)− 足の出(HeiFootOut: 腰あり 0.137・腰なし 0)+ 一升(⛔ 塀の裏・内の帯は削らない ── 天端の裏の端が塀の内面より奥の所で溝を掘る)
            float cell3 = EdoBuild.TerrainCell(EdoBuild.T());
            var foE = new Dictionary<int, float>();
            System.Func<int, float> footOut = e2 => { float f2; if (!foE.TryGetValue(e2, out f2)) { f2 = HeiFootOut(e2); foE[e2] = f2; } return f2; };
            System.Func<Vector2, float> faceAt = q => { int be = -1; float bd = float.MaxValue, bs = 0f; for (int e2 = 0; e2 < PP3.Length; e2++) { Vector2 a2 = PP3[e2], b2 = PP3[(e2 + 1) % PP3.Length]; float L2 = (b2 - a2).magnitude; if (L2 < 1e-4f) continue; float s2 = Mathf.Clamp(Vector2.Dot(q - a2, (b2 - a2) / L2), 0f, L2); float d2 = (a2 + (b2 - a2) / L2 * s2 - q).magnitude; if (d2 < bd) { bd = d2; be = e2; bs = s2; } } return be < 0 ? 0f : FaceIn(be, bs) - footOut(be); };
            System.Func<Vector2, float> cAt = q => { int be = -1; float bd = float.MaxValue, bs = 0f; for (int e2 = 0; e2 < PP3.Length; e2++) { Vector2 a2 = PP3[e2], b2 = PP3[(e2 + 1) % PP3.Length]; float L2 = (b2 - a2).magnitude; if (L2 < 1e-4f) continue; float s2 = Mathf.Clamp(Vector2.Dot(q - a2, (b2 - a2) / L2), 0f, L2); float d2 = (a2 + (b2 - a2) / L2 * s2 - q).magnitude; if (d2 < bd) { bd = d2; be = e2; bs = s2; } } return be < 0 ? 0f : KidanC(be, bs); };
            sb.AppendLine("  " + EdoBuild.LowerSoilOnCrest(igs3, q => EdoGeom.PIP(PP3, q) && EdoBuild.EdgeDistPublic(PP3, q) >= clip3 && EdoBuild.EdgeDistPublic(PP3, q) <= faceAt(q) + cell3
                && EdoBuild.EdgeDistPublic(PP3, q) >= cAt(q) - 0.30f, 0.02f, 0.08f, 99f));
            //   (見え面の肩 = 天端の前の縁 c の手前 0.30 まで ── それより前の根入れの土は削らない)
            //   ⭐ 第123巡: 平らな天端だけでなく法の見え面の上端(天端の前の縁の手前の一升)の上の土も下げる(flatTol 99)── 段の所で上の踏み面の土が下の台の見え面の肩に 0.6〜0.9 載っていた
            //   ⭐ 第126巡: 台の見え面の前の地面を見え面の足(区画の外の地表)より上へ出さない(const.heiLine.faceFront【硬】)── 地面を焼き切った最後に(帯・足の下の上げの後)。
            //   見え面の前 = 区画の線から天端の前の縁 c + 一升 まで。門・石段・溝の駒の下は触らない
            var keepF = new List<GameObject>(); foreach (var gm in MizoGroups) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) keepF.Add(c.gameObject);
            foreach (var gm in new[] { "GateSteps", "KomonFumi" }) { var gg = GameObject.Find(GN).transform.Find(gm); if (gg != null) foreach (Transform c in gg) if (c.gameObject.activeInHierarchy) keepF.Add(c.gameObject); }
            { var kai = GameObject.Find(GN).transform.Find("Fuzoku/Kaidan"); if (kai != null) foreach (Transform c in kai) if (c.gameObject.activeInHierarchy) keepF.Add(c.gameObject); }
            //   塀・隅の駒の下(足の凸包と軒の下)は触らない ── 塀の足は FillUnderFoot が地面で受ける(P12: S_Hei_08 の端の駒の足が辺12 の台の見え面の前に掛かり、
            //   見え面の前の土を下げて足が 1.19 浮いた ⇒ 塀の端と台の見え面の取り合いは ★ で刷る)
            //   ⭐ 第127巡: 塀は軒込みの上面でなく足の帯の凸包 + 一升で除く(軒で除くと出隅 P8・P9・P24 の見え面の前に土が残った)。
            //   区画の線から半升の内の節点も下げる(外の地表へ下げるだけ ── 区画の外の節点は触らない)── 線際の節点が残ると見え面の足に歯が立った
            var heiF = new List<GameObject>(); foreach (Transform c in Group("Kakoi")) { if (!c.gameObject.activeInHierarchy) continue; string nm = c.name; if (nm.StartsWith("Kado_P") || nm.StartsWith("Kiri_") || nm.Contains("Hei_")) heiF.Add(c.gameObject); }
            sb.AppendLine("  " + EdoBuild.LowerGroundBeforeFace(igs3, PP3, null, q => { float c = cAt(q); return c < 0.05f ? float.NaN : c + cell3; }, 0.3f, 0.05f, keepF, null, heiF));
        }
        sb.AppendLine("  " + EdoBuild.HoleUnderMasu(pcs, 0.05f, HoleUndoPath));
        sb.Append(SeRojiHeiFoot(false));   // 据えて下げた後に足を測る(heiFootSpec.order【硬】)
        // ⛔ ここで線の外を造成前へ戻さない(第114巡: 基壇の見え面は区画の外 ── 駒の下を下げた 593 節点を base_dem へ戻し、見え面を埋め戻した)。戻すのは 2b の床の延長と帯の後だけ(clipOrder)
        return sb.ToString();
    }

    /// <summary>**地面と駒の取り合いの表**(皮なし・2026-10-11)── 第109巡まで Stage3b が皮の後に刷っていた二つの表を、描かれた地表(細かい地形)で刷る:
    /// ① 地表と駒の隙・地表が駒の天端に被る(EdoBuild.SkinGapTable・同じ部材の組: 段の土留め・溝・段の土留めに接する外周の石垣・石段)
    /// ② 野面の見え面の土(EdoBuild.NozuraSeamReport・光線)。⛔ 直さない ── 測るだけ。</summary>
    [MenuItem("Edo/岡部筑前守上屋敷/検: 地面と駒の取り合い(皮なし)")]
    public static void GroundQAMenu() { Debug.Log("[Okabe] " + GroundQA()); }
    public static string GroundQA() { using (OnKita()) return GroundQA_(); }
    static string GroundQA_()
    {
        var sb = new System.Text.StringBuilder("地面と駒の取り合い(皮なし・地形 " + EdoBuild.T().name + "):\n");
        float tol = ImplTol("gradeTol", 0.30f);
        var root = GameObject.Find(GN); if (root == null) return sb + "  ⛔ " + GN + " が無い";
        var parts = new List<GameObject>(); var danB = new List<Bounds>();
        var dn = root.transform.Find("Dan");
        if (dn != null) foreach (Transform c in dn) if (c.gameObject.activeInHierarchy) { parts.Add(c.gameObject); danB.Add(EdoBuild.RB(c.gameObject)); }
        foreach (var gm in MizoGroups) { var g = root.transform.Find(gm); if (g != null) foreach (Transform c in g) if (c.gameObject.activeInHierarchy) parts.Add(c.gameObject); }
        var ig = root.transform.Find("Ishigaki"); int igN = 0;
        if (ig != null)
            foreach (Transform c in ig)
            {
                if (!c.gameObject.activeInHierarchy) continue;
                var b = EdoBuild.RB(c.gameObject); if (b.size == Vector3.zero) continue; b.Expand(1f);
                foreach (var db in danB) if (db.Intersects(b)) { parts.Add(c.gameObject); igN++; break; }
            }
        var kai = root.transform.Find("Fuzoku/Kaidan"); int stN = 0;
        if (kai != null)
            foreach (var r in kai.GetComponentsInChildren<MeshRenderer>())
            {
                var b = r.bounds; b.Expand(4f);
                foreach (var db in danB) if (db.Intersects(b)) { parts.Add(r.gameObject); stN++; break; }
            }
        sb.AppendLine("  部材 " + parts.Count + "(段の土留めに接する外周の石垣 " + igN + "・石段 " + stN + ")");
        sb.Append(EdoBuild.SkinGapTable(parts, FlatFaces(null), tol));
        if (dn != null) sb.AppendLine("  " + EdoBuild.NozuraSeamReport(root.transform, dn, null).Replace("\n", "\n  "));
        return sb.ToString();
    }

    public static string Stage3b_Hifu() { using (OnKita()) return Stage3b_Hifu_(); }
    static string Stage3b_Hifu_()
    {
        var gate = ReviewGate(); if (gate != null) return gate;
        var sb = new System.Text.StringBuilder("縁の皮:\n");
        float tol = ImplTol("gradeTol", float.NaN);
        if (float.IsNaN(tol)) return sb + "  ⛔ 算出物 checks.gradeTol が無い ── 皮を起こさない(既定値で埋めない)";
        var grp = Group("EdgeSkin");
        int filled = EdoBuild.ClearEdgeSkins(grp);
        // ⭐ 溝は皮より先に置き、皮が避ける部材に入れる(第81巡【硬】)── 皮の後に置くと、皮(面の 16.50)と穴でない升の地形が溝の中を覆った(第80巡 18 駒中 13)
        sb.Append(PlaceOmoteGesui());     // 指図 Kadonouchi.omoteGesui(表門脇の下水)── 背の雨落ちの落ち先なので先に解く
        sb.Append(PlaceBackGutters());    // 指図 flat 追記 2026-10-10a の背の雨落ち(第80巡)
        sb.Append(PlaceFrontGutters());   // 指図 roadEdge 追記 2026-10-10m・runs[].front の前の下水溝(第95巡)
        sb.Append(PlaceDrainFrontGutters());   // 指図 drains[].route「<棟> の前の全長(s …)に区画の内の石組の下水溝」(D_N40_Mae・第103巡)
        sb.Append(PlaceMizoSections());        // 指図 grading.omoteNagayaDai.mizo.sections(Mizo_Kita ほか・第108巡)── D_N40_Mae の尻を続ける
        sb.Append(PlaceSeRojiAnkyo());         // 指図 drains[D_SeRoji].make(背の路地の桝と型M の吐口・第109巡)── 落とし先の溝(Mizo_*)の後
        // 部材 = 段の土留め(Dan の駒)+ その口を切って上る石段(駒の外形から 2m 以内の段)
        var parts = new List<GameObject>(); var band = new List<GameObject>();
        var danB = new List<Bounds>();
        foreach (Transform c in Group("Dan")) if (c.gameObject.activeInHierarchy) { parts.Add(c.gameObject); band.Add(c.gameObject); danB.Add(EdoBuild.RB(c.gameObject)); }
        foreach (var gm in new[] { "BackMizo", "OmoteGesui", "FrontMizo", "FrontMizoKasa", "FrontAnkyo", "GateSteps", "DrainMizo", "DrainMizoKasa", "DrainMizoFuta", "SecMizo", "SecMizoKasa", "SecMizoFuta", "SeRojiAnkyo" }) foreach (Transform c in Group(gm)) if (c.gameObject.activeInHierarchy) parts.Add(c.gameObject);   // 溝(皮が避ける・帯は持たない)
        int stairN = 0, igN = 0, igOut = 0;
        var root = GameObject.Find(GN); var kai = root == null ? null : root.transform.Find("Fuzoku/Kaidan");
        // ⭐ 外周の石垣(Ishigaki)の駒のうち段の土留めの駒に接する物(外接 1m 内)も部材として渡す(2026-10-04 EDO-0502 第10巡):
        //   皮は渡された駒しか知らない ── 段の土留め 辺24 の穴の升が外周の基壇の石垣 IG_S_Hei_21 の見え面に掛かり、皮が設計の地盤
        //   (法で 7.6 → 11)を石垣の見え面の上に描いて、2m おきの土の三角(最大 +2.33m)を立てた。天端の帯で篩う(見え面の前へ皮を出さない)。
        //   当たる先: 段の土留めと外周の石垣が取り合う所(岡部の西の辺24・南の辺)。
        var ig = root == null ? null : root.transform.Find("Ishigaki"); var outBase = OutsideBase();
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
                if (!near && EdoBuild.OutsideFootExcess(c.gameObject, Poly, outBase, out fa) > 0.10f) { near = true; igOut++; }
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
        // ⭐ 道の側の腰石垣と踏み段の前は道の現地形(指図 roadEdge「土の段・土の法を道に見せない」【硬】・規則9 区画の外の道は触らない・第83巡)── 設計の地盤
        //   (算出物 graded・区画の外は道の現況と違う)を、見え面の足元の線から区画の線の外 1.5 まで地形の高さに置き換え、皮の縁を道の地形に合わせる。
        //   ⛔ 第82巡は 0.5m ごとの平らな面にして段の凸凹が立ち、石垣の下半分と樋口を埋めた
        {
            if (_road == null) _road = RoadEdgePlanOf(); var rd = _road; int nRd = 0;
            if (rd != null && rd.ok)
            {
                var spansF = new List<Vector2>(rd.spans); if (rd.hasGate) spansF.Add(new Vector2(rd.ps0, rd.ps1)); var roadCache = new Dictionary<long, float>();
                for (int j = 0; j < dnz; j++)
                    for (int i = 0; i < dnx; i++)
                    {
                        int k = j * dnx + i; var q = new Vector2(dx0 + i * dstep, dz0 + j * dstep);
                        float sAl = Vector2.Dot(q - rd.ea, rd.ax), dOut = Vector2.Dot(q - rd.ea, rd.outN);
                        foreach (var sp in spansF)
                        {
                            if (sAl < sp.x || sAl > sp.y) continue;
                            bool atGate = sp.x == rd.ps0 && sp.y == rd.ps1; float yR = RoadAtS(rd, sAl);
                            float dIn = atGate ? 0f : rd.setback - rd.batter * (rd.yTop - yR);
                            if (dOut < -dIn || dOut > 1.5f) continue;
                            // 道は区画の外の皮と同じ測り(OutsideOwnGround ── 区画の内の地形の節点は造成前の地盤へ)。⛔ 今の地形の 2m 格子は台の 16.50 を線の外へ一次で引き、
                            //   門の口の段鼻の前を 16.26〜16.38 と読んで段の前に土の山を立てた(第93巡)
                            bool repR; float gy = EdoBuild.OutsideOwnGround(EdoBuild.T(), q.x, q.y, Poly, EdoBuild.BaseDem(), null, roadCache, out repR); if (float.IsNaN(gy)) continue;
                            if (dOut < 0f && (sAl < sp.x || sAl > sp.y)) continue;   // 区画の内は石垣の見え面の前だけ(端の先は台の面のまま ── 第83巡の一回目: 端の先で 1.97 の土の面)
                            if (dOut >= 0f || gy < gh[k]) { gh[k] = gy; ok[k] = true; nRd++; }   // 区画の内(見え面の足元〜線)は道より高くしない
                            break;
                        }
                    }
            }
            if (nRd > 0) sb.AppendLine("  道の側の腰石垣と踏み段の前を道の現地形へ写した設計の節点 " + nRd);
        }
        // ⭐ 坂の路盤の帯(芯から幅/2)の中は、坂の縦断(RampAxis = GradeRamps と同じ節点)を皮の格子で引く(2026-10-07 EDO-0502 施主指摘 B):
        //   今の地形(2m 格子)を写すだけだと、石段の上がり口の段石の背(天端 −0.02 の 0.45m の平ら)を描けず、皮が段石の背で 0.3〜0.85 窪んで
        //   土の斜面で立ち上がった。当たる先: 石段を名指す坂(kaidans[].atRoute)の路盤すべて。
        {
            int nr = 0; var f = Grid; float ken = C("ken");
            foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
            {
                var r = O(o); if (r == null) continue;
                if (!RampDrawnByProfile(r)) continue;   // 石段を名指す坂と石垣で挟んだ坂だけ(芯を寄せる坂 toeFix は均した地形のまま)
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
            var srp = SeRoji(); int nr2 = 0;
            if (srp.ok)
                for (int j = 0; j < dnz; j++)
                    for (int i = 0; i < dnx; i++)
                    {
                        int k = j * dnx + i; if (!ok[k]) continue;
                        float ty = srp.At(new Vector2(dx0 + i * dstep, dz0 + j * dstep));
                        if (!float.IsNaN(ty) && ty < gh[k] - 1e-4f) { gh[k] = ty; nr2++; }
                    }
            sb.AppendLine("  背の路地の床を設計の地盤へ写した節点 " + nr2 + (srp.ok ? "" : "(★ 解けない: " + srp.why + ")"));
        }
        // ⭐ 池の岸の断面(指図 hosoku.zosei「gardens[NiwaShoin].hori」.danmen・EDO-0502 第61巡)を皮の格子で設計の地盤へ ──
        //   算出物 graded は 1m・地形は 2m 格子で、汀の外 2〜3m まで地表が水面より低く描かれ、水面が板のように浮いた(第60巡 縁の 1520/3203 点)。
        //   汀線からの符号付きの距離 d(陸 +)で: 陸は max(設計, 州浜なら 水面 + d/5 ≤ 岸・石組/乱杭なら 岸)、水の中は 型の棚と法(底 bedY で止める)。
        //   型 = 最寄りの護岸の区間(石組護岸・州浜・乱杭)の折れ線が 1.5m 以内ならその型、無ければ州浜。中島(設計 > 水面)は触らない。
        //   描くのは帯 |d| ≤ 3m(drawAreas として CutEdgeSkin に渡す)。当たる先: 算出物の汀線を持つ庭(岡部 書院の泉水)。
        var drawAreas = PondBankDesign(gh, ok, dx0, dz0, dstep, dnx, dnz, sb);
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
            var tdP = EdoBuild.T().terrainData; float padCell = tdP.size.x / (tdP.heightmapResolution - 1);
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
        var buriedParts = new HashSet<GameObject>(); var buryLo = new Dictionary<GameObject, float>(); var buryAim = new Dictionary<GameObject, float>(); float ceilRelax = 0f, buryFaceCover = 0f;
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
                    if (bury) { top = pTop; buriedParts.Add(eg); if (!float.IsNaN(c.buryMin)) buryLo[eg] = pTop + c.buryMin; if (!float.IsNaN(c.buryAim)) buryAim[eg] = pTop + c.buryAim; if (!float.IsNaN(c.ceilRelax)) ceilRelax = Mathf.Max(ceilRelax, c.ceilRelax); if (!float.IsNaN(c.faceCover)) buryFaceCover = Mathf.Max(buryFaceCover, c.faceCover); }   // 検めは端の駒の天端で・埋める駒は皮の被りの検めから外す(SkinDesign.buried)
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
        // 入隅の通しの駒(const.abutOrder 追記 2026-10-10o「延長は土に埋め(根入れと同じ扱いで埋没に数えない)」【硬】・PlaceNozuraNet が名に "_Tooshi" を付ける)
        //   ── 設計で土に埋める駒(見え面の上限・被りの検めから外す)
        { int nT = 0; var dnT = Group("Dan"); foreach (Transform t in dnT) if (t.gameObject.activeInHierarchy && t.name.Contains("_Tooshi")) { buriedParts.Add(t.gameObject); nT++; }
          if (nT > 0) sb.AppendLine("  入隅の通しの駒(abutOrder 10-10o): 土に埋める駒 " + nT + "(見え面の上限・被りの検めから外す)"); }
        var crestCover = NozuraCrestCoverOf(sb, buriedParts);
        var design = new EdoBuild.SkinDesign
        {
            x0 = dx0, z0 = dz0, step = dstep, nx = dnx, nz = dnz, h = gh, ok = ok,
            batterCut = C("batterCut"), batterFill = C("batterFill"), baseAt = EdoBuild.BaseDem(), own = Poly, hold = hold, buried = buriedParts, flats = FlatFacesOf(buriedParts, sb), buryLo = buryLo, mikiriDrop = MikiriSoil(0), mikiriFlat = MikiriSoil(1), mikiriBatter = MikiriSoil(2), buryAim = buryAim, ceilRelax = ceilRelax, buryFaceCover = buryFaceCover, fillSlope = FillEdgeSlope(sb), toeBandW = ToeBand(sb, 0), toeBandRise = ToeBand(null, 1), toeBackNear = ToeBandBack(sb, 0), toeBackFar = ToeBandBack(null, 1), toeBackCrestDrop = ToeBandBack(null, 2),
            crestCover = crestCover
        };
        // ⭐ 区画の外の節点は区画の外の地盤(今の地形・区画の内と駒の下の節点は造成前)で持たせる(EDO-0502 第29巡)── 外周の石垣の見え面の前
        { var bk = design.baseAt; design.baseAt = OutsideBase(); EdoBuild.DesignOutsideOwn(design, parts, sb); design.baseAt = bk; }   // 区画の外の描きだけ道の線際の均しを見る(OutsideBase・第105巡)
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
                                       crestBandParts: band, plantPoints: plant, faceKeepOut: keepNiwa, drawAreas: drawAreas,
                                       solve: true);   // ⭐ 皮の高さは一点ごとの [lo, hi] と狙い y* で解く(EdoBuild.SkinHeightSolve・2026-10-10 施主裁定「作り直す」)── 山王・土井は従来の段3〜3f
        AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
        sb.Append("  " + EdoBuild.SkinSolveLog.Replace("\n", "\n  ").TrimEnd() + "\n");
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
        { var rtH = GameObject.Find(GN); if (rtH != null) { sb.AppendLine("  " + EdoBuild.CloseUncoveredHoles(rtH.transform.Find("EdgeSkin"), Poly)); AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData); } }
        // 野面の継ぎ目の段差・見え面から土が覗く所(光線・EDO-0502 第64巡)── 皮を起こし直した後でないと土の側が測れない
        { var rt = GameObject.Find(GN); var dn = rt == null ? null : rt.transform.Find("Dan");
          if (dn != null) sb.AppendLine("  " + EdoBuild.NozuraSeamReport(rt.transform, dn, rt.transform.Find("EdgeSkin")).Replace("\n", "\n  "));
          if (dn != null && rt.transform.Find("EdgeSkin") != null) sb.AppendLine("  " + EdoBuild.NozuraSkinPlaneCheck(dn, rt.transform.Find("EdgeSkin")));
          if (rt.transform.Find("EdgeSkin") != null) sb.AppendLine("  " + SteepEdgeReport(rt.transform));
          if (rt.transform.Find("EdgeSkin") != null) sb.AppendLine("  " + FlatReport(rt.transform, buriedParts));
          if (rt.transform.Find("EdgeSkin") != null) sb.AppendLine("  " + RoadEdgeEndReport(rt.transform));
          // 二段の重なり(const.abutOrder 追記 2026-10-10i【硬】「上の段の法尻は下の段の控えの後端 +c より内」)── 上の段 = 底が下の段の天端 − gradeTol 以上の駒(EdoBuild.NozuraCrestCover.TwoTierOverlaps)
          if (dn != null)
          {
              string ao = S(Get(O(D["const"]), "abutOrder")) ?? ""; var mC = System.Text.RegularExpressions.Regex.Match(ao, @"控えの後端\s*\+\s*([0-9.]+)\s*より内");
              if (!ao.Contains("追記 2026-10-10i") || !mC.Success) sb.AppendLine("  二段の重なり: ★ const.abutOrder 追記 2026-10-10i の「控えの後端 +c より内」が読めない ── 数えない");
              else
              {
                  float clr = float.Parse(mC.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture); var tw = new EdoBuild.NozuraCrestCover(); var tl = new System.Text.StringBuilder();
                  foreach (Transform c in dn) { if (!c.gameObject.activeInHierarchy) continue; var mfc = c.GetComponentInChildren<MeshFilter>(); if (mfc == null || mfc.sharedMesh == null || !mfc.sharedMesh.name.Contains("Nozura")) continue; bool kd = mfc.sharedMesh.name.Contains("_Kado"); try { tw.Add(c.gameObject, kd); } catch (System.Exception) { } }
                  int nTT = tw.TwoTierOverlaps(tol, clr, tl);
                  sb.AppendLine("  二段の重なり(abutOrder 10-10i・上の段の底 ≥ 下の段の天端 − " + tol.ToString("F2") + "・控えの後端 + " + clr.ToString("F2") + "・硬 0): " + nTT + (nTT > 0 ? " ⛔" : " ⭕") + "(野面の駒 " + tw.pieces + ")"); sb.Append(tl.ToString());
              }
          } }
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
        // 指図 sideEnd 追記 2026-10-10b「見え面の前の土は 16.50 まで下げる(kadoFace と同じ)【硬】」⇒ 延長の駒(<欄>_SideEnd)も隅の駒と同じ見え面の前の下げに入れる(第81巡)
        var sideEndFront = new List<string>(); float sideEndFloor = float.NaN;
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
        { var t2 = O(o2); string se2 = t2 == null ? null : S(Get(t2, "sideEnd")); int i10b = se2 == null ? -1 : se2.IndexOf("追記 2026-10-10b");
          var mFl = i10b < 0 ? null : System.Text.RegularExpressions.Regex.Match(se2.Substring(i10b), @"見え面の前の土は\s*([0-9.]+)\s*まで下げる");
          if (mFl != null && mFl.Success) sideEndFloor = float.Parse(mFl.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
          if (i10b >= 0 && se2.Substring(i10b).Contains("見え面の前の土") && se2.Substring(i10b).Contains("kadoFace と同じ")) { sideEndFront.Add(S(Get(t2, "name")) + "_SideEnd"); if (!cc.kadoFront) sb.AppendLine("  ★ sideEnd 追記 2026-10-10b: kadoFace が効いていない ── 延長の見え面の前を下げられない"); } }
        foreach (Transform c in Group("Dan"))
        {
            if (!c.gameObject.activeInHierarchy) continue;
            var mf = c.GetComponentInChildren<MeshFilter>(); string ap = mf == null || mf.sharedMesh == null ? "" : AssetDatabase.GetAssetPath(mf.sharedMesh);
            if (!ap.Contains("Nozura")) continue;
            if (ap.Contains("Mikiri")) continue;   // 見切り石は頭を見せる石 ── 天端の裏石の帯の土(①の被せ)を当てない(roadEdge・cuts 追記 2026-10-10h【硬】)
            if (buried != null && buried.Contains(c.gameObject)) continue;   // 設計で土に埋める駒(袖の低い端)は帯を持たない
            bool kadoType = System.IO.Path.GetFileName(ap).Contains("_Kado"), kado = kadoType; if (kado) nk++;
            if (!kado) foreach (var sf in sideEndFront) if (c.name.StartsWith(sf)) { kado = true; if (!float.IsNaN(sideEndFloor)) cc.kadoFloor[c.gameObject] = sideEndFloor; break; }
            cc.Add(c.gameObject, kado, kadoType);   // 見え面の二面は隅の型(_Kado)の駒だけ ── 延長の直線の駒は見え面の前の扱いだけ隅に倣う(第89巡)
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
        // 指図 roadEdge 追記 2026-10-10j【硬】「石垣と長屋の間の帯は 16.50 で平ら、天端の裏の盛りは当てない」── 道の側の腰石垣の駒の外形と控えの帯(back)を盛らない所へ
        var roadHulls = new List<Vector2[]>(); int nRoadK = 0;
        { if (_road == null) _road = RoadEdgePlanOf(); var rk = _road;
          if (rk != null && rk.ok && rk.j10 && root != null)
              foreach (Transform c in Group("Dan"))
              {
                  if (!c.gameObject.activeInHierarchy || !c.name.Contains("_RoadEdge_")) continue;
                  var pts = new List<Vector2>(); foreach (var v in EdoBuild.Body(c, 2000)) pts.Add(new Vector2(v.x, v.z)); if (pts.Count < 3) continue;
                  var h = EdoBuild.ConvexHull2(pts); if (h.Count >= 3) { roadHulls.Add(h.ToArray()); nRoadK++; }
              } }
        // 追記 2026-10-10k【硬】「(妻の面の石垣の)天端の裏に盛りを当てない」── 妻の面の天端の前の線から背へ bk・隣の棟の背の一間の線から道の側の線まで(⛔ 駒の名で拾わない ── 線で)
        RoadEdgePlan rkT = _road; bool tsumaKeep = rkT != null && rkT.ok && rkT.k10 && !float.IsNaN(rkT.sCorner) && !float.IsNaN(rkT.nbD0);
        float sgT = tsumaKeep && rkT.gable > rkT.Mid ? 1f : -1f;
        cc.keepOut = q =>
        {
            if (tsumaKeep) { float bs = sgT * (rkT.sCorner - Vector2.Dot(q - rkT.ea, rkT.ax)), dq = Vector2.Dot(q - rkT.ea, rkT.outN); if (bs >= -0.05f && bs <= bk && dq >= rkT.nbD0 - ES - 0.3f && dq <= 0.05f) return true; }
            for (int i = 0; i < roadHulls.Count; i++) if (EdoGeom.PIP(roadHulls[i], q) || EdoGeom.DistToPolyEdge(roadHulls[i], q) < bk) return true;
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
                    + " ── 野面の駒 " + cc.pieces + "(うち隅 " + nk + ")・面 " + cc.faces + "・盛らない所 = 長屋 " + nNag + " の背の一間・Kakoi " + hulls.Count + " の犬走り " + inu.ToString("F2") + (nRoadK > 0 ? "・道の側の腰石垣 " + nRoadK + " 駒の天端の裏(roadEdge 追記 2026-10-10j【硬】)" : ""));
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
            foreach (System.Text.RegularExpressions.Match mb2 in System.Text.RegularExpressions.Regex.Matches(fl, @"(N[0-9_]+)\s*の台まで延ばし"))
            { var kk2 = root.Find("Kakoi/" + mb2.Groups[1].Value); if (kk2 == null) continue; var p2b = new List<Vector2>(); foreach (var v in EdoBuild.Body(kk2, 4000)) p2b.Add(new Vector2(v.x, v.z)); if (p2b.Count >= 3) footH.Add(EdoBuild.ConvexHull2(p2b).ToArray()); }
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
            // 追記 2026-10-10a: 縁の土の板を棟の台まで延ばす(棟の外形まで帯)── 棟の外形は躯体の頂点の凸包(長屋は長方形)
            foreach (System.Text.RegularExpressions.Match mb2 in System.Text.RegularExpressions.Regex.Matches(fl, @"(N[0-9_]+)\s*の台まで延ばし"))
            { var kk2 = GameObject.Find(GN) == null ? null : GameObject.Find(GN).transform.Find("Kakoi/" + mb2.Groups[1].Value);
              if (kk2 == null) { sb.AppendLine("  ★ " + nm + " flat 追記 2026-10-10a: 棟 " + mb2.Groups[1].Value + " が無い"); continue; }
              var p2b = new List<Vector2>(); foreach (var v in EdoBuild.Body(kk2, 4000)) p2b.Add(new Vector2(v.x, v.z)); if (p2b.Count >= 3 && bandH != null) { bandH.Add(EdoBuild.ConvexHull2(p2b).ToArray()); sb.AppendLine("  面の平らの帯 " + nm + ": " + mb2.Groups[1].Value + " の台まで(追記 2026-10-10a)"); } }
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


    /// <summary>面の名 → 高さ(terraces[].y)。無ければ NaN。</summary>
    static float S2F(object faceName)
    { string nm = S(faceName); foreach (var o3 in A(D["terraces"]) ?? new List<object>()) { var t3 = O(o3); if (t3 != null && S(Get(t3, "name")) == nm) return F(Get(t3, "y")); } return float.NaN; }

    /// <summary>**棟の背の雨落ちの浅い石組の溝**(指図 terraces[].flat 追記 2026-10-10a「&lt;棟&gt; の背の雨落ちは y の面の上に浅い石組の溝(幅 w・深さ d まで【柔】)で受け、
    /// 長手に 1/n で門の内の下水を経て表門脇の下水へ【硬】」・第80巡)。駒 = 在庫の石組の溝 1m(EdoAssets.Own.DoiMizo の型 A ── 内の幅 0.30・縁石・天端 +0.02 は部材の札)。
    /// 線 = 棟の背の面(実メッシュ FaceOut・SpecBodySpanAlong)から駒の半幅 + 0.02 前・棟の背の長さ。下流 = 表門(回転間グリッドの原点)に近い端。
    /// 底は EdoBuild.SolveMizoBottom(1/n の下り【硬】・深さ ≤ d【柔】)、据えは EdoBuild.LayMizo(地面より浮かない【硬】)。⛔ 部材が無ければ置かず ★。
    /// 当たる先: 欄 flat に「背の雨落ちは…浅い石組の溝」を持つ面(岡部 Kadonouchi × N39_0)。</summary>
    /// <summary>**道の側の腰石垣と門の口の踏み段**(指図 terraces[].roadEdge・普請方 2026-10-10c・EDO-0502 第82巡)。門長屋(gate.host)の走りの辺に沿い、
    /// 天端 = 欄の高さ一直線【硬】・見え面は区画の線の内【硬】(天端の前の線を線から 法 ×(天端 − 道の最も低い所 + 根入れ)+ 0.02 退ける ── 法は駒の実測 FaceBatterOf)・
    /// 段(天端 − 道)が欄の値を切る所で打ち切り【硬】・門の口(札の passage)は空けて踏み段。道 = 区画の線の外 0.5m の地形。⛔ 座標を書かない ── 毎回測る。</summary>
    class RoadEdgePlan { public bool ok, h10, j10, k10, hasGate; public float anchor = float.NaN; public float Mid { get { return hasGate ? 0.5f * (ps0 + ps1) : anchor; } } public string tsumaSeg; public float sCorner = float.NaN, nbFace = float.NaN, nbLow = float.NaN, nbD0 = float.NaN, nbD1 = float.NaN, tsumaBatterMax = float.NaN; public float mikiriDrop = float.NaN, gable = float.NaN, endDropMax = float.NaN, depth = float.NaN; public string why, terrace, trimNote, gableNb; public int e; public Vector2 ea, ax, outN; public float yTop, cutDrop, fumi, ps0, ps1, sRun0, sRun1, batter, setback, neiri; public Transform host; public EdoPartSpec.Spec spec; public List<Vector2> spans = new List<Vector2>(); }
    static RoadEdgePlan _road;
    /// <summary>道の高さ(線の外 0.5)── 皮が区画の外を描くのと同じ測り(EdoBuild.OutsideOwnGround: 区画の内の地形の節点は造成前の地盤へ)。
    /// ⛔ 地形をそのまま引かない ── 2m 格子が台の 16.50 を線の外へ一次で引き、門の口の道を 16.23 と読んで踏み段が皮(道 15.85)の上に 0.25 浮いた(第92巡)。</summary>
    static float RoadAtS(RoadEdgePlan r, float sAl) { var q = r.ea + r.ax * sAl + r.outN * 0.5f; bool rep; return EdoBuild.OutsideOwnGround(EdoBuild.T(), q.x, q.y, Poly, EdoBuild.BaseDem(), null, new Dictionary<long, float>(), out rep); }
    /// <summary>腰石垣の棟 = roadEdge の文が「&lt;棟&gt; の前」と最初に名指す run(指図の名・⛔ C# に名を書かない)。名指しが無ければ gate.host。
    /// 当たる先: 名指しの棟と門長屋が分かれる邸(岡部 B 案: 腰石垣 N39_0 / 門長屋 N40_0)。</summary>
    static string RoadEdgeHost(string tx)
    {
        string best = null; int bi = int.MaxValue;
        foreach (var rn in Runs) { if (rn.name == null) continue; int i = tx.IndexOf(rn.name + " の前", System.StringComparison.Ordinal); if (i >= 0 && i < bi) { bi = i; best = rn.name; } }
        return best ?? S(Get(O(Get(D, "gate")), "host"));
    }
    static RoadEdgePlan RoadEdgePlanOf()
    {
        var r = new RoadEdgePlan(); var inv = System.Globalization.CultureInfo.InvariantCulture; var root = GameObject.Find(GN); if (root == null) { r.why = "邸が無い"; return r; }
        foreach (var o in A(Get(D, "terraces")) ?? new List<object>())
        {
            var t = O(o); string tx = S(Get(t, "roadEdge")); if (tx == null) continue; r.terrace = S(Get(t, "name"));
            var mT = System.Text.RegularExpressions.Regex.Match(tx, @"天端は台の\s*([0-9.]+)"); var mC = System.Text.RegularExpressions.Regex.Match(tx, @"段が\s*([0-9.]+)\s*を切る所");
            var mF = System.Text.RegularExpressions.Regex.Match(tx, @"踏面\s*([0-9.]+)\s*を狙う");
            if (!mT.Success || !mC.Success) { r.why = "天端・打ち切りの段が読めない"; return r; }
            r.yTop = float.Parse(mT.Groups[1].Value, inv); r.cutDrop = float.Parse(mC.Groups[1].Value, inv); r.fumi = mF.Success ? float.Parse(mF.Groups[1].Value, inv) : float.NaN;
            // 根入れ = sideEnd が名指す野面の根入れ(「根入れ 0.45 以上」)── 無ければ ★
            float ne = float.NaN; foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var m2 = System.Text.RegularExpressions.Regex.Match(S(Get(O(o2), "sideEnd")) ?? "", @"根入れ\s*([0-9.]+)\s*以上"); if (m2.Success) ne = float.Parse(m2.Groups[1].Value, inv); }
            if (float.IsNaN(ne)) { r.why = "野面の根入れが指図に無い"; return r; } r.neiri = ne;
            // 腰石垣の棟 = 欄の文が「<棟> の前」と名指す棟(⛔ gate.host で取らない ── 表門が辺40 へ移って腰石垣が門長屋ごと辺40 へ行った・第101巡)。名指しが無ければ門長屋
            string host = RoadEdgeHost(tx); int ri = -1; for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == host) ri = k;
            var hT = host == null ? null : root.transform.Find("Kakoi/" + host); if (ri < 0 || hT == null) { r.why = "腰石垣の棟 " + (host ?? "-") + " が無い"; return r; }
            var spec = EdoPartSpec.Get(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(hT.gameObject));
            // 門の口 = 棟の札の通り口。口の無い棟(普通の長屋)は口の縁も踏み段も無い ── 腰石垣は棟の前を一続きに通す
            r.hasGate = spec != null && spec.passage != null && spec.passage.x1 - spec.passage.x0 >= 0.1f;
            if (r.hasGate && float.IsNaN(r.fumi)) { r.why = "門の口の踏み段の踏面が読めない"; return r; }
            r.host = hT; r.spec = spec; r.e = Runs[ri].edge; r.ea = EdgePt(r.e, 0f); r.ax = (EdgePt(r.e, 1f) - r.ea).normalized; r.outN = OutNormal(r.e);
            r.sRun0 = Runs[ri].s0; r.sRun1 = Runs[ri].s1;
            if (r.hasGate)
            { float p0 = Vector2.Dot(EdoPartSpec.W(hT, spec.passage.x0, spec.front) - r.ea, r.ax), p1 = Vector2.Dot(EdoPartSpec.W(hT, spec.passage.x1, spec.front) - r.ea, r.ax);
              r.ps0 = Mathf.Min(p0, p1); r.ps1 = Mathf.Max(p0, p1); }
            else
            {   // 口が無い: 区間の向きの拠り所 = 同じ辺の隣の棟と接しない側の端(妻の線の反対)。両端とも隣と接するなら走りの始め
                r.ps0 = r.ps1 = float.NaN; bool nb0 = false, nb1 = false;
                for (int k = 0; k < Runs.Length; k++) if (k != ri && Runs[k].edge == r.e) { if (Mathf.Abs(Runs[k].s1 - r.sRun0) < 0.05f) nb0 = true; if (Mathf.Abs(Runs[k].s0 - r.sRun1) < 0.05f) nb1 = true; }
                r.anchor = (nb0 && !nb1) ? r.sRun1 : r.sRun0;
            }
            r.batter = EdoBuild.FaceBatterOf(EdoAssets.Own.SannoNozura(4.8f, 0f, 0)); if (float.IsNaN(r.batter)) { r.why = "野面の駒の法が測れない"; return r; }
            // 腰石垣を置く区間 = 段(天端 − 道)≥ cutDrop の所(0.1m 刻み)・門の口は空ける
            float lo = float.MaxValue; float sa = float.NaN;
            for (float sAl = r.sRun0; sAl <= r.sRun1 + 1e-3f; sAl += 0.1f)
            {
                float dr = r.yTop - RoadAtS(r, sAl); bool inGate = sAl > r.ps0 && sAl < r.ps1; bool on = dr >= r.cutDrop && !inGate;
                if (on) { lo = Mathf.Min(lo, RoadAtS(r, sAl)); if (float.IsNaN(sa)) sa = sAl; }
                if ((!on || sAl + 0.1f > r.sRun1 + 1e-3f) && !float.IsNaN(sa)) { float sb2 = on ? sAl : sAl - 0.1f; if (sb2 - sa >= 0.5f) r.spans.Add(new Vector2(sa, sb2)); sa = float.NaN; }
            }
            if (r.spans.Count == 0) { r.why = "段が " + r.cutDrop.ToString("F2", inv) + " を超える所が無い"; return r; }
            r.setback = r.batter * (r.yTop - lo + r.neiri) + 0.02f; r.ok = true;
            // 追記 2026-10-10h【硬】: 腰石垣は門の柱筋まで通す ── 口に接する区間の端を口の縁(ps0/ps1)へ(0.1 刻みの歩きの丸めを戻す)
            { int i10h = tx.IndexOf("追記 2026-10-10h"); r.h10 = i10h >= 0 && tx.Substring(i10h).Contains("門の柱筋まで通し");
              var mD = System.Text.RegularExpressions.Regex.Match(tx, @"落差が\s*([0-9.]+)\s*を超えるなら見切り石"); if (mD.Success) r.mikiriDrop = float.Parse(mD.Groups[1].Value, inv);
              if (r.h10) for (int si = 0; si < r.spans.Count; si++) { var v = r.spans[si]; if (Mathf.Abs(v.x - r.ps1) <= 0.25f) v.x = r.ps1; if (Mathf.Abs(v.y - r.ps0) <= 0.25f) v.y = r.ps0; r.spans[si] = v; } }
            // 追記 2026-10-10j【硬】: 腰石垣を門長屋の前に通し、隣の棟との境の妻の線まで延ばす ── 途中に土の口を作らない(門の口から妻の線までを一つの区間に)。
            //   妻の線 = 門長屋の run の、門の口と反対の端で同じ辺の隣の run と接する s(⛔ 座標を書かない ── run の割りから測る)。終わりの端の落差は【硬】≤ 欄の値(皮の後に測る)。
            { int i10j = tx.IndexOf("追記 2026-10-10j"); string tj = i10j < 0 ? "" : tx.Substring(i10j);
              r.j10 = tj.Contains("妻の線まで延ばす");
              var mE = System.Text.RegularExpressions.Regex.Match(tj, @"端の前の落差は\s*([0-9.]+)\s*以下"); if (mE.Success) r.endDropMax = float.Parse(mE.Groups[1].Value, inv);
              if (r.j10)
              {
                  float gm = r.Mid; float far = Mathf.Abs(r.sRun1 - gm) >= Mathf.Abs(r.sRun0 - gm) ? r.sRun1 : r.sRun0;
                  float gEdge = r.hasGate ? (far > gm ? r.ps1 : r.ps0) : (far > gm ? r.spans[0].x : r.spans[r.spans.Count - 1].y);   // 口が無ければ区間の始まり(段が欄の値を切る所)
                  for (int k = 0; k < Runs.Length; k++) if (k != ri && Runs[k].edge == r.e && (Mathf.Abs(Runs[k].s0 - far) < 0.05f || Mathf.Abs(Runs[k].s1 - far) < 0.05f)) r.gableNb = Runs[k].name;
                  if (r.gableNb == null) { r.j10 = false; r.trimNote = "  ★ roadEdge 追記 2026-10-10j: 門長屋 " + host + " の妻の先に同じ辺の棟が無い ── 妻の線が測れない(延ばさない)\n"; }
                  else { r.gable = far; r.spans.RemoveAll(v => (far > gm) ? v.y > gm : v.x < gm); r.spans.Add(far > gm ? new Vector2(gEdge, far) : new Vector2(far, gEdge)); r.spans.Sort((a2, b2) => a2.x.CompareTo(b2.x)); }
              } }
            // 追記 2026-10-10k【硬】: 妻の線の端は隅の駒で出隅にし、妻の線に沿って背へ折って台の妻の面の石垣(溝の返しの止めの区間を前へ延ばした一続き)── 区間は RoadEdgeSegs が継ぐ
            { int i10k = tx.IndexOf("追記 2026-10-10k"); string tk = i10k < 0 ? "" : tx.Substring(i10k);
              r.k10 = r.j10 && tk.Contains("隅の駒で出隅にし") && tk.Contains("躯体の妻の面を越えない");
              var mB = System.Text.RegularExpressions.Regex.Match(tk, @"1:([0-9.]+)\s*まで立てる"); if (mB.Success) r.tsumaBatterMax = float.Parse(mB.Groups[1].Value, inv);
              // 妻の面の石垣の天端の前の線 = 隣の棟の躯体の妻の面から 法 ×(天端 − 隣の側の地盤)+ 0.02 退けた線(法尻が躯体の妻の面を越えない【硬】)。
              //   隣の側の地盤 = 隣の躯体の底と妻の面の前の道の低い方(⛔ 座標を書かない ── 据えた棟の実メッシュから毎回測る)
              var nbT = r.k10 ? root.transform.Find("Kakoi/" + r.gableNb) : null;
              if (r.k10 && nbT == null) { r.k10 = false; r.trimNote = (r.trimNote ?? "") + "  ★ roadEdge 追記 2026-10-10k: 隣の棟 " + r.gableNb + " が無い ── 妻の面の石垣を建てない\n"; }
              if (r.k10)
              {
                  var spN = EdoBuild.SpecBodySpanAlong(nbT.gameObject, r.ea, r.ax); if (float.IsNaN(spN.x)) spN = EdoBuild.BodySpanAlong(nbT.gameObject, r.ea, r.ax);
                  bool upK = r.gable > r.Mid; float sgn = upK ? 1f : -1f; r.nbFace = upK ? spN.x : spN.y;
                  float lowN = float.MaxValue; r.nbD0 = float.MaxValue; r.nbD1 = float.MinValue;
                  foreach (var v in EdoBuild.Body(nbT, 4000)) { lowN = Mathf.Min(lowN, v.y); float dv = Vector2.Dot(new Vector2(v.x, v.z) - r.ea, r.outN); r.nbD0 = Mathf.Min(r.nbD0, dv); r.nbD1 = Mathf.Max(r.nbD1, dv); }
                  float rdF = RoadAtS(r, r.nbFace + sgn * 0.5f); r.nbLow = float.IsNaN(rdF) ? lowN : Mathf.Min(lowN, rdF);
                  if (float.IsNaN(r.nbFace) || lowN == float.MaxValue) { r.k10 = false; r.trimNote = (r.trimNote ?? "") + "  ★ roadEdge 追記 2026-10-10k: " + r.gableNb + " の躯体の妻の面が測れない ── 妻の面の石垣を建てない\n"; }
                  else r.sCorner = r.nbFace - sgn * (r.batter * (r.yTop - r.nbLow) + 0.02f);
              } }
            r.trimNote = (r.trimNote ?? "") + TrimRoadSpans(r); return r;
        }
        r.why = null; return r;
    }

    /// <summary>腰石垣の区間の端を、駒の底の全幅の下に地盤が在る所まで縮める(roadEdge 追記 2026-10-10g【硬】・第90巡)── 計画(RoadEdgePlanOf)の中で一度だけ。</summary>
    static string TrimRoadSpans(RoadEdgePlan r)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        // ⭐ 追記 2026-10-10g【硬】: run の端は駒の底の全幅の下に地盤がある所で止め、溝の肩から 0.3 以上手前 ── 区間の端から内へ歩き、駒の控えの奥行の全幅で
        //   地盤(今の地形)が駒の底(道 − 根入れ)以上の所まで縮め、そこから肩の余裕だけ更に内へ(第90巡: RoadEdge の端が溝 N39_1 の上へ張り出し隙 12 点)
        {
            string re = ""; foreach (var o3 in A(Get(D, "terraces")) ?? new List<object>()) { var t3 = O(o3); if (S(Get(t3, "name")) == r.terrace) re = S(Get(t3, "roadEdge")) ?? ""; }
            int i10g = re.IndexOf("追記 2026-10-10g");
            var mS = i10g < 0 ? null : System.Text.RegularExpressions.Regex.Match(re.Substring(i10g), @"溝の肩から\s*([0-9.]+)\s*以上手前");
            if (mS != null && mS.Success)
            {
                float shoulder = float.Parse(mS.Groups[1].Value, inv); float depth = float.NaN;
                { var bv = EdoBuild.BodyAt(EdoAssets.Own.SannoNozura(4.8f, 0f, 0), Vector3.zero, 0f, true); float z0 = float.MaxValue, z1 = float.MinValue; foreach (var v in bv) { z0 = Mathf.Min(z0, v.z); z1 = Mathf.Max(z1, v.z); } if (bv.Count > 0) depth = z1 - z0; } r.depth = depth;
                if (float.IsNaN(depth)) sb.AppendLine("  ★ roadEdge 追記 2026-10-10g: 駒の奥行が測れない ── 端を縮めない");
                else
                {
                    System.Func<float, bool> under = sAl => { float bot = RoadAtS(r, sAl) - r.neiri; for (float t = 0f; t <= depth + 1e-3f; t += 0.25f) { var q = r.ea + r.ax * sAl - r.outN * (r.setback + t); if (EdoBuild.Ground(q.x, q.y) < bot) return false; } return true; };
                    for (int si = 0; si < r.spans.Count; si++)
                    {
                        var sp0 = r.spans[si]; float s0 = sp0.x, s1 = sp0.y;
                        float m = 0.5f * (s0 + s1); float c0 = s0, c1 = s1;
                        for (float sAl = m; sAl >= s0 - 1e-3f; sAl -= 0.1f) if (!under(sAl)) { c0 = sAl + 0.1f + shoulder; break; }
                        for (float sAl = m; sAl <= s1 + 1e-3f; sAl += 0.1f) if (!under(sAl)) { c1 = sAl - 0.1f - shoulder; break; }
                        // 追記 2026-10-10j: 妻の線まで延ばす端は 10-10g の縮めを掛けない(後の追記が端を名指す)── 縮めの測りは今の地形の 2m 格子で、溝の肩を 1m 余り手前へ引いて読む(第92巡 s 16.3)。
                        //   端の駒の底の下の地盤は皮の後の隙の検めで測る(硬い隙 0)
                        if (r.j10 && Mathf.Abs(s0 - r.gable) < 0.05f && c0 > s0 + 1e-3f) { sb.AppendLine("  腰石垣の端 s " + s0.ToString("F1", inv) + " は妻の線(" + r.gableNb + " との境・追記 2026-10-10j)── 10-10g の縮め(→ " + c0.ToString("F1", inv) + ")を掛けない"); c0 = s0; }
                        if (r.j10 && Mathf.Abs(s1 - r.gable) < 0.05f && c1 < s1 - 1e-3f) { sb.AppendLine("  腰石垣の端 s " + s1.ToString("F1", inv) + " は妻の線(" + r.gableNb + " との境・追記 2026-10-10j)── 10-10g の縮め(→ " + c1.ToString("F1", inv) + ")を掛けない"); c1 = s1; }
                        if (c0 > s0 + 1e-3f || c1 < s1 - 1e-3f) sb.AppendLine("  腰石垣の端を地盤の在る所まで縮めた(roadEdge 追記 2026-10-10g【硬】): s " + s0.ToString("F1", inv) + "〜" + s1.ToString("F1", inv) + " → " + c0.ToString("F1", inv) + "〜" + c1.ToString("F1", inv) + "(肩の余裕 " + shoulder.ToString("F2", inv) + "・奥行 " + depth.ToString("F2", inv) + ")");
                        r.spans[si] = new Vector2(c0, Mathf.Max(c0, c1));
                    }
                    r.spans.RemoveAll(v => v.y - v.x < 0.5f);
                }
            }
        }
        return sb.ToString();
    }
    /// <summary>腰石垣の区間を野面の区間へ(Stage2b の据えの前に)。区間の道の側の城の石垣(IG_<棟>_*・Stage2 の基壇 ── 見え面が区画の外へ出る)は退ける(SetActive false)。</summary>
    static string RoadEdgeSegs(List<EdoBuild.NozuraSeg> nozSegs)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        _road = RoadEdgePlanOf(); var r = _road;
        if (!r.ok) { if (r.why != null) sb.AppendLine("  ★ 道の側の腰石垣(roadEdge): " + r.why + " ── 建てない(普請方へ)"); return sb.ToString(); }
        int k = 0, retired = 0;
        if (r.trimNote != null) sb.Append(r.trimNote);
        foreach (var sp in r.spans)
        {
            Vector2 a = r.ea + r.ax * sp.x - r.outN * r.setback, b = r.ea + r.ax * sp.y - r.outN * r.setback; var rr = r;
            var seg = new EdoBuild.NozuraSeg { name = r.terrace + "_RoadEdge_" + k++, a = a, b = b, crestAt = sl => rr.yTop, face = r.outN,
                                               footAt = (x, z) => { float sAl = Vector2.Dot(new Vector2(x, z) - rr.ea, rr.ax); return RoadAtS(rr, sAl); } };
            seg.noAbut[0] = seg.noAbut[1] = true;
            // 追記 2026-10-10h【硬】: 口の側の端(門の柱筋に接する端)は見切り石・溝の側の端は端の前の地表との落差が mikiriDrop を超えるなら見切り石(打ち切りはそれ以下だけ)
            // 妻の線の端(10-10j/k)は 10-10h が欄から消えても納める(⛔ h10 の内に入れない ── 第101巡: 欄の書き換えで 10-10h が消え、妻の線の隅の駒が黙って落ちた)
            if (r.h10 || r.j10 || r.k10)
                for (int e2 = 0; e2 < 2; e2++)
                {
                    float sE = e2 == 0 ? sp.x : sp.y; bool atGate = Mathf.Abs(sE - r.ps0) < 0.25f || Mathf.Abs(sE - r.ps1) < 0.25f;
                    if (r.k10 && Mathf.Abs(sE - r.gable) < 0.05f)
                    {   // 追記 2026-10-10k【硬】: 妻の線の端は隅の駒で出隅 ── 区間の端を隅(天端の前の線どうしの交わり)へ。妻の面の石垣は溝の返しの止めの区間を前へ延ばした一続き(TsumaWall)
                        string why = TsumaWall(r, nozSegs, seg, e2, sb);
                        if (why == null) { seg.mikiriTo[e2] = null; seg.noAbut[e2] = false; continue; }
                        sb.AppendLine("    ★ 腰石垣の妻の線の端: 妻の面の石垣を継げない(" + why + ")── 見切り石で止める ⛔(普請方へ)");
                        seg.mikiriTo[e2] = new List<GameObject>(); seg.noAbut[e2] = false; continue;
                    }
                    if (r.j10 && Mathf.Abs(sE - r.gable) < 0.05f)
                    {   // 追記 2026-10-10j【硬】: 妻の線の端 ── 別の石垣の止めと出会えば(端の先 0.4・控えの奥行の中に別の野面の駒の実メッシュ)隅の駒が先・突き付け / 出会わなければ見切り石
                        // ⛔ Dan の駒はこの時まだ据わっていない(Stage2b は区間を全部集めてから据える)── 他の区間の計画(線 a→b と見え面の向き・控えの奥行)の帯で測る
                        float sgn = e2 == 0 ? -1f : 1f; string meet = null; float near = float.MaxValue; float dep = float.IsNaN(r.depth) ? 0f : r.depth;
                        var mine = new List<Vector2>(); for (float ds = 0f; ds <= 0.4f + 1e-3f; ds += 0.1f) for (float dd = 0f; dd <= r.setback + dep + 1e-3f; dd += 0.25f) mine.Add(r.ea + r.ax * (sE + sgn * ds) - r.outN * dd);
                        foreach (var os in nozSegs)
                        {
                            if (os.name.Contains("_RoadEdge_")) continue; Vector2 fo = os.face.sqrMagnitude > 1e-6f ? os.face.normalized : Vector2.zero;
                            for (float u = 0f; u <= 1f + 1e-3f; u += Mathf.Min(1f, 0.25f / Mathf.Max(0.25f, os.Len)))
                                for (float bb = 0f; bb <= dep + 1e-3f; bb += 0.25f)
                                {
                                    var q = Vector2.Lerp(os.a, os.b, u) - fo * bb; foreach (var mq in mine) { float dist = Vector2.Distance(q, mq); if (dist < near) { near = dist; if (dist < 0.3f) meet = os.name; } }
                                }
                        }
                        if (meet != null) sb.AppendLine("    ★ 腰石垣の妻の線の端が " + meet + " と出会う(追記 2026-10-10j: 隅の駒が先・突き付け)── 隅の駒の据えは未実装 ── 見切り石で止める ⛔(普請方へ)");
                        else sb.AppendLine("    腰石垣の妻の線の端(s " + sE.ToString("F2", inv) + "・" + r.gableNb + " との境)は別の石垣の止めと出会わない(最も近い野面の駒まで " + (near == float.MaxValue ? "-" : near.ToString("F2", inv)) + "m)── 見切り石で止める(追記 2026-10-10j)");
                        seg.mikiriTo[e2] = new List<GameObject>(); seg.noAbut[e2] = false; continue;
                    }
                    float sOut = e2 == 0 ? sE - 0.5f : sE + 0.5f; var qo = r.ea + r.ax * sOut - r.outN * r.setback; float dropE = r.yTop - EdoBuild.Ground(qo.x, qo.y);
                    if (atGate || (!float.IsNaN(r.mikiriDrop) && dropE > r.mikiriDrop)) { seg.mikiriTo[e2] = new List<GameObject>(); seg.noAbut[e2] = false; sb.AppendLine("    腰石垣の端" + e2 + "(s " + sE.ToString("F1", inv) + ")を見切り石で止める(" + (atGate ? "門の柱筋" : "端の前の落差 " + dropE.ToString("F2", inv)) + "・roadEdge 追記 2026-10-10h)"); }
                }
            nozSegs.Add(seg);
        }
        var ig = Group("Ishigaki"); string run = r.host.name;
        foreach (Transform c in ig)
        {
            if (!c.gameObject.activeSelf || !c.name.StartsWith("IG_" + run + "_")) continue; var cb = EdoBuild.RB(c.gameObject); float sc = Vector2.Dot(new Vector2(cb.center.x, cb.center.z) - r.ea, r.ax);
            bool hit = sc > r.ps0 - 1f && sc < r.ps1 + 1f;   // 門の口(踏み段の下)も
            foreach (var sp in r.spans) if (sc > sp.x - 1f && sc < sp.y + 1f) hit = true;
            if (hit) { c.gameObject.SetActive(false); retired++; }
        }
        var sl0 = new List<string>(); foreach (var sp in r.spans) sl0.Add(sp.x.ToString("F1", inv) + "〜" + sp.y.ToString("F1", inv));
        sb.AppendLine("  道の側の腰石垣(roadEdge・" + run + " の足元): 野面 " + r.spans.Count + " 区間(s " + string.Join("・", sl0.ToArray()) + (r.hasGate ? "・門の口 " + r.ps0.ToString("F1", inv) + "〜" + r.ps1.ToString("F1", inv) + " を空ける)" : "・門の口なし)") + "・天端 " + r.yTop.ToString("F2", inv)
                      + " 一直線・天端の前の線を区画の線から " + r.setback.ToString("F2", inv) + " 退けた(法 " + r.batter.ToString("F2", inv) + " ×(天端 − 道の最低 + 根入れ " + r.neiri.ToString("F2", inv) + "))・段 < " + r.cutDrop.ToString("F2", inv) + " で打ち切り【硬】・道の側の城の石垣 " + retired + " 駒を退けた");
        return sb.ToString();
    }

    /// <summary>**台の妻の面の石垣**(指図 terraces[].roadEdge 追記 2026-10-10k・EDO-0502 第94巡)── 道の側の腰石垣の妻の線の端を隅の駒で出隅にし、妻の線に沿って背へ折る。
    /// 折った石垣 = 妻の線に沿う別の区間(溝の返しの止め ── 両端が妻の線の上)を前へ延ばした一続き: その区間の背の端を天端の前の線 sCorner へ(継ぐ相手の端も同じ点へ)、
    /// 前の端を隅(腰石垣の天端の前の線との交わり)へ。見え面 = 隣の棟の側、足元の地盤 = 溝の中は溝の底・隣の躯体の帯は躯体の底・外は道(⛔ 座標を書かない)。
    /// 隅の駒・突き付けは PlaceNozuraNet(① 出隅の駒が先)。当たる先: roadEdge 10-10k を持つ面(岡部 Kadonouchi × N39_1)。返り値 null = 継いだ / 理由。</summary>
    static string TsumaWall(RoadEdgePlan r, List<EdoBuild.NozuraSeg> nozSegs, EdoBuild.NozuraSeg seg, int e2, System.Text.StringBuilder sb)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; if (float.IsNaN(r.sCorner)) return "天端の前の線が解けていない";
        bool up = r.gable > r.Mid; float sgn = up ? 1f : -1f;
        Func<Vector2, float> sOf = q => Vector2.Dot(q - r.ea, r.ax);
        EdoBuild.NozuraSeg ts = null; float best = float.MinValue;
        foreach (var os in nozSegs)
        {
            if (os == seg || os.name.Contains("_RoadEdge_")) continue;
            if (Mathf.Abs(sOf(os.a) - r.gable) > 0.3f || Mathf.Abs(sOf(os.b) - r.gable) > 0.3f || os.Len < 0.3f) continue;   // 妻の線に沿う区間
            float dF = Mathf.Max(Vector2.Dot(os.a - r.ea, r.outN), Vector2.Dot(os.b - r.ea, r.outN)); if (dF > best) { best = dF; ts = os; }
        }
        if (ts == null) return "妻の線に沿う石垣の区間が無い";
        Vector2 C = r.ea + r.ax * r.sCorner - r.outN * r.setback;
        bool aFront = Vector2.Dot(ts.a - r.ea, r.outN) > Vector2.Dot(ts.b - r.ea, r.outN);
        Vector2 back = aFront ? ts.b : ts.a, back2 = back + r.ax * (r.sCorner - sOf(back));
        int moved = 0; string mate = null;
        foreach (var os in nozSegs)
        {
            if (os == ts || os == seg) continue;
            if (Vector2.Distance(os.a, back) < 0.05f) { if (Mathf.Abs(Vector2.Dot(os.Dir, r.ax)) < 0.9f) return os.name + " が棟の背に沿わない ── 端を延ばせない"; os.a = back2; moved++; mate = os.name; }
            else if (Vector2.Distance(os.b, back) < 0.05f) { if (Mathf.Abs(Vector2.Dot(os.Dir, r.ax)) < 0.9f) return os.name + " が棟の背に沿わない ── 端を延ばせない"; os.b = back2; moved++; mate = os.name; }
        }
        float oldLen = ts.Len;
        if (aFront) { ts.a = C; ts.b = back2; } else { ts.a = back2; ts.b = C; }
        if (e2 == 0) seg.a = C; else seg.b = C;
        ts.face = r.ax * sgn;   // 見え面 = 隣の棟の側
        var trs = BackTrenches(null);
        var rr = r;
        ts.footAt = (x, z) =>
        {
            var q = new Vector2(x, z); float tY = TrenchAt(trs, q); if (!float.IsNaN(tY)) return tY;
            return RoadAtS(rr, sOf(q));   // 指図「法尻は隣の側の地盤(前は道の地表・背は溝の底)」── 溝の外は道の地表(⛔ 第94巡の一回目: 隣の躯体の帯を躯体の底 14.0 と読み、
            //   腕の見付 2.5 を受ける段が H4.8 しか無く鎖の全ての駒が H4.8 ── 隅の腕の根入れが区画の線の外へ 0.75 出た)
        };
        seg.footAt = ts.footAt;   // 鎖の足元は一つの測り(腰石垣の側は従前の道の地表と同じ)
        r.tsumaSeg = ts.name;
        sb.AppendLine("    腰石垣の妻の線の端を隅の駒で出隅に(roadEdge 追記 2026-10-10k【硬】): 隅 (" + C.x.ToString("F2", inv) + ", " + C.y.ToString("F2", inv) + ")・s " + r.sCorner.ToString("F2", inv)
                      + "(" + r.gableNb + " の躯体の妻の面 s " + r.nbFace.ToString("F2", inv) + " から 法 " + r.batter.ToString("F2", inv) + " ×(天端 " + r.yTop.ToString("F2", inv) + " − 隣の側の地盤 " + r.nbLow.ToString("F2", inv) + ")+ 0.02 退けた)・"
                      + ts.name + " を前へ延ばした一続き " + oldLen.ToString("F2", inv) + " → " + ts.Len.ToString("F2", inv) + "m(背の端を天端の前の線へ・" + (mate ?? "継ぐ相手なし") + " の端も " + moved + ")・見え面 = " + r.gableNb + " の側・法 1:"
                      + r.batter.ToString("0.00", inv) + "(狙い 1:0.3【柔】" + (r.batter > 0.3f + 0.005f ? " ⚠ 狙い未達" : " ⭕") + ")");
        return null;
    }

    /// <summary>腰石垣の妻の線の端の前の落差(指図 roadEdge 追記 2026-10-10j「出会わなければ見切り石で止め、端の前の落差は x 以下【硬】」)── 皮の後に、
    /// 端の駒(見切り石)の実メッシュの最も先の s から 0.15・0.5 先、控えの奥行の帯(線の内 0.1〜setback+奥行)の描かれた地表と天端の差の最大。当たる先: 欄 roadEdge を持つ面(岡部 Kadonouchi)。</summary>
    static string RoadEdgeEndReport(Transform root)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var r = _road ?? RoadEdgePlanOf(); if (r == null || !r.ok || !r.j10) return "腰石垣の妻の線の端: 欄 10-10j に該当なし";
        if (r.k10 && !float.IsNaN(r.sCorner))
        {   // 追記 2026-10-10k【硬】: 妻の面の石垣の法尻が隣の棟の躯体の妻の面を越えない ── 段の駒の頂点のうち、隣の躯体の底より上・躯体の奥行の帯の中で、妻の面を越える量の最大
            float sg = r.gable > r.Mid ? 1f : -1f; float over = float.MinValue; string who = "-"; int nP = 0;
            foreach (Transform dc in root.Find("Dan"))
            {
                if (!dc.gameObject.activeInHierarchy) continue; var rb = EdoBuild.RB(dc.gameObject); float sc = Vector2.Dot(new Vector2(rb.center.x, rb.center.z) - r.ea, r.ax);
                if (Mathf.Abs(sc - r.nbFace) > 6f) continue; bool any = false;
                foreach (var v in EdoBuild.Body(dc, 4000))
                {
                    if (v.y < r.nbLow + 0.02f) continue; float dv = Vector2.Dot(new Vector2(v.x, v.z) - r.ea, r.outN); if (dv < r.nbD0 || dv > r.nbD1) continue;
                    float o = sg * (Vector2.Dot(new Vector2(v.x, v.z) - r.ea, r.ax) - r.nbFace); any = true; if (o > over) { over = o; who = dc.name; }
                }
                if (any) nP++;
            }
            return "妻の面の石垣(roadEdge 追記 2026-10-10k・" + r.gableNb + " の躯体の妻の面 s " + r.nbFace.ToString("F2", inv) + "・天端の前の線 s " + r.sCorner.ToString("F2", inv) + "): 駒 " + nP + " の法尻が妻の面を越える最大 "
                   + (over == float.MinValue ? "-" : over.ToString("F3", inv)) + "〔" + who + "〕・硬 ≤ 0" + (over > 1e-3f ? " ⛔" : " ⭕");
        }
        var dg = EdoBuild.Drawn(); float sEnd = float.NaN; string nm = null; bool up = r.gable > r.Mid;
        foreach (Transform dc in root.Find("Dan"))
        {
            if (!dc.gameObject.activeInHierarchy || !dc.name.Contains("_RoadEdge_")) continue;
            foreach (var v in EdoBuild.Body(dc, 4000)) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - r.ea, r.ax); if (float.IsNaN(sEnd) || (up ? sv > sEnd : sv < sEnd)) { sEnd = sv; nm = dc.name; } }
        }
        if (float.IsNaN(sEnd)) return "腰石垣の妻の線の端: 駒が無い ⛔";
        // 帯 = 端の駒の実メッシュの d の幅(⛔ 型の奥行 r.depth は控えの裾まで入り、駒の背より奥の溝を拾う)
        float dIn0 = float.MaxValue, dIn1 = float.MinValue; foreach (Transform dc in root.Find("Dan")) if (dc.name == nm) foreach (var v in EdoBuild.Body(dc, 4000)) { float dv = -Vector2.Dot(new Vector2(v.x, v.z) - r.ea, r.outN); dIn0 = Mathf.Min(dIn0, dv); dIn1 = Mathf.Max(dIn1, dv); }
        float worst = float.MinValue; Vector3 at = Vector3.zero;
        foreach (float ds in new[] { 0.15f, 0.5f })
            for (float dd = Mathf.Max(0.05f, dIn0); dd <= dIn1 + 1e-3f; dd += 0.2f)
            { var q = r.ea + r.ax * (sEnd + (up ? ds : -ds)) - r.outN * dd; float y = dg.At(q.x, q.y), drop = r.yTop - y; if (drop > worst) { worst = drop; at = new Vector3(q.x, y, q.y); } }
        bool bad = !float.IsNaN(r.endDropMax) && worst > r.endDropMax + 1e-3f;
        return "腰石垣の妻の線の端(" + r.gableNb + " との境・端の駒 " + nm + "・s " + sEnd.ToString("F2", inv) + "): 端の前の落差の最大 " + worst.ToString("F2", inv) + " @(" + at.x.ToString("F1", inv) + ", " + at.y.ToString("F2", inv) + ", " + at.z.ToString("F1", inv) + ")・硬 ≤ " + (float.IsNaN(r.endDropMax) ? "?" : r.endDropMax.ToString("F2", inv)) + (bad ? " ⛔" : " ⭕");
    }

    /// <summary>門の口の踏み段(roadEdge【硬】一段目の段鼻は区画の線を越えない・蹴上 = 落差 ÷ 段数・段数 = 落差 ÷ 屋敷の中の石段の既定の蹴上 0.30 の切り上げ・踏面は欄を狙う【柔】)。
    /// 段石は石段の型(SannoDanNearestKeri・PlaceDanStone・StackDownToGround)。</summary>
    static string PlaceGateSteps(List<string> wait)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var r = _road; var grp = Group("GateSteps"); Clear(grp);
        if (r == null || !r.ok) return "";
        if (!r.hasGate) return "  門の口の踏み段(roadEdge): 腰石垣の棟 " + r.host.name + " に門の口が無い ── 置かない\n";
        // 追記 2026-10-10h【硬】(abutOrder: 腰石垣が先): 踏み段の端は腰石垣の口の側の見切り石の面に突き付ける ── 見切り石の実メッシュが口の幅に掛かる分だけ段の幅を縮める
        float gs0 = r.ps0, gs1 = r.ps1;
        if (r.h10)
            foreach (Transform dc in Group("Dan"))
            {
                if (!dc.gameObject.activeInHierarchy || !dc.name.Contains("_RoadEdge_") || !dc.name.Contains("_mikiri")) continue;
                float m0 = float.MaxValue, m1 = float.MinValue; foreach (var v in EdoBuild.Body(dc, 4000)) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - r.ea, r.ax); m0 = Mathf.Min(m0, sv); m1 = Mathf.Max(m1, sv); }
                if (m1 <= gs0 || m0 >= gs1) continue;
                if (m0 - gs0 > gs1 - m1) gs1 = Mathf.Min(gs1, m0); else gs0 = Mathf.Max(gs0, m1);
                sb.AppendLine("  門の口の踏み段の端を見切り石 " + dc.name + " の面へ突き付けた(roadEdge 追記 2026-10-10h・abutOrder): 段の幅 s " + gs0.ToString("F2", inv) + "〜" + gs1.ToString("F2", inv));
            }
        float pm = 0.5f * (gs0 + gs1), road = RoadAtS(r, pm), drop = r.yTop - road; if (drop < 0.05f) { sb.AppendLine("  門の口の踏み段: 落差 " + drop.ToString("F2", inv) + " ── 置かない"); return sb.ToString(); }
        int n = Mathf.Max(1, Mathf.CeilToInt(drop / 0.30f - 1e-3f)); float keri = drop / n; Vector2 up = -r.outN;
        float wid = gs1 - gs0; int across = Mathf.Max(1, Mathf.RoundToInt(wid / 1.818f));
        int made = 0, stacked = 0; float noseOut = float.MinValue; var stackCache = new Dictionary<long, float>();
        // 指図 roadEdge 追記 2026-10-10n ③(第96巡): 段石の天端は前の道より a 以上高く【硬】・満たさない所で段石を打ち切り、その先は一つ上の段を区画の線まで出す(蹴上 ≤ k)【硬】・
        //   道との差が b 未満なら段を置かない【柔】── 列(口の幅の割り)ごとに、その列の前の道(列の両端と中ほどの最高)で測る。当たる先: 道が口の幅で上り下りする門の口の踏み段すべて
        float nAbove = float.NaN, nKeri = float.NaN, nSkip = float.NaN;
        { string rt = null; foreach (var o in A(Get(D, "terraces")) ?? new List<object>()) { var t = O(o); if (S(Get(t, "name")) == r.terrace) rt = S(Get(t, "roadEdge")); }
          int i10n = rt == null ? -1 : rt.IndexOf("追記 2026-10-10n"); string tn = i10n < 0 ? "" : rt.Substring(i10n);
          var mA = System.Text.RegularExpressions.Regex.Match(tn, @"段石の天端は前の道より\s*([0-9.]+)\s*以上高く"); var mKr = System.Text.RegularExpressions.Regex.Match(tn, @"区画の線まで出す[(（]蹴上\s*([0-9.]+)\s*以下"); var mB = System.Text.RegularExpressions.Regex.Match(tn, @"道との差が\s*([0-9.]+)\s*未満なら段を置かない");
          if (mA.Success) nAbove = float.Parse(mA.Groups[1].Value, inv); if (mKr.Success) nKeri = float.Parse(mKr.Groups[1].Value, inv); if (mB.Success) nSkip = float.Parse(mB.Groups[1].Value, inv); }
        int nCut = 0, nExt = 0, nColSkip = 0; float worstKeri = 0f, worstAbove = float.MaxValue;
        for (int j = 0; j < across; j++)
        {
            float tt = (j - (across - 1) * 0.5f) * (wid / across), hw = 0.5f * wid / across;
            float roadJ = float.MinValue, roadLo = float.MaxValue; foreach (float dq in new[] { -hw, 0f, hw }) { float rq = RoadAtS(r, pm + tt + dq); if (!float.IsNaN(rq)) { roadJ = Mathf.Max(roadJ, rq); roadLo = Mathf.Min(roadLo, rq); } }
            if (roadJ == float.MinValue) { roadJ = road; roadLo = road; }
            if (!float.IsNaN(nSkip) && r.yTop - roadJ < nSkip) { nColSkip++; sb.AppendLine("    門の口の踏み段 列" + j + ": 道 " + roadJ.ToString("F2", inv) + " と台 " + r.yTop.ToString("F2", inv) + " の差 " + (r.yTop - roadJ).ToString("F2", inv) + " < " + nSkip.ToString("F2", inv) + " ── 段を置かない(roadEdge 10-10n ③ 柔)"); continue; }
            int first = 1;   // 打ち切り: 天端 < 列の道 + a の段は置かない(上がり口の段石 i = n は台の面なので打ち切らない)
            if (!float.IsNaN(nAbove)) while (first < n && road + keri * first < roadJ + nAbove - 1e-4f) first++;
            nCut += first - 1;
            { float t1 = road + keri * first; if (first > 1) worstKeri = Mathf.Max(worstKeri, t1 - roadLo); worstAbove = Mathf.Min(worstAbove, t1 - roadJ); }   // 蹴上 ≤ k は区画の線まで出した段だけ(欄「その先は一つ上の段を区画の線まで出す(蹴上 k 以下)」)
            for (int i = first; i <= n; i++)
            {
                float top = road + keri * i;
                string pth = EdoAssets.Own.SannoDanNearestKeri(keri, r.fumi, 1.818f, made); if (pth == null) { wait.Add("門の口の踏み段: 段石が焼けていない(蹴上 " + keri.ToString("F3") + ")"); return sb.ToString(); }
                // 打ち切った段の踏面へ、一つ上の段(= 最初に置く段)を区画の線まで出す ── 同じ天端の段石を前へ並べる
                for (int k2 = (i == first ? 1 : i); k2 <= i; k2++)
                {
                    Vector2 nose = r.ea + r.ax * (pm + tt) + up * (0.01f + r.fumi * (k2 - 1));
                    var go = EdoBuild.PlaceDanStone(pth, grp, "GateStep_" + i + "_" + j + (k2 < i ? "_x" + k2 : ""), nose, up, top, wid / across, r.fumi); if (go == null) continue; made++; if (k2 < i) nExt++;
                    stacked += EdoBuild.StackDownToGround(go, pth, grp, go.name, 12, wait, (x, z) => { bool rp; float yRd = EdoBuild.OutsideOwnGround(EdoBuild.T(), x, z, Poly, EdoBuild.BaseDem(), null, stackCache, out rp); float yS = SkinGround(x, z); return float.IsNaN(yRd) ? yS : float.IsNaN(yS) ? yRd : Mathf.Min(yRd, yS); });
                    // ⭐ 段石の下は道の地表(区画の外の皮と同じ測り)まで積む(第93巡: 道が口の幅で 0.7 下り、低い端の段石の端が道の土から 0.17 浮いた ── 設計の地盤 SkinGround は台の 16.50 を読む)
                }
            }
        }
        if (!float.IsNaN(nAbove))
            sb.AppendLine("  門の口の踏み段(roadEdge 追記 2026-10-10n ③): 打ち切った段 " + nCut + "・区画の線まで出した段石 " + nExt + "・段を置かない列 " + nColSkip
                          + "・一段目の天端 − 前の道 最小 " + (worstAbove == float.MaxValue ? "-" : worstAbove.ToString("+0.000;-0.000", inv)) + (worstAbove >= nAbove - 1e-3f || worstAbove == float.MaxValue ? " ⭕" : " ⛔") + "(≥ " + nAbove.ToString("F2", inv) + "【硬】)"
                          + "・区画の線まで出した段の蹴上 最大 " + (nExt == 0 ? "-(出した段なし)" : worstKeri.ToString("F3", inv)) + (float.IsNaN(nKeri) ? "" : worstKeri <= nKeri + 1e-3f ? " ⭕(≤ " + nKeri.ToString("F2", inv) + "【硬】)" : " ⛔(≤ " + nKeri.ToString("F2", inv) + "【硬】)"));
        foreach (Transform c in grp) foreach (var v in EdoBuild.Body(c, 4000)) noseOut = Mathf.Max(noseOut, Vector2.Dot(new Vector2(v.x, v.z) - r.ea, r.outN));
        sb.AppendLine("  門の口の踏み段(roadEdge): 落差 " + drop.ToString("F2", inv) + "(道 " + road.ToString("F2", inv) + " → " + r.yTop.ToString("F2", inv) + ")÷ " + n + " 段 = 蹴上 " + keri.ToString("F3", inv) + "・踏面 " + r.fumi.ToString("F2", inv) + "(柔)・段石 " + made + "・下の積み " + stacked
                      + "・段石の最も外 − 区画の線 = " + (noseOut == float.MinValue ? "-" : noseOut.ToString("+0.000;-0.000", inv)) + "m" + (noseOut > 0.001f ? " ⛔(線を越える)" : " ⭕") + "【硬】");
        return sb.ToString();
    }

    /// <summary>表門脇の下水の線(指図 terraces[].omoteGesui・普請方 2026-10-10b・EDO-0502 第81巡)。門は指図 gate.host の門長屋の**札**(EdoPartSpec の passage・back・front)で測る。
    /// 線 = 門の口の脇(口の縁 + 溝の半幅 + 0.02 ── 口を跨がない側)の局所 x で、門の内の背の雨落ちの線(背 − 半幅 − 0.02)の点 J から、門長屋の背 → 表 → 区画の線の手前 0.01 まで。
    /// 口のどちら脇か = J の地盤の低い側(差 0.02 以内なら背の雨落ちが長い側 ── 雨落ちに口を跨がせない)。⛔ 座標を書かない ── 毎回測る。</summary>
    class GesuiPlan { public bool ok; public string why, terrace; public Transform host; public EdoPartSpec.Spec spec; public float xs, halfW, yF, dMax, slope, back, front; public Vector2 J, E, outDir; public float jBottom = float.NaN;
        public bool higuchi; public Vector2 mouth; public float kuchiDepth, kuchiFloor;
        public bool sump; public float sumpS = float.NaN, sillAbove; public int edge = -1; }
    static GesuiPlan _gesui;
    static GesuiPlan OmoteGesuiPlan()
    {
        var g = new GesuiPlan(); var inv = System.Globalization.CultureInfo.InvariantCulture; var root = GameObject.Find(GN); if (root == null) { g.why = "邸が無い"; return g; }
        foreach (var o in A(Get(D, "terraces")) ?? new List<object>())
        {
            var t = O(o); string og = S(Get(t, "omoteGesui")); if (og == null) continue; g.terrace = S(Get(t, "name")); g.yF = F(Get(t, "y"));
            string fl = S(Get(t, "flat")) ?? ""; var mS = System.Text.RegularExpressions.Regex.Match(fl, @"長手に\s*1\s*/\s*([0-9]+)"); var mU = System.Text.RegularExpressions.Regex.Match(og, @"上限\s*([0-9.]+)\s*を狙う");
            if (!mU.Success) mU = System.Text.RegularExpressions.Regex.Match(og, @"上限\s*([0-9.]+)");   // 第102巡の書式「深さ 0.05→約 0.30【柔・上限 0.35】」
            if (!mS.Success || !mU.Success) { g.why = "勾配(flat の長手 1/n)か深さの上限が読めない"; return g; }
            g.slope = 1f / float.Parse(mS.Groups[1].Value, inv); g.dMax = float.Parse(mU.Groups[1].Value, inv);
            // 下水の棟 = 同じ面の roadEdge が名指す腰石垣の棟(⛔ gate.host で取らない ── 表門が別の辺へ移ると下水が門長屋ごと動く・第101巡)
            string host = RoadEdgeHost(S(Get(t, "roadEdge")) ?? ""); var hT = host == null ? null : root.transform.Find("Kakoi/" + host);
            if (hT == null) { g.why = "棟 " + (host ?? "-") + " が無い"; return g; }
            // ⭐ 集水枡の型(普請方 2026-10-10p・第102巡): 「<棟> の背の s=<n> の集水枡」── 門の口の脇でなく、名指しの棟の背の s で背の雨落ちを受け、
            //   枡から台の下を区画の線へ直角に抜く暗渠 → 腰石垣の見え面の同じ s の樋口。門の有無に依らない(当たる先: 口の無い棟で下水を受ける面)。
            var mSump = System.Text.RegularExpressions.Regex.Match(og, host + @"\s*の背の\s*s\s*=\s*([0-9.]+)\s*の集水枡");
            if (mSump.Success) return SumpGesuiPlan(g, og, hT, float.Parse(mSump.Groups[1].Value, inv));
            var spec = EdoPartSpec.Get(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(hT.gameObject));
            if (spec == null || spec.passage == null || spec.passage.x1 - spec.passage.x0 < 0.1f || spec.jambL == null || spec.jambR == null)
            { g.why = "棟 " + host + " に門の口が無い ── 入口 J(門の口の脇)が測れない。置き場を『今のまま』に取るなら棟の上の位置(s)が指図に要る"; return g; }
            string p0 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.15f); var mp = p0 == null ? null : EdoBuild.MizoPieceOf(p0);
            if (mp == null || !mp.ok) { g.why = "石組の溝の駒(DoiMizo 型 A)が測れない"; return g; }
            g.halfW = Mathf.Max(Mathf.Abs(mp.xMin), Mathf.Abs(mp.xMax)); g.host = hT; g.spec = spec; g.back = spec.back; g.front = spec.front;
            float off = g.halfW + 0.02f, zJ = spec.back - off;
            float xL = spec.passage.x0 - off, xR = spec.passage.x1 + off;
            Vector2 jL = EdoPartSpec.W(hT, xL, zJ), jR = EdoPartSpec.W(hT, xR, zJ);
            float gL = EdoBuild.Ground(jL.x, jL.y), gR = EdoBuild.Ground(jR.x, jR.y);
            bool right = Mathf.Abs(gL - gR) > 0.02f ? gR < gL : (spec.jambR.x - spec.passage.x1) >= (spec.passage.x0 - spec.jambL.x);
            g.xs = right ? xR : xL; g.J = right ? jR : jL;
            Vector2 fP = EdoPartSpec.W(hT, g.xs, spec.front), fO = EdoPartSpec.W(hT, g.xs, spec.front + 1f); g.outDir = (fO - fP).normalized;
            if (!EdoGeom.PIP(Poly, fP)) { g.why = "門長屋の表の面が区画の外"; return g; }
            Vector2 e = fP; bool hit = false; for (float d = 0f; d <= 3f; d += 0.01f) { var q = fP + g.outDir * d; if (!EdoGeom.PIP(Poly, q)) { hit = true; break; } e = q; }
            if (!hit) { g.why = "表の面から 3m 内に区画の線が無い"; return g; }
            g.E = e;
            // 追記 2026-10-10c【硬】: 出口は腰石垣(roadEdge)の見え面に石の樋口を開け、道の面より上で吐き出す・区画の外に何も置かない
            //   ⇒ 溝は樋口(DoiAnkyoKuchi・口 = 局所 z 0・嘴 +0.15・奥 zMin)の奥で止め、樋口の口を見え面(天端の前の線 + 法 ×(天端 − 底の見込み))へ
            if (og.Contains("追記 2026-10-10c") && og.Contains("樋口"))
            {
                if (_road == null) _road = RoadEdgePlanOf(); var rp = _road;
                var kp = EdoAssets.Own.DoiAnkyoKuchi; var km = kp == null ? null : EdoBuild.MizoPieceOf(kp);
                if (rp == null || !rp.ok || km == null || !km.ok) { g.why = "樋口: 腰石垣か樋口の駒が無い(" + (rp == null ? "-" : rp.why) + ")"; g.ok = false; return g; }
                float sF = Vector2.Dot(fP - rp.ea, rp.ax); Vector2 crest = rp.ea + rp.ax * sF - rp.outN * rp.setback;
                float yGuess = g.yF - 0.25f;   // 底の見込み(溝の底は Lay で解く ── 樋口の口は解いた底で据え直す)
                g.mouth = crest + rp.outN * (rp.batter * (rp.yTop - yGuess)); g.kuchiDepth = -km.zMin; g.kuchiFloor = km.floor;
                g.E = g.mouth - rp.outN * g.kuchiDepth; g.higuchi = true;
            }
            g.ok = true; return g;
        }
        g.why = null; return g;   // 欄が無い
    }

    /// <summary>**集水枡の下水の線**(指図 terraces[].omoteGesui「&lt;棟&gt; の背の s=n の集水枡」・普請方 2026-10-10p・EDO-0502 第102巡)。
    /// 枡の芯 J = 棟の背の面(実メッシュ・FaceOut)+ 溝の半幅 + 0.02 の線の上の s。暗渠 J → 区画の線へ直角(辺の外向き)→ 腰石垣(roadEdge)の見え面の同じ s の樋口。
    /// ⛔ 座標を書かない ── s は指図・面は毎回測る。</summary>
    static GesuiPlan SumpGesuiPlan(GesuiPlan g, string og, Transform hT, float sSump)
    {
        int ri = -1; for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == hT.name) ri = k;
        if (ri < 0) { g.why = "棟 " + hT.name + " が runs に無い"; return g; }
        string p0 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.15f); var mp = p0 == null ? null : EdoBuild.MizoPieceOf(p0);
        if (mp == null || !mp.ok) { g.why = "石組の溝の駒(DoiMizo 型 A)が測れない"; return g; }
        int e = Runs[ri].edge; Vector2 ea = EdgePt(e, 0f), ax = (EdgePt(e, 1f) - ea).normalized, yard = -OutNormal(e);
        float seatY = hT.position.y; float back = EdoBuild.FaceOut(hT.gameObject, ea, yard, seatY + 0.1f, seatY + 1.2f);
        if (float.IsNaN(back)) { g.why = "棟 " + hT.name + " の背の面が測れない"; return g; }
        g.halfW = Mathf.Max(Mathf.Abs(mp.xMin), Mathf.Abs(mp.xMax)); g.host = hT; g.sump = true; g.sumpS = sSump; g.edge = e;
        g.J = ea + ax * sSump + yard * (back + g.halfW + 0.02f); g.outDir = OutNormal(e);
        if (!EdoGeom.PIP(Poly, g.J)) { g.why = "枡の芯が区画の外"; return g; }
        if (_road == null) _road = RoadEdgePlanOf(); var rp = _road;
        var kp = EdoAssets.Own.DoiAnkyoKuchi; var km = kp == null ? null : EdoBuild.MizoPieceOf(kp);
        if (rp == null || !rp.ok || km == null || !km.ok) { g.why = "樋口: 腰石垣か樋口の駒が無い(" + (rp == null ? "-" : rp.why) + ")"; return g; }
        float sF = Vector2.Dot(EdgePt(e, sSump) - rp.ea, rp.ax);
        if (sF < rp.sRun0 - 0.01f || sF > rp.sRun1 + 0.01f) { g.why = "樋口の s=" + sSump.ToString("F1") + " が腰石垣の区間 " + rp.sRun0.ToString("F1") + "〜" + rp.sRun1.ToString("F1") + " の外"; return g; }
        Vector2 crest = rp.ea + rp.ax * sF - rp.outN * rp.setback;
        g.mouth = crest + rp.outN * (rp.batter * (rp.yTop - (g.yF - 0.35f))); g.kuchiDepth = -km.zMin; g.kuchiFloor = km.floor;
        g.E = g.mouth - rp.outN * g.kuchiDepth; g.higuchi = true; g.back = float.NaN; g.front = float.NaN;
        var mR = System.Text.RegularExpressions.Regex.Match(og, @"敷きは道の線上の地盤[^+＋]*[+＋]\s*([0-9.]+)\s*以上");
        g.sillAbove = mR.Success ? float.Parse(mR.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : 0f;
        g.ok = true; return g;
    }

    /// <summary>**表門脇の下水を据える**(指図 omoteGesui【硬】出口は入口より低く区画の外へ落とす・塀をくぐる所だけ暗渠)。線は <see cref="OmoteGesuiPlan"/>、
    /// 底は <see cref="EdoBuild.SolveMizoBottom"/>(頭 = 背の雨落ちの尻 − 0.01 ── 受ける側の底 &lt; 入る側の底【硬】)、駒は実測の深さで選ぶ DoiMizo 型 A。
    /// 門長屋の背から表までの駒には蓋石(DoiFutaishiFor 型 A)を二枚ずつ ── 蓋の下端 = 駒の天端の実測。道(線の外 1m の地形)が出口の底より低くなければ据えない(内側を沿わせる線は未)。</summary>
    static string PlaceOmoteGesui()
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        var grp = Group("OmoteGesui"); Clear(grp);
        _gesui = OmoteGesuiPlan(); var g = _gesui;
        if (!g.ok) { if (g.why != null) sb.AppendLine("  ★ 表門脇の下水(omoteGesui): " + g.why + " ── 置かない(普請方へ)"); return sb.ToString(); }
        return sb.ToString();   // 据えは背の雨落ちの尻が解けてから(PlaceOmoteGesuiLay)
    }

    static string PlaceOmoteGesuiLay(float headBottom)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var g = _gesui;
        if (g == null || !g.ok) return "";
        var grp = Group("OmoteGesui"); Clear(grp);
        var line = new List<Vector2> { g.J, g.E };
        // 集水枡の型(第102巡): 枡(DoiMasu G1・ピボット = 芯・地盤・+Z = 吐き口)を J へ・暗渠は枡の外の面から ── 外の半幅は実メッシュで測る
        string masuNote = ""; float masuFloor = float.NaN;
        if (g.sump)
        {
            float yawM = Mathf.Atan2(g.outDir.x, g.outDir.y) * Mathf.Rad2Deg;
            var mgo = EdoBuild.Place(EdoAssets.Own.DoiMasu("G1"), new Vector3(g.J.x, g.yF, g.J.y), yawM, Vector3.one, grp, g.terrace + "_OmoteGesui_Masu");
            float outHalf = 0.375f;
            if (mgo != null) { float mx = 0f; float yLo = float.MaxValue; foreach (var v in EdoBuild.Body(mgo.transform, 4000)) { float d = Vector2.Dot(new Vector2(v.x, v.z) - g.J, g.outDir); if (v.y > g.yF - 0.3f) mx = Mathf.Max(mx, d); yLo = Mathf.Min(yLo, v.y); }
                if (mx > 0.05f) outHalf = mx; masuFloor = yLo; }
            line = new List<Vector2> { g.J + g.outDir * outHalf, g.E };
            masuNote = "・集水枡 G1 s=" + g.sumpS.ToString("F1", inv) + "(芯 " + g.J.x.ToString("F2", inv) + ", " + g.J.y.ToString("F2", inv) + "・外の半幅 " + outHalf.ToString("F3", inv) + (mgo == null ? " ⛔ 駒が無い" : "") + ")";
        }
        System.Func<float, float, float> gnd = (x, z) => g.yF;
        var spec = new EdoBuild.MizoSpec { chord = true, name = g.terrace + "_OmoteGesui", kata = "A", line = line, groundAt = gnd, topAbove = 0.02f, pieceDepth = float.NaN,
                                           depthMin = 0.10f, depthMax = g.dMax, slopeMin = g.slope, halfW = g.halfW, headBottom = headBottom };
        var pr = EdoBuild.SolveMizoBottom(spec);
        int miss; string mw; var fail = new List<string>();
        var made = EdoBuild.LayMizo(grp, g.terrace + "_OmoteGesui", pr, need => MizoAByDepth(need, spec.topAbove), out miss, out mw, gnd, fail);
        // 道(区画の線の外 1m の地形)が出口の底より低いか【硬】
        var road = g.E + g.outDir * 1f; float gr = EdoBuild.Ground(road.x, road.y);
        if (g.higuchi && _road != null && _road.ok) gr = RoadAtS(_road, Vector2.Dot(g.mouth - _road.ea, _road.ax));   // 樋口のときの道 = 区画の線の外 0.5
        bool roadOk = !float.IsNaN(gr) && (g.sump ? pr.Tail >= gr + g.sillAbove - 1e-3f : gr < pr.Tail - 0.01f);   // 集水枡の型: 敷き ≥ 道 + sillAbove【硬】
        if (!roadOk) { Clear(grp); sb.AppendLine("  ⛔ 表門脇の下水: 道 " + gr.ToString("F2", inv) + " が出口の底 " + pr.Tail.ToString("F3", inv) + " より低くない ── 内側を沿わせる線は未(普請方へ)・置かない"); return sb.ToString(); }
        // 樋口(追記 2026-10-10c): 口を腰石垣の見え面(解いた底の高さ)へ・床 = 溝の尻の底・嘴が区画の線の内か【硬】・道より上で吐くか【硬】
        string higNote = "";
        if (g.higuchi && _road != null && _road.ok)
        {
            var rp = _road; float tail = pr.Tail; float sF = Vector2.Dot(g.mouth - rp.ea, rp.ax); Vector2 crest = rp.ea + rp.ax * sF - rp.outN * rp.setback;
            Vector2 mouth = crest + rp.outN * (rp.batter * (rp.yTop - tail)); float yaw = Mathf.Atan2(rp.outN.x, rp.outN.y) * Mathf.Rad2Deg;
            var kgo = EdoBuild.Place(EdoAssets.Own.DoiAnkyoKuchi, new Vector3(mouth.x, tail - g.kuchiFloor, mouth.y), yaw, Vector3.one, grp, g.terrace + "_OmoteGesui_Higuchi");
            float tipOut = float.MinValue; if (kgo != null) foreach (var v in EdoBuild.Body(kgo.transform, 4000)) tipOut = Mathf.Max(tipOut, Vector2.Dot(new Vector2(v.x, v.z) - rp.ea, rp.outN));
            float roadY = RoadAtS(rp, sF);
            higNote = "・樋口 口 (" + mouth.x.ToString("F2", inv) + ", " + mouth.y.ToString("F2", inv) + ") 床 " + tail.ToString("F3", inv) + "・道 " + roadY.ToString("F2", inv) + (tail > roadY ? "(道より " + (tail - roadY).ToString("F2", inv) + " 上で吐く ⭕)" : " ⛔(道より上でない)")
                    + "・樋口の最も外 − 区画の線 " + (tipOut == float.MinValue ? "-" : tipOut.ToString("+0.000;-0.000", inv)) + (tipOut > 0.001f ? " ⛔" : " ⭕") + "【硬】";
        }
        // 暗渠: 門長屋の背〜表の間の駒に蓋石(型 A・厚 0.15)
        string lidP = EdoBuild.AssetByName("Own", "DoiFutaishiFor", "A", 0.15f); int lids = 0;
        if (lidP != null)
            foreach (var pc in made)
            {
                var lp = g.host.InverseTransformPoint(pc.transform.position); if (lp.z < g.back - 0.5f || lp.z > g.front + 0.5f) continue;
                var pb = EdoBuild.RB(pc); Vector3 fw = pc.transform.forward; fw.y = 0f; fw.Normalize(); float yaw = Mathf.Atan2(fw.x, fw.z) * Mathf.Rad2Deg;
                foreach (float dz in new[] { -0.25f, 0.25f })
                {
                    var c = new Vector3(pb.center.x, 0f, pb.center.z) + fw * dz;
                    var lid = EdoBuild.Place(lidP, c, yaw, Vector3.one, grp, pc.name + "_Futa" + (dz < 0f ? "0" : "1")); if (lid == null) continue;
                    // 蓋の天 = 面の高さ(第82巡【硬】: 駒の天端に載せると門長屋の背の手前で地表より 0.15 出た)── 蓋の芯が棟の背〜表の外なら置かない
                    var lpc = g.host.InverseTransformPoint(c); if (lpc.z < g.back || lpc.z > g.front) { UnityEngine.Object.DestroyImmediate(lid); continue; }
                    var lb = EdoBuild.RB(lid); lid.transform.position += new Vector3(0f, g.yF - lb.max.y, 0f); lids++;
                }
            }
        sb.AppendLine("  表門脇の下水 " + g.terrace + "(omoteGesui・門の口の " + (g.xs > 0f ? "+X" : "−X") + " 脇): 石組の溝 型A " + made.Count + " 駒・" + pr.length.ToString("F1", inv) + "m・底 " + pr.Head.ToString("F3", inv) + "→" + pr.Tail.ToString("F3", inv)
                      + "(1/" + Mathf.RoundToInt(1f / g.slope) + " 硬・出口 < 入口 ⭕)・暗渠の蓋 " + lids + " 枚・入口 J (" + g.J.x.ToString("F2", inv) + ", " + g.J.y.ToString("F2", inv) + ")・出口 (" + g.E.x.ToString("F2", inv) + ", " + g.E.y.ToString("F2", inv)
                      + ") 区画の線の内 0.01・道 " + gr.ToString("F2", inv) + "(出口の底より " + (pr.Tail - gr).ToString("F2", inv) + " 低い ⭕)" + (fail.Count > 0 ? "・⛔ 浮く駒 " + fail.Count : "") + (miss > 0 ? "・⚠ 駒が無い " + miss : "")
                      + (pr.worstDeep > 0.005f ? "・⚠ 深さ " + g.dMax.ToString("F2", inv) + " を最大 " + pr.worstDeep.ToString("F2", inv) + " 越える(柔)" : "") + higNote + masuNote
                      + (g.sump ? "・敷き " + pr.Tail.ToString("F3", inv) + " − 道 " + gr.ToString("F2", inv) + " = " + (pr.Tail - gr).ToString("+0.00;-0.00", inv) + "(≥ +" + g.sillAbove.ToString("F2", inv) + "【硬】⭕)" : ""));
        return sb.ToString();
    }

    /// <summary>DoiMizo 型 A のうち実測の深さ ≤ need + topAbove の最も深い駒(第80巡: 名の深さで選ぶと縁 0.02 の分だけ天端が浮いて落ちた)。</summary>
    static string MizoAByDepth(float need, float topAbove)
    {
        string bestP = null; float bestD = -1f;
        for (float dd = 0.10f; dd <= 0.30f + 1e-4f; dd += 0.05f)
        { var pth = EdoBuild.AssetByName("Own", "DoiMizo", "A", (float)System.Math.Round(dd, 2)); if (pth == null) continue; var mq = EdoBuild.MizoPieceOf(pth); if (!mq.ok) continue;
          if (mq.Depth <= need + topAbove + 0.005f && mq.Depth > bestD) { bestD = mq.Depth; bestP = pth; } }
        return bestP ?? EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.10f);
    }

    /// <summary>点 q を含む面のうち面積の最も小さい物の高さ(皮と同じ選び方)。名が skipPrefix で始まる面は外す。無ければ NaN。</summary>
    static float FaceYAt(List<EdoBuild.SkinFace> faces, Vector2 q, string skipPrefix)
    {
        float best = float.NaN, area = float.MaxValue;
        foreach (var f in faces)
        {
            if (f.poly == null || (skipPrefix != null && f.name != null && f.name.StartsWith(skipPrefix)) || !EdoGeom.PIP(f.poly, q)) continue;
            float a = 0f; for (int i = 0; i < f.poly.Length; i++) { var p0 = f.poly[i]; var p1 = f.poly[(i + 1) % f.poly.Length]; a += p0.x * p1.y - p1.x * p0.y; } a = Mathf.Abs(a) * 0.5f;
            if (a < area) { area = a; best = f.y; }
        }
        return best;
    }

    /// <summary>**長屋の前の下水溝**(指図 terraces[].roadEdge 追記 2026-10-10m・runs[].front・drains D_&lt;棟&gt;_Mae・普請方・EDO-0502 第95巡)。
    /// 区画の内に石組の溝(型A ── 背の雨落ち・表門脇の下水と同じ型)を棟の前の全長に通す。置き方(oki-kata の4手):
    /// ① 固定側 = 上の端の石垣(欄が名指す「〜を延ばした石垣」・Stage2b が先に据える)と棟の躯体(Stage2 が runs.front で寄せた)。
    /// ② 溝の芯の線 = 躯体の前の面(溝の高さの帯で**触れる所**を実頂点で測る)+ 0.005 + 駒の半幅 ── 内の壁が躯体の前の面に触れ、外の壁が区画の線の内【硬】。
    /// ③ 上の端 = 石垣の実頂点のうち溝の帯(幅 × 底〜天端)に入る物の、棟の側への最も先の s(突き付け・石垣が先【硬】)。下の端 = 棟の躯体の東の端、
    ///    ただし溝の矩形が他の棟の躯体・区画の外へ入る手前まで。④ 底 = 頭で座 −drop【硬】・そこから 1/n で下げる【柔】(SolveMizoBottom)。
    /// 深さは道の地盤(造成前の地盤 = 道の現地形・道は掘らない【硬】)から選ぶ ── 型A の最も深い版でも道に届かない所は「外の壁の天端が道より低い」を ⚠ で名乗る(柔ではなく
    /// 欄の「外の壁で道の地盤を受ける」が部材で満たせない所 ── 普請方へ)。当たる先: roadEdge 10-10m を持つ面と front に「下水溝」を持つ長屋(岡部 Kadonouchi × N39_1)。</summary>
    static string PlaceFrontGutters()
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var root = GameObject.Find(GN); if (root == null) return "";
        var grp = Group("FrontMizo"); Clear(grp);
        string txt = null, tName = null;
        foreach (var o in A(Get(D, "terraces")) ?? new List<object>()) { var t = O(o); string re = S(Get(t, "roadEdge")); if (re == null) continue; int i0 = re.IndexOf("追記 2026-10-10m"); if (i0 >= 0 && re.Substring(i0).Contains("下水溝")) { txt = re.Substring(i0); tName = S(Get(t, "name")); } }
        if (txt == null) return "";
        foreach (var r in Runs)
        {
            // 欄 10-10m が「<棟> の前の全長に通す」と名指す棟だけ(⛔ 文に名が出るだけで拾わない ── 第101巡: 10-10n② の「N40_0 の躯体の面」で N40_0 を拾い、
            //   別の溝 D_N40_Mae の棟に 10-10m の溝を 0.4m 据えた)
            if (!r.Nagaya) continue; string fr = RunText(r.name, "front"); if (fr == null || !fr.Contains("下水溝") || !txt.Contains(r.name + " の前の全長")) continue;
            var nbT = root.transform.Find("Kakoi/" + r.name); if (nbT == null) { sb.AppendLine("  ★ 前の下水溝 " + r.name + ": 棟が無い"); continue; }
            var mD = System.Text.RegularExpressions.Regex.Match(txt, @"座より\s*([0-9.]+)\s*以上低く");
            var mS = System.Text.RegularExpressions.Regex.Match(txt, @"1/(\d+)\s*で東へ");
            var mW = System.Text.RegularExpressions.Regex.Match(txt, @"溝の幅は\s*([0-9.]+)\s*〜\s*([0-9.]+)");
            var mH = System.Text.RegularExpressions.Regex.Match(txt, @"上の端は\s*([A-Za-z0-9_]+)\s*を延ばした石垣の面に突き付け");
            if (!mD.Success || !mS.Success || !mH.Success) { sb.AppendLine("  ★ 前の下水溝 " + r.name + ": 欄 roadEdge 10-10m の座からの落ち・勾配・上の端の石垣が読めない ── 置かない"); continue; }
            float drop = float.Parse(mD.Groups[1].Value, inv), slope = 1f / float.Parse(mS.Groups[1].Value, inv); string headWall = mH.Groups[1].Value;
            var p30 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.30f); var p10 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.10f);
            var m30 = p30 == null ? default(EdoBuild.MizoPiece) : EdoBuild.MizoPieceOf(p30); var m10 = p10 == null ? default(EdoBuild.MizoPiece) : EdoBuild.MizoPieceOf(p10);
            if (p30 == null || p10 == null || !m30.ok || !m10.ok) { sb.AppendLine("  ★ 前の下水溝 " + r.name + ": 石組の溝の駒(DoiMizo 型A)が測れない ── 置かない"); continue; }
            float halfW = Mathf.Max(Mathf.Abs(m30.xMin), Mathf.Abs(m30.xMax)), W = m30.xMax - m30.xMin;
            int e = r.edge; Vector2 ea = EdgePt(e, 0f), ax = (EdgePt(e, 1f) - ea).normalized, on = OutNormal(e);
            var bp = EdoBuild.BodyExRoof(nbT, 6000); if (bp.Count == 0) { sb.AppendLine("  ★ 前の下水溝 " + r.name + ": 躯体が測れない"); continue; }
            float y0 = float.MaxValue; foreach (var p in bp) y0 = Mathf.Min(y0, p.y);   // 座 = 躯体の底
            float headB = y0 - drop, yLo = headB - 0.40f, yHi = headB + m30.Depth + 0.05f;
            // ② 内の壁が触れる所 = 躯体の前の面(溝の高さの帯)
            float fFront = EdoBuild.FaceOut(nbT.gameObject, ea, on, y0 - 0.01f, Mathf.Max(yHi, y0 + 0.30f));
            if (float.IsNaN(fFront)) { sb.AppendLine("  ★ 前の下水溝 " + r.name + ": 躯体の前の面が測れない"); continue; }
            float dC = fFront + 0.005f + halfW, dOut = dC + halfW;
            if (dOut > 0.001f) { sb.AppendLine("  ⛔ 前の下水溝 " + r.name + ": 外の壁が区画の線の外 " + dOut.ToString("F3", inv) + " ── 置かない(runs.front の寄せが足りない)"); continue; }
            var sp = EdoBuild.SpecBodySpanAlong(nbT.gameObject, ea, ax); if (float.IsNaN(sp.x)) sp = EdoBuild.BodySpanAlong(nbT.gameObject, ea, ax);
            // ③ 上の端 = 石垣が先(溝の帯に入る石垣の実頂点の、棟の側への最も先の s)
            float sHead = float.NaN; string headGo = null;
            foreach (Transform dc in Group("Dan"))
            {
                // 名指しの石垣と、それに出隅で継ぐ駒(道の側の腰石垣の隅の駒 ── 溝の帯へ出るのは隅の駒の腕・第95巡の一回目は名で篩って 0 駒)。
                //   帯 = 溝の幅 × 底〜天端 + 0.6(溝の上に石垣が被る所へも入れない)・棟の妻の ±3m
                if (!dc.gameObject.activeInHierarchy) continue;
                foreach (var v in EdoBuild.Body(dc, 8000))
                {
                    var q = new Vector2(v.x, v.z) - ea; float d = Vector2.Dot(q, on), s = Vector2.Dot(q, ax);
                    if (d < dC - halfW - 0.02f || d > dC + halfW + 0.02f || v.y < yLo || v.y > yHi + 0.6f || s > sp.x + 0.5f || s < sp.x - 3f) continue;
                    if (float.IsNaN(sHead) || s > sHead) { sHead = s; headGo = dc.name; }
                }
            }
            bool headOk = !float.IsNaN(sHead);
            if (!headOk) { sHead = sp.x; sb.AppendLine("  ⛔ 前の下水溝 " + r.name + ": 上の端の石垣 " + headWall + " が溝の帯(芯 " + dC.ToString("F2", inv) + "・底〜天端)に無い ── 突き付けられず躯体の妻 s " + sp.x.ToString("F2", inv) + " から(普請方へ)"); }
            // 下の端 = 躯体の東の端・他の棟の躯体と区画の外の手前
            var hulls = new List<KeyValuePair<string, Vector2[]>>();
            foreach (Transform c in root.transform.Find("Kakoi"))
            {
                if (c == nbT || !c.gameObject.activeInHierarchy || !EdoBuild.IsNagayaBody(c.gameObject)) continue;
                var cp = EdoBuild.BodyExRoof(c, 4000); if (cp.Count == 0) continue; float cy = float.MaxValue; foreach (var v in cp) cy = Mathf.Min(cy, v.y);
                if (cy > yHi + 0.6f) continue;   // 溝より高い座の棟(台の上の N39_0)は溝の高さに居ない ── 平面の重なりで止めない(第95巡の一回目は 0.4m で止めた)
                var p2 = new List<Vector2>(); foreach (var v in cp) if (v.y < cy + 2.0f) p2.Add(new Vector2(v.x, v.z)); if (p2.Count < 3) continue;
                var hh = EdoBuild.ConvexHull2(p2).ToArray(); bool near = false; foreach (var h in hh) if (Vector2.Distance(h, ea + ax * sp.y) < 25f) near = true; if (near) hulls.Add(new KeyValuePair<string, Vector2[]>(c.name, hh));
            }
            float sTail = sp.y; string tailWhy = "躯体の東の端";
            for (float s = sHead + 0.5f; s <= sp.y + 1e-3f; s += 0.05f)
            {
                string hit = null;
                foreach (float dd in new[] { dC - halfW, dC, dC + halfW })
                {
                    var q = ea + ax * s + on * dd; if (!EdoGeom.PIP(Poly, q)) { hit = "区画の線"; break; }
                    foreach (var kv in hulls) if (EdoGeom.PIP(kv.Value, q)) { hit = kv.Key + " の躯体"; break; } if (hit != null) break;
                }
                if (hit != null) { sTail = s - 0.06f; tailWhy = hit + " の手前"; break; }
            }
            var line = new List<Vector2> { ea + ax * sHead + on * dC, ea + ax * sTail + on * dC };
            var bd = EdoBuild.BaseDem();
            System.Func<float, float, float> road = (x, z) => { float s = Vector2.Dot(new Vector2(x, z) - ea, ax); var qq = ea + ax * s + on * 0.05f; return bd(qq.x, qq.y); };
            System.Func<float, float, float> gnd = (x, z) => Mathf.Max(road(x, z), y0);   // 溝の天端の狙い = 道の地盤(座より低い所は座)
            var spec = new EdoBuild.MizoSpec { chord = true, name = r.name + "_Mae", kata = "A", line = line, groundAt = gnd, topAbove = 0.02f, pieceDepth = float.NaN,
                                               depthMin = m10.Depth, depthMax = m30.Depth, slopeMin = slope, halfW = halfW, headBottom = headB };
            var pr = EdoBuild.SolveMizoBottom(spec);
            int miss; string mw; var fail = new List<string>();
            var made = EdoBuild.LayMizo(grp, r.name + "_Mae", pr, need => MizoAByDepth(need, spec.topAbove), out miss, out mw, gnd, fail);
            // 外の壁の天端と道(欄「外の壁で道の地盤を受ける」)── 型A の最も深い版で届かない所
            float shortMax = 0f; int nShort = 0; float sShort0 = float.NaN, sShort1 = float.NaN;
            foreach (var g in made)
            {
                var b = EdoBuild.RB(g); var cq = new Vector2(b.center.x, b.center.z); float rd = road(cq.x, cq.y), sh = rd - b.max.y;
                if (sh > 0.02f) { nShort++; shortMax = Mathf.Max(shortMax, sh); float sc = Vector2.Dot(cq - ea, ax); sShort0 = float.IsNaN(sShort0) ? sc : Mathf.Min(sShort0, sc); sShort1 = float.IsNaN(sShort1) ? sc : Mathf.Max(sShort1, sc); }
            }
            float headGap = float.NaN;
            if (made.Count > 0 && headOk) { float smin = float.MaxValue; foreach (var v in EdoBuild.Body(made[0].transform, 4000)) smin = Mathf.Min(smin, Vector2.Dot(new Vector2(v.x, v.z) - ea, ax)); headGap = smin - sHead; }
            Vector2 tP = line[1]; float roadTail = road(tP.x, tP.y);
            sb.AppendLine("  前の下水溝 " + tName + " × " + r.name + "(roadEdge 追記 2026-10-10m・D_" + r.name + "_Mae): 石組の溝 型A " + made.Count + " 駒・" + pr.length.ToString("F1", inv) + "m(s " + sHead.ToString("F2", inv) + "〜" + sTail.ToString("F2", inv) + "・下の端 = " + tailWhy + ")"
                          + "・全幅 " + W.ToString("F2", inv) + (mW.Success ? (W >= float.Parse(mW.Groups[1].Value, inv) - 1e-3f && W <= float.Parse(mW.Groups[2].Value, inv) + 1e-3f ? " ⭕(柔 " : " ⚠(柔 ") + mW.Groups[1].Value + "〜" + mW.Groups[2].Value + ")" : "")
                          + "・内の壁 = 躯体の前の面 " + fFront.ToString("F3", inv) + "・外の壁 " + dOut.ToString("F3", inv) + "(区画の線の内【硬】⭕)"
                          + "・底 " + pr.Head.ToString("F3", inv) + "→" + pr.Tail.ToString("F3", inv) + "(座 " + y0.ToString("F2", inv) + " − " + drop.ToString("F2", inv) + " 以下【硬】" + (pr.Head <= headB + 1e-3f ? "⭕" : "⛔") + "・1/" + mS.Groups[1].Value + ")"
                          + "・上の端 " + (headOk ? headWall + " の面へ突き付け〔" + headGo + "〕隙 " + headGap.ToString("+0.000;-0.000", inv) : "突き付けず ⛔")
                          + (nShort > 0 ? "・⚠ 外の壁の天端が道より低い " + nShort + " 駒(最大 " + shortMax.ToString("F2", inv) + "・s " + sShort0.ToString("F1", inv) + "〜" + sShort1.ToString("F1", inv) + ")── 型A の深さ " + m30.Depth.ToString("F2", inv) + " では道の地盤を受けきれない(普請方へ)" : "・外の壁の天端 ≥ 道 ⭕")
                          + "・尻の底 " + pr.Tail.ToString("F2", inv) + " / 道 " + roadTail.ToString("F2", inv) + (pr.Tail < roadTail - 0.01f ? " ⚠ 尻が道より低く道へ落ちない(道は掘らない【硬】・排水の検査は未)" : " ⭕")
                          + (fail.Count > 0 ? "・⛔ 浮く駒 " + fail.Count + " を据えない" : "") + (miss > 0 ? "・⚠ 駒が無い " + miss : "") + (pr.ok ? "" : "・⛔ " + pr.hard));
            // ── 追記 2026-10-10n ①(第96巡): 外の壁だけを嵩上げし、天端は道の地盤 + 0.02【硬】・内の壁と底は今のまま・道は触らない【硬】・隣の駒との天端の段差 ≤ 0.05【柔】
            int i10n = txt.IndexOf("追記 2026-10-10n"); string tn = i10n < 0 ? "" : txt.Substring(i10n);
            var mK = System.Text.RegularExpressions.Regex.Match(tn, @"外の壁だけを嵩上げし、天端は道の地盤\s*\+\s*([0-9.]+)");
            var mKs = System.Text.RegularExpressions.Regex.Match(tn, @"天端の段差は\s*([0-9.]+)\s*以下");
            if (mK.Success && made.Count > 0)
            {
                float kUp = float.Parse(mK.Groups[1].Value, inv), kStep = mKs.Success ? float.Parse(mKs.Groups[1].Value, inv) : float.NaN;
                var kg = Group("FrontMizoKasa"); Clear(kg); var kFail = new List<string>();
                System.Func<float, float, float> tgt = (x, z) => road(x, z) + kUp;
                var ks = EdoBuild.LayMizoKasa(kg, made, on, tgt, h => EdoAssets.Own.DoiMizoAKasa(h), 0.10f, 0.45f, 0.05f, kFail);
                // 検め: 天端 − 狙い(両端の最小・最大)・隣の天端の段差(溝の駒の並びで、載せない駒は縁石の天端)
                float dLo = float.MaxValue, dHi = float.MinValue, stepMax = 0f; string stepAt = "-";
                var byP = new Dictionary<GameObject, GameObject>(); foreach (var k in ks) { var pn = k.name.Substring(0, k.name.Length - 5); foreach (var g in made) if (g.name == pn) byP[g] = k; }
                System.Func<GameObject, float, float> topAtEnd = (g, sgn) =>
                {
                    GameObject k; string pp = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(g); var q = EdoBuild.MizoPieceOf(pp);
                    if (byP.TryGetValue(g, out k)) { var km = EdoBuild.MizoPieceOf(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(k)); return k.transform.TransformPoint(new Vector3(0f, km.top, sgn < 0 ? km.zMin : km.zMax)).y; }
                    Vector3 rx = g.transform.right; int sd = Vector2.Dot(new Vector2(rx.x, rx.z), on) >= 0f ? 1 : -1; float xa, xb, ct; EdoBuild.MizoCurbTop(pp, sd, out xa, out xb, out ct);
                    return g.transform.TransformPoint(new Vector3(0.5f * (xa + xb), ct, sgn < 0 ? q.zMin : q.zMax)).y;
                };
                foreach (var k in ks)
                {
                    var km = EdoBuild.MizoPieceOf(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(k));
                    foreach (float lz in new[] { km.zMin, km.zMax }) { var w = k.transform.TransformPoint(new Vector3(0f, km.top, lz)); float d0 = w.y - tgt(w.x, w.z); dLo = Mathf.Min(dLo, d0); dHi = Mathf.Max(dHi, d0); }
                }
                for (int q = 1; q < made.Count; q++) { float st = Mathf.Abs(topAtEnd(made[q], -1f) - topAtEnd(made[q - 1], 1f)); if (st > stepMax) { stepMax = st; stepAt = made[q - 1].name + "×" + made[q].name; } }
                sb.AppendLine("    外の壁の嵩上げ(roadEdge 追記 2026-10-10n ①): 嵩上げ石 " + ks.Count + " / 溝の駒 " + made.Count + "(狙い = 道の地盤 + " + kUp.ToString("F2", inv) + "【硬】)"
                              + (ks.Count > 0 ? "・天端 − 狙い " + dLo.ToString("+0.000;-0.000", inv) + "〜" + dHi.ToString("+0.000;-0.000", inv) + (dLo >= -0.005f ? " ⭕" : " ⛔") + "(上への外れは丈の刻み 0.05)" : "")
                              + "・隣の天端の段差の最大 " + stepMax.ToString("F3", inv) + "〔" + stepAt + "〕" + (float.IsNaN(kStep) ? "" : stepMax <= kStep + 1e-3f ? " ⭕(柔 ≤" + kStep.ToString("F2", inv) + ")" : " ⚠(柔 ≤" + kStep.ToString("F2", inv) + ")")
                              + (kFail.Count > 0 ? "・⛔ " + string.Join(" / ", kFail.ToArray()) : ""));
            }
            // ── drains D_<棟>_Mae(10-10n で置き換え): 尻は塞ぎ石で閉じ、在庫の石樋の暗渠を区画の線の内で隣の辺に沿い 1/n で下流へ【硬】・吐き口は型M・床が前の道より x 以上高くなる最初の所【硬】
            sb.Append(PlaceFrontAnkyo(r, line[1], pr.Tail, sTail, made.Count > 0 ? made[made.Count - 1] : null));
        }
        return sb.ToString();
    }

    /// <summary>台の前の溝(D_N40_Mae・Mizo_*)は**地際の張り出し付きの版**(<c>EdoAssets.Own.DoiMizo(kata, d, ago: true)</c>・縁石の外へ土の板 0.40)で据える
    /// ── 第111巡で天端を地表と面一にした後、0.25m 格子の地形が縁石の外に立てた鋸の歯を板の下に隠す(EDO-0502 第112巡・普請奉行の指示 2026-10-11)。
    /// 溝・石は A / AH と同じ・据え方(天端の線・傾け)も同じ。板の下の地面は <see cref="EdoBuild.SinkGroundUnderMizo"/> が板の上面より下げる。</summary>
    const bool MizoAgo = true;

    /// <summary>**台の前の溝の区間**(指図 grading.omoteNagayaDai.mizo ── sections Mizo_Kita / Mizo_Minami / Mizo_Hashi・outlets・outerTop/topLine/depth/fall・EDO-0502 第108〜111巡)。
    /// ⭐ 第111巡(施主 2026-10-11「側溝の上面がガタガタ」「溝の上面が地表の面と一致しているべき」): 縁石の作り AF/AFH と嵩上げ石は廃止。全区間 型A を
    /// **天端の線**で据える(<see cref="EdoBuild.LayMizoOnTopLine"/>)── 線 = 外の壁の見え面の 0.30 外の造成の面を滑らかにして下り続けさせた線・駒は勾配なりに傾け・
    /// 底は従属(天端 − 版の深さ)。溝の両脇 0.3m の地面は Stage3d が縁石の天端へ合わせる(<see cref="EdoBuild.FlushGroundToMizoTop"/>)。
    /// ① 線 = 区画の線から内へ 駒の半幅 + 0.001(外の壁の見え面 = 区画の線の内【硬】)。辺を跨ぐ区間は二辺の線を交点で折る。
    ///    吐き口(outlets)に先に着く区間は吐き口の駒(AH・1m・芯 = 吐き口の s)を尻の駒として含み、後に着く区間は吐き口の駒の小口で止めて天端をその駒へ寄せる。
    /// ② 頭: Mizo_Kita は D_N40_Mae の尻の天端と底を続ける・分水(s44〜46)は Mizo_Minami の頭の天端へ寄せる。
    /// ③ 門の口(sections[].gate)は蓋石の暗渠 ── 蓋の下の駒は天端を蓋の厚だけ下げ、蓋の天端 = 地表(± 0.02)・敷居 −0.02 以下【硬】。
    /// ④ 刷る: 天端 − 造成の面・隣の天端の段差【硬 ≤0.01】・底の上り【硬 0】・深さ【硬 ≥ depth・柔 狙い】・吐き口の敷き − 線から 1m 外の道。
    /// 当たる先: 台の前の溝を sections・outlets で書く邸(いまは岡部)。同じ型(天端の線で据える)は D_N40_Mae(<see cref="PlaceDrainFrontGutters"/>)。</summary>
    static string PlaceMizoSections()
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var root = GameObject.Find(GN); if (root == null) return "";
        var grp = Group("SecMizo"); Clear(grp); var kg = Group("SecMizoKasa"); Clear(kg); var lg = Group("SecMizoFuta"); Clear(lg);
        _secMizoTail.Clear(); _secMizoProf.Clear(); _secMizoLine.Clear(); _secMizoOutlet.Clear();
        var mz = O(Get(O(Get(O(Get(D, "grading")), "omoteNagayaDai")), "mizo")); if (mz == null) return "";
        // 地際の張り出しの板の材(Hifu_KitaTerrain_World)を細かい地形のスプラット・原点へ結わえ直す(結わえないと _Control が既定の赤 = 層 0 の土一色)。EDO-0502 第113巡
        if (MizoAgo) { var ft = EdoBuild.FineTerrain(); if (ft != null) EdoBuild.SkinWorldMaterial(ft); }
        var RX = (System.Func<string, string, System.Text.RegularExpressions.Match>)((t, p) => System.Text.RegularExpressions.Regex.Match(t ?? "", p));
        string otT = S(Get(mz, "outerTop")) ?? "";
        var mBand = RX(otT, @"幅\s*([0-9.]+)\s*m\s*の帯"); var mDp = RX(S(Get(mz, "depth")), @"([0-9.]+)\s*以上【硬】"); var mDt = RX(S(Get(mz, "depth")), @"([0-9.]+)\s*前後を狙う");
        var mFl = RX(S(Get(mz, "fall")), @"1/(\d+)");
        if (!otT.Contains("面一") || !mBand.Success || !mDp.Success || !mDt.Success)
            return "  ★ 台の前の溝: mizo.outerTop(地表と面一・幅 x m の帯)/ depth(x 以上【硬】・x 前後を狙う)が読めない ── 置かない\n";
        float band = float.Parse(mBand.Groups[1].Value, inv), depthMin = float.Parse(mDp.Groups[1].Value, inv), depthTgt = float.Parse(mDt.Groups[1].Value, inv);
        float fallSoft = mFl.Success ? 1f / float.Parse(mFl.Groups[1].Value, inv) : float.NaN;
        var ol = O(Get(mz, "outlets"));
        var mK = RX(S(Get(ol, "kita_s44")), @"吐き口は辺\s*(\d+)\s*s\s*([0-9.]+)"); var mKs = RX(S(Get(ol, "kita_s44")), @"敷き\s*([0-9.]+)[(（]線から\s*1m\s*外の道.*?\+\s*([0-9.]+)");
        var mM = RX(S(Get(ol, "minami_s76")), @"落ち合い\s*s\s*([0-9.]+)\s*は\s*AH"); var mMs = RX(S(Get(ol, "minami_s76")), @"敷き\s*≥\s*線から\s*1m\s*外の道\s*[−-]\s*([0-9.]+)");
        var mJ = RX(S(Get(ol, "s44_46")), @"s\s*([0-9.]+)\s*を分水の頭");
        if (ol == null || !mK.Success || !mKs.Success || !mM.Success || !mMs.Success || !mJ.Success)
            return "  ★ 台の前の溝: outlets(kita_s44 の吐き口と敷き / minami_s76 の AH と敷き / s44_46 の分水の頭)が読めない ── 置かない\n";
        int eOut = int.Parse(mK.Groups[1].Value);
        float sK = float.Parse(mK.Groups[2].Value, inv), sillKUp = float.Parse(mKs.Groups[2].Value, inv), sM = float.Parse(mM.Groups[1].Value, inv), sillMDown = float.Parse(mMs.Groups[1].Value, inv), sJ = float.Parse(mJ.Groups[1].Value, inv);
        var p30 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.30f); var m30 = p30 == null ? default(EdoBuild.MizoPiece) : EdoBuild.MizoPieceOf(p30);
        if (p30 == null || !m30.ok) return "  ★ 台の前の溝: 石組の溝の駒(DoiMizo 型A)が測れない ── 置かない\n";
        float halfW = Mathf.Max(Mathf.Abs(m30.xMin), Mathf.Abs(m30.xMax)), dC = halfW + 0.001f, pLen = m30.zMax - m30.zMin;
        System.Func<string, List<string>> vers = k =>
        {
            var l = new List<string>();
            for (float dd = 0.10f; dd <= 0.30f + 1e-4f; dd += 0.05f) { string pth = EdoAssets.Own.DoiMizo(k, (float)System.Math.Round(dd, 2), MizoAgo); if (EdoBuild.MizoPieceOf(pth).ok) l.Add(pth); }
            return l;
        };
        var vA = vers("A"); var vAH = vers("AH");
        if (vA.Count == 0 || vAH.Count == 0) return "  ★ 台の前の溝: 型 A / AH の駒が測れない ── 置かない\n";
        var bd = EdoBuild.BaseDem(); var mn = MichiNarashi;
        string lidP = EdoAssets.Own.DoiFutaishiFor("A", 0.15f); var lm = EdoBuild.MizoPieceOf(lidP); float lidT = lm.top - lm.bottom, lidLen = lm.len > 0.05f ? lm.len : 0.5f;
        System.Func<int, Vector2, float, float> roadOn = (e, q, off) =>
        {
            Vector2 eb = EdgePt(e, 0f), axb = (EdgePt(e, 1f) - eb).normalized; float s2 = Mathf.Clamp(Vector2.Dot(q - eb, axb), 0f, EdgeLen(e));
            var p = eb + axb * s2 + OutNormal(e) * off; float b0 = bd(p.x, p.y), m0 = mn == null ? float.NaN : MichiNarashiAt(mn, p.x, p.y);
            return float.IsNaN(m0) ? b0 : (float.IsNaN(b0) ? m0 : Mathf.Min(b0, m0));
        };
        // 地表 = 造成の面(okabe_graded.bin・区画の外も持つ)── 無い所は道の線上の地盤
        System.Func<float, float, float> surf = (x, z) => { var q = new Vector2(x, z); float y = DesignY(q); return float.IsNaN(y) ? roadOn(LidEdge(q), q, 0.30f) : y; };
        System.Func<Vector2, Vector2> outAt = q => OutNormal(LidEdge(q));
        // 区間: sections + s44〜46 の分水(型A)
        var secList = new List<Dictionary<string, object>>();
        foreach (var o in A(Get(mz, "sections")) ?? new List<object>()) { var sec = O(o); if (sec != null) secList.Add(sec); }
        secList.Add(new Dictionary<string, object> { { "name", "Mizo_Bunsui" }, { "kind", "型A(outlets.s44_46)" }, { "from", "辺" + eOut + " s" + sJ.ToString("0.###", inv) }, { "to", "辺" + eOut + " s" + sK.ToString("0.###", inv) } });
        var outletGo = new Dictionary<float, GameObject>(); var headOf = new Dictionary<float, GameObject>();
        foreach (var sec in secList)
        {
            string nm = S(Get(sec, "name")) ?? "?";
            var mF = RX(S(Get(sec, "from")), @"辺\s*(\d+)\s*s\s*([0-9.]+)"); var mT = RX(S(Get(sec, "to")), @"辺\s*(\d+)\s*s\s*([0-9.]+)");
            if (!mF.Success || !mT.Success) { sb.AppendLine("  ★ 台の前の溝 " + nm + ": from / to の辺と s が読めない ── 置かない"); continue; }
            int eF = int.Parse(mF.Groups[1].Value), eT = int.Parse(mT.Groups[1].Value); float sF = float.Parse(mF.Groups[2].Value, inv), sT = float.Parse(mT.Groups[2].Value, inv);
            int nP = Poly.Length;
            if (eT != eF && eT != (eF + 1) % nP) { sb.AppendLine("  ★ 台の前の溝 " + nm + ": 辺" + eF + "→辺" + eT + " は隣の辺でない ── 置かない"); continue; }
            float sOut = float.NaN; string outKata = null;
            if (eT == eOut && Mathf.Abs(sT - sK) < 0.01f) { sOut = sK; outKata = "AH"; }
            else if (eT == eOut && Mathf.Abs(sT - sM) < 0.01f) { sOut = sM; outKata = "AH"; }
            bool first = !float.IsNaN(sOut) && !outletGo.ContainsKey(sOut);
            float fwd = sF < sT || eT != eF ? 1f : -1f;
            float sEnd = float.IsNaN(sOut) ? sT : sT + (first ? fwd : -fwd) * pLen * 0.5f;
            System.Func<int, float, Vector2> At = (e, s) => EdgePt(e, s) - OutNormal(e) * dC;
            var line = new List<Vector2>();
            if (eT == eF) { line.Add(At(eF, sF)); line.Add(At(eF, sEnd)); }
            else
            {
                Vector2 a0 = At(eF, 0f), d0 = (EdgePt(eF, 1f) - EdgePt(eF, 0f)).normalized, a1 = At(eT, 0f), d1 = (EdgePt(eT, 1f) - EdgePt(eT, 0f)).normalized;
                float den = d0.x * d1.y - d0.y * d1.x; if (Mathf.Abs(den) < 1e-4f) { sb.AppendLine("  ★ 台の前の溝 " + nm + ": 二辺が平行 ── 置かない"); continue; }
                Vector2 w = a1 - a0; float t = (w.x * d1.y - w.y * d1.x) / den; var X = a0 + d0 * t;
                line.Add(At(eF, sF)); line.Add(X); line.Add(At(eT, sEnd));
            }
            System.Func<Vector2, float> arcOf = q => { float dd; return EdoBuild.NearestS(line, q, out dd); };
            var gateSpans = new List<Vector2>(); float sillG = float.NaN;
            { var gt = S(Get(sec, "gate")) ?? ""; var mg = RX(gt, @"辺\s*(\d+)\s*s\s*([0-9.]+)\s*〜\s*([0-9.]+)"); var ms = RX(gt, @"敷居\s*([0-9.]+)");
              if (mg.Success) { int ge = int.Parse(mg.Groups[1].Value); gateSpans.Add(new Vector2(arcOf(At(ge, float.Parse(mg.Groups[2].Value, inv))), arcOf(At(ge, float.Parse(mg.Groups[3].Value, inv))))); }
              if (ms.Success) sillG = float.Parse(ms.Groups[1].Value, inv); }
            System.Func<float, bool> inGate = s => { foreach (var g in gateSpans) if (s >= Mathf.Min(g.x, g.y) - 0.05f && s <= Mathf.Max(g.x, g.y) + 0.05f) return true; return false; };
            var spec = new EdoBuild.MizoTopSpec { name = nm, line = line, surfaceAt = surf, outAt = outAt, halfW = halfW, surfaceOff = band, versions = vA,
                                                  tailVersions = first ? vAH : null, depthMin = depthMin, depthTarget = depthTgt, coverAt = gateSpans.Count > 0 ? inGate : null, coverT = lidT };
            // 頭: D_N40_Mae の尻(辺40 で始まる区間)/ 分水は Mizo_Minami の頭の駒へ
            string headNote = "";
            if (eF == 40)
            {
                EdoBuild.MizoTopRep up; if (_drainTopRep.TryGetValue("D_N40_Mae", out up) && up.made.Count > 0)
                { spec.headTop = up.topTail; spec.headBottomMax = up.botTail; headNote = "・頭 = D_N40_Mae の尻(天端 " + up.topTail.ToString("F3", inv) + "・底 " + up.botTail.ToString("F3", inv) + ")"; }
                else headNote = "・⚠ D_N40_Mae が建っていない ── 頭は地表のまま";
            }
            GameObject hg; if (nm == "Mizo_Bunsui" && headOf.TryGetValue(sJ, out hg)) { spec.headTop = EdoBuild.MizoCurbTopAt(hg, line[0], outAt(line[0])); headNote = "・頭 = Mizo_Minami の頭の駒の天端 " + spec.headTop.ToString("F3", inv); }
            GameObject og = null; if (!float.IsNaN(sOut) && !first && outletGo.TryGetValue(sOut, out og)) { spec.tailTop = EdoBuild.MizoCurbTopAt(og, line[line.Count - 1], outAt(line[line.Count - 1])); }
            var rep = EdoBuild.LayMizoOnTopLine(grp, nm, spec);
            if (rep.made.Count == 0) { sb.AppendLine("  ⛔ 台の前の溝 " + nm + ": 駒が据わらない(" + string.Join("・", rep.notes.ToArray()) + ")"); continue; }
            headOf[sF] = rep.made[0];
            // ⭐ 頭の小口止め(sections[].end「…で小口の石で止める【硬: 小口の石の外面は区画の線を越えない】」・第114巡)── 小口の石(EdoAssets.Own.DoiMizoKoguchi)は
            //   A の 1m 駒と同じピボット・局所 −Z の端を塞ぐ ⇒ 頭の駒と同じ position・rotation。頭の駒の −Z が上流(線の頭)を向かなければ 180° 返す。
            string kogNote = "";
            if ((S(Get(sec, "end")) ?? "").Contains("小口の石で止める"))
            {
                var hd = rep.made[0]; Vector2 fl = (line[Mathf.Min(1, line.Count - 1)] - line[0]).normalized; Vector3 fw = hd.transform.forward;
                float rotY = Vector2.Dot(new Vector2(fw.x, fw.z), fl) >= 0f ? 0f : 180f;   // +Z が下流 ⇒ −Z の端 = 頭
                var kgo = EdoBuild.Place(EdoAssets.Own.DoiMizoKoguchi, hd.transform.position, hd.transform.eulerAngles.y + rotY, Vector3.one, grp, nm + "_Koguchi");
                if (kgo != null)
                {
                    kgo.transform.rotation = hd.transform.rotation * Quaternion.Euler(0f, rotY, 0f); kgo.transform.position = hd.transform.position;
                    float oMax = 0f; foreach (var v in EdoBuild.Body(kgo.transform, 4000)) { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(Poly, q)) oMax = Mathf.Max(oMax, EdoGeom.DistToPolyEdge(Poly, q)); }
                    float dHead = Vector2.Distance(new Vector2(EdoBuild.RB(kgo).center.x, EdoBuild.RB(kgo).center.z), line[0]);
                    kogNote = "・頭の小口止め " + kgo.name + "(頭の駒と同じ据え" + (rotY != 0f ? "・180° 返した" : "") + "・線の頭から " + dHead.ToString("F2", inv) + "m・区画の外 " + oMax.ToString("F3", inv) + (oMax <= 0.001f ? " ⭕" : " ⛔") + ")";
                }
                else kogNote = "・⛔ 小口の石 " + EdoAssets.Own.DoiMizoKoguchi + " が据わらない";
            }
            // 吐き口の駒(先に着く区間の尻)
            string outNote = kogNote;
            if (first)
            {
                var go = rep.made[rep.made.Count - 1]; string gn = nm + "_Hakiguchi"; go.name = gn; outletGo[sOut] = go; _secMizoOutlet[gn] = go;
                string pth = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go); var mp = EdoBuild.MizoPieceOf(pth);
                Vector2 c = EdgePt(eOut, sOut) - OutNormal(eOut) * dC, on = OutNormal(eOut);
                float sill = go.transform.TransformPoint(new Vector3(0f, mp.floor, 0.5f * (mp.zMin + mp.zMax))).y, rd1 = roadOn(eOut, c, 1.0f);
                float outMax = float.MinValue, outSoil = float.MinValue; Vector2 e0 = EdgePt(eOut, 0f);
                foreach (var mt in new[] { "rocks", "Gravel" }) foreach (var v in EdoBuild.BodyOfMat(go.transform, mt)) outMax = Mathf.Max(outMax, Vector2.Dot(new Vector2(v.x, v.z) - e0, on));   // 石(縁石・敷き石・底)
                foreach (var v in EdoBuild.ApronBody(go.transform)) outSoil = Mathf.Max(outSoil, Vector2.Dot(new Vector2(v.x, v.z) - e0, on));   // 地際の張り出し(土の板)
                bool kita = Mathf.Abs(sOut - sK) < 0.01f; float dS = sill - rd1;
                outNote = kogNote + "・吐き口 " + gn + "(辺" + eOut + " s" + sOut.ToString("0.##", inv) + "・" + System.IO.Path.GetFileNameWithoutExtension(pth) + "・+X を外へ " + (Vector2.Dot(new Vector2(go.transform.right.x, go.transform.right.z), on) > 0f ? "⭕" : "⛔")
                          + "): 敷き " + sill.ToString("F3", inv) + " − 線から 1m 外の道 " + rd1.ToString("F3", inv) + " = " + dS.ToString("+0.000;-0.000", inv)
                          + (kita ? (dS >= sillKUp - 1e-3f ? " ⭕" : " ⛔(kita_s44『+" + sillKUp.ToString("F2", inv) + " 以上【硬】』── 天端 = 地表と深さ ≥" + depthMin.ToString("F2", inv) + " とは両立しない ⇒ 差し戻し)")
                                  : (dS >= -sillMDown - 1e-3f ? " ⭕(柔 ≥ −" + sillMDown.ToString("F2", inv) + ")" : " ⚠(柔 ≥ −" + sillMDown.ToString("F2", inv) + ")"))
                          + "・駒の石の外の面 − 区画の線 " + outMax.ToString("+0.000;-0.000", inv) + (outMax <= 0.001f ? " ⭕" : " ⛔(区画の外【硬】)")
                          + (outSoil > float.MinValue ? "・地際の張り出し(土の板)の外の縁 − 区画の線 " + outSoil.ToString("+0.000;-0.000", inv) + (outSoil <= 0.001f ? " ⭕" : " ⚠(道の側へ出る)") : "");
                _secMizoTail[nm] = new Vector3(sOut, rep.botTail, sill);
            }
            else if (og != null)
            {
                string op = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(og); var om = EdoBuild.MizoPieceOf(op); var lp = og.transform.InverseTransformPoint(new Vector3(line[line.Count - 1].x, 0f, line[line.Count - 1].y));
                float sillEnd = og.transform.TransformPoint(new Vector3(0f, om.floor, Mathf.Clamp(lp.z, om.zMin, om.zMax))).y;
                outNote = kogNote + "・尻 = 吐き口 " + og.name + " の小口(天端を寄せた " + spec.tailTop.ToString("F3", inv) + "・尻の底 − 吐き口の底 " + (rep.botTail - sillEnd).ToString("+0.000;-0.000", inv) + (rep.botTail >= sillEnd - 1e-3f ? " ⭕(落とし先が低い)" : " ⛔(落とし先が高い)") + ")";
                _secMizoTail[nm] = new Vector3(sOut, rep.botTail, sillEnd);
            }
            // 門の口の蓋石(蓋の下の駒の範囲)
            int nLid = 0, nLidIn = 0; float lidOutLeft = 0f, lidLo = float.MaxValue, lidHi = float.MinValue, sillGap = float.MaxValue; var lids = new List<GameObject>();
            foreach (var cs in rep.coverSpans)
            {
                var under = new List<GameObject>(rep.covered);
                for (float s = cs.x + lidLen * 0.5f; s <= cs.y - lidLen * 0.5f + lidLen * 0.999f; s += lidLen)
                {
                    float sc = Mathf.Min(s, cs.y - lidLen * 0.5f); Vector2 dd; var at = EdoBuild.PointAt(line, Mathf.Clamp(sc, 0f, rep.length), out dd);
                    float off; var lid = EdoBuild.LayFutaishi(lg, nm + "_Futa_" + nLid, lidP, at, dd, under, surf, out off);
                    if (lid == null) continue; nLid++; lids.Add(lid);
                    { var qo = at + outAt(at) * (halfW + band); off = EdoBuild.RB(lid).max.y - surf(qo.x, qo.y); lidLo = Mathf.Min(lidLo, off); lidHi = Mathf.Max(lidHi, off); }   // 蓋の天端 − 帯の外の造成の面
                    { float bf0; var lc = EdoBuild.RB(lid).center; int eL = LidEdge(new Vector2(lc.x, lc.z)); float pl = EdoBuild.PullAlongInside(new List<GameObject> { lid }, Poly, -OutNormal(eL), 0.30f, out bf0);
                      if (bf0 > 0.001f) { nLidIn++; if (float.IsNaN(pl)) lidOutLeft = Mathf.Max(lidOutLeft, bf0); } }   // 蓋石は区画の線を越えない【硬: 区域】
                    if (!float.IsNaN(sillG) && inGate(sc)) sillGap = Mathf.Min(sillGap, sillG - EdoBuild.RB(lid).max.y);
                }
            }
            foreach (var g in rep.covered) { float lt = float.MinValue; var gb = EdoBuild.RB(g); foreach (var l in lids) { var lb = EdoBuild.RB(l); if (lb.Intersects(gb)) lt = Mathf.Max(lt, lb.max.y); } if (lt > float.MinValue) _mizoCoverTop[g] = lt; }
            _secMizoProf[nm] = rep.prof; _secMizoLine[nm] = line;
            float refDev = 0f; string refAt2 = "-"; int curE = eF;
            foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(S(Get(sec, "bottomRef")) ?? "", @"(?:辺\s*(\d+)\s*)?s\s*([0-9.]+)\s*(?:敷き\s*)?([0-9]+\.[0-9]+)"))
            {
                if (m.Groups[1].Success) curE = int.Parse(m.Groups[1].Value);
                float sr = arcOf(At(curE, float.Parse(m.Groups[2].Value, inv))); if (sr < 0.01f || sr > rep.length - 0.01f) continue;
                float dv = rep.prof.At(sr) - float.Parse(m.Groups[3].Value, inv); if (Mathf.Abs(dv) > Mathf.Abs(refDev)) { refDev = dv; refAt2 = "辺" + curE + " s" + m.Groups[2].Value; }
            }
            float fallMin = rep.fallMin;
            sb.AppendLine("  台の前の溝 " + nm + "(辺" + eF + " s" + sF.ToString("0.##", inv) + " → 辺" + eT + " s" + sEnd.ToString("0.##", inv) + "): 石組の溝 型A を天端の線で " + rep.made.Count + " 駒・" + rep.length.ToString("F1", inv) + "m" + headNote
                        + "・天端 − 造成の面 " + rep.devLo.ToString("+0.000;-0.000", inv) + "〜" + rep.devHi.ToString("+0.000;-0.000", inv) + (rep.devLo >= -0.02f - 1e-3f && rep.devHi <= 0.02f + 1e-3f ? " ⭕(±0.02)" : " ⚠(±0.02 の外 ── 帯の地面を天端へ合わせる)")
                        + "・隣の天端の段差 最大 " + rep.stepMax.ToString("F3", inv) + (rep.stepMax <= 0.01f + 1e-4f ? " ⭕" : " ⛔ @" + rep.stepAt) + (rep.coverSpans.Count > 0 ? "(蓋の縁 " + rep.stepCover.ToString("F3", inv) + " は蓋の下)" : "")
                        + "・底 " + rep.botHead.ToString("F3", inv) + "→" + rep.botTail.ToString("F3", inv) + (rep.nRise == 0 ? "(一方向に下る ⭕)" : "(⛔ 上る所 " + rep.nRise + "・最大 " + rep.riseMax.ToString("F3", inv) + ")")
                        + (float.IsNaN(spec.headBottomMax) ? "" : "・頭の底 − 上流の尻の底 " + rep.headOver.ToString("+0.000;-0.000", inv) + (rep.headOver <= 1e-3f ? " ⭕" : " ⛔"))
                        + "・深さ " + rep.depthLo.ToString("F3", inv) + "〜" + rep.depthHi.ToString("F3", inv) + (rep.depthLo >= depthMin - 1e-3f ? " ⭕(≥" + depthMin.ToString("F2", inv) + ")" : " ⛔") + "(狙い " + depthTgt.ToString("F2", inv) + "【柔】)"
                        + (float.IsNaN(fallSoft) || fallMin == float.MaxValue ? "" : "・底の下りの最小 1/" + (fallMin > 1e-4f ? (1f / fallMin).ToString("0", inv) : "∞") + (fallMin >= fallSoft - 1e-4f ? " ⭕" : " △(柔 1/" + (1f / fallSoft).ToString("0", inv) + "・天端を地表に合わせるのが先)"))
                        + "・目安 bottomRef との差 最大 " + refDev.ToString("+0.000;-0.000", inv) + " @" + refAt2
                        + (rep.coverSpans.Count > 0 ? "・門の口の暗渠 蓋石 " + nLid + " 枚(線の内へ寄せた " + nLidIn + (lidOutLeft > 0.001f ? "・⛔ 寄せても区画の外 " + lidOutLeft.ToString("F3", inv) : "") + "・蓋の下の駒 " + rep.covered.Count + (rep.nAutoCover > 0 ? "・うち版で届かず蓋 " + rep.nAutoCover : "") + ")・蓋の天端 − 造成の面 " + (nLid > 0 ? lidLo.ToString("+0.000;-0.000", inv) + "〜" + lidHi.ToString("+0.000;-0.000", inv) + (lidLo >= -0.02f - 1e-3f && lidHi <= 0.02f + 1e-3f ? " ⭕" : " ⚠") : "-") + (float.IsNaN(sillG) || nLid == 0 ? "" : "・敷居 − 蓋 最小 " + sillGap.ToString("F3", inv) + (sillGap >= 0.02f - 0.005f ? " ⭕" : " ⛔")) : "")
                        + (rep.nDeep > 0 ? "・⛔ 版で届かない駒 " + rep.nDeep : "") + (rep.nNoCurb > 0 ? "・⚠ 縁石の天端が測れない駒 " + rep.nNoCurb : "") + outNote);
        }
        return sb.ToString();
    }
    /// <summary>点に最も近い区画の辺(蓋石を線の内へ寄せる向き)。</summary>
    static int LidEdge(Vector2 q)
    {
        int best = 0; float bd2 = float.MaxValue; var P = Poly;
        for (int e = 0; e < P.Length; e++) { Vector2 a = P[e], b = P[(e + 1) % P.Length], ab = b - a; float t = Mathf.Clamp01(Vector2.Dot(q - a, ab) / Mathf.Max(1e-8f, ab.sqrMagnitude)); float d = (a + ab * t - q).sqrMagnitude; if (d < bd2) { bd2 = d; best = e; } }
        return best;
    }
    /// <summary>この巡に据えた台の前の溝(名 → 線・底)と吐き口 ── 背の路地の暗渠(PlaceSeRojiAnkyo)が落とし先の底と縁石を測る。</summary>
    static readonly Dictionary<string, Vector3> _secMizoTail = new Dictionary<string, Vector3>();
    static readonly Dictionary<string, EdoBuild.MizoProfile> _secMizoProf = new Dictionary<string, EdoBuild.MizoProfile>();
    static readonly Dictionary<string, List<Vector2>> _secMizoLine = new Dictionary<string, List<Vector2>>();
    static readonly Dictionary<string, GameObject> _secMizoOutlet = new Dictionary<string, GameObject>();
    /// <summary>天端の線で据えた前の下水溝(D_N40_Mae ほか)── 台の前の溝の頭が尻の天端と底を続ける。</summary>
    static readonly Dictionary<string, EdoBuild.MizoTopRep> _drainTopRep = new Dictionary<string, EdoBuild.MizoTopRep>();
    /// <summary>蓋を掛けた溝の駒 → 蓋の天端(Stage3d が溝の両脇の地面を蓋の天端へ合わせる)。</summary>
    static readonly Dictionary<GameObject, float> _mizoCoverTop = new Dictionary<GameObject, float>();

    /// <summary>辺ごとの練塀の内面の線(実メッシュ ── 練塀・隅の駒・留め柱の頂点を一番近い辺へ)。⟶ 辺 → 線。</summary>
    static Dictionary<int, EdoBuild.FootLine> FootLinesOn(List<int> edges)
    {
        int n = Poly.Length; var byE = new Dictionary<int, EdoBuild.FootLine>(); var lines = new List<EdoBuild.FootLine>();
        System.Func<int, float, float> seatOf = (e, sv) => { foreach (var r in Runs) if (r.Dobei && r.edge == e && sv >= r.s0 - 0.5f && sv <= r.s1 + 0.5f) return r.SeatAt(Mathf.Clamp(sv, r.s0, r.s1)); return float.NaN; };
        foreach (int e in edges) { Vector2 ea = EdgePt(e, 0f); var L = new EdoBuild.FootLine { name = "辺" + e, a = ea, ax = (EdgePt(e, 1f) - ea).normalized, inw = -OutNormal(e), len = EdgeLen(e) }; int ee = e; L.seatAt = sv => seatOf(ee, sv); lines.Add(L); byE[e] = L; }
        var pcs = new List<GameObject>();
        foreach (Transform c in Group("Kakoi"))
        {
            if (!c.gameObject.activeInHierarchy) continue; string nm = c.name; bool take = false;
            foreach (var r in Runs) if (r.Dobei && edges.Contains(r.edge) && nm.StartsWith(r.name + "_")) { take = true; break; }
            int v; if (!take && nm.StartsWith("Kado_P") && int.TryParse(nm.Substring(6), out v) && (edges.Contains((v - 1 + n) % n) || edges.Contains(v % n))) take = true;
            if (take) pcs.Add(c.gameObject);
        }
        EdoBuild.MeasureFootLines(lines, pcs);
        return byE;
    }
    /// <summary>二本の線(点 + 向き)の交点。平行なら NaN。</summary>
    static System.Text.RegularExpressions.Match RXm(string t, string pat) { return System.Text.RegularExpressions.Regex.Match(t ?? "", pat); }
    static Vector2 LineX(Vector2 a0, Vector2 d0, Vector2 a1, Vector2 d1) { float den = d0.x * d1.y - d0.y * d1.x; if (Mathf.Abs(den) < 1e-5f) return new Vector2(float.NaN, float.NaN); Vector2 w = a1 - a0; float t = (w.x * d1.y - w.y * d1.x) / den; return a0 + d0 * t; }

    /// <summary>**南の練塀の内の溝 D_MinamiHei**(指図 drains[D_MinamiHei] の segs・第115巡 ── 普請方の設計 2026-10-12)。
    /// main: 練塀の内の足元の線(内面 + off)の一番高い所(P9 の尾根)から辺を東へ。型は地表の 2m 平均の勾配で引く(1/20 以下 = 型A_Ago・超 = 型H の段落ち)── 型の境は実地形から。
    ///   型A_Ago は天端の線で据える(EdoBuild.LayMizoOnTopLine・頭の底 ≤ 上流の尻の底)、型H は EdoBuild.LayDanOchi(1段 ≤ riseMax・段数 = ceil(落差 / riseMax))。最後の型H は小段の溝の頭へ一直線。
    /// kodan: 小段の溝(内面 + off)を辺に沿って東へ、TW_Higashi_Minami の天端が終わる所まで(駒の実メッシュの天端で測る)。east: そこから型H で角の庭の溝の頭(線が庭の面 + 0.10 以下になる所)へ。
    /// niwa: 型A_Ago D(欄)で一番近い背の路地の床へ。west: 桝 G0 を P12 の窪み(足元の線の最も低い所・長屋の妻から離れ ≥ 欄)に据え、石樋の暗渠(焼かない)の口の底を本線の型H の平らな駒と突き合わせる。
    /// ⛔ 座標を書かない(線は練塀の実メッシュから)。当たる先: 塀の内の足元の溝(土井 D11 と同じ組み ── 型A_Ago + 型H + 桝 + 暗渠)。</summary>
    static string PlaceMinamiHei()
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var dr = DrainByName("D_MinamiHei"); if (dr == null) return "";
        var sb = new System.Text.StringBuilder("  南の練塀の内の溝 D_MinamiHei(drains.segs):\n"); var grp = Group("MinamiHeiMizo"); Clear(grp);
        { var ft = EdoBuild.FineTerrain(); if (ft != null) EdoBuild.SkinWorldMaterial(ft); }   // 段落ちの浅い版の地際の板(材 _World)を細かい地形へ結わえる(第117巡)
        var segs = new Dictionary<string, Dictionary<string, object>>(); foreach (var o in A(Get(dr, "segs")) ?? new List<object>()) { var g = O(o); if (g != null) segs[S(Get(g, "seg"))] = g; }
        System.Func<string, string, string> T_ = (sg, k) => segs.ContainsKey(sg) ? S(Get(segs[sg], k)) ?? "" : "";
        var mOffM = RXm(T_("main", "line"), @"内面\s*\+\s*([0-9.]+)"); var mOffK = RXm(T_("yuka", "line"), @"内面\s*\+\s*([0-9.]+)"); /* 床の溝(施主裁定 2026-10-12 案A ── 小段の溝 kodan/east をやめ一本へ・第119巡) */ var mKata = RXm(T_("main", "kataRule"), @"([0-9.]+)\s*m\s*平均.*?1\s*/\s*([0-9.]+)");
        var mRise = RXm(string.Join(" ", (A(Get(dr, "hardAdd")) ?? new List<object>()).ConvertAll(x => S(x)).ToArray()), @"1段\s*≤\s*([0-9.]+)");
        var mDepA = RXm(T_("main", "kataRule"), @"深さ狙い\s*([0-9.]+)"); var mDepMin = RXm(S(Get(dr, "hard")) ?? "", @"深さ\s*≥\s*([0-9.]+)");
        if (!mOffM.Success || !mOffK.Success || !mKata.Success || !mRise.Success || !mDepMin.Success) return sb + "    ★ segs の main/yuka の芯(内面 + d)・型の境(2m 平均 1/n)・1段 ≤ ・深さ ≥ が読めない ── 建てない\n";
        float offM = float.Parse(mOffM.Groups[1].Value, inv), offK = float.Parse(mOffK.Groups[1].Value, inv), win = float.Parse(mKata.Groups[1].Value, inv), gH = 1f / float.Parse(mKata.Groups[2].Value, inv);
        float riseMax = float.Parse(mRise.Groups[1].Value, inv), depMin = float.Parse(mDepMin.Groups[1].Value, inv), depT = mDepA.Success ? float.Parse(mDepA.Groups[1].Value, inv) : 0.15f;
        int n = Poly.Length;
        // 辺: P12(辺11 の終わり)〜 P3(辺3 の始め)── 本線は辺9 の頭から辺6、小段は辺5〜4
        var edges = new List<int>(); for (int e = 2; e <= 11; e++) edges.Add(e);   // 辺2 は yuka の尻(P3 の角の線)を引くため(第119巡)
        var FL = FootLinesOn(edges);
        //   ⭐ 足の内の縁が測れない辺(駒の足が座の帯の外 ── 第125巡 辺8)は、測れた辺の最も奥の縁で引く(溝を足へ寄せない側へ)
        float dInMax = float.NaN; foreach (var kv in FL) if (kv.Value.nPts > 0) dInMax = float.IsNaN(dInMax) ? kv.Value.dIn : Mathf.Max(dInMax, kv.Value.dIn);
        var noFoot = new List<string>(); foreach (var kv in FL) if (kv.Value.nPts == 0) noFoot.Add("辺" + kv.Key);
        if (noFoot.Count > 0) sb.Append("    ⚠ 足の内の縁が測れない " + string.Join("・", noFoot.ToArray()) + " ── 測れた辺の最も奥 " + (float.IsNaN(dInMax) ? "(無し 0.9)" : dInMax.ToString("F3", inv)) + " で引く\n");
        System.Func<int, float, float, Vector2> At = (e, s, off) => { var L = FL[e]; float d = (L.nPts > 0 ? L.dIn : (float.IsNaN(dInMax) ? 0.9f : dInMax)) + off; return L.a + L.ax * s + L.inw * d; };
        System.Func<int, float, Vector2> Corner = (v, off) => { int e0 = (v - 1 + n) % n, e1 = v % n; var X = LineX(At(e0, 0f, off), FL[e0].ax, At(e1, 0f, off), FL[e1].ax); return float.IsNaN(X.x) ? At(e1, 0f, off) : X; };
        System.Func<float, float, float> G = (x, z) => EdoBuild.Ground(x, z);
        var versions = new List<string>(); for (float d = 0.10f; d <= 0.301f; d += 0.05f) versions.Add(EdoAssets.Own.DoiMizo("A", d, ago: true));
        float halfW; { float xa, xb, ct; halfW = EdoBuild.MizoCurbTop(versions[0], 1, out xa, out xb, out ct) ? Mathf.Max(Mathf.Abs(xa), Mathf.Abs(xb)) : 0.35f; }
        //   ⭐ 溝の線を塀の足の内の縁から(const.heiLine.innerDitch【硬】「溝の外の縁 = 足の内の縁 + c 以上」・第125巡)── 芯の離れ = 狙い(segs の「内面 + d」)と
        //   駒の外の縁(地際の板を含む半幅)+ c の大きい方(EdoBuild.DitchCoreOff)。幅・深さ・勾配・落とし先は欄のまま・線だけ内へ。
        {
            var idt = S(Get(O(Get(O(D["const"]), "heiLine")), "innerDitch")) ?? ""; var mC = RXm(idt, @"足の内の縁\s*\+\s*([0-9.]+)\s*以上");
            if (!mC.Success) sb.Append("    ★ const.heiLine.innerDitch の「足の内の縁 + c 以上」が読めない ── 溝は欄の離れのまま\n");
            else
            {
                float clr0 = float.Parse(mC.Groups[1].Value, inv), hM, hK, hG;
                var mainP = new List<string>(versions); foreach (var rr in new[] { 0f, 0.125f, riseMax }) mainP.Add(EdoAssets.Own.DoiDanOchi(rr, depT));
                float offM2 = EdoBuild.DitchCoreOff(offM, clr0, mainP, out hM), offK2 = EdoBuild.DitchCoreOff(offK, clr0, versions, out hK);
                offM2 = EdoBuild.DitchCoreOff(offM2, clr0, new[] { EdoAssets.Own.DoiMasu("G0") }, out hG);
                sb.Append("    溝の線を足の内の縁から(innerDitch・外の縁 ≥ 足の内の縁 + " + clr0.ToString("0.00", inv) + "): main・west・桝 芯 内面 +" + offM.ToString("0.00", inv) + " → +" + offM2.ToString("0.00", inv)
                        + "(駒の外の半幅 " + hM.ToString("0.00", inv) + "・桝 " + hG.ToString("0.00", inv) + ")・yuka +" + offK.ToString("0.00", inv) + " → +" + offK2.ToString("0.00", inv) + "(半幅 " + hK.ToString("0.00", inv) + ")"
                        + " ── 床が狭まる量 main " + (offM2 - offM).ToString("0.00", inv) + "・yuka " + (offK2 - offK).ToString("0.00", inv) + (offM2 - offM > 0.10f || offK2 - offK > 0.10f ? " ⚠ 狙い ±0.10 の外" : "") + "\n");
                offM = offM2; offK = offK2;
            }
        }
        System.Func<Vector2, Vector2> outAt = q => { int be = 6; float bd = float.MaxValue; foreach (var kv in FL) { var L = kv.Value; float s = Mathf.Clamp(Vector2.Dot(q - L.a, L.ax), 0f, L.len); float d = Vector2.Distance(q, L.a + L.ax * s); if (d < bd) { bd = d; be = kv.Key; } } return OutNormal(be); };
        // ---- main の線: 尾根(辺9 の頭 6m と辺8 の足元の線の地表の最高)→ P9 → P8 → P7 → 辺6 → P6
        Vector2 ridge = At(8, EdgeLen(8), offM); float gR = float.MinValue; int eR = 8; float sR = EdgeLen(8);
        foreach (int e in new[] { 8, 9 }) { float L = EdgeLen(e), sA = e == 9 ? 0f : 0.5f, sB = e == 9 ? Mathf.Min(6f, L) : L - 0.25f; for (float s = sA; s <= sB + 1e-3f; s += 0.25f) { var q = At(e, s, offM); float g = G(q.x, q.y); if (g > gR) { gR = g; ridge = q; eR = e; sR = s; } } }
        var main = new List<Vector2> { ridge }; if (eR == 9) main.Add(Corner(9, offM)); main.Add(Corner(8, offM)); main.Add(Corner(7, offM));
        // 尻: tail「最後の型H は辺6 の s≈a から P6 で小段の溝の頭へ一直線」── a は欄の見当(P)。小段の頭 = P6 の小段の線
        var mTail = RXm(T_("main", "tail"), @"辺6\s*の\s*s\s*≈\s*([0-9.]+)"); float sTail = mTail.Success ? float.Parse(mTail.Groups[1].Value, inv) : 4.5f;
        main.Add(At(6, sTail, offM));
        //   尻の型H(段落ち・地際の板の半幅が型A より広い)が終わる床の溝の頭は、本線の離れ以上で引く(innerDitch【硬】・第125巡: 内面 +offK で引くと tail の板が足の内の縁に 0.26 掛かった)
        Vector2 kHead = Corner(6, Mathf.Max(offK, offM));
        // ---- 区間を型で割る(2m 平均の勾配)
        float Lm = EdoBuild.PolylineLength(main); var Sx = new List<float>(); var Gx = new List<float>(); for (float s = 0f; s <= Lm + 1e-3f; s += 0.25f) { Vector2 dd; var q = EdoBuild.PointAt(main, s, out dd); Sx.Add(s); Gx.Add(G(q.x, q.y)); }
        System.Func<float, float> Gs = ss => { int i = Mathf.Clamp(Mathf.RoundToInt(ss / 0.25f), 0, Gx.Count - 1); return Gx[i]; };
        var isH = new List<bool>(); for (int i = 0; i < Sx.Count; i++) { float a = Mathf.Max(0f, Sx[i] - 0.5f * win), b = Mathf.Min(Lm, Sx[i] + 0.5f * win); isH.Add(b - a > 0.3f && Mathf.Abs(Gs(b) - Gs(a)) / (b - a) > gH); }
        // 区間(上流 → 下流): [s0, s1, H?]・1.0m 未満の区間は前へ吸わせる・角(折れ)で型H を割る
        var cuts = new List<Vector3>(); { float a = 0f; bool h = isH[0]; for (int i = 1; i < Sx.Count; i++) if (isH[i] != h) { cuts.Add(new Vector3(a, Sx[i], h ? 1 : 0)); a = Sx[i]; h = isH[i]; } cuts.Add(new Vector3(a, Lm, h ? 1 : 0)); }
        for (int k = cuts.Count - 1; k >= 1; k--) if (cuts[k].y - cuts[k].x < 1.0f) { cuts[k - 1] = new Vector3(cuts[k - 1].x, cuts[k].y, cuts[k - 1].z); cuts.RemoveAt(k); }
        if (cuts.Count >= 2 && cuts[0].y - cuts[0].x < 1.0f) { cuts[1] = new Vector3(cuts[0].x, cuts[1].y, cuts[1].z); cuts.RemoveAt(0); }
        for (int k = 1; k < cuts.Count; k++) if (cuts[k].z == cuts[k - 1].z) { cuts[k - 1] = new Vector3(cuts[k - 1].x, cuts[k].y, cuts[k].z); cuts.RemoveAt(k); k--; }
        // 型H は折れの点で割る(段落ちは直線)
        var corners = new List<float>(); { float acc = 0f; for (int i = 1; i + 1 < main.Count; i++) { acc += Vector2.Distance(main[i - 1], main[i]); corners.Add(acc); } }
        var segList = new List<Vector3>(); foreach (var c in cuts) { if (c.z < 0.5f) { segList.Add(c); continue; } float a = c.x; foreach (var cs in corners) if (cs > a + 0.3f && cs < c.y - 0.3f) { segList.Add(new Vector3(a, cs, 1)); a = cs; } segList.Add(new Vector3(a, c.y, 1)); }
        System.Func<float, float, List<Vector2>> Sub = (a, b) => { var l = new List<Vector2>(); Vector2 dd; l.Add(EdoBuild.PointAt(main, a, out dd)); float acc = 0f; for (int i = 1; i < main.Count; i++) { acc += Vector2.Distance(main[i - 1], main[i]); if (acc > a + 1e-3f && acc < b - 1e-3f) l.Add(main[i]); } l.Add(EdoBuild.PointAt(main, b, out dd)); return l; };
        float bPrev = float.NaN; var segTxt = new List<string>(); var flats = new List<GameObject>(); bool okAll = true; int nA = 0, nH = 0; float stepMaxA = 0f; int riseA = 0;
        bool lastH = false; float dDeep; { var md = EdoBuild.MizoPieceOf(versions[versions.Count - 1]); float xa0, xb0, c0; dDeep = (md.ok && EdoBuild.MizoCurbTop(versions[versions.Count - 1], 1, out xa0, out xb0, out c0) ? c0 : md.top) - md.floor; }
        // onLine: 地表を溝の芯の線の上で引く(小段の溝 ── 外へ 0.30 の点は野面石の天端の前の縁を越えて床を読み、小段より 0.66〜1.06 低く据わった・第117巡)
        System.Action<string, List<Vector2>, float, bool> layA = (nm, line, headBotMax, onLine) =>
        {
            var spec = new EdoBuild.MizoTopSpec { name = nm, line = line, surfaceAt = G, outAt = outAt, halfW = halfW, surfaceOff = 0.30f, surfaceOnLine = onLine, versions = versions, depthMin = depMin, depthTarget = depT, headBottomMax = headBotMax };
            // ⭐ 型H の後の型A(第116巡): 型H の尻の底は 地表 − 壁の丈(0.49)で、型A の最も深い版でも天端が地表に届かない ⇒ 天端の線の頭を「上流の底 + 最も深い版」へ下げ、地表が下るまで沈めて続ける(底の一方向の下りが先【硬】)
            if (lastH && !float.IsNaN(headBotMax)) { var q0 = line[0]; if (G(q0.x, q0.y) - headBotMax > dDeep - 0.005f) spec.headTop = headBotMax + dDeep - 0.005f; }
            var rep = EdoBuild.LayMizoOnTopLine(grp, nm, spec); nA += rep.made.Count; stepMaxA = Mathf.Max(stepMaxA, rep.stepMax); riseA += rep.nRise;
            if (rep.made.Count == 0) { okAll = false; segTxt.Add(nm + " 型A ⛔ 据わらない(" + string.Join("・", rep.notes.ToArray()) + ")"); return; }
            segTxt.Add(nm + " 型A_Ago " + rep.length.ToString("F1", inv) + "m 駒 " + rep.made.Count + "・底 " + rep.botHead.ToString("F2", inv) + "→" + rep.botTail.ToString("F2", inv) + "・深さ " + rep.depthLo.ToString("F2", inv) + "〜" + rep.depthHi.ToString("F2", inv) + "・天端−地表 " + rep.devLo.ToString("+0.00;-0.00", inv) + "〜" + rep.devHi.ToString("+0.00;-0.00", inv) + "・隣の段差 " + rep.stepMax.ToString("F3", inv) + (rep.nRise > 0 ? "・⛔ 底の上り " + rep.nRise : "・底は下流へ ⭕"));
            bPrev = rep.botTail; lastH = false;
        };
        // ⭐ 型H は地表なりに埋める(第116巡・施主「溝の上面が地表の面と一致しているべき」)── 側の天端(底 + 壁の丈)を地表へ、段は地表が下った所に置く(EdoBuild.LayDanOchiOnGround)。
        //   ⛔ 踏面を等分して落とさない(第115巡: 側の天端が地表から 0.3〜0.5 立った)。尻の底の下限 tailMin は落とし先の頭の底(east → 庭の溝 12.25)。
        //   ⭐ 壁の浅い版(Own.DoiDanOchi(rise, wallTop)・第117巡): 側の壁の丈 = 型A の深さの狙い ⇒ 型H の尻の底 = 地表 − 狙い で、続く型A は沈めずに天端 = 地表で続く(素の H は 0.49 で −0.66 沈んだ)
        float wallTopH = depT; System.Func<float, string> danOf = r => EdoAssets.Own.DoiDanOchi(r, wallTopH);
        System.Action<string, Vector2, Vector2, float> layH = (nm, p0, p1, tailMin) =>
        {
            float wallH0 = EdoBuild.MizoWallRise(danOf(0f)); if (float.IsNaN(wallH0)) wallH0 = 0.49f;   // 板を除いた壁の石の天端 − 底(第117巡)
            float head = float.IsNaN(bPrev) ? G(p0.x, p0.y) - wallH0 : bPrev;
            // 段を一つも置けない落差(頭の底 − 尻の狙い < 0.125)は型H にしない ── 平らな駒だけだと側の天端が地表から 0.5 立つ(第116巡の 1 回目: east 0.5m 段 0)⇒ 型A
            { float tW = G(p1.x, p1.y) - wallH0; if (!float.IsNaN(tailMin)) tW = Mathf.Max(tW, tailMin); if (head - tW < 0.125f) { segTxt.Add(nm + " 型H: 段を置く落差が無い(" + (head - tW).ToString("F2", inv) + ")── 型A へ"); layA(nm, new List<Vector2> { p0, p1 }, bPrev, false); return; } }
            var R = EdoBuild.LayDanOchiOnGround(grp, nm, p0, p1, head, q => G(q.x, q.y), tailMin, riseMax, danOf);
            if (!R.ok) { okAll = false; segTxt.Add(nm + " 型H ⛔ " + R.hard); return; }
            nH += R.pieces.Count; foreach (var g in R.pieces) if (g.name.Contains("_F")) flats.Add(g);
            var rs = new List<string>(); foreach (var r in R.rises) rs.Add(r.ToString("F2", inv));
            segTxt.Add(nm + " 型H(地表なり)" + R.length.ToString("F1", inv) + "m 段 " + R.steps + "(1段 " + string.Join("/", rs.ToArray()) + ")・底 " + head.ToString("F2", inv) + "→" + R.tailY.ToString("F2", inv) + "・側の天端 − 地表(据えた直後) " + R.rimLo.ToString("+0.00;-0.00", inv) + "〜" + R.rimHi.ToString("+0.00;-0.00", inv) + (R.soft != "" ? "・⚠ " + R.soft : ""));
            bPrev = R.tailY; lastH = true;
        };
        for (int k = 0; k < segList.Count; k++)
        {
            var c = segList[k]; string nm = "D_MinamiHei_m" + k.ToString("00");
            if (c.z < 0.5f) layA(nm, Sub(c.x, c.y), bPrev, false);
            else { Vector2 dd; var p0 = EdoBuild.PointAt(main, c.x, out dd); var p1 = EdoBuild.PointAt(main, c.y, out dd); layH(nm, p0, p1, float.NaN); }
            if (!okAll) break;
        }
        // 尻の型H: 辺6 の s≈a → P6 の小段の溝の頭
        float kHeadG = G(kHead.x, kHead.y);
        if (okAll) layH("D_MinamiHei_tail", main[main.Count - 1], kHead, float.NaN);
        // ---- yuka(施主裁定 2026-10-12 案A・第119巡): P6 → 辺5 → 辺4 → 辺3 を東へ、練塀の内面 + offK の床の溝一本。尻 = 線の上の地表が角の庭の面 + 0.10 以下になる所
        //   (旧い east と同じ探し方 ── 庭の溝の頭)。天端 = 線の上の地表(LayMizoOnTopLine・surfaceOnLine)・底は上流の尻(bPrev)から下流へ一方向【硬】。
        //   ⛔ TW_Higashi_Minami の駒を読まない(石垣の見え面の足は床の外の縁 ── 溝は練塀の側)。当たる先: 塀の内の足元を床の溝一本で流す所(岡部 辺4・5)
        if (okAll)
        {
            float nyMin = SessionState.GetFloat("Okabe.niwa.yMin", 12.30f);
            var yl = new List<Vector2> { kHead, Corner(5, offK) };
            // 尻 = 辺4 の終わり(P4 = heiFootSpec.floor45 の床の出口 ── 指図 yuka.levels「→ 12.25(出口)」)。⛔ 地表の高さで探さない(床が出口まで 12.35〜12.40 で、P5 の手前で止まった・第119巡の初回)
            Vector2 nHead = Corner(4, offK); if (float.IsNaN(nHead.x)) nHead = At(4, 0f, offK); bool found = true;
            yl.Add(nHead);
            layA("D_MinamiHei_yuka", yl, bPrev, true);
            segTxt.Add("yuka の尻(庭の溝の頭)" + (found ? "= 辺4 の終わり(floor45 の床の出口)" : "") + " (" + nHead.x.ToString("F2", inv) + "," + nHead.y.ToString("F2", inv) + ")");
            var mNiwaB = RXm(T_("niwa", "levels"), @"頭の底\s*([0-9.]+)"); float niwaHeadB = mNiwaB.Success ? float.Parse(mNiwaB.Groups[1].Value, inv) : nyMin - 0.05f;
            // ---- niwa: 庭の溝の頭 → 一番近い背の路地の床
            var spl = SeRoji(); Vector2 outP = new Vector2(float.NaN, float.NaN); float bdO = float.MaxValue;
            if (spl != null && spl.ok) for (float dx = -6f; dx <= 6f; dx += 0.25f) for (float dz = -6f; dz <= 6f; dz += 0.25f) { var q = nHead + new Vector2(dx, dz); if (float.IsNaN(spl.At(q))) continue; float d = Vector2.Distance(q, nHead); if (d < bdO) { bdO = d; outP = q; } }
            float dN = segs.ContainsKey("niwa") && Has(segs["niwa"], "depth") ? F(segs["niwa"]["depth"]) : 0.10f;
            if (okAll && !float.IsNaN(outP.x))
            {
                var vN = new List<string> { EdoAssets.Own.DoiMizo("A", dN, ago: true) };
                var spec = new EdoBuild.MizoTopSpec { name = "D_MinamiHei_niwa", line = new List<Vector2> { nHead, outP }, surfaceAt = G, outAt = q => outAt(q), halfW = halfW, surfaceOff = 0.30f, versions = vN, depthMin = depMin, depthTarget = dN, headBottomMax = bPrev };
                { var mTB = RXm(T_("niwa", "levels"), @"吐き口の底\s*([0-9.]+)"); var mdN = EdoBuild.MizoPieceOf(vN[0]); float xa1, xb1, c1; float dpN = (mdN.ok && EdoBuild.MizoCurbTop(vN[0], 1, out xa1, out xb1, out c1) ? c1 : mdN.top) - mdN.floor;
                  if (mNiwaB.Success && mTB.Success && mdN.ok) { float tB = Mathf.Max(float.Parse(mTB.Groups[1].Value, inv), spl.At(outP) + 0.02f);
                      spec.headTop = Mathf.Max(Mathf.Min(niwaHeadB, bPrev), tB + 0.002f) + dpN; spec.tailTop = tB + dpN; } }
                var rep = EdoBuild.LayMizoOnTopLine(grp, "D_MinamiHei_niwa", spec); nA += rep.made.Count;
                float fl = spl.At(outP);
                segTxt.Add("niwa 型A_Ago D" + dN.ToString("F2", inv) + " " + rep.length.ToString("F1", inv) + "m 駒 " + rep.made.Count + "・底 " + rep.botHead.ToString("F2", inv) + "→" + rep.botTail.ToString("F2", inv) + "・吐き口の底 − 路地の床 " + (rep.botTail - fl).ToString("+0.000;-0.000", inv) + (rep.botTail - fl >= 0.02f - 1e-3f ? " ⭕(≥ +0.02)" : " ⛔(< +0.02)") + (rep.nRise > 0 ? "・⛔ 底の上り " + rep.nRise : ""));
            }
            else if (okAll) segTxt.Add("niwa ★ 庭の溝の頭の 6m 内に背の路地の床が無い ── 建てない");
        }
        // ---- west: 桝 G0(P12 の窪み)と石樋の暗渠の口(焼かない)
        {
            var mz = RXm(T_("west", "masu"), @"妻から\s*([0-9.]+)\s*以上"); float clr = mz.Success ? float.Parse(mz.Groups[1].Value, inv) : 0.3f;
            float gLo = float.MaxValue; Vector2 mAt = At(11, EdgeLen(11), offM); float L11 = EdgeLen(11);
            for (float s = 0f; s <= L11 - clr + 1e-3f; s += 0.25f) { var q = At(11, s, offM); float g = G(q.x, q.y); if (g < gLo) { gLo = g; mAt = q; } }
            string mp = EdoAssets.Own.DoiMasu("G0"); float floor, sink;
            // ⭐ 足元の型A(segs.west.line「足元を型A で P12 へ寄せ」・第116巡): 尾根の西の 0.25 先 → 辺の折れ(内面 + offM)→ 桝の外の面。天端の線で据え(EdoBuild.LayMizoOnTopLine)、尻の天端 = 桝の天端(地表)
            string westTxt = "";
            {
                var wl = new List<Vector2> { At(eR, Mathf.Min(EdgeLen(eR), sR + 0.25f), offM) };
                for (int v = eR + 1; v <= 11; v++) wl.Add(Corner(v, offM));
                var mpcW = EdoBuild.MizoPieceOf(mp); float hwM = mpcW.ok ? Mathf.Max(Mathf.Abs(mpcW.xMin), Mathf.Abs(mpcW.xMax)) : 0.27f;
                Vector2 dW = (mAt - wl[wl.Count - 1]).normalized; float dLast = Vector2.Distance(mAt, wl[wl.Count - 1]);
                if (dLast > hwM + 0.3f) wl.Add(mAt - dW * hwM); else wl[wl.Count - 1] = mAt - dW * hwM;
                var spW = new EdoBuild.MizoTopSpec { name = "D_MinamiHei_w", line = wl, surfaceAt = G, outAt = outAt, halfW = halfW, surfaceOff = 0.30f, versions = versions, depthMin = depMin, depthTarget = depT, tailTop = G(mAt.x, mAt.y) };
                var rw = EdoBuild.LayMizoOnTopLine(grp, "D_MinamiHei_w", spW); nA += rw.made.Count;
                westTxt = rw.made.Count == 0 ? "west 足元の型A ⛔ 据わらない(" + string.Join("・", rw.notes.ToArray()) + ")"
                        : "west 足元の型A_Ago " + rw.length.ToString("F1", inv) + "m 駒 " + rw.made.Count + "・底 " + rw.botHead.ToString("F2", inv) + "→" + rw.botTail.ToString("F2", inv) + "・深さ " + rw.depthLo.ToString("F2", inv) + "〜" + rw.depthHi.ToString("F2", inv) + "・天端−地表 " + rw.devLo.ToString("+0.00;-0.00", inv) + "〜" + rw.devHi.ToString("+0.00;-0.00", inv) + "・隣の段差 " + rw.stepMax.ToString("F3", inv) + (rw.nRise > 0 ? "・⛔ 底の上り " + rw.nRise : "・底は下流へ ⭕");
            }
            var masu = EdoBuild.PlaceMasu(grp, "D_MinamiHei_G0", mp, mAt, FL[11].ax * -1f, G(mAt.x, mAt.y), float.MaxValue, out floor, out sink);
            float slopeMin = 0.01f; var mS = RXm(T_("west", "ankyo"), @"1\s*/\s*([0-9.]+)\s*以上"); if (mS.Success) slopeMin = 1f / float.Parse(mS.Groups[1].Value, inv);
            // 暗渠の口 = 本線の型H の平らな駒のうち、底 ≤ 口の底 − 0.05 の最初の物(上流から)
            string day = "★ 暗渠の口を出す型H の平らな駒が無い";
            if (masu != null)
            {
                float mouth = floor + 0.15f; // 桝の口の底 = 底の天端 + 溜め(G0: 口の底 −0.20 / 底の天端 −0.35)
                var mpc = EdoBuild.MizoPieceOf(mp); if (mpc.ok) mouth = floor + 0.15f;
                float acc = 0f; Vector2 prevQ = mAt; var path = new List<Vector2> { mAt }; for (int e = 11; e >= 7; e--) path.Add(Corner(e, offM)); 
                foreach (var g in flats)
                {
                    var p = new Vector2(g.transform.position.x, g.transform.position.z); float Lp = EdoBuild.PolylineLength(path) + EdoBuild.NearestS(main, p, out acc);
                    float bot = EdoBuild.RB(g).min.y; float want = mouth - slopeMin * Lp; float fb = EdoBuild.StepPieceOf(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(g)).ok ? 0f : 0f;
                    float mb = g.transform.position.y; // 平らな駒のピボット = 底の天端
                    if (mb <= want - 0.05f) { day = "口 = " + g.name + "(底 " + mb.ToString("F2", inv) + " ≤ 口の底 " + want.ToString("F2", inv) + " − 0.05 ⭕)・暗渠 約" + Lp.ToString("F1", inv) + "m・1/" + (1f / slopeMin).ToString("F0", inv) + "(焼かない)"; break; }
                }
                segTxt.Add("west 桝 G0 @ 辺11 の足元の線の最も低い所(地表 " + gLo.ToString("F2", inv) + ")・底の天端 " + floor.ToString("F2", inv) + "・桝の口の底 " + mouth.ToString("F2", inv) + "・" + day); segTxt.Add(westTxt);
            }
            else segTxt.Add("west ★ 桝 G0 が据わらない(" + mp + ")");
        }
        sb.AppendLine("    尾根 " + (eR == 9 ? "辺9" : "辺8") + " s" + sR.ToString("F2", inv) + "(地表 " + gR.ToString("F2", inv) + ")・型の境は地表の " + win.ToString("0", inv) + "m 平均 1/" + (1f / gH).ToString("F0", inv) + "・駒 型A " + nA + "・型H " + nH + "・隣の天端の段差(型A) 最大 " + stepMaxA.ToString("F3", inv) + (stepMaxA <= 0.01f + 1e-4f ? " ⭕" : " ⛔"));
        foreach (var t in segTxt) sb.AppendLine("    " + t);
        return sb.ToString();
    }
    /// <summary>**背の路地の暗渠**(指図 drains[D_SeRoji].make ── flow・masu・kuchi・toi・at・table・order・EDO-0502 第109巡)。
    /// 置き方(oki-kata の4手): ① 固定側 = 長屋の背(SeRojiPlan の実メッシュの背)・台の前の溝(PlaceMizoSections が据えた駒)・台の石垣(Ishigaki の駒)。
    /// ② 桝(G0 / G1)= 表の行の辺・s(at の「北へ約 x ずらす」を足す)で、**外の面を長屋の背の面へ触れて**(背 + 外の半幅 + 0.005)・+Z(口)を区画の外へ・
    ///    縁 = 路地の床(SeRojiPlan.At)−0.01(masu「床 −0.00〜−0.02」)── G1 は焼いた天端 +0.05 の分を沈める。外の半幅は石の実メッシュ(縁の土の皮の輪より下)。
    /// ③ 吐口(型M・DoiAnkyoKuchi)= 同じ s で**台の石垣の見え面に触れて**(口の高さの帯で石垣の駒の実頂点の最も外)・+Z を区画の外へ・
    ///    口の底 = max(落とし先の溝の底 + 0.05【硬】, 溝の内の縁石の天端 + 0.02【柔】)。④ 石樋は埋めて焼かない(toi)── 桝の口の底 > 吐口の口の底【硬: 一方向に下る】と勾配【柔 1/100〜1/4】を刷る。
    /// 当たる先: 長屋の背の路地を暗渠で前の溝へ落とす邸(岡部 辺40・41)。同じ型(桝 → 石樋 → 型M の吐口)は背に路地を負う外周の長屋すべて。</summary>
    static string PlaceSeRojiAnkyo()
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var root = GameObject.Find(GN); if (root == null) return "";
        var grp = Group("SeRojiAnkyo"); Clear(grp);
        Dictionary<string, object> dr = null; foreach (var o in A(Get(D, "drains")) ?? new List<object>()) { var q = O(o); if (q != null && S(Get(q, "name")) == "D_SeRoji") dr = q; }
        var mk = O(Get(dr, "make")); if (mk == null) return "";
        var sr = SeRoji(); if (sr == null || !sr.ok) return "  ★ 背の路地の暗渠 D_SeRoji: 背の路地が解けない ── 置かない\n";
        string table = S(Get(mk, "table")) ?? "", masuT = S(Get(mk, "masu")) ?? "", atT = S(Get(mk, "at")) ?? "", kuchiT = S(Get(mk, "kuchi")) ?? "", toiT = S(Get(mk, "toi")) ?? "";
        var mSink = System.Text.RegularExpressions.Regex.Match(masuT, @"G1\s*は.*?床\s*[−-]\s*([0-9.]+)\s*に沈める");
        var mShift = System.Text.RegularExpressions.Regex.Match(atT, @"s\s*([0-9.]+)\s*は.*?暗渠の芯は北へ約\s*([0-9.]+)\s*ずらす");
        var mKu = System.Text.RegularExpressions.Regex.Match(kuchiT, @"溝の底\s*\+\s*([0-9.]+)\s*以上.*?縁石の天端\s*\+\s*([0-9.]+)\s*以上");
        var mTo = System.Text.RegularExpressions.Regex.Match(toiT, @"勾配\s*1/(\d+)\s*〜\s*1/(\d+)");
        if (!mSink.Success || !mKu.Success) return "  ★ 背の路地の暗渠 D_SeRoji: make.masu の沈め / make.kuchi の口の底が読めない ── 置かない\n";
        float sinkG1 = float.Parse(mSink.Groups[1].Value, inv), kuOverBot = float.Parse(mKu.Groups[1].Value, inv), kuOverCurb = float.Parse(mKu.Groups[2].Value, inv);
        float gMin = mTo.Success ? 1f / float.Parse(mTo.Groups[1].Value, inv) : float.NaN, gMax = mTo.Success ? 1f / float.Parse(mTo.Groups[2].Value, inv) : float.NaN;
        string kP = EdoAssets.Own.DoiAnkyoKuchi; var km = EdoBuild.MizoPieceOf(kP); if (!km.ok) return "  ★ 背の路地の暗渠: 型M の吐口が測れない ── 置かない\n";
        var ig = root.transform.Find("Ishigaki"); var smz = root.transform.Find("SecMizo");
        int n = 0, bad = 0;
        foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(table, @"(?:辺\s*(\d+)\s*)?s\s*([0-9.]+)\s*(?:床)?\s*約?\s*([0-9.]+)\s*(G\d)\s*(?:口底)?\s*約?\s*([0-9.]+)\s*→\s*(Mizo_[A-Za-z]+)"))
        {
            int e = m.Groups[1].Success ? int.Parse(m.Groups[1].Value) : (n > 0 ? _lastSeRojiEdge : 41); _lastSeRojiEdge = e;
            float s = float.Parse(m.Groups[2].Value, inv), tFloor = float.Parse(m.Groups[3].Value, inv), tMouth = float.Parse(m.Groups[5].Value, inv); string kata = m.Groups[4].Value, mzN = m.Groups[6].Value;
            string lab = "辺" + e + " s" + s.ToString("0.###", inv); n++;
            Vector2 ea = EdgePt(e, 0f), ax = (EdgePt(e, 1f) - ea).normalized, on = OutNormal(e), yd = -on;
            float sAt = s; if (mShift.Success && Mathf.Abs(float.Parse(mShift.Groups[1].Value, inv) - s) < 0.01f) sAt = s + (ax.y > 0f ? 1f : -1f) * float.Parse(mShift.Groups[2].Value, inv);
            EdoBuild.MizoProfile pr; List<Vector2> ln;
            if (!_secMizoProf.TryGetValue(mzN, out pr) || !_secMizoLine.TryGetValue(mzN, out ln)) { sb.AppendLine("  ⛔ 背の路地の暗渠 " + lab + ": 落とし先 " + mzN + " が建っていない ── 置かない(order【硬】)"); bad++; continue; }
            // ② 桝
            string mP = EdoAssets.Own.DoiMasu(kata); var mm = EdoBuild.MizoPieceOf(mP); if (!mm.ok) { sb.AppendLine("  ★ 背の路地の暗渠 " + lab + ": 桝 " + kata + " が測れない"); bad++; continue; }
            float sink = kata == "G1" ? sinkG1 : 0f, drop = tFloor - tMouth;
            float back = e == 40 ? sr.back40 : sr.back41;
            float half = 0f; { var pf = AssetDatabase.LoadAssetAtPath<GameObject>(mP); var tg = (GameObject)PrefabUtility.InstantiatePrefab(pf); tg.transform.position = Vector3.zero; tg.transform.rotation = Quaternion.identity;
                               foreach (var v in EdoBuild.Body(tg.transform, 40000)) if (v.y < -0.10f) half = Mathf.Max(half, Mathf.Abs(v.x)); UnityEngine.Object.DestroyImmediate(tg); }
            Vector2 qM = ea + ax * sAt + yd * (back + half + 0.005f);
            float fl = sr.At(qM); if (float.IsNaN(fl)) { sb.AppendLine("  ⛔ 背の路地の暗渠 " + lab + ": 桝の芯 (" + qM.x.ToString("F2", inv) + "," + qM.y.ToString("F2", inv) + ") が路地の床の帯の外 ── 置かない"); bad++; continue; }
            float yawM = Mathf.Atan2(on.x, on.y) * Mathf.Rad2Deg;
            var mgo = EdoBuild.Place(mP, new Vector3(qM.x, fl - 0.01f - sink, qM.y), yawM, Vector3.one, grp, "SeRoji_Masu_" + e + "_" + s.ToString("0.###", inv));
            float rim = EdoBuild.RB(mgo).max.y; float mouthM = rim - drop;
            // 長屋の背との隙(桝の外の面 − 背の面)
            float mBack = float.MaxValue; foreach (var v in EdoBuild.Body(mgo.transform, 40000)) { if (v.y >= rim - 0.10f || Mathf.Abs(mgo.transform.InverseTransformPoint(v).z) > half + 0.01f) continue; mBack = Mathf.Min(mBack, Vector2.Dot(new Vector2(v.x, v.z) - ea, yd)); }
            // ③ 吐口: 落とし先の溝の底と内の縁石の天端
            Vector2 qL = ea + ax * sAt;
            float bestD = float.MaxValue, arc = 0f, acc = 0f;
            for (int i = 0; i + 1 < ln.Count; i++) { Vector2 a = ln[i], b = ln[i + 1], ab = b - a; float L2 = ab.sqrMagnitude, t = Mathf.Clamp01(Vector2.Dot(qL - a, ab) / Mathf.Max(1e-8f, L2)); float dd = (a + ab * t - qL).sqrMagnitude; if (dd < bestD) { bestD = dd; arc = acc + Mathf.Sqrt(L2) * t; } acc += Mathf.Sqrt(L2); }
            float mzB = pr.At(arc);
            float curb = float.NaN; GameObject cp = null; float cd = float.MaxValue;
            if (smz != null) foreach (Transform c in smz) { if (!c.name.StartsWith(mzN + "_")) continue; var cb = EdoBuild.RB(c.gameObject).center; float dd = (new Vector2(cb.x, cb.z) - qL).sqrMagnitude; if (dd < cd) { cd = dd; cp = c.gameObject; } }
            if (cp != null)
            {
                string pp = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(cp); var cpm = EdoBuild.MizoPieceOf(pp); Vector3 rx = cp.transform.right;
                int side = Vector2.Dot(new Vector2(rx.x, rx.z), on) >= 0f ? -1 : 1; float xa, xb, ct;
                if (EdoBuild.MizoCurbTop(pp, side, out xa, out xb, out ct)) { var lp = cp.transform.InverseTransformPoint(new Vector3(qL.x, 0f, qL.y)); curb = cp.transform.TransformPoint(new Vector3(0.5f * (xa + xb), ct, Mathf.Clamp(lp.z, cpm.zMin, cpm.zMax))).y; }
            }
            float mouthK = mzB + kuOverBot; if (!float.IsNaN(curb)) mouthK = Mathf.Max(mouthK, curb + kuOverCurb);
            // 台の石垣の見え面 = 口の高さの帯(口の底 〜 +0.30)・吐口の幅(±0.45)で区画の線の 0.5 外から内へ打った光線が**最初に触れる面**
            //   (⛔ 頂点の窓で測らない ── 城の石垣の駒は大きな面の殻で、窓の内に頂点が無く測れなかった s65.359・第109巡の初回)
            float face = float.MinValue;
            if (ig != null)
            {
                var near = new List<GameObject>();
                foreach (Transform c in ig) { if (!c.gameObject.activeInHierarchy) continue; var cb = EdoBuild.RB(c.gameObject); if (cb.max.y < mouthK || cb.min.y > mouthK + 0.3f) continue;
                                              var rc = new Vector2(cb.center.x, cb.center.z) - qL; if (Mathf.Abs(Vector2.Dot(rc, ax)) < 3f && Mathf.Abs(Vector2.Dot(rc, on)) < 4f) near.Add(c.gameObject); }
                float reach = EdoBuild.ReachToBodies(qL + on * 0.5f, -on, near, 0.45f, mouthK - 0.1f + 0.001f, mouthK + 0.30f, 6f);
                if (!float.IsNaN(reach)) face = 0.5f - reach;
            }
            if (face == float.MinValue) { sb.AppendLine("  ⛔ 背の路地の暗渠 " + lab + ": 口の高さ " + mouthK.ToString("F2", inv) + " で台の石垣の見え面が測れない ── 吐口を置かない"); bad++; continue; }
            Vector2 qK = ea + ax * sAt + on * face;
            var kgo = EdoBuild.Place(kP, new Vector3(qK.x, 0f, qK.y), yawM, Vector3.one, grp, "SeRoji_Hakiguchi_" + e + "_" + s.ToString("0.###", inv));
            var wk = kgo.transform.TransformPoint(new Vector3(0f, km.floor, 0f)); kgo.transform.position += new Vector3(qK.x - wk.x, mouthK - wk.y, qK.y - wk.z);
            float tip = float.MinValue; foreach (var v in EdoBuild.Body(kgo.transform, 40000)) tip = Mathf.Max(tip, Vector2.Dot(new Vector2(v.x, v.z) - ea, on));
            float dist = Vector2.Distance(qM, qK), fall = mouthM - mouthK, gr = dist > 0.01f ? fall / dist : float.NaN;
            bool hard = fall > 0f && mouthK >= mzB + kuOverBot - 1e-3f && tip <= 0.001f;
            if (!hard) { bad++; UnityEngine.Object.DestroyImmediate(kgo); UnityEngine.Object.DestroyImmediate(mgo); }   // 硬い条件を破る組は据えない(退けて ⛔ を刷る)
            sb.AppendLine("  背の路地の暗渠 " + lab + (Mathf.Abs(sAt - s) > 1e-3f ? "(芯 s" + sAt.ToString("0.###", inv) + ")" : "") + ": 桝 " + kata + " 縁 " + rim.ToString("F3", inv) + "(路地の床 " + fl.ToString("F3", inv) + " − " + (fl - rim).ToString("F3", inv) + ")・長屋の背との隙 " + (mBack - back).ToString("+0.000;-0.000", inv)
                          + "・桝の口の底 " + mouthM.ToString("F3", inv) + " → 吐口(型M)の口の底 " + mouthK.ToString("F3", inv) + "(落ち " + fall.ToString("+0.000;-0.000", inv) + (fall > 0f ? " ⭕" : " ⛔ 逆勾配") + "・勾配 " + (float.IsNaN(gr) ? "-" : "1/" + (1f / Mathf.Max(1e-4f, gr)).ToString("F0", inv)) + (!float.IsNaN(gMin) && !float.IsNaN(gr) ? (gr >= gMin - 1e-4f && gr <= gMax + 1e-4f ? " ⭕(柔)" : " ⚠(柔 1/" + (1f / gMin).ToString("F0", inv) + "〜1/" + (1f / gMax).ToString("F0", inv) + ")") : "") + ")"
                          + "・口の底 − " + mzN + " の底 " + (mouthK - mzB).ToString("+0.000;-0.000", inv) + (mouthK - mzB >= kuOverBot - 1e-3f ? " ⭕" : " ⛔") + "(≥ +" + kuOverBot.ToString("F2", inv) + "【硬】)"
                          + (float.IsNaN(curb) ? "・内の縁石 -" : "・− 内の縁石の天端 " + (mouthK - curb).ToString("+0.000;-0.000", inv) + (mouthK - curb >= kuOverCurb - 1e-3f ? " ⭕" : " ⚠") + "(柔)")
                          + "・吐口の最も外 − 区画の線 " + tip.ToString("+0.000;-0.000", inv) + (tip <= 0.001f ? " ⭕" : " ⛔") + "・台の石垣の見え面 = 線から " + face.ToString("+0.000;-0.000", inv) + "・石樋は埋めて焼かない(toi)" + (hard ? "" : "・⛔ 硬い条件を破る ⇒ 桝と吐口を据えない"));
        }
        sb.Insert(0, "  背の路地の暗渠 D_SeRoji(drains.make): " + n + " か所" + (bad > 0 ? "・⛔ " + bad : " ⭕") + "\n");
        return sb.ToString();
    }
    static int _lastSeRojiEdge = 41;

    /// <summary>**長屋の前の下水溝(drains の route で名指す型)**(指図 drains[].route「&lt;棟&gt;/&lt;棟&gt; の前の全長(s a→b)に区画の内の石組の下水溝(型A)」・普請方 2026-10-10p・EDO-0502 第103巡 岡部 D_N40_Mae)。
    /// <see cref="PlaceFrontGutters"/>(roadEdge 10-10m の文で名指す型)と同じ置き方 ── ① 固定側 = 棟の躯体(Stage2 が runs.front で寄せた)。② 溝の芯 = 棟ごとの躯体の前の面(溝の帯で触れる所)+ 0.005 + 駒の半幅
    /// (棟の前の面が違えば継ぎ目で折る)。③ 頭 = 区間の始まり、ただし上流の前の溝(FrontMizo)の駒の外形の外へ出る所から(角で二つの溝を面で継ぐ)。
    /// ④ 底 = 頭で「(棟) の座 −d」【硬】、そこから「1/n 落とした値」「外の壁の天端 −m」「&lt;棟&gt; の前は &lt;棟&gt; の座 −d」の一番低い値【硬: 一方向に下る】(SolveMizoBottom の地盤の側で解く)。
    /// ⭐ 第111巡(施主 2026-10-11): 外の壁の天端 = 地表と面一(grading.*.mizo.outerTop)── 駒は天端の線で据える(<see cref="EdoBuild.LayMizoOnTopLine"/>)・嵩上げ石は廃止・
    /// 座 − d の底の上限は柔(剛体の駒は地表から測った深さを下流へ減らせないので、頭で満たせない分は刷る)。
    /// 門の口(据えた門長屋の札の通りの実測の幅)の下は蓋石の暗渠 ── 蓋の天端 = 道の線上の地盤 + 0.02 を狙い、敷居 −0.02 以下【硬】・内法の高さ ≥ 0.15【硬】・蓋の厚は在庫の 0.15(指図 0.12 は柔 ⇒ △)。
    /// 尻は区間の終わりで止める(続ける溝が建つまで開いたまま ⇒ ⚠)。当たる先: drains に「の前の全長(s …)に区画の内の石組の下水溝」を持つ前の溝(岡部 D_N40_Mae)。</summary>
    static string PlaceDrainFrontGutters()
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var root = GameObject.Find(GN); if (root == null) return "";
        var grp = Group("DrainMizo"); Clear(grp); var kg = Group("DrainMizoKasa"); Clear(kg); var lg = Group("DrainMizoFuta"); Clear(lg);
        string outerTxt = null; { var gr = O(Get(D, "grading")); foreach (var kv in gr ?? new Dictionary<string, object>()) { var mz = O(Get(O(kv.Value), "mizo")); if (mz != null && S(Get(mz, "outerTop")) != null) outerTxt = S(Get(mz, "outerTop")); } }
        // ⭐ 第111巡: 天端 = 地表と面一(grading.*.mizo.outerTop「面一」・幅 x m の帯・depth「x 以上【硬】・x 前後を狙う」)── 嵩上げ石は廃止
        string depthTxt = null; { var gr = O(Get(D, "grading")); foreach (var kv in gr ?? new Dictionary<string, object>()) { var mz = O(Get(O(kv.Value), "mizo")); if (mz != null && S(Get(mz, "depth")) != null) depthTxt = S(Get(mz, "depth")); } }
        var mOT = System.Text.RegularExpressions.Regex.Match((outerTxt ?? "").Contains("面一") ? outerTxt : "", @"幅\s*([0-9.]+)\s*m\s*の帯");
        var mDpG = System.Text.RegularExpressions.Regex.Match(depthTxt ?? "", @"([0-9.]+)\s*以上【硬】"); var mDtG = System.Text.RegularExpressions.Regex.Match(depthTxt ?? "", @"([0-9.]+)\s*前後を狙う");
        foreach (var o in A(Get(D, "drains")) ?? new List<object>())
        {
            var dr = O(o); if (dr == null) continue; string dn = S(Get(dr, "name")), route = S(Get(dr, "route")) ?? "";
            var mR = System.Text.RegularExpressions.Regex.Match(route, @"((?:N[0-9_]+[/・]?)+)\s*の前の全長[(（]s\s*([0-9.]+)\s*→\s*([0-9.]+)[)）]に区画の内の石組の下水溝[(（]型A[)）]");
            if (!mR.Success) continue;
            var mH = System.Text.RegularExpressions.Regex.Match(route, @"底は\s*s[0-9.]+\s*で\s*[0-9.]+[(（](N[0-9_]+)\s*の座\s*[−-]\s*([0-9.]+)\)");
            var mSl = System.Text.RegularExpressions.Regex.Match(route, @"『1/(\d+)\s*落とした値』");
            var mOm = System.Text.RegularExpressions.Regex.Match(route, @"『外の壁の天端\s*[−-]\s*([0-9.]+)』");
            if (!mH.Success || !mSl.Success || !mOm.Success || !mOT.Success || !mDpG.Success || !mDtG.Success) { sb.AppendLine("  ★ 前の下水溝 " + dn + ": route の頭の底・勾配・外の壁の天端からの深さ・grading.*.mizo の outerTop(面一・帯の幅)/ depth が読めない ── 置かない"); continue; }
            float sA = float.Parse(mR.Groups[2].Value, inv), sB = float.Parse(mR.Groups[3].Value, inv), headDrop = float.Parse(mH.Groups[2].Value, inv);
            float slope = 1f / float.Parse(mSl.Groups[1].Value, inv), depthFromOuter = float.Parse(mOm.Groups[1].Value, inv), band = float.Parse(mOT.Groups[1].Value, inv);
            float depthMin = float.Parse(mDpG.Groups[1].Value, inv), depthTgt = float.Parse(mDtG.Groups[1].Value, inv);
            var names = new List<string>(mR.Groups[1].Value.Split(new[] { '/', '・' }, System.StringSplitOptions.RemoveEmptyEntries));
            // 棟の座 −d(「<棟> の前は <棟> の座 −d」)
            var zaDrop = new Dictionary<string, float>(); zaDrop[mH.Groups[1].Value] = headDrop;
            foreach (System.Text.RegularExpressions.Match mz in System.Text.RegularExpressions.Regex.Matches(route, @"(N[0-9_]+)\s*の前は\s*N[0-9_]+\s*の座\s*[−-]\s*([0-9.]+)")) zaDrop[mz.Groups[1].Value] = float.Parse(mz.Groups[2].Value, inv);
            var p30 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.30f); var p10 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.10f);
            var m30 = p30 == null ? default(EdoBuild.MizoPiece) : EdoBuild.MizoPieceOf(p30); var m10 = p10 == null ? default(EdoBuild.MizoPiece) : EdoBuild.MizoPieceOf(p10);
            if (p30 == null || p10 == null || !m30.ok || !m10.ok) { sb.AppendLine("  ★ 前の下水溝 " + dn + ": 石組の溝の駒(DoiMizo 型A)が測れない ── 置かない"); continue; }
            float halfW = Mathf.Max(Mathf.Abs(m30.xMin), Mathf.Abs(m30.xMax)), W = m30.xMax - m30.xMin;
            // 棟ごとの躯体の前の面・座・走りの範囲
            int edge = -1; var segs = new List<Vector4>(); var zaOf = new List<float>(); var gateSpans = new List<Vector2>(); bool bad = false; string runsNote = "";
            foreach (var nm in names)
            {
                int ri = -1; for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == nm) ri = k; var nbT = root.transform.Find("Kakoi/" + nm);
                if (ri < 0 || nbT == null) { sb.AppendLine("  ★ 前の下水溝 " + dn + ": 棟 " + nm + " が無い"); bad = true; break; }
                var r = Runs[ri];
                if (edge < 0) edge = r.edge; else if (edge != r.edge) { sb.AppendLine("  ★ 前の下水溝 " + dn + ": 棟 " + nm + " が別の辺 ── 置かない"); bad = true; break; }
                Vector2 ea0 = EdgePt(edge, 0f), ax0 = (EdgePt(edge, 1f) - ea0).normalized, on0 = OutNormal(edge);
                var bp = EdoBuild.BodyExRoof(nbT, 6000); if (bp.Count == 0) { sb.AppendLine("  ★ 前の下水溝 " + dn + ": " + nm + " の躯体が測れない"); bad = true; break; }
                float y0 = float.MaxValue; foreach (var p in bp) y0 = Mathf.Min(y0, p.y);
                float fF = EdoBuild.FaceOut(nbT.gameObject, ea0, on0, y0 - 0.01f, y0 + 0.30f);
                var sp = EdoBuild.SpecBodySpanAlong(nbT.gameObject, ea0, ax0); if (float.IsNaN(sp.x)) sp = EdoBuild.BodySpanAlong(nbT.gameObject, ea0, ax0);
                if (float.IsNaN(fF) || float.IsNaN(sp.x)) { sb.AppendLine("  ★ 前の下水溝 " + dn + ": " + nm + " の前の面が測れない"); bad = true; break; }
                // ⭐ 前に溝を持つ台(runs[].front「溝の内の縁」── const.kidan 甲の型)は、溝の外の壁の見え面を区画の線の内 0.001・内の壁 = 台の石垣の根石(基準線 = 溝の全幅 +0.01)。
                //   ⛔ 躯体の前の面から測ると、甲の型で囲いが c + 犬走り 内へ下がった後は溝が台の石垣の法の上に載った(D_N40_Mae の外の壁 −0.55・第108巡)。
                bool onDatum = (RunText(nm, "front") ?? "").Contains("溝の内の縁");
                segs.Add(new Vector4(sp.x, sp.y, onDatum ? -(halfW + 0.001f) : fF + 0.005f + halfW, y0)); zaOf.Add(y0);
                runsNote += nm + "(座 " + y0.ToString("F2", inv) + "・前の面 " + fF.ToString("F3", inv) + ") ";
                // 門の口(札の通りの実測)
                var spc = EdoPartSpec.Get(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(nbT.gameObject));
                if (spc != null && spc.passage != null && spc.passage.x1 - spc.passage.x0 > 0.1f)
                { float sC = Vector2.Dot(EdoPartSpec.PassageCenterWorld(spc, nbT) - ea0, ax0), wC = spc.passage.x1 - spc.passage.x0; gateSpans.Add(new Vector2(sC - wC * 0.5f, sC + wC * 0.5f)); }
            }
            if (bad || segs.Count == 0) continue;
            Vector2 ea = EdgePt(edge, 0f), ax = (EdgePt(edge, 1f) - ea).normalized, on = OutNormal(edge);
            float dOutMax = float.MinValue; foreach (var sg in segs) dOutMax = Mathf.Max(dOutMax, sg.z + halfW);
            if (dOutMax > 0.001f) { sb.AppendLine("  ⛔ 前の下水溝 " + dn + ": 外の壁が区画の線の外 " + dOutMax.ToString("F3", inv) + " ── 置かない(runs.front の寄せが足りない)・" + runsNote); continue; }
            System.Func<float, int> segAt = s => { int k = 0; for (int i = 0; i < segs.Count; i++) if (s >= segs[i].x - 1e-3f) k = i; return k; };
            // ③ 頭: 区間の始まり、上流の前の溝の駒の外形の外へ出る所から
            var up = new List<Vector2[]>(); var fm = root.transform.Find("FrontMizo");
            if (fm != null) foreach (Transform c in fm) { var pts = new List<Vector2>(); foreach (var v in EdoBuild.Body(c, 2000)) pts.Add(new Vector2(v.x, v.z)); if (pts.Count >= 3) up.Add(EdoBuild.ConvexHull2(pts).ToArray()); }
            float sHead = Mathf.Max(sA, segs[0].x); string headWhy = "区間の始まり";
            for (float s = sHead; s < sB; s += 0.05f)
            {
                float dC = segs[segAt(s)].z; bool hit = false;
                foreach (float dd in new[] { dC - halfW, dC, dC + halfW }) { var q = ea + ax * s + on * dd; if (!EdoGeom.PIP(Poly, q)) hit = true; foreach (var h in up) if (EdoGeom.PIP(h, q)) hit = true; }
                if (!hit) { if (s > sHead + 1e-3f) headWhy = "上流の前の溝の駒の外形の外"; sHead = s; break; }
            }
            float sTail = Mathf.Min(sB, segs[segs.Count - 1].y);
            // 線(棟の前の面が違えば継ぎ目で折る)
            var line = new List<Vector2>();
            for (int i = 0; i < segs.Count; i++)
            {
                float s0 = Mathf.Max(sHead, i == 0 ? sHead : segs[i].x), s1 = Mathf.Min(sTail, i + 1 < segs.Count ? segs[i + 1].x : sTail); if (s1 <= s0 + 1e-3f) continue;
                var a = ea + ax * s0 + on * segs[i].z; var b = ea + ax * s1 + on * segs[i].z;
                if (line.Count == 0 || Vector2.Distance(line[line.Count - 1], a) > 0.01f) line.Add(a); line.Add(b);
            }
            if (line.Count < 2) { sb.AppendLine("  ★ 前の下水溝 " + dn + ": 線が無い"); continue; }
            var bd = EdoBuild.BaseDem(); var mnD = MichiNarashi;
            System.Func<float, float, float> sOf = (x, z) => Vector2.Dot(new Vector2(x, z) - ea, ax);
            System.Func<float, float, float> road = (x, z) => { var qq = ea + ax * sOf(x, z) + on * 0.05f; float b0 = bd(qq.x, qq.y), m0 = mnD == null ? float.NaN : MichiNarashiAt(mnD, qq.x, qq.y); return float.IsNaN(m0) ? b0 : (float.IsNaN(b0) ? m0 : Mathf.Min(b0, m0)); };
            // 地表 = 造成の面(okabe_graded.bin)── 無い所は道の線上の地盤
            System.Func<float, float, float> surf = (x, z) => { float y = DesignY(new Vector2(x, z)); return float.IsNaN(y) ? road(x, z) : y; };
            System.Func<float, bool> inGate = s => { foreach (var g in gateSpans) if (s >= g.x - 0.05f && s <= g.y + 0.05f) return true; return false; };
            string lidP = EdoAssets.Own.DoiFutaishiFor("A", 0.15f); var lm = EdoBuild.MizoPieceOf(lidP); float lidT = lm.top - lm.bottom, lidLen = lm.len > 0.05f ? lm.len : 0.5f;
            float sill = float.NaN; { var g = O(Get(D, "gate")); if (g != null && S(Get(g, "host")) != null && names.Contains(S(Get(g, "host"))) && Has(g, "sill")) sill = F(g["sill"]); }
            float headZa = zaOf[0] - headDrop;
            // 底の上限【柔 ── 第111巡: 天端 = 地表が先】: 頭 = 座 − d・「<棟> の前は <棟> の座 − d」
            System.Func<float, float> capAt = a =>
            {
                float s = a + sHead; int k = segAt(s); string nm = names[Mathf.Min(k, names.Count - 1)]; float c = float.NaN, zd;
                if (zaDrop.TryGetValue(nm, out zd)) c = segs[k].w - zd; if (a < 0.5f) c = float.IsNaN(c) ? headZa : Mathf.Min(c, headZa);
                return c;
            };
            var vA = new List<string>(); for (float dd = 0.10f; dd <= 0.30f + 1e-4f; dd += 0.05f) { string pth = EdoAssets.Own.DoiMizo("A", (float)System.Math.Round(dd, 2), MizoAgo); if (EdoBuild.MizoPieceOf(pth).ok) vA.Add(pth); }
            var spec = new EdoBuild.MizoTopSpec { name = dn, line = line, surfaceAt = surf, outAt = q => on, halfW = halfW, surfaceOff = band, versions = vA,
                                                  depthMin = depthMin, depthTarget = Mathf.Max(depthTgt, depthFromOuter), bottomCapAt = capAt, coverAt = gateSpans.Count > 0 ? (System.Func<float, bool>)(a => inGate(a + sHead)) : null, coverT = lidT,
                                                  fitAfter = new List<Vector2> { line[line.Count - 1], line[line.Count - 1] + ax * 8f } };   // 尻は Mizo_Kita へ同じ線で続く(route)── 天端の線の当てはめを続ける溝の地表まで延ばす
            var rep = EdoBuild.LayMizoOnTopLine(grp, dn, spec); _drainTopRep[dn] = rep;
            var made = rep.made;
            // 門の口の蓋石(蓋の下の駒の範囲)── 蓋の天端 = 地表(± 0.02)・敷居 −0.02 以下【硬】
            int nLid = 0, nLidIn = 0; float lidOutLeft = 0f; float lidLo = float.MaxValue, lidHi = float.MinValue, sillGap = float.MaxValue; var lids = new List<GameObject>();
            foreach (var cs in rep.coverSpans)
            {
                var under = new List<GameObject>(rep.covered);
                for (float s = cs.x + lidLen * 0.5f; s <= cs.y - lidLen * 0.5f + lidLen * 0.999f; s += lidLen)
                {
                    float sc = Mathf.Min(s, cs.y - lidLen * 0.5f); Vector2 dd; var at = EdoBuild.PointAt(line, Mathf.Clamp(sc, 0f, rep.length), out dd);
                    float off; var lid = EdoBuild.LayFutaishi(lg, dn + "_Futa_" + nLid, lidP, at, ax, under, surf, out off);
                    if (lid == null) continue; nLid++; lids.Add(lid);
                    { var qo = at + on * (halfW + band); off = EdoBuild.RB(lid).max.y - surf(qo.x, qo.y); lidLo = Mathf.Min(lidLo, off); lidHi = Mathf.Max(lidHi, off); }   // 蓋の天端 − 帯の外の造成の面
                    { float bf0; var lc = EdoBuild.RB(lid).center; int eL = LidEdge(new Vector2(lc.x, lc.z)); float pl = EdoBuild.PullAlongInside(new List<GameObject> { lid }, Poly, -OutNormal(eL), 0.30f, out bf0);
                      if (bf0 > 0.001f) { nLidIn++; if (float.IsNaN(pl)) lidOutLeft = Mathf.Max(lidOutLeft, bf0); } }   // 蓋石は区画の線を越えない【硬: 区域】
                    if (!float.IsNaN(sill) && inGate(sc + sHead)) sillGap = Mathf.Min(sillGap, sill - EdoBuild.RB(lid).max.y);
                }
            }
            foreach (var g in rep.covered) { float lt = float.MinValue; var gb = EdoBuild.RB(g); foreach (var l in lids) { var lb = EdoBuild.RB(l); if (lb.Intersects(gb)) lt = Mathf.Max(lt, lb.max.y); } if (lt > float.MinValue) _mizoCoverTop[g] = lt; }
            float upTail = float.NaN; if (fm != null) foreach (Transform c in fm) { var b = EdoBuild.RB(c.gameObject); upTail = float.IsNaN(upTail) ? b.min.y : Mathf.Min(upTail, b.min.y); }
            sb.AppendLine("  前の下水溝 " + dn + "(drains.route・" + string.Join("/", names.ToArray()) + "): 石組の溝 型A を天端の線で " + made.Count + " 駒・" + rep.length.ToString("F1", inv) + "m(s " + sHead.ToString("F2", inv) + "〜" + sTail.ToString("F2", inv) + "・頭 = " + headWhy + ")・全幅 " + W.ToString("F2", inv)
                          + "・外の壁 最大 " + dOutMax.ToString("F3", inv) + "(区画の線の内【硬】⭕)・" + runsNote
                          + "・天端 − 造成の面 " + rep.devLo.ToString("+0.000;-0.000", inv) + "〜" + rep.devHi.ToString("+0.000;-0.000", inv) + (rep.devLo >= -0.02f - 1e-3f && rep.devHi <= 0.02f + 1e-3f ? " ⭕(±0.02)" : " ⚠(±0.02 の外 ── 帯の地面を天端へ合わせる)")
                          + "・隣の天端の段差 最大 " + rep.stepMax.ToString("F3", inv) + (rep.stepMax <= 0.01f + 1e-4f ? " ⭕" : " ⛔ @" + rep.stepAt) + (rep.coverSpans.Count > 0 ? "(蓋の縁 " + rep.stepCover.ToString("F3", inv) + " は蓋の下)" : "")
                          + "・底 " + rep.botHead.ToString("F3", inv) + "→" + rep.botTail.ToString("F3", inv) + (rep.nRise == 0 ? "(一方向に下る ⭕)" : "(⛔ 上る所 " + rep.nRise + "・最大 " + rep.riseMax.ToString("F3", inv) + ")")
                          + "・底の上限(頭 ≤ " + names[0] + " の座 − " + headDrop.ToString("F2", inv) + " = " + headZa.ToString("F2", inv) + "・棟の前の座 − d)の越え 最大 " + rep.capOver.ToString("F3", inv) + (rep.capOver <= 1e-3f ? " ⭕" : " △ @" + rep.capAt + "(柔 ── 天端 = 地表と深さが下流へ減らない駒では頭で満たせない ⇒ 差し戻し)")
                          + "・深さ " + rep.depthLo.ToString("F3", inv) + "〜" + rep.depthHi.ToString("F3", inv) + (rep.depthLo >= depthMin - 1e-3f ? " ⭕(≥" + depthMin.ToString("F2", inv) + ")" : " ⛔") + "(狙い " + spec.depthTarget.ToString("F2", inv) + "【柔】)"
                          + (rep.coverSpans.Count > 0 ? "・門の口の暗渠 蓋石 " + nLid + " 枚(線の内へ寄せた " + nLidIn + (lidOutLeft > 0.001f ? "・⛔ 寄せても区画の外 " + lidOutLeft.ToString("F3", inv) : "") + "・蓋の下の駒 " + rep.covered.Count + (rep.nAutoCover > 0 ? "・うち版で届かず蓋 " + rep.nAutoCover : "") + "・厚 " + lidT.ToString("F2", inv) + ")・蓋の天端 − 造成の面 " + (nLid > 0 ? lidLo.ToString("+0.000;-0.000", inv) + "〜" + lidHi.ToString("+0.000;-0.000", inv) + (lidLo >= -0.02f - 1e-3f && lidHi <= 0.02f + 1e-3f ? " ⭕" : " ⚠") : "-")
                             + (float.IsNaN(sill) || nLid == 0 ? "" : "・敷居 − 蓋の天端 最小 " + sillGap.ToString("F3", inv) + (sillGap >= 0.02f - 0.005f ? " ⭕" : " ⛔")) : "")
                          + (float.IsNaN(upTail) ? "" : "・上流の溝の底の最低 " + upTail.ToString("F2", inv) + " / 頭の底 " + rep.botHead.ToString("F2", inv) + (upTail > rep.botHead ? " ⭕(落とし先が低い)" : " ⚠"))
                          + (rep.nDeep > 0 ? "・⛔ 版で届かない駒 " + rep.nDeep : ""));
        }
        return sb.ToString();
    }

    /// <summary>**前の下水溝の尻の暗渠**(指図 drains D_&lt;棟&gt;_Mae の route ── 普請方 2026-10-10n・EDO-0502 第96巡)。
    /// route の文: 「尻は塞ぎ石で閉じ、在庫の石樋(…)の暗渠を区画の線の内に入れ辺&lt;n&gt; に沿って … 1/k で下流へ【硬】→ 吐き口は表門脇の下水と同じ型M、床が前の道より x 以上高くなる最初の所【硬】」。
    /// 置き方: 線 = 溝の尻の芯 T → (溝の芯の線と、辺 n を区画の線から石樋の半幅 + 0.01 内へ寄せた線の交わり)→ 辺 n に沿って下流へ。
    /// 石樋の外の面は区画の線の内 0.01【硬】(半幅は実メッシュ)。底 = 溝の尻の底 − 0.01(受ける側の底 &lt; 入る側の底【硬】)から 1/k。
    /// 吐き口 = 底 ≥ 前の道(区画の線の外 0.05 の造成前の地盤)+ x となる最初の s。型M の吐口(DoiAnkyoKuchi)の口の底を樋の底へ・嘴の先を区画の線の内 0.001 へ・口は辺の外向き。
    /// 樋の駒は口の芯で止める(口の駒の奥に埋まる)。⛔ 塞ぎ石は部材が無い ── ★ で名乗る(部材方へ)。当たる先: drains に「石樋」「暗渠」「型M」を持つ前の溝(岡部 D_N39_1_Mae)。</summary>
    static string PlaceFrontAnkyo(Run run, Vector2 T, float tailBottom, float sTail, GameObject tailPiece)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        string route = null, dn = "D_" + run.name + "_Mae";
        foreach (var o in A(Get(D, "drains")) ?? new List<object>()) { var q = O(o); if (q != null && S(Get(q, "name")) == dn) route = S(Get(q, "route")); }
        var grp = Group("FrontAnkyo"); Clear(grp);
        if (route == null || !route.Contains("石樋") || !route.Contains("暗渠")) return "";
        var mE = System.Text.RegularExpressions.Regex.Match(route, @"辺\s*(\d+)\s*に沿");
        var mS = System.Text.RegularExpressions.Regex.Match(route, @"の下を\s*1\s*/\s*(\d+)");
        var mF = System.Text.RegularExpressions.Regex.Match(route, @"床が前の道より\s*([0-9.]+)\s*以上高くなる最初の所");
        var mX = System.Text.RegularExpressions.Regex.Match(route, @"出は\s*([0-9.]+)\s*以下");
        if (!mE.Success || !mS.Success || !mF.Success) return "  ★ 暗渠 " + dn + ": route の辺・勾配・吐き口の床が読めない ── 置かない\n";
        int e2 = int.Parse(mE.Groups[1].Value); float slope = 1f / float.Parse(mS.Groups[1].Value, inv), upF = float.Parse(mF.Groups[1].Value, inv);
        string tP = EdoAssets.Own.MatsudairaIshidoi, kP = EdoAssets.Own.DoiAnkyoKuchi; var tm = EdoBuild.MizoPieceOf(tP); var km = EdoBuild.MizoPieceOf(kP);
        if (!tm.ok || !km.ok) return "  ★ 暗渠 " + dn + ": 石樋か型M の吐口が測れない ── 置かない\n";
        float tHalf = Mathf.Max(Mathf.Abs(tm.xMin), Mathf.Abs(tm.xMax)), tLen = tm.zMax - tm.zMin;
        Vector2 fa = EdgePt(e2, 0f), fx = (EdgePt(e2, 1f) - fa).normalized, fo = OutNormal(e2); float dT = -(tHalf + 0.01f);
        Vector2 ea = EdgePt(run.edge, 0f), ax = (EdgePt(run.edge, 1f) - ea).normalized;
        // 交わり X: T + ax·u が辺 e2 の線から dT
        float den = Vector2.Dot(ax, fo); if (Mathf.Abs(den) < 1e-3f) return "  ★ 暗渠 " + dn + ": 溝の線と辺 " + e2 + " が平行 ── 置かない\n";
        float u = (dT - Vector2.Dot(T - fa, fo)) / den; Vector2 X = T + ax * u;
        var bd = EdoBuild.BaseDem();
        System.Func<float, float> roadE = s => { var q = fa + fx * s + fo * 0.05f; return bd(q.x, q.y); };
        float sX = Vector2.Dot(X - fa, fx), head = tailBottom - 0.01f, lenTX = Mathf.Max(0f, u);
        // 吐き口の s(辺 e2 の上)── 床 ≥ 道 + upF の最初
        float sOut = float.NaN; for (float s = sX + 0.5f; s <= sX + 40f; s += 0.05f) { float fl = head - slope * (lenTX + (s - sX)); if (fl >= roadE(s) + upF) { sOut = s; break; } }
        if (float.IsNaN(sOut)) return "  ⛔ 暗渠 " + dn + ": 辺 " + e2 + " に沿って 40m 内に床が道 + " + upF.ToString("F2", inv) + " を超える所が無い ── 置かない(普請方へ)\n";
        // 吐き口の口の幅が辺 e2 の上に収まるか・その間に区画の線の内か
        Vector2 E = fa + fx * sOut + fo * dT;
        var line = new List<Vector2> { T, X, E }; float L = lenTX + (sOut - sX);
        int n = Mathf.Max(2, Mathf.CeilToInt(L / 0.25f) + 1);
        var pr = new EdoBuild.MizoProfile { s = new float[n], ground = new float[n], bottom = new float[n], p = new Vector2[n], length = L, halfW = tHalf, pieceLen = tLen, topAbove = 0f, chord = true };
        for (int i = 0; i < n; i++) { float s = L * i / (n - 1); Vector2 dd; var p = EdoBuild.PointAt(line, s, out dd); pr.s[i] = s; pr.p[i] = p; pr.bottom[i] = head - slope * s; pr.ground[i] = EdoBuild.Ground(p.x, p.y); }
        pr.p = line.ToArray();   // LayMizo は p を線(折れ線)として読む ── 弧長は s と同じ
        int miss; string mw; var made = EdoBuild.LayMizo(grp, dn + "_Toi", pr, need => tP, out miss, out mw, null, null);
        float floorOut = head - slope * L;
        // 硬(許容0 の浮き): 樋の底が設計の地盤(皮が描く地表 = SkinGround)より上に出る駒があれば暗渠を建てない ── 欄は「帯の下」を前提にしているが、
        //   帯の設計の地盤が樋の底より低い所では樋が浮く(第96巡: N40_0 の前の帯は面 Hokuto 13.10・樋の底 13.56〜13.63 で 0.45〜0.53 浮いた)。⛔ 帯を盛って隠さない(設計判断)── 普請方へ
        { float worstF = 0f; string wf = null; foreach (var g in made) { var b = EdoBuild.RB(g); float gd = SkinGround(b.center.x, b.center.z); if (!float.IsNaN(gd) && b.min.y - gd > worstF) { worstF = b.min.y - gd; wf = g.name + "(底 " + b.min.y.ToString("F2", inv) + "・設計の地盤 " + gd.ToString("F2", inv) + ")"; } }
          if (worstF > 0.05f) { Clear(grp); return "  ⛔ 暗渠 " + dn + "(drains route 10-10n): 石樋の底が設計の地盤より最大 " + worstF.ToString("F2", inv) + " 上 〔" + wf + "〕── 帯の下に入らず浮く(許容0)・建てない(普請方へ: 帯の地盤 < 樋の底)。"
                                     + "参考: 吐き口は s " + sOut.ToString("F2", inv) + "・床 " + floorOut.ToString("F3", inv) + " / 前の道 " + roadE(sOut).ToString("F3", inv) + "\n"
                                     + (route.Contains("塞ぎ石") ? "    ★ 溝の尻の塞ぎ石: 型A の溝の小口を塞ぐ石の部材が無い ── 据えない(部材方へ)\n" : ""); } }
        float yaw = Mathf.Atan2(fo.x, fo.y) * Mathf.Rad2Deg; Vector2 mouth = fa + fx * sOut - fo * (km.zMax + 0.001f);
        var kgo = EdoBuild.Place(kP, new Vector3(mouth.x, 0f, mouth.y), yaw, Vector3.one, grp, dn + "_Hakiguchi");
        var wk = kgo.transform.TransformPoint(new Vector3(0f, km.floor, 0f)); kgo.transform.position += new Vector3(mouth.x - wk.x, floorOut - wk.y, mouth.y - wk.z);
        float tipOut = float.MinValue; foreach (var v in EdoBuild.Body(kgo.transform, 4000)) tipOut = Mathf.Max(tipOut, Vector2.Dot(new Vector2(v.x, v.z) - fa, fo));
        float toiOut = float.MinValue; foreach (var g in made) foreach (var v in EdoBuild.Body(g.transform, 2000)) { var q2 = new Vector2(v.x, v.z); toiOut = Mathf.Max(toiOut, EdoGeom.PIP(Poly, q2) ? -1f : 1f); }
        // 樋が地盤から出る量(柔): 樋の天端 − 外の面の前(区画の線の外 0.05)の造成前の地盤 の最大
        float expo = float.MinValue; string expoAt = "-";
        foreach (var g in made) { var b = EdoBuild.RB(g); var c = new Vector2(b.center.x, b.center.z); float s = Vector2.Dot(c - fa, fx); var q = fa + fx * s + fo * 0.05f; float ex = b.max.y - bd(q.x, q.y); if (ex > expo) { expo = ex; expoAt = g.name; } }
        float roadOut = roadE(sOut);
        sb.AppendLine("  暗渠 " + dn + "(drains route 10-10n): 石樋 " + made.Count + " 駒・" + L.ToString("F1", inv) + "m(溝の尻 → 辺 " + e2 + " の区画の線の内 " + (-dT).ToString("F2", inv) + " を下流へ s " + sX.ToString("F2", inv) + "→" + sOut.ToString("F2", inv) + ")"
                      + "・底 " + head.ToString("F3", inv) + "→" + floorOut.ToString("F3", inv) + "(溝の尻の底 " + tailBottom.ToString("F3", inv) + " − 0.01・1/" + mS.Groups[1].Value + "【硬】)"
                      + "・樋の最も外 " + (toiOut > 0f ? "区画の外 ⛔" : "区画の線の内 ⭕")
                      + "・吐き口 型M(DoiAnkyoKuchi)床 " + floorOut.ToString("F3", inv) + " / 前の道 " + roadOut.ToString("F3", inv) + "(+" + (floorOut - roadOut).ToString("F3", inv) + (floorOut - roadOut >= upF - 1e-3f ? " ⭕" : " ⛔") + " ≥ " + upF.ToString("F2", inv) + "【硬】)"
                      + "・嘴の先 − 区画の線 " + tipOut.ToString("+0.000;-0.000", inv) + (tipOut > 0.001f ? " ⛔" : " ⭕")
                      + "・樋が道の地盤から出る最大 " + expo.ToString("F2", inv) + "〔" + expoAt + "〕" + (mX.Success ? (expo <= float.Parse(mX.Groups[1].Value, inv) + 1e-3f ? " ⭕(柔 ≤" : " ⚠(柔 ≤") + mX.Groups[1].Value + ")" : "")
                      + (miss > 0 ? "・⚠ 駒が無い " + miss + "(" + mw + ")" : ""));
        if (route.Contains("塞ぎ石")) sb.AppendLine("    ★ 溝の尻の塞ぎ石(route「尻は塞ぎ石で閉じ」・roadEdge 10-10n ②「N40_0 の躯体の面に触れて据える」): 型A の溝の小口を塞ぐ石の部材が無い ── 据えない(部材方へ)");
        return sb.ToString();
    }

    static string PlaceBackGutters()
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var root = GameObject.Find(GN); if (root == null) return "";
        foreach (var o in A(Get(D, "terraces")) ?? new List<object>())
        {
            var t = O(o); string fl = S(Get(t, "flat")); if (fl == null) continue; string nm = S(Get(t, "name"));
            var mG = System.Text.RegularExpressions.Regex.Match(fl, @"(N[0-9_]+)\s*の背の足元"); var mW = System.Text.RegularExpressions.Regex.Match(fl, @"浅い石組の溝[(（]\s*幅\s*([0-9.]+)\s*・\s*深さ\s*([0-9.]+)");
            var mS = System.Text.RegularExpressions.Regex.Match(fl, @"長手に\s*1\s*/\s*([0-9]+)"); var mY = System.Text.RegularExpressions.Regex.Match(fl, @"面は\s*([0-9.]+)");
            if (!mG.Success || !mW.Success) continue;
            if (!mS.Success || !mY.Success) { sb.AppendLine("  ★ " + nm + " 背の雨落ち: 勾配か面の高さが読めない ── 置かない"); continue; }
            string rn = mG.Groups[1].Value; float yF = float.Parse(mY.Groups[1].Value, inv), dMax = Mathf.Max(float.Parse(mW.Groups[2].Value, inv), _gesui != null && _gesui.ok ? _gesui.dMax : 0f), slope = 1f / float.Parse(mS.Groups[1].Value, inv);
            string p0 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.15f);
            if (p0 == null || !System.IO.File.Exists(System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName, p0))) { sb.AppendLine("  ★ " + nm + " 背の雨落ち: 石組の溝の駒(DoiMizo 型 A)が在庫に無い ── 置かない"); continue; }
            var mp = EdoBuild.MizoPieceOf(p0); if (!mp.ok) { sb.AppendLine("  ★ " + nm + " 背の雨落ち: 駒の溝の底が測れない ── 置かない"); continue; }
            int ri = -1; for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == rn) ri = k;
            var nbT = root.transform.Find("Kakoi/" + rn); if (ri < 0 || nbT == null) { sb.AppendLine("  ★ " + nm + " 背の雨落ち: 棟 " + rn + " が無い"); continue; }
            int e = Runs[ri].edge; Vector2 ea = EdgePt(e, 0f), ax = (EdgePt(e, 1f) - ea).normalized, yard = -OutNormal(e);
            float seatY = nbT.position.y; float back = EdoBuild.FaceOut(nbT.gameObject, ea, yard, seatY + 0.1f, seatY + 1.2f);
            var sp = EdoBuild.SpecBodySpanAlong(nbT.gameObject, ea, ax); if (float.IsNaN(sp.x)) sp = EdoBuild.BodySpanAlong(nbT.gameObject, ea, ax);
            if (float.IsNaN(back) || float.IsNaN(sp.x)) { sb.AppendLine("  ★ " + nm + " 背の雨落ち: " + rn + " の背の面が測れない"); continue; }
            float halfW = Mathf.Max(Mathf.Abs(mp.xMin), Mathf.Abs(mp.xMax)); float offL = back + halfW + 0.02f;
            // 頭の底 = 最も浅い駒の**実測の**深さ(縁を含む)── 名の 0.10 で解くと頭の駒の天端が縁の分だけ浮いて落ちた(第80巡)
            var p10 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.10f); var m10 = p10 == null ? default(EdoBuild.MizoPiece) : EdoBuild.MizoPieceOf(p10);
            float dMin = p10 != null && m10.ok ? m10.Depth : 0.10f;
            Vector2 a0 = ea + ax * sp.x + yard * offL, a1 = ea + ax * sp.y + yard * offL;
            // 下流 = 表門脇の下水の入口 J(omoteGesui・第81巡)── 背の線の上で J まで流し、J より先(門の口の向こう)へは跨がない。下水が無ければ門の口に近い端。
            //   ⚠ 第80巡は門を Grid.W(0,0)(区画の格子の原点・東の遠く)で測り、門と反対の東の端へ下げていた
            List<Vector2> line = null; bool toJ = _gesui != null && _gesui.ok; var lines = new List<List<Vector2>>();
            if (toJ)
            {
                float sJ = Vector2.Dot(_gesui.J - ea, ax); Vector2 jOn0 = ea + ax * sJ + yard * offL;
                // 集水枡の型(第102巡): 背の雨落ちは枡を境に二手 ── 両端から枡へ(枡の外の面 = 桝 G1 の外 0.75 角の半分で止める)
                var fars = new List<Vector2>();
                if (_gesui.sump) { if (sJ - sp.x > 1.5f) fars.Add(a0); if (sp.y - sJ > 1.5f) fars.Add(a1); }
                else fars.Add(Mathf.Abs(sp.x - sJ) >= Mathf.Abs(sp.y - sJ) ? a0 : a1);
                foreach (var far in fars) {
                Vector2 jOn = _gesui.sump ? jOn0 + (far - jOn0).normalized * 0.375f : jOn0;
                // 頭の端は面の高さ yF の面の内まで引く【硬・浮き 0】── 棟の妻の先は郭の側の溝の面(Mizo_N39_1・13.1)で、頭の駒が 1.02 浮いた(第81巡の一回目)
                var fcs = FlatFaces(null); Vector2 dJ = (jOn - far).normalized, pp = new Vector2(-dJ.y, dJ.x); float clip = 0f, Lf = Vector2.Distance(far, jOn);
                // 追記 2026-10-10g【硬】: 頭は縁の石垣の天端の背の線から keepIn 以上内で止め、石垣の上に据えない ── 段の土留め(Dan)の駒の足形(凸包)から keepIn 以上離す(第90巡: Amaochi_000 × 023f)
                float keepIn = float.NaN; { var m10g = System.Text.RegularExpressions.Regex.Match(fl, @"天端の背の線から\s*([0-9.]+)\s*以上内"); if (fl.Contains("追記 2026-10-10g") && m10g.Success) keepIn = float.Parse(m10g.Groups[1].Value, inv); }
                // 追記 2026-10-10i【硬】(10-10g の 0.3 を改め): 頭は縁の石垣の**見え面の天端の線**から keepFront 以上内(⛔ 凸包の背の線から測らない ── 第91巡: 背の線から 0.3 で頭が溝 N39_1 の脇に出て 2.74 浮いた)・
                //   **頭の底の全幅**(頭の駒の長さ × 幅)が平ら yF の帯の中(点を含む全ての面が yF ± 0.03 ── 小さい面だけで判じない)。満たさなければ溝を頭の側で縮める。
                //   見え面の天端の線は EdoBuild.NozuraCrestCover.CrestFrontDist(天端が yF ± 0.1 の Dan の駒の割りごとの前の縁)。⚠ 欄は「023f」と名指すが、頭の脇の縁の石垣は 036f(Kado_Hokuto_1_0)── 型として全ての縁の石垣から測る。
                float keepFront = float.NaN; bool fullW = false;
                if (fl.Contains("追記 2026-10-10i")) { var m10i = System.Text.RegularExpressions.Regex.Match(fl, @"見え面の天端の線から\s*([0-9.]+)\s*以上内"); if (m10i.Success) { keepFront = float.Parse(m10i.Groups[1].Value, inv); keepIn = 0f; } fullW = fl.Contains("頭の底の全幅が平ら"); }
                var danH = new List<Vector2[]>(); var cf = new EdoBuild.NozuraCrestCover();
                if (!float.IsNaN(keepIn)) foreach (Transform dc in Group("Dan")) { if (!dc.gameObject.activeInHierarchy) continue; var p2 = new List<Vector2>(); foreach (var v in EdoBuild.Body(dc, 3000)) p2.Add(new Vector2(v.x, v.z)); if (p2.Count >= 3) danH.Add(EdoBuild.ConvexHull2(p2).ToArray());
                    if (!float.IsNaN(keepFront)) { var mfd = dc.GetComponentInChildren<MeshFilter>(); bool kd = mfd != null && mfd.sharedMesh != null && mfd.sharedMesh.name.Contains("_Kado"); try { cf.Add(dc.gameObject, kd); } catch (System.Exception) { } } }
                float headL = mp.len > 0.05f ? mp.len : 1f; float worstFront = float.PositiveInfinity; GameObject worstGo = null;
                for (; clip < Lf - 1f; clip += 0.1f)
                {
                    bool okE = true; var q0 = far + dJ * clip;
                    var qs = new List<Vector2> { q0 + pp * halfW, q0 - pp * halfW, q0 };
                    if (fullW) foreach (float tt in new[] { 0.5f * headL, headL }) foreach (float ww in new[] { -halfW, 0f, halfW }) qs.Add(q0 + dJ * tt + pp * ww);
                    foreach (var q in qs)
                    {
                        float fy = FaceYAt(fcs, q, "MizoP_"); if (float.IsNaN(fy) || Mathf.Abs(fy - yF) > 0.03f) { okE = false; break; }
                        if (fullW && !AllFacesAt(fcs, q, yF, 0.03f, "MizoP_")) { okE = false; break; }
                    }
                    if (okE && danH.Count > 0) foreach (var q in qs) foreach (var hh in danH) if (EdoGeom.PIP(hh, q) || EdoBuild.EdgeDistPublic(hh, q) < keepIn) { okE = false; break; }
                    if (okE && !float.IsNaN(keepFront)) { float wmin = float.PositiveInfinity; GameObject wg = null; foreach (var q in qs) { GameObject g0; float dq = cf.CrestFrontDist(q, yF, 0.1f, out g0); if (dq < wmin) { wmin = dq; wg = g0; } } worstFront = wmin; worstGo = wg; if (wmin < keepFront) okE = false; }
                    if (okE) break;
                }
                if (clip > 0f) sb.AppendLine("    背の雨落ちの頭を面 " + yF.ToString("F2", inv) + " の内まで " + clip.ToString("F1", inv) + "m 引いた(棟の妻の先は別の面" + (float.IsNaN(keepFront) ? "" : "・追記 10-10i: 縁の石垣の見え面の天端の線から " + (float.IsInfinity(worstFront) ? "-" : worstFront.ToString("F2", inv)) + " ≥ " + keepFront.ToString("F1", inv) + "【硬】〔" + (worstGo == null ? "-" : worstGo.name) + "〕" + (fullW ? "・頭の底の全幅 " + headL.ToString("F2", inv) + "×" + (2f * halfW).ToString("F2", inv) + " が平らの内" : "")) + ")");
                line = new List<Vector2> { far + dJ * clip, jOn }; lines.Add(line);
                }
            }
            else
            {
                // 下水が無ければ門の口に近い端 ── 門が同じ辺に在るときだけ(⛔ 別の辺の門の s をこの辺で引かない・第101巡)
                var gO = O(Get(D, "gate")); if (gO == null || (int)F(gO["edge"]) != e) { sb.AppendLine("  ★ " + nm + " 背の雨落ち(" + rn + "): 落とし先が無い(門の内の下水が建たず、門も辺 " + e + " に無い)── 置かない(普請方へ)" + (_gesui != null && _gesui.why != null ? "〔下水: " + _gesui.why + "〕" : "")); Clear(Group("BackMizo")); continue; }
                Vector2 gate = EdgePt(e, F(gO["s"])); bool down1 = Vector2.Distance(a1, gate) < Vector2.Distance(a0, gate);
                line = down1 ? new List<Vector2> { a0, a1 } : new List<Vector2> { a1, a0 }; lines.Add(line);
            }
            var grp = Group("BackMizo"); float tailMin = float.MaxValue;
            for (int li = 0; li < lines.Count; li++) {
            line = lines[li]; string sfx = lines.Count > 1 ? "_" + li : "";
            var spec = new EdoBuild.MizoSpec { chord = true, name = nm + "_" + rn + "_Amaochi" + sfx, kata = "A", line = line, groundAt = (x, z) => yF, topAbove = 0.02f,
                                                   pieceDepth = float.NaN, depthMin = dMin, depthMax = dMax, slopeMin = slope, halfW = halfW };
                var pr = EdoBuild.SolveMizoBottom(spec);
                if (li == 0) Clear(grp);
                int miss; string mw; var fail = new List<string>();
                var made = EdoBuild.LayMizo(grp, nm + "_" + rn + "_Amaochi" + sfx, pr, need => MizoAByDepth(need, spec.topAbove),
                                            out miss, out mw, (x, z) => yF, fail);
                Vector2 dn = line[line.Count - 1];
                sb.AppendLine("  背の雨落ち " + nm + " × " + rn + "(flat 追記 2026-10-10a): 石組の溝 型A " + made.Count + " 駒・" + pr.length.ToString("F1", inv) + "m・底 " + pr.Head.ToString("F3", inv) + "→" + pr.Tail.ToString("F3", inv) + "(1/" + mS.Groups[1].Value + " 硬)"
                              + (pr.worstDeep > 0.005f ? "・⚠ 深さ " + dMax.ToString("F2", inv) + " を最大 " + pr.worstDeep.ToString("F2", inv) + " 越える(柔)" : "") + (fail.Count > 0 ? "・⛔ 浮く駒 " + fail.Count + " を据えない" : "") + (miss > 0 ? "・⚠ 駒が無い " + miss : "")
                              + "・下流の端 (" + dn.x.ToString("F2", inv) + ", " + dn.y.ToString("F2", inv) + ")= " + (toJ ? "表門脇の下水の入口" : "表門に近い側"));
                tailMin = Mathf.Min(tailMin, pr.Tail);
            }
            if (toJ && tailMin < float.MaxValue) sb.Append(PlaceOmoteGesuiLay(tailMin - 0.01f));
        }
        return sb.ToString();
    }

    class SodeSlopeCheck { public string key; public List<Vector2> line; public List<Vector2> back; public float maxDiff, depth; public float sLo; }
    /// <summary>袖の坂の低い端の小口へ被せる土(指図 sodeSlope 追記 2026-10-07「その小口は高さ h・長さ len の土を 1:bf で被せて隠す」【硬】)。
    /// end = 線を延ばした低い端の点・away = 端の外へ向く走り。Stage3b が据えた端の駒の小口を実メッシュで測って皮の設計の地盤へ盛る(SodeEndCoverAt)。</summary>
    class SodeEndCover { public string key; public Vector2 end, away; public float h, len, bf, rise, flat, side, drn, buryTop = float.NaN, burySide, buryMin, buryAim = float.NaN, ceilRelax = float.NaN, faceCover = float.NaN; }

    /// <summary>**袖の坂**(指図 terraceWalls[].sodeSlope・普請方の設計 2026-10-07・EDO-0502 第41〜42巡)── 袖の天端を段にせず、背の法 + off の坂の一続きの線にする
    /// (上端 cap で頭打ち)。背の法 = 天端の前の線から背へ「天端の奥行(avoid.dodomeCrestDepthM[野面の乱積み])+ 0.25」の造成の設計面(SodeBenches と同じ)。
    /// ⭐ 第42巡(追記 2026-10-07): **出隅の踊り場** ── 折れ 30° 以上の節点の ±half を水平にし(高さ = 元の坂の線が隅を通る値)、その範囲の背の法も
    /// 天端 − drop の水平に描き直す(EdoBuild.BackBench の切り・盛り ≤ 上限【硬】)。坂の線は描き直した背から引き直す(⛔ 踊り場の脇で段を作らない)。
    /// **低い端** ── 坂の駒で天端が前の地表 + reachHi に届いた所から、水平の駒(見付 fixExp・焼いた H fixH)を一駒(⛔ 傾けて沈めない)。小口の土は Stage3b。
    /// 数は指図の文から読む(⛔ 読めなければ ★ を刷って建てない)。<paramref name="nozSegs"/> が null なら据えずに踊り場の小段と小口の土だけ返す(SodeBenches・Stage3b)。
    /// 当たる先: sodeSlope を持つ袖(岡部 TW_Kado_Sode)。</summary>
    /// <summary>**線の外へ波及した造成を造成前の地盤へ戻す**(const.perimeterRetain【硬】・第90巡)。区画の線の外 <paramref name="band"/> 以内で、他の区画の内でない(道の側の)
    /// 地形の節点のうち、造成前の地盤(base_dem)と 0.3 を超えて違う物を base_dem へ戻す。⚠ 地形の編集は Undo の外 ── 呼ぶ前に退避を取る。⟶ 戻した節点の数の報告。</summary>
    public static string RestorePerimeterSpill(float band) { using (OnKita()) return RestorePerimeterSpill_(band); }
    static string RestorePerimeterSpill_(float band) { return RestorePerimeterSpill_(band, false); }
    /// <param name="lowerOnly">盛りの波及だけを戻す(基準 = base_dem と道の線際の均し michiNarashi の低い方より 0.3 を超えて高い節点を基準へ)── 造成の後に呼ぶとき(seRoji.clipOrder・第114巡)。
    /// ⛔ 両向きで戻すと、道の線際の均しで下げた節点と、駒の下を下げた節点(基壇の見え面は区画の外)を造成前へ埋め戻す(第114巡 1062 / 593 節点)。</param>
    static string RestorePerimeterSpill_(float band, bool lowerOnly)
    {
        string pr = S(Get(O(D["const"]), "perimeterRetain")); if (pr == null || !pr.Contains("造成前の地盤")) return "  ★ const.perimeterRetain が無い ── 戻さない";
        var t = EdoBuild.T(); var td = t.terrainData; var org = t.transform.position; int R = td.heightmapResolution; float hs = td.size.x / (R - 1);
        var P = Poly; var bd = EdoBuild.BaseDem(); var mnR = MichiNarashi; var others = new List<Vector2[]>(); foreach (var pc in EdoParcels.All) if (pc.id != ParcelId && pc.pts.Count >= 3) others.Add(pc.Poly);
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue; foreach (var q in P) { x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y); }
        int i0 = Mathf.Max(0, Mathf.FloorToInt((x0 - band - org.x) / hs)), i1 = Mathf.Min(R - 1, Mathf.CeilToInt((x1 + band - org.x) / hs));
        int j0 = Mathf.Max(0, Mathf.FloorToInt((z0 - band - org.z) / hs)), j1 = Mathf.Min(R - 1, Mathf.CeilToInt((z1 + band - org.z) / hs));
        var h = td.GetHeights(i0, j0, i1 - i0 + 1, j1 - j0 + 1); int n = 0; float mx = 0f;
        for (int j = j0; j <= j1; j++)
            for (int i = i0; i <= i1; i++)
            {
                var q = new Vector2(org.x + i * hs, org.z + j * hs); if (EdoGeom.PIP(P, q) || EdoBuild.EdgeDistPublic(P, q) > band) continue;
                bool oth = false; foreach (var op in others) if (EdoGeom.PIP(op, q)) { oth = true; break; } if (oth) continue;   // 隣の区画の中は隣の造成(掲示板へ)
                float b0 = bd(q.x, q.y); if (float.IsNaN(b0)) continue; float cur = h[j - j0, i - i0] * td.size.y + org.y;
                if (lowerOnly && mnR != null) { float m0 = MichiNarashiAt(mnR, q.x, q.y); if (!float.IsNaN(m0)) b0 = Mathf.Min(b0, m0); }
                if (lowerOnly ? cur - b0 <= 0.3f : Mathf.Abs(cur - b0) <= 0.3f) continue;
                mx = Mathf.Max(mx, Mathf.Abs(cur - b0)); h[j - j0, i - i0] = (b0 - org.y) / td.size.y; n++;
            }
        if (n > 0) { td.SetHeights(i0, j0, h); UnityEditor.AssetDatabase.SaveAssetIfDirty(td); }
        return "  線の外へ波及した造成を造成前の地盤へ戻した(const.perimeterRetain【硬】・線の外 " + band.ToString("F1") + "m・道の側" + (lowerOnly ? "・盛りの波及だけ(基準 = base_dem と道の線際の均しの低い方)" : "") + "): 節点 " + n + "・最大の差 " + mx.ToString("F2");
    }
    /// <summary>指図 ends 追記 2026-10-10f【硬】(第89巡): 「突き付け」を名指す run の端が、別の run の区間の線を越えていれば交点まで縮める(EdoBuild.TrimSegToPartnerLine)──
    /// 隅の駒の天端の帯・見え面の上に駒を据えない。相手の実面への突き付けは PlaceNozuraNet の ③(1.5m 以内の据わった駒)。</summary>
    static string TrimRunsToPartners(List<EdoBuild.NozuraSeg> segs)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var pre = new List<string>();
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
        {
            var t2 = O(o2); string n2 = S(Get(t2, "name")); string en = S(Get(t2, "ends")) ?? ""; int i10f = en.IndexOf("追記 2026-10-10f");
            if (n2 != null && i10f >= 0 && en.Substring(i10f).Contains("突き付け")) pre.Add(n2 + "_");
        }
        if (pre.Count == 0) return "";
        System.Func<string, string> runOf = nm => System.Text.RegularExpressions.Regex.Replace(nm, @"_[0-9]+(f)?$", "");
        int n = 0;
        foreach (var sg in segs)
        {
            if (!pre.Exists(x => sg.name.StartsWith(x))) continue;
            for (int e = 0; e < 2; e++)
            {
                Vector2 ep = e == 1 ? sg.b : sg.a; float best = 0f; EdoBuild.NozuraSeg bo = null;
                foreach (var ot in segs)
                {
                    if (ot == sg || runOf(ot.name) == runOf(sg.name)) continue;
                    // 端の近く(2m)を通る別の run の区間だけ
                    Vector2 od = ot.b - ot.a; float oL = od.magnitude; if (oL < 1e-3f) continue; od /= oL; float uu = Mathf.Clamp(Vector2.Dot(ep - ot.a, od), 0f, oL);
                    if (Vector2.Distance(ot.a + od * uu, ep) > 2f) continue;
                    var tmp = new EdoBuild.NozuraSeg { name = sg.name, a = sg.a, b = sg.b, crestAt = sg.crestAt };
                    float cut = EdoBuild.TrimSegToPartnerLine(tmp, e, ot); if (cut > best) { best = cut; bo = ot; }
                }
                if (bo == null) continue;
                EdoBuild.TrimSegToPartnerLine(sg, e, bo); n++;
                sb.AppendLine("    突き付けの前に縮めた(ends 追記 2026-10-10f): " + sg.name + " 端" + e + " を " + best.ToString("F2", inv) + "m(" + bo.name + " の線まで)");
            }
        }
        return "  相手の区間の線を越えて据えない(ends 追記 2026-10-10f【硬】): 縮めた端 " + n + "\n" + sb;
    }
    /// <summary>指図 cuts 追記 2026-10-10f【硬】(第89巡): 「〜が切る口の両端は見切り石で納め、隅の駒を口に置かない」── その欄の run の区間の端のうち、名指しの石段の駒から 1.5m 以内の端に見切り石を名指す(mikiriTo = 石段の駒)。</summary>
    static string CutEndsMikiri(List<EdoBuild.NozuraSeg> segs)
    {
        var sb = new System.Text.StringBuilder(); int n = 0; var root = GameObject.Find(GN);
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
        {
            var t2 = O(o2); string n2 = S(Get(t2, "name")); string ct = S(Get(t2, "cuts")) ?? ""; int i10f = ct.IndexOf("追記 2026-10-10f");
            if (n2 == null || i10f < 0 || !ct.Substring(i10f).Contains("見切り石")) continue;
            { int i10o = ct.IndexOf("追記 2026-10-10o"); if (i10o >= 0 && ct.Substring(i10o).Contains("取り消して置き換える")) { sb.AppendLine("    口の端の見切り石(cuts 10-10f)は 10-10o で取り消し ── " + n2 + " の口の端は袖の外の面へ(SodesBeforeNet)"); continue; } }
            var mK = System.Text.RegularExpressions.Regex.Match(ct.Substring(i10f), @"(K_[A-Za-z0-9]+)\s*が切る口"); if (!mK.Success || root == null) { sb.AppendLine("    ★ " + n2 + " cuts 追記 2026-10-10f: 石段の名が読めない"); continue; }
            var steps = new List<GameObject>(); foreach (var r in root.GetComponentsInChildren<MeshRenderer>()) if (r.name.StartsWith(mK.Groups[1].Value + "_")) steps.Add(r.gameObject);
            if (steps.Count == 0) { sb.AppendLine("    ★ " + n2 + " cuts 追記 2026-10-10f: 石段 " + mK.Groups[1].Value + " が据わっていない"); continue; }
            var bb = new List<Bounds>(); foreach (var g in steps) bb.Add(EdoBuild.RB(g));
            foreach (var sg in segs)
            {
                if (!sg.name.StartsWith(n2 + "_")) continue;
                for (int e = 0; e < 2; e++)
                {
                    Vector2 ep = e == 1 ? sg.b : sg.a; bool near = false;
                    foreach (var b in bb) { var c2 = new Vector2(Mathf.Clamp(ep.x, b.min.x, b.max.x), Mathf.Clamp(ep.y, b.min.z, b.max.z)); if (Vector2.Distance(c2, ep) <= 1.5f) { near = true; break; } }
                    if (!near || sg.mikiriTo[e] != null) continue;
                    sg.mikiriTo[e] = new List<GameObject>(steps); n++;
                    sb.AppendLine("    口の端を見切り石で(cuts 追記 2026-10-10f): " + sg.name + " 端" + e + "(" + mK.Groups[1].Value + ")");
                }
            }
        }
        return n == 0 && sb.Length == 0 ? "" : "  石段の口の両端は見切り石(cuts 追記 2026-10-10f【硬】): " + n + " 端\n" + sb;
    }
    /// <summary>指図 sideEnd・sodeSlope 追記 2026-10-10d【硬】の打ち切り(第87巡)── 欄が「flat の帯の中に駒を置かない」を持つ run(sodeSlope = 欄の名・sideEnd = 欄の名 + "_SideEnd")の区間を、
    /// 天端が前の地表より低くなった所で切り、それより低い端の側の区間は置かない。</summary>
    static string TrimRunsBelowFront(List<EdoBuild.NozuraSeg> segs)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture; var pre = new List<string>();
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
        {
            var t2 = O(o2); string n2 = S(Get(t2, "name")); if (n2 == null) continue;
            string ss = S(Get(t2, "sodeSlope")) ?? "", se = S(Get(t2, "sideEnd")) ?? "";
            if (ss.Contains("追記 2026-10-10d") && ss.Contains("帯の中に駒を置かない")) pre.Add(n2 + "_");
            if (se.Contains("追記 2026-10-10d") && se.Contains("帯の中に駒を置かない")) pre.Add(n2 + "_SideEnd");
        }
        // 指図 terraceWalls[].ends 追記 2026-10-10p(第98巡の差し戻し): 10-10o の「前の地表が天端 −m に届いた所で終える」は置き換えられた ──『前の地表 ≤ 天端』は検査として刷るだけ(切らない)。
        //   前の地表 = 見え面の 0.6 前(平らな面の内なら面の高さ・外なら設計の地盤 SkinGround)を走りに沿って 0.25 刻み。当たる先: ends に 10-10p の検査の文を持つ欄(岡部 TW_Nishi_Kado 辺24)。
        var chk = new List<string>();
        foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
        {
            var t2 = O(o2); string n2 = S(Get(t2, "name")); string en = S(Get(t2, "ends")) ?? ""; int i10p = en.IndexOf("追記 2026-10-10p"); if (n2 == null || i10p < 0) continue;
            if (!en.Substring(i10p).Contains("『前の地表 ≤ 天端』は検査として残す")) continue;
            var mP = System.Text.RegularExpressions.Regex.Match(en.Substring(0, i10p), @"(辺[0-9]+)\s*の run は、前の地表が天端");
            chk.Add(n2 + "_" + (mP.Success ? mP.Groups[1].Value + "_" : ""));
        }
        if (pre.Count == 0 && chk.Count == 0) return "";
        var flats = FlatFacesOf(new HashSet<GameObject>(), new System.Text.StringBuilder());
        foreach (var sg in segs)
        {
            if (!chk.Exists(x => sg.name.StartsWith(x))) continue;
            var tv = (sg.b - sg.a); if (tv.sqrMagnitude < 1e-6f) continue; float L = tv.magnitude; tv /= L; var nv = new Vector2(-tv.y, tv.x);
            Vector2 mid = (sg.a + sg.b) * 0.5f; Vector2 f = sg.face.sqrMagnitude > 0.5f ? sg.face.normalized : (SkinGround(mid.x + nv.x * 0.6f, mid.y + nv.y * 0.6f) < SkinGround(mid.x - nv.x * 0.6f, mid.y - nv.y * 0.6f) ? nv : -nv);
            float worst = float.MinValue, at = 0f; int over = 0, n0 = 0;
            for (float sl = 0f; sl <= L + 1e-3f; sl += 0.25f)
            {
                var fp = sg.a + tv * sl + f * 0.6f; float fy = float.NaN; foreach (var ff in flats) if (ff.poly != null && EdoGeom.PIP(ff.poly, fp)) { fy = ff.y; break; } if (float.IsNaN(fy)) fy = SkinGround(fp.x, fp.y);
                float dd = fy - sg.crestAt(sl); n0++; if (dd > 0f) over++; if (dd > worst) { worst = dd; at = sl; }
            }
            sb.AppendLine("    検査 前の地表 ≤ 天端(ends 追記 2026-10-10p): " + sg.name + " ── 前の地表 − 天端 最大 " + worst.ToString("+0.00;-0.00", inv) + " @走り " + at.ToString("F2", inv) + "・越える点 " + over + "/" + n0 + (over > 0 ? " ⛔" : " ⭕"));
        }
        if (pre.Count == 0) return sb.ToString();
        var drop = new HashSet<EdoBuild.NozuraSeg>(); int nCut = 0, nDrop = 0;
        foreach (var sg in segs)
        {
            string pf = pre.Find(x => sg.name.StartsWith(x) && (x.EndsWith("_SideEnd") || !sg.name.Contains("_SideEnd"))); if (pf == null) continue;
            var tv = (sg.b - sg.a); if (tv.sqrMagnitude < 1e-6f) continue; tv.Normalize(); var nv = new Vector2(-tv.y, tv.x);
            Vector2 mid = (sg.a + sg.b) * 0.5f; Vector2 f = sg.face.sqrMagnitude > 0.5f ? sg.face.normalized : (SkinGround(mid.x + nv.x * 0.6f, mid.y + nv.y * 0.6f) < SkinGround(mid.x - nv.x * 0.6f, mid.y - nv.y * 0.6f) ? nv : -nv);
            System.Func<Vector2, float> front = q => { var fp = q + f * 0.6f; foreach (var ff in flats) if (ff.poly != null && EdoGeom.PIP(ff.poly, fp)) return ff.y; return SkinGround(fp.x, fp.y); };
            float cut; int r = EdoBuild.TrimSegBelowFront(sg, front, out cut);
            if (r == 0) continue;
            if (r == 2) { drop.Add(sg); nDrop++; } else nCut++;
            sb.AppendLine("    打ち切り(追記 2026-10-10d): " + sg.name + (r == 2 ? " を置かない" : " を走り " + cut.ToString("F2", inv) + " で切った") + "(天端 < 前の地表)");
        }
        segs.RemoveAll(x => drop.Contains(x));
        return "  天端が前の地表より低い所に駒を置かない(sideEnd・sodeSlope 追記 2026-10-10d【硬】): 切った区間 " + nCut + "・置かない区間 " + nDrop + "\n" + sb;
    }
    /// <summary>指図 roadEdge・cuts 追記 2026-10-10h の見切り石の背の土 ── 0: 頭より下げる量・1: 平らの幅(一間 = ken)・2: 先の法 1:n。読めなければ NaN。</summary>
    static float MikiriSoil(int which)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var all3 = new List<object>(A(Get(D, "terraces")) ?? new List<object>()); all3.AddRange(A(Get(D, "terraceWalls")) ?? new List<object>());
        foreach (var o3 in all3) { var t3 = O(o3); foreach (var key3 in new[] { "roadEdge", "cuts" })
        {
            string tx = S(Get(t3, key3)) ?? ""; int i = tx.IndexOf("追記 2026-10-10h"); if (i < 0) continue; string t = tx.Substring(i);
            var m0 = System.Text.RegularExpressions.Regex.Match(t, @"頭より\s*([0-9.]+)\s*以上低く"); var m2 = System.Text.RegularExpressions.Regex.Match(t, @"先は\s*1\s*:\s*([0-9.]+)");
            if (!m0.Success) continue;
            if (which == 0) return float.Parse(m0.Groups[1].Value, inv);
            if (which == 1) return t.Contains("一間を平らに") ? C("ken") : float.NaN;
            if (which == 2) return m2.Success ? float.Parse(m2.Groups[1].Value, inv) : float.NaN;
        } }
        return float.NaN;
    }
    /// <summary>指図 const.fillEdgeSlope「盛りの縁は 1:n より急にしない【硬】」の n(読めなければ NaN と ★)。当たる先: Stage3b の皮の設計の狙い(EdoBuild.SkinHeightSolve の 4a)。</summary>
    /// <summary>指図 const.toeBand(普請方 2026-10-10o・第97巡)── 0: 見え面の前の帯の幅・1: 法尻からの上限。読めなければ NaN(掛けない)。</summary>
    static float ToeBand(System.Text.StringBuilder sb, int which)
    {
        string t = S(Get(O(D["const"]), "toeBand")); if (t == null) return float.NaN;
        var mW = System.Text.RegularExpressions.Regex.Match(t, @"見え面の前\s*([0-9.]+)\s*を法尻の高さで平ら"); var mR = System.Text.RegularExpressions.Regex.Match(t, @"法尻\s*\+\s*([0-9.]+)\s*より上へ出さない");
        if (!mW.Success || !mR.Success) { if (sb != null) sb.AppendLine("  ★ const.toeBand: 帯の幅・法尻からの上限が指図から読めない ── 掛けない"); return float.NaN; }
        var inv = System.Globalization.CultureInfo.InvariantCulture; float w = float.Parse(mW.Groups[1].Value, inv), r = float.Parse(mR.Groups[1].Value, inv);
        if (sb != null) sb.AppendLine("  石垣の足元の帯(const.toeBand 10-10o): 見え面の前 " + w.ToString("F2", inv) + " を法尻の高さで平ら・上限 法尻 +" + r.ToString("F2", inv) + "【硬】・区画の外は今の地形");
        return which == 0 ? w : r;
    }
    /// <summary>指図 const.toeBand 追記 2026-10-10p(普請方・第98巡の差し戻し)の背の押さえ ── 0: 法尻の線から背への近い帯(法尻 + 上限)・1: 遠い帯の端・2: 天端からの下げ。
    /// 読めなければ NaN(掛けない)。当たる先: EdoBuild.SkinHeightSolve の足元の帯の背(第100巡)。</summary>
    static float ToeBandBack(System.Text.StringBuilder sb, int which)
    {
        string t = S(Get(O(D["const"]), "toeBand")); if (t == null) return float.NaN; int i = t.IndexOf("追記 2026-10-10p"); if (i < 0) return float.NaN; t = t.Substring(i);
        var mN = System.Text.RegularExpressions.Regex.Match(t, @"法尻の線から背へ\s*([0-9.]+)\s*以内の点は法尻\s*\+\s*[0-9.]+\s*以下");
        var mF = System.Text.RegularExpressions.Regex.Match(t, @"([0-9.]+)\s*〜\s*([0-9.]+)\s*の点は『天端\s*[−\-]\s*([0-9.]+)』と");
        if (!mN.Success || !mF.Success) { if (sb != null) sb.AppendLine("  ★ const.toeBand 追記 2026-10-10p: 背の押さえの帯・天端からの下げが指図から読めない ── 背は押さえない"); return float.NaN; }
        var inv = System.Globalization.CultureInfo.InvariantCulture; float n = float.Parse(mN.Groups[1].Value, inv), f = float.Parse(mF.Groups[2].Value, inv), d = float.Parse(mF.Groups[3].Value, inv);
        if (sb != null) sb.AppendLine("  足元の帯の背の押さえ(const.toeBand 10-10p【硬】): 法尻の線から背へ " + n.ToString("F2", inv) + " 以内は法尻 + 上限・〜" + f.ToString("F2", inv) + " は天端 −" + d.ToString("F2", inv) + " と勾配なりの低い方");
        return which == 0 ? n : which == 1 ? f : d;
    }
    static float FillEdgeSlope(System.Text.StringBuilder sb)
    {
        string t = S(Get(O(D["const"]), "fillEdgeSlope")); if (t == null) return float.NaN;
        var m = System.Text.RegularExpressions.Regex.Match(t, @"1\s*:\s*([0-9.]+)\s*より急にしない");
        if (!m.Success) { if (sb != null) sb.AppendLine("  ★ const.fillEdgeSlope: 指図から読めない ── 盛りの縁の法を掛けない"); return float.NaN; }
        float n = float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
        if (sb != null) sb.AppendLine("  盛りの縁の法(const.fillEdgeSlope): 1:" + n.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture) + " より急にしない【硬】── 皮の設計の狙い y* へ");
        return n;
    }
    /// <summary>**延長の背の法の行き先の検め**(指図 TW_Kado_Shumen.sideEnd 追記 2026-10-10b【硬】・第81巡)。小段の先を上限なしで切る法(cutBenchOnly)が
    /// 地山に交わるまでに、区画の線の外(= 道)か建物の座(Kakoi・Buildings の躯体の凸包)へ入るなら、その名を返す(入らなければ null)。
    /// 測り = 設計の地盤 DesignY を今の地盤として BackBenchesAt で切る点(0.25m 格子・区画で頭打ちしない写し)。当たる先: cutBenchOnly を立てる小段すべて。</summary>
    static string SideEndSlopeHits(List<EdoBuild.BackBench> ks)
    {
        if (ks == null || ks.Count == 0) return null;
        var free = new List<EdoBuild.BackBench>();
        foreach (var k in ks) free.Add(new EdoBuild.BackBench { name = k.name, a = k.a, b = k.b, back = k.back, top = k.top, drop = k.drop, w = k.w, drain = k.drain, bf = k.bf, maxFill = k.maxFill,
                                                               maxCut = k.maxCut, baseAt = k.baseAt, drainAlong = k.drainAlong, keepOut = k.keepOut, noEndSpill = k.noEndSpill, tuckB = k.tuckB, cutBenchOnly = true, parcel = null });
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var k in ks) foreach (var q in new[] { k.a, k.b }) { x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y); }
        const float R = 9f; x0 -= R; x1 += R; z0 -= R; z1 += R;
        var hulls = new List<KeyValuePair<string, Vector2[]>>(); var root = GameObject.Find(GN);
        if (root != null)
            foreach (var gn in new[] { "Kakoi", "Buildings" })
            {
                var g = root.transform.Find(gn); if (g == null) continue;
                foreach (Transform c in g)
                {
                    if (!c.gameObject.activeInHierarchy) continue; var b = EdoBuild.RB(c.gameObject);
                    if (b.max.x < x0 || b.min.x > x1 || b.max.z < z0 || b.min.z > z1) continue;
                    var pts = new List<Vector2>(); foreach (var v in EdoBuild.Body(c, 4000)) pts.Add(new Vector2(v.x, v.z)); if (pts.Count < 3) continue;
                    hulls.Add(new KeyValuePair<string, Vector2[]>(c.name, EdoBuild.ConvexHull2(pts).ToArray()));
                }
            }
        for (float x = x0; x <= x1; x += 0.25f)
            for (float z = z0; z <= z1; z += 0.25f)
            {
                var q = new Vector2(x, z); float cur = DesignY(q); if (float.IsNaN(cur)) continue;
                if (EdoBuild.BackBenchesAt(free, q, cur) > cur - 0.01f) continue;   // 切らない点
                if (!EdoGeom.PIP(Poly, q)) return "区画の線(道) @(" + x.ToString("F1") + ", " + z.ToString("F1") + ")";
                foreach (var h in hulls) if (EdoGeom.PIP(h.Value, q)) return "建物の座 " + h.Key + " @(" + x.ToString("F1") + ", " + z.ToString("F1") + ")";
            }
        return null;
    }

    /// <summary>sideEnd の延長の背の小段(第74巡)── StairGaps(Stage2b)が作り、SodeBenches(Stage3b の設計の地盤)が読む。</summary>
    static readonly List<EdoBuild.BackBench> _sideEndBenches = new List<EdoBuild.BackBench>();
    static string SodeSlopeSegs(string key, List<Vector2> nodes, string txt, List<EdoBuild.NozuraSeg> nozSegs, List<SodeSlopeCheck> chk,
                                List<EdoBuild.BackBench> landOut = null, List<SodeEndCover> coverOut = null, bool skipOwnLanding = false, float sinkEndOverride = float.NaN, float[] endGrades = null, float endReach = float.NaN)
    {
        // endGrades(第78巡・指図 sideEnd 追記 2026-10-09j【硬】): 線の低い端の先に勾配の駒(m あたり endGrades[k])を一駒ずつ足し、天端が前の地表 + endReach 以下になったら水平の駒で納める
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
        // 追記 2026-10-10e(第87巡): 埋める土は天端 + h 以上【硬】・+ a を狙う【柔】・隣の駒の天端の前の帯の天井を最大 r 緩める【硬】(後の追記が勝つ)
        float buryAim = float.NaN, ceilRelax = float.NaN, faceCover = float.NaN;
        { int i10f = (txt ?? "").IndexOf("追記 2026-10-10f"); if (i10f >= 0) { var mf = System.Text.RegularExpressions.Regex.Match(txt.Substring(i10f), @"見え面の根元を最大\s*([0-9.]+)\s*まで被って"); if (mf.Success) faceCover = float.Parse(mf.Groups[1].Value, inv); else sb.AppendLine("  ★ " + key + " sodeSlope 追記 2026-10-10f: 指図から読めない(見え面の根元を被る高さ)"); } }
        { int i10e = (txt ?? "").IndexOf("追記 2026-10-10e"); if (i10e >= 0) { string t10e = txt.Substring(i10e);
            var m1 = System.Text.RegularExpressions.Regex.Match(t10e, @"埋める土は天端\s*\+\s*([0-9.]+)\s*以上"); var m2 = System.Text.RegularExpressions.Regex.Match(t10e, @"\+\s*([0-9.]+)\s*を狙う"); var m3 = System.Text.RegularExpressions.Regex.Match(t10e, @"天井を最大\s*([0-9.]+)\s*緩め");
            if (m1.Success && m2.Success && m3.Success) { buryMin = float.Parse(m1.Groups[1].Value, inv); buryAim = float.Parse(m2.Groups[1].Value, inv); ceilRelax = float.Parse(m3.Groups[1].Value, inv); }
            else sb.AppendLine("  ★ " + key + " sodeSlope 追記 2026-10-10e: 指図から読めない(下限・狙い・緩め)── 前の下限のまま"); } }
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
        float cEnd0 = float.NaN; var endKnots = new List<Vector2>();   // (道のり, 天端) ── endGrades の折れ
        if (endGrades != null && endGrades.Length > 0)
        {
            cEnd0 = line0(sEnd0); float cc = cEnd0, dd = 0f; endKnots.Add(new Vector2(0f, cc));
            foreach (var g in endGrades)
            {
                dd += W; cc -= g * W; endKnots.Add(new Vector2(dd, cc));
                var pb = pAt(sEnd0 + sgn * dd); float fr = SkinGround(pb.Key.x - pb.Value.x * 0.5f, pb.Key.y - pb.Value.y * 0.5f);
                if (!float.IsNaN(fr) && cc <= fr + endReach + 1e-3f) break;
            }
            E1 = dd;
        }
        else if (!float.IsNaN(sinkEndOverride)) E1 = 0f;   // 打ち切りの条件を当てない(延ばさない)
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
        float sE1 = sEnd0 + sgn * E1, cE1 = endKnots.Count > 1 ? endKnots[endKnots.Count - 1].y : line0(sE1);
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
        { var pe = pAt(sEnd0 + sgn * Ext); var pa = pAt(sEnd0); coverOut.Add(new SodeEndCover { key = key, end = pe.Key, away = (pe.Key - pa.Key).normalized * (Vector2.Distance(pe.Key, pa.Key) > 1e-3f ? 1f : 0f), h = cvH, len = cvL, bf = cvBf, rise = cvRise, flat = cvFlat, side = cvSide, drn = float.IsNaN(cvDrn) ? 0f : 1f / cvDrn, buryTop = buryTop, burySide = burySide, buryMin = buryMin, buryAim = buryAim, ceilRelax = ceilRelax, faceCover = faceCover }); }
        if (dry) { if (endBenchNote != null) sb.AppendLine("    " + endBenchNote); return sb.ToString(); }
        System.Func<float, float> crest = s1 =>
        {
            if (sgn < 0f ? s1 < sE1 : s1 > sE1) return flatEnd ? cFlat : cE1 - gMax * Mathf.Abs(s1 - sE1);
            float v = line0(s1);
            if (endKnots.Count > 1 && (sgn < 0f ? s1 < sEnd0 : s1 > sEnd0))
            {   // 勾配の駒で下ろす区間(endGrades)── 折れの間を一次
                float dd = Mathf.Abs(s1 - sEnd0); v = endKnots[endKnots.Count - 1].y;
                for (int k = 0; k + 1 < endKnots.Count; k++) if (dd <= endKnots[k + 1].x) { v = Mathf.Lerp(endKnots[k].y, endKnots[k + 1].y, (dd - endKnots[k].x) / Mathf.Max(endKnots[k + 1].x - endKnots[k].x, 1e-4f)); break; }
            }
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
    /// <summary>点 q を含む全ての面(名が skipPrefix で始まる物を除く)が y ± tol か(一つも含まなければ false)── 頭の底の全幅が平らの帯の中かの検め(第92巡)。</summary>
    static bool AllFacesAt(List<EdoBuild.SkinFace> faces, Vector2 q, float y, float tol, string skipPrefix)
    {
        int n = 0;
        foreach (var f in faces)
        {
            if (f.poly == null || (skipPrefix != null && f.name != null && f.name.StartsWith(skipPrefix)) || !EdoGeom.PIP(f.poly, q)) continue;
            if (Mathf.Abs(f.y - y) > tol) return false; n++;
        }
        return n > 0;
    }

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
        { var srp = SeRoji(); if (srp.ok) { faces.AddRange(srp.faces); if (sb != null) sb.AppendLine("  面 背の路地 " + srp.faces.Count + "(0.5m ごと・床の縦断)"); } }
        foreach (var tr in BackTrenches(null))
        {
            float L = Vector2.Dot(tr.far - tr.stop, tr.along) + tr.off;
            // ⭐ 郭の側の端は溝の底の高さのまま開け、土の面を作らない【硬】(指図 return<棟> 追記 2026-10-09h・第76巡)── 溝の帯を、帯の芯の設計の地盤(graded)が
            //   溝の底 + 0.05 以下になる所まで長手へ延ばす(郭の面の縁まで)。届かなければ ⚠ で元の長さ。
            float ext = float.NaN; string openNote = "";
            { int iR = -1; foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>()) { var t2 = O(o2); if (t2 != null && S(Get(t2, "name")) == tr.wall) { string rv = S(Get(t2, "return" + tr.run)); if (rv != null && rv.Contains("溝の底の高さのまま開け")) iR = 1; } }
              if (iR > 0)
              {
                  for (float tt = 0f; tt <= 15f + 1e-3f; tt += 0.25f) { var qc = tr.stop + tr.along * (L + tt) + tr.yard * (tr.off * 0.5f); float gy = Graded.At(qc.x, qc.y); if (!float.IsNaN(gy) && gy <= tr.y + 0.05f) { ext = tt; break; } }
                  if (float.IsNaN(ext)) openNote = "・⚠ 郭の側の端: 15m 延ばしても設計の地盤が溝の底に届かない ── 開けない"; else { L += ext; openNote = "・郭の側の端を溝の底のまま " + ext.ToString("F2") + "m 延ばして開けた(追記 2026-10-09h)"; }
              } }
            Vector2 st0 = tr.stop - tr.along * tr.pre; Vector2 p0 = st0 - tr.yard * tr.front, p1 = tr.stop - tr.yard * tr.front + tr.along * L, p2 = tr.stop + tr.along * L + tr.yard * tr.off, p3 = st0 + tr.yard * tr.off;
            faces.Add(new EdoBuild.SkinFace("Mizo_" + tr.run, new[] { p0, p1, p2, p3 }, tr.y));
            if (sb != null) sb.AppendLine("  面 溝 " + tr.run + "(" + tr.y.ToString("F2") + "): 返しと背の間 " + L.ToString("F2") + "×" + (tr.off + 0.30f).ToString("F2") + "m" + openNote);
            // ⭐ 返しの背の平ら(Kadonouchi.flat 追記 2026-10-10p【硬】: 平らの輪郭は返しの石垣の天端の背の線で止める ── 返しの実の線は実メッシュの背から解く・指図の輪郭は目安【柔】・第103巡)。
            //   指図の輪郭の返しの線(目安)と実の返しの間を、高い側の面(欄 hi)の高さの平らで埋める ── 帯 = 返しの線(X→P0)から庭へ一間 + 1。石垣の上へ出る分は皮の 10-10f の止めが天端の背の線で切る。
            //   当たる先: return<棟> で棟の背へ返す段の土留め(岡部 TW_Kado_Hokuto × N39_1)。
            if (!tr.standalone && tr.nodes != null && tr.nodes.Count >= 3)
            {
                Vector2 X = tr.nodes[tr.nodes.Count - 3], P0r = tr.nodes[tr.nodes.Count - 2]; float hiY = float.NaN; string hiN = null;
                foreach (var o3 in A(Get(IMPL, "terraceWalls")) ?? new List<object>()) { var w3 = O(o3); if (w3 != null && S(Get(w3, "name")) == tr.wall) hiN = S(Get(w3, "hi")); }
                foreach (var o3 in A(D["terraces"]) ?? new List<object>()) { var t3 = O(o3); if (t3 != null && hiN != null && S(Get(t3, "name")) == hiN) hiY = F(Get(t3, "y")); }
                float bw = tr.off + 1f;
                if (!float.IsNaN(hiY) && Vector2.Distance(X, P0r) > 0.3f)
                {
                    faces.Add(new EdoBuild.SkinFace("KaeshiSe_" + tr.run, new[] { P0r, X, X + tr.yard * bw, P0r + tr.yard * bw }, hiY));
                    if (sb != null) sb.AppendLine("  面 返しの背 " + tr.run + "(" + hiN + " " + hiY.ToString("F2") + "): 返しの線 " + Vector2.Distance(X, P0r).ToString("F2") + "m から庭へ " + bw.ToString("F2") + "m(輪郭の目安の線との間を平らに ── 10-10p)");
                }
                else if (sb != null) sb.AppendLine("  ★ 面 返しの背 " + tr.run + ": 高い側の面の高さが読めない ── 足さない");
            }
        }
        // ⭐ 棟の台(指図 terraceWalls[].dai<棟>「台とその前の帯の中を y±e に切り」【硬】・普請方 2026-10-10b・EDO-0502 第81巡)── 台 = 据えた棟の躯体の凸包、
        //   前の帯 = 背の雨落ちの外の縁まで(背の面から型 A の溝の幅 + 0.04 ── 実測の駒の幅)。台の外は面の外の法(OutsideY)で受ける。⛔ 読めなければ ★。
        {
            var rootD = GameObject.Find(GN);
            foreach (var o2 in A(Get(D, "terraceWalls")) ?? new List<object>())
            {
                var t2 = O(o2); if (t2 == null) continue;
                foreach (var kv in t2)
                {
                    if (!kv.Key.StartsWith("dai") || kv.Key.Length <= 3) continue; string rn = kv.Key.Substring(3), tx = S(kv.Value) ?? "";
                    var mD = System.Text.RegularExpressions.Regex.Match(tx, @"台とその前の帯の中を\s*([0-9.]+)\s*±\s*([0-9.]+)\s*に切");
                    int ri = -1; for (int k = 0; k < Runs.Length; k++) if (Runs[k].name == rn) ri = k;
                    var nb = rootD == null ? null : rootD.transform.Find("Kakoi/" + rn);
                    string p0 = EdoBuild.AssetByName("Own", "DoiMizo", "A", 0.15f); var mp = p0 == null ? null : EdoBuild.MizoPieceOf(p0);
                    if (!mD.Success || ri < 0 || nb == null || mp == null || !mp.ok) { if (sb != null) sb.AppendLine("  ★ 面 台 " + rn + ": 指図か棟か溝の駒が読めない ── 面にしない"); continue; }
                    float yD = float.Parse(mD.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
                    Vector2 yardD = -OutNormal(Runs[ri].edge); float bandW = (mp.xMax - mp.xMin) + 0.04f;
                    var pts = new List<Vector2>(); foreach (var v in EdoBuild.Body(nb, 4000)) pts.Add(new Vector2(v.x, v.z)); if (pts.Count < 3) continue;
                    // 前の帯: 背の面(yard の向きで最も前の点の線)から bandW
                    float dMax = float.MinValue; foreach (var q in pts) dMax = Mathf.Max(dMax, Vector2.Dot(q, yardD));
                    var all = new List<Vector2>(pts); foreach (var q in pts) if (Vector2.Dot(q, yardD) > dMax - 0.5f) all.Add(q + yardD * (dMax - Vector2.Dot(q, yardD) + bandW));
                    // 第83巡【硬】: 道の側の腰石垣(roadEdge)の天端の前の線より外へ台の面を出さない ── 面が門長屋の表(線の内 0.36)まで 16.50 で出て、石垣の見え面の上へ
                    //   0.8 の土の帯を被せた(r82_omotemon_soto)。棟の躯体の点を天端の前の線へ寄せてから凸包を取る
                    if (_road == null) _road = RoadEdgePlanOf();
                    if (_road != null && _road.ok && _road.host == nb)
                        for (int qi = 0; qi < all.Count; qi++) { float dO = Vector2.Dot(all[qi] - _road.ea, _road.outN); if (dO > -_road.setback) all[qi] -= _road.outN * (dO + _road.setback); }
                    // roadEdge 追記 2026-10-10k【硬】「台は妻の線を石で受ける」── 台の面を妻の面の石垣の天端の前の線より隣の棟の側へ出さない(棟の躯体が隣の棟へ 0.62 入り込み、
                    //   凸包が石垣の見え面の上と隣の棟の下へ 16.50 を引いて土の法 1:1.5 が隣の棟を埋めた ── 第93巡 r93_tsuma)
                    if (_road != null && _road.ok && _road.host == nb && _road.k10 && !float.IsNaN(_road.sCorner))
                    {   float sg = _road.gable > _road.Mid ? 1f : -1f;
                        for (int qi = 0; qi < all.Count; qi++) { float sO = Vector2.Dot(all[qi] - _road.ea, _road.ax); if (sg * (sO - _road.sCorner) > 0f) all[qi] -= _road.ax * (sO - _road.sCorner); } }
                    var hull = EdoBuild.ConvexHull2(all).ToArray();
                    faces.Add(new EdoBuild.SkinFace("Dai_" + rn, hull, yD));
                    if (sb != null) sb.AppendLine("  面 台 " + rn + "(" + yD.ToString("F2") + "・dai" + rn + "): 躯体の凸包 + 前の帯 " + bandW.ToString("F2") + "m");
                }
            }
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
        // ⭐ 溝の駒の中は溝の底(実測の床 −0.02)の面(第81巡【硬】)── 溝を皮の部材に入れても、皮は駒の外形を抜かずに面の高さ 16.50 で溝の上を渡り、
        //   溝の中を覆った(第81巡の一回目: 皮が溝の天端に被る 41 点・最大 0.133)。駒の外形の矩形を面にして、皮を溝の底へ下ろす(面積が小さいので勝つ)。
        //   当たる先: 皮のある邸で皮より先に据える溝(岡部 BackMizo・OmoteGesui)。蓋の駒(_Futa)は除く。
        {
            var rootM = GameObject.Find(GN); int nM = 0; float innerHalfMizo = 0f;
            foreach (var o9 in A(Get(D, "terraces")) ?? new List<object>()) { var mI = System.Text.RegularExpressions.Regex.Match(S(Get(O(o9), "flat")) ?? "", @"浅い石組の溝[(（]\s*幅\s*([0-9.]+)"); if (mI.Success) innerHalfMizo = 0.5f * float.Parse(mI.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture); }
            //   ⭐ 前の下水溝(DrainMizo)・台の前の溝(SecMizo)も同じ(第109巡【硬】)── 入れていなかったので皮が Mizo_Kita / Minami / Hashi の全長で溝の中を覆い
            //   (溝の中の描かれた地表 − 溝の底 最大 +0.49・906/1905 点)、道から見て溝が土に埋まった。縁の外の帯は区画の内だけ(縁石の作りの外の壁は道より 0.3〜0.45 上 ──
            //   線の外へ帯を出すと道の上に土の棚が立つ)。
            foreach (var gm in new[] { "BackMizo", "OmoteGesui", "FrontMizo", "DrainMizo", "SecMizo" })
            {
                var gT = rootM == null ? null : rootM.transform.Find(gm); if (gT == null) continue;
                foreach (Transform c in gT)
                {
                    if (!c.gameObject.activeInHierarchy || c.name.Contains("_Futa")) continue;
                    var mf = c.GetComponentInChildren<MeshFilter>(); string ap = mf == null || mf.sharedMesh == null ? null : AssetDatabase.GetAssetPath(mf.sharedMesh); if (ap == null) continue;
                    var mp = EdoBuild.MizoPieceOf(ap); if (mp == null || !mp.ok) continue;
                    // 内 = 溝の内法(指図 flat「浅い石組の溝(幅 w」の半分)を溝の底 −0.02 / 外 = 駒の外形 + 0.13(皮の格子 0.25 の半ば)を天端 −0.02(第82巡【硬】:
                    //   溝の縁の石の上に皮の節点が残り、縁に 0.156 被った ── 縁の外の帯も天端の下へ下げて皮を縁の石の下へ潜らせる)
                    float inH = innerHalfMizo > 0f ? Mathf.Min(innerHalfMizo, mp.halfW) : mp.halfW; const float RING = 0.13f;
                    System.Func<float, float, float, Vector3> wp = (x, y, z) => c.TransformPoint(new Vector3(x, y, z));
                    var i0 = wp(-inH, mp.floor, mp.zMin); var i1 = wp(inH, mp.floor, mp.zMin); var i2 = wp(inH, mp.floor, mp.zMax); var i3 = wp(-inH, mp.floor, mp.zMax);
                    float yf = Mathf.Min(Mathf.Min(i0.y, i1.y), Mathf.Min(i2.y, i3.y)) - 0.02f;
                    faces.Add(new EdoBuild.SkinFace("MizoP_" + c.name, new[] { new Vector2(i0.x, i0.z), new Vector2(i1.x, i1.z), new Vector2(i2.x, i2.z), new Vector2(i3.x, i3.z) }, yf)); nM++;
                    System.Func<float, bool> inP = lx => { var q0 = wp(lx, mp.top, 0.5f * (mp.zMin + mp.zMax)); return EdoGeom.PIP(Poly, new Vector2(q0.x, q0.z)); };
                    float xL = inP(mp.xMin - RING) ? mp.xMin - RING : mp.xMin, xR = inP(mp.xMax + RING) ? mp.xMax + RING : mp.xMax;
                    var o0 = wp(xL, mp.top, mp.zMin); var o1 = wp(xR, mp.top, mp.zMin); var o2 = wp(xR, mp.top, mp.zMax); var o3 = wp(xL, mp.top, mp.zMax);
                    float yr = Mathf.Min(Mathf.Min(o0.y, o1.y), Mathf.Min(o2.y, o3.y)) - 0.02f;
                    faces.Add(new EdoBuild.SkinFace("MizoP_" + c.name + "_rim", new[] { new Vector2(o0.x, o0.z), new Vector2(o1.x, o1.z), new Vector2(o2.x, o2.z), new Vector2(o3.x, o3.z) }, yr));
                }
            }
            if (sb != null && nM > 0) sb.AppendLine("  面 溝の駒の中 " + nM + "(溝の底 −0.02 ── 皮を溝の中へ下ろす)");
            // 門の口の踏み段の踏面(台の面 16.50 が段を埋めないよう、段石の外形の矩形を天端 −0.02 の面に ── 面積が小さいので勝つ)
            var gsT = rootM == null ? null : rootM.transform.Find("GateSteps"); int nS = 0;
            if (gsT != null)
                foreach (Transform c in gsT)
                {
                    if (!c.gameObject.activeInHierarchy || !System.Text.RegularExpressions.Regex.IsMatch(c.name, @"^GateStep_\d+_\d+$")) continue;
                    var pts = new List<Vector2>(); float yT = float.MinValue; foreach (var v in EdoBuild.Body(c, 4000)) { pts.Add(new Vector2(v.x, v.z)); yT = Mathf.Max(yT, v.y); } if (pts.Count < 3) continue;
                    faces.Add(new EdoBuild.SkinFace("Step_" + c.name, EdoBuild.ConvexHull2(pts).ToArray(), yT - 0.02f)); nS++;
                }
            if (sb != null && nS > 0) sb.AppendLine("  面 門の口の踏み段 " + nS + "(踏面 −0.02)");
            // ⭐ 道の側の腰石垣と踏み段の前は道の高さ(指図 roadEdge「土の段・土の法を道に見せず、擦り付けもしない」【硬】・第82巡)── 台の面の外の法(OutsideY)が
            //   区画の線の外へ 1:1.5 の土の法を描いて石垣と樋口を埋めた。見え面の足元(天端の前の線 + 法 ×(天端 − 道))から線の外 1.0 までを 0.5m ごとの道の高さの面にする
            if (_road == null) _road = RoadEdgePlanOf(); var rd = _road; int nR = 0;
            if (false && rd != null && rd.ok)   // 第83巡: 平らな面をやめ、設計の地盤を道の現地形へ(Stage3b の設計の地盤の写し)
            {
                var spansF = new List<Vector2>(rd.spans); if (rd.hasGate) spansF.Add(new Vector2(rd.ps0, rd.ps1));
                foreach (var sp in spansF)
                    for (float s0 = sp.x; s0 < sp.y - 1e-3f; s0 += 0.5f)
                    {
                        float s1 = Mathf.Min(sp.y, s0 + 0.5f), yR = RoadAtS(rd, 0.5f * (s0 + s1)); if (float.IsNaN(yR)) continue;
                        bool gate = sp.x == rd.ps0 && sp.y == rd.ps1;
                        float dIn = gate ? 0.0f : rd.setback - rd.batter * (rd.yTop - yR);   // 見え面の足元(線から内へ)・門の口は線から
                        Vector2 a0 = rd.ea + rd.ax * s0 - rd.outN * dIn, a1 = rd.ea + rd.ax * s1 - rd.outN * dIn, b1 = rd.ea + rd.ax * s1 + rd.outN * 1.0f, b0 = rd.ea + rd.ax * s0 + rd.outN * 1.0f;
                        faces.Add(new EdoBuild.SkinFace("Road_" + s0.ToString("F1"), new[] { a0, a1, b1, b0 }, yR)); nR++;
                    }
            }
            if (sb != null && nR > 0) sb.AppendLine("  面 道の側の腰石垣と踏み段の前(道の高さ・0.5m ごと) " + nR);
        }
        // ⭐ 座より高い段の面に掛かる長屋の躯体の下は、その面でなく棟の座(第94巡: Kadonouchi の多角形が N39_1(座 14.00)の西の端の下まで入り、皮が躯体を 16.50 で
        //   埋め、外へ 1:1.5 の土の盛り ── 指図 roadEdge 追記 2026-10-10k「今の急な土の盛りは切って除く」【硬】)。躯体の凸包を座の高さの面に(面積の小さい面が勝つ)。
        //   当たる先: 皮を起こす邸の、段の面の多角形に躯体が掛かり座が面より gradeTol(0.25)を超えて低い長屋すべて(岡部 N39_1)
        {
            var rootZ = GameObject.Find(GN); var kz = rootZ == null ? null : rootZ.transform.Find("Kakoi"); int nZ = 0; var zaNote = new List<string>();
            var terrN = new HashSet<string>(); foreach (var oT in A(D["terraces"]) ?? new List<object>()) { var tT = O(oT); string tn = tT == null ? null : S(Get(tT, "name")); if (tn != null) terrN.Add(tn); }
            var baseFaces = faces.FindAll(x => terrN.Contains(x.name));   // 面 = 指図の段(溝・台・踏み段の小さい面は除く)
            if (kz != null)
                foreach (Transform c in kz)
                {
                    if (!c.gameObject.activeInHierarchy || !EdoBuild.IsNagayaBody(c.gameObject)) continue;
                    var pts = new List<Vector2>(); float yLo = float.MaxValue; foreach (var v in EdoBuild.Body(c, 4000)) { pts.Add(new Vector2(v.x, v.z)); yLo = Mathf.Min(yLo, v.y); } if (pts.Count < 3) continue;
                    var hull = EdoBuild.ConvexHull2(pts).ToArray(); string hit = null;
                    foreach (var bf in baseFaces) { if (bf.poly == null || bf.y - yLo <= 0.25f) continue; /* 面が座より高い(躯体を埋める)時だけ */ foreach (var hq in hull) if (EdoGeom.PIP(bf.poly, hq)) { hit = bf.name + " " + bf.y.ToString("F2"); break; } if (hit != null) break; }
                    if (hit == null) continue;
                    // 指図 backOf<棟> 追記 2026-10-10o【硬】「背の台の石垣は <棟> の背の全長に通す」── 座の面は背の面(石垣の天端の前の線)で止め、背の外へ出さない
                    //   (躯体の凸包は軒の下の出を拾い、背の外 0.6〜1.0 を座 14.00 にして台の石垣の前に 0.9 の土の棚が立った ── 第98巡)。当たる先: 背の台の石垣を持つ棟(岡部 N39_1)
                    foreach (var trZ in BackTrenchesFull())
                        if (trZ.run == c.name) { var hc = EdoGeom.ClipHalfPlane(hull, trZ.stop, trZ.yard); if (hc != null) { hull = hc; zaNote.Add(c.name + " を背の面で切った"); } }
                    faces.Add(new EdoBuild.SkinFace("Za_" + c.name, hull, yLo)); nZ++; zaNote.Add(c.name + "(座 " + yLo.ToString("F2") + " ⊂ 面 " + hit + ")");
                }
            if (sb != null && nZ > 0) sb.AppendLine("  面 長屋の座(面の高さと違う座の躯体の下) " + nZ + ": " + string.Join("・", zaNote.ToArray()));
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
    /// <summary>坂の路盤を縦断で描く坂か ── 石段を名指す坂(kaidans[].atRoute)と、両脇を石垣で挟んだ坂(ramps[].kiritoshi.wall)。
    /// ⭐ 第102巡: 石垣で挟んだ幅 1.5間 の坂(岡部 R_KiriZaka)は 2m 格子の地形が溝を描けず、路盤が縦断より 0.3〜0.7 高く描かれた
    /// (芯の節点の両隣が平場 16.0 の節点で一次に引かれる)。当たる先: 石段を持つ坂・石垣で挟んだ坂のすべて(皮を起こす邸)。</summary>
    static bool RampDrawnByProfile(Dictionary<string, object> r)
    {
        foreach (var ko in A(Get(D, "kaidans")) ?? new List<object>()) { var kk = O(ko); if (kk != null && S(Get(kk, "atRoute")) == S(Get(r, "name"))) return true; }
        var kt = O(Get(r, "kiritoshi")); return kt != null && (S(Get(kt, "wall")) ?? "").Contains("石垣");
    }

    static float RampProfileAt(Vector2 q)
    {
        if (_rampProf == null)
        {
            _rampProf = new List<KeyValuePair<Vector2[], float[]>>(); _rampW = new List<float>();
            foreach (var o in A(Get(D, "ramps")) ?? new List<object>())
            {
                var r = O(o); if (r == null) continue;
                if (!RampDrawnByProfile(r)) continue;
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
            case "MunamonSode": return (a0 > 0f ? a0 : wKen) > 0f ? EdoAssets.Own.MunamonSode(a0 > 0f ? a0 : wKen, a1, false) : null;
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
    /// <summary>石段 <paramref name="nm"/> を切る土留めの欄のうち、cuts 追記 2026-10-10o「袖の上端は本線の駒でなく、本線の計画の見え面の線で決める」を持つ欄の名(無ければ null)
    /// ── この石段の袖は本線より先に据える(段石 → 袖 → 本線・指図 TW_Kado_Hokuto.cuts 10-10o【硬】)。</summary>
    static string SodeFirstWall(string nm)
    {
        foreach (var o in A(Get(D, "terraceWalls")) ?? new List<object>())
        {
            var t = O(o); string ct = S(Get(t, "cuts")) ?? ""; if (!ct.StartsWith(nm)) continue;
            int i = ct.IndexOf("追記 2026-10-10o"); if (i < 0) continue; string tx = ct.Substring(i);
            if (tx.Contains("袖の上端は本線の駒でなく") && tx.Contains("見え面の線")) return S(Get(t, "name"));
        }
        return null;
    }

    /// <summary>**石段の袖を本線より先に据え、口の両端の本線をその外の面へ突き付けて止める**(指図 TW_Kado_Hokuto.cuts 追記 2026-10-10o【硬】・EDO-0502 第99巡)。
    /// 置き方の4手: 固定側 = 据わった段石 → 袖(上端は本線の計画の見え面の線 = 区間の線 ── <see cref="EdoBuild.PlaceIshidanSodeRow"/> の planRay)→
    /// 可動側 = 本線の口の端。端は袖の外の面(袖の実メッシュの、本線の見え面の前 1.0 以内の頂点の走りへの射影の最小)まで縮め/延ばし、
    /// その駒を名指しの相手にする(<see cref="EdoBuild.NozuraSeg.abutTo"/> ── 見切り石・隅の駒・打ち切りを置かない)。袖の駒は網の近くの駒(pool)にも足す。
    /// 硬い: 袖が据わらない・端の相手が無い ⇒ ★ を刷り従前(見切り石なし・③)へ。当たる先: cuts に 10-10o の文を持つ土留めが切る石段(岡部 K_Kuruwa)。</summary>
    static string SodesBeforeNet(Transform danGrp, List<EdoBuild.NozuraSeg> segs, List<GameObject> pool)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        var placed = new Dictionary<string, List<GameObject>>();
        sb.Append(PlaceKaidanSodes(danGrp, segs, placed));
        var root = GameObject.Find(GN); var kai = root == null ? null : root.transform.Find("Fuzoku/Kaidan");
        foreach (var o in A(Get(D, "kaidans")) ?? new List<object>())
        {
            var k = O(o); string nm = S(Get(k, "name")); if (nm == null) continue; string twn = SodeFirstWall(nm); if (twn == null) continue;
            var steps = new List<GameObject>(); if (kai != null) foreach (Transform c in kai) if (c.gameObject.activeInHierarchy && c.name.StartsWith(nm + "_") && !c.name.StartsWith("Sode_")) steps.Add(c.gameObject);
            var sodes = new List<GameObject>(); foreach (var kv in placed) if (kv.Key.StartsWith(nm + "|")) foreach (var g in kv.Value) if (g != null) sodes.Add(g);
            if (steps.Count == 0 || sodes.Count == 0) { sb.AppendLine("  ★ 袖を先に(cuts 10-10o) " + nm + ": 段石 " + steps.Count + "・袖 " + sodes.Count + " ── 口の端を突き付けない"); continue; }
            pool.AddRange(sodes);
            var bb = new List<Bounds>(); foreach (var g in steps) bb.Add(EdoBuild.RB(g));
            Vector3 f3 = steps[0].transform.forward; var fwd = new Vector2(f3.x, f3.z).normalized;   // 坂下 = 本線の見え面の前
            foreach (var sg in segs)
            {
                if (!sg.name.StartsWith(twn + "_")) continue;
                for (int e = 0; e < 2; e++)
                {
                    Vector2 ep = e == 1 ? sg.b : sg.a; bool near = false;
                    foreach (var b in bb) { var c2 = new Vector2(Mathf.Clamp(ep.x, b.min.x, b.max.x), Mathf.Clamp(ep.y, b.min.z, b.max.z)); if (Vector2.Distance(c2, ep) <= 1.5f) { near = true; break; } }
                    if (!near) continue;
                    Vector2 away = e == 1 ? sg.Dir : -sg.Dir;   // 端から口へ
                    // 袖の外の面(この端の側の袖・見え面の前 1.0 以内・天端 −1.0 より上の頂点の走りへの射影の最小)
                    float crest = sg.crestAt(e == 0 ? 0f : sg.Len), uMin = float.MaxValue; var side = new List<GameObject>();
                    foreach (var g in sodes)
                    {
                        bool mine = false;
                        foreach (var v in EdoBuild.Body(g.transform, 4000))
                        {
                            Vector2 r = new Vector2(v.x, v.z) - ep; float fr = Vector2.Dot(r, fwd), u = Vector2.Dot(r, away);
                            if (fr < -0.05f || fr > 1.0f || v.y < crest - 1.0f || u < -1.5f || u > 1.5f) continue;
                            mine = true; uMin = Mathf.Min(uMin, u);
                        }
                        if (mine) side.Add(g);
                    }
                    if (side.Count == 0) { sb.AppendLine("  ★ 袖を先に(cuts 10-10o) " + sg.name + " 端" + e + ": 端の 1.5m 内に袖の外の面が無い ── 突き付けない"); continue; }
                    Vector2 nep = ep + away * uMin;
                    if (e == 1) sg.b = nep; else { var c0 = sg.crestAt; float off = -uMin; sg.a = nep; if (c0 != null) sg.crestAt = sl => c0(sl + off); }
                    sg.abutTo[e] = side; sg.mikiriTo[e] = null;
                    sb.AppendLine("  口の端を袖の外の面へ(cuts 追記 2026-10-10o【硬】): " + sg.name + " 端" + e + " を " + (uMin < 0f ? "縮めた " : "延ばした ") + Mathf.Abs(uMin).ToString("F3", inv) + "m・相手 = 袖の駒 " + side.Count + "(見切り石・隅の駒なし)");
                }
            }
        }
        return sb.ToString();
    }

    static string PlaceKaidanSodes(Transform danGrp, List<EdoBuild.NozuraSeg> planSegs = null, Dictionary<string, List<GameObject>> placed = null)
    {
        var sb = new System.Text.StringBuilder(); var inv = System.Globalization.CultureInfo.InvariantCulture;
        var kai = Group("Fuzoku/Kaidan");
        foreach (var o in A(Get(D, "kaidans")) ?? new List<object>())
        {
            var k = O(o); if (k == null) continue;
            string nm = S(Get(k, "name")), txt = S(Get(k, "sode")); if (nm == null || txt == null) continue;
            // 段石 → 袖 → 本線(cuts 10-10o)の石段は網の前に据える(SodesBeforeNet)── 網の後の呼び出しでは飛ばす
            string firstW = SodeFirstWall(nm); if ((planSegs != null) != (firstW != null)) continue;
            System.Func<Vector3, Vector3, float> planRay = null; float planCrest = float.NaN;
            if (planSegs != null)
            {   // 本線の計画の見え面の線 = この欄の区間の線(天端の前の縁)── 光線が最初に交わる区間・天端はその交点の計画の天端
                var cand = planSegs.FindAll(x => x.name.StartsWith(firstW + "_") && x.crestAt != null);
                planRay = (o3, d3) =>
                {
                    Vector2 p0 = new Vector2(o3.x, o3.z), d = new Vector2(d3.x, d3.z).normalized; float best = float.NaN;
                    foreach (var sg in cand)
                    {
                        Vector2 t = sg.Dir; float L = sg.Len; var nrm = new Vector2(-t.y, t.x); float den = Vector2.Dot(d, nrm); if (Mathf.Abs(den) < 1e-4f) continue;
                        float h = Vector2.Dot(sg.a - p0, nrm) / den; if (h <= 0f) continue; float u = Vector2.Dot(p0 + d * h - sg.a, t);
                        if (u < -1.0f || u > L + 1.0f) continue;   // 口で切った端の先 1.0 まで(袖の線は口の縁の外 0.15〜0.45)
                        if (float.IsNaN(best) || h < best) { best = h; planCrest = sg.crestAt(Mathf.Clamp(u, 0f, L)); }
                    }
                    return best;
                };
            }
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
                if (planRay != null) { planCrest = float.NaN; var o0 = dans[dans.Count - 1].transform; planRay(o0.position + o0.forward * 2f, -o0.forward); }   // 計画の天端を先に引く(光線が交わる区間の天端)
                var got = EdoBuild.PlaceIshidanSodeRow(dans, side, (i, d) => kiriishi ? EdoAssets.Own.IshidanSode(rr, ff, i, d) : EdoAssets.Own.IshidanSodeUchikomi(rr, ff, i, d), EdoAssets.Own.IshidanSodeDepthsDeep,
                                                       kai, "Sode_" + nm + (side > 0 ? "_R" : "_L"), kasaT, 0f, walls, sink, SkinGround, 0.05f, warn, out rep, 8, planRay, planCrest);
                if (placed != null) placed[nm + "|" + side] = got;
                sb.AppendLine("  石段の袖 " + nm + (side > 0 ? " 右" : " 左") + "(" + (kiriishi ? "切石" : "打込接ぎ") + (skipTop ? "・上がり口の脇なし" : "") + "): 段の脇 " + rep.placed + " 駒・坂下へ継いだ " + rep.ext + " 駒・退けた " + rep.refused
                            + "・笠の上がり " + rep.kasa.ToString("F3") + "(狙い " + kasaT.ToString("F2") + ")"
                            + (planRay != null ? "・上端 = 本線の計画の見え面の線(cuts 10-10o・天端 " + (float.IsNaN(planCrest) ? "-" : planCrest.ToString("F2")) + ")" : "")
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
            float y = bt.max.y - drop; float uEnd = u1 + flat; string wide = "";
            // 指図 cuts 追記 2026-10-10o【硬】「口の背(両袖の外の面の間・本線の天端の背の線まで)は 16.50 の平らで topStepBackFlat を当てる」── 横は据わった袖の外の面まで、
            //   奥は max(段石の背 + 平らの奥行, 本線の天端の背の線)。本線の天端の背の線 = 口の両脇の本線の駒の天端の帯(最上点 −0.15)の上がる向きへの射影の最大。
            string fw = SodeFirstWall(nm);
            if (fw != null)
            {
                float s0 = float.MaxValue, s1 = float.MinValue, ub = float.MinValue; int ns = 0, nw = 0;
                foreach (Transform c in kai) { if (!c.gameObject.activeInHierarchy || !c.name.StartsWith("Sode_" + nm + "_")) continue; ns++; foreach (var v in EdoBuild.Body(c, 4000)) { float l = Vector2.Dot(new Vector2(v.x, v.z) - c0, side); s0 = Mathf.Min(s0, l); s1 = Mathf.Max(s1, l); } }
                var dnG = root.transform.Find("Dan");
                if (dnG != null) foreach (Transform c in dnG)
                {
                    if (!c.gameObject.activeInHierarchy || !c.name.StartsWith(fw + "_")) continue; var rb = EdoBuild.RB(c.gameObject); if (Vector2.Distance(new Vector2(rb.center.x, rb.center.z), c0) > 5f) continue;
                    var vs = EdoBuild.Body(c, 4000); float tp = float.MinValue; foreach (var v in vs) tp = Mathf.Max(tp, v.y);
                    foreach (var v in vs) { if (v.y < tp - 0.15f) continue; var r = new Vector2(v.x, v.z) - c0; float l = Vector2.Dot(r, side); if (l < s0 - 1.0f || l > s1 + 1.0f) continue; ub = Mathf.Max(ub, Vector2.Dot(r, up)); nw++; }
                }
                if (ns > 0) { l0 = Mathf.Min(l0, s0); l1 = Mathf.Max(l1, s1); }
                if (nw > 0) uEnd = Mathf.Max(uEnd, ub);
                wide = "・口の背(cuts 10-10o): 横 = 袖の外の面" + (ns > 0 ? "" : " ★ 袖が無い") + "・奥 = " + (nw > 0 ? "本線の天端の背の線 " + (ub - u1).ToString("F2") + "m と平らの大きい方" : "★ 本線の駒が無い ── 平らの奥行のまま");
            }
            Vector2 pa = c0 + up * (u1 - 0.05f), pb = c0 + up * uEnd;
            res.Add(new EdoBuild.SkinFace("TopLanding_" + nm, new[] { pa + side * l1, pb + side * l1, pb + side * l0, pa + side * l0 }, y, TOPSTEP_BACK_TOL));
            sb.AppendLine("  面 TopLanding_" + nm + "(" + y.ToString("F2") + "): 上がり口の段石の背 " + (uEnd - u1).ToString("0.0#") + "m・幅 " + (l1 - l0).ToString("F2") + "m(据わった段石から)" + wide);
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

    public static string Stage4_Niwa() { using (OnKita()) return Stage4_Niwa_(); }
    static string Stage4_Niwa_()
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
        var t = EdoBuild.T(); var td = t.terrainData;
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

    public static string Stage5_Nishi() { using (OnKita()) return Stage5_Nishi_(); }
    static string Stage5_Nishi_()
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
    public static string ClosureQA() { using (OnKita()) return ClosureQA_(); }
    static string ClosureQA_()
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
    public static string OpeningQA() { using (OnKita()) return OpeningQA_(); }
    static string OpeningQA_()
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

    public static string RunAll() { using (OnKita()) return RunAll_(); }
    static string RunAll_()
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
        sb.AppendLine(Stage3d_Mizo());      // 皮は退役(2026-10-11)── 溝を据えて溝の下の地面を下げる
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
                               "Assets/Edo/Models/Trees", "Assets/Edo/Models/Niwa",
                               // 野面の重ねの端の版 `Nozura2_*`(Kirishi / Danishi ── 借り先 Assets/Edo/Materials/Sanno・2026-10-11 EDO-0502)
                               "Assets/Edo/Models/Nozura2" };
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
