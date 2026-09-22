#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作業状況の系図 — git の枝と直近コミット、いま動いている普請(claim)、邸ごとの工程、掲示板の残件を
1 枚の HTML に刷る(2026-09-22)。

【何を読むか】どれも読むだけ。何も書き換えない(出力の HTML 以外)。
    git log --all / git branch / git worktree list      系図・枝の台帳・未マージ
    edo_session.load_all()                              生きている claim(心拍 TTL 45 分)
    kansei_gate / review_gate                           邸の工程(完成条件の表 → 検図関門)
    edo_board.py list --json                            掲示板の残件

【使い方】
    python3 Tools/Session/repo_graph.py                 # <git-common-dir>/edo-graph/repo_graph.html へ刷る
    python3 Tools/Session/repo_graph.py --open          # 刷ってブラウザで開く
    python3 Tools/Session/repo_graph.py --out X.html    # 刷り先を指す
    python3 Tools/Session/repo_graph.py --commits 200   # 系図に出すコミット数(既定 110)
    python3 Tools/Session/repo_graph.py --json          # HTML を刷らず、集めた値だけ標準出力へ
    python3 Tools/Session/repo_graph.py --selftest

⚠ 既定の刷り先は .git の中(edo-locks と同じ流儀)。作業ツリーに何も増やさないので `git status` を汚さない。
⚠ 刷った HTML は**その時点の写し**。読み手へ渡すときは Artifact に上げ直す(このスクリプトは公開しない)。
⛔ 邸の工程の段は gate から導く。導けない進み具合だけ HINTS に手書きで補い、画面に † を出す
   — HINTS は腐るので、表(kansei)を起票したら該当行を消す。
