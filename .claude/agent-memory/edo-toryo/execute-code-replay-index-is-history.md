---
name: execute-code-replay-index-is-history
description: execute_code の replay の index は「直前に送った物」ではなく履歴の番号 — 0 を叩いたら別の Stage(山王 Stage7)が走った
metadata:
  type: project
---

症状: 2026-09-26 EDO-0409。計測のスクリプトが FileNotFound で落ちたので `execute_code action=replay index=0` で送り直したら、
計測でなく先に流した `Stage7_Shaso()` がもう一度走った(冪等なので害は無かった・外した 1,924 = 植えた 1,924)。
原因: replay は get_history の並びの番号を引く。失敗した送信が履歴に載らないか、並びが新しい順でない。
対処: ⛔ replay を使わない。直したコードをそのまま execute で送り直す。冪等でない Stage(造成)の直後なら二重に切る。

関連: [[akasaka-open-resent-six-times]]

追記 2026-10-07(土井 第25巡): Unity を立ち上げ直すと execute_code の履歴は空になる(get_history 0件)。
前の巡と同じ段の呼び方・カメラの構図を引くには、前の棟梁の transcript
`~/.claude/projects/-Users-toshio-project-edo-unity/<窓のid>/subagents/agent-*.jsonl` から tool_use の code を
python で抜く(scratchpad に cams.txt が無い構図もそこに在る)。
