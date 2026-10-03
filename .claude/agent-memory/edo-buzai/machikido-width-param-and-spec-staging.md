---
name: machikido-width-param-and-spec-staging
description: 町木戸を幅の引数で焼いた(2026-10-01)— PartSpecs が claim 中は札を scratchpad へ振る・開いた大戸 90° は親柱の真後ろへ畳める
metadata:
  type: project
---

2026-10-01 EDO-0503 ② で `build_machikido.py`(`MachiKido_<haba>`・Models/Mon)を起こした。
- `V.write_spec` の置き場は `V.SPEC_DIR` 固定。PartSpecs/EdoAssets.cs が他セッションの claim 中なら、`BUZAI_SPEC_OUT`(この生成器だけが読む)で札を scratchpad へ出し、C# 断片と一緒に返す。
- 開いた大戸は `build_munamon.leaf` を 90° 振ると戸が親柱の見込の中に収まり、袖と当たらない(78° だと袖へ振れ出す)。
**How to apply:** 道幅いっぱいの部材は jamb を端柱の外の面に置き、端柱は掘立(沓石を外へ出さない)— 区画の角へ石が食い込まない。
