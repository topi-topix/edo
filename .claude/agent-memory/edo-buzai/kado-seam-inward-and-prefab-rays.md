---
name: kado-seam-inward-and-prefab-rays
description: 隅の駒の継ぎ目の小口が内向き(bisect_keep の use_fill)・棟梁の光線の検査は prefab の TRS を Blender で組めば再現できる(2026-09-27 EDO-0437 r16)
metadata:
  type: project
---

- `bisect_keep`(use_fill)が張った腕の先の小口は向きが揃わない(Kado90_H1500_a の −X の 26 面が内向き)。隣の直線の駒を縮めて据える(×0.53)と口が合わず、Unity は裏を描かないので「端面が開いている」に見える ⇒ `kado_cap_end` が平面上の面を外へ揃える。
- 棟梁の検査(q14/kado3.cs の裏当たり・t27/gapA.cs の溝)は、prefab の PrefabInstance の TRS(1001 の propertyPath)と FBX を Blender で Unity 世界座標に組み(Blender→Unity は鏡映 ⇒ 巻きを反転)、同じ向き・格子で撃てば再現した(西 8 行・最大 0.225 まで一致)。地面は見立て(前庭 14.50)で、東は合わない。scratchpad の k28/ctxrays.py・gaprays.py が型。
- 切り版の天端を切り口まで通すと、面の列の石の上の前の層を 0.17〜0.18 送る(法の楔 + 頭の丸み)。袖の天端が隅の天端より低い所(西 001f 14.30 < 14.505)では切り口の平らな面が袖の上に最大 0.2 見える。

**Why:** 単体の光線(`kado_rays_all`)では隣の頭の上から覗く穴も、縮めた隣との継ぎ目の口も出ず、前回は Unity の実測を再現できなかった。
**How to apply:** 据えた相手がある駒を焼き直すときは、prefab から近傍の TRS を抜いて組んだ上で数える。継ぎ目の小口は面の向きを数える(開いた辺が 0 でも裏向きは穴)。[[kado-cut-plane-slivers]] [[fit-end-to-rubble-heightfield]]
