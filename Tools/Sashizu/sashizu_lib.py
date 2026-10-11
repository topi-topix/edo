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

3. **造成モデルの正典 `graded_y`**(2026-08-26 ユーザー指示「岡部式と土井式の
   2パターンがあってよいのか？統一すべきでは？」→ 統一)。土井版
   (一定勾配の法面+着地判定+斜路・石段の先読み+盛土floor)を正典としてここへ移し、
   岡部もこれで生成する(旧岡部式=縁の盛土厚の逓減形 cbee45a は廃止)。
   岡部の切盛・断面・土量が動くのは覚悟の上の裁定(変化量は統一時の報告と git log)。
   岡部の「等高線なり多角形」の段は `poly` 分岐で受ける(土井のデータでは分岐が
   発火せず、出力バイト不変を実証して切り替えた)。

据え置き:
- 山王の `design_y` — 物理モデルは同族(一定勾配 1:batterFill/batterCut +
  着地判定 slope_lands + 土留め免除 on_wall)だが、世界座標の多角形の段・任意向きの
  土留め線分・DEM を法線方向に歩く着地判定と一体で、ここの回転間グリッド前提の
  インタフェース(辺名 u0..v1 / gapU・gapV / v=0 の外周 run / atWall の石段)には
  載らない。無理に載せると着地判定がかえって弱くなる(こちらは評価点の nat と
  比べるだけ)ため据え置く。

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


def s_sign(d):
    """走り s と グリッド u の**向きの関係**。u = sSign·(s − sg)/ken。

    ⛔ 邸によって逆。土井は `s = 47.0 + 1.818·u`(同じ向き=+1)だが、
    岡部は `s = 14.37 − 1.818·u`(逆向き=−1)。ここを +1 に決め打ちしていたため、
    岡部の門の辺の run が**表門をはさんだ反対側**の箱として検査されており、
    重なりを構造的に見つけられなかった(2026-08-31 検図)。

    ⭐ **宣言でなく算出する。** `grid.sSign` の明示があればそれを使うが、
    無ければ **u 軸の世界ベクトルと門の辺の向きの内積**から決める。
    宣言に頼ると次の邸が書き忘れて同じ穴に落ちる(2026-08-31 再検図)。"""
    g = d.get("grid", {})
    if "sSign" in g:
        return -1.0 if g["sSign"] < 0 else 1.0
    uv = g.get("uWorld")            # [ux, uz] — 生成器が入れていれば使う
    P9 = d.get("polygon")
    e9 = d.get("gate", {}).get("edge")
    if uv and P9 is not None and e9 is not None:
        a9, b9 = P9[e9], P9[(e9 + 1) % len(P9)]
        dot = uv[0] * (b9[0] - a9[0]) + uv[1] * (b9[1] - a9[1])
        if abs(dot) > 1e-9:
            return 1.0 if dot > 0 else -1.0
    return 1.0


def _pat(): return "url(#pi%d)" % _SVN[0]


def R(x, y, w, h, fill="none", stroke="none", sw=1.0, dash=None, op=None):
    # ⭐ **幅か高さが 0 の矩形は出さない**(2026-09-08 検図方 低4)。⛔ 退化した図形を紙へ
    #   置かない — ⚠ 何も描かれないのに要素だけが残り、**読み手には「在る」と見える**。
    #   ⚠ 呼び側は「描いたつもり」になるので、**黙って落とすのはここだけ**にする。
    if not (w > 0.05 and h > 0.05):
        return ""
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
        # ⚠ `asset` は**旧い形**(部材を1行の文字列で書いていた頃)のキー。
        #   新しい形は層ごとの `parts` を別配列(`slopePlanting`)に持つので、
        #   ここには無い。**無くても落とさない**(邸ごとに移行の時期が違う)。
        asset = b2.get("asset")
        rows.append("<tr><td>%s</td><td>法肩から %.0f〜%.0f%%</td><td class='note'>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (b2["name"], b2["from"] * 100, b2["to"] * 100, b2.get("veg", ""),
                       ("<code>%s</code>" % asset) if asset
                       else "<span class='note'>(部材は植栽の表へ)</span>"))
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
def _pt_in_ring(p, u, v):
    """点が閉じた点列 p の中か(crossing number)。"""
    n = len(p); c = False
    for i in range(n):
        (au, av), (bu, bv) = p[i], p[(i + 1) % n]
        if (av > v) != (bv > v) and u < (bu - au) * (v - av) / (bv - av) + au:
            c = not c
    return c


def t_holes(t):
    """段の**抜き**(造成しない区画)の輪郭の並び。無ければ空。

    ⭐ 2026-09-02 岡部: ユーザー裁定「主面の5区画を平坦化しない」で入れた。
    段の外周は等高線なりのままにし、**面を作らない区画を穴として抜く** —
    外周多角形を切り欠くと、内側だけの区画(長局の東の坪)が表せない。"""
    return [[(a, b) for a, b in hh["poly"]] for hh in (t.get("holes") or [])]


def t_keeps(t):
    """抜きの中でも**面を残す**区画(=棟が載る所)。ユーザー裁定の但し書き
    「棟が載る所だけ 24.80」を機械で当てる。**生成器が足跡から算出して書き戻す**
    (`GEN_FIELDS["terraces"]["keeps"]`)ので、人は json に書かない。"""
    return [[(a, b) for a, b in kp] for kp in (t.get("keeps") or [])]


def t_contains(t, u, v):
    """(u,v) が段 t の中か。`poly`(岡部の等高線なり多角形)は crossing number、
    `yaw`(土井の回転段)は OBB、どちらも無ければ矩形で見る。
    ⭐ `holes` を持つ段では、穴の中は「段の外」= 造成しない自然地盤とする。"""
    p = t.get("poly")
    if p:
        if not _pt_in_ring(p, u, v):
            return False
        if any(_pt_in_ring(hp, u, v) for hp in t_holes(t)):
            return any(_pt_in_ring(kp, u, v) for kp in t_keeps(t))
        return True
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


# ---------------------------------------------------------------- 造成後の地盤(正典・土井式)
# 2026-08-26 ユーザー指示で統一。土井の実装(検図13〜14巡を経た物理モデル)をそのまま移した。
# `in_parcel` は生成器の区画判定(キャッシュを持つため各自が渡す — design_y と同じ作法)。


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


def band_ramp_at(r, K, u, v):
    """折れ線 `pts` の坂で **`graded: true` を名乗るもの**(帯そのものが造成後の地盤)の、
    (芯線からの距離 m, 芯線の最寄りの点の踏面の高さ)。名乗らない坂(岡部の路盤)は None。

    踏面は `ys`(頂点ごと。null は道のりで内挿)か、無ければ `y0`→`y1` を道のりで内挿。
    端は帯の幅の半分で丸める(芯線の端点からの距離)。⚠ 2026-10-03 土井: 表の道を折れ線で振ったのに
    造成の式が `u0..v1` 式の坂しか読まず、振った線が切盛図にも断面にも出なかった。"""
    if not r.get("graded") or not isinstance(r.get("pts"), list) or len(r["pts"]) < 2:
        return None
    P = [tuple(q[:2]) for q in r["pts"]]
    S = [0.0]
    for a, b in zip(P, P[1:]):
        S.append(S[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    ys = list(r.get("ys") or [r["y0"]] + [None] * (len(P) - 2) + [r["y1"]])
    known = [(S[i], y) for i, y in enumerate(ys) if y is not None]
    best, bs = 1e18, 0.0
    for i, (a, b) in enumerate(zip(P, P[1:])):
        du_, dv_ = b[0] - a[0], b[1] - a[1]
        L2 = du_ * du_ + dv_ * dv_
        q = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((u - a[0]) * du_ + (v - a[1]) * dv_) / L2))
        dd = math.hypot(u - (a[0] + q * du_), v - (a[1] + q * dv_))
        if dd < best:
            best, bs = dd, S[i] + q * (S[i + 1] - S[i])
    y = known[0][1]
    for (s0, y0_), (s1, y1_) in zip(known, known[1:]):
        if s0 - 1e-9 <= bs <= s1 + 1e-9:
            y = y0_ + (y1_ - y0_) * ((bs - s0) / ((s1 - s0) or 1.0))
            break
    else:
        if bs > known[-1][0]:
            y = known[-1][1]
    return best * K, y


def ramp_y(d, u, v):
    """土の斜路の踏面。⚠ `stair_y` は `kaidans` しか見ておらず、**斜路がどこにも存在しなかった**
    (2026-08-25 検図11巡 中-1: 図が出す「厩の動線の最急 1:2.2」は斜路ではなく
    その頭の崖の数字だった。設計勾配は 1:7.4)。"""
    K = d["const"]["ken"]
    for r in d.get("ramps", []):
        if "u0" not in r:
            # 折れ線 `pts` 式の坂(岡部)は斜面の中の路盤 — 地盤は別勘定。`graded: true` を名乗る坂だけ帯が地盤
            br = band_ramp_at(r, d["const"]["ken"], u, v)
            if br is not None and br[0] <= r["w"] / 2.0 + 1e-9:
                return br[1]
            continue
        u0, u1 = min(r["u0"], r["u1"]), max(r["u0"], r["u1"])
        v0, v1 = min(r["v0"], r["v1"]), max(r["v0"], r["v1"])
        if not (u0 - 1e-9 <= u <= u1 + 1e-9 and v0 - 1e-9 <= v <= v1 + 1e-9):
            continue
        w = [x for x in d["terraceWalls"] if x["name"] == r.get("atWall")]
        # ⚠ **面の勾配(`planes[].fall.ramp`)はその面の中だけ。**外接矩形で引くと、矩形に掛かる**別の面**まで
        #   この勾配で埋まる(2026-10-03 岡部: 北東の郭 13.1 の西半が東の平場の勾配 16.4 になり、
        #   郭との境の土留めの下の側が立たなかった ── EDO-0502)。
        own = _fall_terraces(d, r["name"])
        if own is not None and any(t["name"] not in own and t_contains(t, u, v) for t in d["terraces"]):
            continue
        # ⚠ **土留めに付かない斜路もある。** 段の縁が地山と出会う所の摺り付けは、
        #   壁ではなく面と地山のあいだに架かる(2026-08-25 検図14巡 中-4)。
        #   その場合は高い端の高さを `top` で申告する。
        if not w:
            top = r.get("top")
            if top is None:
                continue
            u0_, u1_ = min(r["u0"], r["u1"]), max(r["u0"], r["u1"])
            v0_, v1_ = min(r["v0"], r["v1"]), max(r["v0"], r["v1"])
            # 面の勾配は向きが外接矩形の長手と限らない(2026-10-10 岡部の表の溜り: 矩形は u に長いが勾配は v)。
            #   `axis` を申告すればそれに従い、無ければ長手。
            ax = r.get("axis") or ("u" if (u1_ - u0_) > (v1_ - v0_) else "v")
            if ax == "u":
                t = (u - u0_) / ((u1_ - u0_) or 1.0)
            else:
                t = (v - v0_) / ((v1_ - v0_) or 1.0)
            if r.get("hiAt") == "lo":            # 高い端がどちらかを申告させる
                t = 1.0 - t
            return top - r["drop"] * (1.0 - max(0.0, min(1.0, t)))
        top = w[0]["coping"]
        # ⚠ **走行軸を先に決め、その軸上で「開口の芯に近い端」を上にする。**
        #   「壁に近い側が上」は**壁に平行な斜路では両端が等距離で退化**する
        #   (2026-08-25 検図12巡 中-1: 開口を壁の反対端へ移しても踏面が変わらなかった)。
        vert_w = abs(w[0]["a"][0] - w[0]["b"][0]) < 1e-9
        gk_w = "gapV" if vert_w else "gapU"
        # ⚠ `along` は `=="u"` と比較されていて **`true` は死値**だった(2026-08-25 検図12巡 低-2)。
        #   長短比で決める(斜路は長手に走る)。向きの規則はここ一箇所に置く。
        along_u = (u1 - u0) > (v1 - v0)
        if along_u:
            t = (u - u0) / ((u1 - u0) or 1.0)
            lo_a, hi_a = u0, u1
        else:
            t = (v - v0) / ((v1 - v0) or 1.0)
            lo_a, hi_a = v0, v1
        # 開口の芯(壁が持つ値。無ければ斜路自身の申告)を走行軸へ射影して比べる
        gc = w[0].get(gk_w, r.get(gk_w))
        if gc is not None and abs(hi_a - gc) > abs(lo_a - gc):
            t = 1.0 - t
        return top - r["drop"] * (1.0 - max(0.0, min(1.0, t)))
    return None


def _fall_terraces(d, rname):
    """斜路 rname が面の勾配(`planes[].fall.ramp`)なら、その面の段の名の集合。でなければ None。"""
    for pl in d.get("planes") or []:
        f = pl.get("fall")
        if isinstance(f, dict) and f.get("ramp") == rname:
            return set(pl.get("terraces") or [])
    return None


def stair_y(d, u, v, in_parcel):
    """石段の掘割(切通し)の中なら、その位置の**踏面の高さ**を返す。外なら None。

    石段は段と段のあいだの土手を**切通す**。掘割を地盤として扱わないと、
    「踏面が地山に埋まっている」という誤検出になり、切土も切盛図に出ない
    (2026-08-23 検図 M-2: K_Kita が最大 0.82m 埋まると出た)。
    """
    K = d["const"]["ken"]
    for k in d["kaidans"]:
        w = next((x for x in d["terraceWalls"] if x["name"] == k.get("atWall")), None)
        if w is None:
            continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
        run = k["run"] / K
        hw = k["w"] / 2.0 / K + 0.25                    # 片側に犬走りぶんの余裕
        if abs(w["a"][0] - w["b"][0]) < 1e-9:           # u=const の壁 → 段は u 方向へ下る
            if abs(v - k["gapV"]) > hw:
                continue
            lo = -1.0 if design_y(d, w["a"][0] - 0.5, v, in_parcel) is None or \
                 (design_y(d, w["a"][0] - 0.5, v, in_parcel) or 0) < w["coping"] else 1.0
            t = (u - w["a"][0]) / (lo * run)
        else:                                           # v=const の壁 → 段は v 方向へ下る
            if abs(u - k["gapU"]) > hw:
                continue
            lo = -1.0 if design_y(d, k["gapU"], w["a"][1] - 0.5, in_parcel) is None or \
                 (design_y(d, k["gapU"], w["a"][1] - 0.5, in_parcel) or 0) < w["coping"] else 1.0
            t = (v - w["a"][1]) / (lo * run)
        if -1e-9 <= t <= 1.0 + 1e-9:
            return w["coping"] - k["drop"] * t
    return None


def t_edge_dist(t, u, v):
    """段の縁までの距離[間]。**穴の縁も段の縁**(穴の中の点は穴の縁から法面が下りる)。"""
    # ⚠ **穴の中の点から見て、穴の縁より近くに段は無い。**外輪の線のうち穴の中を通る部分は
    #   穴で抜かれていて段の縁ではない。従前は外輪までの距離をそのまま採ったので、穴の中を通る
    #   外輪の線から盛土の法面が生えていた(2026-10-03 岡部 西端の帯: 勝手道の角に +0.63m の膨らみ)。
    #   ⭕ 穴の中では「穴の縁までの距離」を下限に取る(外輪の外なら外輪までとの大きい方)。
    hs = [hp for hp in t_holes(t) if _pt_in_ring(hp, u, v)]
    if hs:
        dh = min(poly_edge_dist(hp, u, v) for hp in hs)
        if not _pt_in_ring(t["poly"], u, v):
            dh = max(dh, poly_edge_dist(t["poly"], u, v))
        for kp in t_keeps(t):
            dh = min(dh, poly_edge_dist(kp, u, v))
        return dh
    best = poly_edge_dist(t["poly"], u, v)
    # ⚠ **抜きの縁を段の縁と見るのは、外輪の中にいるときだけ。**
    #   抜きの矩形は外輪より外へはみ出して書いてよい(区画で切られる)ので、
    #   外輪の外の点にまで当てると、段から遠い斜面が「抜きの縁のすぐ外」と読まれ、
    #   そこへ法面の盛土が生える(2026-09-02: 辺1 の練塀 S_Hei2b が内側の土に 2.74m 埋まった)。
    if _pt_in_ring(t["poly"], u, v):
        for hp in t_holes(t) + t_keeps(t):
            best = min(best, poly_edge_dist(hp, u, v))
    return best


def poly_edge_dist(p, u, v):
    """多角形の縁までの距離[間](外側の点用)。岡部の「等高線なり多角形」の段の縁。"""
    n = len(p)
    best = 1e18
    for i in range(n):
        (au, av), (bu, bv) = p[i], p[(i + 1) % n]
        du_, dv_ = bu - au, bv - av
        L2 = du_ * du_ + dv_ * dv_
        q = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((u - au) * du_ + (v - av) * dv_) / L2))
        best = min(best, math.hypot(u - (au + q * du_), v - (av + q * dv_)))
    return best


def wall_caps(d, t, u, v, y2):
    """**土留めが法面を打ち切るか。**壁の天端より下へ盛ろうとしたら、そこから先は壁が受ける。

    ⭐ 天端が一定なので「天端より下」= 「壁より外」になる(壁は天端の等高線に立つ)。
      多角形の線を持ち回らずに済む。⛔ `span` の中でだけ効かせる — 段のほかの縁は法面のまま。
    ⚠ 2026-09-02 岡部: 従前は poly の段に土留めの免除が掛からず
      (「壁付き多角形の段が要る邸が出たら拡張する」と書いてあった)、西の法尻で
      法面が着地せず 44m にわたり最大 3.9m の垂直段差が残っていた。"""
    for w in d.get("terraceWalls", []):
        if w.get("terrace") and w["terrace"] != t["name"]:
            continue
        sp = w.get("span")
        if not sp:
            continue
        q = u if sp.get("axis") == "u" else v
        if not (min(sp["from"], sp["to"]) <= q <= max(sp["from"], sp["to"])):
            continue
        if sp.get("vFrom") is not None and v < sp["vFrom"]:
            continue
        if y2 < w["coping"]:
            return True
    return False


