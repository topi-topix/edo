#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""掲示板の一斉整理(計画 D-4・2026-09-13)— 生存 issue に「処置の案」を付けて一覧にし、承認後に一括で実行する。

【なぜ要るか】2026-09-13 の実測: 生存 142 件のうち教訓 34・完了報告 39・裁定の記録 12(=info 95 件の 9 割)、
blocker 21 件のうち本物は 2 件、多邸 task が 7 件、97% が起票時の status のまま。

【使い方】
    python3 Tools/Session/board_triage.py                # 一覧(Markdown)を標準出力へ。ファイルへ: > docs/board-triage.md
    python3 Tools/Session/board_triage.py --apply docs/board-triage.md   # 表の「処置」列どおりに実行(ユーザーが編集してよい)

処置の語彙(表の「処置」列。編集してよい):
    done            — 済みとして閉じる(info の完了報告・裁定の記録・解消済の件)
    lesson          — docs/lessons.md へ 1 行移して閉じる(教訓・一般則)
    task:<邸>       — 種別を task にし owner を <邸> にする(blocker の「発見・疑い」を宿題へ)
    split:<邸,邸>   — 邸ごとに task を分けて起票し、元は閉じる(多邸の task)
                      ⭕ 親の本文と記録の要点を**子へ写す**(2026-09-21・EDO-0308)
                      ⛔ 親の記録に完了報告があれば**分けずに止める**。読んだうえで分けるなら `split!:<邸,邸>`
    keep            — そのまま
    hikitoru:<邸>   — 引き取る(古び・時効を解き、owner を <邸> にして in-progress。畳んだ件も戻る)
    tatamu          — 畳む(誰も引き取らないと決めた件。`list --all` には残る)
    sueoki          — 据え置き(齢の時計を今に戻す。あと 14 日は古びない)
    keep-blocker:<誰が>|<何で解けるか> — 本物の blocker として --blocked/--until を付ける

【朝ひと画面(2026-09-21 施主裁定 EDO-0297=A)】
    python3 Tools/Session/board_triage.py --stuck > docs/board-triage.md
「詰まっている物だけ」= 古びた件・時効で畳んだ件(直近7日)・宛先の無い宿題 を1枚の表にする。
施主は処置の列に一語書くだけでよい(既定の案が入っている)。毎朝の日誌(/nikki)がこれを回す。
⛔ 全件を出さない — 69 件の表は読まれない。読まれない画面は無いのと同じ(2026-09-21 の実測が
   まさにそれで、生きている 69 件のうち 44 件が起票以来ひとことも付いていなかった)。
