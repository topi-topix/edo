#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内藤紀伊守中屋敷の裁定図を組む。

**案の定義は `docs/Sashizu/naito_kii_saitei.json` が持つ(人が書く)。**
面積・内寄せ量・動く頂点・波及はこの生成器が `parcels.json` と `naito_kii_dem.json` から
実測して出す。⛔ 数値を json や html へ手で書き写さないこと。

    python3 Tools/Sashizu/build_naito_kii_saitei.py
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs", "Sashizu")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DOC, "naito_kii_saitei.html")

TSUBO = 3.305785          # 1坪 = m²
PARCEL = "sannobuke_naito"

# 段彩は地図の記号なので明暗テーマに関わらず固定(sashizu.md §3a)。
# 低=水際の湿った低地(青緑) → 高=台地(温かい黄土)。8段。
BAND = [
    (0.0, "#BFD3D0"), (10.0, "#CBDCCE"), (13.0, "#D8E2C9"), (16.0, "#E3E4C2"),
    (19.0, "#EBE1B6"), (22.0, "#EBD8A8"), (25.0, "#E5C994"), (28.0, "#DCB77F"),
]
NEI = {                    # 内藤の辺 → 隣家(共有辺は端点まで一致することを検査済み)
    10: ("sannobuke_kyogoku", "京極備中守 上屋敷"),
    11: ("sannobuke_niwa", "丹羽左京大夫 上屋敷"),
    12: ("sannobuke_shanin", "山王社 社人八家"),
}


# ---------- 幾何 ----------

def area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def signed(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2


def inward(pts, i, sgn):
    a, b = pts[i], pts[(i + 1) % len(pts)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    return (-dy / L * sgn, dx / L * sgn)


def offset(pts, idxs, dist, sgn):
    """idxs の辺だけ内向きに dist 平行移動し、頂点を隣り合う辺の交点で取り直す。"""
    n = len(pts)
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        nx, ny = inward(pts, i, sgn)
        s = dist if i in idxs else 0.0
        lines.append(((a[0] + nx * s, a[1] + ny * s), (b[0] + nx * s, b[1] + ny * s)))
    out = []
    for i in range(n):
        (p1, p2), (p3, p4) = lines[(i - 1) % n], lines[i]
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            out.append(pts[i])
            continue
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den
        out.append((px, py))
    return out


def simple(pts):
    """自己交差していないか。平行移動した辺の交点で頂点を取り直すと破綻することがある。"""
    n = len(pts)

    def seg(a, b, c, d):
        def cr(o, p, q):
            return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
        d1, d2 = cr(c, d, a), cr(c, d, b)
        d3, d4 = cr(a, b, c), cr(a, b, d)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    for i in range(n):
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue
            if seg(pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n]):
                return False
    return True


def solve(pts, idxs, target, sgn):
    """内寄せ量を解く。⚠ 面積は距離に対して単調でない(浅い折れ角では平行移動した辺の
    交点が滑って多角形が破綻し |面積| が増えに転じる)。**まず刻んで括り、それから二分する。**"""
    if not idxs:
        return 0.0, list(pts), True
    step, lo, hi = 0.25, 0.0, None
    d = step
    while d <= 300.0:
        p = offset(pts, idxs, d, sgn)
        if not simple(p):
            break
        if area(p) <= target:
            hi = d
            break
        lo = d
        d += step
    if hi is None:                      # 括れない = この辺の組では記録の坪数に到達しない
        p = offset(pts, idxs, lo, sgn)
        return lo, p, False
    for _ in range(60):
        mid = (lo + hi) / 2
        p = offset(pts, idxs, mid, sgn)
        if not simple(p) or area(p) > target:
            lo = mid
        else:
            hi = mid
    p = offset(pts, idxs, hi, sgn)
    return hi, p, simple(p) and abs(area(p) - target) < 1.0


def pip(poly, x, z):
    n = len(poly)
    ins = False
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z):
            xi = x1 + (z - z1) * (x2 - x1) / (z2 - z1)
            if x < xi:
                ins = not ins
    return ins


# ---------- 図法 ----------

