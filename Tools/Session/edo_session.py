#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""門番 — 同じリポジトリで複数の Claude Code セッションが同時に動くための調停役。

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
import argparse, fnmatch, io, json, os, re, subprocess, sys, time

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip() or os.getcwd()


def _common_git_dir():
    """全 worktree が共有する .git のパス。⚠ 登録簿はここに置く —
    worktree ごとに `.claude/locks` を持つと、隣の worktree の claim が見えない。"""
    r = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                       capture_output=True, text=True, cwd=ROOT)
    d = r.stdout.strip()
    return d if d else os.path.join(ROOT, ".git")


LOCKS = os.path.join(_common_git_dir(), "edo-locks")
TTL_MIN = 45.0
RESOURCES = ("unity", "terrain", "git-index", "assets")
# ⚠ フック(.claude/hooks/edo_guard.py)が session_id を切り詰める長さと**必ず一致させる**。
SID_LEN = 12

# ⚠ **心拍では「作業が終わったか」を判定できない。**
#   心拍は Write/Edit/Bash でも更新されるので、Unity を握ったまま別の作業(指図の推敲など)を
#   続けているセッションの claim は**永久に生き続ける**。TTL を縮めても解けない。
#   2026-08-30 ユーザー指摘「作業が終わっているのに unity をつかみ続けて、他のセッションが
#   さわれなくなる」。→ **資源ごとの最終使用時刻を心拍と別に持ち**、一定時間触られていない
#   資源は空きとみなす(掴んだセッションが生きていても明け渡す)。
IDLE_MIN = {"unity": 20.0, "terrain": 20.0, "assets": 30.0, "git-index": 10.0}


def res_idle(c, r):
    """資源 r を最後に使ってからの経過(分)。記録が無い旧 claim は心拍で代用する。"""
    t = (c.get("used") or {}).get(r)
    return (now() - (t if t else c.get("heartbeat", 0))) / 60.0


def res_stale(c, r):
    """資源 r は放置されているか(掴んだセッションが生きていても明け渡す)。"""
    return res_idle(c, r) >= IDLE_MIN.get(r, 30.0)


# ────────────────────────────── 待ち行列(2026-08-30 ユーザー指示)
#   「つかみたい人がいたら待ち行列を作らせて、誰かが終わったら次の人に連絡して掴めるように」
#   ⛔ 早い者勝ちにしない。空いた瞬間に別のセッションが割り込むと、待っていた側が延々待つ。
#   空いたら**先頭の1名にだけ RESERVE_MIN 分の予約**を出し、その間は他が取れない。
# ⛔ **LOCKS の中に置いてはならない。** load_all は LOCKS 内の *.json をすべて claim とみなし、
#   heartbeat の無いファイルを「死んだ claim」として **削除する**。待ち行列を中に置くと、
#   status を打つたびに行列が消え、全員が永遠に「1番目」になる(2026-08-30 の検査で踏んだ)。
QUEUE = os.path.join(os.path.dirname(LOCKS), "edo-queue.json")
RESERVE_MIN = 15.0


def q_load():
    try:
        q = json.load(open(QUEUE, encoding="utf-8"))
    except Exception:
        return {}
    live = {c["session"] for c in load_all()}
    out = {}
    for r, ws in q.items():
        # 死んだセッションの待ちは落とす。予約が切れたものも待ちに戻す
        keep = [w for w in ws if w["session"] in live]
        for w in keep:
            if w.get("reserved") and (now() - w["reserved"]) / 60.0 > RESERVE_MIN:
                w.pop("reserved", None)
        if keep:
            out[r] = keep
    return out


def q_save(q):
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def q_enqueue(r, me, note=""):
    """待ち行列に並ぶ(既に並んでいれば位置はそのまま)。戻り値: 1始まりの順番。"""
    # ⚠ 待ち人にも claim(=心拍)が要る。無いと q_load の生存判定で自分が即座に落ち、
    #   何度並んでも「1番目」に戻り続ける(2026-08-30 の検査で実際に踏んだ)。
    touch(me)
    q = q_load()
    ws = q.setdefault(r, [])
    for i, w in enumerate(ws):
        if w["session"] == me:
            return i + 1
    ws.append({"session": me, "since": now(), "note": note})
    q_save(q)
    return len(ws)


