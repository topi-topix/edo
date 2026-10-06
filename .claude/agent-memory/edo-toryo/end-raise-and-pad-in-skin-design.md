---
name: end-raise-and-pad-in-skin-design
description: 岡部 endRaise は 1.82m で tallEnd に回り隅の駒+返しになる・皮の設計の地盤へ棟の下の均しを写すと厩/米蔵は下がるが薪蔵と厩の隅は地形の節点の上書きで残る・Stage3b が 58 分かかった
metadata:
  type: project
---
2026-10-06 EDO-0502 第37巡。

1. endRaise(TW_Kita_Koshi_3_0 の終わり)は背 > 22.95 が端から 0.50m で始まり、狙い一間〜二間の外 ⇒ 1.82m(⚠)。
   上げた端の見付 2.50 > 2.4 で tallEnd が先に効き、上げた run は**隅の駒 1 つ + 返し 3.75m + 見切り石**になった(直線の駒 0)。
   段違いの駒(_dan)と積み下ろし(_dan_tsumi0)は従前の型が自動で付く。切る小段(koshiEnd)は raisedSegs で外した。
2. 皮の設計の地盤へ ServicePads を LevelPadAt(升 = 皮の格子 0.25)で写した ⇒ Drawn: 厩 −0.133→−0.053・米蔵 −0.062→−0.028。
   残り(地形で同じ値): 薪蔵 −0.096 は米蔵 15.77 の均しが共有の節点 (-396,1026) を上書き(高い棟が勝つ設計の帰結)・
   厩の北東の隅 −0.078 は (-398,1062)〜(-396,1064) の節点が 16.27〜16.31 ── 均しの後の別の書き手(東の縁の何か・未特定)。
3. Stage3b は 3478 秒(前の巡 627)。CPU 1 本・RSS 0.3〜0.5GB(スワップ)・main thread は大きな配列の確保と GC。原因は未特定 ──
   次に流すときは前に `BackBenchAt` の keepOut を幾何の棄却の後へ回す・`LevelPadAt` の PIP を窓の後へ回す(どちらも結果は不変)。

**How to apply:** 附属屋の埋没が残ったら、まず地形の 2m 節点を刷って「誰がその節点を書いたか」を見る(皮の側ではない)。
関連 [[levelpad-rim-and-skin-hides-terrain]] [[koshi-end-cut-exceeds-on-1to1-slope]] [[nozura-end-rule-blocked-by-back-soil]]
