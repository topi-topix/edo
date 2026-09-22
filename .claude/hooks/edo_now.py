#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""窓の今 — 各セッションが**いま何を待っているか**を刻み、一定時間続いた待ちだけを普請場の一枚へ出す。

【なぜ要るか】2026-09-22 施主指示「複数セッションに指示を出しているが、それぞれの状況が分からず、
毎度『今どういう状況?』と聞いて回っている」。claim の心拍は生死しか語らず、板は「Unity を持つ/待つ」
しか出せなかった。コンパイル待ち・保存待ち・役(サブエージェント)の帰り待ち・施主の返事待ちは
どこにも残らず、聞くしかなかった。

【考え方 — 細かい作業は反映しない(開発時間に影響を出さない)】
  ・刻むのは**道具の呼び出しの始まり・終わり・手止め・発話**だけ。中身の要約はしない。
  ・書くのは小さな json 1 枚(`<git-common-dir>/edo-session/<sid>.now.json`)。板のセッション本体
    (`.json`・文脈計)とは別ファイル — 同じ PreToolUse で門番と並走するので、同じ file を取り合わない。
  ・**板へ出すのは SHOW_S 秒を超えて続く待ちだけ**(`board_now.py` が読む時に判定する。
    刻む側は閾値を知らない)。終わった待ちも LOG_S 秒以上なら `edo-nikki/waits.jsonl` へ 1 行残す
    (帯の斜線と日誌の材料)。
  ・PreToolUse の刻みは**門番 `edo_guard.py` が同じ呼び出しの中で行う**(`record_pre`)。
    プロセスを 1 本増やさない(python の起動は 1 回 80ms)。PostToolUse / Stop / UserPromptSubmit は
    このスクリプト自身を settings.json から呼ぶ。

【状態の読み(board_now.window_state)】
  busy   … 道具を呼んで返事を待っている(stack の一番外側が「窓として」待っている物)
  idle   … 手を止めた(Stop)後に施主の発話が無い = **施主の指示・返事待ち**
  work   … その間(考えている・書いている)
  ⚠ 役(サブエージェント)の中の呼び出しにも同じ session_id で来る。`agent_id`/`agent_type` が付いていれば
    stack は触らず `sub` に「役の中で何をしているか」だけ置く。付かない版でも stack で外側(Agent)が残る。

    python3 .claude/hooks/edo_now.py --selftest
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
LOG_S = 60.0            # これ以上続いた待ちは waits.jsonl へ残す(板の斜線・日誌の材料)
TRACKED = ("Bash", "Agent", "Workflow", "Monitor", "Skill")     # + mcp__unityMCP__*(待ちうる道具だけ)
SUBAGENT_JA = {"edo-kenzu": "検図方", "edo-kosho": "考証方", "edo-niwashi": "庭方", "edo-sashizukata": "指図方",
               "edo-toryo": "棟梁", "edo-fushin-qa": "普請検査", "edo-zaiko": "在庫方", "edo-buzai": "部材方",
               "Explore": "探索役", "Plan": "計画役", "general-purpose": "汎用役"}


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


def state_dir(start=None):
    return os.path.join(_common_git_dir(start or ROOT), "edo-session")


def state_path(sid, start=None):
    return os.path.join(state_dir(start), sid + ".now.json")


def waits_path(start=None):
    return os.path.join(_common_git_dir(start or ROOT), "edo-nikki", "waits.jsonl")


