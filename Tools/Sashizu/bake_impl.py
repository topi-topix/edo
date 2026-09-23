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

【焼ける欄】
  `corners` — 区画(`parcels.json`)と指図の `runs` だけから出る従属値。
  `gates`   — 門の **`yaw` / `passAz` / `yawFrom` / `front`**。`front`(無ければ `pass`)と
              `grid.frames[].deg` と `bom[].axis` だけから出る(2026-09-22・EDO-0261 ①)。
              ⛔ 門の**芯**(`u`/`v`/`world`)と平面(`sill`/`plan`/`monguchiKen`)は焼けない ──
              `uFrom` の組み立て(平場の縁+犬走り)と間数への換算の器が生成器と一緒に消えたので、
              **今の算出物の行から持ち越す**。⇒ 指図に**新しい門を足したら、この道具は焼けない**
              (その門は算出物に行が無い ⇒ `gates` ごと据え置きにして名指しで刷る)。
  **山王は全欄**(`ENGINES`)— 邸ごとの生成器の最終版から `--export-impl` が辿る関数だけを切り出した
              器 `Tools/Sashizu/impl_sanno.py` が焼く(2026-09-23・EDO-0397)。⚠ 約 100 秒かかるので、
              **邸を名指したときだけ**走らせる(全邸を見る `--quiet` は指紋だけ)。
【焼けない欄】(器の無い邸)`dem` / `graded` / `grid` / `planting` / `routes` / `runs` / `setae` / `stairs` /
  `tamagaki` / `terraces` / `rails` / `base` / `kui` / `migiwa` / `gardens` —
  造成・散布・作庭の器が邸ごとの生成器と一緒に消えたので、main には出す手が無い(いま岡部)。
  ⚠ 据え置き(carried)として名指しで刷る。焼き手が要るなら掲示板へ起票すること。
  ⚠ 据え置きの欄が**どの指図から焼かれたか**は `baked.carriedSrc` に残る(下の `write` を見よ)。

    python3 Tools/Sashizu/bake_impl.py okabe           # 突き合わせの一覧(書かない)
    python3 Tools/Sashizu/bake_impl.py okabe --write   # 焼ける欄だけ上書きして src の指紋を刷り直す
    python3 Tools/Sashizu/bake_impl.py --quiet         # 全邸・食い違う時だけ鳴る(挨拶フックが呼ぶ)
    python3 Tools/Sashizu/bake_impl.py okabe --json
    python3 Tools/Sashizu/bake_impl.py sanno           # 器で全欄を焼き直して突き合わせる(約 100 秒)
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
BAKEABLE = ["corners", "gates"]

# ⭕ 区画(`parcels.json`)の輪郭が要る欄。⛔ 要らない欄を区画の有無で据え置きにしない
#   (山王社は `parcels.json` に `sanno` という区画を持たない ── 境内は `sannosha_prec` ほか)。
NEEDS_POLY = {"corners"}

# ⭕ **全欄を焼く器を持つ邸**(邸 → Tools/Sashizu/ のモジュール名)。器は `bake()` で算出物の dict を返す。
#   ⛔ 器の式を作り直さない ── 消えた生成器の写しで、当時の算出物を再現することを検めてある。
ENGINES = {"sanno": "impl_sanno"}

# 算出物のうち**欄ではない**もの(指紋・日付・版)。⛔ 器の返りのこれらを「焼き直すと変わる欄」に数えない。
META = ("of", "src", "at", "generator", "baked")

# ⛔ **焼き手が main に無い欄**(邸ごとの生成器と一緒に消えた)。黙って合格にしない。
CARRIED_WHY = {
    "graded":   "造成後の地盤の格子 — graded_y / DEM / 段の器が要る",
    "rails":    "法肩の竹垣 — auto_rails が要る",
    "base":     "基壇石垣の露出区間 — run_base / edgeProfile の器が要る",
    "planting": "植栽の散布点 — planting_pts が要る",
    "kui":      "杭の散布点 — kui_pts が要る",
    "migiwa":   "汀線の折れ線 — migiwa_line が要る",
    "gardens":  "庭の算出物 — garden_impl が要る",
    "dem":      "造成前の地盤の格子 — base_dem からの切り出しの器が要る",
    "grid":     "境内グリッドの原点と向き — 組み立て(derive_grid)が要る",
    "terraces": "平場の外形 — 平場の組み立て(derive_terraces)が要る",
    "stairs":   "石段の踏面の折れ線 — 段の組み立て(derive_kaidan)が要る",
    "runs":     "囲いの run の割り付け — run の組み立てが要る",
    "routes":   "動線の折れ線(世界座標)— 勝手道からの組み立てが要る",
    "setae":    "背板・添え物の座 — 器が邸ごとの生成器と一緒に消えた",
    "tamagaki": "玉垣の建つ区間(木戸の開口を抜いた実長)— 辺の割り直しの器が要る",
}

