---
name: terrain-detail-array-dims-lie
description: Unity 6000.5 の GetDetailLayer/GetHoles は中身が [y,x] 行優先なのに寸法を [w,h] と名乗る。正方でない範囲は平らに読み直す
metadata:
  type: project
---

**症状**(2026-09-23・山王の井戸 EDO-0274): 4×5 セルの detail を `GetDetailLayer(x0,y0,w,h,l)` で読み
`d[j,i]` で引くと IndexOutOfRange。`d[x,y]` とも `d[y,x]` とも一致しない(40×30 で 379/1200・466/1200)。

**原因**: 返る配列は GetLength(0)=w と名乗るが、中身は [y,x] の行優先。平らに並べた k 番目が
(x0 + k % w, y0 + k / w)(1200/1200 一致)。正方の範囲や全面の読みでは気付かない。`GetHoles` も寸法が同じ癖。

**対処**: `EdoBuildSueru.cs` の `DetailBlock` / `HolesBlock` で平らに読み直して [h,w] に組み、それを
`SetDetailLayer`/`SetHoles` へ渡す(往復で全面の差 0 を実測済み)。⛔ 返った配列をそのまま添字で引かない・
そのまま Set に戻さない(正方でない範囲では別のセルを書く)。

関連: 地形の holes は高さの格子と同じ 2.0m 角。井戸の口(内径 0.91)でも 2m 抜けるので、口の外が駒で覆われて
いるかを `CutHole` が検める。holes を一つでも抜くと TerrainData に holes の面が載り、`ModernTerrain.asset` が
21.3MB → 25.5MB に太った(LFS)。
