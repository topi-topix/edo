---
name: seatplant-nan-enoki-mukunoki-noki
description: LOD 付きで焼き直した榎・椋の木は子の名に "noki" を含み、IsRoofName が屋根と見て SeatPlant が NaN を返す
metadata:
  type: project
---

症状: 2026-09-23 山王 Stage7(EDO-0401 3回目)で名指しの木 6 本(Enoki_*/Mukunoki_*)が「埋 NaN / 浮 NaN」で据わらない。
ピボットを地表に置いたままになり、斜面の 4 本は書き戻し済みの版より 0.01〜0.19m 低い。
原因: 904a6744 で LOD の子名が `Tree_Enoki_Big_LOD0` などになった。GroundCandidates → IsRoofName の部分文字列の篩が
"noki"(軒)に当たって全部の子を屋根として外し、候補 0 → NaN。IsRoofName のコメントに予告済みだった型。
対処: 直すのは EdoBuild の篩(植木は屋根の篩を掛けない、または名の語の境で判定する)。Stage7 側で局所修正しない。
当たる先: SeatPlant / Body / Contact など GroundCandidates・屋根の篩を使うすべて × 榎・椋の木を置く全邸。
