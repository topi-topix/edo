---
name: unity-kill-leaves-holes-without-skin
description: 縁の皮を流した後に保存せず Unity を落とすと、地形の穴だけ残り皮の参照が消えた資産を指す ⇒ 次の Stage9 が空の皮を焼く(2026-09-27 山王)
metadata:
  type: project
---

2026-09-27 EDO-0437: 13:58 に Stage9(縁の皮)を流した後、シーンを保存せず Unity を強制終了した。
地形の穴(TerrainData は SaveAssetIfDirty で保存済み)と新しい皮の資産 `EdgeSkin_Sanno_bf0abdb0` は残り、
シーンの皮は 12:31 のプレハブのまま ── その皮のメッシュ `4a161867` は 13:58 の巡で消されていた(null)。
⇒ `ClearEdgeSkins` は mesh null の枝で穴を塞がず物だけ消し、`CutEdgeSkin` は 1231 升を「既に穴で触らず」で飛ばし、
**頂点 0 の皮**を焼いた(穴が素通しになる)。

**Why:** 穴は地形の資産・皮はシーンという二つの置き場の片方だけが保存された。

**How to apply:** 起こし直した後に Stage9 を流す前に、EdgeSkin の子の sharedMesh が null でないかを見る。null なら
Gen の最新の `EdgeSkin_<邸>_*.asset` を `EdgeSkin_<邸>_restore` として群へ(世界の原点・回転無し)差してから流す
── ClearEdgeSkins がその升を塞ぎ、元の数(山王 1231 升・頂点 96540)で焼き直せた。報告の「皮 頂点 0」「既に穴で触らず N」が合図。
関連: [[brute-force-measure-hangs-unity]] [[writeback-before-measuring]]
