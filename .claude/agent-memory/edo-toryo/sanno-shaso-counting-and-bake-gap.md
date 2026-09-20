---
name: sanno-shaso-counting-and-bake-gap
description: 山王の社叢 — 突き合わせの足し算が入れ物を決めてしまう / 焼き出しの一本立ち7点は part が "{size}" のまま
metadata:
  type: project
---

**① 突き合わせの足し算が「どの入れ物に置くか」を決めている。**
`EdoSannoSashizuCheck` は `wantTree + wantDetail == gotGo + gotTerrain` で数える。
`gotGo` は `SHASO_GROUPS`(`Keidairin` / `Keidai/Trees`)の**直の子だけ**、`gotTerrain` は
焼き出しの外接矩形に入る **Terrain の tree instance** だけ。⇒
- `place=DetailMesh` の 916 本を本物の詳細メッシュで撒くと**どちらにも数えられず**必ず1件鳴る
  (詳細メッシュは密度の升目で点の座標を持てないので、焼き出しの点を活かすなら GameObject が正)。
- `place=GameObject` の名指し 20 本は **SHASO_GROUPS の外**(`Keidai/Meiboku`)へ置く。
  中に入れると 20 本ぶん多く出る。
- 旧 `Keidairin` は `SetActive(false)` だけでは数から消えない(active を見ていない)。
  **群ごと `Kyu_Shaso` の下へ移す**。竹 `Bam_*` の検査も同じ理由で群を見ている。

**② 焼き出し `planting.points` の一本立ち 7 点は `part` が `Own.Matsu("{size}")` の差し込みのまま・
`size` の欄も null。** ⇒ 同じ点の `prefab`(`Tree_<族>_<丈>[_NN]`)から丈と個体を読む。
⛔ 丈を発明しない・⛔ `prefab` からパスを組まない(解いた丈を `EdoAssets.Own.*` へ渡す)。
**Why:** 指図方の焼き出しの綻び。直すのは生成器の側だが、実装は `prefab` の欄で解ける。

**How to apply:** 山王の社叢を触るときに先に読む。関連 [[checkscene-center-vs-seat]]
