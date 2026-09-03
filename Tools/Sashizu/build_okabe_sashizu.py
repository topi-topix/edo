#!/usr/bin/env python3
"""岡部筑前守上屋敷(和泉岸和田藩 五万三千石)の指図を組む。

**正典は docs/Sashizu/okabe_sashizu.json**(寸法)と okabe_kosho.md(文章)。
この生成器は数値を持たない — 図も表もキャプションも json/md から引く。

座標は**回転間グリッド shukaku**: 原点=表門の芯、u=東辺(三べ坂)沿いに北、v=敷地の奥(西)へ。
東辺は世界軸から 5.71° 振れる。1間=1.818m。Y は海抜m。

章は本文の並び順に自動採番する(其一〜)。**図番を生成器に書かない。**
"""
import json, math, os, re, random, subprocess, html, collections

import sashizu_lib
from sashizu_lib import (R, _pat, _SVN, Proj, RGrid, cf_color, cutfill_legend,
                         dem_color, _iso, dem_legend, links_table,
                         _edge_dir, mune_contacts_table,  # バイト同一を実証済みの共通部
                         overlap_check)  # 検査の正典(2026-08-26 統一)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "okabe_sashizu.json")
MD = os.path.join(DOC, "okabe_kosho.md")
OUT = os.path.join(DOC, "okabe_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown(正典は sashizu_lib)
def inline(s):
    """方言なし(2026-08-26 に厳しい既定へ寄せた — 決着済み4項の ~~…~~ が取り消し線で描かれる)。"""
    return sashizu_lib.inline(s)


def md2html(text):
    return sashizu_lib.md2html(text, inline=inline)


# ---------------------------------------------------------------- 作図の土台


def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, label),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.65"/>'
            '</pattern></defs>' % _SVN[0]]


class LProj(object):
    """グリッド座標 (u,v)[間] → SVG px。v(敷地の奥)が画面の下。

    ⚠ **u は画面の左向き**。(u,v) は世界座標で反時計回りの対(u×v>0)なので、
    v を下向きに取ったら u は左向きでないと**図が鏡像になる**
    (2026-08-23 ユーザー指摘で是正 — 「敷地」と「現況図」の左右が逆だった)。
    結果、この図版は 「敷地」(北が上)を反時計回りに 90° 回した向き = **上が東(表門の道)/
    左が北 / 下が西(敷地の奥) / 右が南**。
    """

    def __init__(self, u0, u1, v0, v1, W=900.0, top=22.0, bottom=20.0):
        self.u0, self.u1, self.v0, self.v1 = u0, u1, v0, v1
        self.s = W / float(u1 - u0)
        self.W, self.top = W, top
        self.vh = (v1 - v0) * self.s
        self.H = self.vh + top + bottom

    def X(self, u): return (self.u1 - u) * self.s
    def Y(self, v): return self.top + (v - self.v0) * self.s
    def L(self, ken): return ken * self.s

    def rect(self, u0, v0, u1, v1, **kw):
        return R(min(self.X(u0), self.X(u1)), self.Y(min(v0, v1)),
                 abs(self.X(u1) - self.X(u0)), abs(self.Y(v1) - self.Y(v0)), **kw)

    def poly(self, gp, **kw):
        """グリッド座標の多角形をそのまま描く(段の縁が等高線に沿う場合)。"""
        a = '<polygon points="%s"' % " ".join("%.1f,%.1f" % (self.X(u), self.Y(v)) for u, v in gp)
        if "fill" in kw:
            a += ' fill="%s"' % kw["fill"]
        if kw.get("stroke") and kw["stroke"] != "none":
            a += ' stroke="%s" stroke-width="%.2f"' % (kw["stroke"], kw.get("sw", 1.0))
        if kw.get("dash"):
            a += ' stroke-dasharray="%s"' % kw["dash"]
        if kw.get("op") is not None:
            a += ' opacity="%.2f"' % kw["op"]
        return a + "/>"


def T(x, y, s, cls="sl", anchor=None, fs=None, fill=None):
    """text-anchor は style で出す(クラスの CSS 規則が presentation attribute に勝つため)。"""
    a = '<text class="%s" x="%.1f" y="%.1f"' % (cls, x, y)
    st = []
    if anchor:
        st.append("text-anchor:%s" % anchor)
    if fs:
        st.append("font-size:%.1fpx" % fs)
    if fill:
        st.append("fill:%s" % fill)
    if st:
        a += ' style="%s"' % ";".join(st)
    return a + ">%s</text>" % html.escape(s.replace("**", ""), quote=False)


def LN(x1, y1, x2, y2, stroke="var(--ink)", sw=1.0, dash=None, op=None, cap=None):
    a = '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.2f"' \
        % (x1, y1, x2, y2, stroke, sw)
    if dash:
        a += ' stroke-dasharray="%s"' % dash
    if op is not None:
        a += ' opacity="%.2f"' % op
    if cap:
        a += ' stroke-linecap="%s"' % cap
    return a + "/>"


def fit(txt, wpx, base=12.0, lo=6.0):
    return max(lo, min(base, wpx / (len(txt) * 0.62 + 0.8)))


def edge_pt(P, e, s):
    """辺 e の始点から走り s[m] の世界座標。"""
    a, b = P[e], P[(e + 1) % len(P)]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    t = s / L
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _inward(P, e):
    """辺 e の**内向き**単位法線(世界座標)。
    ⛔ 重心で向きを決めない — 凹み多角形では1辺だけ反転する(掲示板 EDO-0058・松平で塀が隣家へ 0.95m 出た)。
    多角形の回り(符号付き面積)から決めるので、凹みがあっても全辺で一貫する。"""
    n = len(P)
    a, b = P[e], P[(e + 1) % n]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-9
    area2 = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    sgn = 1.0 if area2 > 0 else -1.0
    return (-dy / L * sgn, dx / L * sgn)


PLANE_COL = {"門前面": "var(--pl-omote)", "主面": "var(--pl-main)",
             "斜面(造成しない)": "var(--pl-slope)"}
_DANC = {}


def dan_color(d, y):
    """段の色。**面の名前で引く**(2026-08-23 検図: 高さをキーにした旧 DAN が必ず外れていた)。"""
    key = id(d)
    if key not in _DANC:
        m = {}
        for pl in d.get("planes", []):
            for tn in pl.get("terraces", []):
                m[tn] = PLANE_COL.get(pl["name"], "var(--dan4)")
        _DANC[key] = dict((t["y"], m.get(t["name"], "var(--dan4)")) for t in d["terraces"])
    return _DANC[key].get(y, "var(--dan4)")

KC = {"Nagaya": "var(--nagaya)", "Dobei": "var(--hei)", "Fence": "var(--dan)"}

MUNE_JA = {
    "Kurumayose": "車寄", "Genkan": "玄関棟", "Shoin": "書院棟", "Nakaoku": "中奥棟",
    "Daidokoro": "台所棟", "Okumuki": "奥向棟", "Nagatsubone": "長局",
    "Oku": "奥棟", "Umaya": "厩棟",
}
sashizu_lib.MUNE_JA = MUNE_JA  # lib の mune_contacts_table が引く棟名辞書を差す
TERR_JA = {"Monzen": "門前面", "Shumen": "主面"}


# ---------------------------------------------------------------- 敷地
def tatami(r):
    """室の畳数は**矩形から算出する**(江戸間 1間² = 2畳)。
    ⚠ 2026-08-24 検図: 手で持っていた `tatami` が矩形と合わない室が2件あった
    (御広間 48/36・御湯殿 12/8)。二重に持たない — 矩形が正典。"""
    return int(round(2.0 * (r["u1"] - r["u0"]) * (r["v1"] - r["v0"])))


def tpoly(t):
    """段の輪郭(グリッド座標)。`poly` があればそれ、無ければ外接矩形の四隅。"""
    p = t.get("poly")
    if p:
        return [(a, b) for a, b in p]
    return [(t["u0"], t["v0"]), (t["u1"], t["v0"]), (t["u1"], t["v1"]), (t["u0"], t["v1"])]


def tholes(t):
    """段の**抜き**(面にしない=造成しない区画)の輪郭。正典は sashizu_lib.t_holes。
    ⭐ 2026-09-02 ユーザー裁定(案A)「主面の5区画を平坦化しない」。"""
    return sashizu_lib.t_holes(t)


def tkeeps(t):
    """抜きの中で面を残す区画(棟の足跡+犬走り)。**生成器が算出**して書き戻す。"""
    return sashizu_lib.t_keeps(t)


def _ring_in(p, u, v):
    n = len(p); c = False
    for i in range(n):
        (au, av), (bu, bv) = p[i], p[(i + 1) % n]
        if (av > v) != (bv > v) and u < (bu - au) * (v - av) / (bv - av) + au:
            c = not c
    return c


def tin_outer(t, u, v):
    """段の**外輪**の中か(抜きを数えない)。庭の切り取りと、抜きの位置の検査に使う。"""
    if not t.get("poly"):
        return t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9
    return _ring_in(tpoly(t), u, v)


def tin(t, u, v):
    """(u,v) が段の中か。多角形なら crossing number、矩形なら範囲判定。
    ⭐ **抜き(`holes`)の中は段の外**(造成しない自然地盤)。"""
    if not tin_outer(t, u, v):
        return False
    if any(_ring_in(hp, u, v) for hp in tholes(t)):
        return any(_ring_in(kp, u, v) for kp in tkeeps(t))   # 棟が載る所だけ面を残す
    return True


def clip_ring(subj, win):
    """凸窓 `win`(点列・時計回りでも反時計回りでもよい)で点列 `subj` を切る
    (Sutherland–Hodgman)。庭の輪郭を「段の外輪」「区画」で機械的に切るために使う。
    ⛔ 手で切った輪郭を json に書かない — 段や区画を動かした瞬間に腐る。"""
    def _sgn(a, b, p):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    ar = sum((win[(i + 1) % len(win)][0] - win[i][0]) * (win[(i + 1) % len(win)][1] + win[i][1])
             for i in range(len(win)))
    side = -1.0 if ar > 0 else 1.0          # 窓の内側の符号
    out = [tuple(q) for q in subj]
    for i in range(len(win)):
        a, b = win[i], win[(i + 1) % len(win)]
        if not out:
            return []
        cur, out = out, []
        for j in range(len(cur)):
            p, q = cur[j], cur[(j + 1) % len(cur)]
            sp, sq = _sgn(a, b, p) * side, _sgn(a, b, q) * side
            if sp >= -1e-12:
                out.append(p)
            if (sp > 1e-12 and sq < -1e-12) or (sp < -1e-12 and sq > 1e-12):
                t9 = sp / (sp - sq)
                out.append((p[0] + (q[0] - p[0]) * t9, p[1] + (q[1] - p[1]) * t9))
    return out


def tdist(t, u, v):
    """段の縁までの距離[間]。中なら 0。"""
    if tin(t, u, v):
        return 0.0
    p = tpoly(t); n = len(p); best = 1e18
    for i in range(n):
        (au, av), (bu, bv) = p[i], p[(i + 1) % n]
        du, dv = bu - au, bv - av
        L2 = du * du + dv * dv
        q = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((u - au) * du + (v - av) * dv) / L2))
        best = min(best, math.hypot(u - (au + q * du), v - (av + q * dv)))
    return best


def _ring_area(p):
    n = len(p)
    return abs(sum(p[i][0] * p[(i + 1) % n][1] - p[(i + 1) % n][0] * p[i][1] for i in range(n))) / 2


def tarea(t):
    """段の面積[間²]。⭐ **抜きの分は引く**(造成しない区画は可建地でない)。"""
    a = _ring_area(tpoly(t))
    for hp in tholes(t):
        a -= _ring_area(clip_ring(tpoly(t), hp))
        # ⚠ **足し戻す keep は「その抜きの中」で切る。**外輪で切ると、抜きの外にある keep が
        #   丸ごと二重に足され、非可建地が過少に出る(2026-09-02 検図 K062: 368坪)。
        for kp in tkeeps(t):
            a += _ring_area(clip_ring(clip_ring(tpoly(t), hp), kp))
    return a


_BASE = {}


def run_base(d, r):
    """run の石垣基壇の露出(最小, 最大)。**edgeProfile から算出する** —
    設計値ファイルに書き写すと seat の引き直しに追従せず腐る(2026-08-23 検図)。"""
    key = (id(d), r["name"])
    if key in _BASE:
        return _BASE[key]
    prof = d.get("edgeProfile", {}).get(str(r["edge"]))
    if not prof:
        _BASE[key] = (0.0, 0.0)
        return _BASE[key]

    def g(sv):
        if sv <= prof[0][0]:
            return prof[0][1]
        for (a1, y1), (b1, y2) in zip(prof, prof[1:]):
            if a1 <= sv <= b1:
                return y1 + (y2 - y1) * (sv - a1) / (b1 - a1)
        return prof[-1][1]
    n = max(2, int((r["s1"] - r["s0"]) / 0.5))
    vs = []
    for i in range(n + 1):
        sv = r["s0"] + (r["s1"] - r["s0"]) * i / n
        vs.append(rseat(r, sv) - g(sv))
    _BASE[key] = (min(vs), max(vs))
    return _BASE[key]


_RAILS = {}


def _ptrunc(seq, f="(%.1f, %.1f)"):
    """折れ線の座標列を『始点 → …(折れ点 n点)… → 終点』に畳む。
    法肩の竹垣は折れ点が60を超えるので、そのまま並べると表が読めない。"""
    seq = list(seq)
    if len(seq) <= 4:
        return " → ".join(f % tuple(q) for q in seq)
    return "%s → %s → …(中間の折れ点 %d点)… → %s → %s" % (
        f % tuple(seq[0]), f % tuple(seq[1]), len(seq) - 4,
        f % tuple(seq[-2]), f % tuple(seq[-1]))


def _par_near(d, u, v):
    """区画線までの最短距離と、その最寄りの辺番号・辺上の走り s を返す。"""
    key = id(d)
    if key not in _PIN:
        in_parcel(d, 0, 0)
    Pg = _PIN[key]
    best = None
    for i in range(len(Pg)):
        a, b = Pg[i], Pg[(i + 1) % len(Pg)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((u - a[0]) * dx + (v - a[1]) * dy) / L2))
        dd = math.hypot(u - (a[0] + dx * t), v - (a[1] + dy * t))
        if best is None or dd < best[0]:
            best = (dd, i, t * math.sqrt(L2) * d["const"]["ken"])
    return best


def _on_walled_edge(d, u, v, lim):
    """(u,v) が『当家が囲いを建てている辺』の lim[m] 以内か。
    2026-08-24 検図: 三べ坂の練塀(基壇の露出3.0m)が受けている落差を竹垣がもう一本なぞり、
    5.65m の練塀の裏に高さ0.9m の四つ目垣が二重に回っていた。"""
    dd, e, sv = _par_near(d, u, v)
    if dd * d["const"]["ken"] > lim:
        return False
    for r in d["runs"]:
        if r["edge"] == e and r["s0"] - 1.0 <= sv <= r["s1"] + 1.0:
            return True
    for f in d.get("fences", []):
        if f["edge"] == e and f["s0"] - 1.0 <= sv <= f["s1"] + 1.0:
            return True
    return False


def _in_opening(d, u, v):
    """昇り降りの動線の開口の中か。**竹垣はここで切る**(参道・石段・坂を塞がない)。
    2026-08-24 検図: 折れ線に戻した結果、R_Sh2 が参道帯をほぼ全幅(5.42m)塞いでいた。"""
    K = d["const"]["ken"]
    sd = d["sando"]
    if abs(u - sd["u"]) <= sd["width"] / 2.0 + 0.3 and sd["v0"] - 0.5 <= v <= sd["v1"] + 0.5:
        return True
    for k in d["kaidans"]:                                # 石段の開口
        ax, at2, ka, kb, cu9, cv9 = kgeom(k)
        w = k["w"] / 2.0 / K + 0.3
        if ax == "v":
            if abs(u - at2) <= w and min(ka, kb) - 0.5 <= v <= max(ka, kb) + 0.5:
                return True
        else:
            if abs(v - at2) <= w and min(ka, kb) - 0.5 <= u <= max(ka, kb) + 0.5:
                return True
    for rp in d.get("ramps", []):                          # 坂の路盤
        w = rp["w"] / 2.0 / K + 0.5
        for a, b in zip(rp["pts"], rp["pts"][1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy or 1e-9
            t = max(0.0, min(1.0, ((u - a[0]) * dx + (v - a[1]) * dy) / L2))
            if math.hypot(u - (a[0] + dx * t), v - (a[1] + dy * t)) <= w:
                return True
    return False


def _rail_offset(d, rl):
    """竹垣の各点から法肩(段の輪郭)までの垂直距離の範囲[m]。
    隅では法線が交わるぶん詰まるので、設計上の入り(`inubashiri`+`takegakiInset`)を
    そのまま書かず実距離を出す。"""
    t = next(x for x in d["terraces"] if x["name"] == rl["terrace"])
    poly = tpoly(t)
    ds = []
    for u, v in rl["pts"]:
        best = 1e9
        for a, b in zip(poly, poly[1:] + [poly[0]]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy or 1e-9
            tt = max(0.0, min(1.0, ((u - a[0]) * dx + (v - a[1]) * dy) / L2))
            best = min(best, math.hypot(u - (a[0] + dx * tt), v - (a[1] + dy * tt)))
        ds.append(best * d["const"]["ken"])
    return (min(ds), max(ds)) if ds else (0.0, 0.0)


def auto_rails(d):
    """**法肩の竹垣を段の多角形から算出する。** 手で持つと段を動かすたびに腐る。
    段の輪郭のうち「外側の地山が段より 1.0m 以上低い」= 落差のある縁を拾い、
    法肩から内へ `const.inubashiri` + 0.15m 入った**折れ線**を返す。

    ⚠ 2026-08-24 の検図で三度直している。
    ① 始点と終点だけの**弦**にしていた → 折れ点をすべて残す。
    ② **外周の囲いが載っている辺**をなぞって二重に回っていた → `_on_walled_edge` で外す。
    ③ 参道・石段・坂を塞いでいた → `_in_opening` で切る(「動線を塞がない」は図の宣言)。
    ④ オフセットを重心からの放射方向で取っていたため垂直距離が 0.45m にならなかった
       → **各線分の外向き法線**で取る。"""
    if id(d) in _RAILS:
        return _RAILS[id(d)]
    K = d["const"]["ken"]
    # ⛔ 2026-09-01 六巡目まで 0.15 / 1.0 / 9.0 が直書きだった(規則4違反・実装側と二重管理)。
    off = (d["const"]["inubashiri"] + d["const"]["takegakiInset"]) / K
    dropMin = d["const"]["takegakiDrop"]
    minLen = d["const"]["takegakiMinLen"]
    out = []
    rings = []
    for t in d["terraces"]:
        # ⭐ **外輪だけでなく抜きと keeps の縁も回す**(2026-09-02 検図 K071)。
        #   抜きを窪みへ置いた瞬間、外輪しか見ない形は黙って落ちる。
        #   ⚠ 抜き・keep の縁は法線が**内向き**(段は輪の外側)なので向きを反転して渡す。
        rings.append((t, tpoly(t), 1.0))
        for hp in tholes(t) + tkeeps(t):
            rings.append((t, hp, -1.0))
    for t, poly, sgn in rings:
        n = len(poly)
        cu = sum(p[0] for p in poly) / n; cv = sum(p[1] for p in poly) / n
        segs = []
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            L = max(int(math.hypot(b[0] - a[0], b[1] - a[1])), 1)
            ex, ey = b[0] - a[0], b[1] - a[1]
            en = math.hypot(ex, ey) or 1.0
            nx, ny = ey / en, -ex / en                 # 線分の法線
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if (mid[0] + nx - cu) ** 2 + (mid[1] + ny - cv) ** 2 < \
               (mid[0] - nx - cu) ** 2 + (mid[1] - ny - cv) ** 2:
                nx, ny = -nx, -ny                      # 外向きに揃える
            nx, ny = nx * sgn, ny * sgn                # 抜き・keep は段が輪の外側
            for k in range(L):
                p0 = (a[0] + ex * k / L, a[1] + ey * k / L)
                p1 = (a[0] + ex * (k + 1) / L, a[1] + ey * (k + 1) / L)
                mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
                g = _dem_at(d, mx + nx * 1.2, my + ny * 1.2)
                ok = (g is not None and (t["y"] - g) >= dropMin and in_parcel(d, mx, my)
                      and not _on_walled_edge(d, mx, my, 3.0)
                      and not _in_opening(d, mx, my))
                if ok:
                    segs.append(((p0[0] - nx * off, p0[1] - ny * off),
                                 (p1[0] - nx * off, p1[1] - ny * off),
                                 round(t["y"] - g, 2)))
                else:
                    segs.append(None)                  # 切れ目(開口・囲いのある辺)
        # 連続する区間を**折れ線**としてまとめる(弦に潰さない)
        runs = []
        for it in segs:
            if it is None:
                runs.append(None)
                continue
            p0, p1, dz = it
            if runs and runs[-1] is not None and \
               math.hypot(runs[-1][0][-1][0] - p0[0], runs[-1][0][-1][1] - p0[1]) < 0.30:
                runs[-1][0].append(p1)
                runs[-1][1] = max(runs[-1][1], dz)
            else:
                runs.append([[p0, p1], dz])
        for r9 in runs:
            if r9 is None:
                continue
            pts, dz = r9
            L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])) * K
            if L < minLen:
                continue
            # ⚠ 名は**始点の座標**から作る。算出順(j+1)だと、短くて落ちた run の分だけ
            #    以降の名が全部ずれ、実装との突き合わせが総崩れになる(2026-08-24 検図)。
            out.append({"name": "R_%s_u%+d_v%d" % (t["name"][:2], round(pts[0][0]), round(pts[0][1])),
                        "terrace": t["name"],
                        "pts": [[round(x, 2), round(y, 2)] for x, y in pts],
                        "len": round(L, 1), "drop": dz})
    _RAILS[id(d)] = out
    return out


def _seg_x(p, q, r, s):
    """線分 pq と rs が交わるか(端点接触は交差としない)。"""
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = cr(r, s, p), cr(r, s, q)
    d3, d4 = cr(p, q, r), cr(p, q, s)
    return ((d1 > 1e-9) != (d2 > 1e-9)) and ((d3 > 1e-9) != (d4 > 1e-9))


def _poly_x_rect(pts, u0, v0, u1, v1):
    """折れ線が矩形の内部を通る長さ(m でなく間)。0 なら交差なし。"""
    tot = 0.0
    for a, b in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) * 8))
        seg = 0
        for i in range(n):
            mx = a[0] + (b[0] - a[0]) * (i + 0.5) / n
            my = a[1] + (b[1] - a[1]) * (i + 0.5) / n
            if u0 <= mx <= u1 and v0 <= my <= v1:
                seg += 1
        tot += math.hypot(b[0] - a[0], b[1] - a[1]) * seg / n
    return tot


def base_check(d):
    """基壇石垣の露出が規約の中か。**下限は const.baseMin、上限は石垣の丈 4.0×s**
    (2026-08-24: 文章に 2.5m・検査に別の数字と二重に持っていたのを一本化した)。"""
    bad = []
    lo0 = d["const"]["baseMin"]
    for r in d["runs"]:
        if not r.get("base"):
            continue
        lo, hi = run_base(d, r)
        cap = d["const"]["baseUnit"] * r["s"]
        if lo < -0.02:
            bad.append("%s の天端が地盤の下 %.2fm(塀が土に埋まる)" % (r["name"], -lo))
        if hi > cap + 1e-9:
            bad.append("%s の露出の最大 %.2fm > 石垣の丈 %.2fm(s=%.2f)" % (r["name"], hi, cap, r["s"]))
    return bad


def _run_fp(d, r):
    """run の足跡(世界座標の四角形)。**練塀は境界線に跨り、長屋は外面が境界線に載る。**"""
    P = d["polygon"]
    a = edge_pt(P, r["edge"], r["s0"])
    b = edge_pt(P, r["edge"], r["s1"])
    nx, ny = _inward(P, r["edge"])
    if r["kind"] == "Nagaya":
        o0, o1 = 0.0, d["const"]["nagayaD"]           # 外面が境界線
    else:
        h = d["const"]["dobeiT"] / 2.0
        o0, o1 = -h, h                                # 境界線に跨る
    return [(a[0] + nx * o0, a[1] + ny * o0), (b[0] + nx * o0, b[1] + ny * o0),
            (b[0] + nx * o1, b[1] + ny * o1), (a[0] + nx * o1, a[1] + ny * o1)]


def _seg_dist(p, q, r, s):
    """線分 pq と rs の最短距離。"""
    def pd(pt, u, v):
        dx, dy = v[0] - u[0], v[1] - u[1]
        L2 = dx * dx + dy * dy
        tt = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((pt[0] - u[0]) * dx + (pt[1] - u[1]) * dy) / L2))
        return math.hypot(pt[0] - (u[0] + dx * tt), pt[1] - (u[1] + dy * tt))
    d1 = (q[0] - p[0], q[1] - p[1]); d2 = (s[0] - r[0], s[1] - r[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) > 1e-12:                              # 交差していれば 0
        ta = ((r[0] - p[0]) * d2[1] - (r[1] - p[1]) * d2[0]) / den
        tb = ((r[0] - p[0]) * d1[1] - (r[1] - p[1]) * d1[0]) / den
        if 0.0 <= ta <= 1.0 and 0.0 <= tb <= 1.0:
            return 0.0
    return min(pd(p, r, s), pd(q, r, s), pd(r, p, q), pd(s, p, q))


def _quad_overlap(qa, qb, step=0.02):
    """四角形どうしの重なり面積(ラスタ近似・m²)。**点接触を 0 と数えるのが目的**なので粗くてよい。"""
    xs = [p[0] for p in qa + qb]; ys = [p[1] for p in qa + qb]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    def inq(q, x, y):
        c = False
        for i in range(4):
            (ax, ay), (bx, by) = q[i], q[(i + 1) % 4]
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                c = not c
        return c
    a = 0.0; x = x0 + step / 2
    while x < x1:
        y = y0 + step / 2
        while y < y1:
            if inq(qa, x, y) and inq(qb, x, y):
                a += step * step
            y += step
        x += step
    return a


def footprint_support_check(d, step=0.02, tol=0.01):
    """**外周長屋の足跡が、段か基壇の天端に 100% 載っているか。**

    ⚠ 2026-08-31 四巡目で追加。⛔ `seat_fill_check` は run に沿って**内側 1.2m の1本線**しか
      測らないので、奥行 4.545m の長屋は**足跡の 3.3m ぶんが一度も標本されない**。
      「据面 0 件」は「長屋の内側 3.3m は測っていない」を含んでいた。
    ⛔ 現況が合格でも検査は要る — 辺12 の縁を 0.30m 動かすだけで 24.9m² の床が浮く。
    ⚠ **この検査は一度恒真だった**(2026-08-31 五巡目)。0 件を見ても効いている証拠にならないので、
      直したら必ず**破壊試験**(段の poly を潰し、全 run の `s` を 0.01 に落とす)で件数が出ることを確かめる。
    ⭕ 支えは段(`terraces[].poly`)**または**基壇石垣の天端(内向き 0〜2.4·s)。
      犬走りの帯は段の外だが基壇が受けるので、両方の和で測る。
    """
    K = d["const"]["ken"]
    gr9 = RGrid(d)
    bad = []
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        q = _run_fp(d, r)
        P9w = d["polygon"]
        nn = len(P9w)
        nx, ny = _inward(P9w, r["edge"])
        # ⭕ **隅では隣の辺の基壇も支えになる**(P0 では SE_Hei・底厚 1.8m が受ける)。
        #    効くのは自分の辺と両隣だけなので、その3辺の帯を先に畳んでおく(総当たりは遅すぎた)。
        bands = []
        for e8 in ((r["edge"] - 1) % nn, r["edge"], (r["edge"] + 1) % nn):
            a8 = P9w[e8]; b8 = P9w[(e8 + 1) % nn]
            L8 = math.hypot(b8[0] - a8[0], b8[1] - a8[1]) or 1e-9
            ex8, ey8 = (b8[0] - a8[0]) / L8, (b8[1] - a8[1]) / L8
            n8x, n8y = _inward(P9w, e8)
            for r8 in d["runs"]:
                if r8["edge"] == e8:
                    bands.append((a8, n8x, n8y, 2.4 * r8.get("s", 0.5), ex8, ey8, r8["s0"], r8["s1"]))
        xs = [p[0] for p in q]; ys = [p[1] for p in q]
        miss = 0.0
        x = min(xs)
        while x < max(xs):
            y = min(ys)
            while y < max(ys):
                inq = False
                c = False
                for i in range(4):
                    (ax, ay), (bx, by) = q[i], q[(i + 1) % 4]
                    if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                        c = not c
                inq = c
                if inq:
                    u9, v9 = gr9.L(x, y)
                    on_ter = any(tin(t9, u9, v9) for t9 in d["terraces"])
                    # 基壇の帯: **その run 自身の辺の線**からの垂直距離で測る。
                    # ⛔ `_par_near`(最寄りの辺)を使うと隅で辺が切り替わり、支えがあるのに
                    #    「載っていない」と誤検出する(2026-08-31: 0.004 m² が 0.87 m² に化けた)。
                    # ⭕ **隣の辺の基壇も支えになる。** 隅では自分の辺の帯を外れても、
                    #    直交する辺の基壇(P0 では SE_Hei・底厚 1.8m)が受ける。
                    # ⛔ **2026-08-31 五巡目**: ここに `a8[0] <= 0 or True and …` と書いていた。
                    #    `a8[0]` は辺の始点の**世界座標 X** で当区画は13頂点すべて x<0 なので、
                    #    第1項が常に真=**この検査は恒真だった**(支えを全部消しても 0 件を返した)。
                    #    検図が破壊試験で捕まえた。⭕ 現況の幾何は無罪で、壊れていたのは検査だけ。
                    on_base = any(
                        (-1e-9 <= (x - a8[0]) * n8x + (y - a8[1]) * n8y <= bt8 + 1e-9)
                        and (r8s0 - 1e-9 <= (x - a8[0]) * ex8 + (y - a8[1]) * ey8 <= r8s1 + 1e-9)
                        for (a8, n8x, n8y, bt8, ex8, ey8, r8s0, r8s1) in bands)
                    if not (on_ter or on_base):
                        miss += step * step
                y += step
            x += step
        if miss > tol:
            bad.append("%s の足跡のうち %.2f m² が段にも基壇にも載っていない" % (r["name"], miss))
    return bad


def perimeter_closure_check(d, step=0.02, inset=0.05):
    """**外周が全長で閉じているか** — 区画線を歩き、内側が何かで塞がっているかを測る。

    ⚠ 2026-08-31 の三巡目で作り直した。それまで当方が持っていたのは
      「隣り合う run の足跡どうしの最短距離」を見る検査で、**二度も誤った** —
      ①点接触を『閉じている』と数え(P0 で 1.19m² 開いていたのを 0 件と報告した)、
      ②その 0 件を根拠に『長屋の妻が塞ぐ』と指図に書いてしまった。
      ⛔ **隅の対どうしを見るのでは足りない。**穴は run と run の間ではなく、
      **run と区画線の間**に開く(折れ角が直角でないと妻面と辺の間に楔が開く)。
    ⭕ 区画線から `inset` だけ内へ入った点が、外周の部材のどれかに覆われていれば閉。
    ⛔ 開口は**部材が実際に塞ぐ幅**で閉と数える(run の隙間の幅ではない) —
      **表門は長屋門の躯体の桁行 `monW`**(躯体そのものが塞ぐ)、**木戸は門の幅 `komon.w`**。
      2026-08-31 三巡目: 木戸は開口 2.80m に対し `komon.w` 2.70m で、両端 0.05m ずつ素通しだった。
    """
    P9 = d["polygon"]
    n = len(P9)
    fps = [(_run_fp(d, r), r["name"]) for r in d["runs"]]
    for f in d.get("fences", []):                     # 木柵も囲い
        if "edge" in f:
            fps.append((_run_fp(d, dict(f, kind="Dobei")), f.get("name", "fence")))
    opens = []
    if d.get("gate"):
        opens.append((d["gate"], "表門", d["gate"].get("plan", {}).get("monW")))
    for k9 in (d.get("komon") or []):                 # 木戸は複数ありうる(list)
        opens.append((k9, k9.get("label", "木戸"), k9.get("w")))
    for g9, nm9, w9 in opens:
        e9 = g9.get("edge"); c9 = g9.get("s")
        if e9 is None or c9 is None or not w9:
            continue
        fps.append((_run_fp(d, {"edge": e9, "s0": c9 - w9 / 2.0, "s1": c9 + w9 / 2.0,
                                "kind": "Dobei"}), nm9 + "(扉)"))

    def covered(x, y):
        for q, _nm in fps:
            c = False
            for i in range(4):
                (ax, ay), (bx, by) = q[i], q[(i + 1) % 4]
                if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                    c = not c
            if c:
                return True
        return False

    own = set(r["edge"] for r in d["runs"]) | set(f["edge"] for f in d.get("fences", []) if "edge" in f)
    bad = []
    for e in range(n):
        if e not in own:
            continue                                  # 相手が建てる辺(松平境ほか)
        a, b = P9[e], P9[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        nx, ny = _inward(P9, e)
        holes, cur, s = [], None, 0.0
        while s <= L:
            t9 = s / L
            x = a[0] + (b[0] - a[0]) * t9 + nx * inset
            y = a[1] + (b[1] - a[1]) * t9 + ny * inset
            if covered(x, y):
                if cur is not None:
                    holes.append((cur, s)); cur = None
            elif cur is None:
                cur = s
            s += step
        if cur is not None:
            holes.append((cur, L))
        for h0, h1 in holes:
            if h1 - h0 > step * 1.5:                   # 1標本ぶんの丸めは拾わない
                bad.append("辺%d の s=%.2f〜%.2f(%.2fm)が素通し" % (e, h0, h1, h1 - h0))
    return bad


def perimeter_corner_check(d, tol=0.02):
    """**区画の隅で外周が閉じているか** — 隣り合う辺の run の**実足跡**で測る。

    ⚠ 2026-08-31 の再検図で追加した。それまで隅を見る検査は一つも無かった —
      `sashizu_lib.overlap_check` は `r["edge"] != gate["edge"]` で弾くので、
      **門の辺以外の run は総当たりに一度も入らない**。当方はそれを知らずに
      「重なりを消した」つもりで北東隅に 0.116m の素通しを作り、検図に捕まった。
    ⭕ **めり込みは正常、隙間だけが欠陥**(メモリ「門と塀の閉じは『隙間>めり込み』」)。
      塀は境界線に跨るので隅では必ず重なる。長屋は外面が境界線に載り、**妻面が隣の辺を塞ぐ**
      (辺0 の s0〜4.61 に run が無いのはこれ。走り s だけで測ると穴に見えるので足跡で測る)。
    ⛔ 門の開口は隅ではないのでここでは見ない(`gate_check` の担当)。
    ⚠ 隅部材(`build_kado` の腕)は runs に居ないので、この検査からは見えない。
      **腕で塞ぐ隅は帳簿の側で担保すること。**
    ⚠ **`fences` は見ない**(runs だけを回す)ので、木柵が付く隅(P5: 辺4 `W_Hei_C` ↔ 辺5 `F_Hori`)は
      黙って飛ばす。⭕ そこは `perimeter_closure_check` が全長で見ている。
    """
    P = d["polygon"]
    n = len(P)
    bad = []
    for v in range(n):                                # 頂点 v = 辺(v-1) と 辺(v) の隅
        ea, eb = (v - 1) % n, v
        ra = [r for r in d["runs"] if r["edge"] == ea]
        rb = [r for r in d["runs"] if r["edge"] == eb]
        if not ra or not rb:
            continue                                  # 片側に囲いが無い辺(相手が建てる)
        # ⚠ **ほぼ一直線の継ぎ目は「隅」ではない。** 折れが浅ければ楔は開きようがないので、
        #   面の重なりを求めるのは過剰(2026-08-31: P2 の折れは 1.1° で、全長を歩く検査は閉と出る)。
        ua = (P[v][0] - P[ea][0], P[v][1] - P[ea][1])
        ub = (P[(v + 1) % n][0] - P[v][0], P[(v + 1) % n][1] - P[v][1])
        la = math.hypot(*ua) or 1e-9
        lb = math.hypot(*ub) or 1e-9
        turn = math.degrees(math.acos(max(-1.0, min(1.0,
               (ua[0] * ub[0] + ua[1] * ub[1]) / (la * lb)))))
        ca = max(ra, key=lambda r: r["s1"])           # 頂点に一番近い run
        cb = min(rb, key=lambda r: r["s0"])
        fa, fb = _run_fp(d, ca), _run_fp(d, cb)
        best = min(_seg_dist(fa[i], fa[(i + 1) % 4], fb[j], fb[(j + 1) % 4])
                   for i in range(4) for j in range(4))
        # ⛔ **最短距離だけでは足りない。**足跡が**一点で接する**と距離 0 を返すが、
        #    その先に楔が開いていることがある(2026-08-31 三巡目: P0 で 1.19m² 開いていたのを
        #    当検査は 0 件と報告した。当方はそれを『閉じている』と指図に書いてしまった)。
        #    ⭕ **面で重なっていることを要件にする** — 点接触と面接触を区別する。
        ov = _quad_overlap(fa, fb)
        if best > tol:
            bad.append("頂点P%d(辺%d %s ↔ 辺%d %s)の隅に素通し %.3fm"
                       % (v, ea, ca["name"], eb, cb["name"], best))
        elif ov <= 1e-6 and turn >= 5.0:
            bad.append("頂点P%d(辺%d %s ↔ 辺%d %s・折れ %.1f°)は**点接触**で面で重なっていない — "
                       "折れ角が直角でないと妻面と辺の間に楔が開く"
                       % (v, ea, ca["name"], eb, cb["name"], turn))
    return bad


def seat_fill_check(d):
    """**面の縁と宣言した run の内側が、据面より落ち込んでいないか。**
    2026-08-24 検図: 段の多角形が区画線から最大4.5m離れており、その帯は段の外なので盛土されず、
    三べ坂の正面 96m にわたって据面より最大 2.91m 低い溝が残っていた。
    段の頂点だけを見る検査では捕まらないので、run に沿って 1m 刻みで内側 1.2m の地盤を測る。"""
    K = d["const"]["ken"]
    in_parcel(d, 0, 0)
    Pg = _PIN[id(d)]
    cu = sum(p[0] for p in Pg) / len(Pg); cv = sum(p[1] for p in Pg) / len(Pg)
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    out = []
    for r in d["runs"]:
        # ⚠ **両符号を測る。** 2026-08-26 松平 EDO-0025 / 土井: 埋没だけを測って
        #   逆(塀が浮く/内から埋まる)を構造的に見逃す検査の形。当家も「据面より低い」しか
        #   見ておらず、**塀が内側の地盤に最大1.94m 埋まっている2本**を見逃していた。
        #   溝(+)は面の縁の run だけの問題だが、**埋没(−)は全 run に効く**。
        onedge = str(r.get("on", "")).startswith("面の縁")
        e = r["edge"]; a, b = Pg[e], Pg[(e + 1) % len(Pg)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / L, dx / L
        if (a[0] + nx - cu) ** 2 + (a[1] + ny - cv) ** 2 > \
           (a[0] - nx - cu) ** 2 + (a[1] - ny - cv) ** 2:
            nx, ny = -nx, -ny
        n = 0; bad = 0; mx = 0.0; bur = 0; bmx = 0.0
        sv = r["s0"]
        while sv <= r["s1"]:
            t = sv / K / L
            u = a[0] + dx * t + nx * (1.2 / K); v = a[1] + dy * t + ny * (1.2 / K)
            nat = _dem_at(d, u, v)
            if nat is not None:
                g = graded_y(d, u, v, nat, we)
                g = nat if g is None else g
                n += 1
                dz9 = rseat(r, sv) - g
                if onedge and dz9 > 0.5:
                    bad += 1; mx = max(mx, dz9)
                if dz9 < -0.5:
                    bur += 1; bmx = max(bmx, -dz9)
            sv += 1.0
        if bad:
            out.append((r["name"], bad, n, round(mx, 2)))
        if bur:
            out.append(("%s ⛔内から埋まる" % r["name"], bur, n, round(bmx, 2)))
    return out


def plinth_check(d):
    """**隣家が自分の側に建てている基壇の天端を、当家の塀の据面が下回っていないか。**
    下回ると隣家の土が当家の塀の足元より高くなる(2026-08-24 検図)。"""
    bad = []
    for pl in neighbor_plinth(d):
        n = max(2, int((pl["s1"] - pl["s0"]) / 0.5))
        worst = None
        for i in range(n + 1):
            sv = pl["s0"] + (pl["s1"] - pl["s0"]) * i / n
            r = next((x for x in d["runs"]
                      if x["edge"] == pl["edge"] and x["s0"] - 1e-6 <= sv <= x["s1"] + 1e-6), None)
            if r is None:
                continue
            gap = pl["coping"] - rseat(r, sv)
            if gap > 0.02 and (worst is None or gap > worst[1]):
                worst = (r["name"], gap, sv)
        if worst:
            bad.append("辺%d s=%.1f で %s の据面が隣家の基壇天端 %.2f を %.2fm 下回る"
                       % (pl["edge"], worst[2], worst[0], pl["coping"], worst[1]))
    return bad


def base_thin(d):
    """基壇の露出が `const.baseMin` を下回る = **そこは基壇を置かず塀が犬走りに直に載る**。
    ⚠ これは欠陥ではない(2026-08-24 検図で規則を整理した) — 面の縁を面の高さで通す以上、
    外の地盤が面の高さに迫る区間では基壇が消えるのが正しい。長さだけ図に出す。"""
    lo0 = d["const"]["baseMin"]
    out = []
    for r in d["runs"]:
        if not r.get("base"):
            continue
        n = max(2, int((r["s1"] - r["s0"]) / 0.5))
        g = 0
        for i in range(n + 1):
            sv = r["s0"] + (r["s1"] - r["s0"]) * i / n
            if _run_exposure(d, r, sv) < lo0:
                g += 1
        if g:
            out.append((r["name"], (r["s1"] - r["s0"]) * g / float(n + 1)))
    return out


def _prof_y(d, edge, sv):
    """辺 `edge` の走り sv における**外側の地盤**(edgeProfile の線形補間)。
    ⚠ edgeProfile は main() が毎回 DEM から取り直して書き戻す(静的に持つと腐る)。"""
    prof = d.get("edgeProfile", {}).get(str(edge))
    if not prof:
        return None
    if sv <= prof[0][0]:
        return prof[0][1]
    for (a1, y1), (b1, y2) in zip(prof, prof[1:]):
        if a1 <= sv <= b1:
            return y1 + (y2 - y1) * (sv - a1) / (b1 - a1)
    return prof[-1][1]


def _run_exposure(d, r, sv):
    """run の走り sv における基壇の露出(天端 − その位置の地盤)。"""
    gy = _prof_y(d, r["edge"], sv)
    return 0.0 if gy is None else rseat(r, sv) - gy


def gate_module_check(d):
    """**長屋門の柱割りが江戸間で閉じるか。** 桁行9間 = 門戸6間 + 両端の番所 各1.5間、
    門口(扉の開口)=2間。⛔ どれか一つを丸めた数字で持つと、閉じているつもりで閉じない。
    ⚠ 2026-09-01 六巡目: `bansho.w` が 2.70(1.5間=2.727)で、門戸が 10.96m となり
      6間ちょうど(10.908)から 0.05m ずれていた。番所の位置は見付図と平面図で別々に
      直書きされていたので、この 0.05m は図の上では見えなかった。"""
    gp = d["gate"]["plan"]; K = d["const"]["ken"]
    bw = gp.get("bansho", {}).get("w", 0.0)
    n = gp.get("bansho", {}).get("count", 2)
    out = []
    for nm, got, ken in (("桁行 monW", gp["monW"], 9.0), ("番所 bansho.w", bw, 1.5),
                         ("門口 monkuchi", gp.get("monkuchi", 0.0), 2.0)):
        if abs(got - ken * K) > 0.005:
            out.append("%s = %.3f が %.1f間 = %.3f と %.3f 食い違う"
                       % (nm, got, ken, ken * K, abs(got - ken * K)))
    rest = gp["monW"] - n * bw
    if abs(rest - 6.0 * K) > 0.005:
        out.append("門戸 = 桁行 − 番所%d箇所 = %.3f が 6間 = %.3f と %.3f 食い違う"
                   % (n, rest, 6.0 * K, abs(rest - 6.0 * K)))
    if gp.get("monkuchi", 0.0) > rest + 1e-9:
        out.append("門口 %.3f が門戸 %.3f を超える" % (gp["monkuchi"], rest))
    return out


def keri_check(d):
    """石段の蹴上は const.keri を**上限**とする(実寸は段数の割り付けで決まる)。"""
    lim = d["const"]["keri"]
    return ["%s の蹴上 %.4f > 上限 %.2f" % (k["name"], k["keri"], lim)
            for k in d["kaidans"] if k["keri"] > lim + 1e-9]


def rel(a, b):
    """矩形 a から見た矩形 b の方位を**算出**する。u+ = 北 / v+ = 西。
    ⚠ 2026-08-25 まで3巡続けて方位語を取りこぼしたので、検査に落とす。"""
    du = (b["u0"] + b["u1"]) / 2.0 - (a["u0"] + a["u1"]) / 2.0
    dv = (b["v0"] + b["v1"]) / 2.0 - (a["v0"] + a["v1"]) / 2.0
    ns = "北" if du > 0.5 else ("南" if du < -0.5 else "")
    ew = "西" if dv > 0.5 else ("東" if dv < -0.5 else "")
    return (ns + ew) or "同じ位置"


def face(a, b):
    """矩形 a のどの面で b に接しているか。u0=南面 / u1=北面 / v0=東面 / v1=西面。"""
    eps = 0.05
    if abs(a["u0"] - b["u1"]) < eps:
        return "南面"
    if abs(a["u1"] - b["u0"]) < eps:
        return "北面"
    if abs(a["v0"] - b["v1"]) < eps:
        return "東面"
    if abs(a["v1"] - b["v0"]) < eps:
        return "西面"
    return None


def compass_check(d):
    """**注記に書いた方位語が、グリッドから算出した方位と合っているか。**
    u+ = 北 / v+ = 西。3巡続けて取りこぼしたので機械で見張る。"""
    boxes = dict((o["name"], o) for o in d["munes"] + d["service"] + d["gardens"] + d["links"])
    JA = dict((v, k) for k, v in MUNE_JA.items())
    bad = []
    names = [MUNE_JA.get(nm, ob.get("label", nm)) for nm, ob in boxes.items()]
    W8 = ("北西", "南西", "北東", "南東", "北", "南", "東", "西")
    # ⚠ **物の名前を方位の主張と読まない。** 「長局の北の坪」は庭の**名**であって
    #   「長局から見て北」という主張ではない。名の中に `<棟>の<方位>` が現れる物は、
    #   走査の前に伏せる(2026-09-02: 庭の改名で偽の指摘が3件出た)。
    #   ⛔ 棟の名そのもの(「玄関棟」)は伏せない — 伏せると検査が死ぬ。
    mask = sorted([n9 for n9 in names
                   if any(j9 + "の" + w9 in n9 for j9 in names for w9 in W8 if j9 != n9)],
                  key=len, reverse=True)

    def _mask(t9):
        for n9 in mask:
            t9 = t9.replace(n9, "〓" * len(n9))
        return t9

    for o in d["munes"] + d["service"] + d["gardens"] + d["links"] + d.get("wells", []):
        t = o.get("_")
        if not isinstance(t, str):
            continue
        t = _mask(t)
        for nm, ob in boxes.items():
            ja = MUNE_JA.get(nm, ob.get("label", nm))
            if ja not in t or ja == MUNE_JA.get(o.get("name"), ""):
                continue
            me = o if "u0" in o else {"u0": o["u"] - 0.5, "u1": o["u"] + 0.5,
                                      "v0": o["v"] - 0.5, "v1": o["v"] + 0.5}
            want = rel(ob, me)                      # 相手から見た当方の方位
            fc = face(ob, me)
            for w in ("北西", "南西", "北東", "南東", "北", "南", "東", "西"):
                if ja + "の" + w in t or ja + "棟の" + w in t:
                    if w != want:
                        bad.append("%s の注記『%sの%s』は算出では **%s**"
                                   % (o.get("name"), ja, w, want))
                    break
            for w in ("北面", "南面", "東面", "西面"):
                if ja + "の" + w in t or ja + "棟の" + w in t:
                    if fc and w != fc:
                        bad.append("%s の注記『%sの%s』は算出では **%s**"
                                   % (o.get("name"), ja, w, fc))
                    break
    # 動線(折れ線)の進行方向と終点の面も見る。
    # ⚠ 2026-08-25 検図: routes は走査対象に入っておらず、「路地を北へ」(実際は西)・
    #    「台所棟の南面」(実際は西面)が素通りしていた。
    for r in d.get("routes", []):
        t = r.get("_")
        if not isinstance(t, str) or len(r.get("pts", [])) < 2:
            continue
        t = _mask(t)
        a, b = r["pts"][-2], r["pts"][-1]
        end = {"u0": b[0] - 0.5, "u1": b[0] + 0.5, "v0": b[1] - 0.5, "v1": b[1] + 0.5}
        for nm, ob in boxes.items():
            ja = MUNE_JA.get(nm, ob.get("label", nm))
            if ja not in t:
                continue
            near = (ob["u0"] - 2.0 <= b[0] <= ob["u1"] + 2.0
                    and ob["v0"] - 2.0 <= b[1] <= ob["v1"] + 2.0)
            if not near:
                continue
            fc = ("南面" if b[0] < ob["u0"] else "北面" if b[0] > ob["u1"] else
                  "東面" if b[1] < ob["v0"] else "西面" if b[1] > ob["v1"] else None)
            for w in ("北面", "南面", "東面", "西面"):
                if ja + "の" + w in t or ja + "棟の" + w in t:
                    if fc and w != fc:
                        bad.append("%s の注記『%sの%s』は算出では **%s**" % (r["name"], ja, w, fc))
                    break
    return bad


def edge_drops(d, step=1.5):
    """**段の縁を 1.5間刻みで測る**(`sashizu.md` §3b)。外周の囲いが受けている区間は除く。
    返すのは段ごとの [(落差, 盛土厚, 自然勾配[%], u, v)]。
    ⚠ 2026-08-25: 「土留めか法面か」を決める手順がこれを要求しているのに、表が無いまま
    2026-08-23 に土留めを全廃していた。"""
    out = {}
    for t in d["terraces"]:
        poly = tpoly(t)
        n = len(poly)
        # ⛔ **外向きは重心からの放射方向で取らない。** 段は凹多角形(門口の切り欠きなど)なので、
        #    凹部では重心方向が段の**内側**を向く。2026-08-25 検図: 門前面の80測点中40が真の外法線と
        #    60°超ずれ、15測点は「外側1.5間」が段の中に落ちて、何も測っていなかった。
        #    **辺の向きと多角形の巻き方向(符号付き面積)から法線を出す。**
        area2 = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
                    for i in range(n))
        sgn = 1.0 if area2 > 0 else -1.0       # 反時計回りなら +
        rows = []
        for a, b in zip(poly, poly[1:] + [poly[0]]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 1e-9:
                continue
            nx, ny = sgn * (b[1] - a[1]) / L, -sgn * (b[0] - a[0]) / L   # 外向き法線
            k = 0.0
            while k < L:
                tt = k / L
                u = a[0] + (b[0] - a[0]) * tt; v = a[1] + (b[1] - a[1]) * tt
                k += step
                if not in_parcel(d, u, v) or _on_walled_edge(d, u, v, 3.0):
                    continue
                ou, ov = u + nx * step, v + ny * step
                if tin(t, ou, ov):
                    continue                   # 外側の標本が段の中に落ちる = 測れない
                g0 = _dem_at(d, u, v)
                go = _dem_at(d, ou, ov)
                if g0 is None or go is None:
                    continue
                rows.append((t["y"] - go, t["y"] - g0,
                             abs(g0 - go) / (step * d["const"]["ken"]) * 100.0, u, v))
        out[t["name"]] = sorted(rows, reverse=True)
    return out


def edge_drop_check(d):
    """**盛土が、法面を出せないほど急な自然の斜面の上に載っていないか。**
    載っていれば法面が着地せず、土が崩れる(土留めか、段の縁を引くかのどちらかが要る)。"""
    lim = 100.0 / d["const"]["batterFill"]
    # ⚠ 1間格子の双一次DEMを 67% の斜面で測るので、**2ポイント程度の超過は分解能の内**。
    #   そこを追うのは偽の精度なので、超過が 2.0pt を超えるものだけを不合格にする。
    EPS = 2.0
    bad = []
    for nm, rows in edge_drops(d).items():
        c = [r for r in rows if r[1] > 0.5 and r[2] > lim + EPS]
        if c:
            bad.append("%s の縁 %d測点で、盛土 %.2fm が自然勾配 %.0f%%(法面 %.0f%% より急)の上に載る"
                       % (TERR_JA.get(nm, nm), len(c), max(x[1] for x in c),
                          max(x[2] for x in c), lim))
    return bad


def edge_drop_table(d):
    """§3b の実測表。**土留めか法面かは、この表を見てから決める。**"""
    lim = 100.0 / d["const"]["batterFill"]
    rows = []
    for nm, rs in edge_drops(d).items():
        if not rs:
            rows.append("<tr><td>%s</td><td colspan='6' class='note'>郭の内側の縁は無し"
                        "(全周を外周の囲いが受けている)</td></tr>" % TERR_JA.get(nm, nm))
            continue
        band = []
        for lo, hi, lab in ((3.0, 1e9, "3.0m 超"), (2.0, 3.0, "2.0〜3.0m"),
                            (1.0, 2.0, "1.0〜2.0m"), (-1e9, 1.0, "1.0m 未満")):
            c = [r for r in rs if lo < r[0] <= hi]
            band.append("%s %d(%.0f%%)" % (lab, len(c), 100.0 * len(c) / len(rs)))
        ng = [r for r in rs if r[1] > 0.5 and r[2] > lim]
        rows.append("<tr><td>%s</td><td>%d</td><td>%+.2f 〜 %+.2f m</td>"
                    "<td class='note'>%s</td><td>%.2fm</td><td>%.0f%%</td><td>%s</td></tr>"
                    % (TERR_JA.get(nm, nm), len(rs), rs[-1][0], rs[0][0], " / ".join(band),
                       max(r[1] for r in rs), max(r[2] for r in rs),
                       ("<b>0</b>" if not ng else
                        "%d(超過は最大 %+.1f pt)" % (len(ng), max(r[2] for r in ng) - lim))))
    return ("<h3>段の縁の実測(1.5間刻み・外周の囲いが受ける区間は除く)</h3>"
            "<p class='cap'><b>土留めを置くか法面で摺り付けるかは、この表を見てから決める</b>"
            "(<code>sashizu.md</code> §3b)。落差は「段の高さ − 縁の外 1.5間 の地山」。"
            "⚠ 最後の列は<b>盛土が法面(1:%(batter).1f = %(lim).0f%%)より急な自然斜面の上に載っている測点</b>で、"
            "そこは法面が着地しないので<b>土留めを置くか、段の縁を内へ引く</b>しかない。"
            "2026-08-25 に主面の北東の縁を法面の着地条件で内へ引いた(残数は上の表)。"
            "⚠ <b>合格線 %(eps).1fpt は分解能からの独立な導出ではない</b>(実測の最大値の直上に置いた) — "
            "1間格子・双一次補間・1.5間の測線という条件から先に許容 pt を出せていないので、"
            "<b>残る測点は「分解能に埋もれて判定不能」</b>として扱い、"
            "<code>_pending</code> に残してある。⛔ 次に測点が線を超えたときに線を動かさないこと。</p>"
            "<div class='tw'><table><thead><tr><th>段</th><th>測点</th><th>落差</th>"
            "<th class='note'>落差の分布</th><th>最大の盛土</th><th>最大の自然勾配</th>"
            "<th>法面が出せない測点</th></tr></thead><tbody>%(rows)s</tbody></table></div>"
            % {"batter": d["const"]["batterFill"], "lim": lim, "eps": 2.0,
               "rows": "".join(rows)})


def neighbor_plinth(d):
    """**隣家が自分の側に建てている基壇石垣を、隣家の指図から幾何で引く。**
    ⛔ **値を写さない・辺番号で引かない**(2026-08-26 土井 EDO-0012)。
    隣家の識別子(辺番号・run名・s)は**相手の座標系の番号**なので、写すと
    ①相手が値を直したときに追随せず ②辺番号の対応を取り違える。
    当家の辺の上の点が相手のどの辺の s に当たるかを**座標で**求めて引き直す。"""
    out = []
    for src, label in (("doi_sashizu.json", "土井"), ("matsudaira_dewa_sashizu.json", "松平"),
                       ("sanno_sashizu.json", "山王")):
        try:
            nb = json.load(open(os.path.join(DOC, src), encoding="utf-8"))
        except Exception:
            continue
        NP = nb.get("polygon")
        pl = nb.get("boundaryPlinth") or nb.get("neighborPlinth") or []
        if not NP or not pl:
            continue
        P = d["polygon"]
        n = len(P)
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 1e-9:
                continue
            k = 0.0
            runlen = {}
            while k <= L:
                t = k / L
                x = a[0] + (b[0] - a[0]) * t; z = a[1] + (b[1] - a[1]) * t
                # 相手の辺の上か
                best = None
                for j in range(len(NP)):
                    c, e = NP[j], NP[(j + 1) % len(NP)]
                    dx, dz = e[0] - c[0], e[1] - c[1]
                    L2 = dx * dx + dz * dz or 1e-9
                    tt = max(0.0, min(1.0, ((x - c[0]) * dx + (z - c[1]) * dz) / L2))
                    dd = math.hypot(x - (c[0] + dx * tt), z - (c[1] + dz * tt))
                    if best is None or dd < best[0]:
                        best = (dd, j, tt * math.sqrt(L2))
                if best[0] > 1.5:
                    k += 0.5
                    continue
                for q in pl:
                    if q["edge"] == best[1] and q["s0"] - 0.3 <= best[2] <= q["s1"] + 0.3:
                        key = (q["coping"], round(4.0 * q.get("s", 0.2), 2))
                        runlen.setdefault(key, []).append(k)
                        break
                k += 0.5
            for (cop, h9), ks in runlen.items():
                out.append({"edge": i, "s0": round(min(ks), 2), "s1": round(max(ks), 2),
                            "coping": cop, "h": h9, "src": label,
                            "_": "%s の指図から**幾何で引いた**(値も区間も写さない)" % label})
    return out


PROGRAM_MD = os.path.expanduser(
    "~/.claude/skills/unity-buke-yashiki/references/estate-types.md")


def _gardens_facing_zashiki(d):
    """**座敷の前面にある庭**の数。⛔ 「gardens というキーがある」ではない。

    ⚠ 2026-09-01 庭方: 従前は `json.dumps(d)` に "gardens" が含まれるかを見ていたので
      **恒真**だった(庭を1つも持たない図でも達成と出る)。
    ⭕ 庭が接している棟の面に**室が1間以上退いている**(=入側/縁がある)ことを要件にする。
      妻(白壁)に向いた庭は座敷から見えないので数えない。
    """
    n = 0
    for g in d.get("gardens", []):
        gu0, gu1 = sorted((g["u0"], g["u1"]))
        gv0, gv1 = sorted((g["v0"], g["v1"]))
        for m in d.get("munes", []):
            if not all(k in m for k in ("u0", "u1", "v0", "v1")):
                continue
            mu0, mu1 = sorted((m["u0"], m["u1"]))
            mv0, mv1 = sorted((m["v0"], m["v1"]))
            touch_u = (abs(gu1 - mu0) < 1e-6 or abs(gu0 - mu1) < 1e-6) and gv1 > mv0 and gv0 < mv1
            touch_v = (abs(gv1 - mv0) < 1e-6 or abs(gv0 - mv1) < 1e-6) and gu1 > mu0 and gu0 < mu1
            if not (touch_u or touch_v):
                continue
            # 接した面の内側 1間に室があるか(入側/縁の有無の代理)
            rooms = m.get("rooms") or []
            if not rooms:
                continue
            if touch_u:
                edge = mu0 if abs(gu1 - mu0) < 1e-6 else mu1
                deep = any(min(abs(r.get("u0", 1e9) - edge), abs(r.get("u1", 1e9) - edge)) >= 1.0 - 1e-6
                           for r in rooms if "u0" in r)
            else:
                edge = mv0 if abs(gv1 - mv0) < 1e-6 else mv1
                deep = any(min(abs(r.get("v0", 1e9) - edge), abs(r.get("v1", 1e9) - edge)) >= 1.0 - 1e-6
                           for r in rooms if "v0" in r)
            if deep:
                n += 1
                break
    return n


def program_check(d):
    """**在るべき役割の一覧を、スキルの表(外の錨)から読んで照合する。**
    ⚠ 2026-08-26 土井 EDO-0013: 錨が無いと**役割と棟を同時に消せば検査が通る**。
    当家の `program`(json)ではなく `estate-types.md` の表を毎回読む。"""
    rows = []
    try:
        md = open(PROGRAM_MD, encoding="utf-8").read()
    except Exception:
        return []
    i = md.find("上屋敷が備える役割")
    if i < 0:
        return []
    seg = md[i:]
    j = seg.find("\n#", 1)          # ⚠ 次の見出しで切る。切らないと同じ file の別の表を拾う
    for line in (seg[:j] if j > 0 else seg).split("\n"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) == 3 and c[1] and c[0] not in ("役割", "---") and "-" not in c[1][:3]:
            rows.append(tuple(c))
    # ⛔ **文字列一致をやめた(2026-09-02 検図 K058・当邸4例目)。**
    #   `json.dumps(d)` への一致は、考証の本文に「**当図に表役所という棟は無く**」と書いた瞬間に
    #   「表役所=有る」と刷る。否定文が検査を通す型で、「表門」「練塀(外構)」もキー名一致で
    #   恒真だった(練塀 run を全部消しても True)。⭕ **物を数える述語だけにする。**
    def _munes(*names):
        return [m for m in d.get("munes", [])
                if MUNE_JA.get(m["name"], m["name"]) in names or m["name"] in names]

    def _rooms(*keys):
        return [r for m in d.get("munes", []) for r in (m.get("rooms") or [])
                if any(k in str(r.get("name", "")) for k in keys)]

    def _svc(*keys):
        return [o for o in d.get("service", [])
                if any(k in str(o.get("label", "")) + str(o.get("name", "")) for k in keys)]
    PRED = {
        # ⛔ 「plan という欄がある」では弱い(空の辞書でも通る)。**躯体の実体**を数える。
        "表門": lambda d9: bool((d9.get("gate", {}).get("plan") or {}).get("monW"))
                          and bool((d9.get("gate", {}).get("plan") or {}).get("bansho")),
        "表長屋": lambda d9: any(r["kind"] == "Nagaya" for r in d9.get("runs", [])),
        "練塀(外構)": lambda d9: any(r["kind"] == "Dobei" for r in d9.get("runs", [])),
        "表役所": lambda d9: bool(_munes("表役所", "Yakusho") or _rooms("御役所", "表役所")),
        "玄関・式台": lambda d9: bool(_rooms("御玄関", "御式台")),
        "書院": lambda d9: bool(_munes("書院棟", "Shoin") or _rooms("書院", "上段之間")),
        "居間・中奥": lambda d9: bool(_munes("中奥棟", "Nakaoku") or _rooms("御座之間")),
        "奥向": lambda d9: bool(_munes("奥向棟", "Okumuki")),
        "台所・勝手": lambda d9: bool(_munes("台所棟", "Daidokoro") or _rooms("御台所")),
        "湯殿・雪隠": lambda d9: bool(_rooms("御湯殿")) and bool(_rooms("雪隠", "厠")),
        "局(女中部屋)": lambda d9: bool(_munes("長局", "Nagatsubone")),
        "御錠口": lambda d9: any(l.get("kind") == "御錠口" for l in d9.get("links", [])),
        "厩": lambda d9: bool(_svc("厩") or _munes("厩棟", "Umaya")),
        "土蔵": lambda d9: bool(_svc("土蔵")),
        "家中長屋": lambda d9: bool(_svc("家臣長屋")),
        "米蔵": lambda d9: bool(_svc("米蔵")),
        "火消道具蔵・御駕籠蔵": lambda d9: bool(_svc("火消道具蔵") and _svc("御駕籠蔵")),
        "庭(座敷の前面)": lambda d9: _gardens_facing_zashiki(d9) > 0,
        "井戸": lambda d9: len(d9.get("wells", [])) > 0,
        "隅櫓": lambda d9: len(d9.get("yagura", [])) > 0,
        "稲荷社": lambda d9: bool(_svc("稲荷")),
        "馬場・作事小屋": lambda d9: bool(_svc("馬場", "作事") or _munes("馬場")),
        "中門": lambda d9: any((w9.get("gap") or {}).get("kind") == "中門"
                             for w9 in d9.get("kekkai", []))
                          or any(k9.get("kind") == "中門" for k9 in d9.get("komon", [])),
    }
    out = []
    for role, need, src in rows:
        pr = PRED.get(role)
        # ⛔ **述語の無い役割を「達成」にしない。**表が増えたときに黙って ○ が付くのを防ぐ。
        ok9 = pr(d) if pr else None
        out.append((role, need, src, ok9))
    return out


def coping_check(d):
    """**基壇の天端に、犬走りと塀の掛かりが乗るか。**
    練塀は基壇の天端と背後の盛土にまたがって載る(石垣は擁壁であって基礎ではない)ので、
    天端に要るのは「塀の全厚」ではなく **犬走り + 塀の掛かり**。"""
    need = d["const"]["inubashiri"] + d["const"]["copingBear"]
    bad = []
    for r in d["runs"]:
        if not r.get("base"):
            continue
        top = 1.4 * r["s"]
        if top < need - 1e-9:
            bad.append("%s の基壇の天端 %.2fm < 犬走り%.2f+塀の掛かり%.2f = %.2fm(s=%.2f)"
                       % (r["name"], top, d["const"]["inubashiri"],
                          d["const"]["copingBear"], need, r["s"]))
    return bad


def clearance_check(d):
    """**建物どうしの隙間と、外周の囲いからの離隔。**
    ⚠ 2026-08-25 検図: どちらも図が宣言した規則を図自身が破っていたのに、
    検査が無かった(`overlap_check` は重なり0しか見ない)。
    ① 土蔵は延焼を切る独立建物なので、木造の棟とは 1間(1.818m)以上あける。
    ② 家臣長屋は練塀の躯体と基壇の底から `heiT/2 + 犬走り + 0.5s` をあける
       (必要離隔は run の `s` に比例する — 1.50m の定数ではない)。"""
    K = d["const"]["ken"]
    bad = []
    boxes = [(o["name"], o) for o in d["munes"] + d["service"]]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, a = boxes[i]; n2, b = boxes[j]
            if not (n1.startswith("Dozo") or n2.startswith("Dozo")):
                continue
            gu = max(a["u0"] - b["u1"], b["u0"] - a["u1"], 0.0)
            gv = max(a["v0"] - b["v1"], b["v0"] - a["v1"], 0.0)
            if gu > 0 and gv > 0:
                continue                              # 斜めに離れている
            gap = max(gu, gv) * K
            if 0.0 < gap < 1.818 - 1e-6:
                bad.append("%s ↔ %s の隙間 %.2fm < 1間(土蔵は延焼を切る独立建物)" % (n1, n2, gap))
    in_parcel(d, 0, 0)
    for o in d["service"]:
        if not o["name"].startswith("KN_"):
            continue
        best = None
        for r in d["runs"]:
            for (uu, vv) in ((o["u0"], o["v0"]), (o["u1"], o["v0"]),
                             (o["u0"], o["v1"]), (o["u1"], o["v1"])):
                dd, e, sv = _par_near(d, uu, vv)
                if r["edge"] != e or not (r["s0"] - 1.0 <= sv <= r["s1"] + 1.0):
                    continue
                if best is None or dd < best[0]:
                    best = (dd, r)
        if best is None:
            bad.append("%s の最寄りの辺に run が無い(木柵か相手所有の辺)— **離隔の検査の対象外**"
                       % o["name"])
            continue
        # 法尻の内縁は基壇の芯から 1.2s。塀の半分に足すのではなく **max** を取る
        # (2026-08-25 検図: s=1.0 で 0.12m 過小、s=0.5 で 0.22m 過大だった)。
        need = (max(d["const"]["dobeiT"] / 2.0, 1.2 * best[1]["s"])
                + d["const"]["inubashiri"])
        got = best[0] * K
        if got < need - 1e-6:
            bad.append("%s の離隔 %.2fm < 必要 %.2fm(%s・s=%.2f)"
                       % (o["name"], got, need, best[1]["name"], best[1]["s"]))
    return bad


def crossing_check(d):
    """**図で決めた不変条件を機械検査に落とす**(§B-5)。
    2026-08-24: 竹垣を算出にした結果 御玄関を 21.7m 貫通し、坂を引き直した結果
    勝手動線が白洲を 16.0m 横切った — どちらも「直した結果を検査していない」ため。"""
    K = d["const"]["ken"]
    bad = []
    boxes = [(m["name"], m["u0"], m["v0"], m["u1"], m["v1"]) for m in d["munes"]] + \
            [(s["name"], s["u0"], s["v0"], s["u1"], s["v1"]) for s in d["service"]]
    # ⚠ **2026-09-02: 竹垣の貫通検査から「庭」を外した。**
    #   §4 で主面の全面を12区画の庭に割り当てたので、**法肩の竹垣は必ずどれかの庭の中を通る**
    #   (法肩は庭の中にある)。庭を箱に残すと検査が構造的に落ち、意味を持たない。
    #   ⛔ **緩めたのではない** — 竹垣が横切ってはいけないのは庭の**点景**なので、
    #   `niwa_cross_check()` で汀線・築山・園路・飛石・石組・灯籠・結界塀を見張る。
    # ⚠ 勝手動線の側は「入れない庭」(`katteFree`)だけを見る — 勝手庭・勝手の一画・
    #   南の芝谷・南西の樹林は**通さないと台所の裏へ回れない**(§4・§6 が明示する)。
    katte_boxes = [(g["label"], g["u0"], g["v0"], g["u1"], g["v1"])
                   for g in d.get("gardens", []) if g.get("katteFree")]
    for rl in auto_rails(d):
        for nm, u0, v0, u1, v1 in boxes:
            L = _poly_x_rect(rl["pts"], u0, v0, u1, v1) * K
            if L > 0.3:
                bad.append("%s(竹垣) が %s を %.1fm 貫通" % (rl["name"], nm, L))
        for a, b in zip(rl["pts"], rl["pts"][1:]):
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if not in_parcel(d, mx, my):
                bad.append("%s(竹垣) が区画の外: (%.1f, %.1f)" % (rl["name"], mx, my))
                break
        # 竹垣は昇り降りの動線を塞がない(参道・石段・坂)。図が自分で宣言した規則。
        for a, b in zip(rl["pts"], rl["pts"][1:]):
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if _in_opening(d, mx, my):
                bad.append("%s(竹垣) が参道・石段・坂の開口を塞ぐ: (%.1f, %.1f)"
                           % (rl["name"], mx, my))
                break
        # 外周の囲いが載っている辺を二重になぞらない
        for a, b in zip(rl["pts"], rl["pts"][1:]):
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if _on_walled_edge(d, mx, my, 3.0):
                bad.append("%s(竹垣) が外周の囲いの内側 3m を二重に回る: (%.1f, %.1f)"
                           % (rl["name"], mx, my))
                break
        # 動線(4系統)と平面で交わらない
        for r9 in d["routes"]:
            for a, b in zip(rl["pts"], rl["pts"][1:]):
                if any(_seg_x(tuple(a), tuple(b), tuple(c), tuple(e))
                       for c, e in zip(r9["pts"], r9["pts"][1:])):
                    bad.append("%s(竹垣) が動線 %s と交わる" % (rl["name"], r9["name"]))
                    break
            else:
                continue
            break
    # 勝手動線は白洲・棟・庭を横切らない。参道は**直交して1回だけ**渡る
    sd = d["sando"]
    band = (sd["u"] - sd["width"] / 2.0, sd["v0"], sd["u"] + sd["width"] / 2.0, sd["v1"])
    for r in d["routes"]:
        if r.get("kind") != "katte":
            continue
        pts = [tuple(q) for q in r["pts"]]
        for nm, u0, v0, u1, v1 in boxes + katte_boxes:
            L = _poly_x_rect(pts, u0, v0, u1, v1) * K
            if L > 0.3:
                bad.append("%s(勝手動線) が %s を %.1fm 横切る" % (r["name"], nm, L))
        L = _poly_x_rect(pts, *band) * K
        lim = sd["width"] * K * 1.25
        if L > lim:
            bad.append("%s(勝手動線) の参道の横断が %.1fm(直交1回なら ≦%.1fm)"
                       % (r["name"], L, lim))
    return bad


def _fit_note(d):
    """規則3の合格宣言を**算出**して返す。件数も最大Δも復元セル率も設計値から出す。"""
    E = _DEM.get(id(d))
    if E is None:
        _dem_at(d, 0, 0); E = _DEM.get(id(d))
    cur = None
    try:
        cur = json.load(open(os.path.join(DOC, "okabe_terrain.json"), encoding="utf-8"))
    except Exception:
        pass

    def at(S, u, v):
        iu = int(round(u - S["u0"])); iv = int(round(v - S["v0"]))
        if 0 <= iv < S["nv"] and 0 <= iu < S["nu"]:
            return S["h"][iv][iu]
        return None
    n = 0; mx = 0.0; rec = []; keep = []; over = []
    for o in d["munes"] + d["service"] + d["links"]:
        ds = []; rr = 0; tt = 0
        u = o["u0"] + 0.25
        while u < o["u1"]:
            v = o["v0"] + 0.25
            while v < o["v1"]:
                g = _dem_at(d, u, v)          # ⚠ 双一次。round() で最寄りセルを拾うと
                if g is not None:            #    他の検査(法面・断面)と違う値になる(2026-08-25)
                    # ⚠ **符号を保つ**。abs で潰すと切土が盛土に化ける(2026-08-25 考証:
                    #    「+0.01〜+0.89」と刷っていた棟が実は −0.75〜+0.89 の切盛両側だった)。
                    #    合否の判定にだけ絶対値を使う。
                    ds.append(o["y"] - g); tt += 1
                    c = at(cur, round(u), round(v)) if cur else None
                    if c is not None and abs(c - g) > 0.3:
                        rr += 1
                v += 0.5
            u += 0.5
        if not ds:
            continue
        n += 1; mx = max(mx, max(abs(min(ds)), abs(max(ds))))
        over.append((MUNE_JA.get(o["name"], o.get("label", o["name"])),
                     max(abs(min(ds)), abs(max(ds))), o["y"],
                     bool(o.get("levelOK")), min(ds), max(ds)))
        if tt and rr / float(tt) > 0.5:
            rec.append(MUNE_JA.get(o["name"], o.get("label", o["name"])))
        else:
            keep.append(MUNE_JA.get(o["name"], o.get("label", o["name"])))
    # 二つの別々の指標を出す。**混ぜない**(2026-08-24 考証: 前版は非対称な量を比べていた)。
    #  (a) 実測DEM の最頻値 … 「22.70 の平坦を近代造成と断じた」のと**同じ物差し**
    #  (b) 復元地盤が面の高さと一致する割合 … **復元の自己参照性**の指標
    cur = None
    try:
        cur = json.load(open(os.path.join(DOC, "okabe_terrain.json"), encoding="utf-8"))
    except Exception:
        pass
    try:
        _cp = json.load(open(os.path.join(DOC, "okabe_edo_world.json"), encoding="utf-8"))["_computed"]
        modelpct = " / ".join("%s %.0f%%" % (TERR_JA.get(k, k), v)
                              for k, v in _cp["modelPct"].items())
    except Exception:
        modelpct = "—"
    mode = []; selfref = []; band = {}
    for t in d["terraces"]:
        cnt = {}; tot = 0; ex = 0; tot2 = 0
        for iv in range(E["nv"]):
            for iu in range(E["nu"]):
                u, v = E["u0"] + iu, E["v0"] + iv
                if not tin(t, u, v):
                    continue
                g = E["h"][iv][iu]
                if g is not None:
                    tot2 += 1
                    if abs(g - t["y"]) < 0.005:
                        ex += 1
                c = None
                if cur and 0 <= iv < cur["nv"] and 0 <= iu < cur["nu"]:
                    c = cur["h"][iv][iu]
                if c is not None:
                    tot += 1
                    k = round(c, 2); cnt[k] = cnt.get(k, 0) + 1
        nm = TERR_JA.get(t["name"], t["name"])
        if tot:
            k, c2 = sorted(cnt.items(), key=lambda x: -x[1])[0]
            mode.append("%s %.2f が %.0f%%" % (nm, k, 100.0 * c2 / tot))
            b = sum(v for kk, v in cnt.items() if abs(kk - 22.70) <= 0.25)
            band[nm] = 100.0 * b / tot
        if tot2:
            selfref.append("%s %.0f%%" % (nm, 100.0 * ex / tot2))
    ng = [x for x in over if x[1] > 0.5 and not x[3]]
    okf = [x for x in over if x[1] > 0.5 and x[3]]
    if ng:
        head = ("⛔ <b>規則3 の不合格が %d物件</b>(全%d物件中・最大 %.2fm)。"
                "<b>面の高さか棟の位置を見直す必要がある</b>。" % (len(ng), n, mx))
    else:
        head = ("⚠ <b>規則3(棟が載る所で |設計面 − 江戸期地盤| ≦ 0.5m)を外れる %d物件を"
                "<b>ユーザー裁定待ちとして保留</b>している</b>(残る %d物件は 0.5m 以内)。"
                "⛔ <b>規則3 は CLAUDE.md の不変則で、免除を当方が自分に出せる性質のものではない</b> — "
                "下の理由は<b>当方の裁定(未承認)</b>であって、承認されるまで不合格は残っている。"
                % (len(okf), n - len(okf)))
    if okf:
        head += ("<b>保留にした均し</b>(門前面を<b>一枚の水平面で通す</b>という設計判断を採った結果。"
                 "1883年図の内挿では帯が通り沿いに傾くので、傾いた前庭という代替案もあり得たが、"
                 "白洲と石段の据わり・表門からの動線を理由に退けた【確度U】。"
                 "生じる改変量は [菊地2003]A『土地改変は高さ1〜4m程』の中で拝領時の<b>均し</b>として"
                 "類型から外れないが、⚠ <b>同論文の 1〜4m は屋敷単位の改変高であって"
                 "『棟の下の許容差』ではないので、規則3 を外す根拠にはならない</b>): "
                 + " / ".join("%s %+.2f〜%+.2fm" % (a, lo, hi) for a, b, c, f, lo, hi in
                              sorted(okf, key=lambda q: -q[1])) + "。")
    tail = ("⚠ <b>この検査が独立に効いているのは %d物件だけ</b>(%s。判定は「棟の下のセルの半分以上で"
            "復元値と現況が 0.3m 以内=復元が値をほとんど動かしていない」)。残る %d物件は"
            "<b>復元した地盤の上</b>にあり、そこでは「自分が置いた値を測り返している」"
            "にすぎない(§A-6)。"
            "<b>復元が値を作ったセルの割合</b> — 復元への依存度 — は %s。"
            "(⚠ 従前ここに出していた『復元地盤が面の高さとちょうど一致するセルの割合』は、"
            "帯を傾け平滑化すれば構成上ゼロに近づく量で、依存度の指標にならない。2026-08-25 に差し替えた。)"
            "現況の実測DEMで見た段の中の最頻値は %s。"
            "⚠ <b>この二つは別の物差しなので、足したり比べたりしない。</b>"
            % (len(keep), "・".join(keep) or "—", len(rec),
               modelpct, " / ".join(mode)))
    if ng:
        tail += ("<b>不合格の物件:</b> "
                 + " / ".join("%s(面%.2f・%+.2f〜%+.2fm)" % (a, c, lo, hi)
                              for a, b, c, f, lo, hi in sorted(ng, key=lambda q: -q[1]))
                 + "。")
    return head + tail


def eye_above(d, mode):
    """**眼の高さ**[m](足元からの)。⭐ 基準身長 `const.bodyH` × `const.eyeRatio[mode]`。

    ⛔ 座視・立位を別々の人の値で持たない(2026-09-03 考証4巡目 K147) —
      2026-09-02 まで 畳0.68 / 床几1.23 / 立位1.55 が**互いに違う身長の人**の値だった。
    ⚠ 身長も比も**確度U**([江戸期の人体寸法] は未入手)。"""
    c9 = d["const"]
    return c9.get("bodyH", 1.57) * (c9.get("eyeRatio") or {}).get(mode, 0.93)


def _cert(d, o):
    """確度の本文を引く。`"@<id>"` は `d["certs"]` への参照。
    ⛔ 同じ文を各要素へ写さない — 20本の練塀が同一の545字を20重に持ち、脚注は1本目しか
      読まないので2本目以降を直しても図に出なかった(2026-09-01 六巡目)。"""
    c = (o.get("cert", "") or "") if isinstance(o, dict) else (o or "")
    if c.startswith("@"):
        return d.get("certs", {}).get(c[1:], "")
    return c


def cert_ref_check(d, lim=120):
    """**確度の本文の写しが復活していないか。** 同じ長文を2箇所以上が生で持っていたら、
    それは `certs` へ畳んで `@<id>` で参照すべきもの。⛔ 生で持つと直しても図に出ない。"""
    import collections as _c
    seen = _c.defaultdict(list)

    def walk(o, path):
        """⭐ 2026-09-02: **入れ子ごと歩く。**庭の点景(石組・灯籠・植栽…)は
        `gardens[].ishigumi[]` のように深い所に居るので、トップレベルの
        コレクションだけを見る形では写しを見逃した。"""
        if isinstance(o, dict):
            c = o.get("cert")
            if isinstance(c, str) and not c.startswith("@") and len(c) >= lim:
                seen[c].append("%s/%s" % (path, o.get("name", o.get("label", "?"))))
            for k9, v9 in o.items():
                if k9 != "cert":
                    walk(v9, "%s.%s" % (path, k9) if path else k9)
        elif isinstance(o, list):
            for v9 in o:
                walk(v9, path)
    for key in ("runs", "munes", "planes", "fences", "gardens", "terraces", "kaidans",
                "service", "wells", "kekkai", "links", "slopeBands", "grading", "bom"):
        walk(d.get(key), key)
    return ["同じ確度の本文(%d字)を %d 箇所が生で持つ: %s — `certs` へ畳んで @<id> で参照する"
            % (len(c), len(ns), "・".join(ns[:4]) + ("…" if len(ns) > 4 else ""))
            for c, ns in seen.items() if len(ns) > 1]


def _cert_sig(c):
    """本文が**言っている**確度の記号(S/A/B/P/U)。⛔ **図の確度欄に使わない。**

    ⚠ 2026-09-03 考証4巡目 K143: この関数を図の確度欄に使っていたため、
      本文の「従前の『林縁の構造=**B**』は…**U** へ落とした」から**撤回済みの B** を拾い、
      13行が誤った記号を刷っていた(林縁・切り透し・ヤダケが B のまま/葭原・蓮が空欄/
      林の高木9行が S のみ)。⛔ **散文から確度を推測しない。**
    ⭕ 図が刷るのは `cert_sig()`(json が宣言した `certSig`)で、
      ここは**宣言と本文が食い違っていないか**を検める `certsig_check` のためだけに残す。"""
    sig = []
    for m9 in re.finditer(r"=\s*\**([SABPU])\**(?![A-Za-z])|\*\*([SABPU])\*\*", c or ""):
        g9 = m9.group(1) or m9.group(2)
        if g9 not in sig:
            sig.append(g9)
    return "/".join(sig) if sig else "—"


def cert_sig(d, o):
    """**図の確度欄に刷る記号。**json が宣言した `certSig` だけを見る(⛔ 本文から推測しない)。

    ⭕ `"@<id>"` の cert は `d["certSigs"][<id>]` を引く。宣言が無ければ `?` を刷り、
      `certsig_check` が「宣言が無い」として鳴らす。"""
    if isinstance(o, dict):
        if o.get("certSig"):
            return o["certSig"]
        c9 = o.get("cert", "") or ""
    else:
        c9 = o or ""
    if isinstance(c9, str) and c9.startswith("@"):
        return (d.get("certSigs") or {}).get(c9[1:], "?")
    return "?"


def certsig_check(d):
    """**確度の記号が宣言され、本文と食い違わないか。**

    ⛔ 2026-09-03 まで図は**散文から記号を推測**していて、撤回済みの記号を刷っていた(K143)。
    ⭕ ここが見るのは二つだけ:
      ① cert を持つものは `certSig`(または `certSigs[<id>]`)を**宣言している**
      ② 宣言した記号は、本文のどこかに現れる(⛔ 本文の記号が全部宣言されている必要は無い —
         撤回の記述『従前の…=B は U へ落とした』が本文に残るのは正しい)"""
    bad = []
    seen = []

    def walk(o, path):
        if isinstance(o, dict):
            if isinstance(o.get("cert"), str) and o["cert"]:
                seen.append((path, o, _cert(d, o)))
            for k9, v9 in o.items():
                if k9 != "certs":
                    walk(v9, path + "." + k9)
        elif isinstance(o, list):
            for i9, v9 in enumerate(o):
                walk(v9, path + "[%d]" % i9)

    walk(d, "")
    for cid, ctext in sorted((d.get("certs") or {}).items()):
        seen.append(("certs.%s" % cid, {"certSig": (d.get("certSigs") or {}).get(cid)}, ctext))
    for path, o, ctext in seen:
        # ⛔ **「宣言が無い」と「未定と宣言した」を混ぜない**(前者は欠落・後者は正しい状態)。
        decl = o.get("certSig") if isinstance(o, dict) else None
        if not decl:
            c8 = (o.get("cert") if isinstance(o, dict) else o) or ""
            if isinstance(c8, str) and c8.startswith("@"):
                decl = (d.get("certSigs") or {}).get(c8[1:])
        if not decl:
            bad.append("%s に確度の記号(`certSig`)の宣言が無い" % path)
            continue
        sig = decl
        for q9 in sig.split("/"):
            if q9 == "?":                      # ⭕ 「まだ決まっていない」の宣言は認める
                if "?" not in (ctext or ""):
                    bad.append("%s が確度 ? を名乗るが、本文に未決と書いていない" % path)
                continue
            if q9 not in "SABPU" or len(q9) != 1:
                bad.append("%s の確度の記号『%s』が S/A/B/P/U でない" % (path, q9))
            elif q9 not in (ctext or ""):
                bad.append("%s は確度 %s を名乗るが、本文に %s が一度も出てこない"
                           % (path, sig, q9))
    return bad


def _max_joint_where(d):
    """天端の段差が最大になる継ぎ目が、隅なのか辺の中なのかを言う。
    ⚠ 2026-08-31 五巡目: リード文が「最大 2.63m(**隅を含む**)」と書いていたが、
      実際は辺1 の中間の継ぎ目(s=66)で、隅の最大は 2.22m だった。"""
    best = (0.0, None, None)
    for x, y in _joints(d):
        dz = abs(rseat(y, y["s0"]) - rseat(x, x["s1"]))
        if dz > best[0]:
            best = (dz, x, y)
    if best[1] is None:
        return "—"
    x, y = best[1], best[2]
    if x["edge"] == y["edge"]:
        return "辺%d s=%.0f の継ぎ目" % (x["edge"], x["s1"])
    return "辺%d と辺%d の隅" % (x["edge"], y["edge"])


def _joints(d):
    """天端が隣り合う run の対。(1)同じ辺の中の継ぎ目 (2)頂点をまたぐ隅
    — 隅は『辺の終点で終わる run』と『次に当家が建てる辺の始点から始まる run』を結ぶ。"""
    P = d["polygon"]; n = len(P)

    def el(i):
        return math.hypot(P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1])
    out = []
    for a in d["runs"]:
        for b in d["runs"]:
            if a is b:
                continue
            if a["edge"] == b["edge"] and 0 <= b["s0"] - a["s1"] < 3.0:
                out.append((a, b))
    own = sorted(set(r["edge"] for r in d["runs"]))
    for a in d["runs"]:
        if abs(a["s1"] - el(a["edge"])) > 0.3:
            continue
        nxt = own[(own.index(a["edge"]) + 1) % len(own)]
        if (nxt - a["edge"]) % n != 1:
            continue                       # 間に当家が建てない辺が挟まる隅は結ばない
        for b in d["runs"]:
            if b["edge"] == nxt and b["s0"] < 0.3:
                out.append((a, b))
    return out


def rseat(r, s):
    """run の天端。seat0→seat1 の一直線(水平のときは両端が同値)。"""
    a = r.get("seat0", r.get("seat")); b = r.get("seat1", r.get("seat"))
    if r["s1"] <= r["s0"]:
        return a
    t = (s - r["s0"]) / (r["s1"] - r["s0"])
    return a + (b - a) * max(0.0, min(1.0, t))


def tcuts(t, axis, at):
    """切り線(axis='u' なら u=at)が段の多角形を切る区間 [(a,b)]。
    1本の線が凹んだ多角形を何度も切ることがあるので**区間のリスト**で持つ。"""
    poly = tpoly(t)
    n = len(poly)
    xs = []
    for i in range(n):
        (p0, q0), (p1, q1) = poly[i], poly[(i + 1) % n]
        if axis == "v":                       # 線 v=at、交点は u
            p0, q0, p1, q1 = q0, p0, q1, p1
        if (p0 - at) * (p1 - at) > 0 or p0 == p1:
            continue
        xs.append(q0 + (q1 - q0) * (at - p0) / (p1 - p0))
    xs.sort()
    segs = [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2) if xs[i + 1] - xs[i] > 1e-6]
    # ⭐ 抜き(造成しない区画)の区間を引く — 断面で「面」の帯を穴の上に描かないため
    for hp in tholes(t):
        hs = []
        for i in range(len(hp)):
            (p0, q0), (p1, q1) = hp[i], hp[(i + 1) % len(hp)]
            if axis == "v":
                p0, q0, p1, q1 = q0, p0, q1, p1
            if (p0 - at) * (p1 - at) > 0 or p0 == p1:
                continue
            hs.append(q0 + (q1 - q0) * (at - p0) / (p1 - p0))
        hs.sort()
        for i in range(0, len(hs) - 1, 2):
            ha, hb = hs[i], hs[i + 1]
            nxt = []
            for a9, b9 in segs:
                if hb <= a9 + 1e-9 or ha >= b9 - 1e-9:
                    nxt.append((a9, b9)); continue
                if a9 < ha - 1e-9:
                    nxt.append((a9, ha))
                if b9 > hb + 1e-9:
                    nxt.append((hb, b9))
            segs = nxt
    # ⭐ **keeps(抜きの中で面が残る棟の足跡)を戻す。**⛔ 戻さないと断面で、家臣長屋が載る
    #   keep の上に段の帯が描かれず、棟が宙に浮いて見える(2026-09-02 検図 K075)。
    for kp in tkeeps(t):
        ks = []
        for i in range(len(kp)):
            (p0, q0), (p1, q1) = kp[i], kp[(i + 1) % len(kp)]
            if axis == "v":
                p0, q0, p1, q1 = q0, p0, q1, p1
            if (p0 - at) * (p1 - at) > 0 or p0 == p1:
                continue
            ks.append(q0 + (q1 - q0) * (at - p0) / (p1 - p0))
        ks.sort()
        for i in range(0, len(ks) - 1, 2):
            segs.append((ks[i], ks[i + 1]))
    segs.sort()
    out = []
    for a9, b9 in segs:                       # 重なる区間を畳む
        if out and a9 <= out[-1][1] + 1e-9:
            out[-1] = (out[-1][0], max(out[-1][1], b9))
        else:
            out.append((a9, b9))
    return [x for x in out if x[1] - x[0] > 1e-6]


def kgeom(k):
    """石段の占める帯。**土留めに依らない**(郭内の土留めは全廃した)。
    gapU があれば u=gapU で v0..v1 を降りる段、gapV があれば v=gapV で u0..u1。
    返り値 (axis, at, a, b, cu, cv) — axis は段が『降りる向き』の軸。"""
    if "gapU" in k and k.get("gapU") is not None:
        a, b = k.get("v0", 0.0), k.get("v1", 0.0)
        return ("v", k["gapU"], a, b, k["gapU"], (a + b) / 2.0)
    a, b = k.get("u0", 0.0), k.get("u1", 0.0)
    return ("u", k.get("gapV", 0.0), a, b, (a + b) / 2.0, k.get("gapV", 0.0))


def plan_svg(d):
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), 900.0, pad=14.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 敷地全体")

    def gpoly(u0, v0, u1, v1, **kw):
        return gpolyN([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], **kw)

    def gpolyN(gp, **kw):
        pts = [gr.W(a, b) for a, b in gp]
        a = '<polygon points="%s"' % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts)
        if "fill" in kw:
            a += ' fill="%s"' % kw["fill"]
        if kw.get("stroke"):
            a += ' stroke="%s" stroke-width="%.2f"' % (kw["stroke"], kw.get("sw", 1.0))
        if kw.get("op") is not None:
            a += ' opacity="%.2f"' % kw["op"]
        return a + "/>"

    # 下塗り: 区画の内側全体を斜面(竹林)色に — 面色の隙間を作らない
    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.85"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p2[0]), pr.Y(p2[1])) for p2 in P))
    # 段(回転矩形) — 面ごとの色分け
    for t in d["terraces"]:
        g.append(gpolyN(tpoly(t),
                       fill=dan_color(d, t["y"]), op=1.0))
        # ⭐ **抜き(平坦化しない区画)を必ず描く。**⛔ 描かないと「同じ段が二つの形で描かれる」
        #   型になる(2026-09-02 検図 K060: 6枚中5枚で 1,042坪=主面の27.9% が見えていなかった)。
        for hp in tholes(t):
            # ⛔ **区画線で切ってから描く**(2026-09-02 検図: 抜きの矩形が区画の外へ出ていた)
            g.append(gpolyN(clip_ring(hp, [gr.L(x9, z9) for x9, z9 in P]) or hp,
                            fill=_pat(), stroke="var(--dim)", sw=0.8))
        for kp in tkeeps(t):
            g.append(gpolyN(kp, fill=dan_color(d, t["y"]), op=1.0))
    # 庭(白洲・奥庭・勝手庭) — 面色の上・マスクの前に重ねる(区画線で切られる)
    for n2 in d["gardens"]:
        col = "var(--shirasu)" if n2.get("kind") == "shirasu" else "var(--niwa)"
        g.append(gpoly(n2["u0"], n2["v0"], n2["u1"], n2["v1"], fill=col, stroke="var(--ink)", sw=0.5, op=0.9))
    # 斜面(造成しない)のラベル
    for x, z, t2 in ((-570, 1092, "南西の谷の頭(造成しない)"),
                     (-452, 1096, "南東の低み")):
        g.append(T(pr.X(x), pr.Y(z), t2, "anS2", "middle"))
    # 敷地の外をマスク — 面の色・裾の帯を区画線で正確に切る(evenodd の穴あき矩形)
    ring = " ".join("L %.1f %.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P)
    ring = "M" + ring[1:] + " Z"
    g.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z %s" fill="var(--paper2)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, ring))
    # 区画線と頂点
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    for i, p in enumerate(P):
        g.append('<circle cx="%.1f" cy="%.1f" r="2.4" fill="var(--ink)"/>' % (pr.X(p[0]), pr.Y(p[1])))
        g.append(T(pr.X(p[0]) + 5, pr.Y(p[1]) - 5, "P%d" % i, "jo"))

    # 外周の run(辺+走り)
    for r in d["runs"]:
        a = edge_pt(P, r["edge"], r["s0"]); b = edge_pt(P, r["edge"], r["s1"])
        # ⚠ 2026-08-31 検図: 長屋は太い線でなく**奥行 nagayaD の帯**で描く(足跡が図に出ていなかった)
        if r["kind"] == "Nagaya":
            nx9, ny9 = _inward(P, r["edge"])
            dd9 = d["const"]["nagayaD"]
            q9 = [(a[0], a[1]), (b[0], b[1]),
                  (b[0] + nx9 * dd9, b[1] + ny9 * dd9), (a[0] + nx9 * dd9, a[1] + ny9 * dd9)]
            g.append('<polygon points="%s" fill="%s" stroke="var(--ink)" stroke-width="0.6" opacity="0.9"/>'
                     % (" ".join("%.1f,%.1f" % (pr.X(x9), pr.Y(y9)) for x9, y9 in q9),
                        KC.get(r["kind"], "var(--dim)")))
        else:
            g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]),
                        KC.get(r["kind"], "var(--dim)"), 3.4, cap="round"))
    # 郭の土留め
    for w in d["terraceWalls"]:
        q9 = [gr.W(a9, b9) for a9, b9 in (w.get("pts") or [w["a"], w["b"]])]
        g.append('<polyline points="%s" fill="none" stroke="var(--ishi)" stroke-width="3.4" '
                 'stroke-linecap="round" stroke-linejoin="round"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(x9), pr.Y(z9)) for x9, z9 in q9))
    # 竹垣
    for rl in auto_rails(d):
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="var(--take)" stroke-width="2.6" stroke-dasharray="2 4"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts))

    # 御殿・付属屋の輪郭
    for m in d["munes"]:
        g.append(gpoly(m["u0"], m["v0"], m["u1"], m["v1"],
                       fill="var(--ink-mid)", stroke="var(--ink)", sw=0.5, op=0.85))
    for s in d["service"]:
        g.append(gpoly(s["u0"], s["v0"], s["u1"], s["v1"],
                       fill="var(--ink-lo)", stroke="var(--ink)", sw=0.6, op=0.9))
    # 段ラベル(面ごと・重ね順の最後)
    for t in d["terraces"]:
        cx, cz = gr.W((t["u0"] + t["u1"]) / 2.0, (t["v0"] + t["v1"]) / 2.0)
        g.append(T(pr.X(cx), pr.Y(cz), "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"]),
                   "anS", "middle"))

    # 門・櫓
    gp = d["gate"]["pos"]
    g.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (pr.X(gp[0]), pr.Y(gp[1])))
    g.append(T(pr.X(gp[0]) + 9, pr.Y(gp[1]) - 5, "表門", "sr"))
    om = d.get("onarimon")
    if om:
        op_ = edge_pt(P, om["edge"], om["s"])
        g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="none" stroke="var(--shu)" stroke-width="2.2"/>'
                 % (pr.X(op_[0]), pr.Y(op_[1])))
        g.append(T(pr.X(op_[0]) + 8, pr.Y(op_[1]) - 4, "御成門", "sr"))
    for k in d["komon"]:
        kp = edge_pt(P, k["edge"], k["s"])
        g.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="var(--shu)" opacity="0.7"/>' % (pr.X(kp[0]), pr.Y(kp[1])))
        g.append(T(pr.X(kp[0]) + 6, pr.Y(kp[1]) + 10, "木戸", "jo"))
    for y in d["yagura"]:
        vp = P[y["vertex"]]
        g.append(R(pr.X(vp[0]) - 4.5, pr.Y(vp[1]) - 4.5, 9, 9, fill="var(--shu)"))
        g.append(T(pr.X(vp[0]) - 8, pr.Y(vp[1]) - 8, "櫓", "jo", "end"))
    # 井戸
    for w in d["wells"]:
        wp = gr.W(w["u"], w["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="3" fill="none" stroke="var(--ink)" stroke-width="1.4"/>'
                 % (pr.X(wp[0]), pr.Y(wp[1])))

    # 断面の切り位置
    for s in d["sections"]:
        if s["axis"] == "u":
            f9, t9 = _sec_span(d, s)
            a = gr.W(s["at"], f9); b = gr.W(s["at"], t9)
        else:
            f9, t9 = _sec_span(d, s)
            a = gr.W(f9, s["at"]); b = gr.W(t9, s["at"])
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]), "var(--shu)", 0.9, dash="9 5", op=0.8))
        g.append(T(pr.X(b[0]), pr.Y(b[1]) - 6, s["name"].split(" ")[0], "sr", "middle"))

    # 街路・隣地の名
    g.append(T(pr.X(-443), pr.Y(1128), "三べ坂前身の道", "anS"))
    g.append(T(pr.X(-560), pr.Y(1168), "松平出羽守邸(背中合わせ・塀は松平所有)", "anS2"))
    g.append(T(pr.X(-560), pr.Y(1072), "岡部邸(塀は岡部所有)", "anS2"))
    g.append(T(pr.W - 6, 15, "北 ↑　左=西", "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- ・其三 御殿平面(グリッド座標)
def plan_frame(d, tname, pad=3.0):
    """平面図の枠を**段の外接矩形から算出**する(手で持つと棟を動かすたびに腐る)。
    ⚠ 2026-08-25 検図: 手書きの枠が主面の 7.2% を切り落とし、`KN_Sh1 家臣長屋(主面1)` が
    どの平面図にも載らなくなっていた(断面の見出しには出るので図の中で矛盾していた)。"""
    t = next(x for x in d["terraces"] if x["name"] == tname)
    pts = tpoly(t)
    us = [p[0] for p in pts]; vs = [p[1] for p in pts]
    for o in d["munes"] + d["service"] + d["gardens"] + d["links"]:
        # ⚠ `y` を持たない物(庭)は**段の多角形に入るかで判定する**。
        #    既定値をその段の高さにしていたため、6つの庭が両方の枠に入り、
        #    門前面の平面図が敷地全域=御殿平面の重複になっていた(2026-08-25 検図)。
        cu9 = (o["u0"] + o["u1"]) / 2.0; cv9 = (o["v0"] + o["v1"]) / 2.0
        if "y" in o:
            if abs(o["y"] - t["y"]) > 0.6:
                continue
        elif not tin(t, cu9, cv9):
            continue
        us += [o["u0"], o["u1"]]; vs += [o["v0"], o["v1"]]
    return (math.floor(min(us) - pad), math.ceil(max(us) + pad),
            math.floor(min(vs) - pad), math.ceil(max(vs) + pad))


def goten_plan(d, u0, u1, v0, v1, label, note):
    """段の平面。**枠外の要素は clipPath で切る**(2026-08-23 検図: 枠の外にテキストが残っていた)。"""
    pr = LProj(u0, u1, v0, v1, 900.0)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 %s" % label)
    _SVN[0] = _SVN[0]
    cid = "gp%d" % _SVN[0]
    g.append('<defs><clipPath id="%s"><rect x="0" y="0" width="%.1f" height="%.1f"/></clipPath></defs>'
             % (cid, pr.W, pr.H))
    g.append('<g clip-path="url(#%s)">' % cid)
    gr = RGrid(d)

    def vis(a, b, c, e):
        return not (b < v0 or a > v1 or e < u0 or c > u1)

    # 下塗り: 区画の内側=斜面(竹林)色。面色の隙間を作らない
    Pg0 = [gr.L(x, z) for x, z in d["polygon"]]
    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.85"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in Pg0))
    # 段
    for t in d["terraces"]:
        if not vis(t["v0"], t["v1"], t["u0"], t["u1"]):
            continue
        g.append(pr.poly(tpoly(t),
                         fill=dan_color(d, t["y"]), op=1.0))
        for hp in tholes(t):                      # 抜き(平坦化しない区画)— K060
            g.append(pr.poly(hp, fill=_pat(), stroke="var(--dim)", sw=0.8, dash="4 3"))
        for kp in tkeeps(t):
            g.append(pr.poly(kp, fill=dan_color(d, t["y"]), op=1.0))
        g.append(T((pr.X(max(t["u0"], u0)) + pr.X(min(t["u1"], u1))) / 2, pr.Y(min(t["v1"], v1)) - 4,
                   "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"]), "anS", "middle"))

    # 区画の外をマスクしてから区画線(面の色が境界線とぴったり合う)
    P = [gr.L(x, z) for x, z in d["polygon"]]
    ring = " ".join("L %.1f %.1f" % (pr.X(u), pr.Y(v)) for u, v in P)
    ring = "M" + ring[1:] + " Z"
    g.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z %s" fill="var(--paper2)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, ring))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.8"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))

    # 庭
    for n in d["gardens"]:
        if not vis(n["v0"], n["v1"], n["u0"], n["u1"]):
            continue
        col = "var(--shirasu)" if n.get("kind") == "shirasu" else "var(--niwa)"
        fv = (min(v1, n["v1"]) - max(v0, n["v0"])) / float(n["v1"] - n["v0"])
        fu = (min(u1, n["u1"]) - max(u0, n["u0"])) / float(n["u1"] - n["u0"])
        g.append(pr.rect(n["u0"], max(n["v0"], v0), n["u1"], min(n["v1"], v1),
                         fill=col, stroke="var(--ink)", sw=0.8))
        if min(fu, fv) >= 0.55:
            g.append(T((pr.X(n["u0"]) + pr.X(n["u1"])) / 2,
                       (pr.Y(max(n["v0"], v0)) + pr.Y(min(n["v1"], v1))) / 2 + 4,
                       n["label"], "rmS", "middle", fit(n["label"], pr.L(n["u1"] - n["u0"]), 12.0)))

    # 郭の土留め・石段・竹垣
    for w in d["terraceWalls"]:
        pw = [(a9, b9) for a9, b9 in (w.get("pts") or [w["a"], w["b"]])]
        if not vis(min(q[1] for q in pw), max(q[1] for q in pw),
                   min(q[0] for q in pw), max(q[0] for q in pw)):
            continue
        # **折れ線の帯**で描く(底厚 2.4×s)。⛔ 矩形で描くと天端の等高線が直線に見える
        g.append('<polyline points="%s" fill="none" stroke="var(--ishi)" stroke-width="%.1f" '
                 'stroke-linecap="butt" stroke-linejoin="round" opacity="0.85"/>'
                 % (" ".join("%.1f,%.1f" % (pr.X(a9), pr.Y(b9)) for a9, b9 in pw),
                    max(3.0, pr.L(2.4 * w["s"] / 1.818))))
        mid = pw[len(pw) // 2]
        g.append(T(pr.X(mid[0]), pr.Y(mid[1]) + 12, "%s 天端%.2f" % (w["name"], w["coping"]),
                   "jo", "middle"))
    for k in d["kaidans"]:
        ax, at2, ka, kb, cu, cv = kgeom(k)
        hw = k["w"] / 2 / 1.818
        if ax == "v":
            g.append(pr.rect(at2 - hw, ka, at2 + hw, kb,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
            sgn2 = 1.0 if kb >= ka else -1.0           # 踏面(0.45)と踊り場を分けて筋を引く
            odn = set()
            if k.get("odori"):
                for j2 in range(1, k["odori"] + 1):
                    odn.add(int(round(k["steps"] * j2 / float(k["odori"] + 1))))
            vv = ka
            for i in range(k["steps"]):
                g.append(LN(pr.X(at2 - hw), pr.Y(vv), pr.X(at2 + hw), pr.Y(vv), "var(--shu)", 0.4))
                vv += sgn2 * k["fumi"] / 1.818
                if (i + 1) in odn:                     # 踊り場(幅の広い帯)
                    g.append(R(pr.X(at2 - hw), pr.Y(vv + sgn2 * k["odoriKen"]),
                               pr.X(at2 + hw) - pr.X(at2 - hw),
                               abs(pr.Y(vv) - pr.Y(vv + sgn2 * k["odoriKen"])),
                               fill="var(--shirasu)", stroke="var(--shu)", sw=0.5))
                    vv += sgn2 * k["odoriKen"]
        else:
            g.append(pr.rect(ka, at2 - hw, kb, at2 + hw,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        g.append(T(pr.X(cu), pr.Y(cv) - 8, "%s %d段" % (k["name"], k["steps"]), "anS2", "middle"))
    for o9 in obi_metrics(d):                           # ⭕ 崖下の帯の棟(K248)
        g.append(pr.rect(o9["u0"], o9["v0"], o9["u1"], o9["v1"],
                         fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8, op=0.7))
        g.append(T(pr.X((o9["u0"] + o9["u1"]) / 2), pr.Y((o9["v0"] + o9["v1"]) / 2) + 4,
                   o9["name"], "jo", "middle"))
    for rp in d.get("ramps", []):                       # 坂(斜面を勾配で登る道)
        pts = [(pr.X(u), pr.Y(v)) for u, v in rp["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="%.1f" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.55"/>'
                 % (" ".join("%.1f,%.1f" % q for q in pts), max(4.0, pr.L(rp["w"] / 1.818))))
        g.append(T(pts[len(pts) // 2][0], pts[len(pts) // 2][1] - 7,
                   "%s 全長%.0fm 最急%.1f%%"
                   % (rp["label"], rp["len"],
                      (ramp_metrics(d, rp) or {}).get("grad", 0)), "anS2", "middle"))
    for rl in auto_rails(d):
        pts = [(u, v) for u, v in rl["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="var(--take)" stroke-width="2.4" stroke-dasharray="2 4"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in pts))

    # 廊下 → 棟(入側帯) → 身舎 → 室
    for l in d["links"]:
        if not vis(l["v0"], l["v1"], l["u0"], l["u1"]):
            continue
        col = "var(--shu)" if l["kind"] == "御錠口" else "var(--roka)"
        g.append(pr.rect(l["u0"], l["v0"], l["u1"], l["v1"], fill=col))
    for m in d["munes"]:
        if not vis(m["v0"], m["v1"], m["u0"], m["u1"]):
            continue
        g.append(pr.rect(m["u0"], m["v0"], m["u1"], m["v1"], fill="var(--roka)"))
    for m in d["munes"]:
        if not vis(m["v0"], m["v1"], m["u0"], m["u1"]):
            continue
        # 図版の窓に半分も入らない棟は**輪郭だけ**描く(室名が切れて文字が重なるため)
        fv = (min(v1, m["v1"]) - max(v0, m["v0"])) / float(m["v1"] - m["v0"])
        fu = (min(u1, m["u1"]) - max(u0, m["u0"])) / float(m["u1"] - m["u0"])
        if min(fu, fv) < 0.55:
            g.append(pr.rect(m["u0"], max(m["v0"], v0), m["u1"], min(m["v1"], v1),
                             fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8, dash="4 3", op=0.7))
            continue
        if m.get("ita"):
            mu0, mv0, mu1, mv1 = m["u0"], m["v0"], m["u1"], m["v1"]
        else:
            mu0, mv0, mu1, mv1 = m["u0"] + 1, m["v0"] + 1, m["u1"] - 1, m["v1"] - 1
        g.append(pr.rect(mu0, mv0, mu1, mv1, fill="var(--ink-mid)", stroke="var(--ink)", sw=1.6))
        seen = set()
        for r in m["rooms"]:
            for u in (r["u0"], r["u1"]):
                if u in (mu0, mu1) or ("u", u, r["v0"], r["v1"]) in seen:
                    continue
                seen.add(("u", u, r["v0"], r["v1"]))
                g.append(LN(pr.X(u), pr.Y(r["v0"]), pr.X(u), pr.Y(r["v1"]), "var(--ink)", 0.8, dash="5 3"))
            for v in (r["v0"], r["v1"]):
                if v in (mv0, mv1) or ("v", v, r["u0"], r["u1"]) in seen:
                    continue
                seen.add(("v", v, r["u0"], r["u1"]))
                g.append(LN(pr.X(r["u0"]), pr.Y(v), pr.X(r["u1"]), pr.Y(v), "var(--ink)", 0.8, dash="5 3"))
            cx = (pr.X(r["u0"]) + pr.X(r["u1"])) / 2
            cy = (pr.Y(r["v0"]) + pr.Y(r["v1"])) / 2
            fs = fit(r["name"], pr.L(abs(r["u1"] - r["u0"])) - 4, 11.5)
            g.append(T(cx, cy - 1, r["name"], "rmS", "middle", fs))
            # 土間・板敷に畳数は付けない(考証指摘#17)— 間²で示す
            g.append(T(cx, cy + 11, ("%d間²" % (tatami(r) // 2)) if r.get("ita") else ("%d畳" % tatami(r)),
                       "jo", "middle"))
        nm = MUNE_JA.get(m["name"], m["name"])
        g.append(T((pr.X(m["u0"]) + pr.X(m["u1"])) / 2, pr.Y(m["v0"]) - 4, nm, "mu", "middle",
                   fit(nm, pr.L(m["u1"] - m["u0"]), 12.5)))

    # 付属屋・井戸・門
    for s in d["service"]:
        if not vis(s["v0"], s["v1"], s["u0"], s["u1"]):
            continue
        g.append(pr.rect(s["u0"], s["v0"], s["u1"], s["v1"], fill="var(--ink-lo)", stroke="var(--ink)", sw=1.2))
        g.append(T((pr.X(s["u0"]) + pr.X(s["u1"])) / 2, (pr.Y(s["v0"]) + pr.Y(s["v1"])) / 2 + 4,
                   s["label"], "rmS", "middle", fit(s["label"], pr.L(s["u1"] - s["u0"]) + 16, 11.0)))
    for w in d["wells"]:
        if not vis(w["v"], w["v"], w["u"], w["u"]):
            continue
        g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
                 % (pr.X(w["u"]), pr.Y(w["v"])))
        g.append(T(pr.X(w["u"]) + 7, pr.Y(w["v"]) + 4,
                   "井戸" if "kei" not in w else w["kei"], "jo"))
    if v0 <= 0:
        if u0 <= 0 <= u1:
            g.append(T(pr.X(0), pr.Y(0) - 6, "▼ 表門", "sr", "middle"))
        if d.get("onarimon"):
            ou = d["onarimon"]["s"] / 1.818 - 34.4
            if u0 <= ou <= u1:
                g.append(T(pr.X(ou), pr.Y(0) - 6, "▼ 御成門", "sr", "middle"))
    # 小門(御蔵門など)は世界座標→グリッドへ変換して窓内なら示す
    for k in d["komon"]:
        kp = edge_pt(d["polygon"], k["edge"], k["s"])
        ku, kv = gr.L(kp[0], kp[1])
        if u0 <= ku <= u1 and v0 - 2 <= kv <= v1:
            g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)" opacity="0.8"/>' % (pr.X(ku), pr.Y(kv)))
            g.append(T(pr.X(ku) + 7, pr.Y(kv) + 4, "御蔵門" if k["name"] == "Kuramon" else "小門", "sr"))

    g.append(T(4, 15, "グリッド座標(u=東辺沿い北+ / v=敷地の奥+)。"
               "**上=東(三べ坂前身の南北道)／左=北／下=西／右=南** — 「敷地」(北が上)を反時計回りに90°回した向き",
               "anS"))
    g.append(T(4, pr.H - 5, note, "anS2", "start"))
    g.append("</g>")
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 切盛(どこを盛りどこを切るか)
CF_BANDS = [(0.3, "var(--fill1)"), (1.0, "var(--fill2)"), (2.0, "var(--fill3)"), (3.0, "var(--fill4)")]
# 切盛図には**二つの帯**がある。⛔ キャプションで一つにまとめない(2026-09-02 検図 K076)。
CF_SKIP = 0.05      # これ未満は升そのものを描かない(素地のまま=下塗りの斜面色)
CF_FLAT = 0.3       # これ未満は「動かさない」の無彩(`sashizu_lib.cf_color` の第一段)


def load_terrain(path):
    if not os.path.exists(path):
        return None
    t = json.load(open(path, encoding="utf-8"))

    if "nu" in t:
        def h(u, v):
            iu = int(round((u - t["u0"]) / t["step"]))
            iv = int(round((v - t["v0"]) / t["step"]))
            if 0 <= iv < t["nv"] and 0 <= iu < t["nu"]:
                return t["h"][iv][iu]
            return None
        t["at"] = h
    return t


_PIN = {}


def in_parcel(d, u, v):
    """グリッド座標が区画の中か。**段も法面もここで切る**(敷地外への波及ゼロ)。"""
    key = id(d)
    if key not in _PIN:
        gr = RGrid(d)
        _PIN[key] = [gr.L(x, z) for x, z in d["polygon"]]
    Pg = _PIN[key]
    n = len(Pg); c = False
    for i in range(n):
        (au, av), (bu, bv) = Pg[i], Pg[(i + 1) % n]
        if (av > v) != (bv > v) and u < au + (bu - au) * (v - av) / (bv - av):
            c = not c
    return c


def par_dist(d, u, v):
    """区画線までの最短距離(グリッド単位)。中か外かは in_parcel で別に見る。"""
    key = id(d)
    if key not in _PIN:
        in_parcel(d, 0, 0)
    Pg = _PIN[key]
    best = None
    for i in range(len(Pg)):
        a, b = Pg[i], Pg[(i + 1) % len(Pg)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((u - a[0]) * dx + (v - a[1]) * dy) / L2))
        dd = math.hypot(u - (a[0] + dx * t), v - (a[1] + dy * t))
        best = dd if best is None else min(best, dd)
    return best


def design_y(d, u, v):
    """その (u,v) を覆う段の高さ。正典は sashizu_lib.design_y(poly/yaw/矩形の包含を全部見る)。"""
    return sashizu_lib.design_y(d, u, v, in_parcel)


def walled_edges(d, t):
    """正典は sashizu_lib.walled_edges(区間つき・2026-08-26 造成モデル統一)。
    当邸は `terraceWalls` が空なので常に空を返す。"""
    return sashizu_lib.walled_edges(d, t)


_DEM = {}


def _dem_at(d, u, v):
    """江戸期の復元地盤(回転間グリッド)の値。graded_y の関門で縁の地山を見るために使う。"""
    key = id(d)
    if key not in _DEM:
        try:
            _DEM[key] = json.load(open(os.path.join(DOC, "okabe_edo_dem.json"), encoding="utf-8"))
        except Exception:
            _DEM[key] = None
    E = _DEM[key]
    if not E:
        return None
    # ⚠ **バイリニア。** 最寄り整数セルへ丸めると、崖の肩で 0.4m の盛土厚が 2m 超として読まれ、
    #   法面が土の棚を作って法尻に段差が生えた(2026-08-24 検図)。
    fu = u - E["u0"]; fv = v - E["v0"]
    i0 = int(math.floor(fu)); j0 = int(math.floor(fv))
    tu = fu - i0; tv = fv - j0
    acc = wt = 0.0
    for dj, wv in ((0, 1 - tv), (1, tv)):
        for di, wu in ((0, 1 - tu), (1, tu)):
            i, j = i0 + di, j0 + dj
            if 0 <= j < E["nv"] and 0 <= i < E["nu"]:
                h = E["h"][j][i]
                if h is not None:
                    acc += h * wu * wv; wt += wu * wv
    if wt > 1e-9:
        return acc / wt
    # ⛔ **区画の外は捏造しない。** okabe_edo_dem は区画でクリップされているので、外は null。
    #    ここで端点値へクランプすると、断面の余白に平坦な棚が生えて隣地と街路の高さが嘘になる
    #    (2026-08-25 検図: 16本すべてで最大 5.88m ずれていた)。
    #    区画の外は **okabe_edo_world.json**(区画外=正本そのもの)から双一次で拾う。
    return _world_at(d, u, v)


_WLD = {}


def _world_at(d, u, v):
    """区画の外の地盤。`okabe_edo_world.json`(区画の中=復元 / 外=正本)から双一次で拾う。"""
    key = id(d)
    if key not in _WLD:
        try:
            _WLD[key] = (json.load(open(os.path.join(DOC, "okabe_edo_world.json"), encoding="utf-8")),
                         RGrid(d))
        except Exception:
            _WLD[key] = None
    if not _WLD[key]:
        return None
    W, gr = _WLD[key]
    x, z = gr.W(u, v)
    fx = (x - W["x0"]) / float(W["step"]); fz = (z - W["z0"]) / float(W["step"])
    i0, j0 = int(math.floor(fx)), int(math.floor(fz))
    tx, tz = fx - i0, fz - j0
    acc = wt = 0.0
    for dj, wv in ((0, 1 - tz), (1, tz)):
        for di, wu in ((0, 1 - tx), (1, tx)):
            i, j = i0 + di, j0 + dj
            if 0 <= j < W["nz"] and 0 <= i < W["nx"]:
                h = W["h"][j][i]
                if h is not None:
                    acc += h * wu * wv; wt += wu * wv
    return acc / wt if wt > 1e-9 else None


_NIWA = {}


def niwa_geom(d):
    """庭の土工の下ごしらえ(池の汀線と最大内接距離・築山の楕円)。**一度だけ算出して持つ**。"""
    key = id(d)
    if key in _NIWA:
        return _NIWA[key]
    ponds, mounds = [], []
    for g in d.get("gardens", []):
        mg = g.get("migiwa")
        if mg:
            # ⭐ **実体は Chaikin 平滑後の汀線**(2026-09-02 庭方) — 実際に掘る形はこちら。
            #   生の16点は**設計値**で、検算の円形度は両方を刷って区別する。
            ring = chaikin([(a, b) for a, b in mg["pts"]], mg.get("smooth", 2))
            dmax = 0.0
            for i9 in range(41):
                for j9 in range(41):
                    uu = min(p[0] for p in ring) + (max(p[0] for p in ring) - min(p[0] for p in ring)) * i9 / 40.0
                    vv = min(p[1] for p in ring) + (max(p[1] for p in ring) - min(p[1] for p in ring)) * j9 / 40.0
                    if _ring_in(ring, uu, vv):
                        dmax = max(dmax, sashizu_lib.poly_edge_dist(ring, uu, vv))
            ponds.append((g, mg, ring, max(dmax, 1e-6)))
        for ts in g.get("tsukiyama", []) or []:
            mounds.append((g, ts))
    _NIWA[key] = (ponds, mounds)
    return _NIWA[key]


def niwa_y(d, u, v, nat):
    """**庭の土工の後の地盤。**池の床・岸の摺り付け・築山。触らない所は None。

    ⭐ 段(`design_y`)より**先**に見る — 斜路・石段と同じ順。後にすると池も築山も
      面の高さに隠れ、切盛図にも土量にも断面にも出ない(2026-08-25 検図12巡と同じ型)。
    ・池の床 … 汀から中心へ向かう**放物面**。汀で水面、最深で `bedY`。
    ・岸 … 汀から外へ `bankRun`[間] で面の高さへ摺り付ける。
    ・築山 … 裾で自然地盤、頂で `topY` の**円錐**(裾に平場を作らない)。"""
    ponds, mounds = niwa_geom(d)
    for g, ts in mounds:
        au = ts["dU"] / 2.0; av = ts["dV"] / 2.0
        r = math.hypot((u - ts["u"]) / au, (v - ts["v"]) / av)
        if r <= 1.0:
            base = nat if nat is not None else ts["topY"]
            return base + (ts["topY"] - base) * (1.0 - r)
    for g, mg, ring, dmax in ponds:
        dd = sashizu_lib.poly_edge_dist(ring, u, v)
        if _ring_in(ring, u, v):
            t9 = min(1.0, dd / dmax)
            y9 = mg["waterY"] - (mg["waterY"] - mg["bedY"]) * (1.0 - (1.0 - t9) ** 2)
            sl = mg.get("shallow")
            if sl and sl["v0"] <= v <= sl["v1"]:
                y9 = max(y9, sl["bedY"])       # 渡りの区間は浅い平床(足元を深くしない)
            return y9
        if dd < mg["bankRun"]:
            tgt = design_y(d, u, v)
            if tgt is None:
                tgt = nat
            if tgt is None:
                return None
            return mg["waterY"] + (tgt - mg["waterY"]) * (dd / mg["bankRun"])
    return None


def graded_y(d, u, v, nat, walled=None):
    """**造成後の地盤**。正典は sashizu_lib.graded_y —
    一定勾配の法面(盛土 1:batterFill / 切土 1:batterCut)+着地判定(cap の内で
    現地形に着地しない法面は出さない)+斜路・石段の先読み+盛土floor の土井式。
    2026-08-26 のユーザー指示「岡部式と土井式の2パターンがあってよいのか?統一すべきでは?」
    で、旧岡部式(縁の盛土厚の逓減形 cbee45a)を廃してこれへ統一した。
    段の縁が等高線なりの多角形(`poly`)である点は lib が poly 分岐で受ける。
    土井式が要する法面パラメタ(batterFill/batterCut/featherCap)は当邸の設計値に
    すべて有るので、土井の既定値に頼る項目は無い。
    ⚠ 当邸の石段(atWall なし)と坂(折れ線 `pts`)は従前どおり地盤に出ない(別勘定)。
    ⭐ 2026-09-02: **庭の土工(池・築山)を段より先に重ねる**(`niwa_y`)。"""
    ny = niwa_y(d, u, v, nat)
    if ny is not None:
        return ny
    return sashizu_lib.graded_y(d, u, v, nat, in_parcel, walled)


def cutfill_svg(d, ter):
    """切盛図。造成前の地形(実測)と設計の面の差を、格子のセル塗りで示す。"""
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), 900.0, pad=14.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 切盛図")
    st = ter["step"]
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.55"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    vol_f = vol_c = 0.0
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * st
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * st
            nat = ter["h"][iv][iu]
            if nat is None:
                continue
            dy = graded_y(d, u, v, nat, we)
            dz = dy - nat
            if abs(dz) < CF_SKIP:
                continue                       # 触らない = 素地のまま(下塗りの斜面色)
            a = (st * d["const"]["ken"]) ** 2
            if dz > 0:
                vol_f += dz * a
            else:
                vol_c += -dz * a
            pts = [gr.W(u - st / 2, v - st / 2), gr.W(u + st / 2, v - st / 2),
                   gr.W(u + st / 2, v + st / 2), gr.W(u - st / 2, v + st / 2)]
            g.append('<polygon points="%s" fill="%s"/>'
                     % (" ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts), cf_color(dz)))
    # 段の輪郭(マスクの前に描いて区画線で切る)
    for t in d["terraces"]:
        pts = [gr.W(a, b) for a, b in tpoly(t)]
        g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="0.8" '
                 'stroke-dasharray="5 4" opacity="0.8"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts))
        # ⭐ **抜き(平坦化しない区画)の輪郭を切盛図にも出す** — K060。
        #   ここに出ていないと「無彩の升」が『均した結果ぴったり』なのか
        #   『そもそも面を作っていない』のか読み分けられない。
        for hp in tholes(t):
            q9 = [gr.W(a9, b9) for a9, b9 in hp]
            g.append('<polygon points="%s" fill="none" stroke="var(--dim)" stroke-width="1.2" '
                     'stroke-dasharray="3 3" opacity="0.9"/>'
                     % " ".join("%.1f,%.1f" % (pr.X(x9), pr.Y(z9)) for x9, z9 in q9))
    # 敷地の外をマスクしてから区画線
    ring = " ".join("L %.1f %.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P)
    g.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z M%s Z" fill="var(--paper)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, ring[1:]))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    # 段の名 — 区画の中に入っているセルの重心へ置く(素の中心だと敷地の外へ出る)
    for t in d["terraces"]:
        su = sv = 0.0; n = 0
        iv = 0
        while iv < ter["nv"]:
            v = ter["v0"] + iv * st; iv += 1
            if not (t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9):
                continue
            for iu in range(ter["nu"]):
                u = ter["u0"] + iu * st
                if tin(t, u, v) and ter["h"][iv - 1][iu] is not None:
                    su += u; sv += v; n += 1
        if not n:
            continue
        cx, cz = gr.W(su / n, sv / n)
        g.append(T(pr.X(cx), pr.Y(cz), "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"]),
                   "anS", "middle"))
    for m in d["munes"]:
        pts = [gr.W(m["u0"], m["v0"]), gr.W(m["u1"], m["v0"]),
               gr.W(m["u1"], m["v1"]), gr.W(m["u0"], m["v1"])]
        g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.1" opacity="0.65"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts))
    gp = d["gate"]["pos"]
    g.append('<circle cx="%.1f" cy="%.1f" r="5.5" fill="var(--shu)"/>' % (pr.X(gp[0]), pr.Y(gp[1])))
    g.append(T(pr.X(gp[0]) + 9, pr.Y(gp[1]) - 5, "表門", "sr"))
    g.append(T(pr.W - 6, 15, "北 ↑　左=西", "anS", "end"))
    g.append("</svg>")
    return "\n".join(g), vol_f, vol_c


def cutfill_table(d, ter):
    """段ごとの切盛。**切盛図とまったく同じ走査**(graded_y・±0.05m の不感帯)で積み、
    段に属さないセルを『段の外(法面)』の行にして、行の合計が総量に一致するようにする。
    ⚠ 2026-08-24 検図: 表の切土 704 が総量 702 を上回っていた — 表が design_y、
    図が graded_y と別々に積んでいたため。返り値は (html, 盛土, 切土)。"""
    st = ter["step"]; a = (st * d["const"]["ken"]) ** 2
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    acc = dict((t["name"], [0.0, 0.0, 0.0, 0.0, 0]) for t in d["terraces"])
    acc["_slope"] = [0.0, 0.0, 0.0, 0.0, 0]
    area = dict((t["name"], 0) for t in d["terraces"])
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * st
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * st
            nat = ter["h"][iv][iu]
            if nat is None:
                continue
            key = "_slope"
            for t in d["terraces"]:
                if tin(t, u, v) and in_parcel(d, u, v):
                    key = t["name"]
                    area[t["name"]] += 1
                    break
            dz = graded_y(d, u, v, nat, we) - nat
            if abs(dz) < 0.05:
                continue
            r = acc[key]
            if dz > 0:
                r[0] += dz * a; r[2] = max(r[2], dz)
            else:
                r[1] += -dz * a; r[3] = max(r[3], -dz)
            r[4] += 1
    rows = []
    tf = tc = 0.0
    for t in d["terraces"]:
        f, c, mf, mc, _n = acc[t["name"]]
        tf += f; tc += c
        rows.append("<tr><td>%s</td><td>%.1f</td><td>%.0f 坪</td><td>%.0f m³</td><td>%.1f m</td>"
                    "<td>%.0f m³</td><td>%.1f m</td></tr>"
                    % (TERR_JA.get(t["name"], t["name"]), t["y"],
                       area[t["name"]] * a / TSUBO, f, mf, c, mc))
    f, c, mf, mc, _n = acc["_slope"]
    tf += f; tc += c
    rows.append("<tr><td>段の外(法面の摺り付け)</td><td>—</td><td>—</td><td>%.0f m³</td>"
                "<td>%.1f m</td><td>%.0f m³</td><td>%.1f m</td></tr>" % (f, mf, c, mc))
    rows.append("<tr><td><b>拝領時造成の計</b>(段+法面)</td><td></td><td></td><td><b>%.0f m³</b></td>"
                "<td></td><td><b>%.0f m³</b></td><td></td></tr>" % (tf, tc))
    # 坂の路盤 — 「造成しない斜面」の中なので段別の走査には出ないが、土工は現に生じる。
    # ⚠ 2026-08-24 検図: 図のどこからも読めない土工が 47m³ あった。**拝領時造成には足さない**。
    rf = rc = 0.0
    for rp in d.get("ramps", []):
        ea = rp.get("earth", {})
        if not ea:
            continue
        rf += ea.get("moridoM3", 0.0); rc += ea.get("kiridoM3", 0.0)
        rows.append("<tr><td>坂の路盤 <code>%s</code>(斜面の中・<b>別勘定</b>)</td><td>—</td><td>—</td>"
                    "<td>%.0f m³</td><td>%.1f m</td><td>%.0f m³</td><td>%.1f m</td></tr>"
                    % (rp["name"], ea.get("moridoM3", 0.0), ea.get("moridoMax", 0.0),
                       ea.get("kiridoM3", 0.0), ea.get("kiridoMax", 0.0)))
    if rf or rc:
        rows.append("<tr><td><b>総計</b></td><td></td><td></td><td><b>%.0f m³</b></td><td></td>"
                    "<td><b>%.0f m³</b></td><td></td></tr>" % (tf + rf, tc + rc))
    return ('<div class="tw"><table><thead><tr><th>段</th><th>面の高さ</th><th>面積</th>'
            "<th>盛土量</th><th>最大盛土</th><th>切土量</th><th>最大切土</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>", tf, tc)


# ---------------------------------------------------------------- 現況図(段彩+等高線)
# 段彩の色は地図の記号なので、明暗のテーマに関わらず固定(紙の地形図と同じ読み方をさせる)


def _grad_band(bb):
    """検査に残った件の**自然勾配の帯を算出**して返す(2026-08-25 検図: 手書きの
    「65〜93%」が、その直後に列挙する自分の数値と合っていなかった)。"""
    q = [float(x) for line in bb for x in re.findall(r"自然 (\d+(?:\.\d+)?)%", line)]
    return ("%.0f〜%.0f%%" % (min(q), max(q))) if q else "—"


def _fill_where(d, ter):
    """**盛土・切土が濃く出る所**を算出して名で返す。
    ⚠ 2026-08-25 検図: 手書きの所在リストが地盤の更新に追随せず、
    最大盛土も最大切土もそのリストに入っていなかった(§3c「何を切るかは手で書かない」)。"""
    st = ter["step"]
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    best = {"盛土": (0.0, None), "切土": (0.0, None)}
    cnt = {}
    for iv in range(ter["nv"]):
        for iu in range(ter["nu"]):
            nat = ter["h"][iv][iu]
            if nat is None:
                continue
            u = ter["u0"] + iu * st; v = ter["v0"] + iv * st
            dz = graded_y(d, u, v, nat, we) - nat
            if abs(dz) < 0.05:
                continue
            kind = "盛土" if dz > 0 else "切土"
            nm = None
            for t in d["terraces"]:
                if tin(t, u, v):
                    nm = TERR_JA.get(t["name"], t["name"]); break
            nm = nm or "段の外(法面)"
            if abs(dz) > 1.0:
                cnt[(kind, nm)] = cnt.get((kind, nm), 0) + 1
            if abs(dz) > best[kind][0]:
                best[kind] = (abs(dz), (u, v, nm))
    out = []
    for kind in ("盛土", "切土"):
        m9, loc = best[kind]
        if loc:
            out.append("最大%s %.2fm は<b>%s</b>のグリッド(%.0f, %.0f)"
                       % (kind, m9, loc[2], loc[0], loc[1]))
    for (kind, nm), c in sorted(cnt.items(), key=lambda q: -q[1])[:3]:
        out.append("1m超の%sが %s に %dセル" % (kind, nm, c))
    return " ／ ".join(out) or "—"


def kindai_svg(d, W=900.0):
    """**復元の効き方** — 正本(近代造成を含む現代の地面)と江戸期の復元地盤の差を塗る。
    ⚠ 2026-08-25 検図: この屋敷で最大の土工は「復元そのもの」(拝領時造成の約6倍)なのに、
    どのセルをどのモデルで置き換えたかが**どの図にも描かれていなかった**。
    返すのは (svg, 盛土m³, 切土m³, 最大盛, 最大切, 触ったセル率)。"""
    base = json.load(open(os.path.join(DOC, "base_dem.json"), encoding="utf-8"))
    world = json.load(open(os.path.join(DOC, "okabe_edo_world.json"), encoding="utf-8"))
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), W, pad=14.0)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 復元の効き方")
    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.35"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    ix0 = (world["x0"] - base["x0"]) // base["step"]
    iz0 = (world["z0"] - base["z0"]) // base["step"]
    a = float(world["step"]) ** 2
    vf = vc = 0.0; mf = mc = 0.0; tot = hit = 0
    for iz in range(world["nz"]):
        for ix in range(world["nx"]):
            x = world["x0"] + world["step"] * ix
            z = world["z0"] + world["step"] * iz
            if not _pt_in_poly(P, x, z):
                continue
            b = base["h"][iz + iz0][ix + ix0]; e = world["h"][iz][ix]
            if b is None or e is None:
                continue
            tot += 1
            dz = e - b
            if abs(dz) < 0.05:
                continue
            hit += 1
            if dz > 0:
                vf += dz * a; mf = max(mf, dz)
            else:
                vc += -dz * a; mc = max(mc, -dz)
            g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (pr.X(x - 1), pr.Y(z + 1), pr.L(2), pr.L(2), cf_color(dz)))
    ring = " ".join("L %.1f %.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P)
    g.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z M%s Z" fill="var(--paper)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, ring[1:]))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    g.append(T(pr.W - 6, 15, "北 ↑　左=西", "anS", "end"))
    g.append("</svg>")
    return ("\n".join(g), vf, vc, mf, mc, (100.0 * hit / tot) if tot else 0.0)


def _pt_in_poly(P, x, z):
    n = len(P); c = False
    for i in range(n):
        (ax, az), (bx, bz) = P[i], P[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (bx - ax) * (z - az) / (bz - az):
            c = not c
    return c


def dem_svg(d, dem, others, W=900.0):
    x0, z0, st = dem["x0"], dem["z0"], dem["step"]
    x1, z1 = x0 + (dem["nx"] - 1) * st, z0 + (dem["nz"] - 1) * st
    pr = Proj(x0, x1, z0, z1, W, pad=0.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 現況図(造成前の地形)")
    g.append('<defs><clipPath id="dc%d"><rect x="0" y="0" width="%.1f" height="%.1f"/></clipPath></defs>'
             % (_SVN[0], pr.W, pr.H))
    g.append('<g clip-path="url(#dc%d)">' % _SVN[0])
    for iz in range(dem["nz"] - 1):                       # 同色の連続セルは1つの矩形にまとめる
        run0, runc = 0, None
        for ix in range(dem["nx"]):
            c = None
            if ix < dem["nx"] - 1:
                c = dem_color((dem["h"][iz][ix] + dem["h"][iz][ix + 1]
                               + dem["h"][iz + 1][ix] + dem["h"][iz + 1][ix + 1]) / 4.0)
            if c != runc:
                if runc is not None:
                    g.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>'
                             % (pr.X(x0 + run0 * st), pr.Y(z0 + (iz + 1) * st),
                                pr.L(st) * (ix - run0) + 0.4, pr.L(st) + 0.4, runc))
                run0, runc = ix, c
    lo = min(min(r) for r in dem["h"]); hi = max(max(r) for r in dem["h"])
    lv = math.floor(lo / 2.0) * 2.0
    while lv <= hi:
        segs = _iso(dem, lv)
        if segs:
            major = abs(lv % 10.0) < 1e-6
            g.append('<path d="%s" fill="none" stroke="#3A3428" stroke-width="%.1f" opacity="%.2f"/>'
                     % (" ".join("M%.1f %.1f L%.1f %.1f" % (pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]))
                                 for a, b in segs), 1.4 if major else 0.6, 0.75 if major else 0.4))
            if major:
                mx = max(segs, key=lambda s: s[0][0])[0]
                g.append('<text class="jo" x="%.1f" y="%.1f" style="fill:#3A3428;font-weight:700"'
                         ' text-anchor="middle">%d</text>' % (pr.X(mx[0]), pr.Y(mx[1]) + 3, lv))
        lv += 2.0
    # 隣の区画 → 当屋敷の順に描く
    for (pts, col, wdt, lab, lx, lz) in others:
        g.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="%.1f" opacity="0.95"/>'
                 % (" ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in pts), col, wdt))
        px, py = pr.X(lx), pr.Y(lz)
        if lab and 60 < px < pr.W - 60 and 20 < py < pr.H - 20:
            g.append('<text class="anS" x="%.1f" y="%.1f" style="fill:#241F16;font-weight:700;'
                     'text-anchor:middle;paint-order:stroke;stroke:#FFFFFF;stroke-width:3.5px">%s</text>'
                     % (px, py, lab))
    for s in d["sections"]:
        if s["axis"] == "u":
            f9, t9 = _sec_span(d, s)
            a = gr.W(s["at"], f9); b = gr.W(s["at"], t9)
        else:
            f9, t9 = _sec_span(d, s)
            a = gr.W(f9, s["at"]); b = gr.W(t9, s["at"])
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]), "#7A2E1E", 0.9, dash="8 5", op=0.9))
        g.append('<text class="jo" x="%.1f" y="%.1f" style="fill:#7A2E1E;font-weight:700;'
                 'text-anchor:middle">%s</text>'
                 % (pr.X(b[0]), pr.Y(b[1]) - 4, s["name"].split(" ")[0]))
    gp = d["gate"]["pos"]
    g.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#FFFFFF" stroke="#7A2E1E" stroke-width="1.6"/>'
             % (pr.X(gp[0]), pr.Y(gp[1]) - 7, pr.X(gp[0]) - 6, pr.Y(gp[1]) + 4, pr.X(gp[0]) + 6, pr.Y(gp[1]) + 4))
    g.append('<text class="sr" x="%.1f" y="%.1f" style="fill:#7A2E1E;font-weight:700">表門</text>'
             % (pr.X(gp[0]) + 10, pr.Y(gp[1]) + 4))
    g.append("</g>")
    # 座標の目盛・スケール・方位
    for x in range(int(math.ceil(x0 / 50.0) * 50), int(x1) + 1, 50):
        g.append(LN(pr.X(x), 0, pr.X(x), 7, "#3A3428", 1.0))
        g.append('<text class="jo" x="%.1f" y="%.1f" style="fill:#3A3428;text-anchor:middle">%d</text>'
                 % (pr.X(x), 17, x))
    for z in range(int(math.ceil(z0 / 50.0) * 50), int(z1) + 1, 50):
        g.append(LN(0, pr.Y(z), 7, pr.Y(z), "#3A3428", 1.0))
        g.append('<text class="jo" x="10" y="%.1f" style="fill:#3A3428">%d</text>' % (pr.Y(z) + 3, z))
    sb = pr.L(100.0)
    g.append('<rect x="8" y="%.1f" width="%.1f" height="30" fill="#FFFFFF" opacity="0.82"/>'
             % (pr.H - 38, sb + 20))
    g.append('<rect x="14" y="%.1f" width="%.1f" height="5" fill="#3A3428"/>' % (pr.H - 26, sb / 2))
    g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="5" fill="none" stroke="#3A3428" stroke-width="1"/>'
             % (14 + sb / 2, pr.H - 26, sb / 2))
    g.append('<text class="jo" x="14" y="%.1f" style="fill:#3A3428">0</text>' % (pr.H - 30))
    g.append('<text class="jo" x="%.1f" y="%.1f" style="fill:#3A3428;text-anchor:middle">100 m</text>'
             % (14 + sb, pr.H - 30))
    g.append('<polygon points="%.1f,14 %.1f,34 %.1f,27 %.1f,34" fill="#3A3428"/>'
             % (pr.W - 26, pr.W - 33, pr.W - 26, pr.W - 19))
    g.append('<text class="jo" x="%.1f" y="46" style="fill:#3A3428;text-anchor:middle;font-weight:700">N</text>'
             % (pr.W - 26))
    g.append('<rect x="0.5" y="0.5" width="%.1f" height="%.1f" fill="none" stroke="#3A3428" stroke-width="1.6"/>'
             % (pr.W - 1, pr.H - 1))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 動線
RK = {"omote": ("var(--shu)", "表向"), "yaku": ("var(--take)", "役方"),
      "katte": ("var(--nagaya)", "勝手"), "oku": ("var(--hei)", "奥向")}


def routes_svg(d, u0, u1, v0, v1):
    pr = LProj(u0, u1, v0, v1, 900.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 動線")
    P = [gr.L(x, z) for x, z in d["polygon"]]
    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.5"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    for t in d["terraces"]:
        g.append(pr.poly(tpoly(t),
                         fill=dan_color(d, t["y"]), op=1.0))
        for hp in tholes(t):                      # 抜き — K060
            g.append(pr.poly(hp, fill=_pat(), stroke="var(--dim)", sw=0.8, dash="4 3"))
        for kp in tkeeps(t):
            g.append(pr.poly(kp, fill=dan_color(d, t["y"]), op=1.0))
    ring = " ".join("L %.1f %.1f" % (pr.X(u), pr.Y(v)) for u, v in P)
    g.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z M%s Z" fill="var(--paper2)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, ring[1:]))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    for n in d["gardens"]:
        g.append(pr.rect(n["u0"], n["v0"], n["u1"], n["v1"],
                         fill="var(--shirasu)" if n.get("kind") == "shirasu" else "var(--niwa)",
                         stroke="var(--ink)", sw=0.5, op=0.85))
    for m in d["munes"] + d["service"]:
        g.append(pr.rect(m["u0"], m["v0"], m["u1"], m["v1"],
                         fill="var(--ink-mid)", stroke="var(--ink)", sw=0.6, op=0.85))
        nm = MUNE_JA.get(m.get("name"), m.get("label", ""))
        if nm and abs(m["u1"] - m["u0"]) >= 5:
            g.append(T((pr.X(m["u0"]) + pr.X(m["u1"])) / 2,
                       (pr.Y(m["v0"]) + pr.Y(m["v1"])) / 2 + 4, nm, "rmS", "middle", 11.0))
    for rp in d.get("ramps", []):                            # 坂
        pts = [(pr.X(u), pr.Y(v)) for u, v in rp["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="7" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.35"/>'
                 % " ".join("%.1f,%.1f" % q for q in pts))
    for k in d["kaidans"]:                                   # 動線がどこで段を越えるか
        ax, at2, ka, kb, cu, cv = kgeom(k)
        hw = k["w"] / 2 / 1.818
        if ax == "v":
            g.append(pr.rect(at2 - hw, ka, at2 + hw, kb,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        else:
            g.append(pr.rect(ka, at2 - hw, kb, at2 + hw,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        g.append(T(pr.X(cu), pr.Y(cv) - 10, "%s %d段" % (k["name"], k["steps"]), "anG", "middle"))
    # 表向(門の軸)を最後に描いて一番上に置く
    for r in sorted(d["routes"], key=lambda x: x["kind"] == "omote"):
        col = RK.get(r["kind"], ("var(--dim)", ""))[0]
        pts = [(pr.X(u), pr.Y(v)) for u, v in r["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3.4" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
                 % (" ".join("%.1f,%.1f" % p for p in pts), col))
        for i in range(len(pts) - 1):                        # 進む向きの矢
            ax, ay = pts[i]; bx, by = pts[i + 1]
            L = math.hypot(bx - ax, by - ay)
            if L < 26:
                continue
            mx, my = (ax + bx) / 2, (ay + by) / 2
            dx, dy = (bx - ax) / L, (by - ay) / L
            g.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>'
                     % (mx + dx * 7, my + dy * 7, mx - dx * 4 - dy * 4.5, my - dy * 4 + dx * 4.5,
                        mx - dx * 4 + dy * 4.5, my - dy * 4 - dx * 4.5, col))
        ex, ey = pts[-1]
        g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (ex, ey, col))
        g.append(T(ex + 7, ey + 4, r["label"], "sl", fill=col))
    gp = gr.L(*d["gate"]["pos"])
    g.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (pr.X(gp[0]), pr.Y(gp[1])))
    g.append(T(pr.X(gp[0]), pr.Y(gp[1]) - 10, "▼ 表門", "sr", "middle"))
    g.append(T(4, 15, "上=東(三べ坂前身の道)／左=北／下=西／右=南。朱枠=石段", "anS"))
    g.append("</svg>")
    return "\n".join(g)


def routes_table(d):
    """動線の延長と昇り。段をいくつ越えるかまで出す。"""
    K = d["const"]["ken"]
    rows = []
    for r in d["routes"]:
        ln = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(r["pts"], r["pts"][1:])) * K
        # 高さは「段の面」だけでなく、始点が門・通用口ならその敷居から測る(検図 L-2)
        ys = [design_y(d, u, v) for u, v in r["pts"]]
        ys = [y for y in ys if y is not None]
        u0, v0 = r["pts"][0]
        if abs(u0) < 3 and abs(v0) < 3:
            ys.append(d["gate"]["sill"])                    # 表門の敷居
        for ko in d.get("komon", []):
            gp2 = ko.get("_gridPos")
            if gp2 and math.hypot(u0 - gp2[0], v0 - gp2[1]) < 4:
                ys.append(ko["sill"])
        # ⭕ **継いだ坂は延長も昇降も足す**(2026-09-03 検図5巡目 K249) —
        #   ⛔ 起点が一致する坂しか拾わないと、末尾に継いだ坂(勝手の坂)が数から落ちる。
        for rp2 in d.get("ramps", []):
            ends = (tuple(rp2["pts"][0]), tuple(rp2["pts"][-1]))
            mine = (tuple(r["pts"][0]), tuple(r["pts"][-1]))
            near = min(math.hypot(a8[0] - b8[0], a8[1] - b8[1])
                       for a8 in ends for b8 in mine)
            if near < 1.0:
                m8 = ramp_metrics(d, rp2) or {}
                ln += m8.get("len", 0.0)
                ys.append(rp2["prof"][0][2])
                ys.append(rp2["prof"][-1][2])
        rise = (max(ys) - min(ys)) if ys else 0.0
        steps = 0
        counted = set()
        for a, b in zip(r["pts"], r["pts"][1:]):
            for k in d["kaidans"]:
                if k["name"] in counted:
                    continue
                _ax, _at, _ka, _kb, cu, cv = kgeom(k)
                if min(a[0], b[0]) - 1.2 <= cu <= max(a[0], b[0]) + 1.2 and \
                   min(a[1], b[1]) - 1.2 <= cv <= max(a[1], b[1]) + 1.2:
                    steps += k["steps"]; counted.add(k["name"])
        rows.append("<tr><td><span style='color:%s'>━</span> %s</td><td>%s</td><td>%.0f m</td>"
                    "<td>%+.1f m</td><td>%d 段</td><td class='note'>%s</td></tr>"
                    % (RK.get(r["kind"], ("var(--dim)", ""))[0], r["label"],
                       RK.get(r["kind"], ("", "—"))[1], ln, rise, steps, inline(r.get("_", ""))))
    return ('<div class="tw"><table><thead><tr><th>動線</th><th>系統</th><th>延長</th>'
            "<th>昇り</th><th>石段</th><th class='note'>通る順</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 断面の位置図(キープラン)
def key_plan(d, axis, W=760.0):
    """断面の切り位置だけを示す小さな平面。面の色分けと切り線・番号を載せる。"""
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), W, pad=16.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "断面の位置図")

    def gpoly(u0, v0, u1, v1, fill, op=1.0):
        return gpolyN([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], fill, op)

    def gpolyN(gp, fill, op=1.0):
        pts = [gr.W(a, b) for a, b in gp]
        return ('<polygon points="%s" fill="%s" opacity="%.2f"/>'
                % (" ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts), fill, op))

    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.85"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    for t in d["terraces"]:
        g.append(gpolyN(tpoly(t), dan_color(d, t["y"])))
        for hp in tholes(t):                      # 抜き — K060
            g.append(gpolyN(hp, _pat(), 1.0))
        for kp in tkeeps(t):
            g.append(gpolyN(kp, dan_color(d, t["y"])))
    ring = " ".join("L %.1f %.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P)
    g.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z M%s Z" fill="var(--paper2)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, ring[1:]))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    for m in d["munes"] + d["service"]:
        g.append(gpoly(m["u0"], m["v0"], m["u1"], m["v1"], "var(--ink-mid)", 0.75))
    gp = d["gate"]["pos"]
    g.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="var(--shu)"/>' % (pr.X(gp[0]), pr.Y(gp[1])))

    for s in d["sections"]:
        cut = s["axis"] == axis
        if s["axis"] == "u":
            f9, t9 = _sec_span(d, s)
            a = gr.W(s["at"], f9); b = gr.W(s["at"], t9)
        else:
            f9, t9 = _sec_span(d, s)
            a = gr.W(f9, s["at"]); b = gr.W(t9, s["at"])
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]),
                    "var(--shu)" if cut else "var(--dim)",
                    2.0 if cut else 0.7, dash=None if cut else "6 5",
                    op=1.0 if cut else 0.45))
        if cut:
            nm = s["name"].split(" ")[0]
            for q in (a, b):
                g.append(T(pr.X(q[0]), pr.Y(q[1]) - 5, nm, "sr", "middle"))
    g.append(T(pr.W - 6, 15, "北 ↑　左=西", "anS", "end"))
    g.append(T(6, 15, "太い朱線=この面の断面／細い破線=もう一方の面", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 断面
def _sec_ends(d, sec):
    """断面の両端が区画のどの辺に当たるかを算出して、隣は誰かで返す。"""
    gr = RGrid(d)
    P = d["polygon"]
    n = len(P)
    lo, hi = _sec_span(d, sec)
    out = []
    for w in (lo + 3.0, hi - 3.0):
        u, v = (sec["at"], w) if sec["axis"] == "u" else (w, sec["at"])
        x, z = gr.W(u, v)
        best = None
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz or 1e-9
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
            dd = math.hypot(x - (a[0] + dx * t), z - (a[1] + dz * t))
            if best is None or dd < best[0]:
                best = (dd, i)
        e = d["edges"][best[1]] if best[1] < len(d["edges"]) else {}
        out.append("辺%d %s" % (best[1], e.get("neighbor", "")))
    return out[0], out[1]


def _sec_span(d, sec):
    """断面の描画範囲を**区画から算出する**(±2間の余白)。
    ⚠ 2026-08-25 検図: 追加した2本とも from/to を既存の断面からコピーしており、
    v=86 は区画の北 32.7m を切り落とし、u=−26 は手前 21.8m を空白にしていた。
    手で持つ限り再発するので算出に落とす。"""
    lo = hi = None
    w = -80.0
    while w < 200.0:
        u, v = (sec["at"], w) if sec["axis"] == "u" else (w, sec["at"])
        if in_parcel(d, u, v):
            lo = w if lo is None else lo
            hi = w
        w += 0.5
    if lo is None:
        return 0.0, 100.0
    return math.floor(lo - 3.0), math.ceil(hi + 3.0)


def section_crossings(d, sec):
    """切り線が実際に横切る物の名。**見出しに手で書かない**(§3c)。"""
    out = []
    for o in d["munes"] + d["service"] + d["gardens"]:
        if sec["axis"] == "u":
            hit = o["u0"] <= sec["at"] <= o["u1"]
        else:
            hit = o["v0"] <= sec["at"] <= o["v1"]
        if hit:
            out.append(MUNE_JA.get(o.get("name"), o.get("label", o.get("name", ""))))
    for k in d["kaidans"]:
        ax, at2, a, b, cu, cv = kgeom(k)
        if (sec["axis"] == "u" and abs(sec["at"] - at2) <= k["w"] / 2 / 1.818) or \
           (sec["axis"] == "v" and a <= sec["at"] <= b):
            out.append(k["name"])
    return [x for x in dict.fromkeys(out) if x]


def section_svg(d, sec):
    gr = RGrid(d)
    K = d["const"]["ken"]
    at, ex = sec["at"], sec["vExag"]
    w0, w1 = _sec_span(d, sec)

    # 地盤 = 郭の段が最優先。natural は段の外(未造成の区間)だけ地盤線に使い、
    # 全点は現地形の破線として別に描く(検図 H-1: 段の下に natural を混ぜて跳ねさせない)
    segs = []
    for t in d["terraces"]:
        for a, b in tcuts(t, sec["axis"], at):     # ← 多角形の切り口(外接矩形でない)
            if min(b, w1) > max(a, w0):
                segs.append((max(a, w0), min(b, w1), t["y"]))
    segs.sort()
    nat = sorted(sec.get("natural", []))

    def nat_y(w):
        if not nat:
            return None
        if w <= nat[0][0]:
            return nat[0][1]
        for (na, ya2), (nb, yb2) in zip(nat, nat[1:]):
            if na <= w <= nb:
                return ya2 + (yb2 - ya2) * (w - na) / (nb - na)
        return nat[-1][1]

    we9 = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])

    def uv_at(w):
        return (at, w) if sec["axis"] == "u" else (w, at)

    def gnd_y(w):
        """造成後の地盤 — 段の中は段の高さ、外は法面で現地形へ摺り付く(graded_y と同じ規則)。"""
        ny = nat_y(w)
        u9, v9 = uv_at(w)
        gy = graded_y(d, u9, v9, ny, we9)
        if gy is not None:
            return gy
        return ny if ny is not None else (segs[0][2] if segs else 20.0)

    # 法面を含めて滑らかに拾う(段の縁の折れは壁のある辺だけに残る)
    NS = 400
    prof = []
    for i9 in range(NS + 1):
        x2 = w0 + (w1 - w0) * i9 / float(NS)
        prof.append((x2, gnd_y(x2)))

    # 天地は「実際に描かれる一番高い物」から決める(段の高さ+8m 固定だと空白が open する)
    fl0 = d["const"]["gotenFloor"]
    tops = []
    for m in d["munes"] + d["service"]:
        if (sec["axis"] == "u" and m["u0"] <= at <= m["u1"]) or \
           (sec["axis"] == "v" and m["v0"] <= at <= m["v1"]):
            rf0 = (d.get("roofs") or {}).get(m.get("roof") or "") or {}
            tops.append((m["y"] + rf0.get("ridgeH", sec["ridgeAbove"])) if m.get("obi")
                        else (m["y"] + fl0 + sec["ridgeAbove"]))
    ys = [p[1] for p in prof]
    y1 = max(ys + tops + [d["gate"]["sill"] + d["gate"]["plan"]["monH"]
                          if (sec["axis"] == "u" and abs(sec["at"]) < 2) else -99]) + 1.6
    y0 = min(ys) - 3.0
    W = 1000.0
    sx = W / float(w1 - w0)
    HEAD, FOOT = 26.0, 46.0
    H = (y1 - y0) * sx * ex + HEAD + FOOT

    def X(w): return (w - w0) * sx
    def Y(y): return HEAD + (y1 - y) * sx * ex

    g = _sv(W, H, "岡部筑前守上屋敷 %s" % sec["name"])
    pts = [(X(w0), Y(y0 + 0.01))] + [(X(a), Y(b)) for a, b in prof] + [(X(w1), Y(y0 + 0.01))]
    g.append('<polygon points="%s" fill="var(--dan)" stroke="var(--ink)" stroke-width="1.4"/>'
             % " ".join("%.1f,%.1f" % p for p in pts))
    # 切盛のハッチ — 現地形と造成後の地盤の間を塗り分ける(盛土=暖色/切土=寒色)
    if nat:
        step9 = (w1 - w0) / 240.0
        w9 = w0
        while w9 < w1 - 1e-9:
            wa, wb = w9, min(w9 + step9, w1)
            wm = (wa + wb) / 2.0
            n9, gg = nat_y(wm), gnd_y(wm)
            w9 = wb
            if n9 is None or abs(gg - n9) < 0.05:
                continue
            g.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" opacity="0.95"/>'
                     % (X(wa), Y(nat_y(wa)), X(wb), Y(nat_y(wb)),
                        X(wb), Y(gnd_y(wb)), X(wa), Y(gnd_y(wa)), cf_color(gg - n9)))
    # 無造成の区間 — 地盤線の直下に斜面色の帯を敷き、長い区間には「無造成」と入れる。
    # 「色が付いていない=反映漏れか、触っていないのか」が読めないという指摘への対応。
    runs9 = []
    cur9 = None
    for (x2, y2) in prof:
        n2 = nat_y(x2)
        same = n2 is not None and abs(y2 - n2) < 0.05
        if same and cur9 is None:
            cur9 = [x2, x2]
        elif same:
            cur9[1] = x2
        elif cur9 is not None:
            runs9.append(cur9); cur9 = None
    if cur9 is not None:
        runs9.append(cur9)
    for (a9, b9) in runs9:
        if b9 - a9 < 1.5:
            continue
        pts9 = [(X(x9), Y(gnd_y(x9))) for x9 in
                [a9 + (b9 - a9) * k / 40.0 for k in range(41)]]
        g.append('<polyline points="%s" fill="none" stroke="var(--pl-slope)" stroke-width="7" '
                 'opacity="0.95" stroke-linecap="butt"/>'
                 % " ".join("%.1f,%.1f" % p for p in pts9))
        if b9 - a9 >= 7:
            xm9 = (a9 + b9) / 2.0
            g.append(T(X(xm9), Y(gnd_y(xm9)) + 16, "無造成", "anS2", "middle"))
    # 面割りの色帯(地表下0.6m)と面の高さ — 切盛のハッチの上に置く(数字が隠れないように)
    for a, b, y in segs:
        if b > a:
            g.append(R(X(a), Y(y), X(b) - X(a), 0.6 * sx * ex,
                       fill=dan_color(d, y), op=0.95))
    for a, b, y in segs:
        if b - a >= 6 - 1e-9:
            g.append(T((X(a) + X(b)) / 2, Y(y) + 14, "%.1f m" % y, "anS", "middle"))
    # 現地形の破線(実測 natural 全点 — 造成域の下も描き、切土/盛土を図で読めるようにする)
    natc = [p for p in nat if w0 <= p[0] <= w1]
    if len(natc) >= 2:
        g.append('<polyline points="%s" fill="none" stroke="var(--dim)" stroke-width="1.1" '
                 'stroke-dasharray="5 4" opacity="0.85"/>'
                 % " ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in natc))

    # 郭の土留め
    for w in d["terraceWalls"]:
        (au, av), (bu, bv) = w["a"], w["b"]
        if sec["axis"] == "u":
            if au != bu or not (min(av, bv) - 0.7 <= 0 or True):
                pass
            if au == bu:
                continue                      # v=const の壁は u 断面に平行
            if not (min(au, bu) <= at <= max(au, bu)):
                continue
            wp = av
        else:
            if au != bu:
                continue
            if not (min(av, bv) <= at <= max(av, bv)):
                continue
            wp = au
        if not (w0 <= wp <= w1):
            continue
        # ⚠ 壁は「設計高さの矩形」でなく**その位置の地盤まで**描く。天端は面の高さで一定だが
        #   法尻は地形なりに上下するので、露出高は走りに沿って変わる。設計高さ(4s)で描くと
        #   落差の小さい区間で壁が土に埋もれて見える(2026-08-23 ユーザー指摘)。
        hgt, bt = 4.0 * w["s"], 2.4 * w["s"]
        lo2 = -1.0 if gnd_y(max(wp - 1.0, w0)) < gnd_y(min(wp + 1.0, w1)) else 1.0
        foot = gnd_y(min(max(wp + lo2 * 1.0, w0), w1))
        exp = max(0.35, min(hgt, w["coping"] - foot))
        g.append(R(X(wp) - sx * bt / 2 / K, Y(w["coping"]), sx * bt / K, exp * sx * ex,
                   fill=_pat(), stroke="var(--ishi)", sw=1.2))
        g.append(T(X(wp), Y(w["coping"]) - 5, "%s 露出%.1f" % (w["name"], exp), "jo", "middle"))

    # 石段 — 段の縁または法面の上に直に載る(郭内の土留めは全廃した)。
    #   降りる向きの軸に沿って蹴上×踏面のギザギザを描き、開口が切り線に掛かる断面にだけ出す。
    for k in d["kaidans"]:
        ax, at2, ka, kb, cu, cv = kgeom(k)
        if sec["axis"] == "u":
            if ax != "v" or abs(at - at2) > k["w"] / 2 / K:
                continue
            wa, wb = ka, kb
        else:
            if ax != "u" or abs(at - at2) > k["w"] / 2 / K:
                continue
            wa, wb = ka, kb
        if wb <= w0 or wa >= w1:
            continue
        ylo, yhi = gnd_y(wa), gnd_y(wb)
        top, bot = (wb, wa) if yhi >= ylo else (wa, wb)      # top=高いほう
        ytop = max(ylo, yhi)
        sgn = -1.0 if top > bot else 1.0                     # 段が降りる向き
        tread = k["fumi"] / K                                # 踏面(0.45m)。踊り場と混ぜない
        od = k.get("odori", 0); odk = k.get("odoriKen", 0)
        at_odori = set()
        if od:                                               # 踊り場を段の間へ均等に割る
            for j3 in range(1, od + 1):
                at_odori.add(int(round(k["steps"] * j3 / float(od + 1))))
        pts3 = [(top, ytop)]
        for i3 in range(k["steps"]):
            y3 = ytop - (i3 + 1) * k["keri"]
            pts3.append((pts3[-1][0] + sgn * tread, pts3[-1][1]))
            pts3.append((pts3[-1][0], y3))
            if (i3 + 1) in at_odori:                         # 踊り場(水平)
                pts3.append((pts3[-1][0] + sgn * odk, y3))
        g.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="1.8"/>'
                 % " ".join("%.1f,%.1f" % (X(min(max(px3, w0), w1)), Y(py3)) for px3, py3 in pts3))
        g.append(T(X(min(max((wa + wb) / 2, w0 + 3), w1 - 3)), Y(ytop) - 16,
                   "%s %d段(蹴上%.3f・踏面%.2f・踊り場%d箇所×%g間・走り%.2fm)"
                   % (k["name"], k["steps"], k["keri"], k["fumi"], od, odk, k["run"]),
                   "anG", "middle"))
    # 坂(ランプ)— 切り線に掛かる区間を勾配つきの太線で示す
    for rp in d.get("ramps", []):
        pp = rp["pts"]
        for (a4, b4), (c4, e4) in zip(pp, pp[1:]):
            if sec["axis"] == "u":
                if (a4 - at) * (c4 - at) > 0:
                    continue
                t4 = 0.5 if a4 == c4 else (at - a4) / (c4 - a4)
                wq = b4 + (e4 - b4) * t4
            else:
                if (b4 - at) * (e4 - at) > 0:
                    continue
                t4 = 0.5 if b4 == e4 else (at - b4) / (e4 - b4)
                wq = a4 + (c4 - a4) * t4
            if not (w0 <= wq <= w1):
                continue
            g.append(LN(X(wq) - 8, Y(gnd_y(wq)) - 2, X(wq) + 8, Y(gnd_y(wq)) - 2,
                        "var(--nagaya)", 4.0, cap="round"))
            g.append(T(X(wq), Y(gnd_y(wq)) - 8, rp["label"], "anG", "middle"))

    # 棟・付属屋(切り線に掛かるもの)
    eave, ridge = sec["eaveAbove"], sec["ridgeAbove"]
    fl = d["const"]["gotenFloor"]
    for m in d["munes"] + d["service"]:
        if sec["axis"] == "u":
            if not (m["u0"] <= at <= m["u1"]):
                continue
            a, b = m["v0"], m["v1"]
        else:
            if not (m["v0"] <= at <= m["v1"]):
                continue
            a, b = m["u0"], m["u1"]
        if b <= w0 or a >= w1:
            continue                          # 画枠の外(検図 H-2)
        a, b = max(a, w0), min(b, w1)
        # ⛔ **崖下の帯の棟に御殿の床(`gotenFloor`)を足さない**(2026-09-03 庭方 K231) —
        #   `obi.sahou` は「高床にしない」と宣言している。⭕ 床は棟の面 `y` そのもの。
        # ⛔ **軒・棟の高さも御殿の値を当てない**(検図 K250) — `roofs` の宣言から取る。
        rf8 = (d.get("roofs") or {}).get(m.get("roof") or "") or {}
        if m.get("obi"):
            f = m["y"]
            eave8 = rf8.get("eaveH", eave)
            ridge8 = rf8.get("ridgeH", ridge)
        else:
            f = m["y"] + fl
            eave8, ridge8 = eave, ridge
        nm = MUNE_JA.get(m.get("name"), m.get("label", m.get("name", "")))
        if "label" in m and m["name"] not in MUNE_JA:
            nm = m["label"]
        g.append('<polygon points="%s" fill="var(--ink-mid)" stroke="var(--ink)" stroke-width="1.2"/>'
                 % " ".join("%.1f,%.1f" % p for p in
                            [(X(a), Y(f)), (X(a), Y(f + eave8)),
                             ((X(a) + X(b)) / 2, Y(f + ridge8)),
                             (X(b), Y(f + eave8)), (X(b), Y(f))]))
        g.append(T((X(a) + X(b)) / 2, Y(f + eave8) + 12, nm, "rmS", "middle",
                   fit(nm, sx * (b - a) - 4, 10.5)))
    # 御錠口
    for l in d["links"]:
        if l["kind"] == "階段廊下":
            if sec["axis"] == "u" and l["u0"] <= at <= l["u1"]:
                a3, b3 = l["v0"], l["v1"]
            elif sec["axis"] == "v" and l["v0"] <= at <= l["v1"]:
                a3, b3 = l["u0"], l["u1"]
            else:
                continue
            g.append('<polyline points="%s" fill="none" stroke="var(--roka)" stroke-width="3.2"/>'
                     % " ".join("%.1f,%.1f" % (X(a3 + (b3 - a3) * k / 8.0),
                                               Y(l["y"] - l["drop"] + l["drop"] * k / 8.0) - 3)
                                for k in range(9)))
            g.append(T(X((a3 + b3) / 2), Y(l["y"]) - 12,
                       "%s %d段" % (l["name"], l["steps"]), "anG", "middle"))
            continue
        if l["kind"] != "御錠口":
            continue
        if sec["axis"] == "u" and l["u0"] <= at <= l["u1"]:
            c = (l["v0"] + l["v1"]) / 2.0
            g.append(LN(X(c), Y(l["y"]), X(c), Y(l["y"] + ridge + 1.2), "var(--shu)", 1.6, dash="4 3"))
            g.append(T(X(c), Y(l["y"] + ridge + 1.2) - 4, "御錠口", "anG", "middle"))

    # 区画線との交点に立つ囲い — 面割りに合わせた天端と基壇石垣
    Pg = [gr.L(x, z) for x, z in d["polygon"]]
    ng = len(Pg)
    cross = []
    for i in range(ng):
        (au, av), (bu, bv) = Pg[i], Pg[(i + 1) % ng]
        if sec["axis"] == "u":
            p1, p2, q1, q2 = au, bu, av, bv          # 線 u=at、交点は v
        else:
            p1, p2, q1, q2 = av, bv, au, bu          # 線 v=at、交点は u
        if (p1 - at) * (p2 - at) > 0 or p1 == p2:
            continue
        t = (at - p1) / (p2 - p1)
        w = q1 + (q2 - q1) * t
        if w0 <= w <= w1:
            cross.append(w)

    def ground_at(w):
        best, by = 1e9, None
        for a2, b2 in zip(prof, prof[1:]):
            if a2[0] - 1e-6 <= w <= b2[0] + 1e-6 and b2[0] > a2[0]:
                return a2[1] + (b2[1] - a2[1]) * (w - a2[0]) / (b2[0] - a2[0])
        for a2 in prof:
            if abs(a2[0] - w) < best:
                best, by = abs(a2[0] - w), a2[1]
        return by if by is not None else 20.0

    for w in cross:
        wx, wz = (gr.W(at, w) if sec["axis"] == "u" else gr.W(w, at))
        # 最寄りの辺と走り s → run
        Pw = d["polygon"]
        best, be, bs = 1e18, 0, 0.0
        for i in range(len(Pw)):
            a2, b2 = Pw[i], Pw[(i + 1) % len(Pw)]
            dx2, dz2 = b2[0] - a2[0], b2[1] - a2[1]
            L2 = dx2 * dx2 + dz2 * dz2
            tt2 = max(0.0, min(1.0, ((wx - a2[0]) * dx2 + (wz - a2[1]) * dz2) / L2))
            qx, qz = a2[0] + dx2 * tt2, a2[1] + dz2 * tt2
            dd = (wx - qx) ** 2 + (wz - qz) ** 2
            if dd < best:
                best, be, bs = dd, i, tt2 * math.sqrt(L2)
        K9 = d["const"]["ken"]
        run = next((r for r in d["runs"] if r["edge"] == be and r["s0"] - 0.5 <= bs <= r["s1"] + 0.5), None)
        if run is None:
            continue                                  # 門の開口
        hh = (d["const"]["nagayaH"] if run["kind"] == "Nagaya"
              else d["const"]["dobeiH"])
        seat = rseat(run, bs)                         # 天端は一直線(水平 or 一定勾配)
        # ⛔ **基壇の足元は `edgeProfile` から取る**(断面の地盤線からではない)。
        #    同じ壁の露出が「断面の地盤」と「外周の展開」の二つの基準面から出ていて、
        #    27箇所中16箇所が 0.30m 超ずれ、2本は断面上で壁が土に埋もれていた(2026-08-25 検図)。
        gy = seat - _run_exposure(d, run, bs)
        if seat > gy + 0.05:                          # 基壇石垣
            bt9 = 2.4 * run["s"]          # 基壇の底厚(設計値)。固定1.8mで描いていた
            # ⚠ 2026-08-31 再検図: **単位を間へ揃える**(sx は px/間 なのに bt9 は m。門だけ /K していた)。
            #   基準面は run の種別で決まる — 長屋は外面が境界線に載り、練塀は境界線に跨る。
            _off = 0.0 if run["kind"] == "Nagaya" else -sx * bt9 / K9 / 2
            g.append(R(X(w) + _off, Y(seat), sx * bt9 / K9, (seat - gy) * sx * ex,
                       fill=_pat(), stroke="var(--ishi)", sw=1.0))
        # ⚠ 2026-08-31 検図: kind で分ける。長屋は奥行 nagayaD(4.545m)で、練塀の 1.15m ではない。
        #   あわせて中心合わせをやめ、**外面を境界線に合わせて内側へ**取る(半分が区画外に出ていた)。
        wt9 = d["const"]["nagayaD"] if run["kind"] == "Nagaya" else d["const"]["dobeiT"]
        _offw = 0.0 if run["kind"] == "Nagaya" else -sx * wt9 / K9 / 2
        g.append(R(X(w) + _offw, Y(seat + hh), sx * wt9 / K9, hh * sx * ex,
                   fill=KC.get(run["kind"], "var(--dim)"), op=0.95))
        g.append(T(X(w), Y(seat + hh) - 5, "%s 天端%.2f 露出%.2f"
                   % (run["name"], seat, seat - gy), "jo", "middle"))

    # 表門(門の軸の断面のみ)
    if sec["axis"] == "u" and abs(sec["at"]) < 2:
        gpn = d["gate"]["plan"]
        g.append(R(X(0) - sx * gpn["monD"] / 2 / K, Y(d["gate"]["sill"] + gpn["monH"]),
                   sx * gpn["monD"] / K, gpn["monH"] * sx * ex,
                   fill="var(--shu-lo)", stroke="var(--shu)", sw=1.6))
        g.append(T(X(0), Y(d["gate"]["sill"] + gpn["monH"]) - 5, "表門", "anG", "middle"))

    # 端の囲い(polygon との交点に立つ run)
    # 端のラベルは**算出**する。⚠ 2026-08-25 検図: 注記の「→」の連鎖から作っていたので、
    #   連鎖の無い断面では左右に同じ文字列が出ていた。
    e0, e1 = _sec_ends(d, sec)
    g.append(T(4, 15, e0 + " →", "anS"))
    g.append(T(W - 4, 15, "→ " + e1, "anS", "end"))
    # 江戸期地盤のレンジは**この断面の natural から算出**する(注記に書き写さない)
    if nat:
        g.append(T(W - 4, 30, "江戸期地盤 %.2f〜%.2f" % (min(y for _x, y in nat),
                                                        max(y for _x, y in nat)), "anS2", "end"))
    g.append(T(4, H - 34, "水平は間グリッド沿い/垂直は %.1f 倍に強調。屋根は図示のための概略。"
               "視線は %s" % (ex, "南を向く(左=東の道／右=西の奥)" if sec["axis"] == "u"
                              else "西を向く(左=南の樹下境／右=北の土井境)"), "anS2", "start"))
    g.append(T(4, H - 20, "── 実線=造成後の地盤　┄┄ 破線=造成前の地形(**江戸期の復元地盤**・確度U/B)。"
               "その間の**暖色=盛土／寒色=切土**(濃いほど厚い)。"
               "段の外は法面(盛土1:%.1f/切土1:%.1f)で現地形へ摺り付ける"
               % (d["const"].get("batterFill", 1.5), d["const"].get("batterCut", 1.0)),
               "anS2", "start"))
    g.append(T(4, H - 6, "太い緑帯=**無造成**(江戸期の地盤をそのまま使う区間)。"
               "石垣ハッチ=外周の基壇(郭内の土留めは0本)。朱のギザギザ=石段／太い茶=坂", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 外周の展開
def edge_datum_table(d):
    """**共有辺の上で、当家の復元地盤と隣家が読む正本がどれだけ食い違うか。**
    ⚠ 2026-08-25 検図: 図が「共有辺の上では差 0.00m」と断言していたが偽で、
    樹下境で最大 2.81m あった。この断言が「他家へ通知しなくてよい」根拠になっていた。
    当家だけが復元地盤で設計している以上、境の地盤は**必ず**食い違う — 隠さずに表で出す。"""
    try:
        base = json.load(open(os.path.join(DOC, "base_dem.json"), encoding="utf-8"))
    except Exception:
        return ""
    E = _DEM.get(id(d))
    if E is None:
        _dem_at(d, 0, 0); E = _DEM.get(id(d))
    gr = RGrid(d)
    P = d["polygon"]
    n = len(P)
    cx = sum(p[0] for p in P) / n; cz = sum(p[1] for p in P) / n

    def bl(x, z):
        fx = (x - base["x0"]) / float(base["step"]); fz = (z - base["z0"]) / float(base["step"])
        i0, j0 = int(math.floor(fx)), int(math.floor(fz))
        if not (0 <= i0 < base["nx"] - 1 and 0 <= j0 < base["nz"] - 1):
            return None
        tx, tz = fx - i0, fz - j0
        q = [base["h"][j0][i0], base["h"][j0][i0 + 1], base["h"][j0 + 1][i0], base["h"][j0 + 1][i0 + 1]]
        if any(v is None for v in q):
            return None
        return (q[0] * (1 - tx) + q[1] * tx) * (1 - tz) + (q[2] * (1 - tx) + q[3] * tx) * tz

    rows = []
    worst = 0.0
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        nx0, nz0 = -(b[1] - a[1]) / (L or 1), (b[0] - a[0]) / (L or 1)
        if (a[0] + nx0 - cx) ** 2 + (a[1] + nz0 - cz) ** 2 > \
           (a[0] - nx0 - cx) ** 2 + (a[1] - nz0 - cz) ** 2:
            nx0, nz0 = -nx0, -nz0                    # 内向き
        ds = []
        k = 0
        # ⛔ **クリップを外した辺は 1.0m 内側では足りない**(2026-09-03 検図4巡目 K183) —
        #   そこは復元と正本の継ぎ目で、双一次が段を跨ぐ汚染帯の中に入る。
        #   ⭕ 堤の天端と**同じ 2.0間 内側**へ揃える(片方だけ直すと二つの表がまた割れる)。
        inm = 1.0
        if i in set(d["const"].get("edgeInEdges") or []):
            inm = ((d.get("nishi") or {}).get("tsutsumi") or {}).get("sampleInKen", 2.0) \
                * d["const"]["ken"]
        while k <= L:
            t = k / (L or 1)
            x = a[0] + (b[0] - a[0]) * t + nx0 * inm
            z = a[1] + (b[1] - a[1]) * t + nz0 * inm
            u, v = gr.L(x, z)
            e = _dem_at(d, u, v); c = bl(x, z)
            if e is not None and c is not None:
                ds.append(e - c)
            k += 1.0
        if not ds:
            continue
        over = sum(1 for q in ds if abs(q) > 0.3) * 100.0 / len(ds)
        worst = max(worst, max(abs(min(ds)), abs(max(ds))))
        e9 = d["edges"][i] if i < len(d["edges"]) else {}
        rows.append("<tr><td>辺%d</td><td class='note'>%s</td><td>%.1fm</td>"
                    "<td>%+.2f 〜 %+.2f m</td><td>%.0f%%</td></tr>"
                    % (i, e9.get("neighbor", ""), L, min(ds), max(ds), over))
    return ("<h3>共有辺の上の地盤の食い違い(当家の復元地盤 − 正本)</h3>"
            "<p class='cap'>⚠ <b>当家だけが江戸期の復元地盤で設計しており、土井・松平・山王・樹下は"
            "正本(近代造成を含む現代の地面)で設計している。</b>境の内側1.0m で両者を突き合わせた。"
            "<b>最大 %.2fm 食い違う</b> — 塀の天端・基壇・埋没の検査を隣家と突き合わせるときは"
            "<b>必ず基準面を明記する</b>。0.00m の辺は復元が届いていない区間。</p>"
            "<div class='tw'><table><thead><tr><th>辺</th><th class='note'>隣は誰か</th><th>長さ</th>"
            "<th>食い違い</th><th>0.3m 超の割合</th></tr></thead><tbody>%s</tbody></table></div>"
            % (worst, "".join(rows)))


def edges_table(d):
    """**辺の注記を図に出す**。2026-08-24 検図: 13辺ぶんの典拠・隣家の納まりが json に
    しか無く、ユーザーが見る図には一切現れていなかった(§B-5「文章の追記だけで済ませない」)。"""
    gr = RGrid(d)
    P = d["polygon"]
    n = len(P)
    own = {}
    for r in d["runs"]:
        own.setdefault(r["edge"], []).append(r["name"])
    for f in d.get("fences", []):
        own.setdefault(f["edge"], []).append(f["name"] + "(木柵)")
    rows = []
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        e = d["edges"][i] if i < len(d["edges"]) else {}
        pr9 = d.get("edgeProfile", {}).get(str(i)) or []
        gg = ("%.2f〜%.2f" % (min(q[1] for q in pr9), max(q[1] for q in pr9))) if pr9 else "—"
        rows.append("<tr><td>辺%d</td><td>%.1fm</td><td>%s</td><td><code>%s</code></td>"
                    "<td>%s</td><td class='note'>%s</td></tr>"
                    % (i, L, e.get("neighbor", ""),
                       " ".join(own.get(i, [])) or "—(当家は建てない)", gg,
                       inline(e.get("_", ""))))
    return ("<h3>辺と隣地(全%d辺)</h3><div class='tw'><table><thead><tr><th>辺</th><th>長さ</th>"
            "<th>隣は誰か</th><th>当家の囲い</th><th>辺の地盤</th>"
            "<th class='note'>注記・典拠</th>"
            "</tr></thead><tbody>%s</tbody></table></div>"
            "<p class='cap'><b>辺の地盤は <code>edgeProfile</code> から刷る算出値</b>"
            "(江戸期の復元地盤を辺に沿って 4m 刻みで取り直したもの)。"
            "⛔ 注記に手で書き写さない — 地盤を起こし直した瞬間に腐る"
            "(2026-09-02: 辺5 の『8.5〜8.9』が西の起こし直しで取り残されていた)。</p>"
            % (n, "".join(rows)))


def perimeter_dev_svg(d):
    P = d["polygon"]
    n = len(P)
    elen = [math.hypot(P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1]) for i in range(n)]
    tv = [0.0]
    for i in range(n):
        tv.append(tv[-1] + elen[i])
    total = tv[-1]
    # 展開の起点=P5(松平境の始まり)。当家が建てない辺(5〜7)を図の左端へ寄せ、
    # 当家所有の10辺(辺8→…→辺4)を一続きに読ませる。
    t0 = tv[5]

    def tt(e, s):
        return (tv[e] + s - t0) % total

    W, ex = 1120.0, 6.5
    HEAD, FOOT = 34.0, 70.0
    sx = W / total
    dob = d["const"]["dobeiH"]
    nagH = d["const"]["nagayaH"]
    seats = [y for r in d["runs"] for y in (rseat(r, r["s0"]), rseat(r, r["s1"]))]
    gmin = min([y for prof2 in d.get("edgeProfile", {}).values() for _s2, y in prof2] + seats)
    y1 = max(seats) + nagH + 1.0
    y0 = gmin - 2.0
    H = (y1 - y0) * sx * ex + HEAD + FOOT

    def X(t): return t * sx
    def Y(y): return HEAD + (y1 - y) * sx * ex

    g = _sv(W, H, "外周の展開図")
    lab = []
    # 地盤の補間(edgeProfile)
    profs = {int(e): p for e, p in d.get("edgeProfile", {}).items()}

    def gnd(e, s):
        p = profs.get(e)
        if not p:
            return None
        if s <= p[0][0]:
            return p[0][1]
        for (sa2, ya2), (sb2, yb2) in zip(p, p[1:]):
            if sa2 <= s <= sb2:
                return ya2 + (yb2 - ya2) * (s - sa2) / (sb2 - sa2)
        return p[-1][1]

    # 隣家が自分の側に建てている基壇石垣(土井)を破線で重ねる — 天端の突き合わせのため
    for pl in neighbor_plinth(d):
        ta = tt(pl["edge"], pl["s0"]); tb = tt(pl["edge"], pl["s1"])
        if tb < ta:
            tb += total
        g.append(R(X(ta), Y(pl["coping"]), X(tb) - X(ta), pl["h"] * sx * ex,
                   fill="none", stroke="var(--ishi)", sw=1.4, dash="6 4"))
        g.append(T((X(ta) + X(tb)) / 2, Y(pl["coping"]) - 4,
                   "隣家(土井)の基壇 天端 %.2f・壁高 %.2f" % (pl["coping"], pl["h"]),
                   "anS2", "middle"))

    for r in sorted(d["runs"], key=lambda r: tt(r["edge"], r["s0"])):
        ta = tt(r["edge"], r["s0"]); tb = tt(r["edge"], r["s1"])
        if tb < ta:
            tb += total
        xa, xb = X(ta), X(tb)
        h = nagH if r["kind"] == "Nagaya" else dob
        # 基壇石垣 — 天端(seat)から地盤線まで(浮かせない)
        if r.get("base"):
            base_pts = [(r["s0"], gnd(r["edge"], r["s0"]))]
            for s2, y2 in profs.get(r["edge"], []):
                if r["s0"] < s2 < r["s1"]:
                    base_pts.append((s2, y2))
            base_pts.append((r["s1"], gnd(r["edge"], r["s1"])))
            base_pts = [q for q in base_pts if q[1] is not None and q[1] < rseat(r, q[0])]
            if base_pts:
                poly = [(xa, Y(rseat(r, r["s0"]))), (xb, Y(rseat(r, r["s1"])))] + \
                       [(X(tt(r["edge"], s2)), Y(y2)) for s2, y2 in reversed(base_pts)]
                g.append('<polygon points="%s" fill="%s" stroke="var(--ishi)" stroke-width="0.9" opacity="0.9"/>'
                         % (" ".join("%.1f,%.1f" % q for q in poly), _pat()))
        y_a, y_b = rseat(r, r["s0"]), rseat(r, r["s1"])
        g.append('<polygon points="%s" fill="%s" opacity="0.9"/>'
                 % (" ".join("%.1f,%.1f" % q for q in
                             [(xa, Y(y_a)), (xb, Y(y_b)), (xb, Y(y_b + h)), (xa, Y(y_a + h))]),
                    KC.get(r["kind"], "var(--dim)")))
        if r.get("nijukai"):
            g.append(R(xa, Y(r["seat"] + nagH + 2.6), 20 * 1.818 * sx, 2.6 * sx * ex,
                       fill=KC["Nagaya"], op=0.65))
            lab.append((xa, "門翼二階(海鼠壁)"))
        ym = (y_a + y_b) / 2.0
        g.append(T((xa + xb) / 2, Y(ym) + 11,
                   ("%.2f" % y_a) if abs(y_a - y_b) < 0.02 else ("%.2f→%.2f" % (y_a, y_b)),
                   "jo", "middle"))
        g.append(T((xa + xb) / 2, Y(ym + h) - 3, r["name"], "jo", "middle",
                   fit(r["name"], xb - xa, 9.0)))
    # ⭕ 2026-09-01 六巡目: **木柵(fences)を展開図に描く。** 従前は `runs` しか回しておらず、
    #   辺5(溜池の堤)の木柵 80.6m = 外周の 10.1% が**図に一度も現れなかった**。
    #   木柵は基礎も石垣も持たず地形なりなので、天端は取らず**地盤線に沿う帯**で描く。
    fnH = d["const"]["fenceH"]
    for f9 in d.get("fences", []):
        ta = tt(f9["edge"], f9["s0"]); tb = tt(f9["edge"], f9["s1"])
        if tb < ta:
            tb += total
        pts9 = [(f9["s0"], gnd(f9["edge"], f9["s0"]))]
        for s2, y2 in profs.get(f9["edge"], []):
            if f9["s0"] < s2 < f9["s1"]:
                pts9.append((s2, y2))
        pts9.append((f9["s1"], gnd(f9["edge"], f9["s1"])))
        pts9 = [q for q in pts9 if q[1] is not None]
        if not pts9:
            continue
        low = [(X(tt(f9["edge"], s2)), Y(y2)) for s2, y2 in pts9]
        up = [(xx, Y(y2 + fnH)) for (xx, _yy), (_s2, y2) in zip(low, pts9)]
        g.append('<polygon points="%s" fill="%s" opacity="0.75"/>'
                 % (" ".join("%.1f,%.1f" % q for q in low + list(reversed(up))),
                    KC.get("Fence", "var(--dim)")))
        # 柵らしく縦の桟を入れる(帯だけだと練塀と見分けが付かない)
        k9 = max(2, int((tb - ta) / 1.8))
        for i9 in range(k9 + 1):
            t9 = ta + (tb - ta) * i9 / float(k9)
            gy9 = gnd(f9["edge"], f9["s0"] + (f9["s1"] - f9["s0"]) * i9 / float(k9))
            if gy9 is None:
                continue
            g.append(LN(X(t9), Y(gy9), X(t9), Y(gy9 + fnH), "var(--ink)", 0.7, op=0.7))
        ym9 = sum(y2 for _s2, y2 in pts9) / len(pts9)
        # 起点(P5)に接する柵は図の左端に来るので、中央寄せだとラベルが枠外へ出て切れる
        xm9 = (X(ta) + X(tb)) / 2
        an9 = "start" if xm9 < W * 0.2 else ("end" if xm9 > W * 0.8 else "middle")
        g.append(T(4.0 if an9 == "start" else (W - 4.0 if an9 == "end" else xm9),
                   Y(ym9 + fnH) - 4,
                   "%s(%s h%.2f・地形なり=基礎も石垣も持たない)" % (f9["name"], f9["kind"], fnH),
                   "jo", an9))
    # 地盤線(境界プロファイル・実測) — 基壇の露出が図に出るように
    for e, prof2 in sorted(d.get("edgeProfile", {}).items()):
        for (sa, ya), (sb, yb) in zip(prof2, prof2[1:]):
            ta2, tb2 = tt(int(e), sa), tt(int(e), sb)
            if tb2 < ta2:
                tb2 += total
            g.append(LN(X(ta2), Y(ya), X(tb2), Y(yb), "var(--ink)", 1.3, dash="6 3", op=0.8))
    # 門・櫓
    gates_list = [("表門", d["gate"]["edge"], d["gate"]["s"], d["gate"]["plan"]["monW"])]
    if d.get("onarimon"):
        gates_list.append(("御成門", d["onarimon"]["edge"], d["onarimon"]["s"], d["onarimon"]["w"]))
    gates_list += [("木戸", k["edge"], k["s"], k["w"]) for k in d["komon"]]
    for name, e, s, wd in gates_list:
        t = tt(e, s)
        g.append(LN(X(t), Y(y1 - 0.5), X(t), Y(y0), "var(--shu)", 1.2, dash="5 3"))
        g.append(T(X(t), HEAD - 6, name, "sr", "middle"))
    for y in d["yagura"]:
        t = tt(y["vertex"], 0.0)
        g.append(R(X(t) - 5, Y(y["seat"] + 7.5), 10, 7.5 * sx * ex, fill="var(--shu)", op=0.85))
        g.append(T(X(t), Y(y["seat"] + 7.5) - 4, "隅櫓", "jo", "middle"))
    # 当家が建てない辺のラベル — **runs / edges から作る**(辺番号を手で書かない)
    have = set(r["edge"] for r in d["runs"]) | set(f["edge"] for f in d.get("fences", []))
    blank = [e for e in range(n) if e not in have]
    for e in blank:
        ta2 = (tv[e] - t0) % total; tb2 = (tv[e + 1] - t0) % total
        if tb2 <= ta2:
            tb2 += total
        g.append(T(X((ta2 + tb2) / 2), Y((y0 + y1) / 2),
                   "辺%d %s — 当家は建てない" % (e, d["edges"][e].get("neighbor", "")),
                   "anS2", "middle"))
    # 頂点の目盛
    for i in range(n):
        t = (tv[i] - t0) % total
        g.append(LN(X(t), Y(y0), X(t), Y(y0) + 5, "var(--dim)", 0.8))
        g.append(T(X(t), Y(y0) + 15, "P%d" % i, "jo", "middle"))
    g.append(T(4, H - 22, "展開の起点=P5(松平境の始まり)— 当家が建てない辺を左端に寄せ、当家の10辺を一続きに読む。"
               "天端は run ごとに一直線(面の縁=水平／斜面=一定勾配)、段は継ぎ目でだけ落とす。長屋 桁高 %.1fm/練塀 %.2fm。"
               "破線=区画線上の地盤(**江戸期の復元地盤**・確度U/B。街路の値だけ現況P)/石垣ハッチ=基壇"
               % (nagH, dob), "anS2", "start"))
    g.append(T(4, H - 8, "東辺(三べ坂)の道は南へ落ちるので、練塀の基壇石垣が道へ露出する(台地肩)。"
               "隅の天端差は高い側の基壇小口(隅石)で受ける — 詳細は「取り合い」の隅の表", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 表門まわり
def gate_svg(d):
    """長屋門の正面見付(概略)。躯体の中央に門口、両側に番所(呼称は json `gate.plan.bansho.kind`
    から引く — 2026-08-24 考証: 図だけ「出格子番所」= 1〜5万石の小大名格の呼称になっていた)、
    両袖は練塀へ突き付ける。"""
    gp = d["gate"]["plan"]
    monW, monH, monD = gp["monW"], gp["monH"], gp["monD"]
    wing = 12.0
    total = monW + 2 * wing
    W = 980.0
    sx = W / total
    GY = 260.0
    H = 340.0

    def X(m): return m * sx
    def Y(m): return GY - m * sx

    g = _sv(W, H, "表門(長屋門)正面見付")
    # ⚠ 2026-08-31 四巡目: 両袖を**練塀**として高さ 4.3m の直書きで描いていた。
    #   辺12 は 2026-08-31 のユーザー裁定で**表長屋**になっており、見付だけが旧設計のままだった
    #   (同じ図版の下の平面図は「両袖は表長屋へ継ぐ」と直っていて、上下で食い違っていた)。
    #   ⛔ 高さも門口も直書きだったので、すべて設計値から引く。
    nagH9 = d["const"]["nagayaH"]
    seatN = next(r["seat"] for r in d["runs"] if r["kind"] == "Nagaya")
    dh9 = seatN - d["gate"]["sill"]                   # 長屋の座は門の敷居より高い(段差)
    monkuchi = gp.get("monkuchi", 2.0 * d["const"]["ken"])   # 門口=2間
    # 2026-09-01 六巡目: 見付図を**辺の実際の走り s へ紐づける**。
    #   ⛔ 図の +x を「s の増える向き」と決め打ちしない — 岡部は s = 14.37 − 1.818·u で
    #   走りとグリッドが**逆向き**(EDO-0079・`sashizu_lib.s_sign`)。図の +x は
    #   **他の平面図と同じ +u** に揃え、s は `s_sign` から引く。
    #   従前は両袖を一律 12m の箱で描いており、南袖は実長より図が長かった。
    ge = d["gate"]["edge"]; gs = d["gate"]["s"]
    sgn = sashizu_lib.s_sign(d)

    def S(x):
        return gs + sgn * (x - (wing + monW / 2.0))

    nag12 = [r for r in d["runs"] if r["edge"] == ge and r["kind"] == "Nagaya"]
    sL, sR = S(wing), S(wing + monW)          # 躯体の左端・右端の走り
    rL = next((r for r in nag12 if min(abs(r["s0"] - sL), abs(r["s1"] - sL)) < 0.05), None)
    rR = next((r for r in nag12 if min(abs(r["s0"] - sR), abs(r["s1"] - sR)) < 0.05), None)
    if not (rL and rR):
        print("⚠ 表門の見付: 辺%d の両袖の run が躯体の端に付かない — 図の向きを検算できない" % ge)
    wings = []
    if rL:
        wings.append((rL, max(0.0, wing - (rL["s1"] - rL["s0"])), wing))
    if rR:
        wings.append((rR, total - wing, min(total, total - wing + (rR["s1"] - rR["s0"]))))
    for r9, xa, xb in wings:
        g.append(R(X(xa), Y(dh9 + nagH9), X(xb - xa), nagH9 * sx, fill="var(--nagaya)", op=0.55))
        g.append(R(X(xa) - 3, Y(dh9 + nagH9) - 9, X(xb - xa) + 6, 9, fill="var(--ink-lo)"))
        # ラベルは画枠に収める(袖は図の外まで続くので、中央寄せだと左へはみ出して切れる)
        xm9 = min(max(X((xa + xb) / 2), 4.0), W - 4.0)
        an9 = "start" if xm9 < W * 0.25 else ("end" if xm9 > W * 0.75 else "middle")
        g.append(T(4.0 if an9 == "start" else (W - 4.0 if an9 == "end" else xm9),
                   Y(dh9 + nagH9 + 0.6),
                   "%s(二階瓦葺窓付・棟高%.2f / 座は門の敷居より%.2f高い)" % (r9["name"], nagH9, dh9),
                   "anS2", an9))
    # 長屋門の躯体
    g.append(R(X(wing), Y(monH), X(monW), monH * sx, fill="var(--nagaya)", op=0.85))
    g.append(R(X(wing) - 4, Y(monH) - 12, X(monW) + 8, 12, fill="var(--ink-lo)"))
    # 門口(中央)
    g.append(R(X(wing + monW / 2 - monkuchi / 2), Y(3.2), X(monkuchi), 3.2 * sx,
               fill="var(--paper2)", stroke="var(--ink)", sw=1.2))
    g.append(R(X(wing + monW / 2 - monkuchi / 2 + 0.1), Y(3.0), X(monkuchi / 2 - 0.15), 3.0 * sx,
               fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
    g.append(R(X(wing + monW / 2 + 0.05), Y(3.0), X(monkuchi / 2 - 0.15), 3.0 * sx,
               fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
    g.append(T(X(wing + monW / 2), Y(3.4), "門口(内開き・潜り戸)", "anS2", "middle"))
    # 番所 — ⚠ 2026-08-31 五巡目まで幅3.2m・躯体の22%/78%位置・高さ1.9 が直書きで、
    #   設計(桁行9間 = 門戸6間 + **両端の**番所 各1.5間)と一致していなかった(規則4違反)。
    #   ⭕ 幅は `bansho.w`、位置は**両端**、高さは `bansho.h` から引く。
    bs = d["gate"]["plan"].get("bansho", {})
    bw = bs.get("w", 2.7); bh = bs.get("h", 1.9)
    for x0b in (wing, wing + monW - bw):
        g.append(R(X(x0b), Y(bh + 0.5), X(bw), bh * sx, fill="var(--dan)", stroke="var(--ink)", sw=1.0))
        k9 = max(2, int(bw / 0.36))
        for i in range(k9):
            xx = X(x0b + 0.2 + i * (bw - 0.4) / max(k9 - 1, 1))
            g.append(LN(xx, Y(bh + 0.4), xx, Y(0.7), "var(--ink)", 0.8, op=0.75))
    bnm = bs.get("kind", "番所")
    g.append(T(X(wing + bw / 2), Y(bh + 0.9), bnm, "anS2", "middle"))
    g.append(T(X(wing + monW - bw / 2), Y(bh + 0.9), bnm, "anS2", "middle"))
    # ⭕ 2026-08-31 五巡目: 袖の表長屋が地盤線の 1.05m 上に浮いて見えていた。受けている
    #    石垣基壇(辺12・s=1.0 → 底厚 2.4m)と門前面の地盤線を描く。断面は要らない —
    #    段差は壁の走り方向に起きるので、辺に直交する横断面には原理的に出ない。
    # 2026-09-01 六巡目まで、基壇を **dh9(=座−敷居 1.05m)の一定の丈**で描いていた。
    #   dh9 は「門の敷居と門前面の段差」であって**基壇の露出ではない**。露出は
    #   `座 − 辺の外側の地盤` で、地盤は走りに沿って上下する。edgeProfile を 0.25m 刻みで
    #   拾い、地盤線と基壇を実形で描く(数値は図に写さず毎回算出する)。
    expo = []
    for r9, xa, xb in wings:
        pts_g, x9 = [], xa
        while x9 <= xb + 1e-9:
            gy9 = _prof_y(d, ge, S(x9))
            if gy9 is None:
                gy9 = d["gate"]["sill"]
            expo.append(seatN - gy9)
            pts_g.append((X(x9), Y(gy9 - d["gate"]["sill"])))
            x9 += 0.25
        poly = (["%.1f,%.1f" % (X(xa), Y(dh9))]
                + ["%.1f,%.1f" % (xx, yy) for xx, yy in pts_g]
                + ["%.1f,%.1f" % (X(xb), Y(dh9))])
        g.append('<polygon points="%s" fill="%s" stroke="var(--ishi)" stroke-width="0.8"/>'
                 % (" ".join(poly), _pat()))
        g.append(LN(X(xa), Y(dh9), X(xb), Y(dh9), "var(--ink)", 1.2))
        g.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.2"/>'
                 % " ".join("%.1f,%.1f" % (xx, yy) for xx, yy in pts_g))
    if expo:
        g.append(T(X(wings[0][1]) + 3, Y(dh9) + 12,
                   "門前面 %.2f — 受ける石垣基壇の露出は図示の範囲で %.2f〜%.2fm"
                   "(座 − 辺%d の外側の地盤。走りに沿って変わる)"
                   % (seatN, min(expo), max(expo), ge), "anS2", "start"))
    g.append(LN(0, GY, W, GY, "var(--ink)", 1.6))
    g.append(T(4, GY + 16,
               "三べ坂前身の南北道。**門の敷居 %.2f = 道なり** — 門前面(座 %.2f)はこれより %.2fm 高く、"
               "袖の表長屋はその段の上に載る" % (d["gate"]["sill"], seatN, seatN - d["gate"]["sill"]),
               "anS2", "start"))
    g.append(T(4, 15, "正面見付(概略・等倍)。型式=現存実例2件[山脇]A・[西澄寺]A ＋ 格式階梯B/表門は安政地震で無別条=当屋敷を名指す一次記録(S)", "anS"))
    _dm = (d["gate"]["sill"] + monH) - (seatN + nagH9)
    g.append(T(4, 29, "門の棟 %.2f(敷居%.2f+%.2f)／袖の表長屋の棟 %.2f(座%.2f+%.2f) — %s。"
               "門は街路に、袖は門前面の段に載るので %.2fm の段差がある"
               % (d["gate"]["sill"] + monH, d["gate"]["sill"], monH, seatN + nagH9, seatN, nagH9,
                  ("**門が %.2fm 高い**(長屋門は両袖より高いのが型)" % _dm) if _dm > 0.01
                  else "⚠ **袖のほうが %.2fm 高い — 格式が逆転している。要裁定**" % (-_dm),
                  seatN - d["gate"]["sill"]), "anS"))
    g.append("</svg>")

    # 平面
    W2, H2 = 980.0, 200.0
    s2 = W2 / total
    wy = 100.0
    g2 = _sv(W2, H2, "表門(長屋門)平面")

    def X2(m): return m * s2
    # 2026-09-01 六巡目まで、平面の番所を **躯体の 22%/78% の位置**へ直書きしており、
    #   見付図(両端・幅 bansho.w)と **2.25m ずれていた**。同じ設計値から両図を引く。
    #   奥行も 16px/20px の直書きだったので、梁間 monD・長屋の奥行 nagayaD で引き直す。
    nagD2 = d["const"]["nagayaD"]; K9 = d["const"]["ken"]
    for r9, xa, xb in wings:
        g2.append(R(X2(xa), wy - X2(nagD2) / 2, X2(xb - xa), X2(nagD2),
                    fill="var(--nagaya)", op=0.85))
    g2.append(R(X2(wing), wy - X2(monD) / 2, X2(monW), X2(monD),
                fill="var(--nagaya)", stroke="var(--ink)", sw=1.2))
    for x0b in (wing, wing + monW - bw):
        g2.append(R(X2(x0b), wy - X2(monD) / 2, X2(bw), X2(monD),
                    fill="var(--dan)", stroke="var(--ink)", sw=1.0))
        g2.append(T(X2(x0b + bw / 2), wy + 2, bnm, "anS2", "middle"))
    g2.append(R(X2(wing + monW / 2 - monkuchi / 2), wy - X2(monD) / 2, X2(monkuchi), X2(monD),
                fill="var(--paper2)", stroke="var(--ink)", sw=1.0))
    g2.append(T(X2(wing + monW / 2), wy - X2(monD) / 2 - 6, "門口 %.3fm" % monkuchi, "anS2", "middle"))
    g2.append(T(4, H2 - 8,
                "長屋門の躯体(桁行%.3fm=%.1f間 × 梁間%.3fm=%.1f間)の**両端 各%.3fm(%.1f間)が番所**(躯体内)。"
                "残る%.3fm(%.1f間)が門戸で、その中央に門口%.3fm(%.1f間)。両袖は**表長屋**(奥行%.3fm)へ継ぐ"
                % (monW, monW / K9, monD, monD / K9, bw, bw / K9,
                   monW - 2 * bw, (monW - 2 * bw) / K9, monkuchi, monkuchi / K9, nagD2),
                "anS2", "start"))
    g2.append("</svg>")
    return "\n".join(g) + "\n" + "\n".join(g2)


# ---------------------------------------------------------------- 表


def planes_table(d):
    # ⚠ 確度の列を必ず出す — 面の高さは指図で最も重い設計値なのに、
    #   cert が図に出ていなかった(2026-08-24 考証)。
    """面(planes)と縁の囲いの対応。造成も囲いもこの表から決まる。"""
    rows = []
    for p in d.get("planes", []):
        chip = ('<span style="display:inline-block;width:11px;height:11px;background:%s;'
                'border:1px solid var(--rule);margin-right:6px"></span>' % PLANE_COL.get(p["name"], "transparent")) \
               if p["name"] in PLANE_COL else ""
        rows.append("<tr><td>%s%s</td><td>%s</td><td class='note'>%s</td><td class='note'>%s</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (chip, p["name"], ("%.1f m" % p["y"]) if p["y"] is not None else "地形なり",
                       "・".join(TERR_JA.get(t, t) for t in p["terraces"]) or "—",
                       "・".join("<code>%s</code>" % r for r in p["runs"]),
                       inline(_cert(d, p)), inline(p.get("note", ""))))
    return ("<h3>面と縁の対応</h3><div class='tw'><table><thead><tr><th>面</th><th>高さ</th>"
            "<th class='note'>段(造成)</th><th class='note'>縁の囲い(天端=面の高さ)</th>"
            "<th class='note'>確度(高さの根拠)</th><th class='note'>注記</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def munes_table(d):
    rows = []
    K = d["const"]["ken"]
    for m in d["munes"]:
        kw, kd = abs(m["u1"] - m["u0"]), abs(m["v1"] - m["v0"])
        area = kw * kd * K * K
        tat = sum(tatami(r) for r in m["rooms"])
        rows.append("<tr><td>%s</td><td><code>%s</code></td><td>%s</td><td>%d×%d間</td>"
                    "<td>%.0f m²</td><td>%d</td><td>%d</td></tr>"
                    % (MUNE_JA.get(m["name"], m["name"]), m["name"], m["zone"], kw, kd,
                       area, len(m["rooms"]), tat))
    return ('<div class="tw"><table><thead><tr><th>棟</th><th>名</th><th>ゾーン</th><th>外形</th>'
            "<th>面積</th><th>室数</th><th>畳数計</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def runs_table(d):
    rows = []
    for r in d["runs"]:
        y0r, y1r = rseat(r, r["s0"]), rseat(r, r["s1"])
        rows.append("<tr><td><code>%s</code></td><td>辺%d</td><td>%.0f–%.0f</td><td>%.1fm</td>"
                    "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (r["name"], r["edge"], r["s0"], r["s1"], r["s1"] - r["s0"],
                       "表長屋" if r["kind"] == "Nagaya" else "練塀",
                       ("%.2f" % y0r) if abs(y0r - y1r) < 0.02 else ("%.2f → %.2f" % (y0r, y1r)),
                       ("%.2f–%.2f" % run_base(d, r))
                       if r.get("base") else "—",
                       r.get("on", "—"), cert_sig(d, r)))
    # ⚠ 2026-08-31 五巡目: 確度の欄に約400字の同じ文を22行ぶん刷っており、表として読めなかった。
    #   ⭕ 欄は記号だけにし、本文は種別ごとに1つの脚注へ畳む。
    # 種別ごとに1つの脚注へ畳む。⛔ `next(...)` で1本目だけを読む形へ戻さない —
    #   本文が run ごとに違えば黙って落ちる。**その種別が実際に持つ本文をすべて**出す。
    notes = []
    for kind9, lab9 in (("Nagaya", "表長屋"), ("Dobei", "練塀")):
        seen9 = []
        for r in d["runs"]:
            if r["kind"] != kind9:
                continue
            c9 = _cert(d, r)
            if c9 and c9 not in seen9:
                seen9.append(c9)
        for i9, c9 in enumerate(seen9):
            notes.append("<p class='cap'><b>%s の確度%s</b> — %s</p>"
                         % (lab9, ("(%d)" % (i9 + 1)) if len(seen9) > 1 else "", inline(c9)))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>辺</th><th>走り s</th><th>長さ</th>'
            "<th>種別</th><th>天端 seat</th><th>基壇の露出</th><th>何の縁か</th>"
            "<th>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>" + "".join(notes))


def walls_table(d):
    rows = []
    for w in d["terraceWalls"]:
        dr = w.get("drop") or [0.0, 0.0]
        rows.append("<tr><td><code>%s</code><br><span class='note'>%s</span></td>"
                    "<td>%s<br><span class='note'>延長 %.1fm・%d 折れ点</span></td>"
                    "<td><b>%.2f</b></td><td>%.2f</td>"
                    "<td>%.2f / %.2f / %.2f</td><td>%.2f〜%.2f</td></tr>"
                    % (w["name"], w.get("label", ""),
                       _ptrunc([(a, b) for a, b in (w.get("pts") or [w["a"], w["b"]])]),
                       w.get("len", 0.0), len(w.get("pts") or []),
                       w["coping"], w["s"], 4.0 * w["s"], 1.4 * w["s"], 2.4 * w["s"],
                       dr[0], dr[1]))
    if not rows:
        rows = ["<tr><td colspan='6' class='note'>— <b>郭内に土留めは無い。</b>"
                "⭕ <b>ただし理由が及ぶのは西の法尻だけ</b> — そこは江戸期の斜面が自力で着地する"
                "(盛土の法面より地山が急で、法面は到達距離の中で現地形に着く。"
                "<code>batter_check</code> が毎回検める)。⛔ 置かない理由は方針ではなく<b>地形</b>。"
                "<br>⚠ <b>他の縁は同じ理由では説明できない</b> — 法肩の竹垣が受け持つ縁のうち"
                "<b>落差2m超が %d 本(最大 %.2fm・%s)</b>あり、高さ %.1fm の四つ目垣だけで受けている。"
                "⛔ <b>これは片付いていない宿題</b>で、`_pending` の"
                "「法肩の落差で土留めの要否を検め直す」が持つ(値は上の縁の実測表から刷る)。"
                "<br>⚠ <b>2026-09-02 ユーザー裁定『西の法尻に土留めを1本入れる(案A)』は前提が消えて失効した</b> — "
                "西の地盤を明治16年図から起こし直したところ、天端が全区間で地盤より下になった。"
                "⛔ この一行を消さない(消すと同じ壁がまた建つ)。"
                "⛔ 行が無いことと表が無いことは別 — 空でも表を刷る。</td></tr>"
                % _rail_drops(d)]
    return ('<div class="tw"><table><thead><tr><th>土留め</th><th>線(グリッド)</th>'
            "<th>天端</th><th>s</th><th>壁高/天端幅/底厚</th><th>露出(実測)</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _rail_drops(d):
    """**法肩の竹垣が受ける落差**(2m超の本数・最大値・その箇所・垣の高さ)。

    ⛔ 本文に数を写さない — ここが唯一の出どころ(2026-09-02 検図 K101/K102)。"""
    rs = auto_rails(d)
    ds = []
    for r9 in rs:
        dr = r9.get("drop")
        if dr is None:
            continue
        ds.append((dr, r9.get("name", "")))
    over = [q for q in ds if q[0] > 2.0]
    mx = max(ds)[0] if ds else 0.0
    where = max(ds)[1] if ds else "—"
    hh = d["const"]["takegakiH"]
    return (len(over), mx, where, hh)


def kenpei(d, area):
    """正典は sashizu_lib.kenpei。行ラベル(付属屋の顔ぶれ)だけが当邸の値。"""
    return sashizu_lib.kenpei(
        d, area, TSUBO,
        svc_label="付属屋(厩・供待・蔵・家臣長屋・中間足軽長屋)",
        nagaya_label="外周の長屋(run の kind=Nagaya)",
        ban_label="番所・門の躯体")


_OWNE = {}


def _near_own_edge(d, u, v, lim=1.5):
    """当家が囲いを建てる辺から lim 間以内か。そこの段差は石垣基壇が受ける。"""
    key = id(d)
    if key not in _OWNE:
        gr = RGrid(d)
        P = [gr.L(x, z) for x, z in d["polygon"]]
        own = sorted(set(r["edge"] for r in d["runs"]) | set(f["edge"] for f in d.get("fences", [])))
        _OWNE[key] = [(P[e], P[(e + 1) % len(P)]) for e in own]
    for a, b in _OWNE[key]:
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((u - a[0]) * dx + (v - a[1]) * dz) / L2))
        if math.hypot(u - (a[0] + dx * t), v - (a[1] + dz * t)) <= lim:
            return True
    return False


_CLF = {}


def cliff_metrics(d):
    """**西の崖と、その下の帯の実測。**⛔ 「最急◯%」「標高◯」「幅約◯m」を文章に手で書かない
    (規則4)— ここが**江戸期の復元地盤**から毎回算出する。
    ⚠ これらは 2026-09-02 まで**現代の地面**の値だった(復元が屋敷の平場 v≦108 で止まっており、
      崖の 99.0%・岸の帯の 100% が現況と同一だった)。崖と帯の境 `v1` は復元の仕様が持つ。"""
    key = id(d)
    if key in _CLF:
        return _CLF[key]
    K = d["const"]["ken"]
    py = max(t["y"] for t in d["terraces"])
    try:
        rc = json.load(open(os.path.join(DOC, "okabe_edo_recon.json"), encoding="utf-8"))
        v1 = rc["westCliff"]["v1"]; drop = rc["westCliff"]["drop"]
    except Exception:
        v1, drop = 134.0, 0.5
    steep = 0.0; band = []; hig = []; wid = []
    for i9 in range(-34, 22):
        u = float(i9)
        vh = None; prev = None; v = 100.0; last = None
        while v < 200.0:
            ok = in_parcel(d, u, v)
            y = _dem_at(d, u, v) if ok else None
            if ok:
                last = v
            if y is not None:
                if vh is None and y < py - drop:
                    vh = v
                if vh is not None and v <= v1 and prev is not None:
                    steep = max(steep, abs(y - prev) / (0.5 * K))   # 崖の区間だけで測る
                if v >= v1:
                    band.append(y)
                prev = y
            v += 0.5
        if vh is not None and vh < v1:
            hig.append(vh)
        if last is not None and last > v1:
            wid.append((last - v1) * K)
    _CLF[key] = {"steepPct": 100.0 * steep,
                 "bandMin": min(band) if band else None,
                 "bandMax": max(band) if band else None,
                 "bandCells": len(band),
                 "higV": (min(hig), max(hig)) if hig else None,
                 "v1": v1,
                 "widthM": (sum(wid) / len(wid)) if wid else None,
                 "dropM": (py - (sum(band) / len(band))) if band else None}
    return _CLF[key]


def _near_wall(d, u, v, lim=1.5):
    """郭の土留めの線から `lim` 間以内か。壁が垂直に受ける区間は法面の検査の対象外。"""
    for w in d.get("terraceWalls", []):
        pts = w.get("pts") or []
        for a9, b9 in zip(pts, pts[1:]):
            du, dv = b9[0] - a9[0], b9[1] - a9[1]
            L2 = du * du + dv * dv or 1e-12
            t9 = max(0.0, min(1.0, ((u - a9[0]) * du + (v - a9[1]) * dv) / L2))
            if math.hypot(u - (a9[0] + du * t9), v - (a9[1] + dv * t9)) <= lim:
                return True
    return False


def batter_check(d, ter):
    """法面の検査 — **造成が自然勾配より急にした所で、切土 1:bc を超えていないか**。
    2026-08-23 の旧式(着地判定なし)は地山が急なとき着地せず、cap で切れて法尻に
    垂直の段差を生んだ(55箇所・最大1.58m)。造成モデルは 2026-08-26 に土井式
    (一定勾配+着地判定)へ統一 — この検査はモデルに依らず造成面そのものを見張る。"""
    K = d["const"]["ken"]; bc = d["const"]["batterCut"]
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    Z = {}
    for iv in range(ter["nv"]):
        for iu in range(ter["nu"]):
            n = ter["h"][iv][iu]
            if n is None:
                continue
            u, v = ter["u0"] + iu, ter["v0"] + iv
            Z[(u, v)] = (graded_y(d, u, v, n, we), n)
    bad = []
    for (u, v), (a, b) in Z.items():
        if design_y(d, u, v) is not None:
            continue
        for du, dv in ((1, 0), (0, 1)):
            q = (u + du, v + dv)
            if q not in Z:
                continue
            a2, b2 = Z[q]
            dg = abs(a2 - a) / K; dn = abs(b2 - b) / K
            # **地山がすでに法面の勾配を超えている所は崖**で、この検査の対象外
            # (どんな薄い土工も 1:1 を超えるため。判定するのは「法面が可能だった所を
            #  造成が急にしてしまった」場合だけ)
            if dn > 1.0 / bc + 1e-9:
                continue
            if dg > dn + 1e-9 and dg > 1.0 / bc + 1e-9:
                # **囲いのある辺から 1.5間以内は石垣基壇が受ける**ので法面の対象外。
                # (DEM が区画線でクリップ済みなので in_parcel 判定では発火しない・2026-08-24 検図)
                if _near_own_edge(d, u, v) or _near_own_edge(d, q[0], q[1]):
                    continue
                # **郭の土留めが受ける区間**も対象外 — そこは壁が垂直に受けるのが設計。
                # ⚠ 外周の基壇と同じ扱い(2026-09-02 ユーザー裁定=案A で西の法尻に1本立てた)。
                if _near_wall(d, u, v) or _near_wall(d, q[0], q[1]):
                    continue
                bad.append("グリッド(%g, %g) 造成 %.0f%% > 切土の法面 %.0f%%(自然 %.0f%%)"
                           % (u, v, 100 * dg, 100.0 / bc, 100 * dn))
    return bad


def plane_check(d):
    """面のはみ出し検査。①棟・付属屋・廊下が「自分の y の面の段」の中に完全に載っているか
    (0.5間刻みの被覆)、②棟・付属屋・廊下・庭・井戸・土留め・竹垣が**敷地ポリゴンの中**に
    完全に入っているか(斜めの境界の楔に矩形を当てる — 検図指摘で追加。terrace の素矩形は
    clip されるので見ない)。庭は y を持たないので全段の合併で見る。"""
    ters = d["terraces"]
    eps = 1e-6
    gr = RGrid(d)
    Pg = [gr.L(x, z) for x, z in d["polygon"]]
    npg = len(Pg)

    def inside(u, v):
        c = False
        for i in range(npg):
            (au, av), (bu, bv) = Pg[i], Pg[(i + 1) % npg]
            if (av > v) != (bv > v) and u < au + (bu - au) * (v - av) / (bv - av):
                c = not c
        return c

    cen_u = sum(p[0] for p in Pg) / npg
    cen_v = sum(p[1] for p in Pg) / npg

    def pt_in(u, v, pull=0.2):
        # 境界線上の点は重心側へ pull 間だけ引いて判定する
        du, dv = cen_u - u, cen_v - v
        L2 = math.hypot(du, dv) or 1.0
        return inside(u + du / L2 * pull, v + dv / L2 * pull)

    def rect_out(u0, v0, u1, v1):
        e2 = 0.05
        for (cu, cv) in ((u0 + e2, v0 + e2), (u1 - e2, v0 + e2),
                         (u0 + e2, v1 - e2), (u1 - e2, v1 - e2)):
            if not inside(cu, cv):
                return (cu, cv)
        return None

    def covered(u0, v0, u1, v1, y):
        uu = u0 + 0.25
        while uu < u1:
            vv = v0 + 0.25
            while vv < v1:
                if not inside(uu, vv):
                    return (uu, vv)
                ok = any(tin(t, uu, vv) and (y is None or abs(t["y"] - y) < 0.01)
                         for t in ters)   # ← 段の**多角形**で判定(外接矩形でない)
                if not ok:
                    return (uu, vv)
                vv += 0.5
            uu += 0.5
        return None

    bad = []
    for m in d["munes"] + d["service"]:
        nm = m.get("name", m.get("label"))
        pt = rect_out(m["u0"], m["v0"], m["u1"], m["v1"])
        if pt:
            bad.append("%s が区画の外: グリッド(%.2f, %.2f)" % (nm, pt[0], pt[1]))
            continue
        if m.get("obi"):
            # ⭕ **崖下の帯の棟は「段」に載らない**(2026-09-03 ユーザー裁定8=A) —
            #   帯D2 は造成した面ではなく**地なりの平坦帯**で、棟ごとに小さな面を持つ。
            #   ⛔ 免除ではなく**持ち場の移動**: 帯D2 の中か・切盛が許容内かは `obi_check` が見る。
            continue
        pt = covered(m["u0"], m["v0"], m["u1"], m["v1"], m["y"])
        if pt:
            bad.append("%s (y=%.1f) が面の外: グリッド(%.2f, %.2f)"
                       % (nm, m["y"], pt[0], pt[1]))
    for l in d["links"]:
        pt = rect_out(l["u0"], l["v0"], l["u1"], l["v1"])
        if pt is None and l.get("kind") != "階段廊下":
            # 階段廊下は段をまたぐのが役目なので、単一の面に載る検査はしない
            pt = covered(l["u0"], l["v0"], l["u1"], l["v1"], l["y"])
        if pt:
            bad.append("%s が面/区画の外: (%.2f, %.2f)" % (l["name"], pt[0], pt[1]))
    # ---- 庭。**`polys`(割り当ての矩形から棟と上位の庭を引き、段/区画で切った実形)で見る。**
    #   ⚠ 2026-09-02: 従前は割り当ての矩形をそのまま被覆検査に掛けており、
    #     §4 の割り当て(主面の全面を12区画に割る)にすると構造的に落ちた。
    #   ⭕ 検査の中身は `on`(面の作り方)で分ける — **どちらの向きにも落ちる**:
    #     `面`   … 実形のセルが**すべて段の中**にあること(抜きへはみ出したら不合格)
    #     `地なり` … 実形のセルが**一つも段の中に無い**こと(平坦化しないと宣言した区画に
    #               段の抜きが入っていなければ不合格。=裁定1が実装されているかの検査)
    #     `面+法肩` … 段と抜きにまたがるので被覆は見ない(区画の中であることだけ)
    keeps = [kp for t in d["terraces"] for kp in tkeeps(t)]
    for g in d["gardens"]:
        for ring in (g.get("polys") or []):
            for (uu, vv) in ring:
                if not pt_in(uu, vv, 0.05):
                    bad.append("%s(庭) の実形が区画の外: (%.2f, %.2f)" % (g["name"], uu, vv))
                    break
        on9 = g.get("on")
        mix = [False, False]
        for ring in (g.get("polys") or []):
            us9 = [q[0] for q in ring]; vs9 = [q[1] for q in ring]
            uu = min(us9) + 0.25
            hit = None
            while uu < max(us9) and hit is None:
                vv = min(vs9) + 0.25
                while vv < max(vs9):
                    if _ring_in(ring, uu, vv):
                        inT = any(tin(t, uu, vv) for t in d["terraces"])
                        if on9 == "面" and not inT:
                            hit = (uu, vv, "段の外へ出る")
                            break
                        if on9 == "地なり" and inT and \
                           not any(_ring_in(kp, uu, vv) for kp in keeps):
                            hit = (uu, vv, "平坦化しないと宣言したのに段の中")
                            break
                        if on9 == "混":
                            mix[0] = mix[0] or inT
                            mix[1] = mix[1] or not inT
                    vv += 0.5
                uu += 0.5
            if hit:
                bad.append("%s(庭・%s) が%s: (%.2f, %.2f)"
                           % (g["name"], on9, hit[2], hit[0], hit[1]))
                break
        # ⭕ 「混」は段と抜きにまたがると宣言した庭。⛔ 片側しか無いなら宣言が誤り
        #   (免除ではなく、**またがっていることを検査する**)。
        if on9 == "混" and not (mix[0] and mix[1]):
            bad.append("%s(庭・混) が段と抜きにまたがっていない(段の中=%s / 抜き=%s)"
                       % (g["name"], mix[0], mix[1]))
    for w in d["wells"]:
        if w.get("obi"):
            continue                       # ⭕ 同上(`obi_check` の持ち場)
        pt = covered(w["u"] - 0.5, w["v"] - 0.5, w["u"] + 0.5, w["v"] + 0.5, None)
        if pt:
            bad.append("%s(井戸) が段の外: (%.2f, %.2f)" % (w["name"], pt[0], pt[1]))
    for w in d["terraceWalls"]:
        for (uu, vv) in (w["a"], w["b"]):
            if not pt_in(uu, vv):
                bad.append("%s(土留め) の端点が区画の外: (%g, %g)" % (w["name"], uu, vv))
    for rl in auto_rails(d):
        for (uu, vv) in rl["pts"]:
            if not pt_in(uu, vv):
                bad.append("%s(竹垣) の端点が区画の外: (%g, %g)" % (rl["name"], uu, vv))
    # 段の多角形の頂点は区画の中、かつ区画線から必要な離れだけ内へ入っている。
    # ⚠ 2026-08-31 検図: **必要な離れは辺に何が載るかで違う。**
    #   練塀の辺 … 犬走り 0.30 + 塀厚の半分(塀は境界線に跨る) = 0.875m。
    #   長屋の辺 … 長屋は境界線に跨らず、犬走りの内側から奥行 4.545m を敷地の中へ取る。
    #             段(盛土)は**その足跡の下まで通っていなければ床が空洞の上に載る**ので、
    #             要求は逆に「犬走り 0.30m まで**寄せる**こと」になる。
    #   従前は練塀の数字(0.88m)を全段に当てており、辺12を長屋にした瞬間に
    #   「規約を満たすほど段が足りない」という矛盾が出た。
    clr_hei = (d["const"]["inubashiri"] + d["const"]["dobeiT"] / 2.0) / d["const"]["ken"]
    clr_nag = d["const"]["inubashiri"] / d["const"]["ken"]
    nag_edges = set(r["edge"] for r in d["runs"] if r["kind"] == "Nagaya")
    for t in d["terraces"]:
        for i, (uu, vv) in enumerate(tpoly(t)):
            if not in_parcel(d, uu, vv):
                bad.append("%s(段) の頂点[%d] が区画の外: (%g, %g)" % (t["name"], i, uu, vv))
                continue
            dist, e9, _s9 = _par_near(d, uu, vv)
            clr = clr_nag if e9 in nag_edges else clr_hei
            if dist < clr - 1e-6:
                bad.append("%s(段) の頂点[%d] が区画線まで %.2fm(規定 %.2fm・辺%d)"
                           % (t["name"], i, dist * d["const"]["ken"],
                              clr * d["const"]["ken"], e9))
    return bad


def adjacency_check(d):
    """高さの違う段どうしが接する辺に、土留めが載っているか総当たりで検める。
    2026-08-23 に KitaSumi↔ShuKita の 2.1m の段が受け無しで残っていたのを見落とした。"""
    T = d["terraces"]
    W = d["terraceWalls"]
    bad = []
    for i in range(len(T)):
        for j in range(len(T)):
            if i == j:
                continue
            a, b = T[i], T[j]
            if abs(a["y"] - b["y"]) < 0.05:
                continue
            for axis in ("u", "v"):
                # a と b が axis=const の直線で接する区間を出す
                p, q = ("u", "v") if axis == "u" else ("v", "u")
                line = None
                if abs(a[p + "1"] - b[p + "0"]) < 1e-9:
                    line = a[p + "1"]
                elif abs(a[p + "0"] - b[p + "1"]) < 1e-9:
                    line = a[p + "0"]
                if line is None:
                    continue
                lo = max(a[q + "0"], b[q + "0"]); hi = min(a[q + "1"], b[q + "1"])
                if hi - lo < 0.5:
                    continue
                hi_y = max(a["y"], b["y"])
                held = 0.0
                for w in W:
                    (wa_u, wa_v), (wb_u, wb_v) = w["a"], w["b"]
                    wp = (wa_u, wb_u) if p == "u" else (wa_v, wb_v)
                    wq = (wa_v, wb_v) if p == "u" else (wa_u, wb_u)
                    if abs(wp[0] - wp[1]) > 1e-9 or abs(wp[0] - line) > 1e-9:
                        continue
                    if abs(w["coping"] - hi_y) > 0.05:
                        continue
                    held = max(held, min(hi, max(wq)) - max(lo, min(wq)))
                if held < (hi - lo) - 0.5:
                    pair = " ↔ ".join(sorted(["%s(%.1f)" % (a["name"], a["y"]),
                                              "%s(%.1f)" % (b["name"], b["y"])]))
                    bad.append("%s の %s=%g・%s %g..%g "
                               "(%.1f間)に土留めが %.1f間しか無い — 落差 %.1fm が受け無し"
                               % (pair, p, line, q, lo, hi,
                                  hi - lo, max(held, 0.0), abs(a["y"] - b["y"])))
    return sorted(set(bad))


def wall_check(d):
    """土留めの設計高さ(4s)が、走りに沿った実測落差 drop=[min,max] と釣り合っているか。
    足りなければ崩れ、過大なら**土に埋まる壁**になる(2026-08-23 ユーザー指摘の再発防止)。"""
    bad = adjacency_check(d)
    for w in d["terraceWalls"]:
        dr = w.get("drop")
        if not dr:
            bad.append("%s に drop(実測落差)が無い — 断面で高さを検算できない" % w["name"])
            continue
        h = 4.0 * w["s"]
        if dr[1] < 0.0:
            # ⛔ 天端が地盤より下 = 壁が丸ごと土に埋まる。**立てる前提そのものが消えている。**
            bad.append("%s の天端 %.2f が全区間で地盤より下(露出 %.2f〜%.2fm)— "
                       "**壁が丸ごと埋まる。立てる前提(法面が到達距離の中で着地しない)が"
                       "地盤の直しで消えていないか確かめること**"
                       % (w["name"], w["coping"], dr[0], dr[1]))
            continue
        if h < dr[1] - 0.05:
            bad.append("%s 壁高 %.2f < 最大落差 %.2f — 足りない" % (w["name"], h, dr[1]))
        elif h > dr[1] + 0.8:
            bad.append("%s 壁高 %.2f ≫ 最大落差 %.2f — 過大(埋まる)" % (w["name"], h, dr[1]))
        if dr[0] < 0.3:
            bad.append("%s は落差 %.2f の区間を含む — その区間は壁でなく法面にする" % (w["name"], dr[0]))
    return bad


# overlap_check の正典は sashizu_lib(2026-08-26 統一。石段・段どうし・土留め貫通なども見る
# 土井基準の版。当邸に無いデータ(terraceWalls の実体など)は素通りする)。


# ---------------------------------------------------------------- 取り合い(実装用)(実装用・自動算出)


def corners_table(d):
    """外周の隅(区画の頂点)。世界座標・折れ角・両側の run と天端差・納めを設計値から導く。"""
    P = d["polygon"]
    n = len(P)
    yag = {y["vertex"]: y for y in d["yagura"]}
    rows = []
    for i in range(n):
        prev_e, next_e = (i - 1) % n, i
        rl = [r for r in d["runs"] if r["edge"] == prev_e]
        rr = [r for r in d["runs"] if r["edge"] == next_e]
        rl = max(rl, key=lambda r: r["s1"]) if rl else None
        rr = min(rr, key=lambda r: r["s0"]) if rr else None
        # ⭕ 2026-09-01 六巡目: **木柵(fences)も外周の要素として拾う。** 従前は `runs` しか
        #   見ておらず、辺5(溜池の堤・木柵80.6m)に接する P5 の納めが空欄のままだった。
        fl = next((f for f in d.get("fences", []) if f["edge"] == prev_e), None)
        fr = next((f for f in d.get("fences", []) if f["edge"] == next_e), None)
        dx1, dz1, _ = _edge_dir(P, prev_e)
        dx2, dz2, _ = _edge_dir(P, next_e)
        delta = math.degrees(math.acos(max(-1, min(1, dx1 * dx2 + dz1 * dz2))))
        if (fl or fr) and (rl or rr or fl or fr):
            other = rl or rr
            if other is None:
                osame = ("%s(<code>%s</code>)の端。相手側の辺%d は当家が建てない — "
                         "柵はここで留め、親柱を立てて仕舞う"
                         % ((fl or fr)["kind"], (fl or fr)["name"], next_e if fl else prev_e))
            else:
                k9 = "表長屋" if other["kind"] == "Nagaya" else "練塀"
                osame = ("%sの小口と木柵の取り合い(折れ %.1f°)。⛔ **天端は突き合わせない** — "
                         "木柵は地形なりで基礎も基壇も持たないので、%sの端部で切り、"
                         "柵の親柱をその小口へ抱かせる" % (k9, delta, k9))
        elif rl is None or rr is None:
            osame = ("—(辺%d・辺%d のうち当家が建てるものが無い)"
                     % (prev_e, next_e)) if (rl is None and rr is None) else \
                    ("当家の囲いはここで切れる — 辺%d は当家が建てない"
                     % (next_e if rl is not None else prev_e))
        elif i in yag:
            osame = "隅櫓 %s が受ける" % yag[i]["name"]
        elif rl["kind"] == "Nagaya" and rr["kind"] == "Nagaya":
            osame = "長屋は退けて桁を突き付け(ebc11da の作法)"
        elif rl["kind"] == "Dobei" and rr["kind"] == "Dobei":
            osame = "留め継ぎ隅部材(build_kado・折れ角は現地=Δ%.1f°)" % delta
        elif {rl["kind"], rr["kind"]} == {"Dobei", "Nagaya"}:
            # ⚠ 2026-08-31 三巡目で足した枝。辺12 が表長屋になって P0・P12 がここへ来たのに、
            #    分岐が無いので「天端差」の枝へ落ち、**平面の納めがどこにも書かれていなかった**。
            #    ⛔ 1間厚の練塀の小口を、奥行 4.545m の建屋の妻壁へどう取り付けるかは高さの話ではない。
            ov9 = _quad_overlap(_run_fp(d, rl), _run_fp(d, rr))
            osame = ("練塀の小口を表長屋の妻壁へ**突き付ける**(めり込み %.2f m²・折れ %.1f°)。"
                     "⛔ 隙間を作らない — 折れ角が直角でないと妻面と辺の間に楔が開く"
                     % (ov9, delta))
        elif abs((rseat(rr, rr["s0"]) if rr else 0) - (rseat(rl, rl["s1"]) if rl else 0)) > 0.3:
            osame = "天端差は高い側の基壇小口(隅石)で受ける"
        else:
            osame = "天端同高で留め継ぐ"
        yl = rseat(rl, rl["s1"]) if rl else 0.0
        yr = rseat(rr, rr["s0"]) if rr else 0.0
        ds = (yr - yl) if (rl and rr) else 0.0
        # ⭕ 2026-09-01 六巡目: **Δ天端の納めを、種別で分かれたどの枝にも必ず付ける。**
        #   従前は「天端差は高い側の基壇小口で受ける」が **kind の分岐の後ろの elif** に
        #   居たため、練塀×練塀・長屋×長屋の隅は Δ が 2.22m あっても段の納めが
        #   一言も書かれなかった(P4 −2.22 / P11 −1.74 / P9 +1.34)。
        if rl and rr and abs(ds) > 0.30 and "天端" not in osame:
            hi9 = rr if ds > 0 else rl
            osame += ("／Δ天端 %+.2fm は**高い側(<code>%s</code>)の基壇小口=隅石**で受け、"
                      "低い側の天端をその小口へ突き付ける(段は隅でだけ落とす)"
                      % (ds, hi9["name"]))
        rows.append("<tr><td>P%d</td><td>(%.1f, %.1f)</td><td>%.1f°</td>"
                    "<td><code>%s</code> %.2f</td><td><code>%s</code> %.2f</td><td>%+.2f</td><td class='note'>%s</td></tr>"
                    % (i, P[i][0], P[i][1], delta,
                       rl["name"] if rl else "—", yl,
                       rr["name"] if rr else "—", yr, ds, osame))
    return ("<h3>隅(区画の頂点)</h3><div class='tw'><table><thead><tr><th>頂点</th><th>世界座標 (x,z)</th>"
            "<th>折れ角Δ</th><th>手前の run・天端</th><th>先の run・天端</th><th>Δ天端</th><th class='note'>納め</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def joints_table(d):
    """辺の中の継ぎ目(run と run・run と開口)。s と世界座標、天端差。"""
    P = d["polygon"]
    gp0 = d["gate"]["plan"]
    ops = [("表門", d["gate"]["edge"],
            d["gate"]["s"] - gp0["monW"] / 2, d["gate"]["s"] + gp0["monW"] / 2)]
    if d.get("onarimon"):
        ops.append(("御成門", d["onarimon"]["edge"], d["onarimon"]["s"] - d["onarimon"]["w"] / 2,
                    d["onarimon"]["s"] + d["onarimon"]["w"] / 2))
    for k in d["komon"]:
        ops.append(("木戸", k["edge"], k["s"] - k["w"] / 2, k["s"] + k["w"] / 2))
    rows = []
    for e in range(len(P)):
        rs = sorted([r for r in d["runs"] if r["edge"] == e], key=lambda r: r["s0"])
        for a, b in zip(rs, rs[1:]):
            gap = b["s0"] - a["s1"]
            w = edge_pt(P, e, a["s1"])
            if gap < 0.05:
                rows.append("<tr><td>辺%d s=%.1f</td><td>(%.1f, %.1f)</td>"
                            "<td><code>%s</code> → <code>%s</code></td><td>%.1f → %.1f (%+.1f)</td>"
                            "<td class='note'>段差=高い側の基壇小口が %.1fm 見える</td></tr>"
                            % (e, a["s1"], w[0], w[1], a["name"], b["name"],
                               rseat(a, a["s1"]), rseat(b, b["s0"]),
                               rseat(b, b["s0"]) - rseat(a, a["s1"]),
                               abs(rseat(b, b["s0"]) - rseat(a, a["s1"]))))
            else:
                op = next((o for o in ops if o[1] == e and o[2] > a["s1"] - 1 and o[3] < b["s0"] + 1), None)
                wa = edge_pt(P, e, a["s1"]); wb = edge_pt(P, e, b["s0"])
                rows.append("<tr><td>辺%d s=%.1f–%.1f</td><td>(%.1f, %.1f)–(%.1f, %.1f)</td>"
                            "<td><code>%s</code> ⋯ <code>%s</code></td><td>%.1f ⋯ %.1f</td>"
                            "<td class='note'>開口 %.1fm%s。囲いの端部は門の袖・番所へ突き付け</td></tr>"
                            % (e, a["s1"], b["s0"], wa[0], wa[1], wb[0], wb[1],
                               a["name"], b["name"], rseat(a, a["s1"]), rseat(b, b["s0"]), gap,
                               "(%s)" % op[0] if op else ""))
    return ("<h3>辺の中の継ぎ目と開口</h3><div class='tw'><table><thead><tr><th>位置</th><th>世界座標</th>"
            "<th>run</th><th>天端</th><th class='note'>納め</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def civil_table(d):
    """郭内の土木(土留め・石段・竹垣)の端点の世界座標。"""
    gr = RGrid(d)
    rows = []
    for w in d["terraceWalls"]:
        wa, wb = gr.W(*w["a"]), gr.W(*w["b"])
        rows.append("<tr><td><code>%s</code></td><td>土留め(s=%.2f)</td>"
                    "<td>(%.1f, %.1f) → (%.1f, %.1f)</td><td>天端 %.1f・壁高 %.1f</td></tr>"
                    % (w["name"], w["s"], wa[0], wa[1], wb[0], wb[1], w["coping"], 4.0 * w["s"]))
    for k in d["kaidans"]:
        ax, at2, ka, kb, cu, cv = kgeom(k)
        ca, cb = (gr.W(at2, ka), gr.W(at2, kb)) if ax == "v" else (gr.W(ka, at2), gr.W(kb, at2))
        rows.append("<tr><td><code>%s</code></td><td>石段 %d段(幅 %.2fm)</td>"
                    "<td>(%.1f, %.1f) → (%.1f, %.1f)</td>"
                    "<td>落差 %.2f・走り %.2fm(蹴上 %.3f ≦ 規約0.30)</td></tr>"
                    % (k["name"], k["steps"], k["w"], ca[0], ca[1], cb[0], cb[1],
                       k["drop"], k["run"], k["keri"]))
    for rp in d.get("ramps", []):
        pts = [gr.W(u, v) for u, v in rp["pts"]]
        rows.append("<tr><td><code>%s</code></td><td>坂(幅 %.2fm)</td>"
                    "<td class='note'>%s</td><td>全長 %.1fm・昇り %.2fm・最急 %.1f%%</td></tr>"
                    % (rp["name"], rp["w"], " → ".join("(%.1f, %.1f)" % q for q in pts),
                       rp["len"], rp["rise"],
                       (ramp_metrics(d, rp) or {}).get("grad", 0)))
    for rl in auto_rails(d):
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        lo9, hi9 = _rail_offset(d, rl)
        rows.append("<tr><td><code>%s</code></td><td>竹垣(四つ目垣 h%.2f)</td>"
                    "<td class='note'>%s</td><td>折れ線 %.1fm(法肩からの実距離 %.2f〜%.2fm)</td></tr>"
                    % (rl["name"], d["const"]["takegakiH"], _ptrunc(pts),
                       rl["len"], lo9, hi9))
    return ("<h3>郭内の土木の端点</h3><div class='tw'><table><thead><tr><th>名</th><th>種別</th>"
            "<th>世界座標</th><th>寸法</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def gate_parts_table(d):
    """門構えの部材位置。長屋門は一体の躯体なので芯と両端を出す。"""
    P = d["polygon"]
    g = d["gate"]; gp = g["plan"]
    dx, dz, _ = _edge_dir(P, g["edge"])
    rows = []
    for nm, s_off in [("長屋門(芯)", 0.0),
                      ("躯体 北端(表長屋 E_Nagaya_S との継ぎ)", -gp["monW"] / 2),
                      ("躯体 南端(表長屋 E_Nagaya_N との継ぎ)", gp["monW"] / 2)]:
        x, z = edge_pt(P, g["edge"], g["s"] + s_off)
        rows.append("<tr><td>%s</td><td>(%.2f, %.2f)</td><td>%.2f</td><td>%.1f</td></tr>"
                    % (nm, x, z, g["sill"], g["yaw"]))
    for k in d["komon"]:
        x, z = edge_pt(P, k["edge"], k["s"])
        ddx, ddz, _ = _edge_dir(P, k["edge"])
        kyaw = (math.degrees(math.atan2(ddz, -ddx))) % 360
        rows.append("<tr><td>木戸(芯)</td><td>(%.2f, %.2f)</td><td>%.2f</td><td>%.1f</td></tr>"
                    % (x, z, k["sill"], kyaw))
    return ("<h3>門構えの部材位置</h3><div class='tw'><table><thead><tr><th>部材</th><th>芯の世界座標 (x,z)</th>"
            "<th>敷居</th><th>yaw</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>長屋門の両袖は<b>表長屋へ継ぐ</b>(番所は躯体内。呼称は json <code>gate.plan.bansho.kind</code>)。⭐ 2026-08-31 のユーザー裁定で辺12の両袖を表長屋にした。梁間は長屋と面一(いずれも 2.5間)。</p>")


def bom_table(d):
    if "bom" not in d:
        return ""
    rows = []
    for b in d["bom"]:
        stock = b.get("asset", "")
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (b["item"], "<b>新造(Blender)</b>" if b.get("build") else "在庫",
                       ("<code>%s</code>" % stock) if stock else "—", inline(b.get("note", ""))))
    return ('<div class="tw"><table><thead><tr><th>部材</th><th>調達</th><th class="note">在庫パス/新造名</th>'
            "<th class='note'>備考</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def build_stamp():
    """**この図を組んだ時点**を表の先頭に出す。
    ⛔ 2026-09-01 六巡目まで、改訂表は `git log` だけを引いていたので、
      **図を組んだ後にコミットする**という順序から、その図を作った改訂そのものが
      構造的に表へ出なかった(「⚠ この図を作ったコミット自身は表に出ない(構造上)」と
      注記して済ませていた)。⭕ 組んだ時点の HEAD と、設計値・文章が未コミットかどうかを
      **組むときに読んで**出せば、読み手は表と実物の差を自分で言い当てられる。"""
    try:
        head = subprocess.check_output(
            ["git", "-C", ROOT, "log", "-1", "--date=short", "--pretty=%h|%ad|%s"]).decode().strip()
        h9, d9, s9 = head.split("|", 2)
    except Exception:
        return None
    try:
        st = subprocess.check_output(
            ["git", "-C", ROOT, "status", "--porcelain", "--",
             "docs/Sashizu/okabe_sashizu.json", "docs/Sashizu/okabe_kosho.md"]).decode()
    except Exception:
        st = ""
    # ⛔ 行頭の空白を落とさない — `st.strip()` してから ln[3:] で切ると先頭行だけ1字欠ける。
    dirty = [ln[2:].strip() for ln in st.splitlines() if ln.strip()]
    return (h9, d9, s9, dirty)


def history():
    try:
        log = subprocess.check_output(
            ["git", "-C", ROOT, "log", "--date=short",
             "--pretty=%h|%ad|%s", "--", "docs/Sashizu/okabe_sashizu.json",
             "docs/Sashizu/okabe_kosho.md"]).decode()
    except Exception:
        log = ""
    rows = []
    for ln in log.strip().split("\n"):
        if not ln.strip():
            continue
        h, dt, sub = ln.split("|", 2)
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td class='note'>%s</td></tr>"
                    % (h, dt, html.escape(sub)))
    if not rows:
        rows = ["<tr><td colspan='3' class='note'>初版(未コミット)</td></tr>"]
    st = build_stamp()
    if st:
        h9, d9, s9, dirty = st
        rows.insert(0, "<tr><td><b>組んだ時点</b></td><td>%s</td><td class='note'>"
                       "HEAD=<code>%s</code>「%s」／設計値・文章は<b>%s</b>%s</td></tr>"
                    % (d9, h9, html.escape(s9),
                       "未コミットの改訂を含む" if dirty else "HEAD と一致",
                       ("(%s)" % "・".join("<code>%s</code>" % html.escape(x) for x in dirty))
                       if dirty else ""))
    return ("<div class='tw'><table><thead><tr><th>commit</th><th>日付</th><th class='note'>件名</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 組み立て
# ================================================================ 庭(edo-niwashi の設計の書き起こし)
# ⛔ **この節に数値を書かない。**寸法の正典は json、ここに出る量はすべて算出値。
#   spec(庭方の設計書)の検算値は「一致するはずの照合先」であって、図が刷るのは毎回の算出値。

def chaikin(pts, n=2):
    """折れ線(閉)の Chaikin 平滑化。**実装で汀線に掛ける平滑化を図でも同じだけ掛ける。**
    ⚠ 検算(面積・周長・円形度)は**平滑化前の設計多角形**で出す — 平滑化は形を内へ
      縮めるだけで、設計した寸法ではない。"""
    p = [(a, b) for a, b in pts]
    for _ in range(n):
        q = []
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            q.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            q.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        p = q
    return p


def gardens_by(d):
    return dict((g["name"], g) for g in d.get("gardens", []))


def g_in(g, u, v):
    return any(_ring_in([(a, b) for a, b in r], u, v) for r in (g.get("polys") or []))


def g_area(g):
    return sum(_ring_area([(a, b) for a, b in r]) for r in (g.get("polys") or []))


def pond_of(d):
    """主庭の池。返すのは (庭, migiwa, **平滑後の汀線**)。
    ⭐ 2026-09-02: 点景の合否・掘削・作図はすべて**平滑後**で見る(実際に掘る形)。
    生の16点(設計値)が要るときは `pond_raw(d)`。"""
    for g in d.get("gardens", []):
        mg = g.get("migiwa")
        if mg:
            return g, mg, chaikin([(a, b) for a, b in mg["pts"]], mg.get("smooth", 2))
    return None, None, None


def pond_raw(d):
    """設計値としての汀線(生の16点)。⛔ 施工形状ではない。"""
    for g in d.get("gardens", []):
        if g.get("migiwa"):
            return [(a, b) for a, b in g["migiwa"]["pts"]]
    return None


def pond_sd(ring, u, v):
    """汀線からの符号つき距離[間]。**+ が汀の外(陸)**。"""
    dd = sashizu_lib.poly_edge_dist(ring, u, v)
    return -dd if _ring_in(ring, u, v) else dd


def ring_arc(ring, a, b):
    """閉じた点列 `ring` の上を a から b まで辿る部分列(短いほう)。乱杭の割り付けに使う。
    ⚠ **端点は線分へ正射影する。**最寄りの頂点へ丸めると、平滑後の細かい折れ点のぶん
      弧長が伸びて本数が増える(2026-09-02: 端点丸めで 54本、正射影で 47本)。"""
    def proj(q):
        best = (1e18, 0, (q[0], q[1]))
        for i9 in range(len(ring)):
            p0, p1 = ring[i9], ring[(i9 + 1) % len(ring)]
            du, dv = p1[0] - p0[0], p1[1] - p0[1]
            L2 = du * du + dv * dv or 1e-12
            t9 = max(0.0, min(1.0, ((q[0] - p0[0]) * du + (q[1] - p0[1]) * dv) / L2))
            c9 = (p0[0] + du * t9, p0[1] + dv * t9)
            dd = math.hypot(q[0] - c9[0], q[1] - c9[1])
            if dd < best[0]:
                best = (dd, i9, c9)
        return best[1], best[2]
    i0, c0 = proj(a)
    i1, c1 = proj(b)
    fwd = [c0] + [ring[(i0 + 1 + k) % len(ring)] for k in range((i1 - i0) % len(ring))] + [c1]
    bwd = [c0] + [ring[(i0 - k) % len(ring)] for k in range((i0 - i1) % len(ring))] + [c1]

    def L(seq):
        return sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(seq, seq[1:]))
    return fwd if L(fwd) <= L(bwd) else bwd


def mounds_of(d):
    return [(g, ts) for g in d.get("gardens", []) for ts in (g.get("tsukiyama") or [])]


def _ell_r(ts, u, v):
    return math.hypot((u - ts["u"]) / (ts["dU"] / 2.0), (v - ts["v"]) / (ts["dV"] / 2.0))


def sight_top(d, u, v, nat):
    """視線を遮る物の天端。地盤(築山を含む)に、点景(中島・岩島・橋・景石・灯籠)を重ねる。"""
    g0 = graded_y(d, u, v, nat)
    y = nat if g0 is None else g0
    if y is None:
        return -1e9
    for g in d.get("gardens", []):
        for nj in (g.get("nakajima") or []):
            pol9 = [(a9, b9) for a9, b9 in (nj.get("poly") or [])]
            if pol9 and _ring_in(pol9, u, v):
                y = max(y, nj["topY"])
        for ij in (g.get("iwajima") or []):
            if math.hypot(u - ij["u"], v - ij["v"]) * d["const"]["ken"] <= 0.9:
                y = max(y, (g.get("migiwa") or {}).get("waterY", y) + ij["hMain"] - ij["sink"])
        for sw in (g.get("sawatobi") or []):
            for (su, sv) in sw["pts"]:
                if math.hypot(u - su, v - sv) * d["const"]["ken"] <= sw["rMax"] / 2.0:
                    y = max(y, sw["topY"])
        for st in (g.get("ishigumi") or []) + (g.get("toro") or []):
            if st.get("u") is None or st.get("v") is None:
                continue
            if math.hypot(u - st["u"], v - st["v"]) * d["const"]["ken"] <= 0.7:
                y = max(y, (graded_y(d, st["u"], st["v"], nat) or 24.8) + (st.get("h") or 1.2))
    return y


def pond_metrics(d):
    """池の検算。⛔ **spec の数値を写さない** — ここが毎回算出する。"""
    g, mg, ring = pond_of(d)          # ring = **平滑後(施工形状)**
    if not g:
        return None
    raw = pond_raw(d)                 # raw = 生の16点(設計値)
    K = d["const"]["ken"]

    def shape(p9):
        n9 = len(p9)
        A9 = _ring_area(p9)
        P9 = sum(math.hypot(p9[(i + 1) % n9][0] - p9[i][0], p9[(i + 1) % n9][1] - p9[i][1])
                 for i in range(n9))
        return {"n": n9, "areaKen": A9, "areaM2": A9 * K * K, "tsubo": A9 * K * K / TSUBO,
                "perimM": P9 * K, "circ": 4 * math.pi * (A9 * K * K) / (P9 * K) ** 2}
    raws = shape(raw)
    sms = shape(ring)
    n = len(raw)
    sp = [math.hypot(raw[(i + 1) % n][0] - raw[i][0], raw[(i + 1) % n][1] - raw[i][1])
          for i in range(n)]
    m9 = sum(sp) / n
    cv = (sum((x - m9) ** 2 for x in sp) / n) ** 0.5 / m9
    o = {"raw": raws, "sm": sms, "n": n,
         "areaKen": sms["areaKen"], "areaM2": sms["areaM2"], "tsubo": sms["tsubo"],
         "perimM": sms["perimM"], "circ": sms["circ"], "circRaw": raws["circ"],
         "spMean": m9, "spMin": min(sp), "spMax": max(sp), "spCV": cv,
         "gardenTsubo": g_area(g) * K * K / TSUBO}
    o["waterPct"] = 100.0 * o["tsubo"] / max(o["gardenTsubo"], 1e-9)
    # くびれ(向かい合う汀のいちばん狭い所)
    best = None
    for i in range(n):
        for j in range(i + 2, n):
            if (j - i) % n in (0, 1, n - 1):
                continue
            dd = math.hypot(ring[i][0] - ring[j][0], ring[i][1] - ring[j][1])
            mu = (ring[i][0] + ring[j][0]) / 2.0; mv = (ring[i][1] + ring[j][1]) / 2.0
            if not _ring_in(ring, mu, mv):
                continue
            if best is None or dd < best[0]:
                best = (dd, i, j)
    o["kubireKen"], o["kubireA"], o["kubireB"] = (best if best else (0.0, -1, -1))
    o["kubireM"] = o["kubireKen"] * K
    # ⚠ 上は**汀線のいちばん狭い所**(総当たり)。沢飛石が渡るくびれは `saw` で別に出す —
    #   庭方が「くびれ」と呼ぶのは渡りの架かる所で、必ずしも最狭とは限らない。
    # 離れ(下回ってはならない値との照合)
    def dmin(pred):
        return min(pred(p[0], p[1]) for p in ring)
    o["dShoin"] = dmin(lambda u, v: u - 0.0)
    o["dGenkan"] = dmin(lambda u, v: v - 63.0)
    w1 = next((w for w in d.get("kekkai", []) if w["name"] == "W1"), None)
    o["dKekkai"] = (w1["a"][1] - max(p[1] for p in ring)) if w1 else 0.0
    o["dTsukiyama"] = 1e9
    for _g, ts in mounds_of(d):
        for k9 in range(721):
            th = math.radians(k9 * 0.5)
            pu = ts["u"] + ts["dU"] / 2.0 * math.cos(th)
            pv = ts["v"] + ts["dV"] / 2.0 * math.sin(th)
            o["dTsukiyama"] = min(o["dTsukiyama"], sashizu_lib.poly_edge_dist(ring, pu, pv))
    # 掘り込みであることの実測(汀の内側の江戸期地盤)
    E = _DEM.get(id(d)) or (_dem_at(d, 0, 0) or _DEM.get(id(d)))
    E = _DEM.get(id(d))
    vals = []
    if E:
        for jv in range(E["nv"]):
            for iu in range(E["nu"]):
                uu = E["u0"] + iu * E["step"]; vv = E["v0"] + jv * E["step"]
                if not _ring_in(ring, uu, vv):
                    continue
                h9 = E["h"][jv][iu]
                if h9 is not None:
                    vals.append(h9)
    o["cells"] = len(vals)
    o["natMin"] = min(vals) if vals else None
    o["natMax"] = max(vals) if vals else None
    o["below"] = sum(1 for h9 in vals if h9 < mg["waterY"])
    # 見隠れ(主視点から見える水面の割合)
    mk = next((m for m in (g.get("mikoro") or []) if m.get("main")), None)
    seen = tot = 0
    if mk:
        step = 0.25
        uu = min(p[0] for p in ring)
        while uu <= max(p[0] for p in ring):
            vv = min(p[1] for p in ring)
            while vv <= max(p[1] for p in ring):
                if _ring_in(ring, uu, vv):
                    tot += 1
                    L = math.hypot(uu - mk["u"], vv - mk["v"])
                    ok = True
                    t9 = 0.06
                    while t9 < 0.995:
                        pu = mk["u"] + (uu - mk["u"]) * t9
                        pv = mk["v"] + (vv - mk["v"]) * t9
                        ray = mk["eyeY"] + (mg["waterY"] - mk["eyeY"]) * t9
                        nat = _dem_at(d, pu, pv)
                        if sight_top(d, pu, pv, nat) > ray + 0.02:
                            ok = False
                            break
                        t9 += 0.03
                    if ok:
                        seen += 1
                vv += step
            uu += step
    o["visPct"] = 100.0 * seen / tot if tot else 0.0
    o["visN"] = tot
    # 乱杭 — **平滑汀線に沿った弧長からの従属値**
    o["rangui"] = []
    for rg in (g.get("rangui") or []):
        arc = ring_arc(ring, rg["a"], rg["b"])
        L9 = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(arc, arc[1:])) * K
        o["rangui"].append({"name": rg["label"], "lenM": L9, "pitch": rg["pitch"],
                            "n": int(round(L9 / rg["pitch"])) + 1})
    # 中島の両側の水面の幅
    nj = (g.get("nakajima") or [None])[0]
    o["nakaFlank"] = []
    o["naka"] = None
    if nj and nj.get("poly"):
        pol = [(a9, b9) for a9, b9 in nj["poly"]]
        A9 = _ring_area(pol) * K * K
        n9 = len(pol)
        P9 = sum(math.hypot(pol[(i9 + 1) % n9][0] - pol[i9][0],
                            pol[(i9 + 1) % n9][1] - pol[i9][1]) for i9 in range(n9)) * K
        cu = sum(q[0] for q in pol) / n9; cv = sum(q[1] for q in pol) / n9
        # 主軸の向き(二次モーメントから)
        sxx = sum((q[0] - cu) ** 2 for q in pol); svv = sum((q[1] - cv) ** 2 for q in pol)
        sxv = sum((q[0] - cu) * (q[1] - cv) for q in pol)
        ang = math.degrees(0.5 * math.atan2(2 * sxv, sxx - svv))
        o["naka"] = {"areaM2": A9, "perimM": P9, "circ": 4 * math.pi * A9 / (P9 ** 2),
                     "axisDeg": ang, "cu": cu, "cv": cv}
        for sgn in (1, -1):
            t9 = 0.0
            while t9 < 12.0 and (_ring_in(pol, cu + sgn * t9, cv)
                                 or _ring_in(ring, cu + sgn * t9, cv)):
                t9 += 0.02
            u9 = 0.0
            while u9 < 12.0 and _ring_in(pol, cu + sgn * u9, cv):
                u9 += 0.02
            o["nakaFlank"].append(t9 - u9)
    # 沢飛石(渡り)の実寸と、その区間の実水面幅
    sw = (g.get("sawatobi") or [None])[0]
    o["saw"] = None
    if sw:
        pts9 = [(a, b) for a, b in (sw.get("stonePts") or sw["pts"])]
        L9 = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts9, pts9[1:]))
        sl = mg.get("shallow") or {}
        wmin = None
        v9 = sl.get("v0", min(q[1] for q in pts9))
        while v9 <= sl.get("v1", max(q[1] for q in pts9)) + 1e-9:
            xs = []
            for i9 in range(len(ring)):
                (p0, q0), (p1, q1) = ring[i9], ring[(i9 + 1) % len(ring)]
                if (q0 - v9) * (q1 - v9) > 0 or q0 == q1:
                    continue
                xs.append(p0 + (p1 - p0) * (v9 - q0) / (q1 - q0))
            if len(xs) >= 2:
                w9 = max(xs) - min(xs)
                wmin = w9 if wmin is None else min(wmin, w9)
            v9 += 0.05
        o["saw"] = {"n": len(pts9), "lenKen": L9, "lenM": L9 * K,
                    "pitchKen": L9 / max(len(pts9) - 1, 1),
                    "pitchM": L9 / max(len(pts9) - 1, 1) * K,
                    "widthKen": wmin or 0.0, "widthM": (wmin or 0.0) * K,
                    "sd": [pond_sd(ring, a, b) for a, b in pts9],
                    "depth": mg["waterY"] - (sl.get("bedY") or mg["bedY"])}
    # 飛石の芯々
    # 飛石。⚠ **json の `pts` は石の位置ではなく「筋」の折れ点**(石は筋の上に
    #   芯々 `pitchMin`〜`pitchMax` で置く)。石数は長さからの従属値なので算出する。
    tb = (g.get("tobiishi") or [None])[0]
    o["tobi"] = None
    if tb and isinstance(tb.get("pts"), list):
        L9 = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(tb["pts"], tb["pts"][1:])) * K
        o["tobi"] = {"lenM": L9, "nMin": int(L9 / tb["pitchMax"]), "nMax": int(L9 / tb["pitchMin"]),
                     "segs": [math.hypot(b[0] - a[0], b[1] - a[1]) * K
                              for a, b in zip(tb["pts"], tb["pts"][1:])]}
    return o


def tsukiyama_metrics(d):
    """築山ごとの実測。**底の自然地盤は必ず実測して刷る**(『高まりに載る』を宣言で済ませない)。"""
    out = []
    E = _DEM.get(id(d))
    if E is None:
        _dem_at(d, 0, 0); E = _DEM.get(id(d))
    K = d["const"]["ken"]
    g0, mg0, ring0 = pond_of(d)
    mk = None
    if g0:
        mk = next((m for m in (g0.get("mikoro") or []) if m.get("main")), None)
    for g, ts in mounds_of(d):
        cells = []
        vol = 0.0
        for jv in range(E["nv"]):
            for iu in range(E["nu"]):
                uu = E["u0"] + iu * E["step"]; vv = E["v0"] + jv * E["step"]
                if _ell_r(ts, uu, vv) > 1.0:
                    continue
                h9 = E["h"][jv][iu]
                if h9 is None:
                    continue
                cells.append(h9)
                vol += max(0.0, (ts["topY"] - h9) * (1.0 - _ell_r(ts, uu, vv))) * (E["step"] * K) ** 2
        planKen = math.pi * (ts["dU"] / 2.0) * (ts["dV"] / 2.0)
        o = {"g": g, "ts": ts, "cells": len(cells),
             "natMin": min(cells) if cells else None, "natMax": max(cells) if cells else None,
             "natMean": (sum(cells) / len(cells)) if cells else None,
             "volM3": vol, "planKen": planKen, "planTsubo": planKen * K * K / TSUBO,
             "h": ts["topY"] - ((sum(cells) / len(cells)) if cells else 0.0)}
        # 段の外へ出る面積
        outk = 0.0
        st = 0.25
        uu = ts["u"] - ts["dU"] / 2.0
        while uu <= ts["u"] + ts["dU"] / 2.0:
            vv = ts["v"] - ts["dV"] / 2.0
            while vv <= ts["v"] + ts["dV"] / 2.0:
                if _ell_r(ts, uu, vv) <= 1.0 and not any(tin(t, uu, vv) for t in d["terraces"]):
                    outk += st * st
                vv += st
            uu += st
        o["outKen"] = outk
        # 主視点からの距離と仰角
        vp = mk
        for m9 in (g.get("mikoro") or []):
            if m9.get("target") == ts["name"]:
                vp = m9
        if vp:
            dist = math.hypot(ts["u"] - vp["u"], ts["v"] - vp["v"]) * K
            o["viewFrom"] = vp["label"]
            o["distM"] = dist
            o["elevDeg"] = math.degrees(math.atan2(ts["topY"] - vp["eyeY"], max(dist, 1e-9)))
        out.append(o)
    return out


_BRK = {}


def earth_breakdown(d, ter):
    """**客土がどこで増え、どこで減ったかの内訳。**同じ格子を3つの設計で歩いて差を採る:

      ①素の設計   … 抜きも庭の土工も無い(主面を一枚に均す)
      ②抜きだけ   … 裁定1(5区画を平坦化しない)を入れた
      ③当図       … さらに池と築山を重ねた

    ⛔ **spec の見込み(主面の多角形の中だけを数えた値)と当図の算出値を並べて書かない** —
      読み手が引き算して合わない(2026-09-02 呼び出し元の指示)。**内訳だけを刷る。**
    ⭐ 差の分け方: ②−① を「抜きの中で盛土をやめたぶん」と「**抜きの縁に新しく出る法面**」に、
      ③−② を「池(床と岸)」と「築山」に分ける。四つの合計が ③−① に一致する(検査が見る)。"""
    key = id(d)
    if key in _BRK:
        return _BRK[key]
    import copy
    base = copy.deepcopy(d)
    for t9 in base["terraces"]:
        t9.pop("holes", None); t9.pop("keeps", None)
    for g9 in base["gardens"]:
        g9.pop("migiwa", None); g9.pop("tsukiyama", None)
    hol = copy.deepcopy(d)
    for g9 in hol["gardens"]:
        g9.pop("migiwa", None); g9.pop("tsukiyama", None)
    # ⚠ **キャッシュを差す前に本体で必ず一度作る。**None を焼き付けると in_parcel が
    #   TypeError で落ち、main の呼び順に依存する時限爆弾になる(2026-09-02 検図 K072)。
    _dem_at(d, 0, 0); _world_at(d, 0, 0); in_parcel(d, 0, 0)
    for x9 in (base, hol):                    # DEM の読み直しを避けてキャッシュを差す
        _DEM[id(x9)] = _DEM[id(d)]
        _WLD[id(x9)] = _WLD[id(d)]
        _PIN[id(x9)] = _PIN[id(d)]
    K = d["const"]["ken"]
    cell = (ter["step"] * K) ** 2
    holes = [hp for t9 in d["terraces"] for hp in tholes(t9)]
    mnd = mounds_of(d)
    # ⛔ **`holeEdge`(抜きの縁に新しく出る法面)は 2026-09-02 に消した** — 恒等的に 0 で、
    #   その項を見る検査は永久に沈黙していた。残っている量は `holeLeft`(抜きの中に残る盛土)。
    o = {"holeIn": 0.0, "holeLeft": 0.0, "pond": 0.0, "mound": 0.0, "total": 0.0}
    per = collections.OrderedDict()
    hnm = [(hh["label"], [(a, b) for a, b in hh["poly"]])
           for t9 in d["terraces"] for hh in (t9.get("holes") or [])]
    for lb9, _hp in hnm:
        per[lb9] = {"m3": 0.0, "rectKen": 0.0, "usedKen": 0.0,
                    "left": 0.0, "cells": 0, "leftCells": 0}
    for lb9, hp in hnm:
        per[lb9]["rectKen"] = _ring_area(hp)
        for t9 in d["terraces"]:
            per[lb9]["usedKen"] += _ring_area(clip_ring(tpoly(t9), hp))
    for jv in range(ter["nv"]):
        for iu in range(ter["nu"]):
            nat = ter["h"][jv][iu]
            if nat is None:
                continue
            uu = ter["u0"] + iu * ter["step"]; vv = ter["v0"] + jv * ter["step"]
            yb = graded_y(base, uu, vv, nat)
            yh = graded_y(hol, uu, vv, nat)
            yf = graded_y(d, uu, vv, nat)
            if yb is None or yh is None or yf is None:
                continue
            o["total"] += (yf - yb) * cell     # ⛔ 分類と**別に**独立して積む(恒真にしない)
            hit9 = next((lb9 for lb9, hp in hnm if _ring_in(hp, uu, vv)), None)
            dh = (yh - yb) * cell
            if abs(dh) > 1e-9:
                if hit9:
                    o["holeIn"] += dh
                    per[hit9]["m3"] += dh
                # ⛔ 抜きの外は holeIn に入らない(恒等ゼロの項を作らない)
            # ⭐ **抜きの中に残る盛土。**平坦化をやめても、縁からの法面が抜きの中へ入り込むぶんは
            #   埋め立てが残る。⛔ 従前の「抜きの縁に新しく出る法面」は**恒等的に 0**で、
            #   検査が永久に沈黙していた(2026-09-02 検図 K059)。
            if hit9:
                left = max(0.0, yh - nat) * cell
                if left > 0:
                    o["holeLeft"] += left
                    per[hit9]["left"] += left
                    per[hit9]["leftCells"] += 1
                per[hit9]["cells"] += 1
            dg = (yf - yh) * cell
            if abs(dg) > 1e-9:
                if any(_ell_r(ts9, uu, vv) <= 1.0 for _g9, ts9 in mnd):
                    o["mound"] += dg
                else:
                    o["pond"] += dg
    o["sum"] = o["total"]
    o["per"] = per
    _BRK[key] = o
    return o


def niwa_earth(d, ter):
    """庭の土工の内訳(池の床/岸の摺り付け/築山ごと)。**江戸期の復元地盤に対して**測る。"""
    g, mg, ring = pond_of(d)
    K = d["const"]["ken"]
    cell = (ter["step"] * K) ** 2
    o = {"bed": 0.0, "bank": 0.0, "mounds": []}
    md = [(gg, ts, 0.0) for gg, ts in mounds_of(d)]
    acc = [0.0] * len(md)
    for jv in range(ter["nv"]):
        for iu in range(ter["nu"]):
            uu = ter["u0"] + iu * ter["step"]; vv = ter["v0"] + jv * ter["step"]
            nat = ter["h"][jv][iu]
            if nat is None:
                continue
            hit = False
            for k9, (gg, ts, _z) in enumerate(md):
                if _ell_r(ts, uu, vv) <= 1.0:
                    acc[k9] += max(0.0, niwa_y(d, uu, vv, nat) - nat) * cell
                    hit = True
                    break
            if hit or not ring:
                continue
            dd = sashizu_lib.poly_edge_dist(ring, uu, vv)
            y9 = niwa_y(d, uu, vv, nat)
            if y9 is None:
                continue
            if _ring_in(ring, uu, vv):
                o["bed"] += max(0.0, nat - y9) * cell
            elif dd < mg["bankRun"]:
                o["bank"] += max(0.0, nat - y9) * cell
    o["mounds"] = [(gg, ts, acc[k9]) for k9, (gg, ts, _z) in enumerate(md)]
    o["dig"] = o["bed"] + o["bank"]
    o["fill"] = sum(x[2] for x in o["mounds"])
    o["surplus"] = o["dig"] - o["fill"]
    return o


def shakkei_metrics(d):
    """借景の実測(視点から溜池まで)。⛔ 宣言でなく地盤を歩いて測る。"""
    gm = gardens_by(d).get("NiwaMiharashi")
    if not gm or not gm.get("shakkei"):
        return None
    sk = gm["shakkei"]
    mk = next((m for m in (gm.get("mikoro") or []) if m.get("no") == 8), (gm.get("mikoro") or [None])[0])
    if not mk:
        return None
    K = d["const"]["ken"]
    prof = []
    v9 = mk["v"]
    edgeM = None
    # ⛔ **区画界を跨いで標本しない**(2026-09-03 庭方4巡目 K157)。
    #   ⚠ ここは `_world_at`(区画の外=近代の地面)で歩いていたため、区画界のセルに
    #     外の 9.10 が混ざって 10.28 になり、**同じ点を其十二は 11.11** と読んでいた。
    #     視線を切る所・見えはじめる距離・死角・窓の樹高の上限が二枚の値で割れていた。
    #   ⭕ 江戸期の復元地盤 `_dem_at`(区画でクリップ)へ揃え、**区画の中で止める**。
    vlast = None
    while v9 < mk["v"] + 100.0:
        if in_parcel(d, mk["u"], v9):
            y9 = _dem_at(d, mk["u"], v9)
            if y9 is not None:
                prof.append((round((v9 - mk["v"]) * K, 1), round(y9, 2)))
                vlast = v9
        elif edgeM is None and v9 > mk["v"] + 1.0:
            edgeM = (v9 - mk["v"]) * K          # 区画の西端(溜池の堤)まで
        v9 += 1.0
    # ⛔ **溜池の水面は地形DEMに無い**(DEM は堤と池底の地面)。水面は設計値 `waterY`。
    #   視線を最も制約するのは、視点から見て**傾きが最大**の地点(=自分の堤の天端)で、
    #   そこを掠めた線が水面に達する距離から先が見える。手前は死角。
    # ⛔ **汀の柵も遮蔽物に入れる**(2026-09-02 庭方) — 柵は区画界に立つので、
    #   水面が見えはじめる距離を押し出す。⚠ 入れないと死角を過少に出す。
    # ⭕ 柵は**区画内の最終標本**の上に立てる(⛔ 区画の外の標本に足さない)。
    sh9 = sk.get("sakuH")
    if sh9 and prof:
        s9, y9 = prof[-1]
        prof[-1] = (s9, round(y9 + sh9, 2))
    lim = None
    for s9, y9 in prof:
        if s9 < 2.0 or (edgeM and s9 > edgeM):
            continue                            # ⚠ **自分の側だけ**を見る(対岸は水面を隠さない)
        m9 = (y9 - mk["eyeY"]) / s9
        if lim is None or m9 > lim[0]:
            lim = (m9, s9, y9)
    seeFrom = None
    if lim and lim[0] < 0:
        seeFrom = (sk["waterY"] - mk["eyeY"]) / lim[0]
    # ⛔ **同じ一点を三つの名で呼ばない**(2026-09-03 庭方4巡目 K160・K099 の再発)。
    #   名は其十二(`nishi.mado.crestKind`)と同じ出どころから刷る。
    ck = ((d.get("nishi") or {}).get("mado") or {}).get("crestKind") or "視線を切る所"
    return {"mk": mk, "prof": prof, "edgeM": edgeM, "crestKind": ck,
            "drop": mk["eyeY"] - sk["waterY"],
            "crestM": lim[1] if lim else None, "crestY": lim[2] if lim else None,
            "seeFromM": seeFrom, "blindM": (seeFrom - edgeM) if (seeFrom and edgeM) else None,
            "sk": sk}


# ---------------------------------------------------------------- 庭の図版
NIWA_COL = {"kansho": "var(--niwa)", "shirasu": "var(--shirasu)",
            "sagyo": "var(--ink-lo)", "jurin": "#B9C7A4"}
MARU = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭"


def _clip(pr):
    """図版の枠の外を切る。⚠ 付けないと段や区画の多角形が枠の外へ何百pxも溢れる
    (2026-08-23 検図で御殿平面に入れたのと同じ手当て)。"""
    _SVN[0] = _SVN[0]
    cid = "np%d" % _SVN[0]
    return ('<defs><clipPath id="%s"><rect x="0" y="0" width="%.1f" height="%.1f"/></clipPath></defs>'
            '<g clip-path="url(#%s)">' % (cid, pr.W, pr.H, cid))


def _base_plan(d, pr, g, note=""):
    """庭の図版の下地(段・抜き・区画・棟・付属屋・結界塀)。"""
    gr = RGrid(d)
    out = [_clip(pr)]
    P = [gr.L(x, z) for x, z in d["polygon"]]
    out.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.85"/>'
               % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    for t in d["terraces"]:
        out.append(pr.poly(tpoly(t), fill=dan_color(d, t["y"]), op=1.0))
        for hp in tholes(t):
            out.append(pr.poly(hp, fill=_pat(), stroke="var(--dim)", sw=0.8, dash="4 3"))
        for kp in tkeeps(t):
            out.append(pr.poly(kp, fill=dan_color(d, t["y"]), stroke="none", op=1.0))
    ring = " ".join("L %.1f %.1f" % (pr.X(u), pr.Y(v)) for u, v in P)
    out.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z %s" fill="var(--paper2)" fill-rule="evenodd"/>'
               % (pr.W + 20, pr.H + 20, "M" + ring[1:] + " Z"))
    out.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
               % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    for n in d["gardens"]:
        col = NIWA_COL.get(n.get("kind"), "var(--niwa)")
        for r9 in (n.get("polys") or []):
            out.append(pr.poly([(a, b) for a, b in r9], fill=col,
                               stroke="var(--ink)", sw=0.5, op=0.92 if n is g else 0.55))
    for l in d["links"]:
        out.append(pr.rect(l["u0"], l["v0"], l["u1"], l["v1"], fill="var(--roka)"))
    for m in d["munes"]:
        out.append(pr.rect(m["u0"], m["v0"], m["u1"], m["v1"],
                           fill="var(--ink-mid)", stroke="var(--ink)", sw=1.0))
    for sv in d["service"]:
        out.append(pr.rect(sv["u0"], sv["v0"], sv["u1"], sv["v1"],
                           fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
    for w in d.get("kekkai", []):
        a, b = w["a"], w["b"]
        out.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]), "var(--hei)", 3.0, cap="butt"))
        gp = w.get("gap")
        if gp:
            if gp["axis"] == "u":
                out.append(LN(pr.X(gp["from"]), pr.Y(a[1]), pr.X(gp["to"]), pr.Y(a[1]),
                              "var(--shu)", 3.4))
            else:
                out.append(LN(pr.X(a[0]), pr.Y(gp["from"]), pr.X(a[0]), pr.Y(gp["to"]),
                              "var(--shu)", 3.4))
    for rl in auto_rails(d):
        out.append('<polyline points="%s" fill="none" stroke="var(--take)" stroke-width="2.2" '
                   'stroke-dasharray="2 4"/>'
                   % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in rl["pts"]))
    for w in d.get("wells", []):
        out.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="var(--paper)" stroke="var(--ink)" '
                   'stroke-width="1.4"/>' % (pr.X(w["u"]), pr.Y(w["v"])))
    return out


def _stone(pr, u, v, rm, K, fill="var(--ishi)", op=0.95):
    """`rm` は石の**長軸**[m]。⛔ 半径として渡さない(2026-09-02 庭方: 倍の大きさに描いていた)。"""
    return ('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="var(--ink)" '
            'stroke-width="0.5" opacity="%.2f"/>'
            % (pr.X(u), pr.Y(v), max(1.6, pr.L(rm / 2.0 / K)), fill, op))


def _lantern(pr, u, v):
    x, y = pr.X(u), pr.Y(v)
    return ('<g><circle cx="%.1f" cy="%.1f" r="4.2" fill="none" stroke="var(--ink)" stroke-width="1.4"/>'
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--ink)" stroke-width="1.4"/>'
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--ink)" stroke-width="1.4"/></g>'
            % (x, y, x - 6, y, x + 6, y, x, y - 6, x, y + 6))


def _tree(pr, u, v, r=5.0, col="var(--take)"):
    return ('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" fill-opacity="0.35" '
            'stroke="%s" stroke-width="1.0"/>' % (pr.X(u), pr.Y(v), r, col, col))


def pond_svg(d):
    """**書院の泉水 詳細図。**汀線は実装と同じ Chaikin×2 を掛けて描く。"""
    g, mg, ring = pond_of(d)
    K = d["const"]["ken"]
    pr = LProj(-2.0, 22.0, 60.0, 82.0, 900.0)
    o = _sv(pr.W, pr.H, "岡部筑前守上屋敷 書院の泉水")
    o += _base_plan(d, pr, g)
    sm = ring                     # `pond_of` が返す時点で平滑済み(=実際に掘る形)
    rw = pond_raw(d)              # 生の16点(設計値)は細い破線で重ねる
    # 岸の摺り付けの外縁(汀から bankRun 外へ。頂点法線でオフセットする)
    bk = []
    for i9 in range(len(sm)):
        a9 = sm[i9 - 1]; b9 = sm[i9]; c9 = sm[(i9 + 1) % len(sm)]
        nx9 = (b9[1] - a9[1]) + (c9[1] - b9[1])
        ny9 = -((b9[0] - a9[0]) + (c9[0] - b9[0]))
        L9 = math.hypot(nx9, ny9) or 1.0
        bk.append((b9[0] + nx9 / L9 * mg["bankRun"], b9[1] + ny9 / L9 * mg["bankRun"]))
    if _ring_area(bk) < _ring_area(sm):
        bk = [(2 * b9[0] - q9[0], 2 * b9[1] - q9[1]) for b9, q9 in zip(sm, bk)]
    o.append('<polygon points="%s" fill="none" stroke="var(--cut2)" stroke-width="1.2" '
             'stroke-dasharray="5 4"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in bk))
    o.append(T(pr.X(bk[9][0]) - 6, pr.Y(bk[9][1]) - 4, "岸の摺り付けの外縁", "jo", "end"))
    o.append(pr.poly(sm, fill="var(--ike)", stroke="var(--hei)", sw=1.4, op=0.95))
    o.append(pr.poly(rw, fill="none", stroke="var(--dim)", sw=0.8, dash="4 3"))
    for i9, (ru, rv) in enumerate(rw):
        o.append('<circle cx="%.1f" cy="%.1f" r="1.8" fill="var(--dim)"/>' % (pr.X(ru), pr.Y(rv)))
        o.append(T(pr.X(ru) + 4, pr.Y(rv) - 3, "%d" % (i9 + 1), "jo", None, 7.5))
    # 州浜
    for sh in (g.get("suhama") or []):
        o.append(pr.rect(sh["u0"], sh["v0"], sh["u1"], sh["v1"], fill=_pat(),
                         stroke="var(--dim)", sw=0.8, dash="3 3"))
        o.append(T(pr.X((sh["u0"] + sh["u1"]) / 2), pr.Y(sh["v1"]) + 11, "州浜", "jo", "middle"))
    # 石組護岸(汀線のうち範囲に入る区間を太く)
    for gg in (g.get("gogan") or []):
        if gg.get("rest"):
            continue                       # 土羽=残りを受ける形式。区間は下でまとめて描く
        seg = [(u, v) for u, v in sm if gg["u0"] - 0.3 <= u <= gg["u1"] + 0.3
               and gg["v0"] - 0.3 <= v <= gg["v1"] + 0.3]
        if len(seg) > 1:
            o.append('<polyline points="%s" fill="none" stroke="var(--ishi)" stroke-width="4.2" '
                     'stroke-linecap="round" opacity="0.9"/>'
                     % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in seg))
            o.append(T(pr.X(seg[len(seg) // 2][0]) - 8, pr.Y(seg[len(seg) // 2][1]),
                       "石組護岸", "jo", "end"))
        ar = gg.get("araiso")
        if ar:
            o.append(_stone(pr, ar["u"], ar["v"], 0.9, K, "var(--hei)"))
            o.append(T(pr.X(ar["u"]) - 7, pr.Y(ar["v"]) - 7, "荒磯の立石", "jo", "end"))
    # 土羽(石組・州浜・乱杭が受け持たない**残り**)
    cov = gogan_cover(d)
    if cov and cov["rest"]:
        for a9, b9 in cov["rest"]:
            seg = sm[a9:b9 + 1] if b9 >= a9 else sm[a9:] + sm[:b9 + 1]
            if len(seg) > 1:
                o.append('<polyline points="%s" fill="none" stroke="var(--take)" stroke-width="3.0" '
                         'stroke-linecap="round" opacity="0.8"/>'
                         % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in seg))
        m9 = sm[cov["rest"][0][0]]
        o.append(T(pr.X(m9[0]) - 7, pr.Y(m9[1]) + 10, "土羽(芝付)", "jo", "end"))
    # 乱杭
    for rg in (g.get("rangui") or []):
        arc = ring_arc(sm, rg["a"], rg["b"])
        L9 = sum(math.hypot(b9[0] - a9[0], b9[1] - a9[1]) for a9, b9 in zip(arc, arc[1:])) * K
        n9 = int(round(L9 / rg["pitch"])) + 1
        for i9 in range(n9):
            s9 = L9 * i9 / float(max(n9 - 1, 1)) / K
            acc = 0.0
            for a9, b9 in zip(arc, arc[1:]):
                seg = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
                if acc + seg >= s9:
                    t9 = (s9 - acc) / (seg or 1e-9)
                    o.append('<circle cx="%.1f" cy="%.1f" r="1.1" fill="var(--nagaya)"/>'
                             % (pr.X(a9[0] + (b9[0] - a9[0]) * t9),
                                pr.Y(a9[1] + (b9[1] - a9[1]) * t9)))
                    break
                acc += seg
        o.append(T(pr.X(rg["b"][0]) - 6, pr.Y(rg["b"][1]), "乱杭 %d本" % n9, "jo", "end"))
    # 中島
    for nj in (g.get("nakajima") or []):
        pol = [(a9, b9) for a9, b9 in (nj.get("poly") or [])]
        if pol:
            o.append(pr.poly(pol, fill="var(--tsuki)", stroke="var(--ink)", sw=1.0))
            for i9 in range(nj["stones"]):
                t9 = len(pol) * (i9 + 0.28 * math.sin(i9 * 2.1)) / nj["stones"]
                a9 = pol[int(t9) % len(pol)]; b9 = pol[(int(t9) + 1) % len(pol)]
                f9 = t9 - int(t9)
                o.append(_stone(pr, a9[0] + (b9[0] - a9[0]) * f9, a9[1] + (b9[1] - a9[1]) * f9,
                                nj["stoneRMin"] + (nj["stoneRMax"] - nj["stoneRMin"])
                                * (0.5 + 0.5 * math.sin(i9 * 1.7)), K))
            ar = nj.get("araiso")
            if ar and ar.get("at") is not None and ar["at"] < len(pol):
                o.append(_stone(pr, pol[ar["at"]][0], pol[ar["at"]][1], ar["h"], K, "var(--hei)"))
        ta = nj.get("treeAt") or [nj["u"], nj["v"]]
        o.append(_tree(pr, ta[0], ta[1], 6.0))
        o.append(T(pr.X(nj["u"]), pr.Y(nj["v"]) - 12, "中島(磯島)", "jo", "middle"))
    # 岩島
    for ij in (g.get("iwajima") or []):
        o.append(_stone(pr, ij["u"], ij["v"], ij["hMain"] * 0.5, K, "var(--hei)"))
        o.append(_stone(pr, ij["u"] + 0.35, ij["v"] + 0.25, ij["hShoulder"] * 0.5, K, "var(--hei)"))
        o.append(T(pr.X(ij["u"]) + 9, pr.Y(ij["v"]) + 4, "岩島", "jo"))
    # 沢飛石(渡り)
    for sw in (g.get("sawatobi") or []):
        pts9 = [(a, b) for a, b in sw["pts"]]
        for i9, (su, sv) in enumerate(pts9):
            rr = sw["rMin"] + (sw["rMax"] - sw["rMin"]) * (0.5 + 0.5 * math.sin(i9 * 1.9))
            # ⛔ 等間隔にしない(2026-09-03 庭方4巡目 K168)。長軸は**渡りと直交**に置く。
            o.append(_stone(pr, su, sv, rr, K, "var(--ishi)"))
        for q9 in (pts9[0], pts9[-1]):
            o.append(_stone(pr, q9[0], q9[1], sw["tamotoMax"], K, "var(--hei)", 0.85))
        o.append(T(pr.X((pts9[0][0] + pts9[-1][0]) / 2), pr.Y(pts9[0][1]) - 10,
                   "沢飛石 %d枚" % len(pts9), "jo", "middle"))
    # 景石・灯籠・沓脱
    for st in (g.get("ishigumi") or []):
        if st.get("u") is None:
            continue
        o.append(_stone(pr, st["u"], st["v"], (st.get("h") or 0.6) * 0.5, K, "var(--hei)"))
        o.append(T(pr.X(st["u"]) - 6, pr.Y(st["v"]) - 6, st["label"], "jo", "end"))
    for tr in (g.get("toro") or []):
        o.append(_lantern(pr, tr["u"], tr["v"]))
        o.append(T(pr.X(tr["u"]) + 8, pr.Y(tr["v"]) + 10, "雪見灯籠", "jo"))
    for kt in (g.get("kutsunugi") or []):
        o.append(pr.rect(kt["u"] - kt["W"] / 2 / K, kt["v"] - kt["L"] / 2 / K,
                         kt["u"] + kt["W"] / 2 / K, kt["v"] + kt["L"] / 2 / K,
                         fill="var(--ishi)", stroke="var(--ink)", sw=0.8))
        o.append(T(pr.X(kt["u"]) - 8, pr.Y(kt["v"]) + 4, "沓脱石", "jo", "end"))
    # 飛石(筋の上に芯々で並べる — 石の位置は従属値)
    for tb in (g.get("tobiishi") or []):
        if not isinstance(tb.get("pts"), list):
            continue
        pts = [(a, b) for a, b in tb["pts"]]
        segs = [(a, b, math.hypot(b[0] - a[0], b[1] - a[1])) for a, b in zip(pts, pts[1:])]
        tot = sum(x[2] for x in segs)
        s9 = 0.0
        i9 = 0
        while s9 <= tot:
            acc = 0.0
            for a, b, L9 in segs:
                if acc + L9 >= s9:
                    t9 = (s9 - acc) / L9
                    o.append(_stone(pr, a[0] + (b[0] - a[0]) * t9, a[1] + (b[1] - a[1]) * t9,
                                    0.24, K, "var(--ishi)"))
                    break
                acc += L9
            p9 = tb["pitchMin"] + (tb["pitchMax"] - tb["pitchMin"]) * (0.5 + 0.5 * math.sin(i9 * 1.3))
            s9 += p9 / K
            i9 += 1
        o.append(T(pr.X(pts[1][0]) + 7, pr.Y(pts[1][1]) - 5, "飛石", "jo"))
    # 園路
    for en in (g.get("enro") or []):
        pts9 = [(a, b) for a, b in en["pts"]]
        if en.get("close") is not None:
            pts9 = pts9 + [pts9[en["close"]]]          # 終点は指定の点へ閉じる
        o.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="%.1f" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.55"/>'
                 % (" ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in pts9),
                    max(3.0, pr.L(en["w"] / K))))
    # 井戸の四つ目垣
    gk9 = ((g.get("mizu") or {}).get("gensen") or {}).get("idoKaki")
    if gk9:
        o.append(pr.rect(gk9["u0"], gk9["v0"], gk9["u1"], gk9["v1"],
                         fill="none", stroke="var(--take)", sw=1.6, dash="3 3"))
    # 築山A(等高線)
    for ts in (g.get("tsukiyama") or []):
        for f9 in (1.0, 0.66, 0.33):
            o.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" fill-opacity="%.2f" '
                     'stroke="var(--dim)" stroke-width="0.8"/>'
                     % (pr.X(ts["u"]), pr.Y(ts["v"]), pr.L(ts["dU"] / 2 * f9), pr.L(ts["dV"] / 2 * f9),
                        "var(--tsuki)", 0.30 if f9 == 1.0 else 0.20))
        o.append(T(pr.X(ts["u"]), pr.Y(ts["v"]), ts["label"], "anS2", "middle"))
    # 水の系統
    mz = g.get("mizu") or {}
    gs = mz.get("gensen") or {}
    wl = next((w for w in d.get("wells", []) if w["name"] == (gs.get("ido") or {}).get("ref")), None)
    mo = gs.get("mizuochi")
    if wl and mo:
        o.append(LN(pr.X(wl["u"]), pr.Y(wl["v"]), pr.X(mo["u"]), pr.Y(mo["v"]),
                    "var(--cut4)", 2.0, dash="6 3"))
        o.append(T(pr.X((wl["u"] + mo["u"]) / 2), pr.Y((wl["v"] + mo["v"]) / 2) - 5, "掛樋", "jo", "middle"))
        o.append(T(pr.X(wl["u"]) + 7, pr.Y(wl["v"]) + 4, "井戸", "jo"))
        o.append(_stone(pr, mo["u"], mo["v"], 0.5, K, "var(--ishi)"))
        o.append(T(pr.X(mo["u"]) - 6, pr.Y(mo["v"]) + 12, "水落", "jo", "end"))
    ms = mz.get("mizushiri") or {}
    hg = ms.get("higuchi"); ak = ms.get("ankyo")
    if hg and ak:
        o.append(LN(pr.X(hg["u"]), pr.Y(hg["v"]), pr.X(ak["to"][0]), pr.Y(ak["to"][1]),
                    "var(--cut3)", 2.0, dash="2 3"))
        o.append(T(pr.X(hg["u"]) + 6, pr.Y(hg["v"]) - 6, "水尻の樋口→暗渠", "jo"))
    sd = mz.get("sokodoi")
    if sd:
        o.append(LN(pr.X(hg["u"] if hg else 13.0), pr.Y(hg["v"] if hg else 69.0),
                    pr.X(sd["to"][0]), pr.Y(sd["to"][1]), "var(--shu)", 1.4, dash="1 4"))
        o.append(T(pr.X(sd["to"][0]) + 5, pr.Y(sd["to"][1]) + 10, "底樋(池干し)", "jo"))
    # 見所と視線
    cen = _cen(ring)
    for mk in (g.get("mikoro") or []):
        tg = cen
        if mk.get("target") not in (None, "migiwa", "self"):
            for _g2, ts2 in mounds_of(d):
                if ts2["name"] == mk["target"]:
                    tg = (ts2["u"], ts2["v"])
        o.append(LN(pr.X(mk["u"]), pr.Y(mk["v"]), pr.X(tg[0]), pr.Y(tg[1]),
                    "var(--shu)", 0.8, dash="7 5", op=0.75))
        o.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (pr.X(mk["u"]), pr.Y(mk["v"])))
        o.append(T(pr.X(mk["u"]), pr.Y(mk["v"]) + 4, MARU[mk["no"] - 1], "sr", "middle", 10.0, "#fff"))
    o.append(T(4, 15, "グリッド座標(u=北+ / v=西+)。**上=東 / 左=北 / 下=西 / 右=南**。"
               "汀線は実装と同じ Chaikin×2 を掛けて描いた(検算は平滑化前の設計多角形で出す)", "anS"))
    o.append("</g>")
    o.append("</svg>")
    return "\n".join(o)


def _cen(ring):
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))


def niwa_plan_svg(d):
    """**主面の割り当て。**12区画と、平坦化しない5区画(抜き)を1枚で読む。"""
    pr = LProj(-42.0, 27.0, 42.0, 112.0, 900.0)
    o = _sv(pr.W, pr.H, "岡部筑前守上屋敷 庭の割り当て")
    g0, mg0, ring0 = pond_of(d)
    o += _base_plan(d, pr, None)
    if ring0:
        o.append(pr.poly(chaikin(ring0, mg0.get("smooth", 2)), fill="var(--ike)",
                         stroke="var(--hei)", sw=1.2))
    for _g, ts in mounds_of(d):
        o.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="var(--tsuki)" '
                 'fill-opacity="0.55" stroke="var(--dim)" stroke-width="0.9"/>'
                 % (pr.X(ts["u"]), pr.Y(ts["v"]), pr.L(ts["dU"] / 2), pr.L(ts["dV"] / 2)))
    for g in d["gardens"]:
        for en in (g.get("enro") or []):
            o.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="2.4" '
                     'opacity="0.6"/>'
                     % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in en["pts"]))
        for tr in (g.get("toro") or []):
            o.append(_lantern(pr, tr["u"], tr["v"]))
        for sk in (g.get("shokusai") or []):
            for q in (sk.get("pts") or []):
                o.append(_tree(pr, q[0], q[1], 4.0))
        for ys in (g.get("yashiro") or []):
            c9 = _yashiro_pos(d, ys)
            if not c9:
                continue
            o.append(LN(pr.X(ys["torii"]["u"]), pr.Y(ys["torii"]["v"]),
                        pr.X(c9[0]), pr.Y(c9[1]), "var(--shu)", 1.6))
            kk9 = ys.get("kaki")
            if kk9 and "u0" in kk9:
                o.append(pr.rect(kk9["u0"], kk9["v0"], kk9["u1"], kk9["v1"],
                                 fill="none", stroke="var(--take)", sw=1.4, dash="3 3"))
            o.append(T(pr.X(ys["torii"]["u"]) - 5, pr.Y(ys["torii"]["v"]) + 4, "鳥居", "jo", "end"))
        rs = g.get("rects") or []
        if rs:
            big = max(rs, key=lambda q: (q[2] - q[0]) * (q[3] - q[1]))
            o.append(T((pr.X(big[0]) + pr.X(big[2])) / 2, (pr.Y(big[1]) + pr.Y(big[3])) / 2 + 4,
                       g["label"], "rmS", "middle",
                       fit(g["label"], pr.L(big[2] - big[0]) + 20, 12.0)))
        for mk in (g.get("mikoro") or []):
            o.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>'
                     % (pr.X(mk["u"]), pr.Y(mk["v"])))
            o.append(T(pr.X(mk["u"]), pr.Y(mk["v"]) + 4, MARU[mk["no"] - 1], "sr", "middle", 10.0, "#fff"))
    for w in d.get("kekkai", []):
        a, b = w["a"], w["b"]
        o.append(T(pr.X((a[0] + b[0]) / 2), pr.Y((a[1] + b[1]) / 2) - 4, w["name"], "jo", "middle"))
    o.append(T(4, 15, "グリッド座標(u=北+ / v=西+)。**上=東 / 左=北 / 下=西 / 右=南**。"
               "網掛け=**平坦化しない区画**(段の抜き)／ 太い紺=結界のし塀・朱=中門と木戸", "anS"))
    o.append("</g>")
    o.append("</svg>")
    return "\n".join(o)


def okuniwa_svg(d):
    """奥庭(築山Bと園路)。"""
    g = gardens_by(d).get("NiwaOku")
    pr = LProj(-22.0, -3.0, 78.0, 111.0, 760.0)
    o = _sv(pr.W, pr.H, "岡部筑前守上屋敷 奥庭")
    o += _base_plan(d, pr, g)
    K = d["const"]["ken"]
    for zn in (g.get("zones") or []):
        o.append(LN(pr.X(g["u0"]), pr.Y(zn["v1"]), pr.X(g["u1"]), pr.Y(zn["v1"]),
                    "var(--dim)", 0.8, dash="3 4"))
        o.append(T((pr.X(g["u0"]) + pr.X(g["u1"])) / 2,
                   (pr.Y(zn["v0"]) + pr.Y(zn["v1"])) / 2, zn["label"], "anS2", "middle"))
    for ts in (g.get("tsukiyama") or []):
        for f9 in (1.0, 0.66, 0.33):
            o.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="var(--tsuki)" '
                     'fill-opacity="%.2f" stroke="var(--dim)" stroke-width="0.9"/>'
                     % (pr.X(ts["u"]), pr.Y(ts["v"]), pr.L(ts["dU"] / 2 * f9), pr.L(ts["dV"] / 2 * f9),
                        0.30 if f9 == 1.0 else 0.20))
        o.append(T(pr.X(ts["u"]), pr.Y(ts["v"]), ts["label"], "anS2", "middle"))
        for i9 in range(3):
            o.append(_tree(pr, ts["u"] + (i9 - 1) * 0.8, ts["v"] + (i9 - 1) * 1.1, 6.0))
    for en in (g.get("enro") or []):
        o.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="%.1f" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.55"/>'
                 % (" ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in en["pts"]),
                    max(3.0, pr.L(en["w"] / K))))
    for st in (g.get("ishigumi") or []):          # ⭐ K042: 三石が json に確定済みなのに図に無かった
        if st.get("u") is None:
            continue
        o.append(_stone(pr, st["u"], st["v"], (st.get("h") or 0.6) * 0.5, K, "var(--hei)"))
        o.append(T(pr.X(st["u"]) - 6, pr.Y(st["v"]) - 6, st["label"], "jo", "end"))
    for kt in (g.get("kutsunugi") or []):
        o.append(pr.rect(kt["u"] - kt["W"] / 2 / K, kt["v"] - kt["L"] / 2 / K,
                         kt["u"] + kt["W"] / 2 / K, kt["v"] + kt["L"] / 2 / K,
                         fill="var(--ishi)", stroke="var(--ink)", sw=0.8))
    for tr in (g.get("toro") or []):
        o.append(_lantern(pr, tr["u"], tr["v"]))
        o.append(T(pr.X(tr["u"]) + 8, pr.Y(tr["v"]) + 10, "雪見灯籠", "jo"))
    for sk in (g.get("shokusai") or []):
        if not sk.get("screen"):
            continue
        o.append(pr.rect(sk["u0"], sk["v0"], sk["u1"], sk["v1"], fill="var(--take)",
                         stroke="var(--take)", sw=0.8, op=0.25))
        o.append(T((pr.X(sk["u0"]) + pr.X(sk["u1"])) / 2, (pr.Y(sk["v0"]) + pr.Y(sk["v1"])) / 2 + 4,
                   "クロマツの疎林(見隠れ)", "jo", "middle"))
    for mk in (g.get("mikoro") or []):
        tgt = next((t for _g2, t in mounds_of(d) if t["name"] == mk.get("target")), None)
        if tgt:
            o.append(LN(pr.X(mk["u"]), pr.Y(mk["v"]), pr.X(tgt["u"]), pr.Y(tgt["v"]),
                        "var(--shu)", 0.8, dash="7 5"))
        o.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (pr.X(mk["u"]), pr.Y(mk["v"])))
        o.append(T(pr.X(mk["u"]), pr.Y(mk["v"]) + 4, MARU[mk["no"] - 1], "sr", "middle", 10.0, "#fff"))
    o.append(T(4, 15, "グリッド座標。**上=東 / 左=北 / 下=西 / 右=南**", "anS"))
    o.append("</g>")
    o.append("</svg>")
    return "\n".join(o)


def shakkei_svg(d):
    """溜池の借景の縦断(視点から西へ)。"""
    sk = shakkei_metrics(d)
    if not sk:
        return ""
    W, H = 900.0, 300.0
    o = _sv(W, H, "岡部筑前守上屋敷 溜池の借景(縦断)")
    xs = [p[0] for p in sk["prof"]]
    x1 = max(sk["seeFromM"] or 0.0, max(xs)) + 12.0
    y0, y1 = 4.0, 28.0

    def X(s9):
        return 46.0 + (W - 60.0) * s9 / x1

    def Y(y9):
        return H - 34.0 - (H - 60.0) * (y9 - y0) / (y1 - y0)
    for y9 in range(int(y0), int(y1) + 1, 4):
        o.append(LN(X(0), Y(y9), X(x1), Y(y9), "var(--rule)", 0.6))
        o.append(T(40, Y(y9) + 4, "%d" % y9, "jo", "end"))
    o.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in sk["prof"]))
    wl = sk["sk"]["waterY"]
    o.append(R(X(sk["edgeM"] or 0), Y(wl), X(x1) - X(sk["edgeM"] or 0), Y(y0) - Y(wl),
               fill="var(--ike)", op=0.75))
    o.append(T(X((sk["edgeM"] or 0) + 20), Y(wl) - 6, "溜池の水面 %.2f" % wl, "anS2"))
    mk = sk["mk"]
    o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>' % (X(0), Y(mk["eyeY"])))
    o.append(T(X(0) + 6, Y(mk["eyeY"]) - 6, "%s(眼高 %.2f)" % (mk["label"], mk["eyeY"]), "anS2"))
    if sk["seeFromM"]:
        o.append(LN(X(0), Y(mk["eyeY"]), X(sk["seeFromM"]), Y(wl), "var(--shu)", 1.4, dash="7 4"))
        o.append(LN(X(sk["crestM"]), Y(y0), X(sk["crestM"]), Y(y1), "var(--dim)", 0.8, dash="3 3"))
        o.append(T(X(sk["crestM"]), Y(y1) - 6, "%s %.1fm 先 / %.2f"
                   % (sk["crestKind"], sk["crestM"], sk["crestY"]), "jo", "middle"))
        o.append(R(X(sk["edgeM"]), Y(wl), X(sk["seeFromM"]) - X(sk["edgeM"]), Y(y0) - Y(wl),
                   fill="var(--dim)", op=0.28))
        o.append(T((X(sk["edgeM"]) + X(sk["seeFromM"])) / 2, Y(wl) + 14,
                   "死角 %.0fm" % sk["blindM"], "jo", "middle"))
    # ⭕ **区画界から先は設計線**(2026-09-03 検図4巡目 K159 — 其十二と同じ作法に揃える)。
    N9 = d.get("nishi") or {}
    ts9 = N9.get("tsutsumi") or {}
    if sk["edgeM"] and ts9.get("y0") is not None:
        eM = sk["edgeM"]
        o.append(LN(X(eM), Y(y0), X(eM), Y(y1), "var(--shu)", 1.2, dash="4 3"))
        o.append(T(X(eM), Y(y1) - 6, "区画界(辺%s)" % (N9.get("saku") or {}).get("edge", ""),
                   "jo", "middle"))
        o.append(T(X(eM) + 5, Y(y1) + 8, "← 実測(江戸期の復元地盤)　設計線 →", "jo"))
        mg = ts9.get("mizugiwaM", 0.0)
        o.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="2.2" '
                 'stroke-dasharray="7 4"/>'
                 % " ".join("%.1f,%.1f" % (X(a), Y(b))
                            for a, b in ((eM, ts9["y0"]), (eM + mg, wl))))
        o.append(T(X(eM + mg / 2), Y((ts9["y0"] + wl) / 2) - 8,
                   "E 堤(設計線 1:%.1f)" % ts9.get("batter", 2.2), "jo", "middle"))
    o.append(T(46, H - 10, "水平[m](視点から西へ)／ 縦は標高[m]・**縦%.2f倍**"
               % _vexag(X, Y, 1.0), "anS2"))
    o.append("</svg>")
    return "\n".join(o)


def mizu_svg(d):
    """水の系統の縦断(水源 → 池 → 水尻 → 法尻の水路 → 街路溝)。"""
    g, mg, ring = pond_of(d)
    mz = (g or {}).get("mizu") or {}
    ms = mz.get("mizushiri") or {}
    if not ms:
        return ""
    K = d["const"]["ken"]
    pts = [(ms["higuchi"]["u"], ms["higuchi"]["v"], ms["higuchi"]["sill"], "樋口"),
           (ms["ankyo"]["to"][0], ms["ankyo"]["to"][1], ms["ankyo"]["toY"], "暗渠の出口")]
    for q in ms.get("mizo", []):
        pts.append((q[0], q[1], q[2], "落とし溝"))
    for q in ms.get("houjiri", []):
        pts.append((q[0], q[1], q[2], "法尻の水路"))
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]) * K)
    W, H = 900.0, 260.0
    o = _sv(W, H, "岡部筑前守上屋敷 水の系統(縦断)")
    x1 = acc[-1] + 8.0
    y0, y1 = 14.0, 26.0

    def X(s9):
        return 50.0 + (W - 66.0) * s9 / x1

    def Y(y9):
        return H - 34.0 - (H - 62.0) * (y9 - y0) / (y1 - y0)
    for y9 in range(int(y0), int(y1) + 1, 2):
        o.append(LN(X(0), Y(y9), X(x1), Y(y9), "var(--rule)", 0.6))
        o.append(T(44, Y(y9) + 4, "%d" % y9, "jo", "end"))
    o.append('<polyline points="%s" fill="none" stroke="var(--cut4)" stroke-width="2.0"/>'
             % " ".join("%.1f,%.1f" % (X(acc[i]), Y(pts[i][2])) for i in range(len(pts))))
    for i in range(len(pts)):
        o.append('<circle cx="%.1f" cy="%.1f" r="3" fill="var(--cut4)"/>' % (X(acc[i]), Y(pts[i][2])))
        o.append(T(X(acc[i]), Y(pts[i][2]) - 8,
                   "%s (%.1f,%.1f) %.2f" % (pts[i][3], pts[i][0], pts[i][1], pts[i][2]),
                   "jo", "middle", 8.5))
    o.append(T(50, H - 10, "水平[m]／ 縦は標高[m]。全落差と延長は下の表が算出する", "anS2"))
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- 庭の検査
# ⭐ **図で宣言した不変条件は必ず検査に落とす**(当家の作法)。
#   ⛔ 恒真にしない — 各検査は「わざと壊すと必ず件数が出る」ことを確かめてある(破壊試験)。
#
# **2026-09-03 の破壊試験(117件・すべて期待どおり)**
# ⛔ **「反応する」とだけ書かない — 壊す前と後の件数を並べる。**数が無い記録は偽になり得る。
#   ⚠ この作法にした途端、⛔ **偽の記録が4件見つかった**(前後が同じだったもの):
#     ・「結界を全部消す → 反応する」…… 実際は **1件 → 1件**。経路の指摘が1件出るだけで数が動かず、
#       ⛔ この一件が **27件を1巡隠した**(法面24・必須未達2・結界の穴1)。
#       ⭕ 「結界が1区間も無い」を1件として出す形に直した。
#     ・「法面を緩める → 抜きの中が埋まる」…… 割合の物差しでは **0件 → 0件**。総量の予算へ直した。
#     ・「石段が長屋門へ食い込む」…… 免除の条件式の綴りで**全ての石段の対が免除**されていた。
#     ・「表門の躯体を消す」…… 述語が「plan という欄があるか」だけで空でも通っていた。
#   ⛔ **前後の数が同じだったら、検査そのものを作り直す。**壊し方を変えて誤魔化さない。
#   ⭐ **適用範囲のある検査は「増える壊し方」と「増えない壊し方」の両方を置く**(⚠逆向き の行)。
#     見晴らしの視線の検査は**台の中だけ**が持ち場で、袖は「地面が視線より高いのが設計どおり」。
#     片側だけ試すと、範囲を広げすぎた検査が正しい設計を不合格として刷る事故に気づけない。
#   ⚠ **2026-09-02(西の地盤の直しのあと)に壊し方を4つ作り直した。**地盤が変われば
#     「何を壊せば鳴るか」も変わる。⛔ 前後が同じになった試験を残さない:
#     ・「西の法尻の土留めを消す」…… 24件→0件 だったのが **0件→0件**。
#       ⭕ これは検査の劣化ではなく**前提が消えた証拠**なので、⚠逆向き(増えないのが正)へ移した。
#     ・「主面を 2m 上げる」…… 江戸期の崖が急なので地山側で除外され **0件→0件**。
#       ⭕ batterCut を緩める / featherCap を縮める、へ差し替えた。
#     ・土留めの s を変える2件 …… **天端が全区間で地盤より下**なので、どの s でも
#       「前提が消えた」の枝が先に鳴って **1件→1件**。⛔ 反応したふりをせず**外した**。
#       ⭕ 代わりに「span を与えない(落差が測れない)」で wall_check を突く。
#       ⚠ s の枝は**裁定が下りて壁が正常な状態に戻るまで到達しない**。
#   ⚠ **2026-09-02(庭方の差替のあと)にもう1件作り直した。**
#     ・「木戸を窓の中へ移す」…… **0件→0件**。⛔ 検査の劣化ではなく
#       **規則そのものを廃した**ため(木戸は扇の軸上に置いて見所と兼ねるのが設計)。
#       ⭕ 「柵から離す」「見所を2箇所にする」へ差し替えた。
#   ⚠ **2026-09-02(庭方3巡目のあと)にさらに4つ作り直した。**
#     ⛔ どれも「検査の劣化」ではなく**壊す先が算出値へ移った**ことによる。
#     ・「帯の下端を下げる」…… 3件→3件。帯の境が `y0From`/`y1From` からの算出値に
#       なったので、⭕ **出どころ**を下げる形へ移した。
#     ・「蓮の帯を水面より上げる」…… 蓮は標高を持たない(`kind` が『水面』)ので
#       上げようがない。⭕ 「『地表』の別へ移す」へ差し替えた。
#     ・「林の下端を等間隔にする」…… 点数を9に直すと**素の指摘(13点)が消えて**
#       件数が動かなかった。⛔ 相殺に気づかず通しかけた。⭕ 点数を13のまま等間隔にする。
#     ・「窓の樹高の上限を半分にする」…… 上限が算出値になったので組み直しで戻る。
#       ⭕ 入力側(視線の余裕 1.0→4.0m)を壊す形へ移した。
#   ⚠ **2026-09-03(庭方4巡目のあと)にもう1つ作り直した。**
#     ・「窓の視線の余裕を広げる」…… 1件→1件。⛔ 検査の劣化ではなく、
#       **窓の松の丈が「その点の上限 −1.2m」の従属値になった**ので、上限を下げると
#       丈も一緒に下がって違反にならない(=設計どおり)。
#       ⭕ 「窓の中へ丈 6m の**固定の**植栽を置く」へ差し替えた。
#     ⭐ 従属値を増やすほど「入力を壊す」試験は効かなくなる。⭕ 代わりに
#       **往復試験(人が書き換えると鳴る)**が受け持つ形へ寄せる。
#   ⚠ **2026-09-03(⑦の直しと庭方4巡目の決定のあと)にもう1つ作り直した。**
#     ・「眼高を地盤より下げる」…… 0件→0件。⛔ **庭の見所の眼高も従属値になった**ため
#       (`eyeAbove` があれば地盤+それ / 無ければ `eyeYFix` の入力)。
#       ⭕ 「眼高の**入力**(`eyeYFix`)を下げる」へ移した。
#     ⭐ **同じ型が3巡続いている** — 従属値を増やすたびに、その値を直接壊す試験が死ぬ。
#       ⭕ 壊す先を**入力側**へ移し、従属であること自体は**往復試験**が見張る。
#   ⭐ **地盤を差し替える試験を1つ持つ**(json の変異では届かない層)。
#     ⚠ 2026-09-03 に「脚の中の段」を見る検査を足すまで、**末端の 25.6% の段は
#       脚の平均 7.3% に埋もれて 0件のまま**だった(庭方が目で見つけた)。
#   ⚠ **2026-09-03(考証3巡目・庭方4巡目・検図4巡目のあと)に2つ作り直した。**
#     ・「眼高の入力(`eyeYFix`)を下げる」…… 0件→0件。⛔ 入側の眼が
#       **基準身長からの従属値**になり `eyeYFix` が入力でなくなったため。
#       ⭕ 「御殿の床を −5.0m にする」(いまの入力)へ移した。
#     ・「法尻のススキを窓の中にも置けることにする」…… 1件→1件。
#       ⛔ 代表点を帯の**中ほど**(v150)に置いていて、窓の上限がまだ緩い所だった。
#       ⭕ 帯の中で**いちばん厳しい所**(v160・区画界寄り)で見る形に直した。
#   ⭐ **偽の記録を1件正した**(検図4巡目の指摘) — 「眼高の入力を下げる 0→1」は、
#     `mikoro_check` が `seeFromM=None` で**例外**を投げ、`run_checks` が
#     リストごと1行に差し替えていたものを数えていた(=検出ではない)。
#     ⭕ 例外を潰し、いまは本物の指摘として数える。
#   ⭐ **2026-09-03 庭方5巡目(窓の小径の案H)で1組を入れ替えた。**
#     ・「小径を前の6点へ戻し `stepAddPt` も 3.0 へ戻す」…… 0件 → 1件(局所18%)。
#     ・⚠逆向き「`stepAddPt` だけ 3.0 へ戻す」…… 0件 → 0件。
#       ⭐ これが大事 — **黙ったのは閾値のせいではなく、折れ点が本当に 15% 以内**だから。
#       ⛔ 逃げ道(`stepAddPt`)を戻して黙らせる直し方と、線を引き直す直し方は
#         **この2件の対で見分けがつく**。片方だけでは区別できない。
#   ⚠ **2026-09-03(裁定7=B と庭方5巡目のあと)に3つ作り直した。**
#     ・「蓮の帯を『地表』へ」…… 4件→4件。⛔ 検査の劣化ではなく、**帯Dを D1/D2 に割った**ので
#       `slopeBands[6]` が葭原になり、壊す先が別の帯へずれていた。⭕ **名前で選ぶ**形へ。
#     ・「窓の松 P1 を扇の外へ」…… 1件→1件。⛔ **P1 は素で既に扇の外**(裁定7で窓が細まり
#       0.41間 はみ出している)ので増えようがない。⭕ 扇の中に居る **P2** を出す形へ。
#     ・「確度の記号を本文に無い S へ」…… 0件→0件。⛔ 窓の cert に裁定7の経緯で
#       「唯一のS図」が入り、**S が本文に現れてしまった**。⭕ 本文に無い **P** へ。
#   ⭐ **添字で壊すと、章の構造が変わった日に黙って別の物を壊す。**名前で選ぶ。
#   ⚠ **2026-09-03(庭方5巡目の座標のあと)にもう1つ作り直した。**
#     ・「窓の松の三本を一直線に並べる」…… 2件→2件。⛔ 一直線になる u は
#       **P1 の位置で変わる**のに、P1 が (−4.0)→(−2.0) へ動いたあとも古い u−1.19 を
#       置いていた(=直線から外れたまま壊していた)。⭕ u+0.44 へ。
#     ⭐ **「壊した形」が設計の値に依存する試験は、設計が動いたら必ず計算し直す。**
#   ⭐ **2026-09-03 普請奉行の裁定で「幕の口」の検査の形を変えた。**
#     ⛔ 口の**総幅**で見る形は、庭方が**わざと不揃いに置いた肩**(南 0.6間・北 0.7間 外)を
#       0.15間 の超過として鳴らしていた — **検査の形が意匠の規則と合っていなかった**。
#     ⭕ **肩ごと**に「窓の縁からの外側の余裕 ≦ `gapClearKen`(0.75間・U)」を見る形へ。
#       ⛔ 肩が**窓の中へ入る**(余裕が負)ときも鳴らす。壊し方も肩ごとに2本置いた。
#     ⚠ **閾値を緩めて黙らせたのではない** — 総幅の 0.6×2=1.2 に対し、肩ごとの上限は
#       0.75 で**一つの肩に許す量はむしろ厳しい**。緩めたのは「不揃いを許すかどうか」だけ。
#   ⚠ **2026-09-03(裁定8=A と庭方5巡目のあと)に4つ入れ替えた。**
#     ・「視軸の法肩の柵を h1.4 へ戻す」…… 1件→1件。⛔ K204 で**柵の特例そのものを廃した**
#       (`railH` が無くなった)ので壊す先が消えた。⭕ 「竹垣 `takegakiH` を h2.0 へ」へ。
#     ・小径の2件 …… **例外**(−1)。⛔ K188 で**小径を廃した**ので `komichi` が無い。
#       ⭕ 2件とも**外した** — 設計が消えた試験は残さない(壊す物が無い)。
#     ・「坂を u−26 の崖へ振る」…… 0件→0件。⛔ (−26,127) は崖の肩の手前で、
#       93%の崖(u−25〜−27 / v126〜131)に**入っていなかった**。⭕ (−26.5,130) へ。
#   ⭐ **裁定で設計が消えると、その設計を壊す試験も消える。**⛔ 残すと例外を数える。
#   ⚠ **2026-09-03(K209・K210 のあと)にもう1つ作り直した。**
#     ・「法肩の竹垣を h2.0 へ上げる」…… 0件→0件。⛔ K210 で**視軸の区間だけ四つ目垣 h0.6**
#       に落とす特例が戻り、見所⑧⑨がその区間の中に入ったので、竹垣の丈を上げても当たらない。
#       ⭕ 「特例の幅を −5間 に縮める(見所が特例の外へ出る)」へ差し替えた。
#     ⭐ **特例を足すと、素の値を壊す試験が効かなくなる** — 壊す先を「特例の適用範囲」へ移す。
#   ⚠ **2026-09-03(考証5巡目・庭方5巡目・検図5巡目)に足した検査と、そこで学んだこと。**
#     ・「データの死値」検査を新設 — json のキーが生成器のソースに一度も現れないものを数える。
#       ⭐ **一発で16件**出た(`obi.komono`・`hojiri.ban`・`susuki.clearKen` ほか)。
#       ⛔ `wiring_gate.py` は**関数**の結線しか見ない。データの死値は別の網が要る。
#     ・「動線・坂が樹の芯を横切らない」検査 — 壊し方は**榎を路盤の上へ移す**。
#       ⚠ 松のほうは「坂と動線が帯を横切る所も口として扱う」ようにしたので、
#       坂を松へ寄せても**割り付けが避けて**鳴らない(=設計が正しく追随している)。
#     ・⛔ **「対岸から見た層」の検査は合否を出さない状態で置いた** — 一度目の式は恒真、
#       二度目の式は素の設計で18件鳴る。**どちらが庭方の見立てか決められないので、
#       数だけ刷って合否は開けない**(定義が揃うまで)。⛔ 恒真のまま通さない。
#   ⚠ **2026-09-03(庭方6巡目 K262/K263 と検図5巡目のあと)に2つ作り直した。**
#     ・「法肩の松の南の肩を窓の中へ」…… 0件→0件。⛔ K262 で**南が3区間に割れた**ので
#       `spans[0]` はもう窓の肩ではない(窓の肩は `spans[2]`)。⭕ 添字を直し、
#       u+1.0 まで入れて**窓の中の松の丈**として鳴らす形へ。
#     ・「N1/N2 を汀へ8間」…… ⛔ **庭方の式では 28間 寄せても鳴らない**(草地 0.95°)。
#       ⭕ 検査が生きていることは「層の下限を 0.5→3.5° へ上げる 0→6件」で確かめる。
#       ⚠ この事実は庭方へ返す(棟を汀へ寄せても層は痩せない式になっている)。
#   ⭐ **2026-09-03 ユーザー裁定9=A で「汀へ寄せるな」を m 建てで縛った**(庭方 K264)。
#     ⚠ 角度の検査(対岸から見た層)は**棟を汀へ寄せても痩せない**式なので、
#       それだけでは寄せるなを縛れなかった(28間 寄せても 0.95° で閾値 0.5° に届かない)。
#     ⭕ A 下手の面 → 辺5 ≧ 20.0m /  B 足元の地盤 − 水面 ≧ 4.5m の二本を足し、
#       壊し方も「M1 を v153 へ 0→1件」「N2 の面を 10.9 へ 0→1件」で持った。
#   ⭐ **決定関門 `decision_gate.py` を新設**(裁定9=A の2本目) — 台帳の【決定】の項が
#     閉じ書きで **其◯ / *_check / json のキー** のどれかを指しているかを見る。
#     ⚠ 立ち上げたとき **22件中20件が参照なし**だった。⛔ 参照が書いてあることしか
#     見ない(中身は検分役と破壊試験の仕事)が、書こうとした瞬間に
#     「どこにも出ていない決定」が露見する。
#   【結界(取り付き・表↔奥の非連結・動線)】素 0 件
#     結界を全部消す                                0件 → 2件
#     W1 を段の縁で止める(北の帯を空ける)                   0件 → 2件
#     W6 の西端を元へ戻す(法肩の内側に穴が空く)                0件 → 2件
#     W5 を消す(法肩の内側で塀に穴)                      0件 → 3件
#     W5 の始点をずらして継ぎ手を空ける                     0件 → 3件
#   【池(汀線・離れ・掘り込み)】素 0 件
#     汀線を主面の外へ出す                             0件 → 8件
#     池床を水面より上げる                             0件 → 1件
#     水面を自然地盤より上げる(掘り込みでなくなる)                0件 → 2件
#     宣言した離れを厳しくする(結界塀 1.6→2.5間)             0件 → 1件
#     沢飛石の袂を水の中へ入れる                          0件 → 1件
#     沢飛石を偶数枚にする                             0件 → 1件
#     沢飛石の天端を水面より下げる                         0件 → 1件
#     渡りの浅場を外す(足元が深くなる)                      0件 → 1件
#     三石を一直線に並べる                             0件 → 1件
#     中島の輪郭の1点を水面の外へ出す                       0件 → 1件
#     中島の松を島の輪郭の外へ出す                         0件 → 1件
#     ⚠逆向き: 中島の芯だけを動かす(組み直しで輪郭から引き戻る。増えないのが正) 0件 → 0件
#     浸透の悲観値を標準値より小さくする                      0件 → 1件
#     池面への直接雨に流出係数を掛ける                       0件 → 1件
#     年蒸発量を落として収支の項を空にする                     0件 → 1件
#   【築山(底の実測・段の外・離れ)】素 0 件
#     築山Bの頂を底より低くする                          0件 → 1件
#     築山Bを結界塀 W6 へ寄せる                        0件 → 1件
#     築山Aを段の外へ出す                             0件 → 1件
#   【庭の点景(庭の中・水に落ちていないか)】素 0 件
#     景石を庭の外へ出す                              0件 → 2件
#     沓脱石を棟の中へ入れる                            0件 → 2件
#     灯籠を水の中へ戻す                              0件 → 1件
#     園路の1点を汀へ寄せる(sdMin 割れ)                  0件 → 1件
#     袖の主石を台の中へ移す                            0件 → 1件
#     額縁の松を視軸の中へ入れる                          0件 → 2件
#     台の中へ丈1.5mの石を入れる                        0件 → 1件
#     台の中へ丈0.9mの刈込を入れる                       0件 → 1件
#     台の沓脱石を丈1.4mへ上げる                        0件 → 1件
#     ⚠逆向き: 袖の石を袖の中で動かす(増えないのが正)             0件 → 0件
#     ⚠逆向き: 袖の刈込を袖の中で伸ばす(増えないのが正)            0件 → 0件
#   【見所(入側か庭の中か・借景の視線)】素 0 件
#     見所を庭でも入側でもない所へ置く                       0件 → 1件
#     御殿の床を −5.0m にする(入側の眼が地盤より下がる)          0件 → 8件
#     視軸の特例の幅を −5間 に縮める(見所が特例の外へ出て竹垣 h0.9 に当たる) 0件 → 1件
#     視軸の柵の特例を h0.9 へ戻す(床几の視線を切る)            0件 → 1件
#   【坂の規則(勾配・脚・折れ)】素 0 件
#     北東の坂の2点目 (29,35) を戻す(1脚目が 2.7m に戻る)    0件 → 2件
#     坂の頭を窓の中(u+1)へ移す                        0件 → 1件
#     坂を u−26 の崖(93%)へ振る                     0件 → 1件
#   【庭の点景と竹垣・勝手動線・結界塀の交差】素 0 件
#     結界塀 W1 を池の上へ下ろす                        0件 → 2件
#     勝手動線を築山Bの上へ回す                          0件 → 1件
#     勝手動線を池の中へ引き回す                          0件 → 2件
#   【庭の土量の収支】素 0 件
#     築山を高くして掘削土で足りなくする                      0件 → 1件
#     法面を 1:3 へ緩める(抜きの中が埋まる)                 0件 → 1件
#   【面のはみ出し(棟・庭が段と区画の中か)】素 0 件
#     「地なり」の庭から段の抜きを消す                       0件 → 1件
#     「面」の庭を抜きの中へ広げる                         0件 → 1件
#     「混」の庭を段の中だけに縮める                        0件 → 1件
#   【庭の割り当ての矩形どうしの重なり】素 0 件
#     白洲を書院の泉水へ重ねる                           0件 → 1件
#   【確度の本文の写し】素 0 件
#     庭の点景に長い確度の本文を写す                        0件 → 1件
#   【方位語】素 0 件
#     庭の注記の方位語を壊す                            0件 → 1件
#   【矩形の重なり】素 0 件
#     稲荷社を玄関棟へ重ねる                            0件 → 1件
#     門前の石段を長屋門へ食い込ませる                       0件 → 1件
#   【在るべき役割の未達(必須・望ましい)】素 1 件
#     練塀 run を全部消す                           1件 → 2件
#     表門の番所を消す(躯体が無くなる)                      1件 → 2件
#     庭を全部消す                                 1件 → 2件
#     井戸を全部消す                                1件 → 2件
#     稲荷社を消す                                 1件 → 2件
#     御錠口を消す                                 1件 → 2件
#     表役所の室を消す                               1件 → 2件
#   【法面(段の外が現地形へ着地するか)】素 0 件
#     ⚠逆向き: 西の法尻の土留めを消す(増えないのが正)             0件 → 0件
#     切土の法面を 1:3 へ緩める                        0件 → 226件
#     法面の到達距離を 2m へ縮める                       0件 → 12件
#   【郭の土留めの高さ】素 0 件
#     土留めをもう1本足し、span を与えない(落差が測れない)         0件 → 1件
#   【西の斜面と岸(窓・林・葭蓮・柵・小径)】素 0 件
#     林の下端の線を直線にする                           0件 → 4件
#     帯の連なりを切る(林の下端の**出どころ**を1m下げる)          0件 → 1件
#     蓮の帯を『地表』の別へ移す(標高で切れない物を標高で切る)          0件 → 2件
#     汀の柵を消す                                 0件 → 1件
#     木戸を柵から離す(区画界の上から外す)                    0件 → 1件
#     堀端の見所を2箇所にする(木戸と兼ねる形を崩す)               0件 → 1件
#     窓の松の hDesign を 4.2/4.2 に揃える(丈の不等が消える)  0件 → 1件
#     窓の視線の余裕を 1.0→2.5m へ広げる(頭打ちが効いて丈の差が縮む)  0件 → 1件
#     扇を 23間 へ戻す(裁定7=B の上限を破る)               0件 → 1件
#     窓の松 P2 を扇の外(u+9.0)へ出す                  0件 → 1件
#     窓の松の三本を一直線に並べる                         0件 → 1件
#     林の下端の北の肩を u+6.5 へ開く(余裕 1.3間)           0件 → 1件
#     法肩の松の南の肩を窓の中(u+1.0)へ入れる                0件 → 1件
#     林の下端の点を見透しの窓の中へ入れる                     0件 → 3件
#     窓の松 P3 を扇の中へ戻す                         0件 → 1件
#     法肩の松の丈の下限を 6.0 へ下げる                    0件 → 1件
#     林の下端の u ピッチを等間隔にする(点数は 9 のまま)          0件 → 6件
#     林の下端を 13 点に戻す(点数の規則を突く)                0件 → 6件
#     窓のススキの丈を 6m へ上げる(置ける区間が無くなる)           0件 → 1件
#     汀の杭を陸の上へ並べる(足元が水面を跨がない)                0件 → 2件
#     汀の杭の芯々を径より詰める                          0件 → 1件
#     汀の杭の芯々を一定にする(等間隔)                      0件 → 1件
#     汀の杭の頭を水面より下げる                          0件 → 1件
#     堤の天端の標本を 0.3間 内側へ戻す(区画線の段を跨ぐ)          0件 → 1件
#     堤の天端の隅の除外をやめる(辺4・辺6のクリップ帯を混ぜる)         0件 → 1件
#     葭の上端を水面より上へ戻す(depthMin −0.3)           0件 → 2件
#     葭原の幅を 1.0m へ狭める(勾配が急になる)               0件 → 1件
#     蓮の外端の池床を 4.0 へ下げる(水深 2.6m)             0件 → 1件
#     蓮の外端の池床の宣言を消す(区画外の前提が消える)              0件 → 1件
#     法尻のススキを窓の中にも置けることにする(丈2.0mが上限を超える)     0件 → 1件
#     窓の中へ丈 6m の植栽を1群置く(丈が固定の物)              0件 → 1件
#   【対岸から見た層(林と草地の見かけの厚み)】素 0 件
#     層の下限を 0.5→3.5° へ上げる(検査が生きている確かめ)       0件 → 6件
#   【法肩の松の割り付け(区間ごと)】素 0 件
#     南の小区間を1つに戻す(口を数えない割り付け)                0件 → 1件
#     法肩の松の南を 5本にする(北が空く)                    0件 → 4件
#     法肩の松の総数と区間の合計を食い違わせる                   0件 → 1件
#   【データの死値(json のキーが読まれているか)】素 0 件
#     json に読まれないキーを1つ足す                     0件 → 1件
#   【動線・坂が樹の芯を横切らない】素 0 件
#     榎 E1 を坂の路盤の上へ移す                        0件 → 1件
#   【崖下の帯の棟(帯D2・切盛・榎の離れ)】素 0 件
#     M1 を v153 へ出す(汀へ寄せる)                   0件 → 1件
#     N2 の面を 10.9 へ下げる(水面へ寄せる)               0件 → 1件
#     N1 を東へ1間ずらす(山側の余地を割る)                  0件 → 1件
#     N1 を榎 E1 へ 4m 寄せる                      0件 → 1件
#     N2 の面を 1.0m 上げる(帯を均す)                  0件 → 1件
#     N1 を崖面(帯D1)へ載せる                        0件 → 1件
#   【確度の記号(宣言と本文の食い違い)】素 0 件
#     確度の記号を本文に無い P へ書き換える                   0件 → 1件
#     確度の記号の宣言を消す                            0件 → 1件
#   【往復試験(剥がして組み直すと正典に戻るか)】素 0 件
#     見晴らしの台の眼高を人が書き換える(地盤+1.23 の従属値)        0件 → 1件
#     窓の松の丈を人が書き換える(その点の上限からの従属値)            0件 → 1件
#     中島の芯を人が書き換える(輪郭から出る従属値)                0件 → 2件
#     池面への直接雨の面積を人が書き換える(汀線から出る従属値)          0件 → 1件
#     断面の現地形線を人が書き換える                        0件 → 1件
#   【地盤・コード側(json では届かない層)】素 各1件
#     ⑦の平滑化の除外を戻す(旧DEMを読ませる)              0件 → 1件
#     借景の標本を `_world_at` へ戻す                   1件 → 2件

#   【結界・絞った範囲の確かめ】
#     法肩から上だけを歩く                             抜けられない = 主面の上では閉じている
#     崖の下まで歩く(範囲外の確認)                        抜けられる(最大 v=112.5)= 絞った範囲の外が担っていた
# ⛔ 検査を足したら**必ずこの型で壊して確かめる**。当家は「新設した検査が恒真だった」を
#   3度出している(五巡目1件・庭方の初回検分3件・2026-09-02 の program_check「馬場」)。

def _pt_elems(d, g):
    """庭が持つ「点で位置が決まる物」の一覧 [(種別, 名, u, v, 免除フラグ)]。"""
    out = []
    for st in (g.get("ishigumi") or []):
        if st.get("u") is not None:
            out.append(("石組", st["label"], st["u"], st["v"], st))
    for tr in (g.get("toro") or []):
        out.append(("灯籠", tr["label"], tr["u"], tr["v"], tr))
    for kt in (g.get("kutsunugi") or []):
        out.append(("沓脱石", kt["label"], kt["u"], kt["v"], kt))
    for nj in (g.get("nakajima") or []):
        out.append(("中島", nj["label"], nj["u"], nj["v"], nj))
    for ij in (g.get("iwajima") or []):
        out.append(("岩島", ij["label"], ij["u"], ij["v"], ij))
    for ts in (g.get("tsukiyama") or []):
        out.append(("築山", ts["label"], ts["u"], ts["v"], ts))
    for sk in (g.get("shokusai") or []):
        for q in (sk.get("pts") or []):
            out.append(("植栽", "%s(%s)" % (sk.get("species", ""), sk.get("layer", "")),
                        q[0], q[1], sk))
    for ys in (g.get("yashiro") or []):
        c9 = _yashiro_pos(d, ys)
        if c9:
            out.append(("社殿", ys["label"], c9[0], c9[1], ys))
        out.append(("鳥居", ys["label"] + "の鳥居", ys["torii"]["u"], ys["torii"]["v"], ys))
    return out


def _yashiro_pos(d, ys):
    """社殿の芯は **`service` の矩形から算出**する。⛔ 二箇所に書かない(2026-09-02 検図 K070)。"""
    o9 = next((x for x in d.get("service", []) if x["name"] == ys.get("ref")), None)
    if not o9:
        return None
    return ((o9["u0"] + o9["u1"]) / 2.0, (o9["v0"] + o9["v1"]) / 2.0)


def _line_elems(g):
    out = []
    for en in (g.get("enro") or []):
        out.append(("園路", en["label"], [(a, b) for a, b in en["pts"]]))
    for tb in (g.get("tobiishi") or []):
        if isinstance(tb.get("pts"), list):
            out.append(("飛石", tb["label"], [(a, b) for a, b in tb["pts"]]))
    for sw in (g.get("sawatobi") or []):
        out.append(("沢飛石", sw["label"], [(a, b) for a, b in sw["pts"]]))
    return out


def niwa_element_check(d):
    """**庭の点景が自分の庭の中にあり、棟・渡廊下と重ならず、水に落ちていないか。**

    ⚠ 2026-09-02 の書き起こしで最初に効いた検査。庭方の設計のうち、園路の3点・灯籠1基・
      景石1個が**汀線の内側(水の中)**にあることをここが捕まえた。
    ⭕ 免除は `frame: true`(額縁の植栽=視軸の外に置くのが宣言そのもの)だけ。"""
    K = d["const"]["ken"]
    bad = []
    g0, mg0, ring0 = pond_of(d)
    boxes = [(m["name"], m["u0"], m["v0"], m["u1"], m["v1"]) for m in d["munes"]] + \
            [(l["name"], l["u0"], l["v0"], l["u1"], l["v1"]) for l in d["links"]]
    def _on_saw(u, v):
        """沢飛石の渡りの上か。⭕ 園路と飛石は**渡りの上でだけ**水の上に出てよい。"""
        for g9 in d["gardens"]:
            for sw in (g9.get("sawatobi") or []):
                pts9 = [(a, b) for a, b in sw["pts"]]
                for a9, b9 in zip(pts9, pts9[1:]):
                    du, dv = b9[0] - a9[0], b9[1] - a9[1]
                    L2 = du * du + dv * dv or 1e-9
                    t9 = max(0.0, min(1.0, ((u - a9[0]) * du + (v - a9[1]) * dv) / L2))
                    if math.hypot(u - (a9[0] + du * t9), v - (a9[1] + dv * t9)) * K <= sw["rMax"]:
                        return True
        return False

    def _saw_tamoto(u, v):
        """沢飛石の**袂**(両端)か。園路と飛石はここで汀に寄るのが役目。"""
        for g9 in d["gardens"]:
            for sw in (g9.get("sawatobi") or []):
                for q9 in (sw["pts"][0], sw["pts"][-1]):
                    if math.hypot(u - q9[0], v - q9[1]) < 0.15:
                        return True
        return False
    for g in d["gardens"]:
        for kind, nm, u, v, src in _pt_elems(d, g):
            # ⭕ 社殿は棟(`service`)そのもの — 庭の実形は棟の足跡を引いた残りなので中に入らない
            if src.get("ref") and kind == "社殿":
                pass
            elif not src.get("frame") and not g_in(g, u, v):
                bad.append("%s の%s『%s』(%.2f, %.2f) が庭の実形の外" % (g["label"], kind, nm, u, v))
            if src.get("frame"):
                # `frame`(額縁・袖)= **台の外に置く物**。⛔ 台の矩形は庭の割り当てとは別
                #   (`shakkei.dai`)。⭕ 台の上に置けないのは視線が低く通るためで、
                #   台の上の物は**実際の視線で**判定する(下の別ループ)。
                dai = (g.get("shakkei") or {}).get("dai")
                if dai and dai["u0"] - 1e-9 <= u <= dai["u1"] + 1e-9 \
                   and dai["v0"] - 1e-9 <= v <= dai["v1"] + 1e-9:
                    bad.append("%s の%s『%s』は袖(台の外)のはずだが台の中 (%.2f, %.2f)"
                               % (g["label"], kind, nm, u, v))
                sk9 = g.get("shakkei") or {}
                if sk9 and kind == "植栽" and str(src.get("layer", "")) in ("高木", "中木") \
                   and in_mado(d, u, v):
                    ax9 = axis_at(d, v)
                    bad.append("%s の%s『%s』(高木)が見透しの窓 u%.1f〜%.1f(v%.1f)の中"
                               % (g["label"], kind, nm, ax9[0], ax9[1], v))
            for bn, a0, b0, a1, b1 in boxes:
                if a0 + 1e-6 < u < a1 - 1e-6 and b0 + 1e-6 < v < b1 - 1e-6:
                    bad.append("%s の%s『%s』が %s の中" % (g["label"], kind, nm, bn))
            if ring0 and kind in ("石組", "灯籠", "沓脱石", "植栽", "社殿", "鳥居") \
               and _ring_in(ring0, u, v):
                bad.append("%s の%s『%s』(%.2f, %.2f) が**水の中**(汀線の内側 %.2fm)"
                           % (g["label"], kind, nm, u, v,
                              sashizu_lib.poly_edge_dist(ring0, u, v) * K))
        for kind, nm, pts in _line_elems(g):
            if kind == "沢飛石":
                continue                       # ⭕ 渡りそのもの。中の石が水中にあるのは意図
            for (u, v) in pts:
                if ring0 and _ring_in(ring0, u, v) and not _on_saw(u, v):
                    bad.append("%s の%s『%s』の折れ点 (%.2f, %.2f) が**水の中**(汀線の内側 %.2fm)"
                               % (g["label"], kind, nm, u, v,
                                  sashizu_lib.poly_edge_dist(ring0, u, v) * K))
        # 園路は「芯が汀から `sdMin` 以上離れる」— 図が宣言した規則を検査に落とす
        for en in (g.get("enro") or []):
            if not ring0 or en.get("sdMin") is None:
                continue
            for (u, v) in en["pts"]:
                if _saw_tamoto(u, v):
                    continue                   # ⭕ 渡りの袂は汀に寄るのが役目
                sd9 = pond_sd(ring0, u, v)
                if sd9 < en["sdMin"] - 1e-6:
                    bad.append("%s の園路の折れ点 (%.2f, %.2f) の汀からの離れ %.2f間 が "
                               "宣言 %.2f間 を下回る" % (g["label"], u, v, sd9, en["sdMin"]))
    # **見晴らしの「台」の上の物が、主視点から可視水面への視線を切っていないか。**
    # ⭐ 一律 `platMaxH` ではなく**実際の視線の高さ**で測る(`platMaxH` は視線を引けないときの控え)。
    #
    # ⛔ **判定するのは `shakkei.dai` の矩形の中だけ。袖へ広げてはならない。**
    #   南北の袖は「隣邸を隠して視野を額縁にする」ために**塞ぐ**場所で、
    #   **地面そのものが視線より高いのが設計どおり**である
    #   (2026-09-02 実測: 主石の位置で素の地盤が視線の +0.78m、副石で +0.94m)。
    #   ⛔ 袖まで判定すると、地盤・松・刈込・石のすべてが件数になり、
    #     **正しい設計が不合格として刷られる**。
    #   ⭕ したがって除くのは二つ — ①`frame` を立てた物(台の外に置くと宣言した物)
    #     ②`dai` の矩形の外にある物。
    #   ⚠ 破壊試験は**両方向**で確かめること —
    #     「台の中へ石を1つ入れる → 増える」/「袖の石を動かす → 増えない」。
    for g in d["gardens"]:
        sk9 = g.get("shakkei")
        dai = (sk9 or {}).get("dai")
        if not sk9 or not dai:
            continue
        sm9 = shakkei_metrics(d)
        mk9 = sm9["mk"] if sm9 else None
        slope9 = ((sm9["crestY"] - mk9["eyeY"]) / sm9["crestM"]) if (sm9 and sm9.get("crestM")) else None

        def _limit(u9, v9):
            """その位置で物の天端が超えてはならない高さ。"""
            gy9 = graded_y(d, u9, v9, _dem_at(d, u9, v9)) or 24.8
            if slope9 is None or mk9 is None:
                return gy9 + sk9["platMaxH"], gy9, None
            dist9 = math.hypot(u9 - mk9["u"], v9 - mk9["v"]) * K
            return mk9["eyeY"] + slope9 * dist9, gy9, dist9
        items = [(kind, nm, u, v, (src.get("h") or src.get("hMax") or 0.0), src)
                 for kind, nm, u, v, src in _pt_elems(d, g)]
        items += [("刈込", kk.get("species", ""), (kk["u0"] + kk["u1"]) / 2.0,
                   (kk["v0"] + kk["v1"]) / 2.0, kk.get("h") or 0.0, kk)
                  for kk in (g.get("karikomi") or []) if "u0" in kk]
        for kind, nm, u, v, hh, src in items:
            if src.get("frame") or hh <= 0:
                continue
            if not (dai["u0"] <= u <= dai["u1"] and dai["v0"] <= v <= dai["v1"]):
                continue
            lim9, gy9, dist9 = _limit(u, v)
            if gy9 + hh > lim9 + 1e-6:
                bad.append("%s の台の上の%s『%s』(天端 %.2f)が、主視点から可視水面への視線 %.2f を"
                           "%.2fm 超える%s"
                           % (g["label"], kind, nm, gy9 + hh, lim9, gy9 + hh - lim9,
                              ("(視点から %.1fm)" % dist9) if dist9 else "(視線を引けず控えの物差し)"))
    return bad


def garden_alloc_check(d):
    """**庭の「割り当ての矩形」どうしが重なっていないか。**

    ⚠ 実形(`rects`)は §4 の並び順で上位が取ると決めて機械的に解いてあるので、
      `overlap_check` の総当たりでは**構造的に落ちない**。⛔ 解けたことと、
      庭方の割り当てが整合していることは別なので、**重なりそのものをここで出す**。
    ⛔ 当方が境界を引き直すのは意匠の判断 — 直すのは庭方。"""
    K = d["const"]["ken"]
    G = d["gardens"]
    bad = []
    for i9 in range(len(G)):
        for j9 in range(i9 + 1, len(G)):
            a, b = G[i9], G[j9]
            iu = min(a["u1"], b["u1"]) - max(a["u0"], b["u0"])
            iv = min(a["v1"], b["v1"]) - max(a["v0"], b["v0"])
            # ⛔ 閾値を置かない(2026-09-02 検図 K069: 0.25間²=0.83m² 未満が黙って通っていた)。
            if iu > 1e-6 and iv > 1e-6:
                bad.append("『%s』と『%s』の割り当てが %.2f×%.2f間(%.1f m²)重なる — "
                           "**庭方が境界を引き直すこと**(指図方は引き直さない)"
                           % (a["label"], b["label"], iu, iv, iu * iv * K * K))
    return bad


def gogan_cover(d):
    """**汀線を形式別にどれだけ受けているか。**⛔ 受け持ちの無い区間を図の上で素の縁にしない
    (2026-09-02 検図 K041: 汀線の過半に指定が無かった)。返り値は形式ごとの区間と延長。"""
    g, mg, ring = pond_of(d)
    if not g:
        return None
    K = d["const"]["ken"]
    n = len(ring)
    own = [None] * n
    for gg in (g.get("gogan") or []):
        if gg.get("rest"):
            continue
        for i9, (u9, v9) in enumerate(ring):
            if gg["u0"] - 0.3 <= u9 <= gg["u1"] + 0.3 and gg["v0"] - 0.3 <= v9 <= gg["v1"] + 0.3:
                own[i9] = gg["label"]
    for sh in (g.get("suhama") or []):
        for i9, (u9, v9) in enumerate(ring):
            if own[i9] is None and sh["u0"] - 0.3 <= u9 <= sh["u1"] + 0.3 \
               and sh["v0"] - 0.3 <= v9 <= sh["v1"] + 0.3:
                own[i9] = sh["label"]
    for rg in (g.get("rangui") or []):
        arc = ring_arc(ring, rg["a"], rg["b"])
        for i9, (u9, v9) in enumerate(ring):
            if own[i9] is None and any(math.hypot(u9 - a9[0], v9 - a9[1]) < 0.20 for a9 in arc):
                own[i9] = rg["label"]
    rest_lbl = next((gg["label"] for gg in (g.get("gogan") or []) if gg.get("rest")), None)
    seglen = collections.OrderedDict()
    tot = 0.0
    for i9 in range(n):
        L9 = math.hypot(ring[(i9 + 1) % n][0] - ring[i9][0],
                        ring[(i9 + 1) % n][1] - ring[i9][1]) * K
        tot += L9
        lb = own[i9] or (rest_lbl or "(受け持ちなし)")
        seglen[lb] = seglen.get(lb, 0.0) + L9
    rest = []
    i9 = 0
    while i9 < n:
        if own[i9] is None:
            j9 = i9
            while j9 + 1 < n and own[j9 + 1] is None:
                j9 += 1
            rest.append((i9, j9))
            i9 = j9 + 1
        else:
            i9 += 1
    return {"own": own, "len": seglen, "total": tot, "rest": rest, "restLabel": rest_lbl}


def pond_check(d):
    """**池の不変条件。**汀線が段の中にあること／棟・渡廊下と重ならないこと／
    宣言した離れを下回らないこと／**掘り込みであること**(汀の内に水面より低い自然地盤が無い)。"""
    g, mg, ring = pond_of(d)
    if not g:
        return []
    K = d["const"]["ken"]
    bad = []
    for (u, v) in ring:
        if not any(tin(t, u, v) for t in d["terraces"]):
            bad.append("汀線の点 (%.2f, %.2f) が主面の外" % (u, v))
        if not g_in(g, u, v):
            bad.append("汀線の点 (%.2f, %.2f) が庭の実形の外" % (u, v))
    for o in d["munes"] + d["links"] + d["service"]:
        st = 0.25
        uu = o["u0"]
        while uu <= o["u1"]:
            vv = o["v0"]
            while vv <= o["v1"]:
                if _ring_in(ring, uu, vv):
                    bad.append("汀線が %s と重なる: (%.2f, %.2f)"
                               % (o.get("name", o.get("label")), uu, vv))
                    uu = o["u1"] + 1; break
                vv += st
            uu += st
    m = pond_metrics(d)
    cl = mg.get("clearance") or {}
    for k9, got in (("shoinIrikawa", m["dShoin"]), ("genkanW", m["dGenkan"]),
                    ("kekkai", m["dKekkai"]), ("tsukiyamaA", m["dTsukiyama"])):
        if k9 in cl and got < cl[k9] - 1e-6:
            bad.append("汀からの離れ %s = %.2f間 が宣言 %.2f間 を下回る" % (k9, got, cl[k9]))
    if m["below"] > 0:
        bad.append("汀の内側に水面(%.2f)より低い自然地盤のセルが %d/%d ある — "
                   "『掘り込みの泉水』の宣言と食い違う"
                   % (mg["waterY"], m["below"], m["cells"]))
    if mg["bedY"] >= mg["waterY"]:
        bad.append("池床 %.2f が水面 %.2f 以上" % (mg["bedY"], mg["waterY"]))
    for sw in (g.get("sawatobi") or []):
        pts9 = [(a, b) for a, b in sw["pts"]]
        if len(pts9) % 2 == 0:
            bad.append("沢飛石『%s』が %d 枚 — **奇数**で置くこと" % (sw["label"], len(pts9)))
        for q9 in (pts9[0], pts9[-1]):
            if pond_sd(ring, q9[0], q9[1]) < 0.0:
                bad.append("沢飛石『%s』の袂 (%.2f, %.2f) が水の中(袂は陸に置くこと)"
                           % (sw["label"], q9[0], q9[1]))
        for q9 in pts9[1:-1]:
            if pond_sd(ring, q9[0], q9[1]) > 0.0:
                bad.append("沢飛石『%s』の中の石 (%.2f, %.2f) が陸の上(渡りにならない)"
                           % (sw["label"], q9[0], q9[1]))
        if sw["topY"] <= mg["waterY"]:
            bad.append("沢飛石『%s』の天端 %.2f が水面 %.2f 以下(渡れない)"
                       % (sw["label"], sw["topY"], mg["waterY"]))
        sl = mg.get("shallow")
        if sl:
            for q9 in pts9:
                if not (sl["v0"] - 0.3 <= q9[1] <= sl["v1"] + 0.3):
                    bad.append("沢飛石『%s』の石 (%.2f, %.2f) が浅場(v %.1f〜%.1f)の外 — "
                               "足元が深くなる" % (sw["label"], q9[0], q9[1], sl["v0"], sl["v1"]))
                    break
    # 汀線は**全長どこかの形式が受け持つ**(素の縁を残さない)
    cov = gogan_cover(d)
    if cov and cov["restLabel"] is None and cov["rest"]:
        miss = sum(math.hypot(ring[(a9 + 1) % len(ring)][0] - ring[a9][0],
                              ring[(a9 + 1) % len(ring)][1] - ring[a9][1])
                   for a9, b9 in cov["rest"] for _ in [0]) * K
        bad.append("汀線の %d 区間(約 %.1fm)にどの護岸形式も指定が無く、図の上で素の縁になる"
                   % (len(cov["rest"]), miss))
    # 三石は**不等辺**で、一直線に並ばない(図が宣言した作法を検査に落とす)
    tri = [x for x in (g.get("ishigumi") or []) if x.get("role") in ("主石", "副石", "添石")
           and x.get("u") is not None]
    if len(tri) == 3:
        a9, b9, c9 = [(x["u"], x["v"]) for x in tri]
        L9 = sorted([math.hypot(a9[0] - b9[0], a9[1] - b9[1]),
                     math.hypot(b9[0] - c9[0], b9[1] - c9[1]),
                     math.hypot(c9[0] - a9[0], c9[1] - a9[1])])
        if L9[2] - L9[0] < 0.10:
            bad.append("三石の三辺 %.2f/%.2f/%.2f 間 が等辺に近い(不等辺三角にすること)" % tuple(L9))
        cr = ((b9[0] - a9[0]) * (c9[1] - a9[1]) - (b9[1] - a9[1]) * (c9[0] - a9[0]))
        if abs(cr) < 0.10:
            bad.append("三石が一直線に近い(外積 %.3f)" % cr)
    # 水の収支(2026-09-02 庭方3巡目で浸透・直接雨・年蒸発を入れた)
    #   ⛔ 収支の**値そのもの**の可否は庭方の持ち場。ここは**項が揃い、辻褄が合うか**だけ見る。
    gs9 = (g.get("mizu") or {}).get("gensen") or {}
    if gs9:
        bd = mizu_budget(d)
        for k9, nm9 in (("rainCatch", "集水域の雨"), ("rainDirect", "池面への直接雨"),
                        ("evap", "蒸発"), ("seep", "浸透")):
            if bd[k9] <= 0:
                bad.append("水の収支の項『%s』が 0 — 諸元が入っていない" % nm9)
        sh9 = gs9.get("shintou") or {}
        if sh9 and sh9.get("mmDayPess", 0) < sh9.get("mmDay", 0) - 1e-9:
            bad.append("浸透の悲観値 %.1f mm/日 が標準値 %.1f mm/日 より小さい"
                       % (sh9.get("mmDayPess", 0), sh9.get("mmDay", 0)))
        ro9 = (gs9.get("amegatari") or {}).get("runoff")
        if ro9 is not None and not (0.0 < ro9 <= 1.0):
            bad.append("集水域の流出係数 %.2f が 0〜1 の外" % ro9)
        if ((gs9.get("chokusetsu") or {}).get("runoff") or 0) != 1.0:
            bad.append("池面への直接雨に流出係数 %.2f が掛かっている(池面は 1.0)"
                       % ((gs9.get("chokusetsu") or {}).get("runoff") or 0))
    for nj in (g.get("nakajima") or []):
        for q9 in (nj.get("poly") or []):
            if not _ring_in(ring, q9[0], q9[1]):
                bad.append("中島『%s』の輪郭の点 (%.2f, %.2f) が水面の外へ出る"
                           % (nj["label"], q9[0], q9[1]))
                break
        ta = nj.get("treeAt")
        if ta and not _ring_in([(a9, b9) for a9, b9 in (nj.get("poly") or [])], ta[0], ta[1]):
            bad.append("中島の松 (%.2f, %.2f) が島の輪郭の外" % (ta[0], ta[1]))
    return bad


def tsukiyama_check(d):
    """**築山の不変条件。**底の自然地盤を実測すること／段の外へ出ないこと／
    宣言した離れを下回らないこと／頂が底より高いこと。"""
    bad = []
    K = d["const"]["ken"]
    for o in tsukiyama_metrics(d):
        ts = o["ts"]
        if o["cells"] == 0 or o["natMin"] is None:
            bad.append("築山『%s』の底の自然地盤が測れない(復元地盤の外)" % ts["label"])
            continue
        if ts["topY"] <= o["natMax"]:
            bad.append("築山『%s』の頂 %.2f が底の最高 %.2f 以下" % (ts["label"], ts["topY"], o["natMax"]))
        if o["outKen"] > 0.01:
            bad.append("築山『%s』が段の外へ %.2f間² 出る" % (ts["label"], o["outKen"]))
        cl = ts.get("clearance") or {}
        if "kekkaiW6" in cl:
            w6 = next((w for w in d.get("kekkai", []) if w["name"] == "W6"), None)
            if w6:
                got = abs(w6["a"][0] - (ts["u"] - ts["dU"] / 2.0))
                if got < cl["kekkaiW6"] - 1e-6:
                    bad.append("築山『%s』の裾から結界塀 W6 まで %.2f間 が宣言 %.2f間 を下回る"
                               % (ts["label"], got, cl["kekkaiW6"]))
        if "nakaokuS" in cl:
            mn = next((m for m in d["munes"] if m["name"] == "Nakaoku"), None)
            if mn:
                got = abs((ts["u"] + ts["dU"] / 2.0) - mn["u0"])
                if got < cl["nakaokuS"] - 1e-6:
                    bad.append("築山『%s』の裾から中奥棟の南面まで %.2f間 が宣言 %.2f間 を下回る"
                               % (ts["label"], got, cl["nakaokuS"]))
    return bad


def niwa_cross_check(d):
    """**竹垣・勝手動線・結界塀が庭の点景を横切っていないか。**
    ⚠ 竹垣の貫通検査から「庭」の箱を外した(§4 で主面の全面が庭になったため構造的に落ちる)
      代わりに置く検査。⛔ こちらを外したら竹垣は野放しになる。"""
    K = d["const"]["ken"]
    bad = []
    g0, mg0, ring0 = pond_of(d)
    lines = [("竹垣 " + rl["name"], [(a, b) for a, b in rl["pts"]]) for rl in auto_rails(d)]
    lines += [("勝手動線 " + r["name"], [tuple(q) for q in r["pts"]])
              for r in d.get("routes", []) if r.get("kind") == "katte"]
    lines += [("結界塀 " + w["name"], [tuple(w["a"]), tuple(w["b"])]) for w in d.get("kekkai", [])]
    for nm, pts in lines:
        if ring0:
            L9 = _poly_x_rect(pts, min(p[0] for p in ring0), min(p[1] for p in ring0),
                              max(p[0] for p in ring0), max(p[1] for p in ring0))
            if L9 > 0:
                for a, b in zip(pts, pts[1:]):
                    for i9 in range(21):
                        t9 = i9 / 20.0
                        if _ring_in(ring0, a[0] + (b[0] - a[0]) * t9, a[1] + (b[1] - a[1]) * t9):
                            bad.append("%s が池の水面を横切る" % nm)
                            break
                    else:
                        continue
                    break
        for g, ts in mounds_of(d):
            hit = 0
            for a, b in zip(pts, pts[1:]):
                for i9 in range(21):
                    t9 = i9 / 20.0
                    if _ell_r(ts, a[0] + (b[0] - a[0]) * t9, a[1] + (b[1] - a[1]) * t9) <= 1.0:
                        hit += 1
            if hit > 1 and not nm.startswith("結界塀") and "園路" not in nm:
                bad.append("%s が築山『%s』を横切る" % (nm, ts["label"]))
        for g in d["gardens"]:
            for kind, lb, lp in _line_elems(g):
                if kind == "沢飛石":
                    continue                   # 渡りは水の上にあるのが役目
                for a, b in zip(pts, pts[1:]):
                    if any(_seg_x(a, b, c, e) for c, e in zip(lp, lp[1:])):
                        bad.append("%s が %s の%s『%s』と交わる" % (nm, g["label"], kind, lb))
                        break
    return bad


def _walk_grid(d, step=0.5, scope="hogata"):
    """歩ける升目。**江戸期の復元地盤**で作る(graded_y は重すぎて毎回は回せない)。
    升の間を渡れるのは、標高差が `step` あたり 0.60m 以下(≒1:1.5)のときだけ。
    ⛔ 棟・付属屋・池の中は入れない。

    ⭐ **`scope="hogata"` — 主面の法肩から上だけを歩く**【2026-09-02 ユーザー裁定=案B】。
      判定は当図が段の輪郭を引くときと同じ物差し(`|設計面 − 自然地盤| ≦ 0.5m`)で、
      **段の外輪の中、または地盤が段の高さ −0.5m 以上**の升だけを歩ける地とする。
      ⛔ 緩めるためではない — **図の宣言を実態へ合わせる**ため。
      崖(最急71%)とその下の平らな帯(標高8.5・幅約56m)は屋敷の**外構の地**で、
      表とも奥とも位置づけない。⛔ 内部を分けるための塀を崖に76m下ろすのは
      5万3千石の格に合わず典拠も無い。⭕ 「表と奥を分ける」ことの実体は**御錠口(確度A)**で、
      屋外の結界はもともと当方の外挿(確度U)である。
      ⚠ `scope="all"` は**破壊試験専用** — 崖の下まで歩けるようにして、
      絞った範囲の外を見ていないことを確かめるために使う。"""
    key = (id(d), step, scope)
    if key in _WALK:
        return _WALK[key]
    gr = RGrid(d)
    Pg = [gr.L(x, z) for x, z in d["polygon"]]
    u0 = min(p[0] for p in Pg); u1 = max(p[0] for p in Pg)
    v0 = min(p[1] for p in Pg); v1 = max(p[1] for p in Pg)
    nu = int((u1 - u0) / step) + 1; nv = int((v1 - v0) / step) + 1
    boxes = [(o["u0"], o["v0"], o["u1"], o["v1"])
             for o in d["munes"] + d["service"] + d["links"]]
    _g, _mg, ring = pond_of(d)
    ytop = max(t["y"] for t in d["terraces"])
    H = [[None] * nu for _ in range(nv)]
    for jv in range(nv):
        for iu in range(nu):
            uu = u0 + iu * step; vv = v0 + jv * step
            if not in_parcel(d, uu, vv):
                continue
            if scope == "hogata":
                h9 = _dem_at(d, uu, vv)
                if not (any(tin_outer(t, uu, vv) for t in d["terraces"])
                        or (h9 is not None and h9 >= ytop - 0.5)):
                    continue                    # 崖から下は外構の地 — 結界の持ち場ではない
            if any(a <= uu <= c and b <= vv <= e for a, b, c, e in boxes):
                continue
            if ring and _ring_in(ring, uu, vv):
                continue                        # 水の上は歩けない
            H[jv][iu] = _dem_at(d, uu, vv)
    _WALK[key] = (u0, v0, step, nu, nv, H)
    return _WALK[key]


_WALK = {}


def _wall_segs(d, closed=True):
    """歩みを止める線分。結界のし塀(`closed` なら開口も閉じる)＋外周の囲い＋郭の土留め。"""
    segs = []
    for w in d.get("kekkai", []):
        a, b = tuple(w["a"]), tuple(w["b"])
        gp = w.get("gap")
        if gp and not closed:
            lo, hi = min(gp["from"], gp["to"]), max(gp["from"], gp["to"])
            if gp["axis"] == "u":
                segs += [(a, (lo, a[1])), ((hi, a[1]), b)]
            else:
                segs += [(a, (a[0], lo)), ((a[0], hi), b)]
        else:
            segs.append((a, b))
    return segs


def kekkai_reach(d, closed=True, step=0.5, scope="hogata"):
    """**表から奥へ屋外で抜けられるか。**白洲(表)から奥庭(奥)へ経路探索する。
    ⭐ 開口(中門・木戸)を全部閉じてなお通れるなら、それは結界が**閉じていない**。
    ⛔ 「塀を何本引いたか」ではなく「**抜けられるか**」で判定する — 2026-09-02 検図で、
      端が宙に浮いた結界が『0件』を通していた(`kekkai` を空にしても 0件だった)。"""
    u0, v0, st, nu, nv, H = _walk_grid(d, step, scope)
    segs = _wall_segs(d, closed)
    sd0 = d["sando"]
    start = (sd0["u"], 46.0)                    # 白洲(表)
    goal = (-12.0, 95.0)                        # 奥庭(奥)

    def idx(q):
        return (int(round((q[1] - v0) / st)), int(round((q[0] - u0) / st)))
    sj, si = idx(start); gj, gi = idx(goal)
    if H[sj][si] is None or H[gj][gi] is None:
        return None
    seen = [[False] * nu for _ in range(nv)]
    seen[sj][si] = True
    stack = [(sj, si)]
    prev = {}
    while stack:
        jv, iu = stack.pop()
        if (jv, iu) == (gj, gi):
            path = [(jv, iu)]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return [(u0 + i9 * st, v0 + j9 * st) for j9, i9 in reversed(path)]
        h0 = H[jv][iu]
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            j2, i2 = jv + dj, iu + di
            if not (0 <= j2 < nv and 0 <= i2 < nu) or seen[j2][i2]:
                continue
            h1 = H[j2][i2]
            if h1 is None or abs(h1 - h0) > 0.60:
                continue
            a = (u0 + iu * st, v0 + jv * st); b = (u0 + i2 * st, v0 + j2 * st)
            if any(_seg_x(a, b, c, e) for c, e in segs):
                continue
            seen[j2][i2] = True
            prev[(j2, i2)] = (jv, iu)
            stack.append((j2, i2))
    return None


def kekkai_check(d):
    """**結界が閉じているか。**三段で見る:
    ① 区間どうしが継がるか(継ぎ目は開口か渡廊下か棟か)
    ② **両端が何かに取り付いているか** — 棟・渡廊下・竹垣・段の縁・他の結界のいずれかへ
       `const.inubashiri` 以内。⛔ 端が宙に浮いた塀は塀ではない(2026-09-02 検図 K057)
    ③ **開口を全部閉じたとき、表から奥へ屋外で抜けられないこと**(経路探索)。
       ⭐ 歩く範囲は**主面の法肩から上だけ**【2026-09-02 ユーザー裁定=案B】— 理由は `_walk_grid`。
    ④ 動線が開口の外で横切っていないこと"""
    K = d["const"]["ken"]
    bad = []
    W = d.get("kekkai", [])
    # ⛔ **「結界がある」を前提にしない。**2026-09-02: `kekkai` を空にしても件数が動かず、
    #   破壊試験「結界を全部消す」が **1件 → 1件**で偽になっていた(経路の指摘が1件出るだけで
    #   数が増えない)。⭕ 区間が無いこと自体を1件として出す。
    if not W:
        bad.append("**結界が1区間も無い** — 表と奥を屋外で分けるという宣言が実体を持たない")
    boxes = [(m["name"], m["u0"], m["v0"], m["u1"], m["v1"]) for m in d["munes"]] + \
            [(l["name"], l["u0"], l["v0"], l["u1"], l["v1"]) for l in d["links"]]

    def in_box(u, v, pad=0.0):
        return [n9 for n9, a0, b0, a1, b1 in boxes
                if a0 - pad <= u <= a1 + pad and b0 - pad <= v <= b1 + pad]
    for i9 in range(len(W) - 1):
        a, b = W[i9], W[i9 + 1]
        if a.get("chain") is False or b.get("chain") is False:
            continue
        gap = math.hypot(b["a"][0] - a["b"][0], b["a"][1] - a["b"][1])
        if gap < 1e-6:
            continue
        mu = (a["b"][0] + b["a"][0]) / 2.0; mv = (a["b"][1] + b["a"][1]) / 2.0
        if not in_box(mu, mv, 0.25):
            bad.append("結界 %s の終点と %s の始点の間が %.2f間 空く(継ぎ手が渡廊下でも棟でもない): "
                       "(%.2f, %.2f)" % (a["name"], b["name"], gap, mu, mv))
    # ② 両端の取り付き
    lim = d["const"]["inubashiri"] / K
    rails = auto_rails(d)
    for w in W:
        for lab, q in (("始点", tuple(w["a"])), ("終点", tuple(w["b"]))):
            if in_box(q[0], q[1], lim):
                continue
            if any(w2 is not w and
                   min(math.hypot(q[0] - x[0], q[1] - x[1]) for x in (w2["a"], w2["b"])) <= lim
                   for w2 in W):
                continue
            if any(min(math.hypot(q[0] - a9[0], q[1] - a9[1]) for a9 in rl["pts"]) <= lim
                   for rl in rails):
                continue
            # ⚠ 段の縁は**輪郭線までの距離**で見る(`tdist` は段の中で 0 を返すので使えない —
            #   段の真ん中に浮いた端が「縁に付いている」と読まれる。2026-09-02 検図)
            de = min(sashizu_lib.poly_edge_dist(tpoly(t), q[0], q[1]) for t in d["terraces"])
            if de <= lim:
                continue
            if _on_walled_edge(d, q[0], q[1], d["const"]["inubashiri"] + 0.05):
                continue                        # 外周の練塀・長屋・木柵へ突き付ける
            dd = min([de] +
                     [min([min(math.hypot(q[0] - a9[0], q[1] - a9[1]) for a9 in rl["pts"])
                           for rl in rails] or [9e9])])
            bad.append("結界 %s の%s (%.2f, %.2f) がどこにも取り付いていない — "
                       "最寄りの受け(段の縁か竹垣)まで %.2fm。⛔ 端が宙に浮いた塀は塀ではない"
                       % (w["name"], lab, q[0], q[1], dd * K))
    # ③ 開口を閉じて表↔奥が非連結か
    path = kekkai_reach(d, closed=True, scope="hogata")
    if path:
        cross = None
        for a9, b9 in zip(path, path[1:]):
            if (a9[1] - 79.0) * (b9[1] - 79.0) <= 0 and a9[1] != b9[1]:
                cross = a9
                break
        bad.append("**開口を全部閉じても表から奥へ屋外で抜けられる**(升 %d歩%s)"
                   % (len(path), " ／ v=79 を u=%.2f で越える" % cross[0] if cross else ""))
    # ④ 動線が開口の外で横切らない
    for r in d.get("routes", []):
        for a, b in zip(r["pts"], r["pts"][1:]):
            for w in W:
                wa, wb = w["a"], w["b"]
                vert = abs(wa[0] - wb[0]) < 1e-9
                p0, p1 = (a[0], b[0]) if vert else (a[1], b[1])
                line = wa[0] if vert else wa[1]
                if (p0 - line) * (p1 - line) > 0 or abs(p1 - p0) < 1e-12:
                    continue
                t9 = (line - p0) / (p1 - p0)
                q = a[1] + (b[1] - a[1]) * t9 if vert else a[0] + (b[0] - a[0]) * t9
                lo, hi = (min(wa[1], wb[1]), max(wa[1], wb[1])) if vert else \
                         (min(wa[0], wb[0]), max(wa[0], wb[0]))
                if not (lo - 1e-9 <= q <= hi + 1e-9):
                    continue
                gp = w.get("gap")
                if gp and min(gp["from"], gp["to"]) - 1e-9 <= q <= max(gp["from"], gp["to"]) + 1e-9:
                    continue
                pu, pv = (line, q) if vert else (q, line)
                if in_box(pu, pv, 0.25):
                    continue
                bad.append("動線 %s が結界 %s を開口の外で横切る(%s=%.2f)"
                           % (r["label"], w["name"], "u" if vert else "v", q))
    return bad


def niwa_earth_check(d, ter):
    """**庭の土量の収支が閉じるか。**掘削 = 築山 + 余り。余りが負(=土が足りない)なら、
    どこかから運ぶことになるので宣言と食い違う。"""
    e = niwa_earth(d, ter)
    bad = []
    if e["surplus"] < -1.0:
        bad.append("池の掘削 %.0f m³ に対し築山が %.0f m³ — 不足 %.0f m³(掘削土だけでは築けない)"
                   % (e["dig"], e["fill"], -e["surplus"]))
    if abs((e["bed"] + e["bank"]) - e["dig"]) > 1.0:
        bad.append("掘削の内訳(床 %.0f + 岸 %.0f)が合計 %.0f と合わない"
                   % (e["bed"], e["bank"], e["dig"]))
    if e["fill"] > 1.0:
        tot = sum(x[2] for x in e["mounds"])
        if abs(tot - e["fill"]) > 1.0:
            bad.append("築山の内訳が合計と合わない")
    b = earth_breakdown(d, ter)
    part = b["holeIn"] + b["pond"] + b["mound"]
    if abs(part - b["sum"]) > 1.0:
        bad.append("客土の内訳の四項 %.0f が、独立に積んだ合計 %.0f と合わない(差 %.0f m³)"
                   % (part, b["sum"], part - b["sum"]))
    # ⭐ **平坦化しないと宣言した区画が、縁からの法面で結局埋め立てられていないか。**
    #   ⛔ 従前の「抜きの縁に新しく出る法面 +0」は**恒等的にゼロ**で永久に沈黙していた
    #     (2026-09-02 検図 K059)。物差しを「抜きの中で盛土が残った升の割合」に取り直す —
    #     過半が盛られているなら「平坦化しない」という宣言が実質を失っている。
    # ⭐ **抜きの中に残る盛土の総量**で見る。⛔ 割合で見ると `batterFill` を緩めても
    #   区画ごとに増減が打ち消し合って**反応しなかった**(2026-09-02: 1:1.5→1:3 で 0件→0件)。
    #   総量は 860→1146 と素直に動く。予算 `grading.holeLeftMaxM3` は**当方が置いた許容**で確度U。
    cap9 = (d.get("grading", {}).get("holeLeftMaxM3") or {}).get("m3")
    if cap9 and b["holeLeft"] > cap9:
        bad.append("平坦化しないと宣言した区画に残る盛土が %.0f m³ で、許容 %.0f m³ を超える — "
                   "法面(1:%.1f)が抜きの奥まで入り込んでいる(区画別は土量の表)"
                   % (b["holeLeft"], cap9, d["const"]["batterFill"]))
    return bad


def mikoro_check(d):
    """**見所が座敷の入側(または庭の中)にあり、見るものが視線の中にあるか。**"""
    K = d["const"]["ken"]
    bad = []
    for g in d["gardens"]:
        for mk in (g.get("mikoro") or []):
            u, v = mk["u"], mk["v"]
            onedge = any(abs(u - m[k9]) < 0.05 or abs(v - m[j9]) < 0.05
                         for m in d["munes"]
                         for k9, j9 in (("u0", "v0"), ("u1", "v1"))
                         if m["u0"] - 0.05 <= u <= m["u1"] + 0.05
                         and m["v0"] - 0.05 <= v <= m["v1"] + 0.05)
            if not (onedge or g_in(g, u, v)):
                bad.append("見所%s『%s』(%.2f, %.2f) が座敷の入側でも庭の中でもない"
                           % (MARU[mk["no"] - 1], mk["label"], u, v))
            if mk.get("eyeY") is not None:
                gy = graded_y(d, u, v, _dem_at(d, u, v))
                if gy is not None and mk["eyeY"] < gy:
                    bad.append("見所%s の眼高 %.2f が足元の地盤 %.2f より低い"
                               % (MARU[mk["no"] - 1], mk["eyeY"], gy))
            # **借景の見所は、視軸の法肩の柵が「堤の天端」より視線を切らないこと。**
            # ⭐ 物差しは「柵が新たな遮蔽物になるか」。堤の天端(自然の遮蔽)より
            #   きつい傾きで視線を切るなら、その柵が景を殺している。
            sk9 = g.get("shakkei")
            if sk9 and mk.get("target") == "shakkei":
                # **床几の視線が、法肩の柵の天端の上を `railClear` 以上で通るか。**
                # ⭐ 2026-09-03 庭方 K210: 物差しを一本化した —
                #   ・眼 = 従属値(基準身長)/ ・柵の v = 其十八の竹垣の線(`rail_v_at`)
                #   ・足元 = **造成面**(`graded_y`。⛔ 地山ではない)
                #   ・天端 = 足元 + (視軸の区間なら `railH`、外なら `const.takegakiH`)
                # ⛔ 斜めの距離で測らない(同じ u の v の差で測る)。
                sm9 = shakkei_metrics(d)
                vr9 = rail_v_at(d, mk["u"])
                if sm9 and sm9.get("crestM") and vr9 is not None:
                    gy9 = graded_y(d, mk["u"], vr9, _dem_at(d, mk["u"], vr9))
                    inax = (sk9.get("railU0") is not None
                            and sk9["railU0"] - 1e-9 <= mk["u"] <= sk9["railU1"] + 1e-9)
                    hh9 = sk9.get("railH") if inax else d["const"]["takegakiH"]
                    top = (gy9 or 0.0) + (hh9 or 0.0)
                    dist = max((vr9 - mk["v"]) * K, 1e-9)
                    ray = mk["eyeY"] + (sm9["crestY"] - mk["eyeY"]) / sm9["crestM"] * dist
                    need = sk9.get("railClear", 0.15)
                    if ray - top < need - 1e-6:
                        bad.append("見所%s(眼 %.2f)の視線が、法肩の%s(v%.2f・造成面 %.2f + h%.2f "
                                   "= 天端 %.2f)の上を %.3fm しか通らない — %.2fm 以上要る"
                                   "(⚠ 足元は**造成面**であって地山ではない)"
                                   % (MARU[mk["no"] - 1], mk["eyeY"],
                                      (sk9.get("railKata") if inax else "竹垣"), vr9,
                                      gy9 or 0.0, hh9 or 0.0, top, ray - top, need))
    return bad


# ---------------------------------------------------------------- 庭の表(数値はすべて算出)
def _tw(head, rows, foot=""):
    return ("<div class='tw'><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>%s"
            % ("".join("<th%s>%s</th>" % (" class='note'" if h.startswith("*") else "",
                                          h.lstrip("*")) for h in head),
               "".join("<tr>%s</tr>" % "".join("<td%s>%s</td>"
                                               % (" class='note'" if str(c).startswith("*") else "",
                                                  str(c).lstrip("*")) for c in r) for r in rows),
               ("<p class='cap'>%s</p>" % foot) if foot else ""))


ON_JA = {"面": "面(24.80に均す)", "地なり": "地なり(平坦化しない)", "面+法肩": "面+法肩(西端は地なり)"}
KIND_JA = {"kansho": "鑑賞", "shirasu": "白洲", "sagyo": "作業場", "jurin": "樹林"}


def gardens_table(d):
    K = d["const"]["ken"]
    rows = []
    tot = 0.0
    for g in d["gardens"]:
        a = g_area(g) * K * K / TSUBO
        tot += a
        rows.append(["<b>%s</b>" % g["label"], "<code>%s</code>" % g["name"],
                     "u %.1f〜%.1f / v %.1f〜%.1f" % (g["u0"], g["u1"], g["v0"], g["v1"]),
                     "%.0f 坪" % a, ON_JA.get(g.get("on"), "—"), KIND_JA.get(g.get("kind"), "—"),
                     "○" if g.get("katteFree") else "—",
                     "*" + cert_sig(d, g)])
    return _tw(["庭", "*名", "*割り当ての矩形", "実形の面積", "面の作り方", "性格", "勝手動線を入れない", "*確度"],
               rows,
               "<b>実形の面積は算出値</b> — 割り当ての矩形から<b>棟・付属屋・渡廊下の足跡</b>を引き、"
               "段の外輪(または区画)で切った残り。合計 <b>%.0f 坪</b>。"
               "⭐ <b>割り当ての矩形どうしは重ならない</b>(2026-09-02 に庭方が境界を引き直した。"
               "暫定だった『§4 の並び順で上位が取る』規則は撤去してある) — "
               "重なりの復活は <code>garden_alloc_check</code> が毎回見張る。"
               % tot)


def pond_table(d):
    m = pond_metrics(d)
    g, mg, ring = pond_of(d)
    K = d["const"]["ken"]
    sw = m["saw"]
    rows = [
        ["水面(**施工形状**=平滑後)", "%.1f 間² = %.0f m² = <b>%.0f 坪</b>(庭 %.0f坪の %.0f%%)"
         % (m["sm"]["areaKen"], m["sm"]["areaM2"], m["sm"]["tsubo"],
            m["gardenTsubo"], 100.0 * m["sm"]["tsubo"] / max(m["gardenTsubo"], 1e-9))],
        ["水面(**設計値**=生の %d 点)" % m["raw"]["n"],
         "%.1f 間² = %.0f m² = %.0f 坪" % (m["raw"]["areaKen"], m["raw"]["areaM2"], m["raw"]["tsubo"])],
        ["<b>円形度 4πA/P²</b>",
         "<b>施工形状 %.3f</b>(合否はこちら)／ 設計値 %.3f ／ 周長 %.1fm(設計値 %.1fm)"
         % (m["sm"]["circ"], m["raw"]["circ"], m["sm"]["perimM"], m["raw"]["perimM"])],
        ["設計値の頂点間隔", "平均 %.2f間・最小 %.2f・最大 %.2f・<b>CV %.3f</b>"
         % (m["spMean"], m["spMin"], m["spMax"], m["spCV"])],
        ["汀線の最狭(施工形状)", "%.2fm(点%d↔点%d)" % (m["kubireM"], m["kubireA"] + 1, m["kubireB"] + 1)],
        ["中島の両側の水面", " / ".join("%.2f間" % x for x in m["nakaFlank"])],
        ["汀 → 書院棟の入側(u=0)", "%.2f 間" % m["dShoin"]],
        ["汀 → 玄関棟の西面(v=63)", "%.2f 間" % m["dGenkan"]],
        ["汀 → 結界塀 W1(v=79)", "%.2f 間" % m["dKekkai"]],
        ["汀 → 築山Aの裾", "%.2f 間" % m["dTsukiyama"]],
        ["<b>掘り込みであること</b>",
         "汀の内側の江戸期地盤 <b>%.2f〜%.2f</b>(%d セル)。水面 %.2f より低いセル <b>%d/%d</b>"
         % (m["natMin"], m["natMax"], m["cells"], mg["waterY"], m["below"], m["cells"])],
        ["見隠れ(主視点から見える水面)", "<b>%.0f%%</b>(%d 標本)" % (m["visPct"], m["visN"])],
    ]
    if sw:
        sl = mg.get("shallow") or {}
        rows += [["沢飛石(渡り)",
                  "<b>%d 枚</b>・全長 %.2fm・芯々 %.3fm(%.3f間)・天端 %.2f(=水面+%.2f)"
                  "<br>石の大きさ <b>長軸 %.2f〜%.2fm</b>(⛔ 半径ではない。目地 %.2f〜%.2fm)"
                  % (sw["n"], sw["lenM"], sw["pitchM"], sw["pitchKen"],
                     g["sawatobi"][0]["topY"], g["sawatobi"][0]["topY"] - mg["waterY"],
                     g["sawatobi"][0]["rMin"], g["sawatobi"][0]["rMax"],
                     max(0.0, sw["pitchM"] - g["sawatobi"][0]["rMax"]),
                     max(0.0, sw["pitchM"] - g["sawatobi"][0]["rMin"]))],
                 ["渡りの区間の実水面幅",
                  "<b>%.2f間 = %.2fm</b>(⛔ この幅に橋を架けない。水深は %.2fm 一定で池床 %.2f)"
                  % (sw["widthKen"], sw["widthM"], sw["depth"], sl.get("bedY", mg["bedY"]))]]
    for nj9 in (g.get("nakajima") or []):
        nk = m.get("naka") or {}
        rows.append(["中島(輪郭は %d 点)" % len(nj9.get("poly") or []),
                     "面積 <b>%.1f m²</b>・周長 %.1fm・円形度 %.3f・主軸 %+.1f° ／ "
                     "汀石 %d 個(<b>長軸 %.2f〜%.2fm</b>。⛔ 半径ではない)"
                     % (nk.get("areaM2", 0), nk.get("perimM", 0), nk.get("circ", 0),
                        nk.get("axisDeg", 0), nj9.get("stones", 0),
                        nj9.get("stoneRMin", 0), nj9.get("stoneRMax", 0))])
    for rg in m["rangui"]:
        rows.append(["乱杭", "汀に沿う弧長 %.2fm ／ 芯々 %.3fm → <b>%d 本</b>(本数は従属値)"
                     % (rg["lenM"], rg["pitch"], rg["n"])])
    if m["tobi"]:
        rows.append(["飛石", "筋の長さ %.1fm ／ 芯々 %.2f〜%.2fm なら <b>%d〜%d 石</b>"
                     % (m["tobi"]["lenM"], g["tobiishi"][0]["pitchMin"],
                        g["tobiishi"][0]["pitchMax"], m["tobi"]["nMin"], m["tobi"]["nMax"])])
    return _tw(["検算", "算出値"], [[a, b] for a, b in rows],
               "<b>この表の値はすべてこの図が毎回算出する。</b>設計値ファイルにも文章にも写さない"
               "(CLAUDE.md 規則4)。⭐ <b>『施工形状』と『設計値』を必ず区別する</b> — "
               "実際に掘るのは <b>Chaikin×2 を掛けた後の汀線</b>で、生の点列は設計値にすぎない。"
               "<b>合否は施工形状の円形度で見る</b>(2026-09-02 庭方)。"
               "⚠ <b>『掘り込みであること』は宣言ではなく実測</b> — 台地は平坦で、"
               "汀の内側に水面より低い自然の窪みは無い。"
               "⚠ <b>見隠れが不透明として数えるのは6種だけ</b> — "
               "<b>地盤(築山を含む)／中島／岩島／沢飛石／景石／灯籠</b>。"
               "植栽は枝越しに見えるので数えない(2026-09-02 庭方(う))。")


def tsukiyama_table(d):
    rows = []
    for o in tsukiyama_metrics(d):
        ts = o["ts"]
        rows.append(["<b>%s</b>" % ts["label"],
                     "(%.1f, %.1f)" % (ts["u"], ts["v"]),
                     "%.1f × %.1f 間" % (ts["dU"], ts["dV"]),
                     "%.2f" % ts["topY"],
                     "<b>%.2f〜%.2f(平均 %.2f)</b>" % (o["natMin"], o["natMax"], o["natMean"]),
                     "%.2f m" % o["h"],
                     "<b>%.0f m³</b>" % o["volM3"],
                     "%.0f 坪" % o["planTsubo"],
                     "%.2f 間²" % o["outKen"],
                     "*%s から %.1fm・視線の %.1f° 上" % (o.get("viewFrom", "—"),
                                                       o.get("distM", 0), o.get("elevDeg", 0))])
    return _tw(["築山", "芯", "底径", "頂", "底の自然地盤(実測)", "高さ", "盛土", "平面", "段の外へ出る", "*主視点から"],
               rows,
               "<b>底の自然地盤は江戸期の復元地盤を1間格子で実測した値</b>(セル平均)。"
               "⛔ <b>『自然の高まりに載る』とは書かない</b> — 奥庭は完全に平坦で、"
               "<b>築山Bは全量が人の盛土</b>である。築山Aの底は池側よりわずかに高いが、"
               "<b>盛土量は同じく全量が盛土</b>。盛土は「裾で自然地盤・頂で頂高」の円錐として算出した"
               "(頂に平場を切らない)。")


def niwa_earth_table(d, ter):
    """**土量は一枚の表にまとめる。**⛔ 同じ量を二つの章で別々の基準で刷らない。
    上段=「客土がどこで増減したか」(基準=**素の設計**: 抜きも庭の土工も無い形)/
    下段=「庭で動かす土そのもの」(基準=**江戸期の復元地盤**)。**基準を必ず併記する。**"""
    b = earth_breakdown(d, ter)
    e = niwa_earth(d, ter)
    gr = d["grading"]["haryoJi"]
    cur = gr["moridoM3"] - gr["kiridoM3"]
    rows = [["<b>素の設計の差引</b>(抜きも庭の土工も無く、主面を一枚に均した形)",
             "<b>%+d m³</b>" % int(round(cur - b["sum"]))]]
    for lb, v in b["per"].items():
        rows.append(["　平坦化しない — %s <span class='note'>(割り当て %.0f 間²のうち"
                     "段に掛かるのは %.0f 間² = %.0f%%)</span>"
                     % (lb, v["rectKen"], v["usedKen"],
                        100.0 * v["usedKen"] / max(v["rectKen"], 1e-9)),
                     "%+d m³" % int(round(v["m3"]))])
    rows += [["　抜きの中に残る盛土(縁からの法面が入り込む)", "%+d m³" % int(round(b["holeLeft"]))],
             ["　書院の泉水(床と岸)", "%+d m³" % int(round(b["pond"]))],
             ["　築山A・B", "%+d m³" % int(round(b["mound"]))],
             ["<b>当図の差引 = 残る客土</b>(盛 %d − 切 %d)" % (gr["moridoM3"], gr["kiridoM3"]),
              "<b>%+d m³</b>" % cur]]
    rows.append(["<b>庭で動かす土</b>(基準=<b>江戸期の復元地盤</b>。上段とは基準が違う)", "&nbsp;"])
    rows += [["　池の床の掘削", "− %d m³" % int(round(e["bed"]))],
             ["　岸の摺り付け(汀から %.1f間)" % pond_of(d)[1]["bankRun"],
              "− %d m³" % int(round(e["bank"]))]]
    for g9, ts9, v9 in e["mounds"]:
        rows.append(["　%s の盛土" % ts9["label"], "+ %d m³" % int(round(v9))])
    rows.append(["　<b>掘削 %d − 築山 %d = 余り %d m³</b>(主面・門前面の一般盛土へ回す)"
                 % (int(round(e["dig"])), int(round(e["fill"])), int(round(e["surplus"]))),
                 "&nbsp;"])
    return _tw(["土量", "算出値"], rows,
               "<b>この表の値はすべてこの図が算出する。</b>上段は同じ格子を"
               "<b>三つの設計(素の設計 / 抜きだけ / 当図)で歩いた差</b>で、四項の合計は"
               "『当図の差引 − 素の設計の差引』に一致する(検査 <code>niwa_earth_check</code>)。"
               "⚠ <b>上段と下段は基準が違うので足したり引いたりしない</b> — "
               "下段の池は自然地盤に対する掘削量、上段の池は「素の設計では盛土していた分」を"
               "含む差である。"
               "⭐ <b>平坦化しない区画の効きが割り当ての坪数どおりにならないのは、"
               "割り当ての矩形が段(主面の多角形)に掛かる割合が区画ごとに違うから</b> — "
               "とくに西端の帯と奥の紅葉谷は大半が段の外(もともと造成していない)。"
               "<b>残る客土の出所は json <code>grading.kyakudo</code></b>(確度U・考証方の確認待ち)。")


def mikoro_table(d):
    K = d["const"]["ken"]
    rows = []
    for g in d["gardens"]:
        for mk in (g.get("mikoro") or []):
            tgt = None
            if mk.get("target") == "migiwa":
                _g0, _m0, r0 = pond_of(d)
                tgt = _cen(r0) if r0 else None
            elif mk.get("target") not in (None, "self", "shakkei"):
                tgt = next(((t["u"], t["v"]) for _g2, t in mounds_of(d)
                            if t["name"] == mk["target"]), None)
            if tgt:
                du, dv = tgt[0] - mk["u"], tgt[1] - mk["v"]
                azim = "u%+.1f / v%+.1f(%s)" % (du, dv, rel({"u0": mk["u"], "u1": mk["u"],
                                                             "v0": mk["v"], "v1": mk["v"]},
                                                            {"u0": tgt[0], "u1": tgt[0],
                                                             "v0": tgt[1], "v1": tgt[1]}))
                dist = "%.1f m" % (math.hypot(du, dv) * K)
            else:
                azim, dist = ("西(溜池)" if mk.get("target") == "shakkei" else "—"), "—"
            rows.append([MARU[mk["no"] - 1], mk["label"], "(%.1f, %.1f)" % (mk["u"], mk["v"]),
                         "%.2f" % mk["eyeY"], azim, dist,
                         "*" + " ／ ".join(mk.get("sees") or [])])
    # ⛔ **西の斜面と岸の見所も入れる**(2026-09-02 庭方: 其十三に一行も出ていなかった)
    for m9 in ((d.get("nishi") or {}).get("mikoro") or []):
        rows.append([MARU[m9["no"] - 1], m9.get("label", ""),
                     "(%.1f, %.1f)" % (m9["u"], m9["v"]), "%.2f" % m9.get("eyeY", 0),
                     "西(溜池)", "—", "*" + " ／ ".join(m9.get("sees") or [])])
    rows.sort(key=lambda r9: MARU.index(r9[0]) if r9[0] in MARU else 99)   # ⛔ 番号順に並べる
    return _tw(["#", "見所", "位置", "眼高", "視線の向き(算出)", "距離", "*見えるもの"], rows,
               "<b>視線の向きと距離は算出値</b>(見所の点と `target` の点から出す)。"
               "⭐ <b>眼高はすべて基準身長 %.2fm から出す</b>(2026-09-03 考証4巡目) — "
               "畳の座視 ×%.2f(段の面+御殿の床の上)/ 床几の座視 ×%.2f / 立位 ×%.2f"
               "(いずれも足元の物の天端の上)。⛔ 座視と立位を別々の人の値で持たない。"
               "⚠ 身長も比も<b>確度U</b>([江戸期の人体寸法] は未入手)。u+ = 北 / v+ = 西。"
               % (d["const"]["bodyH"], d["const"]["eyeRatio"]["tatami"],
                  d["const"]["eyeRatio"]["shogi"], d["const"]["eyeRatio"]["stand"]))


def shokusai_table(d):
    rows = []
    for g in d["gardens"]:
        def emit(owner, sk):
            rng = ""
            if "u0" in sk:
                rng = "u %.1f〜%.1f / v %.1f〜%.1f" % (sk["u0"], sk["u1"], sk["v0"], sk["v1"])
            elif sk.get("pts"):
                rng = _ptrunc([(a, b) for a, b in sk["pts"]])
            elif sk.get("where"):
                rng = sk["where"]
            pit = ""
            if sk.get("pitchMin"):
                pit = "%.1f〜%.1f 間" % (sk["pitchMin"], sk["pitchMax"])
            rows.append([owner, sk.get("layer", "—"), sk.get("species", "—"),
                         (str(sk["n"]) + " 本") if sk.get("n") else "—", pit or "—",
                         "*" + (rng or "—"), "*" + cert_sig(d, sk)])
        for sk in (g.get("shokusai") or []):
            emit(g["label"], sk)
        for ts in (g.get("tsukiyama") or []):
            for sk in (ts.get("shokusai") or []):
                emit("%s / %s" % (g["label"], ts["label"]), sk)
    for g in d["gardens"]:
        for kk in (g.get("karikomi") or []):
            rows.append([g["label"], "刈込", kk.get("species", "—"),
                         ("株数 %s" % kk["kabu"]) if kk.get("kabu") else "—",
                         ("h %.1fm" % kk["h"]) if kk.get("h") else "—",
                         "*" + (kk.get("where") or
                                ("u %.1f〜%.1f / v %.1f〜%.1f"
                                 % (kk["u0"], kk["u1"], kk["v0"], kk["v1"]) if "u0" in kk else "—")),
                         "*" + cert_sig(d, kk)])
        for ts in (g.get("tsukiyama") or []):
            for kk in (ts.get("karikomi") or []):
                rows.append(["%s / %s" % (g["label"], ts["label"]), "刈込", kk.get("species", "—"),
                             ("株数 %s" % kk["kabu"]) if kk.get("kabu") else "—",
                             ("h %.1fm" % kk["h"]) if kk.get("h") else "—",
                             "*" + (kk.get("where") or "—"), "*U"])
    # ⛔ **西の斜面と岸の約200本も入れる**(2026-09-02 庭方: 植栽表に一行も出ていなかった)
    N9 = d.get("nishi") or {}
    hy9 = N9.get("hayashi") or {}
    for t9 in (hy9.get("takagi") or []):
        # ⛔ **種ごとの芯々があればそれを刷る**(2026-09-03 庭方4巡目 K165) —
        #   クロマツは林の中で 8〜16m の大きな不等間隔なのに、林ぜんたいの値を刷っていた。
        pit9 = ([t9["pitchMin"], t9["pitchMax"]] if t9.get("pitchMin") is not None
                else (hy9.get("takagiPitch") or [0, 0]))
        rows.append(["西の斜面(林)", "高木", t9["species"], "%d 本" % t9["n"],
                     "%.1f〜%.1f m" % tuple(pit9),
                     "*丈 %d〜%d m%s" % (t9["hMin"], t9["hMax"],
                                        ("・" + t9["_"]) if t9.get("_") else ""),
                     "*" + cert_sig(d, t9 if t9.get("certSig") else hy9)])
    for c9 in (hy9.get("chuboku") or []):
        rows.append(["西の斜面(林)", "中木", c9["species"], "%d 株" % c9["n"],
                     "%.1f〜%.1f m" % tuple(hy9.get("chubokuPitch") or [0, 0]),
                     "*" + (c9.get("_") or ""), "*U"])
    hk9 = N9.get("hokata") or {}
    if hk9:
        rows.append(["西の斜面(法肩帯)", "高木", "クロマツ", "%d 本" % hk9.get("n", 0),
                     "%.1f〜%.1f 間" % (hk9.get("pitchMin", 0), hk9.get("pitchMax", 0)),
                     "*丈 %.1f〜%.1f m・%s" % (hk9.get("hMin", 0), hk9.get("hMax", 0),
                                             hk9.get("lean", "")),
                     "*" + cert_sig(d, hk9)])
    # ⛔ **西の帯の層も植栽表に出す**(2026-09-03 庭方5巡目 K236)
    ts9 = N9.get("tsutsumi") or {}
    su8 = (N9.get("hojiri") or {}).get("susuki") or {}
    if su8:
        rows.append(["西の斜面(法尻の帯)", "草本", "ススキ", "%d〜%d 株" % (su8.get("nMin", 0),
                                                                    su8.get("nMax", 0)),
                     "—", "*v%.0f〜%.0f・棟から %.1f間 以上・丈 %.1f〜%.1fm"
                     % (su8.get("v0", 0), su8.get("v1", 0), su8.get("clearKen", 0),
                        su8.get("hMin", 0), su8.get("hMax", 0)), "*U"])
    bD2 = next((b9 for b9 in (d.get("slopeBands") or []) if b9["name"].startswith("D2")), None)
    if bD2:
        rows.append(["西の斜面(帯D2)", "地被", "ノシバの刈芝", "—", "—",
                     "*%s" % bD2.get("veg", ""), "*" + cert_sig(d, bD2)])
    for nm8, key8 in (("葭原", "yoshi"), ("蓮", "hasu")):
        o8 = ts9.get(key8) or {}
        if not o8:
            continue
        rows.append(["西の岸(%s)" % nm8, "水辺", nm8, "—", "—",
                     "*" + (("幅 %.0f〜%.0fm・稈高 %.1f〜%.1fm" % (o8.get("wMin", 0),
                                                              o8.get("wMax", 0),
                                                              o8.get("hMin", 0),
                                                              o8.get("hMax", 0)))
                            if key8 == "yoshi" else
                            ("汀から %.0f〜%.0fm・葉高 水面+%.1f〜%.1f"
                             % (o8.get("fromM", 0), o8.get("toM", 0),
                                o8.get("leafMin", 0), o8.get("leafMax", 0)))), "*S/B/U"])
    hj9 = N9.get("hojiri") or {}
    if hj9.get("enoki"):
        rows.append(["西の斜面(法尻の帯)", "高木", "エノキ", "%d 本" % len(hj9["enoki"]),
                     "単木", "*丈 %d〜%d m・⛔ 窓の外・代替が効かないので新造"
                     % (hj9["enoki"][0]["hMin"], hj9["enoki"][0]["hMax"]), "*U"])
    return _tw(["庭", "層", "樹種", "本数", "芯々", "*範囲", "*確度"], rows,
               "⛔ <b>開花木(春の桜)は置かない</b>(CLAUDE.md 規則10)。斜面の植生は"
               "松+雑木で、<b>竹林にしない</b>([橋本・堀1998] 朱引内79事例中1例)。"
               "<b>樹種の類型は B、本数と位置は U。</b>"
               "⚠ 確度 <b>?</b> の行は<b>庭方の指定が無い</b>もの — 当方は埋めない。")


def kekkai_table(d):
    K = d["const"]["ken"]
    rows = []
    for w in d.get("kekkai", []):
        a, b = w["a"], w["b"]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) * K
        gp = w.get("gap")
        y0 = graded_y(d, a[0], a[1], _dem_at(d, a[0], a[1]))
        y1 = graded_y(d, b[0], b[1], _dem_at(d, b[0], b[1]))
        rows.append(["<code>%s</code>" % w["name"], w["label"],
                     "(%.1f, %.1f) → (%.1f, %.1f)" % (a[0], a[1], b[0], b[1]),
                     "%.1f m" % L, "%.2f m" % w["h"], w["kata"],
                     ("%s %.1f〜%.1f(%.2fm)" % (gp["kind"], gp["from"], gp["to"],
                                               abs(gp["to"] - gp["from"]) * K)) if gp else "—",
                     "%.2f → %.2f" % (y0 or 0, y1 or 0)])
    return _tw(["記号", "線", "端点(グリッド)", "延長", "高さ", "構法", "開口", "足元の地盤(算出)"], rows,
               "<b>延長と足元の地盤は算出値。</b>塀は外構の練塀より軽い<b>のし塀+瓦</b>とする"
               "(屋敷内部の仕切り)。⭐ <b>結界は崖の上まで</b>【2026-09-02 ユーザー裁定=案B】 — "
               "屋外の結界が受け持つのは<b>主面の上だけ</b>で、W6 は段の縁(法肩)で終える。"
               "⛔ <b>「結界は屋外で閉じている」とは書かない。</b>"
               "西の法肩から下(崖と、その下の平らな帯)は<b>表でも奥でもない、屋敷の外構の地</b>と"
               "位置づける — 内部を分けるための塀を崖に下ろすのは当家の格に合わず、典拠も無い。"
               "⭕ 「表と奥を分ける」ことの実体は<b>御錠口(確度A)</b>で、"
               "屋外の結界はもともと当方の外挿(<b>確度U</b>)である。"
               "主面の上では 東=書院棟+W1〜W5 / 南=W6 / 西と北=法肩の竹垣と段の縁 が受け持つ。"
               "継ぎ目が空く所は<b>渡廊下か棟が受ける</b>(検査 <code>kekkai_check</code>)。"
               "⚠ 崖と岸の帯の植生・地目は<b>考証方が調査中</b>で、当図はいま空白にしてある。")


def mizu_budget(d):
    """**池の水の収支(m³/日)。⛔ 表にも検査にも同じここから配る**(二箇所で計算しない)。

    入 = 集水域の雨 × 流出係数 + 池面への直接雨 / 出 = 蒸発 + 浸透。
    ⚠ **年平均の粗い収支**で、渇水期の可否はこれでは言えない。⛔ 浸透は悲観値も併せて出す。"""
    g9, _mg, _r = pond_of(d)
    gs = ((g9 or {}).get("mizu") or {}).get("gensen") or {}
    am = gs.get("amegatari") or {}
    ck = gs.get("chokusetsu") or {}
    sh = gs.get("shintou") or {}
    jo = gs.get("johatsu") or {}
    a9 = pond_metrics(d)["areaM2"]
    day = lambda mm: mm / 1000.0 / 365.0
    o = {"rainCatch": am.get("catchM2", 0) * day(am.get("rainMmY", 0)) * am.get("runoff", 1.0),
         "rainDirect": ck.get("m2", 0) * day(am.get("rainMmY", 0)) * ck.get("runoff", 1.0),
         "evap": a9 * day(jo.get("mmY", 0)),
         "seep": a9 * sh.get("mmDay", 0) / 1000.0,
         "seepPess": a9 * sh.get("mmDayPess", 0) / 1000.0}
    o["in"] = o["rainCatch"] + o["rainDirect"]
    o["out"] = o["evap"] + o["seep"]
    o["net"] = o["in"] - o["out"]
    o["netPess"] = o["in"] - (o["evap"] + o["seepPess"])
    return o


def mizu_table(d):
    g, mg, ring = pond_of(d)
    mz = g.get("mizu") or {}
    gs = mz.get("gensen") or {}
    ms = mz.get("mizushiri") or {}
    sd = mz.get("sokodoi") or {}
    K = d["const"]["ken"]
    m = pond_metrics(d)
    am = gs.get("amegatari") or {}
    ck = gs.get("chokusetsu") or {}
    sh = gs.get("shintou") or {}
    jo = gs.get("johatsu") or {}
    b = mizu_budget(d)
    pts = [(ms["higuchi"]["u"], ms["higuchi"]["v"], ms["higuchi"]["sill"])]
    pts.append((ms["ankyo"]["to"][0], ms["ankyo"]["to"][1], ms["ankyo"]["toY"]))
    pts += [(q[0], q[1], q[2]) for q in ms.get("mizo", [])]
    pts += [(q[0], q[1], q[2]) for q in ms.get("houjiri", [])]
    L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])) * K
    ro = am.get("runoff")
    rows = [
        ["水源 ①雨水(集水域)", "集水 %.0f m² × 年 %.0f mm × 流出係数 %s = <b>%.2f m³/日</b>"
         % (am.get("catchM2", 0), am.get("rainMmY", 0),
            ("%.2f" % ro) if ro else "(未設定)", b["rainCatch"])],
        ["水源 ①' 池面への直接雨", "水面 <b>%.0f m²(算出)</b> × 年 %.0f mm × 係数 %.1f "
                                "= <b>%.2f m³/日</b> — ⛔ 池面に流出係数は掛けない"
         % (ck.get("m2", 0), am.get("rainMmY", 0), ck.get("runoff", 1.0), b["rainDirect"])],
        ["止水工", "%s 厚 %.2fm — 掘り込みの泉水は地山が礫層なので敷いて水を留める"
         % ((mz.get("shisui") or {}).get("kata", "?"), (mz.get("shisui") or {}).get("t", 0))],
        ["失う分(浸透)", "水面 %.0f m² × <b>%.1f mm/日</b> = <b>%.2f m³/日</b>"
                         "(悲観 %.1f mm/日 なら <b>%.2f m³/日</b>)【%s】"
         % (m["areaM2"], sh.get("mmDay", 0), b["seep"], sh.get("mmDayPess", 0),
            b["seepPess"], cert_sig(d, sh))],
        ["水源 ②井戸+掛樋",
         "井戸 <code>%s</code> → 掛樋 %.1fm → 石組の水落(高さ %.2fm)"
         % ((gs.get("ido") or {}).get("ref", "?"), (gs.get("kakehi") or {}).get("len", 0),
            (gs.get("mizuochi") or {}).get("h", 0))],
        ["失う分(蒸発)", "水面 %.0f m² × 年 %.0f mm = <b>%.2f m³/日</b>【一般値=B】"
         % (m["areaM2"], jo.get("mmY", 0), b["evap"])],
        ["収支(井戸から汲み足す分)",
         "入 %.2f − 出 %.2f = <b>%+.2f m³/日</b>(悲観の浸透なら <b>%+.2f m³/日</b>)"
         " — ⛔ <b>年平均の粗い収支</b>で、渇水期はこれより厳しい"
         % (b["in"], b["out"], b["net"], b["netPess"])],
        ["水尻(余水吐)",
         "樋口 敷 %.2f → 暗渠 %.1fm(落差 %.2fm = %.1f%%)→ 開渠 %.2f"
         % (ms["higuchi"]["sill"], ms["ankyo"]["len"], ms["ankyo"]["drop"],
            100.0 * ms["ankyo"]["drop"] / ms["ankyo"]["len"], ms["ankyo"]["toY"])],
        ["水尻の全落差 / 延長", "<b>%.2f → %.2f = %.2fm ／ 約 %.0fm</b>(算出)"
         % (pts[0][2], pts[-1][2], pts[0][2] - pts[-1][2], L)],
        ["底樋(池干し)", "敷 %.2f(池床の直下)→ (%.1f, %.1f) で %.2f に開口。長 %.1fm・落差 %.2fm(%.1f%%)"
         % (sd.get("sill", 0), sd["to"][0], sd["to"][1], sd.get("toY", 0),
            sd.get("len", 0), sd.get("drop", 0),
            100.0 * sd.get("drop", 0) / max(sd.get("len", 1), 1e-9))],
        ["土井邸への流出", "<b>無し</b> — 水路の最大 u = %.1f(区画の北の境より内側)"
         % max(q[0] for q in pts)],
    ]
    return _tw(["水の系統", "諸元(算出を含む)"], [[a, b] for a, b in rows],
               "⛔ <b>当図では滝を置かない=U</b>(水源が未決のため)。"
               "⚠ 従前の「落差の源が無い」という理由は成り立たない — "
               "<b>西の斜面に十数mの落差がある</b>(値は「西の斜面と溜池の岸」の章が算出)。"
               "[内藤2024]<b>A</b> は台地端の滝の実例(隣の松平出羽守邸を含む)を挙げる。"
               "⚠ <b>当邸に上水が来ていたかは未決</b> — 「上水は無い(青山上水は享保7年廃止)」は"
               "[玉川上水給水域]<b>A</b> に否定される非論理として撤回した。"
               "<b>井戸+掛樋と底樋の作法=B、諸元=U。</b>"
               "⭐ <b>収支は年平均で赤字</b>(上の行が算出) — <b>渇水期は井戸で汲み足す</b>。"
               "⛔ <b>この収支で「持つ」とは言えない</b> — 年平均の粗い出入りで、"
               "渇水期の日々の出入りも、汲み足しの手間(荷数)も、まだ見ていない。"
               "⚠ 浸透 %s は<b>締固めた粘土張りの一般値</b>で当邸の実測ではない。"
               "⛔ <b>悲観値の側も必ず読む</b> — 汲み足す量が桁で変わる。" % cert_sig(
                   d, (((g.get("mizu") or {}).get("gensen") or {}).get("shintou")) or {}))


def _mk9(d):
    """**床几の座視の見所(⑨)**。⛔ 借景の主視点(⑧・入側の座視)と混ぜない —
    柵に一番きついのは眼の低い床几のほう。"""
    for g9 in d.get("gardens", []):
        for m9 in (g9.get("mikoro") or []):
            if m9.get("eyeMode") == "shogi":
                return m9
    return (shakkei_metrics(d) or {}).get("mk")


def _rail_clear(d, mk, sk, h9):
    """床几の視線が法肩の柵の天端の上を通る余裕[m]。⛔ 図と検査で二度計算しない。"""
    sm = shakkei_metrics(d)
    vr = rail_v_at(d, mk["u"])
    if not sm or not sm.get("crestM") or vr is None:
        return 0.0
    gy = graded_y(d, mk["u"], vr, _dem_at(d, mk["u"], vr)) or 0.0
    dist = max((vr - mk["v"]) * d["const"]["ken"], 1e-9)
    ray = mk["eyeY"] + (sm["crestY"] - mk["eyeY"]) / sm["crestM"] * dist
    return ray - (gy + (h9 or 0.0))


def shakkei_table(d):
    sk = shakkei_metrics(d)
    if not sk:
        return ""
    s = sk["sk"]
    rows = [
        ["視点 → 区画の西端(溜池の堤)", "<b>%.0f m</b>" % (sk["edgeM"] or 0)],
        ["落差", "眼高 %.2f → 溜池の水面 %.2f = <b>%.1f m</b>" % (sk["mk"]["eyeY"], s["waterY"], sk["drop"])],
        ["視線を切る所", "<b>%s</b> — %.0f m 先・標高 %.2f(算出)"
         % (sk["crestKind"], sk["crestM"], sk["crestY"])],
        ["水面が見えはじめる距離",
         "<b>%.0f m 以遠</b>(手前 <b>%.0f m</b> は死角)。⛔ <b>天然の見隠れではない</b> — "
         "この死角を作っているのは<b>当方が辺5に建てた柵(確度U)</b>である"
         % (sk["seeFromM"], sk["blindM"])],
        ["見透しの窓(高木を置かない扇)",
         " → ".join("v%.1f で u%.1f〜%.1f(%.1f間)" % (q[0], q[1], q[2], q[2] - q[1])
                    for q in ((d.get("nishi") or {}).get("mado") or {}).get("fan", []))
         + "。⛔ 平行な帯にしない"],
        ["額縁のクロマツ", "視軸の外(|u| > %.1f)の法肩に芯々 %.1f〜%.1f 間で密に"
         % (s["frameOutside"], s["framePitchMin"], s["framePitchMax"])],
        ["法肩の柵", "視軸の <b>u %.2f〜%.2f</b> だけ %s <b>h%.2f</b> へ落とす"
                   "(扇の上端を柵の v=%.2f へ外挿し、左右に %.1f間 を足した幅=算出)<br>"
                   "⚠ 足元は<b>造成面</b> ／ <b>床几の座視</b>(見所⑨・眼 %.2f)が天端の上を"
                   "通る余裕は <b>%.3fm</b>(要 %.2fm)。⛔ 竹垣 h%.2f のままだと "
                   "<b>%+.3fm</b> で切れる"
         % (s.get("railU0", 0), s.get("railU1", 0), s.get("railKata", ""), s.get("railH", 0),
            s.get("railV", 0), s.get("railClearKen", 0), _mk9(d)["eyeY"],
            _rail_clear(d, _mk9(d), s, s.get("railH")),
            s.get("railClear", 0.15), d["const"]["takegakiH"],
            _rail_clear(d, _mk9(d), s, d["const"]["takegakiH"]))],
    ]
    return _tw(["借景", "実測・算出"], [[a, b] for a, b in rows],
               "<b>借景が実在すること=P</b>(江戸期の復元地盤を視軸に沿って歩いて測った)。"
               "⛔ <b>使い方(視軸の位置・抜く幅・額縁の松・柵の高さ)は当方の設計判断=U。</b>"
               "⚠ <b>溜池の水面は地形DEMに無い</b>(DEM は堤と池底の地面)ので、水面は設計値を使った。")


# ================================================================ 検査の列(唯一の入口)
# ⭐ **すべての検査はこの列に載せる。**`main()` はこの列を回して**0件でも件数を刷る**。
#   ⛔ 図のキャプションにしか出ない検査を作らない。⛔ `if bad:` で囲んで0件のとき黙らせない —
#     「件数が出ない」は黙りと同じ。2026-09-02 の検図で `batter_check` の**24件**が
#     切盛図のキャプションにしか出ておらず、要約は「全項目0件」と刷っていた(K061)。
#   ⭕ **新しい検査はこの列へ足すだけ**にすれば、刷り忘れが構造的に起きない。
#   ⚠ 引数の形が違う検査があるので、列の第2要素は「(d, raw, ter) を受けて件数の並びを返す関数」。
CHECK_LIST = [
    ("往復試験(剥がして組み直すと正典に戻るか)", lambda d, raw, ter: roundtrip_check(raw, pipeline)),
    ("矩形の重なり",                       lambda d, raw, ter: overlap_check(d)),
    ("面のはみ出し(棟・庭が段と区画の中か)",     lambda d, raw, ter: plane_check(d)),
    ("郭の土留めの高さ",                    lambda d, raw, ter: wall_check(d)),
    ("段どうしの接する辺に土留めが載るか",        lambda d, raw, ter: adjacency_check(d)),
    ("確度の本文の写し",                    lambda d, raw, ter: cert_ref_check(d)),
    ("表門の柱割り(江戸間で閉じるか)",         lambda d, raw, ter: gate_module_check(d)),
    ("蹴上",                            lambda d, raw, ter: keri_check(d)),
    ("基壇の露出",                        lambda d, raw, ter: base_check(d)),
    ("隣家の基壇との逆転",                   lambda d, raw, ter: plinth_check(d)),
    ("外周の隅の閉じ",                     lambda d, raw, ter: perimeter_corner_check(d)),
    ("外周の閉じ(全長を歩く)",               lambda d, raw, ter: perimeter_closure_check(d)),
    ("長屋の足跡の支え",                    lambda d, raw, ter: footprint_support_check(d)),
    ("据面の内側の落ち込み・埋没",              lambda d, raw, ter:
        ["%s %d/%d 点・最大 %.2fm" % x for x in seat_fill_check(d)]),
    ("段の縁(落差と自然勾配)",               lambda d, raw, ter: edge_drop_check(d)),
    ("基壇の天端(犬走り+塀の掛かり)",          lambda d, raw, ter: coping_check(d)),
    ("離隔(土蔵の延焼・長屋と塀)",            lambda d, raw, ter: clearance_check(d)),
    ("方位語",                           lambda d, raw, ter: compass_check(d)),
    ("竹垣・勝手動線の交差",                 lambda d, raw, ter: crossing_check(d)),
    ("法面(段の外が現地形へ着地するか)",        lambda d, raw, ter:
        batter_check(d, ter) if ter else []),
    ("在るべき役割の未達(必須・望ましい)",       lambda d, raw, ter:
        ["%s(%s・%s)" % (a9, b9, c9) for a9, b9, c9, ok9 in program_check(d)
         if not ok9 and "任意" not in b9]),
    ("庭の割り当ての矩形どうしの重なり",          lambda d, raw, ter: garden_alloc_check(d)),
    ("庭の点景(庭の中・水に落ちていないか)",      lambda d, raw, ter: niwa_element_check(d)),
    ("池(汀線・離れ・掘り込み)",              lambda d, raw, ter: pond_check(d)),
    ("築山(底の実測・段の外・離れ)",           lambda d, raw, ter: tsukiyama_check(d)),
    ("結界(取り付き・表↔奥の非連結・動線)",      lambda d, raw, ter: kekkai_check(d)),
    ("見所(入側か庭の中か・借景の視線)",        lambda d, raw, ter: mikoro_check(d)),
    ("庭の点景と竹垣・勝手動線・結界塀の交差",      lambda d, raw, ter: niwa_cross_check(d)),
    ("庭の土量の収支",                     lambda d, raw, ter:
        niwa_earth_check(d, ter) if ter else []),
    ("郭の土留めの表(結線)",                lambda d, raw, ter: walls_wired_check(d)),
    ("西の斜面と岸(窓・林・葭蓮・柵・小径)",    lambda d, raw, ter: nishi_check(d)),
    ("確度の記号(宣言と本文の食い違い)",        lambda d, raw, ter: certsig_check(d)),
    ("法肩の松の割り付け(区間ごと)",           lambda d, raw, ter: hokata_check(d)),
    ("崖下の帯の棟(帯D2・切盛・榎の離れ)",      lambda d, raw, ter: obi_check(d)),
    ("坂の規則(勾配・脚・折れ)",               lambda d, raw, ter: ramp_check(d)),
    ("勝手の線と法肩の竹垣(木戸以外で跨がない)",  lambda d, raw, ter: katte_rail_check(d)),
    ("動線・坂が樹の芯を横切らない",             lambda d, raw, ter: route_tree_check(d)),
    ("対岸から見た層(林と草地の見かけの厚み)",    lambda d, raw, ter: taigan_check(d)),
    ("データの死値(json のキーが読まれているか)", lambda d, raw, ter: data_wired_check(d)),
]


def run_checks(d, raw, ter):
    """列を回して {題: [件]} を返す。⛔ **ここを通さない検査を作らない。**"""
    out = collections.OrderedDict()
    for nm, fn in CHECK_LIST:
        try:
            out[nm] = list(fn(d, raw, ter) or [])
        except Exception as e:                 # ⛔ 例外で黙らせない — 落ちたことを件として出す
            out[nm] = ["⛔ 検査が例外で落ちた: %s: %s" % (type(e).__name__, e)]
    return out


def report_checks(chk):
    for nm, xs in chk.items():
        print("%s: %d 件" % (nm, len(xs)))      # ⛔ 0件でも必ず刷る
        for b in xs:
            print("    " + str(b))
    tot = sum(len(x) for x in chk.values())
    print("── 検査 %d 種 / 指摘 %d 件" % (len(chk), tot))


def chk_line(chk, nm):
    """図のキャプションから件数を引く。**検査は要約で走ったものを使い回す**(二度計算しない)。"""
    xs = chk.get(nm, [])
    return ("<b>0 件</b>" if not xs else "⚠ <b>%d 件</b> — %s" % (len(xs), " ／ ".join(map(str, xs))))


def walls_wired_check(d):
    """**郭の土留めの表が図に出ているか**(結線)。⛔ 0本でも表は刷る — 「無い」ことは
    設計判断なので、黙って消すと『土留めを検討したのか』が図から読めなくなる。
    ⚠ 2026-09-02 の結線関門: `walls_table()` は書かれて**一度も走っていなかった**。
    ⛔ **2026-09-03 検図5巡目 K255: それでも `return []` の恒真のままだった。**
    ⭕ いまは**表の中身を実際に作って**、①表が空でないこと ②宣言した土留めの本数と
      表の行数が合うこと ③0本のときは『無い理由』の但し書きが載っていることを見る。"""
    bad = []
    try:
        html = walls_table(d)
    except Exception as e9:
        return ["郭の土留めの表が組めない(%s: %s)" % (type(e9).__name__, e9)]
    if not html or "<table" not in html:
        bad.append("郭の土留めの表が刷られていない")
        return bad
    n9 = len(d.get("terraceWalls") or [])
    rows = html.count("<tr>") - 1                      # ヘッダ行を除く
    if n9 == 0:
        if "郭内に土留めは無い" not in html:
            bad.append("土留めが0本なのに『無い』の但し書きが表に無い")
    elif rows != n9:
        bad.append("土留めの表の行数 %d が宣言の本数 %d と合わない" % (rows, n9))
    return bad


# ================================================================ 西の斜面と溜池の岸
# ⛔ **庭ではない** — 屋敷林と堀端。灯籠・飛石・蹲踞は一つも置かない。

def yochi_metrics(d):
    """**法尻の余地**(裁定6=B で建物を置くと決まった帯)の実測 — 区画の中の面積[坪]と勾配。

    ⛔ **棟はまだ置かない**(何をどこには裁定8)。⭕ 裁定8の図がこの数を読む。"""
    N9 = d.get("nishi") or {}
    K9 = d["const"]["ken"]
    out = []
    for a9 in ((N9.get("yochi") or {}).get("areas") or []):
        ar = 0.0
        gs = []
        u9 = a9["u0"]
        while u9 <= a9["u1"] + 1e-9:
            col = []
            v9 = a9["v0"]
            while v9 <= a9["v1"] + 1e-9:
                if in_parcel(d, u9, v9):
                    y9 = _dem_at(d, u9, v9)
                    if y9 is not None:
                        ar += 0.25 * 0.25
                        col.append((v9, y9))
                v9 += 0.25
            if len(col) >= 4:
                L9 = (col[-1][0] - col[0][0]) * K9
                if L9 > 1e-6:
                    gs.append(100.0 * (col[0][1] - col[-1][1]) / L9)
            u9 += 0.25
        out.append({"name": a9["name"], "label": a9["label"], "tsubo": ar,
                    "gMin": min(gs) if gs else 0.0, "gMax": max(gs) if gs else 0.0})
    return out


def _far_note(d):
    """対岸の汀の帯(`hokata.shading.farShoreV`)の一行。⛔ 表の書式文字列に混ぜない。"""
    fv = ((((d.get("nishi") or {}).get("hokata") or {}).get("shading") or {})
          .get("farShoreV") or [])
    if not fv:
        return ""
    return ("⚠ 対岸の汀の帯は v%.0f〜%.0f(`hokata.shading.farShoreV`)で、"
            "眼はその上の実線(`parcels.json` の東縁)に置く。" % (fv[0], fv[-1]))


def taigan_table(d):
    """対岸から見た層の見かけの厚み(u ごと)。⛔ 数は図と表で二度計算しない。"""
    L = taigan_layers(d)
    if not L:
        return ""
    lim = ((d.get("nishi") or {}).get("hayashi") or {}).get("layerMinDeg", 0.5)
    rows = []
    for q9 in L[::4]:
        rows.append(["u%+.0f" % q9["u"], "%.2f°" % q9["forestDeg"],
                     "%.2f°" % q9["grassDeg"], "%.2f m" % q9["d1DropM"]])
    wq = min(L, key=lambda q9: q9["grassDeg"])
    return _tw(["u", "林の見かけの厚み", "草地の見かけの厚み", "*参考: D1の落差"], rows,
               "<b>対岸の汀の眼から測った見かけの厚み</b>(算出)。"
               "⛔ 下限は<b>草地 %.2f°</b>(`layerMinDeg`・確度U)で、"
               "いちばん痩せる所は <b>u%+.0f の %.2f°</b>。"
               "⚠ D1 の落差は<b>刷るだけ</b> — 二層に見えるかは角度で決まる。"
               % (lim, wq["u"], wq["grassDeg"]) + _far_note(d))


def taigan_svg(d):
    """**対岸から見た姿**(2026-09-03 庭方5巡目 K230)— 溜池の西岸の汀に立って東を見る。

    ⛔ 平面と断面だけでは「対岸からどう見えるか」が図に無い。⭕ 横軸 u・縦軸は標高で、
      水面 / 蓮 / 葭 / 杭 / 堤 / 草地 / 帯の屋根 / 榎 / 林冠 / 法肩の松 / 奥向の大棟 を層に重ねる。
    ⚠ 眼と対岸の線は**可視水面と同じ物差し**(`taigan_layers`)。"""
    N = d.get("nishi") or {}
    K = d["const"]["ken"]
    L = taigan_layers(d)
    if not L:
        return ""
    W, H = 900.0, 330.0
    o = _sv(W, H, "岡部筑前守上屋敷 対岸から見た姿")
    u0, u1 = -28.0, 23.0
    y0, y1 = 4.0, 40.0

    def X(u9):
        return 52.0 + (W - 66.0) * (u9 - u0) / (u1 - u0)

    def Y(y9):
        return H - 34.0 - (H - 62.0) * (y9 - y0) / (y1 - y0)
    for y9 in range(int(y0), int(y1) + 1, 6):
        o.append(LN(X(u0), Y(y9), X(u1), Y(y9), "var(--rule)", 0.6))
        o.append(T(46, Y(y9) + 4, "%d" % y9, "jo", "end"))
    ts9 = N.get("tsutsumi") or {}
    wy = ts9.get("waterY", 6.60)
    o.append(R(X(u0), Y(wy), X(u1) - X(u0), Y(y0) - Y(wy), fill="var(--ike)", op=0.55))
    o.append(T(X(u1) - 8, Y(wy) - 5, "溜池の水面 %.2f" % wy, "anS2", "end"))
    hs9 = ts9.get("hasu") or {}
    o.append(R(X(u0), Y(wy + hs9.get("leafMax", 0.9)), X(u1) - X(u0),
               abs(Y(wy + hs9.get("leafMax", 0.9)) - Y(wy)), fill="#6E8B4E", op=0.5))
    ys9 = ts9.get("yoshi") or {}
    o.append(R(X(u0), Y(wy + ys9.get("hMax", 2.0)), X(u1) - X(u0),
               abs(Y(wy + ys9.get("hMax", 2.0)) - Y(wy)), fill="#9FB98C", op=0.45))
    ku9 = N.get("kuiretsu") or {}
    if ku9:
        hd = wy + (ku9.get("topMin", 0.25) + ku9.get("topMax", 0.45)) / 2.0
        u8 = u0
        while u8 < u1:
            o.append(LN(X(u8), Y(hd), X(u8), Y(wy - 0.2), "#6B5637", 0.8))
            u8 += 0.6
    # 草地(辺5の地盤)と林の下端・林冠
    o.append('<polyline points="%s" fill="none" stroke="#CFCF9A" stroke-width="2.4"/>'
             % " ".join("%.1f,%.1f" % (X(q["u"]), Y(q["parcelY"])) for q in L))
    o.append('<polyline points="%s" fill="none" stroke="#7E9A6B" stroke-width="2.4"/>'
             % " ".join("%.1f,%.1f" % (X(q["u"]), Y(q["edgeY"])) for q in L))
    hy9 = N.get("hayashi") or {}
    can = [(q["u"], (_dem_at(d, q["u"], 111.0) or 0) + (hy9.get("takagiHMax") or 12.0))
           for q in L]
    o.append('<polygon points="%s" fill="#7E9A6B" opacity="0.45"/>'
             % (" ".join("%.1f,%.1f" % (X(a9), Y(b9)) for a9, b9 in can)
                + " " + " ".join("%.1f,%.1f" % (X(q["u"]), Y(q["edgeY"]))
                                 for q in reversed(L))))
    o.append(T(X(-22), Y(30), "林冠(高木 %dm)" % (hy9.get("takagiHMax") or 12), "anS2"))
    # 帯の屋根
    rf9 = (d.get("roofs") or {}).get("ObiNagaya") or {}
    for o9 in obi_metrics(d):
        if not o9["roofed"]:
            continue
        yb = (o9["y"] or 0)
        o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#4A4A52" opacity="0.9"/>'
                 % (X(o9["u0"]), Y(yb + rf9.get("eaveH", 2.7)),
                    X((o9["u0"] + o9["u1"]) / 2), Y(yb + rf9.get("ridgeH", 4.3)),
                    X(o9["u1"]), Y(yb + rf9.get("eaveH", 2.7))))
        o.append(R(X(o9["u0"]), Y(yb + rf9.get("eaveH", 2.7)), X(o9["u1"]) - X(o9["u0"]),
                   abs(Y(yb + rf9.get("eaveH", 2.7)) - Y(yb)), fill="#8A8A80", op=0.75))
    # 榎・法肩の松
    for e9 in ((N.get("hojiri") or {}).get("enoki") or []):
        gy = _dem_at(d, e9["u"], e9["v"]) or 0
        o.append(_tree(_TP(X, Y), e9["u"], gy + e9.get("hMax", 12) / 2.0, 6.0, "#7A5C3A"))
    hk9 = N.get("hokata") or {}
    for _i9, u8, v8 in hokata_pts(d):
        gy = _dem_at(d, u8, v8) or 0
        o.append(LN(X(u8), Y(gy), X(u8), Y(gy + hk9.get("hMax", 12)), "#2F5A2F", 1.6))
    # 奥向の大棟(候補の最悪)
    rc = ((hk9.get("shading") or {}).get("ridgeCandidates") or [])
    if rc:
        mn = next((m9 for m9 in d["munes"] if m9["name"] == "Okumuki"), None)
        if mn:
            o.append(LN(X(mn["u0"]), Y(max(rc)), X(mn["u1"]), Y(max(rc)),
                        "var(--shu)", 2.0, dash="6 4"))
            o.append(T(X((mn["u0"] + mn["u1"]) / 2), Y(max(rc)) - 5,
                       "奥向棟の大棟(候補の最悪 %.2f)" % max(rc), "jo", "middle"))
    o.append(T(52, H - 12, "u[間](左=南 / 右=北)／ 縦は標高[m]。"
                           "⚠ **対岸の汀の眼(高さ %.2f)から見た層**で、見かけの厚みは下の表が刷る"
               % (((hk9.get("shading") or {}).get("farEyeY")) or 10.55), "anS2"))
    o.append("</svg>")
    return "\n".join(o)


class _TP(object):
    """`_tree` に渡す簡易プロジェクタ(対岸の見え掛かり用)。"""

    def __init__(self, fx, fy):
        self.X = fx
        self.Y = fy


def data_wired_check(d):
    """**json に書いたキーが生成器で一度も読まれていないか**(2026-09-03 庭方5巡目)。

    ⛔ `wiring_gate.py` は**関数**の結線しか見ない — データのキーは見ない。
    ⭕ ここでは `nishi` / `obi` / `ramps` の「`_` で始まらないキー」が、
      生成器のソースに**文字列として一度以上現れる**ことを見る。
    ⚠ 粗い網(同名の別キーを取り違える)だが、**死値をゼロ件と言い張るよりは良い**。"""
    try:
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "build_okabe_sashizu.py"), encoding="utf-8").read()
    except Exception:
        return []
    skip = {"label", "name", "cert", "certSig", "u", "v", "u0", "u1", "v0", "v1",
            "kind", "n", "h", "y", "pts", "species", "hMin", "hMax", "_"}
    bad = []
    seen = set()

    def walk(o, path):
        if isinstance(o, dict):
            for k9, v9 in o.items():
                if k9.startswith("_"):
                    continue
                if k9 not in skip and k9 not in seen and ('"%s"' % k9) not in src:
                    seen.add(k9)
                    bad.append("`%s.%s` が生成器のどこからも読まれていない(死値)" % (path, k9))
                walk(v9, path + "." + k9)
        elif isinstance(o, list):
            for i9, v9 in enumerate(o[:6]):
                walk(v9, path + "[%d]" % i9)
    for key in ("nishi", "ramps"):
        walk(d.get(key), key)
    return bad


def taigan_layers(d):
    """**対岸の汀の眼から見た層の見かけの厚み**【2026-09-03 庭方6巡目 K263 の式】。

    ⭐ 眼 E(u) = (u, farV(u), `farEyeY`)。`farV` は対岸の区画(`parcels.json`)の東縁の斜線。
      ⛔ 眼の v を固定しない・⛔ 1断面で代表しない(庭方の 0.89° はその2つが原因だった)。
    ⭐ d = (farV − v) × 1間、θ = atan2(y − 眼高, d)。
      ・**林** = θ(法肩 `hokata.v1`, 地盤 + `canopyH`) − θ(林の下端 v(u), 地盤 + `underH`)
      ・**草地** = θ(vG, **地盤**) − θ(vY, 葭の上端)
        vG = max(林の下端 v(u), その u に掛かる棟の**最も汀寄りの v**)
        ⛔ **屋根の高さは使わない**(これが恒真を避ける鍵 — 屋根を上げても厚くならない)
        vY = 辺5の v(u) + (辺5の地盤 − 水面) × `batter` ÷ 1間(葭の上端)
    ⚠ `canopyH` / `underH` / `farShoreY` は**確度U**。"""
    N9 = d.get("nishi") or {}
    K9 = d["const"]["ken"]
    seg = far_shore(d)
    hk = N9.get("hokata") or {}
    sh9 = hk.get("shading") or {}
    hy = N9.get("hayashi") or {}
    ts9 = N9.get("tsutsumi") or {}
    eg = [(a9, b9) for a9, b9 in (hy.get("edge") or [])]
    if not (seg and eg):
        return []
    # ⭕ 眼高 = 対岸の汀の地盤 + 立位(基準身長から。⛔ 別の人の値を持たない)
    eyeY = (sh9.get("farShoreY") if sh9.get("farShoreY") is not None else 9.00) \
        + eye_above(d, "stand")
    canopy = hy.get("canopyH", 12.0)
    under = hy.get("underH", 3.0)
    vTop = hk.get("v1", 111.0)
    wy = ts9.get("waterY", 6.60)
    bat = ts9.get("batter", 2.2)

    def edge_v(u9):
        if u9 <= eg[0][0]:
            return eg[0][1]
        for a9, b9 in zip(eg, eg[1:]):
            if u9 <= b9[0]:
                t9 = (u9 - a9[0]) / max(b9[0] - a9[0], 1e-9)
                return a9[1] + (b9[1] - a9[1]) * t9
        return eg[-1][1]

    def far_v(u9):
        (a9, b9) = seg
        den = (b9[0] - a9[0]) or 1e-9          # ⛔ 符号を潰さない
        return a9[1] + (b9[1] - a9[1]) * ((u9 - a9[0]) / den)
    P9 = d["polygon"]
    e5 = (N9.get("saku") or {}).get("edge", 5)
    gr = RGrid(d)
    pa, pb = gr.L(*P9[e5]), gr.L(*P9[(e5 + 1) % len(P9)])

    def parcel_v(u9):
        den = (pb[0] - pa[0]) or 1e-9
        return pa[1] + (pb[1] - pa[1]) * ((u9 - pa[0]) / den)

    def th(u9, v9, y9):
        return math.degrees(math.atan2(y9 - eyeY, max((far_v(u9) - v9) * K9, 1e-9)))
    out = []
    u9 = max(eg[0][0], -27.0)
    while u9 <= min(eg[-1][0], 22.0) + 1e-9:
        vE = edge_v(u9)
        yE = _dem_at(d, u9, vE)
        yT = _dem_at(d, u9, vTop)
        vP = parcel_v(u9)
        yP = _dem_at(d, u9, vP - 2.0)
        if None in (yE, yT, yP):
            u9 += 1.0
            continue
        aF = th(u9, vTop, yT + canopy) - th(u9, vE, yE + under)
        # 草地の上端 — 林の下端 か、その u に掛かる棟の**最も汀寄りの v**(⛔ 屋根の高さは使わない)
        vG = vE
        for o8 in obi_metrics(d):
            if o8["roofed"] and o8["u0"] - 0.5 <= u9 <= o8["u1"] + 0.5:
                vG = max(vG, o8["v1"])
        yG = _dem_at(d, u9, vG) or yE
        vY = vP + (yP - wy) * bat / K9          # 葭の上端(堤の法尻)
        aG = th(u9, vG, yG) - th(u9, vY, wy + (ts9.get("yoshi") or {}).get("depthMin", 0.0) + 0.30)
        out.append({"u": u9, "forestDeg": aF, "grassDeg": aG,
                    "d1DropM": yE - yP, "topV": vG, "topY": yG,
                    "edgeV": vE, "edgeY": yE, "parcelV": vP, "parcelY": yP,
                    "yoshiV": vY, "eyeY": eyeY})
        u9 += 1.0
    return out


def taigan_check(d):
    """**対岸から二層に見えるか。**⭕ 合否を開けた【2026-09-03 庭方6巡目 K263 で式が決まった】。

    ⛔ 一度目の式(屋根の角 − 辺5の角)は**恒真**、二度目(林の下端 − 手前の遮り)は素で18件鳴った。
    ⭕ 庭方の式は**屋根の高さを使わず**、棟の**汀寄りの縁の地盤**で草地の上端を切る。"""
    bad = []
    lim = ((d.get("nishi") or {}).get("hayashi") or {}).get("layerMinDeg", 0.5)
    for q9 in taigan_layers(d):
        if q9["grassDeg"] < lim - 1e-9:
            bad.append("対岸から見た**草地の層**が u%+.0f で %.2f° しかない — %.2f° 以上要る"
                       "(⚠ 棟が汀へ寄ると草地が食われる)" % (q9["u"], q9["grassDeg"], lim))
        if q9["forestDeg"] < lim - 1e-9:
            bad.append("対岸から見た**林の層**が u%+.0f で %.2f° しかない — %.2f° 以上要る"
                       % (q9["u"], q9["forestDeg"], lim))
    return bad


def far_shore(d):
    """**対岸の汀**(溜池の西岸)の線を `parcels.json` から引く。⛔ 座標を当図に書き写さない。

    ⭐ 2026-09-03 庭方5巡目 K202: 可視水面の定義を庭方に揃えるため、対岸を
      **一定の v ではなく実際の斜線**で取る(`nishi.mado.farShoreParcel` の区画の東縁)。
    ⭕ 東縁の選び方: **区画の重心より v が小さい辺のうち最も長いもの**(=当邸に面する長辺)。"""
    md = ((d.get("nishi") or {}).get("mado") or {})
    pid = md.get("farShoreParcel")
    if not pid:
        return None
    try:
        pj = json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))
    except Exception:
        return None
    rec = next((q for q in pj.get("parcels", []) if q.get("id") == pid), None)
    if not rec or not rec.get("pts"):
        return None
    gr = RGrid(d)
    uv = [gr.L(x, z) for x, z in rec["pts"]]
    cv = sum(q[1] for q in uv) / len(uv)
    best = None
    for i9 in range(len(uv)):
        a9, b9 = uv[i9], uv[(i9 + 1) % len(uv)]
        if (a9[1] + b9[1]) / 2.0 >= cv:
            continue
        L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
        if best is None or L9 > best[0]:
            best = (L9, a9, b9)
    return None if best is None else (best[1], best[2])


def mizu_visible(d):
    """**見える水面**[m²]。⭐ 定義は庭方に揃えた(2026-09-03 K202):

    ① 対岸は `parcels.json` の区画の東縁の**斜線**(⛔ 一定の v ではない)
    ② 床几の眼から**方位ごとに 0.25° 刻みで掃く**(⛔ 眼を頂点にした一つの円錐で近似しない)
    ③ その方位で視線を切る物(区画内の地盤と、区画界に立つ**汀の柵の天端**)を拾い、
       そこを掠める線が水面に達する距離を**見えはじめ**とする
    ④ 見えはじめ 〜 対岸の交点 までを**極座標で積分**する
    ⚠ 掃く範囲は**見透しの窓(扇)の中だけ** — 扇の外は林と法肩の松が閉じている。
      当図の『開き角』は**扇の両縁を眼から見込む角**である(⛔ 遮蔽を掃いて出した角ではない)。"""
    N9 = d.get("nishi") or {}
    md = N9.get("mado") or {}
    ey = md.get("eye") or {}
    fan = md.get("fan") or []
    seg = far_shore(d)
    sk9 = N9.get("saku") or {}
    ts9 = N9.get("tsutsumi") or {}
    if not (fan and seg and ey.get("eyeY") is not None):
        return None
    K9 = d["const"]["ken"]
    wy = ts9.get("waterY", 6.60)
    eu, ev = ey["u"], ey["v"]
    th0 = math.atan2(fan[-1][1] - eu, fan[-1][0] - ev)
    th1 = math.atan2(fan[-1][2] - eu, fan[-1][0] - ev)
    step = math.radians(md.get("sweepDeg", 0.25))
    (a9, b9), area, rs = seg, 0.0, []
    th = min(th0, th1)
    while th <= max(th0, th1) + 1e-12:
        du, dv = math.sin(th), math.cos(th)
        # 対岸の斜線との交点(パラメタ)
        den = du * (b9[1] - a9[1]) - dv * (b9[0] - a9[0])
        if abs(den) < 1e-12:
            th += step
            continue
        s9 = ((a9[0] - eu) * (b9[1] - a9[1]) - (a9[1] - ev) * (b9[0] - a9[0])) / den
        if s9 <= 0:
            th += step
            continue
        rFar = s9 * K9
        # 視線を切る物 — 区画の中の地盤 + 区画界の柵の天端
        slope, r9, last = None, 1.0, None
        while r9 < s9:
            uu, vv = eu + du * r9, ev + dv * r9
            if in_parcel(d, uu, vv):
                yy = _dem_at(d, uu, vv)
                if yy is not None:
                    m9 = (yy - ey["eyeY"]) / (r9 * K9)
                    if slope is None or m9 > slope:
                        slope = m9
                    last = (r9, yy)
            r9 += 0.5
        if last and sk9.get("h"):
            m9 = (last[1] + sk9["h"] - ey["eyeY"]) / (last[0] * K9)
            if slope is None or m9 > slope:
                slope = m9
        if slope is not None and slope < 0:
            rSee = (wy - ey["eyeY"]) / slope
            if rFar > rSee:
                area += 0.5 * (rFar ** 2 - rSee ** 2) * step
                rs.append(rSee)
        th += step
    if not rs:
        return None
    return {"m2": area, "seeFrom": [min(rs), max(rs)],
            "angDeg": math.degrees(abs(th1 - th0)),
            "seg": seg}


def saka_forest(d):
    """勝手の坂が**林を伐る帯**の実測 — 林の中の路長・伐る面積・林に対する割合・伐る本数。

    ⛔ 手で書かない(2026-09-03 庭方5巡目 K205)。⭕ 林の下端の線より上(v が小さい側)を林とする。"""
    K9 = d["const"]["ken"]
    N9 = d.get("nishi") or {}
    hy = N9.get("hayashi") or {}
    eg = [(a9, b9) for a9, b9 in (hy.get("edge") or [])]
    rp = next((q for q in d.get("ramps", []) if q.get("cutW")), None)
    if not (eg and rp):
        return None

    def edge_v(u9):
        if u9 <= eg[0][0]:
            return eg[0][1]
        for a9, b9 in zip(eg, eg[1:]):
            if u9 <= b9[0]:
                t9 = (u9 - a9[0]) / max(b9[0] - a9[0], 1e-9)
                return a9[1] + (b9[1] - a9[1]) * t9
        return eg[-1][1]
    pts = [(a9, b9) for a9, b9 in rp["pts"]]
    inL = 0.0
    for a9, b9 in zip(pts, pts[1:]):
        n9 = max(1, int(math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K9 / 0.5))
        for k9 in range(n9):
            f9 = (k9 + 0.5) / n9
            u8 = a9[0] + (b9[0] - a9[0]) * f9
            v8 = a9[1] + (b9[1] - a9[1]) * f9
            if v8 <= edge_v(u8):                       # 林の下端より上=林の中
                inL += math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K9 / n9
    cut = inL * rp["cutW"]
    # 林の面積(下端の線から法肩まで)と本数の密度から、伐る本数を出す
    us = [q[0] for q in eg]
    ar = 0.0
    u8 = min(us)
    while u8 < max(us):
        ar += max(0.0, edge_v(u8) - hy.get("vTop", 111.0)) * 0.5
        u8 += 0.5
    ar *= K9 * K9
    tg = sum(q["n"] for q in (hy.get("takagi") or []))
    ch = sum(q["n"] for q in (hy.get("chuboku") or []))
    pct = (100.0 * cut / ar) if ar > 0 else 0.0
    return {"inForestM": inL, "cutM2": cut, "forestM2": ar, "pct": pct,
            "takagi": tg * cut / ar if ar > 0 else 0.0,
            "chuboku": ch * cut / ar if ar > 0 else 0.0}


def obi_east_clear(d):
    """崖下の棟の**東(山側)の余地** — 林の下端の線から棟の東面までの距離[m]。"""
    K9 = d["const"]["ken"]
    N9 = d.get("nishi") or {}
    eg = [(a9, b9) for a9, b9 in ((N9.get("hayashi") or {}).get("edge") or [])]
    if not eg:
        return []

    def edge_v(u9):
        if u9 <= eg[0][0]:
            return eg[0][1]
        for a9, b9 in zip(eg, eg[1:]):
            if u9 <= b9[0]:
                t9 = (u9 - a9[0]) / max(b9[0] - a9[0], 1e-9)
                return a9[1] + (b9[1] - a9[1]) * t9
        return eg[-1][1]
    out = []
    for o in obi_metrics(d):
        if not o["roofed"]:
            continue
        worst = None
        u8 = o["u0"]
        while u8 <= o["u1"] + 1e-9:
            gap = (o["v0"] - edge_v(u8)) * K9        # 棟の東面(v が小さい側)まで
            if worst is None or gap < worst[0]:
                worst = (gap, u8)
            u8 += 0.25
        out.append({"name": o["name"], "gapM": worst[0], "atU": worst[1]})
    return out


def fan_at_v(fan, v9):
    """扇の左右の縁を v で引く(⛔ 3点の外へは**最後の勾配で外挿**する)。"""
    if v9 <= fan[0][0]:
        a9, b9 = fan[0], fan[1]
    elif v9 >= fan[-1][0]:
        a9, b9 = fan[-2], fan[-1]
    else:
        for a9, b9 in zip(fan, fan[1:]):
            if v9 <= b9[0]:
                break
    t9 = (v9 - a9[0]) / max(b9[0] - a9[0], 1e-9)
    return (a9[1] + (b9[1] - a9[1]) * t9, a9[2] + (b9[2] - a9[2]) * t9)


def rail_v_at(d, u9):
    """**法肩の竹垣が立つ v** を u で引く(其十八 `auto_rails` の線が実体)。

    ⚠ 2026-09-03 庭方 K210(a): 「柵は眼の 1.31m 先」は**斜めの距離**で、
      柵の点を u ごと拾っていたためだった。⭕ 実体は**同じ u での v の差**(0.55m)で、
      柵の v は其十八の線が持つ。⛔ 眼の v と柵の v を混ぜない。"""
    best = None
    for rl in auto_rails(d):
        for (ru, rv) in rl["pts"]:
            dd = abs(ru - u9)
            if best is None or dd < best[0]:
                best = (dd, rv)
    return None if best is None else best[1]


def ramp_metrics(d, rp):
    """坂の実測 — 総延長・落差・最急勾配・脚の最短・折れの最大。

    ⛔ 2026-09-03 まで `gradMax`/`turnMax`/`legMin` は**どこからも読まれない死値**だった
      (`railU0` と同じ型)。⭕ ここで測り、`ramp_check` が宣言と突き合わせる。"""
    K = d["const"]["ken"]
    pts = [(a9, b9) for a9, b9 in (rp.get("pts") or [])]
    if len(pts) < 2:
        return None
    # ⛔ **坂は地盤なりではない** — 自分の路盤(`prof` の第3欄)を持つ。
    #   ⚠ 地盤で測ると、切土で通す区間が「31.7%の坂」に見える(2026-09-03 の実例)。
    pr9 = rp.get("prof")
    if pr9 and len(pr9) == len(pts):
        ys = [q[2] for q in pr9]
    else:
        ys = [_dem_at(d, q[0], q[1]) for q in pts]
    if any(q is None for q in ys):
        return None
    ls, gs = [], []
    for (a9, b9), (ya, yb) in zip(zip(pts, pts[1:]), zip(ys, ys[1:])):
        L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K
        ls.append(L9)
        gs.append(100.0 * abs(yb - ya) / max(L9, 1e-9))
    ts = []
    for i9 in range(len(pts) - 2):
        v1 = (pts[i9 + 1][0] - pts[i9][0], pts[i9 + 1][1] - pts[i9][1])
        v2 = (pts[i9 + 2][0] - pts[i9 + 1][0], pts[i9 + 2][1] - pts[i9 + 1][1])
        n1, n2 = math.hypot(*v1), math.hypot(*v2)
        if n1 < 1e-9 or n2 < 1e-9:
            continue
        cs = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
        ts.append(math.degrees(math.acos(cs)))
    # ⭕ **`stepWinKen` 間の窓の局所もここで測る**(2026-09-03 庭方5巡目 K233) —
    #   検査の中で後から足していたので、表は常に 0.00% を刷っていた(死値と同じ)。
    loc = 0.0
    win = rp.get("stepWinKen")
    if win:
        for a8, b8 in zip(pts, pts[1:]):
            Lk = math.hypot(b8[0] - a8[0], b8[1] - a8[1])
            n8 = max(1, int(math.ceil(Lk / win)))
            for k8 in range(n8):
                p8 = (a8[0] + (b8[0] - a8[0]) * k8 / n8, a8[1] + (b8[1] - a8[1]) * k8 / n8)
                q8 = (a8[0] + (b8[0] - a8[0]) * (k8 + 1) / n8,
                      a8[1] + (b8[1] - a8[1]) * (k8 + 1) / n8)
                ya, yb = _dem_at(d, p8[0], p8[1]), _dem_at(d, q8[0], q8[1])
                L8 = math.hypot(q8[0] - p8[0], q8[1] - p8[1]) * K
                if ya is None or yb is None or L8 < 1e-6:
                    continue
                loc = max(loc, 100.0 * abs(yb - ya) / L8)
    return {"len": round(sum(ls), 1), "rise": round(max(ys) - min(ys), 2),
            "grad": round(max(gs), 1), "gradAt": gs.index(max(gs)),
            "leg": round(min(ls), 1), "turn": round(max(ts), 1) if ts else 0.0,
            "local": round(loc, 2)}


def ramp_check(d):
    """**坂の規則**(勾配・脚の長さ・折れ角)を実測と突き合わせる。

    ⚠ 2026-09-03 ユーザー裁定8=A の書き起こしで分かったこと —
      **坂の規則は宣言されていたが、検査が一つも無かった**(`gradMax`/`turnMax`/`legMin` が死値)。
    ⛔ 折れ角の規則は**折り返しを許さない** — 折り返しは 140〜150° の折れになる。"""
    bad = []
    for rp in d.get("ramps", []):
        m9 = ramp_metrics(d, rp)
        if not m9:
            bad.append("坂『%s』の折れ点か地盤が測れない" % rp.get("name"))
            continue
        nm = rp.get("label") or rp.get("name")
        if rp.get("gradMax") is not None and m9["grad"] > rp["gradMax"] + 1e-6:
            bad.append("坂『%s』の最急 %.1f%% が上限 %.1f%% を超える(%d脚目)"
                       % (nm, m9["grad"], rp["gradMax"], m9["gradAt"] + 1))
        if rp.get("legMin") is not None and m9["leg"] < rp["legMin"] - 1e-6:
            bad.append("坂『%s』の脚の最短 %.1fm が下限 %.1fm を割る" % (nm, m9["leg"], rp["legMin"]))
        if rp.get("outsideMado"):
            # ⛔ **見透しの窓(扇)の中を坂が通らない**(2026-09-03 ユーザー裁定8=A)。
            pts = [(a9, b9) for a9, b9 in (rp.get("pts") or [])]
            hit = None
            for a9, b9 in zip(pts, pts[1:]):
                n8 = max(1, int(math.hypot(b9[0] - a9[0], b9[1] - a9[1]) / 0.25))
                for k8 in range(n8 + 1):
                    f8 = k8 / float(n8)
                    q8 = (a9[0] + (b9[0] - a9[0]) * f8, a9[1] + (b9[1] - a9[1]) * f8)
                    if in_mado(d, q8[0], q8[1]):
                        hit = q8
                        break
                if hit:
                    break
            if hit:
                ax8 = axis_at(d, hit[1]) or (0.0, 0.0)
                bad.append("坂『%s』が見透しの窓の中を通る — (%.1f, %.1f)。"
                           "その v の窓は u%.2f〜%.2f" % (nm, hit[0], hit[1], ax8[0], ax8[1]))
        if rp.get("turnMax") is not None and m9["turn"] > rp["turnMax"] + 1e-6:
            bad.append("坂『%s』の折れの最大 %.0f° が上限 %.0f° を超える"
                       "(⚠ 折り返しは 140〜150° になるので、この規則では折り返せない)"
                       % (nm, m9["turn"], rp["turnMax"]))
    return bad


def route_tree_check(d):
    """**動線が樹の芯を横切らないか**(2026-09-03 検図5巡目 K245)。

    ⛔ 線が松や榎の**幹の位置**を通ると、実装は木を避けて道を振るか木を消す。
    ⭕ 見るのは法肩の松・榎・窓の松の芯から `treeClearM` 未満を通る動線と坂。"""
    K9 = d["const"]["ken"]
    N9 = d.get("nishi") or {}
    lim = (N9.get("hokata") or {}).get("treeClearM", 1.0)
    trees = [("法肩の松", u9, v9) for _i, u9, v9 in hokata_pts(d)]
    trees += [("榎 " + e9["name"], e9["u"], e9["v"])
              for e9 in ((N9.get("hojiri") or {}).get("enoki") or [])]
    trees += [("窓の松 " + m9["name"], m9["u"], m9["v"])
              for m9 in ((N9.get("mado") or {}).get("matsu") or [])]
    bad = []
    lines = [(r9.get("label") or r9["name"], r9["pts"]) for r9 in d.get("routes", [])]
    lines += [(rp9.get("label") or rp9["name"], rp9["pts"]) for rp9 in d.get("ramps", [])]
    for nm9, pts in lines:
        for tn, tu, tv in trees:
            best = None
            for a9, b9 in zip(pts, pts[1:]):
                dx, dy = b9[0] - a9[0], b9[1] - a9[1]
                L2 = dx * dx + dy * dy or 1e-9
                s9 = max(0.0, min(1.0, ((tu - a9[0]) * dx + (tv - a9[1]) * dy) / L2))
                dd = math.hypot(tu - (a9[0] + dx * s9), tv - (a9[1] + dy * s9)) * K9
                if best is None or dd < best:
                    best = dd
            if best is not None and best < lim - 1e-6:
                bad.append("%s が%sの芯から %.2fm を通る — %.1fm 以上あけること"
                           % (nm9, tn, best, lim))
                break
    return bad


def katte_rail_check(d):
    """**勝手の線が法肩の竹垣を「木戸」以外で跨がないか。**

    ⚠ 2026-09-03 考証5巡目 K216: 勝手の道の末尾が**垣の外**を 20m 走っていた。
    ⭕ 見るのは「竹垣の折れ線と交わる所が、宣言した木戸(`nishi.hokata.gateU` ± 幅)か」。
    ⛔ 交わってよいのは木戸だけ — 垣を跨いだ所が木戸でなければ鳴らす。"""
    bad = []
    gz = [(g9, (d.get("nishi") or {}).get("hokata", {}).get("gateClearKen", 1.0))
          for g9 in ((d.get("nishi") or {}).get("hokata", {}).get("gateU") or [])]
    rails = [rl["pts"] for rl in auto_rails(d)]
    for r9 in d.get("routes", []):
        if "勝手" not in (r9.get("label") or ""):
            continue
        for a9, b9 in zip(r9["pts"], r9["pts"][1:]):
            for pts in rails:
                for c9, e9 in zip(pts, pts[1:]):
                    if not _seg_x(tuple(a9), tuple(b9), tuple(c9), tuple(e9)):
                        continue
                    # 交点の u(近似=線分の中点)
                    uu = (max(min(a9[0], b9[0]), min(c9[0], e9[0]))
                          + min(max(a9[0], b9[0]), max(c9[0], e9[0]))) / 2.0
                    if any(abs(uu - g9) <= w9 + 0.5 for g9, w9 in gz):
                        continue
                    bad.append("勝手の線が法肩の竹垣を u%.1f で跨ぐ — 木戸(%s)以外で跨がない"
                               % (uu, "・".join("u%.1f" % g9 for g9, _w in gz) or "無し"))
    return bad


def obi_items(d):
    """崖下の帯に置いた物(棟・小物・井戸)を (名, u0,v0,u1,v1, 面y or None) で返す。"""
    out = []
    for s9 in d.get("service", []):
        if s9.get("obi"):
            out.append((s9.get("label") or s9["name"], s9["u0"], s9["v0"], s9["u1"], s9["v1"],
                        s9.get("y"), bool(s9.get("roof"))))
    for w9 in d.get("wells", []):
        if w9.get("obi"):
            # ⚠ 井戸は**屋根を持たない**ので、榎の離れ(軒までの規則)の対象外。
            out.append((w9.get("label") or w9["name"], w9["u"] - 0.5, w9["v"] - 0.5,
                        w9["u"] + 0.5, w9["v"] + 0.5, w9.get("y"), False))
    return out


def obi_metrics(d):
    """崖下の帯の棟ごとの実測 — 面積・足跡の実地盤・|地盤 − 面| の最大・榎までの離れ。"""
    K = d["const"]["ken"]
    N9 = d.get("nishi") or {}
    obi = N9.get("obi") or {}
    noki = obi.get("nokiOut", 0.0) / K                 # 軒の出[間]
    enoki = (N9.get("hojiri") or {}).get("enoki") or []
    out = []
    for nm, u0, v0, u1, v1, y9, isB in obi_items(d):
        zs = []
        u8 = u0
        while u8 <= u1 + 1e-9:
            v8 = v0
            while v8 <= v1 + 1e-9:
                q8 = _dem_at(d, u8, v8)
                if q8 is not None:
                    zs.append(q8)
                v8 += 0.25
            u8 += 0.25
        pad = (sum(zs) / len(zs)) if zs else None
        dz = max(abs(q8 - (y9 if y9 is not None else pad)) for q8 in zs) if zs else None
        gaps = []
        for e9 in enoki:
            du = max(u0 - noki - e9["u"], e9["u"] - (u1 + noki), 0.0)
            dv = max(v0 - noki - e9["v"], e9["v"] - (v1 + noki), 0.0)
            gaps.append((e9["name"], math.hypot(du, dv) * K))
        out.append({"name": nm, "roofed": isB, "u0": u0, "v0": v0, "u1": u1, "v1": v1, "y": y9,
                    "areaM2": (u1 - u0) * (v1 - v0) * K * K, "pad": pad, "dz": dz,
                    "gaps": sorted(gaps, key=lambda q: q[1])})
    return out


def obi_kishi(d):
    """崖下の棟ごとの (名, 辺5までの水平距離[m], 水面からの比高[m])。⛔ 図と検査で二度計算しない。"""
    K9 = d["const"]["ken"]
    N9 = d.get("nishi") or {}
    P9 = d["polygon"]
    e9 = (N9.get("saku") or {}).get("edge", 5)
    gr9 = RGrid(d)
    pa9, pb9 = gr9.L(*P9[e9]), gr9.L(*P9[(e9 + 1) % len(P9)])
    wy9 = (N9.get("tsutsumi") or {}).get("waterY", 6.60)
    out = []
    for o9 in obi_metrics(d):
        den = (pb9[0] - pa9[0]) or 1e-9
        dd = min((pa9[1] + (pb9[1] - pa9[1]) * ((u8 - pa9[0]) / den) - o9["v1"]) * K9
                 for u8 in (o9["u0"], (o9["u0"] + o9["u1"]) / 2.0, o9["u1"]))
        out.append((o9["name"], dd,
                    (o9["y"] if o9["y"] is not None else (o9["pad"] or 0)) - wy9))
    return out


def obi_check(d):
    """**崖下の帯の棟の不変条件**(2026-09-03 ユーザー裁定8=A)。

    ① 帯**D2(法尻の平坦帯)**にだけ載る — 崖面(D1)にも堤(E)にも出さない
    ② 棟ごとに面を持ち、|足跡の実地盤 − 面| ≦ `padTolM`(⛔ 帯全体を均さない)
    ③ 榎の幹から**軒**まで `enokiClearM` 以上(⚠ 屋根を持つ物だけ。井戸は対象外)
    ④ 水側(西)は盲面・開口は東(宣言があること)"""
    bad = []
    N9 = d.get("nishi") or {}
    obi = N9.get("obi") or {}
    if not obi.get("munes"):
        return bad
    bands = {b9["name"][:2]: b9 for b9 in (d.get("slopeBands") or [])}
    d2 = next((b9 for b9 in (d.get("slopeBands") or []) if b9["name"].startswith("D2")), None)
    tol = obi.get("padTolM", 0.5)
    clr = obi.get("enokiClearM", 6.0)
    for o in obi_metrics(d):
        if o["pad"] is None:
            bad.append("帯の『%s』の足跡の地盤が測れない(復元地盤の外)" % o["name"])
            continue
        if d2 and d2.get("y0") is not None:
            if not (d2["y1"] - 0.2 <= o["pad"] <= d2["y0"] + 0.2):
                bad.append("帯の『%s』の足跡の地盤 %.2f が帯D2(%.2f〜%.2f)の外 — "
                           "崖面や堤に載せない" % (o["name"], o["pad"], d2["y1"], d2["y0"]))
        if o["y"] is not None and o["dz"] is not None and o["dz"] > tol + 1e-6:
            bad.append("帯の『%s』の切盛が %.2fm(面 %.2f)— 許容 %.1fm を超える"
                       "(⛔ 帯全体を均さない。棟ごとに面を持つ)" % (o["name"], o["dz"], o["y"], tol))
        if o["roofed"] and o["gaps"] and o["gaps"][0][1] < clr - 1e-6:
            bad.append("帯の『%s』の軒が榎『%s』の幹から %.1fm — %.1fm 以上あけること"
                       % (o["name"], o["gaps"][0][0], o["gaps"][0][1], clr))
    ec = obi.get("eastClearM")
    if ec:
        for q9 in obi_east_clear(d):
            if q9["gapM"] < ec - 0.005:
                bad.append("帯の『%s』の東(山側)の余地が %.2fm(u%.1f)— %.1fm あけること"
                           "(犬走り+雨落ち+掃く通り+林縁の張り出し)"
                           % (q9["name"], q9["gapM"], q9["atU"], ec))
    su9 = ((d.get("nishi") or {}).get("hojiri") or {}).get("susuki") or {}
    if su9.get("clearKen"):
        for o9 in obi_metrics(d):
            if not o9["roofed"]:
                continue
            if su9.get("v0") is not None and su9["v0"] < o9["v1"] + su9["clearKen"]:
                bad.append("\u6cd5\u5c3b\u306e\u30b9\u30b9\u30ad(v%.0f\u301c)\u304c\u68df\u300e%s\u300f(\u301cv%.1f)\u304b\u3089 %.1f\u9593 \u4ee5\u5185 \u2014 %.1f\u9593 \u4ee5\u4e0a\u3042\u3051\u308b"
                           % (su9["v0"], o9["name"], o9["v1"],
                              su9["v0"] - o9["v1"], su9["clearKen"]))
                break
    for nm9 in (obi.get("komono") or []):
        if not any(nm9 == s9.get("name") for s9 in d.get("service", []) + d.get("wells", [])):
            bad.append("\u5e2f\u306e\u5c0f\u7269\u300e%s\u300f\u304c\u5b9f\u4f53\u306b\u7121\u3044" % nm9)
    # ⛔ **汀へ寄せない**(2026-09-03 ユーザー裁定9=A / 庭方 K264)。
    #   ⚠ 角度の検査(対岸から見た層)は**棟を汀へ寄せても痩せない**式なので、
    #     それだけでは「寄せるな」を縛れない。⭕ **m 建て**で二本立てる:
    #     A 棟の**下手の面**から、その u の**辺5**までの水平距離 ≧ `kishiClearM`
    #     B 棟の**足元の地盤** − 水面 ≧ `mizuAboveM`
    #   ⛔ どちらも**確度U**(A は堤の法面 10.0m の2倍・B は辺5の比高)。
    K8 = d["const"]["ken"]
    P8 = d["polygon"]
    e8 = ((d.get("nishi") or {}).get("saku") or {}).get("edge", 5)
    gr8 = RGrid(d)
    pa8, pb8 = gr8.L(*P8[e8]), gr8.L(*P8[(e8 + 1) % len(P8)])

    def _par_v(u8):
        den = (pb8[0] - pa8[0]) or 1e-9
        return pa8[1] + (pb8[1] - pa8[1]) * ((u8 - pa8[0]) / den)
    kc = obi.get("kishiClearM")
    mz = obi.get("mizuAboveM")
    wy8 = ((d.get("nishi") or {}).get("tsutsumi") or {}).get("waterY", 6.60)
    for o9 in obi_metrics(d):
        if kc is not None:
            worst = None
            for u8 in (o9["u0"], (o9["u0"] + o9["u1"]) / 2.0, o9["u1"]):
                dd = (_par_v(u8) - o9["v1"]) * K8       # 下手の面 → 辺5[m]
                if worst is None or dd < worst[0]:
                    worst = (dd, u8)
            if worst[0] < kc - 1e-6:
                bad.append("帯の『%s』の下手の面から辺5まで %.1fm(u%.1f)— %.1fm 以上あける"
                           "(⛔ 汀へ寄せない)" % (o9["name"], worst[0], worst[1], kc))
        if mz is not None and o9["pad"] is not None:
            above = (o9["y"] if o9["y"] is not None else o9["pad"]) - wy8
            if above < mz - 1e-6:
                bad.append("帯の『%s』の足元 %.2f が水面 %.2f より %.2fm しか高くない — "
                           "%.1fm 以上要る(⛔ 汀へ下ろさない)"
                           % (o9["name"], o9["y"] if o9["y"] is not None else o9["pad"],
                              wy8, above, mz))
    # ⛔ **軒線が見透しの窓(扇)へ入らない**(2026-09-03 検図5巡目 K251)
    nk8 = obi.get("nokiOut", 0.0) / K8
    for o9 in obi_metrics(d):
        if not o9["roofed"]:
            continue
        worst = None
        for u8 in (o9["u0"] - nk8, o9["u1"] + nk8):
            for v8 in (o9["v0"] - nk8, o9["v1"] + nk8):
                ax8 = axis_at(d, v8)
                if not ax8:
                    continue
                inn = min(u8 - ax8[0], ax8[1] - u8)      # 正なら扇の中
                if inn > 0 and (worst is None or inn > worst[0]):
                    worst = (inn, u8, v8)
        if worst:
            bad.append("帯の『%s』の軒先が見透しの窓へ %.2fm 入る((%.2f, %.2f))— "
                       "南へ寄せるか u1 を詰める" % (o9["name"], worst[0] * K8,
                                                  worst[1], worst[2]))
    # ⛔ **宣言した垣が実体を指しているか**(2026-09-03 庭方5巡目 K235)
    for f9 in (obi.get("fences") or []):
        at9 = f9.get("at")
        if not any(at9 == s9.get("name") for s9 in d.get("service", []) + d.get("wells", [])):
            bad.append("帯の垣『%s h%.1f』の相手『%s』が実体に無い"
                       % (f9.get("kata", ""), f9.get("h", 0), at9))
    rf = (d.get("roofs") or {}).get("ObiNagaya") or {}
    if "盲面" not in str(rf.get("mado", "")):
        bad.append("崖下の長屋の**水側(西)を盲面にする**宣言が屋根の欄に無い")
    return bad


def mado_metrics(d):
    """**見透しの窓の効き**を数で出す。⛔ 図にも表にも数を書かない — ここが唯一の出どころ。

    ⭐ 2026-09-03 ユーザー裁定7=B(23間 → 14間・相似)の効きを、庭方の算出と突き合わせるために
      同じ量を出す: 区画界での開き / 片側の開き角 / 稜線に対する
      「法肩の松を置かない区間」と「林の下端の口」/ 窓の坪 / 見える水面。
    ⚠ 眼高は当図の値(基準身長からの従属値)を使うので、庭方の版と厳密には一致しない。"""
    N9 = d.get("nishi") or {}
    md = N9.get("mado") or {}
    K9 = d["const"]["ken"]
    fan = md.get("fan") or []
    if not fan:
        return None
    o = {"openKen": fan[-1][2] - fan[-1][1]}
    o["angDeg"] = math.degrees(math.atan2((fan[-1][2] - fan[0][2]) * K9,
                                          (fan[-1][0] - fan[0][0]) * K9))
    # 稜線=法肩帯の全長(松の区間の外端どうし)
    hk = N9.get("hokata") or {}
    sp = hk.get("spans") or []
    o["ridgeKen"] = (sp[-1][1] - sp[0][0]) if sp else 0.0
    o["hokataGapKen"] = (sp[1][0] - sp[0][1]) if len(sp) >= 2 else 0.0
    # 林の下端の口(u の飛び)
    eg = [(a9, b9) for a9, b9 in ((N9.get("hayashi") or {}).get("edge") or [])]
    gap = (0.0, None)
    for a9, b9 in zip(eg, eg[1:]):
        if abs(b9[0] - a9[0]) > gap[0]:
            gap = (abs(b9[0] - a9[0]), (a9, b9))
    o["hayashiGapKen"] = gap[0]
    o["hayashiGapAt"] = gap[1]
    for k9, nm in (("hokataGapKen", "hokataPct"), ("hayashiGapKen", "hayashiPct")):
        o[nm] = (100.0 * o[k9] / o["ridgeKen"]) if o["ridgeKen"] else 0.0
    # 窓の坪(法肩 fan[0].v から区画界まで・1間² = 1坪)
    ar = 0.0
    v9 = fan[0][0]
    while v9 < fan[-1][0]:
        a8 = axis_at(d, v9); b8 = axis_at(d, v9 + 0.5)
        if a8 and b8:
            ar += ((a8[1] - a8[0]) + (b8[1] - b8[0])) / 2.0 * 0.5
        v9 += 0.5
    o["tsubo"] = ar
    # 見える水面[m²] — 窓の角の中で、見えはじめる距離から対岸の汀まで
    # ⭕ **可視水面は `mizu_visible`(方位ごとの掃き+極座標積分)に一本化**
    #   (2026-09-03 庭方5巡目 K202)。⛔ 二つの物差しを持たない。
    mv = mizu_visible(d)
    if mv:
        o["seeM2"] = mv["m2"]
        o["seeFromRange"] = mv["seeFrom"]
        o["seeAngDeg"] = mv["angDeg"]
        o["seeFarM"] = None
    else:
        o["seeM2"] = None
    return o


def axis_at(d, v):
    """見透しの窓の左右の縁(u0, u1)を v で引く。**扇**なので v ごとに広がる。
    ⛔ 平行な帯(`axisU0/axisU1`)は 2026-09-02 に廃止した — 遠くほど広げないと視野が窄まる。"""
    fan = (((d.get("nishi") or {}).get("mado") or {}).get("fan")) or []
    if not fan:
        return None
    if v <= fan[0][0]:
        return (fan[0][1], fan[0][2])
    for a9, b9 in zip(fan, fan[1:]):
        if v <= b9[0]:
            t = (v - a9[0]) / max(b9[0] - a9[0], 1e-9)
            return (a9[1] + (b9[1] - a9[1]) * t, a9[2] + (b9[2] - a9[2]) * t)
    return (fan[-1][1], fan[-1][2])


def in_mado(d, u, v):
    a = axis_at(d, v)
    return bool(a) and a[0] - 1e-9 <= u <= a[1] + 1e-9


def mado_hlimit(d, v, u=None):
    """窓の中に置ける樹高の上限[m]。

    ⭐ **`u` を渡すと、その点の地盤で切り直す**(2026-09-03 庭方4巡目)。
      ⛔ 表(`hLimit`)は扇の芯(眼の u)の地盤で作った断面の値なので、
        芯から外れた木にそのまま当てると**地盤の差だけ嘘になる**
        (庭方の実測 5.67m 対 当図 5.03m の残差 0.42m はこれだった)。
      ⭕ 視線(ray)は v だけで決まるので、**ray を復元してから幹元の地盤を引く**。"""
    md = ((d.get("nishi") or {}).get("mado") or {})
    t9 = md.get("hLimit") or []
    if not t9:
        return None
    if u is not None:                       # ⭕ 幹元の地盤で切る(⛔ 表は扇の芯の断面)
        ey = md.get("eye") or {}
        cr = md.get("crest")
        g9 = _dem_at(d, u, v)
        if ey.get("eyeY") is not None and cr and g9 is not None and cr[0] > ey.get("v", 0):
            k9 = (v - ey["v"]) / (cr[0] - ey["v"])
            ray = ey["eyeY"] + (cr[1] - ey["eyeY"]) * k9
            return max(0.0, round(ray - g9 - md.get("clearance", 1.0), 2))
    if v <= t9[0][0]:
        return t9[0][1]
    if v <= t9[0][0]:
        return t9[0][1]
    for a9, b9 in zip(t9, t9[1:]):
        if v <= b9[0]:
            k = (v - a9[0]) / max(b9[0] - a9[0], 1e-9)
            return a9[1] + (b9[1] - a9[1]) * k
    return t9[-1][1]


def nishi_items(d):
    """西の斜面と岸に置く「点で位置が決まる物」。(種別, 名, u, v, 丈)。"""
    N = d.get("nishi") or {}
    out = []
    for m in ((N.get("mado") or {}).get("matsu") or []):
        out.append(("窓のクロマツ", m["name"], m["u"], m["v"], m["h"]))
    for e in ((N.get("hojiri") or {}).get("enoki") or []):
        out.append(("法尻のエノキ", e["name"], e["u"], e["v"], e["hMax"]))
    yd = (N.get("hayashi") or {}).get("yadake")
    if yd:
        out.append(("ヤダケの一叢", "ヤダケ", (yd["u0"] + yd["u1"]) / 2.0,
                    (yd["v0"] + yd["v1"]) / 2.0, yd["hMax"]))
    # ⛔ **法肩帯の松を入れる**(2026-09-02 庭方: 検査が見ていなかった)。位置は帯の中で
    #   芯々を割り付けた点。窓に掛かるかを見るのが目的なので、代表の並びで足りる。
    hk = N.get("hokata") or {}
    for i9, u9, v9 in hokata_pts(d):
        out.append(("法肩の松", "法肩帯%d" % i9, u9, v9, hk.get("hMax", 0)))
    # ⛔ **法尻のススキも入れる**(2026-09-03 庭方4巡目 K163) — `dMin/dMax` という別キーで
    #   持っていたため検査の網の外にあった。位置は宣言されていないので、
    #   **帯の代表点**(法尻の帯の中ほど)で見る。⛔ 窓の中には置かない宣言(`outsideMado`)。
    hj9 = N.get("hojiri") or {}
    su9 = hj9.get("susuki") or {}
    if su9.get("hMax") and not su9.get("outsideMado"):
        # ⭕ **帯の中でいちばん厳しい所**(区画界寄り)で見る — そこに置けないなら
        #   「帯のどこにでも置ける」とは言えない。⛔ 帯の中ほどで甘く見ない。
        out.append(("法尻のススキ", "ススキ", 0.5, su9.get("checkV", 160.0), su9["hMax"]))
    # ⛔ **窓のススキも丈を持つ**。位置は宣言されていないので、置ける限界の v を別に算出して刷る。
    return out


def _hokata_gates(d):
    """**法肩の帯に開く口の u**(宣言した木戸 + 動線・坂が帯を横切る所)。⛔ 二箇所で作らない。"""
    hk = (d.get("nishi") or {}).get("hokata") or {}
    vm = (hk.get("v0", 0) + hk.get("v1", 0)) / 2.0
    out = [g9 for g9 in (hk.get("gateU") or [])]
    lines = [rp9.get("pts") or [] for rp9 in d.get("ramps", [])]
    lines += [r9.get("pts") or [] for r9 in d.get("routes", [])
              if "勝手" in (r9.get("label") or "")]
    for pts in lines:
        for a9, b9 in zip(pts, pts[1:]):
            if (a9[1] - vm) * (b9[1] - vm) > 0 or abs(b9[1] - a9[1]) < 1e-9:
                continue
            t9 = (vm - a9[1]) / (b9[1] - a9[1])
            out.append(a9[0] + (b9[0] - a9[0]) * t9)
    return out


def hokata_pts(d):
    """**法肩帯の松の位置**(区間ごとに本数を割り付け、芯々を不等に振る)。

    ⭐ 2026-09-03 庭方の決定: **11本(南6・北5)**。⛔ 総数だけでは実装が割り方を決められない
      ので `spanN` を持つ。⛔ 等間隔にしない — `jitterSeed` で固定した振れを掛ける。
    ⚠ 10本ではどう割っても片方が上限 `pitchMax` を破る(6/4 なら北が 5.27間)。"""
    hk = (d.get("nishi") or {}).get("hokata") or {}
    sp = hk.get("spans") or []
    ns = hk.get("spanN") or []
    vm = (hk.get("v0", 0) + hk.get("v1", 0)) / 2.0
    rnd = random.Random(hk.get("jitterSeed", 0))
    # ⛔ **木戸の口で区間を割る**(2026-09-03 庭方5巡目 K205) — 口をまたいで芯々を割ると
    #   口の両側に松が寄って、口の前が塞がるか芯々が上限を破る。
    # ⭕ 口 = 宣言した木戸 + 動線・坂が帯を横切る所(`_hokata_gates` が唯一の出どころ)
    gz = _hokata_gates(d)
    gc = hk.get("gateClearKen", 1.0)
    sub = []
    for i9, (a9, b9) in enumerate(sp):
        n9 = ns[i9] if i9 < len(ns) else max(1, int(round((b9 - a9) / 4.0)))
        cuts = []
        for g9 in sorted(q9 for q9 in gz if a9 < q9 < b9):
            lo9, hi9 = g9 - gc, g9 + gc
            if cuts and lo9 <= cuts[-1][1] + 1e-9:      # ⭕ 重なる口はひとつに畳む
                cuts[-1] = (cuts[-1][0], max(cuts[-1][1], hi9))
            else:
                cuts.append((lo9, hi9))
        if not cuts:
            sub.append((i9, a9, b9, n9, None))
            continue
        segs, cur = [], a9
        for lo, hi in sorted(cuts):
            if lo > cur:
                segs.append((cur, lo))
            cur = max(cur, hi)
        if cur < b9:
            segs.append((cur, b9))
        # ⭕ **本数は「芯々の規則から要る数」で割る**(⛔ 長さの按分にしない) —
        #   按分だと、口で切れた短い断片に1本だけ残って芯々が上限を破る
        #   (2026-09-03 検図5巡目 K245: 6.19間 と 2.00間 が同時に出た)。
        mid9 = (hk.get("pitchMin", 3.0) + hk.get("pitchMax", 4.5)) / 2.0
        got = [max(1, int(round((q[1] - q[0]) / mid9)) + 1) for q in segs]
        # 宣言の本数に合わせる(⛔ 足りない/余るときは検査が鳴らす)
        while sum(got) > n9 and max(got) > 1:
            k8 = max(range(len(got)), key=lambda i8: (segs[i8][1] - segs[i8][0]) / got[i8])
            if got[k8] <= 1:
                break
            got[k8] -= 1
        while sum(got) < n9:
            k8 = max(range(len(got)),
                     key=lambda i8: (segs[i8][1] - segs[i8][0]) / max(got[i8] - 1, 1))
            got[k8] += 1
        for (lo, hi), k8 in zip(segs, got):
            # ⭕ 1本しか置けない小区間は、**もとの区間の端(=窓の縁)側**へ寄せる
            #   (⛔ 真ん中に置くと窓の縁に松が立たず、そこだけ対岸から抜ける)。
            end9 = None
            if k8 == 1:
                if abs(hi - b9) < 1e-6:
                    end9 = hi
                elif abs(lo - a9) < 1e-6:
                    end9 = lo
            sub.append((i9, lo, hi, k8, end9))
    out = []
    for i9, a9, b9, n9, end9 in sub:
        if n9 <= 1:
            out.append((i9, end9 if end9 is not None else (a9 + b9) / 2.0, vm))
            continue
        # ⭕ **両端にも立てる**(区間の端=窓の縁に松が無いと、そこだけ対岸から棟が抜ける)。
        base = (b9 - a9) / float(n9 - 1)
        dev = [rnd.uniform(-1.0, 1.0) for _ in range(n9 - 1)]
        mu = sum(dev) / len(dev)
        dev = [q - mu for q in dev]                    # ⭕ 合計を変えない(区間長を保つ)
        mx = max(abs(q) for q in dev) or 1.0
        amp = min(base - hk.get("pitchMin", 3.0), hk.get("pitchMax", 4.5) - base, 0.6)
        dev = [q / mx * max(amp, 0.0) for q in dev]    # ⛔ 等間隔にしない・⛔ 上下限を割らない
        u9 = a9
        pts9 = [u9]
        for k9 in range(n9 - 1):
            u9 += base + dev[k9]
            pts9.append(u9)
        # ⛔ **木戸の口に松の芯を置かない**(2026-09-03 庭方5巡目 K205)
        gz = hk.get("gateU") or []
        gc = hk.get("gateClearKen", 1.0)
        for gu in gz:
            for k9, q9 in enumerate(pts9):
                if abs(q9 - gu) < gc:
                    pts9[k9] = gu + (gc if q9 >= gu else -gc)
        for q9 in pts9:
            out.append((i9, q9, vm))
    return out


def hokata_check(d):
    """**法肩の松の割り付け。**⛔ 総数だけ見ない — 区間ごとに芯々と両端の隙を検める。

    ⚠ 2026-09-03 庭方4巡目: 検査が区間を見ていなかったため、**10本でも割り方を間違えれば
      黙って通る**状態だった(北に 9.57m の隙が空く)。"""
    hk = (d.get("nishi") or {}).get("hokata") or {}
    bad = []
    if not hk.get("spans"):
        return bad
    K9 = d["const"]["ken"]
    if sum(hk.get("spanN") or []) != hk.get("n", 0):
        bad.append("法肩の松の総数 %d と区間ごとの合計 %d が合わない"
                   % (hk.get("n", 0), sum(hk.get("spanN") or [])))
    pts = hokata_pts(d)
    subs = {}
    for i9, u9, _v9 in pts:
        subs.setdefault(i9, []).append(u9)
    # ⭕ 宣言の本数で規則が満たせるかを先に見る(⛔ 満たせないときは黙って詰めない)
    short = set()
    for i9, (a9, b9) in enumerate(hk["spans"]):
        us9 = sorted(q9[1] for q9 in pts if q9[0] == i9)
        n8 = (hk.get("spanN") or [])[i9] if i9 < len(hk.get("spanN") or []) else len(us9)
        need = 0
        segs9 = []
        cur9 = a9
        gz8 = sorted(set(round(q9, 2) for q9 in _hokata_gates(d)))
        gc8 = hk.get("gateClearKen", 1.0)
        for g9 in gz8:
            if not (a9 < g9 < b9):
                continue
            if g9 - gc8 > cur9:
                segs9.append((cur9, g9 - gc8))
            cur9 = max(cur9, g9 + gc8)
        if cur9 < b9:
            segs9.append((cur9, b9))
        mid8 = (hk.get("pitchMin", 3.0) + hk.get("pitchMax", 4.5)) / 2.0
        for lo8, hi8 in segs9:
            need += max(1, int(round((hi8 - lo8) / mid8)) + 1)
        if need > n8:
            short.add(i9)          # ⭕ 根を1件だけ出す(⛔ 同じ原因で芯々の指摘を重ねない)
            bad.append("法肩の松の区間 %d は口が %d 箇所で切れており、芯々 %.1f〜%.1f間 を"
                       "保つには **%d 本**要る(宣言 %d 本)— 庭方の割り付けへ差し戻す"
                       % (i9, len(segs9) - 1, hk.get("pitchMin", 3.0),
                          hk.get("pitchMax", 4.5), need, n8))
    for gu in (hk.get("gateU") or []):
        near = min((abs(q9[1] - gu) for q9 in pts), default=99.0)
        if near < hk.get("gateClearKen", 1.0) - 1e-6:
            bad.append("法肩の松の芯が木戸の口(u%.1f)から %.2f間 — %.1f間 以上あけること"
                       % (gu, near, hk.get("gateClearKen", 1.0)))
    gz9 = [g9 for g9 in (hk.get("gateU") or [])]
    gc9 = hk.get("gateClearKen", 1.0)
    for i9, (a9, b9) in enumerate(hk["spans"]):
        us = sorted(q[1] for q in pts if q[0] == i9)
        if not us:
            bad.append("法肩の松の区間 %d(u%.1f〜%.1f)に1本も無い" % (i9, a9, b9))
            continue
        # ⛔ 木戸の口をまたぐ隙は「芯々」ではない(口は空けるのが設計)
        if i9 in short:
            continue               # ⛔ 本数が足りない区間で芯々を重ねて鳴らさない(根は上の1件)
        gaps = [b8 - a8 for a8, b8 in zip(us, us[1:])
                if not any(a8 < g9 < b8 for g9 in gz9)]
        ends = [us[0] - a9, b9 - us[-1]]
        worst = max(gaps) if gaps else 0.0
        if worst > hk.get("pitchMax", 4.5) + 1e-6:
            bad.append("法肩の松の区間 %d の芯々の最大 %.2f間(%.1fm)が上限 %.1f間 を超える"
                       % (i9, worst, worst * K9, hk.get("pitchMax", 4.5)))
        if gaps and min(gaps) < hk.get("pitchMin", 3.0) - 1e-6:
            bad.append("法肩の松の区間 %d の芯々の最小 %.2f間 が下限 %.1f間 を割る"
                       % (i9, min(gaps), hk.get("pitchMin", 3.0)))
        if max(ends) > hk.get("endGapMax", 0.6) + 1e-6:
            bad.append("法肩の松の区間 %d の端の隙 %.2f間(%.1fm)が %.1f間 を超える — "
                       "窓の縁に松が立たず、そこだけ対岸から棟が抜ける"
                       % (i9, max(ends), max(ends) * K9, hk.get("endGapMax", 0.6)))
    return bad


def hokata_need(d):
    """**法肩の松に要る樹高。**⛔ **要求は窓の外にだけ掛ける** — 窓は意図して開けてあるので、
    窓の中を通る光線を遮蔽の要求に混ぜない(混ぜると要る丈が過大に出る。2026-09-02 に
    指図方が 8.63m と出したのがこの誤り)。

    ⚠ **御殿の大棟の高さが設計値に無い**ので、庭方が3つの候補で総当たりした結果を持つ。
    ⛔ 検査は**最悪の候補**で見る。大棟が設計値に入ったら `needByRidge` を1本にする。"""
    N = (d.get("nishi") or {}).get("hokata") or {}
    sh = N.get("shading")
    if not sh or not sh.get("needByRidge"):
        return None
    nb = sh["needByRidge"]; rc = sh.get("ridgeCandidates") or []
    k9 = nb.index(max(nb))
    return {"needH": max(nb), "ridgeY": rc[k9] if k9 < len(rc) else None,
            "byRidge": list(zip(rc, nb)), "worstAt": sh.get("worstAt"),
            "sens": sh.get("sensitivity"), "scope": sh.get("scope", "窓の外だけ")}


def nishi_check(d):
    """**西の斜面と岸の不変条件。**⛔ 図で宣言したことを全部ここへ落とす。

    ① 窓の中の物は `mado.hLimit` を超えない(超えると床几から水面が見えなくなる)
    ② 法肩の松の丈の下限が、対岸から御殿の棟を切るのに要る高さ以上
    ③ 林の下端の線が直線でない(振れが `edgeWave` 以上)
    ④ 帯が標高で切られ、上から下へ隙間なく連なる
    ①' 窓のススキが置ける区間がある(丈が窓の上限を全域で超えていない)
    ①'' 林の下端の線の点数が `edgeRule` の範囲で、u ピッチが等間隔でない
    ⑤ 葭は水深の窓の外に出ない / 蓮は『水面』の別である
    ⑥ 柵は区画界(辺5)の上にある / 木戸は柵の上に1箇所 / 堀端の見所は1箇所
       ⛔ 「木戸は窓の外」という旧い規則は廃した(木戸は扇の軸上で見所を兼ねる)
    ⑥' 汀の杭列 — 足元が水面を跨ぐ / 頭が水面より上 / 芯々が径より大きい / 径も芯々も不同不等
    ⑦ 窓の小径は林の中を通らず、勾配が `gradMax` 以下
    """
    N = d.get("nishi")
    if not N:
        return []
    K = d["const"]["ken"]
    bad = []
    # ① 窓の中の樹高
    for kind, nm, u, v, hh in nishi_items(d):
        if not in_mado(d, u, v):
            continue
        lim = mado_hlimit(d, v, u)
        if lim is not None and hh > lim + 1e-6:
            bad.append("窓の中の%s『%s』(v%.1f)が丈 %.1fm — その位置の上限 %.1fm を超える"
                       % (kind, nm, v, hh, lim))
    for g9 in d.get("gardens", []):
        for sk9 in (g9.get("shokusai") or []):
            for q9 in (sk9.get("pts") or []):
                if not in_mado(d, q9[0], q9[1]):
                    continue
                lim = mado_hlimit(d, q9[1], q9[0])
                hh = sk9.get("hMax") or sk9.get("hMin") or 0.0
                if lim is not None and hh > lim + 1e-6:
                    bad.append("窓の中の植栽『%s』(%.1f, %.1f)が丈 %.1fm — 上限 %.1fm を超える"
                               % (sk9.get("species", ""), q9[0], q9[1], hh, lim))
    # ①' 窓のススキ — 位置は宣言されていないので「置ける限界の v」で見る
    su = (N.get("mado") or {}).get("susuki") or {}
    if su.get("hMax") and (N.get("mado") or {}).get("hLimit"):
        if su.get("vMax") is None:
            bad.append("窓のススキ(丈 %.1fm)が置ける区間が無い — 窓の中の上限が全域で丈より低い"
                       % su["hMax"])
    # ①'' 林の下端の線の作り(点数と不等)。⛔ 座標は庭方の持ち場なので、規則だけを見る
    hy0 = N.get("hayashi") or {}
    er = hy0.get("edgeRule") or {}
    eg0 = [(a9, b9) for a9, b9 in (hy0.get("edge") or [])]
    if er and eg0:
        if not (er.get("nMin", 0) <= len(eg0) <= er.get("nMax", 99)):
            bad.append("林の下端の線が %d 点 — %d〜%d 点で作ること(等間隔の鋸歯にしない)"
                       % (len(eg0), er.get("nMin", 0), er.get("nMax", 0)))
        # ⛔ **窓の口をまたぐ区間はピッチではない**(2026-09-03 庭方4巡目) —
        #   林はそこで切れているので、口の幅を「間隔が広い」と数えると規則が意味を失う。
        pit = []
        for a9, b9 in zip(eg0, eg0[1:]):
            if in_mado(d, (a9[0] + b9[0]) / 2.0, (a9[1] + b9[1]) / 2.0):
                continue
            if abs(b9[0] - a9[0]) > 1e-6:
                pit.append(abs(b9[0] - a9[0]))
        for q9 in eg0:                       # 林の木を窓の中へ置かない
            if in_mado(d, q9[0], q9[1]):
                bad.append("林の下端の点 (%.1f, %.1f) が見透しの窓の中にある" % (q9[0], q9[1]))
        if pit and (max(pit) - min(pit)) < 0.5:
            bad.append("林の下端の線の u ピッチが %.1f〜%.1f間 でほぼ等間隔 — "
                       "%.1f〜%.1f間 で振ること" % (min(pit), max(pit),
                                                 er.get("pitchMin", 0), er.get("pitchMax", 0)))
    # ①' 窓の松 — 丈が不等・三本が一直線に乗らない(庭方の宣言)
    ms9 = [m9 for m9 in ((N.get("mado") or {}).get("matsu") or []) if m9.get("h") is not None]
    if len(ms9) >= 2:
        hs9 = sorted(m9["h"] for m9 in ms9)
        dmin = min(b9 - a9 for a9, b9 in zip(hs9, hs9[1:]))
        need = (N.get("mado") or {}).get("matsuDhMin", 0.5)
        if dmin < need - 1e-6:
            bad.append("窓の松の丈が %s で、いちばん近い二本の差が %.2fm しかない"
                       "(不等に見えるには %.1fm 以上要る)"
                       % ("・".join("%.2f" % q for q in hs9), dmin, need))
    if len(ms9) >= 3:
        a9, b9, c9 = ms9[0], ms9[1], ms9[2]
        cr9 = ((b9["u"] - a9["u"]) * (c9["v"] - a9["v"])
               - (b9["v"] - a9["v"]) * (c9["u"] - a9["u"]))
        if abs(cr9) < 1.0:
            bad.append("窓の松の三本が一直線に近い(外積 %.2f)" % cr9)
    # \u2460\u2032 \u820c\u306e\u5927\u5c0f(`edgeRule.lobeRatio`)
    if er and eg0:
        amp = [abs(b8[1] - (a8[1] + c8[1]) / 2.0) for a8, b8, c8 in zip(eg0, eg0[1:], eg0[2:])]
        amp = [q8 for q8 in amp if q8 > 1e-6]
        if amp and (max(amp) / max(min(amp), 1e-9)) < er.get("lobeRatio", 2.0) - 1e-6:
            bad.append("\u6797\u306e\u4e0b\u7aef\u306e\u820c\u306e\u5927\u5c0f\u304c %.2f \u500d\u3057\u304b\u9055\u308f\u306a\u3044 \u2014 %.1f \u500d\u4ee5\u4e0a\u306b\u632f\u308b\u3053\u3068"
                       % (max(amp) / max(min(amp), 1e-9), er.get("lobeRatio", 2.0)))
    # ② 法肩の松の丈
    nd = hokata_need(d)
    hk = N.get("hokata") or {}
    if nd and hk.get("hMin") is not None and hk["hMin"] < nd["needH"] - 1e-6:
        bad.append("法肩の松の丈の下限 %.1fm が、対岸から御殿の棟を切るのに要る %.2fm に足りない"
                   "(%s。大棟の候補ごとに %s)"
                   % (hk["hMin"], nd["needH"], nd["scope"],
                      " / ".join("%.2f→%.2fm" % q for q in nd["byRidge"])))
    for g9 in d.get("gardens", []):
        for sk9 in (g9.get("shokusai") or []):
            if sk9.get("screen") and nd and (sk9.get("hMin") or 0) < nd["needH"] - 1e-6:
                bad.append("法肩の疎林『%s』の丈の下限 %.1fm が、要る %.2fm に足りない"
                           % (sk9.get("species", ""), sk9.get("hMin") or 0, nd["needH"]))
    # ③ 林の下端の線
    hy = N.get("hayashi") or {}
    eg = [(a, b) for a, b in (hy.get("edge") or [])]
    if len(eg) >= 3:
        n9 = len(eg)
        mu = sum(q[0] for q in eg) / n9; mv = sum(q[1] for q in eg) / n9
        sxx = sum((q[0] - mu) ** 2 for q in eg) or 1e-9
        sxy = sum((q[0] - mu) * (q[1] - mv) for q in eg)
        sl = sxy / sxx
        wav = max(abs(q[1] - (mv + sl * (q[0] - mu))) for q in eg)
        if wav < hy.get("edgeWave", 2.0):
            bad.append("林の下端の線の振れが ±%.2f間 しかない(直線に見える。%.1f間 以上要る)"
                       % (wav, hy.get("edgeWave", 2.0)))
    # ④ 帯が標高で連なる
    bs = d.get("slopeBands") or []
    gs9 = [b9 for b9 in bs if b9.get("kind") != "水面"]
    for b9 in gs9:
        if b9.get("y0") is None or b9.get("y1") is None:
            bad.append("地表の帯『%s』が標高で切られていない(`y0`/`y1` が出ない)" % b9.get("name"))
        elif b9["y0"] <= b9["y1"] + 1e-9:
            bad.append("地表の帯『%s』の厚さが 0(上端 %.2f ≦ 下端 %.2f)"
                       % (b9["name"], b9["y0"], b9["y1"]))
    for a9, b9 in zip(gs9, gs9[1:]):
        if a9.get("y1") is not None and b9.get("y0") is not None \
           and abs(a9["y1"] - b9["y0"]) > 1e-6:
            bad.append("帯『%s』の下端 %.2f と『%s』の上端 %.2f が繋がらない"
                       % (a9["name"], a9["y1"], b9["name"], b9["y0"]))
    # ⑤ 葭と蓮
    ts = N.get("tsutsumi") or {}
    ys = ts.get("yoshi") or {}
    g0, mg0, _r0 = pond_of(d)
    wy = ((d.get("nishi") or {}).get("tsutsumi") or {}).get("waterY") or 6.60
    if ys:
        lo = wy - ys.get("depthMax", 0.3); hi = wy - ys.get("depthMin", -0.3)
        fb = next((b9 for b9 in bs if "葭" in b9.get("name", "")), None)
        if fb and fb.get("y0") is not None and (fb["y0"] > hi + 1e-6 or fb["y1"] < lo - 1e-6):
            bad.append("葭原の帯 %.2f〜%.2f が、ヨシの育つ水深の窓 %.2f〜%.2f の外へ %.2fm 出る"
                       % (fb["y0"], fb["y1"], lo, hi, max(fb["y0"] - hi, lo - fb["y1"])))
    hb = next((b9 for b9 in bs if "蓮" in b9.get("name", "")), None)
    if hb and hb.get("kind") != "水面":
        bad.append("蓮の帯が『水面』の別になっていない — 水に浮く葉は標高で切れない")
    # ⑥ 柵と木戸
    sk9 = N.get("saku") or {}
    if sk9:
        fe = [f for f in d.get("fences", []) if f["edge"] == sk9.get("edge")]
        if not fe:
            bad.append("汀の柵が辺%s に載っていない(`fences` に無い)" % sk9.get("edge"))
        # ⛔ **「木戸は窓の外」という旧い規則は廃した**(2026-09-02 庭方) —
        #   柵は柵際に立っても足元の水を隠すので、**木戸を扇の軸上に置いて見所と兼ねる**のが設計。
        #   ⭕ 見るのは「1箇所だけであること」と「柵(区画界)の上にあること」。
        kd = sk9.get("kido")
        if kd:
            if not isinstance(kd, dict):
                bad.append("木戸が1箇所に定まっていない")
            else:
                dd9 = _par_near(d, kd["u"], kd["v"])
                if dd9[1] != sk9.get("edge") or dd9[0] * K > 1.0:
                    bad.append("木戸 (%.1f, %.1f) が柵の辺%s の上に無い(最寄りは辺%d・%.2fm)"
                               % (kd["u"], kd["v"], sk9.get("edge"), dd9[1], dd9[0] * K))
        mk9 = [m for m in (N.get("mikoro") or [])]
        if len(mk9) > 1:
            bad.append("堀端の見所が %d 箇所ある — 木戸と兼ねる1箇所に絞ること" % len(mk9))
    # ⑥' 汀の杭列(2026-09-02 庭方3巡目で新設)
    #   ⛔ 位置は区画の外で復元地盤が当たらないので**平面では検めない** —
    #     検めるのは「水面との高さの関係」と「不同・不等であること」。
    ku = N.get("kuiretsu")
    if ku:
        gmin, gmax = ku.get("groundMin"), ku.get("groundMax")
        if gmin is None or gmax is None:
            bad.append("汀の杭列の足元の地盤が宣言されていない")
        elif not (gmin - 1e-9 <= wy <= gmax + 1e-9):
            bad.append("汀の杭列の足元 %.2f〜%.2f が水面 %.2f を跨がない — 杭は汀線に立つ"
                       % (gmin, gmax, wy))
        if (ku.get("topMin") or 0) <= 0:
            bad.append("汀の杭の頭 +%.2f が水面より上に出ない" % (ku.get("topMin") or 0))
        if ku.get("pitchMin", 0) <= ku.get("dMax", 0):
            bad.append("汀の杭の芯々の下限 %.2fm が径の上限 %.2fm 以下 — 杭どうしがめり込む"
                       % (ku.get("pitchMin", 0), ku.get("dMax", 0)))
        for k9, lo, hi, nm9 in (("d", "dMin", "dMax", "径"), ("p", "pitchMin", "pitchMax", "芯々")):
            if ku.get(hi, 0) - ku.get(lo, 0) < 1e-9:
                bad.append("汀の杭の%sが %.2f の一定 — 不同・不等にすること" % (nm9, ku.get(lo, 0)))
        if _kui_n(d) <= 0:
            bad.append("汀の杭の本数が算出できない(辺%s の長さか芯々が無い)" % ku.get("edge"))
    # ⑥'' 汀の並び E堤 → 杭列(汀線)→ F葭原 → G蓮(2026-09-03 庭方の決定 K185)
    #   ⛔ 従前は「葭は杭の陸側」と宣言しながら作図が逆で、検査は順序を見ていなかった。
    ts9 = N.get("tsutsumi") or {}
    ys9 = ts9.get("yoshi") or {}
    fb9 = next((b8 for b8 in bs if "葭" in b8.get("name", "")), None)
    if ku and fb9 is not None and ts9:
        gmin, gmax = ku.get("groundMin"), ku.get("groundMax")
        gmid = ((gmin + gmax) / 2.0) if (gmin is not None and gmax is not None) else None
        # ① 葭原の上端 == 水面 == 杭の足元
        if fb9.get("y0") is not None and abs(fb9["y0"] - wy) > 1e-6:
            bad.append("葭原の上端 %.2f が水面 %.2f と違う — 葭は杭の**沖**(水の中)から始まる"
                       % (fb9["y0"], wy))
        # ② 葭原の勾配(深さ ÷ 幅)が緩いこと
        wmin = ys9.get("wMin", 0.0)
        if wmin > 1e-9:
            inv = wmin / max(ys9.get("depthMax", 0.3), 1e-9)
            lim9 = ts9.get("yoshiBatterMin", 5.0)
            if inv < lim9 - 1e-6:
                bad.append("葭原がいちばん狭い所で 1:%.1f — 1:%.1f より急にしない"
                           "(深さ %.2fm ÷ 幅 %.1fm)"
                           % (inv, lim9, ys9.get("depthMax", 0.3), wmin))
        # ③ 帯Eの法尻・帯Fの上端・杭の足元の代表値が一致
        eb9 = next((b8 for b8 in bs if b8.get("name", "").startswith("E")), None)
        if eb9 is not None and gmid is not None and eb9.get("y1") is not None:
            if max(abs(eb9["y1"] - wy), abs(gmid - wy)) > 0.06:
                bad.append("汀の三つ(帯Eの法尻 %.2f / 帯Fの上端 %.2f / 杭の足元 %.2f)が"
                           "水面 %.2f で揃っていない" % (eb9["y1"], fb9.get("y0") or 0, gmid, wy))
        # ④ 蓮の外端の水深(⚠ 区画の外なので**前提**として鳴らす)
        hs9 = ts9.get("hasu") or {}
        if hs9.get("bedYMin") is None:
            bad.append("蓮の外端の池床(`hasu.bedYMin`)が宣言されていない — "
                       "区画の外の前提なので必ず書き、溜池の普請へ渡す")
        elif wy - hs9["bedYMin"] > hs9.get("depthMax", 1.5) + 1e-6:
            bad.append("蓮の外端の水深 %.2fm が %.1fm を超える — ハスは立てない"
                       "(⚠ 区画の外の前提。溜池側が決まったら実測へ)"
                       % (wy - hs9["bedYMin"], hs9.get("depthMax", 1.5)))
    # ⑥''' 堤の天端の振れと、二つの章の遮蔽点の一致(2026-09-03 検図4巡目)
    ts8 = N.get("tsutsumi") or {}
    if ts8.get("y0Range"):
        spr = ts8["y0Range"][1] - ts8["y0Range"][0]
        if spr > ts8.get("y0SpreadMax", 0.30) + 1e-9:
            bad.append("堤の天端の振れが %.2fm ある(%.2f〜%.2f)— %.2fm 以内に収まらないのは"
                       "標本が区画線の段を跨いでいる疑い"
                       % (spr, ts8["y0Range"][0], ts8["y0Range"][1],
                          ts8.get("y0SpreadMax", 0.30)))
    # ⛔ **同じ点を二つの章が別の値で読まない** — 其十一(借景)と其十二(窓)の遮蔽点。
    md8 = N.get("mado") or {}
    try:
        sm8 = shakkei_metrics(d)
    except Exception:
        sm8 = None
    if sm8 and md8.get("crest") and sm8.get("crestY") is not None:
        if abs(sm8["crestY"] - md8["crest"][1]) > 0.02:
            bad.append("視線を切る所の標高が章で割れている — 借景の章 %.2f / 窓の章 %.2f。"
                       "同じ点(汀の柵の天端)を別の物差しで読んでいる"
                       % (sm8["crestY"], md8["crest"][1]))
    # ①''''' **棟の頂点(大棟・妻)を窓の視線へ総当たり**(2026-09-03 考証 K193)
    #   ⛔ 樹だけ見ても足りない — 屋根は動かないので、**窓から見えるかは棟で決まる**。
    #   ⚠ 御殿の大棟の高さは設計値に無いので `hokata.shading.ridgeCandidates` を**総当たり**する。
    md7 = N.get("mado") or {}
    ey7 = md7.get("eye") or {}
    cr7 = md7.get("crest")
    if ey7.get("eyeY") is not None and cr7:
        def _ray(v9):
            k9 = (v9 - ey7["v"]) / max(cr7[0] - ey7["v"], 1e-9)
            return ey7["eyeY"] + (cr7[1] - ey7["eyeY"]) * k9
        cl7 = md7.get("clearance", 1.0)
        rf7 = d.get("roofs") or {}
        apex = []
        nk7 = (N.get("obi") or {}).get("nokiOut", 0.0) / K      # 軒の出[間]
        for s7 in d.get("service", []):            # 崖下の帯の棟(実寸の棟高を持つ)
            if not s7.get("obi") or not s7.get("roof"):
                continue
            r7 = rf7.get(s7["roof"]) or {}
            # ⭕ **軒線の矩形**で総当たり(2026-09-03 考証 K228 / 検図 K251) —
            #   躯体の隅だけ見ると、軒先が扇へ入っていても丸ごと素通りする。
            for u8 in (s7["u0"] - nk7, (s7["u0"] + s7["u1"]) / 2.0, s7["u1"] + nk7):
                for v8 in (s7["v0"] - nk7, (s7["v0"] + s7["v1"]) / 2.0, s7["v1"] + nk7):
                    apex.append(("%s の軒先" % (s7.get("label") or s7["name"]), u8, v8,
                                 (s7.get("y") or 0) + r7.get("eaveH", 0)))
                    apex.append((s7.get("label") or s7["name"], u8, v8,
                                 (s7.get("y") or 0) + r7.get("ridgeH", 0)))
        sh7 = (N.get("hokata") or {}).get("shading") or {}
        for m7 in d.get("munes", []):              # 御殿の棟 — 大棟の候補ごと
            for rc in (sh7.get("ridgeCandidates") or []):
                for u8 in (m7["u0"], m7["u1"]):
                    for v8 in (m7["v0"], m7["v1"]):
                        apex.append(("%s(大棟の候補 %.2f)" % (MUNE_JA.get(m7["name"], m7["name"]), rc),
                                     u8, v8, rc))
        for nm7, u8, v8, y8 in apex:
            # ⛔ **眼より手前(v が小さい側)は窓ではない** — 扇は前にしか開かない。
            if v8 <= ey7["v"] + 1e-9 or not in_mado(d, u8, v8):
                continue
            lim7 = _ray(v8) - cl7
            if y8 > lim7 + 1e-6:
                bad.append("窓の中の棟の頂点『%s』(%.1f, %.1f)の高さ %.2f が"
                           "視線 − 余裕 %.2f を超える" % (nm7, u8, v8, y8, lim7))
    # ①'''' 窓の開きと、幕(松の列・林の下端)の口(2026-09-03 ユーザー裁定7=B)
    md9 = N.get("mado") or {}
    mm9 = mado_metrics(d)
    if mm9 and md9.get("fanTopKen") is not None and (md9.get("fan") or []):
        top9 = md9["fan"][0][2] - md9["fan"][0][1]
        if abs(top9 - md9["fanTopKen"]) > 0.01:
            bad.append("\u6247\u306e\u4e0a\u7aef\u306e\u5e45 %.2f\u9593 \u304c\u5ba3\u8a00 %.2f\u9593 \u3068\u9055\u3046"
                       % (top9, md9["fanTopKen"]))
    if mm9 and md9.get("fanMaxKen") is not None:
        if mm9["openKen"] > md9["fanMaxKen"] + 1e-6:
            bad.append("見透しの窓の開きが区画界で %.2f間 — 裁定7=B の上限 %.1f間 を超える"
                       % (mm9["openKen"], md9["fanMaxKen"]))
    # 窓の中に置く松(`hDesign` を持つもの)は扇の中に居ること
    for m9 in (md9.get("matsu") or []):
        if m9.get("hDesign") is None:
            continue
        if not in_mado(d, m9["u"], m9["v"]):
            ax9 = axis_at(d, m9["v"]) or (0.0, 0.0)
            bad.append("窓の松『%s』(%.2f, %.2f)が扇の外 — その v の窓は u%.2f〜%.2f"
                       % (m9["name"], m9["u"], m9["v"], ax9[0], ax9[1]))
    # 幕の口(⛔ 窓を細めたのに幕を開けたままにしない)
    #   ⭐ **肩ごとに見る**(2026-09-03 普請奉行の裁定) — 総幅で見る形だと、庭方が
    #     **わざと不揃いに置いた肩**(南 0.6間・北 0.7間 外)が、その不揃いのぶんで鳴ってしまう。
    #     ⛔ 検査の形が意匠の規則と合っていなかった(意匠は「肩ごとに窓の外へ少し」)。
    #   ⭕ 見るのは「その肩の v での**窓の縁からの外側の余裕**」で、
    #     `gapClearKen` を超えたら開けすぎ・**負なら窓の中に入っている**。
    if mm9:
        cl9 = md9.get("gapClearKen", 0.75)

        def _kata(lab, uS, vS, uN, vN):
            axS = axis_at(d, vS) or (0.0, 0.0)
            axN = axis_at(d, vN) or (0.0, 0.0)
            for nm8, got, lim_in in (("南の肩", axS[0] - uS, axS),
                                     ("北の肩", uN - axN[1], axN)):
                if got > cl9 + 1e-6:
                    bad.append("%sの%sの余裕が %.2f間 — 窓の縁から %.2f間 までに寄せる"
                               "(窓を細めたぶん幕を閉じる)" % (lab, nm8, got, cl9))
                elif got < -1e-6:
                    bad.append("%sの%s が窓の中へ %.2f間 入っている" % (lab, nm8, -got))
        hk9 = N.get("hokata") or {}
        if hk9.get("spans") and hk9.get("v0") is not None:
            vm8 = (hk9["v0"] + hk9.get("v1", hk9["v0"])) / 2.0
            ax8 = axis_at(d, vm8) or (0.0, 0.0)
            # ⭕ **窓を挟む肩**を選ぶ(⛔ 区間の一番端どうしではない) —
            #   2026-09-03 庭方6巡目 K262 で南が3区間に割れ、端が窓から 20間 離れた。
            sS = max((q8[1] for q8 in hk9["spans"] if q8[1] <= ax8[0] + 1e-9),
                     default=hk9["spans"][0][1])
            sN = min((q8[0] for q8 in hk9["spans"] if q8[0] >= ax8[1] - 1e-9),
                     default=hk9["spans"][-1][0])
            _kata("法肩の松の口", sS, vm8, sN, vm8)
        if mm9.get("hayashiGapAt"):
            a9, b9 = mm9["hayashiGapAt"]
            _kata("林の下端の口", a9[0], a9[1], b9[0], b9[1])
    # ⑦ 小径
    km = (N.get("mado") or {}).get("komichi") or {}
    pts = [(a, b) for a, b in (km.get("pts") or [])]
    # ⛔ **1件に丸めるが、件数と最悪値は必ず出す**(点ごとに並べると1つの原因で表が埋まる)。
    vlim = (N.get("mado") or {}).get("fanLimitV", 1e9)
    out9 = [q for q in pts if q[1] <= vlim and not in_mado(d, q[0], q[1])]
    if out9:
        ax9 = axis_at(d, out9[0][1])
        bad.append("窓の小径の折れ点 %d/%d 点が、斜面(v≦%.1f)で窓の外=林の中を通る — "
                   "最初は (%.1f, %.1f)、その v での窓は u%.1f〜%.1f"
                   % (len(out9), len(pts), vlim, out9[0][0], out9[0][1], ax9[0], ax9[1]))
    gmax = 0.0; gwhere = None
    for a9, b9 in zip(pts, pts[1:]):
        ya, yb = _dem_at(d, a9[0], a9[1]), _dem_at(d, b9[0], b9[1])
        if ya is None or yb is None:
            continue
        L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K
        if L9 > 1e-6:
            g9 = 100.0 * abs(yb - ya) / L9
            if g9 > gmax:
                gmax, gwhere = g9, (a9, b9)
    # ⑦' **脚の中の段**を見る(2026-09-03)。⛔ 脚ごとの平均だけでは段が隠れる —
    #   庭方が末端で 25.6% の段を見つけたとき、当図の検査は**脚の平均 7.3% しか見ておらず
    #   0件のままだった**(段の正体は復元地盤の縁の癖で、DEM 側を直した)。
    #   ⭕ 判定は「その脚の平均の `stepRatio` 倍」と `gradMax` の**大きいほう**を超えたら段。
    #     ⛔ 絶対値だけで見ない — 設計どおり急な脚(14.5%)まで鳴ってしまう。
    win9 = km.get("stepWinKen", 2.0)
    rat9 = km.get("stepRatio", 2.0)
    for a9, b9 in zip(pts, pts[1:]):
        ya, yb = _dem_at(d, a9[0], a9[1]), _dem_at(d, b9[0], b9[1])
        L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
        if ya is None or yb is None or L9 < 1e-6:
            continue
        avg9 = 100.0 * abs(yb - ya) / (L9 * K)
        n9 = max(1, int(math.ceil(L9 / win9)))
        for i9 in range(n9):
            p9 = (a9[0] + (b9[0] - a9[0]) * i9 / n9, a9[1] + (b9[1] - a9[1]) * i9 / n9)
            q9 = (a9[0] + (b9[0] - a9[0]) * (i9 + 1) / n9, a9[1] + (b9[1] - a9[1]) * (i9 + 1) / n9)
            y1_, y2_ = _dem_at(d, p9[0], p9[1]), _dem_at(d, q9[0], q9[1])
            ll9 = math.hypot(q9[0] - p9[0], q9[1] - p9[1]) * K
            if y1_ is None or y2_ is None or ll9 < 1e-6:
                continue
            loc9 = 100.0 * abs(y2_ - y1_) / ll9
            if loc9 > min(max(km.get("gradMax", 20.0), avg9 + km.get("stepAddPt", 3.0)),
                          avg9 * rat9 if rat9 else 1e9) + 1e-6:
                bad.append("窓の小径の (%.1f,%.1f)→(%.1f,%.1f) に段がある — "
                           "%.1f間 の窓で %.0f%%(この脚の平均は %.0f%%)"
                           % (p9[0], p9[1], q9[0], q9[1], win9, loc9, avg9))
                break
    if gmax > km.get("gradMax", 20.0) + 1e-6:
        bad.append("窓の小径の最急勾配 %.0f%% が上限 %.0f%% を超える"
                   "((%.1f,%.1f)→(%.1f,%.1f))— 斜面が %.0f%% あるので振りを増やすか折り返しを足す"
                   % (gmax, km.get("gradMax", 20.0), gwhere[0][0], gwhere[0][1],
                      gwhere[1][0], gwhere[1][1], gmax))
    return bad


def slope_table(d):
    """**斜面と岸の帯割り。⛔ 割合ではなく標高で切る。**(共有 lib の割合版を当邸で差し替える)"""
    bs = d.get("slopeBands") or []
    rows = []
    wy = ((d.get("nishi") or {}).get("tsutsumi") or {}).get("waterY", 6.60)
    for b9 in bs:
        if b9.get("kind") == "水面":
            rng = "<b>水面 %.2f</b> の上(標高で切れない)" % wy
        elif b9.get("y0") is None or b9.get("y1") is None:
            rng = "—"
        else:
            rng = "%.2f → %.2f" % (b9["y0"], b9["y1"])
        note9 = ""
        if b9["name"].startswith(("D", "E")):
            ln9 = (((d.get("nishi") or {}).get("tsutsumi") or {}).get("y0Line")) or []
            if ln9:
                # ⛔ **帯D/Eの境を単一値で引かない**(2026-09-03 検図4巡目 K162 / 庭方) —
                #   単一値だと、それより低い堀端の約94坪がどの帯にも属さなくなる。
                note9 = ("<br><span class='note'>境は<b>u ごとの線</b>(%d点・%.2f〜%.2f・"
                         "中央の代表 %.2f)。⛔ 単一値で引かない</span>"
                         % (len(ln9), min(q[1] for q in ln9), max(q[1] for q in ln9),
                            (((d.get("nishi") or {}).get("tsutsumi") or {}).get("y0") or 0)))
        if b9["name"].startswith("B"):
            eg9 = [(a8, b8) for a8, b8 in (((d.get("nishi") or {}).get("hayashi") or {})
                                           .get("edge") or [])]
            ys9 = [q for q in (_dem_at(d, a8, b8) for a8, b8 in eg9) if q is not None]
            if ys9:
                # ⛔ **下端の境は標高ではなく線が正典**(2026-09-03 庭方4巡目)。
                note9 = ("<br><span class='note'>下端の公称 %.1f に対し、"
                         "<b>線の実地盤は %.2f〜%.2f</b>(%d点)。"
                         "⛔ <b>境の正典は <code>hayashi.edge</code> の線</b>で、公称は目安。</span>"
                         % (b9.get("y1") or 0, min(ys9), max(ys9), len(ys9)))
        rows.append("<tr><td><b>%s</b></td><td>%s</td><td>%s%s</td><td class='note'>%s</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (b9["name"], b9.get("kind", "地表"), rng, note9, b9["veg"],
                       "<code>%s</code>" % b9.get("asset", ""), cert_sig(d, b9)))
    return ("<h3>西の斜面と岸の帯(%d帯)</h3><div class='tw'><table><thead><tr><th>帯</th>"
            "<th>別</th><th>標高</th><th class='note'>植生</th><th class='note'>部材</th>"
            "<th>確度</th></tr></thead><tbody>%s</tbody></table></div>"
            "<p class='cap'>⛔ <b>帯は法肩からの割合ではなく標高で切る</b>(2026-09-02 庭方) — "
            "割合で切ると斜面の勾配が場所ごとに違うので帯の境が地形と合わない。"
            "⛔ <b>中部を低木にしない</b> — [名所図会・溜池]<b>S</b> が保証するのは"
            "<b>上=樹林 / 下=草地の二層</b>までで、崖面の中ほどを低木の帯にする読みは支えない"
            "(⚠ <b>林冠を閉じるのは当方の設計判断=U</b>)。"
            "⛔ <b>竹は使わない</b>(竹薮は江戸の水辺79事例中1例)。"
            "ヤダケの一叢だけは例外で、林の中に1箇所。竹垣の材としての竹は別。"
            "⚠ <b>『水面』の帯は標高で切れない</b> — 水に浮く葉なので地表の帯とは物が違う"
            "(⛔ 厚さ0の帯を作らない)。"
            "⚠ <b>区画界(辺5)より外は江戸期の復元が当たっていない</b>ので、"
            "堤・葭・蓮・水面は<b>設計線</b>として持つ(地形DEMから拾わない)。</p>"
            % (len(bs), "".join(rows)))


def nishi_cross_svg(d, vCut):
    """**西の岸 — 南北の横断**(v を固定して u を横に取る)。

    ⚠ 2026-09-03 検図5巡目 K247 で作り直した。⛔ 前の版は
      ① 区画の外の近代の地面を実線で描き(自分のキャプションに反する)
      ② 汀の柵を断面の全幅に19本立て(実体は**辺5との交点の1本**)
      ③ 区画界の縦線が無く ④ 堤・葭・杭・蓮を一つも描かなかった。
    ⭐ **辺5は斜めに走る**ので、v を固定した断面は**1点でしか区画界を切らない**。
      その点より西は**設計線**(堤 1:`batter` → 水面 → 葭 → 杭 → 蓮)で描く。"""
    N = d.get("nishi") or {}
    ts = N.get("tsutsumi") or {}
    sk = N.get("saku") or {}
    K = d["const"]["ken"]
    W, H = 900.0, 320.0
    o = _sv(W, H, "西の岸(横断 v=%.0f)" % vCut)
    # ① 区画の中だけを実測で拾う(⛔ 外は拾わない)
    us = [q / 4.0 for q in range(-4 * 30, 4 * 25)]
    prof = [(u9, _dem_at(d, u9, vCut)) for u9 in us if in_parcel(d, u9, vCut)]
    prof = [(a9, b9) for a9, b9 in prof if b9 is not None]
    if not prof:
        return ""
    # ② 辺5(区画界)をこの v で切る u
    P9 = d["polygon"]
    e5 = sk.get("edge", 5)
    gr = RGrid(d)
    pa, pb = gr.L(*P9[e5]), gr.L(*P9[(e5 + 1) % len(P9)])
    uPar = None
    if abs(pb[1] - pa[1]) > 1e-9:
        s9 = (vCut - pa[1]) / (pb[1] - pa[1])
        if -0.01 <= s9 <= 1.01:
            uPar = pa[0] + (pb[0] - pa[0]) * s9
    u0 = min(q[0] for q in prof) - 1.0
    u1 = (uPar if uPar is not None else max(q[0] for q in prof)) + 6.0
    y0, y1 = 4.0, max(q[1] for q in prof) + 3.0

    def X(u9):
        return 52.0 + (W - 66.0) * (u9 - u0) / (u1 - u0)

    def Y(y9):
        return H - 46.0 - (H - 76.0) * (y9 - y0) / (y1 - y0)
    for y9 in range(int(y0), int(y1) + 1, 2):
        o.append(LN(X(u0), Y(y9), X(u1), Y(y9), "var(--rule)", 0.6))
        o.append(T(46, Y(y9) + 4, "%d" % y9, "jo", "end"))
    wy = ts.get("waterY", 6.60)
    o.append(R(X(u0), Y(wy), X(u1) - X(u0), Y(y0) - Y(wy), fill="var(--ike)", op=0.30))
    o.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.8"/>'
             % " ".join("%.1f,%.1f" % (X(a9), Y(b9)) for a9, b9 in prof))
    # ③ 区画界の縦線と、そこに立つ**1本**の柵
    if uPar is not None:
        yPar = _dem_at(d, uPar - 0.3, vCut) or prof[-1][1]
        o.append(LN(X(uPar), Y(y0), X(uPar), Y(y1), "var(--shu)", 1.2, dash="4 3"))
        o.append(T(X(uPar), Y(y1) - 6, "区画界(辺%s)" % e5, "jo", "middle"))
        o.append(T(X(uPar) + 5, Y(y1) + 8, "← 実測　設計線 →", "jo"))
        if sk.get("h"):
            o.append(LN(X(uPar), Y(yPar), X(uPar), Y(yPar + sk["h"]), "#6B5637", 2.4))
            o.append(T(X(uPar) - 6, Y(yPar + sk["h"]) - 4,
                       "汀の柵 h%.1f(1本)" % sk["h"], "jo", "end"))
        # ④ 外は設計線 — 堤 1:batter → 水面 → 葭 → 杭 → 蓮
        bat = ts.get("batter", 2.2)
        mg = (yPar - wy) * bat / K                      # 水面までの水平[間]
        o.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="2.2" '
                 'stroke-dasharray="7 4"/>'
                 % " ".join("%.1f,%.1f" % (X(a9), Y(b9))
                            for a9, b9 in ((uPar, yPar), (uPar + mg, wy))))
        o.append(T(X(uPar + mg / 2), Y((yPar + wy) / 2) - 6,
                   "E 堤(1:%.1f・%.1fm)" % (bat, mg * K), "jo", "middle"))
        ys9 = ts.get("yoshi") or {}
        o.append(R(X(uPar + mg), Y(wy + ys9.get("hMax", 2.0)),
                   max(X(uPar + mg + ys9.get("wMax", 6.0) / K) - X(uPar + mg), 1.0),
                   abs(Y(wy + ys9.get("hMax", 2.0)) - Y(wy)), fill="#9FB98C", op=0.5))
        o.append(T(X(uPar + mg) + 4, Y(wy + ys9.get("hMax", 2.0)) - 4,
                   "F 葭原(幅 %.0f〜%.0fm・稈高 %.1f〜%.1fm)"
                   % (ys9.get("wMin", 0), ys9.get("wMax", 0),
                      ys9.get("hMin", 0), ys9.get("hMax", 0)), "jo"))
        ku9 = N.get("kuiretsu") or {}
        if ku9:
            hd = wy + (ku9.get("topMin", 0.25) + ku9.get("topMax", 0.45)) / 2.0
            for i9 in range(7):
                uk = uPar + mg + i9 * 0.25
                o.append(LN(X(uk), Y(hd), X(uk), Y(wy - 0.6), "#6B5637", 1.0))
            o.append(T(X(uPar + mg) + 4, Y(hd) + 12, "杭列(汀線)", "jo"))
        hs9 = ts.get("hasu") or {}
        u3 = uPar + mg + hs9.get("fromM", 8.0) / K
        u4 = uPar + mg + hs9.get("toM", 30.0) / K
        o.append(R(X(min(u3, u1)), Y(wy + hs9.get("leafMax", 0.9)),
                   max(X(min(u4, u1)) - X(min(u3, u1)), 1.0),
                   abs(Y(wy + hs9.get("leafMax", 0.9)) - Y(wy)), fill="#6E8B4E", op=0.5))
        o.append(T(X(min(u3, u1)) + 4, Y(wy + hs9.get("leafMax", 0.9)) - 4,
                   "G 蓮(汀から %.0f〜%.0fm)" % (hs9.get("fromM", 0), hs9.get("toM", 0)), "jo"))
    # ⑤ 木戸は「その v の断面が木戸を切るとき」だけ
    kd = sk.get("kido") or {}
    if kd and abs(kd.get("v", 0) - vCut) < 0.75:
        o.append(LN(X(kd["u"]), Y(y0), X(kd["u"]), Y(y1), "var(--shu)", 1.6))
        o.append(T(X(kd["u"]), Y(y1) - 18, "木戸(敷居 %.2f)" % (kd.get("groundY") or 0),
                   "jo", "middle"))
    # ⑥ 崖下の棟をこの断面が切るなら描く
    rf9 = (d.get("roofs") or {}).get("ObiNagaya") or {}
    for o9 in obi_metrics(d):
        if not (o9["v0"] <= vCut <= o9["v1"]) or not o9["roofed"]:
            continue
        yb = o9["y"] or 0
        o.append(R(X(o9["u0"]), Y(yb + rf9.get("eaveH", 2.7)), X(o9["u1"]) - X(o9["u0"]),
                   abs(Y(yb + rf9.get("eaveH", 2.7)) - Y(yb)), fill="#8A8A80", op=0.8))
        o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#4A4A52"/>'
                 % (X(o9["u0"] - 0.5), Y(yb + rf9.get("eaveH", 2.7)),
                    X((o9["u0"] + o9["u1"]) / 2), Y(yb + rf9.get("ridgeH", 4.3)),
                    X(o9["u1"] + 0.5), Y(yb + rf9.get("eaveH", 2.7))))
        o.append(T(X((o9["u0"] + o9["u1"]) / 2), Y(yb + rf9.get("ridgeH", 4.3)) - 5,
                   o9["name"], "jo", "middle"))
    ex = _vexag(X, Y, K)
    o.append(T(52, H - 12, "u[間](左=南 / 右=北)／ 縦は標高[m]・**縦%.2f倍**。"
               "⚠ **辺5は斜めに走る**ので、この断面が区画界を切るのは<b>1点だけ</b>"
               "(u%.1f)。その西は設計線" % (ex, uPar if uPar is not None else 0), "anS2"))
    o.append("</svg>")
    return "\n".join(o)


def _vexag(X, Y, K):
    """縦の誇張倍率(横1間=K[m] に対する縦[m]の倍率)。⛔ 「誇張なし」と書かない(K252)。"""
    dx = abs(X(1.0) - X(0.0)) / K            # px / 横1m
    dy = abs(Y(1.0) - Y(0.0))                # px / 縦1m
    return dy / dx if dx > 1e-9 else 1.0


def nishi_plan_svg(d):
    """**西の斜面と岸 — 平面。**窓(扇)・林の下端の線・法肩の松・榎・柵・木戸・小径。"""
    N = d.get("nishi") or {}
    pr = LProj(-30.0, 24.0, 104.0, 172.0, 900.0)
    o = _sv(pr.W, pr.H, "岡部筑前守上屋敷 西の斜面と岸")
    o.append(_clip(pr))
    gr = RGrid(d)
    K = d["const"]["ken"]
    P = [gr.L(x, z) for x, z in d["polygon"]]
    o.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.85"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    for t in d["terraces"]:
        o.append(pr.poly(tpoly(t), fill=dan_color(d, t["y"]), op=1.0))
        for hp in tholes(t):
            o.append(pr.poly(hp, fill=_pat(), stroke="var(--dim)", sw=0.8, dash="4 3"))
    ring = " ".join("L %.1f %.1f" % (pr.X(u), pr.Y(v)) for u, v in P)
    o.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z %s" fill="var(--paper2)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, "M" + ring[1:] + " Z"))
    o.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    # 林(下端の線から法肩まで)
    hy = N.get("hayashi") or {}
    eg = [(a, b) for a, b in (hy.get("edge") or [])]
    if eg:
        west = [(q[0], q[1]) for q in eg]
        ring2 = west + [(eg[-1][0], 111.0), (eg[0][0], 111.0)]
        o.append(pr.poly(ring2, fill="#7E9A6B", op=0.45, stroke="#4E6B3E", sw=1.0))
        o.append('<polyline points="%s" fill="none" stroke="#3E5A30" stroke-width="2.0"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(a), pr.Y(b)) for a, b in west))
        o.append(T(pr.X(-22), pr.Y(120), hy.get("label", "林"), "anS2", "middle"))
    # ⭕ **床几(見所⑨)と視軸**(2026-09-03 庭方5巡目 K239) — 起点が図に無いと視軸を指せない。
    ey9 = (N.get("mado") or {}).get("eye") or {}
    if ey9.get("u") is not None:
        fan9 = (N.get("mado") or {}).get("fan") or []
        if fan9:
            for uEnd in (fan9[-1][1], fan9[-1][2]):
                o.append(LN(pr.X(ey9["u"]), pr.Y(ey9["v"]), pr.X(uEnd), pr.Y(fan9[-1][0]),
                            "var(--shu)", 0.8, dash="3 3"))
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>'
                 % (pr.X(ey9["u"]), pr.Y(ey9["v"])))
        o.append(T(pr.X(ey9["u"]) + 8, pr.Y(ey9["v"]) + 4, "⑨ 床几(眼 %.2f)"
                   % (ey9.get("eyeY") or 0), "jo"))
    # 見透しの窓(扇)
    fan = (N.get("mado") or {}).get("fan") or []
    if fan:
        poly = [(q[1], q[0]) for q in fan] + [(q[2], q[0]) for q in reversed(fan)]
        o.append(pr.poly(poly, fill="var(--shirasu)", op=0.85, stroke="var(--shu)", sw=1.2, dash="6 4"))
        o.append(T(pr.X(0), pr.Y(150), "見透しの窓(扇)", "anS2", "middle"))
    # ⭕ **区画の外の帯も破線で描く**(2026-09-03 検図4巡目) — 平面に堤・杭列・葭・蓮が
    #   一本も無く、断面だけが持っていた。⛔ 実線にしない(設計線であることを図で示す)。
    ts9 = N.get("tsutsumi") or {}
    mgl = ts9.get("mizugiwaLine")
    if mgl:
        e9 = (N.get("saku") or {}).get("edge", 5)
        P9 = d["polygon"]
        a9, b9 = P9[e9], P9[(e9 + 1) % len(P9)]
        nx9, nz9 = _inward(P9, e9)
        n9 = len(mgl) - 1

        def _off(i9, m9):
            t9 = i9 / float(n9) if n9 else 0.0
            return gr.L(a9[0] + (b9[0] - a9[0]) * t9 - nx9 * m9,
                        a9[1] + (b9[1] - a9[1]) * t9 - nz9 * m9)
        ys9 = ts9.get("yoshi") or {}
        hs9 = ts9.get("hasu") or {}
        for lab, offs, col in (("汀線(杭列 約%d本)" % _kui_n(d),
                                [q[1] for q in mgl], "#6B5637"),
                               ("葭原の沖端", [q[1] + ys9.get("wMax", 6.0) for q in mgl], "#9FB98C"),
                               ("蓮の外端", [q[1] + hs9.get("toM", 30.0) for q in mgl], "#6E8B4E")):
            pl = [_off(i9, m9) for i9, m9 in enumerate(offs)]
            o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.8" '
                     'stroke-dasharray="8 5" opacity="0.9"/>'
                     % (" ".join("%.1f,%.1f" % (pr.X(q[0]), pr.Y(q[1])) for q in pl), col))
            o.append(T(pr.X(pl[len(pl) // 2][0]) , pr.Y(pl[len(pl) // 2][1]) - 5, lab, "jo", "middle"))
    # ⭕ **崖下の帯の棟と勝手の坂を描く**(2026-09-03 庭方5巡目 K229) —
    #   json に決めた棟が平面に一つも出ていなかった。
    for o9 in obi_metrics(d):
        o.append(pr.rect(o9["u0"], o9["v0"], o9["u1"], o9["v1"],
                         fill="var(--ink-lo)", stroke="var(--ink)", sw=1.0,
                         op=0.85 if o9["roofed"] else 0.5))
        o.append(T(pr.X((o9["u0"] + o9["u1"]) / 2), pr.Y((o9["v0"] + o9["v1"]) / 2) + 4,
                   o9["name"], "jo", "middle"))
    for w9 in d.get("wells", []):
        if w9.get("obi"):
            o.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="none" stroke="var(--ink)" '
                     'stroke-width="1.2"/>' % (pr.X(w9["u"]), pr.Y(w9["v"])))
            o.append(T(pr.X(w9["u"]) + 7, pr.Y(w9["v"]) + 4, "井戸", "jo"))
    for rp9 in d.get("ramps", []):
        if not rp9.get("cutW"):
            continue
        o.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="2.6" '
                 'stroke-linecap="round" opacity="0.85"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(a9), pr.Y(b9)) for a9, b9 in rp9["pts"]))
        mid = rp9["pts"][len(rp9["pts"]) // 2]
        o.append(T(pr.X(mid[0]) - 6, pr.Y(mid[1]), "勝手の坂", "jo", "end"))
    # ヤダケ
    yd = hy.get("yadake")
    if yd:
        o.append(pr.rect(yd["u0"], yd["v0"], yd["u1"], yd["v1"], fill="var(--take)", op=0.5,
                         stroke="var(--take)", sw=1.0))
        o.append(T(pr.X((yd["u0"] + yd["u1"]) / 2), pr.Y(yd["v1"]) + 10, "ヤダケの一叢", "jo", "middle"))
    # 法肩の松
    hk = N.get("hokata") or {}
    # ⛔ **平面が別の割り付けで描かない**(2026-09-03 庭方5巡目 K234) —
    #   検査は `hokata_pts`(区間ごとの本数・振れ・口の避け)を見るのに、
    #   図は等間隔の別ループで12本描いていた。⭕ 正典は一つ。
    for _i9, u9, v9 in hokata_pts(d):
        o.append(_tree(pr, u9, v9, 5.0, "#2F5A2F"))
    # 榎
    for e in ((N.get("hojiri") or {}).get("enoki") or []):
        o.append(_tree(pr, e["u"], e["v"], 8.0, "#7A5C3A"))
        o.append(T(pr.X(e["u"]) + 10, pr.Y(e["v"]) + 4, "%s 榎" % e["name"], "jo"))
    # 窓の松
    for m in ((N.get("mado") or {}).get("matsu") or []):
        o.append(_tree(pr, m["u"], m["v"], 4.5, "#2F5A2F"))
        o.append(T(pr.X(m["u"]) + 8, pr.Y(m["v"]) - 4, "%s h%.1f" % (m["name"], m["h"]), "jo"))
    # 小径
    km = (N.get("mado") or {}).get("komichi") or {}
    if km.get("pts"):
        o.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="3.0" '
                 'stroke-linecap="round" opacity="0.7"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(a), pr.Y(b)) for a, b in km["pts"]))
        o.append(T(pr.X(km["pts"][3][0]) - 8, pr.Y(km["pts"][3][1]), "窓の小径", "jo", "end"))
    # 柵と木戸
    sk = N.get("saku") or {}
    if sk:
        e5 = sk.get("edge", 5)
        a9, b9 = gr.L(*d["polygon"][e5]), gr.L(*d["polygon"][(e5 + 1) % len(d["polygon"])])
        o.append(LN(pr.X(a9[0]), pr.Y(a9[1]), pr.X(b9[0]), pr.Y(b9[1]), "var(--nagaya)", 3.4))
        kd = sk.get("kido")
        if kd:
            t9 = (kd["u"] - a9[0]) / ((b9[0] - a9[0]) or 1e-9)
            o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>'
                     % (pr.X(a9[0] + (b9[0] - a9[0]) * t9), pr.Y(a9[1] + (b9[1] - a9[1]) * t9)))
            o.append(T(pr.X(kd["u"]) - 7, pr.Y(a9[1] + (b9[1] - a9[1]) * t9) + 4, "木戸", "jo", "end"))
    for mk in (N.get("mikoro") or []):
        o.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (pr.X(mk["u"]), pr.Y(mk["v"])))
        o.append(T(pr.X(mk["u"]), pr.Y(mk["v"]) + 4, MARU[mk["no"] - 1], "sr", "middle", 10.0, "#fff"))
    o.append(T(4, 15, "グリッド座標。**上=東 / 左=北 / 下=西(溜池) / 右=南**", "anS"))
    o.append("</g></svg>")
    return "\n".join(o)


def nishi_sec_svg(d, axisU=None, inForest=False):
    """**西の斜面と岸 — 縦断(窓の芯)。**
    ⛔ **区画界より外は地形DEMから拾わない** — そこは江戸期の復元が当たっていない現代の地面なので、
      堤・葭・蓮・水面は**設計線**として描く(2026-09-02 検図/庭方の致命)。
      縦線で「区画界」と「DEM が尽きる所」を示し、その先が設計線であることを図の上で明示する。
    ⛔ **床几の視線は眼と枠の右端を結んだ直線にしない** — それでは地面の下を通る。
      **実測の最急点(手前の高まり)を掠める線**で描き、手前の死角をハッチする。"""
    N = d.get("nishi") or {}
    K = d["const"]["ken"]
    md = N.get("mado") or {}
    ts = N.get("tsutsumi") or {}
    W, H = 900.0, 360.0
    o = _sv(W, H, "西の斜面と岸(縦断)")
    ey = md.get("eye") or {}
    u0 = ey.get("u", 0.5) if axisU is None else axisU
    v0, v1 = 106.0, 178.0
    y0, y1 = 4.0, 30.0

    def X(v):
        return 52.0 + (W - 66.0) * (v - v0) / (v1 - v0)

    def Y(y):
        return H - 36.0 - (H - 64.0) * (y - y0) / (y1 - y0)
    for y in range(int(y0), int(y1) + 1, 4):
        o.append(LN(X(v0), Y(y), X(v1), Y(y), "var(--rule)", 0.6))
        o.append(T(46, Y(y) + 4, "%d" % y, "jo", "end"))
    # 区画の中は実測、外は設計線
    prof = []
    vpar = None
    v = v0
    while v <= v1:
        if in_parcel(d, u0, v):
            yy = _dem_at(d, u0, v)
            if yy is not None:
                prof.append((v, yy)); vpar = v
        v += 0.25
    wy = ts.get("waterY", 6.60)
    o.append(R(X(v0), Y(wy), X(v1) - X(v0), Y(y0) - Y(wy), fill="var(--ike)", op=0.5))
    o.append(T(X(v1) - 8, Y(wy) - 6, "溜池の水面 %.2f(設計値)" % wy, "anS2", "end"))
    # 帯(地表)を профиль の上へ
    COL = {"A": "#2F5A2F", "B": "#7E9A6B", "C": "#5E7A4E", "D": "#CFCF9A",
           "E": "#D8CFA8", "F": "#9FB98C", "G": "#A9C2CE"}
    for b9 in (d.get("slopeBands") or []):
        if b9.get("kind") == "水面" or b9.get("y0") is None:
            continue
        # ⛔ **窓の芯で「林」を刷らない**(2026-09-03 庭方4巡目 K158) —
        #   帯は標高で切ってあるが、見透しの窓の中は**芝**で林ではない。
        if (not inForest) and b9["name"].startswith(("B", "C")):
            continue
        seg = [q for q in prof if b9["y1"] - 1e-9 <= q[1] <= b9["y0"] + 1e-9]
        if len(seg) < 2:
            continue
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="6" '
                 'stroke-linecap="butt" opacity="0.85"/>'
                 % (" ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in seg), COL.get(b9["name"][0], "var(--dim)")))
        m9 = seg[len(seg) // 2]
        o.append(T(X(m9[0]), Y(m9[1]) - 10, b9["name"][0], "sr", "middle"))
    if prof:
        o.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4"/>'
                 % " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in prof))
    # ---- 区画界の外は設計線(堤 → 葭 → 蓮)
    if vpar is not None and ts.get("y0") is not None:
        vt = vpar
        # ⛔ **法線方向の距離を v 軸へそのまま置かない**(2026-09-03 検図5巡目 K253) —
        #   辺5は斜めなので、法線の 10.05m を v へ置くと図上の法が 1:1.99(宣言 1:2.2 より急)になる。
        #   ⭕ **v 方向へ投影**する(cosθ で割る)。θ は辺5の法線と v 軸のなす角。
        P8 = d["polygon"]
        e8 = (N.get("saku") or {}).get("edge", 5)
        nx8, nz8 = _inward(P8, e8)
        gr8 = RGrid(d)
        o8 = gr8.L(0.0, 0.0)
        n8 = gr8.L(nx8, nz8)
        cos8 = abs(n8[1] - o8[1]) or 1.0                # 法線の v 成分(単位ベクトル)
        dv = ts.get("mizugiwaM", 0.0) / K / cos8
        line = [(vt, ts["y0"]), (vt + dv, ts["y1"])]
        o.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="2.2" '
                 'stroke-dasharray="7 4"/>'
                 % " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in line))
        o.append(T(X(vt + dv / 2) , Y((ts["y0"] + ts["y1"]) / 2) - 8, "E 堤(設計線 1:%.1f)"
                   % ts.get("batter", 2.2), "jo", "middle"))
        vy = vt + dv
        ys8 = ts.get("yoshi") or {}
        vy2 = vy + (ys8.get("wMax", 6.0) / K / cos8)     # ⭕ 葭の幅は宣言から(⛔ 直書きしない)
        o.append(R(X(vy), Y(ts["y1"] + 2.2), X(vy2) - X(vy), abs(Y(ts["y1"] + 2.2) - Y(ts["y1"])),
                   fill="#9FB98C", op=0.65))
        o.append(T(X(vy2) + 4, Y(ts["y1"]) - 4, "F 葭原(%.2f→%.2f・稈高 %.1f〜%.1f)"
                   % (ts["y1"], ts.get("yoshiBottom", 0), (ts.get("yoshi") or {}).get("hMin", 0),
                      (ts.get("yoshi") or {}).get("hMax", 0)), "jo"))
        ku9 = N.get("kuiretsu")
        if ku9:
            # 杭列は**汀線**に立つ(葭原の沖側・蓮の陸側)。頭は水面 + topMin〜topMax。
            hd = wy + (ku9.get("topMax", 0.45) + ku9.get("topMin", 0.25)) / 2.0
            for i9 in range(9):
                vk = vy2 - 0.9 + 0.22 * i9
                o.append(LN(X(vk), Y(hd), X(vk), Y(wy - ku9.get("neire", 1.2)),
                            "#6B5637", 1.2))
            o.append(LN(X(vy2 - 1.0), Y(hd - (ku9.get("nuki") or {}).get("below", 0.35)),
                        X(vy2 + 0.9), Y(hd - (ku9.get("nuki") or {}).get("below", 0.35)),
                        "#6B5637", 1.0))
            o.append(T(X(vy2 - 0.1), Y(hd) - 6, "杭列(約 %d 本・頭 水面+%.2f〜%.2f)"
                       % (_kui_n(d), ku9.get("topMin", 0), ku9.get("topMax", 0)), "jo", "middle"))
        hs = ts.get("hasu") or {}
        # ⭕ 蓮は**汀線から**測る(⛔ 葭の沖端からではない)
        v3 = vy + hs.get("fromM", 8.0) / K / cos8
        v4 = min(v1, vy + hs.get("toM", 30.0) / K / cos8)
        o.append(R(X(v3), Y(wy + hs.get("leafMax", 0.9)), X(v4) - X(v3),
                   abs(Y(wy + hs.get("leafMax", 0.9)) - Y(wy)), fill="#6E8B4E", op=0.55))
        o.append(T(X((v3 + v4) / 2), Y(wy + hs.get("leafMax", 0.9)) - 5,
                   "G 蓮(葉高 水面+%.1f〜%.1f)" % (hs.get("leafMin", 0), hs.get("leafMax", 0)),
                   "jo", "middle"))
        # 縦線: 区画界 / DEM が尽きる所
        o.append(LN(X(vpar), Y(y0), X(vpar), Y(y1), "var(--shu)", 1.2, dash="4 3"))
        o.append(T(X(vpar), Y(y1) - 6, "区画界(辺%s)" % (N.get("saku") or {}).get("edge", ""),
                   "jo", "middle"))
        o.append(T(X(vpar) + 5, Y(y1) + 8, "← 実測(江戸期の復元地盤)　設計線 →", "jo"))
    # ---- 床几の視線: 手前の高まりを掠める線 + 死角のハッチ
    cr = md.get("crest")
    if ey.get("eyeY") is not None and cr:
        sl = (cr[1] - ey["eyeY"]) / ((cr[0] - ey["v"]) * K)
        vend = v1
        o.append(LN(X(ey["v"]), Y(ey["eyeY"]), X(vend),
                    Y(ey["eyeY"] + sl * (vend - ey["v"]) * K), "var(--shu)", 1.6, dash="7 4"))
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>' % (X(ey["v"]), Y(ey["eyeY"])))
        o.append(T(X(ey["v"]) + 6, Y(ey["eyeY"]) - 6, "床几の眼 %.2f" % ey["eyeY"], "anS2"))
        o.append(LN(X(cr[0]), Y(y0), X(cr[0]), Y(y1), "var(--dim)", 0.8, dash="3 3"))
        o.append(T(X(cr[0]), Y(y1) - 18, "視線を切る所 %.2f(刈草地の肩)" % cr[1], "jo", "middle"))
        sf = md.get("seeFromM")
        if sf:
            vsee = ey["v"] + sf / K
            o.append(R(X(cr[0]), Y(wy), max(1.0, X(min(vsee, v1)) - X(cr[0])),
                       abs(Y(wy) - Y(y0)), fill=_pat(), op=0.9))
            o.append(T((X(cr[0]) + X(min(vsee, v1))) / 2, Y(wy) + 14,
                       "死角 %.0fm" % (sf - (cr[0] - ey["v"]) * K), "jo", "middle"))
    # ---- 窓の中の樹高の上限
    hl = md.get("hLimit") or []
    if hl:
        pts = []
        for vv, hh in hl:
            g9 = _dem_at(d, u0, vv)
            if g9 is not None:
                pts.append((vv, g9 + hh))
        if pts:
            o.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="1.2" '
                     'stroke-dasharray="2 3"/>' % " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in pts))
            o.append(T(X(pts[len(pts) // 2][0]), Y(pts[len(pts) // 2][1]) - 6,
                       "窓の中の樹高の上限(視線 − %.1fm)" % md.get("clearance", 1.0), "jo", "middle"))
    for mk in (N.get("mikoro") or []):
        o.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--shu)"/>'
                 % (X(mk["v"]), Y(mk.get("eyeY", wy))))
        o.append(T(X(mk["v"]), Y(mk.get("eyeY", wy)) - 8,
                   "%s %s" % (MARU[mk["no"] - 1], mk.get("label", "")), "jo", "middle"))
    o.append(T(52, H - 10, "横軸=v(グリッド)／ 縦=標高[m]・**縦%.2f倍**。帯は標高で切る"
               % _vexag(X, Y, K), "anS2"))
    o.append("</svg>")
    return "\n".join(o)


def nishi_table(d):
    N = d.get("nishi") or {}
    hy = N.get("hayashi") or {}
    nd = hokata_need(d) or {}
    K = d["const"]["ken"]
    tg = hy.get("takagi") or []
    ch = hy.get("chuboku") or []
    fan = (N.get("mado") or {}).get("fan") or []
    ang = 0.0
    if len(fan) >= 2:
        ang = math.degrees(math.atan2((fan[-1][2] - fan[0][2]) * K,
                                      (fan[-1][0] - fan[0][0]) * K))
    mm = mado_metrics(d) or {}
    rows = [
        ["見透しの窓(扇)", " → ".join("v%.1f で %.2f間" % (q[0], q[2] - q[1]) for q in fan)
         + "。片側の開き %.1f°(算出)" % ang
         + "<br>⭐ <b>区画界での開き %.2f間</b>【2026-09-03 ユーザー裁定7=B で 23間 から相似に細めた】"
           "／ 窓の面積 <b>%.0f 坪</b>(算出)"
         % (mm.get("openKen", 0), mm.get("tsubo", 0))],
        ["窓の効き(算出。⛔ 手で書かない)",
         "稜線(法肩帯の全長)%.1f間 に対し <b>法肩の松を置かない区間 %.1f間(%.0f%%)</b>"
         " ／ <b>林の下端の口 %.1f間(%.0f%%)</b><br>"
         "見える水面 <b>%s</b>(見えはじめ %s ／ 掃いた開き角 %s)"
         % (mm.get("ridgeKen", 0), mm.get("hokataGapKen", 0), mm.get("hokataPct", 0),
            mm.get("hayashiGapKen", 0), mm.get("hayashiPct", 0),
            ("%.0f m²" % mm["seeM2"]) if mm.get("seeM2") else "—",
            ("%.0f〜%.0f m" % tuple(mm["seeFromRange"])) if mm.get("seeFromRange") else "—",
            ("%.2f°" % mm["seeAngDeg"]) if mm.get("seeAngDeg") else "—")],
        ["窓の松2本 + 窓の外の松1本(三本一組)",
         " ／ ".join("<b>%s</b>(%+.1f, %.1f)丈 <b>%.2f</b>%s"
                    % (m9["name"], m9["u"], m9["v"], m9["h"],
                       ("(意匠 %.1f / 頭打ち %.2f = その点の上限 %.2f − %.1f)"
                        % (m9["hDesign"], m9.get("hCap") or 0,
                           (m9.get("hCap") or 0) + (N.get("mado") or {}).get("matsuMargin", 1.0),
                           (N.get("mado") or {}).get("matsuMargin", 1.0)))
                       if m9.get("hDesign") is not None else "(窓の外・入力)")
                    for m9 in ((N.get("mado") or {}).get("matsu") or []))
         + "。⛔ <b>丈の不等は作庭の判断</b>で、上限は<b>頭打ちにしか効かない</b>"
           "(いま効いている松は無い)。差の下限 %.1fm は検査が見る"
         % (N.get("mado") or {}).get("matsuDhMin", 0.5)],
        ["林の高木", "%d 本 / %d 種・芯々 %.1f〜%.1fm"
         % (sum(x["n"] for x in tg), len(tg), *(hy.get("takagiPitch") or [0, 0]))],
        ["林の中木", "%d 株 / %d 種・芯々 %.1f〜%.1fm"
         % (sum(x["n"] for x in ch), len(ch), *(hy.get("chubokuPitch") or [0, 0]))],
        ["林の低木", "%d 群(%s 株の塊)= 約 %d 株"
         % ((hy.get("teiboku") or {}).get("groups", 0),
            "・".join(str(q) for q in (hy.get("teiboku") or {}).get("perGroup", [])),
            (hy.get("teiboku") or {}).get("groups", 0) * 5)],
        ["下草", "被覆 %d%% 以上 — %s" % ((hy.get("shitakusa") or {}).get("coverPct", 0),
                                        (hy.get("shitakusa") or {}).get("species", ""))],
        ["林の下端の線", "%d 点・振れ ±%.2f間(算出。下限 %.1f間)"
         % (len(hy.get("edge") or []), _edge_wave(hy), hy.get("edgeWave", 2.0))],
        ["<b>法肩の松に要る丈</b>",
         "対岸の汀(眼 %.2f)から奥向棟を切る視線 — <b>%s</b>で要る丈は "
         "大棟の候補ごとに %s ／ 最悪の所は (u%.1f, v%.1f) ／ 感度 %.2f(大棟が1m上がると要る丈)"
         "→ <b>要る丈 %.2fm</b>(設計の下限 %.1f・上限 %.1f)"
         % ((N.get("hokata") or {}).get("shading", {}).get("farEyeY", 0),
            nd.get("scope", ""),
            " / ".join("大棟 %.2f → %.2fm" % q for q in nd.get("byRidge", [])),
            (nd.get("worstAt") or [0, 0])[0], (nd.get("worstAt") or [0, 0])[1],
            nd.get("sens", 0), nd.get("needH", 0),
            (N.get("hokata") or {}).get("hMin", 0), (N.get("hokata") or {}).get("hMax", 0))],
        ["崖下の帯の棟(裁定8=A)",
         (" ／ ".join("<b>%s</b> %.1f×%.1f間・%.0f m²(面 %.2f・切盛 %.2f)"
                     % (o9["name"], o9["u1"] - o9["u0"], o9["v1"] - o9["v0"], o9["areaM2"],
                        o9["y"] or 0, o9["dz"] or 0) for o9 in obi_metrics(d) if o9["roofed"])
          + "<br>東(山側)の余地 %s(要 %.1fm)／ 榎の幹から軒まで %s"
          % (" ／ ".join("%s %.2fm" % (q9["name"], q9["gapM"]) for q9 in obi_east_clear(d)),
             (N.get("obi") or {}).get("eastClearM", 0),
             " ／ ".join("%s→%s %.1fm" % (o9["name"], o9["gaps"][0][0], o9["gaps"][0][1])
                        for o9 in obi_metrics(d) if o9["roofed"] and o9["gaps"]))
          + "<br>汀への離れ %s(要 %.1fm)／ 水面より上 %s(要 %.1fm)"
            "<br>⭐ <b>鳴ったら真っ先に M1</b>(どちらもいまの最小)"
          % (" ／ ".join("%s %.1fm" % (q9[0], q9[1]) for q9 in obi_kishi(d)),
             (N.get("obi") or {}).get("kishiClearM", 0),
             " ／ ".join("%s %+.2fm" % (q9[0], q9[2]) for q9 in obi_kishi(d)),
             (N.get("obi") or {}).get("mizuAboveM", 0))
          + "<br>屋根 <b>%s・%s・%s腰</b>(%s)"
          % ((d.get("roofs") or {}).get("ObiNagaya", {}).get("kawara", ""),
             (d.get("roofs") or {}).get("ObiNagaya", {}).get("kai", ""),
             (d.get("roofs") or {}).get("ObiNagaya", {}).get("koshi", ""),
             (d.get("roofs") or {}).get("ObiNagaya", {}).get("mado", "")))
         if any(o9["roofed"] for o9 in obi_metrics(d)) else "—"],
        ["勝手の坂(崖下の帯へ)",
         ("路長 %.1fm・落差 %.2fm・脚ごとの最急 <b>%.1f%%</b> / "
          "<b>2間窓の局所 %.2f%%</b>(上限 %.0f%%)・脚 %.1fm 以上・折れ最大 %.0f°"
          "(⛔ 折れの規則は掛けない=林の中で見えない)<br>"
          "林の中 %.1fm ／ 伐る帯 幅 %.2fm = <b>%.0f m²(林の %.1f%%)</b> ／ "
          "高木 約%.1f本・中木 約%.1f株<br>切土 %d m³(最大 %.2fm)・盛土 %d m³(最大 %.2fm)"
          % (_rp9["measured"]["len"], _rp9["measured"]["rise"], _rp9["measured"]["grad"],
             _rp9["measured"].get("local", 0),
             _rp9.get("gradMax", 0), _rp9["measured"]["leg"], _rp9["measured"]["turn"],
             (saka_forest(d) or {}).get("inForestM", 0), _rp9.get("cutW", 0),
             (saka_forest(d) or {}).get("cutM2", 0), (saka_forest(d) or {}).get("pct", 0),
             (saka_forest(d) or {}).get("takagi", 0), (saka_forest(d) or {}).get("chuboku", 0),
             _rp9["earth"]["kiridoM3"], _rp9["earth"]["kiridoMax"],
             _rp9["earth"]["moridoM3"], _rp9["earth"]["moridoMax"])
          + "<br>⛔ <b>伐った高木の分を他所へ足さない</b>(K207)— 代わりに"
            "<b>筋の両側へ低木のマント(帯C の樹種)を寄せて</b>切り口の裾を閉じる")
         if (_rp9 := next((q for q in d.get("ramps", []) if q.get("cutW")), None)) else "—"],
        ["法尻の帯(草地)",
         "%s ／ ススキ %d〜%d 株(丈 %.1f〜%.1fm・棟から %.1f間 以上・v%.0f〜%.0f)"
         % ((N.get("hojiri") or {}).get("shiba", "—"),
            (N.get("hojiri") or {}).get("susuki", {}).get("nMin", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("nMax", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("hMin", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("hMax", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("clearKen", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("v0", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("v1", 0))],
        ["林のつる", "%s ／ <b>フジ %s 株</b>(高木の幹に。⛔ 花期の外なので花は出さない)"
         % (((N.get("hayashi") or {}).get("tsuru") or {}).get("species", "—"),
            ((N.get("hayashi") or {}).get("tsuru") or {}).get("fuji", 0))],
        ["\u26d4 書かないと決めたこと",
         "<br>".join("<b>%s</b> \u2014 %s\u3010%s\u3011"
                     % (it9.get("no", ""), inline(it9.get("why", "")), cert_sig(d, it9))
                     for it9 in ((N.get("hojiri") or {}).get("ban") or {}).get("items", []))],
        ["法尻の帯の建物 — 型と作法",
         ("<b>%s</b><br>%s<br>確度 %s"
          % (inline((N.get("obi") or {}).get("yoto", "—")),
             "<br>".join(inline(q) for q in ((N.get("obi") or {}).get("sahou") or []))
             + ("<br>\u68df\u306e\u5468\u308a %.1f\u9593 \u306f\u5208\u829d"
                % ((N.get("obi") or {}).get("shibaKen", 0)))
             + "".join("<br>%s\u306e%s\u306b %s h%.1f"
                       % (f9.get("at", ""), f9.get("side", ""), f9.get("kata", ""), f9.get("h", 0))
                       for f9 in ((N.get("obi") or {}).get("fences") or [])),
             cert_sig(d, N.get("obi") or {})))
         if N.get("obi") else "—"],
        ["法尻の余地(裁定8=A で南に一組を置いた**残り**)",
         " ／ ".join("<b>%s %.0f 坪</b>・勾配 %.1f〜%.1f%%" % (y9["label"], y9["tsubo"],
                                                          y9["gMin"], y9["gMax"])
                    for y9 in yochi_metrics(d)) or "—"],
        ["法尻の帯", "ススキ %d〜%d 株(丈 %.1f〜%.1fm・⛔ 窓の中には置かない)・"
                   "榎 %d 本(単木の大木)<br>帯の勾配 <b>%s</b>(算出。法尻から区画界へ)"
         % ((N.get("hojiri") or {}).get("susuki", {}).get("nMin", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("nMax", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("hMin", 0),
            (N.get("hojiri") or {}).get("susuki", {}).get("hMax", 0),
            len((N.get("hojiri") or {}).get("enoki") or []), _hojiri_grad(d))],
        ["汀の柵と木戸", "木柵 h%.1f を辺%s の全長に ／ 木戸 (u%.1f, v%.1f)・幅 %.2fm・h%.1f"
         "(辺の走り s=%.1fm・敷居の地盤 %.2f)。⛔ 木戸は1箇所だけ"
         % ((N.get("saku") or {}).get("h", 0), (N.get("saku") or {}).get("edge", ""),
            ((N.get("saku") or {}).get("kido") or {}).get("u", 0),
            ((N.get("saku") or {}).get("kido") or {}).get("v", 0),
            ((N.get("saku") or {}).get("kido") or {}).get("w", 0),
            ((N.get("saku") or {}).get("kido") or {}).get("h", 0),
            ((N.get("saku") or {}).get("kido") or {}).get("s", 0),
            ((N.get("saku") or {}).get("kido") or {}).get("groundY", 0))],
        ["堀端の見所", " ／ ".join(
            "%s %s (u%.1f, v%.1f)・眼 %.2f — %s"
            % (MARU[m9["no"] - 1], m9["label"], m9["u"], m9["v"], m9["eyeY"],
               "・".join(m9.get("sees") or [])) for m9 in (N.get("mikoro") or []))
         + "。⭕ <b>木戸と兼ねる</b> — 柵(h%.1f)は柵の内側からでは足元の水を隠すので、"
           "敷居に立ってはじめて水面が足元から見える"
         % (N.get("saku") or {}).get("h", 0)],
        (["窓の小径", "折れ点 %d 点・総延長 %.1fm・折り返し 2回<br>"
                   "<b>脚の平均の最急 %.2f%% / %.1f間 窓の局所の最急 %.2f%%</b>(上限 %.0f%%)"
                   "<br>手入れ松 %s の袂を抜ける — 幹の芯まで <b>%.2fm</b>"
                   "(路の半幅 %.2fm を引いて <b>%.2fm</b>)。⭕ <b>意図どおり</b>(算出)"
         % (len(((N.get("mado") or {}).get("komichi") or {}).get("pts") or []),
            _komichi_len(d), _komichi_grad(d),
            ((N.get("mado") or {}).get("komichi") or {}).get("stepWinKen", 2.0),
            _komichi_local(d)[0],
            ((N.get("mado") or {}).get("komichi") or {}).get("gradMax", 20),
            (komichi_matsu_gap(d) or {}).get("name", "—"),
            (komichi_matsu_gap(d) or {}).get("m", 0.0),
            ((N.get("mado") or {}).get("komichi") or {}).get("w", 0.9) / 2.0,
            (komichi_matsu_gap(d) or {}).get("clear", 0.0))]
         if ((N.get("mado") or {}).get("komichi") or {}).get("pts") else
         ["窓の小径", "⛔ <b>置かない</b>【2026-09-03 ユーザー裁定8=A / 庭方 K188】 — "
                   "裁定7=B で窓が細まり、15%% を保つ線は折り返し5回・67.7m になって"
                   "<b>登山道に見える</b>。⭕ 窓は<b>芝だけの切れ込み</b>とし、崖を下りる道は"
                   "<b>南の余地の勝手の坂</b>へ一本化した"]),
        ["汀の杭列", "%s・径 %.2f〜%.2fm 不同・芯々 %.2f〜%.2fm 不等 → <b>汀線の実長 %.1fm "
                   "から 約 %d 本</b>"
         "(算出。⛔ 辺の長さを流用しない)／ 頭は水面+%.2f〜%.2f・根入れ %.1f以上・傾 ±%.0f°"
                   "／ 頭から %.2fm 下に**貫** %d段"
         % ((N.get("kuiretsu") or {}).get("kind", ""),
            (N.get("kuiretsu") or {}).get("dMin", 0), (N.get("kuiretsu") or {}).get("dMax", 0),
            (N.get("kuiretsu") or {}).get("pitchMin", 0), (N.get("kuiretsu") or {}).get("pitchMax", 0),
            migiwa_line(d)[1], _kui_n(d),
            (N.get("kuiretsu") or {}).get("topMin", 0), (N.get("kuiretsu") or {}).get("topMax", 0),
            (N.get("kuiretsu") or {}).get("neire", 0), (N.get("kuiretsu") or {}).get("tilt", 0),
            ((N.get("kuiretsu") or {}).get("nuki") or {}).get("below", 0),
            ((N.get("kuiretsu") or {}).get("nuki") or {}).get("n", 0))]
        if N.get("kuiretsu") else ["汀の杭列", "—"],
        ["柵の外", "堤 1:%.1f の土羽 ／ ヨシ 幅 %.1f〜%.1fm・水深 %+.1f〜%+.1f"
                 "(稈高 %.1f〜%.1fm)／ 蓮 汀から %.0f〜%.0fm"
         % ((N.get("tsutsumi") or {}).get("batter", 0),
            (N.get("tsutsumi") or {}).get("yoshi", {}).get("wMin", 0),
            (N.get("tsutsumi") or {}).get("yoshi", {}).get("wMax", 0),
            (N.get("tsutsumi") or {}).get("yoshi", {}).get("depthMin", 0),
            (N.get("tsutsumi") or {}).get("yoshi", {}).get("depthMax", 0),
            (N.get("tsutsumi") or {}).get("yoshi", {}).get("hMin", 0),
            (N.get("tsutsumi") or {}).get("yoshi", {}).get("hMax", 0),
            (N.get("tsutsumi") or {}).get("hasu", {}).get("fromM", 0),
            (N.get("tsutsumi") or {}).get("hasu", {}).get("toM", 0))],
    ]
    return _tw(["西の斜面と岸", "算出値を含む諸元"], [[a, b] for a, b in rows],
               "<b>本数・樹高・線形は庭方の設計、開き角・振れ・要る丈は算出値。</b>"
               "⛔ <b>灯籠・飛石・蹲踞は一つも置かない</b> — ここは庭ではなく<b>屋敷林と堀端</b>である。"
               "⛔ 柳・屋根の列・畑・馬場・水汲みの段・洗い場・船着も置かない。"
               "⛔ 堤を石垣にしない(切絵図は黒枠の無い無地の緑帯)。")


def migiwa_line(d):
    """**汀線**(堤の法尻=水面に接する線)の世界座標の折れ線と実長[m]。

    ⭐ 天端が u ごとに振れるので汀も振れる(2026-09-03 庭方=案A)。
      ⛔ 手でうねらせない・⛔ 辺の長さで代用しない。"""
    N9 = (d.get("nishi") or {})
    ts = N9.get("tsutsumi") or {}
    sk = N9.get("saku") or {}
    ml = ts.get("mizugiwaLine")
    e9 = sk.get("edge")
    if not ml or e9 is None:
        return [], 0.0
    P9 = d["polygon"]
    a9, b9 = P9[e9], P9[(e9 + 1) % len(P9)]
    nx9, nz9 = _inward(P9, e9)
    pts = []
    n9 = len(ml) - 1
    for i9, (_u9, off) in enumerate(ml):
        t9 = i9 / float(n9) if n9 else 0.0
        x9 = a9[0] + (b9[0] - a9[0]) * t9 - nx9 * off       # 沖(外)へ off[m]
        z9 = a9[1] + (b9[1] - a9[1]) * t9 - nz9 * off
        pts.append((x9, z9))
    L9 = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(pts, pts[1:]))
    return pts, L9


def _hojiri_grad(d):
    """**法尻の帯の勾配**(法尻から区画界へ下る%)。⛔ 本文に数を書かない(2026-09-03 検図4巡目)。"""
    N9 = d.get("nishi") or {}
    K9 = d["const"]["ken"]
    bd = next((b9 for b9 in (d.get("slopeBands") or []) if b9["name"].startswith("D")), None)
    if not bd:
        return "—"
    gs = []
    for u9 in (-24.0, -16.0, -8.0, 0.5, 8.0, 16.0):
        vs = [v9 for v9 in [q / 2.0 for q in range(int(2 * 140.0), int(2 * 168.0))]
              if in_parcel(d, u9, v9)]
        if len(vs) < 4:
            continue
        ya, yb = _dem_at(d, u9, vs[0]), _dem_at(d, u9, vs[-1])
        if ya is None or yb is None:
            continue
        L9 = (vs[-1] - vs[0]) * K9
        if L9 > 1e-6:
            gs.append(100.0 * (ya - yb) / L9)
    if not gs:
        return "—"
    return "%.1f〜%.1f%%" % (min(gs), max(gs))


def _kui_n(d):
    """汀の杭の本数。**汀線の実長と芯々からの従属値**(⛔ 人は書かない)。

    ⛔ 2026-09-03 まで**辺5の長さ 80.589m を流用**していた(庭方4巡目)。
      汀は堤の法面のぶん沖にあり、天端の振れで長さも変わるので辺では代用できない。"""
    ku = (d.get("nishi") or {}).get("kuiretsu")
    if not ku:
        return 0
    _p9, L9 = migiwa_line(d)
    if L9 <= 0:
        return 0
    p9 = (ku.get("pitchMin", 0.3) + ku.get("pitchMax", 0.4)) / 2.0
    return int(round(L9 / p9)) + 1


def _komichi_local(d):
    """窓の小径の **`stepWinKen` 間の窓で測った局所の勾配の最大**[%]と、その区間。

    ⛔ 脚の平均だけを刷らない(2026-09-03 庭方5巡目) — 上限に効くのはこちら。"""
    K9 = d["const"]["ken"]
    km = (((d.get("nishi") or {}).get("mado") or {}).get("komichi") or {})
    pts = [(a9, b9) for a9, b9 in (km.get("pts") or [])]
    win = km.get("stepWinKen", 2.0)
    best = (0.0, None)
    for a9, b9 in zip(pts, pts[1:]):
        Lk = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
        n9 = max(1, int(math.ceil(Lk / win)))
        for i9 in range(n9):
            p9 = (a9[0] + (b9[0] - a9[0]) * i9 / n9, a9[1] + (b9[1] - a9[1]) * i9 / n9)
            q9 = (a9[0] + (b9[0] - a9[0]) * (i9 + 1) / n9, a9[1] + (b9[1] - a9[1]) * (i9 + 1) / n9)
            ya, yb = _dem_at(d, p9[0], p9[1]), _dem_at(d, q9[0], q9[1])
            L9 = math.hypot(q9[0] - p9[0], q9[1] - p9[1]) * K9
            if ya is None or yb is None or L9 < 1e-6:
                continue
            g9 = 100.0 * abs(yb - ya) / L9
            if g9 > best[0]:
                best = (g9, (p9, q9))
    return best


def komichi_matsu_gap(d):
    """窓の小径と**手入れ松 P1** の離れ[m](幹の芯まで / 路の半幅を引いた実の隙)。

    ⭐ 庭方の意図: 小径は**P1 の袂を抜ける**(2026-09-03 庭方5巡目)。
      ⛔ 数を手で書かない — 折れ点と松の位置から毎回算出する。"""
    K9 = d["const"]["ken"]
    N9 = d.get("nishi") or {}
    km = ((N9.get("mado") or {}).get("komichi") or {})
    pts = [(a9, b9) for a9, b9 in (km.get("pts") or [])]
    m9 = next((q for q in ((N9.get("mado") or {}).get("matsu") or [])
               if q.get("name") == "P1"), None)
    if not m9 or len(pts) < 2:
        return None
    best = None
    for a9, b9 in zip(pts, pts[1:]):
        dx, dy = b9[0] - a9[0], b9[1] - a9[1]
        L2 = dx * dx + dy * dy or 1e-9
        t9 = max(0.0, min(1.0, ((m9["u"] - a9[0]) * dx + (m9["v"] - a9[1]) * dy) / L2))
        dd = math.hypot(m9["u"] - (a9[0] + dx * t9), m9["v"] - (a9[1] + dy * t9))
        best = dd if best is None else min(best, dd)
    return {"name": m9["name"], "ken": best, "m": best * K9,
            "clear": best * K9 - km.get("w", 0.9) / 2.0}


def _komichi_len(d):
    K = d["const"]["ken"]
    p9 = (((d.get("nishi") or {}).get("mado") or {}).get("komichi") or {}).get("pts") or []
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p9, p9[1:])) * K


def _komichi_grad(d):
    K = d["const"]["ken"]
    p9 = (((d.get("nishi") or {}).get("mado") or {}).get("komichi") or {}).get("pts") or []
    g9 = 0.0
    for a, b in zip(p9, p9[1:]):
        ya, yb = _dem_at(d, a[0], a[1]), _dem_at(d, b[0], b[1])
        L9 = math.hypot(b[0] - a[0], b[1] - a[1]) * K
        if ya is not None and yb is not None and L9 > 1e-6:
            g9 = max(g9, 100.0 * abs(yb - ya) / L9)
    return g9


def _edge_wave(hy):
    eg = [(a, b) for a, b in (hy.get("edge") or [])]
    if len(eg) < 3:
        return 0.0
    n9 = len(eg)
    mu = sum(q[0] for q in eg) / n9; mv = sum(q[1] for q in eg) / n9
    sxx = sum((q[0] - mu) ** 2 for q in eg) or 1e-9
    sl = sum((q[0] - mu) * (q[1] - mv) for q in eg) / sxx
    return max(abs(q[1] - (mv + sl * (q[0] - mu))) for q in eg)


def plate(h, num, title, meta=""):
    meta = inline(meta) if meta else meta
    h.append('<div class="plate"><div class="phead"><h2>%s　%s</h2>%s</div>'
             % (num, title, ('<span class="meta">%s</span>' % meta) if meta else ""))


def fig(h, svg, cap=None, legend=None):
    h.append('<div class="fig">%s</div>' % svg)
    if legend:
        h.append('<div class="legend">%s</div>' % legend)
    if cap:
        h.append('<p class="cap">%s</p>' % cap)


# ---------------------------------------------------------------- 生成器が正典へ書き戻す欄
# ⚠ **「その物が在ること」は入力、「その寸法」が出力。** 両方消すと生成器が処理を飛ばして
#   偽陽性になる(辺の別・断面の切り位置・run の存在は入力側)。
# ⛔ ここに挙げた欄は**人が json へ書かない**。書いても次の組み立てで上書きされる。
GEN_FIELDS = {
    "sections": ("natural",),          # 断面の現地形線 — 復元地盤から毎回引き直す
    "terraces": ("keeps",),
    "terraceWalls": ("pts", "a", "b", "drop", "len"),   # 壁の線と落差 — 天端の等高線から毎回引く            # 抜きの中で面を残す区画 — 棟の足跡から毎回算出する
    "gardens": ("rects", "polys"),
    "slopeBands": ("y0", "y1"),        # 帯の境 — `y0From`/`y1From` から毎回引く     # 庭の実形 — 割り当ての矩形から棟と上位の庭を引いて出す
}
# 門の開口に接する run の端だけは、開口の幅から決まる**従属値**。
# ⛔ 全部の s0/s1 を消すと run の位置そのものが消えるので、**開口側の端だけ**を検査する。
GEN_FIELDS_GATE = ("s0", "s1")

# **入れ子の中の算出値**。⛔ 2026-09-02 検図: 西の地盤を起こし直したのに、そこから出るはずの
#   従属値が**手書きのまま往復試験の網の外**にあった(窓の樹高の上限・木戸の敷居・眼高・堤の天端)。
#   ⚠ とくに窓の樹高の上限は `nishi_check` の**物差し**なので、
#   **古いと壊れていても鳴らない**(壊すと鳴ることと、物差しが正しいことは別)。
# `*` は並びの全要素。⛔ ここに挙げた欄は**人が json へ書かない**。
GEN_PATHS = [
    "nishi.mado.hLimit", "nishi.mado.crest", "nishi.mado.crestKind", "nishi.mado.seeFromM",
    "nishi.mado.eye.eyeY", "nishi.mado.susuki.vMax",
    "nishi.mado.matsu.*.h", "nishi.mado.matsu.*.hCap",
    "gardens.*.mikoro.*.eyeY",
    "gardens.*.shakkei.railU0", "gardens.*.shakkei.railU1",
    "nishi.saku.kido.groundY",
    "nishi.tsutsumi.y0", "nishi.tsutsumi.y0Range", "nishi.tsutsumi.y1",
    "nishi.tsutsumi.y0Line", "nishi.tsutsumi.y0Mean", "nishi.tsutsumi.mizugiwaLine",
    "nishi.tsutsumi.yoshiBottom", "nishi.tsutsumi.mizugiwaM",
    "nishi.mikoro.*.eyeY",
    "gardens.*.nakajima.*.u", "gardens.*.nakajima.*.v",
    "gardens.*.sawatobi.*.stonePts",
    "ramps.*.measured", "ramps.*.len", "ramps.*.rise", "ramps.*.earth",
    # ⛔ `ramps.*.prof` は入れない — 北東の坂の路盤は**入力**(設計した高さ)で、
    #   剥がすと組み直せない。⭕ 脚長と勾配の欄だけは毎回引き直している。

    "gardens.*.mizu.gensen.chokusetsu.m2",
]


def _gp_walk(o, parts):
    """`GEN_PATHS` の1本を辿って (親, 鍵) の並びを返す。`*` は並びの全要素。"""
    if not parts:
        return []
    k = parts[0]
    if k == "*":
        out = []
        for it in (o or []):
            out += _gp_walk(it, parts[1:])
        return out
    if not isinstance(o, dict) or k not in o:
        return []
    if len(parts) == 1:
        return [(o, k)]
    return _gp_walk(o[k], parts[1:])


GP_DEAD = []


def _gp_strip(x):
    """`GEN_PATHS` の欄を剥がす。⛔ **解決先0件のパスは `GP_DEAD` に積む**(検査が拾う)。

    ⚠ 2026-09-03 検図5巡目 K255: print 止まりだったので、html の往復試験は 0件 と刷っていた
      (K181 の直しが**報告経路まで届いていなかった**)。"""
    del GP_DEAD[:]
    for p9 in GEN_PATHS:
        got = _gp_walk(x, p9.split("."))
        if not got:
            GP_DEAD.append(p9)
        for par, k in got:
            par.pop(k, None)


def _gp_pairs(a, b):
    """正典と組み直しの (path, 正典値, 組み直し値) の並び。"""
    out = []
    for p9 in GEN_PATHS:
        va = [par[k] for par, k in _gp_walk(a, p9.split("."))]
        vb = [par[k] for par, k in _gp_walk(b, p9.split("."))]
        if len(va) != len(vb):
            out.append((p9, "%d 個" % len(va), "%d 個" % len(vb)))
            continue
        for qa, qb in zip(va, vb):
            out.append((p9, qa, qb))
    return out


def fix_gate_runs(x):
    """**門の開口に接する run の端を、門から引き直す。**
    2026-09-01 六巡目: 番所の幅を 1.5間へ直した拍子に桁行が 16.360→16.362 になり、
    静的に持っていた両袖の s(6.19 / 22.55)が 0.001m ずつ食い込んで重なりが2件出た。
    ⛔ 端を動かして従属値を引き直さない型の再発。開口の両端は毎回ここで算出する。"""
    ge9, gs9 = x["gate"]["edge"], x["gate"]["s"]
    half9 = x["gate"]["plan"]["monW"] / 2.0
    for r9 in x["runs"]:
        if r9.get("edge") != ge9:
            continue
        if abs(r9["s1"] - (gs9 - half9)) < 0.20:
            r9["s1"] = round(gs9 - half9, 3)
        if abs(r9["s0"] - (gs9 + half9)) < 0.20:
            r9["s0"] = round(gs9 + half9, 3)
    return x


def _rect_sub(r, c):
    """矩形 r から矩形 c を引く(軸平行なので最大4枚の矩形になる)。"""
    a0, b0, a1, b1 = r
    c0, d0, c1, d1 = c
    if c1 <= a0 + 1e-9 or c0 >= a1 - 1e-9 or d1 <= b0 + 1e-9 or d0 >= b1 - 1e-9:
        return [r]
    out = []
    if d0 > b0 + 1e-9:
        out.append((a0, b0, a1, min(b1, d0)))
    if d1 < b1 - 1e-9:
        out.append((a0, max(b0, d1), a1, b1))
    m0, m1 = max(b0, d0), min(b1, d1)
    if m1 - m0 > 1e-9:
        if c0 > a0 + 1e-9:
            out.append((a0, m0, min(a1, c0), m1))
        if c1 < a1 - 1e-9:
            out.append((max(a0, c1), m0, a1, m1))
    return [q for q in out if q[2] - q[0] > 1e-9 and q[3] - q[1] > 1e-9]


def fix_garden_geom(x):
    """**庭の実形を算出する。**json が持つのは §4 の「割り当ての矩形」だけで、
    図に出る形はそこから機械で導く:

    ① **棟・付属屋・渡廊下の足跡(+犬走り)を引く** — 庭は「建屋と囲いの間に**残る面**」。
    ② 残った矩形を `clip`(`shumen`=段の外輪 / `parcel`=区画)で切って `polys` にする。

    ⭐ **2026-09-02: 「§4 の並び順で上位が取る」暫定規則は撤去した。**庭方が境界を引き直し、
      割り当ての矩形どうしの重なりが 0 になったので不要になった(`garden_alloc_check` が見張る)。

    ⛔ `rects`/`polys` は人が書かない(GEN_FIELDS)。棟や段を動かせば毎回引き直る。"""
    cut = [(o["u0"], o["v0"], o["u1"], o["v1"])
           for o in x["munes"] + x["service"] + x["links"]]
    sh = next((t for t in x["terraces"] if t["name"] == "Shumen"), None)
    gr = RGrid(x)
    par = [gr.L(a, b) for a, b in x["polygon"]]
    for g in x["gardens"]:
        rs = [(g["u0"], g["v0"], g["u1"], g["v1"])]
        for c in cut:
            nxt = []
            for r in rs:
                nxt += _rect_sub(r, c)
            rs = nxt
        g["rects"] = [[round(q, 4) for q in r] for r in rs]
        win = tpoly(sh) if g.get("clip") == "shumen" else par
        polys = []
        for r in rs:
            ring = clip_ring(win, [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])])
            if len(ring) >= 3 and _ring_area(ring) > 1e-6:
                polys.append([[round(a, 3), round(b, 3)] for a, b in ring])
        g["polys"] = polys
    return x


def fix_nishi(x):
    """**西の斜面と岸の従属値を、江戸期の復元地盤と水面から引き直す。**

    ⛔ **手書きにしない。**2026-09-02 検図: 西の地盤を起こし直したのに、そこから出るはずの値
      (窓の樹高の上限・木戸の敷居・眼高・堤の天端・帯の境)が**手書きのまま往復試験の網の外**にあった。
      ⚠ とくに `mado.hLimit` は `nishi_check` ①**の物差し**なので、表が古いと
      **壊れていても鳴らない**(壊すと鳴ることと、物差しが正しいことは別)。
    ⭕ 生成順: 堤の天端(辺5の実測地盤)→ 葭の上下端(水面と水深の窓)→ 帯の境 →
      木戸の敷居 → 眼高 → 小径の終点 → 窓の樹高の上限。"""
    N = x.get("nishi")
    if not N:
        return x
    K = x["const"]["ken"]
    _dem_at(x, 0, 0)
    gr = RGrid(x)
    ts = N.get("tsutsumi") or {}
    sk = N.get("saku") or {}
    # ① 堤の天端 = 柵の載る辺(区画界)の実測地盤。⚠ 単一の値で持たない — u ごとに振れる。
    e9 = sk.get("edge")
    gs = []
    if e9 is not None:
        P9 = x["polygon"]
        a9, b9 = P9[e9], P9[(e9 + 1) % len(P9)]
        # ⛔ **区画線のすぐ内側を読まない**(2026-09-03 検図4巡目)。
        #   ⚠ 辺5は `edgeClip` を外したので、線の上で復元(11.1)と正本(8.6)が直に段になる。
        #     0.3間 内側は双一次がその段を跨ぐ帯で、10.05〜11.13 の鋸歯(±0.5m)が出ていた。
        #   ⭕ **2.0間 内側**を読む(11.10〜11.20 のほぼ水平)。
        #   ⛔ **両隅の3間は数えない** — そこは辺4・辺6 の `edgeClip` 帯で、
        #     隣家との協定で正本(8.56/9.15)に寄せてあるので堤の天端ではない。
        #   ⭕ **u ごとの線**でも持つ(2026-09-03 庭方=案A / 検図4巡目の重い5) —
        #     単一値で帯D/Eの境を引くと、堀端の94坪がどの帯にも属さなくなる。
        inw = ts.get("sampleInKen", 2.0)
        skipU = ts.get("cornerSkipKen", 3.52)
        n9 = 80
        LenKen = math.hypot(b9[0] - a9[0], b9[1] - a9[1]) / x["const"]["ken"]
        nx9, nz9 = _inward(P9, e9)                     # 区画の内側へ向く単位法線(世界)
        line = []
        for i9 in range(n9 + 1):
            t9 = i9 / float(n9)
            x9 = a9[0] + (b9[0] - a9[0]) * t9 + nx9 * inw * x["const"]["ken"]
            z9 = a9[1] + (b9[1] - a9[1]) * t9 + nz9 * inw * x["const"]["ken"]
            u9, v9 = gr.L(x9, z9)
            y9 = _dem_at(x, u9, v9)
            if y9 is None:
                continue
            line.append([round(u9, 2), round(y9, 2)])
            if LenKen * t9 >= skipU and LenKen * (1.0 - t9) >= skipU:
                gs.append(y9)                          # ⭕ 代表値は**中央だけ**から出す
        if line:
            ts["y0Line"] = line
    if gs:
        ts["y0Range"] = [round(min(gs), 2), round(max(gs), 2)]
        ts["y0"] = round(sum(gs) / len(gs), 2)
        if ts.get("y0Line"):
            ts["y0Mean"] = round(sum(q[1] for q in ts["y0Line"]) / len(ts["y0Line"]), 2)
    wy = ts.get("waterY", 6.60)
    ys = ts.get("yoshi") or {}
    ts["y1"] = round(wy - ys.get("depthMin", -0.3), 2)          # 葭の上端
    ts["yoshiBottom"] = round(wy - ys.get("depthMax", 0.3), 2)  # 葭の下端
    if ts.get("y0") is not None and ts.get("batter"):
        # ⛔ **汀は「水面まで」**(2026-09-03 考証 K150)。葭の上端(`y1`)までではない。
        ts["mizugiwaM"] = round((ts["y0"] - wy) * ts["batter"], 2)
        # ⭐ **u ごとの線でも持つ**(2026-09-03 庭方=案A) — 天端が u で振れるので汀も振れる。
        #   ⛔ 手でうねらせない。⛔ 単一値だけで帯の境を引かない(検図4巡目の重い5)。
        if ts.get("y0Line"):
            ts["mizugiwaLine"] = [[q[0], round((q[1] - wy) * ts["batter"], 2)]
                                  for q in ts["y0Line"]]
    # ② 帯の境 — `y0From`/`y1From` が数なら設計値、記号なら算出値
    py = max(t["y"] for t in x["terraces"])
    # ⭕ **法尻の平坦帯の上端**は、裁定6=B の余地の枠(`nishi.yochi`)の上の辺の実地盤から出す
    #   (2026-09-03 考証 K190)。⛔ 手で書かない — 枠を動かせば帯の境も動く。
    yt = None
    ys7 = []
    for a7 in ((N.get("yochi") or {}).get("areas") or []):
        u7 = a7["u0"]
        while u7 <= a7["u1"] + 1e-9:
            q7 = _dem_at(x, u7, a7["v0"])
            if q7 is not None:
                ys7.append(q7)
            u7 += 0.5
    if ys7:
        yt = round(sum(ys7) / len(ys7), 2)
    SRC = {"plateau": round(py - 0.1, 2), "tsutsumiTop": ts.get("y0"),
           "yochiTop": yt,
           "yoshiTop": ts.get("y1"), "yoshiBottom": ts.get("yoshiBottom")}
    for b in x.get("slopeBands", []):
        if b.get("kind") == "水面":
            b.pop("y0", None); b.pop("y1", None)
            continue
        for k9, f9 in (("y0", "y0From"), ("y1", "y1From")):
            v9 = b.get(f9)
            b[k9] = SRC.get(v9) if isinstance(v9, str) else v9
    # ③ 木戸の敷居と眼高
    kd = sk.get("kido") or {}
    if kd:
        g9 = _dem_at(x, kd["u"], kd["v"])
        if g9 is not None:
            kd["groundY"] = round(g9, 2)
    for m9 in (N.get("mikoro") or []):
        g9 = _dem_at(x, m9["u"], m9["v"])
        if g9 is not None:
            m9["eyeY"] = round(g9 + eye_above(x, m9.get("eyeMode", "stand")), 2)
    # ③' 庭の見所の眼高。⭐ **`eyeAbove` があれば「その点の江戸期地盤 + それ」の従属値**、
    #     無ければ `eyeYFix`(入側の床の高さから作った入力)。
    #     ⚠ 2026-09-03 庭方4巡目: 見晴らしの台(見所⑨)は**床几の座視 1.23** で確定。
    #       ⛔ 立位 1.55 で取らない(台は床几と毛氈を出す場所)。座視のほうが眼が低く安全側。
    for g8 in x.get("gardens", []):
        for m8 in (g8.get("mikoro") or []):
            md8 = m8.get("eyeMode")
            bs8 = m8.get("eyeBase")
            if md8 and bs8:
                # 屋外の見所 — 立つ物の天端から。⛔ 眼高を直に書かない(K147)
                y8 = None
                if bs8.get("kind") == "sawatobi":
                    o8 = next((q for q in (g8.get("sawatobi") or [])
                               if q["name"] == bs8.get("name")), None)
                    y8 = o8.get("topY") if o8 else None
                elif bs8.get("kind") == "tsukiyama":
                    o8 = next((q for q in (g8.get("tsukiyama") or [])
                               if q["name"] == bs8.get("name")), None)
                    if o8:
                        t9 = next((q for q in x["terraces"]
                                   if sashizu_lib.t_contains(q, o8["u"], o8["v"])), None)
                        foot = t9["y"] if t9 else _dem_at(x, o8["u"], o8["v"])
                        if foot is not None:
                            y8 = foot + (o8["topY"] - foot) * bs8.get("frac", 0.5)
                elif bs8.get("kind") == "water":
                    mg8 = (g8.get("migiwa") or {})
                    if mg8.get("waterY") is not None:
                        y8 = mg8["waterY"] + bs8.get("offset", 0.0)
                if y8 is not None:
                    m8["eyeY"] = round(y8 + eye_above(x, md8), 2)
            elif md8 and m8.get("eyeOn"):
                # 入側の眼 = 段の面 + 御殿の床 + 身長×比
                t8 = next((q for q in x["terraces"] if q["name"] == m8["eyeOn"]), None)
                if t8:
                    m8["eyeY"] = round(t8["y"] + x["const"]["gotenFloor"]
                                       + eye_above(x, md8), 2)
            elif md8:
                gg8 = _dem_at(x, m8["u"], m8["v"])
                if gg8 is not None:
                    m8["eyeY"] = round(gg8 + eye_above(x, md8), 2)
            elif m8.get("eyeYFix") is not None:
                m8["eyeY"] = m8["eyeYFix"]
    # ③'' 四つ目垣に落とす区間【2026-09-03 庭方 K210】
    #   ⭕ **扇の上端を「柵の v」へ外挿し、左右に `railClearKen` を足した幅**。
    #   ⛔ 手で持たない — 2026-09-03 まで `railU0/railU1` は**どこからも読まれない死値**だった。
    #   ⚠ 扇は v で開くので、柵の立つ v(其十八の竹垣の線)まで伸ばしてから幅を取る。
    md7 = N.get("mado") or {}
    fan7 = md7.get("fan") or []
    for g7 in x.get("gardens", []):
        sk7 = g7.get("shakkei")
        if not sk7 or not fan7:
            continue
        vr7 = rail_v_at(x, (md7.get("eye") or {}).get("u", 0.0))
        if vr7 is None:
            vr7 = fan7[0][0]
        lo7, hi7 = fan_at_v(fan7, vr7)
        cen7 = md7.get("fanCenter")
        if cen7 is not None:                       # ⭕ 芯の宣言があれば芯まわりで対称に取る
            hw7 = max(hi7 - cen7, cen7 - lo7)
            lo7, hi7 = cen7 - hw7, cen7 + hw7
        cl7 = sk7.get("railClearKen", 0.6)
        sk7["railU0"] = round(lo7 - cl7, 2)
        sk7["railU1"] = round(hi7 + cl7, 2)
        sk7["railV"] = round(vr7, 2)
    # ④ 小径の終点は木戸(⛔ 二重持ちをやめた)
    km = (N.get("mado") or {}).get("komichi") or {}
    if km.get("endAtKido") and kd:
        km["endPt"] = [kd["u"], kd["v"]]
    # ⑤ 窓の樹高の上限 — **床几の眼から手前の高まりを掠める線** − 地盤 − 余裕
    #    ⛔ 汀の水面へ直に引いた線では、帯に隠れる区間で上限が負になって意味を成さない。
    md = N.get("mado") or {}
    ey = md.get("eye")
    if ey:
        g9 = _dem_at(x, ey["u"], ey["v"])
        if g9 is not None:
            ey["eyeY"] = round(g9 + eye_above(x, ey.get("eyeMode", "shogi")), 2)
    if ey and ey.get("eyeY") is not None and md.get("hLimitV"):
        lim = None                                   # 視線を最も切る所(手前の高まり)
        v9 = ey["v"] + 1.0
        while v9 < 200.0:
            if in_parcel(x, ey["u"], v9):
                y9 = _dem_at(x, ey["u"], v9)
                if y9 is not None:
                    m9 = (y9 - ey["eyeY"]) / ((v9 - ey["v"]) * K)
                    if lim is None or m9 > lim[0]:
                        lim = (m9, v9, y9)
            v9 += 0.5
        # ⭐ **汀の柵(h1.4)も遮る物に入れる**(2026-09-03 庭方4巡目)。
        #   ⛔ 地盤だけで探すと、区画界に立つ柵が抜け落ちて上限が低く出る
        #     (庭方の実測 5.67m 対 当図 4.60m。差 1.07m は柵の丈がそのまま効いていた)。
        #   ⭕ 借景の遮蔽(`shakkei`)は K114 で柵を入れてある。同じ物差しへ揃える。
        sk8 = N.get("saku") or {}
        if sk8.get("h"):
            vq8 = ey["v"] + 1.0
            vlast = None
            while vq8 < 200.0:
                if in_parcel(x, ey["u"], vq8):
                    vlast = vq8
                vq8 += 0.05
            if vlast is not None:
                y8 = _dem_at(x, ey["u"], vlast)
                if y8 is not None:
                    m8 = (y8 + sk8["h"] - ey["eyeY"]) / ((vlast - ey["v"]) * K)
                    if lim is None or m8 > lim[0]:
                        lim = (m8, vlast, y8 + sk8["h"])
                        md["crestKind"] = "汀の柵の天端(地盤 %.2f + 柵 %.1f)" % (y8, sk8["h"])
        if lim:
            md.setdefault("crestKind", "地盤の高まり")
            md["crest"] = [round(lim[1], 2), round(lim[2], 2)]
            md["seeFromM"] = round((wy - ey["eyeY"]) / lim[0], 1) if lim[0] < 0 else None
            out = []
            for v9 in md["hLimitV"]:
                g9 = _dem_at(x, ey["u"], v9)
                if g9 is None:
                    continue
                ray = ey["eyeY"] + lim[0] * (v9 - ey["v"]) * K
                out.append([v9, round(max(0.0, ray - g9 - md.get("clearance", 1.0)), 2)])
            md["hLimit"] = out
        # ⭐ **窓の松の丈は「その点の上限 − `hBelowLimit`」の従属値**(2026-09-03 庭方4巡目)。
        #   ⛔ 固定値で持つと、大棟や柵の丈・地盤が動いたときに追随せず、
        #     検査だけが鳴る(あるいは黙る)状態になる。⭕ 扇の外の松は `hFix`(入力)。
        for m8 in (md.get("matsu") or []):
            if m8.get("hDesign") is not None:
                lm8 = mado_hlimit(x, m8["v"], m8["u"])
                cap8 = (lm8 - md.get("matsuMargin", 1.0)) if lm8 is not None else None
                m8["h"] = round(m8["hDesign"] if cap8 is None
                                else max(0.0, min(m8["hDesign"], cap8)), 2)
                m8["hCap"] = None if cap8 is None else round(cap8, 2)
            elif m8.get("hFix") is not None:
                m8["h"] = m8["hFix"]
                m8["hCap"] = None          # ⭕ 欄を必ず持たせる(GEN_PATHS の * は在るものだけ回る)
        su = md.get("susuki") or {}
        if su.get("hMax") and md.get("hLimit"):
            ok9 = [q[0] for q in md["hLimit"] if q[1] >= su["hMax"]]
            su["vMax"] = round(max(ok9), 2) if ok9 else None
    return x


def _edge_v(x, e9, u9):
    """辺 `e9` が u=`u9` を横切る v。柵の線の位置を u ごとに引く。"""
    gr = RGrid(x)
    P9 = x["polygon"]
    a9 = gr.L(*P9[e9]); b9 = gr.L(*P9[(e9 + 1) % len(P9)])
    if abs(b9[0] - a9[0]) < 1e-9:
        return a9[1]
    t9 = (u9 - a9[0]) / (b9[0] - a9[0])
    return a9[1] + (b9[1] - a9[1]) * t9


def fix_terrace_walls(x):
    """**土留めの線 `pts` と実測落差 `drop` を算出して書き戻す。**

    ⭐ 壁は**天端の等高線**に立つ(`unity-modular-stonewall` §3: 天端は丸い数字で一直線)。
      線は「段の縁から外へ進んで、法面の高さが天端まで下がる点」の並びで、
      ⛔ 人が書くと段や法面の勾配を動かした瞬間に腐る。
    `drop` は [最小, 最大] の露出(天端 − 江戸期の復元地盤)。`wall_check` がこれで丈を検算する。"""
    K = x["const"]["ken"]
    bf = x["const"].get("batterFill", 1.5)
    _dem_at(x, 0, 0)
    for w in x.get("terraceWalls", []):
        sp = w.get("span")
        t = next((y for y in x["terraces"] if y["name"] == w.get("terrace")), None)
        if not sp or t is None:
            continue
        pts, hs = [], []
        q = min(sp["from"], sp["to"])
        while q <= max(sp["from"], sp["to"]) + 1e-9:
            v = sp.get("vFrom", 0.0)
            hit = None
            while v < sp.get("vFrom", 0.0) + 20.0:
                uu, vv = (q, v) if sp.get("axis") == "u" else (v, q)
                if not tin(t, uu, vv):
                    dm = sashizu_lib.t_edge_dist(t, uu, vv) * K
                    if t["y"] - dm / bf <= w["coping"]:
                        hit = (uu, vv)
                        break
                v += 0.05
            if hit:
                g = _dem_at(x, hit[0], hit[1])
                if g is not None:
                    pts.append([round(hit[0], 2), round(hit[1], 3)])
                    hs.append(w["coping"] - g)
            q += 0.5
        if pts:
            w["pts"] = pts
            w["a"] = pts[0]
            w["b"] = pts[-1]
            w["drop"] = [round(min(hs), 2), round(max(hs), 2)]
            w["len"] = round(sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                                 for i in range(len(pts) - 1)) * K, 1)
    return x


def fix_terrace_keeps(x):
    """**抜き(平坦化しない区画)の中でも、棟が載る所だけは面を残す。**
    2026-09-02 ユーザー裁定「主面の5区画を平坦化しない。**棟が載る所だけ 24.80**」の
    但し書きを、棟・付属屋・渡廊下の足跡(+犬走り)から機械で当てる。
    ⛔ 人が json に矩形を書き足さない — 棟を動かした瞬間に腐る
    (家臣長屋 KN_Sh1 が南西の樹林の抜きの中に入っている。手で書けば必ず取り残す)。"""
    ib = x["const"]["inubashiri"] / x["const"]["ken"]
    for t9 in x["terraces"]:
        hs = t9.get("holes") or []
        if not hs:
            t9.pop("keeps", None)
            continue
        keeps = []
        for o9 in x["munes"] + x["service"] + x["links"]:
            if abs(o9.get("y", -999) - t9["y"]) > 0.05:
                continue
            a9 = [round(o9["u0"] - ib, 4), round(o9["v0"] - ib, 4),
                  round(o9["u1"] + ib, 4), round(o9["v1"] + ib, 4)]
            if not any(a9[0] < max(q[0] for q in h9["poly"]) and a9[2] > min(q[0] for q in h9["poly"])
                       and a9[1] < max(q[1] for q in h9["poly"]) and a9[3] > min(q[1] for q in h9["poly"])
                       for h9 in hs):
                continue
            keeps.append([[a9[0], a9[1]], [a9[2], a9[1]], [a9[2], a9[3]], [a9[0], a9[3]]])
        t9["keeps"] = keeps
    return x


def fix_edge_profile(x):
    """**外周の地盤を毎回取り直して書き戻す。** 2026-08-26 土井 EDO-0024 の警告
    (「境界は正本で測る」が復元の箱の位置でたまたま成り立っているだけだと、箱が動いた瞬間に
     黙って追随しなくなる)を当家に当てたら、`edgeProfile` が json に静的で
    **いまの復元地盤と最大 5.86m ずれていた**(2026-08-23 の値のまま12巡通っていた)。
    run の天端・基壇の露出・展開図の地盤線・断面の足元がすべてこれを読む。"""
    # ⛔ **区画内の地盤は `_dem_at`(区画でクリップした復元地盤)に一本化**する
    #   (2026-09-03 検図4巡目)。⚠ ここは `_world_at` で**線の上**を読んでいたため、
    #     区画の外のセルが混ざって辺5が 8.54〜10.80 の鋸歯になっていた
    #     (同じ点を其十二は 11.11 と読む。区画内4000点で最大差 1.009m)。
    #   ⭕ 線の上ではなく **`edgeInKen` 間だけ内側**を読む。段の際の双一次を跨がない。
    _dem_at(x, 0, 0)
    P9 = x["polygon"]
    gr9 = RGrid(x)
    # ⛔ **内寄せの物差しを二つ持たない**(2026-09-03 検図5巡目 K254) —
    #   `edge_datum_table` は堤の天端と同じ `sampleInKen`(2.0間・辺の法線)で読む。
    #   ⭕ ここも同じ値・同じ向き(辺の法線)に揃える。
    inw = ((x.get("nishi") or {}).get("tsutsumi") or {}).get("sampleInKen",
                                                             x["const"].get("edgeInKen", 1.0))
    ep = {}
    cu, cv = 0.0, 0.0
    for p9 in P9:
        q9 = gr9.L(p9[0], p9[1]); cu += q9[0] / len(P9); cv += q9[1] / len(P9)
    for i9 in range(len(P9)):
        a9, b9 = P9[i9], P9[(i9 + 1) % len(P9)]
        L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
        pr9 = []
        s9 = 0.0
        while s9 <= L9 + 1e-9:
            t9 = (s9 / L9) if L9 else 0.0
            x9 = a9[0] + (b9[0] - a9[0]) * t9
            z9 = a9[1] + (b9[1] - a9[1]) * t9
            u9, v9 = gr9.L(x9, z9)
            if i9 in set(x["const"].get("edgeInEdges") or []):
                # ⛔ **内側へ寄せて読むのは「クリップを外した辺」だけ。**
                #   ⚠ 他の辺は区画線の上が隣家との協定で正本に一致しており、
                #     外周の塀・基壇はその高さに載っている。内側へ寄せると協定が破れる
                #     (2026-09-03: 全辺へ当てたら塀の天端の指摘が 0 → 32件 出た)。
                # ⭕ **辺の法線**で内へ入る(⛔ 重心方向にしない=辺ごとに向きが揺れる)
                nx8, nz8 = _inward(P9, i9)
                q8 = gr9.L(x9 + nx8 * inw * x["const"]["ken"],
                           z9 + nz8 * inw * x["const"]["ken"])
                y9 = _dem_at(x, q8[0], q8[1])
                if y9 is None:
                    y9 = _dem_at(x, u9, v9)
            else:
                # ⭕ 隣家のある辺は**線の上の正本**をそのまま読む(協定の面)。
                y9 = _world_at(x, u9, v9)
            if y9 is not None:
                pr9.append([round(s9, 1), round(y9, 2)])
            s9 += 4.0
        if pr9:
            ep[str(i9)] = pr9
    if ep:
        x["edgeProfile"] = ep
    return x


def fix_sections(x):
    """断面の現地形線を江戸期の復元地盤から引き直す。
    ⚠ 2026-08-24 検図: 静的な `natural` と生成器の DEM が別々の値を持ち、崖の肩で 0.72m
      食い違っていた。**同じ地形の二系統を残さない。**"""
    for sec9 in x["sections"]:
        nat9 = []
        f9, t9 = _sec_span(x, sec9)
        w9 = f9
        while w9 <= t9 + 1e-9:
            u9, v9 = (sec9["at"], w9) if sec9["axis"] == "u" else (w9, sec9["at"])
            y9 = _dem_at(x, u9, v9)
            if y9 is not None:
                nat9.append([round(w9, 2), round(y9, 2)])
            w9 += 1.5
        if nat9:
            sec9["natural"] = nat9
    return x


def fix_naka(x):
    """**中島の芯を輪郭の重心から引く。**

    ⚠ 2026-09-02 庭方3巡目で中島が楕円(芯+径)から**7点の不等辺の輪郭**へ変わった。
      芯 `u`/`v` は輪郭から出る**従属値**で、⛔ 人が別に書くと図(点景の表・平面)と
      検査(池の中か)が**別の島を見る**。輪郭を動かしたら芯も動く形にする。"""
    for g9 in x.get("gardens", []):
        for nj in (g9.get("nakajima") or []):
            pl = [(a9, b9) for a9, b9 in (nj.get("poly") or [])]
            if len(pl) < 3:
                continue
            a2 = cu = cv = 0.0
            for (ua, va), (ub, vb) in zip(pl, pl[1:] + pl[:1]):
                cr = ua * vb - ub * va
                a2 += cr; cu += (ua + ub) * cr; cv += (va + vb) * cr
            if abs(a2) < 1e-9:
                continue
            nj["u"] = round(cu / (3.0 * a2), 3)
            nj["v"] = round(cv / (3.0 * a2), 3)
    return x


def fix_mizu(x):
    """**池面への直接雨の面積を、汀線から引き直す。**

    ⚠ 2026-09-02 庭方3巡目で「集水域の雨」と「池面への直接雨」を分けた。
      池面の面積は**汀線から出る従属値**で、⛔ 別に書くと汀線を動かしたとき片方だけ古くなる。"""
    for g9 in x.get("gardens", []):
        ck = ((g9.get("mizu") or {}).get("gensen") or {}).get("chokusetsu")
        if ck is None:
            continue
        try:
            ck["m2"] = round(pond_metrics(x)["areaM2"], 1)
        except Exception:
            pass
    return x


def fix_sawatobi(x):
    """**沢飛石の石の位置**を、庭方の折れ線の上に芯々を振って割り付ける。

    ⭐ 2026-09-03 庭方4巡目 K168: 芯々 0.683〜0.692(変動係数 0.5%)は**等間隔**で、
      長軸 0.70 では目地が −0.01m になり図で連続した堤に見えた。
      ⭕ 長軸の上限を 0.62 へ下げ、芯々に ±`pitchJitter` の振れを許す(⛔ 乱数は種を固定)。
    ⛔ 庭方の折れ線(`pts`)そのものは動かさない — その上での**割り付け**だけを作る。"""
    for g9 in x.get("gardens", []):
        for sw in (g9.get("sawatobi") or []):
            pts = [(a9, b9) for a9, b9 in (sw.get("pts") or [])]
            if len(pts) < 2:
                continue
            segs = [math.hypot(b9[0] - a9[0], b9[1] - a9[1]) for a9, b9 in zip(pts, pts[1:])]
            L9 = sum(segs)
            n9 = len(pts)
            base = L9 / float(n9 - 1)
            rnd = random.Random(sw.get("jitterSeed", 0))
            amp = sw.get("pitchJitter", 0.0) / max(x["const"]["ken"], 1e-9)
            dev = [rnd.uniform(-1.0, 1.0) for _ in range(n9 - 1)]
            mu = sum(dev) / len(dev)
            dev = [q - mu for q in dev]
            mx = max(abs(q) for q in dev) or 1.0
            dev = [q / mx * amp for q in dev]
            def _at(s8):
                """折れ線の弧長 s8 の点。⛔ 端では折れ線の端点そのものを返す。"""
                if s8 <= 0.0:
                    return list(pts[0])
                if s8 >= L9 - 1e-9:
                    return list(pts[-1])
                r8, i8 = s8, 0
                while i8 < len(segs) - 1 and r8 > segs[i8]:
                    r8 -= segs[i8]; i8 += 1
                a8, b8 = pts[i8], pts[i8 + 1]
                f8 = (r8 / segs[i8]) if segs[i8] > 1e-9 else 0.0
                return [a8[0] + (b8[0] - a8[0]) * f8, a8[1] + (b8[1] - a8[1]) * f8]
            out, s9 = [], 0.0
            for k9 in range(n9):
                q9 = _at(s9)
                out.append([round(q9[0], 3), round(q9[1], 3)])
                if k9 < n9 - 1:
                    s9 += base + dev[k9]
            sw["stonePts"] = out
    return x


def fix_ramps(x):
    """坂の路盤(`prof`)と実測(`measured`)を書き戻す。⛔ 人が書かない。

    ⭐ `profFrom: "uniform"` の坂は、**両端の地盤を一様勾配で結ぶ路盤**を起こす
      (2026-09-03 ユーザー裁定8=A の勝手の坂)。⛔ 途中の地盤なりにしない —
      地盤なりだと 27% の区間が出る。⭕ 一様にすると切盛が要るぶんは `earth` が出す。"""
    K9 = x["const"]["ken"]
    for rp in x.get("ramps", []):
        pts = [(a9, b9) for a9, b9 in (rp.get("pts") or [])]
        if rp.get("profFrom") == "ground" and len(pts) >= 2:
            # ⭕ **土の道は地盤なり**(2026-09-03 庭方5巡目 K205 の案EE)。
            ys = [_dem_at(x, q9[0], q9[1]) for q9 in pts]
            if None not in ys:
                ls = [math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K9
                      for a9, b9 in zip(pts, pts[1:])]
                prof = []
                for i9, q9 in enumerate(pts):
                    leg = ls[i9] if i9 < len(ls) else 0.0
                    gr = (100.0 * abs(ys[i9 + 1] - ys[i9]) / leg) if leg > 1e-9 else 0.0
                    prof.append([q9[0], q9[1], round(ys[i9], 2), round(leg, 1), round(gr, 1)])
                rp["prof"] = prof
        if rp.get("profFrom") == "uniform" and len(pts) >= 2:
            ys = [_dem_at(x, pts[0][0], pts[0][1]), _dem_at(x, pts[-1][0], pts[-1][1])]
            if None not in ys:
                ls = [math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K9
                      for a9, b9 in zip(pts, pts[1:])]
                L9 = sum(ls)
                gr = 100.0 * (ys[0] - ys[1]) / max(L9, 1e-9)
                prof, s9 = [], 0.0
                for i9, q9 in enumerate(pts):
                    y9 = ys[0] - (ys[0] - ys[1]) * (s9 / max(L9, 1e-9))
                    leg = ls[i9] if i9 < len(ls) else 0.0
                    prof.append([q9[0], q9[1], round(y9, 2), round(leg, 1),
                                 round(gr, 1) if i9 < len(ls) else 0.0])
                    if i9 < len(ls):
                        s9 += ls[i9]
                rp["prof"] = prof
        # ⭕ **`prof` の脚長と勾配の欄は従属値**(⛔ 手で持たない) — 点を動かしたら引き直す。
        #   ⚠ 2026-09-03: 1脚目を併合したとき、この2欄が古いままだと表が嘘をつく。
        pr9 = rp.get("prof")
        if pr9 and len(pr9) == len(pts):
            for i9 in range(len(pr9)):
                if i9 < len(pr9) - 1:
                    L8 = math.hypot(pr9[i9 + 1][0] - pr9[i9][0],
                                    pr9[i9 + 1][1] - pr9[i9][1]) * K9
                    dz8 = abs(pr9[i9 + 1][2] - pr9[i9][2])
                    pr9[i9][3] = round(L8, 1)
                    pr9[i9][4] = round(100.0 * dz8 / max(L8, 1e-9), 1)
                else:
                    pr9[i9][3] = 0
                    pr9[i9][4] = 0
        # 切盛(路盤 − 地盤)を帯の全幅で積む
        if pr9:
            w9 = rp.get("w", K9)
            cut = fill = 0.0
            cmax = fmax = 0.0
            for (a9, b9) in zip(pr9, pr9[1:]):
                n9 = max(1, int(math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K9 / 1.0))
                for k9 in range(n9):
                    f9 = (k9 + 0.5) / n9
                    u8 = a9[0] + (b9[0] - a9[0]) * f9
                    v8 = a9[1] + (b9[1] - a9[1]) * f9
                    y8 = a9[2] + (b9[2] - a9[2]) * f9
                    g8 = _dem_at(x, u8, v8)
                    if g8 is None:
                        continue
                    dz = y8 - g8
                    seg = math.hypot(b9[0] - a9[0], b9[1] - a9[1]) * K9 / n9
                    if dz < 0:
                        cut += -dz * seg * w9; cmax = max(cmax, -dz)
                    else:
                        fill += dz * seg * w9; fmax = max(fmax, dz)
            rp["earth"] = {"kiridoM3": int(round(cut)), "kiridoMax": round(cmax, 2),
                           "moridoM3": int(round(fill)), "moridoMax": round(fmax, 2),
                           "_": "坂の路盤(幅 %.3fm)を江戸期地盤へ摺り付ける土工。**帯の全幅で積算**。"
                                "拝領時造成には含めない" % w9}
        m9 = ramp_metrics(x, rp)
        if m9:
            rp["measured"] = m9
            rp["len"] = m9["len"]
            rp["rise"] = m9["rise"]
    return x


def pipeline(x):
    """算出値を正典へ書き戻す一連のパス。**ここが唯一の定義**(土井 build_doi_sashizu.py の作法)。
    ⛔ 往復試験の台本に**同じ手順の写し**を持たせない — 生成器にパスを足したとき、
      台本だけが古いままになって偽の不一致を出す(2026-08-25 土井 検図14巡)。"""
    x = fix_gate_runs(x)
    x = fix_terrace_walls(x)
    x = fix_nishi(x)
    x = fix_ramps(x)
    x = fix_terrace_keeps(x)
    x = fix_naka(x)
    x = fix_sawatobi(x)
    x = fix_garden_geom(x)
    x = fix_mizu(x)
    x = fix_edge_profile(x)
    x = fix_sections(x)
    return x


def roundtrip_check(raw, pipeline):
    """**生成器が書く欄を全消去 → 再生成 → 正典と一致するか。**

    ⚠ 入力側を動かす感度試験では、**生成器が消さない出力欄は どの変異でも生き延びる**。
    土井が 2026-08-25 の検図10巡でこれに刺された — 前の版が書いた値が残り続け、
    2本の検査を黙らせていて「機械検査すべて0件」が**古い値に支えられていた**。
    当家も `edgeProfile` を 3日間 5.86m 古いまま12巡通している(EDO-0026)。
    ⛔ 従属値を人間が引き直すのを覚えている必要はない。**消して組み直して一致を見る。**

    門の開口に接する run の端は消せない(run の位置そのものが消える)ので、
    **わざと 0.05m ずらして**、組み直しが引き戻すかを見る。"""
    import copy
    stripped = copy.deepcopy(raw)
    for coll, keys in GEN_FIELDS.items():
        for o in stripped.get(coll, []):
            for k in keys:
                o.pop(k, None)
    _gp_strip(stripped)                        # 入れ子の中の算出値も剥がす
    dead9 = list(GP_DEAD)                      # ⭕ 解決先0件のパスは往復試験の指摘として出す
    if "edgeProfile" in stripped:              # 値だけ消し、辺の別は残す(入力)
        stripped["edgeProfile"] = dict((k, []) for k in stripped["edgeProfile"])
    ge9 = stripped["gate"]["edge"]
    gs9 = stripped["gate"]["s"]
    half9 = stripped["gate"]["plan"]["monW"] / 2.0
    for r9 in stripped["runs"]:                # 開口側の端をずらす(消せないので破壊する)
        if r9.get("edge") != ge9:
            continue
        if abs(r9["s1"] - (gs9 - half9)) < 0.20:
            r9["s1"] += 0.05
        if abs(r9["s0"] - (gs9 + half9)) < 0.20:
            r9["s0"] -= 0.05
    rebuilt = pipeline(stripped)
    bad = []

    def _cmp(where, a, b, tol=1e-6):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if abs(float(a) - float(b)) > tol:
                bad.append("%s 正典=%.4f 組み直し=%.4f" % (where, a, b))
        elif json.dumps(a, ensure_ascii=False, sort_keys=True) != \
                json.dumps(b, ensure_ascii=False, sort_keys=True):
            bad.append("%s 正典=%s 組み直し=%s"
                       % (where, json.dumps(a, ensure_ascii=False)[:60],
                          json.dumps(b, ensure_ascii=False)[:60]))

    for coll, keys in GEN_FIELDS.items():
        by = dict((o["name"], o) for o in rebuilt.get(coll, []) if "name" in o)
        for o in raw.get(coll, []):
            r = by.get(o.get("name"))
            if r is None:
                bad.append("%s %s が組み直しで消える" % (coll, o.get("name")))
                continue
            for k in keys:
                _cmp("%s %s.%s" % (coll, o.get("name"), k), o.get(k), r.get(k))
    for p9, qa, qb in _gp_pairs(raw, rebuilt):
        _cmp("%s(入れ子の算出値)" % p9, qa, qb, tol=0.005)
    ea, eb = raw.get("edgeProfile") or {}, rebuilt.get("edgeProfile") or {}
    if set(ea) != set(eb):
        bad.append("edgeProfile の辺の集合が組み直しと違う(正典=%s / 組み直し=%s)"
                   % (sorted(ea), sorted(eb)))
    else:
        for k in sorted(ea):
            if len(ea[k]) != len(eb[k]):
                bad.append("edgeProfile[%s] の点数が %d → %d" % (k, len(ea[k]), len(eb[k])))
                continue
            w = max([abs(p0[1] - q0[1]) for p0, q0 in zip(ea[k], eb[k])] or [0.0])
            if w > 1e-6:
                bad.append("edgeProfile[%s] が組み直しと最大 %.3fm 違う — "
                           "辺の地盤線は復元地盤から毎回引く" % (k, w))
    by = dict((r["name"], r) for r in rebuilt["runs"])
    for r9 in raw["runs"]:
        if r9.get("edge") != ge9:
            continue
        for k in GEN_FIELDS_GATE:
            _cmp("runs %s.%s(門の開口側の端)" % (r9["name"], k), r9.get(k), by[r9["name"]].get(k))
    for p9 in dead9:
        bad.append("GEN_PATHS『%s』が指す欄が1つも無い(綴りか構造が変わった)— "
                   "そのパスは往復試験の網から外れている" % p9)
    return bad


def main():
    d = json.load(open(JSON, encoding="utf-8"))
    prose = md2html(open(MD, encoding="utf-8").read())
    P = d["polygon"]
    area = abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
                   for i in range(len(P)))) / 2

    # 表門 yaw の検算 — 辺の外向き法線から Unity yaw(atan2(x,z))を導く(松平 42d4210 の作法)
    dxg, dzg, _ = _edge_dir(P, d["gate"]["edge"])
    nxg, nzg = dzg, -dxg
    cxg = sum(p[0] for p in P) / len(P); czg = sum(p[1] for p in P) / len(P)
    gx0, gz0 = d["gate"]["pos"]
    if (cxg - gx0) * nxg + (czg - gz0) * nzg > 0:
        nxg, nzg = -nxg, -nzg
    yaw_exp = math.degrees(math.atan2(nxg, nzg)) % 360
    if abs((d["gate"]["yaw"] - yaw_exp + 180) % 360 - 180) > 0.5:
        print("⚠ gate.yaw %.2f ≠ 辺法線からの期待値 %.2f — 松平 42d4210 と同種の向き事故"
              % (d["gate"]["yaw"], yaw_exp))

    # ⚠ 2026-08-24 検図: 断面の `natural`(json 静的)と生成器の江戸期DEM が別々の値を持ち、
    #   崖の肩(断面⑧ v=40)で 0.72m 食い違っていた。**毎回 DEM から組み直して書き戻す**
    #   (切盛量と同じ扱い — 同じ地形の二系統を残さない)。
    # ⭕ **往復試験を先に回す** — 正典から生成器の書く欄を剥がして組み直し、正典と一致するか。
    #   ⛔ 「直したか覚えている」に頼らない。EDO-0106 で土井から移した型。
    _raw = json.load(open(JSON, encoding="utf-8"))
    d = pipeline(d)
    ter9 = load_terrain(os.path.join(DOC, "okabe_edo_dem.json"))
    CHK = run_checks(d, _raw, ter9)
    report_checks(CHK)
    bad = CHK["矩形の重なり"]
    pbad = CHK["面のはみ出し(棟・庭が段と区画の中か)"]
    pr9 = program_check(d)

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ['<meta charset="utf-8">', "<title>岡部筑前守上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    hn = d.get("han", {})
    h.append('<p class="eyebrow">外桜田永田町 ／ %s・%s %s 上屋敷</p>'
             % (hn.get("kaku", ""), hn.get("tono", ""), hn.get("kokuJa", "")))
    h.append("<h1>岡部筑前守上屋敷 指図</h1>")
    h.append('<div class="box" style="border-color:var(--shu);margin-top:14px"><h3>基準年次と確度</h3><p>'
             '<b>基準年次=安政3年(1856)</b>(2026-08-30 ユーザー裁定・CLAUDE.md)。<br>'
             '<b>当主=岡部筑前守 長寛</b>(12代・安政2年家督。<b>[安政武鑑 岸和田](1855)が'
             '「岡部筑前守長寛」と刷り確度A</b>)。'
             '⭐ 参勤の年回りでは<b>安政3年(丙辰)は「暇」の年</b>'
             '(参府 丑卯巳未酉亥6月/暇 子寅辰午申戌6月)。<b>交代の月は6月</b>なので'
             '<b>1〜6月=在府 / 7〜12月=在国</b>に割れる。<br>'
             '⚠ <b>描く時点は安政3年の 1月〜6月に限る</b>【確度U — 当方の設計判断】。'
             '⭐ <b>2026-09-02 考証 K031: 従前の「1月〜8月24日」は 6月の交代をまたぐので'
             '末尾2ヶ月半が在国になり、「在府で一本化」と両立しなかった</b> — '
             '在府と両立する 1月〜6月へ詰めた。'
             '安政3年8月25日に<b>安政江戸台風</b>が江戸を襲い、被害は<b>前年に倍すといわれる</b>'
             '([安政江戸台風]B)。⛔ 年の後半を採ると「復旧が済んだ姿」が成立しない。'
             '⭐ この時点では<b>藩主は在府</b>。<br>'
             '⚠ <b>基図(尾張屋版切絵図 NDL1286657)は嘉永3年(1850)の板で、基準年次の6年前</b>。'
             '区画・街路・門の位置は6年で動かないので図の読みは有効だが、'
             '<b>人名表記は基図に合わせない</b>(同図の墨書は「岡部内膳正」)。<br>'
             '⭐ <b>安政江戸地震(安政2年10月2日)は基準年次の前年</b>。'
             '旧「倒れる前の姿として遡って使う」は撤回し、<b>復旧が済んだ姿を描く</b>。<br>'
             '<b>外構が「塀」であったことは当屋敷を含む一次記録から言える</b> — 安政江戸地震の被害書上が'
             '3邸一括で「右外構練塀潰其外所々大破」と記す記事に当屋敷が<b>明示的に含まれる</b>【<b>種別=確度S</b>・2026-08-24 に全文で確定】。'
             '⭐ 基準年次が記録の<b>翌年</b>になったので、旧「嘉永3年への遡及=B」は<b>解消</b>した。⛔ ただし記録は「外構練塀潰」=倒壊なので、建てるのは<b>再建された練塀</b>。'
             '⚠ ただし<b>どの辺か・誰が所有した塀かは書かれていない</b>ので、'
             '<b>帰属と全周であることは確度U(当方の裁定)</b>。三層に分けて読むこと。'
             
             '屋敷指図(建物平面)は現存未確認 — 御殿の構成は類型(B)、室名・畳数は想定(U)。'
             '書院は<b>%s(%s)の格</b>で作る — <b>これは史料が刷る格そのもの</b>'
             '([大成武鑑 嘉永3]<b>A</b>「帝鑑間　朝散大夫」)。'
             '⛔ <b>2026-09-02 考証 K023: 従前の「雁之間詰の格で作り帝鑑間格へ上げない」は結論が逆だった</b> — '
             '上げないのではなく、<b>帝鑑間詰が当家の格</b>である(<b>確度B</b> — 詰間は当書の単独典拠で'
             '『寛政重修諸家譜』での確認は未了。⚠ 居城「泉州南郡岸和田」・詰間「帝鑑間」は『大成武鑑』嘉永3 コマ314–316 で読了済み(2026-08-25)。'
             '領知高・居城は [安政武鑑 岸和田](1855)が同値を刷るので確度A、詰間は当書の単独典拠で基準年次の6年前になるため確度B)。'
             '区画多角形はユーザーのブックマーク角(U)。</p></div>'
             % (hn.get("tono", ""), hn.get("kaku", "")))
    h.append('<p class="lede"><b>この文書は現況だけを載せる。</b>過去の案・撤回した説は書かない — '
             '経緯は <code>git log docs/Sashizu/</code> で追う。'
             '寸法の正典は <code>okabe_sashizu.json</code>、文章は <code>okabe_kosho.md</code>、'
             'この HTML は <code>Tools/Sashizu/build_okabe_sashizu.py</code> が組む。'
             '<b>数値をこの文書に書き足さないこと。</b></p>')
    h.append('<div class="box" style="border-color:var(--shu)"><h3>⚠ この指図はまだ実装されていない</h3><p>'
             '<b>Unity のシーンにあるのは 2026-08-23 のゼロベース改稿より前の設計</b>で、この図とは'
             '座標系ごと別物。実装の <code>EdoOkabeYashikiBuilder.cs</code> は'
             '<b>存在しない章と、番号がずれて別章を指す参照</b>を持ち、'
             'run 名・面の高さ・郭の土留めのいずれも一致しない。'
             '<b>図を現物と照合しないこと。</b>順序は <code>_pending.junjo ③</code>(実装の全面書き直し)。</p></div>')
    h.append('<div class="box"><h3>作る順序</h3><p>'
             '① 設計=<code>json</code>/<code>md</code> を直す → ② 組む → ③ 検図(edo-kosho / edo-kenzu)'
             '→ ユーザーのレビュー → ④ 実装 → ⑤ 指図と実装を突き合わせて 0 件 → ⑥ 経緯はコミットへ。</p></div>')

    KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
           "其十一", "其十二", "其十三", "其十四", "其十五",
           "其十六", "其十七", "其十八", "其十九", "其二十",
           "其二十一", "其二十二", "其二十三", "其二十四", "其二十五",
           "其二十六", "其二十七", "其二十八", "其二十九", "其三十"]   # ⚠ 足りないと nx() が IndexError
    _kn = [0]

    def nx():
        _kn[0] += 1
        return KAN[_kn[0] - 1]

    plate(h, nx(), "敷地",
          "**拝領 %s坪余 ＋ 永預 %d坪余**([大江戸今昔めぐり 岡部区画]B)／"
          "当図の polygon %.0f m²(%.0f坪) = 拝領の %+.1f%%／江戸間 1間=%.3fm／"
          "グリッドは東辺(表門の辺)沿いの回転フレーム"
          % ("{:,}".format(int(hn.get("tsubo", 0))), hn.get("tsuboAzukari", 0),
             area, area / TSUBO,
             100.0 * ((area / TSUBO) / hn.get("tsubo", 1) - 1.0), d["const"]["ken"]))
    plane_legend = "".join(
        '<span style="color:%s">■ %s%s</span>'
        % (PLANE_COL.get(p["name"], "var(--dan4)"), p["name"],
           (" %.1f" % p["y"]) if p["y"] is not None else "(松+雑木の樹林)")
        for p in d.get("planes", []))
    fig(h, plan_svg(d),
        legend=plane_legend
               + '<span style="color:var(--hei)">━ 練塀(当家が建てる)</span>'
               '<span style="color:var(--take)">┄ 竹垣(法肩)／木柵(堀端)</span>'
               '<span style="color:var(--nagaya)">━ 坂(勝手の道)</span>'
               '<span>▪ 御殿の棟 ／ ▫ 付属屋</span>'
               '<span style="color:var(--shu)">● 表門 ／ ▪ 通用口 ／ ▨ 石段 ／ ┄ 断面</span>',
        cap="<b>敷地は水平な面%d枚(%s)+造成しない斜面。</b>"
            "面の高さは<b>主面=盛土を免れた実測セルの中央値(P)+[五千分一東京図31]で24&lt;h&lt;26に拘束(B)</b>、<b>門前面=同図で12〜14の帯に拘束(A)／安政3年への遡及(B)／帯の中で値を採ること(U)</b>(⚠ <b>ただし帯の中を 12 の等高線が渡る位置は未読</b> — 11.7 &lt; 12 &lt; 13.7 である以上どこかで必ず渡るので、『渡りが無い』という読みは<b>内部矛盾を抱えたまま</b>) — 全面が"
            "[菊地2003] の 1〜4m に収まる。%s"
            "<b>東の崖・北東のランプ・南西の谷・西斜面は造成しない</b> — "
            "樹林と庭のまま、生活面の縁に竹垣。斜面の植生は松+雑木(竹林にしない=[橋本・堀1998])。"
            "<b>囲いの天端は run ごとに一直線</b> — 面の縁になる区間は水平に面の高さで通し、"
            "造成しない斜面の区間は一定勾配で地形を追う(規約は下限 %.2fm・上限は石垣の丈 4.0×s。<b>実測の最大は %.1fm</b>)。"
            "<b>街路・隣地への影響はゼロ</b> — 段も法面も区画線で切っている(<code>in_parcel</code> で機械的に)。"
            % (len(d["terraces"]), " / ".join("%.1f" % t["y"] for t in d["terraces"]),
               _fit_note(d), d["const"]["baseMin"],
               max(run_base(d, r)[1] for r in d["runs"])))
    h.append(planes_table(d))
    h.append('<p class="cap"><b>面のはみ出し検査(0.5間刻みの被覆): %s。</b>'
             '棟・付属屋・廊下は自分の y と同じ高さの段の中に、庭・井戸はいずれかの段の中に'
             '完全に載っていることを機械検査している。</p>'
             % ("<b>0 件</b>" if not pbad else "⚠ %d 件 — %s" % (len(pbad), " / ".join(pbad))))
    h.append(slope_table(d))
    h.append("</div>")

    dem = load_terrain(os.path.join(DOC, "okabe_edo_world.json"))   # 造成の出発点=江戸期の復元地盤
    if dem:
        pc = {}
        try:
            for q in json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))["parcels"]:
                pc[q["id"]] = q
        except Exception:
            pass
        others = []
        for pid, col, wdt, lab in (("matsudaira_dewa", "#2E6DA4", 1.8, "松平出羽守 上屋敷"),
                                   ("doi", "#7D3C98", 1.8, "土井大隅守 上屋敷"),
                                   ("sannobuke_juge", "#1E8449", 1.8, "樹下近江守 屋敷"),
                                   ("sanno_monzen_1", "#B7950B", 1.4, "山王門前町"),
                                   ("sannojubo_jomyoin", "#117A65", 1.4, "常明院")):
            if pid in pc:
                q = [(a, b) for a, b in pc[pid]["pts"]]
                cx = sum(a for a, _ in q) / len(q); cz = sum(b for _, b in q) / len(q)
                others.append((q, col, wdt, lab, cx, cz))
        P0 = d["polygon"]      # 岡部は指図の polygon を正典に**1回だけ**描く
        others.append((P0, "#C0392B", 2.8, "岡部筑前守 上屋敷",
                       sum(a for a, _ in P0) / len(P0), sum(b for _, b in P0) / len(P0)))
        plate(h, nx(), "現況図(拝領時造成の前の地形)",
              "**江戸期の復元地盤**(近代造成を戻したもの)／ 段彩 2m ／ 等高線 2m(太線 10m)【確度 U/B】")
        fig(h, dem_svg(d, dem, others), legend=dem_legend(),
            cap="<b>拝領時造成の出発点＝江戸期の復元地盤。</b>いまの地形ではない — "
                "<b>日比谷高校の近代造成(校庭の盛土と校舎の盛土)を戻したもの</b>で、"
                "確度は<b>U/B</b>(実測ではない)。作り方は仕様 <code>okabe_edo_recon.json</code> が持ち、"
                "生成器 <code>build_okabe_edo_dem.py</code> が正本に対して毎回実行する — "
                "校庭に埋もれた東の低い帯と崖は [五千分一東京図31](明治16)の"
                "三帯(台地24〜26／崖／低地12〜14)から起こし、台地は同図の帯の上端を超える所を落とし、"
                "近代の切土平場は周囲の実測から補間して埋め、変えた所を3回平滑化した。"
                "<b>台地の自然面は正本から毎回算出する</b>(盛土を免れた実測セルの中央値。セル数も値も <code>build_okabe_edo_dem.py</code> が刷る — 図に写さない)。"
                "⚠ <b>段の縁は、この図の崖の法肩に合わせてある。その崖は復元モデルが作ったもの(確度U)なので、"
                "『図に見える法肩と段の縁が一致する』ことは外部からの裏づけにならない</b>(自己整合)。"
                "法尻だけは 1883年図の ○13.x(区画内)に錨を取っている(確度A)。"
                "面の高さの根拠は「敷地」の表の確度の列。"
                "切盛図はこの地形と設計の差。"
                "<b>種地は正本 <code>base_dem.json</code></b>(地理院DEM由来・近代造成を含む現代の地面)で、"
                "<b>復元は岡部区画でクリップしてある</b> — 区画の外は正本そのもの。"
                "⛔ Unity の live terrain からは採らない(CLAUDE.md 規則12。2026-08-24 に4邸で"
                "『造成前の地形』が採った時刻によって食い違う事故が出た)。"
                "⚠ <b>当図だけ基準面がこの復元地盤で、土井・松平・山王・樹下は正本(現代の地面)で"
                "設計している。</b>⛔ <b>従前ここに書いていた『共有辺の上では差 0.00m』は誤り"
                "(2026-08-25 検図)</b> — 復元は区画線の直近まで地盤を作り替えるので、"
                "境の上で両者は必ず食い違う。<b>辺ごとの実測は「共有辺の上の地盤の食い違い」の表</b>。"
                "隣家と塀の天端・基壇・埋没を突き合わせるときは<b>必ず基準面を明記し、"
                "食い違う辺(とくに樹下境と土井境)は先方へ通知する</b>。"
                "細い破線は断面の切り位置。座標は Unity の世界座標(m)。")
        h.append("</div>")

    ter = load_terrain(os.path.join(DOC, "okabe_edo_dem.json"))     # 切盛は江戸期地盤に対して出す
    if ter:
        cf, vf, vc = cutfill_svg(d, ter)
        we0 = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
        mf = mc = 0.0
        for iv0 in range(ter["nv"]):
            for iu0 in range(ter["nu"]):
                n0 = ter["h"][iv0][iu0]
                if n0 is None:
                    continue
                dz0 = graded_y(d, ter["u0"] + iu0 * ter["step"],
                               ter["v0"] + iv0 * ter["step"], n0, we0) - n0
                mf = max(mf, dz0); mc = max(mc, -dz0)
        cft, vf, vc = cutfill_table(d, ter)      # ← 総量は表と同じ走査から採る
        gr9 = d.setdefault("grading", {}).setdefault("haryoJi", {})
        gr9["moridoM3"] = int(round(vf)); gr9["kiridoM3"] = int(round(vc))
        gr9["moridoMax"] = round(mf, 2); gr9["kiridoMax"] = round(mc, 2)
        # 復元の効き方 — この屋敷で最大の土工なので図にする(2026-08-25 検図)
        ks, kf, kc, kmf, kmc, kpct = kindai_svg(d)
        kj = d.setdefault("grading", {}).setdefault("kindaiJokyo", {})
        kj["moridoM3"] = int(round(kf)); kj["kiridoM3"] = int(round(kc))
        kj["moridoMax"] = round(kmf, 2); kj["kiridoMax"] = round(kmc, 2)
        kj["touchedPct"] = round(kpct, 1)
        kj["_"] = ("**近代造成の除去量** = 正本(現代の地面)と江戸期の復元地盤の差。"
                   "⛔ **拝領時造成(`haryoJi`)とは別勘定** — こちらは史実の土工ではなく"
                   "『近代に積まれた土を戻す』という当方の復元の量である。"
                   "**生成器が算出して書き戻す**(2026-08-25 まで旧値のまま凍っていた)。")
        plate(h, nx(), "復元の効き方(近代造成をどれだけ戻したか)",
              "正本 − 江戸期の復元地盤 ／ 区画の %.0f%% を動かした ／ 戻した土 切 %d m³・盛 %d m³"
              % (kpct, kj["kiridoM3"], kj["moridoM3"]))
        fig(h, ks, legend=cutfill_legend(),
            cap="<b>この屋敷で最大の土工は「復元そのもの」である。</b>拝領時造成(<b>次の章</b>)の約 %.1f 倍。"
                "寒色=近代の盛土を削り落とした所(校庭・校舎)/暖色=近代の切土を埋め戻した所。"
                "⚠ <b>これは史実の土工ではなく、当方の復元(確度U/B)の量</b> — "
                "手順とパラメータは <code>okabe_edo_recon.json</code>、実行は "
                "<code>build_okabe_edo_dem.py</code>。最大は 切 %.2fm / 盛 %.2fm。"
                "⛔ <b>Unity の造成ステージで流すのは<b>次の章</b>の拝領時造成だけ</b>で、"
                "この量を流すのではない(地形は正本から復元レイヤを別に持つ)。"
                % ((kj["kiridoM3"] + kj["moridoM3"]) / max(1.0, float(
                       d["grading"]["haryoJi"].get("moridoM3", 1) +
                       d["grading"]["haryoJi"].get("kiridoM3", 1))),
                   kj["kiridoMax"], kj["moridoMax"]))
        h.append("</div>")

        plate(h, nx(), "切盛(どこを盛り、どこを切るか)",
              "盛土 %d m³(最大 %.2fm) ／ 切土 %d m³(最大 %.2fm) ／ 差引 %+d m³"
              % (gr9["moridoM3"], gr9["moridoMax"], gr9["kiridoM3"], gr9["kiridoMax"],
                 gr9["moridoM3"] - gr9["kiridoM3"]))
        fig(h, cf, legend=cutfill_legend(),
            cap="<b>造成前の地形(江戸期の復元地盤・確度U/B)と造成後の地盤の差</b>を1間の格子で塗った。"
                "暖色=盛土/寒色=切土/<b>無彩=±%.2fm 以内</b>(動かさない)/"
                "<b>±%.2fm 未満は升そのものを描かない</b>(素地のまま)。"
                "⛔ この二つは別の閾値で、どちらも実装値から刷っている/" % (CF_FLAT, CF_SKIP) +
                "地の色(薄い緑)のまま=<b>造成しない</b>。破線の枠は段、細い実線は御殿の棟。"
                "<b>面の高さを地形の実測と1883の等高線の帯から採ってあるので、郭の大半は無彩か薄い色になる</b> — "
                "<b>濃く出る所は算出して出す</b>(手で書かない): %s。" % _fill_where(d, ter))
        h.append(cft)
        h.append(edge_drop_table(d))
        h.append(walls_table(d))
        h.append('<p class="cap"><b>郭の土留め: %d 本。</b>%s</p>'
                 % (len(d.get("terraceWalls", [])),
                    ('⭕ <b>西の法尻は江戸期の斜面が自力で着地するので土留めは要らない。</b>'
                     '⛔ 「土留めを全廃した」という言い方はしない — '
                     '置かない理由は方針ではなく<b>地形</b>である。'
                     '⚠ 2026-09-02 に一度は立てたが、西の地盤を明治16年図から起こし直したところ'
                     '<b>前提が消えた</b>ので同じ日に外した(経緯は git log)。'
                     if not d.get("terraceWalls") else
                     '⭐ 天端は一つの丸い数字で一直線・丈は埋まりで調整'
                     '(<code>unity-modular-stonewall</code> §3・§3b)。線と落差は生成器が算出する。')))
        bb = CHK["法面(段の外が現地形へ着地するか)"]
        h.append('<p class="cap"><b>法面の検査: %s。</b>'
                 '<b>造成モデルは 2026-08-26 に土井式へ統一した</b>(ユーザー指示。'
                 '旧岡部式=縁の盛土厚の逓減形は廃止): 段の外は<b>一定勾配の法面'
                 '(盛土 1:%.1f/切土 1:%.1f)で現地形へ摺り付け</b>、'
                 'cap %.0fm の内で現地形に着地しない法面は出さない(崖の縁は土留め・石垣の領分)。'
                 '土井式が要する法面パラメタ(batterFill/batterCut/featherCap)は'
                 '当邸の設計値にすべて有り、土井の既定値で補った項目は無い。'
                 '検査は「<b>法面が可能だった所を造成が 1:%.1f より急にしていないか</b>」で、'
                 '地山が既に 1:%.1f を超える崖は対象外(どんな薄い土工も超えるため)。'
                 '囲いのある辺から1.5間以内も対象外 — そこは石垣基壇が受ける。%s</p>'
                 % ("<b>0 件</b>" if not bb else "⚠ <b>%d 件</b>" % len(bb),
                    d["const"]["batterFill"], d["const"]["batterCut"],
                    d["const"].get("featherCap", 12.0), d["const"]["batterCut"], d["const"]["batterCut"],
                    ("" if not bb else
                     "<br>⛔ <b>%d 箇所は「崖の肩」では説明できない</b>(地山 %s) — "
                     "西の法尻(u−7〜+16 / v113〜115)で法面が現地形に着地せず、"
                     "<b>約44m にわたり最大 3.9m の垂直段差</b>が残る。"
                     "⚠ <b>受け方はユーザー裁定待ち</b> — ①土留めを立てる ②段の縁を内へ引く。"
                     "⛔ <b>当図はまだどちらも入れていない</b>(意匠の判断なので指図方では決めない)。"
                     "⭐ 2026-09-02 まで<b>この検査の結果は要約に出ておらず、"
                     "このキャプションの中にしか無かった</b>(K061)。いまは要約に件数が出る。"
                     "<br>%s" % (len(bb), _grad_band(bb), " / ".join(bb)))))
        h.append('<p class="cap"><b>上の段別表の「拝領時造成の計」は章のプレートの総量'
                 '(盛 %d / 切 %d m³)と一致する</b> — 段の外へこぼれる法面の行を含めてあるため。'
                 '坂の路盤 <code>R_Ramp</code> だけが別勘定で、総計の行に分けて出してある。'
                 '(⛔ 従前ここに「一致しない」と書いていたのは、法面の行を足した後の消し忘れ。'
                 '偽の警告は本物の警告の信用を削るので 2026-08-25 に落とした。)'
                 '<b>量の正典は json <code>grading.haryoJi</code></b> — この図が算出して書き戻す。</p>'
                 % (gr9["moridoM3"], gr9["kiridoM3"]))
        h.append('<p class="cap">段の外へこぼれる法面(盛土 1:%.1f/切土 1:%.1f)も土量に含む。'
                 '土留めのある辺は壁が垂直に受けるので法面を出さない。'
                 '[菊地2003] の江戸城下67遺跡の集成では土地改変は <b>1〜4m が多数</b>で、'
                 '当屋敷は盛土 %.1fm・切土 %.1fm に収まる。'
                 '<b>差引が正=土が足りない</b>ので、切土で出た土を盛土へ回してなお不足する量。</p>'
                 % (d["const"]["batterFill"], d["const"]["batterCut"], mf, mc))
        h.append("</div>")
    plate(h, nx(), "御殿平面", "室名=[西川1959]A の型 ／ **畳数と室の配り=確度U(推定)** — 当屋敷の指図は現存未確認")
    fig(h, goten_plan(d, *plan_frame(d, "Shumen"), label="御殿平面", note=
                      "廊下は入側・渡廊下とも幅一間。奥向へ入る廊下は御錠口の一本だけ"),
        legend='<span style="color:var(--roka)">■ 入側・渡廊下(幅一間)</span>'
               '<span style="color:var(--shu)">■ 御錠口</span>'
               '<span style="color:var(--niwa)">■ 庭</span>'
               '<span style="color:var(--shirasu)">■ 白洲</span>'
               '<span>┄ 襖線(続き間の境)</span>',
        cap="<b>長屋門 → 叩きの石段4段 → 門前面 → 参道の石段39段 → 主面の白洲 → 車寄・御式台・御玄関。</b>"
            "門の軸に石段を%d本重ねて主面へ登る(道→玄関の登りは%sのとおり)。"
            % (len(d["kaidans"]),
               next((x["name"] for x in d["sections"]
                     if x["axis"] == "u" and abs(x["at"]) < 1), "門の軸の断面")) +
            "西へ書院棟(上段之間18畳)、その西に中奥棟・奥向棟、南に台所棟、北に長局。"
            "<b>奥向へ入る口は御錠口の一本だけ</b>([西川1959]A)。"
            "室名は [西川1959](正徳期 津軽藩4万7千石 柳原屋敷図)の型で、<b>畳数と配りは確度U</b>。")
    h.append("</div>")

    # ⚠ 之二の親番号は**直前に振った番号から引く**(章を足すと手書きの「其四之二」が腐る)
    plate(h, KAN[_kn[0] - 1] + "之二", "門前面 平面", "長屋門・白洲・厩・供待・蔵・家臣長屋")
    fig(h, goten_plan(d, *plan_frame(d, "Monzen"), label="門前面 平面", note=
                      "土蔵は門まわり([高知2000]A の火消道具蔵・御駕籠蔵)。"
                      "家臣長屋は練塀の内側の帯([西川1959]A)"),
        cap=("<b>拝領時に均した面(高さは「敷地」の表)</b> — 自然のベンチではない。"
             "1883の実地形は北へ約1.07%上がる(段別の切盛量は「切盛」の段別表)。"
             "門の敷居は道なりから採るので面より低い(差は断面の章)。"
             "<b>門口は面から切り欠いてあり</b>、そこが門を入った叩き — "
             "石段 " + d["kaidans"][0]["name"] + " %d段(走りは「取り合い」の表)で面へ受ける。"
             % d["kaidans"][0]["steps"]))
    h.append("</div>")

    if d.get("routes"):
        plate(h, nx(), "動線(表門を入ってからどう動くか)", "系統4つ ／ すべて【設計判断U】")
        fig(h, routes_svg(d, -42, 32, -4, 150),
            legend="".join('<span style="color:%s">━ %s</span>' % (c, n) for c, n in
                           [RK["omote"], RK["yaku"], RK["katte"], RK["oku"]]),
            cap="<b>門の軸(朱)が屋敷の背骨。</b>表門から御式台まで一本で通し、登るほど格が上がる — "
                "白洲 → 参道の石段39段(踊り場3箇所×3間) → 主面 → 車寄 → 御式台。"
                "<b>役方(緑)は表の用で御殿へ上がるので参道の石段を使う</b>(往復43段) — かわりに"
                "毎日の物の出入りが段を登らずに済むよう、土蔵・厩・供待・家臣長屋は門前面に置いた。"
                "<b>勝手(茶)は袋小路の通用口から入り、北東の坂で主面へ登る — 表門も参道も通らない</b>。"
                "奥向(青)へ入る廊下は御錠口の一本だけ。")
        h.append(routes_table(d))
        rp0 = (d.get("ramps") or [{}])[0]
        h.append('<p class="cap"><b>勝手の道は袋小路の通用口から。</b>'
                 '北東(u19〜29)は起伏4.1mでベンチが取れず面にしないので、石段でなく'
                 '<b>斜面なりの坂 %s(全長 %.0fm・最急 %.1f%%)</b>で主面へ登る — '
                 '米俵・薪を担いで通れるよう段を刻まない。'
                 '袋小路の通用口は<b>両家とも開く</b>(2026-08-23 ユーザー裁定) — '
                 '口に辻番を置く行き止まりの小路が存在する理由は、両家の勝手口を兼ねる形がよく説明する。</p>'
                 % (rp0.get("name", "R_Ramp"), rp0.get("len", 0),
                    (ramp_metrics(d, rp0) or {}).get("grad", 0)))
        h.append("</div>")

    plate(h, nx(), "棟と室",
          "1間²=2畳(土間・板敷は間²) ／ **室名=[西川1959]A の型(一部B)／畳数と室の配り=確度U(推定)** — "
          "当屋敷の指図は現存未確認。2026-08-24 に確度を明示して閉じた")
    h.append(munes_table(d))
    h.append(links_table(d))
    kp_html, kp = kenpei(d, area)
    K0 = d["const"]["ken"]
    nagL = sum(r["s1"] - r["s0"] for r in d["runs"] if r["kind"] == "Nagaya")
    perim = sum(math.hypot(P[(i + 1) % len(P)][0] - P[i][0], P[(i + 1) % len(P)][1] - P[i][1])
                for i in range(len(P)))
    h.append("<h3>建蔽率</h3>")
    h.append(kp_html)
    hika = (1.0 - sum(tarea(t) for t in d["terraces"]) * K0 * K0 / area)
    d.setdefault("grading", {}).setdefault("hikaishu", {})["tsubo"] = int(round(hika * area / TSUBO))
    d["grading"]["hikaishu"]["_"] = ("段にしない(＝造成しない)面積。**敷地から段の多角形の面積を引いた残り**を"
                                     "生成器が算出して書き戻す。東の崖・北東のランプ・南西の谷・西斜面・北の法面の総和")
    ownL = sum(r["s1"] - r["s0"] for r in d["runs"]) \
        + sum(f["s1"] - f["s0"] for f in d.get("fences", []))
    h.append('<p class="cap"><b>分母は敷地全体。</b>可建地に替えて数字を作らない。'
             '大名上屋敷の建蔽率の史料値は [福井図] の <b>5〜6割</b> と [鈴木1985] の旗本8例 '
             '<b>22〜55%%</b> の二つで、当図の %.1f%% はどちらの下端も下回る'
             '(広い拝領地・門前と前庭の白洲・奥庭・<b>造成しない斜面が敷地の %.0f%%</b>・'
             '塀の内側に平場がある区間が短く外周の長屋帯が伸びないため)。'
             '[追川2017] の 15%% / 28.6%% / 47.7%% は<b>表長屋の規模比であって建蔽率ではない</b>ので'
             '混ぜない(分母の定義も原典未確認 — sources.md の⚠)。'
             '外周は全周 <b>%.0fm</b> のうち当家が建てるのが <b>%.0fm(%.0f%%)</b> で、'
             'その内訳は<b>表長屋 %.1fm</b>・練塀 %.0fm・木柵 %.0fm・長屋門 %.1fm。'
             '⚠ <b>面積が二つ併存する</b> — 記録の拝領坪数 %s坪余で割れば <b>%.1f%%</b>。'
             '分母は図の実体である polygon のままにするが、読者に隠さない。'
             '<b>建蔽率は結果であって目標ではない</b> — 数字のために空地へ棟を足さない。'
             '⚠ <b>この %.1f%% は史料値の帯の外にある。</b>表長屋を辺12だけに留めた裁定(確度U)と、'
             '造成しない斜面が半分という地形の実体の合成であって、'
             '<b>5万石級上屋敷の類型を代表する数字ではない</b>(§A-3)。</p>'
             % (kp, 100.0 * hika,
                perim, ownL + d["gate"]["plan"]["monW"],
                100.0 * (ownL + d["gate"]["plan"]["monW"]) / perim,
                sum(r["s1"] - r["s0"] for r in d["runs"] if r["kind"] == "Nagaya"),
                sum(r["s1"] - r["s0"] for r in d["runs"] if r["kind"] != "Nagaya"),
                sum(f["s1"] - f["s0"] for f in d.get("fences", [])),
                d["gate"]["plan"]["monW"],
                "{:,}".format(int(d.get("han", {}).get("tsubo", 0))),
                kp * (area / TSUBO) / max(d.get("han", {}).get("tsubo", 1), 1), kp))
    h.append("</div>")

    # ================================================================ 庭
    ter2 = ter if ter else load_terrain(os.path.join(DOC, "okabe_edo_dem.json"))
    pm = pond_metrics(d)
    plate(h, nx(), "庭(主面の割り当て)",
          "**庭方 `edo-niwashi` の設計を書き起こしたもの** ／ %d 区画 ／ "
          "⭐ **主面の5区画は平坦化しない**(2026-09-02 ユーザー裁定=案A)"
          % len(d["gardens"]))
    fig(h, niwa_plan_svg(d),
        legend='<span style="color:var(--niwa)">■ 鑑賞の庭</span>'
               '<span style="color:#B9C7A4">■ 樹林</span>'
               '<span style="color:var(--shirasu)">■ 白洲</span>'
               '<span style="color:var(--ink-lo)">■ 作業場</span>'
               '<span style="color:var(--ike)">■ 泉水</span>'
               '<span style="color:var(--tsuki)">■ 築山</span>'
               '<span style="color:var(--hei)">━ 結界ののし塀</span>'
               '<span style="color:var(--shu)">━ 中門・木戸 ／ ● 見所</span>'
               '<span style="color:var(--take)">┄ 法肩の竹垣</span>',
        cap="<b>主景は一点=「書院の泉水」。</b>第二の景が溜池の借景(見晴らし)、第三が南の芝谷。"
            "<b>網掛けの5区画は面を作らない</b> — 棟が載る所だけ 24.80 に均し、残りは自然地盤のまま"
            "(ユーザー裁定=案A)。段の<b>抜き</b>として持ち、抜きの中でも棟の足跡と犬走りは面が残る。"
            "⛔ <b>馬場は作らない</b> — 30間の直線が取れず、厩は門前面にあって段が違う。"
            "『無い』も当方の推定である【U】。")
    h.append(gardens_table(d))
    if ter2:
        h.append(niwa_earth_table(d, ter2))
    abad = garden_alloc_check(d)
    h.append('<p class="cap"><b>割り当ての矩形どうしの重なり: %s。</b>'
             '⛔ 当図は §4 の並び順で上位が取ると決めて機械的に解いてあるので、'
             '<b>解けたことと割り当てが整合していることは別</b> — 重なりそのものをここに出す。'
             '境界を引き直すのは意匠の判断なので<b>庭方へ差し戻す</b>。%s</p>'
             % ("<b>0 件</b>" if not abad else "⚠ <b>%d 件</b>" % len(abad),
                "" if not abad else "<br>" + "<br>".join(abad)))
    h.append("</div>")

    plate(h, nx(), "書院の泉水(主庭)",
          "主視点=上段之間の北入側 ／ 水面 %.0f坪(庭の %.0f%%)／ "
          "**円形度 施工形状 %.3f / 設計値 %.3f** ／ 見隠れ %.0f%%"
          % (pm["tsubo"], 100.0 * pm["tsubo"] / max(pm["gardenTsubo"], 1e-9),
             pm["circ"], pm["circRaw"], pm["visPct"]))
    fig(h, pond_svg(d),
        legend='<span style="color:var(--ike)">■ 水面</span>'
               '<span style="color:var(--tsuki)">■ 中島・築山</span>'
               '<span style="color:var(--ishi)">● 石(景石・汀石・護岸)</span>'
               '<span style="color:var(--nagaya)">━ 園路</span>'
               '<span style="color:var(--dim)">┄ 設計値の汀線(生の点列)</span>'
               '<span style="color:var(--cut4)">┄ 掛樋</span>'
               '<span style="color:var(--cut3)">┄ 水尻</span>'
               '<span style="color:var(--shu)">┄ 底樋 ／ ● 見所と視線</span>',
        cap="<b>三層に読む。</b>前景=沓脱・飛石・三石(眼から 0〜8m)／ 中景=水面・中島・岩島・沢飛石の渡り／ "
            "遠景=築山Aとその上のアカマツ、さらに土井境の樹林。<b>真行草は行</b>"
            "(石組を使うが草体の柔らかさを残す)。"
            "⛔ <b>くびれに橋は架けない</b> — 平滑後の実水面幅に対して橋が重すぎるので"
            "<b>沢飛石</b>で渡る(2026-09-02 庭方)。渡りの区間だけ池床を上げて水深を一定にする。"
            "⛔ 中島に橋を架けない・真円にしない。"
            "⛔ 春日型の灯籠を置かない・蹲踞を置かない・枯流れを置かない — "
            "<b>いずれも当方の裁定であって史料の否定ではない</b>。"
            "石材は<b>伊豆石で一系統</b>、板石(沓脱)だけ根府川石【流通=B】。")
    h.append(pond_table(d))
    h.append(tsukiyama_table(d))
    nbad = niwa_element_check(d)
    pbad2 = pond_check(d)
    h.append('<p class="cap"><b>池の検査: %s。 築山の検査: %s。 点景の検査: %s。</b>'
             '検査の中身は「汀線が主面の中にあるか / 棟・渡廊下と重ならないか / '
             '宣言した離れを下回らないか / <b>掘り込みであること</b> / '
             '築山の底の自然地盤を実測すること / 点景が自分の庭の中にあり水に落ちていないか」。%s</p>'
             % ("<b>0 件</b>" if not pbad2 else "⚠ %d 件" % len(pbad2),
                "<b>0 件</b>" if not tsukiyama_check(d) else "⚠ %d 件" % len(tsukiyama_check(d)),
                "<b>0 件</b>" if not nbad else "⚠ <b>%d 件</b>" % len(nbad),
                "" if not nbad else "<br>⛔ <b>庭方へ差し戻す:</b> " + " ／ ".join(nbad)))
    h.append("</div>")

    plate(h, KAN[_kn[0] - 1] + "之二", "水の系統(水源・水尻・底樋)",
          "⛔ **当図では滝を置かない=U**(水源が未決)／ ⛔ 土井邸へは一滴も落とさない")
    fig(h, mizu_svg(d),
        cap="<b>水尻は暗渠で法肩の下を抜き、石張りの落とし溝で北の法面を下り、"
            "法尻の自然の水路を東へ、通用口の脇の側溝から袋小路の街路溝へ落とす。</b>"
            "縦断の折れ点は設計値、落差と延長は算出値。"
            "<b>池干しのための底樋</b>を同じ堀に重ねて敷く — これが無いと池を干せない【B】。")
    h.append(mizu_table(d))
    h.append("</div>")

    plate(h, nx(), "奥庭(築山B)",
          "主視点=御座之間の南入側 ／ ⛔ 水を置かない(池は一つ)／ ⛔ 枯流れも置かない")
    fig(h, okuniwa_svg(d),
        legend='<span style="color:var(--tsuki)">■ 築山B</span>'
               '<span style="color:var(--nagaya)">━ 園路</span>'
               '<span style="color:var(--take)">■ クロマツの疎林(見隠れ)</span>'
               '<span style="color:var(--hei)">━ 結界ののし塀</span>'
               '<span style="color:var(--shu)">● 見所と視線</span>',
        cap="<b>歩くと三つの場面が変わる</b> — 苔と石組の静かな平庭 → 築山と谷の道 → 見晴らしへ抜ける。"
            "⛔ <b>築山Bに「自然の高まりに載る」とは書かない</b>: 底は完全に平坦で、"
            "<b>全量を人が築く盛土</b>(用いる土は書院の泉水の掘削土)。⛔ 頂に平場を切らない。"
            "⭐ 築山Bの<b>北東の裾</b>の三石は 2026-09-02 に座標が確定し、図にも描いた"
            "(⛔ 従前この章は『位置が未定』『東裾』のままで、棟梁がここだけ読むと石を据えなかった)。")
    h.append('<p class="cap">築山Bに用いる土は<b>書院の泉水の掘削土</b> — '
             '量と収支は<b>「庭(主面の割り当て)」の土量の表</b>が一枚で刷る'
             '(⛔ 同じ量を二つの章で別々の基準で刷らない)。</p>')
    kbad = kekkai_check(d)
    CLF = cliff_metrics(d)
    h.append(kekkai_table(d))
    h.append('<p class="cap"><b>結界の検査(取り付き・表↔奥の非連結・動線): %s。</b>'
             '⭐ 経路探索の歩く範囲は<b>主面の法肩から上</b>に絞ってある'
             '(段の外輪の中、または地盤が段の高さ −0.5m 以上 — 当図が段の輪郭を引くのと同じ物差し)。'
             '⛔ <b>緩めたのではなく、図の宣言を実態へ合わせた</b> — 崖から下は外構の地である。'
             '⭐ その崖と帯は<b>実測でこうなっている</b>(江戸期の復元地盤から算出): '
             '崖の最急 <b>%.0f%%</b>・法肩 v%.1f〜%.1f ／ 帯の標高 <b>%.2f〜%.2f</b>・'
             '幅 <b>%.0fm</b>・台地からの落差 <b>%.1fm</b>。'
             '⚠ <b>2026-09-02 に西の地盤を [五千分一東京図31](明治16)から起こし直した</b> — '
             'それまで復元は屋敷の平場で止まっており、<b>崖と岸の帯は現代の地面のまま</b>だった。'
             '⛔ 勝手動線は一箇所も結界を横切らない — 台所の勝手口へは v&lt;80 側から回る。'
             '奥向へ入る屋内の口は御錠口の一本だけで、屋外はこの結界が受ける。</p>'
             % (("<b>0 件</b>" if not kbad else "⚠ %d 件 — %s" % (len(kbad), " / ".join(kbad)),
                 CLF["steepPct"], CLF["higV"][0], CLF["higV"][1],
                 CLF["bandMin"], CLF["bandMax"], CLF["widthM"], CLF["dropM"])))
    h.append("</div>")

    plate(h, nx(), "見晴らし(溜池の借景)",
          "第二の景 ／ 借景の実在=**P**(復元地盤の実測)／ 使い方=**U**")
    fig(h, shakkei_svg(d),
        cap="<b>視点から西へ、地盤を1間刻みで歩いて測った縦断。</b>"
            "遮るのは<b>一点だけ</b>(名と位置は図と表が刷る)で、そこを掠めた線が水面に達する"
            "所から先が見える。⛔ <b>手前の死角を『天然の見隠れ』と呼ばない</b> — "
            "その一点は<b>当方が辺5に建てた汀の柵(確度U)の天端</b>で、死角は設計の産物である"
            "(2026-09-03 考証4巡目)。⭕ <b>天然の見隠れ</b>と呼べるのは"
            "<b>奥庭の西の法肩のクロマツの疎林</b>のほうだけ。"
            "⛔ <b>築山Bは視軸の外にあり何も遮らない</b> — 見隠れを作るのは"
            "<b>奥庭の西の法肩に残すクロマツの疎林</b>で、"
            "奥向棟の南西の角で北へ折れた所ではじめて溜池が開く。"
            "面は盛らない(自然のまま)。<b>床几と毛氈</b>を出す場所で、建物は建てない"
            "【[戸山図] 麻呂ヵ嶽の作法=B】。")
    h.append('<p class="cap">⭐ <b>見える水面の測り方</b>(2026-09-03 に庭方と揃えた) — '
             '① 対岸は <code>parcels.json</code> の区画の東縁の<b>斜線</b>'
             '(⛔ 一定の v で切らない)／ ② 床几の眼から<b>方位ごとに %.2f° 刻みで掃く</b>'
             '(⛔ 眼を頂点にした一つの円錐で近似しない)／ ③ その方位で視線を切る物'
             '(区画内の地盤と、区画界に立つ<b>汀の柵の天端</b>)を掠める線が水面に達する所を'
             '<b>見えはじめ</b>とする／ ④ 見えはじめ〜対岸の交点を<b>極座標で積分</b>する。'
             '⚠ 掃く範囲は<b>見透しの窓(扇)の中だけ</b>で、当図の「開き角」は'
             '<b>扇の両縁を眼から見込む角</b>である(⛔ 遮蔽を掃いて出した角ではない)。</p>'
             % ((d.get("nishi") or {}).get("mado", {}).get("sweepDeg", 0.25)))
    h.append(shakkei_table(d))
    h.append("</div>")

    plate(h, nx(), "西の斜面と溜池の岸",
          "**庭方 `edo-niwashi` の設計を書き起こしたもの**(2026-09-02) ／ "
          "⛔ **庭ではない — 屋敷林と堀端**。灯籠・飛石・蹲踞は一つも置かない")
    fig(h, nishi_plan_svg(d),
        legend='<span style="color:#7E9A6B">■ 林</span>'
               '<span style="color:var(--shirasu)">■ 見透しの窓(扇)</span>'
               '<span style="color:#2F5A2F">● 松</span>'
               '<span style="color:#7A5C3A">● 榎</span>'
               '<span style="color:var(--take)">■ ヤダケの一叢</span>'
               '<span style="color:var(--nagaya)">━ 汀の柵'
               + ('・窓の小径' if ((d.get("nishi") or {}).get("mado") or {}).get("komichi")
                  else '') + '</span>'
               '<span style="color:var(--shu)">● 見所 ／ ● 木戸</span>',
        cap="<b>西は屋敷林で閉じ、見透しの窓だけを扇に開く。</b>"
            "⛔ <b>窓を平行な帯にしない</b> — 遠くほど広げないと視野が窄まる。"
            "⛔ <b>林の下端の線を直線にしない</b> — 舌と入江を作る(振れは下の表が算出)。"
            "⛔ <b>中部を低木にしない</b> — [名所図会・溜池]<b>S</b> が保証するのは"
            "<b>上=樹林 / 下=草地の二層</b>までで、崖面の中ほどを低木の帯にする読みは支えない。"
            "⚠ <b>林冠を閉じるのは当方の設計判断(U)</b> — 図は『崖面ぜんたいが閉じた林冠』とは"
            "言っていない(『裸地』とも言っていない)。"
            "⛔ <b>竹林にしない</b> — ヤダケの一叢だけが例外で、林の中に1箇所。"
            + (("<br>⭐ <b>小径は手入れ松 %s の袂を抜ける</b>(意図) — 幹の芯まで <b>%.2fm</b>、"
                "路の半幅を引いて <b>%.2fm</b>(算出)。⛔ 実装で松を避けて路を振らない。"
                % ((komichi_matsu_gap(d) or {}).get("name", "—"),
                   (komichi_matsu_gap(d) or {}).get("m", 0.0),
                   (komichi_matsu_gap(d) or {}).get("clear", 0.0)))
               if komichi_matsu_gap(d) else
               "<br>⛔ <b>窓の中に小径は置かない</b>【2026-09-03 ユーザー裁定8=A】 — "
               "窓は<b>芝だけの切れ込み</b>で、崖を下りる道は南の余地の<b>勝手の坂</b>。")
            + "⭐ 斜面は<b>一様な 25.4% の平面</b>なので路の勾配は<b>等高線となす角だけ</b>で"
              "決まり(<code>25.4% × sinα</code>)、⛔ <b>+u へ振る脚は −1.65%/間 のぶん損</b>を"
              "する。⭕ だから起点を台の北の角へ移し、最初の脚を −u へ振った。")
    fig(h, nishi_sec_svg(d, axisU=-15.0, inForest=True),
        cap="<b>林の中(u=−15)の縦断。</b>⛔ 窓の芯の断面には林が出ない(そこは芝の切り透し)ので、"
            "<b>鬱蒼とした林がどう載っているか</b>はこの一枚で見る(2026-09-03 庭方4巡目)。"
            "帯 B(林)と C(マント)の厚みと、法肩から法尻までの落差が読める。"
            "⚠ 地盤は [五千分一東京図31](明治16)から起こした復元。")
    fig(h, nishi_sec_svg(d),
        cap="<b>窓の芯(u=0)の縦断。</b>帯は<b>標高で切る</b>(法肩からの割合ではない)。"
            "朱の破線が<b>窓の中に置ける樹高の上限</b>で、床几の眼から溜池の水面への視線に"
            "余裕を見た値 — <b>これを超える物を窓の中に置くと検査が鳴る</b>。"
            "⚠ 地盤は 2026-09-02 に [五千分一東京図31](明治16)から起こし直したもの。")
    fig(h, taigan_svg(d),
        legend='<span style="color:#7E9A6B">■ 林冠</span>'
               '<span style="color:#CFCF9A">━ 草地(辺5の地盤)</span>'
               '<span style="color:#4A4A52">■ 帯の屋根</span>'
               '<span style="color:#7A5C3A">● 榎</span>'
               '<span style="color:#2F5A2F">┃ 法肩の松</span>'
               '<span style="color:#6B5637">┃ 汀の杭</span>'
               '<span style="color:var(--shu)">╌ 奥向棟の大棟</span>',
        cap="<b>対岸(溜池の西岸)の汀に立って東を見た姿。</b>"
            "⭐ 眼と対岸の線は<b>可視水面と同じ物差し</b>(`taigan_layers`)。"
            "⛔ <b>『二層に見える』を宣言で済ませない</b> — 見かけの厚みを**角度で測って**下の表に刷り、"
            "草地の層が痩せたら検査が鳴る(2026-09-03 考証 K211→K244 / 庭方 K230)。"
            "⚠ 崖下の帯の屋根は<b>草地の層を食う</b>ので、置き方でこの図が変わる。")
    h.append(taigan_table(d))
    for vC in ((d.get("nishi") or {}).get("crossV") or []):
        fig(h, nishi_cross_svg(d, vC),
            cap="<b>横断 v=%.0f。</b>汀・柵・木戸・見透しの窓の口を<b>横に切って</b>見る"
                "(2026-09-03 検図4巡目 — 横断が一枚も無かった)。"
                "⛔ 区画界より外は設計線なのでここには描かない。" % vC)
    h.append(slope_table(d))
    h.append(nishi_table(d))
    nbad2 = CHK["西の斜面と岸(窓・林・葭蓮・柵・小径)"]
    _km2 = ' / 窓の小径が林の中を通らず勾配が上限以下か' \
        if ((d.get("nishi") or {}).get("mado") or {}).get("komichi") else ''
    h.append('<p class="cap"><b>西の斜面と岸の検査: %s。</b>'
             '中身は「窓の中の樹高(棟の頂点と軒先も)が上限を超えないか / '
             '法肩の松が対岸から棟を切るのに足りるか / '
             '林の下端の線が直線でなく点数とピッチが規則どおりか / 帯が標高で連なるか / '
             '葭が水深の窓の外へ出ないか・蓮が『水面』の別か / '
             '柵が区画界にあり木戸が柵の上に1箇所か / '
             '汀の杭が水面を跨いで立ち径も芯々も不同不等か%s」。%s</p>'
             % ("<b>0 件</b>" if not nbad2 else "⚠ <b>%d 件</b>" % len(nbad2), _km2,
                "" if not nbad2 else "<br>⛔ <b>庭方へ差し戻す:</b> " + " ／ ".join(nbad2)))
    h.append("</div>")

    plate(h, nx(), "見所と植栽",
          "見所 %d 箇所 ／ **樹種の類型=B / 本数と位置=U**"
          % (sum(len(g.get("mikoro") or []) for g in d["gardens"])
             + len((d.get("nishi") or {}).get("mikoro") or [])))
    h.append(mikoro_table(d))
    h.append(shokusai_table(d))
    mbad = mikoro_check(d)
    xbad2 = niwa_cross_check(d)
    h.append('<p class="cap"><b>見所の検査: %s。 竹垣・勝手動線・結界塀が庭の点景を横切らないか: %s。</b>'
             '⚠ <b>法肩の竹垣の貫通検査からは「庭」の箱を外した</b> — §4 で主面の全面を'
             '12区画の庭に割り当てたので、法肩の竹垣は必ずどれかの庭の中を通る(構造的に落ちる)。'
             '⛔ 緩めたのではなく、<b>横切ってはいけないのは庭の点景</b>(池・築山・園路・飛石)だと'
             '言い直して検査に落とし直した。</p>'
             % ("<b>0 件</b>" if not mbad else "⚠ %d 件 — %s" % (len(mbad), " / ".join(mbad)),
                "<b>0 件</b>" if not xbad2 else "⚠ %d 件 — %s" % (len(xbad2), " / ".join(xbad2))))
    h.append("</div>")

    for axis, ttl, lead in (
        ("u", "断面(東西・道から奥へ)",
         "道(東)から敷地の奥(西)へ %d 本。南から北の順に並べる — 下段のベンチ・段丘崖・"
         "台地・西の低みがどう入れ替わるかを読む"),
        ("v", "断面(南北・樹下境から土井境へ)",
         "南(樹下近江守境)から北(土井大隅守境)へ %d 本。道側から奥の順に並べる — "
         "<b>東の崖(v22〜42)と北東のランプ</b>がこの向きで見える")):
        ss = [s for s in d["sections"] if s["axis"] == axis]
        plate(h, nx(), ttl, "%d 面 ／ 垂直はいずれも %.1f 倍" % (len(ss), ss[0]["vExag"]))
        h.append('<p class="cap">%s。</p>' % (lead % len(ss)))
        fig(h, key_plan(d, axis), cap="<b>切り位置</b>。朱の実線がこの節の断面、細い破線がもう一方の節の断面。")
        for s in ss:
            cs = section_crossings(d, s)
            h.append('<h3>%s%s</h3>' % (s["name"].split("(")[0],
                                        ("(" + "・".join(cs) + ")") if cs else ""))
            rng = [y for _w, y in s.get("natural", [])]
            fig(h, section_svg(d, s),
                cap=inline(s["_"].split("(江戸期地盤")[0].rstrip().replace("→", " → "))
                    + ("(江戸期地盤 %.1f〜%.1f)" % (min(rng), max(rng)) if rng else ""))
        h.append('<p class="cap"><b>段のつなぎ方は平面だけでは読めない。</b>地表下の色帯=面(「敷地」と同じ色分け)で、'
                 '<b>段の多角形が切り線を切る区間だけ</b>に出る(外接矩形では描かない)。'
                 '<b>破線=造成前の地形=江戸期の復元地盤</b>(確度U/B)なので、実線との差がそのまま切土/盛土。'
                 '区画線上に練塀を示す — 松平出羽守境(辺6・辺7)と堀端(辺5)は空けてある'
                 '(前者は松平所有、後者は木柵)。基壇は境界線上に垂直に立つ。'
                 '屋根は図示のための概略で、実装の高さは部材が決める(突き合わせの対象外)。</p>')
        h.append("</div>")

    plate(h, nx(), "外周の展開", "天端は run ごとに一直線(面の縁=水平／斜面=一定勾配)。段は継ぎ目と隅でのみ落とす")
    fig(h, perimeter_dev_svg(d))
    h.append(runs_table(d))
    sf = seat_fill_check(d)
    bt = base_thin(d)
    h.append('<p class="cap"><b>据面の内側の検査(面の縁の run・1m 刻み):</b> %s。'
             '<b>基壇を置かない区間</b>(露出が <code>const.baseMin</code> を下回り、塀が犬走りに直に載る): %s。</p>'
             % ("<b>0 件</b>" if not sf else
                "⚠ <b>%d件</b>(" % len(sf)
                + " / ".join("%s %d/%d 点・最大 %.2fm" % x for x in sf)
                + ")。<b>いずれも区画の隅の 4点だけ</b>で、辺12 の走り s=0 と s=95〜96 "
                "(＝三べ坂と隅切りが折れる所)。段の多角形は隅の鋭角に入らないので、"
                "そこだけ塀の据面(面の高さ)と背面の地山が離れる。"
                "<b>塀は基壇で受けており</b>(露出は「外周の展開」の表)、"
                "⚠ <b>隅の楔をどう納めるかは実装で決める</b> — 段を隅まで伸ばすと"
                "区画線から 0.875m の犬走りが取れなくなる",
                "—" if not bt else " / ".join("%s %.1fm" % (a, b) for a, b in bt)))
    h.append(edges_table(d))
    h.append(edge_datum_table(d))
    blankE = sorted(set(range(len(P))) - set(r["edge"] for r in d["runs"])
                    - set(f["edge"] for f in d.get("fences", [])))
    h.append('<p class="cap"><b>当家が建てるのは全13辺のうち %d 辺</b> — '
             '建てないのは 辺%s(<b>松平出羽守所有</b>。松江松平邸の指図が「南東(岡部境)=松平所有」'
             'と明記し、練塀 <code>S_Hei_Okabe4/5</code> を持つ。'
             '2026-08-23 に木柵から練塀へ改まった)。'
             '土井邸の指図は「南(岡部境)=<b>塀は岡部所有・当方は建てない</b>」と書くので、'
             '北辺(辺8・辺9)は当家が持つ。屋敷境の囲いは1条[丸の内三丁目]A。'
             '堀端(辺5)だけ木柵。<b>種別が練塀であることは確度S</b>、'
             '<b>帰属と全周は確度U(当方の裁定)</b>。'
             '<b>天端は run ごとに一直線</b> — 面の縁は水平、斜面は一定勾配。'
             '段は run の継ぎ目と隅でだけ落ち、最大 %.2fm(%s)。犬走り %.2fm。</p>'
             % (len(set(r["edge"] for r in d["runs"])),
                "・辺".join(str(e) for e in blankE),
                max([0.0] + [abs(rseat(y, y["s0"]) - rseat(x, x["s1"]))
                             for x, y in _joints(d)]),
                _max_joint_where(d),
                d["const"]["inubashiri"]))
    h.append("</div>")

    plate(h, nx(), "表門まわり",
          "長屋門+両番所(%s)。型式=現存する武家屋敷門の実例2件(確度A)＋格式階梯(B)/"
          "**表門は安政地震で無事(確度S)** — 当屋敷を名指す一次記録が「表門無別条」と書く"
          % d["gate"]["plan"].get("bansho", {}).get("kind", ""))
    fig(h, gate_svg(d),
        cap="<b>根拠は三段に割れる。</b> ①<b>長屋門であること・片流面出番所であること</b> = "
            "[山脇武家屋敷門]<b>A</b>(官製の構造形式)。同門は<b>5万石・譜代・江戸上屋敷の表門</b>で、"
            "当家(%s・譜代)と石高・格・屋敷の別が揃う。"
            "②<b>番所を両端に持つこと</b> = [西澄寺武家屋敷門]A(番所を両端に持つ長屋門の実寸例)"
            "＋学園側の記述(B) — ⚠ <b>山脇門の官製記録は番所の数を書いていない</b>。"
            "③<b>その両者を束ねた「5〜10万石=長屋門+両番所」</b> = "
            "[武家屋敷門の格式階梯]<b>B</b>。⚠ 階梯は<b>境界(5万石ちょうど)が曖昧</b>と原典自身が明記し、"
            "当家は帯の下端に接する。"
            "⛔ したがって<b>採用形『9間・二階建・%s』は2件のどちらの現物にも無い合成で、"
            "当家への採用そのものは確度U(外挿)</b>。①だけがAで、②はB、③もB。"
            "⛔ [山脇]は<b>門長屋の証拠には使わない</b>(袖が塀に載る現状は移築後の姿)。"
            "⭐ <b>表門は安政地震で無事だった</b> — 〔別本 藤岡屋日記 上〕(記事ID J1400017)が"
            "<b>当屋敷を名指して</b>「一岡部筑前守所々破損、<b>表門無別条</b>、尤潰家出火等無之」と書く"
            "<b>確度S</b>。基準年次は地震の翌年なので、<b>表門は建て替えでなくそのまま建っている</b>。"
            "⛔ したがって焼失規定による冠木門への降格は起きない。"
            "⚠ 別系統の〔安政度地震大風之記〕の3邸一括の記事は「右外構練塀潰其外所々大破」だけで"
            "表門にも表長屋にも触れないが、<b>同記事は網羅的でない</b>(同じ一括に入る土井は別の5記録で"
            "表門・表長屋の被災が記されるのに、この記事はそのどちらも書かない)ので、"
            "<b>この沈黙からは何も導けない</b>。「表門倒」は<b>土井大隅守の条</b>であって当家のものではない。"
            "在庫部材の実寸が門口に合わない場合は縮小流用か新造(部材表参照)。石垣畳出は使わない(設計判断)。"
            % (hn.get("kokuJa", ""), d["gate"]["plan"]["bansho"]["kind"]))
    h.append("</div>")

    rails = auto_rails(d)
    plate(h, nx(), "法肩の竹垣",
          "郭内の土留めは0本 — 全廃した ／ **位置は段の多角形から算出**(手で持たない)")
    h.append('<div class="tw"><table><thead><tr><th>竹垣</th><th>グリッドの折れ線(法肩に沿う)</th>'
             "<th>長さ</th><th class='note'>役目</th></tr></thead><tbody>"
             + "".join("<tr><td><code>%s</code></td><td>%s</td><td>%.1fm</td>"
                       "<td class='note'>%s の縁。落差 %.2fm</td></tr>"
                       % (rl["name"], _ptrunc(rl["pts"]),
                          rl["len"], TERR_JA.get(rl["terrace"], rl["terrace"]), rl["drop"])
                       for rl in rails)
             + "</tbody></table></div>")
    h.append('<p class="cap"><b>郭内の土留めは1本も置かない</b>(2026-08-23 に3本とも全廃)。'
             '⛔ <b>従前ここに書いていた「どの縁も落差が小さく、設計した壁はいずれも露出1m未満」は誤り</b>'
             '(2026-08-25 検図) — 上の表のとおり <b>%d本中 %d本の縁が落差 2m を超える</b>(最大 %.2fm)。'
             '全廃の理由は「落差が小さいから」ではなく、<b>2026-08-23 時点の面の高さでは壁が'
             '地中に埋まったから</b>である。⚠ <b>地盤を作り直した後の落差でこの判断を検め直していない</b> — '
             '落差3m級の縁を高さ%.2fmの四つ目垣だけで受ける形になっており、'
             '<code>sashizu.md</code> §3b の「縁ごとに測って表にしてから土留めか法面かを決める」を'
             '回し直す必要がある(<code>_pending</code> に立てた)。'
             '段の縁は法面(盛土1:%.1f/切土1:%.1f)で摺り付く。'
             '造成しない斜面へ向く生活面の法肩にだけ<b>竹垣(四つ目垣 h%.2f)</b>を回して、'
             '落差のある縁を素にしない。石垣が出るのは<b>外周の基壇だけ</b>(「外周の展開」)。</p>'
             % (len(rails), sum(1 for r in rails if r["drop"] > 2.0),
                max([r["drop"] for r in rails] or [0.0]), d["const"]["takegakiH"],
                d["const"]["batterFill"], d["const"]["batterCut"],
                d["const"]["takegakiH"]))
    h.append("</div>")

    plate(h, nx(), "取り合い(実装用)", "すべて設計値から自動算出 — 手で書き写さない")
    h.append(corners_table(d))
    h.append(joints_table(d))
    h.append(civil_table(d))
    h.append(mune_contacts_table(d))
    h.append(gate_parts_table(d))
    h.append('<p class="cap">基壇石垣は境界線上に垂直に立つ — 隣地・道の地形は動かせないので、'
             '高低差は基壇の露出として受ける(地形へこまめに追従して段を刻まない)。</p>')
    h.append("</div>")

    if "bom" in d:
        plate(h, nx(), "部材表", "在庫は docs/asset-catalog.md 照会済み。新造は edo-buzai(Blender)")
        h.append(bom_table(d))
        h.append("</div>")

    # ⚠ **裁定を仰ぐ項目を図に出す。** 2026-08-25 検図: `_pending` が html に一切出ておらず、
    #    ユーザー裁定待ちの3件のうち2件が図の上に無かった。図に無い項目はレビューで決まらない。
    # ⚠ **残余バケツを必ず置く。** 2026-08-25 検図: 接頭辞の完全一致で分類していたため
    #    34件中15件が黙って落ち、その中に「郭内の土留めの要否」という最重要の要判断があった。
    op9 = list(d["_pending"]["open"])
    yo = [x for x in op9 if "要判断" in x[:14]]
    ji = [x for x in op9 if "実装" in x[:12]]
    ch = [x for x in op9 if ("要調査" in x[:14] or "要通達" in x[:14])]
    cl = [x for x in op9 if x.startswith(("【解決済", "【裁定済"))]
    et = [x for x in op9 if x not in yo + ji + ch + cl]
    pr9 = program_check(d)
    if pr9:
        ng9 = [x for x in pr9 if x[3] is False and "任意" not in x[1]]
        nq9 = [x for x in pr9 if x[3] is None]
        plate(h, nx(), "在るべき役割との照合",
              "⭐ **外の錨** — `estate-types.md`「上屋敷が備える役割」の表を毎回読んで照合する"
              "(2026-08-26 土井 EDO-0013)")
        h.append('<p class="cap">⚠ <b>錨が無いと、役割と棟を同時に消せば検査が通る。</b>'
                 '当図の <code>program</code> ではなく<b>スキルの表</b>を読む。'
                 '%s</p>'
                 % (("<b>必須・望ましい はすべて満たしている。</b>" if not ng9 else
                     "⛔ <b>満たしていない必須・望ましいが %d件</b>: " % len(ng9)
                     + " / ".join("<b>%s</b>(%s・%s)" % (a, b, c) for a, b, c, _ in ng9))
                    + ("" if not nq9 else
                       " ⚠ <b>述語の無い役割が %d件</b>(%s)— <b>「?」で出す。○ にしない。</b>"
                       % (len(nq9), " / ".join(x[0] for x in nq9)))
                    + " ⛔ <b>2026-09-02: 判定を文字列一致から「物を数える述語」へ入れ替えた</b> — "
                    "考証の本文に「<b>当図に表役所という棟は無く</b>」と書いた瞬間に"
                    "「表役所=有る」と刷る型(否定文が検査を通す・当邸4例目)だった。"))
        h.append("<div class='tw'><table><thead><tr><th>役割</th><th>要否</th>"
                 "<th class='note'>典拠</th><th>当図</th></tr></thead><tbody>"
                 + "".join("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td>%s</td></tr>"
                           % (a, b, c, "?" if ok is None else
                              ("○" if ok else ("⛔" if "任意" not in b else "—")))
                           for a, b, c, ok in pr9)
                 + "</tbody></table></div>")
        h.append("</div>")

    plate(h, nx(), "裁定と宿題", "⭐ **この章の【要判断】はユーザーの裁定を待っている**")
    for ttl, xs, mk in (("⭐ ユーザーの裁定を仰ぐ", yo, "yo"),
                        ("実装で納める(図では閉じない)", ji, "ji"),
                        ("調査・通達の宿題", ch, "ch"),
                        ("⚠ その他(上のどれにも入らない)", et, "et"),
                        ("決着済み(記録として残す)", cl, "cl")):
        if not xs:
            continue
        h.append("<h3>%s(%d件)</h3><ol class='note'>%s</ol>"
                 % (ttl, len(xs), "".join("<li>%s</li>" % inline(x) for x in xs)))
    h.append('<p class="cap"><b>open %d件をすべて刷った</b>(裁定%d / 実装%d / 調査%d / その他%d / 決着済み%d)。'
             '正典は json <code>_pending.open</code>。'
             % (len(op9), len(yo), len(ji), len(ch), len(et), len(cl))
             + '⭐ <b>【要判断】は当方では閉じられない</b>(規則3 の免除など、'
               '不変則に関わるものを当方が自分に出すことはできない)。'
               '⛔ <b>分類は残余バケツ付き</b> — どれにも入らない件は「その他」に出る'
               '(2026-08-25 検図: 接頭辞の完全一致で 34件中15件が黙って落ちていた)。</p>')
    h.append("</div>")

    plate(h, nx(), "考証と決めごと")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, "改訂", "", "経緯はここに書かず git で追う ／ 先頭行が**この図を組んだ時点**"
          "(HEAD と、設計値・文章が未コミットかどうか)")
    h.append(history())
    h.append("</div>")

    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>okabe_sashizu.json</code> ／ '
             '文章 <code>okabe_kosho.md</code>。Y は海抜 m(Unity の Y がそのまま標高)。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    open(OUT, "w", encoding="utf-8").write("\n".join(h))
    # 算出値(切盛の量・造成しない坪数)を設計値ファイルへ書き戻す — 二重管理をやめる
    json.dump(d, open(JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %s (%.0f KB) — 図版 %d 面 — 建蔽率 %.1f%%" % (OUT, os.path.getsize(OUT) / 1024, _SVN[0], kp))
    if bad:
        print("⚠ 重なり %d 件 — 検図の前に直すこと" % len(bad))
    print("  run: 検図(edo-kosho / edo-kenzu) → ユーザーのレビュー → 実装 → 突き合わせ")


if __name__ == "__main__":
    main()
