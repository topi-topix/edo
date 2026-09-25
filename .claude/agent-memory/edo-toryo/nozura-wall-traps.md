---
name: nozura-wall-traps
description: 野面の乱積みの土留め(山王 本殿の西)を据えて踏んだ3つ ── 見え面は局所+Z・殻の石垣は頂点で測れない・足の浅い土留めは皮と Tuck が足元を溝に掘る
metadata:
  type: project
---

2026-09-25 EDO-0430(EdoBuild.PlaceNozuraRun・EdoBuildNozura.cs)。

1. **見え面の軸が部材ごとに違う。** Castle Wall は局所 −X、野面の駒 `SannoNozura*` は局所 +Z。`WallFaceRise` は +X 決め打ちで
   野面 9/21 を「裏返り」と嘘を出した → 両軸で法の出を測る形に直した。HifuMeasure の「小口/背/表」の札も +X 前提なので野面では当てにならない。
2. **殻の石垣(Castle Wall)の面は頂点の筋では測れない** ── 大きな面の中に頂点が無く、突き付け先の筋が 2 個しか重ならなかった。
   面は三角形へ光線を打つ(`EdoBuild.RayToBodies`)。柵の端を延ばすのは当たりの**最小**(最大は低い壁の上を抜けて奥の駒に当たり 2.7m 延びた)。
3. ⛔ **足元が地表すれすれの土留め(野面・天端 − 面 ≤ 1.5m)は、皮の「天端の下へ納める cap」と `TuckUnderCrest` が法の足を天端と見て、
   面 28.30 を 27.99〜28.07 へ掘る** ── 石の下端の V が溝の上に覗いた(shaden_nishi_wall_v10.jpg)。未解決。
   直すなら両方とも「駒の天端の帯(最高 − 0.3)に入る面だけを天端として扱う」。城の石垣は法の足が深く地中なので当たらない。

**How to apply:** 野面や低い土留めを据えたら、数値の前に**足元を斜め上から一枚撮る**。見付は指図の足元の平場(`foot.terrace` の多角形の y)で取る
(2m 格子の地表は縁の節点に引かれて面より 0.5m 高く出て、H0.9 を選び床が面の上に浮いた)。
関連: [[castlewall-face-is-local-minus-x]] [[contact-cells-miss-flat-faces]] [[backfill-skin-needs-three-limits]]
