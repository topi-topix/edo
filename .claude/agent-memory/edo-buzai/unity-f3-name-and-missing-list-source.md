---
name: unity-f3-name-and-missing-list-source
description: FBX 名の F3 は Unity(Mono)で 0.2375→0.238・Python は 0.237。欠けた部材の正確な名は棟梁の subagent の jsonl に残る
metadata:
  type: project
---

2026-09-24 EDO-0430(山王の軸 5.5° の建て直しで欠けた 44 駒)。
- ⛔ Unity の `float.ToString("F3")` は**有効7桁に丸めてから四捨五入**(Unity 同梱の mono で実測)。Python "%.3f" は 2 進の正確値で丸めるので 0.2375 が割れる。⭕ `build_sanno_buzai.cs_f3` で綴る。疑ったら `Unity.app/.../MonoBleedingEdge/bin/mcs` で数行の C# を回して確かめる。
- ⭐ 欠けた名の正典は Console ではなく(消されている)`~/.claude/projects/<proj>/<session>/subagents/agent-*.jsonl` の「が無い」の行。女坂の留めは切通しの並びで決まるので計算では出せない。
- ⚠ `build_sanno_shaden.py` の `rects()` は旧鍵 `const.shadenFloor` で止まる。木階だけは `-- kizahashi`(render なし)で迂回できる。

**Why:** 名が 1 字違うと実装は黙って「無い」で建てない。
**How to apply:** 寸法入りの名を焼く前に、実装が要求した綴りと突き合わせる。関連 [[fbx-name-mm-floor-float]] [[ishidan-sode-sheared-module]]