# ⛔ 焼けない欄を「焼けた」と名乗らせないための例外。焼き手はあるが**材料が足りない**ときに投げる。
class Carried(Exception):
    pass


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
def bake_corners(poly, d, im):
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


# ---------------------------------------------------------------- 門の向き
# ⭕ **語の辞書**(⛔ 設計値ではない)。方位の語 → 真北からの角[°・上から見て時計回り]。
_DIR_DEG = {"北": 0.0, "北北東": 22.5, "北東": 45.0, "東北東": 67.5, "東": 90.0,
            "東南東": 112.5, "南東": 135.0, "南南東": 157.5, "南": 180.0,
            "南南西": 202.5, "南西": 225.0, "西南西": 247.5, "西": 270.0,
            "西北西": 292.5, "北西": 315.0, "北北西": 337.5}
# 部材のローカル軸 → 真北からの角[°](Unity の Y 回転 0 のとき。+Z=北 / +X=東)
_LOCAL_AX_DEG = {"+Z": 0.0, "+X": 90.0, "-Z": 180.0, "-X": 270.0, "Z": 0.0, "X": 90.0}
_PASS_DEG = {"南北": 0.0, "東西": 90.0}


def gate_bom_row(d, gt):
    """門の `bom` が指す部材の行(無ければ None)。"""
    nm = gt.get("bom")
    if not nm:
        return None
    for b in d.get("bom") or []:
        if b.get("部材") == nm:
            return b
    return None


def gate_frame_deg(d, gt):
    """門が載る**回した枠**の角[°・上から見て時計回り]。`gates[].frame` が `grid.frames` を名指す。
    ⛔ 角を門ごとに数で持たない ── `grid.frames[].deg` 一本。⛔ 名指したのに引けなければ 0 で埋めない。"""
    nm = gt.get("frame")
    if not nm:
        return 0.0
    fm = ((d.get("grid") or {}).get("frames") or {}).get(nm)
    if fm is None or not isinstance(fm.get("deg"), (int, float)):
        raise Carried("門『%s』の枠『%s』の角が `grid.frames` から引けない(0 で埋めない)"
                      % (gt.get("name"), nm))
    return float(fm["deg"])


def gate_yaw(d, gt):
    """**門の yaw は従属値** ── `front`(無ければ `pass`)と `bom[].axis`(部材のローカル軸)から出す。
    ⭕ 式は消えた生成器 `Tools/Sashizu/build_sanno_sashizu.py::derive_gate_yaw`(afb529c2 で削除)の
    写しで、⛔ **作り直していない**。

    物差しは Unity の Y 回転[°](上から見て時計回り)。回転 θ はローカルの向きの方位角に θ を足す
    ⇒ θ = 正面の方位 − 部材の正面のローカル方位。正面が無い門は通り抜けの軸だけ合わせる(mod 180)。
    ⛔ 部材の軸が無い門は yaw を出さない(0 で埋めない)。`passAz` = 通り抜けの軸の方位[°](mod 180)。
    返りは (yaw, passAz, yawFrom)。"""
    fd = gate_frame_deg(d, gt)
    fr, ps = gt.get("front"), gt.get("pass")
    az = None
    if fr in _DIR_DEG:
        az = (_DIR_DEG[fr] + fd) % 180.0
    elif ps in _PASS_DEG:
        az = (_PASS_DEG[ps] + fd) % 180.0
    ax = (gate_bom_row(d, gt) or {}).get("axis") or {}
    if fr in _DIR_DEG and ax.get("front") in _LOCAL_AX_DEG:
        return (round((_DIR_DEG[fr] + fd - _LOCAL_AX_DEG[ax["front"]]) % 360.0, 6), az,
                "front=%s%s × bom.axis.front=%s"
                % (fr, (" + 枠『%s』%+.1f°" % (gt["frame"], fd)) if fd else "", ax["front"]))
    if az is not None and ax.get("pass") in _LOCAL_AX_DEG:
        return (round((az - _LOCAL_AX_DEG[ax["pass"]]) % 180.0, 6), az,
                "pass × bom.axis.pass=%s(正面は未宣言 — 軸だけ合わせる)" % ax["pass"])
    return None, az, None


