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
  agent  … 手は止めたが、**背景の役がまだ帰っていない** = 放っておけば自分で動き出す窓
  idle   … 手を止めた(Stop)後に施主の発話が無く、背景の役も残っていない = **本当に施主待ち**
  work   … その間(考えている・書いている)
  ⚠ **手を止めた ≠ 施主待ち**(2026-09-22 施主指摘)。背景の役(`Agent` を投げる・`SendMessage` で
    起こす)は道具の返事がすぐ返るので stack には残らず、帰りは `<task-notification>` で来る。
    Stop だけ見て「施主の指示待ち」と出すと、役の帰りを待っている窓に施主が呼ばれる。
    Stop のたびに記録(transcript)の尾を読み、**投げた agentId から帰った agentId を引いた残り**を
    `await` に置く(`pending_agents`)。関門(report_lint)が Stop を差し戻して仕事が続く場合も、
    板は「手を止めた」までしか言わない(黄にするのは 60 秒続いてから・board_now 側)。
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
AWAIT_TTL_S = 60 * 60   # これより古い「背景の役」は数えない(記録の尾を切ったときの取りこぼし避け)
TAIL_BYTES = 2_000_000  # 記録(transcript)の尾をどれだけ読むか(背景の役の帰りを数えるため)
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


# ────────────────────────────── 役へ投げる仕事の見込みと内訳(EDO-0412・2026-09-23 施主指示)
#   「役に作業を依頼したとき、いつ返ってくるか分からず、こちらから状況を聞くことが多い」。
#   Agent の prompt の頭に【見込み】【内訳】を書かせ(門番 edo_guard.py が無ければ止める)、
#   窓の今へ「見込み・残り・超過・見込みでは今どの項か」を出す。
_EST = re.compile(r"【見込み】\s*(?:約|およそ)?\s*(\d+(?:\.\d+)?)\s*(?:[〜~\-–ー]\s*(\d+(?:\.\d+)?))?\s*"
                  r"(分|時間|min|h)")
_BULLET = re.compile(r"^\s*(?:\d+\s*[.)．、:]|[①-⑳]|[・\-*•])\s*")
_ITEM_MIN = re.compile(r"[(（]\s*(?:約)?(\d+(?:\.\d+)?)\s*(分|時間)\s*[)）]")
PLAN_MIN_ITEMS = 2      # 内訳は 2 項以上(「調べる・まとめる」でも 2 項になる。1 項は内訳ではない)


def parse_plan(text):
    """prompt から見込みと内訳を読む。戻り値 dict(lo, hi, items=[{t, m}]) — 分。読めなければ None。
    書式(prompt の頭):
        【見込み】20分            (幅があれば 15〜25分・1.5時間 も可)
        【内訳】
        1. 変わった章を読む(5分)  (項ごとの分は任意。あれば板に「見込みでは今どの項か」が出る)
        2. 重なりを総当たりで数える(10分)
        3. 結果を json にまとめる(5分)
    """
    text = text or ""
    m = _EST.search(text)
    if not m:
        return None
    k = 60.0 if m.group(3) in ("時間", "h") else 1.0
    lo = float(m.group(1)) * k
    hi = float(m.group(2) or m.group(1)) * k
    if hi <= 0:
        return None
    items = []
    mi = re.search(r"【内訳】([^\n]*)((?:\n[^\n]*)*)", text)
    if mi:
        head = mi.group(1).strip()
        lines = ([head] if head else []) + mi.group(2).split("\n")
        for ln in lines:
            if not ln.strip():
                if items:
                    break
                continue
            if ln.strip().startswith("【"):
                break
            # 一行に ①…②… と並べた書き方も割る
            parts = re.split(r"(?=[①-⑳])", ln) if len(re.findall(r"[①-⑳]", ln)) > 1 else [ln]
            for p in parts:
                t = _BULLET.sub("", p).strip()
                if not t:
                    continue
                mm = _ITEM_MIN.search(t)
                items.append({"t": t[:48], "m": (float(mm.group(1)) * (60 if mm.group(2) == "時間" else 1)) if mm else None})
    return {"lo": lo, "hi": hi, "items": items[:8]}


def plan_problem(text):
    """門番が止める理由(日本語 1 行)。問題が無ければ ""。"""
    p = parse_plan(text)
    if not p:
        return "【見込み】(何分で帰るか)が無い"
    if len(p["items"]) < PLAN_MIN_ITEMS:
        return "【内訳】が %d 項しかない(%d 項以上・一行一項)" % (len(p["items"]), PLAN_MIN_ITEMS)
    return ""


