---
name: wall-toe-mound-is-grid-not-grading
description: 段の石垣の見え面の前の盛り上がり(1〜3m)は 2m 格子の描きの限界で、造成で節点を下げても消えない(模擬で前 1.5〜2.0m・裏の凹み 1〜2m)。解くのは縁の皮(CutEdgeSkin)
metadata:
  type: project
---

2026-10-03 EDO-0502 第4巡(岡部 TW_Kado_Hokuto/Shumen/Higashi_Tsuyo)。依頼は「壁の線の下の面側の格子点を下の面の高さへ」だった。
算出物 graded(1m)は線から 1m で段が切れていて正しい。盛りは**地形の 2m 格子**: 城の石垣の駒は線から 見え面の足 −0.75・天端の背 +1.40 の
幅 2.15m しかなく、上の面の節点が線の近くに落ちると、隣の下の節点(最大 2m 先)まで一次で描かれて足の前が盛り上がる。
python で節点を「線の下側=下の面・上側=上の面」に割る模擬: 前の盛り 最大 1.99m(割る位置を +0.33 にずらすと前 1.42 / 背の凹み 1.63)── どこで割っても片方が残る。

**Why:** 造成の直しを書いても検査の数が変わらず、巡を一つ無駄にする。
**How to apply:** 段の土留めの足元の盛り・天端の背の凹みは「描き」の話 ── `EdoBuild.CutEdgeSkin`(山王 Stage9 の型)を邸に足す。
造成の節点をいじる前に、駒の実メッシュの線からの幅(足〜背)と格子 2m を比べる(幅 < 格子×1.5 なら造成では解けない)。
関連 [[terrain-holes-and-skin-traps]] [[unity-kill-leaves-holes-without-skin]] [[wall-foot-ridge-from-nodes-under-hull]]
