---
name: double-kado-and-nagaya-miter
description: 近い出隅二つは背の間が負になる(二重折れの隅)・PlaceRunKado の +X の腕は Δ≠90 で向きが誤り・表長屋の外へ折れる角は妻を剪断で留める(2026-10-03 EDO-0502)
metadata:
  type: project
---

- 出隅の背の交点 P は天端の前の縁の折れ点より**各腕の奥へ** 1.4·tan(Δ/2) 入る ⇒ 腕 = 線の区間長 − 1.4·tan(Δ/2)。岡部 P1 の #1 は 0.703 なので腕 0.19(1.22 と取り違えかけた)。天端で 0.636 離れた 42.5°/36.7° は背の間が −0.372 ⇒ `build_kado.py --deg2`(三本の帯を「控え e 最大の壁が持つ」で分け、B/C は背で第三の留め面 e_B=e_C で継ぐ)。継ぎの小口は帯から消してから切る・T 字は割る・負の腕は小口の背の帯を第三の留め面へ剪断して貼る。
- `EdoBuild.PlaceRunKado` の armZ = 局所 +X は Δ=90 のときだけ正しい(正: 局所 (sinΔ, cosΔ))。40° の隅の「見え面の差 −1.40・口 −2.09」はこれ。修正案は staging/buzai4/EdoBuildKado_armZ.diff(未適用・Assets は触っていない)。
- 表長屋の角(外へ θ 折れる)は `build_nagaya_omote.py --miter θL θR`: x' = x ± w·(0.30 − z)·tan(θ/2)(w は芯 0→端 1・軸 = 区画の線)。並べて隙 0・斜めの光線 0。直線の光線は妻壁の板に平行で抜ける(偽陽性・直角でも 93 本)。

**Why:** 岡部 第4巡の隅 3 件(二重折れ・40° の腕・表長屋の楔)。
**How to apply:** 近い折れは --deg2、短い区間の腕は線から上の式で。長屋の角は --miter を run の両端の折れで焼く。関連 [[okabe-dan-kado-angles-and-deep-nozura-kado]] [[castle-wall-kiri-and-short-arm]] [[nagaya-body-length-and-goten-root-offset]]
