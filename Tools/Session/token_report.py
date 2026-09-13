#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""トークン勘定 — 普請場の費用を「文脈の大きさ × 往復の数」で測る(計画 E-1・2026-09-13)。

【なぜ要るか】2026-09-13 の調査で、主+サブで約 29B トークンの読みが 19 日で出ていた。
主セッションの読みの 44% が文脈 300K 超、検分 1 巡(三役)≈ 50M、検図方の回答 平均 10.4K 字。
どれも「規則はあるが測っていない」ので破られていた。⭕ 直したら、ここで測って効いたかを見る。

【何を測るか】`~/.claude/projects/<この repo>/*.jsonl`(主セッション)と `*/subagents/*.jsonl`
(サブエージェント)の `usage` 欄。
  1. 主セッション: 往復・文脈>300K/400K の割合・圧縮回数・cache_read・エージェント呼出
  2. 役ごと(subagent_type): 呼出・往復/呼出・読み/呼出・最終回答の字数
  3. 自走の巡: ユーザー入力なしに「指図方 → 検分役」が何回連なったか(三巡則)
  4. 報告の質: ユーザー向け最終文の字数・【裁定/報告】見出し率・記号密度・機構語

【使い方】
    python3 Tools/Session/token_report.py                # 直近 14 日・全部
    python3 Tools/Session/token_report.py --since 2026-09-06
    python3 Tools/Session/token_report.py --session 439215b2   # 1 本だけ詳しく
    python3 Tools/Session/token_report.py --self               # いまのセッションの文脈(挨拶用・1行)

⚠ 読むだけ。何も書かない。transcript は数十 MB あるので --since で絞る(全部で 4GB)。
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJ = os.path.join(HOME, ".claude", "projects", "-" + REPO.strip("/").replace("/", "-"))
REVIEWERS = ("edo-kenzu", "edo-kosho", "edo-niwashi")
MECH_WORDS = ("_check", "感度試験", "破壊試験", "母集団", "結線", "関門", "指紋", "台帳")
ROLE_WORDS = ("検図方", "考証方", "庭方", "指図方", "棟梁", "部材方", "在庫方", "普請検査")
MARKS = "⭕⛔⭐⚠"


