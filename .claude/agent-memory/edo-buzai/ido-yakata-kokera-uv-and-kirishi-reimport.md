---
name: ido-yakata-kokera-uv-and-kirishi-reimport
description: 板葺(こけら)の葺き面は WOOD_UV を棟方向に区切って貼る・区切ったら全面を同じ所で割る・読み直した FBX の Kirishi は桃色に刷れる(2026-09-23 山王の井戸屋形)
metadata:
  type: project
---

2026-09-23 `build_sanno_ido_yakata.py`(井戸屋形 + 板石敷)で踏んだ三つ。

- 葺き面 1 枚に `WOOD_UV` の細い帯を貼ると 2.7m に引き伸ばされ、真上から**棟へ流れる縦縞の板**に見えた。
  ⭕ 棟方向 0.30m ごとに区切り、区ごとに矩形の全幅・流れ方向は段の丈ぶんだけ取る(`prism_v(top_seg=)`)。
- 葺き面だけ割ると T 字の継ぎ目で**開いた辺 621**。⭕ 同じ柱体の他の面も同じ所で割る(0 に戻った)。
- 書き出した FBX を読み直して刷ると `Kirishi` は名前だけの入れ物で**桃色(画像欠落)**。`hook_textures` は
  キットの画像しか引かない ⇒ `hook_kirishi()` で `Materials/Sanno/T_Kirishi_Albedo.png` を結ぶ。

**Why:** 木の帯は柱用の縦長の矩形、Kirishi は山王の自前の材で置き場が違う。
**How to apply:** 板葺・こけら葺を起こすときと、切石の部材を読み直して刷るとき。
礎石は石敷の層(割栗の上)に嵌まるので**石の部材の側**に持たせ、木の部材とは柱の根で接させた。
関連 [[kirishi-tile-and-shu-material]] [[magenta-background-finds-holes]]
