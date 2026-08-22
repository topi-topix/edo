#!/usr/bin/env python3
"""岡部筑前守上屋敷の指図を組む。

    python3 Tools/Sashizu/build_okabe_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/okabe_sashizu.json … 設計値の正典（人が書く）
    docs/Sashizu/okabe_kosho.md     … 文章の部（人が書く・現況形）

の二つだけで、それを一枚の HTML に組む。実装から指図を作ると
CLAUDE.md 絶対規則2「指図を先に起こす」の関門が消える（ユーザー指摘 2026-08-20）。

【流れ】
    1. 設計   docs/Sashizu/*.json / *.md を直す
    2. 組む   このスクリプト
    3. 検図   edo-kosho（史実）と edo-kenzu（図の成立）→ ユーザーのレビュー
    4. 実装   ビルダーの表を指図に合わせる
    5. 突合   Unity の「Edo ▸ 岡部筑前守上屋敷 ▸ 指図と実装を突き合わせる」で 0 件を確認
              建ててみて指図が誤りと分かったら **指図を直してから** 合わせ直す
    6. 経緯   コミットメッセージと git log。**指図には残さない**

数値は json にしか無い（この文書にも markdown にも写さない）ので、二重管理が起きない。

【図版 9 面】其一 敷地／其二 主郭 御殿平面／其三 西の下郭 平面／其四 棟と室(表)／
        其五 東西断面／其六 郭をまたぐ動線(平面+横断面)／其七 外周の展開／其八 郭の土留め(表)／
        其九 表門まわり／其十 隅。
        **座標は世界座標から Proj・Grid で直に変換する**ので図と実装がズレない。
        ⚠ 図番を振り直したら、ビルダーの注記が引いている図番も同時に振り直すこと
          (EdoOkabeYashikiBuilder.cs は 67 箇所で図番を引いている)。
"""
import json, math, os, re, subprocess, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "okabe_sashizu.json")
MD = os.path.join(DOC, "okabe_kosho.md")
OUT = os.path.join(DOC, "okabe_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown
def md2html(text):
    """指図の文章に要る分だけの最小変換（見出し・表・箇条書き・強調・コード）。"""
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
            lv = len(m.group(1))
            tag = {1: "h1", 2: "h2", 3: "h3", 4: "h4"}[lv]
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
    # 文章の側に手書きの <span class="cert"> が混じることがある。escape すると
    # タグが文字として出るうえ、下の【確度】の正規表現が二重に包む。先に外す。
    s = re.sub(r'</?span[^>]*>', "", s)
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"【([^】]*確度 ?[SABPU?][^】]*)】", r'<span class="cert">【\1】</span>', s)
    return s
# ---------------------------------------------------------------- 作図の土台
_SVN = [0]


def _sv(W, H, label):
    """SVG の殻。石垣のハッチ（この図だけの id）を defs に入れて返す。"""
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, label),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.65"/>'
            '</pattern></defs>' % _SVN[0]]


def _pat(): return "url(#pi%d)" % _SVN[0]


class Proj(object):
    """世界座標 → SVG px。**z は北が上**なので Y だけ反転する。

    図版はどれもこれ一つで座標を作る（図ごとに書くと図と実装がズレる）。"""

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

    def rect(self, x0, x1, z0, z1, **kw):
        return R(self.X(min(x0, x1)), self.Y(max(z0, z1)),
                 abs(self.X(x1) - self.X(x0)), abs(self.Y(z1) - self.Y(z0)), **kw)


class Grid(object):
    """間グリッドの指数 (u,v) → 世界座標。原点と向きは json の grid が持つ。"""

    def __init__(self, d, name):
        g = d["grid"][name]
        self.name, self.ken = name, d["const"]["ken"]
        self.x0, self.z0, self.du, self.dv = g["x0"], g["z0"], g["du"], g["dv"]
        self.u1, self.v1 = g["u1"], g["v1"]

    def X(self, u): return self.x0 + self.du * u * self.ken
    def Z(self, v): return self.z0 + self.dv * v * self.ken

    def box(self, o):
        """u0/v0/u1/v1（または x0/x1 のメートル直指定）→ 世界座標の (x0,x1,z0,z1)。"""
        if "x0" in o:
            xa, xb = o["x0"], o["x1"]
        else:
            xa, xb = self.X(o["u0"]), self.X(o["u1"])
        za, zb = self.Z(o["v0"]), self.Z(o["v1"])
        return min(xa, xb), max(xa, xb), min(za, zb), max(za, zb)

    def frame(self):
        xa, xb = self.X(0), self.X(self.u1)
        za, zb = self.Z(0), self.Z(self.v1)
        return min(xa, xb), max(xa, xb), min(za, zb), max(za, zb)


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
    """⚠ text-anchor は **style で出す**。クラス側の text-anchor:middle は CSS 規則なので
    presentation attribute（text-anchor="start"）より強く、属性で書くと効かない。
    左端の注記が中央寄せされて画面外へ切れる（2026-08-21 に実際に起きた）。"""
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
    """矩形の幅に収まる文字寸。室名は長短が激しいので必ず通す。"""
    return max(lo, min(base, wpx / (len(txt) * 0.62 + 0.8)))


DAN = {25.5: "var(--dan1)", 19.5: "var(--dan2)", 13.5: "var(--dan3)", 11.5: "var(--dan4)"}


