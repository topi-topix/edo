---
name: grade-transfer-cliff-and-dropped-cells
description: 設計面(graded)を地形へ写す整地の二つの罠 ── 石垣の見え面を双一次で跨ぐと外の節点が天端へ引かれる・設計面を縮めると前の巡の切盛が設計面の外に残る
metadata:
  type: project
---

2026-09-25 山王 EDO-0430(回廊の基壇の北の造成の書き直し・v15)。

1. **graded の石垣の外形のセルは天端の値(29.0)**で、見え面から約 0.9m 外(法の足)まで並ぶ。Stage1 が 1m セルを双一次で 2m 節点へ写すと、
   見え面の 0.94m 外の節点が 28.1 になり、二段築の下段(天端 25)を 2.8m 埋めた。皮はその節点を「縁の点 = 地形のまま」で残す
   (隣の升に地形の木が立って穴を開けられない)ので、皮が天端に被る 39 点になった。
   → `Graded.NodeY`: 4 隅の差が設計の最も急な法の 2 倍(1:batterCut で 2.83m)を超え、節点が高い面の多角形(impl terraces[].world)の外なら低い側を採る。
   ⚠ 高い面の判定を外すと、回廊の基壇(幅 5m・内も 28.3)の内の節点まで外へ引かれ、TW_Kairo_W の見え面の票が割れて 1 駒裏返った。
2. **設計面を縮めて流し直すと、外れたセルは Stage1 が触らない(外挿しない)ので前の巡の切土の法が残る**(東の斜面の段状の窪み −1.25〜+0.85m・9 節点)。
   → `Stage1_Grade(prevImplPath)`: 前の算出物(`git show <前のコミット>:docs/Sashizu/sanno_impl.json` を書き出す)で設計面があり、いまは無い
   区画の中の節点だけ `sanno_dem.json` へ戻す。⛔ 区画の中の設計面の外を全部 DEM へ戻さない ── 北の Ita_Keidai の足元(28.3 に 3m 切ってある)を埋める。

**How to apply:** 整地を流したら、写真の前に `drawn − DEM` を設計面の外で数え、前の巡から残った節点が無いかを見る。
関連: [[regrade-only-the-changed-block]] [[run-corners-seams-and-tiers]] [[terrace-rim-residual-is-the-ruler]]
