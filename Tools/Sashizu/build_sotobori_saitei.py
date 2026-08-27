#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外堀の掘り直しで裁定を仰ぐ3件を、「どこが」「どう変わるか」の図にする。

    python3 Tools/Sashizu/build_sotobori_saitei.py --backups <TerrainBackups>

読むのは

    docs/Sashizu/sotobori_saitei.json  … 裁定の定義(案の中身。人が書く)
    docs/Sashizu/sotobori_sashizu.json … 指図の設計値(汀線・石垣・水位)
    TerrainBackups/…                   … 現況の地形(断面と数量の実測)

⚠ ここは**指図ではなく裁定の資料**。案の採否が決まったら、決まった案だけを
   sotobori_sashizu.json へ書き移し、この文書は「決まった」と記して畳む。
⛔ 実装(シーン・プレハブ・C#)は読まない。
"""
import argparse, html, json, math, os, subprocess
import sashizu_lib
from sashizu_lib import R, _SVN, Proj

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
OUT = os.path.join(DOC, "sotobori_saitei.html")
RAMP = [(1.0, "#2E6E8E"), (2.0, "#3A8398"), (3.0, "#4E9A9B"), (4.0, "#6BAC90"),
        (5.0, "#8ABC84"), (6.0, "#A9C87C"), (7.0, "#C6D07A"), (9.0, "#DCC776"), (99, "#E2B06C")]
COL = {"A": "#1F6F4A", "B": "#8A5A1F", "C": "#6E7A83"}


def col(y):
    for lim, c in RAMP:
        if y < lim:
            return c
    return RAMP[-1][1]


def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, html.escape(label)),
            '<defs><pattern id="wv%d" width="10" height="10" patternUnits="userSpaceOnUse">'
            '<path d="M0,7 q2.5,-3 5,0 t5,0" stroke="#4E7E95" stroke-width="0.8" fill="none" opacity="0.5"/>'
            '</pattern><clipPath id="cl%d"><rect x="0" y="0" width="%.0f" height="%.0f"/></clipPath></defs>'
            % (_SVN[0], _SVN[0], W, H), '<g clip-path="url(#cl%d)">' % _SVN[0]]


ENDSVG = "</g></svg>"


def wave():
    return "url(#wv%d)" % _SVN[0]


def load_terrain(b):
    import numpy as np
    g = os.path.join(b, "terrain_20260822_georef_fix")
    t = os.path.join(b, "tameike_20260826_recarve_pre")
    meta = json.load(open(os.path.join(g, "meta.json")))
    r = meta["R"]
    cur = np.fromfile(os.path.join(t, "heightmap_before.bin"), dtype="float32").reshape(r, r).astype(float)
    return meta, cur


def design_grid(d, b, box):
    """掘り直した後の設計面。⛔ ここで作法を発明しない — 指図の生成器
    (build_sotobori_dem.py)の design_surface をそのまま呼ぶ。box=(x0,x1,z0,z1)。"""
    import numpy as np
    import importlib.util
    sp_ = importlib.util.spec_from_file_location(
        "dem", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_sotobori_dem.py"))
    dem = importlib.util.module_from_spec(sp_)
    sp_.loader.exec_module(dem)
    T = dem.load_terrain(b)
    meta = T["meta"]
    px, pz, sp = meta["posX"], meta["posZ"], meta["spacing"]
    x0, x1, z0, z1 = box
    c0, r0 = int(round((x0 - px) / sp)), int(round((z0 - pz) / sp))
    nx = int((x1 - x0) / sp) + 1
    nz = int((z1 - z0) / sp) + 1
    X = x0 + np.arange(nx) * sp
    Z = z0 + np.arange(nz) * sp
    PX, PZ = np.meshgrid(X, Z)
    cut = lambda A: A[r0:r0 + nz, c0:c0 + nx]
    CUR, PRE = cut(T["cur"]), cut(T["pre"])
    bodies = d["water"]
    ins = np.zeros(PX.shape, bool)
    dist = np.full(PX.shape, 1e9)
    floor = np.zeros(PX.shape)
    for w in bodies:
        if not w.get("works"):
            continue
        m1 = dem.in_poly(np, PX, PZ, w["outline"])
        ins |= m1
        floor = np.where(m1, w["floor"], floor)
        dist = np.minimum(dist, dem.seg_dist(np, PX, PZ, w["outline"]))
    ko = np.zeros(PX.shape, bool)
    kw = d["works"].get("keepOut", {})
    for w in bodies:
        if w.get("works"):
            continue
        ko |= dem.in_poly(np, PX, PZ, w["outline"])
        ko |= dem.seg_dist(np, PX, PZ, w["outline"]) <= kw.get("otherWaterBank", 0.0)
    for q in kw.get("rects", []):
        r = q["rect"]
        ko |= (PX >= r[0]) & (PX <= r[1]) & (PZ >= r[2]) & (PZ <= r[3])
    ko &= ~ins
    COP = np.zeros(PX.shape)
    bdd = np.full(PX.shape, 1e9)
    byid = {w["id"]: w for w in bodies}
    for r in d["ishigaki"]["runs"]:
        if not byid[r["body"]].get("works"):
            continue
        a, b2 = r["p0"], r["p1"]
        dx, dz = b2[0] - a[0], b2[1] - a[1]
        l2 = dx * dx + dz * dz
        tt = np.clip(((PX - a[0]) * dx + (PZ - a[1]) * dz) / l2, 0, 1)
        dd = np.hypot(PX - (a[0] + tt * dx), PZ - (a[1] + tt * dz))
        cp = r["copingFrom"] + (r["copingTo"] - r["copingFrom"]) * tt
        sel = dd < bdd
        bdd = np.where(sel, dd, bdd)
        COP = np.where(sel, cp, COP)
    des, _ = dem.design_surface(np, d, CUR, PRE, ins, dist, floor, ko, COP, sp, PX, PZ)

    def s(x, z):
        fx, fz = (x - x0) / sp, (z - z0) / sp
        i = int(max(0, min(nx - 2, fx)))
        j = int(max(0, min(nz - 2, fz)))
        tx, tz = fx - i, fz - j
        return float(des[j, i] * (1 - tx) * (1 - tz) + des[j, i + 1] * tx * (1 - tz)
                     + des[j + 1, i] * (1 - tx) * tz + des[j + 1, i + 1] * tx * tz)
    return s


def make_sampler(meta, cur):
    px, pz, sp = meta["posX"], meta["posZ"], meta["spacing"]

    def s(x, z):
        fx, fz = (x - px) / sp, (z - pz) / sp
        i, j = int(fx), int(fz)
        tx, tz = fx - i, fz - j
        return float(cur[j, i] * (1 - tx) * (1 - tz) + cur[j, i + 1] * tx * (1 - tz)
                     + cur[j + 1, i] * (1 - tx) * tz + cur[j + 1, i + 1] * tx * tz)
    return s


def frame(d, body):
    """その水面の縦断の基準(郭外汀線)と法線。"""
    seg = [s for s in d["reach"]["segments"] if s["body"] == body][0]
    sw, ne = seg["sw"], seg["ne"]
    ln = math.hypot(sw[1][0] - sw[0][0], sw[1][1] - sw[0][1])
    u = ((sw[1][0] - sw[0][0]) / ln, (sw[1][1] - sw[0][1]) / ln)
    n = (-u[1], u[0])
    a, b = sw[0], sw[1]

    def side(p):
        dx, dz = b[0] - a[0], b[1] - a[1]
        return ((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / math.hypot(dx, dz)
    if side(ne[0]) * side((a[0] + n[0], a[1] + n[1])) < 0:
        n = (-n[0], -n[1])
    return sw, ne, u, n, ln


def width_at(p, n, ne):
    lo, hi = 0.0, 90.0
    a, b = ne
    f = lambda w: (((p[0] + w * n[0]) - a[0]) * (b[1] - a[1])
                   - ((p[1] + w * n[1]) - a[1]) * (b[0] - a[0])) / math.hypot(b[0] - a[0], b[1] - a[1])
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(60):
        m = (lo + hi) / 2
        if f(lo) * f(m) <= 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


def keymap_svg(d, it, W=1180.0):
    """全体の中でどこか。堀ぜんたいを小さく描き、当該箇所を朱で囲う。"""
    xs = [q[0] for w in d["water"] for q in w["outline"]]
    zs = [q[1] for w in d["water"] for q in w["outline"]]
    p = Proj(min(xs) - 30, max(xs) + 30, min(zs) - 30, max(zs) + 30, W=W, top=12, bottom=26)
    h = _sv(p.W, p.H, "位置")
    h.append(R(0, 0, p.W, p.H, fill="var(--paper)"))
    for w in d["water"]:
        dd = "M" + " L".join("%.1f,%.1f" % (p.X(x), p.Y(z)) for x, z in w["outline"]) + " Z"
        h.append('<path d="%s" fill="%s" stroke="#3F6F86" stroke-width="1"/>' % (dd, wave()))
        cx = sum(q[0] for q in w["outline"]) / len(w["outline"])
        cz = sum(q[1] for q in w["outline"]) / len(w["outline"])
        h.append('<text class="jo" x="%.1f" y="%.1f" style="text-anchor:middle">%s</text>'
                 % (p.X(cx), p.Y(cz) + 22, w["id"].replace("Sotobori_", "")))
    for r in d["ishigaki"]["runs"]:
        h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="var(--ishi)" stroke-width="1.6" opacity="0.8"/>'
                 % (p.X(r["p0"][0]), p.Y(r["p0"][1]), p.X(r["p1"][0]), p.Y(r["p1"][1])))
    k = it["keymap"]
    h.append(R(p.X(k[0]), p.Y(k[3]), p.L(k[1] - k[0]), p.L(k[3] - k[2]),
               fill="none", stroke="var(--shu)", sw=2.2))
    h.append('<text class="anG" x="%.1f" y="%.1f">%s ここ</text>'
             % (p.X(k[0]), p.Y(k[3]) - 7, it["id"]))
    h.append('<text class="sl" x="14" y="%.1f">溜池の堰 →</text>' % (p.H - 10))
    h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:end">← 幸橋方向</text>'
             % (p.W - 14, p.H - 10))
    h.append(ENDSVG)
    return "\n".join(h)


def zoom_svg(d, it, samp, W=1180.0):
    """拡大平面 — 現況の段彩・汀線・石垣・案が動かす線。"""
    k = it["keymap"]
    p = Proj(k[0], k[1], k[2], k[3], W=W, top=14, bottom=30)
    h = _sv(p.W, p.H, "拡大平面")
    h.append(R(0, 0, p.W, p.H, fill="var(--paper)"))
    st = 2.0
    s = p.L(st) + 0.5
    z = k[2]
    while z <= k[3]:
        x = k[0]
        while x <= k[1]:
            h.append(R(p.X(x) - s / 2, p.Y(z) - s / 2, s, s, fill=col(samp(x, z))))
            x += st
        z += st
    for w in d["water"]:
        dd = "M" + " L".join("%.1f,%.1f" % (p.X(x), p.Y(zz)) for x, zz in w["outline"]) + " Z"
        h.append('<path d="%s" fill="%s" stroke="#2C5D74" stroke-width="1.6"/>' % (dd, wave()))
    for r in d["ishigaki"]["runs"]:
        mark = r["body"] == it["body"] and it.get("side", "") in r["side"]
        h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="%s" stroke-width="%.1f" '
                 'stroke-linecap="round"/>'
                 % (p.X(r["p0"][0]), p.Y(r["p0"][1]), p.X(r["p1"][0]), p.Y(r["p1"][1]),
                    "var(--shu)" if mark else "var(--ishi)", 4.4 if mark else 2.4))
        if mark:
            mx = (r["p0"][0] + r["p1"][0]) / 2
            mz = (r["p0"][1] + r["p1"][1]) / 2
            h.append('<text class="anG" x="%.1f" y="%.1f">%s(%d個)</text>'
                     % (p.X(mx) + 8, p.Y(mz) - 6, r["line"], r["n"]))
    if it.get("notch"):
        dd = "M" + " L".join("%.1f,%.1f" % (p.X(x), p.Y(zz)) for x, zz in it["notch"])
        h.append('<path d="%s" stroke="%s" stroke-width="3" fill="none" stroke-dasharray="7 4"/>'
                 % (dd, COL["A"]))
        h.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="none" stroke="%s" stroke-width="2"/>'
                 % (p.X(it["notch"][1][0]), p.Y(it["notch"][1][1]), COL["A"]))
        h.append('<text class="anS" x="%.1f" y="%.1f" fill="%s">入隅の頂点</text>'
                 % (p.X(it["notch"][1][0]) + 8, p.Y(it["notch"][1][1]) + 14, COL["A"]))
    if it.get("sectionAt"):
        sa = it["sectionAt"]
        aa = math.radians(sa["yaw"])
        nn = (math.cos(aa + math.pi / 2), math.sin(aa + math.pi / 2))
        p0 = (sa["p"][0] + sa["tFrom"] * nn[0], sa["p"][1] + sa["tFrom"] * nn[1])
        p1 = (sa["p"][0] + sa["tTo"] * nn[0], sa["p"][1] + sa["tTo"] * nn[1])
        h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#7A2E1E" stroke-width="1.4" '
                 'stroke-dasharray="6 4"/>' % (p.X(p0[0]), p.Y(p0[1]), p.X(p1[0]), p.Y(p1[1])))
        h.append('<circle cx="%.1f" cy="%.1f" r="7" fill="var(--paper)" stroke="#7A2E1E" '
                 'stroke-width="1.4"/><text class="rmS" x="%.1f" y="%.1f" fill="#7A2E1E">左</text>'
                 % (p.X(p0[0]), p.Y(p0[1]), p.X(p0[0]), p.Y(p0[1]) + 4))
        h.append('<circle cx="%.1f" cy="%.1f" r="7" fill="var(--paper)" stroke="#7A2E1E" '
                 'stroke-width="1.4"/><text class="rmS" x="%.1f" y="%.1f" fill="#7A2E1E">右</text>'
                 % (p.X(p1[0]), p.Y(p1[1]), p.X(p1[0]), p.Y(p1[1]) + 4))
        h.append('<text class="sr" x="%.1f" y="%.1f">この線で切った断面が下の図。'
                 '丸の「左」が断面の左端、「右」が右端</text>'
                 % (p.X(p0[0]) + 12, p.Y(p0[1]) - 10))
    elif it.get("section"):
        sw, ne, u, n, ln = frame(d, it["body"])
        c = it["section"]["chainage"]
        q = (sw[0][0] + c * u[0], sw[0][1] + c * u[1])
        a = (q[0] + it["section"]["tFrom"] * n[0], q[1] + it["section"]["tFrom"] * n[1])
        b = (q[0] + it["section"]["tTo"] * n[0], q[1] + it["section"]["tTo"] * n[1])
        h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#7A2E1E" stroke-width="1.4" '
                 'stroke-dasharray="6 4"/>' % (p.X(a[0]), p.Y(a[1]), p.X(b[0]), p.Y(b[1])))
        h.append('<circle cx="%.1f" cy="%.1f" r="7" fill="var(--paper)" stroke="#7A2E1E" '
                 'stroke-width="1.4"/><text class="rmS" x="%.1f" y="%.1f" fill="#7A2E1E">左</text>'
                 % (p.X(a[0]), p.Y(a[1]), p.X(a[0]), p.Y(a[1]) + 4))
        h.append('<circle cx="%.1f" cy="%.1f" r="7" fill="var(--paper)" stroke="#7A2E1E" '
                 'stroke-width="1.4"/><text class="rmS" x="%.1f" y="%.1f" fill="#7A2E1E">右</text>'
                 % (p.X(b[0]), p.Y(b[1]), p.X(b[0]), p.Y(b[1]) + 4))
        h.append('<text class="sr" x="%.1f" y="%.1f">この線で切った断面が下の図。'
                 '丸の「左」が断面の左端、「右」が右端</text>'
                 % (p.X(a[0]) + 12, p.Y(a[1]) - 10))
    h.append('<path d="M%.1f,%.1f l0,-26 m-5,7 l5,-7 l5,7" stroke="var(--dim)" '
             'stroke-width="1.2" fill="none"/>'
             '<text class="anS2" x="%.1f" y="%.1f">北</text>'
             % (p.W - 30, p.H - 30, p.W - 30, p.H - 36))
    L = p.L(50)
    h.append('<path d="M14,%.1f h%.1f" stroke="var(--dim)" stroke-width="1.4"/>'
             '<text class="sl" x="%.1f" y="%.1f">50 m</text>' % (p.H - 12, L, 14 + L + 6, p.H - 9))
    h.append(ENDSVG)
    return "\n".join(h)


def sect_svg(d, it, samp, W=1180.0, dsamp=None):
    """断面 — 現況に各案を重ねる。

    通常は水面の縦断の基準(郭外汀線)に直角に切るが、入隅のように基準線が意味を持たない
    所は `sectionAt`(点と向きを直に指定)で切る。
    """
    if it.get("sectionAt"):
        sa = it["sectionAt"]
        q = tuple(sa["p"])
        a = math.radians(sa["yaw"])
        n = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
        sc = {"chainage": 0.0, "tFrom": sa["tFrom"], "tTo": sa["tTo"]}
        wd = 0.0
    else:
        sw, ne, u, n, ln = frame(d, it["body"])
        sc = it["section"]
        q = (sw[0][0] + sc["chainage"] * u[0], sw[0][1] + sc["chainage"] * u[1])
        wd = width_at(q, n, ne)
    body = [w for w in d["water"] if w["id"] == it["body"]][0]
    wy, fl = body["waterY"], body["floor"]
    ts = [sc["tFrom"] + i * 0.5 for i in range(int((sc["tTo"] - sc["tFrom"]) / 0.5) + 1)]
    g = [(t, samp(q[0] + t * n[0], q[1] + t * n[1])) for t in ts]
    gd = ([(t, dsamp(q[0] + t * n[0], q[1] + t * n[1])) for t in ts]
          if (dsamp and it.get("showDesign")) else None)
    lo = min(min(v for _, v in g), fl) - 1.0
    hi = max(max(v for _, v in g), 11.0) + 0.6
    H = 380.0
    h = _sv(W, H, "断面")
    h.append(R(0, 0, W, H, fill="var(--paper)"))
    x0, xw, y0, yh = 58.0, W - 92.0, H - 54, H - 96
    X = lambda t: x0 + (t - sc["tFrom"]) / (sc["tTo"] - sc["tFrom"]) * xw
    Y = lambda v: y0 - (v - lo) / (hi - lo) * yh
    for v in range(int(math.floor(lo)), int(math.ceil(hi)) + 1):
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="var(--rule)" stroke-width="0.5" opacity="0.8"/>'
                 % (x0 - 6, Y(v), x0 + xw))
        h.append('<text class="sl" x="16" y="%.1f">%d m</text>' % (Y(v) + 3, v))
    for t in range(int(sc["tFrom"]), int(sc["tTo"]) + 1, 5):
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="var(--rule)" stroke-width="0.4" opacity="0.6"/>'
                 % (X(t), Y(lo), Y(hi)))
        if t % 10 == 0:
            h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">%+d</text>'
                     % (X(t), y0 + 15, t))
    # 水 — sectionAt のときは「地盤が水面より下の所」を塗る
    if it.get("sectionAt"):
        run = []
        for t, v in (gd or g):
            if v < wy:
                run.append(t)
            elif run:
                h.append(R(X(run[0]), Y(wy), X(run[-1]) - X(run[0]), Y(fl) - Y(wy),
                           fill="#BBD3DF", op=0.85))
                run = []
        if run:
            h.append(R(X(run[0]), Y(wy), X(run[-1]) - X(run[0]), Y(fl) - Y(wy),
                       fill="#BBD3DF", op=0.85))
        a0, a1 = sc["tFrom"], sc["tTo"]
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="#3F6F86" stroke-width="1.8" '
                 'stroke-dasharray="6 3"/>' % (X(a0), Y(wy), X(a1)))
    else:
        a0, a1 = max(0.0, sc["tFrom"]), min(wd, sc["tTo"])
        h.append(R(X(a0), Y(wy), X(a1) - X(a0), Y(fl) - Y(wy), fill="#BBD3DF", op=0.85))
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="#3F6F86" stroke-width="1.8"/>'
                 % (X(a0), Y(wy), X(a1)))
    h.append('<text class="an2b" x="%.1f" y="%.1f">水面 %.2f</text>' % (X(a0) + 5, Y(wy) - 6, wy))
    h.append('<text class="sl" x="%.1f" y="%.1f">床 %.2f</text>' % (X(a0) + 5, Y(fl) + 13, fl))
    for t, lab in (() if it.get("sectionAt") else ((0.0, "いまの汀線"), (wd, "いまの汀線"))):
        if sc["tFrom"] <= t <= sc["tTo"]:
            h.append('<path d="M%.1f,%.1f V%.1f" stroke="#3F6F86" stroke-width="1" '
                     'stroke-dasharray="3 3"/>' % (X(t), Y(lo), Y(hi)))
            h.append('<text class="jo" x="%.1f" y="%.1f" style="text-anchor:middle">%s</text>'
                     % (X(t), Y(hi) + 11, lab))
    # 地盤 — showDesign のときは「掘った後」を主線、現況を破線にする
    if gd:
        h.append('<polyline points="%s" fill="none" stroke="var(--dim)" stroke-width="1.2" '
                 'stroke-dasharray="5 3"/>' % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in g))
        h.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="2.4"/>'
                 % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in gd))
    else:
        h.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="2.2"/>'
                 % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in g))
    # 石垣(いまの位置)
    nlab = [0]
    for r in d["ishigaki"]["runs"]:
        if r["body"] != it["body"] or it.get("side", "") not in r["side"]:
            continue
        # ⚠ その測点に**掛かっている** run だけ描く(掛かっていない折れを描くと嘘になる)
        a2, b2 = r["p0"], r["p1"]
        dx2, dz2 = b2[0] - a2[0], b2[1] - a2[1]
        l2 = dx2 * dx2 + dz2 * dz2
        tt = max(0.0, min(1.0, ((q[0] - a2[0]) * dx2 + (q[1] - a2[1]) * dz2) / l2))
        if math.hypot(q[0] - (a2[0] + tt * dx2), q[1] - (a2[1] + tt * dz2)) > 40:
            continue
        if it.get("sectionAt"):
            a3, b3 = r["p0"], r["p1"]
            dx3, dz3 = b3[0] - a3[0], b3[1] - a3[1]
            l3 = dx3 * dx3 + dz3 * dz3
            u3 = max(0.0, min(1.0, ((q[0] - a3[0]) * dx3 + (q[1] - a3[1]) * dz3) / l3))
            pj = (a3[0] + u3 * dx3, a3[1] + u3 * dz3)
            t = (pj[0] - q[0]) * n[0] + (pj[1] - q[1]) * n[1]
            if math.hypot(pj[0] - q[0] - t * n[0], pj[1] - q[1] - t * n[1]) > 6:
                continue
        else:
            off = r.get("offset", 4.81)
            t = -off if "郭外" in r["side"] else wd + off
        if not (sc["tFrom"] <= t <= sc["tTo"]):
            continue
        cp = (r["copingFrom"] + r["copingTo"]) / 2
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="var(--shu)" stroke-width="5" opacity="0.9"/>'
                 % (X(t), Y(cp), Y(r.get("base", 0.0))))
        h.append('<text class="anG" x="%.1f" y="%.1f" style="text-anchor:middle">'
                 'いまの %s 天端 %.2f</text>' % (X(t), Y(cp) - 8 - 13 * nlab[0], r["line"], cp))
        gh = (dsamp or samp)(q[0] + t * n[0], q[1] + t * n[1]) if it.get("showDesign") \
            else samp(q[0] + t * n[0], q[1] + t * n[1])
        if gh - cp > 0.3:
            h.append('<text class="anG" x="%.1f" y="%.1f" style="text-anchor:middle">'
                     '(地盤 %.2f = %.2fm 埋没)</text>' % (X(t), Y(cp) + 14, gh, gh - cp))
        elif cp - gh > 0.6:
            h.append('<text class="anG" x="%.1f" y="%.1f" style="text-anchor:middle">'
                     '%s の背後 %.2f = 天端より %.2fm 低い</text>'
                     % (X(t), Y(lo) + 24 + 14 * nlab[0], r["line"], gh, cp - gh))
        nlab[0] += 1
    # 案の「掘った後」— before/after
    for o in it["options"]:
        prof, tw, cp = after_profile(d, it, o, wd, q, n, samp, sc)
        if not prof:
            continue
        c = COL[o["key"]]
        poly = [(t, v, samp(q[0] + t * n[0], q[1] + t * n[1])) for t, v in prof]
        cut = [(X(t), Y(v), Y(gv)) for t, v, gv in poly if gv - v > 0.05]   # 削る
        fil = [(X(t), Y(v), Y(gv)) for t, v, gv in poly if v - gv > 0.05]   # 盛る
        for seq, col_ in ((cut, "var(--cut2)"), (fil, "var(--fill2)")):
            if len(seq) < 2:
                continue
            h.append('<path d="M%s L%s Z" fill="%s" opacity="0.5"/>'
                     % (" L".join("%.1f,%.1f" % (x, yg) for x, yv, yg in seq),
                        " L".join("%.1f,%.1f" % (x, yv) for x, yv, yg in reversed(seq)), col_))
        h.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.6"/>'
                 % (" ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v, _ in poly), c))
        h.append('<text class="anS2" x="%.1f" y="%.1f" fill="%s" '
                 'style="text-anchor:start">案%s の地盤</text>'
                 % (X(tw) + 8, Y(cp) + 26, c, o["key"]))
        # 案を採ったときの水面(汀線が動くなら、その分だけ堀が広がる)
        if o.get("waterlineShift"):
            # 幅は「石垣の面 → 対岸の汀線」で定義する(断面の端まで拾わない)
            w0, w1 = (tw, wd) if outward_of(it) < 0 else (0.0, tw)
            h.append(R(X(w0), Y(wy), X(w1) - X(w0), 5, fill=c, op=0.35))
            h.append('<path d="M%.1f,%.1f H%.1f" stroke="%s" stroke-width="2.2" '
                     'stroke-dasharray="9 4"/>' % (X(w0), Y(wy), X(w1), c))
            yy = Y(wy) - 22
            h.append('<path d="M%.1f,%.1f H%.1f M%.1f,%.1f l6,-4 v8 z M%.1f,%.1f l-6,-4 v8 z" '
                     'stroke="%s" stroke-width="1.1" fill="%s"/>'
                     % (X(w0), yy, X(w1), X(w0), yy, X(w1), yy, c, c))
            h.append('<text class="anS2" x="%.1f" y="%.1f" fill="%s">'
                     '案%s の水面 幅 %.0f m(いま %.0f m)</text>'
                     % ((X(w0) + X(w1)) / 2, Y(wy) - 27, c, o["key"], abs(w1 - w0), wd))
    # 案(汀線・天端の位置)
    ly = 22
    for o in it["options"]:
        c = COL[o["key"]]
        drawn = False
        if o.get("waterlineShift"):
            t = o["waterlineShift"] if "郭外" in it.get("side", "") else wd - o["waterlineShift"]
            same = [q2["key"] for q2 in it["options"]
                    if q2.get("waterlineShift") == o["waterlineShift"]]
            if o["key"] == same[0]:            # 同じ位置の案はまとめて1本
                h.append('<path d="M%.1f,%.1f V%.1f" stroke="%s" stroke-width="2.4" '
                         'stroke-dasharray="7 4"/>' % (X(t), Y(lo), Y(hi), c))
                h.append('<text class="anS2" x="%.1f" y="%.1f" fill="%s">'
                         '案%s の新しい汀線(%s %.1fm)</text>'
                         % (X(t), Y(hi) + 24, c, "・".join(same),
                            "郭内へ" if o["waterlineShift"] > 0 else "郭外へ",
                            abs(o["waterlineShift"])))
            drawn = True
        if o.get("fillTo"):
            h.append('<path d="M%.1f,%.1f H%.1f" stroke="%s" stroke-width="2.6" '
                     'stroke-dasharray="8 4"/>'
                     % (X(sc["tFrom"]), Y(o["fillTo"]), X(sc["tTo"]), c))
            h.append('<text class="anS2" x="%.1f" y="%.1f" fill="%s">案%s 楔をここまで盛る %.2f</text>'
                     % (X(sc["tFrom"]) + 70, Y(o["fillTo"]) - 6, c, o["key"], o["fillTo"]))
            drawn = True
        if o.get("newCoping"):
            base = 2.0
            t = 4.5 if o.get("wallToCrest") else (
                -[r for r in d["ishigaki"]["runs"]
                  if r["body"] == it["body"] and it["side"] in r["side"]][0].get("offset", 4.81)
                if "郭外" in it.get("side", "") else
                wd + [r for r in d["ishigaki"]["runs"]
                      if r["body"] == it["body"] and it["side"] in r["side"]][0].get("offset", 4.81))
            h.append('<path d="M%.1f,%.1f V%.1f" stroke="%s" stroke-width="3.4" opacity="0.95"/>'
                     % (X(t), Y(o["newCoping"]), Y(base), c))
            h.append('<text class="anS2" x="%.1f" y="%.1f" fill="%s">案%s 天端 %.2f</text>'
                     % (X(t), Y(o["newCoping"]) - 7, c, o["key"], o["newCoping"]))
            drawn = True
        if drawn:
            h.append('<path d="M%.1f,%.1f h20" stroke="%s" stroke-width="3"/>' % (W - 196, ly, c))
            h.append('<text class="sl" x="%.1f" y="%.1f">案%s %s</text>'
                     % (W - 172, ly + 4, o["key"], html.escape(o["name"])))
            ly += 15
    vex = (yh / (hi - lo)) / (xw / (sc["tTo"] - sc["tFrom"]))
    ttl = (html.escape(it["sectionAt"]["label"]) if it.get("sectionAt")
           else "距離程 %.0f m" % sc["chainage"])
    h.append('<text class="big" x="%.1f" y="20">%s ── %s ／ 垂直倍率 %.1f 倍</text>'
             % (x0, it["id"], ttl, vex))
    h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">'
             '%s</text>'
             % (x0 + xw / 2, y0 + 34,
                ("壁からの距離 [m]　── 掘り直した後の設計面　┄ いまの地盤　■ いまの石垣"
                 if gd else
                 "汀線からの距離 [m]　◀ 左=郭外(南西・愛宕下がわ) ／ 右=郭内(北東・城がわ) ▶"
                 "　┄ いまの地盤　── 案の地盤　■ いまの石垣")))
    h.append(ENDSVG)
    return "\n".join(h)


def outward_of(it):
    """陸へ向かう t の向き。郭外の岸なら左(−)、郭内なら右(+)。"""
    return -1 if "郭外" in it.get("side", "") else 1


def after_profile(d, it, o, wd, q, n, samp, sc):
    """案を採ったときの**地盤**の断面線(after)を、左(tFrom)から右(tTo)へ順に組む。

    ⚠ ここは裁定の資料。形は `saitei.json` の `after` の規則から起こす。
    採用が決まったら、決まった案だけを指図(`sotobori_sashizu.json`)へ書き移す。
    """
    a = o.get("after")
    if not a:
        return None, None, None
    runs = [r for r in d["ishigaki"]["runs"]
            if r["body"] == it["body"] and it.get("side", "") in r["side"]]
    run = next((r for r in runs if r["line"] == a.get("run")), runs[0] if runs else None)
    if run is None:
        return None, None, None
    outward = outward_of(it)                           # 陸へ向かう t の向き
    off = run.get("offset", 4.81)
    tw = -off if outward < 0 else wd + off             # 石垣の面の t
    if a["kind"] == "moveWall":                        # 法肩へ寄せる = 水面幅を変えない
        tw = 0.0 if outward < 0 else wd
    fl = [w for w in d["water"] if w["id"] == it["body"]][0]["floor"]
    cp = o.get("newCoping") or (run["copingFrom"] + run["copingTo"]) / 2
    berm, bat = a.get("berm", 0.3), a.get("batter", 2.0)
    gnd = lambda t: samp(q[0] + t * n[0], q[1] + t * n[1])
    ts = [sc["tFrom"] + i * 0.25 for i in range(int((sc["tTo"] - sc["tFrom"]) / 0.25) + 1)]

    land, moat = [], []
    # --- 陸側: 天端から犬走り、そこから 1:bat で現況へ摺り付ける(raise は水平に盛る)
    t = tw + outward * berm
    v = cp
    land.append((tw, cp))
    land.append((t, cp))
    while sc["tFrom"] <= t <= sc["tTo"]:
        t += outward * 0.25
        if a["kind"] == "raise":
            if gnd(t) >= cp:                           # 現況が天端を越えたら、そこから現況なり
                break
        else:
            v += 0.25 / bat                            # 郭外は陸が高いので**上げて**摺り付ける
            if gnd(t) <= v:
                break
            land.append((t, v))
    while sc["tFrom"] <= t <= sc["tTo"]:
        land.append((t, gnd(t)))
        t += outward * 0.25
    # --- 水側: 石垣の面から床、既に床なら現況なり
    t = tw
    moat.append((tw, fl))
    while sc["tFrom"] <= t <= sc["tTo"]:
        t -= outward * 0.25
        if abs(gnd(t) - fl) < 0.15:
            break
        moat.append((t, fl))
    while sc["tFrom"] <= t <= sc["tTo"]:
        moat.append((t, gnd(t)))
        t -= outward * 0.25
    prof = sorted(land + moat, key=lambda z: z[0])
    return prof, tw, cp


def opt_table(it):
    rows = []
    for o in it["options"]:
        rec = "推奨" in o["name"]
        rows.append("<tr%s><td style='color:%s'><b>案%s</b>%s</td><td>%s</td>"
                    "<td class='note' style='text-align:left'>%s</td>"
                    "<td class='note' style='text-align:left'>%s</td>"
                    "<td class='note' style='text-align:left'>%s</td><td>%s</td></tr>"
                    % (" style='background:var(--shu-lo)'" if rec else "",
                       COL[o["key"]], o["key"], "<br><span class='cert'>◀ 推奨</span>" if rec else "",
                       html.escape(o["name"].replace("(推奨)", "").replace("・推奨)", ")")),
                       sashizu_lib.inline(html.escape(o["detail"])),
                       sashizu_lib.inline(html.escape("⭕ " + o["pro"])),
                       sashizu_lib.inline(html.escape(o["con"])), o["cert"]))
    return ('<div class="tw"><table><thead><tr><th></th><th>案</th><th>中身</th>'
            "<th>よい所</th><th>引っかかる所</th><th>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backups", default=os.path.join(ROOT, "TerrainBackups"))
    a = ap.parse_args()
    d = json.load(open(os.path.join(DOC, "sotobori_sashizu.json"), encoding="utf-8"))
    sj = json.load(open(os.path.join(DOC, "sotobori_saitei.json"), encoding="utf-8"))
    meta, cur = load_terrain(a.backups)
    samp = make_sampler(meta, cur)
    boxes = [it["keymap"] for it in sj["items"] if it.get("showDesign")]
    dsamp = None
    if boxes:
        bx = (min(b[0] for b in boxes) - 30, max(b[1] for b in boxes) + 30,
              min(b[2] for b in boxes) - 30, max(b[3] for b in boxes) + 30)
        dsamp = design_grid(d, a.backups, bx)
    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"),
               encoding="utf-8").read()
    KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九"]
    h = ['<meta charset="utf-8">', "<title>%s</title>" % html.escape(sj["title"]),
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">%s</p>' % html.escape(sj["subtitle"]))
    h.append("<h1>%s</h1>" % html.escape(sj["title"]))
    h.append('<p class="lede">%s</p>' % sashizu_lib.inline(html.escape(sj["lede"])))
    if sj.get("pending"):
        h.append('<div class="box" style="border-color:var(--shu)"><p>%s</p></div>'
                 % sashizu_lib.inline(html.escape(sj["pending"])))
    h.append('<div class="box"><p><b>読み方</b> ── 件ごとに <b>①どこか(全体の中の位置)</b>／'
             '<b>②拡大平面</b>／<b>③断面に案を重ねた図</b>／<b>④案の表</b> の順に並べた。'
             '断面の<span style="color:%s">朱の縦棒</span>がいまの石垣、'
             '<span style="color:%s">緑</span>が案A、<span style="color:%s">茶</span>が案B。'
             '案Cは「現状のまま」なので線を引いていない。</p></div>'
             % ("var(--shu)", COL["A"], COL["B"]))
    n = 0
    for it in sj["items"]:
        for _ in range(1):
            n += 1
            h.append('<div class="plate"><div class="phead"><h2>%s　%s %s</h2>'
                     '<span class="meta">%s</span></div>'
                     % (KAN[n - 1], it["id"], html.escape(it["title"]), html.escape(it["where"])))
        h.append('<p class="cap"><b>いま何がそうなっているか</b> ── %s</p>'
                 % sashizu_lib.inline(html.escape(it["now"])))
        h.append('<p class="cap">%s</p>' % sashizu_lib.inline(html.escape(it["cause"])))
        h.append("<h4>① どこか</h4>")
        h.append('<div class="fig">%s</div>' % keymap_svg(d, it))
        h.append("<h4>② 拡大平面</h4>")
        h.append('<div class="fig">%s</div>' % zoom_svg(d, it, samp))
        if it.get("section") or it.get("sectionAt"):
            h.append("<h4>③ 断面 ── いまの姿(before)に案(after)を重ねる</h4>")
            h.append('<p class="cap">'
                     '<b>┄ 細い破線＝いまの地盤(before)／── 太い実線＝案を採った後の地盤(after)。</b>'
                     '寒色の塗りが<b>削る土</b>、暖色が<b>盛る土</b>。'
                     '⚠ <b>案で汀線が動くのは、水が土を押すからではない</b> — '
                     '石垣の手前に余っている土を削るので、その分だけ<b>堀の水面が広がる</b>。'
                     '断面の左右は下の軸に書いた方位のとおりで、平面図の朱の丸「左」「右」に対応する。</p>')
            h.append('<div class="fig">%s</div>' % sect_svg(d, it, samp, dsamp=dsamp))
        h.append("<h4>④ 案</h4>")
        h.append(opt_table(it))
        h.append("</div>")
    h.append('<div class="plate"><div class="phead"><h2>%s　決め方</h2></div>' % KAN[n])
    h.append('<p class="cap">案を選んでいただければ、選ばれた案だけを '
             '<code>sotobori_sashizu.json</code> へ書き移し、指図を組み直して再検図に掛ける。'
             'この文書はそのとき「決まった」と記して畳む。⛔ '
             '<b>それまで石垣は1個も動かさない</b>(CLAUDE.md 絶対規則1)。'
             '掘り直しそのもの(00002・00003)は、この裁定と無関係に進められる。</p>')
    h.append('<div class="foot">組んだ日 %s ／ 案の定義 <code>sotobori_saitei.json</code> ／ '
             '指図 <code>sotobori_sashizu.json</code>。地盤は 2026-08-26 の現況。'
             'Y は海抜 m。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div></div>")
    out = "\n".join(h)
    open(OUT, "w", encoding="utf-8").write(out)
    print("wrote %s ／ 件 %d ／ 図版 %d 面 ／ %.0f KB"
          % (OUT, len(sj["items"]), out.count("<svg"), os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
