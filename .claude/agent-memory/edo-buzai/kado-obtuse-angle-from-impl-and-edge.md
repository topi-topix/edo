---
name: kado-obtuse-angle-from-impl-and-edge
description: 返しの出隅の折れ角は scene でなく impl の線と区画の辺の向きから出せる・100° 超の石垣の隅は名が 3 桁(2026-10-05 EDO-0502)
metadata:
  type: project
---

- ReturnAlongBack の返しは棟の辺(parcels の辺 e)に平行 ⇒ 折れ = impl terraceWalls の線の向きと辺の向きの角(TW_Kado_Hokuto × N39_1 = 100.212°)。Unity を待たずに焼ける。
- 張り出し 2.4·tan(Δ/2) = 2.87 で n_neg は自動で 2。名は `Ishigaki_Kado_100_H0400`("00" 書式でも 3 桁)。.meta は 95 のを guid だけ替えて写す。
- Unity が他役の手の内なら BUZAI_OUT / BUZAI_SHOTS を staging へ向けて焼く。

**Why:** 棟梁が Unity を握っている間に隅の駒の欠けを埋めるため。
**How to apply:** 別の返しの隅も同じ算で角を出す。関連 [[ishigaki-kado-tall-90]] [[castle-wall-kiri-and-short-arm]]
