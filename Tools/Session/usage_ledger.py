#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""利用実績の台帳 — どの役・スキル・参照が実際に使われたかを transcript から取る(EDO-0221・手入れの第2期)。

【なぜ要るか】道具改め(config_doctor)は「参照が切れていないか」は見るが、**誰にも使われない設定**は見ない。
使われない役・スキル・参照は、読まれもしないのに予算(行数・description・索引)を食い、規則を直すたびに
直す先が増える。手で数えると腐るので、transcript の tool_use から機械で拾う。

【何を拾うか】主セッション・worktree のセッション・サブエージェントの transcript(`*.jsonl`)から:
  role:<名>      Agent(subagent_type)の呼出
  skill:<名>     Skill の呼出 / スラッシュコマンド `<command-name>` / SKILL.md を読んだ
  path:<相対>    スキルの参照(`<スキル>/references/x.md`)と `docs/x.md` を tool の入力に含めた(Read・Bash・Grep)
  base:<x.md>    `references/x.md`(入れ子は `references/d/x.md`)の裸の言及(スキル名を省いた読み方の受け皿)
値は [回数, 最後の時刻(epoch)]。

【台帳】`<state>/usage.json`(既定は `.git/edo-teire/usage.json`。machine-local)。transcript 1 本ごとに
(size, mtime)と寄与を持ち、**変わった物だけ**読み直す(全体は数 GB。初回だけ数十秒、以後は差分)。
`coverage`(最古の時刻)を持つので、記録が 30 日ぶんに満たない間は「呼ばれていない」と言わない。

【使い方】
    python3 Tools/Session/usage_ledger.py                 # 台帳を更新して要約を出す
    python3 Tools/Session/usage_ledger.py --selftest

⚠ 読むだけ(台帳以外は書かない)。判定(30 日・60 日)は config_doctor の U1/U2 が持つ。
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HOME = os.path.expanduser("~")
SKILL_PATH = re.compile(r"(?:Tools/Skills|\.claude/skills)/([\w.-]+)/((?:[\w.-]+/)*[\w.-]+\.md)")
DOCS_PATH = re.compile(r"(?<![\w.-])docs/((?:[\w.-]+/)*[\w.-]+\.md)")
REF_BASE = re.compile(r"references/((?:[\w.-]+/)*[\w.-]+\.md)")
CMD_NAME = re.compile(r"<command-name>/?([\w:-]+)</command-name>")


def _git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def main_root(start):
    d = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return os.path.dirname(d) if d else start


def project_dirs(root):
    """main と、その worktree の transcript の置き場。⚠ worktree のセッションは別のディレクトリに書く
    (`-<repo>--claude-worktrees-<名>`)。main だけ読むと、worktree でしか呼ばれない役が「未使用」に見える。"""
    base = os.path.join(HOME, ".claude", "projects", "-" + root.strip("/").replace("/", "-"))
    out = [base] if os.path.isdir(base) else []
    out += sorted(d for d in glob.glob(base + "--claude-worktrees-*") if os.path.isdir(d))
    return out


def transcripts(dirs):
    fps = []
    for d in dirs:
        fps += glob.glob(os.path.join(d, "*.jsonl"))
        fps += glob.glob(os.path.join(d, "*", "subagents", "*.jsonl"))
    return sorted(fps)


def _epoch(ts):
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _strings(inp):
    return [v for v in inp.values() if isinstance(v, str)] if isinstance(inp, dict) else []


def _hit(hits, key, t):
    h = hits.setdefault(key, [0, 0])
    h[0] += 1
    h[1] = max(h[1], t or 0)


def _paths(text, hits, t):
    for m in SKILL_PATH.finditer(text):
        skill, rest = m.group(1), m.group(2)
        if rest == "SKILL.md":
            _hit(hits, "skill:" + skill, t)
        else:
            _hit(hits, "path:%s/%s" % (skill, rest), t)
    for m in DOCS_PATH.finditer(text):
        _hit(hits, "path:docs/" + m.group(1), t)
    for m in REF_BASE.finditer(text):
        _hit(hits, "base:" + m.group(1), t)


