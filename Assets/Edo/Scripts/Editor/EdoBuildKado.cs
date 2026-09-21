// 隅部材(留め継ぎ)の据え — EdoBuild の partial (2026-09-21・EDO-0289 ②)
//   松江松平が持っていた「隅を犬走りへ寄せる」「腕の実端面を測る」を共通の層へ引き取った。
//   岡部は隅を区画線の上に据えたまま run だけ犬走りへ寄せていたので、隅が壁面より 0.76m 外へ張り出し、
//   腕(±4.1m)は run の端と重なっていた(2026-09-21 実測)。⛔ 邸ビルダーにこの二つを書き写さない。
//   ⭐ 使い方(順が肝): 隅を**先に**据える → KadoFace で両腕の外面を犬走りへ寄せる → KadoArm で腕の実端面を測る
//      → 辺の端の run の端を、その実端面へ突き付ける。事後に寄せる関数は持たない(docs/oki-kata.md §2)。
using System;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary><see cref="KadoFace"/> が 2 元 1 次方程式を厳密に解く下限。両辺の外向き法線の外積の絶対値
    /// (= sin 折れ角)。これ未満は面の法線方向へだけ動かす。</summary>
    const float ExactSolveDet = 0.5f;

    /// <summary>**隅部材の両腕の外面を、平行移動だけで <paramref name="target"/>(区画線から外向きへ。犬走りなら −0.30)へ据える。**
    /// 折れ点 = 辺 <paramref name="e1"/> の終点 = 辺 e1+1 の始点。<b>yaw は動かさない</b>(折れ角は部材が持つ)。
    ///
    /// <para>⭐ 腕ごとに頂点を選り分けてから測る。⛔ 全頂点の最大投影を「その辺の外面」にしない — 入隅では
    /// もう一方の腕がその向きへ余計に張り出して別の腕の面を拾い、隅が 5.9m 動いた(松平 2026-09-07)。
    /// 辺 e の腕に属する頂点 = 折れ点から見てその腕の外向きにあり、かつ相手の腕の中心線からのはみ出しが
    /// 壁厚の 1.5 倍以内の物。選り分けは動かす前の位置で**一度だけ**行う(動かした後で選び直すと発散する)。</para>
    ///
    /// <para>折れ角が 30° 以上(|det| ≥ 0.5)なら 2 元 1 次方程式が exact に解ける。それより浅い隅では解が走り方向へ
    /// 暴れるので、<b>平均の法線方向</b>へだけ動かす(部材の折れ角は辺に合わせて焼いてあるので両腕の残差は小さい)。
    /// 両腕の残差が 0.05m を超えるときは note に出す。</para>
    /// 返り値 = 動かした量(xz)。測れなければ false(note に理由)。</summary>
    public static bool KadoFace(Transform kc, Vector2[] poly, int e1, Func<int, Vector2> outNormal,
                                float target, float wallT, out Vector2 moved, out string note)
    {
        moved = Vector2.zero; note = null;
        int n = poly.Length, e2 = (e1 + 1) % n;
        Vector2 a1 = poly[e1 % n], P = poly[e2 % n], a3 = poly[(e2 + 1) % n];
        Vector2 t1 = (a1 - P).normalized, t2 = (a3 - P).normalized;
        Vector2 kn1 = outNormal(e1), kn2 = outNormal(e2);
        var body = Body(kc, 999999);        // 隅は全頂点(間引かない — 留め継ぎの先端の疎な頂点が落ちる)
        if (body.Count == 0) { note = "メッシュ無し"; return false; }
        float ky0 = 1e9f, ky1 = -1e9f;
        foreach (var v in body) { if (v.y < ky0) ky0 = v.y; if (v.y > ky1) ky1 = v.y; }
        float lo = ky0 + (ky1 - ky0) * 0.15f, hi = ky0 + (ky1 - ky0) * 0.80f;     // 壁体の帯(屋根を除く)
        float cosT = Vector2.Dot(t1, t2), armThresh = wallT * 1.5f;
        float best1 = float.MinValue, best2 = float.MinValue;
        foreach (var w in body)
        {
            if (w.y < lo || w.y > hi) continue;
            Vector2 rel = new Vector2(w.x, w.z) - P;
            float d1 = Vector2.Dot(rel, t1), d2 = Vector2.Dot(rel, t2);
            if (d1 >= 0f && Mathf.Abs(d2 - d1 * cosT) <= armThresh) best1 = Mathf.Max(best1, Vector2.Dot(rel, kn1));
            if (d2 >= 0f && Mathf.Abs(d1 - d2 * cosT) <= armThresh) best2 = Mathf.Max(best2, Vector2.Dot(rel, kn2));
        }
        if (best1 == float.MinValue || best2 == float.MinValue) { note = "両辺の壁体を判別できず"; return false; }
        float r1 = target - best1, r2 = target - best2;
        float det = kn1.x * kn2.y - kn1.y * kn2.x;
        if (Mathf.Abs(det) >= ExactSolveDet)
        {
            moved = new Vector2((r1 * kn2.y - r2 * kn1.y) / det, (kn1.x * r2 - kn2.x * r1) / det);
        }
        else
        {
            // 折れ角が浅い(30° 未満)隅は、走り方向の解が 1/det に増幅されて暴れる(岡部 P3・折れ角 14.45° で
            // 実測 7.79m 動いた)。留め継ぎの位置は壁に沿って滑らせても面は変わらないので、動かすのは**面の法線方向だけ**。
            Vector2 km = (kn1 + kn2).normalized;
            float d = 0.5f * (r1 / Mathf.Max(0.5f, Vector2.Dot(km, kn1)) + r2 / Mathf.Max(0.5f, Vector2.Dot(km, kn2)));
            moved = km * d;
            if (Mathf.Abs(r1 - r2) > 0.05f) note = "折れ角が浅い(det=" + det.ToString("F3") + ")・両腕の面が " + Mathf.Abs(r1 - r2).ToString("F2") + "m 食い違う";
        }
        if (moved.sqrMagnitude > 0.02f * 0.02f) kc.position += new Vector3(moved.x, 0f, moved.y);
        return true;
    }

    /// <summary>**据えた隅部材の「腕」が、接する二辺の s をどこまで覆っているかを実メッシュで測る。**
    /// <paramref name="h"/> = 辺 e1(隅は s=L の側)で腕が覆う下限 / <paramref name="l"/> = 辺 e1+1(隅は s=0 の側)で腕が覆う上限。
    ///
    /// <para>⛔ 指図の `armRaw` を信じない — 部材が持つ寸法で、指図に写した瞬間に食い違う
    /// (松平 2026-09-20: 宣言 4.134m に対し実部材は 3.30m で、差がそのまま外周の口になった)。
    /// 測る帯は**軒下の壁体**(隅の座 +0.6〜1.4m)。⛔ 全メッシュで測ると軒・反り・鬼が先に届いて腕が 0.9m 長く出る。
    /// 辺の壁の帯(線の外 +0.40 〜 線の内 −(|target|+壁厚+0.40))に入る頂点だけがその辺の腕の壁。
    /// ⚠ 呼ぶのは <see cref="KadoFace"/> の**後**(面を寄せてから測る)。</para></summary>
    public static bool KadoArm(Transform kc, Vector2[] poly, int e1, Func<int, Vector2> outNormal,
                               float target, float wallT, float seatDrop, out float h, out float l)
    {
        h = l = 0f;
        int n = poly.Length, e2 = (e1 + 1) % n;
        var body = Body(kc, 999999);
        if (body.Count == 0) return false;
        float y0 = 1e9f; foreach (var v in body) if (v.y < y0) y0 = v.y;
        float seat = y0 + seatDrop;                     // 隅は seat − seatDrop に据える(直線材と同じ沈め)
        float bLo = seat + 0.6f, bHi = seat + 1.4f;
        float tHi = 0.40f, tLo = -(Mathf.Abs(target) + wallT + 0.40f);
        Func<int, float[]> reach = e =>
        {
            Vector2 apex = poly[e % n];
            Vector2 u = (poly[(e + 1) % n] - apex).normalized, nn = outNormal(e);
            float mn = float.MaxValue, mx = float.MinValue;
            foreach (var w in body)
            {
                if (w.y < bLo || w.y > bHi) continue;
                float t = (w.x - apex.x) * nn.x + (w.z - apex.y) * nn.y;
                if (t < tLo || t > tHi) continue;
                float s = (w.x - apex.x) * u.x + (w.z - apex.y) * u.y;
                if (s < mn) mn = s; if (s > mx) mx = s;
            }
            return mn == float.MaxValue ? null : new float[] { mn, mx };
        };
        var r1 = reach(e1); var r2 = reach(e2);
        if (r1 == null || r2 == null) return false;
        h = r1[0]; l = r2[1];
        return true;
    }
}
