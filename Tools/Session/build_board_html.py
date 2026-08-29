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
SITES = {"matsudaira": "松江松平邸", "sanno": "山王社", "okabe": "岡部邸",
         "doi": "土井邸", "sotobori": "外堀・溜池"}
ESTATES = {"matsudaira": "松江松平邸", "sanno": "山王社", "okabe": "岡部邸", "doi": "土井邸"}
SHORT = {"matsudaira": "松", "sanno": "山", "okabe": "岡", "doi": "土", "sotobori": "堀"}
MENTION = {  # 関係図・巡回検知が本文から敷地を拾うときの表記ゆれ(index[1]は path 突合にも使う)
    "matsudaira": ["松平", "松江", "Matsudaira"],
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


def load_junsu_baseline():
    """前回ユーザー裁定時点の巡数(作事奉行の巡回状態から)。無ければ空。"""
    fp = os.path.join(OUT, "state.json")
    try:
        return json.load(open(fp, encoding="utf-8")).get("junsu_baseline", {})
    except Exception:
        return {}


def load_readme_states():
    """README の表から敷地ごとの状態と、公開済み指図 Artifact の URL を拾う。
    URL は表の5列目(素の https://claude.ai/code/artifact/... 行末)。
    敷地が worktree 止まりで README にまだ載っていなければ単に出ない(それが実情)。"""
    out = {}
    fp = os.path.join(ROOT, "docs", "Sashizu", "README.md")
    try:
        for ln in open(fp, encoding="utf-8"):
            m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*\[(\w+)_sashizu\.html\]"
                        r"[^|]*\|\s*(https://\S+)?\s*\|", ln)
            if m and m.group(4) in SITES:
                out[m.group(4)] = {"name": m.group(1), "area": m.group(2),
                                   "state": m.group(3).strip("* "), "url": m.group(5)}
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
.fcheck{font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:5px;cursor:pointer}
.fsearch{font:inherit;font-size:12.5px;padding:5px 10px;border:1px solid var(--line);
  border-radius:6px;background:var(--card);color:var(--ink);min-width:220px}
.fsearch:focus{outline:2px solid var(--ai);outline-offset:-1px}
.fresetbtn{margin-left:auto;color:var(--muted)}
.fcount{font-size:11.5px;color:var(--muted);margin:2px 0 20px}

h2{font-family:'Shippori Mincho',serif;font-weight:600;font-size:17px;
  border-bottom:2px solid var(--ink);padding-bottom:5px;margin:34px 0 14px;letter-spacing:.06em}
.h2note{font-size:11.5px;color:var(--muted);font-weight:400;letter-spacing:0;margin-left:8px}
.dcard{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--oud);
  border-radius:6px;padding:14px 18px;margin-bottom:12px}
.dcard h3{margin:0 0 8px;font-size:15px}
.dcard .id{font-family:var(--mono);color:var(--muted);font-size:12px;margin-right:8px}
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
.kv{font-size:12.5px;color:var(--muted);margin:3px 0}
.kv b{color:var(--ink);font-weight:500}
.kv .n{font-family:var(--mono)}
.metric{margin:10px 0}
.metric .lbl{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:3px}

/* ── issue 行(見やすさ改善: バッジ化・行間・info は控えめに) */
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
  var siteBtns = $all('#siteFilter .fchip');
  var typeBtns = $all('#typeFilter .fchip');
  var showDone = document.getElementById('showDone');
  var search = document.getElementById('fsearch');
  var resetBtn = document.getElementById('fReset');
  var items = $all('.fitem');
  var lanes = $all('.lane[data-site]');
  var countEl = document.getElementById('fcount');

  function activeVals(btns, attr){
    return new Set(btns.filter(function(b){ return b.classList.contains('active'); })
                        .map(function(b){ return b.getAttribute(attr); }));
  }
  function apply(){
    var sites = activeVals(siteBtns, 'data-site');
    var types = activeVals(typeBtns, 'data-type');
    var q = search.value.trim().toLowerCase();
    var shown = 0;
    items.forEach(function(el){
      var okSite = sites.has(el.getAttribute('data-site'));
      var okType = types.has(el.getAttribute('data-type'));
      var st = el.getAttribute('data-status');
      var okStatus = showDone.checked || (st !== 'done' && st !== 'dropped');
      var okSearch = !q || el.textContent.toLowerCase().indexOf(q) !== -1;
      var vis = okSite && okType && okStatus && okSearch;
      el.style.display = vis ? '' : 'none';
      if (vis) shown++;
    });
    lanes.forEach(function(l){
      l.style.display = sites.has(l.getAttribute('data-site')) ? '' : 'none';
    });
    if (countEl) countEl.textContent = shown + ' 件表示中';
  }
  siteBtns.concat(typeBtns).forEach(function(b){
    b.addEventListener('click', function(){ b.classList.toggle('active'); apply(); });
  });
  if (showDone) showDone.addEventListener('change', apply);
  if (search) search.addEventListener('input', apply);
  if (resetBtn) resetBtn.addEventListener('click', function(){
    siteBtns.concat(typeBtns).forEach(function(b){ b.classList.add('active'); });
    showDone.checked = false;
    search.value = '';
    apply();
  });
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


