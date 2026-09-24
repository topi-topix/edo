---
name: backfill-skin-needs-three-limits
description: 裏込めの皮(CutEdgeSkin の backfill)は山王で退役(施主側の決め 2026-09-25)。原因は殻の石垣の見え面で底を天端と取り違えた測り違い — 隙は盛らずに測りを直して消えた
metadata:
  type: project
---

2026-09-25 山王 EDO-0430。`EdoBuildHifu.cs` の 2d 裏込め(backfill > 0)は **Stage9 では backfill: 0 に戻した**
(普請奉行の決め: 石垣の継ぎ目から草の筋・回廊の北東の隅の楔・東の縞・突き合わせ 2→5)。関数は残っている。

**本当の原因は測り違い。** 城の石垣の駒(CastleWall)は底の面の無い殻で、見え面の片側が鉛直。鉛直な面は平面に
面積が無いので `TopIndex.Bottom`(縦の線と三角形の交わり)に掛からず、見え面の脇の底が**天端**に化けた。
⇒ 「底 > 面 + 0.30 の駒が浮く」3,243 点・隙 4,510 点の大半が偽物で、裏込めはその偽の底まで土を盛っていた。
対処: `TopIndex.WallBottom(x, z, r, who)` — r 以内を通る鉛直な面のその位置の下の縁を底に数える(同じ駒に限る)。
MeasureSkin・SkinGapTable・床(floor)・sealFace で使う。隙 4,510 → 15。

残す: 面の縁を多角形の線で切る(design)・面の検査で部材の外形の中を外す・sealFace(面の中で底が面+許容以内なら底まで上げる)。

**How to apply:** 「駒が浮く」「背の隙」が大量に出たら、盛る前に殻の駒の鉛直な面を底に数えているか検める。
試しの度に地形の資産は scratchpad の退避(裏込め前の hifu_bak)から戻して打つ(芝の削除が積もる)。
関連: [[terrain-holes-and-skin-traps]] [[dig-to-unbury-cascades]] [[measure-dont-nudge]]
