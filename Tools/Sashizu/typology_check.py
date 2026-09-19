#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""類型表の関門 — docs/Sashizu/typology.json が区画の正典と噛み合っているかを機械で見張る。

⭐ **狙い。**類型表には指図が無く、検分の輪も一括で一度きり(docs/typology-builder.md §2)。
だから「表の欄が抜けた」「区画が増えたのに表に載っていない」を捕まえる目が**ここにしか無い**。
⛔ 0 件は「合格」ではなく「この型では捕まらなかった」— 値が史実として正しいかは考証方の持ち場、
建った姿が正しいかは建ててみる輪の持ち場(規則19・docs/verification-loops.md)。

    python3 Tools/Sashizu/typology_check.py            # 一覧
    python3 Tools/Sashizu/typology_check.py --quiet    # 破れがある時だけ鳴る(挨拶フックが呼ぶ)
    python3 Tools/Sashizu/typology_check.py --json
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARCELS = os.path.join(ROOT, "docs", "Sashizu", "parcels.json")
TYPO    = os.path.join(ROOT, "docs", "Sashizu", "typology.json")

CERT = set("SABPU")
TYPES = {"buke", "machiya", "jisha", "kouyuu"}
GATES = {"kmon", "nagayamon", "hmon", "kabukimon", "munemon", "yakuimon", "sanmon", "komon", None}
ENCL  = {"nagaya", "nagaya_front+ita", "ita", "dobei", "ita+ikegaki", "ishigaki+hei", "yarai", None}
DIRS  = {"N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW",None}
NEED = {
    "buke":    ["yashiki", "rank", "gate", "enclosure", "kura"],
    "machiya": ["two_sided", "pattern"],
    "jisha":   ["kind", "gate", "enclosure"],
    "kouyuu":  ["kind", "surface", "fence"],
}

def check():
    bad = []
    parcels = json.load(open(PARCELS))["parcels"]
    ids  = [p["id"] for p in parcels]
    cats = {p["id"]: p.get("category") for p in parcels}
    if not os.path.exists(TYPO):
        return [("表が無い", "docs/Sashizu/typology.json が無い — 類型ビルダーは一区画も建てられない")]
    T = json.load(open(TYPO))
    tp = T.get("parcels", {})

    for i in ids:
        if i not in tp:
            bad.append((i, "区画の正典にあるのに類型表に無い — この区画は誰にも建てられない"))
    for i in tp:
        if i not in ids:
            bad.append((i, "類型表にあるのに区画の正典に無い — 区画が消されたか id の綴り違い"))

    for i in ids:
        e = tp.get(i)
        if not e:
            continue
        if e.get("built") == "hand":
            if not e.get("note"):
                bad.append((i, "built:hand なのに、なぜ生成対象外かの一行が無い"))
            continue
        t = e.get("type")
        if t not in TYPES:
            bad.append((i, f"type が無いか未知({t})")); continue
        for k in NEED[t]:
            if k not in e:
                bad.append((i, f"{t} に要る欄 {k} が無い"))
        if e.get("gate") not in GATES:
            bad.append((i, f"門の型 {e.get('gate')} は語彙に無い(EdoAssets に部材が無い)"))
        if t != "kouyuu" and e.get("enclosure") not in ENCL:
            bad.append((i, f"囲いの型 {e.get('enclosure')} は語彙に無い"))
        if e.get("front") not in DIRS:
            bad.append((i, f"front {e.get('front')} は8方位でない(辺番号も座標も書かない・規則5)"))
        c = e.get("cert")
        if not isinstance(c, dict) or not c:
            bad.append((i, "cert が無い — 推定を既成事実にしない(規則7)"))
        else:
            for k, v in c.items():
                if v not in CERT:
                    bad.append((i, f"cert.{k}={v} は S/A/B/P/U でない"))
        if not e.get("source"):
            bad.append((i, "source が無い — 値の出どころを書く(規則7)"))
        # 区画の category と類型の type が食い違うなら、source で断ってあること
        want = {"buke": "buke", "machiya": "machiya", "jisha": "jisha", "kouyuu": "kouyuu"}
        if cats.get(i) in want and want[cats[i]] != t and "⚠" not in (e.get("source") or ""):
            bad.append((i, f"区画は {cats[i]} なのに類型は {t} — 食い違いを source に ⚠ で断る"))
    return bad

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="破れがある時だけ書く(挨拶フック用)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    bad = check()
    if a.json:
        print(json.dumps([{"parcel": p, "why": w} for p, w in bad], ensure_ascii=False)); return
    if not bad:
        if not a.quiet:
            n = len(json.load(open(TYPO)).get("parcels", {}))
            print(f"⭕ 類型表 — {n} 区画すべてが区画の正典と噛み合っている(値が史実かは考証方の持ち場)")
        return
    print("類型表の関門 — **破れ %d 件**(`python3 Tools/Sashizu/typology_check.py`)" % len(bad))
    for p, w in bad[:20]:
        print(f"  ⛔ {p:28s} {w}")
    if len(bad) > 20:
        print(f"  … ほか {len(bad)-20} 件")
    sys.exit(0)

main()
