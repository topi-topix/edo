---
name: dobei-kado-batch-meta-clone
description: 練塀の隅を何十本もまとめて焼くときは整数角で焼き、既存 Dobei_Kado の .meta を guid だけ替えて写すと remap 済みで入る
metadata:
  type: project
---

2026-10-03・岡部の新区画で練塀の隅 23 本を一度に焼いた(EDO-0502)。1 本 5 秒。

**事実:** `Dobei_Kado_*.fbx.meta` は guid 以外すべて同一(externalObjects で `s_heimap` を remap 済み)。
新しい FBX へ guid だけ uuid4 に替えて写せば、Unity で remap メニューを回さずに材が付く。
名は `round(|deg|)` なので、同じ名に丸まる二隅(38.51 と 39.09)は**整数角で焼く**と残差が両側 ≤0.5° に収まる。

**Why:** 隅は区画の実測(`EdoBuild.KadoDeg`)から名を引くので、区画を引き直すたびに角が一斉に変わる。
**How to apply:** 角の一覧は impl の deg を信じず parcels.json の多角形から KadoDeg と同じ式で再計算して名を出す。
1° 前後の浅い角も留めは成り立つ(00/01 が既に据わっている)。[[kado-plus-minus-not-exact-mirror]]
