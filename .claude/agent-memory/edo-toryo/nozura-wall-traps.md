---
name: nozura-wall-traps
description: 野面の乱積みの土留め(山王 本殿の西)で踏んだ4つ ── 見え面は局所+Z・殻の石垣は頂点で測れない・足元の溝は天端の帯で直した(背の帯の溝は未解決)・隅と打ち切りの向き
metadata:
  type: project
---

2026-09-25 EDO-0430(EdoBuild.PlaceNozuraRun・EdoBuildNozura.cs)。

1. **見え面の軸が部材ごとに違う。** Castle Wall は局所 −X、野面の駒 `SannoNozura*` は局所 +Z。`WallFaceRise` は +X 決め打ちで
   野面 9/21 を「裏返り」と嘘を出した → 両軸で法の出を測る形に直した。HifuMeasure の「小口/背/表」の札も +X 前提なので野面では当てにならない。
2. **殻の石垣(Castle Wall)の面は頂点の筋では測れない** ── 大きな面の中に頂点が無く、突き付け先の筋が 2 個しか重ならなかった。
   面は三角形へ光線を打つ(`EdoBuild.RayToBodies`)。柵の端を延ばすのは当たりの**最小**(最大は低い壁の上を抜けて奥の駒に当たり 2.7m 延びた)。
3. **足の浅い土留めの足元の溝は「天端の帯」で直した**(2026-09-25 第2巡)。皮の cap と TuckUnderCrest が法の石の上向きの小面を天端と読んで
   面 28.30 を 27.99 へ掘っていた。`EdoBuild.CREST_BAND`(0.15・周り 0.6m の同じ駒の最高から)の外は法 ── 皮の cap は足元の面
   (外形の外は描く地盤)より下げない・Tuck は下げない・被りに数えない(CutEdgeSkin の crestBandParts・TuckUnderCrest の crestBand)。
   ⚠ 帯 0.3 では天端の奥の控え(−0.3)を天端と読み背の帯が溝。0.15 でも野面の天端の背の石は面より 0.1〜0.4 低く、背の細い帯
   (SukibeiSoto_Chu)に −0.42 の溝が残る(未解決・天端の据え crestOf の側)。⚠ 城の石垣の急な法は上向きの面が無い(Top が NaN)ので
   「篩う駒の外形の中で天端が無い点」も法として面の高さで描く。⚠ 足元の升に地形の木が立つと穴を開けられず 2m 格子の坂が残る ──
   焼き出しに無い古い木(Stage7 未実行)が壁際に 1 列残っていた。Stage7 は**皮を外してから**流す(穴の升の木は Unity が消し、社叢が 3 本欠けた)。
4. 隅の駒・打ち切りの駒の見え面の向きは一軸で測れない ── `EdoBuild.WallFaceRiseKado`(対角の内)・`WallFace`(薄い軸を採る)。

**How to apply:** 野面や低い土留めを据えたら、数値の前に**足元を斜め上から一枚撮る**。見付は指図の足元の平場(`foot.terrace` の多角形の y)で取る
(2m 格子の地表は縁の節点に引かれて面より 0.5m 高く出て、H0.9 を選び床が面の上に浮いた)。
関連: [[castlewall-face-is-local-minus-x]] [[contact-cells-miss-flat-faces]] [[backfill-skin-needs-three-limits]]
