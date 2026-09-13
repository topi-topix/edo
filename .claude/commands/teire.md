---
description: 手入れ — 設定そのもの(CLAUDE.md・役・コマンド・フック・スキル・メモリ・教訓)の破れを表にして処置し、0 ⛔ にしてからコミットする(週次。--deep は月次)
argument-hint: "[--deep]"
---

設定を保守する巡。正典は `docs/teire.md`。検出は道具、処置の決定はこのセッション、実行は機械的な物だけ道具。
⛔ 新しい役や差配役は作らない。エージェントも呼ばない(表を読んで自分で直す)。

1. 表を取る: `python3 Tools/Session/config_doctor.py --table > docs/teire-latest.md`($1 が `--deep` なら
   `--deep > docs/teire-latest.md` — 各関門の自己検査と挨拶の計時も付く)。
2. 表の「処置」列を埋める(語彙は `config_doctor.py` の docstring)。
   - 機械的な行(`rm` / `remeasure` / `index-add` / `index-rm` / `sync-rm` / `lesson-tag`)は案のままでよい。
   - 意味的な行(`drop` / `rewrite` / `merge` / `promote` / `expire` / `sync-add`)は**この場で直す**か、
     直せない物は `task:infra "<何を>"` にして掲示板へ逃がす。
   - 正当な例外は `keep "<理由>"`(対象行が変わるまで再掲されない。⛔ には効かない)。
3. `python3 Tools/Session/config_doctor.py --apply docs/teire-latest.md`。
4. `python3 Tools/Session/config_doctor.py --quick` が**無言**になるまで 2〜3 を繰り返す(⛔ 0 が合格)。
5. `--deep` のときは、表の後に出る月次の手作業(`anthropic-skills:consolidate-memory` でメモリ、
   `anthropic-skills:skill-creator` で各スキルの description と長さ)を回す。
6. `git commit -- <触ったパス>`(⛔ `-a` / `add -A` は門番が止める)。`docs/teire-latest.md` も含める。
7. 【報告】は一件一葉で: 表の件数(⛔/⚠)・直した物・掲示板へ逃がした物・残る keep の理由。
