---
name: nozura-deep-layout-shared-rng
description: 野面の乱積みの駒を H2.40 より深く焼くとき DEEP を上げると既存の全駒の中の石の割りが変わる(乱数列を共有)
metadata:
  type: project
---
`build_sanno_nozura.layout` の中の石は一本の乱数列で行→種ごとの目地幅・頭の弧を引くので、深さ(DEEP)を上げると行が増えて以降の引きが全部ずれ、既存 H0.15〜2.40 の中の石が別物に焼き直る(端の石の列は行を下へ継ぎ足すだけなので不変)。
**Why:** 2026-09-28 EDO-0477 で H4.80 を初めて焼いた。DEEP=2.6 のままだと u<−2.6 は石が無く板だけになる。
**How to apply:** `wall_cells(v, depth)` は h+BURY > DEEP の駒だけ深い型を別キャッシュで引く。既存の見付は DEEP のまま。三角形は H4.8 で約 3 万(H2.4 の約 2 倍)。[[nozura-grade-set-and-nearest]]

2026-10-07 EDO-0502: H3000/H3600/H4200/H4800 × G±120/±275/±450 × a〜d(96 駒・約 2 分)を staging/buzai_nozura_tall に焼いた。深さごとに型のキー (v, depth) が別 ⇒ H3000〜4200 の中の石は H4800 と別物(継ぎ目の端の列は同じ)。⚠ 在庫の G0 は H4800 にしか無い。holes 0・crest 最大 +0.024。並べ焼きの既定カメラ(grade --render)は H4.8 だと天端が切れる ⇒ 引いた構図は scratchpad の render_tall.py の型(カメラ y −14・z 3)。
