#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""検図関門 — 指図が「誰に検められたか」を機械で見張る。

【なぜ要るか】2026-09-01、松江松平邸の庭が**庭方(edo-niwashi)に一度も検められないまま
Stage7 まで実装され**、ユーザーから「この指図でよいとは全く思っていない」と差し戻された。
検図(kenzu)と考証(kosho)は通していたが、**庭の良し悪しを見る目は通していなかった**。
CLAUDE.md のルーティング表に edo-niwashi は載っていたのに、**通さなくても何も起きなかった**
のが原因。⛔ 散文の規則は破れる。関門は機械にする。

さらに同じ日、庭の**再設計**を指図方(edo-sashizukata)へ回しかけてユーザーに止められた。
指図方は「意匠上の判断はしない・書き起こすだけ」の役で、庭を設計する能力はない。
⭕ 正しい順は **庭方が設計 → 指図方が数値へ書き起こす → 検図・考証・庭方が検める**。

【仕組み】各 `docs/Sashizu/<屋敷>_sashizu.json` の直下に `reviews` を置く:

    "reviews": {
      "kenzu":   {"at": "2026-08-23", "verdict": "pass", "hash": "<16桁>", "note": "..."},
      "kosho":   {"at": "2026-08-31", "verdict": "pass", "hash": "<16桁>"},
      "niwashi": {"at": "2026-09-01", "verdict": "fail", "hash": "<16桁>", "note": "..."}
    }

・**誰が要るか**は指図の中身から決まる(庭があれば庭方が要る)。名簿を人が書き足す必要はない
・`hash` は**その検分が見た範囲の中身**の指紋。指図を書き換えると hash がずれ、
  検分は自動で **stale(検め直しが要る)** になる。⛔ 通ったことにして先へ進めない
・検分役は read-only なので自分で書けない。**呼んだ側(本文脈)が結果を書き戻す**義務がある

【使い方】
    python3 Tools/Sashizu/review_gate.py              # 全邸の関門を見る(赤があれば exit 1)
    python3 Tools/Sashizu/review_gate.py matsudaira_dewa
    python3 Tools/Sashizu/review_gate.py --record matsudaira_dewa niwashi fail "庭の主景と園路が無い"
    python3 Tools/Sashizu/review_gate.py --quiet     # 赤の要約だけ(セッション開始の挨拶用)

⛔ **関門が赤の指図を実装しない。赤のシーンをユーザーに見せない。**

⚠ **【移行期間】2026-09-01 ユーザー裁定(案B)。** この関門は 2026-09-01 の新設で、
全6邸が赤で立ち上がった(赤17件)。⛔ 全員を即時停止させない — 赤の大半は
「関門が新しくて記録が無い」だけで、土井は検図14巡・岡部は検図12巡を実際に通している。
  ⭕ 検分を通すまで、従来どおり作業を続けてよい(実装・指図の改訂とも)
  ⛔ ただし**新たにユーザーへ見せる前には必ず通す**(裁定を仰ぐ・レンダを出す・
     指図の Artifact を案内する、のすべて)。ここが移行中も動かない一線
  ⛔ 「記録が無い」は「通していない」ではない。⛔ それでも遡って pass を書かない
     (過去の検分はいまの指図を見ていない)
