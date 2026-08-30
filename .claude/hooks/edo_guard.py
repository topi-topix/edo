#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""門番のフック — Claude Code のツール呼び出しを見て、他セッションとの衝突だけを止める。

stdin に PreToolUse の JSON が来る(session_id / tool_name / tool_input)。
止めるときは **終了コード2 + stderr**(stderr がそのまま Claude に返る)。
素通りは終了コード0。⚠ **フックが落ちても作業は止めない** — 例外は握りつぶして 0 を返す。
"""
import json
import os
import subprocess
import sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
CLI = os.path.join(ROOT, "Tools", "Session", "edo_session.py")


def run(args, sess):
    env = dict(os.environ)
    env["EDO_SESSION_ID"] = sess
    env["CLAUDE_PROJECT_DIR"] = ROOT
    r = subprocess.run([sys.executable, CLI] + args, capture_output=True, text=True, env=env)
    if r.returncode == 2:
        sys.stderr.write(r.stderr)
        sys.exit(2)
    sys.exit(0)


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if not os.path.exists(CLI):
        sys.exit(0)
    sess = (ev.get("session_id") or "unknown")[:12]
    tool = ev.get("tool_name") or ""
    ti = ev.get("tool_input") or {}
    if tool in ("Write", "Edit", "NotebookEdit"):
        fp = ti.get("file_path") or ti.get("notebook_path")
        if fp:
            run(["check-write", fp], sess)
    elif tool in ("Bash", "BashOutput"):
        cmd = ti.get("command")
        if cmd:
            run(["check-bash", cmd], sess)
    elif tool.startswith("mcp__unityMCP__"):
        # 読むだけのものは通す(状態を変えない)
        if tool.split("__")[-1] in ("read_console", "get_sha", "find_in_file", "unity_docs",
                                    "unity_reflect", "debug_request_context", "find_gameobjects",
                                    "manage_script_capabilities", "get_test_job"):
            sys.exit(0)
        run(["check-unity"], sess)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)          # フックの不調で作業を止めない
