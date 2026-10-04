---
name: gate-back-abut-through-passage-and-steps-on-graded-ramp
description: 門の背へ突き付ける土留めの端は光線だと門の口を抜けて扉まで伸びる・2m格子の坂へ石段を据えると段の差が割れる/踏面に土が被る
metadata:
  type: project
---

**① 門の背へ突き付ける野面の端**(土井 TW_Nozura_Tomomachi・2026-10-04)
- 症状: PlaceNozuraNet の pool に表門を渡すと端が s=-2.74(線より 2.7m 門の側)へ伸び、駒が門の口を通って扉の裏まで入った。
- 原因: 線(u=9.5)が潜戸の口(u9.65〜10.14)に重なり、口の下(敷居 21.9 より下)は通り抜けで背の面の実体が無い。光線は口を抜けて扉に当たる。
- 対処: 端は**札の背の面**(EdoPartSpec spec.back)で線を切り、pool に門を入れない(EdoDoiBuilder.Dan.cs Stage4a_Dodome)。隙は札の面からの符号付き離れで測る。

**② 2m 格子の坂に段石**(土井 K_Kura1)
- SlopeSteps(天端を地表へ・等間隔)は段の差 0.45/0.17/0.21/0.24 に割れる。踏面の芯を「地表 = 天端」の点へ当てると踏面の背に土が 0.31 被る。
- 踏面の**坂上の端**を地表 = 天端 −0.05 の点へ当てる(EdoBuild.SlopeStepsAt)と段の差は欄どおり。ただし坂が横にも傾く(0.26m/間)ので片端が浮き・片端に土が被る(0.14)── 皮の巡の話。

**③ scratchpad の印のファイル名は窓と共有** — `s3_run1.txt` が呼び出し元の古い結果で、Stage3 が走らずに「ALREADY」を返した。印の名には `toryo_<仕事>_` を頭に付ける。

関連: [[long-run-guard-and-soft-only-converge]] [[contact-must-use-drawn-surface]]