def q_drop(r, me):
    q = q_load()
    ws = q.get(r, [])
    q[r] = [w for w in ws if w["session"] != me]
    if not q[r]:
        q.pop(r, None)
    q_save(q)


def q_head(r):
    return (q_load().get(r) or [None])[0]


def q_reserve(r):
    """資源が空いたので先頭に予約を出す。戻り値: 予約した待ち人 or None。"""
    q = q_load()
    ws = q.get(r) or []
    if not ws:
        return None
    ws[0]["reserved"] = now()
    q_save(q)
    return ws[0]


def q_may_take(r, me):
    """me はいま r を取ってよいか。予約が他人に出ていれば取れない。"""
    h = q_head(r)
    if h and h.get("reserved") and h["session"] != me:
        return False, h
    return True, h

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


def sid(default=None, strict=True):
    """このセッションの識別子。

    ⚠ **フック経由と Bash 直叩きで別人になってはならない。** フックは session_id を
    EDO_SESSION_ID で渡すが、Bash から直接叩くとそれが無い。無いときは
    **同じ作業ディレクトリの生きた claim を引き継ぐ**(指図は worktree ごとに cwd が
    分かれ、Unity はメインに1つなので実用上は一意)。
    """
    e = os.environ.get("EDO_SESSION_ID") or default
    if e:
        # ⚠ **必ず切り詰める。** フック(edo_guard.py)は session_id を [:12] にして渡すので、
        #   ここで切らないと「フル UUID を渡した自分」が別人になり、自分の claim を他人の
        #   ものと判定して弾かれる(2026-08-30 に山王が踏んだ)。松平は短縮とフルで
        #   claim が二重に立っていた。
        return e[:SID_LEN]
    here = os.path.realpath(os.getcwd())
    same = [c for c in load_all() if os.path.realpath(c.get("cwd", "")) == here]
    # ⛔ **曖昧なら推測しない(EDO-0044)。** 「同じ cwd の最新の心拍」を引き継ぐ実装は、
    #   全セッションがメインのチェックアウトを共有すると**直前に動いた誰か**を指す。
    #   2026-08-30、これで土井の claim が山王の記録へ入り、松平の note が土井に上書きされ、
    #   作事奉行の steal が外堀の記録を書き換えた。**取り違えたまま黙って進むより止める。**
    if len(same) > 1:
        if not strict:
            return None      # 読むだけの照会(status)は身元不明でも通す。▶ が出ないだけ
        sys.exit(
            "⛔ 門番: 自分が誰か決められない — 同じ作業ディレクトリに生きた claim が %d 件ある。\n"
            "   %s\n"
            "   → **`EDO_SESSION_ID=<短縮ID>` を付けて叩くこと。**短縮ID は `status` の ▶ 行に出る\n"
            "     %d 文字の識別子(例 a154144d-ccb)。フル UUID を渡しても内部で切り詰めるので可。\n"
            "   ⚠ 推測で他人の claim に書き込むと、note も資源も静かに壊れる(EDO-0044)。"
            % (len(same), ", ".join(c["session"] for c in same), SID_LEN))
    if same:
        return same[0]["session"]
    return "pid-%s" % os.getppid()


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
    return {"session": s, "pid": os.getppid(), "cwd": os.getcwd(),
            "started": now(), "heartbeat": now(),
            "paths": [], "resources": [], "note": ""}, fp


def save(c, fp):
    os.makedirs(LOCKS, exist_ok=True)
    c["heartbeat"] = now()
    c.setdefault("cwd", os.getcwd())
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
        # ⚠ 心拍と別に**その資源を使った時刻**を残す。これが無いと放置を検出できない
        c.setdefault("used", {})[r] = now()
    save(c, fp)
    return c