def _iter(fp):
    with open(fp, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except Exception:
                continue


def _ctx(u):
    return ((u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
            + (u.get("cache_creation_input_tokens") or 0))


def _text_of(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


def last_context(fp):
    """transcript の末尾から、最後の assistant の文脈(トークン)を読む。フック用に軽く(末尾 256KB)。"""
    try:
        size = os.path.getsize(fp)
        with open(fp, "rb") as fh:
            fh.seek(max(0, size - 256 * 1024))
            tail = fh.read().decode("utf-8", errors="replace").split("\n")
    except OSError:
        return None
    for line in reversed(tail):
        if '"usage"' not in line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "assistant":
            u = (e.get("message") or {}).get("usage") or {}
            if u:
                return _ctx(u)
    return None


def last_user_ts(fp):
    """transcript の末尾から、最後の**人間の**発話の時刻(ISO)を読む。三巡則の reset に使う。"""
    try:
        size = os.path.getsize(fp)
        with open(fp, "rb") as fh:
            fh.seek(max(0, size - 4 * 1024 * 1024))
            tail = fh.read().decode("utf-8", errors="replace").split("\n")
    except OSError:
        return None
    for line in reversed(tail):
        if '"type":"user"' not in line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") != "user" or e.get("isMeta"):
            continue
        c = (e.get("message") or {}).get("content")
        if isinstance(c, str) and c.strip() and not c.lstrip().startswith("<"):
            return e.get("timestamp")
    return None


def scan_main(fp, since):
    """主セッション 1 本の集計。"""
    r = dict(sid=os.path.basename(fp)[:8], title="-", first=None, last=None, turns=0, users=0,
             read=0, write=0, out=0, maxctx=0, over300=0, over400=0, compacts=0,
             agents=collections.Counter(), board_posts=0, msgs=[], streak_max=0, streaks=[])
    last_txt = None
    seen_rev, rounds, last_u = False, 0, ""
    for e in _iter(fp):
        t = e.get("type")
        if t == "custom-title":
            r["title"] = e.get("customTitle") or "-"
            continue
        ts = e.get("timestamp") or ""
        if ts:
            r["first"] = r["first"] or ts
            r["last"] = ts
        if t == "system" and e.get("subtype") == "compact_boundary":
            r["compacts"] += 1
        elif t == "assistant":
            m = e.get("message") or {}
            u = m.get("usage") or {}
            if u:
                r["turns"] += 1
                r["read"] += u.get("cache_read_input_tokens") or 0
                r["write"] += u.get("cache_creation_input_tokens") or 0
                r["out"] += u.get("output_tokens") or 0
                c = _ctx(u)
                r["maxctx"] = max(r["maxctx"], c)
                r["over300"] += c > 300000
                r["over400"] += c > 400000
            for x in m.get("content") or []:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "tool_use":
                    inp = x.get("input") or {}
                    if x.get("name") == "Agent":
                        st = inp.get("subagent_type") or "general"
                        r["agents"][st] += 1
                        if st == "edo-sashizukata":
                            if seen_rev:
                                rounds += 1
                                seen_rev = False
                        elif st in REVIEWERS:
                            seen_rev = True
                    elif x.get("name") == "Bash" and "edo_board.py post" in (inp.get("command") or ""):
                        r["board_posts"] += 1
                elif x.get("type") == "text" and len(x.get("text") or "") > 200:
                    last_txt = x["text"]
        elif t == "user" and not e.get("isMeta"):
            s = _text_of((e.get("message") or {}).get("content"))
            if s.strip() and not s.lstrip().startswith("<"):
                r["users"] += 1
                if rounds:
                    r["streaks"].append((rounds, last_u))
                    r["streak_max"] = max(r["streak_max"], rounds)
                rounds, seen_rev, last_u = 0, False, s[:30].replace("\n", " ")
                if last_txt:
                    r["msgs"].append(last_txt)
                    last_txt = None
    if rounds:
        r["streaks"].append((rounds, last_u))
        r["streak_max"] = max(r["streak_max"], rounds)
    return r


def report_quality(msgs):
    n = len(msgs)
    if not n:
        return None
    L = [len(m) for m in msgs]
    hdr = sum(1 for m in msgs if re.search(r"【(裁定|質問|報告|共有)", m))
    marks = sum(sum(m.count(k) for k in MARKS) for m in msgs)
    mech = sum(1 for m in msgs if any(w in m for w in MECH_WORDS))
    roles = sum(sum(m.count(w) for w in ROLE_WORDS) for m in msgs)
    over = sum(1 for m in msgs if len(m) > 2000)
    return dict(n=n, mean=sum(L) / n, over2000=over, hdr=hdr / n, marks=marks / n,
                mech=mech / n, roles=roles / n)


def agent_map():
    """サブエージェントの transcript(agent-<id>.jsonl)→ subagent_type の対応を主 transcript から引く。"""
    amap = {}
    for fp in glob.glob(os.path.join(PROJ, "*.jsonl")):
        pend = {}
        for e in _iter(fp):
            if e.get("type") == "assistant":
                for x in (e.get("message") or {}).get("content") or []:
                    if isinstance(x, dict) and x.get("type") == "tool_use" and x.get("name") == "Agent":
                        pend[x["id"]] = (x.get("input") or {}).get("subagent_type") or "general"
            elif e.get("type") == "user" and pend:
                c = (e.get("message") or {}).get("content")
                if not isinstance(c, list):
                    continue
                for x in c:
                    if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("tool_use_id") in pend:
                        m = re.search(r"agentId: ([0-9a-f]+)", _text_of(x.get("content")))
                        if m:
                            amap[m.group(1)] = pend[x["tool_use_id"]]
    return amap


def scan_subagents(since, amap):
    by = collections.defaultdict(lambda: dict(calls=0, turns=0, read=0, out=0, final=[], maxturns=0))
    for fp in glob.glob(os.path.join(PROJ, "*", "subagents", "*.jsonl")):
        aid = os.path.basename(fp)[:-6].replace("agent-", "")
        role = amap.get(aid, "?")
        turns, read, out, last_text, last = 0, 0, 0, "", ""
        for e in _iter(fp):
            if e.get("timestamp"):
                last = e["timestamp"]
            if e.get("type") != "assistant":
                continue
            m = e.get("message") or {}
            u = m.get("usage") or {}
            if u:
                turns += 1
                read += u.get("cache_read_input_tokens") or 0
                out += u.get("output_tokens") or 0
            for x in m.get("content") or []:
                if isinstance(x, dict) and x.get("type") == "text":
                    last_text = x.get("text") or ""
        if last < since:
            continue
        b = by[role]
        b["calls"] += 1
        b["turns"] += turns
        b["read"] += read
        b["out"] += out
        b["final"].append(len(last_text))
        b["maxturns"] = max(b["maxturns"], turns)
    return by


def fmt_m(n):
    return "%.1fM" % (n / 1e6) if n < 1e9 else "%.2fB" % (n / 1e9)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--since", default=(datetime.date.today() - datetime.timedelta(days=14)).isoformat())
    ap.add_argument("--session", help="セッション id の先頭数桁。1 本だけ詳しく")
    ap.add_argument("--self", action="store_true", help="いまのセッション(最新更新の transcript)の文脈を1行")
    ap.add_argument("--no-sub", action="store_true", help="サブエージェントの集計を飛ばす(速い)")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(PROJ, "*.jsonl")), key=os.path.getmtime, reverse=True)
    if a.self:
        fp = os.environ.get("EDO_TRANSCRIPT") or (files[0] if files else None)
        c = last_context(fp) if fp else None
        print("文脈 %s" % ("%dK" % (c // 1000) if c else "?"))
        return 0
    if a.session:
        files = [f for f in files if os.path.basename(f).startswith(a.session)]
    rows = []
    for fp in files:
        if datetime.datetime.fromtimestamp(os.path.getmtime(fp)).date().isoformat() < a.since:
            continue
        r = scan_main(fp, a.since)
        if r["turns"] and (r["last"] or "") >= a.since:
            rows.append(r)
    rows.sort(key=lambda r: -r["read"])
    print("■ 主セッション(%s 以降・%d 本)  往復 | >300K | >400K | 圧縮 | cache_read | 呼出 | 自走の巡の最大" % (a.since, len(rows)))
    tot = collections.Counter()
    for r in rows:
        tot["turns"] += r["turns"]; tot["read"] += r["read"]; tot["o3"] += r["over300"]
        print("  %s %-20s %5d | %3d%% | %3d%% | %d | %7s | %3d | %d"
              % (r["sid"], r["title"][:20], r["turns"],
                 100 * r["over300"] // max(1, r["turns"]), 100 * r["over400"] // max(1, r["turns"]),
                 r["compacts"], fmt_m(r["read"]), sum(r["agents"].values()), r["streak_max"]))
    if tot["turns"]:
        print("  合計: 往復 %d / cache_read %s / 文脈>300K の往復 %d%%"
              % (tot["turns"], fmt_m(tot["read"]), 100 * tot["o3"] // tot["turns"]))
    print("\n■ 報告の質(ユーザー向け最終文)  通数 | 平均字 | 2000字超 | 見出し率 | 記号/通 | 役名/通 | 機構語を含む通")
    for r in rows:
        q = report_quality(r["msgs"])
        if q:
            print("  %s %-20s %4d | %5.0f | %3d | %3.0f%% | %4.1f | %4.1f | %3.0f%%"
                  % (r["sid"], r["title"][:20], q["n"], q["mean"], q["over2000"],
                     100 * q["hdr"], q["marks"], q["roles"], 100 * q["mech"]))
    if a.session:
        for r in rows:
            print("\n■ %s の自走の巡(ユーザー入力なしの 指図方→検分 の連鎖)" % r["sid"])
            for n, u in sorted(r["streaks"], key=lambda s: -s[0])[:5]:
                print("   %d 巡  — 直前のユーザー発話: %s" % (n, u))
            print("   エージェント呼出: %s" % dict(r["agents"]))
    if a.no_sub:
        return 0
    by = scan_subagents(a.since, agent_map())
    print("\n■ 役ごと(サブエージェント)  呼出 | 往復/呼出(最大) | 読み/呼出 | 最終回答 平均字(最大) | 合計読み")
    for role, b in sorted(by.items(), key=lambda kv: -kv[1]["read"]):
        n = max(1, b["calls"])
        print("  %-18s %4d | %4d (%4d) | %7s | %5.0f (%5d) | %s"
              % (role, b["calls"], b["turns"] // n, b["maxturns"], fmt_m(b["read"] / n),
                 sum(b["final"]) / n, max(b["final"] or [0]), fmt_m(b["read"])))
    rev = [by[r] for r in REVIEWERS if r in by]
    if rev:
        calls = max(1, min(b["calls"] for b in rev))
        print("  ⇒ 検分 1 巡(三役)の読み ≈ %s / 回答 ≈ %.0f 字"
              % (fmt_m(sum(b["read"] / max(1, b["calls"]) for b in rev)),
                 sum(sum(b["final"]) / max(1, b["calls"]) for b in rev)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
