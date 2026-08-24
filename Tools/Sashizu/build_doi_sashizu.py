#!/usr/bin/env python3
"""土井大隅守上屋敷(三河刈谷藩)の指図を組む。

    python3 Tools/Sashizu/build_doi_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/doi_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/doi_kosho.md     … 文章の部(人が書く・現況形)

の二つだけ。実装から指図を作ると CLAUDE.md 絶対規則2 の関門が消える。

【この屋敷ならではの作り】表門が載る**東辺(辺5)**が世界軸から振れているため、
主郭は**回転間グリッド**(u=東辺沿い北+ / v=敷地の奥=西+)で持つ。
回転角は `gate.yaw` と多角形から導き、ここには書かない(数値は設計値が正典)。
⚠ 2026-08-24 の検図 低-2 まで、ここに「北辺の大通り」「24.49°」「其一〜其九」と
**他屋敷からの写し**が残っていた。**章立てと角度をこの docstring に書かない** —
落款の類は必ず古びる。
    ・世界図版は Proj(世界→px)
    ・御殿平面は LProj(グリッド間→px)— 棟・室・庭はすべて軸平行になる
    ・外周は辺番号+辺沿い走り s で持つ run を展開する

【図版】章立ては本文(`doi_kosho.md`)の見出しが正典。
        組んだら「図版 N 面」を数えること(図版が黙って落ちた前科がある)。
"""
import json, math, os, re, subprocess, html, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "doi_sashizu.json")
MD = os.path.join(DOC, "doi_kosho.md")
OUT = os.path.join(DOC, "doi_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown(岡部と同じ最小変換)
SRC_MD = os.path.expanduser(
    "~/.claude/skills/unity-buke-yashiki/references/sources.md")


def sources_index():
    """`sources.md` の登録 ID → 確度。見出し(### [ID] 確度X)と表の行(| [ID] |)の両方。"""
    if not os.path.exists(SRC_MD):
        return {}, set()
    t = open(SRC_MD, encoding="utf-8").read()
    head = dict((m.group(1), m.group(2))
                for m in re.finditer(r"^### \[([^\]]+)\]\s*確度([SABPU?])", t, re.M))
    tbl = set(re.findall(r"^\|\s*\[([^\]]+)\]\s*\|", t, re.M))
    return head, tbl


def sources_block(md):
    """文章が実際に引いている `[ID]` を集め、確度つきで並べる。

    ⚠ **手で並べない。** 2026-08-24 の考証で、手書きの一覧に撤回済みの根拠が残り、
    翻刻に S が振られ、7件が落ちていた(高④)。
    台帳に無い ID は**そうと明示して出す** — 書誌の無い引用が確度を名乗るのを止める。
    """
    head, tbl = sources_index()
    used = sorted(set(re.findall(r"\[([^\]\n]{2,24})\]", md)))
    rows, miss = [], []
    for u in used:
        if u in head:
            rows.append("| `[%s]` | %s |" % (u, head[u]))
        elif u in tbl:
            rows.append("| `[%s]` | 親エントリに従う |" % u)
        else:
            miss.append(u)
    out = ["| 典拠 | 確度 |", "|---|---|"] + rows
    if miss:
        out.append("")
        out.append("⚠ **台帳に無い ID**: " + " / ".join("`[%s]`" % m for m in miss))
    return "\n".join(out), miss


def neighbour_block(d, ter, dem):
    """隣家の埋没を**毎回測って**表にする。手で書いた表は測り方を変えた瞬間に嘘になる。"""
    rows = ["| 隣家の塀 | 埋没 | 当家側の地盤 |", "|---|---|---|"]
    gr = RGrid(d)
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    n = 0
    for who, (fn_, edges) in NEIGHBOUR.items():
        path = os.path.join(DOC, fn_)
        if not os.path.exists(path):
            continue
        nb = json.load(open(path, encoding="utf-8"))
        P = nb["polygon"]
        for r in nb.get("runs", []):
            if r.get("edge") not in edges:
                continue
            a, b = P[r["edge"]], P[(r["edge"] + 1) % len(P)]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            ex, ez = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx_, nz_ = -ez, ex
            mu, mv = gr.L((a[0] + b[0]) / 2 + nx_ * 3, (a[1] + b[1]) / 2 + nz_ * 3)
            sg = 1.0 if in_parcel(d, mu, mv) else -1.0
            # ⚠ 隣家の run は `seat` を持たず `seat0`/`seat1` だけのことがある
            #   (2026-08-24 に岡部が N_Hei3 を分割した形)。**片方が無い前提で読む。**
            s0v = r.get("seat0", r.get("seat")); s1v = r.get("seat1", r.get("seat"))
            if s0v is None or s1v is None:
                continue
            worst = None
            m = max(4, int((r["s1"] - r["s0"]) / 0.5))
            for i in range(m + 1):
                sq = r["s0"] + (r["s1"] - r["s0"]) * i / float(m)
                t = sq / L
                if t > 1.0:
                    break
                x, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                px, pz = x + nx_ * 0.3 * sg, z + nz_ * 0.3 * sg
                u, v = gr.L(px, pz)
                nat = dem_bilinear(dem, px, pz)
                if nat is None:
                    nat = ter["at"](u, v)
                if nat is None:
                    continue
                g = design_y(d, u, v)
                if g is None:
                    g = graded_y(d, u, v, nat, we)
                if g is None:
                    continue
                tr = 0.0 if r["s1"] <= r["s0"] else (sq - r["s0"]) / (r["s1"] - r["s0"])
                seat = s0v + (s1v - s0v) * max(0.0, min(1.0, tr))
                if worst is None or g - seat > worst[0]:
                    worst = (g - seat, sq, g, nat)
            if worst is None or worst[0] <= 0.05:
                continue
            n += 1
            kind = ("盛土 +%.2fm" % (worst[2] - worst[3])) if worst[2] - worst[3] > 0.05 else "素地"
            rows.append("| %s `%s`(相手の s=%.1f) | **%.2fm** | %.2f(%s) |"
                        % (who, r["name"], worst[1], worst[0], worst[2], kind))
    if n == 0:
        return "**埋まる箇所は無い。**"
    rows.append("")
    rows.append("測り方: 境界から**土井側へ 0.3m**(塀の足元)、`doi_dem.json` を**双一次**で引く。"
                "天端は **run の中**で `seat0→seat1` を按分(相手の生成器の `rseat` が正典)。"
                "判定は 0.05m 超。**是正は隣家側**(据え付け面を当家の地盤より下げない)。")
    return "\n".join(rows)


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
            # ⚠ 行ごとに inline() を呼ぶと**行をまたぐ `**…**` が壊れる**(2026-08-24 検図 低-1)。
            #   まず素のまま連結してから、項目ごとに一度だけ inline() を通す。
            raw = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  ")):
                if lines[i].startswith("- "):
                    raw.append(lines[i][2:])
                elif raw:
                    raw[-1] += " " + lines[i].strip()
                i += 1
            items = [inline(x) for x in raw]
            out.append("<ul>" + "".join("<li>%s</li>" % t for t in items) + "</ul>"); continue
        if ln.strip() == "---":
            out.append('<hr class="rule">'); i += 1; continue
        if ln.strip() == "":
            i += 1; continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "-", "|")) and lines[i].strip() != "---":
            buf.append(lines[i].strip()); i += 1
        if not buf:
            # ⚠ 1行も消費できないと i が進まず**無限ループ**する。
            #   表の途中に別の行が挟まると、後続の `|` 行が「表の始まり」と判定されず
            #   ここへ落ちて固まる(2026-08-23、HTML コメントを1行入れて実際に固まった)。
            #   前進を必ず保証し、拾えなかった行はそのまま段落として出す。
            out.append("<p>%s</p>" % inline(lines[i].strip())); i += 1
            continue
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def inline(s):
    s = re.sub(r'</?span[^>]*>', "", s)
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", s)
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
    """グリッド座標 (u,v)[間] → SVG px。v(敷地の奥)が画面の下。

    ⚠ **u は画面の左向き**。(u,v) は世界座標で反時計回りの対(u×v>0)なので、
    v を下向きに取ったら u は左向きでないと**図が鏡像になる**
    (2026-08-23 ユーザー指摘で是正 — 其一と其二の左右が逆だった)。
    結果、この図版は 其一(北が上)を反時計回りに 90° 回した向き = **上が東(表門の道)/
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


DAN = {17.9: "var(--pl-umaya)", 19.2: "var(--pl-omote)", 21.9: "var(--pl-higashi)", 24.7: "var(--pl-suso)",
       25.0: "var(--pl-kita)", 26.0: "var(--niwa)", 26.6: "var(--pl-main)", 26.7: "var(--pl-main)"}
PLANE_COL = {"厩の郭": "var(--pl-umaya)", "門前面": "var(--pl-omote)", "前庭面": "var(--pl-higashi)", "中段(北隅)": "var(--pl-suso)",
             "玄関の郭": "var(--pl-kita)", "書院の郭": "var(--niwa)", "主面": "var(--pl-main)",
             "斜面(造成しない)": "var(--pl-slope)"}
KC = {"Nagaya": "var(--nagaya)", "Dobei": "var(--hei)"}

MUNE_JA = {
    "Yakusho": "表役所棟", "Genkan": "玄関棟", "Shoin": "書院棟", "Ima": "居間棟",
    "Oku": "奥棟", "Daidokoro": "台所棟", "Umaya": "厩棟",
}
TERR_JA = {"UmayaKaku": "厩の郭", "MonzenE": "門前面(門口)", "Yakusho": "表役所の郭",
           "MonzenN": "門内北", "MaeNiwa": "前庭",
           "KitaSumi": "米蔵の郭", "NagayaKitaDai": "表長屋(北2)の基壇", "Naka": "中段",
           "GenkanKaku": "玄関の郭", "ShoinKaku": "書院の郭", "Shu": "主面",
           "ShuMain": "主面", "ShuKita": "主面(北)", "ShuMae": "主面(南舌)", "ShuMinami": "主面(南)",
           "KachuN1": "家中長屋(北一)", "KachuN2": "家中長屋(北二)", "KachuN3": "家中長屋(北三)",
           "KachuS1": "家中長屋(南一)", "KachuS2": "家中長屋(南二)", "KachuY": "家中長屋(表)"}


# ---------------------------------------------------------------- 其一 敷地
def plan_svg(d):
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), 900.0, pad=14.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "土井大隅守上屋敷 敷地全体")

    def gpoly(u0, v0, u1, v1, **kw):
        pts = [gr.W(u0, v0), gr.W(u1, v0), gr.W(u1, v1), gr.W(u0, v1)]
        return _poly(pts, **kw)

    def gobj(o, **kw):                                  # 回転を持つ物はそのまま四隅で描く
        return _poly([gr.W(u, v) for u, v in obb_pts(o)], **kw)

    def _poly(pts, **kw):
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
        g.append(gobj(t, fill=DAN.get(t["y"], "var(--dan4)"), op=1.0))
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
    for rl in d["rails"]:
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="var(--take)" stroke-width="2.6" stroke-dasharray="2 4"/>'
                 % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts))

    # 御殿・付属屋の輪郭
    for m in d["munes"]:
        g.append(gpoly(m["u0"], m["v0"], m["u1"], m["v1"],
                       fill="var(--ink-mid)", stroke="var(--ink)", sw=0.5, op=0.85))
    for s in d["service"]:
        g.append(gobj(s, fill="var(--ink-lo)", stroke="var(--ink)", sw=0.6, op=0.9))
    # 段ラベル(面ごと・重ね順の最後)
    labs = []
    for t in d["terraces"]:
        cx, cz = gr.W((t["u0"] + t["u1"]) / 2.0, (t["v0"] + t["v1"]) / 2.0)
        labs.append((pr.X(cx), pr.Y(cz),
                     "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"])))
    for lx, ly, txt in declutter(labs):
        g.append(T(lx, ly, txt, "anS", "middle"))

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
            a = gr.W(s["at"], s["from"]); b = gr.W(s["at"], s["to"])
        else:
            a = gr.W(s["from"], s["at"]); b = gr.W(s["to"], s["at"])
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
def goten_plan(d, u0, u1, v0, v1, label, note):
    pr = LProj(u0, u1, v0, v1, 900.0)
    g = _sv(pr.W, pr.H, "土井大隅守上屋敷 %s" % label)
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
        if "yaw" in t:                                  # 回転物は四隅で描く(外接矩形で描かない)
            g.append('<polygon points="%s" fill="%s"/>'
                     % (" ".join("%.1f,%.1f" % (pr.X(a9), pr.Y(b9)) for a9, b9 in obb_pts(t)),
                        DAN.get(t["y"], "var(--dan4)")))
        else:
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
        g.append(T(pr.X(max(a_u, b_u) - 1), pr.Y(max(min(a_v, b_v), v0) + 1.6), w["name"], "jo"))
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
    for rp in d.get("ramps", []):                       # 土の斜路(馬・荷車の通り道)
        if "u0" in rp:                                  # 踏み代を矩形で持つ(壁に沿う斜路)
            g.append(pr.rect(rp["u0"], rp["v0"], rp["u1"], rp["v1"],
                             fill="var(--michi)", stroke="var(--shu)", sw=1.0, op=0.45))
            cu, cv = (rp["u0"] + rp["u1"]) / 2.0, (rp["v0"] + rp["v1"]) / 2.0
        else:
            w = [x for x in d["terraceWalls"] if x["name"] == rp["atWall"]][0]
            hw = rp["w"] / 2 / 1.818
            rk = rp["run"] / 1.818
            if w["a"][0] == w["b"][0]:
                cu, cv = w["a"][0], rp["gapV"]
                g.append(pr.rect(cu - rk / 2, cv - hw, cu + rk / 2, cv + hw,
                                 fill="var(--michi)", stroke="var(--shu)", sw=1.0, op=0.45))
            else:
                cu, cv = rp["gapU"], w["a"][1]
                g.append(pr.rect(cu - hw, cv - rk / 2, cu + hw, cv + rk / 2,
                                 fill="var(--michi)", stroke="var(--shu)", sw=1.0, op=0.45))
        g.append(T(pr.X(cu), pr.Y(cv) - 8, "斜路 1:%.0f" % (1.0 / rp["grade"]),
                   "anS2", "middle"))
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
        if "yaw" in s:
            g.append('<polygon points="%s" fill="var(--ink-lo)" stroke="var(--ink)" stroke-width="1.2"/>'
                     % " ".join("%.1f,%.1f" % (pr.X(a9), pr.Y(b9)) for a9, b9 in obb_pts(s)))
            g.append(T(pr.X(s["uc"]), pr.Y(s["vc"]) + 4, s["label"], "rmS", "middle",
                       fit(s["label"], pr.L(s["D"]) + 16, 11.0)))
        else:
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
               "**上=東(三べ坂前身の南北道)／左=北／下=西／右=南** — 其一(北が上)を反時計回りに90°回した向き",
               "anS"))
    g.append(T(4, pr.H - 5, note, "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 切盛(どこを盛りどこを切るか)
CF_BANDS = [(0.3, "var(--fill1)"), (1.0, "var(--fill2)"), (2.0, "var(--fill3)"), (3.0, "var(--fill4)")]


def cf_color(dz):
    """dz = 設計の面 − 造成前の地形。正=盛土(暖色) / 負=切土(寒色)。"""
    a = abs(dz)
    if a < 0.3:
        return "var(--nomove)"
    i = 0 if a < 1.0 else 1 if a < 2.0 else 2 if a < 3.0 else 3
    return ("var(--fill%d)" if dz > 0 else "var(--cut%d)") % (i + 1)


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


def dem_bilinear(dem, x, z):
    """世界座標2m格子の DEM を**双一次**で引く。

    ⚠ **造成前の地盤は `docs/Sashizu/base_dem.json` が正本**(CLAUDE.md 規則12)。
    Unity の live terrain から採ると、採った時刻までに誰かが流した造成が乗る。
    2026-08-24、当方の旧 `doi_dem.json` は松平区画の 574セル(最大 +6.91m)に
    松平の造成を写しており、2m格子の双一次が境界から 0.3m の点で向こう側のセルを混ぜて、
    当家側の「自然地盤」を 2.5m 押し上げていた(松平の指摘で発覚)。
    一時、区画内のセルだけに平面を当てる回避を入れたが、**正本へ差し替わって不要になった**
    (正本では両家が同じ面を読むのが要件で、素の双一次が正しい。回避は最大 0.63m ずれる)。

    ⚠ `ter["at"]` は 1m 格子の**最近傍**なので、境界を挟んだ ±0.3m が同じセルに落ちる。
    塀の足元の埋没を測るのに使うと、急斜面では ±1.7m の誤差が出た(2026-08-24 第8巡:
    松平 S_Hei_E1 は当家側 +1m で 3.35m 落ちる崖で、判定が立たなかった)。
    **境界際の判定は、内挿した回転格子でなく原資料の DEM を連続に引く。**
    """
    if dem is None:
        return None
    fx = (x - dem["x0"]) / dem["step"]
    fz = (z - dem["z0"]) / dem["step"]
    ix, iz = int(math.floor(fx)), int(math.floor(fz))
    if ix < 0 or iz < 0 or ix + 1 >= dem["nx"] or iz + 1 >= dem["nz"]:
        return None
    tx, tz = fx - ix, fz - iz
    q = [dem["h"][iz][ix], dem["h"][iz][ix + 1], dem["h"][iz + 1][ix], dem["h"][iz + 1][ix + 1]]
    if any(w is None for w in q):
        return None
    return (q[0] * (1 - tx) + q[1] * tx) * (1 - tz) + (q[2] * (1 - tx) + q[3] * tx) * tz



_PGRID = {}


def in_parcel(d, u, v):
    """(u, v) が区画の中か。**段も法面も区画線で切る** — 隣地へ土を出さないため。

    ⚠ 2026-08-24 の検図: `doi_terrain.json` は区画外が null なので、
    それで「区画外へこぼれる量」を測ると**構造的に 0 しか出ない**。
    実際は dem で測ると 387.9m² / 247m³ が隣地へ出ていた。**測れないデータで検証しない。**
    """
    key = repr(d["polygon"])
    P = _PGRID.get(key)
    if P is None:
        gr = RGrid(d)
        P = [gr.L(x, z) for x, z in d["polygon"]]
        _PGRID[key] = P
    c = False
    n = len(P)
    for i in range(n):
        (au, av), (bu, bv) = P[i], P[(i + 1) % n]
        if (av > v) != (bv > v) and u < au + (bu - au) * (v - av) / (bv - av):
            c = not c
    return c


def design_y(d, u, v):
    """その (u,v) を覆う段の高さ。無ければ None(=造成しない斜面)。"""
    if not in_parcel(d, u, v):
        return None                                    # 区画の外に段は無い
    best = None
    for t in d["terraces"]:
        if in_obb(t, u, v, 1e-9):
            best = t["y"] if best is None else max(best, t["y"])
    return best


def run_edges(d):
    """外周 run(表長屋・練塀)が載っている辺の、グリッドでの区間。

    基壇石垣が地形を受けるので、その辺から法面を出してはいけない
    (2026-08-23 検図 M-6: 街路辺で盛土のすそが区画線を最大1.93m越える計算になっていた)。
    表門の辺(v=0)だけを扱う — 他の辺の囲いは隣家の持ち物。
    """
    ken = d["const"]["ken"]
    sg = d["gate"]["s"]
    out = []
    for r in d["runs"]:
        if r["edge"] != d["gate"]["edge"]:
            continue
        out.append(((r["s0"] - sg) / ken, (r["s1"] - sg) / ken))
    gp = d["gate"]["plan"]
    out.append((-gp["monW"] / 2 / ken, gp["monW"] / 2 / ken))
    return out


def walled_edges(d, t):
    """段 t の四辺のうち土留めが載っている**区間**。(辺名, lo, hi) の並びで返す。
    辺単位で「壁が1本でもあれば辺全体を壁付き」と見ると、壁の無い区間に法面が出ず
    垂直の段差が残る(2026-08-23 検図で南東縁に3.5mの受け無し段差が見つかった)。"""
    def emit(name, lo, hi, gap):
        """⚠ **開口の区間は壁が無い。** ここを壁付きとして返すと、法面も出ず検査も素通りし、
        開口幅から通る物の幅を引いた分が**受けの無い垂直段差**として残る
        (2026-08-24 検図: 8本合計28.8m)。開口で区間を割って返す。"""
        segs = [(lo, hi)] if gap is None else \
               [(lo, min(hi, gap[0])), (max(lo, gap[1]), hi)]
        for a9, b9 in segs:
            if b9 - a9 > 0.4:
                out.append((name, a9, b9))

    out = []
    for w in d["terraceWalls"]:
        if abs(w["coping"] - t["y"]) > 0.05:
            continue
        (au, av), (bu, bv) = w["a"], w["b"]
        gh = w.get("gapHalf", 0.0)
        if abs(au - bu) < 1e-9:                       # u=const の壁
            lo, hi = max(min(av, bv), t["v0"]), min(max(av, bv), t["v1"])
            gap = (w["gapV"] - gh, w["gapV"] + gh) if "gapV" in w else None
            if abs(au - t["u0"]) < 1e-6:
                emit("u0", lo, hi, gap)
            if abs(au - t["u1"]) < 1e-6:
                emit("u1", lo, hi, gap)
        else:                                          # v=const の壁
            lo, hi = max(min(au, bu), t["u0"]), min(max(au, bu), t["u1"])
            gap = (w["gapU"] - gh, w["gapU"] + gh) if "gapU" in w else None
            if abs(av - t["v0"]) < 1e-6:
                emit("v0", lo, hi, gap)
            if abs(av - t["v1"]) < 1e-6:
                emit("v1", lo, hi, gap)
    return out


def _walled(we, edge, w):
    """辺 edge の位置 w が、土留めの載っている区間に入っているか。"""
    if not edge:
        return False
    for (e, lo, hi) in we:
        if e == edge and lo - 1e-9 <= w <= hi + 1e-9:
            return True
    return False


def stair_y(d, u, v):
    """石段の掘割(切通し)の中なら、その位置の**踏面の高さ**を返す。外なら None。

    石段は段と段のあいだの土手を**切通す**。掘割を地盤として扱わないと、
    「踏面が地山に埋まっている」という誤検出になり、切土も切盛図に出ない
    (2026-08-23 検図 M-2: K_Kita が最大 0.82m 埋まると出た)。
    """
    K = d["const"]["ken"]
    for k in d["kaidans"]:
        w = [x for x in d["terraceWalls"] if x["name"] == k["atWall"]][0]
        run = k["run"] / K
        hw = k["w"] / 2.0 / K + 0.25                    # 片側に犬走りぶんの余裕
        if abs(w["a"][0] - w["b"][0]) < 1e-9:           # u=const の壁 → 段は u 方向へ下る
            if abs(v - k["gapV"]) > hw:
                continue
            lo = -1.0 if design_y(d, w["a"][0] - 0.5, v) is None or \
                 (design_y(d, w["a"][0] - 0.5, v) or 0) < w["coping"] else 1.0
            t = (u - w["a"][0]) / (lo * run)
        else:                                           # v=const の壁 → 段は v 方向へ下る
            if abs(u - k["gapU"]) > hw:
                continue
            lo = -1.0 if design_y(d, k["gapU"], w["a"][1] - 0.5) is None or \
                 (design_y(d, k["gapU"], w["a"][1] - 0.5) or 0) < w["coping"] else 1.0
            t = (v - w["a"][1]) / (lo * run)
        if -1e-9 <= t <= 1.0 + 1e-9:
            return w["coping"] - k["drop"] * t
    return None


def graded_y(d, u, v, nat, walled=None):
    """**造成後の地盤**。段の中は段の高さ。段の外は法面(盛土 1:%.1f / 切土 1:%.1f)で
    現地形へ摺り付ける — 段の縁に垂直の段差を残さないため(2026-08-23 ユーザー指摘)。
    土留めが載っている辺からは法面を出さない(そこは壁が垂直に受ける)。
    どこも触らない点では nat と同じ値を返すので、差がゼロ=無造成。"""
    if not in_parcel(d, u, v):
        return nat                                     # 区画の外は現地形のまま(造成しない)
    ins = design_y(d, u, v)
    if ins is not None:
        return ins
    st = stair_y(d, u, v)                              # 石段の掘割は踏面が地盤
    if st is not None:
        return st
    if nat is None:
        return None
    K = d["const"]["ken"]
    bf = d["const"].get("batterFill", 1.5)
    bc = d["const"].get("batterCut", 1.0)
    cap = d["const"].get("featherCap", 12.0)
    g = nat
    floor = -1e9
    for t in d["terraces"]:
        if in_obb(t, u, v):
            continue                                   # 回転物の内側は段そのもの
        we = walled[t["name"]] if walled else walled_edges(d, t)
        if u < t["u0"]:
            du, eu = t["u0"] - u, "u0"
        elif u > t["u1"]:
            du, eu = u - t["u1"], "u1"
        else:
            du, eu = 0.0, None
        if v < t["v0"]:
            dv, ev = t["v0"] - v, "v0"
        elif v > t["v1"]:
            dv, ev = v - t["v1"], "v1"
        else:
            dv, ev = 0.0, None
        # ⚠ 隅では、辺の壁の**端**を引き継ぐ。素の v/u で引くと隅の外側は
        #   どちらの壁の区間からも外れ、壁の角から盛土の楔が生える
        #   (2026-08-23 検図: 表役所の郭の南東隅で 2.65m 宙吊り)。
        qv = min(max(v, t["v0"]), t["v1"])
        qu = min(max(u, t["u0"]), t["u1"])
        if _walled(we, eu, qv) or _walled(we, ev, qu):
            continue                                   # 壁が受ける区間 — 法面を出さない
        if ev == "v0" and abs(t["v0"]) < 1e-9 and any(a9 <= qu <= b9 for a9, b9 in run_edges(d)):
            continue                                   # 外周 run の基壇石垣が受ける(法面を出さない)
        dm = math.hypot(du, dv) * K
        if dm > cap:
            continue
        y2 = t["y"] - dm / bf
        if t["y"] - cap / bf > nat:
            continue                                   # cap の内で現地形に着地しない = 法面を出さない
        g = max(g, y2)                                 # 盛土の裾がこぼれる
        floor = max(floor, y2)                         # 盛土が要求する下限
    for t in d["terraces"]:
        if in_obb(t, u, v):
            continue                                   # 回転物の内側は段そのもの
        we = walled[t["name"]] if walled else walled_edges(d, t)
        if u < t["u0"]:
            du, eu = t["u0"] - u, "u0"
        elif u > t["u1"]:
            du, eu = u - t["u1"], "u1"
        else:
            du, eu = 0.0, None
        if v < t["v0"]:
            dv, ev = t["v0"] - v, "v0"
        elif v > t["v1"]:
            dv, ev = v - t["v1"], "v1"
        else:
            dv, ev = 0.0, None
        qv = min(max(v, t["v0"]), t["v1"])
        qu = min(max(u, t["u0"]), t["u1"])
        if _walled(we, eu, qv) or _walled(we, ev, qu):
            continue
        dm = math.hypot(du, dv) * K
        if dm > cap:
            continue
        if t["y"] + cap / bc < nat:
            continue                                   # cap の内で現地形に着かない
        g = min(g, t["y"] + dm / bc)                   # 切土の法が日の目を見る
    # ⚠ 切土の法面が**盛土の要求する下限を割らない**ようにする。
    #   低い段の切土が高い段の縁の下を掘り、縁に受けの無い段差を作っていた
    #   (2026-08-24 検図: 書院の郭の南縁で 0.89m)。
    return max(g, floor)


def cutfill_svg(d, ter):
    """切盛図。造成前の地形(実測)と設計の面の差を、格子のセル塗りで示す。"""
    P = d["polygon"]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), 900.0, pad=14.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "土井大隅守上屋敷 切盛図")
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
        g.append(_obj_poly(pr, gr, t, fill="none", stroke="var(--ink)", sw=0.8,
                           dash="5 4", op=0.8))
    # 敷地の外をマスクしてから区画線
    ring = " ".join("L %.1f %.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P)
    g.append('<path d="M -20 -20 H %.0f V %.0f H -20 Z M%s Z" fill="var(--paper)" fill-rule="evenodd"/>'
             % (pr.W + 20, pr.H + 20, ring[1:]))
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    # 段の名 — 区画の中に入っているセルの重心へ置く(素の中心だと敷地の外へ出る)
    labs = []
    for t in d["terraces"]:
        su = sv = 0.0; n = 0
        iv = 0
        while iv < ter["nv"]:
            v = ter["v0"] + iv * st; iv += 1
            if not (t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9):
                continue
            for iu in range(ter["nu"]):
                u = ter["u0"] + iu * st
                if (t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9
                        and ter["h"][iv - 1][iu] is not None
                        and in_parcel(d, u, v)):        # 格子の被覆でラベルが動かないように
                    su += u; sv += v; n += 1
        if not n:
            continue
        cx, cz = gr.W(su / n, sv / n)
        labs.append((pr.X(cx), pr.Y(cz),
                     "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"])))
    for lx, ly, txt in declutter(labs):
        g.append(T(lx, ly, txt, "anS", "middle"))
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


def cutfill_legend():
    sw = ('<span style="display:inline-block;width:14px;height:11px;background:%s;'
          'border:1px solid var(--rule);margin-right:5px;vertical-align:-1px"></span>')
    out = ["<span>%s盛土 3m超</span>" % (sw % "var(--fill4)"),
           "<span>%s2〜3m</span>" % (sw % "var(--fill3)"),
           "<span>%s1〜2m</span>" % (sw % "var(--fill2)"),
           "<span>%s0.3〜1m</span>" % (sw % "var(--fill1)"),
           "<span>%s±0.3m(動かさない)</span>" % (sw % "var(--nomove)"),
           "<span>%s切土 0.3〜1m</span>" % (sw % "var(--cut1)"),
           "<span>%s1〜2m</span>" % (sw % "var(--cut2)"),
           "<span>%s2〜3m</span>" % (sw % "var(--cut3)"),
           "<span>%s3m超</span>" % (sw % "var(--cut4)"),
           '<span style="color:var(--paper2)">■ 造成しない斜面(素地)</span>']
    return "".join(out)


def cutfill_table(d, ter):
    """段ごとの切盛。造成の重さを面ごとに読む。"""
    st = ter["step"]; a = (st * d["const"]["ken"]) ** 2
    rows = []
    tf = tc = 0.0
    for t in d["terraces"]:
        f = c = 0.0; mf = mc = 0.0; n = 0
        iv = 0
        while iv < ter["nv"]:
            v = ter["v0"] + iv * st
            iu = 0
            while iu < ter["nu"]:
                u = ter["u0"] + iu * st
                iu += 1
                if not in_obb(t, u, v, 1e-9):     # 回転物は外接矩形で走査しない(二重計上になる)
                    continue
                # 同じ高さの段が重なる所は**先に挙がった1枚だけ**が数える(2026-08-24 検図 低-4)
                if next((x for x in d["terraces"]
                         if abs(x["y"] - t["y"]) < 0.01 and in_obb(x, u, v, 1e-9)), None) is not t:
                    continue
                nat = ter["h"][iv][iu - 1]
                if nat is None or design_y(d, u, v) != t["y"]:
                    continue
                dz = t["y"] - nat; n += 1
                if dz > 0:
                    f += dz * a; mf = max(mf, dz)
                else:
                    c += -dz * a; mc = max(mc, -dz)
            iv += 1
        tf += f; tc += c
        rows.append("<tr><td>%s</td><td>%.1f</td><td>%.0f 坪</td><td>%.0f m³</td><td>%.1f m</td>"
                    "<td>%.0f m³</td><td>%.1f m</td></tr>"
                    % (TERR_JA.get(t["name"], t["name"]), t["y"], n * a / TSUBO, f, mf, c, mc))
    # ⚠ **法面(段の外)を別行で足して、見出しの土量と合わせる。**
    #   段の中だけを合計しており、図版見出し(全セル)と 盛 +52 / 切 +145 m³ 食い違って
    #   いた。キャプションは「段の外へこぼれる法面も含む」と書いており表については偽だった
    #   (2026-08-24 検図9巡 中-1)。閾値(|dz|<0.05 は触らない)も見出しに揃える。
    we_t = dict((x["name"], walled_edges(d, x)) for x in d["terraces"])
    sf = sc = 0.0; sn = 0
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * st
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * st
            nat = ter["h"][iv][iu]
            if nat is None or design_y(d, u, v) is not None:
                continue                          # 段の中は上で数えた
            dz = graded_y(d, u, v, nat, we_t) - nat
            if abs(dz) < 0.05:
                continue
            sn += 1
            if dz > 0:
                sf += dz * a
            else:
                sc += -dz * a
    if sn:
        rows.append("<tr><td>法面(段の外)</td><td>—</td><td>%.0f 坪</td><td>%.0f m³</td>"
                    "<td>—</td><td>%.0f m³</td><td>—</td></tr>"
                    % (sn * a / TSUBO, sf, sc))
    rows.append("<tr><td><b>計</b></td><td></td><td></td><td><b>%.0f m³</b></td><td></td>"
                "<td><b>%.0f m³</b></td><td></td></tr>" % (tf + sf, tc + sc))
    return ('<div class="tw"><table><thead><tr><th>段</th><th>面の高さ</th><th>面積</th>'
            "<th>盛土量</th><th>最大盛土</th><th>切土量</th><th>最大切土</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


# ---------------------------------------------------------------- 現況図(段彩+等高線)
# 段彩の色は地図の記号なので、明暗のテーマに関わらず固定(紙の地形図と同じ読み方をさせる)
DEM_RAMP = [(10, "#2E6E8E"), (12, "#3A8398"), (14, "#4E9A9B"), (16, "#6BAC90"),
            (18, "#8ABC84"), (20, "#A9C87C"), (22, "#C6D07A"), (24, "#DCC776"),
            (26, "#E2B06C"), (28, "#D9925C"), (30, "#C87651"), (99, "#A85C45")]


def dem_color(y):
    for lim, c in DEM_RAMP:
        if y < lim:
            return c
    return DEM_RAMP[-1][1]


def _iso(dem, lv):
    """マーチングスクエアで等高線を出す。線分の並びを返す。"""
    st, h = dem["step"], dem["h"]
    segs = []
    for iz in range(dem["nz"] - 1):
        for ix in range(dem["nx"] - 1):
            a, b = h[iz][ix], h[iz][ix + 1]
            c, e = h[iz + 1][ix + 1], h[iz + 1][ix]
            x0, z0 = dem["x0"] + ix * st, dem["z0"] + iz * st
            idx = (1 if a > lv else 0) | (2 if b > lv else 0) | (4 if c > lv else 0) | (8 if e > lv else 0)
            if idx in (0, 15):
                continue

            def ip(p, q, yp, yq, t):
                if abs(yq - yp) < 1e-9:
                    return p
                return p + (q - p) * (lv - yp) / (yq - yp)
            B = (ip(x0, x0 + st, a, b, 0), z0)
            R = (x0 + st, ip(z0, z0 + st, b, c, 0))
            To = (ip(x0, x0 + st, e, c, 0), z0 + st)
            L = (x0, ip(z0, z0 + st, a, e, 0))
            tbl = {1: (B, L), 2: (B, R), 3: (L, R), 4: (R, To), 5: (B, R), 6: (B, To),
                   7: (L, To), 8: (L, To), 9: (B, To), 10: (B, L), 11: (R, To),
                   12: (L, R), 13: (B, R), 14: (B, L)}
            if idx in tbl:
                segs.append(tbl[idx])
    return segs


def pass_span(d, w):
    """土留め w の開口を**通る物**(石段・斜路・廊下)の、壁に沿った向きの span。

    ⚠ 算出結果を設計値へ置くと**偽装できる** — 感度試験で `_pass` を手で広げると
    「20間の物が通っている」ことになり、開口を辺の全長にしても検査が反応しなかった
    (2026-08-24)。**毎回、実在する物から数え直す。**
    """
    K = d["const"]["ken"]
    vert = abs(w["a"][0] - w["b"][0]) < 1e-9
    gk = "gapV" if vert else "gapU"
    line = w["a"][0] if vert else w["a"][1]
    lo, hi = (min(w["a"][1], w["b"][1]), max(w["a"][1], w["b"][1])) if vert else \
             (min(w["a"][0], w["b"][0]), max(w["a"][0], w["b"][0]))
    spans = []
    for k in d["kaidans"] + d.get("ramps", []):
        if k.get("atWall") != w["name"]:
            continue
        c = k.get(gk)
        c = (lo + hi) / 2.0 if c is None else c
        hw = k["w"] / K / 2.0
        spans.append((c - hw, c + hw))
    for l in d.get("links", []):
        lu0, lu1, lv0, lv1 = l["u0"], l["u1"], l["v0"], l["v1"]
        if vert:
            if lu0 <= line <= lu1 and lv1 > lo and lv0 < hi:
                spans.append((lv0, lv1))
        else:
            if lv0 <= line <= lv1 and lu1 > lo and lu0 < hi:
                spans.append((lu0, lu1))
    return spans, gk, lo, hi, line, vert


def snap_openings(d):
    """土留めの**開口の幅**を「通る物の幅+袖」から算出し、石垣のピッチ(1.8×s)の整数倍へ丸める。

    ⚠ **正典の既存値を下限にしない。** それをするとラチェットになり、開口は決して縮まず、
    焼き付いた過大値が「不動点だから正しい」と誤認される(2026-08-24 検図第7巡:
    8本中5本が過大、TW_ShuG は 6.48m も広かった)。
    ⚠ **廊下は壁線と実際に交差するものだけ拾い、幅は壁を横切る向きの寸法を取る。**
    片軸だけで照合すると 10間離れた廊下を拾い、その「長さ」を幅として使ってしまう
    (TW_ShuS の開口が壁より広くなっていた原因)。
    """
    K = d["const"]["ken"]
    SODE = 0.3                                          # 袖(間)
    for w in d["terraceWalls"]:
        vert = abs(w["a"][0] - w["b"][0]) < 1e-9        # u=const の壁(v 方向に走る)
        gk = "gapV" if vert else "gapU"
        if gk not in w:
            continue
        pitch = 1.8 * w["s"] / K
        line = w["a"][0] if vert else w["a"][1]
        lo, hi = (min(w["a"][1], w["b"][1]), max(w["a"][1], w["b"][1])) if vert else \
                 (min(w["a"][0], w["b"][0]), max(w["a"][0], w["b"][0]))
        # ⚠ **幅だけでなく「芯」も通る物から取る。** 幅しか算出せず芯を手書きのまま
        #   残していたため、石段 K_Shu を u=0 → +2.0 へ寄せた是正(2026-08-23)のときに
        #   TW_ShuG の gapU が 0 に取り残され、**石段が開口の外に立った**。
        #   断面⑰に土留めの露出と石段が同じ場所へ同時に描かれていた(2026-08-24 検図 高-3)。
        spans = []
        for k in d["kaidans"] + d.get("ramps", []):
            if k.get("atWall") != w["name"]:
                continue
            c = k.get(gk)
            if c is None:                               # 芯を持たない物は壁の中央に置く
                c = (lo + hi) / 2.0
            hw = k["w"] / K / 2.0
            # **両袖を確保できる位置へ寄せる。** 壁の端に張り付くと片袖が取れず、
            # 開口が壁の外へ出る(2026-08-24: K_ShuS が TW_ShuS の始点を 0.045間 越えていた)。
            if hi - lo >= 2 * (hw + SODE):
                c = max(lo + hw + SODE, min(c, hi - hw - SODE))
            k[gk] = round(c, 3)                         # 算出値を正典へ戻す
            spans.append((c - hw, c + hw))
        for l in d.get("links", []):                    # 壁線を跨ぐ廊下だけ
            lu0, lu1, lv0, lv1 = l["u0"], l["u1"], l["v0"], l["v1"]
            if vert:
                if not (lu0 <= line <= lu1 and lv1 > lo and lv0 < hi):
                    continue
                spans.append((lv0, lv1))                # 壁を横切る向き=v
            else:
                if not (lv0 <= line <= lv1 and lu1 > lo and lu0 < hi):
                    continue
                spans.append((lu0, lu1))                # 同=u
        if spans:
            a0 = min(q[0] for q in spans); a1 = max(q[1] for q in spans)
        else:
            a0 = a1 = (lo + hi) / 2.0
        need = a1 - a0
        ctr = (a0 + a1) / 2.0
        want = max(need + 2 * SODE, pitch)              # 既存値は参照しない
        m = max(1, int(math.ceil(want / pitch - 1e-9)))
        wid = m * pitch
        if wid > (hi - lo) - 2 * SODE:                  # 壁より広い開口を作らない
            wid = max(pitch, math.floor(max(0.0, (hi - lo) - 2 * SODE) / pitch) * pitch)
        # 開口の縁は石垣の**目地**に落とす(積みは開口から外へ向かって並べる)
        g0 = lo + round((ctr - wid / 2.0 - lo) / pitch) * pitch
        for _ in range(64):                             # 通る物を必ず包む
            if g0 > a0 - 1e-9:
                g0 -= pitch
            elif g0 + wid < a1 - 1e-9:
                wid += pitch
            else:
                break
        g0 = max(lo, min(g0, hi - wid))                 # 壁の中に収める
        w[gk] = round(g0 + wid / 2.0, 3)
        w["gapHalf"] = round(wid / 2.0, 3)
        w["_pitch"] = round(pitch, 3)
    return d


def fix_sode(d):
    """開口の**袖石垣**を算出して正典へ戻す。

    開口は「塞ぐ物」ではない — 石段や廊下が通るために**開いているのが正しい**。
    高い側の土は、開口の両端で**直角に振れる袖石垣**が受ける。
    2026-08-24 の検図 高-2 まで `adjacency_check` は開口を壁として数えており、
    辺の全長を開口にしても0件だった。開口を正しく「壁が無い」と数えるようにした以上、
    **袖が設計値に無い開口は不適合**として出す必要がある。

    袖の長さは落差ぶん法内へ振る(切土 1:1 なので落差と同じ長さで法尻に達する)。
    最低でも石垣1ピッチ。
    """
    K = d["const"]["ken"]
    for w in d["terraceWalls"]:
        gk = "gapU" if "gapU" in w else ("gapV" if "gapV" in w else None)
        if gk is None:
            w.pop("sode", None)
            continue
        drop = w.get("drop")
        dm = max(drop) if isinstance(drop, list) else (drop or 0.0)
        pitch = 1.8 * w["s"] / K
        ln = max(pitch, dm / K)
        # ⚠ **余地が無ければ袖を立てない。** かつて開口を持つ壁すべてに無条件で
        #   書き込んでおり、直後の `opening_fit_check` の「袖が無い」分岐が
        #   **到達不能**だった(2026-08-24 検図9巡 中-3)。
        #   ⚠ 袖は壁に**直角**に、高い側の段の中へ振れる。余地は壁沿いではなく
        #   **直角方向**で測る(最初この方向を取り違えた)。
        vert = abs(w["a"][0] - w["b"][0]) < 1e-9
        gk = "gapV" if vert else "gapU"
        line = w["a"][0] if vert else w["a"][1]
        g0, g1 = w[gk] - w["gapHalf"], w[gk] + w["gapHalf"]
        # ⚠ **同高の段は複数ある。** `max(...)` は同値のとき**先頭を返す**ので、
        #   8開口のうち6開口で誤った段を選び、袖が「振れる先が無い」と誤判定されていた
        #   (2026-08-25 検図10巡 高-1)。**同高の段の集合にして、どれかが振れ先を含めば可**。
        hi_ts = [t for t in d["terraces"] if abs(t["y"] - w["coping"]) < 0.01]
        room = None
        for gg in (g0, g1):
            for sgn in (1.0, -1.0):
                if vert:
                    pu, pv = line + sgn * ln, gg
                else:
                    pu, pv = gg, line + sgn * ln
                if not in_parcel(d, pu, pv):
                    continue
                if hi_ts and not any(in_obb(t, pu, pv, 1e-9) for t in hi_ts):
                    continue
                if any(in_obb(m, pu, pv, 1e-9) for m in d["munes"] + d.get("service", [])):
                    continue                       # 棟の中へは振れない
                room = ln if room is None else room
                break
            else:
                room = -1.0                        # この端は振れる先が無い
                break
        if room is None or room < 0:
            w["_sodeRoom"] = [round(ln, 3)]
            # ⚠ **算出値は毎回作り直す。** 判定が不成立でも古い `sode` を消していなかったため、
            #   前の版が書いた `sode` が正典に残り、`opening_fit_check` を素通りさせていた。
            #   **「全検査0件」が古い値に支えられていた**(2026-08-25 検図10巡 高-1)。
            w.pop("sode", None)
            continue
        w.pop("_sodeRoom", None)
        w["sode"] = {"len": round(ln, 3), "drop": round(dm, 2),
                     "_": "開口の両端で直角に振れる袖石垣。長さは落差ぶん(切土1:1で法尻に達する)"}
    return d


def _seg_dist(px, pz, a, b):
    """点から線分までの距離。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (pz - a[1]) * dz) / L2))
    return math.hypot(px - (a[0] + dx * t), pz - (a[1] + dz * t))


