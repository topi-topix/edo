#!/usr/bin/env python3
"""決定関門 — **決めたことが図に届いているか**を機械で見張る。

【なぜ要るか】2026-09-03 ユーザー裁定9=A。検図・考証・庭方の巡で「決定」を閉じても、
それが**図版にも検査にも設計値にも現れていない**ことが繰り返し見つかった
(K214 廃した小径が刷られ続ける / K215「まだ棟を置かない」が現役 / K229 平面に棟が無い)。
⛔ 台帳の `closed` は「直したつもり」であって「図に届いた」ではない。

【何を見るか】台帳の【…決定…】を含む項のうち `closed` のものについて、
閉じ書き(`close_note`)に**次のどれか**が入っているかを見る:
  ・**其◯**(図版の番号) ・**`*_check`**(検査の名) ・**json のキー**(`nishi.mado.fan` の形)
どれも無ければ「図に届いた証拠が無い」として鳴らす。

⛔ **これは中身の検査ではない** — 参照が書いてあることしか見ない。
   中身が本当に届いているかは検分役と破壊試験の仕事。
⭕ それでも効く: 参照を書こうとした瞬間、書けない決定(=どこにも出ていない決定)が露見する。

【使い方】
    python3 Tools/Sashizu/decision_gate.py okabe
    python3 Tools/Sashizu/decision_gate.py --all
"""
import json
import os
import re
import subprocess
import sys

def _common_git_dir():
    """⚠ worktree から呼ばれるので **共有の .git** を引く(`review_ledger.py` と同じ作法)。"""
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run(["git", "-C", here, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    d = r.stdout.strip()
    return d if d else os.path.join(os.path.dirname(os.path.dirname(here)), ".git")


LEDGER = os.path.join(_common_git_dir(), "edo-review")

# 「図に届いた証拠」と認める形
PAT = [
    re.compile(r"其[一二三四五六七八九十百]+"),          # 図版の番号
    re.compile(r"[A-Za-z_][A-Za-z0-9_]*_check\b"),      # 検査の名
    re.compile(r"`[a-zA-Z_][\w.\[\]*]*`"),               # json のキー(バッククォート)
]


def load(name):
    p = os.path.join(LEDGER, name + ".json")
    if not os.path.exists(p):
        sys.exit("台帳が無い: %s" % p)
    return json.load(open(p, encoding="utf-8"))


def check(name, verbose=True):
    d = load(name)
    bad = []
    n = 0
    for it in d["items"]:
        if "決定" not in it.get("text", ""):
            continue
        if it.get("state") != "closed":
            continue
        n += 1
        note = it.get("close_note", "") or ""
        if not any(p.search(note) for p in PAT):
            bad.append((it["id"], it["text"][:60]))
    if verbose:
        print("── %s  決定の項 %d 件 / 参照なし %d 件" % (name, n, len(bad)))
        for iid, txt in bad:
            print("   ⛔ %s 図に届いた証拠が無い — %s…" % (iid, txt))
        if not bad:
            print("   ⭕ すべての決定が **其◯ / *_check / json のキー** のどれかを指している。")
            print("   ⛔ ただし**参照が書いてあること**しか見ていない — 中身は検分役と破壊試験の仕事。")
    return len(bad)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "--all":
        names = sorted(f[:-5] for f in os.listdir(LEDGER)) if os.path.isdir(LEDGER) else []
        bad = 0
        for nm in names:
            bad += check(nm)
        return 1 if bad else 0
    return 1 if check(a[0]) else 0


if __name__ == "__main__":
    sys.exit(main())
