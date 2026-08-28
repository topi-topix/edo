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
    # ⚠ 窓が広いとセルが爆発する(U11 で 6.5MB まで膨らんだ)。1辺 160m を超えたら粗くする
    st = 2.0 if max(k[1] - k[0], k[3] - k[2]) <= 160 else 4.0
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
    sec = None
    if it.get("sectionAt"):
        sa = it["sectionAt"]
        aa = math.radians(sa["yaw"])
        nn = (math.cos(aa), -math.sin(aa))
        sec = ((sa["p"][0] + sa["tFrom"] * nn[0], sa["p"][1] + sa["tFrom"] * nn[1]),
               (sa["p"][0] + sa["tTo"] * nn[0], sa["p"][1] + sa["tTo"] * nn[1]), nn)
    elif it.get("section"):
        sw, ne, u, nn, ln = frame(d, it["body"])
        c = it["section"]["chainage"]
        qq = (sw[0][0] + c * u[0], sw[0][1] + c * u[1])
        sec = ((qq[0] + it["section"]["tFrom"] * nn[0], qq[1] + it["section"]["tFrom"] * nn[1]),
               (qq[0] + it["section"]["tTo"] * nn[0], qq[1] + it["section"]["tTo"] * nn[1]), nn)
    if sec:
        aP, bP, nn = sec
        h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#7A2E1E" stroke-width="1.6" '
                 'stroke-dasharray="9 5"/>' % (p.X(aP[0]), p.Y(aP[1]), p.X(bP[0]), p.Y(bP[1])))
        # 矢視 — 断面の「右」が nn の向きなので、見ている向きは nn を+90°回した向き
        vx, vz = -nn[1], nn[0]
        for pt, lab in ((aP, "左"), (bP, "右")):
            sx, sy = p.X(pt[0]), p.Y(pt[1])
            ex, ey = p.X(pt[0] + 26 * vx), p.Y(pt[1] + 26 * vz)
            dxp, dyp = ex - sx, ey - sy
            ln2 = math.hypot(dxp, dyp) or 1
            ux2, uy2 = dxp / ln2, dyp / ln2
            h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#7A2E1E" stroke-width="2.4"/>'
                     % (sx, sy, ex, ey))
            h.append('<path d="M%.1f,%.1f l%.1f,%.1f l%.1f,%.1f z" fill="#7A2E1E"/>'
                     % (ex, ey, -8 * ux2 - 4 * uy2, -8 * uy2 + 4 * ux2,
                        8 * uy2, -8 * ux2))
            h.append('<circle cx="%.1f" cy="%.1f" r="8" fill="var(--paper)" stroke="#7A2E1E" '
                     'stroke-width="1.6"/><text class="rmS" x="%.1f" y="%.1f" fill="#7A2E1E">%s</text>'
                     % (sx, sy, sx, sy + 4, lab))
        mx = (p.X(aP[0]) + p.X(bP[0])) / 2 + 44 * vx
        my = (p.Y(aP[1]) + p.Y(bP[1])) / 2 - 44 * vz
        h.append(R(mx - 96, my - 13, 192, 20, fill="var(--paper)", op=0.85))
        h.append('<text class="anG" x="%.1f" y="%.1f" style="text-anchor:middle">'
                 '▶ 矢印の向きに見た図が下の断面</text>' % (mx, my + 2))
    h.append('<path d="M%.1f,%.1f l0,-26 m-5,7 l5,-7 l5,7" stroke="var(--dim)" '
             'stroke-width="1.2" fill="none"/>'
             '<text class="anS2" x="%.1f" y="%.1f">北</text>'
             % (p.W - 30, p.H - 30, p.W - 30, p.H - 36))
    L = p.L(50)
    h.append('<path d="M14,%.1f h%.1f" stroke="var(--dim)" stroke-width="1.4"/>'
             '<text class="sl" x="%.1f" y="%.1f">50 m</text>' % (p.H - 12, L, 14 + L + 6, p.H - 9))
    h.append(ENDSVG)
    return "\n".join(h)


