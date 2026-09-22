#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""丹羽左京大夫上屋敷(niwa_sakyo)の指図を組む。

    python3 Tools/Sashizu/build_niwa_sakyo_sashizu.py

【読むもの】この生成器は**実装を読まない**。読むのは

    docs/Sashizu/niwa_sakyo_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/niwa_sakyo_kosho.md     … 文章の部(人が書く・現況形)
    docs/Sashizu/niwa_sakyo_dem.json     … 造成前の地盤(⭐ 正本 base_dem.json からの切り出し。
                                            書くのは Tools/Sashizu/build_base_dem.py の SLICES)
    docs/Sashizu/niwa_sakyo_edo_recon.json … 江戸期の復元の**手順の仕様**(人が書く)
    docs/Sashizu/niwa_sakyo_edo_world.json … 復元した面(build_niwa_sakyo_recon.py が書く派生物)
    docs/Sashizu/parcels.json            … 区画の正典(ユーザーの敷地割)

【この邸ならではの作り】
  ・グリッドは**世界軸そのもの**(u=東+ / v=北+、原点=表門の芯)。棟が yaw 0/90 でしか
    置かれていないので回転フレームは要らない。⚠ **区画の辺は世界軸に平行ではない** —
    2026-08-30 の引き直しで北帯の南辺が斜めの2辺に割れた(9頂点)。グリッドは辺に沿わない。
  ・**造成をしない屋敷**(NaturalMode)。terraces が空なので設計地盤 ≡ 現況地形。
    切盛図は全域が「造成しない」になる — 代わりに**棟の座と地形の差(埋没)**を描く。
  ・断面は json の `sections`(軸と位置だけ)から DEM を直に切って引く。
    ⛔ 何を切るかは手で書かない(sashizu.md §3c)。

【図版】其一 敷地全体/其二 現況図/其三 切盛図/其四 棟の接地/其五 動線図/
        其六 外周の展開/其七 取り合い(表門)/其八〜 断面イ〜ヌ/
        明治16年の実測 vs 現況DEM(平面 + 東西断面 + **南北断面**)/
        **裁定図(P-1)**(位置図+現況 / 三案 同一縮尺 / 断面の対比 / 表 / 6点セット)/
        以降 表と考証。⛔ 図版番号は `nx()` が振るので**手で数えない**。

【出す前の機械検査】矩形の重なり・区画の出入り・規則3の埋没・取り合いの規約(`checks`)/
        図の文字のはみ出し(`check_text_overflow`)/ **強調 `**` の偶奇**(`check_emphasis`)/
        **組み上がった html に生の `**` が残っていないか**(`check_raw_emphasis`)。
