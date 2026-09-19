# 手入れ — 設定そのものを保守する作法(2026-09-13〜)

CLAUDE.md・`.claude/`(役・コマンド・フック・rules・workflows)・スキル(`Tools/Skills/`)・自動メモリ・
`docs/lessons.md` は**それ自体が普請場の道具**で、放っておくと腐る。2026-09-13 の点検: 27 日で 48 コミット、
全部が事故の後追い。参照先を分割した 1 時間後に 5 つの役が古い数字を語り、棟梁の書き戻し先が 3 箇所で食い違い、
スキルは git の外、決定関門はどこにも結線されていなかった。**参照が切れた役・スキル・フックは黙って古い規則で動く**
(EDO-0076 型)ので、散文の作法でなく機械で見張る。

## 何が見張るか

| 役目 | 道具 | いつ |
|---|---|---|
| **道具改め** — 設定の破れを鳴らす | `python3 Tools/Session/config_doctor.py` | 挨拶(`--quick`)・週次(`--table`)・月次(`--deep`) |
| **週次の自動点検** — 表と自己検査を取り、掲示板(`infra`)へ起票して通知する。直さない | スケジュール済みタスク `edo-teire-weekly`(本文 `~/.claude/scheduled-tasks/edo-teire-weekly/SKILL.md`) | 毎週日曜 18 時(アプリが閉じていれば次の起動時)。2026-09-13 ユーザー裁定 |
| **手入れ** — 表を読んで処置する | `/teire` | 週次。自動点検の起票を受けて回す。挨拶も「前回から N 日」と催促する |
| 自己検査 — 道具の検出が生きているか | `config_doctor.py --selftest` | 月次(`--deep` が回す)と道具を直したとき |
| **日誌** — 各セッションが何をして、どこに時間を使ったかを数値にする | `python3 Tools/Session/nikki.py digest`(数値の正典 `docs/Nikki/<日付>.json`、人が読む `.md`) | 毎朝(自動点検と `/nikki` の両方が回す) |
| **日次の自動点検** — 前日の日誌を取り、反映案(→スキル/→規則/→メモリ/→教訓/→不要)を掲示板(`infra`)へ起票して通知する。書かない | スケジュール済みタスク `edo-nikki-daily`(本文 `~/.claude/scheduled-tasks/edo-nikki-daily/SKILL.md`) | 毎朝 5 時に前日ぶん(アプリが閉じていれば次の起動時)。2026-09-19 ユーザー裁定 |
| **日誌の処置** — 日誌を本書きし、反映案をスキル・規則・メモリ・教訓へ手で入れる | `/nikki` | 毎朝。挨拶が「未処置が N 日ぶん」と催促する |
| **週の日誌** — 7 日ぶんを束ねて前週と比べる | `python3 Tools/Session/nikki.py week`(`docs/Nikki/week-*.md`) | 週次(自動点検と `/teire` の両方が回す) |

検査の型(鍵の頭 2 文字): **R** 参照の実在(役→スキル・参照節、CLAUDE.md の表→文書・役、コマンド→Workflow・道具、
フック→スクリプト、SKILL.md↔references、MEMORY.md↔ファイル)/ **Q** 設定を語る数字(計測キー無し・計測とのずれ・
期限切れの移行期間)/ **C** 義務の矛盾(必ず/しない の並存・`obl:` タグの正典が 1 箇所か・description の衛生)/
**S** サイズ予算 / **V** frontmatter の妥当性 / **G** 関門に自己検査 / **K** ゴミ / **W** worktree の設定のずれ /
**Y** sync-tools の網羅 / **SK** スキルの未コミット / **L** 教訓の処置タグ / **N** 催促。
各型の条件と予算は `config_doctor.py` の中(`BUDGET`・各 `chk_*` の docstring)が正典で、ここには写さない。

## 作法

1. **挨拶で ⛔ が出たら、設定を触る前に直す。** ⛔ は曖昧さの無い破れ(無い物を指す・JSON が壊れている・
   義務の正典が 2 つ)。`.claude/`・CLAUDE.md・`Tools/Skills/`・メモリ・`docs/lessons.md` を触るコミットは、
   `--quick` が無言であることが合格の条件。⚠ は表の材料であって止め物ではない。