class Proj:
    """世界座標(x,z) → SVG px。z は北が上なので Y だけ反転する。"""

    def __init__(self, x0, x1, z0, z1, sc, pad):
        self.x0, self.z1, self.sc, self.pad = x0, z1, sc, pad
        self.W = (x1 - x0) * sc + pad * 2
        self.H = (z1 - z0) * sc + pad * 2

    def __call__(self, x, z):
        return (self.pad + (x - self.x0) * self.sc,
                self.pad + (self.z1 - z) * self.sc)

    def path(self, pts, close=True):
        d = "M" + " L".join("%.2f %.2f" % self(x, z) for x, z in pts)
        return d + (" Z" if close else "")


def band_of(v):
    c = BAND[0][1]
    for lo, col in BAND:
        if v >= lo:
            c = col
    return c


def dem_svg(P, dem, clip_id):
    """段彩を 4m セルで敷く(正本は 2m 刻みなので間引く)。"""
    x0, z0, st = dem["x0"], dem["z0"], dem["step"]
    h = dem["h"]
    step = st * 2
    out = []
    for jz in range(0, dem["nz"] - 1, 2):
        z = z0 + jz * st
        if not (P.z1 - P.H / P.sc <= z <= P.z1 + step):
            pass
        for ix in range(0, dem["nx"] - 1, 2):
            x = x0 + ix * st
            v = h[jz][ix]
            if v is None:
                continue
            px, py = P(x, z + step)
            if px < -step * P.sc or py < -step * P.sc or px > P.W or py > P.H:
                continue
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                       % (px, py, step * P.sc + .6, step * P.sc + .6, band_of(v)))
    return '<g clip-path="url(#%s)">%s</g>' % (clip_id, "".join(out))


def contours(P, dem, levels, clip_id):
    """marching squares で等高線を引く(線分の集合で十分)。"""
    x0, z0, st = dem["x0"], dem["z0"], dem["step"]
    h = dem["h"]
    segs = {lv: [] for lv in levels}
    for jz in range(dem["nz"] - 1):
        for ix in range(dem["nx"] - 1):
            a, b = h[jz][ix], h[jz][ix + 1]
            c, d = h[jz + 1][ix + 1], h[jz + 1][ix]
            if None in (a, b, c, d):
                continue
            X, Z = x0 + ix * st, z0 + jz * st
            corners = [(X, Z, a), (X + st, Z, b), (X + st, Z + st, c), (X, Z + st, d)]
            for lv in levels:
                pts = []
                for k in range(4):
                    px1, pz1, v1 = corners[k]
                    px2, pz2, v2 = corners[(k + 1) % 4]
                    if (v1 < lv) != (v2 < lv):
                        t = (lv - v1) / (v2 - v1)
                        pts.append((px1 + (px2 - px1) * t, pz1 + (pz2 - pz1) * t))
                if len(pts) == 2:
                    segs[lv].append(pts)
    out = []
    for lv in levels:
        if not segs[lv]:
            continue
        d = " ".join("M%.2f %.2f L%.2f %.2f" % (P(*s[0]) + P(*s[1])) for s in segs[lv])
        major = (lv % 5 == 0)
        out.append('<path d="%s" fill="none" stroke="#8A8270" stroke-width="%.2f" '
                   'stroke-opacity="%.2f"/>' % (d, 1.0 if major else .5, .75 if major else .5))
    return '<g clip-path="url(#%s)">%s</g>' % (clip_id, "".join(out))


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def md(s):
    """json の本文の **強調** を <b> にする。json には生の HTML を書かない約束。"""
    out, bold = [], False
    for part in esc(s).split("**"):
        out.append(("<b>%s</b>" % part) if bold else part)
        bold = not bold
    return "".join(out)


# ---------- 図版 ----------

