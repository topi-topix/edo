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
    keep            — そのまま
    keep-blocker:<誰が>|<何で解けるか> — 本物の blocker として --blocked/--until を付ける
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
            return "split:%s" % ",".join(owners), "多邸の相乗り task を邸ごとに"
        if not owners and est in ("cross", "infra"):
            return "lesson" if LESSON_PAT.search(title) else "keep", "担い手が無い"
        return "keep", ""
    return "keep", ""


def cmd_list():
    cs = [c for c in load_all() if c["status"] in LIVE]
    print("# 掲示板の一斉整理 — 処置の案(%s・生存 %d 件)\n" % (time.strftime("%Y-%m-%d"), len(cs)))
    print("処置の列を直してから `python3 Tools/Session/board_triage.py --apply <このファイル>`。語彙は同スクリプトの docstring。\n")
    print("| ID | 種別 | 邸 | 齢 | 処置 | 理由 | 題 |\n|---|---|---|---|---|---|---|")
    agg = {}
    for c in sorted(cs, key=lambda c: c["id"]):
        act, why = propose(c)
        agg[act.split(":")[0]] = agg.get(act.split(":")[0], 0) + 1
        age = int((now() - c.get("created", 0)) / 86400)
        print("| %s | %s | %s | %dd | `%s` | %s | %s |" % (c["id"], c["type"], c["estate"], age, act, why,
                                                      c["title"].replace("|", "｜")[:90]))
    print("\n処置の内訳: " + " / ".join("%s %d" % kv for kv in sorted(agg.items())))
    return 0


def _board(*args):
    r = subprocess.run([sys.executable, os.path.join(REPO, "Tools", "Session", "edo_board.py")] + list(args),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().split("\n")[0]


def cmd_apply(fp):
    rows = re.findall(r"^\| (EDO-\d{4}) \| \w+ \| [\w-]+ \| \d+d \| `([^`]+)` \|", open(fp, encoding="utf-8").read(), re.M)
    n = 0
    for iid, act in rows:
        c = json.load(open(path_of(iid), encoding="utf-8"))
        if c["status"] not in LIVE:
            continue
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
        elif kind == "split":
            for est in [e for e in arg.split(",") if e]:
                rc, line = _board("post", "--estate", est, "--type", "task", "--owner", est,
                                  "--title", (c["title"].split("(→")[0].strip())[:70],
                                  "--ref", "board:%s" % iid, "--msg", "一斉整理: %s を邸ごとに分けた" % iid)
                print("   " + line)
            c["status"] = "done"; c["log"].append({"t": now(), "by": "triage", "msg": "一斉整理: 邸ごとに分割して閉じた(%s)" % arg})
        else:
            print("? 不明な処置 %s (%s)" % (act, iid)); continue
        c["updated"] = now(); atomic_write_json(c, path_of(iid)); n += 1
        print("%s ← %s" % (iid, act))
    print("実行 %d 件" % n)
    return 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", metavar="MD")
    a = ap.parse_args()
    return cmd_apply(a.apply) if a.apply else cmd_list()


if __name__ == "__main__":
    sys.exit(main())
