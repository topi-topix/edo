#!/usr/bin/env python3
"""山王権現社(日枝神社)の指図を組む。

    python3 Tools/Sashizu/build_sanno_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/sanno_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/sanno_kosho.md     … 文章の部(人が書く・現況形)

の二つだけ。実装から指図を作ると CLAUDE.md 絶対規則2 の関門が消える。

【この社ならではの作り】参道軸が東西で、絵図の社殿・回廊・透塀がすべて軸平行に描かれるため、
グリッドは**世界軸そのもの**(u=東+/v=北+、原点=楼門の芯)。回転フレームは要らない。
断面は json の `profiles`(Unity 地形の実測)を下敷きにする。

【図版】其一 社地/其二 境内 平面/其三 社殿 平面/其四〜七 断面(東西・南北・回廊の基壇・女坂)/
        其八 男坂と女坂の割付/其九 囲いの展開/其十 門/其十一 山麓/其十二 社僧十坊/
        其十三 棟の表/其十四 囲いと石段の表/其十五 部材/其十六 考証/其十七 未解決・改訂。
        組んだら「図版 N 面」を数えること(図版が黙って落ちた前科がある)。
"""
import json, math, os, re, subprocess, html

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "sanno_sashizu.json")
MD = os.path.join(DOC, "sanno_kosho.md")
OUT = os.path.join(DOC, "sanno_sashizu.html")
TSUBO = 3.305785
VEX = 2.0     # 断面の垂直倍率


# ---------------------------------------------------------------- markdown(岡部・土井と同じ最小変換)
def md2html(text):
    out, i, lines = [], 0, text.split("\n")
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in ln.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")]); i += 1
            out.append('<div class="tw"><table><thead><tr>'
                       + "".join("<th>%s</th>" % inline(x) for x in head)
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
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "-", "|")) and lines[i].strip() != "---":
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"【([SABPU?][^】]*)】", r'<span class="cert">【\1】</span>', s)
    s = re.sub(r"【(確度[^】]*)】", r'<span class="cert">【\1】</span>', s)
    return s


# ---------------------------------------------------------------- 作図の土台
_SVN = [0]


def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, label),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.6"/></pattern>'
            '<pattern id="kr%d" width="7" height="7" patternUnits="userSpaceOnUse">'
            '<path d="M0,7 L7,0" stroke="var(--shu)" stroke-width="0.7" opacity="0.55"/></pattern>'
            '<pattern id="mr%d" width="7" height="7" patternUnits="userSpaceOnUse">'
            '<path d="M0,0 L7,7" stroke="var(--take)" stroke-width="0.7" opacity="0.55"/></pattern>'
            '<clipPath id="cl%d"><rect x="0" y="0" width="%.0f" height="%.0f"/></clipPath></defs>'
            % (_SVN[0], _SVN[0], _SVN[0], _SVN[0], W, H),
            '<g clip-path="url(#cl%d)">' % _SVN[0]]


ENDSVG = "</g></svg>"


def _pat(): return "url(#pi%d)" % _SVN[0]
def _cut(): return "url(#kr%d)" % _SVN[0]      # 切土
def _fill(): return "url(#mr%d)" % _SVN[0]     # 盛土


class Proj(object):
    """世界座標 → SVG px。z は北が上なので Y だけ反転。"""
    def __init__(self, x0, x1, z0, z1, W=900.0, pad=0.0, top=0.0, bottom=0.0):
        self.wx0, self.wx1 = x0 - pad, x1 + pad
        self.wz0, self.wz1 = z0 - pad, z1 + pad
        self.s = W / (self.wx1 - self.wx0)
        self.W, self.top = W, top
        self.zh = (self.wz1 - self.wz0) * self.s
        self.H = self.zh + top + bottom

    def X(self, x): return (x - self.wx0) * self.s
    def Y(self, z): return self.top + self.zh - (z - self.wz0) * self.s
    def L(self, m): return m * self.s


class LProj(object):
    """グリッド (u,v)[間] → SVG px。v は北が上なので Y を反転する。"""
    def __init__(self, u0, u1, v0, v1, W=900.0, top=22.0, bottom=20.0):
        self.u0, self.u1, self.v0, self.v1 = u0, u1, v0, v1
        self.s = W / float(u1 - u0)
        self.W, self.top = W, top
        self.vh = (v1 - v0) * self.s
        self.H = self.vh + top + bottom

    def X(self, u): return (u - self.u0) * self.s
    def Y(self, v): return self.top + self.vh - (v - self.v0) * self.s
    def L(self, ken): return ken * self.s

    def rect(self, u0, v0, u1, v1, **kw):
        return R(self.X(min(u0, u1)), self.Y(max(v0, v1)),
                 abs(self.X(u1) - self.X(u0)), abs(self.Y(v1) - self.Y(v0)), **kw)


def R(x, y, w, h, fill="none", stroke="none", sw=1.0, dash=None, op=None):
    a = '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"' % (x, y, w, h, fill)
    if stroke != "none":
        a += ' stroke="%s" stroke-width="%.2f"' % (stroke, sw)
    if dash:
        a += ' stroke-dasharray="%s"' % dash
    if op is not None:
        a += ' opacity="%.2f"' % op
    return a + "/>"


def T(x, y, s, cls="sl", anchor=None, fs=None, fill=None):
    a = '<text class="%s" x="%.1f" y="%.1f"' % (cls, x, y)
    st = []
    if anchor: st.append("text-anchor:%s" % anchor)
    if fs: st.append("font-size:%.1fpx" % fs)
    if fill: st.append("fill:%s" % fill)
    if st: a += ' style="%s"' % ";".join(st)
    return a + ">%s</text>" % html.escape(s.replace("**", ""), quote=False)


def LN(x1, y1, x2, y2, stroke="var(--ink)", sw=1.0, dash=None, op=None, cap=None):
    a = '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.2f"' % (x1, y1, x2, y2, stroke, sw)
    if dash: a += ' stroke-dasharray="%s"' % dash
    if op is not None: a += ' opacity="%.2f"' % op
    if cap: a += ' stroke-linecap="%s"' % cap
    return a + "/>"


def PL(pts, stroke="var(--ink)", sw=1.0, fill="none", dash=None, op=None, close=False):
    dd = "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")
    a = '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f"' % (dd, fill, stroke, sw)
    if dash: a += ' stroke-dasharray="%s"' % dash
    if op is not None: a += ' opacity="%.2f"' % op
    return a + "/>"


def fit(txt, wpx, base=12.0, lo=8.5):
    return max(lo, min(base, wpx / (len(txt) * 0.62 + 0.8)))


def poly_area(P):
    s = 0.0
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        s += a[0] * b[1] - b[0] * a[1]
    return abs(s) / 2.0


# ---------------------------------------------------------------- グリッド
class G(object):
    def __init__(self, d):
        g = d["grid"]["keidai"]
        self.ken = d["const"]["ken"]
        self.x0, self.z0 = g["x0"], g["z0"]

    def W(self, u, v): return (self.x0 + u * self.ken, self.z0 + v * self.ken)
    def U(self, x): return (x - self.x0) / self.ken
    def V(self, z): return (z - self.z0) / self.ken


YAKU_COL = {"社殿": "var(--shu)", "廊": "var(--roka)", "堂": "var(--nagaya)",
            "蔵": "var(--ishi)", "供": "var(--nagaya)", "接続": "var(--shu-lo)"}