def plate_genkyo(d, sj, P, dem, na, nei, water):
    """其一 — 現況図。段彩・等高線・辺番号・隣家・溜池。"""
    g = ['<defs><clipPath id="cpA"><path d="%s"/></clipPath>' % P.path(na)
         + '<pattern id="hatchA" width="6" height="6" patternTransform="rotate(45)" '
           'patternUnits="userSpaceOnUse">'
           '<line x1="0" y1="0" x2="0" y2="6" stroke="#A8452C" stroke-width="1.4" '
           'stroke-opacity=".55"/></pattern></defs>']
    g.append('<rect x="0" y="0" width="%.0f" height="%.0f" fill="#FBFAF6"/>' % (P.W, P.H))
    # 溜池
    g.append('<path d="%s" fill="#A9C2CE" fill-opacity=".55" stroke="#6E8A98" '
             'stroke-width="1"/>' % P.path(water))
    # 隣家
    for i, (pid, label) in sorted(NEI.items()):
        g.append('<path d="%s" fill="#F0EDE2" stroke="#B9B2A0" stroke-width="1"/>'
                 % P.path(nei[pid]))
    g.append(dem_svg(P, dem, "cpA"))
    g.append(contours(P, dem, [lv for lv in range(8, 29)], "cpA"))
    g.append('<path d="%s" fill="none" stroke="#23201A" stroke-width="2.2"/>' % P.path(na))
    # 辺番号と、隣家/水際/隣地の別
    n = len(na)
    sgn = 1 if signed(na) > 0 else -1
    for i in range(n):
        a, b = na[i], na[(i + 1) % n]
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, nz = inward(na, i, sgn)
        px, py = P(mx - nx * 11, mz - nz * 11)
        g.append('<circle cx="%.1f" cy="%.1f" r="8.4" fill="#FBFAF6" stroke="#615C4E" '
                 'stroke-width=".8"/>' % (px, py))
        g.append('<text class="num" x="%.1f" y="%.1f" text-anchor="middle" '
                 'dominant-baseline="central" fill="#23201A">%d</text>' % (px, py, i))
    for i, (pid, label) in sorted(NEI.items()):
        c = nei[pid]
        cx = sum(p[0] for p in c) / len(c)
        cz = sum(p[1] for p in c) / len(c)
        px, py = P(cx, cz)
        px = min(max(px, 54), P.W - 54)
        py = min(max(py, 20), P.H - 12)
        g.append('<text class="anS2" x="%.1f" y="%.1f">%s</text>' % (px, py, esc(label)))
    # 注記
    def note(x, z, s, cls="anS2", dx=0, dy=0):
        px, py = P(x, z)
        g.append('<text class="%s" x="%.1f" y="%.1f">%s</text>'
                 % (cls, px + dx, py + dy, esc(s)))
    note(-215, 500, "溜　池", "zn")
    note(-150, 697, "表門はこの辺(9)に面する", "anG")
    # 東隣。⚠ 区画の東端から枠の東端まで 16m しかないので、右端に寄せて引き出し線で結ぶ。
    ex, ey = P.W - 12, 128
    ax, ay = P(-56.5, 610)
    g.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="#615C4E" stroke-width=".8" '
             'fill="none" stroke-dasharray="3 2"/>' % (ex - 96, ey + 6, ax + 3, ay))
    for k, (s, cls) in enumerate([("東隣＝松平(鶴之助)", "an2b"),
                                  ("五千五百石余 の屋敷地", "anS2"),
                                  ("【切絵図B】⛔ 街路ではない", "jo")]):
        g.append('<text class="%s" x="%.1f" y="%.1f" style="text-anchor:end">%s</text>'
                 % (cls, ex, ey - 26 + k * 13, esc(s)))
    cx = sum(p[0] for p in na) / len(na)
    cz = sum(p[1] for p in na) / len(na)
    px, py = P(cx, cz)
    g.append('<text class="big" x="%.1f" y="%.1f" text-anchor="middle">内藤紀伊守 中屋敷</text>'
             % (px, py - 6))
    g.append('<text class="anS2" x="%.1f" y="%.1f">%s</text>'
             % (px, py + 12, "現区画 %s m²（%s 坪）" % (fm(area(na), 1), fm(area(na) / TSUBO, 1))))
    # 方位と縮尺
    g.append(north(P.W - 40, 34))
    g.append(scalebar(P, 50, P.H - 22, 100))
    return "".join(g)


