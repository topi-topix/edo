---
name: run-corners-seams-and-tiers
description: 石垣の run の隅は区間の端ごとに EdoBuild.PlaceRunCorners で。短い区間は芯の凹凸判定が入隅と誤る・一直線の継ぎ目の T 字・回廊の基壇の 2 段(tierPlan)は Stage3 が建てず皮が芝の土手を盛る
metadata:
  type: project
---

2026-09-25 EDO-0430(山王 本殿の西の土留めを城の石垣へ)。

1. **折れ線の途中の角も隅**: Stage3 は run の端どうしにしか隅を置かなかった。区間(`segs`)ごとに駒を分けて
   `EdoBuild.PlaceRunCorners(RunEnd[], 区間→駒, …)` に渡す。区間の端を全部渡すと、門で切れた区間の端(回廊の基壇 × 妻の土留め)にも隅が付く ── 正しい納め。
2. **短い区間(1.82m < 駒 4m)は駒が隅の外へ張り出し、`PlaceRunKado` の芯の凹凸判定が入隅と誤る**。同じ run の中の角だけは
   区間の走りで決める(convex 引数)。⚠ 別の run どうしに走りの判定を使うと御供所の郭 EK×SE が出隅に化けて隅が建った ── 芯のまま。
3. **一直線の継ぎ目(天端の段の境)に第三の run が突き当たる T 字**: 一律に隅を止めると Dan_Chu_N × Koshi_NE2 の正しい隅が消えた。
   隅の天端が一直線の相方より 0.5m 以上高い(段として見える)ときだけ試す。
4. 隅の腕が短い区間を越えて先の run(天端の高い土台)の中へ入ると、背の線が同じ線に重なり、その 1 点を「皮が天端に被る 0.027」と数える。
   見えない。部材(短い腕の隅)か数え方の話で、据えでは消えない。
5. **回廊の基壇の北東(Kairo_E s≥47・Kairo_N)の芝の楔形の土手は、指図 `tierPlan`(2 段)を Stage3 が建てていないせい**。
   一段の駒の底 25.0 の下へ皮が設計の地盤 21.7〜22.8 から盛り上げて隙を塞いでいる(浮き最大 3.3m を隠す)。`forwardPieces` の意味(前へ出す量)は
   どこにも定義が無い ── 発明せず差し戻した。

関連: [[castlewall-face-is-local-minus-x]] [[corner-piece-corridor-not-projection]] [[backfill-skin-needs-three-limits]]