# ────────────────────────────── 何を待つ呼び出しか(名札)。⛔ コマンドの全文は残さない。
def classify(tool, ti):
    """(種類, 補足)。種類は板にそのまま出る日本語。補足は括弧の中(空でよい)。"""
    ti = ti or {}
    if tool == "Agent":
        st = ti.get("subagent_type") or ""
        return "%s の帰りを待つ" % SUBAGENT_JA.get(st, st or "役"), ""
    if tool == "Workflow":
        return "検分の輪(Workflow)の帰りを待つ", ""
    if tool == "Monitor":
        return "監視の条件待ち", ""
    if tool == "Skill":
        return "スキルを回している", ti.get("skill") or ""
    if tool.startswith("mcp__unityMCP__"):
        name = tool.split("__")[-1]
        act = str(ti.get("action") or "").lower()
        if name == "refresh_unity":
            return "コンパイル待ち", ""
        if name == "manage_scene":
            if "save" in act:
                return "保存待ち", "シーン"
            if act in ("open", "load"):
                return "シーンを開いている", ""
            return "Unity の応答待ち", "シーン"
        if name == "manage_prefabs":
            return ("プレハブの書き戻し待ち" if act in ("apply", "save", "create", "unpack") else "Unity の応答待ち"), "プレハブ"
        if name in ("manage_script", "create_script", "script_apply_edits", "apply_text_edits", "validate_script"):
            return "C# を書いた(コンパイル待ち)", ""
        if name == "execute_code":
            return "Unity で C# を走らせている", ""
        if name == "execute_menu_item":
            return "メニューの実行待ち", (ti.get("menu_path") or "")[-40:]
        if name == "run_tests":
            return "テストの結果待ち", ""
        return "Unity の応答待ち", name
    if tool == "Bash":
        cmd = ti.get("command") or ""
        if re.search(r"edo_session\.py\s+wait\b", cmd):
            return "Unity の順番待ち", ""
        if re.search(r"(?:^|[\s/])blender\b", cmd):
            m = re.search(r"([A-Za-z0-9_.-]+\.py)\b", cmd)
            return "Blender で焼いている", (m.group(1) if m else "")
        if re.search(r"\bsleep\b|MacOS/Unity|Assembly-CSharp|isCompiling", cmd):
            return "コンパイル待ち", ""
        if re.search(r"build_board_html|board_now|board_window", cmd):
            return "板を焼いている", ""
        if re.search(r"\bgit\s+(push|pull|fetch|clone|lfs)\b", cmd):
            return "git の通信待ち", ""
        if re.search(r"selftest|pytest\b", cmd):
            return "自己検査を回している", ""
        m = re.search(r"python3?\s+(?:\S*/)?([A-Za-z0-9_.-]+\.py)\b", cmd)
        if m:
            return "%s を回している" % m.group(1), ""
        return "コマンドを回している", re.sub(r"\s+", " ", cmd.strip())[:40]
    return "道具の返事待ち", tool


def tracked(tool):
    return tool in TRACKED or tool.startswith("mcp__unityMCP__")


# ────────────────────────────── 状態の読み書き(小さく・落ちても黙る)
def load(sid, start=None):
    try:
        return json.load(open(state_path(sid, start), encoding="utf-8"))
    except Exception:
        return {}


