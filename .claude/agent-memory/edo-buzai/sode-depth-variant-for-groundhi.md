---
name: sode-depth-variant-for-groundhi
description: 袖を背の地盤まで上げる切通しは丈違い(_D3.20)で受ける・透塀の割り付けは C# が算出物の segs を round して ±2mm で探す
metadata:
  type: project
---

2026-09-24 EDO-0430。上げの上限 = 丈 − 笠の上がり 0.30 − 段石の根入れ 0.48(2.20 ⇒ 1.42)。女坂の要る上げ 2.08 に `--depth=3.20`(上限 2.42)を焼いた。
留めの段(2・38〜40)の丈違いは**留めの駒も丈違いが要る**(据え手は平らな駒の transform のまま差し替えるので、2.20 の留めに替えると下が浮く)。
`PlaceIshidanSode` も `MiterPath` も丈を選ぶ口を持たない(棟梁の仕事)。女坂の袖は野面ではなく**切石 `IshidanSode`** が据わっている ── 指示が「野面」でも隣に合わせる。

**Why:** 指示の型の名(野面・F-1.86)と、実際に据わっている型・綴りが食い違っていた。
**How to apply:** 焼く前に使い手の C#(`EdoSannoShaRebuild.Sukibei`/`Stage2_Kaidan`)が引く関数と丸めを読む。透塀は算出物 `sanno_impl.json` の segs を round(L/1.818) 等分・mm は round・±2mm 探索。関連 [[sukibei-roster-needs-derive-gaps]] [[ishidan-sode-sheared-module]]
