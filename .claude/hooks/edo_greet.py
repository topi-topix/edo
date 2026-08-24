#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart — このセッションが始まった時点で、他のセッションが何を押さえているかを出す。
stdout がそのままコンテキストに入る。"""
import json, os, subprocess, sys
ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
CLI = os.path.join(ROOT, "Tools", "Session", "edo_session.py")
try:
    ev = json.load(sys.stdin)
except Exception:
    ev = {}
if os.path.exists(CLI):
    env = dict(os.environ)
    env["EDO_SESSION_ID"] = (ev.get("session_id") or "unknown")[:12]
    env["CLAUDE_PROJECT_DIR"] = ROOT
    r = subprocess.run([sys.executable, CLI, "status"], capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    if out and "生きている claim は無し" not in out:
        print("⚠ このリポジトリでは**他の Claude Code セッションが同時に動いている**。"
              "他人が押さえているファイルと Unity には触らないこと。\n" + out)
        print("作業を始めるには **`python3 Tools/Session/edo_session.py start <屋敷>`**。"
              "指図だけなら worktree を探して(無ければ作って)そこへ回す。"
              "Unity を使うなら `start <屋敷> --unity` でメインに留まり Unity を確保する。")