def cut_lines(d, PX, PY, LEN, inwin=None, clip=None):
    """断面の切断線を平面図へ落とす。PX/PY = 世界座標→px、LEN = m→px。"""
    o = []
    for sec in d.get("sections", []):
        ln = sec.get("line")
        if not ln: continue
        (x0, z0), (x1, z1) = ln
        if inwin and not inwin((x0, z0), (x1, z1)): continue
        ax, ay = PX(x0), PY(z0)
        bx, by = PX(x1), PY(z1)
        if clip:                      # 図の窓で切って、矢視記号を縁に置く
            cx0, cy0, cx1, cy1 = clip
            dx0, dy0 = bx - ax, by - ay
            t0, t1 = 0.0, 1.0
            for pq in ((-dx0, ax - cx0), (dx0, cx1 - ax), (-dy0, ay - cy0), (dy0, cy1 - ay)):
                pp, qq = pq
                if abs(pp) < 1e-9:
                    if qq < 0: t0, t1 = 1.0, 0.0
                    continue
                r = qq / pp
                if pp < 0: t0 = max(t0, r)
                else:      t1 = min(t1, r)
            if t0 >= t1: continue
            ax, ay, bx, by = (ax + dx0 * t0, ay + dy0 * t0, ax + dx0 * t1, ay + dy0 * t1)
        # 一点鎖線
        o.append(LN(ax, ay, bx, by, stroke="var(--shu)", sw=1.0, dash="12 3 2 3", op=0.85))
        vx, vz = sec["view"]
        nv = math.hypot(vx, vz) or 1.0
        # 矢視の向き(px 空間。z は上下反転するので Y 成分の符号に注意)
        adx = PX(x0 + vx / nv) - PX(x0)
        ady = PY(z0 + vz / nv) - PY(z0)
        an = math.hypot(adx, ady) or 1.0
        adx, ady = adx / an, ady / an
        dx, dy = bx - ax, by - ay
        dn = math.hypot(dx, dy) or 1.0
        dx, dy = dx / dn, dy / dn
        for (ex, ey, sgn) in ((ax, ay, 1.0), (bx, by, -1.0)):
            # 端部の太い線
            o.append(LN(ex, ey, ex + dx * 16 * sgn, ey + dy * 16 * sgn, stroke="var(--shu)", sw=2.6))
            # 矢視の矢
            hx, hy = ex + dx * 8 * sgn, ey + dy * 8 * sgn
            tx, ty = hx + adx * 13, hy + ady * 13
            o.append(LN(hx, hy, tx, ty, stroke="var(--shu)", sw=1.8))
            px_, py_ = -ady, adx
            o.append(PL([(tx, ty), (tx - adx * 5 + px_ * 3, ty - ady * 5 + py_ * 3),
                         (tx - adx * 5 - px_ * 3, ty - ady * 5 - py_ * 3)],
                        stroke="none", fill="var(--shu)", close=True))
            # カナの札
            cx, cy = ex - dx * 11 * sgn, ey - dy * 11 * sgn
            o.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="var(--paper2)" stroke="var(--shu)" stroke-width="1.2"/>'
                     % (cx, cy))
            o.append(T(cx, cy + 4, sec["kana"], fs=11.5, anchor="middle", fill="var(--shu)"))
    return o


