---
name: prev-grade-left-in-neighbor-after-parcel-move
description: 区画の線を動かすと前の巡の造成が隣の区画に残る ── Stage1 は区画の外を触らないので DEM へ戻らない。類型の区画(造成の持ち主なし)だけ戻す
metadata:
  type: project
---

2026-09-26 EDO-0430 山王。観理院(sannosha_kanri)の中の節点 x −427.88 / −425.88 が DEM より +0.29〜+1.07m 高いまま残っていた。

- **原因**: 2026-09-23 に社地と観理院の境の頂点を動かした。それ以前の算出物 `graded`(git cd111e71 など)がその節点に設計面を持ち、
  Stage1 が書いた。境の後は社地の外になり、Stage1 も `Stage1_Grade(prevImplPath)`(社地の中だけ戻す)も触らない。
- **対処**: `Stage1_Grade(prev)` が、社地の外でも**類型表に載り built:hand でない区画**(類型ビルダーは造成しない = 持ち主なし)の節点は戻す
  (`InUngradedParcel`)。前の算出物は `git show <hash>:docs/Sashizu/sanno_impl.json` で書き出して渡す。16 節点を戻した。
- ⚠ 観理院の類型の土塀(`Edo_Typo_sannosha_kanri` dobei_2_*)と旧 `Edo_Sanno_Kanriin` の練塀が**二重に**建ち、類型の土塀は
  前庭の東の土留めの線(x ≈ −429)の上に立つ ── 作業場に隣として載らないので測れない。戻した地盤で浮く恐れ(隣の邸の話・掲示板へ)。
- z 826/828 の +0.15/+0.17 はどの前の算出物も覆っていない(DEM の確度 P・中央値 0.127 の内外)。触らない。

関連: [[regrade-only-the-changed-block]] [[grade-transfer-cliff-and-dropped-cells]]
