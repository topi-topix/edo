#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""検図台帳 — 指摘を巡をまたいで持ち越し、**収束しているか**を機械で数える。

【なぜ要るか】2026-09-01、岡部邸の検図が6巡回っても収束しなかった
(指摘の総数 20 → 20 → 12 → 12 → 12 → 17)。岡部自身の原因調査で
**6巡のあいだに22の新しい観点が持ち込まれた**ことが分かった。
「必須の役割の未達」「木柵が展開図に無い」は1巡目から見られたはずのもので、
⛔ **毎回発明されるので原理的に0件にならない**。

原因は機構にある。検分役(edo-kenzu ほか)は**毎回記憶ゼロで起動する**ので、
分類(a)〜(g)の枠を毎回解釈し直し、前巡で何を見て何が片付いたかを知らない。
枠だけでは収束しない — **具体的な指摘そのものを持ち越す台帳**が要る。

【仕組み】`.git/edo-review/<屋敷>.json`(git 管理外・全 worktree 共有)。
⛔ **指図の json には入れない** — 指摘は巡ごとに数十件出るので、指図に混ぜると
検図関門(review_gate.py)のハッシュが毎巡変わり、検分が即座に無効化される。

    {"items": [
       {"id": "K012", "round": 3, "cat": "c", "text": "断面ヌのCAPが図と食い違う",
        "state": "open", "at": "2026-09-01"}
    ], "rounds": [{"n": 6, "at": "...", "new": 5, "closed": 2, "open": 17}]}

【検分役への効き方】検分役は**まず台帳を読む**。
 ⭕ 既に closed の項目は、その部分が変わっていない限り蒸し返さない
 ⛔ 新しい指摘は `新規` として明示的に足す — **毎巡「新規が何件か」が記録に残る**
 ⭐ **新規が0件になった巡が「収束した」の定義。**総数が0になることではない
   (総数を追うと、直した端から新しい観点が湧いて永遠に終わらない)

【使い方】
    python3 Tools/Sashizu/review_ledger.py okabe                  # 台帳を見る
    python3 Tools/Sashizu/review_ledger.py okabe --open           # 未解決だけ
    python3 Tools/Sashizu/review_ledger.py okabe --add c "断面ヌのCAPが図と食い違う"
    python3 Tools/Sashizu/review_ledger.py okabe --close K012 "是正済(commit abc1234)"
    python3 Tools/Sashizu/review_ledger.py okabe --ref K012 "→ 其十二・nishi_check・nishi.mado.fan"
    python3 Tools/Sashizu/review_ledger.py okabe --round-end      # 巡を締めて収束を判定
    python3 Tools/Sashizu/review_ledger.py --all                  # 全邸の収束の様子

⚠ **台帳は検分の代わりではない。**検分役が見る目を持ち越すための道具で、
   何を指摘するかは検分役が決める。⛔ 台帳に載っていないことを見てはいけない、
   という意味ではない — 新規はいつでも足してよい。ただし**数えられる**。
