---
name: qa-code-in-mcp-log
description: 検査役が打った execute_code の全文は ~/Library/Application Support/UnityMCP/Logs/unity_mcp_server.log に残る ── 「同じ測りで刷り直す」はそこから抜く(get_history は先頭だけ)
metadata:
  type: reference
---
2026-10-10 EDO-0502 第97巡。execute_code の get_history は codePreview(先頭 300 字)しか返さないが、MCP サーバの log の
「Tool 'execute_code' called with ... kwargs={...'code': '...'}」の行に全文がある。kwargs は Context(...) を含み ast で丸ごと読めないので、
`'code': ` の後ろを tokenize の最初の STRING トークンで切り出して ast.literal_eval する(scratchpad/r97/qa_*.cs に抜いた手順)。

How to apply: 検査の数を「同じ測り」で前後比較するときは、検査役の刷り(qa97_*.txt)の印の名を grep して log から全文を抜き、
印の名だけ替えて流す。前の巡の自分の Stage の流し方(印・作業場の開け方・書き戻し)も同じ所から写せる。
カメラの構図は刷り(*_shots.mark.txt)に cam と target が残る ── 検査役のカメラは円周の最も低い地表を選ぶので石の中に入ることがある(qa97_07)。
