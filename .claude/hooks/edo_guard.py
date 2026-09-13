#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""門番のフック — Claude Code のツール呼び出しを見て、他セッションとの衝突だけを止める。

stdin に PreToolUse の JSON が来る(session_id / tool_name / tool_input)。
止めるときは **終了コード2 + stderr**(stderr がそのまま Claude に返る)。
素通りは終了コード0。⚠ **フックが落ちても作業は止めない** — 例外は握りつぶして 0 を返す。

【文脈計】(2026-09-13・計画 A-2)transcript の末尾から最後の assistant の文脈(トークン)を読み、
300K / 450K / 600K を**初めて**超えたときに一度だけ止めて「手仕舞い→ /compact」を返す。
同じ段では二度止めない(⛔ 止め続けるとデッドロック — モデルは自分で /compact できない)。
あわせて最後の**人間の発話**の時刻を `.git/edo-session/<sid>.json` に刻む — `review_gate.py` の
三巡則(同じ役で fail 3 回)はこの時刻より後の記録だけを数える。
実測(2026-09-13): 主セッションの読みの 44% が文脈 300K 超だった。散文の天井は守られなかった。
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


CTX_STAGES = (300000, 450000, 600000)
SESS_DIR = os.path.join(MAIN_ROOT, ".git", "edo-session")   # claim(.git/edo-locks)・板(.git/edo-board)と同じ前例


def context_meter(ev, sess):
    """文脈の天井(計画 A-2)。超えた段で一度だけ exit 2。人間の発話の時刻も刻む。"""
    tp = ev.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        return
    sys.path.insert(0, os.path.join(MAIN_ROOT, "Tools", "Session"))
    try:
        from token_report import last_context, last_user_ts
    except Exception:
        return
    ctx = last_context(tp)
    if ctx is None:
        return
    os.makedirs(SESS_DIR, exist_ok=True)
    fp = os.path.join(SESS_DIR, sess + ".json")
    try:
        st = json.load(open(fp, encoding="utf-8"))
    except Exception:
        st = {}
    ts = last_user_ts(tp)
    if ts:
        st["last_user"] = ts
    st["ctx"] = ctx
    st["transcript"] = tp
    stage = sum(1 for t in CTX_STAGES if ctx > t)
    seen = int(st.get("ctx_stage") or 0)
    if stage > seen:
        st["ctx_stage"] = stage
    tmp = fp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    os.replace(tmp, fp)
    if stage > seen:
        sys.stderr.write(
            "⛔ 文脈計: この会話の文脈が %dK トークンで、天井 %dK を超えた(docs/fushin-bugyo.md「文脈の作法」)。\n"
            "   費用は「文脈の大きさ × 往復の数」。ここから先の往復は毎回 %dK を読み直す。\n"
            "   ① 手仕舞い — 畳めなかった残タスクを board へ task で起票し、Unity/main の claim を返す\n"
            "   ② ユーザーに **`/compact`(定型: 裁定・_pending・claim・次の一手だけ残す)か新セッション**を求める\n"
            "   この止めは段ごとに一度だけ。次の呼び出しは通る。\n"
            % (ctx // 1000, CTX_STAGES[stage - 1] // 1000, ctx // 1000))
        sys.exit(2)


def _my_estate(sess):
    """このセッションの claim の `sashizu:<邸>` から邸名を引く。無ければ None。"""
    try:
        r = subprocess.run([sys.executable, CLI, "status"], capture_output=True, text=True,
                           env=dict(os.environ, EDO_SESSION_ID=sess, CLAUDE_PROJECT_DIR=ROOT), timeout=10)
        block, hit = r.stdout.split("\n"), None
        for i, ln in enumerate(block):
            if ln.strip().startswith("▶"):
                for ln2 in block[i + 1:i + 12]:
                    if ln2.strip().startswith(("▶", "・")) and not ln2.strip().startswith("▶ " + sess[:8]):
                        break
                    if "sashizu:" in ln2:
                        hit = ln2.strip().split("sashizu:", 1)[1].split()[0]
                        break
                break
        return hit if hit and hit not in ("infra", "cross") else None
    except Exception:
        return None


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    sess = (ev.get("session_id") or "unknown")[:12]
    try:
        context_meter(ev, sess)
    except SystemExit:
        raise
    except Exception:
        pass
    if not os.path.exists(CLI):
        sys.exit(0)
    tool = ev.get("tool_name") or ""
    ti = ev.get("tool_input") or {}
    if tool == "Agent":
        # 三巡則(計画 B-1)— 検分役を呼ぶ前に、同じ役の fail がユーザー入力なしに 3 回続いていないか。
        st = (ti.get("subagent_type") or "")
        if st in ("edo-kenzu", "edo-kosho", "edo-niwashi"):
            est = _my_estate(sess)
            gate = os.path.join(MAIN_ROOT, "Tools", "Sashizu", "review_gate.py")
            if est and os.path.exists(gate):
                r = subprocess.run([sys.executable, gate, "--rounds", est], capture_output=True, text=True)
                if r.returncode == 2:
                    sys.stderr.write("⛔ 門番(三巡則): %s の検分を止めた。\n%s" % (est, r.stdout))
                    sys.exit(2)
        sys.exit(0)
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
