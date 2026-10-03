---
name: long-run-guard-and-soft-only-converge
description: 30秒を超える Stage は印のファイルで再送を止めて直に呼ぶ(delayCall は一度も発火しなかった)・Converge は柔らかい取り合いだけだと2巡で止まる
metadata:
  type: project
---

2026-09-26 EDO-0437/0454(山王 RunFrom 74 秒・作業場を開く)。

1. `EditorApplication.delayCall` で作業場を開く予約をしたら、5 分待っても一度も発火しなかった(Unity は静か・reload も無し)。
   **対処**: execute_code の冒頭で印のファイルを見て、在れば `return "resend-skip"`、無ければ書いてから直に呼ぶ。
   タイムアウトしても再送は印で弾かれ、1回だけ走る。結果はファイルへ追記して読む(RunFrom・書き戻し・Stage7 で通った)。
2. `EdoBuild.Converge` の「縮まない」判定は**硬い取り合いの最悪**だけで見る ⇒ 柔らかい(狙い)だけを渡すと
   毎巡 0−0 で flat が進み **2巡で止まる**(最良の姿へは戻す)。狙いだけの組は決め打ちの2巡と同じ強さしかない。
3. 呼び出し元が「作業場が開いている」と言っても赤坂が開いていた ── 着手前に active scene を必ず聞く。

**How to apply:** 長い Stage は印のファイル+直呼び。狙いだけの Converge で3巡以上要るなら、硬い取り合いを混ぜるか Converge 側の話として報告する。
関連: [[akasaka-open-resent-six-times]] [[delaycall-lost-and-shared-sashizu]] [[measure-dont-nudge]]