def fix_boundary_plinth(d, dem):
    """**隣家が持つ辺**に沿って、当家の盛土を受ける基壇石垣を算出して正典へ戻す。

    外周長屋の帯(家中長屋)と主面は、設計として区画線まで届く。届く以上、
    当家の土は**当家で受ける** — 隣家の練塀に受けさせない(2026-08-24 検図 高-4)。
    辺5(当家の持ち物)では表長屋の run が基壇石垣を持って同じことをしている。
    隣家の持ち物の辺には run を置けないので、**境界線の内側 0.3m に基壇だけを回す**
    (塀は建てない — 囲いは隣家の持ち物のままで、二重塀にはしない)。

    区間は石垣のピッチ(1.8×s)へ丸め、天端は区間内の設計地盤の最大値。
    """
    d["boundaryPlinth"] = []
    if dem is None:
        return d
    P = d["polygon"]
    own = d.get("edgeOwner", {})
    gr = RGrid(d)
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    FEATHER = d["const"].get("boundaryFeather", 0.20)   # これ以下の盛りは 0.3m の退がりで摺り付く
    pitch = 1.8 * 0.25
    for i in range(len(P)):
        if own.get(str(i)) in (None, "土井"):
            continue
        a, b = P[i], P[(i + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ex, ez = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx_, nz_ = -ez, ex
        mu, mv = gr.L((a[0] + b[0]) / 2 + nx_ * 3, (a[1] + b[1]) / 2 + nz_ * 3)
        sg = 1.0 if in_parcel(d, mu, mv) else -1.0
        n = max(4, int(L / 0.5))
        prof = []
        for k in range(n + 1):
            sq = L * k / float(n)
            x, z = a[0] + (b[0] - a[0]) * sq / L, a[1] + (b[1] - a[1]) * sq / L
            px, pz = x + nx_ * 0.3 * sg, z + nz_ * 0.3 * sg
            u, v = gr.L(px, pz)
            nat = dem_bilinear(dem, px, pz)
            if nat is None:
                prof.append((sq, None, None)); continue
            g = design_y(d, u, v)
            if g is None:
                g = graded_y(d, u, v, nat, we)
            prof.append((sq, g, nat))
        lo = None; top = -9e9; dmax = 0.0
        for sq, g, nat in prof + [(L + 1.0, None, None)]:
            fill = (g - nat) if (g is not None and nat is not None) else -1.0
            if fill > FEATHER:
                lo = sq if lo is None else lo
                top = max(top, g)
                # ⚠ 落差は**同じ点での** g−nat の最大。天端の最大と地盤の最小を
                #   別の場所から取ると、区間が長いほど嘘が大きくなる(2026-08-24)。
                dmax = max(dmax, fill)
            elif lo is not None:
                s0 = math.floor(lo / pitch) * pitch
                s1 = math.ceil(min(sq, L) / pitch) * pitch
                # ⚠ **丁場は落差から算出する。** 0.25 に固定していたので、段をいくら
                #   持ち上げても壁高 1.00m のままで、検査が恒真だった
                #   (2026-08-24 検図9巡 高-1)。壁高は 4s。
                sq_s = max(0.20, math.ceil(dmax / 4.0 / 0.05 - 1e-9) * 0.05)
                d["boundaryPlinth"].append(
                    {"edge": i, "s0": round(max(0.0, s0), 2), "s1": round(min(L, s1), 2),
                     "coping": round(top, 2), "drop": round(dmax, 2), "s": round(sq_s, 2),
                     "_": "隣家が持つ辺に沿う基壇石垣。塀は隣家の持ち物なので石垣だけを回す"})
                lo = None; top = -9e9; dmax = 0.0
    return d


def boundary_fill_check(d, dem):
    """**隣家が持つ辺**へ、当家の造成が垂直面のまま届いていないか。

    段は `in_parcel` で切られるので、区画線まで盛ると**切り口の垂直面が境界に残る**。
    その辺の囲いは隣家の持ち物なので、当家の土を隣家の練塀が受ける形になる
    (2026-08-24 検図 高-4: 岡部境 13.5m・松平境 39.0m で最大 +0.94m)。
    法面を出す余地(盛土 1:1.5)が当家側に無ければ、段を退げるしかない。
    """
    if dem is None:
        return []
    P = d["polygon"]
    own = d.get("edgeOwner", {})
    gr = RGrid(d)
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    bad = []
    for i in range(len(P)):
        if own.get(str(i)) in (None, "土井"):
            continue
        a, b = P[i], P[(i + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ex, ez = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx_, nz_ = -ez, ex
        mu, mv = gr.L((a[0] + b[0]) / 2 + nx_ * 3, (a[1] + b[1]) / 2 + nz_ * 3)
        sg = 1.0 if in_parcel(d, mu, mv) else -1.0
        run_lo = None; worst = 0.0; hit = 0.0
        n = max(4, int(L / 0.5))
        for k in range(n + 1):
            sq = L * k / float(n)
            x, z = a[0] + (b[0] - a[0]) * sq / L, a[1] + (b[1] - a[1]) * sq / L
            px, pz = x + nx_ * 0.3 * sg, z + nz_ * 0.3 * sg
            u, v = gr.L(px, pz)
            nat = dem_bilinear(dem, px, pz)
            if nat is None:
                continue
            g = design_y(d, u, v)
            if g is None:
                g = graded_y(d, u, v, nat, we)
            dz = (g - nat) if g is not None else 0.0
            if dz > d["const"].get("boundaryFeather", 0.20):
                # **基壇石垣が受けきれている所は不適合ではない。**
                # ⚠ かつて「天端 ≥ 設計地盤」で控除していたが、天端は生成の定義上
                #   つねに設計地盤以上なので**どんな設計でも0件を返す恒真**だった
                #   (2026-08-24 検図9巡 高-1: 段を +3m 持ち上げても0件)。
                #   **壁高 4s が落差を受けきれるか**と、**基壇で受ける高さの上限**を見る。
                held = False
                for q in d.get("boundaryPlinth", []):
                    if q["edge"] != i or not (q["s0"] - 1e-6 <= sq <= q["s1"] + 1e-6):
                        continue
                    if 4.0 * q["s"] + 1e-6 < dz:
                        bad.append("辺%d(%s の持ち物)s=%.1f: 基壇の壁高 %.2fm が"
                                   "盛土 %.2fm を受けきれない"
                                   % (i, own.get(str(i)), sq, 4.0 * q["s"], dz))
                    elif dz > d["const"].get("boundaryPlinthMax", 2.0):
                        bad.append("辺%d(%s の持ち物)s=%.1f: 盛土 %.2fm は基壇で受ける高さの"
                                   "上限 %.2fm を超える — 段を退げること"
                                   % (i, own.get(str(i)), sq, dz,
                                      d["const"].get("boundaryPlinthMax", 2.0)))
                    held = True
                    break
                if held:
                    if run_lo is not None:
                        bad.append("辺%d(%s の持ち物)の s=%.1f..%.1f(%.1fm)で当家の盛土が"
                                   "区画線に達している — 最大 %.2fm"
                                   % (i, own.get(str(i)), run_lo, hit, hit - run_lo, worst))
                        run_lo = None; worst = 0.0
                    continue
                if run_lo is None:
                    run_lo = sq
                worst = max(worst, dz)
                hit = sq
            elif run_lo is not None:
                bad.append("辺%d(%s の持ち物)の s=%.1f..%.1f(%.1fm)で当家の盛土が"
                           "区画線に達している — 最大 %.2fm"
                           % (i, own.get(str(i)), run_lo, hit, hit - run_lo, worst))
                run_lo = None; worst = 0.0
        if run_lo is not None:
            bad.append("辺%d(%s の持ち物)の s=%.1f..%.1f(%.1fm)で当家の盛土が"
                       "区画線に達している — 最大 %.2fm"
                       % (i, own.get(str(i)), run_lo, hit, hit - run_lo, worst))
    return bad


def perimeter_check(d):
    """**当家が持つ辺**が、塀・長屋と申告した門口で閉じているか。

    2026-08-24 の検図: 表長屋 `E_Nagaya_S`(19.5m)を消しても全検査が無反応だった。
    外周の閉じは「隙間>めり込み」で、**穴は作らない**のが正典の規則。
    ⚠ 長屋の中の潜り(通用門)は run に含まれるので**開きではない** — 開きと数えるのは
    run が載っていない区間だけ。
    """
    P = d["polygon"]
    own = d.get("edgeOwner", {})
    tol = 0.05
    bad = []
    for i in range(len(P)):
        if own.get(str(i)) != "土井":
            continue
        a, b = P[i], P[(i + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        segs = [(r["s0"], r["s1"]) for r in d["runs"] if r["edge"] == i]
        g = d["gate"]
        if g["edge"] == i:
            w = g["plan"]["monW"] / 2.0
            segs.append((g["s"] - w, g["s"] + w))
        for k in d.get("komon") or []:
            if k["edge"] == i:
                segs.append((k["s"] - k["w"] / 2.0, k["s"] + k["w"] / 2.0))
        segs = sorted((max(0.0, x), min(L, y)) for x, y in segs)
        cur = 0.0
        for x, y in segs:
            if x > cur + tol:
                bad.append("辺%d(当家)の s=%.1f..%.1f(%.1fm)に塀も長屋も門口も無い"
                           % (i, cur, x, x - cur))
            cur = max(cur, y)
        if cur < L - tol:
            bad.append("辺%d(当家)の s=%.1f..%.1f(%.1fm)に塀も長屋も門口も無い"
                       % (i, cur, L, L - cur))
    return bad


def clearance_check(d):
    """棟・付属屋から**区画線まで**の離れ。犬走り+基壇厚を確保する。

    `inubashiri_check` は「棟↔**段**」しか測らないので、区画線までの離れは
    どの検査も見ていなかった。段を半間の格子へ寄せた是正で、米蔵と松平境の離れが
    1.68m → 1.32m に縮んでいたのを見落とした(2026-08-24 検図9巡 中-5)。
    """
    K = d["const"]["ken"]
    need = d["const"]["inubashiri"] * K + 0.3      # 犬走り + 基壇の厚み(境界内側 0.3m)
    P = d["polygon"]
    gr = RGrid(d)
    bad = []
    for m in d["munes"] + d.get("service", []):
        best = 1e9
        for u, v in obb_pts(m):
            x, z = gr.W(u, v)
            for i in range(len(P)):
                best = min(best, _seg_dist(x, z, P[i], P[(i + 1) % len(P)]))
        if best + 1e-6 < need:
            bad.append("%s から区画線までが %.2fm — 犬走り+基壇の %.2fm に足りない"
                       % (m["name"], best, need))
    return bad


def rails_check(d):
    """竹垣の不変条件。設計値 `_rails` が自分で宣言している条件を検査に落とす。

    ⚠ かつて「竹垣は意匠なので不変条件を持たない」と書いたが、`_rails` 自身が
    「**土を受けず動線も止めない**」と宣言しており、後者は検査できる
    (2026-08-24 検図9巡 低-3)。**宣言した不変条件には検査を付ける。**
    土を受けない側は、法肩に沿う垣が自然の崖と重なるため今回は立てない。
    """
    bad = []
    for rl in d.get("rails", []):
        pts = rl["pts"]
        for a, b in zip(pts, pts[1:]):
            for r in d.get("routes", []):
                for c, e in zip(r["pts"], r["pts"][1:]):
                    d1 = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                    d2 = (b[0] - a[0]) * (e[1] - a[1]) - (b[1] - a[1]) * (e[0] - a[0])
                    d3 = (e[0] - c[0]) * (a[1] - c[1]) - (e[1] - c[1]) * (a[0] - c[0])
                    d4 = (e[0] - c[0]) * (b[1] - c[1]) - (e[1] - c[1]) * (b[0] - c[0])
                    if d1 * d2 < -1e-12 and d3 * d4 < -1e-12:
                        bad.append("竹垣 %s が動線 %s を横切る — 垣は動線を止めない"
                                   % (rl["name"], r.get("label", r["name"])))
    return sorted(set(bad))


def norms_check(d):
    """**廊下の規範**(§1)と**柱割り**(§4)を機械検査に落とす。

    2026-08-24 の検図で、故意に壊しても反応しない検査が10通り見つかった。うち4通り
    — 御錠口を二つにする / 同じ二棟間に渡廊下を二本引く / 土蔵に渡廊下を付ける /
    棟を 0.37間 ずらす — は**検査が一つも無かった**。設計は適合していたが、
    ラチェットが無いので次に棟を動かせば黙って壊れる。
    """
    GRID = 0.5                                   # 江戸間の半間。部屋は畳数なのでこれが下限
    bad = []

    def off(x):
        return abs(x / GRID - round(x / GRID)) > 1e-6

    for o in d["munes"] + d.get("service", []):
        if abs(o.get("yaw", 0.0)) > 1e-9:        # 回転棟は寸法だけ見る(位置は現地形都合)
            for k in ("L", "D"):
                if k in o and off(o[k]):
                    bad.append("%s の %s=%.3f間 が半間の格子に載らない" % (o["name"], k, o[k]))
            continue
        for k in ("u0", "u1", "v0", "v1"):
            if k in o and off(o[k]):
                bad.append("%s の %s=%.3f間 が半間の格子に載らない" % (o["name"], k, o[k]))
    for l in d.get("links", []):
        for k in ("u0", "u1", "v0", "v1"):
            if off(l[k]):
                bad.append("%s の %s=%.3f間 が半間の格子に載らない" % (l["name"], k, l[k]))

    # 御錠口は表向・中奥と奥を分かつ**結界**なので一つだけ
    goj = [l for l in d.get("links", []) if l.get("kind") == "御錠口"]
    if len(goj) != 1:
        bad.append("御錠口が %d 本ある — 奥との結界は一つでなければ意味を持たない" % len(goj))

    # 廊下が触れる棟(矩形が接するか重なる)
    def touches(l, m):
        if abs(m.get("yaw", 0.0)) > 1e-9:
            return False
        gu = max(l["u0"], m["u0"]) - min(l["u1"], m["u1"])
        gv = max(l["v0"], m["v0"]) - min(l["v1"], m["v1"])
        return gu <= 0.01 and gv <= 0.01

    KURA = ("Kura", "Komegura")
    pairs = {}
    for l in d.get("links", []):
        hit = [m["name"] for m in d["munes"] + d.get("service", []) if touches(l, m)]
        for h in hit:
            if h.startswith(KURA):
                bad.append("%s が %s に取り付く — 土蔵・米蔵に廊下は付けない(火を分ける)"
                           % (l["name"], h))
        if len(hit) >= 2:
            for i in range(len(hit)):
                for j in range(i + 1, len(hit)):
                    key = tuple(sorted((hit[i], hit[j])))
                    pairs.setdefault(key, []).append(l["name"])
    for key, ls in pairs.items():
        if len(ls) > 1:
            bad.append("%s と %s のあいだに廊下が %d 本(%s)— 二重に引かない"
                       % (key[0], key[1], len(ls), "・".join(sorted(ls))))
    return bad


def refs_check(d):
    """設計値どうしの**参照が切れていないか**。切れた参照は生成を止めるか、黙って検査を素通りさせる。"""
    names = set(w["name"] for w in d["terraceWalls"])
    tn = set(t["name"] for t in d["terraces"])
    bad = []
    for k in d["kaidans"] + d.get("ramps", []):
        w = k.get("atWall")
        if w is None:
            bad.append("%s に atWall が無い" % k["name"])
        elif w not in names:
            bad.append("%s の atWall=%s が土留めに無い" % (k["name"], w))
    for w in d["terraceWalls"]:
        for side in ("hi", "lo", "above", "below"):
            v = w.get(side)
            if isinstance(v, str) and v not in tn:
                bad.append("%s の %s=%s が段に無い" % (w["name"], side, v))
    for m in d["munes"] + d.get("service", []):
        pl = m.get("plane") or m.get("terrace")
        if isinstance(pl, str) and pl not in tn:
            bad.append("%s の面 %s が段に無い" % (m["name"], pl))
    return bad


def opening_fit_check(d):
    """開口に**物が通っているか**と、**通る物が開口に完全に含まれるか**を検める。

    幅だけ算出して芯を手書きで残していたため、石段 K_Shu が開口の外に立ち、
    断面⑰に土留めの露出と石段が同時に描かれていた(2026-08-24 検図 高-3)。
    """
    K = d["const"]["ken"]
    bad = []
    for w in d["terraceWalls"]:
        gk = "gapU" if "gapU" in w else ("gapV" if "gapV" in w else None)
        if gk is None:
            continue
        g0, g1 = w[gk] - w["gapHalf"], w[gk] + w["gapHalf"]
        vert = abs(w["a"][0] - w["b"][0]) < 1e-9
        line = w["a"][0] if vert else w["a"][1]
        lo, hi = (min(w["a"][1], w["b"][1]), max(w["a"][1], w["b"][1])) if vert else \
                 (min(w["a"][0], w["b"][0]), max(w["a"][0], w["b"][0]))
        n = 0
        for o in d["kaidans"] + d.get("ramps", []):
            if o.get("atWall") != w["name"]:
                continue
            n += 1
            c = o.get(gk)
            if c is None:
                bad.append("%s に通る %s が芯(%s)を持たない" % (w["name"], o["name"], gk))
                continue
            hw = o["w"] / K / 2.0
            if c - hw < g0 - 1e-6 or c + hw > g1 + 1e-6:
                bad.append("%s の開口 [%.3f, %.3f] から %s [%.3f, %.3f] がはみ出す"
                           % (w["name"], g0, g1, o["name"], c - hw, c + hw))
        for l in d.get("links", []):
            lu0, lu1, lv0, lv1 = l["u0"], l["u1"], l["v0"], l["v1"]
            if vert:
                if not (lu0 <= line <= lu1 and lv1 > lo and lv0 < hi):
                    continue
                a0, a1 = lv0, lv1
            else:
                if not (lv0 <= line <= lv1 and lu1 > lo and lu0 < hi):
                    continue
                a0, a1 = lu0, lu1
            n += 1
            if a0 < g0 - 1e-6 or a1 > g1 + 1e-6:
                bad.append("%s の開口 [%.3f, %.3f] から廊下 %s [%.3f, %.3f] がはみ出す"
                           % (w["name"], g0, g1, l["name"], a0, a1))
        if n == 0:
            bad.append("%s に開口があるのに通る物が無い" % w["name"])
        if "sode" not in w:
            rr = w.get("_sodeRoom")
            bad.append("%s の開口に袖石垣が無い%s"
                       % (w["name"],
                          "(直角に %.2f間 振れる先が段の中に無い)" % rr[0]
                          if rr else ""))
    return bad


def fix_kaidans(d):
    """石段の段数と水平距離を drop と const.keri/fumi から算出して設計値へ書き戻す。
    手で書くと drop を直したときに段数が置き去りになる(2026-08-23 の _pending.dansu)。
    蹴上は keri を上限として段数で割り直すので、実際の蹴上は keri 以下になる。"""
    keri, fumi = d["const"]["keri"], d["const"]["fumi"]
    for l in d.get("links", []):                       # 階段廊下の蹴上も上限を割らせない(2026-08-24 検図 低-5)
        if "drop" in l and l.get("steps"):
            l["steps"] = max(1, int(math.ceil(l["drop"] / (keri * 0.95) - 1e-9)))
            l["keriActual"] = round(l["drop"] / l["steps"], 3)
    for k in d["kaidans"]:
        # ⚠ 蹴上が上限ちょうど(0.300)に張り付くと、丸めが1段ずれた瞬間に違反する。
        #   余裕を見て 1 段多く取る(2026-08-23 検図 L-8)。
        n = max(1, int(math.ceil(k["drop"] / (keri * 0.95) - 1e-9)))
        k["steps"] = n
        k["run"] = round(n * fumi, 2)
        k["keriActual"] = round(k["drop"] / n, 3)
    return d


def fix_walls(d, ter):
    """土留めの落差 `drop` と規模 `s` を、**壁の足元の地盤**から算出して設計値へ書き戻す。

    ⚠ 2026-08-23 の検図で、落差を壁線から 1.5間(2.73m)外で測っていたことが判明した。
    段丘崖のように外へ落ち続ける縁では 2.73m 外は 1〜2m 下なので、壁が構造的に過大になる
    (TW_GenkanS で 2.03m 埋まっていた)。**測点は壁面のすぐ外(犬走りの内側)にする。**

    足元の地盤 = 低い側の段があればその段の設計高、無ければ現地形。
    s は 4s ≧ 最大落差 を満たす最小の 0.05 刻み。
    """
    if ter is None:
        return d
    OFF = 0.45                                   # 壁面から 0.25間。犬走りの内側
    for w in d["terraceWalls"]:
        (au, av), (bu, bv) = w["a"], w["b"]
        L = math.hypot(bu - au, bv - av) or 1.0
        nu_, nv_ = (bv - av) / L, -(bu - au) / L      # 壁線の法線
        ds = []
        inset = min(0.45, 0.4 * L) / L            # 端は隣の段の角を拾うので 内へ寄せる
        gk = "gapU" if abs(au - bu) > 1e-9 else "gapV"
        for i in range(41):
            t = inset + (1.0 - 2.0 * inset) * i / 40.0
            u = au + (bu - au) * t
            v = av + (bv - av) * t
            if gk in w:                          # 開口の中は壁が無いので測らない
                pos = u if gk == "gapU" else v
                if abs(pos - w[gk]) <= w.get("gapHalf", 1.0):
                    continue
            best = None
            for sg in (1.0, -1.0):
                pu, pv = u + nu_ * OFF * sg, v + nv_ * OFF * sg
                g = design_y(d, pu, pv)
                if g is None:
                    g = ter["at"](pu, pv)
                if g is None:
                    continue
                best = g if best is None else min(best, g)
            if best is not None:
                ds.append(w["coping"] - best)
        if not ds:
            continue
        w["drop"] = [round(min(ds), 2), round(max(ds), 2)]
        w["s"] = round(math.ceil(max(max(ds), 0.2) / 4.0 / 0.05) * 0.05, 2)
    return d


def obb_pts(o):
    """物の四隅を (u, v) で返す。`yaw` を持つ物は**回転矩形**、持たない物は素の矩形。

    境界が斜めに走る辺では、棟を回転間グリッドに載せたままだと「沿わせ」られない
    (2026-08-23 検図: 家中長屋が松平境と22.2°・岡部境と13.0°開いていた)。
    `uc,vc,L,D,yaw` が正典で、`u0..v1` はその外接矩形。
    """
    if "yaw" not in o:
        return [(o["u0"], o["v0"]), (o["u1"], o["v0"]), (o["u1"], o["v1"]), (o["u0"], o["v1"])]
    r = math.radians(o["yaw"])
    lu, lv = math.sin(r), math.cos(r)          # 長手(桁行)の向き
    du, dv = math.cos(r), -math.sin(r)         # 梁間の向き
    L2, D2 = o["L"] / 2.0, o["D"] / 2.0
    return [(o["uc"] + lu * L2 * a + du * D2 * b,
             o["vc"] + lv * L2 * a + dv * D2 * b) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def in_obb(o, u, v, pad=0.0):
    """(u, v) がその物の中(回転を考慮)にあるか。"""
    if "yaw" not in o:
        return (o["u0"] - pad <= u <= o["u1"] + pad) and (o["v0"] - pad <= v <= o["v1"] + pad)
    r = math.radians(o["yaw"])
    lu, lv = math.sin(r), math.cos(r)
    du, dv = math.cos(r), -math.sin(r)
    su, sv = u - o["uc"], v - o["vc"]
    return (abs(su * lu + sv * lv) <= o["L"] / 2.0 + pad and
            abs(su * du + sv * dv) <= o["D"] / 2.0 + pad)


def obb_overlap(a, b):
    """二つの矩形(回転可)が重なるか — 分離軸で判定。触れるだけは可。"""
    pa, pb = obb_pts(a), obb_pts(b)
    for poly in (pa, pb):
        for i in range(4):
            ax = poly[(i + 1) % 4][0] - poly[i][0]
            az = poly[(i + 1) % 4][1] - poly[i][1]
            nx_, nz_ = -az, ax
            la = [p[0] * nx_ + p[1] * nz_ for p in pa]
            lb = [p[0] * nx_ + p[1] * nz_ for p in pb]
            if min(la) >= max(lb) - 1e-9 or min(lb) >= max(la) - 1e-9:
                return False
    return True


def _obj_poly(pr, gr, o, **kw):
    """回転物を四隅の多角形として描く(外接矩形で描かない)。"""
    pts = [gr.W(u, v) for u, v in obb_pts(o)]
    a = '<polygon points="%s"' % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts)
    if "fill" in kw:
        a += ' fill="%s"' % kw["fill"]
    if kw.get("stroke"):
        a += ' stroke="%s" stroke-width="%.2f"' % (kw["stroke"], kw.get("sw", 1.0))
    for k2, v2 in (("dash", "stroke-dasharray"), ):
        if kw.get(k2):
            a += ' %s="%s"' % (v2, kw[k2])
    if kw.get("op") is not None:
        a += ' opacity="%.2f"' % kw["op"]
    return a + "/>"


def write_back(d):
    """生成器が算出した値(石段の段数・土留めの規模と落差)を **設計値ファイルへ書き戻す**。

    ⚠ 2026-08-23 の検図で、`fix_walls` の結果を図にだけ反映して json へ戻しておらず、
    **14本中13本の土留めが図と正典で食い違っていた**(壁高で最大 2.0m)。
    この状態で実装が json を読むと、図と違う物が建つ。算出値は必ず正典へ戻す。
    """
    def dump(o, ind=1):
        sp = " " * ind
        if isinstance(o, list):
            if all(isinstance(x, (int, float, type(None))) for x in o):
                return "[" + ", ".join("null" if x is None else "%g" % x for x in o) + "]"
            return "[\n" + ",\n".join(sp + " " + dump(x, ind + 2) for x in o) + "\n" + sp + "]"
        if isinstance(o, dict):
            return ("{\n" + ",\n".join(sp + " " + json.dumps(k, ensure_ascii=False) + ": " + dump(v, ind + 2)
                                        for k, v in o.items()) + "\n" + sp + "}")
        return json.dumps(o, ensure_ascii=False)
    cur = open(JSON, encoding="utf-8").read()
    new = dump(d) + "\n"
    if new != cur:
        open(JSON, "w", encoding="utf-8").write(new)


def retracted_check(d, texts):
    """**撤回した説の語が、設計値・生成器・図のどこかに生き残っていないか**を機械で照合する。

    3巡続けて「文章だけ直って図と正典に撤回済みの説が残る」再発をした(2026-08-24 考証第5巡)。
    禁句は設計値の `retracted` に置く。撤回の記録そのもの(「〜は反証された」の文脈)は
    別の語で書くこと。
    """
    bad = []
    for w in d.get("retracted", []):
        for label, t in texts:
            if w in t:
                bad.append("撤回済みの語「%s」が %s に残っている" % (w, label))
    return bad


def declutter(items, dy=13.0, dx=90.0):
    """(x, y, text) のラベルが重ならないよう縦にずらす。
    近い段が斜めに並ぶ帯(家中長屋)で名が団子になって読めなくなる — 2026-08-23 の目視で発覚。"""
    out = []
    for x, y, txt in sorted(items, key=lambda it: (it[1], it[0])):
        while any(abs(x - px) < dx and abs(y - py) < dy for px, py, _ in out):
            y += dy
        out.append((x, y, txt))
    return out


def dem_svg(d, dem, others, W=900.0):
    x0, z0, st = dem["x0"], dem["z0"], dem["step"]
    x1, z1 = x0 + (dem["nx"] - 1) * st, z0 + (dem["nz"] - 1) * st
    pr = Proj(x0, x1, z0, z1, W, pad=0.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "土井大隅守上屋敷 現況図(造成前の地形)")
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
            a = gr.W(s["at"], s["from"]); b = gr.W(s["at"], s["to"])
        else:
            a = gr.W(s["from"], s["at"]); b = gr.W(s["to"], s["at"])
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


def dem_legend():
    out = []
    for i, (lim, c) in enumerate(DEM_RAMP):
        lo = DEM_RAMP[i - 1][0] if i else 8
        out.append('<span><span style="display:inline-block;width:15px;height:11px;background:%s;'
                   'border:1px solid var(--rule);margin-right:4px;vertical-align:-1px"></span>%s</span>'
                   % (c, ("%d m〜" % lo) if lim == 99 else "%d–%d m" % (lo, lim)))
    out.append('<span>── 等高線 2m(太線 10m)</span>')
    out.append('<span style="color:#7A2E1E">┄ 断面の切り位置</span>')
    return "".join(out)


# ---------------------------------------------------------------- 動線
RK = {"omote": ("var(--shu)", "表向"), "yaku": ("var(--take)", "役方"),
      "katte": ("var(--nagaya)", "勝手"), "oku": ("var(--hei)", "奥向")}


def routes_svg(d, u0, u1, v0, v1):
    pr = LProj(u0, u1, v0, v1, 900.0)
    gr = RGrid(d)
    g = _sv(pr.W, pr.H, "土井大隅守上屋敷 動線")
    P = [gr.L(x, z) for x, z in d["polygon"]]
    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.5"/>'
             % " ".join("%.1f,%.1f" % (pr.X(u), pr.Y(v)) for u, v in P))
    for t in d["terraces"]:
        g.append(_obj_poly(pr, gr, t, fill=DAN.get(t["y"], "var(--dan4)"), op=1.0))
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
        g.append(_obj_poly(pr, gr, m, fill="var(--ink-mid)", stroke="var(--ink)", sw=0.6, op=0.85))
        nm = MUNE_JA.get(m.get("name"), m.get("label", ""))
        if nm and abs(m["u1"] - m["u0"]) >= 5:
            g.append(T((pr.X(m["u0"]) + pr.X(m["u1"])) / 2,
                       (pr.Y(m["v0"]) + pr.Y(m["v1"])) / 2 + 4, nm, "rmS", "middle", 11.0))
    for k in d["kaidans"]:                                   # 動線がどこで段を越えるか
        w = [x for x in d["terraceWalls"] if x["name"] == k["atWall"]][0]
        if w["a"][0] == w["b"][0]:
            cu, cv = w["a"][0], k["gapV"]
        else:
            cu, cv = k["gapU"], w["a"][1]
        g.append(pr.rect(cu - 1.0, cv - 1.0, cu + 1.0, cv + 1.0,
                         fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        g.append(T(pr.X(cu), pr.Y(cv) - 10, "%d段" % k["steps"], "anG", "middle"))
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
        # ⚠ **累積の昇り降りを密に取る。** 折れ点だけの max−min では、降りが表現できず、
        #   `design_y` が None を返す点(段の外=法面や街路)を黙って捨てるので、
        #   同じ行の「石段◯段」と数字が合わなくなる(2026-08-24 検図 中-5:
        #   表向は +3.1m と出ていたが 21段×蹴上0.27〜0.282 = 5.7〜5.9m で、実際は +5.8m)。
        #   段の外は掘割(石段)→ 現地形 の順に落とす。
        ter_r = load_terrain(os.path.join(DOC, "doi_terrain.json"))
        dem_r = load_terrain(os.path.join(DOC, "doi_dem.json"))
        we_r = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
        gr_r = RGrid(d)

        def _ry(u, v):
            y = design_y(d, u, v)
            if y is not None:
                return y
            y = stair_y(d, u, v)
            if y is not None:
                return y
            x, z = gr_r.W(u, v)
            nat = dem_bilinear(dem_r, x, z)
            if nat is None and ter_r is not None:
                nat = ter_r["at"](u, v)
            if nat is None:
                return None
            g2 = graded_y(d, u, v, nat, we_r)
            return g2 if g2 is not None else nat

        up = dn = 0.0; prev = None; lost = 0
        for a, b in zip(r["pts"], r["pts"][1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            n_r = max(2, int(seg / 0.25))
            for i in range(n_r + 1):
                u = a[0] + (b[0] - a[0]) * i / n_r
                v = a[1] + (b[1] - a[1]) * i / n_r
                y = _ry(u, v)
                if y is None:
                    lost += 1
                    continue
                if prev is not None:
                    if y > prev:
                        up += y - prev
                    else:
                        dn += prev - y
                prev = y
        rise = up - dn
        # ⚠ **縦断の最急も算出する。** `_` に手で書いた「1:8.7」が実算 1:6.2 と食い違い、
        #   「石段を切るまでもなく歩ける」という裁定の前提が崩れていた
        #   (2026-08-24 検図9巡 中-2)。⚠ 石段・斜路を含む区間はその勾配が支配するので、
        #   石段を持つ動線では「(石段を含む)」と断る。歩きの勾配として読めるのは
        #   石段0の動線(役人)だけ。
        steepest = None
        for a, b in zip(r["pts"], r["pts"][1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1]) * K
            if seg < 0.5:
                continue
            ya, yb = _ry(a[0], a[1]), _ry(b[0], b[1])
            if ya is None or yb is None:
                continue
            dh = abs(yb - ya)
            if dh < 0.02:
                continue
            gsl = seg / dh
            if steepest is None or gsl < steepest:
                steepest = gsl
        updn = "昇 %.1f / 降 %.1f" % (up, dn)
        if lost:
            updn += "(地盤の取れない標本 %d)" % lost
        # ⚠ 石段は**線分ごとでなく石段ごと**に数える。線分の箱に芯が入るたび足すと、
        #   一つの石段が2本の線分に拾われて二重に計上される(2026-08-23 検図で 29/20/38段)。
        hitk = set()
        for a, b in zip(r["pts"], r["pts"][1:]):
            for k in d["kaidans"]:
                w = [x for x in d["terraceWalls"] if x["name"] == k["atWall"]][0]
                if w["a"][0] == w["b"][0]:
                    cu, cv = w["a"][0], k["gapV"]
                else:
                    cu, cv = k["gapU"], w["a"][1]
                if min(a[0], b[0]) - 1.2 <= cu <= max(a[0], b[0]) + 1.2 and \
                   min(a[1], b[1]) - 1.2 <= cv <= max(a[1], b[1]) + 1.2:
                    hitk.add(k["name"])
        steps = sum(k["steps"] for k in d["kaidans"] if k["name"] in hitk)
        if steepest:
            updn += " ／ 区間の最急 1:%.1f%s" % (steepest, "(石段を含む)" if steps else "")
        rows.append("<tr><td><span style='color:%s'>━</span> %s</td><td>%s</td><td>%.0f m</td>"
                    "<td>%+.1f m</td><td>%d 段</td><td class='note'>%s</td></tr>"
                    % (RK.get(r["kind"], ("var(--dim)", ""))[0], r["label"],
                       RK.get(r["kind"], ("", "—"))[1], ln, rise, steps,
                       updn + " ／ " + inline(r.get("_", ""))))
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

    def gobj(o, fill, op=1.0):
        pts = [gr.W(a9, b9) for a9, b9 in obb_pts(o)]
        return ('<polygon points="%s" fill="%s" opacity="%.2f"/>'
                % (" ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts), fill, op))

    def gpoly(u0, v0, u1, v1, fill, op=1.0):
        pts = [gr.W(u0, v0), gr.W(u1, v0), gr.W(u1, v1), gr.W(u0, v1)]
        return ('<polygon points="%s" fill="%s" opacity="%.2f"/>'
                % (" ".join("%.1f,%.1f" % (pr.X(x), pr.Y(z)) for x, z in pts), fill, op))

    g.append('<polygon points="%s" fill="var(--pl-slope)" opacity="0.85"/>'
             % " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in P))
    for t in d["terraces"]:
        g.append(gobj(t, DAN.get(t["y"], "var(--dan4)")))
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
            a = gr.W(s["at"], s["from"]); b = gr.W(s["at"], s["to"])
        else:
            a = gr.W(s["from"], s["at"]); b = gr.W(s["to"], s["at"])
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
def section_note(d, sec):
    """断面の注記を**その断面が実際に切る物**から組む。

    ⚠ 手書きにすると、段や棟を動かしたときに注記だけ取り残される
    (2026-08-23 の検図で 14面中8面の注記が実際の交差と食い違っていた)。
    設計者の意図(なぜこの位置で切るか)は `sec["why"]` に書き、事実の列挙はここが作る。
    """
    at, w0, w1 = sec["at"], sec["from"], sec["to"]
    axis = sec["axis"]

    def hits(o):
        if axis == "u":
            return o["u0"] <= at <= o["u1"] and o["v1"] > w0 and o["v0"] < w1
        return o["v0"] <= at <= o["v1"] and o["u1"] > w0 and o["u0"] < w1

    def key(o):
        return o["v0"] if axis == "u" else o["u0"]

    ter = sorted([t for t in d["terraces"] if hits(t)], key=key)
    bld = sorted([m for m in d["munes"] if hits(m)]
                 + [x for x in d["service"] if hits(x)], key=key)
    walls = []
    for w in d["terraceWalls"]:
        (au, av), (bu, bv) = w["a"], w["b"]
        if axis == "u":
            ok = min(au, bu) - 1e-9 <= at <= max(au, bu) + 1e-9 and w0 <= max(av, bv) and min(av, bv) <= w1
        else:
            ok = min(av, bv) - 1e-9 <= at <= max(av, bv) + 1e-9 and w0 <= max(au, bu) and min(au, bu) <= w1
        if ok:
            walls.append(w["name"])
    parts = []
    if ter:
        parts.append("切る段: " + " → ".join("%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"])
                                              for t in ter))
    else:
        parts.append("切る段: 無し(造成しない素地だけを通る)")
    if bld:
        parts.append("棟: " + "・".join(MUNE_JA.get(b["name"], b["name"]) for b in bld))
    if walls:
        parts.append("土留め: " + "・".join("<code>%s</code>" % x for x in walls))
    note = "。".join(parts) + "。"
    if sec.get("why"):
        note += " " + sec["why"]
    return note


def section_svg(d, sec):
    gr = RGrid(d)
    K = d["const"]["ken"]
    at, ex = sec["at"], sec["vExag"]
    w0, w1 = sec["from"], sec["to"]

    def _cut(t):
        """切り線 (axis=at) と物の交線区間を返す。回転物は四隅から解く。"""
        if "yaw" not in t:
            if sec["axis"] == "u":
                return (t["v0"], t["v1"]) if t["u0"] <= at <= t["u1"] else None
            return (t["u0"], t["u1"]) if t["v0"] <= at <= t["v1"] else None
        pts = obb_pts(t)
        ai, bi = (0, 1) if sec["axis"] == "u" else (1, 0)
        hits = []
        for i9 in range(4):
            p9, q9 = pts[i9], pts[(i9 + 1) % 4]
            if (p9[ai] - at) * (q9[ai] - at) > 0 or abs(q9[ai] - p9[ai]) < 1e-12:
                continue
            t9 = (at - p9[ai]) / (q9[ai] - p9[ai])
            hits.append(p9[bi] + (q9[bi] - p9[bi]) * t9)
        if len(hits) < 2:
            return None
        lo, hi = min(hits), max(hits)
        return (lo, hi) if hi - lo > 1e-9 else None

    def covers(t):
        return _cut(t) is not None

    def span(t):
        return _cut(t)

    # 地盤 = 郭の段が最優先。natural は段の外(未造成の区間)だけ地盤線に使い、
    # 全点は現地形の破線として別に描く(検図 H-1: 段の下に natural を混ぜて跳ねさせない)
    segs = []
    for t in d["terraces"]:
        if covers(t):
            a, b = span(t)
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

    g = _sv(W, H, "土井大隅守上屋敷 %s" % sec["name"])
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
                       fill=DAN.get(y, 'var(--dan4)'), op=0.95))
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
        # 切り位置が開口の中なら壁は無い(石段・斜路・廊下が通る所)。
        # 2026-08-23 の検図で、石段の真上に壁がまたがる図が5面あった。
        gk9 = "gapU" if abs(au - bu) > 1e-9 else "gapV"
        if gk9 in w and abs(at - w[gk9]) <= w.get("gapHalf", 1.0) + 1e-9:
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

    # 土の斜路 — 断面の向きで描き分ける
    for rp in d.get("ramps", []):
        if "u0" not in rp:
            continue
        w = [x for x in d["terraceWalls"] if x["name"] == rp["atWall"]][0]
        top = w["coping"]
        lo_l, hi_l = (rp["v0"], rp["v1"])              # 長手(下る向き)は v
        lo_w, hi_w = (rp["u0"], rp["u1"])              # 幅は u
        if sec["axis"] == "v":
            # 幅を横切る断面 — その位置の**水平な踏面**を描く(勾配は見えない)
            if not (lo_l <= at <= hi_l) or not (w0 <= lo_w and hi_w <= w1):
                continue
            t = (hi_l - at) / (hi_l - lo_l)            # 上端からの割合
            y = top - rp["drop"] * t
            g.append(LN(X(lo_w), Y(y), X(hi_w), Y(y), "var(--shu)", 2.2, dash="6 3"))
            g.append(T(X((lo_w + hi_w) / 2), Y(y) - 6,
                       "%s 斜路の踏面 %.2f" % (rp["name"], y), "jo", "middle"))
        else:
            # 長手を切る断面 — 勾配そのものが見える
            if not (lo_w <= at <= hi_w) or not (w0 <= lo_l and hi_l <= w1):
                continue
            g.append('<path d="M%.1f %.1f L%.1f %.1f" fill="none" stroke="var(--shu)"'
                     ' stroke-width="2.2" stroke-dasharray="6 3"/>'
                     % (X(hi_l), Y(top), X(lo_l), Y(top - rp["drop"])))
            g.append(T(X((lo_l + hi_l) / 2), Y(top - rp["drop"] / 2) - 6,
                       "%s 斜路 1:%.0f" % (rp["name"], 1.0 / rp["grade"]), "jo", "middle"))

    # 石段(開口が切り線に掛かるもの)— 蹴上0.30×踏面0.45のギザギザ(検図 H-6)
    for k in d["kaidans"]:
        w = [x for x in d["terraceWalls"] if x["name"] == k["atWall"]][0]
        (au, av), (bu, bv) = w["a"], w["b"]
        if sec["axis"] == "u":
            if au == bu or "gapU" not in k or abs(at - k["gapU"]) > k["w"] / 2 / K:
                continue
            wp = av
        else:
            if au != bu or "gapV" not in k or abs(at - k["gapV"]) > k["w"] / 2 / K:
                continue
            wp = au
        if not (w0 <= wp <= w1):
            continue
        lo3 = -1.0 if gnd_y(max(wp - 0.5, w0)) < gnd_y(min(wp + 0.5, w1)) else 1.0
        runk = k["run"] / K
        tread = runk / k["steps"]
        pts3 = [(wp + lo3 * runk, w["coping"] - k["drop"])]
        for i3 in range(k["steps"]):
            y3 = w["coping"] - k["drop"] + (i3 + 1) * k["keriActual"]   # 蹴上は算出値(0.30固定にしない)
            pts3.append((pts3[-1][0], y3))
            pts3.append((wp + lo3 * (runk - (i3 + 1) * tread), y3))
        g.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="1.6"/>'
                 % " ".join("%.1f,%.1f" % (X(px3), Y(py3)) for px3, py3 in pts3))
        g.append(T(X(wp + lo3 * runk / 2), Y(w["coping"]) - 16, "%s %d段" % (k["name"], k["steps"]),
                   "anG", "middle"))

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
            # ⚠ **隣家が持つ辺には当家の run が無い。** ここで一律 continue していたため、
            #   95.7m の境界の基壇石垣が断面に一度も描かれなかった
            #   (2026-08-24 検図9巡 高-3)。門の開口と隣家辺を区別する。
            pl = next((q for q in d.get("boundaryPlinth", [])
                       if q["edge"] == be and q["s0"] - 0.5 <= bs <= q["s1"] + 0.5), None)
            if pl is None:
                continue                              # 門の開口
            gy = ground_at(w)
            if pl["coping"] > gy + 0.05:
                g.append(R(X(w) - sx * 0.9, Y(pl["coping"]), sx * 1.8,
                           (pl["coping"] - gy) * sx * ex,
                           fill=_pat(), stroke="var(--ishi)", sw=1.0))
            g.append(T(X(w), Y(pl["coping"]) - 5,
                       "境界の基壇 %.2f(囲いは%sの持ち物)"
                       % (pl["coping"], d.get("edgeOwner", {}).get(str(be), "隣家")),
                       "jo", "middle"))
            continue
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
                   sx * gpn["monD"] / K, gpn["monH"] * sx * ex,
                   fill="var(--shu-lo)", stroke="var(--shu)", sw=1.6))
        g.append(T(X(0), Y(d["gate"]["sill"] + gpn["monH"]) - 5, "表門", "anG", "middle"))

    # 端の囲い(polygon との交点に立つ run)
    def endlab(pos):
        for t in d["terraces"]:
            if sec["axis"] == "u":
                if t["u0"] <= at <= t["u1"] and t["v0"] <= pos <= t["v1"]:
                    return "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"])
            elif t["v0"] <= at <= t["v1"] and t["u0"] <= pos <= t["u1"]:
                return "%s %.1f" % (TERR_JA.get(t["name"], t["name"]), t["y"])
        return "素地(造成しない)"
    g.append(T(4, 15, endlab(w0) + " →", "anS"))
    g.append(T(W - 4, 15, "→ " + endlab(w1), "anS", "end"))
    g.append(T(4, H - 34, "水平は間グリッド沿い/垂直は %.1f 倍に強調。屋根は図示のための概略。"
               "視線は %s" % (ex, "南を向く(左=東の道／右=西の奥)" if sec["axis"] == "u"
                              else "西を向く(左=南の岡部境／右=北の松平境)"), "anS2", "start"))
    g.append(T(4, H - 20, "── 実線=造成後の地盤　┄┄ 破線=造成前の現地形(実測・確度P)。"
               "その間の**暖色=盛土／寒色=切土**(濃いほど厚い)。"
               "段の外は法面(盛土1:%.1f/切土1:%.1f)で現地形へ摺り付ける"
               % (d["const"].get("batterFill", 1.5), d["const"].get("batterCut", 1.0)),
               "anS2", "start"))
    g.append(T(4, H - 6, "太い緑帯=**無造成**(現地形をそのまま使う区間)。"
               "石垣ハッチ=土留め(露出高は地盤なりに変わる)", "anS2", "start"))
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
    # 展開の起点=P3(ジョグ南端)。表門を起点にすると東辺(当家の囲いの本体)が
    # 図の左右両端へ割れてしまう — 当家所有の三辺(ジョグ→楔→東辺)を一続きに読ませる。
    t0 = tv[3]

    def tt(e, s):
        return (tv[e] + s - t0) % total

    W, ex = 1120.0, 6.5
    HEAD, FOOT = 34.0, 70.0
    sx = W / total
    dob = d["const"]["dobeiH"]
    nagH = 5.3
    seats = [r["seat"] for r in d["runs"]]
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
            base_pts = [q for q in base_pts if q[1] is not None and q[1] < r["seat"]]
            if base_pts:
                poly = [(xa, Y(r["seat"])), (xb, Y(r["seat"]))] + \
                       [(X(tt(r["edge"], s2)), Y(y2)) for s2, y2 in reversed(base_pts)]
                g.append('<polygon points="%s" fill="%s" stroke="var(--ishi)" stroke-width="0.9" opacity="0.9"/>'
                         % (" ".join("%.1f,%.1f" % q for q in poly), _pat()))
        g.append(R(xa, Y(r["seat"] + h), xb - xa, h * sx * ex, fill=KC.get(r["kind"], "var(--dim)"), op=0.9))
        if r.get("nijukai"):
            g.append(R(xa, Y(r["seat"] + nagH + 2.6), 20 * 1.818 * sx, 2.6 * sx * ex,
                       fill=KC["Nagaya"], op=0.65))
            lab.append((xa, "門翼二階(海鼠壁)"))
        g.append(T((xa + xb) / 2, Y(r["seat"]) + 11, "%.1f" % r["seat"], "jo", "middle"))
        g.append(T((xa + xb) / 2, Y(r["seat"] + h) - 3, r["name"], "jo", "middle",
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
    # 隣家所有の辺(当家は建てない)のラベル
    for (ea, eb, txt) in ((6, 9, "北・西(P6〜P0)=松平出羽守所有の**練塀+石垣基壇**(全区間)。当家は建てない"),
                          (0, 2, "南(P0〜P3)=岡部内膳正所有の練塀 — 当家は建てない")):
        ta2 = (tv[ea] - t0) % total; tb2 = (tv[eb + 1] - t0) % total
        if tb2 <= ta2:
            tb2 += total
        g.append(T(X((ta2 + tb2) / 2), Y((y0 + y1) / 2), txt, "anS2", "middle"))
    # 頂点の目盛
    for i in range(n):
        t = (tv[i] - t0) % total
        g.append(LN(X(t), Y(y0), X(t), Y(y0) + 5, "var(--dim)", 0.8))
        g.append(T(X(t), Y(y0) + 15, "P%d" % i, "jo", "middle"))
    g.append(T(4, H - 22, "展開の起点=P2(ジョグ南端)— 当家所有の三辺(ジョグ→楔→東辺)を一続きに読む。"
               "天端は run ごとに一定、段は継ぎ目で落とす。表長屋 桁高 %.1fm/練塀 %.2fm。"
               "破線=道の地盤(実測)/石垣ハッチ=基壇" % (nagH, dob), "anS2", "start"))
    g.append(T(4, H - 8, "東辺の道は南へ落ちる — 表長屋(南)と練塀の基壇石垣が道へ露出する(台地肩)。"
               "楔→東辺の隅(P5)は天端同高で納め、ジョグ→楔(P4)の小さな段は高い側の基壇小口で受ける", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其七 表門まわり
def gate_svg(d):
    """長屋門の正面見付(概略)。躯体の中央に門口、両側に出格子番所、両袖は表長屋へ連続。"""
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
    # 両翼の表長屋
    for x0 in (0.0, total - wing):
        g.append(R(X(x0), Y(4.3), X(wing), 4.3 * sx, fill="var(--nagaya)", op=0.55))
        g.append(R(X(x0) - 3, Y(4.3) - 9, X(wing) + 6, 9, fill="var(--ink-lo)"))
    g.append(T(X(wing / 2), Y(4.9), "表長屋(潰=安政地震の記録)", "anS2", "middle"))
    # 長屋門の躯体(一段高い屋根)
    g.append(R(X(wing), Y(monH - 0.8), X(monW), (monH - 0.8) * sx, fill="var(--nagaya)", op=0.85))
    g.append(R(X(wing) - 4, Y(monH - 0.8) - 12, X(monW) + 8, 12, fill="var(--ink-lo)"))
    # 門口(中央)
    g.append(R(X(wing + monW / 2 - 1.8), Y(3.2), X(3.6), 3.2 * sx, fill="var(--paper2)", stroke="var(--ink)", sw=1.2))
    g.append(R(X(wing + monW / 2 - 1.7), Y(3.0), X(1.6), 3.0 * sx, fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
    g.append(R(X(wing + monW / 2 + 0.1), Y(3.0), X(1.6), 3.0 * sx, fill="var(--ink-lo)", stroke="var(--ink)", sw=0.8))
    g.append(T(X(wing + monW / 2), Y(3.4), "門口(内開き・潜り戸)", "anS2", "middle"))
    # 出格子番所(躯体内・両側)
    for cx in ((wing + monW * 0.22,) if gp["bansho"]["count"] < 2
               else (wing + monW * 0.22, wing + monW * 0.78)):
        g.append(R(X(cx - 1.6), Y(2.4), X(3.2), 1.9 * sx, fill="var(--dan)", stroke="var(--ink)", sw=1.0))
        for i in range(8):
            xx = X(cx - 1.4 + i * 0.36)
            g.append(LN(xx, Y(2.3), xx, Y(0.7), "var(--ink)", 0.8, op=0.75))
    g.append(T(X(wing + monW * 0.22), Y(2.8), "出格子番所(片)", "anS2", "middle"))
    g.append(LN(0, GY, W, GY, "var(--ink)", 1.6))
    g.append(T(4, GY + 16, "三べ坂前身の南北道。敷居=門前面の地盤=道なり", "anS2", "start"))
    g.append(T(4, 15, "正面見付(概略・等倍)。型式=長屋門【B】/屋根=切妻【B】/番所と潜戸=[下丸子武家屋敷門]A の官製「片番所格子付、片潜門」【B/U・型式をまたぐ移植】/石高帯=A/実在と被災=S", "anS"))
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
    g2.append(T(X2(wing + monW * 0.22), wy + 2, "番所(片)", "anS2", "middle"))
    # ⚠ 数値を直書きしない(2026-08-24 検図 低-4: 「門口 3.6m」は正典の門扉2間=3.636m と別値)
    g2.append(T(X2(wing + monW / 2), wy - 16,
                "門口 %.2fm" % (d["gate"]["plan"].get("doorKen", 2.0) * d["const"]["ken"]),
                "anS2", "middle"))
    g2.append(T(4, H2 - 8, "長屋門の躯体(桁行%.1fm×梁間%.1fm)に**片番所**が入る。**張り出すのは格子窓だけで、番所の室は躯体内**。袖塀は無く両袖が表長屋へ連続する【B — [西澄寺武家屋敷門]A(門長屋・一棟で完結)と [山脇武家屋敷門]A(長屋門)による。現物照合はしていない】" % (monW, monD), "anS2", "start"))
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
                       inline(p.get("note", ""))))
    return ("<h3>面と縁の対応</h3><div class='tw'><table><thead><tr><th>面</th><th>高さ</th>"
            "<th class='note'>段(造成)</th><th class='note'>縁の囲い(天端=面の高さ)</th>"
            "<th class='note'>注記</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def mune_fit(d, ter, o, dem=None):
    """棟の下の |設計面 − 自然地形| を実測して (最大Δ, 超過率%) を返す。§B-1 の合否そのもの。

    ⚠ **地形は原資料の DEM を双一次で引く。** `ter["at"]` は 1間(1.818m)格子の**最近傍**で、
    実効解像度がそれに縛られる。補間法で超過率が動くため、**合否が補間法だけで決まる状態を残さない**
    (2026-08-24 検図 中-4。実測値は図の棟の表が持つ)。
    **合否が補間法だけで決まる状態を残さない。**
    """
    if ter is None and dem is None:
        return None
    if dem is None:
        dem = load_terrain(os.path.join(DOC, "doi_dem.json"))
    gr = RGrid(d)
    ds = []
    for i in range(41):
        for j in range(21):
            if "yaw" in o:
                r = math.radians(o["yaw"])
                lu, lv = math.sin(r), math.cos(r); du, dv = math.cos(r), -math.sin(r)
                a = -o["L"] / 2 + o["L"] * i / 40.0; b = -o["D"] / 2 + o["D"] * j / 20.0
                u = o["uc"] + lu * a + du * b; v = o["vc"] + lv * a + dv * b
            else:
                u = o["u0"] + (o["u1"] - o["u0"]) * i / 40.0
                v = o["v0"] + (o["v1"] - o["v0"]) * j / 20.0
            x, z = gr.W(u, v)
            n = dem_bilinear(dem, x, z)
            if n is None and ter is not None:
                n = ter["at"](u, v)
            if n is not None:
                ds.append(o["y"] - n)
    if not ds:
        return None
    mx = max(ds, key=abs)
    return mx, 100.0 * sum(1 for x in ds if abs(x) > 0.5) / len(ds)


def munes_table(d, ter=None):
    rows = []
    K = d["const"]["ken"]
    for m in d["munes"]:
        kw, kd = abs(m["u1"] - m["u0"]), abs(m["v1"] - m["v0"])
        area = kw * kd * K * K
        # 土間・板敷は畳を敷かないので畳数に混ぜない(2026-08-23 検図)。間²で別立てにする。
        tat = sum(r["tatami"] for r in m["rooms"] if not r.get("ita"))
        ita = sum(r["tatami"] // 2 for r in m["rooms"] if r.get("ita"))
        ft = mune_fit(d, ter, m)
        fitc = "—" if ft is None else ("%+.2f m / %.0f%%" % ft if ft[1] > 0 else "%+.2f m / 0%%" % ft[0])
        rows.append("<tr><td>%s</td><td><code>%s</code></td><td>%s</td><td>%d×%d間</td>"
                    "<td>%.0f m²</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td></tr>"
                    % (MUNE_JA.get(m["name"], m["name"]), m["name"], m["zone"], kw, kd,
                       area, len(m["rooms"]), tat, ("%d 間²" % ita) if ita else "—", fitc))
    return ('<div class="tw"><table><thead><tr><th>棟</th><th>名</th><th>ゾーン</th><th>外形</th>'
            "<th>面積</th><th>室数</th><th>畳数計(座敷)</th><th>土間・板敷</th><th>切盛の最大Δ / ±0.5m超の割合</th></tr></thead><tbody>"
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
    gs = sum((s["L"] * s["D"]) if "yaw" in s else abs(s["u1"] - s["u0"]) * abs(s["v1"] - s["v0"])
             for s in d["service"]) * K * K
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
            "<tr><td>付属屋(家中長屋・米蔵・土蔵・稲荷)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>表長屋(奥行%.1fm)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>門の躯体(番所を含む)+木戸</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td><b>計</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            "<tr><td><b>敷地(分母)</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            '<tr><td><b>建蔽率</b></td><td colspan="2"><b>%.1f%%</b></td></tr>'
            "</tbody></table></div>"
            % (gm, gm / TSUBO, gl, gl / TSUBO, gs, gs / TSUBO, d["const"]["nagayaD"],
               nag, nag / TSUBO, ban + yag + mon, (ban + yag + mon) / TSUBO,
               tot, tot / TSUBO, area, area / TSUBO, 100.0 * tot / area)), 100.0 * tot / area




def edge_step_check(d, dem):
    """**段の縁に受けの無い垂直段差が残っていないか**を測る。`_batter` の宣言そのものの検査。

    ⚠ 検査を書いたら**感度試験で必ず確かめる**。この関数の前身2つはどちらも恒真だった —
    ①区画外で `graded_y` が現地形を返すので差が定義上ゼロ、
    ②区画の辺は全て run か隣家の塀が載るので除外で空になる(2026-08-24 検図第6巡)。
    いまは**区画の内側の、段の縁**を測る。土留めが載る区間と、隣家が持つ区画の辺は除く
    (そこは構造が受ける)。
    """
    if dem is None:
        return ["⚠ doi_dem.json が無いので段の縁を測れない"]
    gr = RGrid(d)
    we = {t["name"]: walled_edges(d, t) for t in d["terraces"]}
    lim = d["const"]["stepAbsorbMax"]
    bad = []
    for t in d["terraces"]:
        for edge in ("u0", "u1", "v0", "v1"):
            lo, hi = (t["v0"], t["v1"]) if edge in ("u0", "u1") else (t["u0"], t["u1"])
            line = t[edge]
            sgn = -1.0 if edge in ("u0", "v0") else 1.0
            worst = 0.0; spot = None
            n = max(6, int(hi - lo))
            for i in range(n + 1):
                q = lo + (hi - lo) * i / float(n)
                if _walled(we[t["name"]], edge, q):
                    continue
                if edge in ("u0", "u1"):
                    ui, vi = line - sgn * 0.06, q
                    uo, vo = line + sgn * 0.06, q
                else:
                    ui, vi = q, line - sgn * 0.06
                    uo, vo = q, line + sgn * 0.06
                gi = design_y(d, ui, vi)
                if gi is None or abs(gi - t["y"]) > 0.01:
                    continue
                if design_y(d, uo, vo) is not None:
                    continue                        # 隣が段 — adjacency_check の担当
                wx, wz = gr.W(uo, vo)
                no = dem_bilinear(dem, wx, wz)
                if no is None or not in_parcel(d, uo, vo):
                    continue                        # 区画の外 — 隣家の塀が受ける
                go = graded_y(d, uo, vo, no, we)
                if go is None:
                    continue
                if abs(gi - go) > abs(worst):
                    worst = gi - go; spot = (uo, vo)
            if abs(worst) > lim and spot:
                bad.append("段の縁に受けの無い段差 %s の %s: %+.2fm (グリッド %.1f, %.1f)"
                           % (t["name"], edge, worst, spot[0], spot[1]))
    return bad


def _walled_at(d, we, u, v):
    """(u, v) の最寄りの段の縁に土留めが載っているか(粗い判定)。"""
    for t in d["terraces"]:
        if not in_obb(t, u, v, 0.6):
            continue
        for (edge, lo, hi) in we[t["name"]]:
            q = v if edge in ("u0", "u1") else u
            if lo - 0.6 <= q <= hi + 0.6:
                return True
    return False


def mune_fit_check(d, ter):
    """**棟の下の |設計面 − 自然地形| ≤ 0.5m**(§B-1 の合否)を検査にする。

    表に出しただけでは、棟を動かしたときに悪化しても誰も気づかない
    (2026-08-24 の感度試験で、居間棟を1間ずらしても検査が反応しなかった)。
    超過の**割合**が 5% を超えたら止める(0% を求めると地形の粒度に負ける)。
    """
    bad = []
    for m in d["munes"] + d["service"]:
        r = mune_fit(d, ter, m)
        if r and r[1] > 5.0:
            bad.append("棟の下の切盛が %.0f%% で ±0.5m を超える(最大 %+.2fm): %s" % (r[1], r[0], m["name"]))
    return bad


NEIGHBOUR = {"岡部": ("okabe_sashizu.json", (8, 9)),
             "松平": ("matsudaira_sashizu.json", (0, 1, 2, 3))}


def wall_needed_check(d, dem):
    """**土留めが要る所に土留めがあるか**を測る。壁を消しても法面が黙って代わりを務めるので、
    「壁が要るかどうか」はどの検査も見ていなかった(2026-08-24 検図第7巡: 14本中3本は消しても無反応)。

    段の縁のうち**壁も開口も無い区間**で、法面が現地形に着地するのに要る水平距離が
    段の外の余地(次の物・区画線まで)を超えるなら、そこは法面では持たない=土留めが要る。
    開口の中も同じ理屈で見る(開口幅から通る物を引いた分に受けが無ければ段差が残る)。
    """
    if dem is None:
        return []
    gr = RGrid(d)
    we = {t["name"]: walled_edges(d, t) for t in d["terraces"]}
    bf = d["const"].get("batterFill", 1.5)
    cap = d["const"].get("featherCap", 12.0)
    K = d["const"]["ken"]
    bad = []
    for t in d["terraces"]:
        for edge in ("u0", "u1", "v0", "v1"):
            lo, hi = (t["v0"], t["v1"]) if edge in ("u0", "u1") else (t["u0"], t["u1"])
            line = t[edge]
            sgn = -1.0 if edge in ("u0", "v0") else 1.0
            worst = 0.0; spot = None
            n = max(6, int(hi - lo))
            for i in range(n + 1):
                q = lo + (hi - lo) * i / float(n)
                if _walled(we[t["name"]], edge, q):
                    continue
                if edge in ("u0", "u1"):
                    uo, vo = line + sgn * 0.3, q
                else:
                    uo, vo = q, line + sgn * 0.3
                if not in_parcel(d, uo, vo) or design_y(d, uo, vo) is not None:
                    continue
                wx, wz = gr.W(uo, vo)
                no = dem_bilinear(dem, wx, wz)
                if no is None:
                    continue
                need = (t["y"] - no) * bf                 # 法面が着地するのに要る水平距離(m)
                if need <= 0.3:
                    continue
                # 段の外に、その水平距離ぶんの**余地**があるか(区画線・他の段まで)
                room = 0.0
                step = 0.5
                while room < min(need, cap) + step:
                    if edge in ("u0", "u1"):
                        pu, pv = line + sgn * (0.3 + room / K), q
                    else:
                        pu, pv = q, line + sgn * (0.3 + room / K)
                    if not in_parcel(d, pu, pv) or design_y(d, pu, pv) is not None:
                        break
                    room += step
                if need - room > 1.0 and need - room > worst:
                    worst = need - room; spot = (uo, vo)
            if spot:
                bad.append("土留めが要る: %s の %s — 法面の着地に %.1fm 足りない"
                           " (グリッド %.1f, %.1f)" % (t["name"], edge, worst, spot[0], spot[1]))
    return bad


def neighbour_wall_check(d, ter, dem=None):
    """**隣家が持つ辺で、隣家の塀が当家側の地盤に埋まっていないか**を毎回測る。

    `edgeOwner` を設計値に置いただけでは死値だった(2026-08-24 検図第7巡: どこからも参照されず)。
    ⚠ **20m 刻みの手作業の標本は run の継ぎ目を飛ばす** — 実測 0.21m と報告していた岡部 `N_Hei1` は、
    0.5m 刻みで測ると **5.80m** 埋まっていた。**継ぎ目を含む細かい刻みで、run ごとの最大を出す。**
    """
    if ter is None:
        return []
    gr = RGrid(d)
    we = {t["name"]: walled_edges(d, t) for t in d["terraces"]}
    bad = []
    for who, (fn, edges) in NEIGHBOUR.items():
        path = os.path.join(DOC, fn)
        if not os.path.exists(path):
            continue
        nb = json.load(open(path, encoding="utf-8"))
        P = nb["polygon"]
        for r in nb.get("runs", []):
            if r.get("edge") not in edges:
                continue
            a, b = P[r["edge"]], P[(r["edge"] + 1) % len(P)]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            ex, ez = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx_, nz_ = -ez, ex
            mu, mv = gr.L((a[0] + b[0]) / 2 + nx_ * 3, (a[1] + b[1]) / 2 + nz_ * 3)
            sg = 1.0 if in_parcel(d, mu, mv) else -1.0
            worst = -9e9; at_s = None; at_off = None
            n = max(4, int((r["s1"] - r["s0"]) / 0.5))
            for i in range(n + 1):
                sq = r["s0"] + (r["s1"] - r["s0"]) * i / float(n)
                t = sq / L
                if t > 1.0:
                    break
                x, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                # ⚠ **塀の足元で測る。** かつて 1.4m 内側で測っており、境界が上り斜面だと
                #   その勾配ぶんが丸ごと「埋没」に化けた(2026-08-24 第8巡: 6件中1件が
                #   偽陽性で、残る5件も過大。松平 S_Hei_Doi_W3 は境界線上では ±0.01m で
                #   合っていたのに 0.89m 埋没と報告していた)。
                #   1.4m 内側は犬走りの位置であって、塀の足元ではない。
                #   地形が欠ける所だけ、値の取れる最寄りの内側へ寄せて、寄せた距離を報告する。
                g = None; off = None
                oq = d["const"].get("neighbourProbe", 0.3)
                _omax = d["const"].get("neighbourProbeMax", 1.5) + 0.0001
                while oq <= _omax:
                    px, pz = x + nx_ * oq * sg, z + nz_ * oq * sg
                    u, v = gr.L(px, pz)
                    nn = dem_bilinear(dem, px, pz)
                    if nn is None:
                        nn = ter["at"](u, v)
                    if nn is not None:
                        g = design_y(d, u, v)
                        if g is None:
                            g = graded_y(d, u, v, nn, we)
                        if g is not None:
                            off = oq
                            break
                    oq += 0.1
                if g is None:
                    continue
                # ⚠ **天端は run の中で按分する**(相手の生成器の `rseat` が正典)。
                #   辺の全長 L で按分していたため、s0>0 の run や辺より短い run で
                #   まるで違う天端と比べていた(2026-08-24 第8巡)。
                #   岡部 N_Hei1 は 5.82m 埋没と報告していたが、run 内按分では合格する。
                # ⚠ 隣家の run は `seat` を持たず `seat0`/`seat1` だけのことがある
                s0 = r.get("seat0", r.get("seat")); s1 = r.get("seat1", r.get("seat"))
                if s0 is None or s1 is None:
                    continue
                tr = 0.0 if r["s1"] <= r["s0"] else (sq - r["s0"]) / (r["s1"] - r["s0"])
                seat = s0 + (s1 - s0) * max(0.0, min(1.0, tr))
                if g - seat > worst:
                    worst = g - seat; at_s = sq; at_off = off
            if at_s is not None and worst > 0.05:
                bad.append("%s の %s が当家側の地盤に %.2fm 埋まる(相手の s=%.1f・境界から %.1fm 内側で実測)"
                           % (who, r["name"], worst, at_s, at_off))
    return bad


def inubashiri_check(d):
    """**棟の縁と、それが載る段の縁の離れ(犬走り)**を検める。

    ⚠ 犬走りは**長辺(軒側)に1間**。桁行の端は隣の段と接して帯になるので 0.5間 でよい
    (2026-08-24 検図: 長屋の帯で端も1間にすると段どうしが重なる)。
    宣言した不変条件には必ず検査を付ける — 以前は宣言だけで8棟が満たしていなかった。
    """
    LONG, END = 1.0, 0.5
    bad = []
    for m in d["munes"] + d["service"]:
        host = None
        for t in d["terraces"]:
            if abs(t["y"] - m["y"]) > 0.01:
                continue
            if all(in_obb(t, u, v, 1e-9) for u, v in obb_pts(m)):
                host = t
                break
        if host is None:
            continue
        if "yaw" in m and "yaw" in host:
            # ⚠ **芯ずれを入れて測る。** (L-l)/2 だけで見ると棟をずらしても値が変わらず、
            #   偽合格を作れた(2026-08-24 検図 中-1)。host のローカル軸へ四隅を射影する。
            r9 = math.radians(host["yaw"])
            lu, lv = math.sin(r9), math.cos(r9)
            du, dv = math.cos(r9), -math.sin(r9)
            aa = []; bb = []
            for u9, v9 in obb_pts(m):
                su, sv = u9 - host["uc"], v9 - host["vc"]
                aa.append(su * lu + sv * lv); bb.append(su * du + sv * dv)
            end = min(host["L"] / 2.0 - max(aa), min(aa) + host["L"] / 2.0)
            side = min(host["D"] / 2.0 - max(bb), min(bb) + host["D"] / 2.0)
        else:
            du0, du1 = m["u0"] - host["u0"], host["u1"] - m["u1"]
            dv0, dv1 = m["v0"] - host["v0"], host["v1"] - m["v1"]
            if (m["v1"] - m["v0"]) >= (m["u1"] - m["u0"]):    # 長手は v
                side, end = min(du0, du1), min(dv0, dv1)
            else:
                side, end = min(dv0, dv1), min(du0, du1)
        if side < LONG - 1e-9:
            bad.append("犬走り(長辺側)が %.2f間 しかない: %s(1間引く)" % (side, m["name"]))
        elif end < END - 1e-9:
            bad.append("犬走り(桁行の端)が %.2f間 しかない: %s(0.5間引く)" % (end, m["name"]))
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

    def covered(u0, v0, u1, v1, y, o=None):
        uu = u0 + 0.25
        while uu < u1:
            vv = v0 + 0.25
            while vv < v1:
                if o is not None and not in_obb(o, uu, vv):
                    vv += 0.5
                    continue                       # 回転矩形の外接部分は対象外
                if not inside(uu, vv):
                    return (uu, vv)
                ok = any(in_obb(t, uu, vv, eps) and
                         (y is None or abs(t["y"] - y) < 0.01) for t in ters)
                if not ok:
                    return (uu, vv)
                vv += 0.5
            uu += 0.5
        return None

    def obj_out(o):                                # 回転を考えた四隅で区画の外を見る
        e2 = 0.05
        cu0, cv0 = (o["uc"], o["vc"]) if "yaw" in o else ((o["u0"] + o["u1"]) / 2, (o["v0"] + o["v1"]) / 2)
        for (cu, cv) in obb_pts(o):
            qu = cu + (cu0 - cu) * e2
            qv = cv + (cv0 - cv) * e2
            if not inside(qu, qv):
                return (qu, qv)
        return None

    bad = []
    for m in d["munes"] + d["service"]:
        nm = m.get("name", m.get("label"))
        pt = obj_out(m)
        if pt:
            bad.append("%s が区画の外: グリッド(%.2f, %.2f)" % (nm, pt[0], pt[1]))
            continue
        pt = covered(m["u0"], m["v0"], m["u1"], m["v1"], m["y"], m)
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
    for rl in d["rails"]:
        for (uu, vv) in rl["pts"]:
            if not pt_in(uu, vv):
                bad.append("%s(竹垣) の端点が区画の外: (%g, %g)" % (rl["name"], uu, vv))
    return bad


def _union_len(segs):
    """区間の並びの**合併**の長さ。重なりを二重に数えない。"""
    ss = sorted((min(x, y), max(x, y)) for x, y in segs if abs(x - y) > 1e-9)
    out = 0.0
    cur_a = cur_b = None
    for a, b in ss:
        if cur_b is None or a > cur_b:
            if cur_b is not None:
                out += cur_b - cur_a
            cur_a, cur_b = a, b
        elif b > cur_b:
            cur_b = b
    if cur_b is not None:
        out += cur_b - cur_a
    return out


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
                # ⚠ **開口は壁が無い。** `walled_edges` は開口で割るのに、こちらは割って
                #   いなかった(2026-08-24 検図 高-2: 土留めの開口を**辺の全長**へ広げても
                #   0件のままで、同じ形状を walled_edges は「壁が無い」・こちらは「壁がある」と
                #   判定して矛盾していた)。**受けの長さは開口を抜いた合併で数える。**
                segs = []
                for w in W:
                    (wa_u, wa_v), (wb_u, wb_v) = w["a"], w["b"]
                    wp = (wa_u, wb_u) if p == "u" else (wa_v, wb_v)
                    wq = (wa_v, wb_v) if p == "u" else (wa_u, wb_u)
                    if abs(wp[0] - wp[1]) > 1e-9 or abs(wp[0] - line) > 1e-9:
                        continue
                    if abs(w["coping"] - hi_y) > 0.05:
                        continue
                    s_lo = max(lo, min(wq)); s_hi = min(hi, max(wq))
                    if s_hi - s_lo <= 1e-9:
                        continue
                    gk = "gapU" if q == "u" else "gapV"
                    if gk in w:
                        gh = w.get("gapHalf", 1.0)
                        g0, g1 = w[gk] - gh, w[gk] + gh
                        if g0 > s_lo:
                            segs.append((s_lo, min(s_hi, g0)))
                        if g1 < s_hi:
                            segs.append((max(s_lo, g1), s_hi))
                        # 開口そのものは**開いているのが正しい** — 石段や廊下が通るため。
                        # 高い側の土は両端で直角に振れる**袖石垣**が受ける。
                        # 袖が設計値にある開口だけを「受けた」と数える
                        # (袖を消すと件数が増えることを感度試験で確かめてある)。
                        _sp = pass_span(d, w)[0]
                        if "sode" in w and _sp:
                            # **通る物+両袖ぶんだけ**を受けと数える。開口の丸めで
                            # 広がったぶんは受けでない。
                            # ⚠ **hull(min..max)で取らない。** 一つの開口を二つ以上の物が
                            #   通ると、その**間の何も無い区間**まで受けと数えてしまう
                            #   (2026-08-24 検図9巡 高-2: TW_ShuG で 1.18m の
                            #   1.60m 垂直面が素で残り、断面③と⑰の間に落ちて
                            #   どの図にも現れなかった)。**物ごとに袖を足して合併する。**
                            for _a, _b in _sp:
                                c0 = max(s_lo, g0, _a - 0.3)
                                c1 = min(s_hi, g1, _b + 0.3)
                                if c1 > c0:
                                    segs.append((c0, c1))
                    else:
                        segs.append((s_lo, s_hi))
                held = _union_len(segs)
                # ⚠ 両側とも「段」なので、ここには法面が入らない(design_y は最大値を採る)。
                #    摺り付けで済むのは蹴上1段ぶん(const.stepAbsorbMax)まで。
                #    2026-08-23 の検図で、Δ=1.00 ちょうどが厳密不等号を抜けて
                #    16m の垂直段差が受け無しで残っていた。
                if held < (hi - lo) - 0.5 and abs(a["y"] - b["y"]) > d["const"]["stepAbsorbMax"]:
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
        boxes.append(("mune", m["name"], m["u0"], m["v0"], m["u1"], m["v1"], None))
    for l in d["links"]:
        boxes.append(("link", l["name"], l["u0"], l["v0"], l["u1"], l["v1"], None))
    for n in d["gardens"]:
        boxes.append(("niwa", n["name"], n["u0"], n["v0"], n["u1"], n["v1"], None))
    for s in d["service"]:
        boxes.append(("svc", s["name"], s["u0"], s["v0"], s["u1"], s["v1"], s))
    # 外周 run と長屋門の躯体帯(表門の辺=グリッドの v=0 帯)。検図 H-3 で追加 —
    # 入れないと表長屋の奥行(4.5m)に厩などが食い込んでも素通しになる。
    ken2 = d["const"]["ken"]
    sg = d["gate"]["s"]
    for r in d["runs"]:
        if r["edge"] != d["gate"]["edge"]:
            continue
        depth = d["const"]["nagayaD"] if r["kind"] == "Nagaya" else d["const"]["dobeiT"]
        boxes.append(("run", r["name"], (r["s0"] - sg) / ken2, 0.0,
                      (r["s1"] - sg) / ken2, depth / ken2, None))
    gp2 = d["gate"]["plan"]
    boxes.append(("run", "Nagayamon", -gp2["monW"] / 2 / ken2, 0.0,
                  gp2["monW"] / 2 / ken2, gp2["monD"] / ken2, None))
    # 斜路と井戸。検図 2026-08-23 第3巡 — 箱に入れていなかったので、
    # 斜路が厩棟を貫き、井戸2基が棟の中に立っていても素通しだった。
    for rp in d.get("ramps", []):
        if "u0" in rp:
            boxes.append(("ramp", rp["name"], rp["u0"], rp["v0"], rp["u1"], rp["v1"], None))
    for wl in d.get("wells", []):
        boxes.append(("ido", wl["name"], wl["u"] - 0.5, wl["v"] - 0.5, wl["u"] + 0.5, wl["v"] + 0.5, None))
    bad = []
    # 段どうしが重なっていないか。design_y は最大値を採るので、低い方の段は図上にしか
    # 存在しなくなり、そこに建つ棟が地盤に埋まる(2026-08-23 検図で家中長屋(南)2棟が全部
    # 主面に食われ、0.2m 埋まって建っていた)。
    TT = d["terraces"]
    for i8 in range(len(TT)):
        for j8 in range(i8 + 1, len(TT)):
            a8, b8 = TT[i8], TT[j8]
            if abs(a8["y"] - b8["y"]) < 0.05:
                continue                          # 同じ高さなら同一の面 — 重なっても消えない
            iu = min(a8["u1"], b8["u1"]) - max(a8["u0"], b8["u0"])
            iv = min(a8["v1"], b8["v1"]) - max(a8["v0"], b8["v0"])
            if iu > 1e-9 and iv > 1e-9 and obb_overlap(a8, b8):
                bad.append("段 %s(%.1f) と %s(%.1f) が %.1f×%.1f間 重なる — 低い方は地盤として存在しない"
                           % (a8["name"], a8["y"], b8["name"], b8["y"], iu, iv))
    # 石段と屋内の階段廊下が同じ場所を占めていないか
    for k8 in d["kaidans"]:
        # ⚠ 参照が切れていても**落ちない**。以前は KeyError/IndexError で生成ごと止まり、
        #   検査を感度試験に掛けること自体ができなかった(2026-08-24 検図 低-6)。
        #   切れた参照は refs_check が指摘する。
        w8 = next((x for x in d["terraceWalls"] if x["name"] == k8.get("atWall")), None)
        if w8 is None:
            continue
        hw = k8["w"] / 2 / ken2
        rn = k8["run"] / ken2
        if abs(w8["a"][0] - w8["b"][0]) < 1e-9:
            kb = (w8["a"][0] - rn, k8["gapV"] - hw, w8["a"][0] + rn, k8["gapV"] + hw)
        else:
            kb = (k8["gapU"] - hw, w8["a"][1] - rn, k8["gapU"] + hw, w8["a"][1] + rn)
        for l8 in d["links"]:
            iu = min(kb[2], l8["u1"]) - max(kb[0], l8["u0"])
            iv = min(kb[3], l8["v1"]) - max(kb[1], l8["v0"])
            if iu > 0.2 and iv > 0.2:
                bad.append("石段 %s と階段廊下 %s が %.1f×%.1f間 重なる — 同じ落差を二つの構造物で登っている"
                           % (k8["name"], l8["name"], iu, iv))
    # 段が外周 run の躯体帯へ食い込んでいないか(座が食い違うと建屋の中に石垣が立つ)
    for r in d["runs"]:
        if r["edge"] != d["gate"]["edge"]:
            continue
        depth = d["const"]["nagayaD"] if r["kind"] == "Nagaya" else d["const"]["dobeiT"]
        r0, r1 = (r["s0"] - sg) / ken2, (r["s1"] - sg) / ken2
        for t in d["terraces"]:
            iu = min(r1, t["u1"]) - max(r0, t["u0"])
            iv = min(depth / ken2, t["v1"]) - max(0.0, t["v0"])
            if iu > 1e-9 and iv > 1e-9 and abs(t["y"] - r["seat"]) > 0.05:
                bad.append("段 %s(%.1f) が外周 %s(座 %.1f)の躯体帯へ %.1f×%.2f間 食い込む"
                           % (t["name"], t["y"], r["name"], r["seat"], iu, iv))
    # 土留め(線分)が棟・廊下に開口なしで刺さっていないか。
    # 竹垣にだけ同種の検査があり土留めに無かったため、廊下3本が壁を貫いていた(検図 2026-08-23 H-6)。
    for w in d.get("terraceWalls", []):
        (wa, wb) = w["a"], w["b"]
        gu = w.get("gapU"); gv = w.get("gapV"); gh = w.get("gapHalf", 0.0)
        for (k1, n1, a0, b0, a1, b1, _o1) in boxes:
            if k1 not in ("mune", "link"):
                continue
            hit = 0
            for i9 in range(81):
                t9 = i9 / 80.0
                pu = wa[0] + (wb[0] - wa[0]) * t9
                pv = wa[1] + (wb[1] - wa[1]) * t9
                if not (a0 + 1e-9 < pu < a1 - 1e-9 and b0 + 1e-9 < pv < b1 - 1e-9):
                    continue
                if gu is not None and abs(pu - gu) <= gh + 1e-9:
                    continue                      # 開口の中は可
                if gv is not None and abs(pv - gv) <= gh + 1e-9:
                    continue
                hit += 1
            if hit > 1:
                bad.append("土留め %s が %s %s に開口なしで刺さる(%.0f%%の区間)"
                           % (w["name"], k1, n1, 100.0 * hit / 81))
    # 動線が土留めを開口の外で横切っていないか(検図 2026-08-23)
    for r in d.get("routes", []):
        for (a, b) in zip(r["pts"], r["pts"][1:]):
            for w in d.get("terraceWalls", []):
                (wa, wb) = w["a"], w["b"]
                gu = w.get("gapU"); gv = w.get("gapV"); gh = w.get("gapHalf", 0.0)
                vert = abs(wa[0] - wb[0]) < 1e-9
                p0, p1 = (a[0], b[0]) if vert else (a[1], b[1])
                line = wa[0] if vert else wa[1]
                if (p0 - line) * (p1 - line) > 0 or abs(p1 - p0) < 1e-9:
                    continue
                t9 = (line - p0) / (p1 - p0)
                q = a[1] + (b[1] - a[1]) * t9 if vert else a[0] + (b[0] - a[0]) * t9
                lo, hi = (min(wa[1], wb[1]), max(wa[1], wb[1])) if vert else \
                         (min(wa[0], wb[0]), max(wa[0], wb[0]))
                if not (lo - 1e-9 <= q <= hi + 1e-9):
                    continue
                g9 = gv if vert else gu
                if g9 is not None and abs(q - g9) <= gh + 1e-9:
                    continue
                bad.append("動線 %s が土留め %s を開口の外で横切る(%s=%.2f)"
                           % (r["label"], w["name"], "v" if vert else "u", q))
    # 竹垣(線分)が建屋を貫通していないか — 箱どうしの総当たりでは拾えない
    for rl in d.get("rails", []):
        for (a, b) in zip(rl["pts"], rl["pts"][1:]):
            for (k1, n1, a0, b0, a1, b1, _o1) in boxes:
                if k1 == "run":
                    continue
                hit = 0.0
                for i9 in range(41):
                    t9 = i9 / 40.0
                    pu = a[0] + (b[0] - a[0]) * t9
                    pv = a[1] + (b[1] - a[1]) * t9
                    if a0 + 1e-9 < pu < a1 - 1e-9 and b0 + 1e-9 < pv < b1 - 1e-9:
                        hit += 1
                if hit > 1:
                    bad.append("竹垣 %s が %s %s を貫通(%.0f%%の区間)"
                               % (rl["name"], k1, n1, 100.0 * hit / 41))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            k1, n1, a0, b0, a1, b1, o1 = boxes[i]
            k2, n2, c0, d0, c1, d1, o2 = boxes[j]
            iu = min(a1, c1) - max(a0, c0)
            iv = min(b1, d1) - max(b0, d0)
            # 回転を持つ物は外接矩形でなく**分離軸**で見る(斜めに並ぶ家中長屋で誤検出する)
            if iu > 1e-9 and iv > 1e-9 and (o1 is not None or o2 is not None):
                q1 = o1 if o1 is not None else {"u0": a0, "v0": b0, "u1": a1, "v1": b1}
                q2 = o2 if o2 is not None else {"u0": c0, "v0": d0, "u1": c1, "v1": d1}
                if not obb_overlap(q1, q2):
                    continue
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
                    (nk, na, n0, n1_, n2_, n3, _n), (sk, sa, s0, s1_, s2_, s3, _s) = \
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
    for rp in d.get("ramps", []):
        w = [x for x in d["terraceWalls"] if x["name"] == rp["atWall"]][0]
        c = gr.W(w["a"][0], rp["gapV"]) if w["a"][0] == w["b"][0] else gr.W(rp["gapU"], w["a"][1])
        rows.append("<tr><td><code>%s</code></td><td>土の斜路 1:%.0f(幅 %.2fm)</td>"
                    "<td>芯 (%.1f, %.1f)</td><td>落差 %.1f・走り %.2fm</td></tr>"
                    % (rp["name"], 1.0 / rp["grade"], rp["w"], c[0], c[1], rp["drop"], rp["run"]))
    for rl in d["rails"]:
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        rows.append("<tr><td><code>%s</code></td><td>竹垣(四つ目垣 h0.9)</td>"
                    "<td class='note'>%s</td><td>法肩から内へ %.2fm</td></tr>"
                    % (rl["name"], " → ".join("(%.1f, %.1f)" % p for p in pts),
                       d["const"]["inubashiri"] * d["const"]["ken"]))
    # ⚠ **隣家が持つ辺の基壇石垣を表に出す。** 95.7m あるのに、どの図・表・部材表にも
    #   出ていなかった(2026-08-24 検図9巡 高-3)。当家が建てる囲い(東辺+ジョグ+楔=93.0m)
    #   より長い土木構造物が無図だった。
    P = d["polygon"]
    own = d.get("edgeOwner", {})
    for q in d.get("boundaryPlinth", []):
        a, b = P[q["edge"]], P[(q["edge"] + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        p0 = (a[0] + (b[0] - a[0]) * q["s0"] / L, a[1] + (b[1] - a[1]) * q["s0"] / L)
        p1 = (a[0] + (b[0] - a[0]) * q["s1"] / L, a[1] + (b[1] - a[1]) * q["s1"] / L)
        rows.append("<tr><td><code>基壇 辺%d</code></td>"
                    "<td>境界の基壇石垣(丁場 %.2f・壁高 %.2fm)</td>"
                    "<td class='note'>(%.1f, %.1f) → (%.1f, %.1f)</td>"
                    "<td>延長 %.1fm・受ける盛土 %.2fm・天端 %.2f</td></tr>"
                    % (q["edge"], q["s"], 4 * q["s"], p0[0], p0[1], p1[0], p1[1],
                       q["s1"] - q["s0"], q["drop"], q["coping"]))
    if d.get("boundaryPlinth"):
        rows.append("<tr><td colspan='4' class='note'>"
                    "隣家(%s)が持つ辺の内側 %.2fm に回す石垣。**塀は建てない**(二重塀にしない)。"
                    "盛りが %.2fm 以下の区間は退がりで摺り付くので基壇を置かない。計 %.1fm。"
                    "</td></tr>"
                    % ("・".join(sorted(set(own.get(str(q["edge"]), "?")
                                            for q in d["boundaryPlinth"]))),
                       d["const"].get("neighbourProbe", 0.3),
                       d["const"].get("boundaryFeather", 0.20),
                       sum(q["s1"] - q["s0"] for q in d["boundaryPlinth"])))
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
    """門構えの部材位置。長屋門は一体の躯体なので芯と両端を出す。"""
    P = d["polygon"]
    g = d["gate"]; gp = g["plan"]
    dx, dz, _ = _edge_dir(P, g["edge"])
    rows = []
    for nm, s_off in [("長屋門(芯)", 0.0),
                      ("躯体 南端(表長屋 南との継ぎ)", -gp["monW"] / 2),
                      ("躯体 北端(表長屋 北との継ぎ)", gp["monW"] / 2)]:
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
            "<p class='cap'>長屋門は袖塀を介さず**両袖がそのまま表長屋へ連続**する(番所は躯体内・出格子)。</p>")


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
             "--pretty=%h|%ad|%s", "--", "docs/Sashizu/doi_sashizu.json",
             "docs/Sashizu/doi_kosho.md"]).decode()
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


# 生成器が正典へ書き戻す欄。**往復試験**はここを全消去して組み直す。
# ⚠ **「その物が在ること」は入力、「その寸法」が出力。** 両方消すと生成器が処理を飛ばし、
#   偽陽性になる(開口の有無 `gapU`/`gapV`、階段廊下であること `links.steps` は入力側)。
#   芯や幅は毎回上書きされるので、消さなくても古い値は検出できる。
GEN_FIELDS = {
    "terraceWalls": ("drop", "s", "sode", "_sodeRoom", "gapHalf", "_pitch"),
    "kaidans": ("steps", "run", "keriActual"),
    "links": ("keriActual",),
}


def roundtrip_check(raw, pipeline):
    """**生成器が書く欄を全消去 → 再生成 → 正典と一致するか。**

    ⚠ 入力側を動かす感度試験では、**生成器が消さない出力欄は どの変異でも生き延びる**。
    2026-08-25 の検図10巡で、前の版が書いた `sode` が2本の壁に残り続け、
    `opening_fit_check` と `adjacency_check` を黙らせていた
    — 「機械検査すべて0件」が**古い値に支えられていた**。
    入力を動かす試験は10通りすべてこれを素通りした。**要るのはこの往復試験。**
    """
    import copy
    stripped = copy.deepcopy(raw)
    for coll, keys in GEN_FIELDS.items():
        for o in stripped.get(coll, []):
            for k in keys:
                o.pop(k, None)
    stripped.pop("boundaryPlinth", None)
    rebuilt = pipeline(stripped)
    bad = []
    for coll, keys in GEN_FIELDS.items():
        by = dict((o["name"], o) for o in rebuilt.get(coll, []))
        for o in raw.get(coll, []):
            r = by.get(o["name"])
            if r is None:
                bad.append("%s %s が組み直しで消える" % (coll, o["name"]))
                continue
            for k in keys:
                a, b = o.get(k), r.get(k)

                def _num(q):            # int と float を同じ物として比べる
                    return [_num(x) for x in q] if isinstance(q, list) else (
                        float(q) if isinstance(q, (int, float)) and not isinstance(q, bool) else q)
                a, b = _num(a), _num(b)
                if isinstance(a, float) and isinstance(b, float):
                    if abs(a - b) > 1e-6:
                        bad.append("%s %s.%s 正典=%.4f 組み直し=%.4f" % (coll, o["name"], k, a, b))
                elif json.dumps(a, sort_keys=True, ensure_ascii=False) != \
                        json.dumps(b, sort_keys=True, ensure_ascii=False):
                    bad.append("%s %s.%s 正典=%s 組み直し=%s"
                               % (coll, o["name"], k,
                                  json.dumps(a, ensure_ascii=False)[:60],
                                  json.dumps(b, ensure_ascii=False)[:60]))
    na, nb = len(raw.get("boundaryPlinth", [])), len(rebuilt.get("boundaryPlinth", []))
    if na != nb:
        bad.append("boundaryPlinth の本数 正典=%d 組み直し=%d" % (na, nb))
    return bad


def main():
    _raw = json.load(open(JSON, encoding="utf-8"))

    def _pipeline(x):
        x = fix_kaidans(x)
        x = fix_walls(x, load_terrain(os.path.join(DOC, "doi_terrain.json")))
        x = snap_openings(x)            # 開口の縁を石垣のピッチ格子へ・芯は通る物から
        x = fix_sode(x)                 # 開口の両端の袖石垣
        x = fix_boundary_plinth(x, load_terrain(os.path.join(DOC, "doi_dem.json")))
        return x

    rtbad = roundtrip_check(_raw, _pipeline)
    d = _pipeline(json.load(open(JSON, encoding="utf-8")))
    write_back(d)
    if rtbad:
        print("⚠ 往復試験の不一致 %d 件 — **正典に生成器が再現できない値が残っている**:" % len(rtbad))
        for b in rtbad:
            print("   ", b)                       # 算出した値は**正典へ戻す**(図だけが新しい状態を作らない)
    raw = open(MD, encoding="utf-8").read()
    blk, miss = sources_block(raw)
    raw = raw.replace("{{典拠一覧}}", blk)
    raw = raw.replace("{{隣家の表}}", neighbour_block(
        d, load_terrain(os.path.join(DOC, "doi_terrain.json")),
        load_terrain(os.path.join(DOC, "doi_dem.json"))))
    prose = md2html(raw)
    if miss:
        print("⚠ 台帳に無い典拠 ID(文章)%d 件: %s" % (len(miss), " / ".join(miss)))
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

    bad = overlap_check(d)
    if bad:
        print("⚠ 矩形の重なり %d 件:" % len(bad))
        for b in bad:
            print("   ", b)
    pbad = (plane_check(d) + inubashiri_check(d) + opening_fit_check(d) + refs_check(d)
            + norms_check(d) + perimeter_check(d) + clearance_check(d) + rails_check(d)
            + boundary_fill_check(d, load_terrain(os.path.join(DOC, "doi_dem.json")))
            + mune_fit_check(d, load_terrain(os.path.join(DOC, "doi_terrain.json")))
            + edge_step_check(d, load_terrain(os.path.join(DOC, "doi_dem.json")))
            + wall_needed_check(d, load_terrain(os.path.join(DOC, "doi_dem.json"))))
    nbad = neighbour_wall_check(d, load_terrain(os.path.join(DOC, "doi_terrain.json")),
                                load_terrain(os.path.join(DOC, "doi_dem.json")))
    if nbad:
        print("── 隣家の宿題(当家では直せない)%d 件:" % len(nbad))
        for b in nbad:
            print("   ", b)
    if pbad:
        print("⚠ 面のはみ出し %d 件:" % len(pbad))
        for b in pbad:
            print("   ", b)
    wbad = wall_check(d)
    if wbad:
        print("⚠ 土留めの高さ %d 件:" % len(wbad))
        for b in wbad:
            print("   ", b)

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ['<meta charset="utf-8">', "<title>土井大隅守上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">外桜田永田町 ／ 譜代・雁間 二万三千石 上屋敷</p>')
    h.append("<h1>土井大隅守上屋敷 指図</h1>")
    h.append('<div class="box" style="border-color:var(--shu);margin-top:14px"><h3>基準年次と確度</h3><p>'
             '<b>基準年次=嘉永3年(1850)</b> — 基図(尾張屋版切絵図)の年次。安政2年の地震記録は'
             '「倒れる前の姿」として遡って使う。所在と屋敷の別は [寛政武鑑 刈谷]A の上屋敷の欄'
             '(寛政元年。嘉永3年への外挿は B)。<br>'
             '<b>当主=土井利善</b>(弘化4年家督・大隅守/嘉永5-6年は大坂加番で江戸不在/安政5年奏者番)。<br>'
             '<b>外周の構成は当屋敷の一次記録から直接言える(確度S)</b> — 安政江戸地震の被害書上5点が'
             '「表門倒・玄関大破」「表長屋潰」「外構練塀潰」を記す。<b>ただし3邸一括の記事で、'
             'どの辺の塀か・誰の所有かは書かれていない</b> — 確定するのは<b>種別だけ</b>。<br>'
             '屋敷指図(建物平面)は現存未確認 — 御殿の構成は類型(B)、室名・畳数は想定(?)。'
             '書院は<b>雁間詰の城主</b>で作り、帝鑑間格へ上げない'
             '(殿席=雁間は [安政地震被害書上]S・岡本家文書が雁間の部に列挙)。'
             '区画多角形はユーザーのブックマーク角(U)。</p></div>')
    h.append('<p class="lede"><b>この文書は現況だけを載せる。</b>過去の案・撤回した説は書かない — '
             '経緯は <code>git log docs/Sashizu/</code> で追う。'
             '寸法の正典は <code>doi_sashizu.json</code>、文章は <code>doi_kosho.md</code>、'
             'この HTML は <code>Tools/Sashizu/build_doi_sashizu.py</code> が組む。'
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

    plate(h, nx(), "敷地", "%.0f m²(%.0f坪)/規定坪数は『青標紙』2〜3万石=2,700坪([西川1959]A)/記録坪数5,417坪2合([大江戸今昔めぐり 岡部区画]B)に対し区画実測4,422坪はU由来で18%%小さい — 坪数比は格の議論に使わない/江戸間 1間=%.3fm/グリッドは東辺(表門の辺)沿いの回転フレーム"
          % (area, area / TSUBO, d["const"]["ken"]))
    plane_legend = "".join(
        '<span style="color:%s">■ %s%s</span>'
        % (PLANE_COL.get(p["name"], "var(--dan4)"), p["name"],
           (" %.1f" % p["y"]) if p["y"] is not None else "(松+雑木の樹林)")
        for p in d.get("planes", []))
    fig(h, plan_svg(d),
        legend=plane_legend
               + '<span style="color:var(--nagaya)">━ 表長屋</span>'
               '<span style="color:var(--hei)">━ 練塀</span>'
               '<span style="color:var(--take)">┄ 竹垣(法肩)</span>'
               '<span style="color:var(--ishi)">┄ 郭の土留め</span>'
               '<span>▪ 御殿の棟 ／ ▫ 付属屋</span>'
               '<span style="color:var(--shu)">● 表門 ／ ○ 御成門 ／ ■ 隅櫓 ／ ┄ 断面</span>',
        cap="<b>敷地の面は自然の平場から採る。</b>造成も囲いも面から決め、囲いの天端=面の高さ。"
            "面の高さは自然地形の段(ベンチ)に載せて盛土を抑える。"
            "<b>面の高さと縁の位置は自然地形の段(ベンチ)と法肩から決めた</b> — "
            "切盛は [菊地2003] の 1〜4m の内。**量は切盛の節の表で読む**(ここに数値を写さない)。"
            "<b>南東の低み・下段と上段を分ける段丘崖・南西の谷の頭・西の低みは造成しない</b> — "
            "樹林と庭のまま、面の縁に竹垣。斜面の植生は松+雑木(竹林にしない=[橋本・堀1998])。"
            "東辺の道は南へ大きく落ちるので、表長屋(南)の基壇石垣が道へ露出する(台地肩)。"
            "<b>街路・隣地への影響はゼロ</b> — 面の造成は区画線で切り、境界の高低差は垂直の基壇石垣で受ける。")
    h.append(planes_table(d))
    h.append('<p class="cap"><b>面のはみ出し検査(0.5間刻みの被覆): %s。</b>'
             '棟・付属屋・廊下は自分の y と同じ高さの段の中に、庭・井戸はいずれかの段の中に'
             '完全に載っていることを機械検査している。</p>'
             % ("<b>0 件</b>" if not pbad else "⚠ %d 件 — %s" % (len(pbad), " / ".join(pbad))))
    h.append(slope_table(d))
    h.append("</div>")

    dem = load_terrain(os.path.join(DOC, "doi_dem.json"))
    if dem:
        pc = {}
        try:
            for q in json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))["parcels"]:
                pc[q["id"]] = q
        except Exception:
            pass
        others = []
        dx0, dz0 = dem["x0"], dem["z0"]
        dx1 = dx0 + (dem["nx"] - 1) * dem["step"]
        dz1 = dz0 + (dem["nz"] - 1) * dem["step"]
        for pid, col, wdt, lab in (("okabe", "#C0392B", 2.0, "岡部内膳正 上屋敷"),
                                   ("matsudaira_dewa", "#2E6DA4", 2.0, "松平出羽守 上屋敷")):
            if pid in pc:
                q = [(a, b) for a, b in pc[pid]["pts"]]
                # ラベルは区画の重心でなく **図に写っている範囲** の重心に置く。
                # 隣地は DEM の枠からはみ出すので、重心だと枠外に落ちて名が消える
                # (2026-08-23 検図: 岡部の区画線は出ているのに名が出ていなかった)。
                vis = [(a, b) for a, b in q if dx0 <= a <= dx1 and dz0 <= b <= dz1]
                src = vis if len(vis) >= 2 else q
                cx = sum(a for a, _ in src) / len(src)
                cz = sum(b for _, b in src) / len(src)
                cx = min(max(cx, dx0 + 20), dx1 - 20)
                cz = min(max(cz, dz0 + 12), dz1 - 12)
                others.append((q, col, wdt, lab, cx, cz))
        P0 = d["polygon"]
        others.append((P0, "#D68910", 2.8, "土井大隅守 上屋敷",
                       sum(a for a, _ in P0) / len(P0), sum(b for _, b in P0) / len(P0)))
        plate(h, nx(), "現況図(造成前の地形)",
              "国土地理院 DEM 由来の現地形を Unity から実測 ／ 段彩 2m ／ 等高線 2m(太線 10m)【確度P】")
        fig(h, dem_svg(d, dem, others), legend=dem_legend(),
            cap="<b>造成する前の、いまの土地の姿。</b>2026-08-22 に地形を作り直して造成を自然地形へ戻した"
                "状態を、2m 格子で実測して段彩と等高線に起こした(確度P)。"
                "<b>この図が造成のすべての出発点</b> — 面の高さも縁の位置も、ここに見える"
                "自然のベンチと法肩から決めている。切盛図はこの地形と設計の差を塗ったもの。"
                "細い破線は断面の切り位置。座標は Unity の世界座標(m)。")
        h.append("</div>")

    ter = load_terrain(os.path.join(DOC, "doi_terrain.json"))
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
        plate(h, nx(), "切盛(どこを盛り、どこを切るか)",
              "盛土 %.0f m³(最大 %.1fm) ／ 切土 %.0f m³(最大 %.1fm) ／ 差引 %+.0f m³"
              % (vf, mf, vc, mc, vf - vc))
        fig(h, cf, legend=cutfill_legend(),
            cap="<b>造成前の地形(2026-08-23 実測・確度P)と造成後の地盤の差</b>を1間の格子で塗った。"
                "暖色=盛土/寒色=切土/無彩=±0.3m以内(実質さわらない)/"
                "地の色(薄い緑)のまま=<b>造成しない</b>。破線の枠は段、細い実線は御殿の棟。"
                "<b>面の高さを自然のベンチに載せてあるので、郭の大半は無彩か薄い色になる</b> — "
                "濃く出るのは門前の道なりへの摺り付け・北隅の高み・門の軸の窪みを埋める区間だけ。")
        h.append(cutfill_table(d, ter))
        h.append('<p class="cap">段の外へこぼれる法面(盛土 1:%.1f/切土 1:%.1f)も土量に含む。'
                 '土留めのある辺は壁が垂直に受けるので法面を出さない。'
                 '[菊地2003] の江戸城下67遺跡の集成では土地改変は <b>1〜4m が多数</b>で、'
                 '当屋敷は盛土 %.1fm・切土 %.1fm に収まる。'
                 '<b>差引が正=土が足りない</b>ので、切土で出た土を盛土へ回してなお不足する量。</p>'
                 % (d["const"]["batterFill"], d["const"]["batterCut"], mf, mc))
        h.append("</div>")
    plate(h, nx(), "御殿平面", "室名・畳数は【確度 ?】— 当屋敷の指図は現存未確認・類型からの想定")
    fig(h, goten_plan(d, -30, 28, -3, 80, "御殿平面",
                      "廊下は入側・渡廊下とも幅一間。奥向へ入る廊下は御錠口の一本だけ"),
        legend='<span style="color:var(--roka)">■ 入側・渡廊下(幅一間)</span>'
               '<span style="color:var(--shu)">■ 御錠口</span>'
               '<span style="color:var(--niwa)">■ 庭</span>'
               '<span style="color:var(--shirasu)">■ 白洲</span>'
               '<span>┄ 襖線(続き間の境)</span>',
        cap="<b>長屋門 → 白洲 → 石段 → 前庭の白洲 → 石段 → 玄関の郭(窪み) → 御式台。</b>"
            "**外の石段は二つだけ** — 玄関を窪みの高さに置いたので三つ目が要らなくなった。"
            "<b>表役所は門を入って南、下段の郭に建つ</b>(自然のベンチにほぼ素で載る面)。"
            "北へ書院(上段12畳=雁間詰の城主)、南へ台所と土蔵(勝手裏)、奥に居間・奥棟。"
            "<b>安政地震で「玄関大破」</b>の玄関がこの棟。")
    h.append("</div>")

    if d.get("routes"):
        plate(h, nx(), "動線(表門を入ってからどう動くか)", "系統4つ ／ すべて【設計判断U】")
        fig(h, routes_svg(d, -26, 22, -4, 66),
            legend="".join('<span style="color:%s">━ %s</span>' % (c, n) for c, n in
                           [RK["omote"], RK["yaku"], RK["katte"], RK["oku"]]),
            cap="<b>門の軸(朱)が屋敷の背骨。</b>表門から御式台まで一本で通し、登るほど格が上がる — "
                "白洲 → 石段%d段 → 前庭の白洲 → 石段%d段 → 玄関の郭 → 御式台。**外の石段は二つ**。"
                % tuple(next(k["steps"] for k in d["kaidans"] if k["name"] == n9)
                        for n9 in ("K_Monzen", "K_Genkan")) +
                "<b>役方(緑)は下段だけを通るので石段を一つも使わない</b> — 毎日の出入りを段で妨げないために"
                "表役所を門前面(下段)に置いた。奥向(青)へ入る廊下は御錠口の一本だけ。")
        h.append(routes_table(d))
        h.append('<p class="cap"><b>勝手(茶)は通用門から入る</b> — 表長屋(北)の潜りで、'
                 '<b>ここが街路と屋敷内が水平で取り付く唯一の点</b>。米も薪も表門と'
                 '門内の白洲・御式台前の白洲のいずれも通らない。'
                 '⚠ ただし<b>米蔵は通用門より一段高く、荷は石段を上げる</b> — 街路は北端でも'
                 '米蔵の郭の高さまで登らないので、当敷地では段差なしの搬入が成立しない。'
                 '蔵は石段の上り口の直上に寄せて担ぎ距離を最短にしてある('
                 '[高知2000] の援用は「直近」に限り、「段差なし」は満たさないと明示する)。</p>')
        h.append("</div>")

    plate(h, nx(), "副郭の平面(拡大)", "全体平面では読めない犬走り・石段の取り合い・竹垣の位置を出す")
    fig(h, goten_plan(d, -30, -2, -2, 34, "下段の郭(門前面・表役所の郭)",
                      "門前面19.2 と表役所の郭。段丘崖の肩と家中長屋(表)の帯"),
        cap="<b>門を入って南へ折れる下段。</b>表役所・厩・家中長屋(表)がここに載る。"
            "石段を一つも使わずに役所へ達する動線(役方)がこの面で完結する。"
            "南東の縁は <code>TW_SE</code> と <code>TW_MinamiS</code> が受け、その天端に竹垣が立つ。")
    fig(h, goten_plan(d, -2, 22, -2, 34, "前庭面と米蔵の郭(北隅)",
                      "前庭21.9 / 米蔵の郭24.7。通用門から蔵への取り合い"),
        cap="<b>門の軸の踊り場と、通用門の受け皿。</b>前庭の白洲から石段11段で玄関の郭へ登る。"
            "北は <code>TW_Kita</code> を越えて米蔵の郭 — <b>通用門(表長屋(北)の潜り)の直近に米蔵</b>を置き、"
            "[高知2000]A の「米蔵は搬出入門の直近」に従う(⚠ 原文は大坂蔵屋敷。**江戸上屋敷への適用はB・位置はU**)。勝手はここから書院の郭を経て台所へ回り、"
            "御式台前の白洲を通らない。")
    fig(h, goten_plan(d, 16, 33, 48, 82, "家中長屋の帯(北・松平境沿い)",
                      "帯は棟ごとに自然の高さを採る。境界が斜めなので棟を継いで沿わせる"),
        cap="<b>松平出羽守との境に沿う家中長屋。</b>境界が回転間グリッドに対して斜めなので、"
            "<b>棟の長軸を境界に平行にして回転グリッドの外に置いた</b>(2026-08-23 の是正。"
            "差は 0.00°)。棟ごとにその位置の自然の高さを面にしてあり、切盛は6棟とも"
            "±0.5m 以内に全域が収まる。段が階段状に上がって見えるのが正しい。"
            "帯の内側は主面の北東肩で、造成しない。"
            "<b>⚠ 家中長屋の規模は未検算</b> — 必要床面積の典拠が無い(石高→軍役→江戸詰人数の"
            "比率に典拠がなく、当家の江戸詰人数の史料も無い)。<b>延長は外周に回した結果</b>であって、"
            "収容力から逆算した数字ではない【確度U】。")
    fig(h, goten_plan(d, -6, 20, 24, 48, "玄関の郭と書院の郭",
                      "窪みをそのまま面にした玄関の郭(25.0)と、その東の帯(26.0)。1.0mの差は階段廊下"),
        cap="<b>御殿の表向が二つの標高に分かれる所。</b>玄関棟は窪みに素で載り、書院棟は"
            "北東の横長の帯に載る。1.0m の差は屋内の階段廊下で越えるので、"
            "**外の石段は使わない**。境の <code>TW_Shoin</code> は<b>辺の全長に回す</b> — "
            "両側とも段なので法面が入らず、壁の無い区間は垂直段差のまま残る。")
    fig(h, goten_plan(d, -21, -11, 54, 78, "家中長屋の帯(南・岡部境沿い)",
                      "岡部境沿いの二棟。土蔵・南庭との取り合い"),
        cap="<b>岡部内膳正との境に沿う家中長屋。</b>北の帯と同じく<b>長軸を境界に平行</b>にし、"
            "棟ごとに自然の高さを採る。高さは主面と同じなので段差は無い。"
            "東は台所棟の勝手裏で、土蔵二棟がこの間に入る。"
            "岡部との共有境界は<b>両指図の区画多角形が 0.00m で一致</b>しており、"
            "囲いは岡部が全区間に持つ(当家は建てない)。")
    h.append("</div>")

    plate(h, nx(), "棟と室", "1間²=2畳 ／ 室名・畳数は【確度 ?】(土間・板敷は間²)")
    h.append(munes_table(d, load_terrain(os.path.join(DOC, "doi_terrain.json"))))
    h.append(links_table(d))
    kp_html, kp = kenpei(d, area)
    nagL = sum(r["s1"] - r["s0"] for r in d["runs"] if r["kind"] == "Nagaya")
    perim = sum(math.hypot(P[(i + 1) % len(P)][0] - P[i][0], P[(i + 1) % len(P)][1] - P[i][1])
                for i in range(len(P)))
    h.append("<h3>建蔽率</h3>")
    h.append(kp_html)
    ownL = sum(math.hypot(P[(e + 1) % len(P)][0] - P[e][0], P[(e + 1) % len(P)][1] - P[e][1])
               for e in (3, 4, 5))
    h.append('<p class="cap"><b>分母は敷地全体。</b>可建地に替えて数字を作らない。'
             '<b>大名上屋敷の建蔽率の史料値は [福井図] の5〜6割の一点しかなく</b>、当図はそれより'
             '大きく低い(広い拝領地・門前と前庭の白洲・奥庭・造成しない斜面が敷地の3割超・'
             '家中長屋は外周に回した結果として出る延長)。'
             '[追川2017] の表長屋の規模比(加賀 15%% / 小浜 28.6%% / 尾張市谷 47.7%%)は'
             '<b>分母の定義が原典未確認のため直接比較しない</b>(sources.md の⚠)。参考値として、'
             '当家所有の囲い %.0fm に占める表長屋は %.1f%%、外周全長 %.0fm に対しては %.1f%%'
             '(外周の約8割が隣家所有の塀のため、後者は構造的に低く出る)。'
             '<b>建蔽率は結果であって目標ではない</b> — 数字のために空地へ棟を足さない。<br>'
             '⚠ <b>御殿の床面積が石高の差に出ていない</b> — 御殿の棟(入側とも)は隣の岡部'
             '(5万3千石)より広い。検算の条件([高知2000]A「24万2千石の上屋敷でも表御殿614坪」)は'
             '表向3棟で満たすが、<b>中奥・奥向まで含めた総量を石高で絞る根拠は台帳に無い</b>。'
             '縮めていないのは設計判断で、<b>判断したことをここに書いておく</b>【確度U】。'
             '(岡部の値は自作なので norm にしない。)</p>'
             % (ownL, 100.0 * nagL / ownL, perim, 100.0 * nagL / perim))
    h.append("</div>")

    for axis, ttl, lead in (
        ("u", "断面(東西・道から奥へ)",
         "道(東)から敷地の奥(西)へ %d 本。南から北の順に並べる — 下段のベンチ・段丘崖・"
         "台地・西の低みがどう入れ替わるかを読む"),
        ("v", "断面(南北・岡部境から松平境へ)",
         "南(岡部境)から北(松平境)へ %d 本。道側から奥の順に並べる — "
         "**下段と上段を分ける段丘崖が u=-8〜-2 を斜めに走る**のがこの向きで見える")):
        ss = [s for s in d["sections"] if s["axis"] == axis]
        plate(h, nx(), ttl, "%d 面 ／ 垂直はいずれも %.1f 倍" % (len(ss), ss[0]["vExag"]))
        h.append('<p class="cap">%s。</p>' % (lead % len(ss)))
        fig(h, key_plan(d, axis), cap="<b>切り位置</b>。朱の実線がこの節の断面、細い破線がもう一方の節の断面。")
        for s in ss:
            h.append('<h3>%s</h3>' % s["name"])
            fig(h, section_svg(d, s), cap=section_note(d, s))
        h.append('<p class="cap"><b>段のつなぎ方は平面だけでは読めない。</b>地表下の色帯=面(其一と同じ色分け)。'
                 '<b>破線=造成前の現地形</b>(2026-08-23 実測・確度P)なので、実線との差がそのまま切土/盛土。'
                 '区画線上には当家所有の囲い(表長屋/練塀)だけを天端と基壇石垣つきで示す — '
                 '南北の境は隣家所有のため空けてある。基壇は境界線上に垂直に立ち、道・隣地の地形には触れない。'
                 '屋根は図示のための概略で、実装の高さは部材が決める(突き合わせの対象外)。</p>')
        h.append("</div>")

    plate(h, nx(), "外周の展開", "天端は辺ごとに一本。段は門・頂点・郭境の延長線でのみ落とす")
    fig(h, perimeter_dev_svg(d))
    h.append(runs_table(d))
    h.append('<p class="cap">表長屋は<b>表(東辺)だけ</b> — 表=表長屋+長屋門、ジョグ・楔=練塀'
             '(当家所有の囲いはこの三辺のみ)。東辺南端は南東の低み(非造成)の前で内側に面が無いため、'
             '表長屋でなく<b>道なりの練塀</b>とする。北・西の囲いは松平所有、南は岡部所有'
             '(屋敷境の囲いは1条・隣家持ちの裁定)。<b>西辺は全区間が練塀+石垣基壇</b> — '
             '松平の指図で「相手のある屋敷境は斜面でも練塀で通す」と改められた(2026-08-23)。'
             '犬走り %.2fm。</p>'
             % d["const"]["inubashiri"])
    h.append("</div>")

    plate(h, nx(), "表門まわり", "長屋門・切妻造(片番所・格子付・片潜門)。型式=B(表長屋の実在S+[山脇武家屋敷門]A)/屋根=B(型式からの帰結)/番所と潜戸=B/U(型式をまたぐ移植)/石高帯=A([下丸子武家屋敷門]の都教委掲示)/実在と被災=S")
    fig(h, gate_svg(d),
        cap="<b>番所と潜戸の形式</b>は [下丸子武家屋敷門](A)の官製構造形式"
            "「<b>片番所格子付、片潜門</b>」による【B/U — 型式をまたぐ移植。下記】。東京都教育委員会の掲示が"
            "「遺存例の少ない<b>1〜5万石の小大名格</b>の形式」と明記しており、二万三千石はこの帯に入る。"
            "<b>⚠ 番所は張り出さない</b> — 官製は「格子付」で、現物でも壁面から出るのは庇付きの格子窓だけ、"
            "番所の室は躯体内に納まる。室ごと一間張り出すのは山脇門(5万石・「片流<b>面出</b>番所附属」)の姿で、"
            "下の段に持ち込むと格が1段上がる。番所と潜戸はともに<b>向かって左</b>、右は板壁のみ【現物1件=P/U】。"
            "⛔ ただし「1〜5万石」は所有者から出た数字ではなく<b>都教委が形式から下した判定</b>で、"
            "元の屋敷の伝承は三説あって互いに矛盾する — <b>独立検証ではない</b>。"
            "安政二年の被害書上は「表門倒」— 嘉永期の姿として<b>倒れる前の門</b>を建てる。"
            "⚠ <b>「表門倒」と「表長屋潰」を独立門の証拠に使わない</b> — 二語は別々の文書に現れるもので"
            "一つの記事の中で対比されておらず、長屋門でも門と長屋は別の名で呼ばれる。"
            "<b>型式は長屋門を採る</b>【B】 — 当家の表長屋の実在(S)と、最も格の近い官製現物"
            "[山脇武家屋敷門](A・<b>5万石・譜代・上屋敷</b>)の「長屋門…<b>切妻造</b>」による。"
            "⚠ <b>下丸子門の入母屋造は採らない</b> — 同門が長屋門か独立門かが官製文言から定まらず、"
            "<b>その屋根をどう説明するかは留保する【確度?】</b>。台帳から言えるのは"
            "「<b>長屋門の官製現物2件([山脇武家屋敷門]A・[西澄寺武家屋敷門]A)はいずれも切妻</b>」までで、当家は長屋門を"
            "採るのでその線に従う。⛔ <b>「独立門=入母屋」という一般化は採らない</b> — "
            "[赤門]A(独立の三間薬医門)が<b>切妻造</b>で反証になる。同門から採るのは"
            "<b>番所と潜戸の形式</b>だけで、それも<b>型式をまたぐ移植なので確度 B/U</b>。"
            "桁行・梁間・門戸部の間数は<b>いまも確度U</b>(下丸子門の実測は Web に無く館内閲覧が要る)。"
            "長屋門は在庫に無いので新造(部材表参照)。石垣畳出は使わない(設計判断)。")
    h.append("</div>")

    plate(h, nx(), "郭の土留めと竹垣")
    h.append(walls_table(d))
    h.append('<p class="cap">造成しない斜面へ向く縁の法肩には<b>竹垣(四つ目垣)</b>を回す — '
             '落差のある生活面を素の縁にしない(岡部指図と同じ作法)。寸法・控えは取り合いの表のとおり。'
             '<b>土留めは落差のある縁にだけ置く</b> — 天端と法尻の差は 2026-08-23 に実測で確かめ、'
             '落差の無い縁(主面の南舌部の縁・主面南翼の南縁・主面の西縁)は<b>土留めを置かず竹垣だけ</b>にした'
             '(地中に埋まる壁を作らない)。いちばん高いのは玄関の郭の南縁 <code>TW_GenkanS</code> で、'
             '下段(表役所の郭)へ落ちる段丘崖を受ける。</p>')
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

    plate(h, nx(), "考証と決めごと")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, "改訂", "", "経緯はここに書かず git で追う")
    h.append(history())
    h.append("</div>")

    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>doi_sashizu.json</code> ／ '
             '文章 <code>doi_kosho.md</code>。Y は海抜 m(Unity の Y がそのまま標高)。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    body = "\n".join(h)
    # ⚠ 生の `**…**` を図に出さない。設計値の `_`/`note` は table のセルへ素で入る所があり、
    #   キャプションにも手書きの `**` が混じる(2026-08-23 検図 L-1 で19箇所)。
    #   <style> の中は触らない(CSS のコメントに `**` が入る)。
    i0 = body.find("<style>"); i1 = body.find("</style>")
    head, css, rest = body[:i0], body[i0:i1], body[i1:]
    rest = re.sub(r"\*\*(.{1,200}?)\*\*", r"<b>\1</b>", rest, flags=re.S)
    rest = re.sub(r"~~(.{1,200}?)~~", r"<s>\1</s>", rest, flags=re.S)
    open(OUT, "w", encoding="utf-8").write(head + css + rest)
    # ⚠ 検査の穴を3つ塞いだ(2026-08-24 考証第6巡):
    #   ①文章(doi_kosho.md)を見ていなかった ②図は**太字変換後**を見ていたので `**` で
    #   分断された禁句を外していた ③検出しても書き出し済みで終了コードも0だった。
    d2 = {k: v for k, v in d.items() if k not in ("retracted", "_retracted")}
    flat = re.sub(r"[*~`]", "", json.dumps(d2, ensure_ascii=False))
    rbad = retracted_check(d, [
        ("設計値", flat),
        ("文章", re.sub(r"[*~`]", "", open(MD, encoding="utf-8").read())),
        ("生成器", re.sub(r"[*~`]", "", open(__file__, encoding="utf-8").read())),
        ("図", re.sub(r"[*~`]", "", body)),
    ])
    if rbad:
        print("⚠ 撤回済みの説が残っている %d 件 — **図は書き出したが要修正**:" % len(rbad))
        for b in rbad:
            print("   ", b)
        sys.exit(2)
    # ⚠ **典拠 ID の照合も「図」を見る。** 文章(md)だけを照合していたため、
    #   生成器のべた書きで出る図の冒頭箱に、撤回済みの典拠(天保9年武鑑・「同時代史料2点」)が
    #   生き残っていた(2026-08-25 考証第8巡 高⑤)。**機械照合の死角を残さない。**
    #   ソースを直接走査すると Python の添字 `d["name"]` を拾うので、**出力を見る。**
    head_, tbl_ = sources_index()
    txt_ = re.sub(r"<[^>]+>", " ", body)
    ids_ = set(re.findall(r"\[([^\]\n]{2,24})\]", txt_))
    miss2 = sorted(i for i in ids_ if i not in head_ and i not in tbl_)
    if miss2:
        print("⚠ 台帳に無い典拠 ID(図)%d 件: %s" % (len(miss2), " / ".join(miss2)))
        sys.exit(2)
    print("wrote %s (%.0f KB) — 図版 %d 面 — 建蔽率 %.1f%%" % (OUT, os.path.getsize(OUT) / 1024, _SVN[0], kp))
    if bad:
        print("⚠ 重なり %d 件 — 検図の前に直すこと" % len(bad))
    print("  run: 検図(edo-kosho / edo-kenzu) → ユーザーのレビュー → 実装 → 突き合わせ")


if __name__ == "__main__":
    main()
