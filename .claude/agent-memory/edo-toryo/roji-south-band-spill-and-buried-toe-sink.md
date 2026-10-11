---
name: roji-south-band-spill-and-buried-toe-sink
description: 背の路地の南の延長の帯は辺41 の向きに延ばすので角 P0 の南で辺1・2 を越えて樹下へ +1.15 盛っていた(perimeterRetain は隣の区画の中を戻さない)・隅の駒の床の下の足を SinkGroundUnderParts が掘る
metadata:
  type: project
---

2026-10-12 EDO-0502 第114巡(岡部 角 P0 の南)。

1. **症状**: 区画の外 26 節点が最大 +1.15(x −378.9〜−379.1・z 953〜955.3 = 辺1・2 の線の東 0.07〜0.32)。
   **原因**: SeRojiSouthExtend の帯は辺41(長屋の背)の向きの矩形で、南の練塀まで延ばすと辺41 に直角でない辺1・2 の線を越える。
   RestorePerimeterSpill は「隣の区画の中は隣の造成」として**戻さない**(樹下の区画)── 戻す処理を後へ回しても消えない。
   **対処**: 帯の yAt で区画の線から ClipIn()(seRoji.clipOrder の 0.125)より外は NaN。r113 の写し(kita_pre.bin)から外の 26 節点を戻した。
2. **症状**: TW_Higashi_Se の南の隅 kado6 の前の路地の床に 10.8 の穴。**原因**: 隅の駒の稜は見え面の線より前へ出て、その足は床の下へ埋まる。
   SinkGroundUnderParts は真上から最初に当たる面(床の下の足)−0.05 まで下げる。
   **対処**: SinkGroundUnderParts に floorMin を足し、背の路地の床(SeRojiPlan.At)−0.02 より下げない。床の帯は SeRoji() が SessionState から南の延長を読み直す。

**How to apply:** 辺に沿う帯を辺の先へ延ばす多角形は必ず区画の線で切る。法の駒の下を下げる処理は、設計の床がある所では床で止める。
関連: [[concave-corner-wall-behind-nagaya-back]] [[prev-grade-left-in-neighbor-after-parcel-move]]
