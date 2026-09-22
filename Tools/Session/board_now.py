#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""普請場の今 — Unity の座(いま誰が使い、誰が何分待っているか)と、窓ごとの時間の帯(2026-09-22)。

【読むもの】どれも読むだけ。何も書き換えない。
    edo_session.load_all() / q_load()      生きている claim と Unity の待ち行列
    <git-common-dir>/edo-nikki/claims.jsonl 畳まれた claim の履歴(いつ Unity を使い、いつ返したか)

【使う側】
    build_board_html.py   一枚の「今」タブ(html())と、敷地別タブの邸ごとの小さな帯(lane_html())
    repo_graph.py         系図の「いま動いている普請」の場所(html())

⭐ 資源の出入りは **edo-nikki/resources.jsonl**(edo_session._res_log)が実測で持つ。
   取る・返す・取り上げ・失効・並ぶ・降りるの 6 つ。帯の朱と斜線はここから引く。
   ⚠ この記録より前に取られた資源は事跡が無いので、前の持ち手が返した時刻から推定し、
   画面に「推定」と出す(記録が一巡すれば自然に消える)。
⭐ **終わった仕事は日を越えて残す(2026-09-22 施主指示)。** 窓を閉じると claim は消えるので、
   `edo_session.py finish` が claims.jsonl へ書く `reason="finish"` の行が唯一の事跡。
   閉じた票・要した時間つきで「終わった仕事」の節に出す(既定 14 日ぶん)。
⛔ 進み具合(「9/16」など)は描かない。仕事の段を記録する口がまだ無く、勘で書かせると嘘になる。
⭐ **窓の今(EDO-0364・2026-09-22 施主指示「毎度『今どういう状況?』と聞いて回るのをやめたい」)。**
   `.claude/hooks/edo_now.py` が刻む `<git-common-dir>/edo-session/<sid>.now.json` を読み、
   **SHOW_S 秒を超えて続く待ちだけ**を札に出す(コンパイル待ち・保存待ち・役の帰り待ち・Blender・
   施主の指示待ち)。それより短い物は「働いている」とだけ出す — 細かい作業を板に映さない。
   終わった待ち(`edo-nikki/waits.jsonl`)は帯に灰の斜線で残す。

    python3 Tools/Session/board_now.py --selftest
    python3 Tools/Session/board_now.py --out X.html      # 単体で刷る(確認用)
