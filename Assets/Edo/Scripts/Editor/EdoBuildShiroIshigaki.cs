// EdoBuild — 城の石垣の直線 run を区画の辺に沿って据える(外周の基壇・2026-10-04・EDO-0533 土井 boundaryPlinth)。
//  スキル unity-modular-stonewall の作法: 天端は区間ごとに一直線(丸い数字のまま)・段は区間の継ぎ目でだけ・ピッチ 1.80 / 重ね 0.20
//  (駒の割りと据えは PlaceCrestWall ── 見え面を低い側へ・天端の前の縁を線へ・走りの端と天端は実メッシュ)。
//  ⭐ この関数が足すのは「区画の辺に沿う」ことだけ: ① 区間を辺の s で受け、② 駒の実メッシュ(根入れの足まで)が区画の線を越えない
//  最小の控えを**据えて測って**解き(InsetRunToPoly)、③ 控えた線どうしの交点で隣の辺の区間と出隅・入隅を閉じる。
//  ⛔ 区画の線を天端の前の縁と決め打ちしない ── 城の石垣は法(1:0.25)で、丈 4.0 の駒の足は天端の縁より 1m 外へ出る。
//  ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図の区間(辺・s・天端・口)を渡すだけ。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>城の石垣の直線 run の一区間(区画の辺 <c>edge</c> の走り s0〜s1・天端 <c>crest</c>・口 <c>gaps</c> は辺の s の [s0, s1])。</summary>
    public class CastleSec
    {
        public string name; public int edge; public float s0, s1, crest;
        public List<Vector2> gaps = new List<Vector2>();
    }

    /// <summary><see cref="PlaceCastleRun"/> の答え。</summary>
    public class CastleRun
    {
        public List<GameObject> pieces = new List<GameObject>();
        /// <summary>辺 → 天端の前の縁の、区画の線から内への距離[m](実測の控え)。</summary>
        public Dictionary<int, float> inset = new Dictionary<int, float>();
        /// <summary>区間の名 → 据えた駒(区間の割りの名ではなく呼び手の区間の名)。</summary>
        public Dictionary<string, List<GameObject>> bySec = new Dictionary<string, List<GameObject>>();
        public List<RunEnd> ends = new List<RunEnd>();
        public Dictionary<string, List<GameObject>> segs = new Dictionary<string, List<GameObject>>();
        public float worstFloat = float.NegativeInfinity, worstOutside;
        public int buried;
    }

    /// <summary>区間の端が区画の頂点に在るとみなす離れ[m] ── 指図の s は 0.01 で丸めてある(辺13 の長さ 77.26 と実の 77.264)。</summary>
    public const float VTX_TOL = 0.02f;

    /// <summary>区画の辺 e の外向き(内外判定で決める ── 重心で決めると凹みのある区画で裏返る)。</summary>
    public static Vector2 PolyEdgeOut(Vector2[] poly, int e)
    {
        int n = poly.Length; Vector2 a = poly[e % n], b = poly[(e + 1) % n];
        Vector2 d = (b - a).normalized, nn = new Vector2(-d.y, d.x), mid = (a + b) * 0.5f;
        float probe = Mathf.Min(0.5f, (b - a).magnitude * 0.2f);
        return EdoGeom.PIP(poly, mid + nn * probe) ? -nn : nn;
    }

    /// <summary>**城の石垣の直線 run を区画の辺に沿って据える**(外周の基壇・腰石垣)。
    /// <para>手順(置き方の4手): ① 区間を区画の線そのものへ <see cref="PlaceCrestWall"/> で仮に据え、辺ごとに駒の実メッシュ
    /// (根入れの足を含む全頂点)が区画の外へ出ない最小の控えを <see cref="InsetRunToPoly"/> で測る ② 据え直す ── 線 = 区画の線を
    /// 控えだけ内へ、隣の辺の区間と頂点で続く端は**控えた線どうしの交点**まで(出隅は <see cref="PlaceRunCorners"/> が受ける端の組になる)
    /// ③ もう一度区画の線を検め、まだ越える駒があれば辺ごとに引いて ★ を刷る。</para>
    /// <para>硬い(許容0): 区域(壁体の全頂点が区画の内・<paramref name="tol"/>)・天端 = 区間の crest(実測の最上点)・全体が地表の下の駒は置かない。
    /// 柔らかい: 見付(露出)の狙いは呼び手が刷る(この関数は天端と足元の地表を測るだけ)。段は区間の継ぎ目でだけ(区間を渡す呼び手が決める)。
    /// 天端が同じで口の無い隣り合う区間は一本に束ねる(天端一直線)。</para>
    /// <para>⭐ <paramref name="stepLap"/> ≥ 0(段の継ぎ目の掛け・2026-10-05 EDO-0533): 同じ辺で天端が下がる継ぎ目では、**高い区間の天端の面を継ぎ目の面より
    /// <paramref name="stepLap"/> 先まで届かせる** ── 仮に据えた駒の天端の面(天端 −0.005 より上の頂点)が継ぎ目の s に届かない分を測り、その分 + stepLap だけ
    /// 高い区間の端を低い区間の側へ延ばす(延ばした駒は低い区間の天端の上に立ち、段の小口が掛けの分だけ低い側へ出る)。
    /// 天端の上に載る棟の足が継ぎ目の面まで来るとき、足の端が下の段の天端の上に浮かないため(土井 E13 の表長屋 ── 札の foot が ±L/2 に伸びた第10巡)。
    /// 負(既定)なら延ばさない(従来どおり)。</para>
    /// 当たる先: 区画の線に沿って建つ城の石垣の基壇・腰石垣の全て(土井 boundaryPlinth。岡部 PlaceIshigaki(外周の基壇)は
    /// ピボットを線に置く旧い据えのまま ── 移し替えは別票)。</summary>
    public static CastleRun PlaceCastleRun(IList<CastleSec> secs, Vector2[] poly, Func<float, float, float> groundAt, Transform parent,
                                           System.Text.StringBuilder log, float maxInset = 2.5f, float tol = 0.001f, float stepLap = -1f)
    {
        var res = new CastleRun();
        if (secs == null || secs.Count == 0 || poly == null) return res;
        int n = poly.Length;
        // 天端が同じ・口の無い継ぎ目の区間を束ねる(辺ごと・s の順)
        var list = new List<CastleSec>(secs);
        list.Sort((x, y) => x.edge != y.edge ? x.edge.CompareTo(y.edge) : x.s0.CompareTo(y.s0));
        var merged = new List<CastleSec>(); var members = new Dictionary<CastleSec, List<string>>();
        foreach (var s in list)
        {
            var last = merged.Count > 0 ? merged[merged.Count - 1] : null;
            if (last != null && last.edge == s.edge && Mathf.Abs(last.s1 - s.s0) < 1e-3f && Mathf.Abs(last.crest - s.crest) < 1e-3f)
            {
                last.s1 = s.s1; last.gaps.AddRange(s.gaps); members[last].Add(s.name); continue;
            }
            var c = new CastleSec { name = s.name, edge = s.edge, s0 = s.s0, s1 = s.s1, crest = s.crest, gaps = new List<Vector2>(s.gaps) };
            merged.Add(c); members[c] = new List<string> { s.name };
        }
        // 口で区間を割る ── 口の脇に残る駒一枚(2.00)に満たない切れ端は、口の反対の端を隣の区間へ延ばす(天端が同じか高い隣だけ ──
        //   延ばした駒は隣の駒の見え面の裏・天端の下に入って隠れる)。⛔ PlaceCrestWall の「短い区間は両側へはみ出す」に任せると、
        //   駒が口の中へ 0.56m 出た(土井 E13_N09 の通用門・2026-10-04)。
        var wallOf = new Dictionary<CastleSec, string>();
        {
            var split = new List<CastleSec>();
            foreach (var c in merged)
            {
                if (c.gaps.Count == 0) { split.Add(c); wallOf[c] = c.name; continue; }
                var cuts = new List<Vector2> { new Vector2(c.s0, c.s1) };
                foreach (var g in c.gaps)
                {
                    var nx = new List<Vector2>();
                    foreach (var q in cuts) { if (g.y <= q.x || g.x >= q.y) { nx.Add(q); continue; } if (g.x > q.x) nx.Add(new Vector2(q.x, g.x)); if (g.y < q.y) nx.Add(new Vector2(g.y, q.y)); }
                    cuts = nx;
                }
                for (int i = 0; i < cuts.Count; i++)
                {
                    float a0 = cuts[i].x, a1 = cuts[i].y;
                    if (a1 - a0 < 2.0f)
                    {
                        bool gapLo = c.gaps.Exists(g => Mathf.Abs(g.y - a0) < 1e-3f), gapHi = c.gaps.Exists(g => Mathf.Abs(g.x - a1) < 1e-3f);
                        var nbHi = merged.Find(x => x.edge == c.edge && Mathf.Abs(x.s0 - c.s1) < 1e-3f);
                        var nbLo = merged.Find(x => x.edge == c.edge && Mathf.Abs(x.s1 - c.s0) < 1e-3f);
                        if (gapLo && !gapHi && Mathf.Abs(a1 - c.s1) < 1e-3f && nbHi != null && nbHi.crest >= c.crest - 1e-3f) a1 = a0 + 2.0f;
                        else if (gapHi && !gapLo && Mathf.Abs(a0 - c.s0) < 1e-3f && nbLo != null && nbLo.crest >= c.crest - 1e-3f) a0 = a1 - 2.0f;
                        if (a1 - a0 >= 2.0f - 1e-3f && (a1 - a0) > cuts[i].y - cuts[i].x + 1e-3f)
                            log?.AppendLine("  城の石垣 " + c.name + ": 口の脇の切れ端 " + (cuts[i].y - cuts[i].x).ToString("F2") + "m ⇒ 口の縁から駒一枚を据え、反対の端を隣の高い区間の裏へ延ばした");
                    }
                    var sub = new CastleSec { name = c.name, edge = c.edge, s0 = a0, s1 = a1, crest = c.crest, gaps = new List<Vector2>() };
                    split.Add(sub); members[sub] = members[c]; wallOf[sub] = c.name + "_k" + i;
                }
            }
            merged = split;
        }
        Func<int, Vector2> A = e => poly[e % n];
        Func<int, Vector2> Dir = e => (poly[(e + 1) % n] - poly[e % n]).normalized;
        Func<int, float> Len = e => (poly[(e + 1) % n] - poly[e % n]).magnitude;
        float area = 0f; for (int i = 0; i < n; i++) area += poly[i].x * poly[(i + 1) % n].y - poly[(i + 1) % n].x * poly[i].y;
        // 頂点 v(辺 v−1 → 辺 v)の折れ[°]。+ = 出隅(区画の巡りと同じ向きへ折れる)
        Func<int, float> Turn = v =>
        {
            Vector2 d1 = Dir((v - 1 + n) % n), d2 = Dir(v % n);
            float a = Mathf.Atan2(d1.x * d2.y - d1.y * d2.x, Vector2.Dot(d1, d2)) * Mathf.Rad2Deg;
            return area >= 0f ? a : -a;
        };
        // 駒の足(天端の縁から外への出)と控え(内への奥行)── 仮に据えた駒の実メッシュで測る(辺ごと)
        var foot = new Dictionary<int, float>(); var back = new Dictionary<int, float>();
        // 相手の無い出隅の端の切り詰め[m]: 端の小口(走りに直角)の四隅が隣の辺の内に入る最小。
        //   L − s ≥ −t·cot φ を t ∈ {控え − 足, 控え + 奥行} で満たす(φ = 頂点の折れ・出隅だけ)
        Func<int, int, float, float> freeTrim = (e, v, de) =>
        {
            float phi = Turn(v); if (phi <= 1f) return 0f;
            float f = foot.ContainsKey(e) ? foot[e] : 1.0f, bk = back.ContainsKey(e) ? back[e] : 2.4f;
            float cot = 1f / Mathf.Tan(phi * Mathf.Deg2Rad), trim = 0f;
            foreach (float t in new[] { de - f, de + bk }) trim = Mathf.Max(trim, -t * cot);
            return trim + 0.01f;
        };

        // 段の継ぎ目の掛け(stepLap ≥ 0)── 区間 → 延ばす長さ[m](低い区間の側の端だけ)
        var lapLo = new Dictionary<CastleSec, float>(); var lapHi = new Dictionary<CastleSec, float>();
        Func<CastleSec, bool, CastleSec> lowerNb = (s, hi) => merged.Find(x => x != s && x.edge == s.edge && (hi ? Mathf.Abs(x.s0 - s.s1) < 1e-3f : Mathf.Abs(x.s1 - s.s0) < 1e-3f) && x.crest < s.crest - 1e-3f);
        // 天端の面の端(走りの s)── 駒の実メッシュの天端 −0.005 より上の頂点の、走りへの射影の最小・最大
        Func<List<GameObject>, CastleSec, Vector2> crestSpan = (gos, s) =>
        {
            float lo = float.MaxValue, hi = float.MinValue; Vector2 dd = (poly[(s.edge + 1) % n] - poly[s.edge % n]).normalized; Vector2 a0 = poly[s.edge % n];
            foreach (var go in gos) { if (go == null) continue; foreach (var v in Body(go.transform, 999999)) if (v.y >= s.crest - 0.005f) { float t = Vector2.Dot(new Vector2(v.x, v.z) - a0, dd); lo = Mathf.Min(lo, t); hi = Mathf.Max(hi, t); } }
            return new Vector2(lo, hi);
        };

        // 一巡目(区画の線そのもの)と二巡目(控えた線)── 同じ組み立てを inset を変えて呼ぶ
        Func<Dictionary<int, float>, bool, List<GameObject>> build = (ins, final) =>
        {
            var made = new List<GameObject>();
            if (final) { res.ends.Clear(); res.segs.Clear(); res.bySec.Clear(); res.worstFloat = float.NegativeInfinity; res.buried = 0; }
            foreach (var s in merged)
            {
                int e = s.edge; Vector2 d = Dir(e), o = PolyEdgeOut(poly, e);
                float de = ins.ContainsKey(e) ? ins[e] : 0f;
                Vector2 a = A(e) + d * s.s0 - o * de, b = A(e) + d * s.s1 - o * de;
                // 頂点で隣の辺の区間へ続く端は、控えた線どうしの交点へ(出隅・入隅を閉じる)
                Func<int, Vector2, Vector2> meet = (e2, p) =>
                {
                    Vector2 d2 = Dir(e2), o2 = PolyEdgeOut(poly, e2); float de2 = ins.ContainsKey(e2) ? ins[e2] : 0f;
                    Vector2 q0 = A(e2) - o2 * de2;   // 線2 上の点
                    float den = d.x * d2.y - d.y * d2.x; if (Mathf.Abs(den) < 1e-4f) return p;
                    Vector2 w = q0 - (A(e) - o * de);
                    float t = (w.x * d2.y - w.y * d2.x) / den;
                    return A(e) - o * de + d * t;
                };
                if (s.s1 >= Len(e) - VTX_TOL)
                {
                    if (merged.Exists(x => x.edge == (e + 1) % n && x.s0 <= VTX_TOL)) b = meet((e + 1) % n, b);
                    else { float tr = freeTrim(e, (e + 1) % n, de); b -= d * tr; if (final && tr > 0.011f) log?.AppendLine("  城の石垣 " + s.name + ": 相手の無い出隅の端を " + tr.ToString("F2") + "m 詰めた(小口が隣の辺の線を越えない)"); }
                }
                if (s.s0 <= VTX_TOL)
                {
                    if (merged.Exists(x => (x.edge + 1) % n == e && x.s1 >= Len(x.edge) - VTX_TOL)) a = meet((e - 1 + n) % n, a);
                    else { float tr = freeTrim(e, e, de); a += d * tr; if (final && tr > 0.011f) log?.AppendLine("  城の石垣 " + s.name + ": 相手の無い出隅の端を " + tr.ToString("F2") + "m 詰めた(小口が隣の辺の線を越えない)"); }
                }
                { float lp; if (lapLo.TryGetValue(s, out lp)) a -= d * lp; if (lapHi.TryGetValue(s, out lp)) b += d * lp; }
                var gaps = new List<Vector2>();
                foreach (var g in s.gaps)
                {
                    Vector2 g0 = A(e) + d * g.x - o * de, g1 = A(e) + d * g.y - o * de;
                    gaps.Add(new Vector2(Vector2.Dot(g0 - a, d), Vector2.Dot(g1 - a, d)));
                }
                var cw = new CrestWall { name = wallOf[s], nodes = new List<Vector2> { a, b }, nodeTops = new List<float> { s.crest, s.crest }, gaps = gaps,
                                         pathOfH = CastleWallOfExpose, runAlongX = false, runLen = 2.0f, pitchMax = 1.8f,
                                         lowHint = (p, q) => o, lowForce = true };
                float wf; int bs;
                var segOut = new Dictionary<string, List<GameObject>>();
                var got = PlaceCrestWall(cw, groundAt, parent, final ? res.ends : null, segOut, final ? log : new System.Text.StringBuilder(), out wf, out bs);
                made.AddRange(got);
                if (final)
                {
                    foreach (var kv in segOut) res.segs[kv.Key] = kv.Value;
                    foreach (var nm in members[s]) if (!res.bySec.ContainsKey(nm)) res.bySec[nm] = new List<GameObject>();
                    // 束ねた区間の駒を元の区間の名へ振り分ける(駒の芯の s で)
                    foreach (var go in got)
                    {
                        var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z) - A(e), d);
                        string pick = members[s][0];
                        foreach (var x in secs) if (x.edge == e && members[s].Contains(x.name) && sc >= x.s0 - 1e-3f && sc <= x.s1 + 1e-3f) { pick = x.name; break; }
                        res.bySec[pick].Add(go);
                    }
                    if (wf > res.worstFloat) res.worstFloat = wf; res.buried += bs;
                }
            }
            return made;
        };

        // ① 仮に据えて辺ごとの控えを測る
        var probe = build(new Dictionary<int, float>(), false);
        var byEdge = new Dictionary<int, List<GameObject>>();
        foreach (var go in probe)
        {
            int e = -1; foreach (var s in merged) if (go.name.StartsWith(wallOf[s] + "_", StringComparison.Ordinal)) e = s.edge;
            if (e < 0) continue; List<GameObject> l; if (!byEdge.TryGetValue(e, out l)) byEdge[e] = l = new List<GameObject>(); l.Add(go);
        }
        foreach (var kv in byEdge)
        {
            Vector2 o = PolyEdgeOut(poly, kv.Key); float f = 0f, bk = 0f;
            foreach (var go in kv.Value) foreach (var v in Body(go.transform, 999999))
            { float t = Vector2.Dot(new Vector2(v.x, v.z) - A(kv.Key), o); f = Mathf.Max(f, t); bk = Mathf.Max(bk, -t); }
            foot[kv.Key] = f; back[kv.Key] = bk;
            // 控えは辺の中ほどの駒で測る ── 頂点の端の駒は隣の辺に掛かり、走りに直角へ引いても収まらない(出隅は②で詰める)
            var mid = kv.Value.FindAll(go =>
            {
                var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z) - A(kv.Key), Dir(kv.Key));
                return sc > 3.0f && sc < Len(kv.Key) - 3.0f;
            });
            if (mid.Count == 0) mid = kv.Value;
            float before; float dpush = InsetRunToPoly(mid, poly, -o, maxInset, out before, 0.005f, tol);
            res.inset[kv.Key] = float.IsNaN(dpush) ? maxInset : dpush;
            log?.AppendLine("  城の石垣 辺" + kv.Key + ": 区画の線に置くと足が " + before.ToString("F3") + "m 外(足の出 " + f.ToString("F2") + "・控えの奥行 " + bk.ToString("F2") + ")⇒ 天端の前の縁を " + res.inset[kv.Key].ToString("F3") + "m 内へ控える(実測)");
        }
        if (stepLap >= 0f)
            foreach (var s in merged)
            {
                bool hiStep = lowerNb(s, true) != null, loStep = lowerNb(s, false) != null;
                if (!hiStep && !loStep) continue;
                var mine = probe.FindAll(go => go != null && go.name.StartsWith(wallOf[s] + "_", StringComparison.Ordinal));
                var sp = crestSpan(mine, s); if (sp.x > sp.y) continue;
                if (hiStep) lapHi[s] = Mathf.Max(0f, s.s1 - sp.y) + stepLap;
                if (loStep) lapLo[s] = Mathf.Max(0f, sp.x - s.s0) + stepLap;
            }
        foreach (var go in probe) if (go != null) UnityEngine.Object.DestroyImmediate(go);
        // ② 控えた線で据え直す
        res.pieces = build(res.inset, true);
        // 段の継ぎ目の掛けの検め(硬い ── 高い区間の天端の面が継ぎ目の面を越える)
        if (stepLap >= 0f)
            foreach (var s in merged)
            {
                if (!lapLo.ContainsKey(s) && !lapHi.ContainsKey(s)) continue;
                var mine = new List<GameObject>(); foreach (var nm in members[s]) if (res.bySec.ContainsKey(nm)) mine.AddRange(res.bySec[nm]);
                var sp = crestSpan(mine, s);
                if (lapHi.ContainsKey(s)) log?.AppendLine("  " + (sp.y >= s.s1 - 1e-3f ? "⭕" : "★") + " 城の石垣 " + s.name + ": 段の継ぎ目(s=" + s.s1.ToString("F2") + "・下の天端 " + lowerNb(s, true).crest.ToString("F2") + ")へ天端の面を " + lapHi[s].ToString("F3") + "m 延ばした ⇒ 天端の面の端 s=" + sp.y.ToString("F3") + "(継ぎ目を " + (sp.y - s.s1).ToString("+0.000;-0.000") + "m 越える)");
                if (lapLo.ContainsKey(s)) log?.AppendLine("  " + (sp.x <= s.s0 + 1e-3f ? "⭕" : "★") + " 城の石垣 " + s.name + ": 段の継ぎ目(s=" + s.s0.ToString("F2") + "・下の天端 " + lowerNb(s, false).crest.ToString("F2") + ")へ天端の面を " + lapLo[s].ToString("F3") + "m 延ばした ⇒ 天端の面の端 s=" + sp.x.ToString("F3") + "(継ぎ目を " + (s.s0 - sp.x).ToString("+0.000;-0.000") + "m 越える)");
            }
        // ③a 相手の無い頂点の端の駒は、走りに沿って区画の内へ引く(駒の実長は送りの 2.00 より長く、端の駒が区間の端から出る)
        foreach (var s in merged)
        {
            int e = s.edge; Vector2 d = Dir(e);
            bool freeHi = s.s1 >= Len(e) - VTX_TOL && !merged.Exists(x => x.edge == (e + 1) % n && x.s0 <= VTX_TOL);
            bool freeLo = s.s0 <= VTX_TOL && !merged.Exists(x => (x.edge + 1) % n == e && x.s1 >= Len(x.edge) - VTX_TOL);
            if (!freeHi && !freeLo) continue;
            var mine = new List<GameObject>(); foreach (var nm in members[s]) mine.AddRange(res.bySec[nm]);
            var ends2 = new List<bool>(); if (freeHi) ends2.Add(true); if (freeLo) ends2.Add(false);
            foreach (bool isHi in ends2)
            {
                GameObject endP = null; float best = isHi ? float.MinValue : float.MaxValue;
                foreach (var go in mine) { if (go == null) continue; var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z), d); if (isHi ? sc > best : sc < best) { best = sc; endP = go; } }
                if (endP == null) continue;
                float before; float pl = PullAlongInside(new List<GameObject> { endP }, poly, isHi ? -d : d, 1.0f, out before, 0f, 0.005f, tol);
                if (before > tol) log?.AppendLine("  城の石垣 " + endP.name + ": 頂点の端の駒が " + before.ToString("F3") + "m 区画の外 ⇒ 走りに沿って " + (float.IsNaN(pl) ? "1.0m 引いても収まらない ★" : pl.ToString("F3") + "m 引いた(隣の駒と重なる)"));
            }
        }
        // ③ 区画の線の検め(硬い)── まだ越える辺は引いて ★
        var byEdge2 = new Dictionary<int, List<GameObject>>();
        foreach (var s in merged) foreach (var nm in members[s]) foreach (var go in res.bySec[nm])
        { List<GameObject> l; if (!byEdge2.TryGetValue(s.edge, out l)) byEdge2[s.edge] = l = new List<GameObject>(); l.Add(go); }
        foreach (var kv in byEdge2)
        {
            float before; float dpush = InsetRunToPoly(kv.Value, poly, -PolyEdgeOut(poly, kv.Key), 0.5f, out before, 0.005f, tol);
            if (before > tol)
            {
                if (float.IsNaN(dpush)) { log?.AppendLine("  ★ 城の石垣 辺" + kv.Key + ": 据え直しても " + before.ToString("F3") + "m 区画の外 ── 0.5m 引いても収まらない"); res.worstOutside = Mathf.Max(res.worstOutside, before); }
                else
                {
                    log?.AppendLine("  ⚠ 城の石垣 辺" + kv.Key + ": 据え直しで " + before.ToString("F3") + "m 外(隅の交点の端の駒)⇒ さらに " + dpush.ToString("F3") + "m 引いた");
                    res.inset[kv.Key] += dpush;
                    for (int i = 0; i < res.ends.Count; i++)
                    {
                        var en = res.ends[i]; bool mine = false;
                        foreach (var go in kv.Value) if (res.segs.ContainsKey(en.key) && res.segs[en.key].Contains(go)) mine = true;
                        if (mine) { en.p -= PolyEdgeOut(poly, kv.Key) * dpush; res.ends[i] = en; }
                    }
                }
            }
        }
        return res;
    }

    /// <summary>**硬い(許容0)・区域**: 駒の組 <paramref name="gos"/> を走り <paramref name="along"/> に沿って一緒に引き、実メッシュが
    /// 区画の多角形の外へ出ない最小の量に納める(区画の頂点の端で、走りに直角な小口が隣の辺を跨ぐ駒 ── 出隅の折れが 90° を超えると
    /// 線から内へ控えた駒ほど隣の辺の外へ出る)。<paramref name="bandH"/> &gt; 0 なら壁体の最低点から bandH までの全頂点(腰)で測る
    /// (一体で焼いた長屋は軒を材で分けられない ── 軒は越えてよい・施主裁定A)、0 なら全頂点(石垣・練塀・布石)。
    /// 返り値 = 引いた量[m](0 = 元から内・<paramref name="maxPull"/> で収まらなければ動かさず NaN)。<paramref name="before"/> = 引く前の外への出。
    /// ⛔ 伸縮しない(長屋・石垣の駒は長さが決まっている)── 引いた分は隣の駒と重なる(埋めて隠す・docs/oki-kata.md §4)。
    /// 当たる先: 区画の出隅の頂点で止まる直線の run の端の駒(土井 辺12/13・13/14 の表長屋・基壇・練塀。岡部 PlaceOmoteNagaya の
    /// 「隅から走りに沿って 0.02m ずつ引く」は同じ型を邸ビルダーの中で回している)。</summary>
    public static float PullAlongInside(IList<GameObject> gos, Vector2[] poly, Vector2 along, float maxPull, out float before,
                                        float bandH = 0f, float step = 0.005f, float tol = 0.001f)
    {
        before = 0f;
        var pts = new List<Vector3>();
        foreach (var go in gos) if (go != null) pts.AddRange(bandH > 0f ? LowBandPoints(go.transform, bandH) : Body(go.transform, 999999, true));
        if (pts.Count == 0) return float.NaN;
        before = OutsideBy(pts, poly, Vector2.zero);
        if (before <= tol) return 0f;
        along = along.normalized;
        for (float d = step; d <= maxPull + 1e-4f; d += step)
        {
            if (OutsideBy(pts, poly, along * d) > tol) continue;
            foreach (var go in gos) if (go != null) go.transform.position += new Vector3(along.x, 0f, along.y) * d;
            return d;
        }
        return float.NaN;
    }

    /// <summary>据えた城の石垣の区間の**天端(実測の最上点)**と**見付**(天端 − 見え面の足元の前の地表)の [最小, 最大] を測る。
    /// 見え面の足元 = 天端の前の縁から法(駒の実メッシュの、外向きへの地表の高さでの出)の分だけ前。<paramref name="step"/> 刻みで区間を歩く。
    /// 返す: (天端の最小, 天端の最大, 見付の最小, 見付の最大)。駒が無ければ NaN。</summary>
    public static Vector4 CastleCrestExposure(IList<GameObject> pieces, Vector2 outward, Func<float, float, float> groundAt, float step = 0.5f)
    {
        var v = new Vector4(float.NaN, float.NaN, float.NaN, float.NaN);
        if (pieces == null || pieces.Count == 0) return v;
        outward = outward.normalized; Vector2 along = new Vector2(-outward.y, outward.x);
        float tMin = float.MaxValue, tMax = float.MinValue, eMin = float.MaxValue, eMax = float.MinValue;
        foreach (var go in pieces)
        {
            if (go == null) continue;
            var vs = Body(go.transform, 999999); if (vs.Count == 0) continue;
            float top = float.MinValue; foreach (var p in vs) top = Mathf.Max(top, p.y);
            tMin = Mathf.Min(tMin, top); tMax = Mathf.Max(tMax, top);
            float lo = float.MaxValue, hi = float.MinValue, edge = float.MinValue; Vector2 o0 = new Vector2(go.transform.position.x, go.transform.position.z);
            foreach (var p in vs)
            {
                var q = new Vector2(p.x, p.z) - o0; float s = Vector2.Dot(q, along); lo = Mathf.Min(lo, s); hi = Mathf.Max(hi, s);
                if (p.y >= top - 0.15f) edge = Mathf.Max(edge, Vector2.Dot(q, outward));
            }
            for (float s = lo + 0.1f; s <= hi - 0.1f + 1e-4f; s += step)
            {
                // 見え面の足元: 天端の縁から外へ x 出た所の地表で見付 e、法の出 = その高さの駒の外向きの最大
                float x = 0.3f, e = float.NaN;
                for (int it = 0; it < 3; it++)
                {
                    Vector2 g = o0 + along * s + outward * (edge + x); float gy = groundAt(g.x, g.y); if (float.IsNaN(gy)) break;
                    e = top - gy; float reach = float.MinValue;
                    foreach (var p in vs)
                    {
                        if (Mathf.Abs(p.y - gy) > 0.15f) continue; var q = new Vector2(p.x, p.z) - o0;
                        if (Mathf.Abs(Vector2.Dot(q, along) - s) > 0.6f) continue;
                        reach = Mathf.Max(reach, Vector2.Dot(q, outward));
                    }
                    if (reach == float.MinValue) break;
                    x = reach - edge + 0.05f;
                }
                if (float.IsNaN(e)) continue;
                eMin = Mathf.Min(eMin, e); eMax = Mathf.Max(eMax, e);
            }
        }
        if (tMin == float.MaxValue) return v;
        return new Vector4(tMin, tMax, eMin == float.MaxValue ? float.NaN : eMin, eMax == float.MinValue ? float.NaN : eMax);
    }

    /// <summary><see cref="PlaceCastleBack"/> の一区間 = 基壇に載る一棟(長屋・門)の背。</summary>
    public class BackSec
    {
        public string name; public GameObject body; public float crest;
        /// <summary>走りの座標: 辺の始点 origin・走り along・区画の内向き inward(世界 xz・単位)。</summary>
        public Vector2 origin, along, inward;
        /// <summary>口(along の s の [s0, s1])── 棟の通り口。背の基壇もここで切る。</summary>
        public List<Vector2> gaps = new List<Vector2>();
        /// <summary>高い側の端を次の区間の線との交点まで延ばす(区画の出隅の内 = 背の面の入隅)。</summary>
        public bool joinNext;
    }

    /// <summary><see cref="PlaceCastleBack"/> の答え。</summary>
    public class CastleBack
    {
        public List<GameObject> pieces = new List<GameObject>();
        /// <summary>区間の名 → 見え面の駒(背の面)。</summary>
        public Dictionary<string, List<GameObject>> face = new Dictionary<string, List<GameObject>>();
        /// <summary>区間の名 → 外の基壇との間を埋めた駒(長屋の下・見えない)。</summary>
        public Dictionary<string, List<GameObject>> fill = new Dictionary<string, List<GameObject>>();
        /// <summary>区間の名 → (背の面の t, 天端の前の縁の t)(origin から inward への距離・実測の札の背の面から)。</summary>
        public Dictionary<string, Vector2> line = new Dictionary<string, Vector2>();
        /// <summary>区間の名 → 外の基壇の背 と 背の基壇の背 の間の残りの隙[m](天端の高さで・0 = 一つの台)。</summary>
        public Dictionary<string, float> slot = new Dictionary<string, float>();
        public int buried;
    }

    /// <summary>**基壇を棟の背まで通し、背の面も城の石垣で立てる**(2026-10-04・EDO-0533 土井 boundaryPlinth.back)。
    /// <para>手順(置き方の4手): ① 固定側 = 据わった棟。背の面は棟の札の back(局所 −Z の壁体の背)を世界へ写して測る ── ⛔ 外接箱・ピボットで決めない。
    /// ② 天端の前の縁の線 = 背の面から内へ <paramref name="inu"/>(犬走り)。走りの端 = 棟の札の躯体の端(<see cref="SpecBodySpanAlong"/>)、
    /// joinNext の端は次の区間の線との交点(入隅)。天端が同じで線が続く棟は一本に束ねる(天端一直線・段は棟の継ぎ目でだけ)。
    /// ③ <see cref="PlaceCrestWall"/> で見え面を内へ(lowForce)据える ── 天端 = 区間の crest(実測の最上点)。口は棟の通り口で切り、
    /// 口の脇に駒一枚(2.00)に満たない切れ端が残るなら口の縁から一枚を据えて反対の端を隣の区間の裏へ延ばす(隣の天端が同じか高いときだけ)。
    /// ④ 外の基壇の駒の背(<paramref name="outer"/>・局所 +X の鉛直な背)と背の駒の背の間に天端の高さで隙が残れば、背の駒の背の面を
    /// 天端の前の縁にした列を足して埋める(長屋の下 ── 妻の小口と口の脇で地表が見えない一つの台にする)。</para>
    /// <para>硬い(許容0): 天端 = crest・全体が地表の下の駒は置かない(PlaceCrestWall)・札の無い棟は据えない(★)。
    /// 柔らかい: 見付の狙いは呼び手が刷る(<see cref="CastleCrestExposure"/>)。</para>
    /// <para>⭐ <paramref name="stepLap"/> ≥ 0(段の継ぎ目の掛け・2026-10-05 EDO-0533 ── <see cref="PlaceCastleRun"/> の stepLap と同じ作法): 同じ辺で隣の区間の天端が
    /// 低い端では、**高い区間の天端の面を継ぎ目(棟の躯体の端)より <paramref name="stepLap"/> 先まで届かせる** ── 仮に据えた見え面の駒の天端の面(天端 −0.005 より上の頂点)が
    /// 端に届かない分を測り、その分 + stepLap だけ端を低い区間の側へ延ばす(延ばした駒は低い区間の天端の上に立ち、段の小口が掛けの分だけ低い側へ出る)。
    /// 棟の足の端が下の段の天端・地表の上に浮かないため(土井 E13 の表長屋・通用門 E13_N09 ── 第10〜12巡 背の下端 − 下の石の天端 +0.3〜1.5)。
    /// 隣の判定は「同じ辺で端の s を覆うか接する(±0.05)、天端の低い区間」── 口の脇の切れ端を高い区間の裏へ延ばした区間も含む。負(既定)なら延ばさない(従来どおり)。</para>
    /// 当たる先: 外周の基壇に載る表長屋・門の背が内の地表より高い所(土井 boundaryPlinth.back。岡部の表長屋・家臣長屋の背は未適用)。
    /// ⟶ 返す: <see cref="CastleBack"/>(駒・区間ごとの見え面と埋めの駒・線・隙)</summary>
    public static CastleBack PlaceCastleBack(IList<BackSec> secs, float inu, IList<GameObject> outer, Func<float, float, float> groundAt, Transform parent,
                                             System.Text.StringBuilder log, string prefix = "IGB_", float stepLap = -1f)
    {
        var res = new CastleBack();
        if (secs == null || secs.Count == 0) return res;
        var wls = new List<BackWall>();
        foreach (var s in secs)
        {
            var sp = SpecOf(s.body);
            if (sp == null) { log?.AppendLine("  ★ 背の基壇 " + s.name + ": 棟の札が無い ── 背の面が測れず据えない"); continue; }
            var bw = s.body.transform.TransformPoint(new Vector3(0f, 0f, sp.back));
            float tBack = Vector2.Dot(new Vector2(bw.x, bw.z) - s.origin, s.inward);
            var span = SpecBodySpanAlong(s.body, s.origin, s.along);
            if (float.IsNaN(span.x)) { log?.AppendLine("  ★ 背の基壇 " + s.name + ": 札に躯体の端(jamb)が無い ── 据えない"); continue; }
            res.line[s.name] = new Vector2(tBack, tBack + inu);
            var last = wls.Count > 0 ? wls[wls.Count - 1] : null;
            if (last != null && Vector2.Dot(last.along, s.along) > 0.9999f && (last.origin - s.origin).sqrMagnitude < 1e-4f
                && Mathf.Abs(last.t - (tBack + inu)) < 0.005f && Mathf.Abs(last.crest - s.crest) < 1e-3f && Mathf.Abs(last.s1 - span.x) < 0.05f)
            { last.s1 = span.y; last.gaps.AddRange(s.gaps); last.members.Add(s); last.joinNext = s.joinNext; continue; }
            wls.Add(new BackWall { origin = s.origin, along = s.along, inward = s.inward, t = tBack + inu, crest = s.crest, s0 = span.x, s1 = span.y,
                                   gaps = new List<Vector2>(s.gaps), members = new List<BackSec> { s }, joinNext = s.joinNext });
        }
        // 入隅: 天端の前の縁の線どうしの交点へ
        for (int i = 0; i + 1 < wls.Count; i++)
        {
            var A = wls[i]; var B = wls[i + 1]; if (!A.joinNext) continue;
            Vector2 pA = A.origin + A.inward * A.t, pB = B.origin + B.inward * B.t;
            float den = A.along.x * B.along.y - A.along.y * B.along.x; if (Mathf.Abs(den) < 1e-4f) continue;
            Vector2 w = pB - pA; float tA = (w.x * B.along.y - w.y * B.along.x) / den;
            Vector2 X = pA + A.along * tA;
            float sB = Vector2.Dot(X - B.origin, B.along);
            // 交点を越えて相手の天端の奥行(駒の天端 1.4 + 犬走り)まで延ばす ── 越えた分は相手の棟の下に入って隠れ、相手の犬走りの帯を天端で塞ぐ。
            //   ⛔ 棟の端まで延ばさない(端の駒の法の足が隣の辺の線を越える)。
            float over = inu + 1.4f;
            float a1 = Mathf.Min(A.s1, tA + over), b0 = Mathf.Max(B.s0, sB - over);
            log?.AppendLine("  背の基壇 " + A.members[A.members.Count - 1].name + "|" + B.members[0].name + ": 入隅 ── 天端の前の縁の線の交点(s " + tA.ToString("F2") + " / " + sB.ToString("F2") + ")から相手の天端の奥行 "
                            + over.ToString("F2") + "m まで延ばした(高い側の端 s " + A.s1.ToString("F2") + "→" + a1.ToString("F2") + " / 低い側の端 s " + B.s0.ToString("F2") + "→" + b0.ToString("F2") + ")");
            A.s1 = a1; B.s0 = b0;
        }
        // 口で割り、切れ端は口の縁から一枚 ── 反対の端を隣(線が続き天端が同じか高い)の裏へ
        var subs = new List<BackWall>();
        for (int i = 0; i < wls.Count; i++)
        {
            var w = wls[i];
            var cuts = new List<Vector2> { new Vector2(w.s0, w.s1) };
            foreach (var g in w.gaps)
            {
                var nx = new List<Vector2>();
                foreach (var q in cuts) { if (g.y <= q.x || g.x >= q.y) { nx.Add(q); continue; } if (g.x > q.x) nx.Add(new Vector2(q.x, g.x)); if (g.y < q.y) nx.Add(new Vector2(g.y, q.y)); }
                cuts = nx;
            }
            for (int k = 0; k < cuts.Count; k++)
            {
                float a0 = cuts[k].x, a1 = cuts[k].y;
                if (a1 - a0 < 0.3f) continue;
                if (a1 - a0 < 2.0f && w.gaps.Count > 0)
                {
                    bool gapLo = w.gaps.Exists(g => Mathf.Abs(g.y - a0) < 1e-3f), gapHi = w.gaps.Exists(g => Mathf.Abs(g.x - a1) < 1e-3f);
                    BackWall nbHi = i + 1 < wls.Count && Mathf.Abs(wls[i + 1].s0 - w.s1) < 0.05f && Mathf.Abs(wls[i + 1].t - w.t) < 0.005f ? wls[i + 1] : null;
                    BackWall nbLo = i > 0 && Mathf.Abs(wls[i - 1].s1 - w.s0) < 0.05f && Mathf.Abs(wls[i - 1].t - w.t) < 0.005f ? wls[i - 1] : null;
                    float L0 = a1 - a0;
                    if (gapLo && !gapHi && Mathf.Abs(a1 - w.s1) < 1e-3f && nbHi != null && nbHi.crest >= w.crest - 1e-3f) a1 = a0 + 2.0f;
                    else if (gapHi && !gapLo && Mathf.Abs(a0 - w.s0) < 1e-3f && nbLo != null && nbLo.crest >= w.crest - 1e-3f) a0 = a1 - 2.0f;
                    if (a1 - a0 > L0 + 1e-3f) log?.AppendLine("  背の基壇 " + w.members[0].name + ": 口の脇の切れ端 " + L0.ToString("F2") + "m ⇒ 口の縁から一枚・反対の端を隣の高い区間の裏へ延ばした");
                    else log?.AppendLine("  ⚠ 背の基壇 " + w.members[0].name + ": 口の脇の切れ端 " + L0.ToString("F2") + "m ── 隣が低く裏へ延ばせない(駒一枚 2.00 が両側へはみ出す)");
                }
                subs.Add(new BackWall { origin = w.origin, along = w.along, inward = w.inward, t = w.t, crest = w.crest, s0 = a0, s1 = a1, members = w.members, gaps = new List<Vector2>(), key = "_k" + k });
            }
        }
        // 段の継ぎ目の掛け(stepLap ≥ 0)── 天端の低い隣へ向く端を、仮に据えた見え面の天端の面の届かない分 + stepLap だけ延ばす
        var lapLog = new List<KeyValuePair<BackWall, Vector2>>();   // (区間, (延ばした低い側の端の s・高い側の端の s) ── NaN = 延ばさない)
        if (stepLap >= 0f)
        {
            Func<BackWall, BackWall, bool> sameLine = (x, y) => Vector2.Dot(x.along, y.along) > 0.9999f && (x.origin - y.origin).sqrMagnitude < 1e-4f;
            // 端 s の低い側の隣: 同じ辺で s を覆うか接し、天端が低い
            Func<BackWall, bool, BackWall> lowerAt = (w, hiEnd) =>
            {
                float se = hiEnd ? w.s1 : w.s0;
                return subs.Find(x => x != w && sameLine(x, w) && x.crest < w.crest - 1e-3f
                                      && (hiEnd ? (x.s0 <= se + 0.05f && x.s1 > se + 0.05f) : (x.s1 >= se - 0.05f && x.s0 < se - 0.05f)));
            };
            Func<List<GameObject>, BackWall, Vector2> crestSpan = (gos, w) =>
            {
                float lo = float.MaxValue, hi = float.MinValue;
                foreach (var go in gos) { if (go == null) continue; foreach (var v in Body(go.transform, 999999)) if (v.y >= w.crest - 0.005f) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.along); lo = Mathf.Min(lo, sv); hi = Mathf.Max(hi, sv); } }
                return new Vector2(lo, hi);
            };
            var newS = new Dictionary<BackWall, Vector2>();
            foreach (var w in subs)
            {
                var nbLo = lowerAt(w, false); var nbHi = lowerAt(w, true);
                if (nbLo == null && nbHi == null) continue;
                Vector2 a = w.origin + w.along * w.s0 + w.inward * w.t, b = w.origin + w.along * w.s1 + w.inward * w.t;
                var inw = w.inward;
                var pcw = new CrestWall { name = prefix + "Probe_" + w.members[0].name + w.key, nodes = new List<Vector2> { a, b }, nodeTops = new List<float> { w.crest, w.crest }, gaps = new List<Vector2>(),
                                          pathOfH = CastleWallOfExpose, runAlongX = false, runLen = 2.0f, pitchMax = 1.8f, lowHint = (p, q) => inw, lowForce = true };
                float pwf; int pbs;
                var probe = PlaceCrestWall(pcw, groundAt, parent, null, null, new System.Text.StringBuilder(), out pwf, out pbs);
                var sp = crestSpan(probe, w);
                foreach (var go in probe) if (go != null) UnityEngine.Object.DestroyImmediate(go);
                if (sp.x > sp.y) continue;
                float s0n = nbLo != null ? w.s0 - (Mathf.Max(0f, sp.x - w.s0) + stepLap) : w.s0;
                float s1n = nbHi != null ? w.s1 + (Mathf.Max(0f, w.s1 - sp.y) + stepLap) : w.s1;
                newS[w] = new Vector2(s0n, s1n);
                lapLog.Add(new KeyValuePair<BackWall, Vector2>(w, new Vector2(nbLo != null ? w.s0 : float.NaN, nbHi != null ? w.s1 : float.NaN)));
            }
            foreach (var kv in newS) { kv.Key.s0 = kv.Value.x; kv.Key.s1 = kv.Value.y; }
        }
        foreach (var w in subs)
        {
            string nm0 = w.members[0].name;
            Func<float, string, List<GameObject>> row = (t, tag) =>
            {
                Vector2 a = w.origin + w.along * w.s0 + w.inward * t, b = w.origin + w.along * w.s1 + w.inward * t;
                var inw = w.inward;
                var cw = new CrestWall { name = prefix + tag + nm0 + w.key, nodes = new List<Vector2> { a, b }, nodeTops = new List<float> { w.crest, w.crest }, gaps = new List<Vector2>(),
                                         pathOfH = CastleWallOfExpose, runAlongX = false, runLen = 2.0f, pitchMax = 1.8f, lowHint = (p, q) => inw, lowForce = true };
                float wf; int bs;
                var got = PlaceCrestWall(cw, groundAt, parent, null, null, log ?? new System.Text.StringBuilder(), out wf, out bs);
                res.buried += bs; res.pieces.AddRange(got);
                return got;
            };
            var faceP = row(w.t, "");
            // 区間の名へ振り分け(駒の芯の s)
            Action<List<GameObject>, Dictionary<string, List<GameObject>>> assign = (gos, dict) =>
            {
                foreach (var m in w.members) if (!dict.ContainsKey(m.name)) dict[m.name] = new List<GameObject>();
                foreach (var go in gos)
                {
                    var c = RB(go).center; float sc = Vector2.Dot(new Vector2(c.x, c.z) - w.origin, w.along);
                    var pick = w.members[0]; float best = float.MaxValue;
                    foreach (var m in w.members)
                    {
                        var sp = SpecBodySpanAlong(m.body, w.origin, w.along);
                        float d = sc < sp.x ? sp.x - sc : (sc > sp.y ? sc - sp.y : 0f); if (d < best) { best = d; pick = m; }
                    }
                    dict[pick.name].Add(go);
                }
            };
            assign(faceP, res.face);
            // ④ 外の基壇の背との隙を埋める
            Func<List<GameObject>, float> backOf = gos => { float mn = float.MaxValue; foreach (var go in gos) foreach (var v in Body(go.transform, 999999)) mn = Mathf.Min(mn, Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.inward)); return mn; };
            float tOuter = float.MinValue;
            if (outer != null)
                foreach (var go in outer)
                {
                    if (go == null) continue;
                    var r = go.transform.right; if (Vector2.Dot(new Vector2(r.x, r.z).normalized, w.inward) < 0.99f) continue;   // 外の駒(見え面 = 局所 −X が外)
                    foreach (var v in Body(go.transform, 999999))
                    {
                        float sv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.along); if (sv < w.s0 - 0.01f || sv > w.s1 + 0.01f) continue;
                        float tv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.inward); if (tv > w.t) continue;
                        tOuter = Mathf.Max(tOuter, tv);
                    }
                }
            float tb = faceP.Count > 0 ? backOf(faceP) : w.t;
            var fillAll = new List<GameObject>();
            for (int k = 0; k < 3 && tOuter > float.MinValue && tb - tOuter > 0.01f; k++)
            {
                var f = row(tb, "F" + k + "_");
                if (f.Count == 0) break;
                fillAll.AddRange(f); tb = Mathf.Min(tb, backOf(f));
            }
            assign(fillAll, res.fill);
            float slot = tOuter > float.MinValue ? Mathf.Max(0f, tb - tOuter) : float.NaN;
            foreach (var m in w.members) res.slot[m.name] = res.slot.ContainsKey(m.name) && !float.IsNaN(res.slot[m.name]) ? Mathf.Max(res.slot[m.name], slot) : slot;
            log?.AppendLine("  背の基壇 " + nm0 + w.key + ": s " + w.s0.ToString("F2") + "〜" + w.s1.ToString("F2") + "・天端 " + w.crest.ToString("F2") + "・見え面 " + faceP.Count + " 駒・埋め " + fillAll.Count + " 駒・外の基壇の背との隙 "
                            + (float.IsNaN(slot) ? "外の駒なし" : slot.ToString("F3")) + "m");
            // 段の継ぎ目の掛けの検め(硬い ── 見え面の天端の面が元の端を stepLap 越える)
            foreach (var kv in lapLog)
            {
                if (kv.Key != w) continue;
                float lo = float.MaxValue, hi = float.MinValue;
                foreach (var go in faceP) { if (go == null) continue; foreach (var v in Body(go.transform, 999999)) if (v.y >= w.crest - 0.005f) { float sv = Vector2.Dot(new Vector2(v.x, v.z) - w.origin, w.along); lo = Mathf.Min(lo, sv); hi = Mathf.Max(hi, sv); } }
                if (!float.IsNaN(kv.Value.x)) log?.AppendLine("  " + (lo <= kv.Value.x + 1e-3f ? "⭕" : "★") + " 背の基壇 " + nm0 + w.key + ": 低い側の段の継ぎ目(s=" + kv.Value.x.ToString("F2") + ")へ天端の面を延ばした ⇒ 天端の面の端 s=" + lo.ToString("F3") + "(継ぎ目を " + (kv.Value.x - lo).ToString("+0.000;-0.000") + "m 越える・掛け " + stepLap.ToString("F2") + ")");
                if (!float.IsNaN(kv.Value.y)) log?.AppendLine("  " + (hi >= kv.Value.y - 1e-3f ? "⭕" : "★") + " 背の基壇 " + nm0 + w.key + ": 高い側の端の隣が低い段の継ぎ目(s=" + kv.Value.y.ToString("F2") + ")へ天端の面を延ばした ⇒ 天端の面の端 s=" + hi.ToString("F3") + "(継ぎ目を " + (hi - kv.Value.y).ToString("+0.000;-0.000") + "m 越える)");
            }
        }
        return res;
    }

    class BackWall
    {
        public Vector2 origin, along, inward; public float t, crest, s0, s1; public bool joinNext; public string key = "";
        public List<Vector2> gaps = new List<Vector2>(); public List<BackSec> members = new List<BackSec>();
    }

    /// <summary>据えた棟の**背の下端 − 下の石垣の天端**[m](浮き = 正・めり込み = 負)。背の面から棟の内へ <paramref name="band"/> の帯の躯体を
    /// 走りの 0.25m 刻みの筋に割り、筋ごとの最下点と、その点を含む石垣の駒(<paramref name="stones"/> ── 背の基壇・埋め・外の基壇・隣の辺の基壇の全て)
    /// の天端(実測の最上点)の差を取る。口 <paramref name="skipS"/> の中は除く。返す: 絶対値の最悪(符号付き)。<paramref name="bare"/> = 下に石の無い筋の数。
    /// 当たる先: <see cref="PlaceCastleBack"/> の検め(土井の表長屋・門)。</summary>
    public static float BackBedGap(GameObject body, IList<GameObject> stones, Vector2 origin, Vector2 along, Vector2 inward, float tBack, IList<Vector2> skipS, out int bare, float band = 0.3f,
                                   IList<GameObject> others = null)
    {
        // 他の棟の躯体の中(札の jamb × back〜front)に入る頂点は見えない ── 出隅の内で棟どうしが重なる所(土井 辺12/13)
        Func<Vector3, bool> hidden = v =>
        {
            if (others == null) return false;
            foreach (var o in others)
            {
                if (o == null || o == body) continue; var sp = SpecOf(o); if (sp == null || sp.jambL == null || sp.jambR == null) continue;
                var l = o.transform.InverseTransformPoint(v);
                if (l.x > Mathf.Min(sp.jambL.x, sp.jambR.x) + 0.01f && l.x < Mathf.Max(sp.jambL.x, sp.jambR.x) - 0.01f && l.z > sp.back + 0.01f && l.z < sp.front - 0.01f) return true;
            }
            return false;
        };
        bare = 0;
        if (body == null || stones == null || stones.Count == 0) return float.NaN;
        var bins = new Dictionary<int, Vector3>();
        var vs = Body(body.transform, 999999);
        Func<float, bool> inGap = sv => { if (skipS != null) foreach (var g in skipS) if (sv > g.x - 0.05f && sv < g.y + 0.05f) return true; return false; };
        float lo = float.MaxValue;
        foreach (var v in vs)
        {
            var q0 = new Vector2(v.x, v.z); float t = Vector2.Dot(q0 - origin, inward);
            if (t <= tBack + 0.01f && t >= tBack - band && !inGap(Vector2.Dot(q0 - origin, along))) lo = Mathf.Min(lo, v.y);
        }
        foreach (var v in vs)
        {
            if (v.y > lo + 0.3f) continue;   // 土台の帯だけ(二階の壁・軒の頂点を筋の最下点に拾わない)
            var q = new Vector2(v.x, v.z); float t = Vector2.Dot(q - origin, inward); if (t > tBack + 0.01f || t < tBack - band) continue;
            float s = Vector2.Dot(q - origin, along); bool skip = false;
            if (skipS != null) foreach (var g in skipS) if (s > g.x - 0.05f && s < g.y + 0.05f) skip = true;
            if (skip) continue;
            int k = Mathf.FloorToInt(s / 0.25f); Vector3 cur;
            if (!bins.TryGetValue(k, out cur) || v.y < cur.y) bins[k] = v;
        }
        if (bins.Count == 0) return float.NaN;
        // 駒の箱は走りの座標(s, t)で取る ── 世界の外接箱は斜めの辺で走りの端より膨らみ、継ぎ目の頂点が高い隣の天端を拾って偽のめり込みになる
        var boxes = new List<Vector4>(); var tops = new List<float>();
        foreach (var go in stones)
        {
            if (go == null) continue; float s0 = float.MaxValue, s1 = float.MinValue, t0 = float.MaxValue, t1 = float.MinValue, top = float.MinValue;
            foreach (var v in Body(go.transform, 999999)) { var q = new Vector2(v.x, v.z) - origin; float sv = Vector2.Dot(q, along), tv = Vector2.Dot(q, inward); s0 = Mathf.Min(s0, sv); s1 = Mathf.Max(s1, sv); t0 = Mathf.Min(t0, tv); t1 = Mathf.Max(t1, tv); top = Mathf.Max(top, v.y); }
            if (top == float.MinValue) continue; boxes.Add(new Vector4(s0, s1, t0, t1)); tops.Add(top);
        }
        float worst = float.NaN;
        foreach (var kv in bins)
        {
            var at = new Vector2(kv.Value.x, kv.Value.z) - origin; float sa = Vector2.Dot(at, along), ta = Vector2.Dot(at, inward), crest = float.MinValue;
            for (int i = 0; i < boxes.Count; i++) { var b = boxes[i]; if (sa < b.x + 0.01f || sa > b.y - 0.01f || ta < b.z - 0.01f || ta > b.w + 0.01f) continue; crest = Mathf.Max(crest, tops[i]); }
            if (crest == float.MinValue)   // 継ぎ目の上の頂点: 端で接する駒のうち低い方(自分の区間の駒)
            {
                float lowTop = float.MaxValue;
                for (int i = 0; i < boxes.Count; i++) { var b = boxes[i]; if (sa < b.x - 0.01f || sa > b.y + 0.01f || ta < b.z - 0.01f || ta > b.w + 0.01f) continue; lowTop = Mathf.Min(lowTop, tops[i]); }
                if (lowTop != float.MaxValue) crest = lowTop;
            }
            if (crest == float.MinValue) { if (!hidden(kv.Value)) bare++; continue; }
            float g = kv.Value.y - crest; if (float.IsNaN(worst) || Mathf.Abs(g) > Mathf.Abs(worst)) worst = g;
        }
        return worst;
    }
}
