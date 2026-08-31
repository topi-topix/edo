#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作事奉行ダッシュボードの生成器 — 掲示板・_pending・git log・claim を1枚の HTML に焼く。

指図の html が json から決定的に組まれるのと同じ思想。手で書かない。
入力(すべて読み取りのみ):
  - .git/edo-board/EDO-*.json      … 掲示板(正典は各ファイル)
  - docs/Sashizu/<敷地>_sashizu.json … `_pending`(正典。件数と鍵だけ見せる、中身は写さない)
  - git log --all                  … 全ブランチ(worktree ブランチ含む)の直近の動き
  - .git/edo-locks/*.json          … 生きているセッション(edo_session.load_all)
  - docs/Sashizu/README.md         … 状態列(正典は README のまま。パースして表示するだけ)
出力:
  - .git/edo-board/_pm/dashboard.html … Artifact に公開する1枚
  - .git/edo-board/_pm/summary.json   … 作事奉行の巡回用の機械可読サマリ(巡数・最終活動など)

2026-08-29 改訂: 「邸」だけでなく溜池・外堀のような邸に属さない敷地も同格の
グループとして扱えるよう SITES を導入(ユーザー指摘)。あわせてクライアント側の
フィルタ(敷地/種別/完了表示/検索)を付けた — 生成器自体は依然として静的HTMLを
焼くだけで、フィルタは焼いた後にブラウザ側で効く(JSで表示/非表示を切り替えるだけ・
サーバもDBも無い)。
"""
import html, json, os, re, subprocess, sys, time
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edo_session import _common_git_dir, load_all as load_claims

ROOT = os.path.dirname(_common_git_dir())
BOARD = os.path.join(_common_git_dir(), "edo-board")
OUT = os.path.join(BOARD, "_pm")

# 「敷地」= 邸(屋敷)に限らない、地区としてまとまった作業単位。
# 邸(sashizu.json/README の状態列/検図・考証の巡数を持つ)と、それを持たない
# 敷地(例: 外堀・溜池 — 複数邸にまたがるので1邸のものにできない)を区別する。
SITES = {"matsudaira_dewa": "松江松平邸", "sanno": "山王社", "okabe": "岡部邸",
         "doi": "土井邸", "sotobori": "外堀・溜池"}
ESTATES = {"matsudaira_dewa": "松江松平邸", "sanno": "山王社", "okabe": "岡部邸", "doi": "土井邸"}
SHORT = {"matsudaira_dewa": "松", "sanno": "山", "okabe": "岡", "doi": "土", "sotobori": "堀"}
MENTION = {  # 関係図・巡回検知が本文から敷地を拾うときの表記ゆれ(index[1]は path 突合にも使う)
    "matsudaira_dewa": ["松平", "松江", "Matsudaira"],
    "sanno": ["山王", "Sanno"],
    "okabe": ["岡部", "Okabe"],
    "doi": ["土井", "Doi"],
    "sotobori": ["外堀", "Tameike", "溜池", "Sotobori"],
}
CROSS_KEY = "cross"  # cross/infra をまとめた「全体・基盤」の表示上のキー
CROSS_LABEL = "全体・基盤"
TYPE_LABEL = {"decision": "裁定", "blocker": "ブロッカー", "task": "task", "info": "info"}
STATUS_LABEL = {"open": "open", "awaiting-user": "要裁定", "in-progress": "進行中",
                "done": "done", "dropped": "見送り"}
LOG_DAYS = 7
JUNSU_WARN = 3  # 三巡則: ユーザー入力なしにこの巡数を超えたら警告

KANJI = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def kanji_int(s):
    """漢数字(〜99)→int。「十一」=11、「二十三」=23。"""
    if s.isdigit():
        return int(s)
    m = re.match(r"([一二三四五六七八九]?)(十?)([一二三四五六七八九]?)$", s)
    if not m:
        return None
    a, ju, b = m.groups()
    n = (KANJI.get(a, 1)) * 10 + KANJI.get(b, 0) if ju else KANJI.get(a, 0)
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


def site_of_paths(paths):
    for p in paths:
        for e in SITES:
            if re.search(r"(?i)(%s|%s)" % (e, MENTION[e][1]), p):
                return e
    return None


def site_of_commit(paths, subject):
    """パスで当たらなければ件名の表記ゆれでも拾う(パスが本文を代表しない敷地対策)。"""
    e = site_of_paths(paths)
    if e:
        return e
    for site, names in MENTION.items():
        if any(n in subject for n in names):
            return site
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


def display_site(i):
    """issue を表示上どの敷地カードへ出すか。sotobori 等の敷地はそのまま、
    cross/infra は 1枚の「全体・基盤」カードへ畳む。"""
    return i["estate"] if i["estate"] in SITES else CROSS_KEY


def load_pending():
    out = {}
    for e in SITES:
        fp = os.path.join(ROOT, "docs", "Sashizu", "%s_sashizu.json" % e)
        try:
            p = json.load(open(fp, encoding="utf-8")).get("_pending") or {}
        except Exception:
            p = {}
        out[e] = {"count": len(p)}
    return out


def load_reviews():
    """検図関門(Tools/Sashizu/review_gate.py)の結果を敷地ごとに拾う。
    ⚠ 判定のロジックは持たない — review_gate を import して**同じ関数**を呼ぶ。
    ここで判定を書き写すと、関門の改訂に追随せず二重管理になる。"""
    out = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "review_gate", os.path.join(ROOT, "Tools", "Sashizu", "review_gate.py"))
        rg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rg)
    except Exception:
        return out
    for e in SITES:
        try:
            red, rows = rg.gate(e)
            out[e] = {"red": red, "rows": [{"mark": r[0], "label": r[2], "state": r[3]}
                                           for r in rows]}
        except Exception:
            pass
    return out


def load_junsu_baseline():
    """前回ユーザー裁定時点の巡数(作事奉行の巡回状態から)。無ければ空。"""
    fp = os.path.join(OUT, "state.json")
    try:
        return json.load(open(fp, encoding="utf-8")).get("junsu_baseline", {})
    except Exception:
        return {}


def load_readme_states():
    """README の表から敷地ごとの状態と、公開済み指図 Artifact の URL を拾う。
    2026-08-31 に「屋敷・社ごとの設計図」表が状態1列(5列)から**指図/実装の2列(6列)**へ
    改訂された(1軸だと「指図はレビュー待ちだが実装は進んでいる」邸を表せなかったため)。
    「土木の指図」表は5列(状態1列)のまま — 両方に当たる。
    URL は行末の素の https://claude.ai/code/artifact/... 。
    敷地が worktree 止まりで README にまだ載っていなければ単に出ない(それが実情)。"""
    out = {}
    fp = os.path.join(ROOT, "docs", "Sashizu", "README.md")
    pat6 = re.compile(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
                      r"\s*\[(\w+)_sashizu\.html\][^|]*\|\s*(https://\S+)?\s*\|")
    pat5 = re.compile(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*\[(\w+)_sashizu\.html\]"
                      r"[^|]*\|\s*(https://\S+)?\s*\|")
    try:
        for ln in open(fp, encoding="utf-8"):
            m6 = pat6.match(ln)
            if m6 and m6.group(5) in SITES:
                out[m6.group(5)] = {"name": m6.group(1), "area": m6.group(2),
                                    "sashizu_state": m6.group(3).strip("* "),
                                    "impl_state": m6.group(4).strip("* "),
                                    "state": "%s / %s" % (m6.group(3).strip("* "),
                                                          m6.group(4).strip("* ")),
                                    "url": m6.group(6)}
                continue
            m5 = pat5.match(ln)
            if m5 and m5.group(4) in SITES and m5.group(4) not in out:
                out[m5.group(4)] = {"name": m5.group(1), "area": m5.group(2),
                                    "state": m5.group(3).strip("* "), "url": m5.group(5)}
    except Exception:
        pass
    return out


def load_commits():
    """全ブランチの直近 LOG_DAYS 日のコミット(敷地タグ・巡数つき、新しい順)。"""
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
                        "estate": site_of_commit(paths, s), "junsu": junsu(s)})
    return commits


def daily_buckets(commits, estate, days=7):
    """直近 days 日、日別のコミット数(古い→新しい)。"""
    keys = []
    t = time.time()
    for i in range(days - 1, -1, -1):
        keys.append(time.strftime("%Y-%m-%d", time.localtime(t - i * 86400)))
    counts = {k: 0 for k in keys}
    for c in commits:
        if c["estate"] != estate:
            continue
        k = time.strftime("%Y-%m-%d", time.localtime(c["t"]))
        if k in counts:
            counts[k] += 1
    return [counts[k] for k in keys]


def issue_text(i):
    return " ".join([i.get("title", "")] + i.get("refs", []) +
                    [e.get("msg", "") for e in i.get("log", [])])


def site_touches(i):
    """この issue が言及する敷地(本文の表記ゆれ + refs のパス + estate 欄)。"""
    t = issue_text(i)
    touched = set()
    if i["estate"] in SITES:
        touched.add(i["estate"])
    for e, names in MENTION.items():
        if any(n in t for n in names):
            touched.add(e)
    return touched


def build_relationships(issues):
    """横断の相関図の元データ — 敷地2つに言及する issue は辺、1つ+全体基盤は hub 辺。"""
    pair, hub, general = {}, {k: 0 for k in SITES}, 0
    for i in issues:
        if i["status"] in ("done", "dropped"):
            continue
        touched = site_touches(i)
        if len(touched) == 2:
            k = tuple(sorted(touched))
            pair[k] = pair.get(k, 0) + 1
        elif len(touched) != 2 and i["estate"] in ("cross", "infra"):
            if touched:
                for e in touched:
                    hub[e] += 1
            else:
                general += 1
    return {"pair": pair, "hub": hub, "general": general}


def build_summary(issues, pending, commits, claims):
    est = {}
    for e in SITES:
        mine = [c for c in commits if c["estate"] == e]
        rounds = [c for c in mine if c["junsu"]]
        est[e] = {
            "latest_commit": ({"h": mine[0]["h"], "t": mine[0]["t"], "s": mine[0]["s"]}
                              if mine else None),
            "commits_7d": len(mine),
            "daily": daily_buckets(commits, e),
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
  --ai:#33518F; --shu:#AE392A; --oud:#B08000; --matsu:#237A4A;
  --ai-soft: color-mix(in srgb, var(--ai) 14%, var(--card));
  --shu-soft: color-mix(in srgb, var(--shu) 14%, var(--card));
  --oud-soft: color-mix(in srgb, var(--oud) 16%, var(--card));
  --matsu-soft: color-mix(in srgb, var(--matsu) 14%, var(--card));
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#181A20; --card:#20232B; --line:#343846; --ink:#E6E2D6; --muted:#98917F;
  --ai:#6E8FD1; --shu:#C34832; --oud:#AC9010; --matsu:#189065;
}}
:root[data-theme="dark"]{
  --bg:#181A20; --card:#20232B; --line:#343846; --ink:#E6E2D6; --muted:#98917F;
  --ai:#6E8FD1; --shu:#C34832; --oud:#AC9010; --matsu:#189065;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:'Noto Sans JP',system-ui,sans-serif;font-size:14px;line-height:1.65}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 64px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:14px;margin-bottom:6px}
h1{font-family:'Shippori Mincho',serif;font-weight:600;font-size:26px;margin:0;letter-spacing:.04em}
.gen{color:var(--muted);font-size:12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 14px}
.chip{padding:3px 12px;border-radius:99px;font-size:12.5px;border:1px solid var(--line);background:var(--card)}
.chip b{font-family:var(--mono)}
.chip.crit{background:var(--shu-soft);border-color:var(--shu);color:var(--shu)}
.chip.wait{background:var(--oud-soft);border-color:var(--oud);color:var(--oud)}
.chip.ok{background:var(--matsu-soft);border-color:var(--matsu);color:var(--matsu)}
.compbar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--line);
  margin:8px 0 6px;max-width:520px}
.compbar span{height:100%}
.complegend{display:flex;flex-wrap:wrap;gap:14px;font-size:11.5px;color:var(--muted);
  margin-bottom:18px}
.complegend .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}

/* ── フィルタバー(見づらさ対策: 敷地/種別/完了表示/検索を1か所に集約) */
.filterbar{position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0 12px;
  margin-bottom:8px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;
  gap:10px 18px;align-items:center}
