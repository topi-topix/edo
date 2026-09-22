// 純幾何ヘルパの共有置き場 (Phase 2c, 2026-08-26)
//   50ファイルに散っていた PIP / SignedArea / InwardNormal / DistToEdge / DistToPolyEdge の
//   同一実装をここへ一本化した。空白正規化後に同一と実証できたコピーだけを置換済み。
//   実装差のある版は各ファイルに据え置き(直上に注記あり)。統一は裁定待ち。
// 依存は UnityEngine の Vector2 / Mathf のみ。シーン・アセットには一切触らない。
using System;
using UnityEngine;

public static class EdoGeom
{
    /// <summary>point-in-polygon (偶奇則)。poly は XZ 平面の頂点列(向き不問・非閉路)。</summary>
    public static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) inside = !inside;
        return inside;
    }

    /// <summary>符号付き面積。CCW で正。</summary>
    public static float SignedArea(Vector2[] poly)
    {
        float a = 0;
        for (int i = 0; i < poly.Length; i++) { var p = poly[i]; var q = poly[(i + 1) % poly.Length]; a += p.x * q.y - q.x * p.y; }
        return 0.5f * a;
    }

    /// <summary>辺 i (poly[i]→poly[i+1]) の、多角形の内側を向く単位法線。</summary>
    public static Vector2 InwardNormal(Vector2[] poly, int i)
    {
        var a = poly[i]; var b = poly[(i + 1) % poly.Length];
        var d = (b - a).normalized;
        var n = new Vector2(-d.y, d.x);
        if (SignedArea(poly) < 0) n = -n;
        return n;
    }

    /// <summary>点 p から線分 ab への最短距離。
    /// ⚠ **長さ0の線分では NaN を返してはいけない。**`parcels.json` には頂点が重複した区画があり
    /// (山王門前の一筆など)、`d /= len` が (NaN,NaN) になって距離が NaN に化けていた。
    /// NaN は比較が全部 false なので `Mathf.Min(m, NaN)` は **NaN** を返し、以後 m は最小値ではなく
    /// 「その次の辺までの距離」になる — 区画の縁に載っている駒が「外へ 10.28m」と出た
    /// (2026-09-21・類型の8区画の赤の主因)。長さ0なら端点までの距離を返す。</summary>
    public static float DistToEdge(Vector2 p, Vector2 a, Vector2 b)
    {
        var d = b - a; float len = d.magnitude;
        if (len < 1e-6f) return (p - a).magnitude;      // 長さ0の辺(頂点の重複)
        d /= len;
        float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
        return (p - (a + d * t)).magnitude;
    }

    /// <summary>点 p から多角形の外周(全辺)への最短距離。
    /// ⛔ NaN を混ぜない — 混ざると最小値でなくなる(<see cref="DistToEdge"/> の注)。</summary>
    public static float DistToPolyEdge(Vector2[] poly, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            float e = DistToEdge(p, poly[i], poly[(i + 1) % poly.Length]);
            if (!float.IsNaN(e) && e < m) m = e;
        }
        return m;
    }

    /// <summary>点集合の凸包の頂点インデックス(反時計回り・共線点は落とす)。
    /// 凸包の**外**の頂点は、定義上どの向きへ投影しても凸包上のいずれかの頂点以下にしかならない —
    /// つまり「どの向きの端(最小/最大)になり得るか」を過不足なく絞り込める、間引きではなく正確な絞り込み。
    /// <c>EdoBuild</c> の境界系(区域侵犯 <c>OutsideBy</c>・軸方向の伸び <c>EdgeAlong</c>/<c>LocalSpan</c>/
    /// <c>StretchEnd</c>)が、一様な添字間引きで極値の頂点を落として区域侵犯を見逃す危険を消すために使う
    /// (EDO-0383)。3点未満ならそのまま全indexを返す。</summary>
    public static int[] HullXZ(Vector2[] pts)
    {
        int n = pts.Length;
        if (n < 3) { var all = new int[n]; for (int i = 0; i < n; i++) all[i] = i; return all; }
        var order = new int[n];
        for (int i = 0; i < n; i++) order[i] = i;
        Array.Sort(order, (a, b) => pts[a].x != pts[b].x ? pts[a].x.CompareTo(pts[b].x) : pts[a].y.CompareTo(pts[b].y));
        var hull = new int[2 * n];
        int k = 0;
        for (int i = 0; i < n; i++)
        {
            while (k >= 2 && HullCross(pts[hull[k - 2]], pts[hull[k - 1]], pts[order[i]]) <= 0f) k--;
            hull[k++] = order[i];
        }
        int lower = k + 1;
        for (int i = n - 2; i >= 0; i--)
        {
            while (k >= lower && HullCross(pts[hull[k - 2]], pts[hull[k - 1]], pts[order[i]]) <= 0f) k--;
            hull[k++] = order[i];
        }
        var result = new int[k - 1];
        Array.Copy(hull, result, k - 1);
        return result;
    }
    static float HullCross(Vector2 o, Vector2 a, Vector2 b)
    {
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
    }
}
