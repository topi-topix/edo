---
name: typology-log-stale-after-neighbor-regrade
description: 隣り合う類型の区画を順に建てると、先に建てた区画のログの浮きの数は後の区画の造成で古くなる(共有辺の地表が動く)
metadata:
  type: project
---

症状(2026-09-28 EDO-0472 十坊): 各区画の BuildParcel のログは、塀の浮きが 248 駒。全部建てた後に同じ測り
(Inspect と同じ RootToBed(GroundBedSpan, 0.05))で数え直すと 231 駒で、1〜6 の数が違った。
原因: 次の区画の造成(GradePads)は自分の区画の中だけを動かすが、共有辺の上の生垣・塀の足もとの地表はその内側を拾う。
対処: 並びの区画を建てたら、ログの数を写さずに全部建て終えた姿で数え直す(区画ごとのログは建てたその時の値)。

関連: [[typology-multi-parcel-koba]]