.fgroup{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.flabel{font-size:11px;color:var(--muted);letter-spacing:.08em;margin-right:2px}
.fchip{padding:4px 12px;border-radius:99px;font-size:12px;border:1px solid var(--line);
  background:var(--card);color:var(--muted);cursor:pointer;user-select:none;
  transition:background .1s,color .1s,border-color .1s}
.fchip:hover{border-color:var(--ink)}
.fchip.active{background:var(--ai-soft);border-color:var(--ai);color:var(--ai);font-weight:600}
.fchip[data-type="blocker"].active{background:var(--shu-soft);border-color:var(--shu);color:var(--shu)}
.fchip[data-type="decision"].active{background:var(--oud-soft);border-color:var(--oud);color:var(--oud)}
.fsearch{font:inherit;font-size:12.5px;padding:5px 10px;border:1px solid var(--line);
  border-radius:6px;background:var(--card);color:var(--ink);min-width:220px}
.fsearch:focus{outline:2px solid var(--ai);outline-offset:-1px}
.fresetbtn{margin-left:auto;color:var(--muted)}
.fcount{font-size:11.5px;color:var(--muted);margin:2px 0 20px}

h2{font-family:'Shippori Mincho',serif;font-weight:600;font-size:17px;
  border-bottom:2px solid var(--ink);padding-bottom:5px;margin:34px 0 14px;letter-spacing:.06em}
.h2note{font-size:11.5px;color:var(--muted);font-weight:400;letter-spacing:0;margin-left:8px}
.dl{display:grid;grid-template-columns:4.5em 1fr;gap:3px 12px;font-size:13.5px}
.dl dt{color:var(--muted)}.dl dd{margin:0}
.dl .rec{color:var(--ai);font-weight:600}
.lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}
.lane{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:14px 16px}
.lane.cross{border-style:dashed}
.lane h3{font-family:'Shippori Mincho',serif;font-size:16px;margin:0;letter-spacing:.05em}
.lane .area{color:var(--muted);font-size:11.5px;margin-bottom:8px}
.state{font-size:12.5px;background:var(--ai-soft);color:var(--ai);
  border-radius:4px;padding:2px 8px;display:inline-block;margin:4px 0}
.statepair{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0}
.statepair .tag{font-size:11px;color:var(--muted);align-self:center}
.gate{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0;align-items:center}
.gate .tag{font-size:11px;color:var(--muted)}
.gitem{font-size:11.5px;border-radius:4px;padding:1px 7px;border:1px solid var(--line);
  background:var(--card);cursor:help}
