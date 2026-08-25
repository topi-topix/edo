// 純幾何ヘルパの共有置き場 (Phase 2c, 2026-08-26)
//   50ファイルに散っていた PIP / SignedArea / InwardNormal / DistToEdge / DistToPolyEdge の
//   同一実装をここへ一本化した。空白正規化後に同一と実証できたコピーだけを置換済み。
//   実装差のある版は各ファイルに据え置き(直上に注記あり)。統一は裁定待ち。
// 依存は UnityEngine の Vector2 / Mathf のみ。シーン・アセットには一切触らない。
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

    /// <summary>点 p から線分 ab への最短距離。</summary>
    public static float DistToEdge(Vector2 p, Vector2 a, Vector2 b)
    {
        var d = b - a; float len = d.magnitude; d /= len;
        float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
        return (p - (a + d * t)).magnitude;
    }

    /// <summary>点 p から多角形の外周(全辺)への最短距離。</summary>
    public static float DistToPolyEdge(Vector2[] poly, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++) m = Mathf.Min(m, DistToEdge(p, poly[i], poly[(i + 1) % poly.Length]));
        return m;
    }
}
