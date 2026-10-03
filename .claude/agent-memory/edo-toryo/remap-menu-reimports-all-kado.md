---
name: remap-menu-reimports-all-kado
description: 「Edo/共通/隅部材のマテリアルをremap」は Kado の FBX 89 本を全部 ForceUpdate で再 import し、MCP の再送で何度も回る(1巡 約1.5分)
metadata:
  type: project
---

2026-10-04 EDO-0502 第9巡。新しい練塀の切り駒 2 本のために menu で remap を打ったら、Kado/ の FBX 89 本が全部再 import され、
応答待ち超えで MCP が再送 ⇒ 新しい FBX の import 行が 4 回以上(1巡 約1.5分・Unity 95% 張り付き・read_console もタイムアウト)。

**How to apply:** 新しい FBX が 1〜2 本だけなら menu を打たず、その FBX だけを remap する(`EdoBuild`/ビルダーの RemapDir に
ファイルを渡すか、AssetImporter.SearchAndRemapMaterials を1本ずつ)。打ってしまったら何も投げずに
Editor.log の「Importing 'GUID ... <新しい FBX>」の回数と CPU を見て待つ。
関連 [[akasaka-open-resent-six-times]] [[scribe-2d-and-stale-fbx-material]]