.gitem.g-ng{background:var(--shu-soft);border-color:var(--shu);color:var(--shu);font-weight:600}
.gitem.g-ok{background:var(--matsu-soft);border-color:var(--matsu);color:var(--matsu)}
.state.impl-wait{background:var(--oud-soft);color:var(--oud);font-weight:600}
.kv{font-size:12.5px;color:var(--muted);margin:3px 0}
.kv b{color:var(--ink);font-weight:500}
.kv .n{font-family:var(--mono)}
.metric{margin:10px 0}
.metric .lbl{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:3px}

/* ── タブ(主=タスク一覧 / 従=敷地別・動き) */
.tabs{display:flex;gap:2px;border-bottom:2px solid var(--line);margin:26px 0 0}
.tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;
  margin-bottom:-2px;padding:9px 18px;font:inherit;font-size:14px;color:var(--muted);
  cursor:pointer;font-family:'Shippori Mincho',serif;letter-spacing:.06em}
.tab:hover{color:var(--ink)}
.tab[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--ink);font-weight:600}
.tab .n{font-family:var(--mono);font-size:11.5px;color:var(--muted);margin-left:7px}
.tab:focus-visible{outline:2px solid var(--ai);outline-offset:-2px}
.panel[hidden]{display:none}

/* ── タスク一覧(全敷地を1枚で。これが主) */
.tasks{width:100%;border-collapse:collapse;font-size:13.5px}
.tasks thead th{position:sticky;top:0;background:var(--bg);text-align:left;font-weight:500;
  font-size:11.5px;letter-spacing:.06em;color:var(--muted);padding:8px 10px;
  border-bottom:1px solid var(--line-strong,var(--line));white-space:nowrap;z-index:2}
.tasks thead th.sortable{cursor:pointer;user-select:none}
.tasks thead th.sortable:hover{color:var(--ink)}
.tasks thead th .ar{opacity:0;font-size:9px;margin-left:3px}
.tasks thead th[data-dir] .ar{opacity:1}
.tasks tbody td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.tasks tbody tr.trow{cursor:pointer}
.tasks tbody tr.trow:hover{background:var(--card)}
.tasks tbody tr.trow:focus-visible{outline:2px solid var(--ai);outline-offset:-2px}
.tasks tbody tr.done-row td{opacity:.5}
.tasks .tw{display:flex;gap:7px;align-items:baseline}
.tasks .caret{color:var(--muted);font-size:10px;flex:none;transition:transform .12s;
  display:inline-block;line-height:1.6}
.tasks tr[aria-expanded="true"] .caret{transform:rotate(90deg)}
.tasks tr[aria-expanded="true"]{background:var(--card)}
.tasks tr[aria-expanded="true"] td{border-bottom-color:transparent}

/* ── 押して開く詳細。経過ログはここにしか出ない */
.drow > td{background:var(--card);padding:0 10px 14px}
.dbox{border-left:2px solid var(--ai);padding:2px 0 2px 14px;margin-left:2px;
  display:flex;flex-direction:column;gap:9px}
.dmeta{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:12px;color:var(--muted)}
.dmeta b{color:var(--ink);font-weight:500}
.dref{font-size:11.5px;color:var(--muted);word-break:break-all}
.dref code{font-family:var(--mono);font-size:11px;background:var(--bg);
  padding:1px 5px;border-radius:2px;word-break:break-all}
.dlog-h{font-size:11px;letter-spacing:.08em;color:var(--muted);
  border-bottom:1px solid var(--line);padding-bottom:3px;margin-bottom:5px}
.dlog-e{display:grid;grid-template-columns:auto auto 1fr;gap:4px 10px;
  font-size:12.5px;padding:4px 0;align-items:baseline}
.dlog-e + .dlog-e{border-top:1px dotted var(--line)}
.dlog-e .t{font-family:var(--mono);font-size:11px;color:var(--muted);white-space:nowrap}
.dlog-e .by{font-family:var(--mono);font-size:10.5px;color:var(--faint,var(--muted));
  white-space:nowrap;opacity:.8}
.dlog-e .m{white-space:pre-wrap;word-break:break-word;line-height:1.7}
.badge.st-info{opacity:.75}
.badge.st-open{background:var(--bg)}

/* ── 狭い画面: タスク一覧は表を畳んでカードに積み替える。
      列を横に並べたままだと5列は入らず横スクロールになるので、
      1行=1カード(状態・敷地・更新の帯 + 題 + ID)へ組み替える。 */
