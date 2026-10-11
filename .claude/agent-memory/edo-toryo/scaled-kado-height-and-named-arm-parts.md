---
name: scaled-kado-height-and-named-arm-parts
description: 倍率の基壇の隅の駒は丈 0.5 刻みでしか引かれず S042(丈 1.68)が「焼いていない」と出た・指図が名指す前の巡の腕の版は面の控えが変わると辺を越える・0.25m の造成の面は焼き直しても Reload しないと古いまま
metadata:
  type: project
---

2026-10-12 EDO-0502 第114巡(岡部 角 P0 の南・P1〜P4)。

1. **症状**: 部材方が焼いた Ishigaki_Kado_90_H0400_S042 が在るのに PlaceRunKado が「隅の駒が焼いていない(要る丈 ≥ 1.68)」。
   **原因**: 隅の駒の丈は両脇の丈を 0.5 刻みに丸めた値(1.68→1.5)と 4.0〜8.0 の実寸でしか引かない。倍率 s の版は実寸 4.0·s で 0.5 に乗らない。
   **対処**: EdoBuildKado の高さ引きに「両脇の丈そのもの(0.01 刻み)」を足した。倍率の差 ≤0.02 は指図が隅の駒を名指すとき柔で通す(NamedCornerPart)。
2. **症状**: 指図が名指す Dobei_Kado_00_A226x50 / Dobei_Kado_90 を据えると腕 4.1m(局所 2.26 × ES)が 3.0〜3.8m の辺を越え、長屋 N41_5・P4 の隅へ入った。
   **原因**: 名指しは前の巡の面(c + 犬走り 0.3)で KadoArms が出した版。犬走り 0・倍率を変えると要る腕が A226x60 / A50x70 に変わる。
   **対処**: 名指しの版で受けない(算出の版を部材方へ差し戻す)。面の控えを変える巡は、部材方に焼かせる前に Stage2 を流して「部材が無い」の行を渡す。
3. 指図を上書きした直後の Stage1 は「0.25m の造成の面が古い指図から焼かれている ── 算出物の 1m で造成」と ⚠ を出して**そのまま全面を 1m で造成する**。
   `impl_okabe.py --graded-bin`(77 秒)を焼いた後も `_graded` が静的に残る ⇒ `EdoOkabeYashikiBuilder.Reload()` を呼んでから流し直す。

**How to apply:** Stage1 の 1 行目の ⚠ を必ず読む。名指しの部材は据える前に腕の実寸を辺の長さと比べる。
関連: [[impl-fingerprint-after-yat-overwrite]] [[kado-arm-overruns-short-edge]] [[concave-corner-wall-behind-nagaya-back]]
