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
    python3 Tools/Sashizu/decision_gate.py --selftest   # ⛔ 落ちたらこの関門の検出が死んでいる(docs/verification-loops.md)
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


def load(name, ledger=None):
    p = os.path.join(ledger or LEDGER, name + ".json")
    if not os.path.exists(p):
        sys.exit("台帳が無い: %s" % p)
    return json.load(open(p, encoding="utf-8"))


def check(name, verbose=True, ledger=None):
    d = load(name, ledger)
    bad = []
    n = 0
    for it in d["items"]:
        if not re.search(r"決定|裁定|答え", it.get("text", "")):
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


def selftest():
    """⛔ 落ちたら**この関門の検出が死んでいる**。台帳でなく道具を疑うこと(関門には自己検査・2026-09-13)。"""
    import tempfile
    import shutil
    d = tempfile.mkdtemp(prefix="decision-")
    ng = 0
    try:
        def ledger(items):
            json.dump({"items": items}, open(os.path.join(d, "fx.json"), "w", encoding="utf-8"), ensure_ascii=False)
            return check("fx", verbose=False, ledger=d)
        ok = [{"id": "K1", "text": "【裁定】決定: 小径を廃す", "state": "closed", "close_note": "其三から消した"},
              {"id": "K2", "text": "【決定】棟を置かない", "state": "closed", "close_note": "roof_check を足した"},
              {"id": "K3", "text": "【決定】窓を扇に", "state": "closed", "close_note": "`nishi.mado.fan` に入れた"},
              {"id": "K4", "text": "【決定】まだ開いている", "state": "open", "close_note": ""},
              {"id": "K5", "text": "ただの指摘", "state": "closed", "close_note": "直した"}]
        n = ledger(ok)
        print("%s 健全な台帳(其◯ / *_check / json のキー・未決・決定でない項)では鳴らない" % ("⭕" if n == 0 else "⛔"))
        ng += n != 0
        cases = [("参照の無い閉じ書き", "直したつもり"), ("空の閉じ書き", ""),
                 ("バッククォート無しのキー", "nishi.mado.fan に入れた")]
        for title, note in cases:
            n = ledger([{"id": "K9", "text": "【決定】x", "state": "closed", "close_note": note}])
            print("%s %s → %s" % ("⭕" if n == 1 else "⛔", title, "鳴らした" if n == 1 else "**鳴らなかった**"))
            ng += n != 1
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("⭕ 自己検査 全通" if not ng else "⛔ 自己検査 %d 件失敗 — この関門の検出が死んでいる。台帳が 0 件でも合格の意味を持たない" % ng)
    return 1 if ng else 0


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "--selftest":
        return selftest()
    if a[0] == "--all":
        names = sorted(f[:-5] for f in os.listdir(LEDGER)) if os.path.isdir(LEDGER) else []
        bad = 0
        for nm in names:
            bad += check(nm)
        return 1 if bad else 0
    return 1 if check(a[0]) else 0


if __name__ == "__main__":
    sys.exit(main())
