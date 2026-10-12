using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 塀の天端の線を指図の値から一本に解き、平ら・坂なり・段の区間で練塀を据える(施主裁定 2026-10-12 案1・岡部 const.heiLine.tenba・EDO-0502 第121巡)。
// ⛔ 棟梁が地形から段の点を選ばない(旧 HeiTenbaSteps の DP は案A の試しの物)── 段の点・座は指図が持つ。ここは線を解いて駒を据えるだけ。
// ⛔ 部材の基準点で位置を決めない ── 駒の高さは据えた駒の実メッシュの底(走りの両端の足)で測って線へ合わせる。
public static partial class EdoBuild
{
    /// <summary>天端の線の決めた座(指図の値)── 辺 edge の走り s の座 y。s &lt; 0 = 辺の終わり(次の頂点)・s = 0 = 辺の始まりの頂点。
    /// 頂点の座は芯線の折れ点(両辺の芯線の交点)の座として読む。</summary>
    public struct HeiKnot { public int edge; public float s, y; }
    /// <summary>天端の段(指図の値)── 辺 edge の走り s に高さ h の段(向きは線の上り下りに従う)。段の面 = 上下の段の棟止めの端の柱の外面が背中合わせになる面。</summary>
    public struct HeiStep { public int edge; public float s, h; }

    /// <summary>芯線に沿う天端の線(<see cref="HeiTenbaProfile"/> の答え)。t = 芯線の道のり(範囲の始めの折れ点から)。節点ごとに左と右の値(段は左右が違う)。</summary>
    public class HeiProfile
    {
        public int e0, e1; public bool ok = true;
        public readonly List<float> nt = new List<float>(), nyL = new List<float>(), nyR = new List<float>();
        public readonly Dictionary<int, float> tStart = new Dictionary<int, float>(), sC = new Dictionary<int, float>(), sCend = new Dictionary<int, float>();
        public readonly List<HeiStep> steps = new List<HeiStep>(); public readonly List<float> stepT = new List<float>();
        /// <summary>芯線の道のり t の座(side −1 = 左の値・+1 = 右の値 ── 段の点で違う)。範囲の外は端の勾配で延ばす。</summary>
        public float Y(float t, int side)
        {
            int n = nt.Count; if (n == 0) return float.NaN; if (n == 1) return nyR[0];
            if (t <= nt[0]) return nyR[0] + (nyL[1] - nyR[0]) / Mathf.Max(1e-4f, nt[1] - nt[0]) * (t - nt[0]);
            if (t >= nt[n - 1]) return nyL[n - 1] + (nyL[n - 1] - nyR[n - 2]) / Mathf.Max(1e-4f, nt[n - 1] - nt[n - 2]) * (t - nt[n - 1]);
            for (int i = 0; i + 1 < n; i++)
            {
                if (Mathf.Abs(t - nt[i]) < 1e-4f) return side < 0 ? nyL[i] : nyR[i];
                if (t > nt[i] && t < nt[i + 1]) return nyR[i] + (nyL[i + 1] - nyR[i]) * (t - nt[i]) / (nt[i + 1] - nt[i]);
            }
            return side < 0 ? nyL[n - 1] : nyR[n - 1];
        }
        /// <summary>道のり t の勾配(side −1 = 手前の区間・+1 = 先の区間)。</summary>
        public float Grade(float t, int side)
        {
            int n = nt.Count; if (n < 2) return 0f;
            for (int i = 0; i + 1 < n; i++)
            {
                bool inI = side < 0 ? (t > nt[i] + 1e-4f && t <= nt[i + 1] + 1e-4f) : (t >= nt[i] - 1e-4f && t < nt[i + 1] - 1e-4f);
                if (inI) return (nyL[i + 1] - nyR[i]) / Mathf.Max(1e-4f, nt[i + 1] - nt[i]);
            }
            return side < 0 ? (nyL[n - 1] - nyR[n - 2]) / Mathf.Max(1e-4f, nt[n - 1] - nt[n - 2]) : (nyL[1] - nyR[0]) / Mathf.Max(1e-4f, nt[1] - nt[0]);
        }
        /// <summary>辺 e の走り s → 芯線の道のり t(辺に平行な芯線へ直角に写す ⇒ 辺の中は s と一対一・頂点の近くは折れ点を通る)。</summary>
        public float TOf(int e, float s) { return tStart[e] + (s - sC[e]); }
        /// <summary>辺 e の走り s の座(芯線へ写した点)。</summary>
        public float YAt(int e, float s, int side) { return Y(TOf(e, s), side); }
        /// <summary>段の数(道のり t までの・t ちょうどの段を含めるか)。区間の番号に使う。</summary>
        public int StepsBefore(float t, bool inclusive) { int c = 0; foreach (var st in stepT) if (inclusive ? st <= t + 1e-3f : st < t - 1e-3f) c++; return c; }
        public bool IsStepAt(float t) { foreach (var st in stepT) if (Mathf.Abs(st - t) < 2e-3f) return true; return false; }
    }