正典: CLAUDE.md 絶対規則18 / 展開は EDO-0099。
"""
import json
import os
import sys
import hashlib
import collections

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(REPO, "docs", "Sashizu")

# 検分役 → (日本語名, その役が見る範囲のキー, いつ要るか)
#   keys=None は「指図全体」。required は指図の中身を受け取って True/False を返す
REVIEWERS = collections.OrderedDict([
    ("kenzu", dict(
        label="検図(edo-kenzu)",
        keys=None,
        why="図として成立しているか(重なり・断面・造成・柱割り・建蔽率)",
        required=lambda d: True)),
    ("kosho", dict(
        label="考証(edo-kosho)",
        keys=None,
        why="史実・典拠・確度",
        required=lambda d: True)),
    ("niwashi", dict(
        label="庭方(edo-niwashi)",
        keys=["gardens", "planting", "plantRule", "tenkei",
              "slopeArea", "slopePlanting", "routes"],
        why="庭が庭として成立しているか(主景・見所・園路・作庭の作法・植栽の時代考証)",
        required=lambda d: _needs_niwashi(d))),
])


# ⚠ **キーの有無だけで判定しない**(2026-09-01 松平セッションの指摘)。
#   「庭・植栽・点景のどれかがあれば」だけだと、**庭の実体はあるのに点景しか書いていない
#   段階の指図**で要求が立たない — 一番検分が要る時期に関門がすり抜ける。
#   ⭕ 「この敷地に庭があるか」を、書きかけでも拾える手がかりから判断する。
_NIWA_HINTS = ("gardens", "planting", "plantRule", "tenkei", "slopePlanting", "slopeArea")
# 棟・郭・区域の**名前**に現れる、庭の存在を示す語(書きかけでも拾える)
#   ⛔ 「池」は入れない — 外堀の題「溜**池**堰下流」のような**地名**を拾ってしまう。
#      庭の池は「泉水」「主庭」など別の語で必ず現れるので、取りこぼしにはならない。
_NIWA_WORDS = ("庭", "泉水", "築山", "露地", "茶室", "稲荷", "園路", "枯山水")


def _walk_names(o):
    """指図の中の**名前らしい値**だけを辿る。題・説明文・典拠の引用は見ない
    (⚠ 本文まで見ると『溜池』のような地名や、史料の引用文で誤検出する)。"""
    if isinstance(o, dict):
        for k, v in o.items():
            if k.startswith("_"):
                continue
            if k in ("name", "ja", "label", "title") and isinstance(v, str):
                yield v
            else:
                for x in _walk_names(v):
                    yield x
    elif isinstance(o, list):
        for v in o:
            for x in _walk_names(v):
                yield x


def _needs_niwashi(d):
    """庭方が要るか。⚠ **キーの有無だけで決めない**(2026-09-01 松平セッションの指摘)—
    「庭の実体はあるのに点景しか書いていない段階」で要求が立たず、
    一番検分が要る時期に関門がすり抜ける。"""
    # ① 庭まわりのキーが1つでも埋まっていれば要る
    if any(d.get(k) for k in _NIWA_HINTS):
        return True
    # ② キーが空でも、棟・郭・区域の**名前**に庭を示す語があれば要る
    #    ⛔ title は除く(「溜池堰下流 外堀 掘り直し指図」で誤検出するため)
    for nm in _walk_names({k: v for k, v in d.items() if k != "title"}):
        if any(w in nm for w in _NIWA_WORDS):
            return True
    return False

VERDICTS = ("pass", "fail", "advisory")


def fingerprint(doc, keys):
    """検分が見た範囲の指紋。⚠ `_` で始まる注記のキーは**除く** —
    文章を直しただけで検め直しを要求すると、関門がすぐ形骸化する。"""
    if keys is None:
        src = {k: v for k, v in doc.items() if not k.startswith("_")}
    else:
        src = {}
        for k in keys:
            if k in doc:
                src[k] = doc[k]
    blob = json.dumps(src, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def estates():
    out = []
    for f in sorted(os.listdir(DOC)):
        if f.endswith("_sashizu.json"):
            out.append(f[:-len("_sashizu.json")])
    return out


def gate(name):
    """1邸の関門。返すのは (赤の件数, 行の列)。"""
    path = os.path.join(DOC, name + "_sashizu.json")
    with open(path) as fp:
        doc = json.load(fp)
    rev = doc.get("reviews") or {}
    rows, red = [], 0
    for key, spec in REVIEWERS.items():
        if not spec["required"](doc):
            continue
        want = fingerprint(doc, spec["keys"])
        got = rev.get(key)
        if not got:
            # ⚠ **「通していない」と書かない。** この関門は 2026-09-01 に新設したので、
            #   それ以前の検分は記録されていないだけで、実際には通している邸がある
            #   (土井=検図14巡・考証13巡 / 岡部=検図12巡)。事実と食い違う非難を機械が
            #   出すと、正しく回してきた邸ほど関門を信用しなくなる。
            #   ⭕ ただし「改めて通す必要がある」という結論は変わらない — 過去の検分は
            #      いまの指図を見ていないので、記録を遡って書いてはならない。
            rows.append(("⛔", key, spec["label"], "**記録が無い**(関門は 2026-09-01 新設)",
                         spec["why"] + " ／ 過去に通していても、いまの指図を見た検分が要る"))
            red += 1
            continue
        verdict = got.get("verdict")
        at = got.get("at", "?")
        if verdict == "fail":
            rows.append(("⛔", key, spec["label"], "不合格(%s)" % at, got.get("note", "")))
            red += 1
        elif got.get("hash") != want:
            rows.append(("⚠", key, spec["label"],
                         "検め直しが要る — %s に通ったあと指図が変わった" % at,
                         "記録 %s / いま %s" % (got.get("hash", "—"), want)))
            red += 1
        elif verdict == "advisory":
            rows.append(("・", key, spec["label"], "助言のみ(%s)" % at, got.get("note", "")))
        elif verdict == "pass":
            rows.append(("⭕", key, spec["label"], "通っている(%s)" % at, ""))
        else:
            rows.append(("⛔", key, spec["label"], "verdict が読めない: %r" % verdict, ""))
            red += 1
    return red, rows


def record(name, key, verdict, note):
    if key not in REVIEWERS:
        sys.exit("検分役が違う。使えるのは: " + " / ".join(REVIEWERS))
    if verdict not in VERDICTS:
        sys.exit("verdict は " + " / ".join(VERDICTS))
    path = os.path.join(DOC, name + "_sashizu.json")
    with open(path) as fp:
        doc = json.load(fp, object_pairs_hook=collections.OrderedDict)
    import datetime
    doc.setdefault("_reviews", (
        "**検図関門。**この指図を誰が検めたか。⛔ 呼んだ側(本文脈)が結果を書き戻す — "
        "検分役は read-only で自分では書けない。`hash` はその検分が見た範囲の指紋で、"
        "指図を書き換えるとずれ、検分は自動で『検め直しが要る』になる。"
        "見張りは `python3 Tools/Sashizu/review_gate.py`。"
        "⛔ 関門が赤の指図を実装しない・赤のシーンをユーザーに見せない。"))
    rv = doc.setdefault("reviews", collections.OrderedDict())
    rv[key] = collections.OrderedDict([
        ("at", datetime.date.today().isoformat()),
        ("verdict", verdict),
        ("hash", fingerprint(doc, REVIEWERS[key]["keys"])),
        ("note", note or ""),
    ])
    with open(path, "w") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("記録: %s / %s = %s" % (name, REVIEWERS[key]["label"], verdict))


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--record":
        if len(argv) < 4:
            sys.exit("使い方: --record <屋敷> <検分役> <pass|fail|advisory> [一言]")
        record(argv[1], argv[2], argv[3], " ".join(argv[4:]))
        return
    quiet = "--quiet" in argv
    names = [a for a in argv if not a.startswith("--")] or estates()
    total = 0
    lines = []
    for n in names:
        red, rows = gate(n)
        total += red
        if quiet:
            if red:
                miss = ", ".join(r[2] for r in rows if r[0] in ("⛔", "⚠"))
                lines.append("  ⛔ %-18s 検図関門 %d 件 — %s" % (n, red, miss))
            continue
        lines.append("%s  %s" % ("⛔" if red else "⭕", n))
        for mark, key, label, state, why in rows:
            lines.append("    %s %-22s %s" % (mark, label, state))
            if why:
                lines.append("        %s" % why)
    if quiet and total:
        lines.insert(0, "検図関門 — **検分の記録が無い/検め直しが要る指図がある**"
                        "(`python3 Tools/Sashizu/review_gate.py`)")
    print("\n".join(lines))
    if not quiet and total:
        print("\n⛔ 赤 %d 件。**関門が赤の指図を実装しない・赤のシーンをユーザーに見せない。**"
              "\n   検分に出す → 結果を `--record <屋敷> <役> <pass|fail>` で書き戻す。"
              "\n"
              "\n⚠ **【移行期間】2026-09-01 ユーザー裁定(案B)。**関門は新設で全邸が赤で"
              "立ち上がったので、\n   ⭕ **検分を通すまで従来どおり作業を続けてよい**"
              "(実装・指図の改訂とも)。\n"
              "   ⛔ **ただし新たにユーザーへ見せる前には必ず通す** — 見せる=裁定を仰ぐ・"
              "レンダを出す・\n      指図の Artifact を案内する、のすべて。ここが移行中も"
              "動かない一線。\n"
              "   ⛔ 「記録が無い」は「通していない」ではない。⛔ それでも遡って pass は"
              "書かない。" % total)
    sys.exit(1 if total else 0)


# ⚠ **`main()` を裸で呼ばない。** import しただけで全邸の検査が走り、`sys.exit` まで
#   到達する(2026-09-01、判定の単体確認をしようとして踏んだ)。他所からこの道具の
#   関数(`_needs_niwashi` / `gate` / `fingerprint`)を使えるようにしておく。
if __name__ == "__main__":
    main()
