---
name: retired-group-makes-children-unmeasurable
description: 前の巡で RetireStaleGroup が退けた群(SetActive false)の下へ建て直すと子が非活性のまま ── Body が 0 点で SeatPlant が全数 NaN
metadata:
  type: project
---

症状(2026-10-03 EDO-0502・岡部 Stage5): 植栽 587 本が全部「埋没 NaN 浮き NaN」で据えに失敗。
原因: 前の巡で算出物が古く `RetireStaleGroup("Nishi")` が群 Nishi を非活性にしていた。`Group("Nishi/Planting")` は
子を作るが親を起こさないので、子は activeInHierarchy=false ── `EdoBuild.Body` は非活性の描画器を数えず 0 点。
対処: 欄が焼けて建て直すときは `Group(親).gameObject.SetActive(true)` を先に打ち、古い欄の子群だけを退ける。
**How to apply:** NaN が全数に出たら据えの関数より先に親の activeSelf を見る。

もう一つ(同じ巡): 附属屋の照合を `BodyExRoofAt`(屋根の材を落とす)の外接で測ると、垂木・桁が wood の材で
軒先まで出ていて軒込みの寸法になる(帯の長屋 33×3間 が 60.73×7.45)。躯体は水平断面で測る ──
`EdoBuild.BodyFootprintLocal`(丈の 1/4 の SectionAt)で 60.16×5.62。
関連: [[one-mesh-part-split-by-submesh]] [[seatplant-float-cap-buries-slope-trees]]
