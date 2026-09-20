---
name: pitfall-writeback-mcp-timeout
description: WriteBackAll/SaveOpenScenes on the 47MB MatsudairaDewa prefab always MCP-times-out though it succeeds — verify by file mtime, never re-send
metadata:
  type: project
---

`EdoYashikiPrefab.WriteBackAll()` + `SaveOpenScenes()` on a large estate prefab
(Edo_Yashiki_MatsudairaDewa is ~48MB) **exceeds the MCP response timeout but completes
successfully**. The client reports `Timeout receiving Unity response`.

- **症状**: `execute_code` で書き戻すと `Timeout receiving Unity response`。その後しばらく
  どの MCP 呼び出しもタイムアウトし、`unity-mcp-status-*.json` の `last_heartbeat` が凍る。
- **原因**: 書き戻し→AssetDatabase import→`sceneSaving` フックの `EdoYashikiPrefabAutoSave`
  が再度 WriteBackAll を回す、で main thread が数分ブロックする。CPU は 70〜100% で「生きている」。
- **対処**: ⛔ 再送しない。ファイルの mtime で着地を確かめる —
  `stat -f "%Sm %z" Assets/Edo/Prefabs/Scene/<邸>.prefab Assets/Edo/Scenes/Akasaka.unity`。
  mtime が進んでいれば成功。`~/.unity-mcp/unity-mcp-status-*.json` の `last_heartbeat` が
  10 秒ごとに進み出したら bridge は復帰。

**Why:** 再送すると書き戻しが二重に走り、時間だけ倍かかる(結果は冪等なので壊れはしない)。
それより「失敗した」と誤診して別の手を打つ方が危ない。
**How to apply:** 大きい邸のプレハブを書き戻したらタイムアウトは既定と思い、mtime で判定する。

関連: [[pitfall-bridge-drops-after-domain-reload]]
