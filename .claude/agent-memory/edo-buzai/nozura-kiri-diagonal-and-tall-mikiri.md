---
name: nozura-kiri-diagonal-and-tall-mikiri
description: 野面の駒を斜めの鉛直面で切るときの罠(ops.bisect が斜め面で外れる・枠の外の石は隣の1間から採る・欠片)と、見切り石は天端まで届く丈で焼き天端で据える
metadata:
  type: project
---

2026-09-26 EDO-0437(`build_sanno_nozura.py -- nkiri` / `-- mikiri_h`・`Own.SannoNozuraKiriEnd` / `Own.SannoNozuraMikiriH`)。

- ⛔ `bpy.ops.mesh.bisect` は軸に沿う面では合うが、斜めの面(43.2°)では面から 0.036 外に頂点が残った ⇒ `bmesh.ops.bisect_plane` + 切り口の境界辺だけ `holes_fill`。
- 切る面を天端の前の縁の端に通すと、法の足(L)か控え(S)が 1間の枠の外へ出る ⇒ 隣の 1間の割り(共有する端の石は除く)を足してから切る。石の角だけ残る欠片(二辺 < 0.08)は袖の前に浮いて見えたので落とす。
- 見切り石は見え 0.6 の一石だと背の土に埋まる(0.82/1.20)⇒ 段(1.2〜2.1)で焼き、最高 = 天端の線。据えは天端で合わせ沈める。

**Why:** 許容0(めり込み −0.55・埋没)を部材の形で消すため。
**How to apply:** 別の角の端・別の丈は一覧(sanno_nozura_kiri_set.txt)/ --h= に足して焼く。関連 [[castle-wall-kiri-and-short-arm]] [[nozura-back-crest-flush]]