@media (max-width:680px){
  .wrap{padding:20px 14px 56px}
  .mwrap{overflow-x:visible}
  .tasks{display:block}
  .tasks thead{display:none}          /* 積み替えると見出しの列が対応しなくなる */
  .tasks tbody{display:block}
  /* 畳んだカード(既定)= 1行。状態 + 題だけ出し、題は1行で省略する。
     40件が3行ずつ積まれると一覧として読めないので、既定は最小の1行にする。 */
  .tasks tbody tr.trow{
    display:grid;grid-template-columns:auto 1fr;
    grid-template-areas:"state title";
    gap:5px 9px;padding:11px 2px;border-bottom:1px solid var(--line);align-items:baseline}
  .tasks tbody tr.trow > td{display:block;border:0;padding:0;min-width:0}
  .tasks .c-badge{grid-area:state}
  .tasks .c-ttl{grid-area:title;font-size:13.5px;line-height:1.55;min-width:0}
  .tasks .tw{min-width:0}
  .tasks tr[aria-expanded="false"] .ttx{
    display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  /* 畳んでいる間は 敷地・更新・ID を隠す(押せば出る) */
  .tasks tr[aria-expanded="false"] > .c-site,
  .tasks tr[aria-expanded="false"] > .c-when,
  .tasks tr[aria-expanded="false"] > .c-id{display:none}
  /* 開いたカード = 帯(状態・敷地・更新) + 題 + ID */
  .tasks tbody tr.trow[aria-expanded="true"]{
    grid-template-columns:auto 1fr auto;
    grid-template-areas:"state site when" "title title title" "id id id"}
  .tasks .c-site{grid-area:site;font-size:12px}
  .tasks .c-when{grid-area:when;text-align:right}
  .tasks .c-id{grid-area:id;font-size:10.5px}
  .tasks tbody tr[aria-expanded="true"] > td{border-bottom-color:transparent}
  /* ⚠ :not([hidden]) は必須。素の display:block は UA の [hidden]{display:none} に
     勝ってしまい、畳んでいるはずの詳細が全件描画される(実際に起こした)。 */
  .tasks tbody tr.drow:not([hidden]){display:block}
  .tasks tbody tr.drow > td{display:block;padding:0 0 14px}
  .dbox{padding-left:11px}
  .dlog-e{grid-template-columns:1fr;gap:2px}      /* 時刻・主体・本文を縦に積む */
  .dlog-e .by{grid-row:1;justify-self:end;margin-top:-17px}
  .dl{grid-template-columns:1fr;gap:1px 0}
  .dl dt{font-size:11px;letter-spacing:.06em;margin-top:6px}
  .filterbar{position:static;gap:8px 12px}         /* 狭い画面で貼り付くと場所を食う */
  .fsearch{min-width:0;flex:1 1 100%}
  .fresetbtn{margin-left:0}
  .netwrap{padding:12px 12px 6px}
  .netcap{max-width:none}
  /* タブ4つが 375px に収まるまで詰める(帯だけ横スクロールするのも避ける) */
  .tabs{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .tab{padding:9px 7px;white-space:nowrap;font-size:13px;letter-spacing:.02em}
  .tab .n{margin-left:4px;font-size:10.5px}
  /* 最近の動きも同じ理由で積み替える(4列は入らない) */
  .scroll{overflow-x:visible}
  .feed,.feed tbody{display:block}
  .feed tr{display:grid;grid-template-columns:auto auto 1fr;gap:2px 8px;
    padding:9px 0;border-bottom:1px solid var(--line);align-items:baseline}
  .feed td{display:block;border:0;padding:0}
  .feed td:last-child{grid-column:1/-1;line-height:1.6}
  /* 敷地別のカードも1列に */
  .lanes{grid-template-columns:1fr}
}
/* 相関図は固定幅の SVG なので、狭い画面では必ず縮める */
.netwrap svg{max-width:100%;height:auto}
.tasks .c-id{font-family:var(--mono);font-size:11px;color:var(--muted);white-space:nowrap}
.tasks .c-site{white-space:nowrap;font-size:12.5px}
.tasks .c-site i{display:inline-block;width:7px;height:7px;border-radius:50%;
  margin-right:6px;background:var(--dot,var(--line-firm))}
.tasks .c-ttl{width:99%}
.tasks .c-ttl .reflinks{margin-top:3px}
.tasks .c-when{white-space:nowrap;font-family:var(--mono);font-size:11px;color:var(--muted);
  font-variant-numeric:tabular-nums;text-align:right}
.tasks .c-badge{white-space:nowrap}
.empty{padding:22px 4px;color:var(--muted);font-size:13.5px}

/* ── issue 行(敷地別タブの中で使う) */
.iss{font-size:13px;margin:8px 0 0;padding:0;list-style:none}
.iss li{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 8px;
  padding:7px 10px;border-left:3px solid var(--line);margin-bottom:5px;
  background:var(--bg);border-radius:0 5px 5px 0}
.iss li.blocker{border-left-color:var(--shu)}
.iss li.awaiting-user{border-left-color:var(--oud)}
.iss li.info-row{opacity:.72}
.iss li.done-row{opacity:.55;text-decoration:line-through}
.iss .id{font-family:var(--mono);font-size:11px;color:var(--muted);flex:none}
.iss .ttl{flex:1 1 260px}
.badge{font-size:10px;padding:1px 7px;border-radius:99px;border:1px solid var(--line);
  color:var(--muted);flex:none;white-space:nowrap}
.badge.type-blocker{background:var(--shu-soft);border-color:var(--shu);color:var(--shu)}
.badge.type-decision{background:var(--oud-soft);border-color:var(--oud);color:var(--oud)}
.badge.type-task{background:var(--ai-soft);border-color:var(--ai);color:var(--ai)}
.badge.st-awaiting-user{background:var(--oud-soft);border-color:var(--oud);color:var(--oud)}
.badge.st-in-progress{background:var(--ai-soft);border-color:var(--ai);color:var(--ai)}
.badge.st-done,.badge.st-dropped{opacity:.7}

.reflinks{margin-top:2px;display:flex;flex-wrap:wrap;gap:10px;flex-basis:100%}
.reflinks a,.openlink{font-size:11.5px;color:var(--ai);text-decoration:none;border-bottom:1px dotted var(--ai)}
.reflinks a:hover,.openlink:hover{border-bottom-style:solid}
.lane h3{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px}
.openlink{font-family:'Noto Sans JP',system-ui,sans-serif;font-size:11px;font-weight:400;letter-spacing:0}
.netwrap{background:var(--card);border:1px solid var(--line);border-radius:6px;
  padding:14px 18px 8px;display:flex;flex-wrap:wrap;gap:20px;align-items:center}
.netcap{font-size:11.5px;color:var(--muted);max-width:280px}
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

JS = """
(function(){
  function $all(sel){ return Array.from(document.querySelectorAll(sel)); }

  /* ── タブ。主タブ=タスク一覧(全敷地を1枚)、従タブ=敷地別・最近の動き。
        フィルタはタブをまたいで効く(同じ .fitem を見る)。 */
  var tabs = $all('.tab'), panels = $all('.panel');
  function selectTab(name){
    tabs.forEach(function(t){
      var on = t.getAttribute('data-tab') === name;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
    });
    panels.forEach(function(pl){ pl.hidden = pl.getAttribute('data-panel') !== name; });
    try { localStorage.setItem('edo_tab', name); } catch(e){}
  }
  tabs.forEach(function(t){
    t.addEventListener('click', function(){ selectTab(t.getAttribute('data-tab')); });
    t.addEventListener('keydown', function(e){
      var i = tabs.indexOf(t), n = null;
      if (e.key === 'ArrowRight') n = tabs[(i+1) % tabs.length];
      if (e.key === 'ArrowLeft')  n = tabs[(i-1+tabs.length) % tabs.length];
      if (n){ e.preventDefault(); n.focus(); selectTab(n.getAttribute('data-tab')); }
    });
  });
  var saved = null;
  try { saved = localStorage.getItem('edo_tab'); } catch(e){}
  selectTab(tabs.some(function(t){ return t.getAttribute('data-tab') === saved; })
            ? saved : 'tasks');

  /* ── フィルタ。**1つも選ばれていない群は絞り込まない**(= 全選択と同じ)。
        既定は全群とも未選択なので、開いた直後は全件が出る。 */
  var siteBtns  = $all('#siteFilter .fchip');
  var stateBtns = $all('#stateFilter .fchip');
  var search    = document.getElementById('fsearch');
  var resetBtn  = document.getElementById('fReset');
  var items = $all('.fitem');
  var lanes = $all('.lane[data-site]');
  var countEl = document.getElementById('fcount');

  function activeVals(btns, attr){
    return new Set(btns.filter(function(b){ return b.classList.contains('active'); })
                        .map(function(b){ return b.getAttribute(attr); }));
  }
  function passes(set, val){ return set.size === 0 || set.has(val); }
  function detailOf(row){
    var id = row.id.replace(/^row-/, '');
    return document.getElementById('det-' + id);
  }
  function apply(){
    var sites  = activeVals(siteBtns, 'data-site');
    var states = activeVals(stateBtns, 'data-state');
    var q = search.value.trim().toLowerCase();
    var shownRows = 0;
    items.forEach(function(el){
      var det = el.classList.contains('trow') ? detailOf(el) : null;
      /* 検索は詳細(経過ログ)の中身も対象にする — 行の題だけでは当たらない語が多い */
      var hay = el.textContent + (det ? det.textContent : '');
      var vis = passes(sites,  el.getAttribute('data-site'))
             && passes(states, el.getAttribute('data-state'))
             && (!q || hay.toLowerCase().indexOf(q) !== -1);
      el.style.display = vis ? '' : 'none';
      /* 親が消えたら詳細も畳む(開いたまま親だけ消えると宙に浮く) */
      if (det && !vis){
        det.hidden = true;
        el.setAttribute('aria-expanded', 'false');
      }
      if (vis && el.classList.contains('trow')) shownRows++;
    });
    lanes.forEach(function(l){
      l.style.display = passes(sites, l.getAttribute('data-site')) ? '' : 'none';
    });
    if (countEl) countEl.textContent = shownRows + ' 件表示中';
    var none = document.getElementById('tasksEmpty');
    if (none) none.hidden = shownRows !== 0;
  }
  siteBtns.concat(stateBtns).forEach(function(b){
    b.addEventListener('click', function(){ b.classList.toggle('active'); apply(); });
  });
  if (search)   search.addEventListener('input', apply);
  if (resetBtn) resetBtn.addEventListener('click', function(){
    /* リセット = 全解除(= 全件表示)。既定の状態へ戻す */
    siteBtns.concat(stateBtns).forEach(function(b){ b.classList.remove('active'); });
    search.value = ''; apply();
  });

  /* ── 行を押したら詳細(経過ログ・裁定の中身・正典の参照)を開く */
  var tbody = document.getElementById('taskBody');
  function toggleRow(row){
    var det = detailOf(row);
    if (!det) return;
    var open = det.hidden;
    det.hidden = !open;
    row.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  $all('#taskBody tr.trow').forEach(function(row){
    row.addEventListener('click', function(e){
      /* 詳細の中のリンクを踏んだときは開閉しない */
      if (e.target.closest('a')) return;
      toggleRow(row);
    });
    row.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); toggleRow(row); }
    });
  });

  /* ── 並べ替え。既定は優先度(要裁定→ブロッカー→進行中→未着手→完了)。
        詳細行は必ず親のすぐ後ろへ連れて動かす。 */
  if (tbody){
    $all('.tasks thead th.sortable').forEach(function(th){
      th.addEventListener('click', function(){
        var key = th.getAttribute('data-key');
        var dir = th.getAttribute('data-dir') === 'asc' ? 'desc' : 'asc';
        $all('.tasks thead th').forEach(function(o){
          o.removeAttribute('data-dir');
          var a = o.querySelector('.ar'); if (a) a.textContent = '';
        });
        th.setAttribute('data-dir', dir);
        var ar = th.querySelector('.ar'); if (ar) ar.textContent = dir === 'asc' ? '▲' : '▼';
        var rows = $all('#taskBody tr.trow');
        rows.sort(function(a, b){
          var av = a.getAttribute('data-' + key), bv = b.getAttribute('data-' + key);
          var an = parseFloat(av), bn = parseFloat(bv);
          var c = (!isNaN(an) && !isNaN(bn)) ? an - bn : String(av).localeCompare(String(bv), 'ja');
          return dir === 'asc' ? c : -c;
        });
        rows.forEach(function(r){
          tbody.appendChild(r);
          var det = detailOf(r);
          if (det) tbody.appendChild(det);
        });
      });
    });
  }

  apply();
})();
"""


REF_RE = re.compile(r"^docs/Sashizu/([a-z0-9]+)_sashizu\.json(?:#(.+))?$")
# 部材・runの識別子(S_Hei_C, TW_Kairo_E 等)は本文の表に literal で出るのでテキスト
# フラグメントの当たりが良い。単なる json のセクション名(munes, open 等)は
# 本文には出ないので当てにいかない。
IDENT_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+){1,}$")


def resolve_ref(ref, states):
    """refを指図Artifactへのリンクに解決する。

    敷地単位のリンクは README に載っていれば張れる(無ければ単に張らない — worktree
    止まりでまだ合流していない敷地はそういう状態にある、というのが実情)。
    ピンポイントの行送りは ブラウザのテキストフラグメント(#:~:text=)で試みるが、
    本文と一致する見込みが薄いキー(json のセクション名など)は諦めて敷地単位の
    リンクへ落とす。GitHub は origin/main がローカルより進んでいないため意図的に
    リンクしない(押していない変更を指すと古い内容を指図として見せてしまう)。
    """
    m = REF_RE.match(ref)
    if not m:
        return None
    estate, key = m.group(1), (m.group(2) or "")
    url = (states.get(estate) or {}).get("url")
    if not url:
        return None
    cand = key.rsplit(".", 1)[-1]  # 例: "runs.S_Hei_C" → "S_Hei_C" / "_pending.○○" → "○○"
    good = bool(re.search(r"[^\x00-\x7f]", cand)) or bool(IDENT_RE.match(cand))
    frag = "#:~:text=%s" % quote(cand) if good else ""
    return {"label": "指図(%s)" % SITES.get(estate, estate), "href": url + frag}


def refs_html(i, states):
    links = [resolve_ref(r, states) for r in i.get("refs", [])]
    links = [l for l in links if l]
    if not links:
        return ""
    seen, uniq = set(), []
    for l in links:
        if l["href"] not in seen:
            seen.add(l["href"]); uniq.append(l)
    return '<div class="reflinks">%s</div>' % "".join(
        '<a href="%s" target="_blank" rel="noopener">%s ↗</a>' % (esc(l["href"]), esc(l["label"]))
        for l in uniq)


def issue_li(i, states):
    # id を振るのは見た目でなく、ダッシュボードのコメント機能が要素を CSS セレクタで
    # 位置(nth-of-type)アンカーするため — issue が close/並び替わるたびに別の
    # カードを指してしまう(実際に2件連続で起きた)。id があれば #EDO-0025 のように
    # セレクタが安定し、後から順序が変わっても指す相手がずれない。
    # data-* はブラウザ側フィルタ専用(敷地/種別/状態) — 生成器はここに書くだけで
    # 実際のフィルタリングはページ内の JS が担う。
    row_cls = i["type"] if i["type"] == "blocker" else i["status"]
    if i["type"] == "info":
        row_cls += " info-row"
    if i["status"] in ("done", "dropped"):
        row_cls += " done-row"
    return ('<li id="%s" class="fitem %s" data-site="%s" data-type="%s" data-status="%s">'
            '<span class="id">%s</span><span class="ttl">%s</span>'
            '<span class="badge type-%s">%s</span><span class="badge st-%s">%s</span>%s</li>'
            % (esc(i["id"]), esc(row_cls), esc(display_site(i)), esc(i["type"]), esc(i["status"]),
               esc(i["id"]), esc(i["title"]),
               esc(i["type"]), esc(TYPE_LABEL.get(i["type"], i["type"])),
               esc(i["status"]), esc(STATUS_LABEL.get(i["status"], i["status"])),
               refs_html(i, states)))


# ── 小さな図表(すべてトークン色を参照するので明暗テーマに追随する)
def spark_svg(daily, w=108, h=26):
    n = len(daily)
    gap = 2
    bw = (w - gap * (n - 1)) / n
    peak = max(1, max(daily))
    bars = []
    for i, v in enumerate(daily):
        bh = round((v / peak) * (h - 4)) if v else 0
        x = i * (bw + gap)
        y = h - bh
        bars.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="1.5" '
                    'fill="var(--ai)" opacity="%s"/>'
                    % (x, y, bw, max(bh, 1), "1" if v else "0.28"))
    return ('<svg width="%d" height="%d" viewBox="0 0 %d %d" aria-hidden="true">%s'
            '<line x1="0" y1="%d" x2="%d" y2="%d" stroke="var(--line)" stroke-width="1"/></svg>'
            % (w, h, w, h, "".join(bars), h - 0.5, w, h - 0.5))


