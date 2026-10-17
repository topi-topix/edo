---
name: okabe-dan-kado-angles-and-deep-nozura-kado
description: 段の土留めの出隅は impl の線から正確な折れ角を出して焼く(名は丸め)・野面の隅 H4.8 は make_kado に深い型を渡す・番所付きの門長屋は名が変わらない(2026-10-03 EDO-0502)
metadata:
  type: project
---

- `PlaceRunCorners` は駒の見え面から測った角を `Mathf.Round` して `IshigakiKado(deg,h)` を引く。⇒ `okabe_impl.json` の terraceWalls の線から折れ角を小数まで出し(40.219/42.504/36.693)、`--deg` に小数のまま渡す(名は丸めた 40/43/37)。整数で焼くと腕の先 2m で 0.5°=1.7cm、tol 0.02 すれすれ。
- 野面の隅 `make_kado` は `kado_layout(v)` 固定で H2.40 までしか石が無かった ⇒ h+BURY > DEEP のときだけ深い型。継ぎ目は直線の H4.8 と全高で頂点一致(424 点・差 0)。`PlaceNozuraNet` は折れ 60° 以上なら 90° の駒を据えるので、86.6° の隅は腕の先で約 5cm ずれる。
- `--bansho` は FBX 名を変えない(`..._mon12.18_2f_kutai` のまま上書き)。門口は旧版と頂点まで同じ(2mm で外れる旧頂点 2・増えたのは出格子 258)。

**Why:** 岡部の段の石垣の出隅 3 と東の野面の隅 2 が「焼いていない」で開いていた。
**How to apply:** 別の邸の土留めの出隅も impl の線から角を出す。野面の隅を 2.4 より深く焼くときは同じ道。関連 [[ishigaki-kado-tall-90]] [[nozura-deep-layout-shared-rng]] [[nagaya-body-length-and-goten-root-offset]]
