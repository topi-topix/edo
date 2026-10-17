---
name: maruta-saku-two-rail
description: 丸太の二段柵(土井 F04/F05)— 柱は wood_log_04 から(log_05 は 1.329 で根入れ込み 1.35 に足りない)・柱の −X 端は Blender +x に置く
metadata:
  type: project
---
build_maruta_saku.py(2026-10-04・EDO-0533)。在庫の丸太の長さ: log_01 3.11 / 02 3.18 / 04 2.30 / 05 1.33 / 03,06-09 は 0.73 以下。根入れ込みで 1.33 を越える柱は log_04。
**Why:** Unity X = −Blender X なので、駒の柱を Unity −X 端に立てるには Blender x=+0.909。build_maruta.py の手すりは x=−0.909 に置いて「−X 端」と書いている(Unity では +X 端の疑い・未実測)。
**How to apply:** 丸太物を足すときは log の長さ表から選び、柱の端は (-x,z,-y) で検算してから注記する。[[logical-axis-and-mirror-checks]]