def plate_case(d, P, na, alt, idxs, nei, water, key, title):
    """案の小図。削られる範囲を朱の斜線で示し、変わった辺を朱で描く。"""
    cid = "cp%s" % key
    # ⚠ defs は SVG ごとに閉じている。網目は各図の中で定義し直すこと(他の SVG の id は引けない)。
    g = ['<defs><clipPath id="%s"><path d="%s"/></clipPath>'
         '<pattern id="hatch%s" width="6" height="6" patternTransform="rotate(45)" '
         'patternUnits="userSpaceOnUse">'
         '<line x1="0" y1="0" x2="0" y2="6" stroke="#A8452C" stroke-width="1.4" '
         'stroke-opacity=".55"/></pattern></defs>' % (cid, P.path(na), key)]
    g.append('<rect x="0" y="0" width="%.0f" height="%.0f" fill="#FBFAF6"/>' % (P.W, P.H))
    g.append('<path d="%s" fill="#A9C2CE" fill-opacity=".55" stroke="#6E8A98" '
             'stroke-width=".8"/>' % P.path(water))
    for pid, label in NEI.values():
        g.append('<path d="%s" fill="#F0EDE2" stroke="#C3BCAA" stroke-width=".8"/>'
                 % P.path(nei[pid]))
    # 現区画(薄) → 差分を朱網 → 案の区画(濃)
    g.append('<path d="%s" fill="#EDEADD" stroke="#B9B2A0" stroke-width="1" '
             'stroke-dasharray="4 3"/>' % P.path(na))
    if idxs:
        g.append('<path d="%s" fill="url(#hatch%s)" fill-rule="evenodd" stroke="none"/>'
                 % (P.path(na) + " " + P.path(alt), key))
    g.append('<path d="%s" fill="#F6F4EC" fill-opacity=".55" stroke="%s" stroke-width="2"/>'
             % (P.path(alt), "#A8452C" if idxs else "#23201A"))
    # 変わった辺を強調
    n = len(na)
    for i in idxs:
        a, b = alt[i], alt[(i + 1) % n]
        g.append('<path d="M%.2f %.2f L%.2f %.2f" stroke="#A8452C" stroke-width="3.4" '
                 'fill="none"/>' % (P(*a) + P(*b)))
    px, py = P(sum(p[0] for p in na) / n, sum(p[1] for p in na) / n)
    g.append('<text class="rmS" x="%.1f" y="%.1f">%s</text>' % (px, py, esc(title)))
    return "".join(g)


def hyps_key_html():
    """段彩の色見本。⚠ 図の中に置くと辺の番号と重なるので HTML の凡例に出す。"""
    vis = BAND[1:]
    cells = "".join(
        '<span style="display:inline-block;width:30px;height:10px;background:%s;'
        'border:.5px solid #B9B2A0"></span>' % col for _, col in vis)
    ticks = "".join('<span style="display:inline-block;width:30px;text-align:right;'
                    'font-size:10.5px">%d</span>' % lo for lo, _ in vis[1:])
    return ('<span style="display:inline-flex;flex-direction:column;gap:1px">'
            '<span style="display:flex">%s</span>'
            '<span style="display:flex;margin-left:15px">%s</span></span>' % (cells, ticks))


def north(cx, cy):
    return ('<g><path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f Z" fill="#23201A"/>'
            '<text class="jo" x="%.1f" y="%.1f" text-anchor="middle">北</text></g>'
            % (cx, cy - 15, cx - 5.5, cy + 4, cx + 5.5, cy + 4, cx, cy + 17))


def scalebar(P, x, y, m):
    w = m * P.sc
    return ('<g><rect x="%.1f" y="%.1f" width="%.1f" height="4" fill="#23201A"/>'
            '<rect x="%.1f" y="%.1f" width="%.1f" height="4" fill="#FBFAF6" stroke="#23201A" '
            'stroke-width=".7"/>'
            '<text class="jo" x="%.1f" y="%.1f">0</text>'
            '<text class="jo" x="%.1f" y="%.1f" text-anchor="end">%dm</text></g>'
            % (x, y, w / 2, x + w / 2, y, w / 2, x, y - 5, x + w, y - 5, m))


def fm(v, nd=0):
    return ("{:,.%df}" % nd).format(v)


# ---------- 組む ----------