def sect_frame(d, it):
    """断面の切り位置(点 q・法線 n・水面幅 wd・範囲 sc)を決める。"""
    if it.get("sectionAt"):
        sa = it["sectionAt"]
        q = tuple(sa["p"])
        # ⚠ yaw は Unity 規約(+Z から +X へ)。方向ベクトルは (sin,cos)、その直角は (cos,-sin)。
        #    数学角の回転(cos(θ+90),sin(θ+90)) を当てると 19°ずれる(2026-08-28 検図 高-2)。
        ang = math.radians(sa["yaw"])
        n = (math.cos(ang), -math.sin(ang))
        return q, n, 0.0, {"chainage": 0.0, "tFrom": sa["tFrom"], "tTo": sa["tTo"]}, sa["label"]
    sw, ne, u, n, ln = frame(d, it["body"])
    sc = it["section"]
    q = (sw[0][0] + sc["chainage"] * u[0], sw[0][1] + sc["chainage"] * u[1])
    return q, n, width_at(q, n, ne), sc, "距離程 %.0f m" % sc["chainage"]


def _axes(h, sc, lo, hi, W, H, x0, xw, y0, yh, X, Y):
    for v in range(int(math.floor(lo)), int(math.ceil(hi)) + 1):
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="var(--rule)" stroke-width="0.5" '
                 'opacity="0.8"/>' % (x0 - 6, Y(v), x0 + xw))
        h.append('<text class="sl" x="16" y="%.1f">%d m</text>' % (Y(v) + 3, v))
    for t in range(int(sc["tFrom"]), int(sc["tTo"]) + 1, 5):
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="var(--rule)" stroke-width="0.4" '
                 'opacity="0.6"/>' % (X(t), Y(lo), Y(hi)))
        if t % 10 == 0:
            h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">%+d</text>'
                     % (X(t), y0 + 15, t))