# ---------------------------------------------------------------- 其一 敷地
def plan_svg(d):
    """敷地の平面。区画・段・外周の種別・郭の土留め・隅・門を一枚に。"""
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), 900.0, pad=12.0)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 敷地全体")

    for t in d["terraces"]:
        g.append(pr.rect(t["x0"], t["x1"], t["z0"], t["z1"],
                         fill=DAN.get(t["y"], "var(--dan4)"), op=0.65))
        g.append(T((pr.X(t["x0"]) + pr.X(t["x1"])) / 2, pr.Y(t["z1"]) + 13,
                   "%s %.1fm" % (TERR_JA.get(t["name"], t["name"]), t["y"]), "sl", "middle"))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    for i, p in enumerate(P):
        g.append('<circle cx="%.1f" cy="%.1f" r="2.4" fill="var(--ink)"/>' % (pr.X(p[0]), pr.Y(p[1])))
        g.append(T(pr.X(p[0]) + 5, pr.Y(p[1]) - 5, "P%d" % i, "jo"))

    kc = {"Tsuiji": "var(--hei)", "Nagaya": "var(--nagaya)", "Takegaki": "var(--take)"}
    for r in d["runs"]:
        a, b = r["a"], r["b"]
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]),
                    kc.get(r["kind"], "var(--dim)"), 5, cap="round"))
    for w in d["terraceWalls"]:
        a, b = w["a"], w["b"]
        g.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]), "var(--ishi)", 3, dash="7 4"))

    # 御殿の輪郭 — 郭の中がどれだけ埋まっているかは配置図でしか読めない
    for gn in ("shukaku", "shimo"):
        gr = Grid(d, gn)
        for m in d["munes"]:
            if m["grid"] != gn:
                continue
            x0, x1, z0, z1 = gr.box(m)
            g.append(pr.rect(x0, x1, z0, z1, fill="var(--ink-mid)", stroke="var(--ink)", sw=0.5, op=0.85))

    for c in d["corners"]:
        g.append('<circle cx="%.1f" cy="%.1f" r="7" fill="none" stroke="var(--shu)" stroke-width="2"/>'
                 % (pr.X(c["v"][0]), pr.Y(c["v"][1])))
    for y in d["yagura"]:
        g.append(R(pr.X(y["pos"][0]) - 4.5, pr.Y(y["pos"][1]) - 4.5, 9, 9, fill="var(--shu)"))
    gp = d["gate"]["pos"]
    g.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--shu)"/>' % (pr.X(gp[0]), pr.Y(gp[1])))
    g.append(T(pr.X(gp[0]) + 9, pr.Y(gp[1]) + 4, "表門", "sr"))
    for s in d["sections"]:
        y = pr.Y(s["at"])
        g.append(LN(0, y, pr.W, y, "var(--shu)", 0.9, dash="9 5", op=0.8))
        g.append(T(4, y - 6, "%s（%s=%.0f）" % (s["name"], s["axis"], s["at"]), "sr", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其二・其三 御殿平面
def goten_plan(d, gname, label):
    """郭の御殿平面。棟の外形＋入側の帯 → 身舎 → 襖線で割った続き間（室名・畳数）。

    廊下は**室群の外周を巡る入側**で、群と群は渡廊下で結ぶ。中央を貫く通路は描かない
    （明治以降の中廊下型になる）。庭は建屋と囲いの**間に残る面**として置く。"""
    gr = Grid(d, gname)
    fx0, fx1, fz0, fz1 = gr.frame()
    pr = Proj(fx0, fx1, fz0, fz1, 900.0, pad=6.0, top=26.0, bottom=18.0)
    g = _sv(pr.W, pr.H, "岡部筑前守上屋敷 %s" % label)
    K = gr.ken

    # 段（郭の地盤）を下敷きに
    for t in d["terraces"]:
        if t["x1"] < fx0 or t["x0"] > fx1 or t["z1"] < fz0 or t["z0"] > fz1:
            continue
        ta, tb = max(t["x0"], fx0 - 6), min(t["x1"], fx1 + 6)
        g.append(pr.rect(ta, tb, max(t["z0"], fz0 - 6), min(t["z1"], fz1 + 6),
                         fill=DAN.get(t["y"], "var(--dan4)"), op=0.75))
        if pr.L(tb - ta) > 40:
            g.append(T((pr.X(ta) + pr.X(tb)) / 2, pr.H - 30,
                       "%s %.1fm" % (TERR_JA.get(t["name"], t["name"]), t["y"]), "anS", "middle"))
    g.append(pr.rect(fx0, fx1, fz0, fz1, fill="none", stroke="var(--ink)", sw=2.0))

    # 庭 — 建屋と囲いの間に残る面
    for n in d["gardens"]:
        if n["grid"] != gname:
            continue
        x0, x1, z0, z1 = gr.box(n)
        g.append(pr.rect(x0, x1, z0, z1, fill="var(--niwa)", stroke="var(--ink)", sw=0.8))
        g.append(T((pr.X(x0) + pr.X(x1)) / 2, (pr.Y(z0) + pr.Y(z1)) / 2 + 4, n["label"], "rmS"))

    # 郭の土留めと石段（郭の縁がどこかを平面でも示す）
    for w in d["terraceWalls"]:
        ax, az, bz = w["a"][0], w["a"][1], w["b"][1]
        if ax < fx0 - 8 or ax > fx1 + 8:
            continue
        g.append(pr.rect(ax - 1.2, ax + 1.2, max(min(az, bz), fz0), min(max(az, bz), fz1),
                         fill=_pat(), stroke="var(--ishi)", sw=1.0))
    for k in d["kaidans"]:
        if min(k["xTop"], k["xBot"]) > fx1 or max(k["xTop"], k["xBot"]) < fx0:
            continue
        if k["z1"] < fz0 or k["z0"] > fz1:
            continue
        g.append(pr.rect(min(k["xTop"], k["xBot"]), max(k["xTop"], k["xBot"]), k["z0"], k["z1"],
                         fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0, dash="5 3"))
        g.append(T((pr.X(k["xTop"]) + pr.X(k["xBot"])) / 2, pr.Y(k["z1"]) - 4,
                   "%s %d段" % (k["name"].replace("Ishidan_", "石段 "), k["steps"]), "anS2", "middle"))

    # 廊下（入側の帯 = 棟の外形、渡廊下・外廊下・取り付き）
    for l in d["links"]:
        if l["grid"] != gname:
            continue
        x0, x1, z0, z1 = gr.box(l)
        col = "var(--shu)" if l["kind"] == "御錠口" else "var(--roka)"
        g.append(pr.rect(x0, x1, z0, z1, fill=col))
    for m in d["munes"]:
        if m["grid"] != gname:
            continue
        x0, x1, z0, z1 = gr.box(m)
        g.append(pr.rect(x0, x1, z0, z1, fill="var(--roka)"))

    # 棟 — 身舎と続き間
    for m in d["munes"]:
        if m["grid"] != gname:
            continue
        mu0, mv0, mu1, mv1 = m["u0"] + 1, m["v0"] + 1, m["u1"] - 1, m["v1"] - 1
        bx0, bx1 = sorted((gr.X(mu0), gr.X(mu1)))
        bz0, bz1 = sorted((gr.Z(mv0), gr.Z(mv1)))
        g.append(pr.rect(bx0, bx1, bz0, bz1, fill="var(--ink-mid)", stroke="var(--ink)", sw=1.6))
        seen = set()
        for r in m["rooms"]:
            for u in (r["u0"], r["u1"]):                       # 襖線（縦）
                if u in (mu0, mu1) or ("u", u, r["v0"], r["v1"]) in seen:
                    continue
                seen.add(("u", u, r["v0"], r["v1"]))
                g.append(LN(pr.X(gr.X(u)), pr.Y(gr.Z(r["v0"])), pr.X(gr.X(u)), pr.Y(gr.Z(r["v1"])),
                            "var(--ink)", 0.8, dash="5 3"))
            for v in (r["v0"], r["v1"]):                       # 襖線（横）
                if v in (mv0, mv1) or ("v", v, r["u0"], r["u1"]) in seen:
                    continue
                seen.add(("v", v, r["u0"], r["u1"]))
                g.append(LN(pr.X(gr.X(r["u0"])), pr.Y(gr.Z(v)), pr.X(gr.X(r["u1"])), pr.Y(gr.Z(v)),
                            "var(--ink)", 0.8, dash="5 3"))
            rx0, rx1 = sorted((gr.X(r["u0"]), gr.X(r["u1"])))
            rz0, rz1 = sorted((gr.Z(r["v0"]), gr.Z(r["v1"])))
            cx, cy = (pr.X(rx0) + pr.X(rx1)) / 2, (pr.Y(rz0) + pr.Y(rz1)) / 2
            fs = fit(r["name"], pr.L(rx1 - rx0) - 6, 12.0)
            g.append(T(cx, cy - 1, r["name"], "rmS", "middle", fs))
            g.append(T(cx, cy + 12, "%d畳" % r["tatami"], "jo", "middle"))
        # 棟名は外形の外へ
        g.append(T((pr.X(x0 if False else gr.X(m["u0"])) + pr.X(gr.X(m["u1"]))) / 2,
                   pr.Y(max(gr.Z(m["v0"]), gr.Z(m["v1"]))) - 5, MUNE_JA.get(m["name"], m["name"]), "mu", "middle"))

    # 付属屋 — 土蔵・物置には入側も廊下も付かない（延焼を切るための独立建物）
    for s in d.get("service", []):
        if s["x1"] < fx0 or s["x0"] > fx1 or s["z1"] < fz0 or s["z0"] > fz1:
            continue
        g.append(pr.rect(s["x0"], s["x1"], s["z0"], s["z1"],
                         fill="var(--ink-lo)", stroke="var(--ink)", sw=1.2))
        g.append(T((pr.X(s["x0"]) + pr.X(s["x1"])) / 2, (pr.Y(s["z0"]) + pr.Y(s["z1"])) / 2 + 4,
                   s["label"], "rmS", "middle", 11.0))

    # 表向 / 中奥 / 奥向 — 境に御錠口
    if gname == "shukaku":
        for zn in ("表向", "中奥", "奥向"):
            us = [(m["u0"] + m["u1"]) / 2.0 for m in d["munes"]
                  if m["grid"] == gname and m["zone"] == zn]
            if us:
                g.append(T(pr.X(gr.X(sum(us) / len(us))), 17, zn, "zn", "middle"))
    g.append(T(pr.W - 6, 15, "北 ↑　左＝西（溜池） ／ 右＝東（三べ坂）", "anS", "end"))
    g.append(T(4, pr.H - 5, "廊下は入側・渡廊下・外廊下とも幅一間で一定。"
                            "群と群は渡廊下で結び、中央を貫く通路は作らない", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


TERR_JA = {"Shukaku": "主郭", "TE": "東中段", "Monzen": "門前", "Chudan": "中段", "TW1": "西低地"}

MUNE_JA = {
    "Genkan": "玄関棟", "Ohiroma": "大広間棟", "Shoin": "書院棟", "Nakaoku": "中奥棟",
    "Daidokoro": "台所棟", "Okumuki": "奥向棟", "Nagatsubone": "長局棟",
    "Katte": "勝手棟", "ShimoGoten": "下御殿棟", "Yudono": "湯殿棟", "Jochu": "女中部屋棟",
    "Goyobeya": "御用部屋棟", "NagatsuboneW": "長局棟（西）",
}


# ---------------------------------------------------------------- 其五 東西断面
def _cross_z(seg, at):
    """線分が z=at を横切る x。横切らなければ None。"""
    (ax, az), (bx, bz) = seg
    if (az - at) * (bz - at) > 0 or az == bz:
        return None
    return ax + (bx - ax) * (at - az) / (bz - az)


def _boundary(d, at):
    """断面線が**敷地の区画線**を横切る位置と、そこの地盤。西端・東端を返す。

    ⚠ run で拾ってはいけない。門の開口では run が切れているので、東端が拾えず
    西の run の天端（竹垣 8.0）を東端に当ててしまう。区画線で拾い、地盤は
    その点にいちばん近い run の top を使う。"""
    P = d["polygon"]
    hit = []
    for i in range(len(P)):
        x = _cross_z((P[i], P[(i + 1) % len(P)]), at)
        if x is not None:
            hit.append(x)
    hit.sort()
    if not hit:
        return None, None

    def top_at(x):
        best, bt = 1e18, 13.5
        for r in d["runs"]:
            for p in (r["a"], r["b"]):
                dd = (p[0] - x) ** 2 + (p[1] - at) ** 2
                if dd < best:
                    best, bt = dd, r["top"]
        return bt
    return (hit[0], top_at(hit[0])), (hit[-1], top_at(hit[-1]))


def _ground(d, at):
    """断面線 z=at の地盤。段の矩形と郭の土留めの位置から作る。

    段の矩形は石垣の体内へ 1.4m 食い込ませてあるので、**境目は土留めの芯**で取る
    （矩形の重なりを跨いで max を取ると段が 1.4m 早く立ち上がる）。"""
    ts = [t for t in d["terraces"] if t["z0"] <= at <= t["z1"]]
    cuts = sorted(w["a"][0] for w in d["terraceWalls"]
                  if min(w["a"][1], w["b"][1]) <= at <= max(w["a"][1], w["b"][1]))
    lo = min(t["x0"] for t in ts); hi = max(t["x1"] for t in ts)
    edges = [lo] + cuts + [hi]
    out = []
    for a, b in zip(edges, edges[1:]):
        mid = (a + b) / 2.0
        lv = [t["y"] for t in ts if t["x0"] <= mid <= t["x1"]]
        if lv:
            out.append((a, b, max(lv)))
    return out


def section_svg(d, sec):
    """東西断面。段のつなぎ方（石垣・石段・開口）は平面だけでは読めないので必須の一枚。"""
    at, ex = sec["at"], sec["vExag"]
    west, east = _boundary(d, at)
    gnd = _ground(d, at)
    x0 = min(west[0], gnd[0][0]) - 14
    x1 = max(east[0], gnd[-1][1]) + 14
    W = 900.0
    sx = W / (x1 - x0)
    ytop, ybot = 33.0, 4.0
    HEAD, FOOT = 24.0, 40.0
    H = (ytop - ybot) * sx * ex + HEAD + FOOT

    def X(v): return (v - x0) * sx
    def Y(v): return HEAD + (ytop - v) * sx * ex

    g = _sv(W, H, "岡部筑前守上屋敷 %s" % sec["name"])
    # 地盤の折れ線。段の落ち口は**盛土の法面**で結ぶ — 石段はその上に載るので、
    # 垂直な崖のまま描くと段が宙に浮いて「石垣の厚みでは降りられない」が図に出ない。
    prof = []
    for a, b, y in gnd:
        prof.append((max(a, west[0]), y))
        prof.append((min(b, east[0]), y))
    for k in d["kaidans"]:
        if not (k["z0"] <= at <= k["z1"]):
            continue
        lo, hi = sorted((k["xTop"], k["xBot"]))
        prof = [(px, py) for px, py in prof if not (lo - 1e-6 < px < hi + 1e-6)]
        prof += [(k["xTop"], k["yTop"]), (k["xBot"], k["yBot"])]
    prof.sort()
    pts = [(X(x0), Y(ybot)), (X(west[0]), Y(west[1]))]
    pts += [(X(px), Y(py)) for px, py in prof]
    pts += [(X(east[0]), Y(east[1])), (X(x1), Y(ybot))]
    g.append('<polygon points="%s" fill="var(--dan)" stroke="var(--ink)" stroke-width="1.4"/>'
             % " ".join("%.1f,%.1f" % p for p in pts))
    for a, b, y in gnd:
        g.append(T((X(a) + X(b)) / 2, Y(y) + 15, "%.1f m" % y, "anS", "middle"))

    # 郭の土留め — 断面線が開口に当たる run は石段が通るので、石垣は奥に見えるものとして破線
    for w in d["terraceWalls"]:
        if not (min(w["a"][1], w["b"][1]) <= at <= max(w["a"][1], w["b"][1])):
            continue
        h, bt = 4.0 * w["s"], 2.4 * w["s"]        # 壁高 / 底厚。どちらも s に比例する
        wx = w["a"][0]
        # 躯体は**全部が低い側**に出る（芯線を跨がない）。低い側は段の高い方の反対。
        lowest = min(y for _, _, y in gnd) if gnd else 0
        east_hi = any(a <= wx - 1 <= b and y >= w["coping"] - 0.01 for a, b, y in gnd)
        sgn = 1.0 if east_hi else -1.0            # 高い側が西なら躯体は東へ
        opened = "gapZ" in w and abs(at - w["gapZ"]) <= w.get("gapHalf", 0)
        g.append(R(X(min(wx, wx + sgn * bt)), Y(w["coping"]), sx * bt, h * sx * ex,
                   fill="none" if opened else _pat(), stroke="var(--ishi)",
                   sw=1.2, dash="4 3" if opened else None))
        g.append(T(X(wx + sgn * bt / 2), Y(w["coping"]) - 6,
                   "%s s=%g" % (w["name"], w["s"]), "jo", "middle"))

    # 石段 — 開口の中を降りる
    for k in d["kaidans"]:
        if not (k["z0"] <= at <= k["z1"]):
            continue
        g.append(LN(X(k["xTop"]), Y(k["yTop"]), X(k["xBot"]), Y(k["yBot"]), "var(--shu)", 2.6))
        g.append(T((X(k["xTop"]) + X(k["xBot"])) / 2 + 6, Y((k["yTop"] + k["yBot"]) / 2) + 14,
                   "%d段 走り%.1fm" % (k["steps"], k["run"]), "anG", "middle"))

    # 棟 — 断面線に掛かる棟だけ
    eave, ridge = sec["eaveAbove"], sec["ridgeAbove"]
    fl = d["const"]["gotenFloor"]
    for m in d["munes"]:
        gr = Grid(d, m["grid"])
        bx0, bx1, bz0, bz1 = gr.box(m)
        if not (bz0 <= at <= bz1):
            continue
        f = m["y"] + fl
        g.append('<polygon points="%s" fill="var(--ink-mid)" stroke="var(--ink)" stroke-width="1.2"/>'
                 % " ".join("%.1f,%.1f" % p for p in
                            [(X(bx0), Y(f)), (X(bx0), Y(f + eave)),
                             ((X(bx0) + X(bx1)) / 2, Y(f + ridge)),
                             (X(bx1), Y(f + eave)), (X(bx1), Y(f))]))
        g.append(T((X(bx0) + X(bx1)) / 2, Y(f + eave) + 13,
                   MUNE_JA.get(m["name"], m["name"]), "rmS", "middle",
                   fit(MUNE_JA.get(m["name"], m["name"]), sx * (bx1 - bx0) - 4, 11.0)))
    # 御錠口 — 表と奥の結界がどこに立つか
    for l in d["links"]:
        if l["kind"] != "御錠口":
            continue
        gr = Grid(d, l["grid"]); bx0, bx1, bz0, bz1 = gr.box(l)
        if bz0 <= at <= bz1:
            g.append(LN((X(bx0) + X(bx1)) / 2, Y(l["y"]), (X(bx0) + X(bx1)) / 2, Y(l["y"] + ridge + 1.5),
                        "var(--shu)", 1.6, dash="4 3"))
            g.append(T((X(bx0) + X(bx1)) / 2, Y(l["y"] + ridge + 1.5) - 4, "御錠口", "anG", "middle"))

    # 表門
    gp = d["gate"]["pos"]
    if abs(gp[1] - at) < (d["gate"]["plan"]["measured"]["mon"]["yane"]["o"][1] - d["gate"]["plan"]["measured"]["mon"]["yane"]["o"][0]):
        gy = east[1]                       # 表門の辺の地盤。run の top から来る
        g.append(R(X(gp[0]) - sx * _gmonD(d) / 2, Y(gy + _gmonH(d)),
                   sx * _gmonD(d), _gmonH(d) * sx * ex,
                   fill="var(--shu-lo)", stroke="var(--shu)", sw=1.6))
        g.append(T(X(gp[0]), Y(gy + _gmonH(d)) - 5, "表門", "anG", "middle"))

    g.append(T(4, 15, "西（溜池）", "anS"))
    g.append(T(W - 4, 15, "東（三べ坂）", "anS", "end"))
    g.append(T(4, H - 22, "水平 約 1/%.0f ／ 垂直は %.1f 倍に強調" % (scale1(sx), ex), "anS2", "start"))
    g.append(T(4, H - 7, "落差 6.0m は蹴上 0.30m で 20 段、踏面 0.45m なら走り 9.0m。"
                         "石垣の厚み 2.4m の中では降りられないので、段は開口の外の法面に載る", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其六 郭をまたぐ動線
def kaidan_svg(d):
    """西の登廊 W1／W2 の平面。石段は盛土の法面に載り、階段廊下はその南を懸造りで降りる。"""
    K = d["const"]["ken"]
    ks = [k for k in d["kaidans"] if k.get("noboriro")]
    nb = []
    for k in ks:
        sg = 1.0 if k["xBot"] > k["xTop"] else -1.0
        top = k["xTop"] + sg * k["odoriKen"] * K
        nb.append((k, top, top + (k["xBot"] - k["xTop"])))
    x0 = min(min(n[2], n[0]["xBot"]) for n in nb) - 8
    x1 = max(k["xTop"] for k in ks) + 8
    pr = Proj(x0, x1, 1036.0, 1053.0, 900.0, top=22.0, bottom=26.0)
    g = _sv(pr.W, pr.H, "郭をまたぐ動線 平面")

    for t in d["terraces"]:
        if t["x1"] < x0 or t["x0"] > x1:
            continue
        g.append(pr.rect(max(t["x0"], x0), min(t["x1"], x1), 1036.0, 1053.0,
                         fill=DAN.get(t["y"], "var(--dan4)"), op=0.55))
        g.append(T((pr.X(max(t["x0"], x0)) + pr.X(min(t["x1"], x1))) / 2, pr.Y(1052.2),
                   "%s %.1fm" % (TERR_JA.get(t["name"], t["name"]), t["y"]), "anS", "middle"))
    # 郭の土留めと開口
    for w in d["terraceWalls"]:
        wx = w["a"][0]
        if wx < x0 or wx > x1:
            continue
        for za, zb in ((1036.0, w["gapZ"] - w["gapHalf"]), (w["gapZ"] + w["gapHalf"], 1053.0)):
            g.append(pr.rect(wx - 1.2, wx + 1.2, za, zb, fill=_pat(), stroke="var(--ishi)", sw=1.0))
        g.append(T(pr.X(wx), pr.Y(1037.0), w["name"], "jo", "middle"))
        g.append(T(pr.X(wx), pr.Y(1051.0), "開口 %.1fm" % (w["gapHalf"] * 2), "anS2", "middle"))

    # 取り付きの廊下 — 登廊より先に敷く（後だと登廊の注記を覆う）
    for l in d["links"]:
        if l["kind"] != "取り付き":
            continue
        gr = Grid(d, l["grid"]); bx0, bx1, bz0, bz1 = gr.box(l)
        if bx1 < x0 or bx0 > x1:
            continue
        g.append(pr.rect(bx0, bx1, bz0, bz1, fill="var(--roka)", op=0.85))

    st, sf = d["const"]["sakaT"], d["const"]["stepW"]
    for k, ntop, nbot in nb:
        zc = (k["z0"] + k["z1"]) / 2.0
        xa, xb = sorted((k["xTop"], k["xBot"]))
        # 盛土の法面（平場）と、その両脇の坂の土留め
        g.append(pr.rect(xa, xb, zc - k["noriHalf"], zc + k["noriHalf"],
                         fill="var(--shu-lo)", stroke="var(--ink)", sw=0.8, dash="4 3"))
        for s in (-1, 1):
            g.append(pr.rect(xa, xb, zc + s * k["noriHalf"], zc + s * (k["noriHalf"] + st),
                             fill=_pat(), stroke="var(--ishi)", sw=1.0))
        # 屋外の石段（法面の芯そのもの）
        g.append(pr.rect(xa, xb, zc - sf / 2, zc + sf / 2,
                         fill="var(--ink-lo)", stroke="var(--ink)", sw=1.2))
        g.append(T((pr.X(xa) + pr.X(xb)) / 2, pr.Y(zc) + 4,
                   "屋外の石段 幅%.2f・%d段" % (sf, k["steps"]), "anS2", "middle"))
        # 階段廊下（登廊）— 盛土に載せず、南を柱で降りる（懸造り）
        zn = d["const"]["noboriZC"]
        na, nb2 = sorted((ntop, nbot))
        g.append(pr.rect(na, nb2, zn - K / 2, zn + K / 2,
                         fill="var(--roka)", stroke="var(--ink)", sw=1.2))
        g.append(T((pr.X(na) + pr.X(nb2)) / 2, pr.Y(zn + K / 2) - 5,
                   "登廊 %s（懸造り）" % k["noboriro"], "anS2", "middle"))
        g.append(pr.rect(min(k["xTop"], ntop), max(k["xTop"], ntop), zn - K / 2, zn + K / 2,
                         fill="none", stroke="var(--shu)", sw=1.4))
        g.append(T((pr.X(k["xTop"]) + pr.X(ntop)) / 2, pr.Y(zn - K / 2) + 13,
                   "踊り場 %d間" % k["odoriKen"], "anG", "middle"))
    g.append(T(4, 15, "平面（北が上）", "anS"))
    g.append(T(4, pr.H - 16, "石段は**盛土の法面**に載り、両脇を「坂の土留め」で留める。"
                             "階段廊下はその南、柱で宙に浮いて降りる（懸造り）", "anS2", "start"))
    g.append(T(4, pr.H - 3, "踊り場は石垣の法尻まで水平に渡ってから降り始める。"
                            "床は坂上で天端 +%.2f しかなく、そのまま降りると天端より下へ潜る"
               % d["const"]["gotenFloor"], "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


def kaidan_section_svg(d):
    """登廊の横断面（走りに直交して見る）。石段・土留め・懸造りの関係を一枚に。"""
    k = [x for x in d["kaidans"] if x.get("noboriro") == "W1"][0]
    K, st = d["const"]["ken"], d["const"]["sakaT"]
    zc, zn = (k["z0"] + k["z1"]) / 2.0, d["const"]["noboriZC"]
    z0, z1 = zn - 4.0, zc + k["noriHalf"] + st + 2.0
    W, ex = 760.0, 1.0
    sx = W / (z1 - z0)
    y0, y1 = 20.0, 26.6
    HEAD = 20.0
    H = (y1 - y0) * sx * ex + HEAD + 52

    def X(z): return (z - z0) * sx
    def Y(y): return HEAD + (y1 - y) * sx * ex

    g = _sv(W, H, "登廊 W1 横断面")
    ymid = (k["yTop"] + k["yBot"]) / 2.0
    # 盛土（法面）とその両脇の土留め
    g.append('<polygon points="%s" fill="var(--dan)" stroke="var(--ink)" stroke-width="1.2"/>'
             % " ".join("%.1f,%.1f" % p for p in [
                 (X(z0), Y(y0)), (X(zc - k["noriHalf"] - st - 1.5), Y(y0)),
                 (X(zc - k["noriHalf"] - st), Y(ymid)), (X(zc + k["noriHalf"] + st), Y(ymid)),
                 (X(zc + k["noriHalf"] + st + 1.5), Y(y0)), (X(z1), Y(y0))]))
    for s in (-1, 1):
        a = zc + s * k["noriHalf"]
        b = zc + s * (k["noriHalf"] + st)
        g.append(R(X(min(a, b)), Y(ymid + 0.9), abs(X(b) - X(a)), 0.9 * sx * ex + 6,
                   fill=_pat(), stroke="var(--ishi)", sw=1.2))
    g.append(T(X(zc + k["noriHalf"] + st / 2), Y(ymid + 0.9) - 6, "坂の土留め 厚%.2f" % st, "anS2", "middle"))
    sw_ = d["const"]["stepW"]
    g.append(R(X(zc - sw_ / 2), Y(ymid + 0.3), sw_ * sx, 0.3 * sx * ex + 4,
               fill="var(--ink-lo)", stroke="var(--ink)", sw=1.2))
    g.append(T(X(zc), Y(ymid + 0.3) - 7, "屋外の石段 %.2f" % sw_, "anS2", "middle"))
    g.append(LN(X(zc - k["noriHalf"]), Y(ymid) + 16, X(zc + k["noriHalf"]), Y(ymid) + 16, "var(--dim)", 0.8))
    g.append(T(X(zc), Y(ymid) + 29, "平場 %.2fm（芯 ± %.2f）" % (k["noriHalf"] * 2, k["noriHalf"]), "anS2", "middle"))

    # 懸造りの登廊 — 床は盛土に載らず柱で立つ
    fy = ymid + 0.62
    g.append(R(X(zn - K / 2), Y(fy), K * sx, 0.35 * sx * ex + 3,
               fill="var(--roka)", stroke="var(--ink)", sw=1.2))
    for s in (-1, 1):                                    # 床を支える柱（地面まで）
        px = X(zn + s * (K / 2 - 0.25))
        g.append(LN(px, Y(fy), px, Y(y0), "var(--ink)", 2.2))
    for s in (-1, 1):                                    # 屋根を受ける柱
        px = X(zn + s * (K / 2 - 0.15))
        g.append(LN(px, Y(fy), px, Y(fy + 1.55), "var(--ink)", 1.6))
    g.append(T(X(zn - K / 2) - 8, Y((fy + y0) / 2), "柱（懸造り）", "anS2", "end"))
    ey, ry = fy + 1.55, fy + 2.503
    g.append('<polygon points="%s" fill="var(--ishi)" opacity="0.85"/>'
             % " ".join("%.1f,%.1f" % p for p in [
                 (X(zn - K / 2 - 0.6), Y(ey)), (X(zn + K / 2 + 0.6), Y(ey)),
                 (X(zn + 0.2), Y(ry)), (X(zn - 0.2), Y(ry))]))
    g.append(T(X(zn), Y(ry) - 5, "登廊の屋根", "anS2", "middle"))
    g.append(T(X(zn), Y(fy) + 16, "階段廊下 幅一間", "anS2", "middle"))
    g.append(T(4, 14, "横断面（走りに直交して見る・垂直は等倍）", "anS"))
    g.append(T(4, H - 18, "**木階段は盛土の坂に載せない。** 法面は石階段だけのもので、"
                          "階段廊下はその南を柱で降りる", "anS2", "start"))
    g.append(T(4, H - 4, "階段廊下の芯 z は下郭のマス目にスナップして**絶対値で持つ**。"
                         "法面の芯を動かしてもここは動かさない — 取り付きの廊下を全部引き直すことになる",
               "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其七 外周の展開図
def _perim_t(d):
    """敷地の周長にそった走り t。run の端点を多角形の辺へ射影して求める。"""
    P = d["polygon"]
    n = len(P)
    tv, acc = [0.0], 0.0
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        acc += math.hypot(b[0] - a[0], b[1] - a[1])
        tv.append(acc)

    def t_of(p):
        best, bt = 1e18, 0.0
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz
            u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
            qx, qz = a[0] + dx * u, a[1] + dz * u
            dd = (p[0] - qx) ** 2 + (p[1] - qz) ** 2
            if dd < best:
                best, bt = dd, tv[i] + math.sqrt(L2) * u
        return bt
    return tv, t_of, acc


def perimeter_dev_svg(d):
    """外周を一直線に伸ばした展開図。地盤・天端・足元の石垣・段の落ちを一枚に。

    **展開の起点は表門。** P0 から巻くと、P0 に端点を持つ run が展開の両端に割れる
    （区画線の折り返しで走りが 0 と全長のどちらにも射影されるため）。表門の開口には
    run が無いので、そこを切れ目にすれば一本も割れない。

    総築地塀なので**段は塀が段違いで越える**。長屋は床から棟まで一体の反復モジュールで
    段を跨げないが、築地塀の笠は切妻状で、留め継ぎで折れ段違いで落とせる。"""
    tv, t_of, total = _perim_t(d)
    t0 = t_of(d["gate"]["pos"])

    def tt(p):
        return (t_of(p) - t0) % total

    W, ex = 1120.0, 7.5
    HEAD, FOOT = 34.0, 58.0
    sx = W / total
    dob = d["const"]["dobeiH"]
    tops = [r["seat"] + dob for r in d["runs"]]
    bots = [r["seat"] - 4 * float(r["wall"].partition(" s=")[2]) for r in d["runs"] if r.get("wall")]
    y1 = max(tops) + 1.0
    y0 = min(min(r["top"] for r in d["runs"]), min(bots)) - 1.0
    H = (y1 - y0) * sx * ex + HEAD + FOOT

    def X(t): return t * sx

    def Y(y): return HEAD + (y1 - y) * sx * ex

    g = _sv(W, H, "外周の展開図")
    kc = {"Tsuiji": "var(--hei)", "Takegaki": "var(--take)"}
    lab = []
    for r in sorted(d["runs"], key=lambda r: tt(r["a"])):
        ta, tb = sorted((tt(r["a"]), tt(r["b"])))
        xa, xb = X(ta), X(tb)
        if r.get("wall"):
            nm, _, sv = r["wall"].partition(" s=")
            hs = 4.0 * float(sv)
            g.append(R(xa, Y(r["seat"]), xb - xa, hs * sx * ex,
                       fill=_pat(), stroke="var(--ishi)", sw=0.9))
            lab.append((xa, xb, Y(r["seat"] - hs) + 11, "%s s=%s" % (nm, sv), "jo"))
        g.append(R(xa, Y(r["seat"] + dob), xb - xa, dob * sx * ex,
                   fill=kc.get(r["kind"], "var(--dim)"), op=0.9))
        g.append(LN(xa, Y(r["top"]), xb, Y(r["top"]), "var(--shu)", 1.2, dash="5 4", op=0.85))
        lab.append((xa, xb, Y(r["seat"] + dob) - 5, r["name"], "jo"))
    # ラベルは幅が足りるものだけ。潰れた文字を重ねるくらいなら出さない
    for xa, xb, y, txt, cls in lab:
        if xb - xa >= len(txt) * 4.6:
            g.append(T((xa + xb) / 2, y, txt, cls, "middle"))

    for i, p in enumerate(d["polygon"]):
        x = X(tt(p))
        g.append(LN(x, HEAD - 10, x, H - FOOT, "var(--rule)", 0.8))
        g.append(T(x + 2, HEAD - 14, "P%d" % i, "jo"))
    for x, t in ((0.0, "表門"), (W, "表門")):
        g.append(LN(x, HEAD - 10, x, H - FOOT, "var(--shu)", 1.6))
    g.append(T(6, HEAD - 14, "表門", "sr"))
    g.append(T(W - 6, HEAD - 14, "表門", "sr", "end"))

    # 段の落ちる位置 — 隣り合う run の天端が変わるところ
    # ⚠ run は端点を走りと逆向きに持つ（tt(a) > tt(b)）ので、
    #   隣り合う run の継ぎ目は **後ろの run の b 側**。a を使うと反対端に線が出る。
    rs = sorted(d["runs"], key=lambda r: tt(r["a"]))
    for i in range(1, len(rs)):
        pv, cu = rs[i - 1], rs[i]
        if abs(pv["seat"] - cu["seat"]) > 0.01:
            x = X(min(tt(cu["a"]), tt(cu["b"])))
            g.append(LN(x, Y(min(pv["seat"], cu["seat"])), x, Y(max(pv["seat"], cu["seat"]) + dob),
                        "var(--shu)", 2.4))
    # ---- 門・番所も囲いの一部。run が無いだけで穴ではない ----
    # 表門の位置を展開の t へ。門は展開の起点なので 0 と total の両端に割れる。
    gp = d["gate"]["plan"]
    occupied = []                                   # (t0, t1, 天端, ラベル) 展開座標
    occupied_spans = []                             # 実際に描いた帯（穴の判定に使う）
    kb = gp["measured"]["monParts"]["kabe"]["t"]     # 門の小壁＝塀が突き当たる面
    ban = gp["bansho"]
    # 東辺の run 座標 t → 展開座標。**推測せず、点を世界座標へ戻して射影する。**
    P0e, P10e = d["polygon"][0], d["polygon"][10]
    _dx, _dz = P10e[0] - P0e[0], P10e[1] - P0e[1]
    _L = math.hypot(_dx, _dz)
    _u = (_dx / _L, _dz / _L)
    _G = d["gate"]["pos"]
    def dev(t_run):
        return tt((_G[0] + _u[0] * t_run, _G[1] + _u[1] * t_run))
    occupied.append((dev(kb), dev(-kb), gp["measured"]["mon"]["yane"]["y"][1], "表門"))
    occupied.append((dev(ban["t"][0]), dev(ban["t"][1]), ban["topY"], "番所"))
    def bands(a, b):
        """展開座標の 2 点から実体の帯を出す。

        ⚠ a>b は「起点をまたいだ」とは限らない — **単に順序が逆なだけ**のことがある
        （番所は dev(a)=11.89 / dev(b)=9.13 で逆順、またいでいない）。
        またいだかどうかは **どちら回りが短いか** で決める。"""
        lo, hi = (a, b) if a <= b else (b, a)
        inner = hi - lo                       # 起点をまたがない回り
        if inner <= total - inner:            # そちらが短ければ実体
            return [(lo, hi)]
        return [(hi, total), (0.0, lo)]       # またぐ回りが短い（表門）
    for a, b, top, nm in occupied:
        segs2 = bands(a, b)
        wide = max(bb - aa for aa, bb in segs2)
        for aa, bb in segs2:
            if bb - aa < 0.02: continue
            g.append(R(X(aa), Y(top), X(bb) - X(aa), (top - 13.4) * sx * ex,
                       fill="var(--shu-lo)", stroke="var(--shu)", sw=1.6))
            if bb - aa == wide:
                g.append(T((X(aa) + X(bb)) / 2, Y(top) - 5, nm, "anG", "middle"))
        occupied_spans.extend(segs2)

    # 囲いの穴 — run も門・番所も無い区間だけを朱で示す
    def covered(a, b):
        m = (a + b) / 2
        return any(oa - 0.02 <= m <= ob + 0.02 for oa, ob in occupied_spans)
    for i in range(1, len(rs)):
        a = max(tt(rs[i - 1]["a"]), tt(rs[i - 1]["b"]))
        b = min(tt(rs[i]["a"]), tt(rs[i]["b"]))
        if b - a > 0.05 and not covered(a, b):
            g.append(R(X(a), Y(max(rs[i - 1]["seat"], rs[i]["seat"]) + dob),
                       X(b) - X(a), (dob + 4.0) * sx * ex,
                       fill="var(--shu)", op=0.18, stroke="var(--shu)", sw=1.4, dash="4 3"))
            g.append(T((X(a) + X(b)) / 2, Y(max(rs[i - 1]["seat"], rs[i]["seat"]) + dob) - 6,
                       "囲いが無い %.2fm" % (b - a), "anG", "middle"))
    g.append(T(4, 16, "展開（表門から時計回り）　水平 約 1/%.0f ・ 垂直は %.0f 倍に強調"
               % (scale1(sx), ex), "anS", "start"))
    g.append(T(4, H - 42, "帯 = 築地塀・竹垣　／　ハッチ = 足元の石垣（天端 seat から 4.0×s 下がる）"
                          "　／　朱の破線 = その run が面する郭の地盤（top）", "anS2", "start"))
    g.append(T(4, H - 27, "**天端は run ごとに一定。** 地形追従で一枚ずつ落とさず、段は run の継ぎ目で落とす"
                          "（太い朱の縦線）。**段は折れ目に置かない** — "
                          "折れの前後で隣地の地盤が変わらないなら、そこに段を置く理由が無い", "anS2", "start"))
    g.append(T(4, H - 12, "⚠ 北東 P[9] まわりの段の位置は未決。総築地塀の前提で引き直し、"
                          "段を P[9] から西へ数間ずらす（okabe_kosho.md「未解決」）", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


def _gmonD(d):
    """門の奥行 = 屋根の o 幅（層別実測から導く。旧 monD は AABB 由来で 0.23 ずれていた）"""
    y = d["gate"]["plan"]["measured"]["mon"]["yane"]
    return y["o"][1] - y["o"][0]


def _gmonH(d):
    """門の高さ = 大棟 − 敷居（同上）"""
    m = d["gate"]["plan"]["measured"]["mon"]
    return m["yane"]["y"][1] - m["tategu"]["y"][0]


# ---------------------------------------------------------------- 其九 表門まわり
def gate_svg(d):
    """放れ門＋片番所＋繋塀。**層別実測（躯体・屋根・腰・建具）を先に持ち、接触はそこから導く。**

    据えの基準は**扉板の面（o=+0.063）を塀の板の面（o=+0.077）へ**。軒先 +0.575 ではない —
    屋根の輪郭で躯体を代用したのが 2026-08-21 の事故と検図の指摘の共通原因。"""
    p = d["gate"]["plan"]
    ms, mon, wr, ban = p["measured"], p["mon"], p["wallRuns"], p["bansho"]
    we, ta = p["wallEnds"], p["tataki"]
    hei = ms["hei"]
    W = 900.0
    t0, t1 = we["southT"] - 4.5, we["northT"] + 4.5
    sx = W / (t1 - t0)
    def X(t): return (t - t0) * sx
    HEAD, PH, MID, EH, FOOT = 22.0, 236.0, 64.0, 196.0, 76.0
    H = HEAD + PH + MID + EH + FOOT
    g = _sv(W, H, "表門まわり 平面と立面")

    # ================= 平面 =================
    OSPAN = 10.0                              # 上 6.6（門の奥行）＋下 3.4（叩きと段の注記）
    so = PH / OSPAN                           # o の縮尺。t とは別（等方だと縦が足りない）
    oy = HEAD + 6.6 * so                      # o=0（外周線）
    def Y(o): return oy + o * so
    g.append(LN(0, Y(0), W, Y(0), "var(--dim)", 0.7, dash="7 4"))
    g.append(T(4, Y(0) - 5, "外周線 t軸", "anS2", "start"))
    # 塀・繋塀は「軒の輪郭（薄）＋躯体の板（濃）」の二層で描く
    def wall(a, b, top=None):
        g.append(R(X(a), Y(hei["eaveO"][0]), X(b) - X(a), (hei["eaveO"][1] - hei["eaveO"][0]) * so,
                   fill="none", stroke="var(--hei)", sw=0.8, dash="4 3"))
        g.append(R(X(a), Y(hei["boardO"][0]) - 1.2, X(b) - X(a),
                   max(3.0, (hei["boardO"][1] - hei["boardO"][0]) * so), fill="var(--hei)"))
    # 叩き
    g.append(R(X(ta["t"][0]), Y(ta["o"][0]), (ta["t"][1] - ta["t"][0]) * sx, (ta["o"][1] - ta["o"][0]) * so,
               fill="var(--dan2)", op=0.75))
    # 前端の段は t の帯ごとに段数が変わる（三べ坂が t につれ上がるため）
    for bd in ta["front"]["bands"]:
        g.append(LN(X(bd["t"][0]), Y(ta["o"][1]), X(bd["t"][1]), Y(ta["o"][1]), "var(--shu)", 2.4))
        for e in bd["t"]:
            g.append(LN(X(e), Y(ta["o"][1]) - 5, X(e), Y(ta["o"][1]) + 5, "var(--shu)", 1.0))
        g.append(T(X((bd["t"][0] + bd["t"][1]) / 2), Y(ta["o"][1]) + 12,
                   "%d段 → %.2f（地形 %.2f）" % (bd["n"], ta["y"] - ta["front"]["riser"] * bd["n"], bd["groundFront"]),
                   "anS2", "middle", 9.5))
    g.append(T(X(0), Y(ta["o"][1]) + 26, "叩き 13.5（塀端から塀端）／ 蹴上 %.2f・踏面 %.2f ／ o+0.575〜+2.4 の 1.83m は路上・通行幅 5.47m 残る"
               % (ta["front"]["riser"], ta["front"]["fumi"]), "anS2", "middle"))
    # 門（屋根┄・躯体・小壁・鏡柱・礎石）
    my, mt = ms["mon"]["yane"], ms["mon"]["tai"]
    g.append(R(X(-mon["roofT"]), Y(my["o"][0]), 2 * mon["roofT"] * sx, (my["o"][1] - my["o"][0]) * so,
               fill="none", stroke="var(--shu)", sw=1.1, dash="6 4"))
    g.append(R(X(-mon["bodyT"]), Y(mt["o"][0]), 2 * mon["bodyT"] * sx, (mt["o"][1] - mt["o"][0]) * so,
               fill="var(--shu-lo)", stroke="var(--shu)", sw=1.8))
    kb = ms["monParts"]["kabe"]
    g.append(R(X(-kb["t"]), Y(kb["o"][0]), 2 * kb["t"] * sx, (kb["o"][1] - kb["o"][0]) * so,
               fill="none", stroke="var(--shu)", sw=2.2))
    g.append(T(X(0), Y(my["o"][0]) - 16, "放れ門　躯体 t=±%.2f ／ 屋根 ±%.2f（┄）" % (mon["bodyT"], mon["roofT"]), "anG", "middle"))
    g.append(T(X(0), Y(my["o"][0]) - 4, "小壁 kabe ±%.3f（━ 繋塀の取り付き先）" % kb["t"], "anS2", "middle"))
    g.append(LN(X(-mon["sosekiT"]), Y(-4.4), X(mon["sosekiT"]), Y(-4.4), "var(--dim)", 1.0, dash="3 3"))
    g.append(T(X(-mon["sosekiT"]) - 5, Y(-4.4) + 3, "礎石 ±%.2f" % mon["sosekiT"], "anS2", "end"))
    wall(t0 - 1, we["southT"])                       # 南（P[0] → 番所）
    wall(ban["t"][1], -we["northT"])                 # 中（番所の北面 → 門の小壁の南面）
    wall(we["northT"], t1 + 1)                       # 北（門の小壁 → P[10]）
    g.append(T(X((t0 + we["southT"]) / 2), Y(hei["eaveO"][0]) - 6, "築地塀", "anS2", "middle"))
    g.append(T(X((ban["t"][1] - we["northT"]) / 2), Y(hei["eaveO"][1]) + 13, "築地塀 2間", "anS2", "middle"))
    g.append(T(X((we["northT"] + t1) / 2), Y(hei["eaveO"][0]) - 6, "築地塀", "anS2", "middle"))
    # 番所（躯体＋屋根）
    g.append(R(X(ban["t"][0]) - (ban["roofW"] - ban["bodyW"]) / 2 * sx, Y(ms["bansho"]["yane"]["o"][0]),
               ban["roofW"] * sx, (ms["bansho"]["yane"]["o"][1] - ms["bansho"]["yane"]["o"][0]) * so,
               fill="var(--ink-mid)", op=0.35))
    g.append(R(X(ban["t"][0]), Y(ban["o"][0]), (ban["t"][1] - ban["t"][0]) * sx,
               (ban["o"][1] - ban["o"][0]) * so, fill="var(--ink-mid)", stroke="var(--ink)", sw=1.4))
    g.append(T(X((ban["t"][0] + ban["t"][1]) / 2), Y(ban["o"][0]) - 8, "片番所（南）", "rmS", "middle", 10.5))
    g.append(T(X((ban["t"][0] + ban["t"][1]) / 2), Y(ms["bansho"]["yane"]["o"][1]) + 12,
               "躯体 %.2f ／ 屋根 %.2f" % (ban["bodyW"], ban["roofW"]), "anS2", "middle"))
    # 接触点
    for c in p["contacts"]:
        r_ = c["rect"]; oo = 0.0 if not r_ or not r_["o"] else (r_["o"][0] + r_["o"][1]) / 2
        g.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="var(--shu)"/>' % (X(c["at_t"]), Y(oo)))
        g.append(T(X(c["at_t"]), Y(oo) + 4, "①②③④⑤⑥⑦⑧"[c["id"] - 1], "rk", "middle", 11))
    for tt in (we["southT"], ban["t"][1], -we["northT"], we["northT"]):
        g.append(LN(X(tt), Y(0) - 4, X(tt), Y(0) + 4, "var(--shu)", 1.0))
        g.append(T(X(tt), HEAD + 2, "%.3f" % tt, "anS2", "middle", 9.5))
    g.append(T(4, 12, "平面（上が屋敷の内・下が三べ坂）　濃＝躯体／薄＝屋根の輪郭", "anS", "start"))

    # ================= 立面 =================
    base = HEAD + PH + MID + EH - 14
    sy = EH / 7.4
    def Ye(y): return base - (y - 13.2) * sy
    g.append(LN(0, Ye(13.5), W, Ye(13.5), "var(--ink)", 1.2))
    g.append(T(4, Ye(13.5) + 13, "地盤 13.5（街路は前で ≈13.1）", "anS2", "start"))
    for a, b in ((t0 - 1, we["southT"]), (ban["t"][1], -we["northT"]), (we["northT"], t1 + 1)):
        g.append(R(X(a), Ye(hei["topY"]), X(b) - X(a), (hei["topY"] - 13.4) * sy, fill="var(--hei)", op=0.85))
    g.append(T(X((we["northT"] + t1) / 2 + 1.2), Ye(hei["topY"]) - 6,
               "築地塀 天端 %.3f（全区間 一本）" % hei["topY"], "anS2", "middle"))
    g.append(R(X(ban["t"][0]), Ye(ban["topY"]), (ban["t"][1] - ban["t"][0]) * sx,
               (ban["topY"] - 13.5) * sy, fill="var(--ink-mid)", stroke="var(--ink)", sw=1.4))
    g.append(T(X((ban["t"][0] + ban["t"][1]) / 2), Ye(ban["topY"]) - 5, "番所 %.3f" % ban["topY"], "anS2", "middle"))
    g.append(R(X(-mon["bodyT"]), Ye(ms["mon"]["yane"]["y"][0]), 2 * mon["bodyT"] * sx,
               (ms["mon"]["yane"]["y"][0] - 13.5) * sy, fill="var(--shu-lo)", stroke="var(--shu)", sw=1.6))
    g.append('<path d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f Z" fill="var(--shu-lo)" stroke="var(--shu)" stroke-width="2"/>'
             % (X(-mon["roofT"]), Ye(ms["mon"]["yane"]["y"][0]), X(mon["roofT"]), Ye(ms["mon"]["yane"]["y"][0]),
                X(mon["roofT"] * 0.28), Ye(mon["ridgeY"]), X(-mon["roofT"] * 0.28), Ye(mon["ridgeY"])))
    g.append(T(X(0), Ye(mon["ridgeY"]) - 6, "大棟 %.3f" % mon["ridgeY"], "anG", "middle"))
    # 繋塀の上の当たり: 小壁の底
    g.append(LN(X(-kb["t"]), Ye(kb["y"][0]), X(kb["t"]), Ye(kb["y"][0]), "var(--shu)", 1.6, dash="4 3"))
    g.append(T(X(0), Ye(kb["y"][0]) - 7, "小壁の底 %.3f（塀はここより外にしか無い）" % kb["y"][0], "anS2", "middle"))
    g.append(T(4, HEAD + PH + MID - 34, "立面（三べ坂から見る）", "anS", "start"))
    g.append(T(4, H - 44, "**据えの基準は板の面。** 扉板 o=+%.3f を 塀の板 o=+%.3f に合わせる（差 %.3f）。"
               "軒先 ±0.575 は屋根の端であって躯体ではない"
               % (mon["doorBoardO"], hei["boardO"][1], mon["doorBoardO"] - hei["boardO"][1]), "anS2", "start"))
    g.append(T(4, H - 30, "**築地塀がそのまま門の小壁 t=±%.3f へ突き当たる。** 別部材の「繋塀」は作らない — "
               "断面も高さも築地塀と同じで、分ける理由が無い" % kb["t"], "anS2", "start"))
    g.append(T(4, H - 16, "塀の上のクリアランス: t≥5.50 の帯で門側の最下は 17.229〜17.501（垂木・破風・螻羽）。"
               "塀の天端 %.3f に対し **1.08m 以上**" % hei["topY"], "anS2", "start"))
    g.append(T(4, H - 2, "QA: " + " ／ ".join(p["qa"][:3]), "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其十 隅
def corner_svg(d):
    """留め継ぎの原理。折れ角を二等分する面で切って接ぐので、角度は部材の引数になる。"""
    W, H = 900.0, 250.0
    g = _sv(W, H, "留め継ぎの隅")
    for i, c in enumerate(d["corners"]):
        cx = 160.0 + i * 300.0
        cy = 130.0
        dg = math.radians(abs(c["deg"]))
        th = 13.0
        for s, lab in ((-1, c["in"]), (1, c["out"])):
            a = math.radians(180.0) if s < 0 else -dg
            ux, uy = math.cos(a), math.sin(a)
            nx, ny = -uy, ux
            pts = [(cx + ux * 0 + nx * th, cy + uy * 0 + ny * th),
                   (cx + ux * 120 + nx * th, cy + uy * 120 + ny * th),
                   (cx + ux * 120 - nx * th, cy + uy * 120 - ny * th),
                   (cx - nx * th, cy - ny * th)]
            g.append('<polygon points="%s" fill="var(--hei)" opacity="0.55" stroke="var(--ink)" stroke-width="0.8"/>'
                     % " ".join("%.1f,%.1f" % p for p in pts))
            g.append(T(cx + ux * 95 + nx * 26, cy + uy * 95 + ny * 26 + 4, lab, "jo", "middle"))
        bis = (math.radians(180.0) + (-dg)) / 2.0
        g.append(LN(cx - math.cos(bis) * 34, cy - math.sin(bis) * 34,
                    cx + math.cos(bis) * 34, cy + math.sin(bis) * 34, "var(--shu)", 2.2))
        g.append('<circle cx="%.1f" cy="%.1f" r="3" fill="var(--ink)"/>' % (cx, cy))
        g.append(T(cx, cy + 52, "%s　Δ=%.1f°" % (CORNER_JA.get(c["part"], c["part"]), c["deg"]),
                   "anG", "middle"))
    g.append(T(4, 16, "朱の線 = 留めの面（折れ角の二等分）", "anS"))
    g.append(T(4, H - 6, "在庫の出隅ブロック（2.4m 角）が成立するのは折れ角 Δ≳60°。"
                         "Δ が浅いと apex が反対側の壁面から 2.4·cosΔ はみ出すので、留め継ぎで納める",
               "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


CORNER_JA = {"Ishigaki": "石垣", "Dobei": "築地塀", "Nagaya": "長屋"}


def scale1(sx):
    """px/m から「1/N」の N。画面の 1px を約 0.2646mm（96dpi）として出す。"""
    return 3779.5 / sx


# ---------------------------------------------------------------- 表
def runs_table(d):
    ja = {"Tsuiji": "築地塀", "Takegaki": "竹垣", "Nagaya": "長屋塀", "None": "囲い無し"}
    rows = ["<tr><td>%s</td><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.1f</td><td class='note'>%s</td></tr>"
            % (r["name"], ja.get(r["kind"], r["kind"]), r["len"], r["top"], r["seat"], r.get("wall") or "—")
            for r in d["runs"]]
    return ("<div class='tw'><table><thead><tr><th>run</th><th>囲い</th><th>延長 m</th>"
            "<th>地盤 top</th><th>天端 seat</th><th class='note'>足元の石垣</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def walls_table(d):
    rows = ["<tr><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.2f</td><td>%.1f</td><td>%.1f</td>"
            "<td>%.1f</td><td>%.1f</td></tr>"
            % (w["name"], w["len"], w["coping"], w["s"], 4 * w["s"], 1.4 * w["s"], 2.4 * w["s"],
               w.get("gapZ", 0))
            for w in d["terraceWalls"]]
    return ("<div class='tw'><table><thead><tr><th>石垣</th><th>延長 m</th><th>天端</th><th>s</th>"
            "<th>壁高</th><th>天端幅</th><th>底厚</th><th>開口 z</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def corners_table(d):
    rows = ["<tr><td>%s</td><td class='note'>%s → %s</td><td>%.1f°</td></tr>"
            % (CORNER_JA.get(c["part"], c["part"]), c["in"], c["out"], c["deg"]) for c in d["corners"]]
    rows += ["<tr><td>隅櫓</td><td class='note'>%s</td><td>%s</td></tr>"
             % (y.get("name", "?"), ("底 %.2f" % y["base"]) if "base" in y else "—")
             for y in d["yagura"]]
    return ("<div class='tw'><table><thead><tr><th>部材</th><th class='note'>場所</th>"
            "<th>折れ角／高さ</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def munes_table(d):
    ken = d["const"]["ken"]
    rows = []
    for m in d["munes"]:
        rows.append("<tr><td>%s</td><td class='note'>%s</td><td>%s</td><td>%d,%d–%d,%d</td>"
                    "<td>%d×%d</td><td>%d×%d</td><td>%.1f</td><td>%d</td><td>%d</td><td>%.0f</td></tr>"
                    % (MUNE_JA.get(m["name"], m["name"]), m["name"], m["zone"],
                       m["u0"], m["v0"], m["u1"], m["v1"], m["kw"], m["kd"],
                       m["kw"] - 2, m["kd"] - 2, m["y"], m["yaw"], len(m["rooms"]),
                       m["kw"] * m["kd"] * ken * ken))
    return ("<div class='tw'><table><thead><tr><th>棟</th><th class='note'>name</th><th>区</th>"
            "<th>u,v</th><th>外形(間)</th><th>身舎(間)</th><th>床</th><th>yaw</th><th>室</th>"
            "<th>外形 m²</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def kaidans_table(d):
    rows = ["<tr><td>%s</td><td>%.1f</td><td>%.1f</td><td>%d</td><td>%.4f</td><td>%.2f</td>"
            "<td>%d</td><td class='note'>%s</td></tr>"
            % (k["name"], k["drop"], k["run"], k["steps"], k["tread"], k["noriHalf"],
               k["odoriKen"], k.get("noboriro") or "—（屋根を架けない）")
            for k in d["kaidans"]]
    return ("<div class='tw'><table><thead><tr><th>石段</th><th>落差</th><th>走り</th><th>段数</th>"
            "<th>踏面</th><th>法面 半幅</th><th>踊り場(間)</th><th class='note'>登廊</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def kenpei(d, area):
    """建蔽率。**分母は敷地全体**（可建地に替えて数字を作らない）。

    数値は json から都度出す — 文章へ写すと片方だけ直る（実際に 31.8% が古いまま残った）。"""
    K = d["const"]["ken"]
    mune = sum(m["kw"] * m["kd"] * K * K for m in d["munes"])
    srv = sum(abs(s["x1"] - s["x0"]) * abs(s["z1"] - s["z0"]) for s in d.get("service", []))
    lk = 0.0
    for l in d["links"]:
        gr = Grid(d, l["grid"]); x0, x1, z0, z1 = gr.box(l)
        lk += (x1 - x0) * (z1 - z0)
    p = d["gate"]["plan"]
    # 屋根の外形で拾う（建蔽率は軒を含む外形で測る）
    mn, bn = p["mon"], p["bansho"]
    ms = p["measured"]
    gt = (2 * mn["roofT"]) * (ms["mon"]["yane"]["o"][1] - ms["mon"]["yane"]["o"][0]) \
         + bn["roofW"] * (ms["bansho"]["yane"]["o"][1] - ms["bansho"]["yane"]["o"][0])
    rows = [("御殿の棟 13", mune), ("＋ 土蔵2・物置", mune + srv),
            ("＋ 渡廊下・取り付き 20", mune + srv + lk),
            ("＋ 表門・番所", mune + srv + lk + gt)]
    body = "".join("<tr><td class='note'>%s</td><td>%.0f</td><td>%.2f%%</td></tr>"
                   % (n, v, v / area * 100) for n, v in rows)
    return ("<div class='tw'><table><thead><tr><th class='note'>分子</th><th>m²</th>"
            "<th>建蔽率</th></tr></thead><tbody>" + body + "</tbody></table></div>")


def links_table(d):
    rows = []
    for l in d["links"]:
        pos = ("x %.3f–%.3f / v %d–%d" % (l["x0"], l["x1"], l["v0"], l["v1"])) if "x0" in l \
              else ("u %d–%d / v %d–%d" % (l["u0"], l["u1"], l["v0"], l["v1"]))
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td><td>%.1f</td></tr>"
                    % (l["name"], l["kind"], l["grid"], pos, l["y"]))
    return ("<div class='tw'><table><thead><tr><th>廊下</th><th>種</th><th>郭</th>"
            "<th class='note'>位置</th><th>床</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def history():
    """経緯は指図に書かない。git log への入口だけ置く。"""
    try:
        out = subprocess.check_output(
            ["git", "log", "-12", "--date=short", "--format=%h|%ad|%s", "--",
             "docs/Sashizu", "Tools/Sashizu",
             "Assets/Edo/Scripts/Editor/EdoOkabeYashikiBuilder.cs"],
            cwd=ROOT, stderr=subprocess.DEVNULL).decode()
    except Exception:
        return "<p class='cap'>git log が読めなかった。</p>"
    rows = []
    for ln in out.strip().split("\n"):
        if not ln:
            continue
        h, dt, sub = ln.split("|", 2)
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td class='note'>%s</td></tr>"
                    % (h, dt, html.escape(sub)))
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

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ["<title>岡部筑前守上屋敷 指図</title>", "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">赤坂 山王社北 ／ 譜代雁間 五万三千石 上屋敷</p>')
    h.append("<h1>岡部筑前守上屋敷 指図</h1>")
    h.append('<div class="box" style="border-color:var(--shu);margin-top:14px"><h3>基準年次と確度</h3><p>'
             '<b>「岡部筑前守」は安政2年（1855）家督の12代 長寛の表記。</b>'
             '基図 NDL 1286657 は嘉永版で「岡部内膳正」（10代 長和）、プロジェクトの基準年次は嘉永期。'
             '<b>どちらを採るかは未決</b>（<code>okabe_kosho.md</code>「未解決」）。<br>'
             '<b>其二・其三・其四 の室名と畳数は 確度 ? の推定。</b>当屋敷の史料には基づかない — '
             '畳数が将軍の御殿を上回る／大広間棟の続き間が二条城の写し／[西川1959]の使者之間が無い／'
             '長局の「側」は大奥の呼称、といった指摘が未処理で、<b>室割りは考証やり直しの対象</b>。'
             '図として何を設計したかを振り返るために載せている。</p></div>')
    h.append('<p class="lede"><b>この文書は現況だけを載せる。</b>過去の案・撤回した説は書かない — '
             '経緯は <code>git log docs/Sashizu/</code> で追う。'
             '寸法の正典は <code>okabe_sashizu.json</code>、文章は <code>okabe_kosho.md</code> で、'
             'この HTML は <code>Tools/Sashizu/build_okabe_sashizu.py</code> が組む。'
             '<b>数値をこの文書に書き足さないこと</b>（写した瞬間に二重管理が始まる）。</p>')
    h.append('<div class="box"><h3>作る順序</h3><p>'
             '① 設計＝<code>json</code>／<code>md</code> を直す　→　② 組む　→　③ 検図（edo-kosho / edo-kenzu）'
             '→ ユーザーのレビュー　→　④ 実装　→　⑤ Unity の「指図と実装を突き合わせる」で 0 件を確認'
             '　→　⑥ 経緯はコミットへ。<br>'
             '建ててみて指図のほうが誤りと分かったときは、<b>指図を直してから</b>実装を合わせ直す。'
             '実装から指図を生成してはならない — 先に図を描く関門が消える。</p></div>')

    plate(h, "其一", "敷地", "%.0f m²（%.0f坪）／ 江戸間 1間 = %.3fm" % (area, area / TSUBO, d["const"]["ken"]))
    fig(h, plan_svg(d),
        legend='<span>■ 段（数字は地盤の標高）</span>'
               '<span style="color:var(--hei)">━ 築地塀</span>'
               '<span style="color:var(--take)">━ 竹垣</span>'
               '<span style="color:var(--ishi)">┄ 郭の土留め</span>'
               '<span>▪ 御殿の棟</span>'
               '<span style="color:var(--shu)">● 表門 ／ ○ 留め継ぎの隅 ／ ┄ 断面の切り位置</span>')
    h.append("</div>")

    plate(h, "其二", "主郭 御殿平面", "%d間 × %d間　外形＝身舎＋四方の入側一間　／　室名・畳数は【確度 ?】"
           % (d["grid"]["shukaku"]["u1"], d["grid"]["shukaku"]["v1"]))
    fig(h, goten_plan(d, "shukaku", "主郭 御殿平面"),
        cap="<b>棟 →（襖）→ 続き間。</b>続き間は棟の中を建具で割ったもので、"
            "別々の矩形に離すと別の建物になる。<b>表向・中奥・奥向</b>を分け、境に<b>御錠口</b>を置く — "
            "奥向へ入る廊下はこの一本だけで、台所棟から奥向棟へ直結する廊下は無い（二本あると錠の意味が消える）。<br>"
            "<b>庭は建屋と囲いの間に残る面。</b>四棟に囲まれた中央が坪庭になるのは帰結であって、"
            "庭から先に矩形で描いたのではない。",
        legend='<span style="color:var(--roka)">■ 入側・渡廊下・外廊下（幅一間）</span>'
               '<span style="color:var(--shu)">■ 御錠口</span>'
               '<span style="color:var(--niwa)">■ 庭</span>'
               '<span>┄ 襖線（続き間の境）</span>')
    h.append("</div>")

    plate(h, "其三", "西の下郭 平面", "西低地 11.5m ／ 中段 19.5m　／　室名・畳数は【確度 ?】")
    fig(h, goten_plan(d, "shimo", "西の下郭 平面"),
        cap="<b>土蔵・物置には入側も廊下も付かない。</b>延焼を切るための独立建物なので、"
            "廊下で繋いだら火が回る。<br>"
            "北縁の廊下は各棟の入側と<b>同じ帯</b>に載る外廊下で、別の帯を隣に足さない — "
            "足すと同じものを二度描いたことになる。",
        legend='<span style="color:var(--roka)">■ 廊下</span>'
               '<span style="color:var(--ink-lo)">■ 土蔵・物置</span>'
               '<span style="color:var(--shu)">┄ 石段の法面</span>')
    h.append("</div>")

    plate(h, "其四", "棟と室", "1間² = 2畳　／　室名・畳数は【確度 ?】")
    h.append(munes_table(d))
    h.append('<p class="cap">室名と畳数は<b>図の中</b>（其二・其三）にある。'
             '<b>rooms は図面だけのもの</b> — Unity の実装は棟単位で襖割りを作らないので、'
             '突き合わせの対象にならない。図中に室名を書き入れるのは指図の作法'
             '（甲良家伝来「江戸城本丸御殿図」ほか）。<br>'
             '<span class="cert">【確度 ? — 室名・畳数は当屋敷の史料に基づかない。'
             '畳数は身舎を間グリッドで機械的に割った数であって格式から出た数ではない。'
             '未処理の指摘は <code>okabe_sashizu.json</code> の <code>_munes</code> に列挙してある】</span></p>')
    h.append(links_table(d))
    h.append('<h3>建蔽率</h3>')
    h.append(kenpei(d, area))
    h.append('<p class="cap"><b>分母は敷地全体（%.0f m² ＝ %.0f坪）。</b>'
             '可建地に替えて数字を作らない。史料値は 22〜55%%（旗本建家図8例）／'
             '小浜 28.6%% ／ 尾張市谷 47.7%% ／ 福井 5〜6割。'
             'レンジ内だが最下端で、外周長屋を全廃したぶんがそのまま出ている — '
             '<b>建蔽率は結果であって目標ではない</b>ので、数字を上げるために空地へ棟を足さない。'
             '埋めるべきは「未解決」の家臣住居の置き直し。<br>'
             '⚠ 実装には郭の土留めの天端に<b>家臣長屋 2 列</b>（<code>KN_IG_W1</code>／'
             '<code>KN_IG_W2</code>・計 約 906 m²）があるが、<b>この指図には無い</b>。'
             '其八の「家臣長屋が載る区間には柵を立てない」はその長屋を根拠にしているので、'
             '図に載せるか実装から外すかを決める必要がある。</p>' % (area, area / TSUBO))
    h.append("</div>")

    for s in d["sections"]:
        plate(h, "其五", s["name"], "%s = %.0f" % (s["axis"], s["at"]))
        fig(h, section_svg(d, s),
            cap="<b>段のつなぎ方は平面だけでは読めない。</b>断面線は表門と石垣の開口の芯を通るので、"
                "石垣ではなく<b>その中を降りる石段</b>が現れる（破線が開口の奥に立つ石垣）。<br>"
                "棟の屋根は<b>図示のための概略</b>で、実装の高さは部材が決める（突き合わせの対象外）。")
        h.append("</div>")

    plate(h, "其六", "郭をまたぐ動線", "登廊 W1／W2")
    fig(h, kaidan_svg(d))
    fig(h, kaidan_section_svg(d))
    h.append(kaidans_table(d))
    h.append('<p class="cap"><b>表門からの参道（E1／E2）には屋根を架けない。</b>'
             '前庭は開けた白洲で、屋根が架かるのは式台・車寄せまで。'
             '屋根を架けるのは郭と郭を結ぶ<b>内部動線（W1／W2）</b>だけ。</p>')
    h.append("</div>")

    plate(h, "其七", "外周", "天端は run ごとに一定。段は継ぎ目で落とす")
    fig(h, perimeter_dev_svg(d))
    h.append(runs_table(d))
    h.append('<p class="cap"><b>地盤 top</b> はその run が面する郭の高さ、'
             '<b>天端 seat</b> は石垣の天端＝塀を据える高さ。犬走りは %.2fm。'
             '石垣は 壁高 = 4.0×s ／ 天端幅 = 1.4×s ／ 底厚 = 2.4×s。</p>' % d["const"]["inubashiri"])
    h.append("</div>")

    plate(h, "其八", "郭の土留め")
    h.append(walls_table(d))
    h.append('<p class="cap">天端には低い竹垣（四つ目垣）を回す — 落差 6〜8m の天端は'
             '御殿と廊下のすぐ脇を歩く<b>生活面</b>なので、素の縁にはしない。'
             '高さ %.2fm・法肩から内へ %.2fm。石段の開口では切る。</p>'
             % (d["terraceRails"]["height"], d["terraceRails"]["insetFromCrest"]))
    if "slopeBands" in d:
        h.append("<h3>西斜面の植生（3帯）</h3>")
        h.append("<div class='tw'><table><thead><tr><th>帯</th><th>標高</th>"
                 "<th class='note'>植生</th><th class='note'>部材</th></tr></thead><tbody>"
                 + "".join("<tr><td>%s</td><td>%.1f〜%s</td><td class='note'>%s</td>"
                           "<td class='note'><code>%s</code></td></tr>"
                           % (b["name"], b["yMin"],
                              ("%.1f m" % b["yMax"]) if b["yMax"] < 90 else "郭の天端",
                              b["veg"], b["asset"])
                           for b in d["slopeBands"]) + "</tbody></table></div>")
        h.append('<p class="cap"><b>竹林ではない。</b>『江戸名所図会』「溜池」（実見）はこの崖線を'
                 '<b>稜線＝松＋広葉樹の樹林／崖面＝ハッチング（草地・裸地）</b>で描き、'
                 '樹は稜線と法面上部に集まる — 法面全体を樹林で埋めない。'
                 '[橋本・堀1998]（査読）では溜池の水辺の樹木は 2 例とも松、'
                 '<b>竹薮は江戸の水辺 79 事例中 1 例</b>の例外。'
                 '<b>竹垣（四つ目垣）は垣の材なので別物</b>で、こちらは残す。</p>')
    h.append("</div>")

    plate(h, "其九", "表門まわり", "放れ門（独立門）＋片番所")
    fig(h, gate_svg(d))
    rows = []
    for c in d["gate"]["plan"]["contacts"]:
        r_ = c["rect"]
        rect = "o[%.3f, %.3f]" % tuple(r_["o"]) if r_ and r_.get("o") else "—"
        if r_ and r_.get("y"): rect += "　y[%.3f, %.3f]" % tuple(r_["y"])
        rows.append("<tr><td>%s</td><td class='note'>%s ⟷ %s</td><td>t=%.3f</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % ("①②③④⑤⑥⑦⑧"[c["id"] - 1], c["a"], c["b"], c["at_t"], rect, c["note"]))
    h.append("<h3>接触の一覧（どの面とどの面が接するか）</h3>"
             "<div class='tw'><table><thead><tr><th></th><th class='note'>部材</th><th>位置</th>"
             "<th class='note'>接触面（run座標）</th><th class='note'>納まり</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table></div>")
    h.append('<p class="cap"><b>据えの基準は扉の面＝塀の外面（o=+0.575）。</b>'
             '2026-08-21 の実装で門が公道の中に 6.5m はみ出した事故を受け、座標を全て数値で確定した。'
             '原因は長屋門用の据え付けロジック（鏡柱の面を塀に合わせる際に別の面を測っていた）と、'
             'k_mon のピボットが躯体の外（鏡柱面より 2.18m 街路側の空中）にあること。<br>'
             '<b>繋塀は実体として置く</b>（従前の「端パネルの伸ばしで代用」は長屋専用の処理で、'
             '総築地塀化後は何も建たないことが分かった）。取り付く先は<b>門柱（躯体の端 ±4.44）</b>であって'
             '屋根の端（±7.20）ではない — 従前の開口半幅 14.47 は屋根幅で計算した誤り。</p>')
    h.append("</div>")

    plate(h, "其十", "隅", "折れ角は現地が決める。決め打ちしない")
    fig(h, corner_svg(d))
    h.append(corners_table(d))
    h.append("</div>")

    plate(h, "其十一", "考証と決めごと")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, "改訂", "", "経緯はここに書かず git で追う")
    h.append(history())
    h.append("</div>")

    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>okabe_sashizu.json</code> ／ '
             '文章 <code>okabe_kosho.md</code>。Y は海抜 m（Unity の Y がそのまま標高）。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    open(OUT, "w", encoding="utf-8").write("\n".join(h))
    print("wrote %s (%.0f KB) — 図版 %d 面" % (OUT, os.path.getsize(OUT) / 1024, _SVN[0]))
    print("  run: 検図 → ユーザーのレビュー → 実装 → 指図と実装を突き合わせる")


if __name__ == "__main__":
    main()
