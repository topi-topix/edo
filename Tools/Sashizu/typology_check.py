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
# ⭕ 区画の実欄でない cert の鍵として許すのはこの三つだけ(区画そのものの素性に掛かる確度)。
#   ⛔ 増やさない — 増やすほど「確度が何に掛かるか」が曖昧になる(掲示板 EDO-0311 ③)。
CERT_META = {"name", "haishaku", "azukari"}
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
    pcert = []          # この表で使ってはいけない確度 P の欄(下でまとめて 1 行にする)
    parcels = json.load(open(PARCELS))["parcels"]
    ids  = [p["id"] for p in parcels]
    cats = {p["id"]: p.get("category") for p in parcels}
    if not os.path.exists(TYPO):
        return [("表が無い", "docs/Sashizu/typology.json が無い — 類型ビルダーは一区画も建てられない")], []
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
            if k == "yashiki" and e.get("rank") == "gokenin":
                # ⛔ 上/中/下は**大名の屋敷の別**で、御家人の拝領屋敷には付かない
                #   (考証方・掲示板 EDO-0311 ④)。付いていたら逆に鳴らす。
                if "yashiki" in e:
                    bad.append((i, "御家人なのに yashiki(上/中/下)が付いている — あれは大名の屋敷の別"))
                continue
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
                elif v == "P":
                    pcert.append(f"{i}.{k}")
                # ⛔ **確度が何に掛かるか定まらない**のを許さない(掲示板 EDO-0311 ③)。
                #   実在しない欄名に確度を付けると、読み手はどの値の話か分からず、
                #   直しようも無い(azukarichi_yl と tamachi5east_kaishopoly に composition が在った)。
                if k not in e and k not in CERT_META:
                    bad.append((i, f"cert.{k} は実在しない欄 — 実欄か {'/'.join(sorted(CERT_META))} のどれかにする"))
        # ⛔ 同じことを二つの欄で言わない — 門の型と山門の有無が食い違うと**二重に建つ**
        #   (観理院で実際に起きた・EDO-0311 ⑤)
        if t == "jisha" and "sanmon" in e and bool(e.get("sanmon")) != (e.get("gate") == "sanmon"):
            bad.append((i, f"gate={e.get('gate')} と sanmon={e.get('sanmon')} が食い違う — 山門が二重に建つ"))
        if not e.get("source"):
            bad.append((i, "source が無い — 値の出どころを書く(規則7)"))
        # 区画の category と類型の type が食い違うなら、source で断ってあること
        want = {"buke": "buke", "machiya": "machiya", "jisha": "jisha", "kouyuu": "kouyuu"}
        if cats.get(i) in want and want[cats[i]] != t and "⚠" not in (e.get("source") or ""):
            bad.append((i, f"区画は {cats[i]} なのに類型は {t} — 食い違いを source に ⚠ で断る"))

    # 確度 P は「当方が測った・算出した値」で、類型の既定値ではない(規則7・sources.md)。
    # 文献から導かれる型は B、当方が地形や接道から推したものは U。⛔ 欄ごとに 1 件ずつ並べない —
    # 数が多いと本物の破れが埋もれる。1 行にまとめ、振り直しが済めば自然に消える。
    if pcert:
        bad.append(("(表ぜんたい)",
                    "cert に P が %d 欄(%d 区画)— P は当方の実測・算出で類型の既定値ではない。"
                    "B(文献の型)か U(当方の推論)へ振り直す。振り分けは考証方の持ち場 → 掲示板 EDO-0255。"
                    "内訳は `--list-p`" % (len(pcert), len({s.split(".")[0] for s in pcert}))))
    return bad, pcert

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="破れがある時だけ書く(挨拶フック用)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list-p", action="store_true",
                    help="確度 P のまま残っている欄を並べる(B/U へ振り直す対象・EDO-0255)")
    a = ap.parse_args()
    bad, pcert = check()
    if a.list_p:
        for s in pcert:
            print(s)
        return
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
