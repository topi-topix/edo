---
name: outer-wall-face-outside-parcel-and-shared-pads
description: 外周の石垣の見え面は区画の線の外にあり、皮は区画の外を 2m 格子のまま描くので鋸の歯の土が残る・隣り合う棟の LevelPad は節点を奪い合う・別窓が Hifu を握ると CutEdgeSkin を直せない
metadata:
  type: project
---

2026-10-06 EDO-0502 第29巡(岡部 東の長屋の台 IG_N40_2・N41)。

1. 症状: 外周の石垣の見え面の足元に高さ最大 2.9m の土の三角が 2m おき。原因: 見え面は区画の線の**外**(0.05m 外の点が全部 out)。
   線の内の節点は台の天端(16.4)、線の外は 12.7 で、2m 格子が一次で描く。皮(CutEdgeSkin)は段の土留めに接する石垣しか受け取らず、
   しかも区画の外の点を probe(=同じ 2m 格子)で描く(SkinDesign.own)。対処: EdoBuild.OutsideFootExcess で足元を描けない外周の駒を選んで皮へ渡し、
   EdoBuild.DesignOutsideOwn で設計の区画の外の節点を「区画の内・駒の下の節点を造成前に置き換えた地盤」にして own を外す(EdoBuildHifuSoto.cs)。
   ⚠ WallFace はこの城の石垣で内向きを返した(N41 で (-1,0)・見え面は東)── 向きを使わず外形の外を一周歩いた。
2. 症状: 米蔵の片側の浮き 0.124。原因: 隣の薪蔵(離れ 0.25m・yAt が 0.15 低い)の LevelPad が後から同じ節点を切り下げた。
   対処: PlaceService で均しを全棟据えた後に低い順に掛ける(共有の節点は高い方が勝ち、低い棟の縁は埋まる)。
3. 別の窓が EdoBuildHifu.cs を claim していると CutEdgeSkin を直せない(門番が止める・steal は不可)。設計(SkinDesign)を呼び手の側で整える新しい partial に逃がした。
   同じ巡のうちに別窓が Unity で作業場を土井へ開き直していた(claim は当方)── 着手のたびに作業場の本体名を確かめる。

**How to apply:** 外周の石垣の足元の土の歯を見たら、まず見え面の外 0.05m の点が区画の内か外かを測る(外なら皮の own の話)。
附属屋の浮きは隣の棟の均しとの節点の取り合いを先に疑う。関連 [[wall-toe-mound-is-grid-not-grading]] [[wall-foot-ridge-from-nodes-under-hull]] [[koba-left-dirty-by-other-window]]