def gauge_svg(baseline, current, w=150, h=12):
    if baseline is None or current is None:
        return ""
    gmax = max(current, baseline + JUNSU_WARN + 1, 1)
    over = current - baseline >= JUNSU_WARN
    def px(v):
        return round((v / gmax) * w, 1)
    zone_x = px(baseline + JUNSU_WARN)
    fill_w = px(current)
    bits = ['<svg width="%d" height="%d" viewBox="0 0 %d %d" aria-hidden="true">' % (w, h, w, h)]
    bits.append('<rect x="0" y="0" width="%d" height="%d" rx="4" fill="var(--line)"/>' % (w, h))
    if zone_x < w:
        bits.append('<rect x="%.1f" y="0" width="%.1f" height="%d" rx="0" fill="var(--shu-soft)"/>'
                    % (zone_x, w - zone_x, h))
    bits.append('<rect x="0" y="0" width="%.1f" height="%d" rx="4" fill="%s"/>'
                % (fill_w, h, "var(--shu)" if over else "var(--ai)"))
    bx = px(baseline)
    bits.append('<line x1="%.1f" y1="-2" x2="%.1f" y2="%d" stroke="var(--ink)" '
                'stroke-width="1.5" opacity="0.55"/>' % (bx, bx, h + 2))
    bits.append("</svg>")
    return "".join(bits)


