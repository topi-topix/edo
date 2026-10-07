---
name: ankyo-lid-and-foot-under-overhang
description: 暗渠の蓋石が全型「測れない」(MizoPieceOf は低ポリの板で ok=偽)・足元を最も低い交わりで読むと笠の裏・底の開いた腰を足元と誤る
metadata:
  type: project
---
症状(土井 r11 2026-10-05): S9 の暗渠が全型で「蓋石の部材が測れない」。直すと次は奥の塀 18 点を「足元が地面より 0.7〜2.9m 高い」で退けた。
原因: ① MizoPieceOf は溝用で、芯の帯(|x|≤0.12)に頂点も上向き面の重心も無い低ポリの板(蓋石)だと floor が解けず ok=偽。② LowestSurfaceAt は最も低い交わり ── 溝が塀の脇を走ると笠の裏(地面+2m)を、練塀の腰は底面が無く腰の上面(上向き)を足元と読む。
対処: 蓋は外形(len・top>bottom)で採る。足元は EdoBuild.LowestFootAt(厚み 0.3 以上の実体の下面だけ・最も低い交わりが上向きなら近くの頂点の最低)。残り3点は本物の段違い(Oku_Hei_0_4 の布石が届かない所)。
