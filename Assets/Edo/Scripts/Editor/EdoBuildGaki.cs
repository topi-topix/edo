using System;
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>**垣・柵の一辺を1間の駒で敷く**(四つ目垣・建仁寺垣・丸太の二段柵 ── 1間の駒+端柱の型)。
    /// 駒はピボットがスパンの中心・地盤レベル・局所 +X が走り。端数は**端の駒を辺の端に合わせ、内側の継ぎ目で重ねて吸う**
    /// (⛔ 等ピッチの中央寄せは端の駒が辺の外へ出る)。辺の +X 端(B)に端柱を1本。
    /// ⛔ <c>SeatBottom</c> で据えない(根入れ 0.150 のぶん浮く)── 足元の地盤 <paramref name="ground"/>(x,z) を直に入れる。
    /// 柔らかい条件: 一駒の両の足の地盤の差 ≤ <paramref name="slopeTol"/>(斜面の途中に立てない)── 超えた駒は数えて返す(⚠)。
    /// 当たる先: 土井の S6(F04/F05/F07/F09/F11)・岡部/土井の旧 LayGaki(EdoDoiBuilder.LayGaki は廃止の順で寄せる)。
    /// ⟶ 返す: 置いた駒(端柱を含む)。<paramref name="onSlope"/> = 足の地盤の差が超えた駒の数、<paramref name="worstStep"/> = その最大[m]。</summary>
    public static List<GameObject> GakiRun(Transform parent, Vector2 A, Vector2 B, string spanPath, string postPath,
                                           string prefix, Func<float, float, float> ground, float slopeTol,
                                           out int onSlope, out float worstStep)
    {
        const float SPAN = 1.818f;
        var made = new List<GameObject>(); onSlope = 0; worstStep = 0f;
        float len = Vector2.Distance(A, B);
        if (len < 0.05f) return made;
        Vector2 dir = (B - A) / len;
        float yaw = Mathf.Atan2(-dir.y, dir.x) * Mathf.Rad2Deg;   // 局所 +X を dir へ
        int k = Mathf.Max(1, Mathf.RoundToInt(len / SPAN));
        if (k * SPAN < len - 0.02f) k++;
        for (int q = 0; q < k; q++)
        {
            float a = (k == 1) ? (len - SPAN) * 0.5f : (len - SPAN) * q / (float)(k - 1);
            Vector2 c = A + dir * (a + SPAN * 0.5f);
            Vector2 f0 = A + dir * a, f1 = A + dir * (a + SPAN);
            float g0 = ground(f0.x, f0.y), g1 = ground(f1.x, f1.y), gc = ground(c.x, c.y);
            float step = Mathf.Abs(g1 - g0);
            if (step > slopeTol) { onSlope++; worstStep = Mathf.Max(worstStep, step); }
            var go = Place(spanPath, new Vector3(c.x, Mathf.Min(gc, Mathf.Min(g0, g1)), c.y), yaw, Vector3.one, parent, prefix + "_" + q);
            if (go != null) made.Add(go);
        }
        if (!string.IsNullOrEmpty(postPath))
        {
            var go = Place(postPath, new Vector3(B.x, ground(B.x, B.y), B.y), yaw, Vector3.one, parent, prefix + "_Post");
            if (go != null) made.Add(go);
        }
        return made;
    }
}