"""
import glob
import html as _html
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

WIN_MIN = 180          # 帯が見せる幅(分)。左端が3時間前、右端が今
FIN_DAYS = 14          # 「終わった仕事」を何日ぶん残すか(掲示板の「古び」と同じ 14 日)
FIN_MAX = 12           # 節に並べる本数の上限(残りは「ほか N 本」)
LIVE_MIN = 15.0        # この心拍以内を「動いている」と数える(TTL は 45 分)
SHOW_S = 60.0          # これを超えて続く待ちだけ札に出す(edo_now.LOG_S と同じ 60 秒。短い物は板に映さない)
STATE_TTL_S = 45 * 60  # 窓の今がこれより古ければ「不明」(claim の TTL と同じ)
esc = lambda s: _html.escape(str(s), quote=True)
hm = lambda t: time.strftime("%H:%M", time.localtime(t))


def _ticket(note):
    m = re.search(r"EDO-\d{4}", note or "")
    return m.group(0) if m else ""


def _title(note):
    n = re.sub(r"^\[[^\]]+\]\s*", "", note or "")
    n = re.sub(r"^EDO-\d{4}\s*(続き)?[::]?\s*", "", n)
    return n.strip()


def _files_title(paths):
    fs = [os.path.basename(p) for p in paths if not p.startswith("sashizu:")]
    if not fs:
        return ""
    return fs[0] + (" ほか" if len(fs) > 1 else "")


def session_name(sid):
    """窓(claim)の短い ID から、そのセッションの**名前**(サイドバーに出る題)を引く。
    正体は会話の記録(~/.claude/projects/*/<sid>*.jsonl)の `custom-title`。無ければ空文字。
    ⚠ 記録は大きい(数十MB)ので、末尾 4MB → 先頭 1MB だけを見る。題は追記されるので末尾が新しい。"""
    import glob as _g
    for f in _g.glob(os.path.expanduser("~/.claude/projects/*/%s*.jsonl" % sid)):
        try:
            size = os.path.getsize(f)
            with open(f, "rb") as fh:
                for a, n in ((max(0, size - 4_000_000), 4_000_000), (0, 1_000_000)):
                    fh.seek(a)
                    hits = re.findall(rb'"type":"custom-title","customTitle":"((?:[^"\\]|\\.)*)"', fh.read(n))
                    if hits:
                        return json.loads(b'"' + hits[-1] + b'"')
        except Exception:
            continue
    return ""


def load_res_events(path=None, max_bytes=2_000_000):
    """資源の出入りの記録(append-only)を新しい順の逆=時刻順で返す。無ければ空。
    ⚠ 後ろから max_bytes だけ読む — 先頭の 1 行は欠けうるので捨てる。"""
    if path is None:
        try:
            import edo_session as es
            path = es.RESLOG
        except Exception:
            return []
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            raw = f.read()
        lines = raw.decode("utf-8", "ignore").split("\n")
        if size > max_bytes:
            lines = lines[1:]
    except Exception:
        return []
    out = []
    for l in lines:
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    out.sort(key=lambda e: e.get("t", 0))
    return out


def _gitdir():
    try:
        import edo_session as es
        return os.path.dirname(es.LOCKS)
    except Exception:
        return None


def load_states(sids, gitdir=None):
    """窓の今(edo_now.py が刻む `<sid>.now.json`)を sid ごとに。無い窓は {}。"""
    g = gitdir or _gitdir()
    out = {}
    for s in sids:
        try:
            out[s] = json.load(open(os.path.join(g, "edo-session", s + ".now.json"), encoding="utf-8"))
        except Exception:
            out[s] = {}
    return out


def load_waits(path=None, since=0.0, max_bytes=1_000_000):
    """終わった待ち(`edo-nikki/waits.jsonl`・60 秒以上続いた物だけ)。`since` より後に終わった行。"""
    if path is None:
        g = _gitdir()
        if not g:
            return []
        path = os.path.join(g, "edo-nikki", "waits.jsonl")
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            lines = f.read().decode("utf-8", "ignore").split("\n")
        if size > max_bytes:
            lines = lines[1:]
    except Exception:
        return []
    out = []
    for l in lines:
        if l.strip():
            try:
                r = json.loads(l)
                if r.get("t1", 0) > since:
                    out.append(r)
            except Exception:
                pass
    return out


def _work(st, now):
    """「働いている」と言ってよいのは**刻みが新しいとき**だけ(EDO-0366)。
    ⚠ 窓は `finish` を通らずに閉じることもある(施主がタブを閉じる・落ちる)。そのとき刻みは
    最後の道具呼び出しのまま止まるので、古い刻みを『働いている』と読むと、閉じた窓が
    最大 45 分のあいだ働いて見える(2026-09-22 施主指摘)。止まっていることを表に出す。"""
    at = st.get("at") or 0
    if now - at > LIVE_MIN * 60:
        return dict(kind="stale", label="刻みが止まっている", since=at)
    return dict(kind="work", label="働いている", since=at)


def window_state(st, now, show_s=SHOW_S):
    """窓の今を一つに畳む。戻り値 dict(kind, label, since)。
    kind: busy=道具の返事を show_s 秒超えて待っている / agent=背景の役の帰り待ち /
          paused=手を止めた直後(show_s 未満) / idle=手が空いている(施主の指示待ち) /
          work=働いている / stale=刻みが止まっている(窓が閉じたかも) / ""=不明(刻みが無い・古い)。
    ⭐ stack の**一番外側**が「窓として」待っている物(役の中の Bash ではなく、役の帰り)。
    ⛔ **手を止めた(Stop)を「施主の指示待ち」と読み替えない**(2026-09-22 施主指摘「施主の指示待ちと
       なっていますが、実際にはなってません」)。黄を出してよいのは次の二つを両方満たすときだけ:
         ① 背景の役(`await`)が一つも残っていない — 残っていれば窓は自分で動き出す
         ② 手を止めてから show_s 秒を超えた — 関門(report_lint)が Stop を差し戻して仕事が続くことがあり、
            板は Stop の直後に焼かれるので、直後の黄は嘘になりやすい
       数えるのは `.claude/hooks/edo_now.py` の `pending_agents`(記録の尾を読む)。"""
    if not st or now - (st.get("at") or 0) > STATE_TTL_S:
        return dict(kind="", label="", since=None)
    stack = st.get("stack") or []
    if stack:
        e = stack[0]
        if now - e.get("since", now) >= show_s:
            lab = e.get("kind", "") + (("(%s)" % e["detail"]) if e.get("detail") else "")
            sub = st.get("sub")
            if sub and e.get("tool") == "Agent" and sub.get("tool"):
                lab += "・役の中: " + sub["tool"].split("__")[-1]
            return dict(kind="busy", label=lab, since=e["since"])
        return _work(st, now)
    if st.get("idle_since"):
        aw = st.get("await") or []
        if aw:
            who = "・".join(dict.fromkeys((a.get("who") or "役") for a in aw))
            return dict(kind="agent", label="%s の帰りを待つ(背景)" % who[:28],
                        since=min(a.get("since") or st["idle_since"] for a in aw))
        if now - st["idle_since"] < show_s:
            return dict(kind="paused", label="手を止めた", since=st["idle_since"])
        return dict(kind="idle", label="手が空いている(施主の指示待ち)", since=st["idle_since"])
    return _work(st, now)


def res_spans(events, resource="unity"):
    """出入りの記録を区間へ畳む。戻り値 {(session, 種別): [(始, 終 or None)]}。
    種別は "unity"(使っていた)と "wait"(待っていた)。終わりが None なら今も続いている。"""
    open_, spans = {}, {}
    for e in events:
        if e.get("resource") != resource:
            continue
        sid, ev, t = e.get("session", ""), e.get("event"), e.get("t", 0)
        kind = {"take": "unity", "wait": "wait"}.get(ev)
        end = {"release": "unity", "steal": "unity", "expire": "unity", "unwait": "wait"}.get(ev)
        if kind:
            open_.setdefault((sid, kind), t)          # 二重の take は最初を採る
        elif end:
            a = open_.pop((sid, end), None)
            if a is not None:
                spans.setdefault((sid, end), []).append((a, t))
    for (sid, kind), a in open_.items():
        spans.setdefault((sid, kind), []).append((a, None))
    return spans


def load_claim_log(path=None, since=0.0):
    """畳まれた claim の履歴(append-only)を時刻順で返す。`since` より後に終わった行だけ。"""
    if path is None:
        try:
            import edo_session as es
            path = os.path.join(os.path.dirname(es.LOCKS), "edo-nikki", "claims.jsonl")
        except Exception:
            return []
    out = []
    if path and os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if r.get("ended", 0) > since:
                out.append(r)
    out.sort(key=lambda r: r.get("ended", 0))
    return out


def fin_rows(log, now, days=FIN_DAYS, namer=None):
    """**終わった仕事**(`edo_session.py finish` の行)を新しい順に畳む。1行=1つの仕舞い。
    ⭐ 窓が閉じると claim は消えるので、日を越えても残るのはこの行だけ(2026-09-22 施主指示)。"""
    namer = namer or session_name
    out = []
    for r in log:
        if r.get("reason") != "finish" or r.get("ended", 0) < now - days * 86400:
            continue
        out.append(dict(sid=r.get("session", ""), name=namer(r.get("session", "")),
                        title=_title(r.get("note")) or _files_title(r.get("paths") or []) or "(名乗りなし)",
                        ended=r.get("ended", 0), started=r.get("started") or 0,
                        closed=list(r.get("closed") or []), kept=list(r.get("kept") or []),
                        task=list(r.get("task") or []), result=r.get("result") or "",
                        estates=list(r.get("estate") or [])))
    out.sort(key=lambda w: -w["ended"])
    return out


def collect(now=None, live=None, queue=None, hist=None, ticket_estate=None, win_min=WIN_MIN, namer=None, events=None,
            fins=None, fin_days=FIN_DAYS, states=None, waits=None):
    """窓ごとの行を集める。live/queue/hist/fins は試験のために差し替えられる。
    ticket_estate={"EDO-0354": "typology"} — 名乗りの票番号から邸を引く(claim に sashizu: が無い窓のため)。"""
    now = now or time.time()
    t0 = now - win_min * 60
    ticket_estate = ticket_estate or {}
    namer = namer or session_name
    if events is None:
        events = load_res_events()
    spans = res_spans(events)
    if live is None or queue is None or hist is None or fins is None:
        import edo_session as es
        if live is None:
            live = es.load_all()
        if queue is None:
            queue = es.q_load().get("unity", [])
        if hist is None or fins is None:
            log = load_claim_log(since=now - max(fin_days * 86400, win_min * 60))
            if hist is None:
                hist = [r for r in log if r.get("ended", 0) > t0]
            if fins is None:
                fins = fin_rows(log, now, fin_days, namer)
    last_unity_release = max([r["ended"] for r in hist if "unity" in r.get("resources", [])] or [0])

    rows = {}

    def row(sid):
        return rows.setdefault(sid, dict(sid=sid, note="", paths=[], res=[], segs=[], beat=None,
                                         live=False, holder=False, wait_from=None,
                                         state=dict(kind="", label="", since=None)))
    for r in hist:
        w = row(r["session"])
        kind = "work" if (r.get("note") or r.get("paths")) else "mute"
        w["segs"].append((max(r["started"], t0), r["ended"], kind))
        w["note"] = w["note"] or r.get("note", "")
        w["paths"] = w["paths"] or r.get("paths", [])
    # ⭐ 仕舞った窓(`finish` の印がある)は**生きている窓として数えない**(EDO-0366)。
    #   finish のあとの touch() で claim は作り直されるので、そのままだと閉じた窓が
    #   閉じた票の題を掲げて『働いている』と出続けた(2026-09-22 施主指摘)。
    #   終わった事跡は下の「終わった仕事」の節が持つ。
    live = [c for c in live if not c.get("finished")]
    for c in live:
        w = row(c["session"])
        w["live"] = True
        w["beat"] = c.get("heartbeat", now)
        w["note"] = c.get("note") or w["note"]
        w["paths"] = c.get("paths") or w["paths"]
        w["res"] = [x for x in c.get("resources", []) if x != "unity"]
        named = bool(c.get("note") or c.get("paths"))
        w["segs"].append((max(c["started"], t0), w["beat"], "work" if named else "mute"))
        if "unity" in c.get("resources", []):
            w["holder"] = True
            live_span = [sp for sp in spans.get((w["sid"], "unity"), []) if sp[1] is None]
            if live_span:                      # ⭕ 実測(resources.jsonl の take)
                w["hold_from"], w["hold_est"] = live_span[0][0], False
            else:                              # ⚠ 記録より前に取られた — 前の返却からの推定
                w["hold_from"] = max(c["started"], last_unity_release, t0)
                w["hold_est"] = True
                w["segs"].append((max(w["hold_from"], t0), w["beat"], "unity"))
    # ⭐ 窓の今 — 生きている窓だけ。60 秒を超えた待ちは札に、終わった待ちは灰の斜線に
    if states is None:
        states = load_states([c["session"] for c in live])
    if waits is None:
        waits = load_waits(since=t0)
    for c in live:
        w = row(c["session"])
        w["state"] = window_state(states.get(c["session"]) or {}, now)
        if w["state"]["kind"] in ("busy", "agent"):
            w["segs"].append((max(w["state"]["since"], t0), now, "stall"))
    for x in waits:
        if x.get("t1", 0) > t0 and x.get("session"):
            row(x["session"])["segs"].append((max(x.get("t0", t0), t0), x["t1"], "stall"))
    for q in queue:
        w = row(q["session"])
        w["segs"].append((max(q["since"], t0), now, "wait"))
        w["wait_from"] = q["since"]
        w["note"] = w["note"] or q.get("note", "")

    for (sid, kind), sp in spans.items():
        w = row(sid)
        for a, b in sp:
            b = b if b is not None else now
            if b > t0:
                w["segs"].append((max(a, t0), b, kind))
                if kind == "wait" and sp[-1][1] is None:
                    w["wait_from"] = min(w["wait_from"] or a, a)

    named, mute = [], []
    for w in rows.values():
        has = bool(w["note"] or w["paths"] or w["holder"] or w["wait_from"])
        (named if has else mute).append(w)
    for w in named:
        tk = _ticket(w["note"])
        w["ticket"] = tk
        w["name"] = namer(w["sid"])
        w["title"] = _title(w["note"]) or _files_title(w["paths"]) or "(名乗りなし)"
        e = [p[8:] for p in w["paths"] if p.startswith("sashizu:")]
        w["estates"] = e or ([ticket_estate[tk]] if tk in ticket_estate else [])
        w["holds"] = w["estates"] + w["res"] + (["ファイル %d" % len([p for p in w["paths"] if not p.startswith("sashizu:")])]
                                                if [p for p in w["paths"] if not p.startswith("sashizu:")] else [])
        w["quiet"] = w["live"] and (now - w["beat"]) / 60 > LIVE_MIN
    named.sort(key=lambda w: (not w["holder"], w["wait_from"] or 9e12, -max(b for _, b, _ in w["segs"])))
    mute_live = [w for w in mute if w["live"]]
    est = any(w.get("hold_est") for w in named)
    return dict(now=now, t0=t0, win=win_min * 60, rows=named, mute=mute_live,
                est=est, logged=bool(events), fins=list(fins or []), fin_days=fin_days)


# ───────────────────────────── 描く

CSS = """<style>
.bn,.bn-mini{--n-card:var(--card,var(--surface,#fff));--n-line:var(--line,var(--rule,#ccc));--n-soft:var(--line,var(--rule-2,#ddd));
  --n-ink:var(--ink);--n-muted:var(--muted,var(--ink-3));--n-ai:var(--ai);--n-shu:var(--shu);
  --n-oud:var(--oud,var(--odo,#b08000));--n-ok:var(--matsu);
  --n-mute:color-mix(in srgb,var(--n-muted) 45%,var(--n-card));--n-work:color-mix(in srgb,var(--n-ai) 55%,var(--n-card))}
.bn h3{font-size:14px;margin:0 0 8px;letter-spacing:.04em}
.bn .sub{font-size:12px;color:var(--n-muted);margin:0 0 10px}
.bn-seat{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:1px;background:var(--n-line);border:1px solid var(--n-line);margin-bottom:20px}
.bn-hold{background:var(--n-card);padding:14px 16px;border-left:5px solid var(--n-shu)}
.bn-hold.free{border-left-color:var(--n-ok)}
.bn-hold .k{font-size:11px;letter-spacing:.14em;color:var(--n-shu)}
.bn-hold.free .k{color:var(--n-ok)}
.bn-hold .t{font-size:18px;line-height:1.45;margin:3px 0 7px;font-weight:600}
.bn-meta{display:flex;flex-wrap:wrap;gap:3px 12px;font-size:12px;color:var(--n-muted);align-items:baseline}
.bn-sn{display:inline-block;font-size:11px;font-weight:700;line-height:1.5;padding:0 7px;margin-right:6px;border:1px solid var(--n-ink);color:var(--n-ink);background:color-mix(in srgb,var(--n-ink) 7%,var(--n-card));vertical-align:1px}
.bn-tk{font:500 11px ui-monospace,Menlo,monospace;color:var(--n-ai)}
.bn-q{list-style:none;margin:0;padding:4px 0;background:var(--n-card)}
.bn-q li{display:grid;grid-template-columns:40px minmax(0,1fr);gap:0 10px;padding:7px 16px;border-bottom:1px solid var(--n-soft)}
.bn-q li:last-child{border-bottom:0}
.bn-q .no{grid-row:span 2;font-size:17px;font-weight:600;color:var(--n-oud)}
.bn-q .qm{font-size:11.5px;color:var(--n-oud);display:flex;gap:10px;align-items:baseline}
.bn-q .none{display:block;color:var(--n-muted);font-size:12.5px}
.bn-bands{border:1px solid var(--n-line);background:var(--n-card)}
.bn-ln{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:0 14px;align-items:center;padding:7px 14px;border-bottom:1px solid var(--n-soft)}
.bn-bands>div:last-child{border-bottom:0}
.bn-ln.bn-axis{padding-block:4px;background:color-mix(in srgb,var(--n-line) 40%,var(--n-card))}
.bn-lab b{display:block;font-weight:500;font-size:12.5px;line-height:1.45}
.bn-lab span{display:flex;flex-wrap:wrap;gap:0 10px;font-size:10.5px;color:var(--n-muted)}
.bn-lab .has{color:var(--n-ink)}
.bn-ln.bn-quiet .bn-lab b{color:var(--n-muted)}
.bn-tr{position:relative;height:18px;background:repeating-linear-gradient(90deg,transparent 0,transparent calc(100%/6 - 1px),var(--n-soft) calc(100%/6 - 1px),var(--n-soft) calc(100%/6))}
.bn-tr.ticks{background:none;height:16px;font-size:10px;color:var(--n-muted)}
.bn-tr.ticks span{position:absolute;top:0;transform:translateX(-50%);font-variant-numeric:tabular-nums}
.bn-b{position:absolute;top:4px;height:10px;display:block}
.bn-b.mute{background:var(--n-mute)}.bn-b.work{background:var(--n-work)}
.bn-b.unity{background:var(--n-shu);top:1px;height:16px}
.bn-b.wait{top:1px;height:16px;border:1px solid var(--n-oud);background:repeating-linear-gradient(135deg,var(--n-oud) 0 2px,transparent 2px 6px)}
.bn-b.stall{top:2px;height:14px;background:repeating-linear-gradient(135deg,var(--n-muted) 0 2px,transparent 2px 5px);opacity:.75}
.bn-chip.s{border-color:var(--n-shu);color:var(--n-shu);font-weight:600}
.bn-chip.i{border-color:var(--n-oud);color:var(--n-oud);font-weight:600}
.bn-chip.a{border-color:var(--n-ai);color:var(--n-ai)}
.bn-chip.k{border-color:var(--n-ok);color:var(--n-ok)}
/* 窓の今 — いま何を待っているか(60 秒を超えた待ちだけ) */
.bn-now-t{width:100%;border-collapse:collapse;border:1px solid var(--n-line);background:var(--n-card);font-size:12.5px;margin-bottom:20px}
.bn-now-t th,.bn-now-t td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--n-soft);vertical-align:baseline}
.bn-now-t th{font-size:11px;letter-spacing:.08em;color:var(--n-muted);font-weight:500;white-space:nowrap}
.bn-now-t tr:last-child td{border-bottom:0}
.bn-now-t .d{white-space:nowrap;font-variant-numeric:tabular-nums;color:var(--n-muted)}
.bn-now-t .none{color:var(--n-muted);font-size:12px}
.bn-now{position:absolute;right:0;top:-7px;bottom:-7px;width:1px;background:var(--n-ink)}
.bn-ended{margin-top:10px}.bn-ended summary{cursor:pointer;font-size:12.5px;color:var(--n-muted);padding:6px 0}
/* 終わった仕事(手仕舞い)— 窓が閉じても残る唯一の事跡 */
.bn-fin{margin-top:22px}
.bn-fin table{width:100%;border-collapse:collapse;border:1px solid var(--n-line);background:var(--n-card);font-size:12.5px}
.bn-fin th,.bn-fin td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--n-soft);vertical-align:baseline}
.bn-fin th{font-size:11px;letter-spacing:.08em;color:var(--n-muted);font-weight:500;white-space:nowrap}
.bn-fin tr:last-child td{border-bottom:0}
.bn-fin .t,.bn-fin .d{white-space:nowrap;font-variant-numeric:tabular-nums;color:var(--n-muted)}
.bn-fin .ti{color:var(--n-ink)}
.bn-fin .ok{font:500 11px ui-monospace,Menlo,monospace;color:var(--n-ok);border:1px solid var(--n-ok);padding:0 5px;margin-right:4px;white-space:nowrap}
.bn-fin .kept{font-size:11px;color:var(--n-oud)}
.bn-fin .none{font-size:11.5px;color:var(--n-muted)}
.bn-keys{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:11.5px;color:var(--n-muted);margin-top:10px}
.bn-keys span{display:inline-flex;align-items:center;gap:6px}
.bn-keys .bn-b{position:static;width:22px;height:10px}
.bn-fine{font-size:12px;color:var(--n-muted);margin:8px 0 0;max-width:70ch}
/* 敷地別の邸の札の中の小さな帯 */
.bn-mini{margin:6px 0 2px;padding:6px 0 0;border-top:1px dashed var(--n-soft)}
.bn-mini .t{font-size:12px;line-height:1.5;display:flex;flex-wrap:wrap;gap:0 8px;align-items:baseline}
.bn-mini .t b{font-weight:500}
.bn-chip{font-size:10.5px;padding:0 6px;border:1px solid var(--n-line);color:var(--n-muted)}
.bn-chip.u{border-color:var(--n-shu);color:var(--n-shu);font-weight:700}
.bn-chip.w{border-color:var(--n-oud);color:var(--n-oud)}
.bn-mini .bn-tr{height:12px;margin-top:3px}
.bn-mini .bn-b{top:2px;height:8px}.bn-mini .bn-b.unity,.bn-mini .bn-b.wait{top:0;height:12px}
@media(max-width:720px){.bn-seat{grid-template-columns:1fr}.bn-ln{grid-template-columns:1fr;gap:4px}.bn-ln.bn-axis .bn-lab{display:none}}
</style>"""


def _sn(w):
    """セッションの名前の札。名前が引けなければ短い ID を出す(空の札は出さない)。"""
    return '<span class="bn-sn" title="%s">%s</span>' % (esc(w["sid"]), esc(w.get("name") or w["sid"][:8]))


def _track(d, segs):
    out = []
    order = {"mute": 0, "work": 1, "stall": 2, "wait": 3, "unity": 4}
    for a, b, k in sorted(segs, key=lambda x: order[x[2]]):
        if b <= d["t0"]:
            continue
        l = 100.0 * (a - d["t0"]) / d["win"]
        w = max(0.6, 100.0 * (b - a) / d["win"])
        out.append('<i class="bn-b %s" style="left:%.2f%%;width:%.2f%%" title="%s–%s"></i>' % (k, l, min(w, 100 - l), hm(a), hm(b)))
    return "".join(out)


def _ticks(d):
    out, t = [], (int(d["t0"]) // 1800 + 1) * 1800
    while t < d["now"]:
        out.append('<span style="left:%.2f%%">%s</span>' % (100.0 * (t - d["t0"]) / d["win"], hm(t)))
        t += 1800
    return "".join(out)


def _dur(a, b):
    if not a or not b or b <= a:
        return "—"
    m = (b - a) / 60.0
    return "%d分" % m if m < 90 else "%.1f時間" % (m / 60.0)


def _state_chip(w, now):
    """窓の今の札。busy=朱(何を待っているか) / agent=藍(背景の役の帰り待ち・施主は呼ばれていない) /
    idle=黄(施主の指示待ち) / paused=灰(手を止めた直後・まだ黄にしない) / work=緑 /
    stale=灰(刻みが止まっている)。不明なら空。"""
    s = w.get("state") or {}
    k = s.get("kind")
    if not k:
        return ""
    mins = ((now - s["since"]) / 60) if s.get("since") else 0
    if k == "busy":
        return '<span class="bn-chip s">⏳ %s %d分</span>' % (esc(s["label"]), mins)
    if k == "agent":
        return '<span class="bn-chip a">⏳ %s %d分</span>' % (esc(s["label"]), mins)
    if k == "idle":
        return '<span class="bn-chip i">%s %d分</span>' % (esc(s["label"]), mins)
    if k in ("stale", "paused"):
        return '<span class="none">%s(%d分)</span>' % (esc(s["label"]), mins)
    return '<span class="bn-chip k">%s</span>' % esc(s["label"])


def _now_table(d):
    """**窓の今** — 生きている名乗りありの窓を一行ずつ。「今どういう状況?」への答えはこの表。"""
    now = d["now"]
    live = [w for w in d["rows"] if w["live"]]
    p = ['<h3>窓の今</h3><p class="sub">一行が一つの窓。<b>黄=施主を待っている窓</b>を上に出す。'
         '藍は背景の役の帰り待ち(施主は呼ばれていない)、朱は道具の返事待ち(%d 秒を超えた物だけ)、'
         '短い待ちは「働いている」。</p>' % SHOW_S]
    if not live:
        return "".join(p) + '<p class="none">生きている窓は無い。</p>'
    p.append('<table class="bn-now-t"><tr><th>窓</th><th>仕事</th><th>今</th><th>から</th></tr>')
    order = {"idle": 0, "busy": 1, "agent": 2, "paused": 3, "work": 4, "stale": 5, "": 6}   # 施主を待つ窓が先頭
    for w in sorted(live, key=lambda w: (order.get(w["state"]["kind"], 6), -(w["beat"] or 0))):
        s = w["state"]
        p.append('<tr><td>%s</td><td>%s%s</td><td>%s</td><td class="d">%s</td></tr>'
                 % (_sn(w), ('<b class="bn-tk">%s</b> ' % esc(w["ticket"])) if w["ticket"] else "", esc(w["title"][:40]),
                    _state_chip(w, now) or '<span class="none">刻みなし(窓の今が届いていない)</span>',
                    esc(hm(s["since"])) if s.get("since") and s["kind"] != "work" else "—"))
    p.append("</table>")
    return "".join(p)


def summary_rows(d):
    """summary.json 用 — 生きている窓の今を機械可読で(名・仕事・票・状態・何分)。"""
    now = d["now"]
    return [dict(sid=w["sid"], name=w.get("name", ""), title=w["title"], ticket=w.get("ticket", ""),
                 state=w["state"]["kind"], label=w["state"]["label"],
                 min=round((now - w["state"]["since"]) / 60, 1) if w["state"].get("since") else None,
                 holder=w["holder"], estates=w.get("estates", []))
            for w in d["rows"] if w["live"]]


def _fin_html(d):
    """**終わった仕事**の節。窓が閉じると claim は消えるので、日を越えて残るのはここだけ。
    正典は `edo-nikki/claims.jsonl` の `reason="finish"` の行(`edo_session.py finish` が書く)。"""
    fins, days = d.get("fins") or [], d.get("fin_days", FIN_DAYS)
    p = ['<div class="bn-fin"><h3>終わった仕事</h3>'
         '<p class="sub">1行=1つの仕舞い。窓が閉じても %d 日ぶん残る — '
         "どの票を閉じ、どれだけ掛かったか。</p>" % days]
    if not fins:
        return "".join(p) + ('<p class="none">この %d 日に仕舞われた仕事は無い。'
                             "仕事が終わったら <b>edo_session.py finish --task EDO-xxxx</b> で"
                             "票を閉じて窓を閉じる — その一手だけがここに残る。</p></div>" % days)
    p.append("<table><tr><th>仕舞った</th><th>窓</th><th>仕事</th><th>閉じた票</th><th>掛かった</th></tr>")
    for w in fins[:FIN_MAX]:
        tk = "".join('<span class="ok">%s</span>' % esc(x) for x in w["closed"])
        if not tk:
            tk = '<span class="kept">票は閉じず%s</span>' % (
                "(" + esc("・".join(w["task"])) + ")" if w["task"] else "(票なし)")
        if w["kept"]:
            tk += '<span class="kept">残 %d</span>' % len(w["kept"])
        p.append('<tr><td class="t">%s</td><td>%s</td><td class="ti">%s</td><td>%s</td>'
                 '<td class="d">%s</td></tr>'
                 % (esc(time.strftime("%m-%d %H:%M", time.localtime(w["ended"]))),
                    _sn(w), esc(w["title"][:46]), tk, esc(_dur(w["started"], w["ended"]))))
    p.append("</table>")
    if len(fins) > FIN_MAX:
        p.append('<p class="none">ほか %d 本(生ログは edo-nikki/claims.jsonl)</p>' % (len(fins) - FIN_MAX))
    p.append("</div>")
    return "".join(p)


def html(d=None, css=True):
    """一枚の「今」タブ(と系図の先頭)に置く節。css=False なら <style> を付けない(頁に既にある場合)。"""
    d = d or collect()
    now, rows = d["now"], d["rows"]
    holder = next((w for w in rows if w["holder"]), None)
    waiters = [w for w in rows if w["wait_from"]]
    waiters.sort(key=lambda w: w["wait_from"])
    p = [CSS if css else "", '<div class="bn">']
    p.append('<h3>Unity の座</h3><p class="sub">一度に一人しか使えない。いま誰が使い、誰が何分待っているか。</p><div class="bn-seat">')
    if holder:
        p.append('<div class="bn-hold"><div class="k">いま使っている</div><div class="t">%s</div>'
                 '<div class="bn-meta">%s<span>%s から(%d分)%s</span><span>%s</span>%s</div></div>'
                 % (_sn(holder) + " " + esc(holder["title"]), ('<b class="bn-tk">%s</b>' % esc(holder["ticket"])) if holder["ticket"] else "",
                    hm(holder["hold_from"]), (now - holder["hold_from"]) / 60,
                    "・推定" if holder.get("hold_est") else "", esc(holder["sid"][:8]), _state_chip(holder, now)))
    else:
        p.append('<div class="bn-hold free"><div class="k">いま使っている</div><div class="t">空いている</div></div>')
    p.append('<ol class="bn-q">')
    for i, w in enumerate(waiters, 1):
        p.append('<li><span class="no">%d番</span><span>%s</span><span class="qm">%s<span>%d分待ち</span></span></li>'
                 % (i, _sn(w) + " " + esc(w["title"]), ('<b class="bn-tk">%s</b>' % esc(w["ticket"])) if w["ticket"] else "",
                    (now - w["wait_from"]) / 60))
    if not waiters:
        p.append('<li class="none">待っている人はいない</li>')
    p.append("</ol></div>")
    p.append(_now_table(d))

    p.append('<h3>窓ごとの時間の帯</h3><p class="sub">一行が一つの窓。左が3時間前、右端(縦線)が今。</p>')
    p.append('<div class="bn-bands"><div class="bn-ln bn-axis"><div class="bn-lab"></div><div class="bn-tr ticks">%s</div></div>' % _ticks(d))
    def one(w):
        beat = ("心拍 %d分前" % ((now - w["beat"]) / 60)) if w["live"] else "終了"
        return ('<div class="bn-ln%s"><div class="bn-lab"><b>%s</b><span>%s<i>%s</i><i>%s</i><i class="has">%s</i>%s</span></div>'
                 '<div class="bn-tr">%s<em class="bn-now"></em></div></div>'
                 % (" bn-quiet" if (not w["live"] or w["quiet"]) else "", _sn(w) + " " + esc(w["title"][:46]),
                    ('<i class="bn-tk">%s</i>' % esc(w["ticket"])) if w["ticket"] else "", esc(w["sid"][:8]), beat,
                    esc(" ・ ".join(w["holds"])), _state_chip(w, now), _track(d, w["segs"])))
    active = [w for w in rows if w["live"] or w["holder"] or w["wait_from"]]
    ended = [w for w in rows if w not in active]
    p.extend(one(w) for w in active)
    if d["mute"]:
        segs = [sg for w in d["mute"] for sg in w["segs"]]
        p.append('<div class="bn-ln bn-quiet"><div class="bn-lab"><b>何をしているか名乗っていない窓 %d 本</b>'
                 '<span><i>仕事の名を帯に出せない</i></span></div><div class="bn-tr">%s<em class="bn-now"></em></div></div>'
                 % (len(d["mute"]), _track(d, segs)))
    if ended:
        p.append('</div><details class="bn-ended"><summary>この3時間に終わった窓 %d 本</summary><div class="bn-bands">%s</div></details><div>'
                 % (len(ended), "".join(one(w) for w in ended)))
    p.append('</div><div class="bn-keys"><span><i class="bn-b unity"></i>Unity を使っている</span>'
             '<span><i class="bn-b wait"></i>Unity を待っている</span><span><i class="bn-b work"></i>仕事の名乗りあり</span>'
             '<span><i class="bn-b mute"></i>名乗りなし</span><span><i class="bn-b stall"></i>%d 秒を超えた待ち(コンパイル・保存・役の帰りなど)</span></div>'
             '<p class="bn-fine">%s窓の名は claim の名乗りから出している。</p>'
             % (SHOW_S,
                "⚠ この窓が Unity を取った事跡が記録より前にあるため、朱の帯の左端は前の持ち手が返した時刻からの推定。"
                if d.get("est") else
                "朱と斜線は資源の出入りの記録(取った・返した・並んだ)の実測。"))
    p.append(_fin_html(d))
    p.append("</div>")
    return "".join(p)


def lane_html(d, estate):
    """敷地別タブの邸の札に足す小さな帯。その邸を持つ窓(なければ空文字)。CSS は「今」の節が持つ。"""
    es = {estate} if isinstance(estate, str) else set(estate)     # 「全体・基盤」は infra と cross の二つ
    mine = [w for w in d["rows"] if es & set(w["estates"]) and (w["live"] or w["holder"] or w["wait_from"])]
    if not mine:
        return ""
    p = []
    for w in mine:
        chips = ""
        if w["holder"]:
            chips += '<span class="bn-chip u">Unity 使用中</span>'
        elif w["wait_from"]:
            chips += '<span class="bn-chip w">Unity %d分待ち</span>' % ((d["now"] - w["wait_from"]) / 60)
        chips += _state_chip(w, d["now"])
        p.append('<div class="bn-mini"><div class="t">%s<b>%s</b>%s<span class="bn-chip">心拍 %s</span></div>'
                 '<div class="bn-tr">%s<em class="bn-now"></em></div></div>'
                 % (_sn(w), esc(w["title"][:40]), chips,
                    ("%d分前" % ((d["now"] - w["beat"]) / 60)) if w["beat"] else "—", _track(d, w["segs"])))
    return "".join(p)


def selftest():
    n = 1_800_000_000.0
    live = [dict(session="aaaaaaaa-111", started=n - 5000, heartbeat=n - 30, paths=["sashizu:typology", "x/A.cs"],
                 resources=["unity"], note="EDO-0354 寺社の建て直し"),
            dict(session="bbbbbbbb-222", started=n - 900, heartbeat=n - 60 * 20, paths=[], resources=[], note="")]
    queue = [dict(session="cccccccc-333", since=n - 600, note="EDO-0355: 棟割")]
    hist = [dict(session="dddddddd-444", started=n - 7000, ended=n - 4000, resources=["unity"], paths=[], note="x", reason="release")]
    ev = [dict(t=n - 7000, session="dddddddd-444", resource="unity", event="take"),
          dict(t=n - 4000, session="dddddddd-444", resource="unity", event="release"),
          dict(t=n - 3000, session="aaaaaaaa-111", resource="unity", event="take"),
          dict(t=n - 600, session="cccccccc-333", resource="unity", event="wait")]
    sp = res_spans(ev)
    assert sp[("dddddddd-444", "unity")] == [(n - 7000, n - 4000)], sp      # 閉じた区間
    assert sp[("aaaaaaaa-111", "unity")] == [(n - 3000, None)], sp          # まだ持っている
    # 窓の今: A は 3 分前から検図方の帰りを待つ(役の中は Bash)、B は手を止めて 20 分
    states = {"aaaaaaaa-111": {"at": n - 10, "stack": [{"tool": "Agent", "kind": "検図方 の帰りを待つ", "detail": "", "since": n - 180}],
                               "sub": {"role": "検図方", "tool": "Bash", "since": n - 10}},
              "bbbbbbbb-222": {"at": n - 1200, "stack": [], "idle_since": n - 1200}}
    waits = [dict(session="aaaaaaaa-111", t0=n - 2000, t1=n - 1700, kind="コンパイル待ち", detail="", tool="mcp__unityMCP__refresh_unity")]
    d = collect(now=n, live=live, queue=queue, hist=hist, events=ev, ticket_estate={"EDO-0355": "typology"},
                namer=lambda sid: {"aaaaaaaa-111": "名前A"}.get(sid, ""), states=states, waits=waits)
    sA = d["rows"][0]["state"]
    assert sA["kind"] == "busy" and sA["label"] == "検図方 の帰りを待つ・役の中: Bash" and sA["since"] == n - 180, sA
    assert any(k == "stall" for _, _, k in d["rows"][0]["segs"]), "今の待ちと終わった待ちは灰の斜線"
    assert window_state({"at": n - 5, "stack": [{"tool": "Bash", "kind": "x", "since": n - 30}]}, n)["kind"] == "work", "60 秒未満は働いている"
    assert window_state({"at": n - 3600 * 2, "stack": []}, n)["kind"] == "", "古い刻みは不明"
    assert window_state({}, n)["kind"] == "", "刻みが無ければ不明"
    # EDO-0366: 刻みが止まった窓を「働いている」と言わない(finish を通らず閉じた窓)
    assert window_state({"at": n - (LIVE_MIN + 5) * 60, "stack": []}, n)["kind"] == "stale", "止まった刻みは働いていない"
    assert window_state({"at": n - 60, "stack": []}, n)["kind"] == "work"
    assert window_state({"at": n - 1200, "stack": [], "idle_since": n - 1200}, n)["kind"] == "idle", \
        "手が空いていると自分で言った窓はそのまま(止まった刻みではない)"
    # ⭐ 2026-09-22 施主指摘「施主の指示待ちとなっていますが、実際にはなってません」
    sa = window_state({"at": n - 600, "stack": [], "idle_since": n - 600,
                       "await": [{"who": "棟梁", "since": n - 900}, {"who": "庭方", "since": n - 700}]}, n)
    assert sa["kind"] == "agent" and sa["label"] == "棟梁・庭方 の帰りを待つ(背景)" and sa["since"] == n - 900, sa
    assert window_state({"at": n - 20, "stack": [], "idle_since": n - 20}, n)["kind"] == "paused", \
        "手を止めた直後(60 秒未満)は黄にしない — 関門が Stop を差し戻すことがある"
    assert window_state({"at": n - 90, "stack": [], "idle_since": n - 90}, n)["kind"] == "idle", \
        "60 秒を超えて手が空いていれば黄"
    # EDO-0366: 仕舞った窓は、そのあと claim が作り直されても板の窓ではない
    fin_live = [dict(live[0], finished=n - 300)]
    d4 = collect(now=n, live=fin_live, queue=[], hist=[], events=[], namer=lambda s: "")
    assert not [w for w in d4["rows"] if w["live"]], "仕舞った窓は窓の今に出さない"
    assert "生きている窓は無い" in html(d4), "仕舞った窓だけなら表は空"
    assert d["rows"][0]["hold_from"] == n - 3000 and not d["rows"][0]["hold_est"], "取った時刻は実測"
    assert not d["est"]
    d2 = collect(now=n, live=live, queue=queue, hist=hist, events=[], namer=lambda s: "")
    assert d2["est"] and d2["rows"][0]["hold_est"], "記録が無ければ推定に落ちる"
    assert d["rows"][0]["holder"] and d["rows"][1]["wait_from"], "持ち手が先頭・待ちが次"
    assert len(d["mute"]) == 1 and d["rows"][1]["estates"] == ["typology"]
    out = html(d)
    assert 'class="bn-sn" title="aaaaaaaa-111">名前A' in out and 'title="cccccccc-333">cccccccc' in out   # 名前が無ければ短い ID
    assert "10分待ち" in out and "Unity 使用中" not in out and "1番" in out and "寺社の建て直し" in out
    assert "窓の今" in out and "⏳ 検図方 の帰りを待つ・役の中: Bash 3分" in out, out[:200]
    # 黄(施主待ち)が先頭・藍(背景の役待ち)は施主を呼ばない — 表の並びごと検める
    live2 = [dict(session="gggggggg-777", started=n - 3000, heartbeat=n - 20, paths=[], resources=[],
                  note="EDO-0400 藍の窓"),
             dict(session="hhhhhhhh-888", started=n - 3000, heartbeat=n - 20, paths=[], resources=[],
                  note="EDO-0401 黄の窓")]
    st2 = {"gggggggg-777": {"at": n - 300, "stack": [], "idle_since": n - 300,
                            "await": [{"who": "棟梁", "since": n - 480}]},
           "hhhhhhhh-888": {"at": n - 300, "stack": [], "idle_since": n - 300}}
    d5 = collect(now=n, live=live2, queue=[], hist=[], events=[], namer=lambda s: "", states=st2, waits=[])
    o5 = html(d5)
    assert "⏳ 棟梁 の帰りを待つ(背景) 8分" in o5 and "手が空いている(施主の指示待ち) 5分" in o5, o5[:400]
    assert o5.index("EDO-0401") < o5.index("EDO-0400"), "黄(施主待ち)の窓が先頭"
    assert [r["state"] for r in summary_rows(d5)].count("agent") == 1
    assert "手が空いている(施主の指示待ち) 20分" not in out, "名乗りの無い窓 B は表に出ない(名乗りなしの帯に畳む)"
    sr = summary_rows(d)
    assert sr and sr[0]["state"] == "busy" and sr[0]["min"] == 3.0, sr
    assert "⏳ 検図方" in lane_html(d, "typology")
    assert "Unity 使用中" in lane_html(d, "typology") or "10分待ち" in lane_html(d, "typology")
    assert "終わった仕事" in out and "この 14 日に仕舞われた仕事は無い" in out    # 仕舞いが無い日も節は出す
    # 仕舞い(finish)の行は窓が消えても残る — 閉じた票と掛かった時間を出す
    log = [dict(session="eeeeeeee-555", started=n - 86400 * 2 - 5400, ended=n - 86400 * 2,
                reason="finish", note="EDO-0361: 日誌の邸引き", paths=["sashizu:infra"],
                closed=["EDO-0361"], kept=["EDO-0360"], task=["EDO-0361"]),
           dict(session="ffffffff-666", started=n - 9000, ended=n - 8000, reason="release", note="x")]
    fr = fin_rows(log, n, namer=lambda s: "名前E")
    assert len(fr) == 1 and fr[0]["closed"] == ["EDO-0361"], fr      # release は仕舞いではない
    assert fr[0]["ended"] < n - 86400, "日を越えた仕舞いも残る"
    d3 = collect(now=n, live=[], queue=[], hist=[], fins=fr)
    h3 = html(d3)
    assert "EDO-0361" in h3 and "1.5時間" in h3 and "残 1" in h3 and "名前E" in h3, h3
    assert fin_rows(log, n, days=1, namer=lambda s: "") == [], "古い仕舞いは落ちる"
    assert html(collect(now=n, live=[], queue=[], hist=[]), css=False).count("空いている") == 1
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
        page = '<meta charset="utf-8"><body style="max-width:1000px;margin:24px auto;padding:0 16px;font:14px sans-serif">' + html()
        if out:
            open(out, "w", encoding="utf-8").write(page)
            print("刷った:", out)
        else:
            print(page)