1.5. **毎朝 `/nikki`。** 夜の自動点検が前日の日誌と反映案を起票する。朝の普請奉行がそれを読み、メモリ・教訓・
   スキル・規則へ**手で**入れてコミットする(自動では書かない — ユーザー裁定 2026-09-19。自動化すると二度と鳴らない
   `docs/verification-loops.md`)。日誌が測る物: 実働(放置と施主の返事待ちを除く)・時間の行き先(役・Bash・Unity・
   読み書きの占有)・手戻り(同一ファイルの Edit・道具のエラー・門番の拒否・自走の巡・検分 fail・Stop の差し戻し)・
   待ち・コミット・掲示板・最終文の質。算法と数字は `nikki.py` の docstring が正典。
2. **週に一度 `/teire`。** 表 → 処置 → `--apply` → 0 ⛔ → コミット。検出は道具、処置の決定は人、
   実行は機械的な物(消す・索引の行・計測値・タグ・掲示板へ逃がす)だけ道具。規則の書き直し・スキルの統合・
   教訓の昇格は**セッションが手で**行う(`docs/verification-loops.md`「書き戻しを自動化しない」)。
   週次はさらに**週の日誌**を読み、7 日ぶんの `/nikki` で足したメモリ・教訓・スキル節を統合・畳み・昇格し、前週より
   改善したかを報告に書く(日次は「足す」、週次は「整える」)。
3. **月に一度 `/teire --deep`。** 各関門の自己検査・挨拶の計時に加え、`anthropic-skills:consolidate-memory` で
   メモリを畳み、`anthropic-skills:skill-creator` で各スキルの description の発火精度と SKILL.md の長さを見直す。
4. **事故のたび**: `edo_board.py post --type lesson` が `docs/lessons.md` へ足した行に、直しと同じコミットで
   処置タグ(`→規則N` / `→スキル:<名>` / `→メモリ:<file>` / `→不要` / `→保留:日付`)を付ける。14 日で道具が鳴る。

## 置き場所の規則の言い直し(CLAUDE.md「知識の置き場所」の延長)

- **義務は正典 1 箇所。** `<!-- obl:<id> canon -->` を正典の行に、他の言及は `→` 付きの 1 行に `<!-- obl:<id> -->`。
  役の義務の正典はその役の**本文**(description は起動判断用なので手順も義務も書かない)。
- **設定を語る数字は計測キー付きか無し。** `<!-- measured: count:asset-index -->` のように同じ行に置けば
  道具が測って `remeasure` で直す。修辞のための数字(「154KB の丸読み禁止」)は消す。
- **スキルの実体は `Tools/Skills/<名>/`、`~/.claude/skills/<名>` は symlink。** リポジトリで版管理し、
  読まれる実体は main の 1 本だけ(`.claude/skills/` に置くと worktree ごとに古い写しが載る)。
  ⛔ `SYNC_PATHS` に入れない。
  ⚠ `unity-mcp-skill` は上流の同期ツール(MCP for Unity の設定画面)の管理下にある。同期を回すと SKILL.md が
  上流の版で上書きされ、手で足した発火条件が消える — 回した後は `git diff Tools/Skills/unity-mcp-skill` で確かめて戻す。
- **フックは `.claude/hooks/` と `.claude/settings.json`。** `~/.claude/settings.json` に edo 用を置かない。

## 誰が・どこに記録するか

- 検出は週次の自動点検が回し、処置はそのセッション(普請奉行)が回す。慣例として `infra` の claim。新しい役・巡回する差配役は置かない。
- 記録: `.git/edo-teire/last.json`(前回の時刻と件数・催促の元。⚠ 自動点検の `--table` でも更新されるので、処置が済んでいなくても催促は消える — 残件の見張りは掲示板の起票が担う)、`ack.json`(`keep` の理由。対象行が変わるまで)、
  `worktrees.json`(1 日 cache)。表は `docs/teire-latest.md`(上書き。経緯は git log)。
  意味的な残件は掲示板の `task`(owner `infra`)。新しい種別は作らない。
- 日誌の記録: `docs/Nikki/<日付>.{json,md}`(冪等。`/nikki` がコミット)、`docs/Nikki/week-*.md`(`/teire`)。
  生ログは `.git/edo-nikki/claims.jsonl`(claim が消える前に門番が刻む — release / 失効 / 奪取)と
  `sessions.jsonl`(SessionEnd フック `.claude/hooks/edo_session_end.py`)。どちらも append-only。
  transcript(`~/.claude/projects/<repo>/`)は Claude Code が消しうるので、日誌がリポジトリに載る側の正典。
- 未着手(元「第 2 期」の残り): 呼ばれない役・スキルと読まれない参照の利用実績、コミット時に門番が `--quick` を
  回す、ダッシュボードの 1 行。長すぎる最終回答は日誌の「最終文の質」が測る。
