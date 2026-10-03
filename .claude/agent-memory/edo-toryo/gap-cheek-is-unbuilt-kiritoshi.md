---
name: gap-cheek-is-unbuilt-kiritoshi
description: 石垣の口の石段の奥の「土の壁」は口の端の位置ではなく、表の坂(profS だけで profY の無い ramp)の路盤を誰も均していなかったのが正体。返しの向きは地表で測ると裏返る
metadata:
  type: project
---

2026-10-04 EDO-0502 第8巡(岡部 TW_Kado_Shumen × K_Dan1 / R_OmoteZaka)。

症状: 見付 4.5m の石垣の口に 1m の石段。石段の奥と脇に高さ 2.25m の土の壁。見立ては「口の端が紙の値・石段が後の Stage」だったが、
測ると石段は紙の口より広く(口 [4.56,10.37]・石段の実面 [4.54,11.82])、隙は無かった。
原因: ① GradeRamps は `profY` の無い坂を「算出物の造成で受ける」として飛ばし、算出物 graded にも表の坂が入っていなかった
(石段の奥 t=0→2m で 17.1→21.0)。② 指図 `ramps[].kiritoshi`(切通しの石垣)を読む所がどこにも無かった。
対処: `ProfSNodes` で profS(同じ s の二つの高さ = 石段の平面 a→b の両端)から芯の節点を起こして GradeSaka で均す。
口は石段が狭い端だけ石段の面へ詰める(`EdoBuild.GapFromPieces`)。返しは `GapReturnLine`+CrestWall(`lowForce`)。

罠: 返しの低い側を `LowSide`(地表)で測ると、返しの裏 = 本体の石垣の法の下の方が低く出て**見え面が裏返る** ── 口の内と決まっている物は lowForce。
返しを runEnds に入れると、口の端と本体の隅が 1m 未満なので二重折れの隅に化けて既存の隅が消える ── 入れない。

**How to apply:** 「口の脇・奥に土」が出たら、まず口の床(graded)が指図の縦断どおりか測る。⚠ 役の門番は `sleep` の見張りを止める ── 長い流しは印+結果ファイルで投げて ls で覗く。
関連: [[run-end-at-opening]] [[long-run-guard-and-soft-only-converge]]
