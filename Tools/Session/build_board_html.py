#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""司令塔ダッシュボードの生成器 — 掲示板・_pending・git log・claim を1枚の HTML に焼く。

指図の html が json から決定的に組まれるのと同じ思想。手で書かない。
入力(すべて読み取りのみ):
  - .git/edo-board/EDO-*.json      … 掲示板(正典は各ファイル)
  - docs/Sashizu/<邸>_sashizu.json … `_pending`(正典。件数と鍵だけ見せる、中身は写さない)
  - git log --all                  … 全ブランチ(worktree ブランチ含む)の直近の動き
  - .git/edo-locks/*.json          … 生きているセッション(edo_session.load_all)
  - docs/Sashizu/README.md         … 状態列(正典は README のまま。パースして表示するだけ)
出力:
  - .git/edo-board/_pm/dashboard.html … Artifact に公開する1枚
  - .git/edo-board/_pm/summary.json   … 司令塔の巡回用の機械可読サマリ(巡数・最終活動など)
"""
import html, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edo_session import _common_git_dir, load_all as load_claims

ROOT = os.path.dirname(_common_git_dir())
BOARD = os.path.join(_common_git_dir(), "edo-board")
OUT = os.path.join(BOARD, "_pm")
ESTATES = {"matsudaira": "松江松平邸", "sanno": "山王社", "okabe": "岡部邸", "doi": "土井邸"}
LOG_DAYS = 7

KANJI = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def kanji_int(s):
    """漢数字(〜99)→int。「十一」=11、「二十三」=23。"""
    if s.isdigit():
        return int(s)
    n, m = 0, re.match(r"([一二三四五六七八九]?)(十?)([一二三四五六七八九]?)$", s)
    if not m:
        return None
    a, ju, b = m.groups()
    if ju:
        n = (KANJI.get(a, 1)) * 10 + KANJI.get(b, 0)
    else:
        n = KANJI.get(a, 0)
    return n or None


def junsu(subject):
    """コミット件名から検図/考証の巡数を拾う。無ければ None。"""
    for pat in (r"検図\s*([0-9一二三四五六七八九十]+)\s*巡",
                r"考証\s*([0-9一二三四五六七八九十]+)\s*巡",
                r"([0-9一二三四五六七八九十]+)\s*巡目"):
        m = re.search(pat, subject)
        if m:
            v = kanji_int(m.group(1))
            if v:
                return v
    return None


def estate_of_paths(paths):
    for p in paths:
        for e in ESTATES:
            if re.search(r"(?i)(%s|%s)" % (e, {"matsudaira": "Matsudaira", "sanno": "Sanno",
                                               "okabe": "Okabe", "doi": "Doi"}[e]), p):
                return e
    return None


def load_issues():
    out = []
    if os.path.isdir(BOARD):
        for fn in sorted(os.listdir(BOARD)):
            if re.match(r"EDO-\d+\.json$", fn):
                try:
                    out.append(json.load(open(os.path.join(BOARD, fn), encoding="utf-8")))
                except Exception:
                    pass
    return out


def load_pending():
    out = {}
    for e in ESTATES:
        fp = os.path.join(ROOT, "docs", "Sashizu", "%s_sashizu.json" % e)
        try:
            p = json.load(open(fp, encoding="utf-8")).get("_pending") or {}
        except Exception:
            p = {}
        keys = list(p.keys()) if isinstance(p, dict) else ["(%d件)" % len(p)]
        out[e] = {"count": len(p), "keys": keys}
    return out


def load_readme_states():
    out = {}
    fp = os.path.join(ROOT, "docs", "Sashizu", "README.md")
    try:
        for ln in open(fp, encoding="utf-8"):
            m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*\[(\w+)_sashizu\.html\]", ln)
            if m and m.group(4) in ESTATES:
                out[m.group(4)] = {"name": m.group(1), "area": m.group(2),
                                   "state": m.group(3).strip("* ")}
    except Exception:
        pass
    return out


def load_commits():
    """全ブランチの直近 LOG_DAYS 日のコミット(邸タグ・巡数つき、新しい順)。"""
    raw = subprocess.run(
        ["git", "-C", ROOT, "log", "--all", "--since=%d days ago" % LOG_DAYS,
         "--date-order", "--pretty=%x01%h|%ct|%s", "--name-only"],
        capture_output=True, text=True).stdout
    commits = []
    for blk in raw.split("\x01"):
        if not blk.strip():
            continue
        lines = blk.strip("\n").split("\n")
        h, ct, s = lines[0].split("|", 2)
        paths = [l for l in lines[1:] if l.strip()]
        commits.append({"h": h, "t": int(ct), "s": s,
                        "estate": estate_of_paths(paths), "junsu": junsu(s)})
    return commits


def build_summary(issues, pending, commits, claims):
    est = {}
    for e in ESTATES:
        mine = [c for c in commits if c["estate"] == e]
        rounds = [c for c in mine if c["junsu"]]
        est[e] = {
            "latest_commit": ({"h": mine[0]["h"], "t": mine[0]["t"], "s": mine[0]["s"]}
                              if mine else None),
            "commits_7d": len(mine),
            "junsu_latest": rounds[0]["junsu"] if rounds else None,
            "junsu_log": [{"t": c["t"], "n": c["junsu"]} for c in rounds][:20],
            "pending_count": pending[e]["count"],
            "open_issues": [i["id"] for i in issues
                            if i["estate"] == e and i["status"] not in ("done", "dropped")],
        }
    return {
        "generated": time.time(),
        "estates": est,
        "claims": [{"session": c["session"], "hb_min": (time.time() - c["heartbeat"]) / 60,
                    "note": c.get("note", ""), "paths": c.get("paths", []),
                    "resources": c.get("resources", []), "cwd": c.get("cwd", "")}
                   for c in claims],
        "issues": {"awaiting_user": [i["id"] for i in issues if i["status"] == "awaiting-user"],
                   "blockers": [i["id"] for i in issues
                                if i["type"] == "blocker" and i["status"] not in ("done", "dropped")],
                   "open_total": len([i for i in issues if i["status"] not in ("done", "dropped")])},
    }


# ────────────────────────────────────────────── HTML
def esc(s):
    return html.escape(str(s), quote=True)


def ago(t):
    m = (time.time() - t) / 60
    return ("%.0f日前" % (m / 1440) if m >= 1440 else
            "%.0f時間前" % (m / 60) if m >= 60 else "%.0f分前" % max(0, m))


CSS = """
:root{
  --bg:#F4F1E8; --card:#FCFAF4; --line:#DDD6C6; --ink:#26241E; --muted:#6E6759;
  --ai:#33518F; --ai-soft:#E4E9F4; --shu:#AE392A; --shu-soft:#F5E4E0;
  --oud:#8A6218; --oud-soft:#F1E8D4; --matsu:#4A7042; --matsu-soft:#E3EBDF;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#181A20; --card:#20232B; --line:#343846; --ink:#E6E2D6; --muted:#98917F;
  --ai:#8AA5DD; --ai-soft:#28324A; --shu:#E0705B; --shu-soft:#432823;
  --oud:#D0A354; --oud-soft:#3D3322;
  --matsu:#82AC77; --matsu-soft:#28352A;
}}
:root[data-theme="dark"]{
  --bg:#181A20; --card:#20232B; --line:#343846; --ink:#E6E2D6; --muted:#98917F;
  --ai:#8AA5DD; --ai-soft:#28324A; --shu:#E0705B; --shu-soft:#432823;
  --oud:#D0A354; --oud-soft:#3D3322; --matsu:#82AC77; --matsu-soft:#28352A;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:'Noto Sans JP',system-ui,sans-serif;font-size:14px;line-height:1.65}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 64px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:14px;margin-bottom:6px}
h1{font-family:'Shippori Mincho',serif;font-weight:600;font-size:26px;margin:0;letter-spacing:.04em}
.gen{color:var(--muted);font-size:12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 26px}
.chip{padding:3px 12px;border-radius:99px;font-size:12.5px;border:1px solid var(--line);background:var(--card)}
.chip b{font-family:var(--mono)}
.chip.crit{background:var(--shu-soft);border-color:var(--shu);color:var(--shu)}
.chip.wait{background:var(--oud-soft);border-color:var(--oud);color:var(--oud)}
.chip.ok{background:var(--matsu-soft);border-color:var(--matsu);color:var(--matsu)}
h2{font-family:'Shippori Mincho',serif;font-weight:600;font-size:17px;
  border-bottom:2px solid var(--ink);padding-bottom:5px;margin:34px 0 14px;letter-spacing:.06em}
.dcard{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--oud);
  border-radius:6px;padding:14px 18px;margin-bottom:12px}
.dcard h3{margin:0 0 8px;font-size:15px}
.dcard .id{font-family:var(--mono);color:var(--muted);font-size:12px;margin-right:8px}
.dl{display:grid;grid-template-columns:4.5em 1fr;gap:3px 12px;font-size:13.5px}
.dl dt{color:var(--muted)}.dl dd{margin:0}
.dl .rec{color:var(--ai);font-weight:600}
.lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:14px}
.lane{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:14px 16px}
.lane h3{font-family:'Shippori Mincho',serif;font-size:16px;margin:0;letter-spacing:.05em}
.lane .area{color:var(--muted);font-size:11.5px;margin-bottom:8px}
.state{font-size:12.5px;background:var(--ai-soft);color:var(--ai);
  border-radius:4px;padding:2px 8px;display:inline-block;margin:4px 0}
.kv{font-size:12.5px;color:var(--muted);margin:3px 0}
.kv b{color:var(--ink);font-weight:500}
.kv .n{font-family:var(--mono)}
.iss{font-size:12.5px;margin:6px 0 0;padding:0;list-style:none}
.iss li{padding:4px 8px;border-left:3px solid var(--line);margin-bottom:4px;background:var(--bg);border-radius:0 4px 4px 0}
.iss li.blocker{border-left-color:var(--shu)}
.iss li.awaiting-user{border-left-color:var(--oud)}
.iss .id{font-family:var(--mono);font-size:11px;color:var(--muted)}
.feed{font-size:13px;border-collapse:collapse;width:100%}
.feed td{padding:4px 10px 4px 0;border-bottom:1px solid var(--line);vertical-align:top}
.feed .t{white-space:nowrap;color:var(--muted);font-family:var(--mono);font-size:11.5px}
.feed .e{white-space:nowrap;color:var(--ai);font-size:12px}
.feed .h{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
.scroll{overflow-x:auto}
.quiet{color:var(--matsu);background:var(--matsu-soft);border:1px solid var(--matsu);
  border-radius:6px;padding:9px 14px;font-size:13.5px}
footer{margin-top:40px;color:var(--muted);font-size:11.5px}
"""


def issue_li(i):
    return ('<li class="%s"><span class="id">%s</span> %s <span class="id">[%s/%s]</span></li>'
            % (esc(i["type"] if i["type"] == "blocker" else i["status"]),
               esc(i["id"]), esc(i["title"]), esc(i["type"]), esc(i["status"])))


def build_html(issues, pending, commits, claims, states, summary):
    live = [i for i in issues if i["status"] not in ("done", "dropped")]
    waits = [i for i in live if i["status"] == "awaiting-user"]
    blks = [i for i in live if i["type"] == "blocker"]
    p = []
    p.append("<title>赤坂普請 司令塔</title>")
    p.append('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             'family=Shippori+Mincho:wght@600&family=Noto+Sans+JP:wght@400;500;700&'
             'family=IBM+Plex+Mono:wght@400;500&display=swap">')
    p.append("<style>%s</style>" % CSS)
    p.append('<div class="wrap">')
    p.append('<header><h1>赤坂普請 司令塔</h1><span class="gen">巡回 %s</span></header>'
             % esc(time.strftime("%m-%d %H:%M")))
    p.append('<div class="chips">')
    p.append('<span class="chip %s">要裁定 <b>%d</b></span>' % ("wait" if waits else "ok", len(waits)))
    p.append('<span class="chip %s">ブロッカー <b>%d</b></span>' % ("crit" if blks else "ok", len(blks)))
    p.append('<span class="chip">open <b>%d</b></span>' % len(live))
    p.append('<span class="chip">生きているセッション <b>%d</b></span>' % len(claims))
    p.append("</div>")

    # ── 要裁定
    p.append("<h2>要裁定 — ユーザーの判断待ち</h2>")
    if not waits:
        p.append('<div class="quiet">裁定待ちはありません。</div>')
    for i in waits:
        d = i.get("decision") or {}
        p.append('<div class="dcard"><h3><span class="id">%s</span>[%s] %s</h3>'
                 % (esc(i["id"]), esc(ESTATES.get(i["estate"], i["estate"])), esc(i["title"])))
        if d:
            p.append('<dl class="dl">')
            p.append("<dt>背景</dt><dd>%s</dd>" % esc(d.get("background", "")))
            p.append("<dt>選択肢</dt><dd>%s</dd>"
                     % "<br>".join(esc(o) for o in d.get("options", [])))
            p.append('<dt>推奨</dt><dd class="rec">%s</dd>' % esc(d.get("recommend", "")))
            p.append("<dt>影響</dt><dd>%s</dd>" % esc(d.get("impact", "")))
            p.append("</dl>")
        p.append("</div>")

    # ── 邸別レーン
    p.append("<h2>邸別</h2><div class='lanes'>")
    for e, name in ESTATES.items():
        s = summary["estates"][e]
        st = states.get(e, {})
        cl = [c for c in claims if any(g == "sashizu:%s" % e for g in c.get("paths", []))]
        p.append('<div class="lane"><h3>%s</h3><div class="area">%s</div>' % (
            esc(name), esc(st.get("area", ""))))
        if st.get("state"):
            p.append('<span class="state">%s</span>' % esc(st["state"]))
        if cl:
            for c in cl:
                p.append('<div class="kv">担当: <b class="n">%s</b>(心拍 %.0f分前)%s</div>'
                         % (esc(c["session"][:12]), (time.time() - c["heartbeat"]) / 60,
                            " — " + esc(c["note"]) if c.get("note") else ""))
        else:
            p.append('<div class="kv">担当セッションなし</div>')
        if s["latest_commit"]:
            lc = s["latest_commit"]
            p.append('<div class="kv">最新: <span class="n">%s</span> %s<br><b>%s</b></div>'
                     % (esc(lc["h"]), esc(ago(lc["t"])), esc(lc["s"][:60])))
        p.append('<div class="kv">7日のコミット <b class="n">%d</b> ／ 検図・考証 <b class="n">%s</b>'
                 '巡 ／ _pending <b class="n">%d</b>件</div>'
                 % (s["commits_7d"], s["junsu_latest"] or "—", s["pending_count"]))
        lane_iss = [i for i in live if i["estate"] == e]
        if lane_iss:
            p.append('<ul class="iss">%s</ul>' % "".join(issue_li(i) for i in lane_iss))
        p.append("</div>")
    p.append("</div>")

    # ── 横断
    cross = [i for i in live if i["estate"] in ("cross", "infra")]
    p.append("<h2>横断・基盤</h2>")
    p.append('<ul class="iss">%s</ul>' % "".join(issue_li(i) for i in cross)
             if cross else '<div class="quiet">横断の open issue はありません。</div>')

    # ── 最近の動き
    p.append("<h2>最近の動き(全ブランチ)</h2><div class='scroll'><table class='feed'>")
    for c in commits[:20]:
        p.append('<tr><td class="t">%s</td><td class="e">%s</td>'
                 '<td class="h">%s</td><td>%s</td></tr>'
                 % (esc(ago(c["t"])), esc(ESTATES.get(c["estate"], "—")),
                    esc(c["h"]), esc(c["s"])))
    p.append("</table></div>")

    p.append("<footer>Tools/Session/build_board_html.py が生成。正典: "
             ".git/edo-board(issue)/ docs/Sashizu/*_sashizu.json(_pending)/ "
             "docs/Sashizu/README.md(状態)。作法: docs/session-board.md</footer>")
    p.append("</div>")
    return "\n".join(p)


def main():
    issues = load_issues()
    pending = load_pending()
    commits = load_commits()
    claims = load_claims()
    states = load_readme_states()
    summary = build_summary(issues, pending, commits, claims)
    os.makedirs(OUT, exist_ok=True)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "dashboard.html"), "w", encoding="utf-8").write(
        build_html(issues, pending, commits, claims, states, summary))
    print("dashboard: %s\nsummary:   %s" % (os.path.join(OUT, "dashboard.html"),
                                            os.path.join(OUT, "summary.json")))


if __name__ == "__main__":
    main()
