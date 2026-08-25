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
    # 掲示板の digest(裁定待ち・ブロッカー・open)。CLI は**メインの checkout の物**を使う
    # (worktree のブランチには main を取り込むまで無いことがある)
    gc = subprocess.run(["git", "-C", ROOT, "rev-parse", "--path-format=absolute",
                         "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    bcli = os.path.join(os.path.dirname(gc), "Tools", "Session", "edo_board.py")
    if os.path.exists(bcli):
        b = subprocess.run([sys.executable, bcli, "digest"], capture_output=True, text=True, env=env)
        if b.stdout.strip():
            print(b.stdout.strip())
            print("報告・裁定要請の作法は **docs/session-board.md**(節目・ブロッカー・裁定要請だけ"
                  " post。自己検図・自己考証は**ユーザー入力なしに3巡まで**)。")
