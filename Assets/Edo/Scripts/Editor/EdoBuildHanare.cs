using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**線(塀の芯など)から壁体の面を離す**(硬い・離れの下限)。駒の壁体(屋根を除く・帯 [<paramref name="yLo"/>, <paramref name="yHi"/>]
    /// は駒の下端からの高さ)の頂点のうち、折れ線 <paramref name="line"/>(世界 xz)に最も近い点が <paramref name="clear"/> 未満なら、
    /// その点から線の最寄りの点へ向かう向きの逆へ、足りない分だけ平行移動する(線を跨いでいれば跨いだ側へは出さない ── 呼び手が刷る)。
    /// 測りは置いた駒の実メッシュ(⛔ ピボット・足形の欄で測らない)。2巡まで(動かすと最寄りの点が変わる)。
    /// 当たる先: 土井の奥の塀 Oku_Hei の「塀の芯は棟の面から 0.5間 以上」(土蔵・家中長屋)。指図の runs[].clear を持つ塀の脇の棟すべて。
    /// ⟶ 返す: 動かした量[m](合計)。<paramref name="minDist"/> = 動かした後の最も近い離れ[m]。</summary>
    public static float KeepClearOfLine(GameObject go, IList<Vector2> line, float clear, float yLo, float yHi, out float minDist)
    {
        float moved = 0f; minDist = float.NaN;
        for (int pass = 0; pass < 3; pass++)
        {
            var vs = Body(go.transform, 6000, false);
            if (vs.Count == 0) return moved;
            float y0 = float.MaxValue; foreach (var v in vs) y0 = Mathf.Min(y0, v.y);
            float best = float.MaxValue; Vector2 bp = Vector2.zero, bq = Vector2.zero;
            foreach (var v in vs)
            {
                if (v.y < y0 + yLo || v.y > y0 + yHi) continue;
                var p = new Vector2(v.x, v.z);
                for (int i = 0; i + 1 < line.Count; i++)
                {
                    Vector2 a = line[i], e = line[i + 1] - a;
                    float t = Mathf.Clamp01(Vector2.Dot(p - a, e) / Mathf.Max(1e-8f, e.sqrMagnitude));
                    var q = a + e * t; float d = Vector2.Distance(p, q);
                    if (d < best) { best = d; bp = p; bq = q; }
                }
            }
            minDist = best;
            if (best >= clear - 1e-4f || best < 1e-5f || pass == 2) return moved;
            Vector2 away = (bp - bq).normalized * (clear - best);
            go.transform.position += new Vector3(away.x, 0f, away.y);
            moved += away.magnitude;
        }
        return moved;
    }
}
