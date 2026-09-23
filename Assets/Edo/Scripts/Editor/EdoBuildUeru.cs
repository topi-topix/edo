// 植木を斜面に据える (EdoBuild の partial・2026-09-23・EDO-0401)
//
// ⭐ **何が足りなかったか**: 山王の社叢(EdoSannoShaRebuild.Stage7_Shaso)は下層の木を
//    「ピボットを点の地表の高さへ置く」だけで据えていた(⛔ 規則21 — 基準点で位置を決めない)。
//    勾配 56〜79° の崖では山側の枝葉が地中へ 1.0〜1.8m 潜り、完成の表の「埋没・浮き」が赤になった。
//
// ⛔ **初版の誤り(c68f7959・同日に流して判明)**: 「当たりの浮き」を**全部の当たりの最大**で数え、
//    それを 0.7 に抑えるため木ごと下げていた。斜面では谷側の樹冠の下は地面から何mも離れているのが
//    当たり前で(浮きではない)、下げた結果 名指しの木 20 本が 14.8〜20.9m・下層 759/870 本が埋まった。
//    浮き・埋没は完成の表(GroundQA / Contact)と同じく**最も低い当たり1つ**の隙で数える
//    (docs/oki-kata.md §3・§4)。谷側の樹冠と地面の間は測らない。
//
// ⭕ <see cref="SeatPlant"/> — 触れている箇所は2種ある:
//    ・**根元**(局所の上向きで最も低い帯 = 幹の足・根張り)── これを地表へ着ける
//    ・**枝葉の当たり**(格子ごとの最下点・EdoBuild.GroundCandidates)── 斜面の山側では根元より先に地面へ当たる
//    1) 根元の最も低い当たりを地表へ(sink だけ潜らせる)。
//    2) 山側の枝葉の埋没が buryMax を超えるなら、超えた分だけ持ち上げる(根元はその分浮く)。
//    3) 根元の浮き(根元の当たりの最小の隙)が floatMax を超えれば**据えられない**と返す
//       (⛔ 黙って浮かせない・埋めない — 呼び手が数えて刷る)。閾値は完成の表と同じ数(規則4 の許容0)。
//    〔硬い制約〕埋没 ≤ buryMax・根元の浮き ≤ floatMax。据わらない木は置いたうえで名指しする。
//
// 当たる先: SeatPlant を呼ぶ所すべて(今は山王の社叢の下層と名指しの木 = Stage7_Shaso だけ)。
//   類型の庭の NiwaField.Put は SeatOnGround+起伏の据え直し+Contact で据えていて、同じ「谷側の樹冠を
//   浮きと数える」誤りは持たない(最小の隙で数えている)。
using System.Collections.Generic;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>植木を足元の当たりで据える。戻り値 = 埋没 ≤ <paramref name="buryMax"/> かつ 根元の浮き ≤ <paramref name="floatMax"/>
    /// で据わったか。<paramref name="bury"/> = 最も深い当たり(枝葉を含む)の埋没[m]、<paramref name="flt"/> = 根元の浮き[m]
    /// (根元の当たりのうち最も地面に近い所の隙。負なら根元は地中)。
    /// 根元 = 局所の上向き(transform.up)で最も低い当たりから <paramref name="footBand"/> 以内の当たり。
    /// ⛔ 基準点(ピボット)の高さは使わない。⛔ 谷側の樹冠の下の隙を浮きと数えない。当たりが測れなければ false(NaN を返す)。</summary>
    public static bool SeatPlant(GameObject go, float sink, out float bury, out float flt,
                                 float buryMax = 1.0f, float floatMax = 0.7f, float footBand = 0.3f,
                                 int maxSamples = 60000)
    {
        bury = flt = float.NaN;
        var pts = GroundCandidates(go.transform, maxSamples);
        if (pts.Count == 0) return false;
        var probe = Probe();
        Vector3 up = go.transform.up;
        float hmin = float.MaxValue;
        foreach (var p in pts) hmin = Mathf.Min(hmin, Vector3.Dot(p, up));
        float cmin = float.MaxValue, fmin = float.MaxValue;   // 全部の当たりの最小の隙 / 根元の当たりの最小の隙
        foreach (var p in pts)
        {
            float c = p.y - probe.At(p.x, p.z);
            if (c < cmin) cmin = c;
            if (Vector3.Dot(p, up) <= hmin + footBand && c < fmin) fmin = c;
        }
        float dy = -sink - fmin;                          // 1) 根元を地表へ
        if (-(cmin + dy) > buryMax) dy = -buryMax - cmin; // 2) 山側の枝葉が埋まりすぎるなら持ち上げる
        go.transform.position += new Vector3(0f, dy, 0f);
        bury = Mathf.Max(0f, -(cmin + dy));
        flt = fmin + dy;
        return bury <= buryMax + 1e-4f && flt <= floatMax + 1e-4f;
    }
}
