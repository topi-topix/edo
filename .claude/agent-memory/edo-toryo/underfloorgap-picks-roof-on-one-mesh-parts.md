---
name: underfloorgap-picks-roof-on-one-mesh-parts
description: EdoBuild.UnderfloorGap は山王の堂・鐘楼鼓楼(一体で焼いた駒)で屋根の頂点を接地候補に拾い 5〜7m の偽の浮きを出す
metadata:
  type: project
---

**症状**(2026-09-23 EDO-0395): 平らな段(地盤 28.30)に据えた附属堂8棟が、Contact=0.000 なのに
UnderfloorGap が 3.85〜6.92m。最悪点の y が 32〜35 = 宝形の露盤・大棟の高さ。

**原因**: `GroundCandidates` が一体メッシュの駒で底の点を選べず、屋根の頂点まで候補に入れている。

**対処**: 底の浮き・埋没は「最下の頂点(y ≤ 底+0.02)ごとに 頂点y − EdoBuild.Ground」で測る。8棟は浮き 0.000〜0.007
(観音堂だけ段の縁の隅で 0.094)。⛔ UnderfloorGap の数を浮きとして報告しない。直しは EdoBuild 側(未着手・pitfalls 候補)。

関連: [[one-mesh-part-split-by-submesh]]
