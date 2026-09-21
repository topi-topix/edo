#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指図の文章を値から切り離す(第一段・2026-09-21 施主指示)。

    python3 Tools/Sashizu/prose_split.py <邸> --check     # 測るだけ(何も書かない)
    python3 Tools/Sashizu/prose_split.py <邸> --apply     # 切り出す
    python3 Tools/Sashizu/prose_split.py <邸> --restore   # 戻して原本と一致するか確かめる

**なぜ** — 大きい邸の指図 json は 7 割が文章で、値を一つ直すのに 700KB 読む羽目になっていた
(2026-09-21 の実測: 松江松平 824KB / 山王 755KB / 土井 692KB)。文章の正典はもともと
`<邸>_kosho.md` と決まっていたのに、直しを重ねるうちに `_` の注記として json へ流れ込んだ。

**何を動かすか** — `_` で始まる欄のうち、**中身が文字列だけ**の物。数値を含む `_` の欄は動かさない
(土井 `terraceWalls/*/_exposure` ほか 42 件 — 測った値で、消すと「測っていない」が消える)。
`_` で始まらない欄は一切触らない(`why` / `note` / `bom` の説明文は読み手が使う本文)。

**どこへ行くか** — `docs/Sashizu/<邸>_notes/<章>.json`。章は指図の top-level の欄名。
章ごとに分けるのは「gardens を直すなら gardens の注記だけ読む」ためで、これが第一段の眼目。

⭕ **可逆**。`--restore` が notes を json へ戻し、原本と一致することを毎回確かめる。
⛔ **値を書き換えない。**数値・真偽・短い文字列・欄の並びはそのまま。
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(HERE), "..", "docs", "Sashizu")
DOC = os.path.normpath(DOC)

# ⭐ **生成器が読んでいる `_` は動かさない — 名前も変えない。**
#   build_sashizu.py:595 が `p.get("note") or p.get("_")` で program の注記を組み立て、
#   役割の表の「覚」の列に刷る(土井で 6 件・952 字)。
# ⚠ **`note` へ改名する版を一度書いて捨てた。**改名すると `_` でない欄が増えて検分の指紋が動き、
#   **完成済みの邸(松江松平)を赤に落とす**。据え置けば `_` のままなので、指紋が `_` を
#   再帰的に除くようになったとき「文章を動かしても検分は動かない」が例外なく成り立つ(実証済み)。
# ⚠ **深さちょうどで当てる。**拾われるのは `program/<i>/_` だけ。`program/<i>/aspects/<j>/_`
#   (土井で 90 件)は拾われないので、章名だけで当てると図に出ない文章まで json に残る。
# ⛔ **ここを増やすときは図を焼いて突き合わせること。**2026-09-21、刷られている 6 件を
#   「刷られていない」と誤判定した — markdown が `<b>` `<code>` を挿むので、
#   html への部分一致では見つからない。⭕ 正しい検めは **切り出しの前後で html を diff する**。
READ_BY_GENERATOR = (("program",),)

# 注記の在り処を指す道しるべ。top-level の `_` なので検分の指紋には入らない
# (review_gate.fingerprint は top-level の `_` を除く)。
POINTER_KEY = "_notes"


def notes_dir(est):
    return os.path.join(DOC, est + "_notes")


def sashizu_path(est):
    return os.path.join(DOC, est + "_sashizu.json")


def only_strings(v):
    """中身が文字列だけか(数値・真偽が一つでもあれば False)。"""
    if isinstance(v, str):
        return True
    if isinstance(v, bool) or isinstance(v, (int, float)):
        return False
    if isinstance(v, list):
        return all(only_strings(x) for x in v) if v else False
    if isinstance(v, dict):
        return all(only_strings(x) for x in v.values()) if v else False
    return False


def _read_by_generator(path):
    """その `_` を生成器が拾う場所か。章が合い、かつ**深さがちょうど一つ下**(章/<i>)のときだけ。
    ⚠ `program/<i>/aspects/<j>/_`(土井で 90 件)は拾われない — 深さで見分ける。"""
    for pref in READ_BY_GENERATOR:
        if len(path) == len(pref) + 1 and tuple(path[:len(pref)]) == pref:
            return True
    return False


