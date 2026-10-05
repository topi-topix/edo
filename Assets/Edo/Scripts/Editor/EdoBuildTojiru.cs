using System.Collections.Generic;
using UnityEngine;

// 外周の閉じを、建っている駒の実メッシュで測る(EDO-0502 第29巡・2026-10-06)
public static partial class EdoBuild
{
    /// <summary>辺 a→b の上で、建っている駒(塀・長屋・門・柵)の**実メッシュ**が覆う区間(s[m]・a からの距離)を返す(硬い・駒どうし)。
    /// 駒ごとに、躯体(屋根を除く)の頂点のうち辺の線から <paramref name="maxOff"/> 以内・駒の下端から <paramref name="yLo"/>〜<paramref name="yHi"/>
    /// の帯(目の高さ)にある頂点を辺へ射影し、その最小〜最大を一つの区間とする。⭐ 指図の s(run の s0/s1・開口の幅)で覆いを数えると、
    /// 門の柱と袖の練塀が実際には 0.7m 重なっているのに、指図の口の幅と袖の s の間の 0.11/0.17m を「切れ目」と数えた(岡部 辺41 の 0.27)。
    /// 当たる先: 外周の閉じを検める全邸(いまは岡部 ClosureQA の「実装の素通し」)。⟶ 返す: 区間 [s0, s1] の並び(重なりは呼び手が束ねる)。</summary>
    public static List<Vector2> CoverAlongEdge(Vector2 a, Vector2 b, IList<GameObject> pieces, float maxOff, float yLo, float yHi)
    {
        var res = new List<Vector2>(); var ab = b - a; float L = ab.magnitude; if (L < 1e-4f) return res;
        var dir = ab / L; var nrm = new Vector2(dir.y, -dir.x);
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            var rb = RB(g); if (rb.size == Vector3.zero) continue;
            // 外接が辺の帯に掛からない駒は測らない(頂点を読まない)
            float cs = Vector2.Dot(new Vector2(rb.center.x, rb.center.z) - a, dir), ct = Vector2.Dot(new Vector2(rb.center.x, rb.center.z) - a, nrm);
            float rad = new Vector2(rb.extents.x, rb.extents.z).magnitude;
            if (Mathf.Abs(ct) > maxOff + rad || cs < -rad || cs > L + rad) continue;
            var vs = Body(g.transform, 6000, false); if (vs.Count == 0) continue;
            float y0 = float.MaxValue; foreach (var v in vs) y0 = Mathf.Min(y0, v.y);
            float s0 = float.MaxValue, s1 = float.MinValue;
            foreach (var v in vs)
            {
                if (v.y < y0 + yLo || v.y > y0 + yHi) continue;
                var p = new Vector2(v.x, v.z) - a; if (Mathf.Abs(Vector2.Dot(p, nrm)) > maxOff) continue;
                float s = Vector2.Dot(p, dir); s0 = Mathf.Min(s0, s); s1 = Mathf.Max(s1, s);
            }
            if (s1 > s0) res.Add(new Vector2(Mathf.Max(0f, s0), Mathf.Min(L, s1)));
        }
        return res;
    }
}
