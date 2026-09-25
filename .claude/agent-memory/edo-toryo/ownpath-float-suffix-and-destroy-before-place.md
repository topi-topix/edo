---
name: ownpath-float-suffix-and-destroy-before-place
description: partFrom の `4.5f` を EdoAssets.OwnF が 0 に読み「_0x0ken_」の偽パスになった(直した)。棟一つを差し替えるときは Place が通ってから旧を消す
metadata:
  type: project
---

症状(2026-09-26 EDO-0438 山王 薬師堂): `partFrom` = `EdoAssets.Own.SannoDo("Hogyo6Dan", 4.5f, 4.5f, 8181, 8181)` を
`EdoAssets.OwnPath` が `Sanno_Do_Hogyo6Dan_0x0ken_8181x8181.fbx` へ解き、Place が「asset not found」で例外。
原因: `OwnF` が float.TryParse に `4.5f` をそのまま渡していた(C# の接尾辞)。以前の partFrom は `3` のような裸の数だった。
対処: `OwnF` で末尾の f/F を落とす(EdoAssets.cs)。⚠ 同じ execute_code で旧い棟を先に DestroyImmediate していたので、
例外の時点で旧い薬師堂がシーンから消えた(Undo 無し)。**差し替えは新しい駒を Place してから旧を消す**。

関連: [[partfrom-two-spellings]] [[new-fbx-without-meta-reads-as-unbaked]]
