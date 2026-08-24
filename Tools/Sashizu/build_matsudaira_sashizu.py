#!/usr/bin/env python3
"""松平出羽守上屋敷(出雲松江藩)の指図を組む。

    python3 Tools/Sashizu/build_matsudaira_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/matsudaira_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/matsudaira_kosho.md     … 文章の部(人が書く・現況形)

の二つだけ。実装から指図を作ると CLAUDE.md 絶対規則2 の関門が消える。

【この屋敷ならではの作り】北辺の大通りが世界軸から振れているため(角度は json の grid が正典)、
主郭は**回転間グリッド**(u=北辺沿い東+ / v=敷地の奥+)で持つ。
    ・世界図版(其一)は Proj(世界→px)
    ・御殿平面(其二・其三)は LProj(グリッド間→px)— 棟・室・庭はすべて軸平行になる
    ・外周(其六)は辺番号+辺沿い走り s で持つ run を展開する

【図版】章立ては生成順(敷地/表向 平面/中奥・奥向 平面/東上段 平面/棟と室/断面×4/
        外周の展開/表門まわり/郭の土留め/考証/改訂)。
        組んだら「図版 N 面」を数えること(図版が黙って落ちた前科がある)。
"""
import json, math, os, re, subprocess, html

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "matsudaira_sashizu.json")
MD = os.path.join(DOC, "matsudaira_kosho.md")
OUT = os.path.join(DOC, "matsudaira_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown(岡部と同じ最小変換)
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
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "-", "|")) and lines[i].strip() != "---":
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def inline(s):
    s = re.sub(r'</?span[^>]*>', "", s)
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"【([^】]*確度 ?[SABPU?][^】]*)】", r'<span class="cert">【\1】</span>', s)
    s = re.sub(r"【(写真=A[^】]*)】", r'<span class="cert">【\1】</span>', s)
    return s


# ---------------------------------------------------------------- 作図の土台
_SVN = [0]


def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, label),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.65"/>'
            '</pattern></defs>' % _SVN[0]]


def _pat(): return "url(#pi%d)" % _SVN[0]


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


class RGrid(object):
    """回転間グリッド (u,v)[間] → 世界座標。u=北辺沿い東+ / v=敷地の奥+。"""

    def __init__(self, d, name="shukaku"):
        g = d["grid"][name]
        self.ken = d["const"]["ken"]
        self.x0, self.z0 = g["x0"], g["z0"]
        self.ux, self.uz, self.vx, self.vz = g["ux"], g["uz"], g["vx"], g["vz"]

    def W(self, u, v):
        um, vm = u * self.ken, v * self.ken
        return (self.x0 + self.ux * um + self.vx * vm,
                self.z0 + self.uz * um + self.vz * vm)

    def L(self, x, z):
        """世界 → (u,v)[間]。"""
        dx, dz = x - self.x0, z - self.z0
        return ((dx * self.ux + dz * self.uz) / self.ken,
                (dx * self.vx + dz * self.vz) / self.ken)


