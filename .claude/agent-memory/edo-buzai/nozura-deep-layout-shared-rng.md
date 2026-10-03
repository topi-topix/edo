---
name: nozura-deep-layout-shared-rng
description: 野面の乱積みの駒を H2.40 より深く焼くとき DEEP を上げると既存の全駒の中の石の割りが変わる(乱数列を共有)
metadata:
  type: project
---
`build_sanno_nozura.layout` の中の石は一本の乱数列で行→種ごとの目地幅・頭の弧を引くので、深さ(DEEP)を上げると行が増えて以降の引きが全部ずれ、既存 H0.15〜2.40 の中の石が別物に焼き直る(端の石の列は行を下へ継ぎ足すだけなので不変)。
**Why:** 2026-09-28 EDO-0477 で H4.80 を初めて焼いた。DEEP=2.6 のままだと u<−2.6 は石が無く板だけになる。
**How to apply:** `wall_cells(v, depth)` は h+BURY > DEEP の駒だけ深い型を別キャッシュで引く。既存の見付は DEEP のまま。三角形は H4.8 で約 3 万(H2.4 の約 2 倍)。[[nozura-grade-set-and-nearest]]
