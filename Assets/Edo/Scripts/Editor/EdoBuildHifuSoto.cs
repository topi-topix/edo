using System;
using System.Collections.Generic;
using UnityEngine;

// 縁の皮の「区画の外」── 外周の石垣・土留めの見え面の前の地盤(EDO-0502 第29巡・2026-10-06)
public static partial class EdoBuild
{
    /// <summary>区画の外の点の地盤(硬い・地面)。今の地形(隣の造成)の 2m 格子を一次で引くが、**持ち主の区画 own の中か、
    /// 部材の外形の中(inPart)に落ちた節点**は造成前の地盤 baseAt に置き換える。⭐ 外周の石垣の見え面は区画の線の外へ出ており、
    /// 線の内の節点は台の天端の側(岡部 東の長屋の台で 16.4)を持つ ── 2m 格子はそれを線の外の節点(12.7)まで一次で描き、
    /// 見え面の前に高さ最大 2.9m の土の楔が 2m おきに鋸の歯に立った(岡部 IG_N40_2・N41)。
    /// ⟶ 返す: 地盤の高さ。<paramref name="replaced"/> = 置き換えた節点があったか(無ければ呼び手は地形そのもの Probe を使う)。
    /// 当たる先: 縁の皮に外周の石垣・土留めを渡す全邸(いまは岡部 Stage3b)。</summary>
    public static float OutsideOwnGround(Terrain t, float x, float z, Vector2[] own, Func<float, float, float> baseAt,
                                         Func<Vector2, bool> inPart, Dictionary<long, float> cache, out bool replaced)
    {
        var td = t.terrainData; var org = t.transform.position;
        int HR = td.heightmapResolution; float hs = td.size.x / (HR - 1);
        float fi = (x - org.x) / hs, fj = (z - org.z) / hs; int i = Mathf.FloorToInt(fi), j = Mathf.FloorToInt(fj);
        float tx = fi - i, tz = fj - j; replaced = false;
        var v = new float[4]; int n = 0;
        for (int dj = 0; dj <= 1; dj++)
            for (int di = 0; di <= 1; di++)
            {
                int ni = i + di, nj = j + dj; long k = ((long)ni << 32) ^ (uint)nj; float b;
                if (!cache.TryGetValue(k, out b))
                {
                    b = float.NaN; var q = new Vector2(org.x + ni * hs, org.z + nj * hs);
                    if ((own != null && EdoGeom.PIP(own, q)) || (inPart != null && inPart(q))) b = baseAt(q.x, q.y);
                    cache[k] = b;
                }
                if (!float.IsNaN(b)) replaced = true;
                else b = td.GetHeight(Mathf.Clamp(ni, 0, HR - 1), Mathf.Clamp(nj, 0, HR - 1)) + org.y;
                v[n++] = b;
            }
        return Mathf.Lerp(Mathf.Lerp(v[0], v[1], tx), Mathf.Lerp(v[2], v[3], tx), tz);
    }

    /// <summary>部材の外形の判定(XZ・実メッシュの凸包と外接)を作る ── OutsideOwnGround の inPart に渡す。</summary>
    public static Func<Vector2, bool> InHulls(IList<GameObject> parts)
    {
        var hs = new List<Vector2[]>(); var bs = new List<Vector4>();
        foreach (var g in parts)
        {
            if (g == null || !g.activeInHierarchy) continue;
            var h = HullOfMat(g.transform, null); if (h == null || h.Length < 3) continue;
            float a = float.MaxValue, b = float.MaxValue, c = float.MinValue, d = float.MinValue;
            foreach (var q in h) { a = Mathf.Min(a, q.x); b = Mathf.Min(b, q.y); c = Mathf.Max(c, q.x); d = Mathf.Max(d, q.y); }
            hs.Add(h); bs.Add(new Vector4(a, b, c, d));
        }
        return q =>
        {
            for (int k = 0; k < hs.Count; k++)
            {
                var bb = bs[k]; if (q.x < bb.x || q.x > bb.z || q.y < bb.y || q.y > bb.w) continue;
                if (EdoGeom.PIP(hs[k], q)) return true;
            }
            return false;
        };
    }

