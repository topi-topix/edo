#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionEnd — セッションが閉じた事実を日誌の生ログへ 1 行刻む(append-only)。

【なぜ要るか】claim(.git/edo-locks)は release / TTL 失効で消え、文脈計(.git/edo-session)は上書きなので、
「いつ終わったか」がどこにも残らなかった(2026-09-19)。読む側は Tools/Session/nikki.py。
⚠ アプリの強制終了では来ない。その穴は claim の失効(claims.jsonl)と *.desktop-released.json が埋める。
常に exit 0。何も出力しない。"""
import datetime, json, os, subprocess, sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _common_git_dir(start):
    try:
        r = subprocess.run(["git", "-C", start, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, timeout=5)
        d = r.stdout.strip()
        if d:
            return d
    except Exception:
        pass
    return os.path.join(start, ".git")


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    sid_full = ev.get("session_id") or ""
    sid = sid_full[:12]
    if not sid:
        return 0
    git = _common_git_dir(ROOT)
    rec = {"sid": sid, "sid_full": sid_full, "transcript_path": ev.get("transcript_path"),
           "cwd": ev.get("cwd") or ROOT, "reason": ev.get("reason") or "other",
           "ended": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"}
    try:
        st = json.load(open(os.path.join(git, "edo-session", sid + ".json"), encoding="utf-8"))
        rec["ctx"] = st.get("ctx")
        rec["last_user"] = st.get("last_user")
    except Exception:
        pass
    try:
        d = os.path.join(git, "edo-nikki")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "sessions.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