def _force_release(session, resources):
    """他セッションの claim から資源だけを外す(放置の引き取り用)。"""
    fp = os.path.join(LOCKS, "%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "_", session))
    try:
        c = json.load(open(fp, encoding="utf-8"))
    except Exception:
        return
    for r in resources:
        if r in c.get("resources", []):
            c["resources"].remove(r)
        (c.get("used") or {}).pop(r, None)
    json.dump(c, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ────────────────────────────────────────────── サブコマンド
def cmd_status(a):
    cs = load_all(a.ttl)
    if not cs:
        print("門番: 生きている claim は無し")
        return 0
    me = sid(a.session, strict=False)
    print("門番 — 生きている claim %d 件(TTL %.0f 分)" % (len(cs), a.ttl))
    for c in cs:
        age = (now() - c["heartbeat"]) / 60.0
        print("  %s %-22s pid%-7s 心拍%4.1f分前" % (
            "▶" if c["session"] == me else " ", c["session"][:22], c.get("pid"), age))
        if c.get("note"):
            print("      %s" % c["note"])
        if c.get("resources"):
            rs = []
            for r in c["resources"]:
                idle = res_idle(c, r)
                rs.append("%s(最終使用 %.0f分前%s)" % (
                    r, idle, " ⚠放置" if res_stale(c, r) else ""))
            print("      資源: %s" % ", ".join(rs))
        for g in c["paths"]:
            print("      %s" % g)
    q = q_load()
    if q:
        print("待ち行列:")
        for r, ws in q.items():
            for i, w in enumerate(ws):
                print("  %s %s %d番 %s(%.0f分待ち)%s" % (
                    "▶" if w["session"] == me else " ", r, i + 1, w["session"][:22],
                    (now() - w["since"]) / 60.0,
                    " ⭐予約中(残り %.0f分)" % (RESERVE_MIN - (now() - w["reserved"]) / 60.0)
                    if w.get("reserved") else ""))
    return 0


def cmd_wait(a):
    me = sid(a.session)
    for r in a.resources:
        if r not in RESOURCES:
            print("不明な資源: %s" % r, file=sys.stderr)
            return 1
        hold = [c for c in load_all(a.ttl)
                if r in c.get("resources", []) and c["session"] != me]
        if not hold or res_stale(hold[0], r):
            print("%s は空いている(待つ必要なし)。そのまま使えば claim が付く" % r)
            continue
        n = q_enqueue(r, me, a.note or "")
        print("待ち行列: %s の %d 番目に並んだ(いまの使用者 %s・最終使用 %.0f分前)。\n"
              "  空けば先頭のあなたに %.0f 分の予約が出る。使用者から連絡が来る決まり。"
              % (r, n, hold[0]["session"], res_idle(hold[0], r), RESERVE_MIN))
    return 0


def cmd_unwait(a):
    me = sid(a.session)
    for r in a.resources:
        q_drop(r, me)
    print("待ち行列から降りた: %s" % ", ".join(a.resources))
    return 0


def cmd_claim(a):
    me = sid(a.session)
    c, fp = mine(me)
    was = os.path.exists(fp)
    old_note = c.get("note", "")
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
        # ⚠ `claim` で直接取得したときも待ち行列から自分を落とす。落とさないと、
        #   `check-unity` を経ずに取得したセッションが「保持者なのに順番待ち」のまま残り、
        #   status の待ち行列の人数が水増しされる(2026-08-31、松平の 180分待ち表示で発覚)。
        q_drop(r, me)
    # ⚠ **既存の記録へ追記するときは黙って進まない(EDO-0044・土井の要望)。**
    #   取り違えたまま note を上書きすると、相手は自分の claim が化けたことに気づけない。
    if was and (a.note and old_note and a.note != old_note):
        print("⚠ 門番: 既存の claim `%s` の note を書き換える。\n"
              "     旧: %s\n     新: %s\n"
              "   これがあなたの claim でないなら、いますぐ `EDO_SESSION_ID=<短縮ID>` を付けて\n"
              "   やり直し、`edo_session.py claim --note '<旧の文言>'` で戻すこと。"
              % (me, old_note, a.note), file=sys.stderr)
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
    freed = []
    for r in a.resources:
        if r in c["resources"]:
            c["resources"].remove(r)
            freed.append(r)
        (c.get("used") or {}).pop(r, None)
    save(c, fp)
    print("release: 残り %s %s" % (c["paths"], c["resources"]))
    _hand_over(freed)
    return 0


def _hand_over(freed):
    """空けた資源を待ち行列の先頭へ引き渡す。⛔ 連絡は解放した側の義務。"""
    for r in freed:
        w = q_reserve(r)
        if not w:
            print("  %s は空きになった(待っているセッションは無し)" % r)
            continue
        print("  ⭐ %s の待ち行列の先頭は **%s**(%.0f 分待ち)。%.0f 分の予約を出した。\n"
              "     ⛔ **次の人へ必ず連絡すること** — `ListAgents` で相手を探し、`SendMessage` で\n"
              "     「%s が空きました。予約は %.0f 分です」と伝える。連絡しないと待ち続ける。"
              % (r, w["session"], (now() - w["since"]) / 60.0, RESERVE_MIN, r, RESERVE_MIN))


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
    # ── ① 本物の競合(誰かが既にこのパス/ドメインを持っている)を**先に**見る。
    #    ここを後回しにすると、third が「山王は solo がメインで書いている最中」なのに
    #    「worktree を用意したのでどうぞ」と案内してしまい、**同じ論理ファイルを
    #    別の場所で同時編集する**という門番が防ぎたい事故そのものになる(2026-08-24)。
    hs = holders(p, me, a.ttl)
    if hs:
        c, g = hs[0]
        return _deny(
            "⛔ 門番: `%s` は**別のセッション %s** が押さえている(claim `%s`／心拍 %.0f 分前)。\n"
            "   %s\n"
            "   同じファイルを同時に書くと片方の編集が消える。\n"
            "   → 待つか、そのセッションに `Tools/Session/edo_session.py release %s` を頼むこと。\n"
            "   → 引き継ぐと決めたなら `Tools/Session/edo_session.py steal %s` で奪える(理由を残す)。"
            % (r, c["session"], g, (now() - c["heartbeat"]) / 60.0, c.get("note", ""), g, g))

    # ── ② 競合はしていないが、他のセッションが存在する。**このセッションにとって
    #    新しいドメイン**なら worktree へ回して隔離する。既に自分が持っているドメイン
    #    (作業を続けているだけ)は回さない — 無関係なセッションの起動で追い出されない。
    d = domain(p)
    if d and in_main_checkout() and not a.no_route:
        others = [c for c in load_all(a.ttl) if c["session"] != me]
        mineC, _ = mine(me)
        if (others and d not in mineC.get("paths", [])
                and "unity" not in mineC.get("resources", [])
                and "main" not in mineC.get("resources", [])):
            wt = ensure_wt(d)
            if wt and os.path.realpath(wt) != os.path.realpath(ROOT):
                touch(me, paths=[d])
                return _deny(
                    "⛔ 門番: いま**他のセッションが %d 本動いている**。指図の作業は worktree でやること。\n"
                    "   `%s` の worktree を用意した:\n"
                    "     %s\n"
                    "   → **そこの同じパスを絶対パスで開けばよい**(cd は要らない):\n"
                    "     %s\n"
                    "   → ビルダーもその worktree のものを走らせること:\n"
                    "     python3 %s/Tools/Sashizu/...\n"
                    "   ⚠ Unity の計測が要るなら `edo_session.py claim --resources unity` を先に取る"
                    "(その場合はメインのままで通す)。\n"
                    "   ⚠ どうしてもメインで書くなら `edo_session.py claim --resources main`。"
                    % (len(others), d, wt, os.path.join(wt, rel(p)), wt))
    touch(me, paths=[p])
    return 0


BLENDER = re.compile(r"(?:^|[;&|(\n]\s*)(?:\S*/)?blender\b")


def cmd_check_bash(a):
    me = sid(a.session)
    cmd = a.command or ""
    # ── Blender(部材作り)
    #    ⚠ Blender 同士は競合しない(--background の使い捨て)。効くのは
    #    「worktree では在庫キットも出力先も無い」ことと、出力が共有資産であること。
    if BLENDER.search(cmd):
        if not in_main_checkout():
            return _deny(
                "⛔ 門番: **Blender は worktree では回せない**。\n"
                "   在庫キット(Japanese Village Kit ほか)は再配布不可で gitignore されているので\n"
                "   sparse worktree に**来ない**。`vklib.py` はメインの絶対パスを直書きしており、\n"
                "   出力先 `Assets/Edo/Models/` も worktree には無い。\n"
                "   → **メインのチェックアウトのセッション**で回すこと:\n"
                "     %s" % os.path.dirname(_common_git_dir()))
        cs = load_all(a.ttl)
        h = [c for c in cs if c["session"] != me and "assets" in c.get("resources", [])]
        if h:
            return _deny(
                "⛔ 門番: 部材の書き出しは**セッション %s** が使用中(心拍 %.0f 分前)。\n"
                "   %s\n"
                "   出力先 `Assets/Edo/Models/` は共有で、同じ部材を同時に焼くと**後勝ちで上書き**される\n"
                "   (`build_goten_roof.py -- rebuild` は Roofs/ の全数を焼き直す)。\n"
                "   → 終わるのを待つこと。"
                % (h[0]["session"], (now() - h[0]["heartbeat"]) / 60.0, h[0].get("note", "")))
        touch(me, resources=["assets"])
    for pat, why in BANNED:
        if re.search(pat, cmd):
            return _deny("⛔ 門番: この git の打ち方は共有ワークツリーでは禁止。\n   %s" % why)
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
                "⛔ 門番: staging に**別のセッションが押さえているファイル**が入っている。\n"
                + "".join("   %s ← %s\n" % (f, s) for f, s in bad[:8])
                + "   このままコミットすると相手の作業を巻き込む(2026-08-24 の事故と同じ)。\n"
                  "   → `git restore --staged <パス>` で外してからコミットすること。")
    touch(me)
    return 0


def cmd_check_unity(a):
    me = sid(a.session)
    cs = load_all(a.ttl)
    hold = [c for c in cs if "unity" in c.get("resources", [])]
    if hold and hold[0]["session"] == me:
        touch(me, resources=["unity"])   # 自分の使用時刻を打ち直す
        q_drop("unity", me)  # ⚠ 保持者自身が待ち行列に残ると人数が水増しされる(2026-08-31 実測)
        return 0
    ok, h = q_may_take("unity", me)
    if not ok:                            # 空いていても予約者が居るなら割り込ませない
        return _deny(
            "⛔ 門番: Unity は**待ち行列の先頭 %s** に予約が出ている(残り最大 %.0f 分)。\n"
            "   `edo_session.py wait --resources unity` で並ぶこと。"
            % (h["session"], RESERVE_MIN - (now() - h["reserved"]) / 60.0))
    if not hold:
        q_drop("unity", me)
        touch(me, resources=["unity"])
        return 0
    # 掴んだままだが**一定時間 Unity を触っていない** → 明け渡させる(心拍では判定できない)
    if res_stale(hold[0], "unity"):
        _force_release(hold[0]["session"], ["unity"])
        q_drop("unity", me)
        touch(me, resources=["unity"])
        print("⚠ 門番: Unity は %s が握ったままだったが、%.0f 分使われていないので引き取った。\n"
              "   作業が終わったら `edo_session.py release --resources unity` を打つこと。"
              % (hold[0]["session"], res_idle(hold[0], "unity")))
        return 0
    n = q_enqueue("unity", me, a.session or "")
    return _deny(
        "⛔ 門番: Unity は**セッション %s** が使用中(最終使用 %.0f 分前)。\n   %s\n"
        "   Unity の実体は1つで、シーン・プレハブ・地形を共有している。"
        "**地形の編集は Undo の外**なので、同時に触ると復旧できない。\n"
        "   → **待ち行列に並べた(%d 番目)。** 空けば先頭のあなたに %.0f 分の予約が出る。\n"
        "   順番は `edo_session.py status` で見える。降りるなら "
        "`edo_session.py unwait --resources unity`。"
        % (hold[0]["session"], res_idle(hold[0], "unity"), hold[0].get("note", ""),
           n, RESERVE_MIN))


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


SPARSE = ["docs", "Tools", ".claude"]


def _wt_root():
    return os.path.join(os.path.dirname(_common_git_dir()), ".claude", "worktrees")


def wt_for(dom):
    """屋敷 `sashizu:<名>` に対応する worktree のパス(在れば)。"""
    name = dom.split(":", 1)[-1]
    path = os.path.join(_wt_root(), name)
    if os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(os.path.join(path, ".git")):
        return path
    r = subprocess.run(["git", "-C", ROOT, "worktree", "list", "--porcelain"],
                       capture_output=True, text=True).stdout
    for blk in r.split("\n\n"):
        wp = br = None
        for ln in blk.split("\n"):
            if ln.startswith("worktree "): wp = ln[9:]
            if ln.startswith("branch "): br = ln[7:]
        if wp and br and br.endswith("/" + name):
            return wp
    return None


def ensure_wt(dom, quiet=True):
    """屋敷の worktree を用意して返す。⚠ 無ければ黙って作る。"""
    got = wt_for(dom)
    if got:
        return got
    name = dom.split(":", 1)[-1]
    class _A:  # cmd_worktree の引数の器
        pass
    a = _A(); a.name = name; a.branch = None; a.base = None; a.full = False
    buf = io.StringIO() if quiet else None
    if quiet:
        old = sys.stdout; sys.stdout = buf
    try:
        cmd_worktree(a)
    finally:
        if quiet:
            sys.stdout = old
    return wt_for(dom)


def in_main_checkout():
    return os.path.realpath(ROOT) == os.path.realpath(os.path.dirname(_common_git_dir()))


def _board_open(name):
    """掲示板のその邸+横断の open issue を出す。CLI は**メインの checkout の物**を使う
    (worktree のブランチには main を取り込むまで無いことがある)。"""
    bcli = os.path.join(os.path.dirname(_common_git_dir()), "Tools", "Session", "edo_board.py")
    if not os.path.exists(bcli):
        return
    r = subprocess.run([sys.executable, bcli, "list", "--estate", name],
                       capture_output=True, text=True)
    o = r.stdout.strip()
    if r.returncode == 0 and o and "該当 issue なし" not in o:
        print("  掲示板(この邸+横断の open。作法: docs/session-board.md):")
        for ln in o.split("\n"):
            print("    " + ln)


def cmd_start(a):
    """屋敷の作業を始める。**worktree を探し、無ければ作って**、claim まで済ませる。"""
    me = sid(a.session)
    dom = "sashizu:" + re.sub(r"[^A-Za-z0-9_-]", "-", a.name)
    c, fp = mine(me)
    if dom not in c["paths"]:
        c["paths"].append(dom)
    if a.note:
        c["note"] = a.note
    if a.unity or a.blender:
        want = ["unity"] if a.unity else ["assets"]
        for w in want:
            h = [x for x in load_all(a.ttl) if x["session"] != me and w in x.get("resources", [])]
            if h:
                print("⛔ %s は %s が使用中(%s)。終わるのを待つこと"
                      % (w, h[0]["session"], h[0].get("note", "")), file=sys.stderr)
                return 2
        for r in want + ["main"]:
            if r not in c["resources"]:
                c["resources"].append(r)
        save(c, fp)
        print("start: %s ／ %s を確保。**メインのチェックアウトで作業する**\n  %s"
              % (dom, "／".join(want), ROOT))
        if a.blender:
            print("  ⚠ 焼いたら Unity で **Edo ▸ 御殿 ▸ …マテリアルをremap** を走らせること"
                  "(FBX は材質名しか運ばないので、やらないと白い模型になる)")
        _board_open(dom.split(":", 1)[-1])
        return 0
    save(c, fp)
    wt = ensure_wt(dom, quiet=False)
    print("start: %s\n  作業ディレクトリ: %s" % (dom, wt))
    print("  ⚠ Unity はここでは開けない。計測が要るなら別途 `claim --resources unity`")
    _board_open(dom.split(":", 1)[-1])
    return 0


def cmd_worktree(a):
    """指図作業用の **sparse worktree** を切る。

    Assets(249MB・825ファイル)を落として docs/Tools だけを置く。
    ⚠ **Unity は開けない**(パックが gitignore で来ない)。計測が要るなら
    メインのチェックアウトで `unity` 資源を取ってから測ること。
    """
    name = re.sub(r"[^A-Za-z0-9_-]", "-", a.name)
    branch = a.branch or ("sashizu/%s" % name)
    path = os.path.join(_wt_root(), name)
    if os.path.exists(path):
        print("既にある: %s" % path)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        base = a.base or subprocess.run(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"],
                                        capture_output=True, text=True).stdout.strip()
        cmd = ["git", "-C", ROOT, "worktree", "add", "--no-checkout", path]
        ex = subprocess.run(["git", "-C", ROOT, "rev-parse", "--verify", "-q", branch],
                            capture_output=True, text=True).returncode == 0
        cmd += ([branch] if ex else ["-b", branch, base])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(r.stderr, file=sys.stderr)
            return 1
        if not a.full:
            subprocess.run(["git", "-C", path, "sparse-checkout", "init", "--cone"], check=True)
            subprocess.run(["git", "-C", path, "sparse-checkout", "set"] + SPARSE, check=True)
        subprocess.run(["git", "-C", path, "checkout"], check=False)
    n = len(subprocess.run(["git", "-C", path, "ls-files"], capture_output=True,
                           text=True).stdout.split())
    print("worktree: %s\n  ブランチ %s ／ ファイル %d 件%s" % (
        path, branch, n, "" if a.full else "(sparse: %s)" % " ".join(SPARSE)))
    print("  ⚠ ここでは Unity は開けない。計測はメインのチェックアウトで `claim --resources unity`")
    print("  この worktree でセッションを始めるには:")
    print("    cd %s" % path)
    return 0


def cmd_worktrees(a):
    r = subprocess.run(["git", "-C", ROOT, "worktree", "list", "--porcelain"],
                       capture_output=True, text=True).stdout
    cur, rows = {}, []
    for ln in r.split("\n"):
        if not ln.strip():
            if cur: rows.append(cur); cur = {}
            continue
        k, _, v = ln.partition(" ")
        cur[k] = v
    if cur: rows.append(cur)
    main_wt = os.path.dirname(_common_git_dir())
    for w in rows:
        wp = w.get("worktree", "")
        if os.path.realpath(wp) == os.path.realpath(main_wt):
            tag = "メイン ─ Unity はここ"
        elif os.path.isdir(os.path.join(wp, "Assets")):
            tag = "全部入り(Unity 可)"
        else:
            tag = "指図用(sparse・Unity 不可)"
        print("  %-58s %-22s %s" % (wp, w.get("branch", "(detached)").replace("refs/heads/", ""), tag))
    return 0


def main():
    ap = argparse.ArgumentParser(description="門番 — 並行セッションの調停")
    ap.add_argument("--session"); ap.add_argument("--ttl", type=float, default=TTL_MIN)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("claim"); p.add_argument("paths", nargs="*")
    p.add_argument("--resources", nargs="*", default=[]); p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_claim)
    p = sub.add_parser("release", help="claim を返す。⭐ Unity 作業が終わったら "
                                       "`release --resources unity` を必ず打つ")
    p.add_argument("paths", nargs="*")
    p.add_argument("--resources", nargs="*", default=[]); p.set_defaults(fn=cmd_release)
    p = sub.add_parser("wait", help="使用中の資源の待ち行列に並ぶ(空けば先頭に予約が出る)")
    p.add_argument("--resources", nargs="+", required=True, choices=RESOURCES)
    p.add_argument("--note", default=""); p.set_defaults(fn=cmd_wait)
    p = sub.add_parser("unwait", help="待ち行列から降りる")
    p.add_argument("--resources", nargs="+", required=True, choices=RESOURCES)
    p.set_defaults(fn=cmd_unwait)
    p = sub.add_parser("check-write"); p.add_argument("path")
    p.add_argument("--no-route", action="store_true"); p.set_defaults(fn=cmd_check_write)
    p = sub.add_parser("check-bash"); p.add_argument("command"); p.set_defaults(fn=cmd_check_bash)
    sub.add_parser("check-unity").set_defaults(fn=cmd_check_unity)
    p = sub.add_parser("steal"); p.add_argument("what", nargs="+")
    p.add_argument("--reason", default=""); p.set_defaults(fn=cmd_steal)
    p = sub.add_parser("start"); p.add_argument("name")
    p.add_argument("--unity", action="store_true", help="Unity を使う(メインに留まる)")
    p.add_argument("--blender", action="store_true", help="Blender で部材を作る(メインに留まる)")
    p.add_argument("--note", default=""); p.set_defaults(fn=cmd_start)
    p = sub.add_parser("worktree"); p.add_argument("name")
    p.add_argument("--branch"); p.add_argument("--base")
    p.add_argument("--full", action="store_true", help="Assets も含める(Unity を開くなら)")
    p.set_defaults(fn=cmd_worktree)
    sub.add_parser("worktrees").set_defaults(fn=cmd_worktrees)
    p = sub.add_parser("commit"); p.add_argument("paths", nargs="+")
    p.add_argument("-m", "--message", required=True); p.set_defaults(fn=cmd_commit)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
