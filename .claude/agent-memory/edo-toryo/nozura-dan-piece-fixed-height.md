---
name: nozura-dan-piece-fixed-height
description: 野面の段の境の駒(*_dan)は H1.50 しか焼いておらず、走りに沿って地盤が下がる袖では継ぎ目の下が抜ける。直線の駒は needH で H4.8 まで選ぶので抜けない。EdoBuild.StackDownAtNozuraSteps で積み下ろす
metadata:
  type: project
---

2026-10-04 EDO-0502 第11巡(岡部 TW_Kado_Sode)。

症状: 縁の皮の検査が「C 面の外の取り合い TW_Kado_Sode_2_0_dan 小口 1.42m」。駒の一覧を刷ると直線の駒(*_016f ほか)は H4800 で底 14.5〜16.0 と深く、
段の境の駒だけ Sanno_Nozura_H1500_G±220 で底 18.32・足元 16.54。
原因: PlaceNozuraRun の段の境は `mid - 1.5` に固定の丈の駒を一つ据えるだけで、見付(needH)を測らない。
対処: `EdoBuild.StackDownAtNozuraSteps`(EdoBuildDanIshigaki.cs)── 段の境の駒の下へ**同じ駒**(同じ FBX)を積み、筋ごとの「上の底 − 下の頭」の最大だけ上げる。
⚠ 初手で平らな直線の駒(勾配0)を積んだら、勾配の駒は**底も勾配**(1間で 0.35m)なので継ぎ目に楔の黒い口が開いた ── 底の筋を刷ってから積む駒を選ぶ。
「小口」の点の隙の行は駒の一覧(RB の min・焼いた FBX 名)を刷れば 1 回で原因の駒が分かる。

**How to apply:** 野面の段違いで抜けを言われたら、まず *_dan の FBX と底を刷る。山王の野面の段の境(呼んでいない)も同じ型が当たる。
関連 [[foot-bottom-batter-and-stair-front]] [[nozura-wall-traps]]
