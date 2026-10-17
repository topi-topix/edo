---
name: r155-off-heiline-dobei-sinks-and-unread-fields
description: 岡部 第155巡 — 天端の線の外の練塀(N_Hei_39)は床へ沈み台の中へ 0.7〜1.1 埋まる・runs の steps 文は読まれず seatBreakS だけが段・線の上の塀は runs の seat1 でなく tenba の値+一続きの上げ・野面石の背の腰は読む型が無い
metadata:
  type: project
---
2026-10-17 EDO-0502 第155巡(案1 の S1→S2 だけ)。

1. **天端の線(const.heiLine.trial)に入らない辺の練塀**(辺39 の N_Hei_39)は SeatHeiOnBed の SinkGroupToBed を通る。犬走りへ寄せて塀が台の天端の奥へ出ると
   床 = 内の地面 16.5 になり、台(天端 17.2〜17.6)の中へ 0.93 沈んだ。ログは「練塀・隅を床へ据えた ... 最も下げた -0.93m」の一行だけ。
2. **runs[].steps の文は段にならない**。Runs が段として読むのは seatBreakS だけ。無ければ seat0→seat1 の一直線 ⇒ 台は 1.8m ごとに 0.2 ずつの段で写る。
3. **線の上の塀(N_Hei_35)は runs の seat0/seat1 を読まない** ── tenba.N の「辺の始まりの座…終 x」と seatOverGround の一続きの平行上げ(他の辺の不足で +0.29)で決まる。
   欄の seat1 だけ書き換えても頂点で隣の塀と合わない(18.06 / 17.7)。差し戻す先は tenba.N の値。
4. 野面石の背の腰(N18_a・N40_0 の back「野面石の腰 天端 x」)を据える型は無い。RunBackBands の二書式は帯と擦り付けだけ。
5. 腰の刺さりの測り = 座 − max(線上・外0.5・外1.0 の地形)を 0.25 ごと(普請方の線際の定義に揃える)。前の溝を持つ棟は S3d の前に測っても負になる(溝が無い)。

**How to apply:** 欄の上書きで新しい塀・段が来たら、まず流す前に「heiLine の trial に入るか」「段が seatBreakS か文か」を見る。測りの型は scratchpad r155(koshi_s2)。
関連 [[r154-front-ditch-needs-parts-and-floor-in-ditch]] [[heiline-tenba-spec-r121]] [[return-lost-when-sashizu-text-format-changes]]
