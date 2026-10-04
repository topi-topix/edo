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

    /// <summary>**線の端を相手の面へ突き付ける**(塀の端 → 廊下・棟の側面)。線の最後の区間 <paramref name="inner"/>→<paramref name="end"/>
    /// の向き d に沿い、<paramref name="inner"/> から相手 <paramref name="target"/> の実メッシュ(屋根を除く)の三角形へ水平な光線を打ち
    /// (高さ帯 [<paramref name="yLo"/>, <paramref name="yHi"/>] は世界の Y・横は ±<paramref name="halfW"/>・<see cref="ReachToBodies"/>)、最初に触れる所へ端を動かす
    /// (= 触れている箇所を測る・⛔ 相手のピボットや指図の座標で決めない)。硬い条件: 隙 0。
    /// 当たる先: 土井の奥の塀 Oku_Hei / Oku_Hei_Roka の端(廊下 L_HiromaOku の側面・runs[].ends)。指図の runs[].ends に面を名指す塀すべて。
    /// ⟶ 返す: 新しい端(世界 xz)。測れなければ <paramref name="end"/> のまま・<paramref name="shift"/> = NaN。shift は d 向きの移動量[m]。</summary>
    public static Vector2 EndToFace(Vector2 inner, Vector2 end, GameObject target, float yLo, float yHi, float halfW, out float shift)
    {
        shift = float.NaN;
        if (target == null) return end;
        // ⭐ 面で測る(ReachToBodies = 三角形への光線)。⛔ 頂点の窓で採らない ── 廊下の側桁・高欄・柱は低ポリで
        //   頂点が端にしか無く、塀の線の前の帯は空だった(2026-10-04 EDO-0533「点なし」)。
        Vector2 d = (end - inner).normalized;
        float reach = Vector2.Distance(inner, end) + 1.5f;
        float hit = ReachToBodies(inner, d, new[] { target }, halfW, yLo, yHi, reach);
        if (float.IsNaN(hit)) return end;
        var ne = inner + d * hit;
        shift = Vector2.Dot(ne - end, d);
        return ne;
    }
}
