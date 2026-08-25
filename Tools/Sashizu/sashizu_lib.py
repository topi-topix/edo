# -*- coding: utf-8 -*-
"""指図生成器(build_*_sashizu.py)の共通ライブラリ。

置くものは二種類:

1. **バイト同一を実証した共通部**(R / Proj / RGrid / cf_color / DEM まわり等)。
   4本の生成器から、空白正規化なしの完全一致で同一と実証できたものを移した。
2. **検査の正典**(2026-08-26 裁定「適切な厳しさにした上で統一する」)。
   `overlap_check` / `kenpei` / `design_y` / `md2html` は最も厳しい版(概ね土井)を
   基準にここで一本化した。**判定・閾値は既存4実装のいずれかに在ったものだけ**で
   構成する(新しい検査を発明しない)。パラメタの既定は厳しい側に置き、
   邸固有の正当な差(建蔽率の行ラベル、考証 md の方言)は引数で吸収する。
   岡部・松平で新たに落ちる項目は**修正せず一覧で報告**(同裁定)。

据え置き(統一すると意味が変わるため、裁定の据え置き条項で各生成器に残す):
- `graded_y` — 岡部は「縁の盛土厚の逓減形」(cbee45a)、土井は「一定勾配+着地判定+
  斜路・石段の先読み」で、**法面の物理モデルそのものが別**。どちらへ寄せても
  切盛図・断面・土量の数値が変わる。
- 山王の `design_y` — 世界座標・多角形の段・法面まで一体の実質 graded_y。

- `_SVN` は SVG 図版番号のカウンタ。各生成器の `_sv()`(図版を開く関数、生成器ごとに
  defs が異なるため各自が持つ)が `from sashizu_lib import _SVN` で同じ list を
  参照して増やし、ここの `_pat()` がそれを読む。
- `MUNE_JA` は棟名→和名の辞書で**邸ごとに中身が違う**。`mune_contacts_table` が
  ここのモジュール変数を読むので、各生成器は自分の辞書を定義した直後に
  `sashizu_lib.MUNE_JA = MUNE_JA` で差し替えてから表を組む(`_SVN` と同じ共有の作法)。
  未設定でも `.get(n, n)` で素の棟名に落ちるだけで壊れない。
"""
import html as _html
import math
import re

_SVN = [0]

MUNE_JA = {}


def _pat(): return "url(#pi%d)" % _SVN[0]


def R(x, y, w, h, fill="none", stroke="none", sw=1.0, dash=None, op=None):
    a = '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"' % (x, y, w, h, fill)
    if stroke != "none":
        a += ' stroke="%s" stroke-width="%.2f"' % (stroke, sw)
    if dash:
        a += ' stroke-dasharray="%s"' % dash
    if op is not None:
        a += ' opacity="%.2f"' % op
    return a + "/>"


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


def cf_color(dz):
    """dz = 設計の面 − 造成前の地形。正=盛土(暖色) / 負=切土(寒色)。"""
    a = abs(dz)
    if a < 0.3:
        return "var(--nomove)"
    i = 0 if a < 1.0 else 1 if a < 2.0 else 2 if a < 3.0 else 3
    return ("var(--fill%d)" if dz > 0 else "var(--cut%d)") % (i + 1)


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


def links_table(d):
    rows = []
    for l in d["links"]:
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td>(%g,%g)-(%g,%g)</td></tr>"
                    % (l["name"], l["kind"], l["u0"], l["v0"], l["u1"], l["v1"]))
    return ('<div class="tw"><table><thead><tr><th>廊下</th><th>種別</th><th>グリッド</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


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


def _edge_dir(P, e):
    a, b = P[e], P[(e + 1) % len(P)]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / L, (b[1] - a[1]) / L, L)


# ================================================================ 検査の正典
# 2026-08-26 裁定「適切な厳しさにした上で統一する」。以降、overlap_check / kenpei /
# design_y / md2html の正典はここ。生成器側には置かない。


# ---------------------------------------------------------------- markdown(考証 md → HTML)
# 確度の刻印。既定=岡部・松平・土井の形(【… 確度 S …】/【写真=A…】)。
# 山王は【S …】/【確度…】と先頭に置く方言なので CERT_LEADING を渡す。
CERT_DEFAULT = (r"【([^】]*確度 ?[SABPU?][^】]*)】", r"【(写真=A[^】]*)】")
CERT_LEADING = (r"【([SABPU?][^】]*)】", r"【(確度[^】]*)】")


def inline(s, cert=CERT_DEFAULT, bold_ml=True, strike=True, strip_spans=True):
    """行内の記法。既定は厳しい側(行跨ぎの ** / ~~取り消し~~ / span 除去すべて有効)。

    方言パラメタは**既存の考証 md の描画をバイト単位で保存する**ためだけに使う
    (bold_ml=False は `[^*]+`、strike=False は ~~ を素通し)。新しい邸は既定で書く。
    """
    if strip_spans:
        s = re.sub(r'</?span[^>]*>', "", s)
    s = _html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    if bold_ml:
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    else:
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    if strike:
        s = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", s)
    for p in cert:
        s = re.sub(p, r'<span class="cert">【\1】</span>', s)
    return s


