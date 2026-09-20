---
name: one-part-for-drop0-and-drop30
description: 縁石は天端を揃え下に隠れる丈を変えれば落差0と落差0.30を一つの型で賄える。Kirishi の 0.44 タイルを縁石に流用しない
metadata:
  type: project
---

2026-09-20 松江松平の切石の縁石(`Own.Fuchiishi`)。

- ⭕ **落差の違う縁を一つの型で賄う筋** — **天端を揃え、下に隠れる丈を変える**。
  天端 Y=0・躯体 Y −0.48(最大落差 0.30 + 根入れ 0.18)固定で焼き、出るか隠れるかは
  **据える側の地盤**が決める。⇒ 落差 0 の縁も落差 0.30 の縁も同じ FBX。
- ⛔ **落差が 0 でも縁石を省かない。**役目は『白洲の砂利を留める』ことで、落差の有無とは別
  (指図 `_fuchi` の但し書き)。
- ⚠ `Kirishi` のタイルは **1.05m**。⛔ `build_sanno_buzai.KIRISHI_TILE` 0.44 を縁石へ流用しない
  (normal の 2×2 の継ぎ目が 0.22m ごとに立って**小口積みの壁**に見える)。
- ⚠ 縁石の FBX は **`Assets/Edo/Models/Fuchi/`**。`EdoMatsudairaDewaBuilder.RemapFuzokuya` の
  `modelDirs` にこのフォルダを足してある(⛔ 足し忘れると真っ白)。材は donorDirs の
  `Assets/Edo/Materials` が**再帰的に** `Materials/Sanno/Kirishi.mat` を拾う。

**Why:** 部材を落差ごとに焼き分けると、落差が従属値である限り無限に増える。
**How to apply:** 「寸法の違いが**据える高さ**だけで吸えるか」をまず疑う。
関連 [[kirishi-tile-and-shu-material]]
