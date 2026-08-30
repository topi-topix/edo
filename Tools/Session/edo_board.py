#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""掲示板 — セッション横断のタスク・裁定要請・ブロッカーの登録簿。

**なぜ要るか**: claim(edo_session.py)は衝突を防ぐだけで、「どのセッションが何を
やっていて、何に詰まっていて、ユーザーの裁定を何件待っているか」は誰にも見えない。
横断影響(基準面・共有境界・parcels)の伝達をユーザーが人力でやっていた。

**考え方**
- **1 issue 1ファイル**(`EDO-0001.json`)。3セッションが同時に書いても後勝ち上書きが
  起きない。採番だけ O_EXCL で衝突を避ける。
- **正典は写さない。** 邸の未決の中身は `docs/Sashizu/<屋敷>_sashizu.json` の `_pending` が
  正典のまま。issue は `refs` で指すだけ(CLAUDE.md「同じ事実を二重に書かない」)。
- **post する契機は3つだけ**: 節目(info)/ブロッカー(blocker)/裁定要請(decision)。
  細かい報告は書かない — コミットが報告を兼ね、作事奉行が git log を読む。
- **decision はテンプレ強制**(背景/選択肢/推奨/影響)。ユーザーが判断できる形で
  しか裁定を仰げないようにする。

