// 植木を斜面に据える (EdoBuild の partial・2026-09-23・EDO-0401)
//
// ⭐ **何が足りなかったか**: 山王の社叢(EdoSannoShaRebuild.Stage7_Shaso)は下層の木を
//    「ピボットを点の地表の高さへ置く」だけで据えていた(⛔ 規則21 — 基準点で位置を決めない)。
//    勾配 56〜79° の崖では山側の枝葉が地中へ 1.0〜1.8m 潜り、完成の表の「埋没・浮き」が赤になった。
//    SeatOnGround(最も低い当たりを地表へ)だけでは、今度は谷側が大きく浮く。
//
// ⭕ <see cref="SeatPlant"/> — 足元の当たり(格子ごとの最下点)を**全部**地表と比べ、
//    まず一番深い当たりを地表へ(=埋没 sink)。谷側の浮きが floatMax を超えるなら、浮きが
//    floatMax になるまで下げる。そのとき山側の埋没が buryMax を超えれば**据えられない**と返す
//    (⛔ 黙って浮かせない・埋めない — 呼び手が数えて刷る)。閾値は完成の表と同じ数(規則4 の許容0)。
//
// 当たる先: 山王の社叢の下層・名指しの木(GameObject で据える木 全部)。類型の庭の NiwaField.Put は
//   同じ事を SeatOnGround+起伏の据え直し+Contact で行っている(EdoBuildNiwa.cs)。
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>植木を足元の当たりで据える。戻り値 = 埋没 ≤ <paramref name="buryMax"/> かつ 浮き ≤ <paramref name="floatMax"/>
    /// で据わったか。<paramref name="bury"/> = 最も深い当たりの埋没[m]、<paramref name="flt"/> = 最も浮いた当たりの浮き[m]。
    /// ⛔ 基準点(ピボット)の高さは使わない。当たりが測れなければ false(NaN を返す)。</summary>
    public static bool SeatPlant(GameObject go, float sink, out float bury, out float flt,
                                 float buryMax = 1.0f, float floatMax = 0.7f, int maxSamples = 60000)
    {
        bury = flt = float.NaN;
        var pts = GroundCandidates(go.transform, maxSamples);
        if (pts.Count == 0) return false;
        var probe = Probe();
        float cmin = float.MaxValue, cmax = float.MinValue;
        foreach (var p in pts)
        {
            float c = p.y - probe.At(p.x, p.z);
            if (c < cmin) cmin = c;
            if (c > cmax) cmax = c;
        }
        float dy = -sink - cmin;                          // 一番深い当たりを sink だけ潜らせる
        if (cmax + dy > floatMax) dy = floatMax - cmax;   // 谷側が浮きすぎるなら下げる
        go.transform.position += new Vector3(0f, dy, 0f);
        bury = -(cmin + dy);
        flt = cmax + dy;
        return bury <= buryMax + 1e-4f && flt <= floatMax + 1e-4f;
    }
}