def sect_svg(d, it, samp, mode="before", dsamp=None, W=1180.0):
    """断面を**1枚に1状態だけ**描く。mode="before" は現況、それ以外は案のキー。

    ⚠ before と after を重ねない(2026-08-27 ユーザー指示)。読み比べは図を並べて行う。
    """
    q, n, wd, sc, sub = sect_frame(d, it)
    body = [w for w in d["water"] if w["id"] == it["body"]][0]
    wy, fl = body["waterY"], body["floor"]
    ts = [sc["tFrom"] + i * 0.5 for i in range(int((sc["tTo"] - sc["tFrom"]) / 0.5) + 1)]
    cur = [(t, samp(q[0] + t * n[0], q[1] + t * n[1])) for t in ts]
    if it.get("showDesign") and dsamp:
        cur = [(t, dsamp(q[0] + t * n[0], q[1] + t * n[1])) for t in ts]
    o = None
    prof, tw, cp = None, None, None
    if mode != "before":
        o = [x for x in it["options"] if x["key"] == mode][0]
        prof, tw, cp = after_profile(d, it, o, wd, q, n, samp, sc)
    g = prof if prof else cur          # fitBed は地形を動かさないので現況のまま
    lo = min(min(v for _, v in g), fl) - 1.0
    hi = max(max(v for _, v in g), (cp or 0) + 0.5, 10.5) + 0.6
    H = 340.0
    h = _sv(W, H, "断面")
    h.append(R(0, 0, W, H, fill="var(--paper)"))
    x0, xw, y0, yh = 58.0, W - 92.0, H - 54, H - 96
    X = lambda t: x0 + (t - sc["tFrom"]) / (sc["tTo"] - sc["tFrom"]) * xw
    Y = lambda v: y0 - (v - lo) / (hi - lo) * yh
    _axes(h, sc, lo, hi, W, H, x0, xw, y0, yh, X, Y)
    # --- 水面
    if it.get("sectionAt"):
        run = []
        for t, v in g:
            if v < wy:
                run.append(t)
            elif run:
                h.append(R(X(run[0]), Y(wy), X(run[-1]) - X(run[0]), Y(fl) - Y(wy),
                           fill="#BBD3DF", op=0.85))
                run = []
        if run:
            h.append(R(X(run[0]), Y(wy), X(run[-1]) - X(run[0]), Y(fl) - Y(wy),
                       fill="#BBD3DF", op=0.85))
        w0 = w1 = None
    else:
        # ⚠ 幅は断面の描画範囲でなく**堀の全幅**で測る(範囲外へ出ていても数字は全幅)
        full = [(t, samp(q[0] + t * n[0], q[1] + t * n[1]))
                for t in [-24 + i * 0.25 for i in range(int((wd + 48) / 0.25) + 1)]]
        if prof:
            # ⚠ prof の t は tw 起点の累積で格子に乗らない。**線形補間で合成する**
            #    (dict 引きは 0/91 ヒットの死にコードだった。2026-08-28 検図 中-3)
            px_ = [t for t, _ in prof]
            pv_ = [v for _, v in prof]
            lo_, hi_ = px_[0], px_[-1]
            full = [(t, (np_interp(t, px_, pv_) if lo_ <= t <= hi_ else v)) for t, v in full]
        b0, b1 = waterline_span(full, wy)
        w0, w1 = 0.0, wd
        kind = (o or {}).get("after", {}).get("kind")
        fit = bool(o and (kind in ("fitBed", "fitWaterline") or o.get("assumeFitBed")))
        if fit and b0 is not None:
            w0, w1 = b0, b1                            # 板を**本当の汀線**へ載せる
        elif o and o.get("waterlineShift") and tw is not None:
            if outward_of(it) < 0:
                w0 = tw
            else:
                w1 = tw
        a0, a1 = max(sc["tFrom"], w0), min(sc["tTo"], w1)
        h.append(R(X(a0), Y(wy), X(a1) - X(a0), Y(fl) - Y(wy), fill="#BBD3DF", op=0.9))
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="#3F6F86" stroke-width="1.8"/>'
                 % (X(a0), Y(wy), X(a1)))
        h.append('<text class="an2b" x="%.1f" y="%.1f">水面 %.2f</text>'
                 % (X(a0) + 5, Y(wy) - 6, wy))
        h.append('<text class="sl" x="%.1f" y="%.1f">床 %.2f</text>' % (X(a0) + 5, Y(fl) + 13, fl))
        yy = Y(wy) - 26
        cw = COL[mode] if o else "#3F6F86"
        h.append('<path d="M%.1f,%.1f H%.1f M%.1f,%.1f l7,-4 v8 z M%.1f,%.1f l-7,-4 v8 z" '
                 'stroke="%s" stroke-width="1.1" fill="%s"/>'
                 % (X(a0), yy, X(a1), X(a0), yy, X(a1), yy, cw, cw))
        h.append('<text class="anS2" x="%.1f" y="%.1f" fill="%s">水面の板の幅 %.1f m%s</text>'
                 % ((X(a0) + X(a1)) / 2, yy - 6, cw, w1 - w0,
                    "" if (a0 <= w0 + 0.01 and a1 >= w1 - 0.01) else "(図は一部)"))
        if b0 is not None:                             # 堀底の範囲と、板とのズレ
            yb = Y(fl) + 26
            q0, q1 = max(b0, sc["tFrom"]), min(b1, sc["tTo"])
            h.append('<path d="M%.1f,%.1f H%.1f M%.1f,%.1f l7,-4 v8 z M%.1f,%.1f l-7,-4 v8 z" '
                     'stroke="var(--ink)" stroke-width="1.1" fill="var(--ink)"/>'
                     % (X(q0), yb, X(q1), X(q0), yb, X(q1), yb))
            h.append(R((X(max(b0, sc["tFrom"])) + X(min(b1, sc["tTo"]))) / 2 - 88, yb + 2, 176, 16,
                       fill="var(--paper)", op=0.9))
            bx0, bx1 = X(max(b0, sc["tFrom"])), X(min(b1, sc["tTo"]))
            h.append('<text class="anS2" x="%.1f" y="%.1f" style="text-anchor:middle">'
                     '地形が水位を切る幅(本当の汀線) %.1f m%s</text>'
                     % ((bx0 + bx1) / 2, yb + 14, b1 - b0,
                        "" if (b0 >= sc["tFrom"] and b1 <= sc["tTo"]) else "(図は一部)"))
            for tt, dd, lab in ((b0, b0 - w0, "板が地形にめり込む"),
                                (b1, b1 - w1, "板が地形に届かない")):
                if dd > 0.4:
                    x1_, x2_ = sorted([X(tt), X(tt - dd if tt == b0 else tt - dd)])
                    h.append(R(x1_, Y(wy), x2_ - x1_, Y(fl) - Y(wy),
                               fill="var(--ishi)" if fit else "var(--shu)", op=0.30))
                    h.append('<text class="anG" x="%.1f" y="%.1f" style="text-anchor:middle">'
                             '%s %.1fm</text>' % ((x1_ + x2_) / 2, Y(fl) + 13, lab, dd))
    # --- 地盤
    h.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.6"/>'
             % (" ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in g),
                COL[mode] if o else "var(--ink)"))
    # --- 石垣
    runs = [r for r in d["ishigaki"]["runs"] if r["body"] == it["body"]]   # 両岸を描く
    for r in runs:
        a2, b2 = r["p0"], r["p1"]
        dx2, dz2 = b2[0] - a2[0], b2[1] - a2[1]
        l2 = dx2 * dx2 + dz2 * dz2
        u2 = max(0.0, min(1.0, ((q[0] - a2[0]) * dx2 + (q[1] - a2[1]) * dz2) / l2))
        pj = (a2[0] + u2 * dx2, a2[1] + u2 * dz2)
        if it.get("sectionAt"):
            t = (pj[0] - q[0]) * n[0] + (pj[1] - q[1]) * n[1]
            if math.hypot(pj[0] - q[0] - t * n[0], pj[1] - q[1] - t * n[1]) > 6:
                continue
        else:
            if math.hypot(q[0] - pj[0], q[1] - pj[1]) > 40:
                continue
            off = r.get("offset", 4.81)
            t = -off if "郭外" in r["side"] else wd + off
        c0_ = r["copingFrom"] + (r["copingTo"] - r["copingFrom"]) * u2
        base = r.get("base", 0.0)
        if o and (o.get("after", {}).get("snapWalls") or o.get("assumeFitBed")) and b0 is not None:
            t = b0 if "郭外" in r["side"] else b1   # 案で汀線へ据え直す石垣
            col_ = COL[mode]
        elif o and tw is not None and r["line"] == o.get("after", {}).get("run"):
            t, c0_ = tw, cp                       # 案で動く/上がる石垣
            col_ = COL[mode]
        else:
            col_ = "var(--shu)"
        if not (sc["tFrom"] <= t <= sc["tTo"]):
            continue
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="%s" stroke-width="5.5" opacity="0.95"/>'
                 % (X(t), Y(c0_), Y(base), col_))
        h.append('<text class="anS2" x="%.1f" y="%.1f" fill="%s">%s 天端 %.2f</text>'
                 % (X(t), Y(c0_) - 8, col_, r["line"], c0_))
        gh = dict((round(a3, 1), b3) for a3, b3 in g).get(round(t, 1))
        if gh is None:
            gh = samp(q[0] + t * n[0], q[1] + t * n[1])
        if gh - c0_ > 0.3:
            h.append('<text class="anG" x="%.1f" y="%.1f" style="text-anchor:middle">'
                     '⛔ 地盤 %.2f = 天端が %.2fm 土の中</text>' % (X(t), Y(c0_) + 15, gh, gh - c0_))
    face = "掘り直し後の設計面" if it.get("showDesign") else "いまの姿(before)"
    ttl = (face if mode == "before"
           else "案%s を採った後(after) ── %s" % (mode, html.escape(o["name"])))
    h.append('<text class="big" x="%.1f" y="20">%s ── %s ／ %s</text>'
             % (x0, it["id"], html.escape(sub), ttl))
    vex = (yh / (hi - lo)) / (xw / (sc["tTo"] - sc["tFrom"]))
    # ⚠ 左右は**その断面の法線**から出す。literal に刷ると sectionAt の断面で逆になる(検図 高-1)
    seg0 = [w for w in d["reach"]["segments"] if w["body"] == it["body"]][0]
    inw = (seg0["ne"][0][0] - seg0["sw"][0][0], seg0["ne"][0][1] - seg0["sw"][0][1])
    toward_kakunai = n[0] * inw[0] + n[1] * inw[1] > 0     # +t が郭内を向くか
    lab_l, lab_r = ("郭外(南西・愛宕下がわ)", "郭内(北東・城がわ)") if toward_kakunai \
        else ("郭内(北東・城がわ)", "郭外(南西・愛宕下がわ)")
    h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">'
             '◀ 左=%s ／ 右=%s ▶　汀線からの距離 [m]　垂直倍率 %.1f 倍</text>'
             % (x0 + xw / 2, y0 + 34, lab_l, lab_r, vex))
    h.append(ENDSVG)
    return "\n".join(h)