def plan_now(plan, since, now):
    """見込みに照らした今。戻り値 dict(est="20分", left=残り分(負=超過), step="②の頃" or "")。"""
    if not plan:
        return None
    lo, hi = plan.get("lo") or 0, plan.get("hi") or 0
    est = ("%d分" % hi) if lo == hi else ("%d〜%d分" % (lo, hi))
    if hi >= 90 and lo == hi:
        est = "%.1f時間" % (hi / 60.0)
    el = (now - since) / 60.0
    step = ""
    its = plan.get("items") or []
    if its and all(i.get("m") for i in its):
        acc = 0.0
        for n, i in enumerate(its):
            acc += i["m"]
            if el < acc:
                step = "%sの頃" % ("①②③④⑤⑥⑦⑧"[n] if n < 8 else str(n + 1))
                break
    return {"est": est, "left": hi - el, "step": step}


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
            row = {"session": sid, "t0": e["since"], "t1": t1, "kind": e["kind"],
                   "detail": e.get("detail", ""), "tool": e["tool"]}
            if e.get("plan"):
                row["est_min"] = e["plan"].get("hi")        # 見込みと実際の差を日誌が数える(EDO-0412)
            if e.get("aid"):
                row["aid"] = e["aid"]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _sub(ev):
    """役(サブエージェント)の中からの呼び出しか。付いていれば役の名。"""
    a = ev.get("agent_type") or ev.get("agent_id")
    return SUBAGENT_JA.get(a, a) if a else ""


