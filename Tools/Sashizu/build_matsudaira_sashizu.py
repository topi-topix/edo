#!/usr/bin/env python3
"""松平出羽守上屋敷(出雲松江藩)の指図を組む。

    python3 Tools/Sashizu/build_matsudaira_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/matsudaira_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/matsudaira_kosho.md     … 文章の部(人が書く・現況形)

の二つだけ。実装から指図を作ると CLAUDE.md 絶対規則2 の関門が消える。

【この屋敷ならではの作り】北辺の大通りが世界軸から 24.49° 振れているため、
主郭は**回転間グリッド**(u=北辺沿い東+ / v=敷地の奥+)で持つ。
    ・世界図版(其一)は Proj(世界→px)
    ・御殿平面(其二・其三)は LProj(グリッド間→px)— 棟・室・庭はすべて軸平行になる
    ・外周(其六)は辺番号+辺沿い走り s で持つ run を展開する

【図版】其一 敷地/其二 表向・御成 平面/其三 中奥・奥向 平面/其四 棟と室(表)/
        其五 断面(南北・東西)/其六 外周の展開/其七 表門まわり(写真A)/
        其八 郭の土留めと竹垣/其九 考証/改訂。
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


DAN = {26.1: "var(--pl-omote)", 27.0: "var(--pl-main)", 28.8: "var(--pl-higashi)"}
PLANE_COL = {"表郭": "var(--pl-omote)", "主平面": "var(--pl-main)", "東上段": "var(--pl-higashi)",
             "堀端の裾": "var(--pl-suso)", "斜面(造成しない)": "var(--pl-slope)"}
KC = {"Nagaya": "var(--nagaya)", "Dobei": "var(--hei)"}

MUNE_JA = {
    "Yakusho": "表役所棟", "Genkan": "玄関棟", "Ohiroma": "大広間棟", "Kuroshoin": "黒書院棟",
    "OnariGenkan": "御成玄関", "OnariShoin": "御成書院棟", "OnariYudono": "御成湯殿",
    "Gakuya": "楽屋棟", "Butai": "能舞台", "Nakaoku": "中奥棟", "Daidokoro": "大台所棟",
    "Okugoten": "奥御殿棟", "OkuYudono": "御湯殿", "NagatsuboneN": "長局棟(北)",
    "NagatsuboneS": "長局棟(南)", "OkuDaidokoro": "奥台所棟", "Umaya": "厩棟",
}
TERR_JA = {"Omote": "表郭", "ShukakuN": "御成道", "Shukaku": "主郭", "ShukakuE": "主郭(東翼)",
           "ShukakuS": "奥郭", "Higashi": "東上段"}


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
    om = d["onarimon"]
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
        g.append(T(pr.X(min(a_u, b_u) + 1), pr.Y(max(min(a_v, b_v), v0) + 1.6), w["name"], "jo"))
    for k in d["kaidans"]:
        w = [x for x in d["terraceWalls"] if x["name"] == k["atWall"]][0]
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

    # 地盤 = 郭の段 + natural の折れ線
    segs = []
    for t in d["terraces"]:
        if covers(t):
            a, b = span(t)
            segs.append((max(a, w0), min(b, w1), t["y"]))
    segs.sort()
    prof = []
    for a, b, y in segs:
        if b <= a:
            continue
        prof.append((a, y)); prof.append((b, y))
    for p in sec.get("natural", []):
        prof.append((p[0], p[1]))
    prof.sort()

    ys = [p[1] for p in prof]
    y1 = max(ys) + 8.0
    y0 = min(ys) - 3.0
    W = 1000.0
    sx = W / float(w1 - w0)
    HEAD, FOOT = 26.0, 46.0
    H = (y1 - y0) * sx * ex + HEAD + FOOT

    def X(w): return (w - w0) * sx
    def Y(y): return HEAD + (y1 - y) * sx * ex

    g = _sv(W, H, "松平出羽守上屋敷 %s" % sec["name"])
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
            continue                                  # 門の開口
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
    y1 = max(seats) + nagH + 1.0
    y0 = min(seats) - 2.0
    H = (y1 - y0) * sx * ex + HEAD + FOOT

    def X(t): return t * sx
    def Y(y): return HEAD + (y1 - y) * sx * ex

    g = _sv(W, H, "外周の展開図")
    lab = []
    for r in sorted(d["runs"], key=lambda r: tt(r["edge"], r["s0"])):
        ta = tt(r["edge"], r["s0"]); tb = tt(r["edge"], r["s1"])
        if tb < ta:
            tb += total
        xa, xb = X(ta), X(tb)
        h = nagH if r["kind"] == "Nagaya" else dob
        g.append(R(xa, Y(r["seat"] + h), xb - xa, h * sx * ex, fill=KC.get(r["kind"], "var(--dim)"), op=0.9))
        if r.get("nijukai"):
            g.append(R(xa, Y(r["seat"] + nagH + 2.6), 20 * 1.818 * sx, 2.6 * sx * ex,
                       fill=KC["Nagaya"], op=0.65))
            lab.append((xa, "門翼二階(海鼠壁)"))
        g.append(T((xa + xb) / 2, Y(r["seat"]) + 11, "%.1f" % r["seat"], "jo", "middle"))
        g.append(T((xa + xb) / 2, Y(r["seat"] + h) - 3, r["name"], "jo", "middle",
                   fit(r["name"], xb - xa, 9.0)))
    # 門・櫓
    for name, e, s, wd in ([("表門", d["gate"]["edge"], d["gate"]["s"], d["gate"]["plan"]["monW"] + 2 * d["gate"]["plan"]["sode"] + 2 * d["gate"]["plan"]["bansho"]["w"]),
                            ("御成門", d["onarimon"]["edge"], d["onarimon"]["s"], d["onarimon"]["w"])]
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
               "表長屋 桁高 %.1fm/練塀 %.2fm" % (nagH, dob), "anS2", "start"))
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
    # 嘉永期の正=冠木上の切妻小屋根(確度B)。写真(明治初)は屋根なし=代替形
    g.append('<polygon points="%s" fill="var(--ink-mid)" stroke="var(--ink)" stroke-width="1.2"/>'
             % " ".join("%.1f,%.1f" % p for p in [
                 (X(x - 0.9), Y(monH + 0.15)), (X(x + monW / 2), Y(monH + 1.05)),
                 (X(x + monW + 0.9), Y(monH + 0.15))]))
    g.append(T(X(x + monW / 2), Y(monH + 1.05) - 6,
               "切妻小屋根(嘉永期の正=B。写真の明治姿は屋根なし=A)", "anS2", "middle"))
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
        + d["onarimon"]["w"] * 1.5 + sum(k["w"] * 1.2 for k in d["komon"])
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

    def covered(u0, v0, u1, v1, y):
        uu = u0 + 0.25
        while uu < u1:
            vv = v0 + 0.25
            while vv < v1:
                ok = any(t["u0"] - eps <= uu <= t["u1"] + eps and
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
            d["gate"]["s"] + d["gate"]["plan"]["monW"] / 2 + d["gate"]["plan"]["sode"] + d["gate"]["plan"]["bansho"]["w"]),
           ("御成門", d["onarimon"]["edge"], d["onarimon"]["s"] - d["onarimon"]["w"] / 2,
            d["onarimon"]["s"] + d["onarimon"]["w"] / 2)]
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
        w = [x for x in d["terraceWalls"] if x["name"] == k["atWall"]][0]
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
    om = d["onarimon"]
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
             '(嘉永期の冠木上の屋根のみ B=類推)。御殿の構成は<b>類型(確度B)</b>、'
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
           "其十一", "其十二", "其十三", "其十四", "其十五"]
    _kn = [0]

    def nx():
        _kn[0] += 1
        return KAN[_kn[0] - 1]

    plate(h, nx(), "敷地", "%.0f m²(%.0f坪)/拝領11,942坪(出所未確定=?)/江戸間 1間=%.3fm/主郭グリッドは北辺沿いに24.49°回転"
          % (area, area / TSUBO, d["const"]["ken"]))
    fig(h, plan_svg(d),
        legend='<span style="color:var(--pl-omote)">■ 表郭 26.1</span>'
               '<span style="color:var(--pl-main)">■ 主平面 27.0</span>'
               '<span style="color:var(--pl-higashi)">■ 東上段 28.8</span>'
               '<span style="color:var(--pl-suso)">■ 堀端の裾 9.2(帯)</span>'
               '<span style="color:var(--pl-slope)">■ 斜面(造成しない・松+雑木の樹林)</span>'
               '<span style="color:var(--nagaya)">━ 表長屋</span>'
               '<span style="color:var(--hei)">━ 練塀</span>'
               '<span style="color:var(--take)">┄ 竹垣(法肩)</span>'
               '<span style="color:var(--ishi)">┄ 郭の土留め</span>'
               '<span>▪ 御殿の棟 ／ ▫ 付属屋</span>'
               '<span style="color:var(--shu)">● 表門 ／ ○ 御成門 ／ ■ 隅櫓 ／ ┄ 断面</span>',
        cap="<b>敷地は4つの水平面+2つの斜面。</b>造成も囲いもまず面から決め、"
            "囲いの天端=面の高さ、段は面の境にだけ立つ。"
            "<b>西斜面(溜池東岸)と南西の谷(岡部境)は造成しない</b> — 庭のまま、面の縁に竹垣。"
            "斜面は<b>黒松を疎に交えた雑木の樹林</b>(法肩=樹林／中部=低木／下部=草地の3帯)"
            "【確度B — 溜池の水辺の樹木は松、竹薮は江戸の水辺79事例中1例(其十一)】。"
            "北辺中央の鞍部だけ最大2.4mの盛土で、表長屋の石垣基壇が大通りへ露出する。"
            "<b>街路・隣地への影響はゼロ</b> — 面の造成は区画線で切り(図の色もその形)、"
            "境界の高低差は垂直の基壇石垣で受けるので、法尻が道や隣地へ出ることもない。")
    h.append(planes_table(d))
    h.append(slope_table(d))
    h.append('<p class="cap"><b>面のはみ出し検査(0.5間刻みの被覆): %s。</b>'
             '棟・付属屋・廊下は自分の y と同じ高さの段の中に、庭・井戸はいずれかの段の中に'
             '完全に載っていることを機械検査している(造成しない斜面に載る庭=西庭の斜面部だけ除外)。</p>'
             % ("<b>0 件</b>" if not pbad else "⚠ %d 件 — %s" % (len(pbad), " / ".join(pbad))))
    h.append("</div>")

    plate(h, nx(), "表向・御成 平面", "室名・畳数は【確度 ?】— 当屋敷の史料は散逸・類型からの想定")
    fig(h, goten_plan(d, -48, 68, -3, 36, "表向・御成 平面",
                      "廊下は入側・渡廊下とも幅一間で一定。能舞台は御成書院の広縁から白洲越しに観る"),
        legend='<span style="color:var(--roka)">■ 入側・渡廊下(幅一間)</span>'
               '<span style="color:var(--niwa)">■ 庭</span>'
               '<span style="color:var(--shirasu)">■ 白洲</span>'
               '<span>┄ 襖線(続き間の境)</span>',
        cap="<b>表門 → 白洲 → 石段(3段) → 御式台・御玄関</b>。東へ大広間・黒書院、西へ表役所(藩庁)。"
            "御成門からの御成道は白洲のまま御成玄関へ直進し、表と交わらない — "
            "<b>御成対応=能+風呂+専用門の3点セット</b>は家門・大藩の装置(福井図=同じ結城秀康系)。")
    h.append("</div>")

    plate(h, nx(), "中奥・奥向 平面", "室名・畳数は【確度 ?】/御書物之間・御時計之間は斉貴の嗜好(B)からの想定")
    fig(h, goten_plan(d, -16, 96, 31, 84, "中奥・奥向 平面",
                      "奥向へ入る廊下は御錠口の一本だけ。奥台所・長局はすべて錠の先にある"),
        legend='<span style="color:var(--roka)">■ 入側・渡廊下</span>'
               '<span style="color:var(--shu)">■ 御錠口</span>'
               '<span style="color:var(--niwa)">■ 庭</span>',
        cap="<b>大台所は敷地のほぼ中心</b>(西川1959)。中奥の御書物之間(鷹書)・御時計之間(西洋文物)は"
            "斉貴の嗜好からの想定の設え【確度 ?】。奥庭の<b>石井戸枠(慶長18年銘・約2m四方)は"
            "現存する実物</b>【存在=A/奥庭という位置=?】— 家康が駿府で使った物を直政が拝領して移した伝承。")
    h.append("</div>")

    plate(h, nx(), "東上段 平面", "御蔵・御蔵門。主郭+1.8m")
    fig(h, goten_plan(d, 58, 104, -2, 30, "東上段 平面",
                      "土蔵に入側も廊下も付けない(延焼を切る独立建物)。搬入は御蔵門から"),
        cap="東上段は主郭より石段6段(蹴上0.30)高い蔵前の平場。<b>土留め TW_HigashiW/S</b> が主郭側の縁で、"
            "石段 K_Higashi が唯一の内部動線。御作事小屋は石段下の主郭側に置き、蔵とは離す。")
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
    h.append('<p class="cap"><b>分母は敷地全体。</b>可建地に替えて数字を作らない。'
             '<b>大名上屋敷の建蔽率の史料値は [福井図] の5〜6割の一点しかなく</b>、当図はそれより'
             '大きく低い(広い拝領地・御成の白洲・奥庭・造成しない斜面の帰結)。'
             '原典に忠実な比較指標は<b>表長屋の規模比 %.1f%%</b>(表長屋 %.0fm / 外周 %.0fm)で、'
             '[追川2017] の実測帯(小浜 28.6%% 〜 尾張市谷 47.7%%)に収まる。'
             '<b>建蔽率は結果であって目標ではない</b> — 数字のために空地へ棟を足さない。</p>'
             % (100.0 * nagL / perim, nagL, perim))
    h.append("</div>")

    for s in d["sections"]:
        plate(h, nx(), s["name"], "%s = %g ／ 垂直%.1f倍" % (s["axis"], s["at"], s["vExag"]))
        fig(h, section_svg(d, s),
            cap="<b>段のつなぎ方は平面だけでは読めない。</b>地表下の色帯=面(其一と同じ色分け)。"
                "両端には区画線上の囲い(表長屋/練塀)を天端と基壇石垣つきで示す — 基壇は境界線上に"
                "垂直に立ち、道・隣地の地形には触れない。斜面(西・南西)は現地形のまま=庭。"
                "屋根は図示のための概略で、実装の高さは部材が決める(突き合わせの対象外)。")
        h.append("</div>")

    plate(h, nx(), "外周の展開", "天端は辺ごとに一本。段は門・頂点・郭境の延長線でのみ落とす")
    fig(h, perimeter_dev_svg(d))
    h.append(runs_table(d))
    h.append('<p class="cap">表長屋は<b>街路に面する北・東だけ</b>。南(土井境)・西(堀端通り)は練塀。'
             '土井境の囲いは1条・松平が持つ(区画トポロジの裁定)。犬走り %.2fm。</p>'
             % d["const"]["inubashiri"])
    h.append("</div>")

    plate(h, nx(), "表門まわり", "独立門(切妻小屋根=確度B)+両唐破風番所(写真=確度A)。屋根の確定はToMuCo原板の高精細確認待ち")
    fig(h, gate_svg(d),
        cap="<b>江戸東京博物館 温古写真集11「旧雲州松江藩松平候上屋敷門」(88005761・明治初撮影)から。</b>"
            "昭和14年時点の現存5大名門の一つで、東京大空襲で焼失。"
            "両唐破風番所は国持の格(加賀赤門・鳥取黒門と同格)。石垣畳出は親藩ゆえ制限外。"
            "台紙注記の「早くから撤去され」の解釈(屋根か否か)が未解決。")
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
