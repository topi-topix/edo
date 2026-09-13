---
paths:
  - "Assets/**"
  - "Tools/Blender/**"
---

# Unity / Blender を触るときの一線(CLAUDE.md「触ると壊れるもの」から移した・2026-09-13)

- **複数の Claude Code セッションが同時に動く。** 作業は `python3 Tools/Session/edo_session.py start <屋敷>`
  で始める(指図だけなら worktree、Unity なら `--unity`、Blender なら `--blender`。⛔ Blender は
  worktree では回せない)。⛔ **Unity は排他**。作業が切れたら即 `release --resources unity`(20分未使用は
  待っている側が自動で引き取る)。埋まっていれば `wait --resources unity`。返した側は次の人へ SendMessage。<!-- obl:unity-release canon -->
  ⛔ `git add -A` / `git commit -a` は門番が止める。→ `docs/session-coordination.md`
- **屋敷は1軒1プレハブ。** ビルダーの前に `Edo/屋敷/編集のためにプレハブを解く`、後に `プレハブへ書き戻す`。
  **Revert All を押さない。**
- **地形の編集は Undo の外。** 触る前に heightmap を `.bin` で退避。`TerrainData.asset` と `.unity` も。
- **2026-08-22 に地形を作り直した。** 屋敷を建てる前に必ず造成ステージを流し直す。→ `docs/terrain-georef-fix.md`
- **コンパイルが止まっていることがある。** `Library/ScriptAssemblies/Assembly-CSharp-Editor.dll` の mtime が
  ソースより古ければ実行しない。
- **MCP タイムアウト後の再送で多重実行が起きる。** 冪等でないステージ(特に造成)は実行済みかを先に確認。
  ガードのマーカーは active にする。
- **Blender の FBX を入れたらマテリアルを remap する**(`Edo/御殿/…マテリアルをremap`)。