def split(doc):
    """(値だけの doc, 注記 {path: value}, 据え置いた path) を返す。原本は書き換えない。"""
    notes = collections.OrderedDict()
    kept = []

    def walk(v, path):
        if isinstance(v, dict):
            out = collections.OrderedDict()
            for k, x in v.items():
                p = path + [str(k)]
                if k == "_" and _read_by_generator(path):
                    kept.append("/".join(p))      # 生成器が刷る — 据え置く
                    out[k] = x
                    continue
                if str(k).startswith("_") and k != POINTER_KEY and only_strings(x):
                    notes["/".join(p)] = x
                    continue
                out[k] = walk(x, p)
            return out
        if isinstance(v, list):
            return [walk(x, path + [str(i)]) for i, x in enumerate(v)]
        return v

    return walk(doc, []), notes, kept


def by_chapter(notes):
    """注記を top-level の章ごとに束ねる。"""
    out = collections.OrderedDict()
    for path, v in notes.items():
        out.setdefault(path.split("/")[0], collections.OrderedDict())[path] = v
    return out


def merge(doc, notes):
    """注記を doc へ戻す(--restore の検算用)。並びは原本と違ってよい — 比較は正規形で行う。"""
    out = json.loads(json.dumps(doc), object_pairs_hook=collections.OrderedDict)
    for path, v in notes.items():
        cur = out
        parts = path.split("/")
        for k in parts[:-1]:
            cur = cur[int(k)] if isinstance(cur, list) else cur[k]
        cur[parts[-1]] = v
    return out


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load(est):
    with open(sashizu_path(est), encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)


def load_notes(est):
    """散らばった章の注記を一つに集める(他の道具から呼べる)。"""
    d = notes_dir(est)
    out = collections.OrderedDict()
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                out.update(json.load(f, object_pairs_hook=collections.OrderedDict))
    return out


def count_values(v):
    """数値と真偽の数。⚠ 文字列は数えない — 短い `_` の注記も動かすので、
    文字列まで数えると「動かした」と「失った」の区別がつかない。
    文字列を含めた完全性は `merge()` の往復で見る(そちらが本当の関門)。"""
    if isinstance(v, bool) or isinstance(v, (int, float)):
        return 1
    if isinstance(v, list):
        return sum(count_values(x) for x in v)
    if isinstance(v, dict):
        return sum(count_values(x) for x in v.values())
    return 0


def report(est, doc, stripped, notes, kept):
    a = len(json.dumps(doc, ensure_ascii=False, indent=1).encode())
    b = len(json.dumps(stripped, ensure_ascii=False, indent=1).encode())
    ch = by_chapter(notes)
    print("== %s ==" % est)
    print("  指図    %7.1fKB → %7.1fKB  (%.0f%%)" % (a / 1024, b / 1024, b * 100.0 / a))
    print("  注記    %d 件 → %d 章のファイル" % (len(notes), len(ch)))
    if kept:
        print("  据置    生成器が刷る `_`  %d 件: %s"
              % (len(kept), ", ".join(kept[:4]) + (" ほか" if len(kept) > 4 else "")))
    print("  数値    %d → %d" % (count_values(doc), count_values(stripped)))
    big = sorted(((sum(len(json.dumps(v, ensure_ascii=False).encode()) for v in m.values()), c)
                  for c, m in ch.items()), reverse=True)
    print("  大きい章:", ", ".join("%s %.0fK" % (c, s / 1024) for s, c in big[:8]))
    return a, b


def verify(doc, stripped, notes):
    """三つの検算。一つでも落ちたら書かない。"""
    bad = []
    if canon(merge(stripped, notes)) != canon(doc):
        bad.append("戻した物が原本と一致しない(可逆でない)")
    if count_values(doc) != count_values(stripped):
        bad.append("値の数が変わった %d → %d" % (count_values(doc), count_values(stripped)))

    # 残った所に長い文章が無いか(`_` でない本文は対象外なので数えるだけ)
    def stray(v, path, acc):
        if isinstance(v, dict):
            for k, x in v.items():
                if (str(k).startswith("_") and k != POINTER_KEY and only_strings(x)
                        and not (k == "_" and _read_by_generator(path))):
                    acc.append("/".join(path + [str(k)]))
                stray(x, path + [str(k)], acc)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                stray(x, path + [str(i)], acc)
    acc = []
    stray(stripped, [], acc)
    if acc:
        bad.append("切り残した `_` の欄 %d 件: %s" % (len(acc), ", ".join(acc[:5])))
    return bad


