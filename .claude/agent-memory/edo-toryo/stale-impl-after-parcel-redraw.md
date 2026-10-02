---
name: stale-impl-after-parcel-redraw
description: 区画を引き直した後、焼き手の無い算出物の欄(kui など)は新しい線の外に据わる。RetireOutsidePoly で建てずに退ける・前もって python で PIP を数える
metadata:
  type: project
---

2026-10-03 EDO-0502 岡部(42頂点へ引き直し)。graded/corners だけ焼き直し、rails/base/planting/kui/migiwa/gardens は旧いまま。

- **症状**: Stage5 が汀の杭列 242 本+貫 242 を新しい線の 4.3〜11.0m 外へ据えた(ビルダーは区画を見ていなかった)。
  rails・planting・gardens の点は内側だった(gardens の外形の頂点が 6 件外へ掛かるが、据わる駒は 0 件外)。
- **対処**: `EdoBuild.RetireOutsidePoly(群, Poly, wait, 札)`(硬い・壁体の実頂点で測って消す)を杭列・竹垣・庭の各群に掛けた。
  着手前に scratchpad の python で `impl` の world 点を新しい parcels.json に PIP しておくと、どの欄が外れるか先に分かる。
- 囲い(塀・石垣・柵)には掛けない ── 線の上に立つ物。基壇 base は焼き手が無く、新しい辺の run 34 本ぶんが無いまま。

関連: [[prev-grade-left-in-neighbor-after-parcel-move]]
