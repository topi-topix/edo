#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""検分役(検図・考証・庭方)の Stop フック — 返り値の天井(計画 B-4)。

【なぜ要るか】2026-09-13 の実測: 検図方の最終回答は平均 10.4K 字・最大 20K 字。三役で 1 巡 24K 字が
主セッションの文脈へ流れ込み、普請奉行がそれをそのまま施主へ転記していた。公式の指針は
「サブエージェントは凝縮した要約(1,000〜2,000 トークン)だけを返す」。

【止める条件】最後の回答が 3,000 字超(コード塊を除く)。1 回だけ(`stop_hook_active` で通す)。
指摘の全文は scratchpad の json(findings ≤10 件・各 ≤200 字・counts・resolved・verdict・truncated)へ
書き、回答は要約だけにする。呼び出し元は json のパスを受け取れば足りる。
各検分役の frontmatter `hooks.Stop` から呼ぶ(settings.json ではなく)。
"""
import json
import re
import sys

LIMIT = 3000


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if ev.get("stop_hook_active"):
        sys.exit(0)
    msg = re.sub(r"```.*?```", "", ev.get("last_assistant_message") or "", flags=re.S)
    if len(msg) <= LIMIT:
        sys.exit(0)
    print(json.dumps({"decision": "block",
                      "reason": "⛔ 検分の返り値が %d 字。上限は %d 字(公式の指針: 1,000〜2,000 トークンの要約)。"
                                "指摘の全文は scratchpad の json(findings ≤10 件・重要度順・各 ≤200 字・"
                                "counts{高,中,低}・resolved[]・verdict・truncated)に書き、ここには "
                                "verdict・件数・上位 5 件の一行・json のパスだけを返すこと。"
                                % (len(msg), LIMIT)}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