"""
import argparse, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edo_board import load_all, LIVE, BOARD, path_of, atomic_write_json, now, REPO

LESSON_PAT = re.compile(r"(せよ|しない|てはいけない|作法|とは限らない|疑い|の罠|数えない|決めない|使えない|読まれる危険|効かなくなる|切れない|括る)")
DONE_PAT = re.compile(r"(完了|済|返しました|commit しました|到達|節目|通過|ユーザー裁定|ユーザー確定|ユーザー判読|ユーザー回答|ユーザー参照|ユーザー大方針|直した|足した|広げた|確定)")
REAL_BLOCKER = {"EDO-0014"}          # 精読で「誰かが止まっている」と判じた物(0005 は裁定済で done)


def propose(c):
    t, title, est = c["type"], c["title"], c["estate"]
    owners = [o for o in re.split(r"[,、\s]+", c.get("owner") or "") if o]
    arrow = re.search(r"→([A-Za-z_,]+)", title)
    if arrow:
        owners = owners or arrow.group(1).split(",")
    if t == "decision":
        return "keep", "裁定待ち"
    if t == "info":
        if LESSON_PAT.search(title) and not DONE_PAT.search(title.split("—")[0]):
            return "lesson", "一般則・教訓 → docs/lessons.md"
        return "done", "完了報告・裁定の記録(記録として残る。list --all で引ける)"
    if t == "blocker":
        if c["id"] in REAL_BLOCKER or c.get("blocked"):
            return "keep-blocker:%s|%s" % (c.get("blocked") or "山王(切り出し)", c.get("until") or "生成器の復旧"), "本物の詰まり"
        if c["id"] == "EDO-0005":
            return "done", "ユーザー裁定で追わないと確定済"
        if LESSON_PAT.search(title) and not est in ("cross", "infra"):
            return "task:%s" % est, "自邸の発見 → 宿題"
        if est in ("cross", "infra"):
            return ("task:infra" if est == "infra" else "lesson"), "発見・疑い・一般則(誰も止まっていない)"
        return "task:%s" % est, "自邸の宿題"
    if t == "task":
        if len(owners) > 1:
            # ⚠ 親の記録に完了報告があれば表の段階で断る — 済んだ仕事の再発行を人が止められるように
            #   (実行の側でも --apply が止める。EDO-0308)
            hits = _done_hits(c)
            return ("split:%s" % ",".join(owners),
                    "多邸の相乗り task を邸ごとに" if not hits else
                    "⚠ **親の記録に完了報告が %d 件** — 分ける前に読むこと(%s…)。承知で分けるなら `split!:`"
                    % (len(hits), hits[0][:40]))
        if not owners and est in ("cross", "infra"):
            return "lesson" if LESSON_PAT.search(title) else "keep", "担い手が無い"
        return "keep", ""
    return "keep", ""


def _age_d(c):
    return (now() - (c.get("updated") or c.get("created") or now())) / 86400.0


def stuck_rows():
    """朝ひと画面に出す物 — 古びた件・直近7日に時効で畳んだ件・宛先の無い宿題。"""
    out = []
    for c in load_all():
        live = c["status"] in LIVE
        if live and c.get("stale"):
            out.append(c)
        elif c.get("expired") and _age_d(c) < 7:
            out.append(c)
        elif live and c["type"] == "task" and not c.get("owner"):
            out.append(c)
    return sorted(out, key=lambda c: (-_age_d(c), c["id"]))


def propose_stuck(c):
    if c.get("expired"):
        return "keep", "時効で畳んだ(戻すなら hikitoru:<邸>)"
    owner = c.get("owner") or (c["estate"] if c["estate"] not in ("cross", "infra") else "")
    if c.get("stale"):
        if owner:
            return "hikitoru:%s" % owner, "%d 日止まっているが宛先はある" % _age_d(c)
        return "tatamu", "%d 日止まっていて宛先も無い" % _age_d(c)
    return ("hikitoru:%s" % owner if owner else "keep"), "宛先が空のまま"


def cmd_list(stuck=False):
    if stuck:
        cs = stuck_rows()
        print("# 掲示板の差配 — 詰まっている %d 件(%s)\n" % (len(cs), time.strftime("%Y-%m-%d")))
        print("処置の列を一語直してから `python3 Tools/Session/board_triage.py --apply <このファイル>`。")
        print("`hikitoru:<邸>`=引き取る / `tatamu`=畳む / `sueoki`=据え置き(あと14日) / `keep`=案のまま。\n")
    else:
        cs = [c for c in load_all() if c["status"] in LIVE]
        print("# 掲示板の一斉整理 — 処置の案(%s・生存 %d 件)\n" % (time.strftime("%Y-%m-%d"), len(cs)))
        print("処置の列を直してから `python3 Tools/Session/board_triage.py --apply <このファイル>`。語彙は同スクリプトの docstring。\n")
    print("| ID | 種別 | 邸 | 齢 | 処置 | 理由 | 題 |\n|---|---|---|---|---|---|---|")
    agg = {}
    for c in (cs if stuck else sorted(cs, key=lambda c: c["id"])):
        act, why = propose_stuck(c) if stuck else propose(c)
        agg[act.split(":")[0]] = agg.get(act.split(":")[0], 0) + 1
        age = int(_age_d(c) if stuck else (now() - c.get("created", 0)) / 86400)
        print("| %s | %s | %s | %dd | `%s` | %s | %s |" % (c["id"], c["type"], c["estate"], age, act, why,
                                                      c["title"].replace("|", "｜")[:90]))
    print("\n処置の内訳: " + " / ".join("%s %d" % kv for kv in sorted(agg.items())))
    return 0


def _human_log(c):
    """一斉整理そのものが足した行を除いた、人の書いた記録。"""
    return [l for l in (c.get("log") or []) if l.get("by") not in ("triage",)]


def _done_hits(c):
    """親の記録の中の**完了報告らしい行**。

    ⛔ **題だけを見て分けてはいけない。**2026-09-13 の一斉整理は親の題だけを写して子を起こし、
    親の記録に在った完了報告を読まなかった。その結果、**2週間前に済んでいた仕事を4件再発行**した
    (基準年次が岡部・土井・山王で完了済み、取り合いが土井で完了済み)。掲示板 EDO-0308。
    """
    out = []
    for l in _human_log(c):
        msg = (l.get("msg") or "").strip()
        if DONE_PAT.search(msg):
            out.append("%s %s: %s" % ((l.get("t") or "")[:10], (l.get("by") or "?")[:12], msg[:90]))
    return out


def _parent_digest(c, iid, limit=780):
    """子へ写す本文。

    ⛔ **本文の無い子を起こさない。**分割された32件は中身が閉じた親の中にしか無く、
    引き取った側に読む物が無かった — 8日間ひとことも付かなかった(EDO-0308)。
    """
    parts = ["親 %s「%s」から分けた宿題。⛔ 親は閉じているので、以下が中身のすべて。"
             % (iid, (c.get("title") or "").strip())]
    logs = _human_log(c)
    if logs:
        parts.append("【起票時】" + (logs[0].get("msg") or "").strip())
    for l in logs[1:][-2:]:
        parts.append("【%s】%s" % ((l.get("t") or "")[:10], (l.get("msg") or "").strip()))
    body = "\n".join(parts)
    return body if len(body) <= limit else body[:limit - 1] + "…"


def _board(*args):
    r = subprocess.run([sys.executable, os.path.join(REPO, "Tools", "Session", "edo_board.py")] + list(args),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().split("\n")[0]


def cmd_apply(fp):
    rows = re.findall(r"^\| (EDO-\d{4}) \| \w+ \| [\w-]+ \| \d+d \| `([^`]+)` \|", open(fp, encoding="utf-8").read(), re.M)
    n = 0
    for iid, act in rows:
        c = json.load(open(path_of(iid), encoding="utf-8"))
        if c["status"] not in LIVE and not c.get("expired"):
            continue        # 時効で畳んだ件だけは、朝の差配で引き取り直せる
        kind, _, arg = act.partition(":")
        if kind == "keep":
            continue
        if kind == "done":
            c["status"] = "done"; c["log"].append({"t": now(), "by": "triage", "msg": "一斉整理(2026-09-13): 記録として閉じた"})
        elif kind == "lesson":
            c["type"] = "lesson"; c["status"] = "done"
            c["log"].append({"t": now(), "by": "triage", "msg": "一斉整理: 教訓として docs/lessons.md へ"})
            with open(os.path.join(REPO, "docs", "lessons.md"), "a", encoding="utf-8") as f:
                f.write("- %s **%s**(%s・%s)\n" % (time.strftime("%Y-%m-%d"), c["title"], iid, c["estate"]))
        elif kind == "task":
            c["type"] = "task"; c["owner"] = arg; c["status"] = "open"
            c["log"].append({"t": now(), "by": "triage", "msg": "一斉整理: blocker → task(owner %s)。誰も止まっていない発見" % arg})
        elif kind == "keep-blocker":
            who, _, until = arg.partition("|")
            c["blocked"], c["until"] = who, until
            c["log"].append({"t": now(), "by": "triage", "msg": "一斉整理: --blocked/--until を付けた"})
        elif kind in ("split", "split!"):
            hits = _done_hits(c)
            if hits and kind == "split":
                print("⛔ %s は分けない — 親の記録に完了報告がある(済んだ仕事の再発行になる):" % iid)
                for h in hits[:3]:
                    print("     " + h)
                print("     読んだうえで分けるなら処置を `split!:%s` に書き換える" % arg)
                continue
            body = _parent_digest(c, iid)
            for est in [e for e in arg.split(",") if e]:
                rc, line = _board("post", "--estate", est, "--type", "task", "--owner", est,
                                  "--title", (c["title"].split("(→")[0].strip())[:70],
                                  "--ref", "board:%s" % iid, "--msg", body)
                print("   " + line)
            c["status"] = "done"; c["log"].append({"t": now(), "by": "triage", "msg": "一斉整理: 邸ごとに分割して閉じた(%s)%s"
                                                   % (arg, "・⚠ 完了報告があるのを承知で分けた" if hits else "")})
        elif kind == "hikitoru":
            c["status"] = "in-progress" if arg else "open"
            c.pop("stale", None); c.pop("stale_at", None); c.pop("expired", None)
            if arg:
                c["owner"] = arg
            c["log"].append({"t": now(), "by": "triage", "msg": "朝の差配: 引き取った(→%s)" % (arg or "—")})
        elif kind == "tatamu":
            c["status"] = "dropped"
            c["log"].append({"t": now(), "by": "triage", "msg": "朝の差配: 誰も引き取らないと決めた(戻すなら reopen)"})
        elif kind == "sueoki":
            c.pop("stale", None); c.pop("stale_at", None)
            c["log"].append({"t": now(), "by": "triage", "msg": "朝の差配: 据え置き(齢の時計を戻した)"})
        else:
            print("? 不明な処置 %s (%s)" % (act, iid)); continue
        c["updated"] = now(); atomic_write_json(c, path_of(iid)); n += 1
        print("%s ← %s" % (iid, act))
    print("実行 %d 件" % n)
    return 0


def selftest():
    """⛔ 落ちたら**分割の歯止めが死んでいる。**

    ⚠ 分割は「正しく動いても何も鳴らない」種類の処置なので、壊れても誰も気づかない —
    済んだ仕事が静かに再発行され、本文の無い子が静かに積まれる(2026-09-13 に実際に起きた)。
    ⛔ 本物の掲示板は一切触らない(捨て場に作り物を置き、post は差し替える)。
    """
    import shutil, tempfile
    import edo_board
    tmp = tempfile.mkdtemp(prefix="board-triage-selftest-")
    orig_board, orig__board = edo_board.BOARD, globals()["_board"]
    posted = []
    globals()["_board"] = lambda *a: (posted.append(list(a)), (0, "post: (作り物)"))[1]
    edo_board.BOARD = tmp
    ng = []

    def plant(iid, log):
        c = {"id": iid, "title": "連なる棟の継ぎ目に渡廊下", "type": "task", "estate": "cross",
             "owner": "", "status": "open", "updated": now(), "log": log}
        atomic_write_json(c, path_of(iid))

    def table(iid, act):
        fp = os.path.join(tmp, "t.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("| ID | 種別 | 邸 | 齢 | 処置 | 理由 | 題 |\n|---|---|---|---|---|---|---|\n"
                    "| %s | task | cross | 8d | `%s` | r | t |\n" % (iid, act))
        return fp

    def check(title, ok, why=""):
        print("%s %s%s" % ("⭕" if ok else "⛔", title, "" if ok else " — " + why))
        if not ok:
            ng.append(title)

    try:
        # ① 完了報告のある親は分けない
        done_log = [{"t": "2026-08-31T10:00:00+09:00", "by": "doi", "msg": "土井です。渡廊下と突き付けの検査を2本足して完了しました。"}]
        plant("EDO-9001", done_log)
        del posted[:]
        cmd_apply(table("EDO-9001", "split:okabe,doi"))
        c = json.load(open(path_of("EDO-9001"), encoding="utf-8"))
        check("完了報告のある親を分けない", not posted and c["status"] == "open",
              "子を %d 件起こし、親は %s" % (len(posted), c["status"]))

        # ② split! なら承知のうえで分ける
        del posted[:]
        cmd_apply(table("EDO-9001", "split!:okabe,doi"))
        c = json.load(open(path_of("EDO-9001"), encoding="utf-8"))
        check("split! なら分ける", len(posted) == 2 and c["status"] == "done",
              "子 %d 件・親 %s" % (len(posted), c["status"]))

        # ③ 子に親の本文が入る(⛔ 「分けた」の一言だけにしない)
        msg = posted[0][posted[0].index("--msg") + 1] if posted else ""
        check("子が親の本文を持つ", "検査を2本足して完了" in msg and "EDO-9001" in msg,
              "本文= %r" % msg[:60])

        # ④ 完了報告の無い親は素の split で通り、やはり本文が入る
        plant("EDO-9002", [{"t": "2026-09-13T10:00:00+09:00", "by": "sanno",
                            "msg": "山王です。崖線の植生を3邸で揃える必要があります。"}])
        del posted[:]
        cmd_apply(table("EDO-9002", "split:sanno,doi"))
        msg2 = posted[0][posted[0].index("--msg") + 1] if posted else ""
        check("無傷な親は分けられる", len(posted) == 2 and "崖線の植生" in msg2,
              "子 %d 件・本文= %r" % (len(posted), msg2[:60]))
    finally:
        edo_board.BOARD = orig_board
        globals()["_board"] = orig__board
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if ng:
        print("⛔ 自己検査 不通 %d 件 — **分割の歯止めが死んでいる。**%s" % (len(ng), " / ".join(ng)))
        return 1
    print("⭕ 自己検査 全通 — 4 つの形とも生きている。")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", metavar="MD")
    ap.add_argument("--stuck", action="store_true", help="朝ひと画面 — 詰まっている件だけ出す")
    a = ap.parse_args()
    return cmd_apply(a.apply) if a.apply else cmd_list(a.stuck)


if __name__ == "__main__":
    sys.exit(main())