def michi_narashi_spec(d):
    """指図 `grading.michiNarashi`(区画線の外の道の線際の帯の均し・EDO-0502 施主 2026-10-11『均す』)を数へ読む。
    欄が無ければ None。`band`(帯の幅 m)・`cross`(線上の高さで平らに保つ幅 m と、その先の擦り付けの勾配 1/n)は
    文の数を読む ── 読めなければ ⛔ 例外(推し量って幅を作らない・規則19)。"""
    g = (d.get("grading") or {}).get("michiNarashi")
    if not g:
        return None
    mb = re.search(r"([0-9.]+)\s*m", str(g.get("band", "")))
    mc = re.search(r"([0-9.]+)\s*m", str(g.get("cross", "")))
    ms = re.search(r"1\s*/\s*([0-9.]+)", str(g.get("cross", "")))
    if not (mb and mc and ms) or not g.get("lineProfile") or g.get("edge") is None:
        raise ValueError("grading.michiNarashi の band / cross / lineProfile / edge が読めない")
    prof = sorted((float(a), float(b)) for a, b in g["lineProfile"])
    return {"edge": int(g["edge"]), "band": float(mb.group(1)), "flat": float(mc.group(1)),
            "slope": 1.0 / float(ms.group(1)), "prof": prof}


def front_band_spec(d):
    """指図 `grading.omoteNagayaDai.frontBand`(道に面する辺の線際の帯・EDO-0502 第108巡 普請方の設計 2026-10-11)を数へ読む。
    欄が無ければ None。文の数(帯の幅・線上の地盤への足し・辺と s の範囲と線上の地盤の出所・門の口)を読む ──
    読めなければ ⛔ 例外(推し量って帯を作らない・規則19)。"""
    g = ((d.get("grading") or {}).get("omoteNagayaDai") or {}).get("frontBand")
    if not g:
        return None
    what, ref, exc = str(g.get("what", "")), str(g.get("lineRef", "")), str(g.get("except", ""))
    mb = re.search(r"内へ\s*([0-9.]+)\s*m", what)
    mu = re.search(r"線上の地盤\s*\+\s*([0-9.]+)", what)
    ents = []
    for m in re.finditer(r"辺\s*(\d+)\s*(?:s\s*([0-9.]+)\s*〜\s*([0-9.]+))?\s*は\s*(grading\.michiNarashi\.lineProfile|線上の\s*base_dem)", ref):
        ents.append({"edge": int(m.group(1)), "s0": float(m.group(2)) if m.group(2) else None,
                     "s1": float(m.group(3)) if m.group(3) else None,
                     "src": "michi" if "michiNarashi" in m.group(4) else "dem"})
    gates = [(int(m.group(1)), float(m.group(2)), float(m.group(3)))
             for m in re.finditer(r"辺\s*(\d+)\s*s\s*([0-9.]+)\s*〜\s*([0-9.]+)", exc)]
    if not (mb and mu and ents):
        raise ValueError("grading.omoteNagayaDai.frontBand の what(内へ m・線上の地盤 +)/ lineRef が読めない")
    mi = michi_narashi_spec(d) if any(e["src"] == "michi" for e in ents) else None
    if any(e["src"] == "michi" for e in ents) and mi is None:
        raise ValueError("frontBand が grading.michiNarashi.lineProfile を名指すが欄が無い")
    return {"band": float(mb.group(1)), "up": float(mu.group(1)), "ents": ents, "gates": gates, "michi": mi}


def front_band_y(sp, poly, x, z, dem_at):
    """区画の内の線際の帯の地盤(世界 x, z)= 線上の地盤 + up。帯の外・門の口は None。角で二辺の帯が重なれば低い方。
    `dem_at(x, z)` = 造成前の地盤(base_dem)。s は辺の始まりの頂点からの道のり。"""
    if sp is None:
        return None
    n = len(poly)
    ar = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    best = None
    for e in sp["ents"]:
        a, b = poly[e["edge"] % n], poly[(e["edge"] + 1) % n]
        Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        tx, tz = (b[0] - a[0]) / Ln, (b[1] - a[1]) / Ln
        s = (x - a[0]) * tx + (z - a[1]) * tz
        s0 = 0.0 if e["s0"] is None else e["s0"]
        s1 = Ln if e["s1"] is None else min(Ln, e["s1"])
        if s < s0 - 1e-6 or s > s1 + 1e-6:
            continue
        ix, iz = (-tz, tx) if ar > 0 else (tz, -tx)            # 内向き
        dd = (x - a[0]) * ix + (z - a[1]) * iz
        if dd < 0.0 or dd > sp["band"]:
            continue
        if any(ge == e["edge"] and g0 <= s <= g1 for ge, g0, g1 in sp["gates"]):
            continue
        if e["src"] == "michi":
            pr = sp["michi"]["prof"]
            if s <= pr[0][0]:
                y0 = pr[0][1]
            elif s >= pr[-1][0]:
                y0 = pr[-1][1]
            else:
                y0 = pr[-1][1]
                for (q1, y1), (q2, y2) in zip(pr, pr[1:]):
                    if q1 <= s <= q2:
                        y0 = y1 + (y2 - y1) * (s - q1) / ((q2 - q1) or 1.0)
                        break
        else:
            y0 = dem_at(a[0] + tx * s, a[1] + tz * s)
            if y0 is None:
                continue
        y = y0 + sp["up"]
        best = y if best is None else min(best, y)
    return best


def michi_narashi_y(sp, poly, x, z, inside):
    """区画線の外の道の線際の帯の**均した面**(世界 x, z)。帯の外・区画の中・辺の両端の外は None。
    面 = 線上の高さ lineProfile(s)(線から flat m まで)、その先は slope の勾配で上る(今の地盤との min を取る側が擦り付けになる)。
    ⛔ 盛らない ── 呼ぶ側が min(今の地盤, 面) を取る【硬】。s は辺の始まりの頂点 poly[edge] からの道のり。"""
    if sp is None or inside:
        return None
    n = len(poly)
    a, b = poly[sp["edge"] % n], poly[(sp["edge"] + 1) % n]
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    s = (x - a[0]) * tx + (z - a[1]) * tz
    if s < 0.0 or s > L:
        return None
    # 外向きの法線(区画の巡りで決める ── 辺の延長の上の、隣の辺の外の点を拾わない)
    ar = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    ox, oz = (tz, -tx) if ar > 0 else (-tz, tx)
    dd = (x - a[0]) * ox + (z - a[1]) * oz
    if dd < 0.0 or dd > sp["band"]:
        return None
    pr = sp["prof"]
    if s <= pr[0][0]:
        y0 = pr[0][1]
    elif s >= pr[-1][0]:
        y0 = pr[-1][1]
    else:
        y0 = pr[-1][1]
        for (s1, y1), (s2, y2) in zip(pr, pr[1:]):
            if s1 <= s <= s2:
                y0 = y1 + (y2 - y1) * (s - s1) / ((s2 - s1) or 1.0)
                break
    return y0 + max(0.0, dd - sp["flat"]) * sp["slope"]


def graded_y(d, u, v, nat, in_parcel, walled=None):
    """**造成後の地盤**。段の中は段の高さ。段の外は法面(盛土 1:batterFill / 切土 1:batterCut)で
    現地形へ摺り付ける — 段の縁に垂直の段差を残さないため(2026-08-23 ユーザー指摘)。
    土留めが載っている辺からは法面を出さない(そこは壁が垂直に受ける)。
    どこも触らない点では nat と同じ値を返すので、差がゼロ=無造成。

    `poly` を持つ段(岡部の等高線なり多角形)は、中を t_contains・縁までの距離を
    poly_edge_dist で見る。辺名を持たないので土留め・外周 run の免除は掛からない
    (岡部は terraceWalls が空なので実害なし。壁付き多角形の段が要る邸が出たら拡張する)。"""
    if not in_parcel(d, u, v):
        return nat                                     # 区画の外は現地形のまま(造成しない)
    # ⭐ 関係で解いた土留め(`_twLines`・EDO-0502)── 欄の無い邸では何もしない
    tw = d.get("_twLines")
    if tw:
        y = tw_effect_pre(d, tw, u, v)                 # 壁の肩の摺り付け(上の面の中)
        if y is not None:
            return y
    # ⚠ **斜路と石段は段より先に見る。** 段の中を通るので `design_y` を先に引くと隠れ、
    #   切盛図にも土量にも断面にも出なかった(2026-08-25 検図12巡 中-2:
    #   斜路 26m³・石段 40m³ が隠れていた)。動線の `_ry` と同じ順にする。
    rp = ramp_y(d, u, v)                               # 土の斜路の踏面
    if rp is not None:
        return rp
    st = stair_y(d, u, v, in_parcel)                   # 石段の掘割は踏面が地盤
    if st is not None:
        return st
    ins = design_y(d, u, v, in_parcel)
    if ins is not None:
        if d.get("gardens") and niwa_setup(d):         # 庭の造成(`gardens[].hosoku.zosei` を持つ庭だけ)
            nz = niwa_y(d, u, v, ins, nat)
            if nz is not None:
                return nz
        return ins
    if nat is None:
        return None
    K = d["const"]["ken"]
    bf = d["const"].get("batterFill", 1.5)
    bc = d["const"].get("batterCut", 1.0)
    cap = d["const"].get("featherCap", 12.0)
    g = nat
    floor = -1e9
    for t in d["terraces"]:
        p9 = t.get("poly")
        if p9:
            if t_contains(t, u, v):
                continue                               # 多角形の内側は段そのもの
            dm = t_edge_dist(t, u, v) * K
            if wall_caps(d, t, u, v, t["y"] - dm / bf):
                continue                               # 土留めが受ける — これ以上先へ盛らない
        else:
            if in_obb(t, u, v):
                continue                               # 回転物の内側は段そのもの
            we = walled[t["name"]] if walled else walled_edges(d, t)
            # ⚠ **回転する段は、法面の距離も回転した軸で測る。**
            #   外接矩形 `u0..v1` で測ると、OBB の外・AABB の内で du=dv=0 になり
            #   **外接矩形いっぱいが段の高さで平らに造成される**
            #   (2026-08-25 検図12巡 高-2: 6段で 114セル・96坪・90m³。平面は回転矩形、
            #   切盛図は軸平行の矩形で、同じ段が二つの形で描かれていた)。
            if "yaw" in t:
                r_ = math.radians(t["yaw"])
                lu_, lv_ = math.sin(r_), math.cos(r_)
                du_, dv_ = math.cos(r_), -math.sin(r_)
                a_ = (u - t["uc"]) * lu_ + (v - t["vc"]) * lv_
                b_ = (u - t["uc"]) * du_ + (v - t["vc"]) * dv_
                du = max(0.0, abs(a_) - t["L"] / 2.0)
                dv = max(0.0, abs(b_) - t["D"] / 2.0)
                eu = ("u1" if a_ > 0 else "u0") if du > 1e-9 else None
                ev = ("v1" if b_ > 0 else "v0") if dv > 1e-9 else None
            elif u < t["u0"]:
                du, eu = t["u0"] - u, "u0"
            elif u > t["u1"]:
                du, eu = u - t["u1"], "u1"
            else:
                du, eu = 0.0, None
            if "yaw" not in t:
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
                continue                               # 壁が受ける区間 — 法面を出さない
            if ev == "v0" and abs(t["v0"]) < 1e-9 and any(a9 <= qu <= b9 for a9, b9 in run_edges(d)):
                continue                               # 外周 run の基壇石垣が受ける(法面を出さない)
            dm = math.hypot(du, dv) * K
        if dm > cap:
            continue
        y2 = t["y"] - dm / bf
        if tw:
            y2 = tw_fill_rule(tw, t["name"], u, v, cap / K, y2)
            if y2 is None:
                continue                               # 土留めより下の側 ── 壁が受ける(盛の法を越させない)
        if t["y"] - cap / bf > nat:
            continue                                   # cap の内で現地形に着地しない = 法面を出さない
        g = max(g, y2)                                 # 盛土の裾がこぼれる
        floor = max(floor, y2)                         # 盛土が要求する下限
    for t in d["terraces"]:
        p9 = t.get("poly")
        if p9:
            if t_contains(t, u, v):
                continue                               # 多角形の内側は段そのもの
            dm = t_edge_dist(t, u, v) * K
        else:
            if in_obb(t, u, v):
                continue                               # 回転物の内側は段そのもの
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
        if tw:
            ok, alt = tw_cut_rule(tw, t["name"], u, v, cap / K, K)
            if not ok:
                if alt is not None:
                    g = min(g, alt)                    # 土留めの天端から上の土羽
                continue                               # 土留めが切りを受ける
        if dm > cap:
            continue
        if t["y"] + cap / bc < nat:
            continue                                   # cap の内で現地形に着かない
        g = min(g, t["y"] + dm / bc)                   # 切土の法が日の目を見る
    # 帯が地盤の坂(`graded: true`)の両脇も法面で摺り付ける(盛 1:batterFill / 切 1:batterCut)。
    for r in d.get("ramps", []):
        br = band_ramp_at(r, K, u, v) if "u0" not in r else None
        if br is None:
            continue
        dm = br[0] - r["w"] / 2.0
        if dm <= 0 or dm > cap:
            continue
        yf = br[1] - dm / bf
        if yf > nat:
            g = max(g, yf)
            floor = max(floor, yf)
        yc = br[1] + dm / bc
        if yc < nat:
            g = min(g, yc)
    # ⚠ 切土の法面が**盛土の要求する下限を割らない**ようにする。
    #   低い段の切土が高い段の縁の下を掘り、縁に受けの無い段差を作っていた
    #   (2026-08-24 検図: 書院の郭の南縁で 0.89m)。
    return max(g, floor)


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
    # ⛔ **躯体内の番所は別計上しない**(長屋門の桁行×梁間に既に含まれる)。
    #    ⚠ 2026-08-31 五巡目: コメントは「躯体内=別計上なし」と書きながら**足していた**。
    #    岡部で 6.48 m²(建蔽率 0.02pt)の二重計上。`bansho.kind` が「躯体内」を含むかで分ける。
    ban = (0.0 if "躯体内" in str(bs.get("kind", ""))
           else bs["count"] * bs.get("w", 0) * bs.get("d", 0))
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
def _g_poly(o):
    """物が `poly`(実形)を持つなら折れ線を返す。矩形しか持たない物は None。"""
    if isinstance(o, dict) and o.get("poly"):
        return [tuple(p) for p in o["poly"]]
    return None


def _contains(outer, inner, step=0.25):
    """`inner` が `outer` に**完全に包含**されているか。

    ⭐ 2026-09-03(松江・検図【高2】)に**実形**へ替えた。⛔ 従前は外接矩形の包含だけを見ており、
      **台形の庭から矩形の露地が 3.53 m² はみ出していても 0 件**だった(38 m² でも通った)。
    ⭕ `poly` を持つ物は折れ線で判定する — `inner` の縁と中を刻んで、すべて `outer` の中か。
    ⚠ どちらも `poly` を持たないときは従来どおり矩形の包含(挙動を変えない)。"""
    (_k1, _n1, a0, b0, a1, b1, o1) = outer
    (_k2, _n2, c0, d0, c1, d1, o2) = inner
    po, pi = _g_poly(o1), _g_poly(o2)
    if po is None and pi is None:
        return a0 <= c0 and b0 <= d0 and c1 <= a1 and d1 <= b1
    pts = pi if pi is not None else [(c0, d0), (c1, d0), (c1, d1), (c0, d1)]
    qs = []
    for i in range(len(pts)):                       # 縁を刻む
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for k in range(n + 1):
            t = k / float(n)
            qs.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    for q in qs:
        if po is not None:
            # ⚠ 辺の上に載る点は「中」に数える(接するは可)
            if not (_pip(q, po) or _poly_edge_dist(q, po) <= 1e-6):
                return False
        elif not (a0 - 1e-6 <= q[0] <= a1 + 1e-6 and b0 - 1e-6 <= q[1] <= b1 + 1e-6):
            return False
    return True


def _poly_edge_dist(p, poly):
    """点から多角形の**辺**までの最短距離。辺の上に載る点(=0)を内包から外すために使う。"""
    best = None
    for i in range(len(poly)):
        (ax, az), (bx, bz) = poly[i], poly[(i + 1) % len(poly)]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 <= 1e-18 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / L2))
        dd = math.hypot(p[0] - (ax + dx * t), p[1] - (az + dz * t))
        best = dd if best is None else min(best, dd)
    return best if best is not None else 0.0


def _pip(p, poly):
    x, y = p
    c = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            c = not c
    return c


