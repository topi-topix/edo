---
description: 日誌 — 前日の各セッションの記録(何をして・どこに時間が掛かったか)を docs/Nikki へ本書きし、自動タスクが起票した反映案をスキル・規則・メモリ・教訓へ処置してコミットする(毎朝)
argument-hint: "[YYYY-MM-DD]"
---

日次の振り返りの処置。正典は `docs/teire.md`「日誌」の節。集計は道具、反映案の起票は夜の自動タスク、
**処置の決定と書き込みはこのセッション**(検出は道具・処置は人。自動では書かない — ユーザー裁定 2026-09-19)。
⛔ メインの checkout で回す(worktree で commit すると `sashizu/<邸>` に乗り、週次が読めない)。
⛔ 新しい役は作らない。エージェントも呼ばない(日誌と起票を読んで自分で直す)。

1. `python3 Tools/Session/edo_session.py start infra --phase 基盤`。
2. 日誌を本書き: `python3 Tools/Session/nikki.py digest`($1 があれば `--date $1`。既定は前日)。
   `docs/Nikki/<date>.md` を読む — 総括・時間の行き先・役ごと・手戻り・セッション表。
3. 起票を読む: `python3 Tools/Session/edo_board.py list --estate infra --type task` で題が「日誌(<date>)」の物を
   `show <ID>`。本文の反映案(→スキル / →規則 / →メモリ / →教訓 / →不要)を一件ずつ裁く。
4. 処置(すべて手で):
   - **→メモリ**: `~/.claude/projects/-Users-toshio-project-edo-unity/memory/<slug>.md` を書き、**MEMORY.md の索引行も同時に**。
     既存に同じ事実があれば新設せず更新する。
   - **→教訓**: `python3 Tools/Session/edo_board.py post --type lesson --title "…" --msg "…"`(docs/lessons.md へ 1 行入る)。
     同じコミットで処置タグ(`→規則N` / `→スキル:<名>` / `→メモリ:<file>` / `→不要`)を付ける。
   - **→スキル / →規則**: `Tools/Skills/<名>/…` か CLAUDE.md・`.claude/` を直す。規則の書き直しは根拠(日誌の数値)を
     コミット本文に書く。
   - **→不要**: 起票へ `note <ID> "却下: <理由>"`。
   - 日誌に反映案が無くても、時間の行き先の上位と手戻りを見て、自分で気付いた物があれば同じ形で処置する。
5. **掲示板の差配(朝ひと画面・2026-09-21 施主裁定 EDO-0297=A)** — ⛔ この節を飛ばさない。板が読まれなくなる唯一の原因は溢れ。
   `python3 Tools/Session/board_triage.py --stuck > docs/board-triage.md` を焼き、**表そのものを施主へ出す**
   (古びた件・時効で畳んだ件・宛先の無い宿題だけ。既定の案が処置の列に入っている)。
   施主が一語ずつ直した表を `python3 Tools/Session/board_triage.py --apply docs/board-triage.md` で一括で効かせ、
   `docs/board-triage.md` は消す(正典は `.git/edo-board/`。表は使い捨ての画面)。
   ⛔ 施主に見せる前に自分で `--apply` しない(差配は施主の仕事・畳むかどうかは施主が決める)。
6. `python3 Tools/Session/config_doctor.py --quick` が**無言**になるまで直す(⛔ 0 が合格)。
7. コミット(⛔ `git add -A` / `-a` は門番が止める。未追跡の日誌は `git commit --` に掛からないので門番の commit を使う):
   `python3 Tools/Session/edo_session.py commit docs/Nikki/<date>.json docs/Nikki/<date>.md <触ったパス> -m "chore(日誌): <date> — 反映 k 件 … closes EDO-xxxx"`。
8. 普請場の一枚を焼き直して**同じ URL へ上げ、判を押す**(2026-09-20 施主裁定 — 定期の担い手はここ):
   `python3 Tools/Session/build_board_html.py` → `Artifact(file_path=".git/edo-board/_pm/index.html",
   url="https://claude.ai/artifact/3wTRqrXgJBp8LJUwWFZ4KY", files={"board.html": ".git/edo-board/_pm/dashboard.html"},
   overwrite_unread=["board.html"])` → `build_board_html.py --published <URL>`。
   ⛔ 880KB の中身は**読まない**(表紙だけが頁。正典 docs/session-board.md「ダッシュボード」)。
   ⛔ 焼いただけでは施主に届かない(公開だけは手が要る)。
   ⭐ 2026-09-21 以降、焼き直しは**日誌だけの仕事ではない** — 板が動いた日は手仕舞いのたびに
   Stop フック(`.claude/hooks/edo_board_fresh.py`)が焼いて公開を促す。机の前の窓は
   http://127.0.0.1:8787/ (常駐は `Tools/Session/board_window.py`)。
9. `python3 Tools/Session/edo_session.py release`。
10. 【報告】は一件一葉で: 実働と時間の行き先の上位 3・処置した反映(何を・どこへ)・却下した物と理由。800 字以内。