def network_svg(rel, open_counts, w=380, h=280):
    import math
    cx, cy, R = w / 2, h / 2 + 6, 100
    keys = list(SITES.keys())
    n = len(keys)
    pos = {"hub": (cx, cy)}
    for i, e in enumerate(keys):
        ang = -math.pi / 2 + i * (2 * math.pi / n)
        pos[e] = (cx + R * math.cos(ang), cy + R * math.sin(ang))
    bits = ['<svg width="%d" height="%d" viewBox="0 0 %d %d" aria-hidden="true">' % (w, h, w, h)]
    # 辺(敷地2つに言及=直接、単独+横断=hub経由)を先に描く(節が上に来るように)
    for e, cnt in rel["hub"].items():
        if not cnt:
            continue
        x1, y1 = pos["hub"]; x2, y2 = pos[e]
        sw = min(6, 1.5 + cnt * 1.3)
        bits.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--line)" '
                    'stroke-width="%.1f"/>' % (x1, y1, x2, y2, sw))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        bits.append('<circle cx="%.1f" cy="%.1f" r="8" fill="var(--card)" stroke="var(--line)"/>'
                    '<text x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
                    'font-size="9" fill="var(--muted)" font-family="var(--mono)">%d</text>'
                    % (mx, my, mx, my, cnt))
    for (a, b), cnt in rel["pair"].items():
        x1, y1 = pos[a]; x2, y2 = pos[b]
        sw = min(6, 1.5 + cnt * 1.3)
        bits.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--ai)" '
                    'stroke-width="%.1f" opacity="0.7"/>' % (x1, y1, x2, y2, sw))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        bits.append('<circle cx="%.1f" cy="%.1f" r="9" fill="var(--ai)"/>'
                    '<text x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
                    'font-size="10" fill="var(--card)" font-family="var(--mono)" font-weight="600">%d</text>'
                    % (mx, my, mx, my, cnt))
    # 節
    hx, hy = pos["hub"]
    bits.append('<circle cx="%.1f" cy="%.1f" r="17" fill="var(--card)" stroke="var(--muted)" '
                'stroke-width="1.5" stroke-dasharray="2,2"/>'
                '<text x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
                'font-size="12" fill="var(--muted)">共通</text>' % (hx, hy, hx, hy))
    for e in keys:
        x, y = pos[e]
        n_open = open_counts.get(e, 0)
        bits.append('<circle cx="%.1f" cy="%.1f" r="24" fill="var(--card)" stroke="var(--ink)" '
                    'stroke-width="1.5"/>' % (x, y))
        bits.append('<text x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
                    'font-size="16" fill="var(--ink)" font-family="\'Shippori Mincho\',serif">%s</text>'
                    % (x, y - 5, SHORT[e]))
        bits.append('<text x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
                    'font-size="9.5" fill="var(--muted)" font-family="var(--mono)">open %d</text>'
                    % (x, y + 11, n_open))
    bits.append("</svg>")
    return "".join(bits)


SITE_DOT = {"matsudaira_dewa": "var(--ai)", "sanno": "var(--matsu)", "okabe": "var(--oud)",
            "doi": "var(--shu)", "sotobori": "#4E8FA8", CROSS_KEY: "var(--line-firm)"}
# 既定の並び: 手を打つべき順。要裁定 → ブロッカー → 進行中 → open → 完了
PRIO = {"awaiting-user": 0, "in-progress": 2, "open": 3, "done": 8, "dropped": 9}


def task_prio(i):
    if i["status"] == "awaiting-user":
        return 0
    if i["type"] == "blocker" and i["status"] not in ("done", "dropped"):
        return 1
    return PRIO.get(i["status"], 5)


# 種別(task/info/blocker/decision)と状態(open/awaiting-user/…)を**1列に畳む**。
# 2026-08-29 ユーザー指摘「種別と状態の違いがよくわからない。状態だけでよい」——
# 実際 種別「裁定」と状態「要裁定」が紛らわしく、並べても読み分けられなかった。
# 畳むときは**手を打つべき緊急度の高い方**を出す(生きているブロッカーは状態より種別が効く)。
# 種別そのものは詳細と絞り込みには残す(info を畳んで静かにする、が効くため)。
def task_state(i):
    """(表示ラベル, バッジのCSSクラス)。"""
    if i["status"] == "awaiting-user":
        return "要裁定", "st-awaiting-user"
    if i["status"] in ("done", "dropped"):
        return ("完了", "st-done") if i["status"] == "done" else ("見送り", "st-dropped")
    if i["type"] == "blocker":
        return "ブロッカー", "type-blocker"
    if i["status"] == "in-progress":
        return "進行中", "st-in-progress"
    if i["type"] == "info":
        return "記録", "st-info"
    return "未着手", "st-open"


def detail_html(i, states):
    """行を押したときに開く詳細。経過ログはここにしか出ない(表には出さない)。"""
    b = []
    b.append('<div class="dmeta">'
             '<span>敷地 <b>%s</b></span><span>種別 <b>%s</b></span>'
             '<span>状態 <b>%s</b></span>%s</div>'
             % (esc(SITES.get(i["estate"], CROSS_LABEL)),
                esc(TYPE_LABEL.get(i["type"], i["type"])),
                esc(STATUS_LABEL.get(i["status"], i["status"])),
                ('<span>担当 <b>%s</b></span>' % esc(i["owner"])) if i.get("owner") else ""))
    d = i.get("decision") or {}
    if d:
        b.append('<dl class="dl">')
        b.append("<dt>背景</dt><dd>%s</dd>" % esc(d.get("background", "")))
        b.append("<dt>選択肢</dt><dd>%s</dd>"
                 % "<br>".join(esc(o) for o in d.get("options", [])))
        b.append('<dt>推奨</dt><dd class="rec">%s</dd>' % esc(d.get("recommend", "")))
        b.append("<dt>影響</dt><dd>%s</dd>" % esc(d.get("impact", "")))
        b.append("</dl>")
    for r in i.get("refs", []):
        b.append('<div class="dref">正典 <code>%s</code></div>' % esc(r))
    b.append(refs_html(i, states))
    log = i.get("log") or []
    if log:
        b.append('<div class="dlog"><div class="dlog-h">経過 %d件</div>' % len(log))
        for e in log:
            b.append('<div class="dlog-e"><span class="t">%s</span>'
                     '<span class="by">%s</span><span class="m">%s</span></div>'
                     % (esc(time.strftime("%m-%d %H:%M", time.localtime(e.get("t", 0)))),
                        esc((e.get("by") or "")[:12]), esc(e.get("msg", ""))))
        b.append("</div>")
    return "".join(b)


def task_row(i, states):
    """タスク一覧(全敷地を1枚)の1行 + 押したら開く詳細行。
    data-* はフィルタと並べ替えが読む。詳細行は同じ data-* を持たないと
    フィルタで親だけ消えて詳細が浮くので、JS 側で親と対で扱う。"""
    site = display_site(i)
    cls = "fitem trow"
    if i["status"] in ("done", "dropped"):
        cls += " done-row"
    label, badge_cls = task_state(i)
    row = (
        '<tr id="row-%s" class="%s" data-site="%s" data-type="%s" data-status="%s"'
        ' data-prio="%d" data-when="%d" data-sitename="%s" data-title="%s"'
        ' data-state="%s" tabindex="0" role="button" aria-expanded="false"'
        ' aria-controls="det-%s">'
        '<td class="c-id">%s</td>'
        '<td class="c-site"><i style="--dot:%s"></i>%s</td>'
        '<td class="c-badge"><span class="badge %s">%s</span></td>'
        '<td class="c-ttl"><span class="tw"><span class="caret">▸</span>'
        '<span class="ttx">%s</span></span></td>'
        '<td class="c-when">%s</td></tr>'
        % (esc(i["id"]), esc(cls), esc(site), esc(i["type"]), esc(i["status"]),
           task_prio(i), int(i.get("updated") or 0),
           esc(SITES.get(i["estate"], CROSS_LABEL)), esc(i["title"]),
           esc(label), esc(i["id"]),
           esc(i["id"]),
           esc(SITE_DOT.get(site, "var(--line-firm)")), esc(SITES.get(i["estate"], CROSS_LABEL)),
           esc(badge_cls), esc(label),
           esc(i["title"]),
           esc(ago(i.get("updated") or 0))))
    det = ('<tr id="det-%s" class="drow" data-for="%s" hidden>'
           '<td colspan="5"><div class="dbox">%s</div></td></tr>'
           % (esc(i["id"]), esc(i["id"]), detail_html(i, states)))
    return row + det


