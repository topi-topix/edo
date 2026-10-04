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
        /// <summary>描かれた法尻(節点の間の一次の描きで盛りが 0.02 に落ちる点)の区画の線からの最短[m]・締めて盛らなかった節点の数。</summary>
        public float toeRender = float.PositiveInfinity; public int unfilled;
        /// <summary>路面の節点(締めない)の盛りが描かれて下りる点の区画の線からの最短[m]。路肩が線に近い坂で toeMin を割る ── 芯を寄せる話(呼び手が刷る)。</summary>
        public float toeRoad = float.PositiveInfinity;
        /// <summary>芯を maxShift まで寄せても toeRoad が割ったので、区画の線の側の路肩の節点を盛らなかった(⚠ 呼び手が刷る)。</summary>
        public bool roadUnfilled;
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
        // ⭐ 路面の節点の盛りが描かれて区画の線へ下りる点(toeRoad)も硬い法尻に数える(2026-10-03 EDO-0502 第4巡・
        //   普請検査: R_UraZaka の描かれた法尻 1.15〜1.50m)。① 芯を寄せて toeRoad も満たす最小の寄せを探す
        //   ② maxShift まで寄せても割るなら、**区画の線の側の路肩の節点の列を盛らない**(縁の根より外は元の地盤 ── 縁の石が路面を受ける)。
        for (int pass = 0; pass < 2; pass++)
        {
            bool unfillRoad = pass == 1;
            // ② は寄せ切った芯で(寄せで足りる所は寄せ・足りない所だけ盛らない)
            for (float d = unfillRoad ? maxShift : 0f; d <= maxShift + 1e-4f; d += 0.25f)
            {
                var p2 = new Vector2[pts.Length];
                for (int i = 0; i < pts.Length; i++) p2[i] = (pinned != null && pinned[i]) ? pts[i] : pts[i] + inward[i] * d;
                var r = GradeSakaOnce(parcel, p2, ys, width, bf, bc, false, curbS0, curbH, toeMin, unfillRoad);
                if (r.toeMin >= toeMin && r.toeRoad >= toeMin && (float.IsNaN(curbS0) || r.curbToe >= curbToeMin))
                {
                    r.shift = d; r.pts = p2;
                    if (write) { var w2 = GradeSakaOnce(parcel, p2, ys, width, bf, bc, true, curbS0, curbH, toeMin, unfillRoad); w2.shift = d; w2.pts = p2; w2.ok = true; w2.roadUnfilled = unfillRoad; return w2; }
                    r.ok = true; r.roadUnfilled = unfillRoad; return r;
                }
                res = r; res.shift = d; res.pts = p2;
            }
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
    { return GradeSakaOnce(parcel, pts, ys, width, bf, bc, write, curbS0, curbH, toeMin, false); }

    /// <summary><paramref name="unfillRoad"/> なら、描かれた盛りが区画の線から toeMin を割る**区画の線の側の**路面の節点も盛らない。</summary>
    static SakaResult GradeSakaOnce(Vector2[] parcel, Vector2[] pts, float[] ys, float width, float bf, float bc, bool write,
                                    float curbS0, float curbH, float toeMin, bool unfillRoad)
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
        // 描かれる地表の法尻を守るため、節点ごとの新しい高さを一度ためてから書く(下の「描かれた法尻」の締め)
        var NW = new float[h, w]; var CUR = new float[h, w]; var ROAD = new bool[h, w]; var LSIDE = new bool[h, w];
        for (int iz = 0; iz < h; iz++) for (int ix = 0; ix < w; ix++) NW[iz, ix] = float.NaN;
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
                if (useCurb || probeCurb || unfillRoad)
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
                NW[iz, ix] = nw; CUR[iz, ix] = cur; ROAD[iz, ix] = hh <= 0f; LSIDE[iz, ix] = lineSide;
            }
        // ⭐ **描かれた法尻**(2026-10-03・EDO-0502 普請検査: 法尻 1.39〜1.49m < 硬い 1.5m)。地表は節点の間を一次で描くので、
        //   盛った節点の盛りは隣の(盛らない)節点まで一升ぶん滑らかに下りる ── 法の線で測った法尻(toeLine)より区画の線へ近く描かれる。
        //   盛り > 0.02 の各節点から 8 方の隣へ、描かれた盛りが 0.02 に落ちる点を測り、区画の線から toeMin を割る節点は**盛らない**
        //   (路面の節点は締めない ── 道が凹む。路面で割るなら芯を寄せる側の話として toeMin に返す)。硬い。
        float toeRender = float.PositiveInfinity, toeRoad = float.PositiveInfinity; int unfilled = 0;
        for (int pass = 0; pass < 8; pass++)
        {
            bool changed = false; toeRender = float.PositiveInfinity; toeRoad = float.PositiveInfinity;
            for (int iz = 0; iz < h; iz++)
                for (int ix = 0; ix < w; ix++)
                {
                    if (float.IsNaN(NW[iz, ix])) continue;
                    float f = NW[iz, ix] - CUR[iz, ix]; if (f <= 0.02f) continue;
                    var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
                    float worst = float.PositiveInfinity;
                    for (int dz = -1; dz <= 1; dz++)
                        for (int dx = -1; dx <= 1; dx++)
                        {
                            if (dx == 0 && dz == 0) continue;
                            int jz = iz + dz, jx = ix + dx;
                            float fn = (jz >= 0 && jz < h && jx >= 0 && jx < w && !float.IsNaN(NW[jz, jx])) ? NW[jz, jx] - CUR[jz, jx] : 0f;
                            if (fn > 0.02f) continue;
                            float tt = (f - 0.02f) / Mathf.Max(1e-5f, f - fn);
                            var q = p + new Vector2(dx, dz) * cell * Mathf.Clamp01(tt);
                            worst = Mathf.Min(worst, EdoGeom.PIP(parcel, q) ? DistPolyLine(parcel, q) : 0f);
                        }
                    if (worst < toeMin && (!ROAD[iz, ix] || (unfillRoad && LSIDE[iz, ix]))) { NW[iz, ix] = CUR[iz, ix]; changed = true; unfilled++; continue; }
                    if (ROAD[iz, ix]) toeRoad = Mathf.Min(toeRoad, worst); else toeRender = Mathf.Min(toeRender, worst);
                }
            if (!changed) break;
        }
        res.toeRender = toeRender; res.toeRoad = toeRoad; res.unfilled = unfilled;
        if (write)
            for (int iz = 0; iz < h; iz++) for (int ix = 0; ix < w; ix++)
                if (!float.IsNaN(NW[iz, ix])) H[iz, ix] = (NW[iz, ix] - tp.y) / ts.y;
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
        res.toeMin = Mathf.Min(res.toeLine, res.toeRender);
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

    /// <summary>**棟の下の均し**(2026-10-03 EDO-0502 第4巡・岡部の厩と蔵1 が勾配の面の上手へ 0.78m 埋まった)。
    /// 指図の `yAt`(棟の芯での面の高さ)で足あと <paramref name="foot"/>(呼び手が据えた駒の躯体から測る・世界 xz)の下を平らにし、
    /// その外は盛土 1:<paramref name="bf"/>・切土 1:<paramref name="bc"/> の法で今の地盤へ擦り付ける。
    /// ⭐ 2m 格子は節点の間を一次で描く ⇒ 足あとの縁に掛かる升の節点まで平らにしないと縁の下が勾配のまま描かれる ──
    /// 平らに取るのは足あと + 一升(<c>cell</c>)。硬い: 区画の外の節点は触らない。冪等(今の地盤を法で挟むだけ)。
    /// 当たる先: 勾配の面(指図 `yFrom`)の上に建つ附属屋(岡部の厩・蔵・米蔵・薪蔵・家臣長屋)── 呼び手が埋まり・浮きを測って渡す。
    /// ⟶ 返す: 書いた節点の数(切 / 盛の最大は out)</summary>
    public static int LevelPad(Vector2[] parcel, Vector2[] foot, float y, float bf, float bc, out float cutMax, out float fillMax)
    {
        cutMax = 0f; fillMax = 0f;
        if (foot == null || foot.Length < 3) return 0;
        var t = T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        float reach = cell + 6f * Mathf.Max(bf, bc) + cell;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in foot) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - reach - tp.x) / cell), 0, hres - 1);
        int z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - reach - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx + reach - tp.x) / cell), 0, hres - 1);
        int z1 = Mathf.Clamp(Mathf.CeilToInt((mxz + reach - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        int n = 0;
        for (int iz = 0; iz < h; iz++)
            for (int ix = 0; ix < w; ix++)
            {
                var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
                if (!EdoGeom.PIP(parcel, p)) continue;                  // ⛔ 区画の外は触らない
                float d = EdoGeom.PIP(foot, p) ? 0f : DistPolyLine(foot, p);
                float cur = H[iz, ix] * ts.y + tp.y, nw;
                if (d <= cell) nw = y;
                else { float hh = d - cell; nw = Mathf.Min(Mathf.Max(cur, y - hh / bf), y + hh / bc); }
                if (Mathf.Abs(nw - cur) < 1e-4f) continue;
                if (nw > cur) fillMax = Mathf.Max(fillMax, nw - cur); else cutMax = Mathf.Max(cutMax, cur - nw);
                H[iz, ix] = (nw - tp.y) / ts.y; n++;
            }
        if (n > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        return n;
    }
    /// <summary>**棟の背の下端の浮きを、背に沿う内の帯を盛って塞ぐ**(埋めて隠す・docs/oki-kata.md §4・2026-10-04 EDO-0533 土井の表長屋 E13_N11 の背が +0.062 浮いた)。
    /// 線 <paramref name="a"/>–<paramref name="b"/> = 棟の背の面の足元(世界 xz)、<paramref name="inward"/> = 区画の内へ向く水平の単位。
    /// 背の面から内へ <paramref name="band"/>[m] までと、背の面の外(棟の下)の一升の節点を <paramref name="y"/>(背の下端 + 根入れ)まで盛り、
    /// 帯の外は盛土 1:<paramref name="bf"/> で今の地盤へ摺り付ける。⭐ 2m 格子は節点の間を一次で描く ⇒ 背の線の両側の節点を上げないと線の上が描かれない
    /// ── 棟の下の節点は躯体が隠す。硬い: 盛るだけ(切らない)・区画の外の節点は触らない。冪等。体積は節点の升の面積 × 盛りの和。
    /// 当たる先: 基壇の天端に土台を据えた棟の背が、基壇より低い内の地表に面する所(土井の表長屋・門長屋・表門、外周に長屋を回す各邸の表長屋)。
    /// ⟶ 返す: 書いた節点の数(盛りの最大と体積は out)</summary>
    public static int FillAlongBack(Vector2[] parcel, Vector2 a, Vector2 b, Vector2 inward, float y, float band, float bf, out float fillMax, out float vol)
    {
        fillMax = 0f; vol = 0f;
        var t = T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        float reach = band + cell + 6f * bf + cell;
        float mnx = Mathf.Min(a.x, b.x) - reach, mxx = Mathf.Max(a.x, b.x) + reach, mnz = Mathf.Min(a.y, b.y) - reach, mxz = Mathf.Max(a.y, b.y) + reach;
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / cell), 0, hres - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / cell), 0, hres - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        Vector2 ab = b - a; float L = ab.magnitude; if (L < 1e-3f) return 0; Vector2 al = ab / L;
        int n = 0;
        for (int iz = 0; iz < h; iz++)
            for (int ix = 0; ix < w; ix++)
            {
                var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
                if (!EdoGeom.PIP(parcel, p)) continue;                       // ⛔ 区画の外は触らない
                float s = Vector2.Dot(p - a, al), dn = Vector2.Dot(p - a, inward);
                float ds = s < 0f ? -s : (s > L ? s - L : 0f);              // 線の端の外へ出た量
                if (dn < -cell || ds > cell + 6f * bf) continue;            // 棟の下は一升まで
                float over = Mathf.Max(0f, dn - band) + Mathf.Max(0f, ds - cell);   // 帯の外へ出た量 ⇒ 1:bf で下ろす
                float tgt = y - over / bf;
                float cur = H[iz, ix] * ts.y + tp.y;
                if (tgt <= cur + 1e-4f) continue;                           // 盛るだけ
                fillMax = Mathf.Max(fillMax, tgt - cur); vol += (tgt - cur) * cell * cell;
                H[iz, ix] = (tgt - tp.y) / ts.y; n++;
            }
        if (n > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        return n;
    }
}