def _poly_box_overlap(o1, o2, a0, b0, a1, b1, c0, d0, c1, d1, step=0.25):
    """実形どうし(片方が矩形でも可)が本当に重なるか。重なりの帯を細かく走査する。"""
    p1, p2 = _g_poly(o1), _g_poly(o2)
    u0, u1_ = max(a0, c0), min(a1, c1)
    v0, v1_ = max(b0, d0), min(b1, d1)
    u = u0 + step / 2
    while u < u1_:
        v = v0 + step / 2
        while v < v1_:
            if (p1 is None or _pip((u, v), p1)) and (p2 is None or _pip((u, v), p2)):
                return True
            v += step
        u += step
    return False


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
        # ⭐ 2026-09-02 岡部: 庭が `rects`(**割り当ての矩形から棟と上位の庭を引いた残り**)を
        #   持つときは、そちらを箱に入れる。庭は「建屋と囲いの間に残る面」なので、
        #   割り当ての矩形そのものは棟や隣の庭と重なってよい(重なりは順で解く)。
        #   ⛔ 免除ではない — 残りの矩形どうしはこの総当たりで従来どおり検査される。
        # ⚠ 第7欄は「回転物 or 実形」。`poly` を持つ庭はここで実体を渡す(松平 2026-09-01)
        rr = n.get("rects")
        if rr:
            for i9, q9 in enumerate(rr):
                boxes.append(("niwa", "%s[%d]" % (n["name"], i9), q9[0], q9[1], q9[2], q9[3], None))
        else:
            boxes.append(("niwa", n["name"], n["u0"], n["v0"], n["u1"], n["v1"],
                          n if n.get("poly") else None))
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
        ua, ub = sorted((s_sign(d) * (r["s0"] - sg) / ken2, s_sign(d) * (r["s1"] - sg) / ken2))
        boxes.append(("run", r["name"], ua, 0.0, ub, depth / ken2, None))
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
    # ⭐ **石段の箱を総当たりへ入れる。**⛔ 従前は「石段×棟」「石段×階段廊下」の2つの専用ループ
    #   しか無く、**石段×外周 run(長屋門)が構造的に検査されていなかった**
    #   (2026-09-02 検図 K065: 門前の石段が長屋門へ食い込んでも 0件)。
    for k7 in d.get("kaidans", []):
        hw7 = k7["w"] / 2 / ken2
        if k7.get("gapU") is not None:
            a7, b7 = sorted((k7.get("v0", 0.0), k7.get("v1", 0.0)))
            boxes.append(("kaidan", k7["name"], k7["gapU"] - hw7, a7, k7["gapU"] + hw7, b7, None))
        elif k7.get("gapV") is not None:
            a7, b7 = sorted((k7.get("u0", 0.0), k7.get("u1", 0.0)))
            boxes.append(("kaidan", k7["name"], a7, k7["gapV"] - hw7, b7, k7["gapV"] + hw7, None))
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
        hw9 = k9["w"] / 2 / ken2
        # ⚠ `run` を持たない石段(松江松平の庭の段・2026-09-04 merge で判明)は土留めに付く箱を作れない。
        #   ⛔ KeyError で生成ごと止めない — 土留め無しの箱(gapU/gapV)はそのまま作れる
        rn9 = (k9["run"] / ken2) if k9.get("run") is not None else None
        if w9 is None:
            # ⭐ **土留めに付かない石段(岡部は郭内の土留めが0本)でも箱を作る。**
            #   ⛔ 従前は `atWall` が null だと素通りし、**当邸の石段は1本も総当たりに
            #     入っていなかった**(2026-09-02 検図 K065。K_Mon が長屋門へ 0.793m² 食い込んだ
            #     穴が塞がっていなかった)。降りる向きと区間は json が持っているので、それで作る。
            if k9.get("gapU") is not None:
                a9, b9 = sorted((k9.get("v0", 0.0), k9.get("v1", 0.0)))
                kb9 = {"name": k9["name"], "u0": k9["gapU"] - hw9, "u1": k9["gapU"] + hw9,
                       "v0": a9, "v1": b9}
            elif k9.get("gapV") is not None:
                a9, b9 = sorted((k9.get("u0", 0.0), k9.get("u1", 0.0)))
                kb9 = {"name": k9["name"], "u0": a9, "u1": b9,
                       "v0": k9["gapV"] - hw9, "v1": k9["gapV"] + hw9}
            else:
                continue
        elif rn9 is None:
            continue
        elif abs(w9["a"][0] - w9["b"][0]) < 1e-9:
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
        r0, r1 = sorted((s_sign(d) * (r["s0"] - sg) / ken2, s_sign(d) * (r["s1"] - sg) / ken2))
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
                # ⭐ **実形を持つ物は外接矩形で判定しない**(2026-09-03 松江・庭方【高5】)。
                #   ⛔ 従前は `_o1`(poly)を受け取っていながら bbox しか見ておらず、
                #     台形の庭が**外接矩形の隅**で竹垣に当たって偽陽性を出した
                #     (実測は 0.76〜0.78 間 離れている)。⭕ poly があれば実形で判定する。
                p9 = _g_poly(_o1)
                hit = 0.0
                for i9 in range(41):
                    t9 = i9 / 40.0
                    pu = a[0] + (b[0] - a[0]) * t9
                    pv = a[1] + (b[1] - a[1]) * t9
                    if p9 is not None:
                        # ⚠ **開区間で判定する**(2026-09-03 松江・庭方【高5】)。
                        #   矩形の側は `1e-9` の余白つきの厳密不等号なので、poly の側も
                        #   **辺の上に載る点は「貫通」に数えない** — さもないと
                        #   「垣と庭が同じ線を共有する」正しい設計が貫通に化ける。
                        if _pip((pu, pv), p9) and _poly_edge_dist((pu, pv), p9) > 1e-6:
                            hit += 1
                        continue
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
            if iu > 1e-9 and iv > 1e-9 and (o1 is not None or o2 is not None) \
                    and not (_g_poly(o1) or _g_poly(o2)):
                q1 = o1 if o1 is not None else {"u0": a0, "v0": b0, "u1": a1, "v1": b1}
                q2 = o2 if o2 is not None else {"u0": c0, "v0": d0, "u1": c1, "v1": d1}
                if not obb_overlap(q1, q2):
                    continue
            if iu > 1e-9 and iv > 1e-9 and (_g_poly(o1) or _g_poly(o2)):
                # ⚠ **`poly` を持つ庭は矩形ではない**(`u0..v1` はその外接箱)。
                #   外接箱どうしで見ると、庭が避けて通した棟や隣の庭と「重なる」と出る
                #   (2026-09-01 松平・枯池の庭と書院の中庭)。実形で見直す。
                if not _poly_box_overlap(o1, o2, a0, b0, a1, b1, c0, d0, c1, d1):
                    continue
            if iu > 1e-9 and iv > 1e-9:
                if {k1, k2} == {"niwa", "link"}:
                    # 中庭を渡廊下が横切るのは正しい姿(庭は地面)。**完全に包含**なら可。
                    # ⛔ はみ出す渡廊下は下の「一間だけ乗り込む」規約で見る
                    (n0_, n1_, n2_, n3_) = (a0, b0, a1, b1) if k1 == "niwa" else (c0, d0, c1, d1)
                    (l0_, l1_, l2_, l3_) = (c0, d0, c1, d1) if k1 == "niwa" else (a0, b0, a1, b1)
                    if n0_ <= l0_ and n1_ <= l1_ and l2_ <= n2_ and l3_ <= n3_:
                        continue
                if {"link"} & {k1, k2}:
                    # 取り付き: 渡廊下は**長手方向に一間だけ**棟の外形(入側帯)へ乗り込める。
                    # 幅方向の一間重なりを盾に長手で何間も乗り込むのは不可(検図指摘)。
                    lk = boxes[i] if k1 == "link" else boxes[j]
                    llong = "u" if (lk[4] - lk[2]) >= (lk[5] - lk[3]) else "v"
                    along = iu if llong == "u" else iv
                    if along <= 1.0 + 1e-9:
                        continue
                    # ⭐ **庭に完全に包含された渡廊下は可**(庭は地面)。2026-09-04 松江・検図 D6:
                    #   ⛔ ここも外接矩形の包含で見ていたので、台形の庭で破れる。実形で見る。
                    nb2, lb2 = (boxes[i], boxes[j]) if k1 == "niwa" else (boxes[j], boxes[i])
                    if _contains(nb2, lb2):
                        continue
                if k1 == "niwa" and k2 == "niwa":
                    # 庭の中の池・中島・築山は、親の庭に**完全に包含**されていれば可(松平)
                    if _contains(boxes[i], boxes[j]) or _contains(boxes[j], boxes[i]):
                        continue
                if {k1, k2} == {"kaidan", "niwa"} or {k1, k2} == {"kaidan"}:
                    continue          # 石段×白洲(庭)は通り道なので可・石段どうしは別の段
                if {k1, k2} == {"kaidan", "ramp"}:
                    continue          # 石段と坂は別の動線
                if {k1, k2} == {"niwa", "svc"} or {k1, k2} == {"niwa", "ido"}:
                    # 庭の中に立つ亭・祠・井戸は庭に**完全に包含**されていれば可(庭は地面)。
                    # ido の免除は EDO-0023(2026-08-26): 統一時に土井・岡部に niwa×ido の
                    # 事例が無く落としていた — 庭の井戸は松平で5件、svc と同型の免除で受ける
                    nb, sb = (boxes[i], boxes[j]) if k1 == "niwa" else (boxes[j], boxes[i])
                    if _contains(nb, sb):
                        continue
                bad.append("%s %s × %s %s (%.1f×%.1f間)" % (k1, n1, k2, n2, iu, iv))
    return bad


# ===========================================================================
# 感度試験(破壊試験)の回し方 — 既定では回さず、前回の記録を読む(2026-09-20)
# ===========================================================================
#
# 【なぜ】実測(2026-09-20): 松江松平の生成器は 1 回 120〜178 分(中央値 86 分)かかり、
#   9/15 以降の実測 41 回ぶんの待ちがそのまま役の実働になっていた。内訳を測ると
#   `_garden_checks` 1 回が 61 秒で、それを「わざと壊して鳴るか」で 81 通り回すので
#   **破壊試験だけで約 80 分**。設計値を 1 つ直すたびにこれを丸ごと回していた。
#
# 【どう変えたか】破壊試験は**既定では回さず、前回回したときの結果を記録から読む**。
#   `--deep`(または `SASHIZU_DEEP=1`)を付けたときだけ実際に壊して回し、
#   `docs/Sashizu/<邸>_sensitivity.json` へ書く。
#
# ⛔ **「回さない」は「合格」ではない**(CLAUDE.md 規則19)。だから:
#   - 記録が無い項目は ⛔ で「**回っていない**(合格ではない)」と刷る
#   - 記録はそのときの**生成器と設計値の指紋**を持ち、どちらかが変わっていれば
#     ⚠「記録が古い」と刷る。緑にはならない
#   - 既定の run でも**前回の結果そのもの**(鳴らなかった probe を含む)を刷るので、
#     報告経路は切れない
#
# 【使い方】各生成器の呼び出し側を次の形にするだけ:
#     base, probes = sens("matsudaira_dewa", "planting",
#                         lambda: planting_sensitivity(d, dem), default=(0, []))

import hashlib as _hashlib
import json as _json
import os as _os
import sys as _sys
import time as _time

_SENS_DEEP = None
_SENS_MEM = {}
_SENS_REC = {}
_SENS_SEEN = []


def sens_root():
    """`docs/Sashizu/` の絶対パス(このファイルは `Tools/Sashizu/` に在る)。"""
    here = _os.path.dirname(_os.path.abspath(__file__))
    return _os.path.join(_os.path.dirname(_os.path.dirname(here)), "docs", "Sashizu")


def deep_enabled():
    """破壊試験を実際に回すか。`--deep` か `SASHIZU_DEEP=1`。"""
    global _SENS_DEEP
    if _SENS_DEEP is None:
        _SENS_DEEP = ("--deep" in _sys.argv) or (_os.environ.get("SASHIZU_DEEP") == "1")
    return _SENS_DEEP


def _sens_file(estate):
    return _os.path.join(sens_root(), estate + "_sensitivity.json")


def _sha(path, *more):
    """ファイルの指紋。`more` があれば、その中身も続けて混ぜる(生成器が別ファイルの式を呼ぶとき)。"""
    try:
        h = _hashlib.sha256()
        for p in (path,) + more:
            with open(p, "rb") as f:
                h.update(f.read())
        return h.hexdigest()[:16]
    except Exception:
        return "?"


def sens_fingerprint(estate):
    """記録の鮮度を決める指紋 — 生成器そのものと設計値の json。"""
    here = _os.path.dirname(_os.path.abspath(__file__))
    gen = _os.path.join(here, "build_%s_sashizu.py" % estate)
    if not _os.path.exists(gen):                       # 共通の生成器(2026-09-20 以降はこちらが既定)
        gen = _os.path.join(here, "build_sashizu.py")
    soil = _os.path.join(here, "sashizu_soil.py")       # 法面の式(EDO-0270)── 生成器の一部として数える
    return {"gen": _sha(gen, soil) if gen.endswith("build_sashizu.py") else _sha(gen),
            "json": _sha(_os.path.join(sens_root(), "%s_sashizu.json" % estate)),
            "md": _sha(_os.path.join(sens_root(), "%s_kosho.md" % estate)),
            "lib": _sha(_os.path.abspath(__file__))}


def _sens_load(estate):
    if estate in _SENS_REC:
        return _SENS_REC[estate]
    try:
        with open(_sens_file(estate), encoding="utf-8") as f:
            rec = _json.load(f)
    except Exception:
        rec = {}
    _SENS_REC[estate] = rec
    return rec


def sens_stale(estate):
    """記録が古い(生成器か設計値が変わった)なら理由の一覧、新しければ []。"""
    rec = _sens_load(estate)
    if not rec.get("probes"):
        return ["記録が無い"]
    old, new = rec.get("fingerprint") or {}, sens_fingerprint(estate)
    JA = {"gen": "生成器", "json": "設計値", "md": "考証の文", "lib": "共通ライブラリ"}
    return ["%s が変わった" % JA[k] for k in ("gen", "json", "md", "lib")
            if old.get(k) != new.get(k)]


def sens(estate, name, fn, default=None):
    """感度試験を回す(`--deep`)か、前回の記録をそのまま返す(既定)。

    `fn` は引数なしで、従来どおりの戻り値を返す呼び出し可能。
    戻り値は json を往復するので tuple は list になる(展開は同じに効く)。
    同じ `(estate, name)` は 1 プロセスで一度しか回さない(土井は同じ束を 2 度呼ぶ)。
    """
    key = (estate, name)
    if key in _SENS_MEM:
        return _SENS_MEM[key]
    if deep_enabled():
        t0 = _time.time()
        val = fn()
        rec = _sens_load(estate)
        rec.setdefault("probes", {})[name] = val
        rec["fingerprint"] = sens_fingerprint(estate)
        rec["t"] = _time.strftime("%Y-%m-%dT%H:%M:%S")
        rec.setdefault("secs", {})[name] = round(_time.time() - t0, 1)
        try:
            with open(_sens_file(estate), "w", encoding="utf-8") as f:
                _json.dump(rec, f, ensure_ascii=False, indent=1)
        except Exception as ex:
            print("  ⛔ 感度試験の記録が書けない(%s): %s" % (name, ex))
        _SENS_SEEN.append((name, "回した", round(_time.time() - t0, 1)))
    else:
        rec = _sens_load(estate)
        if name in (rec.get("probes") or {}):
            val = rec["probes"][name]
            _SENS_SEEN.append((name, "記録", (rec.get("secs") or {}).get(name)))
        else:
            val = default
            _SENS_SEEN.append((name, "未実施", None))
    _SENS_MEM[key] = val
    return val


def sens_report(estate):
    """既定の run の末尾に 1 行で刷る — 何が回り、何が回っていないか。"""
    if deep_enabled():
        tot = sum(s or 0 for _n, _k, s in _SENS_SEEN)
        return ("感度試験(破壊試験): %d 束を実際に回した(計 %.0f 分)。記録 = %s"
                % (len(_SENS_SEEN), tot / 60.0,
                   _os.path.relpath(_sens_file(estate), _os.getcwd())))
    miss = [n for n, k, _s in _SENS_SEEN if k == "未実施"]
    stale = sens_stale(estate)
    rec = _sens_load(estate)
    head = ("感度試験(破壊試験): 回していない(既定) — 上の判定は %s に回した記録"
            % (rec.get("t") or "?"))
    if miss:
        return (head + "\n   ⛔ %d 束は**記録が無い = 回っていない**(合格ではない): %s"
                "\n   ⭕ `python3 Tools/Sashizu/build_sashizu.py %s --deep` で回すこと"
                % (len(miss), "・".join(miss), estate))
    if stale:
        return (head + "\n   ⚠ 記録が古い(%s)— 上の判定は**今の設計値のものではない**"
                "\n   ⭕ `python3 Tools/Sashizu/build_sashizu.py %s --deep` で回し直すこと"
                % ("・".join(stale), estate))
    return head + "(生成器・設計値とも記録のときと同じ)"


# ===========================================================================
# 検査ごとの所要を測る(2026-09-20)— どの検査が輪を長くしているかを毎回刷る
# ===========================================================================
_CHK_T = {}


def chk(name, fn):
    """検査を 1 本回し、所要を記録する。戻り値はそのまま。"""
    t0 = _time.time()
    try:
        return fn()
    finally:
        dt = _time.time() - t0
        _CHK_T[name] = _CHK_T.get(name, 0.0) + dt
        if dt >= 20:
            print("    ⏱ %s %.0f 秒" % (name, dt), flush=True)


def chk_report(top=10, floor=1.0):
    """重い順に刷る。`floor` 秒未満は畳む。"""
    if not _CHK_T:
        return ""
    tot = sum(_CHK_T.values())
    rows = sorted(_CHK_T.items(), key=lambda kv: -kv[1])[:top]
    rows = [(k, v) for k, v in rows if v >= floor]
    if not rows:
        return "検査 %d 本で計 %.0f 秒(どれも %.0f 秒未満)" % (len(_CHK_T), tot, floor)
    return ("検査 %d 本で計 %.0f 秒。重い順:\n" % (len(_CHK_T), tot)
            + "\n".join("    %6.1fs %5.0f%%  %s" % (v, 100 * v / tot, k) for k, v in rows))


