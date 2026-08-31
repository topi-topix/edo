#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外堀下流の掘り直しの指図を組む。

    python3 Tools/Sashizu/build_sotobori_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/sotobori_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/sotobori_kosho.md     … 文章の部(人が書く・現況形)
    docs/Sashizu/sotobori_dem.json     … 段彩・等高線・切盛の格子(build_sotobori_dem.py)
    docs/Sashizu/sotobori_terrain.json … 縦断・横断・土量・検査の実測(同上)

【この普請ならではの作り】屋敷ではなく**土木**なので、回転間グリッド・室割り・建蔽率は無い。
基準は**距離程**(SW 汀線に沿う)で、図版は 位置と水系 / 現況 / 切盛 / 縦断 / 横断イ〜ホ /
石垣との取り合い / 工区と摺り付け の順に置く。段彩のランプは 0〜8m 用に別に持つ
(sashizu_lib の DEM_RAMP は 10m からで、この堀は全部いちばん下の色になってしまう)。
"""
import html
import json
import math
import os
import re
import subprocess

import sashizu_lib
from sashizu_lib import R, _SVN, Proj, cf_color, cutfill_legend

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "sotobori_sashizu.json")
MD = os.path.join(DOC, "sotobori_kosho.md")
DEM = os.path.join(DOC, "sotobori_dem.json")
TER = os.path.join(DOC, "sotobori_terrain.json")
OUT = os.path.join(DOC, "sotobori_sashizu.html")
VEX = 3.0          # 断面の垂直倍率
KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
       "其十一", "其十二", "其十三", "其十四", "其十五", "其十六", "其十七", "其十八",
       "其十九", "其二十", "其二十一", "其二十二"]

# 低地の堀用の段彩(0〜8m)。sashizu_lib の DEM_RAMP は 10m からで使えない
LOW_RAMP = [(1.0, "#2E6E8E"), (2.0, "#3A8398"), (3.0, "#4E9A9B"), (4.0, "#6BAC90"),
            (5.0, "#8ABC84"), (6.0, "#A9C87C"), (7.0, "#C6D07A"), (99, "#DCC776")]


def low_color(y):
    for lim, c in LOW_RAMP:
        if y < lim:
            return c
    return LOW_RAMP[-1][1]


def low_legend():
    out = []
    for i, (lim, c) in enumerate(LOW_RAMP):
        lo = LOW_RAMP[i - 1][0] if i else None
        lab = ("%.0f m〜" % LOW_RAMP[i - 1][0]) if lim == 99 else \
              ("〜%.0f m" % lim if lo is None else "%.0f–%.0f m" % (lo, lim))
        out.append('<span><span style="display:inline-block;width:15px;height:11px;background:%s;'
                   'border:1px solid var(--rule);margin-right:4px;vertical-align:-1px"></span>%s</span>'
                   % (c, lab))
    out.append('<span>── 等高線 1m(太線 5m)</span>')
    out.append('<span style="color:#7A2E1E">┄ 横断の切り位置</span>')
    return "".join(out)


def inline(s):
    return sashizu_lib.inline(s)


def plain(s):
    """SVG の <text> 用。markdown の強調記号を落とす(SVG では <b> が効かない)。

    ⚠ html の <p> では inline() を使うこと — そちらは ** を <b> に変える。
    """
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s, flags=re.S)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return html.escape(s)


def md2html(text):
    return sashizu_lib.md2html(text, inline=inline)


# ---------------------------------------------------------------- 作図の土台
def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, html.escape(label)),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.6"/></pattern>'
            '<pattern id="wv%d" width="10" height="10" patternUnits="userSpaceOnUse">'
            '<path d="M0,7 q2.5,-3 5,0 t5,0" stroke="#4E7E95" stroke-width="0.8" fill="none" opacity="0.55"/>'
            '</pattern>'
            '<clipPath id="cl%d"><rect x="0" y="0" width="%.0f" height="%.0f"/></clipPath></defs>'
            % (_SVN[0], _SVN[0], _SVN[0], W, H),
            '<g clip-path="url(#cl%d)">' % _SVN[0]]


ENDSVG = "</g></svg>"


def _wave():
    return "url(#wv%d)" % _SVN[0]


def poly_path(p, pts, close=True):
    d = "M" + " L".join("%.1f,%.1f" % (p.X(x), p.Y(z)) for x, z in pts)
    return d + (" Z" if close else "")


def iso(dem, key, lv):
    """マーチングスクエア。sashizu_lib._iso は h キー固定なので層を選べる版を持つ。"""
    st, h = dem["step"], dem[key]
    segs = []
    for iz in range(dem["nz"] - 1):
        for ix in range(dem["nx"] - 1):
            a, b = h[iz][ix], h[iz][ix + 1]
            c, e = h[iz + 1][ix + 1], h[iz + 1][ix]
            x0, z0 = dem["x0"] + ix * st, dem["z0"] + iz * st
            idx = (1 if a > lv else 0) | (2 if b > lv else 0) | (4 if c > lv else 0) | (8 if e > lv else 0)
            if idx in (0, 15):
                continue

            def ip(p, q, yp, yq):
                return p if abs(yq - yp) < 1e-9 else p + (q - p) * (lv - yp) / (yq - yp)
            B = (ip(x0, x0 + st, a, b), z0)
            Rr = (x0 + st, ip(z0, z0 + st, b, c))
            To = (ip(x0, x0 + st, e, c), z0 + st)
            L = (x0, ip(z0, z0 + st, a, e))
            tbl = {1: (B, L), 2: (B, Rr), 3: (L, Rr), 4: (Rr, To), 5: (B, Rr), 6: (B, To),
                   7: (L, To), 8: (L, To), 9: (B, To), 10: (B, L), 11: (Rr, To),
                   12: (L, Rr), 13: (B, Rr), 14: (B, L)}
            if idx in tbl:
                segs.append(tbl[idx])
    return segs


def dist_to_outlines(x, z, polys):
    d = 1e9
    for w in polys:
        for e, f in zip(w, w[1:] + w[:1]):
            dx, dz = f[0] - e[0], f[1] - e[1]
            t = max(0.0, min(1.0, ((x - e[0]) * dx + (z - e[1]) * dz) / (dx * dx + dz * dz)))
            d = min(d, math.hypot(x - (e[0] + t * dx), z - (e[1] + t * dz)))
    return d


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


# ---------------------------------------------------------------- 図版
def extent(d):
    xs = [p[0] for w in d["water"] for p in w["outline"]]
    zs = [p[1] for w in d["water"] for p in w["outline"]]
    m = d["works"]["outerWidth"] + 24
    return min(xs) - m, max(xs) + m, min(zs) - m, max(zs) + m


def base_plan(d, dem, W=1180.0, layer=None, cf=False, ter=None):
    """平面の下地。layer='cur' で段彩、cf=True で切盛。"""
    x0, x1, z0, z1 = extent(d)
    p = Proj(x0, x1, z0, z1, W=W, top=16, bottom=26)
    h = _sv(p.W, p.H, "外堀下流 平面")
    h.append(R(0, 0, p.W, p.H, fill="var(--paper)"))
    polys = [w["outline"] for w in d["water"]]
    st = dem["step"]
    s = p.L(st) + 0.6
    if layer or cf:
        for iz in range(dem["nz"]):
            z = dem["z0"] + iz * st
            if not (z0 - st <= z <= z1 + st):
                continue
            for ix in range(dem["nx"]):
                x = dem["x0"] + ix * st
                if not (x0 - st <= x <= x1 + st):
                    continue
                cur = dem["cur"][iz][ix]
                if cf:
                    wp = [b for b in d["water"] if b.get("works")]
                    dd = dist_to_outlines(x, z, [b["outline"] for b in wp])
                    hit = [b for b in wp if in_poly(x, z, b["outline"])]
                    if hit:
                        des = hit[0]["floor"]
                    elif dd <= d["works"]["outerWidth"]:
                        t = min(1.0, max(0.0, (dd - d["works"]["featherFrom"])
                                         / (d["works"]["outerWidth"] - d["works"]["featherFrom"])))
                        des = dem["pre"][iz][ix] * (1 - t) + cur * t
                    else:
                        continue
                    col = cf_color(des - cur)
                else:
                    col = low_color(cur)
                h.append(R(p.X(x) - s / 2, p.Y(z) - s / 2, s, s, fill=col))
    if layer:
        for lv in [v for v in range(0, 9)]:
            segs = iso(dem, layer, float(lv))
            if not segs:
                continue
            dd = " ".join("M%.1f,%.1f L%.1f,%.1f" % (p.X(a[0]), p.Y(a[1]), p.X(b[0]), p.Y(b[1]))
                          for a, b in segs)
            h.append('<path d="%s" stroke="var(--ink)" stroke-width="%.2f" fill="none" opacity="%.2f"/>'
                     % (dd, 0.85 if lv % 5 == 0 else 0.4, 0.5 if lv % 5 == 0 else 0.3))
    return p, h, polys


def draw_frame(d, p, h, polys, water=True, ishigaki=True, works=True, labels=True):
    if works:
        w = d["works"]["outerWidth"]
        for q in [b["outline"] for b in d["water"] if b.get("works")]:
            n = len(q)
            off = []
            for i in range(n):
                a, b, c = q[i - 1], q[i], q[(i + 1) % n]
                v1 = (b[0] - a[0], b[1] - a[1])
                v2 = (c[0] - b[0], c[1] - b[1])
                l1 = math.hypot(*v1) or 1
                l2 = math.hypot(*v2) or 1
                nn = ((-v1[1] / l1 - v2[1] / l2), (v1[0] / l1 + v2[0] / l2))
                ln = math.hypot(*nn) or 1
                sgn = -1 if in_poly(b[0] + nn[0] / ln, b[1] + nn[1] / ln, q) else 1
                off.append((b[0] + sgn * w * 1.35 * nn[0] / ln, b[1] + sgn * w * 1.35 * nn[1] / ln))
            h.append('<path d="%s" stroke="#7A2E1E" stroke-width="1" fill="none" '
                     'stroke-dasharray="6 4" opacity="0.65"/>' % poly_path(p, off))
    if water:
        for w in d["water"]:
            h.append('<path d="%s" fill="%s" stroke="#3F6F86" stroke-width="%.1f" opacity="0.95"%s/>'
                     % (poly_path(p, w["outline"]), _wave(),
                        1.3 if w.get("works") else 1.0,
                        "" if w.get("works") else ' stroke-dasharray="7 4"'))
    if ishigaki:
        for r in d["ishigaki"]["runs"]:
            a, b = r["p0"], r["p1"]
            if r.get("provisional"):
                # ⛔ 非史実の仮設(END3)。史実の石垣と同列に見せない
                h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#8A8A8A" stroke-width="2.4" '
                         'stroke-dasharray="5 4" stroke-linecap="butt" opacity="0.9"/>'
                         % (p.X(a[0]), p.Y(a[1]), p.X(b[0]), p.Y(b[1])))
                if labels:
                    h.append('<text class="anS2" x="%.1f" y="%.1f">%s(仮設)</text>'
                             % (p.X((a[0] + b[0]) / 2) + 6, p.Y((a[1] + b[1]) / 2), html.escape(r["line"])))
                continue
            h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="var(--ishi)" stroke-width="3.2" '
                     'stroke-linecap="round" opacity="0.95"/>'
                     % (p.X(a[0]), p.Y(a[1]), p.X(b[0]), p.Y(b[1])))
        for c in d["ishigaki"]["corners"]:
            h.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--ishi)"/>'
                     % (p.X(c["p"][0]), p.Y(c["p"][1])))
    for s in d["structures"]:
        if s["id"] == "Edo_Atarashibashi":
            cx, cz = s["center"]
            a = math.radians(s["axis"])
            u = (math.sin(a), math.cos(a))
            h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="var(--nagaya)" stroke-width="4" '
                     'stroke-linecap="round" opacity="0.9"/>'
                     % (p.X(cx - 24 * u[0]), p.Y(cz - 24 * u[1]), p.X(cx + 24 * u[0]), p.Y(cz + 24 * u[1])))
            if labels:
                h.append('<text class="anS" x="%.1f" y="%.1f">新シ橋</text>'
                         % (p.X(cx) + 7, p.Y(cz) - 6))
    if labels:
        h.append('<text class="anS" x="%.1f" y="%.1f">虎ノ門の橋(堰)</text>'
                 % (p.X(392), p.Y(462) - 4))
        h.append('<text class="anS" x="%.1f" y="%.1f">幸橋・汐留川へ(未再現)</text>'
                 % (p.X(1050) - 30, p.Y(150) + 26))
        h.append('<text class="anS" x="%.1f" y="%.1f">郭内(北東)</text>' % (p.X(700), p.Y(400)))
        h.append('<text class="anS" x="%.1f" y="%.1f">郭外(南西)</text>' % (p.X(640), p.Y(250)))
        # 方位
        h.append('<path d="M%.1f,%.1f l0,-24" stroke="var(--dim)" stroke-width="1"/>'
                 '<text class="anS2" x="%.1f" y="%.1f">北</text>'
                 % (p.W - 34, p.H - 34, p.W - 34, p.H - 40))
    # スケールバー
    L = p.L(100)
    y = p.H - 12
    h.append('<path d="M14,%.1f h%.1f" stroke="var(--dim)" stroke-width="1.4"/>'
             '<text class="sl" x="%.1f" y="%.1f">100 m</text>' % (y, L, 14 + L + 6, y + 3))


def plan_svg(d, dem, ter, mode):
    p, h, polys = base_plan(d, dem, layer="cur" if mode == "cur" else None, cf=(mode == "cf"))
    draw_frame(d, p, h, polys)
    if mode == "cur":
        for s in ter["sections"]:
            px, pz = s["p"]
            n = s["nrm"]
            a = (px - 26 * n[0], pz - 26 * n[1])
            b = (px + (s["width"] + 26) * n[0], pz + (s["width"] + 26) * n[1])
            h.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#7A2E1E" stroke-width="1.1" '
                     'stroke-dasharray="5 3"/>' % (p.X(a[0]), p.Y(a[1]), p.X(b[0]), p.Y(b[1])))
            h.append('<text class="sr" x="%.1f" y="%.1f">%s</text>'
                     % (p.X(a[0]) - 12, p.Y(a[1]) + 4, s["mark"]))
    if mode == "cf":
        for q in d["works"].get("keepOut", {}).get("rects", []):
            r = q["rect"]
            h.append(R(p.X(r[0]), p.Y(r[3]), p.L(r[1] - r[0]), p.L(r[3] - r[2]),
                       fill="var(--paper2)", stroke="var(--shu)", sw=1.4, dash="5 3", op=0.55))
            h.append('<text class="anG" x="%.1f" y="%.1f">%s 凍結</text>'
                     % (p.X(r[0]) + 4, p.Y(r[3]) - 5, q["id"]))
    h.append(ENDSVG)
    return "\n".join(h)


def system_svg(d, W=1180.0):
    """水系の段階(模式縦断)。左=溜池、右=幸橋方向。"""
    st = d["system"]["steps"]
    H = 250.0
    h = _sv(W, H, "水系の段階")
    h.append(R(0, 0, W, H, fill="var(--paper)"))
    y0, ys = H - 46, 22.0     # y0 = 0m の位置 / 1m あたり px
    ax = lambda v: y0 - v * ys
    h.append('<path d="M40,%.1f H%.1f" stroke="var(--rule)" stroke-width="1"/>' % (y0, W - 20))
    for v in range(0, 9):
        h.append('<path d="M36,%.1f H%.1f" stroke="var(--rule)" stroke-width="0.5" opacity="0.7"/>'
                 % (ax(v), W - 20))
        h.append('<text class="sl" x="10" y="%.1f">%d m</text>' % (ax(v) + 3, v))
    n = len(st)
    seg = (W - 90) / n
    for i, s in enumerate(st):
        x = 50 + i * seg
        wy = s.get("waterY")
        cr = s.get("crest")
        if wy is not None:
            h.append(R(x, ax(wy), seg - 8, y0 - ax(wy), fill="#BBD3DF", op=0.75))
            h.append('<path d="M%.1f,%.1f h%.1f" stroke="#3F6F86" stroke-width="1.8"/>'
                     % (x, ax(wy), seg - 8))
            h.append('<text class="an2b" x="%.1f" y="%.1f">%.2f</text>' % (x + 3, ax(wy) - 5, wy))
            fl = s.get("floor")
            if fl is not None:
                h.append('<path d="M%.1f,%.1f h%.1f" stroke="var(--ink)" stroke-width="1.2" '
                         'stroke-dasharray="4 3"/>' % (x, ax(fl), seg - 8))
                h.append('<text class="sl" x="%.1f" y="%.1f">床 %.2f</text>' % (x + 3, ax(fl) + 12, fl))
        if cr is not None:
            h.append('<path d="M%.1f,%.1f h%.1f" stroke="var(--shu)" stroke-width="2.4"/>'
                     % (x + (seg - 8) / 2 - 14, ax(cr), 28))
            h.append('<text class="anG" x="%.1f" y="%.1f">天端 %.2f</text>'
                     % (x + (seg - 8) / 2 - 14, ax(cr) - 6, cr))
        h.append('<text class="anS2" x="%.1f" y="%.1f">%s</text>'
                 % (x + (seg - 8) / 2, H - 24, plain(s["name"])))
        if s.get("note"):
            h.append('<text class="jo" x="%.1f" y="%.1f" style="text-anchor:middle">%s</text>'
                     % (x + (seg - 8) / 2, H - 10, plain(s["note"])))
    h.append('<text class="zn" x="%.1f" y="16">溜 池 ─── 虎 ノ 門 ─── 幸 橋</text>' % (W / 2))
    h.append(ENDSVG)
    return "\n".join(h)


def profile_svg(d, ter, W=1180.0):
    """縦断面。距離程 × 標高。水位は虎ノ門の橋で 3.50 → 1.80 に落ちる。"""
    pr = ter["profile"]
    L = ter["reachLength"]
    H = 340.0
    h = _sv(W, H, "縦断面")
    h.append(R(0, 0, W, H, fill="var(--paper)"))
    x0, xw = 52.0, W - 76.0
    y0, ys = H - 56, 30.0
    X = lambda s: x0 + s / L * xw
    Y = lambda v: y0 - v * ys
    for v in range(0, 8):
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="var(--rule)" stroke-width="%.1f" opacity="0.8"/>'
                 % (x0 - 6, Y(v), x0 + xw, 0.9 if v == 0 else 0.5))
        h.append('<text class="sl" x="14" y="%.1f">%d m</text>' % (Y(v) + 3, v))
    for s in range(0, int(L) + 1, 100):
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="var(--rule)" stroke-width="0.5" opacity="0.7"/>'
                 % (X(s), Y(0), Y(7.4)))
        h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">%d</text>'
                 % (X(s), y0 + 15, s))
    h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">距離程 [m] ── '
             '0 = 堰の直下(00001 の西端)</text>' % (x0 + xw / 2, y0 + 32))
    # 水位と床は水面ごとに帯で描く(距離程の連続する塊にまとめる)
    runs = []
    for r in pr:
        if runs and runs[-1][0] == r[0]:
            runs[-1][2] = r[1]
        else:
            runs.append([r[0], r[1], r[1], r[9], r[10]])
    for i, (body, s0, s1, wy, fl) in enumerate(runs):
        s1 = runs[i + 1][1] if i + 1 < len(runs) else s1   # 次の水面まで帯を継ぐ(測点の隙間を埋める)
        h.append(R(X(s0), Y(wy), X(s1) - X(s0), Y(fl) - Y(wy), fill="#BBD3DF", op=0.8))
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="#3F6F86" stroke-width="1.8"/>'
                 % (X(s0), Y(wy), X(s1)))
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="var(--ink)" stroke-width="1.3" '
                 'stroke-dasharray="5 3"/>' % (X(s0), Y(fl), X(s1)))
        h.append('<text class="an2b" x="%.1f" y="%.1f">水面 %.2f</text>' % (X(s0) + 6, Y(wy) - 6, wy))
        h.append('<text class="sl" x="%.1f" y="%.1f">床 %.2f</text>' % (X(s0) + 6, Y(fl) + 13, fl))
        h.append('<text class="jo" x="%.1f" y="%.1f" style="text-anchor:middle">%s</text>'
                 % ((X(s0) + X(s1)) / 2, Y(7.4) - 20, body.replace("Sotobori_", "")))
    # 虎ノ門の橋(堰堤)の段差
    for i in range(1, len(runs)):
        if runs[i][3] != runs[i - 1][3]:
            sx = (runs[i - 1][2] + runs[i][1]) / 2
            h.append('<path d="M%.1f,%.1f V%.1f" stroke="var(--shu)" stroke-width="2.4"/>'
                     % (X(sx), Y(runs[i - 1][3]), Y(runs[i][3])))
            crest = next((st.get("crest") for st in d["system"]["steps"]
                          if st.get("crest") and runs[i][3] < st["crest"] < runs[i - 1][3]), None)
            h.append('<text class="anG" x="%.1f" y="%.1f" style="text-anchor:middle">%s落差 %.2f m</text>'
                     % (X(sx), Y(runs[i - 1][3]) - 9,
                        ("虎ノ門の橋の堰 天端 %.2f ／ " % crest) if crest else "",
                        runs[i - 1][3] - runs[i][3]))
    for key, col, dash, lab in ((5, "var(--dim)", "3 3", "現況 郭外"),
                                (6, "var(--dim)", None, "現況 郭内"),
                                (7, "var(--ishi)", "6 3", "石垣天端 郭外"),
                                (8, "var(--ishi)", None, "石垣天端 郭内")):
        seg, cur = [], []
        for r in pr:
            if r[key] is None:
                if len(cur) > 1:
                    seg.append(cur)
                cur = []
            else:
                cur.append((X(r[1]), Y(r[key])))
        if len(cur) > 1:
            seg.append(cur)
        for q in seg:
            h.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f"%s/>'
                     % (" ".join("%.1f,%.1f" % t for t in q), col, 1.9 if key > 6 else 1.3,
                        (' stroke-dasharray="%s"' % dash) if dash else ""))
    lg = [("現況 郭外", "var(--dim)", "3 3"), ("現況 郭内", "var(--dim)", None),
          ("石垣天端 郭外", "var(--ishi)", "6 3"), ("石垣天端 郭内", "var(--ishi)", None)]
    for i, (t, c, ds) in enumerate(lg):
        yy = 20 + i * 15
        h.append('<path d="M%.1f,%.1f h22" stroke="%s" stroke-width="1.8"%s/>'
                 % (W - 178, yy, c, (' stroke-dasharray="%s"' % ds) if ds else ""))
        h.append('<text class="sl" x="%.1f" y="%.1f">%s</text>' % (W - 152, yy + 3, t))
    for sc in ter["sections"]:
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="#7A2E1E" stroke-width="1" '
                 'stroke-dasharray="4 3"/>' % (X(sc["chainage"]), Y(0), Y(7.4)))
        h.append('<text class="sr" x="%.1f" y="%.1f" style="text-anchor:middle">%s</text>'
                 % (X(sc["chainage"]), Y(7.4) - 5, sc["mark"]))
    h.append(ENDSVG)
    return "\n".join(h)


def section_svg(d, s, W=1180.0):
    """横断面。"""
    row = s["row"]
    t0, t1 = row[0][0], row[-1][0]
    lo = min(min(r[1], r[2]) for r in row) - 0.8
    hi = max(max(r[1], r[2]) for r in row) + 1.6
    H = 300.0
    h = _sv(W, H, "横断面 " + s["mark"])
    h.append(R(0, 0, W, H, fill="var(--paper)"))
    x0, xw = 56.0, W - 90.0
    y0, yh = H - 46, H - 84
    X = lambda t: x0 + (t - t0) / (t1 - t0) * xw
    Y = lambda v: y0 - (v - lo) / (hi - lo) * yh
    for v in range(int(math.floor(lo)), int(math.ceil(hi)) + 1):
        h.append('<path d="M%.1f,%.1f H%.1f" stroke="var(--rule)" stroke-width="0.5" opacity="0.8"/>'
                 % (x0 - 6, Y(v), x0 + xw))
        h.append('<text class="sl" x="16" y="%.1f">%d m</text>' % (Y(v) + 3, v))
    for t in range(int(t0), int(t1) + 1, 5):
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="var(--rule)" stroke-width="0.4" opacity="0.6"/>'
                 % (X(t), Y(lo), Y(hi)))
        if t % 10 == 0:
            h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">%+d</text>'
                     % (X(t), y0 + 15, t))
    wy, fl = s["waterY"], s["floor"]
    des = [(X(r[0]), Y(r[2])) for r in row]
    cur = [(X(r[0]), Y(r[1])) for r in row]
    if s["works"]:
        h.append('<path d="%s L%s Z" fill="var(--cut2)" opacity="0.55"/>'
                 % ("M" + " L".join("%.1f,%.1f" % q for q in cur),
                    " L".join("%.1f,%.1f" % q for q in reversed(des))))
    h.append(R(X(0), Y(wy), X(s["width"]) - X(0), Y(fl) - Y(wy), fill="#BBD3DF", op=0.85))
    h.append('<path d="M%.1f,%.1f H%.1f" stroke="#3F6F86" stroke-width="1.6"/>'
             % (X(0), Y(wy), X(s["width"])))
    h.append('<polyline points="%s" fill="none" stroke="var(--dim)" stroke-width="1.1" '
             'stroke-dasharray="4 3"/>' % " ".join("%.1f,%.1f" % q for q in cur))
    h.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.9"/>'
             % " ".join("%.1f,%.1f" % q for q in des))
    # ⭐ 汀線 = 石垣の見え面。躯体はそこから陸側へ ishigaki.faceToPivot(=4.80m)ぶん厚い。
    tw = d["ishigaki"].get("faceToPivot", 4.80)   # 躯体の厚み(見え面→ピボット線)
    for ta, tb, cp, lab in ((-tw, 0.0, s["copingSW"], "郭外 石垣"),
                            (s["width"], s["width"] + tw, s["copingNE"], "郭内 石垣")):
        if cp is None:
            continue
        h.append(R(X(min(ta, tb)), Y(cp), abs(X(tb) - X(ta)), Y(fl) - Y(cp),
                   fill="var(--ishi)", op=0.75))
        h.append('<text class="anS2" x="%.1f" y="%.1f">%s 天端 %.2f</text>' % (X(ta), Y(cp) - 7, lab, cp))
    for t, lab in ((0, "汀線"), (s["width"], "汀線")):
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="#3F6F86" stroke-width="0.8" '
                 'stroke-dasharray="2 3"/>' % (X(t), Y(lo), Y(hi)))
    ww = d["works"]["outerWidth"] if s["works"] else None
    for t in ((-ww, s["width"] + ww) if ww else ()):
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="#7A2E1E" stroke-width="1" '
                 'stroke-dasharray="6 4"/>' % (X(t), Y(lo), Y(hi)))
    if ww:
        h.append('<text class="sl" x="%.1f" y="%.1f">工区の境</text>' % (X(-ww) + 4, Y(hi) + 12))
        h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:end">工区の境</text>'
                 % (X(s["width"] + ww) - 4, Y(hi) + 12))
    vex = (yh / (hi - lo)) / (xw / (t1 - t0))
    h.append('<text class="big" x="%.1f" y="20">断面 %s ── 距離程 %.0f m ／ 水面幅 %.2f m ／ '
             '垂直倍率 %.1f 倍%s</text>'
             % (x0, s["mark"], s["chainage"], s["width"], vex,
                "" if s["works"] else " ／ 調査(掘らない)"))
    h.append('<text class="sl" x="%.1f" y="%.1f" style="text-anchor:middle">汀線からの距離 [m] '
             '(左=郭外 / 右=郭内)</text>' % (x0 + xw / 2, y0 + 32))
    h.append(ENDSVG)
    return "\n".join(h)


def byid_works(d, r):
    """その run が『掘る水面』に属するか。"""
    return any(b["id"] == r.get("body") and b.get("works") for b in d["water"])


def rule_svg(d, W=1180.0):
    """工区と摺り付けの規則(模式)。"""
    H = 300.0
    h = _sv(W, H, "工区と摺り付け")
    h.append(R(0, 0, W, H, fill="var(--paper)"))
    x0, xw = 60.0, W - 100.0
    y0, ys = H - 60, 26.0
    w = d["works"]
    span = w["outerWidth"] + 20
    X = lambda t: x0 + (t + span) / (2 * span) * xw
    Y = lambda v: y0 - v * ys
    fl = [b["floor"] for b in d["water"] if b.get("works")][0]
    tw = d["ishigaki"].get("faceToPivot", 4.80)
    zones = [(-span, 0, "① 汀線の内側(堀) ── 床 %.2f 一律" % fl, "#BBD3DF"),
             (0, tw, "躯体 0–%.2fm ── 石垣の下(種地を戻す)" % tw, "var(--cut1)"),
             (tw, w["featherFrom"], "② %.2f–%.0fm ── 天端 − %.2f まで盛る"
              % (tw, w["featherFrom"], w.get("bankBelowCoping", 0.2)), "var(--fill1)"),
             (w["featherFrom"], w["outerWidth"], "③ %.0f–%.0fm ── 摺り付け(④で45°頭打ち)"
              % (w["featherFrom"], w["outerWidth"]), "var(--fill1)"),
             (w["outerWidth"], span, "⑥ 工区の外 ── 触らない", "var(--paper2)")]
    for a, b, lab, col in zones:
        h.append(R(X(a), Y(7.6), X(b) - X(a), Y(0) - Y(7.6), fill=col, op=0.55))
        h.append('<text class="anS2" x="%.1f" y="%.1f">%s</text>'
                 % ((X(a) + X(b)) / 2, Y(7.6) - 8, html.escape(lab.split("──")[0].strip())))
    h.append('<path d="M%.1f,%.1f H%.1f" stroke="var(--rule)" stroke-width="1"/>' % (x0, Y(0), x0 + xw))
    for v in range(0, 8):
        h.append('<text class="sl" x="20" y="%.1f">%d m</text>' % (Y(v) + 3, v))
    wy = [b["waterY"] for b in d["water"] if b.get("works")][0]
    h.append('<path d="M%.1f,%.1f H%.1f" stroke="#3F6F86" stroke-width="1.8"/>'
             % (X(-span), Y(wy), X(0)))
    h.append('<text class="an2b" x="%.1f" y="%.1f">水面 %.2f</text>' % (X(-span) + 6, Y(wy) - 6, wy))
    r0 = max((r for r in d["ishigaki"]["runs"]
              if byid_works(d, r) and "郭外" in r["side"]), key=lambda r: r["n"])
    cop = r0["copingFrom"]
    ofs = d["ishigaki"].get("faceToPivot", 4.80)   # 汀線(見え面)から躯体の裏面まで
    bk = cop - d["works"].get("bankBelowCoping", 0.2)
    seg = [(-span, fl), (0, fl), (ofs, fl), (ofs, bk), (10, bk),
           (14, cop - 0.4), (span, cop - 0.6)]
    h.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="2.2"/>'
             % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in seg))
    h.append('<polyline points="%s" fill="none" stroke="var(--dim)" stroke-width="1.1" '
             'stroke-dasharray="4 3"/>'
             % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in
                        [(-span, cop - 0.5), (0, cop - 0.5), (10, cop - 0.6),
                         (14, cop - 0.4), (span, cop - 0.6)]))
    h.append(R(X(0), Y(cop), X(ofs) - X(0), Y(fl) - Y(cop), fill="var(--ishi)", op=0.8))
    h.append('<text class="anS2" x="%.1f" y="%.1f">石垣(見え面=汀線・躯体の厚み %.2f m・天端 %.2f)</text>'
             % (X(ofs) + 6, Y(cop) - 8, ofs, cop))
    for t in (0, w["outerWidth"]):
        h.append('<path d="M%.1f,%.1f V%.1f" stroke="#7A2E1E" stroke-width="1" '
                 'stroke-dasharray="6 4"/>' % (X(t), Y(0), Y(7.6)))
    h.append('<text class="big" x="%.1f" y="20">工区と摺り付けの規則(模式・郭外側の片側だけ)</text>' % x0)
    h.append('<text class="sl" x="%.1f" y="%.1f">── 設計面　┄ 現況</text>' % (x0, y0 + 22))
    h.append('<text class="sl" x="%.1f" y="%.1f">⛔ 45°の頭打ちは③の帯だけ。'
             '堀の壁は総石垣なので垂直のまま残す　⭐ ②は最寄りの天端 − %.2f m'
             '(2026-08-30 ユーザー裁定A)</text>'
             % (x0, y0 + 38, d["works"].get("bankBelowCoping", 0.2)))
    h.append('<text class="sl" x="%.1f" y="%.1f">⛔ 躯体の帯(0–%.2fm)は「触らない」のではない '
             '── 天端基準で盛らないだけで、種地(08-22 リセット直前)を戻すので'
             '掘削も埋め戻しも起きる。上の平らな線は模式で、実際は種地の起伏をなぞる</text>'
             % (x0, y0 + 52, ofs))
    h.append(ENDSVG)
    return "\n".join(h)


# ---------------------------------------------------------------- 表
def tbl(head, rows, cls="tw"):
    return ('<div class="%s"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
            % (cls, "".join("<th>%s</th>" % c for c in head), "".join(rows)))


def spec_table(d, ter):
    v = ter["volumes"]
    rows = []
    add = lambda a, b: rows.append(
        "<tr><td class='note' style='text-align:left'>%s</td><td>%s</td></tr>" % (a, b))
    add("距離程(郭外の汀線に沿う。0 = 堰の直下)", "%.1f m" % ter["reachLength"])
    add("掘り直す水面(00002 + 00003)", "%.2f ha" % v["waterAreaHa"])
    add("工区(その汀線 + %.0f m)" % d["works"]["outerWidth"], "%.2f ha" % v["workAreaHa"])
    add("掘削", "%s m³(最大 %.2f m)" % ("{:,}".format(v["cut_m3"]), v["maxCut_m"]))
    mf = "%s m³(最大 %.2f m)" % ("{:,}".format(v["fill_m3"]), v["maxFill_m"])
    mf += "　⚠ この最大は<b>石垣の躯体の下</b>(汀線から %.2f m 以内)の値で、<b>地表には現れない</b>" \
          % d["ishigaki"].get("faceToPivot", 4.80)
    if v.get("maxFillOutsideBody_m") is not None:
        mf += " ── 躯体を除いた最大は <b>%.2f m</b>" % v["maxFillOutsideBody_m"]
    else:
        mf += " ── 躯体を除いた最大は次の再生成で出る(<code>maxFillOutsideBody_m</code>)"
    add("盛土", mf)
    add("差引(場外へ出る土)",
        "%s m³　⚠ <b>行き先は未決</b>(U13)" % "{:,}".format(v["net_m3"]))
    if v.get("overshoot_m2") is not None:
        add("汀線の外に残る水面下の床",
            "%s m²(<b>全量が石垣の躯体の下</b>・汀線から中央 %.1f m・最大 %.1f m 外)"
            % ("{:,}".format(v["overshoot_m2"]), v["overshootMedianOutside_m"],
               v["overshootMaxOutside_m"]))
    for k in ("inside", "body", "bank"):
        z = v.get("byZone", {}).get(k)
        if z:
            add("　└ 帯ごとの土量 — %s" % html.escape(z["label"]),
                "掘 %s / 盛 %s m³(最大 掘 %.2f・盛 %.2f m)"
                % ("{:,}".format(z["cut_m3"]), "{:,}".format(z["fill_m3"]),
                   z["maxCut_m"], z["maxFill_m"]))
    add("工区の外へ出た変更セル", "%d" % v["spillCells"])
    g = ter.get("grid", {})
    if g.get("sampleOffset"):
        add("計算格子",
            "%d m 刻み ／ ラベル原点 (%d, %d)　⚠ <b>高さを採った実位置は (%.2f, %.2f)</b> ── "
            "heightmap の刻みに丸めるため (%.2f, %.2f) m ずれる。再実装は実位置の側を使うこと"
            % (g["step"], g["x0"], g["z0"], g["sampleX0"], g["sampleZ0"],
               g["sampleOffset"][0], g["sampleOffset"][1]))
    add("凍結域(帯から外した所)", "%.2f ha ／ 動いたセル %d" % (v["keepOutHa"], v["keepOutCells"]))
    for g in ter.get("gaps", []):
        add("距離程の隙間 — %s" % html.escape(g["name"]),
            "%.1f m(距離程 %.1f–%.1f)" % (g["length"], g["from"], g["to"]))
    return tbl(["諸元", "値"], rows)


def survey_table(ter):
    rows = []
    for r in ter["survey"]:
        if r["works"]:
            after = "%.1f%% → <b>%.1f%%</b>" % (r["curSubmergedPct"], r["designSubmergedPct"])
            fl = "%.2f(設計)" % r["floor"]
            note = "全面 掘り直し"
        else:
            after = "%.1f%%" % r["curSubmergedPct"]
            fl = "%.2f — 床±0.2m に %.1f%%" % (r["floor"], r["curOnFloorPct"])
            zs = "／".join("%s %d m²(水面+1m超 %d)" % (z["name"], z["m2"], z["over1m_m2"])
                           for z in r.get("dryZoneRows", []))
            note = ("調査のみ ── 08-22 リセット直前と一致 %.1f%%。水面より上 %.3f ha "
                    "(最大 +%.2f m・汀線から最大 %.1f m 内側)： %s"
                    % (r["curVsPreSamePct"], r["dryHa"], r["dryMaxOver_m"],
                       r["dryMaxInsideFromEdge_m"], zs))
        rows.append("<tr><td>%s</td><td>%.2f ha</td><td>%.2f</td><td>%s</td><td>%s</td>"
                    "<td class='note' style='text-align:left'>%s</td></tr>"
                    % (r["id"], r["areaHa"], r["waterY"], fl, after, note))
    return tbl(["水面", "面積", "水位", "床", "水面より下", "扱い"], rows)


def _prov(d):
    return {r["line"] for r in d["ishigaki"]["runs"] if r.get("provisional")}


def buried_table(d, ter):
    prov = _prov(d)
    rows = []
    for b in ter["ishigakiBuried"]:
        flag = " ⚠" if b["buriedPct"] > 20 else ""
        b = dict(b, line=b["line"] + ("(仮設)" if b["line"] in prov else ""))
        rows.append("<tr><td>%s</td><td>%s</td><td>%d</td><td>%+.2f</td><td>%+.2f</td>"
                    "<td>%.0f%%%s</td></tr>"
                    % (b["line"], b["body"].replace("Sotobori_", ""), b["n"],
                       b["curOverCopingMedian"], b["designOverCopingMedian"],
                       b["buriedPct"], flag))
    return tbl(["石垣の run", "水面", "評価点", "現況地盤 − 天端(中央)",
                "設計地盤 − 天端(中央)", "天端が埋まる割合"], rows)


def back_table(d, ter):
    prov = _prov(d)
    rows = []
    for b in ter["ishigakiBack"]:
        flag = "" if (abs(b["median"]) <= 1.0 or not b["works"]) else " ⚠"
        o = b["byOffset"]
        b = dict(b, line=b["line"] + ("(仮設)" if b["line"] in prov else ""))
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td>"
                    "<td>%+.2f</td><td>%+.2f%s</td><td>%+.2f</td><td>%+.2f</td></tr>"
                    % (b["line"], b["body"].replace("Sotobori_", ""),
                       "掘る" if b["works"] else "調査", b["n"],
                       o["2"], o["4"], flag, o["6"], o["8"]))
    return tbl(["石垣の run", "水面", "扱い", "評価点",
                "天端 − 背面の設計地盤(中央) +2m", "+4m", "+6m", "+8m"], rows)


def stage_table(d):
    rows = ["<tr><td>%d</td><td>%s</td><td class='note' style='text-align:left'>%s</td></tr>"
            % (s["n"], html.escape(s["name"]), inline(html.escape(s["what"]))) for s in d["stages"]]
    return tbl(["段", "段階", "中身"], rows)


def check_table(d):
    rows = ["<tr><td><code>%s</code></td><td>%s</td>"
            "<td class='note' style='text-align:left'>%s</td>"
            "<td class='note' style='text-align:left'>%s</td></tr>"
            % (c["id"], html.escape(c.get("on", "—")), inline(html.escape(c["what"])),
               inline(html.escape(c["pass"] + ("　" + c["note"] if c.get("note") else ""))))
            for c in d["checks"]]
    return tbl(["id", "どの面で測るか", "何を測るか", "合格"], rows)


def pending_table(d):
    rows = ["<tr><td>%s</td><td class='note' style='text-align:left'>%s</td><td>%s</td>"
            "<td class='note' style='text-align:left'>%s</td><td>%s</td></tr>"
            % (u["id"], inline(html.escape(u["what"])), html.escape(u.get("status", "—")),
               inline(html.escape(u["detail"])), inline(html.escape(u["cert"])))
            for u in d["unresolved"]]
    return tbl(["", "事項", "状態", "中身", "確度"], rows)


def history():
    try:
        log = subprocess.check_output(
            ["git", "-C", ROOT, "log", "--date=short", "--pretty=%h|%ad|%s", "--",
             "docs/Sashizu/sotobori_sashizu.json", "docs/Sashizu/sotobori_kosho.md"]).decode()
    except Exception:
        log = ""
    rows = []
    for ln in log.strip().split("\n"):
        if not ln.strip():
            continue
        hh, dt, sub = ln.split("|", 2)
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td class='note' style='text-align:left'>%s</td></tr>"
                    % (hh, dt, html.escape(sub)))
    if not rows:
        rows = ["<tr><td colspan='3' class='note'>初版(未コミット)</td></tr>"]
    return tbl(["commit", "日付", "件名"], rows)


# ---------------------------------------------------------------- 組み立て
def plate(h, num, title, meta=""):
    """章を開く。前の章が開いていれば閉じてから開く(閉じ忘れで div が入れ子になる)。"""
    if any('<div class="plate">' in x for x in h):
        h.append("</div>")
    h.append('<div class="plate"><div class="phead"><h2>%s　%s</h2>%s</div>'
             % (num, title, ('<span class="meta">%s</span>' % meta) if meta else ""))


def fig(h, svg, cap=None, legend=None):
    h.append('<div class="fig">%s</div>' % svg)
    if legend:
        h.append('<div class="legend">%s</div>' % legend)
    if cap:
        h.append('<p class="cap">%s</p>' % cap)


def main():
    d = json.load(open(JSON, encoding="utf-8"))
    dem = json.load(open(DEM, encoding="utf-8"))
    ter = json.load(open(TER, encoding="utf-8"))
    prose = md2html(open(MD, encoding="utf-8").read())
    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"),
               encoding="utf-8").read()
    n = [0]

    def nx():
        n[0] += 1
        return KAN[n[0] - 1]

    h = ['<meta charset="utf-8">', "<title>%s</title>" % html.escape(d["title"]),
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">%s ／ %s ／ 基準年次 %s</p>'
             % (html.escape(d["subtitle"]), html.escape(d["board"]), html.escape(d["year"])))
    h.append("<h1>%s</h1>" % html.escape(d["title"]))
    h.append('<p class="lede">2026-08-22 の造成リセットが、虎ノ門の橋の東面から東の外堀を'
             '<b>掘削もろとも現代の地面へ戻していた</b>。水面のメッシュは張られたままだったので、'
             '乾いた地面の中に水の板が沈み、両岸の総石垣も土に埋まっていた。'
             'これは<b>溜池の堰(どんどん)から下流ひと続き</b>を対象とした掘り直しの指図である。'
             '<b>新設ではなく復旧</b>で、堀の形・水位・石垣・橋はすでに実装されており、'
             'この指図はそれを動かさない。'
             '<b>⭐ 00001 は 2026-08-29 に、00002・00003 は 2026-08-31 に実装を終え、'
             '施工後の7検査をすべて通した。</b>'
             '<b>数値の正典は <code>sotobori_sashizu.json</code>、文章の正典は <code>sotobori_kosho.md</code>、'
             '実測は <code>sotobori_terrain.json</code>。</b>この頁はその三つから組んだもので、実装は読んでいない。</p>')
    sv = {r["id"]: r for r in ter["survey"]}
    nishi = sum(r["n"] for r in d["ishigaki"]["runs"] if byid_works(d, r))
    h.append('<div class="box"><p><b>三つの水面で扱いが違う</b> ── 08-22 のリセットが'
             '「水色の囲い」の内か外かで生死が分かれた。'
             '<b>00001</b>(堰〜虎ノ門)は囲いの中で無傷 ── 水面より下 <b>%.1f%%</b>・'
             'リセット直前と一致 <b>%.1f%%</b> なので<b>調査のみ</b>。'
             '囲いの外の <b>00002 / 00003</b>(虎ノ門の橋の東)は掘削が丸ごと戻り、水面より下は'
             'それぞれ <b>%.1f%% / %.1f%%</b> しか残っていない ── こちらが<b>掘り直しの対象</b>で、'
             '両岸の石垣 <b>%d 個</b>が土に埋まっている。%s</p></div>'
             % (sv["Sotobori_00001"]["curSubmergedPct"], sv["Sotobori_00001"]["curVsPreSamePct"],
                sv["Sotobori_00002"]["curSubmergedPct"], sv["Sotobori_00003"]["curSubmergedPct"],
                nishi, inline(html.escape(d["why"]["note"]))))

    plate(h, nx(), "位置と水系", "溜池 → 堰 → 虎ノ門 → 幸橋")
    fig(h, system_svg(d),
        cap="水位の段階は既存実装の設計値で、<b>この指図では動かさない</b>。"
            "溜池から堰(「どんどん」)で落ちた水は虎ノ門の堀へ入り、"
            "<b>虎ノ門の橋の堰でもう一段落ちて</b>この区間の水位になる。"
            "東端の先は東へ<b>幸橋御門 →(一区間)→ 汐留の土橋 → 汐留川</b>の順で、いずれも未再現。")
    fig(h, plan_svg(d, dem, ter, "plain"),
        cap="平面。<b>青=水面 / 灰=石垣の run / 灰の破線=非史実の仮設 / 赤の破線=工区の境</b>。"
            "堀は虎ノ門の橋の東面から東南東へ下り、幸橋方向で切れる。"
            + inline(html.escape(d["scope"]["naming"])))

    plate(h, nx(), "現況調査", "三つの水面を同じ物差しで測る")
    h.append(survey_table(ter))
    h.append('<p class="cap">⛔ <b>00001 は1セルも触らない。</b>現況が 08-22 リセット直前と'
             '完全に一致しており、<b>2026-08-10 に建てたときからこの姿</b>である。'
             '水面より上に出ている所の主なものは堰の頭と虎ノ門の橋 ── どちらも構造物であって'
             '掘り残しではない。⛔ <b>「乾きの9割は汀線から4m以内の縁」という前版の説明は撤回した</b> ── '
             '物差しが「汀線からの距離」で、<b>水面より何m高いか</b>を測っていなかった(2026-08-26 検図)。'
             '⚠ 数値は<b>溜池の掘り直し(2026-08-26)の直前</b>のスナップショットによる。'
             '⭐ その工事が堰の頭に及んでいるかは <b>2026-08-30 に実機で確かめ済</b>で、'
             '00001 の本体にも工区にも掛かっていない(U8 解決)。</p>')

    plate(h, nx(), "現況図", "段彩 + 等高線 1m ── 造成リセット後の地面")
    fig(h, plan_svg(d, dem, ter, "cur"), legend=low_legend(),
        cap="<b>虎ノ門の橋の東(00002・00003)は汀線の内側がほぼ全面、水面 %.2f より上の陸になっている</b>のが"
            "読み取れる。上流の 00001(破線の汀線)は掘れたままで、段彩がそこだけ寒色に沈む。"
            "段彩のランプはこの低地用に 0〜8m で別に持つ(屋敷の指図の 10m 起点のランプでは全部同じ色になる)。"
            "赤の一点鎖線は横断の切り位置。"
            % [b["waterY"] for b in d["water"] if b.get("works")][0])

    plate(h, nx(), "掘削平面図", "切盛 ── 寒色=掘る / 暖色=盛る")
    fig(h, plan_svg(d, dem, ter, "cf"), legend=cutfill_legend(),
        cap="工区(掘る水面の汀線 + %.0f m)の中だけを塗った。<b>その外は1セルも触らない。</b>"
            "朱の破線の矩形は<b>凍結域 K1</b>(虎ノ門枡形と虎ノ門の橋の足元)で、"
            "帯がここを覆うと生き残っている造成を最大 %.2f m 掘り落とすため、帯から外してある。"
            "⛔ <b>掘り直しの西端は虎ノ門の橋の東面。</b>"
            % (d["works"]["outerWidth"], ter["provenance"]["survMaxPreCurDiff"]))
    h.append(spec_table(d, ter))

    plate(h, nx(), "縦断面", "距離程 %.0f m ── 水位は一定・地盤は東へ下る" % ter["reachLength"])
    fig(h, profile_svg(d, ter),
        cap="<b>水位と床は全区間で一定</b>(段差は虎ノ門の橋の堰で作る)。"
            "現況の地盤は西の 6m 台から東の 3m 台まで下るので、"
            "<b>西では深く掘り、東では岸を盛る</b>。石垣の天端も東へ向かって下がる。")

    for s in ter["sections"]:
        note = [x["note"] for x in d["sections"]["list"] if x["mark"] == s["mark"]][0]
        plate(h, nx(), "横断面 %s" % s["mark"], "距離程 %.0f m ／ %s" % (s["chainage"], s["body"]))
        if s["works"]:
            cap = ("<b>┄ 現況 / ── 設計 / 寒色の塗り = 掘る量</b>。%s。"
                   "⛔ <b>堀の壁は垂直のまま残す</b> — 溜池の掘り直しのように 45°で均すと"
                   "石垣の面が土に埋まり、堀が皿になる。" % inline(html.escape(note)))
        else:
            cap = ("<b>調査断面 — 掘らないので設計 = 現況で、線は重なる。</b>%s。"
                   "この一枚が<b>無傷の堀の姿</b>で、虎ノ門の橋の東はこれが失われた状態にある。"
                   "⚠ 郭外の石垣の天端が地面のずっと下にあるのが読み取れる(未解決 U9)。"
                   % inline(html.escape(note)))
        fig(h, section_svg(d, s), cap=cap)

    plate(h, nx(), "工区と摺り付け", "規則 ①〜⑥")
    fig(h, rule_svg(d))
    h.append("<ul class='prose'>%s</ul>"
             % "".join("<li>%s</li>" % inline(html.escape(r)) for r in d["works"]["rule"]))
    pv = ter["provenance"]
    h.append('<div class="box"><p><b>種地の出所の検算</b> ── 工区の中で現況が自然地形と 0.3m 超'
             'ちがう(=08-22 のリセットを生き延びた造成の)セルは <b>%d 個</b>。そのうち種地と現況が'
             '一致するのは <b>%.1f%%</b>(最大差 %.2f m)にすぎない。'
             '⛔ <b>初版はここを「一致する」と書いていたが、通っていなかった</b> ── 種地をそのまま'
             '戻すと生き残っている枡形・橋を最大 %.2f m 掘り落とすところだった。'
             'そこで虎ノ門の橋の足元を<b>凍結域 K1</b> として帯から外した結果、'
             '<b>不一致のまま帯で動くセルは %d 個</b>まで落ちた'
             '(水面の内側で動く %d 個は、虎ノ門の橋を貫く水路を床まで掘るもので設計どおり)。'
             '⚠ この検算は工区を広げれば成り立たなくなるので、広げるときは必ず取り直すこと。</p></div>'
             % (pv["survivingGradingCells"], pv["survSamePreCurPct"], pv["survMaxPreCurDiff"],
                pv["survMaxPreCurDiff"], pv["survMovedInBandCells"], pv["survMovedInWaterCells"]))
    h.append("<h4>やってはならないこと</h4>")
    h.append("<ul class='prose'>%s</ul>"
             % "".join("<li>⛔ %s</li>" % inline(html.escape(r)) for r in d["works"]["forbid"]))

    plate(h, nx(), "石垣との取り合い", "背面の地盤が天端の直下にあるか")
    h.append(back_table(d, ter))
    h.append('<p class="cap">石垣は <b>1個も動かさない</b>(CLAUDE.md 絶対規則1)。'
             '底は y=0 にあり、床はその %.2f m 上に来るので、掘っても石垣は浮かない。'
             '測るのは<b>背面(陸側4m)の設計地盤が天端の直下にあるか</b>で、'
             '天端 − 地盤が 0 に近いほど土留めとして正しく立っている。'
             '⚠ 短い折れ(NE3f・SW3b・END3)は評価点が数点しかないので、'
             '中央値だけで合否を決めず<b>実装後に目視で確かめる</b>。'
             '⚠ <b>最大の外れ値は 00002 と 00003 の継ぎ目に集まる</b>(SW3b・NE3g) — '
             '継ぎ目では石垣の背後に<b>溝が残る</b>。'
             '⛔ その量と原因の診断は<b>未解決 U7 が正典</b>で、ここには数値を写さない'
             '(2026-08-28 に写した値は 2026-08-30 に撤回された)。'
             '⚠ SW2 の最小が負なのは西端の虎ノ門寄りで<b>現況の地面がもともと天端より高い</b>ため。'
             '⚠ 00001 の run(CW1s・CW1n・R1・R3)は<b>合否の対象ではない</b> — 掘らないので'
             '設計地盤 = 現況で、断面の形も 00002・00003 と違う(次の表を見ること)。</p>'
             % [b["floor"] for b in d["water"] if b.get("works")][0])

    h.append("<h4>石垣が土に埋まっていないか(run 線そのもので測る)</h4>")
    h.append(buried_table(d, ter))
    h.append('<p class="cap">⚠ <b>00001 の郭外の CW1s(Ishigaki_Ext_4・86駒)は天端が地面に潜る。</b>'
             '虎ノ門の橋の取付の R1・R3 も同様。'
             'これは 08-22 のリセットのせいではない ── <b>現況と 08-22 リセット直前が一致</b>しており、'
             '2026-08-10 に建てたときからこの姿である。'
             '<b>この指図では直さない</b>(00001 は調査のみ。汀線と地形の是正は 2026-08-29 に実施済=U9)。'
             '⭐ 2026-08-30 に 00001 の run 線(ピボット)を実測へ直し(CW1s で 8.5〜8.9m 動いた)、'
             '<b>08-31 に組み直したので上の値は実測の線で採ったもの</b>である。</p>')

    plate(h, nx(), "施工の段階", "地形の編集は Undo の外 ── 2026-08-31 実施済")
    h.append(stage_table(d))
    pw = ter.get("postWork2026_0831")
    if pw:
        a = pw["applied"]
        h.append('<p class="cap">⭐ <b>%s に実施した。</b>%s '
                 '設計どおり動いたセル <b>%s(%s m²)</b>／工区 %s m²、'
                 '設計面との最大誤差 <b>%.3f m</b>(%s)。%s</p>'
                 % (pw["date"], inline(html.escape(pw["what"])),
                    "{:,}".format(a["cellsMoved"]), "{:,}".format(a["m2"]),
                    "{:,}".format(a["workAreaM2"]), a["maxErrorVsDesign_m"],
                    inline(html.escape(a["note"])), inline(html.escape(pw["baseline"]))))
        inc = pw["incident"]
        h.append('<div class="box"><p><b>⛔ 施工中に踏んだ事故(復旧済)</b><br>'
                 '%s<br><b>原因</b> ── %s<br><b>なぜ検算が見逃したか</b> ── %s<br>'
                 '<b>復旧</b> ── %s<br>%s</p></div>'
                 % (inline(html.escape(inc["what"])), inline(html.escape(inc["cause"])),
                    inline(html.escape(inc["whyMissed"])), inline(html.escape(inc["recovered"])),
                    inline(html.escape(inc["rule"]))))
        rows = ["<tr><td><code>%s</code></td><td class='note' style='text-align:left'>%s</td>"
                "<td>%s</td><td class='note' style='text-align:left'>%s</td></tr>"
                % (c["id"], inline(html.escape(c["measured"])), html.escape(c["verdict"]),
                   inline(html.escape(c.get("note", "—"))))
                for c in pw["checks"]]
        h.append("<h4>施工後の検査(実測)</h4>")
        h.append(tbl(["id", "実測", "判定", "註"], rows))
    plate(h, nx(), "検査", "1件でも落ちたら退避から戻す")
    h.append(check_table(d))
    plate(h, nx(), "考証と決めごと", "文章の正典は sotobori_kosho.md")
    h.append('<div class="prose">%s</div>' % prose)
    plate(h, nx(), "未解決", "推定で埋めない対象")
    h.append('<p class="cap">%s</p>' % inline(html.escape(d["unresolvedNote"])))
    h.append(pending_table(d))
    plate(h, nx(), "改訂", "経緯は git log docs/Sashizu/")
    h.append(history())
    h.append('<p class="cap" style="margin-top:44px">@@PLATES@@。'
             '<b>組み直すときは図を落としていないか必ず数える。</b></p>')
    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>sotobori_sashizu.json</code> ／ '
             '文章 <code>sotobori_kosho.md</code> ／ 実測 <code>sotobori_terrain.json</code>。'
             'Y は海抜 m(Unity の Y がそのまま標高)。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")      # 最後の章
    h.append("</div>")      # .wrap
    out = "\n".join(h)
    nsvg = out.count("<svg")
    out = out.replace("@@PLATES@@", "章 %d ／ 図版(SVG) %d 面" % (n[0], nsvg))
    open(OUT, "w", encoding="utf-8").write(out)
    print("wrote %s ／ 章 %d ／ 図版(SVG) %d 面 ／ %.0f KB"
          % (OUT, n[0], nsvg, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