def save(sid, st, start=None):
    fp = state_path(sid, start)
    try:
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        tmp = "%s.%d.tmp" % (fp, os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
        os.replace(tmp, fp)
    except Exception:
        pass


def _log_wait(sid, e, t1, start=None):
    try:
        fp = waits_path(start)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "a", encoding="utf-8") as f:
            f.write(json.dumps({"session": sid, "t0": e["since"], "t1": t1, "kind": e["kind"],
                                "detail": e.get("detail", ""), "tool": e["tool"]}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _sub(ev):
    """役(サブエージェント)の中からの呼び出しか。付いていれば役の名。"""
    a = ev.get("agent_type") or ev.get("agent_id")
    return SUBAGENT_JA.get(a, a) if a else ""


def record_pre(ev, now=None):
    """PreToolUse。門番 edo_guard.py が呼ぶ(プロセスを増やさない)。純粋に状態を更新するだけ。"""
    now = now or time.time()
    sid = (ev.get("session_id") or "")[:12]
    if not sid:
        return
    tool = ev.get("tool_name") or ""
    st = load(sid, ev.get("cwd"))
    st.pop("idle_since", None)          # 道具を呼んだ = 手は空いていない
    st["at"] = now
    sub = _sub(ev)
    if sub:
        st["sub"] = {"role": sub, "tool": tool, "since": now}
        save(sid, st, ev.get("cwd"))
        return
    stack = [e for e in st.get("stack") or [] if e.get("tool") != tool]     # 同じ道具は入れ子にならない=幽霊を落とす
    if tracked(tool):
        kind, detail = classify(tool, ev.get("tool_input") or {})
        stack.append({"tool": tool, "kind": kind, "detail": detail, "since": now})
    st["stack"] = stack
    save(sid, st, ev.get("cwd"))


def record_post(ev, now=None):
    """PostToolUse。stack から同じ道具を落とし、LOG_S 以上続いていたら waits.jsonl へ。"""
    now = now or time.time()
    sid = (ev.get("session_id") or "")[:12]
    if not sid:
        return
    tool = ev.get("tool_name") or ""
    st = load(sid, ev.get("cwd"))
    st["at"] = now
    if _sub(ev):
        st.pop("sub", None)
        save(sid, st, ev.get("cwd"))
        return
    keep = []
    for e in st.get("stack") or []:
        if e.get("tool") == tool:
            if now - e.get("since", now) >= LOG_S:
                _log_wait(sid, e, now, ev.get("cwd"))
            st["last"] = {"kind": e["kind"], "detail": e.get("detail", ""), "since": e["since"], "until": now}
        else:
            keep.append(e)
    st["stack"] = keep
    if tool == "Agent":
        st.pop("sub", None)
    save(sid, st, ev.get("cwd"))


def record_stop(ev, now=None):
    """Stop = 手を止めた。以後は施主の発話が来るまで「指示・返事待ち」。stack の幽霊も全部落とす。"""
    now = now or time.time()
    sid = (ev.get("session_id") or "")[:12]
    if not sid:
        return
    st = load(sid, ev.get("cwd"))
    for e in st.get("stack") or []:
        if now - e.get("since", now) >= LOG_S:
            _log_wait(sid, e, now, ev.get("cwd"))
    st["stack"] = []
    st.pop("sub", None)
    st["idle_since"] = now
    st["at"] = now
    save(sid, st, ev.get("cwd"))


def record_prompt(ev, now=None):
    """UserPromptSubmit = 施主が話した。手は空いていない。"""
    now = now or time.time()
    sid = (ev.get("session_id") or "")[:12]
    if not sid:
        return
    st = load(sid, ev.get("cwd"))
    st.pop("idle_since", None)
    st["at"] = now
    st["spoke"] = now
    save(sid, st, ev.get("cwd"))


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return
    kind = ev.get("hook_event_name") or ""
    if kind == "PreToolUse":
        record_pre(ev)
    elif kind == "PostToolUse":
        record_post(ev)
    elif kind == "Stop":
        record_stop(ev)
    elif kind == "UserPromptSubmit":
        record_prompt(ev)


def selftest():
    """名札と状態遷移を検める。⛔ 0 件は合格ではない — 名札を足したらここへ 1 行足す(規則19)。"""
    import tempfile
    bad = 0
    cases = [
        ("mcp__unityMCP__refresh_unity", {}, "コンパイル待ち"),
        ("mcp__unityMCP__manage_scene", {"action": "save"}, "保存待ち"),
        ("mcp__unityMCP__manage_prefabs", {"action": "apply"}, "プレハブの書き戻し待ち"),
        ("mcp__unityMCP__execute_code", {"code": "x"}, "Unity で C# を走らせている"),
        ("mcp__unityMCP__manage_script", {}, "C# を書いた(コンパイル待ち)"),
        ("Bash", {"command": "python3 Tools/Session/edo_session.py wait --resources unity"}, "Unity の順番待ち"),
        ("Bash", {"command": "/Applications/Blender.app/Contents/MacOS/blender --background --python Tools/Blender/build_x.py"}, "Blender で焼いている"),
        ("Bash", {"command": "for i in 1 2 3; do sleep 5; ps -Ao %cpu,comm | grep MacOS/Unity$; done"}, "コンパイル待ち"),
        ("Bash", {"command": "python3 Tools/Session/build_board_html.py --stage Temp/edo-board"}, "板を焼いている"),
        ("Bash", {"command": "git push origin main"}, "git の通信待ち"),
        ("Bash", {"command": "python3 Tools/Sashizu/kansei_gate.py sanno"}, "kansei_gate.py を回している"),
        ("Bash", {"command": "ls -la"}, "コマンドを回している"),
        ("Agent", {"subagent_type": "edo-kenzu"}, "検図方 の帰りを待つ"),
        ("Workflow", {}, "検分の輪(Workflow)の帰りを待つ"),
    ]
    for tool, ti, want in cases:
        got = classify(tool, ti)[0]
        if got != want:
            bad += 1
            print("  ⛔ %s %s → %r(%r のはず)" % (tool, ti, got, want))
    # 状態遷移: 通しで(git の common-dir を仮の場所へ)
    base = tempfile.mkdtemp(prefix="edo_now_")
    subprocess.run(["git", "init", "-q", base], check=True)
    sid, n = "selftest000", 1_800_000_000.0
    ev = lambda **k: dict(session_id=sid, cwd=base, **k)
    record_pre(ev(tool_name="Bash", tool_input={"command": "ls"}), now=n)
    st = load(sid, base)
    if not (len(st["stack"]) == 1 and st["stack"][0]["kind"] == "コマンドを回している"):
        bad += 1; print("  ⛔ Pre で stack に積まれない", st)
    record_post(ev(tool_name="Bash"), now=n + 10)
    st = load(sid, base)
    if st["stack"] or os.path.exists(waits_path(base)):
        bad += 1; print("  ⛔ 10 秒の呼び出しは stack から落ち、waits.jsonl には残らない", st)
    record_pre(ev(tool_name="Agent", tool_input={"subagent_type": "edo-kenzu"}), now=n + 20)
    record_pre(ev(tool_name="Bash", tool_input={"command": "ls"}, agent_type="edo-kenzu"), now=n + 30)
    st = load(sid, base)
    if not (len(st["stack"]) == 1 and st["stack"][0]["tool"] == "Agent" and st.get("sub", {}).get("role") == "検図方"):
        bad += 1; print("  ⛔ 役の中の呼び出しは stack を触らず sub に置く", st)
    record_post(ev(tool_name="Bash", agent_type="edo-kenzu"), now=n + 40)
    record_post(ev(tool_name="Agent"), now=n + 200)
    st = load(sid, base)
    ws = [json.loads(l) for l in open(waits_path(base), encoding="utf-8")] if os.path.exists(waits_path(base)) else []
    if not (st["stack"] == [] and len(ws) == 1 and ws[0]["kind"] == "検図方 の帰りを待つ" and ws[0]["t1"] - ws[0]["t0"] == 180):
        bad += 1; print("  ⛔ 180 秒の Agent は waits.jsonl に 1 行残る", st, ws)
    record_pre(ev(tool_name="Bash", tool_input={"command": "ls"}), now=n + 300)
    record_pre(ev(tool_name="Bash", tool_input={"command": "ls"}), now=n + 310)     # Post が来なかった幽霊
    st = load(sid, base)
    if len(st["stack"]) != 1 or st["stack"][0]["since"] != n + 310:
        bad += 1; print("  ⛔ 同じ道具の二度目の Pre は幽霊を置き換える", st)
    record_stop(ev(), now=n + 400)
    st = load(sid, base)
    if st["stack"] or st.get("idle_since") != n + 400:
        bad += 1; print("  ⛔ Stop で stack を空にし idle_since を置く", st)
    record_prompt(ev(prompt="次"), now=n + 500)
    if "idle_since" in load(sid, base):
        bad += 1; print("  ⛔ 発話で idle_since が消える")
    # 入口の配線(stdin → hook_event_name で振り分ける)
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True,
                       input=json.dumps({"session_id": sid, "cwd": base, "hook_event_name": "Stop"}))
    if r.returncode != 0 or "idle_since" not in load(sid, base):
        bad += 1; print("  ⛔ 通しで: Stop が stdin から届かない", r.stderr[-200:])
    import shutil
    shutil.rmtree(base, ignore_errors=True)
    print(("⛔ 窓の今 — 破れ %d 件" % bad) if bad else "⭕ 窓の今 — 名札 %d 型・遷移 7 型・配線 1" % len(cases))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    try:
        main()
    except Exception:
        pass
    sys.exit(0)             # 記録で作業を止めない
