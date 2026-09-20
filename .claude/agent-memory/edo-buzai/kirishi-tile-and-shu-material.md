---
name: kirishi-tile-and-shu-material
description: T_Kirishi_Normal.png は4分割の継ぎ目が入っているので 0.44 タイルを大きな石材へ流用すると小口積みの壁に見える。朱は Shu_Torii.mat が既にあるが置き場が Materials 直下で remap の借り先に無い
metadata:
  type: project
---

2026-09-20 に山王の石鳥居(`Sanno_Torii_5454x7272`)で踏んだ二つ。

- ⛔ **`SB.KIRISHI_TILE`(0.44)を大きな切石へ流用しない。** `T_Kirishi_Normal.png` は
  **2×2 の継ぎ目が入った normal**(albedo のほうは継ぎ目なしの斑)なので、7.65 m の笠木に貼ると
  継ぎ目が 17 本立ち、**一本の石が小口積みの壁**に見える(検証レンダで実見)。⇒ 鳥居は **1.05** にした。
  ⚠ 石の鳥居の笠木は実際に数石を継ぐので、継ぎ目が**数本**出るのはむしろ正しい。基壇・礎盤の 0.44 は動かさない。
- ⭕ **朱の材は既にある** — `Assets/Edo/Materials/Shu_Torii.mat`。⛔ 新規に作らない
  (`V.named_material("Shu_Torii")` で名前だけ運ぶ)。⚠⚠ ただし置き場が **`Assets/Edo/Materials` 直下**で、
  山王の remap(`EdoSannoShaBuilder.RemapSannoShinzo`)の `donorDirs` は `…/Materials/Sanno` までしか見ない。
  ⇒ **そのフォルダを donorDirs の最後に足した**(最後に置けば同名があっても上の借り先が勝つ)。
  ⛔ 足さないと扁額だけ真っ白で出る。
- ⚠ Blender の検証レンダでは `hook_textures` が名前でテクスチャを引くだけなので、
  在庫の .mat の色は**乗らない**。朱・銅瓦のように色が要る材は**生成器側で基色を入れて**刷る
  (⛔ FBX が運ぶのは材質名だけなので Unity 側には影響しない)。
- ⚠ 朱の板を1枚貼っただけでは**扁額に見えない** — 石の縁を回して初めて額として読める。

**Why:** 在庫の材は「どこに置いてあるか」と「どの実寸で貼るか」で見え方が変わる。
**How to apply:** 新しい材名を FBX に載せたら、**その .mat が remap の借り先フォルダに在るか**を
先に確かめる。関連 [[roof-atlas-rect-and-soban-ray]]