def bed_span(g, fl, tol=0.25):
    """断面の中で「床」になっている範囲。"""
    ts = [t for t, v in g if abs(v - fl) < tol]
    return (min(ts), max(ts)) if ts else (None, None)


def waterline_span(g, wy):
    """**本当の汀線** — 地形が水位を横切る所。水面の板の縁はここに来るのが正しい。

    ⚠ 床(堀底)の縁ではない。床の縁は法尻で、水位を切る線はその 0.5〜1.3m 外側にある。
    ⛔ **事前条件: 窓の両端が水位より高いこと。** 満たさないと堀の外の低地を平然と拾う
       (2026-08-28 検図 中-4。00001 の距離程10 で窓を広げると 49m→85m と発散した)。
       満たさないときは (None, None) を返し、図には「判定不能」を出す。
    """
    if not g or g[0][1] < wy or g[-1][1] < wy:
        return None, None
    ts = [t for t, v in g if v < wy]
    return (min(ts), max(ts)) if ts else (None, None)


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
    runs = [r for r in d["ishigaki"]["runs"] if r["body"] == it["body"]]   # 両岸を描く
    run = next((r for r in runs if r["line"] == a.get("run")), runs[0] if runs else None)
    if run is None:
        return None, None, None
    outward = outward_of(it)                           # 陸へ向かう t の向き
    off = run.get("offset", 4.81)
    tw = -off if outward < 0 else wd + off             # 石垣の面の t
    if a["kind"] in ("fitBed", "fitWaterline"):        # 地形は動かさない
        return None, None, None
    gnd = gnd0 = lambda t: samp(q[0] + t * n[0], q[1] + t * n[1])
    fl = [w for w in d["water"] if w["id"] == it["body"]][0]["floor"]
    if a["kind"] == "moveWall":                        # 法肩/法尻へ寄せる
        gg = [(t, gnd0(t)) for t in [sc["tFrom"] + i * 0.5
                                     for i in range(int((sc["tTo"] - sc["tFrom"]) / 0.5) + 1)]]
        b0, b1 = bed_span(gg, fl)
        if b0 is not None:
            tw = b0 if outward < 0 else b1
    cp = o.get("newCoping") or (run["copingFrom"] + run["copingTo"]) / 2
    berm, bat = a.get("berm", 0.3), a.get("batter", 2.0)
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
            v -= 0.25 / bat                            # 天端から 1:bat で**降ろして**現況へ当てる
            if gnd(t) >= v:
                land.append((t, gnd(t)))
                break
            land.append((t, v))
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
    # ⚠ t=tw で3点が同値になる。水側(床)→天端→犬走り の順に固定しないと犬走りが斜路になる
    tag = [(t, v, 1) for t, v in land] + [(t, v, 0) for t, v in moat]
    tag.sort(key=lambda z: (z[0], z[2] if z[0] >= tw else -z[2]))
    prof = [(t, v) for t, v, _ in tag]
    return prof, tw, cp


