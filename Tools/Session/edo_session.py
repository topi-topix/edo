#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""司令塔 — 同じリポジトリで複数の Claude Code セッションが同時に動くための調停役。

**なぜ要るか**: 2026-08-24 に、松平・岡部を作業していたセッションが `git add` を広く打ち、
**別のセッションが編集中だった山王の指図を巻き込んでコミットした**。作業自体は失われなかったが、
履歴から山王の改訂が追えなくなった。加えてこのリポジトリは Unity の実体が1つしかなく、
地形の編集は Undo の外にあるので、2つのセッションが同時に触ると復旧できない。

**考え方**
- **申告は自動**。書いた時点でそのパスを名乗ったことにする(`claim` を打ち忘れても効く)。
- **止めるのは他人の領分に踏み込むときだけ。** 自分の claim なら素通り。
- **Unity は排他**。`unity` 資源を取っていないセッションは Unity MCP を触れない。
- **git は広い staging を禁じる。** `git add -A` / `git commit -a` の類は常に止める。

登録簿は `.claude/locks/*.json`(machine-local・gitignore)。
プロセスが消えたか、`--ttl` 分だけ心拍が途絶えた claim は死んだものとして無視する。
"""
import argparse, fnmatch, json, os, re, subprocess, sys, time

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip() or os.getcwd()
LOCKS = os.path.join(ROOT, ".claude", "locks")
TTL_MIN = 45.0
RESOURCES = ("unity", "terrain", "git-index")

# ── 常に止める git の打ち方(他人の作業を巻き込む/破壊する)
# ⚠ **コマンド位置に現れたものだけを見る。**
#   文字列の中の例示や説明文まで拾うと、
#   ドキュメントを書いただけで作業が止まる
#   (2026-08-24 に自分で踏んだ — このフックを直すコマンド自体が止められた)。
CMDPOS = r"(?:^|[;&|(\n]\s*)"

BANNED = [
    (CMDPOS + r"git\s+add\s+(-A\b|--all\b|\.(\s|$))",
     "git add -A / git add . は**他のセッションの編集中のファイルを巻き込む**。"
     "`git add <パス>...` でパスを明示すること(2026-08-24 に実際に事故が起きた)"),
    (CMDPOS + r"git\s+commit\b[^|;&]*(\s-\w*a\w*\b|--all\b)",
     "git commit -a は追跡中の全変更を巻き込む。`git commit -- <パス>...` か "
     "`Tools/Session/edo_session.py commit <パス>...` を使うこと"),
    (CMDPOS + r"git\s+(checkout|restore)\s+(\.|--\s+\.)(\s|$)",
     "作業ツリー全体の破棄は他のセッションの未保存の作業を消す"),
    (CMDPOS + r"git\s+reset\s+--hard\b", "reset --hard は他のセッションの作業を消す"),
    (CMDPOS + r"git\s+clean\b\s+[^|;&]*-\w*f", "git clean -f は他のセッションの未追跡ファイルを消す"),
    (CMDPOS + r"git\s+stash\b(?!\s+list)", "git stash は他のセッションの編集を巻き上げる"),
    (CMDPOS + r"git\s+push\b[^|;&]*(--force\b|-f\b)", "強制 push は他のセッションが積んだコミットを消す"),
    (CMDPOS + r"git\s+rebase\b", "共有ワークツリーでの rebase は他のセッションの HEAD を動かす"),
]


def now():
    return time.time()


def sid(default=None):
    return (os.environ.get("EDO_SESSION_ID") or default
            or ("pid-%s" % os.getppid()))


def load_all(ttl=TTL_MIN):
    """生きている claim だけを返す。死んだものは掃除する。"""
    out = []
    if not os.path.isdir(LOCKS):
        return out
    for fn in sorted(os.listdir(LOCKS)):
        if not fn.endswith(".json"):
            continue
        fp = os.path.join(LOCKS, fn)
        try:
            c = json.load(open(fp, encoding="utf-8"))
        except Exception:
            os.remove(fp)
            continue
        # ⚠ **生存は心拍だけで判定する。** pid を使ってはならない — フックから呼ばれる
        #   スクリプトの親はその都度のシェルで、セッションの寿命と無関係(2026-08-24 に
        #   これで claim が即死し、事故の再現テストが素通りした)。pid は表示用。
        if (now() - c.get("heartbeat", 0)) / 60.0 > ttl:
            try:
                os.remove(fp)
            except OSError:
                pass
            continue
        out.append(c)
    return out


def mine(s):
    fp = os.path.join(LOCKS, "%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "_", s))
    if os.path.exists(fp):
        try:
            return json.load(open(fp, encoding="utf-8")), fp
        except Exception:
            pass
    return {"session": s, "pid": os.getppid(), "started": now(), "heartbeat": now(),
            "paths": [], "resources": [], "note": ""}, fp


def save(c, fp):
    os.makedirs(LOCKS, exist_ok=True)
    c["heartbeat"] = now()
    json.dump(c, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def rel(p):
    p = os.path.abspath(os.path.expanduser(p))
    return os.path.relpath(p, ROOT) if p.startswith(ROOT) else p


def domain(p):
    """指図・ビルダーは**屋敷の名前**を単位にまとめる(docs と Tools が対で動くので)。"""
    r = rel(p).replace(os.sep, "/")
    m = re.match(r"docs/Sashizu/([a-z0-9]+)_", r) or \
        re.match(r"Tools/Sashizu/build_([a-z0-9]+)_sashizu\.py", r)
    return "sashizu:" + m.group(1) if m else None


def covers(claim, path):
    r = rel(path).replace(os.sep, "/")
    d = domain(path)
    for g in claim.get("paths", []):
        if g == r or fnmatch.fnmatch(r, g) or (d and g == d):
            return g
    return None


def holders(path, me, ttl=TTL_MIN):
    out = []
    for c in load_all(ttl):
        if c["session"] == me:
            continue
        g = covers(c, path)
        if g:
            out.append((c, g))
    return out


def touch(me, paths=(), resources=()):
    c, fp = mine(me)
    for p in paths:
        k = domain(p) or rel(p).replace(os.sep, "/")
        if k not in c["paths"]:
            c["paths"].append(k)
    for r in resources:
        if r not in c["resources"]:
            c["resources"].append(r)
    save(c, fp)
    return c


# ────────────────────────────────────────────── サブコマンド
def cmd_status(a):
    cs = load_all(a.ttl)
    if not cs:
        print("司令塔: 生きている claim は無し")
        return 0
    me = sid(a.session)
    print("司令塔 — 生きている claim %d 件(TTL %.0f 分)" % (len(cs), a.ttl))
    for c in cs:
        age = (now() - c["heartbeat"]) / 60.0
        print("  %s %-22s pid%-7s 心拍%4.1f分前" % (
            "▶" if c["session"] == me else " ", c["session"][:22], c.get("pid"), age))
        if c.get("note"):
            print("      %s" % c["note"])
        if c.get("resources"):
            print("      資源: %s" % ", ".join(c["resources"]))
        for g in c["paths"]:
            print("      %s" % g)
    return 0


def cmd_claim(a):
    me = sid(a.session)
    c, fp = mine(me)
    for p in a.paths:
        k = p if (p.startswith("sashizu:") or "*" in p) else (domain(p) or rel(p).replace(os.sep, "/"))
        if k not in c["paths"]:
            c["paths"].append(k)
    for r in a.resources:
        if r not in RESOURCES:
            print("不明な資源: %s(%s のいずれか)" % (r, "/".join(RESOURCES)), file=sys.stderr)
            return 1
        h = [x for x in load_all(a.ttl) if x["session"] != me and r in x.get("resources", [])]
        if h:
            print("⛔ 資源 %s は %s が押さえている。先に解放してもらうこと" % (r, h[0]["session"]),
                  file=sys.stderr)
            return 2
        if r not in c["resources"]:
            c["resources"].append(r)
    if a.note:
        c["note"] = a.note
    c["pid"] = os.getppid()
    save(c, fp)
    print("claim: %s → %s %s" % (me, c["paths"], c["resources"]))
    return 0


def cmd_release(a):
    me = sid(a.session)
    c, fp = mine(me)
    if not a.paths and not a.resources:
        if os.path.exists(fp):
            os.remove(fp)
        print("release: %s の claim をすべて解いた" % me)
        return 0
    for p in a.paths:
        k = p if (p.startswith("sashizu:") or "*" in p) else (domain(p) or rel(p).replace(os.sep, "/"))
        if k in c["paths"]:
            c["paths"].remove(k)
    for r in a.resources:
        if r in c["resources"]:
            c["resources"].remove(r)
    save(c, fp)
    print("release: 残り %s %s" % (c["paths"], c["resources"]))
    return 0


def _deny(msg):
    print(msg, file=sys.stderr)
    return 2


def cmd_check_write(a):
    me = sid(a.session)
    p = a.path
    if not p:
        return 0
    r = rel(p).replace(os.sep, "/")
    if r.startswith(".claude/locks"):
        return 0
    hs = holders(p, me, a.ttl)
    if hs:
        c, g = hs[0]
        return _deny(
            "⛔ 司令塔: `%s` は**別のセッション %s** が押さえている(claim `%s`／心拍 %.0f 分前)。\n"
            "   %s\n"
            "   同じファイルを同時に書くと片方の編集が消える。\n"
            "   → 待つか、そのセッションに `Tools/Session/edo_session.py release %s` を頼むこと。\n"
            "   → 引き継ぐと決めたなら `Tools/Session/edo_session.py steal %s` で奪える(理由を残す)。"
            % (r, c["session"], g, (now() - c["heartbeat"]) / 60.0, c.get("note", ""), g, g))
    touch(me, paths=[p])
    return 0


def cmd_check_bash(a):
    me = sid(a.session)
    cmd = a.command or ""
    for pat, why in BANNED:
        if re.search(pat, cmd):
            return _deny("⛔ 司令塔: この git の打ち方は共有ワークツリーでは禁止。\n   %s" % why)
    m = re.search(CMDPOS + r"git\s+commit\b", cmd)
    if m and not re.search(CMDPOS + r"git\s+commit\b[^|;&]*(--amend|-C\b|--continue)", cmd):
        staged = subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--name-only"],
                                capture_output=True, text=True).stdout.split()
        bad = []
        for f in staged:
            hs = holders(os.path.join(ROOT, f), me, a.ttl)
            if hs:
                bad.append((f, hs[0][0]["session"]))
        if bad:
            return _deny(
                "⛔ 司令塔: staging に**別のセッションが押さえているファイル**が入っている。\n"
                + "".join("   %s ← %s\n" % (f, s) for f, s in bad[:8])
                + "   このままコミットすると相手の作業を巻き込む(2026-08-24 の事故と同じ)。\n"
                  "   → `git restore --staged <パス>` で外してからコミットすること。")
    touch(me)
    return 0


def cmd_check_unity(a):
    me = sid(a.session)
    cs = load_all(a.ttl)
    hold = [c for c in cs if "unity" in c.get("resources", [])]
    if not hold:
        touch(me, resources=["unity"])
        return 0
    if hold[0]["session"] == me:
        touch(me)
        return 0
    return _deny(
        "⛔ 司令塔: Unity は**セッション %s** が使用中(心拍 %.0f 分前)。\n   %s\n"
        "   Unity の実体は1つで、シーン・プレハブ・地形を共有している。"
        "**地形の編集は Undo の外**なので、同時に触ると復旧できない。\n"
        "   → 終わるのを待つか、`Tools/Session/edo_session.py status` で状況を見ること。"
        % (hold[0]["session"], (now() - hold[0]["heartbeat"]) / 60.0, hold[0].get("note", "")))


def cmd_steal(a):
    me = sid(a.session)
    n = 0
    for c in load_all(a.ttl):
        if c["session"] == me:
            continue
        ch = False
        for k in list(c["paths"]):
            if k in a.what:
                c["paths"].remove(k); ch = True
        for r in list(c.get("resources", [])):
            if r in a.what:
                c["resources"].remove(r); ch = True
        if ch:
            n += 1
            fp = os.path.join(LOCKS, "%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "_", c["session"]))
            save(c, fp)
    touch(me, paths=[w for w in a.what if w not in RESOURCES],
          resources=[w for w in a.what if w in RESOURCES])
    print("steal: %s を %d 件のセッションから引き取った(理由: %s)" % (a.what, n, a.reason or "—"))
    return 0


def cmd_commit(a):
    me = sid(a.session)
    if not a.paths:
        print("コミットするパスを明示すること", file=sys.stderr)
        return 1
    bad = [(p, holders(p, me, a.ttl)[0][0]["session"]) for p in a.paths if holders(p, me, a.ttl)]
    if bad:
        print("⛔ 他のセッションが押さえているパスが混ざっている:\n"
              + "".join("   %s ← %s\n" % b for b in bad), file=sys.stderr)
        return 2
    subprocess.run(["git", "-C", ROOT, "reset", "-q"], check=False)
    subprocess.run(["git", "-C", ROOT, "add", "--"] + list(a.paths), check=True)
    r = subprocess.run(["git", "-C", ROOT, "commit", "-m", a.message], check=False)
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description="司令塔 — 並行セッションの調停")
    ap.add_argument("--session"); ap.add_argument("--ttl", type=float, default=TTL_MIN)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("claim"); p.add_argument("paths", nargs="*")
    p.add_argument("--resources", nargs="*", default=[]); p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_claim)
    p = sub.add_parser("release"); p.add_argument("paths", nargs="*")
    p.add_argument("--resources", nargs="*", default=[]); p.set_defaults(fn=cmd_release)
    p = sub.add_parser("check-write"); p.add_argument("path"); p.set_defaults(fn=cmd_check_write)
    p = sub.add_parser("check-bash"); p.add_argument("command"); p.set_defaults(fn=cmd_check_bash)
    sub.add_parser("check-unity").set_defaults(fn=cmd_check_unity)
    p = sub.add_parser("steal"); p.add_argument("what", nargs="+")
    p.add_argument("--reason", default=""); p.set_defaults(fn=cmd_steal)
    p = sub.add_parser("commit"); p.add_argument("paths", nargs="+")
    p.add_argument("-m", "--message", required=True); p.set_defaults(fn=cmd_commit)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
