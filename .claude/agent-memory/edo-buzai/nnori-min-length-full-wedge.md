---
name: nnori-min-length-full-wedge
description: 小口を相手の法で切った野面の駒(NoriP/M)は天端の長さが 0.3·(見付+0.20) 未満だと底へ届く前に尽きる・深い見付は wall_cells の depth を渡す
metadata:
  type: project
---
2026-10-10 EDO-0502(岡部の入隅・abutOrder で後から据える側)で `okabe_nozura_nori_set.txt` の P/M × H0.30〜2.40・4.80 を焼いた。
- 法の面は天端で ls/2・下ほど 0.3 ずつ内へ入る ⇒ 長さ ls < 0.3·(h+根入れ0.20) の駒は Y = h − ls/0.3 で幅 0 になり、その下は継ぐ直線の駒の鉛直な小口が相手の法へ入る(H4.80 の L0.30 は Y 3.80 より下が空)。検算(check_nnori)はこれを捕まえない ⇒ unity_bounds の Y の下端を見る。H4.80 は 1.50〜1.80 だけ焼いた。山王の H1.80 L0.30〜0.55 はこの下限を割る(未直し)。
- make_nnori は wall_cells(v) 固定だった ⇒ h+BURY を渡さないと H2.40 超は石が DEEP で尽きる。端は cut_each_planes で石ごとに切る形へ改めた(継ぐ側の切り口は直線の駒と差 0 のまま)。
- 据える側(EdoBuildNozura の入隅の可動側)の長さの走査は 0.80→0.30 決め打ち ⇒ H4.80 を引かせるには上限を `Own.SannoNozuraNoriMaxLen` へ上げる。

**How to apply:** 法で切った端の駒を深い見付で焼く注文は、まず下限長を出してから長さの列を決める。[[nori-cut-step-and-sode]] [[nozura-deep-layout-shared-rng]]
