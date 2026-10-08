---
name: scaled-tree-lod-and-branch-tip-seat
description: 拡大した木が「埋没」で退く正体は二つ ── LOD1〜3 の板を当たりに数える・垂れた枝先を根元と読む(岡部 主木の黒松 1.65 倍 2026-10-09)
metadata:
  type: project
---

症状: 岡部 Stage5 で主木の黒松 7 本(1.65 倍・傾き 12°)が埋没 1.0〜3.9 で建たなかった。平らな地表(21.0)でも 1.01。
原因1: GroundCandidates が LODGroup の LOD1〜3 も当たりに入れていた ── 粗い十字の板が地中へ 1m 刺さる(LOD0 の樹皮は −0.17)。
原因2: SeatPlant の根元の帯 = 全当たりの最も低い所 ── 拡大した樹冠の垂れた枝先(芯から 5.7m)が池の側の低い地表 19.99 に当たり、それを根元として据えて幹の足を 1m 埋めた。
対処(EDO-0502 第60巡): GroundCandidates は LOD1 以降だけの描き手を外す。SeatPlantAt は TrunkBaseRadius(LOD0 の樹皮の足 0.3m の半径 +0.1)の内だけを根元の帯にする。
**How to apply:** 木の埋没が数m・平地でも 1m を見たら、まず当たりの最深点の芯からの距離と、どの LOD/材の頂点かを刷る。普請検査の RootBandGap は今も全当たりで測る(枝先を根元と読む偽の浮きが出得る)。関連 [[trunk-foot-band-catches-foliage]] [[seatplant-float-cap-buries-slope-trees]]
