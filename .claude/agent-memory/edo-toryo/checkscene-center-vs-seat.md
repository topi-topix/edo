---
name: checkscene-center-vs-seat
description: EdoSashizuExport.CheckScene measures 附属屋 against the rect CENTER, so any part seated by `seat` reports a permanent false mismatch
metadata:
  type: project
---

`EdoSashizuExport.CheckScene` の附属屋の照合は、実装位置を
**矩形の芯 `((u0+u1)/2, (v0+v1)/2)`** と比べる(EdoSashizuExport.cs の `service` ループ)。
`seat`(面で納める)で据えた部材は**設計上わざと芯から逃げる**ので、
検査は**永久に消えない差**を鳴らす。

- **実例(松江松平 2026-09-16)**: 稲荷社 `service.Inari`。指図は背面を矩形の東面から
  `gap` 0.45m 離して据えよと書き、`_seat` に「⛔ ピボットを矩形の中心にも参道の終点にも置かない」
  と明記。据え付けの実測は gap 0.450m(許容 ±0.05)で ⭕ なのに、
  突き合わせは「Inari が 0.57m ずれている」と鳴る。
  0.57m は従属値で説明が付く: `(u1 - (gap + |zLocal.min|)/1.818) - (u0+u1)/2` = 0.3124 間 = **0.568m**。
- ⛔ **芯へ動かして 0 件にしない** — 指図の明記と CLAUDE.md 規則5(中心で合わせない)に反する。

**Why:** 「突き合わせ 0 件」を目的にすると、検査を満たすために設計を壊す方向へ手が動く。
0 件は緩い条件の証拠でしかない(既存メモリ `check-must-name-what-it-measures` と同じ型)。
**How to apply:** `seat` を持つ部材が「ずれている」と鳴ったら、まず逃げの量が
`seat.gap` と `buhin.zLocal` から再現できるか計算する。再現できたら実装は正しく、
直すべきは**汎用検査の側**(全邸に効くので棟梁の一存では変えない → 呼び出し元へ差し戻す)。
