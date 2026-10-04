---
name: sode-back-bench-cap-conflict
description: 袖の背の小段(天端を背の法で0.5刻み切り上げ・run内の下がり≤0.5)は run の下手の端で盛りが最大≈1.0要り、盛りの上限0.6と天端−背≤0.3が同時に満たせない ── 格子を細かくしても0.42のまま
metadata:
  type: project
---

2026-10-04 EDO-0502 第13巡 岡部 TW_Kado_Sode。指図 top/backfill を EdoBuild.RunsByBackSlope/BackBenchAt で入れた。
見える背の口は 15 → 0 になったが、天端−背の描かれた地盤は最大 0.42(硬 ≤0.30)。外れは全部 run の**下手の端**(s≈0.1)。
原因は皮の分解能ではなかった: 設計の格子を 1m → 0.5 → 0.25m に割っても 0.43 → 0.43 → 0.42。
そこは設計面が 18.60 で、狙い 19.39 に対して盛りの上限 0.6 で 19.20 止まり(切り上げ ≤0.5 + run 内の下がり ≤0.5 ⇒ 要る盛りは最大 ≈1.0)。

**How to apply:** 硬い条件が二つある小段・裏込めは、流す前に「要る盛り = 天端 − drop − 設計面」の最大を上限と突き合わせる。
衝突は指図の数(刻み・下がり・上限)の話なので普請奉行へ返す。皮の格子を割っても直らない。
関連: [[wall-toe-mound-is-grid-not-grading]] [[skin-gap-table-reruns-and-lost-scene]]
