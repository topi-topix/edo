#!/usr/bin/env python3
"""PreToolUse hook (matcher: mcp__unityMCP__execute_code)

長い処理を execute_code の 1 回の中で回させない(EDO-0503・2026-10-03 施主「以降発生しないように対策を」)。

⛔ 事故: BuildParcel を 21 区画ぶん 1 回の execute_code で回した(約 9 分)。MCP が応答の時間切れを見て
   同じ命令を自動で送り直し、建て直しが 3 巡くり返して CPU 100% のまま止まらなくなり、施主が Unity を再起動した。
   1 区画でも 30 秒を超えれば同じことが起きる(樹下で 2 回走った)。

止めるもの: コードに BuildParcel( の直呼びがあって、EdoBuildQueue を通していないもの。
直し方:   EdoBuildQueue.Enqueue("<scratchpad>/<dir>", "id1", "id2", ...) を呼ぶだけにし、
          待つのは `python3 Tools/Unity/build_queue_wait.py <dir>` の一手(Unity へ問い合わせを重ねない・EDO-0517)。
"""
import json
import re
import sys

HEAVY = [r"\bBuildParcel\s*\("]

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    code = (data.get("tool_input") or {}).get("code") or ""
    if not code or "EdoBuildQueue" in code:
        return 0
    hits = [p for p in HEAVY if re.search(p, code)]
    if not hits:
        return 0
    sys.stderr.write(
        "⛔ 長い建て直しを execute_code の中で直に回さない(EDO-0503)。\n"
        "   時間切れになると MCP が同じ命令を自動で送り直し、建て直しが何巡もくり返す(2026-10-03 に Unity を再起動した事故)。\n"
        "   → execute_code では EdoBuildQueue.Enqueue(\"<scratchpad>/<dir>\", \"id1\", \"id2\", ...) を呼ぶだけにし、\n"
        "     待つのは python3 Tools/Unity/build_queue_wait.py <dir> の一手。区画ごとの log は <dir>/<id>.txt。\n")
    return 2

if __name__ == "__main__":
    sys.exit(main())
