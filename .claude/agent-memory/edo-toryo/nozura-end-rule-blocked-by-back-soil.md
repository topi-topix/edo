---
name: nozura-end-rule-blocked-by-back-soil
description: 野面の端の納め(nozuraEndRule)は岡部では背の土が天端より高い端が多く、延ばしも見切り石も硬い埋没で退く・端の見付は端の一点でなく駒の走りで測る
metadata:
  type: project
---
2026-10-06 EDO-0502 第30巡。EdoBuild.NozuraEndRule(PlaceNozuraNet の endRule)を入れて岡部 Stage2b を4回流した。

1. 端の見付を端の一点で測ると坂の端で −0.18 と読む → 打ち切りへ回した端が駒の奥で 1.20 を残し直線の駒へ逃げた。
   **端の駒が受け持つ走り(内へ 1.2W)で PlaceNozuraRun の needH と同じ測り**(天端は中ほど・足元は線の前 0.25/0.7 の最小)で取る。
2. 延ばす先の背の地盤が端の天端より高い(土の斜面へ入る)端は、延ばすと打ち切りの駒の先が 0.8〜2.2m 土に埋まり(SoilSideCrestShort)直線の駒へ戻る。
   延ばす前に「背 > 天端 + 0.05 で止める」を入れた。
3. 見切り石は頭を天端に揃えるが、端の背の土が天端より 0.14〜0.33 高い端(TW_Kita_Koshi_3_0 端1・辺28北端の両端・辺24 端0・辺4〜5 端0)では
   PlaceNozuraMikiri の埋没の関門が退け、直線の駒で終わる。**型では解けない ── 天端か背の土(設計)の話**。普請方へ戻す。

**How to apply:** 端の納めを触る巡は、流す前に各自由端の「背の地盤 − 天端」を刷る。正なら納めの型を直す前に普請方へ。
関連: [[short-return-tie-and-sode-extent]] [[nozura-wall-traps]]
