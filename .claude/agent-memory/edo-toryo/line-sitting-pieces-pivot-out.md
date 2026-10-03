---
name: line-sitting-pieces-pivot-out
description: 区画線に法肩・芯を置いた基壇と柵は float で 0.25mm・芯で半分・隅で控えが隣の辺を跨ぐ。材 null の一体駒は BodyExRoof が屋根を外せない
metadata:
  type: project
---

2026-10-03 EDO-0502 岡部の外周。囲いの実頂点を区画へ PIP すると、基壇 111/642 駒・木柵 46/46 駒・表門が外に出た。
1. 基壇の 108 駒は 0.0001〜0.00025m ── 線の上に法肩を置いた float の往復。tol=0 の RetireOutsidePoly を掛けると全部消える。
   ⭕ 測りの分解能 1mm(SEAM_TOL)を渡す。KeepInsidePoly にも tol を足した。
2. 区間の端の基壇の駒は、隅で控え(2.4s)が隣の辺を跨ぐ・0.4m の返しでは 2m の駒が辺の先へ 1.26m 突き出す。
   ⭕ 端の駒だけ駒一つ分まで走りに沿って引く(隣の辺の駒の小口が隅を塞ぐ ── P0 を3方向の光線で素通し0 を確認)。退けると隅に 2.7m の穴。
3. 柵は芯を線に置いていた(板 0.055・潜り 0.17 外)。⭕ 列ごと同じ量だけ内へ(EdoBuild.InsetRunToPoly)。端の杭は列の量を決めさせず、走りに沿って引く(隅で隣の辺 0.108)。
4. 表長屋の FBX の材が null(remap 済みでも)。一体の駒は材の名で屋根を分けるので、null だと屋根が躯体に数えられ 0.33m の偽の区画外。ForceUpdate で直る。測る前に材の null を数える。
5. 表長屋+表門は腰の出(0.97m・壁面から0.35m)が 0.051m 越え。一体の駒は凸包(EdgeCandidates)だと軒の先に隠れて見落とす。⭕ InsetRunToPoly(bandH=1.2)で一組のまま 0.06m 内へ。
6. 汀の木柵は Graded(設計面)で据えるが、辺25 の汀では設計面が描かれた地形より 0.4〜1.4m 高く 32/46 駒が浮く(内へ寄せる前から)。
関連: [[scribe-2d-and-stale-fbx-material]] [[one-mesh-part-split-by-submesh]] [[kado-arm-overruns-short-edge]]