def tasks_table_html(issues, states):
    rows = sorted(issues, key=lambda i: (task_prio(i), -(i.get("updated") or 0)))
    head = [("prio", "ID", "sortable"), ("sitename", "敷地", "sortable"),
            ("state", "状態", "sortable"),
            ("title", "タスク", "sortable"), ("when", "更新", "sortable")]
    th = "".join(
        '<th %sdata-key="%s">%s<span class="ar"></span></th>'
        % (('class="%s" ' % c) if c else "", esc(k), esc(lbl)) for k, lbl, c in head)
    return ('<div class="mwrap"><table class="tasks"><thead><tr>%s</tr></thead>'
            '<tbody id="taskBody">%s</tbody></table></div>'
            '<div class="empty" id="tasksEmpty" hidden>'
            '条件に合うタスクがありません。フィルタを緩めてください。</div>'
            % (th, "".join(task_row(i, states) for i in rows)))


# 状態の絞り込みに出す並び(task_state が返すラベルと一致させる)。
# 2026-08-29 ユーザー指示で「種別」の絞り込みを廃してこちらへ置き換えた —
# 種別「裁定」と状態「要裁定」が読み分けられない、という同じ指摘の続き。
STATE_CHIPS = ["要裁定", "ブロッカー", "進行中", "未着手", "記録", "完了", "見送り"]


def filterbar_html():
    # ⚠ 既定は**すべて未選択**。JS 側で「1つも選ばれていない群は絞り込まない」と
    #    扱うので、未選択 = 全件表示 になる(ユーザー指示 2026-08-29)。
    p = ['<div class="filterbar">']
    p.append('<div class="fgroup" id="siteFilter"><span class="flabel">敷地</span>')
    for e, name in SITES.items():
        p.append('<button type="button" class="fchip" data-site="%s">%s</button>'
                 % (esc(e), esc(name)))
    p.append('<button type="button" class="fchip" data-site="%s">%s</button>'
             % (esc(CROSS_KEY), esc(CROSS_LABEL)))
    p.append("</div>")
    p.append('<div class="fgroup" id="stateFilter"><span class="flabel">状態</span>')
    for s in STATE_CHIPS:
        p.append('<button type="button" class="fchip" data-state="%s">%s</button>'
                 % (esc(s), esc(s)))
    p.append("</div>")
    p.append('<input type="search" id="fsearch" class="fsearch" placeholder="IDやキーワードで絞り込み…">')
    p.append('<button type="button" id="fReset" class="fchip fresetbtn">リセット</button>')
    p.append("</div>")
    p.append('<div id="fcount" class="fcount"></div>')
    return "".join(p)


