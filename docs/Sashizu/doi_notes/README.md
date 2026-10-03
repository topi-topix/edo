# doi 指図の注記 — 章ごとの目次

設計値の正典は `../doi_sashizu.json`、**この下は文章だけ**。
`<章>/<添字>/<欄>` の path がそのまま鍵なので、直したい欄の path で grep すれば意図と経緯が引ける。

⛔ **値をここへ書かない。**⛔ 文章を指図 json へ戻さない。
戻して原本と突き合わせるのは `python3 Tools/Sashizu/prose_split.py doi --restore`。

| 章 | 注記 | 大きさ |
|---|---:|---:|
| [_reviews](_reviews.json) | 1 | 0.5 KB |
| [boundaryPlinth](boundaryPlinth.json) | 2 | 0.3 KB |
| [edgeProfile](edgeProfile.json) | 1 | 0.2 KB |
| [_rounds_ack](_rounds_ack.json) | 1 | 0.1 KB |

計 4 章 / 5 件 / 1 KB
