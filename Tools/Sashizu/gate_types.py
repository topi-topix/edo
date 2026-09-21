#!/usr/bin/env python3
"""門の完備 — 門の型が要求する部材が、指図の欄に全部あるか(EDO-0315)。

背景: 松江松平の検証レンダで『表門の屋根が見当たらず板一枚に見える』が絵で初めて見つかった。
門の取り合い(隙間0・めり込み0)は「隣り合う部材が接しているか」しか見ておらず、
「その型が持つべき部材が居るか」を誰も見ていなかった。屋根の有無は数えられる(verification-loops §4)。

正典は docs/Sashizu/gate_types.json(型 → 屋根の有無・部材)。読み手は2つ:
  ・この module           … 図の輪。指図の gate / komon / gates の欄が型と食い違わないか(build_sashizu.py C24)
  ・EdoGateComplete.cs    … 実装の輪。建てた門の上に本当に屋根が架かっているかを Unity で測る

使い方:
    python3 Tools/Sashizu/gate_types.py                 # 全邸の門を型に引いて一覧
    python3 Tools/Sashizu/gate_types.py --selftest      # 検査自身の破壊試験(壊した版で必ず鳴ること)

⛔ 型が決まらない門は「未検査」であって「合格」ではない(規則19)。0 件を合格と読まないこと。
"""
import glob
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TABLE_PATH = os.path.join(REPO, "docs", "Sashizu", "gate_types.json")

_NO_ROOF_WORDS = ("屋根なし", "屋根無し", "無屋根")
_ROOF_WORDS = ("造", "葺", "屋根", "破風")      # 「切妻造」「銅瓦葺」「向唐破風」


