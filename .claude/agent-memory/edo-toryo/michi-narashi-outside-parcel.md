---
name: michi-narashi-outside-parcel
description: 区画の外の道の線際の帯を均すとき、Stage1 は区画の外を一切書かない・帯は外向きの片側だけで取らないと隣の辺の外を拾う(2026-10-11 EDO-0502 第104巡 三べ坂)
metadata:
  type: project
---
三べ坂(岡部 辺41)の線際の帯の均し(指図 grading.michiNarashi)を通した巡。

- 症状: 均した面を graded に入れても地形は動かない。原因: Okabe Stage1_Grade は `PIP` の外を continue(「敷地の外は一切触らない」)。
  対処: 算出物に別の欄 `michiNarashi`(0.5m 格子・帯の外 null)を焼き、Stage1 が区画の外のその帯だけ min(今の地形, 面) で下げる。
  帯の縁は最も近い格子点が null なら触らない(WGrid.At は null を飛ばして平均するので縁の外へにじむ)。
- 症状: 帯を |距離| で取ったら、辺の延長の側(区画の外だが隣の辺 0/1 の外)まで下げ、無関係の S_Hei_01 の基壇の露出が変わった。
  対処: 区画の巡り(符号付き面積)から外向きの法線を出し、片側 0〜band だけ。
- 道の地盤の測り(roadRef)を変えると base の s が変わる run がある(N41_0 0.25→0.5・N41_2 0.5→0.75)── 焼く前に旧の impl を写して base を run ごとに diff する。

**How to apply:** 区画の外の地形を触る欄が来たら、まず Stage1 が外を書くかを見る。[[grade-transfer-cliff-and-dropped-cells]]

追記(同巡): 岡部で 2b+3b だけを流し直すと RunAll の結果と変わる(TW_Higashi_Hokuto の通しの駒 × 隅で前後 1.68・皮の頂点が見え面より前 0→104 ⛔)。
2b は Stage1 が戻した地形の上で解く ⇒ 野面を触った後も RunAll(S1→S5)で流す。2b+3b だけは swap 下で 45 分掛かり RunAll(22 分)より遅かった。
腕の届く所の折れで隅の駒を選ぶ試み(K_Dan2 の上端の脇の Kado33)は Hokuto 隅 2 を 72.5→88.1° に変えて前後 1.77 の楔を作ったので戻した。
