---
name: terrain-holes-and-skin-traps
description: 地形に穴を開けて皮(EdoBuild.CutEdgeSkin)で描くときの罠 — 穴の升の地形の木は消える・地形のシェーダの材質は真っ黒になる・艶で白く光る
metadata:
  type: project
---

2026-09-24 山王 EDO-0430 で縁の皮(`EdoBuildHifu.cs` の `CutEdgeSkin`)を起こしたときに踏んだ罠。

1. **Unity は穴の升の地形の木を消す。** SetHoles の時点でも、後から SetTreeInstances で足しても、穴の升の木は
   treeInstances から落ちる(社叢 70 本が消え、突き合わせに「社叢の木の数」が出て気付いた)。
   対処: 木の立つ升には穴を開けない(`skipTree` に数える)。⚠ 消えた木は地形の資産を戻さないと帰らない。
2. **地形のシェーダをメッシュの材質に使うと真っ黒。** 地形が毎フレーム渡す層の値(`_DiffuseRemapScale*` ほか)は
   シェーダの Properties に無いので、材質に SetVector しても保存されない ⇒ 0 ⇒ 黒。
   対処: Properties に宣言した写し(`Edo/TerrainSkinStochastic` / `Edo/TerrainSkinAdd`)。
3. **層の smoothnessSource(赤坂は DiffuseAlphaChannel)を写すと空を映して白く光る。** 定数(2)で地形と同じ見え。
4. 天端で皮を下げる相手は**上を向いた面だけ**。全ての面で下げると城の石垣の駒の控え(背の斜面)に沿って上の段が 3.4m 掘れた。
5. `EditorApplication.delayCall` は Unity が裏にいると走らない(10 分待っても来ない)。30 秒を超える処理は割るか、再送されても冪等にする。

**How to apply:** 皮を起こす前に地形の資産を scratchpad へ退避(穴・芝・木は Undo の外)。試し打ちで芝を消したら
資産を戻して打ち直す(cp → ImportAsset ForceUpdate)。整地・石段・土留めを流し直したら Stage9 を最後に流す。

関連: [[dig-to-unbury-cascades]] [[terrain-detail-array-dims-lie]] [[contact-must-use-drawn-surface]]

追記 2026-09-25 EDO-0409(前庭v2 の植え直し): 皮の穴は**後から焼き足した植栽の点**も食う。Stage9 の skipTree はその時点の
treeInstances しか見ないので、焼き直しで新しく入った前庭の帯の低木 4 点(x≈−441, z 851〜865・穴の升 775 列)が SetTreeInstances で
黙って落ちた(Stage7 の報告は「1929 本植えた」のまま・資産は 4 本少ない)。突き合わせの「数が違う」はまず穴の升を引く。
直すのは穴の側で、Stage7 では消せない。→ 直した(2026-09-25): `CutEdgeSkin(plantPoints:)` に算出物の点(place≠GameObject)を渡し、その升は開けない(skipPlant・検め plantOnHole=0)。開けていたのは前庭の西の土留め TW_Zentei_W の外形+margin 0.5m。名指しの GameObject の木は穴に消されないので渡していない。