"""
import argparse
import collections
import datetime
import importlib
import json
import os
import re
import subprocess
import sys
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "Tools", "Sashizu"))

SEP = "\x1f"
LIVE_MIN = 15.0  # この心拍以内を「生きている」と数える(TTL は 45 分)

STAGES = ["下書き", "考証+指図", "部材", "実装", "完成"]

# 表示名。⚠ 見た目だけ — 邸の一覧そのものは gate と掲示板から集める(ここに無い邸は id のまま出る)。
NAMES = {
    "matsudaira_dewa": "松江松平邸", "sanno": "山王社", "okabe": "岡部邸", "doi": "土井邸",
    "kyogoku_bitchu": "京極備中守邸", "sotobori": "外堀", "niwa_sakyo": "丹羽左京邸",
    "naito_kii": "内藤紀伊守邸", "typology": "類型(町屋・寺社・公有地)",
    "matsudaira_yamato": "松平大和守邸", "infra": "基盤(道具・規則)", "cross": "横断",
}

# 手書きの補足(2026-09-22 時点)。表(kansei)が無い邸は gate からは「実装前」に見えるが、
# 実際は建て始めている物がある。{id: (段, 状態, 注)}。表を起票したら消す。
HINTS = {
    "okabe": (4, "実装中", "主郭12まで建て済・完成条件の表は未起票。外周の越境と練塀の隅が残件"),
    "sotobori": (4, "一部実装", "00001〜00003 実装済・完成条件の表は未起票"),
    "doi": (3, "実装未着手", "指図は通ったが、その後の変更で検分の検め直しが要る"),
    "typology": (4, "実装中", "全区画をまず類型で建てる車線。庭(Stage5)・寺社16区画・町屋の建て直しが進行中"),
}


def git(*a, check=True):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(a), r.stderr.strip()))
    return r.stdout


def common_git_dir():
    d = git("rev-parse", "--path-format=absolute", "--git-common-dir", check=False).strip()
    return d or os.path.join(REPO, ".git")


# ── 系図 ─────────────────────────────────────────────────────────────────────
SCOPE_RE = re.compile(r"^(\w+)\((.+?)\)\s*[:：]")
CAT_BY_SCOPE = {
    "typology": ("類型", "町屋", "寺社", "公有地"),
    "parts": ("部材", "御殿", "置き方"),
    "infra": ("基盤", "フック", "門番", "インフラ"),
    "rec": ("掲示板", "日誌", "報告の作法", "記録", "docs"),
    "estate": ("山王", "岡部", "土井", "松江松平", "松平", "京極", "丹羽", "外堀", "内藤", "大和守"),
}


def classify(sub):
    m = SCOPE_RE.match(sub)
    typ = m.group(1) if m else (sub.split(":")[0].strip() if ":" in sub[:12] else "")
    scope = m.group(2) if m else ""
    for cat, scopes in CAT_BY_SCOPE.items():
        if scope in scopes:
            return typ, scope, cat
    if typ == "docs":
        return typ, scope, "rec"
    if typ in ("chore", "build"):
        return typ, scope, "infra"
    return typ, scope, "other"


def collect_commits(n):
    raw = git("log", "--all", "--date-order", "--date=format:%Y-%m-%d %H:%M",
              "--pretty=format:%H" + SEP + "%P" + SEP + "%ad" + SEP + "%D" + SEP + "%s", "-%d" % n)
    commits, idx = [], {}
    for i, line in enumerate(l for l in raw.split("\n") if l.strip()):
        h, p, d, dec, sub = (line.split(SEP) + [""] * 5)[:5]
        typ, scope, cat = classify(sub)
        refs = []
        for r in (dec or "").split(","):
            r = r.strip().replace("HEAD -> ", "")
            if r and r != "HEAD" and not r.startswith("tag: "):
                refs.append(r)
        commits.append(dict(h=h, s=h[:8], p=p.split(), d=d, refs=refs, sub=sub, typ=typ, scope=scope,
                            cat=cat, tickets=sorted(set(re.findall(r"EDO-\d{4}", sub)))))
        idx[h] = i
    return commits, idx


def assign_lanes(commits, idx):
    """親をたどって車線(列)を割る。first-parent が同じ列を続け、merge の第2親は空き列へ。"""
    lanes = []
    for c in commits:
        k = lanes.index(c["h"]) if c["h"] in lanes else None
        if k is None:
            k = lanes.index(None) if None in lanes else len(lanes)
            if k == len(lanes):
                lanes.append(None)
        c["lane"] = k
        for j, exp in enumerate(lanes):
            if j != k and exp == c["h"]:
                lanes[j] = None
        lanes[k] = c["p"][0] if c["p"] else None
        for pa in c["p"][1:]:
            if pa in lanes:
                continue
            j = lanes.index(None) if None in lanes else len(lanes)
            if j == len(lanes):
                lanes.append(None)
            lanes[j] = pa
    edges = []
    for i, c in enumerate(commits):
        for n, pa in enumerate(c["p"]):
            if pa in idx:
                pc = commits[idx[pa]]
                edges.append(dict(fr=c["lane"], fy=i, to=pc["lane"], ty=idx[pa], merge=n > 0, cat=c["cat"]))
            else:
                edges.append(dict(fr=c["lane"], fy=i, to=c["lane"], ty=len(commits), merge=n > 0,
                                  cat=c["cat"], open=True))
    return (max(c["lane"] for c in commits) + 1 if commits else 1), edges


def collect_branches():
    wtmap = {}
    for l in git("worktree", "list").strip().split("\n"):
        parts = l.split()
        if len(parts) >= 3 and parts[-1].startswith("["):
            wtmap[parts[-1].strip("[]")] = parts[0]
    out, unmerged = [], {}
    for b in git("branch", "--format=%(refname:short)").split():
        lr = git("rev-list", "--left-right", "--count", "main...%s" % b, check=False).split() or ["0", "0"]
        behind, ahead = int(lr[0]), int(lr[1])
        last = (git("log", "-1", "--date=format:%Y-%m-%d", "--format=%ad" + SEP + "%s", b).strip().split(SEP) + ["", ""])[:2]
        # ⚠ main と共通の祖先が無い枝 = 履歴の書き換え前(LFS 移行)の写し。「未マージの仕事」ではない
        orphan = not git("merge-base", "main", b, check=False).strip()
        out.append(dict(name=b, behind=behind, ahead=ahead, date=last[0], sub=last[1],
                        wt=wtmap.get(b), head=(b == "main"), orphan=orphan))
        if ahead and b != "main" and not orphan:
            unmerged[b] = [dict(s=x.split(" ", 2)[0], d=x.split(" ", 2)[1], sub=x.split(" ", 2)[2])
                           for x in git("log", "--date=short", "--pretty=%h %ad %s", "main..%s" % b).strip().split("\n")
                           if x.count(" ") >= 2][:12]
    return out, unmerged


def collect_series(days=56):
    cnt = collections.Counter(git("log", "--all", "--date=short", "--pretty=format:%ad").split())
    today = datetime.date.today()
    return [dict(d=(today - datetime.timedelta(days=k)).isoformat(),
                 n=cnt.get((today - datetime.timedelta(days=k)).isoformat(), 0))
            for k in range(days - 1, -1, -1)]


# ── 車線(claim)・掲示板 ──────────────────────────────────────────────────────
def collect_claims():
    try:
        es = importlib.import_module("edo_session")
        now, out = time.time(), []
        for c in es.load_all():
            paths = c.get("paths", [])
            out.append(dict(sid=c["session"], note=c.get("note", ""), phase=c.get("phase", ""),
                            estate=[p[8:] for p in paths if p.startswith("sashizu:")],
                            res=c.get("resources", []), files=[p for p in paths if not p.startswith("sashizu:")],
                            beat=round((now - c["heartbeat"]) / 60, 1), age=round((now - c["started"]) / 60, 1)))
        return sorted(out, key=lambda x: x["beat"])
    except Exception as e:  # 門番が読めなくても系図は刷る
        sys.stderr.write("repo_graph: claim を読めない(%s)\n" % e)
        return []


def collect_board():
    r = subprocess.run([sys.executable, os.path.join(HERE, "edo_board.py"), "list", "--json"],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode:
        sys.stderr.write("repo_graph: 掲示板を読めない(%s)\n" % r.stderr.strip()[:120])
        return []
    now, out = time.time(), []
    for b in json.loads(r.stdout or "[]"):
        last = max([x.get("t", 0) for x in b.get("log", [])] or [0])
        out.append(dict(id=b["id"], estate=b.get("estate", ""), kind=b.get("type", ""),
                        state=b.get("status", ""), title=b.get("title", ""),
                        age=int((now - last) / 86400) if last else None))
    return out


# ── 邸の工程 ─────────────────────────────────────────────────────────────────
def collect_estates(board):
    """段は gate から導く: 表が done→5 / built→4 / 表なしで検図関門が緑→3 / 赤→2。"""
    try:
        kg = importlib.import_module("kansei_gate")
        rg = importlib.import_module("review_gate")
    except Exception as e:
        sys.stderr.write("repo_graph: gate を読めない(%s)\n" % e)
        return []
    out, seen = [], set()
    for n in rg.estate_names():
        seen.add(n)
        ph = kg.phase(n)
        row = dict(id=n, kana=n, name=NAMES.get(n, n), hint=False)
        if ph == "done":
            doc, _ = kg.rows(n)
            row.update(stage=5, state="完成", gate="完成条件 5/5", note="完成 %s。以後の指摘は欄の上書き" % doc.get("completed"))
        elif ph == "built":
            doc, rr = kg.rows(n)
            npass = sum(1 for r in rr if r[0] == "⭕")
            nfail = sum(1 for r in rr if r[0] == "⛔")
            row.update(stage=4, state="実装中", gate="完成条件 %d/5%s" % (npass, "(不合格%d・未測%d)" % (nfail, 5 - npass - nfail) if npass < 5 else ""),
                       note="完成条件の表が関門" if npass < 5 else "")
        else:
            red, rr = rg.gate(n)
            bad = [r for r in rr if r[0] in ("⛔", "⚠")]
            row.update(stage=3 if red == 0 else 2, state="検分通過" if red == 0 else "検分待ち",
                       gate=("検図関門 ⛔ %d件" % red) if red else "検図関門 通過",
                       note="・".join(r[2] for r in bad)[:70])
        h = HINTS.get(n)
        if h and ph == "design":
            row.update(stage=h[0], state=h[1], note=h[2], hint=True)
        out.append(row)
    # 指図の無い担当(掲示板だけにある邸・横断・基盤)
    for e in sorted({b["estate"] for b in board if b["estate"]} - seen):
        row = dict(id=e, kana=e, name=NAMES.get(e, e), stage=None, state="担当のみ", gate="関門の対象外",
                   note="", hint=False)
        if e in HINTS:
            row.update(stage=HINTS[e][0], state=HINTS[e][1], note=HINTS[e][2], hint=True)
        out.append(row)
    order = {5: 0, 4: 1, 3: 2, 2: 3, 1: 4, None: 9}
    out.sort(key=lambda r: (order.get(r["stage"], 8), r["id"]))
    return out


def collect(n_commits):
    commits, idx = collect_commits(n_commits)
    nlanes, edges = assign_lanes(commits, idx)
    branches, unmerged = collect_branches()
    board = collect_board()
    ao = git("rev-list", "--count", "origin/main..main", check=False).strip()
    bo = git("rev-list", "--count", "main..origin/main", check=False).strip()
    return dict(commits=commits, edges=edges, lanes=nlanes, branches=branches, unmerged=unmerged,
                ahead_origin=int(ao or 0), behind_origin=int(bo or 0), series=collect_series(),
                claims=collect_claims(), board=board, estates=collect_estates(board), stages=STAGES,
                live_min=LIVE_MIN, gen=time.strftime("%Y-%m-%d %H:%M"))


TEMPLATE = r"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>edo-unity 普請の系図</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@600;700&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap">
<style>
:root{
  --paper:#eaecef; --surface:#f5f6f8; --surface-2:#e0e3e8; --ink:#15181d; --ink-2:#4a515c;
  --ink-3:#7b838f; --rule:#c9cdd4; --rule-2:#d9dce1;
  --ai:#2d4a7c;        /* 藍 — 幹・構造 */
  --ai-soft:#6a86b4;
  --shu:#c0442b;       /* 朱 — いま動いている */
  --shu-soft:#e2a595;
  --matsu:#2f6f52;     /* 松葉 — 済 */
  --odo:#9a6a14;       /* 黄土 — 待ち */
  --murasaki:#6a4a86; --cha:#7a5a3a;
  --shadow:0 1px 2px rgba(21,24,29,.07);
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --paper:#111318; --surface:#171a20; --surface-2:#20242c; --ink:#e4e7ec; --ink-2:#a8b0bb;
  --ink-3:#737c88; --rule:#2c313a; --rule-2:#232830;
  --ai:#7ea6e0; --ai-soft:#4d6893;
  --shu:#e9765c; --shu-soft:#8a4536;
  --matsu:#5aa383; --odo:#c99a3e; --murasaki:#a288c4; --cha:#b28a63;
  --shadow:0 1px 2px rgba(0,0,0,.4);
}}
:root[data-theme="dark"]{
  --paper:#111318; --surface:#171a20; --surface-2:#20242c; --ink:#e4e7ec; --ink-2:#a8b0bb;
  --ink-3:#737c88; --rule:#2c313a; --rule-2:#232830;
  --ai:#7ea6e0; --ai-soft:#4d6893; --shu:#e9765c; --shu-soft:#8a4536;
  --matsu:#5aa383; --odo:#c99a3e; --murasaki:#a288c4; --cha:#b28a63;
  --shadow:0 1px 2px rgba(0,0,0,.4);
}
*{box-sizing:border-box}
body{
  background:var(--paper); color:var(--ink);
  font-family:"Zen Kaku Gothic New",-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;
  font-size:14px; line-height:1.7; margin:0;
  padding-block:32px 64px; padding-inline:16px;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px;margin:0 auto}
h1,h2,h3{font-family:"Shippori Mincho",serif;font-weight:600;text-wrap:balance;margin:0}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
.num{font-variant-numeric:tabular-nums}

/* ── 表題 ── */
header.masthead{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:6px}
.masthead h1{font-size:clamp(26px,5vw,38px);letter-spacing:.04em;line-height:1.25}
.masthead .sub{color:var(--ink-2);font-size:13px;margin-top:6px;display:flex;flex-wrap:wrap;gap:6px 16px}
.masthead .sub b{font-weight:500;color:var(--ink)}
.asof{color:var(--ink-3);font-size:12px}

/* ── 要点の列 ── */
.vitals{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));
  gap:1px;background:var(--rule);border:1px solid var(--rule);margin:22px 0 34px}
.vital{background:var(--surface);padding:12px 14px}
.vital .k{font-size:11px;letter-spacing:.12em;color:var(--ink-3);text-transform:uppercase}
.vital .v{font-family:"Shippori Mincho",serif;font-size:26px;line-height:1.2;margin-top:2px}
.vital .v small{font-size:12px;font-family:"Zen Kaku Gothic New",sans-serif;color:var(--ink-2);margin-left:3px}
.vital .n{font-size:11.5px;color:var(--ink-3);margin-top:2px}
.vital.alert .v{color:var(--shu)}

section{margin:40px 0}
.head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
  border-bottom:1px solid var(--rule);padding-bottom:7px;margin-bottom:16px}
.head h2{font-size:19px;letter-spacing:.05em}
.head .note{font-size:12px;color:var(--ink-3)}
.head .spacer{flex:1}

/* ── 生きている車線 ── */
.lanes{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.lane{background:var(--surface);border:1px solid var(--rule);border-left:3px solid var(--ink-3);
  padding:10px 12px;box-shadow:var(--shadow)}
.lane.live{border-left-color:var(--shu)}
.lane.idle{opacity:.72}
.lane .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.lane .sid{font-size:11.5px;color:var(--ink-3)}
.lane .beat{font-size:11px;color:var(--ink-3)}
.lane.live .beat{color:var(--shu);font-weight:700}
.lane .note{font-size:12.5px;margin-top:4px;line-height:1.55}
.lane .note.none{color:var(--ink-3)}
.lane .tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:7px}
.tag{font-size:10.5px;padding:1px 6px;border:1px solid var(--rule);color:var(--ink-2);
  background:var(--surface-2);letter-spacing:.02em}
.tag.res{border-color:var(--shu);color:var(--shu);background:transparent;font-weight:700}
.tag.zone{border-color:var(--ai);color:var(--ai)}
.lane .files{font-size:11px;color:var(--ink-3);margin-top:6px;line-height:1.5;
  font-family:ui-monospace,Menlo,monospace;word-break:break-all}

/* ── 工程の帯 ── */
.estates{border:1px solid var(--rule);background:var(--surface)}
.est{display:grid;grid-template-columns:minmax(140px,1.15fr) 172px minmax(150px,1.5fr) 54px;
  gap:12px;align-items:center;padding:11px 14px;border-bottom:1px solid var(--rule-2)}
.est:last-child{border-bottom:0}
.est .nm{font-weight:500}
.est .nm span{display:block;font-size:10.5px;color:var(--ink-3);letter-spacing:.06em;
  font-family:ui-monospace,Menlo,monospace}
.rail{display:flex;gap:2px}
.seg{height:9px;flex:1;background:var(--surface-2);border:1px solid var(--rule-2)}
.seg.done{background:var(--ai);border-color:var(--ai)}
.seg.now{background:var(--shu);border-color:var(--shu)}
.seg.fin{background:var(--matsu);border-color:var(--matsu)}
.est .gate{font-size:12px;color:var(--ink-2)}
.est .gate b{color:var(--ink);font-weight:500}
.est .gate.bad b{color:var(--shu)}
.est .gate.ok b{color:var(--matsu)}
.est .gate em{display:block;font-style:normal;font-size:11px;color:var(--ink-3);line-height:1.45}
.norail{font-size:11px;color:var(--ink-3)}
.est .cnt{text-align:right;font-size:12px;color:var(--ink-3)}
.est .cnt b{font-size:17px;color:var(--ink);font-family:"Shippori Mincho",serif;font-weight:600}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--ink-3);margin-top:9px}
.legend i{display:inline-block;width:20px;height:8px;vertical-align:middle;margin-right:5px;border:1px solid var(--rule-2)}

/* ── 系図 ── */
.filters{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.chip{font-size:11.5px;padding:3px 10px;border:1px solid var(--rule);background:var(--surface);
  color:var(--ink-2);cursor:pointer;font-family:inherit;letter-spacing:.02em}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.chip .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;vertical-align:1px}
.chip:focus-visible,.branchrow:focus-visible{outline:2px solid var(--ai);outline-offset:2px}
.graphbox{border:1px solid var(--rule);background:var(--surface);max-height:660px;overflow:auto;position:relative}
.graphinner{position:relative}
.graphinner svg{position:absolute;left:0;top:0;pointer-events:none}
.crow{display:grid;grid-template-columns:var(--gw) 74px 60px 1fr auto;gap:10px;align-items:center;
  padding:0 12px 0 0;font-size:12.5px;white-space:nowrap;position:relative;height:26px;line-height:26px}
.crow.alt{background:color-mix(in srgb,var(--surface-2) 55%,transparent)}
.crow:hover{background:var(--surface-2)}
.crow.dim{opacity:.26}
.crow .h{color:var(--ink-3);font-size:11px}
.crow .sc{font-size:10.5px;letter-spacing:.04em;overflow:hidden;text-overflow:ellipsis}
.crow .sj{overflow:hidden;text-overflow:ellipsis;color:var(--ink)}
.crow .tm{color:var(--ink-3);font-size:11px}
.crow .rf{font-size:10px;padding:0 5px;border:1px solid var(--ai);color:var(--ai);margin-right:5px}
.crow .rf.wt{border-color:var(--shu);color:var(--shu)}
.crow .tk{font-size:10px;color:var(--ink-3);border-bottom:1px dotted var(--rule);margin-left:6px}
.ghint{font-size:11.5px;color:var(--ink-3);margin-top:8px;display:flex;gap:16px;flex-wrap:wrap}

/* ── 枝の台帳 ── */
.tablebox{border:1px solid var(--rule);background:var(--surface);overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:620px}
th{text-align:left;font-weight:500;font-size:11px;letter-spacing:.1em;color:var(--ink-3);
  padding:8px 12px;border-bottom:1px solid var(--rule);text-transform:uppercase}
td{padding:7px 12px;border-bottom:1px solid var(--rule-2);vertical-align:top}
tr:last-child td{border-bottom:0}
td.nm{font-family:ui-monospace,Menlo,monospace;font-size:12px;white-space:nowrap}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pill{font-size:10.5px;padding:1px 7px;border:1px solid var(--rule);color:var(--ink-3);white-space:nowrap}
.pill.merged{border-color:var(--matsu);color:var(--matsu)}
.pill.left{border-color:var(--shu);color:var(--shu);font-weight:700}
.pill.wt{border-color:var(--ai);color:var(--ai)}
.pill.old{border-color:var(--rule);color:var(--ink-3)}
td.sub{color:var(--ink-2);max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
details.unm{margin-top:12px;border:1px solid var(--rule);background:var(--surface)}
details.unm summary{padding:9px 14px;cursor:pointer;font-size:12.5px;color:var(--ink-2)}
details.unm summary b{color:var(--shu)}
details.unm .body{padding:0 14px 12px;font-size:12px}
details.unm .u{display:flex;gap:8px;padding:3px 0;border-top:1px solid var(--rule-2)}
details.unm .u .mono{color:var(--ink-3);font-size:11px;white-space:nowrap}
details.unm .u .t{color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ── 日ごとの量 ── */
.strip{border:1px solid var(--rule);background:var(--surface);padding:14px;overflow-x:auto}
.bars{display:flex;align-items:flex-end;gap:2px;height:110px;min-width:560px}
.bar{flex:1;background:var(--ai-soft);min-height:1px;position:relative}
.bar.zero{background:var(--rule-2);height:1px!important}
.bar.hot{background:var(--ai)}
.bar.today{background:var(--shu)}
.barlabels{display:flex;gap:2px;margin-top:6px;min-width:560px;font-size:9.5px;color:var(--ink-3)}
.barlabels span{flex:1;text-align:center;overflow:hidden}
footer{margin-top:52px;border-top:1px solid var(--rule);padding-top:14px;
  font-size:11.5px;color:var(--ink-3);line-height:1.8}
footer code{font-family:ui-monospace,Menlo,monospace;background:var(--surface-2);padding:1px 5px}
@media(max-width:720px){
  .est{grid-template-columns:1fr 54px;grid-template-areas:"nm cnt" "rail rail" "gate gate";gap:7px 12px}
  .est .nm{grid-area:nm}.est .rail{grid-area:rail}.est .gate{grid-area:gate}.est .cnt{grid-area:cnt}
  .crow{grid-template-columns:var(--gw) 60px 1fr;font-size:12px}
  .crow .sc,.crow .tm{display:none}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
<div class="wrap">

<header class="masthead">
  <h1>edo-unity 普請の系図</h1>
  <div class="sub">
    <span>安政三年(1856)の赤坂・溜池</span>
    <span>Unity 6000.5.2f1 ・ URP 17.5.0 ・ シーン1枚</span>
    <span class="asof" id="asof"></span>
  </div>
</header>

<div class="vitals" id="vitals"></div>

<section>
  <div class="head">
    <h2>いま動いている普請</h2>
    <span class="note">心拍 15 分以内を「生きている」とする(TTL 45 分)</span>
  </div>
  <div class="lanes" id="lanes"></div>
</section>

<section>
  <div class="head">
    <h2>邸ごとの工程</h2>
    <span class="note">① 下書き → ② 考証+指図 → ③ 部材 → ④ 実装 → ⑤ 完成</span>
  </div>
  <div class="estates" id="estates"></div>
  <div class="legend">
    <span><i style="background:var(--ai);border-color:var(--ai)"></i>済んだ段</span>
    <span><i style="background:var(--shu);border-color:var(--shu)"></i>いまの段</span>
    <span><i style="background:var(--matsu);border-color:var(--matsu)"></i>完成</span>
    <span>右端の数字＝その邸で開いている掲示板の件数</span>
    <span>†＝機械では読めない進み具合を手書きで補った(スクリプト冒頭の HINTS)</span>
  </div>
</section>

<section>
  <div class="head">
    <h2>系図</h2>
    <span class="note" id="grange"></span>
    <span class="spacer"></span>
  </div>
  <div class="filters" id="filters"></div>
  <div class="graphbox"><div class="graphinner" id="graph"></div></div>
  <div class="ghint">
    <span>◯＝コミット ／ ◇＝マージ ／ 破線＝この窓の外へ続く親</span>
    <span>札を押すと、その系統だけが残る</span>
  </div>
</section>

<section>
  <div class="head">
    <h2>枝の台帳</h2>
    <span class="note">main に入っていない仕事がどこに残っているか</span>
  </div>
  <div class="tablebox">
    <table>
      <thead><tr><th>枝</th><th>状態</th><th class="n">未マージ</th><th class="n">main より遅れ</th><th>最後の仕事</th><th class="n">日付</th></tr></thead>
      <tbody id="branches"></tbody>
    </table>
  </div>
  <div id="unmerged"></div>
</section>

<section>
  <div class="head">
    <h2>日ごとの手数</h2>
    <span class="note" id="srange"></span>
  </div>
  <div class="strip">
    <div class="bars" id="bars"></div>
    <div class="barlabels" id="barlabels"></div>
  </div>
</section>

<footer id="foot"></footer>
</div>

<script id="edo-data" type="application/json">__DATA__</script>
<script>
(function(){
"use strict";
var D = JSON.parse(document.getElementById('edo-data').textContent);

var CATS = {
  typology:{label:'類型',   color:'var(--ai)'},
  estate:  {label:'邸',     color:'var(--murasaki)'},
  parts:   {label:'部材',   color:'var(--cha)'},
  infra:   {label:'基盤',   color:'var(--matsu)'},
  rec:     {label:'記録',   color:'var(--odo)'},
  other:   {label:'その他', color:'var(--ink-3)'}
};
var esc = function(s){ return String(s).replace(/[&<>"]/g, function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); };

/* ── 要点 ── */
var live = D.claims.filter(function(c){ return c.beat <= 15; });
var unmTotal = D.branches.reduce(function(a,b){ return a + ((b.ahead>0 && !b.orphan && !b.head) ? b.ahead : 0); },0);
var unmBr = D.branches.filter(function(b){ return b.ahead>0 && !b.orphan && !b.head; }).length;
var oldBr = D.branches.filter(function(b){ return b.orphan; }).length;
var wtCount = D.branches.filter(function(b){ return b.wt; }).length;
var todayN = D.series[D.series.length-1].n;
var week = D.series.slice(-7).reduce(function(a,s){ return a+s.n; },0);
var vit = [
  {k:'普請中の車線', v:live.length, u:'／'+D.claims.length+' 席', n:'心拍 15 分以内', alert:false},
  {k:'main の未送り', v:D.ahead_origin, u:'commit', n:'origin/main へ push 待ち', alert:D.ahead_origin>0},
  {k:'枝', v:D.branches.length, u:'本', n:wtCount+' 本が worktree に開いている', alert:false},
  {k:'置き去りの仕事', v:unmTotal, u:'commit', n:unmBr+' 本の枝に未マージ', alert:unmTotal>0},
  {k:'掲示板', v:D.board.length, u:'件', n:'裁定待ち '+D.board.filter(function(b){return b.state==='awaiting-user';}).length+' 件', alert:false},
  {k:'この 7 日', v:week, u:'commit', n:'本日 '+todayN+' 件', alert:false}
];
document.getElementById('vitals').innerHTML = vit.map(function(o){
  return '<div class="vital'+(o.alert?' alert':'')+'"><div class="k">'+esc(o.k)+'</div>'+
    '<div class="v num">'+o.v+'<small>'+esc(o.u)+'</small></div><div class="n">'+esc(o.n)+'</div></div>';
}).join('');
document.getElementById('asof').textContent = '読み取り '+D.gen;

/* ── 車線 ── */
document.getElementById('lanes').innerHTML = D.claims.map(function(c){
  var isLive = c.beat <= 15;
  var tags = c.estate.map(function(e){ return '<span class="tag zone">'+esc(e)+'</span>'; })
    .concat(c.res.map(function(r){ return '<span class="tag res">'+esc(r)+' を占有</span>'; }))
    .concat(c.phase ? ['<span class="tag">'+esc(c.phase)+'</span>'] : []).join('');
  var files = c.files.slice(0,3).map(function(f){ return f.split('/').pop(); }).join(' / ');
  if (c.files.length>3) files += ' ほか'+(c.files.length-3);
  return '<div class="lane '+(isLive?'live':'idle')+'">'+
    '<div class="top"><span class="sid mono">'+esc(c.sid)+'</span>'+
    '<span class="beat num">心拍 '+c.beat.toFixed(1)+'分前</span></div>'+
    '<div class="note'+(c.note?'':' none')+'">'+esc(c.note || '(札なし — 何をしているか掲げていない)')+'</div>'+
    (tags?'<div class="tags">'+tags+'</div>':'')+
    (files?'<div class="files">'+esc(files)+'</div>':'')+'</div>';
}).join('');

/* ── 工程 ── */
var byEstate = {};
D.board.forEach(function(b){ byEstate[b.estate] = (byEstate[b.estate]||0)+1; });
document.getElementById('estates').innerHTML = D.estates.map(function(e){
  var fin = e.stage >= 5;
  var rail = D.stages.map(function(_,i){
    var cls = i+1 < e.stage ? 'done' : (i+1 === e.stage ? (fin?'fin':'now') : '');
    return '<span class="seg '+cls+'" title="'+esc(D.stages[i])+'"></span>';
  }).join('');
  var bad = /⛔|不合格|検め直し|未測|未検分/.test(e.gate) && !fin;
  if (e.stage === null) rail = '<span class="norail">指図なし・掲示板の担当のみ</span>';
  return '<div class="est">'+
    '<div class="nm">'+esc(e.name)+'<span>'+esc(e.kana)+'</span></div>'+
    '<div class="rail">'+rail+'</div>'+
    '<div class="gate '+(fin?'ok':(bad?'bad':''))+'"><b>'+esc(e.state)+(e.hint?'†':'')+'</b> ・ '+esc(e.gate)+
      '<em>'+esc(e.note)+'</em></div>'+
    '<div class="cnt"><b class="num">'+(byEstate[e.kana]||0)+'</b><br>件</div>'+
  '</div>';
}).join('');

/* ── 系図 ── */
var RH=26, LW=15, PADL=13;
var gw = D.lanes*LW + PADL*2;
var gbox = document.getElementById('graph');
gbox.style.setProperty('--gw', gw+'px');
var H = D.commits.length*RH;
var lx = function(l){ return PADL + l*LW; };
var ly = function(r){ return r*RH + RH/2; };
var laneCol = ['var(--ai)','var(--matsu)','var(--murasaki)','var(--cha)','var(--odo)','var(--shu)'];

var paths = D.edges.map(function(e){
  var x1=lx(e.fr), y1=ly(e.fy), x2=lx(e.to), y2=e.open ? H : ly(e.ty);
  var d = (x1===x2) ? ('M'+x1+' '+y1+'V'+y2)
        : ('M'+x1+' '+y1+'C'+x1+' '+((y1+y2)/2)+' '+x2+' '+((y1+y2)/2)+' '+x2+' '+y2);
  return '<path d="'+d+'" fill="none" stroke="'+laneCol[(e.open?e.fr:e.to)%laneCol.length]+'" '+
    'stroke-width="'+(e.merge?1.3:1.8)+'" stroke-opacity="'+(e.open?.35:(e.merge?.55:.8))+'"'+
    (e.open?' stroke-dasharray="3 3"':'')+'></path>';
}).join('');
var dots = D.commits.map(function(c,i){
  var x=lx(c.lane), y=ly(i), col=CATS[c.cat].color;
  var merge = c.p.length>1;
  return merge
    ? '<rect class="gd" data-i="'+i+'" x="'+(x-4.3)+'" y="'+(y-4.3)+'" width="8.6" height="8.6" '+
      'transform="rotate(45 '+x+' '+y+')" fill="var(--surface)" stroke="'+col+'" stroke-width="2"></rect>'
    : '<circle class="gd" data-i="'+i+'" cx="'+x+'" cy="'+y+'" r="3.6" fill="'+col+'" '+
      'stroke="var(--surface)" stroke-width="1.5"></circle>';
}).join('');

var wtBranches = {};
D.branches.forEach(function(b){ if (b.wt) wtBranches[b.name]=1; });
var lastDay=null, alt=false;
var rows = D.commits.map(function(c,i){
  var day = c.d.slice(0,10);
  if (day!==lastDay){ alt=!alt; lastDay=day; }
  var refs = c.refs.map(function(r){
    return '<span class="rf'+(wtBranches[r]?' wt':'')+'">'+esc(r)+'</span>'; }).join('');
  var tk = c.tickets.map(function(t){ return '<span class="tk">'+t+'</span>'; }).join('');
  var sub = c.sub.replace(/^\w+\(.+?\)\s*[:：]\s*/,'').replace(/\s*\(EDO-\d{4}[^)]*\)\s*$/,'');
  return '<div class="crow'+(alt?' alt':'')+'" data-cat="'+c.cat+'" data-i="'+i+'">'+
    '<span></span>'+
    '<span class="h mono">'+esc(c.s)+'</span>'+
    '<span class="sc" style="color:'+CATS[c.cat].color+'">'+esc(c.scope || CATS[c.cat].label)+'</span>'+
    '<span class="sj">'+refs+esc(sub)+tk+'</span>'+
    '<span class="tm mono">'+esc(c.d.slice(5))+'</span>'+
  '</div>';
}).join('');

gbox.innerHTML = '<svg width="'+gw+'" height="'+H+'" aria-hidden="true">'+paths+dots+'</svg>'+rows;
document.getElementById('grange').textContent =
  '直近 '+D.commits.length+' コミット('+D.commits[D.commits.length-1].d+' 〜 '+D.commits[0].d+')・'+D.lanes+' 車線';

/* 札で絞る */
var counts={}; D.commits.forEach(function(c){ counts[c.cat]=(counts[c.cat]||0)+1; });
var order = Object.keys(CATS).filter(function(k){ return counts[k]; });
var active = null;
document.getElementById('filters').innerHTML =
  '<button class="chip" id="chip-all" aria-pressed="true">すべて '+D.commits.length+'</button>' +
  order.map(function(k){
    return '<button class="chip" data-cat="'+k+'" aria-pressed="false">'+
      '<span class="dot" style="background:'+CATS[k].color+'"></span>'+CATS[k].label+' '+counts[k]+'</button>';
  }).join('');
function apply(){
  var rowsEl = gbox.querySelectorAll('.crow'), dotsEl = gbox.querySelectorAll('.gd');
  for (var i=0;i<rowsEl.length;i++){
    var on = !active || rowsEl[i].dataset.cat===active;
    rowsEl[i].classList.toggle('dim', !on);
    if (dotsEl[i]) dotsEl[i].setAttribute('opacity', on ? 1 : .22);
  }
  document.querySelectorAll('.chip').forEach(function(b){
    b.setAttribute('aria-pressed', String(b.dataset.cat ? b.dataset.cat===active : !active));
  });
}
document.getElementById('filters').addEventListener('click', function(ev){
  var b = ev.target.closest('.chip'); if(!b) return;
  active = (!b.dataset.cat || b.dataset.cat===active) ? null : b.dataset.cat;
  apply();
});

/* ── 枝 ── */
var order2 = D.branches.slice().sort(function(a,b){
  if (a.head!==b.head) return a.head?-1:1;
  var ua=(a.ahead>0&&!a.orphan), ub=(b.ahead>0&&!b.orphan);
  if (ua!==ub) return ua?-1:1;
  if (a.orphan!==b.orphan) return a.orphan?1:-1;
  return a.date<b.date?1:-1;
});
document.getElementById('branches').innerHTML = order2.map(function(b){
  var pills=[];
  if (b.head) pills.push('<span class="pill left">HEAD</span>');
  if (b.wt) pills.push('<span class="pill wt">作業場</span>');
  if (b.orphan) pills.push('<span class="pill old" title="main と共通の祖先が無い — 履歴を書き換える前(LFS 移行)の写し">別系統の履歴</span>');
  else if (b.ahead>0) pills.push('<span class="pill left">未マージ</span>');
  else if (!b.head) pills.push('<span class="pill merged">main に吸収済</span>');
  if (!b.orphan && b.behind>900) pills.push('<span class="pill old">古株</span>');
  return '<tr><td class="nm">'+esc(b.name)+'</td><td style="white-space:nowrap">'+pills.join(' ')+'</td>'+
    '<td class="n">'+(b.ahead||'—')+'</td><td class="n">'+(b.behind||'—')+'</td>'+
    '<td class="sub">'+esc(b.sub)+'</td><td class="n mono">'+esc(b.date)+'</td></tr>';
}).join('');
document.getElementById('unmerged').innerHTML = Object.keys(D.unmerged).map(function(k){
  var us = D.unmerged[k];
  return '<details class="unm"><summary><b>'+us.length+' commit</b> が <code>'+esc(k)+'</code> に置き去り</summary>'+
    '<div class="body">'+us.map(function(u){
      return '<div class="u"><span class="mono">'+esc(u.s)+' '+esc(u.d)+'</span><span class="t">'+esc(u.sub)+'</span></div>';
    }).join('')+'</div></details>';
}).join('');

/* ── 日ごと ── */
var mx = Math.max.apply(null, D.series.map(function(s){ return s.n; }));
document.getElementById('bars').innerHTML = D.series.map(function(s,i){
  var h = s.n ? Math.max(2, Math.round(s.n/mx*106)) : 0;
  var cls = s.n===0 ? 'zero' : (i===D.series.length-1 ? 'today' : (s.n>=mx*0.6 ? 'hot' : ''));
  return '<div class="bar '+cls+'" style="height:'+h+'px" title="'+s.d+' — '+s.n+' commit"></div>';
}).join('');
document.getElementById('barlabels').innerHTML = D.series.map(function(s,i){
  return '<span>'+((i%7===0) ? s.d.slice(5).replace('-','/') : '')+'</span>';
}).join('');
document.getElementById('srange').textContent =
  D.series[0].d+' 〜 '+D.series[D.series.length-1].d+'・最多 '+mx+' commit/日';

document.getElementById('foot').innerHTML =
  '読み取り元 — <code>git log --all --date-order</code>(直近 '+D.commits.length+' コミット)／'+
  '<code>git worktree list</code>／<code>Tools/Session/edo_session.py</code> の生きている claim／'+
  '<code>Tools/Sashizu/review_gate.py</code>・<code>kansei_gate.py</code>／'+
  '<code>Tools/Session/edo_board.py list</code>。<br>'+
  'この頁は '+D.gen+' 時点の写し。邸ごとの工程の段は CLAUDE.md「制作パイプライン」の①〜⑤に対応する。';
})();
</script>
"""