def md2html(text, inline=inline, indent_tables=True, join_list=True):
    """考証 md の最小変換。構造は4方言の合併で、既定は厳しい側:

    - 表は**字下げされていても拾い**(2026-08-24 岡部考証)、区切り行が空で
      ないことを確かめる(空行を区切りと誤読して表を開かない)。
    - リスト項目は**素のまま連結してから inline() を一度だけ**通す
      (行をまたぐ `**…**` が壊れる — 2026-08-24 土井検図 低-1)。
      join_list=False は行ごとに inline する旧方言(岡部・松平・山王の md は
      `**` の対応が行単位で取れている前提で書かれており、連結すると対が動く)。
    - 1行も消費できない行は段落として出して**必ず前進する**
      (表の途中に別の行が挟まると無限ループ — 2026-08-23 土井)。
    """
    out, i, lines = [], 0, text.split("\n")
    tline = (lambda s: s.lstrip()) if indent_tables else (lambda s: s)
    while i < len(lines):
        ln = lines[i]
        if tline(ln).startswith("|") and i + 1 < len(lines) \
                and lines[i + 1].strip() and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and tline(lines[i]).startswith("|"):
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
            raw = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  ")):
                if lines[i].startswith("- "):
                    raw.append(lines[i][2:] if join_list else inline(lines[i][2:]))
                elif raw:
                    raw[-1] += " " + (lines[i].strip() if join_list else inline(lines[i].strip()))
                i += 1
            items = [inline(x) for x in raw] if join_list else raw
            out.append("<ul>" + "".join("<li>%s</li>" % t for t in items) + "</ul>"); continue
        if ln.strip() == "---":
            out.append('<hr class="rule">'); i += 1; continue
        if ln.strip() == "":
            i += 1; continue
        buf = []
        while i < len(lines) and lines[i].strip() \
                and not lines[i].lstrip().startswith(("#", "- ", "|")) and lines[i].strip() != "---":
            buf.append(lines[i].strip()); i += 1
        if not buf:
            out.append("<p>%s</p>" % inline(lines[i].strip())); i += 1
            continue
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


# ---------------------------------------------------------------- 回転矩形(OBB)
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


# ---------------------------------------------------------------- 設計地盤(段の高さ)
def t_contains(t, u, v):
    """(u,v) が段 t の中か。`poly`(岡部の等高線なり多角形)は crossing number、
    `yaw`(土井の回転段)は OBB、どちらも無ければ矩形で見る。"""
    p = t.get("poly")
    if p:
        n = len(p); c = False
        for i in range(n):
            (au, av), (bu, bv) = p[i], p[(i + 1) % n]
            if (av > v) != (bv > v) and u < (bu - au) * (v - av) / (bv - av) + au:
                c = not c
        return c
    return in_obb(t, u, v, 1e-9)


def design_y(d, u, v, in_parcel):
    """その (u,v) を覆う段の高さ。無ければ None(=造成しない斜面)。区画の外では常に None。
    `in_parcel` は生成器の区画判定(キャッシュを持つため各自が渡す)。"""
    if not in_parcel(d, u, v):
        return None
    best = None
    for t in d["terraces"]:
        if t_contains(t, u, v):
            best = t["y"] if best is None else max(best, t["y"])
    return best


