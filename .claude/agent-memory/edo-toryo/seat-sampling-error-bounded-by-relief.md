---
name: seat-sampling-error-bounded-by-relief
description: 間引いた接地(SeatOnGround の maxSamples)は埋没方向にしか外れず、嘘の上限は足元の起伏。だから起伏で選んで細かく据え直せる
metadata:
  type: project
---

**症状**(2026-09-22 EDO-0323): 急斜面の区画で庭木が本当に埋没する(三べ坂阿部の屋敷林 −1.67m・
渡辺の常緑中木 −1.15m)。据えたのは `SeatOnGround` なのに埋まる。

**原因**: `SeatOnGround(go, sink, 600)` の **600 点の間引き**が、真の接地箇所(斜面の**上手側**の
根元の頂点)を拾い損ねる。頂点が数万ある木は間引きで根元が消えやすい。

**効く性質(ここが非自明)**: 間引いた測りは真の最小より**必ず大きい**側にしか外れない
= 駒は**沈む側にしか外れない**(浮く側へは外れない)。そして沈み量の上限は
**駒の足元の地形の起伏**。だから:

- 起伏 ≤ 閾値 の駒は**測り直す必要がない**(埋没も浮きも起こりえない)
- 起伏が大きい駒だけ間引かずに据え直せばよい(`SeatOnGround(go, sink, 60000)`)。
  平らな区画では一度も通らないので再生成は重くならない
- 起伏は `Ground`(SampleHeight)で引く。⛔ `GroundGrid` は 2m 格子で ±(1m×勾配) の嘘が乗る
  → [[contact-must-use-drawn-surface]]
- ⚠ 起伏を四隅+中央の5点でしか測らないので、閾値には余裕を取る(1.0 でなく 0.5)

**この型が当たる先**: 庭木だけでなく**斜面に据える全部** — 三べ坂・山王の斜面、石段、景石、
囲いの駒、町屋。`EdoBuild` の `SeatOnGround` を粗い maxSamples で呼んでいる呼び手すべて。
実装は `EdoBuildNiwa.cs` の `NiwaField.Put` / `ReliefUnder`。

⛔ 据え直しが効くと Stage6 の「埋没」は 0 になる — **0 を合格と読まない**。刷るのは
「据え直した駒の数」と「それでも据わらなかった駒の数と最悪値」の両方(規則19)。

関連: [[measure-dont-nudge]] / [[mesh-atari-is-lower-than-paper.md]]