def filterbar_html():
    p = ['<div class="filterbar">']
    p.append('<div class="fgroup" id="siteFilter"><span class="flabel">敷地</span>')
    for e, name in SITES.items():
        p.append('<button type="button" class="fchip active" data-site="%s">%s</button>'
                 % (esc(e), esc(name)))
    p.append('<button type="button" class="fchip active" data-site="%s">%s</button>'
             % (esc(CROSS_KEY), esc(CROSS_LABEL)))
    p.append("</div>")
    p.append('<div class="fgroup" id="typeFilter"><span class="flabel">種別</span>')
    for t in ("blocker", "decision", "task", "info"):
        p.append('<button type="button" class="fchip active" data-type="%s">%s</button>'
                 % (esc(t), esc(TYPE_LABEL[t])))
    p.append("</div>")
    p.append('<label class="fcheck"><input type="checkbox" id="showDone"> 完了・見送りも表示</label>')
    p.append('<input type="search" id="fsearch" class="fsearch" placeholder="IDやキーワードで絞り込み…">')
    p.append('<button type="button" id="fReset" class="fchip fresetbtn">リセット</button>')
    p.append("</div>")
    p.append('<div id="fcount" class="fcount"></div>')
    return "".join(p)


def build_html(issues, pending, commits, claims, states, summary):
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

    # ── フィルタバー(敷地・種別・完了表示・検索)
    p.append(filterbar_html())

    # ── 要裁定
    p.append("<h2>要裁定 — ユーザーの判断待ち</h2>")
    if not waits:
        p.append('<div class="quiet">裁定待ちはありません。</div>')
    for i in waits:
        d = i.get("decision") or {}
        # id 付与の理由は issue_li と同じ — コメントのアンカーを issue 単位で固定する
        p.append('<div id="%s" class="dcard fitem" data-site="%s" data-type="%s" data-status="%s">'
                 '<h3><span class="id">%s</span>[%s] %s</h3>'
                 % (esc(i["id"]), esc(display_site(i)), esc(i["type"]), esc(i["status"]),
                    esc(i["id"]), esc(SITES.get(i["estate"], i["estate"])), esc(i["title"])))
        if d:
            p.append('<dl class="dl">')
            p.append("<dt>背景</dt><dd>%s</dd>" % esc(d.get("background", "")))
            p.append("<dt>選択肢</dt><dd>%s</dd>"
                     % "<br>".join(esc(o) for o in d.get("options", [])))
            p.append('<dt>推奨</dt><dd class="rec">%s</dd>' % esc(d.get("recommend", "")))
            p.append("<dt>影響</dt><dd>%s</dd>" % esc(d.get("impact", "")))
            p.append("</dl>")
        p.append(refs_html(i, states))
        p.append("</div>")

    # ── 敷地別レーン(邸はスパークライン+三巡則ゲージつき。邸を持たない敷地は
    #    issue 一覧だけ。「全体・基盤」は cross/infra をまとめた専用レーン)
    p.append("<h2>敷地別<span class=\"h2note\">邸だけでなく溜池・外堀のような敷地も同格で並ぶ</span></h2>"
              "<div class='lanes'>")
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
        if st.get("state"):
            p.append('<span class="state">%s</span>' % esc(st["state"]))
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
    p.append("</div></div>")

    # ── 横断の相関
    p.append('<h2>横断の相関<span class="h2note">円の太さ=言及した open issue 件数・数字=件数</span></h2>')
    p.append('<div class="netwrap">')
    p.append(network_svg(rel, open_counts))
    p.append('<div class="netcap">丸=各敷地(open issue数を併記)。中央の「共通」は特定の敷地に'
             "紐づかない横断課題。線は2敷地にまたがる issue(藍色)/ 1敷地+横断の issue(灰色)を表す。"
             "全敷地に及ぶ課題は「共通」から各敷地へ辺が伸びる。%s</div>"
             % (("全敷地共通(敷地を特定しない)課題 %d件。" % rel["general"]) if rel["general"] else ""))
    p.append("</div>")

    # ── 最近の動き
    p.append("<h2>最近の動き(全ブランチ)</h2><div class='scroll'><table class='feed'>")
    for c in commits[:20]:
        p.append('<tr><td class="t">%s</td><td class="e">%s</td>'
                 '<td class="h">%s</td><td>%s</td></tr>'
                 % (esc(ago(c["t"])), esc(SITES.get(c["estate"], "—")),
                    esc(c["h"]), esc(c["s"])))
    p.append("</table></div>")

    p.append("<footer>Tools/Session/build_board_html.py が生成。正典: "
             ".git/edo-board(issue)/ docs/Sashizu/*_sashizu.json(_pending)/ "
             "docs/Sashizu/README.md(状態)。作法: docs/session-board.md<br>"
             "フィルタ(敷地・種別・完了表示・検索)はこのページ内だけで完結する — "
             "サーバや保存は無く、再読込すると全表示に戻る。</footer>")
    p.append("</div>")
    p.append("<script>%s</script>" % JS)
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
