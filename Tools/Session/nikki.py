#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日誌(nikki) — 各セッションが何をして、どこに時間を使ったかを日ごとに記録する(2026-09-19)。

【なぜ要るか】指図・検図に時間がかかり続けているのに、「どのセッションが何に何分使ったか」の記録が
どこにも無かった。transcript(~/.claude/projects/<repo>/*.jsonl)は残るが集計は保存されず、claim は
release / 失効で消え、掲示板と git log には節目しか載らない。ここで**時間の行き先**と**手戻り**を数値にし、
日誌として残す。正典は docs/teire.md「日誌」の節。日次の処置は /nikki、週次の整理は /teire。

【何を出すか】
  digest --date YYYY-MM-DD   その日に活動した主セッションを集計し docs/Nikki/<date>.json(数値の正典)と
                             <date>.md(人が読む)を書く。冪等(同じ入力なら同じ出力。ただし終了の記録と
                             claim 履歴は後から届くので、翌日以降の再実行で埋まる)。
  week   --end YYYY-MM-DD    直近 7 日の json を束ねて docs/Nikki/week-YYYY-Www.md を書く(週次の入力)。
  sessions --date            候補の transcript と判定した邸だけを表にする(デバッグ)。

【算法】
  実働    = 活動(assistant の出力・tool_result・人間の発話)を 20 分以上の空白で区切った区間と、役の稼働区間の
            和集合から、施主の返事待ち(AskUserQuestion / ExitPlanMode)を引いた物。放置中は数えない。
  行き先  = tool_use(assistant の時刻)→ tool_result(user の時刻)の区間を種別ごとに和集合。
            Agent だけは subagents/agent-<id>.jsonl の first→last(tool_result は即時に返るため)。
            model = 実働 − 全道具の和集合(生成・思考)。
  役の中  = 役 1 回ぶんの subagents/agent-<id>.jsonl を同じ算法で割る(EDO-0453)。往復・考える(活動 − 道具)・
            道具(Unity / 読む・Bash)・execute_code 回数・起動の文脈・手を付けるまでの読み(最初に Unity・書き込み・
            役を呼んだ往復の文脈 − 最初の往復の文脈)。20 分を超えて返らない道具は「止まり」として別に数える。
  重複    = transcript は再開・圧縮の後に同じ行を書き直すので uuid で 1 度だけ数える(2026-09-26 まで役の呼出・
            Edit・エラーが 2〜3 倍に出ていた。それ以前の日誌の json は水増しのまま)。
  手戻り  = 同一ファイルの Edit 上位・道具のエラー・門番の拒否・同じ役の連続呼出・自走の巡・検分 fail・Stop の差し戻し。
  待ち    = `edo_session.py wait` から次の Unity 取得まで。

【制約(掲示板へ起票する側が守る数字)】題 80 字・本文 800 字・反映案は最大 8 件・各 90 字。md は 150 行以内。

【使い方】
    python3 Tools/Session/nikki.py digest                       # 前日ぶんを docs/Nikki へ
    python3 Tools/Session/nikki.py digest --date 2026-09-13 --out /tmp/x   # 作業ツリーへ書かない(自動タスク用)
    python3 Tools/Session/nikki.py week --end 2026-09-21

⚠ 書き先は --out が無ければ **main の作業ツリー**(worktree から叩いても main に落ちる)。
⚠ 当日(進行中)を回すと途中結果になる。日次は前日固定。
"""
import argparse
import calendar
import collections
import datetime
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import token_report as TR  # noqa: E402

LOOK = 3 * 3600  # 窓の前後に読む幅(秒)。前日から続く往復を閉じるため
IDLE_GAP = 20 * 60  # 主セッションの活動(assistant・tool_result・人間の発話)がこれ以上途切れたら放置とみなす
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
USER_WAIT_TOOLS = ("AskUserQuestion", "ExitPlanMode")  # 施主の返事待ち = 実働から除く
READ_TOOLS = ("Read", "Grep", "Glob")
BASH_KIND = (
    # sleep・until/while の待ちループ = Unity のコンパイル・再読込の待ち(棟梁の道具時間の最大、EDO-0453)
    (re.compile(r"(?:^|[;&|(\n]\s*)sleep\b|\b(?:until|while)\b[^\n]*;\s*do\b"), "sleep"),
    (re.compile(r"build_\w+_sashizu\.py"), "sashizu-build"),
    (re.compile(r"review_gate\.py|wiring_gate\.py"), "review_gate"),
    (re.compile(r"edo_board\.py"), "edo_board"),
    (re.compile(r"edo_session\.py"), "edo_session"),
    (re.compile(r"nikki\.py|token_report\.py|config_doctor\.py"), "nikki"),
    (re.compile(r"(?:^|[;&|(\n]\s*)(?:\S*/)?blender\b"), "blender"),
    (re.compile(r"(?:^|[;&|(\n]\s*)git\b"), "git"),
    (re.compile(r"(?:^|[;&|(\n]\s*)python3?\b"), "python"),
)
AUTO_MARK = ("--session teire-weekly", "--session nikki-daily", "nikki.py digest")
MSG_KEEP, MSG_CUT = 5, 1500
TOP_N = 5


