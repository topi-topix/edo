#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""山王の算出物 `sanno_impl.json` の**焼き手の器**(EDO-0397・2026-09-23)。⛔ 単独では走らせない。

⭐ **出所。**邸ごとの生成器 `build_sanno_sashizu.py` の**最終版**(枝 sashizu/sanno の bbdb6b5a・
2026-09-19 19:41)から、`--export-impl`(= `main_export_impl`)が**実際に辿る関数だけ**を依存の閉包で
切り出した写し(22,579 行 → この器)。⛔ **式を作り直していない** ── 関数の本文は元のまま。
  ⚠ 本線の最後の版(afb529c2^ = 7880850c)ではない。本線に載らなかった枝の3コミット
    (法面の「一枚の土の面」・楼門前の輪郭の穴・法面の植栽を土の厚みへ)を含む版で、
    `sanno_impl.json` はずっとこの版で焼かれていた。7880850c の版で焼くと造成の格子と庭が別物になる。
⭕ **検証**: 09-22 以前の指図(ec137264…)をこの器に通すと、据え置いていた10欄
  (dem/grid/terraces/graded/stairs/runs/routes/tamagaki/setae/planting)が当時の算出物と**一致**する
  (tamagaki.spec の地の文 `_*` だけは 09-21 の文章分離で指図から抜けたので出ない)。

⛔ ここへ設計値を足さない・式を直さない。直すなら**指図の欄**(規則4)。この器は図を刷らない
  (図は共通の生成器 `build_sashizu.py sanno`)。呼び口は `bake()` 一つで、`bake_impl.py` だけが呼ぶ。
⚠ 走るのに約 100 秒かかる(造成の格子と散布)。挨拶フックの `--quiet` はこれを走らせず指紋だけ見る。
"""
import json, sys, math, os, re, html, bisect, collections, copy, hashlib, heapq


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DOC = os.path.join(ROOT, "docs/Sashizu")


JSON = os.path.join(DOC, "sanno_sashizu.json")


TSUBO = 3.305785


def PL(pts, stroke="var(--ink)", sw=1.0, fill="none", dash=None, op=None, close=False):
    dd = "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")
    a = '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f"' % (dd, fill, stroke, sw)
    if dash: a += ' stroke-dasharray="%s"' % dash
    if op is not None: a += ' opacity="%.2f"' % op
    return a + "/>"


# ---------------------------------------------------------------- グリッド
class G(object):
    def __init__(self, d):
        g = d["grid"]["keidai"]
        self.ken = d["const"]["ken"]
        self.x0, self.z0 = g["x0"], g["z0"]

    def W(self, u, v): return (self.x0 + u * self.ken, self.z0 + v * self.ken)
    def U(self, x): return (x - self.x0) / self.ken
    def V(self, z): return (z - self.z0) / self.ken


def gap_split(a, b, o, horiz):
    """run/wall の開口(gapU/gapV/gapHalf)で区間を割る。horiz=True なら u 方向に走る辺。

    2026-08-23 検図 — 指図が宣言した開口が図に一つも描かれていなかったので入れた。
    """
    hw = o.get("gapHalf")
    if not hw:
        return [(a, b)]
    c = o.get("gapU") if horiz else o.get("gapV")
    if c is None:
        c = o.get("gapV") if horiz else o.get("gapU")
    if c is None:
        return [(a, b)]
    i = 0 if horiz else 1
    lo, hi = min(a[i], b[i]), max(a[i], b[i])
    g0, g1 = c - hw, c + hw
    if g1 <= lo or g0 >= hi:
        return [(a, b)]
    out = []
    def pt(v):
        q = list(a)
        q[i] = v
        q[1 - i] = a[1 - i] + (b[1 - i] - a[1 - i]) * ((v - a[i]) / (b[i] - a[i]) if b[i] != a[i] else 0)
        return q
    if g0 > lo: out.append((pt(lo), pt(g0)))
    if g1 < hi: out.append((pt(g1), pt(hi)))
    return out


def clip_gaps(a, b, gaps):
    """線分から `gaps`=[(u,v,半幅)] の円い開口を抜く。折れ線の任意の向きに効く。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    if L < 1e-9: return [(a, b)]
    cut = []
    for gu, gv, hw in gaps:
        t = ((gu - a[0]) * dx + (gv - a[1]) * dz) / (L * L)
        px, pz = a[0] + dx * t, a[1] + dz * t
        dd = math.hypot(gu - px, gv - pz)
        if dd >= hw: continue
        half = math.sqrt(max(0.0, hw * hw - dd * dd)) / L
        cut.append((max(0.0, t - half), min(1.0, t + half)))
    if not cut: return [(a, b)]
    cut.sort()
    out, cur = [], 0.0
    P = lambda t: [a[0] + dx * t, a[1] + dz * t]
    for c0, c1 in cut:
        if c1 <= 0.0 or c0 >= 1.0: continue
        if c0 > cur + 1e-6: out.append((P(cur), P(c0)))
        cur = max(cur, c1)
    if cur < 1.0 - 1e-6: out.append((P(cur), P(1.0)))
    return out


# 口の縁に残る**切れ端**の下限[間](1.8 mm)。⛔ 設計値ではなく数値の残りかすを落とす閾値。
# ⚠ 2026-09-07 検図11巡目 高1 の後始末 — 口の芯と半幅を丸めると、抜いたはずの区間の端に
#   0.1 mm 級の断片が残り、**そこだけが透塀の 0.149 m 隣に立っている**ように測れた。
SEG_MIN_KEN = 0.001


def run_segs(o):
    """run/wall を開口で割った描画区間。折れ線にも対応。⛔ 1 mm 級の切れ端は run ではない。"""
    out = []
    for a, b in segs(o):
        horiz = abs(b[0] - a[0]) >= abs(b[1] - a[1])
        for p, q in gap_split(a, b, o, horiz):
            out += clip_gaps(p, q, o.get("gaps") or [])
    return [(a, b) for a, b in out if math.hypot(b[0] - a[0], b[1] - a[1]) > SEG_MIN_KEN]


def run_band_uv(r, bw):
    """run(a→b)の両側へ半幅 bw[間]の四隅[uv]。⭐ 斜めの run でも向きに沿う(2026-09-14)。"""
    a, b = r["a"], r["b"]
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    nx, ny = -(b[1] - a[1]) / L * bw, (b[0] - a[0]) / L * bw
    return [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]


def run_len_ken(o):
    """run/wall の **開口を抜いた実長**[間]。⛔ **発注量はこちら**(節点間の総和ではない)。

    ⚠ 2026-09-07 検図10巡目 中1 — 図と run の表が刷っていたのは `ken`(節点間の総和)で、
    **石段の頭・勝手口・中門・潜りの開口を一つも抜いていなかった**。`bom`「境内の外周の柵」は
    『延長は図が算出する(開口を抜いた実長)』と宣言しており、**この数がそのまま新造の発注量になる**。
    ⛔ 二本の物差しを混ぜない — 史料拘束(透塀の周長)は `run_nodes_ken` の側で読む。
    """
    if not o.get("pts") and (o.get("a") is None or o.get("b") is None): return 0.0
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in run_segs(o))


def gap_ledger(o):
    """run の**切れ目の内訳**[間] ── 折れ線 / 宣言した口 / 宣言していない切れ目(`skips`)。

    ⭐ **2026-09-07 検図12巡目 低1 で起こした。**口は**芯まわりの円**で切るので、平場の折れ返しに
    載った口は**複数の区間をまとめて食う**。⛔ そのため「折れ線 − 宣言した開口幅 − skip」は実長に
    ならず、**読者が足し算で検算できない**。⛔ 宣言幅と**実際に抜けた長さ**の両方を刷る。
    ⛔ 数を json に持たない — すべて折れ線と口の半幅からの従属値。

    ⭐ **軸の口(`gapU`/`gapV` + `gapHalf`)も帳簿に載せる**【低 検図1巡目 → 2026-09-18】──
      旧版の「折れ線」は `run_segs` から採っており、**軸の口はすでに抜けた後の長さ**だった。
      ⇒ 中門の口(`Sukibei_E` 2.840 m)と南の潜り(`Sukibei_S` 1.818 m)は、抜けているのに
      帳簿の「口が抜いた」が 0.000 と刷られ、⛔ **差が原理的に出ない帳簿**になっていた。
      ⭕ 「折れ線」は**節点間の総和**(口を一つも抜かない)に改め、軸の口を別の欄で持つ。
    """
    gs = o.get("gaps") or []
    sk = o.get("skips") or []
    dec = [q for q in gs if q not in sk]

    def L(g2, axis=True):
        q = dict(o); q["gaps"] = g2
        if not axis:
            for k9 in ("gapU", "gapV", "gapHalf"): q.pop(k9, None)
        return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in run_segs(q))
    raw = L([], axis=False)          # 折れ線(口を一つも抜かない = 節点間の総和)
    L0 = L([])                       # 軸の口(`gapU`/`gapV`)だけ抜いた長さ
    ax = 1 if (o.get("gapU") is not None or o.get("gapV") is not None) \
              and o.get("gapHalf") is not None else 0
    return {"折れ線": raw, "実長": L(gs),
            "軸の口の宣言幅": 2.0 * float(o.get("gapHalf") or 0.0) * ax,
            "軸の口が抜いた": raw - L0, "軸の口の数": ax,
            "口の宣言幅": sum(2 * q[2] for q in dec), "口が抜いた": L0 - L(dec), "口の数": len(dec),
            "skip の宣言幅": sum(2 * q[2] for q in sk), "skip が抜いた": L0 - L(sk), "skip の数": len(sk)}


def run_nodes_ken(o):
    """run の **節点間の総和**[間](開口を含む)。⛔ **発注量ではない。**

    透塀だけはこちらが史料拘束(周長 486.01尺 = 147.28 m【S】)と突き合わせる数で、
    宣言 `ken` があればそれを、無ければ折れ線 a→b の総和を採る。
    """
    if o.get("ken"): return float(o["ken"])
    if not o.get("pts") and (o.get("a") is None or o.get("b") is None): return 0.0
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs(o))


def band(pts, PX, PY, LEN, w, fill, stroke, op=0.55, sw=0.8):
    """折れ線を実幅の帯として描く。角は法線の二等分(留め)で継ぐ。

    2026-08-23 — 参道を「適当な点線」で描いていたのをユーザーに指摘されて入れた。
    """
    import math as _m
    n = len(pts)
    left, right = [], []
    for i, q in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(n - 1, i + 1)]
        if i == 0: a = q
        if i == n - 1: b = q
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = _m.hypot(dx, dz) or 1.0
        nx, nz = -dz / L, dx / L
        hw = w / 2
        if 0 < i < n - 1:                      # 留め: 折れ角で半幅を w/2/cos(θ/2) に補正(検図 2026-09-06)
            ux, uz = q[0] - a[0], q[1] - a[1]; vx, vz = b[0] - q[0], b[1] - q[1]
            lu = _m.hypot(ux, uz) or 1.0; lv = _m.hypot(vx, vz) or 1.0
            c = _m.hypot(ux / lu + vx / lv, uz / lu + vz / lv) / 2.0
            hw = w / 2 / max(c, 0.3)
        left.append((q[0] + nx * hw, q[1] + nz * hw))
        right.append((q[0] - nx * hw, q[1] - nz * hw))
    ring = left + right[::-1]
    out = [PL([(PX(x), PY(z)) for x, z in ring], fill=fill, op=op,
              stroke=stroke, sw=sw, close=True)]
    out.append(PL([(PX(x), PY(z)) for x, z in pts], stroke=stroke, sw=0.7, dash="6 4", op=0.9))
    return out


# ---------------------------------------------------------------- 植栽(社叢・境内の立木・参道沿い・前庭)
def garden_poly(gd):
    """gardens の面(uv)。多角形 `poly` があればそれ、無ければ矩形。面を持たない項(社叢)は None。

    ⚠ 2026-09-06 — 境内の立木3区が矩形から多角形になったので、`lp.rect` 決め打ちをやめた。
    """
    if gd.get("poly"):
        return [(q[0], q[1]) for q in gd["poly"]]
    if gd.get("uv"):                      # 社叢の帯4(多角形を持つ帯)も同じ形で読める
        return [(q[0], q[1]) for q in gd["uv"]]
    if gd.get("u0") is None:
        return None
    return [(gd["u0"], gd["v0"]), (gd["u1"], gd["v0"]),
            (gd["u1"], gd["v1"]), (gd["u0"], gd["v1"])]


def shrub_ok(gd, q):
    """点が**その区の低木を撒く面**の中か(枠 ∩ 輪郭から樹冠半径以上内)。"""
    sh = gd.get("shrubs") or {}
    if not sh.get("box"): return False
    u0, v0, u1, v1 = sh["box"]
    if not (u0 <= q[0] <= u1 and v0 <= q[1] <= v1): return False
    P = [(x, y) for x, y in (gd.get("poly") or [])]
    if not P: return True
    r = sh.get("crownRKen", 0.0)
    return in_poly(q, P) and min(_pt_seg(q, P[i], P[(i + 1) % len(P)])
                                 for i in range(len(P))) >= r


# ---------------------------------------------------------------- 井戸屋形(前庭の帯の北の端)
def ido_rects(d):
    """井戸屋形の面 ── **芯と寸法からの従属値**。⛔ 矩形を json に書かない(規則4)。

    石敷・軒先・浸透枡・井桁は (u0,v0,u1,v1)、柱は点の列。
    ⭐ `nokiDeKen` / `hafuDeKen` は**柱芯からの出**で、軒先が石敷の縁と一致するように取ってある
    (雨落ちが石敷に落ちる)。一致は `ido_check` が毎回測る。
    """
    io = d.get("ido")
    if not io: return None
    u, v = io["uv"]
    ken = d["const"]["ken"]
    h = io["ishikiKen"] / 2.0
    p = io["hashiraPitchKen"] / 2.0
    # ⭐ 井桁は**外形**で採る(2026-09-07 裁定2)— 内径 `igetaShaku` 尺 + 見付の両側。
    g = io["igetaShaku"] / 6.0 / 2.0 + io.get("igetaMitsukeM", 0.0) / ken
    m = io["masuKen"] / 2.0
    mu, mv = io["masuUV"]
    return {"石敷": (u - h, v - h, u + h, v + h),
            "軒先": (u - p - io["nokiDeKen"], v - p - io["hafuDeKen"],
                     u + p + io["nokiDeKen"], v + p + io["hafuDeKen"]),
            "井桁": (u - g, v - g, u + g, v + g),
            "浸透枡": (mu - m, mv - m, mu + m, mv + m),
            "柱": [(u - p, v - p), (u + p, v - p), (u + p, v + p), (u - p, v + p)]}


def tamagaki_gap_span(d, gd, e, a, b):
    """辺の**開口**の沿線区間 (s0, s1)[間]。`gapFrom` が指す面を辺へ射影して出す。

    ⭐ 2026-09-06b — 玉垣の東面は**井戸の口**で開く。⛔ 開口の値を json に二重に書かない。
    """
    src = e.get("gapFrom")
    if not src: return None
    if src == "ido":
        R = ido_rects(d)
        if not R: return None
        u0, v0, u1, v1 = R["石敷"]
        Q = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    else:
        raise SystemExit("玉垣の辺『%s』の gapFrom が引けない: %s" % (e["name"], src))
    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    ss = [(q[0] - a[0]) * tx + (q[1] - a[1]) * tz for q in Q]
    s0, s1 = max(0.0, min(ss)), min(ln, max(ss))
    return None if s1 - s0 <= 1e-9 else (s0, s1)


def tamagaki_gaps(d, gd, e, a, b):
    """辺の**開口**の沿線区間の列 [(s0,s1)]。井戸の口(`gapFrom`)と**木戸**の両方。

    ⭐ 2026-09-06c 裁定4 — 木戸も辺を割る(開口の両脇に柱が立つ)。⛔ 木戸を引かない実延長を刷らない。
    """
    out = []
    gp = tamagaki_gap_span(d, gd, e, a, b)
    if gp is not None: out.append(gp)
    kd = (gd.get("tamagaki") or {}).get("kido")
    if kd and kd.get("edge") == e["i"]:
        ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        s = ((kd["uv"][0] - a[0]) * (b[0] - a[0]) + (kd["uv"][1] - a[1]) * (b[1] - a[1])) / ln
        hw = kd["wM"] / 2.0 / d["const"]["ken"]
        s0, s1 = max(0.0, s - hw), min(ln, s + hw)
        if s1 - s0 > 1e-9: out.append((s0, s1))
    return sorted(out)


def tamagaki_edge_runs(d, gd, e, a, b):
    """辺の**実際に立つ区間**の列 ((a,b) の列)。開口(井戸の口・木戸)を抜く。"""
    gaps = tamagaki_gaps(d, gd, e, a, b)
    if not gaps: return [(a, b)]
    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    P = lambda s: (a[0] + tx * s, a[1] + tz * s)
    out = []
    s = 0.0
    for g0, g1 in gaps:
        if g0 - s > 1e-9: out.append((P(s), P(g0)))
        s = max(s, g1)
    if ln - s > 1e-9: out.append((P(s), b))
    return out


def tamagaki_edges(d, gd):
    """玉垣の辺 ── (名, a, b, 立てるか, **実長**[間], 立つ区間の列)。

    ⛔ 延長を json に書かない(辺と開口からの従属値)。
    ⭐ 2026-09-06b — 辺が**開口を持てる**ようになったので、長さは開口を抜いた実長を返す。
    """
    tg = gd.get("tamagaki")
    P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
    if not tg or not P: return []
    out = []
    for e in tg["edges"]:
        a, b = P[e["i"]], P[(e["i"] + 1) % len(P)]
        rs = tamagaki_edge_runs(d, gd, e, a, b) if e.get("fence") else [(a, b)]
        L = sum(math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]) for q in rs)
        out.append((e["name"], a, b, bool(e.get("fence")), L, rs))
    return out


def kido_rect(gd, ken):
    """木戸の**開口の裏へ低木を植えない矩形**(uv の4点)。開口 ± 半幅 × 内へ `insideKen` 間。"""
    tg = gd.get("tamagaki") or {}
    kd = tg.get("kido")
    P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
    if not kd or not P: return None
    a, b = P[kd["edge"]], P[(kd["edge"] + 1) % len(P)]
    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    cu = sum(q[0] for q in P) / len(P); cv = sum(q[1] for q in P) / len(P)
    nx, nz = -tz, tx
    if (cu - kd["uv"][0]) * nx + (cv - kd["uv"][1]) * nz < 0: nx, nz = tz, -tx   # 内向き
    hw = kd["wM"] / 2.0 / ken
    dp = kd.get("insideKen", 1.0)
    u0, v0 = kd["uv"][0] - tx * hw, kd["uv"][1] - tz * hw
    u1, v1 = kd["uv"][0] + tx * hw, kd["uv"][1] + tz * hw
    return [(u0, v0), (u1, v1), (u1 + nx * dp, v1 + nz * dp), (u0 + nx * dp, v0 + nz * dp)]


def plane_y(d, pl):
    """面の**天端**[m 海抜] ── 正典は `terraces[].y`。造成しない面は None。

    ⚠ 2026-09-07 検図8巡目 中2 — 天端が `planes[].y` と `terraces[].y` の**二重持ち**で、
    幾何の側(`design_y`・切盛・法面・断面・地山)は 8 箇所とも `terraces[].y` を読むのに、
    Δ の検査と面の表だけが `planes[].y` を読んでいた。⛔ `terraces[Keidai].y` を動かしても
    検査は旧い天端を刷り続け(=物差しが図から外れている)。**`planes[].y` は落とした。**
    ⛔ 一つの面が高さの違う terrace を抱えたら検査『面の天端の出所』が⛔で止める。
    """
    ys = [t["y"] for t in d["terraces"]
          if t["name"] in (pl.get("terraces") or []) and t.get("y") is not None]
    return ys[0] if ys else None


def shrub_box(gd):
    """低木を撒く面の**枠**(uv の4点)。⚠ 枠の中がすべて撒ける訳ではない — 実際の面は
    `shrub_ok`(枠 ∩ 帯の輪郭から `crownRKen` 以上内)で、帯の折れに追随する。"""
    sh = gd.get("shrubs") or {}
    if not sh.get("box"): return None
    u0, v0, u1, v1 = sh["box"]
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def island_shrubs(gd, ken):
    """帯(旧・植込みの島)の照葉低木の位置 ── **面からの従属値**。⛔ 本数を json に書かない。

    `shrubs.box`(2026-09-06b の帯)があればその面、無ければ玉垣の芯線から**芯々の半分**だけ
    内へ寄せた面を、芯々の格子で走査する。⭐ どちらの形でも**木戸の開口の裏は空ける**。
    """
    sh = gd.get("shrubs")
    P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
    if not sh or not P: return []
    st = sh["spacingM"] / ken
    # ⭐ **木戸の開口の裏は空ける**(2026-09-06 検図4巡目 中4 — 開口の真裏 0.60m に低木が立っていた)
    kr = kido_rect(gd, ken)
    B = shrub_box(gd)
    # ⭐ **千鳥に据える**【B-5 庭方 2026-09-08 十六巡目】── 一列おきに芯々の**半分**だけ u をずらす。
    #    ⛔ 面も芯々も変えない(⛔ ずらし量を json に持たない — `spacingM` の半分)。
    #    ⚠ 旧式は u 3 列 × v 1.2 m ちょうど刻みの**直交格子**で、⛔ 図の中で唯一、目に格子と映った。
    stag = st / 2.0 if sh.get("stagger") else 0.0
    # ⭐ **正三角の格子**【中7 庭方 2026-09-09 十七巡目】── ⛔ 行の間隔を数で持たない
    vst = (st * math.sqrt(3.0) / 2.0) if "正三角" in (sh.get("lattice") or "") else None
    scan = ((lambda Q: _stagger_scan(Q, st, stag, vst)) if (stag or vst)
            else (lambda Q: poly_scan(Q, st)))
    if B:
        # ⭐ **輪郭から樹冠半径以上**(2026-09-06 検図5巡目 中12 — 帯が v3.5 で折れるのを枠が見ておらず、
        #    低木1本が袖塀 `Ita_Niou_N` へ 0.546m めり込んでいた)
        src = (q for q in scan(B) if shrub_ok(gd, q))
    else:
        ins = st / 2.0
        src = (q for q in scan(P)
               if min(_pt_seg(q, P[i], P[(i + 1) % len(P)]) for i in range(len(P))) >= ins)
    return [q for q in src if not (kr and in_poly(q, kr))]


def _stagger_scan(P, step, shift, vstep=None):
    """**千鳥の走査** ── v の一列おきに u を `shift` だけずらす(⛔ 面も芯々も変えない)。

    ⭐ **行の間隔 `vstep`**【中7 庭方 2026-09-09 十七巡目】── 宣言が `正三角` なら
      芯々 × √3/2(⛔ 数を json に持たない)。⚠ 旧式は行の間隔も芯々のままだったので、
      斜めの芯々が芯々の 1.12 倍あり(√(1 + 1/4))、**塊にならなかった**。
    """
    us = [q[0] for q in P]; vs = [q[1] for q in P]
    vs9 = vstep or step
    v = min(vs) + vs9 / 2.0
    row = 0
    while v < max(vs):
        u = min(us) + step / 2.0 + (shift if row % 2 else 0.0)
        while u < max(us):
            if in_poly((u, v), P): yield (u, v)
            u += step
        v += vs9
        row += 1


def cluster_boxes(c):
    """塊の箱(uv の [u0,v0,u1,v1])。`box` 単数と `boxes` 複数の両方に対応。"""
    if c.get("boxes"): return [tuple(q) for q in c["boxes"]]
    if c.get("box"):   return [tuple(c["box"])]
    return []


def cluster_polys(c):
    """塊の**輪郭**(uv の多角形の列)。⭐ 2026-09-08 十六巡目 C-1 で起こした。

    ⛔ **軸平行の箱で代表させない** ── 参道の林縁は『高木の縁の線に沿う平行四辺形』で、
    箱で囲むと幅が 9.1 間になって林縁でなくなる(**焼き出しが `unresolved` になった真因**)。
    `poly`(`derive_clusters` が線から起こす)があればそれ、無ければ箱の四隅。
    """
    if c.get("poly"): return [[(q[0], q[1]) for q in c["poly"]]]
    return [[(u0, v0), (u1, v0), (u1, v1), (u0, v1)] for u0, v0, u1, v1 in cluster_boxes(c)]


def cluster_spacing(d, c):
    """塊の中の**芯々**[間]。`spacing` があればそれ、無ければ `spacingFrom` の従属値。

    ⛔ 数を二重に持たない(規則4)。⭐ **2026-09-09 十八巡目に `spacingFrom`
    (`takagiEdgeLine.firstRowSpacing` の下端)の道を落とした**【指4 庭方】── 参道の林縁は
    一列でなくなり、芯々の正典は `groups` の `groupSpacingKen` / `groupGapKen` になった。
    """
    if c.get("spacing"): return float(c["spacing"])
    return None


def cluster_n(c):
    """塊の本数。範囲 [lo,hi] で書かれていれば中央を採る。

    ⭐ **`n` が無ければ `mix` の割り前の和**(2026-09-08)── ⛔ 同じ本数を `n` と `mix` の
    二箇所に持たない(規則4)。⚠ `mix` を持つ塊は `mix` が正典。
    """
    n = c.get("n")
    if isinstance(n, (list, tuple)): return sum(n) / 2.0
    if n is None and c.get("mix"): return float(sum(q[1] for q in cluster_mix(c)))
    return float(n or 0)


def edge_offset(d, idx, ins_ken):
    """`polygon` の辺 idx=[i,j] を内側へ ins_ken[間] 寄せた線分(uv)。参道の柵・高木の縁の線の正典。"""
    g = G(d)
    a, b = d["polygon"][idx[0]], d["polygon"][idx[1]]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    nx, nz = dz / L, -dx / L                       # 社地は辺の西 = 内向き
    t = ins_ken * d["const"]["ken"]
    return [(g.U(a[0] + nx * t), g.V(a[1] + nz * t)),
            (g.U(b[0] + nx * t), g.V(b[1] + nz * t))]


def touch_edge_idx(d, areas_src):
    """**道敷に接する社地の辺**を番号つきで返す [(i, a, b, 長さ[m])]。⛔ 辺の番号を書かせない。

    ⭐ **同定の式は `planting.bandDef.rinenEdgeRule` 一本**(辺の中点と両三分点がすべて道敷から
      `rinenEdgeTouchKen` 以内)【決4 庭方 2026-09-09 十八巡目】── ⛔ 二つ持たない。
    ⚠ 引数は `areasFrom` の綴り(`sando.area` / `fumotomichi[].area`)。
    """
    g = G(d)
    soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    A = []
    for s9 in (areas_src or []):
        if s9.startswith("sando") and d.get("sando", {}).get("area"):
            A.append([(g.U(x), g.V(z)) for x, z in d["sando"]["area"]])
        elif s9.startswith("fumotomichi"):
            A += [[(g.U(x), g.V(z)) for x, z in f["area"]]
                  for f in d.get("fumotomichi", []) if f.get("area")]
    tol = (d["planting"]["bandDef"].get("rinenEdgeTouchKen") or _TOUCH_KEN)
    ken = d["const"]["ken"]
    out = []
    for i in range(len(soch)):
        a, b = soch[i], soch[(i + 1) % len(soch)]
        for Q in A:
            ok = True
            for t in (1.0 / 3.0, 0.5, 2.0 / 3.0):
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                dd = 0.0 if in_poly(p, Q) else min(_pt_seg(p, Q[j], Q[(j + 1) % len(Q)])
                                                   for j in range(len(Q)))
                if dd > tol: ok = False; break
            if ok:
                out.append((i, a, b, math.hypot(b[0] - a[0], b[1] - a[1]) * ken))
                break
    return out


_EDGE_NOTE = []


def derive_edges(d):
    """`edgeFrom` を宣言した物の **`fromEdge`(辺の番号)を毎回引き直す**【決4 庭方 十八巡目】。

    ⛔ **番号を json に書かない。**同定は `touch_edge_idx`、**どの辺を張るか**は `spanFrom` の
      とおり「宣言の `uv`(または run の a/b)がその辺の `insetKen` オフセットに載る辺」。
    ⛔ **一致する辺が無ければ番号を立てない** ── `sando_offset_check` が⛔で止める
      (⛔ 黙って近い辺を当てて図を組ませない)。
    〔記録〕同定した辺を**全部、長さつきで**残す(⛔ 黙って一本だけ使わない・規則19)。
    """
    del _EDGE_NOTE[:]
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    items = [(tl, [tuple(q) for q in (tl.get("uv") or [])], "高木の縁の線")] if tl.get("edgeFrom") else []
    for r in d["runs"]:
        if r.get("edgeFrom"): items.append((r, [tuple(r["a"]), tuple(r["b"])], r["name"]))
    for o, pts, nm in items:
        src = o.get("areasFrom")
        if src is None and o is not tl: src = tl.get("areasFrom")
        E = touch_edge_idx(d, src)
        _EDGE_NOTE.append((nm, [(i, L) for i, _a, _b, L in E]))
        ins = o.get("insetKen")
        if ins is None: ins = tl.get("insetKen")
        hit = None
        for i, _a, _b, _L in E:
            want = edge_offset(d, [i, (i + 1) % len(d["polygon"])], ins)
            if pts and max(min(math.hypot(q[0] - w[0], q[1] - w[1]) for w in want)
                           for q in pts) <= 0.02:
                hit = i; break
        o["fromEdge"] = ([hit, (hit + 1) % len(d["polygon"])] if hit is not None else None)


def fumiishi_rects(d):
    """踏石の矩形(uv)。**`from` から従属して算出する** — 座標を二重に持たない(規則5)。"""
    g = G(d)
    ken = d["const"]["ken"]
    src = list((d["sando"].get("roadside") or {}).get("fumiishi", []))
    src += list((d["terraces"][1].get("surface") or {}).get("fumiishi", []))
    out = []
    for f in src:
        kind, _, nm = f.get("from", "").partition(":")
        dp = f.get("depthKen", 1.0)
        if kind == "torii":
            t = [q for q in d["torii"] if q["name"] == nm and q.get("pos")]
            if not t: continue
            u, v = g.U(t[0]["pos"][0]), g.V(t[0]["pos"][1])
            h = f.get("squareKen", 1.0) / 2.0
            out.append((f["name"], u - h, v - h, u + h, v + h))
        elif kind == "gate":
            gt = [q for q in d["gates"] if q["name"] == nm]
            if not gt: continue
            gt = gt[0]; pl = gt["plan"]
            # ⭐ **踏石の幅は戸口の内法**(`monguchiKen`)。三間一戸は三間の幅に戸口ひとつで、
            #    両脇間は連子。⛔ `plan.dv`(桁行の全幅)を戸口として敷かない(2026-09-06 検図4巡目 中10)
            # ⛔ 東西の面に敷く踏石は**東西に抜ける門**にしか敷けない(K004)── 黙って東西で敷かない
            if not gate_face_is_pass(gt, "東" if f.get("side") == "E" else "西"):
                raise SystemExit("踏石『%s』は門『%s』の東西の面に敷くが、門が東西に抜けていない — "
                                 "奥行 du を東西に取れない" % (f["name"], nm))
            hu, hv = pl["du"] / 2.0, gt.get("monguchiKen", pl["dv"]) / 2.0
            if f.get("side") == "E":
                out.append((f["name"], gt["u"] + hu, gt["v"] - hv, gt["u"] + hu + dp, gt["v"] + hv))
            else:
                out.append((f["name"], gt["u"] - hu - dp, gt["v"] - hv, gt["u"] - hu, gt["v"] + hv))
        elif kind == "kaidan":
            k = [q for q in d["kaidans"] if q["name"] == nm]
            if not k: continue
            k = k[0]
            hw = kaidan_wken(d, k) / 2.0
            u, v = k["a"]
            if f.get("side") == "S":
                out.append((f["name"], u - hw, v - dp, u + hw, v))
            else:
                out.append((f["name"], u - hw, v, u + hw, v + dp))
    return out


def fumitome_polys(d):
    """**石段の頭の踏み止めの敷石**(多角形 uv)【石垣の設計 2026-09-14 ①】── `kaidans[].fumitome.poly`。"""
    return [(k["name"] + "の頭の踏み止め", [(q[0], q[1]) for q in k["fumitome"]["poly"]])
            for k in d["kaidans"] if (k.get("fumitome") or {}).get("poly")]


# ================================================================ 植栽の幾何(2026-09-06)
# ⛔ 数値の正典は json(設計値)と docs/asset-index.tsv(部材の実寸・三角数)。
#    ここには**式と作図と検査だけ**を置き、寸法も本数も書かない(CLAUDE.md 規則4)。
_AIDX = {}


def asset_index():
    """`docs/asset-index.tsv` を読む。**樹の実寸(幅×丈×奥行)・三角数の正典**。

    ⚠ 指図(json)には写さない — 部材を差し替えたら目録が変わり、写した値だけが古く残る。
    ⚠ **fbx も読む**(自作の木は prefab を持たず `EdoAssets.Own.*` が fbx を直に指す)。
    """
    if _AIDX: return _AIDX
    with open(os.path.join(ROOT, "docs/asset-index.tsv"), encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("#"): continue
            c = ln.rstrip("\n").split("\t")
            if len(c) < 12 or c[0] == "path" or c[3] not in ("prefab", "fbx"): continue
            if c[3] == "fbx" and c[1] in _AIDX: continue
            try:
                rec = {"sx": float(c[4]), "sy": float(c[5]), "sz": float(c[6]), "tris": int(c[9])}
            except ValueError:
                continue
            if c[3] == "prefab" or c[1] not in _AIDX: _AIDX[c[1]] = rec
    return _AIDX


def part_geom(pt):
    """部材1点の素の見え寸 (樹冠径 m, 丈 m, 三角数)。目録に無ければ None。"""
    rec = asset_index().get(pt.get("prefab"))
    if rec is None: return None
    return (max(rec["sx"], rec["sz"]), rec["sy"], rec["tris"])


# 部材名・API の雛形に開けてある「大きさ」の穴。⛔ 綴りは json の `sizeRule.sizes` が正典。
_SIZE_HOLE = "{size}"


def mune_ornament(d, m=None):
    """**棟飾り(鬼板・置千木)の丈**[m] と その出所。⛔ 数を図に写さない(規則4)。

    ⭐ **目録 `docs/asset-index.tsv` の丈は『鬼の頂』であって大棟ではない**
    【高2 考証19巡目 → 2026-09-09】── `const.muneHeightRule` は棟飾りを含まないと定めたので、
    棟高は **目録の丈 − ここ** の従属値になる。
    ⚠ **部材方の報告が届くまでは暫定値**(`const.muneOrnamentProvisionalM`)で、
      ⛔ **『暫定』と名乗ったまま**使う(⛔ 設計値として通さない)。
    戻り (丈[m], 出所の語) — どちらも無ければ (None, None)。
    """
    c = d["const"]
    if m is not None and m.get("muneOrnamentM") is not None:
        return float(m["muneOrnamentM"]), "棟ごとの宣言(部材方の実測)"
    # ⭐ **棟ごとの暫定値**【B-1 検図22巡目 → 2026-09-09 十九巡目】── ⛔ **`const` の一律で
    #   引いてはならない**。部材の生成器が自ら『引けない』と言っている棟が三つある
    #   (向拝は大棟を持たない ／ 両下造は鬼が無いので値は変わらない)。
    if m is not None and m.get("muneOrnamentProvisionalM") is not None:
        return (float(m["muneOrnamentProvisionalM"]),
                "⚠ **暫定値 — この棟の棟飾りは測られていない**(部材方の報告待ち)")
    if c.get("muneOrnamentM") is not None:
        return float(c["muneOrnamentM"]), "`const.muneOrnamentM`"
    return None, None


def mune_h(d, m):
    """棟高[m]。⛔ **測り方の正典は `const.muneHeightRule` 一本**(裁定 2026-09-09)。

    ⭐ 出所は二つだけ ── ① `munes[].h`(実測が返って**数で決まった**棟)
    ② `munes[].partFrom` が指す**目録の部材の丈 − 棟飾りの丈**(⛔ 図が写さない・規則4)。
    どちらも無ければ None(= 棟高が引けない)。⛔ 類型で埋めない(規則7)。
    ⭐ **棟飾りを引く**【高2 考証19巡目 → 2026-09-09】── ⛔ 目録が測っているのは**鬼の頂**で、
      物差しが『⛔ 棟飾りを含まない』と定めた値ではなかった(⛔ 定義を書いただけで測る対象は
      変わっていなかった)。
    """
    if m.get("h") is not None: return float(m["h"])
    pf = m.get("partFrom")
    if not pf: return None
    g0 = part_geom({"prefab": pf})
    if not g0: return None
    orn, _src = mune_ornament(d, m)
    # ⭐ 【部材方の実測 2026-09-14】目録の丈が屋根の頂でない部材(向拝 ── 背面の木部の頂が最も高い)は
    #    `roofTopM`(屋根の最高点)を頂に採る。⛔ 部材への指し先 `partFrom` が解けることは据え置きで要る
    top = float(m["roofTopM"]) if m.get("roofTopM") is not None else g0[1]
    return top - (orn or 0.0)


def part_is_tpl(pt):
    """palette の一点が**大きさを持たない雛形**か(`{size}` を含む)。"""
    return _SIZE_HOLE in (pt.get("prefab") or "") or _SIZE_HOLE in (pt.get("api") or "")


def size_rule(d):
    """`planting.scaleRule.sizeRule` ── 大きさ(変種)を丈から選ぶ規約。無ければ None。"""
    return (d["planting"].get("scaleRule") or {}).get("sizeRule")


def part_variants(d, pt):
    """雛形 `pt` の**目録に在る変種**の列 [(size, prefab, api, 素の丈, 素の樹冠, 三角数)]。

    ⛔ 変種を json に書かない(規則4)── `sizeRule.sizes` の綴りで目録を引くだけ。
    """
    sr = size_rule(d)
    if not sr: return []
    out = []
    for sz in sr.get("sizes", []):
        pf = (pt.get("prefab") or "").replace(_SIZE_HOLE, sz)
        g0 = part_geom({"prefab": pf})
        if g0 is None: continue
        out.append((sz, pf, (pt.get("api") or "").replace(_SIZE_HOLE, sz), g0[1], g0[0], g0[2]))
    return out


def species_h_cap(d, pt):
    """**樹種ごとの丈の上端**[m] = その樹種の**最大変種の素の丈** × `sizeRule.scaleYMax`。

    ⭐ 2026-09-08 庭方12巡目 裁定1 ── 帯は層(落葉高木)に**一つの**丈の範囲を宣言するが、
    部材の素の丈は樹種で違う。**帯の上端が悪いのではなく、帯が三樹種に同じ天井を当てているのが
    悪い** — 実際の樹高もケヤキ ＞ ムクノキで、**部材はそれを正しく写している**。
    ⇒ 各樹種の丈をここで頭打ちにする。⛔ `rakuyoH` そのものを下げない(下げるとケヤキ・エノキまで
    連れて下がり、社叢から最も高い抜け木が消える)。
    ⛔ **規約 `sizeRule.speciesHCap` の宣言が無ければ効かせない** — 宣言の無い頭打ちは
    「黙って丈を縮める道」であって、それこそ規則19 が禁じる形。無ければ None。
    """
    sr = size_rule(d) or {}
    if not sr.get("speciesHCap"): return None
    cap = sr.get("scaleYMax")
    vs = part_variants(d, pt)
    if cap is None or not vs: return None
    return max(q[3] for q in vs) * cap


def pick_variant(d, pt, h):
    """**`sizeRule` — 丈 h[m] に対して選ぶ変種**。(size, prefab, api, scaleY) か None。

    ⭐ 2026-09-07 庭方8巡目 裁定1 ── 「`scaleY` ≤ `scaleYMax` を満たす変種のうち
    |ln(scaleY)| が最小。満たす変種が無ければ**最も大きい変種**」。
    ⛔ 雛形でない(大きさを名指しした)部材はそのまま返す。
    """
    if not part_is_tpl(pt):
        g0 = part_geom(pt)
        return (None, pt.get("prefab"), pt.get("api"),
                (h / g0[1]) if (g0 and h and g0[1]) else None)
    vs = part_variants(d, pt)
    if not vs or not h: return None
    cap = (size_rule(d) or {}).get("scaleYMax")
    cand = [(sz, pf, api, h / hh) for sz, pf, api, hh, _cr, _t in vs if hh]
    ok = [q for q in cand if cap is None or q[3] <= cap + 1e-12]
    if ok: return min(ok, key=lambda q: abs(math.log(q[3])))
    big = max(vs, key=lambda q: q[3])
    return (big[0], big[1], big[2], h / big[3])


def derive_cluster_groups(d):
    """**`groups` を持つ塊を、弧長の割り付けから兄弟の塊へ展開する**
    【中6 庭方 2026-09-09 十七巡目】。

    ⭐ **一列を三塊に割る。**⛔ 位置の数を json に持たない ── 塊の中の芯々
      (`groupSpacingKen` の中央)から各塊の弧長を出し、残りを塊と塊で等分する。
    ⛔ 展開した兄弟は親の宣言(`alongTakagiEdgeLine` / `widthKen` / `layers` / `hFrom` /
      `variantRule` / `overhangFrom` / `edaShitaOverRoadM`)をそのまま引き継ぐ。
    〔記録〕割り付けた離れは `_gapKen` に載せ、検査『塊が塊として組めるか』が刷る。
    """
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    for gd in d["gardens"] + d["slopeBands"]:
        cs = gd.get("clusters")
        if not cs: continue
        out = []
        for c in cs:
            gp = c.get("groups")
            if not gp or not c.get("vRange"):
                out.append(c); continue
            v0, v1 = c["vRange"]
            V = float(v1 - v0)
            # 弧長 → v の換算(線の向きから・⛔ 数を持たない)
            kv = 1.0
            if tl.get("fromEdge") and tl.get("insetKen") is not None:
                A, B = edge_offset(d, tl["fromEdge"], tl["insetKen"])
                L9 = math.hypot(B[0] - A[0], B[1] - A[1]) or 1.0
                kv = abs(B[1] - A[1]) / L9
            sp = c.get("groupSpacingKen") or [0.0, 0.0]
            # ⭐ **上端で置く**【A-7 庭方 2026-09-09 十九巡目 ── ⛔ 十七巡目の『幅は上端・
            #   芯々は下端 × `packRatio`』は撤回された】。線に沿う塊は**弧長を芯々で刻んで
            #   据える**ので、塊の弧長も据える刻みも `groupSpacingKen` の**上端**そのもの。
            #   ⛔ 詰めない ── 詰めると宣言の下限を割り、しかも誰も鳴らさない。
            s9, sx9 = sp[1], sp[1]
            ext = [(len(cluster_mix(q)) and float(sum(k for _k, k in cluster_mix(q))) - 1.0
                    or 0.0) * sx9 * kv for q in gp]
            gap = ((V - sum(ext)) / (len(gp) - 1)) if len(gp) > 1 else 0.0
            at = v0
            for i, q in enumerate(gp):
                ch = collections.OrderedDict()
                ch["name"] = "%s %s" % (c["name"], q.get("name") or (i + 1))
                for k9 in ("alongTakagiEdgeLine", "shape", "layers", "widthKen", "hFrom",
                           "variantRule", "overhangFrom", "role", "edaShitaOverRoadM"):
                    if c.get(k9) is not None: ch[k9] = c[k9]
                ch["mix"] = q["mix"]
                ch["spacing"] = s9
                ch["vRange"] = [round(at, 4), round(at + ext[i], 4)]
                ch["_"] = ("**親の塊『%s』の `groups` からの展開**(⛔ 位置も芯々も数で持たない)。"
                           "⚠ 兄弟との離れは残りの等分で、下限は親の `groupGapKen`。" % c["name"])
                ch["_ofGroup"] = c["name"]
                ch["_gapKen"] = round(gap / (kv or 1.0), 4)
                ch["_gapMinKen"] = c.get("groupGapKen")
                # ⭐ **親の芯々の宣言を子へ運ぶ**【A-7 庭方 2026-09-09 十九巡目】── ⛔ 親は
                #   この展開で `clusters` から消えるので、⛔ 運ばないと**焼き出しの芯々を
                #   宣言と突き合わせる検査が黙る**(規則19)。
                ch["_spacingRangeKen"] = list(sp)
                out.append(ch)
                at += ext[i] + gap
        gd["clusters"] = out


def derive_clusters(d):
    """`boxFrom` を持つ塊の**箱を宣言から起こす**(⛔ 箱の数を json に持たない・規則4)。

    ⭐ 2026-09-07 八巡目 中3 ── 辻の留めの箱は「東縁=高木の縁の線・西へ `widthKen`・
    v は `vRange`」の従属値。箱は軸に平行なので、**東縁は v の範囲で線がいちばん西へ来る
    値に取る**(こうすれば林縁の帯へ一切食い込まない)。
    """
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            bf = c.get("boxFrom")
            if not bf or c.get("box"): continue
            if bf.get("eastEdge") != "sando.roadside.takagiEdgeLine": continue
            if not tl.get("fromEdge") or tl.get("insetKen") is None: continue
            A, B = edge_offset(d, tl["fromEdge"], tl["insetKen"])
            v0, v1 = bf["vRange"]
            if abs(B[1] - A[1]) < 1e-9: continue
            uu = [A[0] + (v - A[1]) * (B[0] - A[0]) / (B[1] - A[1]) for v in (v0, v1)]
            u1 = min(uu)
            c["box"] = [u1 - bf["widthKen"], v0, u1, v1]
    # ⭐ **線に沿う平行四辺形**(2026-09-08 十六巡目 C-1・庭方)── 東縁 = `takagiEdgeLine` の
    #    `vRange` の区間そのもの、西縁 = 法線方向へ `widthKen` 寄せた線。
    #    ⛔ 四隅の座標を json に持たない。⛔ 内向きは決め打ちしない — **同じ `edge_offset` を
    #    1 間ぶん深く引いた差**を内向きに採る(社地の内外の判定と食い違う道を作らない)。
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            if not c.get("alongTakagiEdgeLine") or c.get("poly"): continue
            if not tl.get("fromEdge") or tl.get("insetKen") is None: continue
            if not c.get("vRange") or c.get("widthKen") is None: continue
            A, B = edge_offset(d, tl["fromEdge"], tl["insetKen"])
            A2, _B2 = edge_offset(d, tl["fromEdge"], tl["insetKen"] + 1.0)
            if abs(B[1] - A[1]) < 1e-9: continue
            v0, v1 = c["vRange"]
            at = lambda v: (A[0] + (v - A[1]) * (B[0] - A[0]) / (B[1] - A[1]), v)
            a0, a1 = at(v0), at(v1)
            nx, nz = A2[0] - A[0], A2[1] - A[1]          # 1 間ぶんの**内向き**
            w = c["widthKen"]
            c["poly"] = [[a0[0], a0[1]], [a1[0], a1[1]],
                         [a1[0] + nx * w, a1[1] + nz * w], [a0[0] + nx * w, a0[1] + nz * w]]
            c["_lineLenKen"] = math.hypot(a1[0] - a0[0], a1[1] - a0[1])


def derive_view_clusters(d, g):
    """**視線が決める塊の丈を、箱が跨ぐ帯から起こす**(`hFrom`)。⛔ 数を json に持たない。

    ⭐ 2026-09-08 ── `planting.viewClusters` は本数と箱と役だけを持ち、**丈も層も無かった**ので、
    部材も樹冠も `scaleY` も一行も刷られていなかった(⛔ 0 件は合格ではなく未測定・規則19)。
    ⭐ **丈は箱が跨ぐ帯の `matsuH` の共通部分**【庭方 2026-09-07 十巡目】── 額縁は
    **自分が立っている林を超えない**ので、跨ぐ帯のどちらでも成り立つ丈=共通部分を採る。
    ⛔ 幅が狭いのは額縁として正しい(稜線を作るのは主景の側)。
    """
    cells, _sk = band_scan(d, g)
    for c in d["planting"].get("viewClusters", []):
        if not c.get("hFrom"): continue
        bx = cluster_boxes(c)
        bs = set()
        for k, ps in cells.items():
            for u, v in ps:
                if any(u0 <= u <= u1 and v0 <= v <= v1 for u0, v0, u1, v1 in bx):
                    bs.add(k); break
        hs = [b.get("matsuH") for b in d["slopeBands"] if b["band"] in bs and b.get("matsuH")]
        c["_bands"] = sorted(bs)
        if hs:
            c["matsuH"] = [max(q[0] for q in hs), min(q[1] for q in hs)]


def view_holders(d):
    """`viewClusters` を **塊を持つ holder** の形で返す(⛔ 名簿を別に持たない)。

    ⚠ `cluster_parts` は holder の `zone_h()` から丈を引くので、丈が holder まで届く道が要る。
    """
    out = []
    for c in d["planting"].get("viewClusters", []):
        h = {"name": "視線の塊", "clusters": [c]}
        if c.get("matsuH"): h["matsuH"] = c["matsuH"]
        if c.get("rakuyoH"): h["rakuyoH"] = c["rakuyoH"]
        out.append(h)
    return out


def _h_pair(h):
    """丈の宣言(数 or [lo,hi])を (lo, hi) へ。宣言が無ければ (None, None)。"""
    if isinstance(h, (list, tuple)):
        return (float(h[0]), float(h[1])) if len(h) >= 2 else (None, None)
    return (float(h), float(h)) if h else (None, None)


def pick_variants_over(d, pt, h, n=201):
    """丈が**範囲**のとき、その範囲に現れる変種と `scaleY` の幅。

    ⚠ **変種は一本ずつ選ぶ** — 帯の丈は範囲なので、同じ樹種でも丈で変種が変わる。
    戻り ([(size, prefab, api)], scaleY 最小, scaleY 最大)。
    """
    lo, hi = _h_pair(h)
    if lo is None: return ([], None, None)
    # ⭐ **樹種ごとの頭打ち**(`sizeRule.speciesHCap`・裁定1 庭方 2026-09-08)。⛔ ここだけに置く —
    #    一本立ちの `h` は意匠が名指しした丈なので縮めない(縮めたら宣言を黙って書き換えたことになる)。
    cp = species_h_cap(d, pt)
    if cp is not None and hi > cp: hi = max(lo, cp)
    seen, ylo, yhi = [], None, None
    for i in range(n if hi > lo else 1):
        hh = lo + (hi - lo) * i / float(max(1, n - 1))
        q = pick_variant(d, pt, hh)
        if q is None: continue
        if (q[0], q[1], q[2]) not in seen: seen.append((q[0], q[1], q[2]))
        y = q[3]
        if y is None: continue
        ylo = y if ylo is None else min(ylo, y)
        yhi = y if yhi is None else max(yhi, y)
    return (seen, ylo, yhi)


def layer_xz(d, kind, iso=False):
    """層 `kind` の `scaleXZ`(範囲)。⛔ 数をここに書かない — `scaleRule` が正典。

    ⭐ **2026-09-08 十六巡目 中6(庭方)** ── 落葉・中木は `crownPerH`(樹冠÷丈)から
    **部材 × `scaleXZ`** へ移した。⛔ 同じ量に二つの宣言を置かない(規則4)。
    ⭕ `iso=True`(一本立ち・`isolatedCrown` の塊)は `scaleRule.isolatedXZ` を当てる ──
    孤立木は**野に一本で育った開いた形が正しい**。⛔ 松はこの規約の外(範囲は部材寄り)。
    """
    rule = d["planting"]["scaleRule"].get(kind) or {}
    if iso and kind != "matsu":
        v = d["planting"]["scaleRule"].get("isolatedXZ")
        if v is not None: return [float(v), float(v)]
    return rule.get("scaleXZ") or [1.0, 1.0]


def crown_of(d, kind, prefab, h, iso=False):
    """据えたあとの樹冠径[m]。目録に無ければ None(=**測れていない**。合格ではない)。

    ⭐ **2026-09-08 十六巡目 中6(庭方)** ── **樹冠 = 部材の素の樹冠 × `scaleXZ`** の一本に
    揃えた(松がもともとこの形)。⛔ 旧 `crownPerH`(樹冠÷丈)は落とした ── 同じ量に二つの
    宣言を置かない(規則4)。⚠ 引数 `h` は `sizeRule` が選んだ変種を通じてのみ効く。
    ⚠ 旧宣言が残っていれば**そちらを優先して**返す(⛔ 黙って二重にしない — 検査が止める)。
    """
    rule = d["planting"]["scaleRule"].get(kind) or {}
    cph = rule.get("crownPerH")
    if cph is not None:
        lo, hi = _h_pair(h)
        if lo is None: return None
        return (cph * lo, cph * hi)
    g0 = part_geom({"prefab": prefab})
    if g0 is None: return None
    xz = layer_xz(d, kind, iso)
    return (g0[0] * xz[0], g0[0] * xz[1])


def crown_scale_xz(d, kind, prefab, h, iso=False):
    """その木に掛かる **`scaleXZ`(範囲の中央)**。⛔ json に個体の数を置かない(規則4)。

    実装(棟梁)が使うのはこの倍率。⭐ 2026-09-08 以後は `scaleRule[kind].scaleXZ`
    (孤立木は `isolatedXZ`)そのもので、⛔ 部材の素の樹冠からの逆算ではない。
    """
    if part_geom({"prefab": prefab}) is None: return None
    xz = layer_xz(d, kind, iso)
    return (xz[0] + xz[1]) / 2.0


# ---------------------------------------------------------------- 退避(木を植えない所)
def _pt_seg(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz)


def _seg_cross(a, b, c, e):
    """線分 a→b と c→e の交点(**パラメタ付き**)。交わらなければ None。戻り (点, t, u)。

    ⚠ `_seg_x` とは別物 — あちらは点だけを返す(交差の有無を見る用)。こちらは交点が
    それぞれの折れ線の**端か途中か**を判じるために t / u が要る(検図11巡目 中1)。
    """
    d1 = (b[0] - a[0], b[1] - a[1]); d2 = (e[0] - c[0], e[1] - c[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12: return None
    t = ((c[0] - a[0]) * d2[1] - (c[1] - a[1]) * d2[0]) / den
    u = ((c[0] - a[0]) * d1[1] - (c[1] - a[1]) * d1[0]) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return ((a[0] + d1[0] * t, a[1] + d1[1] * t), t, u)
    return None


def _seg_seg_dist(a, b, c, e):
    """線分どうしの最小距離[間]。交われば 0。"""
    if _seg_cross(a, b, c, e): return 0.0
    return min(_pt_seg(a, c, e), _pt_seg(b, c, e), _pt_seg(c, a, b), _pt_seg(e, a, b))


def _shape_rect(u0, v0, u1, v1, nm):
    return ("rect", min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1), nm,
            (min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1)))


def _shape_seg(a, b, r, nm):
    return ("seg", (a[0], a[1]), (b[0], b[1]), r, nm,
            (min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r))


def _shape_band(a, b, r, nm):
    """**線分の区間だけ**の帯(端に半円のキャップを付けない)。

    ⭐ 2026-09-06c 裁定3(庭方)— 石段の退避はこれで当てる。退避の趣旨は「坂の**両側**を空ける」
    (=法線方向)であって、坂の端から先へ張り出すことではない。キャップを付けると男坂の上端が
    楼門を・下端が仁王門を呑む(構造物を2つ食う退避は形が誤っている徴候)。
    ⛔ 面の総当たり(`_ovl_shapes` の石段)も端に丸みを付けない矩形なので、**形はこれで揃う**。
    """
    return ("band", (a[0], a[1]), (b[0], b[1]), r, nm,
            (min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r))


def _shape_disc(c, r, nm):
    """点まわりの円。**折れ線の内側の節の丸み**にだけ使う(⛔ 端には付けない)。"""
    return ("disc", (c[0], c[1]), r, nm, (c[0] - r, c[1] - r, c[0] + r, c[1] + r))


def _band_chain(pts, r, nm):
    """折れ線に沿う帯 ── **内側の節にだけ丸みを付ける**。⛔ 端の二つには付けない。

    ⭐ **2026-09-08 十六巡目 A-5(庭方)**。`_shape_band` は `0≤t≤1` の区間でしか当たらないので、
    折れ線が折れる**節の外側に楔形の穴**が開き、女坂の頭の喉で 幹が敷きの半幅の内側(芯から横
    2.07 m)に立っていた。⛔ 節の丸みを落としたまま「端にキャップを付けない」で済ませない。
    ⚠ **端の二つはこれまで通りキャップ無し**(2026-09-06c 裁定3・庭方)── あれは
    「坂の**両側**を空ける」趣旨で、**坂の端から先へ張り出さない**ための決めであり、
    折れ線の**内側の節**までは及ばない(男坂の上端が楼門を・下端が仁王門を呑む話である)。
    """
    out = [_shape_band(pts[i], pts[i + 1], r, nm) for i in range(len(pts) - 1)]
    out += [_shape_disc(pts[i], r, nm) for i in range(1, len(pts) - 1)]
    return out


def _shape_poly(P, m, nm):
    """多角形 + 余白 m。**設計された塊の箱を走査面から落とす**のに使う(2026-09-08 A-3)。"""
    us = [q[0] for q in P]; vs = [q[1] for q in P]
    return ("poly", [(q[0], q[1]) for q in P], m, nm,
            (min(us) - m, min(vs) - m, max(us) + m, max(vs) + m))


def _pt_line_t(p, a, b):
    """点から**直線**への距離と、線分上の助変数 t(クランプしない)。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    if L2 < 1e-12: return math.hypot(p[0] - a[0], p[1] - a[1]), 0.0
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz), t


def band_shoulder(d, lay=None):
    """帯1〜3 の石段の**肩**[間]。層ごとの宣言 `bandDef.avoid.kaidanShoulderKen` を引く。

    ⭐ **2026-09-08 に層ごとへ刻んだ**【裁き1 庭方】── 低木 0.5 ／ 中木 1.0 ／ 高木 1.5 間。
    旧式は一本の指し先(腰石垣からの離れ)を全層へ当てており、石段の両側に**下草だけの縁**を
    残す一方で**高木の根株は擁壁の上まで寄れた**。⛔ 数をここに書かない(json が正典)。
    `lay=None` は**最も大きい肩**(=高木)を返す — 層を渡し忘れた側が甘い面を得ないため。
    """
    sh = ((d["planting"].get("bandDef") or {}).get("avoid") or {}).get("kaidanShoulderKen") or {}
    if not sh: return None
    return sh.get(lay) if lay else max(sh.values())


def kattemichi_shoulder(d, lay=None):
    """**勝手道の肩**[間]。⛔ 石段の `kaidanShoulderKen` を借りない
    【高1 庭方 2026-09-09 十七巡目 → `bandDef.avoid.kattemichiShoulderKen`】。

    ⚠ 肩の根拠は『**幹の根が擁壁を押さない**』で、⭕ **勝手道は土の小径・擁壁が無い**。
      石段の肩(高木 1.5 間)を借りていたので、九十九折で隣の脚の退避が融合して**島が消え**、
      南面に幅 10〜17 m の裸の斜め筋(1,043 m²・最大内接半径 8.7 m)が残った。
    ⛔ 宣言が無ければ**石段の肩へ落ちない** ── None を返し、検査が⛔で止める(規則19)。
    """
    sh = ((d["planting"].get("bandDef") or {}).get("avoid") or {}).get("kattemichiShoulderKen")
    if not sh: return None
    return sh.get(lay) if lay else max(sh.values())


def kyoukai_shoulder(d, lay=None):
    """**社地の境からの幹の離れ**[間]【中5 庭方 2026-09-09 十七巡目 → `avoid.kyoukaiKen`】。

    ⛔ 林縁(`rinen`)とは別物 ── 林縁は『道に接する辺だけ』の意匠で、こちらは**全周**に効く。
    ⚠ 宣言が無かったので幹が境界線に乗っていた(実測 最短 松 0.09 m ／ 中木 0.03 ／ 低木 0.00 m)。
    """
    sh = ((d["planting"].get("bandDef") or {}).get("avoid") or {}).get("kyoukaiKen")
    if not sh: return None
    return sh.get(lay) if lay else max(sh.values())


def kyoukai_avoid_shapes(d, g, sh_ken):
    """**社地の境 `polygon` の内側 `sh_ken`[間] の帯**(幹を退ける面)。⛔ 数を持たない。

    ⭕ **樹冠は境の外へ張り出してよい** ── 退けるのは幹だけ(`plantRule.crownRule` と同じ物差し)。
    """
    if not sh_ken: return []
    P = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    out = []
    for i in range(len(P)):
        out.append(_shape_band(P[i], P[(i + 1) % len(P)], sh_ken, "社地の境:辺%d" % i))
    return out


def avoid_shapes(d, g, scope):
    """退避の形 + **木を植えない面**(`gardens[].noTrees`・庭方 2026-09-15)── どの撒く面にも当てる。"""
    out = _avoid_shapes_base(d, g, scope)
    for gd in d["gardens"]:
        if gd.get("noTrees") and garden_poly(gd):
            out.append(_shape_poly(garden_poly(gd), 0.0, "植えない面:" + gd["name"]))
    return out


def _avoid_shapes_base(d, g, scope):
    """**退避の宣言から障害物の buffer を組み立てる。**⛔ ここに数を書かない — 宣言が正典。

    scope="keidai" … 境内の立木3区に効く(`planting.clearance.keidai`)
    scope="zentei" … 前庭の面(帯・供待・点景)に効く(`planting.clearance.zentei`)
    scope="obi4"   … 社叢 帯4 に効く(**多角形を持つ帯**の `avoid`)
    scope="obi123:<層>" … 社叢 帯1〜3 に効く(`planting.bandDef.avoid` ── 三本で共通の規約なので
                     ⛔ 帯ごとに写さない。帯の側は `avoidFrom` で指し先だけを持つ)。
                     ⭐ **肩は層ごと**なので面も層ごとに違う(2026-09-08 裁き1)

    ⚠ **2026-09-06 に zentei を実装した。**宣言はあったのに表へ刷るだけで、
    どの面にも効いていなかった(結線の欠落・規則19)。
    """
    ken = d["const"]["ken"]
    out = []
    if scope == "keidai":
        ck = d["planting"]["clearance"]["keidai"]
        p = ck["do"]
        for m in d["munes"]:
            if m["yaku"] == "接続": continue
            out.append(_shape_rect(m["u0"] - p, m["v0"] - p,
                                   m["u0"] + m["du"] + p, m["v0"] + m["dv"] + p, "棟:" + m["name"]))
        p = ck["sukibeiKairo"]
        for r in d["runs"]:
            if r["kind"] not in ("透塀", "回廊", "袖塀"): continue
            out.append(_shape_seg(r["a"], r["b"], p + r.get("bari", 0) / 2.0,
                                  r["kind"] + ":" + r["name"]))
        for gd in d["gardens"]:
            if gd["name"] == "白洲" and gd.get("poly"):
                # ⭐ 【庭方の設計 2026-09-14 D2】白洲は多角形。北の退がりは**北縁の頂点**を北へ出して当てる
                P9 = [(q[0], q[1]) for q in gd["poly"]]
                vmax = max(q[1] for q in P9)
                vn = ck["shirasuNorthFromV"] + ck["shirasuNorthKen"]
                out.append(_shape_poly([(q[0], vn if abs(q[1] - vmax) < 1e-6 else q[1]) for q in P9], 0.0,
                                       "白洲(+北の退がり)"))
            elif gd["name"] == "白洲":
                out.append(_shape_rect(gd["u0"], gd["v0"], gd["u1"],
                                       ck["shirasuNorthFromV"] + ck["shirasuNorthKen"], "白洲(+北の退がり)"))
            elif gd["name"] == "中庭":
                out.append(_shape_poly(garden_poly(gd), 0.0, "中庭"))
        for rt in d.get("routes", []):
            rr = rt["w"] / 2.0 / ken + ck["routeHalfPlus"]
            pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
            for i in range(len(pts) - 1):
                out.append(_shape_seg(pts[i], pts[i + 1], rr, "動線:" + rt["name"]))
        for k in d["kaidans"]:
            rr = kaidan_wken(d, k) / 2.0 + ck["kaidanHalfPlus"]
            pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
            out += _band_chain(pts, rr, "石段:" + k["name"])   # ⭐ 内側の節に丸み(A-5)
        return out
    if scope == "zentei":
        cz = d["planting"]["clearance"]["zentei"]
        for rt in d.get("routes", []):
            # ⭐ 前庭の中は路面幅を読み替える(`wByTerrace`・庭方 2026-09-06b)
            rr = route_w(d, rt, "Zentei") / 2.0 / ken + cz["routeHalfPlus"]
            pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
            for i in range(len(pts) - 1):
                out.append(_shape_seg(pts[i], pts[i + 1], rr, "動線:" + rt["name"]))
        for k in d["kaidans"]:
            # ⭐ **端にキャップを付けない**(2026-09-06c 裁定3・庭方)— 坂の側方だけを空ける
            rr = kaidan_wken(d, k) / 2.0 + cz["kaidanHalfPlus"]
            pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
            out += _band_chain(pts, rr, "石段:" + k["name"])   # ⭐ 内側の節に丸み(A-5)
        p = cz["gate"]
        for gt in d["gates"]:
            hu, hv = gate_half_uv(gt)
            out.append(_shape_rect(gt["u"] - hu - p, gt["v"] - hv - p,
                                   gt["u"] + hu + p, gt["v"] + hv + p, "門:" + gt["name"]))
        zp = terrace_poly_uv(d["terraces"][1])
        # ⭐ **西の辺だけ犬走りで受ける**(2026-09-06c 裁定2・庭方)— 帯の西縁を腰石垣 `TW_Zentei_W`
        #    の天端まで出したので、`terraceEdge`(縁の退避)ではなく `inuBashiriM` が当たる。
        #    西の辺 = **u が最小の南北の辺**として同定する(⛔ 辺の番号を json に書かない)
        uw = min(q[0] for q in zp)
        inu = cz.get("inuBashiriM")
        for i in range(len(zp)):
            a, b = zp[i], zp[(i + 1) % len(zp)]
            west = abs(a[0] - uw) < 1e-9 and abs(b[0] - uw) < 1e-9
            r = (inu / ken) if (west and inu is not None) else cz["terraceEdge"]
            out.append(_shape_seg(a, b, r, "前庭の縁" + ("(西=犬走り)" if west and inu is not None else "")))
        # ⭐ **2026-09-06 検図5巡目 中5 で足した実体** — 井戸屋形の石敷・玉垣・縁台・空地(供待)が
        #    一つも入っておらず、前庭の合法域が実際より広く出ていた。
        #    ⛔ 退避の余白は宣言が無いので**実体の輪郭そのもの**(余白 0)で当てる。
        _ir = ido_rects(d)
        if _ir:
            out.append(_shape_rect(*(list(_ir["石敷"]) + ["井戸:石敷"])))
        for gd in d["gardens"]:
            own = gd.get("tamagaki")
            for nm, a, b, fence, _ln, rs in tamagaki_edges(d, gd):
                if not fence: continue
                for rn in rs:
                    out.append(_shape_seg(rn[0], rn[1], own["postDiaM"] / 2.0 / ken, "玉垣:" + nm))
            if gd.get("noPlant") and gd.get("poly"):
                us = [q[0] for q in gd["poly"]]; vs = [q[1] for q in gd["poly"]]
                out.append(_shape_rect(min(us), min(vs), max(us), max(vs), "空地:" + gd["name"].split("(")[0]))
        for nm, Q in prop_rects(d):
            us = [q[0] for q in Q]; vs = [q[1] for q in Q]
            out.append(_shape_rect(min(us), min(vs), max(us), max(vs), "点景:" + nm))
        return out
    if scope.startswith("obi123"):
        # ⭐ **帯1〜3 の石段の退避**(2026-09-08)。⛔ 数を持たない ──
        #    芯からの半径 = 石段の敷きの半幅(`kaidans[].wKen`/2)+ **その層の肩**。
        # ⭐ **肩は層ごと**【裁き1 庭方 2026-09-08】── `scope` は "obi123:<層>"。
        #    ⛔ 層を省いた呼び方は**最も大きい肩**(=高木)で代表する — 層を渡し忘れた側が
        #    黙って甘い面を得る道を作らない。
        sh = band_shoulder(d, scope.partition(":")[2] or None)
        if sh is None: return []
        for k in d["kaidans"]:
            rr = kaidan_wken(d, k) / 2.0 + sh
            pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
            out += _band_chain(pts, rr, "石段:" + k["name"])   # ⭐ 内側の節に丸み(A-5)
        # ⭐ **勝手道・囲い・土留め・塊の箱**(2026-09-08 十六巡目 A-1/A-3/B-4・庭方)
        #    ⛔ 数はどれも宣言からの従属値(`kattemichiRule` / `kakoiRule` / `clusterRule`)
        av123 = d["planting"]["bandDef"]["avoid"]
        lay9 = scope.partition(":")[2] or None
        # ⭐ **勝手道の肩は石段とは別の宣言**【高1 庭方 2026-09-09 十七巡目】
        if av123.get("kattemichiRule"):
            out += kattemichi_apron_shapes(d, g, kattemichi_shoulder(d, lay9) or 0.0)
        if av123.get("kakoiRule"): out += kakoi_avoid_shapes(d, sh)
        # ⭐ **社地の境からの幹の離れ**(全周)【中5 庭方 2026-09-09 十七巡目】
        if av123.get("kyoukaiRule"):
            out += kyoukai_avoid_shapes(d, g, kyoukai_shoulder(d, lay9))
        # ⛔ **塊の箱はここへ入れない** — 塊の本数は既に帯から差し引いてあるので、面まで引くと
        #    二重に引くことになる(⛔ 本数の配り方は変えない・庭方 A-3)。落とすのは
        #    **撒くときの候補セル**だけで、それは `scatter_pts` が `cluster_keepout_shapes` で行う。
        return out
    # ⚠ **多角形を持つ帯**(帯4)の宣言を採る ── ⛔ 「最初に `avoid` を持つ帯」で拾わない
    #    (帯1〜3 が指し先を持った日に、帯4 の額縁が黙って入れ替わる)
    av = [b["avoid"] for b in d["slopeBands"] if b.get("avoid") and b.get("uv")][0]
    ot = [k for k in d["kaidans"] if k["name"] == "男坂"][0]
    out.append(_shape_seg(ot["a"], ot["b"], av["otokozakaFromAxis"], "男坂"))
    on = [k for k in d["kaidans"] if k["name"].startswith("女坂")][0]
    rr = kaidan_wken(d, on) / 2.0 + av["onnazakaFromShoulder"]
    op = [tuple(q) for q in on["pts"]]
    for i in range(len(op) - 1):
        out.append(_shape_seg(op[i], op[i + 1], rr, "女坂"))
    sp = [(g.U(x), g.V(z)) for x, z in d["sando"]["pts"]]
    for i in range(len(sp) - 1):
        out.append(_shape_seg(sp[i], sp[i + 1], av["sandoFromAxis"], "参道"))
    zp = terrace_poly_uv(d["terraces"][1])
    # ⭐ **東の辺だけ退避を緩める**(庭方 中-2 2026-09-06b)。東の辺 = **u が最大の南北の辺**として
    #    同定する(⛔ 辺の番号を json に書かない — 前庭の輪郭を直した日に取り残される)
    ue = max(q[0] for q in zp)
    for i in range(len(zp)):
        a, b = zp[i], zp[(i + 1) % len(zp)]
        east = abs(a[0] - ue) < 1e-9 and abs(b[0] - ue) < 1e-9
        r = av.get("zenteiFromEdgeEast", av["zenteiFromEdge"]) if east else av["zenteiFromEdge"]
        out.append(_shape_seg(a, b, r, "前庭の縁" + ("(東)" if east else "")))
    # ⭐ **柵と塊の箱**(2026-09-08 十六巡目 B-4/A-3)。⛔ **前庭の縁の土留め・板塀は外す** ──
    #    帯4 は上の `zenteiFromEdge`/`zenteiFromEdgeEast` で同じ縁を測っている(⛔ 二重に効かせない)
    av4 = d["planting"]["bandDef"]["avoid"]
    sh4 = band_shoulder(d, "松")
    if av4.get("kakoiRule") and sh4 is not None:
        out += kakoi_avoid_shapes(d, sh4, skip_zentei=True)
    # ⭐ **社地の境からの幹の離れ**(全周)【中5 庭方 2026-09-09 十七巡目】。⚠ 帯4 は層で
    #    分けない額縁の宣言だが、境の離れは**層ごと**なので最も大きい肩(高木)で代表させる
    #    ── ⛔ 甘い側へ倒さない。
    if av4.get("kyoukaiRule"):
        out += kyoukai_avoid_shapes(d, g, kyoukai_shoulder(d, "松"))
    # ⛔ 塊の箱はここへ入れない(理由は obi123 と同じ)── `scatter_pts` が候補から落とす
    return out


def shape_hit(p, shapes):
    """点が退避に載っていれば障害物の名、載っていなければ None。"""
    for sh in shapes:
        bb = sh[-1]                                  # ⚠ 末尾が bbox・その前が名(rect と seg で長さが違う)
        if not (bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]): continue
        if sh[0] == "rect":
            if sh[1] < p[0] < sh[3] and sh[2] < p[1] < sh[4]: return sh[-2]
        elif sh[0] == "band":
            # ⭐ 端に半円を付けない — 線分の**区間の中**だけ、法線方向に r
            dd, t = _pt_line_t(p, sh[1], sh[2])
            if 0.0 <= t <= 1.0 and dd < sh[3]: return sh[-2]
        elif sh[0] == "disc":
            # ⭐ **折れ線の内側の節の丸み**(2026-09-08 A-5)
            if math.hypot(p[0] - sh[1][0], p[1] - sh[1][1]) < sh[2]: return sh[-2]
        elif sh[0] == "poly":
            # ⭐ **塊の箱 + 余白**(2026-09-08 A-3)。内か、辺から余白の内か
            Q = sh[1]
            if in_poly(p, Q): return sh[-2]
            if sh[2] > 0.0 and min(_pt_seg(p, Q[i], Q[(i + 1) % len(Q)])
                                   for i in range(len(Q))) < sh[2]: return sh[-2]
        elif _pt_seg(p, sh[1], sh[2]) < sh[3]:
            return sh[-2]
    return None


def kaidan_apron_shapes(d):
    """石段の**敷き**(踏面の帯)。⛔ 端にキャップを付けない(2026-09-06c 裁定3・庭方)。

    ⭐ 2026-09-08 ── 帯1〜3 は石段の敷きを一度も見ておらず、**踏面の上に木が立っていた**。
    敷きの半幅は `kaidans[].wKen` からの従属値で、⛔ 数を別に持たない。
    """
    out = []
    for k in d["kaidans"]:
        hw = kaidan_wken(d, k) / 2.0
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        out += _band_chain(pts, hw, "石段:" + k["name"])       # ⭐ 内側の節に丸み(A-5)
    return out


def kattemichi_apron_shapes(d, g, sh_ken=0.0):
    """**勝手道の敷き(+ 層の肩)**。⛔ 数を持たない — `kattemichi[].w` と肩の宣言からの従属値。

    ⭐ **2026-09-08 十六巡目 A-1(庭方)。**`avoid_shapes(…, "obi123:<層>")` が見ていたのは
    `d["kaidans"]` だけで、**勝手道(西・東、幅 `w`)が退避に一つも入っていなかった** ──
    芯からの最短 0.01 m、松でも 0.38 m で、⛔ **動線図が道として描く九十九折が木で塞がっていた**。
    ⛔ 端にキャップは付けない・**内側の節には丸みを付ける**(`_band_chain`)。
    """
    out = []
    ken = d["const"]["ken"]
    for k in d.get("kattemichi", []):
        pts = [(g.U(x), g.V(z)) for x, z in k["pts"]]
        if len(pts) < 2: continue
        out += _band_chain(pts, k["w"] / 2.0 / ken + sh_ken, "勝手道:" + k["name"])
    return out


def kakoi_avoid_shapes(d, sh_ken, skip_zentei=False):
    """**柵・板塀・土留めの線 + その層の肩**。⛔ 厚みを発明しない(宣言があるのは柵の柱だけ)。

    ⭐ **2026-09-08 十六巡目 B-4(庭方)。**幹が柵・土留めに当たっていた(`Saku_Sando` に8本・
    最短 0.09 m ／ `Ita_Keidai` に22本 ／ `TW_Zentei_E` に5本)── 10〜12 m の松の幹は径
    0.3〜0.4 m あるので ⛔ **柵はそこに建たない**。
    `skip_zentei=True` は**前庭の縁の土留め**を外す ── 帯4 は `avoid.zenteiFromEdge` /
    `zenteiFromEdgeEast` という**別の宣言**(庭方 中-2 の緩め)で同じ縁を測っているので、
    ⛔ 二重に効かせて裁定済みの意匠を黙って上書きしない。
    """
    out = []
    ken = d["const"]["ken"]
    post = 0.0
    for gd in d["gardens"]:
        tg = gd.get("tamagaki")
        if tg and tg.get("postDiaM"): post = max(post, tg["postDiaM"] / 2.0 / ken)
    for r in d["runs"]:
        if r.get("kind") not in ("柵", "板塀"): continue
        if skip_zentei and r["name"].startswith("Ita_Z"): continue
        # ⛔ **生成前の run を測らない** — `Ita_Keidai`/`Saku_SW` は `derive_runs` が形を入れる
        if not r.get("pts") and (r.get("a") is None or r.get("b") is None): continue
        half = post if r.get("kind") == "柵" else 0.0
        for a, b in run_segs(r):
            out.append(_shape_band(a, b, half + sh_ken, r.get("kind") + ":" + r["name"]))
    for w in d.get("terraceWalls", []):
        if skip_zentei and w["name"].startswith("TW_Zentei"): continue
        pts = [tuple(q) for q in (w.get("pts") or [w.get("a"), w.get("b")])]
        if any(q is None for q in pts) or len(pts) < 2: continue
        out += _band_chain(pts, sh_ken, "土留め:" + w["name"])
    return out


def cluster_keepout_shapes(d):
    """**設計された塊の箱 + 芯々 × `packRatio` の余白**。⛔ 帯の走査面から落とすための形。

    ⭐ **2026-09-08 十六巡目 A-3(庭方)。**`view_cluster_cut` は塊のぶんの**本数**を帯から
    引くが、**箱を走査面から落としていなかった** ── 『男坂の見切り』(額縁・設計6本)へ帯から
    24 本が撒き込み、⛔ **『主景は一点』を測る見込み角がもう額縁を測っていなかった**。
    ⛔ 本数の配り方は変えない(引くのは面であって密度ではない)。
    ⚠ **『変えない』が当たるのは総数だけ**【低3 検図21巡目 → 2026-09-09】── 面が縮むと
      層ごとの整数配分(`_apportion`)の丸めが動くので、⛔ **層の割り前は 1〜十数本ずれる**。
      ⭕ 検図の再現でも旧の松の本数は再現しなかった(原因は帯3 林縁の再配分と塊の
      `n` → `nFrom` 化)。⛔ 「層の内訳まで不変」と読ませない。
    """
    pack = d["planting"]["plantRule"]["packRatio"]
    out = []
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            sp = cluster_spacing(d, c)
            m = (sp or 0.0) * pack
            for Q in cluster_polys(c):
                out.append(_shape_poly(Q, m, "塊:" + c["name"]))
    return out


def poly_scan(P, step):
    """多角形の中のセルの中心を走査する(セルは step[間] 角)。"""
    us = [q[0] for q in P]; vs = [q[1] for q in P]
    u = min(us) + step / 2.0
    while u < max(us):
        v = min(vs) + step / 2.0
        while v < max(vs):
            if in_poly((u, v), P): yield (u, v)
            v += step
        u += step


def cell_tsubo(d, step):
    return step * step * d["const"]["ken"] ** 2 / TSUBO


# ---------------------------------------------------------------- 社叢の帯(面と本数)
_BANDS = {}


# 帯に撒く層。⛔ 綴りは `planting.parts` と `bandDef.avoid.layers` の鍵そのもの
_LAYS = ("松", "落葉", "中木", "低木")


def band_scan(d, g):
    """**帯1〜3の面を走査する**(`planting.bandDef` の規約)。⛔ 面積も本数も定数で持たない。

    法肩 = 平場の天端、法尻 = 社地の境(東〜北東は帯4の西縁)。各セルで
    t = (天端 − 現地形h) / (天端 − 最寄りの法尻のh) を出し、帯の `from`/`to` で切る。
    ⭐ **2026-09-08 ── `exclude` が名指しする石段の敷きを落とす。**旧式は男坂・女坂の踏面を
    帯の面に数えており、そこへ密度どおりに木が撒かれていた(⛔ 0 件は合格ではなく未測定)。
    敷きの分は `_BANDS["kai"]` に別に数え、**不変条件①の和に足す**(社地は 平場+前庭+帯+敷き で閉じる)。
    戻り値: ({帯番号: [(u,v)…]}, 未分類のセル数)
    """
    if _BANDS: return _BANDS["cells"], _BANDS["skip"]
    bd = d["planting"]["bandDef"]
    step = bd["stepKen"]
    top = d["terraces"][0]["y"]
    soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    keidai = terrace_poly_uv(d["terraces"][0])
    zentei = terrace_poly_uv(d["terraces"][1])
    obi4 = [(q[0], q[1]) for q in d["slopeBands"][3]["uv"]]

    def ring(P): return [(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    toe = ring(soch) + ring(obi4)
    # ⭐ **石段の敷き**は `bandDef.exclude` の宣言で落とす(⛔ 生成器に焼き込まない)。
    #    宣言を外すと踏面が帯の面へ戻り、検査『植栽の面と退避』が鳴る(規則19)。
    kai_sh = kaidan_apron_shapes(d) if any("石段" in q for q in (bd.get("exclude") or [])) else []
    cells = {1: [], 2: [], 3: []}
    kai_n = [0]
    skip = 0
    for p in poly_scan(soch, step):
        if in_poly(p, keidai) or in_poly(p, zentei) or in_poly(p, obi4): continue
        x, z = g.W(p[0], p[1])
        h = dem_h(x, z)
        if h is None: skip += 1; continue
        best, bq = 1e9, None
        for a, b in toe:
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
            q = (a[0] + dx * t, a[1] + dz * t)
            dd = math.hypot(p[0] - q[0], p[1] - q[1])
            if dd < best: best, bq = dd, q
        ht = dem_h(*g.W(bq[0], bq[1]))
        if ht is None or top - ht <= 0.5: skip += 1; continue
        t = (top - h) / (top - ht)
        for b in d["slopeBands"][:3]:
            if b["from"] <= t < b["to"] or (b["to"] >= 1.0 and t >= b["from"]):
                # ⭐ **敷きのセルは帯の面から落とし、不変条件①の第五の部分に数える。**
                #    ⛔ **『橋として渡す』細工は 2026-09-09 十八巡目に廃した**【決3 庭方】──
                #    帯ごとの連結を測ること自体が誤りだったので、橋も要らなくなった。
                if kai_sh and shape_hit(p, kai_sh):
                    kai_n[0] += 1
                else:
                    cells[b["band"]].append(p)
                break
        else:
            skip += 1
    _BANDS["cells"], _BANDS["skip"] = cells, skip
    _BANDS["kai"] = kai_n[0]           # 不変条件①の第五の部分(石段の敷き)
    return cells, skip


# 「**接する**」の数値の許容[間]。⛔ **設計値ではない** — 丸めの幅(≒18 mm)。
_TOUCH_KEN = 0.01


def rinen_areas(d, g, b):
    """林縁が『接するか』を測る**相手の道敷**(uv の多角形の列)。⛔ 辺の番号を書かない。"""
    src = (b.get("rinen") or {}).get("areasFrom") or []
    out = []
    for s in src:
        if s.startswith("fumotomichi"):
            out += [[(g.U(x), g.V(z)) for x, z in f["area"]]
                    for f in d.get("fumotomichi", []) if f.get("area")]
        elif s.startswith("sando"):
            if d.get("sando", {}).get("area"):
                out.append([(g.U(x), g.V(z)) for x, z in d["sando"]["area"]])
    return out


def rinen_edge_idx(d, g, b):
    """帯の**林縁が距離を測る社地の辺**を**番号つき**で返す [(i, a, b)]。

    ⭐ **同定は『辺の中点と両三分点がすべて道敷から `rinenEdgeTouchKen` 以内』**
    【中4 庭方 2026-09-09 十七巡目 → `bandDef.rinenEdgeRule`】。
    ⚠ **旧式は辺を11点に刻んで一点でも触れれば採っていた**ので、⛔ **頂点で触れるだけの辺**を
      拾った ── 帯3 の林縁が『道に接しない2辺』(東の境 110 m・南西の境 83 m)へ掛かり、
      **幅 2.73 m の高木の空白が 193 m 続いていた**(帯3 自身の註と矛盾)。
    ⛔ 宣言(`rinen.edgeFrom` / `areasFrom`)が無ければ**社地の境の全部**を返す。
    """
    soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    E = [(i, soch[i], soch[(i + 1) % len(soch)]) for i in range(len(soch))]
    ef = (b.get("rinen") or {}).get("edgeFrom")
    if not ef: return E
    areas = rinen_areas(d, g, b)
    tol = (d["planting"]["bandDef"].get("rinenEdgeTouchKen") or _TOUCH_KEN)
    out = []
    for i, a, b_ in E:
        for Q in areas:
            ok = True
            for t in (1.0 / 3.0, 0.5, 2.0 / 3.0):        # ⛔ 端点は見ない(頂点接触を落とす)
                p = (a[0] + (b_[0] - a[0]) * t, a[1] + (b_[1] - a[1]) * t)
                dd = 0.0 if in_poly(p, Q) else min(_pt_seg(p, Q[j], Q[(j + 1) % len(Q)])
                                                   for j in range(len(Q)))
                if dd > tol: ok = False; break
            if ok: out.append((i, a, b_)); break
    return out


def rinen_edges(d, g, b):
    """`rinen_edge_idx` の辺だけ(番号を落とした形)。⛔ 同定の式を二つ持たない。"""
    return [(a, b_) for _i, a, b_ in rinen_edge_idx(d, g, b)]


_RLAY = {"松": "takagi", "落葉": "takagi", "中木": "chuboku", "低木": "teiboku"}


def rinen_tiers(b):
    """林縁の**段**【④ 庭方 2026-09-09 十七巡目】。⛔ 宣言が無ければ一段(`rinen` そのもの)。

    ⚠ **林縁は独立の密度を持つ**(帯の `teibokuPer100` の範囲では二段に割れない — 実測で
      林縁 5.64 本/100 m² 対 帯の本体 4.90 の 15% 増、丈も 2.16 対 2.15 でほぼ同じだった)。
    """
    rin = b.get("rinen") or {}
    if not rin: return []
    ts = rin.get("tiers")
    if not ts: return [{"name": "一段", "fromKen": rin.get("fromKen", 0.0),
                        "toKen": rin["toKen"]}]
    return list(ts)


def _rinen_pick(d, b, t, lay, suffix):
    """段 → 林縁 → 帯 の順に宣言を引く(⛔ 段が持たない量は上位へ落ちる)。"""
    rin = b.get("rinen") or {}
    k = _RLAY[lay] + suffix
    for src in ([t, rin] if t is not rin else [rin]):
        if src.get(k) is not None: return src[k]
        fr = src.get(k + "From")
        if fr and "上端" in fr:
            q = b.get(k)
            return [q[1], q[1]] if isinstance(q, (list, tuple)) else q
        if fr and ("本体" in fr or "帯の" in fr):
            return b.get(k)
    return None


def rinen_dens_t(d, b, t, lay):
    """段 `t` の林縁の密度[本/100 m²]。⛔ 数を作らない。"""
    v = _rinen_pick(d, b, t, lay, "Per100")
    if v is None: return None
    return (v[0] + v[1]) / 2.0 if isinstance(v, (list, tuple)) else float(v)


def rinen_h_t(d, b, t, lay):
    """段 `t` の林縁の丈[lo,hi]。⛔ 新しい丈を作らない。"""
    return _rinen_pick(d, b, t, lay, "H")


def rinen_range_t(b, t, lay):
    """段 `t` にとっての範囲 (内, 外)[間]。⛔ 高木は段に分けない(林縁の全幅で 0 本)。"""
    rin = b.get("rinen") or {}
    if not rin: return None
    if lay in ("松", "落葉"): return (0.0, rin["toKen"])
    return (t["fromKen"], t["toKen"])


def rinen_range(b, lay):
    """層 `lay` にとっての林縁の帯の**全体**の範囲 (内, 外)[間]。⛔ 数を作らない。

    ⭐ **高木は境から `toKen` まで一本も置かない**(⛔ `fromKen` の内側も含む)── `fromKen` は
    **下層を撒き始める線**(内側は柵の帯 `sando.roadside.west.sakuKen`)であって、
    高木の境ではない。⚠ 旧図は高木を 0〜`fromKen` の 0.5 間へ落としており、
    社地の境から 0.09 m に松が立っていた(2026-09-08 十六巡目 A-4・庭方)。
    """
    rin = b.get("rinen") or {}
    if not rin: return None
    ts = rinen_tiers(b)
    if lay in ("松", "落葉") or not ts: return (0.0 if lay in ("松", "落葉")
                                                else rin["fromKen"], rin["toKen"])
    return (min(t["fromKen"] for t in ts), max(t["toKen"] for t in ts))


def band_density(b):
    """採用密度[本/100m²]。`takagiAdopted` があればそれ、無ければ `takagiPer100` の中央。"""
    if b.get("takagiAdopted"): return b["takagiAdopted"]
    r = b.get("takagiPer100") or [0, 0]
    return (r[0] + r[1]) / 2.0


_VCUT = {"fall": []}


def view_cluster_cut(d, g):
    """視線が決める塊(`planting.viewClusters`)の本数を、箱の中心が落ちる帯から差し引く。

    ⭐ **落ちなかった箱は記録する**【低3 検図15巡目 → 2026-09-08】── 旧式は既定で
    「セル数最大の帯」へ**黙って落として**おり、`avoid` や敷きを動かした日に本数が黙って移った。
    ⛔ 黙って移す道を塞ぐ ── 検査『塊が塊として組めるか』が ⛔ で止める。
    """
    cells, _ = band_scan(d, g)
    own = {}
    for k, ps in cells.items():
        for p in ps: own[(round(p[0] * 2), round(p[1] * 2))] = k
    cut = {1: 0, 2: 0, 3: 0}
    _VCUT["fall"], _VCUT["on"] = [], []
    for c in d["planting"].get("viewClusters", []):
        bx = cluster_boxes(c)
        per = cluster_n(c) / max(1, len(bx))
        for j, (u0, v0, u1, v1) in enumerate(bx):
            cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
            k = own.get((round(cu * 2), round(cv * 2)))
            if k is None:
                k = min(cut, key=lambda q: -len(cells[q]))
                _VCUT["fall"].append((c["name"], j + 1, k, per))
            else:
                _VCUT["on"].append((c["name"], j + 1, k, per))
            cut[k] += per
    return cut


_BSTAT = []


def band_stats(d, g):
    """帯1〜4 の 面[坪]・退避[坪]・有効面[坪]・採用密度・高木/落葉/中木/低木の本数。"""
    if _BSTAT: return _BSTAT
    ken = d["const"]["ken"]
    cells, skip = band_scan(d, g)
    ct = cell_tsubo(d, d["planting"]["bandDef"]["stepKen"])
    cut = view_cluster_cut(d, g)
    for b in d["slopeBands"]:
        if b.get("uv"):
            P = [(q[0], q[1]) for q in b["uv"]]
            sh = avoid_shapes(d, g, "obi4")
            st = 0.25
            c2 = cell_tsubo(d, st)
            tot = av = 0
            rin = b.get("rinen") or {}
            E = rinen_edges(d, g, b) if rin else []
            dds = []
            for p in poly_scan(P, st):
                tot += 1
                if shape_hit(p, sh): av += 1; continue
                # ⭐ **林縁は帯の中の小領域**(2026-09-08 十六巡目 A-4)── ⛔ 有効面から落とし、
                #    層ごとに別の密度と丈で撒く。⛔ 高木は林縁へ一本も入れない。
                if rin and E: dds.append(min(_pt_seg(p, q[0], q[1]) for q in E))
            # ⭐ 帯の中に**位置を決めて据える一本立ち**があれば、密度から出した本数から差し引く
            #    (視線が決める塊と同じ扱い。2026-09-06 庭方 A-3b の門被りの松)
            row = {"b": b, "tsubo": tot * c2, "avoid": av * c2,
                   "cut": float(len(b.get("singles", []))),
                   "usableBy": {}, "avoidBy": {}, "rinenBy": {}}
            # ⚠ 帯4 の退避は**額縁**(見え掛かり)の宣言なので層で分けない ── ⛔ 帯1〜3 の
            #    層ごとの肩をここへ写さない(測っている物が違う)。
            #    ⭐ **林縁の範囲だけは層で違う**(高木は境から `toKen` まで全部・A-4)
            row["rinenTier"] = {}
            for k in _LAYS:
                rg = rinen_range(b, k)
                rn = sum(1 for q in dds if rg[0] <= q <= rg[1]) if rg else 0
                row["avoidBy"][k] = av * c2
                row["rinenBy"][k] = rn * c2
                row["usableBy"][k] = (tot - av - rn) * c2
                # ⭐ **段ごとの面**(④ 庭方 2026-09-09)── ⛔ 合算だけを持たない
                for ti, t in enumerate(rinen_tiers(b)):
                    rgt = rinen_range_t(b, t, k)
                    row["rinenTier"][(ti, k)] = (
                        sum(1 for q in dds if rgt[0] <= q <= rgt[1]) * c2) if rgt else 0.0
            row["usable"], row["rinen"] = row["usableBy"]["松"], row["rinenBy"]["松"]
        else:
            # ⭐ **2026-09-08 ── 帯1〜3 も退避を引く。**旧式は `avoid` が 0 坪 固定で、
            #    石段の脇の肩がまるごと有効面に入っていた(⛔ 0 は合格ではなく未測定)。
            # ⭐ **退避は層ごとに違う**【裁き1 庭方 2026-09-08】── 肩が 低木 0.5 / 中木 1.0 /
            #    高木 1.5 間 と刻まれたので、有効面も層ごとに出す。⛔ 一つの `usable` で
            #    三層を代表させない(高木の不足と低木の過剰は**逆向き**の欠陥である)。
            ps = cells[b["band"]]
            row = {"b": b, "tsubo": len(ps) * ct, "rinen": 0.0,
                   "cut": cut.get(b["band"], 0.0), "usableBy": {}, "avoidBy": {},
                   "rinenBy": {}}
            # ⭐ **林縁は帯の中の小領域**(2026-09-08 十六巡目 C-2)── 帯3 の南面がこれ。
            rin = b.get("rinen") or {}
            E = rinen_edges(d, g, b) if rin else []
            dmap = {}
            if rin and E:
                for p in ps: dmap[p] = min(_pt_seg(p, q[0], q[1]) for q in E)
            row["rinenTier"] = {}
            for lay in _LAYS:
                sh = avoid_shapes(d, g, "obi123:" + lay)
                hit = set(p for p in ps if shape_hit(p, sh)) if sh else set()
                rg = rinen_range(b, lay)
                inrin = set(p for p, q in dmap.items() if rg[0] <= q <= rg[1]) if rg else set()
                rn = sum(1 for p in inrin if p not in hit)
                row["avoidBy"][lay] = len(hit) * ct
                row["rinenBy"][lay] = rn * ct
                row["usableBy"][lay] = (len(ps) - len(hit) - rn) * ct
                for ti, t in enumerate(rinen_tiers(b)):
                    rgt = rinen_range_t(b, t, lay)
                    row["rinenTier"][(ti, lay)] = (
                        len([p for p, q in dmap.items()
                             if rgt[0] <= q <= rgt[1] and p not in hit]) * ct) if rgt else 0.0
            # ⚠ 素の `avoid`/`usable` は**高木**の値(表と検査が層ごとに刷る)
            row["avoid"], row["usable"] = row["avoidBy"]["松"], row["usableBy"]["松"]
            row["rinen"] = row["rinenBy"]["松"]
        row["dens"] = band_density(b)
        row["takagi"] = row["usableBy"]["松"] * TSUBO * row["dens"] / 100.0 - row["cut"]
        row["rakuyo"] = row["takagi"] * (b.get("rakuyoRatio") or 0.0)
        for k, key, lay in (("chuboku", "chubokuPer100", "中木"),
                            ("teiboku", "teibokuPer100", "低木")):
            r = b.get(key) or [0, 0]
            row[k] = row["usableBy"][lay] * TSUBO * (r[0] + r[1]) / 2.0 / 100.0
            # ⭐ **林縁の本数は独立の行**(2026-09-08 十六巡目 C-2)── ⛔ 帯の本体の行へ混ぜない
            #    (混ぜたら誰も見ない = 旧の状態)。密度は `rinen` の宣言か帯の上端の従属値。
            # ⭐ **段ごとに別の密度**(④ 庭方 2026-09-09 十七巡目)── ⛔ 合算の密度で掛けない
            nr9 = 0.0
            for ti, t in enumerate(rinen_tiers(b)):
                dr = rinen_dens_t(d, b, t, lay)
                if not dr: continue
                nr9 += (row.get("rinenTier") or {}).get((ti, lay), 0.0) * TSUBO * dr / 100.0
            row[k + "Rinen"] = nr9
        _BSTAT.append(row)
    _BSTAT.append({"skip": skip * ct})
    return _BSTAT


# ---------------------------------------------------------------- 境内の立木3区
_MIXRE = re.compile(r"(松|欅|椋|榎)\s*(\d+)")


_MIXSP = {"欅": "ケヤキ", "椋": "ムクノキ", "榎": "エノキ"}


def cluster_mix(c):
    """塊の `mix`(「松4・欅1」)を [(種, 本数)] へ。⛔ 本数を二重に持たない。"""
    return [(k, int(n)) for k, n in _MIXRE.findall(c.get("mix") or "")]


def zone_h(d, gd):
    """区の松・落葉高木の丈[m]。

    区(`gardens`)は `hBand` の帯から引き、**帯そのもの(`slopeBands`)は自分の宣言を使う**。
    ⚠ 2026-09-07 八巡目 中3 ── 旧式は `hBand` しか見ず、帯4の塊(辻の留め)は
    **部材・丈・樹冠の欄が丸ごと刷られなかった**(いちばん混んだ塊だけが黙っていた)。
    """
    if gd.get("matsuH") or gd.get("rakuyoH"):
        return gd.get("matsuH"), gd.get("rakuyoH")
    b = [q for q in d["slopeBands"] if q["band"] == gd.get("hBand")]
    if not b: return None, None
    return b[0].get("matsuH"), b[0].get("rakuyoH")


def cluster_parts(d, gd, c):
    """塊の部材 — `mix` の割り前 × `planting.parts` の palette。

    戻り (種, palette の点, 本数, 丈, 樹冠, 層の鍵, 変種の列, scaleY 下, scaleY 上)。
    ⭐ **大きさ(変種)は名指しでなく `sizeRule` が丈から選ぶ**(2026-09-07 裁定1)。
    帯の丈は範囲なので、同じ樹種でも丈で変種が変わる — 現れる変種は**全部**返す。
    """
    pal = d["planting"]["parts"]
    mH, rH = zone_h(d, gd)
    # ⭐ **塊が棟高からの下限を宣言していれば松の丈の下端を上げる**
    #    【中8 庭方 2026-09-09 十七巡目 / 書き方は裁4】── ⛔ 数を持たない。
    # ⭐ **上端を部材の箍まで開く塊がある**【決5 庭方 2026-09-09 十八巡目】── ⛔ 帯の `matsuH`
    #    の上端で切ると 4 本が全部その一つの値へ張り付き、棟に対して横一線の『生垣』になる。
    #    上端 = `sizeRule.speciesHCap`(その樹種の最大変種の素の丈 × `scaleYMax`)。⛔ 数を持たない。
    if c.get("matsuHMaxFrom") and mH:
        caps = [q for q in (species_h_cap(d, pt) for pt in pal["松"]) if q]
        if caps:
            a9, b9 = _h_pair(mH)
            mH = [a9, max(b9, max(caps))]
    mf = c.get("matsuHMinFrom")
    if mf and mH:
        m9 = ([q for q in d["munes"] if q["name"] == mf.get("mune")] or [None])[0]
        h9 = mune_h(d, m9) if m9 else None
        if h9 is not None:
            lo9 = h9 * float(mf.get("factor") or 1.0)
            a9, b9 = _h_pair(mH)
            # ⛔ **上端は越えない** ── 越えるなら帯の丈の宣言と衝突しているということで、
            #    検査『塊の松の丈の下限(棟高からの従属)』が⛔で名指しする(⛔ 黙って伸ばさない)。
            if a9 is not None: mH = [min(max(a9, lo9), b9), b9]
    out = []
    for kind, n in cluster_mix(c):
        if kind == "松":
            src, h, sk = pal["松"], mH, "matsu"
        else:
            src = [q for q in pal["落葉"] if q.get("species") == _MIXSP[kind]]
            h, sk = rH, "rakuyo"
        if not src: continue
        wt = sum(q.get("w", 1) for q in src)
        rest = n
        for i, pt in enumerate(src):
            k = n - rest if i == len(src) - 1 else int(round(n * pt.get("w", 1) / float(wt)))
            k = min(k, rest) if i < len(src) - 1 else rest
            rest -= k
            if k <= 0: continue
            vs, ylo, yhi = pick_variants_over(d, pt, h)
            pf = vs[0][1] if vs else pt.get("prefab")
            out.append((kind, pt, k, h, crown_of(d, sk, pf, h), sk, vs, ylo, yhi))
    return out


def sando_edge_uv(d):
    """**社地の境**のうち参道に面する辺(`takagiEdgeLine.fromEdge`)を uv の線分で。"""
    tl = (d["sando"].get("roadside") or {}).get("takagiEdgeLine") or {}
    if not tl.get("fromEdge"): return None
    return edge_offset(d, tl["fromEdge"], 0.0)


def sando_far_edge(d):
    """参道の道敷 `sando.area` のうち**社地の境の向かい側の縁**(觀理院の西縁)。

    ⛔ 辺の番号を書かない(検図の作法)── **社地の境の辺と最も平行な辺**を幾何で同定する
    (その辺自身は端点の一致で除く)。戻り (世界座標の2点)。
    """
    ar = d["sando"].get("area")
    tl = (d["sando"].get("roadside") or {}).get("takagiEdgeLine") or {}
    if not ar or not tl.get("fromEdge"): return None
    a, b = d["polygon"][tl["fromEdge"][0]], d["polygon"][tl["fromEdge"][1]]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    best = None
    for k in range(len(ar)):
        p, q = ar[k], ar[(k + 1) % len(ar)]
        ex, ez = q[0] - p[0], q[1] - p[1]
        le = math.hypot(ex, ez)
        if le < 1e-6: continue
        if min(math.hypot(p[0] - a[0], p[1] - a[1]), math.hypot(q[0] - a[0], q[1] - a[1]),
               math.hypot(p[0] - b[0], p[1] - b[1]), math.hypot(q[0] - b[0], q[1] - b[1])) < 0.3:
            continue                                   # 社地の境の辺そのもの
        dot = abs((ex * dx + ez * dz) / (le * L))
        if best is None or dot > best[0]: best = (dot, p, q)
    return None if best is None else (best[1], best[2])


def sando_road_width(d, v):
    """**局所の道敷幅[m]** ── 社地の境の v の点から、向かいの縁の**直線**までの垂距。

    ⚠ 楔形の区間は道敷の幅が場所で変わる。⛔ 代表値(最も狭い東西の帯の値)を当てない。
    """
    eg = sando_edge_uv(d)
    fe = sando_far_edge(d)
    if eg is None or fe is None: return None
    (au, av), (bu, bv) = eg
    if abs(bv - av) < 1e-9: return None
    t = (v - av) / (bv - av)
    g = G(d)
    px, pz = g.W(au + t * (bu - au), v)
    (e0, e1) = fe
    ex, ez = e1[0] - e0[0], e1[1] - e0[1]
    le = math.hypot(ex, ez) or 1.0
    return abs((px - e0[0]) * ez - (pz - e0[1]) * ex) / le


def sando_rokata(d, v):
    """局所の (路肩[m], 路肩+側溝[m])。`rokataRule` の従属値。⛔ 数を json に持たない。"""
    rs = d["sando"].get("roadside") or {}
    W_ = sando_road_width(d, v)
    if W_ is None or rs.get("roadWidth") is None or rs.get("sokkoKen") is None: return None
    sk = rs["sokkoKen"] * d["const"]["ken"]
    ro = (W_ - rs["roadWidth"] - 2.0 * sk) / 2.0
    return (ro, ro + sk)


def overhang_limit(d, c):
    """林縁の塊の **張り出しの上限[m]** = 局所の(路肩+側溝)− `marginM`。

    ⭐ 2026-09-07 八巡目 裁定2 ── ⛔ **上だけを置く**(下限は置かない)。
    戻り [(v, 上限)] を塊の `vRange` の両端で。
    """
    oh = c.get("overhangFrom") or {}
    mg = oh.get("marginM")
    vr = c.get("vRange")
    if mg is None or not vr: return []
    out = []
    for v in (vr[0], vr[1]):
        q = sando_rokata(d, v)
        if q is None: continue
        out.append((v, q[1] - mg, q[0], q[1]))
    return out


# ---------------------------------------------------------------- 見所と主景
def shukei_hmin(d, sk):
    """★主景の木の**丈の下限**[m]。⛔ 数を json に持たない(`tree.hMinFrom` の従属値)。

    ⭐ **2026-09-08 に従属値へ移した**【A-2 の裁き 庭方】── 旧値 18.0 m は部材と箍では届かない
    丈で、`scaleY` が `sizeRule.scaleYMax` を超えていた(⛔ 松で閉じたのと同じ欠陥)。
    **落葉高木の最も高い変種の素の丈 × `sizeRule.scaleYMax`** = 箍の内で出せる最も高い丈。
    ⛔ 部材を新造しない・⛔ 箍を上げない。引けなければ None(= 測れていない)。
    """
    if not (sk.get("tree") or {}).get("hMinFrom"): return None
    cap = (size_rule(d) or {}).get("scaleYMax")
    hs = [q[3] for pt in d["planting"]["parts"].get("落葉", []) for q in part_variants(d, pt)]
    if not hs or cap is None: return None
    return max(hs) * cap


# 方位の語 → 真北からの角[°](時計回り・世界 +Z=北 / +X=東)。⛔ 設計値ではない — 語の辞書。
_DIR_DEG = {"北": 0.0, "北北東": 22.5, "北東": 45.0, "東北東": 67.5, "東": 90.0,
            "東南東": 112.5, "南東": 135.0, "南南東": 157.5, "南": 180.0,
            "南南西": 202.5, "南西": 225.0, "西南西": 247.5, "西": 270.0,
            "西北西": 292.5, "北西": 315.0, "北北西": 337.5}


def _azim(du, dv):
    """uv の向きの**真北からの角**[°]。当社のグリッドは u=東+ / v=北+(世界軸そのもの)。"""
    return math.degrees(math.atan2(du, dv)) % 360.0


def viewpoint_eye(d, g, vp):
    """見所の**眼高**[m]とその出所。⛔ 数を json に持たない(規則4)。

    ⭐ **設計地盤(平場があれば平場・無ければ現地形)+ 座面高 + `eyeOver`**
    (2026-09-06 検図5巡目 低15 — 旧版は現地形しか見ず、V2/V-Z1/V-Z3 は `eye` に
    `terraces[1].y + eyeOver` を書き写して二重に持っていた)。
    """
    u, v = vp["uv"]
    if vp.get("eye") is not None: return vp["eye"], "設計値"
    h = design_y(d, g, *g.W(u, v))
    base = "設計地盤" if h is not None else "現地形"
    if h is None: h = dem_h(*g.W(u, v))
    seat = 0.0
    if vp.get("seatOn"):
        _k, _, _nm = vp["seatOn"].partition(":")
        for _p in d.get(_k, []):
            if _p.get("name") == _nm: seat = (_p.get("plan") or {}).get("seatH", 0.0)
    return ((h or 0.0) + seat + vp.get("eyeOver", 0.0),
            "%s %.2f m%s + %.2f m" % (base, h or 0.0,
                                      " + 座面 %.2f m" % seat if seat else "",
                                      vp.get("eyeOver", 0.0)))


def viewpoint_target(d, vp):
    """見所が**見ている先**の (u,v) と出所。`shows` の対象の芯 → 無ければ None。"""
    for nm in vp.get("shows", []):
        if nm.startswith("★主景"):
            for gd in d["gardens"]:
                sk = gd.get("shukei")
                if sk and sk.get("tree", {}).get("uv"):
                    return tuple(sk["tree"]["uv"]), "shows:★主景の木"
            continue
        for holder in d["gardens"] + d["slopeBands"] + [d["planting"]]:
            for c in holder.get("clusters", []) + holder.get("viewClusters", []):
                if c["name"] != nm: continue
                Q = [p for P_ in cluster_polys(c) for p in P_]
                if not Q: continue
                return ((sum(q[0] for q in Q) / len(Q), sum(q[1] for q in Q) / len(Q)),
                        "shows:" + nm)
    return None, None


def derive_viewpoints(d, g):
    """見所の **`eyeH`(眼高)と `look`(向き)を起こす**【B-3 庭方 2026-09-08 十六巡目】。

    ⛔ **数を json に置かない**(規則4)── 焼き出しが持つのは算出値である。
    ⚠ 旧図は焼き出しの `eyeH`/`look` が両方 `null` で、⛔ **検証レンダを図の見所に合わせられなかった**
    (規則19)。⚠ **算出すると `dir` の散文と食い違う点が出る** — ⛔ 黙って `dir` を書き換えない
    (向きは庭方の意匠)。食い違いは検査が毎回刷る。
    """
    for vp in d.get("viewpoints", []):
        eye, src = viewpoint_eye(d, g, vp)
        vp["eyeH"] = round(eye, 3)
        vp["_eyeFrom"] = src
        tgt, tsrc = viewpoint_target(d, vp)
        tu, tv = tgt if tgt else (None, None)
        dd = _DIR_DEG.get(vp.get("dir") or "")
        if tu is not None:
            az = _azim(tu - vp["uv"][0], tv - vp["uv"][1])
            frm = tsrc
        elif dd is not None:
            az, frm = dd, "dir:" + vp["dir"]
        else:
            vp["look"] = None
            continue
        vp["look"] = {"azDeg": round(az, 2), "from": frm,
                      "world": [round(math.sin(math.radians(az)), 4),
                                round(math.cos(math.radians(az)), 4)],
                      "_": "**真北からの角**[°](時計回り)。`world` は世界の (x, z) の単位ベクトル"}
        vp["_dirDeg"] = dd


_SG_LAYER = {"松": ("松", "matsu"), "落葉": ("落葉", "rakuyo"),
             "中木": ("中木", "chuboku"), "低木": ("低木", "chuboku")}


def single_parts(d, sg):
    """一本立ちが指す palette の点。`part` の名指しがあればその一点、無ければ層の全部。

    ⭐ 名指しは**樹種と個体**だけを指す — 大きさ(変種)は `sizeRule` が丈から選ぶので、
    `part` に大きさは書かない(2026-09-07 裁定1)。層の宣言が無ければ空(=**測れていない**)。
    """
    key = _SG_LAYER.get(sg.get("layer") or "")
    if key is None: return []
    pal = d["planting"]["parts"].get(key[0], [])
    named = [pt for pt in pal if pt.get("api") == sg.get("part")]
    return named or pal


def single_prefab(d, sg):
    """一本立ちが据える部材の prefab 名(**大きさまで解いた実名**)。無ければ None。"""
    pal = single_parts(d, sg)
    if not pal: return None
    q = pick_variant(d, pal[0], sg.get("h"))
    return q[1] if q else pal[0].get("prefab")


def single_crown(d, sg):
    """一本立ちの**据えたあとの樹冠の半径[間]**。`crown` があればそれ、無ければ部材と規約から。

    ⭐ 2026-09-06b — 一本立ちが**部材を名指し**(`part`)していればその一点だけを見る
    (⛔ palette の最大で代表させない)。個体の `scaleXZ` は `scaleRule` の倍率の**上に**掛ける。
    ⛔ **層の宣言が無ければ None を返す**【中1 庭方 2026-09-07 八巡目】── 旧式は既定を
    「落葉」に落としており、層も部材も丈も宣言していない一本立ちに**落葉 palette の最大**を
    当てて「樹冠 16.31 m の落葉高木」の円を描いていた。⛔ **既定で最大の落葉樹冠を当てるのは
    『測れていない物を測れたことにする』形**(規則19)。
    """
    ken = d["const"]["ken"]
    if sg.get("crown"): return sg["crown"] / 2.0 / ken
    key = _SG_LAYER.get(sg.get("layer") or "")
    if key is None: return None
    best = None
    for pt in single_parts(d, sg):
        q = pick_variant(d, pt, sg.get("h"))
        # ⭕ **一本立ちは孤立木**なので `isolatedXZ`(2026-09-08 中6・庭方)
        c = crown_of(d, key[1], (q[1] if q else pt.get("prefab")), sg.get("h"), iso=True)
        if c is None: continue
        v = max(c) / 2.0 / ken
        best = v if best is None else max(best, v)
    rule0 = d["planting"]["scaleRule"].get(key[1]) or {}
    if best is not None and sg.get("scaleXZ") and rule0.get("crownPerH") is None:
        rule = rule0.get("scaleXZ") or [1.0, 1.0]
        best = best / max(rule) * max(sg["scaleXZ"])
    return best


def single_lean(d, sg):
    """一本立ちの**傾き**(度の範囲, 傾ける先の (u,v))。宣言が無ければ None。

    ⭐ 2026-09-08 中3(庭方)── 部材が『林の松(直立・段)』に替わったので、⛔ **指図が言わなければ
    棟梁は真っ直ぐ立てる**。`leanDeg`(度の範囲)と `leanToward`(門の名)で宣言する。
    ⛔ 傾きの数をここに書かない(json が正典)。
    """
    dg = sg.get("leanDeg")
    if not dg: return None
    tw = sg.get("leanToward") or ""
    for gt in d["gates"]:
        if gt["name"] and gt["name"] in tw and gt.get("u") is not None:
            return (dg, (gt["u"], gt["v"]))
    return (dg, None)


def gate_at(d, q):
    """点 (u,v) が門の平面の中なら、その門。無ければ None。"""
    for gt in d["gates"]:
        s9, t9 = gate_local(gt, q)             # ⭐ 門の軸で測る(K004)
        if abs(s9) <= gt["plan"]["du"] / 2.0 and abs(t9) <= gt["plan"]["dv"] / 2.0: return gt
    return None


def route_w(d, rt, terrace=None, at=None):
    """動線の路面幅[m]。**区間ごとの読み替え**。

    ⛔ 幅を二重に持たない — `w` は参道(公道)の幅で、前庭の中は門口から導いた別の値
    (庭方 2026-09-06b)。⭐ **門をくぐる区間は `gates[].monguchiKen` が幅を決める**
    (2026-09-06 検図5巡目 中7 — 宣言だけあって計算が無く、表参の通行帯 3.636m が
    門口 1.818m の2倍のまま両脇柱へ 0.909m ずつ乗っていた)。`at` は測る点 (u,v)。
    **門 > 段 > 素の `w`** の順で決まる。
    """
    if at is not None:
        gt = gate_at(d, at)
        if gt is not None and gt.get("monguchiKen"):
            return gt["monguchiKen"] * d["const"]["ken"]
    if terrace and (rt.get("wByTerrace") or {}).get(terrace) is not None:
        return rt["wByTerrace"][terrace]
    tw = rt.get("tailW")
    if tw and at is not None and rt.get("world") and rt.get("tail"):
        # ⭐ `tail` の頂点 `fromVertex` から先の脚は細い(庭方 2026-09-15)── 測る点がその脚に載るか
        kd = d["grid"]["keidai"]; ken = d["const"]["ken"]
        tl = [((q[0] - kd["x0"]) / ken, (q[1] - kd["z0"]) / ken) for q in rt["tail"]]
        for k in range(int(tw["fromVertex"]), len(tl) - 1):
            if _pt_seg(at, tl[k], tl[k + 1]) < 1e-6:
                return float(tw["wKen"]) * ken
    return rt["w"]


def _rect_seg_dist(rect, a, b):
    """矩形と線分の距離[間](交わっていれば 0)。⛔ 端にキャップを付けない扱いはしない
    ── ここで測るのは『箱がどの石段にいちばん近いか』であって退避ではない。"""
    u0, v0, u1, v1 = min(rect[0], rect[2]), min(rect[1], rect[3]), \
        max(rect[0], rect[2]), max(rect[1], rect[3])
    C = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    ds = [_pt_seg(q, a, b) for q in C]
    for q in (a, b):
        du = max(u0 - q[0], 0.0, q[0] - u1)
        dv = max(v0 - q[1], 0.0, q[1] - v1)
        ds.append(math.hypot(du, dv))
    return min(ds)


def view_cluster_crown(d, c):
    """視線の塊の**松の樹冠径**(最小, 最大)[m]。⛔ 数を json に持たない(丈と部材からの従属値)。"""
    h = c.get("matsuH")
    if not h: return None
    cr = crown_of(d, "matsu", None, h)
    if cr is not None: return cr
    vs = []
    for pt in d["planting"]["parts"]["松"]:
        v2, _a, _b = pick_variants_over(d, pt, h)
        vs += v2
    if not vs: return None
    xz = d["planting"]["scaleRule"]["matsu"].get("scaleXZ") or [1.0, 1.0]
    w = [part_geom({"prefab": q[1]})[0] for q in vs]
    return (min(w) * xz[0], max(w) * xz[1])


def view_cluster_eda_rows(d, c):
    """視線の塊 × その樹冠が差し掛かる石段 ── [(箱の番号, 石段, どちら, 幹の離れ m, 掛かり m,
    勾配 %, 要る枝下 m)]。

    ⭐ **`edaShitaFrom` の規約はここが唯一の実装**【中2 庭方 2026-09-08 十二巡目】── 図が刷る値と
    検査が測る値と、指図が宣言する枝下が**同じ一本の式**から出るようにする。
    ⚠ **石段は登る**ので、幹の足元で測った枝下は、樹冠が差し掛かる先の踏面の上では
    **樹冠の張り出し × その石段の勾配**だけ目減りする。
    ⛔ 対象は `axis` の一本だけにしない【低5 検図15巡目】── **箱に最も近い石段**も測る。
    """
    ken = d["const"]["ken"]
    eda = ((d["planting"]["plantRule"].get("crownRule") or {}).get("takagi") or {}).get("edaShitaMinM")
    cr = view_cluster_crown(d, c)
    bx = cluster_boxes(c)
    if eda is None or cr is None or not bx: return []
    rr = cr[1] / 2.0
    kd = [k for k in d["kaidans"] if k["name"] == c.get("axis")]
    out = []
    for j, rect in enumerate(bx):
        seen = []
        near = _kaidan_near_box(d, rect)
        for tag, k in (("軸", kd[0] if kd else None),
                       ("箱に最も近い", near[0] if near else None)):
            if k is None or k["name"] in seen: continue
            seen.append(k["name"])
            pts = [tuple(x) for x in (k.get("pts") or [k["a"], k["b"]])]
            dd = min(_rect_seg_dist(rect, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            hw2 = kaidan_wken(d, k) / 2.0
            gr = (k.get("grade") or 0.0) / 100.0
            out.append((j + 1, k, tag, (dd - hw2) * ken, (rr / ken - (dd - hw2)) * ken,
                        k.get("grade") or 0.0, eda + max(0.0, rr) * gr))
    return out


def derive_view_eda(d):
    """`viewClusters[].edaShitaFrom` から**枝下**を起こす【中2 庭方 2026-09-08 十二巡目】。

    ⛔ 数を json に持たない ── 樹冠(部材と丈からの従属値)と石段の勾配から毎回算出する。
    ⛔ **宣言(`edaShitaFrom`)が無い塊には何も入れない** — 既定で高木の下限へ落ちると、
    棟梁は平地の値で建て、坂の踏面の上に枝が来る(検査が『宣言していない』と刷る)。
    """
    for c in d["planting"].get("viewClusters", []):
        if not c.get("edaShitaFrom") or c.get("edaShita") is not None: continue
        rows = view_cluster_eda_rows(d, c)
        if rows: c["edaShita"] = max(q[6] for q in rows)


def _kaidan_near_box(d, rect):
    """箱に**最も近い石段**と、その敷きの縁までの離れ(間)。⛔ `axis` の一本で代表させない
    【低5 検図15巡目 → 2026-09-08】── 額縁の樹冠は女坂の踏面へも掛かる。"""
    best = None
    for k in d["kaidans"]:
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        dd = min(_rect_seg_dist(rect, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        hw = kaidan_wken(d, k) / 2.0
        if best is None or dd - hw < best[1]: best = (k, dd - hw, dd, hw)
    return best


def prop_rects(d):
    """面を持つ点景(`plan {du,dv}`[間] か `planM {du,dv}`[m] と `yaw`)の輪郭。(名, 4点[uv]) の列。

    ⚠ 2026-09-06 検図4巡目 低14 — 縁台は点だけで、図に縮尺どおりに描けず総当たりにも載らなかった。
    ⭐ **呼び名は `labels` から採る**(2026-09-06 検図6巡目 低7)— 「其N」を焼き込んでいたので、
    総当たり・退避・断面の marks が「其N」、設計値と表が「甲1/乙2」で**突き合わせられなかった**。
    ⭐ **2026-09-07 検図9巡目 低4 — `planM`(m)を足した。**石灯籠・手水鉢は寸法の出所が
    在庫部材の実測と部材表(どちらも m)なので、間へ丸めて持つと出所が消える。
    ⛔ **一つの点景が `plan` と `planM` の両方を持たない**(二本立てにしない)。
    ⚠ 面を持たない点景は `prop_rects` が矩形を作らず、**面の総当たり・犬走り・視線の抜き・
    断面の marks から丸ごと抜ける**(帯へ動かしても鳴らない)。
    """
    out = []
    ken = d["const"]["ken"]
    for p in d.get("props", []):
        pl, plm = p.get("plan"), p.get("planM")
        if pl and plm:
            raise SystemExit("点景『%s』が `plan` と `planM` の両方を持つ(⛔ 二本立て)" % p["name"])
        if plm: pl = {"du": plm["du"] / ken, "dv": plm["dv"] / ken}
        if not pl or not p.get("uv"): continue
        yaws = p.get("yaw") or [0] * len(p["uv"])
        for i, (u, v) in enumerate(p["uv"]):
            a = math.radians(yaws[i] if i < len(yaws) else 0)
            ca, sa = math.cos(a), math.sin(a)
            hu, hv = pl["du"] / 2.0, pl["dv"] / 2.0
            q = [(-hu, -hv), (hu, -hv), (hu, hv), (-hu, hv)]
            out.append(("%s %s" % (p["name"], prop_label(p, i)),
                        [(u + x * ca - y * sa, v + x * sa + y * ca) for x, y in q]))
    return out


def prop_label(p, i):
    """点景の i 番目の呼び名 ── `labels` があればそれ、無ければ「其N」。⛔ 二本立てにしない。"""
    lb = p.get("labels") or []
    return lb[i] if i < len(lb) else "其%d" % (i + 1)


def prop_rect_of(d, name, label):
    """点景の1点の輪郭[uv 4点]。無ければ None。"""
    for nm, Q in prop_rects(d):
        if nm == "%s %s" % (name, label): return Q
    return None


def kaidan_wken(d, k):
    """石段の**幅**[間] ── 正典は `wKen`(⛔ `w`[m] と二本立てにしない・検図7巡目 低5)。

    ⚠ 旧版は `wKen or w/ken` で、参道の階が 5.500 m 対 3.03 間(5.5085 m)の二本立てだった。
    **図が描く階の帯が、その階のために板塀に開けた口より 8.5 mm 狭い**という食い違いが出る。
    """
    if k.get("wKen") is None:
        raise SystemExit("石段『%s』に `wKen` が無い(幅の正典は間)" % k["name"])
    return k["wKen"]


def kaidan_wm(d, k):
    """石段の幅[m] ── `wKen` × 間。⛔ メートルの値を json に持たない。"""
    return kaidan_wken(d, k) * d["const"]["ken"]


def segs(o):
    """石段・土留めの区間。`pts`(折れ線)があればそれ、無ければ a→b の1区間。

    2026-08-23、女坂を明治16年実測図の**屈曲**へ改めたときに導入した。
    """
    p = o.get("pts")
    if p:
        return [(p[i], p[i + 1]) for i in range(len(p) - 1)]
    # ⛔ **a / b を持たない物で落ちない**【庭方 低 2026-09-19】── 折れ線だけを持つ土留め
    #   (`TW_SandoKai_W` / `_E`)は死んだ `a`/`b` を落としてあるので、`pts` の無い道から
    #   ここへ来たら**区間が無い**と答える(⛔ KeyError で生成器ごと止めない)。
    if "a" in o and "b" in o:
        return [(o["a"], o["b"])]
    return []


# ---------------------------------------------------------------- 現況図 / 切盛図(スキル §3a・§3b)
DEM = None


def dem():
    """造成前の地形【確度P】。`docs/Sashizu/sanno_dem.json`。

    ⚠ **実体は正本 `docs/Sashizu/base_dem.json` からの切り出し**(生成器 `Tools/Sashizu/build_base_dem.py`)。
    ⛔ **Unity の live terrain から採り直さない**(CLAUDE.md 規則12)— live は自他の造成が
    乗る作業面で、**採った時刻で値が変わる**。2026-08-23 に岡部・土井が松平の造成を
    「造成前の地形」として吸い込む事故が起きた(山王は範囲が届かず無傷)。
    ⛔ `sanno_dem.json` を手で編集しない。区画を動かしたら `build_base_dem.py` を回す。
    """
    global DEM
    if DEM is None:
        DEM = json.load(open(os.path.join(DOC, "sanno_dem.json"), encoding="utf-8"))
    return DEM


def dem_h(x, z):
    D = dem()
    i = (x - D["x0"]) / D["step"]; j = (z - D["z0"]) / D["step"]
    a, b = int(math.floor(i)), int(math.floor(j))
    if a < 0 or b < 0 or a + 1 >= D["nx"] or b + 1 >= D["nz"]: return None
    fx, fz = i - a, j - b
    H = D["h"]
    return ((H[b][a] * (1 - fx) + H[b][a + 1] * fx) * (1 - fz)
            + (H[b + 1][a] * (1 - fx) + H[b + 1][a + 1] * fx) * fz)


def _stair_hit(d, g, x, z):
    """石段の通路(帯)に載る点なら **(石段の名, 設計高さ)**。載らなければ (None, None)。

    ⭐ **どの石段か**を返す【低4 検図16巡目 → 2026-09-08】── 切盛図の註が『男坂の盛土/切土』を
    語るのに、集計は『石段(男坂・女坂・参道の階)』の一括りしか持っておらず、**註の数がどの計算
    からも出ていなかった**。⛔ 註へ数を直書きしない ── 坂ごとに数えて刷る。
    """
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        hw = kaidan_wm(d, k) / 2.0
        tot = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                  for i in range(len(pts) - 1)) or 1.0
        acc = 0.0
        for i in range(len(pts) - 1):
            ax, az = pts[i]; bx, bz = pts[i + 1]
            dx, dz = bx - ax, bz - az
            L = math.hypot(dx, dz) or 1.0
            t = ((x - ax) * dx + (z - az) * dz) / (L * L)
            if t < 0 or t > 1: acc += L; continue
            px, pz = ax + dx * t, az + dz * t
            if math.hypot(x - px, z - pz) <= hw:
                sfrac = (acc + L * t) / tot
                # ⚠ pts[0] が山上か坂下かで向きが変わる(2026-08-23 検図 — 男坂だけ上下逆だった)。
                #    第一点の自然地形が最後の点より高ければ pts[0] = 山上。
                h0 = dem_h(pts[0][0], pts[0][1]); h1 = dem_h(pts[-1][0], pts[-1][1])
                if h0 is not None and h1 is not None and h0 > h1:
                    sfrac = 1.0 - sfrac
                # ⚠ **踊り場のある坂は直線補間にならない**(2026-08-24 検図 高-4 —
                #    切盛図が男坂で断面と最大1.34m 食い違っていた)。断面と同じ割付から引く。
                return (k["name"], stair_y_at(k, sfrac))
            acc += L
    return (None, None)


def _stair_y(d, g, x, z):
    """石段の通路(帯)の設計高さ。坂も造成の対象(2026-08-23 検図 — 図から丸ごと落ちていた)。"""
    return _stair_hit(d, g, x, z)[1]


def stair_spans(k):
    """石段の割付を **(s0, s1, 面の高さ)** の列で返す(s は坂下からの展開長)。

    断面(stair_profile)・切盛図(_stair_y)・動線の昇りが**この一つの関数**を通る。
    ⚠ 二つの式で別々に割ると蹴上1段ぶん(0.30m)ずれる(2026-08-24 検図 高-4)。
    """
    keri = k.get("keri", 0.30); fumi = k.get("fumi", 0.45); od = k.get("odoriba", 0.0)
    fl = k.get("flights") or ([k["steps"]] if k.get("steps") else None)
    if not fl: return None, None
    y0 = k["yBot"]
    out, sacc, n = [], 0.0, 0
    for fi, fn in enumerate(fl):
        for _ in range(fn):
            out.append((sacc, sacc + fumi, y0 + n * keri)); sacc += fumi; n += 1
        if fi < len(fl) - 1 and od > 0:
            out.append((sacc, sacc + od, y0 + n * keri)); sacc += od
    return out, sacc


def stair_y_at(k, sfrac):
    """石段の縦断上の高さ。sfrac は坂下 0 → 頭 1。"""
    sp, tot = stair_spans(k)
    if sp is None:                        # 斜路 — 一様勾配
        return k["yBot"] + (k["yTop"] - k["yBot"]) * max(0.0, min(1.0, sfrac))
    w = max(0.0, min(1.0, sfrac)) * tot
    if w >= tot - 1e-9: return k["yTop"]  # 頭は境内面(最後の蹴上を上がりきった高さ)
    for a, b, y in sp:
        if w <= b + 1e-9: return y
    return k["yTop"]


def offset_poly_in(P, ins):
    """多角形を内側へ ins だけ寄せる(角は留め継ぎ)。板塀・柵を平場から機械生成するため。"""
    n = len(P)
    # 向きを CCW に揃える
    a2 = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    Q = P if a2 > 0 else P[::-1]
    out = []
    for i in range(len(Q)):
        p0, p1, p2 = Q[i - 1], Q[i], Q[(i + 1) % len(Q)]
        def nrm(a, b):
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz) or 1.0
            return (-dz / L, dx / L)          # CCW なら内向き
        n1, n2 = nrm(p0, p1), nrm(p1, p2)
        bx, bz = n1[0] + n2[0], n1[1] + n2[1]
        L = math.hypot(bx, bz)
        if L < 1e-6: bx, bz, L = n1[0], n1[1], 1.0
        cosh = max(0.35, (bx * n1[0] + bz * n1[1]) / L)     # 留めの伸び(鋭角で暴れないよう頭打ち)
        out.append([p1[0] + bx / L * ins / cosh, p1[1] + bz / L * ins / cosh])
    return out if a2 > 0 else out[::-1]


def gap_source(d, gf, owner):
    """`gapFrom` / `vFrom` が指す物の **芯[uv] と半幅[間]**。⛔ 口の半幅を literal で持たない。

    ・`kaidan` ── 石段。半幅 = `wKen`/2、芯 = 折れ線の第1点(平場の縁に取り付く端)
    ・`gate`   ── 門。半幅 = `plan[span]`/2(既定は桁行 `dv` の半分)、芯 = 門の芯
      ⭐ `edge: "側柱の外面"`(= 一間門なら `"本柱の外面"`。**同じ面の呼び名**で、門の柱の数で
      名が変わるだけ)なら半幅 = 芯から**幅の脇の柱の外面**まで(`gate_col_face_dist`)
      【普請奉行の裁定 2026-09-14 案A を回廊の基壇の口へ及ぼす — 回廊の端 `endFrom` と同じ面】。
      ⛔ 柱芯のまま開けると、門の基壇・礎盤が基壇の石垣の口の縁へ食い込む(検図 2026-09-14 高)
      ⚠ **呼び名を一つに揃える**【低 検図1巡目 → 2026-09-18】── 中門(一間平唐門)の口は
        `gapFrom.edge` / `_gapFrom` / `endSeatM.t` / `joints[].bFace` で「側柱」「本柱」と
        三様に書かれており、⛔ 実装が別の面を探す余地が残っていた。⇒ 一間門は **`本柱の外面`** 一本。
    """
    if gf.get("kaidan"):
        k = [q for q in d["kaidans"] if q["name"] == gf["kaidan"]]
        if not k: raise SystemExit("『%s』の `gapFrom` が引けない: %s" % (owner, gf["kaidan"]))
        k = k[0]
        p = (k.get("pts") or [k["a"], k["b"]])[0]
        return (p[0], p[1]), kaidan_wken(d, k) / 2.0
    if gf.get("gate"):
        gt = gate_by_name(d, gf["gate"])
        eg = gf.get("edge")
        if eg is None:
            return (gt["u"], gt["v"]), gt["plan"][gf.get("span", "dv")] / 2.0
        if eg == "門の基壇の脇面":
            # ⭐ 【石垣の設計 2026-09-14 ②】口の縁 = 門の部材の**最下の帯(基壇)の幅の脇の面**
            #    (`bom[].outlineM` の hM が最も低い帯の |widthM| の最大)。⛔ 数を持たない。
            b9 = gate_bom_row(d, gt) or {}
            ol9 = b9.get("outlineM") or []
            if not ol9:
                raise SystemExit("『%s』── 門『%s』の部材に外形 `outlineM` が無い(基壇の脇面を出せない)" % (owner, gt["name"]))
            low = min(ol9, key=lambda q: q["hM"][0])
            return (gt["u"], gt["v"]), max(abs(low["widthM"][0]), abs(low["widthM"][1])) / d["const"]["ken"]
        if eg not in ("側柱の外面", "本柱の外面"):
            raise SystemExit("『%s』の `gapFrom.edge` が読めない: %s" % (owner, eg))
        _p, n = gate_axes_uv(gt)
        fc = [f for f, v in _FACE_VEC.items() if abs(v[0] * n[0] + v[1] * n[1]) >= 0.99]
        if not fc:
            raise SystemExit("『%s』── 門『%s』の幅の脇の面が東西南北に揃わない(幅の脇の柱の外面を出せない)"
                             % (owner, gt["name"]))
        return (gt["u"], gt["v"]), gate_col_face_dist(d, gt, fc[0])[0]
    raise SystemExit("『%s』の `gapFrom` が何を指すのか読めない" % owner)


def derive_gaps(d):
    """**口は、その口が通す物の幅からの従属値**にする ── 囲い(`runs`)と土留め(`terraceWalls`)の両方。

    ⚠ 2026-09-07 検図8巡目 中3 — `wKen` 一本化(7巡目 低5)が**土留めの口に届いていなかった**。
    `TW_Zentei_W`(男坂の口)・`TW_Zentei_N`(参道の階の口)・`TW_Kairo_E`/`_W`(楼門の口)の
    半幅と、男坂の側壁 `TW_Otoko_N`/`_S` の通りが literal で、**石段の幅を動かしても口は動かない**
    (1.82 m の階に 7.0 m の口が残る)形だった。差が今日 0.0 mm でも、**動かした日に破れる**。
    ⛔ どちらの軸に開くかも書かない — 辺の向き(a→b)から決める。
    """
    for o in d["runs"] + d["terraceWalls"]:
        gf = o.get("gapFrom")
        if not gf: continue
        (cu, cv), hw = gap_source(d, gf, o["name"])
        o["gapHalf"] = hw
        a, b = o.get("a"), o.get("b")
        if a is not None and b is not None and abs(a[0] - b[0]) > 1e-9 and abs(a[1] - b[1]) > 1e-9:
            # ⭐ **斜めの辺**(回した枠の基壇 — 2026-09-14)── 口の芯は通す物の芯から辺へ下ろした足、
            #    半幅は**辺に沿って** hw。`gap_split` は走る軸の座標で割るので、その軸への射影で持つ。
            #    ⛔ 芯の v(または u)をそのまま使わない ── 枠の角のぶん口が片側へずれる。
            L9 = math.hypot(b[0] - a[0], b[1] - a[1])
            ex, ey = (b[0] - a[0]) / L9, (b[1] - a[1]) / L9
            t9 = (cu - a[0]) * ex + (cv - a[1]) * ey
            fu, fv = a[0] + ex * t9, a[1] + ey * t9
            if abs(ex) < abs(ey):
                o["gapV"] = fv; o.pop("gapU", None); o["gapHalf"] = hw * abs(ey)
            else:
                o["gapU"] = fu; o.pop("gapV", None); o["gapHalf"] = hw * abs(ex)
            continue
        if a is not None and b is not None and abs(a[0] - b[0]) < abs(a[1] - b[1]):
            o["gapV"] = cv; o.pop("gapU", None)    # v に走る辺 → 口は v で開く
        else:
            o["gapU"] = cu; o.pop("gapV", None)
    # 石段の**両側の側壁**の通り ── 芯 ± 半幅(⛔ ±1.925 のような数を持たない)
    for w in d["terraceWalls"]:
        vf = w.get("vFrom")
        if not vf: continue
        (cu9, cv), hw = gap_source(d, vf, w["name"])
        if vf["side"] in ("東", "西"):
            # ⭐ **v に走る石段の袖**(参道の階 ── ユーザー裁定〈造成の縁〉2 2026-09-19)── 通りは芯 ± 半幅で
            #   **u** が決まり、走りは**石段の折れ線そのもの**。⛔ 石段の座標を壁へ書き写さない
            #   (規則4 ── 石段が動けば袖も動く)。
            k9 = ([k for k in d["kaidans"] if k["name"] == vf["kaidan"]] or [None])[0]
            if k9 is None:
                raise SystemExit("袖の石垣『%s』の `vFrom.kaidan` が引けない" % w["name"])
            pts9 = k9.get("pts") or [k9["a"], k9["b"]]
            u9 = round(cu9 + (hw if vf["side"] == "東" else -hw), 4)
            w["a"] = [u9, pts9[0][1]]; w["b"] = [u9, pts9[-1][1]]
            continue
        w["a"][1] = w["b"][1] = cv + (hw if vf["side"] == "北" else -hw)


def derive_garden_vertex_from(d):
    """**区の頂点・名指しの木を囲いの辺から従属させる**【庭方 2026-09-14c】── `gardens[].vertexFrom` と
    `gardens[].shukei.tree.uFrom`。辺は軸に平行な run(`a`/`b` のその座標が等しい)に限る。
    値 = 辺の座標 + `offKen` + `side` × (退避 `planting.clearance.keidai[clearance]` + `marginKen`)。⛔ json の数を読まない。"""
    runs = {r["name"]: r for r in d["runs"]}
    ck = d["planting"]["clearance"]["keidai"]

    def coord(sp, ax):
        r = runs.get(sp.get("run"))
        j = 0 if ax == "u" else 1
        if r is None or abs(r["a"][j] - r["b"][j]) > 1e-9:
            raise SystemExit("`vertexFrom` の辺『%s』が無いか、%s に平行でない" % (sp.get("run"), ax))
        off = float(sp.get("offKen", 0.0))
        if sp.get("clearance"):
            off += float(sp.get("side", 1)) * (float(ck[sp["clearance"]]) + float(sp.get("marginKen", 0.0)))
        return round(r["a"][j] + off, 4)

    for gd in d["gardens"]:
        for vf in gd.get("vertexFrom") or []:
            P = gd["poly"][vf["i"]]
            if vf.get("u"): P[0] = coord(vf["u"], "u")
            if vf.get("v"): P[1] = coord(vf["v"], "v")
        tr = (gd.get("shukei") or {}).get("tree") or {}
        if tr.get("uFrom"): tr["uv"][0] = coord(tr["uFrom"], "u")


def derive_runs(d, g):
    """平場の輪郭に従う囲いを**その場で生成する**(2026-08-23 検図 中-5)。

    囲いの座標を独立に持つと、平場を動かしたとき黙って取り残される
    (前庭を多角形にしたとき南の板塀が5m内側に残った)。
    ⭐ 境内の外周は 2026-09-07 のユーザー裁定で**腰高の柵**になった(旧・板塀)。
    ⛔ 生成の仕方は変わらない — 種別が替わっても輪郭からの従属値である。
    """
    derive_gaps(d)             # 口は通す物の幅からの従属値(囲い・土留めの両方・検図8巡目 中3)
    derive_garden_vertex_from(d)   # 立木・西の東縁と★主景の欅は透塀の辺からの従属値(庭方 2026-09-14c)
    # ⛔ **宣言が無ければ止める**(検図9巡目 中3)— 既定値で黙って埋めると、
    #    `const.inubashiri` を消しても板塀が同じ所に立ち、検査も鳴らない
    if d["const"].get("inubashiri") is None:
        raise SystemExit("犬走り `const.inubashiri` の宣言が無い(境内の囲いの寄せ幅)")
    ins = d["const"]["inubashiri"] / d["const"]["ken"]
    by = {r["name"]: r for r in d["runs"]}
    if "Ita_Keidai" not in by: return
    uv = d["terraces"][0]["uv"]
    off = offset_poly_in(uv, ins)
    # ⚠ **回廊の基壇が東front を成すので、平場の東の張り出しには塀を回さない**
    #    (2026-08-24 検図 高-1 — 機械化したとき楼門・回廊・男坂の前を塀が塞いだ)。
    #    u>0 の頂点 = 回廊の前の辺。そこを落とし、南北の隅を直線で継ぐ。
    n = len(uv)
    drop = [i for i in range(n) if uv[i][0] > 0.0]
    # ⚠ **落とした区間を弦で結んではならない** — 回廊の後ろに南北32間の塀が立ってしまう
    #   (2026-08-24 検図 高-3 の後始末)。落とした先頭から始まる**開いた折れ線**にする。
    start = (drop[-1] + 1) % n if drop else 0
    pts = [off[(start + i) % n] for i in range(n) if uv[(start + i) % n][0] <= 0.0]
    # 開口 ── 平場の縁に取り付く石段の頭と、勝手口
    gaps = []
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        for q in ((k.get("pts") or [k["a"], k["b"]])[0], (k.get("pts") or [k["a"], k["b"]])[-1]):
            if _near_poly(q, pts, 2.0):
                gaps.append([round(q[0], 3), round(q[1], 3), round(kaidan_wken(d, k) / 2.0 + 0.2, 3)])
    for gt in d["gates"]:
        if _near_poly([gt["u"], gt["v"]], pts, 2.0):
            gaps.append([gt["u"], gt["v"], round(gt["plan"]["du"] / 2.0 + 0.3, 3)])
    # 開口の芯は**塀の線の上へ落とす** — 平場の縁に立つ門・石段は塀より 0.25間 外にあるので、
    #   芯のままでは半幅が届かず開口が切れない(2026-08-24 検図 高-1 の後始末)
    gaps = [[round(q[0], 3), round(q[1], 3), hw] for q, hw in
            ((_proj_poly(gq[:2], pts), gq[2]) for gq in gaps)]
    # ⛔ **他の囲いへ犬走りより近く並走する区間には柵を回さない**【検図11巡目 高1 → 2026-09-07】。
    #    平場の南西の縁は社殿を囲う透塀のすぐ外を通るので、輪郭を `ins` だけ内へ寄せた線が
    #    透塀と 0.15 m まで寄り、**二本の囲いの間に人の通れない溝**が残る。
    #    ⛔ 輪郭を南へ出して犬走りを取らない — 造成の量が動き、面を動かさないという裁定に触れる。
    #    ⭕ **回廊の前の東側と同じ作法**で、その区間だけ柵を回さない(⛔ 弦で結ばない)。
    #    ⛔ 区間を数で持たない — **節点間の区間ごとに他の囲いとの離れを測って決める従属値**。
    #    ⛔ **区間を「節点から節点まで」で落とさない** — 隅で一点だけ寄る辺まで丸ごと消える。
    #    ⭕ **近い所だけを落とす**(0.01 間で歩き、`ins` を割る連続した範囲をそのまま口にする)。
    osegs = [s for q in d["runs"] if q["name"] != "Ita_Keidai" for s in run_segs(q)]
    skips = []
    for i in range(len(pts) - 1):
        a, b_ = pts[i], pts[i + 1]
        L = math.hypot(b_[0] - a[0], b_[1] - a[1])
        if L < 1e-9: continue
        n = max(2, int(L / 0.01))
        at = lambda t: (a[0] + (b_[0] - a[0]) * t, a[1] + (b_[1] - a[1]) * t)
        #    ⛔ **点で測らない** — 相手の端が柵の線の脇に来る所は点どうしでは拾えない。
        #    刻みの小片と相手の区間の**線分どうしの距離**で測り、口は前後へ一刻み広げる
        #    (⛔ 口の縁ぎりぎりに 0.44 m の切れ端を残さない)。
        near = [min(_seg_seg_dist(at(j / float(n)), at((j + 1) / float(n)), c, e)
                    for c, e in osegs) < ins - 1e-9 for j in range(n)]
        j = 0
        while j < n:
            if not near[j]: j += 1; continue
            k = j
            while k + 1 < n and near[k + 1]: k += 1
            j0, k1 = max(0, j - 1), min(n, k + 2)
            cm = at((j0 + k1) / 2.0 / n)
            skips.append([cm[0], cm[1], L * (k1 - j0) / 2.0 / n])
            j = k + 1
    by["Ita_Keidai"]["pts"] = [[round(u, 3), round(v, 3)] for u, v in pts]
    by["Ita_Keidai"]["gaps"] = gaps + skips
    by["Ita_Keidai"]["skips"] = skips
    by["Ita_Keidai"].pop("gapU", None); by["Ita_Keidai"].pop("gapHalf", None)
    by["Ita_Keidai"]["_"] = ("境内の外周の**腰高の柵**【U ユーザー裁定 2026-09-07】。"
                             "**平場の輪郭から犬走り(`const.inubashiri`)ぶん内へ寄せて機械生成する** — "
                             "独立の座標を持たない(2026-08-23 検図 中-5)。"
                             "⚠ **回廊の基壇が東front なので東の張り出しには回さない**。"
                             "**開口は石段の頭と勝手口で自動に開く**(2026-08-24 検図 高-1)。"
                             "⚠ **他の囲いへ犬走りより近く並走する区間には回さない**"
                             "(南西の透塀の外・検図11巡目 高1)")


def derive_routes(d):
    """`from` を持つ動線の折れ線を、名指した道 + `tail` から**その場で組み立てる**。

    ⛔ 同じ座標を二重に持たない(規則4)。賄の動線は `kattemichi[西の勝手道]` そのものだったのに、
    json が同じ 28 点を写しており、勝手道を直しても動線が古いまま残る形だった
    (2026-09-06 検図4巡目 高1)。
    """
    src = {"kattemichi": dict((q["name"], q) for q in d.get("kattemichi", [])),
           "fumotomichi": dict((q["name"], q) for q in d.get("fumotomichi", []))}
    for rt in d.get("routes", []):
        if not rt.get("from"): continue
        kind, _, nm = rt["from"].partition(":")
        base = src.get(kind, {}).get(nm)
        if base is None:
            raise SystemExit("動線『%s』の from が引けない: %s" % (rt["name"], rt["from"]))
        te = rt.get("tailEndFrom")
        if te and rt.get("tail"):
            # ⭐ 末尾 = 棟の面の外 `offKen`(庭方 2026-09-15)── ⛔ 世界座標の数を手で持たない
            mm = next((q for q in d["munes"] if q["name"] == te["mune"]), None)
            if mm is None:
                raise SystemExit("動線『%s』の `tailEndFrom` の棟『%s』が無い" % (rt["name"], te["mune"]))
            kd = d["grid"]["keidai"]; ken = d["const"]["ken"]
            off = float(te.get("offKen") or 0.0)
            ax, val = {"南面": (1, mm["v0"] - off), "北面": (1, mm["v0"] + mm["dv"] + off),
                       "西面": (0, mm["u0"] - off), "東面": (0, mm["u0"] + mm["du"] + off)}[te["face"]]
            rt["tail"][-1][ax] = round((kd["z0"] if ax == 1 else kd["x0"]) + val * ken, 3)
        rt["pts"] = [list(q) for q in base["pts"]] + [list(q) for q in rt.get("tail", [])]
        # 折返しの宣言も引き継ぐ(`tail` は末尾に継ぐので頂点の番号は変わらない)
        rt["switchbacks"] = list(base.get("switchbacks", []))


AMAOCHI_MIN_KEN = 0.25   # 帯の切れ端を落とす下限[間] ── ⛔ 設計値ではない(隣の屋根を抜いた残り)


def derive_amaochi(d):
    """**雨落ち**(`amaochi`)の帯を `gardens` へ書き込む【庭方の設計 2026-09-19 ── K115(a)】。

    ⭐ **面を json に持たない**(規則4)── 帯は棟の**柱芯の矩形の四面の外**へ幅 `widthKen` を
      回した従属値で、置き方は既に在る `gardens[御供所の雨落ち・東/西]` と**同じ**。
    ⚠ **隣の屋根の下になる区間は抜く** ── 帯の芯線が別の棟の柱芯の矩形に入る区間を、長手方向の
      区間の引き算で落とす(残りが `AMAOCHI_MIN_KEN` に満たない切れ端は捨てる)。
    ⭕ **回廊は run** なので梁間 `bari` の半分の外へ両側に回す(`run_band_uv`)。
    ⛔ **軒の出をここで発明しない** ── 当図は棟ごとの軒の出を持たない
      (→ `_pending`「棟ごとの軒の出が図に無い」)。
    """
    am = d.get("amaochi")
    if not am: return
    if any(q.get("amaochi") for q in d["gardens"]): return      # ⭕ 二度呼ばれても増やさない
    w = float(am["widthKen"]); out = []
    R = [(m["name"], m["u0"], m["v0"], m["u0"] + m["du"], m["v0"] + m["dv"]) for m in d["munes"]]
    M = dict((m["name"], m) for m in d["munes"])

    def sub(seg, cuts):
        """区間 [a,b] から cuts の区間を引く。⛔ 新しい物差しではない(ただの引き算)。"""
        keep = [seg]
        for c0, c1 in cuts:
            nx = []
            for a, b in keep:
                if c1 <= a + 1e-9 or c0 >= b - 1e-9: nx.append((a, b)); continue
                if c0 > a + 1e-9: nx.append((a, min(b, c0)))
                if c1 < b - 1e-9: nx.append((max(a, c1), b))
            keep = nx
        return [q for q in keep if q[1] - q[0] >= AMAOCHI_MIN_KEN]

    for nm in am.get("roster") or []:
        if nm not in M: raise SystemExit("⛔ `amaochi.roster`『%s』が `munes` に無い" % nm)
        m = M[nm]
        u0, v0 = m["u0"], m["v0"]; u1, v1 = u0 + m["du"], v0 + m["dv"]
        for face in ("東面", "西面", "南面", "北面"):
            if face in ("東面", "西面"):
                a0, a1 = ((u1, u1 + w) if face == "東面" else (u0 - w, u0))
                uc = (a0 + a1) / 2.0
                cuts = [(q[2], q[4]) for q in R if q[0] != nm and q[1] - 1e-9 <= uc <= q[3] + 1e-9]
                # ⚠ **先に据えた帯とも重ねない**【2026-09-19】── 棟と棟の間が `widthKen` 以下だと
                #   両側の帯が同じ土地を取り合う。⭕ 一枚で済むので**先に据えたほうが持つ**
                #   (名簿の順が決める ── ⛔ 二枚重ねない)。
                cuts += [(q[3], q[5]) for q in out
                         if q[2] - 1e-9 <= uc <= q[4] + 1e-9]
                for b0, b1 in sub((v0, v1), cuts):
                    out.append((nm, face, a0, b0, a1, b1))
            else:
                a0, a1 = ((v1, v1 + w) if face == "北面" else (v0 - w, v0))
                vc = (a0 + a1) / 2.0
                cuts = [(q[1], q[3]) for q in R if q[0] != nm and q[2] - 1e-9 <= vc <= q[4] + 1e-9]
                cuts += [(q[2], q[4]) for q in out
                         if q[3] - 1e-9 <= vc <= q[5] + 1e-9]
                for b0, b1 in sub((u0, u1), cuts):
                    out.append((nm, face, b0, a0, b1, a1))
    for gd9 in out:
        nm, face, x0, y0, x1, y1 = gd9
        d["gardens"].append({
            "name": "%sの雨落ち・%s" % (nm, face[0]), "kind": am["kind"], "amaochi": True,
            "clip": am.get("clip"), "noPlant": True, "noTrees": True, "acc": am["acc"],
            "poly": [[round(x0, 4), round(y0, 4)], [round(x1, 4), round(y0, 4)],
                     [round(x1, 4), round(y1, 4)], [round(x0, 4), round(y1, 4)]],
            "_": "**雨落ち**(`amaochi` からの従属値)── 棟『%s』の%sの外へ幅 %g 間。"
                 "⛔ 数を json に持たない・⛔ 水尻を付けない(敷きなのでその場で浸む)" % (nm, face, w)})
    RN = dict((r["name"], r) for r in d["runs"])
    for rn in am.get("runs") or []:
        if rn not in RN: raise SystemExit("⛔ `amaochi.runs`『%s』が `runs` に無い" % rn)
        r = RN[rn]
        hw = float(r["bari"]) / 2.0
        Q0 = run_band_uv(r, hw); Q1 = run_band_uv(r, hw + w)
        for side, P9 in (("東", [Q1[0], Q1[1], Q0[1], Q0[0]]), ("西", [Q0[3], Q0[2], Q1[2], Q1[3]])):
            d["gardens"].append({
                "name": "%sの雨落ち・%s" % (rn, side), "kind": am["kind"], "amaochi": True,
                "clip": am.get("clip"), "noPlant": True, "noTrees": True, "acc": am["acc"],
                "poly": [[round(q[0], 4), round(q[1], 4)] for q in P9],
                "_": "**雨落ち**(`amaochi` からの従属値)── 回廊『%s』の梁間 %g 間の外へ幅 %g 間。"
                     "⛔ 数を json に持たない" % (rn, r["bari"], w)})


def derive_kaidan_tataki(d):
    """**石段の足の水叩き**の輪郭を書き込む【庭方の設計 2026-09-19 ── K115(b)】。

    ⚠ **`derive_gates` の後でなければ引けない** ── 起点の踏石(`afterFumiishi`)は門の芯からの
      従属値で、門の芯は `derive_gates` が入れる。⛔ `derive_garden_strips` に置かない。
    """
    # ⭐ **石段の足の水叩き**(`gardens[].polyFrom.kaidanFoot`)【庭方 2026-09-19 ── K115(b)】──
    #    坂は樋なので、足に水叩きを敷く。⛔ 数を json に持たない(坂の足が動けば追随する)。
    K9 = dict((k["name"], k) for k in d["kaidans"])
    for gd in d["gardens"]:
        pf = gd.get("polyFrom")
        if not (pf and pf.get("kaidanFoot")): continue
        k9 = K9.get(pf["kaidanFoot"])
        if k9 is None:
            raise SystemExit("『%s』の `polyFrom.kaidanFoot`『%s』が `kaidans` に無い"
                             % (gd["name"], pf["kaidanFoot"]))
        pts9 = [tuple(q) for q in (k9.get("pts") or [k9["a"], k9["b"]])]
        a9, b9 = pts9[-2], pts9[-1]                 # 足 = 末端の一区間(下端)
        L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1]) or 1.0
        ex9, ez9 = (b9[0] - a9[0]) / L9, (b9[1] - a9[1]) / L9
        ln9 = float(pf["lenKen"]); hw9 = float(pf["widthKen"]) / 2.0
        c0 = b9
        # ⭐ **門と踏石を跨がない**(`polyFrom.afterFumiishi`)【2026-09-19】── 坂の足は門の下で、
        #   その東には既に踏石が敷いてある。⛔ 玉石を門の柱間と踏石の上へ重ねない ⇒ 起点を
        #   **踏石の東の縁**へ送る(⛔ 数を持たない ── `fumiishi_rects` からの従属値)。
        if pf.get("afterFumiishi"):
            fr9 = [q for q in fumiishi_rects(d) if q[0] == pf["afterFumiishi"]]
            if not fr9:
                raise SystemExit("『%s』の `polyFrom.afterFumiishi`『%s』が踏石に無い"
                                 % (gd["name"], pf["afterFumiishi"]))
            c0 = (max(fr9[0][1], fr9[0][3]), b9[1])
        c1 = (c0[0] + ex9 * ln9, c0[1] + ez9 * ln9)
        nx9, nz9 = -ez9 * hw9, ex9 * hw9
        gd["poly"] = [[round(c0[0] + nx9, 4), round(c0[1] + nz9, 4)],
                      [round(c1[0] + nx9, 4), round(c1[1] + nz9, 4)],
                      [round(c1[0] - nx9, 4), round(c1[1] - nz9, 4)],
                      [round(c0[0] - nx9, 4), round(c0[1] - nz9, 4)]]


def derive_garden_strips(d):
    """**棟・渡廊下に沿う帯**(`gardens[].stripFrom`)の輪郭を書き込む【庭方 2026-09-15】。
    ⛔ 数を json に持たない ── 棟の柱芯の矩形の辺・渡廊下の芯と幅からの従属値。"""
    derive_amaochi(d)          # ⭐ 雨落ちの帯(庭方 2026-09-19)── ⛔ 面を json に持たない
    M = dict((m["name"], m) for m in d["munes"])
    L = dict((q["name"], q) for q in d.get("links", []))

    def fv(m, face, off=0.0):
        return {"南面": m["v0"] - off, "北面": m["v0"] + m["dv"] + off,
                "西面": m["u0"] - off, "東面": m["u0"] + m["du"] + off}[face]
    for gd in d["gardens"]:
        sf = gd.get("stripFrom")
        if not sf: continue
        w = float(sf["widthKen"])
        if sf.get("mune"):
            m = M[sf["mune"]]
            sp = sf.get("span") or {}
            if sf["face"] in ("東面", "西面"):
                u0, u1 = ((fv(m, "東面"), fv(m, "東面") + w) if sf["face"] == "東面" else (fv(m, "西面") - w, fv(m, "西面")))
                v0 = fv(m, sp.get("from", "南面")) + float(sp.get("fromOffKen") or 0.0)
                v1 = fv(m, sp.get("to", "北面"))
            else:
                v0, v1 = ((fv(m, "北面"), fv(m, "北面") + w) if sf["face"] == "北面" else (fv(m, "南面") - w, fv(m, "南面")))
                u0, u1 = fv(m, sp.get("from", "西面")), fv(m, sp.get("to", "東面"))
        else:
            lk = L[sf["link"]]
            c = float(lk["from"][0]); hw = float(lk["w"]) / 2.0
            u0, u1 = ((c + hw, c + hw + w) if sf["side"] == "東" else (c - hw - w, c - hw))
            mf = sf["fromMuneFace"]
            v0 = fv(M[mf["mune"]], mf["face"], float(mf.get("offKen") or 0.0))
            v1 = float(lk["to"][1])
        gd["poly"] = [[round(u0, 4), round(v0, 4)], [round(u1, 4), round(v0, 4)],
                      [round(u1, 4), round(v1, 4)], [round(u0, 4), round(v1, 4)]]
    for dr in d.get("drains", []):
        vf = dr["vFrom"]
        dr["v"] = round(fv(M[vf["mune"]], vf["face"], float(vf.get("offKen") or 0.0)), 4)
    D = dict((q["name"], q) for q in d.get("drains", []))
    te = terrace_poly_uv(d["terraces"][0])
    for gd in d["gardens"]:
        cf = gd.get("chuteFrom")
        if not cf: continue
        dr = D[cf["drain"]]
        v = dr["v"]; ou = dr["outlet"]["u"]
        # ⭐ 上端 = 平場の縁と溝の通りの交点のうち、吐口の西で最も近い点(⛔ 数を持たない)
        xs = []
        for i in range(len(te)):
            a, c = te[i], te[(i + 1) % len(te)]
            if (a[1] - v) * (c[1] - v) <= 0 and abs(c[1] - a[1]) > 1e-12:
                xs.append(a[0] + (v - a[1]) * (c[0] - a[0]) / (c[1] - a[1]))
        xs = [x for x in xs if x <= ou + 1e-6]
        if not xs:
            raise SystemExit("『%s』── 平場の縁が溝の通り v %.3f で吐口の西に無い" % (gd["name"], v))
        u0 = max(xs); hw = float(cf["widthKen"]) / 2.0
        # ⭐ **下端 = 法尻**(`chuteFrom.uToFrom` ── ⛔ 数を持たない)【検図1巡目 高 → 2026-09-16】。
        #    ⚠ 旧版は数(-34.30)を持ち、上端の高さを**造成前の地盤**で刷っていた(実際は平場の設計面)。
        #    据え石と水叩きが法面の途中に乗る図になっていた。
        u1, y0, y1 = chute_toe(d, gd, u0, v)
        gd["poly"] = [[round(u1, 4), round(v - hw, 4)], [round(u0, 4), round(v - hw, 4)],
                      [round(u0, 4), round(v + hw, 4)], [round(u1, 4), round(v + hw, 4)]]
        if gd.get("sueishi"):
            gd["sueishi"]["uv"] = [round(u1, 4), round(v, 4)]
    # ⭐ **水叩きは張り石の下端(法尻)からの従属値**(`gardens[].polyFrom.chute`)── ⛔ 数を持たない
    for gd in d["gardens"]:
        pf = gd.get("polyFrom")
        if not (pf and pf.get("chute")): continue
        src = next((q for q in d["gardens"] if q["name"] == pf["chute"]), None)
        if src is None or not src.get("poly"):
            raise SystemExit("『%s』の `polyFrom.chute`『%s』が引けない" % (gd["name"], pf["chute"]))
        us = [q[0] for q in src["poly"]]; vs = [q[1] for q in src["poly"]]
        ut = min(us); vc = (min(vs) + max(vs)) / 2.0
        ln = float(pf["lenKen"]); hw = float(pf["widthKen"]) / 2.0
        gd["poly"] = [[round(ut - ln, 4), round(vc - hw, 4)], [round(ut, 4), round(vc - hw, 4)],
                      [round(ut, 4), round(vc + hw, 4)], [round(ut - ln, 4), round(vc + hw, 4)]]


# 法尻を解く刻み[間]。⛔ 設計値ではなく解の刻み(0.005 間 = 9 mm)。
CHUTE_STEP_KEN = 0.005


def chute_toe(d, gd, u0, v):
    """張り石の**法尻**[間]と、上端・下端の高さ[m]。(u1, 上端の設計面, 法尻の地盤)。

    ⭐ **上端は平場の設計面**(`terraces[].y`)であって造成前の地盤ではない【検図1巡目 高 → 2026-09-16】。
    縁から西へ `const.batterFill` の法面を下ろし、**造成前の地盤に当たった点**が法尻。
    ⚠ 地盤も西へ下るので「1.5 × 縁の落差」では届かない(当図で 0.30 m 足りなかった)。
    ⛔ 法尻を数で持たない ── 地盤か面の高さが動けば法尻も動く。
    """
    g = G(d)
    ken = d["const"]["ken"]
    bf = float(d["const"]["batterFill"])
    y0 = float(d["terraces"][0]["y"])
    n = int(round(12.0 / CHUTE_STEP_KEN))
    for i in range(1, n + 1):
        uu = u0 - i * CHUTE_STEP_KEN
        hh = dem_h(*g.W(uu, v))
        if hh is None:
            raise SystemExit("『%s』── 法尻を解く途中で造成前の地盤が引けない(u %.3f)" % (gd["name"], uu))
        if y0 - (u0 - uu) * ken / bf <= hh + 1e-9:
            return uu, y0, hh
    raise SystemExit("『%s』── 縁から %.1f 間 西まで法面が造成前の地盤に当たらない" % (gd["name"], n * CHUTE_STEP_KEN))


def kakoi_segs(d, gd):
    """囲い(`gardens[].kakoi`)の立つ区間[uv]── 矩形の四辺から口(`gate`: 辺・端・幅[間])を抜く。"""
    P = garden_poly(gd)
    us = [q[0] for q in P]; vs = [q[1] for q in P]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    E = {"南": ((u0, v0), (u1, v0)), "東": ((u1, v0), (u1, v1)), "北": ((u1, v1), (u0, v1)), "西": ((u0, v1), (u0, v0))}
    gt = (gd.get("kakoi") or {}).get("gate") or {}
    out = []
    for nm, (a, b) in E.items():
        if nm != gt.get("edge"):
            out.append((a, b)); continue
        w = float(gt["wKen"])
        if nm == "南":
            out.append(((u0, v0), (u1 - w, v0)) if gt.get("end") == "東" else ((u0 + w, v0), (u1, v0)))
        elif nm == "北":
            out.append(((u1, v1), (u0 + w, v1)) if gt.get("end") == "西" else ((u1 - w, v1), (u0, v1)))
        elif nm == "東":
            out.append(((u1, v0), (u1, v1 - w)) if gt.get("end") == "北" else ((u1, v0 + w), (u1, v1)))
        else:
            out.append(((u0, v1), (u0, v0 + w)) if gt.get("end") == "南" else ((u0, v1 - w), (u0, v0)))
    return out


def garden_holes(d, gd):
    """砂利敷から抜く面(`gardens[].holesFrom`)の多角形の列[uv]。棟 = 柱芯の矩形 + `offKen`・石段 = 敷きの帯。"""
    hf = gd.get("holesFrom")
    if not hf: return []
    out = []
    off = float(hf.get("offKen") or 0.0)
    for m in d["munes"]:
        if m["name"] not in (hf.get("munes") or []): continue
        out.append([(m["u0"] - off, m["v0"] - off), (m["u0"] + m["du"] + off, m["v0"] - off),
                    (m["u0"] + m["du"] + off, m["v0"] + m["dv"] + off), (m["u0"] - off, m["v0"] + m["dv"] + off)])
    for k in d["kaidans"]:
        if k["name"] not in (hf.get("kaidans") or []): continue
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        hw = kaidan_wken(d, k) / 2.0
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            L9 = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            nx, ny = -(b[1] - a[1]) / L9 * hw, (b[0] - a[0]) / L9 * hw
            out.append([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])
    return out


def route_fork(d, na, nb):
    """二本の動線が**分かれる最後の共有点**(二股)[世界座標]。無ければ None。

    ⚠ 二本は参道の階から二股まで重なり、中門から西でまた重なる(2本の共有区間がある)ので、
    「共有点」ではなく「**共有点のうち、次の点が食い違うもの**」で二股を同定する。
    """
    R = dict((rt["name"], rt) for rt in d.get("routes", []))
    a, b = R.get(na), R.get(nb)
    if not a or not b: return None
    PA = [tuple(q) for q in a["pts"]]
    PB = [tuple(q) for q in b["pts"]]
    for i, p in enumerate(PA[:-1]):
        if p not in PB: continue
        j = PB.index(p)
        if j + 1 >= len(PB): continue
        if PA[i + 1] != PB[j + 1]: return p
    return None


def gate_by_name(d, nm):
    """名で門を引く。⛔ 番号で指さない(門が増減した日に取り違える)。"""
    for gt in d["gates"]:
        if gt["name"] == nm: return gt
    raise SystemExit("門『%s』が無い" % nm)


def gate_face_u(d, nm, face):
    """門の**面の通り**[間] ── 芯 ± **梁間(通り抜けの奥行 `plan.du`)の半分**。⛔ 面の u を json に書き写さない。

    ⚠ 2026-09-07 検図7巡目 低4 — 門の芯を犬走りからの従属値に改めたのに、その**面の通り**は
    旧値 23.600 / 21.600 のまま4箇所に literal で残り、27.3 mm ずつずれていた。
    面に取り付く物(袖塀・帯の輪郭・動線の折れ点・断面の切断線・見所)は**すべてここから引く**。
    ⭐ **面は通り抜けの軸の上の面だけ**【K004 検図 2026-09-13】── 東西に抜ける門の東面/西面。
    ⛔ 南北に抜ける門の「東面」は桁行の側面で、奥行 du の半分では出ない ⇒ 止める(黙って東西で出さない)。
    """
    gt = gate_by_name(d, nm)
    if face not in ("東", "西") or not gate_face_is_pass(gt, face):
        raise SystemExit("門『%s』の面『%s』は通り抜けの軸の上の面でない — 奥行 du で面の通りを出せない(K004)"
                         % (nm, face))
    hu = gt["plan"]["du"] / 2.0
    return gt["u"] + (hu if face == "東" else -hu)


_FACE_VEC = {"東": (1.0, 0.0), "西": (-1.0, 0.0), "北": (0.0, 1.0), "南": (0.0, -1.0)}


def gate_pass_az(gt):
    """門の**通り抜けの軸の方位**[°・mod 180](真北から時計回り)。`front` が先、無ければ `pass`。
    宣言が無ければ None。⛔ 組み立て時の写し `passAz` を読まない ── 変異の図でもその場で出す。"""
    fr, ps = gt.get("front"), gt.get("pass")
    fd = gate_frame_deg(gt)
    if fr in _DIR_DEG: return (_DIR_DEG[fr] + fd) % 180.0
    if ps in _PASS_DEG: return (_PASS_DEG[ps] + fd) % 180.0
    return None


def gate_frame_deg(gt):
    """門が載る**回した枠**の角[°・上から見て時計回り]。`gates[].frame` が `grid.frames` を名指す。

    ⭐ 明治16年実測図の読み【A】── 回廊の東面(北翼・楼門・南翼)は一直線のまま傾く(2026-09-14)。
    ⛔ 角を門ごとに数で持たない ── `grid.frames[].deg` 一本。⛔ 名指したのに組み立て前で角が解けて
    いなければ止める(0 で埋めると回した門が黙って真東西へ戻る)。
    """
    if not gt.get("frame"): return 0.0
    if gt.get("frameDeg") is None:
        raise SystemExit("門『%s』の枠『%s』の角が解けていない(`derive_gate_yaw` の前に読んだ)"
                         % (gt["name"], gt["frame"]))
    return float(gt["frameDeg"])


def gate_axes_uv(gt):
    """(p, n) ── 通り抜けの単位ベクトル p と桁行の単位ベクトル n [uv](u=東・v=北)。

    ⭐ **奥行 `plan.du` は p、幅 `plan.dv` は n に取る**【K004 検図 2026-09-13】。
    ⛔ 向きが未宣言の門は、平面が正方形(du = dv)のときに限り東西とみなす(回しても形が同じ)。
       正方形でなければ止める ── 東西で埋めると南北に抜ける門で黙って崩れる。
    """
    az = gate_pass_az(gt)
    if az is None:
        pl = gt["plan"]
        if abs(pl["du"] - pl["dv"]) > 1e-9:
            raise SystemExit("門『%s』は通り抜けの向き(`front`/`pass`)が未宣言で平面が正方形でない — "
                             "奥行 du をどちらへ取るか決まらない(⛔ 東西で埋めない)" % gt["name"])
        az = 90.0
    a = math.radians(az)
    px, py = round(math.sin(a), 12) + 0.0, round(math.cos(a), 12) + 0.0
    return (px, py), (py, -px)


def gate_col_face_dist(d, gt, face):
    """門の芯から**幅の脇(桁行の側)の側柱の外面**までの距離[間]と、その向きの単位ベクトル[uv]。

    ⭐ 面 = 柱芯(`plan.dv`/2)+ 部材の側柱の半径 `bom[].axis.colRadiusM`【普請奉行の裁定 2026-09-14 案A】。
    ⛔ 半径の宣言が無ければ止める(0 で埋めると柱芯へ戻り、柱と礎盤が黙って囲いへ食い込む)。
    ⛔ 通り抜けの軸の上の面(`gate_face_u` の側)をここで出さない。
    """
    b = gate_bom_row(d, gt)
    rad = ((b or {}).get("axis") or {}).get("colRadiusM")
    if rad is None:
        raise SystemExit("門『%s』の部材に側柱の半径 `axis.colRadiusM` の宣言が無い — 側柱の外面を出せない" % gt["name"])
    p, n = gate_axes_uv(gt)
    fv = _FACE_VEC.get(face)
    if fv is None or abs(fv[0] * n[0] + fv[1] * n[1]) < 0.99:
        raise SystemExit("門『%s』の面『%s』は幅の脇(桁行の側)の面でない — 側柱の外面を出せない" % (gt["name"], face))
    sg = 1.0 if fv[0] * n[0] + fv[1] * n[1] > 0 else -1.0
    return gt["plan"]["dv"] / 2.0 + float(rad) / d["const"]["ken"], (sg * n[0], sg * n[1])


def gate_col_face_end(d, r, ef):
    """run `r` の端 `ef.end` を、門 `ef.gate` の `ef.face` の側柱の外面の通りと run の線の交点へ[uv]。"""
    gt = gate_by_name(d, ef["gate"])
    dist, m = gate_col_face_dist(d, gt, ef["face"])
    A, B = r["a"], r["b"]
    dx, dy = B[0] - A[0], B[1] - A[1]
    den = dx * m[0] + dy * m[1]
    if abs(den) < 1e-9:
        raise SystemExit("run『%s』の線が門『%s』の%sの側柱の外面と平行 — 端を面へ出せない" % (r["name"], gt["name"], ef["face"]))
    t = ((gt["u"] + dist * m[0] - A[0]) * m[0] + (gt["v"] + dist * m[1] - A[1]) * m[1]) / den
    return [A[0] + dx * t, A[1] + dy * t]


def gate_local(gt, q):
    """点 q[uv] を門の軸の座標 (s = 通り抜けの向き, t = 桁行の向き)[間] へ。"""
    p, n = gate_axes_uv(gt)
    x, y = q[0] - gt["u"], q[1] - gt["v"]
    return (x * p[0] + y * p[1], x * n[0] + y * n[1])


def gate_rect_uv(gt):
    """門の平面の4隅[uv] ── **奥行 du を通り抜けの軸へ回す**(K004)。反時計回りにそろえて返す。"""
    p, n = gate_axes_uv(gt)
    hu, hv = gt["plan"]["du"] / 2.0, gt["plan"]["dv"] / 2.0
    c = (gt["u"], gt["v"])
    R = [(c[0] + sp * hu * p[0] + sn * hv * n[0], c[1] + sp * hu * p[1] + sn * hv * n[1])
         for sp, sn in ((-1, 1), (1, 1), (1, -1), (-1, -1))]
    ar = sum(R[i][0] * R[(i + 1) % 4][1] - R[(i + 1) % 4][0] * R[i][1] for i in range(4))
    return R if ar > 0 else R[::-1]


def gate_half_uv(gt):
    """門の平面(軸へ回したもの)の**外接矩形の半幅** (hu 東西, hv 南北)[間]。"""
    R = gate_rect_uv(gt)
    return (max(q[0] for q in R) - gt["u"], max(q[1] for q in R) - gt["v"])


def gate_face_is_pass(gt, face):
    """面の語 `face`(東/西/北/南)が**通り抜けの軸の上の面**か。向きが未宣言なら False。"""
    if face not in _FACE_VEC or gate_pass_az(gt) is None: return False
    p, _n = gate_axes_uv(gt)
    f = _FACE_VEC[face]
    return abs(abs(f[0] * p[0] + f[1] * p[1]) - 1.0) < 1e-9


# 部材のローカル軸 → 真北からの角[°](Unity の Y 回転 0 のとき。+Z=北 / +X=東)。⛔ 設計値ではない — 語の辞書
_LOCAL_AX_DEG = {"+Z": 0.0, "+X": 90.0, "-Z": 180.0, "-X": 270.0, "Z": 0.0, "X": 90.0}


_PASS_DEG = {"南北": 0.0, "東西": 90.0}


def gate_bom_row(d, gt):
    """門の `bom` が指す部材の行(無ければ None)。"""
    nm = gt.get("bom")
    if not nm: return None
    for b in d["bom"]:
        if b.get("部材") == nm: return b
    return None


def derive_gate_yaw(d):
    """**門の yaw は従属値**【検図 2026-09-13 高1・高2/考証 高2】── `front`(無ければ `pass`)と
    `bom[].axis`(部材のローカル軸)から出す。⛔ 数を json に持たない(`_gates`)。

    物差しは Unity の Y 回転[°](上から見て時計回り)。回転 θ はローカルの向きの方位角に θ を足す
    ⇒ θ = 正面の方位 − 部材の正面のローカル方位。正面が無い門は通り抜けの軸だけ合わせる(mod 180)。
    ⛔ 部材の軸が無い門は yaw を出さない(0 で埋めない)。`passAz` = 通り抜けの軸の方位[°](mod 180)。
    """
    frames = (d.get("grid") or {}).get("frames") or {}
    for gt in d["gates"]:
        gt["yaw"], gt["passAz"], gt["yawFrom"] = None, None, None
        if gt.get("frame"):
            fm = frames.get(gt["frame"])
            if fm is None or not isinstance(fm.get("deg"), (int, float)):
                raise SystemExit("門『%s』の `frame`『%s』が `grid.frames` に無い(角 `deg` が引けない)"
                                 % (gt["name"], gt["frame"]))
            gt["frameDeg"] = float(fm["deg"])
        else:
            gt.pop("frameDeg", None)
        fd = gate_frame_deg(gt)
        fr, ps = gt.get("front"), gt.get("pass")
        if fr in _DIR_DEG:
            gt["passAz"] = (_DIR_DEG[fr] + fd) % 180.0
        elif ps in _PASS_DEG:
            gt["passAz"] = (_PASS_DEG[ps] + fd) % 180.0
        ax = (gate_bom_row(d, gt) or {}).get("axis") or {}
        if fr in _DIR_DEG and ax.get("front") in _LOCAL_AX_DEG:
            gt["yaw"] = round((_DIR_DEG[fr] + fd - _LOCAL_AX_DEG[ax["front"]]) % 360.0, 6)
            gt["yawFrom"] = "front=%s%s × bom.axis.front=%s" % (
                fr, (" + 枠『%s』%+.1f°" % (gt["frame"], fd)) if fd else "", ax["front"])
        elif gt["passAz"] is not None and ax.get("pass") in _LOCAL_AX_DEG:
            gt["yaw"] = round((gt["passAz"] - _LOCAL_AX_DEG[ax["pass"]]) % 180.0, 6)
            gt["yawFrom"] = "pass × bom.axis.pass=%s(正面は未宣言 — 軸だけ合わせる)" % ax["pass"]


SUKIBEI_ROW = "透塀(連子窓の塀)"


# ⭐ **等分の丸めの不感帯**[mm]【指図方 2026-09-18】── uv を四桁(0.0001 間 = 0.18 mm)で持つので、
#   節点の間の長さ自体がこの桁で揺れる。切り上げ(`ceil`)をそのまま当てると、丸め誤差だけで
#   一段上がった部材が生まれる(北の段 3.2000436 m ÷ 2 = 1600.02 mm → 1601 mm の部材が一点)。
#   ⛔ この不感帯は「隙間を許す」ためのものではない ── uv の刻みより細かく、辺ぜんたいでも 1 mm に
#   満たない(隅の取り合いの許容 `joints[].tol` の 1/50 以下)。
SPAN_EPS_MM = 0.05


def sukibei_span_plan(d):
    """**透塀のスパンの割り付け**【部材方 2026-09-14 / K085 の直し 2026-09-18】── 辺を run の側で
    **等分**する: 本数 = round(建つ長さ / 基準スパン)・スパン = 建つ長さ / 本数。⛔ 数を json に持たない。
    ⭐ **建つ長さ = 節点の間の長さ**(開口の分を除く)。⛔ **隅のぶんを引かない**
      ── スパン部材は端の型ごとに自分の中で帯を引き込んで焼いてあり、`n` / `t` / `c` / `h` の
      四つとも**割り付けの差し引きは 0**(`sukibei_kado_reach` ── 部材方の実測 2026-09-18)。
      2026-09-17 に入れた「隅の食い込みを引く」規則は二重の引き算で、誤りとして撤回した。
    端の種類(−X, +X — run の a → b の向き): n = 次のスパンへ続く / t = 中門へ突き付け / c = 隅部材へ続く /
    h = 潜りの口の縁の柱 / ? = 部材が決まっていない口。
    戻り [(run 名, 区間の名, 建つ長さ m, 本数, スパン mm, [端の種類…], 辺の頭 `a` からの走り m)]。
    ⭐ **走り `s0` は実装へ渡すために持つ**(K068)── 部材の据わりは「辺の頭から s0 + i×スパン」で
      決まり、⛔ これが無いと棟梁は図の本文から部材名を読み取るしかない。"""
    ken = d["const"]["ken"]
    row = next((b for b in d["bom"] if b.get("部材") == SUKIBEI_ROW), {}) or {}
    base = float(row.get("spanBaseM") or 2.54)
    out = []
    for r in d["runs"]:
        if r.get("kind") != "透塀": continue
        A, B = r["a"], r["b"]
        L = math.hypot(B[0] - A[0], B[1] - A[1]) * ken
        segs = [(0.0, L, "c", "c", "全長")]
        gv = r.get("gapV") if r.get("gapV") is not None else r.get("gapU")
        if gv is not None and r.get("gapHalf") is not None:
            j = 1 if r.get("gapV") is not None else 0
            sc = abs(gv - A[j]) * ken
            h = float(r["gapHalf"]) * ken
            eg = "t" if r.get("gapFrom") else (r.get("gapEnd") or "?")   # ⭐ 潜りの口の端(`gapEnd`・部材方 d2e9de85)
            segs = [(0.0, sc - h, "c", eg, "口の手前"), (sc + h, L, eg, "c", "口の先")]
        for s0, s1, e0, e1, nm in segs:
            ln = s1 - s0                       # ⛔ 隅のぶんを引かない(K085 ── 差し引きは 0)
            n = max(1, int(round(ln / base)))
            # ⭐ **mm の丸めはめり込む側へ**(規則『隙間は不可・めり込みは可』)── 切り捨てると
            #   本数ぶんの端数がそのまま**隙間**になる。切り上げなら重なりは高々 本数 × 1 mm
            # ⚠ **不感帯 0.05 mm**【指図方 2026-09-18】── uv は四桁(0.0001 間 = 0.18 mm)で持つので、
            #   切り上げが**丸め誤差だけで**一段上がる。北の段は 3.2000436 m ÷ 2 = 1600.02 mm となり、
            #   1601 mm の部材が一点だけ増えていた。0.05 mm は uv の刻みより細かく、辺ぜんたいでも
            #   1 mm に満たない(隅の取り合いの許容 `joints[].tol` の 1/50 以下)。
            mm = int(math.ceil(ln / n * 1000.0 - SPAN_EPS_MM))
            ends = [e0 + e1] if n == 1 else [e0 + "n"] + ["nn"] * (n - 2) + ["n" + e1]
            out.append((r["name"], nm, ln, n, mm, ends, s0))
    return out


# ---------------------------------------------------------------- 透塀の隅(凹凸は折れ線の従属値)
#   ⛔ **出隅/入隅を手で書かない**【K059 2026-09-16 棟梁の差し戻し】── 旧図は 8 隅のうち
#   **4 箇所で凹凸が折れ線と逆**だった(総数 出隅6・入隅2 は合っていたので数では鳴らない)。
#   棟梁は図を信じず折れ線の凹凸から測って据えた。⇒ 凹凸・隅柱のどちらの面・動かす側を
#   すべて折れ線からの従属値にして、同じ取り違えが二度と起きない形にする。
KADO_PART = {"出隅": "Dezumi", "入隅": "Irizumi"}


def sukibei_kado_plan(d):
    """**透塀の隅の凹凸**── 折れ線そのものから決める。⛔ json の宣言を読まない。

    隣り合う 2 run の向きの外積の符号を、**折れ線全体の回り(靴紐の符号)**と突き合わせて
    出隅(内角 < 180°)か入隅(> 180°)かを決める。並べ替えは端点の一致でつなぐので
    ⛔ json の並び順にも頼らない。戻り [(前の run, 次の run, 隅の uv, "出隅"/"入隅")]。
    """
    rs = [r for r in d["runs"] if r.get("kind") == "透塀" and r.get("a") and r.get("b")]
    if len(rs) < 3: return None
    def _k(p): return (round(p[0], 4), round(p[1], 4))
    chain = [rs[0]]
    used = {rs[0]["name"]}
    while len(chain) < len(rs):
        nx9 = [q for q in rs if q["name"] not in used and _k(q["a"]) == _k(chain[-1]["b"])]
        if len(nx9) != 1: return None                  # 数珠がつながらない(⛔ は検査が出す)
        chain.append(nx9[0]); used.add(nx9[0]["name"])
    if _k(chain[-1]["b"]) != _k(chain[0]["a"]): return None
    area2 = sum(chain[i]["a"][0] * chain[i]["b"][1] - chain[i]["b"][0] * chain[i]["a"][1]
                for i in range(len(chain)))
    sgn = 1.0 if area2 > 0 else -1.0
    out = []
    for i, r in enumerate(chain):
        n9 = chain[(i + 1) % len(chain)]
        ux, uz = r["b"][0] - r["a"][0], r["b"][1] - r["a"][1]
        vx, vz = n9["b"][0] - n9["a"][0], n9["b"][1] - n9["a"][1]
        cr = (ux * vz - uz * vx) * sgn
        if abs(cr) < 1e-9: continue                    # 折れていない(隅ではない)
        out.append((r, n9, list(r["b"]), "出隅" if cr > 0 else "入隅"))
    return out


def derive_sukibei_kado(d):
    """`joints[].kadoFrom` の行へ、折れ線から算出した `kind`/`bFace`/`moves` を書き込む。

    ⭐ **動かす側は短いほうの辺**(端数を短い辺で吸う。⛔ 中門を挟む東線=周長の拘束が効く辺は
      動かさない)── これも辺長からの従属値で、⛔ 手で書かない。
    ⚠ 長短は**節点の間の長さ**(`run_nodes_ken`)で較べる ── `run_len_ken` は口(中門・南の潜り)を
      引いた**建つ長さ**なので、口の大きい東線が「短い辺」に化けて動かす側が入れ替わる。
    """
    pl = sukibei_kado_plan(d) or []
    by = dict(((a["name"], b["name"]), (a, b, uv, t)) for a, b, uv, t in pl)
    for j in d.get("joints", []):
        kf = j.get("kadoFrom")
        if not kf: continue
        # ⛔ **手で書いた凹凸を黙って上書きしない** ── 書いてあったことを残して検査が⛔で拾う
        j["_byHand"] = [q9 for q9 in ("kind", "bFace", "moves") if j.get(q9) is not None]
        q = by.get((kf.get("in"), kf.get("out")))
        if q is None: continue                          # 検査が⛔で拾う
        a9, b9, uv, t9 = q
        mv = a9 if run_nodes_ken(a9) <= run_nodes_ken(b9) else b9
        # ⭐ **この隅に向いている木口**(前の辺なら `b` の木口・次の辺なら `a` の木口)。
        #   ⚠ **これは端数の行き先ではない**【低5 検図23巡目 → 2026-09-17】── 端数は
        #   `sukibei_span_plan` が**二つの隅柱の面の間で等分し直して**吸う(⛔ 木口へ寄せ集めない)。
        #   旧版は `moves` が「この木口で吸う」・`absorb` が「等分し直す」と二つの事を言っており、
        #   実装がどちらを読むか決まらなかった ⇒ ⭕ **等分し直す側へ一本化**し、木口は寄せ先の面としてだけ名乗る。
        #   ⚠ 上限(丸めの端数が隅部材へめり込む量)は同じ取り合いの `tol`(めり込み可・隙間不可)。
        end9 = "b" if mv is a9 else "a"
        tol9 = (j.get("tol") or [0.05, 0.0])
        j["kind"] = "突き付け(%sの%s)" % (kf.get("name", ""), t9)
        j["bFace"] = ("隅部材(%s ── %s)の脚の木口。帯ごとに ①軸部(土台・腰板・連子・小壁)= **隅柱の側面** "
                      "②軒・屋根 = **隅部材の軒の端** ③基壇 = **隅の石敷の縁**"
                      "(到達は `bom[透塀].kadoLegM` ── ⛔ 外形 `kadoOutlineM` の最大は**外の角の隅棟**で"
                      "脚の到達ではない ／ スパンの側の引き込みは `bom[透塀].endSeatM.c`)。⭐ 据える当たりは"
                      "**隅柱の芯**(= 折れ線の節点・隅部材のピボット `bom[透塀].axis.kadoPivot`)で、"
                      "スパン部材の `c` の端は帯ごとのこの引き込みを**自分の中に焼き込んである**"
                      "(`Tools/Blender/build_sanno_sukibei.py` の `build_span`)⇒ ⛔ **辺長から隅のぶんを"
                      "引かない**(差し引き 0 ── K085 の直し 2026-09-18)"
                      % (KADO_PART[t9], t9))
        j["moves"] = ("透塀(%s ── 短い側の辺が動く。この隅では `%s` の木口を上の面へ寄せ、"
                      "端数は辺の全長(**据えた隅部材のピボット = 隅柱の芯の間**)を"
                      "**スパンごと等分し直して**吸う／めり込みの上限 %.2f m・隙間 %.2f m)"
                      % (mv["name"], end9, tol9[0], tol9[1]))
        j["kado"] = t9
        j["absorb"] = {"run": mv["name"], "end": end9, "rule": "等分し直す", "limitM": tol9,
                       "_": "**端数の始末**【算出 — 低2/低5 検図23巡目 2026-09-17】。⛔ 手で書かない。"
                            "⭐ **端数は木口へ寄せ集めない** ── 動かす側の辺(`run`)を**二つの隅柱の"
                            "芯(= 折れ線の節点)の間でスパンごと等分し直す**(`bom[透塀].手当` の等分の作法"
                            "そのもの。割り付けは `sukibei_span_plan` ── ⛔ 隅のぶんを引かない・差し引き 0)。"
                            "⚠ `end` は**この隅で寄せる木口**(寄せ先は `bFace`)であって、⛔ 端数の"
                            "行き先ではない。`limitM` は等分の丸めが隅部材へめり込んでよい量 = `tol`"}
    return pl


def sukibei_kado_seat(d, a9, b9, uv, t9):
    """**隅部材の据え方**(部材名・向き・据える責め)【中 検図2巡目 2026-09-18 → 規則19】。

    ⛔ **凹凸だけ渡して向きを渡さない、をしない** ── 旧版の焼き出しは `{at,with,type,part,world}`
      だけで、⛔ FBX の名も yaw も無く、同じ隅が両方の run に載って**据える責めが決まらなかった**
      (二重に据える口 ── K062/K089 の再発口)。
    ⭐ 向きは**部材の脚の向きの宣言**(`bom[透塀].kadoLegDir` ── 部材方の実測)と折れ線から解く。
      ⛔ 生成器に脚の向きを焼き込まない(部材を焼き直せば宣言が動く)。
    ⭐ **据える責めは一つ**(`owner`)── 隅へ**入ってくる辺**(`at == "b"` の側)が据え、
      出ていく辺は同じ隅を `owner:false` で持つ(取り合いの相手として読むため ── ⛔ 消さない)。
    戻り dict(`fbx` / `asset` / `yawDeg` / `legM` / `owner`…)。⛔ 向きが解けなければ `yawDeg` は None。
    """
    row = next((b for b in d["bom"] if b.get("部材") == SUKIBEI_ROW), {}) or {}
    dirs = (row.get("kadoLegDir") or {}).get(t9)
    ref = int(round(float(row.get("spanBaseM") or 0.0) * 1000.0))
    yaw, how = None, None
    if dirs and len(dirs) == 2 and all(q in _LOCAL_AX_DEG for q in dirs):
        want = (_LOCAL_AX_DEG[dirs[1]] - _LOCAL_AX_DEG[dirs[0]]) % 360.0
        dA = _azim(a9["a"][0] - uv[0], a9["a"][1] - uv[1])       # 入ってくる辺のほうへ
        dB = _azim(b9["b"][0] - uv[0], b9["b"][1] - uv[1])       # 出ていく辺のほうへ
        for p9, q9, nm9 in ((dA, dB, a9["name"]), (dB, dA, b9["name"])):
            if abs(((q9 - p9) % 360.0) - want) < 1e-6:
                yaw = round((p9 - _LOCAL_AX_DEG[dirs[0]]) % 360.0, 6)
                how = ("脚 %s を『%s』の向き(方位 %.1f°)へ・脚 %s を残りの辺へ"
                       % (dirs[0], nm9, p9, dirs[1]))
                break
    return {"fbx": ("Sanno_Sukibei_Kado_%s_%d.fbx" % (KADO_PART[t9], ref)) if ref else None,
            "asset": ('EdoAssets.Own.SannoSukibeiKado("%s", %d)' % (KADO_PART[t9], ref)) if ref else None,
            "yawDeg": yaw, "yawFrom": how, "legDir": dirs,
            "legM": row.get("kadoLegM"), "pivot": (row.get("axis") or {}).get("kadoPivot")}


def derive_gates(d, g):
    """門の芯と、**その面に取り付く物の通り**を組み立てる。⛔ 面の u を二重に持たない。

    ⭐ `gates[].uFrom` ── 門の芯そのものを平場の縁と犬走りからの従属値にする
    (⛔ 丸めた芯を置くと犬走りが 0.03 mm 足りない)。
    ⭐ `runs[].uFrom` / `gardens[].polyFrom` / `routes[].uFrom` / `sections[].atFrom` /
       `viewpoints[].uFrom` ── どれも門の面の通りを引く宣言。
    """
    ken = d["const"]["ken"]
    derive_gate_yaw(d)
    for gt in d["gates"]:
        uf = gt.get("uFrom")
        if not uf: continue
        te = [t for t in d["terraces"] if t["name"] == uf["terrace"]][0]
        us = [q[0] for q in terrace_poly_uv(te)]
        edge = min(us) if uf["side"] == "西" else max(us)
        cl = ((d["planting"]["clearance"] or {}).get(uf["clearanceOf"]) or {})[uf["clearance"]]
        if not gate_face_is_pass(gt, uf["face"]):
            raise SystemExit("門『%s』の `uFrom.face`『%s』が通り抜けの軸の上の面でない — 奥行 du で芯を出せない"
                             "(K004)" % (gt["name"], uf["face"]))
        hu = gt["plan"]["du"] / 2.0
        gt["u"] = edge + (cl / ken + hu if uf["face"] == "西" else -cl / ken - hu)

    def face_u(o):
        return gate_face_u(d, o["gate"], o["face"])

    for r in d["runs"]:
        uf = r.get("uFrom")
        if not uf: continue
        r["a"][0] = r["b"][0] = face_u(uf)
    for r in d["runs"]:
        ef = r.get("endFrom")
        if not ef or not ef.get("gate"): continue
        if ef.get("fromCentre"):
            # ⭐ **門の芯を通る線の上の run**(回廊の東面が楼門の芯を通る一直線 — 明治16年実測図【A】)。
            #    端 = 芯 + 外向き × 側柱の外面までの距離。⛔ json の a/b の向きを読まない。
            gt9 = gate_by_name(d, ef["gate"])
            dist, m = gate_col_face_dist(d, gt9, ef["face"])
            r[ef["end"]] = [gt9["u"] + m[0] * dist, gt9["v"] + m[1] * dist]
            r["_outward"] = [m[0], m[1]]
        else:
            r[ef["end"]] = gate_col_face_end(d, r, ef)
    by9 = {q["name"]: q for q in d["runs"]}
    for r in d["runs"]:
        ef = r.get("endFrom")
        if not ef or not ef.get("run"): continue
        # ⭐ **run の端から継ぐ**(回廊の翼の妻 ≡ 袖塀の先の木口 — 2026-09-14)。向きは相手の run の向き。
        q = by9.get(ef["run"])
        if q is None or q.get("_outward") is None:
            raise SystemExit("run『%s』の `endFrom.run`『%s』が引けない(門から出した run でない)" % (r["name"], ef["run"]))
        r[ef["end"]] = list(q[ef["runEnd"]])
        r["_outward"] = list(q["_outward"])
    for r in d["runs"]:
        ef = r.get("endFrom")
        if not ef or not r.get("farByKen"): continue
        if r.get("_outward") is None or not r.get("ken"):
            raise SystemExit("run『%s』の `farByKen` に向きか長さ `ken` が無い" % r["name"])
        far = "b" if ef["end"] == "a" else "a"
        m = r["_outward"]
        r[far] = [r[ef["end"]][0] + m[0] * float(r["ken"]), r[ef["end"]][1] + m[1] * float(r["ken"])]
    for gd in d["gardens"]:
        pf = gd.get("polyFrom")
        if not pf: continue
        for fc in ("東", "西"):
            for i in pf.get(fc, []):
                gd["poly"][i][0] = gate_face_u(d, pf["gate"], fc)
    for rt in d.get("routes", []):
        uf = rt.get("uFrom")
        if not uf: continue
        for fc in ("東", "西"):
            for i in uf.get(fc, []):
                u = gate_face_u(d, uf["gate"], fc)
                v = g.V(rt["pts"][i][1]) if rt.get("world") else rt["pts"][i][1]
                rt["pts"][i][0] = g.W(u, v)[0] if rt.get("world") else u
    for sc in d.get("sections", []):
        af = sc.get("atFrom")
        if not af: continue
        x = g.W(face_u(af), 0.0)[0]
        sc["at"] = x
        for q in sc.get("line", []): q[0] = x
    for vp in d.get("viewpoints", []):
        uf = vp.get("uFrom")
        if not uf: continue
        vp["uv"][0] = face_u(uf)


def derive_zentei(d, g):
    """前庭の**従属値**をその場で組み立てる ── 木戸の芯の v・供待の北辺。

    ⛔ 丸めた値を json に持たない(2026-09-06 検図6巡目 低6/低13)。
    ・木戸の芯 = **縁台の塊の間の中央**(`tamagaki.kido.vFrom` が指す二基の向かい合う端の中央)
    ・供待の北辺 = **表参と御成の二股の点の通り**(`gardens[].northFrom`)
    """
    for gd in d.get("gardens", []):
        kd = ((gd.get("tamagaki") or {}).get("kido"))
        if kd and kd.get("vFrom"):
            vf = kd["vFrom"]
            pr = [p for p in d.get("props", []) if p["name"] == "縁台(床几)"]
            A = prop_rect_of(d, pr[0]["name"], vf["a"]) if pr else None
            B = prop_rect_of(d, pr[0]["name"], vf["b"]) if pr else None
            if A is None or B is None:
                raise SystemExit("木戸の `vFrom` が引けない: %s / %s" % (vf["a"], vf["b"]))
            end = {"北端": max, "南端": min}
            kd["uv"] = [kd["uv"][0],
                        (end[vf["aEnd"]](q[1] for q in A) + end[vf["bEnd"]](q[1] for q in B)) / 2.0]
        nf = gd.get("northFrom")
        if nf and nf.get("kind") == "routeFork":
            p = route_fork(d, nf["a"], nf["b"])
            if p is None:
                raise SystemExit("空地『%s』の `northFrom` の二股が引けない" % gd["name"])
            v = g.V(p[1])
            vs = [q[1] for q in gd["poly"]]
            mid = (min(vs) + max(vs)) / 2.0        # 北の辺 = 芯より北の頂点(⛔ 番号で指さない)
            for q in gd["poly"]:
                if q[1] > mid: q[1] = v


def _proj_poly(q, pts):
    """点を折れ線へ落とす。"""
    best, bp = 1e9, q
    for a, b in zip(pts, pts[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1.0
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / L2))
        p = [a[0] + dx * t, a[1] + dz * t]
        dd = math.hypot(q[0] - p[0], q[1] - p[1])
        if dd < best: best, bp = dd, p
    return bp


def _near_poly(q, pts, tol):
    """点が折れ線から tol[間] 以内にあるか。"""
    for a, b in zip(pts, pts[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1.0
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / L2))
        if math.hypot(q[0] - (a[0] + dx * t), q[1] - (a[1] + dz * t)) <= tol: return True
    return False


def terrace_poly_uv(te):
    """平場の輪郭を uv で返す。`uv`(境内)/`poly`(前庭)/矩形 の三形に対応。"""
    if te.get("uv"): return te["uv"]
    if te.get("poly"): return te["poly"]
    return [[te["u0"], te["v0"]], [te["u1"], te["v0"]],
            [te["u1"], te["v1"]], [te["u0"], te["v1"]]]


def terrace_poly(te, g):
    """段の平面。`poly`(uv)があればそれ、無ければ u0/v0/u1/v1 の矩形。2026-08-23 に前庭が多角形になった。"""
    if te.get("poly"):
        return [g.W(u, v) for u, v in te["poly"]]
    if te["kind"] == "rect":
        return [g.W(te["u0"], te["v0"]), g.W(te["u1"], te["v0"]),
                g.W(te["u1"], te["v1"]), g.W(te["u0"], te["v1"])]
    return [g.W(u, v) for u, v in te["uv"]]


def in_poly(pt, P):
    x, z = pt; c = False; j = len(P) - 1
    for i in range(len(P)):
        if (P[i][1] > z) != (P[j][1] > z) and \
           x < (P[j][0] - P[i][0]) * (z - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0]:
            c = not c
        j = i
    return c


# ---------------------------------------------------------------- 縁の法面 ── **一枚の土の面**
#   ⭐ **2026-09-19 ユーザー裁定 = 案A(庭方の設計)** ── 法面は「輪郭の一点ごとに外へ降ろす
#   **一本の ray**」ではなく、**盛土の縁から外へ広がる一枚の土の面**である:
#
#       設計面 = min( max( 現地形, 面の高さ − 距離 / `const.batterFill` ),
#                     面の高さ + 距離 / `const.batterCut` )
#
#   ── **距離は土留めを障害物とした測地距離**(壁の向こうへは回り込まない)。盛の円錐は**縁の
#   盛厚が +0.05 m を超える区間**から、切の円錐は **−0.05 m を下回る区間**からだけ出し、
#   **現地形に沈んだ所で止まる**。⛔ 1.5 / 1.0 は図が元から持つ `const.batterFill` /
#   `const.batterCut` で、⛔ 新しい勾配値は作らない。
#   ⛔ **捨てた三つ**(どれも『途中で法面を**横へ消す**』作法。⭕ **土の面は横に消せない** ──
#      この三つが段を立てていた):
#     ① `slope_lands` の二値判定 ── 着地するか否かで ray を丸ごと採否していた。隣り合う ray が
#        判定を跨ぐ所で法面が消え、一枡の崖が立った(現況 23 枡)
#     ② `on_wall` による ray の全消し ── 土留めが受ける縁の法面を消していた。壁区間と法面区間の
#        **継ぎ目**に段が立った(現況 4 枡・最大 1.95 m)
#     ③ `featherCap` 12 m の打ち切り ── 現地形へ着かない ray をそこで切っていた(現況 39 枡)
#   ⭕ 土留めは**消す物ではなく障害物**になった ── 測地距離が壁を回り込まないので壁の受ける区間に
#     円錐は入らず、**壁の端では盛土が回り込んで自然に薄れる**(継ぎ目が消える)。
#   ⚠ **リーチに設計値の上限は無い** ── `_CONE_GUARD_M` は走査域の**外枠**(暴走よけ)であって
#     設計値ではない。⛔ ここで法面が切れたら欠陥で、切れた節点数は検査が毎回刷る(規則19)。
_CONE_GUARD_M = 40.0     # 走査域の外枠[m] ── ⛔ 設計値ではない(⭕ 張らないことを検査が毎回刷る)


_CONE_SEED_M = 0.25      # 縁の標本の刻み[m] ── ⛔ 設計値ではない(円錐の頭を置く歩きの細かさ)


_CONE_SEED_R = 2.0       # 標本が種を置く半径[m] ── ⛔ 設計値ではない(格子へ頭を移すだけ)


# ⚠ **測地距離の例外はここ一つだけ**【検図 低 2026-09-19】── 面の広がり(`_prop`)は土留めを
#   障害物とした測地距離だが、**種を撒く最初の `_CONE_SEED_R` m だけは直線距離**である
#   (輪郭の標本から格子の節点へ頭を移すだけの手当て)。⇒ 壁の端や入隅では、理屈の上では
#   種が壁の向こう側の節点へ落ちうる。⛔ 宣言を『全部が測地』と読ませない。
#   ⭕ 直線が障害の節点に当たった回数は毎回測って刷る(`seedJump`)── ⚠ **上限の見積り**で、
#     格子 1 m では**壁のすぐ脇を通る種も数える** ⇒ ⛔ そのまま『壁を越えた種』と読ませない。
_CONE = {"key": None}


def cone_field(d, g):
    """**縁から外へ広がる土の面**を造成の格子(`IMPL_STEP`)へ解く【裁定 2026-09-19 = 案A】。

    戻り dict ── `h`(節点 → **補間に使う高さ**)/ `nat` / `graded`(造成する節点の集合)/
    `reach`(輪郭からの届きの最大[m])/ `guardN`(外枠に達した節点 ── ⭕ **0 が正**)/
    `blocked`(障害の節点数)/ `seedF` `seedC`(円錐の頭の数)/ `bbox`。

    ⭐ **障害は二つだけ** ── ① **土留めの胴**(`_wall_dist` ≤ `wallCollarM` ── ⛔ 新しい物差しを
      作らない)② **平場と石段**(土は面の中へは広がらない)。⛔ 障害は伝播を**迂回させる**
      のであって、⛔ 法面を消さない。
    ⭐ **補間に使う高さ**は、造成する節点では円錐の値、それ以外は**現地形**。平場の中の節点は
      **面の高さ**(⛔ ただしその節点の最寄りの縁を**土留めが受けている**なら現地形 ── 壁の外へ
      面の高さを引き出すと見付が埋まる・**〈造成の縁〉1** の⛔)。石段の帯は `_stair_y` が先に受け持つ
      ので、格子には**現地形**を置く(⛔ 段の踏面を法面の補間へ持ち出さない)。
    """
    if _CONE.get("key") == id(d): return _CONE["v"]
    S = IMPL_STEP
    bf = float(d["const"]["batterFill"]); bc = float(d["const"].get("batterCut", 1.0))
    wc = wall_collar_m(d) or 0.0
    polys = [(te, terrace_poly(te, g)) for te in d["terraces"]]
    xs = [p[0] for _t, P in polys for p in P]; zs = [p[1] for _t, P in polys for p in P]
    i0 = int(math.floor((min(xs) - _CONE_GUARD_M) / S)); i1 = int(math.ceil((max(xs) + _CONE_GUARD_M) / S))
    j0 = int(math.floor((min(zs) - _CONE_GUARD_M) / S)); j1 = int(math.ceil((max(zs) + _CONE_GUARD_M) / S))
    nat, h, blocked = {}, {}, set()
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            x, z = i * S, j * S
            n9 = dem_h(x, z)
            te9 = None
            for te, P in polys:
                if in_poly((x, z), P): te9 = (te, P); break
            if te9 is not None:
                # 平場の中 ── 補間の角に使う高さだけを持つ(⛔ 伝播はさせない)
                dd9, nr9 = _poly_near(x, z, te9[1])
                if n9 is not None and dd9 <= 2.0 * S and on_wall(d, g, nr9[0], nr9[1]):
                    h[(i, j)] = n9                 # ⛔ 壁の外へ面の高さを引き出さない
                else:
                    h[(i, j)] = float(te9[0]["y"])
                blocked.add((i, j)); continue
            if n9 is None: continue
            nat[(i, j)] = n9; h[(i, j)] = n9
            if _stair_y(d, g, x, z) is not None: blocked.add((i, j)); continue
            if wc and _wall_dist(d, g, x, z) <= wc: blocked.add((i, j))
    # ---- 円錐の頭 ── 輪郭を `_CONE_SEED_M` で歩き、**縁の盛厚の符号**で盛/切を分ける
    seedF, seedC = {}, {}
    jump = [0]          # 直線で撒いた種が障害(土留め)を跨いだ回数 ── ⭕ 0 が正
    for te, P in polys:
        for k9 in range(len(P)):
            a9 = P[k9]; b9 = P[(k9 + 1) % len(P)]
            L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
            n8 = max(1, int(L9 / _CONE_SEED_M))
            for q9 in range(n8):
                t9 = (q9 + 0.5) / n8
                x = a9[0] + (b9[0] - a9[0]) * t9; z = a9[1] + (b9[1] - a9[1]) * t9
                if on_wall(d, g, x, z): continue        # 土留めが受ける区間からは出さない
                en = dem_h(x, z)
                if en is None: continue
                dv = te["y"] - en
                if -0.05 <= dv <= 0.05: continue        # 縁がほぼ地山 ── 円錐を出さない
                bi = int(math.floor(x / S)); bj = int(math.floor(z / S))
                r9 = int(math.ceil(_CONE_SEED_R / S)) + 1
                for ii in range(bi - r9, bi + r9 + 1):
                    for jj in range(bj - r9, bj + r9 + 1):
                        kk = (ii, jj)
                        if kk in blocked or kk not in nat: continue
                        dd = math.hypot(ii * S - x, jj * S - z)
                        if dd > _CONE_SEED_R: continue
                        # ⚠ **直線で撒いた種が壁を跨いでいないか毎回測る**【検図 低 2026-09-19】──
                        #   宣言は「測地距離」だが、種の 2 m だけは直線である(上の註)。
                        #   ⛔ 例外を書いて済ませない ── ⭕ **跨いだ数を刷る**(0 が正)。
                        m9 = max(1, int(math.ceil(dd / (S / 2.0))))
                        for s9 in range(1, m9):
                            px9 = x + (ii * S - x) * s9 / m9; pz9 = z + (jj * S - z) * s9 / m9
                            if (int(round(px9 / S)), int(round(pz9 / S))) in blocked:
                                jump[0] += 1; break
                        if dv > 0.05: seedF[kk] = max(seedF.get(kk, -1e9), te["y"] - dd / bf)
                        else:         seedC[kk] = min(seedC.get(kk, 1e9), te["y"] + dd / bc)

    def _prop(seed, sign, bat):
        """円錐を測地距離で広げる(sign +1 = 盛・−1 = 切)。**現地形に沈んだ節点で止める**。"""
        POT = dict(seed)
        hp = [(-sign * v, k) for k, v in seed.items()]
        heapq.heapify(hp)
        while hp:
            key, k = heapq.heappop(hp)
            v = POT[k]
            if abs(-sign * v - key) > 1e-9: continue
            n9 = nat[k]
            if sign > 0 and v <= n9 + 0.05: continue    # 現地形に沈んだ ── ここで止まる
            if sign < 0 and v >= n9 - 0.05: continue
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dz == 0: continue
                    q = (k[0] + dx, k[1] + dz)
                    if q in blocked or q not in nat: continue
                    st = math.hypot(dx, dz) * S
                    nv = v - st / bat if sign > 0 else v + st / bat
                    if (sign > 0 and nv > POT.get(q, -1e9) + 1e-9) or \
                       (sign < 0 and nv < POT.get(q, 1e9) - 1e-9):
                        POT[q] = nv; heapq.heappush(hp, (-sign * nv, q))
        return POT
    PF = _prop(seedF, 1, bf); PC = _prop(seedC, -1, bc)
    for k, v in PF.items():
        if v > h[k]: h[k] = v
    for k, v in PC.items():
        if v < h[k]: h[k] = v
    graded, reach, guardn = set(), 0.0, 0
    for k in set(PF) | set(PC):
        if abs(h[k] - nat[k]) <= 0.05: continue
        graded.add(k)
        reach = max(reach, min(_poly_dist(k[0] * S, k[1] * S, P) for _t, P in polys))
        if k[0] <= i0 + 1 or k[0] >= i1 - 1 or k[1] <= j0 + 1 or k[1] >= j1 - 1: guardn += 1
    v9 = {"h": h, "nat": nat, "graded": graded, "reach": reach, "guardN": guardn,
          "blocked": len(blocked), "seedF": len(seedF), "seedC": len(seedC),
          "bbox": (i0, j0, i1, j1), "guardM": _CONE_GUARD_M,
          "seedR": _CONE_SEED_R, "seedM": _CONE_SEED_M, "seedJump": jump[0]}
    _CONE["key"] = id(d); _CONE["v"] = v9
    return v9


def cone_reach_m(d, g):
    """**円錐が輪郭から届く最大[m]** ── ⛔ 宣言値ではなく**解いた面からの実測**(規則4)。"""
    return cone_field(d, g)["reach"]


def _cone_at(d, g, x, z):
    """円錐の面をその点で読む ── **造成の格子の双一次**(⛔ 実装が読むのと同じ読み方)。"""
    F = cone_field(d, g); S = IMPL_STEP
    i0 = int(math.floor(x / S)); j0 = int(math.floor(z / S))
    tx = x / S - i0; tz = z / S - j0
    v = []
    for ii, jj in ((i0, j0), (i0 + 1, j0), (i0, j0 + 1), (i0 + 1, j0 + 1)):
        q = F["h"].get((ii, jj))
        if q is None:
            q = dem_h(ii * S, jj * S)
            if q is None: return None
        v.append(q)
    return ((v[0] * (1 - tx) + v[1] * tx) * (1 - tz)
            + (v[2] * (1 - tx) + v[3] * tx) * tz)


def design_y(d, g, x, z):
    """設計地盤。段(平場)・石段の通路の中なら面の高さ、縁の外は**円錐の法面**、造成しなければ None。

    ⚠ **平場が石段より優先**(2026-08-24 検図 中-5)。逆にすると、坂の帯が平場へ食い込んだ分だけ
    面に溝が掘れる(女坂の頭で最大 2.19 m)。坂は平場の外だけを受け持つ。
    ⭐ **法面は `cone_field` 一つから出る**【裁定 2026-09-19 = 案A】── ⛔ ここで ray を降ろさない。
    """
    for te in d["terraces"]:
        if in_poly((x, z), terrace_poly(te, g)): return te["y"]
    sy = _stair_y(d, g, x, z)
    if sy is not None: return sy
    nat = dem_h(x, z)
    if nat is None: return None
    y = _cone_at(d, g, x, z)
    if y is None or abs(y - nat) <= 0.05: return None
    # ④ **凹みを抜く**(裁定〈法尻と法肩〉1 = 案①『均す』・物差しは**溜まるか**)── 水の抜けない
    #    節点を落とす。⛔ 上げる方向には効かない(`min`)。⛔ ここで数え直さない(`ridge_level`)。
    cap9 = _level_cap(d, g, x, z)
    return y if cap9 is None else min(y, cap9)


def run_tamagaki(d, r):
    """run が `hFrom` で名指す玉垣の定義(丈・柱の芯々・貫の段数・立子)を引く。

    ⭐ **境内の外周の柵は前庭の玉垣と同じ作り**【ユーザー裁定 2026-09-07】なので、
    ⛔ **丈も柱の刻みも独立に持たない** — `gardens[…].tamagaki` が唯一の正典で、
    玉垣を動かせば柵も動く(規則4)。⛔ 宣言の指し先が無ければ止める(規則19)。
    """
    hf = r.get("hFrom")
    if not hf: return None
    gd = [q for q in d["gardens"] if q["name"] == hf["garden"]]
    if not gd:
        raise SystemExit("run『%s』の `hFrom` が指す区『%s』が無い" % (r["name"], hf["garden"]))
    o = gd[0]
    for seg in hf["field"].split("."):
        if not isinstance(o, dict) or seg not in o:
            raise SystemExit("run『%s』の `hFrom.field`『%s』が指図に無い" % (r["name"], hf["field"]))
        o = o[seg]
    return gd[0]["tamagaki"], o


def run_take_m(d, r):
    """run の丈[m]。⛔ 宣言(`hFrom`)を持つ物だけが値を持ち、他は None(図が『—』を刷る)。"""
    q = run_tamagaki(d, r)
    return None if q is None else q[1]


_WSEG = [None]


_WSEGP = [None]        # ⚠ `wall_segs_world` の射影の覚え書き(⛔ 55,660 節点で毎回組み直さない)


def wall_segs_named(d, g):
    """土留めを開口で割った世界座標の線分に**どの壁か**を添えたもの ── [(w, (ax,az), (bx,bz))]。

    ⛔ 線分だけの版(`wall_segs_world`)と二つの母数を作らない ── ⭕ こちらが正本で、
      あちらは名を落とした射影。**控えの天端**(`_collar_top`)が名を要る(検図 高1 2026-09-19)。
    """
    if _WSEG[0] is None:
        out = []
        for w in d["terraceWalls"]:
            for a, b in run_segs(w):
                out.append((w, g.W(a[0], a[1]), g.W(b[0], b[1])))
        _WSEG[0] = out
    return _WSEG[0]


def wall_segs_world(d, g):
    """土留め(terraceWalls)を開口で割って世界座標の線分にしたもの(`wall_segs_named` の射影)。"""
    if _WSEGP[0] is None:
        _WSEGP[0] = [(a, b) for _w, a, b in wall_segs_named(d, g)]
    return _WSEGP[0]


def _seg_dist(x, z, a, b):
    """点から線分への距離。⛔ 距離の式を検査ごとに書かない(規則4)。"""
    ddx, ddz = b[0] - a[0], b[1] - a[1]
    L2 = ddx * ddx + ddz * ddz or 1.0
    t = max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[1]) * ddz) / L2))
    return math.hypot(x - (a[0] + ddx * t), z - (a[1] + ddz * t))


def wall_in_gap(d, g, w, x, z):
    """その点は壁 `w` の**口の中**か【K106 検図 2026-09-19】。

    ⭐ **壁は自分の口の所には無い** ── 口(`gapFrom`)で割る前の折れ線までの距離が、割った後の
      線分までの距離より**近い**なら、その点は口の中に落ちている。⛔ 口の縁の小口までの距離で
      『いちばん近い壁』に選ばれると、**そこに立っていない壁の見付**でその点を裁くことになる。
    ⚠ 実害(K106 2026-09-19)── 前庭の北の腰石垣 `TW_Zentei_N` は参道の階で 3.03 間開くのに、
      口の中の縁 5 点がその壁の見付 0.50 m で裁かれ、**素土 0.78 m**と出ていた。口に立つのは
      石段の**袖石垣** `TW_SandoKai_W`/`_E`(見付 1.04 / 1.31 m)である。
    ⛔ 新しい作法ではない ── 口の位置は `run_segs`(= `gapFrom` からの従属値)そのもの。
    """
    S = run_segs(w)
    if not S: return False
    N = wall_nodes(d, w)
    if len(N) < 2: return False
    df = min(_seg_dist(x, z, g.W(*N[i]), g.W(*N[i + 1])) for i in range(len(N) - 1))
    ds = min(_seg_dist(x, z, g.W(*a), g.W(*b)) for a, b in S)
    return df + 1e-6 < ds


def wall_near_named(d, g, x, z):
    """その点に**いちばん近い土留め**と距離 ── 戻り (w, 距離) ／ 壁が無ければ (None, 1e9)。

    ⛔ **口の中に落ちた点をその壁へ結び付けない**(`wall_in_gap` ── K106 2026-09-19)。
    """
    best = (None, 1e9)
    for w, a, b in wall_segs_named(d, g):
        dd = _seg_dist(x, z, a, b)
        if dd < best[1] and not wall_in_gap(d, g, w, x, z): best = (w, dd)
    return best


def on_wall(d, g, x, z, tol=1.5):
    """その位置の平場の縁を土留めが受けているか。受けていなければ法面で摺り付ける。"""
    return wall_near_named(d, g, x, z)[1] <= tol


def igeta_rise(d):
    """井桁の**石敷からの立ち上がり**[m] ── 見付 × 段数(⛔ 数を json に持たない)。"""
    io = d.get("ido") or {}
    return io.get("igetaMitsukeM", 0.0) * io.get("igetaDanN", 0)


def soishi_radii(d):
    """(柱芯の隅の半径, 礎石の内隅の半径)[m] ── 筒の芯からの距離。⛔ 数を json に持たない。"""
    io = d.get("ido") or {}
    ken = d["const"]["ken"]
    p = io["hashiraPitchKen"] / 2.0 * ken
    s = io.get("soishiM", 0.0) / 2.0
    return math.hypot(p, p), math.hypot(p - s, p - s)


def izutsu_radii(d):
    """井筒の**三重の半径**[m] ── (内径の半分, 石積の外半径, 練り粘土の外半径)。

    ⭐ 2026-09-07 裁定2(庭方)。⛔ 径を json に書かない — 内径 `naikeiShaku` 尺・壁厚
    `kabeAtsuM`・粘土 `nendoMakiTM` からの従属値。
    """
    io = d.get("ido") or {}
    iz = io.get("izutsu") or {}
    ken = d["const"]["ken"]
    r1 = iz.get("naikeiShaku", 3) / 6.0 * ken / 2.0
    r2 = r1 + iz.get("kabeAtsuM", 0.0)
    return r1, r2, r2 + iz.get("nendoMakiTM", 0.0)


def wall_ground(d, g, px, pz, nx, nz):
    """土留めの一点の**両側の地盤**(造成後)。返り (低い側, 高い側, 犬走り or None)。

    ⭐ **物差しは二つの量**【裁定 2026-09-09 普請奉行 = 検図21巡目 A案】── 旧図の `face_toe`
      は**符号を持つ一つの量**(天端 − 外の地盤)で、三つの穴があった:
      ① 基準面が同じ壁の中ですり替わる(平場の内は造成後 `terraces[].y`・外は造成前 `dem_h`)
      ② 切土を受ける壁で 0 を返し、⛔ **未測定と区別が付かない**
      ③ 外向きを固定するので、女坂の頭のように途中で切盛が入れ替わる壁で符号が反転する
    ⭕ **基準面は造成後 `design_y` 一本**(造成しない所は現地形 `dem_h` — これが『造成後の
      地盤』の定義そのものである)。**両側を採り、どちらが外かで場合分けしない**。
      ・**見付高** `faceH` = 天端 − min(両側) …… 壁が見せる面
      ・**受け高** `backH` = max(両側) − 天端 …… 壁が背に負う土
    ⛔ **判定は焼かない** ── 判定則(擁壁として正常/埋まっている壁/段差が無い)は検査が持つ。
      ⛔ 「埋まっている壁」を地形を削って直さない(天端が自然地盤より下 ── スキル
      `unity-modular-stonewall` terrain-grading。始末は `_pending`「埋まっている土留めの始末」)。
    ⚠ 採る距離は `const.wallProbeM`(⛔ 設計値ではなく物差しの刻み)。
    """
    pr = d["const"]["wallProbeM"]
    ys, ben = [], None
    for sg in (1.0, -1.0):
        qx, qz = px + nx * pr * sg, pz + nz * pr * sg
        y = design_y(d, g, qx, qz)
        if y is None: y = dem_h(qx, qz)
        if y is None: y = plane_y(d, d["planes"][0])
        ys.append(y)
    # 犬走り ── **外向き**の側が平場の中なら、その面の高さ(展開図が細点線で重ねる)
    qo = (px + nx * pr, pz + nz * pr)
    for te in d["terraces"]:
        if in_poly(qo, terrace_poly(te, g)): ben = te["y"]
    return min(ys), max(ys), ben


def wall_nodes(d, w):
    """土留めの節点(uv)。⛔ `pts` と `a`/`b` の二通りをここ一箇所で吸う。

    ⛔ **`a`/`b` を持たない物で落ちない**【庭方 低 2026-09-19 ── `segs()` と同じ始末】──
      折れ線だけを持つ土留め(`TW_SandoKai_W` / `_E`)は `derive_gaps` が `pts` を書き込むまで
      節点を持たない。json 単体を読む道具(検査・焼き出しの一部)がそこへ来たら**空**と答える
      (⛔ KeyError で生成器ごと止めない)。⭕ 節点が要る検査は空の名簿を見て黙って飛ばす。
    """
    p = w.get("pts")
    if p: return [tuple(q) for q in p]
    if "a" in w and "b" in w: return [tuple(w["a"]), tuple(w["b"])]
    return []


def wall_stair(d, w):
    """`coping:"stair"` の土留めが**天端を引く石段**。⛔ 石段の名を数のように持たない ──
    指し先は `copingFrom.kaidan`、無ければ通りの従属元 `vFrom.kaidan`(男坂の側壁)。
    """
    if w.get("coping") != "stair": return None
    nm = ((w.get("copingFrom") or {}).get("kaidan")
          or (w.get("vFrom") or {}).get("kaidan"))
    if not nm: return None
    return ([k for k in d["kaidans"] if k["name"] == nm] or [None])[0]


def stair_first_is_top(d, g, k):
    """石段の第一点が**山上**か。⛔ 向きを手で決めない — 現地形が決める。

    ⚠ `_stair_hit` と**同じ判定**をここ一箇所に置く(2026-08-23 検図 — 男坂だけ上下逆だった)。
    """
    pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
    h0 = dem_h(pts[0][0], pts[0][1]); h1 = dem_h(pts[-1][0], pts[-1][1])
    return h0 is not None and h1 is not None and h0 > h1


def stair_sfrac(d, g, k, x, z):
    """点を石段の折れ線へ落とし、**坂下 0 → 頭 1** の走りの割合を返す(最も近い投影)。"""
    pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
    tot = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
              for i in range(len(pts) - 1)) or 1.0
    acc, best = 0.0, None
    for i in range(len(pts) - 1):
        ax, az = pts[i]; bx, bz = pts[i + 1]
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz) or 1.0
        t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (L * L)))
        dd = math.hypot(x - (ax + dx * t), z - (az + dz * t))
        if best is None or dd < best[0]: best = (dd, (acc + L * t) / tot)
        acc += L
    sf = best[1]
    return (1.0 - sf) if stair_first_is_top(d, g, k) else sf


_WCOMP = [None]


def wall_components(d):
    """土留めを**節点を共有する連なり**へ分ける。⛔ 群の名を json に書かない。

    ⭐ 回廊の基壇の4面(南妻・東面・北妻・西面)は閉じた一周をなすので、外向きは
      **その一周の重心から遠ざかる側**として機械的に決まる(⛔ 「回廊の芯 u0,v0」という
      literal を作図の中に持たない)。
    """
    if _WCOMP[0] is not None: return _WCOMP[0]
    W = d["terraceWalls"]
    par = list(range(len(W)))

    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    key = lambda q: (round(q[0], 4), round(q[1], 4))
    seen = {}
    for i, w in enumerate(W):
        for q in wall_nodes(d, w):
            k9 = key(q)
            if k9 in seen:
                a, b = find(seen[k9]), find(i)
                if a != b: par[a] = b
            else:
                seen[k9] = i
    comp = {}
    for i, w in enumerate(W):
        comp.setdefault(find(i), []).append(i)
    out = {}
    for _r, idx in comp.items():
        P = [q for i in idx for q in wall_nodes(d, W[i])]
        c = (sum(q[0] for q in P) / len(P), sum(q[1] for q in P) / len(P))
        for i in idx: out[W[i]["name"]] = c
    _WCOMP[0] = out
    return out


def wall_outward(d, g, w, a, b, k=None):
    """土留めの**外向き**(法尻を測る側)の単位法線[世界]。⛔ 符号を手で書かない。

    ① **石段の側壁** ── 石段の芯から遠ざかる側(`coping:"stair"`)
    ② **平場を受ける壁** ── 片側だけが平場の中なら、**平場でない**側(前庭の縁の5本)
    ③ ①②が決めない壁 ── **節点を共有する連なりの重心**から遠ざかる側(回廊の基壇の4面)
    """
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    nx, nz = -dz / L, dx / L
    mx, mz = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    if k is not None:                                    # ① 石段の芯から遠ざかる
        sp = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        best = None
        acc = 0.0
        for i in range(len(sp) - 1):
            ax, az = sp[i]; bx, bz = sp[i + 1]
            ddx, ddz = bx - ax, bz - az
            LL = math.hypot(ddx, ddz) or 1.0
            t = max(0.0, min(1.0, ((mx - ax) * ddx + (mz - az) * ddz) / (LL * LL)))
            q = (ax + ddx * t, az + ddz * t)
            dd = math.hypot(mx - q[0], mz - q[1])
            if best is None or dd < best[0]: best = (dd, q)
            acc += LL
        if best and ((mx - best[1][0]) * nx + (mz - best[1][1]) * nz) < 0: nx, nz = -nx, -nz
        return nx, nz
    ins = lambda q: any(in_poly(q, terrace_poly(te, g)) for te in d["terraces"])
    pr = d["const"]["wallProbeM"]                        # ⛔ 歩幅を二箇所に書かない(規則4)
    pa = ins((mx + nx * pr, mz + nz * pr))
    pb = ins((mx - nx * pr, mz - nz * pr))
    if pb and not pa: return nx, nz                      # ② 平場でない側
    if pa and not pb: return -nx, -nz
    cu, cv = wall_components(d)[w["name"]]               # ③ 連なりの重心から遠ざかる
    cx, cz = g.W(cu, cv)
    if (mx - cx) * nx + (mz - cz) * nz < 0: nx, nz = -nx, -nz
    return nx, nz


def wall_top_ground(d, g, w, k, px, pz, nx, nz):
    """土留めの一点の **(天端, 低い側の地盤, 高い側の地盤, 犬走り)**。⛔ 天端をここ以外で決めない。

    ⭐ 天端の座 ── `coping` が数ならその値、`"stair"` なら石段の割付 `stair_spans`。
    ⭐ **`copingRise: "groundHi"`**【裁定 EDO-0182 (a) 普請奉行 2026-09-13】── 天端 =
      **max(座, 高い側の地盤)**。浅い所は座に従い、地盤が座より上の所は**自然地盤まで**立ち上がる。
      ・天端の出 = 0(⛔ 自然地盤より上へは上げない ── スキル §3b『露出 0〜駒の丈』の下端)
      ・外側の地盤 = 両側の高い側(⛔ 外向きの一点で採らない ── 裁定 2026-09-09 の物差しと揃える)
    ⛔ 地形を壁に合わせて削らない(天端が自然地盤より下 ── スキル terrain-grading)。
    """
    base = (stair_y_at(k, stair_sfrac(d, g, k, px, pz))
            if k is not None else float(w.get("coping")))
    glo, ghi, ben = wall_ground(d, g, px, pz, nx, nz)
    top = max(base, ghi) if w.get("copingRise") == "groundHi" else base
    return top, glo, ghi, ben


def wall_stations(d, g, w, step=1.0):
    """土留めの走りの**駅** ── (s, x, z, 外向き nx, 外向き nz) を節点から `step`[m] 刻みで。

    ⛔ **歩き方を二箇所に書かない**【考証 高 2026-09-19】── 縦断(`wall_samples`)と一点の
      問い合わせ(`wall_tg_at`)が別々に走りを刻んでいたので、同じ壁が二つの答えを持った。
    """
    P = [g.W(*q) for q in wall_nodes(d, w)]
    k = wall_stair(d, w)
    acc = 0.0
    for i in range(len(P) - 1):
        ax, az = P[i]; bx, bz = P[i + 1]
        L = math.hypot(bx - ax, bz - az)
        if L < 1e-9: continue
        nx, nz = wall_outward(d, g, w, P[i], P[i + 1], k)
        n = max(1, int(math.ceil(L / step)))
        for j in range(n + 1):
            if i and j == 0: continue                    # 節点の重複を落とす
            t = min(L, j * L / n)
            yield (acc + t, ax + (bx - ax) * t / L, az + (bz - az) * t / L, nx, nz)
        acc += L


def wall_tg_at(d, g, w, px, pz):
    """世界の一点に**最も近い駅**での **(天端, 低い側の地盤, 高い側の地盤, 犬走り)**。

    ⛔ `wall_samples` と別の物差しを作らない ── 中身は同じ `wall_top_ground` を一点で呼ぶだけ。
    ⭕ 見付高 = 天端 − 低い側 ／ 受け高 = 高い側 − 天端(裁定 2026-09-09 と同じ定義)。
    ⭐ **駅で測る**【考証 高 2026-09-19】── 旧は問う点を走りへ落とした**その場**で測っていた。
      設計面は平場の輪郭で垂直に飛ぶので、輪郭の突端の際では**両側の探りがどちらも平場へ落ち**、
      同じ壁『TW_Kairo_N』を縦断が 4.07〜6.96 m と刷るかたわらで検査が 0.70 m と読んでいた
      (問う点を 4 cm ずらすと値が飛ぶ)。⭕ 歩き方は縦断と同じ一つ(`wall_stations`)にし、
      刻みは物差しの歩幅 `const.wallProbeM`。⛔ 縦断と検査で二つの答えを持たない(規則4)。
    """
    k = wall_stair(d, w)
    best = None
    for _s, qx, qz, nx, nz in wall_stations(d, g, w, float(d["const"]["wallProbeM"])):
        dd = math.hypot(px - qx, pz - qz)
        if best is None or dd < best[0]: best = (dd, qx, qz, nx, nz)
    _dd, qx, qz, nx, nz = best
    return wall_top_ground(d, g, w, k, qx, qz, nx, nz)


def wall_samples(d, g, w, step=1.0):
    """土留めの走りを `step`[m] 刻みに歩く。

    返り [(s, 天端, 低い側の地盤, 高い側の地盤, 見付高, 受け高, 犬走り or None, 建つか)]
    ── s は**節点の第一点から**の走り[m]。
    ⭐ **地盤は両側を採る**(`wall_ground`)【裁定 2026-09-09 = 検図21巡目 A案】── 見付高 =
      天端 − 低い側 ／ 受け高 = 高い側 − 天端。⛔ **一つの符号付きの量に畳まない**
      (0 が『段差が無い』なのか『未測定』なのか区別が付かなくなる)。
    ⭐ 天端 ── `coping` が数ならその値、`"stair"` なら**石段の割付 `stair_spans` から引く**
      (点を石段の折れ線へ落として走りの割合を出し、`stair_y_at` を通す)。
      ⛔ 側壁のためにもう一つの段割りを書かない(⚠ 二つの式で割ると蹴上1段ぶんずれる —
      2026-08-24 検図 高-4、男坂で最大 1.34 m)。
    ⭐ 「建つか」── `run_segs`(開口を抜いた実際に建つ区間)の上にあるか。⛔ 開口を実装に
      切り直させない。
    """
    segU = run_segs(w)                                   # uv・開口を抜いた区間
    k = wall_stair(d, w)
    out = []
    for s9, px, pz, nx, nz in wall_stations(d, g, w, step):   # ⛔ 歩き方は一つ(規則4)
        top, glo, ghi, ben = wall_top_ground(d, g, w, k, px, pz, nx, nz)
        u9, v9 = g.U(px), g.V(pz)
        st = any(_pt_seg((u9, v9), q[0], q[1]) < 1e-3 for q in segU) if segU else False
        out.append((s9, top, glo, ghi, top - glo, ghi - top, ben, st))
    return out


def wall_profile(d, g, w, step=1.0):
    """焼き出し用の縦断 **6列** `[[s, top, groundLo, groundHi, faceH, backH], ...]`。

    ⛔ 実装が引き直さない。⭐ 6列である理由は `wall_ground` の docstring(裁定 2026-09-09)。
    """
    return [[round(q[i], 3) for i in range(6)] for q in wall_samples(d, g, w, step)]


def wall_gaps_s(sm, step=1.0):
    """`wall_samples` の列から、**建たない区間**(開口)の s の範囲 [[s0,s1], ...]。

    ⛔ 開口を数で持たない ── 出所は `run_segs`(= `gaps`/`gapFrom` からの従属値)そのもの。
    """
    out, run = [], False
    for q9 in sm:
        s9, st = q9[0], q9[-1]
        if st:
            run = False; continue
        if run and out and s9 - out[-1][1] <= step * 1.001 + 1e-6:
            out[-1][1] = s9
        else:
            out.append([s9, s9]); run = True
    return [[round(a, 3), round(b, 3)] for a, b in out]


def ido_depth(d):
    """掘井戸の深さの幅[m] ── **石敷の天端 − 地下水面の上限/下限**。

    ⚠ 2026-09-06 考証検分4巡目 中4: 指図が 5〜8 m を直に持っていたが、前庭の天端と東の麓道は
    ほぼ同高で「麓道以下」からは数十cmしか出ず、8m を出す一歩(溜池の水面を下限に置く)が
    図にも指図にも無かった。⛔ 数を持たず、`ido.gwBoundsM` からの引き算で出す。
    ⛔ 記号 P(プロジェクト内実測)を地下水位の推定に使わない — 確度は【U 設計値】。
    ⚠ 旧版はここに【B 常態】と書いていたが、『台地の縁の掘井戸は江戸の常態【B】』は
    2026-09-07 考証7巡目 中1 で取り下げられている(掃き残し・検図12巡目 の巡で直した)。
    """
    lo, hi = d["ido"]["gwBoundsM"]
    y = d["terraces"][1]["y"]
    return (y - hi, y - lo)


# ================================================================ 実装が読む算出物(`--export-impl`)
# ⭐ **なぜ焼くか**(2026-09-08 棟梁が Stage 1 の一手目で止まった)。
#   造成後の地盤 `design_y`・境内の囲いの折れ線(平場の輪郭からの生成物)・石段の割付
#   `stair_spans`・社叢に撒く木の位置は、**指図の json には一つも入っておらず**、
#   この生成器だけが持っている。C# へ移植すると正典が二つになって黙ってドリフトするので
#   (⚠ 実例 — 切盛図と断面が男坂で最大 1.34 m 食い違い、段割りを `stair_spans` 一つへ
#   寄せて直した)、**指図が正典で実装はその従属物**という作法(CLAUDE.md 規則4・規則11)に
#   倣ってここから焼き出す。⛔ **岡部邸 2026-09-03 の裁定1=A を典拠に引かない**【K110
#   2026-09-19】── あれは『勝手の道が竹垣の外を走る区間』(K300)の裁定で**別件**である。
#   ⚠ 焼き出しをここに置くこと自体は【U 当方の作法 ── 典拠なし】
#   (⛔ **題を付けない** ── 当図の〈造成の縁〉1 は 2026-09-19 の別の決定の題で、同じ題を
#   別日の別件へ流用すると名乗りが再び衝突する【考証 中 2026-09-19】)。
#   ⛔ 焼き出し用に別の実装を書かない — **図が使うのと同じ関数の返り値**をそのまま書くこと。


DEM_JSON = os.path.join(DOC, "sanno_dem.json")


# 焼き出しの地盤の格子[m]。⛔ **設計値ではない** — 地形のハイトマップが世界軸の格子なので、
# 回転させず世界座標のまま 1 m で刻む(この社のグリッドは世界軸そのものなので回転は元より無い)。
IMPL_STEP = 1.0


# 土留めの縦断を焼く走りの刻み[m]。⛔ **設計値ではない**(検図20巡目 中4 の求めが「1m 刻み」)。
IMPL_WALL_STEP = 1.0


# ⭐ **物差しは二つある。混ぜない**【中3 検図20巡目 → 2026-09-09】。
#   どちらも ⛔ **検査の物差しであって設計値ではない**(だから json ではなくここに置く。
#   岡部も `("checks", {"gradeTol": 0.30, "baseMin": bmin})` を生成器側に持つ)。
# ① `exportTol` ── **図の側**。焼き出した `graded` と `design_y` の許容差[m]。
#   同じ関数から出ている以上、丸めの 0.001 m 以外は出ないはず(⛔ 緩めて黙らせない)。
# ② `gradeTol`  ── **実装側**。造成した Unity の地形と設計面の許容差[m]。
#   ⚠ ハイトマップは 16bit 正規化なので量子が 0.003〜0.009 m あり、⛔ ここへ 0.001 を
#   入れると棟梁の造成後QAが**全セル不合格**になる。意味の正典は
#   `EdoOkabeYashikiBuilder.IMPL` の doc コメント(岡部は 0.30)で、同じ値に揃える。
IMPL_EXPORT_TOL = 0.001


IMPL_GRADE_TOL = 0.30


def _sha256(path):
    """ファイルの**バイト列**の SHA-256(小文字hex)。⛔ 中身を読み直して作り直さない。"""
    import hashlib
    h9 = hashlib.sha256()
    with open(path, "rb") as f9:
        h9.update(f9.read())
    return h9.hexdigest()


def _seed_rnd(d, name, lay):
    """撒く乱数の種 ── **`planting.plantRule.seed` の宣言そのもの**(「帯・区の名 + '/' + 層の名」)。

    ⛔ 時刻や連番で振らない(流し直すたびに木が動くと検証レンダが比較できない)。
    ⛔ 宣言が無ければ止める — 種の出所が指図に無いまま撒くと、**同じ指図から別の林**が出る。
    """
    import hashlib, random
    if not (d["planting"].get("plantRule") or {}).get("seed"):
        raise SystemExit("`planting.plantRule.seed` の宣言が無い — 撒く種の出所が指図に無い")
    key = "%s/%s" % (name, lay)
    return random.Random(int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)), key


def _apportion(vals, tot):
    """実数の列 `vals` を、和が `tot` になる整数へ**最大剰余法**で配る。

    ⛔ 帯ごとに丸めない — 帯ごとに丸めると和が予算表(`plant_budget`)と食い違い、
    「焼いた点の数 = 図が刷った本数」の検査が立たなくなる。
    """
    fl = [int(math.floor(max(0.0, v))) for v in vals]
    rest = tot - sum(fl)
    order = sorted(range(len(vals)), key=lambda i: (-(max(0.0, vals[i]) - fl[i]), i))
    for i in order[:max(0, rest)]:
        fl[i] += 1
    return fl


def _scatter_take(rnd, cells, n, rmin, seeded=()):
    """候補のセル(uv)から **n 点**を決定論的に採る。芯々の下限は `rmin`[間]。

    ⭕ 位置は**セルの中心のまま**(⛔ 揺らぎを足さない)── セルは退避を引いた面の走査結果で、
      中心を外すと退避へはみ出す点が出る(図が測った面と別物になる)。
    ⚠ 採りきれなければ `rmin` を 0.9 倍して採り直す。**緩めた回数は記録に残す**
      (⛔ 黙って詰めない — 密度と芯々が両立しないことは指図の側の欠陥である)。
    戻り (点, 実際の rmin, 緩めた回数)。
    """
    cs = list(cells)
    rnd.shuffle(cs)
    fix = [tuple(q) for q in seeded]
    r, relax = float(rmin), 0
    while True:
        gr, out = {}, []
        for q in fix:
            gr.setdefault((int(math.floor(q[0] / r)), int(math.floor(q[1] / r))), []).append(q)
        for p in cs:
            c = (int(math.floor(p[0] / r)), int(math.floor(p[1] / r)))
            ok = True
            for a in range(c[0] - 1, c[0] + 2):
                for b in range(c[1] - 1, c[1] + 2):
                    for q in gr.get((a, b), ()):
                        if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < r * r:
                            ok = False
                            break
                    if not ok: break
                if not ok: break
            if not ok: continue
            gr.setdefault(c, []).append(p)
            out.append(p)
            if len(out) >= n: return out, r, relax
        if len(out) >= n or relax >= 40 or r < 1e-3:
            return out, r, relax
        r *= 0.9
        relax += 1


def _pick_part(rnd, pal):
    """palette の一点を**宣言の重み `w`** で引く。⛔ 重みを発明しない。"""
    tot = sum(q.get("w", 1) for q in pal)
    x = rnd.uniform(0.0, tot)
    for pt in pal:
        x -= pt.get("w", 1)
        if x <= 0.0: return pt
    return pal[-1]


_LAY_KIND = {"松": "matsu", "落葉": "rakuyo", "中木": "chuboku"}


def _variant_under(d, pt, h, kind, xz, rmax):
    """**樹冠の半径が `rmax`[m] 以下の変種**から引く(`clusters[].variantRule`)。

    ⭐ 2026-09-08 十六巡目 C-1(庭方)── 素のまま `sizeRule` に任せると
    『張り出し ≤ 局所の(路肩+側溝) − `marginM`』の条項を割る個体が出る。
    ⛔ 数を持たない ── 上限は局所の道敷幅からの従属値。
    ⚠ 満たす変種が一つも無ければ**最も細い変種**を返す(⛔ 黙って通さない — 検査が名で刷る)。
    戻り (size, prefab, api, scaleY) か None。
    """
    vs = part_variants(d, pt)
    if not vs: return pick_variant(d, pt, h)
    ok = [q for q in vs if q[4] * xz / 2.0 <= rmax]
    src = ok or vs
    pick = max(src, key=lambda q: q[4]) if ok else min(src, key=lambda q: q[4])
    return (pick[0], pick[1], pick[2], (h / pick[3]) if pick[3] else None)


def _xz_capped(d, kind, xz, xzr, h, g0, iso=False):
    """個体の `scaleXZ` を **`scaleRule.scaleXZCapFrom`** で頭打ちにする【指3 庭方 十八巡目】。

    上端 = `crownPerHMax` × **その個体の丈** ÷ **部材の素の樹冠**。
    ⛔ **孤立木(`isolatedXZ` の側)には当てない** ── そもそも `crownPerHMax` の対象外である。
    ⛔ 下限(範囲の下端)は割らない ── 割るなら**部材と丈の組み合わせ**の問題で、検査が名で刷る。
    """
    sr = d["planting"]["scaleRule"]
    if xz is None or iso or not sr.get("scaleXZCapFrom") or not kind: return xz
    cap = (sr.get(kind) or {}).get("crownPerHMax")
    if cap is None or not g0 or not g0[0] or not h: return xz
    lim = cap * h / g0[0]
    lo = xzr[0] if xzr else 0.0
    return max(lo, min(xz, lim))


def _tree_row(d, g, rnd, name, group, lay, pal, hrng, u, v, iso=False, rmax=None):
    """撒いた一本。丈は宣言の範囲から、**大きさ(変種)は `sizeRule` が丈から選ぶ**。

    ⭐ **2026-09-08 十六巡目 B-2(庭方)── `scaleXZ` を点ごとに焼く。**旧式は点が `scaleY`
    しか持たず、**樹冠 = 部材の樹冠 × `scaleXZ`** に乗る三つ(①退避の可否 ②参道への張り出しの
    条項 ③石段の肩の上限)が全部、⛔ **図が測った樹冠と現物の樹冠が別**になる形だった。
    ⛔ `plantRule.scaleJitter` は 2026-09-08 に廃した(裁き3・庭方)── `scaleY` へ二重に掛けると
    箍と樹冠が黙って動く。役『同じ大きさの木を並べない』は丈を範囲から引くことが果たす。
    """
    pt = _pick_part(rnd, pal)
    lo, hi = _h_pair(hrng)
    if lo is None:
        raise SystemExit("『%s』の %s の丈の宣言が無い — 撒けない" % (group, lay))
    h = rnd.uniform(lo, hi)
    cap = species_h_cap(d, pt)               # 樹種ごとの丈の上端(`sizeRule.speciesHCap`)
    if cap is not None: h = min(h, cap)
    kind = _LAY_KIND.get(lay)
    xzr = layer_xz(d, kind, iso) if kind else None
    # ⭐ **点ごとに引く**(⛔ 範囲の中央で代表させない — 図が測るのは個体の樹冠である)
    xz = rnd.uniform(xzr[0], xzr[1]) if xzr else None
    q = (_variant_under(d, pt, h, kind, xz or 1.0, rmax) if (rmax is not None and kind)
         else pick_variant(d, pt, h))
    g0 = part_geom({"prefab": (q[1] if q else pt.get("prefab"))})
    # ⭐ **`scaleXZ` の上端を個体ごとに頭打ちにする**【指3 庭方 2026-09-09 十八巡目】──
    #    `sizeRule` が目標より高い部材を採って丈を Y で縮めた個体(`scaleY` < 1)は、
    #    樹冠 ÷ 丈 が `素の比 × scaleXZ ÷ scaleY` で膨れる。⛔ 上限(`crownPerHMax`)を緩めず、
    #    ⛔ 密度も部材も動かさず、**倍率の側**で収める。⛔ 下限は範囲の下端のまま。
    xz = _xz_capped(d, kind, xz, xzr, h, g0, iso)
    x, z = g.W(u, v)
    py, pg = _plant_y(d, g, x, z)
    return {"name": name, "group": group, "layer": lay,
            "species": pt.get("species"), "part": (q[2] if q else pt.get("api")),
            "prefab": (q[1] if q else pt.get("prefab")), "size": (q[0] if q else None),
            "h": round(h, 3), "scaleY": (round(q[3], 4) if q and q[3] else None),
            "scaleXZ": (round(xz, 4) if xz is not None else None),
            # ⭐ 【庭方 2026-09-15】低木は `scaleXZ` が引けなくても樹冠を作る(部材の樹冠径 × 1.0)── 見上げの隠す物に数えるため
            "crownM": (round(g0[0] * xz, 3) if (g0 and xz is not None) else
                       (round(g0[0], 3) if (g0 and lay == "低木") else None)),
            "u": round(u, 4), "v": round(v, 4),
            "world": [round(x, 3), round(z, 3)],
            "y": round(py, 3),
            "ground": pg,
            "place": (d["planting"]["plantRule"].get("placement") or {}).get(lay)}


def _plant_y(d, g, x, z):
    """**木の足元の地盤**(y[m], その出所)【中 庭方2巡目 2026-09-18 → 規則19】。

    ⛔ **現地形のままの y を焼かない** ── 実装は**造成した地形**に木を置く(`graded`)ので、
      面の外の「格子の縁(帯 + 法面)」に落ちた木は図と現物で足元が食い違っていた
      (旧版は `design_y` が無ければ即 `dem_h` に落ちていた)。
    ⇒ ① 設計面(`design_y`)② 格子の縁(`graded_y` ── 帯 + 法面)③ 現地形、の順に採る。
    ⛔ 木の**位置**(u,v)は動かさない ── 動かすのは庭方の領分。⚠ 縁の盛土の上に立つ木が
      どれだけ在るかは検査『焼き出した木が…』が名指しで刷る(⛔ 数を黙って呑まない)。
    """
    dy = _design_y_cold(d, g, x, z)
    if dy is not None:
        return dy, "design"
    gy = graded_y(d, g, x, z)
    if gy is not None:
        return gy, "graded"
    nat = dem_h(x, z)
    return (nat if nat is not None else 0.0), "terrain"


def cluster_crown_cap(d, c):
    """`clusters[].variantRule` の**樹冠の半径の上限**[m]。⛔ 数を持たない(局所の道敷幅から)。"""
    if not c.get("variantRule"): return None
    lim = overhang_limit(d, c)
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    ins = tl.get("insetKen")
    if not lim or ins is None: return None
    return min(q[1] for q in lim) + ins * d["const"]["ken"]


_ZONE_RE = re.compile(r"(南|北)\s*1\s*/\s*(\d+)")


def cluster_zone(c, kind):
    """`mixZone` が樹種 `kind` に切る**v の小領域**(lo, hi)。⛔ v の数を書かない(`vRange` から)。"""
    z = (c.get("mixZone") or {}).get(kind)
    vr = c.get("vRange")
    if not z or not vr: return None
    m = _ZONE_RE.search(z)
    if not m: return None
    f = 1.0 / float(m.group(2))
    v0, v1 = vr
    return (v0, v0 + (v1 - v0) * f) if m.group(1) == "南" else (v1 - (v1 - v0) * f, v1)


def scatter_pts(d, g):
    """**撒いた木の点**。実装(棟梁)はこれをそのまま置く。

    ⛔ 「帯1に松 N 本」と数だけ渡して実装に撒かせない ── 撒き方が実装ごとに変わると、
      指図の検査(退避・樹冠・林縁の張り出し・不変条件)が見ている面と現物が別になる。
    ⭕ 出所はすべて宣言:面 = `band_scan`/`poly_scan`、退避 = `avoid_shapes`、
      本数 = `band_stats`(密度 × 有効面)、芯々 = 帯の `spacing` × `plantRule.packRatio`、
      丈 = 帯の `matsuH`/`rakuyoH`/`chubokuH`/`teibokuH`、種 = `plantRule.seed` の宣言。
    戻り (点の列, 帯ごとの記録, 塊の記録)。
    """
    ken = d["const"]["ken"]
    pal = d["planting"]["parts"]
    pack = d["planting"]["plantRule"]["packRatio"]
    st = band_stats(d, g)
    cells, _skip = band_scan(d, g)
    rows = [r for r in st if "b" in r]
    # ---- 塊(位置を決めて据える物)を先に解く。⛔ 帯の塊は帯の本数の**内訳**なので後で差し引く
    cl_pts, cl_note, cl_cut, rc = [], [], {}, {}
    gapd = []           # 間合い(`gapDiscFrom`)の円 [(u, v, 半径[間], 塊の名)]

    def _in_gap(p, skip=None):
        """間合いの円の中か(⛔ 円を出した塊自身は除く)。"""
        for u9, v9, r9, nm9 in gapd:
            if skip == nm9: continue
            if (p[0] - u9) ** 2 + (p[1] - v9) ** 2 < r9 * r9: return True
        return False

    def rnd_of(name, lay):
        """種は**一つの (名, 層) につき一本**の流れ。⛔ 部材ごとに引き直さない
        (引き直すと同じ並びが繰り返され、丈まで同じ値が出る)。"""
        if (name, lay) not in rc: rc[(name, lay)] = _seed_rnd(d, name, lay)
        return rc[(name, lay)]
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            polys = cluster_polys(c)          # ⭐ 箱でなく**輪郭**(2026-09-08 C-1)
            parts = cluster_parts(d, gd, c)
            sp = cluster_spacing(d, c)
            nm = "%s／%s" % (gd["name"], c["name"])
            if not polys or not parts or sp is None:
                cl_note.append({"name": nm, "n": cluster_n(c), "boxes": cluster_boxes(c),
                                "points": None,
                                "unresolved": ("輪郭が引けない" if not polys else
                                               "芯々(`spacing`/`spacingFrom`)の宣言が無い"
                                               if sp is None else
                                               "`mix`(樹種の割り前)の宣言が無い")})
                continue
            rmin = sp * pack                                # [間]。⛔ 数を作らない
            step = max(rmin / 4.0, 0.05)
            cand0 = [p for Q in polys for p in poly_scan(Q, step)]
            cand = [p for p in cand0 if not _in_gap(p, c["name"])]  # 指1 辻の留めの間合い
            # ⭐ **間合いに食われたら線に沿ってずらす**【指1 庭方 2026-09-09 十八巡目】──
            #    ⛔ **本数を減らして黙らせない。**⛔ ずらす量を json に持たない ── 「その塊の木が
            #    全部、間合いの外に立てる最小の移動」として図が毎回求める。
            #    ⭕ 林縁が辻の手前で切れるのは**留めの木の作法どおり**である。
            slid, seed0 = 0.0, []
            if len(cand) < len(cand0) and c.get("poly"):
                need = int(math.ceil(cluster_n(c) - 1e-9))
                Pq = c["poly"]
                du9 = Pq[1][0] - Pq[0][0]; dv9 = Pq[1][1] - Pq[0][1]
                Ln9 = math.hypot(du9, dv9) or 1.0
                du9, dv9 = du9 / Ln9, dv9 / Ln9
                # ⛔ **向きを決め打ちしない**(⚠ 間合いの芯は線から横へ外れているので、
                #    線に沿った射影だけで『遠ざかる向き』を決めると逆を選ぶ)。
                #    ⭕ **両方向を同じ刻みで試し、先に成り立ったほう**(= 移動が小さいほう)を採る。
                # ⭕ **先に据えた塊の木も避ける**(⛔ 兄弟の塊と融合した位置へ滑らせない)。
                prev9 = [(q["u"], q["v"]) for q in cl_pts]
                # ⭕ **滑らせた先が退避へ載らないことも測る**【低2 検図20巡目 の指摘の射程】──
                #    ⛔ 塊の候補セルは箱の走査だけで作られていて退避を一度も引いていないので、
                #    ⛔ **箱を動かせば黙って社地の外や石段の敷きへ入る**。
                sh9 = avoid_shapes(d, g, "obi4" if gd.get("uv") else
                                   ("obi123:松" if gd.get("band") else "keidai"))
                t9 = 0.0
                while t9 < 8.0 and not slid:
                    t9 += step
                    for sgn9 in (1.0, -1.0):
                        QS = [[(q[0] + du9 * sgn9 * t9, q[1] + dv9 * sgn9 * t9) for q in Q]
                              for Q in polys]
                        cd = [p for Q in QS for p in poly_scan(Q, step)]
                        cd = [p for p in cd if not _in_gap(p, c["name"])
                              and not (sh9 and shape_hit(p, sh9))]
                        # ⛔ **緩めた置き方で『入った』と読まない**(`_scatter_take` は入らないと
                        #    `rmin` を 0.9 倍して採り直す)── 芯々の下限を割ったまま滑らせると、
                        #    ⛔ 幹が二本同じ株から生えて見える。
                        _t9 = _scatter_take(rnd_of(nm, "松")[0], cd, need, rmin, seeded=prev9)
                        if len(_t9[0]) >= need and _t9[2] == 0:
                            polys, cand, slid, seed0 = QS, cd, sgn9 * t9, prev9
                            break
            cap = cluster_crown_cap(d, c)                   # `variantRule` の上限[m]
            iso = bool(c.get("isolatedCrown"))              # 孤立木の樹冠(⛔ 林の形にしない)
            got = []
            # ⛔ **通し番号は塊 × 樹種で一本** ── ⚠ 2026-09-09: palette の点ごとに `i` を
            #   振り直していたので、塊が小さいと**同じ名が二本**出た(『参道の林縁 中 松01』が
            #   二つ)。⛔ 名が衝突すると実装が木を指せず、検査の対も潰れる。
            seq9 = {}
            # ⭐⭐ **線に沿う塊は『撒く』のではなく『弧長を芯々で刻んで据える』**
            #   【A-7 庭方 2026-09-09 十九巡目】── ⛔ `planting.plantRule.packRatio` は
            #   **面へ撒くときの詰まり**であって、一列に据える塊には当たらない。⚠ 掛けたまま
            #   撒いていたので、宣言した芯々 [1.8, 2.4] 間に対し実測は 2.36〜2.92 m で
            #   **5 対すべてが下限を割っていた**(⛔ 検査は鳴っていなかった)。
            #   ⛔ 位置の数を json に持たない ── 平行四辺形の芯線と `spacing` からの従属値。
            line9 = None
            if c.get("alongTakagiEdgeLine") and c.get("poly") and len(c["poly"]) == 4:
                P4 = c["poly"]
                a0 = ((P4[0][0] + P4[3][0]) / 2.0, (P4[0][1] + P4[3][1]) / 2.0)  # 南端の芯
                a1 = ((P4[1][0] + P4[2][0]) / 2.0, (P4[1][1] + P4[2][1]) / 2.0)  # 北端の芯
                L9 = math.hypot(a1[0] - a0[0], a1[1] - a0[1])
                need9 = int(round(cluster_n(c)))
                run9 = (need9 - 1) * sp
                t09 = max(0.0, (L9 - run9) / 2.0)
                ux9 = ((a1[0] - a0[0]) / L9, (a1[1] - a0[1]) / L9) if L9 > 1e-9 else (0.0, 1.0)
                line9 = [(a0[0] + ux9[0] * (t09 + i * sp), a0[1] + ux9[1] * (t09 + i * sp))
                         for i in range(need9)]
                # ⛔ **間合い(辻の留め)の中へ据えない** ── 受入値②『高木の縁の線の s の範囲を
                #   出ないこと』。⚠ 入ってしまう本は据えずに `gapHit` で数える(⛔ 黙って詰めない)。
                gh9 = [p for p in line9 if _in_gap(p, c["name"])]
                if gh9:
                    line9 = [p for p in line9 if not _in_gap(p, c["name"])]
                    cl_note.append({"name": nm, "gapHit": len(gh9),
                                    "runKen": round(run9, 3), "lineKen": round(L9, 3)})
                cl_note.append({"name": nm, "alongLine": True, "spacingKen": sp,
                                "runKen": round(run9, 3), "lineKen": round(L9, 3),
                                "slackKen": round(L9 - run9, 3)})
            for kind, pt, k, hh, _cr, sk, _vs, _lo, _hi in parts:
                lay = "松" if kind == "松" else "落葉"
                rnd, _key = rnd_of(nm, lay)
                if line9 is not None:
                    # ⭕ **`mix` の並びがそのまま南→北の順**(⛔ `mixZone` は当てない)
                    pts, r_, rx = line9[:k], sp, 0
                    line9 = line9[k:]
                else:
                    # ⭐ **樹種を v の小領域へ寄せる**(`mixZone`・2026-09-08 C-1)
                    zn = cluster_zone(c, kind)
                    cz = [p for p in cand if zn[0] <= p[1] <= zn[1]] if zn else cand
                    pts, r_, rx = _scatter_take(rnd, cz, k, rmin, seeded=got + seed0)
                for (u9, v9) in pts:
                    got.append((u9, v9))
                    seq9[kind] = seq9.get(kind, 0) + 1
                    q = _tree_row(d, g, rnd, "%s %s%02d" % (c["name"], kind, seq9[kind]),
                                  nm, lay, [pt], hh, u9, v9, iso=iso, rmax=cap)
                    cl_pts.append(q)
                if len(pts) < k:
                    cl_note.append({"name": nm, "short": k - len(pts)})
            # ⭐ **★主景の幹からの離れ**【庭方 2026-09-13 中】── 割った木だけを箱の `gapRelocate` の
            #    四分へ据え直す。⛔ ほかの木・丈・部材は動かさない(位置だけ)。⛔ 位置の数を持たない。
            if c.get("trunkGapFromShukeiKen") is not None:
                gap9 = float(c["trunkGapFromShukeiKen"])
                tr9 = [(gd9.get("shukei") or {}).get("tree") for gd9 in d["gardens"]]
                tr9 = [t for t in tr9 if t and t.get("uv")]
                if tr9:
                    tu9, tv9 = tr9[0]["uv"]
                    bx9 = cluster_boxes(c)[0]
                    uc9, vc9 = (bx9[0] + bx9[2]) / 2.0, (bx9[1] + bx9[3]) / 2.0
                    quad9 = {"北西": lambda p: p[0] <= uc9 and p[1] >= vc9,
                             "北東": lambda p: p[0] >= uc9 and p[1] >= vc9,
                             "南西": lambda p: p[0] <= uc9 and p[1] <= vc9,
                             "南東": lambda p: p[0] >= uc9 and p[1] <= vc9}.get(c.get("gapRelocate"))
                    mine9 = [q for q in cl_pts if q["group"] == nm]
                    for q in mine9:
                        if math.hypot(q["u"] - tu9, q["v"] - tv9) >= gap9 - 1e-9: continue
                        if quad9 is None:
                            cl_note.append({"name": nm, "gapShukei": q["name"], "relocated": False}); continue
                        oth9 = [(p["u"], p["v"]) for p in cl_pts if p is not q]
                        cd9 = [p for p in cand if quad9(p)
                               and math.hypot(p[0] - tu9, p[1] - tv9) >= gap9]
                        tk9 = _scatter_take(rnd_of(nm, "松")[0], cd9, 1, rmin, seeded=oth9)
                        if not tk9[0] or tk9[2]:
                            cl_note.append({"name": nm, "gapShukei": q["name"], "relocated": False})
                            continue
                        u9, v9 = tk9[0][0]
                        for i9, p9 in enumerate(got):
                            if abs(p9[0] - q["u"]) < 1e-3 and abs(p9[1] - q["v"]) < 1e-3:
                                got[i9] = (u9, v9)
                        x9, z9 = g.W(u9, v9)
                        py9, pg9 = _plant_y(d, g, x9, z9)
                        q.update({"u": round(u9, 4), "v": round(v9, 4),
                                  "world": [round(x9, 3), round(z9, 3)],
                                  "y": round(py9, 3), "ground": pg9})
                        cl_note.append({"name": nm, "gapShukei": q["name"], "relocated": True,
                                        "to": [round(u9, 4), round(v9, 4)]})
            cl_note.append({"name": nm, "n": cluster_n(c), "boxes": cluster_boxes(c),
                            "points": len(got),
                            "rmin": round(sp if line9 is not None else rmin, 3),
                            "slidKen": (round(slid, 3) if slid else None)})
            # ⭐ **間合いを宣言した塊は、据えたあとの幹から円を切る**【指1 庭方 十八巡目】──
            #    ⛔ 帯・ほかの塊の高木の幹をこの円に入れない(⛔ この塊自身は除く)。
            #    ⭕ 役『路の終端を一点でふさぐ』は、隣の塊の頭が寄り添うと成り立たない。
            if c.get("gapDiscFrom"):
                rq = [q for q in cl_pts if q["group"] == nm and q.get("crownM")]
                rr = max((q["crownM"] / 2.0 / ken) for q in rq) if rq else None
                if rr:
                    for (u9, v9) in got:
                        gapd.append((u9, v9, rr, c["name"]))
            if gd.get("band"):                              # 帯の塊 = 帯の本数の内訳
                for kind, _pt, k, _h, _c, _s, _v, _l, _hi in parts:
                    key = (gd["band"], "松" if kind == "松" else "落葉")
                    cl_cut[key] = cl_cut.get(key, 0) + k
    # ⭐ **名指しの木も帯の本数の内訳**【決1③ 庭方 2026-09-09 十八巡目】── 帯の面に立つ以上、
    #    ⛔ 帯の本数に上積みしない(⛔ 密度は動かさない、が決1 の要である)。
    _NT9 = named_tree_rows(d, g)
    for r9 in _NT9:
        if r9.get("band"):
            k9 = (r9["band"], r9.get("layer") or "落葉")
            cl_cut[k9] = cl_cut.get(k9, 0) + 1
    # ---- 帯に撒く。⭐ **層ごとに四帯を一度に引く**(2026-09-08 十六巡目 A-2・庭方)──
    #    旧式は帯ごとに独立で、**帯どうし・帯と塊が互いを知らないまま**撒いており、
    #    芯々の下限を割る対が 229(すべて『別の帯・区どうし』)出た。⛔ 本数の配り方は変えない。
    #    ⭕ 松と落葉は**同じ林冠**なので互いの芯々も守る(一つの `seeded` に積む)。
    n_f, n_rf = {}, {}
    for lay in _LAYS:
        for i, r in enumerate(rows):
            v = (r["takagi"] - r["rakuyo"]) if lay == "松" else \
                r["rakuyo"] if lay == "落葉" else \
                r["chuboku"] if lay == "中木" else r["teiboku"]
            n_f.setdefault(lay, []).append(v)
            # ⭐ **林縁は別の面・別の密度・別の丈**(2026-09-08 A-4/C-2)。高木は 0。
            n_rf.setdefault(lay, []).append(r.get({"中木": "chubokuRinen",
                                                   "低木": "teibokuRinen"}.get(lay), 0.0) or 0.0)
    n_i = dict((lay, _apportion(n_f[lay], int(math.floor(sum(n_f[lay]) + 0.5))))
               for lay in _LAYS)
    n_ir = dict((lay, _apportion(n_rf[lay], int(math.floor(sum(n_rf[lay]) + 0.5))))
                for lay in _LAYS)
    # ⭐ **塊の箱を候補セルから落とす**(2026-09-08 A-3)。⛔ 本数は既に差し引いてあるので
    #    面(`band_stats`)からは落とさない ── ここは**撒く場所**だけを外す。
    keep = cluster_keepout_shapes(d)
    # ⭐ **位置の決まった木を種として渡す**(A-2)── 塊の点と一本立ち。⛔ 帯より先に確定している
    #    ものを知らないまま撒かない(『別の帯・区どうし』が 229 対の全部だった)。
    seeded = {"canopy": [], "中木": [], "低木": []}

    def _bucket(lay): return "canopy" if lay in ("松", "落葉") else lay
    for q in cl_pts:
        seeded.setdefault(_bucket(q["layer"]), []).append((q["u"], q["v"]))
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            seeded.setdefault(_bucket(sg.get("layer") or "松"), []).append(tuple(sg["uv"]))
    # ⭐ **差し掛けの高木も位置が決まっている**(高2 庭方 2026-09-09 十七巡目)
    _SK9 = sashikake_rows(d, g)
    for sk in _SK9:
        seeded.setdefault(_bucket(sk.get("layer") or "落葉"), []).append((sk["u"], sk["v"]))
    # ⭐ **名指しの木も位置が決まっている**(決1③ 庭方 2026-09-09 十八巡目)
    for r9 in _NT9:
        seeded.setdefault(_bucket(r9.get("layer") or "落葉"), []).append((r9["u"], r9["v"]))
    bd_note, out = [], []
    HK = {"松": "matsuH", "落葉": "rakuyoH", "中木": "chubokuH", "低木": "teibokuH"}
    for lay in _LAYS:
        bk = _bucket(lay)
        for i, r in enumerate(rows):
            b = r["b"]
            bn = b["band"]
            if b.get("uv"):
                P = [(q[0], q[1]) for q in b["uv"]]
                step = 0.25
                src = list(poly_scan(P, step))
            else:
                step = d["planting"]["bandDef"]["stepKen"]
                src = list(cells[bn])
            sh = avoid_shapes(d, g, "obi4" if b.get("uv") else ("obi123:" + lay))
            cand = [p for p in src if not (sh and shape_hit(p, sh)) and not shape_hit(p, keep)]
            # ⭐ **間合いは高木にだけ効く**【指1 庭方 2026-09-09 十八巡目】── 測っているのは
            #    『同じ頭が二つ並ばないこと』なので、下層(中木・低木)は入ってよい。
            if lay in ("松", "落葉"): cand = [p for p in cand if not _in_gap(p)]
            # ⭐ **林縁は帯の中の小領域**(A-4)── 高木は本体だけ、中木・低木は両方(別の丈)
            rin = b.get("rinen") or {}
            E = rinen_edges(d, g, b) if rin else []
            cand_t = []
            if rin and E:
                rg = rinen_range(b, lay)          # ⭐ 高木は境から `toKen` まで全部(A-4)
                inr = dict((p, min(_pt_seg(p, q[0], q[1]) for q in E)) for p in cand)
                cand_r = [p for p in cand if rg[0] <= inr[p] <= rg[1]]
                cand = [p for p in cand if p not in set(cand_r)]
                # ⭐ **段ごとの候補**(④ 庭方 2026-09-09 十七巡目)
                for t in rinen_tiers(b):
                    rgt = rinen_range_t(b, t, lay)
                    cand_t.append((t, [p for p in cand_r if rgt[0] <= inr[p] <= rgt[1]]
                                   if rgt else []))
            else:
                cand_r = []
            # ⭐ **芯々の下限は『中央』で揃える**(2026-09-08 裁き4・庭方)。⛔ 高木だけ下端を使わない
            if lay in ("松", "落葉") and b.get("spacing"):
                sp = b["spacing"]
                rmin = (sp[0] + sp[1]) / 2.0 * pack / ken     # 宣言の芯々[m]の中央 × packRatio
            else:
                dens = {"中木": "chubokuPer100", "低木": "teibokuPer100"}.get(lay)
                q = (b.get(dens) or [0, 0]) if dens else [0, 0]
                dm = (q[0] + q[1]) / 2.0
                rmin = (math.sqrt(100.0 / dm) * pack / ken) if dm > 0 else step
            rnd, key = rnd_of("帯%d %s" % (bn, b["name"]), lay)
            n = n_i[lay][i] - cl_cut.get((bn, lay), 0)
            pts, r_, rx = _scatter_take(rnd, cand, max(0, n), rmin, seeded=seeded[bk])
            seeded[bk] += list(pts)
            for j, (u9, v9) in enumerate(pts):
                out.append(_tree_row(d, g, rnd, "帯%d_%s%04d" % (bn, lay, j + 1),
                                     "社叢 帯%d %s" % (bn, b["name"]), lay,
                                     pal[lay], b.get(HK[lay]), u9, v9))
            bd_note.append({"band": bn, "layer": lay, "seed": key, "want": n,
                            "got": len(pts), "cells": len(cand), "step": step,
                            "rmin": round(rmin, 4), "rminUsed": round(r_, 4), "relax": rx})
            # ---- 林縁(同じ層・別の面・**段ごとに別の密度と丈**)
            nr = n_ir[lay][i]
            if nr <= 0 or not cand_r: continue
            # ⭐ **段ごとの本数**は面 × その段の密度。⛔ 合算してから割らない(丸めが動く)。
            want_t = []
            for ti, (t, cs) in enumerate(cand_t):
                dr = rinen_dens_t(d, b, t, lay) or 0.0
                m2 = len(cs) * cell_tsubo(d, step) * TSUBO
                want_t.append(m2 * dr / 100.0)
            if not want_t:
                want_t, cand_t = [float(nr)], [({"name": "一段"}, cand_r)]
            # ⛔ **和を `nr` へ正規化してから配る** ── `_apportion` は最大剰余法なので、
            #   桶より余りが多いと配りきれない(⚠ 2026-09-09: 帯4 の一段へ 3 本のはずが 1 本しか
            #   配られず、焼き出しと予算表が 2 本食い違った)。⛔ 帯ごとの丸めと同じ轍を踏まない。
            tw9 = sum(want_t)
            n_t = _apportion([(w9 / tw9 * nr) if tw9 > 0 else (float(nr) / len(want_t))
                              for w9 in want_t], nr)
            jj = 0
            for ti, (t, cs) in enumerate(cand_t):
                if n_t[ti] <= 0 or not cs: continue
                dr = rinen_dens_t(d, b, t, lay) or 0.0
                rminr = (math.sqrt(100.0 / dr) * pack / ken) if dr > 0 else step
                ptsr, rr_, rxr = _scatter_take(rnd, cs, max(0, n_t[ti]), rminr,
                                               seeded=seeded[bk])
                seeded[bk] += list(ptsr)
                for (u9, v9) in ptsr:
                    jj += 1
                    out.append(_tree_row(d, g, rnd, "帯%d林縁_%s%04d" % (bn, lay, jj),
                                         "社叢 帯%d %s の林縁(%s)"
                                         % (bn, b["name"], t.get("name") or "一段"), lay,
                                         pal[lay], rinen_h_t(d, b, t, lay), u9, v9))
                bd_note.append({"band": bn, "layer": "%s(林縁 %s)" % (lay, t.get("name") or "一段"),
                                "seed": key, "want": n_t[ti], "got": len(ptsr),
                                "cells": len(cs), "step": step, "rmin": round(rminr, 4),
                                "rminUsed": round(rr_, 4), "relax": rxr})
    # ---- 帯の低木の面(区の植込み)と一本立ち ── 位置は指図が持つので**写すだけ**
    for gd in d["gardens"] + d["slopeBands"]:
        if gd.get("shrubs"):
            sh = gd["shrubs"]
            rnd, _k = rnd_of(gd["name"], "低木")
            for j, (u9, v9) in enumerate(island_shrubs(gd, ken)):
                out.append(_tree_row(d, g, rnd, "%s_低木%03d" % (gd["name"], j + 1),
                                     gd["name"], "低木", pal["低木"], sh.get("hM"), u9, v9))
        for sg in gd.get("singles", []):
            u9, v9 = sg["uv"]
            x9, z9 = g.W(u9, v9)
            dy = _design_y_cold(d, g, x9, z9)
            nat = dem_h(x9, z9)
            ln = single_lean(d, sg)
            # ⭐ **一本立ちにも `scaleXZ` を焼く**(2026-09-08 B-2)── 孤立木なので `isolatedXZ`
            _pf = single_prefab(d, sg)
            _kd = _LAY_KIND.get(sg.get("layer") or "")
            _xz = crown_scale_xz(d, _kd, _pf, sg.get("h"), iso=True) if _kd else None
            _cr = single_crown(d, sg)
            out.append({"name": sg["name"], "group": gd["name"] + "(一本立ち)",
                        "layer": sg.get("layer"), "species": sg.get("kind"),
                        "part": sg.get("part"), "prefab": _pf,
                        "size": None, "h": sg.get("h"), "scaleY": None,
                        "scaleXZ": (round(_xz, 4) if _xz is not None else None),
                        "crownM": (round(_cr * 2.0 * ken, 3) if _cr is not None else None),
                        "u": u9, "v": v9, "world": [round(x9, 3), round(z9, 3)],
                        "y": round(dy if dy is not None else (nat or 0.0), 3),
                        "ground": "design" if dy is not None else "terrain",
                        "place": (d["planting"]["plantRule"].get("placement") or {}).get("singles"),
                        "leanDeg": (ln[0] if ln else None),
                        "leanToward": (list(ln[1]) if ln and ln[1] else None),
                        "edaShita": sg.get("edaShita")})
    # ---- 名指しの木(位置は庭方の名指し・据え方は一本立ちと同じ GameObject)
    for r9 in _NT9:
        x9, z9 = g.W(r9["u"], r9["v"])
        dy = _design_y_cold(d, g, x9, z9)
        nat = dem_h(x9, z9)
        out.append({"name": r9["name"],
                    "group": ("★主景(区『%s』)" % r9.get("zone") if r9.get("shukei")
                              else "名指しの木(帯%s)" % r9.get("band")),
                    "layer": r9.get("layer"), "species": r9.get("kind"),
                    "part": r9.get("part"), "prefab": r9.get("prefab"),
                    "size": r9.get("size"), "h": r9.get("h"), "scaleY": r9.get("scaleY"),
                    "scaleXZ": r9.get("scaleXZ"), "crownM": r9.get("crownM"),
                    "u": r9["u"], "v": r9["v"],
                    "world": [round(x9, 3), round(z9, 3)],
                    "y": round(dy if dy is not None else (nat or 0.0), 3),
                    "ground": "design" if dy is not None else "terrain",
                    "place": (d["planting"]["plantRule"].get("placement") or {}).get("singles")})
    # ---- 差し掛けの高木(位置は宣言からの従属値・据え方は一本立ちと同じ GameObject)
    for sk in _SK9:
        x9, z9 = g.W(sk["u"], sk["v"])
        dy = _design_y_cold(d, g, x9, z9)
        nat = dem_h(x9, z9)
        g0 = part_geom({"prefab": sk.get("prefab")})
        xz = sk.get("scaleXZ")
        out.append({"name": sk["name"], "group": "差し掛け(%s)" % sk["of"],
                    "layer": sk.get("layer"), "species": sk.get("kind"),
                    "part": sk.get("part"), "prefab": sk.get("prefab"),
                    "size": sk.get("size"), "h": sk.get("h"), "scaleY": sk.get("scaleY"),
                    "scaleXZ": xz,
                    "crownM": (round(g0[0] * xz, 3) if (g0 and xz) else None),
                    "u": sk["u"], "v": sk["v"],
                    "world": [round(x9, 3), round(z9, 3)],
                    "y": round(dy if dy is not None else (nat or 0.0), 3),
                    "ground": "design" if dy is not None else "terrain",
                    "place": (d["planting"]["plantRule"].get("placement") or {}).get("singles"),
                    "kaidan": sk.get("kaidan"), "sM": sk.get("sM"), "side": sk.get("side")})
    return out + cl_pts, bd_note, cl_note


def sashikake_offset(d, sk, k):
    """差し掛けの**芯からの離れ**[間]。⛔ 数を持たない【決2① 庭方 2026-09-09 十八巡目】。

    = `kaidans[].wKen`/2 + `planting.bandDef.avoid.kaidanShoulderKen`[その層] の従属値。
    ⚠ 幹は敷きの縁から肩のぶんだけ退く = 擁壁の物理(肩の由来)そのもの。
    """
    if sk.get("offsetKen") is not None: return float(sk["offsetKen"])
    shk = ((d["planting"]["bandDef"].get("avoid") or {}).get("kaidanShoulderKen") or {})
    sh = shk.get(sk.get("layer"))
    if sh is None:
        raise SystemExit("差し掛け『%s』の肩(`kaidanShoulderKen`[%s])が引けない"
                         % (sk.get("name"), sk.get("layer")))
    return kaidan_wken(d, k) / 2.0 + float(sh)


def sashikake_xz(d, sk):
    """差し掛けの `scaleXZ`。⭕ **林縁木なので `scaleRule.isolatedXZ`**【決2② 庭方 十八巡目】。"""
    if sk.get("scaleXZFrom"):
        return d["planting"]["scaleRule"].get("isolatedXZ")
    return sk.get("scaleXZ")


def sashikake_rows(d, g):
    """**差し掛けの高木**(`planting.sashikake`)の据え所を組み立てる。

    ⭐ **位置は宣言からの従属値**【高2 庭方 2026-09-09 十七巡目】── 石段の折れ線の**弧長**を
      `n`+1 等分した内側 `n` 点で、芯から `offsetFrom`(敷きの半幅 + 肩)の法線上、
      **南(進行方向の右)のみ**【決2 庭方 2026-09-09 十八巡目】。
      ⛔ 弧長の数も座標も json に書かない(坂の折れ線が動けば追随する)。
    ⚠ **帯の密度からは出ない** ── 帯は面で撒くので、坂の脇という細い線には確率的にしか
      当たらない(実測 女坂の芯線 55 点中 樹冠に覆われるのは 3 点)。
    戻り [{name, kaidan, u, v, layer, kind, h, scaleXZ, part, prefab, side, sM}]。
    """
    out = []
    for sk in d["planting"].get("sashikake", []):
        k = ([q for q in d["kaidans"] if q["name"] == sk["kaidan"]] or [None])[0]
        if k is None: continue
        P = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        ken = d["const"]["ken"]
        L = [0.0]
        for i in range(len(P) - 1):
            L.append(L[-1] + math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) * ken)
        tot = L[-1]
        n = int(sk["n"])
        # 樹種の割り前(`mix`)を順に配る。⛔ 本数を別に持たない
        sp9 = []
        for kind, cnt in cluster_mix(sk):
            sp9 += [_MIXSP.get(kind, kind)] * int(cnt)
        pal = d["planting"]["parts"].get(sk["layer"]) or []
        for j in range(1, n + 1):
            s9 = tot * j / float(n + 1)
            seg = None
            for i in range(len(P) - 1):
                if L[i] <= s9 <= L[i + 1] + 1e-9: seg = i; break
            if seg is None: continue
            t9 = (s9 - L[seg]) / ((L[seg + 1] - L[seg]) or 1.0)
            u9 = P[seg][0] + (P[seg + 1][0] - P[seg][0]) * t9
            v9 = P[seg][1] + (P[seg + 1][1] - P[seg][1]) * t9
            du, dv = P[seg + 1][0] - P[seg][0], P[seg + 1][1] - P[seg][1]
            nn = math.hypot(du, dv) or 1.0
            nx9, nz9 = -dv / nn, du / nn                  # 法線(向きは次の行で南北へ揃える)
            # ⭐ **南のみ**【決2③ 庭方 2026-09-09 十八巡目 ── 十七巡目の『片側に寄せない』は
            #    撤回】。北隣は男坂の額縁で、交互にすると偶数番が `viewClusters` へ食い込む。
            # ⛔ **『進行方向の右』で決めない** ── 折れ線の向きが変われば右も変わる。
            #    ⭕ **南は v が小さくなる側**として法線そのものから決める(⛔ 符号を決め打ちしない)。
            #    ⚠ 旧式は左法線を『v が増える側 = 北』と決め打ちしており、⛔ **この坂では逆**で
            #    あった(据え位置が庭方の宣言した表と 2 × 離れ だけ食い違い、北側の額縁へ
            #    食い込んでいた)。
            s_south = -1.0 if nz9 > 0 else 1.0
            sgn = s_south if "南" in (sk.get("sides") or "") else -s_south
            if "交互" in (sk.get("sides") or ""):
                sgn = s_south if (j % 2) == 1 else -s_south
            sp = sp9[(j - 1) % len(sp9)] if sp9 else None
            cand = [pt for pt in pal if pt.get("species") == sp] or pal
            pt = cand[(j - 1) % len(cand)] if cand else None
            lo, hi = _h_pair(sk.get("h"))
            h9 = lo + (hi - lo) * ((j - 1) / float(max(1, n - 1))) if lo is not None else None
            q = pick_variant(d, pt, h9) if (pt and h9) else None
            off9 = sashikake_offset(d, sk, k)
            out.append({"name": "%s %02d" % (sk["name"], j), "of": sk["name"],
                        "kaidan": sk["kaidan"], "sM": round(s9, 3),
                        "side": ("南" if sgn * nz9 < 0 else "北"),
                        "u": round(u9 + nx9 * off9 * sgn, 4),
                        "v": round(v9 + nz9 * off9 * sgn, 4),
                        "layer": sk["layer"], "kind": sp, "h": (round(h9, 3) if h9 else None),
                        "scaleXZ": sashikake_xz(d, sk),
                        "part": (q[2] if q else (pt or {}).get("api")),
                        "prefab": (q[1] if q else (pt or {}).get("prefab")),
                        "size": (q[0] if q else None),
                        "scaleY": (round(q[3], 4) if q and q[3] else None)})
    return out


def band_at(d, g, u, v):
    """点 (u,v) が落ちる**帯**を同定する【決1③ 庭方 2026-09-09 十八巡目】。

    ⛔ **帯の番号を json に書かせない**ための一本 ── 名指しの木の丈は『その木が落ちる帯の
      `rakuyoH` の上端』という従属値なので、帯の同定は図の仕事である。
    ⭕ 帯4 は多角形、帯1〜3 は `band_scan` が刻んだセルの**最寄り**で決める。
    """
    b4 = d["slopeBands"][3]
    if b4.get("uv") and in_poly((u, v), [(q[0], q[1]) for q in b4["uv"]]): return b4
    cells, _sk = band_scan(d, g)
    step = d["planting"]["bandDef"]["stepKen"]
    best, bb = None, None
    for bn, ps in cells.items():
        for p in ps:
            dd = (p[0] - u) ** 2 + (p[1] - v) ** 2
            if best is None or dd < best: best, bb = dd, bn
            if dd <= (step * 0.75) ** 2: return [q for q in d["slopeBands"] if q["band"] == bn][0]
    if bb is None: return None
    return [q for q in d["slopeBands"] if q["band"] == bb][0]


def shukei_named(d):
    """**★主景の木を『名指しの木』として引く**【A-1 庭方 2026-09-09 十九巡目】。

    ⛔⛔ **区の塊の一本として撒くと、区の丈の範囲(`hBand` の `rakuyoH` / `matsuHMaxFrom`)が
      掛かって `shukei.tree.hMinFrom` を切り落とす。**⚠ 実測で丈は宣言より 4.22 m 低く、
      位置は名指しの点から 8.20 m 離れ、V3 からの仰角は西Aの木でいちばん低かった ──
      ⛔ **『★主景の検算』は宣言から計算した紙の上の数で、棟梁が読む焼き出しに対応物が無かった。**
    ⭕ 戻りは `planting.namedTrees.trees[]` と同じ形(`hMinFrom` を持つ点だけが違う)。
    """
    out = []
    for gd in d["gardens"]:
        sk = gd.get("shukei")
        if not sk or not sk.get("tree"): continue
        t = dict(sk["tree"])
        t["zone"] = t.get("zone") or gd["name"]
        out.append(t)
    return out


def named_tree_rows(d, g):
    """**名指しの木**(`planting.namedTrees` と ★主景)の据え所【決1③ 庭方 十八巡目 / A-1 十九巡目】。

    ⛔ 位置は庭方が名指しした (u,v) そのもの(意匠)。⭕ **丈・部材・樹冠は従属値** ──
      丈は `hFrom`(その木が落ちる帯の `rakuyoH` の上端)か `hMinFrom`(★主景 ── 落葉の
      最も高い変種の素の丈 × 箍)、大きさは `sizeRule` が丈から選ぶ。
    ⛔ 帯の番号も丈の数も json に書かない。
    """
    nt = ((d["planting"].get("namedTrees") or {}).get("trees") or []) + shukei_named(d)
    out = []
    for t in nt:
        u9, v9 = t["uv"]
        lay = t.get("layer") or "落葉"
        hk = {"松": "matsuH", "落葉": "rakuyoH", "中木": "chubokuH", "低木": "teibokuH"}[lay]
        if t.get("hMinFrom"):
            # ⭐ ★主景 ── **丈は帯からではなく `hMinFrom` から**(⛔ 区の丈の範囲を掛けない)
            b = None
            h9 = shukei_hmin(d, {"tree": t})
        else:
            b = band_at(d, g, u9, v9)
            rng = (b or {}).get(hk)
            h9 = _h_pair(rng)[1] if rng else None
        pal = [q for q in (d["planting"]["parts"].get(lay) or [])
               if q.get("species") == t.get("kind")]
        pt = pal[0] if pal else None
        if h9 is not None and pt is not None:
            cap = species_h_cap(d, pt)
            if cap is not None: h9 = min(h9, cap)
        q = pick_variant(d, pt, h9) if (pt and h9) else None
        kind = _LAY_KIND.get(lay)
        xz = (d["planting"]["scaleRule"].get("isolatedXZ")
              if t.get("scaleXZFrom") else None)
        g0 = part_geom({"prefab": (q[1] if q else (pt or {}).get("prefab"))})
        out.append({"name": t["name"], "of": ("★主景" if t.get("hMinFrom") else "名指しの木"),
                    "shukei": bool(t.get("hMinFrom")),
                    "zone": t.get("zone"), "band": (b or {}).get("band"),
                    "hSrc": ("`hMinFrom`(落葉の最も高い変種の素の丈 × 箍)"
                             if t.get("hMinFrom") else "帯の `%s` の上端" % hk),
                    "u": u9, "v": v9, "layer": lay, "kind": t.get("kind"),
                    "h": (round(h9, 3) if h9 else None), "scaleXZ": xz,
                    "part": (q[2] if q else (pt or {}).get("api")),
                    "prefab": (q[1] if q else (pt or {}).get("prefab")),
                    "size": (q[0] if q else None),
                    "scaleY": (round(q[3], 4) if q and q[3] else None),
                    "crownM": (round(g0[0] * xz, 3) if (g0 and xz) else None),
                    "role": t.get("role")})
    return out


def _design_y_cold(d, g, x, z):
    """`design_y` を**呼び出し順に依存しない形**で引く(焼き出しの定義)。

    ⭐ **揺れは根で消えた**【裁定 2026-09-19 = 案A】── 法面は `cone_field` が**一度だけ解く
      一枚の面**で、点ごとの ray も、その答えを覚える `slope_lands`/`_LAND` も無い。⇒
      `design_y` は構造として呼び出し順に依らない。
    ⛔ **それでも測るのはやめない**(規則19 — 直したから測るのをやめる、をしない)── 一致は
      `graded.orderDrift` が毎回全セルで測り、⛔ 一セルでも食い違えば検査が止める。
    """
    return design_y(d, g, x, z)


# ---------------------------------------------------------------- 格子へ焼くときの縁の作法
#   ⛔ **面の輪郭が格子の隙に落ちると、その帯は造成されない**【K060 2026-09-16 棟梁の差し戻し】。
#   実装(`EdoSannoShaRebuild.Graded.Bilinear`)は**四隅がそろった枡の中でしか読まない**ので、
#   輪郭が最外の節点より外にあると、輪郭沿いの帯が現地形のまま残る。
#   ⭐ **2026-09-19 ユーザー裁定〈造成の縁〉1 = 案A** ── 旧『**帯**』(輪郭の外 格子の刻みぶんを**面の高さ**で
#   保つ作法)と、その外を独自の法勾配 1:0.7 で降ろす作法は、**両方とも廃した**。縁は三つしかない:
#     ① **`design_y`** ── 法面は**縁から外へ広がる一枚の土の面**(円錐)で、`const.batterFill`
#        1:1.5 / `batterCut` 1:1.0 を**土留めを障害物とした測地距離**に掛けて降ろす
#        (⛔ 『輪郭から直に』ではない ── 名乗りを古いままにしない〔庭方 低 2026-09-19〕。
#         ⛔ 帯のぶん外へ押し出さない。土量・切盛図・断面と**同じ一つの式**)
#     ② **壁の控え** ── 土留めが受ける縁だけ、面の高さを**壁の外面まで**保つ
#        (`terrainCheck.gradedCover.wallCollarM`)。その外へは書かない ── ⛔ **見付を埋めない**
#     ③ **平接ぎ** ── 造成の域の外へ**一節点だけ現地形の高さ**を書く(Δ=0)。⭕ 輪郭の枡を閉じる
#        **だけ**の作法で、⛔ **土は一粒も動かない**(⛔ 格子の都合を土で辻褄合わせしない)
#   ⛔ 輪郭そのものを縮めて辻褄を合わせない。⛔ `design_y` が値を持つ節点は上書きしない。
#   ⛔ 社地の外へは出さない。⚠ ②③は**格子へ焼くときだけ** ── `design_y` は動かさない。
#   ⚠ **格子(1 m)も実装の地形(2 m テクセル)も垂直面を持てない** ⇒ 土留めが受ける縁で地盤が
#     天端から法尻へ落ちるのは**一枡の斜路**になる。⭕ 図が約束するのは「**その斜路を一枡より外へ
#     出さない**」ことだけで(検査『格子の縁が一枡より外へ土を持ち出していないか』)、⛔ 土で解かない。
GRADE_REACH = IMPL_STEP          # 平接ぎの幅[m] ── ⛔ 新しい数を作らない(格子の刻みそのもの)


_GPOLY = {}


_DYC = {}


def _dyc(d, g, x, z):
    """`_design_y_cold` の覚え書き ── ⛔ 平接ぎの八方の当たりで同じ点を何度も引き直さない。
    ⚠ **理由を撤回済みの機構で書かない**【検図 低 2026-09-19】── 旧文は「`slope_lands` の
      覚え書きを捨てるので」と書いていたが、`slope_lands`/`_LAND` は裁定 2026-09-19 = 案A で
      **無くなっている**。⭕ いま重いのは `design_y` そのもの(面の内外の判定と円錐の読み)で、
      平接ぎは一点あたり八方 + 段差の当たりで同じ点を何度も引くため。
    ⭕ 返す値そのものは `_design_y_cold` と同じ(冷えた値 ── 焼き出しの定義)。"""
    if _DYC.get("key") != id(d):
        _DYC.clear(); _DYC["key"] = id(d)
    k = (round(x, 3), round(z, 3))
    if k not in _DYC: _DYC[k] = _design_y_cold(d, g, x, z)
    return _DYC[k]


def _terrace_polys(d, g):
    """平場の輪郭(世界座標)と外接矩形を覚える。⛔ 55,660 セルの走査で毎回作らない。"""
    if _GPOLY.get("key") != id(d):
        v = []
        for te in d["terraces"]:
            P = terrace_poly(te, g)
            xs = [q[0] for q in P]; zs = [q[1] for q in P]
            v.append((te, P, (min(xs), min(zs), max(xs), max(zs))))
        _GPOLY["key"] = id(d); _GPOLY["v"] = v
    return _GPOLY["v"]


def _poly_near(x, z, P):
    """点から多角形の辺までの**最短距離とその最寄りの点**。⛔ 距離だけを返す版と二重に書かない。"""
    best = (1e9, None)
    for i in range(len(P)):
        ax, az = P[i]; bx, bz = P[(i + 1) % len(P)]
        ddx, ddz = bx - ax, bz - az
        L2 = ddx * ddx + ddz * ddz or 1.0
        t = max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
        qx, qz = ax + ddx * t, az + ddz * t
        dd = math.hypot(x - qx, z - qz)
        if dd < best[0]: best = (dd, (qx, qz))
    return best


def _poly_dist(x, z, P):
    """点から多角形の辺までの最短距離。"""
    return _poly_near(x, z, P)[0]


def wall_collar_m(d):
    """**壁の控え**[m] ── 土留めが受ける縁で面の高さを保つ幅(壁の線から外へ = 石垣の見込み)。

    ⛔ ここで数を作らない ── 正典は `terrainCheck.gradedCover.wallCollarM`
    (断面が土留めを描く厚み `WALL_T` と**同じ量**。⛔ 同じ量に二つの正典を置かない・規則4)。
    """
    v = ((d.get("terrainCheck") or {}).get("gradedCover") or {}).get("wallCollarM")
    return None if v is None else float(v)


_CTOP = {}


def wall_near_tg(d, g, x, z):
    """その点に**いちばん近い土留め**と、そこでの (天端, 低い側の地盤)。⛔ 物差しは `wall_tg_at`。

    ⚠ 控えと天端が同じ問い合わせを二度するので、丸めた座標で憶える(⛔ 値は作らない)。
    """
    if _CTOP.get("key") != id(d):
        _CTOP.clear(); _CTOP["key"] = id(d)
    k = ("tg", round(x, 3), round(z, 3))
    if k in _CTOP: return _CTOP[k]
    w = wall_near_named(d, g, x, z)[0]
    v = (None, None, None) if w is None else ((w,) + tuple(wall_tg_at(d, g, w, x, z)[:2]))
    _CTOP[k] = v
    return v


def collar_top(d, g, x, z, te):
    """**壁の控えの天端**[m] ── その節点を受ける土留めの**天端そのもの**(⛔ 平場の `y` ではない)。

    ⭐ **2026-09-19 検図 高1** ── 旧図はここに `te["y"]` を書いた。平らな平場を受ける壁ならそれで
      合うが、⛔ **`coping:"stair"` の側壁**(男坂・女坂・参道の階)は天端が段なりに上がるので、
      石段の脇 0.03〜1.2 m の節点に**階の頂の高さ**が入り、一枡幅の土の背が立った。
    ⭕ 天端は **`wall_top_at`**(`coping` が数ならその数、`"stair"` なら `stair_spans` の割付、
      `copingRise:"groundHi"` なら高い側の地盤まで)から採る ── ⛔ ここで段を割り直さない(規則4)。
    ⚠ 受ける壁が見つからないときだけ平場の `y`(= 旧の作法)へ落ちる。
    """
    w, top, _glo = wall_near_tg(d, g, x, z)
    return float(te["y"]) if w is None else float(top)


def ridge_keep_m():
    """**均しが手を付けない法肩の帯**[m] ── 輪郭からこの距離の内の節点は落とさない。

    ⭐ **法肩の丸みを落とさないため**【K108 2026-09-19 → ユーザー裁定で決着】── 実装は格子の
      **双一次**で読むので、輪郭に接する枡の節点を落とすと**法肩そのものが下がる**(旧版で
      射程を広げた初回、『法肩の丸み』が上限に対し 0.794 m で鳴った)。
      ⛔ 丸みの上限はユーザー裁定〈法尻と法肩〉2 で**従属値のまま**と決まっている。
    ⭕ **帯は均さないままでよい**【ユーザー裁定 2026-09-19 ── 庭方の答えを施主が採った】── 帯の
      中の落ちは 1 枡で 0.43 m = 1:2.3 で、**設計の法 1:1.5 より緩い** ⇒ **超過ではない**。
      ⛔ この件で `_pending` を立てない(2026-09-19 に畳んだ)。
    ⛔ 新しい物差しを作らない ── 丸みの上限を導いた**枡の対角** √2 × `IMPL_STEP` そのもの。
    ⚠ 帯の中に超過が残るなら、それは**均しの対象外**として別に数えて刷る(⛔ ⛔にも 0 にもしない)。
    """
    return math.sqrt(2.0) * IMPL_STEP


def _grade_reach(d, g=None):
    """縁の作法の走査が届く幅[m] ── **円錐の届きの実測** + 平接ぎの一枡 + 控えの上限。

    ⭐ **宣言値ではない**【裁定 2026-09-19 = 案A】── 旧版は `const.featherCap` 12 m という
      **作図の打ち切り**を走査幅に使っており、⛔ 同じ一つの数が「法面をどこで切るか」と
      「どこまで数えるか」の両方を決めていた。⇒ 円錐は自分で止まるので、走査幅は
      **解いた面から測った届き**(`cone_reach_m`)に一枡ぶんの余白を足して取る。
    """
    return (cone_reach_m(d, g) + 2.0 * IMPL_STEP + GRADE_REACH * math.sqrt(2.0)
            + (wall_collar_m(d) or 0.0))


def _grade_pick(d, g, x, z):
    """その節点を受け持つ**面**と輪郭までの距離・最寄りの点。戻り (te, P, 距離, 最寄りの点)。"""
    reach = _grade_reach(d, g)
    best = None
    for te, P, bb in _terrace_polys(d, g):
        if x < bb[0] - reach or x > bb[2] + reach: continue
        if z < bb[1] - reach or z > bb[3] + reach: continue
        dd, near = _poly_near(x, z, P)
        if dd > reach or near is None: continue
        if best is None or dd < best[0]: best = (dd, (te, P, dd, near))
    return best[1] if best else None


_GRADE = {}


def grade_rule(d, g, x, z, cold=True):
    """**格子へ焼く設計面の作法**── 戻り (高さ, 空である理由, 縁の別)。⭕ 図・焼き出し・検査・
    切盛図はすべてこの一つから出る(規則4・規則19)。作法そのものは上の見出しの ①②③。
    """
    if _GRADE.get("key") != id(d):
        _GRADE.clear(); _GRADE["key"] = id(d)
    k = (round(x, 3), round(z, 3), bool(cold))
    v = _GRADE.get(k)
    if v is None:
        v = _grade_rule(d, g, x, z, cold); _GRADE[k] = v
    return v


def _grade_rule(d, g, x, z, cold=True):
    y = _dyc(d, g, x, z) if cold else design_y(d, g, x, z)
    if y is not None: return (y, None, "design_y")
    pick = _grade_pick(d, g, x, z)
    if pick is None: return (None, "縁の作法の外(面から遠い)", None)
    te, P, dd, near = pick
    # ⚠ **社地でのクリップは掛けない**【2026-09-19】── `design_y` の法面は元から社地の境で
    #   切っておらず(法尻は着く所まで行く)、縁の作法だけ切ると**同じ縁が二つの規則で動く**。
    #   ⛔ 規則4。⭕ 造成が社地の外へ出ること自体は裁定済(`_pending`)で、面積と土量は
    #   検査『造成が社地の外へ及んでいないか』と切盛図の欄『うち社地外』が毎回刷る。
    # ② **壁の控え** ── 土留めが受ける縁。面の高さを保つのは**壁の外面まで**
    why9 = "造成の域の外(現地形のまま = 社叢の山肌)"
    if on_wall(d, g, near[0], near[1]):
        # ⚠ **控えは宣言のまま**(⛔ 指図方が作法を変えない)── 見付からの従属値へ改める案は
        #   考証 中 2026-09-19 の差し戻しだが、控えの帯には**天端**が書かれるので、広げると
        #   その分だけ**見付が埋まる**(**〈造成の縁〉1** の⛔・実測 3 点 最大 1.20 m)。⇒ 事実と実測を
        #   `_pending`「壁の控えが石垣の基部の出を覆っていない」に記録し、**普請奉行の裁定**へ。
        wc = wall_collar_m(d)
        if wc is None: return (None, "壁の控えの宣言が無い", None)
        # ⚠ **控えは『壁の線から』と『輪郭から』の両方で測る** ── 土留めの線は壁体の**芯**で、
        #   平場の輪郭は壁のどちら側にも寄りうる。片方だけで測ると、輪郭が芯より外へ出ている所で
        #   **平場の縁そのものが控えから外れ**、地盤が壁の足元で天端から法尻へ落ちる(回廊の基壇の
        #   北で 4.0 m 落ちていた ── 石垣が宙に浮く)。
        # ⭐ 天端は**その壁の天端**から採る(`collar_top`)── ⛔ 平場の `y` を書かない(検図 高1)
        if _wall_dist(d, g, x, z) <= wc or dd <= wc:
            return (collar_top(d, g, x, z, te), None, "壁の控え")
        # ⛔ **壁の外面の外へ面の高さを持ち出さない**(見付が埋まる)。⭕ ただし③の平接ぎは出す
        #   ── 出さないと枡が閉じず、実装が `Near` で**平場の高さを壁の外へ持ち出す**
        #   (= 同じ埋没が、図の数に出ない形で起きる。⛔ 図が閉じない枡を実装へ押し付けない)。
        why9 = "土留めが受ける縁(壁の外面の外 ── ⛔ 見付を埋めない)"
    nat = dem_h(x, z)
    if nat is None: return (None, "現地形が無い", None)
    # ③ **平接ぎ** ── 造成の域に隣り合う一節点だけ、現地形の高さを書く(Δ=0・土は動かない)
    s9 = GRADE_REACH
    for dx, dz in ((s9, 0), (-s9, 0), (0, s9), (0, -s9),
                   (s9, s9), (s9, -s9), (-s9, s9), (-s9, -s9)):
        if _graded_core(d, g, x + dx, z + dz): return (nat, None, "平接ぎ")
    if dd <= s9 * math.sqrt(2.0): return (nat, None, "平接ぎ")
    return (None, why9, None)


def _graded_core(d, g, x, z):
    """その節点が**造成の域**(① `design_y` か ② 壁の控え)か ── 平接ぎの当たり。

    ⛔ `grade_rule` を呼び返さない(平接ぎが平接ぎを呼んで際限なく広がる)。⭕ 判定は作法の
      ①②をここで**そのまま**当てる ── ⛔ 規則を書き直さない。
    ⭐ **壁の外にも平接ぎを出す**【2026-09-19】── 出さないと壁の外の枡が閉じず、実装は
      `Near`(1 セル以内の最寄り)で**平場の高さを壁の外へ持ち出す** = 見付が埋まる。
      ⭕ 現地形をそのまま書けば枡が閉じ、⛔ 土は一粒も動かない。
    """
    if _dyc(d, g, x, z) is not None: return True
    wc = wall_collar_m(d)                        # ⛔ ①②の判定を書き直さない(同じ宣言)
    if wc is None: return False
    pick = _grade_pick(d, g, x, z)
    if pick is None: return False
    return (on_wall(d, g, pick[3][0], pick[3][1])
            and (_wall_dist(d, g, x, z) <= wc or pick[2] <= wc))


_LEVEL = {"key": None, "busy": False, "h": {}, "map": {}, "cells": [], "runs": [],
          "iter": 0, "left": [], "leftAt": None, "stuck": 0, "nat": 0, "pits": 0,
          "natCells": [], "natRuns": [], "natBy": {}}


_NB8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


LEVEL_POOL_M = 0.05      # 凹みの深さの敷居[m]【U 当方の作法値 ── 格子の丸めの幅】


_LEVEL_EPS = 0.001       # 抜け道に付ける勾配[m/枡] ── ⛔ 設計値ではない(0 除算よけ)


def _flood(E, seeds):
    """**優先度洪水** ── 各節点に『水が溜まる高さ』と、そこへ水を通した隣(親)を与える。

    ⭕ 親を辿ると**必ず外(排水口)へ出る**ので、凹みの縁のどこを抜けば水が落ちるかが決まる。
    """
    W, par, hp = {}, {}, []
    for k in seeds:
        W[k] = E[k]; heapq.heappush(hp, (E[k], k))
    heapq.heapify(hp)
    while hp:
        w, k = heapq.heappop(hp)
        if w > W.get(k, 1e18) + 1e-12: continue
        for dx, dz in _NB8:
            q = (k[0] + dx, k[1] + dz)
            if q not in E or q in W: continue
            W[q] = max(w, E[q]); par[q] = k
            heapq.heappush(hp, (W[q], q))
    return W, par


def ridge_level(d, g):
    """**④ 水の抜けない凹みを抜く**【ユーザー裁定〈法尻と法肩〉1 2026-09-19 = 案①『均す』。
    物差しは 2026-09-19 に**幅(枡)から『溜まるか』へ入れ替えた**(庭方の答え)】。

    ⭐ **なぜ幅をやめたか** ── 旧版は「向かい合う一対がどちらも低い節点」を土手と数え、その幅の
      上限を `const.ridgeLevelSpanCells`【U 当方の作法値】で切っていた。⛔ **幅を広げれば必ず
      法面そのものを拾う**(実測 幅6枡で 73 点・落差 1.32 m)ので収束せず、⛔ どこで切るかを
      施主に問うしかなくなっていた。⭕ 裁定〈法尻と法肩〉1 の理由は**見えではなく水**である ⇒
      物差しは『**溜まるか**』でなければならない。⇒ 射程は自動で決まり、凹みが消えれば必ず止まる。
    ⭕ **均すのは水の抜けない節点だけ** ── まわり八方が全部高い閉じた凹み(深さ `LEVEL_POOL_M`
      を超える所)を見つけ、**その縁の抜け道を落として**水を落とす。⛔ 土を足す方向には効かない。
    ⛔ **平場・石段・法肩の帯は動かさない**(`ridge_keep_m` ── 輪郭に接する枡を落とすと実装の
      双一次が**法肩そのものを下げる**。ユーザー裁定〈法尻と法肩〉2 の丸みの上限を破る)。
    ⭕ **帳簿**は `cells`(落とした枡)/ `runs`(条)/ `left`(残った凹み)/ `stuck`(抜き道が
      動かせない節点に塞がれた凹み)/ `nat`(**現地形そのものの凹み** ── 当図の土ではない)。
    """
    if _LEVEL.get("key") == id(d): return _LEVEL
    _LEVEL["key"] = id(d); _LEVEL["busy"] = True
    _LEVEL["h"] = {}; _LEVEL["map"] = {}; _LEVEL["cells"] = []; _LEVEL["runs"] = []
    _LEVEL["iter"] = 0; _LEVEL["left"] = []; _LEVEL["leftAt"] = None
    _LEVEL["stuck"] = 0; _LEVEL["nat"] = 0; _LEVEL["pits"] = 0
    # ⛔ **帳簿を初期化し忘れない**【検図 高 / 考証 高 / 庭方 高 2026-09-19】── 旧版は
    #   `natCells`/`natRuns`/`natBy` だけ初期化せず、⛔ 破壊試験が別の `d` で呼ぶたびに
    #   **積み上がった**。⇒ 同じ一つの集計を名乗る切盛図(110 枡)と検査(95 枡)が別の数を
    #   刷っていた(規則4)。⭕ 三つとも毎回空にする。
    _LEVEL["natCells"] = []; _LEVEL["natRuns"] = []; _LEVEL["natBy"] = {}
    try:
        H, MOV, INFO = {}, set(), {}
        reach = _grade_reach(d, g)
        seen = set()
        for te, P, bb in _terrace_polys(d, g):
            i0 = int(math.floor((bb[0] - reach) / IMPL_STEP)) - 1
            i1 = int(math.ceil((bb[2] + reach) / IMPL_STEP)) + 1
            j0 = int(math.floor((bb[1] - reach) / IMPL_STEP)) - 1
            j1 = int(math.ceil((bb[3] + reach) / IMPL_STEP)) + 1
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    if (i, j) in seen: continue
                    x, z = i * IMPL_STEP, j * IMPL_STEP
                    if any(in_poly((x, z), P2) for _t2, P2, _b2 in _terrace_polys(d, g)): continue
                    y, w9, kind = grade_rule(d, g, x, z)
                    if y is None and w9 == "縁の作法の外(面から遠い)": continue
                    seen.add((i, j))
                    if y is None: continue
                    H[(i, j)] = y
                    pk9 = _grade_pick(d, g, x, z)
                    nat9 = dem_h(x, z)
                    INFO[(i, j)] = ((0.0 if nat9 is None else y - nat9),
                                    te["name"] if pk9 is None else pk9[0]["name"])
                    if (kind == "design_y" and _stair_y(d, g, x, z) is None
                            and pk9 is not None and pk9[2] > ridge_keep_m()):
                        MOV.add((i, j))
        # ---- 走査の箱 ── 造成の域を 2 枡ぶん広げ、外周は**排水口**(水はそこから落ちる)
        if H:
            ii = [k[0] for k in H]; jj = [k[1] for k in H]
            i0, i1 = min(ii) - 2, max(ii) + 2
            j0, j1 = min(jj) - 2, max(jj) + 2
        else:
            i0 = i1 = j0 = j1 = 0
        E, edge = {}, set()
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                k = (i, j)
                if k in H: E[k] = H[k]; continue
                x, z = i * IMPL_STEP, j * IMPL_STEP
                y9, _w9, _k9 = grade_rule(d, g, x, z)
                if y9 is None: y9 = dem_h(x, z)
                if y9 is None: continue
                E[k] = y9
        for k in E:
            if (k[0] in (i0, i1) or k[1] in (j0, j1)
                    or any((k[0] + dx, k[1] + dz) not in E for dx, dz in _NB8)):
                edge.add(k)
        drop, stuck, natp = {}, set(), set()
        lim9 = 200
        for it in range(lim9):
            W, par = _flood(E, edge)
            pits = sorted(((W[k] - E[k], k) for k in E
                           if k in H and (W.get(k, E[k]) - E[k]) > LEVEL_POOL_M),
                          key=lambda t: -t[0])
            pits = [p for p in pits if p[1] not in stuck and p[1] not in natp]
            _LEVEL["pits"] = max(_LEVEL["pits"], len(pits))
            if not pits:
                _LEVEL["iter"] = it
                break
            moved = 0
            for _dp, p in pits:
                if (W[p] - E[p]) <= LEVEL_POOL_M: continue
                path, k = [], par.get(p)
                ok, anymov = True, False
                while k is not None and E[k] >= E[p] - 1e-9:
                    if k in MOV: anymov = True
                    else: ok = False; break
                    path.append(k); k = par.get(k)
                    if len(path) > 64: ok = False; break
                if not ok or not path:
                    # ⚠ **抜き道が動かせない** ── 何が塞いでいるかまで控える(⛔ 一語で畳まない)
                    blk, k2 = "現地形", par.get(p)
                    while k2 is not None and E[k2] >= E[p] - 1e-9 and k2 not in MOV:
                        if k2 not in H: blk = "造成の域の外(現地形)"; break
                        y3, _w3, k3 = grade_rule(d, g, k2[0] * IMPL_STEP, k2[1] * IMPL_STEP)
                        if _stair_y(d, g, k2[0] * IMPL_STEP, k2[1] * IMPL_STEP) is not None:
                            blk = "石段の帯"; break
                        if k3 == "壁の控え": blk = "土留めの控え"; break
                        if k3 == "平接ぎ": blk = "平接ぎ(Δ=0 = 現地形)"; break
                        blk = "法肩の帯(輪郭に接する枡)"; break
                    if anymov: stuck.add(p)
                    else:
                        natp.add(p)
                        _LEVEL["natBy"][blk] = _LEVEL["natBy"].get(blk, 0) + 1
                    continue
                for n9, kk in enumerate(path):
                    tgt = E[p] - _LEVEL_EPS * (n9 + 1)
                    if E[kk] > tgt:
                        drop[kk] = drop.get(kk, 0.0) + (E[kk] - tgt)
                        E[kk] = tgt; moved += 1
            if not moved:
                _LEVEL["iter"] = it
                break
        else:
            raise SystemExit("⛔ 凹みの均しが %d 巡で収束しない" % lim9)
        W, _par = _flood(E, edge)
        for k in H:
            if (W.get(k, E.get(k, 0.0)) - E.get(k, 0.0)) <= LEVEL_POOL_M: continue
            dp9 = W[k] - E[k]
            c9 = (k[0] * IMPL_STEP, k[1] * IMPL_STEP, dp9,
                  INFO.get(k, (0.0, "?"))[0], INFO.get(k, (0.0, "?"))[1])
            # ⚠ **均しで抜けない凹みは⛔ にしない** ── 均しは**落とすだけ**の作法で、抜き道が
            #   平場・石段・法肩の帯・現地形なら一節点も動かせない。⛔ 0 に畳まず別に数えて刷る。
            if k in natp:
                _LEVEL["natCells"].append(c9); continue
            _LEVEL["left"].append(c9)
            if _LEVEL["leftAt"] is None or dp9 > _LEVEL["leftAt"][3]:
                _LEVEL["leftAt"] = (c9[0], c9[1], c9[4], dp9)
        _LEVEL["stuck"] = len(stuck); _LEVEL["nat"] = len(natp)
        _LEVEL["natRuns"] = _ridge_runs(_LEVEL["natCells"])
        for k, r9 in drop.items():
            if k not in H: continue
            H[k] = E[k]
            _LEVEL["map"][k] = E[k]
            _LEVEL["cells"].append((k[0] * IMPL_STEP, k[1] * IMPL_STEP, r9,
                                    INFO.get(k, (0.0, "?"))[0], INFO.get(k, (0.0, "?"))[1]))
        _LEVEL["h"] = H
        _LEVEL["runs"] = _ridge_runs(_LEVEL["cells"])
    finally:
        _LEVEL["busy"] = False
    # ⛔ **素の値を覚え書きに残さない** ── 均す前に引いた値が居座ると、図と焼き出しで別の
    #    地面が出る(規則4)。⇒ 帽子が載った後で全部引き直させる。
    _DYC.clear(); _GRADE.clear(); _COLLAR.clear(); _IMPLR.clear()
    return _LEVEL


def _level_cap(d, g, x, z):
    """**均しの帽子**[m] ── その点を囲む枡の四隅に均した節点があれば、格子の**双一次**で
    読んだ高さを返す(⛔ 無ければ None = 設計面に触らない)。

    ⭐ **枡の中まで効かせる理由**【2026-09-19】── 均しを節点だけに効かせると、⛔ **断面と
      切盛図は `design_y` を半刻みで引くので土手が絵から消えない**(帳簿だけ減って図が前のまま)。
      ⭕ 実装が建てるのは格子の双一次そのものなので、枡の中もそれで読めば図と地面が一致する。
    ⛔ 均していない枡には一切触らない ── 帽子は畝の周り一枡にだけ載る。
    """
    if _LEVEL.get("busy"): return None
    L = ridge_level(d, g)
    if not L["map"]: return None
    i0 = int(math.floor(x / IMPL_STEP)); j0 = int(math.floor(z / IMPL_STEP))
    ks = ((i0, j0), (i0 + 1, j0), (i0, j0 + 1), (i0 + 1, j0 + 1))
    if not any(k in L["map"] for k in ks): return None
    v = []
    for k in ks:
        h9 = L["h"].get(k)
        if h9 is None: h9 = dem_h(k[0] * IMPL_STEP, k[1] * IMPL_STEP)
        if h9 is None: return None
        v.append(h9)
    tx = x / IMPL_STEP - i0; tz = z / IMPL_STEP - j0
    return ((v[0] * (1 - tx) + v[1] * tx) * (1 - tz)
            + (v[2] * (1 - tx) + v[3] * tx) * tz)


def graded_y(d, g, x, z, cold=True):
    """**格子へ焼く設計面**── `design_y` に縁の作法(壁の控え・平接ぎ)を重ねた物(`grade_rule`)。

    ⭐ **図と焼き出しは同じこの関数から出る**(規則19)── `graded_grid` が焼き、
      `impl_graded_check` が全セル引き直して突き合わせるのはどちらもここ。
    ⛔ `design_y` を動かさない ── 縁の作法が効くのは `design_y` が値を持たない節点だけ。
    """
    return grade_rule(d, g, x, z, cold)[0]


_COLLAR = {}


_IMPLR = {}


def _wall_dist(d, g, x, z):
    """その点から**土留めの線**までの最短距離[m](⛔ 受けているか否かの閾は `on_wall` が持つ)。"""
    best = 1e9
    for (ax, az), (bx, bz) in wall_segs_world(d, g):
        ddx, ddz = bx - ax, bz - az
        L2 = ddx * ddx + ddz * ddz or 1.0
        t = max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
        best = min(best, math.hypot(x - (ax + ddx * t), z - (az + ddz * t)))
    return best


def _outward(P, i, x, z):
    """多角形 P の辺 i の上の点 (x,z) での**外向きの単位法線**。⛔ 向きを決め打ちしない。"""
    ax, az = P[i]; bx, bz = P[(i + 1) % len(P)]
    L = math.hypot(bx - ax, bz - az) or 1.0
    nx, nz = (bz - az) / L, -(bx - ax) / L
    if in_poly((x + nx * 0.25, z + nz * 0.25), P): nx, nz = -nx, -nz
    return nx, nz


def _ridge_runs(cells):
    """**畝を連なりへ束ねる**【K099 検図 高 2026-09-19】── 畝の枡 (x, z, 畝の高さ, 盛土の厚み, 面名)
    を**隣り合う枡(斜めを含む 8 近傍)**で連結成分にまとめ、連なりごとに

        (点数, 走り[m], 幅[m], 畝の高さの最大[m], 盛土の厚みの最大[m], 盛土の厚みの和[m³],
         端[A], 端[B], 面名, 端点間の直距離[m], **落とす土**[m³], 切土の中の高まりか, 芯の折れ線)

    を**落とす土 [10](= Σ 畝の高さ)の大きい順**で返す【考証 中 2026-09-19】。
    ⛔ **刷らない量で並べ替えない** ── 旧版は [5](盛土の厚みの和)で並べながら、欄は走り [1] と
      落とす土 [10] を刷っていたので、『最大』と名乗る一条の走りが総走りと算が合わなかった
      (22 m / 8 条に対し『最大』が 2 m)。⇒ ⭕ **鍵は刷る量に合わせ**、選んだ基準を銘に名乗る。

    ⛔ **物差しと工事を取り違えない**【検図 中 / 考証 中 2026-09-19】── [5] は Σ(盛土の厚み)で
      **現地形からの盛り全部**(畝の下の盛土を含む)、[10] は Σ(畝の高さ)で**案①が両隣の高さへ
      落とす土**そのもの。⛔ 一方だけを『土量』と名乗らせない ── 欄は両方を並べて刷る。
    ⚠ **走り [1] = 点数 × 刻み**は一枡幅の直線でしか実延長にならない ── 斜めに継いだ条では
      過大に、塊では過小に出る ⇒ [9] **端点間の直距離**を必ず併記する(⛔ 片方だけ刷らない)。
    ⚠ [11] が真の条は盛土の厚みが負(= **切土の中の高まり**)で、そこの案①は『土手を落とす』
      ではなく『**削る**』工事である(庭方 低 2026-09-19)。

    ⭐ **なぜ束ねるのか** ── 点の数と最大だけを刷ると、⛔ 施主は『一枡の点がばらばらに残る』と
      読む。実体は**一枡幅で連なる土手**で、①『均す』はその走りの分の土を落とす工事である。
    ⭕ **走り** = 点数 × 刻み(一枡幅の列なので枡の数がそのまま延長)。**幅** は行ごと・列ごとの
      枡数の**少ないほう**の最大(= 一枡幅なら刻みそのもの)。**土量** = Σ 盛土の厚み × 一枡の面積。
    ⛔ ここで新しい閾を作らない ── 枡を選ぶ条件は呼ぶ側(`grade_collar_stats`)が持つ。
    """
    ix = {}
    for c in cells:
        ix[(int(round(c[0] / IMPL_STEP)), int(round(c[1] / IMPL_STEP)))] = c
    seen, out = set(), []
    for k0 in ix:
        if k0 in seen: continue
        stack, comp = [k0], []
        seen.add(k0)
        while stack:
            i, j = stack.pop(); comp.append((i, j))
            # ⭐ **束ねるのは 8 近傍**【K099 検図 高 2026-09-19】── 畝は法尻に沿って走るので、
            #   一枡ずつ横へずれながら続く。⛔ 4 近傍で束ねると**一条の土手が三つに切れ**、
            #   走りも土量も小さく出る(当図の北西で 9 枡 14.0 m³ が 4/3/2 枡に割れていた)。
            #   ⭕ 斜めに接する枡は**地面の上では続いている**ので一条と数える。
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                k = (i + di, j + dj)
                if k in ix and k not in seen:
                    seen.add(k); stack.append(k)
        cs = [ix[k] for k in comp]
        rows, cols = {}, {}
        for i, j in comp:
            rows[j] = rows.get(j, 0) + 1
            cols[i] = cols.get(i, 0) + 1
        wid = min(max(rows.values()), max(cols.values())) * IMPL_STEP
        ends = max(((a, b) for a in cs for b in cs),
                   key=lambda t: (t[0][0] - t[1][0]) ** 2 + (t[0][1] - t[1][1]) ** 2)
        ex, ez = ends[1][0] - ends[0][0], ends[1][1] - ends[0][1]
        el = math.hypot(ex, ez)
        # ⭐ **条の芯**(朱の一本線で通す)【検図 低 2026-09-19 ── 一辺 2.5 px の枠では 9 m の条が
        #   22 px の滲みに見え、『連なり』が読めなかった】。⛔ 枠の並びで連なりを表さない。
        spine = [(c[0], c[1]) for c in sorted(
            cs, key=lambda c: ((c[0] - ends[0][0]) * ex + (c[1] - ends[0][1]) * ez) / (el or 1.0))]
        out.append((len(cs), len(cs) * IMPL_STEP, wid,
                    max(c[2] for c in cs), max(c[3] for c in cs),
                    sum(max(0.0, c[3]) for c in cs) * IMPL_STEP * IMPL_STEP,
                    (round(ends[0][0], 1), round(ends[0][1], 1)),
                    (round(ends[1][0], 1), round(ends[1][1], 1)),
                    sorted(cs, key=lambda c: -c[3])[0][4],
                    el,                                                    # [9] 端点間の直距離
                    sum(max(0.0, c[2]) for c in cs) * IMPL_STEP * IMPL_STEP,  # [10] 落とす土
                    max(c[3] for c in cs) <= 0.0,                          # [11] 切土の中の高まり
                    spine))                                                # [12] 芯の折れ線
    # ⛔ 鍵は**刷る量**(落とす土)。同量は盛土の厚みの和で割る【考証 中 2026-09-19】
    out.sort(key=lambda t: (-t[10], -t[5]))
    return out


def graded_grid(d, g):
    """造成後の地盤 ── **図の切盛図と同じ `design_y`** を世界座標 1 m 格子へ焼く。

    ⛔ 実装側で計算し直さない(段・石段の割付・法面・崖の上の縁の仕分けが全部ここに入る)。
    ⭐ **引くのは `design_y` ではなく `graded_y`**【K060 2026-09-16】── 面の輪郭が格子の隙に
      落ちないよう、輪郭の外へ刻みぶんの縁を持たせる(⛔ 輪郭は縮めない)。
    ⚠ `null` は「造成しない」= **現地形のまま**であって、穴ではない
    (この社は面が2枚しかなく、社地の大半は自然の斜面 = 社叢の帯である)。
    """
    P = d["polygon"]
    cap = _grade_reach(d, g)
    x0 = math.floor(min(p[0] for p in P) - cap)
    x1 = math.ceil(max(p[0] for p in P) + cap)
    z0 = math.floor(min(p[1] for p in P) - cap)
    z1 = math.ceil(max(p[1] for p in P) + cap)
    nx = int((x1 - x0) / IMPL_STEP) + 1
    nz = int((z1 - z0) / IMPL_STEP) + 1
    H, n9 = [], 0
    for iz in range(nz):
        row = []
        for ix in range(nx):
            y9 = graded_y(d, g, x0 + ix * IMPL_STEP, z0 + iz * IMPL_STEP)
            row.append(None if y9 is None else round(y9, 3))
            if y9 is not None: n9 += 1
        H.append(row)
    # ⭕ **揺れそのものを測って残す**(規則19)── 同じ格子を「覚え書きを積んだまま」= 図が
    #    実際に描く順で引き直し、冷えた値と何セル食い違うかを数える。⛔ 数を文章に書かない —
    #    検査『焼き出しの造成後の地盤…』がこの欄を読んで刷り、⛔ **0 でなければ止める**。
    #    ⚠ 2026-09-09 に鍵を直して 0 になったが、測るのはやめない(戻ったら鳴る所が要る)。
    flip, dmax = 0, 0.0
    for iz in range(nz):
        for ix in range(nx):
            y8 = graded_y(d, g, x0 + ix * IMPL_STEP, z0 + iz * IMPL_STEP, cold=False)
            y9 = H[iz][ix]
            if (y8 is None) != (y9 is None): flip += 1
            elif y8 is not None: dmax = max(dmax, abs(round(y8, 3) - y9))
    return {"x0": float(x0), "z0": float(z0), "step": IMPL_STEP,
            "nx": nx, "nz": nz, "filled": n9, "h": H,
            "orderDrift": {"cells": nx * nz, "nullFlip": flip, "maxDiff": round(dmax, 4),
                           "_": "**`design_y` が呼び出し順で答えを変えるセルの数**。"
                                "⭕ **0 が正**【裁定 2026-09-19 = 案A】── 法面は `cone_field` が"
                                "**一度だけ解く一枚の面**で、点ごとの ray も覚え書きも無い。"
                                "⛔ 0 でなければ検査が止める(覚え書きが答えを変えている = "
                                "切盛図・断面・社地外の集計が呼ぶ順で動くということ)"}}


def _w(g, p):
    x, z = g.W(p[0], p[1])
    return [round(x, 3), round(z, 3)]


def _w_segs(g, o):
    """`run_segs`(= 開口を抜いた実際に建つ区間)を世界座標へ。⛔ 実装が開口を切り直さない。"""
    return [[_w(g, a), _w(g, b)] for a, b in run_segs(o)]


def impl_sukibei_spans(d, g):
    """**透塀の割り付けを実装が読む形で焼く**【K068 2026-09-16 棟梁の差し戻し → 2026-09-18】。

    ⛔ **割り付けが図の本文にしか無い状態を残さない。**隅の型(`Dezumi`/`Irizumi`)は
    `impl_runs` の `kado` で渡っていたが、81 本のスパンは**どれがどの FBX か**が検査の
    〔記録〕の文にしか無く、棟梁は部材名を引けなかった(芯 0.29 m ずれの再発口)。
    ⇒ 辺ごとに **区間・本数・スパン mm・端の型・部材名・木口の世界座標**を焼く。

    ⭐ **木口は面で渡す** ── 部材の据わりは `aWorld`→`bWorld` の**二つの木口の通り**で、
      ⛔ 中心を渡さない(規則5)。端の型 `n`/`t`/`c`/`h` はいずれも割り付けの差し引きが 0 なので、
      この区切りがそのまま節点であり、柱は節点をまたいで ±0.090 出る(`bom[].endSeatM`)。
    ⛔ 数を json に持たない — すべて折れ線・基準スパン・部材の実測からの従属値。
    """
    ken = d["const"]["ken"]
    row = next((b for b in d["bom"] if b.get("部材") == SUKIBEI_ROW), {}) or {}
    baked = set(row.get("baked") or [])
    R = dict((r["name"], r) for r in d["runs"])
    out = {}
    for rn, nm, ln, n, mm, ends, s0 in sukibei_span_plan(d):
        r = R[rn]
        A, B = r["a"], r["b"]
        Lm = math.hypot(B[0] - A[0], B[1] - A[1]) * ken
        if Lm < 1e-9: continue
        ux, uy = (B[0] - A[0]) / Lm, (B[1] - A[1]) / Lm        # [間 / m]
        pcs = []
        for i, e in enumerate(ends):
            sa, sb = s0 + ln * i / n, s0 + ln * (i + 1) / n
            key = "%d_%s" % (mm, e)
            pcs.append({"name": "Sanno_Sukibei_" + key, "spanMm": mm, "ends": e,
                        "aWorld": _w(g, [A[0] + ux * sa, A[1] + uy * sa]),
                        "bWorld": _w(g, [A[0] + ux * sb, A[1] + uy * sb]),
                        "baked": key in baked})
        o = out.setdefault(rn, {"spanBaseM": row.get("spanBaseM"), "loader":
                                "EdoAssets.Own.SannoSukibei(spanMm, ends) / "
                                "EdoAssets.Own.SannoSukibeiKado(part)", "segs": []})
        o["segs"].append({"seg": nm, "sM": [round(s0, 3), round(s0 + ln, 3)],
                          "lenM": round(ln, 3), "count": n, "spanMm": mm, "ends": ends,
                          "pieces": pcs})
    for o in out.values():
        o["segs"].sort(key=lambda q: q["sM"][0])
        o["count"] = sum(q["count"] for q in o["segs"])
        o["builtM"] = round(sum(q["lenM"] for q in o["segs"]), 3)
    return out


def impl_kado(d, g):
    """**透塀の隅を実装が読む形で焼く**(辺の名 → その辺に載る隅の列)。

    ⭐ 図の検査(`impl_fresh_check`)と焼き出し(`impl_runs`)が**同じこの一つ**から出る(規則19)
      ── ⛔ 二か所で組み立てない。
    """
    kado = {}
    for a9, b9, uv, t9 in (sukibei_kado_plan(d) or []):
        st = sukibei_kado_seat(d, a9, b9, uv, t9)
        # ⭐ **据える責めは入ってくる辺(`at":"b"`)に一つだけ**【中 検図2巡目 2026-09-18】──
        #    ⛔ 同じ隅が二つの run に載ったまま `owner` が無いと、実装が**二度据える**
        #    (K062/K089 の再発口)。⛔ 相手側の行を消さない ── 取り合いの相手として読む。
        base = dict(st, type=t9, part=KADO_PART[t9], world=_w(g, uv),
                    ownerRun=a9["name"],
                    _="`owner` = この隅を**据える責め**(⛔ true の行だけが据える。false の行は"
                      "取り合いの相手として読む)。`yawDeg` は `bom[透塀].kadoLegDir` と折れ線からの"
                      "従属値(局所 +Z = 北 = 0°)。`legM` は隅柱の芯から脚が届く量(層ごと)")
        kado.setdefault(a9["name"], []).append(dict(base, at="b", with_=b9["name"], owner=True))
        kado.setdefault(b9["name"], []).append(dict(base, at="a", with_=a9["name"], owner=False))
    for v9 in kado.values():
        for q9 in v9:
            q9["with"] = q9.pop("with_")
    return kado


def impl_runs(d, g):
    """囲い(`runs`)と土留め(`terraceWalls`)の**建つ区間**を世界座標で焼く。

    ⭐ `Ita_Keidai` は `a`/`b` が null で、**平場の輪郭からの生成物**(`derive_runs`)なので
      指図からは引けない。`Saku_SW`(法尻の柵)・`Saku_Sando`(参道の柵)も同じく折れ線が要る。
    ⭐ 口(`gaps`)は石段の頭・門の口・並走の切れ(`skips`)からの従属値(`derive_gaps`)。
    """
    out = []
    # ⭐ **透塀の隅の凹凸を焼く**【K059 2026-09-16】── 棟梁が図を信じられず折れ線から測り直した
    #   のは、凹凸が指図の中で手書きの銘だったから。⇒ 算出値そのものを実装へ渡す。
    kado = impl_kado(d, g)
    spans = impl_sukibei_spans(d, g)
    for o in d["runs"]:
        gl = gap_ledger(o)
        out.append({"name": o["name"], "of": "run", "kind": o.get("kind"),
                    "kado": kado.get(o["name"]),
                    "spans": spans.get(o["name"]),
                    "seat": o.get("seat"), "h": run_take_m(d, o),
                    "nodes": [_w(g, q) for q in (o.get("pts") or
                                                 ([o["a"], o["b"]] if o.get("a") else []))],
                    "segs": _w_segs(g, o),
                    "gaps": [[_w(g, q)[0], _w(g, q)[1], round(q[2] * d["const"]["ken"], 3)]
                             for q in (o.get("gaps") or [])],
                    "skips": len(o.get("skips") or []),
                    "lenM": round(run_len_ken(o) * d["const"]["ken"], 3),
                    "nodeLenM": round(run_nodes_ken(o) * d["const"]["ken"], 3),
                    "gapLedgerM": dict((k9, round(v9 * d["const"]["ken"], 3))
                                       for k9, v9 in gl.items() if not k9.endswith("の数"))})
    for o in d["terraceWalls"]:
        sm = wall_samples(d, g, o, IMPL_WALL_STEP)
        k9 = wall_stair(d, o)
        fh = [q[4] for q in sm] or [0.0]                  # 見付高
        bh = [q[5] for q in sm] or [0.0]                  # 受け高
        out.append({"name": o["name"], "of": "wall", "kind": "土留め",
                    "coping": o.get("coping"),
                    "copingFrom": (k9["name"] if k9 is not None else None),
                    "nodes": [_w(g, q) for q in wall_nodes(d, o)],
                    "segs": _w_segs(g, o),
                    "lenM": round(run_len_ken(o) * d["const"]["ken"], 3),
                    # ⭐ **走り 1 m 刻みの 6 列**【中4 検図20巡目 → 裁定 2026-09-09(A案)】。
                    #   ⛔ `coping:"stair"` の4本は **`stair_spans` から天端を引く** ── 実装が
                    #   「壁の走り → 石段の割付の y」の対応を自力で作る道を塞ぐ。
                    "profileStep": IMPL_WALL_STEP,
                    "profile": wall_profile(d, g, o, IMPL_WALL_STEP),
                    "gapsS": wall_gaps_s(sm, IMPL_WALL_STEP),
                    "tiers": int(o.get("tiers", 1)),
                    "pieceHM": d["const"].get("stoneWallPieceHM"),
                    "tierSpans": wall_tier_spans(d, g, o),
                    "faceM": [round(min(fh), 3), round(max(fh), 3)],
                    "backM": [round(min(bh), 3), round(max(bh), 3)],
                    "_": "`profile` = **[走り s[m], 天端 y[m], 低い側の地盤 y[m], "
                         "高い側の地盤 y[m], 見付高[m], 受け高[m]]** を `profileStep` 刻みで。"
                         "s は `nodes[0]` からの走り。⛔ 実装が引き直さない ── 天端は `coping` "
                         "が数ならその値、`\"stair\"` なら `copingFrom` が指す石段の割付"
                         "(`stair_spans`)から引いてある。⭐ 図の `copingRise:\"groundHi\"` の壁は "
                         "天端 = max(その座, 高い側の地盤)(裁定 EDO-0182 (a))。**地盤は造成後 `design_y` 一本を基準に"
                         "壁の両側で採る**(`const.wallProbeM`)。見付高 = 天端 − 低い側 ／ "
                         "受け高 = 高い側 − 天端【裁定 2026-09-09 普請奉行 = 検図21巡目 A案】。"
                         "⛔ **見付≦0 かつ 受け>0 の区間は『埋まっている壁』**で、⛔ 実装が"
                         "地形を削って直さない(始末は指図が持つ)。`gapsS` は**建たない区間**(開口)の "
                         "s の範囲で、`segs` と同じ出所。`tiers` は段数(i 段目の駒の天端 = 天端 − (i−1)×`pieceHM`)、"
                         "`tierSpans[i−2]` は i 段目(2 段目以下)が地上に見える走りの範囲(裁定 EDO-0182 (a) ③)"})
    return out


def impl_stairs(d, g):
    """石段 ── 折れ線・幅・**割付**(`stair_spans`)。⛔ 実装が段を割り直さない。

    ⚠ 切盛図・断面・動線の昇りが**この一つの関数**を通る(二つの式で別々に割ると
      蹴上1段ぶんずれる — 2026-08-24 検図 高-4、男坂で最大 1.34 m)。
    """
    out = []
    for k in d["kaidans"]:
        sp, tot = stair_spans(k)
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        out.append({"name": k["name"], "wM": round(kaidan_wm(d, k), 4),
                    "yBot": k["yBot"], "yTop": k["yTop"],
                    "keri": k.get("keri"), "fumi": k.get("fumi"),
                    "steps": k.get("steps"), "flights": k.get("flights"),
                    "odoriba": k.get("odoriba"),
                    "nodes": [_w(g, q) for q in pts],
                    # ⭐ **s の起点を宣言する**【検図 中 2026-09-19】── ⛔ 実装が `nodes` の順に
                    #   s を取ると、`firstIsTop` の石段(男坂)だけ**上下逆に建つ**。
                    # ⛔ **折れ線の正典を二つ持たない**【検図 低 2026-09-19 第2巡】── 旧は
                    #   `nodes` を反転した `nodesUp` を並べて焼いていたが、`firstIsTop` と
                    #   `sFrom` があれば向きは決まる。片方だけ直した日に静かにずれる。
                    "firstIsTop": bool(stair_first_is_top(d, g, k)),
                    "sFrom": ("nodes[-1](= 坂下。`nodes` は上から下へ並んでいる)"
                              if stair_first_is_top(d, g, k) else "nodes[0](= 坂下)"),
                    "runM": (round(tot * 1.0, 4) if tot else None),
                    "spans": ([[round(a, 4), round(b, 4), round(y, 4)] for a, b, y in sp]
                              if sp else None),
                    "_": "`spans` の s は **坂下からの走り**[m]・y は踏面の高さ。坂下は "
                         "`sFrom` が指す端(`firstIsTop` が真なら `nodes[-1]`、偽なら `nodes[0]`)。"
                         "⛔ `nodes` の順に s を取らない ── `firstIsTop` が真の石段"
                         "(`nodes[0]` が山上)は上下が逆になる。⛔ 反転した折れ線をここへ焼かない"
                         "(同じ形に二つの正典ができる)。⭕ 向きは現地形が決めた値で、"
                         "図の側の `stair_first_is_top` がただ一つの正典(⛔ 実装が引き直さない)"})
    return out


def impl_gates(d, g):
    """門の芯 ── **`uFrom` を持つ門は芯が従属値**(仁王門は前庭の西縁+犬走りから)。"""
    return [{"name": gt["name"], "u": gt["u"], "v": gt["v"], "yaw": gt.get("yaw"),
             "front": gt.get("front"), "passAz": gt.get("passAz"), "yawFrom": gt.get("yawFrom"),
             "bom": gt.get("bom"),
             "sill": gt.get("sill"), "plan": gt["plan"],
             "monguchiKen": gt.get("monguchiKen"),
             "world": _w(g, (gt["u"], gt["v"]))} for gt in d["gates"]]


def impl_routes(d, g):
    """動線の折れ線(世界座標)。⭐ `from` を持つ動線は勝手道からの組み立て(`derive_routes`)。"""
    out = []
    for rt in d.get("routes", []):
        pts = [[round(q[0], 3), round(q[1], 3)] if rt.get("world") else _w(g, q)
               for q in rt["pts"]]
        out.append({"name": rt["name"], "kind": rt.get("kind"), "w": rt.get("w"),
                    "wByTerrace": rt.get("wByTerrace"), "world": pts})
    return out


def impl_tamagaki(d, g):
    """玉垣の**建つ区間**(辺ごと・木戸の開口を抜いた実長)。⛔ 実装が辺を割り直さない。"""
    out = []
    for gd in d["gardens"]:
        if not gd.get("tamagaki"): continue
        for nm, a, b, fence, ln, rs in tamagaki_edges(d, gd):
            out.append({"garden": gd["name"], "edge": nm, "fence": bool(fence),
                        "a": _w(g, a), "b": _w(g, b),
                        "segs": [[_w(g, q[0]), _w(g, q[1])] for q in rs],
                        "lenM": round(ln * d["const"]["ken"], 3),
                        "spec": gd["tamagaki"]})
    return out


def impl_props(d, g):
    """点景・踏石・井戸屋形・区の輪郭・見所 ── どれも**宣言からの従属値**で、
    指図に矩形が入っていない(規則4)。⛔ 実装が組み立て直さない。

    ・`props`      … `prop_rects`(芯 + `plan`/`planM` + `yaw` から回した4点)
    ・`fumiishi`   … `fumiishi_rects`(門の戸口の内法・石段の幅からの従属値)
    ・`ido`        … `ido_rects` / `ido_depth` / 井桁・礎石・井筒の径
    ・`gardens`    … 区の輪郭(`polyFrom` を持つ区は門の面から従属)
    ・`viewpoints` … 見所(`uFrom` を持つ見所は門の面から従属)。検証レンダの視点でもある
    """
    io9 = ido_rects(d)
    return {
        "props": [{"name": nm, "world": [_w(g, q) for q in Q]} for nm, Q in prop_rects(d)],
        "fumiishi": [{"name": q[0], "world": [_w(g, (q[1], q[2])), _w(g, (q[3], q[2])),
                                              _w(g, (q[3], q[4])), _w(g, (q[1], q[4]))]}
                     for q in fumiishi_rects(d)]
                    + [{"name": nm, "world": [_w(g, q) for q in P9]} for nm, P9 in fumitome_polys(d)],
        "ido": (None if not io9 else
                {"rects": dict((k9, ([_w(g, q) for q in v9] if k9 == "柱" else
                                     [_w(g, (v9[0], v9[1])), _w(g, (v9[2], v9[1])),
                                      _w(g, (v9[2], v9[3])), _w(g, (v9[0], v9[3]))]))
                               for k9, v9 in io9.items()),
                 "depthM": [round(q, 3) for q in ido_depth(d)],
                 "igetaRise": igeta_rise(d), "soishiR": soishi_radii(d),
                 "izutsuR": izutsu_radii(d)}),
        "drains": [{"name": dr["name"], "kind": dr.get("kind"), "slope": dr.get("slope"),
                    "world": [_w(g, (dr["u"][0], dr["v"])), _w(g, (dr["u"][1], dr["v"]))],
                    "outlet": _w(g, (dr["outlet"]["u"], dr["v"]))} for dr in d.get("drains", [])],
        "gardens": [{"name": gd["name"], "kind": gd.get("kind"),
                     "kakoi": ({"spec": gd["kakoi"], "segs": [[_w(g, a9), _w(g, b9)] for a9, b9 in kakoi_segs(d, gd)]}
                               if gd.get("kakoi") else None),
                     "sueishi": (_w(g, gd["sueishi"]["uv"]) if (gd.get("sueishi") or {}).get("uv") else None),
                     "noTrees": bool(gd.get("noTrees")),
                     "holes": [[_w(g, q) for q in H9] for H9 in garden_holes(d, gd)] or None,
                     "world": [_w(g, q) for q in (gd.get("poly") or [])],
                     "rect": ([gd.get("u0"), gd.get("v0"), gd.get("u1"), gd.get("v1")]
                              if gd.get("u0") is not None else None)}
                    for gd in d["gardens"]],
        "viewpoints": [{"name": vp["name"], "u": vp["uv"][0], "v": vp["uv"][1],
                        "world": _w(g, vp["uv"]), "eyeH": vp.get("eyeH"),
                        "look": vp.get("look")} for vp in d.get("viewpoints", [])],
    }


def export_impl(d, g):
    """**実装が読む算出物を焼く**(`docs/Sashizu/sanno_impl.json`)。

    ⭕ スキーマの正典は棟梁の `EdoOkabeYashikiBuilder.IMPL` の doc コメント(岡部が先例)。
    ⛔ **指図か造成前の地盤が変われば焼き直しが要る** — `src.sha256` / `dem.sha256` を入れ、
      実装も図(`impl_fresh_check`)も同じ照合をして、食い違えば止まる。
    ⛔ ここで設計値を作らない ── すべて図が使うのと**同じ関数**の返り値である。
    """
    import datetime
    pts, bd, cl = scatter_pts(d, g)
    gr = graded_grid(d, g)
    out = dict([
        ("of", "sanno_sashizu.json"),
        ("src", {"sha256": _sha256(JSON), "bytes": os.path.getsize(JSON),
                 "_": "**`docs/Sashizu/sanno_sashizu.json` のバイト列**の SHA-256(小文字hex)。"
                      "⛔ 一致しなければ**古い焼き**なので建てない"}),
        ("dem", {"sha256": _sha256(DEM_JSON), "bytes": os.path.getsize(DEM_JSON),
                 "_": "**`docs/Sashizu/sanno_dem.json`(造成前の地盤の正本)のバイト列**の "
                      "SHA-256。⛔ 地盤が変われば `graded` も社叢の帯も変わる"}),
        ("generator", {"path": "Tools/Sashizu/bake_impl.py sanno --write(焼き手 impl_sanno.py)",
                       "sha256": _sha256(os.path.abspath(__file__)),
                       "_": "⚠ 生成器の版。⛔ 一致の照合には使わない(図の作り替えで毎回変わる)"}),
        ("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
        ("checks", {"exportTol": IMPL_EXPORT_TOL, "gradeTol": IMPL_GRADE_TOL,
                    "_": "⭐ **物差しは二つ。混ぜない**【中3 検図20巡目 → 2026-09-09】。"
                         "`exportTol` = **図の側** ── 焼いた `graded` と `design_y` の許容差[m]"
                         "(同じ関数から出るので丸めの 0.001 m 以外は出ない。図は**全セル**を"
                         "引き直して突き合わせる ⛔ 標本で済ませない)。"
                         "`gradeTol` = **実装側** ── 造成した地形と設計面の許容差[m]で、意味の"
                         "正典は `EdoOkabeYashikiBuilder.IMPL` の doc コメント(岡部と同じ 0.30)。"
                         "⚠ ハイトマップは 16bit 正規化で量子が 0.003〜0.009 m あるので、"
                         "⛔ ここへ 0.001 を入れると造成後QAが全セル不合格になる。"
                         "⛔ どちらも検査の物差しであって設計値ではない。"
                         "⚠ **`gradeTol` は当図の側に消費者がゼロ**【低1 検図21巡目 → 2026-09-09】"
                         "── 図は `exportTol` しか使わない。⭕ **設計としては正しい**(実装側の"
                         "造成後QAの許容差で、意味の正典は岡部の `IMPL` の doc コメント)ので、"
                         "⛔ 落とさない。⚠ **輪に入るのは棟梁が造成した地形をこの値で測る所**で、"
                         "そこまでは『**焼いてあるが誰も読んでいない値**』である(規則19)── "
                         "実装の着手時に消費点を作ること"}),
        ("grid", {"x0": d["grid"]["keidai"]["x0"], "z0": d["grid"]["keidai"]["z0"],
                  "ken": d["const"]["ken"],
                  "_": "x = x0 + u×ken ／ z = z0 + v×ken(u=東+/v=北+・軸は世界軸)"}),
        ("terraces", [{"name": t["name"], "y": t["y"],
                       "world": [[round(q[0], 3), round(q[1], 3)]
                                 for q in terrace_poly(t, g)]} for t in d["terraces"]]),
        ("graded", gr),
        ("stairs", impl_stairs(d, g)),
        ("runs", impl_runs(d, g)),
        ("gates", impl_gates(d, g)),
        ("routes", impl_routes(d, g)),
        ("tamagaki", impl_tamagaki(d, g)),
        ("setae", impl_props(d, g)),
        ("planting", {"points": pts, "bands": bd, "clusters": cl,
                      "seedRule": d["planting"]["plantRule"]["seed"],
                      "placement": d["planting"]["plantRule"].get("placement"),
                      "_": "**撒いた木の点**。⛔ 実装側で撒き直さない — 別の乱数で撒けば"
                           "退避も林冠も図が測った物と別になる。種は `seedRule` の宣言から"
                           "決定論的に作るので、同じ指図からは同じ配置が出る"}),
    ])
    return out


def wall_tier_spans(d, g, w):
    """段 i(上から 0 段目・i ≥ 1)が**地上に見える走りの範囲** `[[s0, s1], ...]` を段ごとに並べる。

    ⭐ 段 i の駒の天端 = 天端 − i × 駒の丈(`const.stoneWallPieceHM`)── スキル §3b の閉形式
      (駒は伸縮させず、高さは埋まりで吸う)をそのまま段に重ねた従属値。⛔ 段の境を数で持たない。
    ⭐ 段 i が見えるのは **見付高 > i × 駒の丈** の点(建つ区間だけ)。⛔ 実装が引き直さない。
    """
    H = d["const"].get("stoneWallPieceHM")
    nt = w.get("tiers", 1)
    if not isinstance(H, (int, float)) or H <= 0 or not isinstance(nt, int) or nt < 2:
        return []
    sm = wall_samples(d, g, w, IMPL_WALL_STEP)
    out = []
    for i9 in range(1, nt):
        sp, prev = [], None
        for q9 in sm:
            if q9[-1] and round(q9[4], 3) > i9 * H + 1e-6:
                if sp and prev is not None and q9[0] - prev <= IMPL_WALL_STEP * 1.001 + 1e-6:
                    sp[-1][1] = round(q9[0], 3)
                else:
                    sp.append([round(q9[0], 3), round(q9[0], 3)])
                prev = q9[0]
            else:
                prev = None
        out.append(sp)
    return out


def bake():
    """**山王の算出物を焼いて dict で返す(書かない)。**書くのは `bake_impl.py sanno --write`。

    ⭕ 手順(derive_* の順)は元の `main_export_impl` のまま。⛔ 指図へ書き戻さない
      (`d` は読んだ写しを組み立てるだけ)ので、`src.sha256` は読んだ指図そのものを指す。
    """
    d = json.load(open(JSON, encoding="utf-8"))
    derive_routes(d)
    derive_garden_strips(d)
    g = G(d)
    derive_edges(d)             # ⭐ 道敷に接する辺を毎回同定(決4 庭方 2026-09-09 十八巡目)
    derive_gates(d, g)
    derive_kaidan_tataki(d)    # 石段の足の水叩き(踏石=門の従属値なので門の後)
    derive_runs(d, g)
    derive_zentei(d, g)
    derive_sukibei_kado(d)     # 透塀の隅の凹凸は折れ線からの従属値(K059 2026-09-16)
    derive_cluster_groups(d)    # ⭐ 塊の `groups` を兄弟へ展開(中6 庭方 2026-09-09)
    derive_clusters(d)
    derive_view_clusters(d, g)
    derive_view_eda(d)
    derive_viewpoints(d, g)     # ⭐ 見所の `eyeH`/`look` を焼く(2026-09-08 B-3・庭方)
    return export_impl(d, g)