# ---------------------------------------------------------------- 建蔽率
def kenpei(d, area, tsubo, svc_label, nagaya_label, ban_label):
    """建蔽率の算出(分母は敷地全体 — CLAUDE.md 規則5)。計算は最も厳しい土井版:

    - 渡廊下が棟へ一間乗り込む取り合いの分を**二重に数えない**(2026-08-25 検図12巡 低-6)。
      岡部・松平は乗り込み面積が 0 なので数値は動かないことを実証済(2026-08-26)。
    - `yaw` を持つ付属屋は外接矩形でなく **L×D** で数える(無ければ同値)。
    - 行ラベルは考証の一部なので呼び出し側から渡す(邸ごとに付属屋の顔ぶれが違う)。
    """
    K = d["const"]["ken"]
    gm = sum(abs(m["u1"] - m["u0"]) * abs(m["v1"] - m["v0"]) for m in d["munes"]) * K * K
    # ⚠ 渡廊下が棟へ一間乗り込む取り合いの分を**二重に数えない**
    #   (2026-08-25 検図12巡 低-6。影響は +0.02pt だが数え方は正しくする)。
    gl = 0.0
    for l in d["links"]:
        ov = 0.0
        for m in d["munes"] + d.get("service", []):
            if "yaw" in m:
                continue
            iu = min(l["u1"], m["u1"]) - max(l["u0"], m["u0"])
            iv = min(l["v1"], m["v1"]) - max(l["v0"], m["v0"])
            if iu > 1e-9 and iv > 1e-9:
                ov += iu * iv
        gl += max(0.0, abs(l["u1"] - l["u0"]) * abs(l["v1"] - l["v0"]) - ov)
    gl *= K * K
    gs = sum((s["L"] * s["D"]) if "yaw" in s else abs(s["u1"] - s["u0"]) * abs(s["v1"] - s["v0"])
             for s in d["service"]) * K * K
    nag = sum((r["s1"] - r["s0"]) * d["const"]["nagayaD"] for r in d["runs"] if r["kind"] == "Nagaya")
    bs = d["gate"]["plan"]["bansho"]
    ban = bs["count"] * bs.get("w", 0) * bs.get("d", 0)   # 長屋門は番所が躯体内=別計上なし
    yag = sum((y["ken"] * K) ** 2 for y in d.get("yagura", []))
    gp = d["gate"]["plan"]
    mon = gp["monW"] * gp.get("monD", 1.2) + 2 * gp.get("sode", 0) * 0.4 \
        + (d["onarimon"]["w"] * 1.5 if d.get("onarimon") else 0) \
        + sum(k["w"] * 1.2 for k in d["komon"])
    tot = gm + gl + gs + nag + ban + yag + mon
    return ('<div class="tw"><table><thead><tr><th></th><th>m²</th><th>坪</th></tr></thead><tbody>'
            "<tr><td>御殿の棟(入側とも)</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>%s</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>%s</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>%s</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td>%s</td><td>%.0f</td><td>%.0f</td></tr>"
            "<tr><td><b>計</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            "<tr><td><b>敷地(分母)</b></td><td><b>%.0f</b></td><td><b>%.0f</b></td></tr>"
            '<tr><td><b>建蔽率</b></td><td colspan="2"><b>%.1f%%</b></td></tr>'
            "</tbody></table></div>"
            % (gm, gm / tsubo, "渡廊下・御錠口", gl, gl / tsubo, svc_label, gs, gs / tsubo,
               nagaya_label, nag, nag / tsubo, ban_label, ban + yag + mon, (ban + yag + mon) / tsubo,
               tot, tot / tsubo, area, area / tsubo, 100.0 * tot / area)), 100.0 * tot / area


# ---------------------------------------------------------------- 矩形の重なり検査
def overlap_check(d):
    """矩形の総当たり重なり検査(棟・廊下・庭・付属屋)。接するは可、重なるは不可。
    ただし渡廊下が棟の外形(入側帯)に一間だけ乗り込むのは取り付きなので許す。

    最も厳しい土井版が基準(2026-08-26 裁定)。土井にしか無いデータ
    (terraceWalls の実体・atWall 参照・回転物)は、無い邸では素通りする。
    松平の「庭の中の池・中島は親の庭に完全包含なら可」も取り込む(包含のみの
    免除なので、入れ子の庭を持たない邸では挙動が変わらない)。
    """
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
    # ⚠ 石段の箱を総当たりに入れる(ramps と wells は入っていたのに kaidans だけ抜けていた。
    #   2026-08-25 検図13巡 中-6)。石段×白洲・石段×段は除外規約で落とす。
    for k9 in d["kaidans"]:
        w9 = next((x for x in d["terraceWalls"] if x["name"] == k9.get("atWall")), None)
        if w9 is None:
            continue
        hw9 = k9["w"] / 2 / ken2
        rn9 = k9["run"] / ken2
        if abs(w9["a"][0] - w9["b"][0]) < 1e-9:
            kb9 = {"name": k9["name"], "u0": w9["a"][0] - rn9, "u1": w9["a"][0],
                   "v0": k9.get("gapV", 0) - hw9, "v1": k9.get("gapV", 0) + hw9}
        else:
            kb9 = {"name": k9["name"], "u0": k9.get("gapU", 0) - hw9, "u1": k9.get("gapU", 0) + hw9,
                   "v0": w9["a"][1] - rn9, "v1": w9["a"][1]}
        for m9 in d["munes"] + d.get("service", []):
            if "yaw" in m9:
                continue
            iu = min(kb9["u1"], m9["u1"]) - max(kb9["u0"], m9["u0"])
            iv = min(kb9["v1"], m9["v1"]) - max(kb9["v0"], m9["v0"])
            if iu > 0.05 and iv > 0.05:
                bad.append("石段 %s と %s が %.1f×%.1f間 重なる" % (k9["name"], m9["name"], iu, iv))

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
                if k1 == "niwa" and k2 == "niwa":
                    # 庭の中の池・中島・築山は、親の庭に**完全に包含**されていれば可(松平)
                    if (a0 <= c0 and b0 <= d0 and c1 <= a1 and d1 <= b1) or \
                       (c0 <= a0 and d0 <= b0 and a1 <= c1 and b1 <= d1):
                        continue
                if {k1, k2} == {"niwa", "svc"}:
                    # 庭の中に立つ亭・祠は庭に**完全に包含**されていれば可(庭は地面)
                    (nk, na, n0, n1_, n2_, n3, _n), (sk, sa, s0, s1_, s2_, s3, _s) = \
                        (boxes[i], boxes[j]) if k1 == "niwa" else (boxes[j], boxes[i])
                    if n0 <= s0 and n1_ <= s1_ and s2_ <= n2_ and s3 <= n3:
                        continue
                bad.append("%s %s × %s %s (%.1f×%.1f間)" % (k1, n1, k2, n2, iu, iv))
    return bad
