---
name: dobei-kiri-hand-and-radian
description: 端を切った練塀の駒は +Z=外・+X=切る端なので、一つの手では run の片方の端にしか据わらない(岡部 849_L は SE_Hei の始めで手が逆)・Atan2 は既にラジアン(2026-10-03 EDO-0502)
metadata:
  type: project
---

- `Dobei_Kiri_*_L` は局所 +Z = 見え面(外)・+X = 切る端・体は −X。外向きを固定すると +X は区画の巡りの一方向に決まる ⇒
  同じ手の駒は「辺の始め」か「辺の終わり」の片方にしか合わない。岡部では 255_L(S_Hei_21 の終わり)は合い、849_L(SE_Hei の始め)は
  逆の手が要る(据えると体が区画の外へ 3.07m 出た)。KiriEnd が局所 +X と角の向きの内積で検めて退ける。
- 自分の踏んだ罠: `Mathf.Atan2(...) * Mathf.Deg2Rad` と二重に掛けて手の検めが素通りした。Atan2 はラジアンを返す。

**Why:** 部材方の明細は「どちらも _L」で、手の違いは据えてみるまで分からなかった。
**How to apply:** 新しい端の駒は据える前に局所軸と run の巡りで手を検める。手が逆なら部材方へ鏡像を頼む(鏡像の綴りは未定)。
関連 [[ownpath-float-suffix-and-destroy-before-place]] [[free-run-end-at-oblique-parcel-corner]]
