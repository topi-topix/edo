---
name: gravel-band-mesh-not-splat
description: 園路の敷き(玉砂利など)はスプラットでは敷けない — alphamap 4.0 m/px。折れ線から帯メッシュを起こし、巻きは上から見て時計回り
metadata:
  type: project
---

**症状**: 幅 0.8m の参道を地表のスプラットで敷こうとしても何も見えない。

**原因**: `ModernTerrain` は 4096m / alphamapRes 1024 = **4.0 m/px**。園路の幅は 1/5 画素。
(heightmap は 2.0 m/px。こちらも園路の造形には粗い)

**対処**: 指図の折れ線から**帯のメッシュ**を起こし、頂点ごとに `SampleHeight` で地形に沿わせる。
- ⚠ **巻きは上から見て時計回り**(Unity は左手系)。逆だと材は付いているのに上から見て消える。
  `RecalculateNormals` 後に `normals[i].y > 0.5` の数を必ず数える。
- ⚠ 生成 Mesh は**アセットに保存しないとシーン保存で消える** → `AssetDatabase.CreateAsset`
  (置き場は `EdoAssets.Own.Matsudaira.GenMeshDir`。再実行は `CopySerialized` で上書き)。
- ⚠ 刻み(STEP)で切ると**指図の見切り(例: 鳥居の足元 ±0.25m)が刻み1つぶん広がる**。
  刻みの位置は走り[m]で決め、**境の走り値をそのまま点として足す**。
- 玉砂利の材は在庫に 1 つだけ: `EdoAssets.JG.GravelMat`
  (`M_FJG_Terrain_Ground_Gravel_01`・URP/Lit・タイリング 1×1 なので UV は m 単位で張る)。
