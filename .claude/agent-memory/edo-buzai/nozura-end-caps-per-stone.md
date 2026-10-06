---
name: nozura-end-caps-per-stone
description: 野面の駒の継ぎ目の小口は join 後の一括 bisect(use_fill)では内向き・欠けになる。石ごとに切って塞ぐ(cut_each_ends)。G±450 は剪断のままで崩れない
metadata:
  type: project
---
2026-10-07 EDO-0502(岡部 袖石垣の天端を背の法なりに下げる G±450)で踏んだ。施主「段差の部分が石が切り取られたよう」= 袖の低い端に出た小口の黒い穴。

- 旧の `make_wall` は join の後に `bisect_keep`(ops.bisect use_fill)で両端を切っていた。表の石・裏石・間詰めは互いに食い込むので切り口の輪が交わり、塞ぎが内向き(片端 0.04〜0.13 m²)・欠けになる。Unity の裏面カリングで消えて中が覗く。**G0〜G±275 の既存駒は全部これを持つ**(据えた run の中の継ぎ目は隣の駒で隠れ、端に出た所だけ見える)。
- ⭕ join の前に石ごとに `bm_cut_keep(chip=0)` → 切り口の面だけ三角に割り `dissolve_degenerate`(潰れ三角 200→≤5)。
- 小口の検査は scratchpad の koguchi.py の型: 端の外から ∓X へ撃ち最初に裏面に当たる本数。⚠ 片面の板(ura_floor・back)は勾配の駒では斜めになり当たる ⇒ 面 ≤2 枚の塊は数えない。EEVEE は裏面を描くので見る時は `use_backface_culling = True`。

**How to apply:** 野面の駒を焼き直すとき(どの勾配でも)小口は石ごとに塞がる。旧駒の端が露わになる所は焼き直しが要る。[[nozura-steep-grade-275-and-staged-meta]] [[kado-seam-inward-and-prefab-rays]]
