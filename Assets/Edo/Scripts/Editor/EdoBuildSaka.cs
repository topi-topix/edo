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
    {
        var res = new SakaResult { ok = false, toeMin = float.PositiveInfinity };
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
            var r = GradeSakaOnce(parcel, p2, ys, width, bf, bc, false);
            if (r.toeMin >= toeMin)
            {
                r.shift = d; r.pts = p2;
                if (write) { var w2 = GradeSakaOnce(parcel, p2, ys, width, bf, bc, true); w2.shift = d; w2.pts = p2; w2.ok = true; return w2; }
                r.ok = true; return r;
            }
            res = r; res.shift = d; res.pts = p2;
        }
        res.ok = false;
        res.note = "芯の途中を " + maxShift.ToString("F2") + "m まで寄せても法尻が区画の線から "
                 + res.toeMin.ToString("F2") + "m(< " + toeMin.ToString("F2") + ")── 地形に触らない(硬い)。塀側の土留め(1m 未満)か芯の引き直しが要る";
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
    {
        var res = new SakaResult { toeMin = float.PositiveInfinity };
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
                float nw = Mathf.Min(Mathf.Max(cur, lo), hi);
                if (Mathf.Abs(nw - cur) < 1e-4f) continue;
                res.nodes++;
                if (nw > cur)
                {
                    res.fillMax = Mathf.Max(res.fillMax, nw - cur); res.fillM3 += (nw - cur) * area;
                    if (nw - cur > 0.02f) res.toeMin = Mathf.Min(res.toeMin, DistPolyLine(parcel, p));
                }
                else { res.cutMax = Mathf.Max(res.cutMax, cur - nw); res.cutM3 += (cur - nw) * area; }
                if (write) H[iz, ix] = (nw - tp.y) / ts.y;
            }
        if (write) { td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap(); }
        return res;
    }
}