def load_table(path=None):
    with open(path or TABLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def classify(text, table):
    """自由文(gate.kind など)から型を引く。当たらなければ None。上から順に最初の型。"""
    if not text:
        return None
    for key, t in table["types"].items():
        if any(w in text for w in t["match"]):
            return key
    return None


def _txt(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("kind", "type", "form", "label"):
            if isinstance(v.get(k), str):
                return v[k]
    return ""


def declared_roof(g):
    """指図の欄が言っている屋根。'none' / 'roof' / None(欄が無い=語らない)。"""
    plan = g.get("plan") if isinstance(g.get("plan"), dict) else {}
    for src in (plan.get("roof"), g.get("roof")):
        if src is None:
            continue
        s = _txt(src)
        if s:
            return "none" if any(w in s for w in _NO_ROOF_WORDS) or s.strip() in ("なし", "無", "none") else "roof"
        if isinstance(src, dict):
            return "roof"           # 欄はあるが型名が読めない = 屋根の記述を持っている
    kind = g.get("kind") if isinstance(g.get("kind"), str) else ""
    if any(w in kind for w in _NO_ROOF_WORDS):
        return "none"
    if any(w in kind for w in _ROOF_WORDS):
        return "roof"
    return None


def bansho_count(g):
    """指図が数を言う番所。言わなければ None。"""
    plan = g.get("plan") if isinstance(g.get("plan"), dict) else {}
    b = plan.get("bansho")
    if isinstance(b, dict) and isinstance(b.get("count"), (int, float)):
        return int(b["count"])
    return None


def audit(g, name, table, hint_kind=None):
    """門1つを型に引いて、指図の欄との食い違いを返す。
    戻り値: (型キー or None, [(level, msg)])。level は 'ng'(矛盾)/'na'(欄が無い=未検査)/'info'(記録)。"""
    out = []
    kind_text = g.get("kind") if isinstance(g.get("kind"), str) else ""
    ty = classify(kind_text, table) or classify(hint_kind, table) or classify(name, table)
    if ty is None:
        shown = kind_text or hint_kind or "(kind 無し)"
        out.append(("na", "型が読めない(『%s』が表の match に当たらない)— 屋根の有無を検められない" % shown[:24]))
        return None, out
    t = table["types"][ty]
    dr = declared_roof(g)
    if t["roof"] == "none":
        if dr == "roof":
            out.append(("ng", "型『%s』は屋根を持たないのに、指図が屋根を書いている(型の取り違えか欄の書き間違い)" % t["label"]))
        elif dr == "none":
            out.append(("info", "屋根なし(型どおり)— 実装でも屋根が載っていないことを測る"))
    elif t["roof"] == "yes":
        if dr == "none":
            out.append(("ng", "型『%s』は屋根を持つのに、指図が『屋根なし』と書いている" % t["label"]))
        elif dr is None:
            out.append(("na", "型『%s』は屋根を持つが、指図に屋根の欄が無い(plan.roof か kind に形を書く)" % t["label"]))
    bc = bansho_count(g)
    if bc:
        out.append(("info", "番所 %d(実装で %s が %d 居るか測る)" % (bc, table["attachments"]["bansho"]["scene"], bc)))
    return ty, out


def gates_of(d):
    """指図 json から (呼び名, 門の dict, 既定の kind) を拾う。build_sashizu.py の M.gates と同じ3経路。"""
    res = []
    g = d.get("gate")
    if isinstance(g, dict):
        res.append((g.get("name", "表門"), g, "表門"))
    elif isinstance(g, list):
        res += [(x.get("name", "門"), x, "門") for x in g if isinstance(x, dict)]
    km = d.get("komon")
    for x in (km if isinstance(km, list) else ([km] if isinstance(km, dict) else [])):
        res.append((x.get("name", "通用門"), x, "通用門"))
    for x in d.get("gates", []) or []:
        if isinstance(x, dict):
            res.append((x.get("name", "門"), x, "門"))
    return res


# ---------------------------------------------------------------- 一覧
def main_list():
    table = load_table()
    print("門の完備 — 全邸の門を型に引く(表: docs/Sashizu/gate_types.json)")
    tot = {"ng": 0, "na": 0}
    for f in sorted(glob.glob(os.path.join(REPO, "docs", "Sashizu", "*_sashizu.json"))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        est = os.path.basename(f)[: -len("_sashizu.json")]
        for name, g, dflt in gates_of(d):
            ty, res = audit(g, name, table, dflt)
            mark = "⛔" if any(l == "ng" for l, _ in res) else ("⚠" if any(l == "na" for l, _ in res) else "⭕")
            print("  %s %-16s %-14s 型=%-9s %s" % (mark, est, str(name)[:14], ty or "?", " / ".join(m for _, m in res) or "—"))
            for l, _ in res:
                if l in tot:
                    tot[l] += 1
    print("矛盾 %d / 未検査(欄なし・型不明)%d" % (tot["ng"], tot["na"]))
    return 1 if tot["ng"] else 0


# ---------------------------------------------------------------- 自己検査(破壊試験)
def selftest():
    """⛔ 0件は「合格」とも「検査が死んでいる」とも読める。健全な版で鳴らず、壊した版で必ず鳴ることを見る。"""
    table = load_table()
    fails = []

    def expect(label, g, want_levels, name="門", hint=None, want_type="?"):
        ty, res = audit(g, name, table, hint)
        got = sorted({l for l, _ in res if l != "info"})
        if got != sorted(want_levels):
            fails.append("%s: 期待 %s / 実際 %s %s" % (label, sorted(want_levels), got, [m for _, m in res]))
        if want_type != "?" and ty != want_type:
            fails.append("%s: 型 期待 %s / 実際 %s" % (label, want_type, ty))

    # 健全
    expect("冠木門(屋根なし)", {"kind": "冠木門(屋根なし)+両唐破風番所", "plan": {"bansho": {"count": 2}}}, [], want_type="kabukimon")
    expect("長屋門+切妻造", {"kind": "長屋門(片番所)", "plan": {"roof": "切妻造"}}, [], want_type="nagayamon")
    expect("棟門+葺", {"kind": "棟門・銅瓦葺"}, [], want_type="munemon")
    expect("楼門+入母屋造", {"kind": "三間一戸・単層・入母屋造(楼門)"}, [], want_type="romon")
    expect("木戸は屋根の欄が無くてよい", {"kind": "木戸(板扉+冠木)"}, [], want_type="kido")
    # 壊す — 欄が無い(未検査)
    expect("長屋門 屋根の欄なし", {"kind": "長屋門(門長屋)", "plan": {}}, ["na"], want_type="nagayamon")
    expect("型が読めない", {"kind": "表門"}, ["na"], want_type=None)
    expect("kind 自体が無い", {}, ["na"], want_type=None)
    # 壊す — 矛盾
    expect("長屋門なのに屋根なし", {"kind": "長屋門(屋根なし)"}, ["ng"], want_type="nagayamon")
    expect("長屋門 plan.roof=なし", {"kind": "長屋門", "plan": {"roof": "なし"}}, ["ng"], want_type="nagayamon")
    expect("冠木門なのに切妻造", {"kind": "冠木門", "plan": {"roof": "切妻造"}}, ["ng"], want_type="kabukimon")
    expect("薬医門 屋根 dict なし", {"kind": "薬医門", "plan": {"roof": {"kind": "屋根なし"}}}, ["ng"], want_type="yakuimon")
    # 型の取り違えは match の順で防ぐ — 『冠木』だけの木戸を冠木門にしない
    ty, _ = audit({"kind": "木戸(板扉+冠木)"}, "勝手口", table)
    if ty != "kido":
        fails.append("『木戸(板扉+冠木)』が %s に引かれた(kido であること)" % ty)
    # 表そのものの破壊試験: 型を消すと『型が読めない』になる
    t2 = json.loads(json.dumps(table))
    del t2["types"]["nagayamon"]
    ty, res = audit({"kind": "長屋門", "plan": {"roof": "切妻造"}}, "門", t2)
    if ty is not None or not any(l == "na" for l, _ in res):
        fails.append("表から長屋門を消しても鳴らない(検査が死んでいる)")
    # 表の整合: 全ての型が roof / parts / match を持つ
    for k, t in table["types"].items():
        if t.get("roof") not in ("none", "yes", "opt") or not t.get("match") or not t.get("parts"):
            fails.append("表の型 %s が roof/match/parts を欠く" % k)
    if fails:
        print("⛔ gate_types selftest: %d 件\n  " % len(fails) + "\n  ".join(fails))
        return 1
    print("⭕ gate_types selftest: 全件通過")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main_list())