"""
import json
import os
import re
import subprocess
import sys
import datetime


def _common_git_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run(["git", "-C", here, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    d = r.stdout.strip()
    return d if d else os.path.join(os.path.dirname(os.path.dirname(here)), ".git")


LEDGER = os.path.join(_common_git_dir(), "edo-review")
CATS = {"0": "図と実装のドリフト", "a": "重なり", "b": "廊下と室", "c": "断面",
        "d": "造成", "e": "寸法と作法", "f": "建蔽率", "g": "図面の完備",
        "k": "考証(史実・典拠・確度)", "n": "庭方(庭の成立)", "x": "その他"}
STATES = ("open", "closed", "dropped")


def path_of(name):
    return os.path.join(LEDGER, "%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "_", name))


def load(name):
    try:
        with open(path_of(name), encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.setdefault("items", [])
    d.setdefault("rounds", [])
    return d


def save(name, d):
    os.makedirs(LEDGER, exist_ok=True)
    # ⚠ 非アトミック書き込みは同時に読む他セッションへ壊れた JSON を見せる
    #   (2026-08-31、claim の登録簿で実害が出た)。同じ轍を踏まない。
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=LEDGER, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path_of(name))
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def cur_round(d):
    """いま何巡目か。--round-end を打つまで同じ巡に足され続ける。"""
    return (d["rounds"][-1]["n"] + 1) if d["rounds"] else 1


def next_id(d):
    n = 0
    for it in d["items"]:
        m = re.match(r"K(\d+)$", it.get("id", ""))
        if m:
            n = max(n, int(m.group(1)))
    return "K%03d" % (n + 1)


def cmd_add(name, cat, text):
    if cat not in CATS:
        sys.exit("分類が違う。使えるのは: " + " / ".join("%s=%s" % kv for kv in CATS.items()))
    d = load(name)
    # ⭐ **同じ指摘の言い直しを拾う。**検分役は毎回言葉を変えるので、
    #   素の重複判定(完全一致)では効かない。頭20文字が同じなら候補として警告する。
    head = text[:20]
    dup = [it for it in d["items"] if it["text"][:20] == head]
    if dup:
        print("⚠ 似た指摘が既にある(言い直しなら --close せず既存を使うこと):")
        for it in dup:
            print("   %s [%s] %s — %s" % (it["id"], it["state"], it["text"][:60], it["at"]))
    it = {"id": next_id(d), "round": cur_round(d), "cat": cat,
          "text": text, "state": "open", "at": datetime.date.today().isoformat()}
    d["items"].append(it)
    save(name, d)
    print("足した: %s [%s] %d巡目 %s" % (it["id"], CATS[cat], it["round"], text[:60]))
    return 0


def cmd_close(name, iid, note, state="closed"):
    d = load(name)
    for it in d["items"]:
        if it["id"] == iid:
            it["state"] = state
            it["closed_at"] = datetime.date.today().isoformat()
            if note:
                it["close_note"] = note
            save(name, d)
            print("%s: %s — %s" % (iid, state, note or ""))
            return 0
    sys.exit("その指摘が無い: %s" % iid)


def cmd_ref(name, iid, note):
    """**閉じ書きへ「図に届いた証拠」を追記する**(2026-09-03 ユーザー裁定9=A)。

    ⛔ 上書きしない — 既にある閉じ書きの後ろへ足す。⭕ 追記するのは
      **其◯(図版)・`*_check`(検査)・json のキー**のどれか。`decision_gate.py` がこれを見る。"""
    d = load(name)
    for it in d["items"]:
        if it["id"] == iid:
            cur = it.get("close_note", "")
            if note in cur:
                print("%s: 既に同じ追記がある" % iid)
                return 0
            it["close_note"] = (cur + " " + note).strip()
            save(name, d)
            print("%s: 追記 — %s" % (iid, note))
            return 0
    sys.exit("その指摘が無い: %s" % iid)


def cmd_round_end(name):
    """巡を締める。⭐ **新規が0件なら収束**。総数0ではない。"""
    d = load(name)
    n = cur_round(d)
    mine = [it for it in d["items"] if it["round"] == n]
    new = len(mine)
    closed = len([it for it in d["items"] if it.get("closed_at") and it["state"] == "closed"])
    still = len([it for it in d["items"] if it["state"] == "open"])
    d["rounds"].append({"n": n, "at": datetime.date.today().isoformat(),
                        "new": new, "closed_total": closed, "open": still})
    save(name, d)
    print("%d巡目を締めた — **新規 %d件** / 未解決 %d件 / 通算 closed %d件"
          % (n, new, still, closed))
    if new == 0 and still == 0:
        print("⭕ **収束した。**新規0件・未解決0件。")
    elif new == 0:
        print("⭕ **新しい観点は出尽くした**(新規0件)。残る %d件を潰せば終わる。" % still)
    else:
        print("⚠ **まだ新しい観点が出ている**(新規 %d件)。収束していない。\n"
              "   ⛔ 3巡目以降も新規が出続けるなら、検査の枠そのものが未定義の疑い —\n"
              "      三巡則(docs/session-board.md)に従い `blocker` か `decision` を post して"
              "手を止めること。" % new)
    return 0


def show(name, only_open=False):
    d = load(name)
    if not d["items"] and not d["rounds"]:
        print("⭕ %s: 台帳はまだ空(--add で足す)" % name)
        return 0
    print("── %s  巡 %d / 指摘 %d件(未解決 %d)"
          % (name, cur_round(d) - 1, len(d["items"]),
             len([i for i in d["items"] if i["state"] == "open"])))
    if d["rounds"]:
        print("   収束の様子(新規の件数): "
              + " → ".join("%d巡%d件" % (r["n"], r["new"]) for r in d["rounds"][-8:]))
    for it in d["items"]:
        if only_open and it["state"] != "open":
            continue
        mark = {"open": "⛔", "closed": "⭕", "dropped": "・"}.get(it["state"], "?")
        print("   %s %s [%s] %d巡 %s" % (mark, it["id"], CATS.get(it["cat"], it["cat"]),
                                        it["round"], it["text"][:70]))
    return 0


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "--all":
        names = sorted(f[:-5] for f in os.listdir(LEDGER)) if os.path.isdir(LEDGER) else []
        if not names:
            print("台帳を持つ屋敷はまだ無い")
            return 0
        for n in names:
            d = load(n)
            rs = d["rounds"]
            print("%-18s 巡%-3d 新規の推移 %s  未解決 %d"
                  % (n, len(rs),
                     " ".join(str(r["new"]) for r in rs[-8:]) or "—",
                     len([i for i in d["items"] if i["state"] == "open"])))
        return 0
    name = a[0]
    rest = a[1:]
    if not rest:
        return show(name)
    if rest[0] == "--open":
        return show(name, only_open=True)
    if rest[0] == "--add":
        if len(rest) < 3:
            sys.exit("使い方: <屋敷> --add <分類> <一行の指摘>")
        return cmd_add(name, rest[1], " ".join(rest[2:]))
    if rest[0] == "--close":
        return cmd_close(name, rest[1], " ".join(rest[2:]))
    if rest[0] == "--ref":
        return cmd_ref(name, rest[1], " ".join(rest[2:]))
    if rest[0] == "--drop":
        return cmd_close(name, rest[1], " ".join(rest[2:]), state="dropped")
    if rest[0] == "--round-end":
        return cmd_round_end(name)
    sys.exit("使い方は --help")


if __name__ == "__main__":
    sys.exit(main())
