---
name: hex-hogyo-and-kidan-minus-x
description: 六角の宝形は GR.tile_field に面ごとの三角を渡せば葺ける・RM.kidan の finish に "-X" を入れると −X 面が丸ごと抜ける
metadata:
  type: project
---

2026-09-26 EDO-0438(薬師堂 `yakushi6`)。

- **六角(多角形)の宝形はキットで葺ける。** `GR.tile_field([[Vj, Vj+1, 頂点]], Vj, yaw=法線+180, 0)` を 6 面回し、
  隅棟は `GR.ridge`。野地は面ごとに平面なので**三角で厳密に張る**(`hex_noji`)。⛔ `make_yosemune` は正方形しか作れない。
- ⛔ **`RM.kidan(finish=…)` に "-X" を入れない** — 仕上げは +X/+Z/−Z しか作らず、平の段積みからも外すので
  **−X の面が空く**。`do()`(既存の堂宇)が四面とも渡しているので既存の `Sanno_Do_*` も −X が抜けている疑い(未確認・呼び出し元へ申し送り)。
  ⭕ +X の仕上げを別に焼いて X 鏡 + `GR._flip_faces` で −X に据える。
- 露盤は隅棟の冠瓦の丈(0.28)を呑む丈にする。四角の 0.16 のままだと頂に暗い隙が覗く。

関連 [[sanno-do-parts-and-reuse]] [[magenta-background-finds-holes]]
