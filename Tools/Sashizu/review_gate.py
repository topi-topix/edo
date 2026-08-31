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
        # 庭・植栽・点景のどれかが指図にあれば庭方が要る
        required=lambda d: any(d.get(k) for k in
                               ("gardens", "planting", "tenkei", "slopePlanting")))),
])

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
            rows.append(("⛔", key, spec["label"], "**一度も通していない**", spec["why"]))
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
        lines.insert(0, "検図関門 — **通していない/検め直しが要る指図がある**"
                        "(`python3 Tools/Sashizu/review_gate.py`)")
    print("\n".join(lines))
    if not quiet and total:
        print("\n⛔ 赤 %d 件。**関門が赤の指図を実装しない・赤のシーンをユーザーに見せない。**"
              "\n   検分に出す → 結果を `--record <屋敷> <役> <pass|fail>` で書き戻す。" % total)
    sys.exit(1 if total else 0)


main()
