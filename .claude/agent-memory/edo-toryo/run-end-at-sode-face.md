---
name: run-end-at-sode-face
description: 土留めの端を袖の外面で止める型(EdoBuild.RunEndAtFace)は山王の袖の端 9 箇所に当たる。一直線に続く袖は外す・斜め 43° は切った駒が要る・柵の端の詰めは法の足に沿う run を誤検出する
metadata:
  type: project
---

2026-09-26 EDO-0430(山王 Stage3/4)。

- 症状: 石段の袖(厚 0.6)が土留めの端の駒の中に丸ごと隠れていた(郭の階の北・男坂の口・参道の階・楼門の腰)。
  原因: 区間の端 = 袖の線(内面)で、駒はそこまで積む。対処: Stage3 が据える**前に** `EdoBuild.RunEndAtFace` で端を袖の外面へ(−0.60)。
  ⚠ 短い区間(N=1)は止めた端を必ず面一に(`stopA/stopB` → ce)── 芯に置くと余りが袖へ 0.32 入った。
- ⚠ 袖が土留めの通りを**一直線に続ける**端(EK×郭の階の南の袖・前庭の切り込み×参道の階の袖)は止めない ── 止めると段石の端の切り
  (CutStairEndsToBatter)が焼いていない形に変わる。
- 女坂の口(前庭の SW/SE)は袖が走りに 43° で交わる ⇒ 直の小口では面で当たらない。★ で差し戻す(端を斜めに切った Castle Wall が要る)。
- 隅の駒(Ishigaki_Kado_90)の腕が短い区間より長いと、腕が袖へ入る(郭の階の南 0.41・参道の階の東 0.29)── 据えでは消えない。短い腕の隅が要る。
- 柵の端の詰め(`RetractEndFromBodies`)は、run が土留めの法の足に沿って立つ板塀(Ita_ZSW/ZSE)を「端が中」と誤り 1.5m 詰めかけた
  ⇒ 戻った点の真上から下ろす光線が帯で当たれば測らない。根入れまで帯に入れると法 1:0.25 で口が 0.07 広がる(許容超え)⇒ 帯は地表から上。
- 突き合わせは `BuiltSegs` がビルダーと同じ関数(`RetractRunEndsFromWalls`)を通さないと端のずれを嘘で鳴らす。

関連: [[short-return-tie-and-sode-extent]] [[batter-cut-parts-measure-and-check]] [[run-corners-seams-and-tiers]]
