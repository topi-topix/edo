#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""算出物 `<邸>_impl.json` の**焼き手**(main 側・EDO-0386)。

⭐ **何のためか。**実装(C#)が読む算出物は指図 json に入っていない従属値の焼き出しで、
邸ごとの生成器が `--export-impl` で焼いていた。その生成器は 2026-09-20 の共通化(afb529c2)で
消え、**main には焼き手が一つも残らなかった**。焼き直せない欄は「古い焼きのまま黙って腐る」——
実際に岡部の `corners[].deg` は 13 隅すべて符号が逆のまま半月止まっていた(EDO-0343 / EDO-0386)。

⭕ **焼き直せる欄だけを焼き、焼けない欄は名指しで刷る。**(規則19「輪に入っていない値は
『未検査』であって『合格』ではない」)。⛔ 焼けない欄を黙って素通りさせない。
⛔ **指図を開き直さない**(規則4)— 建った敷地の直しは欄の上書き。この道具は欄しか触らない。

【焼ける欄】`corners` — 区画(`parcels.json`)と指図の `runs` だけから出る従属値。
【焼けない欄】`graded` / `rails` / `base` / `planting` / `kui` / `migiwa` / `gardens` —
  造成・散布・作庭の器が邸ごとの生成器と一緒に消えたので、main には出す手が無い。
  ⚠ 据え置き(carried)として名指しで刷る。焼き手が要るなら掲示板へ起票すること。

    python3 Tools/Sashizu/bake_impl.py okabe           # 突き合わせの一覧(書かない)
    python3 Tools/Sashizu/bake_impl.py okabe --write   # 焼ける欄だけ上書きして src の指紋を刷り直す
    python3 Tools/Sashizu/bake_impl.py --quiet         # 全邸・食い違う時だけ鳴る(挨拶フックが呼ぶ)
    python3 Tools/Sashizu/bake_impl.py okabe --json
"""
import argparse
import datetime
import glob
import hashlib
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs", "Sashizu")
PARCELS = os.path.join(DOC, "parcels.json")
GEN = "Tools/Sashizu/bake_impl.py <邸> --write"

# ⭕ **この道具が焼ける欄。**ここに無い欄は「据え置き」として名指しで刷る。
BAKEABLE = ["corners"]

# ⛔ **焼き手が main に無い欄**(邸ごとの生成器と一緒に消えた)。黙って合格にしない。
CARRIED_WHY = {
    "graded":   "造成後の地盤の格子 — graded_y / DEM / 段の器が要る",
    "rails":    "法肩の竹垣 — auto_rails が要る",
    "base":     "基壇石垣の露出区間 — run_base / edgeProfile の器が要る",
    "planting": "植栽の散布点 — planting_pts が要る",
    "kui":      "杭の散布点 — kui_pts が要る",
    "migiwa":   "汀線の折れ線 — migiwa_line が要る",
    "gardens":  "庭の算出物 — garden_impl が要る",
}


# ================================================================ 幾何
def kado_deg(poly, vertex):
    """**隅の折れ角[°]を区画から測る。**入りの辺から出の辺への旋回で、左へ曲がれば負・右なら正。

    ⭕ 正典は C# の `EdoBuild.KadoDeg`(`Assets/Edo/Scripts/Editor/EdoBuildKado.cs`)。
      部材の名前の符号 = この旋回の符号で、`EdoAssets.Own.Kado(part, deg)` が deg<0 で鏡像変種を引く。
    ⛔ 数学の慣習(辺ベクトルの外積・反時計回りが正)で書かない —— **符号が逆になる**。
      岡部の旧い生成器がその式で焼いていて、隅 8 基すべてが鏡像の部材で建っていた(EDO-0343)。
    ⚠ ここは C# の写しなので二重に持っている。⭕ 食い違いは実装側でも鳴る
      (`PlaceKado` の degWarn が毎回 json と実測を突き合わせる)— この関門はその**安い前段**。"""
    n = len(poly)
    p = poly[vertex % n]
    a = poly[(vertex - 1) % n]
    b = poly[(vertex + 1) % n]
    h_in = math.degrees(math.atan2(p[0] - a[0], p[1] - a[1]))       # compass 方位(+z から時計回り)
    h_out = math.degrees(math.atan2(b[0] - p[0], b[1] - p[1]))
    return (h_out - h_in + 180.0) % 360.0 - 180.0                   # = Mathf.DeltaAngle


def rseat(r, s):
    """run の天端。seat0→seat1 の一直線(水平のときは両端が同値)。"""
    a = r.get("seat0", r.get("seat"))
    b = r.get("seat1", r.get("seat"))
    if r["s1"] <= r["s0"]:
        return a
    t = (s - r["s0"]) / (r["s1"] - r["s0"])
    return a + (b - a) * max(0.0, min(1.0, t))


# ================================================================ 欄の焼き
def bake_corners(poly, d):
    """`corners[]` を区画と指図の `runs` から焼く。

    隅 i は「辺 i-1 の終い」と「辺 i の初め」の継ぎ目。両方が練塀なら留め継ぎの部材が要る。"""
    runs = d.get("runs") or []
    n = len(poly)
    out = []
    for i in range(n):
        pe, ne = (i - 1) % n, i
        rl = [r for r in runs if r.get("edge") == pe]
        rr = [r for r in runs if r.get("edge") == ne]
        rl = max(rl, key=lambda r: r["s1"]) if rl else None
        rr = min(rr, key=lambda r: r["s0"]) if rr else None
        part = "Dobei" if (rl and rr and rl.get("kind") == "Dobei" and rr.get("kind") == "Dobei") else None
        out.append({"id": "P%d" % i, "vertex": i,
                    "world": [round(poly[i][0], 3), round(poly[i][1], 3)],
                    "deg": round(kado_deg(poly, i), 2), "part": part,
                    "runIn": rl["name"] if rl else None,
                    "runOut": rr["name"] if rr else None,
                    "seatIn": round(rseat(rl, rl["s1"]), 3) if rl else None,
                    "seatOut": round(rseat(rr, rr["s0"]), 3) if rr else None,
                    "yawFrom": "in" if rl else "out"})
    return out


BAKERS = {"corners": bake_corners}


# ================================================================ 突き合わせ
def parcel_poly(est):
    D = json.load(open(PARCELS, encoding="utf-8"))
    for p in D.get("parcels", []):
        if p.get("id") == est:
            return [list(q) for q in p["pts"]]
    return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def diff_rows(old, new):
    """焼き直した欄と今の欄の食い違いを [(場所, 今, 焼き直し)] で返す。"""
    rows = []
    if len(old) != len(new):
        rows.append(("件数", len(old), len(new)))
        return rows
    for o, q in zip(old, new):
        for k in q:
            a, b = o.get(k), q[k]
            if isinstance(a, float) and isinstance(b, float):
                if abs(a - b) <= 5e-3:
                    continue
            elif a == b:
                continue
            rows.append(("%s.%s" % (q["id"], k), a, b))
    return rows


def audit(est):
    """一邸ぶんの突き合わせ。書かない。"""
    impl_p = os.path.join(DOC, est + "_impl.json")
    sash_p = os.path.join(DOC, est + "_sashizu.json")
    if not os.path.exists(impl_p):
        return None
    im = json.load(open(impl_p, encoding="utf-8"))
    r = {"estate": est, "impl": impl_p, "baked": {}, "carried": [], "stale": None, "diff": []}
    # ---- 指紋。⛔ 古い焼きで建てると、図では直った物が現物にだけ残る
    if os.path.exists(sash_p):
        want = ((im.get("src") or {}).get("sha256"))
        got = sha256(sash_p)
        r["stale"] = (want != got)
        r["src"] = {"want": want, "got": got, "bytes": os.path.getsize(sash_p)}
    poly = parcel_poly(est)
    d = json.load(open(sash_p, encoding="utf-8")) if os.path.exists(sash_p) else {}
    for col in BAKEABLE:
        if col not in im:
            continue
        if poly is None:
            r["carried"].append((col, "区画 %s が parcels.json に無い" % est))
            continue
        fresh = BAKERS[col](poly, d)
        r["baked"][col] = fresh
        r["diff"] += [(col,) + t for t in diff_rows(im[col], fresh)]
    for col in im:
        if col in BAKEABLE or col in ("of", "src", "at", "generator", "checks", "baked"):
            continue
        r["carried"].append((col, CARRIED_WHY.get(col, "焼き手が main に無い")))
    r["carried"].sort(key=lambda t: t[0])
    return r


def write(est, r):
    """焼ける欄だけ上書きし、指紋と焼いた履歴を刷り直す。⛔ 据え置きの欄はバイトごと触らない。"""
    im = json.load(open(r["impl"], encoding="utf-8"))
    for col, fresh in r["baked"].items():
        im[col] = fresh
    at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    sash_p = os.path.join(DOC, est + "_sashizu.json")
    # ⛔⛔ **古い焼きを「新しい」と名乗らせない。**指紋の食い違いは「据え置きの欄が別の指図から
    #   焼かれている」という意味で、この道具にはそれを焼き直す手が無い。指紋だけ書き換えると
    #   **中身が古いまま関門が緑になり**、実装が黙って古い値で建つ。⇒ 一致しているときだけ刷り直す。
    if os.path.exists(sash_p) and not r["stale"]:
        im["src"] = {"sha256": sha256(sash_p), "bytes": os.path.getsize(sash_p)}
    im["at"] = at
    im["generator"] = GEN
    # ⭕ **どの欄を誰が焼いたか**を残す。⛔ 全欄を焼いたように名乗らない —
    #   据え置きの欄は古い焼きのままで、「合格」ではなく「未検査」(規則19)。
    im["baked"] = {"at": at, "by": GEN,
                   "columns": sorted(r["baked"].keys()),
                   "carried": {c: w for c, w in r["carried"]},
                   "_": "columns = この焼き手が出し直した欄 / carried = 焼き手が main に無く据え置いた欄"}
    with open(r["impl"], "w", encoding="utf-8") as f:
        json.dump(im, f, ensure_ascii=False)
        f.write("\n")


def report(r, quiet):
    """人が読む報告。⭕ 据え置きの欄は食い違いが 0 件でも必ず名指しで刷る(規則19)。"""
    est = r["estate"]
    n = 0
    if r["stale"]:
        print("算出物の焼き手 — ⛔ %s: 算出物が**いまの指図から焼かれていない** "
              "(指図 %s… / 算出物が名乗る元 %s…)"
              % (est, r["src"]["got"][:12], (r["src"]["want"] or "?")[:12]))
        n += 1
    if r["diff"]:
        print("算出物の焼き手 — ⛔ %s: 焼き直すと変わる欄が %d 件"
              "(`python3 Tools/Sashizu/bake_impl.py %s --write`)" % (est, len(r["diff"]), est))
        for col, where, a, b in r["diff"][:12]:
            print("  ⛔ %-8s %-14s 今 %s → 焼き直し %s" % (col, where, a, b))
        if len(r["diff"]) > 12:
            print("  … ほか %d 件" % (len(r["diff"]) - 12))
        n += len(r["diff"])
    if quiet:
        return n
    print("⭕ %s — 焼いた欄 %s / 食い違い %d 件"
          % (est, "・".join(sorted(r["baked"])) or "(無し)", len(r["diff"])))
    # ⛔ 0 件は「合格」ではない。焼き手の無い欄は**一度も検め直されていない**。
    for col, why in r["carried"]:
        print("  ⚠ 据え置き %-9s — %s ＝ 未検査" % (col, why))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("estate", nargs="?")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    ests = ([a.estate] if a.estate else
            sorted(os.path.basename(p)[:-len("_impl.json")] for p in glob.glob(os.path.join(DOC, "*_impl.json"))))
    if a.estate and not os.path.exists(os.path.join(DOC, a.estate + "_impl.json")):
        print("⛔ 算出物が無い: docs/Sashizu/%s_impl.json" % a.estate)
        return 2
    bad = 0
    for est in ests:
        r = audit(est)
        if r is None:
            continue
        if a.json:
            print(json.dumps({k: v for k, v in r.items() if k != "baked"}, ensure_ascii=False, default=str))
            continue
        if a.write:
            if r["stale"]:
                # ⛔ 焼き直せる欄だけ直しても、据え置きの欄は別の指図から焼かれたまま。
                #    指紋を書き換えて関門を緑にするのは嘘なので、ここで止めて起票させる。
                print("⛔ %s — 算出物が**いまの指図から焼かれていない**"
                      "(指図 %s… / 算出物が名乗る元 %s…)"
                      % (est, r["src"]["got"][:12], (r["src"]["want"] or "?")[:12]))
                print("  ⛔ この道具は据え置きの欄(%s)を焼き直せないので、**指紋を書き換えない**。"
                      % "・".join(c for c, _ in r["carried"]))
                print("  ⭕ 焼き手を起こすか、欄の中身が今の指図と同じであることを確かめた上で"
                      "指紋を宣言し直すこと(先例 b9613ad8)。掲示板へ起票してから建てること。")
                bad += 1
                continue
            if not r["diff"]:
                print("⭕ %s — 焼き直しても変わらない(書かない)" % est)
                continue
            write(est, r)
            print("⭕ %s — 欄 %s を焼き直した(%d 件を上書き)"
                  % (est, "・".join(sorted(r["baked"])), len(r["diff"])))
            for col, why in r["carried"]:
                print("  ⚠ 据え置き %-9s — %s" % (col, why))
            continue
        bad += report(r, a.quiet)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
