---
name: kado-cut-plane-slivers
description: 焼いた隅の駒を平面で一度切ると、切り口に 1mm 未満の頂点と 0〜8mm の開いた辺が残る・継ぎ目の奥が素通しになる(2026-09-27)
metadata:
  type: project
---

隅の駒(Kado90)を bmesh.bisect_plane + holes_fill で一度切ると、書き出しの三角形割りで切り口に潰れた三角形と 0〜8mm の開いた辺が残った(H1500_b)。
切り口の平面に乗る頂点だけ 1mm で溶接 → dissolve_degenerate → 平面の開いた辺を holes_fill し直すと 0 になった(残る開いた辺は背の板 Danishi だけ = 元と同じ)。

**Why:** 石は凸包の塊が隣り合うだけなので、平面が石の頂点のすぐ脇を通ると 1mm 未満の辺ができる。検算は Blender 内の面で 0 でも FBX を読み直すと出る。
**How to apply:** 切った駒は FBX を読み直して「平面上の開いた辺」「平面上で法線が外を向かない面」を数える。make_kado は決定的(頂点の多重集合が既存 FBX と一致)なので焼き直してから切ってよい。切り口の面は石の継ぎ目が奥まで素通し ── 相手(袖の背)に当たって隠れる面にしか使わない。[[castle-wall-kiri-and-short-arm]] [[rebake-regression-by-vertex-multiset]]
