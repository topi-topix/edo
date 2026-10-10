---
name: ramp-side-walls-unresolved-by-bake
description: 坂の両脇の石垣(between [面, 坂])は bake が「between の形が読めない」で黙って線を作らず、坂の足が壁の線の 0.05 間手前で止まって口も開かなかった
metadata:
  type: project
---
2026-10-10 EDO-0502 第102巡(岡部 東の坂 R_KiriZaka・TW_KiriZaka_N/S)。

- 症状: 指図に両脇の石垣があるのに、算出物 okabe_impl.json の terraceWalls が `line: null`・`unresolved: between の形が読めない: Higashi R_KiriZaka`。
  本線 TW_Higashi_Hokuto の gaps も [] ── 坂の芯の足 u=15.41 が壁の線(面の輪郭 u≈15.46)の手前で止まり、交わりの検めが外れた。
- 対処: sashizu_lib.tw_resolve に ramp の枝(`_tw_ramp_side`: 線 = 坂の芯 ± w/2・口 = 面の輪郭・止め = 天端 − 縦断 < ends の落差・天端は文の「口の側 Y … 約 Lm から先は Y」で mode sode)、
  build_sashizu._tw_gaps で坂の芯も石段と同じく両端 1 間延ばす(継ぎ目の重複は除く)。どちらの脇かは文が名指す棟(「蔵1 の …」)から、無ければ相方の反対。
- 罠2: 皮が坂の路盤を縦断で描くのは「石段を名指す坂(atRoute)」だけ ── 石垣で挟んだ 1.5間の坂は 2m 格子が溝を描けず路盤が 0.3〜0.7 高い。
  RampDrawnByProfile(石段を名指す坂 + kiritoshi.wall に「石垣」)で SkinGround と 3b の写しに入れた ⇒ 頭の半分は ±0.05、足の半分は +0.2〜0.55 が残る(駒の底の lo が皮を押し上げる疑い・未検)。
- 第103巡の測り: 足の半分(s1.5〜11)の皮は SkinTrace の「4 の前」で既に縦断 +0.35〜+0.86 ── 皮の設計の地盤(gh)は縦断を写しているので、上げているのは 4 より前の手(lo の押し上げ)。次は SkinTrace の点を増やして 1〜3 の手を名指す(RunAll は swap で 61 分かかった)。
- 残り: 算出物の `h` は sode の測りで lo を持たないので嘘の値(-0.03〜0.16)。

How to apply: 算出物の notes / unresolved を流す前に grep する ── 欄が増えても bake は黙って退く。関連: [[return-lost-when-sashizu-text-format-changes]]
