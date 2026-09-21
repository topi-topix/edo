#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""検査の差分 — **その巡で触った物から、要る検査項目と「測らない項目」を機械で決める。**

【なぜ要るか】2026-09-21、施主から「この時間の長さは開発速度のボトルネックでは」と問われた。
岡部の外周の隅しか触っていない巡で、普請検査は10項目すべてとレンダ3点を回して **29分** かかった。
隅を動かして変わり得るのは境界・接地・隙・門の取り合いだけで、建蔽率も池も地形の副作用も、
**前の巡から一つも動いていない値を測り直していた**。

⛔ **これは「検査を省く」道具ではない。**CLAUDE.md 規則19「輪に入っていない値は**未検査**であって
**合格ではない**」がそのまま効く。省いた項目は報告の表に **未検査** の行として必ず出し、
完成条件の表(`kansei_gate.py --record`)へは **その巡で実際に測った欄しか**書かない。
⭕ だから本ツールは「測る項目」と**同時に**「未検査として報告する項目」を刷る。片方だけ使わない。

⛔ **地形・造成を触った巡は差分にできない。**地形が動くと全駒の接地・池・境界が同時に動く
(規則3「面の高さは地形が決める」)。`--touched 地形` を渡すと全項目に戻る。

⛔ **完成の一巡は差分にしない。**`kansei_gate.py` の表を閉じる巡と、施主へ見せる巡は
全項目 + レンダ。`--full` を渡すか `--touched` を省く。

【使い方】
    python3 Tools/Sashizu/qa_scope.py --touched 外周 隅           # 要る項目と未検査の項目を刷る
    python3 Tools/Sashizu/qa_scope.py --touched 棟 --estate okabe # 邸を添えると書き戻せる欄も出る
    python3 Tools/Sashizu/qa_scope.py --list                      # 触った物の名前の一覧
    python3 Tools/Sashizu/qa_scope.py --full                      # 全項目(完成の一巡・見せる前)
    python3 Tools/Sashizu/qa_scope.py --touched 外周 --json       # 検査役へ渡す形

正典の表は `docs/Sashizu/qa_scope.json`。項目の中身は `unity-buke-yashiki/references/qa-and-pitfalls.md`。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABLE = os.path.join(ROOT, "docs", "Sashizu", "qa_scope.json")


def load():
    with open(TABLE, encoding="utf-8") as f:
        return json.load(f)


def resolve(tbl, touched):
    """触った物の名前 → (要る項目の番号, 差分にできない理由)。"""
    items, why, unknown = set(), [], []
    for name in touched:
        hit = None
        for key, ent in tbl["触った物"].items():
            if name == key or name in ent.get("別名", []):
                hit = (key, ent)
                break
        if hit is None:
            unknown.append(name)
            continue
        key, ent = hit
        if ent.get("全項目"):
            why.append("%s: %s" % (key, ent["全項目"]))
            items |= set(int(k) for k in tbl["項目"])
        else:
            items |= set(ent["項目"])
    return sorted(items), why, unknown


def kansei_columns(tbl, items):
    """測った項目から、完成条件の表へ書き戻してよい欄を引く。
    ⛔ 欄が要求する項目が**一つでも**欠けたら、その欄は書き戻せない(部分的な pass を作らない)。"""
    ok = []
    for col, need in tbl["完成条件の欄"].items():
        if set(need) <= set(items):
            ok.append(col)
    return ok


def main():
    ap = argparse.ArgumentParser(description="検査の差分 — 触った物から要る検査項目を決める")
    ap.add_argument("--touched", nargs="*", default=[], help="この巡で触った物(--list で名前の一覧)")
    ap.add_argument("--estate", help="邸(完成条件の表の欄を併せて刷る)")
    ap.add_argument("--full", action="store_true", help="全項目(完成の一巡・施主へ見せる前)")
    ap.add_argument("--list", action="store_true", help="触った物の名前の一覧")
    ap.add_argument("--json", action="store_true", help="json で刷る(検査役へ渡す形)")
    a = ap.parse_args()
    tbl = load()

    if a.list:
        print("触った物の名前(--touched に渡す):")
        for key, ent in tbl["触った物"].items():
            alias = ("／" + "・".join(ent["別名"])) if ent.get("別名") else ""
            tail = ent["全項目"] if ent.get("全項目") else "項目 " + "・".join("#%d" % i for i in ent["項目"])
            print("  %-10s%-22s %s" % (key, alias, tail))
        return 0

    allitems = sorted(int(k) for k in tbl["項目"])
    if a.full or not a.touched:
        items, why, unknown = allitems, ["全項目(--full / --touched 無し)"], []
    else:
        items, why, unknown = resolve(tbl, a.touched)

    if unknown:
        print("⛔ 知らない名前: %s — `--list` で確かめること。"
              "**名前が引けないときは差分にしない**(全項目へ戻す)" % "・".join(unknown), file=sys.stderr)
        items = allitems
        why.append("知らない名前があったので全項目へ戻した")

    skipped = [i for i in allitems if i not in items]
    cols = kansei_columns(tbl, items)

    if a.json:
        print(json.dumps({
            "触った物": a.touched, "測る項目": items, "未検査で報告する項目": skipped,
            "書き戻してよい欄": cols, "全項目に戻した理由": why,
            "項目名": {str(i): tbl["項目"][str(i)] for i in allitems},
        }, ensure_ascii=False, indent=2))
        return 0

    print("触った物: %s" % ("・".join(a.touched) if a.touched else "(指定なし → 全項目)"))
    for w in why:
        print("  ⚠ %s" % w)
    print("\n⭕ この巡で測る項目 %d 件:" % len(items))
    for i in items:
        print("   #%-3d %s" % (i, tbl["項目"][str(i)]))
    if skipped:
        print("\n⛔ 測らない項目 %d 件 — **報告の表に「未検査」の行として必ず出す。"
              "合格と書かない・黙って消さない**(規則19):" % len(skipped))
        for i in skipped:
            print("   #%-3d %s" % (i, tbl["項目"][str(i)]))
    print("\n完成条件の表(kansei_gate.py --record)へ書き戻してよい欄: %s"
          % ("・".join(cols) if cols else "無し(この巡では一つも閉じられない)"))
    if skipped:
        print("⛔ 上に出ていない欄は**据え置き**。前の巡の pass をこの巡の根拠にしない。")
    print("\n⛔ 施主へ見せる巡と完成を閉じる巡は差分にしない — `--full` で全項目 + 検証レンダ3点。")
    if a.estate:
        print("\n今の表: python3 Tools/Sashizu/kansei_gate.py %s" % a.estate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
