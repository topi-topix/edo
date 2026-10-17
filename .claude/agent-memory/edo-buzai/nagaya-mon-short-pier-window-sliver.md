---
name: nagaya-mon-short-pier-window-sliver
description: 3間の門長屋で口の端が躯体の端から 0.78〜1.95m に来ると端の間の一階窓が切れて 0.1m の窓枠の欠片が方立の脇に残る・gateFromLeft は局所 +X 端から(2026-10-04 土井 EDO-0533)
metadata:
  type: project
---
- 5.46 --body の端の間の一階窓は躯体の端から 0.78〜1.95m(両端対称)。口の縁がこの帯に入ると窓の欠片が残る ⇒ 縁を 0.78 以下か 1.95 以上へ。土井の通用門は芯 3.37(縁 0.89)で欠片が残り、指図を 3.52(縁 0.74)へ直して消えた。
- gateFromLeft は札の passage が示すとおり**局所 +X 端**から(芯 = len/2 − g)。土井の辺13は YawFace(外向き)で局所 +X = −走り ⇒ +X 端 = s0 側 ⇒ g = s − s0。
- --gate-drop は札の source に入っていなかった ⇒ source と passage.sillY に書くよう直した(C# の JsonUtility の書き戻しでは sillY は落ちる)。
関連 [[run-length-float32-names]] [[nagaya-body-length-and-goten-root-offset]]
