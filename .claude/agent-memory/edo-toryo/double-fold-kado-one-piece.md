---
name: double-fold-kado-one-piece
description: 1m 未満で続く出隅二つは PlaceRunCorners の前段で一つの駒(PlaceRunKado2)に据える・中の区間の駒は一つで両隣の折れの外まで張り出している(岡部 TW_Kado_Shumen P4/P5 2026-10-03 EDO-0502)
metadata:
  type: project
---

- 中の区間(0.636)には直線材が 1 駒(2.0m)しか無く、両端の外へ 0.68 ずつ張り出す。素の隅を折れ 1 に据えると、PlaceRunKado の
  「端の駒を兼ねる」でその 1 駒が消え、折れ 2 は「駒の並びが無い」で黙って飛ぶ(DebugCorners でしか出ない)。
- 一体の駒は P = 折れ 1 の両脇の控えの交点・yaw = 局所 −X を中の区間の見え面へ。折れ 1 がどちらかは局所 −Z が折れ 2 へ向く側で決まる
  (両巡りを試して ⛔ で振り分ける)。名の度は折れ 1→2 の順(43_37)。
- 丈 4.5 の直線材(IshigakiChoku)と混ぜると、隅の丈は三本の直線材の実の底から丸めて引く(PlaceRunKado の nbH と同じ)。

**Why:** 二つ据えると腕が重なり、一つだと折れ 2 が抜けたまま「隅 1 駒」と報告されていた。
**How to apply:** 隅の駒数が折れの数より少ないときは「駒の並びが無い」を疑う。関連 [[run-corners-seams-and-tiers]] [[kado-arm-overruns-short-edge]]
