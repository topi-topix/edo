#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""進め方の一枚を正典から焼く — docs/Sashizu/susumekata.html

⭐ **狙い。**区画は増えるし、史料を読めば表は書き換わる。その都度この一枚を手で書き直すなら、
いつか必ず古くなって嘘をつく。⛔ 2026-09-19、この一枚を**一度きりの使い捨ての script** で
書いて施主へ出した — 誰も(書いた本人も)焼き直せない産物だった(規則19)。だから道具にした。

⛔ **二つの車線は別々の物差しで測る。**一つの順位に混ぜない。
  ・類型の車線(79区画) = 読み具合(類型表の欄の確度の平均)
  ・図の車線(9敷地)   = 検分の関門(三役)と完成条件の表 — 確度の欄を持たないので読み具合は出ない

    python3 Tools/Sashizu/build_typology_page.py            # docs/Sashizu/susumekata.html へ焼く
    python3 Tools/Sashizu/build_typology_page.py --out <path>
"""
import argparse, json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SA = os.path.join(ROOT, "docs", "Sashizu")
TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "typology_page.html")

FIELD_JA = {"rank": "格", "yashiki": "屋敷の別", "koku": "石高", "front": "表門の向き",
            "gate": "門の型", "units": "戸数", "kind": "種別", "main_hall_ken": "主屋の柱間",
            "name": "名", "two_sided": "両側町", "pattern": "割り", "maguchi_ken": "間口",
            "depth_ken": "奥行", "houses": "軒数", "surface": "地表", "fence": "柵",
            "azukari": "預り", "composition": "構え", "hoshiba": "干場", "haishaku": "拝借",
            "enclosure": "囲い", "yagura": "矢倉", "building": "建物", "jishinban": "自身番"}
TYPE_JA = {"buke": "武家", "machiya": "町屋", "jisha": "寺社", "kouyuu": "公有・明地"}
ROLE_JA = {"kenzu": "図として成立しているか", "kosho": "史実と典拠", "niwashi": "庭"}
# 類型表の区画 id → 図の車線の敷地名(指図のファイル名の頭)
ESTATE = {"okabe": "okabe", "doi": "doi", "matsudaira_dewa": "matsudaira_dewa",
          "sannobuke_kyogoku": "kyogoku_bitchu", "sannobuke_niwa": "niwa_sakyo",
          "sannosha_prec": "sanno"}


def head(s):
    """正典の一行目から人の読める名を採る。⛔ 空白で切らない — 『山王社 社僧十坊の 円乗院』が
    全部『山王社』になった(2026-09-19)。長い名の列挙だけ括弧ごと落とす。"""
    s = (s or "").strip()
    s = re.split(r"[。\[【]", s, maxsplit=1)[0].strip()
    if len(s) > 26:
        s = re.split(r"[(（]", s, maxsplit=1)[0].strip()
    return s[:30] or "—"


def drawing_lane():
    """図の車線 — 検分の関門と完成条件の表を読む。⛔ ここは確度の欄では測らない。
    ⛔ 判定を自分で書き直さない。`review_gate.gate()` が正典で、指紋の取り方も
    worktree の新しい指図を見に行く作法もそこにある(規則8)。import しても走らない
    作りになっている(review_gate.py 末尾の注意書き)。"""
    import importlib.util
    rg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_gate.py")
    spec = importlib.util.spec_from_file_location("review_gate", rg_path)
    rg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rg)
    MARK = {"⭕": "pass", "⛔": "red", "⚠": "stale", "・": "advisory"}
    out = {}
    for pid, est in ESTATE.items():
        rec = {"estate": est, "reviews": [], "kansei": None, "err": None}
        try:
            red, rows = rg.gate(est)
            rec["red"] = red
            for mark, key, label, state, why in rows:
                rec["reviews"].append([ROLE_JA.get(key, label), MARK.get(mark, "?"),
                                       re.sub(r"\s+", " ", state)[:60]])
        except Exception as e:
            rec["err"] = "%s: %s" % (type(e).__name__, e)
        kp = os.path.join(SA, est + "_kansei.json")
        if os.path.exists(kp):
            k = json.load(open(kp, encoding="utf-8"))
            it = k.get("items") or {}
            rec["kansei"] = {"phase": k.get("phase"),
                             "pass": sum(1 for v in it.values() if v.get("verdict") == "pass"),
                             "n": len(it),
                             "labels": [[v.get("label") or kk, v.get("verdict")]
                                        for kk, v in it.items()]}
        out[pid] = rec
    return out


def build():
    T = json.load(open(os.path.join(SA, "typology.json"), encoding="utf-8"))
    P = T["parcels"]
    draw = drawing_lane()
    rows, cnt, bytype = [], collections.Counter(), collections.Counter()
    for k, v in P.items():
        hand = v.get("built") == "hand"
        cert = v.get("cert") or {}
        if not hand:
            bytype[v.get("type")] += 1
            for g in cert.values():
                cnt[g] += 1
        rows.append({"id": k,
                     "name": head(v.get("note")) if hand else head(v.get("source")),
                     "type": v.get("type") or "hand", "hand": hand,
                     "cert": [[FIELD_JA.get(f, f), g] for f, g in sorted(cert.items())],
                     "draw": draw.get(k)})
    order = ["buke", "machiya", "jisha", "kouyuu", "hand"]
    rows.sort(key=lambda r: (r["hand"],
                             order.index(r["type"]) if r["type"] in order else 9, r["id"]))
    return {"rows": rows, "cnt": dict(cnt), "bytype": dict(bytype), "typeja": TYPE_JA,
            "total": len(P), "hand": sum(1 for r in rows if r["hand"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(SA, "susumekata.html"))
    ap.add_argument("--json", action="store_true", help="html を焼かずに中身だけ出す")
    a = ap.parse_args()
    data = build()
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1)); return
    tpl = open(TPL, encoding="utf-8").read()
    assert "__DATA__" in tpl, "台紙に __DATA__ が無い: " + TPL
    open(a.out, "w", encoding="utf-8").write(
        tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    d = sum(data["cnt"].values())
    print("⭕ 進め方の一枚を焼いた: %s" % os.path.relpath(a.out, ROOT))
    print("   区画 %d(類型 %d・図 %d)/ 確度の欄 %d — 未読 %d (%.0f%%)"
          % (data["total"], data["total"] - data["hand"], data["hand"], d,
             data["cnt"].get("U", 0), 100.0 * data["cnt"].get("U", 0) / d))


# ⚠ **`main()` を裸で呼ばない。**import しただけで走ってしまう(review_gate.py が同じ罠を
#   注意書きで残している)。普請場の一枚がこの `build()` を import して使う。
if __name__ == "__main__":
    main()