def render(data):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload)


def selftest():
    fake = [dict(h="c", p=["b"], d="", refs=[], sub="x", typ="", scope="", cat="other", tickets=[], lane=0),
            dict(h="b", p=["a", "z"], d="", refs=[], sub="m", typ="", scope="", cat="other", tickets=[], lane=0),
            dict(h="a", p=[], d="", refs=[], sub="r", typ="", scope="", cat="other", tickets=[], lane=0),
            dict(h="z", p=[], d="", refs=[], sub="s", typ="", scope="", cat="other", tickets=[], lane=0)]
    idx = {c["h"]: i for i, c in enumerate(fake)}
    n, edges = assign_lanes(fake, idx)
    assert n == 2 and fake[3]["lane"] == 1, (n, [c["lane"] for c in fake])   # merge の第2親は別の列
    assert sum(1 for e in edges if e["merge"]) == 1
    assert classify("fix(類型): 庭")[2] == "typology" and classify("docs: x")[2] == "rec"
    assert classify("feat(山王): 楼門")[2] == "estate" and classify("wip")[2] == "other"
    html = render(dict(commits=[], edges=[], lanes=1, branches=[], unmerged={}, ahead_origin=0, behind_origin=0,
                       series=[dict(d="2026-01-01", n=0)], claims=[], board=[], estates=[], stages=STAGES,
                       live_min=LIVE_MIN, gen="t", x="</script>"))
    assert "</script><" not in html.split('id="edo-data"', 1)[1].split("</script>", 1)[0]  # 値が script を閉じない
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description="作業状況の系図を HTML に刷る")
    ap.add_argument("--out")
    ap.add_argument("--commits", type=int, default=110)
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    data = collect(a.commits)
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return
    out = a.out or os.path.join(common_git_dir(), "edo-graph", "repo_graph.html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data))
    print("刷った: %s (%d commit・%d 車線・claim %d・掲示板 %d・邸 %d)" % (
        out, len(data["commits"]), data["lanes"], len(data["claims"]), len(data["board"]), len(data["estates"])))
    if a.open:
        webbrowser.open("file://" + os.path.abspath(out))


if __name__ == "__main__":
    main()