class LProj(object):
    """グリッド座標 (u,v)[間] → SVG px。v は下向き(奥)がそのまま画面の下。"""

    def __init__(self, u0, u1, v0, v1, W=900.0, top=22.0, bottom=20.0):
        self.u0, self.u1, self.v0, self.v1 = u0, u1, v0, v1
        self.s = W / float(u1 - u0)
        self.W, self.top = W, top
        self.vh = (v1 - v0) * self.s
        self.H = self.vh + top + bottom

    def X(self, u): return (u - self.u0) * self.s
    def Y(self, v): return self.top + (v - self.v0) * self.s
    def L(self, ken): return ken * self.s

    def rect(self, u0, v0, u1, v1, **kw):
        return R(self.X(min(u0, u1)), self.Y(min(v0, v1)),
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


# 面の色は **planes(正典)から組む**。直書きすると面の高さを変えたとき図だけ古くなる
# (2026-08-23 検図: 表郭を 25.8→26.7 にしたのに DAN のキーが 25.8 のままで、
#  白洲が fallback 色=斜面とほぼ同色で描かれていた)
_PL_COLS = ["var(--pl-omote)", "var(--pl-main)", "var(--pl-higashi)", "var(--pl-suso)"]
def dan_map(d):
    m = {}
    for i, pl in enumerate(d["planes"]):
        if isinstance(pl.get("y"), (int, float)):
            m[float(pl["y"])] = _PL_COLS[min(i, len(_PL_COLS) - 1)]
    return m
DAN = {}
PLANE_COL = {"表郭": "var(--pl-omote)", "主平面": "var(--pl-main)", "斜面(造成しない)": "var(--pl-slope)"}
KC = {"Nagaya": "var(--nagaya)", "Dobei": "var(--hei)"}
FENCE_H = 1.4                                        # 境界の木柵(地形なり・基礎なし)

MUNE_JA = {
    "Yakusho": "表役所棟", "Genkan": "玄関棟", "Ohiroma": "大広間棟", "Kuroshoin": "黒書院棟",
    "OnariGenkan": "御成玄関", "OnariShoin": "御成書院棟", "OnariYudono": "御成湯殿",
    "Gakuya": "楽屋棟", "Butai": "能舞台", "Nakaoku": "中奥棟", "Daidokoro": "大台所棟",
    "Okugoten": "奥御殿棟", "OkuYudono": "御湯殿", "NagatsuboneN": "長局棟(北)",
    "NagatsuboneS": "長局棟(南)", "OkuDaidokoro": "奥台所棟", "Umaya": "厩棟",
}
TERR_JA = {"Omote": "表郭", "OmoteE": "東肩の帯", "Shukaku": "主郭", "ShukakuE": "主郭(東翼)",
           "ShukakuS": "奥郭", "ShukakuN": "蔵の帯", "Fukugen": "掘削跡の埋め戻し(復元)"}


# ---------------------------------------------------------------- 其一 敷地
def plan_svg(d):
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), 900.0, pad=14.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 敷地全体")

    def gpoly(u0, v0, u1, v1, **kw):
        pts = [gr.W(u0, v0), gr.W(u1, v0), gr.W(u1, v1), gr.W(u0, v1)]
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
        g.append(gpoly(t["u0"], t["v0"], t["u1"], t["v1"],
                       fill=DAN.get(t["y"], "var(--dan4)"), op=1.0))
    # 堀端の裾(9.2)の帯 — 縁の run に沿う内側幅3mの整地帯
    suso = [r for r in d["runs"] if abs(r["seat"] - 9.2) < 0.01]
    for r in suso:
        a2 = edge_pt(P, r["edge"], r["s0"]); b2 = edge_pt(P, r["edge"], r["s1"])
        dx, dz, _L = _edge_dir(P, r["edge"])
        nx_, nz_ = -dz, dx
        cx = ((-694.7) - (a2[0] + b2[0]) / 2, 1029.5 - (a2[1] + b2[1]) / 2)
        if False:
            pass
        # 内向き判定: 敷地重心側
        gx, gz = -640.0, 1180.0
        if (gx - a2[0]) * nx_ + (gz - a2[1]) * nz_ < 0:
            nx_, nz_ = -nx_, -nz_
        quad = [a2, b2, (b2[0] + nx_ * 3, b2[1] + nz_ * 3), (a2[0] + nx_ * 3, a2[1] + nz_ * 3)]
        g.append('<polygon points="%s" fill="var(--pl-suso)" opacity="0.85"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in quad))
    # 斜面(造成しない)のラベル
    for x, z, t2 in ((-724, 1105, "西斜面(造成しない)"),
                     (-630, 1110, "南西の谷"),
                     (-742, 1195, "北西の登り")):
        g.append(T(pr.X(x), pr.Y(z), t2, "anS2", "middle"))
        cx, cz = gr.W((t["u0"] + t["u1"]) / 2.0, (t["v0"] + t["v1"]) / 2.0)
        g.append(T(pr.X(cx), pr.Y(cz), "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"]),
                   "anS", "middle"))
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
    # 境界の木柵(地形なり)
    for f in d.get("fences", []):
        a = edge_pt(P, f["edge"], f["s0"]); b = edge_pt(P, f["edge"], f["s1"])
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]),
                    "var(--take)", 1.8, dash="6 3"))
    # 郭の土留め
    for w in d["terraceWalls"]:
        a = gr.W(*w["a"]); b = gr.W(*w["b"])
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]), "var(--ishi)", 3, dash="7 4"))
    # 竹垣
    for rl in d["rails"]:
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
        g.append(T(pr.X(kp[0]) + 6, pr.Y(kp[1]) + 10, k["name"] == "Kuramon" and "御蔵門" or "小門", "jo"))
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
            a = gr.W(s["at"], s["from"]); b = gr.W(s["at"], s["to"])
        else:
            a = gr.W(s["from"], s["at"]); b = gr.W(s["to"], s["at"])
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]), "var(--shu)", 0.9, dash="9 5", op=0.8))
        g.append(T(pr.X(b[0]), pr.Y(b[1]) - 6, s["name"].split(" ")[0], "sr", "middle"))

    # 街路の名
    g.append(T(pr.X(-660), pr.Y(1292), "赤坂御門 → 永田馬場の大通り", "anS"))
    g.append(T(pr.X(-462), pr.Y(1240), "三べ坂前身の南北道", "anS", "end"))
    g.append(T(pr.X(-750), pr.Y(1082), "堀端通り(溜池東岸)", "anS"))
    g.append(T(pr.X(-604), pr.Y(1120), "土井邸(背中合わせ)", "anS2"))
    g.append(T(pr.X(-648), pr.Y(1052), "岡部邸", "anS2"))
    g.append(T(pr.W - 6, 15, "北 ↑　左=西(溜池)", "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其二・其三 御殿平面(グリッド座標)
def goten_plan(d, u0, u1, v0, v1, label, note):
    pr = LProj(u0, u1, v0, v1, 900.0)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 %s" % label)
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
        g.append(pr.rect(max(t["u0"], u0), max(t["v0"], v0), min(t["u1"], u1), min(t["v1"], v1),
                         fill=DAN.get(t["y"], "var(--dan4)"), op=1.0))
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
        col = {"shirasu": "var(--shirasu)", "ike": "var(--ike)",
               "nakajima": "var(--niwa)", "tsukiyama": "var(--tsuki)"}.get(
                   n.get("kind"), "var(--niwa)")
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
        g.append(T(pr.X(min(a_u, b_u) + 1), pr.Y(max(min(a_v, b_v), v0) + 1.6), w["name"], "jo"))
    for k in d["kaidans"]:
        _ws = [x for x in d["terraceWalls"] if x["name"] == k.get("atWall")]
        if not _ws:
            continue          # 土留めの無い段(0.3m など)は石段だけ
        w = _ws[0]
        if w["a"][0] == w["b"][0]:
            cu, cv = w["a"][0], k["gapV"]
            g.append(pr.rect(cu - 0.9, cv - k["w"] / 2 / 1.818, cu + 0.9, cv + k["w"] / 2 / 1.818,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        else:
            cu, cv = k["gapU"], w["a"][1]
            g.append(pr.rect(cu - k["w"] / 2 / 1.818, cv - 0.9, cu + k["w"] / 2 / 1.818, cv + 0.9,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        g.append(T(pr.X(cu), pr.Y(cv) - 8, "%s %d段" % (k["name"], k["steps"]), "anS2", "middle"))
    for rl in d["rails"]:
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
            g.append(T(cx, cy + 11, ("%d間²" % (r["tatami"] // 2)) if r.get("ita") else ("%d畳" % r["tatami"]),
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
            ou = (d["onarimon"]["s"] - d["gate"]["s"]) / 1.818
            if u0 <= ou <= u1:
                g.append(T(pr.X(ou), pr.Y(0) - 6, "▼ 御成門", "sr", "middle"))
    # 小門(御蔵門など)は世界座標→グリッドへ変換して窓内なら示す
    for k in d["komon"]:
        kp = edge_pt(d["polygon"], k["edge"], k["s"])
        ku, kv = gr.L(kp[0], kp[1])
        if u0 <= ku <= u1 and v0 - 2 <= kv <= v1:
            g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)" opacity="0.8"/>' % (pr.X(ku), pr.Y(kv)))
            g.append(T(pr.X(ku) + 7, pr.Y(kv) + 4, "御蔵門" if k["name"] == "Kuramon" else "小門", "sr"))

    g.append(T(4, 15, "グリッド座標(u=大通り沿い東+/v=敷地の奥+)。図の上=大通り", "anS"))
    g.append(T(4, pr.H - 5, note, "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其五 断面
def section_svg(d, sec):
    gr = RGrid(d)
    K = d["const"]["ken"]
    at, ex = sec["at"], sec["vExag"]
    w0, w1 = sec["from"], sec["to"]

    def covers(t):
        if sec["axis"] == "u":
            return t["u0"] <= at <= t["u1"]
        return t["v0"] <= at <= t["v1"]

    def span(t):
        return (t["v0"], t["v1"]) if sec["axis"] == "u" else (t["u0"], t["u1"])

    # 施工後の面(design)と現況地盤(natural)を**別々に**持つ。
    # 段が覆う区間=設計面、覆わない区間=現況のまま。両者の差が切土/盛土。
    segs = []
    for t in d["terraces"]:
        if covers(t):
            a, b = span(t)
            a, b = max(a, w0), min(b, w1)
            if b > a:
                segs.append((a, b, t["y"]))
    segs.sort()
    nat = sorted([(p[0], p[1]) for p in sec.get("natural", [])])

    def nat_at(w):
        """現況地盤(実測)。実測範囲の外は None。"""
        if not nat or w < nat[0][0] - 1e-6 or w > nat[-1][0] + 1e-6:
            return None
        for i in range(len(nat) - 1):
            a, ya = nat[i]
            b, yb = nat[i + 1]
            if a <= w <= b:
                return ya if b <= a else ya + (yb - ya) * (w - a) / (b - a)
        return nat[-1][1]

    # 段の縁の始末は**実装(EdoMatsudairaBuilder.DesignY)と同じ規則**で描く。
    #   土留め(terraceWalls)のある縁 … 垂直。石垣が段差を受けるので地面は現況のまま
    #   土留めの無い縁               … 1:const.feather の土の法面で現況へ着地
    K = d["const"]["ken"]
    BFILL = d["const"].get("batterFill", 1.5)
    BCUT = d["const"].get("batterCut", 1.0)
    WALLNEAR = d["const"].get("wallNear", 0.6)
    CAP = d["const"].get("featherCap", 12.0)

    def _dseg(p, a, b):
        (px, py), (ax, ay), (bx, by) = p, a, b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        return math.hypot(px - (ax + dx * t), py - (ay + dy * t))

    def _grid_pt(w):
        """断面上の位置 w → グリッド座標 (u,v)。"""
        return (at, w) if sec["axis"] == "u" else (w, at)

    def design_at(w):
        """施工後の地盤。実装の DesignY と同じ三層。"""
        for a, b, y in segs:
            if a - 1e-6 <= w <= b + 1e-6:
                return y
        nz = nat_at(w)
        if nz is None:
            return None
        g = _grid_pt(w)
        # 最寄りの段と、その縁の最寄り点
        dT, yT, cp = 1e9, None, None
        for t in d["terraces"]:
            cu = max(t["u0"], min(g[0], t["u1"]))
            cv = max(t["v0"], min(g[1], t["v1"]))
            dd = math.hypot(g[0] - cu, g[1] - cv) * K
            if dd < dT:
                dT, yT, cp = dd, t["y"], (cu, cv)
        if yT is None:
            return nz
        for wl in d["terraceWalls"]:              # 縁に土留めがあれば垂直=現況のまま
            if _dseg(cp, tuple(wl["a"]), tuple(wl["b"])) <= WALLNEAR:
                return nz
        # 法面は盛土を支えるためだけに張る: 縁が盛土/cap以内/着地する の三つ
        cpn = nat_at(cp[1] if sec["axis"] == "u" else cp[0])
        if cpn is None or yT - cpn <= 0.05:
            return nz
        if dT > CAP or not _daylights(cp, g, yT, nat_at, BFILL, CAP, K):
            return nz
        slack = dT / max(0.5, BFILL if yT > nz else BCUT)
        return max(yT - slack, min(nz, yT + slack))

    ws = [w0 + (w1 - w0) * i / 600.0 for i in range(601)]
    for a, b, _y in segs:                          # 段の縁を標本に含める(鋸歯を出さない)
        ws += [a - 1e-4, a + 1e-4, b - 1e-4, b + 1e-4]
    ws += [p[0] for p in nat]
    ws = sorted(set(w for w in ws if w0 - 1e-9 <= w <= w1 + 1e-9))
    prof = [(w, design_at(w)) for w in ws]
    prof = [(w, y) for w, y in prof if y is not None]

    ys = [p[1] for p in prof] + [p[1] for p in nat]
    y1 = max(ys) + 8.0
    y0 = min(ys) - 3.0
    W = 1000.0
    sx = W / float(w1 - w0)
    HEAD, FOOT = 26.0, 46.0
    H = (y1 - y0) * sx * ex + HEAD + FOOT

    def X(w): return (w - w0) * sx
    def Y(y): return HEAD + (y1 - y) * sx * ex

    g = _sv(W, H, "松平出羽守上屋敷 %s" % sec["name"])
    _id = _SVN[0]
    g.append('<defs>'
             '<pattern id="cut%d" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<path d="M0,0 v6" stroke="var(--shu)" stroke-width="1.6" opacity="0.8"/></pattern>'
             '<pattern id="fil%d" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
             '<path d="M0,0 v6" stroke="var(--nagaya)" stroke-width="1.6" opacity="0.75"/></pattern>'
             '</defs>' % (_id, _id))
    # 施工後の地盤(この線から下が拝領時造成を終えた地面)
    pts = [(X(w0), Y(y0 + 0.01))] + [(X(a), Y(b)) for a, b in prof] + [(X(w1), Y(y0 + 0.01))]
    g.append('<polygon points="%s" fill="var(--dan)" stroke="var(--ink)" stroke-width="1.4"/>'
             % " ".join("%.1f,%.1f" % p for p in pts))
    # 面割りの色帯(地表下0.6m)
    for a, b, y in segs:
        if b > a:
            g.append(R(X(a), Y(y), X(b) - X(a), 0.6 * sx * ex,
                       fill=DAN.get(y, 'var(--dan4)'), op=0.9))
    for a, b, y in segs:
        if b - a > 6:
            g.append(T((X(a) + X(b)) / 2, Y(y) + 14, "%.1f m" % y, "anS", "middle"))

    # ---- 切土(なくなる部分)/ 盛土(足す部分)/ 造成しない(守る部分) ----
    TOL = 0.05
    kinds, cur = [], None
    for w in ws:
        dz, nz = design_at(w), nat_at(w)
        k = None
        if dz is None or nz is None:
            k = "unknown"
        elif nz - dz > TOL:
            k = "cut"
        elif dz - nz > TOL:
            k = "fill"
        else:
            k = "keep"
        if cur is None or cur[0] != k:
            cur = (k, [])
            kinds.append(cur)
        cur[1].append((w, dz, nz))
    for k, rows in kinds:
        if len(rows) < 2:
            continue
        wa, wb = rows[0][0], rows[-1][0]
        if k in ("cut", "fill"):
            hi = [(X(w), Y(max(dz, nz))) for w, dz, nz in rows]
            lo = [(X(w), Y(min(dz, nz))) for w, dz, nz in rows]
            g.append('<polygon points="%s" fill="url(#%s%d)" stroke="%s" stroke-width="1.0" '
                     'stroke-dasharray="4 3"/>'
                     % (" ".join("%.1f,%.1f" % p for p in hi + lo[::-1]),
                        "cut" if k == "cut" else "fil", _id,
                        "var(--shu)" if k == "cut" else "var(--nagaya)"))
            dep = max(abs(nz - dz) for _w, dz, nz in rows)
            if (wb - wa) * sx > 46:
                mid = rows[len(rows) // 2]
                g.append(T((X(wa) + X(wb)) / 2, Y((mid[1] + mid[2]) / 2) + 4,
                           ("切土 −%.1fm" if k == "cut" else "盛土 +%.1fm") % dep,
                           "anS2", "middle",
                           fill="var(--shu)" if k == "cut" else "var(--nagaya)"))
        # 足元の帯: 守る区間 / 未実測区間
        if k in ("keep", "unknown") and (wb - wa) * sx > 10:
            col = "var(--take)" if k == "keep" else "var(--dim)"
            g.append(R(X(wa), Y(y0) + 20, X(wb) - X(wa), 5, fill=col,
                       op=0.85 if k == "keep" else 0.35))
            if (wb - wa) * sx > 52:
                g.append(T((X(wa) + X(wb)) / 2, Y(y0) + 34,
                           "造成しない(現地形のまま)" if k == "keep" else "現況未実測",
                           "anS2", "middle", fill=col))
    # 現況地盤の線(この線が地形再作成後の実測)
    if nat:
        g.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.3" '
                 'stroke-dasharray="7 4" opacity="0.85"/>'
                 % " ".join("%.1f,%.1f" % (X(w), Y(y)) for w, y in nat))
        g.append(T(X(nat[0][0]) + 3, Y(nat[0][1]) - 6,
                   "現況地盤(暫定)" if sec.get("naturalProvisional") else "現況地盤(実測)", "jo"))

    # 石段(踏面/蹴上のギザギザ)。§3c「垂直な壁が並ぶだけの図は §1f を満たさない」
    # ⚠ 2026-08-23 是正: (1)踏面は m なのでグリッド(間)へ割る、(2)段は高い側から下る、
    #    (3)同じブロックが2度書かれていた、(4)判定半径が狭く K_Kuramon が断面Iに出なかった
    ken = d["const"]["ken"]
    for k in d["kaidans"]:
        if "pos" not in k:
            continue
        kp = k["pos"][1] if sec["axis"] == "u" else k["pos"][0]
        other = k["pos"][0] if sec["axis"] == "u" else k["pos"][1]
        if abs(other - at) > 7 or not (w0 <= kp <= w1):
            continue
        top = design_at(kp)
        if top is None:
            continue
        n_st = max(1, int(k["steps"]))
        rise = k["drop"] / n_st
        tread = k["run"] / n_st / ken                      # m → 間
        # 高い側へ向かって登る向きを決める(前後 1.5間 の設計面を見比べる)
        a_ = design_at(max(w0, kp - 1.5)); b_ = design_at(min(w1, kp + 1.5))
        sgn = 1.0 if (a_ is not None and b_ is not None and a_ >= b_) else -1.0
        pts = []
        for i in range(n_st + 1):
            pts.append((X(kp + sgn * tread * i), Y(top - rise * i)))
            pts.append((X(kp + sgn * tread * (i + 1)), Y(top - rise * i)))
        g.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="1.8"/>'
                 % " ".join("%.1f,%.1f" % q for q in pts))
        g.append(T(X(kp), Y(top) - 8, "%s %d段" % (k["name"], n_st), "sr", "middle"))

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
        hgt, bt = 4.0 * w["s"], 2.4 * w["s"]
        g.append(R(X(wp) - sx * bt / 2 / K, Y(w["coping"]), sx * bt / K, hgt * sx * ex,
                   fill=_pat(), stroke="var(--ishi)", sw=1.2))
        g.append(T(X(wp), Y(w["coping"]) - 5, "%s s=%.2f" % (w["name"], w["s"]), "jo", "middle"))

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
            fence = next((f for f in d.get("fences", []) if f["edge"] == be and f["s0"] - 0.5 <= bs <= f["s1"] + 0.5), None)
            if fence is not None:                     # 地形なりの木柵
                gy = ground_at(w)
                g.append(R(X(w) - sx * 0.4, Y(gy + FENCE_H), sx * 0.8, FENCE_H * sx * ex,
                           fill="var(--take)", op=0.9))
                g.append(T(X(w), Y(gy + FENCE_H) - 5, "%s(木柵)" % fence["name"], "jo", "middle"))
            continue                                  # 門の開口 or 柵の区間
        hh = 5.3 if run["kind"] == "Nagaya" else d["const"]["dobeiH"]
        gy = ground_at(w)
        if run["seat"] > gy + 0.05:                   # 基壇石垣
            g.append(R(X(w) - sx * 0.9, Y(run["seat"]), sx * 1.8, (run["seat"] - gy) * sx * ex,
                       fill=_pat(), stroke="var(--ishi)", sw=1.0))
        g.append(R(X(w) - sx * 0.7, Y(run["seat"] + hh), sx * 1.4, hh * sx * ex,
                   fill=KC.get(run["kind"], "var(--dim)"), op=0.95))
        g.append(T(X(w), Y(run["seat"] + hh) - 5, "%s %.1f" % (run["name"], run["seat"]), "jo", "middle"))

    # 表門(断面Aのみ)
    if sec["axis"] == "u" and abs(sec["at"]) < 2:
        gpn = d["gate"]["plan"]
        g.append(R(X(0) - sx * gpn["monD"] / 2 / K, Y(d["gate"]["sill"] + gpn["monH"]),
                   sx * gpn["monD"] / K * 2, gpn["monH"] * sx * ex,
                   fill="var(--shu-lo)", stroke="var(--shu)", sw=1.6))
        g.append(T(X(0), Y(d["gate"]["sill"] + gpn["monH"]) - 5, "表門", "anG", "middle"))

    # 端の囲い(polygon との交点に立つ run)
    g.append(T(4, 15, sec["_"].split("→")[0] + " →", "anS"))
    g.append(T(W - 4, 15, "→ " + sec["_"].split("→")[-1], "anS", "end"))
    g.append(T(4, H - 20, "水平は間グリッド沿い/垂直は %.1f 倍に強調。屋根は図示のための概略" % ex, "anS2", "start"))
    g.append(T(4, H - 6, "斜面(natural)は現地形のまま=造成しない区間", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其六 外周の展開
def perimeter_dev_svg(d):
    P = d["polygon"]
    n = len(P)
    elen = [math.hypot(P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1]) for i in range(n)]
    tv = [0.0]
    for i in range(n):
        tv.append(tv[-1] + elen[i])
    total = tv[-1]
    t0 = tv[d["gate"]["edge"]] + d["gate"]["s"]

    def tt(e, s):
        return (tv[e] + s - t0) % total

    W, ex = 1120.0, 6.5
    HEAD, FOOT = 34.0, 70.0
    sx = W / total
    dob = d["const"]["dobeiH"]
    nagH = 5.3
    seats = [r["seat"] for r in d["runs"]]
    prof = d.get("edgeProfiles") or {}
    gmin = min([y for arr in prof.values() for _, y in arr] or seats)
    y1 = max(seats) + nagH + 1.0
    y0 = min(min(seats), gmin) - 2.0
    H = (y1 - y0) * sx * ex + HEAD + FOOT

    def X(t): return t * sx
    def Y(y): return HEAD + (y1 - y) * sx * ex

    def gY(e, s):
        """辺 e の s[m] の地盤(edgeProfiles の内挿)。無ければ None。"""
        arr = prof.get(str(e))
        if not arr:
            return None
        if s <= arr[0][0]:
            return arr[0][1]
        for i in range(len(arr) - 1):
            (sa, ya), (sb, yb) = arr[i], arr[i + 1]
            if sa <= s <= sb:
                return ya + (yb - ya) * (s - sa) / max(1e-6, sb - sa)
        return arr[-1][1]

    g = _sv(W, H, "外周の展開図")
    lab = []
    for r in sorted(d["runs"], key=lambda r: tt(r["edge"], r["s0"])):
        ta = tt(r["edge"], r["s0"]); tb = tt(r["edge"], r["s1"])
        if tb < ta:
            tb += total
        xa, xb = X(ta), X(tb)
        h = nagH if r["kind"] == "Nagaya" else dob
        # 石垣基壇: seat から地盤まで(地盤が seat より上=埋まりは描かない)
        if prof:
            nsm = 8
            base = []
            for k in range(nsm + 1):
                s_ = r["s0"] + (r["s1"] - r["s0"]) * k / float(nsm)
                gy = gY(r["edge"], s_)
                t_ = tt(r["edge"], s_)
                if t_ < ta - 1e-6:
                    t_ += total
                base.append((X(t_), Y(min(gy, r["seat"])) if gy is not None else Y(r["seat"])))
            pts = "%.1f,%.1f " % (xa, Y(r["seat"])) + \
                  " ".join("%.1f,%.1f" % p for p in base) + \
                  " %.1f,%.1f" % (xb, Y(r["seat"]))
            g.append('<polygon points="%s" fill="var(--ishi)" opacity="0.45"/>' % pts)
        g.append(R(xa, Y(r["seat"] + h), xb - xa, h * sx * ex, fill=KC.get(r["kind"], "var(--dim)"), op=0.9))
        if r.get("nijukai"):
            w2 = min(20 * 1.818, r["s1"] - r["s0"]) * sx
            x2 = xa if ta < total / 2 else xb - w2      # 二階は門寄り(展開の起点=表門)
            g.append(R(x2, Y(r["seat"] + nagH + 2.6), w2, 2.6 * sx * ex,
                       fill=KC["Nagaya"], op=0.65))
            lab.append((x2, "門翼二階(海鼠壁)"))
        g.append(T((xa + xb) / 2, Y(r["seat"]) + 11, "%.1f" % r["seat"], "jo", "middle"))
        g.append(T((xa + xb) / 2, Y(r["seat"] + h) - 3, r["name"], "jo", "middle",
                   fit(r["name"], xb - xa, 9.0)))
    # 境界の木柵(地形なりの帯)
    for f in d.get("fences", []):
        ta = tt(f["edge"], f["s0"]); tb = tt(f["edge"], f["s1"])
        if tb < ta:
            tb += total
        nsm = 8
        top = []; bot = []
        for k in range(nsm + 1):
            s_ = f["s0"] + (f["s1"] - f["s0"]) * k / float(nsm)
            gy = gY(f["edge"], s_)
            if gy is None:
                gy = y0 + 2
            t_ = tt(f["edge"], s_)
            if t_ < ta - 1e-6:
                t_ += total
            top.append((X(t_), Y(gy + FENCE_H)))
            bot.append((X(t_), Y(gy)))
        pts = " ".join("%.1f,%.1f" % p for p in top) + " " + \
              " ".join("%.1f,%.1f" % p for p in reversed(bot))
        g.append('<polygon points="%s" fill="var(--take)" opacity="0.55"/>' % pts)
        g.append(T((X(ta) + X(min(tb, total + ta))) / 2, Y((gY(f["edge"], (f["s0"] + f["s1"]) / 2) or y0) + FENCE_H) - 4,
                   f["name"], "jo", "middle", fit(f["name"], X(tb) - X(ta), 9.0)))
    # 地盤線(区画線上の現地形・実測【P】)
    if prof:
        gpts = []
        for e in range(n):
            for s_, y_ in prof.get(str(e), []):
                gpts.append((tt(e, s_), y_))
        gpts.sort()
        g.append('<polyline points="%s" fill="none" stroke="var(--ink)" '
                 'stroke-width="1.1" opacity="0.75"/>'
                 % " ".join("%.1f,%.1f" % (X(t_), Y(y_)) for t_, y_ in gpts))
    # 門・櫓
    _gates = [("表門", d["gate"]["edge"], d["gate"]["s"], d["gate"]["plan"]["monW"] + 2 * d["gate"]["plan"]["sode"] + 2 * d["gate"]["plan"]["bansho"]["w"])]
    if d.get("onarimon"):
        _gates.append(("御成門", d["onarimon"]["edge"], d["onarimon"]["s"], d["onarimon"]["w"]))
    for name, e, s, wd in (_gates
                           + [(("御蔵門" if k["name"] == "Kuramon" else "小門"), k["edge"], k["s"], k["w"]) for k in d["komon"]]):
        t = tt(e, s)
        g.append(LN(X(t), Y(y1 - 0.5), X(t), Y(y0), "var(--shu)", 1.2, dash="5 3"))
        g.append(T(X(t), HEAD - 6, name, "sr", "middle"))
    for y in d["yagura"]:
        t = tt(y["vertex"], 0.0)
        g.append(R(X(t) - 5, Y(y["seat"] + 7.5), 10, 7.5 * sx * ex, fill="var(--shu)", op=0.85))
        g.append(T(X(t), Y(y["seat"] + 7.5) - 4, "隅櫓", "jo", "middle"))
    # 頂点の目盛
    for i in range(n):
        t = (tv[i] - t0) % total
        g.append(LN(X(t), Y(y0), X(t), Y(y0) + 5, "var(--dim)", 0.8))
        g.append(T(X(t), Y(y0) + 15, "P%d" % i, "jo", "middle"))
    g.append(T(4, H - 22, "展開の起点=表門。天端は run ごとに一定、段は継ぎ目で落とす。"
               "表長屋 桁高 %.1fm/練塀 %.2fm。細線=区画線上の現地形(実測【P】)、"
               "薄塗り=石垣基壇(天端と地盤の間)" % (nagH, dob), "anS2", "start"))
    g.append(T(4, H - 8, "北辺中央の鞍部(道23.4m)では表長屋の石垣基壇が道へ露出する。"
               "練塀の浅い折れは留め継ぎの隅部材で納める(角度は現地が決める)", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其七 表門まわり
def gate_svg(d):
    """写真(温古写真集11)から起こした正面の見付と平面。寸法は json の gate.plan。"""
    gp = d["gate"]["plan"]
    K = d["const"]["ken"]
    monW, monH = gp["monW"], gp["monH"]
    sod, bw, bd = gp["sode"], gp["bansho"]["w"], gp["bansho"]["d"]
    wing = 12.0                                   # 描画する長屋翼の長さ
    total = monW + 2 * sod + 2 * bw + 2 * wing
    W = 980.0
    sx = W / total
    GY = 300.0                                    # 地面の px
    H = 395.0

    def X(m): return m * sx
    def Y(m): return GY - m * sx                  # 高さ→px(等倍)

    g = _sv(W, H, "表門まわり 正面見付")
    x = 0.0
    # 左翼の長屋(海鼠壁・二階)
    g.append(R(X(x), Y(7.9), X(wing), (7.9 - 0) * sx, fill="var(--nagaya)", op=0.5))
    g.append(R(X(x), Y(7.9) - 10, X(wing) + 4, 10, fill="var(--ink-lo)"))
    for i in range(6):
        for j in range(3):
            g.append(LN(X(x + 1 + i * 1.8), Y(1.2 + j * 1.1), X(x + 1.9 + i * 1.8), Y(0.1 + j * 1.1), "var(--ink)", 0.5, op=0.5))
            g.append(LN(X(x + 1 + i * 1.8), Y(0.1 + j * 1.1), X(x + 1.9 + i * 1.8), Y(1.2 + j * 1.1), "var(--ink)", 0.5, op=0.5))
    g.append(T(X(x + wing / 2), Y(8.4), "表長屋(海鼠壁・二階)", "anS2", "middle"))
    x += wing
    # 番所(向唐破風・石垣畳出)
    for side in (0, 1):
        bx = x if side == 0 else total - wing - bw
        g.append(R(X(bx), Y(0.9), X(bw), 0.9 * sx, fill=_pat(), stroke="var(--ishi)", sw=1.0))
        g.append(R(X(bx + 0.3), Y(3.6), X(bw - 0.6), (3.6 - 0.9) * sx, fill="var(--dan)", stroke="var(--ink)", sw=1.1))
        for i in range(int((bw - 1.2) / 0.35)):
            xx = X(bx + 0.6 + i * 0.35)
            g.append(LN(xx, Y(3.3), xx, Y(1.3), "var(--ink)", 0.8, op=0.75))
        # 唐破風
        g.append('<path d="M %.1f %.1f C %.1f %.1f %.1f %.1f %.1f %.1f C %.1f %.1f %.1f %.1f %.1f %.1f Z" '
                 'fill="var(--ink-mid)" stroke="var(--ink)" stroke-width="1.2"/>'
                 % (X(bx - 0.4), Y(3.8), X(bx + bw * 0.25), Y(3.9), X(bx + bw * 0.32), Y(5.0),
                    X(bx + bw / 2), Y(5.05),
                    X(bx + bw * 0.68), Y(5.0), X(bx + bw * 0.75), Y(3.9), X(bx + bw + 0.4), Y(3.8)))
        g.append(T(X(bx + bw / 2), Y(5.3), "向唐破風の番所(出格子・石垣畳出)", "anS2", "middle") if side == 0 else "")
    x += bw
    # 袖塀(潜り戸)
    for side in (0, 1):
        sx0 = x if side == 0 else total - wing - bw - sod
        g.append(R(X(sx0), Y(3.2), X(sod), 3.2 * sx, fill="var(--hei)", op=0.75))
        if side == 0:
            g.append(R(X(sx0 + 0.5), Y(2.2), X(sod - 1.0), 2.2 * sx, fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
            g.append(T(X(sx0 + sod / 2), Y(3.6), "袖塀(潜り戸)", "anS2", "middle"))
    x += sod
    # 門柱・冠木・扉
    for px in (x, x + monW):
        g.append(R(X(px) - 5, Y(monH), 10, monH * sx, fill="var(--ink)", op=0.92))
        g.append(R(X(px) - 7, Y(monH) - 6, 14, 8, fill="var(--ink)"))
    g.append(R(X(x) - 5, Y(monH - 0.55), X(monW) + 10, 0.5 * sx, fill="var(--ink)", op=0.92))
    # 屋根なし冠木門が正(写真A+日本案内記A。切妻小屋根案は 2026-08-23 撤回)
    g.append(T(X(x + monW / 2), Y(monH) - 8,
               "冠木(屋根なし=写真A+日本案内記A)", "anS2", "middle"))
    g.append(R(X(x + 0.15), Y(3.6), X(monW / 2 - 0.3), 3.6 * sx, fill="var(--ink-lo)", stroke="var(--ink)", sw=1.0))
    g.append(R(X(x + monW / 2 + 0.15), Y(3.6), X(monW / 2 - 0.3), 3.6 * sx, fill="var(--ink-lo)", stroke="var(--ink)", sw=1.0))
    for i in range(3):
        g.append(LN(X(x + 0.3), Y(0.8 + i * 1.1), X(x + monW - 0.3), Y(0.8 + i * 1.1), "var(--ink)", 0.7, op=0.6))
    g.append(T(X(x + monW / 2), Y(1.9), "門扉(筋金具・乳鋲)", "anS2", "middle", 9.5))
    # 右翼の長屋
    g.append(R(X(total - wing), Y(7.9), X(wing), 7.9 * sx, fill="var(--nagaya)", op=0.5))
    g.append(R(X(total - wing) - 4, Y(7.9) - 10, X(wing) + 4, 10, fill="var(--ink-lo)"))
    for i in range(6):
        for j in range(3):
            bx = total - wing + 1 + i * 1.8
            g.append(LN(X(bx), Y(1.2 + j * 1.1), X(bx + 0.9), Y(0.1 + j * 1.1), "var(--ink)", 0.5, op=0.5))
            g.append(LN(X(bx), Y(0.1 + j * 1.1), X(bx + 0.9), Y(1.2 + j * 1.1), "var(--ink)", 0.5, op=0.5))
    g.append(LN(0, GY, W, GY, "var(--ink)", 1.6))
    g.append(T(4, GY + 16, "大通り(赤坂御門→永田馬場)。門の敷居=表郭の地盤", "anS2", "start"))
    g.append(T(4, 15, "正面見付(等倍)。江戸東京博物館 温古写真集11(88005761・明治初撮影)の実見から", "anS"))
    g.append("</svg>")

    # 平面
    W2, H2 = 980.0, 240.0
    s2 = W2 / total
    wy = 120.0
    g2 = _sv(W2, H2, "表門まわり 平面")

    def X2(m): return m * s2
    x = wing
    g2.append(R(0, wy - 8, X2(wing), 16, fill="var(--nagaya)", op=0.85))
    g2.append(R(X2(total - wing), wy - 8, X2(wing), 16, fill="var(--nagaya)", op=0.85))
    for side in (0, 1):
        bx = x if side == 0 else total - wing - bw
        g2.append(R(X2(bx), wy - 8 - s2 * gp["bansho"]["protrude"], X2(bw), s2 * (bd + gp["bansho"]["protrude"]) ,
                    fill="var(--dan)", stroke="var(--ink)", sw=1.2))
        g2.append(T(X2(bx + bw / 2), wy + 30, "番所(張出%.1fm)" % gp["bansho"]["protrude"], "anS2", "middle"))
    x += bw
    for side in (0, 1):
        sx0 = x if side == 0 else total - wing - bw - sod
        g2.append(R(X2(sx0), wy - 5, X2(sod), 10, fill="var(--hei)"))
    x += sod
    for px in (x, x + monW):
        g2.append(R(X2(px) - 4, wy - 4, 8, 8, fill="var(--ink)"))
    for sgn, px in ((1, x), (-1, x + monW)):
        g2.append('<path d="M %.1f %.1f A %.1f %.1f 0 0 %d %.1f %.1f" fill="none" stroke="var(--ink)" stroke-width="0.9" stroke-dasharray="3 3"/>'
                  % (X2(px), wy + 4, s2 * monW / 2, s2 * monW / 2, 0 if sgn > 0 else 1,
                     X2(px + sgn * monW / 2), wy + 4 + s2 * monW / 2))
    g2.append(T(X2(x + monW / 2), wy - 14, "門柱間 %.1fm" % monW, "anS2", "middle"))
    g2.append(LN(0, wy - 8, W2, wy - 8, "var(--dim)", 0.7, dash="3 4"))
    g2.append(T(4, wy - 14, "外周線(大通り側)", "jo"))
    g2.append(T(4, H2 - 8, "門構え全幅 約%.0fm。番所は外周線から街路側へ張り出し、袖塀が門柱と番所を繋ぐ。"
                "扉は内開き" % (monW + 2 * sod + 2 * bw), "anS2", "start"))
    g2.append("</svg>")
    return "\n".join(g) + "\n" + "\n".join(g2)


# ---------------------------------------------------------------- 表
def slope_table(d):
    if "slopeBands" not in d:
        return ""
    rows = []
    for b2 in d["slopeBands"]:
        rows.append("<tr><td>%s</td><td>法肩から %.0f〜%.0f%%</td><td class='note'>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (b2["name"], b2["from"] * 100, b2["to"] * 100, b2["veg"],
                       "<code>%s</code>" % b2["asset"]))
    return ("<h3>斜面の植生(3帯)</h3><div class='tw'><table><thead><tr><th>帯</th><th>範囲</th>"
            "<th class='note'>植生</th><th class='note'>部材</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>『江戸名所図会』「溜池」は<b>崖面をハッチング(草地・裸地)で描き、"
            "樹は稜線と法面上部に集まる</b> — 法面全体を樹林で埋めない。"
            "<b>竹は使わない</b>(竹薮は江戸の水辺79事例中1例の例外／孟宗竹は吹上御苑と"
            "近郊農村の筍畑にしか無い)。竹垣の材としての竹は別で、これは問題ない。</p>")


def planes_table(d):
    """面(planes)と縁の囲いの対応。造成も囲いもこの表から決まる。"""
    rows = []
    for p in d.get("planes", []):
        chip = ('<span style="display:inline-block;width:11px;height:11px;background:%s;'
                'border:1px solid var(--rule);margin-right:6px"></span>' % PLANE_COL.get(p["name"], "transparent")) \
               if p["name"] in PLANE_COL else ""
        rows.append("<tr><td>%s%s</td><td>%s</td><td class='note'>%s</td><td class='note'>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (chip, p["name"], ("%.1f m" % p["y"]) if p["y"] is not None else "地形なり",
                       "・".join(TERR_JA.get(t, t) for t in p["terraces"]) or "—",
                       "・".join("<code>%s</code>" % r for r in p["runs"]),
                       p.get("note", "")))
    return ("<h3>面と縁の対応</h3><div class='tw'><table><thead><tr><th>面</th><th>高さ</th>"
            "<th class='note'>段(造成)</th><th class='note'>縁の囲い(天端=面の高さ)</th>"
            "<th class='note'>注記</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def munes_table(d):
    rows = []
    K = d["const"]["ken"]
    for m in d["munes"]:
        kw, kd = abs(m["u1"] - m["u0"]), abs(m["v1"] - m["v0"])
        area = kw * kd * K * K
        tat = sum(r["tatami"] for r in m["rooms"])
        rows.append("<tr><td>%s</td><td><code>%s</code></td><td>%s</td><td>%d×%d間</td>"
                    "<td>%.0f m²</td><td>%d</td><td>%d</td></tr>"
                    % (MUNE_JA.get(m["name"], m["name"]), m["name"], m["zone"], kw, kd,
                       area, len(m["rooms"]), tat))
    return ('<div class="tw"><table><thead><tr><th>棟</th><th>名</th><th>ゾーン</th><th>外形</th>'
            "<th>面積</th><th>室数</th><th>畳数計</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def links_table(d):
    rows = []
    for l in d["links"]:
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td>(%g,%g)-(%g,%g)</td></tr>"
                    % (l["name"], l["kind"], l["u0"], l["v0"], l["u1"], l["v1"]))
    return ('<div class="tw"><table><thead><tr><th>廊下</th><th>種別</th><th>グリッド</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def runs_table(d):
    rows = []
    for r in d["runs"]:
        rows.append("<tr><td><code>%s</code></td><td>辺%d</td><td>%.0f–%.0f</td><td>%.1fm</td>"
                    "<td>%s</td><td>%.1f</td><td>%s</td><td>%s</td></tr>"
                    % (r["name"], r["edge"], r["s0"], r["s1"], r["s1"] - r["s0"],
                       "表長屋" if r["kind"] == "Nagaya" else "練塀", r["seat"],
                       "石垣" if r.get("base") else "—",
                       "整地" if r.get("bench") else "—"))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>辺</th><th>走り s</th><th>長さ</th>'
            "<th>種別</th><th>天端 seat</th><th>基壇</th><th>外周帯</th></tr></thead><tbody>"
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
    ban = 2 * d["gate"]["plan"]["bansho"]["w"] * d["gate"]["plan"]["bansho"]["d"]
    yag = sum((y["ken"] * K) ** 2 for y in d["yagura"])
    gp = d["gate"]["plan"]
    mon = gp["monW"] * gp["monD"] + 2 * gp["sode"] * 0.4 \
        + (d["onarimon"]["w"] * 1.5 if d.get("onarimon") else 0) + sum(k["w"] * 1.2 for k in d["komon"])
    tot = gm + gl + gs + nag + ban + yag + mon
    return ('<div class="tw"><table><thead><tr><th></th><th>m²</th><th>坪</th></tr></thead><tbody>'
            "<tr><td>御殿の棟(入側とも)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>渡廊下・御錠口</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>付属屋(蔵・作事・茶屋・稲荷)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>表長屋(奥行%.1fm)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>番所・隅櫓・門の躯体</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td><b>計</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            "<tr><td><b>敷地(分母)</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            '<tr><td><b>建蔽率</b></td><td colspan="2"><b>%.1f%%</b></td></tr>'
            "</tbody></table></div>"
            % (gm, gm / TSUBO, gl, gl / TSUBO, gs, gs / TSUBO, d["const"]["nagayaD"],
               nag, nag / TSUBO, ban + yag + mon, (ban + yag + mon) / TSUBO,
               tot, tot / TSUBO, area, area / TSUBO, 100.0 * tot / area)), 100.0 * tot / area


def plane_check(d):
    """面のはみ出し検査。棟・付属屋・廊下が「自分の y の面の段」の中に完全に載っているか、
    0.5間刻みの被覆で機械検査する。庭は y を持たないので全段の合併で見る(slope=true は
    造成しない斜面に載る設計なので除外)。"""
    ters = d["terraces"]
    eps = 1e-6
    G = RGrid(d)
    P = d["polygon"]

    def inpoly(x, z):
        c = False
        for i in range(len(P)):
            x1, z1 = P[i]
            x2, z2 = P[i - 1]
            if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
                c = not c
        return c

    def covered(u0, v0, u1, v1, y):
        uu = u0 + 0.25
        while uu < u1:
            vv = v0 + 0.25
            while vv < v1:
                ok = inpoly(*G.W(uu, vv)) and any(
                    t["u0"] - eps <= uu <= t["u1"] + eps and
                    t["v0"] - eps <= vv <= t["v1"] + eps and
                    (y is None or abs(t["y"] - y) < 0.01) for t in ters)
                if not ok:
                    return (uu, vv)
                vv += 0.5
            uu += 0.5
        return None

    bad = []
    for m in d["munes"] + d["service"]:
        pt = covered(m["u0"], m["v0"], m["u1"], m["v1"], m["y"])
        if pt:
            bad.append("%s (y=%.1f) が面の外: グリッド(%.2f, %.2f)"
                       % (m.get("name", m.get("label")), m["y"], pt[0], pt[1]))
    for l in d["links"]:
        pt = covered(l["u0"], l["v0"], l["u1"], l["v1"], l["y"])
        if pt:
            bad.append("%s (y=%.1f) が面の外: (%.2f, %.2f)" % (l["name"], l["y"], pt[0], pt[1]))
    for g in d["gardens"]:
        if g.get("slope"):
            continue
        pt = covered(g["u0"], g["v0"], g["u1"], g["v1"], None)
        if pt:
            bad.append("%s(庭) が段の外: (%.2f, %.2f)" % (g["name"], pt[0], pt[1]))
    for w in d["wells"]:
        pt = covered(w["u"] - 0.5, w["v"] - 0.5, w["u"] + 0.5, w["v"] + 0.5, None)
        if pt:
            bad.append("%s(井戸) が段の外: (%.2f, %.2f)" % (w["name"], pt[0], pt[1]))
    bad += run_seat_check(d)
    bad += route_pierce_check(d)
    bad += room_containment_check(d)
    bad += barrier_check(d)
    bad += kaidan_ground_check(d)
    bad += hardcode_check()
    bad += gate_overlap_check(d)
    return bad


def route_pierce_check(d, tol=1.0):
    """**動線が室の中を通っていないかの検査。**入側(外形から一間の帯)・渡廊下・棟間は通路なので許す。
    起終点の棟と、座敷の順路(供之間→次之間→上段のように室を継いで進む所)は allow に列挙する。
    2026-08-23 検図: 勝手が御土蔵一を10.3m貫通し、奥向が長局を室の中で22.7m縦断していた。"""
    allow = {("R_Omote", "Ohiroma"), ("R_Yaku", "Yakusho"),
             ("R_Katte", "Daidokoro"), ("R_Oku", "Nakaoku")}
    K = d["const"]["ken"]
    agg = {}
    for r in d.get("routes", []):
        for i in range(len(r["pts"]) - 1):
            a, b = r["pts"][i], r["pts"][i + 1]
            seg = math.hypot(b[0] - a[0], b[1] - a[1]) * K
            if seg < 1e-6:
                continue
            for m in d["munes"] + d["service"]:
                iu0, iv0 = m["u0"] + 1, m["v0"] + 1
                iu1, iv1 = m["u1"] - 1, m["v1"] - 1
                if iu1 <= iu0 or iv1 <= iv0:
                    continue
                N, L = 200, 0.0
                for k in range(N):
                    t = (k + 0.5) / N
                    mx = a[0] + (b[0] - a[0]) * t
                    my = a[1] + (b[1] - a[1]) * t
                    if iu0 <= mx <= iu1 and iv0 <= my <= iv1:
                        L += seg / N
                if L > 0:
                    agg[(r["name"], m["name"])] = agg.get((r["name"], m["name"]), 0.0) + L
    return ["%s が %s の室内を %.1fm 通る(入側・渡廊下に載せ直す)" % (rn, mn, L)
            for (rn, mn), L in sorted(agg.items(), key=lambda x: -x[1])
            if L > tol and (rn, mn) not in allow]


def run_seat_check(d, tol=0.6):
    """**run の天端と背後の地盤の照合。**これが無いと「塀が埋まる/浮く」を図で見逃す
    (2026-08-23 検図: 北東で 2.26m 埋没・南東で 3.74m 浮きを見逃していた)。
    地盤は matsudaira_terrain.json(造成前)から読む。埋没(地盤>天端)は即不可、
    浮きは石垣基壇 4.0×s で受けられる範囲まで許す。"""
    try:
        terr = json.load(open(os.path.join(DOC, "matsudaira_terrain.json"), encoding="utf-8"))
    except Exception:
        return []
    gr = RGrid(d)
    P = d["polygon"]
    n = len(P)
    out = []
    for r in d["runs"]:
        e = r["edge"]
        a, b = P[e % n], P[(e + 1) % n]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz)
        ux, uz = dx / L, dz / L
        nx, nz = -uz, ux
        cx = sum(q[0] for q in P) / n
        cz = sum(q[1] for q in P) / n
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (cx - mx) * nx + (cz - mz) * nz < 0:
            nx, nz = -nx, -nz                       # 内向き
        worstB = worstF = 0.0
        steps = max(2, int((r["s1"] - r["s0"]) / 3))
        # 斜面の run は天端が一直線に下る(seat0→seat1)。単一 seat で見ると全長を誤判定する
        y0 = r.get("seat0", r["seat"]); y1 = r.get("seat1", r["seat"])
        for i in range(steps + 1):
            sv = r["s0"] + (r["s1"] - r["s0"]) * i / steps
            top = y0 + (y1 - y0) * (sv - r["s0"]) / max(1e-9, r["s1"] - r["s0"])
            for off in (1.5, 3.0, 4.5):
                wx = a[0] + ux * sv + nx * off
                wz = a[1] + uz * sv + nz * off
                g = gr.L(wx, wz)
                h = _nat_uv(terr, round(g[0]), round(g[1]))
                if h is None:
                    continue
                worstB = max(worstB, h - top)   # 埋まる
                worstF = max(worstF, top - h)   # 浮く
        cap = 4.0 * r.get("s", 0.0) + 0.3
        if worstB > tol:
            out.append("%s(天端%.1f→%.1f) の背後の地盤が %.2fm 高い = 塀が埋まる" % (r["name"], y0, y1, worstB))
        elif r.get("base") == "Ishigaki" and worstF > cap:
            out.append("%s(天端%.1f→%.1f) が %.2fm 浮くが石垣基壇は %.2fm しか無い(s=%.2f)"
                       % (r["name"], y0, y1, worstF, cap, r.get("s", 0.0)))
        elif r.get("base") != "Ishigaki" and worstF > tol:
            out.append("%s(天端%.1f) が %.2fm 浮くのに石垣基壇が無い" % (r["name"], r["seat"], worstF))
    return out


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
                if k1 == "niwa" and k2 == "niwa":
                    # 庭の中の池・中島・築山は、親の庭に**完全に包含**されていれば可
                    if (a0 <= c0 and b0 <= d0 and c1 <= a1 and d1 <= b1) or \
                       (c0 <= a0 and d0 <= b0 and a1 <= c1 and b1 <= d1):
                        continue
                if {k1, k2} == {"niwa", "svc"}:
                    # 庭の中に立つ亭・祠は庭に**完全に包含**されていれば可(庭は地面)
                    (nk, na, n0, n1_, n2_, n3), (sk, sa, s0, s1_, s2_, s3) = \
                        (boxes[i], boxes[j]) if k1 == "niwa" else (boxes[j], boxes[i])
                    if n0 <= s0 and n1_ <= s1_ and s2_ <= n2_ and s3 <= n3:
                        continue
                bad.append("%s %s × %s %s (%.1f×%.1f間)" % (k1, n1, k2, n2, iu, iv))
    return bad


def room_containment_check(d):
    """室は棟の外形の中にある。棟を動かして室を置き去りにすると、
    室名だけが旧位置(=庭の中など)に残る。2026-08-23 にユーザー指摘で発覚し追加。"""
    bad = []
    for m in d["munes"]:
        for r in m.get("rooms", []):
            if not (m["u0"] <= r["u0"] and r["u1"] <= m["u1"]
                    and m["v0"] <= r["v0"] and r["v1"] <= m["v1"]):
                bad.append("室 %s(%s)が棟の外形の外 u[%g,%g] v[%g,%g]"
                           % (r["name"], m["name"], r["u0"], r["u1"], r["v0"], r["v1"]))
        # 身舎(外形から入側一間を除いた内側)に収まるか
        for r in m.get("rooms", []):
            if (r["u0"] < m["u0"] + 1 or r["u1"] > m["u1"] - 1
                    or r["v0"] < m["v0"] + 1 or r["v1"] > m["v1"] - 1):
                bad.append("室 %s(%s)が入側の帯に食い込む" % (r["name"], m["name"]))
    return bad


def section_crossings(d, sec):
    """断面が実際に切るものを算出する。**手で書いた交差リストは持たない** —
    棟を動かすたびに腐り、2026-08-23 に8本中6本が旧配置のままだった。"""
    ax, at = sec["axis"], sec["at"]
    hit = []
    def add(nm, a, b, c, e):
        if ax == "u":
            if a <= at <= c:
                hit.append((b, e, nm))
        else:
            if b <= at <= e:
                hit.append((a, c, nm))
    for m in d["munes"]:
        add(MUNE_JA.get(m["name"], m["name"]), m["u0"], m["v0"], m["u1"], m["v1"])
    for x in d["service"]:
        add(x.get("label", x["name"]), x["u0"], x["v0"], x["u1"], x["v1"])
    for x in d["gardens"]:
        add(x.get("label", x["name"]), x["u0"], x["v0"], x["u1"], x["v1"])
    hit.sort()
    return [h[2] for h in hit]


def barrier_check(d):
    """御錠口の結界。**廊下だけでなく「面として閉じているか」を見る。**
    2026-08-23 検図: 旧版は links しか見ておらず、結界線の帯が16間開いていても合格を出していた
    (西庭を南へ回れば奥御殿の西を素通りできた)。被覆検査を足す。"""
    zone = {m["name"]: m["zone"] for m in d["munes"]}
    bad = []
    for l in d["links"]:
        z = set()
        for m in d["munes"]:
            if (m["u0"] - 1 <= l["u1"] and l["u0"] <= m["u1"] + 1
                    and m["v0"] - 1 <= l["v1"] and l["v0"] <= m["v1"] + 1):
                z.add(zone.get(m["name"], "?"))
        if "奥向" in z and len(z) > 1 and "口" not in l["kind"]:
            bad.append("%s(%s)が %s を跨ぐのに口でない — 御錠口の結界が無効"
                       % (l["name"], l["kind"], "/".join(sorted(z))))

    # ---- 面としての被覆。奥向ゾーンの外周が、棟・中仕切塀・口 のいずれかで閉じているか
    oku = [m for m in d["munes"] if m.get("zone") == "奥向"]
    if not oku:
        return bad
    ou0 = min(m["u0"] for m in oku); ou1 = max(m["u1"] for m in oku)
    ov0 = min(m["v0"] for m in oku); ov1 = max(m["v1"] for m in oku)
    segs = []                                        # 結界線 v=ov0-0.5 上で塞がっている区間
    line = ov0 - 0.5
    for m in d["munes"]:
        if m["v0"] <= line <= m["v1"]:
            segs.append((m["u0"], m["u1"]))
    for l in d["links"]:
        if l["v0"] <= line <= l["v1"]:
            segs.append((l["u0"], l["u1"]))
    for w in d.get("nakajikiri", []):
        (a0, b0), (a1, b1) = w["a"], w["b"]
        if min(b0, b1) <= line <= max(b0, b1):
            segs.append((min(a0, a1), max(a0, a1)))
    segs.sort()
    cov, cur = [], None
    for a, b in segs:
        if cur is None or a > cur[1] + 1e-9:
            if cur: cov.append(cur)
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur:
        cov.append(cur)
    # 閉じるべき範囲は、奥向の棟が載る段の u 範囲(区画の外まで塀を伸ばす必要は無い)
    lo, hi = ou0, ou1
    for t in d["terraces"]:
        if any(t["u0"] <= m["u0"] and m["u1"] <= t["u1"]
               and t["v0"] <= m["v0"] and m["v1"] <= t["v1"] for m in oku):
            lo = min(lo, t["u0"]); hi = max(hi, t["u1"])
    gaps, x = [], lo
    for a, b in cov:
        if a > x + 1e-9:
            gaps.append((x, a))
        x = max(x, b)
    if x < hi:
        gaps.append((x, hi))
    big = [gp for gp in gaps if gp[1] - gp[0] > 1.0]
    if big:
        bad.append("奥向の結界線 v=%.1f が %d 箇所で開いている(最大 %.1f 間) — "
                   "面として閉じていないと錠は効かない"
                   % (line, len(big), max(gp[1] - gp[0] for gp in big)))
    return bad


def gate_overlap_check(d):
    """run が門の組立(番所・袖塀・門柱)と重なっていないか。
    2026-08-24: N_Nagaya_E1 が東番所と 5.5m 重なり、実装は開口で割るので
    **run に部材が一つも入らない**状態だった。矩形の重なり検査は門の組立を持たないので気づけない。"""
    bad = []
    spans = []
    g = d.get("gate")
    if g and "plan" in g and "sPos" in g["plan"]:
        for k, v in g["plan"]["sPos"].items():
            spans.append((int(g["edge"]), float(v[0]), float(v[1]), "表門の" + k))
    for k in d.get("komon", []):
        spans.append((int(k["edge"]), k["s"] - k["w"] / 2.0, k["s"] + k["w"] / 2.0, k.get("name", "小門")))
    for r in d["runs"]:
        for e, a, b, nm in spans:
            if r["edge"] != e:
                continue
            ov = min(r["s1"], b) - max(r["s0"], a)
            if ov > 0.05:
                bad.append("%s が %s(s%.1f〜%.1f)と %.1fm 重なる — 実装は開口で割るので部材が入らない"
                           % (r["name"], nm, a, b, ov))
    return bad


def kaidan_ground_check(d):
    """石段の落差が、その位置の造成前地盤と面の差に合っているか。
    2026-08-23: 御蔵門の石段が『存在しない帯』の上に置かれ、降りた先が窪地になっていた。"""
    try:
        terr = json.load(open(os.path.join(DOC, "matsudaira_terrain.json"), encoding="utf-8"))
    except Exception:
        return []
    bad = []
    for k in d["kaidans"]:
        if "pos" not in k:
            continue
        ku, kv = k["pos"]
        nat = _nat_uv(terr, ku, kv)
        if nat is None:
            continue
        pl = None
        for t in d["terraces"]:
            if t["u0"] <= ku <= t["u1"] and t["v0"] <= kv <= t["v1"]:
                pl = t["y"]
                break
        if pl is None:
            bad.append("石段 %s (%g,%g) がどの段の上にも無い" % (k["name"], ku, kv))
            continue
        want = abs(nat - pl)
        if abs(want - k["drop"]) > 0.6:
            bad.append("石段 %s: 設計の落差 %.2fm に対し、その位置の地盤 %.2f と面 %.2f の差は %.2fm"
                       % (k["name"], k["drop"], nat, pl, want))
    return bad


def hardcode_check():
    """生成器の legend/caption に数値が直書きされていないか(正典は json)。"""
    import io, re as _re
    src = io.open(__file__, encoding="utf-8").read()
    bad = []
    # 凡例の色見出しに標高が直書きされている形だけを拾う(散文の数値は対象外)
    for m in _re.finditer(r'■\s*[^<">\n%]{1,12}?\s(\d{2}\.\d)', src):
        bad.append("生成器の凡例に直書きの標高: %s" % m.group(0).strip())
    return bad


# ---------------------------------------------------------------- 其十 取り合い(実装用・自動算出)
def _edge_dir(P, e):
    a, b = P[e], P[(e + 1) % len(P)]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / L, (b[1] - a[1]) / L, L)


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
        else:
            osame = "塀を長屋の妻へ突き付け"
        ds = (rr["seat"] - rl["seat"]) if (rl and rr) else 0.0
        rows.append("<tr><td>P%d</td><td>(%.1f, %.1f)</td><td>%.1f°</td>"
                    "<td><code>%s</code> %.1f</td><td><code>%s</code> %.1f</td><td>%+.1f</td><td class='note'>%s</td></tr>"
                    % (i, P[i][0], P[i][1], delta,
                       rl["name"] if rl else "—", rl["seat"] if rl else 0,
                       rr["name"] if rr else "—", rr["seat"] if rr else 0,
                       ds, osame))
    return ("<h3>隅(区画の頂点)</h3><div class='tw'><table><thead><tr><th>頂点</th><th>世界座標 (x,z)</th>"
            "<th>折れ角Δ</th><th>手前の run・天端</th><th>先の run・天端</th><th>Δ天端</th><th class='note'>納め</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def joints_table(d):
    """辺の中の継ぎ目(run と run・run と開口)。s と世界座標、天端差。"""
    P = d["polygon"]
    ops = [("表門", d["gate"]["edge"],
            d["gate"]["s"] - d["gate"]["plan"]["monW"] / 2 - d["gate"]["plan"]["sode"] - d["gate"]["plan"]["bansho"]["w"],
            d["gate"]["s"] + d["gate"]["plan"]["monW"] / 2 + d["gate"]["plan"]["sode"] + d["gate"]["plan"]["bansho"]["w"])]
    if d.get("onarimon"):
        ops.append(("御成門", d["onarimon"]["edge"], d["onarimon"]["s"] - d["onarimon"]["w"] / 2,
                    d["onarimon"]["s"] + d["onarimon"]["w"] / 2))
    for k in d["komon"]:
        nm = "御蔵門" if k["name"] == "Kuramon" else "小門"
        ops.append((nm, k["edge"], k["s"] - k["w"] / 2, k["s"] + k["w"] / 2))
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
                               a["seat"], b["seat"], b["seat"] - a["seat"], abs(b["seat"] - a["seat"])))
            else:
                op = next((o for o in ops if o[1] == e and o[2] > a["s1"] - 1 and o[3] < b["s0"] + 1), None)
                wa = edge_pt(P, e, a["s1"]); wb = edge_pt(P, e, b["s0"])
                rows.append("<tr><td>辺%d s=%.1f–%.1f</td><td>(%.1f, %.1f)–(%.1f, %.1f)</td>"
                            "<td><code>%s</code> ⋯ <code>%s</code></td><td>%.1f ⋯ %.1f</td>"
                            "<td class='note'>開口 %.1fm%s。囲いの端部は門の袖・番所へ突き付け</td></tr>"
                            % (e, a["s1"], b["s0"], wa[0], wa[1], wb[0], wb[1],
                               a["name"], b["name"], a["seat"], b["seat"], gap,
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
        _ws = [x for x in d["terraceWalls"] if x["name"] == k.get("atWall")]
        if not _ws:
            continue          # 土留めの無い段(0.3m など)は石段だけ
        w = _ws[0]
        if w["a"][0] == w["b"][0]:
            c = gr.W(w["a"][0], k["gapV"])
        else:
            c = gr.W(k["gapU"], w["a"][1])
        rows.append("<tr><td><code>%s</code></td><td>石段 %d段(幅 %.2fm)</td>"
                    "<td>芯 (%.1f, %.1f)</td><td>落差 %.1f・走り %.2fm</td></tr>"
                    % (k["name"], k["steps"], k["w"], c[0], c[1], k["drop"], k["run"]))
    for rl in d["rails"]:
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        rows.append("<tr><td><code>%s</code></td><td>竹垣(四つ目垣 h0.9)</td>"
                    "<td class='note'>%s</td><td>法肩から内へ 0.45m</td></tr>"
                    % (rl["name"], " → ".join("(%.1f, %.1f)" % p for p in pts)))
    return ("<h3>郭内の土木の端点</h3><div class='tw'><table><thead><tr><th>名</th><th>種別</th>"
            "<th>世界座標</th><th>寸法</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def mune_contacts_table(d):
    """棟どうし・棟と廊下の共有辺。取り付く面と長さを設計値から導く。"""
    gr = RGrid(d)
    boxes = [(m["name"], m["u0"], m["v0"], m["u1"], m["v1"], "棟") for m in d["munes"]] + \
            [(l["name"], l["u0"], l["v0"], l["u1"], l["v1"], l["kind"]) for l in d["links"]]
    rows = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, a0, b0, a1, b1, k1 = boxes[i]
            n2, c0, d0, c1, d1, k2 = boxes[j]
            if k1 != "棟" and k2 != "棟":
                continue
            # 縦辺の共有
            seg = None
            if abs(a1 - c0) < 1e-9 or abs(a0 - c1) < 1e-9:
                u = a1 if abs(a1 - c0) < 1e-9 else a0
                lo, hi = max(b0, d0), min(b1, d1)
                if hi - lo > 1e-9:
                    seg = ((u, lo), (u, hi), hi - lo)
            if seg is None and (abs(b1 - d0) < 1e-9 or abs(b0 - d1) < 1e-9):
                v = b1 if abs(b1 - d0) < 1e-9 else b0
                lo, hi = max(a0, c0), min(a1, c1)
                if hi - lo > 1e-9:
                    seg = ((lo, v), (hi, v), hi - lo)
            if seg is None and (k1 != "棟" or k2 != "棟"):
                # 渡廊下は棟の外形(入側帯)へ一間乗り込む取り付きも拾う
                iu = min(a1, c1) - max(a0, c0)
                iv = min(b1, d1) - max(b0, d0)
                if iu > 1e-9 and iv > 1e-9 and min(iu, iv) <= 1.0 + 1e-9:
                    seg = ((max(a0, c0), max(b0, d0)), (min(a1, c1), min(b1, d1)), max(iu, iv))
            if seg is None:
                continue
            wa, wb = gr.W(*seg[0]), gr.W(*seg[1])
            nm1 = MUNE_JA.get(n1, n1); nm2 = MUNE_JA.get(n2, n2)
            rows.append("<tr><td>%s ↔ %s</td><td>%s</td><td>%.1f間 (%.2fm)</td>"
                        "<td>(%.1f, %.1f) – (%.1f, %.1f)</td></tr>"
                        % (nm1, nm2, "接続(共有辺)" if (k1 == "棟" and k2 == "棟") else k2 if k1 == "棟" else k1,
                           seg[2], seg[2] * d["const"]["ken"], wa[0], wa[1], wb[0], wb[1]))
    return ("<h3>棟の取り合い(共有辺・取り付き)</h3><div class='tw'><table><thead><tr><th>組</th><th>種別</th>"
            "<th>長さ</th><th>世界座標(共有区間)</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def gate_parts_table(d):
    """門構えの部材位置。辺の向きから各部材の芯の世界座標と yaw を導く。"""
    P = d["polygon"]
    g = d["gate"]; gp = g["plan"]
    dx, dz, _ = _edge_dir(P, g["edge"])
    yaw = g["yaw"]
    rows = []

    def at(s_off, out_off=0.0):
        # out_off: 外周線から街路側(外向き)+
        x, z = edge_pt(P, g["edge"], g["s"] + s_off)
        ox, oz = dz, -dx                       # 外向き法線(北辺では街路側)
        if (ox * (P[6][0] - x) + oz * (P[6][1] - z)) > 0:   # P6=敷地の南端で内外判定
            ox, oz = -ox, -oz
        return (x + ox * out_off, z + oz * out_off)

    half = gp["monW"] / 2
    for nm, s_off, out in [("門柱(西)", -half, 0.0), ("門柱(東)", half, 0.0),
                           ("袖塀(西)", -(half + gp["sode"] / 2), 0.0),
                           ("袖塀(東)", half + gp["sode"] / 2, 0.0),
                           ("番所(西)", -(half + gp["sode"] + gp["bansho"]["w"] / 2),
                            gp["bansho"]["protrude"] / 2),
                           ("番所(東)", half + gp["sode"] + gp["bansho"]["w"] / 2,
                            gp["bansho"]["protrude"] / 2)]:
        x, z = at(s_off, out)
        rows.append("<tr><td>%s</td><td>(%.2f, %.2f)</td><td>%.2f</td><td>%.1f</td></tr>"
                    % (nm, x, z, g["sill"], yaw))
    om = d.get("onarimon")
    if om:
        x, z = edge_pt(P, om["edge"], om["s"])
        rows.append("<tr><td>御成門(芯)</td><td>(%.2f, %.2f)</td><td>%.2f</td><td>%.1f</td></tr>"
                    % (x, z, om["sill"], yaw))
    for k in d["komon"]:
        x, z = edge_pt(P, k["edge"], k["s"])
        ddx, ddz, _ = _edge_dir(P, k["edge"])
        kyaw = (math.degrees(math.atan2(ddz, -ddx))) % 360
        rows.append("<tr><td>%s(芯)</td><td>(%.2f, %.2f)</td><td>%.2f</td><td>%.1f</td></tr>"
                    % ("御蔵門" if k["name"] == "Kuramon" else "東小門", x, z, k["sill"], kyaw))
    return ("<h3>門構えの部材位置</h3><div class='tw'><table><thead><tr><th>部材</th><th>芯の世界座標 (x,z)</th>"
            "<th>敷居</th><th>yaw</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>番所は外周線から街路側へ張出の半分だけ前に出た位置が芯。"
            "袖塀は門柱と番所のあいだを繋ぐ。すべて表門と同じ yaw(辺の向き)。</p>")


def bom_table(d):
    if "bom" not in d:
        return ""
    rows = []
    for b in d["bom"]:
        stock = b.get("asset", "")
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (b["item"], "<b>新造(Blender)</b>" if b.get("build") else "在庫",
                       ("<code>%s</code>" % stock) if stock else "—", b.get("note", "")))
    return ('<div class="tw"><table><thead><tr><th>部材</th><th>調達</th><th class="note">在庫パス/新造名</th>'
            "<th class='note'>備考</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def history():
    try:
        log = subprocess.check_output(
            ["git", "-C", ROOT, "log", "--date=short",
             "--pretty=%h|%ad|%s", "--", "docs/Sashizu/matsudaira_sashizu.json",
             "docs/Sashizu/matsudaira_kosho.md"]).decode()
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
    h.append('<div class="plate"><div class="phead"><h2>%s　%s</h2>%s</div>'
             % (num, title, ('<span class="meta">%s</span>' % meta) if meta else ""))


def _daylights(cp, g, yT, nat_at, feather=2.0, cap=12.0, ken=1.818):
    """段の縁 cp から g の向きへ 1:feather の法面を cap[m] 延ばして現地形に着地するか。
    着地しない縁は崖(石垣で受けるべき所)— 無理に法面を張ると宙に土手が伸びる。
    断面では現況が断面線上しか分からないので、着地の判定も断面線上で行う。"""
    du, dv = g[0] - cp[0], g[1] - cp[1]
    L = math.hypot(du, dv)
    if L < 1e-9:
        return True
    # 断面線に沿った位置に読み替えて現況を引く
    probe = None
    if abs(dv) >= abs(du):
        probe = cp[1] + (cap / ken) * (1 if dv > 0 else -1)
    else:
        probe = cp[0] + (cap / ken) * (1 if du > 0 else -1)
    nz = nat_at(probe)
    if nz is None:
        return True
    return yT - cap / max(0.5, feather) <= nz


def cutfill_table(d, sec):
    """断面線に沿った 切土/盛土/造成しない/未実測 の内訳。section_svg と同じ判定を使う。"""
    K = d["const"]["ken"]
    at, w0, w1 = sec["at"], sec["from"], sec["to"]
    segs = []
    for t in d["terraces"]:
        cov = (t["u0"] <= at <= t["u1"]) if sec["axis"] == "u" else (t["v0"] <= at <= t["v1"])
        if not cov:
            continue
        a, b = (t["v0"], t["v1"]) if sec["axis"] == "u" else (t["u0"], t["u1"])
        a, b = max(a, w0), min(b, w1)
        if b > a:
            segs.append((a, b, t["y"]))
    nat = sorted([(p[0], p[1]) for p in sec.get("natural", [])])

    def nat_at(w):
        if not nat or w < nat[0][0] - 1e-6 or w > nat[-1][0] + 1e-6:
            return None
        for i in range(len(nat) - 1):
            a, ya = nat[i]
            b, yb = nat[i + 1]
            if a <= w <= b:
                return ya if b <= a else ya + (yb - ya) * (w - a) / (b - a)
        return nat[-1][1]

    BFILL = d["const"].get("batterFill", 1.5)
    BCUT = d["const"].get("batterCut", 1.0)
    WALLNEAR = d["const"].get("wallNear", 0.6)
    CAP = d["const"].get("featherCap", 12.0)

    def _dseg(p, a, b):
        (px, py), (ax, ay), (bx, by) = p, a, b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        return math.hypot(px - (ax + dx * t), py - (ay + dy * t))

    def design_at(w):
        """section_svg / 実装の DesignY と同じ規則(段 → 土留めの有無 → 法面)。"""
        for a, b, y in segs:
            if a - 1e-6 <= w <= b + 1e-6:
                return y
        nz = nat_at(w)
        if nz is None:
            return None
        g = (at, w) if sec["axis"] == "u" else (w, at)
        dT, yT, cp = 1e9, None, None
        for t in d["terraces"]:
            cu = max(t["u0"], min(g[0], t["u1"]))
            cv = max(t["v0"], min(g[1], t["v1"]))
            dd = math.hypot(g[0] - cu, g[1] - cv) * K
            if dd < dT:
                dT, yT, cp = dd, t["y"], (cu, cv)
        if yT is None:
            return nz
        for wl in d["terraceWalls"]:
            if _dseg(cp, tuple(wl["a"]), tuple(wl["b"])) <= WALLNEAR:
                return nz
        cpn = nat_at(cp[1] if sec["axis"] == "u" else cp[0])
        if cpn is None or yT - cpn <= 0.05:
            return nz
        if dT > CAP or not _daylights(cp, g, yT, nat_at, BFILL, CAP, K):
            return nz
        slack = dT / max(0.5, BFILL if yT > nz else BCUT)
        return max(yT - slack, min(nz, yT + slack))

    N = 2000
    step = (w1 - w0) / float(N)
    acc = {"cut": [0.0, 0.0], "fill": [0.0, 0.0], "keep": [0.0, 0.0], "unknown": [0.0, 0.0]}
    for i in range(N):
        w = w0 + (i + 0.5) * step
        dz, nz = design_at(w), nat_at(w)
        if dz is None or nz is None:
            k, dep = "unknown", 0.0
        elif nz - dz > 0.05:
            k, dep = "cut", nz - dz
        elif dz - nz > 0.05:
            k, dep = "fill", dz - nz
        else:
            k, dep = "keep", 0.0
        acc[k][0] += step * K
        acc[k][1] = max(acc[k][1], dep)
    tot = sum(v[0] for v in acc.values()) or 1.0
    JA = {"cut": "切土(なくなる)", "fill": "盛土(足す)",
          "keep": "造成しない(守る)", "unknown": "現況未実測"}
    rows = ""
    for k in ("cut", "fill", "keep", "unknown"):
        L, mx = acc[k]
        if L < 0.05:
            continue
        rows += ("<tr><td>%s</td><td>%.1f m</td><td>%.0f%%</td><td>%s</td></tr>"
                 % (JA[k], L, 100.0 * L / tot, ("最大 %.1f m" % mx) if mx > 0 else "—"))
    return ('<div class="tw"><table><thead><tr><th>区分</th><th>断面上の長さ</th>'
            "<th>割合</th><th>深さ</th></tr></thead><tbody>%s</tbody></table></div>" % rows)


# ================================================================ §3a 現況図
DEM_BANDS = [(8,"#2d6b8f"),(10,"#3d8fa8"),(12,"#5aa9a0"),(14,"#7cbf8e"),(16,"#a3d18a"),
             (18,"#c6de8c"),(20,"#e3e69a"),(22,"#f0dd93"),(24,"#e8c47e"),(26,"#dda86c"),
             (28,"#cf8a5e"),(30,"#bd6d55")]
def _band(h):
    """段彩。地図の記号なので**明暗テーマに関わらず固定色**(紙の地形図と同じ読み方をさせる)。"""
    c = DEM_BANDS[0][1]
    for lim, col in DEM_BANDS:
        if h >= lim:
            c = col
    return c


def dem_svg(d, dem, neighbours):
    """現況図(§3a)。段彩2m + 等高線(2m・10mを太線)+ 隣の屋敷の区画。"""
    x0, z0, st = dem["x0"], dem["z0"], dem["step"]
    nx, nz, H = dem["nx"], dem["nz"], dem["h"]
    P = d["polygon"]
    W = 980.0
    sx = W / (nx * st)
    Hh = nz * st * sx + 30 + 54
    def X(x): return (x - x0) * sx
    def Y(z): return 30 + (nz * st - (z - z0)) * sx
    g = _sv(W, Hh, "松平出羽守上屋敷 現況図(造成前の地形)")
    # 段彩(セル塗り)
    for j in range(nz - 1):
        for i in range(nx - 1):
            h = H[j][i]
            if h is None:
                continue
            g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (X(x0 + i * st), Y(z0 + (j + 1) * st), st * sx + 0.6, st * sx + 0.6, _band(h)))
    # 等高線(2m。10m は太線+数値)
    for lev in range(8, 32, 2):
        segs = []
        for j in range(nz - 1):
            for i in range(nx - 1):
                a, b, c2, e = H[j][i], H[j][i+1], H[j+1][i+1], H[j+1][i]
                if None in (a, b, c2, e):
                    continue
                cs = [a, b, c2, e]
                if min(cs) > lev or max(cs) < lev:
                    continue
                px, pz = x0 + i * st, z0 + j * st
                pts = []
                for (h1, h2, xa, za, xb, zb) in (
                        (a, b, px, pz, px+st, pz), (b, c2, px+st, pz, px+st, pz+st),
                        (c2, e, px+st, pz+st, px, pz+st), (e, a, px, pz+st, px, pz)):
                    if (h1 - lev) * (h2 - lev) < 0:
                        t = (lev - h1) / (h2 - h1)
                        pts.append((xa + (xb - xa) * t, za + (zb - za) * t))
                if len(pts) >= 2:
                    segs.append((pts[0], pts[1]))
        if not segs:
            continue
        thick = (lev % 10 == 0)
        for (p1, p2) in segs:
            g.append(LN(X(p1[0]), Y(p1[1]), X(p2[0]), Y(p2[1]),
                        "#5a4632", 1.5 if thick else 0.55, op=0.85 if thick else 0.5))
        if thick:
            p1 = segs[len(segs)//2][0]
            g.append(T(X(p1[0]), Y(p1[1]) - 2, "%dm" % lev, "jo", "middle", fill="#4a3a28"))
    # 隣の屋敷の区画
    for nm, poly, col in neighbours:
        g.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="1.6" stroke-dasharray="7 4" opacity="0.95"/>'
                 % (" ".join("%.1f,%.1f" % (X(q[0]), Y(q[1])) for q in poly), col))
        cx = sum(q[0] for q in poly) / len(poly); cz = sum(q[1] for q in poly) / len(poly)
        g.append(T(X(cx), Y(cz), nm, "anS", "middle", fill=col))
    # 当屋敷
    g.append('<polygon points="%s" fill="none" stroke="#1a1a1a" stroke-width="2.6"/>'
             % " ".join("%.1f,%.1f" % (X(q[0]), Y(q[1])) for q in P))
    # 表門・断面の切り位置
    gp = d["gate"]["pos"]
    g.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (X(gp[0]), Y(gp[1])))
    g.append(T(X(gp[0]) + 9, Y(gp[1]) - 5, "表門", "sr"))
    gr = RGrid(d)
    for sec in d["sections"]:
        if sec["axis"] == "u":
            a = gr.W(sec["at"], sec["from"]); b = gr.W(sec["at"], sec["to"])
        else:
            a = gr.W(sec["from"], sec["at"]); b = gr.W(sec["to"], sec["at"])
        g.append(LN(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), "var(--shu)", 1.0, dash="9 5", op=0.9))
        g.append(T(X(b[0]), Y(b[1]) - 5, sec["name"][:3], "sr", "middle"))
    # 目盛・スケールバー・方位
    g.append(LN(20, Hh - 30, 20 + 100 * sx, Hh - 30, "#1a1a1a", 2.4))
    g.append(T(20 + 50 * sx, Hh - 34, "100 m", "anS2", "middle", fill="#1a1a1a"))
    g.append(T(W - 8, 42, "北 ↑", "anS", "end", fill="#1a1a1a"))
    g.append(T(4, 16, "造成前の地形【確度P】段彩2m・等高線2m(10mを太線)。世界座標 x%.0f..%.0f / z%.0f..%.0f"
               % (x0, x0 + nx * st, z0, z0 + nz * st), "anS", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ================================================================ §3b 切盛図
def cutfill_map_svg(d, terr):
    """切盛図(§3b)。Δ=造成後−造成前 のセル塗り。暖色=盛土/寒色=切土/無彩=±0.3m/地の色=造成しない。"""
    gr = RGrid(d)
    u0, v0, st = terr["u0"], terr["v0"], terr["step"]
    nu, nv, H = terr["nu"], terr["nv"], terr["h"]
    P = d["polygon"]
    pr = Proj(min(q[0] for q in P) - 14, max(q[0] for q in P) + 14,
              min(q[1] for q in P) - 14, max(q[1] for q in P) + 14, W=940.0, top=26.0, bottom=58.0)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 切盛図")
    def col(dz, outside=False):
        a = abs(dz)
        if outside and a <= 0.05: return "#6f7a63"     # 地の色=造成しない(§3b の4区分目)
        if a <= 0.3: return "#b9b5a8"
        if dz > 0:   return "#f0d9a0" if a<1 else ("#e0a95e" if a<2 else ("#c9762f" if a<3 else "#9c4a14"))
        return "#c8dcea" if a<1 else ("#8fb6d4" if a<2 else ("#5286b2" if a<3 else "#2b5a83"))
    stats = {}
    cell = (st * d["const"]["ken"]) ** 2
    for j in range(nv):
        for i in range(nu):
            nz = H[j][i]
            if nz is None: continue
            u, v = u0 + i * st, v0 + j * st
            des = _design_at_uv(d, u, v, terr)
            if des is None: continue
            dz = des - nz
            wx, wz = gr.W(u, v)
            g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.95"/>'
                     % (pr.X(wx) - 2.4, pr.Y(wz) - 2.4, 4.8, 4.8,
                        col(dz, _terr_at(d, u, v) is None)))
            key = _terr_at(d, u, v) or ("段の外(法面・帯)" if abs(dz) > 0.05 else "造成しない(現地形のまま)")
            s = stats.setdefault(key, [0.0, 0.0, 0.0, 0.0, 0])
            if dz > 0: s[0] += dz * cell; s[1] = max(s[1], dz)
            else:      s[2] += -dz * cell; s[3] = max(s[3], -dz)
            s[4] += 1
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="2.0"/>'
             % " ".join("%.1f,%.1f" % (pr.X(q[0]), pr.Y(q[1])) for q in P))
    for t in d["terraces"]:
        c = gr.W((t["u0"]+t["u1"])/2.0, (t["v0"]+t["v1"])/2.0)
        g.append(T(pr.X(c[0]), pr.Y(c[1]), "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"]), "anS", "middle"))
    gp = d["gate"]["pos"]
    g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--shu)"/>' % (pr.X(gp[0]), pr.Y(gp[1])))
    g.append(T(4, 16, "Δ = 造成後の地盤 − 造成前の地形。暖色=盛土 / 寒色=切土 / 灰=±0.3m以内(実質さわらない)", "anS", "start"))
    g.append("</svg>")
    return "\n".join(g), stats


def _terr_at(d, u, v):
    for t in d["terraces"]:
        if t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9:
            return TERR_JA.get(t["name"], t["name"])
    return None


def _nat_uv(terr, u, v):
    i = int(round((u - terr["u0"]) / terr["step"])); j = int(round((v - terr["v0"]) / terr["step"]))
    if i < 0 or j < 0 or i >= terr["nu"] or j >= terr["nv"]: return None
    return terr["h"][j][i]


def _design_at_uv(d, u, v, terr):
    """面図と同じ規則(段 → 土留めの有無 → 法面)。断面の design_at の2次元版。"""
    K = d["const"]["ken"]
    for t in d["terraces"]:
        if t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9:
            return t["y"]
    nz = _nat_uv(terr, u, v)
    if nz is None: return None
    BF = d["const"].get("batterFill", 1.5); BC = d["const"].get("batterCut", 1.0)
    WN = d["const"].get("wallNear", 0.6);   CAP = d["const"].get("featherCap", 12.0)
    dT, yT, cp = 1e9, None, None
    for t in d["terraces"]:
        cu = max(t["u0"], min(u, t["u1"])); cv = max(t["v0"], min(v, t["v1"]))
        dd = math.hypot(u - cu, v - cv) * K
        if dd < dT: dT, yT, cp = dd, t["y"], (cu, cv)
    if yT is None: return nz
    for wl in d["terraceWalls"]:
        (ax, ay), (bx, by) = tuple(wl["a"]), tuple(wl["b"])
        dx, dy = bx - ax, by - ay; L2 = dx*dx + dy*dy
        tt = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((cp[0]-ax)*dx + (cp[1]-ay)*dy) / L2))
        if math.hypot(cp[0] - (ax + dx*tt), cp[1] - (ay + dy*tt)) <= WN: return nz
    cn = _nat_uv(terr, round(cp[0]), round(cp[1]))
    if cn is None or yT - cn <= 0.05: return nz
    if dT > CAP: return nz
    slack = dT / max(0.5, BF if yT > nz else BC)
    return max(yT - slack, min(nz, yT + slack))


# ================================================================ §3d 動線図
ROUTE_COL = {"omote": "#a8452c", "yaku": "#3d6ea8", "katte": "#7a5c3a", "oku": "#5f7a4e"}
def routes_svg(d):
    gr = RGrid(d); P = d["polygon"]
    pr = Proj(min(q[0] for q in P) - 14, max(q[0] for q in P) + 14,
              min(q[1] for q in P) - 14, max(q[1] for q in P) + 14, W=940.0, top=26.0, bottom=44.0)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 動線図")
    for t in d["terraces"]:
        g.append(gpoly_pr(gr, pr, t["u0"], t["v0"], t["u1"], t["v1"], DAN.get(t["y"], "var(--dan4)"), 0.5))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.8"/>'
             % " ".join("%.1f,%.1f" % (pr.X(q[0]), pr.Y(q[1])) for q in P))
    for m in d["munes"] + d["service"]:
        g.append(gpoly_pr(gr, pr, m["u0"], m["v0"], m["u1"], m["v1"], "var(--ink-mid)", 0.7))
    for k in d["kaidans"]:                     # 石段を重ねる(§3d「どこで段を越えるか」)
        if "pos" not in k:
            continue
        q = gr.W(k["pos"][0], k["pos"][1])
        g.append('<rect x="%.1f" y="%.1f" width="9" height="9" fill="var(--shu-lo)" '
                 'stroke="var(--shu)" stroke-width="1.4"/>' % (pr.X(q[0]) - 4.5, pr.Y(q[1]) - 4.5))
        g.append(T(pr.X(q[0]) + 7, pr.Y(q[1]) + 4, "%s %d段" % (k["name"], k["steps"]), "jo"))
    for r in d["routes"]:
        pts = [gr.W(p[0], p[1]) for p in r["pts"]]
        c = ROUTE_COL.get(r["kind"], "var(--ink)")
        g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3.2" opacity="0.9" stroke-linejoin="round" stroke-linecap="round"/>'
                 % (" ".join("%.1f,%.1f" % (pr.X(q[0]), pr.Y(q[1])) for q in pts), c))
        g.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s"/>' % (pr.X(pts[0][0]), pr.Y(pts[0][1]), c))
        g.append(T(pr.X(pts[-1][0]) + 6, pr.Y(pts[-1][1]) - 4, r["label"], "anS", "start", fill=c))
    g.append(T(4, 16, "門を入ってからの動きの想定。表向/役方/勝手/奥向で色を分ける", "anS", "start"))
    g.append("</svg>")
    return "\n".join(g)


def gpoly_pr(gr, pr, u0, v0, u1, v1, fill, op):
    q = [gr.W(u0, v0), gr.W(u1, v0), gr.W(u1, v1), gr.W(u0, v1)]
    return '<polygon points="%s" fill="%s" opacity="%.2f"/>' % (
        " ".join("%.1f,%.1f" % (pr.X(a[0]), pr.Y(a[1])) for a in q), fill, op)


def garden_svg(d):
    """庭園図 — 庭域だけを大縮尺で。敷地図の縮尺では飛石も植栽も読めない。
    §3d の動線図とは別物: こちらは「庭として何がどこにあるか」を示す。"""
    gr = RGrid(d)
    gz = [g for g in d["gardens"] if g["name"] in ("G_NishiNiwa",)]
    if not gz:
        return ""
    u0 = min(g["u0"] for g in gz) - 4; u1 = max(g["u1"] for g in gz) + 18
    v0 = min(g["v0"] for g in gz) - 6; v1 = max(g["v1"] for g in gz) + 10
    corners = [gr.W(a, b) for a in (u0, u1) for b in (v0, v1)]
    pr = Proj(min(q[0] for q in corners) - 6, max(q[0] for q in corners) + 6,
              min(q[1] for q in corners) - 6, max(q[1] for q in corners) + 6,
              W=940.0, top=26.0, bottom=46.0)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 庭園図")

    def gp(a, b, c, e, fill, op=1.0, stroke="none", sw=0.0):
        q = [gr.W(a, b), gr.W(c, b), gr.W(c, e), gr.W(a, e)]
        return ('<polygon points="%s" fill="%s" opacity="%.2f" stroke="%s" stroke-width="%.1f"/>'
                % (" ".join("%.1f,%.1f" % (pr.X(x[0]), pr.Y(x[1])) for x in q), fill, op, stroke, sw))
    def gpt(u, v):
        q = gr.W(u, v); return pr.X(q[0]), pr.Y(q[1])

    for t in d["terraces"]:
        g.append(gp(t["u0"], t["v0"], t["u1"], t["v1"], "var(--pl-main)", 0.5))
    for n in d["gardens"]:
        if n["u1"] < u0 or n["u0"] > u1 or n["v1"] < v0 or n["v0"] > v1:
            continue
        col = "var(--shirasu)" if n.get("kind") == "shirasu" else "var(--niwa)"
        g.append(gp(n["u0"], n["v0"], n["u1"], n["v1"], col, 0.9, "var(--ink-lo)", 1.0))
        x, y = gpt((n["u0"] + n["u1"]) / 2.0, (n["v0"] + n["v1"]) / 2.0)
        g.append(T(x, y + 4, n["label"], "rmS", "middle",
                   fit(n["label"], pr.L(n["u1"] - n["u0"]), 12.0)))
    for m in d["munes"] + d["service"]:
        if m["u1"] < u0 or m["u0"] > u1 or m["v1"] < v0 or m["v0"] > v1:
            continue
        g.append(gp(m["u0"], m["v0"], m["u1"], m["v1"], "var(--ink-mid)", 0.85, "var(--ink)", 0.7))
        x, y = gpt((m["u0"] + m["u1"]) / 2.0, (m["v0"] + m["v1"]) / 2.0)
        lb = MUNE_JA.get(m["name"], m.get("label", m["name"]))
        g.append(T(x, y + 4, lb, "rmS", "middle", fit(lb, pr.L(m["u1"] - m["u0"]), 11.0)))
    for w in d.get("wells", []):
        if not (u0 <= w["u"] <= u1 and v0 <= w["v"] <= v1):
            continue
        x, y = gpt(w["u"], w["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="var(--paper)" stroke="var(--ink)" '
                 'stroke-width="1.4"/>' % (x, y))
        g.append(T(x + 6, y + 4, "井戸", "jo"))
    for r in d["routes"]:
        pts = [gpt(q[0], q[1]) for q in r["pts"]]
        if not any(u0 <= q[0] <= u1 and v0 <= q[1] <= v1 for q in r["pts"]):
            continue
        g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.6" '
                 'stroke-linejoin="round" stroke-linecap="round" opacity="0.85"/>'
                 % (" ".join("%.1f,%.1f" % q for q in pts), ROUTE_COL.get(r["kind"], "var(--ink)")))
    # 植栽 — 層ごとに記号を散らす(位置は設計値でなく、層と本数から決めた見当)
    import random as _rnd
    PLC = {"主木": ("#3E5A3A", 5.2), "中木": ("#5E7A4E", 3.6),
           "低木・刈込": ("#8FA36B", 4.4), "中木・下草": ("#5E7A4E", 3.4),
           "花木": ("#8A6B7A", 3.0)}
    for pl in d.get("planting", []):
        z = next((x for x in d["gardens"] if x["name"] == pl["zone"]), None)
        if z is None or not pl.get("n"):
            continue
        col, rr = PLC.get(pl["layer"], ("#5E7A4E", 3.2))
        rg = _rnd.Random(hash(pl["zone"] + pl["layer"]) & 0xffff)
        for _ in range(int(pl["n"])):
            uu = rg.uniform(z["u0"] + 1.5, z["u1"] - 1.5)
            vv = rg.uniform(z["v0"] + 1.5, z["v1"] - 1.5)
            x, y = gpt(uu, vv)
            g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.75"/>'
                     % (x, y, rr, col))

    # 点景(露地の飛石道・中門・蹲踞・灯籠・石組・垣)
    TK = {"露地(飛石道)": "var(--michi)", "建仁寺垣": "var(--take)"}
    for t in d.get("tenkei", []):
        if "pts" in t:
            g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4" '
                     'stroke-dasharray="3 4" stroke-linecap="round"/>'
                     % (" ".join("%.1f,%.1f" % gpt(q[0], q[1]) for q in t["pts"]),
                        TK.get(t["kind"], "var(--michi)")))
        elif "a" in t:
            xa, ya = gpt(t["a"][0], t["a"][1]); xb, yb = gpt(t["b"][0], t["b"][1])
            g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                     'stroke-width="2.2" stroke-dasharray="6 3"/>'
                     % (xa, ya, xb, yb, TK.get(t["kind"], "var(--take)")))
        else:
            x, y = gpt(t["u"], t["v"])
            g.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--shu)"/>' % (x, y))
            g.append(T(x + 5, y + 4, t["kind"], "jo"))
    g.append(T(4, 16, "西の帯は露地と芝野。**池は置かない**(裁定の理由は其廿二)", "anS", "start"))
    g.append(T(pr.W - 4, 16, "北 ↑　左=西(溜池・崖)", "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


def routes_table(d):
    gr = RGrid(d); K = d["const"]["ken"]
    rows = ""
    for r in d["routes"]:
        L = 0.0
        for i in range(len(r["pts"]) - 1):
            a, b = r["pts"][i], r["pts"][i + 1]
            L += math.hypot(b[0] - a[0], b[1] - a[1]) * K
        # 越える石段: 石段の位置(pos)から3間以内を通る折れ線だけを数える
        uniq = []
        for k in d["kaidans"]:
            if "pos" not in k:
                continue
            ku, kv = k["pos"]
            near = False
            for i in range(len(r["pts"]) - 1):
                a, b = r["pts"][i], r["pts"][i + 1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dy * dy
                t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((ku - a[0]) * dx + (kv - a[1]) * dy) / L2))
                if math.hypot(ku - (a[0] + dx * t), kv - (a[1] + dy * t)) <= 3.0:
                    near = True
                    break
            if near:
                uniq.append(k)
        rise = sum(k["drop"] for k in uniq)
        steps = sum(k["steps"] for k in uniq)
        rows += ("<tr><td>%s</td><td>%.0f m</td><td>%.1f m</td><td>%d 段</td><td class='note'>%s</td></tr>"
                 % (r["label"], L, rise, steps,
                    " / ".join(k["name"] for k in uniq) if uniq else "石段なし"))
    return ('<div class="tw"><table><thead><tr><th>系統</th><th>延長</th><th>昇り</th>'
            "<th>石段</th><th class='note'>越える石段</th></tr></thead><tbody>%s</tbody></table></div>" % rows)


def cutfill_stats_table(d, stats):
    rows = ""
    tf = tc = 0.0
    for k in sorted(stats, key=lambda x: -stats[x][0]):
        f2, fm, c2, cm, n = stats[k]
        tf += f2; tc += c2
        rows += ("<tr><td>%s</td><td>%.0f m²</td><td>%.0f m³</td><td>%.2f m</td>"
                 "<td>%.0f m³</td><td>%.2f m</td></tr>"
                 % (k, n * (d["const"]["ken"]) ** 2, f2, fm, c2, cm))
    rows += ("<tr><td><b>計</b></td><td></td><td><b>%.0f m³</b></td><td></td>"
             "<td><b>%.0f m³</b></td><td></td></tr>" % (tf, tc))
    rows += ("<tr><td><b>差引</b></td><td colspan='5' class='note'>盛土 − 切土 = <b>%.0f m³</b>%s</td></tr>"
             % (tf - tc, "(正なら土が足りない=客土が要る)" if tf > tc else ""))
    return ('<div class="tw"><table><thead><tr><th>段</th><th>面積</th><th>盛土量</th><th>最大盛土</th>'
            "<th>切土量</th><th>最大切土</th></tr></thead><tbody>%s</tbody></table></div>" % rows)


def fig(h, svg, cap=None, legend=None):
    h.append('<div class="fig">%s</div>' % svg)
    if legend:
        h.append('<div class="legend">%s</div>' % legend)
    if cap:
        h.append('<p class="cap">%s</p>' % cap)


def main():
    global DAN
    d = json.load(open(JSON, encoding="utf-8"))
    prose = md2html(open(MD, encoding="utf-8").read())
    # 造成前の地形【確度P】。**生成器はこれを読む — 実装は読まない**(§3a/§3b)
    dem = json.load(open(os.path.join(DOC, "matsudaira_dem.json"), encoding="utf-8"))
    DAN = dan_map(d)
    terr = json.load(open(os.path.join(DOC, "matsudaira_terrain.json"), encoding="utf-8"))
    parcels = json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))
    NEI = [("土井大隅守邸", "doi", "#7a4a8a"), ("岡部内膳正邸", "okabe", "#2f6b4f")]
    neighbours = []
    for label, pid, col in NEI:
        for pc in parcels["parcels"]:
            if pc["id"] == pid:
                neighbours.append((label, pc["pts"], col))
    P = d["polygon"]
    area = abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
                   for i in range(len(P)))) / 2

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

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ['<meta charset="utf-8">', "<title>松平出羽守上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">外桜田永田町 ／ 親藩国主・大広間 十八万六千石 上屋敷</p>')
    h.append("<h1>松平出羽守上屋敷 指図</h1>")
    h.append('<div class="box" style="border-color:var(--shu);margin-top:14px"><h3>基準年次と確度</h3><p>'
             '<b>「松平出羽守」は斉貴(〜嘉永6年9月)と定安(嘉永6年9月〜)のどちらも指す。</b>'
             'シーンの基準は嘉永期。嘉永前半は斉貴がほぼ連続在府していた。<br>'
             '<b>当屋敷の指図・絵図は散逸</b>(藩主家の史料自体が散逸)。表門まわりの部材・意匠は'
             '明治初期の実写真(江戸東京博物館 温古写真集11)から起こした<b>確度A</b>'
             '(表門=屋根なし冠木門+両唐破風番所【写真A+日本案内記A/嘉永期への外挿はB】、位置=明治16年実測図【A寄りB】)。御殿の構成は<b>類型(確度B)</b>、'
             '室名・畳数は<b>想定(確度?)</b>。区画の多角形は<b>ユーザーのブックマーク角(確度U)</b>。'
             '石井戸枠は存在A・奥庭という位置は?。</p></div>')
    h.append('<p class="lede"><b>この文書は現況だけを載せる。</b>過去の案・撤回した説は書かない — '
             '経緯は <code>git log docs/Sashizu/</code> で追う。'
             '寸法の正典は <code>matsudaira_sashizu.json</code>、文章は <code>matsudaira_kosho.md</code>、'
             'この HTML は <code>Tools/Sashizu/build_matsudaira_sashizu.py</code> が組む。'
             '<b>数値をこの文書に書き足さないこと。</b></p>')
    h.append('<div class="box"><h3>作る順序</h3><p>'
             '① 設計=<code>json</code>/<code>md</code> を直す → ② 組む → ③ 検図(edo-kosho / edo-kenzu)'
             '→ ユーザーのレビュー → ④ 実装 → ⑤ 指図と実装を突き合わせて 0 件 → ⑥ 経緯はコミットへ。</p></div>')

    KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
           "其十一", "其十二", "其十三", "其十四", "其十五",
           "其十六", "其十七", "其十八", "其十九", "其二十",
           "其廿一", "其廿二", "其廿三", "其廿四", "其廿五"]
    _kn = [0]

    def nx():
        _kn[0] += 1
        return KAN[_kn[0] - 1]

    _gr = d["grid"]["shukaku"]
    grid_deg = math.degrees(math.atan2(_gr["uz"], _gr["ux"]))
    plate(h, nx(), "敷地", "%.0f m²(%.0f坪)/拝領%s坪%s【%s】/江戸間 1間=%.3fm/主郭グリッドは北辺沿いに%.2f°回転"
          % (area, area / TSUBO, format(d["hairyo"]["tsubo"], ","),
             "余" if d["hairyo"].get("approx") else "", d["hairyo"]["cert"],
             d["const"]["ken"], grid_deg))
    fig(h, plan_svg(d),
        legend=('<span style="color:var(--pl-omote)">■ 表郭 %.1f</span>'
                '<span style="color:var(--pl-main)">■ 主平面 %.1f</span>'
                % (d["planes"][0]["y"], d["planes"][1]["y"])) +
               '<span style="color:var(--pl-slope)">■ 斜面(造成しない・松+雑木の樹林)</span>'
               '<span style="color:var(--nagaya)">━ 表長屋</span>'
               '<span style="color:var(--hei)">━ 練塀(面の縁のみ)</span>'
               '<span style="color:var(--take)">┄ 竹垣(法肩)/ 木柵(境界・地形なり)</span>'
               '<span style="color:var(--ishi)">┄ 郭の土留め</span>'
               '<span>▪ 御殿の棟 ／ ▫ 付属屋</span>'
               '<span style="color:var(--shu)">● 表門 ／ ■ 隅櫓 ／ ┄ 断面</span>',
        cap="<b>敷地は2つの水平面+1つの斜面。</b>造成も囲いもまず面から決め、"
            "囲いの天端=面の高さ、段は面の境にだけ立つ。"
            "<b>西斜面(溜池東岸)と南西の谷(岡部境)は造成しない</b> — 庭のまま、面の縁に竹垣。"
            "斜面は<b>黒松を疎に交えた雑木の樹林</b>(法肩=樹林／中部=低木／下部=草地の3帯)"
            "【確度B — 溜池の水辺の樹木は松、竹薮は江戸の水辺79事例中1例(其十一)】。"
            "鞍部の盛土(量は段の note を正とする)で表長屋の石垣基壇が大通りへ露出する。"
            "西斜面の近代掘削の埋め戻しは拝領時造成と別勘定の復元【出自判定は ?】。"
            "<b>街路・隣地への影響はゼロ</b> — 面の造成は区画線で切り(図の色もその形)、"
            "境界の高低差は垂直の基壇石垣で受けるので、法尻が道や隣地へ出ることもない。")
    h.append(planes_table(d))
    h.append(slope_table(d))
    h.append('<p class="cap"><b>面のはみ出し検査(0.5間刻みの被覆・区画内包も判定): %s。</b>'
             '棟・付属屋・廊下は自分の y と同じ高さの段の中に、庭・井戸はいずれかの段の中に'
             '完全に載っていること+**区画多角形の内側にあること**を機械検査している'
             '(造成しない斜面に載る庭=西庭の斜面部だけ除外)。'
             '<b>矩形の総当たり重なり: %s。</b></p>'
             % ("<b>0 件</b>" if not pbad else "⚠ %d 件 — %s" % (len(pbad), " / ".join(pbad)),
                "<b>0 件</b>" if not bad else "⚠ %d 件" % len(bad)))
    h.append("</div>")

    plate(h, nx(), "現況図(造成前の地形)", "段彩2m・等高線2m(10mを太線)/【確度P】2026-08-23 実測")
    fig(h, dem_svg(d, dem, neighbours),
        legend='<span style="color:#2d6b8f">■ 8-12m</span><span style="color:#5aa9a0">■ 12-16m</span>'
               '<span style="color:#a3d18a">■ 16-20m</span><span style="color:#e3e69a">■ 20-24m</span>'
               '<span style="color:#dda86c">■ 24-28m</span><span style="color:#bd6d55">■ 28m-</span>'
               '<span style="color:#7a4a8a">┄ 土井邸</span><span style="color:#2f6b4f">┄ 岡部邸</span>',
        cap="<b>造成のすべての出発点。</b>面の高さはこの地形を 0.5間刻みで走査して決めた(§B-1) — "
            "設計者が先に決めていない。<b>隣の屋敷の区画も重ねてある</b>: 尾根と谷がどこから来ているかは、"
            "自分の区画だけ描くと読めない。段彩の色は地図の記号なので明暗テーマによらず固定。")
    h.append("</div>")

    plate(h, nx(), "切盛図", "Δ = 造成後の地盤 − 造成前の地形")
    _cf_svg, _cf_stats = cutfill_map_svg(d, terr)
    fig(h, _cf_svg,
        legend='<span style="color:#9c4a14">■ 盛土 3m超</span><span style="color:#c9762f">■ 2-3m</span>'
               '<span style="color:#e0a95e">■ 1-2m</span><span style="color:#f0d9a0">■ 0.3-1m</span>'
               '<span style="color:#b9b5a8">■ ±0.3m(実質さわらない)</span>'
               '<span style="color:#c8dcea">■ 切土 0.3-1m</span><span style="color:#8fb6d4">■ 1-2m</span>'
               '<span style="color:#5286b2">■ 2-3m</span><span style="color:#2b5a83">■ 3m超</span>',
        cap="<b>面の高さの表だけでは造成が読めない</b>ので図にする(§3b)。"
            "法面も土量に含む — 段の外へこぼれる分は本物の土工。"
            "<b>灰色が広いほど地形に素直</b>。近代の掘削跡の埋め戻し(西の濃い暖色)は拝領時造成とは別勘定。")
    h.append(cutfill_stats_table(d, _cf_stats))
    h.append("</div>")

    plate(h, nx(), "表向 平面", "室名・畳数は【確度 ?】— 当屋敷の史料は散逸・類型からの想定")
    fig(h, goten_plan(d, -50, 22, -3, 36, "表向 平面",
                      "廊下は入側・渡廊下とも幅一間で一定。表門の軸=玄関の軸"),
        legend='<span style="color:var(--roka)">■ 入側・渡廊下(幅一間)</span>'
               '<span style="color:var(--niwa)">■ 庭</span>'
               '<span style="color:var(--shirasu)">■ 白洲</span>'
               '<span>┄ 襖線(続き間の境)</span>',
        cap="<b>表門 → 白洲 → 石段(4段) → 御式台・御玄関</b>。西へ大広間・黒書院・表役所(藩庁)、"
            "東は東肩の帯を経て蔵の帯(主平面と同高)。"
            "御成セット(御成門・御成書院・能舞台)は 2026-08-23 撤去 — 御成の記録なし・"
            "御成を受けた加賀本郷邸の幕末プランにも御成門は無い(其九)。")
    h.append("</div>")

    plate(h, nx(), "中奥・奥向 平面", "室名・畳数は【確度 ?】/御書物之間・御時計之間は斉貴の嗜好(B)からの想定")
    fig(h, goten_plan(d, -78, 18, 31, 82, "中奥・奥向 平面",
                      "奥向へ入る廊下は御錠口の一本だけ。奥台所・長局はすべて錠の先にある"),
        legend='<span style="color:var(--roka)">■ 入側・渡廊下</span>'
               '<span style="color:var(--shu)">■ 御錠口</span>'
               '<span style="color:var(--niwa)">■ 庭</span>',
        cap="<b>大台所は敷地のほぼ中心</b>(西川1959)。中奥の御書物之間(鷹書)・御時計之間(西洋文物)は"
            "斉貴の嗜好からの想定の設え【確度 ?】。奥庭の<b>石井戸枠(慶長18年銘・約2m四方)は"
            "現存する実物</b>【存在=A/奥庭という位置=?】— 家康が駿府で使った物を直政が拝領して移した伝承。")
    h.append("</div>")


    plate(h, nx(), "棟と室", "1間²=2畳 ／ 室名・畳数は【確度 ?】(土間・板敷は間²)")
    h.append(munes_table(d))
    h.append(links_table(d))
    kp_html, kp = kenpei(d, area)
    nagL = sum(r["s1"] - r["s0"] for r in d["runs"] if r["kind"] == "Nagaya")
    perim = sum(math.hypot(P[(i + 1) % len(P)][0] - P[i][0], P[(i + 1) % len(P)][1] - P[i][1])
                for i in range(len(P)))
    h.append("<h3>建蔽率</h3>")
    h.append(kp_html)
    h.append('<p class="cap"><b>分母は敷地全体=図上実測 %.0f坪</b>(拝領%s坪【%s】との差+%.1f%%。'
             '拝領値を分母にすると%.1f%%)。可建地に替えて数字を作らない。'
             '<b>大名上屋敷の建蔽率の史料値は [福井図] の5〜6割の一点しかなく</b>、当図はそれより'
             '大きく低い(広い拝領地・表門前の白洲・奥庭・明地・造成しない斜面の帰結)。'
             '参考: 表長屋の外周比 %.1f%%(表長屋 %.0fm / 外周 %.0fm)— [追川2017] の「表長屋の規模比」'
             'は<b>分母が原典未確認のため帯(加賀本郷15%%・小浜28.6%%・尾張市谷47.7%%)との数値比較は'
             'しない</b>(sources.md の警告)。'
             '<b>建蔽率は結果であって目標ではない</b> — 数字のために空地へ棟を足さない。</p>'
             % (area / TSUBO, format(d["hairyo"]["tsubo"], ","), d["hairyo"]["cert"],
                100.0 * (area / TSUBO - d["hairyo"]["tsubo"]) / d["hairyo"]["tsubo"],
                kp * (area / TSUBO) / d["hairyo"]["tsubo"], 100.0 * nagL / perim, nagL, perim))
    h.append("</div>")

    for s in d["sections"]:
        plate(h, nx(), s["name"], "%s = %g ／ 垂直%.1f倍 ／ 切るもの: %s"
              % (s["axis"], s["at"], s["vExag"],
                 " → ".join(section_crossings(d, s)) or "(無し)"))
        fig(h, section_svg(d, s),
            legend='<span style="color:var(--shu)">▨ 切土 — 削り取ってなくなる土</span>'
                   '<span style="color:var(--nagaya)">▨ 盛土 — 足す土</span>'
                   '<span>┅ 現況地盤(地形再作成後の実測)</span>'
                   '<span style="color:var(--take)">▬ 造成しない区間(現地形のまま=守る)</span>'
                   '<span style="color:var(--dim)">▬ 現況未実測(切盛を判定していない)</span>',
            cap="<b>実線=拝領時の造成を終えた地盤/破線=現況地盤。</b>2本の間が動く土で、"
                "<b>現況が上なら切土(なくなる)・設計が上なら盛土(足す)</b>。"
                "足元の緑の帯は<b>造成せず現地形のまま残す区間</b>(斜面・明地)。"
                "地表下の色帯=面(其一と同じ色分け)。両端には区画線上の囲いを天端と基壇石垣つきで示す — "
                "基壇は境界線上に垂直に立ち、道・隣地の地形には触れない。"
                "屋根は図示のための概略で、実装の高さは部材が決める(突き合わせの対象外)。"
                + ("<br><b style='color:var(--shu)'>⚠ 現況地盤は暫定値</b> — 表門移設でグリッドを"
                   "引き直す前の座標系で測った値の換算。平場の誤差は小さいが斜面では断面線が横へ"
                   "ずれている可能性がある(測り直しは _pending.dammenSaisokutei)。切土・盛土の"
                   "量もこの精度で読むこと。" if s.get("naturalProvisional") else ""))
        h.append(cutfill_table(d, s))
        h.append("</div>")

    plate(h, nx(), "動線", "門を入ってからどう動く想定か(§3d)")
    fig(h, routes_svg(d),
        legend='<span style="color:#a8452c">━ 表向(客・使者)</span><span style="color:#3d6ea8">━ 役方(日勤)</span>'
               '<span style="color:#7a5c3a">━ 勝手(賄・物資)</span><span style="color:#5f7a4e">━ 奥向</span>',
        cap="平面と断面だけでは<b>建てた後に人がどう動くか</b>が読めない。"
            "<b>勝手の動線は御蔵門から引いた</b> — これが無いと米も薪も表門から入ることになる。"
            "奥向へ入る経路は<b>御錠口ただ一本</b>で、表・勝手とは交わらない。")
    h.append(routes_table(d))
    h.append("</div>")

    if any(g["name"] == "G_NishiNiwa" for g in d["gardens"]):
        plate(h, nx(), "庭園図(西庭)",
              "露地・芝野・樹林 ／ **池は置かない**(裁定と典拠は其廿二)")
        fig(h, garden_svg(d),
            cap="<b>敷地図の縮尺では飛石も植栽も読めないので庭だけを大縮尺で出す。</b>"
                "西の帯は御殿複合と崖の間に残る面で、<b>造成しない</b>(西縁 v15..36 だけ土留め TW_Nishi が受ける)。"
                "役所・奥御殿の西面がここに向き、竹垣の先は崖と溜池。"
                "⚠ <b>図中の樹の位置は層と本数から散らした目安で、設計値ではない</b> — "
                "実装では<b>3・5・7 の奇数の塊で不等辺三角</b>に組む(等間隔に並べない)。"
                "設計値は下の植栽表と点景表が正典。")
        if d.get("planting"):
            rows = "".join("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td>%s</td>"
                           "<td class='note'>%s</td></tr>"
                           % (pl["zone"], pl["layer"], pl["species"],
                              pl["n"] or "—", pl["_"])
                           for pl in d["planting"])
            h.append("<h3>植栽【すべて確度B=類型。当屋敷の一次史料は無い】</h3>"
                     "<div class='tw'><table><thead><tr><th>庭</th><th>層</th>"
                     "<th class='note'>樹種</th><th>本</th><th class='note'>置き方</th>"
                     "</tr></thead><tbody>%s</tbody></table></div>" % rows)
            h.append("<p class='cap'>⛔ <b>ソメイヨシノを植えない</b>(命名 明治33年。"
                     "そもそも季節が春でないので開花木は置かない)／⛔ <b>孟宗竹の竹叢を広げない</b>"
                     "(江戸の水辺79事例中1例。竹垣の材としての竹は別)／⛔ 幕末以降の外来種は不可。"
                     "<b>石材は庭全体で一系統</b>(伊豆石)。</p>")
        if d.get("tenkei"):
            rows2 = "".join("<tr><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                            % (t["name"], t["kind"], t["_"]) for t in d["tenkei"])
            h.append("<h3>点景(露地・灯籠・石組・垣)</h3><div class='tw'><table><thead><tr>"
                     "<th>名</th><th>種別</th><th class='note'>注記</th></tr></thead>"
                     "<tbody>%s</tbody></table></div>" % rows2)
        h.append("</div>")

    plate(h, nx(), "外周の展開", "天端は辺ごとに一本。段は門・頂点・郭境の延長線でのみ落とす")
    fig(h, perimeter_dev_svg(d))
    h.append(runs_table(d))
    h.append('<p class="cap">長屋は<b>表門の両翼と北東・東辺だけ</b>。南(土井境の台地上)と北辺西は練塀、'
             '<b>斜面・谷・水際は塀を立てず地形なりの木柵</b>(囲いの実体は崖と樹林+法肩の竹垣)。'
             '土井境の囲いは1条・松平が持つ(区画トポロジの裁定)。犬走り %.2fm。</p>'
             % d["const"]["inubashiri"])
    h.append("</div>")

    plate(h, nx(), "表門まわり", "冠木門(屋根なし)+両唐破風番所【写真A+日本案内記A/嘉永期への外挿はB】")
    fig(h, gate_svg(d),
        cap="<b>江戸東京博物館 温古写真集11「旧雲州松江藩松平候上屋敷門」(88005761・明治初撮影)から。</b>"
            "昭和14年時点の現存5大名門の一つで、東京大空襲で焼失。"
            "屋根なし冠木門は焼失規定(焼失後は冠木門しか再建できず番所の唐破風で格式を示す)と整合 — "
            "切妻小屋根を載せる前案は撤回(2026-08-23)。当門の焼失・改築の年次が嘉永の前か後かが残る宿題。"
            "両唐破風番所は国持の格(加賀赤門・鳥取黒門と同格)。石垣畳出は親藩ゆえ制限外。")
    h.append("</div>")

    plate(h, nx(), "郭の土留めと竹垣")
    h.append(walls_table(d))
    h.append('<p class="cap">西斜面・南西の谷の法肩には<b>竹垣(四つ目垣)</b>を回す — '
             '落差のある生活面を素の縁にしない(岡部指図と同じ作法)。高さ0.9m・法肩から内へ0.45m。'
             '茶庭の縁もこの竹垣で、座敷と茶亭から溜池を垣越しに望む。</p>')
    h.append("</div>")

    plate(h, nx(), "取り合い(実装用)", "すべて設計値から自動算出 — 手で書き写さない")
    h.append(corners_table(d))
    h.append(joints_table(d))
    h.append(civil_table(d))
    h.append(mune_contacts_table(d))
    h.append(gate_parts_table(d))
    h.append('<p class="cap"><b>bench=true の run は外周帯(内側幅3m)を天端へ整地する</b>(切盛±1.7m)。'
             '地形へこまめに追従して段を刻まない — 堀端通り沿い5辺215mは一本の天端。'
             '隣地・道の地形は動かせないので、差は基壇石垣の露出として受ける。</p>')
    h.append("</div>")

    if "bom" in d:
        plate(h, nx(), "部材表", "在庫は docs/asset-catalog.md 照会済み。新造は edo-buzai(Blender)")
        h.append(bom_table(d))
        h.append("</div>")

    plate(h, nx(), "考証と決めごと")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, "改訂", "", "経緯はここに書かず git で追う")
    h.append(history())
    h.append("</div>")

    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>matsudaira_sashizu.json</code> ／ '
             '文章 <code>matsudaira_kosho.md</code>。Y は海抜 m(Unity の Y がそのまま標高)。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    open(OUT, "w", encoding="utf-8").write("\n".join(h))
    print("wrote %s (%.0f KB) — 図版 %d 面 — 建蔽率 %.1f%%" % (OUT, os.path.getsize(OUT) / 1024, _SVN[0], kp))
    if bad:
        print("⚠ 重なり %d 件 — 検図の前に直すこと" % len(bad))
    print("  run: 検図(edo-kosho / edo-kenzu) → ユーザーのレビュー → 実装 → 突き合わせ")


if __name__ == "__main__":
    main()
