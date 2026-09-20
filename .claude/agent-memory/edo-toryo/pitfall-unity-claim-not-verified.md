---
name: pitfall-unity-claim-not-verified
description: start --unity が成功と見えても claim が付いていないことがある。status で「資源: unity」を自分の行に見るまで MCP を叩かない
metadata:
  type: project
---

`edo_session.py start <邸> --unity` が門番の⛔を出さずに終わっても、**unity の claim が
付いていないことがある**(2026-09-20・松江松平の据え直し2巡目で踏んだ)。`status` の
自分の行には `資源: main` しか無く、その間に別セッションが unity を握っていた。

**Why:** 待ち行列の先頭に他人の**予約**が出ている間、`wait --resources unity` は
「unity は空いている(待つ必要なし)」と返す(予約は「保持者」ではないので空きと見える)。
その返事を信じて `start` を打つと、今度は `start` 側の門番が予約を理由に拒む。
予約が切れた瞬間に別のセッションが claim を取り、こちらは取れないまま先へ進んでしまう。
この回はそれに気づかず `refresh_unity` を1回、他人が握っている Unity へ流してしまった。

**How to apply:**
- `start --unity` の**直後に必ず** `status` を読み、**自分の行に `資源: unity`** が出ているかを見る。
  出るまで MCP のツールを1つも叩かない(`refresh_unity` も `read_console` も書き込み側に数える)。
- 並ぶときは `wait` の返事を信用しない。`start` を打って `status` で確かめる、を 20〜30 秒ごとに繰り返す。
- 長引くときは `edo_board.py post --type task --estate cross --owner <相手の邸> --blocked <自分>`
  で明け渡しを頼む(EDO-0278 がその例)。⛔ 予約や claim を力ずくで奪わない。

関連: [[pitfall-bridge-drops-after-domain-reload]]
