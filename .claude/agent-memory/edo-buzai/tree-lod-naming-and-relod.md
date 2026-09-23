---
name: tree-lod-naming-and-relod
description: 木の FBX の LOD 子名は <名>_LOD0。build_tree.py を回し直すと旧6樹種51点の姿が変わる・名だけ直すなら relod_fbx.py(材質を消さないと .001 が付く)
metadata:
  type: project
---

2026-09-23 EDO-0401: `LOD_0/1/2` 綴りでは Unity が LODGroup を作らず、地形の木が Validate で全滅していた。69 点を `<名>_LOD0/1/2` + meta の lODScreenPercentages 0.80/0.60/0.04 に是正。

**Why:** build_tree.py は焼いた後も骨格の作りが進んでおり、回し直すとエノキ・常緑・ケヤキ・モミジ・ムク・ウメ 51 点の姿が変わる(クロマツ・照葉低木 18 点だけ一致)。Unity のメッシュ名と fileID は**ノード名**由来なので改名で変わり、土井邸の庭に解いた木 14 本(MeshFilter 42)を張り替えた。

**How to apply:** 焼き直し前に基準を scratchpad へ退避して読み比べる(FBX は LFS — `git show HEAD:` はポインタが出る)。読み込み→書き出しの往復はノードの 0.01 倍と軸回転を頂点へ焼き戻し、`bpy.data.materials` も毎回消す(残すと材質名に `.001` が付き remap が外れる)。関連 [[rebake-regression-by-vertex-multiset]]
