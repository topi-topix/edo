---
name: partfrom-two-spellings
description: 指図の partFrom は2書式(部材の stem / EdoAssets.Own の呼び名)が混在。フォルダ決め打ちは別フォルダに焼いた部材で破れる
metadata:
  type: project
---

**症状**: 山王 `Stage6_Shaden` は `partFrom` を `"Assets/Edo/Models/Sanno/" + stem + ".fbx"` で解いていた。
2026-09-22 の10棟は `partFrom` が **`EdoAssets.Own.SannoDo("Hogyo", 3, 3, 5454, 5454)` という呼び名**なので
解けず、しかも**鐘楼・鼓楼は `Assets/Edo/Models/Jisha/`**(寺社の類型と同じ駒)に在るので
フォルダの決め打ちも破れた。

**対処**: `EdoAssets.OwnPath(api)`(`EdoAssets.cs` 末尾)— `Own.<関数>(引数…)` の綴りを解いて
`EdoAssets.Own` の関数へ渡すだけの受け(括弧の無い定数 `Own.SannoInari` も解く)。
邸ビルダー側は `PartFromPath` が「`Own.` を含むなら `OwnPath`・含まなければ旧書式の stem」と振り分ける。
⛔ **解けない呼び名は null**(近い名前で代用しない)。⛔ フォルダを実装に書かない(規則12)。

**⚠ 同じ型が先にあった**: `EdoSannoShaRebuild.TreePath`(社叢の `planting[].part`)が同じ解き方を
していたのに、棟の側は決め打ちのままだった。**新しい族を足すときは `EdoAssets.OwnPath` に 1 行**足す。
