---
name: stair-out-of-wall-and-yat-mismatch
description: 石垣の口から下の面へ張り出す石段は段石が下の面から浮く(graded は線で段が切れ段の下の盛りを持たない)・附属屋の yAt が造成後の地盤と 0.6〜0.7m 違って埋まった
metadata:
  type: project
---

2026-10-03 EDO-0502 第4巡(岡部)。
1. K_Kuruwa(13.1→16.5・4.95m)は a が石垣の線の上・b が下の面。算出物 graded は線で 16.5→13.1 に切れるので、段石は下の面の上へ最大 1.49m 浮いた。
   `EdoBuild.StackDownToGround`(段石の下を同じ段石で接地まで積む・19 個)で浮きを消した ⇒ ⚠ 雁木の積みか盛土かは指図に無い(普請奉行の確かめ)。
2. 厩・蔵1 の `yAt` 15.5 に対し造成後の地盤(勾配の面 Higashi_Fall)は足あとで 16.00〜16.28 ── 棟が 0.78 埋まった(二棟とも同じ −0.777 は Contact の当たりがピボットの下だったため)。
   足元の中央値へ据え `EdoBuild.LevelPad` で棟の下を均した。yAt と ±0.25 を超えたら ⚠ で欄の上書きを頼む。

**Why:** どちらも指図の値をそのまま座に使って地盤を測らなかった。
**How to apply:** 石段・棟を据えたら足元を Contact で測り、指図の面の値と地盤が 0.25 を超えて違えば地盤側で据えて ⚠。関連 [[stair-position-is-terrain-dependent]] [[measure-dont-nudge]]
