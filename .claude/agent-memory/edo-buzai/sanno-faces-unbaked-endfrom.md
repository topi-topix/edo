---
name: sanno-faces-unbaked-endfrom
description: 山王の門の生成器で RM.faces を worktree の指図に当てると、他の門に従属する run(endFrom/uFrom)の端が sanno_impl.json に無くて止まる。Blender は門番の資源名に無い
metadata:
  type: project
---

2026-09-14 中門を明治16年寸法(`--pitch 2.54x2.54`)で起こし直したとき、`SANNO_SASHIZU=<worktree の指図>` で `RM.faces` を呼ぶと
「run『Sode_Romon_S』の解決済みの端が sanno_impl.json に無い」で止まった(楼門の袖塀は改訂中で焼き出しが古い)。
中門から数十 m 離れた run なので、**この門を指さない従属 run を面の読みから外して**渡した。
あわせて、worktree の透塀は `gapHalf` ではなく `gapFrom.edge = 側柱の外面` を持つので、口の縁を `colRadiusM` から解く分岐が要った。
`edo_session.py claim --resources blender` は「不明な資源」で弾かれる(資源は unity/terrain/git-index/assets/main)。

**Why:** 指図は worktree で改訂中、`sanno_impl.json` は main の古い焼き出し。両者を混ぜて読むと従属値が解けない。
**How to apply:** 山王の門を別寸で焼くときは、面の読みを「この門に関わる run」だけへ絞る。json の axis と引数が違っても ⚠ で進め、報告で指図方へ返す。関連 [[shaden-scaled-span-eave-band]]
