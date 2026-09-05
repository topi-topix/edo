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
  細かい報告は書かない — コミットが報告を兼ねる。
- **decision はテンプレ強制**(背景/選択肢/推奨/影響)。ユーザーが判断できる形で
  しか裁定を仰げないようにする。

置き場所は `.git/edo-board/`(git 管理外・全 worktree 共有)。`.git/edo-locks` と同じ前例。
使い方の正典: docs/session-board.md
"""
import argparse, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edo_session import sid, _common_git_dir, atomic_write_json, estate_names

BOARD = os.path.join(_common_git_dir(), "edo-board")
# ⛔ **敷地の名簿を手で持たない。** 固定の tuple にしていたため、あとから起きた邸
#   (京極備中守・丹羽左京・内藤紀伊)は `post --estate <邸>` が argparse で弾かれ、
#   **掲示板に一言も起票できなかった**(2026-09-01 の点検で発覚。該当3邸の issue は 0 件)。
#   横断影響の伝達は起票が記録の本体なので、名簿の抜けはそのまま「記録が無い」に化ける。
#   ⭕ 指図の実体(main と worktree の docs/Sashizu/*_sashizu.json)から毎回引く。
_FIXED = ("cross", "infra")          # 邸ではない置き場(横断・普請場の機構そのもの)
_LEGACY = ("matsudaira_dewa", "sanno", "okabe", "doi", "sotobori")  # 既存 issue の後方互換
ESTATES = tuple(sorted(set(estate_names()) | set(_FIXED) | set(_LEGACY)))
TYPES = ("task", "decision", "blocker", "info")
STATUSES = ("open", "awaiting-user", "in-progress", "done", "dropped")
LIVE = ("open", "awaiting-user", "in-progress")
MARK = {"decision": "⚖", "blocker": "⛔", "task": "・", "info": "ℹ"}


def now():
    return time.time()


# ────────────────────────────── 一件一葉(docs/reporting-protocol.md・規則8)
#   ⛔ 1件の issue に複数の裁定を詰めない。
#   EDO-0057 は「其の一=隅部材」「其の二=門の切り欠き」で起票され、両方に裁定が下りた後に
#   さらに「天端の段」が湧いて、1件に3つの裁定が積み上がった。片方だけ答えても status が
#   動かせず、巡回のたびに「未裁定が残っている」ようにしか見えない。
_PACK_PATTERNS = (
    (r"其の?[一二三四五六七八九十]", "「其の一/其の二」で数えている"),
    (r"[①②③④⑤]\s*\S+.*[②③④⑤]", "丸数字で数えている"),
    (r"\(1\).*\(2\)", "(1)(2) で数えている"),
)


def check_one_issue_one_ask(a):
    """複数の裁定の詰め込みを弾く。戻り値: 理由(str) or None"""
    body = " ".join([a.title or "", a.background or "", a.msg or ""] + list(a.options or []))
    for pat, why in _PACK_PATTERNS:
        if len(re.findall(pat, body)) >= 2:
            return why
    # 表題が2つの話題を「+」で束ねている(例: 「隅部材が建っていない + 門の切り欠きの扱い」)
    if re.search(r"\S\s*[+＋]\s*\S", a.title or ""):
        return "表題が「+」で2つの話題を束ねている"
    return None


def check_options(opts):
    """選択肢が A/B/C の記号付きで2つ以上あるか。戻り値: 理由(str) or None"""
    if len(opts) < 2:
        return "選択肢が %d 個しかない(2つ以上)" % len(opts)
    bad = [o for o in opts if not re.match(r"\s*[A-Z]\s*[:：]", o)]
    if bad:
        return "記号が無い選択肢がある(先頭を 'A: ' 'B: ' にする): %r" % bad[0][:40]
    return None


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
    # ⛔ 非アトミックな書き込みは、同時に読んでいる別セッションへ壊れた(途中の)JSON を
    #   見せる瞬間がある(2026-08-31、edo_session.py の claim 消失と同根の問題として発見)。
    atomic_write_json(issue, fp)


def fmt_line(c):
    mins = (now() - c.get("updated", 0)) / 60.0
    age = ("%.0f日前" % (mins / 1440) if mins >= 1440 else
           "%.0f時間前" % (mins / 60) if mins >= 60 else "%.0f分前" % mins)
    own = "(→%s)" % c["owner"] if c.get("owner") else ""
    return "%s %s [%s/%s] %-13s %s%s %s" % (
        MARK.get(c["type"], "・"), c["id"], c["estate"], c["type"],
        c["status"], c["title"], own, age)


# ────────────────────────────────────────────── サブコマンド
# ⛔ 規則9 — 内部の符牒(U12 / EDO-0064 / 其十四 / SW2 …)を裸で出さない。
#   2026-08-31 ユーザー指摘「U12 とか言われてもどんな内容だったか分かりません。
#   必ずタスク表か裁定図、指図の該当箇所のリンクを示すように」。
#   題は「その1行だけ見せて相手が中身を言い当てられるか」で判定する。
BARE_TOKEN = re.compile(r"(?<![0-9A-Za-z])(U\d{1,3}|EDO-\d{3,4}|其[一二三四五六七八九十廿卅]+)(?![0-9A-Za-z])")


def check_bare_token(title):
    """題に符牒だけが載っていて、中身の説明が無いなら理由を返す。"""
    m = BARE_TOKEN.findall(title or "")
    if not m:
        return None
    # 符牒を抜いた残りが実質的な説明になっているか(記号と空白を除いて8文字以上)
    rest = BARE_TOKEN.sub("", title)
    rest = re.sub(r"[\s\-—:：/()（）\[\]、。,.]", "", rest)
    if len(rest) >= 8:
        return None
    return "題が符牒(%s)だけで中身が分からない" % "・".join(sorted(set(m)))


def cmd_post(a):
    me = sid(a.session)
    if a.type == "decision":
        missing = [k for k in ("background", "options", "recommend", "impact", "where", "zu")
                   if not getattr(a, k)]
        if missing:
            print("⛔ decision は裁定のテンプレが必須: --%s が無い。\n"
                  "   ユーザーが判断できる形(背景/選択肢/推奨/影響/どこ)でしか裁定は仰げない。"
                  % " --".join(missing), file=sys.stderr)
            return 1
        why = check_options(a.options)
        if why:
            print("⛔ 選択肢は A/B/C の記号付きで2つ以上: %s\n"
                  "   例: --options 'A: 深い石垣で受ける(造成小)' 'B: 平場を北へ補う(造成大)'\n"
                  "   ⭐ 狙いは「1=A」の一言で返せる形。正典: docs/reporting-protocol.md 規則6"
                  % why, file=sys.stderr)
            return 1
    why = check_bare_token(a.title)
    if why:
        print("⛔ 題に内部の符牒を裸で置かない(%s)。\n"
              "   読み手はあなたの文脈を持っていない。符牒は**あなたの索引**であって相手の索引ではない。\n"
              "   ⭐ 判定法: その題だけを他人に見せて、相手が中身を言い当てられるか。\n"
              "   例: ⛔『U12 の扱い』→ ⭕『外堀: 掘る水面 SW2 の 2%% が石垣の天端に埋まる(U12)』\n"
              "   正典: docs/reporting-protocol.md 規則9" % why, file=sys.stderr)
        return 1
    if a.type in ("decision", "blocker"):
        why = check_one_issue_one_ask(a)
        if why:
            print("⛔ 一件一葉 — 1件に複数の裁定を詰めない(%s)。\n"
                  "   独立に答えられる事柄は別の issue に分けて起票する。\n"
                  "   詰めると片方だけ裁定が下りたとき status を動かせず、巡回のたびに\n"
                  "   「未裁定が残っている」ようにしか見えない(実例 EDO-0057 は3つ積み上がった)。\n"
                  "   正典: docs/reporting-protocol.md 規則8\n"
                  "   (図版番号を並べただけなら --where / --zu へ移す)" % why, file=sys.stderr)
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
    while True:  # 採番の衝突だけ O_EXCL で避ける(空ファイルの確保のみ・中身は後で atomic に書く)
        iid = "EDO-%04d" % n
        try:
            open(path_of(iid), "x", encoding="utf-8").close()
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
    atomic_write_json(issue, path_of(iid))
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
    # argparse の usage 行には decision 固有の必須が出ない(required=False のため)。
    # 空振りを減らすため epilog に6点セットを明記する(2026-08-30 外堀セッションの指摘)。
    p = sub.add_parser(
        "post", help="起票(節目=info/ブロッカー=blocker/裁定要請=decision)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚖ --type decision は6点セットが全部必須(1つでも欠けたら弾かれる):
     --where  どこ(図の上で指させるもの)   --background 背景(2文以内)
     --options 選択肢(A/B/C 記号・2つ以上)  --recommend  推奨と理由1文
     --impact 影響(他邸への波及を含む)      --zu         裁定図(図版番号かパス)
⛔ --type blocker は --where が必須。
⛔ 一件一葉 — 1件に複数の裁定を詰めない(其の一/其の二・丸数字・表題の「+」は弾かれる)。
   正典: docs/reporting-protocol.md 規則6・規則8
""")
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
    p.add_argument("--zu", default="",
                   help="decision 必須: **裁定図**。図版番号(其◯)か描いた図のパス。"
                        "各案を同じ縮尺で並べた図と、案ごとに動く数値を添えること"
                        "(2026-08-30 ユーザー指示。名前と数字の羅列で選ばせない)")
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
