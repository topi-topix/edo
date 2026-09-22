#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""普請場の今 — Unity の座(いま誰が使い、誰が何分待っているか)と、窓ごとの時間の帯(2026-09-22)。

【読むもの】どれも読むだけ。何も書き換えない。
    edo_session.load_all() / q_load()      生きている claim と Unity の待ち行列
    <git-common-dir>/edo-nikki/claims.jsonl 畳まれた claim の履歴(いつ Unity を使い、いつ返したか)

【使う側】
    build_board_html.py   一枚の「今」タブ(html())と、敷地別タブの邸ごとの小さな帯(lane_html())
    repo_graph.py         系図の「いま動いている普請」の場所(html())

⚠ Unity を**取った時刻**は記録されていない(claim には `used`=最後に使った時刻しか無い)。
   いまの持ち手の帯の左端は「前の持ち手が返した時刻」から引いた推定で、画面にもそう書く。
   取る・返す・並ぶ時刻を edo_session.py が残すようになったら、ここの推定を実測へ差し替える。
⛔ 進み具合(「9/16」など)は描かない。仕事の段を記録する口がまだ無く、勘で書かせると嘘になる。

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
LIVE_MIN = 15.0        # この心拍以内を「動いている」と数える(TTL は 45 分)
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


def collect(now=None, live=None, queue=None, hist=None, ticket_estate=None, win_min=WIN_MIN, namer=None):
    """窓ごとの行を集める。live/queue/hist は試験のために差し替えられる。
    ticket_estate={"EDO-0354": "typology"} — 名乗りの票番号から邸を引く(claim に sashizu: が無い窓のため)。"""
    now = now or time.time()
    t0 = now - win_min * 60
    ticket_estate = ticket_estate or {}
    namer = namer or session_name
    if live is None or queue is None or hist is None:
        import edo_session as es
        if live is None:
            live = es.load_all()
        if queue is None:
            queue = es.q_load().get("unity", [])
        if hist is None:
            hist = []
            p = os.path.join(os.path.dirname(es.LOCKS), "edo-nikki", "claims.jsonl")
            if os.path.exists(p):
                for l in open(p, encoding="utf-8"):
                    try:
                        r = json.loads(l)
                    except Exception:
                        continue
                    if r.get("ended", 0) > t0:
                        hist.append(r)
    last_unity_release = max([r["ended"] for r in hist if "unity" in r.get("resources", [])] or [0])

    rows = {}

    def row(sid):
        return rows.setdefault(sid, dict(sid=sid, note="", paths=[], res=[], segs=[], beat=None,
                                         live=False, holder=False, wait_from=None))
    for r in hist:
        w = row(r["session"])
        named = bool(r.get("note") or [p for p in r.get("paths", []) if not p.startswith("sashizu:") or True])
        kind = "unity" if "unity" in r.get("resources", []) else ("work" if named and (r.get("note") or r.get("paths")) else "mute")
        w["segs"].append((max(r["started"], t0), r["ended"], kind))
        w["note"] = w["note"] or r.get("note", "")
        w["paths"] = w["paths"] or r.get("paths", [])
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
            a = max(c["started"], last_unity_release, t0)
            w["segs"].append((a, w["beat"], "unity"))
            w["holder"], w["hold_from"] = True, a
    for q in queue:
        w = row(q["session"])
        w["segs"].append((max(q["since"], t0), now, "wait"))
        w["wait_from"] = q["since"]
        w["note"] = w["note"] or q.get("note", "")

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
    return dict(now=now, t0=t0, win=win_min * 60, rows=named, mute=mute_live)


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
.bn-now{position:absolute;right:0;top:-7px;bottom:-7px;width:1px;background:var(--n-ink)}
.bn-ended{margin-top:10px}.bn-ended summary{cursor:pointer;font-size:12.5px;color:var(--n-muted);padding:6px 0}
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
    order = {"mute": 0, "work": 1, "wait": 2, "unity": 3}
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
                 '<div class="bn-meta">%s<span>%s から(%d分)</span><span>%s</span></div></div>'
                 % (_sn(holder) + " " + esc(holder["title"]), ('<b class="bn-tk">%s</b>' % esc(holder["ticket"])) if holder["ticket"] else "",
                    hm(holder["hold_from"]), (now - holder["hold_from"]) / 60, esc(holder["sid"][:8])))
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

    p.append('<h3>窓ごとの時間の帯</h3><p class="sub">一行が一つの窓。左が3時間前、右端(縦線)が今。</p>')
    p.append('<div class="bn-bands"><div class="bn-ln bn-axis"><div class="bn-lab"></div><div class="bn-tr ticks">%s</div></div>' % _ticks(d))
    def one(w):
        beat = ("心拍 %d分前" % ((now - w["beat"]) / 60)) if w["live"] else "終了"
        return ('<div class="bn-ln%s"><div class="bn-lab"><b>%s</b><span>%s<i>%s</i><i>%s</i><i class="has">%s</i></span></div>'
                 '<div class="bn-tr">%s<em class="bn-now"></em></div></div>'
                 % (" bn-quiet" if (not w["live"] or w["quiet"]) else "", _sn(w) + " " + esc(w["title"][:46]),
                    ('<i class="bn-tk">%s</i>' % esc(w["ticket"])) if w["ticket"] else "", esc(w["sid"][:8]), beat,
                    esc(" ・ ".join(w["holds"])), _track(d, w["segs"])))
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
             '<span><i class="bn-b mute"></i>名乗りなし</span></div>'
             '<p class="bn-fine">⚠ Unity を「いつ取ったか」はまだ記録されていない。朱の帯の左端は、前の持ち手が返した時刻から引いた推定。'
             '窓の名は claim の note(名乗り)から出している。</p></div>')
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
    d = collect(now=n, live=live, queue=queue, hist=hist, ticket_estate={"EDO-0355": "typology"},
                namer=lambda sid: {"aaaaaaaa-111": "名前A"}.get(sid, ""))
    assert d["rows"][0]["holder"] and d["rows"][1]["wait_from"], "持ち手が先頭・待ちが次"
    assert len(d["mute"]) == 1 and d["rows"][1]["estates"] == ["typology"]
    out = html(d)
    assert 'class="bn-sn" title="aaaaaaaa-111">名前A' in out and 'title="cccccccc-333">cccccccc' in out   # 名前が無ければ短い ID
    assert "10分待ち" in out and "Unity 使用中" not in out and "1番" in out and "寺社の建て直し" in out
    assert "Unity 使用中" in lane_html(d, "typology") or "10分待ち" in lane_html(d, "typology")
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
