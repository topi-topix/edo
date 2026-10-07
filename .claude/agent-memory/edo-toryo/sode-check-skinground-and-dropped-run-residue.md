---
name: sode-check-skinground-and-dropped-run-residue
description: Stage2b の袖の坂の検めは SkinGround(設計面と地形の低い方)で盛った小段を読まず偽の ⛔・run を外すと前の巡の盛りが残る・練塀の隅の駒は内面が直の塀より 0.5 奥
metadata:
  type: project
---
2026-10-07 EDO-0502 第45巡(岡部 A〜C)。

1. **Stage2b の「袖の坂 天端と背の地盤の差」は SkinGround で背を測る** = flat 面 → 坂 → min(DesignY, 地形)。背の小段(#land)で地形を盛っても
   設計面の方が低いので盛りを読まず、0.41 の ⛔ が何巡も出ていた(描かれた地表では 0.30 ⭕)。しかも 2b は皮の前に測る。
   ⇒ 皮の後に `EdoOkabeYashikiBuilder.Stage3c_SodeSlopeCheck`(EdoBuild.Drawn().At で測る)を流して読む。
2. **返しの run を外す・縮める直しは、前の巡の BackBench の盛りが地形に残る**(BackBench は盛るだけ・切らない)。外した run の背に 0.60 残っていた。
   ⇒ 測る: 地形 − BackBenchesAt(全小段, DesignY) を返しの周りで刷る。残れば Stage1 から流す([[backbench-residue-cleared-by-stage1]])。
3. **積み止めの行く手の塀の内面は隅の駒(Dobei_Kado_78)で 1.05**(直の練塀 S_Hei は 0.55)。指図の目安 0.9 は区画の線を内面と見た数で、
   実測では引き 2.1 になった(EndSpec.tomeClear・TomeClearShort)。狙い未達は ⚠ で返す。

関連: [[tome-piece-facing-and-joint]] [[contact-must-use-drawn-surface]]

4. **(第49巡)Stage3b の「小口の土の検め」も同じ罠で +0.70 の偽の ⛔**: SkinGround は盛った小口の土も皮も読まず設計面 15.95 を拾った
   (描かれた地表は 16.41〜16.49)。⇒ 皮の後の検めは全部 `EdoBuild.Drawn()` で。さらに皮の法の頭打ち(OutsideY)が面の縁の脇の盛りを
   面の高さへ削り戻す ⇒ 盛った節点は `SkinDesign.hold` で法から外す。小口の面は野面で凸凹なので 0.1m の帯ごとに面と頂を測る。
5. **Stage3b(皮)は M1 8GB で Unity をメモリ不足で落とすことがある**(第49巡 q5)。落ちた後は作業場が開き直しで、書き戻していない
   流しは消える(袖の据え替えが元の駒に戻っていた)⇒ 2b の後に一度書き戻してから 3b を流す。
