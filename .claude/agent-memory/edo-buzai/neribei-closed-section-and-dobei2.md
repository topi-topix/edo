---
name: neribei-closed-section-and-dobei2
description: 練塀を一つの閉じた断面で焼き直した時の罠(押縁の隙・切り口の板の小口・瓦場の継ぎ目の割れ・光線の内側判定)と Dobei2m の系(2026-10-12 EDO-0502)
metadata:
  type: project
---
2026-10-12 施主裁定「案1」で build_neribei.py(Neribei_*)、追加指示で build_dobei2.py(Dobei2_* 端・切り・隅)を起こした。

- 厚くした s_hei の下見板は押縁の脇に細い隙があり、背景が点で抜ける ⇒ 板の裏に外向きの裏打ち `shin` を張る。切り口の断面は板の表(0.206)まで取る(漆喰の 0.20 で切ると縦の白い筋)。
- Dobei2m の slab は面ごとに頂点を溶接しないので、切り口は holes_fill で塞げない ⇒ 作図の値で断面を貼る。roof 2x2 の瓦場は枚の境で軒の鼻が突き付けになり見上げで割れる ⇒ 駒の中に枚の境を作らない(始めを x0 へ)。留めの線にも面の中の板を立てる。
- 組み姿の光線は「最初に当たった面が裏 = 他の駒の中から撃った」を別に数えないと入隅で偽の抜けが出る。周期は s_hei 瓦 P/14・板と垂木 P/8・束 P/2。Dobei2m は 2.004 にしか周期が無い。

**How to apply:** 練塀・土塀の新しい駒はこの二本の生成器へ足す(s_hei の組で焼かない)。[[dobei-pair-kado-arms-single-sheet]] [[magenta-background-finds-holes]]
