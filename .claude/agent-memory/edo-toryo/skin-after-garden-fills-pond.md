---
name: skin-after-garden-fills-pond
description: 縁の皮(CutEdgeSkin)を庭の土工の後に流すと池・築山を「面から外れた升」と読み面の高さで埋める。faceKeepOut で外す。印の名は巡ごとに替える
metadata:
  type: project
---

2026-10-04 EDO-0533 土井 第6巡。

1. 症状: 6奥庭(池を掘る)の後に 4b 縁の皮を流し直したら穴 558→804 升・「元の地形から下げ 1.80m」が庭の中に出た。
   原因: CutEdgeSkin は面の多角形の中で地形が face.y から faceTol を超えて外れる升(と縁の線の帯 bandCells)を皆「面の縁」と読み、皮を面の高さで張る。庭が面の上にあると池を埋め築山を削る。
   対処: `EdoBuild.CutEdgeSkin(..., faceKeepOut: 庭の土工の矩形)` を足した(面の縁の升・帯の両方から外す)。土井は Stage4b が NiwaModel の矩形を渡す。⚠ 皮が芝のスプラットを消した升(726)は戻らない。
2. 症状: 同じセッションの前の巡で使った印のファイル(open_doi.mark)が scratchpad に残っていて、初回から resend-skip が返った。
   対処: 印の名に巡の札を付ける(r6_open.mark など)。返り値が resend-skip なら開く前に .txt を見る。

**How to apply:** 面の上に庭を掘る邸(岡部・松江松平の庭も)で皮を流すときは庭の区域を faceKeepOut に渡す。印は巡ごとに名を替える。
関連: [[long-run-guard-and-soft-only-converge]] [[terrain-holes-and-skin-traps]]
