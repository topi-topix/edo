---
name: backbench-residue-cleared-by-stage1
description: 岡部の BackBenchWrite の盛り残りは Stage1 から流せば消える(Stage1 は区画内を graded へ上書き)── 残る尾根は前の盛りでなく、壁の下の節点の設計値を 2m 格子が溝へ一次で描く物
metadata:
  type: project
---

2026-10-05 EDO-0502 第26巡(岡部 S1→S5 通し・全体 約10分 ── 3b が 472 秒、他は各 15 秒以内)。

- Stage1_Grade は区画内の全節点を算出物 graded へ書く(現況を読まない)⇒ 2b の BackBenchWrite の「盛るだけ」の残りは Stage1 から流せば消える。
  型の直しは要らなかった。消えたのは 10 節点だけ(門の内 4 点 −1.00・西の返し 2 点 −0.43/−0.20 ほか)。区画の外は 0。
- 西の返しの前の「尾根」はそのまま残った: 壁の下の節点(-528, 950)の設計値 20.80 と溝の節点 19.33 を 2m 格子が一次でつなぐ
  ⇒ 見え面の 0.4m 前で描かれた地表 20.10。前の盛りではない。皮の穴が返しの見え面の前の升に開いていないのが原因(3b の側)。
- 測り方: heightmap 全体を前後で .bin に落とし numpy で差 → 変わった節点の数と外接箱。DesignY(public)と SampleHeight+tp.y を並べる。

**How to apply:** 2b だけを流し直す巡が続いたら、残った盛りは S1 から流して消す(冪等)。尾根を見たら先に「その節点の DesignY と地形が同じか」を刷る。
関連: [[bench-end-slope-spills-and-3b-opposite-wall]] [[wall-toe-mound-is-grid-not-grading]]
