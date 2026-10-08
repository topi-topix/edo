---
name: pond-outline-and-garden-seat-traps
description: 算出物の汀線で水面を張ると縁が宙に浮く・作業場で張った水面は作業場シーンにしか居ない・JG の黒松を拡大すると平地でも SeatPlant が埋没で退ける・退けた Niwa の下で SeatOnGround が投げる
metadata:
  type: project
---

2026-10-08 EDO-0502 第59巡(岡部 書院の泉水を初めて建てた)。

1. 汀線(impl gardens の 汀線(平滑後))の上で描かれた地表が水面より最大 0.56 低く、557 点のうち 273 で水面の縁が宙に浮いた。
   原因: 石組の岸の断面(niwa_y)と 2m 格子で、設計の地盤そのものが汀線で 20.45〜20.7(水面 20.7)。汀線は狙いでしかない。
   対処: PlaceWaterSurface で汀線を 0.5m に割り、外向きの法線に沿って描かれた地表が水面+0.02 に届く所まで出す(上限 2.0m)。
   残り: 橋の掛かるくびれ 8 点は 2m 出しても届かない(-0.60)。
2. PlaceWaterSurface は場面の root "Water" の下に置く ⇒ 作業場(Koba)で流すと水面は Koba.unity にしか居ず、赤坂へは追従しない(プレハブの外)。
   流した巡は報告に必ず書く(赤坂で Stage4 を流し直すか、水面を運ぶ手が要る)。RebuildSurface は流すたびに `_mesh N.asset` を足す(孤児)。
3. JG.Pine(FreeJapaneseGarden の黒松)を丈 1.65 倍にすると、平地でも SeatPlant の埋没 1.01〜1.20 > 1.0 で退ける
   (根の帯 ROOT_TOUCH の最も浮いた根を地表へ下ろす規則で、反り上がった根の先を合わせて根元が沈む)。主木 7 本が建たなかった。EdoBuild 側の型。
4. RetireStaleGroup が前の巡で Niwa を非活性にしていると、Stage4 の SeatOnGround が「測れる頂点が無い」で投げる ⇒ Stage4 の頭で群を起こした。

**How to apply:** 池を張る邸(土井・松江松平)でも汀の地表−水面を 0.1m おきに測ってから合格と言う。作業場で庭を流したら水面の居場所を報告する。
大きく拡大する庭木は先に平地で PlantAtPoint を試し、bury を見る。関連 [[retired-group-makes-children-unmeasurable]] [[pond-carved-but-water-lost]] [[skin-after-garden-fills-pond]]
