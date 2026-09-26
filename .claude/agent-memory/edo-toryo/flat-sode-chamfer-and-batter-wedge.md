---
name: flat-sode-chamfer-and-batter-wedge
description: 水平の袖の継ぎ目を天端の帯で測ると面取りの V を 0.015 の口と読む・鉛直な端を法の隅へ突き付けると帯の下で楔に入る
metadata:
  type: project
---

2026-09-27 EDO-0459(山王 男坂の最上段の袖 052f を水平の袖 IshidanSodeFlat へ・EdoBuild.LayFlatSode)。

1. 症状: 下の斜めの袖 051f との継ぎ目の口が MeasureEndGap(天端 −0.005 から)で +0.015。原因: 水平の袖の端の面取り 0.02 の V。
   高さを変えて測ると 28.565 以下は 0.0001(Contact も 0.0001)。対処: 継ぎ目は天端 −0.02 の帯で測る。
2. 症状: 坂上の端は天端の帯(28.30)で腰の隅 kado1 に口 0 だが、帯の下で 0.2m 下がるごとに 0.05 ずつ kado1 の中へ入る(1:0.25 の法)。
   旧の斜めの袖(StretchEnd 1.94 倍)も同じ位置まで延ばしていたので前からある形。駒は相手の中に隠れる(相手の頂点は袖の中に 0)。
   解くのは端を法で切った水平の袖の部材(EDO-0442 の斜めの袖の法切りと同じ型)。

**How to apply:** 面取りのある駒どうしの継ぎ目は面取りの下で測る。鉛直な端を法の相手へ ExtendEndToFace で突き付けたら、帯の下の楔を光線で測って報告する。
関連: [[oblique-contact-and-batter-wedge]] [[batter-cut-parts-measure-and-check]]
