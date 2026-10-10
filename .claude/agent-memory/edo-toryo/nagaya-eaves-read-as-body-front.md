---
name: nagaya-eaves-read-as-body-front
description: 長屋の躯体(_kutai・材1つ)は BodyExRoof が二階の軒を落とせず、軒の 0.27 越えを「躯体の前の面が区画の線を越える」と読む。前の面は一階の帯で測る
metadata:
  type: project
---
2026-10-10 EDO-0502 第95巡(岡部 N39_1)。指図 runs[37].front は「第94巡: 躯体の前の面が区画の線を 0.27 越えていた=区域侵犯」と書いたが、
実測は一階の壁 −0.32・土台 −0.36(線の内)。+0.27 は y 19.4〜19.7(座 14.0 + 5.4)の二階の軒先。Nagaya_Omote_*_2f_kutai は材が knagayamap 一つで、
`EdoBuild.BodyExRoof` は材の名で屋根を落とせず軒まで「躯体」に入れる。N39_0 0.27・N40_x 0.33〜0.40 も同じく軒(施主裁定A で軒は越えてよい)。

How to apply: 長屋の前の面・区域侵犯は `FaceOut` / `BodySpanAlong` を躯体の底〜+2.0 の帯で測る(`FrontForGutter` の型)。高さの帯を見ずに BodyExRoof の最大を
「躯体」と名乗らない。数を受け取ったら、まず高さごとの張り出し(0.3m 帯)を刷って何の頂点かを確かめる。

同じ巡: Stage2_Perimeter は 5 秒で、Kakoi 241 駒のうち動かした N39_1 以外の 240 駒が名と位置まで書き戻し済みのプレハブと一致した(再び流して安全)。
Stage2b は 85 秒(返しの溝の地形の切りが棟の背について動く ── 退避と比べて報告)。
