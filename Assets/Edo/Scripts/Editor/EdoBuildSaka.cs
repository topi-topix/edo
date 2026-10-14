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
                // 芯の最寄りの点と芯の高さ(道のりで一次)── 造成QA と同じ関数(SakaCenterAt)
                float bd, bs, yr;
                if (!SakaCenterAt(pts, ys, p, out bd, out bs, out yr)) continue;   // 坂の両端より先は触らない
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

    /// <summary>**法で寄せる一節点の式**: 面の高さ <paramref name="y"/> の縁から水平に <paramref name="hh"/>[m] 離れた節点の地盤 <paramref name="cur"/> を、
    /// 盛土 1:<paramref name="bf"/>・切土 1:<paramref name="bc"/> の法の間へ挟んだ高さ(LevelPad・GradeSakaOnce・各邸の造成QA が同じ式を使う ── ⛔ 式を二重に持たない)。</summary>
    public static float BatterTo(float y, float hh, float bf, float bc, float cur)
    { return Mathf.Min(Mathf.Max(cur, y - hh / bf), y + hh / bc); }

    /// <summary>**棟の下の均し(LevelPad)が節点 <paramref name="p"/> に与える高さ**。触らない節点(区画の外・窓の外)は <paramref name="cur"/> を返す。
    /// LevelPad はこの関数で書き、造成QA はこの関数で「設計面からの差が均しの跡か」を測る(2026-10-04 EDO-0502 第13巡)。測るだけ。</summary>
    public static float LevelPadAt(Vector2[] parcel, Vector2[] foot, float y, float bf, float bc, float cell, Vector2 p, float cur)
    { return LevelPadAt(parcel, foot, y, bf, bc, cell, p, cur, null); }

    /// <summary>棟の下の均しが**棟の建つ面の外**で触ってよい節点(<see cref="LevelPadAt(Vector2[], Vector2[], float, float, float, float, Vector2, float, PadRim)"/>)。
    /// <c>outer</c> = 触ってよい外の範囲(区画)・<c>keepOut</c> = 触らない面(ほかの段の平らな面 ── 段の土留めを越えて下の面を盛らない・第7巡)。
    /// <c>holes</c> = 面の**中でも**触らない範囲(2026-10-14 EDO-0502 第133巡: 面の中に掘り残した坂の路盤 ── 岡部 R_KiriZaka は東の平場の盛りの中の溝で、
    /// 蔵1 の均しの盛りの法 1:1.5 が両脇の石垣を越えて路盤の東の縁を 0.3〜0.6 盛り、横断の左右の差が 0.275 になった)。
    /// 当たる先: 面の中に坂(ramps の路盤)を持つ邸の棟の下の均しと、同じ式で均しの跡を数える造成QA。</summary>
    public class PadRim { public Vector2[] outer; public IList<Vector2[]> keepOut; public IList<Vector2[]> holes; }

    /// <summary>LevelPadAt に、面の外の**縁の節点**の扱いを足したもの(2026-10-07 EDO-0502 第46巡)。⭐ 棟の隅が面の縁から一升の内に在ると、
    /// 隅の升を描く節点が面の外(面と面の間の坂・法)に落ち、面の中だけ均すとその節点が坂の高さのまま残って隅が埋まる
    /// (岡部の厩の NE の隅 −0.053: 節点 3 つが東の平場の外で +0.13〜+0.17)。<paramref name="rim"/> があれば、面の外でも区画(outer)の内・
    /// ほかの平らな面(keepOut)の外で、**升が足あとに掛かる節点だけ**を均しの高さにする(法は掛けない ── 面の外の坂は描かれたまま)。
    /// 当たる先: LevelPad を呼ぶ全邸の棟の下の均し(岡部の附属屋・家臣長屋)のうち、足あとが面の縁から一升の内に在る棟と、同じ式で均しの跡を数える造成QA。</summary>
    public static float LevelPadAt(Vector2[] parcel, Vector2[] foot, float y, float bf, float bc, float cell, Vector2 p, float cur, PadRim rim)
    {
        if (foot == null || foot.Length < 3) return cur;
        if (rim != null && rim.holes != null) foreach (var k in rim.holes) if (k != null && EdoGeom.PIP(k, p)) return cur;   // 面の中の触らない範囲(坂の路盤)
        if (parcel != null && !EdoGeom.PIP(parcel, p))   // ⛔ 面の外は触らない(縁の節点だけ rim で)
        {
            if (rim == null) return cur;
            if (rim.outer != null && !EdoGeom.PIP(rim.outer, p)) return cur;
            if (rim.keepOut != null) foreach (var k in rim.keepOut) if (k != null && EdoGeom.PIP(k, p)) return cur;
            float dr = EdoGeom.PIP(foot, p) ? 0f : DistPolyLine(foot, p);
            return (dr <= cell || SquareHitsPoly(foot, p, cell)) ? y : cur;
        }
        float reach = cell + 6f * Mathf.Max(bf, bc) + cell;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in foot) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        // LevelPad の窓(足あとの外接 ± reach を一升に丸めた範囲)の外は触らない
        if (p.x < mnx - reach - cell || p.x > mxx + reach + cell || p.y < mnz - reach - cell || p.y > mxz + reach + cell) return cur;
        float d = EdoGeom.PIP(foot, p) ? 0f : DistPolyLine(foot, p);
        // ⭐ 平らに取る節点は「その節点を角に持つ升(4升)のどれかが足あとに掛かる」節点(2026-10-06 EDO-0502 第36巡)。
        //   ⛔ 水平距離 ≤ 一升で取ると、回った足あとの隅の対角の節点(距離 ≤ √2 升)が法のまま残り、隅の升が勾配の上手へ描かれて
        //   厩の隅が 0.117・薪蔵の隅が 0.123 埋まった。升の範囲(節点 ± 一升の正方形)と足あとの交わりで見る。
        //   当たる先: LevelPad を呼ぶ全邸の棟の下の均し(岡部の附属屋・家臣長屋)と、同じ式で均しの跡を測る造成QA。
        return (d <= cell || SquareHitsPoly(foot, p, cell)) ? y : BatterTo(y, d - cell, bf, bc, cur);
    }

    /// <summary>軸に沿う正方形(芯 <paramref name="c"/>・半辺 <paramref name="h"/>)と多角形 <paramref name="poly"/> が交わるか
    /// (多角形の頂点が正方形の内・正方形の芯が多角形の内・辺が正方形を横切る ── Liang–Barsky)。測るだけ。</summary>
    public static bool SquareHitsPoly(Vector2[] poly, Vector2 c, float h)
    {
        if (poly == null || poly.Length < 3) return false;
        if (EdoGeom.PIP(poly, c)) return true;
        float x0 = c.x - h, x1 = c.x + h, z0 = c.y - h, z1 = c.y + h;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % poly.Length];
            float t0 = 0f, t1 = 1f, dx = b.x - a.x, dz = b.y - a.y; bool ok = true;
            float[] pp = { -dx, dx, -dz, dz }, qq = { a.x - x0, x1 - a.x, a.y - z0, z1 - a.y };
            for (int k = 0; k < 4 && ok; k++)
            {
                if (Mathf.Abs(pp[k]) < 1e-9f) { if (qq[k] < 0f) ok = false; continue; }
                float r = qq[k] / pp[k];
                if (pp[k] < 0f) { if (r > t1) ok = false; else if (r > t0) t0 = r; }
                else { if (r < t0) ok = false; else if (r < t1) t1 = r; }
            }
            if (ok) return true;
        }
        return false;
    }

    /// <summary>**据わった棟の躯体の足あと**(世界 xz の四隅)。躯体の断面(BodyFootprintLocal)を駒の今の姿勢で世界へ写す。
    /// 棟の下の均し(LevelPad)の足あとと、造成QA が均しの跡を測る足あとは**同じこの関数**で取る。測れなければ null。</summary>
    public static Vector2[] BodyFootWorld(GameObject go, string prefabPath)
    {
        Vector2 c; float w, d;
        if (go == null || string.IsNullOrEmpty(prefabPath) || !BodyFootprintLocal(prefabPath, out c, out w, out d)) return null;
        var tr = go.transform; var foot = new Vector2[4];
        float[] sx = { -0.5f, 0.5f, 0.5f, -0.5f }, sz = { -0.5f, -0.5f, 0.5f, 0.5f };
        for (int k = 0; k < 4; k++) { var wp = tr.TransformPoint(new Vector3(c.x + sx[k] * w, 0f, c.y + sz[k] * d)); foot[k] = new Vector2(wp.x, wp.z); }
        return foot;
    }

    /// <summary>**坂の芯の最寄り**: 節点 <paramref name="p"/> から芯 <paramref name="pts"/> への水平距離 <paramref name="bd"/>・道のり <paramref name="bs"/>・
    /// その点の路面の高さ <paramref name="yr"/>(<paramref name="ys"/> を道のりで一次)。坂の両端より先なら false(触らない)。
    /// GradeSakaOnce と造成QA が同じ関数で坂の範囲を測る(⛔ 式を二重に持たない)。</summary>
    public static bool SakaCenterAt(Vector2[] pts, float[] ys, Vector2 p, out float bd, out float bs, out float yr)
    {
        bd = float.MaxValue; bs = 0f; yr = ys[ys.Length - 1]; bool beyond = false;
        float acc = 0f;
        var st = new float[pts.Length];
        for (int i = 1; i < pts.Length; i++) st[i] = st[i - 1] + (pts[i] - pts[i - 1]).magnitude;
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
        acc = bs;
        for (int k = 0; k + 1 < pts.Length; k++)
            if (acc <= st[k + 1] + 1e-5f) { float u = (acc - st[k]) / Mathf.Max(1e-5f, st[k + 1] - st[k]); yr = Mathf.Lerp(ys[k], ys[k + 1], u); break; }
        return !beyond;
    }

    /// <summary>土留めの**背の小段の裏込め**の一本(run 一つ)。a→b = 天端の前の線(世界 xz)・back = 背へ向く水平の単位・
    /// top = run の天端・drop = 小段の天端からの下げ(天端 − drop)・w = 小段の幅・drain = 小段の水勾配(石垣から離れる向きへ下る)・
    /// bf = 小段の先の盛土の法 1:bf・maxFill = 盛りの上限(硬い)・parcel = 触ってよい範囲(区画)。</summary>
    public class BackBench { public string name; public Vector2 a, b, back; public float top, drop, w, drain, bf, maxFill; public Vector2[] parcel;
        /// <summary>盛りの上限を測る元の地盤(造成の設計面)。null なら今の地盤 ── 流し直しで盛りが積もらないよう設計面を渡す。</summary>
        public Func<Vector2, float> baseAt;
        /// <summary>盛らない所(他の土留めの見え面の前 ── 小段の端の法が隣の袖の前へ回り込まない・EDO-0502 第25巡)。null なら無し。</summary>
        public Func<Vector2, bool> keepOut;
        /// <summary>小段を走りに沿って落とす勾配(b の端が高く a の側へ下がる・指図 endRaise.drain の 1/20)。0 なら走りには落とさない(2026-10-06 EDO-0502 第37巡)。</summary>
        public float drainAlong;
        /// <summary>真なら run の両端の先(走りの外)へは盛らない【硬】── 端の側の天端を越えて表へ土を落とさない(指図 endRaise.drain)。</summary>
        public bool noEndSpill;
        /// <summary>切りの上限(設計面 baseAt から)。0 なら切らない(盛るだけ・従前)。> 0 なら小段より高い今の地盤を小段と 1:bf の法まで切る
        /// (指図 sodeSlope 追記 2026-10-07「出隅の踊り場の背を天端 −0.15 の水平に描き直し、上手の切り ≤0.35・下手の盛り ≤0.35」【硬】・EDO-0502 第42巡)。</summary>
        public float maxCut;
        /// <summary>真なら b の端の先(走りの外)へ盛らず、端の手前で 1:bf で回して下ろす ── 盛りの法尻が b の端の線に来る【硬】(指図 TW_Minami_Koshi.returnEnd 追記
        /// 2026-10-07「端の手前で妻の外の法へ 1:1.5 で回して下ろし、法尻は長屋の背と妻から一間の外・口へ入れない」・EDO-0502 第45巡)。
        /// 当たる先: 返しの終わりを積み止めで終える run(岡部 TW_Minami_Koshi#ret)。</summary>
        public bool tuckB;
        /// <summary>真なら切りの上限 maxCut を**小段の上だけ**に当て、小段の先の 1:bf の法は上限なしで地山に交わるまで切る【硬】── 法は小段の縁の
        /// (上限で頭打ちした)高さから上がる(指図 TW_Kado_Shumen.sideEnd 追記 2026-10-10b「切りの上限 0.7 は小段だけに当て、超える分は擦り付けで受ける」・EDO-0502 第81巡)。
        /// 当たる先: 背の地山が高い延長の背の小段(岡部 TW_Kado_Shumen の sideEnd)。</summary>
        public bool cutBenchOnly; }

    /// <summary>**土留めの見え面の前の帯**(線 a→b・背 back の逆の側へ depth まで・走りの両端は線の内)に点 p が入るか。
    /// 当たる先: <see cref="BackBench.keepOut"/> ── 小段の裏込めの端の法(1:bf)が、隣の土留めの見え面の前へ回り込んで土の箱を立てない
    /// (2026-10-05 岡部 門の内: TW_Kado_Sode_0 の小段の端の法が TW_Kado_Sode_1_0/3_0 の前へ 2.5m 回り込み、地盤 16.50 の上に 17.50 の土の箱を立てた)。</summary>
    public static bool InFrontOfFace(Vector2 a, Vector2 b, Vector2 back, Vector2 p, float depth)
    {
        Vector2 ab = b - a; float L = ab.magnitude; if (L < 1e-4f) return false;
        float s = Vector2.Dot(p - a, ab / L), d = Vector2.Dot(p - a, back);
        return s >= 0f && s <= L && d < 0f && d > -depth;
    }

    /// <summary>**背の小段の裏込めが節点 p に与える高さ**(2026-10-04 EDO-0502 第13巡・岡部 TW_Kado_Sode.backfill)。
    /// 前の線より前(門の内の側)は触らない。小段 = 前の線から背へ w まで、天端 − drop から石垣を離れる向きへ drain で下る面。
    /// その先と run の両端の先は 1:bf の法で下ろし、今の地盤 cur より高い所だけ盛る(⛔ 切らない)。盛りは maxFill で頭打ち(硬い・超えた量は呼び手が測る)。
    /// 盛る・GradeQA・皮の設計の地盤が**同じこの関数**を使う(式を二重に持たない)。当たる先: 背が法の土留め・袖石垣(岡部 TW_Kado_Sode)。</summary>
    public static float BackBenchAt(BackBench k, Vector2 p, float cur)
    {
        if (k.parcel != null && !EdoGeom.PIP(k.parcel, p)) return cur;
        if (k.keepOut != null && k.keepOut(p)) return cur;
        Vector2 ab = k.b - k.a; float L = ab.magnitude; if (L < 1e-4f) return cur;
        Vector2 t = ab / L;
        float sAl = Vector2.Dot(p - k.a, t), dn = Vector2.Dot(p - k.a, k.back);
        if (dn < 0f) return cur;                                       // 前(門の内)は触らない
        if (k.noEndSpill && (sAl < 0f || sAl > L)) return cur;          // 走りの外へは盛らない(硬い)
        if (k.tuckB && sAl > L) return cur;                             // b の端の先へは盛らない(端の手前で回して下ろす)
        float dEnd = sAl < 0f ? -sAl : (sAl > L ? sAl - L : 0f);
        float benchY = k.top - k.drop - k.drain * Mathf.Min(dn, k.w) - k.drainAlong * (L - Mathf.Clamp(sAl, 0f, L));
        float hh = Mathf.Sqrt(Mathf.Pow(Mathf.Max(0f, dn - k.w), 2f) + dEnd * dEnd);
        float target = benchY - hh / k.bf;
        float b0 = k.baseAt != null ? k.baseAt(p) : cur; if (float.IsNaN(b0)) b0 = cur;
        if (k.maxCut > 0f)
        {   // 切り: 小段 + 1:bf の法(上へ)より高い今の地盤を切る ── 切りの上限は設計面から(硬)
            float hi = benchY + hh / k.bf;
            if (cur > hi)
            {
                if (k.cutBenchOnly && (dn > k.w || dEnd > 0f))
                {   // 小段の先: 小段の縁(上限で頭打ちした高さ)から 1:bf で上がる法 ── 上限なしで地山まで(超える分は法で受ける)
                    Vector2 pe = k.a + t * Mathf.Clamp(sAl, 0f, L) + k.back * Mathf.Min(dn, k.w);
                    float be = k.baseAt != null ? k.baseAt(pe) : float.NaN; float edgeY = benchY;
                    if (!float.IsNaN(be)) edgeY = Mathf.Max(benchY, be - k.maxCut);
                    return Mathf.Min(cur, edgeY + hh / k.bf);
                }
                return Mathf.Min(cur, Mathf.Max(hi, b0 - k.maxCut));
            }
        }
        if (k.tuckB) target = Mathf.Min(target, b0 + (L - sAl) / k.bf);   // 法尻 = b の端の線(設計面から 1:bf で上がる)
        if (target <= cur) return cur;
        return Mathf.Max(cur, Mathf.Min(target, b0 + k.maxFill));
    }

    /// <summary>**小段の組が節点 p に与える高さ**(盛りは最大・切りは最小 ── 盛る小段が一つでもあれば盛りが勝つ)。BackBenchWrite・皮の設計の地盤・GradeQA が
    /// 同じこれを使う(式を二重に持たない)。当たる先: BackBench を渡すすべて(岡部 袖の小段・端の天端上げ・出隅の踊り場)。</summary>
    public static float BackBenchesAt(IList<BackBench> ks, Vector2 p, float cur)
    {
        float up = cur, dn = cur;
        foreach (var k in ks) { float v = BackBenchAt(k, p, cur); if (v > up) up = v; if (v < dn) dn = v; }
        return up > cur + 1e-5f ? up : dn;
    }

    /// <summary>**土留めの端の一部を高い天端の別の run に割る長さ**(指図 terraceWalls[].endRaise・2026-10-06 EDO-0502 第37巡 岡部 TW_Kita_Koshi)。
    /// <paramref name="backFromEnd"/>(s) = 端から内へ s の背の地盤。端から内へ測って背が <paramref name="thr"/> を超え始める所 <paramref name="sCross"/> までを狙いとし、
    /// 【柔】長さの狙い [<paramref name="lo"/>, <paramref name="hi"/>](一間〜二間)の中で sCross に最も近い長さを採る(狙いを外せば <paramref name="softMiss"/>)。
    /// 【硬】段違いの継ぎ目は端から <paramref name="minIn"/>(1 駒)以上内・残る低い run も <paramref name="minIn"/> 以上 ── 取れなければ NaN(上げない)。
    /// 当たる先: 背の地盤が端へ向かって上がる腰の土留めの端(見切り石の頭を背の土より上げる)。測るだけ。</summary>
    public static float RaiseEndLen(Func<float, float> backFromEnd, float thr, float L, float minIn, float lo, float hi, out float sCross, out bool softMiss, float ds = 0.1f)
    {
        sCross = float.NaN; softMiss = false;
        for (float s = 0f; s <= L + 1e-4f; s += ds) { float h = backFromEnd(s); if (!float.IsNaN(h) && h > thr) { sCross = s; break; } }
        float want = float.IsNaN(sCross) ? lo : sCross;
        float len = Mathf.Clamp(want, Mathf.Max(lo, minIn), Mathf.Max(hi, minIn));
        softMiss = float.IsNaN(sCross) || sCross < lo - 1e-3f || sCross > hi + 1e-3f;
        if (len < minIn - 1e-4f || L - len < minIn - 1e-4f) return float.NaN;
        return len;
    }

    /// <summary>**段違いの run を背の法の等高線で割る**(指図 TW_Kado_Sode.runSplit・EDO-0502 第32巡)。道のり [0, <paramref name="L"/>](折れ線を跨いでよい ──
    /// ⛔ 節点で切らない)で背の高さ <paramref name="backAt"/> を <paramref name="ds"/> 刻みに測り、各点の天端 = 背を <paramref name="step"/> 刻みで切り上げた値。
    /// run の境 = 天端の値が変わる所(背の法が刻みの等高線を横切る所)。長さ <paramref name="minLen"/> 未満の run は作らず、隣の高い側の run に含める【硬】。
    /// 返り値 = (始まり, 終わり, 天端) を道のりの順に。天端は刻みの倍数だけ(中間値は出さない)。
    /// 当たる先: 法なりの段違いの土留め(岡部 TW_Kado_Sode)。返しの割り(RunsByCrestGap)・節点ごとの割り(RunsByBackSlope)とは別の規則。</summary>
    public static List<Vector3> RunsByContour(float L, Func<float, float> backAt, float step, float minLen, float ds = 0.1f)
    {
        var res = new List<Vector3>();
        int n = Mathf.Max(1, Mathf.CeilToInt(L / ds));
        float prevTop = float.NaN, s0 = 0f;
        for (int i = 0; i <= n; i++)
        {
            float s = L * i / n, h = backAt(s);
            float top = float.IsNaN(h) ? prevTop : Mathf.Ceil(h / step - 1e-4f) * step;
            if (float.IsNaN(prevTop)) { prevTop = top; continue; }
            if (Mathf.Abs(top - prevTop) > 1e-4f)
            {   // 境は前の点と今の点の間の等高線(一次で内挿)
                float hp = backAt(L * (i - 1) / n), lv = Mathf.Min(top, prevTop);
                float u = float.IsNaN(hp) || float.IsNaN(h) || Mathf.Abs(h - hp) < 1e-5f ? 0.5f : Mathf.Clamp01((lv - hp) / (h - hp));
                float sb = L * (i - 1 + u) / n;
                res.Add(new Vector3(s0, sb, prevTop)); s0 = sb; prevTop = top;
            }
        }
        if (!float.IsNaN(prevTop)) res.Add(new Vector3(s0, L, prevTop));
        // 短い run は隣の高い側へ(短い順に一つずつ)
        while (res.Count > 1)
        {
            int k = -1; float best = minLen;
            for (int i = 0; i < res.Count; i++) { float len = res[i].y - res[i].x; if (len < best - 1e-4f) { best = len; k = i; } }
            if (k < 0) break;
            int nb = k == 0 ? 1 : k == res.Count - 1 ? k - 1 : (res[k - 1].z >= res[k + 1].z ? k - 1 : k + 1);
            if (nb < k) res[nb] = new Vector3(res[nb].x, res[k].y, res[nb].z); else res[nb] = new Vector3(res[k].x, res[nb].y, res[nb].z);
            res.RemoveAt(k);
        }
        for (int i = res.Count - 1; i > 0; i--)
            if (Mathf.Abs(res[i].z - res[i - 1].z) < 1e-4f) { res[i - 1] = new Vector3(res[i - 1].x, res[i].y, res[i].z); res.RemoveAt(i); }
        return res;
    }

    /// <summary>run の線 a→b を、**背の法の高さ**(<paramref name="backAt"/>(s) = 道のり s の背の地盤)で天端の割りへ分ける
    /// (指図 TW_Kado_Sode.top: 天端 = run の上手の端の背の高さを <paramref name="step"/> 刻みで切り上げ・run の中で背が下がる量 ≤ <paramref name="maxDrop"/>・超えたら切る)。
    /// 返す: (s0, s1, 天端) の並び(道のりの順)。<paramref name="minLen"/> 未満の切れ端は隣へ寄せる。測るだけ。</summary>
    public static List<Vector3> RunsByBackSlope(float L, Func<float, float> backAt, float step, float maxDrop, float minLen, float ds = 0.25f)
    {
        var res = new List<Vector3>();
        int n = Mathf.Max(1, Mathf.CeilToInt(L / ds)); var ss = new float[n + 1]; var hs = new float[n + 1];
        for (int i = 0; i <= n; i++) { ss[i] = L * i / n; hs[i] = backAt(ss[i]); }
        // 上手 = 背の高い端。上手から下手へ歩いて割る
        bool fwd = !(hs[0] > hs[n]);   // 上手が s=L 側なら fwd(L から 0 へ歩く)
        int i0 = fwd ? n : 0, di = fwd ? -1 : 1;
        int cur = i0;
        while (true)
        {
            float h0 = float.NaN; for (int i = cur; i >= 0 && i <= n; i += di) if (!float.IsNaN(hs[i])) { h0 = hs[i]; break; }
            if (float.IsNaN(h0)) break;
            float top = Mathf.Ceil(h0 / step - 1e-4f) * step;
            int j = cur;
            while (j + di >= 0 && j + di <= n && (float.IsNaN(hs[j + di]) || h0 - hs[j + di] <= maxDrop + 1e-4f)) j += di;
            // 残りが短すぎるならこの run に含める
            int end = (di < 0) ? 0 : n;
            if (j != end && Mathf.Abs(ss[end] - ss[j]) < minLen) j = end;
            float a = Mathf.Min(ss[cur], ss[j]), b = Mathf.Max(ss[cur], ss[j]);
            res.Add(new Vector3(a, b, top));
            if (j == end) break;
            cur = j;
        }
        res.Sort((x, y) => x.x.CompareTo(y.x));
        // 同じ天端の隣り合う run は一つに(段の境を作らない)
        for (int i = res.Count - 1; i > 0; i--)
            if (Mathf.Abs(res[i].z - res[i - 1].z) < 1e-4f) { res[i - 1] = new Vector3(res[i - 1].x, res[i].y, res[i].z); res.RemoveAt(i); }
        return res;
    }

    /// <summary>**天端と背の地盤の差で run を切る割り**(指図 TW_Minami_Koshi.returnTop・EDO-0502 第24巡 ── 普請方の設計)。
    /// 上手の端(s = 0・出隅)の天端 <paramref name="firstTop"/> で始め、天端 − 背の地盤 &gt; <paramref name="maxGap"/>【硬】になる所で run を切り、
    /// 次の run の天端 = その上手の端の背の地盤を <paramref name="step"/> 刻みで切り上げた値(前の天端を越えない)。
    /// 終わり: 表の地表と背の地盤の差が <paramref name="endDiff"/> 未満になった所(<paramref name="sEnd"/>・無ければ L)。
    /// ⭐ run の長さに下限は無い ── <paramref name="minLen"/>(1 駒)より短い run は、駒の端を**下手の端**に合わせ、始まりを上手へ延ばして
    /// 余りを上手の run の駒の裏へ重ねて埋める(返す a が前の run の b より手前になる)。返す: (a, b, 天端)。測るだけ。
    /// 当たる先: 段違いの天端で割る返し・袖(RunsByBackSlope の「下がる量」でなく「天端との差」で切る欄 ── いまは岡部の腰石垣の返し)。</summary>
    /// <para>⭐ <paramref name="dropHidden"/> を渡すと(指図 TW_Minami_Koshi.returnEnd 追記 2026-10-07「返しの最後の run が 1 駒より短く上の run の裏に隠れるときは
    /// その run を作らない」・EDO-0502 第45巡)、最後の run が 1 駒より短く上手の run の後に続く(延ばせば上の run の駒の裏へ重なる)とき、延ばさずに外して
    /// <paramref name="dropHidden"/> へ入れ、<paramref name="sEnd"/> を上手の run の終わりへ戻す ── 返しはその run の端で終わる(端の納めは呼び手 ── 積み止め)。
    /// 当たる先: 返しの割り(岡部 TW_Minami_Koshi の両端の返し)。</para></summary>
    public static List<Vector3> RunsByCrestGap(float L, Func<float, float> backAt, Func<float, float> frontAt, float firstTop, float step, float maxGap,
                                               float endDiff, float minLen, out float sEnd, float ds = 0.25f, List<Vector3> dropHidden = null)
    {
        var res = new List<Vector3>(); sEnd = L;
        int n = Mathf.Max(1, Mathf.CeilToInt(L / ds));
        for (int i = 1; i <= n; i++)
        {
            float s = L * i / n, bk = backAt(s), fr = frontAt != null ? frontAt(s) : float.NaN;
            if (!float.IsNaN(bk) && !float.IsNaN(fr) && Mathf.Abs(bk - fr) < endDiff) { sEnd = s; break; }
        }
        float top = firstTop, a = 0f; int m = Mathf.Max(1, Mathf.CeilToInt(sEnd / ds));
        for (int i = 0; i <= m; i++)
        {
            float s = sEnd * i / m, bk = backAt(s); if (float.IsNaN(bk)) continue;
            if (top - bk > maxGap + 1e-4f && s > a + 1e-3f)
            {
                res.Add(new Vector3(a, s, top));
                float nt = Mathf.Min(top, Mathf.Ceil(bk / step - 1e-4f) * step);
                a = s; top = nt;
            }
        }
        if (sEnd - a > 1e-3f) res.Add(new Vector3(a, sEnd, top));
        if (dropHidden != null && res.Count >= 2 && res[res.Count - 1].y - res[res.Count - 1].x < minLen)
        { dropHidden.Add(res[res.Count - 1]); res.RemoveAt(res.Count - 1); sEnd = res[res.Count - 1].y; }
        for (int i = 0; i < res.Count; i++)
            if (res[i].y - res[i].x < minLen) res[i] = new Vector3(Mathf.Max(0f, res[i].y - minLen), res[i].y, res[i].z);
        return res;
    }

    /// <summary>背の小段の裏込めを地形へ書く(<see cref="BackBenchAt"/> を節点ごとに・run を順に重ねる)。硬い: 盛るだけ・区画の外は触らない・盛り ≤ maxFill。
    /// ⟶ 返す: 書いた節点の数(盛りの最大は out)。</summary>
    public static int BackBenchWrite(IList<BackBench> ks, out float fillMax) { float cm; return BackBenchWrite(ks, out fillMax, out cm); }
    public static int BackBenchWrite(IList<BackBench> ks, out float fillMax, out float cutMax) { return BackBenchWrite(ks, out fillMax, out cutMax, null); }
    /// <summary><paramref name="recPath"/>: 書いた節点の設計の高さを残す(<see cref="SaveNodeTargets"/> ── 造成QA が domain reload の後も同じ小段を引く。
    /// ⚠ GradeQA が小段の式を設計面で引き直すと、延長の背の小段(静的な一覧)が reload で消え、盛り ≤ 上限の頭打ちの節点 28 升を超過と読んだ・岡部 第131巡)。</summary>
    public static int BackBenchWrite(IList<BackBench> ks, out float fillMax, out float cutMax, string recPath)
    {
        fillMax = 0f; cutMax = 0f; if (ks == null || ks.Count == 0) return 0;
        var t = T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue, reach = 0f;
        foreach (var k in ks)
        {
            reach = Mathf.Max(reach, k.w + k.bf * (Mathf.Max(k.maxFill, k.maxCut) + (k.cutBenchOnly ? 6f : 1f)) + 2f * cell);   // 小段の先を上限なしで切る法は地山の起伏 6m まで届かせる
            foreach (var q in new[] { k.a, k.b }) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - reach - tp.x) / cell), 0, hres - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - reach - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx + reach - tp.x) / cell), 0, hres - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz + reach - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h); int n = 0; var rec = recPath != null ? new Dictionary<long, float>() : null;
        for (int iz = 0; iz < h; iz++)
            for (int ix = 0; ix < w; ix++)
            {
                var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
                float cur = H[iz, ix] * ts.y + tp.y, nw = cur;
                nw = BackBenchesAt(ks, p, cur);
                if (Mathf.Abs(nw - cur) < 1e-4f) continue;
                if (rec != null) rec[((long)(x0 + ix) << 32) ^ (uint)(z0 + iz)] = nw;
                if (nw > cur) fillMax = Mathf.Max(fillMax, nw - cur); else cutMax = Mathf.Max(cutMax, cur - nw);
                H[iz, ix] = (nw - tp.y) / ts.y; n++;
            }
        if (n > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        if (rec != null) SaveNodeTargets(recPath, t.name, rec, null);
        return n;
    }

    /// <summary>**法尻の土留めの背の小段**(切り)の一本(指図 terraceWalls[].toeBench・EDO-0502 第33巡)。a + t·s = 線・back = 背へ向く水平の単位・
    /// crest[i] = 道のり s = s0 + i·ds の駒の天端(実メッシュの最上点)・bench0..bench1 = 小段を取る道のり(差し込んだ端は届いた所まで)・
    /// dFront = 駒の見え面の前の縁(これより前は触らない)・w = 小段の奥行(駒の控えの後端 + behind)・drop = 天端からの下げ・bf = 小段の先の盛の法 1:bf。</summary>
    public class ToeBench { public string name; public Vector2 a, t, back; public float s0, ds, bench0, bench1, dFront, w, drop, bf; public float[] crest; public Vector2[] parcel;
        public bool ins0, ins1; }

    /// <summary>**法尻の土留めの背の小段を、据えた駒の実メッシュから解く**(指図 toeBench: 天端 − drop の小段を控えの後端 + behind までとり、その先 1:bf で
    /// 平場の縁まで盛の法を描き直す【硬: 天端に土を載せない】)。⛔ 駒の基準点で測らない ── 全頂点の線への射影で、走り(s)・控えの後端(d の最大)・
    /// 見え面の前の縁(d の最小)・天端(s の帯ごとの y の最大)を取る。差し込んだ端(端の先の地盤 <paramref name="groundAt"/> が天端 + <paramref name="reach"/> を
    /// 超える端・指図 nozuraEndRule ④)は、小段を端から <paramref name="tail"/>(半駒)手前で止める ── その先は根入れとして土が載ってよい区間。
    /// 当たる先: 盛の法の法尻に立つ野面の土留め(岡部 TW_Nishi_Kado ── TW_Higashi_Minami は 2026-10-12 案A で石垣 野面へ)── 背が法で土が天端を越える土留め全般。⟶ 返す: 解けなければ null(理由は note)。</summary>
    public static ToeBench ToeBenchOf(string name, IList<GameObject> pieces, Vector2 a, Vector2 b, Vector2 back, float drop, float behind, float bf,
                                      Vector2[] parcel, Func<Vector2, float> groundAt, float reach, float tail, System.Text.StringBuilder note)
    {
        Vector2 ab = b - a; float L = ab.magnitude; if (L < 1e-3f || pieces == null || pieces.Count == 0) { if (note != null) note.AppendLine("    " + name + ": 駒が無い ── 小段を取らない"); return null; }
        Vector2 t = ab / L; const float ds = 0.25f;
        var vs = new List<Vector3>();
        foreach (var g in pieces) if (g != null) vs.AddRange(Body(g.transform, 6000));
        if (vs.Count == 0) { if (note != null) note.AppendLine("    " + name + ": 駒の頂点が無い"); return null; }
        float s0 = float.MaxValue, s1 = float.MinValue, dMin = float.MaxValue, dMax = float.MinValue;
        foreach (var v in vs) { var q = new Vector2(v.x, v.z) - a; float s = Vector2.Dot(q, t), d = Vector2.Dot(q, back); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s); dMin = Mathf.Min(dMin, d); dMax = Mathf.Max(dMax, d); }
        int n = Mathf.Max(1, Mathf.CeilToInt((s1 - s0) / ds)) + 1; var cr = new float[n]; for (int i = 0; i < n; i++) cr[i] = float.NaN;
        // ⭐ 天端は**背の縁の石の上面**(控えの後端から 0.5m の帯の頂点の最上点)で帯ごとに取り、隣の帯と最小を取る(EDO-0502 第34巡):
        //   帯の全頂点の最上点で引くと、run の継ぎ目(辺24 の 098f/099f)で背の縁の石が 0.14 低く、小段の土が石の上面に 0.09〜0.2 被った
        foreach (var v in vs) { var q = new Vector2(v.x, v.z) - a; if (Vector2.Dot(q, back) < dMax - 0.5f) continue; int i = Mathf.Clamp(Mathf.RoundToInt((Vector2.Dot(q, t) - s0) / ds), 0, n - 1); if (float.IsNaN(cr[i]) || v.y > cr[i]) cr[i] = v.y; }
        // 穴(頂点の落ちない帯)は隣から埋める
        for (int i = 1; i < n; i++) if (float.IsNaN(cr[i])) cr[i] = cr[i - 1];
        for (int i = n - 2; i >= 0; i--) if (float.IsNaN(cr[i])) cr[i] = cr[i + 1];
        { var c2 = (float[])cr.Clone(); for (int i = 0; i < n; i++) { if (i > 0) cr[i] = Mathf.Min(cr[i], c2[i - 1]); if (i + 1 < n) cr[i] = Mathf.Min(cr[i], c2[i + 1]); } }
        var k = new ToeBench { name = name, a = a, t = t, back = back, s0 = s0, ds = ds, crest = cr, dFront = dMin, w = dMax + behind, drop = drop, bf = bf, parcel = parcel, bench0 = s0, bench1 = s1 };
        // 差し込んだ端: 端の先 0.3m・奥行の中ほどの地盤が端の天端 + reach を超える
        if (groundAt != null)
        {
            float dm = (dMin + dMax) * 0.5f;
            float g0 = groundAt(a + t * (s0 - 0.3f) + back * dm), g1 = groundAt(a + t * (s1 + 0.3f) + back * dm);
            if (!float.IsNaN(g0) && g0 > cr[0] + reach) { k.ins0 = true; k.bench0 = s0 + tail; }
            if (!float.IsNaN(g1) && g1 > cr[n - 1] + reach) { k.ins1 = true; k.bench1 = s1 - tail; }
        }
        if (note != null) note.AppendLine("    " + name + ": 走り " + (s1 - s0).ToString("F2") + "m・控えの後端 " + dMax.ToString("F2") + "(線から)・見え面の前の縁 " + dMin.ToString("F2")
                                          + "・小段の奥行 " + k.w.ToString("F2") + "・天端 " + cr[0].ToString("F2") + "→" + cr[n - 1].ToString("F2")
                                          + (k.ins0 ? "・始まりは差し込み(半駒 " + tail.ToString("F1") + " 手前で止める)" : "") + (k.ins1 ? "・終わりは差し込み(半駒 " + tail.ToString("F1") + " 手前で止める)" : ""));
        return k;
    }

    /// <summary>**駒を据える前の法尻の背の小段**(指図 nozuraEndRule 追記3 toeEnd・EDO-0502 第34巡): 区間の線(見え面の線)・設計の天端(crestAt)と、
    /// 駒の控えの後端(呼び手が焼いた駒の全頂点から測った値)+ 指図の奥行で <see cref="ToeBench"/> を起こす。走りは区間の全長に、端の先へ ext0/ext1
    /// (見切り石の外形の最大の寸)を足す。据えた後は <see cref="ToeBenchOf"/>(実メッシュ)で引き直す。当たる先: <see cref="ToeBenchOf"/> と同じ。</summary>
    public static ToeBench ToeBenchOnSeg(NozuraSeg sg, Vector2 back, float w, float drop, float bf, Vector2[] parcel, float ext0, float ext1)
    {
        float L = sg.Len; const float ds = 0.25f; int n = Mathf.Max(1, Mathf.CeilToInt((L + ext0 + ext1) / ds)) + 1;
        var cr = new float[n];
        // 端の見切り石は頭を端の天端に揃えて端から走りの内へも入る ⇒ 端から外形の寸(ext)の内は天端を端の値で頭打ち(勾配の run で小段が石の頭を越えない)
        float c0 = sg.crestAt(0f), c1 = sg.crestAt(L);
        for (int i = 0; i < n; i++)
        {
            float s = -ext0 + i * ds; float c = sg.crestAt(Mathf.Clamp(s, 0f, L));
            if (ext0 > 0f && s <= ext0) c = Mathf.Min(c, c0);
            if (ext1 > 0f && s >= L - ext1) c = Mathf.Min(c, c1);
            cr[i] = c;
        }
        return new ToeBench { name = sg.name + "#toeEnd", a = sg.a, t = sg.Dir, back = back.normalized, s0 = -ext0, ds = ds, crest = cr, dFront = 0f, w = w, drop = drop, bf = bf,
                              parcel = parcel, bench0 = -ext0, bench1 = L + ext1 };
    }

    /// <summary>**法尻の土留めの背の小段が節点 p に与える高さ**(切るだけ ── 今の地盤 cur より低い所だけ下げる・⛔ 盛らない)。
    /// 見え面の前の縁より前は触らない。小段 = 天端(その道のりの駒の最上点)− drop の水平な面を奥行 w まで、その先と小段の両端の先は 1:bf で上がる面。
    /// 地形を切る(<see cref="ToeBenchWrite"/>)・皮の設計の地盤・GradeQA が**同じこの関数**を使う。当たる先: <see cref="ToeBenchOf"/> と同じ。</summary>
    public static float ToeBenchAt(ToeBench k, Vector2 p, float cur)
    {
        if (k == null || float.IsNaN(cur)) return cur;
        if (k.parcel != null && !EdoGeom.PIP(k.parcel, p)) return cur;
        var q = p - k.a; float s = Vector2.Dot(q, k.t), d = Vector2.Dot(q, k.back);
        if (d < k.dFront) return cur;
        float sc = Mathf.Clamp(s, k.bench0, k.bench1), dEnd = Mathf.Abs(s - sc);
        int i = Mathf.Clamp(Mathf.RoundToInt((sc - k.s0) / k.ds), 0, k.crest.Length - 1);
        float hh = Mathf.Sqrt(Mathf.Pow(Mathf.Max(0f, d - k.w), 2f) + dEnd * dEnd);
        float target = k.crest[i] - k.drop + hh / k.bf;
        return target < cur ? target : cur;
    }

    /// <summary>地形の高さの格子の一升 [m](heightmap の節点の間隔)。当たる先: 地形を書く関数の守りの幅(床の升を切らない)。</summary>
    public static float HeightCell() { var td = T().terrainData; return td.size.x / (td.heightmapResolution - 1); }

    /// <summary>法尻の土留めの背の小段を地形へ切る(<see cref="ToeBenchAt"/> を節点ごとに)。硬い: 切るだけ・区画の外は触らない・
    /// <paramref name="keep"/>(点・切った後の高さ → 守るか ── 建物の足あと・塀の床の升)は触らない。⟶ 返す: 切った節点の数(切りの最大と位置は out)。</summary>
    public static int ToeBenchWrite(IList<ToeBench> ks, Func<Vector2, float, bool> keep, out float cutMax, out Vector2 cutAt)
    {
        cutMax = 0f; cutAt = Vector2.zero; if (ks == null || ks.Count == 0) return 0;
        var t = T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var k in ks)
        {
            float reach = k.w + k.bf * 6f + 2f * cell;
            foreach (var s in new[] { k.s0 - k.bf * 6f, k.s0 + k.crest.Length * k.ds + k.bf * 6f })
                foreach (var d in new[] { k.dFront, reach })
                { var q = k.a + k.t * s + k.back * d; mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        }
        int x0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / cell), 0, hres - 1), z0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / cell), 0, hres - 1);
        int x1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / cell), 0, hres - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / cell), 0, hres - 1);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h); int n = 0;
        for (int iz = 0; iz < h; iz++)
            for (int ix = 0; ix < w; ix++)
            {
                var p = new Vector2(tp.x + (x0 + ix) * cell, tp.z + (z0 + iz) * cell);
                float cur = H[iz, ix] * ts.y + tp.y, nw = cur;
                foreach (var k in ks) nw = Mathf.Min(nw, ToeBenchAt(k, p, cur));
                if (cur - nw < 1e-4f) continue;
                if (keep != null && keep(p, nw)) continue;   // 切る所だけ問う(点と切った後の高さ ── 数えるのは守った節点だけ)
                if (cur - nw > cutMax) { cutMax = cur - nw; cutAt = p; }
                H[iz, ix] = (nw - tp.y) / ts.y; n++;
            }
        if (n > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        return n;
    }

    /// <summary>**一枚の均しの足あと**(指図 `service[].padGroup` ── 同じ組の棟と棟の間を一枚の平らな床面にする・2026-10-07 EDO-0502 第46巡)。
    /// 組の各棟の足あと(<see cref="BodyFootWorld"/>)の頂点の凸包を返す。⛔ 棟ごとに均すと 2m 格子の節点を分け合い、片方の縁が浮くか埋まる
    /// (岡部の薪蔵 −0.094・米蔵 +0.017 が 45 巡残った)。棟の間の一間も同じ高さで平らに取る。硬い: 組の yAt は等しい(呼び手が検める)。
    /// 当たる先: padGroup を持つ全邸の附属屋(今は岡部の米蔵・薪蔵)と、同じ足あとで均しの跡を数える造成QA。測るだけ。
    /// ⟶ 返す: 凸包(反時計回り)。足あとが無ければ null</summary>
    public static Vector2[] PadGroupFoot(IList<Vector2[]> feet)
    {
        var pts = new List<Vector2>();
        foreach (var f in feet) if (f != null) pts.AddRange(f);
        if (pts.Count < 3) return null;
        var h = ConvexHull2(pts);
        return h.Count >= 3 ? h.ToArray() : null;
    }

    /// <summary>**棟の下の均し**(2026-10-03 EDO-0502 第4巡・岡部の厩と蔵1 が勾配の面の上手へ 0.78m 埋まった)。
    /// 指図の `yAt`(棟の芯での面の高さ)で足あと <paramref name="foot"/>(呼び手が据えた駒の躯体から測る・世界 xz)の下を平らにし、
    /// その外は盛土 1:<paramref name="bf"/>・切土 1:<paramref name="bc"/> の法で今の地盤へ擦り付ける。
    /// ⭐ 2m 格子は節点の間を一次で描く ⇒ 足あとの縁に掛かる升の節点まで平らにしないと縁の下が勾配のまま描かれる ──
    /// 平らに取るのは足あと + 一升(<c>cell</c>)。硬い: 区画の外の節点は触らない。冪等(今の地盤を法で挟むだけ)。
    /// 当たる先: 勾配の面(指図 `yFrom`)の上に建つ附属屋(岡部の厩・蔵・米蔵・薪蔵・家臣長屋)── 呼び手が埋まり・浮きを測って渡す。
    /// ⟶ 返す: 書いた節点の数(切 / 盛の最大は out)</summary>
    public static int LevelPad(Vector2[] parcel, Vector2[] foot, float y, float bf, float bc, out float cutMax, out float fillMax)
    { return LevelPad(parcel, foot, y, bf, bc, out cutMax, out fillMax, null); }

    /// <summary>LevelPad に面の外の縁の節点(<see cref="PadRim"/>)を足したもの。式は LevelPadAt(rim つき)だけ。</summary>
    public static int LevelPad(Vector2[] parcel, Vector2[] foot, float y, float bf, float bc, out float cutMax, out float fillMax, PadRim rim)
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
                float cur = H[iz, ix] * ts.y + tp.y;
                float nw = LevelPadAt(parcel, foot, y, bf, bc, cell, p, cur, rim);   // ⭐ 一節点の式は LevelPadAt だけ(造成QA も同じ式で均しの跡を数える)
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

    /// <summary>**棟の背の前の地盤が座より高い所を、犬走りの幅だけ切り下げ地山へ切土で摺り付ける**(<see cref="FillAlongBack"/> の切りの対・
    /// 2026-10-04 EDO-0533 土井 boundaryPlinth.back の丙)。線 <paramref name="a"/>–<paramref name="b"/> = 棟の背の面の足元、<paramref name="inward"/> = 区画の内向き。
    /// 背の面から内へ <paramref name="band"/>[m] までと棟の下の一升の節点を <paramref name="y"/> まで下げ、帯の外は切土 1:<paramref name="bc"/> で今の地盤へ上げる。
    /// 硬い: 切るだけ(盛らない)・区画の外の節点は触らない。冪等。⟶ 返す: 書いた節点の数(切りの最大と体積は out)。
    /// 当たる先: 基壇の天端に土台を据えた棟の背の内の地盤が座より高い所(土井の表長屋 E13_N05 の北端・表門の北の隅)。</summary>
    public static int CutAlongBack(Vector2[] parcel, Vector2 a, Vector2 b, Vector2 inward, float y, float band, float bc, out float cutMax, out float vol)
    {
        cutMax = 0f; vol = 0f;
        var t = T(); var td = t.terrainData;
        int hres = td.heightmapResolution; Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        float reach = band + cell + 6f * bc + cell;
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
                if (dn < -cell || s < -0.01f || s > L + 0.01f) continue;    // 棟の下は一升まで・⛔ 線の端の外(隣の棟の背)は切らない
                float over = Mathf.Max(0f, dn - band);
                float tgt = y + over / bc;
                float cur = H[iz, ix] * ts.y + tp.y;
                if (tgt >= cur - 1e-4f) continue;                           // 切るだけ
                cutMax = Mathf.Max(cutMax, cur - tgt); vol += (cur - tgt) * cell * cell;
                H[iz, ix] = (tgt - tp.y) / ts.y; n++;
            }
        // ② 描かれた地表で検める ── 2m 格子は帯(0.3m)を描けず、切った節点と切らない奥の節点の間を一次で描いて帯の上に地山が残る。
        //   帯の中の点(背の面から内へ 0〜band+0.6・走りの 0.25m 刻み)で描かれた地表 > y の所は、その升の四隅の節点を超えた分だけ下げる
        //   (三角形の補間は四隅の凸結合 ⇒ 四隅を下げればその点は y 以下)。切りの勾配は升一つの幅に緩む(1:bc より緩い)。
        var cutBefore = new Dictionary<int, float>();
        for (int it = 0; it < 8; it++)
        {
            bool any = false;
            for (float s = 0f; s <= L + 1e-3f; s += 0.25f)
                for (float dn = 0f; dn <= band + 0.6f + 1e-3f; dn += 0.15f)
                {
                    var q = a + al * s + inward * dn;
                    if (!EdoGeom.PIP(parcel, q)) continue;
                    float fx = (q.x - tp.x) / cell, fz = (q.y - tp.z) / cell;
                    int cx = Mathf.FloorToInt(fx) - x0, cz = Mathf.FloorToInt(fz) - z0;
                    if (cx < 0 || cz < 0 || cx + 1 >= w || cz + 1 >= h) continue;
                    float h00 = H[cz, cx], h10 = H[cz, cx + 1], h01 = H[cz + 1, cx], h11 = H[cz + 1, cx + 1];
                    // ⚠ 地形は三角形で描く ⇒ 双一次で検めると嘘が出る。四隅の最大で上から押さえる(保守側)
                    float gy = Mathf.Max(h00, Mathf.Max(h10, Mathf.Max(h01, h11))) * ts.y + tp.y;
                    if (gy <= y + 1e-3f) continue;
                    foreach (var c in new[] { new Vector2Int(cx, cz), new Vector2Int(cx + 1, cz), new Vector2Int(cx, cz + 1), new Vector2Int(cx + 1, cz + 1) })
                    {
                        var np = new Vector2(tp.x + (x0 + c.x) * cell, tp.z + (z0 + c.y) * cell);
                        if (!EdoGeom.PIP(parcel, np)) continue;
                        // ⛔ 検める帯(背から band + 0.6)より奥の節点は下げない ── 升の四隅は帯の向こう 2m まで届き、返しの石垣の向こうの面(岡部 門の内 16.50)の節点を
                        //   13.10 へ掘って、面の縁に高さ 3.4 の急な土の面を 100 余り立てた(EDO-0502 第95巡: 棟を 0.39 寄せて溝の帯が隣の升へ入った)。帯の地山は皮が設計の地盤で描く。
                        //   当たる先: CutAlongBack を呼ぶ全て(岡部の返しの溝・土井の門の背)。
                        if (Vector2.Dot(np - a, inward) > band + 0.6f + 1e-3f) continue;
                        float cur = H[c.y, c.x] * ts.y + tp.y; if (cur <= y + 1e-4f) continue;
                        int key = c.y * w + c.x; if (!cutBefore.ContainsKey(key)) cutBefore[key] = cur;
                        H[c.y, c.x] = (y - tp.y) / ts.y; any = true;
                    }
                }
            if (!any) break;
        }
        foreach (var kv in cutBefore)
        {
            int cx = kv.Key % w, cz = kv.Key / w; float now = H[cz, cx] * ts.y + tp.y;
            cutMax = Mathf.Max(cutMax, kv.Value - now); vol += (kv.Value - now) * cell * cell; n++;
        }
        if (n > 0) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        return n;
    }
}
