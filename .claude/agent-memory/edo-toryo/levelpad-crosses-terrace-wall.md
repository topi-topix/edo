---
name: levelpad-crosses-terrace-wall
description: LevelPad に区画を渡すと法が段の土留めを越えて下の面を盛る(岡部 米蔵の均しで通用門の溜りが 2.01m 埋まった)。範囲は棟の建つ面の poly を渡す
metadata:
  type: project
---

2026-10-04 EDO-0502 岡部 第7巡。附属屋の均しの見逃しを 0.15→0.02 に締めたら、米蔵・蔵1 の LevelPad が走り、
盛土の法(1:batterFill)が東の平場の縁の土留め TW_Higashi_Tsuyo / TW_Kado_Hokuto を越えて、下の面(通用門の溜り 12.2・
北東の郭 13.1)の節点を 2.01 / 0.75m 盛った(造成QA の最大が 1.68→2.01 へ悪化して気付いた)。

原因: LevelPad の第1引数は「この外の節点は触らない」多角形で、区画(Poly)を渡していた。区画の中には段の土留めの向こうの面も入る。
対処: 棟の建つ**面**(指図 terraces の poly・TerracePolyAt)を渡す。
How to apply: 均し・盛りを伴う据えを締めたら、Stage1 前の heightmap と差を取り、0.3m を超えて動いた節点が面の外に無いかを見る。

関連: [[regrade-only-the-changed-block]] [[dig-to-unbury-cascades]]
