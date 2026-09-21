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

import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARCELS = os.path.join(ROOT, "docs", "Sashizu", "parcels.json")
TYPO    = os.path.join(ROOT, "docs", "Sashizu", "typology.json")
BUILDER = os.path.join(ROOT, "Assets", "Edo", "Scripts", "Editor", "EdoTypologyBuilder.cs")
# ⭐ 表の欄を**建てる以外の手**で使う道具(地表の輪)。`surface` は地形のスプラットへ塗る欄で、類型ビルダーは
#   駒を置くだけなので読まない — 使い手が別のファイルにいても「使われている」と数える(EDO-0319)。
#   ⛔ 増やすときは、そのファイルが**表の欄名を `.欄` で引いて実際に効かせている**ことを確かめてから。
CONSUMERS = [os.path.join(ROOT, "Assets", "Edo", "Scripts", "Editor", "EdoSurfacePaint.cs")]


def read_keys():
    """類型ビルダーが**実際に読む**欄の名。⛔ 手で写した一覧にしない — 写しはビルダーが
    変わった日にそのまま嘘になる。ソースの `S(d,"…")` / `I(d,"…",…)` / `Bo(d,"…",…)` を引く。"""
    if not os.path.exists(BUILDER):
        return None
    src = open(BUILDER, encoding="utf-8").read()
    return set(re.findall(r'\b[SIB]o?\(\s*d\s*,\s*"([^"]+)"', src))


def read_but_unused():
    """ビルダーが **Spec へ読み込みはするのに、一度も使っていない**欄。
    ⭐ `inert_defaults` の裏返しで、こちらの方が見つけにくい — 表にも欄があり C# も読んでいるので
    「効いている」ように見えるのに、建てる側が参照しないので姿は変わらない(`inari` が実際にそう)。
    ⛔ 0 件でも「合格」ではない: 参照していても**使い道が間違っている**のはここでは捕まらない。"""
    if not os.path.exists(BUILDER):
        return None
    src = open(BUILDER, encoding="utf-8").read()
    out = []
    for field, key in re.findall(r'\b(\w+)\s*=\s*[SIB]o?\(\s*d\s*,\s*"([^"]+)"', src):
        # 宣言 1 回 + この読み込みの左辺 1 回を引いた残りが、その欄の**使われ方**。
        # ⛔ C# の欄名と json の鍵名が同じとき(`inari`)は**鍵の文字列そのもの**も数に入るので
        #    もう 1 回引く — これを忘れて 2026-09-21 に `inari` を取り逃がした。
        minus = 3 if field == key else 2
        uses = len(re.findall(r"\b%s\b" % re.escape(field), src)) - minus
        for cp in CONSUMERS:   # 別ファイルの使い手は `.欄` の参照だけ数える(宣言ではあり得ない)
            if os.path.exists(cp):
                uses += len(re.findall(r"\.%s\b" % re.escape(field), open(cp, encoding="utf-8").read()))
        if uses <= 0:
            out.append(key)
    # ⭕ 典拠(`source`)と史料値(`koku`)は姿を決めない欄なので、破れの列から外して別に刷る。
    #   ⛔ 黙って落とさない — 落とした事実も毎回刷る(規則19)。
    return sorted(set(out) - NOT_SHAPE)


# ⭕ **建つ姿に効かなくて当たり前の欄。**典拠と史料値は姿を決めず、決めてはいけない —
#   `source` は値の出どころ、`koku` は格帯(`rank`)を裏づける史料値で、石高から棟数を引く鎖は
#   史料で切れている(docs/typology-builder.md §4「附属の種別」)。⛔ この集合を静かに増やさない:
#   増やすほど「効かない欄」が正当化され、EDO-0304 と同じ沈黙に戻る。増やすなら理由をここへ書く。
NOT_SHAPE = {"source", "koku"}


def unread_fields(T):
    """**区画に書いてあるのに、ビルダーがその名を一度も読まない欄。**
    ⭐ 第三の盲点(EDO-0317・2026-09-21)。`inert_defaults` は `defaults` の側しか見ず、
    `read_but_unused` は「読んでから使わない」欄しか見ないので、**区画にだけ在る欄**は
    どちらの網にも掛からない — `kamiyui`(髪結床・24区画)`tanagari`(店借)`hoshiba`(干場)
    `tokinokane`(時の鐘)がそうで、史料から起こして書き込んだのに誰も建てていなかった。
    ⛔ 破れ(赤)にしない: 部材が無くて建てられない欄もある。ここは「見えるようにする」係。"""
    read = read_keys()
    if read is None:
        return None
    seen = {}
    for pid, e in (T.get("parcels") or {}).items():
        if not isinstance(e, dict) or e.get("built") == "hand":
            continue
        for k in e:
            if k.startswith("_") or k in ("cert", "source", "note") or k in read:
                continue
            seen.setdefault(k, []).append(pid)
    return sorted(seen.items(), key=lambda kv: (-len(kv[1]), kv[0]))