# ----------------------------------------------------------------- 場所
def _git_common_dir(start):
    try:
        r = subprocess.run(["git", "-C", start, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, timeout=5)
        if r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return os.path.join(start, ".git")


REPO = os.path.dirname(os.path.dirname(HERE))
COMMON_GIT = _git_common_dir(REPO)
MAIN_ROOT = os.path.dirname(COMMON_GIT)
NIKKI_DIR = os.path.join(MAIN_ROOT, "docs", "Nikki")
STATE_DIR = os.path.join(COMMON_GIT, "edo-nikki")
BOARD_DIR = os.path.join(COMMON_GIT, "edo-board")
# main と worktree の project dir。TR.PROJ はこのファイルの置き場から引くので、worktree から叩くと worktree の
# transcript しか拾わない — main の根から引く(Claude は "/" と "." を "-" にして dir 名を作る)
PROJ_GLOB = os.path.join(TR.HOME, ".claude", "projects", "-" + re.sub(r"[/.]", "-", MAIN_ROOT.strip("/"))) + "*"


# ----------------------------------------------------------------- 時刻
def parse_ts(s):
    """'2026-09-13T03:14:04.606Z' → epoch(float)。strptime は遅いので手で分解。"""
    try:
        base = calendar.timegm((int(s[0:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16]), int(s[17:19])))
        ms = int(s[20:23]) if len(s) > 22 and s[19] == "." else 0
        return base + ms / 1000.0
    except Exception:
        return None


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def local_hm(t):
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M") if t else "-"


def day_window(date):
    d = datetime.date.fromisoformat(date)
    lo = datetime.datetime(d.year, d.month, d.day).astimezone().timestamp()
    hi = (datetime.datetime(d.year, d.month, d.day) + datetime.timedelta(days=1)).astimezone().timestamp()
    return lo, hi


_TS_KEY = b'"timestamp":"'


def ts_of_line(line):
    """行を parse せずに timestamp を読む。本文に写された断片で二重に出る行は None(=parse して確かめる)。"""
    i = line.find(_TS_KEY)
    if i < 0:
        return None
    if line.rfind(_TS_KEY) != i:
        return None
    e = line.find(b'"', i + len(_TS_KEY))
    if e < 0:
        return None
    return parse_ts(line[i + len(_TS_KEY):e].decode("ascii", "replace"))


def iter_window(fp, lo, hi):
    """窓 [lo-LOOK, hi+LOOK) の entry だけ yield。窓外の行は json.loads しない(1 日ぶんでも数百 MB)。"""
    a, b = lo - LOOK, hi + LOOK
    with open(fp, "rb") as fh:
        for line in fh:
            ts = ts_of_line(line)
            if ts is not None and (ts < a or ts >= b):
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


_START_RX = re.compile(rb"edo_session\.py\s+start\s+([A-Za-z_][\w-]*)(?:[^\n\"]{0,80}?--phase\s+(\S+?))?[\s\"\\]")


def candidate_files(lo, hi):
    """その日に entry を持ちうる主 transcript。mtime と、UTC の 2 日付の bytes で絞る。
    返り値は {fp: start_hint}(transcript 全体から `edo_session.py start <邸> [--phase]` を拾う —
    長寿命のセッションでは窓の外にある)。"""
    days = {datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT").encode()
            for t in (lo, hi - 1)}
    out = {}
    for fp in sorted(glob.glob(os.path.join(PROJ_GLOB, "*.jsonl"))):
        if os.path.getmtime(fp) < lo:
            continue
        try:
            blob = open(fp, "rb").read()
        except OSError:
            continue
        if not any((b'"timestamp":"' + d) in blob for d in days):
            continue
        hint = None
        for m in _START_RX.finditer(blob):
            est = m.group(1).decode("ascii", "replace")
            ph = m.group(2).decode("utf-8", "replace") if m.group(2) else None
            if hint is None or (ph and not hint[1]):
                hint = (est, ph)
        out[fp] = hint
    return out


# ----------------------------------------------------------------- 区間
def dedup(entries):
    """同じ uuid の行を 1 度だけ通す。transcript には再開・圧縮の後に同じ行が書き直されて重なる
    (2026-09-25 の主セッションで assistant 2,329 行中 1,951 行が重複 — 役の呼出・Edit・エラーが 2〜3 倍に数えられていた)。"""
    seen = set()
    for e in entries:
        u = e.get("uuid")
        if u:
            if u in seen:
                continue
            seen.add(u)
        yield e


def union_min(ivs, lo, hi):
    xs = sorted((max(a, lo), min(b, hi)) for a, b in ivs if a is not None and b is not None and b > lo and a < hi)
    tot, cur = 0.0, None
    for a, b in xs:
        if cur is None or a > cur[1]:
            if cur:
                tot += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur:
        tot += cur[1] - cur[0]
    return round(tot / 60.0, 1)


def _strip_cd(cmd):
    return re.sub(r"^\s*cd\s+\S+\s*&&\s*", "", cmd or "")


def tool_category(name, inp):
    inp = inp or {}
    if name == "Agent":
        return "Agent", inp.get("subagent_type") or "?"
    if name == "Bash":
        c = _strip_cd(inp.get("command") or "")
        for rx, lab in BASH_KIND:
            if rx.search(c):
                return "Bash", lab
        return "Bash", "other"
    if name.startswith("mcp__unityMCP__"):
        return "unity", name[len("mcp__unityMCP__"):]
    if name in READ_TOOLS:
        return "read", name
    if name in EDIT_TOOLS:
        return "edit", name
    if name == "Workflow":
        return "workflow", inp.get("name") or "script"
    if name in USER_WAIT_TOOLS:
        return "user", name
    if name in ("WebFetch", "WebSearch"):
        return "web", name
    return "other", name


# ----------------------------------------------------------------- サブエージェント
# 役の中の内訳(EDO-0453)。「手を付けた」= 最初に Unity・書き込み・役・workflow を呼んだ往復。
# 起動の読み = その往復の文脈 − 最初の往復の文脈(規則・スキル・覚え書き・コードを読んで膨らんだ分)。
INNER_KEYS = ("turns", "cs_seek", "active_min", "think_min", "tool_min", "unity_min", "sleep_min", "read_min", "bash_min",
              "stall_min", "stalls", "exec_code", "unity_calls", "tool_calls", "start_ctx_k", "startup_read_k", "startup_min", "max_ctx_k")


# 既存の C# を読み歩く呼び出し(EDO-0456)。据え方の関数を探す grep・sed・Read を数える。
# ⚠ 書き込み(Edit/Write)と cs_check は数えない。目録(docs/edobuild-mokuroku.md)を引いた回は数えない。
CS_SEEK_RX = re.compile(r"Assets/Edo/Scripts/\S*\.cs|Scripts/Editor")
CS_SEEK_CMD = re.compile(r"(?:^|[;&|(\n]\s*)(?:grep|rg|sed -n|cat|head|tail|awk)\b")
CS_SEEK_NOT = re.compile(r"<<\s*'?EOF|sed -i|cat\s*>|\bsleep\b|\buntil\b|stat -f|edo_board\.py|edo_session\.py")


def is_cs_seek(name, inp):
    inp = inp or {}
    if name in ("Read", "Grep", "Glob"):
        blob = " ".join(str(inp.get(k) or "") for k in ("file_path", "path", "glob", "pattern"))
        return bool(CS_SEEK_RX.search(blob)) and not blob.endswith(".md") and "/tmp/" not in blob
    if name == "Bash":
        c = _strip_cd(inp.get("command") or "")
        # 書き換え(python の heredoc・sed -i・cat >)とコンパイルの待ち(sleep・until・stat)は探すのではない。
        # ⚠ 2026-09-26 の初版はこれを数えていて、棟梁の 117 件のうち 37 件が探すでなかった(EDO-0456 の仕分け)
        if CS_SEEK_NOT.search(c):
            return False
        return (bool(CS_SEEK_CMD.search(c)) and bool(CS_SEEK_RX.search(c)) and "cs_check" not in c)
    return False


def _is_work_tool(name):
    return name.startswith("mcp__unityMCP__") or name in EDIT_TOOLS or name in ("Agent", "Workflow")


def inner_of(rec, spans, ctx0, ctx_work, t_work):
    """役 1 回の中の時間と量。考える = 役の活動区間 − 道具の占有(和集合)。"""
    everything = (0, 1e12)
    # 20 分を超えて返らない道具(モーダルの詰まり・タイムアウト)は「止まり」として分ける。主セッションの
    # 活動区間が同じ幅で切れるのと揃え、1 回の 6 時間の詰まりで平均が化けないようにする
    stall = [(a, b) for _, _, a, b in spans if b - a > IDLE_GAP]
    spans = [x for x in spans if x[3] - x[2] <= IDLE_GAP]
    ivs = [(a, b) for _, _, a, b in spans]
    active = union_min(list(rec["segs"]) + ivs, *everything)
    tool = union_min(ivs, *everything)
    by = lambda bk: union_min([(a, b) for k, _, a, b in spans if k == bk], *everything)
    return dict(
        turns=rec["turns"], cs_seek=rec.get("cs_seek", 0), active_min=active, think_min=round(max(0.0, active - tool), 1), tool_min=tool,
        unity_min=by("unity"), read_min=by("read"), bash_min=by("Bash"), sleep_min=by("sleep"),
        stall_min=union_min(stall, *everything), stalls=len(stall),
        exec_code=sum(1 for _, n, _, _ in spans if n == "mcp__unityMCP__execute_code"),
        unity_calls=sum(1 for k, _, _, _ in spans if k == "unity"), tool_calls=len(spans),
        start_ctx_k=round((ctx0 or 0) / 1000.0, 1),
        startup_read_k=round(max(0, (ctx_work or 0) - (ctx0 or 0)) / 1000.0, 1) if t_work else None,
        startup_min=round((t_work - rec["first"]) / 60.0, 1) if t_work and rec["first"] else None,
        max_ctx_k=0.0)


def add_inner(acc, inner):
    """役の中の内訳を足し込む。n = 数えた回数・startup_n = 手を付けた回数(起動の読みの分母)。"""
    acc["n"] = acc.get("n", 0) + (inner.get("n") or 1)
    acc["startup_n"] = acc.get("startup_n", 0) + (
        inner["startup_n"] if "startup_n" in inner else (inner.get("startup_min") is not None))
    for k in INNER_KEYS:
        acc[k] = round((acc.get(k) or 0) + (inner.get(k) or 0), 1)
    return acc


def inner_row(r, acc):
    """1 回あたりの表の 1 行。"""
    n, sn = max(1, acc.get("n") or 0), acc.get("startup_n") or 0
    per = lambda k: acc.get(k, 0) / n
    think_s = 60.0 * acc.get("think_min", 0) / max(1, acc.get("turns") or 0)
    su = ("+%.0fK / %.1f" % (acc["startup_read_k"] / sn, acc["startup_min"] / sn)) if sn else "-"
    st = ("%d 回 %.0f 分" % (acc["stalls"], acc["stall_min"])) if acc.get("stalls") else "-"
    return "| %s | %d | %.0f | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f | %.0f | %.0f | %.0fK | %s | %.0f | %s |" % (
        r, acc.get("n") or 0, per("turns"), per("cs_seek"), per("think_min"), per("tool_min"), per("unity_min"), per("sleep_min"),
        per("read_min") + per("bash_min"), per("exec_code"), think_s, per("start_ctx_k"), su, per("max_ctx_k"), st)


INNER_NOTE = ("考える = 役の活動 − 道具の占有(和集合)。起動の文脈 = 最初の往復の文脈(役の定義・規則・依頼文)。"
              "手を付けるまでの読み = 最初に Unity・書き込み・役を呼んだ往復の文脈 − 起動の文脈(K トークン)/ そこまでの分"
              "(読むだけの役は -)。C#を探す回 = 既存の C# を grep・sed・Read で読んだ呼び出しの数(EDO-0456 の効きの物差し)。止まり = 20 分を超えて返らなかった道具(1 回あたりの列には入れない)。")
INNER_HEAD = ["| 役 | 回 | 往復 | C#を探す回 | 考える分 | 道具分 | うち Unity | うち sleep 待ち | うち読む・Bash | execute_code "
              "| 1往復の考える秒 | 起動の文脈 | 手を付けるまでの読み/分 | 文脈max K | 止まり(計) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]


def subagent_index(fp):
    """<sid>/subagents/agent-<id>.meta.json → 役、対の jsonl → first/last/turns/read/out/final_len。
    返り値は {toolUseId: rec} と {agentId: rec} を合わせた辞書。"""
    sdir = os.path.join(fp[:-len(".jsonl")], "subagents")
    idx = {}
    if not os.path.isdir(sdir):
        return idx
    for meta_fp in glob.glob(os.path.join(sdir, "agent-*.meta.json")):
        aid = os.path.basename(meta_fp)[len("agent-"):-len(".meta.json")]
        try:
            meta = json.load(open(meta_fp, encoding="utf-8"))
        except Exception:
            meta = {}
        rec = dict(role=meta.get("agentType") or "?", desc=(meta.get("description") or "")[:60],
                   first=None, last=None, turns=0, read=0, out=0, final_len=0, aid=aid, segs=[], inner=None)
        seg = None
        jl = os.path.join(sdir, "agent-%s.jsonl" % aid)
        if os.path.exists(jl):
            seen, last_text = {}, ""
            pend, spans = {}, []  # 役の中の道具: tool_use_id -> (ts, name, input) / (bucket, name, t0, t1)
            ctx0 = ctx_work = t_work = None
            for e in dedup(TR._iter(jl)):
                if e.get("type") == "assistant":
                    ts_a = parse_ts(e.get("timestamp") or "") if e.get("timestamp") else None
                    m_a = e.get("message") or {}
                    c_now = TR._ctx(m_a.get("usage") or {})
                    if ctx0 is None and c_now:
                        ctx0 = c_now
                    for x in m_a.get("content") or []:
                        if isinstance(x, dict) and x.get("type") == "tool_use":
                            nm, ip = x.get("name") or "?", x.get("input") or {}
                            pend[x.get("id")] = (ts_a, nm, ip)
                            if is_cs_seek(nm, ip):
                                rec["cs_seek"] = rec.get("cs_seek", 0) + 1
                            if t_work is None and _is_work_tool(nm):
                                t_work, ctx_work = ts_a, c_now
                elif e.get("type") == "user":
                    ts_u = parse_ts(e.get("timestamp") or "") if e.get("timestamp") else None
                    c_u = (e.get("message") or {}).get("content")
                    if isinstance(c_u, list):
                        for x in c_u:
                            if isinstance(x, dict) and x.get("type") == "tool_result":
                                p = pend.pop(x.get("tool_use_id"), None)
                                if p and p[0] and ts_u:
                                    b_, lab_ = tool_category(p[1], p[2])
                                    spans.append(("sleep" if lab_ == "sleep" else b_, p[1], p[0], ts_u))
                ts = parse_ts(e.get("timestamp") or "") if e.get("timestamp") else None
                if ts:
                    rec["first"] = ts if rec["first"] is None else min(rec["first"], ts)
                    rec["last"] = ts if rec["last"] is None else max(rec["last"], ts)
                    if e.get("type") in ("user", "assistant"):
                        if seg is None or ts - seg[1] > IDLE_GAP:
                            if seg:
                                rec["segs"].append(tuple(seg))
                            seg = [ts, ts]
                        else:
                            seg[1] = max(seg[1], ts)
                if e.get("type") == "user":
                    c = (e.get("message") or {}).get("content")
                    if isinstance(c, list):
                        for x in c:
                            if isinstance(x, dict) and x.get("type") == "tool_result":
                                body = TR._text_of(x.get("content"))
                                if "] " in body:
                                    rec.setdefault("commits", []).extend(
                                        re.findall(r"\[([\w./-]+) ([0-9a-f]{7,})\]", body))
                    continue
                if e.get("type") != "assistant":
                    continue
                m = e.get("message") or {}
                u = m.get("usage") or {}
                if u:
                    mid = m.get("id") or e.get("uuid")
                    if mid not in seen or (u.get("output_tokens") or 0) > (seen[mid].get("output_tokens") or 0):
                        seen[mid] = u
                for x in m.get("content") or []:
                    if isinstance(x, dict) and x.get("type") == "text" and x.get("text"):
                        last_text = x["text"]
            if seg:
                rec["segs"].append(tuple(seg))
            rec["turns"] = len(seen)
            rec["read"] = sum(u.get("cache_read_input_tokens") or 0 for u in seen.values())
            rec["out"] = sum(u.get("output_tokens") or 0 for u in seen.values())
            rec["final_len"] = len(last_text)
            rec["inner"] = inner_of(rec, spans, ctx0, ctx_work, t_work)
            rec["inner"]["max_ctx_k"] = round(max([TR._ctx(u) for u in seen.values()] or [0]) / 1000.0, 1)
        if meta.get("toolUseId"):
            idx[meta["toolUseId"]] = rec
        idx[aid] = rec
    return idx


# ----------------------------------------------------------------- 履歴(claim・終了・掲示板)
def _read_jsonl(fp):
    out = []
    if not os.path.exists(fp):
        return out
    for line in open(fp, encoding="utf-8", errors="replace"):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def load_claims(lo, hi):
    """claim の履歴(claims.jsonl)+いま生きている claim(.git/edo-locks)。"""
    by = collections.defaultdict(list)
    for r in _read_jsonl(os.path.join(STATE_DIR, "claims.jsonl")):
        if (r.get("started") or 0) < hi and (r.get("ended") or 0) >= lo:
            by[(r.get("session") or "")[:12]].append(r)
    for fp in glob.glob(os.path.join(COMMON_GIT, "edo-locks", "*.json")):
        try:
            c = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        if (c.get("started") or 0) < hi:
            by[(c.get("session") or "")[:12]].append(
                {"session": c.get("session"), "estate": [p[8:] for p in c.get("paths", []) if p.startswith("sashizu:")],
                 "phase": c.get("phase"), "started": c.get("started"), "ended": None, "reason": None})
    return by


def load_ends():
    by = {}
    for r in _read_jsonl(os.path.join(STATE_DIR, "sessions.jsonl")):
        by[r.get("sid")] = {"at": r.get("ended"), "reason": r.get("reason") or "other"}
    for fp in glob.glob(os.path.join(PROJ_GLOB, "*.desktop-released.json")):
        sid = os.path.basename(fp)[:12]
        if sid in by:
            continue
        try:
            r = json.load(open(fp, encoding="utf-8"))
            by[sid] = {"at": r.get("releasedAt"), "reason": "desktop-%s" % (r.get("reason") or "released")}
        except Exception:
            pass
    return by


_TITLE_ID_RX = re.compile(r"EDO-?(\d{4})")


def load_board_owners():
    """id(EDO-xxxx) → owner邸(無ければ estate)。題に残った票番号から邸を引く索引(EDO-0361)。"""
    out = {}
    for fp in glob.glob(os.path.join(BOARD_DIR, "EDO-*.json")):
        try:
            c = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        iid = c.get("id") or os.path.basename(fp)[:-len(".json")]
        out[iid] = c.get("owner") or c.get("estate") or None
    return out


def board_day(lo, hi):
    out = []
    for fp in glob.glob(os.path.join(BOARD_DIR, "EDO-*.json")):
        try:
            c = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for e in c.get("log") or []:
            t = e.get("t") or 0
            if lo <= t < hi:
                out.append({"id": c.get("id"), "title": (c.get("title") or "")[:60], "type": c.get("type"),
                            "estate": c.get("estate"), "status": c.get("status"), "by": (e.get("by") or "")[:12],
                            "t": iso(t), "msg": (e.get("msg") or "")[:120]})
    return sorted(out, key=lambda x: (x["t"] or "", x["id"] or ""))


def day_commits(lo, hi):
    try:
        r = subprocess.run(["git", "-C", MAIN_ROOT, "log", "--all", "--since=@%d" % int(lo), "--until=@%d" % int(hi),
                            "--format=%H%x1f%ct%x1f%s%x1f%b%x1e"], capture_output=True, text=True, timeout=20)
    except Exception:
        return []
    out = []
    for rec in r.stdout.split("\x1e"):
        p = rec.strip("\n").split("\x1f")
        if len(p) < 3 or not p[0].strip():
            continue
        body = p[3] if len(p) > 3 else ""
        out.append({"sha": p[0].strip()[:8], "t": iso(int(p[1])), "subject": p[2][:80],
                    "refs": sorted(set(re.findall(r"EDO-\d{4}", p[2] + " " + body)))})
    return out


# ----------------------------------------------------------------- 1 セッション
def scan_session(fp, lo, hi, subs, start_hint=None):
    sid_full = os.path.basename(fp)[:-len(".jsonl")]
    rec = dict(sid=sid_full[:12], transcript=fp, title="-", branch=None, cwd=None, first=None, last=None,
               turns=0, users=0, compacts=0, maxctx=0, over300=0, tokens=dict(read=0, write=0, out=0),
               estate="?", phase="?", estate_src="-", kind="work", msgs=[], quality=None)
    seen_mid = {}
    pending = {}   # tool_use_id -> (ts, name, input)
    tools = []     # (bucket, label, t0, t1)
    edits = collections.Counter()
    agent_seq = []
    agent_calls = collections.Counter()
    agent_inner = {}  # aid -> (role, inner)
    st = TR.Streaks()
    segs, seg = [], None  # 活動の区間 [start, last]
    first_ts = last_ts = None

    def act(t):
        nonlocal seg
        if t is None:
            return
        if seg is None or t - seg[1] > IDLE_GAP:
            if seg:
                segs.append(tuple(seg))
            seg = [t, t]
        else:
            seg[1] = max(seg[1], t)
    last_txt, msgs_all = None, []
    errs = dict(tool_errors=0, guard_denies=0, review_fails=0, stop_blocks=0)
    waits, wait_open = [], None
    commit_ev, posts, notes = [], [], []
    auto = False

    def in_win(t):
        return t is not None and lo <= t < hi

    for e in dedup(iter_window(fp, lo, hi)):
        t = e.get("type")
        if t == "custom-title":
            rec["title"] = e.get("customTitle") or "-"
            continue
        ts = parse_ts(e.get("timestamp")) if e.get("timestamp") else None
        if ts:
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
        if e.get("gitBranch") and not rec["branch"]:
            rec["branch"], rec["cwd"] = e.get("gitBranch"), e.get("cwd")
        if t == "system":
            sub = e.get("subtype")
            if sub == "compact_boundary" and in_win(ts):
                rec["compacts"] += 1
            elif sub == "stop_hook_summary" and in_win(ts):
                if e.get("preventedContinuation") or e.get("hookErrors"):
                    errs["stop_blocks"] += 1
            continue
        if t == "assistant":
            act(ts)
            m = e.get("message") or {}
            u = m.get("usage") or {}
            if u and in_win(ts):
                mid = m.get("id") or e.get("uuid")
                if mid not in seen_mid or (u.get("output_tokens") or 0) > (seen_mid[mid].get("output_tokens") or 0):
                    seen_mid[mid] = u
                rec["maxctx"] = max(rec["maxctx"], TR._ctx(u))
            for x in m.get("content") or []:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "tool_use":
                    inp = x.get("input") or {}
                    name = x.get("name") or "?"
                    pending[x.get("id")] = (ts, name, inp)
                    if not in_win(ts):
                        continue
                    if name == "Agent":
                        role = inp.get("subagent_type") or "?"
                        agent_seq.append(role)
                        agent_calls[role] += 1
                        st.on_agent(role)
                    elif name in EDIT_TOOLS and inp.get("file_path"):
                        edits[os.path.relpath(inp["file_path"], MAIN_ROOT) if inp["file_path"].startswith(MAIN_ROOT)
                              else inp["file_path"]] += 1
                    elif name == "Bash":
                        c = inp.get("command") or ""
                        if any(k in c for k in AUTO_MARK):
                            auto = True
                        if re.search(r"edo_session\.py\s+wait\b", c) and wait_open is None:
                            wait_open = ts
                        if re.search(r"review_gate\.py\s+--record\s+\S+\s+\S+\s+fail\b", c):
                            errs["review_fails"] += 1
                elif x.get("type") == "text" and len(x.get("text") or "") > 200:
                    last_txt = x["text"]
            continue
        if t == "user":
            c = (e.get("message") or {}).get("content")
            if isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                act(ts)
                tur = e.get("toolUseResult")
                for x in c:
                    if not isinstance(x, dict) or x.get("type") != "tool_result":
                        continue
                    p = pending.pop(x.get("tool_use_id"), None)
                    if not p:
                        continue
                    t0, name, inp = p
                    body = TR._text_of(x.get("content"))
                    if isinstance(tur, dict) and tur.get("stdout"):
                        body += "\n" + str(tur.get("stdout"))
                    if in_win(t0) or in_win(ts):
                        if x.get("is_error"):
                            if body.lstrip().startswith("PreToolUse:"):
                                errs["guard_denies"] += 1
                            else:
                                errs["tool_errors"] += 1
                        if name == "Agent":
                            s = subs.get(x.get("tool_use_id"))
                            if s is None:
                                mo = re.search(r"agentId: ([0-9a-f]+)", body)
                                s = subs.get(mo.group(1)) if mo else None
                            role = s["role"] if s else (inp.get("subagent_type") or "?")
                            if s and s.get("segs"):
                                for a0, a1 in s["segs"]:
                                    tools.append(("Agent", role, a0, a1))
                            else:
                                tools.append(("Agent", role, t0, ts))
                            if s:
                                commit_ev += s.get("commits", [])
                                if s.get("inner"):
                                    agent_inner[s["aid"]] = (role, s["inner"])
                        else:
                            b, lab = tool_category(name, inp)
                            tools.append((b, lab, t0, ts))
                        if name == "Bash":
                            cmd = inp.get("command") or ""
                            if "git commit" in cmd or "edo_session.py commit" in cmd:
                                commit_ev += re.findall(r"\[([\w./-]+) ([0-9a-f]{7,})\]", body)
                            if "edo_board.py" in cmd:
                                ids = re.findall(r"EDO-\d{4}", body)
                                if re.search(r"\bpost\b", cmd):
                                    posts += ids
                                elif re.search(r"\bnote\b", cmd):
                                    notes += ids
                            if wait_open is not None and not x.get("is_error") and re.search(
                                    r"--unity\b|claim\b.*\bunity\b", cmd):
                                waits.append((wait_open, ts)); wait_open = None
                        elif name.startswith("mcp__unityMCP__") and wait_open is not None and not x.get("is_error"):
                            waits.append((wait_open, ts)); wait_open = None
                continue
            s = TR.human_text(e)
            if s is None:
                continue
            # 人間の発話: 結果の来ていない道具を閉じる
            act(ts)
            for uid, (t0, name, inp) in list(pending.items()):
                b, lab = tool_category(name, inp)
                tools.append((b, lab, t0, ts))
            pending.clear()
            st.on_user(s)
            if in_win(ts):
                rec["users"] += 1
                if last_txt:
                    msgs_all.append(last_txt)
            last_txt = None
    # 締め
    if seg:
        segs.append(tuple(seg))
    for uid, (t0, name, inp) in pending.items():
        b, lab = tool_category(name, inp)
        tools.append((b, lab, t0, last_ts or t0))
    if wait_open is not None:
        waits.append((wait_open, last_ts or wait_open))
    st.finish()
    if last_txt and in_win(last_ts):
        msgs_all.append(last_txt)

    rec["first"], rec["last"] = iso(first_ts), iso(last_ts)
    rec["spans"] = {"prev": bool(first_ts and first_ts < lo), "next": bool(last_ts and last_ts >= hi)}
    user_wait = [(t0, t1) for b, lab, t0, t1 in tools if b == "user"]
    agent_spans = [(t0, t1) for b, lab, t0, t1 in tools if b == "Agent"]
    rec["active_min"] = round(max(0.0, union_min(segs + agent_spans, lo, hi) - union_min(user_wait, lo, hi)), 1)
    rec["user_wait_min"] = union_min(user_wait, lo, hi)
    rec["wall_min"] = round(max(0.0, min(hi, last_ts or lo) - max(lo, first_ts or lo)) / 60.0, 1) if first_ts else 0.0
    rec["turns"] = len(seen_mid)
    for u in seen_mid.values():
        rec["tokens"]["read"] += u.get("cache_read_input_tokens") or 0
        rec["tokens"]["write"] += u.get("cache_creation_input_tokens") or 0
        rec["tokens"]["out"] += u.get("output_tokens") or 0
        rec["over300"] += TR._ctx(u) > 300000
    rec["kind"] = "auto" if auto else "work"
    rec["start_hint"] = start_hint
    # 時間の行き先
    buckets = collections.defaultdict(list)
    labels = collections.defaultdict(list)
    agents = collections.defaultdict(lambda: dict(calls=0, min=0.0, spans=[]))
    for b, lab, t0, t1 in tools:
        if b == "user":
            continue
        buckets[b].append((t0, t1))
        labels["%s:%s" % (b, lab)].append((t0, t1))
        if b == "Agent":
            agents[lab]["spans"].append((t0, t1))
    for role in agents:
        agents[role]["calls"] = agent_calls.get(role, 0)
    all_tools = union_min([iv for ivs in buckets.values() for iv in ivs], lo, hi)
    time = dict(model_min=round(max(0.0, rec["active_min"] - all_tools), 1),
                tools_min=all_tools,
                buckets={b: union_min(ivs, lo, hi) for b, ivs in buckets.items()},
                labels={k: union_min(ivs, lo, hi) for k, ivs in labels.items()},
                agents={})
    for role, a in agents.items():
        m = union_min(a["spans"], lo, hi)
        time["agents"][role] = dict(calls=a["calls"], min=m, mean_min=round(m / max(1, a["calls"]), 1))
    for role, inner in agent_inner.values():
        if role in time["agents"]:
            add_inner(time["agents"][role].setdefault("inner", {}), inner)
    time["top"] = sorted(time["labels"].items(), key=lambda kv: -kv[1])[:TOP_N]
    rec["time"] = time
    rec["rework"] = dict(edits_top=edits.most_common(3), agent_repeats=sum(
        1 for i in range(1, len(agent_seq)) if agent_seq[i] == agent_seq[i - 1]),
        streak_max=st.max, streaks=st.list[:5], **errs)
    rec["wait"] = dict(calls=len(waits), min=union_min(waits, lo, hi))
    rec["commit_evidence"] = [{"branch": b, "sha": s[:8]} for b, s in commit_ev]
    rec["board"] = dict(posts=sorted(set(posts)), notes=sorted(set(notes)))
    rec["quality"] = TR.report_quality(msgs_all)
    rec["msgs_n"] = len(msgs_all)
    rec["msgs"] = [m[:MSG_CUT] for m in msgs_all[-MSG_KEEP:]]
    return rec


def estate_of(rec, claims, board_owners=None):
    cs = claims.get(rec["sid"]) or []
    ests = collections.Counter(e for c in cs for e in (c.get("estate") or []))
    if ests:
        ph = next((c.get("phase") for c in cs if c.get("phase")), None)
        if not ph and rec.get("start_hint") and rec["start_hint"][1]:
            ph = rec["start_hint"][1]
        return ests.most_common(1)[0][0], ph or "?", "claims"
    b = rec.get("branch") or ""
    if b.startswith("sashizu/"):
        return b[len("sashizu/"):], "指図", "branch"
    if rec.get("start_hint"):
        e, p = rec["start_hint"]
        return e, p or "?", "bash"
    if board_owners:
        m = _TITLE_ID_RX.search(rec.get("title") or "")
        if m:
            owner = board_owners.get("EDO-%s" % m.group(1))
            if owner:
                return owner, "?", "title"
    return "?", "?", "-"


# ----------------------------------------------------------------- 日
def link_commits(sessions, commits):
    """Bash の証拠(sha)→ 直接。無ければ EDO 参照の交わり。残りは unlinked。"""
    by_sha = {c["sha"]: c for c in commits}
    taken = set()
    for s in sessions:
        mine = []
        for ev in s.pop("commit_evidence", []):
            c = by_sha.get(ev["sha"])
            if c and ev["sha"] not in taken:
                mine.append(dict(c, link="bash")); taken.add(ev["sha"])
        ids = set(s["board"]["posts"]) | set(s["board"]["notes"])
        for c in commits:
            if c["sha"] in taken or not ids:
                continue
            if ids & set(c["refs"]):
                mine.append(dict(c, link="refs")); taken.add(c["sha"])
        s["commits"] = sorted(mine, key=lambda c: c["t"] or "")
    # 残りは「そのコミット時刻に活動していた作業セッションが 1 本だけ」なら時刻で紐付ける
    for c in commits:
        if c["sha"] in taken:
            continue
        ct = parse_ts(c["t"]) if c["t"] else None
        cands = [s for s in sessions if s["kind"] == "work" and s["first"] and s["last"]
                 and parse_ts(s["first"]) - 120 <= (ct or -1) <= parse_ts(s["last"]) + 120]
        if len(cands) == 1:
            cands[0]["commits"].append(dict(c, link="time")); taken.add(c["sha"])
    for s in sessions:
        s["commits"].sort(key=lambda c: c["t"] or "")
    return [c for c in commits if c["sha"] not in taken]


def totals_of(sessions, unlinked, board):
    work = [s for s in sessions if s["kind"] == "work"]
    T = dict(sessions=len(sessions), work_sessions=len(work), active_min=round(sum(s["active_min"] for s in work), 1),
             wall_min=round(sum(s["wall_min"] for s in work), 1), turns=sum(s["turns"] for s in work),
             users=sum(s["users"] for s in work), compacts=sum(s["compacts"] for s in work),
             tokens={k: sum(s["tokens"][k] for s in work) for k in ("read", "write", "out")},
             tool_errors=sum(s["rework"]["tool_errors"] for s in work),
             guard_denies=sum(s["rework"]["guard_denies"] for s in work),
             stop_blocks=sum(s["rework"]["stop_blocks"] for s in work),
             review_fails=sum(s["rework"]["review_fails"] for s in work),
             streak_max=max([s["rework"]["streak_max"] for s in work] or [0]),
             wait_min=round(sum(s["wait"]["min"] for s in work), 1),
             commits=sum(len(s["commits"]) for s in work), commits_unlinked=unlinked,
             estate_unknown=sum(1 for s in work if s["estate"] == "?"),
             board_day=board)
    by_e = collections.defaultdict(lambda: dict(sessions=0, active_min=0.0, turns=0, commits=0))
    for s in work:
        b = by_e[s["estate"]]
        b["sessions"] += 1; b["active_min"] = round(b["active_min"] + s["active_min"], 1)
        b["turns"] += s["turns"]; b["commits"] += len(s["commits"])
    T["by_estate"] = dict(by_e)
    by_r = collections.defaultdict(lambda: dict(calls=0, min=0.0))
    lab = collections.Counter()
    buck = collections.Counter()
    for s in work:
        for role, a in s["time"]["agents"].items():
            by_r[role]["calls"] += a["calls"]; by_r[role]["min"] = round(by_r[role]["min"] + a["min"], 1)
            if a.get("inner"):
                add_inner(by_r[role].setdefault("inner", {}), a["inner"])
        for k, v in s["time"]["labels"].items():
            lab[k] += v
        for k, v in s["time"]["buckets"].items():
            buck[k] += v
    for r in by_r.values():
        r["mean_min"] = round(r["min"] / max(1, r["calls"]), 1)
    T["by_role"] = dict(by_r)
    T["model_min"] = round(sum(s["time"]["model_min"] for s in work), 1)
    T["buckets"] = {k: round(v, 1) for k, v in buck.items()}
    T["time_top"] = [(k, round(v, 1)) for k, v in lab.most_common(TOP_N)]
    rw = []
    for s in work:
        for f, n in s["rework"]["edits_top"]:
            if n >= 5:
                rw.append(("%s: %s を %d 回 Edit" % (s["estate"], f, n), n))
        if s["rework"]["streak_max"] >= 3:
            rw.append(("%s: 自走の巡 %d" % (s["estate"], s["rework"]["streak_max"]), s["rework"]["streak_max"]))
        if s["rework"]["tool_errors"] >= 5:
            rw.append(("%s: 道具のエラー %d 回" % (s["estate"], s["rework"]["tool_errors"]), s["rework"]["tool_errors"]))
        if s["rework"]["guard_denies"] >= 3:
            rw.append(("%s: 門番の拒否 %d 回" % (s["estate"], s["rework"]["guard_denies"]), s["rework"]["guard_denies"]))
        if s["compacts"] >= 2:
            rw.append(("%s: 圧縮 %d 回(文脈の膨らみ)" % (s["estate"], s["compacts"]), s["compacts"]))
    T["rework_top"] = sorted(rw, key=lambda x: -x[1])[:TOP_N]
    return T


def deltas_of(T, prev):
    if not prev:
        return {"prev": None}
    P = prev.get("totals") or {}
    d = {"prev": prev.get("date")}
    for k in ("active_min", "turns", "compacts", "review_fails", "stop_blocks", "guard_denies", "tool_errors", "commits"):
        d[k] = round((T.get(k) or 0) - (P.get(k) or 0), 1)
    d["tokens_read"] = (T["tokens"]["read"] or 0) - ((P.get("tokens") or {}).get("read") or 0)
    return d


def _h(m):
    return "%.1fh" % (m / 60.0)


def _pct(a, b):
    return "%d%%" % round(100.0 * a / b) if b else "-"


def render_md(doc):
    T, D = doc["totals"], doc["deltas"]
    L = ["# 日誌 %s" % doc["date"], "",
         "数値の正典は同名の json。集計は `Tools/Session/nikki.py digest`(終了の記録と claim 履歴は後から届くので、"
         "翌日以降の再実行で埋まる)。", ""]
    line = ("**総括** — セッション %d 本(自動 %d 本を除く)・実働 %s(壁時計 %s)・往復 %d・人間の発話 %d・"
            "読み %s / 出力 %s・圧縮 %d 回・コミット %d(紐付かず %d)・待ち %s。"
            % (T["work_sessions"], T["sessions"] - T["work_sessions"], _h(T["active_min"]), _h(T["wall_min"]),
               T["turns"], T["users"], TR.fmt_m(T["tokens"]["read"]), TR.fmt_m(T["tokens"]["out"]), T["compacts"],
               T["commits"], len(T["commits_unlinked"]), _h(T["wait_min"])))
    if D.get("prev"):
        line += " 前日(%s)比: 実働 %+.0f 分・往復 %+d・圧縮 %+d・検分 fail %+d・差し戻し %+d・拒否 %+d。" % (
            D["prev"], D["active_min"], D["turns"], D["compacts"], D["review_fails"], D["stop_blocks"], D["guard_denies"])
    if T["estate_unknown"]:
        line += " ⚠ 邸が判らないセッション %d 本(`edo_session.py start <邸>` が無い)。" % T["estate_unknown"]
    L += [line, ""]
    L += ["## 邸ごと", "", "| 邸 | 本 | 実働 | 往復 | コミット |", "|---|---|---|---|---|"]
    for e, b in sorted(T["by_estate"].items(), key=lambda kv: -kv[1]["active_min"]):
        L.append("| %s | %d | %s | %d | %d |" % (e, b["sessions"], _h(b["active_min"]), b["turns"], b["commits"]))
    L += ["", "## 時間の行き先(上位 %d・道具の占有の和集合)" % TOP_N, "",
          "実働 %s のうち道具の待ち %s・生成と思考 %s。" % (_h(T["active_min"]),
                                                     _h(sum(T["buckets"].values())), _h(T["model_min"])), "",
          "| 何に | 分 | 実働比 |", "|---|---|---|"]
    for k, v in T["time_top"]:
        L.append("| %s | %.0f | %s |" % (k, v, _pct(v, T["active_min"])))
    L += ["", "## 役ごと(サブエージェント)", "", "| 役 | 呼出 | 合計分 | 平均分 |", "|---|---|---|---|"]
    for r, a in sorted(T["by_role"].items(), key=lambda kv: -kv[1]["min"]):
        L.append("| %s | %d | %.0f | %.1f |" % (r, a["calls"], a["min"], a["mean_min"]))
    inner = [(r, a["inner"]) for r, a in sorted(T["by_role"].items(), key=lambda kv: -kv[1]["min"]) if a.get("inner")]
    if inner:
        L += ["", "## 役の中の内訳(1 回あたり)", "",
              INNER_NOTE, ""] + INNER_HEAD
        L += [inner_row(r, acc) for r, acc in inner]
    L += ["", "## 手戻りの兆候", "",
          "道具のエラー %d・門番の拒否 %d・検分 fail %d・Stop の差し戻し %d・自走の巡の最大 %d。" % (
              T["tool_errors"], T["guard_denies"], T["review_fails"], T["stop_blocks"], T["streak_max"]), ""]
    for txt, n in T["rework_top"]:
        L.append("- " + txt)
    if not T["rework_top"]:
        L.append("- 目立つ物なし")
    L += ["", "## セッション", "",
          "| sid | 題 | 邸/工程 | 時刻 | 実働/壁 | 往復 | 文脈max | 圧縮 | 上位 | 手戻り | commit | 終了 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(doc["sessions"], key=lambda s: -s["active_min"])[:25]:
        top = ", ".join("%s %.0f" % (k.split(":", 1)[1][:12], v) for k, v in s["time"]["top"][:3])
        rw = s["rework"]
        rws = "E%d/拒%d/巡%d" % (rw["tool_errors"], rw["guard_denies"], rw["streak_max"])
        t0 = local_hm(parse_ts(s["first"])) if s["first"] else "-"
        t1 = local_hm(parse_ts(s["last"])) if s["last"] else "-"
        span = ("←" if s["spans"]["prev"] else "") + t0 + "–" + t1 + ("→" if s["spans"]["next"] else "")
        L.append("| %s | %s | %s/%s | %s | %s/%s | %d | %dK | %d | %s | %s | %d | %s |" % (
            s["sid"][:8], (s["title"] or "-")[:14] + (" (自動)" if s["kind"] == "auto" else ""),
            s["estate"], s["phase"], span, _h(s["active_min"]), _h(s["wall_min"]), s["turns"],
            s["maxctx"] // 1000, s["compacts"], top, rws, len(s["commits"]),
            (s.get("ended") or {}).get("reason") or "?"))
    if T["commits_unlinked"]:
        L += ["", "紐付かないコミット: " + ", ".join("%s %s" % (c["sha"], c["subject"][:30]) for c in T["commits_unlinked"][:8])]
    L += ["", "## 掲示板(当日の動き)", ""]
    for b in T["board_day"][:20]:
        L.append("- %s %s [%s/%s] %s — %s" % (b["t"][11:16] if b["t"] else "-", b["id"], b["estate"], b["type"],
                                            b["title"], b["msg"][:60]))
    if not T["board_day"]:
        L.append("- なし")
    L += ["", "## ユーザー向け最終文の質", "", "| sid | 通数 | 平均字 | 2000字超 | 見出し率 | 記号/通 | 役名/通 |",
          "|---|---|---|---|---|---|---|"]
    for s in sorted(doc["sessions"], key=lambda s: -s["active_min"])[:15]:  # md は 150 行以内(docstring の制約)
        q = s.get("quality")
        if q:
            L.append("| %s | %d | %.0f | %d | %.0f%% | %.1f | %.1f |" % (
                s["sid"][:8], q["n"], q["mean"], q["over2000"], 100 * q["hdr"], q["marks"], q["roles"]))
    return "\n".join(L) + "\n"


def write_atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def digest(date, out=None, json_only=False, quiet=False):
    out = out or NIKKI_DIR
    lo, hi = day_window(date)
    claims = load_claims(lo, hi)
    ends = load_ends()
    board_owners = load_board_owners()
    sessions = []
    for fp, hint in candidate_files(lo, hi).items():
        subs = subagent_index(fp)
        s = scan_session(fp, lo, hi, subs, hint)
        if not s["turns"] and not s["users"]:
            continue
        s["estate"], s["phase"], s["estate_src"] = estate_of(s, claims, board_owners)
        s.pop("start_hint", None)
        cl = claims.get(s["sid"]) or []
        cl_ended = [c for c in cl if c.get("ended")]
        if s["sid"] in ends:
            s["ended"] = ends[s["sid"]]
        elif cl_ended:
            last = max(cl_ended, key=lambda c: c.get("ended") or 0)
            s["ended"] = {"at": iso(last.get("ended")), "reason": last.get("reason")}
        else:
            s["ended"] = None
        sessions.append(s)
    unlinked = link_commits(sessions, day_commits(lo, hi))
    T = totals_of(sessions, unlinked, board_day(lo, hi))
    prev_fp = os.path.join(out, "%s.json" % (datetime.date.fromisoformat(date) - datetime.timedelta(days=1)).isoformat())
    prev = None
    if os.path.exists(prev_fp):
        try:
            prev = json.load(open(prev_fp, encoding="utf-8"))
        except Exception:
            prev = None
    tz = datetime.datetime.now().astimezone().strftime("%z")
    doc = dict(nikki=1, date=date, tz=tz[:3] + ":" + tz[3:], window={"lo": iso(lo), "hi": iso(hi)},
               sessions=sorted(sessions, key=lambda s: s["sid"]), totals=T, deltas=deltas_of(T, prev))
    write_atomic(os.path.join(out, date + ".json"), json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    if not json_only:
        write_atomic(os.path.join(out, date + ".md"), render_md(doc))
    if not quiet:
        print("日誌 %s: セッション %d 本・実働 %s・往復 %d → %s" % (date, T["work_sessions"], _h(T["active_min"]),
                                                            T["turns"], os.path.join(out, date + ".md")))
    return doc


# ----------------------------------------------------------------- 週
def _touch_counts(lo, hi):
    """その週に足した/直した知識の器 — メモリ・教訓・スキル・役・CLAUDE.md のコミット数。"""
    out = {}
    paths = {"教訓": ["docs/lessons.md"], "スキル": ["Tools/Skills"], "役・規則": [".claude", "CLAUDE.md"],
             "日誌": ["docs/Nikki"]}
    for k, ps in paths.items():
        try:
            r = subprocess.run(["git", "-C", MAIN_ROOT, "log", "--all", "--oneline", "--since=@%d" % int(lo),
                                "--until=@%d" % int(hi), "--"] + ps, capture_output=True, text=True, timeout=20)
            out[k] = len([ln for ln in r.stdout.split("\n") if ln.strip()])
        except Exception:
            out[k] = 0
    mem = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                       "-" + MAIN_ROOT.strip("/").replace("/", "-"), "memory")
    out["メモリ(更新ファイル)"] = sum(1 for f in glob.glob(os.path.join(mem, "*.md")) if lo <= os.path.getmtime(f) < hi)
    return out


def week(end, out=None):
    out = out or NIKKI_DIR
    e = datetime.date.fromisoformat(end)
    days = [(e - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    docs = []
    for d in days:
        fp = os.path.join(out, d + ".json")
        if os.path.exists(fp):
            try:
                docs.append(json.load(open(fp, encoding="utf-8")))
            except Exception:
                pass
    prev_days = [(e - datetime.timedelta(days=i)).isoformat() for i in range(13, 6, -1)]
    prev = []
    for d in prev_days:
        fp = os.path.join(out, d + ".json")
        if os.path.exists(fp):
            try:
                prev.append(json.load(open(fp, encoding="utf-8")))
            except Exception:
                pass

    def agg(ds):
        A = dict(days=len(ds), active_min=0.0, turns=0, users=0, compacts=0, read=0, commits=0, review_fails=0,
                 stop_blocks=0, guard_denies=0, tool_errors=0, wait_min=0.0)
        lab, roles, ests = collections.Counter(), collections.defaultdict(lambda: dict(calls=0, min=0.0)), collections.Counter()
        for d in ds:
            T = d["totals"]
            for k in ("active_min", "turns", "users", "compacts", "commits", "review_fails", "stop_blocks",
                      "guard_denies", "tool_errors", "wait_min"):
                A[k] += T.get(k) or 0
            A["read"] += (T.get("tokens") or {}).get("read") or 0
            for s in d["sessions"]:
                if s["kind"] != "work":
                    continue
                for k, v in s["time"]["labels"].items():
                    lab[k] += v
                ests[s["estate"]] += s["active_min"]
            for r, a in (T.get("by_role") or {}).items():
                roles[r]["calls"] += a["calls"]; roles[r]["min"] += a["min"]
                if a.get("inner"):
                    add_inner(roles[r].setdefault("inner", {}), a["inner"])
        return A, lab, roles, ests

    A, lab, roles, ests = agg(docs)
    P = agg(prev)[0] if prev else None
    iso_y, iso_w, _ = e.isocalendar()
    name = "week-%04d-W%02d" % (iso_y, iso_w)
    lo = datetime.datetime.combine(e - datetime.timedelta(days=6), datetime.time()).astimezone().timestamp()
    hi = datetime.datetime.combine(e + datetime.timedelta(days=1), datetime.time()).astimezone().timestamp()
    touched = _touch_counts(lo, hi)
    L = ["# 週の日誌 %s(%s 〜 %s)" % (name, days[0], days[-1]), "",
         "日誌のある日 %d/7。数値は各日の json の和。" % A["days"], "",
         "## 週の総括", "", "| 指標 | 今週 | 前週 | 差 |", "|---|---|---|---|"]
    for k, lab_k in (("active_min", "実働(分)"), ("turns", "往復"), ("users", "人間の発話"), ("read", "読み(トークン)"),
                     ("compacts", "圧縮"), ("commits", "コミット"), ("review_fails", "検分 fail"),
                     ("stop_blocks", "Stop の差し戻し"), ("guard_denies", "門番の拒否"), ("tool_errors", "道具のエラー"),
                     ("wait_min", "Unity 待ち(分)")):
        a = A[k]; p = P[k] if P else None
        fa = TR.fmt_m(a) if k == "read" else ("%.0f" % a)
        fp_ = ("-" if p is None else (TR.fmt_m(p) if k == "read" else "%.0f" % p))
        fd = ("-" if p is None else ("%+.0f" % (a - p)))
        L.append("| %s | %s | %s | %s |" % (lab_k, fa, fp_, fd))
    L += ["", "## 時間の行き先(週・上位 %d)" % TOP_N, "", "| 何に | 分 | 実働比 |", "|---|---|---|"]
    for k, v in lab.most_common(TOP_N):
        L.append("| %s | %.0f | %s |" % (k, v, _pct(v, A["active_min"])))
    L += ["", "## 邸ごとの実働", "", "| 邸 | 実働 |", "|---|---|"]
    for k, v in ests.most_common():
        L.append("| %s | %s |" % (k, _h(v)))
    L += ["", "## 役ごと", "", "| 役 | 呼出 | 合計分 | 平均分 |", "|---|---|---|---|"]
    for r, a in sorted(roles.items(), key=lambda kv: -kv[1]["min"]):
        L.append("| %s | %d | %.0f | %.1f |" % (r, a["calls"], a["min"], a["min"] / max(1, a["calls"])))
    inner = [(r, a["inner"]) for r, a in sorted(roles.items(), key=lambda kv: -kv[1]["min"]) if a.get("inner")]
    if inner:
        L += ["", "## 役の中の内訳(週・1 回あたり)", "", INNER_NOTE, ""] + INNER_HEAD + [inner_row(r, acc) for r, acc in inner]
    L += ["", "## 今週足した・直した知識の器(コミット数)", "", "| 器 | 件 |", "|---|---|"]
    for k, v in touched.items():
        L.append("| %s | %d |" % (k, v))
    L += ["", "## 日ごと", "", "| 日 | 本 | 実働 | 往復 | 圧縮 | fail | 差し戻し | commit | 手戻り上位 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for d in docs:
        T = d["totals"]
        L.append("| %s | %d | %s | %d | %d | %d | %d | %d | %s |" % (
            d["date"], T["work_sessions"], _h(T["active_min"]), T["turns"], T["compacts"], T["review_fails"],
            T["stop_blocks"], T["commits"], (T["rework_top"][0][0][:40] if T["rework_top"] else "-")))
    L += ["", "週次の処置(統合・畳み・昇格・前週比の評価)は /teire が行い、その報告とコミットに残す。"]
    fp = os.path.join(out, name + ".md")
    write_atomic(fp, "\n".join(L) + "\n")
    print("週の日誌 %s: 日誌 %d/7 日・実働 %s → %s" % (name, A["days"], _h(A["active_min"]), fp))
    return fp


# ----------------------------------------------------------------- 入口
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    yday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    p = sub.add_parser("digest", help="1 日ぶんの日誌(json+md)を書く")
    p.add_argument("--date", default=yday)
    p.add_argument("--out", help="書き先(既定 docs/Nikki。自動タスクは scratchpad を渡し、作業ツリーへ書かない)")
    p.add_argument("--json-only", action="store_true")
    p = sub.add_parser("week", help="直近 7 日を束ねる")
    p.add_argument("--end", default=datetime.date.today().isoformat())
    p.add_argument("--out")
    p = sub.add_parser("sessions", help="候補の transcript と判定した邸(デバッグ)")
    p.add_argument("--date", default=yday)
    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        return 1
    if getattr(a, "out", None) is None and a.cmd in ("digest", "week"):
        if os.path.abspath(os.getcwd()) != os.path.abspath(MAIN_ROOT):
            print("⚠ 書き先は main の作業ツリー %s(worktree からでもここへ落ちる)" % NIKKI_DIR, file=sys.stderr)
    if a.cmd == "digest":
        digest(a.date, a.out, a.json_only)
        return 0
    if a.cmd == "week":
        week(a.end, a.out)
        return 0
    if a.cmd == "sessions":
        lo, hi = day_window(a.date)
        claims = load_claims(lo, hi)
        board_owners = load_board_owners()
        for fp, hint in candidate_files(lo, hi).items():
            s = scan_session(fp, lo, hi, {}, hint)
            e, ph, src = estate_of(s, claims, board_owners)
            print("%s %-22s %-14s %-4s %-6s 実働 %6.1f 往復 %4d %s" % (
                s["sid"], (s["title"] or "-")[:22], e, ph, src, s["active_min"], s["turns"], s["kind"]))
        return 0


if __name__ == "__main__":
    sys.exit(main())