def write_index(est, ch):
    """章の目次。⭐ **これが「参照しやすい構造」の入口** — どの章を開けばよいかを
    大きさ付きで示す。自動生成なので手で書き足さない(切り出すたびに刷り直る)。"""
    rows = sorted(((sum(len(json.dumps(v, ensure_ascii=False).encode()) for v in m.values()),
                    c, len(m)) for c, m in ch.items()), reverse=True)
    h = ["# %s 指図の注記 — 章ごとの目次" % est, "",
         "設計値の正典は `../%s_sashizu.json`、**この下は文章だけ**。" % est,
         "`<章>/<添字>/<欄>` の path がそのまま鍵なので、"
         "直したい欄の path で grep すれば意図と経緯が引ける。", "",
         "⛔ **値をここへ書かない。**⛔ 文章を指図 json へ戻さない。",
         "戻して原本と突き合わせるのは "
         "`python3 Tools/Sashizu/prose_split.py %s --restore`。" % est, "",
         "| 章 | 注記 | 大きさ |", "|---|---:|---:|"]
    for s, c, n in rows:
        h.append("| [%s](%s.json) | %d | %.1f KB |" % (c, c, n, s / 1024.0))
    h += ["", "計 %d 章 / %d 件 / %.0f KB"
          % (len(rows), sum(n for _, _, n in rows), sum(s for s, _, _ in rows) / 1024.0), ""]
    with open(os.path.join(notes_dir(est), "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(h))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("estate")
    ap.add_argument("--apply", action="store_true", help="切り出して書く")
    ap.add_argument("--restore", action="store_true", help="notes を json へ戻して原本と比べる")
    ap.add_argument("--check", action="store_true", help="測るだけ(既定)")
    a = ap.parse_args()
    est = a.estate

    if a.restore:
        stripped = load(est)
        notes = load_notes(est)
        if not notes:
            print("⛔ %s に注記のファイルが無い" % notes_dir(est))
            return 1
        back = merge(stripped, notes)
        print("戻した指図: %.1fKB / 注記 %d 件 / 章 %d"
              % (len(json.dumps(back, ensure_ascii=False, indent=1).encode()) / 1024,
                 len(notes), len(by_chapter(notes))))
        return 0

    doc = load(est)
    stripped, notes, kept = split(doc)
    if not notes:
        print("⭕ %s は切り出す `_` の文章が無い(済んでいる)" % est)
        return 0
    report(est, doc, stripped, notes, kept)
    bad = verify(doc, stripped, notes)
    if bad:
        print("\n⛔ 検算に落ちた — 書かない")
        for b in bad:
            print("   ・" + b)
        return 1
    print("  検算    ⭕ 可逆・値の数が同じ・切り残し 0")

    if not a.apply:
        print("\n(測っただけ。書くには --apply)")
        return 0

    d = notes_dir(est)
    os.makedirs(d, exist_ok=True)
    ch = by_chapter(notes)
    for c, m in ch.items():
        with open(os.path.join(d, c + ".json"), "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
            f.write("\n")
    write_index(est, ch)
    stripped[POINTER_KEY] = (
        "⭐ **この指図の文章は `docs/Sashizu/%s_notes/<章>.json` にある。**"
        "欄を直すときは同じ章の注記を先に読むこと(path がそのまま鍵)。"
        "戻すのは `python3 Tools/Sashizu/prose_split.py %s --restore`。"
        "⛔ 文章をここへ書き戻さない — 値だけを置く欄にした(2026-09-21 施主指示)。" % (est, est))
    with open(sashizu_path(est), "w", encoding="utf-8") as f:
        json.dump(stripped, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n⭕ 書いた: %s / %s (%d 章)"
          % (os.path.relpath(sashizu_path(est)), os.path.relpath(d), len(ch)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
