#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""京極備中守上屋敷(丹後峯山藩 1万1,144石)の指図を一枚に組む。

  設計値の正典 = docs/Sashizu/kyogoku_bitchu_sashizu.json
  文章の正典   = docs/Sashizu/kyogoku_bitchu_kosho.md
  地盤         = docs/Sashizu/kyogoku_bitchu_edo_world.json(江戸期復元・造成前)
                 docs/Sashizu/kyogoku_bitchu_dem.json      (現況・近代造成を含む)

⛔ **この生成器は実装(C#)を読まない。**座標は世界座標から Proj/RGrid で直に変換する。
⛔ 設計値をここに書かない。数値はすべて json から引く。

    python3 Tools/Sashizu/build_kyogoku_bitchu_sashizu.py
"""
import json, math, os, sys, itertools, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sashizu_lib as L

DOC = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "Sashizu"))
JSON = os.path.join(DOC, "kyogoku_bitchu_sashizu.json")
MD = os.path.join(DOC, "kyogoku_bitchu_kosho.md")
EDO = os.path.join(DOC, "kyogoku_bitchu_edo_world.json")
CUR = os.path.join(DOC, "kyogoku_bitchu_dem.json")
OUT = os.path.join(DOC, "kyogoku_bitchu_sashizu.html")
KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
       "其十一", "其十二", "其十三", "其十四"]

d = json.load(open(JSON, encoding="utf-8"))
KEN = d["const"]["ken"]
TSUBO = d["const"]["tsubo"]
GR = d["grid"]["shukaku"]
POLY = d["polygon"]
IPOLY = d["insetPolygon"]
DEM = {"edo": json.load(open(EDO, encoding="utf-8")), "cur": json.load(open(CUR, encoding="utf-8"))}


# ---------------------------------------------------------------- 座標
def W(u, v):
    return (GR["x0"] + (GR["ux"] * u + GR["vx"] * v) * KEN,
            GR["z0"] + (GR["uz"] * u + GR["vz"] * v) * KEN)


def UV(x, z):
    dx, dz = x - GR["x0"], z - GR["z0"]
    return ((dx * GR["ux"] + dz * GR["uz"]) / KEN, (dx * GR["vx"] + dz * GR["vz"]) / KEN)


def H(key, x, z):
    S = DEM[key]
    fx = (x - S["x0"]) / S["step"]; fz = (z - S["z0"]) / S["step"]
    i0, j0 = math.floor(fx), math.floor(fz)
    if not (0 <= i0 < S["nx"] - 1 and 0 <= j0 < S["nz"] - 1):
        return None
    tx, tz = fx - i0, fz - j0
    a, b = S["h"][j0][i0], S["h"][j0][i0 + 1]
    c, e = S["h"][j0 + 1][i0], S["h"][j0 + 1][i0 + 1]
    return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + e * tx) * tz


def in_poly(p, x, z):
    c = False; n = len(p)
    for i in range(n):
        (ax, az), (bx, bz) = p[i], p[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (bx - ax) * (z - az) / (bz - az):
            c = not c
    return c


def in_uv(p, u, v):
    c = False; n = len(p)
    for i in range(n):
        (au, av), (bu, bv) = p[i], p[(i + 1) % n]
        if (av > v) != (bv > v) and u < au + (bu - au) * (v - av) / (bv - av):
            c = not c
    return c


def poly_area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
                   for i in range(len(p)))) / 2.0


T = {t["name"]: t for t in d["terraces"]}
M = {m["name"]: m for m in d["mune"]}
Z = {z["name"]: z for z in d["zones"]}
AREA = poly_area(POLY)


def in_terrace(name, u, v):
    t = T[name]
    if "poly" in t:
        return in_uv(t["poly"], u, v)
    return t["u0"] <= u <= t["u1"] and t["v0"] <= v <= t["v1"]


def design_y(u, v):
    for nm in ("T1", "T2"):
        if in_terrace(nm, u, v):
            return T[nm]["y"]
    return None


def edge_at(e, s):
    a, b = IPOLY[e], IPOLY[(e + 1) % len(IPOLY)]
    Lm = d["edgeLen"][str(e)]
    t = s / Lm
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def edge_norm(e):
    a, b = IPOLY[e], IPOLY[(e + 1) % len(IPOLY)]
    Lm = math.hypot(b[0] - a[0], b[1] - a[1])
    nx_, nz_ = (b[1] - a[1]) / Lm, -(b[0] - a[0]) / Lm
    cx = sum(p[0] for p in IPOLY) / len(IPOLY); cz = sum(p[1] for p in IPOLY) / len(IPOLY)
    mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if (cx - mx) * nx_ + (cz - mz) * nz_ < 0:
        nx_, nz_ = -nx_, -nz_
    return nx_, nz_


# ---------------------------------------------------------------- SVG の道具
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def dpath(P, pts, close=True):
    s = "M " + " L ".join("%.1f %.1f" % (P.X(a), P.Y(b)) for a, b in pts)
    return s + (" Z" if close else "")


def uvpath(P, pts, close=True):
    return dpath(P, [W(u, v) for u, v in pts], close)


def rect_uv(P, u0, u1, v0, v1, **kw):
    return '<path d="%s" %s/>' % (uvpath(P, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]),
                                  " ".join('%s="%s"' % (k.replace("_", "-"), v) for k, v in kw.items()))


def txt(P, u, v, s, cls="anS", anchor="middle", dy=0.0, rot=None):
    x, y = P.X(W(u, v)[0]), P.Y(W(u, v)[1]) + dy
    r = ' transform="rotate(%.1f %.1f %.1f)"' % (rot, x, y) if rot else ""
    return '<text x="%.1f" y="%.1f" class="%s" style="text-anchor:%s"%s>%s</text>' % (x, y, cls, anchor, r, esc(s))


def scalebar(P, x, y, m=50):
    px = P.L(m)
    return ('<g><rect x="%.1f" y="%.1f" width="%.1f" height="4" fill="var(--ink)"/>'
            '<rect x="%.1f" y="%.1f" width="%.1f" height="4" fill="var(--paper)" stroke="var(--ink)" stroke-width=".6"/>'
            '<text x="%.1f" y="%.1f" class="sl">0</text>'
            '<text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">%d m</text></g>'
            % (x, y, px / 2, x + px / 2, y, px / 2, x, y - 5, x + px, y - 5, m))


def northmark(P, x, y):
    return ('<g><path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="var(--ink)"/>'
            '<text x="%.1f" y="%.1f" class="sl" style="text-anchor:middle">北</text></g>'
            % (x, y - 15, x - 5, y, x + 5, y, x, y + 12))


def proj(w=980, pad=16):
    xs = [p[0] for p in POLY]; zs = [p[1] for p in POLY]
    return L.Proj(min(xs) - pad, max(xs) + pad, min(zs) - pad, max(zs) + pad, W=w)


def svg(P, body, extra=""):
    return ('<svg viewBox="0 0 %.0f %.0f" %s>%s</svg>'
            % (P.W, P.H, extra, "".join(body)))


_CLIP = [0]
def parcel_layer(P, fill="var(--dan1)"):
    _CLIP[0] += 1
    o = ['<rect x="0" y="0" width="%.0f" height="%.0f" fill="var(--paper2)"/>' % (P.W, P.H)]
    o.append('<defs><clipPath id="kc%d"><path d="%s"/></clipPath></defs>' % (_CLIP[0], dpath(P, POLY)))
    o.append('<path d="%s" fill="%s" stroke="none"/>' % (dpath(P, POLY), fill))
    return o


def clip():
    return ' clip-path="url(#kc%d)"' % _CLIP[0]


def dem_layer(P, key, step=2.0, alpha=1.0):  # 区画の中だけ塗る(セル中心で判定)
    o = []
    x = P.wx0
    while x < P.wx1:
        z = P.wz0
        while z < P.wz1:
            cx, cz = x + step / 2, z + step / 2
            if in_poly(POLY, cx, cz):
                y = H(key, cx, cz)
                if y is not None:
                    o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>'
                             % (P.X(x), P.Y(z + step), P.L(step) + .4, P.L(step) + .4, L.dem_color(y)))
            z += step
        x += step
    return ['<g opacity="%.2f"%s>%s</g>' % (alpha, clip(), "".join(o))]


def iso_layer(P, key, levels):
    o = []
    for lv in levels:
        segs = L._iso(DEM[key], lv)
        dd = []
        for (ax, az), (bx, bz) in segs:
            if not in_poly(POLY, (ax + bx) / 2, (az + bz) / 2):
                continue
            dd.append("M %.1f %.1f L %.1f %.1f" % (P.X(ax), P.Y(az), P.X(bx), P.Y(bz)))
        if dd:
            o.append('<path d="%s" fill="none" stroke="var(--ishi)" stroke-width="%.1f" opacity="%.2f"/>'
                     % (" ".join(dd), 1.5 if lv % 10 == 0 else .6, .9 if lv % 10 == 0 else .5))
    return o


def gate_layer(P, small=False):
    g = d["gate"]; k = d["komon"]
    o = []
    for spec, lab in ((g, "表門"), (k, "通用門")):
        nx_, nz_ = edge_norm(spec["edge"])
        x, z = spec["world"]
        sz = 5.0 if small else 8.0
        px, py = P.X(x), P.Y(z)
        ax, ay = P.X(x + nx_ * 6), P.Y(z + nz_ * 6)
        dx, dy = ax - px, ay - py
        n = math.hypot(dx, dy) or 1
        dx, dy = dx / n, dy / n
        ox, oy = -dy, dx
        o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="var(--shu)"/>'
                 % (px + dx * sz * 1.7, py + dy * sz * 1.7,
                    px + ox * sz, py + oy * sz, px - ox * sz, py - oy * sz))
        if not small:
            o.append('<text x="%.1f" y="%.1f" class="anG" style="text-anchor:end;paint-order:stroke;'
                     'stroke:var(--paper);stroke-width:3px">%s</text>'
                     % (px - dx * sz * 1.2, py - dy * sz * 1.2 + 4, lab))
    return o


# ================================================================ 図版
MUNE_FILL = {"Genkan": "var(--nagaya)", "Ohiroma": "var(--nagaya)", "Shoin": "var(--nagaya)",
             "Nakaoku": "var(--nagaya)", "Daidokoro": "var(--nagaya)", "Okumuki": "var(--nagaya)"}
def mune_fill(m):
    if m["name"].startswith("Kachu"):
        return "var(--hei)"
    if m["name"] in ("Kura1", "Kura2", "Kagokura"):
        return "var(--ishi)"
    if m["name"] in ("Umaya",):
        return "var(--pl-umaya)"
    if m["name"] == "Inari":
        return "var(--shu)"
    return "var(--nagaya)"


ZONE_FILL = {"Shirasu": "var(--shirasu)", "OmoteNiwa": "var(--niwa)", "OkuNiwa": "var(--niwa)",
             "ShuNiwa": "var(--tsuki)", "Juri": "var(--take)", "Baba": "var(--dan3)"}


def zone_path(P, z):
    if "poly" in z:
        return uvpath(P, z["poly"])
    return uvpath(P, [(z["u0"], z["v0"]), (z["u1"], z["v0"]), (z["u1"], z["v1"]), (z["u0"], z["v1"])])


def run_quad(P, r, depth=None):
    """run を辺に沿った帯として描く。depth[間] が無ければ塀の厚みで描く。"""
    e = r["edge"]
    nx_, nz_ = edge_norm(e)
    dep = (depth if depth is not None else d["const"]["dobeiT"] / KEN) * KEN
    a = edge_at(e, r["s0"]); b = edge_at(e, r["s1"])
    pts = [(a[0], a[1]), (b[0], b[1]),
           (b[0] + nx_ * dep, b[1] + nz_ * dep), (a[0] + nx_ * dep, a[1] + nz_ * dep)]
    return dpath(P, pts)


def perim_layer(P, thin=False):
    o = []
    for r in d["runs"]:
        kind = r["kind"]
        dep = r.get("depth")
        if kind == "Nagaya":
            fill, stroke = "var(--nagaya)", "var(--ink)"
        elif kind == "Mon":
            fill, stroke = "var(--shu)", "var(--ink)"
        elif kind == "Komon":
            fill, stroke = "var(--shu)", "var(--ink)"
        else:
            fill, stroke = ("var(--hei)" if r["build"] else "var(--ink-mid)"), "none"
            dep = 0.45 / KEN
        op = 1.0 if r["build"] else 0.55
        o.append('<path d="%s" fill="%s" stroke="%s" stroke-width=".7" opacity="%.2f"/>'
                 % (run_quad(P, r, dep), fill, stroke, op))
    return o


def garden_layer(P, small=False):
    """園路・築山・見所・鳥居。"""
    G = d.get("garden")
    if not G:
        return []
    o = []
    for f in G["features"]:
        if "poly" in f:
            fill = "var(--tsuki)" if f["name"] == "Tsukiyama" else "var(--niwa)"
            o.append('<path d="%s" fill="%s" stroke="var(--roka)" stroke-width=".8" '
                     'stroke-dasharray="3 2" opacity=".85"/>' % (uvpath(P, f["poly"]), fill))
            cu = sum(q[0] for q in f["poly"]) / len(f["poly"])
            cv = sum(q[1] for q in f["poly"]) / len(f["poly"])
            if not small:
                o.append(txt(P, cu, cv, f["ja"].split("(")[0], "anS2", dy=3))
    for pa in G["paths"]:
        o.append('<path d="%s" fill="none" stroke="var(--roka)" stroke-width="%.1f" '
                 'stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="5 3"/>'
                 % (uvpath(P, pa["pts"], False), min(2.6, max(1.4, P.L(pa["w"] * KEN)))))
    for f in G["features"]:
        if f["name"] == "Torii":
            x, z = W(f["u"], f["v"])
            o.append('<path d="M %.1f %.1f L %.1f %.1f M %.1f %.1f L %.1f %.1f" '
                     'stroke="var(--shu)" stroke-width="2.2" fill="none"/>'
                     % (P.X(x) - 5, P.Y(z) - 4, P.X(x) + 5, P.Y(z) - 4,
                        P.X(x) - 4, P.Y(z) - 1, P.X(x) + 4, P.Y(z) - 1))
    for st in G.get("stones", []):
        x, z = W(st["u"], st["v"])
        for i in range(st["n"]):
            r = 3.2 - i * 0.6
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="var(--ishi)" stroke="var(--ink)" '
                     'stroke-width=".6"/>' % (P.X(x) + i * 5.0 - 3, P.Y(z) + (i % 2) * 4.5 - 2, max(1.6, r)))
    for lt in G.get("lanterns", []):
        x, z = W(lt["u"], lt["v"])
        o.append('<path d="M %.1f %.1f l 3 0 l -1.5 -5 Z" fill="var(--ishi)" stroke="var(--ink)" '
                 'stroke-width=".5"/>' % (P.X(x) - 1.5, P.Y(z)))
    for tb in G.get("tobiishi", []):
        pa = next((q for q in G["paths"] if q["name"] == tb["path"]), None)
        if not pa:
            continue
        pts = pa["pts"]
        tot = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])) * KEN
        for i in range(tb["n"]):
            dd = min(tot - 0.01, i * tb["pitch"] + 0.5)
            acc = 0.0
            for a, b in zip(pts, pts[1:]):
                seg = math.hypot(b[0] - a[0], b[1] - a[1]) * KEN
                if acc + seg >= dd:
                    t = (dd - acc) / (seg or 1)
                    x, z = W(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                    o.append('<circle cx="%.1f" cy="%.1f" r="1.7" fill="var(--ishi)"/>' % (P.X(x), P.Y(z)))
                    break
                acc += seg
    for vw in G["views"]:
        x, z = W(vw["u"], vw["v"])
        tx_, tz_ = W(vw["toward"][0], vw["toward"][1])
        o.append('<path d="M %.1f %.1f L %.1f %.1f" stroke="var(--shu)" stroke-width="1.1" '
                 'stroke-dasharray="2 4" fill="none" opacity=".8"/>'
                 % (P.X(x), P.Y(z), P.X(tx_), P.Y(tz_)))
        o.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="var(--paper)" stroke="var(--shu)" stroke-width="2"/>'
                 % (P.X(x), P.Y(z)))
    return o


def haichi_svg(kan):
    P = proj(980)
    o = parcel_layer(P)
    # 郭の外の zone(区画でクリップする)
    o.append('<g%s>' % clip())
    for nm in ("Juri", "ShuNiwa"):
        o.append('<path d="%s" fill="%s" opacity=".8" stroke="none"/>' % (zone_path(P, Z[nm]), ZONE_FILL[nm]))
    o.append('</g>')
    # 段
    o.append('<path d="%s" fill="var(--pl-main)" stroke="var(--ink)" stroke-width="1.1" stroke-dasharray="6 3"/>'
             % uvpath(P, T["T1"]["poly"]))
    t2 = T["T2"]
    o.append(rect_uv(P, t2["u0"], t2["u1"], t2["v0"], t2["v1"],
                     fill="var(--pl-suso)", stroke="var(--ink)", stroke_width="1.1", stroke_dasharray="6 3"))
    # 郭の中の zone
    for nm in ("Shirasu", "OmoteNiwa", "OkuNiwa", "Baba"):
        o.append('<path d="%s" fill="%s" opacity=".75" stroke="none"/>' % (zone_path(P, Z[nm]), ZONE_FILL[nm]))
    o += garden_layer(P)
    # 外周
    o += perim_layer(P)
    # 棟
    for m in d["mune"]:
        o.append(rect_uv(P, m["u0"], m["u1"], m["v0"], m["v1"],
                         fill=mune_fill(m), stroke="var(--ink)", stroke_width="0.9"))
    # 石段
    for k in d["kaidans"]:
        o.append(rect_uv(P, min(k["u0"], k["u1"]), max(k["u0"], k["u1"]),
                         k["vc"] - k["w"] / 2, k["vc"] + k["w"] / 2,
                         fill="var(--ishi)", stroke="var(--ink)", stroke_width="0.8"))
        n = k["steps"]
        for i in range(1, n):
            uu = k["u0"] + (k["u1"] - k["u0"]) * i / n
            o.append('<path d="%s" stroke="var(--paper)" stroke-width=".5" fill="none"/>'
                     % uvpath(P, [(uu, k["vc"] - k["w"] / 2), (uu, k["vc"] + k["w"] / 2)], False))
    # 井戸
    for p in d["points"]:
        x, z = W(p["u"], p["v"])
        o.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="var(--ike)" stroke="var(--ink)" stroke-width=".8"/>'
                 % (P.X(x), P.Y(z)))
    o += gate_layer(P)
    # 注記
    o.append(txt(P, 68, 26, "御殿複合", "mu"))
    o.append(txt(P, 11.5, 9.9, "家中の郭 22.0", "mu"))
    o.append(txt(P, 40, 25, "主庭(自然の窪み)", "mu"))
    o.append(txt(P, 18, 40, "北西の樹林", "mu"))
    o.append(txt(P, 74.5, 36, "白洲", "anS2"))
    o.append(txt(P, 58.5, 43.5, "馬場", "anS2"))
    for m in d["mune"]:
        if m["ken2"] >= 20:
            o.append(txt(P, (m["u0"] + m["u1"]) / 2, (m["v0"] + m["v1"]) / 2, m["ja"], "rmS", dy=4))
    o.append('<path d="%s" fill="none" stroke="var(--ink)" stroke-width="2.2"/>' % dpath(P, POLY))
    o.append(scalebar(P, 16, P.H - 14, 50))
    o.append(northmark(P, P.W - 26, 34))
    return svg(P, o)


def genkyo_svg(key, kan, show_pits=True, sections=True):
    P = proj(980)
    o = parcel_layer(P, fill="var(--paper2)")
    o += dem_layer(P, key)
    o += iso_layer(P, key, [l for l in range(4, 32, 2)])
    o.append('<path d="%s" fill="none" stroke="var(--ink)" stroke-width="2.2"/>' % dpath(P, POLY))
    o.append('<path d="%s" fill="none" stroke="var(--shu)" stroke-width="1.2" stroke-dasharray="7 4"/>'
             % uvpath(P, T["T1"]["poly"]))
    t2 = T["T2"]
    o.append(rect_uv(P, t2["u0"], t2["u1"], t2["v0"], t2["v1"],
                     fill="none", stroke="var(--shu)", stroke_width="1.2", stroke_dasharray="7 4"))
    if sections:
        for sc in SECTIONS:
            a, b = sc["a"], sc["b"]
            o.append('<path d="%s" stroke="var(--shu)" stroke-width="1" stroke-dasharray="9 3 2 3" fill="none"/>'
                     % uvpath(P, [a, b], False))
            o.append(txt(P, a[0], a[1], sc["name"], "anG", dy=-4))
            o.append(txt(P, b[0], b[1], sc["name"] + "′", "anG", dy=-4))
    o += gate_layer(P)
    o.append(txt(P, 68, 10, "上段 27.0", "mu"))
    o.append(txt(P, 11.5, 4.8, "下段 22.0", "mu"))
    o.append(scalebar(P, 16, P.H - 14, 50))
    o.append(northmark(P, P.W - 26, 34))
    return svg(P, o)


def kirimori_svg(kan):
    P = proj(980)
    o = parcel_layer(P, fill="var(--paper2)")
    step = 1.0
    cells = []
    u = -2.0
    while u <= 86:
        v = -2.0
        while v <= 60:
            x, z = W(u + step / 2, v + step / 2)
            if in_poly(POLY, x, z):
                y0 = design_y(u + step / 2, v + step / 2)
                nat = H("edo", x, z)
                if nat is not None:
                    if y0 is None:
                        col = "var(--paper2)"
                    else:
                        col = L.cf_color(y0 - nat)
                    cells.append('<path d="%s" fill="%s"/>'
                                 % (uvpath(P, [(u, v), (u + step, v), (u + step, v + step), (u, v + step)]), col))
            v += step
        u += step
    o.append('<g%s>%s</g>' % (clip(), "".join(cells)))
    o += iso_layer(P, "edo", [l for l in range(10, 30, 2)])
    o.append('<path d="%s" fill="none" stroke="var(--ink)" stroke-width="2.2"/>' % dpath(P, POLY))
    for m in d["mune"]:
        o.append(rect_uv(P, m["u0"], m["u1"], m["v0"], m["v1"],
                         fill="none", stroke="var(--ink)", stroke_width="0.8", stroke_dasharray="3 2"))
    o += gate_layer(P, small=True)
    o.append(scalebar(P, 16, P.H - 14, 50))
    o.append(northmark(P, P.W - 26, 34))
    return svg(P, o)


SECTIONS = [
    {"name": "イ", "a": [0.0, 6.0], "b": [83.0, 6.0], "dir": "西→東", "_": "下段・法面・上段の南半・大台所を通る"},
    {"name": "ロ", "a": [0.0, 36.0], "b": [83.0, 36.0], "dir": "西→東", "_": "表門の軸。北西の斜面・主庭の窪み・玄関棟・白洲・長屋門を通る"},
    {"name": "ハ", "a": [30.0, -1.0], "b": [30.0, 59.0], "dir": "南→北", "_": "奥向棟の西・主庭の窪み・北西の樹林を通る"},
    {"name": "ニ", "a": [66.0, -1.0], "b": [66.0, 59.0], "dir": "南→北", "_": "大台所・表書院・大広間・玄関・厩を通る"},
    {"name": "ホ", "a": [18.0, 2.0], "b": [36.0, 2.0], "dir": "西→東", "lo": 18.0, "hi": 30.0,
     "_": "**石段 K_Nishi の詳細。**下段 22.0 から上段 27.0 へ 18段で上がる。"
          "走りは郭の縁どうしの水平距離そのもので、自然の法面の勾配とほぼ一致する"},
]


def section_svg(sc, w=980, hgt=210, pad=44):
    a, b = sc["a"], sc["b"]
    n = 400
    lo, hi = sc.get("lo", 0.0), sc.get("hi", 32.0)
    def PX(t): return pad + t * (w - pad * 2)
    def PY(y): return hgt - pad - (y - lo) / (hi - lo) * (hgt - pad * 1.5)
    natp, edop, desp, ins = [], [], [], []
    for i in range(n + 1):
        t = i / n
        u = a[0] + (b[0] - a[0]) * t; v = a[1] + (b[1] - a[1]) * t
        x, z = W(u, v)
        inside = in_poly(POLY, x, z)
        ins.append(inside)
        natp.append(H("cur", x, z)); edop.append(H("edo", x, z))
        dy = design_y(u, v) if inside else None
        desp.append(dy)
    o = ['<rect x="0" y="0" width="%d" height="%d" fill="var(--paper2)"/>' % (w, hgt)]
    gstep = 5 if (hi - lo) > 20 else 2
    for gy in range(int(lo), int(hi) + 1, gstep):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--rule)" stroke-width=".7"/>'
                 % (pad, PY(gy), w - pad, PY(gy)))
        o.append('<text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">%d</text>' % (pad - 4, PY(gy) + 3, gy))
    def line(arr, **kw):
        segs = []; cur = []
        for i, y in enumerate(arr):
            if y is None:
                if len(cur) > 1: segs.append(cur)
                cur = []
            else:
                cur.append((PX(i / n), PY(y)))
        if len(cur) > 1: segs.append(cur)
        return "".join('<path d="M %s" fill="none" %s/>'
                       % (" L ".join("%.1f %.1f" % p for p in s),
                          " ".join('%s="%s"' % (k.replace("_", "-"), vv) for k, vv in kw.items())) for s in segs)
    # 江戸期地盤(塗り)
    pts = [(PX(i / n), PY(y)) for i, y in enumerate(edop) if y is not None]
    if pts:
        o.append('<path d="M %s L %.1f %.1f L %.1f %.1f Z" fill="var(--dan3)" stroke="none"/>'
                 % (" L ".join("%.1f %.1f" % p for p in pts), pts[-1][0], PY(lo), pts[0][0], PY(lo)))
    o.append(line(natp, stroke="var(--ishi)", stroke_width="1.0", stroke_dasharray="4 3"))
    o.append(line(edop, stroke="var(--ink)", stroke_width="1.5"))
    o.append(line(desp, stroke="var(--shu)", stroke_width="2.2"))
    # 区画の範囲
    idx = [i for i, q in enumerate(ins) if q]
    if idx:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="var(--shu)" '
                 'stroke-width="1" stroke-dasharray="5 3"/>'
                 % (PX(idx[0] / n), pad * 0.35, PX(idx[-1] / n) - PX(idx[0] / n), hgt - pad - pad * 0.35))
    # 棟の輪郭
    for m in d["mune"]:
        hit = []
        for i in range(n + 1):
            t = i / n
            u = a[0] + (b[0] - a[0]) * t; v = a[1] + (b[1] - a[1]) * t
            if m["u0"] <= u <= m["u1"] and m["v0"] <= v <= m["v1"]:
                hit.append(i)
        if len(hit) > 2:
            y0 = T[m["plane"]]["y"] + d["const"]["gotenFloor"]
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="var(--nagaya)" opacity=".85"/>'
                     % (PX(hit[0] / n), PY(y0 + 4.2), PX(hit[-1] / n) - PX(hit[0] / n), PY(y0) - PY(y0 + 4.2)))
            o.append('<text x="%.1f" y="%.1f" class="jo" style="text-anchor:middle">%s</text>'
                     % ((PX(hit[0] / n) + PX(hit[-1] / n)) / 2, PY(y0 + 4.2) - 3, esc(m["ja"])))
    for k in d["kaidans"]:
        if abs(((a[1] + b[1]) / 2) - k["vc"]) > k["w"] / 2:
            continue
        ua, ub = k["u0"], k["u1"]
        ya, yb = T[k["from"]]["y"], T[k["to"]]["y"]
        pts2 = []
        for i in range(k["steps"] + 1):
            t = i / k["steps"]
            uu = ua + (ub - ua) * t
            yy = ya - (ya - yb) * t
            tt = (uu - a[0]) / ((b[0] - a[0]) or 1)
            pts2.append((PX(tt), PY(yy)))
            if i < k["steps"]:
                tt2 = (ua + (ub - ua) * ((i + 1) / k["steps"]) - a[0]) / ((b[0] - a[0]) or 1)
                pts2.append((PX(tt2), PY(yy)))
        o.append('<path d="M %s" fill="none" stroke="var(--shu)" stroke-width="2"/>'
                 % " L ".join("%.1f %.1f" % q for q in pts2))
        o.append('<text x="%.1f" y="%.1f" class="anG" style="text-anchor:middle">%s %d段 蹴上%.3f 踏面%.3f</text>'
                 % ((PX((ua - a[0]) / ((b[0] - a[0]) or 1)) + PX((ub - a[0]) / ((b[0] - a[0]) or 1))) / 2,
                    PY(ya) - 8, k["ja"], k["steps"], k["keriActual"], k["fumiActual"]))
    o.append('<text x="%.1f" y="%.1f" class="sl">%s–%s′  %s</text>' % (pad, hgt - 8, sc["name"], sc["name"], sc["dir"]))
    o.append('<text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">標高 m ／ 縦横同尺ではない</text>'
             % (w - pad, hgt - 8))
    return '<svg viewBox="0 0 %d %d">%s</svg>' % (w, hgt, "".join(o))


def goten_svg(kan):
    """主郭の御殿平面。室名と畳数を書き入れる。"""
    us = [m["u0"] for m in d["mune"] if m["plane"] == "T1"] + [Z["Shirasu"]["u0"]]
    ue = [m["u1"] for m in d["mune"] if m["plane"] == "T1"] + [Z["Shirasu"]["u1"]]
    vs = [m["v0"] for m in d["mune"] if m["plane"] == "T1"]
    ve = [m["v1"] for m in d["mune"] if m["plane"] == "T1"]
    u0, u1, v0, v1 = min(us) - 3, max(ue) + 4, min(vs) - 3, max(ve) + 3
    (x0, z0) = W(u0, v0); (x1, z1) = W(u1, v1)
    P = L.Proj(min(x0, x1), max(x0, x1), min(z0, z1), max(z0, z1), W=980)
    o = ['<rect x="0" y="0" width="%.0f" height="%.0f" fill="var(--paper2)"/>' % (P.W, P.H)]
    # 間グリッド
    gl = []
    u = math.ceil(u0)
    while u <= u1:
        gl.append(uvpath(P, [(u, v0), (u, v1)], False)); u += 1
    v = math.ceil(v0)
    while v <= v1:
        gl.append(uvpath(P, [(u0, v), (u1, v)], False)); v += 1
    o.append('<path d="%s" stroke="var(--grid)" stroke-width=".4" fill="none"/>' % " ".join(gl))
    o.append('<path d="%s" fill="var(--pl-main)" opacity=".5" stroke="var(--ink)" stroke-width="1" stroke-dasharray="6 3"/>'
             % uvpath(P, T["T1"]["poly"]))
    for z in d["zones"]:
        if z["name"] in ("Shirasu", "OmoteNiwa", "OkuNiwa", "Baba"):
            o.append('<path d="%s" fill="%s" opacity=".65"/>' % (zone_path(P, z), ZONE_FILL[z["name"]]))
    o += garden_layer(P, small=True)
    o += perim_layer(P)
    for m in d["mune"]:
        if m["plane"] != "T1":
            continue
        o.append(rect_uv(P, m["u0"], m["u1"], m["v0"], m["v1"],
                         fill="var(--paper)", stroke="var(--ink)", stroke_width="1.4"))
        for r in m.get("rooms", []):
            o.append(rect_uv(P, r["u0"], r["u1"], r["v0"], r["v1"],
                             fill="var(--dan2)", stroke="var(--ink)", stroke_width=".7", stroke_dasharray="4 2"))
            cu, cv = (r["u0"] + r["u1"]) / 2, (r["v0"] + r["v1"]) / 2
            o.append(txt(P, cu, cv, r["ja"], "rmS", dy=-1))
            o.append(txt(P, cu, cv, "%d畳" % r["jo"], "jo", dy=11))
        o.append('<text x="%.1f" y="%.1f" class="anS2" style="paint-order:stroke;stroke:var(--paper);'
                 'stroke-width:3.5px">%s</text>'
                 % (P.X(W((m["u0"] + m["u1"]) / 2, m["v1"])[0]), P.Y(W(0, m["v1"])[1]) + 11, esc(m["ja"])))
    # 御錠口
    o.append('<path d="%s" stroke="var(--shu)" stroke-width="3" fill="none"/>'
             % uvpath(P, [(50.0, 10.2), (50.0, 11.8)], False))
    o.append('<text x="%.1f" y="%.1f" class="anG" style="text-anchor:middle;paint-order:stroke;'
             'stroke:var(--paper);stroke-width:3.5px">御錠口</text>'
             % (P.X(W(50.0, 12.4)[0]), P.Y(W(0, 12.4)[1]) - 3))
    for p in d["points"]:
        if p["u"] < u0 or p["u"] > u1:
            continue
        x, z = W(p["u"], p["v"])
        o.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="var(--ike)" stroke="var(--ink)" stroke-width=".8"/>'
                 % (P.X(x), P.Y(z)))
        o.append(txt(P, p["u"], p["v"], p["ja"], "jo", dy=-7))
    o += gate_layer(P)
    o.append(txt(P, 74.5, 36, "白洲", "mu"))
    o.append(txt(P, 58.5, 24, "表向の前庭", "mu", rot=-90))
    o.append(scalebar(P, 16, P.H - 14, 20))
    o.append(northmark(P, P.W - 26, 34))
    return svg(P, o)


def kachu_svg(kan):
    """家中の郭(下段)の平面。"""
    t2 = T["T2"]
    u0, u1, v0, v1 = t2["u0"] - 4, t2["u1"] + 8, t2["v0"] - 3, t2["v1"] + 4
    (x0, z0) = W(u0, v0); (x1, z1) = W(u1, v1)
    P = L.Proj(min(x0, x1), max(x0, x1), min(z0, z1), max(z0, z1), W=760)
    o = ['<rect x="0" y="0" width="%.0f" height="%.0f" fill="var(--paper2)"/>' % (P.W, P.H)]
    gl = []
    u = math.ceil(u0)
    while u <= u1:
        gl.append(uvpath(P, [(u, v0), (u, v1)], False)); u += 1
    v = math.ceil(v0)
    while v <= v1:
        gl.append(uvpath(P, [(u0, v), (u1, v)], False)); v += 1
    o.append('<path d="%s" stroke="var(--grid)" stroke-width=".4" fill="none"/>' % " ".join(gl))
    o += iso_layer(P, "edo", [l for l in range(18, 30, 1)])
    o.append(rect_uv(P, t2["u0"], t2["u1"], t2["v0"], t2["v1"],
                     fill="var(--pl-suso)", opacity=".8", stroke="var(--ink)", stroke_width="1.2", stroke_dasharray="6 3"))
    o.append('<path d="%s" fill="var(--pl-main)" opacity=".45" stroke="var(--ink)" stroke-width="1" stroke-dasharray="6 3"/>'
             % uvpath(P, T["T1"]["poly"]))
    o += perim_layer(P)
    for m in d["mune"]:
        if m["plane"] != "T2" and m["name"] != "KachuS":
            continue
        o.append(rect_uv(P, m["u0"], m["u1"], m["v0"], m["v1"],
                         fill="var(--paper)", stroke="var(--ink)", stroke_width="1.3"))
        o.append(txt(P, (m["u0"] + m["u1"]) / 2, (m["v0"] + m["v1"]) / 2, m["ja"], "rmS", dy=4))
    for k in d["kaidans"]:
        o.append(rect_uv(P, min(k["u0"], k["u1"]), max(k["u0"], k["u1"]),
                         k["vc"] - k["w"] / 2, k["vc"] + k["w"] / 2,
                         fill="var(--ishi)", stroke="var(--ink)", stroke_width="0.9"))
        n = k["steps"]
        for i in range(1, n):
            uu = k["u0"] + (k["u1"] - k["u0"]) * i / n
            o.append('<path d="%s" stroke="var(--paper)" stroke-width=".6" fill="none"/>'
                     % uvpath(P, [(uu, k["vc"] - k["w"] / 2), (uu, k["vc"] + k["w"] / 2)], False))
        o.append('<text x="%.1f" y="%.1f" class="anG" style="text-anchor:middle;paint-order:stroke;'
                 'stroke:var(--paper);stroke-width:3.5px">%s %d段 落差%.1fm</text>'
                 % (P.X(W((k["u0"] + k["u1"]) / 2, 0)[0]), P.Y(W(0, k["vc"] + k["w"] / 2)[1]) - 6,
                    esc(k["ja"]), k["steps"], k["drop"]))
    for p in d["points"]:
        if not (u0 <= p["u"] <= u1):
            continue
        x, z = W(p["u"], p["v"])
        o.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="var(--ike)" stroke="var(--ink)" stroke-width=".8"/>'
                 % (P.X(x), P.Y(z)))
        o.append(txt(P, p["u"], p["v"], p["ja"], "jo", dy=-7))
    o.append(txt(P, 11.5, 9.6, "家中の郭 22.0", "mu"))
    o.append(txt(P, 28.5, 13.0, "主郭 27.0", "mu"))
    o.append(scalebar(P, 16, P.H - 14, 20))
    o.append(northmark(P, P.W - 26, 34))
    return svg(P, o)


def doro_svg(kan):
    """動線図。"""
    P = proj(980)
    o = parcel_layer(P, fill="var(--paper2)")
    o.append('<path d="%s" fill="var(--dan1)" stroke="var(--rule)" stroke-width="1"/>' % uvpath(P, T["T1"]["poly"]))
    t2 = T["T2"]
    o.append(rect_uv(P, t2["u0"], t2["u1"], t2["v0"], t2["v1"], fill="var(--dan1)", stroke="var(--rule)", stroke_width="1"))
    o += perim_layer(P)
    for m in d["mune"]:
        o.append(rect_uv(P, m["u0"], m["u1"], m["v0"], m["v1"], fill="var(--dan3)", stroke="var(--rule)", stroke_width=".6"))
    COL = {"omote": "#A8452C", "yaku": "#3E6A8C", "katte": "#7A6A2A", "oku": "#7A3A6A", "kachu": "#3E7A55"}
    for r in d["routes"]:
        c = COL[r["color"]]
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.6" stroke-linejoin="round" '
                 'stroke-linecap="round" opacity=".9"/>' % (uvpath(P, r["pts"], False), c))
        a = r["pts"][0]
        x, z = W(a[0], a[1])
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (P.X(x), P.Y(z), c))
        b = r["pts"][-1]
        x, z = W(b[0], b[1])
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--paper)" stroke="%s" stroke-width="2"/>'
                 % (P.X(x), P.Y(z), c))
    o += gate_layer(P, small=True)
    o.append(scalebar(P, 16, P.H - 14, 50))
    o.append(northmark(P, P.W - 26, 34))
    return svg(P, o)


def tenkai_svg(kan, w=980):
    """外周の展開図 — 辺ごとに run の座を横に並べる。"""
    order = [3, 4, 5, 6, 0, 1, 2]
    tot = sum(d["edgeLen"][str(e)] for e in order)
    pad, hgt = 46, 300
    lo, hi = 4.0, 32.0
    def PY(y): return hgt - pad - (y - lo) / (hi - lo) * (hgt - pad * 1.6)
    o = ['<rect x="0" y="0" width="%d" height="%d" fill="var(--paper2)"/>' % (w, hgt)]
    for gy in range(5, 33, 5):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--rule)" stroke-width=".7"/>'
                 % (pad, PY(gy), w - pad, PY(gy)))
        o.append('<text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">%d</text>' % (pad - 4, PY(gy) + 3, gy))
    acc = 0.0
    sc = (w - pad * 2) / tot
    for e in order:
        Lm = d["edgeLen"][str(e)]
        x0 = pad + acc * sc; x1 = pad + (acc + Lm) * sc
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--rule)" stroke-width="1"/>'
                 % (x0, pad * 0.5, x0, hgt - pad))
        nm = {0: "西辺", 1: "北西辺", 2: "北辺", 3: "東辺(表門)", 4: "南東の切欠き", 5: "同(南北)", 6: "南辺"}[e]
        o.append('<text x="%.1f" y="%.1f" class="sl" style="text-anchor:middle">%s</text>'
                 % ((x0 + x1) / 2, pad * 0.5 - 4, nm))
        for r in sorted([q for q in d["runs"] if q["edge"] == e], key=lambda q: q["s0"]):
            a = pad + (acc + r["s0"]) * sc; b = pad + (acc + r["s1"]) * sc
            seat = r["seat"]
            top = seat + (d["const"]["dobeiH"] if r["kind"] == "Neribei" else 4.2)
            fill = {"Neribei": "var(--hei)", "Nagaya": "var(--nagaya)",
                    "Mon": "var(--shu)", "Komon": "var(--shu)"}[r["kind"]]
            op = 1.0 if r.get("build", True) else .5
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="%.2f" '
                     'stroke="var(--ink)" stroke-width=".4"/>'
                     % (a, PY(top), b - a, PY(seat) - PY(top), fill, op))
            if "natLo" in r:
                o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="var(--ishi)" opacity="%.2f"/>'
                         % (a, PY(seat), b - a, max(0.0, PY(min(r["natLo"], seat)) - PY(seat)), op * .85))
                o.append('<path d="M %.1f %.1f L %.1f %.1f" stroke="var(--ink)" stroke-width="1" '
                         'stroke-dasharray="3 2" fill="none"/>' % (a, PY(r["natHi"]), b, PY(r["natLo"])))
        acc += Lm
    o.append('<text x="%.1f" y="%.1f" class="sl">■ 練塀 ■ 表長屋 ■ 門 ／ 灰=基壇石垣(座−素地) ／ 破線=江戸期地盤</text>'
             % (pad, hgt - 8))
    o.append('<text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">薄い run は隣家が持つ辺</text>'
             % (w - pad, hgt - 8))
    return '<svg viewBox="0 0 %d %d">%s</svg>' % (w, hgt, "".join(o))


# ================================================================ 表と検査
def tbl(head, rows, cls=""):
    h = ['<div class="tw"><table%s><thead><tr>' % ((' class="%s"' % cls) if cls else "")]
    for c in head:
        h.append('<th%s>%s</th>' % (' class="note"' if c.startswith("*") else "", esc(c.lstrip("*"))))
    h.append("</tr></thead><tbody>")
    for r in rows:
        h.append("<tr>")
        for c in r:
            cl = ""
            s = str(c)
            if s.startswith("*"):
                cl, s = ' class="note"', L.inline(s[1:])
            h.append("<td%s>%s</td>" % (cl, s))
        h.append("</tr>")
    h.append("</tbody></table></div>")
    return "".join(h)


def grid_scan(pred, y0, step=0.25):
    ds = []
    u = -2.0
    while u <= 86:
        v = -2.0
        while v <= 60:
            if pred(u, v):
                x, z = W(u, v)
                if in_poly(POLY, x, z):
                    nat = H("edo", x, z)
                    if nat is not None:
                        ds.append(y0 - nat)
            v += step
        u += step
    return ds


CELL = None
def cutfill(name):
    t = T[name]
    y0 = t["y"]
    step = 0.25
    cell = (step * KEN) ** 2
    f = c = mf = mc = 0.0; n = 0
    u = -2.0
    while u <= 86:
        v = -2.0
        while v <= 60:
            if in_terrace(name, u, v):
                x, z = W(u, v)
                if in_poly(POLY, x, z):
                    nat = H("edo", x, z)
                    if nat is not None:
                        n += 1
                        dv = y0 - nat
                        if dv > 0: f += dv * cell; mf = max(mf, dv)
                        else: c += -dv * cell; mc = max(mc, -dv)
            v += step
        u += step
    return dict(area=n * cell, fill=f, cut=c, maxfill=mf, maxcut=mc)


def planes_table():
    rows = []
    tot = [0.0, 0.0]
    for nm in ("T1", "T2"):
        r = cutfill(nm); t = T[nm]
        tot[0] += r["fill"]; tot[1] += r["cut"]
        ds = grid_scan(lambda u, v, n=nm: in_terrace(n, u, v), t["y"])
        ok = 100.0 * sum(1 for q in ds if abs(q) <= 0.5) / len(ds)
        rows.append([t["ja"], "%.1f" % t["y"], "{:,.0f}".format(r["area"]),
                     "{:,.0f}".format(r["area"] / TSUBO), "{:,.0f}".format(r["fill"]),
                     "%.2f" % r["maxfill"], "{:,.0f}".format(r["cut"]), "%.2f" % r["maxcut"],
                     "%.1f%%" % ok])
    rows.append(["<b>合計</b>", "—", "{:,.0f}".format(sum(cutfill(n)["area"] for n in ("T1", "T2"))),
                 "{:,.0f}".format(sum(cutfill(n)["area"] for n in ("T1", "T2")) / TSUBO),
                 "<b>{:,.0f}</b>".format(tot[0]), "—", "<b>{:,.0f}</b>".format(tot[1]), "—",
                 "差引 {:+,.0f} m³".format(tot[0] - tot[1])])
    return tbl(["面(郭)", "面の高さ m", "面積 m²", "坪", "盛土 m³", "最大盛 m", "切土 m³", "最大切 m",
                "|Δ|≤0.5m"], rows)


def mune_table():
    rows = []
    tot = 0.0
    for m in d["mune"]:
        y0 = T[m["plane"]]["y"]
        ds = grid_scan(lambda u, v, m=m: m["u0"] <= u <= m["u1"] and m["v0"] <= v <= m["v1"], y0)
        tot += (m["u1"] - m["u0"]) * (m["v1"] - m["v0"])
        rows.append([m["ja"], T[m["plane"]]["ja"],
                     "%.1f×%.1f" % (m["u1"] - m["u0"], m["v1"] - m["v0"]),
                     "%.1f" % ((m["u1"] - m["u0"]) * (m["v1"] - m["v0"])),
                     "%.2f 〜 %.2f" % (min(ds), max(ds)),
                     "%.0f%%" % (100.0 * sum(1 for q in ds if abs(q) <= 0.5) / len(ds)),
                     "*" + m["_"]])
    return tbl(["棟", "面", "桁行×梁間 間", "坪", "Δ=設計面−地形 m", "|Δ|≤0.5", "*覚"], rows)


def runs_table():
    rows = []
    NM = {0: "西", 1: "北西", 2: "北", 3: "東(表門)", 4: "南東(切欠)", 5: "南東(切欠)", 6: "南"}
    OW = {"kyogoku": "当家", "niwa": "丹羽", "naito": "内藤"}
    for r in sorted(d["runs"], key=lambda q: (q["edge"], q["s0"])):
        ex = ("%+.2f 〜 %+.2f" % tuple(r["expose"])) if "expose" in r else "—"
        rows.append([NM[r["edge"]], r["name"], r["ja"],
                     "%.2f–%.2f" % (r["s0"], r["s1"]), "%.2f" % (r["s1"] - r["s0"]),
                     "%.1f" % r["seat"], ex, OW[r["owner"]], "建てる" if r["build"] else "—"])
    return tbl(["辺", "run", "種別", "s (m)", "延長 m", "座 m", "基壇の露出 m", "持ち主", "当家の実装"], rows)


def program_table():
    rows = []
    for p in d["program"]:
        by = "、".join(p["by"]) if p["by"] else "—"
        rows.append([p["role"], p["need"], by, p["cert"], "、".join(p["src"]) or "—", "*" + p["_"]])
    return tbl(["役割", "要否", "棟・zone", "確度", "典拠", "*覚"], rows)


def routes_table():
    rows = []
    for r in d["routes"]:
        Lm = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(r["pts"], r["pts"][1:])) * KEN
        ys = [design_y(u, v) for u, v in r["pts"]]
        ys = [q for q in ys if q is not None]
        rise = (max(ys) - min(ys)) if ys else 0.0
        rows.append([r["ja"], "%.0f m" % Lm, "%.1f m" % rise, "%d 段" % r["steps"], "*" + r["_"]])
    return tbl(["系統", "延長", "昇り", "越える石段", "*経路"], rows)


def kenpei():
    tot = 0.0
    rows = []
    for m in d["mune"]:
        a = (m["u1"] - m["u0"]) * (m["v1"] - m["v0"]); tot += a
        rows.append([m["ja"], "%.1f" % a])
    for r in d["runs"]:
        if r["kind"] in ("Nagaya", "Mon"):
            a = (r["s1"] - r["s0"]) / KEN * r.get("depth", 3.0); tot += a
            rows.append([r["ja"] + " " + r["name"], "%.1f" % a])
    return tot, rows


def checks_run():
    out = []
    # C1 棟の重なり
    n = 0
    for a, b in itertools.combinations(d["mune"], 2):
        du = min(a["u1"], b["u1"]) - max(a["u0"], b["u0"])
        dv = min(a["v1"], b["v1"]) - max(a["v0"], b["v0"])
        if du > 1e-9 and dv > 1e-9:
            n += 1
    out.append(("C1", "棟どうしの重なり", "%d 件" % n, n == 0))
    # C2 室
    bad = 0; nr = 0
    for m in d["mune"]:
        rs = m.get("rooms", []); nr += len(rs)
        for r in rs:
            if not (m["u0"] - 1e-9 <= r["u0"] and r["u1"] <= m["u1"] + 1e-9
                    and m["v0"] - 1e-9 <= r["v0"] and r["v1"] <= m["v1"] + 1e-9):
                bad += 1
        for a, b in itertools.combinations(rs, 2):
            du = min(a["u1"], b["u1"]) - max(a["u0"], b["u0"])
            dv = min(a["v1"], b["v1"]) - max(a["v0"], b["v0"])
            if du > 1e-9 and dv > 1e-9:
                bad += 1
    out.append(("C2", "室が棟に収まる / 室どうしが重ならない(全 %d 室)" % nr, "%d 件" % bad, bad == 0))
    # C3 棟が段の中
    bad = 0
    for m in d["mune"]:
        for u, v in [(m["u0"] + .05, m["v0"] + .05), (m["u1"] - .05, m["v0"] + .05),
                     (m["u0"] + .05, m["v1"] - .05), (m["u1"] - .05, m["v1"] - .05)]:
            if not in_terrace(m["plane"], u, v):
                bad += 1
    out.append(("C3", "棟が段の中に収まる", "%d 件" % bad, bad == 0))
    # C4
    worst = 0.0; nbad = 0
    for m in d["mune"]:
        ds = grid_scan(lambda u, v, m=m: m["u0"] <= u <= m["u1"] and m["v0"] <= v <= m["v1"], T[m["plane"]]["y"])
        pc = 100.0 * sum(1 for q in ds if abs(q) <= 0.5) / len(ds)
        worst = max(worst, max(abs(min(ds)), abs(max(ds))))
        if pc < 100.0:
            nbad += 1
    out.append(("C4", "棟の下で |設計面−江戸期地盤| ≤ 0.5m", "不合格の棟 %d / 最大 %.2f m" % (nbad, worst), nbad == 0))
    # C5 run の連続
    gaps = 0
    for e in range(7):
        rs = sorted([q for q in d["runs"] if q["edge"] == e], key=lambda q: q["s0"])
        Lm = d["edgeLen"][str(e)]
        if abs(rs[0]["s0"]) > 1e-6: gaps += 1
        for a, b in zip(rs, rs[1:]):
            if abs(a["s1"] - b["s0"]) > 1e-6: gaps += 1
        if abs(rs[-1]["s1"] - Lm) > 1e-6: gaps += 1
    out.append(("C5", "外周 run が辺の全長を隙間なく覆う", "隙間 %d 件" % gaps, gaps == 0))
    # C6 座が素地を下回らない(郭の縁の切土を除く)
    bad = []
    for r in d["runs"]:
        if "expose" not in r: continue
        if r["expose"][0] < -0.001 and r["seat"] not in (27.0, 22.0):
            bad.append(r["name"])
    out.append(("C6", "run の座が素地を下回らない(郭の縁の切土を除く)", "%d 件" % len(bad), not bad))
    # C7 造成が区画の外へ出ない
    outside = 0
    u = -4.0
    while u <= 88:
        v = -4.0
        while v <= 62:
            if design_y(u, v) is not None:
                x, z = W(u, v)
                if not in_poly(POLY, x, z):
                    outside += 1
            v += .5
        u += .5
    out.append(("C7", "段が区画の外へ出ない", "%d セル" % outside, outside == 0))
    # C8 建蔽率
    tot, _ = kenpei()
    out.append(("C8", "建蔽率(分母=敷地全体 %s 坪)" % "{:,.0f}".format(AREA / TSUBO),
                "%.1f%%" % (100 * tot / (AREA / TSUBO)), True))
    # C9 動線が棟を貫かない
    hit = 0
    for r in d["routes"]:
        for a, b in zip(r["pts"], r["pts"][1:]):
            for t in [i / 20.0 for i in range(21)]:
                u = a[0] + (b[0] - a[0]) * t; v = a[1] + (b[1] - a[1]) * t
                for m in d["mune"]:
                    if m["name"].startswith("Kachu") or m["name"] in ("Kura1", "Kura2", "Umaya", "Kagokura", "Inari"):
                        if m["u0"] + .2 < u < m["u1"] - .2 and m["v0"] + .2 < v < m["v1"] - .2:
                            hit += 1
    out.append(("C9", "動線が御殿以外の棟を貫かない", "%d 点" % hit, hit == 0))
    # C10 program
    miss = [p["role"] for p in d["program"] if p["need"].startswith("必須") and not p["by"]]
    out.append(("C10", "『必須』の役割がすべて棟・zone に結び付く", "欠 %d" % len(miss), not miss))
    return out


# ================================================================ 組み立て
def plate(h, kan, title, meta=""):
    h.append('<div class="plate"><div class="phead"><h2>%s　%s</h2><span class="meta">%s</span></div>'
             % (kan, esc(title), esc(meta)))


def fig(h, s, legend="", cap=""):
    h.append('<div class="fig">%s</div>' % s)
    if legend:
        h.append('<div class="legend">%s</div>' % legend)
    if cap:
        h.append('<p class="cap">%s</p>' % cap)


def main():
    css = open(os.path.join(HERE, "sashizu.css"), encoding="utf-8").read()
    prose = L.md2html(open(MD, encoding="utf-8").read())
    n = [0]
    def nx():
        n[0] += 1
        return KAN[n[0] - 1]

    h = ['<meta charset="utf-8">', "<title>京極備中守上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">丹後峯山藩 一万一千百四十四石 ／ 菊間詰(譜代格) ／ 安政三年</p>')
    h.append("<h1>京極備中守 上屋敷 指図</h1>")
    tot, krows = kenpei()
    h.append('<p class="lede">永田町、山王社の東の台地。道に面するのは<b>東辺だけ</b>で、'
             '北と西は丹羽左京大夫(二本松藩)、南は内藤紀伊守(村上藩)と背中合わせに接する。'
             '敷地は<b>東の台地(上段)と南西の一段低い平場(下段)の二段</b>からなり、'
             '西の窪みと北西の斜面は造成せずに庭と樹林に使う。'
             '<b>数値の正典は <code>kyogoku_bitchu_sashizu.json</code>、文章の正典は '
             '<code>kyogoku_bitchu_kosho.md</code>。</b>この頁はその二つと地盤の三枚から組んだもので、'
             '実装は読んでいない。</p>')
    h.append('<div class="box"><p><b>敷地 %s 坪</b>(%s m²)【区画は町割の正典 <code>parcels.json</code> の '
             '<code>sannobuke_kyogoku</code> — 2026-08-30 にユーザーが敷地割ツールで引き直した・確度U】。'
             '元文三年の拝領坪数の規定は 1〜2万石で 2,500 坪だが、'
             '⚠ <b>区画がユーザー由来(U)なので、実測坪と規定坪の比を格の議論に使わない</b>。'
             '<b>建蔽率 %.1f%%</b>(分母=敷地全体・CLAUDE.md 規則6。⛔ 可建地に替えない)。'
             '敷地の半分あまりが斜面と窪みで、そこには棟を置かない。</p></div>'
             % ("{:,.0f}".format(AREA / TSUBO), "{:,.0f}".format(AREA), 100 * tot / (AREA / TSUBO)))

    # 其一 配置図
    plate(h, nx(), "敷地全体 配置図", "北が上 ／ 段・棟・外周・門・庭")
    fig(h, haichi_svg(KAN[n[0] - 1]),
        legend='<span style="color:var(--nagaya)">■ 御殿複合・表長屋</span>'
               '<span style="color:var(--hei)">■ 家中長屋・練塀</span>'
               '<span style="color:var(--ishi)">■ 土蔵・石段</span>'
               '<span style="color:var(--shu)">▶ 門</span>'
               '<span>■ 白洲</span><span style="color:var(--take)">■ 樹林</span>'
               '<span style="color:#7f8f6f">■ 主庭(造成しない窪み)</span>'
               '<span style="color:var(--roka)">╌ 園路</span>'
               '<span style="color:var(--shu)">○┈ 見所と視線 ／ ⛩ 鳥居</span>',
        cap="<b>表門を入って北東から南西へ、表向 → 中奥 → 奥向 が一列に連続する</b>"
            "([西川1959]A)。台地がΓ形なので、表向は東の腕に、中奥・奥向・勝手は南の広いブロックに割れる。"
            "薄く描いた練塀は<b>隣家が持つ辺</b>(⚠ 未裁定・P2)。")
    h.append(planes_table())
    h.append('<p class="cap"><b>面の高さは設計者が決めていない。</b>江戸期復元地盤を 0.5間で走査し、'
             '起伏の小さい矩形を探してその高さをそのまま採った(<code>sashizu.md</code> §3a)。'
             '⭐ <b>土留めは1本も要らない</b> — 二つの郭はどちらも自然のベンチに載り、'
             '郭の縁が自然の法肩・法尻と一致する。</p>')
    G = d["garden"]
    h.append("<h3>庭 — 見所と園路</h3>")
    h.append(tbl(["見所", "位置 (u,v)", "見る先", "比高 m", "水平 m", "俯角", "*覚"],
                 [[v["ja"], "(%.0f, %.0f)" % (v["u"], v["v"]), "(%.0f, %.0f)" % tuple(v["toward"]),
                   "%+.1f" % v["drop"], "%.1f" % v["dist"], "%.1f°" % v["angle"], "*" + v["_"]]
                  for v in G["views"]]))
    def _uvarea(pp):
        return abs(sum(pp[i][0] * pp[(i + 1) % len(pp)][1] - pp[(i + 1) % len(pp)][0] * pp[i][1]
                       for i in range(len(pp)))) / 2.0
    rows = [[p2["ja"],
             "%.0f m" % (sum(math.hypot(b[0] - a[0], b[1] - a[1])
                             for a, b in zip(p2["pts"], p2["pts"][1:])) * KEN),
             "%.1f" % p2["w"], "*" + p2["_"]] for p2 in G["paths"]]
    for f in G["features"]:
        where = ("(%.1f, %.1f)" % (f["u"], f["v"])) if "u" in f else ("%.0f 坪" % _uvarea(f["poly"]))
        rows.append([f["ja"], where, "—", "*" + f["_"]])
    h.append(tbl(["園路・点景", "延長 / 位置", "幅 間", "*覚"], rows))
    h.append("<h4>植栽 — 帯ごとの樹種と本数</h4>")
    h.append(tbl(["場", "帯", "高さ m", "何を", "本数", "*在庫 / 覚"],
                 [[z["ja"], b["band"], b["y"], b["what"], ("%d" % b["n"]) if b["n"] else "—",
                   "*" + "<br>".join("<code>%s</code>" % esc(a) for a in b["asset"]) + "<br>" + b["_"]]
                  for z in G["planting"] for b in z["bands"]]))
    h.append("<h4>石組・灯籠・飛石</h4>")
    rows2 = []
    for st in G.get("stones", []):
        rows2.append(["石組", st["ja"], "(%.1f, %.1f)" % (st["u"], st["v"]), "%d 石" % st["n"],
                      "*" + "<code>%s</code><br>%s" % (esc(st["asset"][0]), st["_"])])
    for lt in G.get("lanterns", []):
        rows2.append(["灯籠", "%s(%s)" % (lt["ja"], lt["form"]), "(%.1f, %.1f)" % (lt["u"], lt["v"]),
                      "%d 基" % lt.get("n", 1),
                      "*" + "<code>%s</code><br>%s" % (esc(lt["asset"][0]), lt["_"])])
    for tb in G.get("tobiishi", []):
        rows2.append(["飛石", tb["ja"], tb["path"], "%d 枚 / 芯々 %.1f m" % (tb["n"], tb["pitch"]),
                      "*" + "<code>%s</code><br>%s" % (esc(tb["asset"][0]), tb["_"])])
    h.append(tbl(["種", "名", "位置 (u,v)", "数", "*在庫 / 覚"], rows2))
    h.append('<p class="cap">⚠ <b>庭方(edo-niwashi)の検分をまだ通していない。</b>'
             '確度はすべて U(設計判断)。⭐ <b>主景は自然の高まり</b>で、'
             '⛔ 盛りも削りもしない(§B-1「肩の高まりは築山に使う」)。</p>')
    h.append("</div>")

    # 其二 現況図
    plate(h, nx(), "現況図 — 江戸期の復元地盤", "段彩 2m ／ 等高線 2m(10m 太線) ／ 確度P")
    fig(h, genkyo_svg("edo", KAN[n[0] - 1]), legend=L.dem_legend(),
        cap="<b>造成のすべての出発点。</b>正本 <code>base_dem.json</code>(国土地理院 DEM5A/10B 由来・"
            "造成を一切含まない<b>現代</b>の地面)に、<code>kyogoku_bitchu_edo_recon.json</code> の手順で"
            "近代の掘削を戻したもの。朱の破線が二つの郭、一点鎖線が断面の切り位置。"
            "<br>⚠ <b>これは「今日の地面から近代の掘削を戻した面」であって、江戸の地面そのものではない。</b>"
            "戻した範囲は 2026-08-31 のユーザー裁定B による。")
    plate(h, nx(), "現況図 — 今日の地面(復元前)", "同じ枠・同じ段彩で並べて読む")
    fig(h, genkyo_svg("cur", KAN[n[0] - 1], sections=False),
        cap="<b>上の図との差が復元の量。</b>台地の縁に食い込む窪みと西辺の窪みが埋まり、"
            "北西隅の掘り込みが谷底の高さまで上がる。⛔ 北西の<b>谷そのもの</b>は残す"
            "(山王下の谷筋。谷ごと埋めると隣の丹羽・社人八家の地形と食い違う)。")

    # 其四 切盛図
    plate(h, nx(), "切盛図", "暖色=盛土 ／ 寒色=切土 ／ 無彩=±0.3m ／ 地の色=造成しない")
    fig(h, kirimori_svg(KAN[n[0] - 1]), legend=L.cutfill_legend(),
        cap="<b>造成は二つの郭の中だけ。</b>郭の外(法面・窪み・斜面)は一切さわらない。"
            "破線は棟の輪郭 — <b>棟が載る所はすべて ±0.5m に収まる</b>(其一の表)。")

    # 其五 断面
    plate(h, nx(), "断面", "実線=江戸期地盤 ／ 破線=今日の地面 ／ 朱=設計の面 ／ 朱の破線枠=区画")
    for sc in SECTIONS:
        h.append('<h4>%s–%s′(%s)　%s</h4>' % (sc["name"], sc["name"], sc["dir"], sc["_"]))
        h.append('<div class="fig">%s</div>' % section_svg(sc))
    h.append("</div>")

    # 其六 御殿平面
    plate(h, nx(), "主郭 御殿平面", "室名と畳数 ／ 細い格子は江戸間 1間=1.818m")
    fig(h, goten_svg(KAN[n[0] - 1]),
        cap="<b>室名を書いていない部分は入側(縁)。</b>棟と棟は襖ではなく渡廊下・接続でつなぐ。"
            "⛔ <b>中央を突っ切る通路は明治以降の型</b>なので採らない — 廊下は室群の外周を巡る入側にする。"
            "御錠口から西は奥向で、<b>藩士は入れない</b>。")
    h.append(mune_table())

    # 其七 家中の郭
    plate(h, nx(), "家中の郭(下段)と石段", "面 22.0m ／ 主郭とは落差 5.0m")
    fig(h, kachu_svg(KAN[n[0] - 1]),
        cap="2026-08-31 ユーザー裁定1=A。<b>石段の走りは郭の縁どうしの水平距離そのもの</b>で、"
            "自然の法面の勾配とほぼ一致するので掘割はごく浅い。"
            "石段は主郭の南縁の勝手道の延長に採り、<b>奥向の前を通らせない</b>。")

    # 其八 外周の展開
    plate(h, nx(), "外周の展開", "左から 東辺(表門)→南東→南→西→北西→北。横は辺の走り、縦は標高")
    fig(h, tenkai_svg(KAN[n[0] - 1]),
        cap="<b>斜面では水平な run を段違いに連ねる。</b>練塀は版築なので壁面が水平にしかならず、"
            "勾配なりに傾けられない。<b>座はその run の素地の最大</b>に採り、差は基壇石垣が受ける"
            "(⛔ 中央値に採ると塀の根が埋まる区間ができる)。"
            "薄い run は隣家が持つ辺で、当家は建てないが<b>座と露出は設計してある</b>。")
    h.append(runs_table())

    # 其九 動線
    plate(h, nx(), "動線図", "表向 / 役方 / 勝手 / 奥向 / 家中 の5系統")
    fig(h, doro_svg(KAN[n[0] - 1]),
        legend='<span style="color:#A8452C">— 表向(客・謁見)</span>'
               '<span style="color:#3E6A8C">— 役方(藩士の日勤)</span>'
               '<span style="color:#7A6A2A">— 勝手(物の出入り)</span>'
               '<span style="color:#7A3A6A">— 奥向(藩主一家)</span>'
               '<span style="color:#3E7A55">— 家中(下段の長屋から)</span>',
        cap="●=起点 ○=終点。<b>役方は御錠口で止まる</b>。"
            "<b>家中は奥向の前を通らない</b> — そのために石段を主郭の南縁に採った。")
    h.append(routes_table())

    # 其十 格式と典拠
    plate(h, nx(), "格式と典拠", "『上屋敷が備える役割』(estate-types.md)を外の錨にした突き合わせ")
    h.append(program_table())
    h.append('<p class="cap">⚠ <b>「必須」は類型としての必須</b>(確度B〜A)であって、当邸に在ったことの'
             '典拠ではない。⛔ <b>「任意」を落とすときも落とした理由を書く</b> — '
             '沈黙は「落とした」のか「捨てた」のかを区別しない。</p>')
    h.append("</div>")

    # 其十一 検査
    plate(h, nx(), "検査", "生成のたびに機械で通す")
    rows = []
    ng = 0
    for cid, what, res, ok in checks_run():
        if not ok: ng += 1
        rows.append([cid, "*" + what, res, "○" if ok else "⛔"])
    h.append(tbl(["#", "*検査", "結果", "可否"], rows))
    h.append('<p class="cap">不合格 <b>%d</b> 件。⚠ <b>0件は「その条件を満たした」以上を意味しない</b> — '
             '検査の文言が測っている集合を、求めている集合と突き合わせ直すこと。</p>' % ng)
    h.append("</div>")

    # 其十二 未決
    plate(h, nx(), "未決", "⛔ 決まっていないことを決まったように書かない")
    h.append(tbl(["#", "件名", "*中身"],
                 [[p["id"], p["title"], "*" + p["_"]] for p in d["_pendingItems"]]))
    h.append("</div>")

    # 考証
    h.append('<div class="plate"><div class="phead"><h2>考証と決めごと</h2>'
             '<span class="meta">kyogoku_bitchu_kosho.md</span></div>')
    h.append('<div class="prose">%s</div></div>' % prose)

    h.append('<p class="foot">京極備中守上屋敷 指図 ／ '
             '設計値 <code>docs/Sashizu/kyogoku_bitchu_sashizu.json</code> ／ '
             '文章 <code>docs/Sashizu/kyogoku_bitchu_kosho.md</code> ／ '
             '地盤 <code>kyogoku_bitchu_edo_world.json</code>(江戸期復元)・'
             '<code>kyogoku_bitchu_dem.json</code>(現況) ／ '
             '生成器 <code>Tools/Sashizu/build_kyogoku_bitchu_sashizu.py</code>。'
             '⛔ 生成器は実装を読まない。</p>')
    h.append("</div>")
    open(OUT, "w", encoding="utf-8").write("\n".join(h))
    print("書いた: %s (%.0f KB)" % (os.path.relpath(OUT, os.path.join(HERE, "..", "..")),
                                  os.path.getsize(OUT) / 1024))
    print("検査 不合格 %d 件 / 建蔽率 %.1f%% / 図版 %d 面" % (ng, 100 * tot / (AREA / TSUBO), n[0]))


if __name__ == "__main__":
    main()
