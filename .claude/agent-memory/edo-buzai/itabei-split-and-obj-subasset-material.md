---
name: itabei-split-and-obj-subasset-material
description: 在庫の板塀 itabei5 は itabei.obj の1スパン×5(ピッチ素寸0.82023)。分けて焼くと材 itabei は .obj のサブアセットにしか無く、フォルダの remap では当たらない
metadata:
  type: project
---

2026-09-26・EDO-0437 で板塀を「板1間 `Own.ItabeiIta`」「柱1本 `Own.ItabeiHashira`」に分けた(`build_itabei_bunkatsu.py`)。

- `itabei5.obj` は `itabei.obj`(g hei + g pole)の 121 頂点をピッチ 0.82023 で 5 つ並べた物。柱は各スパンの **obj −X 端**
  (Unity では +X 端)に 1本ずつで、**5本目の先(端)に柱は無い**。分けるときは 1スパンの obj から切れば済む。
- 部品は loose part で 13 個: 根元の台(y<0.06)・柱身(幅<0.1・丈>1)・残り 11 が板(貫3・羽目板7・笠木)。
- 検算は「板+柱を組み直して元の1スパンと頂点の多重集合が一致」(欠け0/余り0)。[[rebake-regression-by-vertex-multiset]]
- ⚠ 材 `itabei` は edogoyomi の .obj が抱えるサブアセットだけ ⇒ `EdoRemapMat.ByFolder` では当たらない。
  `RemapSannoShinzo` に `Eg.Itabei5` の `LoadAllAssetsAtPath` を借り先として足した。**別の邸で使うなら同じ足しが要る。**
- obj 取り込みは Blender 既定(forward −Z / up Y)+ vklib.export_fbx で、Unity の .obj 直読みと同じ向きになる。
