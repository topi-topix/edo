---
name: nozura-tome-two-kado
description: 野面の積み止めの駒は Kado90 を二つ小口で突き合わせて作る(腕の先どうしは直線の継ぎ目と同じに合う)・H2400 の端の石に裏面 3 本は G0/Kado90 から継いだ既存の欠陥
metadata:
  type: project
---
2026-10-07 EDO-0502(岡部 nozuraEndRule 2026-10-07b)で `Sanno_Nozura_H{0600,1200,2400}_Tome{P,M}_{a,b}` を焼いた(`build_sanno_nozura.py -- tome`)。
- 新しい割りは書かず、make_kado を二度回して頂点を python に写し(reset が全部消す)、前の角 yaw 0/−90・奥の角 yaw 90/180 を (0,0,−1.818) に起こし直して join。腕の先の切り口は直線の駒の B+/B− と同じなので小口の面の中の継ぎ目も一石に合う ⇒ 小口の奥行は 1.818(半間×2)に縛られる(G0 の天端の奥 1.04 より 0.77 背へ出る・背土に埋まる)。
- H2400 は表・小口に裏面の当たり 1〜3 本(深さ 1.72・継ぎ目から 0.085 の端の石)── 既存の G0/Kado90 H2400 にも同じ所に在る(端の石の型の欠陥)。

**How to apply:** 小口の奥行を詰める注文が来たら、継ぎ目のずれ(竪目地が通る)と引き換えになる。H2400 の端の石を直すなら G0・Kado90 ごと焼き直し。[[nozura-kado-sigma-fold]] [[nozura-end-caps-per-stone]]
