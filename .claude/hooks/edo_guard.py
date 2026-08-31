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


def _main_root(start):
    """git の common-dir から、全 worktree が共有する main のルートを解く。
    ⚠ **worktree で動くセッションは CLAUDE_PROJECT_DIR がその worktree を指す。**
    sparse worktree には Tools/ も入るが、main を更新しても sashizu/<邸> ブランチへ
    マージするまでは古いまま — フックが worktree 内の CLI を呼ぶと、9677eea の
    wait/unwait も 81a5250 の身元判定の是正も届かず、「入口ごとに判定が違う」現象になる
    (2026-08-31、松平・外堀の両セッションが実例で発見・EDO-0076)。
    git-common-dir はどの worktree から見ても main の .git を指すので、
    その親を「常に最新のツールが置かれている場所」として使う。"""
    try:
        r = subprocess.run(["git", "-C", start, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True, timeout=5)
        d = r.stdout.strip()
        if d:
            return os.path.dirname(d)
    except Exception:
        pass
    return start


MAIN_ROOT = _main_root(ROOT)
CLI = os.path.join(MAIN_ROOT, "Tools", "Session", "edo_session.py")


def run(args, sess):
    env = dict(os.environ)
    env["EDO_SESSION_ID"] = sess
    # ⚠ CLAUDE_PROJECT_DIR は呼び出し元の実際の作業場所(worktree ならその cwd)のまま渡す —
    #   CLI のコード自体は MAIN_ROOT の最新版を使うが、sid() の cwd 判定や rel() の
    #   パス相対化は「このセッションが今どこにいるか」を見るべきなので変えない。
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
