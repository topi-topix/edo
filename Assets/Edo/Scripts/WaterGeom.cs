using System.Collections.Generic;
using UnityEngine;

/// <summary>水域の多角形処理（平滑化・三角形化・内外判定）。WaterBaker/トレーサーで共有。</summary>
public static class WaterGeom
{
    public static float SignedArea(List<Vector2> p)
    {
        float a = 0f;
        for (int i = 0; i < p.Count; i++) { Vector2 u = p[i], v = p[(i + 1) % p.Count]; a += u.x * v.y - v.x * u.y; }
        return a * 0.5f;
    }

    public static bool PointInPoly(Vector2 pt, List<Vector2> poly)
    {
        bool inside = false; int n = poly.Count;
        for (int i = 0, j = n - 1; i < n; j = i++)
            if (((poly[i].y > pt.y) != (poly[j].y > pt.y)) &&
                (pt.x < (poly[j].x - poly[i].x) * (pt.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x))
                inside = !inside;
        return inside;
    }

    public static List<Vector3> Chaikin(List<Vector3> p, int iters)
    {
        var cur = new List<Vector3>(p);
        for (int it = 0; it < iters; it++)
        {
            var nxt = new List<Vector3>(); int n = cur.Count;
            for (int i = 0; i < n; i++)
            {
                Vector3 a = cur[i], b = cur[(i + 1) % n];
                nxt.Add(Vector3.Lerp(a, b, 0.25f));
                nxt.Add(Vector3.Lerp(a, b, 0.75f));
            }
            cur = nxt;
        }
        return cur;
    }

    /// <summary>
    /// 頂点ごとに「角(sharp=true)を残す / 丸める(false)」を切り替えられる平滑化。
    /// smooth 頂点は隣接辺の 25% 位置に丸め（＝Chaikin と同一）、sharp 頂点はその点を厳密に残す（直角）。
    /// sharp が null/短い場合は該当頂点を smooth 扱い → 全点 smooth のときは Chaikin と完全一致。
    /// </summary>
    public static List<Vector3> SmoothTagged(List<Vector3> p, List<bool> sharp, int iters)
    {
        var cur = new List<Vector3>(p);
        var tag = new List<bool>(p.Count);
        for (int i = 0; i < p.Count; i++) tag.Add(sharp != null && i < sharp.Count && sharp[i]);
        for (int it = 0; it < iters; it++)
        {
            var nxt = new List<Vector3>(); var ntag = new List<bool>(); int n = cur.Count;
            for (int i = 0; i < n; i++)
            {
                Vector3 a = cur[i], prev = cur[(i - 1 + n) % n], b = cur[(i + 1) % n];
                if (tag[i]) { nxt.Add(a); ntag.Add(true); }            // 角: そのまま残す（直角）
                else
                {
                    nxt.Add(Vector3.Lerp(a, prev, 0.25f)); ntag.Add(false);
                    nxt.Add(Vector3.Lerp(a, b, 0.25f)); ntag.Add(false);
                }
            }
            cur = nxt; tag = ntag;
        }
        return cur;
    }

    public static List<int> EarClip(List<Vector2> poly)
    {
        var tris = new List<int>(); int n = poly.Count;
        if (n < 3) return tris;
        var idx = new List<int>(); for (int i = 0; i < n; i++) idx.Add(i);
        int guard = 0;
        while (idx.Count > 3 && guard++ < 20000)
        {
            bool clipped = false;
            for (int i = 0; i < idx.Count; i++)
            {
                int i0 = idx[(i - 1 + idx.Count) % idx.Count], i1 = idx[i], i2 = idx[(i + 1) % idx.Count];
                Vector2 a = poly[i0], b = poly[i1], c = poly[i2];
                if (Cross(b - a, c - a) <= 0f) continue;
                bool ear = true;
                for (int k = 0; k < idx.Count; k++)
                {
                    int pI = idx[k];
                    if (pI == i0 || pI == i1 || pI == i2) continue;
                    if (InTri(poly[pI], a, b, c)) { ear = false; break; }
                }
                if (ear) { tris.Add(i0); tris.Add(i1); tris.Add(i2); idx.RemoveAt(i); clipped = true; break; }
            }
            if (!clipped) break;
        }
        if (idx.Count == 3) { tris.Add(idx[0]); tris.Add(idx[1]); tris.Add(idx[2]); }
        return tris;
    }

    static float Cross(Vector2 a, Vector2 b) { return a.x * b.y - a.y * b.x; }
    static bool InTri(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
    {
        float d1 = Cross(b - a, p - a), d2 = Cross(c - b, p - b), d3 = Cross(a - c, p - c);
        bool neg = (d1 < 0) || (d2 < 0) || (d3 < 0);
        bool pos = (d1 > 0) || (d2 > 0) || (d3 > 0);
        return !(neg && pos);
    }
}
