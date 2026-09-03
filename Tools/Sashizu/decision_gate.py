#!/usr/bin/env python3
"""決定→図の参照の関門(2026-09-03 ユーザー裁定9=A で新設)。

検図台帳の【…決定…】の項が closed になるとき、閉じ書き(note)に
  ①図版の参照(其◯) か ②検査名(*_check) か ③json のキー(a.b.c)
が最低1つ無ければ「図に届いた証拠が無い」として鳴らす。
⛔ 5巡目で新規49件の約7割が「json に書いた決定が図に出ない・死値」だった — 決定を閉じるときに
「どの図・どの検査に出たか」を書かせ、それを機械で見張る。
使い方: python3 Tools/Sashizu/decision_gate.py <屋敷> [--all]
"""
import json, re, sys, os

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    estate = sys.argv[1]
    show_all = "--all" in sys.argv
    p = os.path.join(os.environ.get("EDO_REPO", "/Users/toshio/project/edo-unity"), ".git", "edo-review", estate + ".json")
    d = json.load(open(p, encoding="utf-8"))
    zu = re.compile(r"其[一二三四五六七八九十〇]+")
    chk = re.compile(r"[A-Za-z_]+_check")
    key = re.compile(r"[A-Za-z_]+\.[A-Za-z_][A-Za-z0-9_.\[\]*]*")
    bad, ok, open_dec = [], [], []
    for it in d["items"]:
        if "決定" not in it.get("text", ""):
            continue
        if it.get("state") == "open":
            open_dec.append(it); continue
        note = " ".join(str(it.get(k, "")) for k in ("close_note", "note", "resolution"))
        if zu.search(note) or chk.search(note) or key.search(note):
            ok.append(it)
        else:
            bad.append(it)
    print("── %s  決定→図の参照: 参照あり %d / ⛔ 参照なし %d / 未決の決定 %d" % (estate, len(ok), len(bad), len(open_dec)))
    for it in bad:
        print("   ⛔ %s(%s巡) %s" % (it["id"], it.get("round"), it["text"][:60].replace("\n", " ")))
    for it in open_dec:
        print("   ⏳ %s 未決 %s" % (it["id"], it["text"][:60].replace("\n", " ")))
    if show_all:
        for it in ok:
            print("   ⭕ %s" % it["id"])
    print("⛔ 閉じ書きに 其◯ / *_check / json のキー のどれかを書くこと。書けない決定は図に届いていない。")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
