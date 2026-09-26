---
name: panel-on-crest-and-shoulder-traps
description: 板塀を土留めの天端・切土の法肩に据える罠 ── 帯は天端の最高で・地山(base_dem)では口の切り下げが読めない・Itabei5 は 7.49m で 3m 未満に割れない
metadata:
  type: project
---

2026-09-26 EDO-0437 第6巡(山王 前庭の南の板塀 Ita_ZSW / Ita_ZSE)。

1. **天端に載る run の端を「駒の中」と誤読** — RetractEndFromBodies の帯を端の設計面(SurfaceY)から取ると、割肌の天端(15.99〜16.19)の
   高い石の小口に当たり、Ita_ZSW を天端の上から 2.05m 詰めて女坂の袖の上(浮き 0.46〜0.76)にだけ残した。
   対処: 帯の下端 = 走りに沿う天端の最高(EdoBuild.BedTopAt)、受けが途切れる所で端を止める(RetractEndToBedEdge)、床 = 地表と天端の高い方。
2. **法肩の「下り始め」は base_dem では平ら** — 造成(女坂の口の切り下げ)は地山に載っていない。地山の法肩は 17.04→17.01 で下らず、
   描かれた地表との低い方で測って初めて 0.45m 手前で下る(EdoBuild.ShoulderLevelEnd の drawn)。
3. **Itabei5 は 1 枚 7.49m**(RunMeasure 4.118×ES)── PanelRun の割りの下限 0.4 倍 = 3.0m なので 5.8m は 1 枚(縮めて 0.77 倍)にしかならず、
   床の起伏 0.17 を割って逃がせない。1.8m の run は 0.42 倍に縮む。柱 5 本の一体の駒なので割肌の天端では柱ごとに 0.005〜0.046 浮く。

**How to apply:** 板塀の浮きを割りで消せないときは、駒の側(柱を別の子に分けて一本ずつ据える)か run の端の話として返す。
関連: [[skin-edge-across-nozura-face]] [[measure-dont-nudge]] [[contact-not-bottom]]
