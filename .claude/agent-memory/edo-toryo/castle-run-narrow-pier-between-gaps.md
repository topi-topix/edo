---
name: castle-run-narrow-pier-between-gaps
description: PlaceCastleRun の口が二つ近いと間の切れ端(2m未満)へ芯で 2m の駒を据え、両方の口へ食い込む
metadata:
  type: project
---
症状: 2026-10-04 EDO-0533 土井の表門。扉口と潜戸を gaps に二つ渡したら、間の 0.459m に 2.0m の駒が芯で据わり、扉口へ 0.771・潜戸へ 0.771 食い込んだ(石が扉の前に立つ)。
原因: EdoBuildShiroIshigaki の割りは 2m 未満の切れ端を、片側が口で隣が高い区間のときだけ延ばす。両側が口だと延ばす先が無く、駒の最小 2m がそのまま芯に置かれる。
対処: 据える前に口と口の間を測る。2m 未満なら据え方の話でなく部材(細い石・間の壁を敷居まで下ろす)か指図(潜戸の位置)の話 ⇒ 差し戻す。JsonUtility の札は欄が無くても空の Span を作る(幅で在否を見る)。
解決(同日): 部材方が間の壁の下に地覆を敷居まで通し、札の passage を扉口〜潜戸の一つの口にした(案A)。⚠ その札で「口の芯=s」と据えると扉が 0.68m ずれる ⇒ 扉口は潜戸の反対の端から欄の gate.plan.leaf.w で解く(EdoDoiBuilder.Mon.cs Stage3_Mon の gDoorL)。
