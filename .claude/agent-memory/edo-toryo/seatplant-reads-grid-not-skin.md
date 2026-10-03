---
name: seatplant-reads-grid-not-skin
description: SeatPlant/SeatPlantAt は既定で heightmap の格子で引く ── 縁の皮の上の木は浮き・埋まる。皮の後に EdoBuild.Drawn() を一度作って drawn に渡す
metadata:
  type: project
---

2026-10-04 EDO-0502 岡部 第6巡の検査: Stage5 の植栽 613 本中 266 本が皮の上で浮き(最大 0.44)・埋まり(−0.26)。
footProbe は全部 0 = 格子には正しく据わっていた。原因は SeatPlant の `Probe()`(SampleHeight)で、皮の升(穴)を見ない。

対処: `SeatPlant(..., drawn)` / `SeatPlantAt(..., drawn)` に `DrawnGround` を渡す(NaN の所は格子へ落とす)。
`Drawn()` は場面の全 MeshFilter を舐めるので**1 Stage に一度だけ**作る。皮(Stage3b / 山王 Stage9)の後に流すこと。
同じ型の残り: 附属屋の LevelPad 判定・坂の縁石(PlaceCurb の EdoBuild.Ground)も格子で引いている。

関連: [[contact-must-use-drawn-surface]] [[gate-float-measure-on-bed]]