# ---------------------------------------------------------------- 其一 社地
def shachi_svg(d, kan="其一"):
    g = G(d)
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), W=900.0, pad=22.0, top=26.0, bottom=30.0)
    o = _sv(pr.W, pr.H, "社地の全図")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))

    # 社地
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in P], stroke="var(--ink)", sw=1.6,
                fill="var(--pl-slope)", op=0.55, close=True))
    # 社叢の帯(社地の内側を薄く)
    o.append(T(pr.X(-600), pr.Y(760), "社叢(造成しない)", fs=11, fill="var(--take)"))

    # 境内の平場
    kp = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in kp], stroke="var(--ink)", sw=1.3,
                fill="var(--pl-main)", op=0.85, close=True))
    # 前庭
    zt = d["terraces"][1]
    a = g.W(zt["u0"], zt["v0"]); b = g.W(zt["u1"], zt["v1"])
    o.append(R(pr.X(a[0]), pr.Y(b[1]), pr.X(b[0]) - pr.X(a[0]), pr.Y(a[1]) - pr.Y(b[1]),
               fill="var(--pl-suso)", stroke="var(--ink)", sw=1.0, op=0.9))

    # 透塀・回廊・社殿
    for r in d["runs"]:
        if r["kind"] not in ("透塀", "回廊"): continue
        w0 = g.W(*r["a"]); w1 = g.W(*r["b"])
        col = "var(--shu)" if r["kind"] == "透塀" else "var(--roka)"
        o.append(LN(pr.X(w0[0]), pr.Y(w0[1]), pr.X(w1[0]), pr.Y(w1[1]), stroke=col, sw=2.0))
    for m in d["munes"]:
        if m["yaku"] not in ("社殿",): continue
        w0 = g.W(m["u0"], m["v0"]); w1 = g.W(m["u0"] + m["du"], m["v0"] + m["dv"])
        o.append(R(pr.X(w0[0]), pr.Y(w1[1]), pr.X(w1[0]) - pr.X(w0[0]), pr.Y(w0[1]) - pr.Y(w1[1]),
                   fill="var(--shu)", op=0.85))

    # 石段
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        w0 = g.W(*k["a"]); w1 = g.W(*k["b"])
        o.append(LN(pr.X(w0[0]), pr.Y(w0[1]), pr.X(w1[0]), pr.Y(w1[1]), stroke="var(--ishi)", sw=5.0, op=0.9))
        mx, mz = (w0[0] + w1[0]) / 2, (w0[1] + w1[1]) / 2
        o.append(T(pr.X(mx), pr.Y(mz) - 7, k["name"].split("(")[0], fs=10.5, anchor="middle", fill="var(--ink)"))

    # 参道
    sp = d["sando"]["pts"]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in sp], stroke="var(--shu)", sw=2.2, dash="7 4"))
    # 二ノ鳥居
    for t in d["torii"]:
        if not t["pos"]: continue
        x, z = t["pos"]
        o.append(LN(pr.X(x) - 6, pr.Y(z), pr.X(x) + 6, pr.Y(z), stroke="var(--shu)", sw=2.4))
        o.append(LN(pr.X(x) - 4, pr.Y(z) + 4, pr.X(x) - 4, pr.Y(z) - 4, stroke="var(--shu)", sw=1.6))
        o.append(LN(pr.X(x) + 4, pr.Y(z) + 4, pr.X(x) + 4, pr.Y(z) - 4, stroke="var(--shu)", sw=1.6))
        o.append(T(pr.X(x) + 9, pr.Y(z) + 3, t["name"], fs=10.5, fill="var(--shu)"))

    # 隣地
    for nb in d["neighbors"]:
        if "polygon" not in nb: continue
        Q = nb["polygon"]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in Q], stroke="var(--dim)", sw=1.0,
                    dash="4 3", fill="var(--paper)", op=0.35, close=True))
        cx = sum(p[0] for p in Q) / len(Q); cz = sum(p[1] for p in Q) / len(Q)
        o.append(T(pr.X(cx), pr.Y(cz), nb["name"].split(" ")[-1], fs=11, anchor="middle", fill="var(--dim)"))

    # 断面の切断線
    o += cut_lines(d, pr.X, pr.Y, pr.L,
                   clip=(14.0, pr.top + 10.0, pr.W - 14.0, pr.top + pr.zh - 6.0))
    # 注記
    o.append(T(6, 15, kan + "　社地 ─ 社叢の中の明地に建つ", fs=12.5, fill="var(--dim)"))
    o.append(T(pr.W - 6, 15, "北が上 ／ 東が右", fs=11, anchor="end", fill="var(--dim)"))
    kc = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
    ccx = sum(p[0] for p in kc) / len(kc); ccz = sum(p[1] for p in kc) / len(kc)
    o.append(T(pr.X(ccx), pr.Y(ccz) + 34, "境内(山上)", fs=12, anchor="middle", fill="var(--ink)"))
    o.append(T(pr.X(-443), pr.Y(858) + 4, "前庭", fs=11, anchor="middle", fill="var(--ink)"))
    # 縮尺
    y = pr.H - 14
    o.append(LN(14, y, 14 + pr.L(100), y, stroke="var(--dim)", sw=1.2))
    o.append(T(14 + pr.L(100) / 2, y - 4, "100 m", fs=10.5, anchor="middle"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其二 境内 平面
def keidai_svg(d, u0, u1, v0, v1, title, W=900.0):
    g = G(d)
    ken = d["const"]["ken"]

    def inwin(a, b, pad=3.0):
        return not (max(a[0], b[0]) < u0 - pad or min(a[0], b[0]) > u1 + pad
                    or max(a[1], b[1]) < v0 - pad or min(a[1], b[1]) > v1 + pad)

    lp = LProj(u0, u1, v0, v1, W=W, top=26.0, bottom=24.0)
    o = _sv(lp.W, lp.H, title)
    o.append(R(0, 0, lp.W, lp.H, fill="var(--paper2)"))

    # 間グリッド
    for u in range(int(math.ceil(u0)), int(u1) + 1):
        if u % 5: continue
        o.append(LN(lp.X(u), lp.top, lp.X(u), lp.top + lp.vh, stroke="var(--grid)", sw=0.5, op=0.7))
    for v in range(int(math.ceil(v0)), int(v1) + 1):
        if v % 5: continue
        o.append(LN(0, lp.Y(v), lp.W, lp.Y(v), stroke="var(--grid)", sw=0.5, op=0.7))

    # 境内の平場
    o.append(PL([(lp.X(u), lp.Y(v)) for u, v in d["terraces"][0]["uv"]],
                stroke="var(--ink)", sw=1.3, fill="var(--pl-main)", op=0.55, close=True))
    # 前庭
    zt = d["terraces"][1]
    o.append(lp.rect(zt["u0"], zt["v0"], zt["u1"], zt["v1"], fill="var(--pl-suso)",
                     stroke="var(--ink)", sw=1.0, op=0.75))
    # 白洲・中庭
    for gd in d["gardens"]:
        if gd["u0"] is None: continue
        if not inwin([gd["u0"], gd["v0"]], [gd["u1"], gd["v1"]]): continue
        o.append(lp.rect(gd["u0"], gd["v0"], gd["u1"], gd["v1"], fill="var(--shirasu)", op=0.9))
        o.append(T(lp.X((gd["u0"] + gd["u1"]) / 2), lp.Y((gd["v0"] + gd["v1"]) / 2) + 4,
                   gd["name"], fs=11, anchor="middle", fill="var(--dim)"))
    # 板塀(折れ線)
    for r in d["runs"]:
        if r["kind"] != "板塀": continue
        pts = r.get("pts")
        if pts:
            o.append(PL([(lp.X(u), lp.Y(v)) for u, v in pts], stroke="var(--hei)", sw=1.8, dash="7 3"))
        elif r["a"] is not None and inwin(r["a"], r["b"]):
            o.append(LN(lp.X(r["a"][0]), lp.Y(r["a"][1]), lp.X(r["b"][0]), lp.Y(r["b"][1]),
                        stroke="var(--hei)", sw=1.6, dash="6 3"))
    # 透塀
    for r in d["runs"]:
        if r["kind"] != "透塀": continue
        if not inwin(r["a"], r["b"]): continue
        o.append(LN(lp.X(r["a"][0]), lp.Y(r["a"][1]), lp.X(r["b"][0]), lp.Y(r["b"][1]),
                    stroke="var(--shu)", sw=2.4))
    # 石段
    for k in d["kaidans"]:
        a, b = k["a"], k["b"]
        if not inwin(a, b): continue
        n = k["steps"] if k["steps"] <= 60 else 60
        ax, ay, bx, by = lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1])
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        hw = lp.L(k["w"] / d["const"]["ken"]) / 2
        o.append(PL([(ax + nx * hw, ay + ny * hw), (bx + nx * hw, by + ny * hw),
                     (bx - nx * hw, by - ny * hw), (ax - nx * hw, ay - ny * hw)],
                    stroke="var(--ishi)", sw=1.0, fill="var(--dan)", op=0.9, close=True))
        for i in range(1, n):
            t = i / float(n)
            px, py = ax + dx * t, ay + dy * t
            o.append(LN(px + nx * hw, py + ny * hw, px - nx * hw, py - ny * hw,
                        stroke="var(--ishi)", sw=0.5, op=0.8))
    # 渡廊下
    for lk in d.get("links", []):
        a, b = lk["from"], lk["to"]
        if not inwin(a, b): continue
        hw = lk["w"] / 2.0
        o.append(lp.rect(a[0], a[1] - hw, b[0], b[1] + hw, fill="var(--roka)",
                         stroke="var(--ink)", sw=0.8, op=0.7))
    # 棟
    for m in d["munes"]:
        col = YAKU_COL.get(m["yaku"], "var(--nagaya)")
        u, v, du, dv = m["u0"], m["v0"], m["du"], m["dv"]
        if u + du < u0 or u > u1 or v + dv < v0 or v > v1: continue
        dash = "3 3" if m["yaku"] == "接続" else None
        o.append(lp.rect(u, v, u + du, v + dv, fill=col, stroke="var(--ink)", sw=0.9,
                         op=0.35 if m["yaku"] == "接続" else 0.85, dash=dash))
        wpx = abs(lp.X(u + du) - lp.X(u))
        nm = m["name"].replace("附属堂 ", "").replace("回廊 ", "廊")
        o.append(T(lp.X(u + du / 2.0), lp.Y(v + dv / 2.0) + 4, nm, fs=fit(nm, wpx, 11.5),
                   anchor="middle", fill="var(--paper)"))
    # 門
    for gt in d["gates"]:
        u, v = gt["u"], gt["v"]
        if not inwin([u, v], [u, v]): continue
        pl = gt["plan"]
        o.append(lp.rect(u - pl["du"] / 2.0, v - pl["dv"] / 2.0, u + pl["du"] / 2.0, v + pl["dv"] / 2.0,
                         fill="var(--shu)", stroke="var(--ink)", sw=1.1))
        lx, la = lp.X(u), "middle"
        if gt["name"] == "中門": lx, la = lp.X(u) - lp.L(1.2), "end"
        o.append(T(lx, lp.Y(v + pl["dv"] / 2.0) - 5, gt["name"], fs=11, anchor=la, fill="var(--shu)"))
    # 石灯籠
    for p in d["props"]:
        if not p.get("uv"): continue
        for u, v in p["uv"]:
            if not inwin([u, v], [u, v]): continue
            x, y = lp.X(u), lp.Y(v)
            if p["name"] == "石灯籠":
                o.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="none" stroke="var(--ink)" stroke-width="1.1"/>' % (x, y))
            elif p["name"] == "白洲の△":
                o.append(PL([(x, y - 4), (x + 3.6, y + 2.6), (x - 3.6, y + 2.6)],
                            stroke="var(--ink)", sw=1.1, close=True))
            else:
                o.append(R(x - 3.0, y - 1.6, 6.0, 3.2, fill="none", stroke="var(--dim)", sw=0.9))
    # 断面の切断線
    def _win(a, b):
        ua, va = g.U(a[0]), g.V(a[1])
        ub, vb = g.U(b[0]), g.V(b[1])
        return not (max(ua, ub) < u0 - 2 or min(ua, ub) > u1 + 2
                    or max(va, vb) < v0 - 2 or min(va, vb) > v1 + 2)
    o += cut_lines(d, lambda x: lp.X(g.U(x)), lambda z: lp.Y(g.V(z)),
                   lambda m: lp.L(m / ken), inwin=_win,
                   clip=(14.0, lp.top + 10.0, lp.W - 14.0, lp.top + lp.vh - 6.0))
    o.append(T(6, 15, title, fs=12.5, fill="var(--dim)"))
    o.append(T(lp.W - 6, 15, "1目盛 = 5間 ／ 原点 = 楼門の芯", fs=11, anchor="end", fill="var(--dim)"))
    # 縮尺
    y = lp.H - 10
    o.append(LN(14, y, 14 + lp.L(10), y, stroke="var(--dim)", sw=1.2))
    o.append(T(14 + lp.L(10) / 2, y - 4, "10 間 (18.18 m)", fs=10.5, anchor="middle"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 断面
def _profile(d, key):
    p = d["profiles"][key]
    if p["axis"] == "EW":
        return [(p["x0"] + i * p["step"], h) for i, h in enumerate(p["h"])]
    if p["axis"] == "NS":
        return [(p["z0"] + i * p["step"], h) for i, h in enumerate(p["h"])]
    a, b = p["a"], p["b"]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return [((p["s0"] + i * p["step"]) * L, h) for i, h in enumerate(p["h"])]


def design_line(prof, flats, stairs=()):
    """flats = [(c0, c1, y)] 平場 / stairs = [(c0, c1, y0, y1)] 石段。外は現地形なり。"""
    out = []
    for c, hn in prof:
        y = None
        for a, b, yy in flats:
            if a - 1e-6 <= c <= b + 1e-6: y = yy
        for a, b, ya, yb in stairs:
            if a - 1e-6 <= c <= b + 1e-6:
                y = ya + (yb - ya) * (c - a) / (b - a)
        out.append((c, hn if y is None else y))
    # 平場・石段の端点を明示的に差し込む
    for a, b, yy in flats:
        out += [(a, yy), (b, yy)]
    for a, b, ya, yb in stairs:
        out += [(a, ya), (b, yb)]
    out.sort(key=lambda p: p[0])
    return out


def section_svg(d, key, design, marks, title, flip=False, viewtxt=""):
    """design = [(coord, y), ...] 設計地盤 / marks = [(coord0, coord1, y, ラベル, 種別)]"""
    g = G(d)
    prof = _profile(d, key)
    c0, c1 = prof[0][0], prof[-1][0]
    ys = [h for _, h in prof] + [y for _, y in design]
    y0, y1 = min(ys) - 2.0, max(ys) + 6.0
    W = 900.0
    s = W / (c1 - c0)
    Hh = min(460.0, (y1 - y0) * s * VEX)
    top = 26.0
    H = Hh + top + 26.0
    X = (lambda c: (c1 - c) * s) if flip else (lambda c: (c - c0) * s)
    vs = Hh / (y1 - y0)
    Y = lambda y: top + Hh - (y - y0) * vs
    o = _sv(W, H, title)
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    dpts = [(X(c), Y(y)) for c, y in design]
    npts = [(X(c), Y(h)) for c, h in prof]
    # 地表下の塗り
    o.append(PL(npts + [(npts[-1][0], Y(y0)), (npts[0][0], Y(y0))],
                stroke="none", fill="var(--dan3)", op=0.75, close=True))

    # 切土(設計 < 現地形)と盛土(設計 > 現地形)を塗り分ける
    cs = sorted(set([c for c, _ in prof] + [c for c, _ in design]))
    cs = [c for c in cs if prof[0][0] - 1e-6 <= c <= prof[-1][0] + 1e-6]

    def at(series, c):
        for i in range(len(series) - 1):
            a, b = series[i], series[i + 1]
            if a[0] - 1e-9 <= c <= b[0] + 1e-9:
                if abs(b[0] - a[0]) < 1e-9: return a[1]
                return a[1] + (b[1] - a[1]) * (c - a[0]) / (b[0] - a[0])
        return series[-1][1]

    for i in range(len(cs) - 1):
        ca, cb = cs[i], cs[i + 1]
        if cb - ca < 1e-6: continue
        na, nb = at(prof, ca), at(prof, cb)
        da, db = at(design, ca), at(design, cb)
        if abs(na - da) < 0.05 and abs(nb - db) < 0.05: continue
        cut = (na + nb) / 2 > (da + db) / 2
        o.append(PL([(X(ca), Y(na)), (X(cb), Y(nb)), (X(cb), Y(db)), (X(ca), Y(da))],
                    stroke="none", fill=_cut() if cut else _fill(), close=True))

    o.append(PL(npts, stroke="var(--dim)", sw=1.1, dash="5 3"))
    o.append(PL(dpts, stroke="var(--ink)", sw=2.0))
    # 高さの罫(塗りの上に載せる)
    for y in range(int(math.ceil(y0 / 5.0) * 5), int(y1) + 1, 5):
        o.append(LN(0, Y(y), W, Y(y), stroke="var(--grid)", sw=0.5, op=0.55))
        o.append(T(3, Y(y) - 2, "%d m" % y, fs=9.5, fill="var(--dim)"))
    # 建物・門・石段のマーク
    for c0m, c1m, yb, lab, kind in marks:
        xa, xb = X(c0m), X(c1m)
        if xa > xb: xa, xb = xb, xa
        hgt = {"社殿": 7.5, "門": 9.0, "廊": 5.0, "塀": 2.1, "堂": 4.5}.get(kind, 4.0)
        col = {"社殿": "var(--shu)", "門": "var(--shu)", "廊": "var(--roka)",
               "塀": "var(--hei)", "堂": "var(--nagaya)"}.get(kind, "var(--nagaya)")
        hpx = max(9.0, min(46.0, hgt * vs))
        o.append(R(xa, Y(yb) - hpx, xb - xa, hpx, fill=col, op=0.55, stroke="var(--ink)", sw=0.8))
        o.append(T((xa + xb) / 2, Y(yb) - hpx - 4, lab, fs=fit(lab, xb - xa, 10.5), anchor="middle"))
    o.append(T(6, 15, title, fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "垂直 %.1f 倍" % (vs / s), fs=11, anchor="end", fill="var(--dim)"))
    o.append(T(W - 6, 30, viewtxt, fs=10.5, anchor="end", fill="var(--shu)"))
    o.append(T(W - 6, H - 8, "破線 = 現地形(Unity Terrain 実測) ／ 実線 = 設計地盤 ／ ╲ 切土 ／ ╱ 盛土", fs=10.5,
               anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其八 坂の割付
def saka_svg(d, kan="其八"):
    ken = d["const"]["ken"]
    ks = [k for k in d["kaidans"] if k["name"] != "向拝の階"]
    W = 900.0
    ROW, RISE = 150.0, 78.0          # 1段あたりの行高 / 比高の描画高
    H = 46.0 + len(ks) * ROW
    o = _sv(W, H, "男坂と女坂の割付")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    Ls = [math.hypot((k["b"][0] - k["a"][0]) * ken, (k["b"][1] - k["a"][1]) * ken) for k in ks]
    hs = 560.0 / max(Ls)             # 水平スケール
    for i, k in enumerate(ks):
        L, rise = Ls[i], k["yTop"] - k["yBot"]
        vs = RISE / rise             # 垂直スケール(行ごとに同じ比高なので共通)
        bx, by = 96.0, 56.0 + i * ROW
        o.append(LN(bx, by, bx + L * hs, by, stroke="var(--grid)", sw=0.6, dash="4 3"))
        o.append(LN(bx, by + rise * vs, bx + L * hs, by + rise * vs, stroke="var(--grid)", sw=0.6, dash="4 3"))
        n, px, py = k["steps"], bx, by
        pts = [(px, py)]
        for j in range(n):
            px2 = bx + (j + 1) * (L * hs / n)
            py2 = by + (j + 1) * (rise * vs / n)
            pts += [(px2, py), (px2, py2)]
            px, py = px2, py2
        o.append(PL(pts, stroke="var(--ishi)", sw=1.3))
        o.append(T(bx, by - 12, k["name"], fs=12.5, fill="var(--ink)"))
        o.append(T(bx + L * hs + 10, by + rise * vs * 0.42,
                   "%d 段　蹴上 %.2f ／ 踏面 %.3f" % (k["steps"], k["keri"], k["fumi"]), fs=11))
        o.append(T(bx + L * hs + 10, by + rise * vs * 0.42 + 16,
                   "勾配 %.1f%%  (%.1f°)" % (k["grade"], k["deg"]), fs=11, fill="var(--shu)"))
        o.append(T(bx - 8, by + 4, "%.1f m" % k["yTop"], fs=10, anchor="end", fill="var(--dim)"))
        o.append(T(bx - 8, by + rise * vs + 4, "%.1f m" % k["yBot"], fs=10, anchor="end", fill="var(--dim)"))
        o.append(T(bx + L * hs / 2, by + rise * vs + 20, "平面長 %.2f m" % L, fs=10.5,
                   anchor="middle", fill="var(--dim)"))
    o.append(T(6, 15, kan + "　男坂と女坂の割付 ─ 同じ比高を、違う踏面で降ろす", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "水平・垂直とも図版内で正規化(勾配は数値で読む)", fs=10.5,
               anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其九 囲いの展開
def kakoi_svg(d, kan="其九"):
    ken = d["const"]["ken"]
    W = 900.0
    rows = [r for r in d["runs"] if r["kind"] in ("透塀", "回廊")]
    H = 60.0 + len(rows) * 46.0
    o = _sv(W, H, "囲いの展開")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    maxk = max(r["ken"] for r in rows)
    for i, r in enumerate(rows):
        y = 52.0 + i * 46.0
        L = 470.0 * r["ken"] / maxk
        col = "var(--shu)" if r["kind"] == "透塀" else "var(--roka)"
        o.append(R(200, y, L, 20, fill=col, op=0.5, stroke="var(--ink)", sw=0.8))
        # 柱の刻み(1間ごと)
        for j in range(1, int(r["ken"]) + 1):
            o.append(LN(200 + L * j / r["ken"], y, 200 + L * j / r["ken"], y + 20,
                        stroke="var(--ink)", sw=0.4, op=0.5))
        o.append(T(194, y + 14, r["name"], fs=11, anchor="end"))
        o.append(T(212 + L, y + 14, "%.1f 間 = %.2f m　天端 %.1f m" % (r["ken"], r["ken"] * ken, r["seat"]), fs=10.5))
        if r.get("gate"):
            o.append(T(200 + L / 2, y - 3, "◇ " + r["gate"], fs=10, anchor="middle", fill="var(--shu)"))
    tot = sum(r["ken"] for r in rows if r["kind"] == "透塀")
    o.append(T(6, 15, kan + "　囲いの展開 ─ 透塀の延長は史料値がそのまま設計拘束", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "透塀 計 %.0f 間 = %.3f m" % (tot, tot * ken), fs=11.5, anchor="end", fill="var(--shu)"))
    o.append(T(W - 6, H - 10, "史料値 147.28 m(486.01尺)との差 %.3f m" % abs(tot * ken - 147.28),
               fs=10.5, anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其十一 山麓
def sanroku_svg(d, kan="其十一"):
    g = G(d)
    pr = Proj(-505, -320, 715, 955, W=900.0, pad=6.0, top=26.0, bottom=24.0)
    o = _sv(pr.W, pr.H, "山麓 ─ 前庭・辻・別当・神主・門前町")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))
    # 社地
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in d["polygon"]], stroke="var(--ink)", sw=1.2,
                fill="var(--pl-slope)", op=0.4, close=True))
    # 前庭
    zt = d["terraces"][1]
    a = g.W(zt["u0"], zt["v0"]); b = g.W(zt["u1"], zt["v1"])
    o.append(R(pr.X(a[0]), pr.Y(b[1]), pr.X(b[0]) - pr.X(a[0]), pr.Y(a[1]) - pr.Y(b[1]),
               fill="var(--pl-suso)", stroke="var(--ink)", sw=1.0, op=0.9))
    o.append(T(pr.X(-443), pr.Y(858), "前庭", fs=11.5, anchor="middle"))
    # 隣地
    for nb in d["neighbors"]:
        if "polygon" not in nb: continue
        Q = nb["polygon"]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in Q], stroke="var(--dim)", sw=1.1, dash="4 3",
                    fill="var(--paper)", op=0.5, close=True))
        cx = sum(p[0] for p in Q) / len(Q); cz = sum(p[1] for p in Q) / len(Q)
        o.append(T(pr.X(cx), pr.Y(cz), nb["name"], fs=11.5, anchor="middle", fill="var(--ink)"))
    # 境内の平場と社殿(位置の手がかり)
    kp = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in kp], stroke="var(--ink)", sw=1.0,
                fill="var(--pl-main)", op=0.7, close=True))
    for r in d["runs"]:
        if r["kind"] not in ("透塀", "回廊"): continue
        w0 = g.W(*r["a"]); w1 = g.W(*r["b"])
        o.append(LN(pr.X(w0[0]), pr.Y(w0[1]), pr.X(w1[0]), pr.Y(w1[1]),
                    stroke="var(--shu)" if r["kind"] == "透塀" else "var(--roka)", sw=2.0))
    # 石段
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        w0 = g.W(*k["a"]); w1 = g.W(*k["b"])
        o.append(LN(pr.X(w0[0]), pr.Y(w0[1]), pr.X(w1[0]), pr.Y(w1[1]), stroke="var(--ishi)", sw=6.0, op=0.9))
        o.append(T(pr.X((w0[0] + w1[0]) / 2), pr.Y((w0[1] + w1[1]) / 2) - 8,
                   k["name"].split("(")[0], fs=10.5, anchor="middle"))
    # 山王門前町(CODH点)
    o.append(T(pr.X(-339), pr.Y(928), "山王門前町", fs=11.5, anchor="middle", fill="var(--ink)"))
    o.append(R(pr.X(-352), pr.Y(936), pr.L(26), pr.L(16), fill="none", stroke="var(--dim)", sw=1.0, dash="4 3"))
    # 参道と鳥居
    sp = d["sando"]["pts"]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in sp], stroke="var(--shu)", sw=2.4, dash="8 4"))
    for t in d["torii"]:
        if not t["pos"]: continue
        x, z = t["pos"]
        o.append(LN(pr.X(x) - 8, pr.Y(z), pr.X(x) + 8, pr.Y(z), stroke="var(--shu)", sw=2.6))
        o.append(T(pr.X(x) + 11, pr.Y(z) + 4, t["name"], fs=11, fill="var(--shu)"))
    # 坂下の門
    for gt in d["gates"]:
        if gt["name"] != "坂下の門": continue
        w = g.W(gt["u"], gt["v"])
        o.append(R(pr.X(w[0]) - 4, pr.Y(w[1]) - 6, 8, 12, fill="var(--shu)", stroke="var(--ink)", sw=1.0))
        o.append(T(pr.X(w[0]) - 8, pr.Y(w[1]) + 4, gt["name"], fs=11, anchor="end", fill="var(--shu)"))
    # 山麓の通り(南北小路)
    o.append(PL([(pr.X(-386.4), pr.Y(715)), (pr.X(-387.8), pr.Y(845)), (pr.X(-390.0), pr.Y(926))],
                stroke="var(--dim)", sw=6.0, op=0.35))
    o.append(T(pr.X(-383), pr.Y(760), "山麓の通り(南北小路)", fs=10.5, fill="var(--dim)"))
    o += cut_lines(d, pr.X, pr.Y, pr.L,
                   clip=(14.0, pr.top + 10.0, pr.W - 14.0, pr.top + pr.zh - 6.0))
    o.append(T(6, 15, kan + "　山麓 ─ 二ノ鳥居の辻で折れて前庭へ入る", fs=12.5, fill="var(--dim)"))
    y = pr.H - 10
    o.append(LN(14, y, 14 + pr.L(50), y, stroke="var(--dim)", sw=1.2))
    o.append(T(14 + pr.L(50) / 2, y - 4, "50 m", fs=10.5, anchor="middle"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 門の立面
def mon_svg(d, kan="其十"):
    ken = d["const"]["ken"]
    W, H = 900.0, 300.0
    o = _sv(W, H, "門の立面")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    xs = [130.0, 450.0, 760.0]
    for i, gt in enumerate(d["gates"]):
        cx = xs[i]
        wk, dk = gt["plan"]["dv"], gt["plan"]["du"]      # 桁行(南北) / 梁間(東西)
        s = 20.0
        w = wk * ken * s / ken                            # px/間 = s
        bw = wk * s
        two = "楼門" in gt["kind"] or "二天門" in gt["name"]
        bh = (2.6 if two else 1.6) * s
        y0 = 232.0
        # 基壇
        o.append(R(cx - bw / 2 - 6, y0, bw + 12, 10, fill=_pat(), stroke="var(--ink)", sw=0.8))
        # 躯体
        o.append(R(cx - bw / 2, y0 - bh, bw, bh, fill="var(--shu)", op=0.35, stroke="var(--ink)", sw=1.0))
        # 柱
        for j in range(int(wk) + 1):
            px = cx - bw / 2 + bw * j / wk
            o.append(LN(px, y0, px, y0 - bh, stroke="var(--ink)", sw=1.4))
        # 屋根
        o.append(PL([(cx - bw / 2 - 14, y0 - bh), (cx, y0 - bh - 26), (cx + bw / 2 + 14, y0 - bh)],
                    stroke="var(--ink)", sw=1.2, fill="var(--hei)", op=0.55, close=True))
        if two:   # 二階の縁と腰屋根
            o.append(LN(cx - bw / 2 - 8, y0 - bh * 0.55, cx + bw / 2 + 8, y0 - bh * 0.55,
                        stroke="var(--ink)", sw=1.2))
        # 開口(一戸)
        o.append(R(cx - s * 0.5, y0 - bh * 0.62, s, bh * 0.62, fill="var(--paper)",
                   stroke="var(--ink)", sw=0.9))
        o.append(T(cx, y0 + 30, gt["name"], fs=13, anchor="middle"))
        o.append(T(cx, y0 + 46, gt["kind"], fs=10, anchor="middle", fill="var(--dim)"))
        o.append(T(cx, y0 + 60, "敷居 %.1f m ／ 桁行 %g 間 × 梁間 %g 間" % (gt["sill"], wk, dk),
                   fs=10, anchor="middle", fill="var(--dim)"))
        o.append(T(cx, y0 + 74, gt["acc"], fs=9.5, anchor="middle", fill="var(--dim)"))
    o.append(T(6, 15, kan + "　門の立面 ─ 高さと屋根は図示のための概略", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "**寸法が確度Aなのは中門だけ**", fs=10.5, anchor="end", fill="var(--shu)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 表
def munes_table(d):
    ken = d["const"]["ken"]
    rows = []
    for m in d["munes"]:
        w = m["du"] * ken; dpt = m["dv"] * ken
        rows.append("<tr><td>%s</td><td>%s</td><td>%g 間</td><td>%g 間</td><td>%.2f×%.2f m</td>"
                    "<td>%.0f m²</td><td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (m["name"], m["yaku"], m["dv"], m["du"], w, dpt, w * dpt,
                       html.escape(m["roof"]), m["acc"]))
    return ('<div class="tw"><table><thead><tr><th>棟</th><th>役</th><th>桁行(南北)</th><th>梁間(東西)</th>'
            "<th>外形 東西×南北</th><th>面積</th><th class='note'>屋根</th><th class='note'>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def runs_table(d):
    ken = d["const"]["ken"]
    rows = []
    for r in d["runs"]:
        if r.get("ken"):
            L = "%.1f 間 / %.2f m" % (r["ken"], r["ken"] * ken)
        elif r.get("pts"):
            pl = sum(math.hypot(r["pts"][i + 1][0] - r["pts"][i][0], r["pts"][i + 1][1] - r["pts"][i][1])
                     for i in range(len(r["pts"]) - 1))
            L = "%.1f 間 / %.2f m" % (pl, pl * ken)
        else:
            L = "—"
        seat = ("%.1f m" % r["seat"]) if r.get("seat") else "地形なり"
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (r["name"], r["kind"], L, seat, r.get("base", "—"),
                       html.escape(r.get("gate", "") or "—"), r.get("acc", "—")))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>種別</th><th>長さ</th><th>天端</th>'
            "<th>基壇</th><th class='note'>開口</th><th class='note'>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def kaidan_table(d):
    ken = d["const"]["ken"]
    rows = []
    for k in d["kaidans"]:
        L = math.hypot((k["b"][0] - k["a"][0]) * ken, (k["b"][1] - k["a"][1]) * ken)
        rise = k["yTop"] - k["yBot"]
        rows.append("<tr><td>%s</td><td>%d</td><td>%.3f</td><td>%.3f</td><td>%.2f m</td><td>%.2f m</td>"
                    "<td>%.1f%%</td><td>%s</td></tr>"
                    % (k["name"], k["steps"], rise / k["steps"], L / k["steps"], rise, L,
                       rise / L * 100, k["acc"]))
    return ('<div class="tw"><table><thead><tr><th>石段</th><th>段数</th><th>蹴上</th><th>踏面</th>'
            "<th>比高</th><th>平面長</th><th>勾配</th><th>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def walls_table(d):
    rows = []
    for w in d["terraceWalls"]:
        cop = w["coping"] if not isinstance(w["coping"], str) else w["coping"]
        rows.append("<tr><td>%s</td><td>(%.1f, %.1f) → (%.1f, %.1f)</td><td>%s</td><td>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (w["name"], w["a"][0], w["a"][1], w["b"][0], w["b"][1], cop,
                       w.get("acc", "—"), html.escape(w.get("_", ""))))
    return ('<div class="tw"><table><thead><tr><th>土留め</th><th>グリッド (u,v)</th><th>天端</th><th>確度</th>'
            "<th class='note'>注記</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def bom_table(d):
    rows = []
    for b in d["bom"]:
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td>%s</td></tr>"
                    % (inline(b["部材"]), inline(b["在庫"]), inline(b["手当"]), b["優先"]))
    return ('<div class="tw"><table><thead><tr><th>部材</th><th>在庫</th><th class="note">手当</th>'
            "<th>優先</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def sections_table(d):
    rows = []
    for s in d["sections"]:
        (x0, z0), (x1, z1) = s["line"]
        rows.append("<tr><td>%s</td><td>%s</td><td>(%.1f, %.1f) → (%.1f, %.1f)</td><td>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (s["kana"], s["name"], x0, z0, x1, z1, s["viewText"], inline(s["_"])))
    return ('<div class="tw"><table><thead><tr><th>矢視</th><th>断面</th><th>切断線の世界座標</th>'
            "<th>向き</th><th class='note'>何が読めるか</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def planes_table(d):
    rows = []
    for p in d["planes"]:
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (p["name"], ("%.1f m" % p["y"]) if p["y"] else "—(造成しない)",
                       inline(p["note"])))
    return ('<div class="tw"><table><thead><tr><th>面</th><th>高さ</th><th class="note">注記</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def neighbors_table(d):
    rows = []
    for n in d["neighbors"]:
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (n["name"], n["acc"], inline(n["_"])))
    return ('<div class="tw"><table><thead><tr><th>区画</th><th>確度</th><th class="note">考証</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def pending_table(d):
    rows = []
    for k, v in d["_pending"].items():
        rows.append("<tr><td>%s</td><td class='note'>%s</td></tr>" % (k, inline(v)))
    return ('<div class="tw"><table><thead><tr><th>件</th><th class="note">状態</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def history():
    try:
        log = subprocess.check_output(
            ["git", "-C", ROOT, "log", "--date=short", "--pretty=%h|%ad|%s", "--",
             "docs/Sashizu/sanno_sashizu.json", "docs/Sashizu/sanno_kosho.md"]).decode()
    except Exception:
        log = ""
    rows = []
    for ln in log.strip().split("\n"):
        if not ln.strip(): continue
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
    if legend: h.append('<div class="legend">%s</div>' % legend)
    if cap: h.append('<p class="cap">%s</p>' % cap)


KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
       "其十一", "其十二", "其十三", "其十四", "其十五", "其十六", "其十七", "其十八"]


def main():
    d = json.load(open(JSON, encoding="utf-8"))
    prose = md2html(open(MD, encoding="utf-8").read())
    g = G(d)
    ken = d["const"]["ken"]
    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()

    n = [0]
    def nx():
        n[0] += 1
        return KAN[n[0] - 1]

    h = ['<meta charset="utf-8">', "<title>山王権現社 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">永田馬場 星野山 ／ 江戸城の産土神 ／ 社領六百石</p>')
    h.append("<h1>山王権現社(日枝神社) 指図</h1>")
    h.append('<p class="lede">嘉永期の姿。社殿は万治二年造営のものが昭和二十年まで存続し、'
             '昭和六年に本殿・幣殿・拝殿・中門・透塀の五件が国宝に指定された。'
             'その指定説明を『麹町区史』が転記していて、<b>桁行×梁間・屋根形式・透塀の実延長までここで確定する</b>。'
             '境内の配置は文政三年の彩色実測図『山王御宮絵図』による。'
             '<b>数値の正典は <code>sanno_sashizu.json</code>、文章の正典は <code>sanno_kosho.md</code>。</b>'
             'この頁はその二つから組んだもので、実装は読んでいない。</p>')

    area = poly_area(d["polygon"])
    kei = poly_area([g.W(u, v) for u, v in d["terraces"][0]["uv"]])
    h.append('<div class="box"><p><b>境内 一万八千五百七十坪</b>【B — 『大江戸今昔めぐり』(嘉永年間の切絵図がベース)の記載】。'
             'これは社地・別当観理院・社僧十坊を合わせた社領全体の坪数で、'
             '当図の区画の実測合計は <b>19,202 坪</b>(社地 %.0f 坪 + 観理院 1,526 坪 + 十坊 4,402 坪)= <b>記載値の +3.4%%</b>【P】。'
             '<b>多角形そのものは拝領坪数の起こしではなく、既実装の隣地から割り出した残余</b>【U】 — '
             '一致は裏づけであって典拠ではない。山上の平場は %.0f m²(%.0f 坪)【P】。'
             '⚠ 俗説の「約一万坪」は出所不明【?】。</p></div>'
             % (area / TSUBO, kei, kei / TSUBO))

    # 其一 社地
    plate(h, nx(), "社地", "北が上 ／ 境内 18,570 坪【B】")
    fig(h, shachi_svg(d, KAN[n[0] - 1]),
        legend='<span style="color:var(--shu)">■ 社殿・透塀・参道</span>'
               '<span style="color:var(--roka)">■ 回廊</span>'
               '<span style="color:var(--ishi)">■ 石段</span>'
               '<span>■ 境内(山上)</span><span>■ 前庭</span><span>■ 社叢(造成しない)</span>',
        cap="<b>社叢が境内の実体で、建物は樹林の中の明地に建つ。</b>切絵図は境内全体を"
            "「緑=山林土手馬場原」一筆で塗り、御宮絵図も外周をぐるりと濃緑で塗る【S】。"
            "石段は東へ二本だけで、<b>南西(溜池側)には降りていない</b>【S】。")
    h.append(planes_table(d))
    h.append("<h3>断面の一覧</h3>")
    h.append(sections_table(d))
    h.append('<p class="cap">切断線は其一・其二・其十四の平面に<b>一点鎖線と矢視記号</b>で落としてある。'
             '<b>東西の断面は左が西・右が東で北を見る</b>／<b>南北の断面は左が南・右が北で西を見る</b>。</p>')
    h.append("</div>")

    # 其二 境内 平面
    plate(h, nx(), "境内 平面", "世界軸グリッド ／ 1間 = 1.818 m ／ 原点 = 楼門の芯")
    fig(h, keidai_svg(d, -50, 36, -34, 33, "其二　境内 平面"),
        legend='<span style="color:var(--shu)">■ 社殿・門・透塀</span>'
               '<span style="color:var(--roka)">■ 回廊</span>'
               '<span style="color:var(--nagaya)">■ 附属堂・御供所</span>'
               '<span style="color:var(--ishi)">■ 御蔵</span>'
               '<span style="color:var(--hei)">┄ 板塀</span><span>○ 石灯籠</span>',
        cap="<b>軸は一直線の東西。</b>東から 坂下の門 → 男坂 → 楼門 → 白洲 → 中門 → 向拝 → 拝殿 → 幣殿 → 本殿。"
            "<b>山上の門は楼門一基</b>で、南北に長い御廻廊二棟の中央に立ち、回廊が境内の東frontを成す【S】。"
            "社殿を囲うのは透塀で、その正面に中門【S/A】。<b>附属堂九棟の銘はすべて崩し字で未判読</b>【?】 — "
            "名所図会の題箋(薬師・不動・庚申・鐘楼・鼓楼・宝蔵)のどれかである見込みだが、推定で名を与えない。")

    h.append("</div>")

    # 其三 社殿 平面
    plate(h, nx(), "社殿 平面", "透塀 東西23.5間 × 南北17間 = 周長 81 間 ／ 東線 = 袖8+中門1+袖8")
    fig(h, keidai_svg(d, -49, -19, -12, 12, "其三　社殿 平面(拡大)"),
        cap="<b>幣殿型権現造・本殿入母屋造。</b>本殿(方三間)—作り合い(一間・海老虹梁)—幣殿(三間×一間)"
            "—拝殿(七間×三間)—向拝(三間)。<b>幣殿型は向拝一間が通例だが、日枝は石の間型と同格の三間を採る</b>【A】。"
            "囲いは瑞垣のタイプX(正面に瑞垣門=中門を構え、門の両側から瑞垣=透塀が社殿を一周する)【A】。"
            "<b>透塀の矩形は史料の延長 147.28 m にちょうど合わせてある</b> — 周長が設計拘束になっている。")
    h.append(munes_table(d))
    h.append("</div>")

    # 断面
    # ---- 断面(json の sections を順に) ----
    def poly_zrange(x):
        """境内の平場の多角形が x で覆う z の範囲。"""
        P = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
        zs = []
        for i in range(len(P)):
            (x1, z1), (x2, z2) = P[i], P[(i + 1) % len(P)]
            if (x1 - x) * (x2 - x) <= 0 and abs(x2 - x1) > 1e-9:
                zs.append(z1 + (z2 - z1) * (x - x1) / (x2 - x1))
        return (min(zs), max(zs)) if len(zs) >= 2 else (None, None)

    yk, yz = 28.3, 14.5
    st = [k for k in d["kaidans"] if k["name"] == "男坂"][0]
    sx0, sx1 = g.W(st["a"][0], 0)[0], g.W(st["b"][0], 0)[0]
    zt = d["terraces"][1]
    zx0, zx1 = g.W(zt["u0"], 0)[0], g.W(zt["u1"], 0)[0]
    kz0, kz1 = g.W(0, -11)[1], g.W(0, 11)[1]
    po = d["profiles"]["ONNA"]
    L_on = math.hypot(po["b"][0] - po["a"][0], po["b"][1] - po["a"][1])
    uo = (-466.0 - g.x0) / ken
    y_ox = yk - (uo - st["a"][0]) / (st["b"][0] - st["a"][0]) * (yk - yz)

    CAP = {
      "EW857": ("<b>この図が指図の要。</b><b>左が西(本殿)・右が東(山麓)で、北を見る断面</b>。"
                "<b>規定の蹴上・踏面で割った石段は東法面より格段に急なので、男坂の区間は切通しになり両側に石垣が立つ。</b>"
                "名所図会が描く「石段の両側の笠付きの土留め側壁」と「坂下の門の左右の塀が石積みの上に載る」姿は、まさにこの形【S】。"
                "⚠ <b>未解決</b> — 地理院1mレーザDEMを直接引くと東法面はもっと急で、その断面なら切土はごく浅くて済む。"
                "<b>地形を寄せ直すかどうかはユーザーの裁定</b>。"),
      "NS560": ("<b>左が南・右が北で、西を見る断面</b>。<b>観音堂 → 御供所 → 透塀 → 本殿 → 透塀 → 附属堂 其一</b>を切る。"
                "⚠ 山頂平坦面は南北の縁で下がるので、境内面28.3への均しは<b>切土だけでなく1.4〜1.6mの盛土にもなる</b>。"),
      "ONNA":  ("<b>左が山上(西南)・右が前庭(東北)で、北西を見る断面</b>。<b>女坂は男坂の南を斜めに下る</b>【S 御宮絵図】。"
                "『新撰東京名所図会』が「昔時将軍家御成の節、峻坂を避け、此坂のみ御通行遊ばされしにより、"
                "御成坂と申侍る」とする【B】 — <b>裏の脇道ではないので踏面を男坂より広く取り格を落とさない</b>。"
                "下三分の一が4m級の切通しになるので、両側に側壁(TW_Onna_N/S)を立てる。"),
      "NS4842": ("<b>回廊は直線で通るが、平坦面の東縁は z870 から急に西へ退く。</b>差は石垣の基壇で受ける。"
                "回廊を22間に詰めたので露出は北端で約1.3mに収まる。名所図会が回廊を石垣の上に載せて描くのはこの形【S】。"),
      "OTOKO_X": ("<b>切通しのU字。</b>男坂は設計中いちばん大きい土木構造物だが、"
                "軸方向の断面イにはその姿が写らない。<b>左が南・右が北で、西を見る断面</b> — <b>地形が南で高いぶん南側壁のほうが高い</b>。"),
      "ZENTEI_NS": ("<b>左が南・右が北で、西を見る断面</b>。<b>前庭は南で切土・北で盛土と符号が変わる</b>(地形が北へ下るため)。"
                "北縁の土留めは山を受ける擁壁ではなく<b>盛土の腰石垣</b>。"),
      "WEST":  ("境内の西縁のすぐ外。<b>30mで17m落ちる急崖で、造成しない</b>。"
                "切絵図はここを含めて境内全体を「緑=山林土手馬場原」一筆で塗る【S】。"),
    }
    for sec in d["sections"]:
        key = sec["profile"]
        prof = _profile(d, key)
        flats, stairs, marks = [], [], []
        if key == "EW857":
            flats = [(-573.0, sx0, yk), (sx1, zx1, yz)]
            stairs = [(sx0, sx1, yk, yz)]
            for m in d["munes"]:
                if m["yaku"] not in ("社殿",): continue
                marks.append((g.W(m["u0"], 0)[0], g.W(m["u0"] + m["du"], 0)[0], yk, m["name"], "社殿"))
            for gt in d["gates"]:
                marks.append((g.W(gt["u"] - gt["plan"]["du"] / 2.0, 0)[0],
                              g.W(gt["u"] + gt["plan"]["du"] / 2.0, 0)[0],
                              gt["sill"], gt["name"].split("(")[0], "門"))
        elif key == "NS560":
            za, zb = poly_zrange(-560.0)
            flats = [(za, zb, yk)]
            uu = (-560.0 - g.x0) / ken
            for m in d["munes"]:
                if not (m["u0"] <= uu <= m["u0"] + m["du"]): continue
                marks.append((g.W(0, m["v0"])[1], g.W(0, m["v0"] + m["dv"])[1], yk, m["name"],
                              "社殿" if m["yaku"] == "社殿" else "堂"))
            for v in (-8.5, 8.5):
                z = g.W(0, v)[1]
                marks.append((z - 0.4, z + 0.4, yk, "透塀", "塀"))
        elif key == "ONNA":
            flats = [(prof[0][0], 0.0, yk), (L_on, prof[-1][0], yz)]
            stairs = [(0.0, L_on, yk, yz)]
        elif key == "NS4842":
            flats = [(kz0 - 2.0, kz1, yk)]
            marks = [(kz0, g.W(0, -1.5)[1], yk, "回廊 南翼", "廊"),
                     (g.W(0, -1.5)[1], g.W(0, 1.5)[1], yk, "楼門", "門"),
                     (g.W(0, 1.5)[1], kz1, yk, "回廊 北翼", "廊")]
        elif key == "OTOKO_X":
            flats = [(g.W(0, -1.5)[1], g.W(0, 1.5)[1], y_ox)]
            for v in (-1.5, 1.5):
                z = g.W(0, v)[1]
                marks.append((z - 0.4, z + 0.4, y_ox, "側壁", "塀"))
        elif key == "ZENTEI_NS":
            flats = [(g.W(0, zt["v0"])[1], g.W(0, zt["v1"])[1], yz)]
        design = design_line(prof, flats, stairs)
        plate(h, nx(), sec["name"],
              ("%s = %g ／ %s" % (sec["axis"], sec["at"], sec["viewText"]))
              if "at" in sec else "%s ／ %s" % (sec["axis"], sec["viewText"]))
        fig(h, section_svg(d, key, design, marks, "%s　%s" % (KAN[n[0] - 1], sec["name"]),
                           flip=False, viewtxt="矢視 " + sec["kana"] + " ／ " + sec["viewText"]),
            cap=CAP.get(key, ""))
        h.append("</div>")

    plate(h, nx(), "男坂と女坂の割付", "蹴上 0.30 は CLAUDE.md の規定")
    fig(h, saka_svg(d, KAN[n[0] - 1]),
        cap="<b>現状の男坂は五十三段だが、江戸期の段数の記録は無い</b>【?】。当図の段数は現地形の比高と"
            "規定の蹴上から出した設計値【U】。⚠ <b>現行実装は男坂として成立していない</b> — "
            "石段の下端が法尻より外へ大きく食み出していて、勾配が緩い雁木になっている。")
    h.append(kaidan_table(d))
    h.append("</div>")

    plate(h, nx(), "囲いの展開", "透塀 = 旧国宝五件のうちの一件")
    fig(h, kakoi_svg(d, KAN[n[0] - 1]),
        cap="刻みは一間ごとの柱。<b>透塀の延長 147.28 m(486.01尺)は『麹町区史』の指定説明の転記で確度A</b>。"
            "これはちょうど八十一間で、設計の矩形はこの周長に合わせてある。")
    h.append(runs_table(d))
    h.append(walls_table(d))
    h.append("</div>")

    plate(h, nx(), "門", "山上は楼門一基。もう一基は男坂の下")
    fig(h, mon_svg(d, KAN[n[0] - 1]))
    rows = []
    for gt in d["gates"]:
        w = g.W(gt["u"], gt["v"])
        rows.append("<tr><td>%s</td><td>(%.1f, %.1f)</td><td>%.1f m</td><td>%d×%d 間</td>"
                    "<td class='note'>%s</td><td>%s</td></tr>"
                    % (gt["name"], w[0], w[1], gt["sill"], gt["plan"]["du"], gt["plan"]["dv"],
                       html.escape(gt["kind"]), gt["acc"]))
    h.append('<div class="tw"><table><thead><tr><th>門</th><th>芯の世界座標 (x,z)</th><th>敷居</th>'
             "<th>外形</th><th class='note'>形式</th><th>確度</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table></div>")
    h.append('<p class="cap">⛔ <b>現行実装の「境内に仁王門と随身門の二基」は誤り。</b>'
             '絵図の銘は「樓門」、名所図会の題箋は「随身門」で、同一の門の別称と読む【S】。'
             'もう一基は男坂の下にあり、名所図会では「仁王門」と読める【S(読みは要確認)】が、'
             '<b>形式も名も確定していない</b>【?】。<b>中門だけは旧国宝の指定説明に'
             '「一間平唐門・屋根銅瓦葺」とあり確度A</b>。</p>')
    h.append("</div>")

    plate(h, nx(), "山麓 ─ 別当・神主・門前町", "この指図の範囲は「山王社一式」")
    fig(h, sanroku_svg(d, KAN[n[0] - 1]),
        cap="二ノ鳥居は境内東麓の辻(北=樹下邸・山王門前町/南=観理院)に立ち、"
            "参道はそこで折れて前庭へ入る — 名所図会の「鳥居から左折して参道が進む」と整合【S】。"
            "<b>一ノ鳥居は存在が確度Sだがシーン座標は未確定</b>【?】(切絵図は非等尺で px/m 換算が効かない)。")
    h.append(neighbors_table(d))
    h.append("</div>")

    plate(h, nx(), "部材", "神社建築は在庫にゼロ")
    h.append(bom_table(d))
    h.append('<p class="cap">edogoyomi / Japanese Castle / Japanese Village Kit / Waldemarst の四パックとも'
             '城郭・町屋・農家・植栽しか持たない。流用できるのは<b>石段</b>(汐見坂で実績のある段石)と'
             '<b>石灯籠</b>だけ。<b>社殿本体が最優先</b> — 現況は Village Kit の民家を代用していて神社に見えない。</p>')
    h.append("</div>")

    plate(h, nx(), "考証と決めごと", "文章の正典は sanno_kosho.md")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, nx(), "未解決", "推定で埋めない対象")
    h.append(pending_table(d))
    h.append("</div>")

    plate(h, nx(), "改訂", "経緯は git log docs/Sashizu/")
    h.append(history())
    h.append("</div>")

    h.append('<p class="cap" style="margin-top:44px">図版 %d 面。'
             '<b>組み直すときは図を落としていないか必ず数える</b>(過去に16図版→1図版へ落ちた前科がある)。</p>'
             % n[0])
    h.append("</div>")
    open(OUT, "w", encoding="utf-8").write("\n".join(h))
    print("wrote %s ／ 図版 %d 面" % (OUT, n[0]))


if __name__ == "__main__":
    main()
