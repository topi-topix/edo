---
name: stale-matrix-world-after-location
description: GR.make_kirizuma の後に o.location を 0 にしてすぐ matrix_world で頂点を測ると、古い行列(6.8, 2.3 ずれ)のまま読まれ、瓦の谷が −1.6 と出て野地・桁が 1.6 m 落ちた
metadata:
  type: feedback
---

2026-09-15 山王の御供所(`build_sanno_gokusho.py`)で、切妻の瓦場の谷の深さを `o.matrix_world @ co` で測ったら −1.6 m と出た。
原因は `GR.make_kirizuma` が `set_origin` で location を (W/2, D/2, 0) に置いたあと、こちらで `o.location = 0` にした直後の測りで、
**`matrix_world` がまだ更新されていなかった**こと。素のメッシュで測り直すと −0.151(主屋の入母屋と同じ)。

**Why:** Blender の matrix_world は depsgraph の評価(`view_layer.update()`)まで古い値を返す。
**How to apply:** location / rotation を触った直後に world 座標で測るときは、先に `bpy.context.view_layer.update()`。
値が他の部材の実測(瓦の谷 ≈ −0.15)と桁違いなら、形を疑う前に座標系を疑う。関連 [[small-roof-tile-scale-and-panel-gaps]]