    /// <summary>外周の駒の足元を 2m 格子が描けているか(硬い・地面)。駒の実メッシュの外形を 0.25m で歩き、外へ 0.05m の点のうち
    /// **区画の外**の点で、今の地形(Probe)が OutsideOwnGround(区画の内と駒の下の節点を造成前に置き換えた地盤)より高い量の最大。
    /// これが皮の描きの許し(drawTol)を超える駒は、縁の皮に渡して足元を描き直す。
    /// ⟶ 返す: 最大の上がり[m](区画の外の点が無ければ 0)。<paramref name="at"/> = その点。</summary>
    public static float OutsideFootExcess(GameObject piece, Vector2[] own, Func<float, float, float> baseAt, out Vector2 at)
    {
        at = Vector2.zero; float worst = 0f;
        var h = HullOfMat(piece.transform, null); if (h == null || h.Length < 3) return 0f;
        var t = T(); var probe = Probe(); var cache = new Dictionary<long, float>();
        var inMe = InHulls(new[] { piece });
        Vector2 cen = Vector2.zero; foreach (var q in h) cen += q; cen /= h.Length;
        for (int e = 0; e < h.Length; e++)
        {
            Vector2 A = h[e], B = h[(e + 1) % h.Length], ab = B - A; float L = ab.magnitude; if (L < 1e-4f) continue;
            Vector2 tn = ab / L, nrm = new Vector2(tn.y, -tn.x);
            if (Vector2.Dot(nrm, (A + B) * 0.5f - cen) < 0) nrm = -nrm;
            int ns = Mathf.Max(1, Mathf.CeilToInt(L / 0.25f));
            for (int s = 0; s <= ns; s++)
            {
                var q = A + tn * (L * s / ns) + nrm * 0.05f;
                if (own != null && EdoGeom.PIP(own, q)) continue;
                bool rep; float g = OutsideOwnGround(t, q.x, q.y, own, baseAt, inMe, cache, out rep);
                if (!rep) continue;
                float d = probe.At(q.x, q.y) - g;
                if (d > worst) { worst = d; at = q; }
            }
        }
        return worst;
    }

    /// <summary>皮の設計 d の**区画の外の節点**を OutsideOwnGround(今の地形・区画の内と部材の下の節点は造成前)に置き換え、
    /// d.own を外す(硬い・地面)。⭐ CutEdgeSkin は区画の外の点を今の地形そのもの(2m 格子)で描くので、外周の石垣の見え面の前に
    /// 線の内の節点(台の天端の側)から引かれた土の楔が残る ── 設計の節点(1m・0.25m)で区画の外の地盤を持たせて描かせる。
    /// 区画の外は持ち主の設計(graded)を写さない(隣の区画の中は隣の造成が決める ── SkinDesign.own の趣旨はそのまま)。
    /// ⟶ 返す: 区画の外の節点の数・うち置き換えの効いた数を note へ。当たる先: 外周の石垣を皮に渡す邸(岡部 Stage3b)。</summary>
    public static int DesignOutsideOwn(SkinDesign d, IList<GameObject> parts, System.Text.StringBuilder note)
    {
        if (d == null || d.own == null || d.baseAt == null) return 0;
        var t = T(); var probe = Probe(); var cache = new Dictionary<long, float>(); var inP = InHulls(parts);
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in d.own) { mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x); mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y); }
        int outN = 0, repN = 0;
        for (int j = 0; j < d.nz; j++)
            for (int i = 0; i < d.nx; i++)
            {
                var q = new Vector2(d.x0 + i * d.step, d.z0 + j * d.step);
                bool inBox = q.x >= mnx && q.x <= mxx && q.y >= mnz && q.y <= mxz;
                if (inBox && EdoGeom.PIP(d.own, q)) continue;
                int k = j * d.nx + i; outN++;
                bool rep; float g = OutsideOwnGround(t, q.x, q.y, d.own, d.baseAt, inP, cache, out rep);
                if (rep) repN++; else g = probe.At(q.x, q.y);
                //   ⭐ 区画の外の点そのものの地盤(baseAt を点で引く)との min【硬: 盛らない】(2026-10-11 EDO-0502 第109巡)── 2m 格子の双一次は
                //   線の内の節点(造成前の三べ坂の高まり 12.2〜12.5・線から 2.5m より奥)を線の外へ引き、台の前の溝の外(道)に線から 1:1 で
                //   下る土の棚(線の外 0.45 で道 +1.5・辺41 s45〜62)を立てた。点の地盤(岡部 OutsideBase = base_dem・道の線際の均し・今の地形の min)は
                //   その楔を持たない。当たる先: DesignOutsideOwn を通す邸(いまは岡部 Stage3b)── 外の点が線の内の高い節点に引かれる所だけ下がる。
                if (!float.IsNaN(g)) { float gp = d.baseAt(q.x, q.y); if (!float.IsNaN(gp) && gp < g) g = gp; }
                d.h[k] = g; d.ok[k] = !float.IsNaN(g);
            }
        d.ownKept = d.own; d.own = null;   // 区画の外は描き終えた ── 以後 own は null(従来どおり)。区画の内だけに掛ける決まり(盛りの縁の法・平らの帯)は ownKept で見る(第92巡)
        if (note != null) note.AppendLine("  区画の外の設計の節点を区画の外の地盤へ " + outN + "(うち区画の内・駒の下の節点を造成前に置き換えた " + repN + ")");
        return repN;
    }
}
