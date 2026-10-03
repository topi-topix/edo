// EdoBuild — 坂の路盤(折れ線の芯と縦断で道の面を均し、盛土・切土の法で地盤へ擦り付ける)。
// 2026-10-03・EDO-0502(岡部 案1 の塀の内の坂 R_UraZaka・崖の坂 R_GakeZaka)。
// 当たる先: 指図の ramps[] のうち `pts` と `profY` を持つ坂(岡部の R_UraZaka / R_GakeZaka)。
//   `sashizu_lib.ramp_y` が「pts 式の坂は地盤は別勘定」として造成(impl.graded)に入れていないので、
//   造成(Stage1)の後にここで路盤を均す。
// ⛔ 置き方を邸ビルダーに書かない(規則21)── 邸ビルダーは指図を読んで渡すだけ。
using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>坂の路盤を均した結果。</summary>
    public class SakaResult
    {
        public Vector2[] pts;        // 実際に均した芯(世界 XZ)
        public float shift;          // 法尻の硬い条件のために芯の途中を内へ寄せた量[m]
        public float toeMin;         // 盛土の法尻(盛った節点)と区画の線の最短[m]。盛りが無ければ +∞
        public float fillMax, cutMax;
        public float fillM3, cutM3;
        public int nodes;
        /// <summary>路肩の石の縁(toeFix)を置いた走りの範囲[m](道のり)と、区画の線の側の路肩の線(世界 xz)。縁が無ければ curbS0 = NaN。</summary>
        public float curbS0 = float.NaN, curbS1 = float.NaN, curbHMax, curbToe = float.PositiveInfinity;
        /// <summary>法尻を**法の面と今の地盤の交わり**で測った区画の線からの最短[m](芯の 0.5m ごとに路肩から法の面を外へ 0.1m 刻みで歩く)。
        /// toeMin(節点)は格子の節点の距離 ── 2m 格子では法尻の位置を一升の精度でしか言えない。toeNodeMin に残す。</summary>
        public float toeLine = float.PositiveInfinity, toeNodeMin = float.PositiveInfinity;
        public List<Vector2> curbLine = new List<Vector2>();
        public bool ok;
        public string note;
    }

    /// <summary>
    /// **坂の路盤を均す**(硬い: 盛土の法尻 ≥ <paramref name="toeMin"/> を区画の線から ── 満たせなければ地形に触らない)。
    /// 芯 <paramref name="pts"/>(世界 XZ)と各点の高さ <paramref name="ys"/> を道のりで一次に結び、幅 <paramref name="width"/> の
    /// 中は芯の高さで横断水平、外は盛土 1:<paramref name="bf"/>・切土 1:<paramref name="bc"/> の法で今の地形へ擦り付ける
    /// (節点の新しい高さ = clamp(今, 芯 − h/bf, 芯 + h/bc)、h = 路肩からの水平距離)。坂の両端より先は触らない。
    /// 法尻が近すぎるときは、端の点(門の内面・平場の角 = <paramref name="pinned"/>)を動かさず、途中の点を
    /// 最寄りの区画の辺の内向きへ 0.25m 刻みで寄せて最も小さい寄せを採る(柔らかい: 指図の芯 = 狙い・寄せは ⚠ で報告)。
    /// ⛔ 区画の外の節点は触らない。冪等ではない(今の地形から盛り切りする)── 造成(Stage1)の直後に一度だけ呼ぶ。
    /// </summary>
    public static SakaResult GradeSaka(Vector2[] parcel, Vector2[] pts, float[] ys, bool[] pinned,
                                       float width, float bf, float bc, float toeMin, float maxShift, bool write)
    { return GradeSaka(parcel, pts, ys, pinned, width, bf, bc, toeMin, maxShift, write, 0f, 0f); }

    /// <summary>
    /// <see cref="GradeSaka(Vector2[],Vector2[],float[],bool[],float,float,float,float,float,bool)"/> に**路肩の石の縁**を足した版
    /// (指図 ramps[].toeFix・2026-10-03 EDO-0502 普請方の設計「芯は描いた線のまま・区画線側の路肩に野面石の縁 h≤<paramref name="curbH"/>・法尻=石の根=路肩」)。
    /// <para>手順: ① 芯を動かさず縁なしで均したときの法尻が近すぎる節点(区画の線の側)を測り、その道のりの最小〜坂の終わりを縁の区間とする
    /// (縁の区間は指図の数でなく**実地形の測り**で決まる)② 縁の区間の区画線側の路肩は、地盤が路面から <paramref name="curbH"/> 以内なら盛らない
    /// (石が受ける)・それより低ければ路面 − curbH から法で擦り付ける ③ それでも法尻が近ければ芯の途中を内へ寄せる(maxShift まで・柔らかい)。</para>
    /// <para>硬い: 法尻 ≥ toeMin(満たせなければ地形に触らない)。柔らかい: 芯 = 狙い(寄せたら ⚠)。curbH = 0 なら縁を置かない(旧と同じ)。</para>
    /// </summary>
    public static SakaResult GradeSaka(Vector2[] parcel, Vector2[] pts, float[] ys, bool[] pinned,
                                       float width, float bf, float bc, float toeMin, float maxShift, bool write, float curbH, float curbToeMin)
    {
        var res = new SakaResult { ok = false, toeMin = float.PositiveInfinity };
        float curbS0 = float.NaN;
        if (curbH > 0f)
        {
            var r0 = GradeSakaOnce(parcel, pts, ys, width, bf, bc, false, float.NaN, curbH, toeMin);   // 測るだけ(縁の区間の始まり)
            if (r0.toeMin < toeMin && !float.IsNaN(r0.curbS0)) curbS0 = r0.curbS0;
        }
        // 寄せる向き: 各点の最寄りの区画の辺の内向き
        var inward = new Vector2[pts.Length];
        for (int i = 0; i < pts.Length; i++)
        {
            int e = NearestEdge(parcel, pts[i]);
            inward[i] = EdoGeom.InwardNormal(parcel, e);
        }
        for (float d = 0f; d <= maxShift + 1e-4f; d += 0.25f)
        {
            var p2 = new Vector2[pts.Length];
            for (int i = 0; i < pts.Length; i++) p2[i] = (pinned != null && pinned[i]) ? pts[i] : pts[i] + inward[i] * d;
            var r = GradeSakaOnce(parcel, p2, ys, width, bf, bc, false, curbS0, curbH, toeMin);
            if (r.toeMin >= toeMin && (float.IsNaN(curbS0) || r.curbToe >= curbToeMin))
            {
                r.shift = d; r.pts = p2;
                if (write) { var w2 = GradeSakaOnce(parcel, p2, ys, width, bf, bc, true, curbS0, curbH, toeMin); w2.shift = d; w2.pts = p2; w2.ok = true; return w2; }
                r.ok = true; return r;
            }
            res = r; res.shift = d; res.pts = p2;
        }
        res.ok = false;
        res.note = "芯の途中を " + maxShift.ToString("F2") + "m まで寄せても法尻が区画の線から "
                 + res.toeMin.ToString("F2") + "m(< " + toeMin.ToString("F2") + ")"
                 + (float.IsNaN(curbS0) ? "" : "・縁の石の根 " + res.curbToe.ToString("F2") + "m(< " + curbToeMin.ToString("F2") + ")") + "── 地形に触らない(硬い)。塀側の土留め(1m 未満)か芯の引き直しが要る";
        return res;
    }

    static int NearestEdge(Vector2[] P, Vector2 p)
    {
        int best = 0; float bd = float.MaxValue;
        for (int e = 0; e < P.Length; e++)
        {
            float dd = DistSeg2(p, P[e], P[(e + 1) % P.Length]);
            if (dd < bd) { bd = dd; best = e; }
        }
        return best;
    }

    static float DistSeg2(Vector2 p, Vector2 a, Vector2 b)
    {
        Vector2 ab = b - a; float L2 = ab.sqrMagnitude;
        float t = L2 > 1e-9f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / L2) : 0f;
        return (a + ab * t - p).magnitude;
    }

    static float DistPolyLine(Vector2[] P, Vector2 p)
    {
        float bd = float.MaxValue;
        for (int e = 0; e < P.Length; e++) bd = Mathf.Min(bd, DistSeg2(p, P[e], P[(e + 1) % P.Length]));
        return bd;
    }

    static SakaResult GradeSakaOnce(Vector2[] parcel, Vector2[] pts, float[] ys, float width, float bf, float bc, bool write)
    { return GradeSakaOnce(parcel, pts, ys, width, bf, bc, write, float.NaN, 0f, 0f); }

    /// <summary>curbS0 が数なら、道のり ≥ curbS0 の区画線側の路肩に高さ curbH の石の縁を置いた形で均す。
    /// curbS0 が NaN で curbH &gt; 0 なら、縁なしで均して**法尻が toeMin を割る区画線側の節点の道のりの最小**を res.curbS0 に返す(測るだけ)。</summary>
    static SakaResult GradeSakaOnce(Vector2[] parcel, Vector2[] pts, float[] ys, float width, float bf, float bc, bool write,
                                    float curbS0, float curbH, float toeMin)
    {
        var res = new SakaResult { toeMin = float.PositiveInfinity };
        bool probeCurb = float.IsNaN(curbS0) && curbH > 0f;
        bool useCurb = !float.IsNaN(curbS0) && curbH > 0f;
        float probeMin = float.PositiveInfinity;
        var t = T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        // 道のり
        var st = new float[pts.Length];
        for (int i = 1; i < pts.Length; i++) st[i] = st[i - 1] + (pts[i] - pts[i - 1]).magnitude;
        float yMin = float.MaxValue, yMax = float.MinValue;
        foreach (var y in ys) { yMin = Mathf.Min(yMin, y); yMax = Mathf.Max(yMax, y); }
        float reach = width * 0.5f + 4f * Mathf.Max(bf, bc) + 2f * cell;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in pts) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - reach - tp.x) / cell), 0, hres - 1);
        int z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - reach - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx + reach - tp.x) / cell), 0, hres - 1);
        int z1 = Mathf.Clamp(Mathf.CeilToInt((mxz + reach - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        float half = width * 0.5f, area = cell * cell;
        for (int iz = 0; iz < h; iz++)
            for (int ix = 0; ix < w; ix++)
            {
                var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
                if (!EdoGeom.PIP(parcel, p)) continue;                    // ⛔ 区画の外は触らない
                // 芯の最寄りの点
                float bd = float.MaxValue, bs = 0f; bool beyond = false;
                for (int k = 0; k + 1 < pts.Length; k++)
                {
                    Vector2 a = pts[k], b = pts[k + 1], ab = b - a; float L2 = ab.sqrMagnitude; if (L2 < 1e-9f) continue;
                    float tr = Vector2.Dot(p - a, ab) / L2;
                    float tc = Mathf.Clamp01(tr);
                    float dd = (a + ab * tc - p).magnitude;
                    if (dd < bd)
                    {
                        bd = dd; bs = st[k] + Mathf.Sqrt(L2) * tc;
                        beyond = (k == 0 && tr < 0f) || (k == pts.Length - 2 && tr > 1f);
                    }
                }
                if (beyond) continue;                                     // 坂の両端より先は触らない
                // 芯の高さ(道のりで一次)
                float yr = ys[ys.Length - 1];
                for (int k = 0; k + 1 < pts.Length; k++)
                    if (bs <= st[k + 1] + 1e-5f) { float u = (bs - st[k]) / Mathf.Max(1e-5f, st[k + 1] - st[k]); yr = Mathf.Lerp(ys[k], ys[k + 1], u); break; }
                float hh = Mathf.Max(0f, bd - half);
                float lo = yr - hh / bf, hi = yr + hh / bc;
                float cur = H[iz, ix] * ts.y + tp.y;
                // 区画の線の側の路肩か(芯の最寄りの点より区画の線に近い節点)
                bool lineSide = false;
                if (useCurb || probeCurb)
                {
                    Vector2 cp = Vector2.zero; float cbd = float.MaxValue;
                    for (int k = 0; k + 1 < pts.Length; k++)
                    {
                        Vector2 a = pts[k], b = pts[k + 1], ab = b - a; float L2 = ab.sqrMagnitude; if (L2 < 1e-9f) continue;
                        float tc = Mathf.Clamp01(Vector2.Dot(p - a, ab) / L2); var q = a + ab * tc;
                        float dd = (q - p).magnitude; if (dd < cbd) { cbd = dd; cp = q; }
                    }
                    lineSide = DistPolyLine(parcel, p) < DistPolyLine(parcel, cp);
                }
                if (useCurb && lineSide && bs >= curbS0 && hh > 0f)
                {
                    lo = yr - curbH - hh / bf;                            // 石の縁が curbH まで受ける
                    if (cur >= yr - curbH) res.curbHMax = Mathf.Max(res.curbHMax, Mathf.Min(curbH, yr - cur));
                    else res.curbHMax = curbH;
                }
                float nw = Mathf.Min(Mathf.Max(cur, lo), hi);
                if (Mathf.Abs(nw - cur) < 1e-4f) continue;
                res.nodes++;
                if (nw > cur)
                {
                    res.fillMax = Mathf.Max(res.fillMax, nw - cur); res.fillM3 += (nw - cur) * area;
                    if (nw - cur > 0.02f)
                    {
                        float dl = DistPolyLine(parcel, p);
                        // 縁の区間の路面の節点は法尻でない(法尻 = 石の根 = 路肩 ── 線で測る: curbToe)
                        if (!(useCurb && lineSide && bs >= curbS0 && hh <= 0f)) res.toeMin = Mathf.Min(res.toeMin, dl);
                    }
                }
                else { res.cutMax = Mathf.Max(res.cutMax, cur - nw); res.cutM3 += (cur - nw) * area; }
                if (write) H[iz, ix] = (nw - tp.y) / ts.y;
            }
        // 法尻を線で測る(書き込みの前の地盤 = SampleHeight は SetHeights の前なので今の地盤)
        {
            float L = st[st.Length - 1];
            for (float s0 = 0f; s0 <= L + 1e-4f; s0 += 0.5f)
            {
                int k = 0; while (k + 2 < pts.Length && s0 > st[k + 1]) k++;
                Vector2 a = pts[k], b = pts[k + 1]; float u = (s0 - st[k]) / Mathf.Max(1e-5f, st[k + 1] - st[k]);
                Vector2 c = Vector2.Lerp(a, b, u), dir = (b - a).normalized, n = new Vector2(-dir.y, dir.x);
                float yr = Mathf.Lerp(ys[k], ys[k + 1], u);
                for (int sd = -1; sd <= 1; sd += 2)
                {
                    Vector2 nn = n * sd;
                    Vector2 sh = c + nn * half;
                    bool toLine = DistPolyLine(parcel, sh) < DistPolyLine(parcel, c);
                    float drop = (useCurb && toLine && s0 >= curbS0) ? curbH : 0f;
                    for (float hh = 0f; hh <= 12f; hh += 0.1f)
                    {
                        Vector2 q = sh + nn * hh;
                        if (!EdoGeom.PIP(parcel, q)) { res.toeLine = 0f; break; }
                        float g = t.SampleHeight(new Vector3(q.x, 0f, q.y)) + tp.y;
                        if (g >= yr - drop - hh / bf - 0.02f)
                        {
                            if (hh > 0f || g < yr - 0.02f)
                            {
                                float dq = DistPolyLine(parcel, q);
                                res.toeLine = Mathf.Min(res.toeLine, dq);
                                if (probeCurb && toLine && dq < toeMin) probeMin = Mathf.Min(probeMin, s0);
                            }
                            break;
                        }
                    }
                }
            }
        }
        res.toeNodeMin = res.toeMin;
        res.toeMin = res.toeLine;
        if (write) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        if (probeCurb && !float.IsInfinity(probeMin)) res.curbS0 = Mathf.Max(0f, probeMin - 2f * cell);   // 一升の余裕を二つ取って縁を始める
        if (useCurb)
        {
            res.curbS0 = curbS0; res.curbS1 = st[st.Length - 1];
            // 区画の線の側の路肩の線(縁の石を据える線)── 芯の各点から路肩へ。向きは区画の線に近い側
            for (float s0 = curbS0; s0 <= st[st.Length - 1] + 1e-4f; s0 += 0.5f)
            {
                int k = 0; while (k + 2 < pts.Length && s0 > st[k + 1]) k++;
                Vector2 a = pts[k], b = pts[k + 1]; float u = (s0 - st[k]) / Mathf.Max(1e-5f, st[k + 1] - st[k]);
                Vector2 c = Vector2.Lerp(a, b, u), dir = (b - a).normalized, n = new Vector2(-dir.y, dir.x);
                Vector2 s1 = c + n * half, s2 = c - n * half;
                var cl = DistPolyLine(parcel, s1) < DistPolyLine(parcel, s2) ? s1 : s2;
                res.curbLine.Add(cl);
                res.curbToe = Mathf.Min(res.curbToe, DistPolyLine(parcel, cl));
            }
        }
        return res;
    }
}