def np_interp(x, xs, ys):
    """xs は昇順。線形補間(numpy を使わない小さな実装)。"""
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    if xs[hi] == xs[lo]:
        return ys[lo]
    r = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] * (1 - r) + ys[hi] * r


def in_poly(x, z, w):
    ins = False
    j = len(w) - 1
    for i in range(len(w)):
        xi, zi = w[i]
        xj, zj = w[j]
        if ((zi > z) != (zj > z)) and (x < (xj - xi) * (z - zi) / ((zj - zi) + 1e-12) + xi):
            ins = not ins
        j = i
    return ins


def notch_svg(d, it, W=1180.0):
    """U7 専用 — 水面の形だけを大きく描いて、出っ張りの before / after を左右に並べる。

    ⚠ 段彩や等高線は載せない。**形の話**なので、線だけにしたほうが伝わる。
    """
    nt = it["notch"]                       # [手前, 出っ張りの頂点, 先]
    new = it["options"][0]["newOutline"]   # 出っ張りを落とした線
    xs = [p2[0] for p2 in nt] + [p2[0] for p2 in new]
    zs = [p2[1] for p2 in nt] + [p2[1] for p2 in new]
    pad = 26.0
    H = 470.0
    half = W / 2 - 12
    sc = min(half / (max(xs) - min(xs) + 2 * pad), (H - 96) / (max(zs) - min(zs) + 2 * pad))
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    h = _sv(W, H, "入隅の before/after")
    h.append(R(0, 0, W, H, fill="var(--paper)"))
    body = [w for w in d["water"] if w["id"] == it["body"]][0]

    # 水の側(00003 の内側)へ向かう法線
    ax_, az_ = nt[0]
    cx_, cz_ = nt[2]
    dxv, dzv = cx_ - ax_, cz_ - az_
    ln_ = math.hypot(dxv, dzv)
    nrm = (-dzv / ln_, dxv / ln_)
    mid = ((ax_ + cx_) / 2, (az_ + cz_) / 2)
    if not in_poly(mid[0] + 5 * nrm[0], mid[1] + 5 * nrm[1], body["outline"]):
        nrm = (-nrm[0], -nrm[1])

    def panel(ox, pts, title, col_, note):
        X = lambda x: ox + half / 2 + (x - cx) * sc
        Y = lambda z: 62 + (H - 118) / 2 - (z - cz) * sc
        h.append(R(ox + 6, 46, half - 12, H - 76, fill="var(--paper2)", stroke="var(--rule)", sw=1))
        h.append('<text class="big" x="%.1f" y="34">%s</text>' % (ox + 16, title))
        poly = [(X(a[0]), Y(a[1])) for a in pts]
        deep = [(X(a[0] + 32 * nrm[0]), Y(a[1] + 32 * nrm[1])) for a in pts]   # 堀の実幅 ≈32m
        h.append('<path d="M%s L%s Z" fill="#BBD3DF" opacity="0.6"/>'
                 % (" L".join("%.1f,%.1f" % q for q in poly),
                    " L".join("%.1f,%.1f" % q for q in reversed(deep))))
        h.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3.4"/>'
                 % (" ".join("%.1f,%.1f" % q for q in poly), col_))
        h.append('<text class="anS2" x="%.1f" y="%.1f">水面(堀)</text>'
                 % (X(mid[0] + 34 * nrm[0]), Y(mid[1] + 34 * nrm[1])))
        h.append('<text class="anS2" x="%.1f" y="%.1f">陸(郭内・城がわ)</text>'
                 % (X(mid[0] - 22 * nrm[0]), Y(mid[1] - 22 * nrm[1])))
        h.append('<text class="cap" x="%.1f" y="%.1f" style="font-size:12.5px;fill:var(--dim)">'
                 '%s</text>' % (ox + 16, H - 16, note))
        return X, Y

    X1, Y1 = panel(0, nt, "いま ── 岸が水の中へ三角に張り出している",
                   "#2C5D74", "この三角形は実際の堀には無い(明治17年の実測図で確認)")
    v = nt[1]
    a2, c2 = nt[0], nt[2]
    # 張り出しの深さを寸法で
    mx = (X1(a2[0]) + X1(c2[0])) / 2
    my = (Y1(a2[1]) + Y1(c2[1])) / 2
    h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="var(--dim)" stroke-width="1" '
             'stroke-dasharray="5 3"/>' % (X1(a2[0]), Y1(a2[1]), X1(c2[0]), Y1(c2[1])))
    h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="var(--shu)" stroke-width="1.6"/>'
             % (mx, my, X1(v[0]), Y1(v[1])))
    h.append('<circle cx="%.1f" cy="%.1f" r="5" fill="none" stroke="var(--shu)" stroke-width="2"/>'
             % (X1(v[0]), Y1(v[1])))
    dxc, dzc = c2[0] - a2[0], c2[1] - a2[1]
    depth = abs((v[0] - a2[0]) * dzc - (v[1] - a2[1]) * dxc) / math.hypot(dxc, dzc)
    h.append('<text class="anG" x="%.1f" y="%.1f">張り出しの深さ %.1f m</text>'
             % (X1(v[0]) + 10, Y1(v[1]) + 4, depth))
    X2, Y2 = panel(W / 2 + 12, new, "案A ── 岸を一直線にする",
                   COL["A"], "明治17年の実測図では、この区間の岸は新橋を過ぎても一直線")
    for r in d["ishigaki"]["runs"]:
        if r["line"] not in ("NE3f", "NE3g"):
            continue
        for X_, Y_, cc in ((X1, Y1, "var(--shu)"), (X2, Y2, COL["A"])):
            h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="%s" stroke-width="4" '
                     'stroke-linecap="round" opacity="0.9"/>'
                     % (X_(r["p0"][0]), Y_(r["p0"][1]), X_(r["p1"][0]), Y_(r["p1"][1]), cc))
        h.append('<text class="anS2" x="%.1f" y="%.1f">%s(%d個)</text>'
                 % (X1((r["p0"][0] + r["p1"][0]) / 2), Y1((r["p0"][1] + r["p1"][1]) / 2) - 10,
                    r["line"], r["n"]))
        a3, c3 = new[0], new[1]
        dxn, dzn = c3[0] - a3[0], c3[1] - a3[1]
        lnn = math.hypot(dxn, dzn)
        sd_ = lambda pt: ((pt[0] - a3[0]) * dzn - (pt[1] - a3[1]) * dxn) / lnn
        s0, s1 = sd_(r["p0"]), sd_(r["p1"])
        if s0 * s1 < 0:                                   # 新しい汀線をまたぐ
            frac = abs(s1) / (abs(s0) + abs(s1)) if s0 < 0 else abs(s0) / (abs(s0) + abs(s1))
            msg = "%s は新しい汀線をまたぐ(約%d個が水中)" % (r["line"], round(r["n"] * frac))
        else:
            msg = "%s は%s" % (r["line"], "全部が水中" if max(s0, s1) > 0 else "全部が陸側")
        h.append('<text class="anG" x="%.1f" y="%.1f">%s</text>'
                 % (X2((r["p0"][0] + r["p1"][0]) / 2), Y2((r["p0"][1] + r["p1"][1]) / 2) + 16, msg))
    h.append('<text class="sl" x="%.1f" y="%.1f">← 虎ノ門・新シ橋がわ</text>' % (14, H - 34))
    h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:end">幸橋がわ →</text>'
             % (W - 14, H - 34))
    h.append(ENDSVG)
    return "\n".join(h)


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
        if it.get("notch"):
            h.append("<h4>② 何が問題なのか ── 水面の形だけを見る</h4>")
            h.append('<div class="fig">%s</div>' % notch_svg(d, it))
            for para in it["plain"].split("\n\n"):
                h.append('<p class="cap" style="max-width:80ch">%s</p>'
                         % sashizu_lib.inline(html.escape(para.strip())))
            h.append("<h4>③ 同じ場所の地形(段彩は<b>現況</b>)</h4>")
        else:
            h.append("<h4>② 拡大平面</h4>")
        h.append('<div class="fig">%s</div>' % zoom_svg(d, it, samp))
        if it.get("section") or it.get("sectionAt"):
            h.append("<h4>%s 断面 ── %s</h4>"
                     % ("④" if it.get("notch") else "③",
                        "掘り直し後の設計面(この件は掘った後の姿で見る)"
                        if it.get("showDesign") else "いまの姿"))
            h.append('<div class="fig">%s</div>' % sect_svg(d, it, samp, "before", dsamp))
            nn = 4
            for o in it["options"]:
                if not o.get("after"):
                    continue
                h.append("<h4>%s 断面 ── 案%s を採った後</h4>"
                         % ("④⑤⑥⑦⑧"[nn - 4 + (1 if it.get("notch") else 0)], o["key"]))
                h.append('<div class="fig">%s</div>' % sect_svg(d, it, samp, o["key"], dsamp))
                if o.get("after", {}).get("kind") == "fitBed":
                    h.append('<p class="cap">⭐ <b>地形は1セルも触っていない。</b>動かしたのは'
                             '<b>水面のポリゴンだけ</b>で、堀底(黒の寸法線)にぴたりと載せた。'
                             'ひとつ上の「いまの姿」で朱に塗った<b>「板が届かない」帯が消える</b>のが'
                             'この案の中身。</p>')
                elif o.get("waterlineShift"):
                    h.append('<p class="cap">ひとつ上の「いまの姿」と見比べること。</p>')
                nn += 1
        h.append("<h4>案</h4>")
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