# ================================================================ 囲いの内の幹(施主裁定 2026-09-23 EDO-0409)
def _seg_d(p, a, b):
    """点と線分の距離(世界 xz)。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
    return math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dz * t)


def _near_on_segs(p, segs):
    """線分の列の上で p に最も近い点と距離。"""
    best = (1e18, None)
    for a, b in segs:
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
        q = (a[0] + dx * t, a[1] + dz * t)
        dd = math.hypot(p[0] - q[0], p[1] - q[1])
        if dd < best[0]: best = (dd, q)
    return best


def kakoi_facing_road(runs, W, road_edges, facing_m):
    """**道辺に面する囲い**(柵・板塀)。戻り [{name, kind, pts(世界), inner(+1/-1 左法線に対する内側), roadM}]。

    ⭐ 散布(`impl_sanno.kakoi_inside_shapes`)と検査(`build_sashizu.Checks.c25`)が**この一本**を使う
      (⛔ 拾い方を二つ持たない)。⛔ 名前で決め打ちしない ── `runs[]` の `kind` が 柵/板塀 のうち、
      線上の探り点(各区間の t=1/4,1/2,3/4)が**どれも**道辺から `facing_m` 以内にある物。
    ⭐ 内側 = 道辺の反対側(区間ごとの多数決)。⛔ 位置が読めない run(生成前)は拾わない。
    """
    out = []
    if not road_edges: return out
    for r in runs:
        if r.get("kind") not in ("柵", "板塀"): continue
        pts = r.get("pts") or ([r["a"], r["b"]] if r.get("a") is not None and r.get("b") is not None else None)
        if not pts or len(pts) < 2: continue
        P = [tuple(W(q[0], q[1])) for q in pts]
        fc = _facing_segs([(P[i], P[i + 1]) for i in range(len(P) - 1)], road_edges, facing_m)
        if fc is None: continue
        out.append({"name": r.get("name"), "kind": r.get("kind"), "pts": P, "inner": fc[0], "roadM": fc[1]})
    return out


def _facing_segs(segs, road_edges, facing_m):
    """**道辺に面するか**の一本(世界 xz の区間の列)。各区間の t=1/4,1/2,3/4 の探り点が**どれも**道辺から
    `facing_m` 以内なら (内側の符号, 最も遠い探り点の道辺からの距離)、そうでなければ None。
    ⭐ 囲い(`kakoi_facing_road`)と土留め(`kakoi_lines`)が同じ式で判る(⛔ 同定の式を二つ持たない)。"""
    if not road_edges: return None
    ds, s = [], 0.0
    for a, b in segs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-9: continue
        nl = (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)
        for t in (0.25, 0.5, 0.75):
            m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            dd, q = _near_on_segs(m, road_edges)
            ds.append(dd)
            s += nl[0] * (q[0] - m[0]) + nl[1] * (q[1] - m[1])
    if not ds or max(ds) > facing_m: return None
    return (-1.0 if s > 0 else 1.0), max(ds)


def _offset_line(P, r):
    """折れ線を左法線へ r だけずらす(節は留め・角の二等分線)。r<0 は右。"""
    n = len(P)
    N = []
    for i in range(n - 1):
        a, b = P[i], P[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        N.append((-(b[1] - a[1]) / L, (b[0] - a[0]) / L))
    out = []
    for i in range(n):
        if i == 0: m, k = N[0], 1.0
        elif i == n - 1: m, k = N[-1], 1.0
        else:
            mx, mz = N[i - 1][0] + N[i][0], N[i - 1][1] + N[i][1]
            L = math.hypot(mx, mz) or 1.0
            m = (mx / L, mz / L)
            c = m[0] * N[i][0] + m[1] * N[i][1]
            k = 1.0 / max(c, 0.2)
        out.append((P[i][0] + m[0] * r * k, P[i][1] + m[1] * r * k))
    return out


def kakoi_half_thickness(d, run_name):
    """囲いの**半厚**[m]とその出どころ。戻り (半厚, 出どころ)。⛔ 値を発明しない ── 取れなければ 0 と明示。

    ・柵: `hFrom.garden` が指す庭の `tamagaki.postDiaM / 2`(柱の径。impl の `kakoi_avoid_shapes` と同じ欄)
    ・板塀: 指図に厚みの欄が無い。在庫の実寸(`itabei5` の奥行)は目録にあるが、線に対する据わり(表裏2枚・
      ずらし)は棟梁が実メッシュで測る値で紙からは決まらない ── 0 として『取れない』と返す。
    """
    r = next((x for x in d.get("runs") or [] if x.get("name") == run_name), None)
    if r is None: return 0.0, "取れない(run が無い)"
    hf = r.get("hFrom") or {}
    if r.get("kind") == "柵" and hf.get("garden"):
        gd = next((g for g in d.get("gardens") or [] if g.get("name") == hf["garden"]), None)
        pd = ((gd or {}).get("tamagaki") or {}).get("postDiaM")
        if pd: return float(pd) / 2.0, "gardens[%s].tamagaki.postDiaM/2" % hf["garden"]
    return 0.0, "取れない(%s に厚みの欄が無い — 0 で扱う)" % r.get("kind")


def kakoi_keepout_polys(fences, inside_m, d=None):
    """**囲いの道側全部** + **囲いの線を半径 r = inside_m + 半厚 で丸く膨らませた形**(世界 xz)。

    戻り [(名, 種, 形)]: 種 "poly" の形は [(x,z)…](道側)/ 種 "seg" の形は (a, b, r)(区間の帯と
    両端の円を一つにしたカプセル ── 各区間に一つずつ出すので、**各節と run の両端**にも円が付く)。
    判定は `kakoi_keepout_hit` の一本(散布は同じ形を `impl_sanno._shape_poly/_shape_seg` に写すだけ)。

    ⭐ 幹は囲いの**実体の面**から `inside_m` 以上(線=芯でなく、半厚ぶん足す)。⛔ 囲いの道側
    (囲いと道辺の間)には一本も置かない。道側の外縁は `roadM + inside_m`。
    ⭐ **run の端の先**(線の延長上)も円で締め出す(2026-09-23 EDO-0409: `Saku_SW` の終わりの柱の 1.10m 先に
    低木が立った)。半厚は `kakoi_half_thickness(d, 名)`(d が無ければ 0)。
    """
    out = []
    for f in fences:
        P, s = f["pts"], f["inner"]
        half = kakoi_half_thickness(d, f["name"])[0] if d is not None else 0.0
        r = inside_m + half
        inner = _offset_line(P, s * inside_m)
        outer = _offset_line(P, -s * (f["roadM"] + inside_m))
        out.append((f["name"], "poly", inner + list(reversed(outer))))
        for i in range(len(P) - 1):
            out.append((f["name"], "seg", (tuple(P[i]), tuple(P[i + 1]), r)))
    return out


def kakoi_keepout_hit(K, x, z):
    """点 (x,z) が `kakoi_keepout_polys` の形に載っていれば囲いの名、載っていなければ None。"""
    for nm, kind, g in K:
        if kind == "poly":
            if _pip((x, z), g): return nm
        elif kind == "polym":           # 多角形 + 余白 m(内か、辺から m 未満)── `kakoi_kado_fills`
            P, mm = g
            if _pip((x, z), P) or (mm > 0 and min(_seg_d((x, z), P[i], P[(i + 1) % len(P)])
                                                   for i in range(len(P))) < mm): return nm
        elif _seg_d((x, z), g[0], g[1]) < g[2]:
            return nm
    return None


def kakoi_line_m(d):
    """**塀・囲い・土留めの実体線からの幹の離れ**[m](`planting.bandDef.avoid.kakoiLineFrom` が指す欄の値)。
    宣言が無ければ None(⛔ 数を持たない ── 値は指し先の欄 = 道辺と同じ `kyoukaiRoadM`)。"""
    av = (((d.get("planting") or {}).get("bandDef") or {}).get("avoid") or {})
    k = av.get("kakoiLineFrom")
    v = av.get(k) if k else None
    return float(v) if isinstance(v, (int, float)) else None


def dodome_crest_depth(d, run):
    """土留めの**天端の奥行**[m]とその出どころ ── 紙の線(城の石垣=天端の前の縁 / 袖=段石の小口)から実物の天端の
    奥の縁まで。戻り (奥行, 出どころ, 種)。値は `planting.bandDef.avoid.dodomeCrestDepthM`(種 → m)。
    ・種: `coping` が "stair" の土留め = **袖**(石段の袖石 `IshidanSode` を段ごとに据える)/ ほか = 指図の
      `terraceWalls[].masonry`(無ければ **城の石垣**)。
    ⛔ 値を発明しない ── 種の値が無ければ 0 と『取れない』を返す。
    ⭐ 天端がどちら側へ伸びるかは紙で分からない(法の足元も反対側へ出る)ので、**両側へ取る**(保守側)。
    """
    av = (((d.get("planting") or {}).get("bandDef") or {}).get("avoid") or {})
    tbl = av.get("dodomeCrestDepthM") or {}
    if run.get("coping") == "stair":
        kd = "袖"
    else:
        tw = next((w for w in d.get("terraceWalls") or [] if w.get("name") == run.get("name")), {})
        kd = tw.get("masonry") or "城の石垣"
    v = tbl.get(kd)
    if isinstance(v, (int, float)):
        return float(v), "avoid.dodomeCrestDepthM[%s]" % kd, kd
    return 0.0, "取れない(avoid.dodomeCrestDepthM に %s が無い — 0 で扱う)" % kd, kd


def kakoi_lines(d, poly, runs, tamagaki, road_edges=None):
    """**塀・囲い・土留めの実体線のすべて**(世界 xz)。戻り [{name, kind, segs:[(a,b)…], half, halfFrom}]。

    【施主 2026-09-23 EDO-0409】幹の芯は、塀・囲い・土留めの**すべての**実体線から `kakoi_line_m` 以上内。
    ・区画の**全辺**(`poly` = 社地の `polygon`。道辺だけでなく隣地辺も ── 隣家の塀は区画線の上に立つ)
    ・算出物の `runs[]` の**建つ区間** `segs`(透塀・回廊・袖塀・柵・板塀・土留め `terraceWalls` の全部)
    ・算出物の `tamagaki[]` の**立てる辺**(`fence`)の建つ区間 ── **`avoid.kakoiLineTamagaki` が true のときだけ**
      (玉垣を囲いに数えるかは施主の裁定待ち・既定は数えない 2026-09-23)
    ⭐ 散布(`impl_sanno.kakoi_line_shapes`)と検査(`build_sashizu.Checks.c29`)が**この一本**を使う。
    ⭐ 半厚: 柵・玉垣は柱の径の半分(`kakoi_half_thickness` / `tamagaki.spec.postDiaM`)、ほかは指図に厚みの
      欄が無いので 0 と明示(⛔ 発明しない)。
    ⭐ **土留めは天端の奥の縁から測る**(普請検査の実測 2026-09-25 EDO-0409)── 半厚の代わりに天端の奥行
      `dodome_crest_depth` を両側へ取る。⭐ 2m を当てるのは**道に面する土留めだけ**(施主裁定B 2026-09-25)──
      判定は柵・板塀と同じ `_facing_segs`(`avoid.kakoiFacingRoadM`)。道に面さない土留めは `facing`=False で、
      退けるのは実体(線 + 天端の奥行)だけ。`road_edges` が無ければ判定できないので道に面するとみる(保守側)。
    """
    out = []
    av = (((d.get("planting") or {}).get("bandDef") or {}).get("avoid") or {})
    P = [tuple(q[:2]) for q in (poly or [])]
    # `avoid.kakoiLineExceptEdges`(辺の番号の列)を宣言した邸だけ、その区画の辺には `m` を当てない
    #   (土井 2026-10-04: 松江松平との谷の境は沢を開けたままで、両岸の林を切らない ── EDO-0554 の施主裁定の申し送り)。
    #   宣言の無い邸は一字も変わらない。退けるのは辺の実体(半厚 0)だけ ── `facing` = False と同じ扱い
    ex = set(int(i) for i in (av.get("kakoiLineExceptEdges") or []) if isinstance(i, (int, float)))
    for i in range(len(P)):
        row = {"name": "区画の辺%d" % i, "kind": "区画の辺", "segs": [(P[i], P[(i + 1) % len(P)])],
               "half": 0.0, "halfFrom": "取れない(区画の線 — 0 で扱う)"}
        if i in ex:
            row["facing"] = False
            row["halfFrom"] += "・avoid.kakoiLineExceptEdges で離れを当てない"
        out.append(row)
    for r in runs or []:
        sg = [(tuple(a[:2]), tuple(b[:2])) for a, b in (r.get("segs") or [])]
        if not sg: continue
        if r.get("of") != "wall" and r.get("kind") != "土留め":
            h, hf = kakoi_half_thickness(d, r.get("name"))
            out.append({"name": r.get("name"), "kind": r.get("kind") or "?", "segs": sg, "half": h, "halfFrom": hf})
            continue
        h, hf, kd = dodome_crest_depth(d, r)
        fm = av.get("kakoiFacingRoadM")
        fc = (road_edges is None or fm is None
              or _facing_segs(sg, road_edges, float(fm)) is not None)
        out.append({"name": r.get("name"), "kind": "土留め(%s)" % kd, "segs": sg, "half": h,
                    "halfFrom": "天端の奥行 " + hf, "facing": fc})
    for t in (tamagaki or []) if av.get("kakoiLineTamagaki") is True else []:
        if not t.get("fence"): continue
        sg = [(tuple(a[:2]), tuple(b[:2])) for a, b in (t.get("segs") or [])]
        if not sg: continue
        pd = ((t.get("spec") or {}).get("postDiaM"))
        out.append({"name": "玉垣:%s %s" % (t.get("garden"), t.get("edge")), "kind": "玉垣", "segs": sg,
                    "half": float(pd) / 2.0 if pd else 0.0,
                    "halfFrom": "tamagaki.postDiaM/2" if pd else "取れない(玉垣に柱径の欄が無い — 0 で扱う)"})
    return out


_KAKOI_MEET_EPS = 0.01      # 端が相手の線の上にあるとみなす幾何の誤差[m](設計値ではない ── 算出物は同じ点を共有する)


def kakoi_line_ends(lines, eps=_KAKOI_MEET_EPS):
    """**2m を当てる線の端を、出会う相手の壁の実体の分だけ延ばす**(普請検査の実測 2026-09-25 EDO-0409)。

    出隅・T の取り合いでは、相手の壁の実体(土留め = 天端の奥行 / 柵 = 柱の径の半分 ── `kakoi_lines` の `half`)が
    こちらの線の端より外へ出うる。出隅では、相手の土留めの法の足元が道に面した線の端より外へ出る(実測 1.00m)。
    延長量はその天端の奥行きの欄(`dodome_crest_depth`)で保守的に取る。
    【典拠: 普請検査の実測 2026-09-26 EDO-0409・前庭の `TW_Zentei_W_x_N_kado` ── 角石の外隅は北の線の始点と一致
    (差 0.000m)、天端は両 run に沿う 3.40m の L 字で線の端より外へ出ない。出るのは法の足元だけ。確度 A】
    ・対象は `m` を当てる線(`facing` が False でない線)の**端**(同じ線の別の区間と繋がらない区間の端点)。
    ・その端が**他の線**の区間の上(`eps` 以内)にあれば、端を自分の区間の向きに沿って外へ、出会う相手の `half` の
      最大だけ延ばす。⛔ 相手を道に面した扱いにしない(相手の線はそのまま)。⛔ 延ばす量を測らない ── 欄の値だけ。
    ・土留めの上に立つ塀(全区間が土留めの線の上)は、相手の土留めでは延ばさない ── 角の天端は下の土留めの物。
    ⭐ 天端がどちらへ伸びるか紙で分からないので、出隅も入隅も同じに延ばす(保守側・`dodome_crest_depth` と同じ理屈)。
    戻り: 線ごとの区間の列 [[(a', b')…]…] と、延ばした記録 [(線の名, 端の点, 相手の名, 延ばした m)…]。
    """
    out_segs, log = [], []
    for i, ln in enumerate(lines):
        segs = list(ln["segs"])
        if ln.get("facing", True) is False:
            out_segs.append(segs)
            continue
        pts = [p for s in segs for p in s]
        # ⭐ 土留めの上に立つ塀(透塀が腰石垣の上に立つ等)は、角の天端が**下の土留めの物** ── その土留めが道に
        #   面するか否かに従う。塀の端を土留めの天端で延ばさない(延ばすと面さない土留めの角へ 2m を当てる)。
        on_wall = not str(ln.get("kind", "")).startswith("土留め") and all(
            any(_seg_d(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), c, e) < eps
                for o in lines if str(o.get("kind", "")).startswith("土留め") for c, e in o["segs"])
            for a, b in segs)
        new = []
        for a, b in segs:
            L0 = math.hypot(b[0] - a[0], b[1] - a[1])
            if L0 < 1e-9:
                new.append((a, b))
                continue
            ux, uz = (b[0] - a[0]) / L0, (b[1] - a[1]) / L0
            ends = []
            for p, sg in ((a, -1.0), (b, 1.0)):
                if sum(1 for q in pts if math.hypot(q[0] - p[0], q[1] - p[1]) < eps) > 1:
                    ends.append(p)          # 同じ線の節(繋がる区間がある)── 延ばさない
                    continue
                h, who = 0.0, None
                for j, o in enumerate(lines):
                    if j == i or o["half"] <= 0.0: continue
                    if on_wall and str(o.get("kind", "")).startswith("土留め"): continue
                    if any(_seg_d(p, c, e) < eps for c, e in o["segs"]) and o["half"] > h:
                        h, who = o["half"], o["name"]
                if who is None:
                    ends.append(p)
                    continue
                ends.append((p[0] + sg * ux * h, p[1] + sg * uz * h))
                log.append((ln["name"], p, who, h))
            new.append((ends[0], ends[1]))
        out_segs.append(new)
    return out_segs, log


def dodome_kado_leg(d, kind):
    """土留めの**隅の駒の天端の腕の長さ**[m](紙の線の交点から、各線に沿って天端の L 字が伸びる長さ)と出どころ。
    値は `planting.bandDef.avoid.dodomeKadoLegM`(種 → m・種は `kakoi_lines` の『土留め(<種>)』)。
    ⛔ 値を発明しない ── 種の値が無ければ None(その種の隅は三角を足さない)。"""
    av = (((d.get("planting") or {}).get("bandDef") or {}).get("avoid") or {})
    v = (av.get("dodomeKadoLegM") or {}).get(kind)
    return (float(v), "avoid.dodomeKadoLegM[%s]" % kind) if isinstance(v, (int, float)) else (None, None)


def _clip_half(P, o, n, c):
    """多角形 P の、(q − o)·n ≤ c の側だけ(Sutherland–Hodgman の一辺)。"""
    out = []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        fa = (a[0] - o[0]) * n[0] + (a[1] - o[1]) * n[1] - c
        fb = (b[0] - o[0]) * n[0] + (b[1] - o[1]) * n[1] - c
        if fa <= 0: out.append(a)
        if fa * fb < 0:
            t = fa / (fa - fb)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _poly_area(P):
    return abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))) / 2.0


def kakoi_kado_fills(d, lines, eps=_KAKOI_MEET_EPS):
    """**土留めの隅の駒の天端が入隅を斜めに埋める三角**(世界 xz)。戻り [(名, [(x,z)×3…], m を当てるか)]。

    【普請検査の実測 2026-09-26 EDO-0409】隅の駒(`EdoAssets.Own.IshigakiKado`)の天端は、紙の線の交点 V から両方の線に
    沿って腕の長さ `dodome_kado_leg` の **L 字**(幅 = 天端の奥行 `dodome_crest_depth`)で、L の入隅を斜めの辺で埋める
    ── 帯(線 + 天端の奥行)に入らない三角 C = V + h·e1 + h·e2 / A = V + ℓ·e1 + h·e2 / B = V + h·e1 + ℓ·e2
    (e1, e2 = V から各線が延びる向き・h = 天端の奥行・ℓ = 腕の長さ)が残る。前庭の低木009 がこの斜めの辺から 1.940 m で
    2 m を割り、線のカプセルだけの C29 は通していた。
    ・対象: 土留めの線の端(または同じ線の節)どうしが `eps` 以内で出会い、折れる所(一直線は除く)。両方の種に腕の長さの
      欄があるときだけ(袖・柵には隅の駒が無い)。天端がどちら側へ伸びるか紙で分からないので、**折れの内角の側に取る**
      (出隅も入隅も同じ・保守側 ── `dodome_crest_depth` と同じ理屈)。
    ・施主裁定B(2026-09-25): 数えるのは**道に面した側の天端の帯だけ** ── 片方だけ道に面する隅は、三角のうち面した線から
      天端の奥行 h 以内の所だけを残す(三角はどちらの線からも h 以上奥なので、直角の隅では何も残らない)。
      両方とも面さなければ退けるのは実体(三角そのもの・m を足さない)。
    """
    ends = []                                           # (点, 延びる向き, 線の添字, 種)
    for i, ln in enumerate(lines):
        k = str(ln.get("kind", ""))
        if not k.startswith("土留め("): continue
        kd = k[len("土留め("):-1]
        for a, b in ln["segs"]:
            L0 = math.hypot(b[0] - a[0], b[1] - a[1])
            if L0 < 1e-9: continue
            u = ((b[0] - a[0]) / L0, (b[1] - a[1]) / L0)
            ends.append((a, u, i, kd))
            ends.append((b, (-u[0], -u[1]), i, kd))
    out, seen = [], set()
    for x in range(len(ends)):
        for y in range(x + 1, len(ends)):
            p, e1, i, k1 = ends[x]
            q, e2, j, k2 = ends[y]
            if math.hypot(p[0] - q[0], p[1] - q[1]) >= eps: continue
            cr = e1[0] * e2[1] - e1[1] * e2[0]
            if abs(cr) < 1e-3 or e1[0] * e2[0] + e1[1] * e2[1] < -0.999: continue    # 一直線(継ぎ目・折れない)
            l1, _ = dodome_kado_leg(d, k1)
            l2, _ = dodome_kado_leg(d, k2)
            if l1 is None or l2 is None: continue
            key = (round(p[0], 2), round(p[1], 2), min(i, j), max(i, j))
            if key in seen: continue
            seen.add(key)
            A, B = lines[i], lines[j]
            h, ell = max(A["half"], B["half"]), min(l1, l2)
            if ell <= h: continue
            V = p
            T = [(V[0] + h * e1[0] + h * e2[0], V[1] + h * e1[1] + h * e2[1]),
                 (V[0] + ell * e1[0] + h * e2[0], V[1] + ell * e1[1] + h * e2[1]),
                 (V[0] + h * e1[0] + ell * e2[0], V[1] + h * e1[1] + ell * e2[1])]
            fa, fb = A.get("facing", True) is not False, B.get("facing", True) is not False
            nm = "%s×%s の隅の天端" % (A["name"], B["name"]) if i != j else "%s の隅の天端" % A["name"]
            if fa and fb:
                out.append((nm, T, True))
                continue
            if not fa and not fb:
                out.append((nm, T, False))
                continue
            # 片方だけ道に面する ── 面した線から天端の奥行 h 以内の所だけに m を当て、残りは実体だけ退ける
            ef, eo = (e1, e2) if fa else (e2, e1)
            n = (-ef[1], ef[0])
            if n[0] * eo[0] + n[1] * eo[1] < 0: n = (-n[0], -n[1])       # 面した線から三角の側への法線
            Tf = _clip_half(T, V, n, h)
            To = _clip_half(T, V, (-n[0], -n[1]), -h)
            if len(Tf) >= 3 and _poly_area(Tf) > 1e-6: out.append((nm + "(道に面した側)", Tf, True))
            if len(To) >= 3 and _poly_area(To) > 1e-6: out.append((nm, To, False))
    return out


def kakoi_line_keepout(lines, m, d=None):
    """`kakoi_lines` の各区間を半径 `m + 半厚` で膨らませたカプセル(両端・各節も丸い)。
    形は `kakoi_keepout_polys` の "seg" と同じで、判定は `kakoi_keepout_hit` の一本。
    ⭐ 道に面さない土留め(`facing` = False)は `m` を足さず、実体(線 + 天端の奥行)だけを退ける(施主裁定B 2026-09-25)。
    ⭐ `m` を当てる線の端は、出会う相手の壁の実体の分だけ延ばしてから膨らませる(`kakoi_line_ends`)。
    ⭐ `d` を渡せば、土留めの隅の駒の天端が入隅を斜めに埋める三角(`kakoi_kado_fills`)を種 "polym"(多角形 + 余白)で足す
      (普請検査の実測 2026-09-26 EDO-0409)。"""
    S, _log = kakoi_line_ends(lines)
    out = [(ln["name"], "seg", (a, b, (m if ln.get("facing", True) else 0.0) + ln["half"]))
           for ln, sg in zip(lines, S) for a, b in sg]
    if d is not None:
        out += [(nm, "polym", (T, m if fc else 0.0)) for nm, T, fc in kakoi_kado_fills(d, lines)]
    return out


def do_rin_rects(d):
    """**堂・棟の外面**(uv の矩形・間)── 3間の離れ(`planting.clearance.keidai.doRinKen`)を測る相手。
    戻り [(名, (u0, v0, u1, v1), 基壇の出[m] か None)]。

    ・`munes[]`(⛔ `yaku` = 接続 は隣の棟の内側なので除く)。矩形は `u0,v0,du,dv`(柱芯の矩形)。
    ・`clearance.keidai.doRinKenOf` に "ido" があれば**井戸屋形**(`ido.uv` ± `hashiraPitchKen`/2 = 柱芯の矩形)。
      (井戸屋形を棟に数えるかは施主の裁定待ち・既定は `["munes"]` = 数えない 2026-09-23)
    ⭐ **基壇の出**は棟の `munes[].kidanM.out`、無ければ `bom[]` の行(『部材』を『・』と括弧で割った語にその棟の
      名がある行)の `kidanM.out` があれば外へ足す。
      無い棟は None を返し、検査は『基壇を含まない』と名乗る(⛔ 出を発明しない)。
    """
    ken = d["const"]["ken"]
    kd = (((d.get("planting") or {}).get("clearance") or {}).get("keidai") or {})
    of = kd.get("doRinKenOf") or ["munes"]
    out = []

    def kidan(nm, m=None):
        # ⭐ まず棟の欄 `munes[].kidanM.out`(部材の基壇の写し)、無ければ `bom[]` の行 ── 行は「鐘楼・鼓楼・
        #   附属堂(其一・其五・其八ほか)・観音堂…」とまとめて書くので、『・』と括弧で割った語で当てる
        #   (「附属堂 其五」は頭の語「附属堂」でも当てる)。⛔ 出を発明しない。
        k = ((m or {}).get("kidanM") or {}).get("out")
        if isinstance(k, (int, float)): return float(k)
        keys = {nm, nm.split()[0]} if nm.split() else {nm}
        for b in d.get("bom") or []:
            bn = str(b.get("部材") or "")
            words = set(w.strip() for w in re.split(r"[・()（）、]", bn) if w.strip())
            if (bn.startswith(nm) or keys & words) and isinstance((b.get("kidanM") or {}).get("out"), (int, float)):
                return float(b["kidanM"]["out"])
        return None
    if "munes" in of:
        for m in d.get("munes") or []:
            if m.get("yaku") == "接続" or m.get("u0") is None: continue
            # 矩形は `u0,v0,du,dv`(山王)か `u0,v0,u1,v1`(土井)── どちらも柱芯の矩形。どちらも無ければ測れない(飛ばす)
            u1 = m["u0"] + m["du"] if m.get("du") is not None else m.get("u1")
            v1 = m["v0"] + m["dv"] if m.get("dv") is not None else m.get("v1")
            if u1 is None or v1 is None: continue
            k = kidan(m["name"], m)
            e = (k or 0.0) / ken
            out.append((m["name"], (m["u0"] - e, m["v0"] - e, u1 + e, v1 + e), k))
    io = d.get("ido")
    if "ido" in of and io and io.get("uv"):
        u, v = io["uv"]
        p = io["hashiraPitchKen"] / 2.0
        nm = io.get("name") or "井戸屋形"
        k = kidan(nm)
        e = (k or 0.0) / ken
        out.append((nm, (u - p - e, v - p - e, u + p + e, v + p + e), k))
    return out


def do_rin_dist(R, u, v):
    """点 (u,v) から `do_rin_rects` の最も近い外面まで[間](内なら 0)と、その名。"""
    best = (1e18, None)
    for nm, (u0, v0, u1, v1), _k in R:
        du = max(u0 - u, 0.0, u - u1)
        dv = max(v0 - v, 0.0, v - v1)
        dd = math.hypot(du, dv)
        if dd < best[0]: best = (dd, nm)
    return best


# ================================================================ 道の上の枝下(EDO-0409 2026-09-25)
def edashita_profile(s):
    """目録 `docs/asset-index.tsv` の `edashita` 列(`r:h;r:h…` ── r = 0.5m 刻みの環の外半径・h = その環の最も
    低い頂点の足元からの高さ。scale 1・m)を [(r, h)…] に。空・読めなければ []。"""
    out = []
    for tok in (s or "").split(";"):
        if ":" not in tok: continue
        a, b = tok.split(":", 1)
        try: out.append((float(a), float(b)))
        except ValueError: return []
    return sorted(out)


def road_region(own_poly, parcels):
    """**道の上か**を答える関数 ── 道 = 敷地割の間に残った領域(自身の区画の外で、どの区画にも入らない所)。
    `own_poly` は自身の区画(世界 xz)、`parcels` は [(id, 多角形(世界 xz))](自身を含んでよい ── 自身と同じ
    輪郭の区画は除く)。⛔ 道の幅を持たない。"""
    own = [tuple(q[:2]) for q in own_poly]
    Q = []
    for _pid, pp in parcels:
        P = [tuple(q[:2]) for q in pp]
        if len(P) == len(own) and all(abs(a[0] - b[0]) + abs(a[1] - b[1]) < 1e-3 for a, b in zip(P, own)):
            continue
        xs, zs = [q[0] for q in P], [q[1] for q in P]
        Q.append(((min(xs), min(zs), max(xs), max(zs)), P))

    def is_road(p):
        if _pip(p, own): return False
        for (x0, z0, x1, z1), P in Q:
            if x0 <= p[0] <= x1 and z0 <= p[1] <= z1 and _pip(p, P): return False
        return True
    return is_road


def edashita_over_road(pt, rec, is_road, road_y, need_m, own_poly=None, n_ang=24):
    """**道の上へ張り出す樹冠の枝下**(`planting.bandDef.avoid.edaShitaOverRoadM`)。散布と検査の一本。

    木 `pt`(焼いた点: world・y(足元の地盤)・scaleXZ・scaleY)と部材の目録の行 `rec`(crown_r・edashita・
    trunk_dx/dz)から、樹冠の各環 r(部材の r × scaleXZ)のうち**道の上に在る所**で
      要る枝下 = 路面 `road_y(p)` − 足元の地盤 + `need_m`
      ある枝下 = edashita(r) × scaleY
    を比べる。環は内外の縁と中ほどの三つの半径 × `n_ang` 方位で探る。幹の足の片寄り(trunk_dx/dz)は向きが
    焼きに無いので、その長さ × scaleXZ だけ環を内外へ広げて探る(保守側)。
    戻り None(満たす・張り出さない・目録に枝下が無い物は `"noProfile"` を返す)か
    {"ringM", "needM", "haveM", "shortM", "at"}(最も足りない所)。
    ⛔ 樹冠の丸みを発明しない ── 環の高さは目録の実測(部材の最も低い頂点)。
    """
    prof = edashita_profile((rec or {}).get("edashita"))
    if not prof: return "noProfile"
    xz = float(pt.get("scaleXZ") or 1.0)
    sy = float(pt.get("scaleY") or 1.0)          # ⭐ 実装は scaleY が無ければ 1(EdoSannoShaRebuild)
    off = math.hypot(float(rec.get("trunk_dx") or 0.0), float(rec.get("trunk_dz") or 0.0)) * xz
    x0, z0 = pt["world"][0], pt["world"][1]
    y0 = float(pt["y"])
    reach = prof[-1][0] * xz + off
    if own_poly is not None and _pip((x0, z0), own_poly):
        # 張り出しの届かない木は探らない(区画の辺まで reach より遠い)
        n = len(own_poly)
        dmin = min(_seg_d((x0, z0), tuple(own_poly[i][:2]), tuple(own_poly[(i + 1) % n][:2])) for i in range(n))
        if dmin > reach: return None
    worst = None
    rin = 0.0
    for r, h in prof:
        have = h * sy
        for rr in (max(rin * xz - off, 0.0), (rin + r) / 2.0 * xz, r * xz + off):
            if rr <= 1e-6: continue
            for k in range(n_ang):
                a = 2.0 * math.pi * k / n_ang
                p = (x0 + rr * math.cos(a), z0 + rr * math.sin(a))
                if not is_road(p): continue
                ry = road_y(p)
                if ry is None: continue
                need = ry - y0 + float(need_m)
                if have < need - 1e-9 and (worst is None or need - have > worst["shortM"]):
                    worst = {"ringM": round(r * xz, 3), "needM": round(need, 3), "haveM": round(have, 3),
                             "shortM": round(need - have, 3), "at": [round(p[0], 2), round(p[1], 2)]}
        rin = r
    return worst


# ================================================================ 植栽の散布(共通 ── EDO-0502)
#   ⭐ 山王(`impl_sanno.scatter_pts`)と岡部(`impl_okabe.bake_planting`)が同じ撒き方を使う。
#   ⛔ 邸ごとに写しを持たない ── 種・本数の配り方・芯々の採り方が邸で違うと、検査(C25〜C30)の前提が崩れる。

def plant_rnd(d, name, lay):
    """撒く乱数の種 ── **`planting.plantRule.seed` の宣言そのもの**(「帯・区の名 + '/' + 層の名」)。

    ⛔ 時刻や連番で振らない(流し直すたびに木が動くと検証レンダが比較できない)。
    ⛔ 宣言が無ければ止める — 種の出所が指図に無いまま撒くと、**同じ指図から別の林**が出る。
    戻り (random.Random, 種の語)。
    """
    import random
    if not (((d.get("planting") or {}).get("plantRule") or {}).get("seed")):
        raise SystemExit("`planting.plantRule.seed` の宣言が無い — 撒く種の出所が指図に無い")
    key = "%s/%s" % (name, lay)
    return random.Random(int(_hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)), key


def apportion(vals, tot):
    """実数の列 `vals` を、和が `tot` になる整数へ**最大剰余法**で配る。

    ⛔ 帯ごとに丸めない — 帯ごとに丸めると和が予算表と食い違い、「焼いた点の数 = 図が刷った本数」の検査が立たない。
    """
    fl = [int(math.floor(max(0.0, v))) for v in vals]
    rest = tot - sum(fl)
    order = sorted(range(len(vals)), key=lambda i: (-(max(0.0, vals[i]) - fl[i]), i))
    for i in order[:max(0, rest)]:
        fl[i] += 1
    return fl


def scatter_take(rnd, cells, n, rmin, seeded=(), other=(), rx=0.0, accept=None):
    """候補のセルから **n 点**を決定論的に採る。芯々の下限は `rmin`(セルと同じ単位)。

    ⭐ **層をまたぐ幹の芯々 `rx` は硬い(許容0)**【EDO-0420 2026-09-23】── `other` は**別の層**で位置の決まった幹。
      ⛔ `rx` は `rmin` と違って**緩めない** ── 採りきれなければ `got < want` で名乗る。
    ⭕ 位置は**セルの中心のまま**(⛔ 揺らぎを足さない ── 中心を外すと退避へはみ出す)。
    ⚠ 採りきれなければ `rmin` を 0.9 倍して採り直す(柔らかい条件)。**緩めた回数は記録に残す**。
    ⭐ `accept(p)` があれば、芯々を満たした候補を**さらにその口で**採るか決める(硬い制約 ── 道の上の枝下など)。
    戻り (点, 実際の rmin, 緩めた回数)。
    """
    cs = list(cells)
    rnd.shuffle(cs)
    if other and rx > 0:
        go = {}
        for q in other:
            go.setdefault((int(math.floor(q[0] / rx)), int(math.floor(q[1] / rx))), []).append(q)

        def _clear(p):
            c = (int(math.floor(p[0] / rx)), int(math.floor(p[1] / rx)))
            return not any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < rx * rx
                           for a in range(c[0] - 1, c[0] + 2) for b in range(c[1] - 1, c[1] + 2)
                           for q in go.get((a, b), ()))
        cs = [p for p in cs if _clear(p)]
    fix = [tuple(q) for q in seeded]
    r, relax = float(rmin), 0
    while True:
        gr, out = {}, []
        for q in fix:
            gr.setdefault((int(math.floor(q[0] / r)), int(math.floor(q[1] / r))), []).append(q)
        for p in cs:
            c = (int(math.floor(p[0] / r)), int(math.floor(p[1] / r)))
            ok = True
            for a in range(c[0] - 1, c[0] + 2):
                for b in range(c[1] - 1, c[1] + 2):
                    for q in gr.get((a, b), ()):
                        if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < r * r:
                            ok = False
                            break
                    if not ok: break
                if not ok: break
            if not ok: continue
            if accept is not None and not accept(p): continue
            gr.setdefault(c, []).append(p)
            out.append(p)
            if len(out) >= n: return out, r, relax
        if len(out) >= n or relax >= 40 or r < 1e-3:
            return out, r, relax
        r *= 0.9
        relax += 1


_PART_RE = re.compile(r"^\s*([A-Za-z]+)\.([A-Za-z]+)\(([^)]*)\)\s*(.*)$")


def plant_part(s):
    """指図の `planting.parts` の一行(`Own.Matsu(Mid|Big,1..3) クロマツ` の書式)を読む。

    戻り {fam, name, sizes[], idx[], note, detail} か None(読めない行)。
    ・括弧の第1項は大きさの選択肢(`|` 区切り)、第2項は個体の範囲(`1..3`)。大きさを持たない部材
      (`JG.Fern(1|2)`)は第1項が個体になる ── 呼び手は `sizes` を個体として読む。
    ・`detail` は行の末尾の語(地形の詳細メッシュで撒く層 ── 点としては焼かない)。
    """
    m = _PART_RE.match(s or "")
    if not m: return None
    fam, nm, inner, rest = m.groups()
    args = [a.strip() for a in inner.split(",")]
    sizes = [x for x in (args[0].split("|") if args and args[0] else []) if x]
    idx = [1]
    if len(args) > 1 and ".." in args[1]:
        a, b = args[1].split("..", 1)
        idx = list(range(int(a), int(b) + 1))
    elif len(args) > 1 and args[1].isdigit():
        idx = [int(args[1])]
    return {"fam": fam, "name": nm, "sizes": sizes, "idx": idx, "note": rest.strip(),
            "detail": "detail" in rest.split()}


def grid_sampler(g):
    """算出物の世界格子(`graded` ── x0・z0・step・nx・nz・h[行][列]、None = 区画の外)を**双一次**で引く関数。

    ⭐ 実装(`EdoOkabeYashikiBuilder.WGrid.At`)と同じ読み方 ── 四隅のうち値のある節点だけで重みを割る。
    戻り f(x, z) → y か None。
    """
    x0, z0, st, nx, nz, H = g["x0"], g["z0"], g["step"], g["nx"], g["nz"], g["h"]

    def at(x, z):
        fx, fz = (x - x0) / st, (z - z0) / st
        i0, j0 = int(math.floor(fx)), int(math.floor(fz))
        tx, tz = fx - i0, fz - j0
        acc = wt = 0.0
        for dj in (0, 1):
            for di in (0, 1):
                i, j = i0 + di, j0 + dj
                if i < 0 or i >= nx or j < 0 or j >= nz: continue
                v = H[j][i]
                if v is None: continue
                w = (1.0 - tx if di == 0 else tx) * (1.0 - tz if dj == 0 else tz)
                acc += v * w
                wt += w
        return acc / wt if wt > 1e-9 else None
    return at


# ================================================================ 土留めの線を関係から解く(EDO-0502)
#   指図の `terraceWalls[]` が**関係だけ**(`between: [面, 面/辺]`・種別・天端・高さ・区間の言葉)で書かれた邸
#   (岡部)の、置き場の線を面の区域(terraces の poly)・区画の辺(polygon / runs)から解く。⛔ 指図は座標を書かない
#   (規則2・5)⇒ 線はここで毎回解き、算出物 `<邸>_impl.json` の `terraceWalls` にだけ焼く。
#   ⭐ 上の面の縁 = 天端の線。下の面との間は石垣の面で受ける(下の面は壁の足元まで延ばす)。
#   ⭐ 造成の式(`graded_y`)は `d["_twLines"]`(ここの戻り)を読んで段を付ける ── 欄が無い邸は一字も変わらない。
#   型(`mode`):
#     fill  面↔面 ── 上の面の縁に立つ。下の側へ上の面の盛の法を出さない。間が空いていれば下の面を壁の足元まで延ばす
#     back  面↔「辺N〜Mの長屋の背」── 長屋の背から `face` の間数の線。上の面をその線まで内へ引く(clip)
#     cut   面↔「辺N〜Mの切りの法」── 面の縁に立ち、切りの法を受ける。上は `above` の勾配の土羽
#     sode  「法(X↔Y)の端」↔面 ── X と Y の間の法が下の面に突き当たる所。天端は段違い・落差が `stop` 未満で止める
#     toe   「面の…法尻」↔「辺N(端)…」── 当家の囲いの内面の線。盛の法をここで受ける(足元の外へ盛を出さない)
#   ⛔ 解けない本・部分は推し量らず (名, 理由) で返す。

TW_RAY_KEN = 3.0        # 面↔面: 上の面の縁から下の面を探す距離[間](これより離れた縁は向かい合っていない)
TW_STEP_KEN = 0.25      # 縁を刻む間隔[間]
TW_BRIDGE_KEN = 2.0     # 同じ本の切れ目(石段の口)をまたいで一本にする上限[間]


def tw_relational(d):
    """関係で書いた土留め(`between` が並び・`a`/`b`/`edgeOf` を持たない)。"""
    return [w for w in (d.get("terraceWalls") or [])
            if isinstance(w.get("between"), list) and "a" not in w and not w.get("edgeOf")]


def _tw_area(P):
    return 0.5 * sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))


def _tw_ccw(P):
    P = [tuple(q[:2]) for q in P]
    return P if _tw_area(P) > 0 else P[::-1]


def _tw_near(P, u, v, closed=True):
    """折れ線(closed なら輪)の最寄り: (距離, 辺番号, t, 点)。"""
    n = len(P)
    best = (1e18, 0, 0.0, P[0])
    for i in range(n if closed else n - 1):
        a, b = P[i], P[(i + 1) % n]
        du, dv = b[0] - a[0], b[1] - a[1]
        L2 = du * du + dv * dv
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((u - a[0]) * du + (v - a[1]) * dv) / L2))
        q = (a[0] + du * t, a[1] + dv * t)
        dd = math.hypot(u - q[0], v - q[1])
        if dd < best[0]:
            best = (dd, i, t, q)
    return best


def _tw_ray(o, dvec, P, maxd):
    """o から dvec(単位)へ射た半直線が輪 P の辺に当たる最初の距離。当たらなければ None。"""
    best = None
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = dvec[0] * ey - dvec[1] * ex
        if abs(den) < 1e-12:
            continue
        wx, wy = a[0] - o[0], a[1] - o[1]
        s = (wx * ey - wy * ex) / den
        t = (wx * dvec[1] - wy * dvec[0]) / den
        if s >= 0.0 and -1e-9 <= t <= 1.0 + 1e-9 and s <= maxd and (best is None or s < best):
            best = s
    return best


def _tw_stations(P, step=TW_STEP_KEN):
    """輪 P(反時計回り)を刻む: [(辺番号, t0, t1, 中点, 外向きの法線)]。"""
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        Ln = math.hypot(b[0] - a[0], b[1] - a[1])
        if Ln < 1e-9:
            continue
        k = max(1, int(math.ceil(Ln / step)))
        nrm = ((b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln)      # 反時計回りの輪の外向き = 右の法線
        for j in range(k):
            t0, t1 = j / float(k), (j + 1) / float(k)
            tm = (t0 + t1) / 2
            out.append((i, t0, t1, (a[0] + (b[0] - a[0]) * tm, a[1] + (b[1] - a[1]) * tm), nrm))
    return out


def _tw_runs(P, st, keep):
    """刻みのうち keep が真の連なりを折れ線にする(輪の継ぎ目をまたぐ)。戻り [[点...]]。"""
    n = len(st)
    if not any(keep):
        return []
    if all(keep):
        return [list(P) + [P[0]]]
    s0 = next(i for i in range(n) if keep[i] and not keep[i - 1])
    runs, cur = [], None
    for k in range(n):
        i = (s0 + k) % n
        if keep[i]:
            if cur is None:
                cur = [i]
            else:
                cur.append(i)
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    out = []
    for r in runs:
        pts = []
        for idx in r:
            e, t0, t1 = st[idx][0], st[idx][1], st[idx][2]
            a, b = P[e], P[(e + 1) % len(P)]
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            if not pts or math.hypot(pts[-1][0] - p0[0], pts[-1][1] - p0[1]) > 1e-9:
                pts.append(p0)
            pts.append(p1)
        out.append(_tw_simplify(pts))
    return out


def _tw_simplify(pts, tol=0.01):
    """Douglas–Peucker(開いた折れ線)。"""
    if len(pts) <= 2:
        return list(pts)
    a, b = pts[0], pts[-1]
    dmax, k = -1.0, 0
    for i in range(1, len(pts) - 1):
        dd = _tw_near([a, b], pts[i][0], pts[i][1], closed=False)[0]
        if dd > dmax:
            dmax, k = dd, i
    if dmax <= tol:
        return [a, b]
    return _tw_simplify(pts[:k + 1], tol)[:-1] + _tw_simplify(pts[k:], tol)


def _tw_len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _tw_offset_chain(pts, D):
    """開いた折れ線を左へ D だけ平行に移す(継ぎ目は留め)。"""
    nrm = []
    for a, b in zip(pts, pts[1:]):
        Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
        nrm.append((-(b[1] - a[1]) / Ln, (b[0] - a[0]) / Ln))
    out = []
    for i, p in enumerate(pts):
        if i == 0:
            n = nrm[0]
            out.append((p[0] + n[0] * D, p[1] + n[1] * D))
        elif i == len(pts) - 1:
            n = nrm[-1]
            out.append((p[0] + n[0] * D, p[1] + n[1] * D))
        else:
            n1, n2 = nrm[i - 1], nrm[i]
            bx, by = n1[0] + n2[0], n1[1] + n2[1]
            bl = math.hypot(bx, by) or 1e-9
            c = max(0.2, (bx * n1[0] + by * n1[1]) / bl)
            out.append((p[0] + bx / bl * D / c, p[1] + by / bl * D / c))
    return out


def tw_rel(line, u, v, reach):
    """点と土留めの線の関係: (距離[間], 側 +1=上(線の左)/-1=下, 線の内か, 線の頭からの道のり[間])。
    reach[間] より遠い・線の端の外は (None…)。"""
    bb = line["_bb"]
    if u < bb[0] - reach or u > bb[2] + reach or v < bb[1] - reach or v > bb[3] + reach:
        return None
    P = line["pts"]
    dd, i, t, q = _tw_near(P, u, v, closed=False)
    if dd > reach:
        return None
    last = len(P) - 2
    if (i == 0 and t <= 1e-6) or (i == last and t >= 1 - 1e-6):
        if dd > 1e-6:
            return None                                   # 線の端の外 ── 壁は効かない(法は端へ呑ませる)
    a, b = P[i], P[i + 1]
    if t <= 1e-6 and i > 0:
        a0 = P[i - 1]
        n1 = (-(a[1] - a0[1]), a[0] - a0[0])
        n2 = (-(b[1] - a[1]), b[0] - a[0])
        nx, ny = n1[0] / (math.hypot(*n1) or 1) + n2[0] / (math.hypot(*n2) or 1), n1[1] / (math.hypot(*n1) or 1) + n2[1] / (math.hypot(*n2) or 1)
    elif t >= 1 - 1e-6 and i < last:
        c = P[i + 2]
        n1 = (-(b[1] - a[1]), b[0] - a[0])
        n2 = (-(c[1] - b[1]), c[0] - b[0])
        nx, ny = n1[0] / (math.hypot(*n1) or 1) + n2[0] / (math.hypot(*n2) or 1), n1[1] / (math.hypot(*n1) or 1) + n2[1] / (math.hypot(*n2) or 1)
    else:
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
    side = 1 if (u - q[0]) * nx + (v - q[1]) * ny >= 0 else -1
    s = line["_cum"][i] + t * (line["_cum"][i + 1] - line["_cum"][i])
    return dd, side, True, s


def tw_top_at(line, s):
    """線の頭からの道のり s[間] での天端(頂点ごとの `tops` を内挿。無ければ `top`)。"""
    ts = line.get("tops")
    if not ts:
        return line.get("top")
    C = line["_cum"]
    for i in range(len(C) - 1):
        if C[i] - 1e-9 <= s <= C[i + 1] + 1e-9:
            if ts[i] is None or ts[i + 1] is None:
                return ts[i] if ts[i] is not None else ts[i + 1]
            # 段違いの run(sode)は内挿しない ── 区間の天端は区間の頭の値
            if line.get("mode") == "sode":
                return ts[i]
            f = (s - C[i]) / ((C[i + 1] - C[i]) or 1.0)
            return ts[i] + (ts[i + 1] - ts[i]) * f
    return ts[-1]


def tw_prep(line):
    P = line["pts"]
    line["_bb"] = (min(p[0] for p in P), min(p[1] for p in P), max(p[0] for p in P), max(p[1] for p in P))
    C = [0.0]
    for a, b in zip(P, P[1:]):
        C.append(C[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    line["_cum"] = C
    return line


def _tw_edge_refs(s):
    """「辺12〜15」「辺24・辺28北端・辺26〜27」→ [(辺番号, 端の限定 or None)]。"""
    out = []
    for a, b, q in re.findall(r"辺(\d+)(?:〜(\d+))?(北端|南端|東端|西端)?", s or ""):
        for e in range(int(a), int(b or a) + 1):
            out.append((e, q or None))
    return out


def _tw_num(s, pat, default=None):
    m = re.search(pat, str(s or ""))
    return float(m.group(1)) if m else default


def tw_resolve(d, parcel_uv, nat, in_parcel):
    """関係で書いた `terraceWalls` を線に解く。`d` は生成器が lib へ渡す写し(段は `poly` を持つ)。

    戻り (lines, bad, polys)。lines は uv[間]の折れ線(上の側が左)と型・天端の行、bad は (名, 理由)、
    polys は**形を変えた面**の新しい輪 {面の名: [(u,v)...]}(下の面を壁の足元まで延ばす・上の面を内へ引く)。
    ⛔ `d` の指図の欄は書き換えない(呼び手が自分の写しへ polys を当てる)。"""
    K = d["const"]["ken"]
    c = d["const"]
    T = dict((t["name"], t) for t in d["terraces"])
    JA = {}
    for pl in d.get("planes") or []:
        for tn in pl.get("terraces") or []:
            JA[pl["name"]] = tn
    polys = dict((nm, _tw_ccw(t["poly"])) for nm, t in T.items() if t.get("poly"))
    PU = _tw_ccw(parcel_uv)
    nP = len(PU)
    rev = _tw_area([tuple(q) for q in parcel_uv]) < 0      # 区画の辺番号は元の並びで数える
    runs_on = {}
    for r in d.get("runs") or []:
        runs_on.setdefault(r.get("edge"), []).append(r)

    def edge_pts(e):
        """区画の辺 e の両端(反時計回りの輪での向き)。"""
        a, b = parcel_uv[e], parcel_uv[(e + 1) % len(parcel_uv)]
        return ((tuple(b), tuple(a)) if rev else (tuple(a), tuple(b)))

    def tname(tok):
        h = tok.split()[0] if tok.split() else tok
        if h in T:
            return h
        return JA.get(h)

    def gy(dd, u, v):
        return graded_y(dd, u, v, nat(u, v), in_parcel)

    lines, bad = [], []
    ws = tw_relational(d)
    # 面↔面を先に解く(下の面を延ばす)→ 袖はその延びた面の縁で解く
    order = sorted(ws, key=lambda w: 0 if all(tname(str(x)) for x in w["between"]) and not any(
        ("法尻" in str(x) or "法(" in str(x)) for x in w["between"]) else 1)
    for w in order:
        nm = w["name"]
        bt = [str(x) for x in w["between"]]
        tn = [tname(x) for x in bt]
        txt = " ".join(bt)
        hard = w.get("hard")
        base = {"name": nm, "kind": w.get("kind"), "cert": w.get("cert"), "hard": hard}
        if "法(" in txt and "の端" in txt:
            # ---------------- sode
            m = re.search(r"法\(([^)↔]+)↔([^)]+)\)", txt)
            X, Y = (JA.get(m.group(1).strip()) or m.group(1).strip(), JA.get(m.group(2).strip()) or m.group(2).strip()) if m else (None, None)
            lo = next((t for t in tn if t), None)
            if not m or X not in polys or Y not in polys or lo is None:
                bad.append((nm, "「法(X↔Y)の端」の X・Y か相手の面が面の名簿に無い: %s" % txt))
                continue
            tops = sorted(set(float(x) for x in re.findall(r"\d+\.\d+", str(w.get("top")))), reverse=True)
            stop = _tw_num(w.get("stop"), r"([\d.]+)", 0.6)
            if not tops:
                bad.append((nm, "段違いの天端の値が読めない: %r" % w.get("top")))
                continue
            dd = dict(d)
            dd["terraces"] = [t for t in d["terraces"] if t["name"] != lo]
            ylo = T[lo]["y"]
            P = polys[lo]
            st = _tw_stations(P)
            keep, ret = [], []
            others = [n9 for n9 in polys if n9 != lo]
            for (e, t0, t1, p, n) in st:
                q = (p[0] + n[0] * 0.3, p[1] + n[1] * 0.3)
                if not in_parcel(d, q[0], q[1]) or any(_pt_in_ring(polys[o], q[0], q[1]) for o in others):
                    keep.append(False); ret.append(None); continue
                cx = _tw_near(polys[X], q[0], q[1])[3]
                cy = _tw_near(polys[Y], q[0], q[1])[3]
                ax, ay = cx[0] - q[0], cx[1] - q[1]
                bx, by = cy[0] - q[0], cy[1] - q[1]
                cosg = (ax * bx + ay * by) / ((math.hypot(ax, ay) * math.hypot(bx, by)) or 1e-9)
                if cosg > -0.5:                             # q が X と Y の間(なす角 120° 超)に無い
                    keep.append(False); ret.append(None); continue
                g = gy(dd, q[0], q[1])
                ok = g is not None and g - ylo >= stop
                keep.append(ok)
                ret.append(g)
            parts = _tw_runs(P, st, keep)
            if not parts:
                bad.append((nm, "%s の縁で X↔Y の法に面し落差 %.1fm 以上の所が無い" % (lo, stop)))
                continue
            for pts in parts:
                pts = pts[::-1]                              # 上(法の側)を左へ
                # 刻みごとの天端 = 外(法の側)の地盤以上の最小の段 ⇒ 同じ天端の連なりが一本の run(各 run 一直線)
                V, TV = [], []
                for a9, b9 in zip(pts, pts[1:]):
                    Ln = math.hypot(b9[0] - a9[0], b9[1] - a9[1]) or 1e-9
                    n9 = ((b9[1] - a9[1]) / Ln, -(b9[0] - a9[0]) / Ln)       # 右 = 下の面(lo)の外 … 上の側は左
                    n9 = (-n9[0], -n9[1])
                    k = max(1, int(math.ceil(Ln / TW_STEP_KEN)))
                    for j in range(k):
                        f0, f1 = j / float(k), (j + 1) / float(k)
                        fm = (f0 + f1) / 2
                        pm = (a9[0] + (b9[0] - a9[0]) * fm, a9[1] + (b9[1] - a9[1]) * fm)
                        g = gy(dd, pm[0] + n9[0] * 0.3, pm[1] + n9[1] * 0.3)
                        tp = min([x for x in tops if x >= (g or 0) - 1e-6] or [tops[0]])
                        p0 = (a9[0] + (b9[0] - a9[0]) * f0, a9[1] + (b9[1] - a9[1]) * f0)
                        if not V or (j == 0) or TV[-1] != tp:
                            if V and math.hypot(V[-1][0] - p0[0], V[-1][1] - p0[1]) < 1e-9:
                                TV[-1] = tp
                            else:
                                V.append(p0)
                                TV.append(tp)
                V.append(pts[-1])
                TV.append(TV[-1])
                # 同じ天端で一直線に並ぶ頂点は畳む
                V2, T2 = [V[0]], [TV[0]]
                for i in range(1, len(V) - 1):
                    a9, b9, c9 = V2[-1], V[i], V[i + 1]
                    col = abs((b9[0] - a9[0]) * (c9[1] - a9[1]) - (b9[1] - a9[1]) * (c9[0] - a9[0])) < 1e-6
                    if col and TV[i] == T2[-1]:
                        continue
                    V2.append(V[i])
                    T2.append(TV[i])
                V2.append(V[-1])
                T2.append(T2[-1])
                lines.append(tw_prep(dict(base, mode="sode", hi=None, lo=lo, pts=V2, tops=T2,
                                          top=None, stop=stop, steps=tops)))
            continue
        if any("法尻" in x for x in bt):
            # ---------------- toe(法尻の土留め): 当家の囲いの内面の線
            hi = next((t for t in tn if t), None)
            other = next((x for x, t in zip(bt, tn) if not t), "")
            refs = _tw_edge_refs(other)
            if hi is None or not refs:
                bad.append((nm, "法尻の面か辺が読めない: %s" % txt))
                continue
            hspec = re.findall(r"[\d.]+", str(w.get("h")))
            hmin, hmax = (float(hspec[0]), float(hspec[-1])) if hspec else (None, None)
            # 辺ごとの内面までの距離[m](当家の run の型から)
            chains, cur = [], None
            for e, qual in sorted(refs):
                rs = runs_on.get(e) or []
                kinds = set(r.get("kind") for r in rs)
                if not rs:
                    bad.append((nm + "(辺%d)" % e, "辺%d に当家の囲い(runs)が無く、法尻の線の位置(内面からの距離)が書かれていない" % e))
                    cur = None
                    continue
                if "Nagaya" in kinds:
                    Dm = c.get("inubashiri", 0.3) + c.get("nagayaD", 4.35)
                else:
                    Dm = c.get("inubashiri", 0.3) + c.get("dobeiT", 1.15)
                if cur and cur["edges"][-1] == e - 1 and abs(cur["D"] - Dm) < 1e-6 and not qual and not cur["qual"]:
                    cur["edges"].append(e)
                else:
                    cur = {"edges": [e], "D": Dm, "qual": qual}
                    chains.append(cur)
            for ch in chains:
                es = ch["edges"]
                pts = [edge_pts(es[0])[0]] + [edge_pts(e)[1] for e in es] if not rev else None
                if rev:
                    pts = [edge_pts(es[-1])[0]] + [edge_pts(e)[1] for e in reversed(es)]
                off = _tw_offset_chain(pts, ch["D"] / K)
                # 法尻の要否: 上の面の盛の法が線の上でまだ地形より高いか
                Q = polys[hi]
                bf = c.get("batterFill", 1.5)

                def need(p):
                    dm = _tw_near(Q, p[0], p[1])[0] * K
                    qn = _tw_near(Q, p[0], p[1])[3]
                    yq = gy(d, qn[0] + (qn[0] - p[0]) * 0.02, qn[1] + (qn[1] - p[1]) * 0.02)
                    if yq is None:
                        yq = T[hi]["y"]
                    g0 = _tw_seat_at(parcel_uv, runs_on, es, p, K)       # 足元 = 囲いの座(辺の内側の造成後の地盤)
                    if g0 is None:
                        g0 = nat(p[0], p[1])
                    return (yq - dm / bf) - (g0 if g0 is not None else -1e9), yq - dm / bf
                # 端の限定(北端など)は、その端から法がまだ届かない所まで
                dense = []
                for a, b in zip(off, off[1:]):
                    Ln = math.hypot(b[0] - a[0], b[1] - a[1])
                    k = max(1, int(math.ceil(Ln / TW_STEP_KEN)))
                    for j in range(k + (1 if (a, b) == (off[-2], off[-1]) else 0)):
                        f = j / float(k)
                        dense.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                if ch["qual"]:
                    ax = {"北端": (1, 0), "南端": (-1, 0), "西端": (0, 1), "東端": (0, -1)}[ch["qual"]]
                    flip = dense[0][0] * ax[0] + dense[0][1] * ax[1] < dense[-1][0] * ax[0] + dense[-1][1] * ax[1]
                    if flip:
                        dense = dense[::-1]
                    # その端に最も近い「法がまだ届かない」連なり(角の 1 点が届いていても端の連なりとみる ── 辺の前半まで探す)
                    k0 = next((i for i in range(len(dense) // 2) if need(dense[i])[0] > 0.0), None)
                    k = k0 if k0 is not None else 0
                    while k0 is not None and k < len(dense) and need(dense[k])[0] > 0.0:
                        k += 1
                    dense = dense[(k0 or 0):] if k0 is not None else dense
                    k = k - (k0 or 0)
                    if k < 2:
                        bad.append((nm + "(辺%d%s)" % (es[0], ch["qual"]),
                                    "%s の端から盛の法が線の手前で着地する(法尻の土留めが要る所が無い)" % ch["qual"]))
                        continue
                    dense = dense[:k]
                    if flip:                                 # 上(面の側)が左になる向き(区画の内向き)へ戻す
                        dense = dense[::-1]
                    off = _tw_simplify(dense)
                tv = []
                for p in off:
                    ex_, _ = need(p)
                    g0 = _tw_seat_at(parcel_uv, runs_on, es, p, K)
                    if g0 is None:
                        g0 = nat(p[0], p[1])
                    if hmin is None:
                        h = max(0.0, ex_)
                    elif hmin == hmax:
                        h = hmin
                    else:
                        h = min(hmax, max(hmin, ex_))
                    tv.append(round((g0 if g0 is not None else 0.0) + h, 3))
                lines.append(tw_prep(dict(base, mode="toe", hi=hi, lo=None, pts=off, tops=tv, top=None,
                                          part="辺" + "〜".join(str(x) for x in ([es[0], es[-1]] if len(es) > 1 else es))
                                               + (ch["qual"] or ""),
                                          offsetM=round(ch["D"], 3), hSpec=[hmin, hmax],
                                          _P=parcel_uv, _runs=runs_on, _es=list(es),
                                          loFrom="囲いの座(辺の runs[].seat0→seat1)")))
            continue
        if sum(1 for t in tn if t) == 2:
            # ---------------- fill(面↔面)
            a9, b9 = tn
            hi, lo = (a9, b9) if T[a9]["y"] >= T[b9]["y"] else (b9, a9)
            P, Q = polys[hi], polys[lo]
            st = _tw_stations(P)
            keep, hits = [], []
            for (e, t0, t1, p, n) in st:
                o = (p[0] - n[0] * 0.02, p[1] - n[1] * 0.02)
                h = _tw_ray(o, n, Q, TW_RAY_KEN + 0.02)
                keep.append(h is not None)
                hits.append(None if h is None else (max(0.0, h - 0.02), (o[0] + n[0] * h, o[1] + n[1] * h)))
            parts = _tw_runs(P, st, keep)
            if not parts:
                bad.append((nm, "%s の縁から %.0f間 以内に %s が無い(向かい合っていない)" % (hi, TW_RAY_KEN, lo)))
                continue
            # 石段の口でとぎれた同じ本の切れを一本にまたぐ
            parts = _tw_bridge(parts)
            gapmax = max((h[0] for h in hits if h), default=0.0)
            if gapmax > 0.05 and len(parts) == 1:
                kept = [i for i in range(len(st)) if keep[i]]

                def hit_near(p):
                    i = min(kept, key=lambda j: math.hypot(st[j][3][0] - p[0], st[j][3][1] - p[1]))
                    return hits[i][1]
                newQ = _tw_extend(Q, hit_near(parts[0][0]), hit_near(parts[0][-1]), parts[0])
                if newQ:
                    polys[lo] = newQ
            top = w.get("top") if isinstance(w.get("top"), (int, float)) else T[hi]["y"]
            sh = _tw_num(w.get("note"), r"肩\s*([\d.]+)\s*間", 0.0)
            for pts in parts:
                lines.append(tw_prep(dict(base, mode="fill", hi=hi, lo=lo, pts=pts, top=float(top), tops=None,
                                          shoulderKen=sh, gapKen=round(gapmax, 3))))
            continue
        hi = next((t for t in tn if t), None)
        other = next((x for x, t in zip(bt, tn) if not t), "")
        refs = _tw_edge_refs(other)
        if hi is not None and refs and "の背" in other:
            # ---------------- back(長屋の背から n 間)
            es = sorted(e for e, _ in refs)
            fk = _tw_num(w.get("face"), r"背から\s*([\d.]+)\s*間")
            if fk is None or any((es[i + 1] - es[i]) != 1 for i in range(len(es) - 1)):
                bad.append((nm, "長屋の背からの間数(face)が読めないか辺が連なっていない: %r" % w.get("face")))
                continue
            Dm = c.get("inubashiri", 0.3) + c.get("nagayaD", 4.35) + fk * K
            chain = [edge_pts(es[0])[0]] + [edge_pts(e)[1] for e in es] if not rev else \
                    [edge_pts(es[-1])[0]] + [edge_pts(e)[1] for e in reversed(es)]
            D = Dm / K
            P = polys[hi]
            dense = []
            for i in range(len(P)):
                a, b = P[i], P[(i + 1) % len(P)]
                Ln = math.hypot(b[0] - a[0], b[1] - a[1])
                k = max(1, int(math.ceil(Ln / 0.2)))
                for j in range(k):
                    f = j / float(k)
                    dense.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            pushed, moved = [], []
            for p in dense:
                dd9, i9, t9, q9 = _tw_near(chain, p[0], p[1], closed=False)
                if dd9 < D - 1e-6 and 1e-6 < t9 + i9 < len(chain) - 1 - 1e-6:
                    dx, dy = p[0] - q9[0], p[1] - q9[1]
                    Ln = math.hypot(dx, dy) or 1e-9
                    pushed.append((q9[0] + dx / Ln * D, q9[1] + dy / Ln * D))
                    moved.append(True)
                    p_m = (D - dd9) * K
                    moved[-1] = p_m
                else:
                    pushed.append(p)
                    moved.append(False)
            if not any(m is not False for m in moved):
                bad.append((nm, "%s の縁はどこも長屋の背から %.1f間 の線より外 ── 引く所が無い" % (hi, fk)))
                continue
            # 押した連なり = 壁の線(面の輪の向き = 上の面が左)
            keep = [m is not False for m in moved]
            n = len(dense)
            s0 = next(i for i in range(n) if keep[i] and not keep[i - 1]) if not all(keep) else 0
            seq = []
            for k9 in range(n):
                i = (s0 + k9) % n
                if keep[i]:
                    seq.append(i)
                else:
                    break
            line = _tw_simplify([pushed[i] for i in seq], 0.02)
            polys[hi] = _tw_simplify_ring(pushed)
            mv = [m for m in moved if m is not False]
            lines.append(tw_prep(dict(base, mode="back", hi=hi, lo=None, pts=line, top=float(w.get("top") or T[hi]["y"]),
                                      tops=None, offsetM=round(Dm, 3), movedM=[round(min(mv), 2), round(max(mv), 2)],
                                      _P=parcel_uv, _runs=runs_on, _es=list(es),
                                      loFrom="長屋の座(辺%s の runs[].seat)" % "〜".join(str(x) for x in (es[0], es[-1])))))
            continue
        if hi is not None and refs and "切り" in other:
            # ---------------- cut(面の縁に立ち、辺へ向かう切りの法を受ける)
            es = set(e for e, _ in refs)
            P = polys[hi]
            st = _tw_stations(P)
            keep = []
            for (e, t0, t1, p, n) in st:
                h = _tw_ray(p, n, PU, 8.0)
                if h is None:
                    keep.append(False); continue
                q = (p[0] + n[0] * h, p[1] + n[1] * h)
                ei = _tw_near(PU, q[0], q[1])[1]
                eo = (nP - 1 - ei - 1) % nP if rev else ei
                # 受ける切りがある所だけ ── 外の地形が天端に届かない所では壁が両側に立ってしまう
                g0 = nat(p[0] + n[0] * 0.5, p[1] + n[1] * 0.5)
                keep.append(eo in es and g0 is not None and isinstance(w.get("top"), (int, float)) and g0 >= w["top"])
            parts = _tw_runs(P, st, keep)
            if not parts:
                bad.append((nm, "%s の縁で辺%s へ向かう所が無い" % (hi, sorted(es))))
                continue
            above = _tw_num(w.get("above"), r"1\s*:\s*([\d.]+)", c.get("batterCut", 1.0))
            top = w.get("top")
            if not isinstance(top, (int, float)):
                bad.append((nm, "切りの法の土留めの天端が数でない: %r" % top))
                continue
            for pts in _tw_bridge(parts):
                lines.append(tw_prep(dict(base, mode="cut", hi=None, lo=hi, pts=pts[::-1], top=float(top), tops=None,
                                          above=above)))
            continue
        rp = next((r for r in (d.get("ramps") or []) if r.get("name") in bt), None)
        hi = next((t for t in tn if t), None)
        if rp is not None and hi is not None:
            # ---------------- ramp(面 ↔ 坂: 面の盛りの中に坂の幅だけ盛り残した溝の両脇の石垣・EDO-0502 第102巡)
            #   線 = 坂の芯 ± 幅/2(坂の縁)。始まり = 線が面(hi)の輪郭を出る所(口)・終わり = 天端 − 坂の縦断 < 積み止めの落差(ends)。
            #   天端 = 「口の側 Y1 … (約 Lm)から先は Y2」の段違い(sode と同じく区間の頭の値)。どちらの脇かは文が名指す棟から測る
            #   (「<棟の名> の … から n間」)── 名指しが無い本は同じ坂のもう一本の反対の脇。⛔ 読めなければ線を作らない。
            got = _tw_ramp_side(d, w, rp, polys[hi], T, ws, K)
            if isinstance(got, str):
                bad.append((nm, got))
            else:
                lines.append(tw_prep(dict(base, mode="sode", hi=hi, lo=None, ramp=rp["name"], **got)))
            continue
        bad.append((nm, "between の形が読めない: %s" % txt))
    return lines, bad, polys


def _tw_ramp_side(d, w, rp, P, T, ws, K, side=None):
    """`_tw_resolve` の ramp の枝。戻り {pts, tops, top, stop, steps, sideV} か 理由の文。"""
    C = [tuple(q[:2]) for q in rp.get("pts") or []]
    if len(C) != 2 or not rp.get("w") or not isinstance(rp.get("profY"), list) or len(rp["profY"]) != 2:
        return "坂 %s の芯(2点)・幅 w・縦断 profY(2値)が無い" % rp.get("name")
    (a, b) = C
    L0 = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
    ax = ((b[0] - a[0]) / L0, (b[1] - a[1]) / L0)
    nrm = (-ax[1], ax[0])
    half = float(rp["w"]) / K / 2.0
    y0, y1 = float(rp["profY"][0]), float(rp["profY"][1])
    top_s = str(w.get("top") or "")
    m1 = re.search(r"口の側\s*([\d.]+)", top_s)
    m2 = re.search(r"約\s*([\d.]+)\s*m\s*\)\s*から先は\s*([\d.]+)", top_s)
    m3 = re.search(r"落差\s*([\d.]+)\s*未満", str(w.get("ends") or ""))
    if not (m1 and m2 and m3):
        return "坂の脇の石垣の天端(口の側 Y・約 Lm から先は Y)か積み止めの落差(ends)が読めない"
    yA, sStep, yB, stop = float(m1.group(1)), float(m2.group(1)), float(m2.group(2)), float(m3.group(1))

    def side_of(wall):
        txt = _json.dumps(wall, ensure_ascii=False)
        for s in (d.get("service") or []) + (d.get("munes") or []):
            lab = s.get("label")
            if lab and lab + " の" in txt and all(k in s for k in ("u0", "v0", "u1", "v1")):
                cu, cv = (s["u0"] + s["u1"]) / 2.0, (s["v0"] + s["v1"]) / 2.0
                return 1 if (cu - a[0]) * nrm[0] + (cv - a[1]) * nrm[1] > 0 else -1
        return None
    sg = side_of(w)
    if sg is None:
        mates = [x for x in ws if x is not w and rp["name"] in [str(y) for y in x.get("between") or []]]
        sm = [side_of(x) for x in mates]
        sm = [x for x in sm if x is not None]
        if len(sm) != 1:
            return "坂 %s のどちらの脇か名指しが無い(相方の名指しも無い)" % rp["name"]
        sg = -sm[0]
    off = (nrm[0] * half * sg, nrm[1] * half * sg)
    o = (a[0] + off[0], a[1] + off[1])
    # 口 = 線が面の輪郭を横切る所(坂の足の側の外から坂の向きへ射る)── 足の点が輪郭の外なら芯の向き、内なら逆向き
    inside = _pt_in_ring(P, o[0], o[1])
    t0 = None
    if inside:
        h = _tw_ray(o, (-ax[0], -ax[1]), P, 4.0)
        t0 = None if h is None else -h
    else:
        h = _tw_ray(o, ax, P, 4.0)
        t0 = h
    if t0 is None:
        return "坂 %s の脇の線が面の輪郭と交わらない(口が無い)" % rp["name"]
    grade = (y1 - y0) / (L0 * K)
    tEnd = (yB - stop - y0) / grade / K if grade > 1e-6 else L0
    tEnd = min(tEnd, L0)
    tS = t0 + sStep / K
    if not (t0 < tS < tEnd):
        return "段違いの継ぎ目 %.1fm が口と積み止めの間に無い" % sStep
    pt = lambda t: (o[0] + ax[0] * t, o[1] + ax[1] * t)
    pts, tops = [pt(t0), pt(tS), pt(tEnd)], [yA, yB, yB]
    # 上(面の側)を左へ: 進む向き ax の左は +nrm ── 外(sg)が左でなければ向きを返す
    if sg < 0:
        # sode の天端は区間の頭の値 ⇒ 逆向きでは [積み止め→継ぎ目 = Y2, 継ぎ目→口 = Y1, 終わり]
        pts, tops = [pts[2], pts[1], pts[0]], [yB, yA, yA]
    return {"pts": pts, "tops": tops, "top": None, "stop": stop, "steps": [yA, yB], "sideV": sg}


def _tw_nearest_edge(P, es, p):
    """区画の辺 es(元の番号)のうち p に最も近い辺と距離[間]。"""
    best = (None, 1e18)
    for e in es:
        a, b = P[e], P[(e + 1) % len(P)]
        dd = _tw_near([tuple(a), tuple(b)], p[0], p[1], closed=False)[0]
        if dd < best[1]:
            best = (e, dd)
    return best


def _tw_seat_at(P, runs_on, es, p, K):
    """辺 es の囲い(runs)の座を、p に最も近い辺の上の位置で引く(seat0→seat1 を道のりで内挿)。無ければ None。"""
    e, _ = _tw_nearest_edge(P, es, p)
    if e is None:
        return None
    a, b = P[e], P[(e + 1) % len(P)]
    _, _, t, _ = _tw_near([tuple(a), tuple(b)], p[0], p[1], closed=False)
    sm = t * math.hypot(b[0] - a[0], b[1] - a[1]) * K
    rs = [r for r in runs_on.get(e) or [] if r.get("seat") is not None]
    if not rs:
        return None
    r = min(rs, key=lambda r: 0.0 if r.get("s0", 0) - 1e-6 <= sm <= r.get("s1", 0) + 1e-6
            else min(abs(sm - r.get("s0", 0)), abs(sm - r.get("s1", 0))))
    s0, s1 = r.get("s0", 0.0), r.get("s1", 0.0)
    y0 = r.get("seat0") if r.get("seat0") is not None else r["seat"]
    y1 = r.get("seat1") if r.get("seat1") is not None else r["seat"]
    f = 0.0 if s1 - s0 < 1e-9 else max(0.0, min(1.0, (sm - s0) / (s1 - s0)))
    return float(y0) + (float(y1) - float(y0)) * f


def _tw_simplify_ring(P, tol=0.01):
    if len(P) < 4:
        return list(P)
    k = max(range(len(P)), key=lambda i: math.hypot(P[i][0] - P[0][0], P[i][1] - P[0][1]))
    a = _tw_simplify(P[:k + 1], tol)
    b = _tw_simplify(P[k:] + [P[0]], tol)
    return a[:-1] + b[:-1]


def _tw_bridge(parts):
    """同じ本の切れ(石段・坂の口)を TW_BRIDGE_KEN 以内ならまたいで一本にする。"""
    parts = [list(p) for p in parts]
    merged = True
    while merged and len(parts) > 1:
        merged = False
        for i in range(len(parts)):
            for j in range(len(parts)):
                if i == j:
                    continue
                a, b = parts[i][-1], parts[j][0]
                if math.hypot(a[0] - b[0], a[1] - b[1]) <= TW_BRIDGE_KEN:
                    parts[i] = parts[i] + parts[j]
                    del parts[j]
                    merged = True
                    break
            if merged:
                break
    return parts


def _tw_extend(Q, h_first, h_last, line):
    """下の面 Q(反時計回り)を、上の面の縁の線 `line`(上の面の輪の向き)まで延ばした輪。
    h_first / h_last は line の頭 / 尻の刻みから下の面に当たった点。⚠ 一続きの向かい合いだけを扱う。"""
    n = len(Q)

    def par(p):
        _, i, t, _ = _tw_near(Q, p[0], p[1])
        return i + t
    pa, pb = par(h_first), par(h_last)
    # 上の縁の順(頭→尻)は下の輪では時計回り ⇒ 下の輪を h_first から反時計回りに h_last まで(向かい合わない側)
    arc = [tuple(h_first)]
    k = int(math.floor(pa)) + 1
    span = (pb - pa) % n
    while ((k - pa) % n) < span - 1e-9:
        arc.append(Q[k % n])
        k += 1
    arc.append(tuple(h_last))
    newQ = arc + [tuple(p) for p in reversed(line)]
    if _tw_area(newQ) <= _tw_area(Q) + 1e-6:
        return None
    return newQ


def tw_measure(d, lines, nat, in_parcel, step_m=0.5):
    """解いた線ぶんの天端と高さを、**壁を入れた造成後の地盤**で測る(呼び手は `d["_twLines"]` を入れてから呼ぶ)。
    行に h=[min,max]・hiDev(上の側の地盤 − 天端 の最悪)・lenM を足す。"""
    K = d["const"]["ken"]
    for ln in lines:
        P = ln["pts"]
        hs, dev = [], []
        tot = ln["_cum"][-1]
        n = max(2, int(tot * K / step_m))
        eps = min(0.05, tot / 4.0)                         # 線の端そのものは測らない(端の外は壁が効かない側)
        for k in range(n + 1):
            s = eps + (tot - 2 * eps) * k / float(n)
            C = ln["_cum"]
            i = max(0, min(len(P) - 2, next((j for j in range(len(C) - 1) if C[j + 1] >= s - 1e-9), len(C) - 2)))
            f = (s - C[i]) / ((C[i + 1] - C[i]) or 1.0)
            a, b = P[i], P[i + 1]
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
            nl = (-(b[1] - a[1]) / Ln, (b[0] - a[0]) / Ln)
            off = 0.1
            lo_p = (p[0] - nl[0] * off, p[1] - nl[1] * off)
            hi_p = (p[0] + nl[0] * off, p[1] + nl[1] * off)
            if not (in_parcel(d, *lo_p) and in_parcel(d, *hi_p)):
                continue
            ylo = graded_y(d, lo_p[0], lo_p[1], nat(*lo_p), in_parcel)
            yhi = graded_y(d, hi_p[0], hi_p[1], nat(*hi_p), in_parcel)
            top = tw_top_at(ln, s)
            if ylo is None or top is None:
                continue
            hs.append(top - ylo)
            if yhi is not None:
                dev.append(yhi - top)
        ln["h"] = [round(min(hs), 2), round(max(hs), 2)] if hs else None
        ln["hiDev"] = [round(min(dev), 2), round(max(dev), 2)] if dev else None
        ln["lenM"] = round(tot * K, 1)
    return lines


def tw_effect_pre(d, tw, u, v):
    """壁の肩の摺り付け(`shoulderKen`): 上の面の中で線から肩の幅までは天端へ寄せる。
    長屋の背の土留め(back)の下の側は、長屋の座(その辺の run の `seat`)まで(長屋の背から壁の足元まで平ら)。
    該当しなければ None。"""
    for ln in tw:
        if ln["mode"] in ("back", "toe") and ln.get("_es"):
            Dk = ln["offsetM"] / d["const"]["ken"]
            r = tw_rel(ln, u, v, Dk + 0.5)
            if r is not None and r[1] < 0:
                e_, dd_ = _tw_nearest_edge(ln["_P"], ln["_es"], (u, v))
                if dd_ <= Dk + 1e-6:
                    sv = _tw_seat_at(ln["_P"], ln["_runs"], ln["_es"], (u, v), d["const"]["ken"])
                    if sv is not None:
                        return sv                          # 壁の足元から囲いまで = 囲いの座
    for ln in tw:
        sh = ln.get("shoulderKen") or 0.0
        if sh <= 0 or not ln.get("hi"):
            continue
        r = tw_rel(ln, u, v, sh)
        if r is None or r[1] < 0:
            continue
        t = next((x for x in d["terraces"] if x["name"] == ln["hi"]), None)
        if t is None or not t_contains(t, u, v):
            continue
        plane = ramp_y(d, u, v)
        if plane is None:
            plane = t["y"]
        top = tw_top_at(ln, r[3])
        return top + (plane - top) * min(1.0, r[0] / sh)
    return None


def tw_fill_rule(tw, tname, u, v, reach, y2):
    """盛の法(面 tname から)に対する壁の効き: None = 法を出さない / 数 = 法の高さ(法尻の段で持ち上げた値)。"""
    for ln in tw:
        if ln.get("hi") != tname or ln["mode"] not in ("fill", "back", "toe"):
            continue
        r = tw_rel(ln, u, v, reach)
        if r is None:
            continue
        if r[1] < 0:
            return None                                    # 壁より下の側 ── 壁が受ける
        if ln["mode"] == "toe":
            top = tw_top_at(ln, r[3])
            if top is not None:
                y2 = max(y2, top)                          # 法は壁の天端へ着く
    return y2


def tw_cut_rule(tw, tname, u, v, reach, K):
    """切りの法(面 tname から)に対する壁の効き: (法を出すか, 代わりの上限 or None)。"""
    for ln in tw:
        if ln.get("lo") != tname or ln["mode"] not in ("cut", "sode"):
            continue
        r = tw_rel(ln, u, v, reach)
        if r is None or r[1] < 0:
            continue
        if ln.get("above"):
            return False, tw_top_at(ln, r[3]) + r[0] * K / ln["above"]
        return False, None
    return True, None


# ================================================================ 庭の算出物の共有の手(EDO-0502・EDO-0407)
#   ⭐ 岡部の器(`impl_okabe.bake_gardens`)が使う。⚠ 他の邸の器はまだ呼ばない ── 足しても他邸の焼きは変わらない。

def seeded_rnd(key):
    """**名から決まる乱数**(`random.Random`)。⛔ 時刻や連番で振らない ── 同じ指図からは同じ石の並びが出る。"""
    import random
    return random.Random(int(_hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:16], 16))


def polyline_len(P):
    """折れ線の長さ(点の単位のまま)。"""
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(P, P[1:]))


def ring_seg(ring, i_from, i_to):
    """閉じた輪 `ring`(頂点の列・閉じ点なし)の **1 始まりの番号** `i_from` から `i_to` まで(進む向き・輪を回る)の
    頂点の列。指図の汀線の符牒 `#3→#4→#5` を点の列へ解く。"""
    n = len(ring)
    a, b = (i_from - 1) % n, (i_to - 1) % n
    out = [tuple(ring[a])]
    k = a
    while k != b:
        k = (k + 1) % n
        out.append(tuple(ring[k]))
    return out


def parse_ring_seg(seg):
    """汀線の区間の符牒 `#19→#20→#1→#2→#3` / `#8→…→#16` を (始め, 終わり) の番号へ。読めなければ None。"""
    ns = [int(x) for x in re.findall(r"#(\d+)", str(seg))]
    return (ns[0], ns[-1]) if len(ns) >= 2 else None


def stones_along(P, pmin, pmax, rnd):
    """折れ線 `P` に沿って、芯々 `pmin`〜`pmax`(P の単位)の**不等ピッチ**で石の芯を置く。両端を含む。
    ⛔ 等間隔にしない(飛石・沢飛石の作法)。"""
    if len(P) < 2:
        return [tuple(q) for q in P]
    Ltot = polyline_len(P)
    out, s = [tuple(P[0])], 0.0
    while True:
        s += rnd.uniform(pmin, pmax)
        if s > Ltot - pmin * 0.5:
            break
        out.append(point_at(P, s))
    if math.hypot(out[-1][0] - P[-1][0], out[-1][1] - P[-1][1]) > pmin * 0.5:
        out.append(tuple(P[-1]))
    return out


def point_at(P, s):
    """折れ線 `P` の頭から道のり `s` の点。"""
    acc = 0.0
    for a, b in zip(P, P[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + L >= s and L > 1e-12:
            t = (s - acc) / L
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        acc += L
    return tuple(P[-1])


def split_polyline(P, mark):
    """`[点, 点, "橋", 点, …]` のように**符牒の語で切れた折れ線**を、点だけの折れ線の列へ割る。"""
    out, cur = [], []
    for q in P:
        if isinstance(q, str):
            if q == mark or mark is None:
                if len(cur) >= 2:
                    out.append(cur)
                cur = []
            continue
        cur.append((float(q[0]), float(q[1])))
    if len(cur) >= 2:
        out.append(cur)
    return out


# ================================================================ 庭の造成(築山の削り残し・池の掘りの見込み)── EDO-0502・EDO-0407
#   ⭐ 欄 `gardens[].hosoku.zosei`(庭方の設計)を持つ庭だけに効く。⚠ 持たない邸の graded は1点も変わらない。
#   池の本当の掘りは WaterBaker(migiwa.pts・深さ)が正 ── ここは**見込みの断面**(土量と据えの高さの目安)。

def _niwa_seg_d(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
    return math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dz * t), t


def _ring_d(p, R):
    """閉じた輪 R への距離(R の単位)と最寄りの辺の番号(0 始まり = 頂点 i→i+1)。"""
    best, bi = 1e18, 0
    for i in range(len(R)):
        dd, _ = _niwa_seg_d(p, R[i], R[(i + 1) % len(R)])
        if dd < best:
            best, bi = dd, i
    return best, bi


def _line_d2(p, P):
    best, bs, acc = 1e18, 0.0, 0.0
    for a, b in zip(P, P[1:]):
        dd, t = _niwa_seg_d(p, a, b)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if dd < best:
            best, bs = dd, acc + t * L
        acc += L
    return best, bs, acc


def _grade_val(s):
    m = re.search(r"1\s*:\s*([\d.]+)", str(s or ""))
    return float(m.group(1)) if m else None


def niwa_setup(d):
    """庭の造成の材料を一度だけ組む(d['_niwaZ'] に覚える)。無ければ []。"""
    if "_niwaZ" in d:
        return d["_niwaZ"]
    out = []
    K = d["const"]["ken"]
    tks = dict((t.get("name"), t) for t in d.get("tsukiyama") or [] if isinstance(t, dict))
    for g in d.get("gardens") or []:
        z = ((g.get("hosoku") or {}).get("zosei")) if isinstance(g, dict) else None
        if not z or not g.get("poly"):
            continue
        gp = [tuple(q) for q in g["poly"]]
        mounds = []
        for key, f in z.items():
            m = re.match(r"tsukiyama\[(.+)\]\.form", key)
            if not m or m.group(1) not in tks:
                continue
            t = tks[m.group(1)]
            sk = [tuple(q) for q in t.get("skirt") or []]
            if len(sk) < 3:
                continue
            mounds.append({"name": m.group(1), "skirt": sk, "peak": (t["u"], t["v"]), "top": float(f["topY"]),
                           "flat": float(f.get("topFlatR_m") or 0.0) / K, "foot": float(f["skirtY"]),
                           "grade": _grade_val(f.get("maxGrade"))})
        mg = g.get("migiwa") or {}
        ring = [tuple(q) for q in mg.get("pts") or []]
        hori = z.get("gardens[%s].hori" % g["name"]) or {}
        types = [None] * len(ring)
        for gg in g.get("gogan") or []:
            se = parse_ring_seg(gg.get("seg"))
            if se is None or not ring:
                continue
            n9, a9 = len(ring), (se[0] - 1) % len(ring)
            while a9 != (se[1] - 1) % n9:                             # 辺 a→a+1 の型(番号は1始まり)
                types[a9] = str(gg.get("type") or "")
                a9 = (a9 + 1) % n9
        isl = [([tuple(q) for q in nk.get("outline") or []], float(nk.get("topY") or 0), float(nk.get("rTop_m") or 0) / K)
               for nk in g.get("nakajima") or [] if len(nk.get("outline") or []) >= 3 and nk.get("falloff") == "cos"]
        shelf = []
        m = re.search(r"([\d.]+)\s*径\s*([\d.]+)", str((hori.get("danmen") or {}).get("岩島") or ""))
        if m:
            for iw in g.get("iwajima") or []:
                if iw.get("uv"):
                    shelf.append((tuple(iw["uv"]), float(m.group(1)), float(m.group(2)) / 2.0 / K))
        ym = ((g.get("mizu") or {}).get("inflow") or {})
        yb = z.get("yarimizu.bank") or {}
        mb = re.search(r"幅\s*([\d.]+)\s*m.*?\+\s*([\d.]+).*?肩\s*([\d.]+)\s*→\s*([\d.]+)", str(yb.get("value") or ""))
        yar = None
        if len(ym.get("yarimizu") or []) >= 2 and isinstance(ym.get("bedY"), list):
            yar = {"pts": [tuple(q) for q in ym["yarimizu"]], "bed": [float(x) for x in ym["bedY"]],
                   "half": float(ym.get("width_m") or 0.0) / 2.0 / K,
                   "bankW": (float(mb.group(1)) / K) if mb else 0.0,
                   "sh0": float(mb.group(3)) if mb else None, "sh1": float(mb.group(4)) if mb else None}
        dm = hori.get("danmen") or {}
        out.append({"name": g["name"], "poly": gp, "K": K,
                    "mounds": mounds, "ring": ring, "types": types, "waterY": float(hori.get("waterY") or mg.get("waterY")),
                    "floor": float(hori.get("floorY") or mg.get("floorY")), "bank": float(hori.get("bank") or 0.0),
                    "danmen": dm, "isl": isl, "shelf": shelf, "yar": yar})
    d["_niwaZ"] = out
    return out


def _danmen(z, typ, dm):
    """汀から水の側へ dm[m] の池の底の見込み(`hori.danmen` の型ごと)。"""
    w, fl = z["waterY"], z["floor"]
    t = str(typ or "")
    if t.startswith("州浜"):
        y = w - min(dm, 1.2) / 8.0                     # 水中 1.2m を 1:8
        if dm > 1.2:
            y -= (dm - 1.2) / 3.0                      # 以遠 1:3
    elif t.startswith("石組"):
        y = 20.2 if dm <= 0.6 else 20.2 - (dm - 0.6) / 2.0       # 根石の棚 20.2 幅0.6・以遠 1:2
    elif t.startswith("乱杭"):
        y = 20.1 - dm / 2.0                            # 杭の面で 20.1・以遠 1:2
    else:
        y = fl
    return max(fl, y)


def niwa_y(d, u, v, base, nat):
    """庭の造成(築山・池の見込み・遣水の野筋)の高さ。効かない点は None。"""
    for z in niwa_setup(d):
        if not _pip((u, v), z["poly"]):
            continue
        K = z["K"]
        y = base
        p = (u, v)
        # 築山(削り残し)── cos の断面・頂の平場・勾配の上限・地山を超えない
        for mo in z["mounds"]:
            if not _pip(p, mo["skirt"]):
                continue
            ds, _ = _ring_d(p, mo["skirt"])
            dp = max(0.0, math.hypot(u - mo["peak"][0], v - mo["peak"][1]) - mo["flat"])
            t = 1.0 if ds + dp <= 1e-9 else ds / (ds + dp)
            ym = mo["foot"] + (mo["top"] - mo["foot"]) * (1.0 - math.cos(math.pi * t)) / 2.0
            if mo["grade"]:
                ym = min(ym, mo["foot"] + ds * K / mo["grade"])
            if nat is not None:
                ym = min(ym, nat)
            y = max(y, ym)
        # 池(汀の輪の内)と州浜の陸の側
        R = z["ring"]
        if len(R) >= 3:
            dr, ei = _ring_d(p, R)
            dm = dr * K
            typ = z["types"][ei]
            if _pip(p, R):
                y = _danmen(z, typ, dm)
                for sp, sy, sr in z["shelf"]:
                    if math.hypot(u - sp[0], v - sp[1]) <= sr:
                        y = max(y, sy)
                for ol, top, rt in z["isl"]:
                    if _pip(p, ol):
                        di, _ = _ring_d(p, ol)
                        c = (sum(q[0] for q in ol) / len(ol), sum(q[1] for q in ol) / len(ol))
                        dc = max(0.0, math.hypot(u - c[0], v - c[1]) - rt)
                        t = 1.0 if di + dc <= 1e-9 else di / (di + dc)
                        y = max(y, z["waterY"] + (top - z["waterY"]) * (1.0 - math.cos(math.pi * t)) / 2.0)
                return y
            if str(typ or "").startswith("州浜") and dm < 1.5:
                y = min(y, z["waterY"] + (z["bank"] - z["waterY"]) * dm / 1.5)     # 陸 1.5m を 1:5
        # 遣水(溝の底と両岸の野筋)
        ya = z["yar"]
        if ya:
            dl, s, tot = _line_d2(p, ya["pts"])
            if dl <= ya["half"]:
                y = ya["bed"][0] + (ya["bed"][1] - ya["bed"][0]) * (s / tot if tot > 0 else 0.0)
            elif ya["sh0"] is not None and dl <= ya["half"] + ya["bankW"] and 0.0 < s < tot:
                y = max(y, ya["sh0"] + (ya["sh1"] - ya["sh0"]) * (dl - ya["half"]) / ya["bankW"])
        return y
    return None