def _epoch(ts):
    """記録の ISO 時刻 → epoch 秒。読めなければ 0。"""
    try:
        import datetime
        return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def pending_agents(transcript, now=None, max_bytes=TAIL_BYTES, done=None):
    """**まだ帰っていない背景の役**を記録(transcript)の尾から拾う。戻り値 [{"who","since","plan"?}](古い順)。
    `done` にリストを渡すと、**帰ってきた**役を {aid, who, since, until, plan} で積む(見込みと実際の差の材料)。

    ⭐ 背景の役は投げた瞬間に道具の返事が返る(「Async agent launched」/ `resumedAgentId`)ので
      stack には残らない。帰りは `<task-notification>` の `<task-id>`(= agentId)で来る。
      **投げた・起こした** agentId を積み、**帰った** agentId を落とした残りが「待っている役」。
    ⚠ 尾しか読まないので、投げた行が尾の外なら数えられない(取りこぼす側=黄が出る側へ倒す)。
      AWAIT_TTL_S より古い待ちも捨てる — 役が死んでいるのに窓が永久に青くならないように。"""
    now = now or time.time()
    try:
        size = os.path.getsize(transcript)
        with open(transcript, "rb") as f:
            f.seek(max(0, size - max_bytes))
            lines = f.read().decode("utf-8", "ignore").split("\n")
        if size > max_bytes:
            lines = lines[1:]                      # 切れた先頭行は捨てる
    except Exception:
        return []
    calls, roles, live = {}, {}, {}                # 道具の id→役名 / agentId→役名 / agentId→投げた時刻
    plans, cplans = {}, {}                         # agentId→見込み / 道具の id→見込み
    for l in lines:
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except Exception:
            r = None
        t = (_epoch(r.get("timestamp")) if isinstance(r, dict) else 0) or now
        for tid in re.findall(r"<task-id>([0-9A-Za-z_-]{6,})</task-id>", l):
            t0 = live.pop(tid, None)               # 帰ってきた(順に見るので、起こし直しは後で積み直る)
            if t0 is not None and done is not None:
                done.append(dict(aid=tid, who=roles.get(tid) or "役", since=t0, until=t, plan=plans.get(tid)))
        if not isinstance(r, dict):
            continue
        c = (r.get("message") or {}).get("content")
        for b in c if isinstance(c, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") in ("Agent", "SendMessage"):
                ti = b.get("input") or {}
                st = ti.get("subagent_type") or ""
                calls[b.get("id")] = SUBAGENT_JA.get(st, st) or str(ti.get("to") or "")
                src = ti.get("prompt") if b.get("name") == "Agent" else ti.get("message")
                pl = parse_plan(src) if isinstance(src, str) else None
                if pl:
                    cplans[b.get("id")] = pl
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                pl = cplans.pop(b["tool_use_id"], None)
                who = calls.pop(b["tool_use_id"])
                s = b.get("content")
                s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
                m = (re.search(r"Async agent launched[\s\S]{0,300}?agentId[^0-9A-Za-z]{1,4}([0-9A-Za-z]{8,})", s)
                     or re.search(r"resumedAgentId[^0-9A-Za-z]{1,6}([0-9A-Za-z]{8,})", s))
                if not m:
                    continue    # 前で待つ役(返事がその場で返る)と、他の窓への言伝(返事が来るとは限らない)は数えない
                aid = m.group(1)
                if who and who != aid:              # 起こし直しは相手が agentId のことがある — 名は投げた時の物を残す
                    roles[aid] = who
                live[aid] = t
                if pl:
                    plans[aid] = pl
                else:
                    plans.pop(aid, None)            # 見込みの無い起こし直しに古い見込みを残さない
    out = []
    for a, t in live.items():
        if now - t > AWAIT_TTL_S and not (plans.get(a) and now - t <= plans[a]["hi"] * 60 * 2):
            continue                                # 長い見込みの役は見込みの倍まで待つ
        e = dict(who=roles.get(a) or "役", since=t)
        if plans.get(a):
            e["plan"] = plans[a]
        out.append(e)
    out.sort(key=lambda x: x["since"])
    return out


def record_pre(ev, now=None):
    """PreToolUse。門番 edo_guard.py が呼ぶ(プロセスを増やさない)。純粋に状態を更新するだけ。"""
    now = now or time.time()
    sid = (ev.get("session_id") or "")[:12]
    if not sid:
        return
    tool = ev.get("tool_name") or ""
    st = load(sid, ev.get("cwd"))
    st.pop("idle_since", None)          # 道具を呼んだ = 手は空いていない
    st.pop("await", None)               # 待っていた役は、次に手を止めたとき数え直す
    st["at"] = now
    sub = _sub(ev)
    if sub:
        st["sub"] = {"role": sub, "tool": tool, "since": now}
        save(sid, st, ev.get("cwd"))
        return
    stack = [e for e in st.get("stack") or [] if e.get("tool") != tool]     # 同じ道具は入れ子にならない=幽霊を落とす
    if tracked(tool):
        kind, detail = classify(tool, ev.get("tool_input") or {})
        e = {"tool": tool, "kind": kind, "detail": detail, "since": now}
        if tool == "Agent":
            pl = parse_plan((ev.get("tool_input") or {}).get("prompt"))
            if pl:
                e["plan"] = pl
        stack.append(e)
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
    """Stop = 手を止めた。stack の幽霊を全部落とし、**まだ帰っていない背景の役**を `await` に控える。

    ⛔ Stop を「施主の指示待ち」と読み替えない(2026-09-22 施主指摘)。役の帰りを待つ窓は自分で
       動き出すので、施主を呼んではいけない。どちらかは `pending_agents` が記録から数える。"""
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
    done = []
    aw = pending_agents(ev.get("transcript_path") or "", now, done=done)
    seen = st.get("logged_aids") or []
    for d in done:                                  # 帰った背景の役を一度だけ残す(見込みと実際の差・EDO-0412)
        if d["aid"] in seen or d["until"] - d["since"] < LOG_S:
            continue
        e = {"tool": "Agent", "kind": "%s の帰りを待つ(背景)" % d["who"], "detail": "", "since": d["since"], "aid": d["aid"]}
        if d.get("plan"):
            e["plan"] = d["plan"]
        _log_wait(sid, e, d["until"], ev.get("cwd"))
        seen.append(d["aid"])
    if seen:
        st["logged_aids"] = seen[-100:]
    if aw:
        st["await"] = aw
    else:
        st.pop("await", None)
    save(sid, st, ev.get("cwd"))


def record_prompt(ev, now=None):
    """UserPromptSubmit = 施主が話した。手は空いていない。"""
    now = now or time.time()
    sid = (ev.get("session_id") or "")[:12]
    if not sid:
        return
    st = load(sid, ev.get("cwd"))
    st.pop("idle_since", None)
    st.pop("await", None)
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
    # EDO-0412: 見込みと内訳の読み
    plans = [
        ("【見込み】20分\n【内訳】\n1. 読む(5分)\n2. 数える(10分)\n3. まとめる(5分)\n\n本文 1. これは項ではない",
         (20, 20, 3), "三項・項ごとの分"),
        ("【見込み】15〜25分\n【内訳】\n・読む\n・まとめる", (15, 25, 2), "幅と中黒"),
        ("【見込み】1.5時間 【内訳】①建てる②測る③書き戻す", (90, 90, 3), "時間と一行の ①②③"),
        ("見込みは20分くらい", None, "括弧書きが無ければ読まない"),
    ]
    for txt, want, name in plans:
        p = parse_plan(txt)
        got = (p["lo"], p["hi"], len(p["items"])) if p else None
        if got != want:
            bad += 1; print("  ⛔ 見込みの読み: %s → %s(%s のはず)" % (name, got, want))
    pn = plan_now(parse_plan(plans[0][0]), n0 := 1_000_000.0, n0 + 8 * 60)
    if not (pn["est"] == "20分" and round(pn["left"]) == 12 and pn["step"] == "②の頃"):
        bad += 1; print("  ⛔ 見込みの今: 8 分経過は残り 12 分・②の頃", pn)
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
    # 背景の役(2026-09-22 施主指摘「施主の指示待ちとなっていますが、実際にはなってません」)
    tr = os.path.join(base, "transcript.jsonl")
    iso = lambda k: time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(n + k))
    use = lambda i, name, inp: {"type": "assistant", "timestamp": iso(0),
                                "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]}}
    res = lambda k, i, txt: {"type": "user", "timestamp": iso(k),
                             "message": {"content": [{"type": "tool_result", "tool_use_id": i,
                                                      "content": [{"type": "text", "text": txt}]}]}}
    rows = [
        use("t1", "Agent", {"subagent_type": "edo-toryo",
                            "prompt": "【見込み】30分\n【内訳】\n1. 建てる\n2. 書き戻す"}),   # 背景へ投げた
        res(10, "t1", "Async agent launched successfully.\nagentId: aaa111bbb222"),
        use("t2", "Agent", {"subagent_type": "edo-kenzu"}),                       # 前で待つ役(その場で返る)
        res(20, "t2", "指摘 0 件。図は成立している。"),
        use("t3", "SendMessage", {"to": "EDO-0318 続き"}),                        # 他の窓への言伝
        res(30, "t3", '{"success":true,"message":"→ EDO-0318 続き (another Claude session; queued there)"}'),
        {"type": "user", "timestamp": iso(40),
         "message": {"content": "<task-notification><task-id>aaa111bbb222</task-id></task-notification>"}},
        use("t4", "SendMessage", {"to": "aaa111bbb222"}),                          # 起こし直した = また待ち
        res(50, "t4", '{"success":true,"resumedAgentId":"aaa111bbb222"}'),
    ]
    with open(tr, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    aw = pending_agents(tr, now=n + 60)
    if not (len(aw) == 1 and aw[0]["who"] == "棟梁" and abs(aw[0]["since"] - (n + 50)) < 2 and "plan" not in aw[0]):
        bad += 1; print("  ⛔ 帰っていない背景の役は起こし直した時刻から 1 件だけ", aw)
    dn = []
    pending_agents(tr, now=n + 60, done=dn)
    if not (len(dn) == 1 and dn[0]["who"] == "棟梁" and dn[0]["plan"]["hi"] == 30 and abs(dn[0]["until"] - (n + 40)) < 2):
        bad += 1; print("  ⛔ 帰った背景の役は見込みつきで done に積む(起こし直しは見込み無し)", dn)
    if pending_agents(tr, now=n + AWAIT_TTL_S + 120):
        bad += 1; print("  ⛔ 古すぎる待ちは数えない(役が死んだまま窓が青く残らない)")
    record_stop(ev(transcript_path=tr), now=n + 60)
    if [a["who"] for a in load(sid, base).get("await", [])] != ["棟梁"]:
        bad += 1; print("  ⛔ Stop で await に控える", load(sid, base))
    record_pre(ev(tool_name="Bash", tool_input={"command": "ls"}), now=n + 70)
    if "await" in load(sid, base):
        bad += 1; print("  ⛔ 動き出したら await は消える")
    record_stop(ev(transcript_path=os.path.join(base, "無い.jsonl")), now=n + 80)
    if "await" in load(sid, base) or load(sid, base).get("idle_since") != n + 80:
        bad += 1; print("  ⛔ 記録が読めなければ await 無し(=施主待ち)へ落ちる")
    # 入口の配線(stdin → hook_event_name で振り分ける)
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True,
                       input=json.dumps({"session_id": sid, "cwd": base, "hook_event_name": "Stop"}))
    if r.returncode != 0 or "idle_since" not in load(sid, base):
        bad += 1; print("  ⛔ 通しで: Stop が stdin から届かない", r.stderr[-200:])
    import shutil
    shutil.rmtree(base, ignore_errors=True)
    print(("⛔ 窓の今 — 破れ %d 件" % bad) if bad else "⭕ 窓の今 — 名札 %d 型・見込み %d 型・遷移 7 型・背景の役 6 型・配線 1" % (len(cases), len(plans) + 1))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    try:
        main()
    except Exception:
        pass
    sys.exit(0)             # 記録で作業を止めない
