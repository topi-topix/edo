---
description: 指図(設計図)をユーザーに出す前に検分する — 三役を並列に、変わった章だけ、上限10件、最大3巡(Workflow sashizu-review)
argument-hint: "<邸名(doi / matsudaira_dewa / sanno / okabe …)>"
---

指図を**ユーザーに見せる前・実装に入る前**の関門。検分の輪は Workflow `sashizu-review` に書いてあり、
反復の上限(3 巡)・返り値の上限(指摘 10 件・要約 1,500 字)・差分だけ見ることをコードで守る。

対象: $1(省略されたらこのセッションの claim の `sashizu:<邸>`)

1. `python3 Tools/Sashizu/review_gate.py --rounds <邸>` — 三巡則で止まっていたら**ここで終わり**。
   `decision` か `blocker` を post してユーザーの返事を待つ(返事が来たら `--ack <邸> "<引用>"`)。
2. 材料を 1 本の Bash で集める:
   `python3 Tools/Sashizu/review_gate.py --changed <邸>`(変わった章)と
   `python3 Tools/Sashizu/review_ledger.py <邸> --open`(前巡の未解決)。
3. **Workflow を名前で起動する**: `Workflow(name: "sashizu-review", args: {estate, changed, ledger, roles})`。
   `roles` は `review_gate.py <邸>` が要るとした役だけ(庭が無い邸は庭方を外す)。
4. 返り値(役ごとの verdict・findings ≤10・counts・truncated・summary)を見て、
   `review_gate.py --record <邸> <役> <pass|fail> "<summary の要点 ≤300 字>"` を役ごとに 1 本の Bash で書く。
   新規の指摘は `review_ledger.py <邸> --add` に、解消は `--close` に写し、`--round-end` で巡を締める。
5. verdict が `stopped`(3 巡で止まった)なら、残る指摘を 1 件ずつ `decision` か `blocker` に起票して
   ユーザーへ(裁定は一通 3 件まで・6 点セット)。

⛔ 検分役を Agent ツールで直接呼ばない(門番が三巡則で止めるが、上限 10 件・差分の規則が効かない)。
⛔ 指図の起案・修正は指図方(edo-sashizukata)。検分役は書き換えない。