def bake_gates(poly, d, im):
    """`gates[]` の**向き**を指図から焼き直す。⛔ 芯と平面は焼かない(今の行から持ち越す)。

    ⭐ なぜ持ち越すか: 門の芯は `uFrom`(平場の縁 + 犬走り)からの組み立てで、その器は
    邸ごとの生成器と一緒に消えている。⇒ **指図に無い門・算出物に無い門があれば `gates` ごと据え置く**
    (半分だけ焼いて「焼けた」と名乗らせない・規則19)。"""
    old = {}
    for g in (im.get("gates") or []):
        old[g.get("name")] = g
    out = []
    for gt in d.get("gates") or []:
        nm = gt.get("name")
        o = old.get(nm)
        if o is None:
            raise Carried("門『%s』が算出物に無い ── 芯(`uFrom` の組み立て)の焼き手が main に無い" % nm)
        yaw, az, how = gate_yaw(d, gt)
        row = dict(o)
        row["name"] = nm
        row["front"] = gt.get("front")
        row["yaw"], row["passAz"], row["yawFrom"] = yaw, az, how
        row["bom"] = gt.get("bom")
        out.append(row)
    return out


BAKERS = {"corners": bake_corners, "gates": bake_gates}


def run_engine(est):
    """器で全欄を焼く(書かない)。返りは算出物の dict。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        mod = __import__(ENGINES[est])
    finally:
        sys.path.pop(0)
    return mod.bake()


def diff_deep(old, new, path, out, cap=40):
    """入れ子の欄の食い違いを葉ごとに数える。数は 5e-3 まで同じと見る。
    ⭐ 指図の地の文(`_` で始まる鍵)は 2026-09-21 の文章分離で notes へ出たので、食い違いに数えない。
    返りは食い違いの件数。`out` には先頭 cap 件だけ (場所, 今, 焼き直し) を積む。"""
    def push(a, b):
        return _push(out, path, a, b, cap)
    if isinstance(old, dict) and isinstance(new, dict):
        n = 0
        for k in sorted(set(old) | set(new)):
            if k.startswith("_"):
                continue
            if k not in old or k not in new:
                n += _push(out, "%s.%s" % (path, k), old.get(k, "(無し)"), new.get(k, "(無し)"), cap)
                continue
            n += diff_deep(old[k], new[k], "%s.%s" % (path, k), out, cap)
        return n
    # ⭐ 器の返りは tuple を含む(json に書けば list)。⛔ 型の違いだけで食い違いに数えない。
    if isinstance(old, (list, tuple)) and isinstance(new, (list, tuple)):
        if len(old) != len(new):
            return push("%d 件" % len(old), "%d 件" % len(new))
        return sum(diff_deep(a, b, "%s[%d]" % (path, i), out, cap)
                   for i, (a, b) in enumerate(zip(old, new)))
    if isinstance(old, (int, float)) and isinstance(new, (int, float)) \
            and not isinstance(old, bool) and not isinstance(new, bool):
        return 0 if abs(old - new) <= 5e-3 else push(old, new)
    return 0 if old == new else push(old, new)


def _push(out, where, a, b, cap):
    if len(out) < cap:
        out.append((where, _short(a), _short(b)))
    return 1


def _short(v):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= 60 else s[:57] + "…"


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
        # ⭐ 行の名札は `id`(隅)か `name`(門)。⛔ どちらかに決め打ちしない。
        who = q.get("id") or q.get("name") or "?"
        for k in q:
            a, b = o.get(k), q[k]
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
                    and not isinstance(a, bool) and not isinstance(b, bool):
                if abs(a - b) <= 5e-3:
                    continue
            elif a == b:
                continue
            rows.append(("%s.%s" % (who, k), a, b))
    return rows


def audit(est, engine=False):
    """一邸ぶんの突き合わせ。書かない。`engine` が真なら器を持つ邸は器で全欄を焼き直す。"""
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
    r["counts"] = {}
    if est in ENGINES:
        if not engine:
            # ⚠ 器はあるが走らせていない(約 100 秒)。⛔ 「焼いた」と名乗らない — 指紋だけで見る。
            for col in im:
                if col not in META:
                    r["carried"].append((col, "器 %s.py はあるがこの走りでは焼いていない"
                                              "(`bake_impl.py %s` で焼き直す)" % (ENGINES[est], est)))
            r["carried"].sort(key=lambda t: t[0])
            r["carriedSrc"] = carried_src(im, r)
            r["carriedStale"] = bool(r.get("src") and r["carriedSrc"] != r["src"]["got"])
            r["engine"] = False
            return r
        fresh_all = run_engine(est)
        r["engine"] = True
        for col, fresh in fresh_all.items():
            if col in META:
                continue
            r["baked"][col] = fresh
            rows = []
            n = diff_deep(im.get(col), fresh, col, rows, cap=12)
            if n:
                r["counts"][col] = n
                r["diff"] += [(col,) + t for t in rows]
        # ⛔ 器が返さない欄が算出物に残っていれば、据え置きとして名指しで刷る(黙って合格にしない)。
        for col in im:
            if col not in META and col not in r["baked"]:
                r["carried"].append((col, "器 %s.py が返さない欄" % ENGINES[est]))
        r["carriedSrc"] = carried_src(im, r) if r["carried"] else None
        r["carriedStale"] = bool(r["carried"] and r.get("src") and r["carriedSrc"] != r["src"]["got"])
        return r
    for col in BAKEABLE:
        if col not in im:
            continue
        if poly is None and col in NEEDS_POLY:
            r["carried"].append((col, "区画 %s が parcels.json に無い" % est))
            continue
        try:
            fresh = BAKERS[col](poly, d, im)
        except Carried as e:
            # ⛔ 材料が足りない欄を**半分だけ焼かない**。据え置きとして名指しで刷る(規則19)。
            r["carried"].append((col, str(e)))
            continue
        r["baked"][col] = fresh
        rows = diff_rows(im[col], fresh)
        if rows:
            r["counts"][col] = len(rows)
        r["diff"] += [(col,) + t for t in rows]
    for col in im:
        if col in r["baked"] or col in ("of", "src", "at", "generator", "checks", "baked"):
            continue
        if any(c == col for c, _ in r["carried"]):
            continue
        r["carried"].append((col, CARRIED_WHY.get(col, "焼き手が main に無い")))
    r["carried"].sort(key=lambda t: t[0])
    # ⚠ 据え置きの欄が名乗る元の指紋。`src` と違えば「別の指図から焼かれたまま」= 未検査。
    r["carriedSrc"] = carried_src(im, r) if r["carried"] else None
    r["carriedStale"] = bool(r["carried"] and r.get("src")
                             and r["carriedSrc"] != r["src"]["got"])
    return r


def carried_src(im, r):
    """**据え置きの欄がどの指図から焼かれたか**の指紋。⭐ 一度ずれたら、その欄を誰かが焼き直すまで
    ずっと同じ値を持ち回る(⛔ 指紋を刷り直すたびに「今の指図から焼けた」と名乗らせない)。"""
    b = im.get("baked") or {}
    if b.get("carriedSrc"):
        return b["carriedSrc"]
    return (im.get("src") or {}).get("sha256")


def write(est, r):
    """焼ける欄だけ上書きし、指紋と焼いた履歴を刷り直す。⛔ 据え置きの欄はバイトごと触らない。"""
    im = json.load(open(r["impl"], encoding="utf-8"))
    cs = carried_src(im, r) if r["carried"] else None
    for col, fresh in r["baked"].items():
        im[col] = fresh
    at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    sash_p = os.path.join(DOC, est + "_sashizu.json")
    # ⛔⛔ **古い焼きを「新しい」と名乗らせない。**`src` の指紋は「焼ける欄がどの指図から出たか」で、
    #   据え置きの欄は別の指図から焼かれたままのことがある。⇒ 指紋は刷り直すが、**据え置きの欄が
    #   名乗る元**を `baked.carriedSrc` に残して、食い違いを報告で鳴らし続ける(規則19)。
    #   ⛔ carriedSrc を消さない ── 消すと「未検査」が黙って「合格」に化ける。
    if os.path.exists(sash_p):
        im["src"] = {"sha256": sha256(sash_p), "bytes": os.path.getsize(sash_p)}
    im["at"] = at
    im["generator"] = GEN
    # ⭕ **どの欄を誰が焼いたか**を残す。⛔ 全欄を焼いたように名乗らない —
    #   据え置きの欄は古い焼きのままで、「合格」ではなく「未検査」(規則19)。
    im["baked"] = {"at": at, "by": GEN,
                   "columns": sorted(r["baked"].keys()),
                   "carried": {c: w for c, w in r["carried"]},
                   "carriedSrc": cs,
                   "_": "columns = この焼き手が出し直した欄 / carried = 焼き手が main に無く据え置いた欄 / "
                        "carriedSrc = その据え置きの欄が焼かれた**当時の指図**の指紋"
                        "(`src.sha256` と違えば、据え置きの欄は今の指図から出ていない＝未検査)"}
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
        tot = sum(r["counts"].values())
        print("算出物の焼き手 — ⛔ %s: 焼き直すと変わる値が %d 件(欄 %s)"
              "(`python3 Tools/Sashizu/bake_impl.py %s --write`)"
              % (est, tot, "・".join("%s %d" % kv for kv in sorted(r["counts"].items())), est))
        shown = {}
        for col, where, a, b in r["diff"]:
            # 欄ごとに先頭 3 件まで(散布のように何万と変わる欄で他の欄を埋もれさせない)
            shown[col] = shown.get(col, 0) + 1
            if shown[col] <= 3:
                print("  ⛔ %-8s %-28s 今 %s → 焼き直し %s" % (col, where, a, b))
        n += tot
    if quiet:
        return n
    print("⭕ %s — 焼いた欄 %s / 食い違い %d 件"
          % (est, "・".join(sorted(r["baked"])) or "(無し)", sum(r["counts"].values())))
    # ⛔ 0 件は「合格」ではない。焼き手の無い欄は**一度も検め直されていない**。
    for col, why in r["carried"]:
        print("  ⚠ 据え置き %-9s — %s ＝ 未検査" % (col, why))
    # ⚠ 据え置きの欄が**別の指図から焼かれたまま**なら、指紋が緑でも鳴らし続ける(規則19)。
    if r.get("carriedStale"):
        print("  ⚠ 据え置きの欄は**別の指図から焼かれたまま**(当時 %s… / 今 %s…)"
              % (r["carriedSrc"][:12], r["src"]["got"][:12]))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("estate", nargs="?")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--deep", action="store_true", help="全邸でも器を走らせる(遅い)")
    a = ap.parse_args()
    ests = ([a.estate] if a.estate else
            sorted(os.path.basename(p)[:-len("_impl.json")] for p in glob.glob(os.path.join(DOC, "*_impl.json"))))
    if a.estate and not os.path.exists(os.path.join(DOC, a.estate + "_impl.json")):
        print("⛔ 算出物が無い: docs/Sashizu/%s_impl.json" % a.estate)
        return 2
    bad = 0
    for est in ests:
        # ⭐ 器は邸を名指したとき(か --deep)だけ走らせる。全邸の見張り(挨拶フック・20 秒)は指紋だけ。
        r = audit(est, engine=bool(a.estate) or a.deep)
        if r is None:
            continue
        if a.json:
            print(json.dumps({k: v for k, v in r.items() if k != "baked"}, ensure_ascii=False, default=str))
            continue
        if a.write:
            if not r["diff"] and not r["stale"]:
                print("⭕ %s — 焼き直しても変わらない(書かない)" % est)
                continue
            was, cs0 = r["stale"], r["carriedSrc"]
            write(est, r)
            print("⭕ %s — 欄 %s を焼き直した(%d 件を上書き)"
                  % (est, "・".join(sorted(r["baked"])) or "(無し)", sum(r["counts"].values())))
            for col, why in r["carried"]:
                print("  ⚠ 据え置き %-9s — %s" % (col, why))
            # ⛔ 「指紋が緑になった＝全部いまの指図から焼けた」と読ませない。据え置きの欄は
            #    当時の指図のまま(= 未検査)で、その指紋は `baked.carriedSrc` に残してある(規則19)。
            if was and r["carried"]:
                print("  ⚠ 指紋を刷り直した(指図 %s…)が、**据え置きの欄はいまの指図から焼かれていない**"
                      "(当時 %s…)。⇒ `baked.carriedSrc` に残した。"
                      % (r["src"]["got"][:12], (cs0 or "?")[:12]))
                print("  ⭕ 焼き手が要る欄は掲示板へ起票すること。")
            continue
        bad += report(r, a.quiet)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
