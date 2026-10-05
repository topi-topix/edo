---
name: castle-batter-no-up-tris-skips-3b
description: 城の石垣(Castle Wall)の滑らかな法の帯の下の皮の点は TopRaw が NaN で CutEdgeSkin 3b の候補に入らない・外形の中で入れると背の帯を掘る
metadata:
  type: project
---

2026-10-05 EDO-0502 第23巡(岡部 門の内 TW_Kado_Shumen_0_0 × 袖の入隅の皮の三角)。

症状: 3b(見え面の前へ皮を出さない)を何度直しても三角が消えない。見え面の線の皮の点 17.39 → 前の地盤 16.94 の辺が法の前へ立つ。
原因: 3b の候補は `TopIndex.TopRaw`(上を向いた面 ny>0.7)が在る点だけ。城の石垣の見え面は ny≈0.24 で法の帯の下の点は全部 NaN
(野面は石の頭の小面が上を向くので入っていた)。さらに床の BotL は法の帯の下で法の面そのもの(殻の駒に底が無い)を返し、下げられない。
対処: 候補に「真上にその駒の見え面が在る点」(`TopIndex.UnderFace`・表の法線の水平 · WallFace > 0.3)を足し、その点の床は
その駒の `WallBottom(0.2)`。⛔ 外形の中というだけで入れると背の帯(天端も見え面も上に無い)まで 1.4m 下げ、小口の隙が 7→13 に増えた。

**How to apply:** 皮の候補・床を足すときは、帯の点の真上に何の面が在るか(天端・見え面・何も無い)を TopIndex を reflection で組んで格子で刷ってから決める(execute_code で 13 駒・数秒)。
岡部 Stage3b は 6.5〜8 分(印のファイル+txt で待つ)。関連: [[skin-edge-across-nozura-face]] [[foot-bottom-batter-and-stair-front]]