def inert_defaults(T):
    """`defaults` にあってビルダーが読まない欄。⭐ これが EDO-0304 の正体 — 表へ欄を足しても
    C# が読んでいなければ**建つ姿は一切変わらない**のに、表を見た者には効いているように見える。
    ⛔ 破れ(赤)にはしない: 既に居る欄の是非は考証方と部材方の持ち場で、ここは「見えるようにする」係。"""
    read = read_keys()
    if read is None:
        return None
    keys = set()
    for branch in (T.get("defaults") or {}).values():
        if not isinstance(branch, dict):
            continue
        leaves = [v for v in branch.values() if isinstance(v, dict)] or [branch]
        for leaf in leaves:
            keys |= {k for k in leaf if not k.startswith("_") and k != "src"}
    return sorted(keys - read)

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
            if k == "yashiki" and e.get("rank") != "daimyo":
                # ⛔ 上/中/下を冠するのは**大名だけ**。旗本・御家人には付かない(考証方 2026-09-21・EDO-0311 ②)。
                #   同時代の一括記録は同じ記事の中で大名にだけ「上 岡部筑前守殿」「中 鳥居丹波守殿」と
                #   屋敷の別を冠し、旗本には「御小姓組 村瀬平四郎殿」と役名を冠して別を書かない
                #   [安政地震被害書上 J1400016]S。切絵図の悉皆でも旗本の第二の屋敷は「抱屋敷」で
                #   「下屋敷」とは書かれない([江戸マップ地名データセット]A 悉皆7例)。
                #   ⚠ **「旗本は上屋敷を持たない」とは書かない** — 辞典は「拝領居屋敷=上屋敷」の
                #   類別を旗本・御家人へも及ぼす([世界大百科事典『武家屋敷』鈴木充]A)。両立する:
                #   概念上の類別名であって、実務の記載では屋敷の別を冠さない。
                if "yashiki" in e:
                    bad.append((i, "大名でないのに yashiki(上/中/下)が付いている — "
                                   "屋敷の別を冠するのは大名だけ(類別としての『拝領居屋敷』は source へ書く)"))
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
    T = json.load(open(TYPO)) if os.path.exists(TYPO) else None
    inert = inert_defaults(T) if T else None
    unused = read_but_unused()
    unread = unread_fields(T) if T else None
    if a.list_p:
        for s in pcert:
            print(s)
        return
    if a.json:
        print(json.dumps({"bad": [{"parcel": p, "why": w} for p, w in bad],
                          "inert_defaults": inert, "read_but_unused": unused,
                          "unread_fields": {k: v for k, v in (unread or [])},
                          "not_shape": sorted(NOT_SHAPE)},
                         ensure_ascii=False)); return
    # ⭐ 破れが 0 件でも必ず刷る(規則19)— 「既定を足したのに効かない」は赤ではなく沈黙で来る。
    if inert:
        print("  ⚠ defaults の欄 %d 個を類型ビルダーが読まない — 足しても建つ姿は変わらない: %s"
              % (len(inert), "・".join(inert)))
    if unused:
        print("  ⚠ 欄 %d 個はビルダーが読むのに一度も使っていない — 値を入れても姿は変わらない: %s"
              % (len(unused), "・".join(unused)))
    if unread:
        print("  ⚠ 欄 %d 個は区画に書いてあるのにビルダーが読みもしない — 史料から起こした値が誰にも建てられていない: %s"
              % (len(unread), "・".join("%s(%d区画)" % (k, len(v)) for k, v in unread)))
    # ⭕ 除外した欄も名指しで刷る(規則19 — 黙って緩めた検査は「合格」に見える)。
    #   ⛔ `--quiet`(挨拶フック)で破れも ⚠ も無いときだけ黙る — 毎回の固定費にしない。
    if not a.quiet or inert or unused or unread:
        print("  ⭕ 建つ姿に効かなくて当たり前の欄(意図して除外)= %s" % "・".join(sorted(NOT_SHAPE)))
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