def main():
    sj = json.load(open(os.path.join(DOC, "naito_kii_saitei.json"), encoding="utf-8"))
    par = {p["id"]: [tuple(q) for q in p["pts"]]
           for p in json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))["parcels"]
           if p.get("pts")}
    dem = json.load(open(os.path.join(DOC, sj["dem"]), encoding="utf-8"))
    na = par[sj["parcel"]]
    nei = {pid: par[pid] for pid, _ in NEI.values()}
    n = len(na)
    sgn = 1 if signed(na) > 0 else -1
    cur = area(na)
    rec_t = sj["datum"]["record_tsubo"]
    rec = rec_t * TSUBO

    # 溜池 — 南辺(辺2〜6)の外側。汀線は現区画の南辺に一致するという読み(確度S)。
    # 汀線=辺3〜6(切絵図で土手帯が入らず水面に直接接する・確度S)。辺0〜2 は西で御預明地が近い。
    south = [na[i] for i in range(3, 8)]
    water = south + [(south[-1][0] + 80, 470), (south[0][0] - 80, 470)]

    # 各案を解く
    cases = []
    for o in sj["options"]:
        idxs = set(o["edges"])
        dd, alt, ok = solve(na, idxs, rec, sgn)
        moved = [(i, math.hypot(alt[i][0] - na[i][0], alt[i][1] - na[i][1]))
                 for i in range(n)
                 if math.hypot(alt[i][0] - na[i][0], alt[i][1] - na[i][1]) > 0.01]
        shared_v = {10, 11, 12, 0}          # 共有辺 10/11/12 の端点
        gate_v = {9, 10}                    # 表門が面する辺9の端点
        cases.append(dict(o=o, d=dd, alt=alt, a=area(alt), moved=moved, ok=ok,
                          hits_shared=sorted(v for v, _ in moved if v in shared_v),
                          hits_gate=sorted(v for v, _ in moved if v in gate_v)))

    # 図法
    PA = Proj(-392, -38, 502, 700, 2.32, 26)
    PB = Proj(-388, -42, 508, 696, 0.86, 12)

    css = open(os.path.join(HERE, "sashizu.css"), encoding="utf-8").read()

    h = ['<meta charset="utf-8">',
         '<title>内藤紀伊守中屋敷 裁定図</title>',
         '<style>%s\n.cases{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:8px}'
         '\n.cases .fig{margin-top:0;padding:8px;overflow:visible}'
         # ⚠ sashizu.css の `.fig svg{min-width:560px}` は一枚図の前提。3案を横に並べる小図に
         #   効かせると各図が 560px に膨らんで横並びが壊れるので、ここだけ解除する。
         '\n.cases .fig svg{min-width:0}'
         '\n.opt{border:1px solid var(--rule);background:var(--paper2);padding:14px 16px;margin-top:14px}'
         '\n.opt h3{margin:0 0 6px}'
         '\n.opt .k{display:inline-block;min-width:1.5em;text-align:center;background:var(--shu);'
         'color:var(--paper);font-weight:700;padding:0 6px;margin-right:8px}'
         '\n.opt p{margin:6px 0 0;font-size:13.5px}'
         '\n.rec{border-color:var(--shu)}'
         '\n@media (max-width:900px){.cases{grid-template-columns:1fr}}'
         '</style>' % css,
         '<div class="wrap">',
         '<p class="eyebrow">%s ／ %s ／ %s ／ %s</p>'
         % tuple(esc(sj["datum"][k]) for k in ("year", "han", "koku", "yashiki")),
         '<h1>%s</h1>' % esc(sj["title"]),
         '<p class="lede"><b>%s</b></p>' % esc(sj["subtitle"]),
         '<p class="lede">%s</p>' % md(sj["lede"]),
         '<div class="box rec"><h3>⚠ 上屋敷ではなく中屋敷である</h3><p>%s</p></div>'
         % md(sj["datum"]["yashiki_note"]),
         ]

    # 其一
    h.append('<div class="plate"><div class="phead"><h2>其一　どこ — 敷地と隣家</h2>'
             '<span class="meta">現況 %s m²（%s 坪）／記録 %s 坪（%s m²）／差 <b>%+s 坪（%+.1f%%）</b></span>'
             '</div>' % (fm(cur, 1), fm(cur / TSUBO, 1), fm(rec_t, 2), fm(rec, 1),
                         fm((cur - rec) / TSUBO, 1), (cur - rec) / rec * 100))
    h.append('<div class="fig"><svg viewBox="0 0 %.0f %.0f" role="img" '
             'aria-label="内藤紀伊守中屋敷 現況の敷地と隣家">%s</svg></div>'
             % (PA.W, PA.H, plate_genkyo(sj, sj, PA, dem, na, nei, water)))
    h.append('<p class="cap">%s</p>' % esc(sj["where"]))
    h.append('<div class="legend"><span>丸数字＝辺の番号（0起点）</span>'
             '<span>等高線 1m 間隔・5m ごとに太線</span>'
             '<span>水色＝溜池</span><span>灰＝隣家</span></div>')
    h.append('<div class="legend"><span>段彩＝造成前の地盤'
             '（<code>naito_kii_dem.json</code>・海抜m）</span>%s</div>' % hyps_key_html())

    # 辺の表
    h.append('<h3>辺ごとの相手</h3><div class="tw"><table><tr>'
             '<th>辺</th><th>始点 (x, z)</th><th>終点 (x, z)</th><th>長さ m</th>'
             '<th class="note">相手</th></tr>')
    for i in range(n):
        a, b = na[i], na[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if i in NEI:
            who = "%s ／ 共有辺（端点まで一致・道なしの背中合わせ）" % NEI[i][1]
        elif i == 9:
            who = "街路（東の南北通りの行き止まり）／<b>表門はこの辺に面する</b>"
        elif i in (7, 8):
            who = "隣地「松平(鶴之助) 五千五百石余」【切絵図・確度B】⛔ 街路ではない"
        elif i in (3, 4, 5, 6):
            who = "溜池の水際（切絵図で土手帯が入らない・確度S）"
        else:
            who = "未同定（西・御預明地が近い）"
        h.append('<tr><td>%d</td><td>%.3f, %.3f</td><td>%.3f, %.3f</td><td>%.2f</td>'
                 '<td class="note">%s</td></tr>' % (i, a[0], a[1], b[0], b[1], L, who))
    h.append('</table></div></div>')

    # 其二 — 3案を同じ縮尺で
    h.append('<div class="plate"><div class="phead"><h2>其二　三案を同じ縮尺で並べる</h2>'
             '<span class="meta">いずれも記録の %s 坪ちょうどに合わせた場合／朱の網＝削られる範囲</span>'
             '</div><div class="cases">' % fm(rec_t, 2))
    for c in cases:
        o = c["o"]
        lab = "案%s　%s" % (o["key"], "現区画のまま" if not o["edges"]
                            else "内寄せ %.1f m" % c["d"])
        h.append('<div><div class="fig"><svg viewBox="0 0 %.0f %.0f" role="img" '
                 'aria-label="案%s">%s</svg></div>'
                 '<p class="cap"><b>案%s</b>　%s</p></div>'
                 % (PB.W, PB.H, o["key"],
                    plate_case(sj, PB, na, c["alt"], set(o["edges"]), nei, water, o["key"], lab),
                    o["key"], esc(o["title"])))
    h.append('</div>')

    # 数量の表
    h.append('<h3>案ごとに何がどれだけ変わるか</h3><div class="tw"><table><tr>'
             '<th>案</th><th class="note">動かす辺</th><th>内寄せ m</th><th>面積 m²</th>'
             '<th>坪</th><th>記録との差</th><th>動く頂点</th><th>最大移動 m</th>'
             '<th class="note">共有辺</th><th class="note">表門の辺9</th>'
             '<th class="note">記録の坪数に届くか</th></tr>')
    for c in cases:
        o = c["o"]
        if not o["edges"]:
            reach = "—（合わせない案）"
        elif c["ok"]:
            reach = "✔ 届く"
        else:
            reach = ("⛔ <b>届かない</b>（%.2fm で多角形が破綻し、"
                     "削れるのは %s 坪まで）" % (c["d"], fm((cur - c["a"]) / TSUBO, 0)))
        h.append('<tr><td><b>%s</b></td><td class="note">%s</td><td>%s</td><td>%s</td>'
                 '<td>%s</td><td>%s</td><td>%d / %d</td><td>%s</td>'
                 '<td class="note">%s</td><td class="note">%s</td>'
                 '<td class="note">%s</td></tr>'
                 % (o["key"],
                    "—（動かさない）" if not o["edges"]
                    else "辺 " + "・".join(str(i) for i in o["edges"]),
                    "—" if not o["edges"] else "%.2f" % c["d"],
                    fm(c["a"], 1), fm(c["a"] / TSUBO, 1),
                    "%+.1f 坪 (%+.1f%%)" % ((c["a"] - rec) / TSUBO, (c["a"] - rec) / rec * 100),
                    len(c["moved"]), n,
                    "—" if not c["moved"] else "%.1f" % max(m for _, m in c["moved"]),
                    "✔ 動かない" if not c["hits_shared"]
                    else "⛔ 頂点 " + "・".join(str(v) for v in c["hits_shared"]),
                    "✔ 動かない" if not c["hits_gate"]
                    else "⛔ 頂点 " + "・".join(str(v) for v in c["hits_gate"]) + " が動く",
                    reach))
    h.append('</table></div>')
    h.append('<p class="cap">⚠ 面積は内寄せ量に対して<b>単調ではない</b>。浅い折れ角では平行移動した'
             '辺の交点が滑って多角形が自己交差し、そこから先は |面積| が増えに転じる。'
             '生成器は 0.25m 刻みで括ってから二分し、自己交差を検査して止めている。</p>')

    # 案の中身
    for c in cases:
        o = c["o"]
        h.append('<div class="opt%s"><h3><span class="k">%s</span>%s</h3>'
                 '<p>%s</p><p><b>利</b>　%s</p><p><b>難</b>　%s</p></div>'
                 % (" rec" if o["key"] == sj["recommend"][3] else "", o["key"], esc(o["title"]),
                    md(o["gist"]), md(o["pro"]),
                    md(o["con"])))
    h.append('</div>')

    # 其三 — 推奨・影響・宿題
    h.append('<div class="plate"><div class="phead"><h2>其三　推奨と影響</h2></div>')
    h.append('<div class="box rec"><h3>推奨</h3><p>%s</p></div>'
             % md(sj["recommend"]))
    h.append('<div class="box"><h3>採ったときの影響</h3><p>%s</p></div>'
             % md(sj["impact"]))
    h.append('<div class="box"><h3>宿題 — 表門の形式</h3><p>%s</p></div>'
             % md(sj["pending2_mon"]))
    h.append('<div class="box"><h3>宿題 — 坪数の原典</h3><p>%s</p></div>'
             % md(sj["pending"]))
    h.append('<div class="box"><h3>典拠</h3><p>%s</p></div>'
             % esc(sj["datum"]["record_src"]))
    h.append('</div>')

    h.append('<div class="foot">この図の公開先 <a href="%s">%s</a><br>'
             % (sj["artifact"], sj["artifact"]))
    h.append('組んだ日 %s ／ 生成器 <code>Tools/Sashizu/build_naito_kii_saitei.py</code>'
             ' ／ 案の定義 <code>docs/Sashizu/naito_kii_saitei.json</code>'
             ' ／ 区画 <code>docs/Sashizu/parcels.json</code> の <code>%s</code>'
             ' ／ 地盤 <code>docs/Sashizu/%s</code>'
             '<br>⛔ 数値をこの文書へ手で書き足さないこと — 面積・内寄せ量・動く頂点はすべて生成器が実測して出す。'
             '</div>' % (sj["date"], sj["parcel"], sj["dem"]))
    h.append('</div>')

    open(OUT, "w", encoding="utf-8").write("\n".join(h))
    print("書いた: %s" % os.path.relpath(OUT, ROOT))
    print("  現況 %s m² (%s 坪) / 記録 %s 坪 (%s m²) / 差 %+.1f 坪 (%+.1f%%)"
          % (fm(cur, 1), fm(cur / TSUBO, 1), fm(rec_t, 2), fm(rec, 1),
             (cur - rec) / TSUBO, (cur - rec) / rec * 100))
    for c in cases:
        print("  案%s 内寄せ %6.2fm → %s m² (%s 坪) 動く頂点 %d/%d 共有辺%s 辺9%s"
              % (c["o"]["key"], c["d"], fm(c["a"], 1), fm(c["a"] / TSUBO, 1),
                 len(c["moved"]), n,
                 "✔" if not c["hits_shared"] else "⛔" + str(c["hits_shared"]),
                 "✔" if not c["hits_gate"] else "⛔" + str(c["hits_gate"])))


if __name__ == "__main__":
    main()
