---
name: sukibei-roster-needs-derive-gaps
description: 透塀の焼く一覧は derive_gaps を通してから sukibei_span_plan を呼ばないと、中門の口が消えて t 端の 3 点が名簿から落ちる
metadata:
  type: project
---

山王の透塀で「何を焼くか」を出すときは、指図の json をそのまま
`sukibei_span_plan(d)` へ渡してはいけない。**`derive_gaps(d)` を先に呼ぶ。**

`runs[Sukibei_E]` は中門の口を `gapFrom`(門の側柱の外面からの従属値)でしか持たず、
`gapV` / `gapHalf` は**図を焼くときに計算して書き込まれる**。生の json では口が無いので
run が割れず、`1865_*`(29.83 m を 16 等分)という**存在しない部材**が 3 点出て、
本来の `1767_cn/nn/nt` と `1850_nc/nn/tn` の 6 点が名簿から落ちる(要る 23 点 ≠ 実際の 26 点)。

**Why:** 指図は「同じ量に二つの数を作らない」ので、従属値を json に置かない(規則どおり)。
**How to apply:** 焼く前に `derive_gaps(d)` → `sukibei_span_plan(d)` を scratchpad の
python で回し、呼び出し元がくれた一覧と**突き合わせてから**焼く(食い違ったら報告する)。
同じ作法は口を持つ他の run にも効く。関連 [[sukibei-c-end-meets-kado-at-node]]

**部材を焼いた物を枝へ載せる道**(2026-09-18 に通した): 門番は
**worktree で blender を回すのを拒む**(在庫キットが gitignore で来ない)。
⇒ ①メインのチェックアウトで `BUZAI_OUT=<scratchpad>/staging` を立てて焼く
(Unity を持っている他セッションのドメインリロードを起こさない)②検証レンダを見る
③ `git -C <worktree> sparse-checkout add Assets/Edo/Models/<邸> Assets/Edo/Scripts/Editor`
④ staging から copy して worktree で pathspec 1 回の commit ⑤ `sparse-checkout set` で戻す。
⚠ この道だとメインの `Assets/` には部材が現れない ⇒ **Unity の remap は枝を main へ取り込んでから**。