"""
import html
import json
import math
import os
import re
import subprocess

import sashizu_lib
from sashizu_lib import R, _pat, _SVN, Proj, dem_color, dem_legend, _iso, cutfill_legend
from cliff_polyline import Cliff

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "niwa_sakyo_sashizu.json")
MD = os.path.join(DOC, "niwa_sakyo_kosho.md")
DEMF = os.path.join(DOC, "niwa_sakyo_dem.json")
RECON = os.path.join(DOC, "niwa_sakyo_edo_recon.json")     # 復元の手順の仕様(人が書く)
WORLD = os.path.join(DOC, "niwa_sakyo_edo_world.json")     # 復元した面(生成器が書く派生物)
PARCELS = os.path.join(DOC, "parcels.json")
OUT = os.path.join(DOC, "niwa_sakyo_sashizu.html")
TSUBO = 3.305785
VEX = 2.4      # 断面の垂直倍率


# ---------------------------------------------------------------- markdown
def inline(s):
    return sashizu_lib.inline(s)


def check_emphasis(*objs):
    """⛔ **強調 `**` の偶奇を機械で検める。**奇数個あると、そこから先の強調が
    反転して図と本文の意味が裏返る(2026-09-01 検図 K14: `pending` P-1 の本文が
    21 個で、以降の「⛔」の強調がすべて外れていた)。目視では見つからない。
    ⭐ json の全文字列と kosho.md の全行を見る。"""
    out = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + "/%d" % i)
        elif isinstance(o, str) and o.count("**") % 2:
            out.append("%s(%d 個)「%s…」" % (path, o.count("**"), o[:26]))
    for k, o in objs:
        walk(o, k)
    return out


def check_raw_emphasis(body):
    """⛔ **組み上がった html に `**` が生で残っていないか。**
    `check_emphasis` は偶奇しか見ないので、`inline()` を通し忘れた欄
    (2026-09-01 検図 Kz-1: 其二十四 実装の順序の `work` を `html.escape` だけで出していた)
    は釣り合ったまま素通りする。⭐ **最終成果物の側から数えるのが唯一確実な検査。**"""
    # ⚠ `<style>` の中は sashizu.css のコメントで、図にも本文にも出ない — 数えない。
    #   位置を保つため、同じ長さの空白へ潰す。
    b = re.sub(r"<style>.*?</style>", lambda m: " " * (m.end() - m.start()), body, flags=re.S)
    out = []
    for m in re.finditer(r"\*\*", b):
        a = max(0, m.start() - 40)
        out.append("html:%d 付近「…%s…」" % (m.start(), b[a:m.start() + 20]))
    return out


def md2html(text):
    return sashizu_lib.md2html(text, inline=inline)


# ---------------------------------------------------------------- 作図の土台
def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, html.escape(label)),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.6"/></pattern>'
            '<pattern id="bu%d" width="7" height="7" patternUnits="userSpaceOnUse">'
            '<path d="M0,7 L7,0" stroke="var(--shu)" stroke-width="1.1" opacity="0.75"/></pattern>'
            '<pattern id="na%d" width="6" height="6" patternUnits="userSpaceOnUse">'
            '<path d="M0,0 L6,6" stroke="var(--nagaya)" stroke-width="0.7" opacity="0.5"/></pattern>'
            '<clipPath id="cl%d"><rect x="0" y="0" width="%.0f" height="%.0f"/></clipPath></defs>'
            % (_SVN[0], _SVN[0], _SVN[0], _SVN[0], W, H),
            '<g clip-path="url(#cl%d)">' % _SVN[0]]


ENDSVG = "</g></svg>"


def _bur():
    return "url(#bu%d)" % _SVN[0]


def _nag():
    return "url(#na%d)" % _SVN[0]


def T(x, y, s, cls="sl", anchor=None, fs=None, fill=None, rot=None):
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
    if rot is not None:
        a += ' transform="rotate(%.1f %.1f %.1f)"' % (rot, x, y)
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


def PL(pts, stroke="var(--ink)", sw=1.0, fill="none", dash=None, op=None, close=False):
    dd = "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")
    a = '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f"' % (dd, fill, stroke, sw)
    if dash:
        a += ' stroke-dasharray="%s"' % dash
    if op is not None:
        a += ' opacity="%.2f"' % op
    return a + "/>"


def CIR(x, y, r, fill="none", stroke="var(--ink)", sw=1.0):
    return ('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%.2f"/>'
            % (x, y, r, fill, stroke, sw))


def poly_area(P):
    s = 0.0
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        s += a[0] * b[1] - b[0] * a[1]
    return abs(s) / 2.0


def pip(P, x, z):
    c = False
    n = len(P)
    for i in range(n):
        (ax, az), (bx, bz) = P[i], P[(i + 1) % n]
        if (az > z) != (bz > z) and x < (bx - ax) * (z - az) / (bz - az) + ax:
            c = not c
    return c


# ---------------------------------------------------------------- 地形(正本からの切り出し)
class DEM(object):
    """世界座標2m格子の面。`key` で同じファイルの中の別の面を選ぶ
    (`niwa_sakyo_edo_world.json` は `h`=A案の復元面 / `hB`=B案の復元面 を持つ)。"""

    def __init__(self, path, key="h"):
        d = json.load(open(path, encoding="utf-8"))
        self.d = d
        self.key = key
        self.x0, self.z0, self.st = d["x0"], d["z0"], d["step"]
        self.nx, self.nz, self.h = d["nx"], d["nz"], d[key]

    def grid(self):
        """`_iso`(等高線)へ渡す辞書。選んだ面を `h` として見せる。"""
        return {"x0": self.x0, "z0": self.z0, "step": self.st,
                "nx": self.nx, "nz": self.nz, "h": self.h}

    def __call__(self, x, z):
        fx = (x - self.x0) / self.st
        fz = (z - self.z0) / self.st
        i0 = min(max(int(math.floor(fx)), 0), self.nx - 2)
        j0 = min(max(int(math.floor(fz)), 0), self.nz - 2)
        tx, tz = fx - i0, fz - j0
        a, b = self.h[j0][i0], self.h[j0][i0 + 1]
        c, e = self.h[j0 + 1][i0], self.h[j0 + 1][i0 + 1]
        return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + e * tx) * tz


# ---------------------------------------------------------------- 幾何(区画・辺・門)
class Geo(object):
    """区画の辺・表門・囲いの区間。**すべて多角形から導く**(数値を書き写さない)。"""

    def __init__(self, d, P):
        self.P = P
        self.N = len(P)
        self.d = d
        self.sa = self._signed_area()
        g = d["gate"]
        e = g["edge"]
        a, b = P[e], P[(e + 1) % self.N]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        self.gdir = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        t = (g["atZ"] - a[1]) / self.gdir[1]
        self.gate = (a[0] + self.gdir[0] * t, a[1] + self.gdir[1] * t)
        self.gh = g["plan"]["gateHalf"]
        self.gA, self.gB = a, b

    def _signed_area(self):
        s = 0.0
        for i in range(self.N):
            a, b = self.P[i], self.P[(i + 1) % self.N]
            s += a[0] * b[1] - b[0] * a[1]
        return s / 2.0

    def edge(self, i):
        a, b = self.P[i], self.P[(i + 1) % self.N]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return a, b, L, ((b[0] - a[0]) / L, (b[1] - a[1]) / L)

    def outward(self, i):
        _, _, _, dd = self.edge(i)
        n = (-dd[1], dd[0])
        if self.sa < 0:
            n = (-n[0], -n[1])
        return (-n[0], -n[1])

    def wall_ends(self):
        """表門の左右の塀の端(門の芯 ∓ (gateHalf + `const.gatePad`))。
        ⛔ 逃げの量を literal で書かない — `const.gatePad` が唯一の出どころで、
        取り合い J1/J2 の隙間もそこから引く(規則4)。"""
        m = self.gh + self.d["const"]["gatePad"]
        gl = (self.gate[0] - self.gdir[0] * m, self.gate[1] - self.gdir[1] * m)
        gr = (self.gate[0] + self.gdir[0] * m, self.gate[1] + self.gdir[1] * m)
        return gl, gr

    def run_span(self, r):
        """run の区間(世界座標の始点・終点)。表門の辺だけ門で割れる。
        ⛔ **頂点の番号で分岐しない** — 区画を引き直すと番号がずれる(2026-09-01 に実際にずれた)。
        門で割れる区間は `gateL` / `gateR` という**役の名**で指す。"""
        i = r["edge"]
        a, b, L, dd = self.edge(i)
        if r.get("to") == "gateL":
            return a, self.wall_ends()[0]
        if r.get("from") == "gateR":
            return self.wall_ends()[1], b
        return a, b


def _seg_dist(p, a, b):
    vx, vz = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vz * vz
    if L2 < 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vz) / L2))
    return math.hypot(p[0] - (a[0] + vx * t), p[1] - (a[1] + vz * t))


def edge_touch(geo, ei, Q, tol=0.6, ds=0.5):
    """辺 i のうち、多角形 Q の輪郭に `tol` 以内で**接している区間**。
    返すのは (長さ, 始点の s, 終点の s)。⛔ **辺が丸ごと共有とは限らない** —
    2026-09-01 の検図 K6 で、辺7(山王坂)の東の 4 割が町屋の区画と背中合わせだと分かった。
    ⛔ 区間を手で持たず、**区画どうしの幾何から毎回測る**(規則4)。"""
    a, b, L, dd = geo.edge(ei)
    n = int(L / ds)
    hit = []
    for k in range(n + 1):
        s = k * ds
        p = (a[0] + dd[0] * s, a[1] + dd[1] * s)
        if min(_seg_dist(p, Q[i], Q[(i + 1) % len(Q)]) for i in range(len(Q))) <= tol:
            hit.append(s)
    if not hit:
        return 0.0, None, None
    return len(hit) * ds, hit[0], hit[-1]


def dobei_pieces(L, nom):
    n = max(1, int(round(L / nom)))
    return n, L / n


def nagaya_chain(L, c, lr):
    """盲長屋の鎖: n = round(L/c)、実延長 = lr + c×(n-2) + lr(n=1 なら c)。"""
    n = max(1, int(round(L / c)))
    tot = c if n == 1 else (2 * lr + c * (n - 2))
    return n, tot, (L - tot) / 2.0


# ---------------------------------------------------------------- 棟の接地
def foot(o):
    """外形の X / Z の半寸。"""
    return o["w"] / 2.0, o["d"] / 2.0


def seat_of(o, dem, sink):
    """CenterSeat: 中心と四隅・四辺中点の9点の地形の最小値 − sink。"""
    ex, ez = foot(o)
    x, z = o["pos"]
    g = [dem(x + i * ex, z + j * ez) for i in (-1, 0, 1) for j in (-1, 0, 1)]
    return min(g) - sink


def nat_range(o, dem, n=9):
    ex, ez = foot(o)
    x, z = o["pos"]
    vs = [dem(x - ex + 2 * ex * i / (n - 1.0), z - ez + 2 * ez * j / (n - 1.0))
          for i in range(n) for j in range(n)]
    return min(vs), max(vs)


def all_bodies(d):
    out = []
    for m in d["munes"]:
        out.append(("棟", m))
    for s in d["service"]:
        out.append(("付属", s))
    return out


def sink_of(d, m):
    """駒ごとの沈め代。門だけ `gateSink` を使う。"""
    return m.get("sink", d["const"]["sink"])


def gate_body(d, geo):
    """表門を棟と同じ形の駒として扱う。**門も CenterSeat で地形へ載るので規則3の対象**。
    ⚠ 門は yaw 90 なので X = monD / Z = monW(部材の素の X が塀の走り方向へ回る)。"""
    gp = d["gate"]["plan"]
    return ("門", {"name": "Kmon", "label": "表門", "pos": [geo.gate[0], geo.gate[1]],
                   "w": gp["monD"], "d": gp["monW"], "h": gp["monH"],
                   "asset": d["gate"]["asset"], "seat": d["gate"]["seat"],
                   "sink": d["gate"]["sink"], "acc": d["gate"]["acc"]})


def seat_bodies(d, geo):
    """**接地・埋没を見るときの集合** = 棟 + 付属 + 表門。
    ⛔ 平面図の集合(`all_bodies`)とは別 — 門は平面では門として別に描くので二重に出さない。"""
    return all_bodies(d) + [gate_body(d, geo)]


# ---------------------------------------------------------------- 断面の切り線
def sec_line(sec):
    """断面の切り線を **(起点, 単位方向, 長さ)** に正規化する。EW / NS / DIAG を同じ形に落とす。
    こうしておくと、棟・run・門の当たりを軸ごとに場合分けせずに一つの手で取れる。"""
    if sec["axis"] == "EW":
        return (sec["x0"], sec["at"]), (1.0, 0.0), sec["x1"] - sec["x0"]
    if sec["axis"] == "NS":
        return (sec["at"], sec["z0"]), (0.0, 1.0), sec["z1"] - sec["z0"]
    p0, p1 = sec["p0"], sec["p1"]
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    return (p0[0], p0[1]), ((p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L), L


def sec_pt(sec, c):
    (px, pz), (dx, dz), _ = sec_line(sec)
    return px + dx * c, pz + dz * c


def sec_ends(sec):
    (px, pz), (dx, dz), L = sec_line(sec)
    return (px, pz), (px + dx * L, pz + dz * L)


def clip_rect(sec, a0, b0, a1, b1):
    """切り線 × 軸平行の矩形。切り線上の区間 (c0, c1) を返す(当たらなければ None)。"""
    (px, pz), (dx, dz), L = sec_line(sec)
    lo, hi = 0.0, L
    for o, dd, q0, q1 in ((px, dx, a0, a1), (pz, dz, b0, b1)):
        if abs(dd) < 1e-9:
            if o < q0 - 1e-9 or o > q1 + 1e-9:
                return None
            continue
        t0, t1 = (q0 - o) / dd, (q1 - o) / dd
        lo = max(lo, min(t0, t1))
        hi = min(hi, max(t0, t1))
    return (lo, hi) if hi > lo else None


def sec_body_span(sec, m):
    ex, ez = foot(m)
    x, z = m["pos"]
    return clip_rect(sec, x - ex, z - ez, x + ex, z + ez)


def sec_seg_hit(sec, a, b):
    """切り線 × 線分 ab。切り線上の位置 c を返す(平行・区間外は None)。"""
    (px, pz), (dx, dz), L = sec_line(sec)
    sx, sz = b[0] - a[0], b[1] - a[1]
    den = dx * sz - dz * sx
    if abs(den) < 1e-9:
        return None
    qx, qz = a[0] - px, a[1] - pz
    c = (qx * sz - qz * sx) / den
    u = (qx * dz - qz * dx) / den
    if -1e-6 <= u <= 1 + 1e-6 and 0.0 <= c <= L:
        return c
    return None


def sec_run_along(sec, a, b, tol=0.75):
    """切り線が run に**重なって**いるか(縦断)。重なっていれば run の始点の c を返す。
    ⚠ tol は塀の厚み(`dobeiT` 1.15m)の半分ぶん。これより離れていれば『平行だが切っていない』"""
    (px, pz), (dx, dz), L = sec_line(sec)
    sx, sz = b[0] - a[0], b[1] - a[1]
    sl = math.hypot(sx, sz)
    if sl < 1e-9 or abs(dx * sz - dz * sx) / sl > 1e-3:
        return None                       # 平行でない
    off = abs((a[0] - px) * dz - (a[1] - pz) * dx)
    if off > tol:
        return None                       # 平行だが離れている
    return (a[0] - px) * dx + (a[1] - pz) * dz


def body_label(o, pj, m, k, wpx, hpx, cx, cy, sub=None):
    """棟の名札。**外形の中に収まらない小さい駒は、引き出し線で外へ出して段違いに置く。**
    土蔵3棟・家臣長屋2棟が重なって読めなかった(2026-08-30 自己検図)。"""
    if wpx >= 52 and hpx >= 18:
        o.append(T(cx, cy + 3, m["label"], cls="anS2"))
        if sub:
            o.append(T(cx, cy + 15, sub, cls="jo", anchor="middle", fill="var(--shu)"))
        return
    dy = 18 + (k % 3) * 26
    o.append(LN(cx, cy, cx, cy - dy + 4, stroke="var(--rule)", sw=0.7))
    o.append(T(cx, cy - dy, m["label"], cls="anS2"))
    if sub:
        o.append(T(cx, cy - dy + 10, sub, cls="jo", anchor="middle", fill="var(--shu)"))


# ---------------------------------------------------------------- 其一 敷地全体
YAKU_COL = {"表向": "var(--shu)", "奥向": "var(--roka)", "役方": "var(--hei)", "勝手": "var(--nagaya)"}


def haichi_svg(d, geo, dem, kan, W=940.0):
    P = geo.P
    x0, x1 = min(p[0] for p in P) - 26, max(p[0] for p in P) + 26
    z0, z1 = min(p[1] for p in P) - 26, max(p[1] for p in P) + 26
    pj = Proj(x0, x1, z0, z1, W=W, top=26, bottom=34)
    o = _sv(pj.W, pj.H, "%s 敷地全体 配置図" % kan)
    X, Y = pj.X, pj.Y
    o.append(R(0, 0, pj.W, pj.H, fill="var(--paper)"))
    # 隣地
    for nb in json.load(open(PARCELS, encoding="utf-8"))["parcels"]:
        if nb["id"] == d["parcelId"] or not nb.get("pts"):
            continue
        pts = [(X(q[0]), Y(q[1])) for q in nb["pts"]]
        if all(p[0] < -60 or p[0] > pj.W + 60 or p[1] < -60 or p[1] > pj.H + 60 for p in pts):
            continue
        o.append(PL(pts, stroke="var(--shu)", sw=0.8, dash="5 4", op=0.5, close=True))
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        if 0 < cx < pj.W and 0 < cy < pj.H:
            o.append(T(cx, cy, nb["label"], cls="anS2", fill="var(--shu)"))
    # 敷地
    poly = [(X(q[0]), Y(q[1])) for q in P]
    o.append(PL(poly, stroke="var(--ink)", sw=1.6, fill="var(--paper2)", close=True, op=0.85))
    # 外周の run
    for r in d["runs"]:
        a, b = geo.run_span(r)
        col = "var(--nagaya)" if r["kind"] == "Nagaya" else "var(--hei)"
        sw = 5.0 if r["kind"] == "Nagaya" else 2.6
        o.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), stroke=col, sw=sw, cap="butt", op=0.9))
    # 囲いの無い辺
    for e in d["edges"]:
        if e["run"] is None:
            a, b, L, _ = geo.edge(e["i"])
            o.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), stroke="var(--shu)", sw=2.4, dash="3 5"))
            o.append(T((X(a[0]) + X(b[0])) / 2, (Y(a[1]) + Y(b[1])) / 2 + 13,
                       "辺%d 囲い無し %.1fm" % (e["i"], L), cls="anS2", fill="var(--shu)"))
    # 辺の番号(囲いの無い辺は上で書いたので飛ばす)
    for e in d["edges"]:
        if e["run"] is None:
            continue
        a, b, L, dd = geo.edge(e["i"])
        ow = geo.outward(e["i"])
        t = 0.85 if e["i"] == d["gate"]["edge"] else 0.5     # 門の辺は名札が門・断面線と当たるので寄せる
        mx = a[0] + (b[0] - a[0]) * t + ow[0] * 9
        mz = a[1] + (b[1] - a[1]) * t + ow[1] * 9
        o.append(T(X(mx), Y(mz), "辺%d %.1fm" % (e["i"], L), cls="jo", anchor="middle"))
    # 建屋
    for k, (kind, m) in enumerate(all_bodies(d)):
        ex, ez = foot(m)
        x, z = m["pos"]
        col = YAKU_COL.get(m.get("yaku"), "var(--ishi)")
        o.append(R(X(x - ex), Y(z + ez), pj.L(2 * ex), pj.L(2 * ez),
                   fill=col, stroke="var(--ink)", sw=0.8, op=0.30))
        body_label(o, pj, m, k, pj.L(2 * ex), pj.L(2 * ez), X(x), Y(z))
    # 井戸
    for w in d["wells"]:
        o.append(CIR(X(w["pos"][0]), Y(w["pos"][1]), 4.0, fill="var(--ike)", stroke="var(--hei)", sw=1.0))
        o.append(T(X(w["pos"][0]) + 7, Y(w["pos"][1]) + 3, w["label"], cls="jo"))
    # 表門
    gx, gz = geo.gate
    ow = geo.outward(d["gate"]["edge"])
    gd = geo.gdir
    hw = pj.L(geo.gh)
    o.append(LN(X(gx - gd[0] * geo.gh), Y(gz - gd[1] * geo.gh),
                X(gx + gd[0] * geo.gh), Y(gz + gd[1] * geo.gh), stroke="var(--shu)", sw=5.0, cap="butt"))
    o.append(PL([(X(gx), Y(gz)), (X(gx + ow[0] * 11 + gd[0] * 5), Y(gz + ow[1] * 11 + gd[1] * 5)),
                 (X(gx + ow[0] * 11 - gd[0] * 5), Y(gz + ow[1] * 11 - gd[1] * 5))],
                stroke="var(--shu)", sw=1.2, fill="var(--shu)", op=0.5, close=True))
    o.append(T(X(gx) - 12, Y(gz) - 16, d["gate"]["name"], cls="anG", anchor="end"))
    # 番所
    bs = d["gate"]["plan"]["bansho"]
    uh = (ow[1], -ow[0])
    for s in (1, -1):
        bx = gx + uh[0] * s * bs["offset"] + ow[0] * bs["extrude"]
        bz = gz + uh[1] * s * bs["offset"] + ow[1] * bs["extrude"]
        o.append(R(X(bx - bs["w"] / 2), Y(bz + bs["d"] / 2), pj.L(bs["w"]), pj.L(bs["d"]),
                   fill="var(--shu)", stroke="var(--ink)", sw=0.7, op=0.35))
    # 断面の切り位置(**キープラン** — 軸に関わらず起点→終点で引く)
    for s in d["sections"]:
        (ax0, az0), (ax1, az1) = sec_ends(s)
        o.append(LN(X(ax0), Y(az0), X(ax1), Y(az1),
                    stroke="#7A2E1E", sw=0.8, dash="10 3 2 3", op=0.75))
        o.append(T(X(ax1) + (5 if ax1 >= ax0 else -5), Y(az1) + 3, s["name"][2], cls="jo",
                   fill="#7A2E1E", anchor="start" if ax1 >= ax0 else "end"))
    # 方位・スケール
    o.append(T(pj.W - 22, 20, "N", cls="big", anchor="middle"))
    o.append(LN(pj.W - 22, 24, pj.W - 22, 44, stroke="var(--ink)", sw=1.2))
    o.append(PL([(pj.W - 26, 30), (pj.W - 22, 22), (pj.W - 18, 30)], stroke="var(--ink)", sw=1.2))
    sb = 50.0
    o.append(LN(24, pj.H - 16, 24 + pj.L(sb), pj.H - 16, stroke="var(--ink)", sw=1.6))
    o.append(T(24 + pj.L(sb) / 2, pj.H - 4, "%.0f m" % sb, cls="jo", anchor="middle"))
    o.append(T(14, 18, "%s　敷地全体 配置図" % kan, cls="big"))
    o.append(ENDSVG)
    return "".join(o)


# ---------------------------------------------------------------- 其二 現況図
def genkyo_svg(d, geo, dem, kan, W=940.0):
    P = geo.P
    x0, x1 = min(p[0] for p in P) - 20, max(p[0] for p in P) + 20
    z0, z1 = min(p[1] for p in P) - 20, max(p[1] for p in P) + 20
    pj = Proj(x0, x1, z0, z1, W=W, top=26, bottom=30)
    X, Y = pj.X, pj.Y
    o = _sv(pj.W, pj.H, "%s 現況図" % kan)
    o.append(R(0, 0, pj.W, pj.H, fill="var(--paper)"))
    st = dem.st
    cell = pj.L(st) + 0.6
    jz0 = max(0, int((z0 - dem.z0) / st))
    jz1 = min(dem.nz, int((z1 - dem.z0) / st) + 2)
    ix0 = max(0, int((x0 - dem.x0) / st))
    ix1 = min(dem.nx, int((x1 - dem.x0) / st) + 2)
    for jz in range(jz0, jz1):
        z = dem.z0 + jz * st
        for ix in range(ix0, ix1):
            x = dem.x0 + ix * st
            o.append(R(X(x), Y(z + st), cell, cell, fill=dem_color(dem.h[jz][ix]), op=0.92))
    # 等高線
    lo = int(min(min(r[ix0:ix1]) for r in dem.h[jz0:jz1]) // 2 * 2)
    hi = int(max(max(r[ix0:ix1]) for r in dem.h[jz0:jz1]) // 2 * 2 + 2)
    for lv in range(lo, hi + 1, 2):
        segs = _iso(dem.d, lv)
        thick = (lv % 10 == 0)
        for (a, b) in segs:
            if not (x0 <= a[0] <= x1 and z0 <= a[1] <= z1):
                continue
            o.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), stroke="var(--ink)",
                        sw=1.1 if thick else 0.45, op=0.55 if thick else 0.32))
    # 隣地
    for nb in json.load(open(PARCELS, encoding="utf-8"))["parcels"]:
        if nb["id"] == d["parcelId"] or not nb.get("pts"):
            continue
        pts = [(X(q[0]), Y(q[1])) for q in nb["pts"]]
        if all(p[0] < -40 or p[0] > pj.W + 40 or p[1] < -40 or p[1] > pj.H + 40 for p in pts):
            continue
        o.append(PL(pts, stroke="var(--shu)", sw=0.9, dash="5 4", op=0.65, close=True))
    o.append(PL([(X(q[0]), Y(q[1])) for q in P], stroke="var(--ink)", sw=2.0, close=True))
    # 棟の位置(輪郭だけ)
    for kind, m in all_bodies(d):
        ex, ez = foot(m)
        x, z = m["pos"]
        o.append(R(X(x - ex), Y(z + ez), pj.L(2 * ex), pj.L(2 * ez),
                   fill="none", stroke="var(--ink)", sw=0.9, dash="3 2"))
    gx, gz = geo.gate
    o.append(CIR(X(gx), Y(gz), 4.5, fill="var(--shu)", stroke="var(--paper)", sw=1.0))
    for s in d["sections"]:
        (ax0, az0), (ax1, az1) = sec_ends(s)
        o.append(LN(X(ax0), Y(az0), X(ax1), Y(az1),
                    stroke="#7A2E1E", sw=0.8, dash="10 3 2 3", op=0.8))
        o.append(T(X(ax1) + (5 if ax1 >= ax0 else -5), Y(az1) + 3, s["name"][2], cls="jo",
                   fill="#7A2E1E", anchor="start" if ax1 >= ax0 else "end"))
    o.append(T(14, 18, "%s　現況図(造成前の地形)" % kan, cls="big"))
    sb = 50.0
    o.append(LN(24, pj.H - 14, 24 + pj.L(sb), pj.H - 14, stroke="var(--ink)", sw=1.6))
    o.append(T(24 + pj.L(sb) / 2, pj.H - 3, "%.0f m" % sb, cls="jo", anchor="middle"))
    o.append(ENDSVG)
    return "".join(o)


# ---------------------------------------------------------------- 其三 切盛図
def kirimori_svg(d, geo, dem, kan, W=940.0):
    """当邸は段を持たないので Δ は全域ゼロ。**素地(造成しない)の地の色**で塗り、
    区画の中を『触らない』ことが図の上で読めるようにする。"""
    P = geo.P
    x0, x1 = min(p[0] for p in P) - 20, max(p[0] for p in P) + 20
    z0, z1 = min(p[1] for p in P) - 20, max(p[1] for p in P) + 20
    pj = Proj(x0, x1, z0, z1, W=W, top=26, bottom=30)
    X, Y = pj.X, pj.Y
    o = _sv(pj.W, pj.H, "%s 切盛図" % kan)
    o.append(R(0, 0, pj.W, pj.H, fill="var(--paper)"))
    st = dem.st
    cell = pj.L(st) + 0.6
    n_in = 0
    for jz in range(dem.nz):
        z = dem.z0 + jz * st
        if not (z0 <= z <= z1):
            continue
        for ix in range(dem.nx):
            x = dem.x0 + ix * st
            if not (x0 <= x <= x1):
                continue
            inp = pip(P, x, z)
            if inp:
                n_in += 1
            o.append(R(X(x), Y(z + st), cell, cell,
                       fill="var(--nomove)" if inp else "var(--paper2)", op=1.0 if inp else 0.55))
    o.append(PL([(X(q[0]), Y(q[1])) for q in P], stroke="var(--ink)", sw=2.0, close=True))
    o.append(T(pj.W / 2, pj.H / 2 - 26, "切　盛　な　し", cls="zn", fs=26))
    o.append(T(pj.W / 2, pj.H / 2 - 2, "Δ = 設計地盤 − 現況 = 0.00 m(区画の全域)", cls="anS2"))
    o.append(T(pj.W / 2, pj.H / 2 + 18, "囲いも棟も置いた点の地形にそのまま載る(NaturalMode)", cls="anS2"))
    # 棟だけは地形との差が出る(座は9点の最小値)
    for k, (kind, m) in enumerate(all_bodies(d)):
        ex, ez = foot(m)
        x, z = m["pos"]
        y = seat_of(m, dem, sink_of(d, m))
        nlo, nhi = nat_range(m, dem)
        bad = nhi - y
        col = "var(--cut4)" if bad > 3 else ("var(--cut2)" if bad > 0.5 else "var(--nomove)")
        o.append(R(X(x - ex), Y(z + ez), pj.L(2 * ex), pj.L(2 * ez),
                   fill=col, stroke="var(--ink)", sw=0.9, op=0.85))
        body_label(o, pj, m, k, pj.L(2 * ex), pj.L(2 * ez), X(x), Y(z) - 4,
                   sub="埋没 %.1fm" % bad)
    o.append(T(14, 18, "%s　切盛図(造成しない)" % kan, cls="big"))
    o.append(T(14, pj.H - 8, "区画内 %d セル すべて Δ=0.00 m ／ 塗ってあるのは棟の座と地形の差(=埋没)"
               % n_in, cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


# ---------------------------------------------------------------- 其四 棟の接地
def seat_svg(d, geo, dem, kan, W=940.0):
    """棟ごとに 座・地形の最小/最大・埋没を一本の棒で並べる。CLAUDE.md 規則3 の合否が読める図。
    ⭐ **表門も同じ CenterSeat で地形へ載るので、この図と表に含める**(2026-08-30 検図 K-11)。"""
    B = seat_bodies(d, geo)
    n = len(B)
    lm, rm, top, bot = 118.0, 74.0, 62.0, 44.0    # top は棟名+埋没の2行ぶんを空ける
    bw = (W - lm - rm) / n
    lo = min(min(nat_range(m, dem)[0], seat_of(m, dem, sink_of(d, m))) for _, m in B) - 1.5
    hi = max(nat_range(m, dem)[1] for _, m in B) + 1.5
    Hh = 300.0
    o = _sv(W, Hh + top + bot, "%s 棟の接地" % kan)
    o.append(R(0, 0, W, Hh + top + bot, fill="var(--paper)"))

    def PY(y):
        return top + Hh - (y - lo) / (hi - lo) * Hh
    for y in range(int(lo // 2 * 2), int(hi) + 3, 2):
        if not (lo <= y <= hi):
            continue
        o.append(LN(lm - 6, PY(y), W - rm + 6, PY(y), stroke="var(--rule)", sw=0.7))
        o.append(T(lm - 10, PY(y) + 3, "%d m" % y, cls="jo", anchor="end"))
    for k, (kind, m) in enumerate(B):
        cx = lm + bw * (k + 0.5)
        y = seat_of(m, dem, sink_of(d, m))
        nlo, nhi = nat_range(m, dem)
        o.append(R(cx - bw * 0.30, PY(nhi), bw * 0.60, PY(nlo) - PY(nhi),
                   fill="var(--dan2)", stroke="var(--rule)", sw=0.7))
        bad = nhi - y
        if bad > 0.5:
            o.append(R(cx - bw * 0.30, PY(nhi), bw * 0.60, PY(y) - PY(nhi), fill=_bur(), op=0.9))
        o.append(LN(cx - bw * 0.36, PY(y), cx + bw * 0.36, PY(y), stroke="var(--shu)", sw=2.2))
        o.append(T(cx, PY(y) + 13, "座 %.1f" % y, cls="jo", anchor="middle", fill="var(--shu)"))
        # 名札は棒の幅(約 75px)に収まらないので**段違い**に置く(隣どうしが重なる)
        o.append(T(cx, top - 34 + (k % 2) * 13, m["label"], cls="anS2"))
        o.append(T(cx, top - 8, "埋没 %.1fm" % bad, cls="jo", anchor="middle",
                   fill="var(--shu)" if bad > 0.5 else "var(--dim)"))
    o.append(T(14, 18, "%s　棟の接地(座と外形の下の地形)" % kan, cls="big"))
    o.append(T(14, Hh + top + 22, "灰の棒 = 外形の下の自然地形の最小〜最大 ／ 朱の線 = 棟の座"
                                  "(9点の最小値 − 沈め代) ／ 斜線 = 地中に入る部分", cls="jo"))
    o.append(T(14, Hh + top + 36, "CLAUDE.md 規則3 の合格は 埋没 ≤ 0.5m", cls="jo", fill="var(--shu)"))
    o.append(ENDSVG)
    return "".join(o)


# ---------------------------------------------------------------- 其五 動線図
ROUTE_COL = {"shu": "var(--shu)", "roka": "var(--roka)", "nagaya": "var(--nagaya)",
             "take": "var(--take)", "hei": "var(--hei)"}


def dousen_svg(d, geo, dem, kan, W=940.0):
    """⚠ **北の帯だけを切り出す。** 動線も棟も z>795 に集まっていて、南の脚(z 678〜802)まで
    描くと図の三分の二が白紙になる。**南の脚に動線が一本も無いこと自体が読みどころ**なので、
    切り出した旨と欠けている範囲を図中に明記する。"""
    P = geo.P
    x0, x1 = min(p[0] for p in P) - 20, max(p[0] for p in P) + 20
    z0, z1 = 795.0, max(p[1] for p in P) + 20
    # ⛔ 注記は**1本1行**にする。1行に並べると図の右端で文字が切れる(2026-08-30 自己検図)
    MET = [(r, route_metrics(d, r, dem)) for r in d["routes"]]
    # ⛔ 直線は 段数×踏面、折返しは その半分+踊り場1枚(検図 L1/L2)。式は kaidan_need に一本化。
    ng = []
    for r, m in MET:
        if m[6]:
            continue
        nst, rq, half = kaidan_need(m[5][0], d["const"])
        ng.append("%s: 落差 %.1f m を水平 %.1f m で降りる(1:%.2f・%d 段)"
                  "　直線に要る %.1f m ／ 折返し %.1f m → %s"
                  % (r["label"], m[5][0], m[5][1], m[5][1] / m[5][0], nst, rq, half,
                     "水平は足りる(余裕 %+.1f m・踊り場の幅は未検証)" % (m[5][1] - half)
                     if m[5][1] >= half else "折返しでも足りない"))
    # ⛔ 裁定待ちの一文は **json の `saitei.P-1.block` が唯一の出どころ**(規則4)。
    #    図は markdown を解さないので `_wrap` で折る(fs=11 なので幅を 9.5/11 に縮めて測る)。
    blk = _wrap(sai(d)["block"], "jo", (W - 40) * 9.5 / 11.0)
    pj = Proj(x0, x1, z0, z1, W=W, top=44 + 13 * (len(ng) + len(blk)), bottom=44)
    X, Y = pj.X, pj.Y
    o = _sv(pj.W, pj.H, "%s 動線図" % kan)
    o.append(R(0, 0, pj.W, pj.H, fill="var(--paper)"))
    o.append(PL([(X(q[0]), Y(q[1])) for q in P], stroke="var(--ink)", sw=1.4,
                fill="var(--paper2)", close=True, op=0.8))
    for k, (kind, m) in enumerate(all_bodies(d)):
        ex, ez = foot(m)
        x, z = m["pos"]
        o.append(R(X(x - ex), Y(z + ez), pj.L(2 * ex), pj.L(2 * ez),
                   fill="var(--dan3)", stroke="var(--rule)", sw=0.7, op=0.9))
        body_label(o, pj, m, k, pj.L(2 * ex), pj.L(2 * ez), X(x), Y(z))
    for r in d["runs"]:
        a, b = geo.run_span(r)
        col = "var(--nagaya)" if r["kind"] == "Nagaya" else "var(--hei)"
        o.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), stroke=col, sw=2.0, op=0.5))
    for kr, (r, met) in enumerate(MET):
        col = ROUTE_COL.get(r.get("color"), "var(--shu)")
        pts = [(X(p[0]), Y(p[1])) for p in r["pts"]]
        prof, L, up, dn, steps, cliff, ok, need = met
        o.append(PL(pts, stroke=col, sw=2.4, op=0.9, dash="7 4" if not ok else None))
        for p in pts:
            o.append(CIR(p[0], p[1], 2.2, fill=col, stroke="none"))
        # 名札は棟の名札と当たるので、終点から段違いに離す
        o.append(LN(pts[-1][0], pts[-1][1], pts[-1][0] + 6, pts[-1][1] - 14 - (kr % 3) * 13 + 4,
                    stroke=col, sw=0.6, op=0.7))
        o.append(T(pts[-1][0] + 8, pts[-1][1] - 14 - (kr % 3) * 13,
                   r["label"] + ("　✗" if not ok else ""), cls="jo", fill=col))
        if not ok:
            # 崖を横切る区間に朱の太線と×を打つ
            wp = []
            for c in (cliff[2], (cliff[2] + cliff[3]) / 2.0, cliff[3]):
                s2 = 0.0
                for a, b in zip(r["pts"], r["pts"][1:]):
                    seg = math.hypot(b[0] - a[0], b[1] - a[1])
                    if s2 + seg >= c - 1e-9:
                        t = (c - s2) / max(1e-6, seg)
                        wp.append((X(a[0] + (b[0] - a[0]) * t), Y(a[1] + (b[1] - a[1]) * t)))
                        break
                    s2 += seg
            if len(wp) == 3:
                o.append(PL([wp[0], wp[2]], stroke="var(--shu)", sw=5.0, op=0.55))
                cxp, czp = wp[1]
                o.append(LN(cxp - 5, czp - 5, cxp + 5, czp + 5, stroke="var(--shu)", sw=2.2))
                o.append(LN(cxp - 5, czp + 5, cxp + 5, czp - 5, stroke="var(--shu)", sw=2.2))
    gx, gz = geo.gate
    o.append(CIR(X(gx), Y(gz), 5.0, fill="var(--shu)", stroke="var(--paper)", sw=1.2))
    o.append(T(X(gx) - 8, Y(gz) - 9, "表門", cls="anG", anchor="end"))
    o.append(T(14, 18, "%s　動線図(北の帯 z ≧ 795 の切り出し)" % kan, cls="big"))
    o.append(T(14, 34, "⛔ %d 本が崖を横切って直線では不成立(破線 + ×)。蹴上 %.2f / 踏面 %.2f では "
                       "1:%.2f より緩くないと直線の石段が入らない(折返しは半分+踊り場1枚)。"
               % (len(ng), d["const"]["keri"], d["const"]["fumi"],
                  d["const"]["fumi"] / d["const"]["keri"]),
               cls="jo", fill="var(--shu)", fs=11.0))
    for kq, q in enumerate(ng):
        o.append(T(28, 47 + kq * 13, "・" + q, cls="jo", fill="var(--shu)", fs=11.0))
    for kb, q in enumerate(blk):
        o.append(T(14, 47 + (len(ng) + kb) * 13, q, cls="jo", fill="var(--shu)", fs=11.0))
    o.append(T(14, pj.H - 26, "⛔ 南の脚(z 678〜802・敷地の三割)は図の外 — "
                              "そこには棟も動線も一本も無い。", cls="jo", fill="var(--shu)"))
    o.append(T(14, pj.H - 12, "表向=朱 ／ 役方=茶 ／ 勝手=褐 ／ 奥向=緑 ／ 家中=紺。"
                              "渡廊下は起こしていないので、棟から棟へは外を歩く。", cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


def route_profile(r, dem, step=1.0):
    """動線を等間隔で拾って (始点からの距離, 地盤) の列にする。"""
    pts = r["pts"]
    out = [(0.0, dem(pts[0][0], pts[0][1]))]
    s = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg < 1e-9:
            continue
        n = max(1, int(math.ceil(seg / step)))
        for i in range(1, n + 1):
            t = i / float(n)
            out.append((s + seg * t,
                        dem(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)))
        s += seg
    return out


def route_cliff(prof, need, minrise=1.0):
    """動線が横切る**崖**。蹴上/踏面で石段が入らない(水平 < 落差 × need)窓のうち、
    **落差が最大のもの**を返す (落差, 水平, 起点, 終点)。⛔ 平均勾配では崖が均されて消える。"""
    best = None
    n = len(prof)
    for i in range(n):
        for j in range(i + 1, n):
            run = prof[j][0] - prof[i][0]
            rise = abs(prof[j][1] - prof[i][1])
            if run < 1e-6 or rise < minrise or run >= rise * need:
                continue
            if best is None or rise > best[0]:
                best = (rise, run, prof[i][0], prof[j][0])
    return best


def kaidan_need(rise, C):
    """石段に要る水平。返すのは **(段数, 直線に要る水平, 折返しに要る水平)**。

    ⛔ **`落差 × 踏面/蹴上` では出さない** — 段数は切り上げなので、
    正しくは **段数(ceil) × 踏面**(2026-09-01 検図 L1: 表向で 48段×0.45=21.6m に対し
    従前の式は 21.4m を出していた)。
    ⛔ **折返しは「ちょうど半分」ではない** — `sashizu.md` §1f の例
    (落差6.0m → 直線9.0m → **折返し5.0m** / 落差8.0m → 12.1m → **6.5m**)は
    いずれも**半分 + 踊り場1枚(踏面ぶん)**である(同 検図 L2)。
    ⚠ **踊り場の「幅」は断面では決まらない**【?】 — ここで見込むのは奥行だけ。"""
    n = int(math.ceil(rise / C["keri"]))
    straight = n * C["fumi"]
    return n, straight, straight / 2.0 + C["fumi"]


def route_metrics(d, r, dem):
    """延長・登り・下り・横切る崖・越える石段の段数・石段が成立するか。"""
    C = d["const"]
    prof = route_profile(r, dem)
    L = prof[-1][0]
    up = dn = 0.0
    for a, b in zip(prof, prof[1:]):
        if b[1] > a[1]:
            up += b[1] - a[1]
        else:
            dn += a[1] - b[1]
    need = C["fumi"] / C["keri"]              # 石段が要る水平/垂直 = 踏面/蹴上
    cliff = route_cliff(prof, need)
    ok = cliff is None
    steps = int(math.ceil((cliff[0] if cliff else (up + dn)) / C["keri"]))
    return prof, L, up, dn, steps, cliff, ok, need


def routes_table(d, dem):
    """⭐ **直線と折返しを両方出す**(`sashizu.md` §1f: 折返しなら要る水平は半分)。
    ⛔ 直線だけで「入らない」と断じない — 2026-09-01 の検図 K3 で、
    **3本とも折返しなら水平が足りる**ことが分かった。⚠ ただし**踊り場の幅は断面では
    測れない**ので、判定は「折返しの水平は足りる/踊り場は未検証」と書き分ける。"""
    C = d["const"]
    rows = []
    ng = nz = 0
    marg = []          # (余裕[m], 系統名) — 折返しにしたときの余裕。薄い順に名指しする
    for r in d["routes"]:
        prof, L, up, dn, steps, cliff, ok, need = route_metrics(d, r, dem)
        if ok:
            g = "<span class='cert'>崖なし</span>"
            st = "%d 段<br><span class='cert'>路の全長で</span>" % steps
            sw = "<span class='cert'>—</span>"
        else:
            # ⛔ 段数から従属させる(検図 L1)。折返しは踊り場1枚を見込む(検図 L2)。
            nst, rq, half = kaidan_need(cliff[0], C)
            g = ("<b>1 : %.2f</b> ✗ 直線では入らない<br>"
                 "<span class='cert'>落差 %.1f m / 水平 %.1f m(路の %.0f〜%.0f m)</span>"
                 % (cliff[1] / cliff[0], cliff[0], cliff[1], cliff[2], cliff[3]))
            st = ("<b>%d 段</b><br><span class='cert'>%d × %.2f = %.1f m ／ 取れる %.1f m</span>"
                  % (nst, nst, C["fumi"], rq, cliff[1]))
            fit = cliff[1] >= half
            marg.append((cliff[1] - half, r["label"]))
            sw = ("<b style='color:%s'>%.1f m %s</b><br>"
                  "<span class='cert'>半分 %.1f + 踊り場 %.2f ／ 余裕 %+.1f m</span>"
                  % ("var(--take)" if fit else "var(--shu)", half,
                     "○ 足りる" if fit else "✗ 足りない",
                     rq / 2.0, C["fumi"], cliff[1] - half))
            ng += 1
            if fit:
                nz += 1
        rows.append("<tr><td>%s</td><td>%.1f m<br><span class='cert'>登り %.1f ／ 下り %.1f</span>"
                    "</td><td>%.1f → %.1f m</td><td%s>%s</td><td%s>%s</td><td>%s</td></tr>"
                    % (r["label"], L, up, dn, prof[0][1], prof[-1][1],
                       ' style="color:var(--shu)"' if not ok else "", g,
                       ' style="color:var(--shu)"' if not ok else "", st, sw))
        # ⛔ 長い備考を列に押し込まない(列幅が潰れて表が枠を越える)。次の行へ colspan で流す。
        if r.get("_"):
            rows.append("<tr><td class='note' colspan='6'>%s</td></tr>"
                        % html.escape(r["_"]))
    return ("<div class='tw'><table><thead><tr><th>系統</th>"
            "<th>延長<br><span class='cert'>登り / 下り 累計</span></th>"
            "<th>両端の地盤</th><th>最急勾配</th>"
            "<th>直線の石段</th><th>折返しなら</th>"
            "</tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>⛔ <b>最急勾配</b>は動線を 1 m 刻みで拾い、"
            "<b>石段が入らない(水平 &lt; 落差 × 踏面/蹴上)窓のうち落差が最大のもの</b>を採った"
            "(平均勾配では崖が均されて消える)。"
            "蹴上 %.2f m / 踏面 %.2f m の石段が直線で成立するには <b>1 : %.2f より緩い</b>ことが要る。"
            "<br>⭐ <b>「直線に要る水平」は 段数(切り上げ)× 踏面</b>で、落差からの比例では出さない"
            "(2026-09-01 検図 L1)。"
            "<b>「折返しなら」は その半分 + 踊り場1枚(踏面 %.2f m)</b> — "
            "<code>sashizu.md</code> §1f の例(落差6.0m → 直線9.0m → <b>折返し5.0m</b>)は"
            "ちょうど半分(4.5m)ではなく<b>踊り場を見込んだ値</b>である(同 検図 L2)。"
            "<br><b>直線で入らないのは %d 本だが、そのうち %d 本は折返しなら水平が足りる。</b>"
            "%s"
            "⚠ <b>足りるのは水平(奥行)だけで、踊り場の<u>幅</u>は断面では測れない</b>【?】 — "
            "「成立する」と断ずるには平面で踊り場を描く必要がある。"
            "<br>⭐ <b>そもそも崖は斜めなので、横切る向きで勾配が変わる</b> — "
            "下の検算のとおり<b>東西に横切れば直線のまま入る</b>。"
            "<br>%s</p>"
            % (C["keri"], C["fumi"], need, C["fumi"], ng, nz,
               ("⚠ <b>余裕が最も薄いのは「%s」で %+.1f m しかない</b> — "
                "取り付きを数m振っただけで不成立に転ぶ。" % (min(marg)[1], min(marg)[0]))
               if marg else "",
               inline(sai(d)["block"])))


def cross_check(d):
    """**崖を東西(x 方向)に横切ったときの勾配**を走査して、直線の石段が入る切り線を拾う。
    ⛔ 結果を json に持たない(規則4)。⛔ **ここで引く線は動線ではない** — 動線を増やすのは
    配置の判断で指図方の領分ではなく、これは『東西に横切れば入る』という幾何の検算である。"""
    cc = d.get("crossCheck")
    if not cc:
        return []
    C = d["const"]
    need = C["fumi"] / C["keri"]
    f = SURF[cc.get("surface", "recon")]
    out = []
    z = cc["z0"]
    while z <= cc["z1"] + 1e-9:
        for toe, crest in cliff_cross(z, -380.0, -120.0):
            if crest is None:
                continue
            if not (pip(GEOP[0], toe, z) and pip(GEOP[0], crest, z)):
                continue
            run = abs(crest - toe)
            rise = abs(f(crest, z) - f(toe, z))
            if rise < 1e-3:
                continue
            n = int(math.ceil(rise / C["keri"]))
            out.append({"z": z, "x0": toe, "x1": crest, "run": run, "rise": rise,
                        "ratio": run / rise, "n": n, "need": n * C["fumi"],
                        "ok": run >= n * C["fumi"],
                        "land": int(max(0, n // max(1, int(cc.get("landing", 12))) - 1))})
        z += cc["step"]
    return out


def cross_check_table(d):
    rows = cross_check(d)
    if not rows:
        return ""
    okr = [q for q in rows if q["ok"]]
    best = max(rows, key=lambda q: q["ratio"])
    sel = sorted(okr or rows, key=lambda q: -q["ratio"])[:5]
    body = "".join(
        "<tr><td>z = %.0f</td><td>x %.1f → %.1f</td><td>%.1f m</td><td>%.2f m</td>"
        "<td><b>1 : %.2f</b></td><td>%d 段</td><td>%.1f m</td>"
        "<td%s><b>%s</b></td></tr>"
        % (q["z"], q["x0"], q["x1"], q["run"], q["rise"], q["ratio"], q["n"], q["need"],
           "" if q["ok"] else " style='color:var(--shu)'",
           "○ 直線で入る(踊り場 %d 箇所)" % q["land"] if q["ok"] else "✗")
        for q in sel)
    return ("<div class='tw'><table><thead><tr><th>切り線</th><th>法尻 → 法肩</th>"
            "<th>水平</th><th>落差</th><th>勾配</th><th>段数</th><th>直線に要る水平</th>"
            "<th>判定</th></tr></thead><tbody>" + body + "</tbody></table></div>"
            "<p class='cap'>⭐ <b>崖を東西(x 方向)に横切ったときの検算。</b>"
            "復元面(A案)の上で z = %.0f〜%.0f を %.0f m 刻みに走査し、"
            "<b>%d 本の切り線のうち %d 本で、既定の蹴上・踏面の石段が"
            "『直線のまま』入る</b>(最も緩いのは z = %.0f の <b>1 : %.2f</b>)。"
            "⚠ <b>崖が WNW–ESE の斜めだから</b>で、南北に横切ると同じ崖が急になる。"
            "<br>⛔ <b>ここに引いた線は動線ではない</b> — 動線を増やす/付け替えるのは配置の判断で、"
            "指図方は決めない。この表が言うのは<b>「東西に横切る取り付きなら幾何としては成立する」</b>"
            "ということだけである。⚠ 踊り場の数は %d 段ごとに1箇所という目安で、"
            "<b>幅は断面では決まらない</b>【?】。</p>"
            % (d["crossCheck"]["z0"], d["crossCheck"]["z1"], d["crossCheck"]["step"],
               len(rows), len(okr), best["z"], best["ratio"],
               int(d["crossCheck"].get("landing", 12))))


# ---------------------------------------------------------------- 其六 外周の展開
def run_pieces(d, geo, dem, r):
    """run の**駒ごと**の座と天端。返すのは [(t0, t1, 座, 天端)]、t は run の始点からの距離[m]。
    座の採り方は json の `_seatRules`(築地塀 = nat-max2 / 長屋 = nat-min3)。
    ⚠ **駒は独立して地形に載るので、天端は run の中で折れる** — その折れがこの図の主題。"""
    C = d["const"]
    a, b = geo.run_span(r)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    dr = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)

    def at(t):
        return (a[0] + dr[0] * t, a[1] + dr[1] * t)
    out = []
    if r["kind"] == "Nagaya":
        n, tot, half = nagaya_chain(L, C["nagayaModC"], C["nagayaModLR"])
        ws = ([C["nagayaModC"]] if n == 1 else
              [C["nagayaModLR"]] + [C["nagayaModC"]] * (n - 2) + [C["nagayaModLR"]])
        t = half
        for w in ws:
            c = t + w / 2.0
            g = min(dem(*at(c)), dem(*at(c - 4.0)), dem(*at(c + 4.0)))
            y = g - C["runSink"]
            out.append((t, t + w, y, y + C["nagayaH"]))
            t += w
    else:
        n, p = dobei_pieces(L, C["dobeiPitchNom"])
        for k in range(n):
            t0 = k * p
            g = max(dem(*at(t0)), dem(*at(t0 + p)))
            y = g - C["runSink"]
            out.append((t0, t0 + p, y, y + C["dobeiH"]))
    return out


def perimeter_segs(d, geo):
    """外周を辺0→最終辺の順に一列へ伸ばす。返すのは [(辺, 名, 種, run, s0, s1)]。
    **s は外周に沿った累計距離**で、表門の辺だけ 塀 / 開口 / 塀 の三つに割れる。"""
    out, s = [], 0.0
    for e in d["edges"]:
        a, b, L, _ = geo.edge(e["i"])
        if e["run"] is None:
            out.append((e["i"], "囲い無し", "none", None, s, s + L))
            s += L
        elif e["i"] == d["gate"]["edge"]:
            gl, gr = geo.wall_ends()
            l1 = math.hypot(gl[0] - a[0], gl[1] - a[1])
            lg = math.hypot(gr[0] - gl[0], gr[1] - gl[1])
            l2 = math.hypot(b[0] - gr[0], b[1] - gr[1])
            rl = next(q for q in d["runs"] if q.get("to") == "gateL")
            rr = next(q for q in d["runs"] if q.get("from") == "gateR")
            out.append((e["i"], "築地塀", "dobei", rl, s, s + l1))
            out.append((e["i"], "表門(開口)", "gate", None, s + l1, s + l1 + lg))
            out.append((e["i"], "築地塀", "dobei", rr, s + l1 + lg, s + L))
            s += L
        else:
            r = next(q for q in d["runs"] if q.get("edge") == e["i"])
            out.append((e["i"], e["kind"], "nagaya" if e["kind"] == "盲長屋" else "dobei",
                        r, s, s + L))
            s += L
    return out


def run_stats(d, geo, dem, r):
    """run の天端の 最低 / 最高 / 振れ / 最大段差 / 塀高を超える継ぎ目の数。"""
    hgt = d["const"]["nagayaH"] if r["kind"] == "Nagaya" else d["const"]["dobeiH"]
    pc = run_pieces(d, geo, dem, r)
    tops = [q[3] for q in pc]
    jm = [abs(tops[i + 1] - tops[i]) for i in range(len(tops) - 1)]
    cut = [i for i, j in enumerate(jm) if j > hgt]
    return {"pieces": pc, "h": hgt, "lo": min(tops), "hi": max(tops),
            "swing": max(tops) - min(tops), "jmax": max(jm) if jm else 0.0,
            "jumps": jm, "cut": cut, "n": len(pc)}


def tenkai_svg(d, geo, dem, kan, W=940.0):
    """外周を辺の順に一列へ伸ばした**展開図**。⛔ 帯だけでは天端が読めないので、
    **駒ごとの天端の折れ線(座+塀高)と地盤線**を重ねる(2026-08-30 検図 K-3)。"""
    segs = perimeter_segs(d, geo)
    tot = segs[-1][5]
    lm, rm = 52.0, 18.0
    band, PH, bot = 20.0, 300.0, 78.0
    s = (W - lm - rm) / tot
    # ⭐ **帯が細くて字が入らない辺は、引出線で帯の外へ出す**(2026-09-01 検図 Kz-4)。
    #   ⛔ ラベルを落とさない — 落とすと図の上でその辺が名前を失う。出す分だけ天を空ける。
    NARROW = 30.0
    nnar = sum(1 for q in segs if (q[5] - q[4]) * s <= NARROW)
    top = 62.0 + (26.0 if nnar else 0.0)
    # 地盤線(外周に沿って 1.5m 刻み)
    gpts, ss = [], 0.0
    for e in d["edges"]:
        a, b, L, dr = geo.edge(e["i"])
        m = max(2, int(L / 1.5))
        for q in range(m + 1):
            t = L * q / m
            gpts.append((ss + t, dem(a[0] + dr[0] * t, a[1] + dr[1] * t)))
        ss += L
    # 駒
    ST = {}
    for (i, nm, k, r, s0, s1) in segs:
        if r is not None:
            ST[r["name"]] = run_stats(d, geo, dem, r)
    gp = d["gate"]["plan"]
    gy = seat_of(gate_body(d, geo)[1], dem, d["gate"]["sink"])
    ylo = min([q[1] for q in gpts] + [min(q[2] for q in v["pieces"]) for v in ST.values()]) - 1.5
    yhi = max([max(q[3] for q in v["pieces"]) for v in ST.values()] + [gy + gp["monH"]]) + 2.0
    vs = PH / (yhi - ylo)
    Hh = top + band + PH + bot
    o = _sv(W, Hh, "%s 外周の展開" % kan)
    o.append(R(0, 0, W, Hh, fill="var(--paper)"))

    def PX(q):
        return lm + q * s

    def PY(y):
        return top + band + PH - (y - ylo) * vs
    # 高さの目盛
    for y in range(int(ylo // 5 * 5), int(yhi) + 5, 5):
        if not (ylo <= y <= yhi):
            continue
        o.append(LN(lm, PY(y), W - rm, PY(y), stroke="var(--rule)", sw=0.6))
        o.append(T(lm - 6, PY(y) + 3, "%d m" % y, cls="jo", anchor="end"))
    # 種別の帯
    COL = {"dobei": "var(--hei)", "nagaya": "var(--nagaya)", "gate": "var(--shu)",
           "none": "var(--paper2)"}
    nar = [0]
    for (i, nm, k, r, s0, s1) in segs:
        w = (s1 - s0) * s
        o.append(R(PX(s0), top, w, band, fill=COL[k], stroke="var(--ink)", sw=0.7,
                   op=0.30 if k != "none" else 1.0))
        if k == "none":
            o.append(R(PX(s0), top, w, band, fill="none", stroke="var(--shu)", sw=1.2, dash="4 4"))
        if w > NARROW:
            o.append(T(PX(s0) + w / 2, top + 14, nm, cls="anS2"))
            o.append(T(PX(s0) + w / 2, top - 5, "辺%d %.0fm" % (i, s1 - s0), cls="jo",
                       anchor="middle"))
        else:
            # 細い帯は引出線で外へ。上下2段に振って隣どうしの重なりを避ける。
            cx = PX(s0) + w / 2
            ty = top - 21 - (nar[0] % 2) * 13
            nar[0] += 1
            o.append(LN(cx, top - 2, cx, ty + 3, stroke="var(--rule)", sw=0.7))
            o.append(T(cx, ty, "%s 辺%d %.0fm" % (nm, i, s1 - s0), cls="jo", anchor="middle"))
        o.append(LN(PX(s0), top - 2, PX(s0), PY(ylo), stroke="var(--rule)", sw=0.7, op=0.7))
    o.append(LN(W - rm, top - 2, W - rm, PY(ylo), stroke="var(--rule)", sw=0.7, op=0.7))
    # 地盤線
    o.append(PL([(PX(q[0]), PY(q[1])) for q in gpts], stroke="var(--ink)", sw=1.4, op=0.85))
    # 駒ごとの天端(折れ線)と胴
    marks = []
    for (i, nm, k, r, s0, s1) in segs:
        if k == "gate":
            o.append(R(PX(s0), PY(gy + gp["monH"]), (s1 - s0) * s, gp["monH"] * vs,
                       fill="var(--shu)", stroke="var(--ink)", sw=0.9, op=0.35))
            o.append(T(PX((s0 + s1) / 2), PY(gy + gp["monH"]) - 5, "表門", cls="jo",
                       anchor="middle", fill="var(--shu)"))
            continue
        if r is None:
            continue
        st = ST[r["name"]]
        col = "var(--nagaya)" if r["kind"] == "Nagaya" else "var(--hei)"
        for (t0, t1, y, ty) in st["pieces"]:
            o.append(R(PX(s0 + t0), PY(ty), max(0.7, (t1 - t0) * s), st["h"] * vs,
                       fill=col, stroke="none", op=0.30))
        # 天端の折れ線(段差の縦線を含む)
        pts = []
        for (t0, t1, y, ty) in st["pieces"]:
            pts.append((PX(s0 + t0), PY(ty)))
            pts.append((PX(s0 + t1), PY(ty)))
        o.append(PL(pts, stroke=col, sw=1.6))
        for idx in st["cut"]:
            t = st["pieces"][idx][1]
            marks.append((s0 + t, st["pieces"][idx][3], st["pieces"][idx + 1][3], r["name"]))
    # 塀が切れる継ぎ目
    for mi, (sm, y1, y2, nm) in enumerate(marks):
        o.append(LN(PX(sm), PY(min(y1, y2)), PX(sm), PY(max(y1, y2)), stroke="var(--shu)", sw=2.4))
        o.append(CIR(PX(sm), PY(max(y1, y2)), 4.0, fill="none", stroke="var(--shu)", sw=1.6))
        dy = 16 + (mi % 2) * 14
        o.append(LN(PX(sm), PY(max(y1, y2)) - 4, PX(sm), PY(max(y1, y2)) - dy,
                    stroke="var(--shu)", sw=0.7))
        o.append(T(PX(sm), PY(max(y1, y2)) - dy - 3, "切れ %.2fm" % abs(y2 - y1),
                   cls="jo", anchor="middle", fill="var(--shu)"))
    o.append(T(14, 18, "%s　外周の展開(辺0 → 辺%d の順・駒ごとの天端)" % (kan, len(geo.P) - 1), cls="big"))
    o.append(T(14, 36, "周長 %.1f m ／ 築地塀 %.1f m ／ 盲長屋 %.1f m ／ 開口(表門)%.1f m ／ 囲い無し %.1f m"
               "　│　横 1:%.0f ／ 縦 1:%.0f(垂直倍率 ×%.1f)"
               % (tot,
                  sum(q[5] - q[4] for q in segs if q[2] == "dobei"),
                  sum(q[5] - q[4] for q in segs if q[2] == "nagaya"),
                  sum(q[5] - q[4] for q in segs if q[2] == "gate"),
                  sum(q[5] - q[4] for q in segs if q[2] == "none"),
                  1000.0 / s, 1000.0 / vs, vs / s), cls="jo", fs=11.0))
    o.append(T(14, Hh - 50, "細い実線 = 外周に沿った地盤 ／ 太い折れ線 = 駒ごとの天端(座 + 塀高・長屋高)"
                            " ／ 帯 = 塀・長屋の胴", cls="jo"))
    o.append(T(14, Hh - 36, "⛔ 朱の丸 = 継ぎ目の段差が塀の高さを超え、"
                            "上の駒の下端が下の駒の天端より高い所 =「塀が物理的に切れている」(%d 箇所)"
               % len(marks), cls="jo", fill="var(--shu)"))
    o.append(T(14, Hh - 22, "朱の破線の帯 = 囲いを建てない区間(内藤が背中合わせで受け持つ前提・未解決 P-5)",
               cls="jo", fill="var(--shu)"))
    o.append(T(14, Hh - 8, "⚠ 縦は横の %.1f 倍に伸ばしてある。段差の見た目の急さは誇張、数字は実寸。"
               % (vs / s), cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


def tenkai_table(d, geo, dem):
    rows = []
    for (i, nm, k, r, s0, s1) in perimeter_segs(d, geo):
        if r is None:
            rows.append("<tr><td>辺%d</td><td>%s</td><td>%.1f m</td><td>—</td><td>—</td>"
                        "<td>—</td><td>—</td><td>—</td><td>—</td></tr>" % (i, nm, s1 - s0))
            continue
        st = run_stats(d, geo, dem, r)
        rows.append("<tr><td>辺%d</td><td>%s<br><span class='cert'>%s</span></td><td>%.1f m</td>"
                    "<td>%d 駒</td><td>%.3f m</td><td>%.1f 〜 %.1f m</td>"
                    "<td%s>%.1f m</td><td%s>%.2f m</td><td%s>%s</td></tr>"
                    % (i, nm, r["name"], s1 - s0, st["n"], (s1 - s0) / st["n"],
                       st["lo"], st["hi"],
                       ' style="color:var(--shu);font-weight:700"' if st["swing"] > st["h"] else "",
                       st["swing"],
                       ' style="color:var(--shu);font-weight:700"' if st["jmax"] > st["h"] else "",
                       st["jmax"],
                       ' style="color:var(--shu);font-weight:700"' if st["cut"] else "",
                       ("<b>%d 箇所</b>" % len(st["cut"])) if st["cut"] else "0"))
    return ("<div class='tw'><table><thead><tr><th>辺</th><th>種 / run</th><th>長さ</th>"
            "<th>駒数</th><th>実ピッチ</th><th>天端 最低〜最高</th><th>振れ</th>"
            "<th>最大段差</th><th>塀が切れる継ぎ目</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 其七 取り合い(表門)
def toriai_svg(d, geo, kan, W=940.0):
    """表門と築地塀の取り合いを**面**で描く。芯で合わせていないことが読める縮尺にする。"""
    gp = d["gate"]["plan"]
    span = 24.0                      # 走り方向に ±12m
    lm = 40.0
    s = (W - 2 * lm) / span
    cx = W / 2
    base = 215.0                     # 区画線の位置。門の奥行 8.66m×s = 310px が上下に開く
    Hh = 505.0
    o = _sv(W, Hh, "%s 取り合い(表門)" % kan)
    o.append(R(0, 0, W, Hh, fill="var(--paper)"))

    def SX(m):
        return cx + m * s
    # 通り(外)側を上に、敷地の中を下に描く平面詳細
    o.append(LN(lm, base, W - lm, base, stroke="var(--rule)", sw=0.8, dash="6 4"))
    o.append(T(W - lm + 4, base + 4, "区画線", cls="jo"))
    dep = d["const"]["dobeiT"] * s
    for sgn in (-1, 1):
        e0 = sgn * (gp["gateHalf"] + 0.35)
        e1 = sgn * span / 2
        o.append(R(min(SX(e0), SX(e1)), base - dep / 2, abs(SX(e1) - SX(e0)), dep,
                   fill="var(--hei)", stroke="var(--ink)", sw=1.0, op=0.35))
    o.append(T(SX(-8), base - dep / 2 - 8, "築地塀 Hei_F_L", cls="anS2"))
    o.append(T(SX(8), base - dep / 2 - 8, "築地塀 Hei_F_R", cls="anS2"))
    # 門: 螻羽(屋根) / 袖壁 / 冠木
    o.append(R(SX(-gp["gateHalf"]), base - gp["monD"] * s / 2, 2 * gp["gateHalf"] * s, gp["monD"] * s,
               fill="var(--shu)", stroke="var(--shu)", sw=1.0, op=0.13, dash="4 3"))
    o.append(R(SX(-gp["bodyW"] / 2), base - gp["sosekiD"] * s / 2, gp["bodyW"] * s, gp["sosekiD"] * s,
               fill="var(--shu)", stroke="var(--shu)", sw=1.4, op=0.30))
    o.append(R(SX(-gp["doorW"] / 2), base - 4, gp["doorW"] * s, 8,
               fill="var(--paper)", stroke="var(--ink)", sw=1.0))
    o.append(T(cx, base + 4, "扉 %.2fm" % gp["doorW"], cls="anS2"))
    o.append(T(cx, base - gp["monD"] * s / 2 - 9, "螻羽(屋根)の実幅 %.2fm — 実装はこの端で塀を止める"
               % gp["monW"], cls="anS2", fill="var(--shu)"))
    o.append(T(cx, base + gp["sosekiD"] * s / 2 + 17,
               "軸部(袖壁)%.2fm — 螻羽より片側 %.2f m 内側(その差は屋根の陰)"
               % (gp["bodyW"], gp["gateHalf"] - gp["bodyW"] / 2), cls="anS2", fill="var(--shu)"))
    # 寸法線
    def dim(a, b, y, txt, col="var(--ink)"):
        o.append(LN(SX(a), y, SX(b), y, stroke=col, sw=0.9))
        o.append(LN(SX(a), y - 4, SX(a), y + 4, stroke=col, sw=0.9))
        o.append(LN(SX(b), y - 4, SX(b), y + 4, stroke=col, sw=0.9))
        o.append(T((SX(a) + SX(b)) / 2, y - 6, txt, cls="jo", anchor="middle", fill=col))
    gh = gp["gateHalf"]
    y1 = base + gp["monD"] * s / 2 + 34
    dim(-gh - 0.35, -gh, y1, "隙間 0.35", col="var(--shu)")
    dim(gh, gh + 0.35, y1, "隙間 0.35", col="var(--shu)")
    dim(-gh - 0.35, -gp["bodyW"] / 2, y1 + 24, "屋根の陰 %.2f(隙間ではない)"
        % (gh + 0.35 - gp["bodyW"] / 2), col="var(--dim)")
    dim(gp["bodyW"] / 2, gh + 0.35, y1 + 24, "屋根の陰 %.2f(隙間ではない)"
        % (gh + 0.35 - gp["bodyW"] / 2), col="var(--dim)")
    dim(-gh - 0.35, gh + 0.35, y1 + 48, "塀の妻面どうし %.2fm" % (2 * gh + 0.7))
    o.append(T(14, 18, "%s　取り合い 詳細 ①(表門 ↔ 築地塀)　J1 / J2" % kan, cls="big"))
    o.append(T(14, 34, "縮尺 1:%.0f 相当 ／ 上 = 通り側 / 下 = 敷地の中 ／ 走り方向に ±12 m"
               % (1000.0 / s), cls="jo", fs=12.0))
    o.append(T(14, Hh - 40, "⛔ 閉じの検査が見る面は『塀の妻面 ↔ 螻羽の外端』で、そこが %.2f m 開いている。"
                            "直すのはこの 0.35 m だけ(未解決 P-3)。" % 0.35,
               cls="jo", fill="var(--shu)"))
    o.append(T(14, Hh - 26, "⭕ 螻羽の下の %.2f m は**屋根の陰** — 螻羽(屋根の端)は軸部(袖壁)より "
                            "%.2f m 外へ出ているので、塀の妻面と軸部のあいだのこの距離は"
                            "**隙間ではない**。"
               % (gh + 0.35 - gp["bodyW"] / 2, gh - gp["bodyW"] / 2), cls="jo"))
    o.append(T(14, Hh - 12, "規約は 0.00(+0.05 / −0.00、隙間は不可・めり込みは可)。"
                            "寄せるときに動かすのは塀の側(門は開口の芯に固定)。", cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


# ------------------------------------------------ 其七 取り合い ②〜④(J3 / J4・J5 / J8・J9)
def _dimline(o, x1, y, x2, txt, col="var(--ink)", up=True):
    o.append(LN(x1, y, x2, y, stroke=col, sw=0.9))
    for q in (x1, x2):
        o.append(LN(q, y - 4, q, y + 4, stroke=col, sw=0.9))
    o.append(T((x1 + x2) / 2, y - 6 if up else y + 12, txt, cls="jo", anchor="middle", fill=col))


def toriai_nagaya_svg(d, kan, W=940.0):
    """J3 — 家臣長屋2棟。**屋根が重なるのは正しい納まりで、直すのは壁の面**。"""
    C = d["const"]
    L = next(x for x in d["service"] if x["name"] == "KashinNagaya_L")
    Rt = next(x for x in d["service"] if x["name"] == "KashinNagaya_R")
    pitch = abs(Rt["pos"][0] - L["pos"][0])
    wall = C["nagayaModLR"]
    span = 24.0
    lm = 60.0
    s = (W - 2 * lm) / span
    cx = W / 2
    y0 = 108.0
    dep = L["d"]
    Hh = y0 + dep * s + 58 + 60          # 下は寸法線2本 + 注記3行ぶん
    o = _sv(W, Hh, "%s 取り合い(家臣長屋)" % kan)
    o.append(R(0, 0, W, Hh, fill="var(--paper)"))

    def SX(m):
        return cx + m * s

    def rect(c0, half, dep, y0, fill, op, dash=None, stroke="var(--ink)"):
        o.append(R(SX(c0 - half), y0, 2 * half * s, dep * s, fill=fill, stroke=stroke,
                   sw=1.0, op=op, dash=dash))
    # 屋根の外形(bbox)
    for c, nm in ((-pitch / 2, L["label"]), (pitch / 2, Rt["label"])):
        rect(c, L["w"] / 2, dep, y0 - 0.29 * s, "var(--nagaya)", 0.18, dash="4 3")
        rect(c, wall / 2, dep, y0, "var(--nagaya)", 0.42)
        o.append(T(SX(c), y0 + dep * s / 2, nm, cls="anS2"))
        o.append(LN(SX(c), y0 - 26, SX(c), y0 + dep * s + 8, stroke="var(--shu)", sw=0.6, dash="4 3"))
    o.append(T(SX(-pitch / 2 - L["w"] / 2) + 4, y0 - 0.29 * s - 6, "破線 = 屋根の外形 %.2fm"
               % L["w"], cls="jo", fill="var(--dim)"))
    o.append(T(SX(-pitch / 2 - wall / 2) + 4, y0 + dep * s + 14, "塗り = 壁の実面 %.2fm" % wall,
               cls="jo"))
    _dimline(o, SX(-pitch / 2), y0 - 30, SX(pitch / 2), "芯間 %.2f m" % pitch, col="var(--shu)")
    _dimline(o, SX(-pitch / 2 + wall / 2), y0 + dep * s + 34, SX(pitch / 2 - wall / 2),
             "壁の面どうし %+.2f m(めり込み)" % (pitch - wall), col="var(--shu)")
    _dimline(o, SX(pitch / 2 - L["w"] / 2), y0 + dep * s + 58, SX(-pitch / 2 + L["w"] / 2),
             "屋根の重なり %.2f m ＝ 正しい納まり" % (L["w"] - pitch), col="var(--take)")
    o.append(T(14, 18, "%s　取り合い 詳細 ②(家臣長屋 西 ↔ 東)　J3" % kan, cls="big"))
    o.append(T(14, 34, "縮尺 1:%.0f 相当 ／ 上 = 北 / 下 = 南 ／ 走り方向に ±%.0f m"
               % (1000.0 / s, span / 2), cls="jo", fs=12.0))
    o.append(T(14, Hh - 40, "⭕ **軒(屋根)が %.2f m 重なるのは長屋の連なりとして正しい姿**で、"
                            "機械検査の外形の重なりはここを拾う(偽陽性)。" % (L["w"] - pitch),
               cls="jo", fill="var(--take)"))
    o.append(T(14, Hh - 26, "⛔ 直すのは**壁の面**のほう — 芯間を %.2f m(= 壁の実寸)にすれば "
                            "妻面が面一に揃う。いまは %.2f m のめり込み(許容 −0.00 を超える)。"
               % (wall, wall - pitch), cls="jo", fill="var(--shu)"))
    o.append(T(14, Hh - 12, "動かす側は東棟(西棟は据え置き)。未解決 P-4。", cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


def toriai_chain_svg(d, geo, kan, W=940.0):
    """J4 / J5 — 盲長屋の鎖と隅。⚠ **端数の符号は辺の長さで決まる** —
    鎖が長ければ隅からはみ出し、短ければ両端に隙間が開く。⛔ どちらかを決め打ちしない
    (2026-09-01 の区画の引き直しで実際に反転した)。"""
    C = d["const"]
    r = next(q for q in d["runs"] if q["kind"] == "Nagaya")
    ei = r["edge"]
    va, vb = ei, (ei + 1) % geo.N
    a, b = geo.run_span(r)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n, tot, half = nagaya_chain(L, C["nagayaModC"], C["nagayaModLR"])
    over = half < 0                     # True = はみ出す / False = 隙間が開く
    lm, rm = 46.0, 46.0
    s = (W - lm - rm) / (max(tot, L) + 6.0)
    Hh = 316.0
    o = _sv(W, Hh, "%s 取り合い(盲長屋の鎖)" % kan)
    o.append(R(0, 0, W, Hh, fill="var(--paper)"))

    def SX(t):                                  # t = 辺の始点からの距離
        return lm + (t - min(half, 0.0) + 3.0) * s
    y0, dep = 132.0, C["nagayaD"] * s
    # 辺(区画線)
    o.append(LN(SX(0.0), y0 - 14, SX(L), y0 - 14, stroke="var(--ink)", sw=1.8))
    # ⛔ 隅の名札は図の端に立つので、左は左寄せ・右は右寄せにする(中央寄せだと枠を越える)
    for t, nm, ax in ((0.0, "頂点%d(南の隅・辺%d と)" % (va, (ei - 1) % geo.N), "start"),
                      (L, "頂点%d(北の隅・辺%d と)" % (vb, (ei + 1) % geo.N), "end")):
        o.append(LN(SX(t), y0 - 42, SX(t), y0 + dep + 20, stroke="var(--ink)", sw=1.2, dash="5 3"))
        o.append(T(SX(t) + (2 if ax == "start" else -2), y0 - 46, nm, cls="anS2", anchor=ax))
    # 駒
    t = half
    ws = [C["nagayaModLR"]] + [C["nagayaModC"]] * (n - 2) + [C["nagayaModLR"]]
    for k, w in enumerate(ws):
        out = (t < -0.01) or (t + w > L + 0.01)
        o.append(R(SX(t), y0, w * s, dep, fill="var(--nagaya)",
                   stroke="var(--shu)" if out else "var(--ink)", sw=1.4 if out else 0.8,
                   op=0.55 if out else 0.35))
        o.append(T(SX(t + w / 2), y0 + dep / 2 + 3,
                   "端" if k in (0, n - 1) else "%d" % (k + 1), cls="anS2"))
        t += w
    _dimline(o, SX(half), y0 + dep + 30, SX(half + tot), "鎖の実延長 %.3f m" % tot,
             col="var(--shu)")
    _dimline(o, SX(0.0), y0 + dep + 54, SX(L), "辺%d の長さ %.2f m" % (ei, L))
    # 端数は 1〜2m = 十数 px しかないので、名札は図の外へ引き出す
    lab0 = ("J4 南端が %.4f m はみ出す" if over else "J4 南端に %.4f m の隙間") % abs(half)
    lab1 = ("J5 北端が %.4f m はみ出す" if over else "J5 北端に %.4f m の隙間") % abs(half)
    for t0, t1, lab, ax in ((half, 0.0, lab0, "start"),
                            (L, L - half, lab1, "end")):
        o.append(LN(SX(t0), y0 - 22, SX(t1), y0 - 22, stroke="var(--shu)", sw=2.4))
        tx = 14.0 if ax == "start" else W - 14.0
        o.append(LN(tx + (60 if ax == "start" else -60), 76, SX((t0 + t1) / 2), y0 - 24,
                    stroke="var(--shu)", sw=0.6))
        o.append(T(tx, 72, lab, cls="jo", anchor=ax, fill="var(--shu)"))
    o.append(T(14, 18, "%s　取り合い 詳細 ③(盲長屋の鎖 ↔ 隅)　J4 / J5" % kan, cls="big"))
    o.append(T(14, 34, "縮尺 1:%.0f 相当 ／ 上 = 通り(谷)側 / 下 = 敷地の中 ／ 辺%d を真上から"
               % (1000.0 / s, ei), cls="jo", fs=12.0))
    o.append(T(14, 50, "駒の割り: 端 %.2f m + 中 %.3f m × %d + 端 %.2f m ＝ %.3f m"
               % (C["nagayaModLR"], C["nagayaModC"], n - 2, C["nagayaModLR"], tot),
               cls="jo", fs=11.0))
    n2 = n + (-1 if over else 1)
    t2 = 2 * C["nagayaModLR"] + C["nagayaModC"] * (n2 - 2)
    o.append(T(14, Hh - 40,
               ("⛔ 駒数は %d = round(%.2f / %.3f)。鎖の実延長が辺より %.3f m %s、"
                "中央寄せなので**両端が %.4f m ずつ%s**。"
                % (n, L, C["nagayaModC"], abs(tot - L),
                   "長く" if over else "短く", abs(half),
                   "隅の外へ出る" if over else "隅との間に空く")),
               cls="jo", fill="var(--shu)"))
    o.append(T(14, Hh - 26, "駒数を %d に%sと実延長 %.3f m で %+.3f m の端数が出る — "
                            "**端数を隅と開口のどちらで吸うかがユーザーの裁定**(未解決 P-2)。"
               % (n2, "落とす" if over else "増やす", t2, L - t2), cls="jo"))
    o.append(T(14, Hh - 12, "動かす側は鎖(隅は区画の頂点なので固定)。⛔ 鎖の頭から丸ごと並べない — "
                            "端は隅の面に合わせ、端数は鎖の中で吸う。", cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


def toriai_bansho_svg(d, geo, kan, W=940.0):
    """J8 / J9 — 門と番所が区画線をまたぐ。**区画線が斜めなので、はみ出しは番所ごとに違う**。"""
    gp = d["gate"]["plan"]
    bs = gp["bansho"]
    gx, gz = geo.gate
    ow = geo.outward(d["gate"]["edge"])
    uh = (ow[1], -ow[0])
    a, b, EL, edir = geo.edge(d["gate"]["edge"])
    spanz, spanx = 34.0, 16.0
    lm, top = 150.0, 74.0
    s = min((W - 2 * lm) / spanx, 420.0 / spanz)
    Hh = top + spanz * s + 96.0
    cx, cz = W / 2, top + spanz * s / 2
    o = _sv(W, Hh, "%s 取り合い(門と番所 ↔ 区画線)" % kan)
    o.append(R(0, 0, W, Hh, fill="var(--paper)"))

    def SX(dx):                       # dx = 門の芯から東(外)向きの距離
        return cx + dx * s

    def SZ(dz):                       # dz = 門の芯から北向きの距離
        return cz - dz * s
    # 区画線(斜め)
    def edge_x(dz):
        """門の芯から北へ dz の所の区画線の x(門の芯からの東向き距離)。"""
        t = (gz + dz - a[1]) / edir[1]
        return (a[0] + edir[0] * t) - gx
    zz = [-spanz / 2 + spanz * i / 40.0 for i in range(41)]
    o.append(PL([(SX(edge_x(q)), SZ(q)) for q in zz], stroke="var(--ink)", sw=1.6))
    o.append(T(SX(edge_x(spanz / 2)) + 6, SZ(spanz / 2) + 12,
               "区画線(辺%d)" % d["gate"]["edge"], cls="jo"))
    o.append(T(SX(edge_x(0)) - 6, SZ(-spanz / 2) + 4, "← 敷地の中 ／ 通り →", cls="jo", anchor="end"))
    # 門(螻羽)
    o.append(R(SX(-gp["monD"] / 2), SZ(gp["monW"] / 2), gp["monD"] * s, gp["monW"] * s,
               fill="var(--shu)", stroke="var(--shu)", sw=1.0, op=0.14, dash="4 3"))
    o.append(R(SX(-gp["sosekiD"] / 2), SZ(gp["bodyW"] / 2), gp["sosekiD"] * s, gp["bodyW"] * s,
               fill="var(--shu)", stroke="var(--shu)", sw=1.4, op=0.28))
    o.append(T(SX(0), SZ(0) + 4, "表門", cls="anS2", fill="var(--shu)"))
    # 番所(門と同じく yaw 90 — 部材の X が塀の走り方向へ回る)
    for sgn in (1, -1):
        bz = sgn * bs["offset"]
        bx = bs["extrude"]
        o.append(R(SX(bx - bs["d"] / 2), SZ(bz + bs["w"] / 2), bs["d"] * s, bs["w"] * s,
                   fill="var(--shu)", stroke="var(--ink)", sw=1.0, op=0.40))
        o.append(T(SX(bx), SZ(bz) + 4, "番所(%s)" % ("北" if sgn > 0 else "南"), cls="anS2"))
        for cz2 in (bz - bs["w"] / 2, bz + bs["w"] / 2):
            ovr = (bx + bs["d"] / 2) - edge_x(cz2)
            o.append(LN(SX(edge_x(cz2)), SZ(cz2), SX(bx + bs["d"] / 2), SZ(cz2),
                        stroke="var(--shu)", sw=2.0))
            o.append(T(SX(bx + bs["d"] / 2) + 6, SZ(cz2) + 3, "%.2f m 外へ" % ovr,
                       cls="jo", fill="var(--shu)"))
        o.append(LN(SX(0), SZ(0), SX(0), SZ(bz), stroke="var(--shu)", sw=0.6, dash="4 3"))
        o.append(T(SX(0) - 6, SZ(bz / 2), "offset %.3f" % bs["offset"], cls="jo", anchor="end"))
    # 門そのもののはみ出し
    ovg = gp["monD"] / 2 - edge_x(0)
    o.append(LN(SX(edge_x(0)), SZ(0), SX(gp["monD"] / 2), SZ(0), stroke="var(--shu)", sw=2.4))
    o.append(T(SX(gp["monD"] / 2) + 6, SZ(0) + 3, "門の屋根 %.2f m 外へ" % ovg,
               cls="jo", fill="var(--shu)"))
    o.append(T(14, 18, "%s　取り合い 詳細 ④(門と番所 ↔ 区画線)　J8 / J9" % kan, cls="big"))
    o.append(T(14, 34, "縮尺 1:%.0f 相当 ／ 上 = 北 / 右 = 通り側(東)。門の芯が区画線の上に乗る"
               % (1000.0 / s), cls="jo", fs=12.0))
    o.append(T(14, 50, "⚠ **区画線は南北で %.2f m 傾いている**ので、はみ出し量は番所の南端と北端で違う。"
               % abs(edge_x(spanz / 2) - edge_x(-spanz / 2)), cls="jo", fs=11.0))
    o.append(T(14, Hh - 40, "⛔ 番所は `extrude` %.2f m ぶん外向きに押し出されているうえ、"
                            "門の芯が区画線の上にあるので、東面が線の外へ出る。"
               % bs["extrude"], cls="jo", fill="var(--shu)"))
    o.append(T(14, Hh - 26, "⛔ **どこを区画線と見るか(敷居の芯か・軸部の外面か)が決まっていない** — "
                            "門の一部が通りへ出るのは薬医門・冠木門では珍しくない。未解決 P-7。", cls="jo"))
    o.append(T(14, Hh - 12, "動かす側は番所(`extrude` を 0 にするか、内側へ回す)。門は開口の芯に固定。",
               cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


# ---------------------------------------------------------------- 断面
def crossings(d, geo, sec):
    """断面が何を切るか。**設計値から毎回算出する**(手で書かない — sashizu.md §3c)。"""
    hit = []
    for kind, m in seat_bodies(d, geo):
        sp = sec_body_span(sec, m)
        if sp:
            hit.append((sp[0], m["label"]))
    for r in d["runs"]:
        a, b = geo.run_span(r)
        al = sec_run_along(sec, a, b)
        if al is not None:
            hit.append((al, r["name"] + "(縦断)"))
            continue
        c = sec_seg_hit(sec, a, b)
        if c is not None:
            hit.append((c, r["name"]))
    hit.sort()
    seen, out = set(), []
    for _, nm in hit:
        if nm in seen:
            continue
        seen.add(nm)
        out.append(nm)
    return out


def section_scale(d, W=940.0, lm=54.0, rm=26.0):
    """**断面はすべて同じ縮尺で引く。** 断面ごとに横幅へ合わせて伸ばすと、
    短い断面だけ垂直倍率が跳ね上がって比べられなくなる(南北の断面が 803px になった)。"""
    span = max(sec_line(s)[2] for s in d["sections"])
    return (W - lm - rm) / span, span


def section_svg(d, geo, dem, sec, kan, sc, W=940.0):
    """⭐ **切り線を (起点, 単位方向, 長さ) に正規化してあるので、東西・南北・斜めを同じ手で引く。**
    c は切り線の起点からの距離[m]で、軸が何であっても左 = c 小 / 右 = c 大。"""
    s, spanmax = sc
    SL = sec_line(sec)[2]
    c0, c1 = 0.0, SL
    stp = sec["step"]
    ns = int(SL / stp) + 1
    cs = [c0 + i * stp for i in range(ns)]
    ys = [dem(*sec_pt(sec, c)) for c in cs]
    lm, rm, top, bot = 54.0, 26.0, 34.0, 74.0
    pad = (spanmax - SL) / 2.0 * s             # 短い断面は中央へ寄せて余白に置く(縮尺を揃えるため)
    # 天端・底は「地形」と「この断面に載る棟の頂部・座」の両方から採る
    tops, bots = [max(ys)], [min(ys)]
    for kind, m in seat_bodies(d, geo):
        if sec_body_span(sec, m):
            y = seat_of(m, dem, sink_of(d, m))
            tops.append(y + m["h"])
            bots.append(y)
    for r in d["runs"]:
        a, b = geo.run_span(r)
        if sec_run_along(sec, a, b) is not None:
            for (t0, t1, y, ty) in run_pieces(d, geo, dem, r):
                tops.append(ty)
                bots.append(y)
    lo = math.floor(min(bots) - 2)
    hi = math.ceil(max(tops) + 4)
    vs = s * VEX
    Hh = (hi - lo) * vs
    o = _sv(W, Hh + top + bot, "%s %s" % (kan, sec["name"]))
    o.append(R(0, 0, W, Hh + top + bot, fill="var(--paper)"))

    def PX(c):
        return lm + pad + (c - c0) * s

    def PY(y):
        return top + Hh - (y - lo) * vs
    for y in range(int(lo // 5 * 5), hi + 5, 5):
        if not (lo <= y <= hi):
            continue
        o.append(LN(PX(c0), PY(y), PX(c1), PY(y), stroke="var(--rule)", sw=0.6))
        o.append(T(PX(c0) - 6, PY(y) + 3, "%d" % y, cls="jo", anchor="end"))
    # 区画の中の区間を帯で示す(=造成しない区間)
    inside = [pip(geo.P, *sec_pt(sec, c)) for c in cs]
    run = None
    for i, ins in enumerate(inside):
        if ins and run is None:
            run = cs[i]
        if (not ins or i == ns - 1) and run is not None:
            o.append(LN(PX(run), PY(lo) + 8, PX(cs[i]), PY(lo) + 8,
                        stroke="var(--take)", sw=5.0, op=0.55, cap="butt"))
            run = None
    o.append(T(PX(c0) + 4, PY(lo) + 22, "■ 区画の中 = 造成しない(設計地盤 ≡ 現況地形)",
               cls="jo", fill="var(--take)"))
    # 地形(実線=設計地盤も同じ)
    o.append(PL([(PX(c), PY(y)) for c, y in zip(cs, ys)], stroke="var(--ink)", sw=1.8))
    o.append(PL([(PX(c), PY(y)) for c, y in zip(cs, ys)], stroke="var(--shu)", sw=0.9, dash="6 4", op=0.7))
    # 棟・表門(名札は隣り合う駒どうしが重なるので段違いにする)
    for kb, (kind, m) in enumerate(seat_bodies(d, geo)):
        sp = sec_body_span(sec, m)
        if sp is None:
            continue
        a, b = sp
        y = seat_of(m, dem, sink_of(d, m))
        col = "var(--shu)" if kind == "門" else "var(--dan2)"
        o.append(R(PX(a), PY(y + m["h"]), (b - a) * s, m["h"] * vs,
                   fill=col, stroke="var(--ink)", sw=1.0, op=0.40 if kind == "門" else 0.95))
        # 地中に入る部分
        sub = [(c, dem(*sec_pt(sec, c))) for c in cs if a <= c <= b]
        if sub and max(q[1] for q in sub) > y + 0.2:
            pts = [(PX(q[0]), PY(min(q[1], y + m["h"]))) for q in sub]
            pts += [(PX(sub[-1][0]), PY(y)), (PX(sub[0][0]), PY(y))]
            o.append(PL(pts, stroke="none", fill=_bur(), op=0.9, close=True))
        o.append(T(PX((a + b) / 2), PY(y + m["h"]) - 5 - (kb % 2) * 11,
                   m["label"], cls="jo", anchor="middle",
                   fill="var(--shu)" if kind == "門" else None))
    # 外周の run — 横断は1駒の胴、**縦断(切り線が run に重なる)は駒ごとの天端**で描く
    for r in d["runs"]:
        a, b = geo.run_span(r)
        h = d["const"]["nagayaH"] if r["kind"] == "Nagaya" else d["const"]["dobeiH"]
        col = "var(--nagaya)" if r["kind"] == "Nagaya" else "var(--hei)"
        al = sec_run_along(sec, a, b)
        if al is not None:
            pts = []
            for (t0, t1, y, ty) in run_pieces(d, geo, dem, r):
                if al + t1 < c0 or al + t0 > c1:
                    continue
                o.append(R(PX(al + t0), PY(ty), max(0.7, (t1 - t0) * s), h * vs,
                           fill=col, stroke="var(--ink)", sw=0.5, op=0.45))
                pts += [(PX(al + t0), PY(ty)), (PX(al + t1), PY(ty))]
            if pts:
                o.append(PL(pts, stroke=col, sw=1.6))
                o.append(T((pts[0][0] + pts[-1][0]) / 2, min(q[1] for q in pts) - 6,
                           "%s(縦断・駒ごとの天端)" % r["name"], cls="jo", anchor="middle"))
            continue
        pos = sec_seg_hit(sec, a, b)
        if pos is None or not (c0 <= pos <= c1):
            continue
        g = dem(*sec_pt(sec, pos))
        wpx = max(3.0, (d["const"]["nagayaD"] if r["kind"] == "Nagaya"
                        else d["const"]["dobeiT"]) * s)
        o.append(R(PX(pos) - wpx / 2, PY(g + h), wpx, h * vs, fill=col,
                   stroke="var(--ink)", sw=0.8, op=0.55))
        o.append(T(PX(pos), PY(g + h) - 4, r["name"], cls="jo", anchor="middle"))
    o.append(T(14, 18, "%s　%s" % (kan, sec["name"]), cls="big"))
    cr = crossings(d, geo, sec)
    o.append(T(14, Hh + top + 44, ("切るもの(%s): " % sec["view"]) + " → ".join(cr), cls="jo"))
    o.append(T(14, Hh + top + 58, "垂直倍率 ×%.1f(全断面 同一縮尺)／ 実線 = 地盤(設計 ≡ 現況)／ "
                                  "朱の破線 = 造成前(同じ線に重なる=造成していない)／ "
                                  "斜線 = 棟が地中に入る部分" % VEX, cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


# ---------------------------------------------------------------- 崖(折れ線)
# ⚠ 2026-09-01 の考証の訂正で、崖は「法尻 X / 法肩 X の南北の直線」ではなくなった。
#    WNW–ESE の斜め → X ≳ −185 で東西、という**折れ線**なので、
#    ⛔ 一本の X では指せない。算法は Tools/Sashizu/cliff_polyline.py が正典(規則4)。
CLIFF = [None]           # main が `Cliff` を入れる


def cliff_draw(o, X, Y, x0, x1, z0, z1, col="var(--dim)", sw=1.0, label=True):
    """崖の法尻・法肩の折れ線を平面図へ引く。窓 (x0,x1,z0,z1) でクリップする。"""
    for line, lab in ((CLIFF[0].toe, "法尻"), (CLIFF[0].crest, "法肩")):
        pts = [(X(q[0]), Y(q[1])) for q in line
               if x0 - 40 <= q[0] <= x1 + 40 and z0 - 40 <= q[1] <= z1 + 40]
        if len(pts) < 2:
            continue
        o.append(PL(pts, stroke=col, sw=sw, dash="5 3"))
        if label:
            o.append(T(pts[len(pts) // 2][0] + 4, pts[len(pts) // 2][1] - 4, lab,
                       cls="jo", fill=col))


def cliff_cross(z, xa, xb, step=0.5):
    """東西の切り線 z が崖を横切る位置。返り値は [(法尻の x, 法肩の x)]。
    ⛔ 手で書かない — 区分の切り替わりを走査して拾う。"""
    C = CLIFF[0]
    xs = [xa + i * step for i in range(int((xb - xa) / step) + 1)]
    ks = [C.frac(x, z)[0] for x in xs]
    out, toe = [], None
    for i in range(1, len(xs)):
        if ks[i - 1] == "valley" and ks[i] == "cliff":
            toe = xs[i]
        elif ks[i - 1] == "cliff" and ks[i] == "plateau" and toe is not None:
            out.append((toe, xs[i]))
            toe = None
    # ⚠ 切り線が崖の帯の中で終わることがある(東西の崖を東西に切ると法肩に届かない)。
    #    そのときは**法尻だけ**返す(法肩は None)。⛔ 黙って落とさない。
    if toe is not None:
        out.append((toe, None))
    return out


def cliff_cross_ns(x, za, zb, step=0.5):
    """南北の切り線 x が崖を横切る位置。返り値は [(法尻の z, 法肩の z)]。"""
    C = CLIFF[0]
    zs = [za + i * step for i in range(int((zb - za) / step) + 1)]
    ks = [C.frac(x, z)[0] for z in zs]
    out, toe = [], None
    for i in range(1, len(zs)):
        if ks[i - 1] == "valley" and ks[i] == "cliff":
            toe = zs[i]
        elif ks[i - 1] == "cliff" and ks[i] == "plateau" and toe is not None:
            out.append((toe, zs[i]))
            toe = None
    return out


# ---------------------------------------------------------------- 明治16年の実測 vs 現況DEM
# ⭐ **これが裁定の根拠なので、裁定図より前に置く。**
# ⛔ 現況DEM の「造成前」は『当プロジェクトが流した造成の前』の意味であって**近代開発の前ではない**。
#    丹羽区画には衆議院議員会館の掘削と首相官邸側の盛土がそのまま入っている。
# ⛔ **名は「測ったこと」だけを言う。**旧名(近代の掘削 / 本物の地形 / 近代の盛土)は
#    Δ の符号にそのまま解釈を貼っていたが、2026-09-01 に「南は近代の盛土」の根拠が消えた
#    (錨2点が京極の区画内と判明)ので、**解釈は名から外した**。
MJ_CLASS = [("cut", "現況が復元より低い", "var(--cut3)"),
            ("real", "差が判定値以下(現況 ≒ 復元)", "var(--nomove)"),
            ("fill", "現況が復元より高い", "var(--fill3)")]


def flat_stat(geo, dem):
    """現況の「人工の平場」の量を**毎回数える**。⛔ セル数を文章へ書き写さない(規則4)。"""
    vs = [dem.h[j][i] for j in range(dem.nz) for i in range(dem.nx)
          if pip(geo.P, dem.x0 + i * dem.st, dem.z0 + j * dem.st)]
    n = len(vs)
    lo = [v for v in vs if v < 10.0]
    from collections import Counter
    mode, mn = Counter(round(v, 1) for v in lo).most_common(1)[0] if lo else (0.0, 0)
    return ("区画内 %s セルのうち %s(%.1f %%)が 10 m 未満で、"
            "その <b>%s セルが %.1f m ちょうど</b>に揃う【P 実測】"
            % ("{:,}".format(n), "{:,}".format(len(lo)), 100.0 * len(lo) / max(n, 1),
               "{:,}".format(mn), mode))


def mj_class(dz, tol):
    """dz = 現況 − 復元。⛔ **範囲を手で描かない** — Δ から機械的に三区分する。"""
    return "real" if abs(dz) <= tol else ("fill" if dz > 0 else "cut")


def mj_stats(d, geo, cur, rec):
    tol = d["meiji"]["classTol"]
    n = {k: 0 for k, _, _ in MJ_CLASS}
    ext = {k: 0.0 for k, _, _ in MJ_CLASS}
    for j in range(cur.nz):
        z = cur.z0 + j * cur.st
        for i in range(cur.nx):
            x = cur.x0 + i * cur.st
            if not pip(geo.P, x, z):
                continue
            dz = cur.h[j][i] - rec.h[j][i]
            k = mj_class(dz, tol)
            n[k] += 1
            if abs(dz) > abs(ext[k]):
                ext[k] = dz
    return n, ext, cur.st * cur.st


def meiji_svg(d, geo, cur, rec, kan, W=940.0):
    """明治16年の実測(錨)と現況DEM の対比。左=三区分の平面 / 右=錨ごとの実測値。"""
    tol = d["meiji"]["classTol"]
    P = geo.P
    # ⛔ 右の欄が伸びると下がはみ出す(2026-09-01 の機械検査で実際に 15px 越えた)。下の余白を取る。
    mw, top, bot = 430.0, 46.0, 150.0
    x0, x1 = min(p[0] for p in P) - 26, max(p[0] for p in P) + 12
    z0, z1 = min(p[1] for p in P) - 12, max(p[1] for p in P) + 12
    pj = Proj(x0, x1, z0, z1, W=mw, top=top, bottom=bot)
    X, Y, H = pj.X, pj.Y, pj.H
    o = _sv(W, H, "%s 明治16年の実測と現況DEM の対比(錨と三区分)" % kan)
    o.append(R(0, 0, W, H, fill="var(--paper)"))
    o.append(T(14, 18, "%s　明治16年の実測 vs 現況DEM — どこがどれだけ食い違うか" % kan,
               cls="big"))
    o.append(T(14, 32, "左: Δ = 現況 − 復元(明治16年の実測を錨にした面)を区画の中で三区分。"
                       "⛔ 範囲を手で描いたものではなく Δ から機械的に分けたもの。", cls="jo"))
    o.append(T(14, 44, "⛔ 符号に解釈を貼らない(錨の無い所では復元面が外挿)。", cls="jo"))
    st = cur.st
    cell = pj.L(st) + 0.6
    for j in range(cur.nz):
        z = cur.z0 + j * st
        if not (z0 <= z <= z1):
            continue
        for i in range(cur.nx):
            x = cur.x0 + i * st
            if not (x0 <= x <= x1) or not pip(P, x, z):
                continue
            k = mj_class(cur.h[j][i] - rec.h[j][i], tol)
            col = [c for kk, _, c in MJ_CLASS if kk == k][0]
            o.append(R(X(x), Y(z + st), cell, cell, fill=col, op=0.95))
    o.append(PL([(X(q[0]), Y(q[1])) for q in P], stroke="var(--ink)", sw=1.6, close=True))
    # 法尻・法肩(⚠ 折れ線。⛔ 一本の X では指せない)
    cliff_draw(o, X, Y, x0, x1, z0, z1, col="var(--ink)", sw=1.1)
    # 錨(明治16年の標高点)。⚠ `y` が null = 数字が判読不能。**位置だけを出す。**
    for a in RECON_SPEC["anchors"]:
        x, z = a["xz"]
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            continue
        ins = pip(P, x, z)
        o.append(CIR(X(x), Y(z), 4.2, fill="var(--paper)",
                     stroke="var(--ink)" if ins else "var(--dim)", sw=1.4))
        o.append(CIR(X(x), Y(z), 1.6, fill="var(--ink)" if ins else "var(--dim)",
                     stroke="none", sw=0))
        lb = "?" if a["y"] is None else "%.1f" % a["y"]
        lw = _tw(lb, "jo") + 6
        o.append(R(X(x) + 6, Y(z) - 6, lw, 12, fill="var(--paper)",
                   stroke="var(--rule)", sw=0.6))
        o.append(T(X(x) + 9, Y(z) + 3, lb, cls="jo",
                   fill="var(--ink)" if ins else "var(--dim)"))
    # 方位・スケール
    o.append(T(mw - 18, top + 12, "N", cls="big", anchor="middle"))
    o.append(LN(mw - 18, top + 16, mw - 18, top + 34, stroke="var(--ink)", sw=1.2))
    o.append(PL([(mw - 22, top + 22), (mw - 18, top + 14), (mw - 14, top + 22)],
                stroke="var(--ink)", sw=1.2))
    o.append(LN(16, H - 16, 16 + pj.L(100.0), H - 16, stroke="var(--ink)", sw=1.6))
    o.append(T(16 + pj.L(100.0) / 2, H - 4, "100 m", cls="jo", anchor="middle"))
    # 右 — 錨の実測値
    tx = mw + 20
    y = top + 4
    o.append(T(tx, y, "明治16年の標高点(五千分一東京図・原寸実見)", cls="an2b"))
    y += 18
    for c, lb in ((tx, "図葉"), (tx + 40, "読み"), (tx + 78, "世界座標"),
                  (tx + 168, "区画"), (tx + 196, "区分"), (tx + 240, "現況"),
                  (tx + 282, "差"), (tx + 322, "復元"), (tx + 362, "残差")):
        o.append(T(c, y, lb, cls="jo", fill="var(--dim)"))
    y += 4
    o.append(LN(tx, y, W - 18, y, stroke="var(--rule)", sw=0.8))
    y += 13
    ZL = {"valley": "谷底", "cliff": "崖", "plateau": "台地"}
    for a, c in zip(RECON_SPEC["anchors"], RECON_OUT["anchors"]):
        col = "var(--ink)" if c["in"] else "var(--dim)"
        use = a.get("use")
        unread = a["y"] is None
        o.append(T(tx, y, "%s" % a["sheet"], cls="jo", fill=col))
        o.append(T(tx + 40, y, "%s%s" % (a["mark"], "?" if unread else "%.1f" % a["y"]),
                   cls="jo", fill="var(--dim)" if unread else col))
        o.append(T(tx + 78, y, "(%.0f, %.0f)" % (a["xz"][0], a["xz"][1]), cls="jo", fill=col))
        o.append(T(tx + 168, y, "内" if c["in"] else "外", cls="jo", fill=col))
        o.append(T(tx + 196, y, "%s%s" % (ZL.get(c["zone"], c["zone"]),
                                          "" if c["zone"] != "cliff"
                                          else "(%.0f%%)" % (100 * c["f"])),
                   cls="jo", fill=col))
        o.append(T(tx + 240, y, "%.2f" % c["cur"], cls="jo", fill=col))
        if unread:
            o.append(T(tx + 282, y, "— 判読不能なので当てはめ・判定に使わない", cls="jo",
                       fill="var(--dim)"))
        else:
            o.append(T(tx + 282, y, "%+.2f" % (c["cur"] - a["y"]), cls="jo",
                       fill="var(--shu)" if abs(c["cur"] - a["y"]) > 1.0 else col))
            o.append(T(tx + 322, y, "%.2f" % c["recon"], cls="jo", fill=col))
            o.append(T(tx + 362, y, "%+.2f" % c["resid"], cls="jo",
                       fill=("var(--dim)" if use == "ref" else
                             "var(--shu)" if abs(c["resid"]) > 1.0 else "var(--take)")))
        y += 14
    y += 4
    o.append(LN(tx, y - 10, W - 18, y - 10, stroke="var(--rule)", sw=0.8))
    chk = [c for a, c in zip(RECON_SPEC["anchors"], RECON_OUT["anchors"])
           if a.get("use") == "check"]
    y += TW(o, tx, y,
            "「差」= 現況 − 明治の読み。「残差」= 復元面 − 明治の読み(**復元がその点を"
            "どれだけ再現できたか**)。⭐ **台地の錨は当てはめに入れず、検証にだけ使う** — "
            "復元は谷底の錨だけで組み立ててあるので、台地の錨の残差(%s)は**独立した検算**である。"
            "⚠ **`?` の錨は数字が判読不能**で、位置だけが読める【?】 — "
            "当てはめにも判定にも使っていない。⚠ **区画外の ⊙28 は参照**で、"
            "台地面の高さを挟むためだけに載せてある(残差は灰)。"
            % ("・".join("%s %+.2f m" % (q["id"], q["resid"]) for q in chk) or "—"),
            cls="jo", maxw=W - tx - 18, lh=13) * 13
    y += 6
    n, ext, ca = mj_stats(d, geo, cur, rec)
    tot = sum(n.values())
    o.append(T(tx, y, "区画内 %s セルの三区分(判定 |Δ| ≤ %.1f m を「本物」とする)"
               % ("{:,}".format(tot), tol), cls="an2b"))
    y += 16
    for k, lab, col in MJ_CLASS:
        o.append(R(tx, y - 9, 13, 11, fill=col, stroke="var(--rule)", sw=0.6))
        o.append(T(tx + 20, y, "%s … %s セル(%.1f %%)= %s m²　最大 %+.2f m"
                   % (lab, "{:,}".format(n[k]), 100.0 * n[k] / tot,
                      "{:,.0f}".format(n[k] * ca), ext[k]), cls="sl"))
        y += 16
    y += 4
    zp = RECON_OUT["zonePct"]
    zc = RECON_OUT["zoneCells"]
    o.append(T(tx, y, "復元面の三区分(区画の中の面積比)", cls="an2b"))
    y += 16
    o.append(T(tx, y, "谷底 %.1f %%(%s m²)／ 崖 %.1f %%(%s m²)／ **台地 %.1f %%**(%s m²)"
               .replace("**", "")
               % (zp["valley"], "{:,.0f}".format(zc["valley"] * ca),
                  zp["cliff"], "{:,.0f}".format(zc["cliff"] * ca),
                  zp["plateau"], "{:,.0f}".format(zc["plateau"] * ca)), cls="sl"))
    y += 18
    y += TW(o, tx, y,
            "⭐ **御殿を置ける台地は区画の %.1f %% しかない。** 残りは谷戸の底と崖で、"
            "**配置の大方針に直に効く**(⛔ どう置くかは配置の判断なので指図方は決めない)。"
            "○ の白抜き = 区画の外の錨(当てはめには使うが復元は**区画の中だけ**)。"
            % zp["plateau"], cls="jo", maxw=W - tx - 18, lh=13) * 13
    y += 4
    TW(o, tx, y,
       "⚠ **「現況 ≒ 復元」の区分が区画の中では %.1f %% しかない。** ⛔ **区画の中の西端・南の脚・"
       "北帯の東には錨が1点も無く、そこは谷底の平面の外挿である**【?】 — "
       "旧記が脚の根拠にしていた標高点2点は、原図の地境線から**京極の区画内**と分かって"
       "2026-09-01 に典拠から外した(未解決 P-18)。"
       % (100.0 * n["real"] / tot), cls="jo", maxw=W - tx - 18, lh=13, fill="var(--shu)")
    o.append(ENDSVG)
    return "".join(o)


def meiji_sec_ns_svg(d, geo, cur, rec, kan, W=940.0):
    """⭐ **南北断面**で重ねる。⛔ **これが無いと訂正した崖の東半が原理的に図に出ない** —
    崖は X ≳ −185 で**東西に走る**(法尻 Z≈803 / 法肩 Z≈819)ので、東西の切り線では
    その区間と平行になってしまう(2026-09-01 検図 K5)。切り位置は `meiji.cutX`。"""
    xs = d["meiji"].get("cutX") or []
    if not xs:
        return ""
    lm, rm, top, gp, bot = 54.0, 26.0, 52.0, 52.0, 128.0
    za, zb = 760.0, 892.0
    s = (W - lm - rm) / (zb - za)
    vs = s * VEX
    ys = []
    for x in xs:
        for z in [za + i * 2.0 for i in range(int((zb - za) / 2) + 1)]:
            ys += [cur(x, z), rec(x, z)]
    y0, y1 = math.floor(min(ys) - 2), math.ceil(max(ys) + 3)
    bh = (y1 - y0) * vs
    H = top + bh * len(xs) + gp * (len(xs) - 1) + bot
    o = _sv(W, H, "%s 明治の復元面と現況DEM の南北断面" % kan)
    o.append(R(0, 0, W, H, fill="var(--paper)"))
    o.append(T(14, 18, "%s　南北断面の対比 — 東西に走る崖を直交で切る(実線=復元面 / 破線=現況DEM)"
               "　垂直倍率 ×%.1f" % (kan, VEX), cls="big"))
    for kb, x in enumerate(xs):
        oy = top + (bh + gp) * kb

        def PX(z):
            return lm + (z - za) * s

        def PY(y, oy=oy):
            return oy + bh - (y - y0) * vs
        for yy in range(int(y0 // 5 * 5), y1 + 5, 5):
            if not (y0 <= yy <= y1):
                continue
            o.append(LN(PX(za), PY(yy), PX(zb), PY(yy), stroke="var(--rule)", sw=0.6))
            o.append(T(PX(za) - 6, PY(yy) + 3, "%d" % yy, cls="jo", anchor="end"))
        # 切り線が何を通るか(⛔ 手で書かない — 駒の外形で毎回判定する)
        hit = [m["label"] for _k, m in seat_bodies(d, geo)
               if abs(m["pos"][0] - x) <= m["w"] / 2.0]
        o.append(T(lm, oy - 12, "南北 x=%.0f(左=南 / 右=北)%s"
                   % (x, ("　通るもの: " + "・".join(hit)) if hit else ""), cls="an2b"))
        zsq = [za + i * 2.0 for i in range(int((zb - za) / 2) + 1)]
        o.append(PL([(PX(z), PY(cur(x, z))) for z in zsq], stroke="var(--dim)",
                    sw=1.4, dash="4 3"))
        o.append(PL([(PX(z), PY(rec(x, z))) for z in zsq], stroke="var(--ink)", sw=1.9))
        for i in range(len(zsq) - 1):
            if pip(geo.P, x, zsq[i]) and pip(geo.P, x, zsq[i + 1]):
                o.append(LN(PX(zsq[i]), PY(y0) + 8, PX(zsq[i + 1]), PY(y0) + 8,
                            stroke="var(--hei)", sw=4.0, op=0.45, cap="butt"))
        for tZ, cZ in cliff_cross_ns(x, za, zb):
            for zz, lab in ((tZ, "法尻"), (cZ, "法肩")):
                o.append(LN(PX(zz), PY(y1), PX(zz), PY(y0), stroke="var(--shu)",
                            sw=1.0, dash="5 3"))
                o.append(T(PX(zz), PY(y0) + 22, lab, cls="jo", anchor="middle",
                           fill="var(--shu)"))
        for a2 in RECON_SPEC["anchors"]:
            ax, az = a2["xz"]
            if a2["y"] is None or abs(ax - x) > 14 or not (za <= az <= zb):
                continue
            o.append(CIR(PX(az), PY(a2["y"]), 3.4, fill="var(--shu)",
                         stroke="var(--paper)", sw=1.0))
            o.append(T(PX(az) + 6, PY(a2["y"]) - 9, "%s%.1f(x=%.0f)"
                       % (a2["mark"], a2["y"], ax), cls="jo", fill="var(--shu)"))
    yn = H - bot + 46
    yn += TW(o, 14, yn,
             "⭐ **東西に走る崖(法尻 Z≈803 / 法肩 Z≈819)は、この向きでしか図に出ない。** "
             "⛔ **行き先未決の家臣長屋2棟はまさにこの帯に立っている** — "
             "x=−144 の切り線がその継ぎ目を通る。"
             "x=−170 は京極との境(北帯の南辺)の直下で、**区画線の上に立つ段が最大になる線**である。",
             cls="jo", maxw=W - 28, lh=14) * 14
    TW(o, 14, yn,
       "地盤線の下の太い帯 = 丹羽の区画(復元はこの中だけ)。"
       "⛔ **区画の外では実線と破線が一致する** — 復元を区画でクリップしているためで、"
       "**帯の端の段差がそのまま区画線の上に立つ段**である(摺り付けない)。"
       "⚠ 南の端(左)は脚の付け根で、**そこには明治の標高点が1点も無い**(未解決 P-18)。",
       cls="jo", maxw=W - 28, lh=14)
    o.append(ENDSVG)
    return "".join(o)


def meiji_sec_svg(d, geo, cur, rec, kan, W=940.0):
    """明治の骨格(復元面)と現況DEM を、同じ切り位置の東西断面で重ねる。"""
    zs = d["meiji"]["cutZ"]
    lm, rm, top, gp, bot = 54.0, 26.0, 52.0, 52.0, 112.0
    xa, xb = -380.0, -120.0
    s = (W - lm - rm) / (xb - xa)
    vs = s * VEX
    ys = []
    for z in zs:
        for x in [xa + i * 2.0 for i in range(int((xb - xa) / 2) + 1)]:
            ys += [cur(x, z), rec(x, z)]
    y0, y1 = math.floor(min(ys) - 2), math.ceil(max(ys) + 3)
    bh = (y1 - y0) * vs
    H = top + bh * len(zs) + gp * (len(zs) - 1) + bot
    o = _sv(W, H, "%s 明治の復元面と現況DEM の東西断面" % kan)
    o.append(R(0, 0, W, H, fill="var(--paper)"))
    o.append(T(14, 18, "%s　東西断面の対比 — 明治16年を錨にした復元面(実線)と現況DEM(破線)"
               "　垂直倍率 ×%.1f" % (kan, VEX), cls="big"))
    for kb, z in enumerate(zs):
        oy = top + (bh + gp) * kb

        def PX(x):
            return lm + (x - xa) * s

        def PY(y, oy=oy):
            return oy + bh - (y - y0) * vs
        for yy in range(int(y0 // 5 * 5), y1 + 5, 5):
            if not (y0 <= yy <= y1):
                continue
            o.append(LN(PX(xa), PY(yy), PX(xb), PY(yy), stroke="var(--rule)", sw=0.6))
            o.append(T(PX(xa) - 6, PY(yy) + 3, "%d" % yy, cls="jo", anchor="end"))
        o.append(T(lm, oy - 12, "東西 z=%.0f(左=西 / 右=東)" % z, cls="an2b"))
        xsq = [xa + i * 2.0 for i in range(int((xb - xa) / 2) + 1)]
        o.append(PL([(PX(x), PY(cur(x, z))) for x in xsq], stroke="var(--dim)",
                    sw=1.4, dash="4 3"))
        o.append(PL([(PX(x), PY(rec(x, z))) for x in xsq], stroke="var(--ink)", sw=1.9))
        # 区画の内外
        for i in range(len(xsq) - 1):
            if pip(geo.P, xsq[i], z) and pip(geo.P, xsq[i + 1], z):
                o.append(LN(PX(xsq[i]), PY(y0) + 8, PX(xsq[i + 1]), PY(y0) + 8,
                            stroke="var(--hei)", sw=4.0, op=0.45, cap="butt"))
        # ⛔ 名札を上に置くと明治の錨の名札とぶつかる(2026-08-31 レンダで実際にぶつかった)。**下へ。**
        # ⚠ 崖は折れ線なので、**切り線ごとに横切る位置が違う**(2026-09-01)。走査して拾う。
        for tX, cX in cliff_cross(z, xa, xb):
            for xx, lab in ((tX, "法尻" if cX is not None else "法尻(この線は法肩に届かない)"),
                            (cX, "法肩")):
                if xx is None:
                    continue
                o.append(LN(PX(xx), PY(y1), PX(xx), PY(y0),
                            stroke="var(--shu)", sw=1.0, dash="5 3"))
                o.append(T(PX(xx), PY(y0) + 22, lab, cls="jo", anchor="middle",
                           fill="var(--shu)"))
        # その切り線の上に載る錨(⛔ 数字が判読不能な錨は高さを持たないので描かない)
        na = 0
        for a, c in zip(RECON_SPEC["anchors"], RECON_OUT["anchors"]):
            ax, az = a["xz"]
            if a["y"] is None or abs(az - z) > 14 or not (xa <= ax <= xb):
                continue
            o.append(CIR(PX(ax), PY(a["y"]), 3.4, fill="var(--shu)",
                         stroke="var(--paper)", sw=1.0))
            # ⛔ 隣り合う錨は名札が重なる(2026-08-31 レンダで実際に重なった)。
            #    **上へ二段に振り、さらに左右へ逃がす** — 同じ切り線に載る錨は X が 16〜22m しか
            #    離れていないので上下だけでは足りず、下へ逃がすと地盤線の上に乗る。
            o.append(T(PX(ax) + (-6 if na % 2 == 0 else 6),
                       PY(a["y"]) - (9 if na % 2 == 0 else 23),
                       "%s%.1f(z=%.0f)" % (a["mark"], a["y"], az),
                       cls="jo", anchor="end" if na % 2 == 0 else "start",
                       fill="var(--shu)"))
            na += 1
    # ⚠ 帯の下の「法尻/法肩」の名札(PY(y0)+22)と注記がぶつかるので、注記を下げる
    yn = H - bot + 46
    yn += TW(o, 14, yn,
             "実線 = 明治16年を錨にした復元面(A案)／ 破線 = 現況DEM ／ "
             "地盤線の下の太い帯 = 丹羽の区画(復元はこの中だけ)／ "
             "朱の丸 = その切り線の近く(±14 m)に落ちる明治の標高点(名札は上下に振ってある)。"
             "⛔ **区画の外では両者が一致する** — 復元は丹羽の区画の中だけで行うからで、"
             "**区画線の上に段が立つのはそのため**である(摺り付けない)。",
             cls="jo", maxw=W - 28, lh=14) * 14
    TW(o, 14, yn,
       "⭐ **崖は切り位置ごとに違うところを横切る** — 訂正した崖は北で WNW–ESE の斜め、"
       "南東で東西に折れるので、**z=866 では区画の西寄り・z=812 では東の端で**切り線に当たる。"
       "⛔ 一本の東西断面では崖の姿が読めないので3本にしてある。"
       "⚠ **南の脚はこの断面には写らない** — 脚には明治の標高点が1点も無く、"
       "復元面は谷底の平面の外挿である(未解決 P-18)。",
       cls="jo", maxw=W - 28, lh=14)
    o.append(ENDSVG)
    return "".join(o)


SASHIZU_D = [None]      # `recon_table` が案の面を引くための控え(main が入れる)


def cliff_measure(opt):
    """案の面の上で崖を測る。⛔ **式ではなく実際に使う面から測る**(平滑化のぶん式より緩む)。
    返り値は (比高の一覧, 勾配の一覧, 水平幅の一覧)。"""
    f = sai_surf(opt)
    C = CLIFF[0]
    rise, slope, wid = [], [], []
    for c, t, w in C.profiles(lambda x, z: pip(GEOP[0], x, z), ds=4.0):
        r = f(c[0], c[1]) - f(t[0], t[1])
        rise.append(r)
        slope.append(100.0 * r / w)
        wid.append(w)
    return rise, slope, wid


def _offset_line(line, off):
    """折れ線を法線方向へ `off` m ずらす(左=高い側が正)。⛔ 頂点ごとに前後の線分の
    法線を平均するので、折れの内側で少し詰まる — 感度を見るための近似である。"""
    out = []
    n = len(line)
    for i, p in enumerate(line):
        segs = []
        if i > 0:
            segs.append((line[i - 1], p))
        if i < n - 1:
            segs.append((p, line[i + 1]))
        vx = vz = 0.0
        for a, b in segs:
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz) or 1.0
            vx += -dz / L
            vz += dx / L
        L = math.hypot(vx, vz) or 1.0
        out.append((p[0] + vx / L * off, p[1] + vz / L * off))
    return out


def anchor_robust(d, offs=(-4.0, -2.0, 0.0, 2.0, 4.0)):
    """⭐ **検算の錨(`use=check`)の残差が、崖の折れ線の位置の不確かさにどれだけ耐えるか。**
    ⛔ 「残差が小さいから台地面は正しい」と言う前に、**折れ線を法線方向へ ±4〜5 m 振って
    残差がどう動くか**を測る(折れ線そのものが確度P ±4〜5 m である)。
    2026-09-01 検図 K8: 振ると残差は符号ごと変わり、**この錨に台地面を 0.2 m の精度で
    決める力は無い**ことが分かった。"""
    vp = RECON_OUT["valleyPlane"]
    py = RECON_SPEC["plateau"]["y"]

    def valley(x, z):
        return vp["a"] + vp["b"] * x + vp["c"] * z
    out = []
    for a in RECON_SPEC["anchors"]:
        if a.get("use") != "check" or a["y"] is None:
            continue
        row = []
        for o in offs:
            cl = Cliff({"toe": _offset_line(CLIFF[0].toe, o),
                        "crest": _offset_line(CLIFF[0].crest, o)})
            row.append((o, cl.height(a["xz"][0], a["xz"][1], valley, py) - a["y"]))
        out.append((a, row))
    return out


def plateau_models(d, geo):
    """**台地面のモデル**を並べて比べる。⛔ 『等高線が無い』は『水平』を意味しない
    (同じ図葉の松江区画では等高線の無い台地面の水準点が 0.9 m 振れる)。
    ⭐ 読める2点を通す**一様勾配の面**を対抗仮説として立て、**隔たり・勾配・
    棟の位置での食い違い**を毎回算出する(2026-09-01 考証 Ko2)。返すのは
    (モデル名, 高さ関数, 確度) と、二点の隔たり・比高差・勾配。"""
    t = d["meiji"].get("tilt")
    A = {a["id"]: a for a in RECON_SPEC["anchors"]}
    p, q = A[t["through"][0]], A[t["through"][1]]
    dx, dz = q["xz"][0] - p["xz"][0], q["xz"][1] - p["xz"][1]
    L = math.hypot(dx, dz)
    dy = q["y"] - p["y"]
    ux, uz = dx / L, dz / L
    g = dy / L                                   # 勾配(進む向きに上がる量)

    def tilt(x, z):
        return p["y"] + ((x - p["xz"][0]) * ux + (z - p["xz"][1]) * uz) * g
    models = [("A案 水平面 %.2f m" % RECON_SPEC["plateau"]["y"],
               (lambda x, z: RECON_SPEC["plateau"]["y"]),
               "U(帯 %.1f〜%.1f m の中の一つの選び)"
               % (RECON_SPEC["plateau"]["band"][0], RECON_SPEC["plateau"]["band"][1])),
              ("B案 水平面 %.2f m" % RECON_OUT["plateauB"],
               (lambda x, z: RECON_OUT["plateauB"]),
               "U(現況の台地セルの中央値=近代の建設platform)"),
              ("東上がりの面(%s → %s)" % (p["id"], q["id"]), tilt,
               "A(%s の読み)/ B(%s の読み)/ P(座標 ±3 m)/ U(一様勾配という形)"
               % (p["id"], q["id"]))]
    return models, {"p": p, "q": q, "L": L, "dy": dy, "gradPct": 100.0 * g}


def plateau_model_table(d, geo):
    models, m = plateau_models(d, geo)
    # 台地の上に載る駒(復元面の区分で判定する。⛔ 手で並べない)
    bods = [b for _k, b in seat_bodies(d, geo)
            if CLIFF[0].frac(b["pos"][0], b["pos"][1])[0] == "plateau"]
    rows = []
    for kk, (nm, f, acc) in enumerate(models):
        cells = []
        for a in RECON_SPEC["anchors"]:
            if a["y"] is None or a.get("use") not in ("check", "ref"):
                continue
            zk, fr = CLIFF[0].frac(a["xz"][0], a["xz"][1])
            cells.append("%s <b>%+.2f m</b><br><span class='cert'>その点は %s%s</span>"
                         % (a["id"], f(a["xz"][0], a["xz"][1]) - a["y"],
                            {"valley": "谷底", "cliff": "崖の面", "plateau": "台地"}[zk],
                            "(法尻から %.0f %%)" % (100 * fr) if zk == "cliff" else ""))
        if kk == 2:
            sp = "<span class='cert'>—(この面が比較の基準)</span>"
        elif bods:
            dv = [abs(f(b["pos"][0], b["pos"][1]) - models[2][1](b["pos"][0], b["pos"][1]))
                  for b in bods]
            sp = "%.2f〜%.2f m<br><span class='cert'>台地に載る %d 駒</span>" % (
                min(dv), max(dv), len(bods))
        else:
            sp = "—"
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='cert'>%s</td></tr>"
                    % (nm, "　／　".join(cells) or "—", sp, acc))
    return ("<div class='tw'><table><thead><tr><th>台地面のモデル</th>"
            "<th>読める錨との差(復元 − 読み)</th>"
            "<th>台地の駒の位置で「東上がりの面」との違い</th><th>確度</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>⛔ <b>「等高線が無い」は「水平」を意味しない。</b>"
            "同じ図葉の松江区画では、等高線の無い台地面の水準点が <b>0.9 m</b> 振れている"
            "(考証方の実見)。⭐ <b>読める2点(%s %.1f m と %s %.1f m)は %.0f m 隔たって "
            "%.1f m 差</b>、すなわち <b>%.1f %% の東上がり</b>になる。"
            "<br>⛔ <b>%s は崖の面の上に落ちるので、そもそも台地面を直接は決めない</b> — "
            "表の「差」はその点まで<b>台地の面を延ばしたら</b>という仮の値である。"
            "<br>⛔ <b>どのモデルを採るかは考証の判断で、指図方は決めない</b>(未解決 P-15)。"
            "⚠ 表の <b>%s は当てはめに使っていない検算の点</b>、<b>%s は区画の外 10 m の参照</b>"
            "【B】である。</p>"
            % (m["p"]["id"], m["p"]["y"], m["q"]["id"], m["q"]["y"], m["L"], m["dy"],
               abs(m["gradPct"]), m["p"]["id"], m["p"]["id"], m["q"]["id"]))


def recon_table(d, geo, cur, rec):
    """復元の手順と、その当てはまり。⛔ **数値は仕様と面から毎回引く**(規則4)。"""
    C = RECON_OUT
    vp = C["valleyPlane"]
    pl = RECON_SPEC["plateau"]
    rows = []

    def row(no, name, how, fit, acc):
        rows.append("<tr><td><b>%s</b></td><td>%s</td><td class='note'>%s</td>"
                    "<td class='note'>%s</td><td class='cert'>%s</td></tr>"
                    % (no, name, how, fit, acc))
    row("①", "谷底",
        "<code>use=valley</code> の錨 %d 点への<b>最小二乗平面</b>。⛔ 係数は生成器が毎回当てはめる。"
        "⚠ <b>2026-09-01 に錨を2点外した</b> — ○11.3・○11.5 は原図の地境線から"
        "<b>京極備中守上屋敷の区画内</b>と判明した【A】"
        % len(vp["resid"]),
        "h = %.4f %+.6f·x %+.6f·z　／　<b>勾配 %.2f %%</b>　／　"
        "残差 最大 <b>%.2f m</b>(%s)"
        "<br>⛔ <b>南の脚と北帯の東には錨が1点も無く、そこは外挿</b>である — "
        "谷底に分類したセルのうち<b>錨から最も遠い点は %s m</b>先(%s)にあり、"
        "そこでの高さは<b>「平面」という形の仮定に全面的に依存する</b>【?】(未解決 P-18)"
        "<br>⚠ <b>残差 1〜3 m は較正に使った 5 辺の中の話である</b> — "
        "較正に使わなかった 2 辺では 20〜30 m ずれる。⛔ さらに、"
        "<b>区画(確度U のユーザー裁定)で明治図を較正し、その明治図で区画内の地形を"
        "決めているので、位置の精度の議論には循環が入っている</b>(考証 Ko3)"
        % (vp["a"], vp["b"], vp["c"], vp["gradPct"], vp["residMax"],
           "・".join("%s %+.2f" % (q[0], q[1]) for q in vp["resid"]),
           ("%.0f" % C["valleyExtrap"]["maxDist"]) if C.get("valleyExtrap") else "—",
           ("(%.0f, %.0f)" % tuple(C["valleyExtrap"]["at"]))
           if C.get("valleyExtrap") and C["valleyExtrap"]["at"] else "—"),
        "A(読み値)/ P(座標 ±3 m — 較正集合内。集合外は 20〜30 m)/ U(平面という形)")
    row("②", "崖",
        "<b>法尻と法肩の折れ線</b>のあいだを、両者からの符号つき距離の比で一次に結ぶ"
        "(算法は <code>Tools/Sashizu/cliff_polyline.py</code>)。"
        "⚠ <b>2026-09-01 に向きを訂正した</b> — 旧「法尻 X=−270・法肩 X=−240 の南北の直線」は"
        "誤りで、正しくは <b>WNW–ESE の斜め → X ≳ −185 で東西</b>(高い側は北東)。"
        "⚠ <b>折れ線の頂点は考証の実測</b>【P ±4〜5 m】で、指図方の裁定ではない",
        "<b>A案の面で</b> %s"
        "<br>⚠ <b>この値は解析の式ではなく、実際に使う面から測った値</b>である"
        "(継ぎ目を2回平滑化してあるので、式より少し緩む)。"
        "⛔ B案は台地面が高いぶん急になる(⑤ の表)"
        % surf_cliff(sai_opt(SASHIZU_D[0], "A")).split("<br>")[-1],
        "P(折れ線の実測 ±4〜5 m)/ U(一次で結ぶという形)")
    rb = anchor_robust(SASHIZU_D[0])
    row("③", "台地面",
        "<b>水平面</b>。根拠は明治16年図の法肩より東に<b>等高線が1本も無い</b>こと"
        "【A — 不存在の観測】。⛔ <b>ただし「等高線が無い」は「水平」を意味しない</b> — "
        "対抗仮説(東上がりの面)は下の「台地面のモデル」の表で比べる",
        "A案 <b>%.2f m</b> ／ B案 <b>%.2f m</b>(現況の台地セルの中央値)／ "
        "区画外10m の参照 <b>⊙28</b>【B】"
        "<br>⛔ <b>「A案の高さは錨 ⊙24.8 を再現する値だから正しい」という論は撤回した。</b>"
        "⊙24.8 は崖の面の上(法肩から少し下)に落ちるので台地面を直接は決めず、"
        "しかも <code>use:\"check\"</code>=<b>当てはめへ入れてはならない点</b>である。"
        "%s"
        "<br>⭕ いま言えるのは<b>台地面は帯 %.1f〜%.1f m のどこか【?】</b>ということだけで、"
        "A案も B案もその帯の中の一つの選びにすぎない(未解決 P-15)。"
        "<br>⛔ <b>水平面なので台地の上では規則3 が恒真に近い</b> — "
        "駒の下の起伏が 0.00 m になる(棟ごとの内訳の「下の起伏」の欄)"
        % (pl["y"], C["plateauB"],
           "".join("<br>⚠ <b>%s の残差は頑健でない</b> — 崖の折れ線を法線方向へ振ると "
                   "%s と動く(折れ線そのものが確度P ±4〜5 m)。<b>この錨は A案と B案を"
                   "弁別する力はあるが、台地面を 0.2 m の精度で決める根拠にはならない。</b>"
                   % (a["id"],
                      " ／ ".join("%+.0f m → %+.2f m" % (o, v) for o, v in row2))
                   for a, row2 in rb),
           pl["band"][0], pl["band"][1]),
        "A(等高線の不存在)/ ?(高さ — 帯でしか言えない)")
    row("④", "掘削の底の埋め戻し",
        "⛔ <b>別の手順を持たない</b> — ①②③ を区画の全域へ当てれば同時に成る。"
        "④ は③に含まれる",
        "⛔ <b>だから「骨格(①②)だけ」という中間案が取れない。</b>"
        "字義どおり ③④ を外すと、法肩(現況のまま=掘削矩形の底)が法尻(復元した谷底)より"
        "低くなるセルが <b>%d</b> 個(最大 <b>%.2f m</b>・z %s〜%s)出て、"
        "<b>崖が逆勾配になる</b>"
        % (C["skeletonInverted"]["cells"], C["skeletonInverted"]["max"],
           C["skeletonInverted"]["zRange"][0] if C["skeletonInverted"]["zRange"] else "—",
           C["skeletonInverted"]["zRange"][1] if C["skeletonInverted"]["zRange"] else "—"),
        "P(実測)")
    sens = C["plateauSens"]
    ks = sorted(sens.keys(), key=float)
    row("感度", "台地面を帯の端に振ったら",
        "区画内の Δ(復元 − 現況)の中央値がどう動くか。⛔ 手で持たず毎回計算する",
        "　／　".join("<b>%s m</b> → 中央 %+.2f m(上げ %+.2f / 下げ %+.2f)"
                      % (k, sens[k]["medianDelta"], sens[k]["maxUp"], sens[k]["maxDown"])
                      for k in ks),
        "P(算出)")
    return ("<div class='tw'><table><thead><tr><th>手順</th><th>何を</th><th>どう起こすか</th>"
            "<th>当てはまり(生成器が毎回算出)</th><th>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 裁定図(P-1)
# ⛔ **裁定を仰ぐときは名前と数字の羅列で選ばせない**(CLAUDE.md 2026-08-30 ユーザー指示)。
#    ①どこ ②現況の実測値 ③各案を**同じ縮尺で並べた**図 ④案ごとに動く数値 ⑤推奨と理由 を図にする。
# ⛔ 案の座標だけが json の設計値で、**埋没・面積・合格数・石段の段数はここで地盤から毎回算出する**(規則4)。
# ⛔ **選択肢に「何も動かさない」を入れない。** それは選べる案ではなく、現況の実測値は ② が持つ。
SAI_ST = {"move": "移す", "und": "<b>行き先未決</b>(復元した崖の面に載る)",
          "stay": "動かさない", "fix": "三案とも動かない(門は開口の芯に固定)"}
# ⚠ 図の中の埋没は**すべて %.2f** で出す(表・②の欄と桁を揃える。2026-08-31 検図 K-11)。
BADF = "%.2f"


def _sw(col):
    """凡例の色見本。⛔ 淡い色(var(--nomove) など)は文字色にすると読めないので**四角で示す**。"""
    return ('<span><span style="display:inline-block;width:14px;height:11px;background:%s;'
            'border:1px solid var(--rule);margin-right:5px;vertical-align:-1px"></span>' % col)


# ---- 図の中の文字は必ず幅を測ってから置く -------------------------------------
# ⛔ 2026-08-31 の検図で、④断面の注記(125字)が SVG の幅を 142.8px 超えて
#    末尾「…引き直す。」が切れていた。**1行に流し込まず、幅で折る。**
_FS = {"jo": 9.5, "sl": 10.5, "big": 15.0, "an2b": 11.5, "anG": 12.0, "anS2": 10.5, "cert": 12.0}


def _tw(s, cls="jo"):
    """SVG テキストのおおよその描画幅[px]。半角は 0.55em、全角は 1.0em で見積もる。"""
    fs = _FS.get(cls, 10.5)
    return sum(fs * (0.55 if ord(c) < 0x2000 else 1.0) for c in s.replace("**", ""))


_NOHEAD = "。、）)』」]・?!,."
_ATOM = set("0123456789.-−%m²・")


def _tokens(s):
    """折ってはいけない塊にまとめる。⛔ **数値の途中で折らない**
    (2026-08-31 の検図で『z 831.98〜846.02』が「z 831.」「98〜…」に割れた)。"""
    out = []
    cur = ""
    for ch in s:
        if (ch.isascii() and (ch.isalnum() or ch in _ATOM)) or ch in "².−":
            cur += ch
        else:
            if cur:
                out.append(cur)
                cur = ""
            out.append(ch)
    if cur:
        out.append(cur)
    return out


def _wrap(s, cls, maxw):
    """幅で折る。⛔ 行頭に句読点・閉じ括弧を残さない。⛔ 数値・英字の途中で折らない。"""
    out, cur = [], ""
    for tk in _tokens(s.replace("**", "")):
        if cur and _tw(cur + tk, cls) > maxw and tk[0] not in _NOHEAD:
            out.append(cur)
            cur = tk
        else:
            cur += tk
    if cur:
        out.append(cur)
    return out


def TW(o, x, y, s, cls="jo", maxw=900.0, lh=14.0, **kw):
    """折り返して置く。**返り値は使った行数**(下の余白を計算するのに要る)。"""
    ls = _wrap(s, cls, maxw)
    for i, ln in enumerate(ls):
        o.append(T(x, y + i * lh, ln, cls=cls, **kw))
    return len(ls)


# 案ごとに読む面。⛔ **裁定の三案は棟ではなく地盤が動く**ので、埋没は案ごとに別の面で測る。
#    `main()` が組み立てる(`current` = 現況 / `recon` = A案の復元面 / `reconB` = B案の復元面)。
SURF = {}
RECON_SPEC = {}          # niwa_sakyo_edo_recon.json(復元の手順の仕様。人が書く)
RECON_OUT = {}           # niwa_sakyo_edo_world.json の `_computed`(生成器が書いた算出値)


def sai_surf(opt):
    return SURF[opt.get("surface", "current")]


def surf_plateau(opt):
    """案ごとの台地面[m]。⛔ **手で持たない** — A案は復元の仕様、B案は復元の生成器の算出値。"""
    return (RECON_SPEC["plateau"]["y"] if opt["surface"] == "recon"
            else RECON_OUT["plateauB"])


def surf_cliff(opt):
    """案ごとの崖(法尻 → 法肩)。⛔ **比高も勾配も手で持たない** — 面から毎回測る。
    ⚠ 崖は折れ線なので「X=◯ → X=◯」では書けない — **法肩に沿った標本の幅・比高・勾配**で出す。"""
    if opt["surface"] == "current":
        return "復元しない(現況の崖は近代の掘削で失われている)"
    rise, slope, wid = cliff_measure(opt)
    if not rise:
        return "—"
    return ("折れ線(北=WNW–ESE の斜め → X ≳ −185 で東西)／ 標本 %d<br>"
            "水平幅 %.1f〜%.1f m ／ 比高 %.2f〜%.2f m ／ 勾配 %.0f〜%.0f %%"
            % (len(rise), min(wid), max(wid), min(rise), max(rise),
               min(slope), max(slope)))


def surf_seam(geo, opt):
    """区画線の上に立つ段(復元 − 現況)。⚠ 摺り付けないので、隣家との食い違いそのもの。"""
    if opt["surface"] == "current":
        return "無し(現況のまま)"
    f, cur = sai_surf(opt), SURF["current"]
    st = cur.st
    v = []
    for j in range(cur.nz):
        z = cur.z0 + j * st
        for i in range(cur.nx):
            x = cur.x0 + i * st
            if not pip(geo.P, x, z):
                continue
            if any(not pip(geo.P, x + dx, z + dz)
                   for dx, dz in ((-st, 0), (st, 0), (0, -st), (0, st))):
                v.append(abs(f.h[j][i] - cur.h[j][i]))
    if not v:
        return "—"
    v.sort()
    return ("最大 <b>%.2f m</b> ／ 中央 %.2f m(区画線に接する %d セル)"
            % (v[-1], v[len(v) // 2], len(v)))


def seam_by_edge(d, geo, opt, ds=0.5, off=1.0):
    """**辺ごと**の区画線の段(復元面の内側 − 現況の外側)。⛔ 全周の最大だけでは
    「相手が後で揃える段」と「永久に残る段」が混ざる(2026-09-01 検図 K7)。
    返すのは [(辺index, 相手の別, 最大, 中央)]。相手の別は `neighbors` から引く。"""
    if opt["surface"] == "current":
        return []
    f, cur = sai_surf(opt), SURF["current"]
    who = {}
    for nb in d["neighbors"]:
        for ei in nb["edges"]:
            who.setdefault(ei, []).append(nb)
    out = []
    for e in d["edges"]:
        a, b, L, dd = geo.edge(e["i"])
        nx2, nz2 = geo.outward(e["i"])
        v = []
        t = 0.0
        while t <= L:
            x, z = a[0] + dd[0] * t, a[1] + dd[1] * t
            v.append(abs(f(x - nx2 * off, z - nz2 * off) - cur(x + nx2 * off, z + nz2 * off)))
            t += ds
        v.sort()
        nb = who.get(e["i"], [])
        street = any(q["id"] == "(街路)" for q in nb)
        parcel = any(q["id"] != "(街路)" for q in nb)
        kind = ("街路+隣家" if street and parcel else
                "街路" if street else "隣家" if parcel else "?")
        out.append((e["i"], e["label"], L, kind,
                    v[-1] if v else 0.0, v[len(v) // 2] if v else 0.0,
                    "・".join(q["label"] for q in nb) or "—"))
    return out


def seam_by_edge_html(d, geo, opt):
    rows = seam_by_edge(d, geo, opt)
    if not rows:
        return ("<b>区画線の段(辺ごと)</b> 無し(現況のまま)　／　"
                "⛔ <b>この案は段を作らないかわりに、史実との食い違いをそのまま残す。</b>")
    st = [q for q in rows if "街路" in q[3]]
    nb = [q for q in rows if q[3] == "隣家"]

    def one(q):
        return ("辺%d %s <b>最大 %.2f m</b>(中央 %.2f m・長さ %.0f m%s)"
                % (q[0], q[1], q[4], q[5], q[2],
                   "・<b>%s</b>" % q[3] if q[3] == "街路+隣家" else ""))
    return ("<b>区画線の段(辺ごと)</b><br>"
            "<b>隣家に面する辺</b>(相手が自分の区画で復元すれば縮む見込み): %s"
            "<br><b style='color:var(--shu)'>街路に面する辺</b>"
            "(⛔ 街路は規則9で永久に現地形のまま = <b>恒久的に残る段</b>): %s"
            "<br>⛔ <b>当図は <code>terraceWalls</code> が空で、土留めも法面も1本も無い</b>"
            "(スキル §3b 違反)。街路側の段は<b>石垣か法面で受けるほかない</b> — "
            "どちらにするかは設計の判断なので指図方は決めない。"
            % ("　／　".join(one(q) for q in nb) or "—",
               "　／　".join(one(q) for q in st) or "—"))


GEOP = [None]            # `surf_cliff` が区画多角形を引くための控え(main が入れる)


def surf_delta(geo, opt):
    """その案で**地盤がどれだけ動くか**。区画内のセルを現況と突き合わせて毎回数える。"""
    f = sai_surf(opt)
    cur = SURF["current"]
    n = tot = 0
    up = down = 0.0
    vu = vd = 0.0
    for j in range(cur.nz):
        z = cur.z0 + j * cur.st
        for i in range(cur.nx):
            x = cur.x0 + i * cur.st
            if not pip(geo.P, x, z):
                continue
            tot += 1
            dz = f.h[j][i] - cur.h[j][i]
            if abs(dz) <= 0.05:
                continue
            n += 1
            up, down = max(up, dz), min(down, dz)
            if dz > 0:
                vu += dz
            else:
                vd -= dz
    a = cur.st * cur.st
    return {"n": n, "tot": tot, "up": up, "down": down,
            "volUp": vu * a, "volDown": vd * a, "cellArea": a}


def sai(d):
    return d["saitei"]["P-1"]


def sai_opt(d, key):
    return [q for q in sai(d)["options"] if q["key"] == key][0]


def sai_gian(opt):
    """A/B/C と kosho.md の 案(a)(b)(c) の対応。⛔ 図だけを見る読み手が取り違えないよう**図に出す**
    (2026-08-31 検図 K-8: 対応表が kosho.md にしか無く、B案の中身が食い違ったまま潜伏した)。"""
    return "%s案(=%s)" % (opt["key"], opt.get("gian", "?"))


def body_on_cliff(b):
    """駒の外形(中心・四隅・四辺中点の9点)が**復元した崖の面**に掛かるか。
    ⛔ 「どの駒が行き先未決か」を手で並べない — 崖を動かせば結果が変わるので毎回測る
    (2026-09-01 の崖の訂正で、台所と家臣長屋2棟が新たに崖へ載った)。"""
    ex, ez = foot(b)
    x, z = b["pos"]
    return any(CLIFF[0].frac(x + i * ex, z + j * ez)[0] == "cliff"
               for i in (-1, 0, 1) for j in (-1, 0, 1))


def sai_bodies(d, geo, opt):
    """案ごとの棟の姿。`(kind, 移したあとの駒, 扱い, 現況の位置)`。
    ⭐ **表門も CenterSeat で地形へ載るので規則3の対象に入れる**(其四と同じ集合)。
    門は三案とも動かないので `fix` — <b>どの案を採っても門の埋没は残る</b>ことが表と図に出る。"""
    mv = opt.get("move", {})
    recon = opt["surface"] != "current"
    out = []
    for kind, m in seat_bodies(d, geo):
        b = dict(m)
        if kind == "門":
            st = "fix"
        elif m["name"] in mv:
            b["pos"] = list(mv[m["name"]])
            st = "move"
        elif recon and body_on_cliff(b):
            # ⛔ 復元する案では**崖の面に載る駒**が行き先未決になる。名前で並べず毎回測る。
            st = "und"
        else:
            st = "stay"
        out.append((kind, b, st, tuple(m["pos"])))
    return out


def sai_well_pos(opt, w):
    """案ごとの井戸の位置。`moveWell` に無ければ現況のまま。"""
    return list(opt.get("moveWell", {}).get(w["name"], w["pos"]))


def sai_bad(d, dem, opt, b, st):
    """案ごとの埋没[m]。⛔ **面は案ごとに違う**(`dem` は無視して `sai_surf` を使う)。
    行き先が未決の駒は None(=図と表で「?」)。"""
    if st == "und":
        return None
    f = sai_surf(opt)
    return nat_range(b, f)[1] - seat_of(b, f, sink_of(d, b))


def sai_relief(opt, b):
    """その案の面の、駒の外形の下の**起伏**[m]。
    ⛔ **これを併記しないと『規則3 に通った』が恒真かどうか読めない** — 台地を水平面で
    復元しているので、台地の上では起伏が 0.00 で、埋没は沈め代そのものになる。"""
    lo, hi = nat_range(b, sai_surf(opt))
    return hi - lo


def sai_metrics(d, geo, dem, opt):
    rows = [(k, b, st, old, sai_bad(d, dem, opt, b, st))
            for k, b, st, old in sai_bodies(d, geo, opt)]
    known = [r[4] for r in rows if r[4] is not None]
    ok = sum(1 for v in known if v <= 0.5)
    return rows, (max(known) if known else None), ok, len(known), len(rows)


def sai_metrics_all(d, geo, opt):
    """⭐ **行き先未決の駒を「現位置のまま」として算入した成績。**
    ⛔ **案ごとに分母が違う表を並べてはならない**(2026-09-01 検図 K4)— A案・B案は
    崖に載る駒を分母から外すのに C案は外さないので、**外した駒こそ最も深く埋まる駒**
    であるにもかかわらず A案が実力以上に良く見えていた。**同じ 10 駒・同じ位置**で測る。"""
    f = sai_surf(opt)
    vals = [nat_range(b, f)[1] - seat_of(b, f, sink_of(d, b))
            for _k, b, _st, _o in sai_bodies(d, geo, opt)]
    return max(vals), sum(1 for v in vals if v <= 0.5), len(vals)


def sai_overlaps(d, geo, opt):
    """案の中で外形どうしが重なる組。**A案の3つのベンチは棟ごとに独立に探した候補なので重なる** —
    それを隠すと『確定した配置』に見えてしまう(2026-08-31 自己検図)。
    返すのは (Aの名, Bの名, 重なり幅, 重なり奥行, 面積, Aの外形に対する割合, Bの外形に対する割合)。
    ⛔ **面積だけでは「呑まれている」ことが読めない** — 割合まで返す(2026-08-31 検図 K-3)。"""
    B = [(b, st) for k, b, st, _ in sai_bodies(d, geo, opt) if st != "und" and k != "門"]
    out = []
    for i in range(len(B)):
        for j in range(i + 1, len(B)):
            A, C = B[i][0], B[j][0]
            ax, az = A["pos"]
            cx, cz = C["pos"]
            ox = min(ax + A["w"] / 2, cx + C["w"] / 2) - max(ax - A["w"] / 2, cx - C["w"] / 2)
            oz = min(az + A["d"] / 2, cz + C["d"] / 2) - max(az - A["d"] / 2, cz - C["d"] / 2)
            if ox <= 0.01 or oz <= 0.01:
                continue
            # ⛔ 機械検査と同じ**除外規約②** — 長屋どうしで芯間が壁の実寸に一致する組は
            #    軒が重なるのが正しい姿(P-4 が別に見る)。ここで拾うと案の欠陥に見えてしまう。
            if ("nagaya" in A["asset"].lower() and "nagaya" in C["asset"].lower()
                    and abs(math.hypot(cx - ax, cz - az) - d["const"]["nagayaModLR"]) <= 0.20):
                continue
            ar = ox * oz
            out.append((A["label"], C["label"], ox, oz, ar,
                        100.0 * ar / (A["w"] * A["d"]), 100.0 * ar / (C["w"] * C["d"])))
    out.sort(key=lambda q: -q[4])
    return out


def sai_footprint(d, geo, opt):
    """案ごとの建築面積。**(外形の総和, 重なりを除いた実面積)**。
    ⛔ 建蔽率は屋根の水平投影の**和集合**で数えないと、重なった分を二重に数える(2026-08-31 検図 K-3)。"""
    rects = [(b["pos"][0] - b["w"] / 2, b["pos"][0] + b["w"] / 2,
              b["pos"][1] - b["d"] / 2, b["pos"][1] + b["d"] / 2)
             for k, b, st, _ in sai_bodies(d, geo, opt) if st != "und" and k != "門"]
    tot = sum((r[1] - r[0]) * (r[3] - r[2]) for r in rects)
    xs = sorted(set([r[0] for r in rects] + [r[1] for r in rects]))
    zs = sorted(set([r[2] for r in rects] + [r[3] for r in rects]))
    uni = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            if any(r[0] < cx < r[1] and r[2] < cz < r[3] for r in rects):
                uni += (xs[i + 1] - xs[i]) * (zs[j + 1] - zs[j])
    return tot, uni


def sai_kaidans(d, dem, opt):
    """案が新設する石段廊下。**両端の座標だけが設計値で、落差・段数・必要水平は地盤から出す**(規則4)。
    ⛔ 直線で入らないときは §1f のとおり**折返し**にして水平を半分にする。"""
    C = d["const"]
    out = []
    for k in opt.get("kaidans", []):
        a, b = k["from"], k["to"]
        ya, yb = dem(*a), dem(*b)
        rise = abs(ya - yb)
        n, need, half = kaidan_need(rise, C)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        form = "直線" if L >= need else ("折返し" if L >= half else "入らない")
        out.append(dict(k, ya=max(ya, yb), yb=min(ya, yb), rise=rise, n=n,
                        need=need, half=half, L=L, form=form, ok=(L >= half)))
    return out


def sai_terrain_stats(d, geo, dem):
    """区画内の地盤の内訳。**台地(平場の候補)と低地(人工の平場)がどれだけ在るか**。"""
    S = sai(d)
    st = dem.st
    tot = hi = lo = 0
    for j in range(dem.nz):
        z = dem.z0 + j * st
        for i in range(dem.nx):
            x = dem.x0 + i * st
            if not pip(geo.P, x, z):
                continue
            v = dem.h[j][i]
            tot += 1
            if v >= S["plateau"]:
                hi += 1
            if v < S["lowland"]:
                lo += 1
    return tot, hi, lo, st * st


def sai_low_in_crop(d, geo, dem):
    """低地(=C案が作り直す範囲)のうち、③の切り取り枠に**写っている割合**。
    ⛔ 写っていない分を黙っていると、C案の規模が図から読めない(2026-08-31 検図 K-7)。"""
    S = sai(d)
    cr = S["crop"]
    st = dem.st
    tot = ins = 0
    for j in range(dem.nz):
        z = dem.z0 + j * st
        for i in range(dem.nx):
            x = dem.x0 + i * st
            if not pip(geo.P, x, z) or dem.h[j][i] >= S["lowland"]:
                continue
            tot += 1
            if cr["x0"] <= x <= cr["x1"] and cr["z0"] <= z <= cr["z1"]:
                ins += 1
    return tot, ins, st * st


def sai_key_svg(d, geo, dem, kan, W=940.0):
    """① どこの話か(位置図・小)+ ② いま何がどうなっているか(現況の実測値)。"""
    S = sai(d)
    cr = S["crop"]
    P = geo.P
    mw, top, bot = 300.0, 30.0, 30.0
    x0, x1 = min(p[0] for p in P) - 8, max(p[0] for p in P) + 8
    z0, z1 = min(p[1] for p in P) - 8, max(p[1] for p in P) + 8
    pj = Proj(x0, x1, z0, z1, W=mw, top=top, bottom=bot)
    X, Y = pj.X, pj.Y
    H = pj.H
    o = _sv(W, H, "%s 裁定図(P-1)位置図と現況の実測値" % kan)
    o.append(R(0, 0, W, H, fill="var(--paper)"))
    st = dem.st
    cell = pj.L(st) + 0.6
    for j in range(dem.nz):
        z = dem.z0 + j * st
        if not (z0 <= z <= z1):
            continue
        for i in range(dem.nx):
            x = dem.x0 + i * st
            if not (x0 <= x <= x1):
                continue
            o.append(R(X(x), Y(z + st), cell, cell, fill=dem_color(dem.h[j][i]), op=0.9))
    # C案が作り直す範囲(=低地)を区画の全域で示す。③の枠に入りきらないので**ここで全体を出す**
    for j in range(dem.nz):
        z = dem.z0 + j * st
        if not (z0 <= z <= z1):
            continue
        for i in range(dem.nx):
            x = dem.x0 + i * st
            if not (x0 <= x <= x1) or dem.h[j][i] >= S["lowland"] or not pip(P, x, z):
                continue
            o.append(R(X(x), Y(z + st), cell, cell, fill=_bur(), op=0.7))
    o.append(PL([(X(q[0]), Y(q[1])) for q in P], stroke="var(--ink)", sw=1.6, close=True))
    # 埋没の大きい駒に印(どこの話かを図の上で指させる)。
    # ⛔ 段彩の赤系の上では朱が沈むので**濃紺の枠+白抜きの名札**にする(2026-08-31 検図 K-10)。
    for k, (kind, m) in enumerate(all_bodies(d)):
        if m["name"] not in S["keyBodies"]:
            continue
        ex, ez = foot(m)
        x, z = m["pos"]
        o.append(R(X(x - ex), Y(z + ez), pj.L(2 * ex), pj.L(2 * ez),
                   fill="var(--ink)", stroke="var(--ink)", sw=1.4, op=0.30))
        o.append(R(X(x - ex), Y(z + ez), pj.L(2 * ex), pj.L(2 * ez),
                   fill="none", stroke="var(--ink)", sw=1.4))
        lw = _tw(m["label"], "jo") + 6
        o.append(R(X(x) - lw / 2, Y(z) - 6, lw, 12, fill="var(--paper)", stroke="var(--ink)", sw=0.6))
        o.append(T(X(x), Y(z) + 3, m["label"], cls="jo", anchor="middle", fill="var(--ink)"))
    gx, gz = geo.gate
    o.append(CIR(X(gx), Y(gz), 3.5, fill="var(--shu)", stroke="var(--paper)", sw=1.0))
    o.append(T(X(gx) - 6, Y(gz) + 3, "表門", cls="jo", anchor="end", fill="var(--shu)"))
    # 三案を並べた図の切り取り範囲
    o.append(R(X(cr["x0"]), Y(cr["z1"]), pj.L(cr["x1"] - cr["x0"]), pj.L(cr["z1"] - cr["z0"]),
               fill="none", stroke="var(--shu)", sw=1.6, dash="6 3"))
    o.append(T(X(cr["x0"]) + 3, Y(cr["z1"]) - 4, "③の範囲", cls="jo", fill="var(--shu)"))
    o.append(T(14, 18, "%s　裁定図(P-1)　① どこの話か　② いまどうなっているか" % kan, cls="big"))
    # 方位とスケール(其一と同じ作法)
    o.append(T(mw - 16, top + 12, "N", cls="big", anchor="middle"))
    o.append(LN(mw - 16, top + 16, mw - 16, top + 34, stroke="var(--ink)", sw=1.2))
    o.append(PL([(mw - 20, top + 22), (mw - 16, top + 14), (mw - 12, top + 22)],
                stroke="var(--ink)", sw=1.2))
    sb = 100.0
    o.append(LN(16, H - 16, 16 + pj.L(sb), H - 16, stroke="var(--ink)", sw=1.6))
    o.append(T(16 + pj.L(sb) / 2, H - 4, "%.0f m" % sb, cls="jo", anchor="middle"))
    # ② 現況の実測値
    tot, phi, plo, ca = sai_terrain_stats(d, geo, dem)
    tx = mw + 26
    y = top + 6
    o.append(T(tx, y, "② いま何がどうなっているか(現況の実測値)", cls="an2b"))
    y += 20
    rows = []
    for kind, m in seat_bodies(d, geo):
        bad = nat_range(m, dem)[1] - seat_of(m, dem, sink_of(d, m))
        rows.append((bad, m["label"], m["pos"]))
    rows.sort(key=lambda q: -q[0])
    for bad, lb, ps in rows:
        col = "var(--shu)" if bad > 0.5 else "var(--take)"
        o.append(T(tx, y, ("✗ " if bad > 0.5 else "○ ") + lb, cls="sl", fill=col))
        o.append(T(tx + 108, y, "(%.2f, %.2f)" % (ps[0], ps[1]), cls="jo"))
        o.append(T(tx + 216, y, ("埋没 " + BADF + " m") % bad, cls="sl", fill=col))
        y += 15
    y += 8
    o.append(LN(tx, y - 12, W - 18, y - 12, stroke="var(--rule)", sw=0.8))
    o.append(T(tx, y, "区画内 %s セル(1セル %.2f m²)のうち" % ("{:,}".format(tot), ca), cls="jo"))
    y += 14
    o.append(T(tx, y, "　低地 %.2f m 未満 … %s セル(%.2f %%)= %s m²【人工の平場】"
               % (S["lowland"], "{:,}".format(plo), 100.0 * plo / tot,
                  "{:,.0f}".format(plo * ca)), cls="sl", fill="var(--shu)"))
    y += 15
    o.append(T(tx, y, "　台地 %.2f m 以上 … %s セル(%.2f %%)= %s m²【A案の受け皿】"
               % (S["plateau"], "{:,}".format(phi), 100.0 * phi / tot,
                  "{:,.0f}".format(phi * ca)), cls="sl", fill="var(--take)"))
    y += 15
    ab = sum(m["w"] * m["d"] for _, m in all_bodies(d))
    o.append(T(tx, y, "　棟+付属の建築面積の合計 %s m²(台地の %.2f %%)"
               % ("{:,.0f}".format(ab), 100.0 * ab / (phi * ca)), cls="sl"))
    y += 18
    lt, li, lca = sai_low_in_crop(d, geo, dem)
    y += TW(o, tx, y, "朱の斜線 = 低地(C案が作り直す範囲)。区画全体で %s m² あり、"
                      "③の切り取り枠に写るのはそのうち %.1f %%(%s m²)なので、"
                      "**範囲の全体はこの位置図で見る**。"
            % ("{:,.0f}".format(lt * lca), 100.0 * li / lt, "{:,.0f}".format(li * lca)),
            cls="jo", maxw=W - tx - 18, lh=13) * 13
    o.append(T(tx, y, "○ = 規則3(埋没 ≤ 0.50 m)に通る ／ ✗ = 通らない", cls="jo"))
    o.append(ENDSVG)
    return "".join(o)


def sai_plan_svg(d, geo, dem, kan, W=940.0):
    """③ 三案を**同じ縮尺で横に並べる**。⛔ 案ごとに別の図にしない — 並べないと差が読めない。"""
    S = sai(d)
    cr = S["crop"]
    lm, gp, top, bot = 10.0, 16.0, 128.0, 104.0
    pw = (W - lm * 2 - gp * 2) / 3.0
    s = pw / (cr["x1"] - cr["x0"])
    ph = (cr["z1"] - cr["z0"]) * s
    H = top + ph + bot
    o = _sv(W, H, "%s 三案の配置比較" % kan)
    o.append(R(0, 0, W, H, fill="var(--paper)"))
    o.append(T(14, 18, "%s　③ 三案を同じ縮尺で並べる(三面とも同じ範囲・同じ大きさ・同じ縮尺)"
               % kan, cls="big"))
    o.append(T(14, 34, "外周(築地塀・盲長屋)と表門は三案とも動かない。動くのは棟(A案・B案)か地盤(C案)だけ。",
               cls="jo"))
    _tot, _phi, plo, ca = sai_terrain_stats(d, geo, dem)
    st = dem.st
    cell = s * st + 0.6
    for kp, opt in enumerate(S["options"]):
        ox = lm + (pw + gp) * kp
        rows, mx, ok, nk, nb = sai_metrics(d, geo, dem, opt)

        def X(x, ox=ox):
            return ox + (x - cr["x0"]) * s

        def Y(z):
            return top + ph - (z - cr["z0"]) * s
        # 見出し。⛔ **案名・題・一行説明を3段に分ける** — 1行に詰めると題が枠の外で切れる
        #   (2026-08-31 の検図でB案の題「…一段低い郭にする」の末尾が消えた)。
        o.append(R(ox, top - 58, pw, 54, fill="var(--paper2)", stroke="var(--rule)", sw=0.8))
        o.append(T(ox + 7, top - 43, sai_gian(opt), cls="an2b"))
        if opt.get("tag"):
            o.append(T(ox + pw - 7, top - 43, "【%s】" % opt["tag"], cls="anG", anchor="end"))
        TW(o, ox + 7, top - 28, opt["label"], cls="an2b", maxw=pw - 14, lh=13)
        o.append(T(ox + 7, top - 13, opt["short"], cls="jo"))
        # ⛔ **面ごとにクリップする。** 区画の南の脚(z 678〜802)と辺1/辺3 の塀は切り取り範囲の
        #   外まで延びるので、クリップしないと下の注記を縦線が突き抜ける(2026-08-31 自己検図)。
        o.append('<clipPath id="sp%d_%d"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                 '</clipPath><g clip-path="url(#sp%d_%d)">'
                 % (_SVN[0], kp, ox, top, pw, ph, _SVN[0], kp))
        # 地盤 — ⛔ **案ごとに別の面**(動くのは棟ではなく地盤)
        sf = sai_surf(opt)
        o.append('<g opacity="1">')
        for j in range(sf.nz):
            z = sf.z0 + j * st
            if not (cr["z0"] - st <= z <= cr["z1"]):
                continue
            for i in range(sf.nx):
                x = sf.x0 + i * st
                if not (cr["x0"] - st <= x <= cr["x1"]):
                    continue
                o.append(R(X(x), Y(z + st), cell, cell, fill=dem_color(sf.h[j][i]), op=0.9))
        o.append("</g>")
        # 崖の法尻・法肩(三案とも同じ線)。⛔ 復元した崖がどこかを図の上で指させるため
        cliff_draw(o, X, Y, cr["x0"], cr["x1"], cr["z0"], cr["z1"],
                   col="var(--dim)", sw=1.0)
        o.append(PL([(X(q[0]), Y(q[1])) for q in geo.P], stroke="var(--ink)", sw=1.4, close=True))
        # 動かない要素(外周・門)
        for r in d["runs"]:
            a, b = geo.run_span(r)
            col = "var(--nagaya)" if r["kind"] == "Nagaya" else "var(--hei)"
            o.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), stroke=col,
                        sw=3.0 if r["kind"] == "Nagaya" else 1.8, cap="butt", op=0.85))
        for e in d["edges"]:
            if e["run"] is None:
                a, b, _, _ = geo.edge(e["i"])
                o.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]),
                            stroke="var(--shu)", sw=1.6, dash="3 4"))
        gx, gz = geo.gate
        o.append(CIR(X(gx), Y(gz), 3.4, fill="var(--shu)", stroke="var(--paper)", sw=1.0))
        # 石段廊下(その案が新設するもの)
        for kd in sai_kaidans(d, dem, opt):
            a, b = kd["from"], kd["to"]
            o.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]),
                        stroke="var(--roka)", sw=3.2, cap="butt", op=0.95))
            nb2 = max(2, min(kd["n"], 14))
            for i in range(1, nb2):
                t = i / float(nb2)
                px, pz = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                dx, dz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dz)
                nx_, nz_ = -dz / L * 2.6, dx / L * 2.6
                o.append(LN(X(px) - nx_, Y(pz) + nz_, X(px) + nx_, Y(pz) - nz_,
                            stroke="var(--paper)", sw=0.8))
            o.append(T((X(a[0]) + X(b[0])) / 2 + 6, (Y(a[1]) + Y(b[1])) / 2,
                       kd["name"], cls="jo", fill="var(--roka)"))
        # 棟
        kaku = opt.get("kaku", {})
        for kb, (kind, b, sts, old, bad) in enumerate(rows):
            ex, ez = foot(b)
            x, z = b["pos"]
            if sts == "move":
                o.append(R(X(old[0] - ex), Y(old[1] + ez), 2 * ex * s, 2 * ez * s,
                           fill="none", stroke="var(--dim)", sw=0.8, dash="3 3"))
                ax0, ay0 = X(old[0]), Y(old[1])
                ax1, ay1 = X(x), Y(z)
                o.append(LN(ax0, ay0, ax1, ay1, stroke="var(--shu)", sw=1.1, op=0.9))
                ang = math.atan2(ay1 - ay0, ax1 - ax0)
                o.append(PL([(ax1, ay1),
                             (ax1 - 7 * math.cos(ang - 0.42), ay1 - 7 * math.sin(ang - 0.42)),
                             (ax1 - 7 * math.cos(ang + 0.42), ay1 - 7 * math.sin(ang + 0.42))],
                            stroke="none", fill="var(--shu)", close=True))
            if bad is None:
                fl, so, dsh = "none", "var(--dim)", "3 3"
            else:
                fl = "var(--cut4)" if bad > 3 else ("var(--cut2)" if bad > 0.5 else "var(--nomove)")
                so, dsh = "var(--ink)", None
            o.append(R(X(x - ex), Y(z + ez), 2 * ex * s, 2 * ez * s,
                       fill=fl, stroke=so, sw=0.9, dash=dsh, op=0.92))
            tag = "?" if bad is None else (BADF % bad)
            big = (2 * ex * s >= 26 and 2 * ez * s >= 14)
            kk = kaku.get(b["name"])
            if kk and big:
                tag = "%s %s" % (kk, tag)      # ⛔ 小さい駒に郭名まで書くと隣と当たる
            # 小さい駒(土蔵・家臣長屋)は名札が隣と当たるので**3段**違いにする
            dy = 3 if big else (-6 + (kb % 3) * 12)
            o.append(T(X(x), Y(z) + dy, tag, cls="jo", anchor="middle",
                       fill="var(--shu)" if (bad is None or bad > 0.5) else "var(--take)"))
        for w in d["wells"]:
            und = w["name"] in set(opt.get("undecided", []))
            wp = sai_well_pos(opt, w)
            o.append(CIR(X(wp[0]), Y(wp[1]), 3.0, fill="var(--ike)",
                         stroke="var(--dim)" if und else "var(--hei)", sw=1.0))
        o.append("</g>")                       # クリップ終わり(以下は面の外の注記)
        o.append(R(ox, top, pw, ph, fill="none", stroke="var(--rule)", sw=0.8))
        # 案ごとの成績
        fy = top + ph + 16
        if mx is None:
            o.append(T(ox + 3, fy, "最大の埋没 … 復元してみるまで不明【?】", cls="sl", fill="var(--shu)"))
            o.append(T(ox + 3, fy + 15, "規則3 の合否 … 判定できない", cls="sl", fill="var(--shu)"))
        else:
            o.append(T(ox + 3, fy, ("最大の埋没 " + BADF + " m") % mx, cls="sl",
                       fill="var(--shu)" if mx > 0.5 else "var(--take)"))
            o.append(T(ox + 3, fy + 15, "規則3 合格 %d / %d 駒%s"
                       % (ok, nk, ("(ほか %d 駒は行き先未決)" % (nb - nk)) if nb > nk else ""),
                       cls="sl", fill="var(--take)" if ok == nk else "var(--shu)"))
        o.append(T(ox + 3, fy + 30, "動かす棟 %d ／ 行き先未決 %d ／ 台地面 %s"
                   % (sum(1 for r in rows if r[2] == "move"),
                      sum(1 for r in rows if r[2] == "und"),
                      "現況のまま" if opt["surface"] == "current"
                      else "%.2f m" % surf_plateau(opt)), cls="jo"))
        dl = surf_delta(geo, opt)
        o.append(T(ox + 3, fy + 43, "地盤が動くセル %s(%.1f %%)／ 最大 %+.2f / %+.2f m"
                   % ("{:,}".format(dl["n"]), 100.0 * dl["n"] / max(dl["tot"], 1),
                      dl["up"], dl["down"]), cls="jo"))
    # スケールバー(三面とも同じ縮尺なので1本で足りる)
    sb = 50.0
    o.append(LN(lm + 3, H - 30, lm + 3 + sb * s, H - 30, stroke="var(--ink)", sw=1.6))
    o.append(T(lm + 3 + sb * s + 8, H - 27, "%.0f m(三面とも同じ)" % sb, cls="jo"))
    TW(o, 14, H - 12, "駒の中の数字 = その案の面での埋没[m](? = 復元した崖の面に載るので行き先未決)／ "
                      "破線の枠 = 行き先未決の駒／ 灰の破線 = 崖の法尻・法肩(三案とも同じ線)／ "
                      "⛔ 棟・外周・表門は三案とも1つも動かない — 違いはすべて地盤の段彩に出ている。"
                      "枠に入りきらない西の谷と南の脚は ① と前の節の対比図で見る",
       cls="jo", maxw=W - 28, lh=12)
    o.append(ENDSVG)
    return "".join(o)


def sec_project(sec, p):
    """点を切り線へ落とす。返り値 (切り線上の位置 c, 線からの離れ off)。"""
    (px, pz), (dx, dz), L = sec_line(sec)
    qx, qz = p[0] - px, p[1] - pz
    return qx * dx + qz * dz, abs(qx * dz - qz * dx)


def sai_sec_svg(d, geo, dem, kan, W=940.0):
    """④ 断面の対比。**現況(2本)・A案・B案を同じ縮尺・同じ標高目盛で上下に並べる。**
    埋没は平面では読めない — 何メートル地中に入っているかは断面でしか分からない。
    ⛔ **現況は 1本では足りない** — z=839 は表門を、z=855 は最大の埋没(奥御殿)を切る
    (2026-08-31 検図 K-4 / K-5)。⛔ **B案は二段の郭なので東西にも南北にも串刺しにできず、
    石段廊下 K1 に沿った斜で切る**。"""
    S = sai(d)
    bands = []
    for sec in S["sections"]:
        opt = sai_opt(d, sec["opt"])
        # ⛔ **行き先未決の駒(土蔵三棟)も描く** — 「復元した崖の面に載る」ことを見せるための
        #    切り位置なので、外すと図の目的が消える。名札に「未決」と出す。
        bods = [(k, b, st) for k, b, st, _ in sai_bodies(d, geo, opt)]
        col = "var(--shu)" if opt["surface"] == "current" else "var(--take)"
        ttl = "%s の面" % sai_gian(opt)
        bands.append((ttl, sec, bods, col, opt))
    # ⚠ top は「大見出し + 帯ごとの見出し」、bot は「地盤の帯の名札 + 注記」ぶんを空ける。
    #   詰めると帯の名札と注記が重なる(2026-08-31 自己検図で実際に重なった)。
    lm, rm, top, gp, bot = 54.0, 26.0, 56.0, 52.0, 122.0
    SL = max(sec_line(b[1])[2] for b in bands)
    s = (W - lm - rm) / SL
    vs = s * VEX
    lo, hi = [], []
    prof = []
    for _t, sec, bods, _c, o_ in bands:
        f = sai_surf(o_)
        L = sec_line(sec)[2]
        cs = [i * sec["step"] for i in range(int(L / sec["step"]) + 1)]
        ys = [f(*sec_pt(sec, c)) for c in cs]
        prof.append((cs, ys))
        lo.append(min(ys))
        hi.append(max(ys))
        for kind, m, _st in bods:
            if sec_body_span(sec, m):
                y = seat_of(m, f, sink_of(d, m))
                lo.append(y)
                hi.append(y + m["h"])
    y0 = math.floor(min(lo) - 2)
    y1 = math.ceil(max(hi) + 5)
    bh = (y1 - y0) * vs
    H = top + bh * len(bands) + gp * (len(bands) - 1) + bot
    o = _sv(W, H, "%s 断面の対比(現況 / A案 / B案)" % kan)
    o.append(R(0, 0, W, H, fill="var(--paper)"))
    o.append(T(14, 18, "%s　④ 断面の対比 — 同じ切り位置を三案の面で切る(四段とも同じ縮尺・"
               "同じ標高目盛・垂直倍率 ×%.1f)" % (kan, VEX), cls="big"))
    for kbd, (title, sec, bods, tcol, opt) in enumerate(bands):
        oy = top + (bh + gp) * kbd
        cs, ys = prof[kbd]

        def PX(c):
            return lm + c * s

        def PY(y, oy=oy):
            return oy + bh - (y - y0) * vs
        for y in range(int(y0 // 5 * 5), y1 + 5, 5):
            if not (y0 <= y <= y1):
                continue
            o.append(LN(PX(0), PY(y), PX(sec_line(sec)[2]), PY(y), stroke="var(--rule)", sw=0.6))
            o.append(T(PX(0) - 6, PY(y) + 3, "%d" % y, cls="jo", anchor="end"))
        # ⛔ 見出しに「現況」を二度書かない(2026-08-31 検図 K-13)
        o.append(T(lm, oy - 12, "%s　%s" % (title, sec["name"]), cls="an2b", fill=tcol))
        o.append(PL([(PX(c), PY(y)) for c, y in zip(cs, ys)], stroke="var(--ink)", sw=1.7))
        # 台地と低地の帯(受け皿がどこかを地盤の上に出す)
        for lim, col, lab in ((S["lowland"], "var(--shu)", "低地(人工の平場)"),
                              (S["plateau"], "var(--take)", "台地")):
            seg = None
            for i, (c, y) in enumerate(zip(cs, ys)):
                inb = (y < lim) if lim == S["lowland"] else (y >= lim)
                inb = inb and pip(geo.P, *sec_pt(sec, c))
                if inb and seg is None:
                    seg = c
                if (not inb or i == len(cs) - 1) and seg is not None:
                    o.append(LN(PX(seg), PY(y0) + 10, PX(c), PY(y0) + 10,
                                stroke=col, sw=4.0, op=0.5, cap="butt"))
                    if c - seg > 24:
                        o.append(T((PX(seg) + PX(c)) / 2, PY(y0) + 24, lab, cls="jo",
                                   anchor="middle", fill=col))
                    seg = None
        # 石段廊下(その案が新設するもの)を**踏面/蹴上のギザギザで**描く(sashizu.md §3c)
        for kd in sai_kaidans(d, dem, opt) if opt else []:
            ca_, oa = sec_project(sec, kd["from"])
            cb_, ob = sec_project(sec, kd["to"])
            if max(oa, ob) > 3.0:
                continue                      # この切り線には載っていない
            ya, yb = dem(*kd["from"]), dem(*kd["to"])
            n = min(kd["n"], 40)
            pts = [(PX(ca_), PY(ya))]
            for i in range(n):
                t0, t1 = i / float(n), (i + 1) / float(n)
                pts.append((PX(ca_ + (cb_ - ca_) * t1), PY(ya + (yb - ya) * t0)))
                pts.append((PX(ca_ + (cb_ - ca_) * t1), PY(ya + (yb - ya) * t1)))
            o.append(PL(pts, stroke="var(--roka)", sw=1.6))
            # ⛔ 名札を段の上に重ねない(踏面のギザギザが読めなくなる)。段の下・進行方向の手前へ置く
            o.append(T(PX((ca_ + cb_) / 2) - 8, PY((ya + yb) / 2) + 16,
                       "%s %d段 %s" % (kd["name"], kd["n"], kd["form"]), cls="jo",
                       anchor="end", fill="var(--roka)"))
        fs = sai_surf(opt)
        for kb, (kind, m, mst) in enumerate(bods):
            sp = sec_body_span(sec, m)
            if sp is None:
                continue
            a, b = sp
            y = seat_of(m, fs, sink_of(d, m))
            bad = nat_range(m, fs)[1] - y
            col = "var(--shu)" if kind == "門" else "var(--dan2)"
            o.append(R(PX(a), PY(y + m["h"]), (b - a) * s, m["h"] * vs, fill=col,
                       stroke="var(--ink)", sw=1.0,
                       dash="3 3" if mst == "und" else None,
                       op=0.40 if kind == "門" else 0.9))
            sub = [(c, fs(*sec_pt(sec, c))) for c in cs if a <= c <= b]
            if sub and max(q[1] for q in sub) > y + 0.2:
                pts = [(PX(q[0]), PY(min(q[1], y + m["h"]))) for q in sub]
                pts += [(PX(sub[-1][0]), PY(y)), (PX(sub[0][0]), PY(y))]
                o.append(PL(pts, stroke="none", fill=_bur(), op=0.9, close=True))
            # 名札は3段違いにする。寄せたあとの面は棟が近接するので2段では重なる
            o.append(T(PX((a + b) / 2), PY(y + m["h"]) - 6 - (kb % 3) * 12,
                       ("%s 埋没 " + BADF + " m %s%s")
                       % (m["label"], bad, "✗" if bad > 0.5 else "○",
                          "・行き先未決" if mst == "und" else ""),
                       cls="jo", anchor="middle",
                       fill="var(--shu)" if bad > 0.5 else "var(--take)"))
    yn = H - bot + 34
    yn += TW(o, 14, yn, "実線 = その案の地盤／ 斜線 = 棟が地中に入る部分／ "
                        "破線の枠 = 行き先未決の駒(土蔵三棟)／ "
                        "帯 = 区画内の低地(朱・現況の 9.3m 平場の判定)と台地(緑)",
             cls="jo", maxw=W - 28, lh=14) * 14
    yn += TW(o, 14, yn,
             "⛔ **上の三段は同じ切り位置(z=839)を三案の面で切ったもの** — 棟は三案とも1棟も"
             "動かないので、段どうしの違いは**すべて地盤の違い**である。四段目だけは切り位置が違い、"
             "**A案・B案で唯一 規則3 を落とす土蔵三棟**を通す斜の線で切ってある。",
             cls="jo", maxw=W - 28, lh=14) * 14
    TW(o, 14, yn, "⚠ **表門(z 831.98〜846.02)は上の三段すべてに写る** — 三案とも動かないので、"
                  "面が変わったときに門の埋没がどう変わるかがそのまま読める。"
                  "⚠ **表門は区画線をまたぐ**ので、復元する案では**区画の中(復元面)と外(現況)の"
                  "両方を踏む** — その段差が門の埋没に出る(未解決 P-7 と同じ根)。",
       cls="jo", maxw=W - 28, lh=14)
    o.append(ENDSVG)
    return "".join(o)


def sai_case_table(d, geo, dem):
    """⑤ 案ごとに何がどれだけ変わるか。"""
    # ⛔ 長い文を列に押し込まない。列幅が潰れて縦一列に折り返す(2026-08-31 自己検図)。
    #   数値は上段の行に、文章は次の行へ colspan で流す。
    # ⛔ **長い文を列に押し込まない。**6列にすると右端の列が枠を越えて切れる
    #    (2026-08-31 のレンダで「作り直すもの」が読めなかった)。数値だけを列にし、
    #    崖・作り直すもの・地盤は colspan の行へ流す。
    hd = ["案(kosho.md の対応)", "台地面", "最大の埋没<br><span class='cert'>未決を除く</span>",
          "規則3 合格<br><span class='cert'>未決を除く</span>",
          "<b>未決の駒が現位置のままなら</b><br>"
          "<span class='cert'>最大の埋没 ／ 規則3 合格(同じ 駒数)</span>"]
    rows = []
    for opt in sai(d)["options"]:
        _, mx, ok, nk, nb = sai_metrics(d, geo, dem, opt)
        mxa, oka, nka = sai_metrics_all(d, geo, opt)
        mxs = "—(不明)" if mx is None else (BADF + " m") % mx
        oks = "判定不能" if mx is None else "%d / %d 駒" % (ok, nk)
        nu = sum(1 for r in sai_bodies(d, geo, opt) if r[2] == "und")
        cl = surf_cliff(opt)
        rows.append("<tr><td class='note'><b>%s</b> %s%s</td><td>%s</td><td%s>%s</td>"
                    "<td%s>%s</td><td%s><b>%s</b> ／ <b>%d / %d 駒</b></td></tr>"
                    % (sai_gian(opt), html.escape(opt["label"]),
                       ("　<span class='cert'>【%s】</span>" % opt["tag"]) if opt.get("tag") else "",
                       "現況のまま" if opt["surface"] == "current"
                       else "<b>%.2f m</b>" % surf_plateau(opt),
                       " style='color:var(--shu)'" if (mx is None or mx > 0.5) else "", mxs,
                       " style='color:var(--shu)'" if (mx is None or ok < nk) else "", oks,
                       " style='color:var(--shu)'" if (mxa > 0.5 or oka < nka) else "",
                       (BADF + " m") % mxa, oka, nka))
        rows.append("<tr><td class='note' colspan='5'><b>崖</b> %s　／　"
                    "<b>作り直すもの</b> %s</td></tr>" % (cl, inline(opt["redo"])))
        dl = surf_delta(geo, opt)
        rows.append("<tr><td class='note' colspan='5'><b>地盤</b> %s"
                    "<br><b>動くセル</b> %s / %s(%.1f %%)　"
                    "<b>最大</b> 上げ %+.2f m ／ 下げ %+.2f m　"
                    "<b>土量</b> 盛 %s m³ ／ 切 %s m³"
                    "<br><b>区画線の段(全周)</b> %s　／　<b>他邸への波及</b> %s"
                    "<br><b>確度</b> %s</td></tr>"
                    % (inline(opt["ground"]),
                       "{:,}".format(dl["n"]), "{:,}".format(dl["tot"]),
                       100.0 * dl["n"] / max(dl["tot"], 1), dl["up"], dl["down"],
                       "{:,.0f}".format(dl["volUp"]), "{:,.0f}".format(dl["volDown"]),
                       surf_seam(geo, opt), inline(opt["spill"]), inline(opt["acc"])))
        rows.append("<tr><td class='note' colspan='5'>%s</td></tr>"
                    % seam_by_edge_html(d, geo, opt))
        if nu:
            und = [b for _, b, st, _ in sai_bodies(d, geo, opt) if st == "und"]
            rows.append("<tr><td class='note' colspan='5'>"
                        "<span class='cert'>⚠ <b>行き先未決 %d 駒</b>(%s)は"
                        "「規則3 合格」の分母から外してある — "
                        "復元した崖の面に載るので、行き先が決まるまで判定できない。"
                        "<b>制約</b>: 外形の四隅がすべて<b>法肩の折れ線より台地側</b>に入ること"
                        "(⚠ 崖は折れ線なので<b>一本の X では書けない</b>)。"
                        "⛔ 行き先そのものは配置の判断なので指図方は決めない。"
                        "</span></td></tr>"
                        % (nu, "・".join(b["label"] for b in und)))
    return ("<div class='tw'><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>"
            % ("".join("<th>%s</th>" % x for x in hd), "".join(rows)))


def sai_kaidan_table(d, dem):
    """案が新設する石段廊下。⛔ **落差・段数・必要水平は地盤から算出する**(規則4)。"""
    C = d["const"]
    rows = []
    for opt in sai(d)["options"]:
        for k in sai_kaidans(d, dem, opt):
            rows.append("<tr><td>%s</td><td>%s</td><td>%.2f m</td><td><b>%d 段</b></td>"
                        "<td>%.2f m</td><td>%.2f m</td><td%s>%.2f m</td>"
                        "<td%s><b>%s</b></td></tr>"
                        % (sai_gian(opt), html.escape("%s %s" % (k["name"], k["label"])),
                           k["rise"], k["n"], k["need"], k["half"],
                           "" if k["L"] >= k["need"] else " style='color:var(--shu)'", k["L"],
                           "" if k["ok"] else " style='color:var(--shu)'", k["form"]))
            # ⛔ 長い文と座標を列に押し込まない(列幅が潰れて行が縦に伸びる)
            rows.append("<tr><td class='note' colspan='8'><b>両端</b> "
                        "(%.2f, %.2f) → (%.2f, %.2f)　／　<b>両端の地盤</b> %.2f → %.2f m"
                        "<br>%s</td></tr>"
                        % (k["from"][0], k["from"][1], k["to"][0], k["to"][1],
                           k["ya"], k["yb"], inline(k.get("_", ""))))
    if not rows:
        return ""
    return ("<div class='tw'><table><thead><tr><th>案</th><th>石段廊下</th>"
            "<th>落差</th><th>段数</th><th>直線に要る水平</th>"
            "<th>折返しなら</th><th>現況で取れる水平</th><th>形</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>⛔ <b>段数は落差 ÷ 蹴上 %.2f m の切り上げ</b>、"
            "<b>直線に要る水平は 段数 × 踏面 %.2f m</b>、"
            "<b>折返しにすると その半分 + 踊り場1枚(踏面ぶん)</b>"
            "(sashizu.md §1f)。「現況で取れる水平」は両端の平面距離で、"
            "<b>これが必要水平を下回ると石段が入らない</b>。"
            "⚠ 石段廊下は<b>在庫に無い新造部材</b> — 採用が決まったら edo-zaiko で照会し、"
            "無ければ edo-buzai へ回す。</p>" % (C["keri"], C["fumi"]))


def sai_overlap_table(d, geo, dem):
    """案ごとの外形の重なり。⛔ **面積だけでは「呑まれている」ことが読めない** —
    外形に対する割合まで出す(2026-08-31 検図 K-3)。"""
    rows = []
    for opt in sai(d)["options"]:
        ov = sai_overlaps(d, geo, opt)
        if not ov:
            rows.append("<tr><td>%s</td><td class='note' colspan='5'>"
                        "<span class='cert'>重なり無し</span></td></tr>" % sai_gian(opt))
            continue
        for a, b, ox, oz, ar, pa, pb in ov:
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%.2f × %.2f m</td>"
                        "<td>%.0f m²</td><td%s>%.0f %% ／ %.0f %%</td></tr>"
                        % (sai_gian(opt), html.escape(a), html.escape(b), ox, oz, ar,
                           " style='color:var(--shu);font-weight:700'"
                           if max(pa, pb) >= 99.5 else "", pa, pb))
    return ("<div class='tw'><table><thead><tr><th>案</th><th>棟 A</th><th>棟 B</th>"
            "<th>重なり</th><th>面積</th><th>A の外形 ／ B の外形 に対する割合</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def sai_body_table(d, geo, dem):
    """駒ごとに、案ごとの面の上でどうなるか。⛔ 埋没も起伏も面から毎回算出する。
    ⭐ **「埋没」だけでは足りない** — 台地を水平面で復元しているので、
    **その駒の下の面の起伏**を併記しないと『規則3 に通った』が恒真かどうか読めない。"""
    keys = [q["key"] for q in sai(d)["options"]]
    hd = ["駒", "位置(三案とも同じ)"]
    for k in keys:
        hd += ["%s案 埋没" % k, "%s案 下の起伏" % k]
    hd += ["扱い"]
    rows = []
    base = sai_bodies(d, geo, sai_opt(d, keys[0]))
    for idx, (kind, _b0, _st0, old) in enumerate(base):
        m0 = seat_bodies(d, geo)[idx][1]
        cells = ""
        note = ""
        for k in keys:
            opt = sai_opt(d, k)
            _k2, b, st, _o = sai_bodies(d, geo, opt)[idx]
            bad = sai_bad(d, dem, opt, b, st)
            # ⛔ **「扱い」は復元する案での扱いを出す。** C案(現況)では土蔵も `stay` になるので、
            #    最後の案で上書きすると「動かさない」に見えてしまう(2026-08-31 レンダで実際に出た)。
            if st == "fix":
                note = "三案とも動かない(門は開口の芯に固定)"
            elif st == "und":
                note = SAI_ST["und"]
            elif not note:
                note = SAI_ST.get(st, st)
            cells += ("<td%s>%s</td><td class='cert'>%.2f m</td>"
                      % (" style='color:var(--shu)'" if (bad is None or bad > 0.5) else "",
                         "?" if bad is None else (BADF + " m %s") % (bad, "✗" if bad > 0.5 else "○"),
                         sai_relief(opt, b)))
        rows.append("<tr><td>%s</td><td>(%.2f, %.2f)</td>%s<td class='note'>%s</td></tr>"
                    % (html.escape(m0["label"]), old[0], old[1], cells, note))
    return ("<div class='tw'><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>"
            % ("".join("<th>%s</th>" % x for x in hd), "".join(rows)))


def sai_prose(d, dem):
    """6点セット(どこ / 背景2文 / 選択肢 A・B・C / 推奨と理由 / 影響)。
    ⛔ 数値は書かない — 上の図と表が地盤から算出したものを持つ(CLAUDE.md 規則4)。"""
    S = sai(d)
    h = ['<div class="box">']
    h.append("<p><b>【どこ】</b>%s</p>" % inline(S["where"]))
    h.append("<p style='margin-top:10px'><b>【背景】</b>%s</p>" % inline(" ".join(S["haikei"])))
    h.append("</div>")
    h.append("<h3>【選択肢】</h3>")
    for opt in S["options"]:
        h.append("<h4>%s　%s%s</h4>"
                 % (sai_gian(opt), html.escape(opt["label"]),
                    ("　【%s】" % opt["tag"]) if opt.get("tag") else ""))
        h.append("<p class='cap'>%s<br>%s</p>" % (inline(opt["desc"]), inline(opt["risk"])))
    rec = sai_opt(d, S["recommend"])
    h.append("<div class='box' style='margin-top:18px'>")
    h.append("<p><b>【推奨】%s — %s。</b>%s</p>"
             % (sai_gian(rec), html.escape(rec["label"]), inline(S["why"])))
    h.append("<p style='margin-top:10px'><b>【影響】</b>%s</p>" % inline(S["eikyo"]))
    h.append("<p style='margin-top:10px'>%s</p>" % inline(S["excluded"]))
    h.append("</div>")
    return "".join(h)


# ---------------------------------------------------------------- 機械検査
def check_rects(d, geo):
    """機械検査に載せる**すべての矩形**。棟・付属屋だけでは足りない —
    **番所2棟と盲長屋の鎖の駒**も置かれた実体なので総当たりの集合に入れる(2026-08-30 検図 K-6)。
    返すのは (名, x0, z0, x1, z1, 群, 順, 長屋か)。群/順は「同一鎖の隣り合う駒」の除外に使う。"""
    C = d["const"]
    out = []
    for kind, m in all_bodies(d):
        out.append((m["label"], m["pos"][0] - m["w"] / 2, m["pos"][1] - m["d"] / 2,
                    m["pos"][0] + m["w"] / 2, m["pos"][1] + m["d"] / 2,
                    m["name"], 0, "Knagaya" in m.get("asset", "")))
    gp = d["gate"]["plan"]
    gx, gz = geo.gate
    out.append(("表門", gx - gp["monD"] / 2, gz - gp["monW"] / 2,
                gx + gp["monD"] / 2, gz + gp["monW"] / 2, "Kmon", 0, False))
    # 番所(門と同じく yaw 90 — 部材の X=w が塀の走り方向へ回り、Z=d が通りの向きになる)
    bs = gp["bansho"]
    ow = geo.outward(d["gate"]["edge"])
    uh = (ow[1], -ow[0])
    for sgn in (1, -1):
        bx = gx + uh[0] * sgn * bs["offset"] + ow[0] * bs["extrude"]
        bz = gz + uh[1] * sgn * bs["offset"] + ow[1] * bs["extrude"]
        hx = abs(uh[0]) * bs["w"] / 2 + abs(ow[0]) * bs["d"] / 2
        hz = abs(uh[1]) * bs["w"] / 2 + abs(ow[1]) * bs["d"] / 2
        out.append(("番所(%s)" % ("北" if sgn > 0 else "南"), bx - hx, bz - hz, bx + hx, bz + hz,
                    "Bansho", 0, False))
    # 盲長屋の鎖の駒(⚠ 当邸の長屋の辺は世界軸に平行なので、四隅の bbox が外形そのもの)
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        a, b = geo.run_span(r)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        dr = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        ow2 = geo.outward(r["edge"])
        nin = (-ow2[0], -ow2[1])                 # 敷地の内向き = 長屋の奥行の向き
        n, tot, half = nagaya_chain(L, C["nagayaModC"], C["nagayaModLR"])
        ws = ([C["nagayaModC"]] if n == 1 else
              [C["nagayaModLR"]] + [C["nagayaModC"]] * (n - 2) + [C["nagayaModLR"]])
        t = half
        for k, w in enumerate(ws):
            cor = [(a[0] + dr[0] * tt + nin[0] * dd, a[1] + dr[1] * tt + nin[1] * dd)
                   for tt in (t, t + w) for dd in (0.0, C["nagayaD"])]
            out.append(("%s 駒%d/%d" % (r["name"], k + 1, n),
                        min(q[0] for q in cor), min(q[1] for q in cor),
                        max(q[0] for q in cor), max(q[1] for q in cor), r["name"], k, True))
            t += w
    return out


def overlap_eps(A, B):
    ca = ((A[1] + A[3]) / 2.0, (A[2] + A[4]) / 2.0)
    cb = ((B[1] + B[3]) / 2.0, (B[2] + B[4]) / 2.0)
    return math.hypot(cb[0] - ca[0], cb[1] - ca[1])


def overlap_exempt(d, A, B):
    """外形の重なりの**除外規約**。⛔ 規約は図にも書く(checks_table)。
       ① 同一の鎖(run)の隣り合う駒 — 突き付けで積むので軒が重なるのが正しい姿。
       ② 長屋どうしで芯間が壁の実寸(const.nagayaModLR)と ±0.20m で一致する組 —
          軒の重なりは正しい納まりで、壁の面のズレは取り合い表(J3)が別に見る。"""
    if A[5] == B[5] and abs(A[6] - B[6]) == 1:
        return "同一の鎖の隣り合う駒(規約①)"
    if A[7] and B[7] and abs(overlap_eps(A, B) - d["const"]["nagayaModLR"]) <= 0.20:
        return "芯間 %.2f m が壁の実寸 %.2f m と一致する長屋(規約②)" \
            % (overlap_eps(A, B), d["const"]["nagayaModLR"])
    return None


def checks(d, geo, dem):
    """⛔ **図を出す前に機械で検める**(sashizu.md §4「矩形の重なりは機械検査してから出す」)。
    目視では必ず見落とす。落ちた項目は `pending` に立っているものと突き合わせること。"""
    bad = []
    B = check_rects(d, geo)
    skipped = []
    for i in range(len(B)):
        for j in range(i + 1, len(B)):
            iu = min(B[i][3], B[j][3]) - max(B[i][1], B[j][1])
            iv = min(B[i][4], B[j][4]) - max(B[i][2], B[j][2])
            if not (iu > 0.05 and iv > 0.05):
                continue
            why = overlap_exempt(d, B[i], B[j])
            if why:
                skipped.append("%s × %s (%.2f × %.2f m) — %s"
                               % (B[i][0], B[j][0], iu, iv, why))
                continue
            bad.append("外形の重なり: %s × %s (%.2f × %.2f m)" % (B[i][0], B[j][0], iu, iv))
    # 区画からの出入り(⚠ 面が区画線に**載る**駒があるので、四隅を 0.05m 内へ寄せて判定する)
    for q in B:
        nm, a0, b0, a1, b1 = q[0], q[1], q[2], q[3], q[4]
        e = 0.05
        out = [(x, z) for x in (a0 + e, a1 - e) for z in (b0 + e, b1 - e)
               if not pip(geo.P, x, z)]
        if out:
            bad.append("区画の外へ出る: %s(四隅のうち %d 点)" % (nm, len(out)))
    for w in d["wells"]:
        if not pip(geo.P, w["pos"][0], w["pos"][1]):
            bad.append("区画の外: 井戸 %s" % w["label"])
    # 棟の埋没(規則3)。⭐ **表門も CenterSeat で地形へ載るので算入する**(2026-08-30 検図 K-11)
    for _, m in seat_bodies(d, geo):
        y = seat_of(m, dem, sink_of(d, m))
        bur = nat_range(m, dem)[1] - y
        if bur > 0.5:
            bad.append("規則3: %s が %.2f m 埋まる(合格は ≦0.5 m)" % (m["label"], bur))
    # 築地塀・長屋の天端(駒ごとに地形へ載るので継ぎ目に段差が出る)
    for r in d["runs"]:
        st = run_stats(d, geo, dem, r)
        if st["cut"]:
            bad.append("塀が切れる: %s の継ぎ目 %d 箇所で段差が高さ %.2f m を超える(最大 %.2f m)"
                       % (r["name"], len(st["cut"]), st["h"], st["jmax"]))
    # 盲長屋の鎖の端数(⚠ **符号の両方を見る** — はみ出しも隙間も規約外)
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        a, b = geo.run_span(r)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n, tot, half = nagaya_chain(L, d["const"]["nagayaModC"], d["const"]["nagayaModLR"])
        if half < -0.05:
            bad.append("鎖のはみ出し: %s が両端で %.2f m ずつ辺の外へ出る" % (r["name"], -half))
        elif half > 0.001:
            bad.append("鎖の隙間: %s の両端に %.2f m ずつ隙間が開く(棟 %d・実延長 %.2f m / 辺 %.2f m)"
                       % (r["name"], half, n, tot, L))
    # 取り合いの規約(0.00 / +0.05 / −0.00)。⛔ 隙間の量は毎回測る(json に持たない)
    for j in d["joints"]:
        gv = joint_gap(d, geo, j)
        if gv is None:
            continue
        if gv > 0.001 or gv < -0.05:
            bad.append("取り合い %s: %+.2f m(規約は 0.00 / +0.05 / −0.00)" % (j["id"], gv))
    # 囲いの無い辺
    for e in d["edges"]:
        if e["run"] is None:
            bad.append("囲いの無い辺: 辺%d %.1f m(%s が受け持つ前提)"
                       % (e["i"], geo.edge(e["i"])[2], e["owner"]))
    return bad, skipped, len(B)


def checks_table(bad, skipped, nrect):
    h = []
    if not bad:
        h.append("<p class='cap'>機械検査 0 件。</p>")
    else:
        h.append("<div class='tw'><table><thead><tr><th>#</th><th>落ちた項目</th></tr></thead><tbody>"
                 + "".join("<tr><td>%d</td><td class='note'>%s</td></tr>" % (i + 1, html.escape(b))
                           for i, b in enumerate(bad))
                 + "</tbody></table></div>")
    h.append("<h3>外形の重なりの除外規約</h3>"
             "<p class='cap'>総当たりは <b>%d 矩形 %d 組</b>(棟・付属屋・表門・番所2・"
             "<b>盲長屋の鎖の駒</b>)。次の二つは<b>正しい納まりなので除外する</b> — "
             "除外しないと、正しく連なっている長屋がすべて「重なり」で落ちる。</p>"
             "<ol class='cap'><li><b>同一の鎖(run)の隣り合う駒</b> — 突き付けで積むので"
             "軒が重なるのが正しい姿。</li>"
             "<li><b>長屋どうしで芯間が壁の実寸(<code>const.nagayaModLR</code>)と "
             "±0.20 m で一致する組</b> — 軒の重なりは正しい納まりで、"
             "壁の面のズレは取り合い表(J3)が別に見る。</li></ol>"
             % (nrect, nrect * (nrect - 1) // 2))
    if skipped:
        h.append("<p class='cap'>除外した組(%d):<br>%s</p>"
                 % (len(skipped), "<br>".join(html.escape(q) for q in skipped)))
    return "".join(h)


# ---------------------------------------------------------------- 表
PCS = {}                 # parcels.json の全区画(main が入れる)。辺の区間の照合に使う


def edge_faces(d, geo, e):
    """辺が**何に面しているか**を、区間つきで書く。⛔ 「(街路)」で済ませない —
    区間だけ接する隣(町屋)があれば、**どこからどこまでか**を幾何から測って出す(検図 K6)。"""
    out = [html.escape(e["faces"])]
    for nb in d["neighbors"]:
        if e["i"] not in nb["edges"] or not nb.get("partial"):
            continue
        Q = PCS.get(nb["id"])
        if not Q:
            continue
        tl, s0, s1 = edge_touch(geo, e["i"], [tuple(q) for q in Q])
        L = geo.edge(e["i"])[2]
        out.append("<span class='cert'>⚠ <b>%s</b> と s %.0f〜%.0f m で接する"
                   "(<b>%.0f m ／ 辺の %.0f %%</b>)</span>"
                   % (html.escape(nb["label"]), s0, s1, tl, 100.0 * tl / L))
    return "<br>".join(out)


def edges_table(d, geo):
    rows = []
    for e in d["edges"]:
        a, b, L, dd = geo.edge(e["i"])
        run = next((r for r in d["runs"] if r.get("edge") == e["i"]), None)
        if e["i"] == d["gate"]["edge"]:
            gl, gr = geo.wall_ends()
            det = "築地塀 %.2f m + 表門 %.2f m + 築地塀 %.2f m" % (
                math.hypot(gl[0] - a[0], gl[1] - a[1]), 2 * geo.gh,
                math.hypot(b[0] - gr[0], b[1] - gr[1]))
        elif e["run"] is None:
            det = "—"
        elif e["kind"] == "盲長屋":
            n, tot, half = nagaya_chain(L, d["const"]["nagayaModC"], d["const"]["nagayaModLR"])
            det = "%d棟 実延長 %.3f m(端数 %+.3f m / 片側 %+.3f m)" % (n, tot, L - tot, half)
        else:
            n, p = dobei_pieces(L, d["const"]["dobeiPitchNom"])
            det = "%d駒 × ピッチ %.4f m" % (n, p)
        rows.append("<tr><td>辺%d</td><td>%s</td><td>%.2f m</td><td>%s</td><td>%s</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (e["i"], e["label"], L, e["kind"], det, edge_faces(d, geo, e),
                       inline(e.get("_", "")) + " " + '<span class="cert">【%s】</span>' % inline(e["acc"])))
    return ("<div class='tw'><table><thead><tr><th>辺</th><th>名</th><th>長さ</th><th>種別</th>"
            "<th>割付け</th><th class='note'>面する先</th><th class='note'>備考</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def munes_table(d, dem, geo):
    ken = d["const"]["ken"]
    rows = []
    for kind, m in seat_bodies(d, geo):
        y = seat_of(m, dem, sink_of(d, m))
        nlo, nhi = nat_range(m, dem)
        bad = nhi - y
        u = (m["pos"][0] - d["grid"]["shukaku"]["x0"]) / ken
        v = (m["pos"][1] - d["grid"]["shukaku"]["z0"]) / ken
        # ⛔ **柱割りに乗っているか**を数で出す(2026-09-01 検図 K10)。
        #    江戸間 1間 の格子から、いちばん近い割り位置までの外れ(0 = 乗っている)。
        du = abs(u - round(u))
        dv = abs(v - round(v))
        off = max(du, dv)
        rows.append("<tr><td>%s</td><td>%s</td><td>(%.1f, %.1f)</td><td>(%+.2f, %+.2f)</td>"
                    "<td%s>%.2f 間</td>"
                    "<td>%.2f × %.2f m</td><td>%.0f m²</td><td>%.1f m</td>"
                    "<td%s>%.2f m</td><td class='note'><code>%s</code></td>"
                    "<td class='note'>%s</td></tr>"
                    % (kind, m["label"], m["pos"][0], m["pos"][1], u, v,
                       ' style="color:var(--shu)"' if off > 0.05 else "", off,
                       m["w"], m["d"], m["w"] * m["d"], y,
                       ' style="color:var(--shu);font-weight:700"' if bad > 0.5 else "", bad,
                       m["asset"], '<span class="cert">【%s】</span>' % inline(m["acc"])))
    non = sum(1 for _k, m in seat_bodies(d, geo)
              if max(abs((m["pos"][0] - d["grid"]["shukaku"]["x0"]) / ken
                         - round((m["pos"][0] - d["grid"]["shukaku"]["x0"]) / ken)),
                     abs((m["pos"][1] - d["grid"]["shukaku"]["z0"]) / ken
                         - round((m["pos"][1] - d["grid"]["shukaku"]["z0"]) / ken))) > 0.05)
    return ("<div class='tw'><table><thead><tr><th>別</th><th>棟</th><th>中心(x, z)</th>"
            "<th>(u, v)間</th><th>柱割りからの外れ</th><th>外形</th><th>建築面積</th>"
            "<th>座</th><th>埋没</th>"
            "<th class='note'>部材</th><th class='note'>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>⛔ <b>柱割りからの外れ</b>は、棟の中心が江戸間 1 間"
            "(<b>%.3f m</b>)の格子からどれだけ外れているかで、<b>0 なら柱割りに乗っている</b>。"
            "<b>%d / %d 駒が乗っていない</b>(2026-09-01 検図 K10・未解決 P-9)。"
            "⚠ 原因は<b>棟の位置を丸い世界座標で置いた</b>ことと、"
            "<b>在庫部材の寸法が間の倍数でない</b>ことの両方にある — "
            "⛔ 位置だけ格子へ寄せても部材の寸法は乗らないので、"
            "<b>柱割りに乗せるには棟そのものを起こし直すことになる</b>"
            "(<code>edo-buzai</code> の領分)。</p>" % (ken, non, len(seat_bodies(d, geo))))


def joint_gap(d, geo, j):
    """取り合いの現況の隙間[m]。**正=隙間 / 負=めり込み**。
    ⛔ **json に数値を持たせない**(規則4)— 区画を引き直すと辺の長さが変わり、
    手で持った値は黙って腐る(2026-09-01 に J4/J5 は符号ごと反転した)。"""
    C = d["const"]
    k = j.get("calc")
    if k == "gatePad":
        return C["gatePad"]
    if k == "nagayaEnd":
        r = next(q for q in d["runs"] if q["kind"] == "Nagaya")
        a, b = geo.run_span(r)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return nagaya_chain(L, C["nagayaModC"], C["nagayaModLR"])[2]
    if k == "kashinWall":
        ps = [s["pos"][0] for s in d["service"] if s["name"].startswith("Kashin")]
        return abs(ps[1] - ps[0]) - C["nagayaModLR"] if len(ps) == 2 else None
    if k == "banshoSpill":
        bs = d["gate"]["plan"]["bansho"]
        return -(bs["extrude"] + bs["d"] / 2.0)
    if k == "dobeiSeam":
        g = []
        for r in d["runs"]:
            if r["kind"] != "Dobei":
                continue
            a, b = geo.run_span(r)
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            _, p = dobei_pieces(L, C["dobeiPitchNom"])
            g.append(p * (1.0 - C["dobeiModXReal"] / C["dobeiModX"]))
        return max(g) if g else None
    return None


def joints_table(d, geo):
    rows = []
    JU = {"○": "適合", "△": "許容外(軽)", "×": "不適合", "?": "未確認"}
    for j in d["joints"]:
        gv = joint_gap(d, geo, j)
        g = "—" if gv is None else ("%+.2f m" % gv)
        rows.append("<tr><td>%s</td><td>%s<br><span class='cert'>%s</span></td>"
                    "<td>%s<br><span class='cert'>%s</span></td><td>%s</td><td>%s</td>"
                    "<td>%s</td><td%s>%s %s</td></tr>"
                    % (j["id"], html.escape(j["a"]), html.escape(j["aFace"]),
                       html.escape(j["b"]), html.escape(j["bFace"]), j["kind"], g,
                       html.escape(j["moves"]),
                       ' style="color:var(--shu);font-weight:700"' if j["judge"] in ("×", "△") else "",
                       j["judge"], JU.get(j["judge"], "")))
        # ⛔ 長い備考を列に押し込むと表が枠を越えて横スクロールになる(2026-08-31 の機械検査)。
        #    次の行へ colspan で流す。
        if j.get("_"):
            rows.append("<tr><td class='note' colspan='7'>%s</td></tr>" % inline(j["_"]))
    return ("<div class='tw'><table><thead><tr><th>#</th><th>A / 面</th><th>B / 面</th>"
            "<th>納め</th><th>現況</th><th>動く側</th><th>判定</th>"
            "</tr></thead><tbody>" + "".join(rows)
            + "</tbody></table></div>"
            "<p class='cap'>規約は <b>0.00 m(+0.05 / −0.00)</b> — <b>隙間は不可、めり込みは 0.05 m まで</b>"
            "(memory <code>gate-wall-closure-rule</code>)。負の値はめり込み。"
            "⛔ <b>中心・芯・ピボットで合わせない</b>(CLAUDE.md 規則5)。"
            "実装では置いたあとに<b>実メッシュから面を測って寄せる</b>。</p>")


def kenpei(d, geo, area):
    ken = d["const"]["ken"]
    gm = sum(m["w"] * m["d"] for m in d["munes"])
    kura = sum(s["w"] * s["d"] for s in d["service"] if s["name"].startswith("Kura"))
    kn = sum(s["w"] * s["d"] for s in d["service"] if s["name"].startswith("Kashin"))
    nag = 0.0
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        a, b = geo.run_span(r)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n, tot, _ = nagaya_chain(L, d["const"]["nagayaModC"], d["const"]["nagayaModLR"])
        nag += tot * d["const"]["nagayaD"]
    gp = d["gate"]["plan"]
    mon = gp["monW"] * gp["monD"]
    ban = gp["bansho"]["count"] * gp["bansho"]["w"] * gp["bansho"]["d"]
    rows = [("御殿の棟(表・奥・役所・台所)", gm), ("土蔵 3棟", kura), ("家臣長屋 2棟", kn),
            ("外周の盲長屋(辺%d)" % next(r["edge"] for r in d["runs"] if r["kind"] == "Nagaya"), nag), ("表門(屋根の水平投影)", mon), ("番所 2棟", ban)]
    tot = sum(r[1] for r in rows)
    body = "".join("<tr><td>%s</td><td>%.0f</td><td>%.0f</td></tr>" % (n, v, v / TSUBO)
                   for n, v in rows)
    return ('<div class="tw"><table><thead><tr><th></th><th>m²</th><th>坪</th></tr></thead><tbody>'
            + body
            + "<tr><td><b>計</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
              "<tr><td><b>敷地(分母)</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
              '<tr><td><b>建蔽率</b></td><td colspan="2"><b>%.1f %%</b></td></tr>'
              "</tbody></table></div>" % (tot, tot / TSUBO, area, area / TSUBO, 100.0 * tot / area)), \
           100.0 * tot / area


def bom_counts(d, geo):
    """部材表の**員数を毎回算出する**。⛔ **手書きの員数を持たない**(規則4)。
    ⚠ 2026-09-01 の検図 K2: 区画の引き直しで辺6 が長くなったのに、
    盲長屋(中)の員数が手書きの 7 のまま腐っていた(其六 の展開は 9 と数えていた)。"""
    C = d["const"]
    mid = end = 0
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        a, b = geo.run_span(r)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n, _, _ = nagaya_chain(L, C["nagayaModC"], C["nagayaModLR"])
        mid += max(0, n - 2)
        end += 1 if n >= 2 else 0
    dob = 0
    for r in d["runs"]:
        if r["kind"] == "Nagaya":
            continue
        a, b = geo.run_span(r)
        dob += dobei_pieces(math.hypot(b[0] - a[0], b[1] - a[1]),
                            C["dobeiPitchNom"])[0]
    kashin = sum(1 for s in d["service"] if "家臣長屋" in s.get("label", ""))
    return {"dobei_pieces": dob, "nagaya_mid": mid, "nagaya_end": end,
            "kashin_nagaya": kashin}


def bom_table(d, geo):
    cnt = bom_counts(d, geo)
    rows = []
    for b in d["bom"]:
        # ⚠ 定数もパスも `class='note'` + `word-break:break-all`。
        #   パスは空白を含まない長い1語なので、折り返せないと表が枠を越えて
        #   右の「実寸」列が切れていた(2026-08-31 に是正)。
        rows.append("<tr><td>%s</td><td class='note' style='word-break:break-all'><code>%s</code></td>"
                    "<td class='note' style='word-break:break-all'><code>%s</code></td>"
                    "<td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (b["part"], b["asset"], html.escape(b["path"]), b["size"],
                       b["scale"],
                       ("<b>%d</b><br><span class='cert'>算出</span>" % cnt[b["nkey"]])
                       if b.get("nkey") in cnt
                       else ("—" if b["n"] is None else b["n"]), inline(b["acc"])))
    return ("<div class='tw'><table><thead><tr><th>部材</th><th class='note'>定数</th>"
            "<th class='note'>パス</th>"
            "<th>実寸(scale=1)</th><th>scale</th><th>員数</th><th class='note'>解決</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>⛔ <b>「算出」の員数は json に持たない</b> — "
            "区画の幾何と <code>const</code> から毎回数える(規則4)。"
            "⚠ 2026-09-01 の検図 K2: 区画の引き直しで辺が長くなったのに、"
            "<b>手書きの員数だけが古い区画のまま腐っていた</b>"
            "(同じ指図の外周の展開とは数が合っていなかった)。</p>")


def stages_table(d):
    rows = ["<tr><td>%d</td><td>%s</td><td class='note'>%s</td><td>%s</td><td class='note'>%s</td></tr>"
            % (s["n"], s["name"], inline(s["work"]), "冪等" if s["idempotent"] else "⛔ 非冪等",
               inline(s.get("_", ""))) for s in d["stages"]]
    return ("<div class='tw'><table><thead><tr><th>#</th><th>Stage</th><th class='note'>作業</th>"
            "<th>冪等性</th><th class='note'>備考</th></tr></thead><tbody>" + "".join(rows)
            + "</tbody></table></div>")


def neighbors_table(d, geo):
    rows = []
    for n in d["neighbors"]:
        span = ""
        if n.get("partial") and n["id"] in PCS:
            for e in n["edges"]:
                tl, s0, s1 = edge_touch(geo, e, [tuple(q) for q in PCS[n["id"]]])
                span += ("<br><span class='cert'>辺%d の s %.0f〜%.0f m ／ "
                         "<b>%.0f m</b>(辺の %.0f %%)</span>"
                         % (e, s0, s1, tl, 100.0 * tl / geo.edge(e)[2]))
        # ⛔ **確度と注記は「行の下の1行」に置く。列にしない。**
        #    列にすると、いちばん長い注記が表の min-content を押し広げ、
        #    ⛔ **確度の列が丸ごと画面の外へ出る**(2026-09-01 に実測。
        #    `th,td` は既定 `white-space:nowrap` なので `table-layout:fixed` でも直らない)。
        # ⚠ 「隣」「共有」も `note`(= `white-space:normal`)にする — 既定の `nowrap` だと
        #    長い欄が幅を独占し、⛔ **「囲いの受け持ち」が1文字幅まで潰れて縦読みになる**。
        rows.append("<tr><td><code>%s</code></td><td class='note'>%s</td><td>%s</td>"
                    "<td class='note'>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (n["id"], inline(n["label"]),
                       "・".join("辺%d%s" % (e, "(区間)" if n.get("partial") else "")
                                 for e in n["edges"]),
                       inline(n["share"]),
                       inline(n["wall"])
                       + ("" if n.get("_") else
                          ' <span class="cert">【確度 %s】</span>' % inline(n["acc"]))))
        # ⚠ 注記の無い行に空の注記行を足さない(街路の3行が1行ずつ無駄に伸びる)。
        if n.get("_"):
            rows.append("<tr><td class='note' colspan='5' style='border-top:0'>%s</td></tr>"
                        % ('<span class="cert">【確度 %s】</span>' % inline(n["acc"])
                           + " " + inline(n["_"])))
    return ("<div class='tw'><table><thead><tr><th>id</th><th class='note'>隣</th><th>辺</th>"
            "<th class='note'>共有</th>"
            "<th class='note'>囲いの受け持ち</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>⛔ <b>辺は丸ごと一人の相手とは限らない</b> — "
            "「(区間)」の行は<b>辺の一部だけ</b>で接する相手で、区間は区画どうしの幾何から"
            "毎回測っている(手で持たない)。⚠ <b>街路と書いた辺も「区画に接していないこと」を"
            "生成器が毎回検める</b> — 5 m 以上接する区画が neighbors に無ければ組み立てを止める"
            "(2026-09-01 検図 K6)。</p>")


def nagaya_counts(d, geo):
    """外周の**盲長屋の鎖**の棟数と実延長。⛔ **数を手で持たない**(規則4)。
    ⚠ 盲長屋は「外に窓を持たない**家中長屋**」なので、
    **家中長屋の員数には敷地内の棟とこの鎖の棟の両方が入る**(2026-09-01 検図 K1)。
    ⛔ 単位は**棟**に統一する — 其六 の外周の表と同じ数え方でなければ、
    同じ図の中で同じ物が別の数になる。"""
    C = d["const"]
    n_tot = 0
    L_tot = 0.0
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        a, b = geo.run_span(r)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n, tot, _ = nagaya_chain(L, C["nagayaModC"], C["nagayaModLR"])
        n_tot += n
        L_tot += tot
    return n_tot, L_tot


def todoke_table(d, geo):
    """⭐ **確度Sの一次史料(丹羽家の地震御届)が伝える棟数と、当図の棟数の対照。**

    ⛔ **当図の側の数は json に持たない — ここで図から数える**(CLAUDE.md 規則4)。
    棟を足したり消したりすれば、この表の右の欄はひとりでに動く。
    ⚠ 御届の側の値だけが設計値(`todoke.rows[].todoke`)で、それは史料の記載そのものである。
    ⛔ **御届の数は「壊れた数」= 在った数の下限**であって「在った数」ではない
    (2026-09-01 の考証 Ko1)。
    """
    t = d["todoke"]
    labels = [m.get("label", "") for m in d["munes"]] + \
             [s.get("label", "") for s in d["service"]]

    def n_label(*keys):
        return sum(1 for L in labels if any(k in L for k in keys))

    per = sum(geo.edge(i)[2] for i in range(len(geo.P)))
    # ⭐ 丹羽が囲いを受け持つ辺の合計(辺3 は内藤が受け持つ)。分母の候補として並べる。
    own = sum(geo.edge(e["i"])[2] for e in d["edges"] if e["owner"] == "丹羽")
    nagaya_runs = [r for r in d["runs"] if r["kind"] == "Nagaya"]
    hei_runs = [r for r in d["runs"] if r["kind"] != "Nagaya"]
    n_chain, L_chain = nagaya_counts(d, geo)
    n_in = n_label("家臣長屋")
    zu = {
        # ⚠ `zu` の値は**生成器が組む html** なので escape しない(下の `vhtml`)。
        #   ⛔ ただし td は既定 nowrap なので、**1行を長くしない** — `<br>` で折り、
        #   内訳は `cert`(小字)に落とす。長い1行は隣の「備考」列を潰す(2026-09-01)。
        "kashinNagaya": ("<b>%d 棟</b><br><span class='cert'>敷地内 %d + 外周の鎖 %d</span>"
                         % (n_in + n_chain, n_in, n_chain)),
        "kura": "%d 棟" % n_label("土蔵"),
        "umaya": "%d 棟(種別ごと無い)" % n_label("厩", "馬屋"),
        "kamaya": "%d 棟(種別ごと無い)" % n_label("釜屋"),
        "umamisho": "%d 棟(種別ごと無い)" % n_label("馬見所"),
        "monooki": "%d ケ所(種別ごと無い)" % n_label("物置"),
        "ishigaki": "%d ケ所(土留めも法面も無い)" % len(d["terraceWalls"]),
        "gaishu": "築地塀 %d 本 + 盲長屋 %d 本(%d 棟)<br>"
                  "<span class='cert'>周長 %.0f m ／ 丹羽が持つ辺 %.0f m</span>"
                  % (len(hei_runs), len(nagaya_runs), n_chain, per, own),
        "mon": "表門 %d ・小門 %d" % (1 if d.get("gate") else 0, len(d["komon"])),
        # ⭐ 屋敷内の塀 = 外周の辺に載っていない run。⛔ 0 を手で書かない — 引けば動く。
        "uchibei": "<b>%d 本</b><br><span class='cert'>当図の囲いは外周だけ</span>"
                   % sum(1 for r in d["runs"] if r.get("edge") is None),
        # ⛔ 御届が数えるのは「系統」なので、**系統どうしで対照する**(2026-09-01 検図 L3)。
        "goten": "<b>1 系統</b><br><span class='cert'>棟 %d(表・奥・役所・台所)</span>"
                 % len(d["munes"]),
    }
    rows = []
    for r in t["rows"]:
        # ⭐ `zu` に鍵があれば**生成器が組んだ html**(escape しない)。無ければ json の文字列。
        v = zu.get(r["zu"])
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='note' style='max-width:34ch'>%s</td></tr>"
                    % (html.escape(r["item"]), inline(r["todoke"]),
                       v if v is not None else inline(r["zu"]),
                       inline(r.get("note", ""))))
    # ⭐ 表囲の延長は「間」からここで換算する(m の値を json に二重に持たない)。
    kl = t.get("kenLen")
    cap = ""
    if kl:
        m = kl * d["const"]["ken"]
        cap = ("<p class='cap'>⭐ <b>表囲(外周)で<u>崩れた</u>延長は %.1f 間 = %.1f m</b>。"
               "⛔ <b>これは表囲の全長ではなく、崩れた分だけである。</b>"
               "<br>⛔ <b>分母は一つに決まらないので、両方を並べる</b>(2026-09-01 検図 K5)— "
               "<b>区画周長 %.1f m に対して %.1f %%</b> / "
               "<b>丹羽が囲いを受け持つ辺 %.1f m(辺3 は内藤が持つので除く)に対して %.1f %%</b> "
               "に相当する。⛔ どちらか一方を「正しい割合」として採らない。"
               "<br>⛔ <b>この割合は「外周に長屋は無かった」を補強しない</b> — "
               "むしろ逆で、<b>御届の沈黙が届く範囲はこの割合までである</b>という"
               "<b>射程の限定</b>に働く。残りが何だったかは御届からは読めない【?】 — "
               "(a) 崩れなかった区間 (b) 別種の囲い (c) 隣家が持つ辺 のいずれとも決まらない。"
               "⛔ <b>「残りも練塀だった」と埋めない。</b>未解決 P-26。"
               "<br>⚠ <b>間 → m は 1間 = 6尺 = %.3f m(CLAUDE.md の江戸間)を当てた</b>【U 換算の仮定】"
               " — <b>史料は間の種別を書かない。</b>京間・田舎間で読めば延長も割合も動く。</p>"
               % (kl, m, per, 100.0 * m / per, own, 100.0 * m / own,
                  d["const"]["ken"]))
    return ("<div class='tw'><table><thead><tr><th>事項</th>"
            "<th>御届【S】<br><span class='cert'>いずれも<b>壊れた</b>数</span></th>"
            "<th>当図</th><th class='note'>備考</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>" + cap)


def pending_table(d):
    PC = {"高": "var(--shu)", "中": "var(--nagaya)", "低": "var(--dim)"}
    # ⚠ 「件」は class='note'(折り返す)。既定の td は white-space:nowrap なので、
    #   題を1行に伸ばして表が枠を越え、「中身」の右端が切れていた(2026-08-31 に是正)。
    # ⭐ 「図」の列は **FIGREF が組み立て時に控えた図版番号**を引く — 手で「其十七」と
    #   書くと図版が増減したときに黙ってズレる(2026-08-31 検図 K-14)。
    rows = ["<tr><td>%s</td><td style='color:%s;font-weight:700'>%s</td><td>%s</td>"
            "<td class='note' style='max-width:26ch'>%s</td>"
            "<td class='note'>%s</td></tr>"
            % (p["id"], PC.get(p["pri"], "var(--dim)"), p["pri"],
               FIGREF.get(p.get("fig"), "—"), html.escape(p["title"]),
               inline(p["_"])) for p in d["pending"]]
    return ("<div class='tw'><table><thead><tr><th>#</th><th>優先</th><th>図</th>"
            "<th class='note'>件</th>"
            "<th class='note'>中身</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>「図」の列は、その未解決を図で見られる図版の番号。"
            "<b>P-1 は裁定図(%s)</b>で、どこ・現況の実測値・三案・断面・変わる数値・推奨が"
            "そろっている。</p>" % FIGREF.get("saitei", "—"))


def history():
    try:
        log = subprocess.check_output(
            ["git", "-C", ROOT, "log", "--date=short", "--pretty=%h|%ad|%s", "--",
             "docs/Sashizu/niwa_sakyo_sashizu.json", "docs/Sashizu/niwa_sakyo_kosho.md"]).decode()
    except Exception:
        log = ""
    rows = []
    for ln in log.strip().split("\n"):
        if not ln.strip():
            continue
        hh, dt, sub = ln.split("|", 2)
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td class='note'>%s</td></tr>"
                    % (hh, dt, html.escape(sub)))
    if not rows:
        rows = ["<tr><td colspan='3' class='note'>初版(未コミット)</td></tr>"]
    return ("<div class='tw'><table><thead><tr><th>commit</th><th>日付</th><th class='note'>件名</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 組み立て
def plate(h, num, title, meta=""):
    h.append('<div class="plate"><div class="phead"><h2>%s　%s</h2>%s</div>'
             % (num, title, ('<span class="meta">%s</span>' % meta) if meta else ""))


def fig(h, svg, cap=None, legend=None):
    h.append('<div class="fig">%s</div>' % svg)
    if legend:
        h.append('<div class="legend">%s</div>' % legend)
    if cap:
        h.append('<p class="cap">%s</p>' % cap)


# 図版番号の控え。⛔ **本文や表に「其十七」と直書きしない** — 組み立て時にここへ控えて引く。
FIGREF = {}


def figtok(key):
    """⭐ **まだ組んでいない節の番号を前方参照する**ための差し込み札。
    ⛔ 手で数えた章番号を本文に書かない(章が増えると必ずズレる。2026-09-01 考証 Ko-K)。
    札は `main()` の最後に `FIGREF` の実値へ置き換わり、残っていれば生成器が落ちる。"""
    return "@@FIG:%s@@" % key

# **必須8図**(`unity-buke-yashiki/references/sashizu.md` §3)。
# ⛔ **揃っているかを冒頭で自己申告する**(2026-09-01 検図 K10: 「4 主郭 御殿平面」が
#    欠図なのに、どこにもそう書いていなかった)。`key` は FIGREF の控え。
ZUMEN = [
    ("1", "敷地全体 配置図", "haichi", None),
    ("2", "現況図(造成前の地形)", "genkyo", None),
    ("3", "切盛図", "kirimori", None),
    ("4", "主郭 御殿平面", None,
     "⛔ <b>欠図。</b>御殿が在庫の一軒家プレハブの代用で、<b>室割り・入側・渡廊下が"
     "一つも定義されていない</b>ので図にできない(未解決 P-9)。"),
    ("5", "副郭の平面", "—",
     "⭕ <b>非該当。</b>当邸は面(terrace)を持たない無造成の屋敷で、郭が分かれていない。"),
    ("6", "断面", "sections", None),
    ("7", "動線図", "dousen", None),
    ("8", "格式の判断と典拠", "kosho", None),
]


def zumen_table(nsec):
    rows = []
    na = 0
    for no, nm, key, miss in ZUMEN:
        if key == "—":
            na += 1
            cell = ("<td style='color:var(--dim)'><b>—</b></td>"
                    "<td class='note'>%s</td>" % miss)
        elif miss:
            cell = "<td style='color:var(--shu)'><b>✗</b></td><td class='note'>%s</td>" % miss
        else:
            cell = ("<td style='color:var(--take)'><b>○</b></td>"
                    "<td class='note'>%s</td>" % (FIGREF.get(key) or "—"))
        rows.append("<tr><td>%s</td><td>%s</td>%s</tr>" % (no, nm, cell))
    ng = sum(1 for q in ZUMEN if q[3] and q[2] != "—")
    ok = len(ZUMEN) - na - ng
    return ("<div class='tw'><table><thead><tr><th>#</th><th>必須の図"
            "(<code>sashizu.md</code> §3)</th><th>有無</th><th class='note'>どこに</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>⛔ <b>必須の図が揃っているかを冒頭で自己申告する</b>"
            "(2026-09-01 検図 K10)。<b>○ %d ／ ✗ %d(欠図)／ — %d(非該当)</b>。"
            "断面は %d 面(東西・南北・斜)に加えて、明治の復元面との対比を東西・南北で重ねてある。"
            "<br>⛔ <b>欠けている図を「後で描く」と書いて先へ進まない</b> — "
            "描けない理由(この図では御殿の室割りが無いこと)がそのまま未解決である。</p>"
            % (ok, ng, na, nsec))

TEXTN = [0]


def check_text_overflow(body, pad=2.0):
    """⛔ **図の文字が枠からはみ出していないかを機械で検める。**
    2026-08-31 の検図で、断面の注記(125字)が SVG の幅を 142.8px 超え、末尾が消えていた —
    目視では「文が短く見える」だけなので気づけない。**組むたびに全テキストを測る。**

    ⛔ **横だけでなく縦も測る**(2026-08-31 の指摘)。SVG は `viewBox` の外を描かないので、
    `y > H`(下へ落ちる)と `y − fontSize < 0`(上へ出る)は、横のはみ出しと同じく
    **文字が丸ごと消える**。`TW()` が行を増やしたときに下へ抜けるのが典型で、
    横幅で折っているぶん**縦のほうが起きやすい**。"""
    import re
    TEXTN[0] = 0
    out = []
    for msvg in re.finditer(r'<svg viewBox="0 0 ([\d.]+) ([\d.]+)"[^>]*aria-label="([^"]*)"',
                            body):
        W = float(msvg.group(1))
        H = float(msvg.group(2))
        label = msvg.group(3)
        end = body.find("</svg>", msvg.end())
        seg = body[msvg.end():end if end > 0 else len(body)]
        for mt in re.finditer(r'<text class="([^"]*)" x="([-\d.]+)" y="([-\d.]+)"'
                              r'(?: style="([^"]*)")?[^>]*>([^<]*)</text>', seg):
            cls, x, y = mt.group(1), float(mt.group(2)), float(mt.group(3))
            style, txt = mt.group(4) or "", mt.group(5)
            if "rotate" in (mt.group(0) or ""):
                continue
            TEXTN[0] += 1
            w = _tw(html.unescape(txt), cls)
            fs = _FS.get(cls, 10.5)
            m2 = re.search(r"font-size:([\d.]+)px", style)
            if m2:
                fs = float(m2.group(1))
                w = w * fs / _FS.get(cls, 10.5)
            anc = "start"
            if "text-anchor:middle" in style:
                anc = "middle"
            elif "text-anchor:end" in style:
                anc = "end"
            x0 = x if anc == "start" else (x - w / 2 if anc == "middle" else x - w)
            x1 = x0 + w
            if x1 > W + pad or x0 < -pad:
                out.append("%s: 「%s…」が横に %.1fpx はみ出す(幅 %.0f / 文字の右端 %.0f)"
                           % (label, html.unescape(txt)[:22], max(x1 - W, -x0), W, x1))
            # 縦。y は**ベースライン**なので、上端は y − fs、下端はほぼ y(ディセンダは無視)
            if y > H + pad:
                out.append("%s: 「%s…」が下に %.1fpx はみ出す(高さ %.0f / ベースライン %.0f)"
                           % (label, html.unescape(txt)[:22], y - H, H, y))
            elif y - fs < -pad:
                out.append("%s: 「%s…」が上に %.1fpx はみ出す(文字の上端 %.0f)"
                           % (label, html.unescape(txt)[:22], fs - y, y - fs))
    return out

KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
       "其十一", "其十二", "其十三", "其十四", "其十五", "其十六", "其十七", "其十八",
       "其十九", "其二十", "其二十一", "其二十二", "其二十三", "其二十四", "其二十五",
       "其二十六", "其二十七", "其二十八", "其二十九", "其三十"]


def main():
    d = json.load(open(JSON, encoding="utf-8"))
    mdtext = open(MD, encoding="utf-8").read()
    prose = md2html(mdtext)
    # ⛔ **強調の偶奇を先に検める**(検図 K14)。奇数個あると以降の強調が反転する。
    embad = check_emphasis(("sashizu.json", d))
    # ⚠ md の強調は**行をまたぐ**(段落の中で折り返してよい)ので、**段落単位**で数える。
    _ln = 1
    for _para in mdtext.split("\n\n"):
        if _para.count("**") % 2:
            embad.append("kosho.md:%d 付近(%d 個)「%s…」"
                         % (_ln, _para.count("**"), _para.strip()[:26]))
        _ln += _para.count("\n") + 2
    dem = DEM(DEMF)
    # ⭐ 復元レイヤ。仕様(人が書く)と面(build_niwa_sakyo_recon.py が書く)を別に読む。
    RECON_SPEC.update(json.load(open(RECON, encoding="utf-8")))
    demA, demB = DEM(WORLD, "h"), DEM(WORLD, "hB")
    RECON_OUT.update(demA.d["_computed"])
    SURF.update({"current": dem, "recon": demA, "reconB": demB})
    for nmw, w in (("recon", demA), ("reconB", demB)):
        if (w.x0, w.z0, w.st, w.nx, w.nz) != (dem.x0, dem.z0, dem.st, dem.nx, dem.nz):
            raise SystemExit("⛔ 復元面 %s の格子が現況 DEM と違う — "
                             "build_niwa_sakyo_recon.py を回し直すこと" % nmw)
    pcs = {p["id"]: p["pts"] for p in json.load(open(PARCELS, encoding="utf-8"))["parcels"]}
    PCS.update(pcs)
    P = [tuple(q) for q in pcs[d["parcelId"]]]
    # 区画の正典との突き合わせ(写しがズレたら止める)
    for a, b in zip(P, d["polygon"]):
        if abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6:
            raise SystemExit("⛔ json の polygon が parcels.json の %s と食い違う: %s vs %s"
                             % (d["parcelId"], a, b))
    geo = Geo(d, P)
    GEOP[0] = P
    SASHIZU_D[0] = d
    CLIFF[0] = Cliff(RECON_SPEC["cliff"])
    # ⛔ グリッドの原点は表門の芯の写しなので、多角形から算出した門と突き合わせる
    #    (区画を引き直すと門の x が動く — 2026-09-01 に実際に 0.24 m 動いた)
    gk = d["grid"]["shukaku"]
    if abs(gk["x0"] - geo.gate[0]) > 1e-3 or abs(gk["z0"] - geo.gate[1]) > 1e-3:
        raise SystemExit("⛔ grid.shukaku の原点 (%.4f, %.4f) が表門の芯 (%.4f, %.4f) と食い違う "
                         "— json を直すこと" % (gk["x0"], gk["z0"], geo.gate[0], geo.gate[1]))
    # ⛔ 隣家との共有辺は**番号ではなく幾何で**照合する(EDO-0012: 辺番号を2度取り違えた)
    for nb in d["neighbors"]:
        if nb["id"] not in pcs:
            continue
        Q = [tuple(q) for q in pcs[nb["id"]]]
        for ei in nb["edges"]:
            a, b, _, _ = geo.edge(ei)
            if nb.get("partial"):
                # ⭐ **区間だけ接する隣**(2026-09-01 追加)。辺の一部が輪郭に沿っていればよい。
                tl, s0, s1 = edge_touch(geo, ei, Q)
                if tl < 5.0:
                    raise SystemExit("⛔ 辺%d を %s の**区間**共有としているが、"
                                     "接している長さが %.1f m しかない — neighbors を直すこと"
                                     % (ei, nb["id"], tl))
                continue
            if not any(max(abs(a[0] - u[0]), abs(a[1] - u[1])) < 4.0
                       and max(abs(b[0] - v[0]), abs(b[1] - v[1])) < 4.0
                       for u, v in [(Q[k], Q[(k + 1) % len(Q)]) for k in range(len(Q))]
                       + [(Q[(k + 1) % len(Q)], Q[k]) for k in range(len(Q))]):
                raise SystemExit("⛔ 辺%d を %s の共有辺としているが、%s の多角形に対応する辺が"
                                 "無い(4m 以内で照合)— neighbors の辺番号を取り直すこと"
                                 % (ei, nb["id"], nb["id"]))
    # ⛔ **街路と書いた辺も「区画に接していないこと」を検める**(2026-09-01 検図 K6)。
    #    従前は `(街路)` の辺を素通しにしていたので、辺7 の東の 4 割が町屋と背中合わせで
    #    あることが図に出ていなかった。**declared していない接触が 5m 以上あれば止める。**
    for e in d["edges"]:
        nbs = [q for q in d["neighbors"] if e["i"] in q["edges"]]
        if not any(q["id"] == "(街路)" for q in nbs):
            continue
        named = set(q["id"] for q in nbs)
        for pid, Q in pcs.items():
            if pid == d["parcelId"] or pid in named:
                continue
            tl, s0, s1 = edge_touch(geo, e["i"], [tuple(q) for q in Q])
            if tl >= 5.0:
                raise SystemExit("⛔ 辺%d を街路に面する辺としているが、区画 %s と %.1f m "
                                 "(s %.1f〜%.1f)接している — neighbors に足して"
                                 "『どこまでが街路か』を書くこと" % (e["i"], pid, tl, s0, s1))
    area = poly_area(P)
    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"),
               encoding="utf-8").read()

    n = [0]

    def nx():
        n[0] += 1
        return KAN[n[0] - 1]

    h = ['<meta charset="utf-8">', "<title>丹羽左京大夫上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    # ⛔ **表紙に家格(「外様」)を書かない** — 武鑑に語が無く典拠を持たない【?】。
    #    断定と否認を同じ頁に同居させない(CLAUDE.md 規則7・2026-09-01 考証 Ko-A)。
    h.append('<p class="eyebrow">永田馬場 山王坂 ／ 陸奥二本松藩 十万七百石 ／ 大広間詰</p>')
    h.append("<h1>丹羽左京大夫長富 上屋敷 指図</h1>")
    h.append('<p class="lede">安政三年(1856)の姿。切絵図の直違紋で<b>上屋敷</b>と確定し、'
             '溜池遺跡の発掘(都埋文258)が<b>長屋地区・蔵跡・池跡・井戸・境界石垣・埋立造成</b>を出している'
             '【S 記載事項に限る。⚠ 本文未入手・抄録のみ】。'
             '表門が<b>東辺</b>であることは切絵図の IIIF 実見で確定した【A】。'
             '跡地は衆議院議員会館と首相官邸の一部。'
             '<b>数値の正典は <code>niwa_sakyo_sashizu.json</code>、文章の正典は '
             '<code>niwa_sakyo_kosho.md</code>、地盤は <code>niwa_sakyo_dem.json</code>。</b>'
             'この頁はその三つから組んだもので、実装は読んでいない。</p>')
    h.append('<div class="box"><p>⚠ <b>この指図は「既に建っているものの書き起こし」である。</b>'
             '当邸は 2026-08-11 に <code>EdoSannoBukeBuilder.Stage4_Niwa()</code> として実装され、'
             '専用の指図を持たないまま山王社の指図の脇に置かれていた。'
             '2026-08-30 のユーザー裁定で独立の指図として切り出した。'
             'したがって順序は CLAUDE.md 規則2(指図 → レビュー → 実装)の<b>逆</b>で、'
             '書き起こしの過程で見つかった不整合は<b>直さずに「未解決」へ立ててある</b> — '
             '直すのは設計の判断で、指図方の領分ではない。'
             '<b>この指図をもって「合格」とは言えない。</b>'
             '敷地は <b>%s m²(%s 坪)</b>【P 当プロジェクトの敷地割から算出】。'
             '<br>⚠ <b>2026-08-30 にユーザーが敷地割を引き直した</b>(8頂点 → 9頂点)。'
             '<b>辺の番号は総入れ替え</b>になっているので、旧番号で書かれた記録を読み替えないこと。'
             '<br>⚠ <b>拝領坪数の同格帯([%s]【%s】%s〜%s 坪)の %.2f 倍</b>にあたる。'
             '⛔ これは<b>傍証にとどまる</b>(原典未確認の二次情報で、当家を名指ししていない)。'
             '⚠ <b>倍率が 1 を大きく超えるので、拝領坪数との整合は考証方の判断に回す。</b></p></div>'
             % ("{:,.0f}".format(area), "{:,.0f}".format(area / TSUBO),
                d["norm"]["src"], d["norm"]["acc"],
                "{:,}".format(d["norm"]["tsuboBand"][0]),
                "{:,}".format(d["norm"]["tsuboBand"][1]),
                (area / TSUBO) / (sum(d["norm"]["tsuboBand"]) / 2.0)))

    # ⛔ **必須8図の充足表**は図版番号が要るので、ここに枠だけ置いて最後に差し替える。
    ZPLACE = len(h)
    h.append("")

    # 其一
    FIGREF["haichi"] = KAN[n[0]]
    plate(h, nx(), "敷地全体 配置図",
          "北が上 ／ %s 坪【P】 ／ 表門 = 東辺 z=839" % "{:,.0f}".format(area / TSUBO))
    fig(h, haichi_svg(d, geo, dem, KAN[n[0] - 1]),
        legend='<span style="color:var(--shu)">■ 表向・表門</span>'
               '<span style="color:var(--roka)">■ 奥向</span>'
               '<span style="color:var(--hei)">■ 役方・築地塀</span>'
               '<span style="color:var(--nagaya)">■ 勝手・盲長屋</span>'
               '<span style="color:var(--ishi)">■ 土蔵・家臣長屋</span>'
               '<span style="color:var(--shu)">┄ 隣地の区画</span>'
               '<span style="color:#7A2E1E">┄・┄ 断面の切り位置</span>',
        cap="<b>北の帯(山王坂沿い)と、そこから南へ延びる脚(京極の西・内藤の北)。</b>"
            "南西の切り欠きは山王社の社人八家。"
            "<b>辺%d(内藤との境)には囲いを建てていない</b> — 背中合わせで内藤が受け持つ前提"
            "(未解決 P-5)。⚠ <b>最長の辺(山王坂)に門が無い</b>のが当図の特徴で、"
            "⭕ <b>切絵図の文字の頭も東を指す</b>ので、これは切絵図と矛盾しない【A IIIF実見】。"
            "<br>⚠ <b>北帯の南辺(京極との境)は世界軸に平行ではない</b> — "
            "2026-08-30 の敷地割の引き直しで、一直線だった南辺が<b>斜めの2辺</b>に割れて"
            "南へ張り出した。<b>辺の番号は総入れ替えになっている。</b>"
            % next(e["i"] for e in d["edges"] if e["run"] is None))
    h.append("<h3>外周の辺と割付け</h3>")
    h.append(edges_table(d, geo))
    h.append("</div>")

    # 其二 現況図
    FIGREF["genkyo"] = KAN[n[0]]
    plate(h, nx(), "現況図(造成前の地形)",
          "段彩 2 m ／ 等高線 2 m(10 m 太線) ／ 確度P")
    fig(h, genkyo_svg(d, geo, dem, KAN[n[0] - 1]),
        legend=dem_legend(),
        cap="<b>造成のすべての出発点。</b>当邸は造成をしないので、これが<b>そのまま設計地盤</b>になる。"
            "赤の破線は隣地の区画 — 境の地形は隣と一続きなので重ねてある。"
            "<br>⛔ <b>この「現況」は今日の地面であって江戸の地面ではない。</b>"
            "区画の中央から西にかけて、<b>単一の標高でそろった平場</b>が広がっている — "
            "%s。⚠ <b>自然の谷底ならこうはならない</b>。"
            "2026-08-11 の実装時にはこの造成をラプラシアン緩和で復元した地形があり、"
            "棟はその上に置かれた。<b>その復元は 2026-08-22 の地形の作り直しで消えている。</b>"
            "結果として、いまの地盤では御殿が地中へ深く入る(其三・其四)。<b>未解決 P-1。</b>"
            "<br>⭕ <b>地盤は正本 <code>base_dem.json</code> からの切り出しに一本化した</b>"
            "。正本が東と南へ広がったので、当邸だけ別経路で"
            "参照ハイトマップから直に切っていた <code>build_niwa_sakyo_dem.py</code> は捨てた — "
            "いまは <code>build_base_dem.py</code> の <code>SLICES</code> が全邸まとめて回す。"
            "⛔ Unity の live terrain からは採っていない(CLAUDE.md 規則13)。"
            % flat_stat(geo, dem))
    h.append("</div>")

    # 其三 切盛図
    FIGREF["kirimori"] = KAN[n[0]]
    plate(h, nx(), "切盛図", "Δ = 設計地盤 − 現況 ／ 全域 0.00 m")
    fig(h, kirimori_svg(d, geo, dem, KAN[n[0] - 1]),
        legend=cutfill_legend(),
        cap="<b>切土も盛土も一切しない。</b>実装は <code>NaturalMode = true</code> で、"
            "囲いも棟も置いた点の地形にそのまま載る。段(terrace)を持たないので土留めも法面も石段も無い。"
            "<br>⚠ <b>これは「地形が平らだから」ではない。</b>区画の中の起伏は 19.8 m ある。"
            "無造成のまま棟を置いた結果が、図に朱で出ている<b>埋没</b>である — "
            "座は外形の下の9点の地形の<b>最小値</b>で決まるので、起伏のある所では棟の大半が地中へ入る。"
            "<b>CLAUDE.md 規則3(|設計面 − 自然地形| ≤ 0.5 m)を満たすのは4棟だけ。未解決 P-1。</b>")
    h.append("</div>")

    # 其四 棟の接地
    plate(h, nx(), "棟の接地", "座 ／ 外形の下の地形 ／ 埋没 — 規則3の合否")
    fig(h, seat_svg(d, geo, dem, KAN[n[0] - 1]),
        cap="<b>棟ごとに、外形の下の自然地形の幅(灰の棒)と、そこへ据えた座(朱の線)を並べた。</b>"
            "座は <code>CenterSeat</code> が中心・四隅・四辺中点の9点で採った地形の最小値から"
            "沈め代を引いた高さ。<b>棒の上端が朱の線より上に出ている量が、そのまま棟が地中へ入る深さ</b>。")
    h.append(munes_table(d, dem, geo))
    h.append('<p class="cap">(u, v) は<b>表門の芯を原点とする世界軸グリッド</b>(u=東+ / v=北+、単位は間)。'
             '⚠ <b>建物の寸法は在庫部材の実寸で決まっていて間の倍数ではない</b> — '
             'グリッドは位置の読み取りのためのもので、寸法をこれに丸めていない。'
             '⛔ <b>室割りは無い</b>(未解決 P-9)。</p>')
    h.append("</div>")

    # 其五 動線
    FIGREF["dousen"] = KAN[n[0]]
    plate(h, nx(), "動線図", "表向 / 役方 / 勝手 / 奥向 / 家中")
    fig(h, dousen_svg(d, geo, dem, KAN[n[0] - 1]),
        cap="<b>門は表門1基だけ。</b>勝手口も裏門も無いので、賄も物資も表門から入り、"
            "台地の縁を降りて台所へ至る。⛔ <b>これは確度Sの史料の下限に届いていない</b> — "
            "御届【S】は表門のほかに<b>広敷門1・用心口門3</b>を数える(%s の門の行)。"
            "<b>どこへ開けるかは配置の判断で、門を増やすことは格式にも触れるのでユーザーの裁定"
            "(未解決 P-8)。</b>渡廊下は起こしていないので、棟から棟へは外を歩く。"
            % figtok("todoke"))
    h.append(routes_table(d, dem))
    h.append('<p class="cap">登り・下りは <code>niwa_sakyo_dem.json</code> を 2 m 刻みで拾った累計。'
             '⚠ <b>勝手の下りが大きいのは、台所が上の平場(近代の造成)の底に立っているためである</b>(未解決 P-1)。</p>')
    h.append("<h3>崖を東西に横切ったら — 勾配の検算</h3>")
    h.append('<p class="cap">⭐ <b>崖は南北の直線ではなく WNW–ESE の斜めである。</b>'
             'だから<b>横切る向きで勾配が変わる</b> — 上の動線はいずれも東西方向に'
             '崖を突っ切っていないので、下の検算とは別の勾配を踏んでいる。'
             '⛔ <b>これは動線案ではない</b>(動線を引き直すのは配置の判断)。</p>')
    h.append(cross_check_table(d))
    h.append("</div>")

    # 其六 外周の展開
    plate(h, nx(), "外周の展開", "辺0 → 辺%d を一列に伸ばす ／ 駒ごとの天端と地盤" % (len(geo.P) - 1))
    fig(h, tenkai_svg(d, geo, dem, KAN[n[0] - 1]),
        legend='<span style="color:var(--hei)">■ 築地塀</span>'
               '<span style="color:var(--nagaya)">■ 盲長屋</span>'
               '<span style="color:var(--shu)">■ 表門(開口)</span>'
               '<span style="color:var(--shu)">┄ 囲い無し</span>'
               '<span>── 外周に沿った地盤</span>'
               '<span style="color:var(--shu)">○ 塀が切れる継ぎ目</span>',
        cap="<b>外周のどこが塀で、どこが長屋で、どこが開いているか。</b>"
            "通りに面する西辺(谷側)だけが盲長屋で、他は築地塀。"
            "<br>⚠ <b>「塀」の種別は二段に分けて読む</b> — <b>史料の語は「練塀/煉塀」【S】</b>"
            "(二つの一次史料が独立に書く)。<b>当図がそれを築地塀の部材で受けたのは【U 語義の同定】</b>で、"
            "⛔ <b>「練塀=築地塀」は史料が言っていない</b>(練塀=瓦と練土を交互に積む / "
            "築地塀=版築の土塀。<b>別種</b>で、見付の意匠に直に効く)。"
            "受ける部材を替えるかは意匠の判断なので指図方は決めない — "
            "<code>niwa_sakyo_kosho.md</code>「外周の囲い」。"
            "<br><b>辺%d は丹羽側では建てない</b>(長さは下の表)— 内藤が背中合わせで受け持つ前提だが、"
            "内藤側に実際にその塀が在るかは未確認(未解決 P-5)。"
            "<br>⛔ <b>塀は地形追従で、駒ごとに独立して地面へ載る</b>(<code>nat-max2</code>)。"
            "そのため天端は一直線にならず、斜面では<b>継ぎ目の段差が塀の高さを超えて塀が切れる</b> — "
            "上の駒の下端が下の駒の天端より高くなり、そこに穴が開く。"
            "<b>朱の丸がその位置。未解決 P-14。</b>"
            "<br>⚠ スキル <code>perimeter.md</code>「外周は地形追従で置けばよい」は<b>撤回済みの誤り</b>で、"
            "一本の run で天端が大きく振れると棟が段々になる。直し方(一直線の天端 + 土留め / "
            "段付き天端 / 斜面区間を長屋に替える)は<b>設計の判断なのでユーザーの裁定に回す</b>。"
            % next(e["i"] for e in d["edges"] if e["run"] is None))
    h.append("<h3>run ごとの天端(駒の座 + 塀高・長屋高)</h3>")
    h.append(tenkai_table(d, geo, dem))
    h.append('<p class="cap">「振れ」は同じ run の中の天端の最高 − 最低、「最大段差」は'
             '隣り合う駒の天端の差の最大。<b>段差が塀の高さ(<code>const.dobeiH</code>)を超えると'
             '塀が物理的に切れる</b>。⚠ <b>盲長屋(辺%d)は座を3点の最小値で採る</b>ので、'
             '築地塀より天端が揃う — 採り方の違いがそのまま出ている。</p>'
             % next(r["edge"] for r in d["runs"] if r["kind"] == "Nagaya"))
    h.append("</div>")

    # 其七 取り合い
    plate(h, nx(), "取り合い 詳細", "面で決める ／ 芯で合わせない ／ 図4面 + 表")
    fig(h, toriai_svg(d, geo, KAN[n[0] - 1]),
        cap="<b>① 表門 ↔ 築地塀(J1 / J2)。</b>実装は塀の端を『門の実測半幅 + 0.35 m』で"
            "止めているので、<b>閉じの検査が見る面(塀の妻面 ↔ 螻羽の外端)が 0.35 m 開く</b>。"
            "⭕ <b>螻羽の下の 1.89 m は隙間ではない</b> — 螻羽(屋根の端)は軸部(袖壁)より"
            "外へ出ているので、塀の妻面と軸部のあいだのその距離は<b>屋根の陰</b>である。"
            "<b>直すのは 0.35 m だけ(未解決 P-3)。</b>動かすのは塀の側(門は開口の芯に固定)。")
    fig(h, toriai_nagaya_svg(d, KAN[n[0] - 1]),
        cap="<b>② 家臣長屋 西 ↔ 東(J3)。</b>芯間 7.80 m に対し壁の実寸は 7.91 m なので"
            "<b>壁が 0.11 m めり込む</b>(許容 −0.00 を超える)。"
            "⭕ <b>屋根が 0.69 m 重なるのは長屋の連なりとして正しい姿</b>で、"
            "機械検査の「外形の重なり」はここを拾う — だから除外規約を置いてある。"
            "<b>直すのは壁の面(未解決 P-4)。</b>")
    fig(h, toriai_chain_svg(d, geo, KAN[n[0] - 1]),
        cap="<b>③ 盲長屋の鎖 ↔ 隅(J4 / J5)。</b>鎖の実延長が辺より長く、中央寄せなので"
            "<b>両端が隅の外へ出る</b>。⛔ <b>run の端を「丸ごとの駒が並んだ成り行き」にしない</b> — "
            "端は隅の面に合わせ、端数は鎖の中で吸う(sashizu.md §3f)。"
            "駒数を落とすと今度は端数が余るので、<b>端数を隅と開口のどちらで吸うかがユーザーの裁定"
            "(未解決 P-2)。</b>")
    fig(h, toriai_bansho_svg(d, geo, KAN[n[0] - 1]),
        cap="<b>④ 門と番所 ↔ 区画線(J8 / J9)。</b>門の芯が区画線の上に乗っているので、"
            "門の屋根も番所も線の外(通り側)へ出る。"
            "⚠ <b>区画線は南北で傾いている</b>ので、はみ出し量は番所の南端と北端で違う — "
            "取り合い表の値は門の芯の位置で測った代表値である。"
            "<b>どこを区画線と見るか(敷居の芯か・軸部の外面か)が決まっていない(未解決 P-7)。</b>")
    h.append("<h3>取り合い表</h3>")
    h.append(joints_table(d, geo))
    h.append("</div>")

    # 断面(全断面 同一縮尺)
    sscale = section_scale(d)
    FIGREF["sections"] = "%s〜%s" % (KAN[n[0]], KAN[n[0] + len(d["sections"]) - 1])
    for s in d["sections"]:
        plate(h, nx(), s["name"], s["view"] + " ／ 垂直倍率 ×%.1f ／ 全断面 同一縮尺" % VEX)
        fig(h, section_svg(d, geo, dem, s, KAN[n[0] - 1], sscale),
            cap=inline(s.get("_", "")) if s.get("_") else
                "地盤の実線と造成前の破線が<b>完全に重なる</b> — 造成していないことがこの図で読める。")
        h.append("</div>")

    # 明治16年の実測 vs 現況DEM(⭐ 裁定の根拠なので裁定図より前に置く)
    FIGREF["meiji"] = KAN[n[0]]
    nread = sum(1 for a in RECON_SPEC["anchors"] if a["y"] is not None)
    plate(h, nx(), "明治16年の実測 vs 現況DEM",
          "五千分一東京図(0.3175 m/px)原寸実見 ／ 標高点 %d 点(うち値が読めるのは %d 点)"
          " ／ 三区分は Δ から機械で分ける" % (len(RECON_SPEC["anchors"]), nread))
    h.append('<div class="box"><p>⛔ <b>現況DEM の「造成前」は、『当プロジェクトのシーンで'
             '我々が流した造成の前』という意味であって、近代開発の前ではない。</b>'
             '<code>base_dem.json</code> 自身が「これは現代の地面であって江戸の地面ではない」と'
             '明記しており、丹羽区画には<b>衆議院議員会館の掘削</b>と<b>官邸側の盛土</b>が'
             'そのまま入っている。'
             '<br>⭐ <b>そこで錨を明治16年(1883)の五千分一東京図に取り替えた。</b>'
             '安政三年(1856)の27年後で、当区画に近代の建物が入る前である。'
             '標高点の<b>読み値は確度A</b>(原寸実見)、<b>世界座標は確度P(±3 m)</b>'
             ' — ⚠ 2026-09-01 に「±10〜20 m」から訂正した(区画の輪郭5辺で較正した残差が 1〜3 m)。'
             '<br>⚠ <b>2026-09-01 に考証の訂正が3件入った</b> — '
             '<b>(1) 崖の向き</b>(南北の直線 → WNW–ESE の折れ線・X ≳ −185 で東西へ抜ける)/ '
             '<b>(2) 錨2点を典拠から外した</b>(原図の地境線から<b>京極の区画内</b>と判明。'
             'あわせて「南は近代の盛土」という結論も撤回した)/ '
             '<b>(3) 台地の錨1点の値を「?」へ格下げ</b>(公開スキャンで数字が判読不能)。'
             '<br>⭐ <b>[都埋文258]【S】は「丹羽家屋敷が西側の低地を順次埋め立て造成して'
             '屋敷化する過程」を書く</b>ので、<b>明治16年の谷底の高さには丹羽自身が江戸期に'
             '入れた埋立が既に含まれている</b> — つまりこの面は「江戸の丹羽の地面」の'
             '最良の代理であり、従前 案(d) として別に立てていた「埋立造成を史実として再現する」は'
             '<b>この錨の中に吸収されている</b>。'
             '<br>復元の手順の仕様は <code>docs/Sashizu/niwa_sakyo_edo_recon.json</code>、'
             '面は <code>docs/Sashizu/niwa_sakyo_edo_world.json</code>'
             '(生成器 <code>Tools/Sashizu/build_niwa_sakyo_recon.py</code>)。'
             '⛔ <b>復元は丹羽の区画の中だけで行う</b>(2026-08-24 に岡部が越境した前例)。</p></div>')
    fig(h, meiji_svg(d, geo, dem, demA, KAN[n[0] - 1]),
        legend="".join(_sw(c) + lab + "</span>" for _k, lab, c in MJ_CLASS)
               + '<span style="color:var(--ink)">◎ 明治16年の標高点(区画内)</span>'
               '<span style="color:var(--dim)">○ 同(区画外)</span>'
               '<span style="color:var(--ink)">┄ 崖の法尻 / 法肩</span>',
        cap="<b>現況DEM は明治16年の面と、場所によって符号が反転して食い違う。</b>"
            "西端はほぼ一致する【本物の地形】、中央〜東は現況が大きく低い【近代の掘削】。"
            "<br>⭐ <b>崖の向きを訂正した結果、台地の錨 ⊙24.8 が法肩のすぐ下に正しく乗った</b> — "
            "残差は表のとおりで、<b>これは当てはめに使っていない点なので独立した検算である</b>。"
            "<br>⚠ <b>区画内で値の読める錨は %d 点しかない</b>(表の「区画」「読み」の欄)。"
            "⭕ <b>区画の外の錨も当てはめには使う</b>が、<b>復元そのものは区画の中だけ</b>で行う。"
            "<br>⛔ <b>残るのは台地面の高さの典拠</b> — 帯の上端だった錨は数字が判読不能へ"
            "格下げされ、区画外10m の参照 ⊙28【B】と現況DEM は<b>どちらも高い側</b>を指す。"
            "<b>どちらで受けるかは考証の判断なので、指図方は決めていない【?】</b>(未解決 P-15)。"
            % sum(1 for a, c in zip(RECON_SPEC["anchors"], RECON_OUT["anchors"])
                  if c["in"] and a["y"] is not None))
    fig(h, meiji_sec_svg(d, geo, dem, demA, KAN[n[0] - 1]),
        cap="<b>同じ切り位置で、復元面(実線)と現況DEM(破線)を重ねた。</b>"
            "⛔ <b>区画の外では両者が完全に一致する</b> — 復元を区画の中でクリップしているためで、"
            "<b>区画線の上に段が立つ</b>のはその帰結である(摺り付けない)。"
            "⚠ <b>これは隠すべきものではない</b> — 隣家(京極・内藤・社人八家)がまだ"
            "近代の掘削・盛土を履いているという事実そのものだからで、"
            "<b>境の面は明治16年の実測を共通の錨にして突き合わせる</b>"
            "(EDO-0093 のユーザー裁定 = 復元は各邸が自分の区画内で行い、境界は情報共有する)。")
    fig(h, meiji_sec_ns_svg(d, geo, dem, demA, KAN[n[0] - 1]),
        cap="<b>南北の切り位置で重ねた。</b>⛔ <b>訂正した崖の東半は東西に走る</b>"
            "(法尻 Z≈803 / 法肩 Z≈819)ので、<b>東西断面ではその区間と平行になって図に出ない</b> — "
            "この向きが要る(2026-09-01 検図 K5)。"
            "⚠ <b>行き先未決の家臣長屋2棟はまさにこの帯に立っている。</b>")
    h.append("<h3>復元の手順と当てはまり</h3>")
    h.append(recon_table(d, geo, dem, demA))
    h.append("<h3>台地面のモデル — 水平面か、東上がりの面か</h3>")
    h.append(plateau_model_table(d, geo))
    h.append("</div>")

    # 裁定図(P-1)
    S = sai(d)
    FIGREF["saitei"] = KAN[n[0]]          # ⛔ 図版番号は手で数えない(pending の参照に使う)
    plate(h, nx(), "裁定図(P-1)　%s" % S["title"],
          "① どこ ② 現況 ③ 三案 同一縮尺 ④ 断面の対比 ⑤ 変わる数値 ⑥ 推奨")
    h.append('<div class="box"><p>⛔ <b>これは裁定を仰ぐための図で、指図方は案を選んでいない。</b>'
             'CLAUDE.md 規則16 の6点セット(どこ / 背景 / 選択肢 A・B・C / 推奨 / 影響 / 裁定図)を'
             'この一節で満たす。<b>裁定が下りるまで「未解決 P-1」は未解決のまま</b>で、'
             '本文も実装も動かさない。⛔ <b>埋没・合格数・崖の比高と勾配・区画線の段は'
             '<code>niwa_sakyo_dem.json</code> と <code>niwa_sakyo_edo_world.json</code> から'
             '毎回算出している</b>(規則4)。'
             '<br>⭐ <b>三案とも棟は1棟も動かない。動くのは地盤だけ</b>である — '
             '従前の三案は現況DEM を起点に「棟をどこへ寄せるか」を問うていたが、'
             '<b>その現況DEM が江戸の地面ではなかった</b>ので、問いそのものを'
             '<b>「地盤をどの面に置くか」</b>へ立て直した(前の節)。'
             '<br>⛔ <b>「骨格(①②)だけに留める中間案」は計算した結果 図として成立しないので'
             '入れていない</b> — 理由と数値は前の節の「復元の手順と当てはまり」の ④⑤ の行が持つ。'
             '<br>⭐ <b>A/B/C は <code>niwa_sakyo_kosho.md</code> の 案(a)(b)(c) と対応する</b> — '
             '対応は見出しと表の「案」の列に併記した(<b>%s</b> ／ <b>%s</b> ／ <b>%s</b>)。</p></div>'
             % (sai_gian(sai_opt(d, "A")), sai_gian(sai_opt(d, "B")), sai_gian(sai_opt(d, "C"))))
    fig(h, sai_key_svg(d, geo, dem, KAN[n[0] - 1]),
        legend=dem_legend(),
        cap="<b>① どこの話か。</b>濃い枠と名札を付けた3棟(表御殿・奥御殿・土蔵三)が"
            "現況で特に深く埋まっている駒で、朱の破線が③の切り取り範囲。"
            "<b>② いま何がどうなっているか</b>を右に実測で並べた — 順位は埋没の深い順。"
            "<br>⚠ <b>朱の斜線は現況の人工の平場</b>で、"
            "前の節の三区分では<b>近代の掘削</b>にあたる区域である。"
            "表御殿・奥御殿はその底に据えられていて、東の台地との間を急な段が落ちる — "
            "<b>その落差がそのまま現況の埋没の量になっている</b>。"
            "<br>⭐ <b>A案・B案はこの区域を明治16年の谷底へ戻す</b>ので、"
            "埋没は棟を動かさずに解消する(③④の図)。")
    fig(h, sai_plan_svg(d, geo, dem, KAN[n[0] - 1]),
        legend='<span style="color:var(--hei)">■ 築地塀(三案とも動かない)</span>'
               '<span style="color:var(--nagaya)">■ 盲長屋(同)</span>'
               '<span style="color:var(--shu)">● 表門(同)</span>'
               + _sw("var(--cut4)") + "埋没 3m 超</span>"
               + _sw("var(--cut2)") + "0.5〜3m</span>"
               + _sw("var(--nomove)") + "0.5m 以下(規則3 合格)</span>"
               + '<span style="color:var(--dim)">┄ 行き先未決</span>'
               '<span style="color:var(--dim)">┄ 崖の法尻 / 法肩(折れ線)</span>',
        cap="<b>③ 三案を同じ縮尺・同じ範囲で並べた。</b>案ごとに別の図にすると差が読めないので"
            "並べてある(CLAUDE.md 2026-08-30)。"
            "<b>棟も外周も表門も三案とも一切動かない — 違いはすべて地盤の段彩に出ている。</b>"
            "<br>⚠ <b>A案・B案では復元した崖の面に載る駒</b>を破線と「?」で示した"
            "(⛔ どの駒かは<b>崖の折れ線に当てて毎回測る</b> — 手で並べない)。"
            "行き先は配置の判断なので<b>指図方は決めていない</b> — "
            "制約(外形が法肩の折れ線より台地側)だけを⑤の表に出してある。"
            "<br>⚠ <b>崖は折れ線</b>(北=WNW–ESE の斜め → 東西)なので、"
            "<b>破線は縦一直線ではない</b>。"
            "<br>⭐ <b>A案とB案の違いは台地面の高さだけ</b>で、"
            "谷底と崖は同じ錨・同じ手順である。")
    fig(h, sai_sec_svg(d, geo, dem, KAN[n[0] - 1]),
        cap="<b>④ 断面の対比。</b>埋没は平面図では読めない — <b>何メートル地中に入っているかは断面でしか"
            "分からない</b>ので、<b>同じ切り位置(z=839)を三案の面で切って</b>上下に並べた。"
            "<br>⛔ <b>棟は三案とも動かないので、段どうしの違いはすべて地盤の違いである。</b>"
            "<b>z=839 は表門・表御殿・崖・谷底・西の通りを一本で切る唯一の位置</b>で、"
            "三段すべてに表門が写る。"
            "<br>⚠ <b>四段目だけ切り位置が違う</b> — 土蔵三棟は"
            "西へ 8 m・南へ 6 m ずつ斜めに並ぶので東西にも南北にも串刺しにできず、"
            "三棟の中心を通る斜の線で切って<b>復元した崖の法肩から法尻まで</b>通してある。"
            "⭐ この線は訂正した崖(WNW–ESE)と<b>ほぼ直交する</b>ので、崖の姿がそのまま出る。")
    h.append("<h3>⑤ 案ごとに何がどれだけ変わるか</h3>")
    h.append(sai_case_table(d, geo, dem))
    h.append('<p class="cap">「最大の埋没」は、その案でのすべての駒(棟・付属屋・表門)の埋没の最大。'
             '<b>行き先未決の駒(復元した崖の面に載るもの)は分母からも最大値からも外してある</b>。'
             '<br>⛔ <b>建蔽率はここでは出さない</b> — 三案とも棟を動かさないので'
             '建築面積は変わらず、分母(敷地全体)も変わらないからである(次節の「建蔽率」が持つ)。'
             '<br>⚠ <b>「区画線の段」は摺り付けていない量そのもの</b>で、'
             '<b>隣家がまだ近代の掘削・盛土を履いている</b>ことを表す。'
             '⛔ 丹羽側から隣家の地盤を持ち上げて隠さない(2026-08-24 に岡部が越境した前例)。</p>')
    h.append("<h3>外形の重なり</h3>")
    h.append(sai_overlap_table(d, geo, dem))
    h.append('<p class="cap">⭕ <b>三案とも棟を動かさないので、重なりは現況のままである</b> — '
             '長屋どうしの軒の重なりは機械検査と同じ除外規約で外してある(未解決 P-4 が別に見る)。</p>')
    h.append("<h3>駒ごとの内訳(A案 / B案 / C案)</h3>")
    h.append(sai_body_table(d, geo, dem))
    h.append('<p class="cap">⛔ <b>「下の起伏」を必ず併記する</b> — '
             '台地を<b>水平面</b>で復元しているので、台地の上では起伏が 0.00 m になり、'
             '<b>埋没は沈め代(<code>const.sink</code>)そのもの</b>になる。'
             'つまり<b>台地の上の「規則3 合格」は恒真に近く、独立した検査ではない</b>。'
             '岡部が 2026-08-25 に同じ性質を <code>okabe_edo_recon.json</code> に明記している。'
             '<br>⚠ <b>表門は区画線をまたぐ</b>ので、復元する案では区画の中(復元面)と'
             '外(現況)の両方を踏む — <b>その段差が門の埋没に出る</b>(未解決 P-7 と同じ根)。</p>')
    h.append(sai_prose(d, dem))
    h.append("</div>")

    # 建蔽率
    plate(h, nx(), "建蔽率", "分母 = 敷地全体(CLAUDE.md 規則6)")
    kt, kp = kenpei(d, geo, area)
    h.append(kt)
    h.append('<p class="cap">⛔ <b>分母は敷地全体のみ</b>。可建地・平坦地ベースの数字は作らない。'
             '建築面積は<b>屋根の水平投影</b>(在庫部材の外形 bbox)で数えている。'
             '⚠ <b>外周の盲長屋の面積は 鎖の実延長 × <code>const.nagayaD</code></b> で、'
             'その奥行は<b>部材の実寸</b>(knagaya01l/r の Z=2.39 × ES)から採る — '
             '家臣長屋の <code>d</code> と同じ数字であって、丸めた値ではない。'
             '<br>⚠ <b>%.1f %% は上屋敷として低い。</b>'
             '⭐ <b>原因は屋敷が疎だったことではなく、この指図が棟を取りこぼしていることにある</b>。'
             '丹羽家自身の地震御届【S】は<b>壊れた数だけで当図の棟数を上回り</b>'
             '(家中長屋・土蔵)、<b>厩・釜屋・馬見所・物置・石垣は種別ごと当図に無い</b>。'
             '⛔ <b>御届の数は「壊れた数」なので、各項は在った数の下限である</b> — '
             '数と当図との対照は<b>%s</b>「御届が伝える屋敷の中身」の表が持つ(未解決 P-25)。'
             '⛔ <b>だからといって数字を上げるために棟を足さない</b> — '
             'どこへ置くかは配置の大改訂でユーザー裁定である。'
             'あわせて<b>御殿が連続複合になっていない</b>(未解決 P-9)ことも効く — '
             'スキル §B-3「建蔽率は目標値でなく正しいレイアウトの結果」。</p>'
             % (kp, figtok("todoke")))
    h.append('<div class="tw"><table><thead><tr><th>比べる相手</th><th>値</th>'
             '<th class="note">典拠</th></tr></thead><tbody>'
             '<tr><td>当図(敷地全体ベース)</td><td><b>%.2f %%</b></td>'
             '<td class="note">【P 算出】</td></tr>'
             '<tr><td>大名上屋敷の史料値</td><td><b>%d〜%d %%</b></td>'
             '<td class="note">%s【%s】<code>estate-types.md</code>'
             '「建蔽率の史料値」。⚠ <b>大名上屋敷の史料値はこの一点しかない</b></td></tr>'
             '<tr><td><b>当図 ÷ 史料値の中央</b></td><td><b>約 1 / %.0f</b></td>'
             '<td class="note">⛔ <b>桁(10倍)ではないが、値の欄のとおり桁に近い開きがある。</b>'
             '数字を上げるために棟を足さない'
             '(スキル §B-3)。⭐ <b>この差は「取りこぼした棟」で説明がつく</b> — '
             '御届【S】の棟数と当図の棟数の対照は<b>未解決 P-25</b> の表が持つ</td></tr>'
             '</tbody></table></div>'
             '<p class="cap">⛔ <b>比べる相手を図に置く</b>(2026-09-01 検図 K11)— '
             '数字だけでは「低い」が読み手に伝わらない。'
             '⚠ 史料値は<b>目測</b>【B】で、当図の算出(部材の bbox の総和)とは測り方が違う。'
             '⛔ それでも<b>分母を可建地に替えて差を縮めない</b>(規則6)。</p>'
             % (kp, d["norm"]["kenpeiBand"][0], d["norm"]["kenpeiBand"][1],
                html.escape(d["norm"]["kenpeiSrc"]), d["norm"]["kenpeiAcc"],
                (sum(d["norm"]["kenpeiBand"]) / 2.0) / max(kp, 1e-6)))
    h.append("</div>")

    # 部材
    plate(h, nx(), "部材", "在庫はすべて EdoAssets.cs の定数で解決済み ／ 新造なし")
    h.append(bom_table(d, geo))
    h.append('<p class="cap">⛔ <b>パスの literal を新規に書かない</b>(CLAUDE.md 規則12)— '
             '実装は必ず <code>EdoAssets</code> の定数を通す。'
             '⚠ <b>御殿4棟は Japanese Village Kit の一軒家プレハブの代用</b>で、'
             '廊下から壁が見える(memory <code>goten-asset-blender-todo</code>)。未解決 P-9。</p>')
    h.append("</div>")

    # 庭
    FIGREF["niwa"] = KAN[n[0]]
    plate(h, nx(), "庭", "⛔ 庭方の検分は不合格(2026-09-01) ／ 図は0枚 ／ 池は未再現")
    pl = d["planting"]
    h.append('<div class="box"><p><b>池は掘っていない。</b>都埋文258 の発掘で池跡は確認されている'
             '【S 記載事項に限る】が、<b>位置も形状も不明</b>【?】なので推定で掘らない(CLAUDE.md 規則7)。'
             '庭は seed=%d で <b>%d 本</b>の松・低木を撒いたもので、区画の縁 %.1f m 以内と'
             '建屋の外形 +%.1f m を避ける。松の比率 %.0f %%。'
             '⛔ 自作の低ポリゴンの木は使っていない(規則10)— 在庫のパックから採っている。'
             '<br>⚠ <b>これは「見る場所(入側)とセットになった庭」ではなく、空地に木を撒いたもの</b>である。'
             '庭として成立しているかは <code>edo-niwashi</code> の検分に回すこと。</p></div>'
             % (pl["seed"], pl["count"], pl["edgeClear"], pl["buildClear"], pl["pineRatio"] * 100))
    h.append('<div class="box"><p>⛔ <b>庭方(<code>edo-niwashi</code>)の検分は 2026-09-01 に'
             '<b>不合格</b>である。</b>指摘は<b>未解決へ立てるところまで</b>を反映してあり、'
             '<b>庭そのものの設計はしていない</b> — 見所・園路・築山・池・石組・植栽の層は'
             '<b>作庭の意匠</b>で、CLAUDE.md 規則17 のとおり'
             '<b>庭方が設計してから指図方が数値へ書き起こす</b>順序になる。'
             '<br>立っている未解決: %s。'
             '<br>⚠ <b>この節に図は1枚も無い</b>(未解決 %s)。庭園図・園路図・'
             '主視点からの視野図・水の縦断の4面が要る — <b>図の無い庭は検図できない。</b>'
             '<br>⭐ 1本あたりの受け持ちは <b>%s m²</b>(敷地 ÷ 本数)= 一辺 <b>%.1f m</b> の'
             '正方形に1本にあたる。⚠ <b>層は主木と低木の2層だけ</b>で、中木も下草も落葉樹も無い。</p></div>'
             % ("・".join("<b>%s</b>(%s)" % (q["id"], html.escape(q["title"].split(" — ")[0]))
                          for q in d["pending"] if q.get("fig") == "niwa"),
                "・".join(q["id"] for q in d["pending"]
                          if q.get("fig") == "niwa" and "図が1枚も無い" in q["title"]),
                "{:,.0f}".format(area / max(pl["count"], 1)),
                math.sqrt(area / max(pl["count"], 1))))
    h.append("</div>")

    # 隣家
    plate(h, nx(), "隣家との取り合い", "囲いを誰が受け持つか")
    h.append(neighbors_table(d, geo))
    h.append("</div>")

    # Stage
    plate(h, nx(), "実装の順序",
          "⛔ 流し直し不可(未解決 P-19) ／ 建っているのは 2026-08-11 の版")
    h.append('<div class="box"><p>⛔ <b>いま Stage4 を流し直してはならない。</b>'
             '<code>EdoSannoBukeBuilder.Stage4_Niwa</code> は<b>辺の役を辺 index の literal で'
             '決めている</b>が、区画は <code>EdoParcels.Get</code> で<b>新しい9頂点</b>を読む — '
             '<b>旧8辺の番号のまま新9辺に当たり、9辺のうち役が一致するのは3本だけ</b>になる。'
             '<b>門本体は区画の内部へ 147.2 m 移り、塀の開口だけが北辺(山王坂)に開く</b> — '
             '⛔ <b>症状の内訳と直し方は未解決 P-19 が持つ</b>(同じ説明をここに書き写さない)。'
             '<br>⭕ 下の表の辺番号は<b>新9辺</b>で書いてある(=あるべき姿)。'
             '実装をそこへ合わせるときは、<b>辺の役を番号ではなく幾何で引く</b>こと。</p></div>')
    h.append(stages_table(d))
    h.append('<p class="cap">⛔ <b>Stage 全体が一発のガードで SKIP する</b> — '
             '途中で例外が出ると半端に建った状態のまま二度と走らない(未解決 P-10)。'
             '<br>⭕ <b>造成をしないので地形のバックアップは要らない</b>(地形を一切触らない)。</p>')
    h.append("</div>")

    # 機械検査
    bad, skipped, nrect = checks(d, geo, dem)
    plate(h, nx(), "機械検査", "%d 件が落ちる ／ %d 矩形 %d 組の総当たり ／ 図を出す前に必ず回す"
          % (len(bad), nrect, nrect * (nrect - 1) // 2))
    h.append(checks_table(bad, skipped, nrect))
    h.append('<p class="cap">⛔ <b>目視では必ず見落とすので、外形の重なり・区画からの出入り・'
             '規則3の埋没・鎖のはみ出し・取り合いの規約を機械で検めてから図を出す</b>'
             '(sashizu.md §4)。<b>落ちた項目はすべて「未解決」に立ててある</b> — '
             'この検査に通っていないものが図に残っているのは、'
             '<b>直すのが設計の判断だから</b>であって、見落としているからではない。</p>')
    h.append("</div>")

    # 御届が伝える屋敷の中身(確度Sの一次史料 vs 当図)
    FIGREF["todoke"] = KAN[n[0]]
    plate(h, nx(), "御届が伝える屋敷の中身",
          "確度%s(%s)の一次史料【%s】 ／ 当図の数は図から数える"
          % (d["todoke"]["acc"], d["todoke"]["accNote"], d["todoke"]["src"]))
    h.append('<div class="box"><p>%s</p></div>' % inline(d["todoke"]["_"]))
    h.append(todoke_table(d, geo))
    # ⛔ **柱書を三重に持たない**(規則4・2026-09-01 考証 Ko-I)。
    #    読み方(下限としてしか使えないこと・向き・位置は書かれていないこと)は
    #    上の枠 = json `todoke._` が正で、ここでは参照だけにする。
    h.append('<p class="cap">⛔ <b>読み方は上の枠が正</b>(数は「壊れた数」= 在った数の下限 ／ '
             '使ってよい向きは「当図はこの下限に届いていない」だけ ／ '
             'どこに在ったかは書かれていない)。<b>同じ説明をここに書き写さない。</b>'
             '未解決 P-25。</p>')
    h.append("</div>")

    # 未解決
    plate(h, nx(), "未解決", "%d 件(高 %d / 中 %d / 低 %d)"
          % (len(d["pending"]), sum(1 for p in d["pending"] if p["pri"] == "高"),
             sum(1 for p in d["pending"] if p["pri"] == "中"),
             sum(1 for p in d["pending"] if p["pri"] == "低")))
    h.append(pending_table(d))
    h.append('<p class="cap">⛔ <b>ここに立っているものは、書き起こしの過程で見つけた現況の不整合で、'
             '直していない。</b>直すのは設計の判断(配置・史料解釈・意匠)で、'
             '指図方の領分ではない — <b>本文脈とユーザーの裁定に回す</b>。</p>')
    h.append("</div>")

    # 考証
    FIGREF["kosho"] = KAN[n[0]]
    plate(h, nx(), "考証", "典拠と確度 ／ 正典は niwa_sakyo_kosho.md")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, nx(), "履歴", "経緯は git log が持つ(指図の本文には残さない)")
    h.append(history())
    h.append("</div>")

    h.append('<div class="foot">図版 %d 面。'
             '数値の正典 <code>docs/Sashizu/niwa_sakyo_sashizu.json</code> ／ '
             '文章 <code>docs/Sashizu/niwa_sakyo_kosho.md</code> ／ '
             '地盤 <code>docs/Sashizu/niwa_sakyo_dem.json</code> ／ '
             '生成器 <code>Tools/Sashizu/build_niwa_sakyo_sashizu.py</code>。'
             'この頁は生成物なので直接編集しない。</div>' % _SVN[0])
    h.append("</div>")
    # ⛔ **必須8図の充足表を冒頭へ差し込む**(図版番号が要るのでここで組む)。
    hz = []
    plate(hz, "図", "必須の図が揃っているか", "sashizu.md §3 の8図 ／ 欠図は理由まで書く")
    hz.append(zumen_table(len(d["sections"])))
    hz.append("</div>")
    h[ZPLACE] = "\n".join(hz)
    body = "\n".join(h)
    # ⭐ 前方参照の札(figtok)を実際の図版番号へ置き換える。残ったら落とす。
    body = re.sub(r"@@FIG:([a-zA-Z0-9_]+)@@",
                  lambda m: FIGREF.get(m.group(1)) or "@@MISSING:%s@@" % m.group(1), body)
    if "@@" in body:
        raise SystemExit("⛔ 図版番号の札が解決できない: %s"
                         % re.findall(r"@@[^@]+@@", body)[:5])
    # ⛔ **組み上がった html に `**` が残っていないかを検める**(2026-09-01 検図 Kz-1)。
    #    偶奇(check_emphasis)は釣り合っていても、`inline()` を通し忘れた欄は
    #    `**` が生のまま図・表に出る。偶奇検査では原理的に捕まらないので別に数える。
    rawem = check_raw_emphasis(body)
    # ⛔ **宙吊りの未解決参照を捕まえる**(2026-09-01 検図 Kz-3。前回は P-17 で同型)。
    #    pending から件を落としたのに、本文の「未解決 P-◯◯」が残ると読み手が追えない。
    have = set(p["id"] for p in d["pending"])
    dang = sorted(set(re.findall(r"P-\d+", body)) - have)
    open(OUT, "w", encoding="utf-8").write(body)
    over = check_text_overflow(body)
    print("組んだ: %s" % os.path.relpath(OUT, ROOT))
    if embad:
        print("  ⛔ 強調 `**` の偶奇が合わない %d 件" % len(embad))
        for q in embad:
            print("    ⛔ %s" % q)
    else:
        print("  ⭕ 強調 `**` の偶奇 0 件")
    if rawem:
        print("  ⛔ 組み上がった html に `**` が生で残る %d 件" % len(rawem))
        for q in rawem[:20]:
            print("    ⛔ %s" % q)
    else:
        print("  ⭕ html に残る生の `**` 0 件")
    if dang:
        print("  ⛔ pending に無い未解決参照 %d 件: %s" % (len(dang), "・".join(dang)))
    else:
        print("  ⭕ 宙吊りの未解決参照 0 件")
    if over:
        print("  ⛔ 図の文字が枠からはみ出す %d 件" % len(over))
        for q in over[:20]:
            print("    ⛔ %s" % q)
    else:
        print("  ⭕ 図の文字のはみ出し 0 件(全 %d 個のテキストを実測)" % TEXTN[0])
    print("  図版 %d 面 / 節 %d / 敷地 %.0f m² (%.0f 坪) / 建蔽率 %.1f%%"
          % (_SVN[0], n[0], area, area / TSUBO, kp))
    print("  未解決 %d 件(高 %d / 中 %d / 低 %d) / 機械検査 %d 件が落ちる"
          % (len(d["pending"]), sum(1 for p in d["pending"] if p["pri"] == "高"),
             sum(1 for p in d["pending"] if p["pri"] == "中"),
             sum(1 for p in d["pending"] if p["pri"] == "低"), len(bad)))
    for b in bad:
        print("    ⛔ %s" % b)


if __name__ == "__main__":
    main()
