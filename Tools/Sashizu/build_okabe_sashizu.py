#!/usr/bin/env python3
"""岡部内膳正上屋敷(和泉岸和田藩 五万三千石)の指図を組む。

**正典は docs/Sashizu/okabe_sashizu.json**(寸法)と okabe_kosho.md(文章)。
この生成器は数値を持たない — 図も表もキャプションも json/md から引く。

座標は**回転間グリッド shukaku**: 原点=表門の芯、u=東辺(三べ坂)沿いに北、v=敷地の奥(西)へ。
東辺は世界軸から 5.71° 振れる。1間=1.818m。Y は海抜m。

章は本文の並び順に自動採番する(其一〜)。**図番を生成器に書かない。**
"""
import json, math, os, re, subprocess, html

import sashizu_lib
from sashizu_lib import (R, _pat, _SVN, Proj, RGrid, cf_color, cutfill_legend,
                         dem_color, _iso, dem_legend, slope_table, links_table,
                         _edge_dir, mune_contacts_table)  # バイト同一を実証済みの共通部

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "okabe_sashizu.json")
MD = os.path.join(DOC, "okabe_kosho.md")
OUT = os.path.join(DOC, "okabe_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown(岡部と同じ最小変換)
def md2html(text):
    out, i, lines = [], 0, text.split("\n")
    while i < len(lines):
        ln = lines[i]
        # ⚠ 表とリストは**字下げされていても拾う**(箇条書きの中の表が生で出ていた・2026-08-24 考証)
        if ln.lstrip().startswith("|") and i + 1 < len(lines) \
                and lines[i + 1].strip() and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            out.append('<div class="tw"><table><thead><tr>'
                       + "".join("<th>%s</th>" % inline(h) for h in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join('<td class="note">%s</td>' % inline(c) for c in r) + "</tr>" for r in rows)
                       + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            tag = {1: "h1", 2: "h2", 3: "h3", 4: "h4"}[len(m.group(1))]
            out.append("<%s>%s</%s>" % (tag, inline(m.group(2)), tag)); i += 1; continue
        if ln.startswith("- "):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  ")):
                if lines[i].startswith("- "):
                    items.append(inline(lines[i][2:]))
                elif items:
                    items[-1] += " " + inline(lines[i].strip())
                i += 1
            out.append("<ul>" + "".join("<li>%s</li>" % t for t in items) + "</ul>"); continue
        if ln.strip() == "---":
            out.append('<hr class="rule">'); i += 1; continue
        if ln.strip() == "":
            i += 1; continue
        buf = []
        while i < len(lines) and lines[i].strip() \
                and not lines[i].lstrip().startswith(("#", "- ", "|")) and lines[i].strip() != "---":
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def inline(s):
    s = re.sub(r'</?span[^>]*>', "", s)
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    s = re.sub(r"【([^】]*確度 ?[SABPU?][^】]*)】", r'<span class="cert">【\1】</span>', s)
    s = re.sub(r"【(写真=A[^】]*)】", r'<span class="cert">【\1】</span>', s)
    return s


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

KC = {"Nagaya": "var(--nagaya)", "Dobei": "var(--hei)"}

MUNE_JA = {
    "Kurumayose": "車寄", "Genkan": "玄関棟", "Shoin": "書院棟", "Nakaoku": "中奥棟",
    "Daidokoro": "台所棟", "Okumuki": "奥向棟", "Nagatsubone": "長局",
    "Oku": "奥棟", "Umaya": "厩棟",
}
sashizu_lib.MUNE_JA = MUNE_JA  # lib の mune_contacts_table が引く棟名辞書を差す
TERR_JA = {"Monzen": "門前面", "Shumen": "主面"}


# ---------------------------------------------------------------- 其一 敷地
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


def tin(t, u, v):
    """(u,v) が段の中か。多角形なら crossing number、矩形なら範囲判定。"""
    if not t.get("poly"):
        return t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9
    p = tpoly(t); n = len(p); c = False
    for i in range(n):
        (au, av), (bu, bv) = p[i], p[(i + 1) % n]
        if (av > v) != (bv > v) and u < (bu - au) * (v - av) / (bv - av) + au:
            c = not c
    return c


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


def tarea(t):
    """段の面積[間²]。"""
    p = tpoly(t); n = len(p)
    return abs(sum(p[i][0] * p[(i + 1) % n][1] - p[(i + 1) % n][0] * p[i][1] for i in range(n))) / 2


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
    隅では法線が交わるぶん詰まるので、一律「0.45m」と書かず実距離を出す。"""
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
    off = (d["const"]["inubashiri"] + 0.15) / K
    out = []
    for t in d["terraces"]:
        poly = tpoly(t)
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
            for k in range(L):
                p0 = (a[0] + ex * k / L, a[1] + ey * k / L)
                p1 = (a[0] + ex * (k + 1) / L, a[1] + ey * (k + 1) / L)
                mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
                g = _dem_at(d, mx + nx * 1.2, my + ny * 1.2)
                ok = (g is not None and (t["y"] - g) >= 1.0 and in_parcel(d, mx, my)
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
            if L < 9.0:
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
        if not str(r.get("on", "")).startswith("面の縁"):
            continue
        e = r["edge"]; a, b = Pg[e], Pg[(e + 1) % len(Pg)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / L, dx / L
        if (a[0] + nx - cu) ** 2 + (a[1] + ny - cv) ** 2 > \
           (a[0] - nx - cu) ** 2 + (a[1] - ny - cv) ** 2:
            nx, ny = -nx, -ny
        n = 0; bad = 0; mx = 0.0
        sv = r["s0"]
        while sv <= r["s1"]:
            t = sv / K / L
            u = a[0] + dx * t + nx * (1.2 / K); v = a[1] + dy * t + ny * (1.2 / K)
            nat = _dem_at(d, u, v)
            if nat is not None:
                g = graded_y(d, u, v, nat, we)
                g = nat if g is None else g
                n += 1
                if rseat(r, sv) - g > 0.5:
                    bad += 1; mx = max(mx, rseat(r, sv) - g)
            sv += 1.0
        if bad:
            out.append((r["name"], bad, n, round(mx, 2)))
    return out


def plinth_check(d):
    """**隣家が自分の側に建てている基壇の天端を、当家の塀の据面が下回っていないか。**
    下回ると隣家の土が当家の塀の足元より高くなる(2026-08-24 検図)。"""
    bad = []
    for pl in d.get("neighborPlinth", []):
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


def _run_exposure(d, r, sv):
    """run の走り sv における基壇の露出(天端 − その位置の地盤)。"""
    prof = d.get("edgeProfile", {}).get(str(r["edge"]))
    if not prof:
        return 0.0
    if sv <= prof[0][0]:
        gy = prof[0][1]
    else:
        gy = prof[-1][1]
        for (a1, y1), (b1, y2) in zip(prof, prof[1:]):
            if a1 <= sv <= b1:
                gy = y1 + (y2 - y1) * (sv - a1) / (b1 - a1)
                break
    return rseat(r, sv) - gy


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
    for o in d["munes"] + d["service"] + d["gardens"] + d["links"] + d.get("wells", []):
        t = o.get("_")
        if not isinstance(t, str):
            continue
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
            [(s["name"], s["u0"], s["v0"], s["u1"], s["v1"]) for s in d["service"]] + \
            [(g["name"], g["u0"], g["v0"], g["u1"], g["v1"]) for g in d.get("gardens", [])]
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
        for nm, u0, v0, u1, v1 in boxes:
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
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2) if xs[i + 1] - xs[i] > 1e-6]


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
    g = _sv(pr.W, pr.H, "岡部内膳正上屋敷 敷地全体")

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
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]),
                    KC.get(r["kind"], "var(--dim)"), 5 if r["kind"] == "Nagaya" else 3.4, cap="round"))
    # 郭の土留め
    for w in d["terraceWalls"]:
        a = gr.W(*w["a"]); b = gr.W(*w["b"])
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]), "var(--ishi)", 3, dash="7 4"))
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


# ---------------------------------------------------------------- 其二・其三 御殿平面(グリッド座標)
def plan_frame(d, tname, pad=3.0):
    """平面図の枠を**段の外接矩形から算出**する(手で持つと棟を動かすたびに腐る)。
    ⚠ 2026-08-25 検図: 手書きの枠が主面の 7.2% を切り落とし、`KN_Sh1 家臣長屋(主面1)` が
    どの平面図にも載らなくなっていた(断面の見出しには出るので図の中で矛盾していた)。"""
    t = next(x for x in d["terraces"] if x["name"] == tname)
    pts = tpoly(t)
    us = [p[0] for p in pts]; vs = [p[1] for p in pts]
    for o in d["munes"] + d["service"] + d["gardens"] + d["links"]:
        if abs(o.get("y", t["y"]) - t["y"]) > 0.6:
            continue
        us += [o["u0"], o["u1"]]; vs += [o["v0"], o["v1"]]
    return (math.floor(min(us) - pad), math.ceil(max(us) + pad),
            math.floor(min(vs) - pad), math.ceil(max(vs) + pad))


def goten_plan(d, u0, u1, v0, v1, label, note):
    """段の平面。**枠外の要素は clipPath で切る**(2026-08-23 検図: 枠の外にテキストが残っていた)。"""
    pr = LProj(u0, u1, v0, v1, 900.0)
    g = _sv(pr.W, pr.H, "岡部内膳正上屋敷 %s" % label)
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
        (a_u, a_v), (b_u, b_v) = w["a"], w["b"]
        if not vis(min(a_v, b_v), max(a_v, b_v), min(a_u, b_u), max(a_u, b_u)):
            continue
        if a_u == b_u:
            g.append(pr.rect(a_u - 0.66, max(min(a_v, b_v), v0), a_u + 0.66, min(max(a_v, b_v), v1),
                             fill=_pat(), stroke="var(--ishi)", sw=1.0))
        else:
            g.append(pr.rect(max(min(a_u, b_u), u0), a_v - 0.66, min(max(a_u, b_u), u1), a_v + 0.66,
                             fill=_pat(), stroke="var(--ishi)", sw=1.0))
        g.append(T(pr.X(max(a_u, b_u) - 1), pr.Y(max(min(a_v, b_v), v0) + 1.6), w["name"], "jo"))
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
    for rp in d.get("ramps", []):                       # 坂(斜面を勾配で登る道)
        pts = [(pr.X(u), pr.Y(v)) for u, v in rp["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="var(--nagaya)" stroke-width="%.1f" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.55"/>'
                 % (" ".join("%.1f,%.1f" % q for q in pts), max(4.0, pr.L(rp["w"] / 1.818))))
        g.append(T(pts[len(pts) // 2][0], pts[len(pts) // 2][1] - 7,
                   "%s 全長%.0fm 最急%.1f%%" % (rp["label"], rp["len"], rp["gradMax"]), "anS2", "middle"))
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
    """その (u,v) を覆う段の高さ。無ければ None(=造成しない斜面)。区画の外では常に None。"""
    if not in_parcel(d, u, v):
        return None
    best = None
    for t in d["terraces"]:
        if tin(t, u, v):
            best = t["y"] if best is None else max(best, t["y"])
    return best


def walled_edges(d, t):
    """段 t の四辺のうち、土留めが載っている辺。法面でなく垂直に納まる。"""
    out = set()
    for w in d["terraceWalls"]:
        if abs(w["coping"] - t["y"]) > 0.05:
            continue
        (au, av), (bu, bv) = w["a"], w["b"]
        if abs(au - bu) < 1e-9:                       # u=const の壁
            if min(av, bv) < t["v1"] - 0.4 and max(av, bv) > t["v0"] + 0.4:
                if abs(au - t["u0"]) < 1e-6:
                    out.add("u0")
                if abs(au - t["u1"]) < 1e-6:
                    out.add("u1")
        else:                                          # v=const の壁
            if min(au, bu) < t["u1"] - 0.4 and max(au, bu) > t["u0"] + 0.4:
                if abs(av - t["v0"]) < 1e-6:
                    out.add("v0")
                if abs(av - t["v1"]) < 1e-6:
                    out.add("v1")
    return out


EDGE_DEAD = 0.30     # 縁が地山と同高とみなす不感帯。切盛図の「無彩=±0.3m」と揃える


_EDGEFILL = {}


def edge_is_fill(d, t, u, v, ter=None):
    """段 t の縁のうち (u,v) に最も近い点が**盛土の縁か**を返す(法面の関門①)。
    縁が地山と同高なら、その外へ盛土の法面を出してはならない — 出すと法尻が着地せず、
    cap で切れて垂直の段差が生える(2026-08-23 検図で 55 箇所・最大1.58m を検出)。"""
    key = (id(d), t["name"])
    if key not in _EDGEFILL:
        pts = []
        poly = tpoly(t)
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            L = max(int(math.hypot(b[0] - a[0], b[1] - a[1])), 1)
            for k in range(L):
                q = (a[0] + (b[0] - a[0]) * k / L, a[1] + (b[1] - a[1]) * k / L)
                g = _dem_at(d, q[0], q[1])
                pts.append((q[0], q[1], None if g is None else (t["y"] - g)))
        _EDGEFILL[key] = pts
    pts = _EDGEFILL[key]
    # **縁に沿って連続にする** — 最近傍1点だと縁の標本の間で値が跳ね、法面に段差が出る。
    near = sorted(((a - u) ** 2 + (b - v) ** 2, f) for (a, b, f) in pts if f is not None)[:4]
    if not near:
        return None
    if near[0][0] < 1e-9:
        return near[0][1]
    w = sum(1.0 / dd for dd, _ in near)
    return sum(f / dd for dd, f in near) / w


def _nat_grad(d, u, v):
    """江戸期地盤のその場の勾配(m/間 → 無次元)。崖かどうかの判定に使う。"""
    a = _dem_at(d, u + 0.5, v); b = _dem_at(d, u - 0.5, v)
    c = _dem_at(d, u, v + 0.5); e = _dem_at(d, u, v - 0.5)
    if None in (a, b, c, e):
        return 0.0
    K = d["const"]["ken"]
    return math.hypot(a - b, c - e) / K


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


def graded_y(d, u, v, nat, walled=None):
    """**造成後の地盤**。段の中は段の高さ。段の外は法面(盛土 1:1.5 / 切土 1:1)で現地形へ摺り付ける。
    **段の縁は等高線に沿った多角形**なので、距離は縁からの最短距離で測る。
    どこも触らない点では nat と同じ値を返すので、差がゼロ=無造成。"""
    ins = design_y(d, u, v)
    if ins is not None:
        return ins
    if nat is None:
        return None
    if not in_parcel(d, u, v):
        return nat                      # **区画の外は一切動かさない**(街路・隣地)
    K = d["const"]["ken"]
    bf = d["const"].get("batterFill", 1.5)
    bc = d["const"].get("batterCut", 1.0)
    cap = d["const"].get("featherCap", 12.0)
    g = nat
    for t in d["terraces"]:
        dm = tdist(t, u, v) * K
        if dm > cap:
            continue
        ef = edge_is_fill(d, t, u, v)      # 段の縁での盛土(+)/切土(−)の厚み
        if ef is None:
            continue
        # **関門③: 地山がすでに法面より急な所は崖・石垣の領分。法面を出さない。**
        #   出すと造成が自然より急になり、法尻に段差が生える(2026-08-24 検図)。
        if _nat_grad(d, u, v) > 0.75 * (1.0 / bc if ef < 0 else 1.0 / bf):
            continue
        # **法面は「縁の土の厚みが 0 へ逓減する」形で出す。**
        #   盛土: 縁で ef、そこから 1:bf の勾配で薄くなり、距離 ef*bf で地山に着く。
        #   切土: 同じく 1:bc。
        # 縁から一定勾配の平面を伸ばす旧式は、地山のほうが急なとき永久に着地せず、
        # cap で切れて法尻に垂直の段差を生んだ(2026-08-23 検図で55箇所・最大1.58m)。
        # この形なら **定義上かならず着地し、段差が生じない**(sashizu.md §3b の関門③)。
        if ef > 0.0:
            g = max(g, nat + max(0.0, ef - dm / bf))
        elif ef < 0.0:
            g = min(g, nat - max(0.0, -ef - dm / bc))
    return g


def cutfill_svg(d, ter):
    """切盛図。造成前の地形(実測)と設計の面の差を、格子のセル塗りで示す。"""
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), 900.0, pad=14.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "岡部内膳正上屋敷 切盛図")
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
            if abs(dz) < 0.05:
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
    g = _sv(pr.W, pr.H, "岡部内膳正上屋敷 復元の効き方")
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
    g = _sv(pr.W, pr.H, "岡部内膳正上屋敷 現況図(造成前の地形)")
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
    g = _sv(pr.W, pr.H, "岡部内膳正上屋敷 動線")
    P = [gr.L(x, z) for x, z in d["polygon"]]
    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.5"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    for t in d["terraces"]:
        g.append(pr.poly(tpoly(t),
                         fill=dan_color(d, t["y"]), op=1.0))
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
        for rp2 in d.get("ramps", []):
            if math.hypot(u0 - rp2["pts"][0][0], v0 - rp2["pts"][0][1]) < 4:
                ys.append(rp2["prof"][0][2])
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
            tops.append(m["y"] + fl0 + sec["ridgeAbove"])
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

    g = _sv(W, H, "岡部内膳正上屋敷 %s" % sec["name"])
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
        f = m["y"] + fl
        nm = MUNE_JA.get(m.get("name"), m.get("label", m.get("name", "")))
        if "label" in m and m["name"] not in MUNE_JA:
            nm = m["label"]
        g.append('<polygon points="%s" fill="var(--ink-mid)" stroke="var(--ink)" stroke-width="1.2"/>'
                 % " ".join("%.1f,%.1f" % p for p in
                            [(X(a), Y(f)), (X(a), Y(f + eave)),
                             ((X(a) + X(b)) / 2, Y(f + ridge)),
                             (X(b), Y(f + eave)), (X(b), Y(f))]))
        g.append(T((X(a) + X(b)) / 2, Y(f + eave) + 12, nm, "rmS", "middle",
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
        run = next((r for r in d["runs"] if r["edge"] == be and r["s0"] - 0.5 <= bs <= r["s1"] + 0.5), None)
        if run is None:
            continue                                  # 門の開口
        hh = 5.3 if run["kind"] == "Nagaya" else d["const"]["dobeiH"]
        seat = rseat(run, bs)                         # 天端は一直線(水平 or 一定勾配)
        # ⛔ **基壇の足元は `edgeProfile` から取る**(断面の地盤線からではない)。
        #    同じ壁の露出が「断面の地盤」と「外周の展開」の二つの基準面から出ていて、
        #    27箇所中16箇所が 0.30m 超ずれ、2本は断面上で壁が土に埋もれていた(2026-08-25 検図)。
        gy = seat - _run_exposure(d, run, bs)
        if seat > gy + 0.05:                          # 基壇石垣
            bt9 = 2.4 * run["s"]          # 基壇の底厚(設計値)。固定1.8mで描いていた
            g.append(R(X(w) - sx * bt9 / 2, Y(seat), sx * bt9, (seat - gy) * sx * ex,
                       fill=_pat(), stroke="var(--ishi)", sw=1.0))
        wt9 = d["const"]["dobeiT"]        # 練塀の厚さ(設計値)。固定1.4mで描いていた
        g.append(R(X(w) - sx * wt9 / 2, Y(seat + hh), sx * wt9, hh * sx * ex,
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


# ---------------------------------------------------------------- 其六 外周の展開
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
        while k <= L:
            t = k / (L or 1)
            x = a[0] + (b[0] - a[0]) * t + nx0 * 1.0
            z = a[1] + (b[1] - a[1]) * t + nz0 * 1.0
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
        rows.append("<tr><td>辺%d</td><td>%.1fm</td><td>%s</td><td><code>%s</code></td>"
                    "<td class='note'>%s</td></tr>"
                    % (i, L, e.get("neighbor", ""),
                       " ".join(own.get(i, [])) or "—(当家は建てない)",
                       inline(e.get("_", ""))))
    return ("<h3>辺と隣地(全%d辺)</h3><div class='tw'><table><thead><tr><th>辺</th><th>長さ</th>"
            "<th>隣は誰か</th><th>当家の囲い</th><th class='note'>注記・典拠</th>"
            "</tr></thead><tbody>%s</tbody></table></div>" % (n, "".join(rows)))


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
    nagH = 5.3
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
    for pl in d.get("neighborPlinth", []):
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


# ---------------------------------------------------------------- 其七 表門まわり
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
    # 両翼の練塀
    for x0 in (0.0, total - wing):
        g.append(R(X(x0), Y(4.3), X(wing), 4.3 * sx, fill="var(--nagaya)", op=0.55))
        g.append(R(X(x0) - 3, Y(4.3) - 9, X(wing) + 6, 9, fill="var(--ink-lo)"))
    g.append(T(X(wing / 2), Y(4.9), "練塀(外構練塀潰=安政地震の記録)", "anS2", "middle"))
    # 長屋門の躯体(一段高い屋根)
    g.append(R(X(wing), Y(monH - 0.8), X(monW), (monH - 0.8) * sx, fill="var(--nagaya)", op=0.85))
    g.append(R(X(wing) - 4, Y(monH - 0.8) - 12, X(monW) + 8, 12, fill="var(--ink-lo)"))
    # 門口(中央)
    g.append(R(X(wing + monW / 2 - 1.8), Y(3.2), X(3.6), 3.2 * sx, fill="var(--paper2)", stroke="var(--ink)", sw=1.2))
    g.append(R(X(wing + monW / 2 - 1.7), Y(3.0), X(1.6), 3.0 * sx, fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
    g.append(R(X(wing + monW / 2 + 0.1), Y(3.0), X(1.6), 3.0 * sx, fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
    g.append(T(X(wing + monW / 2), Y(3.4), "門口(内開き・潜り戸)", "anS2", "middle"))
    # 出格子番所(躯体内・両側)
    for cx in (wing + monW * 0.22, wing + monW * 0.78):
        g.append(R(X(cx - 1.6), Y(2.4), X(3.2), 1.9 * sx, fill="var(--dan)", stroke="var(--ink)", sw=1.0))
        for i in range(8):
            xx = X(cx - 1.4 + i * 0.36)
            g.append(LN(xx, Y(2.3), xx, Y(0.7), "var(--ink)", 0.8, op=0.75))
    bnm = d["gate"]["plan"].get("bansho", {}).get("kind", "番所")
    g.append(T(X(wing + monW * 0.22), Y(2.8), bnm, "anS2", "middle"))
    g.append(T(X(wing + monW * 0.78), Y(2.8), bnm, "anS2", "middle"))
    g.append(LN(0, GY, W, GY, "var(--ink)", 1.6))
    g.append(T(4, GY + 16, "三べ坂前身の南北道。敷居=門前面の地盤=道なり", "anS2", "start"))
    g.append(T(4, 15, "正面見付(概略・等倍)。型式=現存実例2件[山脇]A・[西澄寺]A ＋ 格式階梯B/実在と被災=安政地震の記録(S)", "anS"))
    g.append("</svg>")

    # 平面
    W2, H2 = 980.0, 200.0
    s2 = W2 / total
    wy = 100.0
    g2 = _sv(W2, H2, "表門(長屋門)平面")

    def X2(m): return m * s2
    g2.append(R(0, wy - 8, X2(wing), 16, fill="var(--nagaya)", op=0.85))
    g2.append(R(X2(total - wing), wy - 8, X2(wing), 16, fill="var(--nagaya)", op=0.85))
    g2.append(R(X2(wing), wy - 10, X2(monW), 20, fill="var(--nagaya)", stroke="var(--ink)", sw=1.2))
    g2.append(R(X2(wing + monW / 2 - 1.8), wy - 10, X2(3.6), 20, fill="var(--paper2)", stroke="var(--ink)", sw=1.0))
    g2.append(T(X2(wing + monW * 0.22), wy + 2, "番所", "anS2", "middle"))
    g2.append(T(X2(wing + monW * 0.78), wy + 2, "番所", "anS2", "middle"))
    g2.append(T(X2(wing + monW / 2), wy - 16, "門口 3.6m", "anS2", "middle"))
    g2.append(T(4, H2 - 8, "長屋門の躯体(桁行%.1fm×梁間%.1fm)に番所が入る。両袖は**練塀**へ直に突き付ける(表長屋は0本)" % (monW, monD), "anS2", "start"))
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
                       inline(p.get("cert", "")), inline(p.get("note", ""))))
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
                       r.get("on", "—"), inline(r.get("cert", ""))))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>辺</th><th>走り s</th><th>長さ</th>'
            "<th>種別</th><th>天端 seat</th><th>基壇の露出</th><th>何の縁か</th>"
            "<th class='note'>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def walls_table(d):
    rows = []
    for w in d["terraceWalls"]:
        rows.append("<tr><td><code>%s</code></td><td>(%g,%g)-(%g,%g)</td><td>%.1f</td><td>%.2f</td>"
                    "<td>%.1f / %.2f / %.2f</td></tr>"
                    % (w["name"], w["a"][0], w["a"][1], w["b"][0], w["b"][1],
                       w["coping"], w["s"], 4.0 * w["s"], 1.4 * w["s"], 2.4 * w["s"]))
    return ('<div class="tw"><table><thead><tr><th>土留め</th><th>グリッド</th><th>天端</th><th>s</th>'
            "<th>壁高/天端幅/底厚</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def kenpei(d, area):
    K = d["const"]["ken"]
    gm = sum(abs(m["u1"] - m["u0"]) * abs(m["v1"] - m["v0"]) for m in d["munes"]) * K * K
    gl = sum(abs(l["u1"] - l["u0"]) * abs(l["v1"] - l["v0"]) for l in d["links"]) * K * K
    gs = sum(abs(s["u1"] - s["u0"]) * abs(s["v1"] - s["v0"]) for s in d["service"]) * K * K
    nag = sum((r["s1"] - r["s0"]) * d["const"]["nagayaD"] for r in d["runs"] if r["kind"] == "Nagaya")
    bs = d["gate"]["plan"]["bansho"]
    ban = bs["count"] * bs.get("w", 0) * bs.get("d", 0)   # 長屋門は番所が躯体内=別計上なし
    yag = sum((y["ken"] * K) ** 2 for y in d["yagura"])
    gp = d["gate"]["plan"]
    mon = gp["monW"] * gp.get("monD", 1.2) + 2 * gp.get("sode", 0) * 0.4 \
        + (d["onarimon"]["w"] * 1.5 if d.get("onarimon") else 0) \
        + sum(k["w"] * 1.2 for k in d["komon"])
    tot = gm + gl + gs + nag + ban + yag + mon
    return ('<div class="tw"><table><thead><tr><th></th><th>m²</th><th>坪</th></tr></thead><tbody>'
            "<tr><td>御殿の棟(入側とも)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>渡廊下・御錠口</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>付属屋(厩・供待・蔵・家臣長屋・中間足軽長屋)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>外周の長屋(run の kind=Nagaya)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>番所・門の躯体</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td><b>計</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            "<tr><td><b>敷地(分母)</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            '<tr><td><b>建蔽率</b></td><td colspan="2"><b>%.1f%%</b></td></tr>'
            "</tbody></table></div>"
            % (gm, gm / TSUBO, gl, gl / TSUBO, gs, gs / TSUBO,
               nag, nag / TSUBO,          # ⚠ 計に入るのに行が無かった(2026-08-25 検図)
               ban + yag + mon, (ban + yag + mon) / TSUBO,
               tot, tot / TSUBO, area, area / TSUBO, 100.0 * tot / area)), 100.0 * tot / area


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


def batter_check(d, ter):
    """法面の検査 — **造成が自然勾配より急にした所で、切土 1:bc を超えていないか**。
    旧式(縁から一定勾配の平面)は地山が急なとき着地せず、cap で切れて法尻に垂直の段差を生んだ。
    2026-08-23 の検図で55箇所・最大1.58m。逓減形へ改めたので、これが再発しないことを見張る。"""
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
    for g in d["gardens"]:
        pt = rect_out(g["u0"], g["v0"], g["u1"], g["v1"])
        if pt:
            bad.append("%s(庭) が区画の外: (%.2f, %.2f)" % (g["name"], pt[0], pt[1]))
            continue
        if g.get("slope"):
            continue
        pt = covered(g["u0"], g["v0"], g["u1"], g["v1"], None)
        if pt:
            bad.append("%s(庭) が段の外: (%.2f, %.2f)" % (g["name"], pt[0], pt[1]))
    for w in d["wells"]:
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
    # 段の多角形の頂点は区画の中、かつ区画線から犬走り+塀厚半分だけ内へ入っている
    clr = (d["const"]["inubashiri"] + d["const"]["dobeiT"] / 2.0) / d["const"]["ken"]
    for t in d["terraces"]:
        for i, (uu, vv) in enumerate(tpoly(t)):
            if not in_parcel(d, uu, vv):
                bad.append("%s(段) の頂点[%d] が区画の外: (%g, %g)" % (t["name"], i, uu, vv))
            elif par_dist(d, uu, vv) < clr - 1e-6:
                bad.append("%s(段) の頂点[%d] が区画線まで %.2fm(規定 %.2fm)"
                           % (t["name"], i, par_dist(d, uu, vv) * d["const"]["ken"],
                              clr * d["const"]["ken"]))
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
        if h < dr[1] - 0.05:
            bad.append("%s 壁高 %.2f < 最大落差 %.2f — 足りない" % (w["name"], h, dr[1]))
        elif h > dr[1] + 0.8:
            bad.append("%s 壁高 %.2f ≫ 最大落差 %.2f — 過大(埋まる)" % (w["name"], h, dr[1]))
        if dr[0] < 0.3:
            bad.append("%s は落差 %.2f の区間を含む — その区間は壁でなく法面にする" % (w["name"], dr[0]))
    return bad


def overlap_check(d):
    """矩形の総当たり重なり検査(棟・廊下・庭・付属屋)。接するは可、重なるは不可。
    ただし渡廊下が棟の外形(入側帯)に一間だけ乗り込むのは取り付きなので許す。"""
    boxes = []
    for m in d["munes"]:
        boxes.append(("mune", m["name"], m["u0"], m["v0"], m["u1"], m["v1"]))
    for l in d["links"]:
        boxes.append(("link", l["name"], l["u0"], l["v0"], l["u1"], l["v1"]))
    for n in d["gardens"]:
        boxes.append(("niwa", n["name"], n["u0"], n["v0"], n["u1"], n["v1"]))
    for s in d["service"]:
        boxes.append(("svc", s["name"], s["u0"], s["v0"], s["u1"], s["v1"]))
    # 井戸(半径0.5間)。⚠ 2026-08-24 検図: 対象外だったため W_Monzen が供待の躯体の中で素通りした
    for w in d.get("wells", []):
        boxes.append(("well", w["name"], w["u"] - 0.5, w["v"] - 0.5, w["u"] + 0.5, w["v"] + 0.5))
    # 外周 run と長屋門の躯体帯(表門の辺=グリッドの v=0 帯)。検図 H-3 で追加 —
    # 入れないと表長屋の奥行(4.5m)に厩などが食い込んでも素通しになる。
    ken2 = d["const"]["ken"]
    sg = d["gate"]["s"]
    for r in d["runs"]:
        if r["edge"] != d["gate"]["edge"]:
            continue
        depth = d["const"]["nagayaD"] if r["kind"] == "Nagaya" else d["const"]["dobeiT"]
        boxes.append(("run", r["name"], (r["s0"] - sg) / ken2, 0.0, (r["s1"] - sg) / ken2, depth / ken2))
    gp2 = d["gate"]["plan"]
    boxes.append(("run", "Nagayamon", -gp2["monW"] / 2 / ken2, 0.0,
                  gp2["monW"] / 2 / ken2, gp2["monD"] / ken2))
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            k1, n1, a0, b0, a1, b1 = boxes[i]
            k2, n2, c0, d0, c1, d1 = boxes[j]
            iu = min(a1, c1) - max(a0, c0)
            iv = min(b1, d1) - max(b0, d0)
            if iu > 1e-9 and iv > 1e-9:
                if {"link"} & {k1, k2}:
                    # 取り付き: 渡廊下は**長手方向に一間だけ**棟の外形(入側帯)へ乗り込める。
                    # 幅方向の一間重なりを盾に長手で何間も乗り込むのは不可(検図指摘)。
                    lk = boxes[i] if k1 == "link" else boxes[j]
                    llong = "u" if (lk[4] - lk[2]) >= (lk[5] - lk[3]) else "v"
                    along = iu if llong == "u" else iv
                    if along <= 1.0 + 1e-9:
                        continue
                if {k1, k2} == {"niwa", "svc"}:
                    # 庭の中に立つ亭・祠は庭に**完全に包含**されていれば可(庭は地面)
                    (nk, na, n0, n1_, n2_, n3), (sk, sa, s0, s1_, s2_, s3) = \
                        (boxes[i], boxes[j]) if k1 == "niwa" else (boxes[j], boxes[i])
                    if n0 <= s0 and n1_ <= s1_ and s2_ <= n2_ and s3 <= n3:
                        continue
                bad.append("%s %s × %s %s (%.1f×%.1f間)" % (k1, n1, k2, n2, iu, iv))
    return bad


# ---------------------------------------------------------------- 其十 取り合い(実装用・自動算出)


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
        dx1, dz1, _ = _edge_dir(P, prev_e)
        dx2, dz2, _ = _edge_dir(P, next_e)
        delta = math.degrees(math.acos(max(-1, min(1, dx1 * dx2 + dz1 * dz2))))
        if rl is None or rr is None:
            osame = "—"
        elif i in yag:
            osame = "隅櫓 %s が受ける" % yag[i]["name"]
        elif rl["kind"] == "Nagaya" and rr["kind"] == "Nagaya":
            osame = "長屋は退けて桁を突き付け(ebc11da の作法)"
        elif rl["kind"] == "Dobei" and rr["kind"] == "Dobei":
            osame = "留め継ぎ隅部材(build_kado・折れ角は現地=Δ%.1f°)" % delta
        elif abs((rseat(rr, rr["s0"]) if rr else 0) - (rseat(rl, rl["s1"]) if rl else 0)) > 0.3:
            osame = "天端差は高い側の基壇小口(隅石)で受ける"
        else:
            osame = "天端同高で留め継ぐ"
        yl = rseat(rl, rl["s1"]) if rl else 0.0
        yr = rseat(rr, rr["s0"]) if rr else 0.0
        ds = (yr - yl) if (rl and rr) else 0.0
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
                       rp["len"], rp["rise"], rp["gradMax"]))
    for rl in auto_rails(d):
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        lo9, hi9 = _rail_offset(d, rl)
        rows.append("<tr><td><code>%s</code></td><td>竹垣(四つ目垣 h0.9)</td>"
                    "<td class='note'>%s</td><td>折れ線 %.1fm(法肩からの実距離 %.2f〜%.2fm)</td></tr>"
                    % (rl["name"], _ptrunc(pts), rl["len"], lo9, hi9))
    return ("<h3>郭内の土木の端点</h3><div class='tw'><table><thead><tr><th>名</th><th>種別</th>"
            "<th>世界座標</th><th>寸法</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def gate_parts_table(d):
    """門構えの部材位置。長屋門は一体の躯体なので芯と両端を出す。"""
    P = d["polygon"]
    g = d["gate"]; gp = g["plan"]
    dx, dz, _ = _edge_dir(P, g["edge"])
    rows = []
    for nm, s_off in [("長屋門(芯)", 0.0),
                      ("躯体 南端(練塀 E_Hei_S との継ぎ)", -gp["monW"] / 2),
                      ("躯体 北端(練塀 E_Hei_N との継ぎ)", gp["monW"] / 2)]:
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
            "<p class='cap'>長屋門の両袖は<b>練塀へ直に突き付ける</b>(番所は躯体内。呼称は json <code>gate.plan.bansho.kind</code>)。表長屋は0本。</p>")


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
    return ("<div class='tw'><table><thead><tr><th>commit</th><th>日付</th><th class='note'>件名</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 組み立て
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
    _dem_at(d, 0, 0)
    for sec9 in d["sections"]:
        nat9 = []
        f9, t9 = _sec_span(d, sec9)
        w9 = f9
        while w9 <= t9 + 1e-9:
            u9, v9 = (sec9["at"], w9) if sec9["axis"] == "u" else (w9, sec9["at"])
            y9 = _dem_at(d, u9, v9)
            if y9 is not None:
                nat9.append([round(w9, 2), round(y9, 2)])
            w9 += 1.5
        if nat9:
            sec9["natural"] = nat9

    bad = overlap_check(d)
    if bad:
        print("⚠ 矩形の重なり %d 件:" % len(bad))
        for b in bad:
            print("   ", b)
    pbad = plane_check(d)
    if pbad:
        print("⚠ 面のはみ出し %d 件:" % len(pbad))
        for b in pbad:
            print("   ", b)
    wbad = wall_check(d)
    if wbad:
        print("⚠ 土留めの高さ %d 件:" % len(wbad))
        for b in wbad:
            print("   ", b)
    kbad = keri_check(d)
    if kbad:
        print("⚠ 蹴上 %d 件:" % len(kbad))
        for b in kbad:
            print("   ", b)
    bbad = base_check(d)
    if bbad:
        print("⚠ 基壇の露出 %d 件:" % len(bbad))
        for b in bbad:
            print("   ", b)
    lbad = plinth_check(d)
    if lbad:
        print("⚠ 隣家の基壇との逆転 %d 件:" % len(lbad))
        for b in lbad:
            print("   ", b)
    sbad = seat_fill_check(d)
    if sbad:
        print("⚠ 据面の内側の落ち込み %d 件:" % len(sbad))
        for b in sbad:
            print("   ", b)
    ebad = edge_drop_check(d)
    if ebad:
        print("⚠ 段の縁 %d 件:" % len(ebad))
        for b in ebad:
            print("   ", b)
    cpbad = coping_check(d)
    if cpbad:
        print("⚠ 基壇の天端 %d 件:" % len(cpbad))
        for b in cpbad:
            print("   ", b)
    clbad = clearance_check(d)
    if clbad:
        print("⚠ 離隔 %d 件:" % len(clbad))
        for b in clbad:
            print("   ", b)
    cbad = compass_check(d)
    if cbad:
        print("⚠ 方位語 %d 件:" % len(cbad))
        for b in cbad:
            print("   ", b)
    xbad = crossing_check(d)
    if xbad:
        print("⚠ 竹垣・勝手動線の交差 %d 件:" % len(xbad))
        for b in xbad:
            print("   ", b)

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ['<meta charset="utf-8">', "<title>岡部内膳正上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    hn = d.get("han", {})
    h.append('<p class="eyebrow">外桜田永田町 ／ %s・%s %s 上屋敷</p>'
             % (hn.get("kaku", ""), hn.get("tono", ""), hn.get("kokuJa", "")))
    h.append("<h1>岡部内膳正上屋敷 指図</h1>")
    h.append('<div class="box" style="border-color:var(--shu);margin-top:14px"><h3>基準年次と確度</h3><p>'
             '<b>基準年次=嘉永3年(1850)</b> — 基図(尾張屋版切絵図)の年次。安政2年の地震記録は'
             '「倒れる前の姿」として遡って使う。<br>'
             '<b>当主=岡部内膳正 長和</b>(10代。<b>嘉永3年『大成武鑑』の「岡部家」の條に'
             '「岡部内膳正長和」とあり確度A</b>。⚠ 嘉永3年9月24日に没し弟の長発が継ぐので、'
             '「当主=長和」と言えるのは同年9月まで【確度B — Web二次】)。'
             '「岡部筑前守」は12代 長寛(安政2年家督)以降の受領名。<b>基準年次が嘉永3年なので表題は「内膳正」を採る</b>。<br>'
             '<b>外構が「塀」であったことは当屋敷を含む一次記録から言える</b> — 安政江戸地震の被害書上が'
             '3邸一括で「右外構練塀潰其外所々大破」と記す記事に当屋敷が<b>明示的に含まれる</b>【<b>種別=確度S</b>・2026-08-24 に全文で確定】。'
             '⚠ ただし<b>どの辺か・誰が所有した塀かは書かれていない</b>ので、'
             '<b>帰属と全周であることは確度U(当方の裁定)</b>。三層に分けて読むこと。'
             
             '屋敷指図(建物平面)は現存未確認 — 御殿の構成は類型(B)、室名・畳数は想定(U)。'
             '書院は<b>%s(%s)の格</b>で作り、帝鑑間格へ上げない(<b>確度B</b> — [岡部家歴代]Web二次。'
             '『寛政重修諸家譜』での確認は未了。⚠ 居城の行は『大成武鑑』嘉永3 コマ314–316 が未読)。'
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
           "其十六", "其十七", "其十八", "其十九", "其二十"]   # ⚠ 足りないと nx() が IndexError
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
            "面の高さは<b>主面=盛土を免れた実測セルの中央値(P)+[五千分一東京図31]で24&lt;h&lt;26に拘束(B)</b>、<b>門前面=同図で12〜14の帯に拘束(A)／嘉永への遡及(B)／帯の中で値を採ること(U)</b>(⚠ <b>ただし帯の中を 12 の等高線が渡る位置は未読</b> — 11.7 &lt; 12 &lt; 13.7 である以上どこかで必ず渡るので、『渡りが無い』という読みは<b>内部矛盾を抱えたまま</b>) — 全面が"
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
        others.append((P0, "#C0392B", 2.8, "岡部内膳正 上屋敷",
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
                "暖色=盛土/寒色=切土/無彩=±0.3m以内(実質さわらない)/"
                "地の色(薄い緑)のまま=<b>造成しない</b>。破線の枠は段、細い実線は御殿の棟。"
                "<b>面の高さを地形の実測と1883の等高線の帯から採ってあるので、郭の大半は無彩か薄い色になる</b> — "
                "<b>濃く出る所は算出して出す</b>(手で書かない): %s。" % _fill_where(d, ter))
        h.append(cft)
        h.append(edge_drop_table(d))
        bb = batter_check(d, ter)
        h.append('<p class="cap"><b>法面の検査: %s。</b>'
                 '段の外は「縁の土の厚みが 0 へ逓減する」形で法面を出す。'
                 '関門は三つ — ①縁が盛土(切土)であること ②cap %.0fm 以内 '
                 '③<b>地山がすでに法面より急な所(崖)には法面を出さない</b>。'
                 '検査は「<b>法面が可能だった所を造成が 1:%.1f より急にしていないか</b>」で、'
                 '地山が既に 1:%.1f を超える崖は対象外(どんな薄い土工も超えるため)。'
                 '囲いのある辺から1.5間以内も対象外 — そこは石垣基壇が受ける。%s</p>'
                 % ("<b>0 件</b>" if not bb else "⚠ %d 件" % len(bb),
                    d["const"].get("featherCap", 12.0), d["const"]["batterCut"], d["const"]["batterCut"],
                    ("" if not bb else "<br>⚠ 残るのは<b>崖の肩</b>(地山 %s)の %d 箇所 — %s。"
                     "法面と崖の境目で、実装では石垣か地形の均しで受ける。"
                     % (_grad_band(bb), len(bb), " / ".join(bb)))))
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
        fig(h, routes_svg(d, -42, 32, -4, 112),
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
                 % (rp0.get("name", "R_Ramp"), rp0.get("len", 0), rp0.get("gradMax", 0)))
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
             'その内訳は練塀 %.0fm・木柵 %.0fm・長屋門 %.1fm。<b>表長屋は0本</b>。'
             '⚠ <b>面積が二つ併存する</b> — 記録の拝領坪数 %s坪余で割れば <b>%.1f%%</b>。'
             '分母は図の実体である polygon のままにするが、読者に隠さない。'
             '<b>建蔽率は結果であって目標ではない</b> — 数字のために空地へ棟を足さない。'
             '⚠ <b>この %.1f%% は史料値の帯の外にある。</b>総練塀(表長屋0本・確度U)という当図固有の裁定と、'
             '造成しない斜面が半分という地形の実体の合成であって、'
             '<b>5万石級上屋敷の類型を代表する数字ではない</b>(§A-3)。</p>'
             % (kp, 100.0 * hika,
                perim, ownL + d["gate"]["plan"]["monW"],
                100.0 * (ownL + d["gate"]["plan"]["monW"]) / perim,
                sum(r["s1"] - r["s0"] for r in d["runs"]),
                sum(f["s1"] - f["s0"] for f in d.get("fences", [])),
                d["gate"]["plan"]["monW"],
                "{:,}".format(int(d.get("han", {}).get("tsubo", 0))),
                kp * (area / TSUBO) / max(d.get("han", {}).get("tsubo", 1), 1), kp))
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
             '段は run の継ぎ目と隅でだけ落ち、最大 %.2fm(隅を含む)。犬走り %.2fm。</p>'
             % (len(set(r["edge"] for r in d["runs"])),
                "・辺".join(str(e) for e in blankE),
                max([0.0] + [abs(rseat(y, y["s0"]) - rseat(x, x["s1"]))
                             for x, y in _joints(d)]),
                d["const"]["inubashiri"]))
    h.append("</div>")

    plate(h, nx(), "表門まわり",
          "長屋門+両番所(%s)。型式=現存する武家屋敷門の実例2件(確度A)＋格式階梯(B)/"
          "⚠ 実在と被災=安政地震の記録は**外構の練塀のみ**(表門には触れない)"
          % d["gate"]["plan"].get("bansho", {}).get("kind", ""))
    fig(h, gate_svg(d),
        cap="<b>根拠は三段に割れる。</b> ①<b>長屋門であること・片流面出番所であること</b> = "
            "[山脇武家屋敷門]<b>A</b>(官製の構造形式)。同門は<b>5万石・譜代・江戸上屋敷の表門</b>で、"
            "当家(%s・譜代)と石高・格・屋敷の別が揃う。"
            "②<b>番所を両端に持つこと</b> = [西澄寺武家屋敷門]A(番所を両端に持つ長屋門の実寸例)"
            "＋学園側の記述(B) — ⚠ <b>山脇門の官製記録は番所の数を書いていない</b>。"
            "③<b>その両者を束ねた「5〜10万石=長屋門+片流れの張出し両番所」</b> = "
            "[武家屋敷門の格式階梯]<b>B</b>。⚠ 階梯は<b>境界(5万石ちょうど)が曖昧</b>と原典自身が明記し、"
            "当家は帯の下端に接する。"
            "⛔ したがって<b>採用形『9間・二階建・片流れ張出し両番所』は2件のどちらの現物にも無い合成で、"
            "当家への採用そのものは確度U(外挿)</b>。①だけがAで、②はB、③もB。"
            "⛔ [山脇]は<b>門長屋の証拠には使わない</b>(袖が塀に載る現状は移築後の姿)。"
            "⛔ <b>安政二年の被害書上の当家の条は「右外構練塀潰其外所々大破」だけで、"
            "表門にも表長屋にも触れない。</b>「表門倒」は<b>土井大隅守の条</b>であって当家のものではない"
            "(2026-08-25 考証で誤帰属を是正)。"
            "⭐ その沈黙が情報を持たないことは<b>同じ表の中で実証できる</b> — 同じ3邸一括に入る土井は"
            "別の4記録で表門も表長屋も倒れたと記されるのに、大風之記の一括記事はそのどちらも書かない。"
            "よって当家の条の沈黙は<b>長屋門説の反証にも支持にもならない</b>。"
            "在庫部材の実寸が門口に合わない場合は縮小流用か新造(部材表参照)。石垣畳出は使わない(設計判断)。"
            % hn.get("kokuJa", ""))
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
             '落差3m級の縁を高さ0.9mの四つ目垣だけで受ける形になっており、'
             '<code>sashizu.md</code> §3b の「縁ごとに測って表にしてから土留めか法面かを決める」を'
             '回し直す必要がある(<code>_pending</code> に立てた)。'
             '段の縁は法面(盛土1:%.1f/切土1:%.1f)で摺り付く。'
             '造成しない斜面へ向く生活面の法肩にだけ<b>竹垣(四つ目垣 h0.9)</b>を回して、'
             '落差のある縁を素にしない。石垣が出るのは<b>外周の基壇だけ</b>(「外周の展開」)。</p>'
             % (len(rails), sum(1 for r in rails if r["drop"] > 2.0),
                max([r["drop"] for r in rails] or [0.0]),
                d["const"]["batterFill"], d["const"]["batterCut"]))
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
    yo = [x for x in d["_pending"]["open"] if x.startswith("【要判断")]
    ji = [x for x in d["_pending"]["open"] if x.startswith("【実装で納める")]
    ch = [x for x in d["_pending"]["open"] if x.startswith(("【要調査", "【要通達"))]
    plate(h, nx(), "裁定と宿題", "⭐ **この章の【要判断】はユーザーの裁定を待っている**")
    for ttl, xs, mk in (("⭐ ユーザーの裁定を仰ぐ", yo, "yo"),
                        ("実装で納める(図では閉じない)", ji, "ji"),
                        ("調査・通達の宿題", ch, "ch")):
        if not xs:
            continue
        h.append("<h3>%s(%d件)</h3><ol class='note'>%s</ol>"
                 % (ttl, len(xs), "".join("<li>%s</li>" % inline(x) for x in xs)))
    h.append('<p class="cap">⚠ <b>ここに出ていない宿題は無い</b> — 正典は json '
             '<code>_pending.open</code> で、この章はその全件を分類して刷る。'
             '⭐ <b>【要判断】は当方では閉じられない</b>(規則3 の免除など、'
             '不変則に関わるものを当方が自分に出すことはできない)。</p>')
    h.append("</div>")

    plate(h, nx(), "考証と決めごと")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, "改訂", "", "経緯はここに書かず git で追う ／ ⚠ **この図を作ったコミット自身は表に出ない**(構造上)")
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