    /// <summary>**塀の天端の線を指図の値から一本に解く**(施主裁定 2026-10-12 案1・const.heiLine.tenba)── 辺 e0〜e1 の芯線(区画の線から内へ d[e] + <paramref name="coreIn"/>・
    /// 頂点は両辺の芯線の交点 = 隅の駒の折れ点)の道のり t に沿って、決めた座(<paramref name="knots"/>)の間を一様な勾配で結び、段(<paramref name="steps"/>)はその間で
    /// 線の上り下りの向きに h だけ落とす ⇒ 段の間の踏み面の勾配 g = (Δy − Σh)/Δt(段の間も坂なり)。決めた座の点ちょうどの段は、他の段を含む側の区間へ入れる
    /// (案1 の 辺21 s5.50 = 段の手前の座・辺22 s2.72 = 段の先の座)。
    /// 【硬】|g| ≤ <paramref name="maxGrade"/>(越えたら ok = false・★ ── 呼び手は建てずに返す)・段の点の外で天端の段 0(線が一本)・同じ点の座の食い違い ≤0.005(越えたら ★)。
    /// 1/20 以下も勾配のまま(坂なりの駒・平らと同じ作り)。⛔ 部材の基準点を使わない(線を決めるだけ)。当たる先: 岡部の外周の練塀(SE 辺1〜11・SW 辺19〜24・N 辺28〜38)。</summary>
    public static HeiProfile HeiTenbaProfile(Vector2[] poly, int e0, int e1, float[] d, float coreIn, List<HeiKnot> knots, List<HeiStep> steps, float maxGrade, out string note)
    { return HeiTenbaProfile(poly, e0, e1, d, coreIn, knots, steps, maxGrade, 0f, null, out note); }
    /// <summary><paramref name="stepClear"/> &gt; 0: 範囲の中の頂点 v(<paramref name="hasKado"/>(v) = 隅の駒が立つ)の折れ点から芯線の道のり stepClear の内に入る段は、
    /// 段が書かれた辺の側(入りの辺 = 折れ点の手前・出の辺 = 先)の stepClear の所へ寄せる ⚠【柔】(隅の駒は一つの駒 ⇒ 腕の中で段を切れない・腕の最短 + 棟止めの端の柱 = stepClear)。
    /// 寄せた段は答えの steps の s を書き直す(呼び手の腕の詰めが読む)。</summary>
    public static HeiProfile HeiTenbaProfile(Vector2[] poly, int e0, int e1, float[] d, float coreIn, List<HeiKnot> knots, List<HeiStep> steps, float maxGrade,
                                             float stepClear, Func<int, bool> hasKado, out string note)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture; var sb = new System.Text.StringBuilder();
        int n = poly.Length; var pf = new HeiProfile { e0 = e0, e1 = e1 };
        Func<int, int> W = k => ((k % n) + n) % n;
        Func<int, float> wOf = e => d[e - e0] + coreIn;
        Func<int, Vector2> U = e => (poly[W(e + 1)] - poly[W(e)]).normalized;
        Func<int, Vector2> Inw = e => EdoGeom.InwardNormal(poly, W(e));
        // 芯線の頂点 C[v](v = e0..e1+1)── 範囲の中は両辺の芯線の交点・両端は直角に控えた点
        var C = new Dictionary<int, Vector2>();
        for (int v = e0; v <= e1 + 1; v++)
        {
            if (v == e0) { C[v] = poly[W(v)] + Inw(v) * wOf(v); continue; }
            if (v == e1 + 1) { C[v] = poly[W(v)] + Inw(v - 1) * wOf(v - 1); continue; }
            Vector2 p1 = poly[W(v)] + Inw(v - 1) * wOf(v - 1), u1 = U(v - 1), p2 = poly[W(v)] + Inw(v) * wOf(v), u2 = U(v);
            float den = u1.x * u2.y - u1.y * u2.x;
            if (Mathf.Abs(den) < 1e-5f) { C[v] = 0.5f * (p1 + p2); continue; }
            Vector2 w = p2 - p1; float tt = (w.x * u2.y - w.y * u2.x) / den; C[v] = p1 + u1 * tt;
        }
        float T = 0f;
        for (int e = e0; e <= e1; e++)
        {
            int ee = W(e); float a = Vector2.Dot(C[e] - poly[ee], U(e)), b = Vector2.Dot(C[e + 1] - poly[ee], U(e));
            pf.sC[ee] = a; pf.sCend[ee] = b; pf.tStart[ee] = T; T += b - a;
        }
        float Tend = T;
        Func<int, float, float> tOfKnot = (e, s) =>
        {
            int ee = W(e); float L = (poly[W(e + 1)] - poly[ee]).magnitude;
            if (s < 0f || Mathf.Abs(s - L) < 1e-3f) return pf.tStart[ee] + (pf.sCend[ee] - pf.sC[ee]);   // 辺の終わり = 次の折れ点
            if (s < 1e-3f) return pf.tStart[ee];                                                         // 辺の始まり = 折れ点
            return pf.tStart[ee] + (s - pf.sC[ee]);
        };
        // 決めた座を道のりの順に・同じ点は一つ
        var K = new List<Vector2>();
        foreach (var k in knots)
        {
            if (!pf.tStart.ContainsKey(W(k.edge))) continue;
            float t = tOfKnot(k.edge, k.s); int j = K.FindIndex(q => Mathf.Abs(q.x - t) < 0.01f);
            if (j >= 0) { if (Mathf.Abs(K[j].y - k.y) > 0.005f) { sb.Append("★ 同じ点(t " + t.ToString("F2", inv) + ")に座が二つ " + K[j].y.ToString("F3", inv) + " / " + k.y.ToString("F3", inv) + " ── 先の値を採る; "); pf.ok = false; } continue; }
            K.Add(new Vector2(t, k.y));
        }
        K.Sort((p, q) => p.x.CompareTo(q.x));
        if (K.Count < 2) { note = "★ 天端の線: 範囲 辺" + e0 + "〜" + e1 + " に決めた座が " + K.Count + " 点 ── 解けない"; pf.ok = false; return pf; }
        if (K[0].x > 0.05f || K[K.Count - 1].x < Tend - 0.05f) sb.Append("⚠ 決めた座が範囲の両端に無い(t " + K[0].x.ToString("F2", inv) + "〜" + K[K.Count - 1].x.ToString("F2", inv) + " / 範囲 0〜" + Tend.ToString("F2", inv) + ")── 端の勾配で延ばす; ");
        // 段を道のりへ
        var ST = new List<KeyValuePair<float, HeiStep>>();
        foreach (var st0 in steps)
        {
            var st = st0; if (!pf.tStart.ContainsKey(W(st.edge))) continue; float t = pf.TOf(W(st.edge), st.s);
            if (stepClear > 0f)
            {
                int vIn = st.edge + 1, vOut = st.edge;   // 入りの辺として終わりの頂点・出の辺として始まりの頂点
                if (vIn > e0 && vIn <= e1 && (hasKado == null || hasKado(W(vIn)))) { float tf = pf.tStart[W(vIn)]; if (t > tf - stepClear) { float t2 = tf - stepClear; sb.Append("⚠ 段 辺" + W(st.edge) + " s" + st.s.ToString("F2", inv) + " は P" + W(vIn) + " の隅の駒の中(折れ点から " + (t - tf).ToString("+0.00;-0.00", inv) + ")── 手前 " + stepClear.ToString("F2", inv) + " へ " + (t2 - t).ToString("+0.00;-0.00", inv) + " 寄せた; "); st.s += t2 - t; t = t2; } }
                if (vOut > e0 && vOut <= e1 && (hasKado == null || hasKado(W(vOut)))) { float tf = pf.tStart[W(vOut)]; if (t < tf + stepClear) { float t2 = tf + stepClear; sb.Append("⚠ 段 辺" + W(st.edge) + " s" + st.s.ToString("F2", inv) + " は P" + W(vOut) + " の隅の駒の中(折れ点から " + (t - tf).ToString("+0.00;-0.00", inv) + ")── 先 " + stepClear.ToString("F2", inv) + " へ " + (t2 - t).ToString("+0.00;-0.00", inv) + " 寄せた; "); st.s += t2 - t; t = t2; } }
            }
            ST.Add(new KeyValuePair<float, HeiStep>(t, st));
        }
        ST.Sort((p, q) => p.Key.CompareTo(q.Key));
        // 段を区間へ割り当てる(点ちょうどの段は、他の段を含む側)
        int m = K.Count - 1; var inside = new List<List<KeyValuePair<float, HeiStep>>>(); for (int i = 0; i < m; i++) inside.Add(new List<KeyValuePair<float, HeiStep>>());
        var onKnot = new List<KeyValuePair<int, KeyValuePair<float, HeiStep>>>();
        foreach (var kv in ST)
        {
            float t = kv.Key; int hit = -1;
            for (int i = 0; i <= m; i++) if (Mathf.Abs(t - K[i].x) < 0.01f) hit = i;
            if (hit >= 0) { onKnot.Add(new KeyValuePair<int, KeyValuePair<float, HeiStep>>(hit, kv)); continue; }
            int seg = -1; for (int i = 0; i < m; i++) if (t > K[i].x && t < K[i + 1].x) seg = i;
            if (seg < 0) { sb.Append("★ 段 辺" + kv.Value.edge + " s" + kv.Value.s.ToString("F2", inv) + " が決めた座の範囲の外 ── 捨てた; "); pf.ok = false; continue; }
            inside[seg].Add(kv);
        }
        var assigned = new List<List<KeyValuePair<float, HeiStep>>>(); for (int i = 0; i < m; i++) assigned.Add(new List<KeyValuePair<float, HeiStep>>(inside[i]));
        foreach (var ok in onKnot)
        {
            int i = ok.Key; bool before = i > 0 && inside[i - 1].Count > 0, after = i < m && inside[i].Count > 0;
            int seg = after ? i : (before ? i - 1 : (i < m ? i : i - 1));
            if (before && after) { sb.Append("⚠ 段 辺" + ok.Value.Value.edge + " s" + ok.Value.Value.s.ToString("F2", inv) + " は決めた座の点ちょうどで両側に段がある ── 先の区間へ入れた; "); }
            // 両側とも他に段が無い: 他の点ちょうどの段と同じ区間へ(無ければ先)
            if (!before && !after) foreach (var o2 in onKnot) if (o2.Key != i && (o2.Key == i + 1 || o2.Key == i - 1)) { seg = Mathf.Min(i, o2.Key); break; }
            assigned[seg].Add(ok.Value);
        }
        // 区間ごとに踏み面の勾配を解き、節点を並べる
        pf.nt.Add(K[0].x); pf.nyL.Add(K[0].y); pf.nyR.Add(K[0].y);
        for (int i = 0; i < m; i++)
        {
            var A2 = assigned[i]; A2.Sort((p, q) => p.Key.CompareTo(q.Key));
            float t0 = K[i].x, t1 = K[i + 1].x, dy = K[i + 1].y - K[i].y, sumH = 0f; foreach (var kv in A2) sumH += kv.Value.h;
            float sgn = A2.Count == 0 ? 0f : Mathf.Sign(dy);
            if (A2.Count > 0 && Mathf.Abs(dy) < 1e-4f) { sb.Append("★ 区間 t " + t0.ToString("F2", inv) + "〜" + t1.ToString("F2", inv) + " は上り下りが無いのに段がある; "); pf.ok = false; }
            float g = (dy - sgn * sumH) / Mathf.Max(1e-4f, t1 - t0);
            if (Mathf.Abs(g) > maxGrade + 2e-4f) { sb.Append("★ 区間 t " + t0.ToString("F2", inv) + "〜" + t1.ToString("F2", inv) + " の勾配 " + (g * 100f).ToString("F2", inv) + "% が上限 " + (maxGrade * 100f).ToString("F1", inv) + "% を越える; "); pf.ok = false; }
            float y = K[i].y; float tp = t0;
            // 区間の始めちょうどの段
            foreach (var kv in A2)
            {
                float ts = kv.Key; y += g * (ts - tp); tp = ts;
                float yR = y + sgn * kv.Value.h;   // 段は線の上り下りの向きへ
                int last = pf.nt.Count - 1;
                if (Mathf.Abs(pf.nt[last] - ts) < 1e-3f) { pf.nyR[last] = yR; }
                else { pf.nt.Add(ts); pf.nyL.Add(y); pf.nyR.Add(yR); }
                y = yR; pf.steps.Add(kv.Value); pf.stepT.Add(ts);
            }
            y += g * (t1 - tp);
            float resid = y - K[i + 1].y;
            int lst = pf.nt.Count - 1;
            if (Mathf.Abs(resid) > 0.002f) { sb.Append("★ 区間 t " + t0.ToString("F2", inv) + "〜" + t1.ToString("F2", inv) + " の終わりの残差 " + resid.ToString("+0.000;-0.000", inv) + "; "); pf.ok = false; }
            if (Mathf.Abs(pf.nt[lst] - t1) < 1e-3f) pf.nyR[lst] = K[i + 1].y;
            else { pf.nt.Add(t1); pf.nyL.Add(K[i + 1].y); pf.nyR.Add(K[i + 1].y); }
            sb.Append("[t " + t0.ToString("F2", inv) + "〜" + t1.ToString("F2", inv) + " 座 " + K[i].y.ToString("F3", inv) + "→" + K[i + 1].y.ToString("F3", inv) + (A2.Count > 0 ? "・段 " + A2.Count + "(Σh " + sumH.ToString("F3", inv) + ")" : "") + "・勾配 " + (g * 100f).ToString("F2", inv) + "%] ");
        }
        // 範囲の外へ延ばす(端の座が範囲の端に無いとき)── Y が端の勾配で延ばす
        note = "天端の線 辺" + W(e0) + "〜" + W(e1) + "(芯線 " + Tend.ToString("F2", inv) + "m・決めた座 " + K.Count + "・段 " + pf.steps.Count + ")" + (pf.ok ? "" : " ★") + ": " + sb.ToString();
        return pf;
    }

    /// <summary>天端の線(<see cref="HeiTenbaProfile"/>)を辺ごとの区間(走り s0〜s1・始めの座 seat・勾配 grade[走り 1m あたり]・段の後の通し番号 sec・始めが段か stepAt0)へ割る。
    /// 区間の切れ目 = 段・決めた座の点(勾配の変わる所)・芯線の折れ点の写し。走り s は辺の線のまま(芯線へは直角に写す)。</summary>
    public static List<HeiSec> HeiProfileRows(HeiProfile pf, Vector2[] poly)
    {
        var rows = new List<HeiSec>(); int n = poly.Length;
        for (int e = pf.e0; e <= pf.e1; e++)
        {
            int ee = ((e % n) + n) % n; float L = (poly[(ee + 1) % n] - poly[ee]).magnitude;
            float tA = pf.TOf(ee, 0f), tB = pf.TOf(ee, L);
            var cut = new List<float> { 0f, L };
            foreach (var t in pf.nt) if (t > tA + 1e-3f && t < tB - 1e-3f) cut.Add(t - pf.tStart[ee] + pf.sC[ee]);
            cut.Sort();
            for (int k = 0; k + 1 < cut.Count; k++)
            {
                float s0 = cut[k], s1 = cut[k + 1]; if (s1 - s0 < 1e-3f) continue;
                float t0 = pf.TOf(ee, s0), t1 = pf.TOf(ee, s1);
                float y0 = pf.Y(t0, +1), y1 = pf.Y(t1, -1);
                rows.Add(new HeiSec { edge = ee, sec = pf.StepsBefore(t0, true), s0 = s0, s1 = s1, seat = y0, grade = (y1 - y0) / (s1 - s0), t0 = t0, t1 = t1, stepAt0 = pf.IsStepAt(t0) });
            }
        }
        return rows;
    }

    static readonly HashSet<string> _neribeiFootParts = new HashSet<string> { "ishigaki", "koguchi", "koshi" };
    /// <summary>駒の足(腰の石垣の底)の高さを走り <paramref name="dir"/> の両端で測る(端から 0.03 内の頂点の最低)── 坂なりの駒は底が勾配で傾くので、両端の中ほどで線へ合わせる。</summary>
    static bool FootEnds(GameObject go, Vector2 dir, out float uLo, out float yLo, out float uHi, out float yHi)
    {
        uLo = float.MaxValue; uHi = float.MinValue; yLo = yHi = float.NaN;
        var pts = new List<Vector3>();
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (!_neribeiFootParts.Contains(mf.gameObject.name)) continue; var mesh = mf.sharedMesh; if (mesh == null) continue;
            foreach (var v in mesh.vertices) { var w = mf.transform.TransformPoint(v); float u = w.x * dir.x + w.z * dir.y; pts.Add(new Vector3(u, w.y, 0f)); uLo = Mathf.Min(uLo, u); uHi = Mathf.Max(uHi, u); }
        }
        if (pts.Count == 0) return false;
        float a = float.MaxValue, b = float.MaxValue;
        foreach (var p in pts) { if (p.x <= uLo + 0.03f) a = Mathf.Min(a, p.y); if (p.x >= uHi - 0.03f) b = Mathf.Min(b, p.y); }
        yLo = a; yHi = b; return a < float.MaxValue && b < float.MaxValue;
    }

    static float _tomePost = float.NaN, _tomeBody = float.NaN;
    /// <summary>棟止めだけの駒(<see cref="EdoAssets.Own.NeribeiTome"/>)の切り口から端の柱の外面 / 壁体(腰の小口)の外までの実寸(実メッシュ・一度だけ測る)。</summary>
    static void TomeGauge(out float post, out float body)
    {
        if (float.IsNaN(_tomePost))
        {
            var pr = Place(EdoAssets.Own.NeribeiTome(true), new Vector3(0f, -9999f, 0f), 0f, Vector3.one, null, "__tome_probe");
            float mn, mx; ProjExtent(pr, new Vector2(1f, 0f), float.MinValue, float.MaxValue, nm => nm == "hashira", out mn, out mx); _tomePost = mx;
            ProjExtent(pr, new Vector2(1f, 0f), float.MinValue, float.MaxValue, nm => !NeribeiRoofParts.Contains(nm), out mn, out mx); _tomeBody = mx;
            UnityEngine.Object.DestroyImmediate(pr);
        }
        post = _tomePost; body = _tomeBody;
    }

    /// <summary>棟止めの駒の実寸(<see cref="TomeGauge"/>)── 隅の腕を段の面まで詰める呼び手が読む。</summary>
    public static void NeribeiTomeGauge(out float post, out float body) { TomeGauge(out post, out body); }

    /// <summary>天端の線の区間の端の納め(<see cref="NeribeiLineRun"/>)。None = 突き付け(隅の腕・隣の区間・門の柱・長屋)/ Free = 自由端(端の外 = 腰の小口)/ Step = 段の面(端の外 = 端の柱の外面)。</summary>
    public enum HeiEnd { None, Free, Step }

    /// <summary>**練塀を天端の線の一区間で据える**(施主裁定 2026-10-12 案1・const.heiLine.tenba / parts)── 走り A→B を、勾配 0 は今の駒(<see cref="EdoAssets.Own.Neribei"/>・切り)、
    /// 勾配のある区間は坂なりの駒(<see cref="EdoAssets.Own.NeribeiSaka"/>・勾配 g を駒の局所 +X の向きへ直した綴り)で割り切る(割りは <see cref="NeribeiPanelRun"/> と同じ:
    /// n 枚 + 瓦の切り 1 枚・全部の駒の走りに倍率)。端は <paramref name="endA"/>/<paramref name="endB"/>: 段・自由端は棟止めだけの駒(<see cref="EdoAssets.Own.NeribeiTome"/>)を
    /// 駒の端へ突き付ける(段 = 端の柱の外面が A/B ・自由端 = 腰の小口が A/B)。
    /// 高さ: 駒ごとに**実メッシュの足(腰の底)を走りの両端で測り**、その中ほどを線 yA + g·(走り) へ(⛔ ピボットで据えない ── 倍率で駒の勾配は g/f になり、両端の食い違いは g·|f−1|·幅/2)。
    /// 棟止めは隣の駒の端の足へ。外面(<paramref name="faceIn"/>)は据える時に壁面で線へ。硬い(隙0 ── 割り切る)。⟶ 据えた駒・note(走りの残差・端の足の食い違いの最大)。
    /// 当たる先: 天端の線の上の練塀(岡部の外周 const.heiLine の全辺)── 他邸は未適用。</summary>
    public static List<GameObject> NeribeiLineRun(Transform parent, Vector2 A, Vector2 B, Vector2 outward, string prefix, float yA, float grade,
        HeiEnd endA, HeiEnd endB, float latOff, float faceIn, out string note, out float footErr)
    {
        var made = new List<GameObject>(); note = null; footErr = 0f;
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        Vector2 dir = (B - A).normalized; float L = (B - A).magnitude; if (L < 0.005f) return made;
        float post, tbody; TomeGauge(out post, out tbody);
        float wA = endA == HeiEnd.Step ? post : (endA == HeiEnd.Free ? tbody : 0f), wB = endB == HeiEnd.Step ? post : (endB == HeiEnd.Free ? tbody : 0f);
        float a0 = Vector2.Dot(A, dir), pa = a0 + wA, pb = a0 + L - wB, Lp = pb - pa;
        float psi = Mathf.Atan2(outward.x, outward.y) * Mathf.Rad2Deg;
        Vector2 lx = new Vector2(Mathf.Cos(psi * Mathf.Deg2Rad), -Mathf.Sin(psi * Mathf.Deg2Rad));   // 据えた向きの局所 +X
        float sgn = Vector2.Dot(lx, dir) > 0f ? 1f : -1f;
        bool flat = Mathf.Abs(grade) < 0.5e-4f;
        float gLoc = Mathf.Round(sgn * grade * 10000f) / 10000f;
        Func<string, bool> body = nm => !NeribeiRoofParts.Contains(nm);
        Func<float, float> yOn = u => yA + grade * (u - a0);
        GameObject first = null, last = null;
        if (Lp > 0.02f)
        {
            float P = EdoAssets.Own.NeribeiP, tile = EdoAssets.Own.NeribeiTile;
            int n = Mathf.FloorToInt(Lp / P + 1e-4f), k = Mathf.RoundToInt((Lp - n * P) / tile);
            if (k >= 14) { n++; k = 0; }
            if (n == 0 && k == 0) k = 1;
            var seq = new List<string>();
            for (int i = 0; i < n; i++) seq.Add(flat ? EdoAssets.Own.Neribei : EdoAssets.Own.NeribeiSaka(gLoc));
            if (k > 0) seq.Add(flat ? EdoAssets.Own.NeribeiKiri(k) : EdoAssets.Own.NeribeiSaka(gLoc, k));
            var missing = seq.FindAll(pth => AssetDatabase.LoadAssetAtPath<GameObject>(pth) == null);
            if (missing.Count > 0) { note = "駒が無い " + string.Join(" / ", missing.ConvertAll(x => System.IO.Path.GetFileNameWithoutExtension(x)).ToArray()); footErr = 0f; return made; }
            float sumW = 0f; foreach (var pth in seq) sumW += NeribeiBodyW(pth, body);
            float f = sumW > 1e-3f ? Lp / sumW : 1f;
            float cur = pa;
            for (int i = 0; i < seq.Count; i++)
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(seq[i]) == null ? null : Place(seq[i], Vector3.zero, psi, new Vector3(f, 1f, 1f), parent, prefix + "_" + i);
                if (go == null) { note = (note == null ? "" : note + " / ") + "駒が無い " + System.IO.Path.GetFileName(seq[i]); continue; }
                float mn, mx; ButtOnRun(go, A, dir, outward, latOff, cur, out mn, out mx, body);
                if (!float.IsNaN(faceIn))
                {
                    float wmn, wmx; ProjExtent(go, outward, float.MinValue, float.MaxValue, nm => NeribeiWallParts.Contains(nm), out wmn, out wmx);
                    if (wmx > wmn) { float sh = (Vector2.Dot(A, outward) - faceIn) - wmx; go.transform.position += new Vector3(outward.x * sh, 0f, outward.y * sh); }
                }
                cur = mx;
                float uL, yL, uH, yH;
                if (FootEnds(go, dir, out uL, out yL, out uH, out yH))
                {
                    float sh = 0.5f * (yOn(uL) + yOn(uH)) - 0.5f * (yL + yH); go.transform.position += Vector3.up * sh;
                    footErr = Mathf.Max(footErr, Mathf.Abs((yL + sh) - yOn(uL)), Mathf.Abs((yH + sh) - yOn(uH)));
                }
                else SeatBottom(go, yOn(0.5f * (mn + mx)));
                if (first == null) first = go; last = go; made.Add(go);
            }
            float resid = cur - pb; if (Mathf.Abs(resid) > 0.01f) note = (note == null ? "" : note + " / ") + "走りの端の残差 " + resid.ToString("+0.000;-0.000", inv) + "m";
        }
        else if (Lp < -0.02f) note = "走り " + L.ToString("F3", inv) + " に両端の棟止め " + (wA + wB).ToString("F3", inv) + " が入らない ⚠";
        // 棟止め(切り口 = 駒の端・棟止めは区間の外の向き)
        foreach (int side in new[] { 0, 1 })
        {
            HeiEnd et = side == 0 ? endA : endB; if (et == HeiEnd.None) continue;
            //   駒が無い(棟止めだけの区間 ── 隅の腕の先から段の面まで)なら、切り口は相手の端(片方だけ棟止め)か各々の幅(両方)
            float cut = side == 0 ? (Lp > 0.02f ? pa : (endB == HeiEnd.None ? a0 + L : a0 + wA)) : (Lp > 0.02f ? pb : (endA == HeiEnd.None ? a0 : a0 + L - wB));
            Vector2 outRun = side == 0 ? -dir : dir;
            var tg = Place(EdoAssets.Own.NeribeiTome(Vector2.Dot(lx, outRun) > 0f), Vector3.zero, psi, Vector3.one, parent, prefix + (side == 0 ? "_TomeA" : "_TomeB"));
            if (tg == null) { note = (note == null ? "" : note + " / ") + "棟止めの駒が無い"; continue; }
            float mn, mx; ButtOnRun(tg, A, dir, outward, latOff, 0f, out mn, out mx, body);
            // 走り: 切り口(壁体の区間の内の側の端)を cut へ
            float inner = side == 0 ? mx : mn; float dRun = cut - inner; tg.transform.position += new Vector3(dir.x * dRun, 0f, dir.y * dRun);
            // 奥行: 隣の駒の腰(ishigaki)の外面と内面の中ほどに合わせる(無ければ端の柱の外面を線から faceIn へ)
            var nb = side == 0 ? first : last; float tmn, tmx; ProjExtent(tg, outward, float.MinValue, float.MaxValue, nm => nm == "ishigaki", out tmn, out tmx);
            if (nb != null) { float nmn, nmx; ProjExtent(nb, outward, float.MinValue, float.MaxValue, nm => nm == "ishigaki", out nmn, out nmx); float sh = 0.5f * (nmn + nmx) - 0.5f * (tmn + tmx); tg.transform.position += new Vector3(outward.x * sh, 0f, outward.y * sh); }
            else if (!float.IsNaN(faceIn)) { float hmn, hmx; ProjExtent(tg, outward, float.MinValue, float.MaxValue, nm => nm == "hashira", out hmn, out hmx); float sh = (Vector2.Dot(A, outward) - faceIn) - hmx; tg.transform.position += new Vector3(outward.x * sh, 0f, outward.y * sh); }
            // 高さ: 足(腰の底)の最低を切り口の線の座へ
            float yb = float.MaxValue; foreach (var mf in tg.GetComponentsInChildren<MeshFilter>()) { if (mf.gameObject.name != "ishigaki" || mf.sharedMesh == null) continue; foreach (var v in mf.sharedMesh.vertices) yb = Mathf.Min(yb, mf.transform.TransformPoint(v).y); }
            if (yb < float.MaxValue) tg.transform.position += Vector3.up * (yOn(cut) - yb);
            made.Add(tg);
        }
        return made;
    }
}