置き場所は `.git/edo-board/`(git 管理外・全 worktree 共有)。`.git/edo-locks` と同じ前例。
使い方の正典: docs/session-board.md
"""
import argparse, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edo_session import sid, _common_git_dir

BOARD = os.path.join(_common_git_dir(), "edo-board")
ESTATES = ("matsudaira_dewa", "sanno", "okabe", "doi", "sotobori", "cross", "infra")
TYPES = ("task", "decision", "blocker", "info")
STATUSES = ("open", "awaiting-user", "in-progress", "done", "dropped")
LIVE = ("open", "awaiting-user", "in-progress")
MARK = {"decision": "⚖", "blocker": "⛔", "task": "・", "info": "ℹ"}


def now():
    return time.time()


def path_of(iid):
    return os.path.join(BOARD, "%s.json" % iid)


def load_all():
    out = []
    if not os.path.isdir(BOARD):
        return out
    for fn in sorted(os.listdir(BOARD)):
        if not re.match(r"EDO-\d+\.json$", fn):
            continue
        try:
            out.append(json.load(open(os.path.join(BOARD, fn), encoding="utf-8")))
        except Exception:
            pass  # 壊れた issue は無視(claim と違い消さない — 履歴なので)
    return out


def load_one(iid):
    iid = iid if iid.startswith("EDO-") else "EDO-%04d" % int(iid)
    fp = path_of(iid)
    if not os.path.exists(fp):
        print("無い: %s" % iid, file=sys.stderr)
        return None, None
    return json.load(open(fp, encoding="utf-8")), fp


def save(issue, fp):
    issue["updated"] = now()
    json.dump(issue, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def fmt_line(c):
    mins = (now() - c.get("updated", 0)) / 60.0
    age = ("%.0f日前" % (mins / 1440) if mins >= 1440 else
           "%.0f時間前" % (mins / 60) if mins >= 60 else "%.0f分前" % mins)
    own = "(→%s)" % c["owner"] if c.get("owner") else ""
    return "%s %s [%s/%s] %-13s %s%s %s" % (
        MARK.get(c["type"], "・"), c["id"], c["estate"], c["type"],
        c["status"], c["title"], own, age)


# ────────────────────────────────────────────── サブコマンド
def cmd_post(a):
    me = sid(a.session)
    if a.type == "decision":
        missing = [k for k in ("background", "options", "recommend", "impact", "where")
                   if not getattr(a, k)]
        if missing:
            print("⛔ decision は裁定のテンプレが必須: --%s が無い。\n"
                  "   ユーザーが判断できる形(背景/選択肢/推奨/影響/どこ)でしか裁定は仰げない。"
                  % " --".join(missing), file=sys.stderr)
            return 1
    # ⛔ **どこの話か分からない裁定・ブロッカーは立てられない。**
    #   2026-08-29 にユーザーから「どこのことを指してるのか分からない」と差し戻された。
    #   図版番号・辺と s・グリッド・世界座標・隣接物のうち、図の上で指させるものを最低1つ。
    if a.type == "blocker" and not a.where:
        print("⛔ blocker には --where が要る(どこの話か)。\n"
              "   例: --where '其廿三の左図 / 辺14 s6.8〜12.3(東辺の北端・隅櫓のすぐ南)'",
              file=sys.stderr)
        return 1
    os.makedirs(BOARD, exist_ok=True)
    nums = [int(re.search(r"\d+", c["id"]).group()) for c in load_all()]
    n = max(nums or [0]) + 1
    while True:  # 採番の衝突だけ O_EXCL で避ける
        iid = "EDO-%04d" % n
        try:
            f = open(path_of(iid), "x", encoding="utf-8")
            break
        except FileExistsError:
            n += 1
    issue = {
        "id": iid, "title": a.title, "estate": a.estate, "type": a.type,
        "status": "awaiting-user" if a.type == "decision" else "open",
        "owner": a.owner or "", "refs": a.ref or [], "where": a.where,
        "decision": ({"background": a.background, "options": a.options,
                      "recommend": a.recommend, "impact": a.impact}
                     if a.type == "decision" else None),
        "log": [{"t": now(), "by": me, "msg": a.msg or "起票"}],
        "created": now(), "updated": now(),
    }
    json.dump(issue, f, ensure_ascii=False, indent=1)
    f.close()
    print("post: %s" % fmt_line(issue))
    return 0


def cmd_note(a):
    c, fp = load_one(a.id)
    if not c:
        return 1
    c["log"].append({"t": now(), "by": sid(a.session), "msg": a.msg})
    if a.status:
        if a.status not in STATUSES:
            print("不明な status: %s(%s)" % (a.status, "/".join(STATUSES)), file=sys.stderr)
            return 1
        c["status"] = a.status
    save(c, fp)
    print("note: %s" % fmt_line(c))
    return 0


def cmd_close(a):
    c, fp = load_one(a.id)
    if not c:
        return 1
    c["status"] = "dropped" if a.dropped else "done"
    c["log"].append({"t": now(), "by": sid(a.session), "msg": a.msg or c["status"]})
    save(c, fp)
    print("close: %s" % fmt_line(c))
    return 0


def cmd_list(a):
    cs = load_all()
    if a.estate:
        cs = [c for c in cs if c["estate"] == a.estate or
              (a.estate != "cross" and c["estate"] == "cross")]
    if not a.all:
        cs = [c for c in cs if c["status"] in LIVE]
    if a.json:
        json.dump(cs, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    if not cs:
        print("board: 該当 issue なし")
        return 0
    order = {"awaiting-user": 0, "open": 1, "in-progress": 2, "done": 3, "dropped": 4}
    for c in sorted(cs, key=lambda c: (order.get(c["status"], 9), c["id"])):
        print(fmt_line(c))
    return 0


def cmd_show(a):
    c, _ = load_one(a.id)
    if not c:
        return 1
    print(fmt_line(c))
    if c.get("where"):
        print("  どこ: %s" % c["where"])
    for r in c.get("refs", []):
        print("  ref: %s" % r)
    d = c.get("decision")
    if d:
        print("  背景: %s" % d["background"])
        for o in d["options"]:
            print("  選択肢: %s" % o)
        print("  推奨: %s\n  影響: %s" % (d["recommend"], d["impact"]))
    for e in c.get("log", []):
        print("  %s %s: %s" % (
            time.strftime("%m-%d %H:%M", time.localtime(e["t"])), e["by"][:12], e["msg"]))
    return 0


def cmd_digest(a):
    """greet 用の圧縮表示(≤12行)。裁定待ちとブロッカーを優先。"""
    cs = [c for c in load_all() if c["status"] in LIVE]
    if not cs:
        return 0  # 静かに(greet に空行を足さない)
    wait = [c for c in cs if c["status"] == "awaiting-user"]
    blk = [c for c in cs if c["type"] == "blocker"]
    rest = [c for c in cs if c not in wait and c not in blk]
    print("掲示板 — open %d 件(裁定待ち %d・ブロッカー %d)。詳細: python3 Tools/Session/edo_board.py show <ID>"
          % (len(cs), len(wait), len(blk)))
    lines = 0
    for c in wait + blk + rest:
        if lines >= 10:
            print("  …ほか %d 件(`edo_board.py list`)" % (len(cs) - lines))
            break
        print("  %s" % fmt_line(c))
        lines += 1
    return 0


def main():
    ap = argparse.ArgumentParser(description="掲示板 — セッション横断の issue 登録簿(正典: docs/session-board.md)")
    ap.add_argument("--session")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post", help="起票(節目=info/ブロッカー=blocker/裁定要請=decision)")
    p.add_argument("--title", required=True)
    p.add_argument("--estate", required=True, choices=ESTATES)
    p.add_argument("--type", required=True, choices=TYPES)
    p.add_argument("--owner", default="")
    p.add_argument("--ref", action="append", help="正典への参照(例: docs/Sashizu/doi_sashizu.json#_pending.monsun)")
    p.add_argument("--msg", default="", help="起票時の一言")
    p.add_argument("--background", default="", help="decision: 背景(2文以内)")
    p.add_argument("--options", nargs="*", default=[], help="decision: 選択肢")
    p.add_argument("--recommend", default="", help="decision: 推奨と理由")
    p.add_argument("--impact", default="", help="decision: 採ったときの影響(他邸への波及を含む)")
    p.add_argument("--where", default="",
                   help="decision/blocker 必須: **どこ**の話か。図版番号(其◯)・辺と s・"
                        "グリッド(u,v)・世界座標・隣接物のうち、相手が図の上で指させるものを最低1つ")
    p.set_defaults(fn=cmd_post)
    p = sub.add_parser("note", help="log へ1行追記(--status で状態遷移も)")
    p.add_argument("id"); p.add_argument("msg")
    p.add_argument("--status", choices=STATUSES)
    p.set_defaults(fn=cmd_note)
    p = sub.add_parser("close"); p.add_argument("id")
    p.add_argument("--dropped", action="store_true"); p.add_argument("--msg", default="")
    p.set_defaults(fn=cmd_close)
    p = sub.add_parser("list"); p.add_argument("--estate", choices=ESTATES)
    p.add_argument("--all", action="store_true", help="done/dropped も含める")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show"); p.add_argument("id"); p.set_defaults(fn=cmd_show)
    sub.add_parser("digest", help="greet 用の圧縮表示").set_defaults(fn=cmd_digest)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
