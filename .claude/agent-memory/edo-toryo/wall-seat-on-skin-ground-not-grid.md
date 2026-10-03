---
name: wall-seat-on-skin-ground-not-grid
description: 皮を足す邸では段の土留めの駒を「皮が描く地表」(平らな面の高さ・graded)で据える。2m 格子の盛りに載せたまま皮で盛りを削ると駒が 0.5m 浮き、三角の土の足が覗く
metadata:
  type: project
---

2026-10-03 EDO-0502 第5巡(岡部 Stage3b 縁の皮を新設)。Stage2b は駒を `EdoBuild.Ground`(2m 格子)で据えていた ⇒ 見え面の足元の
盛り(最大 1.77m)に駒の底が載ったまま。皮が足元を面の高さ(門の内 16.5)まで削ると、門の内の石垣の下に隙と三角の土の足が並んだ(近景で一目)。
対処: Stage2b の ground を `SkinGround`(平らな面の中は面の y・外は min(graded, 地形))に替え、皮と同じ地表で据える。
⇒ 正直な浮きが出る: TW_Kado_Shumen は見付 4.42〜4.50 > 城の石垣の駒 4.0 で底が 0.5m 上(盛りが隠していた)── 二段築の下段は 0.5 では建たず、
丈 4.5 の駒(部材)が要る。

**Why:** 皮は「描く地表」を変える。駒を据えた地表と皮の地表が違えば、片方を直すたびに浮き/埋没が入れ替わる。
**How to apply:** 皮を新しく足す邸では、まず土留めの据えの ground を皮の地表へ揃えてから皮を流す。順は 1→2→2b→3→3b(皮)→4→5。
3b は約5分(execute_code は必ずタイムアウトする・印のファイルで再送を止める)。
関連 [[wall-toe-mound-is-grid-not-grading]] [[long-run-guard-and-soft-only-converge]]