def build_html(issues, pending, commits, claims, states, summary, reviews):
    live = [i for i in issues if i["status"] not in ("done", "dropped")]
    waits = [i for i in live if i["status"] == "awaiting-user"]
    blks = [i for i in live if i["type"] == "blocker"]
    others = [i for i in live if i not in waits and i not in blks]
    rel = build_relationships(issues)
    open_counts = {e: len(summary["estates"][e]["open_issues"]) for e in SITES}
    junsu_base = load_junsu_baseline()

    p = []
    p.append("<title>赤坂普請 作事奉行</title>")
    p.append('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             'family=Shippori+Mincho:wght@600&family=Noto+Sans+JP:wght@400;500;700&'
             'family=IBM+Plex+Mono:wght@400;500&display=swap">')
    p.append("<style>%s</style>" % CSS)
    p.append('<div class="wrap">')
    p.append('<header><h1>赤坂普請 作事奉行</h1><span class="gen">巡回 %s</span></header>'
             % esc(time.strftime("%m-%d %H:%M")))
    p.append('<div class="chips">')
    p.append('<span class="chip %s">要裁定 <b>%d</b></span>' % ("wait" if waits else "ok", len(waits)))
    p.append('<span class="chip %s">ブロッカー <b>%d</b></span>' % ("crit" if blks else "ok", len(blks)))
    p.append('<span class="chip">open <b>%d</b></span>' % len(live))
    p.append('<span class="chip">生きているセッション <b>%d</b></span>' % len(claims))
    p.append("</div>")

    # ── open issue の内訳(裁定待ち/ブロッカー/その他 の構成比)
    tot = max(1, len(live))
    p.append('<div class="compbar">'
             '<span style="width:%.1f%%;background:var(--oud)"></span>'
             '<span style="width:%.1f%%;background:var(--shu)"></span>'
             '<span style="width:%.1f%%;background:var(--line)"></span></div>'
             % (100 * len(waits) / tot, 100 * len(blks) / tot, 100 * len(others) / tot))
    p.append('<div class="complegend">'
             '<span><span class="dot" style="background:var(--oud)"></span>要裁定 %d</span>'
             '<span><span class="dot" style="background:var(--shu)"></span>ブロッカー %d</span>'
             '<span><span class="dot" style="background:var(--line)"></span>その他(task/info) %d</span>'
             "</div>" % (len(waits), len(blks), len(others)))

    # ── タブ。主=タスク一覧(全敷地を1枚)。要裁定・敷地別・動きは
    #    「その見方をしたいとき用」の従タブ(2026-08-29 ユーザー指示で要裁定もトップから外した)。
    # タブの数字は**一覧に出る件数**(既定は絞り込み無しなので完了・見送りも含む全件)。
    # open だけの数を出すと、既定表示の件数と食い違って読めない。
    p.append('<div class="tabs" role="tablist">')
    p.append('<button class="tab" role="tab" data-tab="tasks" aria-selected="true">'
             'タスク一覧<span class="n">%d</span></button>' % len(issues))
    p.append('<button class="tab" role="tab" data-tab="sites" aria-selected="false">'
             '敷地別<span class="n">%d</span></button>' % (len(SITES) + 1))
    p.append('<button class="tab" role="tab" data-tab="feed" aria-selected="false">'
             '最近の動き</button>')
    p.append("</div>")

    # ── 主タブ: 全敷地のタスクを1枚の表で。フィルタで絞る。
    p.append('<div class="panel" data-panel="tasks">')
    p.append(filterbar_html())
    p.append(tasks_table_html(issues, states))
    p.append("</div>")

    # ⚠ 要裁定タブは 2026-08-29 に廃止(ユーザー指示)。裁定の中身(背景/選択肢/推奨/影響)は
    #    タスク一覧の行を開けば出るので、専用タブは重複だった。
    #    状態フィルタの「要裁定」で絞れば同じ一覧になる。

    # ── 従タブ: 敷地別(邸はスパークライン+三巡則ゲージつき。邸を持たない敷地は
    #    issue 一覧だけ。「全体・基盤」は cross/infra をまとめた専用レーン)
    p.append('<div class="panel" data-panel="sites" hidden>')
    p.append('<p class="sub" style="color:var(--muted);font-size:12.5px;margin:14px 0 4px">'
             '敷地ごとに進み具合を見たいとき用。タスクを横断で探すなら「タスク一覧」タブへ。'
             '上のフィルタの敷地の絞り込みはこちらにも効く。</p>')
    p.append("<div class='lanes'>")
    for e, name in SITES.items():
        is_estate = e in ESTATES
        s = summary["estates"][e]
        st = states.get(e, {})
        cl = [c for c in claims if any(g == "sashizu:%s" % e for g in c.get("paths", []))]
        p.append('<div id="lane-%s" class="lane" data-site="%s"><h3>%s%s</h3>' % (
            esc(e), esc(e), esc(name),
            ' <a class="openlink" href="%s" target="_blank" rel="noopener">指図を開く ↗</a>'
            % esc(st["url"]) if st.get("url") else ""))
        if st.get("area"):
            p.append('<div class="area">%s</div>' % esc(st["area"]))
        if st.get("sashizu_state") is not None:
            # 指図/実装の2軸(2026-08-31 改訂)。指図が済んで実装が未着手の邸は
            # 「いま着手してよい屋敷」なので目立たせる(規則: ユーザーが一目で拾えること)。
            impl = st.get("impl_state", "")
            waiting = "未着手" in impl or "未着手" in st.get("sashizu_state", "")
            p.append('<div class="statepair">'
                     '<span class="tag">指図</span><span class="state">%s</span>'
                     '<span class="tag">実装</span><span class="state%s">%s</span>'
                     '</div>' % (esc(st["sashizu_state"]),
                                " impl-wait" if waiting else "",
                                esc(impl)))
        elif st.get("state"):
            p.append('<span class="state">%s</span>' % esc(st["state"]))
        # 検図関門(2026-09-01 新設)。⛔ 赤の指図は実装しない・ユーザーに見せない。
        rv = reviews.get(e)
        if rv and rv.get("rows"):
            p.append('<div class="gate%s">' % (" gate-red" if rv["red"] else ""))
            p.append('<span class="tag">検分</span>')
            for r in rv["rows"]:
                cls = "g-ng" if r["mark"] in ("⛔", "⚠") else "g-ok"
                p.append('<span class="gitem %s" title="%s">%s %s</span>'
                         % (cls, esc(r["state"]), r["mark"], esc(r["label"].split("(")[0])))
            p.append("</div>")
        if cl:
            for c in cl:
                p.append('<div class="kv">担当: <b class="n">%s</b>(心拍 %.0f分前)%s</div>'
                         % (esc(c["session"][:12]), (time.time() - c["heartbeat"]) / 60,
                            " — " + esc(c["note"]) if c.get("note") else ""))
        elif is_estate:
            p.append('<div class="kv">担当セッションなし</div>')
        if s["latest_commit"]:
            lc = s["latest_commit"]
            p.append('<div class="kv">最新: <span class="n">%s</span> %s<br><b>%s</b></div>'
                     % (esc(lc["h"]), esc(ago(lc["t"])), esc(lc["s"][:60])))
        p.append('<div class="metric"><div class="lbl"><span>直近7日のコミット</span>'
                 '<span class="n">%d</span></div>%s</div>' % (s["commits_7d"], spark_svg(s["daily"])))
        if s["junsu_latest"] is not None:
            cur = s["junsu_latest"]
            base = (junsu_base.get(e) or {}).get("n", cur)
            over = cur - base >= JUNSU_WARN
            p.append('<div class="metric"><div class="lbl"><span>検図・考証(基準%s巡)</span>'
                     '<span class="n" style="%s">%s巡</span></div>%s</div>'
                     % (base, "color:var(--shu)" if over else "", cur,
                        gauge_svg(base, cur)))
        if is_estate:
            p.append('<div class="kv">_pending <b class="n">%d</b>件</div>' % s["pending_count"])
        lane_iss = [i for i in issues if i["estate"] == e]
        if lane_iss:
            p.append('<ul class="iss">%s</ul>' % "".join(issue_li(i, states) for i in lane_iss))
        else:
            p.append('<div class="kv">issue なし</div>')
        p.append("</div>")

    # ── 全体・基盤(cross/infra。特定の敷地に紐づかない横断課題)
    cross_iss = [i for i in issues if i["estate"] in ("cross", "infra")]
    p.append('<div id="lane-cross" class="lane cross" data-site="%s"><h3>%s</h3>'
             '<div class="area">邸にも溜池・外堀にも紐づかない横断課題(方法論・基盤・座組)</div>'
             % (esc(CROSS_KEY), esc(CROSS_LABEL)))
    if cross_iss:
        p.append('<ul class="iss">%s</ul>' % "".join(issue_li(i, states) for i in cross_iss))
    else:
        p.append('<div class="kv">issue なし</div>')
    p.append("</div>")  # #lane-cross
    p.append("</div>")  # .lanes

    # 横断の相関(敷地の見方の一部なのでこのタブに置く)
    p.append('<h2>横断の相関<span class="h2note">円の太さ=言及した open issue 件数・数字=件数</span></h2>')
    p.append('<div class="netwrap">')
    p.append(network_svg(rel, open_counts))
    p.append('<div class="netcap">丸=各敷地(open issue数を併記)。中央の「共通」は特定の敷地に'
             "紐づかない横断課題。線は2敷地にまたがる issue(藍色)/ 1敷地+横断の issue(灰色)を表す。"
             "全敷地に及ぶ課題は「共通」から各敷地へ辺が伸びる。%s</div>"
             % (("全敷地共通(敷地を特定しない)課題 %d件。" % rel["general"]) if rel["general"] else ""))
    p.append("</div>")
    p.append("</div>")  # panel sites

    # ── 従タブ: 最近の動き
    p.append('<div class="panel" data-panel="feed" hidden>')
    p.append("<h2>最近の動き(全ブランチ)</h2><div class='scroll'><table class='feed'>")
    for c in commits[:20]:
        p.append('<tr><td class="t">%s</td><td class="e">%s</td>'
                 '<td class="h">%s</td><td>%s</td></tr>'
                 % (esc(ago(c["t"])), esc(SITES.get(c["estate"], "—")),
                    esc(c["h"]), esc(c["s"])))
    p.append("</table></div>")
    p.append("</div>")  # panel feed

    p.append("<footer>Tools/Session/build_board_html.py が生成。正典: "
             ".git/edo-board(issue)/ docs/Sashizu/*_sashizu.json(_pending)/ "
             "docs/Sashizu/README.md(状態)。作法: docs/session-board.md<br>"
             "タスク一覧は全敷地を1枚に出し、フィルタで絞る。要裁定・敷地別・最近の動きは別タブ。<br>"
             "フィルタと並べ替えはこのページ内だけで完結する(サーバも保存も無い)。"
             "開いていたタブだけは次に開いたときも復元する。</footer>")
    p.append("</div>")
    p.append("<script>%s</script>" % JS)
    return "\n".join(p)


def main():
    issues = load_issues()
    pending = load_pending()
    commits = load_commits()
    claims = load_claims()
    states = load_readme_states()
    reviews = load_reviews()
    summary = build_summary(issues, pending, commits, claims)
    os.makedirs(OUT, exist_ok=True)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "dashboard.html"), "w", encoding="utf-8").write(
        build_html(issues, pending, commits, claims, states, summary, reviews))
    print("dashboard: %s\nsummary:   %s" % (os.path.join(OUT, "dashboard.html"),
                                            os.path.join(OUT, "summary.json")))


if __name__ == "__main__":
    main()
