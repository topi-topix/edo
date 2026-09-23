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

2026-09-22(末社の小鳥居 `Sanno_Torii_Massha_1818x2727`)で足した三つ。

- ⭕ **`Shu_Torii.mat` はテクスチャを持たない**(`_BaseMap` = null / `_BaseColor` 0.62,0.13,0.08 の**単色**)。
  ⇒ 朱で塗る部材は **UV を凝っても一切効かない**。見せ場は**造形だけ**(面の分節・木鼻・楔・反り)。
  ⛔ 「朱がのっぺりする」を UV で直そうとしない。⭕ 逆に UV の心配が要らないので矩形サンプルは形式的でよい。
- ⭕ **`build_sanno_torii`(石鳥居)の道具はそのまま木の鳥居に使える** — `face/prism/octagon/swept_bar`
  の材質の並びが **[Kirishi, Shu_Torii] = [STONE, SHU]** で、朱の木部は `mat=ST.SHU` を渡すだけ。
  ⚠ `ST.face` の既定タイルは **1.05**(石鳥居の笠木用)なので、小さな石には `tile=0.44` を明示して渡す。
- ⛔ **楔(くさび)を角柱で作ると「輪」に見える**(検証レンダで実見)。上が広く下が狭い**台形**にする。
