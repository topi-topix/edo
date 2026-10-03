---
name: run-end-at-wall-plinth-and-6e-kido
description: 中仕切の端を外周の塀へ ReachToBodies(最小)で止めると塀の腰に当たり上に口が残る。6e は動いた木戸そのものを板塀の駒と読んで消す。光線の起点が厚い駒の中だと偽の口
metadata:
  type: project
---
2026-10-03 EDO-0535 松江松平 Stage6 / 6e。

1. **症状**: NJ_Oku_S_E の端を `ReachToBodies`(帯全体の最小)で止めたら、外周の塀(16° で斜交)の腰の張り出しに当たって止まり、
   上の壁面まで走りに沿って 0.46〜0.64m の口。**対処**: 高さ 0.2m の段ごとに最初の当たりを測り、最も奥(最小+1m 以内)まで延ばす
   (`EdoMatsudairaDewaBuilder.Stage6_Zosaku` の kakoiEnd)。下は呑まれる(めり込みは数えない)。
2. **症状**: 庭木戸 NJ_Taki_Kido を開口の芯へ移したら、6e が「開口に掛かる板塀の駒」として木戸本体を非アクティブにした。
   **対処**: 6e は kind=庭木戸 の名を飛ばす(`Stage6e_TakiKido`)。Stage6 が穴を空けるので 6e は普段 0 駒。
3. 口の検めは**壁の法線方向**に、**ヤード側 3m 外から**光線を打つ。起点が石垣基壇の中だと裏面に当たり偽の 0.5〜0.75m が出た。
   `ReachToBodies` は yLo+0.1 から回るので帯を 0.05 にすると黙って NaN。

関連: [[run-end-at-opening]] [[oblique-contact-and-batter-wedge]]
