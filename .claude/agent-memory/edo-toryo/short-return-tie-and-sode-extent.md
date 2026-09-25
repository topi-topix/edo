---
name: short-return-tie-and-sode-extent
description: 短い返し(1.7m)の土留めは LowSide の票が 1対1 で割れ右手に倒れて裏返る・石段の袖は脇の離れだけで段を選び切り込みの中まで据わる・Stage3 を皮の後に流し直すと駒ごとの向きが揺れる
metadata:
  type: project
---

2026-09-25 EDO-0430/0442 山王 前庭の切り込み `TW_Zentei_Kiri`。

- **症状1**: 東の返し(1.7m)の駒が前庭の側を向いた(Stage9「高い側を向く Zentei_Kiri 1/5」)。
  **原因**: 区間の票が2つで 1対1、`LowSide` は同票を右手へ倒す。**対処**: `EdoBuild.RunLowHand`(同じ run の区間の票の差で手を決める)を
  Stage3 が同票・無票の区間で使う。
- **症状2**: 参道の階の袖が段の全長(5段)に据わり、切り込みの返しと重なった。**原因**: Stage2 は袖の線からの脇の離れだけで段を選んでいた。
  **対処**: `EdoBuild.OverlapAlong`(袖の run を段の弦へ射影した重なり)で袖の run が走る段だけに据える。他の石段の袖の数は不変。
- **症状3**: Stage2・3 を皮(Stage9)の後に流し直すと、低い腰石垣(見付 0.1m)の駒が一つ逆へ向いた(`TW_Koshi_W_009f`)。
  **原因**: 前の巡の TuckUnderCrest が地形を下げた状態で駒ごとの LowSide を測る。**対処**: Stage1 から流し直す(S1→S2→S3→S9→S4→S5)。
- 残り(未解決): 返しの駒(城の石垣 2.2m)を 1.7m の区間の芯に置くので、口の出隅で N の天端の線より 0.146m 北へ出る。

関連: [[gate-float-measure-on-bed]] [[nozura-wall-traps]]
