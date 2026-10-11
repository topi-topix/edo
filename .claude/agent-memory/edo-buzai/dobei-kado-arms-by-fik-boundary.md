---
name: dobei-kado-arms-by-fik-boundary
description: 練塀の短い腕の名は隅の外面の内寄せ fiK で割れる(岡部 P3/P4 は fiK 0.52 が境)── KadoArms を python で写し、幅の両側の名を焼く(2026-10-11 EDO-0502)
metadata:
  type: project
---
- 腕は `EdoBuild.KadoArms` が 0.05 刻みで選び、入力は fiK = max(両辺の FaceIn) = 法肩の控え c + 犬走り(実行時に据えた基壇から測る)。棟梁の探した名(P3 30x55)と普請方の見込み(40x60)は fiK が 1.0 と 0.55 で違うだけ。
- python で KadoArms を写して fiK を走査すると名の境が出る(岡部 P2〜P4: 0.42 / 0.52 / 0.64 / 0.91 / 0.97)。見込み ±0.05 が境を跨ぐなら両側を焼く。写しは scratchpad の r107kado/arms.py(parcels.json + impl.corners)。
- 切り駒 Dobei_Kiri は隅の腕が無い端の代わりで、隅が据われば引かれない(cornerEnd)。「隅も切り駒も無い」と言われたら隅だけ焼けば足りる。

**How to apply:** 基壇・犬走りを動かした巡の後は、名を棟梁の旧い ★ 行から取らず fiK の幅で表を出してから焼く。[[dobei-kado-short-arms]] [[dobei-kado-batch-meta-clone]]
