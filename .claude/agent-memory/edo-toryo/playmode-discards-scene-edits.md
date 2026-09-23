---
name: playmode-discards-scene-edits
description: Unity が再生中(isPlaying)のまま Stage を流すと、シーンの据え付けは再生を止めた瞬間に消える。書き戻しの MarkSceneDirty 例外が唯一の合図
metadata:
  type: project
---

**症状**(2026-09-22・山王 Stage7)。`execute_code` も `execute_menu_item` も**成功**し、
Stage の戻り値も据えた本数も正しい。ところが `プレハブへ書き戻す` の直後に
`InvalidOperationException: This cannot be used during play mode.`(`EditorSceneManager.MarkSceneDirty`・
`EdoYashikiPrefab.WriteBack`)が Logs/Editor.log に出る ⇒ **Editor が再生中**だった。
再生中のシーン編集は再生を止めた瞬間に全部捨てられる(= 据えた木は消える)。

**なぜ気づきにくいか**: `read_console` には出ない(直近の取得が古い側を返すことがある)し、
`manage_scene`/`execute_code` は普通に通る。`Application.isPlaying` を聞くまで分からない。
⭐ 救いは**資産への書き込みは再生中でも残る**こと — この回は先に走った書き戻しで
`Edo_Sanno_Sha.prefab` が焼けており、`manage_editor stop` の後もプレハブ実体から 20 本が戻った。
TerrainData も資産なので `SetTreeInstances` は残る(ただし `AssetDatabase.SaveAssets` は要る)。

**How to apply:**
- Stage を流す前の一行に `Application.isPlaying` を混ぜる(シーン名・地形と一緒に聞けば只)。
  真なら `manage_editor(action="stop")` → 赤坂は復元に **約2分**(%CPU が 2 台に落ちるまで待つ)→
  edit モードで Stage を流し直す。⛔ 再生中の結果を「建った」と報告しない。
- 止めた直後の 1〜2 回は bridge が `No Unity Editor instances found` を返す(素直に再送)。
- 仕上げは 書き戻し → `AssetDatabase.SaveAssets`(TerrainData)→ `SaveScene` の順。
  書き戻しの成否は `Logs/Editor.log` の `[EdoWriteBack] done ... wrote=N` で読む。

関連: [[pitfall-bridge-drops-after-domain-reload]] / [[pitfall-writeback-mcp-timeout]]
