---
name: wallface-thin-axis-fails-on-deep-nozura
description: WallFace の「薄い軸が見え面」は深い見付の野面(Nozura2_H4800 走り2.12・奥行2.61)で走りを見え面と取り違える・背の路地の型は欄が建たないと長屋の背が埋まる(2026-10-11 EDO-0502 第105巡)
metadata:
  type: project
---
- 症状: K_Dan1 の右脇の土の縦帯・皮が見え面より前 104 点。原因: `EdoBuild.WallFace` が薄い軸を採り、H4800 の駒(奥行>走り)46/48 と留め 3 駒で
  見え面=走りの向き ⇒ 皮の上限「見え面 −0.02」と NozuraCrestCover の帯が横向きに掛かった。
  対処: 野面の直線の駒(Sanno_Nozura_*/Nozura2_* で _Kado 以外)は札どおり局所 Z を軸に、± だけ FaceSide で測る(`EdoBuild.IsNozuraStraightPiece`)。
  岡部 Dan の 199 駒で軸外れ 0 を確かめた。
- 罠2: 施主裁定で長屋の座を下げた(12.80/12.30)のに、背の路地(grading.seRoji)と TW_Higashi_Se が建たないと、長屋の背が 1.2〜3.5m 埋まる
  (背の 0.5m 先の地表 14.0〜16.4)。座の欄だけ先に流すと許容0の埋没を作る ── 背の土の受け(路地・石垣)と同じ巡で建てる。

**How to apply:** 見え面の向きを測る関数を部材の形(縦横比)で決めない。札(局所軸)で決め符号だけ測る。座を下げる裁定は背の受けとセットで流す。
[[nozura-wall-traps]] [[nozura2-joint-line-and-grade-chain]]