def scan_file(fp):
    """→ (寄与 {鍵: [回数, 最後]}, 最古の時刻)。tool_use と、ユーザー発話のスラッシュコマンドだけを見る。"""
    hits, first = {}, None
    with open(fp, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            hot = '"tool_use"' in line
            if not hot and "<command-name>" not in line:
                if first is None and '"timestamp"' in line:
                    m = re.search(r'"timestamp":\s*"([^"]+)"', line)
                    first = _epoch(m.group(1)) if m else None
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            t = _epoch(e.get("timestamp") or "")
            if t and (first is None or t < first):
                first = t
            content = (e.get("message") or {}).get("content")
            if isinstance(content, str):
                for m in CMD_NAME.finditer(content):
                    _hit(hits, "skill:" + m.group(1), t)
                continue
            for x in content if isinstance(content, list) else []:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "text":
                    for m in CMD_NAME.finditer(x.get("text") or ""):
                        _hit(hits, "skill:" + m.group(1), t)
                    continue
                if x.get("type") != "tool_use":
                    continue
                name, inp = x.get("name"), x.get("input") or {}
                if name in ("Agent", "Task") and inp.get("subagent_type"):
                    _hit(hits, "role:" + inp["subagent_type"], t)
                elif name == "Skill" and inp.get("skill"):
                    _hit(hits, "skill:" + inp["skill"], t)
                for s in _strings(inp):
                    _paths(s, hits, t)
    return hits, first


VERSION = 2     # 拾い方を変えたら上げる(古い台帳は捨てて読み直す)


def load(state):
    try:
        led = json.load(open(os.path.join(state, "usage.json"), encoding="utf-8"))
        return led if led.get("v") == VERSION else None
    except Exception:
        return None


def _save(state, led):
    os.makedirs(state, exist_ok=True)
    tmp = os.path.join(state, "usage.json.tmp")
    json.dump(led, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, os.path.join(state, "usage.json"))


def scan(state, dirs):
    """差分だけ読み直して台帳を保存し返す。消えた transcript の寄与は**残す**(Claude Code は古い物を消しうる。
    消えたから「使われなかった」に戻ってはならない)。"""
    led = load(state) or {"v": VERSION, "files": {}}
    files = led["files"]
    for fp in transcripts(dirs):
        try:
            st = os.stat(fp)
        except OSError:
            continue
        old = files.get(fp)
        if old and old["size"] == st.st_size and old["mtime"] == int(st.st_mtime):
            continue
        try:
            hits, first = scan_file(fp)
        except Exception:
            continue
        files[fp] = {"size": st.st_size, "mtime": int(st.st_mtime), "first": first, "hits": hits}
    led["t"] = time.time()
    _save(state, led)
    return led


def summarize(led):
    """→ ({鍵: (回数, 最後)}, coverage_epoch|None)。"""
    tot, first = {}, None
    for f in (led or {}).get("files", {}).values():
        if f.get("first") and (first is None or f["first"] < first):
            first = f["first"]
        for k, (n, t) in f.get("hits", {}).items():
            a = tot.get(k, (0, 0))
            tot[k] = (a[0] + n, max(a[1], t))
    return tot, first


def _days(t, now):
    return int((now - t) / 86400)


def main(argv=None):
    ap = argparse.ArgumentParser(description="利用実績の台帳")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--root")
    ap.add_argument("--state-dir")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    root = os.path.abspath(a.root) if a.root else main_root(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    gd = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    state = os.path.abspath(a.state_dir) if a.state_dir else os.path.join(gd or root, "edo-teire")
    t0 = time.time()
    led = scan(state, project_dirs(root))
    tot, first = summarize(led)
    now = time.time()
    print("台帳 %s(transcript %d 本・%.0f 秒・記録は %s 日前から)" %
          (os.path.join(state, "usage.json"), len(led["files"]), now - t0,
           _days(first, now) if first else "?"))
    for kind in ("role", "skill"):
        rows = sorted(((k[len(kind) + 1:], v) for k, v in tot.items() if k.startswith(kind + ":")),
                      key=lambda kv: -kv[1][1])
        print("\n■ %s(%d)" % (kind, len(rows)))
        for name, (n, t) in rows:
            print("  %-28s %5d 回 / 最後 %d 日前" % (name, n, _days(t, now)))
    return 0


# ── 自己検査 ─────────────────────────────────────────────────────────────
def _line(kind, name, inp, ts):
    return json.dumps({"type": "assistant", "timestamp": ts, "message": {"content": [
        {"type": "tool_use", "id": "x", "name": name, "input": inp}]}}, ensure_ascii=False)


def selftest():
    """⛔ 落ちたら**この道具の拾いが死んでいる**(0 件は合格でなく「拾えていない」かもしれない)。"""
    ng = 0
    base = tempfile.mkdtemp(prefix="usage-")
    try:
        d = os.path.join(base, "p")
        os.makedirs(os.path.join(d, "s1", "subagents"))
        ts = lambda days: (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        main_fp = os.path.join(d, "s1.jsonl")
        with open(main_fp, "w", encoding="utf-8") as fh:
            fh.write(_line("a", "Agent", {"subagent_type": "edo-kenzu"}, ts(3)) + "\n")
            fh.write(_line("a", "Skill", {"skill": "unity-buke-yashiki"}, ts(2)) + "\n")
            fh.write(_line("a", "Read", {"file_path": "/x/Tools/Skills/unity-buke-yashiki/references/sashizu.md"}, ts(2)) + "\n")
            fh.write(_line("a", "Bash", {"command": "sed -n 1,5p docs/teire.md && cat references/oki.md"}, ts(1)) + "\n")
            fh.write(_line("a", "Read", {"file_path": "/h/.claude/skills/kenzu-x/SKILL.md"}, ts(1)) + "\n")
            fh.write(json.dumps({"type": "user", "timestamp": ts(1), "message": {"content":
                     "<command-name>/nikki</command-name>"}}) + "\n")
            fh.write("こわれた行\n")
        sub = os.path.join(d, "s1", "subagents", "agent-1.jsonl")
        with open(sub, "w", encoding="utf-8") as fh:
            fh.write(_line("a", "Read", {"file_path": "docs/oki-kata.md"}, ts(60)) + "\n")
        led = scan(os.path.join(base, "st"), [d])
        tot, first = summarize(led)
        want = {"role:edo-kenzu": 1, "skill:unity-buke-yashiki": 1, "skill:kenzu-x": 1, "skill:nikki": 1,
                "path:unity-buke-yashiki/references/sashizu.md": 1, "base:sashizu.md": 1,
                "path:docs/teire.md": 1, "base:oki.md": 1, "path:docs/oki-kata.md": 1}
        for k, n in want.items():
            if tot.get(k, (0,))[0] != n:
                print("⛔ 拾えていない: %s(期待 %d・実際 %s)" % (k, n, tot.get(k)))
                ng += 1
        if not first or _days(first, time.time()) < 59:
            print("⛔ coverage(最古)が subagent の 60 日前を拾っていない: %s" % first)
            ng += 1
        # 差分: 変わらなければ読み直さない・増えたら読み直す・消えても寄与は残る
        led2 = scan(os.path.join(base, "st"), [d])
        if led2["files"][main_fp] != led["files"][main_fp]:
            print("⛔ 変わっていない transcript を読み直して結果が変わった")
            ng += 1
        with open(main_fp, "a", encoding="utf-8") as fh:
            fh.write(_line("a", "Agent", {"subagent_type": "edo-kenzu"}, ts(0)) + "\n")
        os.utime(main_fp, (time.time() + 5, time.time() + 5))
        tot2, _ = summarize(scan(os.path.join(base, "st"), [d]))
        if tot2.get("role:edo-kenzu", (0,))[0] != 2:
            print("⛔ 増えた transcript を読み直していない(edo-kenzu=%s)" % (tot2.get("role:edo-kenzu"),))
            ng += 1
        os.remove(sub)
        tot3, _ = summarize(scan(os.path.join(base, "st"), [d]))
        if "path:docs/oki-kata.md" not in tot3:
            print("⛔ transcript が消えたら寄与も消えた(古い物を消されて「使われなかった」に戻る)")
            ng += 1
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)
    print("⛔ 自己検査 %d 件失敗" % ng if ng else "⭕ 自己検査 全通 — role / skill / path / base / コマンド / 差分 / 残存")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
