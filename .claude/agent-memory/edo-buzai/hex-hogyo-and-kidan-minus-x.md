---
name: hex-hogyo-and-kidan-minus-x
description: 六角の宝形は GR.tile_field に面ごとの三角を渡せば葺ける・RM.kidan の −X の抜けは EDO-0445 で直した(面の光線検査つき)
metadata:
  type: project
---

2026-09-26 EDO-0438(薬師堂 `yakushi6`)。

- **六角(多角形)の宝形はキットで葺ける。** `GR.tile_field([[Vj, Vj+1, 頂点]], Vj, yaw=法線+180, 0)` を 6 面回し、
  隅棟は `GR.ridge`。野地は面ごとに平面なので**三角で厳密に張る**(`hex_noji`)。⛔ `make_yosemune` は正方形しか作れない。
- ⭕ **`RM.kidan(finish=…)` の "-X" は 2026-09-26 EDO-0445 で直した。**それまでは仕上げを +X/+Z/−Z しか作らず、
  平の段積みからも外すので −X の面が丸ごと空いていた(既存の `Sanno_Do_*`・稲荷社・向拝の礎石も同じ抜け)。
  いまは `_kidan_faces_closed` が四面を水平の光線で撃ち、1 本でも抜けたら焼かない(硬い条件)。
  ⚠ 光線を目地の面の中に通すと石と石の間を掠めて抜ける偽陽性が出る ⇒ 標本点を端数でずらす。
- 露盤は隅棟の冠瓦の丈(0.28)を呑む丈にする。四角の 0.16 のままだと頂に暗い隙が覗く。

関連 [[sanno-do-parts-and-reuse]] [[magenta-background-finds-holes]]
