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
import collections
import hashlib

import sashizu_lib
from sashizu_lib import (R, _pat, _SVN, Proj, RGrid, cf_color, cutfill_legend,
                         dem_color, _iso, dem_legend, slope_table, links_table,
                         _edge_dir, mune_contacts_table,  # バイト同一を実証済みの共通部
                         obb_pts, in_obb, obb_overlap, overlap_check)  # 検査の正典(2026-08-26 統一)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "doi_sashizu.json")
MD = os.path.join(DOC, "doi_kosho.md")
OUT = os.path.join(DOC, "doi_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown(岡部と同じ最小変換)
SRC_MD = os.path.expanduser(
    "~/.claude/skills/unity-buke-yashiki/references/sources.md")
# 上屋敷が備える役割の**最小の一覧**。⚠ 各邸の json だけを見ていると、役割と棟を
# **同時に消せば検査が通る**(2026-08-25 検図14巡 中-6)。外の錨として共有台帳を読む。
TYPES_MD = os.path.expanduser(
    "~/.claude/skills/unity-buke-yashiki/references/estate-types.md")


def _unmeasured(fn, what):
    """⛔ **地盤が読めないときに 0 件を返さない。**

    `qa-and-pitfalls.md`「測れないものは 0 件になる」。地形を引く検査が `return []` で
    素通りすると、**合格と区別が付かない**(2026-08-26 松平の指摘 ⑩ の地形版)。
    「回っていない」と明示して非0で返す。
    """
    return ["⛔ %s が %s を読めない — **この検査は回っていない**(合格ではない)" % (fn, what)]


class AnchorMissing(Exception):
    """**外の錨が読めない。** ⛔ 空を返して素通りさせない。

    `qa-and-pitfalls.md`「測れないものは 0 件になる」がここに効く。錨を読みに行って読めなかった
    ときに空集合を返すと、**連鎖を自邸の外へ出した意味がまるごと消える**
    (2026-08-26 松平の指摘。当家は `estate_zone_norm` が `set()` を返しており、
    台帳を隠すと⑤が丸ごと素通りして「表役所と玄関が同じ区画」が**完全に隠れた**)。
    """


def estate_zone_norm():
    """`estate-types.md` の「**別の区画に属す役割**」行 → 役割名の集合。

    ⚠ 台帳の**存在**しか錨にしないと、「区画を減らす」道が残る(2026-08-26 松平:
    zones から区画を消し・棟を別区画へ移し・裁定も辻褄を合わせれば、当家では**距離だけ**が
    拾っていた=幾何が偶々効いただけ)。**台帳の役割の名前から要求を組み立てる**と、
    自邸の json をどう書き換えても**台帳から役割を落とさない限り要求が消えない**。
    落とすほうは `program_check` が塞ぐので、そこで連鎖が止まる。
    """
    if not os.path.exists(TYPES_MD):
        raise AnchorMissing("共有台帳 `estate-types.md` が読めない(%s)" % TYPES_MD)
    t = open(TYPES_MD, encoding="utf-8").read()
    m = re.search(r"\*\*別の区画に属す役割\*\*\s*[::]\s*(.+)", t)
    if not m:
        raise AnchorMissing("共有台帳に「別の区画に属す役割」の行が無い")
    out = set(x.strip() for x in m.group(1).split("/") if x.strip())
    if len(out) < 4:
        raise AnchorMissing("「別の区画に属す役割」が %d 個しか読めない — 行が壊れている"
                            % len(out))
    return out


def estate_program_norm():
    """`estate-types.md` の「上屋敷が備える役割」表 → {役割: 要否}。"""
    if not os.path.exists(TYPES_MD):
        raise AnchorMissing("共有台帳 `estate-types.md` が読めない(%s)" % TYPES_MD)
    t = open(TYPES_MD, encoding="utf-8").read()
    # ⚠ **要否の欄は自然文で書かれる**(「上屋敷は必須」「奥向があれば必須」「必須(室として)」)。
    #   かつて `(必須[^|]*|望ましい|任意)` で**先頭一致**を要求しており、
    #   **「上屋敷は必須」= 表長屋 と「奥向があれば必須」= 御錠口 の2行を行ごと読み飛ばして**いた
    #   (2026-08-26。22行のうち20行しか見ておらず、床10行も素通り)。
    #   ⇒ **欄をそのまま取り、分類できない欄は黙って落とさず止める。**
    sec = t.split("上屋敷が備える役割")[-1].split("### 建蔽率")[0]
    out = {}
    unknown = []
    for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", sec, re.M):
        role, need = m.group(1).strip(), m.group(2).strip()
        if role in ("役割", "---") or set(role) <= set("-: "):
            continue
        if "必須" in need or "望ましい" in need or "任意" in need:
            out[role] = need
        else:
            unknown.append("%s=%s" % (role, need))
    if unknown:
        raise AnchorMissing("「上屋敷が備える役割」表に要否を判じられない行がある: %s"
                            % " / ".join(unknown[:4]))
    if len(out) < 20:
        raise AnchorMissing("「上屋敷が備える役割」表が %d 行しか読めない — 表が壊れている"
                            % len(out))
    return out


def sources_index():
    """`sources.md` の登録 ID → 確度。見出し(### [ID] 確度X)と表の行(| [ID] |)の両方。"""
    if not os.path.exists(SRC_MD):
        return {}, set()
    t = open(SRC_MD, encoding="utf-8").read()
    # ⚠ **見出しの書式は一様でない。**`### [ID] 確度A` のほかに
    #   `### [水道歴史館 樋線図 永田町] ①K0136=確度B / ②K0105=確度A` のように
    #   **一つの項が複数の確度を持つ**書き方があり、`\s*確度([SABPU?])` では拾えず
    #   **台帳に在る ID が「台帳に無い」と出ていた**(2026-09-04 考証方 中-5 で発覚)。
    #   ⇒ 見出し行を丸ごと読み、確度が2つ以上ならその文言をそのまま値にする。
    # ⚠ **同じ ID の見出しが複数ある**(`### [安政地震被害書上](続き — …) 確度A` のような
    #   続きの項)。⛔ 後勝ちにすると本項の確度が続きの項に上書きされる(S → A)。**先勝ち**にする。
    head = {}
    for m in re.finditer(r"^### \[([^\]]+)\](.*)$", t, re.M):
        tail = m.group(2)
        qs = re.findall(r"確度\s*([SABPU?])", tail)
        if not qs:
            continue                       # 確度を持たない見出しは台帳のエントリではない
        head.setdefault(m.group(1), tail.strip() if len(qs) > 1 else qs[0])
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
    _margins = []                      # ⭐ run ごとの余裕(2026-09-06 検図方 中8)
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
                px, pz = x + nx_ * _PROBE(d) * sg, z + nz_ * _PROBE(d) * sg
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
            if worst is not None:
                # 余裕 = 相手の据え付け面 − 当家の地盤(＋=空き)。⛔ 埋没の有無に関わらず記録する
                _margins.append((who, r["name"], -worst[0], worst[2], worst[2] - worst[0]))
            if worst is None or worst[0] <= 0.05:
                continue
            n += 1
            kind = ("盛土 +%.2fm" % (worst[2] - worst[3])) if worst[2] - worst[3] > 0.05 else "素地"
            rows.append("| %s `%s`(相手の s=%.1f) | **%.2fm** | %.2f(%s) |"
                        % (who, r["name"], worst[1], worst[0], worst[2], kind))
    if n == 0:
        # ⭐⭐ **0件でも run ごとの余裕を刷る**(2026-09-06 検図方 中8)。
        #   ⚠ 岡部 `N_Hei3b` の余裕は **0.075m** しかなく、閾値 0.05 まで **0.025m**。
        #   ⛔ 「埋まる箇所は無い」だけだと、**誰かが `Kachu_Y` の面を 0.1m 上げれば
        #   黙って隣家に食い込む**。⭕ 薄い所が見えていれば止められる。
        rows = ["| 隣家の run | 余裕(＋=空き) | 当家の地盤 | 相手の据え付け面 |",
                "|---|---|---|---|"]
        worst = None
        for who, nm9, mg9, g9, s9 in sorted(_margins, key=lambda q: q[2]):
            rows.append("| %s `%s` | **%+.3f m** | %.2f | %.2f |" % (who, nm9, mg9, g9, s9))
            if worst is None or mg9 < worst[1]:
                worst = (nm9, mg9)
        rows.append("")
        rows.append("⭕ **埋まる箇所は無い**(判定は 0.05m 超)。"
                    "⚠⚠ **いちばん薄いのは `%s` の %+.3fm** で、閾値まで **%.3fm** しかない。"
                    "⛔ **この run の側で当家の面を上げない** — 上げれば黙って隣家に食い込む。"
                    "測り方は境界から**当家側へ 0.3m**、`doi_dem.json` を**双一次**で引く。"
                    % (worst[0], worst[1], worst[1] - 0.05) if worst else "")
        return "\n".join(rows)
    rows.append("")
    rows.append("測り方: 境界から**土井側へ 0.3m**(塀の足元)、`doi_dem.json` を**双一次**で引く。"
                "天端は **run の中**で `seat0→seat1` を按分(相手の生成器の `rseat` が正典)。"
                "判定は 0.05m 超。**是正は隣家側**(据え付け面を当家の地盤より下げない)。")
    return "\n".join(rows)


# markdown の正典は sashizu_lib(2026-08-26 統一。既定=厳しい側がそのまま当邸の方言)。
inline = sashizu_lib.inline


def md2html(text):
    return sashizu_lib.md2html(text)


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
    (2026-08-23 ユーザー指摘で是正 — 敷地図と御殿平面の左右が逆だった)。
    結果、この図版は敷地図(北が上)を反時計回りに 90° 回した向き = **上が東(表門の道)/
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
sashizu_lib.MUNE_JA = MUNE_JA  # lib の mune_contacts_table が引く棟名辞書を差す
TERR_JA = {
    "MaeNiwaApron": "前庭の白洲(石段前)","UmayaKaku": "厩の郭", "MonzenE": "門前面(門口)", "Yakusho": "表役所の郭",
           "MonzenN": "門内北", "MaeNiwa": "前庭",
           "KitaSumi": "米蔵の郭", "NagayaKitaDai": "表長屋(北2)の基壇", "Naka": "中段",
           "GenkanKaku": "玄関の郭", "ShoinKaku": "書院の郭", "Shu": "主面",
           "ShuMain": "主面", "ShuKita": "主面(北)", "ShuMae": "主面(南舌)", "ShuMinami": "主面(南)",
           "KachuN1": "家中長屋(北一)", "KachuN2": "家中長屋(北二)", "KachuN3": "家中長屋(北三)",
           "KachuS1": "家中長屋(南一)", "KachuS2": "家中長屋(南二)", "KachuY": "家中長屋(表)"}


# ---------------------------------------------------------------- 敷地
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


# ---------------------------------------------------------------- 御殿平面(グリッド座標)
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
        w = next((x for x in d["terraceWalls"] if x["name"] == k["atWall"]), None)
        if w is None:
            continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
        if w["a"][0] == w["b"][0]:
            cu, cv = w["a"][0], k["gapV"]
            g.append(pr.rect(cu - 0.9, cv - k["w"] / 2 / 1.818, cu + 0.9, cv + k["w"] / 2 / 1.818,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        else:
            cu, cv = k["gapU"], w["a"][1]
            g.append(pr.rect(cu - k["w"] / 2 / 1.818, cv - 0.9, cu + k["w"] / 2 / 1.818, cv + 0.9,
                             fill="var(--shu-lo)", stroke="var(--shu)", sw=1.0))
        g.append(T(pr.X(cu), pr.Y(cv) - 8, "%s %d段" % (k["name"], k["steps"]), "anS2", "middle"))
        # ⚠ **側石垣を描く。** 3石段×左右2枚=31.5m の石垣が、平面にも断面にも部材表にも
        #   出ていなかった(2026-08-25 検図14巡 中-2)。白洲の中に 2.8m の石垣が立つ姿が
        #   どの図にも無いのは、ユーザーが図を見て最初に気づく類の欠落である。
        fl = k.get("flank")
        if fl:
            hw_ = k["w"] / 2 / 1.818
            rn_ = fl["run"] / 1.818
            tw_ = 2.4 * fl["s"] / 1.818          # 石垣の底厚(間)
            if w["a"][0] == w["b"][0]:           # 縦壁 — 走りは −u 方向
                for sgn in (-1.0, 1.0):
                    b0 = cv + sgn * hw_
                    b1 = b0 + sgn * tw_
                    g.append(pr.rect(cu - rn_, min(b0, b1), cu, max(b0, b1),
                                     fill=_pat(), stroke="var(--ishi)", sw=0.8))
            else:                                # 横壁 — 走りは −v 方向
                for sgn in (-1.0, 1.0):
                    b0 = cu + sgn * hw_
                    b1 = b0 + sgn * tw_
                    g.append(pr.rect(min(b0, b1), cv - rn_, max(b0, b1), cv,
                                     fill=_pat(), stroke="var(--ishi)", sw=0.8))
    for rp in d.get("ramps", []):                       # 土の斜路(馬・荷車の通り道)
        if "u0" in rp:                                  # 踏み代を矩形で持つ(壁に沿う斜路)
            g.append(pr.rect(rp["u0"], rp["v0"], rp["u1"], rp["v1"],
                             fill="var(--michi)", stroke="var(--shu)", sw=1.0, op=0.45))
            cu, cv = (rp["u0"] + rp["u1"]) / 2.0, (rp["v0"] + rp["v1"]) / 2.0
        else:
            w = next((x for x in d["terraceWalls"] if x["name"] == rp["atWall"]), None)
            if w is None:
                continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
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
            # ⛔ 入側の幅を直書きしない — `const.moyaBand.irikawa` が正典(規則4)
            mu0, mv0, mu1, mv1 = moya_rect(d, m)
        g.append(pr.rect(mu0, mv0, mu1, mv1, fill="var(--ink-mid)", stroke="var(--ink)", sw=1.6))
        # ⭐ **身舎の帯 — 大棟(朱の破線)と谷(太い実線)**(2026-09-06 ユーザー裁定=案C)。
        #   ⛔ 設計値を入れて図に描かない、をしない(規則19)。⚠ 向きが未決の棟(正方形)は
        #   位置が出ないので何も描かない — 表と差し戻しの一覧に ⚠ で出る。
        _bd = (m.get("roof") or {}).get("bands") or {}
        _tn = (m.get("roof") or {}).get("tani") or {}
        for _c in (_bd.get("at") or []):
            if _bd.get("along") == "u":
                g.append(LN(pr.X(mu0), pr.Y(_c), pr.X(mu1), pr.Y(_c), "var(--shu)", 1.4, dash="8 4"))
            elif _bd.get("along") == "v":
                g.append(LN(pr.X(_c), pr.Y(mv0), pr.X(_c), pr.Y(mv1), "var(--shu)", 1.4, dash="8 4"))
        for _c in (_tn.get("at") or []):
            if _tn.get("dir") == "u":
                g.append(LN(pr.X(mu0), pr.Y(_c), pr.X(mu1), pr.Y(_c), "var(--take)", 2.4))
            elif _tn.get("dir") == "v":
                g.append(LN(pr.X(_c), pr.Y(mv0), pr.X(_c), pr.Y(mv1), "var(--take)", 2.4))
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
               "**上=東(三べ坂前身の南北道)／左=北／下=西／右=南** — 敷地図(北が上)を反時計回りに90°回した向き",
               "anS"))
    g.append(T(4, pr.H - 5, note, "anS2", "start"))
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


def _PROBE(d):
    """境界から当家側へ測点を退げる距離(m)。**定数を読む** —
    3箇所でベタ書きしており、定数を変えると黙って取り残された(2026-08-25 検図10巡 低-2)。"""
    return d["const"].get("neighbourProbe", 0.3)


def dem_bilinear(dem, x, z):
    """世界座標2m格子の DEM を**双一次**で引く。

    ⚠ **造成前の地盤は `docs/Sashizu/base_dem.json` が正本**(CLAUDE.md 規則12)。
    Unity の live terrain から採ると、採った時刻までに誰かが流した造成が乗る。
    2026-08-24、当方の旧 `doi_dem.json` は松平区画の 574セル(最大 +6.91m)に
    松平の造成を写しており、2m格子の双一次が境界から 0.3m の点で向こう側のセルを混ぜて、
    当家側の「自然地盤」を 2.5m 押し上げていた(松平の指摘で発覚)。
    一時、区画内のセルだけに平面を当てる回避を入れたが、**正本へ差し替わって不要になった**
    (正本では両家が同じ面を読むのが要件で、素の双一次が正しい。回避は全辺で最大 0.99m ずれ、
    しかも各家が自分の区画でマスクするので**同じ点を両家が別の値で読む**)。

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
    """その (u,v) を覆う段の高さ。正典は sashizu_lib.design_y(poly/yaw/矩形の包含を全部見る)。"""
    return sashizu_lib.design_y(d, u, v, in_parcel)


def run_edges(d):
    """正典は sashizu_lib.run_edges(2026-08-26 造成モデル統一)。"""
    return sashizu_lib.run_edges(d)


def walled_edges(d, t):
    """正典は sashizu_lib.walled_edges(開口で区間を割る版・2026-08-26 統一)。"""
    return sashizu_lib.walled_edges(d, t)


def _walled(we, edge, w):
    """正典は sashizu_lib._walled。"""
    return sashizu_lib._walled(we, edge, w)


def ramp_y(d, u, v):
    """正典は sashizu_lib.ramp_y(土の斜路の踏面)。"""
    return sashizu_lib.ramp_y(d, u, v)


def stair_y(d, u, v):
    """正典は sashizu_lib.stair_y(石段の掘割の踏面)。"""
    return sashizu_lib.stair_y(d, u, v, in_parcel)


def graded_y(d, u, v, nat, walled=None):
    """**造成後の地盤**。正典は sashizu_lib.graded_y —
    一定勾配の法面(盛土 1:batterFill / 切土 1:batterCut)+着地判定+
    斜路・石段の先読み+盛土floor。2026-08-26 のユーザー指示で全生成器を
    この土井式へ統一した(移動時に出力バイト不変を実証)。"""
    return sashizu_lib.graded_y(d, u, v, nat, in_parcel, walled)


def ground_y(d, u, v, nat, walled=None):
    """**図に描く地表** = 造成後の地盤に**奥庭の土工(池床・築山・土手)を重ねた面**。

    ⚠ `graded_y` は郭・法面・石段・斜路しか知らない。庭は別の章で設計されるので、
    断面も切盛も庭の中を**素の面 26.60 の平地**として描いていた
    (2026-09-04 検図方 高-2 / 中-1: 断面⑪⑳ に池も築山も出ず、其四の土量に
    掘削も盛土も入っていなかった)。⭕ **庭の矩形の中では `Niwa.ground()`**、
    外では `graded_y` を返す。⛔ 検査の地盤(`graded_y`)は差し替えない —
    土留め・法面・段の検査は郭の土工だけを見る建て付けで、庭の起伏を混ぜると
    「土留めの要る辺」の判定が庭の築山で狂う。
    ⚠ 庭を持たない邸(`NI(d) is None`)では `graded_y` と完全に同じ。
    """
    n = NI(d)
    if n is not None:
        g = n.g
        if (g["u0"] - 1e-9 <= u <= g["u1"] + 1e-9
                and g["v0"] - 1e-9 <= v <= g["v1"] + 1e-9):
            return n.ground(u, v)
    return graded_y(d, u, v, nat, walled)


def in_niwa(d, u, v):
    """点が奥庭の矩形の中か(庭が無ければ False)。"""
    n = NI(d)
    if n is None:
        return False
    g = n.g
    return (g["u0"] - 1e-9 <= u <= g["u1"] + 1e-9
            and g["v0"] - 1e-9 <= v <= g["v1"] + 1e-9)


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
            dy = ground_y(d, u, v, nat, we)     # ⭕ 奥庭の池床・築山を含む(高-2/中-1)
            dz = dy - nat
            # ⚠ **閾値は塗り分けだけに使い、合計には使わない。**
            #   見出し(閾値あり)と土量表(閾値なし)で合計が食い違っていた
            #   (2026-08-25 検図12巡 高-3)。同じ量が同じ図の中で二つあった。
            a = (st * d["const"]["ken"]) ** 2
            if dz > 0:
                vol_f += dz * a
            else:
                vol_c += -dz * a
            if abs(dz) < 0.05:
                continue                       # 触らない = 素地のまま(下塗りの斜面色)
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


def cutfill_table(d, ter):
    """段ごとの切盛。造成の重さを面ごとに読む。

    ⚠ **全セルを一度だけ走査して分類する。** 段ごとに別々の条件で数えていたため、
    図版の見出し(全セル)と表の合計が食い違っていた(2026-08-25 検図12巡 高-3)。
    分類は `graded_y` が返す面そのもの — 斜路・石段・法面も行にする。
    ⭐ **2026-09-04: 奥庭の土工を行に立てた**(検図方 中-1)。庭の中は `Niwa.ground()` が
    返す面(池床・築山・土手)なので段の高さと一致せず、そのままだと「法面(段の外)」に
    落ちて名前が嘘になる。⛔ 庭を別章(其八)へ逃がさない — **同じ敷地の土は一つの表で足す**。
    """
    st = ter["step"]; a = (st * d["const"]["ken"]) ** 2
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    agg = {}
    order = [t["name"] for t in d["terraces"]] + ["斜路", "石段", "奥庭(池・築山)", "法面(段の外)"]
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * st
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * st
            nat = ter["h"][iv][iu]
            if nat is None or not in_parcel(d, u, v):
                continue
            g = ground_y(d, u, v, nat, we)      # ⭕ 奥庭の池床・築山を含む(高-2/中-1)
            if g is None:
                continue
            if ramp_y(d, u, v) is not None:
                key = "斜路"
            elif stair_y(d, u, v) is not None:
                key = "石段"
            elif in_niwa(d, u, v) and abs(g - graded_y(d, u, v, nat, we)) > 1e-9:
                key = "奥庭(池・築山)"
            else:
                t0 = next((t for t in d["terraces"] if in_obb(t, u, v, 1e-9)
                           and abs(t["y"] - g) < 1e-9), None)
                key = t0["name"] if t0 else "法面(段の外)"
            e = agg.setdefault(key, [0, 0.0, 0.0, 0.0, 0.0])
            dz = g - nat
            e[0] += 1
            if dz > 0:
                e[1] += dz * a; e[2] = max(e[2], dz)
            else:
                e[3] += -dz * a; e[4] = max(e[4], -dz)
    rows = []; tf = tc = 0.0
    for k in order:
        if k not in agg:
            continue
        n, f, mf, c, mc = agg[k]
        tf += f; tc += c
        y = next((t["y"] for t in d["terraces"] if t["name"] == k), None)
        rows.append("<tr><td>%s</td><td>%s</td><td>%.0f 坪</td><td>%.0f m³</td><td>%.1f m</td>"
                    "<td>%.0f m³</td><td>%.1f m</td></tr>"
                    % (TERR_JA.get(k, k), "%.1f" % y if y is not None else "—",
                       n * a / TSUBO, f, mf, c, mc))
    rows.append("<tr><td><b>計</b></td><td></td><td></td><td><b>%.0f m³</b></td><td></td>"
                "<td><b>%.0f m³</b></td><td></td></tr>" % (tf, tc))
    # ⭐ **差引を印字する**(検図方 低-2)。⛔ 符号の向きは**当図で一つ** —
    #   **差引 = 盛土 − 切土 / 正 = 土が足りない(客土)**。其八(奥庭の土量)も同じ向きで刷る。
    rows.append("<tr><td><b>差引(盛土 − 切土)</b></td><td></td><td></td>"
                "<td colspan='4'><b>%+.0f m³</b> — %s</td></tr>"
                % (tf - tc, "客土が要る" if tf - tc > 0 else "土が余る"))
    return ('<div class="tw"><table><thead><tr><th>面</th><th>面の高さ</th><th>面積</th>'
            "<th>盛土</th><th>最大</th><th>切土</th><th>最大</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>"
            "<p class='cap'>⚠ <b>全セルを一度だけ走査して分類している</b> — 段・斜路・石段・"
            "奥庭・法面の合計が図版の見出しと構造的に一致する。"
            "⭐ <b>奥庭の池の掘削と築山の盛土もこの表に入る</b>(其八は同じ土を庭の中だけで"
            "内訳に割ったもので、別勘定ではない)。"
            "⚠ <b>同じ土だが刻みが違うので数字は一致しない</b> — この表は敷地全体を <b>1間格子</b>で、"
            "其八は庭だけを <b>0.1間格子</b>で積む。池の縁と築山の裾は1間では拾いきれないので、"
            "<b>細かい其八のほうが正しい</b>(庭の土量を読むときは其八を見ること)。"
            "⛔ <b>差引の向きは当図で一つ — 盛土 − 切土 / 正=土が足りない。</b></p></div>")


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


def fix_obb_aabb(d):
    """回転物の**外接矩形 `u0..v1` を `uc,vc,L,D,yaw` から算出して正典へ戻す**。

    ⚠ docstring は「`uc,vc,L,D,yaw` が正典で `u0..v1` はその外接矩形」と宣言していたのに、
    **書き戻す関数が無く、往復試験の対象にも入っていなかった**
    (2026-08-25 検図11巡 高-2。第10巡 高-1 で潰した「生成器が消さない出力欄が
    生き延びる」型が、もう一箇所そのまま残っていた)。
    ⛔ **`overlap_check` は総当たりの入口で AABB を関門にしている**ので、AABB が古い(小さい)と
    分離軸の判定に到達せず、**47m² の重なりが 0 件と出る**(実測)。
    """
    for coll in ("terraces", "munes", "service"):
        for o in d.get(coll, []):
            if "yaw" not in o:
                continue
            pts = obb_pts(o)
            o["u0"] = round(min(p[0] for p in pts), 4)
            o["u1"] = round(max(p[0] for p in pts), 4)
            o["v0"] = round(min(p[1] for p in pts), 4)
            o["v1"] = round(max(p[1] for p in pts), 4)
    return d


def fix_edge_profile(d, dem):
    """外周の展開図が使う**辺の地盤線 `edgeProfile` を、正本の DEM から毎回生成する**。

    ⚠ 手書きだったため、`fix_run_s` が DEM から測る露出と**同じ量に二つの出所**があり、
    `SE_Hei_Jog` で **0.77m** 食い違っていた(2026-08-25 検図11巡 中-5:
    展開図はその区間を正典より 0.77m 低い石垣として描いていた)。
    測点は**街路側 1.0m**(基壇の足元)で、`fix_run_s` と同じ取り方。
    """
    if dem is None:
        return d
    P = d["polygon"]
    gr = RGrid(d)
    out = {}
    for e in sorted(set(int(k) for k in d.get("edgeProfile", {}))):
        a, b = P[e], P[(e + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        ex, ez = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx_, nz_ = -ez, ex
        mu, mv = gr.L((a[0] + b[0]) / 2 + nx_ * 3, (a[1] + b[1]) / 2 + nz_ * 3)
        sg = -1.0 if in_parcel(d, mu, mv) else 1.0     # 街路側
        pts = []
        n = max(4, int(L / 2.0))
        for i in range(n + 1):
            sq = L * i / float(n)
            x = a[0] + (b[0] - a[0]) * sq / L
            z = a[1] + (b[1] - a[1]) * sq / L
            h = dem_bilinear(dem, x + nx_ * 1.0 * sg, z + nz_ * 1.0 * sg)
            if h is not None:
                pts.append([round(sq, 2), round(h, 2)])
        if pts:
            out[str(e)] = pts
    if out:
        d["edgeProfile"] = out
    return d


def fix_run_s(d, dem):
    """外周 run の**基壇石垣の丁場 `s`** を、街路側の地盤からの露出で算出して正典へ戻す。

    ⚠ `terraceWalls`(15本)と `boundaryPlinth` は全部 `s` を持ち `wall_check` も掛かるのに、
    **屋敷でいちばん高い石垣(外周 run の基壇・最大 3.35m)だけ無検査**だった
    (2026-08-25 検図10巡 中-6)。図にも表にも部材表にも寸法が無かった。
    """
    if dem is None:
        return d
    P = d["polygon"]
    for r in d["runs"]:
        if r.get("base") != "Ishigaki":
            r.pop("s", None); r.pop("expose", None)
            continue
        e = r["edge"]
        a, b = P[e], P[(e + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        ex, ez = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx_, nz_ = -ez, ex
        gr = RGrid(d)
        mu, mv = gr.L((a[0] + b[0]) / 2 + nx_ * 3, (a[1] + b[1]) / 2 + nz_ * 3)
        sg = -1.0 if in_parcel(d, mu, mv) else 1.0      # 街路側(区画の外)へ出す
        seat = r.get("seat", r.get("seat0"))
        n = max(4, int((r["s1"] - r["s0"]) / 0.5))
        hi = 0.0
        for i in range(n + 1):
            sq = r["s0"] + (r["s1"] - r["s0"]) * i / float(n)
            x = a[0] + (b[0] - a[0]) * sq / L; z = a[1] + (b[1] - a[1]) * sq / L
            g = dem_bilinear(dem, x + nx_ * 1.0 * sg, z + nz_ * 1.0 * sg)
            if g is None:
                continue
            s0v = r.get("seat0", seat); s1v = r.get("seat1", seat)
            t = 0.0 if r["s1"] <= r["s0"] else (sq - r["s0"]) / (r["s1"] - r["s0"])
            hi = max(hi, (s0v + (s1v - s0v) * t) - g)
        r["expose"] = round(max(0.0, hi), 2)
        smax = d["const"].get("plinthSMax", 0.75)
        # ⚠ **丁場の上限を超える露出は段築にする。** 一段で受けようとすると
        #   石垣キットに無い丁場を要求する図になる(2026-08-25 検図10巡 中-6)。
        #   段のあいだには犬走りを取る。
        r["tiers"] = max(1, int(math.ceil(hi / (4.0 * smax) - 1e-9)))
        need = hi / r["tiers"]
        r["s"] = round(min(smax, max(0.20, math.ceil(need / 4.0 / 0.05 - 1e-9) * 0.05)), 2)
    return d


def terrace_overhang_check(d):
    """**段の矩形が区画からはみ出していないか。**

    註は「段は `in_parcel` で切られる」と言うので**実効は無い**が、矩形の宣言としては誤りで、
    地盤を引く検査すべての**標本を黙って減らす**(2026-08-26: 主面 Shu が 16 セル=52.9m²
    はみ出しており、`terrain_provenance_check` を書くまで誰も見ていなかった)。
    ⛔ はみ出しに**物が載っていたら**それは実効のある誤りなので別に出す。
    """
    K = d["const"]["ken"]
    lim = d["const"].get("terraceOverhangMax", 60.0)      # m²
    occ = d["munes"] + d.get("service", []) + d.get("gardens", [])
    bad = []
    for t in d["terraces"]:
        pts = [(iu, iv)
               for iu in range(int(t["u0"]) - 1, int(t["u1"]) + 2)
               for iv in range(int(t["v0"]) - 1, int(t["v1"]) + 2)
               if in_obb(t, iu, iv, 1e-9) and not in_parcel(d, iu, iv)]
        if not pts:
            continue
        a = len(pts) * K * K
        for o in occ:
            for (pu, pv) in pts:
                inside = (in_obb(o, pu, pv, 1e-9) if "yaw" in o else
                          (o["u0"] <= pu <= o["u1"] and o["v0"] <= pv <= o["v1"]))
                if inside:
                    bad.append("⛔ 段 %s の**区画外**に %s が載る(グリッド %d, %d)"
                               % (t["name"], o["name"], pu, pv))
                    break
        if a > lim:
            bad.append("段 %s が区画から %.1f m² はみ出す(上限 %.1f m²)— "
                       "矩形の宣言を区画に合わせること" % (t["name"], a, lim))
    return bad


def terrain_provenance_check(d, base):
    """**回転間格子 `doi_terrain.json` の種地が、地盤の正本から出ているか。**

    司令塔の通達(2026-08-24)は「回転間格子の terrain は各邸の生成器が作る。
    **種地を正本へ揃えるのは各自の手当て**」。⚠ 当家はそれを `_pending` に
    「今すぐの実害は無い」と書いて**測っていなかった** — 宣言のままの手当てだった
    (2026-08-26 松平の指摘)。

    ⛔ これが無いと、**2026-08-23 の live terrain 吸い込み事故が同じ形で再発しても
    誰も気づかない**。当家の図はこの格子の**形と null マスク**しか使っていないが、
    ファイル自身が「種地は正本」と名乗っている以上、名乗りは検めること。
    """
    path = os.path.join(DOC, "doi_terrain.json")
    if base is None or not os.path.exists(path):
        return _unmeasured("terrain_provenance_check", "base_dem.json / doi_terrain.json")
    t = json.load(open(path, encoding="utf-8"))
    gr = RGrid(d)
    lim = d["const"].get("terrainProvenanceTol", 0.30)
    n = 0
    skipped = 0
    worst = 0.0
    spot = None
    over = 0
    hole = 0
    for iv in range(t["nv"]):
        v = t["v0"] + iv * t["step"]
        for iu in range(t["nu"]):
            u = t["u0"] + iu * t["step"]
            h = t["h"][iv][iu]
            if h is None:
                if in_parcel(d, u, v):
                    hole += 1
                continue
            x, z = gr.W(u, v)
            b = dem_bilinear(base, x, z)
            if b is None:
                skipped += 1
                continue
            n += 1
            dd = abs(h - b)
            if dd > worst:
                worst, spot = dd, (u, v)
            if dd > lim:
                over += 1
    bad = []
    # ⛔ **この検査自身が「測れないものを黙って飛ばす」形だった。**
    #   `dem_bilinear` が None を返す点を `continue` していたので、区画が正本の切り出しから
    #   はみ出しても「差が小さい」に化けて見えない(2026-08-26 松平の指摘 ②:
    #   **「測れないものは0件になる」を直すために書いた検査の中に、同じ形があった**)。
    #   ⇒ 余白を先に見て、飛ばした点を数える。
    P = d["polygon"]
    xs = [q[0] for q in P]
    zs = [q[1] for q in P]
    bx1 = base["x0"] + (base["nx"] - 1) * base["step"]
    bz1 = base["z0"] + (base["nz"] - 1) * base["step"]
    for lbl, mgn in (("西", min(xs) - base["x0"]), ("東", bx1 - max(xs)),
                     ("南", min(zs) - base["z0"]), ("北", bz1 - max(zs))):
        if mgn < 0:
            bad.append("区画が正本の切り出しから %s へ %.1fm はみ出している — "
                       "地盤を引けない範囲がある" % (lbl, -mgn))
    if n == 0:
        return _unmeasured("terrain_provenance_check", "重なる格子点")
    if skipped > max(2, n * 0.02):
        bad.append("回転間格子の %d/%d 点(%.1f%%)で正本が引けない — "
                   "照合の標本が黙って減っている" % (skipped, n + skipped,
                                          100.0 * skipped / (n + skipped)))
    if over:
        bad.append("回転間格子の種地が正本から外れる — %d/%d 点が %.2fm 超"
                   "(最大 %.2fm・グリッド %.0f, %.0f)"
                   % (over, n, lim, worst, spot[0], spot[1]))
    if hole:
        bad.append("回転間格子に区画の中の欠測が %d セル — 復元の null マスクが狂う" % hole)
    return bad


def terrain_canon_check(d, ter, dem):
    """**種地が動いていないか**を二段で検める。

    ⛔ 照合先を `doi_edo_world.json` にしたのは誤りだった — `doi_edo_dem` はそれを同じ格子・
    同じ双一次で再標本した**派生物**なので、比較が派生物どうしになり**恒真化**した
    (2026-08-25 検図13巡 高-6: 正本を全セル +2.00m しても全検査が無反応)。
    ① **復元のマスクの外**では復元地盤 = 正本(復元は掘削跡しか触らないので、そこ以外は一致する)
    ② 触った所は仕様の箱の中に収まっているか
    """
    if ter is None or dem is None:
        return []
    try:
        wld = json.load(open(os.path.join(DOC, "doi_edo_world.json"), encoding="utf-8"))
        bx = wld["_reconBox"]          # 復元が**実際に触ったセル**の外接箱(生成器が実測で記録)
    except Exception:
        return ["`doi_edo_world.json` に `_reconBox` が無い — 種地の照合ができない"]
    gr = RGrid(d)
    bad = []
    out_box = 0
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * ter["step"]
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * ter["step"]
            h = ter["h"][iv][iu]
            if h is None:
                continue
            x, z = gr.W(u, v)
            b = dem_bilinear(dem, x, z)
            if b is None:
                continue
            if abs(h - b) <= d["const"].get("terrainCanonTol", 0.15):
                continue
            # 差が出てよいのは復元の箱の中(+平滑化の1環ぶん)だけ
            # 回転格子は世界2m格子から双一次で引くので、箱の外へ1セル分だけ滲む
            if bx[0] - 2.0 <= x <= bx[1] + 2.0 and bx[2] - 2.0 <= z <= bx[3] + 2.0:
                continue
            out_box += 1
            if len(bad) < 6:
                bad.append("復元地盤が正本から %.2fm 外れる(復元の箱の外。グリッド %.0f, %.0f)"
                           % (h - b, u, v))
    if out_box > len(bad):
        bad.append("… ほか %d セル" % (out_box - len(bad)))
    return bad


def fix_sections(d, ter, dem):
    """断面の `natural`(現地形の線)を**地盤から毎回生成する**。

    手で持っていたため、地盤を差し替えても断面だけが古いまま残る型
    (2026-08-25 検図10巡 中-7 と同じ二重管理)。1間刻みで引き直す。
    """
    gr = RGrid(d)
    for sec in d.get("sections", []):
        a0, a1 = int(math.floor(sec["from"])), int(math.ceil(sec["to"]))
        out = []
        for q in range(a0, a1 + 1):
            u, v = (sec["at"], q) if sec["axis"] == "u" else (q, sec["at"])
            # ⚠ **断面の地形線も復元地盤から引く。** dem(正本=現代の地面)を先に引いていたため、
            #   切盛図と棟の表は復元、断面の破線は現代、と**同じ図面の中に地盤モデルが二つ**あった
            #   (2026-08-25 検図13巡 高-4: 1,217点中991点が食い違い、最大1.85m)。
            h = ter["at"](u, v) if ter is not None else None
            if h is None:
                x, z = gr.W(u, v)
                h = dem_bilinear(dem, x, z)
            if h is not None:
                out.append([q, round(h, 2)])
        if out:
            sec["natural"] = out
    return d


def completeness_check(d):
    """**在るべき物が在るか。** 検図12巡の「第三系統」— 物を消しても誰も気づかない、を塞ぐ。

    ⚠ 128物を1個ずつ消す変異試験で **57物(45%)が無反応**だった(2026-08-25 検図12巡 中-6)。
    ここで見るのは `sashizu.md` §3c/§3d が**明文で要求している数**と、
    「段を立てる理由」「廊下の端が棟に接すること」「残る面が庭で覆われること」。
    """
    bad = []
    # ⑦ 動線は4系統(表向・役方・勝手・奥向)
    kinds = set(r.get("kind") for r in d.get("routes", []))
    for k, nm in (("omote", "表向"), ("yaku", "役方"), ("katte", "勝手"), ("oku", "奥向")):
        if k not in kinds:
            bad.append("動線の系統「%s」が無い(§3d は4系統を要求する)" % nm)
    # ⑧ 断面は各軸3本以上・郭ごとに最低1本
    for ax, nm in (("u", "東西"), ("v", "南北")):
        n = len([x for x in d.get("sections", []) if x["axis"] == ax])
        if n < 3:
            bad.append("%s の断面が %d 本(§3c は各軸3本以上)" % (nm, n))
    for t in d["terraces"]:
        cut = any((s["at"] >= t["u0"] - 1e-9 and s["at"] <= t["u1"] + 1e-9) if s["axis"] == "u"
                  else (s["at"] >= t["v0"] - 1e-9 and s["at"] <= t["v1"] + 1e-9)
                  for s in d.get("sections", []))
        if not cut:
            bad.append("段 %s を切る断面が1本も無い" % t["name"])
    # ① 段に載る棟・付属屋・庭が一つも無ければ、その段を立てる理由が無い
    for t in d["terraces"]:
        used = any(all(in_obb(t, u, v, 1e-9) for u, v in obb_pts(m))
                   for m in d["munes"] + d.get("service", []))
        if used:
            continue
        used = any(t["u0"] - 1e-9 <= g["u0"] and g["u1"] <= t["u1"] + 1e-9
                   and t["v0"] - 1e-9 <= g["v0"] and g["v1"] <= t["v1"] + 1e-9
                   for g in d.get("gardens", []))
        if used:
            continue
        # 外周の run(表長屋・練塀の基壇)が載る段も「使われている」
        used = any(t["name"] in (pl.get("terraces") or []) and (pl.get("runs") or [])
                   for pl in d.get("planes", []))
        if not used:
            bad.append("段 %s に載る棟も庭も run も無い — 段を立てる理由が無い" % t["name"])
    # ② 廊下の両端が棟の外形に接すること
    for l in d.get("links", []):
        touch = 0
        for m in d["munes"] + d.get("service", []):
            if "yaw" in m:
                continue
            gu = max(l["u0"], m["u0"]) - min(l["u1"], m["u1"])
            gv = max(l["v0"], m["v0"]) - min(l["v1"], m["v1"])
            if gu <= 0.01 and gv <= 0.01:
                touch += 1
        if touch < 2:
            bad.append("廊下 %s の端が棟に接していない(接する棟 %d)" % (l["name"], touch))
    # ⑥ 儀式の軸は素地の上を通らない(白洲か石段か段の上)
    K = d["const"]["ken"]
    r_om = next((r for r in d.get("routes", []) if r.get("kind") == "omote"), None)
    if r_om:
        bare = 0.0
        for a, b in zip(r_om["pts"], r_om["pts"][1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            n_o = max(2, int(seg / 0.2))
            for i in range(n_o + 1):
                u = a[0] + (b[0] - a[0]) * i / n_o
                v = a[1] + (b[1] - a[1]) * i / n_o
                if not in_parcel(d, u, v):
                    continue
                # ⛔ **`design_y` で免じない。** それは「段の上か」でしかなく、
                #   段は敷地のほぼ全部にある。ここで免じていたので、**庭を全部消しても
                #   0件**だった(2026-08-25 検図13巡・削除の感度試験)。註が言う
                #   「白洲か石段で通す」を字義どおり測る — 通ってよいのは
                #   **石段・白洲(surfaced な庭)・棟の中**だけ。
                if stair_y(d, u, v) is not None:
                    continue
                if any(g["u0"] - 1e-9 <= u <= g["u1"] + 1e-9
                       and g["v0"] - 1e-9 <= v <= g["v1"] + 1e-9
                       for g in d.get("gardens", []) if g.get("kind") == "shirasu"):
                    continue
                if any(in_obb(m, u, v, 1e-9) for m in d["munes"] + d.get("service", [])):
                    continue                      # 棟に入った先は屋内
                # 長屋門の躯体帯(門を潜る区間)も屋内。表門の辺の run と門の躯体を見る
                gp3, sg3 = d["gate"]["plan"], d["gate"]["s"]
                if (-gp3["monW"] / 2 / K <= u <= gp3["monW"] / 2 / K
                        and -1e-9 <= v <= gp3["monD"] / K + 1e-9):
                    continue
                if any((r3["s0"] - sg3) / K <= u <= (r3["s1"] - sg3) / K
                       and -1e-9 <= v <= (d["const"]["nagayaD"] if r3["kind"] == "Nagaya"
                                          else d["const"]["dobeiT"]) / K + 1e-9
                       for r3 in d["runs"] if r3["edge"] == d["gate"]["edge"]):
                    continue
                bare += seg / n_o * K
        if bare > 1.0:
            bad.append("表向の動線が %.1fm にわたり素地の上を通る — 儀式の軸は白洲か石段で通す"
                       % bare)
    # ⑨ 井戸は台所・厩から遠すぎないこと
    lim = d["const"].get("wellReach", 40.0)
    for m in d["munes"] + d.get("service", []):
        if m["name"] not in ("Daidokoro", "Umaya", "Yakusho"):
            continue
        cu = (m["u0"] + m["u1"]) / 2.0 if "yaw" not in m else m["uc"]
        cv = (m["v0"] + m["v1"]) / 2.0 if "yaw" not in m else m["vc"]
        best = min((math.hypot(w["u"] - cu, w["v"] - cv) * K for w in d.get("wells", [])),
                   default=None)
        if best is None:
            bad.append("井戸が一つも無い")
            break
        if best > lim:
            bad.append("%s から最寄りの井戸まで %.0fm(上限 %.0fm)" % (m["name"], best, lim))
    # run が載る段が消えていないか
    for pl in d.get("planes", []):
        if pl.get("y") is None:
            continue                        # 造成しない斜面の run は素地に載る(段は要らない)
        for rn in (pl.get("runs") or []):
            if not any(t["name"] in (pl.get("terraces") or []) for t in d["terraces"]):
                bad.append("外周 %s が載る面「%s」に段が一つも無い" % (rn, pl["name"]))
                break
    # ② 御殿の棟はすべて玄関から廊下でたどれること
    def _touch(o1, o2):
        if "yaw" in o1 or "yaw" in o2:
            return False
        return (max(o1["u0"], o2["u0"]) - min(o1["u1"], o2["u1"]) <= 0.01
                and max(o1["v0"], o2["v0"]) - min(o1["v1"], o2["v1"]) <= 0.01)
    # ⚠ 対象は**連続御殿複合**の棟だけ。表役所と厩は独立して下の段に置く設計で、
    #   外の動線で行き来する(2026-08-25 検図12巡)。印は正典の `goten`。
    nodes = {m["name"]: m for m in d["munes"] if m.get("goten")}
    adj = dict((k, set()) for k in nodes)
    for l in d.get("links", []):
        hit = [k for k, m in nodes.items() if _touch(l, m)]
        for i in range(len(hit)):
            for j in range(i + 1, len(hit)):
                adj[hit[i]].add(hit[j]); adj[hit[j]].add(hit[i])
    for a2, b2 in ((x, y) for x in nodes for y in nodes if x < y):
        if _touch(nodes[a2], nodes[b2]):
            adj[a2].add(b2); adj[b2].add(a2)
    if "Genkan" in nodes:
        seen = {"Genkan"}; stack = ["Genkan"]
        while stack:
            for nx2 in adj[stack.pop()]:
                if nx2 not in seen:
                    seen.add(nx2); stack.append(nx2)
        for k in nodes:
            if k not in seen:
                bad.append("棟 %s へ玄関から廊下でたどれない" % k)
        # ⚠ **客が奥を通って書院へ行けてはならない。** 到達可能なだけでは足りない —
        #   `L_GenkanShoin` を消しても「居間(中奥)経由で書院に着ける」ので無音だった
        #   (2026-08-25 検図14巡・削除の感度試験)。御錠口は表向と奥を分かつ結界であり、
        #   表向の棟は**中奥・奥向を通らずに**玄関から着けること。
        omote = set(d["const"].get("omoteMune", ["Genkan", "Shoin"]))
        inner = set(nodes) - omote
        seen2 = {"Genkan"}; st2 = ["Genkan"]
        while st2:
            for nx3 in adj[st2.pop()]:
                if nx3 in seen2 or nx3 in inner:
                    continue
                seen2.add(nx3); st2.append(nx3)
        for k in omote & set(nodes):
            if k not in seen2:
                bad.append("表向の棟 %s へ、中奥・奥向を通らずに玄関から着けない — "
                           "御錠口の結界が意味を持たない" % k)
    return bad


def _shared_edges(d, who):
    """当家の多角形のうち、`who` の多角形と**実際に重なっている**辺の番号。

    ⛔ 番号で照合しない。`NEIGHBOUR` の辺番号は相手の多角形の番号である。
    当家の辺の両端が相手のどれかの辺の上に載っていれば共有辺と見なす。
    """
    fn_ = NEIGHBOUR.get(who, (None, ()))[0]
    if not fn_:
        return []
    path = os.path.join(DOC, fn_)
    if not os.path.exists(path):
        return []
    Q = json.load(open(path, encoding="utf-8"))["polygon"]
    P = d["polygon"]

    def on_seg(pt, a, b, tol=1.5):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        if L2 < 1e-9:
            return False
        t = ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dz) / L2
        if t < -0.01 or t > 1.01:
            return False
        return math.hypot(a[0] + dx * t - pt[0], a[1] + dz * t - pt[1]) <= tol

    out = []
    for e in range(len(P)):
        a, b = P[e], P[(e + 1) % len(P)]
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        for f in range(len(Q)):
            qa, qb = Q[f], Q[(f + 1) % len(Q)]
            if on_seg(a, qa, qb) and on_seg(b, qa, qb) and on_seg(mid, qa, qb):
                out.append(e)
                break
    return out


def _shared_edge_stats(d, base):
    """共有辺検査の実測。返すのは (rows, missing) —
    rows = [(who, 当家の辺e, 正本との差の最大)] / missing = [(who, ファイル名, 未検査の辺)]。

    ⛔ **復元地盤ファイルが無い相手を `continue` で黙って飛ばさない。**
    2026-08-26 まで `matsudaira_dewa_edo_world.json` が存在せず、当家の辺8・9(松平に面する、
    **一番検査したい辺**)が一度も検査されないまま「指摘 0 件」を名乗っていた。
    採らなかった辺は `missing` として必ず表に出す(沈黙は情報を持たない)。
    ファイルが**在るのに読めない**場合はここでは受けない — `load_terrain` の `json.load` が
    例外で落ちるのが正しい(壊れた正本の上で検査を続けない)。
    """
    P = d["polygon"]
    rows, missing = [], []
    for who, fn_ in (("岡部", "okabe_edo_world.json"), ("松平", "matsudaira_dewa_edo_world.json"),
                     ("土井", "doi_edo_world.json")):
        # ⚠ **共有辺は幾何で決める。** `NEIGHBOUR` が持つ辺番号は**相手の多角形の番号**で、
        #   当家の番号ではない(岡部の辺8・9は当家の辺0・1・2にあたり、当家の辺8・9は
        #   **松平**に面する)。番号をそのまま当家の多角形に当てて2度間違えた
        #   — 1度目は全辺を回して隣家の敷地内の復元を指摘に化けさせ、
        #   2度目は相手の番号を当家の辺として使い、**本当の共有辺を見逃した**
        #   (2026-08-25 検図14巡 中-8)。当家(土井)は自分の全辺を見る。
        edges = list(range(len(P))) if who == "土井" else _shared_edges(d, who)
        if not edges:
            continue                     # 幾何的に接していない相手は検査対象ではない
        path = os.path.join(DOC, fn_)
        if not os.path.exists(path):
            missing.append((who, fn_, edges))
            continue
        w = load_terrain(path)
        for e in edges:
            a, b = P[e], P[(e + 1) % len(P)]
            L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            worst = 0.0
            for i in range(max(4, int(L)) + 1):
                x = a[0] + (b[0] - a[0]) * i / max(4, int(L))
                z = a[1] + (b[1] - a[1]) * i / max(4, int(L))
                bb = dem_bilinear(base, x, z)
                vv = dem_bilinear(w, x, z)
                if bb is not None and vv is not None:
                    worst = max(worst, abs(vv - bb))
            rows.append((who, e, worst))
    return rows, missing


def recon_reach_check(d, margin=None):
    """**当家の復元が区画線に近づいていないか。**

    ⚠ 境界と外周の設計は**正本 `base_dem.json`** から測る(両家が同じ面を読むことが要件)。
    その前提は「当家の復元が境界に届いていない」ことで**たまたま**成り立っている。
    箱を広げた瞬間、`fix_boundary_plinth` は正本を読み続けるので**基壇が黙って追随しなくなる**
    (2026-08-26 岡部の指摘: 当家の基壇の丁場 0.80m は現代の地面では足りるが、
    近代の盛土を戻した面では足りない)。**前提が崩れたらここで止める。**
    """
    path = os.path.join(DOC, "doi_edo_world.json")
    if not os.path.exists(path):
        return _unmeasured("recon_reach_check", "doi_edo_world.json")
    try:
        bx = json.load(open(path, encoding="utf-8"))["_reconBox"]
    except Exception:
        return ["`doi_edo_world.json` に `_reconBox` が無い — 復元の届く先を測れない"]
    lim = margin if margin is not None else d["const"].get("reconEdgeMargin", 5.0)
    P = d["polygon"]
    best, spot = 1e9, None
    for e in range(len(P)):
        a, b = P[e], P[(e + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        for i in range(int(L) + 1):
            t = i / max(1, int(L))
            x, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            dd = math.hypot(max(bx[0] - x, 0, x - bx[1]), max(bx[2] - z, 0, z - bx[3]))
            if dd < best:
                best, spot = dd, (e, x, z)
    if best < lim:
        return ["当家の復元が区画線から %.1fm(辺%d の %.1f, %.1f)まで迫っている — "
                "境界と外周は正本で測る前提が崩れる。基壇の丁場を復元面で測り直すか、"
                "復元を境界から離すかの**裁定が要る**" % (best, spot[0], spot[1], spot[2])]
    return []


def shared_edge_check(d, base):
    """**共有境界の地盤は、どの家も正本のまま読むこと。**

    各家が江戸期の復元を持つと、**同じ境界線を別の面の上で設計する**ことになる
    (2026-08-25 検図13巡 高-7: 岡部の復元が辺1で最大 **0.63m** 動かしていた。
    当家の復元は全辺 0.00m)。司令塔の通達も「隣家との境の地盤は (a) 正本 —
    **両家が同じ面を読むことが要件**」としている。
    """
    if base is None:
        return _unmeasured("shared_edge_check", "base_dem.json")
    rows, missing = _shared_edge_stats(d, base)
    bad = []
    for who, fn_, edges in missing:
        bad.append("⛔ %s の復元地盤 %s が無い — 当家の共有辺%s が**未検査のまま**になる。"
                   "生成器(Tools/Sashizu/build_*_edo_dem.py)を回してから当図を組み直すこと"
                   % (who, fn_, "・".join(str(e) for e in edges)))
    for who, e, worst in rows:
        if worst > 0.05:
            bad.append("%s の復元が共有辺%d の地盤を正本から %.2fm 動かしている — "
                       "**境界は両家が正本を読む**" % (who, e, worst))
    return bad


def shared_edge_html(d, base):
    """共有辺検査の**合否と数値**を図に出す。0件でも沈黙しない —
    何を測って合格したのかまで載せる(採らなかった辺は ⛔ で出す)。"""
    if base is None:
        return "⛔ 正本 <code>base_dem.json</code> が無い — 共有辺検査が走っていない。"
    rows, missing = _shared_edge_stats(d, base)
    parts = []
    for who, e, worst in rows:
        parts.append("%s×辺%d <b>%.2fm</b>%s"
                     % (who if who != "土井" else "当家の復元", e, worst,
                        " ✔" if worst <= 0.05 else " ⛔"))
    for who, fn_, edges in missing:
        parts.append("⛔ <b>%s の復元地盤 <code>%s</code> が無く、共有辺%s は未検査</b>"
                     % (who, fn_, "・".join(str(e) for e in edges)))
    return ("<b>共有辺の地盤検査</b>(各復元地盤と正本の差の最大。0.05m 超と未検査が不適合。"
            "当家の全辺は自家の復元に対して検る): " + " / ".join(parts) + "。")


def ramp_check(d):
    """土の斜路の勾配。**馬と乗物が上がれる勾配か。**

    ⚠ 勾配を 1:7.4 → 1:1.1 に書き換えても**どの検査も反応しなかった**
    (2026-08-25 検図11巡 中-1)。設計意図の数値に検査が無かった。
    """
    K = d["const"]["ken"]
    lim = d["const"].get("rampGradeMax", 1.0 / 6.0)
    bad = []
    for r in d.get("ramps", []):
        run = r.get("run")
        drop = r.get("drop")
        if not run or not drop:
            continue
        g = drop / run
        if g > lim + 1e-9:
            bad.append("斜路 %s の勾配 1:%.1f が上限 1:%.1f を超える(馬は上がれない)"
                       % (r["name"], 1.0 / g, 1.0 / lim))
        if abs(g - r.get("grade", g)) > 1e-3:
            bad.append("斜路 %s の grade %.3f が drop/run %.3f と合わない"
                       % (r["name"], r.get("grade"), g))
        # 平面に走りの余地があるか
        span = max(abs(r["u1"] - r["u0"]), abs(r["v1"] - r["v0"])) * K
        if span + 0.02 < run:                       # run は 2 桁丸めなので 2cm の余裕
            bad.append("斜路 %s の走り %.2fm が平面の %.2fm に収まらない" % (r["name"], run, span))
    return bad


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
            px, pz = x + nx_ * _PROBE(d) * sg, z + nz_ * _PROBE(d) * sg
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
                # ⚠ 丁場に**上限**を置く。上限が無いと、段をいくら持ち上げても
                #   `4s >= dmax` が構造的に成り立ち、「壁高が足りるか」の分岐が
                #   **到達不能**になる(2026-08-25 検図10巡 中-1)。
                sq_s = min(d["const"].get("plinthSMax", 0.75),
                           max(0.20, math.ceil(dmax / 4.0 / 0.05 - 1e-9) * 0.05))
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
        return _unmeasured("boundary_fill_check", "doi_dem.json")
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
            px, pz = x + nx_ * _PROBE(d) * sg, z + nz_ * _PROBE(d) * sg
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


def _seg_seg_dist(p, q, r, t):
    """線分 p-q と r-t の最短距離。交われば 0。⚠ 既存の `_seg_dist`(点→線分)とは別物。"""
    def _pt(a, b, c):
        bx, by = b[0] - a[0], b[1] - a[1]
        L2 = bx * bx + by * by
        if L2 <= 1e-18:
            return math.hypot(c[0] - a[0], c[1] - a[1])
        s9 = max(0.0, min(1.0, ((c[0] - a[0]) * bx + (c[1] - a[1]) * by) / L2))
        return math.hypot(a[0] + bx * s9 - c[0], a[1] + by * s9 - c[1])
    if _seg_cross(p, q, r, t):
        return 0.0
    return min(_pt(p, q, r), _pt(p, q, t), _pt(r, t, p), _pt(r, t, q))


def obb_gap(a, b):
    """物どうしの**平面の最短距離**[間]。重なっていれば 0。⛔ 外接矩形で測らない。

    ⚠ 2026-09-06 検図方 高3: `mune_gap_check` は「隣り合う棟」と名乗りながら
    **`munes` の7棟しか回しておらず、棟×附属屋・附属屋どうしを一度も見ていなかった**。
    附属屋には**回転した家中長屋**があるので、外接矩形で測ると空きを過大に読む。
    """
    P, Q = obb_pts(a), obb_pts(b)
    if obb_overlap(a, b):
        return 0.0
    n = len(P)
    m = len(Q)
    return min(_seg_seg_dist(P[i], P[(i + 1) % n], Q[j], Q[(j + 1) % m])
               for i in range(n) for j in range(m))


def _overhang(d, o):
    """その建物の屋根が**足形の外へ出る量**[m](軒の出 + 妻の出)。

    ⚠ 2026-09-06 検図方 高3: **軒の出は建物ごとに違う**。閾値を一律 2.40m に固定すると、
    ⛔ 祠のように**足形=部材の外形**の物まで 1.20m 出ていることにして、要らない空きを求める。
    ⭕ 正典は物の `noki`(`de` / `tsuma`)で、無ければ `const` の既定。
    """
    C = d["const"]
    nk = o.get("noki") or {}
    return nk.get("de", C["nokiDe"]) + nk.get("tsuma", C["tsumaEnd"])


def mune_gap_check(d):
    """**隣り合う建物の空きが、屋根として成立するか。**

    ⚠ 2026-08-27(EDO-0049)に松平が実装で踏み、他邸へ申し送った。当家では
      当たっていた — にもかかわらず**20本以上ある検査のどれも鳴らなかった**。
      棟の矩形が重なっていないことは `overlap_check` が見ているが、
      **「重なっていない」と「屋根が成立する」は別**。

    切妻屋根は桁行方向へ両端が `tsumaEnd` 長く、両隣の棟の軒の出 `nokiDe` と重なる。
    重なりの合計が棟間の空きを超えると、瓦が隣の棟の屋根を突き抜ける。
    処方は正典 `buildings.md`「渡廊下は1間では成立しない」の2択 —
      (a) 空きを必要量まで広げる  (b) 空きを詰めて入側どうしを直に継ぐ(突き付け)。
    ⛔ **中途半端な空きを残さない** — 0 か 必要量以上か、のどちらか。

    ⭐⭐ **2026-09-06 検図方 高3 で三つ直した**:
      ① 対象を **`munes` + `service`** へ広げた(⛔ 棟どうしだけを見ない)。
      ② **OBB で測る**(回転した家中長屋を外接矩形で測ると空きを過大に読む)。
      ③ 必要量を**建物ごとの軒の出+妻の出の和**から出す(⛔ 一律 2.40m に固定しない)。
    """
    K = d["const"]["ken"]
    M = d["munes"] + d.get("service", [])
    bad = []
    for i in range(len(M)):
        for j in range(i + 1, len(M)):
            a, b = M[i], M[j]
            need = _overhang(d, a) + _overhang(d, b)
            sep = obb_gap(a, b) * K
            if sep <= 1e-9 or sep >= need - 1e-9:
                continue                       # 突き付け か 十分な空き
            bad.append("%s と %s の空きが %.3fm(%.2f間)しかない — "
                       "屋根が %.2fm(%s %.2f + %s %.2f)出るので瓦が突き抜ける。"
                       "広げるか突き付けるか"
                       % (a.get("label", a["name"]), b.get("label", b["name"]),
                          sep, sep / K, need,
                          a.get("label", a["name"]), _overhang(d, a),
                          b.get("label", b["name"]), _overhang(d, b)))
    return bad


def _quad(cx, cz, ux, uz, hl, ht):
    """辺に沿う矩形の平面形。(ux,uz)=辺の単位ベクトル、hl=辺方向の半長、ht=法線方向の半厚。"""
    nx, nz = -uz, ux
    return [(cx + ux * a * hl + nx * b * ht, cz + uz * a * hl + nz * b * ht)
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _seg_x(p1, p2, q1, q2):
    """線分 p1-p2 と q1-q2 が交わるか。"""
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = cr(q1, q2, p1), cr(q1, q2, p2)
    d3, d4 = cr(p1, p2, q1), cr(p1, p2, q2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _closure_footprints(d):
    """**外周を実際に塞ぐ物**の平面形を、指図の設計値だけから組む(世界座標)。

    ⛔ **門の開口は、扉(`leaf`)を申告するまで穴として数える。**開口幅と敷居しか
      書いていない門は、建てれば素通しになる。⭐ 扉の出どころ(門の躯体に含まれる /
      別部材)は閉じの判定を変えない — どちらでも開口は閉じる。
    """
    P = d["polygon"]
    C = d["const"]
    n = len(P)
    out = []

    def edge(e):
        a, b = P[e % n], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return a, ((b[0] - a[0]) / L, (b[1] - a[1]) / L), L

    def put(name, e, s0, s1, t):
        a, u, L = edge(e)
        c = (a[0] + u[0] * (s0 + s1) / 2.0, a[1] + u[1] * (s0 + s1) / 2.0)
        out.append((name, _quad(c[0], c[1], u[0], u[1], (s1 - s0) / 2.0, t)))

    for r in d["runs"]:
        t = (C["nagayaD"] if r["kind"] == "Nagaya" else C["dobeiT"]) / 2.0
        put(r["name"], r["edge"], r["s0"], r["s1"], t)

    g = d.get("gate")
    if g:
        w = g["plan"]["monW"] / 2.0
        door = g["plan"]["doorKen"] * C["ken"] / 2.0        # 門戸部(扉の開口)
        t = g["plan"]["monD"] / 2.0
        # 躯体のうち門戸部の左右は塞ぐ。門戸部そのものは leaf を申告した時だけ塞ぐ。
        put("表門/躯体(南)", g["edge"], g["s"] - w, g["s"] - door, t)
        put("表門/躯体(北)", g["edge"], g["s"] + door, g["s"] + w, t)
        if g["plan"].get("leaf"):
            put("表門/門扉", g["edge"], g["s"] - door, g["s"] + door, t)

    for k in d.get("komon") or []:
        if not k.get("leaf"):
            continue                                        # 扉が無い門は穴
        put(k["name"], k["edge"], k["s"] - k["w"] / 2.0, k["s"] + k["w"] / 2.0,
            C["dobeiT"] / 2.0)
    return out


def perimeter_closure_check(d, tol=0.4, step=0.2):
    """**外周が閉じているか** — 区画線をまたぐ線が、どこかで外周の物に当たるかを全長で測る。

    ⚠ 2026-08-29(EDO-0053)に松平がユーザーの指摘4件から起こした検査の当家版。
      当家には検査が20本以上あるが、`perimeter_check` は**辺の s 上の帳簿**しか見ていない
      — 「run を申告した」ことと「建てれば塞がる」ことは別で、0件はその帳簿を満たした
      以上を意味しない。`qa-and-pitfalls.md`「検査の文言と実装の集合を突き合わせる」。
    ⛔ **当家が持つ辺だけを回す**(`edgeOwner`)。南=岡部・北西=松平の所有辺で回すと
      全区間が穴として出る — それは当家の欠陥ではない。
    """
    P = d["polygon"]
    own = d.get("edgeOwner", {})
    n = len(P)
    fps = _closure_footprints(d)
    cx = sum(q[0] for q in P) / n
    cz = sum(q[1] for q in P) / n
    bad = []
    for e in range(n):
        if own.get(str(e)) != "土井":
            continue
        a, b = P[e], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -uz, ux
        mx, mz = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        if (cx - mx) * nx + (cz - mz) * nz < 0:
            nx, nz = -nx, -nz                               # 内向き
        holes, cur, s = [], None, 0.0
        while s <= L + 1e-9:
            p1 = (a[0] + ux * s - nx * 2.0, a[1] + uz * s - nz * 2.0)
            p2 = (a[0] + ux * s + nx * 5.0, a[1] + uz * s + nz * 5.0)
            hit = False
            for _, q in fps:
                for i in range(4):
                    if _seg_x(p1, p2, q[i], q[(i + 1) % 4]):
                        hit = True
                        break
                if hit:
                    break
            if hit:
                if cur is not None:
                    holes.append(tuple(cur))
                    cur = None
            else:
                cur = [s, s] if cur is None else [cur[0], s]
            s += step
        if cur is not None:
            holes.append(tuple(cur))
        for s0, s1 in holes:
            if s1 - s0 + step >= tol:
                bad.append("辺%d(当家)の s%.1f〜%.1f(%.2fm)が外周として閉じていない — "
                           "塞ぐ物を指図に書く(門なら扉 leaf)" % (e, s0, s1, s1 - s0 + step))
    return bad


def clearance_check(d):
    """棟・付属屋から**区画線まで**の離れ。犬走り+基壇厚を確保する。

    `inubashiri_check` は「棟↔**段**」しか測らないので、区画線までの離れは
    どの検査も見ていなかった。段を半間の格子へ寄せた是正で、米蔵と松平境の離れが
    1.68m → 1.32m に縮んでいたのを見落とした(2026-08-24 検図9巡 中-5)。
    """
    K = d["const"]["ken"]
    # ⚠ **基壇の厚みを定数で持たない。** `fix_run_s` が算出する 2.4s(段築で最大 2.71m)と
    #   定数 0.3m が**最大 2.41m 食い違って**いた(2026-08-25 検図12巡 中-3)。
    #   その辺に外周 run があればその底厚を、無ければ境界の基壇の底厚を使う。
    P2 = d["polygon"]
    gr2 = RGrid(d)
    inub = d["const"]["inubashiri"] * K

    def _need_at(x, z):
        best = inub + 0.3
        for r in d["runs"]:
            if r.get("base") != "Ishigaki" or "s" not in r:
                continue
            a2, b2 = P2[r["edge"]], P2[(r["edge"] + 1) % len(P2)]
            if _seg_dist(x, z, a2, b2) > 4.0:
                continue
            ti = r.get("tiers", 1)
            best = max(best, inub + 2.4 * r["s"] * ti + inub * (ti - 1))
        for q in d.get("boundaryPlinth", []):
            a2, b2 = P2[q["edge"]], P2[(q["edge"] + 1) % len(P2)]
            if _seg_dist(x, z, a2, b2) <= 4.0:
                best = max(best, inub + 2.4 * q["s"])
        return best
    P = d["polygon"]
    gr = RGrid(d)
    bad = []
    for m in d["munes"] + d.get("service", []):
        best = 1e9
        for u, v in obb_pts(m):
            x, z = gr.W(u, v)
            for i in range(len(P)):
                best = min(best, _seg_dist(x, z, P[i], P[(i + 1) % len(P)]))
        need = _need_at(*gr2.W(*obb_pts(m)[0]))
        if best + 1e-6 < need:
            bad.append("%s から区画線までが %.2fm — 犬走り+基壇の底 %.2fm に足りない"
                       % (m["name"], best, need))
    return bad


def rails_check(d):
    """竹垣の不変条件。設計値 `_rails` が自分で宣言している条件を検査に落とす。

    ⚠ かつて「竹垣は意匠なので不変条件を持たない」と書いたが、`_rails` 自身が
    「**土を受けず動線も止めない**」と宣言しており、後者は検査できる
    (2026-08-24 検図9巡 低-3)。**宣言した不変条件には検査を付ける。**
    土を受けない側は、法肩に沿う垣が自然の崖と重なるため今回は立てない。

    ⭐ **2026-09-06 に「丈」の条を足した。**部材 `EdoAssets.Own.YotsumeGaki(h)` は
    **胴縁の段数を丈で変える**(h1.2=4段 / h0.9=3段 / h0.6=2段)ので、丈が無いと
    棟梁が段数を発明することになる(棟梁の差し戻し①)。焼いてあるのは 0.6/0.9/1.2 の3種だけ。
    ⛔ **これは意匠の検査ではない** — 「指図が名指しした部材で建つか」の検査で、
    測れば決まる(在庫の焼成寸法と設計値の突き合わせ)。
    """
    YOTSUME_H = (0.6, 0.9, 1.2)      # `EdoAssets.Own.YotsumeGaki(h)` が焼いてある丈
    bad = []
    for rl in d.get("rails", []):
        if rl.get("h") is None:
            bad.append("竹垣 %s に丈 `h` が無い — 四つ目垣は**丈で胴縁の段数が変わる**ので、"
                       "無いと実装が段数を発明する" % rl["name"])
        elif not any(abs(rl["h"] - q) < 1e-9 for q in YOTSUME_H):
            bad.append("竹垣 %s の丈 %.2fm は `EdoAssets.Own.YotsumeGaki(h)` に焼いていない"
                       "(焼成済は %s)— 焼き足すか丈を揃えるか、どちらかが要る"
                       % (rl["name"], rl["h"], " / ".join("%.1f" % q for q in YOTSUME_H)))
        if not rl.get("asset"):
            bad.append("竹垣 %s に部材 `asset` が無い" % rl["name"])
        elif "TakeGaki" in rl["asset"]:
            bad.append("竹垣 %s が `Eg.TakeGaki` を指している — あれは**竹の菱格子**で"
                       "四つ目垣ではない(2026-09-04 実見)。`Own.YotsumeGaki(h)` を使う"
                       % rl["name"])
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


def cert_rulings_table(d):
    """**過去に確度を裁定した項目**(`certRulings`)を図に出す。

    ⚠⚠ **2026-09-06 まで `certRulings` はどこにも描かれていなかった** — `program_check` が
    「裁定を黙って巻き戻していないか」を測るためだけに読んでおり、**裁定の出自(`when`)と
    理由(`why`)は正典にだけ在って、図には一行も出ていなかった**。
    ⛔ **書いたのに誰の目にも入らない産物を作らない**(規則19)。
    ⭐ 発覚は 2026-09-06、**池の裁定の attribution を直した巡** — 「⛔ ユーザー裁定ではない」と
    正典に書いても、**読む人の目には届かないまま**だった。
    """
    rows = []
    for r in d.get("certRulings", []):
        rows.append((r.get("role", "?"), r.get("what", "?"),
                     "<b>%s</b>" % r.get("cert", "?"), r.get("when", "—"),
                     " / ".join("[%s]" % q for q in r.get("src", [])) or "—",
                     r.get("why", "")))
    if not rows:
        return "<p class='cap'>⚠ <b>裁定の記録が 0 件。</b></p>"
    return _tw(("役割", "側面", "確度", "いつ・誰が", "典拠", "理由"), rows) + (
        "<p class='cap'>⛔ <b>一度下した裁定を黙って巻き戻さない。</b>"
        "確度の妥当さは機械では測れないが、<b>裁定と食い違っていることは測れる</b> — "
        "<code>program_check</code> が「役割 × 側面」で <code>program</code> と突き合わせ、"
        "ずれたら鳴る。⭕ <b>上げ直すならこの表を書き換える</b>(その差分がレビューに乗る)。"
        "⚠⚠ <b>「いつ・誰が」を正しく書く</b> — 意匠の役(庭方・部材方)は"
        "<b>棟や池の『存在』を決める権限を持たない</b>(規則17)。"
        "⛔ <b>渡された側を出自として記録しない。</b></p>")


def program_table(d):
    """在るべき役割の表。**確度は側面ごと**に出す(役割ごとに一つへ潰さない)。"""
    # 確度の色。⚠ sashizu.css に在る変数だけを使う — 無い変数は黙って既定色になり、
    #   S と U が同じ見た目になる(2026-08-25: --cert-* を書いて全部同色だった)
    CC = {"S": "var(--cut1)", "A": "var(--shu)", "B": "var(--ink-mid)",
          "P": "var(--take)", "U": "var(--fill1)", "?": "var(--ink-lo)"}
    rows = ["<table><thead><tr><th>役割</th><th>満たす物</th><th>側面</th>"
            "<th>確度</th><th>典拠</th><th class='note'>断り</th></tr></thead><tbody>"]
    for pg in d.get("program", []):
        asp = pg.get("aspects", [])
        for i, a in enumerate(asp):
            head = ("<td rowspan='%d'><b>%s</b></td><td rowspan='%d'><code>%s</code></td>"
                    % (len(asp), pg["role"], len(asp),
                       "</code> <code>".join(pg["by"]))) if i == 0 else ""
            rows.append("<tr>%s<td>%s</td>"
                        "<td style='color:%s'><b>%s</b></td><td><code>%s</code></td>"
                        "<td class='note'>%s</td></tr>"
                        % (head, a.get("what", ""), CC.get(a.get("cert"), "var(--note)"),
                           a.get("cert", "—"),
                           "</code> <code>".join(a.get("src") or []) or "—",
                           a.get("_", "")))
    rows.append("</tbody></table>")
    nt = d.get("_採らなかった役割") or {}
    if nt:
        rows.append("<h3>採らなかった役割</h3><table><thead><tr><th>役割</th>"
                    "<th class='note'>採らない理由</th></tr></thead><tbody>")
        for k, v in nt.items():
            rows.append("<tr><td><b>%s</b></td><td class='note'>%s</td></tr>" % (k, v))
        rows.append("</tbody></table>")
        rows.append("<p class='cap'>⛔ <b>沈黙は情報を持たない。</b> 採らなかったものは"
                    "「落とした」のか「捨てた」のかが区別できるよう、ここに理由を書く。</p>")
    return "".join(rows)


def komon_step_check(d, dem):
    """**門の敷居と街路の差を、段が受けているか。**

    ⚠ 2026-09-06 検図方 中-1: 通用門の敷居を基壇の天端(21.90)へ揃えた結果、
    **街路(21.32)より 0.58m 高くなったのに登る段が図に無かった** — 勝手の門で
    荷を担いで上がる所である。⚠ `route_check` の 3m 窓では**均されて見えなかった**
    (動線が門の位置に折れ点を持っていなかったため)。

    ⭐ **閾値は `const.keri`(蹴上 0.30)**。⛔ 新しい閾値を発明していない — 理屈は
    **「一蹴上に満たない差は段では受けられない」**(そこは跨ぐ敷居であって段ではない)。
    ⇒ 表門 +0.15 / 裏木戸 +0.21 は段の要らない敷居、通用門 +0.58 は段が要る。
    ⚠ **差の実測は3門とも「小門の部材」の表に刷る**(閾値で隠さない=規則19)。
    """
    if dem is None:
        return _unmeasured("komon_step_check", "doi_dem.json")
    P = d["polygon"]
    lim = d["const"]["keri"]
    bad = []
    for k in (d.get("komon") or []) + [dict(d["gate"], name="表門",
                                            w=d["gate"]["plan"]["monW"])]:
        x, z = edge_pt(P, k["edge"], k["s"])
        g9 = dem_bilinear(dem, x, z)
        if g9 is None:
            continue
        dz = k["sill"] - g9
        fi = k.get("fumiishi")
        if dz > lim + 1e-6 and not fi:
            bad.append("門 %s の敷居が街路より %+.2fm 高い(蹴上 %.2f を超える)のに"
                       "登る段が無い — `fumiishi` を立てるか敷居を下げる"
                       % (k["name"], dz, lim))
        if fi:
            n9 = int(fi.get("n", 0))
            if n9 < 1:
                bad.append("門 %s の `fumiishi.n` が %r" % (k["name"], fi.get("n")))
            elif dz <= 1e-6:
                bad.append("門 %s に踏石があるが敷居が街路より高くない(%+.2fm)"
                           % (k["name"], dz))
            elif dz / n9 > lim + 1e-6:
                bad.append("門 %s の踏石 %d段 では蹴上が %.2fm になる(上限 %.2f)— 段を増やす"
                           % (k["name"], n9, dz / n9, lim))
    return bad


def route_check(d, dem):
    """**動線の縦断勾配**と、**段の縁をどこで越えるか**。

    ⚠ `rampGradeMax` は**宣言した斜路にしか効かない**。動線図は「3m窓の最急」を算出して
    図に出していたが**閾値の判定が無く**、勝手動線が石段の足元へ 1:3.0 の法面を斜めに
    登っていた(2026-08-25 検図14巡 中-4)。
    ⚠ さらに `TW_Kita` と `K_Kita` を**同時に**消しても全検査が無音だった —
    **段の縁を石段・斜路・廊下以外で越えることを止める検査が一つも無かった。**
    """
    if dem is None:
        return _unmeasured("route_check", "doi_edo_world.json")
    K = d["const"]["ken"]
    gr = RGrid(d)
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    lim = d["const"].get("routeGradeMax", 1.0 / 6.0)
    win = d["const"].get("routeGradeWindow", 3.0)      # m。3m窓の最急で見る
    bad = []
    for r in d.get("routes", []):
        pts, ys, run = [], [], 0.0
        for a, b in zip(r["pts"], r["pts"][1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            n = max(2, int(seg / 0.1))
            for i in range(n + 1):
                if i == 0 and pts:
                    continue
                u = a[0] + (b[0] - a[0]) * i / n
                v = a[1] + (b[1] - a[1]) * i / n
                x, z = gr.W(u, v)
                nat = dem_bilinear(dem, x, z)
                y = stair_y(d, u, v)
                if y is None:
                    y = ramp_y(d, u, v)
                if y is None:
                    y = design_y(d, u, v)
                if y is None and nat is not None:
                    y = graded_y(d, u, v, nat, we)
                if y is None:
                    continue
                if pts:
                    run += math.hypot(u - pts[-1][0], v - pts[-1][1]) * K
                # 勾配の判定から外す区間 — ここは専用の検査が見ている:
                #   石段 / 斜路 / 段のある廊下 / 区画の外(取付の街路)
                skip = (stair_y(d, u, v) is not None or ramp_y(d, u, v) is not None
                        or not in_parcel(d, u, v)
                        or any(l.get("steps") and l["u0"] - 0.2 <= u <= l["u1"] + 0.2
                               and l["v0"] - 0.2 <= v <= l["v1"] + 0.2
                               for l in d.get("links", [])))
                pts.append((u, v, run, skip))
                ys.append(y)
        # ① 3m窓の最急(石段・斜路の区間は除く — そこは専用の検査が見る)
        worst, spot = 0.0, None
        # 直前までに現れた「除外区間」の位置。⚠ **両端だけ見ると窓が石段をまたぐ。**
        #   端点が石段の外でも、あいだに石段があれば窓はその落差を拾う
        #   (K_ShuS の 0.6m を 1:3.0 の斜面として報告していた)。**あいだも見る。**
        nskip = [0] * (len(pts) + 1)
        for q in range(len(pts)):
            nskip[q + 1] = nskip[q] + (1 if pts[q][3] else 0)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if pts[j][2] - pts[i][2] > win:
                    break
                if nskip[j + 1] - nskip[i] > 0:
                    continue
                dl = pts[j][2] - pts[i][2]
                if dl < 0.5:
                    continue
                # ⚠ **段差と斜面を混同しない。** 0.15m の敷居は「登る斜面」ではないので、
                #   歩行者が呑める高さ(`routeStepAbsorb`)までは勾配として数えない。
                #   これを入れないと、面と面が実質つながっている所が延々と鳴る。
                if abs(ys[j] - ys[i]) <= d["const"].get("routeStepAbsorb", 0.2):
                    continue
                gsl = abs(ys[j] - ys[i]) / dl
                if gsl > worst:
                    worst, spot = gsl, (pts[i][0], pts[i][1])
        if worst > lim + 1e-9:
            bad.append("動線 %s が 1:%.1f の斜面を登る(上限 1:%.0f・グリッド %.1f, %.1f)"
                       " — 石段か斜路を切るか、面を延ばして足元を受けること"
                       % (r["label"], 1.0 / worst, 1.0 / lim, spot[0], spot[1]))
        # ② 段の縁(土留めの線)を、開口の外で越えていないか
        for w in d["terraceWalls"]:
            vert = abs(w["a"][0] - w["b"][0]) < 1e-9
            line = w["a"][0] if vert else w["a"][1]
            lo, hi = ((min(w["a"][1], w["b"][1]), max(w["a"][1], w["b"][1])) if vert
                      else (min(w["a"][0], w["b"][0]), max(w["a"][0], w["b"][0])))
            for (u0_, v0_, _, _), (u1_, v1_, _, _) in zip(pts, pts[1:]):
                q0 = u0_ if vert else v0_
                q1 = u1_ if vert else v1_
                if (q0 - line) * (q1 - line) >= 0:
                    continue
                t = (line - q0) / (q1 - q0)
                cross = (v0_ + (v1_ - v0_) * t) if vert else (u0_ + (u1_ - u0_) * t)
                if not (lo - 1e-9 <= cross <= hi + 1e-9):
                    continue
                sp = pass_span(d, w)[0]
                gk = "gapV" if vert else "gapU"
                if gk in w and any(a_ - 0.3 <= cross <= b_ + 0.3 for a_, b_ in sp):
                    continue
                bad.append("動線 %s が土留め %s を**開口の外**で越える(%s=%.2f)"
                           % (r["label"], w["name"], "v" if vert else "u", cross))
                break
    return bad


def setchin_check(d):
    """**区画ごとに雪隠が在るか。**

    ⚠ 2026-08-26 まで当家は中奥と奥向にしか雪隠が無く、**客が用を足すのに中奥へ入る**図に
    なっていた(表向の到達に結界を効かせたのと同じ理屈で成り立たない)。
    ⛔ **松平・岡部も同じ欠落で、3邸とも雪隠が抜けていた** — 外の錨(`estate-types.md` の
    役割表)が無ければ**自己検図では構造的に見えない**穴である。
    """
    KEY = ("雪隠", "後架", "厠", "閑所")
    zones = d["const"].get("setchinZones") or {}
    by = dict((m["name"], m) for m in d["munes"] + d.get("service", []))
    bad = []
    # ⛔ **宣言を消せば通る、をやらない。** 区画の宣言そのものが無ければ検査は自己免除になる。
    #   人が居続ける棟(御殿の棟+表役所)は必ずどれかの区画に属していること。
    need = set(m["name"] for m in d["munes"] if m.get("goten")) | {"Yakusho"}
    covered = set()
    for names in zones.values():
        covered |= set(names)
    for n in sorted(need - covered):
        bad.append("棟 %s が雪隠の区画(`setchinZones`)のどれにも属していない — "
                   "人が居続ける棟は必ず区画に入れること" % n)
    # ⛔ **区画を粗くする道を塞ぐ。** 段①②だけでは「表役所を表向へ統合してその雪隠を消す」が
    #   通った(2026-08-26 松平の指摘)。当家で試すと**全部を1区画にまとめて雪隠を3室消しても
    #   0件**だった。宣言を消すのではなく**宣言を薄める**ほうの自己免除である。
    #   ⇒ 区画そのものを**裁定 `zoneRulings` として持つ**(`certRulings` と同じ考え)。
    #   溶かすなら裁定を書き換えることになり、その差分がレビューに乗る。
    # ⛔ **錨にも錨が要る。** 裁定を丸ごと消せば通る、では自己免除が一段外へ逃げるだけ。
    #   ⇒ **最外の錨は共有台帳**(`estate-types.md`)に置く。役割表が「湯殿・雪隠」を必須と
    #   している限り、裁定は空にできない。ここで止める(台帳は他邸と共有で、当邸だけでは変えられない)。
    rulings = d.get("zoneRulings", [])
    try:
        norm = estate_program_norm()
        sep0 = estate_zone_norm()
    except AnchorMissing as e:
        # ⛔ **錨が読めないなら、錨に依る検査は「合格」ではなく「回っていない」。**
        return bad + ["⛔ %s — **区画の裁定と区画の別の検査が回っていない**(合格ではない)" % e]
    # ⛔ **台帳の役割の「名前」から区画の別を組み立てる。** 台帳が在ることだけを錨にすると
    #   「区画を減らす」道が残る(2026-08-26 松平)。⚠ 書院と局は集合に入れない —
    #   **人の別ではなく場の別**を分ける集合でないと正しい構成まで落ちる。
    sep = sep0
    if sep:
        zone_of = {}
        for zn, ns in zones.items():
            for n in ns:
                zone_of[n] = zn
        seen_zone = {}
        for pg in d.get("program", []):
            if pg["role"] not in sep:
                continue
            zs = set(zone_of.get(n) for n in pg["by"] if n in zone_of)
            zs.discard(None)
            if not zs:
                bad.append("役割「%s」を満たす棟(%s)がどの雪隠の区画にも属していない — "
                           "台帳は別の区画に属す役割としている"
                           % (pg["role"], "・".join(pg["by"])))
                continue
            for z in zs:
                if z in seen_zone and seen_zone[z] != pg["role"]:
                    bad.append("役割「%s」と「%s」が同じ区画「%s」に居る — "
                               "台帳は別の区画に属す役割としている(`estate-types.md`)"
                               % (seen_zone[z], pg["role"], z))
                seen_zone[z] = pg["role"]
    if any(k.startswith("湯殿") or "雪隠" in k for k, v in norm.items() if "必須" in v):
        ruled = set()
        for rl in rulings:
            ruled |= set(rl.get("must", []))
        for n in sorted(need - ruled):
            bad.append("棟 %s が雪隠の区画の**裁定** `zoneRulings` に現れない — "
                       "共有台帳 `estate-types.md` は雪隠を必須としている" % n)
    for rl in rulings:
        nm = rl["zone"]
        if nm not in zones:
            bad.append("雪隠の区画「%s」が `setchinZones` から消えている(%s の裁定)— "
                       "区画を溶かすなら `zoneRulings` を書き換えること" % (nm, rl["when"]))
        elif not zones[nm]:
            bad.append("雪隠の区画「%s」に棟が一つも属していない(%s の裁定)" % (nm, rl["when"]))
        else:
            miss = [n for n in rl.get("must", []) if n not in zones[nm]]
            if miss:
                bad.append("区画「%s」から %s が外れている(%s の裁定)"
                           % (nm, "・".join(miss), rl["when"]))
    gr = RGrid(d)
    K = d["const"]["ken"]
    lim = d["const"].get("setchinReach", 40.0)
    for zone, names in zones.items():
        got = []
        pts = []
        for n in names:
            m = by.get(n)
            if m is None:
                bad.append("雪隠の区画「%s」が挙げる棟 %s が指図に無い" % (zone, n))
                continue
            for r in m.get("rooms", []):
                if any(k in r["name"] for k in KEY):
                    got.append(r["name"])
                    pts.append(((r["u0"] + r["u1"]) / 2.0, (r["v0"] + r["v1"]) / 2.0))
        if not got:
            bad.append("区画「%s」(%s)に雪隠が一室も無い — "
                       "用を足すのに区画をまたぐ図は成り立たない"
                       % (zone, "・".join(names)))
            continue
        # ⚠ **区画を粗くしても距離では逃げられない。** 区画が正しくても遠すぎれば同じこと。
        for n in names:
            m = by.get(n)
            if m is None or "yaw" in m:
                continue
            cu, cv = (m["u0"] + m["u1"]) / 2.0, (m["v0"] + m["v1"]) / 2.0
            dmin = min(math.hypot(cu - p[0], cv - p[1]) * K for p in pts)
            if dmin > lim:
                bad.append("棟 %s から同じ区画「%s」の雪隠まで %.1fm(上限 %.1fm)— "
                           "遠すぎる" % (n, zone, dmin, lim))
    return bad


# ⛔ **分類の網から落ちたものを既定値へ倒さない。** 語彙で振り分ける欄は、知らない値が来たら
#   黙って「その他」に落ちる。2026-08-26 に実測した当家の被害:
#     `runs[].kind` を誤字にすると表長屋が数から消え、**建蔽率が 23.6% → 22.3%**(誰も鳴らない)
#     `bom[].measure` を誤字にすると延長が「—」になる(同上)
#   松平が同日、要否の判定を接頭辞の白名簿で書いていて同じ形を踏んだ
#   ——「取りこぼしを黙って安全側でない側へ倒している」。**「分からない」と言わせる。**
#   (欄そのものが無くてよい所は opt=True。**「無い」と「知らない値」を分ける** —
#    無いのは設計、知らない値は誤字。)
VOCAB = [
    # coll,       fld,        許される値,                                       opt,  名前の欄
    ("runs",      "kind",     ("Nagaya", "Dobei"),                              False, "name"),
    ("bom",       "measure",  ("terraceWalls", "boundaryPlinth", "runBase",
                               "flank", "kaidan", "rails", "umeToi",
                               "otoshimizo"),                                   True,  "item"),
    ("links",     "kind",     ("渡廊下", "階段廊下", "御錠口"),                  False, "name"),
    # kansho = 鑑賞の庭(座敷から見る庭)。2026-09-04 に奥庭が池庭になったので足した
    ("gardens",   "kind",     ("shirasu", "niwa", "kansho"),                    True,  "name"),
    # ⭐ 2026-09-04: 4枠のうち1枠(表と中奥の間)が「中庭」として名が立ち **B** になった
    #   (考証方 中-10)。⛔ **無条件に広げない** — 許すのは「?(用途未定)」と「B(類型で
    #   名が立った)」の二つだけで、S/A は当屋敷の記録が要る。
    ("akichi",    "cert",     ("?", "B"),                                       False, "name"),
    ("routes",    "kind",     ("omote", "yaku", "katte", "oku"),                False, "name"),
]


def vocab_check(d):
    """**語彙で振り分ける欄に、知らない値が入っていないか。**"""
    bad = []
    for coll, fld, ok, opt, nm in VOCAB:
        for o in d.get(coll, []):
            if fld not in o or o.get(fld) is None:
                if opt:
                    continue
                bad.append("%s %s に `%s` が無い" % (coll, o.get(nm, "?"), fld))
                continue
            if o[fld] not in ok:
                bad.append("%s %s の `%s` が知らない値 %r — "
                           "語彙に無い値は黙って既定へ倒れる(建蔽率・延長が静かに狂う)"
                           % (coll, o.get(nm, "?"), fld, o[fld]))
    return bad


def program_check(d):
    """**在るべき役割が在るか。側面ごとに確度と典拠が付いているか。**

    ⚠ これが無いあいだ、**棟を消しても検査が一つも鳴らなかった**
    (2026-08-25 検図13巡・削除の感度試験: Yakusho / Komegura / Kura1 / Kura2 / Inari)。
    ⚠ 初版は役割ごとに確度を**一つ**しか持てず、「存在は S だが位置は U」を潰していた。
    さらに台帳が U と裁定済みの米蔵を [高知2000]A へ戻していた(2026-08-25 考証13巡 高-1)。
    **側面ごとに確度と典拠IDを持ち、ID は台帳と突き合わせる。**
    """
    CERT = ("S", "A", "B", "P", "U", "?")
    have = set(o["name"] for o in d["munes"] + d.get("service", []))
    have |= set(w["name"] for w in d.get("wells", []))
    have |= set(r["name"] for r in d.get("runs", []))       # 外周(表長屋・練塀)も役割を負う
    have |= set(g["name"] for g in d.get("gardens", []))    # 庭・白洲
    have |= set(l["name"] for l in d.get("links", []))      # 御錠口・廊下
    have |= set(r["name"] for r in d.get("rails", []))      # 竹垣
    have |= set(a["name"] for a in d.get("akichi", []))     # 明地(用途未定の空白)
    if d.get("gate"):
        have.add("gate")
    head, tbl = sources_index()
    known = set(head) | set(tbl)
    bad = []
    named = set()
    for pg in d.get("program", []):
        named |= set(pg["by"])
        miss = [n for n in pg["by"] if n not in have]
        if len(miss) == len(pg["by"]):
            bad.append("役割「%s」を満たす物が一つも無い(%s)" % (pg["role"], "・".join(pg["by"])))
        elif miss:
            bad.append("役割「%s」の %s が指図に無い" % (pg["role"], "・".join(miss)))
        asp = pg.get("aspects")
        if not asp:
            bad.append("役割「%s」に側面(`aspects`)が無い — 確度を一つに潰さない" % pg["role"])
            continue
        for a in asp:
            if a.get("cert") not in CERT:
                bad.append("役割「%s」の側面「%s」に確度が無い(規則6)" % (pg["role"], a.get("what")))
            for sid in a.get("src", []):
                if sid not in known:
                    bad.append("役割「%s」の側面「%s」が引く `[%s]` が台帳に無い"
                               % (pg["role"], a.get("what"), sid))
            # ⛔ **典拠を引きながら S/A を名乗るのは、その典拠が当屋敷を直接指すときだけ**
            if a.get("cert") in ("S", "A") and not a.get("src"):
                bad.append("役割「%s」の側面「%s」が確度 %s なのに典拠IDが無い"
                           % (pg["role"], a.get("what"), a.get("cert")))
    # ⛔ **過去の裁定を黙って巻き戻さない。** 確度が妥当かは機械では測れないが、
    #   一度下した裁定と食い違っていることは測れる(2026-08-25 考証13巡 高-1:
    #   台帳が U と裁定済みの米蔵の存在を [高知2000]A へ戻していた)。
    idx = {}
    for pg in d.get("program", []):
        for a in pg.get("aspects", []):
            idx[(pg["role"], a.get("what"))] = a.get("cert")
    for rl in d.get("certRulings", []):
        key = (rl["role"], rl["what"])
        if key not in idx:
            bad.append("裁定「%s / %s」に対応する側面が `program` に無い(%s の裁定)"
                       % (rl["role"], rl["what"], rl["when"]))
        elif idx[key] != rl["cert"]:
            bad.append("役割「%s」の側面「%s」が確度 %s だが、%s の裁定は %s — "
                       "巻き戻すなら `certRulings` を書き換えること"
                       % (rl["role"], rl["what"], idx[key], rl["when"], rl["cert"]))

    # ⛔ **共有台帳を外の錨にする。** `program` だけを見ていると、役割と棟を
    #   **同時に消せば通る**(2026-08-25 検図14巡 中-6)。
    try:
        norm = estate_program_norm()
    except AnchorMissing as e:
        return bad + ["⛔ %s — **在るべき役割の照合が回っていない**(合格ではない)" % e]
    have_roles = set(pg["role"] for pg in d.get("program", []))
    waived = set(d.get("_採らなかった役割") or {})
    for role, need in norm.items():
        # ⛔ **免除にも上限を置く。** 「採らなかった」へ移せば通る形だと、
        #   **必須の役割を5つ移すだけで 0件**になった(2026-08-26。松平が同じ形を3度踏んで
        #   「例外を許す仕組みを足したら、その例外の上限も同時に決める」と書いてきた4例目)。
        #   ⇒ **台帳が必須としている役割は「採らなかった」で免除できない。**
        #   外すなら共有台帳の要否を変えることになり、他邸と共有なので当邸だけでは動かせない。
        if role in waived and "必須" in need:
            bad.append("役割「%s」は台帳が**必須**としている — `_採らなかった役割` では"
                       "免除できない(外すなら `estate-types.md` の要否を変えること)" % role)
            continue
        if role in have_roles or role in waived:
            continue
        base = role.split("(")[0]
        if any(base and base in h for h in have_roles) or any(base and base in w for w in waived):
            continue
        if "必須" in need:
            bad.append("上屋敷に**必須**の役割「%s」が `program` にも `_採らなかった役割` にも無い"
                       " — 落としたなら理由を書くこと(`estate-types.md`)" % role)
        else:
            bad.append("役割「%s」(%s)が `program` にも `_採らなかった役割` にも無い — "
                       "採らないなら理由を書くこと" % (role, need))

    # 逆向き — `program` のどの役割にも現れない棟は、消しても誰も気づかない
    for o in d["munes"] + d.get("service", []):
        if o["name"] not in named:
            bad.append("棟 %s が `program` のどの役割にも現れない — 消しても検査が鳴らない"
                       % o["name"])
    return bad


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

    # ⚠ **庭の点景は柱割りに載せない。** 稲荷の小祠は庭方が景の中で据える物で、
    #   御殿の柱割りに乗る建屋ではない(2026-09-04、庭方が北東の隅へ移した位置は
    #   半間の格子から 0.05〜0.10間 外れる)。⛔ 免除は**名指し**で持ち、
    #   `const.gridFreeService` に理由つきで書く — 無名の例外にしない。
    gfree = set(d["const"].get("gridFreeService", []))
    for o in d["munes"] + d.get("service", []):
        if o["name"] in gfree:
            continue
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
        # ⭐ **廊下の幅は一間**(2026-09-06 検図方の検め直し)。`_links` が冒頭で
        #   「幅一間」と宣言しているのに検査が無く、⚠ **御錠口を 3間幅にしても 0 件で黙った**。
        #   ⛔ 宣言した規範には検査を付ける(規則19)。**短辺=幅**として見る
        #   (廊下は長辺が走り・短辺が幅で、向きは棟の並びで決まる)。
        wd = min(l["u1"] - l["u0"], l["v1"] - l["v0"])
        if abs(wd - 1.0) > 1e-6:
            bad.append("%s の幅(短辺)が %.2f間 — 廊下の幅は一間"
                       "(`_links` の宣言。部材キットも幅一間しか持たない)" % (l["name"], wd))

    # ⭐ **室割り**(2026-09-04 検図方 中-2)。⚠ 従前 `rooms` 53室に検査が一本も無く、
    #   御小姓部屋を 0.37間 ずらしても、御次之間を隣室へ2間食い込ませても 0 件だった。
    #   `_pending.rooms` は「検算済み」と書いていたが、**それは人が一度手で見た記録**であって
    #   ラチェットではない(規則19: 輪に入っていない値は未検査)。⛔ 畳数を写して持つ以上、
    #   **面積との一致は毎回測る** — 室を動かして畳数を直し忘れる型は自己検図では見えない。
    for m in d["munes"]:
        rs = m.get("rooms", [])
        for r in rs:
            for k in ("u0", "u1", "v0", "v1"):
                if off(r[k]):
                    bad.append("%s の室「%s」の %s=%.3f間 が半間の格子に載らない"
                               % (m["name"], r["name"], k, r[k]))
            if not (m["u0"] - 1e-9 <= r["u0"] and r["u1"] <= m["u1"] + 1e-9
                    and m["v0"] - 1e-9 <= r["v0"] and r["v1"] <= m["v1"] + 1e-9):
                bad.append("%s の室「%s」(%.1f,%.1f)–(%.1f,%.1f) が棟の矩形からはみ出す"
                           % (m["name"], r["name"], r["u0"], r["v0"], r["u1"], r["v1"]))
            a9 = (r["u1"] - r["u0"]) * (r["v1"] - r["v0"])
            if "tatami" in r and abs(r["tatami"] - a9 * 2.0) > 1e-6:
                bad.append("%s の室「%s」の畳数 %g が面積 %.2f間²×2 = %g と合わない"
                           % (m["name"], r["name"], r["tatami"], a9, a9 * 2.0))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a9, b9 = rs[i], rs[j]
                iu = min(a9["u1"], b9["u1"]) - max(a9["u0"], b9["u0"])
                iv = min(a9["v1"], b9["v1"]) - max(a9["v0"], b9["v0"])
                if iu > 1e-9 and iv > 1e-9:
                    bad.append("%s の室「%s」と「%s」が %.2f×%.2f間 重なる"
                               % (m["name"], a9["name"], b9["name"], iu, iv))

    # ⭐⭐ **大棟と谷の座標も半間の格子に載る**(2026-09-06 検図方 高1)。
    #   ⚠ **全座標に課している網から屋根だけが漏れていた** — 大棟10・谷10 のうち **8本が
    #   1/3間(0.606m)ずれ**ていたのに、`norms_check` は `munes`/`rooms`/`links` しか見ておらず
    #   一件も鳴らなかった。⛔ **江戸間1間=柱の心々**で、**谷は柱通りの上にしか置けない**。
    for m in d["munes"]:
        rf9 = m.get("roof") or {}
        for key9, lab9 in ((rf9.get("bands") or {}, "大棟"), (rf9.get("tani") or {}, "谷")):
            for q9 in (key9.get("at") or []):
                if off(q9):
                    bad.append("%s の%sが %.3f間 — 半間の格子に載らない"
                               "(柱の心々を外れた所に棟も谷も置けない)" % (m["name"], lab9, q9))

    # ⭐ **大棟の向き**(2026-09-06 普請検査の差し戻し)。⚠ 向きが指図に無かったため、
    #   実装が居間棟(16×12間)の大棟を**12間側**に架け、16間 を梁間で飛ばして
    #   棟高 10.3m にしていた(奥 9.8・玄関 9.3・書院 7.3 より高い＝中奥が御殿でいちばん高い姿)。
    #   ⛔ **向きを実装に選ばせない。**規範は「大棟は桁行=長辺方向、棟高は梁間から」【U】。
    for m in d["munes"]:
        rf = m.get("roof") or {}
        a9, b9 = m["u1"] - m["u0"], m["v1"] - m["v0"]
        if "roof" not in m or "ridge" not in rf:
            bad.append("%s に `roof.ridge`(大棟の向き)が無い — "
                       "無いと実装が短辺に架けて棟高が跳ねる" % m["name"])
            continue
        if abs(a9 - b9) < 1e-9:
            if rf["ridge"] is not None:
                bad.append("%s は正方形(%g × %g間)なので大棟の向きは該当なし — "
                           "`ridge` は null にする" % (m["name"], a9, b9))
        elif rf["ridge"] not in ("u", "v"):
            bad.append("%s の `roof.ridge` が %r — `\"u\"` か `\"v\"` で書く"
                       % (m["name"], rf["ridge"]))
        elif (rf["ridge"] == "u") != (a9 > b9):
            bad.append("%s の大棟が**短辺**(%s 方向 %g間)に架かっている — "
                       "大棟は桁行=長辺(%s 方向 %g間)に架け、棟高は梁間から決まる"
                       % (m["name"], rf["ridge"], min(a9, b9),
                          "u" if a9 > b9 else "v", max(a9, b9)))

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
    # ⚠ **面が並べる段と外周の名前**。ここが切れると建蔽率の分母が黙って縮む —
    #   面積は `planes[].terraces` から積むので、名前が消えてもその段のぶんが
    #   落ちるだけで、どの検査も鳴らなかった(2026-08-25 検図13巡・削除の感度試験)。
    rn = set(r["name"] for r in d.get("runs", []))
    used = set()
    for pl in d.get("planes", []):
        for t in pl.get("terraces", []):
            if t not in tn:
                bad.append("面「%s」が並べる段 %s が段に無い" % (pl["name"], t))
            used.add(t)
        for r in pl.get("runs", []):
            if r not in rn:
                bad.append("面「%s」が並べる外周 %s が外周に無い" % (pl["name"], r))
    # 逆向き — どの面にも属さない段は、面積にも図にも出ないまま canon に残る
    for t in d["terraces"]:
        if t["name"] not in used:
            bad.append("段 %s がどの面にも属していない" % t["name"])
    for k in d["kaidans"] + d.get("ramps", []):
        for side in ("hi", "lo"):
            v = k.get(side)
            if isinstance(v, str) and v not in tn:
                bad.append("%s の %s=%s が段に無い" % (k["name"], side, v))
    # ⚠ **区画の正典は `parcels.json`(CLAUDE.md 規則10)。** 指図が持つ `polygon` は写しなので、
    #   突き合わせが無いと**建蔽率の分母が黙って写しのほうから出る**
    #   (2026-08-25 検図14巡 低-4: 頂点の最大差 0.004m・面積差 0.064 m² で照合は無かった)。
    pj = os.path.join(DOC, "parcels.json")
    if os.path.exists(pj):
        try:
            pl = json.load(open(pj, encoding="utf-8"))
            src = None
            for q in (pl.get("parcels") if isinstance(pl, dict) else pl) or []:
                if q.get("id") == "doi" or "土井" in str(q.get("name", "")):
                    src = q.get("poly") or q.get("polygon") or q.get("pts")
                    break
            if src is None:
                bad.append("`parcels.json` に土井の区画が見つからない — 分母の照合ができない")
            elif len(src) != len(d["polygon"]):
                bad.append("区画の頂点数が `parcels.json` と違う(%d ≠ %d)"
                           % (len(src), len(d["polygon"])))
            else:
                w = max(math.hypot(a[0] - b[0], a[1] - b[1])
                        for a, b in zip(src, d["polygon"]))
                if w > 0.05:
                    bad.append("区画の頂点が `parcels.json` と最大 %.3fm ずれる — "
                               "正典は `parcels.json`(規則10)" % w)
        except Exception as e:
            bad.append("`parcels.json` を読めない(%s)" % e)
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
    for k in d["kaidans"] + d.get("ramps", []):
        # ⛔ **落差を手で書かない。** 註は「落差は二つの面の差から算出」と言っていたのに、
        #   実際は手書きの数だった。`K_Genkan.drop` を 4.1→6.0 に書き換えても全検査が
        #   無音で、22段9.9m の石段が下段より 1.9m 低い所へ降りる図が通った
        #   (2026-08-25 検図14巡 中-3)。**結ぶ二つの面から毎回算出する。**
        w = next((x for x in d["terraceWalls"] if x["name"] == k.get("atWall")), None)
        if w is None:
            continue
        vert = abs(w["a"][0] - w["b"][0]) < 1e-9
        c = k.get("gapV") if vert else k.get("gapU")
        if c is None:
            continue
        # ⚠ 走り `run` からは測らない — 往復試験は `run` も剥がすので、剥がした状態で
        #   落差が復元できなくなる(相互に依存させない)。**壁の低い側の段**から測る。
        lo = None
        for ext in [0.3 + 0.25 * i for i in range(28)]:
            pu, pv = (w["a"][0] - ext, c) if vert else (c, w["a"][1] - ext)
            y = design_y(d, pu, pv)
            if y is not None and y < w["coping"] - 0.05:
                lo = y
                break
        if lo is not None:
            k["drop"] = round(w["coping"] - lo, 2)
        elif "drop" not in k:
            raise SystemExit("⛔ %s の落差が算出できない — 壁 %s の低い側に段が無い"
                             % (k["name"], w["name"]))
    for k in d["kaidans"]:
        # ⚠ 蹴上が上限ちょうど(0.300)に張り付くと、丸めが1段ずれた瞬間に違反する。
        #   余裕を見て 1 段多く取る(2026-08-23 検図 L-8)。
        n = max(1, int(math.ceil(k["drop"] / (keri * 0.95) - 1e-9)))
        k["steps"] = n
        # ⭐ **踏面は段ごとに上書きできる**(2026-09-04 検図方 低-6)。既定は `const.fumi`
        #   0.45m だが、**両端が地形と面の縁で固定される石段**では踏面のほうが従属値になる
        #   (CLAUDE.md 蹴上/踏面の項・汐見坂の裁定と同じ理屈)。⛔ 発明ではなく**合わせ込み** —
        #   合わせる先(どの面の縁に足元を載せるか)は当該石段の `_` に書く。
        k["run"] = round(n * float(k.get("fumi", fumi)), 3)
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
        # ⚠ 丁場に**上限**を置く(2026-08-25 検図11巡 中-6: 郭の土留め15本だけ青天井で、
        #   落差が 0.01m 増えれば石垣キットに無い丁場 0.80 を無警告で出していた)。
        _mx = max(max(ds), 0.2)
        _smax = d["const"].get("plinthSMax", 0.75)
        w["tiers"] = max(1, int(math.ceil(_mx / (4.0 * _smax) - 1e-9)))
        w["s"] = round(min(_smax,
                           math.ceil(_mx / w["tiers"] / 4.0 / 0.05) * 0.05), 2)
    return d


# obb_pts / in_obb / obb_overlap の正典は sashizu_lib(2026-08-26 統一で移設)。


def fix_gardens(d):
    """庭の**従属値**を算出して正典へ書き戻す。

    ⚠ `migiwa.bedY`(池の最深部)は `waterY − depthMax` そのもので、**設計値ではない**。
    正典に写しておくと、水面を上げたときに池床だけ古い値で残る(2026-09-04 検図方 中-3)。
    ⛔ 従属値を正典に手で置かない — 生成器が毎回算出し、往復試験に掛ける。
    """
    for g in d.get("gardens", []):
        mg = g.get("migiwa")
        if not mg:
            continue
        mg["bedY"] = round(mg["waterY"] - mg["depthMax"], 6)
    return d


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


IMPL = os.path.join(os.path.dirname(os.path.dirname(DOC)),
                    "Assets", "Edo", "Scripts", "Editor", "EdoSannoKitaBuilder.cs")


MEMO = os.path.expanduser("~/.claude/projects/-Users-toshio-project-edo-unity/memory")
MEMO_FILES = ("doi-sashizu-structure.md", "sannokita-3yashiki.md")


def _ledger_text():
    return open(SRC_MD, encoding="utf-8").read() if os.path.exists(SRC_MD) else ""


def _memo_text():
    out = []
    for f in MEMO_FILES:
        q = os.path.join(MEMO, f)
        if os.path.exists(q):
            out.append(open(q, encoding="utf-8").read())
    return "\n\n".join(out)


def _impl_text():
    """実装(ビルダー)の本文。撤回の照合に掛ける。無ければ空。"""
    return open(IMPL, encoding="utf-8").read() if os.path.exists(IMPL) else ""


HIST_MARK = "経緯はここに書かず git で追う"


def _strip_history(body):
    """図の本文から**改訂の章(git のコミット件名の表)だけ**を落とす。

    ⛔ コミット件名は履歴で書き換えられない(規則4)。撤回の作業を記録した件名は
    必ず禁句を含むので、⚠ **撤回を済ませた瞬間に `retracted_check` が赤くなる**。
    ⛔ 章まるごとの除外リストにしない — 落とすのはこの1章だけで、他は全部照合に掛ける。
    """
    i = body.find(HIST_MARK)
    return body if i < 0 else body[:i]


def moya_rect(d, m):
    """棟の**身舎**の矩形 (u0, v0, u1, v1)[間]。⛔ 足形ではない — 外周に入側 1間 を取った内側。

    ⭕ 入側の幅は `const.moyaBand.irikawa`(2026-08-14 ユーザー裁定=外周に1間)。
    ⚠ **[西川1959]A の原文は『片側に入側』**であって四周入側ではない — 四周に回すのは裁定【U】。
    """
    ir = (d["const"].get("moyaBand") or {}).get("irikawa", 1.0)
    return (m["u0"] + ir, m["v0"] + ir, m["u1"] - ir, m["v1"] - ir)


def fix_bands(x):
    """**身舎を平行な帯に割る**(2026-09-06 ユーザー裁定=案C)。⛔ 従属値なので毎回組み直す。

    ⭐⭐ **2026-09-06 に規則を「整数間」へ決め直した**(考証方 高2 / 普請奉行)。
    ⚠ **江戸間 1間 = 柱の心々**で、**谷は柱通りの上にしか置けない**。
    ⛔ 前の規則(帯の身舎が 3.0間 に最も近くなる帯数)は 2.667 / 3.333間 を生み、
    **谷10本のうち8本が柱通りに乗らなかった** — ⛔ **確度Uの外挿(長屋の梁間)を守るために
    確度Uのユーザー裁定(柱割)を破っていた**。柱割が優先(CLAUDE.md の座標系の不変則)。

    規則は `const.moyaBand` — **帯の身舎は `widths`(4〜5間)の整数**。**`base`(4間)を基本**とし、
    割り切れない棟は **5間で吸う**(⛔ 5間の帯は**端側**へ置く)。**帯数は最小**(谷を増やさない)。
    ⭕ 帯は**大棟と平行**に走り(`bandAlong`)、**境ごとに谷を1本**通す。
    ⛔ **座標は 0.001間・寸法は 0.0001間 で丸める** — 平坦な数値配列は書き戻しで
    有効数字6桁に落ちるので、丸めておかないと往復試験が毎回鳴る。
    """
    C = x["const"]
    mb = C.get("moyaBand")
    if not mb:
        return x
    K, kb, eave = C["ken"], C.get("kawaraKobai"), C.get("gotenEave")
    fl = C.get("gotenFloor", 0.0)
    lo, hi = min(mb["widths"]), max(mb["widths"])
    for m in x["munes"]:
        rf = m.get("roof")
        if not isinstance(rf, dict):
            continue
        rf.pop("bands", None)
        rf.pop("tani", None)
        if not rf.get("banded"):
            continue
        u0, v0, u1, v1 = moya_rect(x, m)
        mu, mv = u1 - u0, v1 - v0
        along = rf.get("bandAlong")                  # None = 未決
        across = {"u": "v", "v": "u"}.get(along)
        span = mv if along == "u" else (mu if along == "v" else min(mu, mv))
        alng = mu if along == "u" else (mv if along == "v" else max(mu, mv))
        ws = None
        if abs(span - round(span)) < 1e-9 and span >= lo:
            sp = int(round(span))
            n9 = -(-sp // hi)                        # 帯数は最小 = ceil(span / 5)
            f9 = sp - lo * n9                        # 5間の帯の本数(端側へ寄せる)
            if 0 <= f9 <= n9:
                ws = [lo] * (n9 - f9) + [hi] * f9
        if ws is None:
            rf["bands"] = {"n": None, "along": along, "across": across,
                           "moyaAcross": round(span, 4), "moyaAlong": round(alng, 4)}
            continue
        n = len(ws)
        rise = [(w * K / 2.0 * kb) if kb else 0.0 for w in ws]
        b0 = (v0 if along == "u" else u0) if along else None
        edges = []
        acc = 0.0
        for w in ws[:-1]:
            acc += w
            edges.append(acc)
        at = ([round(b0 + sum(ws[:i]) + ws[i] / 2.0, 3) for i in range(n)]
              if b0 is not None else None)
        tani = ([round(b0 + e, 3) for e in edges] if b0 is not None else None)
        rf["bands"] = {"n": n, "along": along, "across": across, "ws": ws,
                       "moyaAcross": round(span, 4), "moyaAlong": round(alng, 4),
                       "eaveH": eave,
                       "ridgeH": [round((eave or 0.0) + r, 4) for r in rise],
                       "ridgeG": [round(fl + (eave or 0.0) + r, 4) for r in rise],
                       "ridgeY": [round(m["y"] + fl + (eave or 0.0) + r, 4) for r in rise],
                       "at": at}
        # ⚠ 確度は **U**(2026-09-06 考証方 中5)。⛔ P は「プロジェクト内実測」で、
        #   谷樋の作法は**一般類型**かつ**松江松平の成果物に倣った**もの。
        #   ⛔ 自分の成果物を基準に norm を作らない(規則8)。
        rf["tani"] = {"n": n - 1, "dir": along, "at": tani,
                      "fall": C.get("taniFall"), "cert": "U",
                      "drain": "中央から両端の軒先へ振り分けて落とす(縦樋を立てない)"}
    return x


def mune_ridge_above(d, m, eave):
    """棟の**いちばん高い大棟の高さ**(床からの m)を**設計値から導く**。

    ⭐ 2026-09-06 検図方 中-1。⚠ 従前は `sections[].ridgeAbove` の定数 5.8 を全20面が共有して
    いたが、`munes[].roof.ridge` と `const.kawaraKobai` が入って**設計値から導けるようになった**
    ので、定数で持つのは二重管理(規則4)。⛔ 定数を手で書き換えない。

    起り = **梁間 ÷ 2 × 瓦勾配**。⭐ 帯に割った棟の梁間は**帯の身舎**(`roof.bands.ws`)であって
    足形の辺ではない。⚠ **帯の幅は棟の中で一様ではない**(4間と5間が混ざる)ので、
    ここが返すのは**最も高い帯**。⛔ 図枠の天地と断面の頂はこの値でよいが、
    **帯ごとの高さは `bands.ridgeH` を引く**(⛔ 最大値で全部の帯を描かない)。
    ⛔ **これは図示のための見込み【P】** — 屋根部材の実測があるときはそちらが正。
    """
    rf = m.get("roof") or {}
    bd = rf.get("bands") or {}
    kb = d["const"].get("kawaraKobai")
    if bd.get("ridgeH"):
        return max(bd["ridgeH"])
    a, b = m["u1"] - m["u0"], m["v1"] - m["v0"]
    r = rf.get("ridge")
    beam = (b if r == "u" else a) if r in ("u", "v") else min(a, b)
    return eave + (beam * d["const"]["ken"] / 2.0 * kb if kb else 0.0)


def svc_roof(d, o):
    """**附属屋の屋根の高さ**(その物の `y` からの m)を (軒高, 棟高) で返す。

    ⚠ 2026-09-06 検図方 中1: **断面20面が `service` を一律 `eaveAbove` 3.4 + 御殿の勾配で
    描いており、`const.kuraEave` 4.84 / `kuraRidge` 6.867 を使っていなかった**
    (蔵を 1.979m 低く描いていた)。⛔ 御殿の軒高を附属屋へ当てない。
    ⭕ 引き先は物の `roofRef`(`const._svcRoof` が正典)。⛔ 生成器に無名の対応表を置かない。
    ⚠ **軒高が実測で入っている附属屋は無い**ので、そこは瓦勾配からの逆算【P+U】。
    """
    C = d["const"]
    kb = C.get("kawaraKobai") or 0.0
    ref = o.get("roofRef")
    if ref == "kura":
        return (C["kuraEave"], C["kuraRidge"])
    if ref == "kachu":
        # ⭐⭐ **家中長屋は平家**(2026-09-06 考証方 高2)。[西川1959]A「外周部は、二階瓦葺窓付の
        #   長屋がめぐらされ、**邸内には平家建の長屋が密接して建並んでいた**」。
        #   ⛔ `const.nagayaRidge`(5.509)は**二階建の表長屋の部材実測**なので流用しない。
        #   ⭕ **軒高を置いて棟高を導く**(⛔ 棟高を置いて軒高を逆算しない)。
        ev = C["kachuEave"]
        beam = o.get("D", min(o["u1"] - o["u0"], o["v1"] - o["v0"]))
        return (ev, ev + beam * C["ken"] / 2.0 * kb)
    if ref == "inari":
        rg = C["inariRidge"]
        beam = min(o["u1"] - o["u0"], o["v1"] - o["v0"])
    elif ref == "nagaya":
        rg = C["nagayaRidge"]
        beam = o.get("D", min(o["u1"] - o["u0"], o["v1"] - o["v0"]))
    else:
        return (None, None)
    return (rg - beam * C["ken"] / 2.0 * kb, rg)


def mune_roof_pts(d, m, coord, eave):
    """断面に描く**屋根の折れ線**[(横軸の座標[間], 床からの高さ[m])]。

    ⭐ 2026-09-06 ユーザー裁定=案C。帯に割った棟は、**切り口が帯を横切る面**では
    **帯の数だけ頂**が立ち、**境ごとに谷**が落ちる。**切り口が帯に沿う面**では
    稜線が身舎の上を平らに走る。⛔ 足形の中央に一つだけ頂を立てない。
    ⚠⚠ **帯の幅は棟の中で一様ではない**(4間と5間が混ざる)ので、**頂の高さは帯ごとに違う**。
    ⚠ 帯の向きが未決の棟は、いちばん高い帯の稜線の平ら(包絡)で描く。

    ⭐⭐ **2026-09-06 検図方 中3・低6 で二つ足した**:
      ① **入側の上を勾配で描く**(`const.gesyaKobai`)。⚠ 従前は入側1間が**標高 3.4 の水平
         =陸屋根**に描かれていた。軒先高 = `gotenEave` − 入側 × `ken` × 勾配。
         ⛔ **「下屋」と呼ばない**(2026-09-06 部材方の試し焼き)— 母屋と同勾配なので
         **身舎の流れがそのまま延びた一枚の平面**になり、⛔ **段のある庇ではない**。
      ② **軒の出 `const.nokiDe` を描く**。⚠ 従前は足形の縁で切れており、
         **棟どうしの当たりを見る唯一の図なのに 0.836m の食い込みが読めなかった**。
    """
    C = d["const"]
    rf = m.get("roof") or {}
    bd = rf.get("bands") or {}
    a0 = m["u0"] if coord == "u" else m["v0"]
    b0 = m["u1"] if coord == "u" else m["v1"]
    K = C["ken"]
    ir = (C.get("moyaBand") or {}).get("irikawa", 1.0)
    gk = C.get("gesyaKobai") or 0.0
    nk = _overhang(d, m) - C.get("tsumaEnd", 0.0)      # 軒の出だけ(妻の出は桁行の話)
    ridge = mune_ridge_above(d, m, eave)
    if not bd.get("n"):
        # 帯に割らない棟 — 一枚の屋根。⛔ 軒の出は描く(低6)
        return [(a0 - nk / K, eave - nk * gk), (a0, eave),
                ((a0 + b0) / 2.0, ridge), (b0, eave), (b0 + nk / K, eave - nk * gk)]
    r0, s0, r1, s1 = moya_rect(d, m)
    m0, m1 = (r0, r1) if coord == "u" else (s0, s1)
    ge = eave - ir * K * gk                            # 入側の先(足形の縁)。⛔ 段は付けない
    tip = ge - nk * gk                                 # 軒の出の先
    head = [(a0 - nk / K, tip), (a0, ge)]
    tail = [(b0, ge), (b0 + nk / K, tip)]
    if bd.get("across") == coord and bd.get("at"):
        ws, hs = bd["ws"], bd["ridgeH"]
        pts = list(head) + [(m0, eave)]
        acc = m0
        for i, w in enumerate(ws):
            pts.append((acc + w / 2.0, hs[i]))         # 帯の大棟(高さは帯ごと)
            acc += w
            if i < len(ws) - 1:
                pts.append((acc, eave))                # 谷
        return pts + [(m1, eave)] + tail
    return head + [(m0, ridge), (m1, ridge)] + tail


def svc_roof_pts(d, o, coord, a0, b0):
    """附属屋の屋根の折れ線(その物の `y` からの高さ)。⛔ 御殿の勾配で描かない。"""
    ev, rg = svc_roof(d, o)
    if ev is None:
        return None
    C = d["const"]
    nk = _overhang(d, o) - C.get("tsumaEnd", 0.0)
    gk = C.get("gesyaKobai") or 0.0
    return [(a0 - nk / C["ken"], ev - nk * gk), (a0, ev),
            ((a0 + b0) / 2.0, rg), (b0, ev), (b0 + nk / C["ken"], ev - nk * gk)]


def obb_chord(o, axis, at):
    """回転物を切り線(`axis`=u なら u=at)で切った**弦**を返す。⛔ 外接矩形で切らない。

    ⚠ 2026-09-06 検図方 中2: 断面が回転した家中長屋を **AABB で切っていた**
    (梁間が最大 2.842間 過大・棟が +1.16m)。
    """
    P = obb_pts(o)
    i0, i1 = (0, 1) if axis == "u" else (1, 0)
    xs = []
    n = len(P)
    for i in range(n):
        p, q = P[i], P[(i + 1) % n]
        if (p[i0] - at) * (q[i0] - at) > 0 or p[i0] == q[i0]:
            continue
        t = (at - p[i0]) / (q[i0] - p[i0])
        xs.append(p[i1] + (q[i1] - p[i1]) * t)
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def _clipx(pts, w0, w1):
    """折れ線(**横軸について単調増加**)を [w0, w1] に切り詰める。境では線形に内挿する。"""
    out = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x2 < w0 or x1 > w1:
            continue

        def _y(xq, x1=x1, y1=y1, x2=x2, y2=y2):
            return y1 if abs(x2 - x1) < 1e-12 else y1 + (y2 - y1) * (xq - x1) / (x2 - x1)

        xa = max(x1, w0)
        xb = min(x2, w1)
        for xq in (xa, xb):
            q = (xq, _y(xq))
            if not out or abs(out[-1][0] - q[0]) > 1e-9 or abs(out[-1][1] - q[1]) > 1e-9:
                out.append(q)
    if not out:
        out = [(max(w0, min(w1, pts[0][0])), pts[0][1])]
    return out


def retracted_check(d, texts):
    """**撤回した説の語が、設計値・生成器・図のどこかに生き残っていないか**を機械で照合する。

    3巡続けて「文章だけ直って図と正典に撤回済みの説が残る」再発をした(2026-08-24 考証第5巡)。
    禁句は設計値の `retracted` に置く。撤回の記録そのもの(「〜は反証された」の文脈)は
    別の語で書くこと。

    ⭐⭐ **2026-09-06 検図方 高2 で免除の粒度を段落から「禁句のすぐ前」へ狭めた。**
    ⚠⚠ **段落に印が1つでもあれば段落中の禁句を全部見逃していた** — `_pending` や `roof._` は
    **一つの巨大な段落**で、無関係な「⛔ ここに数字を写さない」が必ず入るため、
    **現行の主張として書かれた禁句が丸ごと赦されていた**(実測: 禁句の出る11段落が
    **免除11・報告0**、うち正当な撤回記録は3段落だけ)。
    ⇒ ① **免除は印が禁句を直接修飾しているときだけ**(直前 `MARK_NEAR` 文字の窓)
       ② **文(`。`)でも割る**(1項=1段落にしない)
       ③ **免除した件数を必ず刷る**(0件と未実行を見分ける=規則19)。
    """
    MARK = ("⛔", "撤回", "誤り", "反証", "旧記", "採らない", "採用しない", "禁句",
            "落とした", "廃した", "訂正", "失効", "二次資料", "決め直した", "改めた", "置き直した",
            "岡部筑前守の条")   # ⭐ 帰属を明記した文は「当家の説」ではない(禁句表の作法)
    MARK_NEAR = 80                      # 禁句の**直前**この文字数に印があれば撤回の記録とみなす
    # ⚠⚠ **厳しい方の物差しは当邸の成果物にだけ当てる。**
    #   ⛔ `台帳`(`sources.md`)と`メモリ`は**別の役の正典**で、当方は書き換えられない
    #   (規則: 検分役の覚え書きと同じ理屈)。そこは従来どおり**段落**単位で免除する。
    #   ⭕ 当邸の 設計値 / 図 / 文章 / 実装 は**文**で割り、**印が禁句を直接修飾するときだけ**赦す。
    #   ⛔ **`生成器` は OWN に入れない** — 禁句の**定義と説明そのもの**が本文に載る面なので、
    #   厳しい窓を当てると「撤回した説を説明している行」が全部鳴る(2026-09-06 検図方 9)。
    OWN = ("設計値", "図", "文章", "実装")
    bad = []
    marked = 0
    for label, t in texts:
        strict = label in OWN
        # ⛔ 空行だけで割らない — 句点でも割る(⚠ 巨大な一段落に免除が効いてしまう)
        parts = re.split(r"\n\s*\n|(?<=。)", t) if strict else re.split(r"\n\s*\n", t)
        for para in parts:
            for w in d.get("retracted", []):
                i = para.find(w)
                while i >= 0:
                    win = (para[max(0, i - MARK_NEAR):i] + para[i + len(w):i + len(w) + 24]
                           if strict else para)
                    if any(mk in win for mk in MARK):
                        marked += 1     # 撤回の記録として許す
                    else:
                        bad.append("撤回済みの語「%s」が %s に残っている"
                                   "(%s に撤回の印が無い)— …%s…"
                                   % (w, label,
                                      ("直前 %d 文字" % MARK_NEAR) if strict else "同じ段落",
                                      re.sub(r"\s+", " ", para[max(0, i - 40):i + len(w) + 20])))
                    i = para.find(w, i + 1)
    d["_retractedMarked"] = marked                  # 印つき出現の数。増減だけ見張る
    return sorted(set(bad))


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
    g = _sv(pr.W, pr.H, "土井大隅守上屋敷 現況図(現代の地面=地盤の正本)")
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


def _recon_max(world, base):
    """復元が正本から離れた最大量(m)。図に出す数を文章へ書かないため。"""
    mx = 0.0
    for iz in range(min(world["nz"], base["nz"])):
        for ix in range(min(world["nx"], base["nx"])):
            a, b = world["h"][iz][ix], base["h"][iz][ix]
            if a is not None and b is not None:
                mx = max(mx, abs(a - b))
    return mx


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
        w = next((x for x in d["terraceWalls"] if x["name"] == k["atWall"]), None)
        if w is None:
            continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
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
        ter_r = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
        dem_r = load_terrain(os.path.join(DOC, "doi_dem.json"))
        we_r = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
        gr_r = RGrid(d)

        def _ry(u, v):
            # ⚠ **斜路と石段は段より先に見る。** 段の中を通るので、`design_y` を先に引くと
            #   段の高さに隠れて**斜路がどこにも存在しないことになる**
            #   (2026-08-25 検図11巡 中-1)。
            y = ramp_y(d, u, v)
            if y is not None:
                return y
            y = stair_y(d, u, v)
            if y is not None:
                return y
            y = design_y(d, u, v)
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
        # ⚠ **折れ点だけで測らない。** 端点間の勾配は途中の急な所を平均で薄める
        #   (2026-08-25 検図10巡 中-3: 表に 1:6.2 と出るが 3m 窓では 1:4.3)。
        WIN = 3.0
        prof = []; acc = 0.0
        for a, b in zip(r["pts"], r["pts"][1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            n_w = max(2, int(seg / 0.05))
            for i in range(1, n_w + 1):
                u = a[0] + (b[0] - a[0]) * i / n_w
                v = a[1] + (b[1] - a[1]) * i / n_w
                acc += seg / n_w * K
                y = _ry(u, v)
                if y is not None:
                    prof.append((acc, y))
        steepest = None; j = 0
        for i in range(len(prof)):
            while prof[i][0] - prof[j][0] > WIN:
                j += 1
            dl = prof[i][0] - prof[j][0]; dh = abs(prof[i][1] - prof[j][1])
            if dl < WIN * 0.9 or dh < 0.05:
                continue
            gsl = dl / dh
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
                w = next((x for x in d["terraceWalls"] if x["name"] == k["atWall"]), None)
                if w is None:
                    continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
                if w["a"][0] == w["b"][0]:
                    cu, cv = w["a"][0], k["gapV"]
                else:
                    cu, cv = k["gapU"], w["a"][1]
                if min(a[0], b[0]) - 1.2 <= cu <= max(a[0], b[0]) + 1.2 and \
                   min(a[1], b[1]) - 1.2 <= cv <= max(a[1], b[1]) + 1.2:
                    hitk.add(k["name"])
        steps = sum(k["steps"] for k in d["kaidans"] if k["name"] in hitk)
        if steepest:
            updn += " ／ 3m窓の最急 1:%.1f%s" % (steepest, "(石段を含む)" if steps else "")
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
    # ⭐ **庭も交差の一覧に入れる**(2026-09-04 検図方 低-4)。断面の地表は `ground_y` が
    #   庭の池床・築山を描くので、**何を切っているかの列挙に庭が無いと注記が図と食い違う**。
    gar = sorted([g0 for g0 in d.get("gardens", []) if hits(g0)], key=key)
    if gar:
        parts.append("庭: " + "・".join(
            (g0.get("label", g0["name"]) + ("(池・築山)" if g0.get("migiwa") else ""))
            for g0 in gar))
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
        """造成後の地表 — 段の中は段の高さ、外は法面で現地形へ摺り付く。
        ⭐ **奥庭の矩形の中では池床・築山を描く**(`ground_y`)。⚠ 従前は `graded_y` だけを
        読んでいたので、**断面⑪⑳ が庭の中を平らな面 26.60 で通っていた**(検図方 高-2)。
        """
        ny = nat_y(w)
        u9, v9 = uv_at(w)
        gy = ground_y(d, u9, v9, ny, we9)
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
        if not ((sec["axis"] == "u" and m["u0"] <= at <= m["u1"])
                or (sec["axis"] == "v" and m["v0"] <= at <= m["v1"])):
            continue
        # ⭐ 天地も**建物ごとの棟高**から(2026-09-06 検図方 中1)。⛔ 御殿の勾配で附属屋を測らない。
        if m.get("roofRef"):
            _, rg9 = svc_roof(d, m)
            tops.append(m["y"] + (rg9 or 0.0))
        elif (m.get("roof") or {}).get("ridgeH") is not None:
            tops.append(m["y"] + m["roof"]["ridgeH"])
        else:
            tops.append(m["y"] + fl0 + mune_ridge_above(d, m, sec["eaveAbove"]))
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
        w = next((x for x in d["terraceWalls"] if x["name"] == rp["atWall"]), None)
        if w is None:
            continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
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
        w = next((x for x in d["terraceWalls"] if x["name"] == k["atWall"]), None)
        if w is None:
            continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
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
    # ⭐ **大棟の高さは棟ごとに設計値から導く**(2026-09-06 検図方 中-1)。
    #   ⛔ `sections[].ridgeAbove` の定数(5.8)は廃した — `roof.ridge` と
    #   `const.kawaraKobai` から出るようになった以上、定数で持つのは二重管理(規則4)。
    eave = sec["eaveAbove"]
    fl = d["const"]["gotenFloor"]
    for m in d["munes"] + d["service"]:
        cd = "v" if sec["axis"] == "u" else "u"
        if "yaw" in m:
            # ⭐ **回転物は OBB の弦で切る**(2026-09-06 検図方 中2)。
            #   ⛔ 外接矩形で切ると梁間が最大 2.842間 過大になり、棟が +1.16m 高く描かれる。
            ch = obb_chord(m, sec["axis"], at)
            if ch is None:
                continue
            a, b = ch
        elif sec["axis"] == "u":
            if not (m["u0"] <= at <= m["u1"]):
                continue
            a, b = m["v0"], m["v1"]
        else:
            if not (m["v0"] <= at <= m["v1"]):
                continue
            a, b = m["u0"], m["u1"]
        if b <= w0 or a >= w1:
            continue                          # 画枠の外(検図 H-2)
        nm = MUNE_JA.get(m.get("name"), m.get("label", m.get("name", "")))
        if "label" in m and m["name"] not in MUNE_JA:
            nm = m["label"]
        # ⭐ **屋根の見え掛かりは建物ごとに引く**(2026-09-06 ユーザー裁定=案C / 検図方 中1・中3・低6)。
        #   ⛔ 足形の中央に一つだけ頂を立てない・⛔ 附属屋へ御殿の軒高と勾配を当てない。
        if m.get("roofRef"):
            f = m["y"]                        # 附属屋は地盤から(⛔ 御殿の床上げを足さない)
            prof = svc_roof_pts(d, m, cd, a, b)
        elif (m.get("roof") or {}).get("ridgeH") is not None:
            f = m["y"]                        # 部材実測の棟(厩)も地盤から
            rf9 = m["roof"]
            nk9 = _overhang(d, m) - d["const"].get("tsumaEnd", 0.0)
            gk9 = d["const"].get("gesyaKobai") or 0.0
            prof = [(a - nk9 / d["const"]["ken"], rf9["eaveH"] - nk9 * gk9), (a, rf9["eaveH"]),
                    ((a + b) / 2.0, rf9["ridgeH"]), (b, rf9["eaveH"]),
                    (b + nk9 / d["const"]["ken"], rf9["eaveH"] - nk9 * gk9)]
        else:
            f = m["y"] + fl
            prof = mune_roof_pts(d, m, cd, eave)
        if prof is None:
            continue
        prof = _clipx(prof, w0, w1)
        a, b = max(a, w0), min(b, w1)
        g.append('<polygon points="%s" fill="var(--ink-mid)" stroke="var(--ink)" stroke-width="1.2"/>'
                 % " ".join("%.1f,%.1f" % q for q in
                            [(X(prof[0][0]), Y(f))]
                            + [(X(px), Y(f + py)) for px, py in prof]
                            + [(X(prof[-1][0]), Y(f))]))
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
    g.append(T(4, H - 34, "水平は間グリッド沿い/垂直は %.1f 倍に強調。屋根の起りは設計値からの見込み【P】(梁間÷2×瓦勾配)・実装の高さは部材が正。"
               "視線は %s" % (ex, "南を向く(左=東の道／右=西の奥)" if sec["axis"] == "u"
                              else "西を向く(左=南の岡部境／右=北の松平境)"), "anS2", "start"))
    g.append(T(4, H - 20, "── 実線=造成後の地盤　┄┄ 破線=<b>江戸期の復元地盤</b>(手順U / 根拠A+B)。"
               "その間の**暖色=盛土／寒色=切土**(濃いほど厚い)。"
               "段の外は法面(盛土1:%.1f/切土1:%.1f)で現地形へ摺り付ける"
               % (d["const"].get("batterFill", 1.5), d["const"].get("batterCut", 1.0)),
               "anS2", "start"))
    g.append(T(4, H - 6, "太い緑帯=**無造成**(現地形をそのまま使う区間)。"
               "石垣ハッチ=土留め(露出高は地盤なりに変わる)", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 外周の展開
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
    g.append(T(4, H - 22, "展開の起点=P3(ジョグ南端)— 当家所有の三辺(ジョグ→楔→東辺)を一続きに読む。"
               "天端は run ごとに一定、段は継ぎ目で落とす。表長屋 桁高 %.1fm/練塀 %.2fm。"
               "破線=道の地盤(実測)/石垣ハッチ=基壇" % (nagH, dob), "anS2", "start"))
    g.append(T(4, H - 8, "東辺の道は南へ落ちる — 表長屋(南)と練塀の基壇石垣が道へ露出する(台地肩)。"
               "楔→東辺の隅(P5)は天端同高で納め、ジョグ→楔(P4)の小さな段は高い側の基壇小口で受ける", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 表門まわり
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
    g.append(T(4, 15, "正面見付(概略・等倍)。型式=長屋門【B】/屋根=切妻【B】/番所と潜戸=[下丸子武家屋敷門]A の官製「片番所格子付、片潜門」【B/U・型式をまたぐ移植】/石高帯: 掲示の記載=A / 当てはめ=B / 採用=U/実在と被災=S", "anS"))
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


def mune_fit(d, o, dem=None):
    """棟の下の |設計面 − 自然地形| を実測して (最大Δ, 超過率%) を返す。§B-1 の合否そのもの。

    ⚠ **地形は原資料の DEM を双一次で引く。** `ter["at"]` は 1間(1.818m)格子の**最近傍**で、
    実効解像度がそれに縛られる。補間法で超過率が動くため、**合否が補間法だけで決まる状態を残さない**
    (2026-08-24 検図 中-4。実測値は図の棟の表が持つ)。
    **合否が補間法だけで決まる状態を残さない。**
    """
    # ⚠ かつて `ter`(回転間格子)を受けていたが、**null 判定にしか使っておらず**
    #   実際に引くのは常に世界2m格子の復元地盤だった(2026-08-25 検図13巡 低-5)。
    #   引数に在ると「回転格子を見ている」と読めてしまうので落とした。
    if dem is None:
        # ⚠ 棟の切盛は**江戸期の復元地盤**に対して測る(2026-08-25)。
        #   現代の地面(正本)で測ると、近代の掘削跡を「自然地形」として合否を出すことになる。
        dem = load_terrain(os.path.join(DOC, "doi_edo_world.json"))
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
        ft = mune_fit(d, m)
        fitc = "—" if ft is None else ("%+.2f m / %.0f%%" % ft if ft[1] > 0 else "%+.2f m / 0%%" % ft[0])
        rows.append("<tr><td>%s</td><td><code>%s</code></td><td>%s</td><td>%g×%g間</td>"
                    "<td>%.0f m²</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td></tr>"
                    % (MUNE_JA.get(m["name"], m["name"]), m["name"], m["zone"], kw, kd,
                       area, len(m["rooms"]), tat, ("%d 間²" % ita) if ita else "—", fitc))
    return ('<div class="tw"><table><thead><tr><th>棟</th><th>名</th><th>ゾーン</th><th>外形</th>'
            "<th>面積</th><th>室数</th><th>畳数計(座敷)</th><th>土間・板敷</th><th>切盛の最大Δ / ±0.5m超の割合</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def runs_table(d):
    rows = []
    for r in d["runs"]:
        if r.get("base") == "Ishigaki" and "s" in r:
            base = ("石垣 丁場%.2f×%d段築(壁高%.2fm)" % (r["s"], r["tiers"], 4 * r["s"] * r["tiers"])
                    if r.get("tiers", 1) > 1 else
                    "石垣 丁場%.2f(壁高%.2fm)" % (r["s"], 4 * r["s"]))
            base += " / 露出 %.2fm" % r.get("expose", 0.0)
        else:
            base = "石垣" if r.get("base") else "—"
        rows.append("<tr><td><code>%s</code></td><td>辺%d</td><td>%.0f–%.0f</td><td>%.1fm</td>"
                    "<td>%s</td><td>%.1f</td><td>%s</td><td>%s</td></tr>"
                    % (r["name"], r["edge"], r["s0"], r["s1"], r["s1"] - r["s0"],
                       "表長屋" if r["kind"] == "Nagaya" else "練塀", r["seat"], base,
                       "整地" if r.get("bench") else "—"))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>辺</th><th>走り s</th><th>長さ</th>'
            "<th>種別</th><th>天端 seat</th><th>基壇石垣</th><th>外周帯</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>"
            "<p class='cap'>⚠ <b>基壇石垣の丁場と段数は生成器が算出する</b> — 街路側の地盤から"
            "露出を測り、丁場の上限(<code>const.plinthSMax</code>)を超える露出は<b>段築</b>にする。"
            "<b>段数は部材の丁場上限からの従属値【U】で、段築を支える史料は台帳に無い</b>"
            "(露出高は地形実測=P)。</p></div>")


def walls_table(d):
    rows = []
    for w in d["terraceWalls"]:
        gk = "gapU" if "gapU" in w else ("gapV" if "gapV" in w else None)
        if gk:
            op = "%s=%.2f 幅 %.2f間(%.2fm)" % (gk[-1].lower(), w[gk], 2 * w["gapHalf"],
                                              2 * w["gapHalf"] * d["const"]["ken"])
            sd = ("袖 %.2f間(%.2fm)" % (w["sode"]["len"], w["sode"]["len"] * d["const"]["ken"])
                  if "sode" in w else "<b>袖なし</b>")
        else:
            op, sd = "—", "—"
        rows.append("<tr><td><code>%s</code></td><td>(%g,%g)-(%g,%g)</td><td>%.1f</td><td>%.2f</td>"
                    "<td>%.1f / %.2f / %.2f</td><td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (w["name"], w["a"][0], w["a"][1], w["b"][0], w["b"][1],
                       w["coping"], w["s"], 4.0 * w["s"] * w.get("tiers", 1),
                       1.4 * w["s"], 2.4 * w["s"], op, sd))
    return ('<div class="tw"><table><thead><tr><th>土留め</th><th>グリッド</th><th>天端</th><th>s</th>'
            "<th>壁高/天端幅/底厚</th><th>開口</th><th>袖石垣</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>"
            "<p class='cap'>⚠ <b>開口の芯と幅、袖石垣の長さは生成器が算出する</b> — 開口は"
            "石段・斜路・廊下が通るために開いており、高い側の土は両端で<b>直角に振れる袖石垣</b>が受ける。"
            "袖が立たない開口は <code>opening_fit_check</code> が不適合として出す。</p></div>")


def gate_area_note(d):
    """建蔽率の「門の躯体+木戸」の**出所**を算出して出す(`_pending.kenpei` の残作業)。

    ⚠ 門の躯体と表長屋の run が**同じ辺の同じ帯**にあるので、二重に数えていないことを
    数字で示さないと読者が検算できない。手で書かず毎回測る。
    """
    gp = d["gate"]["plan"]
    bs = gp["bansho"]
    mon = gp["monW"] * gp.get("monD", 1.2)
    sode = 2 * gp.get("sode", 0) * 0.4
    komon = sum(k["w"] * 1.2 for k in d["komon"])
    ban = bs["count"] * bs.get("w", 0) * bs.get("d", 0)
    g0, g1 = d["gate"]["s"] - gp["monW"] / 2, d["gate"]["s"] + gp["monW"] / 2
    ov = 0.0
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        ov += max(0.0, min(g1, r["s1"]) - max(g0, r["s0"]))
    return ("<p class='cap'><b>「門の躯体+木戸」の出所</b>: 躯体 %.2f×%.2f=<b>%.1f m²</b>"
            " ／ 袖塀 %.1f m² ／ 木戸・通用門 %s = %.1f m² ／ 番所 %.1f m²"
            "(<b>長屋門は番所が躯体内</b>なので別計上しない)= 計 <b>%.1f m²</b>。<br>"
            "⚠ <b>表長屋の行と二重に数えていない</b> — 門の桁行は辺の s%.2f〜%.2f を占め、"
            "表長屋の run はその手前 s%.2f で切れ、その先 s%.2f から再開する"
            "(重なり <b>%.2f m</b>)。数値は毎回測る。</p>"
            % (gp["monW"], gp.get("monD", 1.2), mon, sode,
               " + ".join("%.2f×1.2" % k["w"] for k in d["komon"]), komon, ban,
               mon + sode + komon + ban, g0, g1,
               max((r["s1"] for r in d["runs"] if r["kind"] == "Nagaya" and r["s1"] <= g0 + 1e-6),
                   default=0.0),
               min((r["s0"] for r in d["runs"] if r["kind"] == "Nagaya" and r["s0"] >= g1 - 1e-6),
                   default=0.0),
               ov))


def gate_overlap_check(d):
    """門の躯体と表長屋の run が**重なっていないか**。重なれば建蔽率が二重に数える。"""
    gp = d["gate"]["plan"]
    g0, g1 = d["gate"]["s"] - gp["monW"] / 2, d["gate"]["s"] + gp["monW"] / 2
    bad = []
    for r in d["runs"]:
        if r["kind"] != "Nagaya":
            continue
        ov = min(g1, r["s1"]) - max(g0, r["s0"])
        if ov > 1e-6:
            bad.append("門の躯体(s%.2f〜%.2f)と表長屋 %s(s%.2f〜%.2f)が %.2fm 重なる — "
                       "建蔽率が二重に数える" % (g0, g1, r["name"], r["s0"], r["s1"], ov))
    return bad


def kenpei(d, area):
    """正典は sashizu_lib.kenpei(当邸の実装をそのまま基準にした)。行ラベルだけが当邸の値。"""
    return sashizu_lib.kenpei(
        d, area, TSUBO,
        svc_label="付属屋(家中長屋・米蔵・土蔵・稲荷)",
        nagaya_label="表長屋(奥行%.1fm)" % d["const"]["nagayaD"],
        ban_label="門の躯体(番所を含む)+木戸")


def stair_bank_check(d, dem):
    """**石段の帯の側面**に受けがあるか。石段は地山の上に立つ土手になりうる。

    `edge_step_check` は段(terrace)の縁しか回らないので、石段の帯は**構造的に検査の外**だった
    (2026-08-25 検図13巡 中-1: K_Genkan の掘割の外 0.10間で 踏面−地盤 が最大 2.68m)。
    """
    if dem is None:
        return _unmeasured("stair_bank_check", "doi_edo_world.json")
    K = d["const"]["ken"]
    gr = RGrid(d)
    we = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
    lim = d["const"].get("stairBankMax", 1.5)
    bad = []
    for k in d["kaidans"]:
        w = next((x for x in d["terraceWalls"] if x["name"] == k.get("atWall")), None)
        if w is None:
            continue
        vert = abs(w["a"][0] - w["b"][0]) < 1e-9
        gk = "gapV" if vert else "gapU"
        c = k.get(gk)
        if c is None:
            continue
        hw = k["w"] / K / 2.0
        line = w["a"][0] if vert else w["a"][1]
        rn = k["run"] / K
        worst = 0.0
        need = 0.0                              # 受けが要る走り長(壁線からの m)
        for i in range(21):
            t = i / 20.0
            for side in (-1.0, 1.0):
                if vert:
                    u = line - rn * t
                    v = c + side * (hw + 0.10)
                else:
                    u = c + side * (hw + 0.10)
                    v = line - rn * t
                tread = w["coping"] - k["drop"] * t
                x, z = gr.W(u, v)
                # ⚠ 側面の地盤に `graded_y` を使わない。`graded_y` は `stair_y` を含むので、
                #   石段の法が横へ滲む所では**踏面を踏面と比べる**ことになり、恒真で 0.00 を返す
                #   (K_Genkan がそれで見えなかった)。受けになりうるのは**段の設計面**か**地山**だけ。
                g = design_y(d, u, v)
                if g is None:
                    g = dem_bilinear(dem, x, z)
                if g is not None:
                    worst = max(worst, tread - g)
                    if tread - g > lim:
                        need = max(need, k["run"] * t)
        f = k.get("flank")
        if worst <= lim:
            continue
        if f is None:
            bad.append("石段 %s の帯の側面に %.2fm の土手が立つ(上限 %.2fm)— "
                       "側石垣 `flank` が設計値に無い" % (k["name"], worst, lim))
            continue
        # ⛔ **在ることだけを見ない。** 走りの長さしか見ていなかったので、
        #   `s`=0.05 / `tiers`=0(壁高 0.2m)で 2.56m の土手を受ける宣言が通り、
        #   `{"run": 999}` の空箱でも通った(2026-08-25 検図14巡 中-1)。
        for key in ("run", "s", "tiers"):
            if f.get(key) is None:
                bad.append("石段 %s の側石垣に %s が無い" % (k["name"], key))
        if f.get("s") is None or f.get("tiers") is None:
            continue
        h = 4.0 * f["s"] * f["tiers"]
        if h + 1e-6 < worst:
            bad.append("石段 %s の側石垣が低い — 壁高 %.2fm(s=%.2f×%d段)で "
                       "%.2fm の土手は受けられない" % (k["name"], h, f["s"], f["tiers"], worst))
        # 註は「**走りの全長に**側石垣を返す」と言っている。字義どおり測る
        # (上限超えの区間だけで足りるとすると、註と実装が別のことを言う)。
        if abs(f.get("run", 0.0) - k["run"]) > 1e-6:
            bad.append("石段 %s の側石垣の走り %.2fm が石段の走り %.2fm と違う — "
                       "註は走りの全長に返すと言っている(上限超えは %.2fm まで)"
                       % (k["name"], f["run"], k["run"], need))
    return bad


def fix_wall_exposure(d, ter):
    """走りに沿った**露出の分布**を土留めへ書き戻す。

    ⚠ `fix_walls` の中でやると、開口の幅 `gapHalf` が**同じパスで後から決まる**ため、
    往復試験で平均が 0.03m 揺れて収束しなかった(2026-08-25)。**開口が確定した後**に回す。
    """
    if ter is None:
        return d
    OFF = 0.45
    K = d["const"]["ken"]
    lim = d["const"].get("wallEndFillMax", 0.5)
    for w in d["terraceWalls"]:
        (au, av), (bu, bv) = w["a"], w["b"]
        L = math.hypot(bu - au, bv - av) or 1.0
        nu_, nv_ = (bv - av) / L, -(bu - au) / L
        gk = "gapU" if abs(au - bu) > 1e-9 else "gapV"
        inset = min(0.45, 0.4 * L) / L
        ds = []
        for i in range(41):
            t = inset + (1.0 - 2.0 * inset) * i / 40.0
            u, v = au + (bu - au) * t, av + (bv - av) * t
            if gk in w:
                pos = u if gk == "gapU" else v
                if abs(pos - w[gk]) <= w.get("gapHalf", 1.0):
                    continue
            best = None
            for sg in (1.0, -1.0):
                pu, pv = u + nu_ * OFF * sg, v + nv_ * OFF * sg
                g = design_y(d, pu, pv)
                if g is None:
                    g = ter["at"](pu, pv)
                if g is not None:
                    best = g if best is None else min(best, g)
            if best is not None:
                ds.append(w["coping"] - best)
        if not ds:
            w.pop("_exposure", None)
            w.pop("_endLow", None)
            continue
        w["_exposure"] = [round(min(ds), 2), round(sum(ds) / len(ds), 2), round(max(ds), 2)]

        def _tail(seq):
            n = 0
            for e in seq:
                if e <= lim:
                    n += 1
                else:
                    break
            return round(n * L * K / max(1, len(seq) - 1), 2)
        w["_endLow"] = [_tail(ds), _tail(ds[::-1])]
    return d


# ─────────────────────────────────────────────────────────────────────────────
# ⚠ **地盤の面は2つある。読み分けの理由をここに1箇所で書く**(2026-08-25 検図14巡 低-3)。
#
#   `doi_edo_world.json` / `doi_edo_dem.json` = **江戸期の復元地盤**
#     → 棟の接地(§B-1)・石段の帯・土留めの端と露出・断面の地盤線・切盛
#       理由: 江戸の屋敷は江戸の地面の上に建つ。近代の掘削跡を「自然地形」として
#             合否を出さないため。
#
#   `doi_dem.json`(= `base_dem.json` の切り出し)= **現代の地面(正本)**
#     → 段の縁・土留めの要否・**境界の埋没と基壇**・辺の地盤線・外周の基壇の丁場
#       理由: **境界は両家が同じ面を読むことが要件**(司令塔 08-24 通達)。
#             隣家がどう復元するかに当家の境界設計を依存させない。
#
#   ⚠ 復元の箱は TW_GenkanS / TW_GenkanE / TW_ShuG に掛かっている。
#     **箱が広がれば黙って食い違う**ので、広げたらこの読み分けを見直すこと。
# ─────────────────────────────────────────────────────────────────────────────


def wall_profile_check(d):
    """**走りに沿った露出**で土留めを検める。`wall_check` は最大落差**一点**しか見ない。

    ⚠ `sashizu.md` §3c(ユーザー指摘)——「設計高さで描くと壁が土に埋もれ、
    **要らない壁が図に残る**」。⇒ (a) 端が長く低いまま続くなら切り詰める、
    (b) 壁高が最大露出より1ピッチ以上大きいなら過大。
    """
    K = d["const"]["ken"]
    lim = d["const"].get("wallEndFillMax", 0.5)
    trim = d["const"].get("wallTrimMin", 2.0)          # m。これ以上続く低い端は切る
    bad = []
    for w in d["terraceWalls"]:
        ex = w.get("_exposure")
        if not ex:
            continue
        h = 4.0 * w["s"] * w.get("tiers", 1)
        pitch = 1.8 * w["s"]
        if h > ex[2] + pitch + 1e-6:
            bad.append("土留め %s の壁高 %.2fm が最大露出 %.2fm より1ピッチ(%.2fm)以上大きい"
                       " — 丁場が過大" % (w["name"], h, ex[2], pitch))
        for k, ek in enumerate(("a", "b")):
            t = (w.get("_endLow") or [0, 0])[k]
            if t >= trim - 1e-6 and ek not in (w.get("endOpen") or {}):
                bad.append("土留め %s の %s 端は %.1fm にわたり露出 %.2fm 以下 — "
                           "その区間は法面で足りる。切り詰めるか `endOpen` に理由を書くこと"
                           % (w["name"], ek, t, lim))
    return bad


def wall_end_check(d, dem):
    """**土留めが尽きる所で、面がまだ地山からどれだけ立っているか。**

    指図はもともと「落差 0.5 以下なので壁を置かず法面」という規則で壁の端を決めていたが、
    その端点は**面を上げる前の実測**で選ばれていた(2026-08-25 検図13巡 中-2)。
    面が上がると盛が増えるのに端点は動かず、TW_GenkanS は盛 1.56m、TW_GenkanE は 0.97m の
    所で壁が尽きていた。

    ⚠ `edge_step_check` はこれを構造的に見つけられない — 縁の 0.06間 外で `graded_y` を読むので、
    法が付いている限り差はほぼ 0 になる。**壁の端そのもの**を測るのはこの関数の仕事。
    """
    if dem is None:
        return _unmeasured("wall_end_check", "doi_edo_world.json")
    gr = RGrid(d)
    K = d["const"]["ken"]
    lim = d["const"].get("wallEndFillMax", 0.5)
    bad = []
    for w in d["terraceWalls"]:
        vert = abs(w["a"][0] - w["b"][0]) < 1e-9
        for end in (w["a"], w["b"]):
            # ⚠ **隅は「尽きた」ではない。** 別の土留めが同じ天端で同じ点から続くなら
            #   受けは折れて続いている。これを除かないと隅が全部偽陽性になる。
            if any(o is not w and abs(o["coping"] - w["coping"]) < 0.01
                   and any(abs(p[0] - end[0]) < 0.05 and abs(p[1] - end[1]) < 0.05
                           for p in (o["a"], o["b"]))
                   for o in d["terraceWalls"]):
                continue
            # 区画の辺に着いた所は外周の囲い(runs)が受ける
            if not in_parcel(d, end[0] + 0.3, end[1]) or not in_parcel(d, end[0] - 0.3, end[1]) \
               or not in_parcel(d, end[0], end[1] + 0.3) or not in_parcel(d, end[0], end[1] - 0.3):
                continue
            for off in (-0.15, 0.15):              # 内側がどちらかは面で判定する
                u, v = (end[0] + off, end[1]) if vert else (end[0], end[1] + off)
                g = design_y(d, u, v)
                if g is None or abs(g - w["coping"]) > 0.01:
                    continue                        # 高い側の面でなければ内側でない
                x, z = gr.W(u, v)
                nat = dem_bilinear(dem, x, z)
                if nat is None:
                    continue
                if g - nat <= lim:
                    break
                ek = "a" if end is w["a"] else "b"
                fill = g - nat
                # ⚠ **幾何と作法を分ける。** 法面が着地しない端は宣言では免れない(幾何)。
                land = _batter_lands(d, w, end, dem, gr)
                if land is None:
                    bad.append("土留め %s の端 (%.1f, %.1f) で法面が着地しない — "
                               "盛 %.2fm。壁を延ばすか折り返すこと"
                               % (w["name"], end[0], end[1], fill))
                    break
                eo = (w.get("endOpen") or {}).get(ek)
                if eo is None:
                    bad.append("土留め %s が端 (%.1f, %.1f) で尽きるが、面はまだ地山から "
                               "%.2fm 立っている(上限 %.2fm)— 壁を延ばすか、"
                               "開けておく理由を `endOpen` に書くこと"
                               % (w["name"], end[0], end[1], fill, lim))
                    break
                # ⛔ **宣言は「書けば通る」ではない。** キーの有無しか見ていなかったので、
                #   全端に `endOpen` を書けば 13巡で延ばした4端を旧位置へ戻しても無音だった
                #   (2026-08-25 検図14巡 高-1)。**宣言した数値を毎回測り直して照合する。**
                if not isinstance(eo, dict):
                    bad.append("土留め %s の `endOpen.%s` が文字列 — "
                               "`{why, fill, lands, at}` の形で数値を宣言すること"
                               % (w["name"], ek))
                    break
                hard = d["const"].get("wallEndFillHardMax", 1.6)
                if fill > hard:
                    bad.append("土留め %s の端 (%.1f, %.1f) の盛 %.2fm が**絶対上限** %.2fm を超える"
                               " — `endOpen` では通せない。壁を延ばすか折り返すこと"
                               % (w["name"], end[0], end[1], fill, hard))
                    break
                for key, got, want in (("fill", fill, eo.get("fill")),
                                       ("lands", land * K, eo.get("lands"))):
                    if want is None:
                        bad.append("土留め %s の `endOpen.%s` に %s が無い(実測 %.2f)"
                                   % (w["name"], ek, key, got))
                    elif abs(float(want) - got) > 0.06:
                        bad.append("土留め %s の `endOpen.%s.%s` が宣言 %.2f・実測 %.2f — "
                                   "宣言が古い(端か面が動いている)"
                                   % (w["name"], ek, key, float(want), got))
                at = eo.get("at")
                if at is None:
                    bad.append("土留め %s の `endOpen.%s` に端点 `at` が無い — "
                               "端が動いても宣言が生き残る" % (w["name"], ek))
                elif abs(at[0] - end[0]) > 1e-6 or abs(at[1] - end[1]) > 1e-6:
                    bad.append("土留め %s の `endOpen.%s` は端点 (%.2f, %.2f) についての宣言だが、"
                               "端は (%.2f, %.2f) にある — **端が動いたら宣言は失効する**"
                               % (w["name"], ek, at[0], at[1], end[0], end[1]))
                break
    return bad


def _batter_lands(d, w, end, dem, gr):
    """壁の端の先で、盛の法面が**区画の中・棟に当たらずに**着地するか。

    着地するなら距離(間)を返し、しないなら None。`wall_end_check` の幾何側の判定で、
    ここが None の端は `endOpen` の宣言では通せない。
    """
    occ = d["munes"] + d.get("service", [])
    vert = abs(w["a"][0] - w["b"][0]) < 1e-9
    sgn = 1.0 if (end[1] if vert else end[0]) > ((w["a"][1] if vert else w["a"][0])
                                                 if end is w["b"] else
                                                 (w["b"][1] if vert else w["b"][0])) else -1.0
    base = (end[0], end[1] + sgn * 0.5) if vert else (end[0] + sgn * 0.5, end[1])
    K = d["const"]["ken"]
    for j in range(1, 61):
        dd = j * 0.1
        cands = ([(base[0] + dd, base[1]), (base[0] - dd, base[1])] if vert
                 else [(base[0], base[1] + dd), (base[0], base[1] - dd)])
        for pu, pv in cands:
            if design_y(d, pu, pv) is not None:
                continue
            if not in_parcel(d, pu, pv):
                continue
            if any(in_obb(m, pu, pv, 1e-9) for m in occ):
                continue
            xx, zz = gr.W(pu, pv)
            n2 = dem_bilinear(dem, xx, zz)
            if n2 is None:
                continue
            if w["coping"] - dd * K / d["const"]["batterFill"] <= n2:
                return dd
    return None


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
            steep = (0.0, 0.0, 0.0, 0.0, 0.0)      # (超過, u, v, 落差, 許容)
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
                # ⭐ **法面が追いつくか**(2026-09-06 普請奉行)。⚠ probe 0.11m の落差だけを
                #   見ていると、**法面の走りが足りない縁**を拾えない — 縁ぎわは小さくても、
                #   少し外で設計の法(盛 1:1.5 / 切 1:1.0)より急に落ちていれば壁が要る。
                #   ⛔ **落差の絶対値でなく「勾配」で見る**(規則: 法は走りと落差の比)。
                r9 = 0.5                                   # 0.5間 外まで見る
                uo2, vo2 = ((line + sgn * r9, q) if edge in ("u0", "u1")
                            else (q, line + sgn * r9))
                if design_y(d, uo2, vo2) is None and in_parcel(d, uo2, vo2):
                    wx2, wz2 = gr.W(uo2, vo2)
                    n2 = dem_bilinear(dem, wx2, wz2)
                    g2 = None if n2 is None else graded_y(d, uo2, vo2, n2, we)
                    if g2 is not None:
                        dz = gi - g2
                        bat = (d["const"]["batterFill"] if dz > 0
                               else d["const"]["batterCut"])
                        allow = r9 * d["const"]["ken"] / bat
                        if abs(dz) - allow > abs(steep[0]):
                            steep = (abs(dz) - allow, uo2, vo2, dz, allow)
            if abs(worst) > lim and spot:
                bad.append("段の縁に受けの無い段差 %s の %s: %+.2fm (グリッド %.1f, %.1f)"
                           % (t["name"], edge, worst, spot[0], spot[1]))
            if steep[0] > 1e-6:
                bad.append("段の縁の法が設計より急 %s の %s: 0.5間 外で %+.2fm "
                           "(法の許容 %.2fm)— 法面が追いつかないので土留めが要る "
                           "(グリッド %.1f, %.1f)"
                           % (t["name"], edge, steep[3], steep[4], steep[1], steep[2]))
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


def mune_fit_check(d):
    """**棟の下の |設計面 − 自然地形| ≤ 0.5m**(§B-1 の合否)を検査にする。

    表に出しただけでは、棟を動かしたときに悪化しても誰も気づかない
    (2026-08-24 の感度試験で、居間棟を1間ずらしても検査が反応しなかった)。
    超過の**割合**が 5% を超えたら止める(0% を求めると地形の粒度に負ける)。
    """
    bad = []
    for m in d["munes"] + d["service"]:
        r = mune_fit(d, m)
        if r and r[1] > 5.0:
            bad.append("棟の下の切盛が %.0f%% で ±0.5m を超える(最大 %+.2fm): %s" % (r[1], r[0], m["name"]))
    return bad


NEIGHBOUR = {"岡部": ("okabe_sashizu.json", (8, 9)),
             "松平": ("matsudaira_dewa_sashizu.json", (0, 1, 2, 3))}


def wall_needed_check(d, dem):
    """**土留めが要る所に土留めがあるか**を測る。壁を消しても法面が黙って代わりを務めるので、
    「壁が要るかどうか」はどの検査も見ていなかった(2026-08-24 検図第7巡: 14本中3本は消しても無反応)。

    段の縁のうち**壁も開口も無い区間**で、法面が現地形に着地するのに要る水平距離が
    段の外の余地(次の物・区画線まで)を超えるなら、そこは法面では持たない=土留めが要る。
    開口の中も同じ理屈で見る(開口幅から通る物を引いた分に受けが無ければ段差が残る)。
    """
    if dem is None:
        return _unmeasured("wall_needed_check", "doi_dem.json")
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
        return _unmeasured("neighbour_wall_check", "doi_edo_dem.json")
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
            float_worst = -9e9; f_s = None
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
                # ⚠ **符号を片方しか見ていなかった。** 埋没(g > seat)だけを測っており、
                #   **塀が当家側の地盤の上に浮く**(seat > g)ほうは構造的に見えなかった
                #   (2026-08-26 松平 EDO-0025: S_Hei_C が 1.53m 浮いていたのを
                #   当家の検査は 0件と報告していた)。⛔ **境界に立つ物は両方の符号で測る。**
                #   ただし基壇(`base`)を持つ run は、基壇が足元まで下ろすので浮きではない。
                if seat - g > float_worst:
                    float_worst = seat - g; f_s = sq
            if at_s is not None and worst > 0.05:
                bad.append("%s の %s が当家側の地盤に %.2fm 埋まる(相手の s=%.1f・境界から %.1fm 内側で実測)"
                           % (who, r["name"], worst, at_s, at_off))
            # ⚠ **根石を数える。** 基壇だけを免除条件にすると、**根石で受けている run が
            #   全部鳴る**(2026-08-26 松平: `S_Hei_Okabe5` が 0.40m の浮きで鳴ったが、
            #   `ishi` 0.30m を引けば 0.10m で許容内だった=検査が根石を見ていなかっただけ)。
            #   ⛔ ただし根石が背丈を超えたらそれは基壇である。`base` を持たせること。
            if f_s is not None and not r.get("base"):
                ishi = float(r.get("ishi") or 0.0)
                cap = d["const"].get("neighbourIshiMax", 1.0)
                if ishi > cap:
                    bad.append("%s の %s の根石 `ishi`=%.2fm が上限 %.2fm を超える — "
                               "それは基壇なので `base` を持たせること"
                               % (who, r["name"], ishi, cap))
                elif float_worst - ishi > 0.30:
                    bad.append("%s の %s が当家側の地盤から %.2fm 浮く"
                               "(根石 %.2fm を引いて %.2fm・相手の s=%.1f)— "
                               "基壇 `base` も根石も足りない。境界に足元の無い塀が立つ"
                               % (who, r["name"], float_worst, ishi,
                                  float_worst - ishi, f_s))
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
    # ⭐ **明地の枠**(検図方 中-4)。⚠ 従前 `akichi` はどの面の検査にも入っておらず、
    #   `Akichi_Kita.v1` を 110 にしても 0 件だった。
    # ⛔ **区画多角形との比較にはしない。** 枠は矩形、区画の南西辺は斜めなので、
    #   `Akichi_Minami` のように**辺に沿った正しい枠でも角が必ず外へ出る**(実測 (−17.95, 79.95))。
    #   ⭕ 見るのは **`akichi_stats` が実際に走査する範囲=主面 `Shu` の矩形**に収まっているか。
    #   区画の外のセルは `in_parcel` で落ちるので坪数には入らない。
    shu9 = next((t for t in d["terraces"] if t["name"] == "Shu"), None)
    if shu9 is None:
        bad.append("段 Shu が無い — 明地の枠を検める範囲が決まらない")
    for a in d.get("akichi", []):
        if shu9 is None:
            break
        if not (shu9["u0"] - 1e-9 <= a["u0"] and a["u1"] <= shu9["u1"] + 1e-9
                and shu9["v0"] - 1e-9 <= a["v0"] and a["v1"] <= shu9["v1"] + 1e-9):
            bad.append("%s(明地の枠)(%.1f,%.1f)–(%.1f,%.1f) が主面 Shu "
                       "(%.1f,%.1f)–(%.1f,%.1f) の外へ出る — 走査されない枠は坪数を持てない"
                       % (a["name"], a["u0"], a["v0"], a["u1"], a["v1"],
                          shu9["u0"], shu9["v0"], shu9["u1"], shu9["v1"]))
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
        # ⚠ 段築を勘定に入れる(丁場に上限を入れた 2026-08-25 以降、高い壁は段築になる)
        h = 4.0 * w["s"] * w.get("tiers", 1)
        if h < dr[1] - 0.05:
            bad.append("%s 壁高 %.2f(丁場%.2f×%d段築)< 最大落差 %.2f — 足りない"
                       % (w["name"], h, w["s"], w.get("tiers", 1), dr[1]))
        elif h > dr[1] + 0.8:
            bad.append("%s 壁高 %.2f ≫ 最大落差 %.2f — 過大(埋まる)" % (w["name"], h, dr[1]))
        if dr[0] < 0.3:
            bad.append("%s は落差 %.2f の区間を含む — その区間は壁でなく法面にする" % (w["name"], dr[0]))
    return bad


# overlap_check の正典は sashizu_lib(2026-08-26 統一 — 当邸の実装をそのまま基準にした)。


# ---------------------------------------------------------------- 取り合い(実装用・自動算出)


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
        ex = w.get("_exposure")
        rows.append("<tr><td><code>%s</code></td><td>土留め(s=%.2f×%d段)</td>"
                    "<td>(%.1f, %.1f) → (%.1f, %.1f)</td>"
                    "<td>天端 %.1f・壁高 %.1f・<b>露出 %s</b></td></tr>"
                    % (w["name"], w["s"], w.get("tiers", 1), wa[0], wa[1], wb[0], wb[1],
                       w["coping"], 4.0 * w["s"] * w.get("tiers", 1),
                       ("%.2f〜%.2f(平均 %.2f)" % (ex[0], ex[2], ex[1])) if ex else "—"))
    for k in d["kaidans"]:
        w = next((x for x in d["terraceWalls"] if x["name"] == k["atWall"]), None)
        if w is None:
            continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
        if w["a"][0] == w["b"][0]:
            c = gr.W(w["a"][0], k["gapV"])
        else:
            c = gr.W(k["gapU"], w["a"][1])
        rows.append("<tr><td><code>%s</code></td><td>石段 %d段(幅 %.2fm)</td>"
                    "<td>芯 (%.1f, %.1f)</td><td>落差 %.1f・走り %.2fm</td></tr>"
                    % (k["name"], k["steps"], k["w"], c[0], c[1], k["drop"], k["run"]))
        if "flank" in k:
            # ⚠ 側石垣を表に出す。石段が張り出す所の両側の土留めで、
            #   出さないと**どの図・表にも無い土木構造物**になる(2026-08-25 検図13巡 中-1)。
            fl = k["flank"]
            rows.append("<tr><td><code>%s_Flank</code></td><td>側石垣 左右2枚(s=%.2f)</td>"
                        "<td>石段 <code>%s</code> の両側</td>"
                        "<td>走り %.2fm・天端は踏面なり</td></tr>"
                        % (k["name"], fl["s"], k["name"], fl["run"]))
    for rp in d.get("ramps", []):
        w = next((x for x in d["terraceWalls"] if x["name"] == rp["atWall"]), None)
        if w is None:
            continue          # 参照切れは refs_check が非0で止める(例外で落とさない)
        c = gr.W(w["a"][0], rp["gapV"]) if w["a"][0] == w["b"][0] else gr.W(rp["gapU"], w["a"][1])
        rows.append("<tr><td><code>%s</code></td><td>土の斜路 1:%.0f(幅 %.2fm)</td>"
                    "<td>芯 (%.1f, %.1f)</td><td>落差 %.1f・走り %.2fm</td></tr>"
                    % (rp["name"], 1.0 / rp["grade"], rp["w"], c[0], c[1], rp["drop"], rp["run"]))
    for rl in d["rails"]:
        # ⛔ **丈と形を文字列に焼かない。**2026-09-06 まで「竹垣(四つ目垣 h0.9)」と
        #   ここに書いてあり、**指図が主張している数値が設計値ファイルに無かった**
        #   (規則4)。棟梁は丈が分からず胴縁の段数を発明するほかなかった。
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        rows.append("<tr><td><code>%s</code></td><td>竹垣(%s h%.1f)</td>"
                    "<td class='note'>%s</td><td>法肩から内へ %.2fm</td></tr>"
                    % (rl["name"], rl.get("kata", "?"), rl.get("h", float("nan")),
                       " → ".join("(%.1f, %.1f)" % p for p in pts),
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
        rows.append("<tr><td>%s(芯)</td><td>(%.2f, %.2f)</td><td>%.2f</td><td>%.1f</td></tr>"
                    % (k["name"], x, z, k["sill"], kyaw))
    # ⭐ **小門の部材と、焼くのに要る引数を算出して出す**(2026-09-06 棟梁の差し戻し②)。
    #   ⛔ 引数を指図へ手で書かない — `runs` と `komon` を動かせば値が変わる従属値。
    kr = []
    for k in d["komon"]:
        r = next((q for q in d["runs"] if q["name"] == k.get("inRun")), None)
        # ⭐ **開口の有効高は敷居から測る**(2026-09-06 部材方)。`komon[].sill`(道なり+0.20)と
        #   run の `seat`(躯体の据え付け面)は同じ高さではなく、その差は部材側で吸収する。
        #   ⛔ `leaf.h` をそのまま部材へ渡すと、run の座と敷居の差だけ門口が低く出る。
        #   run が名指しされていない木戸は、**同じ辺で開口の両肩に継ぐ run** を幾何で拾う。
        adj = [q for q in d["runs"] if q["edge"] == k["edge"]
               and (abs(q["s1"] - (k["s"] - k["w"] / 2.0)) < 0.05
                    or abs(q["s0"] - (k["s"] + k["w"] / 2.0)) < 0.05)]
        seats = sorted(set(round(q["seat"], 3) for q in ([r] if r is not None else adj)))
        lh = (k.get("leaf") or {}).get("h")
        if seats and lh is not None:
            eff = ("run の座 %s − 敷居 %.2f = <b>%+.2f</b> を部材側で吸収 ⇒ "
                   "<b>有効高は土台の底から %.2f</b>"
                   % ("/".join("%.2f" % s for s in seats), k["sill"],
                      seats[0] - k["sill"], lh + (seats[0] - k["sill"])))
            if len(seats) > 1:
                eff += " ⚠ <b>両肩の run の座が揃っていない</b>(%s)" % "・".join(
                    "%s %.2f" % (q["name"], q["seat"]) for q in adj)
        else:
            eff = "⚠ 継ぐ run が見つからない — 有効高が出せない"
        arg = "—"
        if r is not None:
            L0, G0 = r["s1"] - r["s0"], k["s"] - r["s0"]
            arg = ("run <code>%s</code> 長 <b>%.2f m</b> / 門口の芯は run の s0 から "
                   "<b>%.2f m</b> / 門口 %.2f × 扉丈 %.2f<br>焼く名 "
                   "<code>Nagaya_Omote_%s_mon%s.fbx</code>"
                   % (r["name"], L0, G0, k["w"],
                      (k.get("leaf") or {}).get("h", float("nan")),
                      ("%.2f" % L0).rstrip("0").rstrip("."),
                      ("%.2f" % G0).rstrip("0").rstrip(".")))
        elif k.get("w"):
            arg = ("開口 <b>%.2f m</b> / 扉丈 %.2f ／ ⚠ 部材の走り方向の実寸は開口より"
                   "方立柱2本ぶん広い — <b>塀の run はその実寸の外側に取り付く</b>(規則5)"
                   % (k["w"], (k.get("leaf") or {}).get("h", float("nan"))))
        # ⭐ **敷居と街路の差は3門とも刷る**(⛔ 閾値で隠さない=規則19)。
        dem9 = load_terrain(os.path.join(DOC, "doi_dem.json"))
        x9, z9 = edge_pt(P, k["edge"], k["s"])
        g9 = dem_bilinear(dem9, x9, z9) if dem9 else None
        fi = k.get("fumiishi")
        if g9 is None:
            eff += "<br>⚠ 街路の地盤が測れない"
        else:
            dz = k["sill"] - g9
            eff += ("<br>街路 %.2f に対し敷居 %.2f = <b>%+.2f m</b> ／ %s"
                    % (g9, k["sill"], dz,
                       ("<b>門外に踏石 %d段</b>(蹴上 <b>%.3f</b>・踏面 %.2f・幅 %.2f)"
                        % (fi["n"], dz / fi["n"], d["const"]["fumi"], k["w"])) if fi
                       else ("段は不要(蹴上 %.2f 未満の敷居)" % d["const"]["keri"]
                             if dz <= d["const"]["keri"] else "⚠ <b>段が無い</b>")))
        kr.append((k["name"], (k.get("leaf") or {}).get("kind", "小門"),
                   "<code>%s</code>" % k.get("asset", "⚠ 未解決"),
                   k.get("assetState", "—"), arg, eff))
    return ("<h3>門構えの部材位置</h3><div class='tw'><table><thead><tr><th>部材</th><th>芯の世界座標 (x,z)</th>"
            "<th>敷居</th><th>yaw</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>長屋門は袖塀を介さず**両袖がそのまま表長屋へ連続**する(番所は躯体内・格子付)。</p>"
            "<h3>小門の部材と、焼くのに要る引数</h3>"
            + _tw(("小門", "種", "部材", "調達", "引数(設計値から算出)",
                   "開口の有効高(敷居基準)"), kr)
            + "<p class='cap'>⭐ <b>開口の有効高は「敷居」から測る</b>(2026-09-06 部材方)。"
              "⚠ <b>敷居の採り方は門の型で分かれる</b>(<code>doi_kosho.md</code> の確度U一覧)— "
              "<b>run に抜いた潜り(通用門)は基壇の天端(<code>seat</code>)に揃え</b>、"
              "<b>独立門(裏木戸)は道なり+0.20</b>。"
              "⭕ <b>通用門は 2026-09-06 の裁定で <code>sill</code> = <code>seat</code> になったので、"
              "部材が差を吸う造り(<code>--gate-drop</code>)は要らなくなった</b> — "
              "焼き直し版は H 5.509・ピボットより下へ出る頂点 0 で、"
              "<code>runs.E_Nagaya_N.seat</code> をそのまま <code>position.y</code> に渡せる。"
              "⛔ <b><code>leaf.h</code> をそのまま部材へ渡さない</b> — あれは<b>開口の内法</b>で、"
              "部材の丈(裏木戸なら 3.45)とは別物。</p>"
            + "<p class='cap'>⛔ <b>引数を指図に手で書かない</b> — "
              "<code>runs</code> と <code>komon</code> を動かせば変わる従属値なので毎回ここで測る。"
              "⚠ <b>通用門は独立した門ではない</b> — 表長屋(北)の run ごと"
              "「門口を抜いた表長屋」として焼く(開口だけの短い部材は妻2つ+bay で最小 5.2m ほどあり作れない)。"
              "⚠ 生成器は書き出す前に Z まわりに 180° 回すので、"
              "<b>左右を取り違えると門口が反対の端に出る</b> — 据えたあと実メッシュで検めること。"
              "⚠ <b>裏木戸の X の実寸は開口より方立柱2本ぶん広い</b>"
              "(岡部の実測で 2.727 → 3.197 / 2.909 → 3.379)。"
              "<b>練塀の run は据えた木戸の OBB の実寸の外側に取り付く</b>(可動側は練塀)— "
              "⛔ 開口の呼び寸法で継ぐと 0.47m 食い込む(規則5)。</p>"
            + "<p class='cap'>⭐ <b>門の敷居と街路の差は3門とも刷る</b>(⛔ 閾値で隠さない)。"
              "⚠ <b>通用門は敷居を基壇の天端へ揃えた結果 街路より 0.58m 高い</b> — "
              "<b>勝手の門で荷を担いで上がる</b>ので<b>門外に踏石2段</b>を置く"
              "(⛔ 敷居を街路へ下げて解かない=基壇に揃える裁定と衝突する)。"
              "⭕ <b>蹴上は書かない</b> — <code>(敷居 − 街路の地盤) ÷ 段数</code> の従属値で"
              "毎回ここで出す(街路が動けば蹴上も動く)。踏面は <code>const.fumi</code>、"
              "幅は門口に揃える。"
              "⭕ <b>表門(+0.15)と裏木戸(+0.21)は段が要らない</b> — "
              "<b>一蹴上(<code>const.keri</code> %.2f)に満たない差は段では受けられない</b>"
              "(跨ぐ敷居であって段ではない)。⚠ 裏木戸の設計は「道+0.20」で、"
              "実測 +0.21 の差 0.01 は DEM の読み取り差。</p>" % d["const"]["keri"])


def bom_measure(d, kind):
    """部材表の延長を**正典から測る**。⚠ 手で書かない — 石垣は延長が動くたびに嘘になる。"""
    K = d["const"]["ken"]
    if kind == "terraceWalls":
        return sum(math.hypot(w["b"][0] - w["a"][0], w["b"][1] - w["a"][1]) * K
                   for w in d["terraceWalls"])
    if kind == "boundaryPlinth":
        return sum(b["s1"] - b["s0"] for b in d.get("boundaryPlinth", []))
    if kind == "runBase":
        return sum((r["s1"] - r["s0"]) for r in d.get("runs", []) if r.get("base"))
    if kind == "flank":
        return sum(k["flank"]["run"] * 2 for k in d["kaidans"] if "flank" in k)
    if kind == "kaidan":
        return sum(k["run"] for k in d["kaidans"])
    if kind == "rails":
        return sum(math.hypot(b[0] - a[0], b[1] - a[1]) * K
                   for rl in d.get("rails", []) for a, b in zip(rl["pts"], rl["pts"][1:]))
    # 水尻(余水吐)— ⚠ **埋樋は閾から始まらない。**閾は汀 #14 に据え、樋は `pts[0]` から
    #   走る。⛔ 閾→pts[0] の一跨ぎを樋の延長に足さない(石の閾の見付であって樋ではない)。
    if kind in ("umeToi", "otoshimizo"):
        g = niwa(d)
        mz = ((g or {}).get("mizu") or {}).get("mizushiri") or {}
        pts = (mz.get("umeToi") or {}).get("pts") or []
        if not pts:
            return None
        if kind == "umeToi":
            return sum(math.hypot(b[0] - a[0], b[1] - a[1]) * K
                       for a, b in zip(pts, pts[1:]))
        to = (mz.get("otoshimizo") or {}).get("to")
        if not to:
            return None
        return math.hypot(to[0] - pts[-1][0], to[1] - pts[-1][1]) * K
    return None


def bom_table(d):
    if "bom" not in d:
        return ""
    rows = []
    tot = 0.0
    nb = 0
    for b in d["bom"]:
        stock = b.get("asset", "")
        ln = bom_measure(d, b["measure"]) if b.get("measure") else None
        if ln is not None:
            tot += ln
        if b.get("build"):
            nb += 1
        # ⭐ `how` = 部材方の第1段の結果(焼成済 / 在庫で組む / C#(棟梁))。
        #   ⛔ 未着の行を「新造(Blender)」のまま黙って通さない — ⚠ を出す。
        proc = (("<b>%s</b>" % b["how"]) if b.get("how")
                else ("<b>新造</b> ⚠ 手当て未定" if b.get("build") else "在庫"))
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (b["item"], proc,
                       ("%.1f m" % ln) if ln is not None else "—",
                       ("<code>%s</code>" % stock) if stock else "—",
                       ("<code>_pending.%s</code>" % b["ask"]) if b.get("ask") else "—",
                       b.get("note", "")))
    return ('<div class="tw"><table><thead><tr><th>部材</th><th>調達</th><th>延長</th>'
            '<th class="note">在庫パス/新造名</th><th class="note">宿題</th>'
            "<th class='note'>備考</th></tr></thead><tbody>" + "".join(rows)
            + "</tbody></table></div>"
            + "<p class='cap'>延長は<b>正典から毎回測る</b> — 手で書かない。"
              "測れる項の合計 <b>%.1f m</b>(石垣・石段・竹垣・水尻の樋と溝)。"
              "⚠ 2026-08-25 の検図14巡まで、"
              "<b>部材表に石垣の項が一つも無かった</b>(側石垣31.5mは表にも図にも出ていなかった)。"
              "⭐ <b>調達が「新造」の %d 行が、そのまま部材方(edo-buzai)への依頼票</b>になる — "
              "「宿題」の欄が <code>_pending</code> のどの項へ続くかを指す。"
              "⚠ 2026-09-06 に、棟梁が据えられなかった物を全部この表へ立てた"
              "(表門・井戸5・土蔵の足形・厩・渡廊下1.5間・建仁寺垣 h1.8・手水石・通用門・"
              "裏木戸・水尻4点・地表の仕上げ)— "
              "<b>据えられなかった物が表に無いと、実装の抜けが誰にも見えない</b>。</p>"
            % (tot, nb))


def _band_desc(d, m):
    """棟の**帯の割り付け**を人の読める一行に。⛔ 数字は `roof.bands` から引く(写さない)。"""
    rf = m.get("roof") or {}
    bd = rf.get("bands")
    K = d["const"]["ken"]
    if not rf.get("banded"):
        return ("<b>帯に割らない</b>【例外・名指し=U】<br>御殿の棟ではなく、"
                "軒高 2.35 / 棟高 5.42 と<b>別の作法で高さが決まっている</b>")
    if not bd or bd.get("n") is None:
        return ("⚠ <b>帯が組めない</b> — 身舎 %.4g間 を %g〜%g間 の整数に割れない"
                % (bd.get("moyaAcross", 0.0) if bd else 0.0,
                   min(d["const"]["moyaBand"]["widths"]),
                   max(d["const"]["moyaBand"]["widths"])))
    s = ("<b>%d本</b> 身舎 <b>%s間</b>(%s)"
         % (bd["n"], "+".join("%g" % w for w in bd["ws"]),
            " / ".join("%.2fm" % (w * K) for w in bd["ws"])))
    if bd["along"] is None:
        s += "<br>⚠ <b>向きは未決</b>(<code>_pending.bandmuki</code>)"
    else:
        s += "<br>帯の長手 <b>%s 方向</b> ／ 割る向き %s" % (bd["along"], bd["across"])
    return s


def _tani_desc(d, m):
    """**谷**(帯の境)の本数・向き・位置。"""
    rf = m.get("roof") or {}
    tn = rf.get("tani")
    if not rf.get("banded") or not tn:
        return "—"
    if not tn.get("n"):
        return "<b>0本</b>(帯1本)"
    at = tn.get("at")
    return ("<b>%d本</b> ／ %s<br>%s"
            % (tn["n"],
               ("<b>%s 方向</b>(大棟と平行)" % tn["dir"]) if tn["dir"]
               else "⚠ <b>向きは未決</b>",
               ("位置 %s" % " / ".join("%.4g" % q for q in at)) if at
               else "位置は向きが決まってから"))


def _cert(rf, key, dflt="?"):
    """棟の屋根の**要素ごとの確度**。⛔ 棟に一つの `cert` を置かない(2026-09-06 考証方 中5)。"""
    return ((rf or {}).get("certs") or {}).get(key, dflt)


def neighbour_hash_check(d):
    """**隣家の指図が動いたら鳴らす。**⛔ 隣家の json を読む検査があるのに、
    **隣家が動いたことを誰も検知していなかった**(2026-09-06 検図方 中1)。

    ⚠ commit 済みの図に、既に消えた松平の run(`S_Hei_Doi_S1` +1.680m)が載ったままだった。
    ⛔ **生成器がハッシュを書き戻してはいけない** — 書き戻すと二度と鳴らない。
    ⇒ 鳴ったら **①回し直す ②`neighbours[].sha` を書き直す ③図を commit する**。
    """
    bad = []
    for pid, q in (d.get("neighbours") or {}).items():
        fp = os.path.join(DOC, q["file"])
        if not os.path.exists(fp):
            bad.append("隣家の指図 `%s` が無い — `neighbours.%s` の宣言と食い違う" % (q["file"], pid))
            continue
        cur = hashlib.sha256(open(fp, "rb").read()).hexdigest()[:16]
        if cur != q.get("sha"):
            bad.append("**隣家が動いた — 図を回し直せ**: `%s` の sha が %s → %s。"
                       "⛔ 当図の隣家の表(埋没・余裕)は古い可能性がある。"
                       "回し直して `neighbours.%s.sha` を書き直し、図を commit すること"
                       % (q["file"], q.get("sha"), cur, pid))
    return bad


def band_check(d):
    """**身舎の帯の割り付けが規則どおりか。**(2026-09-06 ユーザー裁定=案C)

    ⛔ **意匠は測らない** — 測るのは ①どの棟も「帯に割る」か「名指しの例外」かのどちらかであること
    ②**帯の身舎が `widths`(4〜5間)の整数**であること・帯数が最小であること
    ③帯の長手が大棟と一致すること ④室が身舎の中に収まること
    ⑤**御殿の棟を切る断面の軒高が `const.gotenEave` と一致すること**(同じ数字を二箇所に
    持っているので、輪に入れる=規則19)⑥**葺材(格の表示)が全棟に入っていること**
    ⑦**御殿の最低の棟高(地盤上)が表長屋の棟高を下回らないこと**(格式の逆転)
    ⑧**絶対高でも逆転が無いこと**(御殿の最高 ≥ 附属屋の最高。⭕ 蔵は名指しの例外だが上限つき)
    ⑨**軒の出/妻の出が 0 でないこと**(欄が無い物は `const` の既定を当てる。const 自身も見る)
    ⑩**`const.gesyaKobai` が `kawaraKobai` と同値**であること(入側は身舎の屋根の続き)。
    ⛔ **目録を本体より古いままにしない**(2026-09-06 検図方 6)。

    ⭐ ②は 2026-09-06 の考証方 高2 で入った。⚠ **江戸間 1間 = 柱の心々**で、**谷は柱通りの
    上にしか置けない** — 端数の帯は谷を柱通りから外す。
    ⭐ ⑦は 2026-09-06 の考証方 高1 で入った。⚠ **他の建物との序列を測る検査が一本も無かった**。
    """
    C = d["const"]
    mb = C.get("moyaBand")
    if not mb:
        return ["`const.moyaBand`(帯の割り付けの規則)が無い"]
    bad = []
    names = set(m["name"] for m in d["munes"])
    for nm in mb.get("exempt", []):
        if nm not in names:
            bad.append("`moyaBand.exempt` の %s という棟が無い" % nm)
    lo, hi = min(mb["widths"]), max(mb["widths"])
    banded, gy = [], []
    for m in d["munes"]:
        rf = m.get("roof") or {}
        if not rf.get("banded"):
            if m["name"] not in mb.get("exempt", []):
                bad.append("%s が帯にも例外表にも無い — `roof.banded` を立てるか "
                           "`const.moyaBand.exempt` に理由つきで名指しする"
                           "(⛔ 無名の例外を作らない)" % m["name"])
            continue
        banded.append(m)
        bd = rf.get("bands") or {}
        if bd.get("n") is None:
            bad.append("%s の身舎 %.4g間 を %g〜%g間 の整数の帯に割れない"
                       % (m["name"], bd.get("moyaAcross", 0.0), lo, hi))
            continue
        for w in bd["ws"]:
            if abs(w - round(w)) > 1e-9 or not (lo - 1e-9 <= w <= hi + 1e-9):
                bad.append("%s の帯の身舎に %.4g間 がある — %g〜%g間 の**整数**でなければ"
                           "谷が柱通りに乗らない(江戸間1間=柱の心々)"
                           % (m["name"], w, lo, hi))
        if abs(sum(bd["ws"]) - bd["moyaAcross"]) > 1e-9:
            bad.append("%s の帯の合計 %.4g間 が身舎 %.4g間 と合わない"
                       % (m["name"], sum(bd["ws"]), bd["moyaAcross"]))
        if bd["n"] > -(-int(round(bd["moyaAcross"])) // hi):
            bad.append("%s の帯が %d本 — 身舎 %.4g間 なら %d本 で足りる(⛔ 谷を増やさない)"
                       % (m["name"], bd["n"], bd["moyaAcross"],
                          -(-int(round(bd["moyaAcross"])) // hi)))
        a9, b9 = m["u1"] - m["u0"], m["v1"] - m["v0"]
        sq = abs(a9 - b9) < 1e-9
        al = rf.get("bandAlong")
        if sq:
            # ⭐ 2026-09-06 普請奉行の裁定(平入り)で向きが入った。⛔ 幾何では決まらないので
            #   **裁定が無ければ未決**。⚠ `roof.ridge` は `null` のまま(足形は正方形)。
            if al not in ("u", "v"):
                bad.append("%s は正方形(%g × %g間)で帯の向きが幾何では決まらない — "
                           "`bandAlong` に裁定の向き(`\"u\"` か `\"v\"`)を入れる"
                           % (m["name"], a9, b9))
            if rf.get("ridge") is not None:
                bad.append("%s は正方形なので `roof.ridge` は null のまま — "
                           "帯の向きは `bandAlong` が持つ" % m["name"])
        elif al != rf.get("ridge"):
            bad.append("%s の `bandAlong` が %r で `roof.ridge` %r と食い違う — "
                       "谷は大棟と平行なので帯も大棟の向きに走る"
                       % (m["name"], al, rf.get("ridge")))
        # ⭐ **葺材(格の表示)は帯の対象棟すべてが持つ**(2026-09-06 普請奉行の裁定)。
        #   ⛔ 欄が無い棟を作らない — 案Cで格を分ける軸はここしか残っていない。
        if not rf.get("fukizai"):
            bad.append("%s に `roof.fukizai`(葺材)が無い — 案Cで屋根の型でも棟高でも"
                       "格を分けられなくなったので、格の表示はここが受ける" % m["name"])
        if bd.get("ridgeG"):
            gy.append((m["name"], min(bd["ridgeG"])))

    # ⭐⭐ **室は身舎に収まり、かつ身舎を覆い尽くす**(2026-09-06 検図方 低2・低3)。
    #   ⚠ **`continue` で例外の棟(厩)を抜けていたので、室の検査が一切走らなかった**(低3)。
    #   ⇒ **帯の検査だけを飛ばし、室はすべての棟で測る**(例外の棟は足形で見る)。
    #   ⚠ **被覆を誰も測っていなかった**(低2)— `Oku` の室を1つ消しても 0 件だった。
    cov = C.get("moyaCoverMin", 1.0)
    for m in d["munes"]:
        rf = m.get("roof") or {}
        bnd = bool(rf.get("banded"))
        r0, s0, r1, s1 = moya_rect(d, m) if bnd else (m["u0"], m["v0"], m["u1"], m["v1"])
        what = "身舎" if bnd else "足形"
        for r in m.get("rooms", []):
            if not (r0 - 1e-9 <= r["u0"] and r["u1"] <= r1 + 1e-9
                    and s0 - 1e-9 <= r["v0"] and r["v1"] <= s1 + 1e-9):
                bad.append("%s の室「%s」が%s(%.4g,%.4g)–(%.4g,%.4g)からはみ出す%s"
                           % (m["name"], r["name"], what, r0, s0, r1, s1,
                              (" — 外周 %.4g間 は入側で、帯に割れる身舎ではない" % mb["irikawa"])
                              if bnd else ""))
        if not bnd:
            continue                       # 覆い尽くしは入側を持つ棟だけの条
        area = (r1 - r0) * (s1 - s0)
        got = sum((r["u1"] - r["u0"]) * (r["v1"] - r["v0"]) for r in m.get("rooms", []))
        if area > 0 and got < area * cov - 1e-9:
            bad.append("%s の室が身舎を覆い尽くさない — 室 %.2f間² / 身舎 %.2f間²(%.1f%%・下限 %.0f%%)"
                       % (m["name"], got, area, 100.0 * got / area, 100.0 * cov))

    # ⑤ 軒高 — `const.gotenEave` と `sections[].eaveAbove` の二重管理を輪に入れる
    ge = C.get("gotenEave")
    if ge is not None:
        for sec in d.get("sections", []):
            hit = [m["name"] for m in banded
                   if (sec["axis"] == "u" and m["u0"] <= sec["at"] <= m["u1"])
                   or (sec["axis"] == "v" and m["v0"] <= sec["at"] <= m["v1"])]
            if hit and abs(sec.get("eaveAbove", ge) - ge) > 1e-9:
                bad.append("%s の `eaveAbove` %.4g が `const.gotenEave` %.4g と違う"
                           "(%s を切る面)" % (sec["name"], sec["eaveAbove"], ge, "・".join(hit)))
    # ⑦ 格式の逆転 — 御殿の最低の棟高(地盤上)が表長屋を下回らないこと
    nr = C.get("nagayaRidge")
    if nr is not None and gy:
        nm9, h9 = min(gy, key=lambda q: q[1])
        if h9 < nr - 1e-9:
            bad.append("**格式の逆転**: 帯に割った棟の最低 %s の棟高(地盤上)%.3fm が"
                       "表長屋 %.3fm を下回る — 御殿の棟が外周の長屋より低い姿になる"
                       % (nm9, h9, nr))
    # ⭐⭐ ⑧ **絶対高でも逆転を見る**(2026-09-06 検図方 中7)。
    #   ⚠ ⑦ は `nagayaRidge` と**地盤上の値だけ**を見ており、`const.kachuEave` を 6.00 にして
    #   **家中長屋の絶対棟 34.94 > 御殿 33.10** にしても **0件**だった。
    #   ⛔ 図自身が「地盤上と絶対で順が変わる」と書いている以上、**両方**要る。
    #   ⭕ **蔵だけは名指しの例外**(2階建て・御殿は平屋。2026-09-06 普請奉行の裁定=このまま)。
    KURA = ("Komegura", "Kura1", "Kura2")
    # ⭐ **例外にも上限を置く**(2026-09-06 検図方 8)。⛔ 名指しで外したままだと
    #   `kuraRidge` を 40.0 にしても 0件になる — **例外は「無検査」ではない**。
    kover = C.get("kuraOverGoten")
    ab = []
    for m in d["munes"]:
        rf = m.get("roof") or {}
        if (rf.get("bands") or {}).get("ridgeY"):
            ab.append(("御殿", m["name"], max(rf["bands"]["ridgeY"])))
        elif rf.get("ridgeH") is not None:
            ab.append(("他", m["name"], m["y"] + rf["ridgeH"]))
    for o in d.get("service", []):
        if o["name"] in KURA:
            continue
        _e, rg9 = svc_roof(d, o)
        if rg9 is not None:
            ab.append(("他", o.get("label", o["name"]), o["y"] + rg9))
    #   ⚠ **比べるのは「御殿の最高」と「附属屋の最高」** — ⛔ 最低と比べない。
    #     面の高さが棟ごとに違うので(表役所は下段 19.2)、**最低との比較は面の差を測ってしまう**。
    #     図自身が「地盤上と絶対で順が変わる。⛔ 混ぜて語らない」と書いているとおり。
    lo9 = max([q for q in ab if q[0] == "御殿"], key=lambda q: q[2], default=None)
    hi9 = max([q for q in ab if q[0] == "他"], key=lambda q: q[2], default=None)
    if lo9 and hi9 and hi9[2] > lo9[2] + 1e-9:
        bad.append("**格式の逆転(絶対高)**: %s の棟が %.3fm で、御殿の最高 %s %.3fm を上回る"
                   " — 御殿より高く見える附属屋は蔵だけ(2階建て)という裁定に反する"
                   % (hi9[1], hi9[2], lo9[1], lo9[2]))
    if kover is not None and lo9:
        for o in d.get("service", []):
            if o["name"] not in KURA:
                continue
            _e, rg9 = svc_roof(d, o)
            if rg9 is not None and o["y"] + rg9 > lo9[2] + kover + 1e-9:
                bad.append("%s の棟が %.3fm で、御殿の最高 %s %.3fm を %.3fm 超える"
                           "(蔵の例外の上限 %.3fm)— 蔵は2階建てだが、御殿より高くてよい幅にも限りがある"
                           % (o.get("label", o["name"]), o["y"] + rg9, lo9[1], lo9[2],
                              o["y"] + rg9 - lo9[2], kover))
    # ⭐ ⑨ **軒の出が 0 の物を黙って通さない**(同 中7)。
    #   ⭐⭐ **2026-09-06 検図方 5 で穴を塞いだ** — ⛔ 従前は `noki` の**欄を持つ物しか見ておらず**、
    #   ①**欄ごと消せば無反応**(確度Pの実測値が黙って消せた)②**御殿6棟と厩は欄を持たない**ので
    #   **一度も見ていなかった**(`const.nokiDe` を 0 にしても 0件)。
    #   ⇒ **欄が無い物には const の既定を当てて同じ条で測り、const 自身も 0 でないことを確かめる**。
    for key9 in ("nokiDe", "tsumaEnd"):
        if C.get(key9, 0.0) <= 1e-9:
            bad.append("`const.%s` が 0 — 屋根は足形の外へ出る。"
                       "0 にすると棟どうしの当たりの検査が丸ごと無効になる" % key9)
    # ⭐ **部材実測を持つべき物は、欄ごと消せない**(2026-09-06 検図方 5 の第2の穴)。
    #   ⛔ `noki` の欄を削ると const の既定へ静かに落ちるので、**確度P の値が黙って消える**。
    #   ⇒ **名指しの一覧**(`const.nokiMeasured`)を突き合わせる。
    have9 = dict((o["name"], o) for o in d["munes"] + d.get("service", []))
    for nm9 in C.get("nokiMeasured", []):
        o9 = have9.get(nm9)
        if o9 is None:
            bad.append("`const.nokiMeasured` の %s という物が無い" % nm9)
        elif not isinstance(o9.get("noki"), dict):
            bad.append("%s に部材実測の `noki` が無い — 欄を消すと `const` の既定へ静かに落ちて"
                       "**確度P の実測値が黙って消える**" % o9.get("label", nm9))
    for o in d["munes"] + d.get("service", []):
        if o["name"] in ("Inari",):        # ⭕ 足形=部材の外形(名指しの例外)
            continue
        nk = o.get("noki") or {}
        de9 = nk.get("de", C.get("nokiDe", 0.0))
        tm9 = nk.get("tsuma", C.get("tsumaEnd", 0.0))
        if de9 <= 1e-9 or tm9 <= 1e-9:
            bad.append("%s の軒の出/妻の出が 0(軒 %.3f / 妻 %.3f)— "
                       "屋根が足形の外へ出ない建物は稲荷(足形=部材の外形)だけ"
                       % (o.get("label", o["name"]), de9, tm9))
    # ⭐ ⑩ **入側の勾配は母屋と同値**(同 中7)。⛔ `gesyaKobai` を 0.1 にしても 0件だった。
    #   ⭕ 設計の宣言(「母屋と同じ瓦勾配に採る」)そのものを測る。
    gk9, kb9 = C.get("gesyaKobai"), C.get("kawaraKobai")
    if gk9 is not None and kb9 is not None and abs(gk9 - kb9) > 1e-9:
        bad.append("`const.gesyaKobai` %.4f が `kawaraKobai` %.4f と違う — "
                   "入側は身舎の屋根がそのまま延びた一枚の流れなので**同じ勾配**でなければならない"
                   % (gk9, kb9))
    return bad


def band_todo(d):
    """**普請奉行/ユーザーへ差し戻す点**(意匠なので指図方では決められない)。

    ⛔ 面のはみ出しの検査と混ぜない — 混ぜると「指図が不成立」に見える(庭方の差し戻しと同じ扱い)。
    ⛔ **0件でも件数を出す**(0件と未実行を見分けられなくしない)。
    ⭐ 2026-09-06 に3件が裁定で閉じた(正方形2棟の帯の向き=平入り / 格は座敷飾と棟の配置で /
    書院の棟高=身舎で測る)。⛔ **関数は残す** — 同じ型の未決はまた出る。
    """
    out = []
    for m in d["munes"]:
        rf = m.get("roof") or {}
        if not rf.get("banded"):
            continue
        bd = rf.get("bands") or {}
        if bd.get("along") is None:
            out.append("**%s の帯の向きが未決** — 足形が正方形で、帯数(%s本)・帯の身舎"
                       "(%.4g間)・棟高(%.4gm)は向きに依らず確定している。"
                       "平面の向きだけが意匠(`_pending.bandmuki`)"
                       % (m["name"], bd.get("n"), bd.get("w", 0.0), bd.get("ridgeH", 0.0)))
        if not rf.get("fukizai"):
            out.append("**%s の葺材(格の表示)が未決** — 案Cで屋根の型でも棟高でも格を"
                       "分けられなくなったので、葺材で分ける(`_pending.kakusa`)" % m["name"])
    return out


def _rank_cap(d):
    """**棟高の序列を機械で刷る。**⛔ 「書院がいちばん高い」を文章で断言しない — 測って出す。

    ⭐⭐ **2026-09-06 検図方 高2 で「御殿の7棟」から「蔵・表長屋・厩・門を含む全建物」へ広げた。**
    ⚠ **附属屋との比較が図のどこにも無く、逆転が読めなかった** — 実測で
    **御土蔵 6.867m > 御殿の最高 6.498m**。
    ⭕ **裁定C(このまま)**: **土蔵は2階建て・御殿は平屋**なので、蔵の棟が高いのは江戸として
    尤もらしい【U・2026-09-06 普請奉行】。⛔ 蔵を下げも軒高もいじらない。
    ⚠ **床上と絶対で順が変わる** — 面の高さが建物ごとに違うから。⛔ 混ぜて語らない。
    ⚠ 同値は「＝」で結ぶ(⛔ 「＞」で並べない。2026-09-06 検図方 低4)。
    """
    C = d["const"]
    ge, fl = C.get("gotenEave"), C.get("gotenFloor", 0.0)
    if ge is None or not C.get("kawaraKobai"):
        return ""
    rs = []
    for m in d["munes"]:
        rf = m.get("roof") or {}
        if rf.get("ridgeH") is not None:              # 部材方の実測がある棟(厩)
            rs.append((MUNE_JA.get(m["name"], m["name"]), rf["ridgeH"], m["y"] + rf["ridgeH"]))
            continue
        h = mune_ridge_above(d, m, ge)
        rs.append((MUNE_JA.get(m["name"], m["name"]), fl + h, m["y"] + fl + h))
    for o in d.get("service", []):
        _, rg = svc_roof(d, o)
        if rg is None:
            continue
        rs.append((o.get("label", o["name"]), rg, o["y"] + rg))
    g9 = d.get("gate") or {}
    if g9.get("plan", {}).get("monH") is not None:
        rs.append(("表門", g9["plan"]["monH"], g9["sill"] + g9["plan"]["monH"]))
    nr = C.get("nagayaRidge")
    if nr is not None:
        rs.append(("表長屋", nr, None))

    def _line(items):
        out, run = [], []
        for nm, h in items:
            if run and abs(run[-1][1] - h) < 0.005:
                run.append((nm, h))
                continue
            if run:
                out.append("＝".join(q[0] for q in run) + " %.2f" % run[0][1])
            run = [(nm, h)]
        if run:
            out.append("＝".join(q[0] for q in run) + " %.2f" % run[0][1])
        return " ＞ ".join(out)

    f = sorted(((a9, b9) for a9, b9, _ in rs), key=lambda q: -q[1])
    g = sorted(((a9, c9) for a9, _, c9 in rs if c9 is not None), key=lambda q: -q[1])
    return ("<p class='cap'>⭐ <b>棟高の序列 — 全建物</b>(機械で毎回並べ直す)。"
            "⚠⚠ <b>地盤上と絶対で順が変わる</b> — 面の高さが建物ごとに違うから。⛔ 混ぜて語らない。<br>"
            "<b>地盤上</b>(建物そのものの高さ): %s<br>"
            "<b>絶対</b>(建ったときに目に映る側): %s<br>"
            "⛔⛔ <b>この表は並べるだけ。序列を「正しい/誤り」と評価しない</b>"
            "(2026-09-06 考証方 高1)— <b>棟高の序列を書いた史料は台帳に無い</b>。"
            "⭐ <b>棟高は梁間の従属値であって格の表示ではない</b>【U】 — 身舎の広い棟ほど高くなる。"
            "⚠ <b>表向の書院(身舎 4間)が中奥・奥向(身舎 5間)より低い</b>が、"
            "⛔ <b>これは身舎の広さの差であって格の判断ではない</b>。"
            "⭕ [二条城二の丸御殿]A でも<b>最大の棟(大広間)が複合で最大</b>で、"
            "<b>大きい棟が高いこと自体は現存例と矛盾しない</b>。"
            "⭕ <b>御土蔵が御殿より高いのは、土蔵が2階建て・御殿が平屋だから</b>"
            "【U・2026-09-06 普請奉行の裁定=このまま】。⛔ 蔵を下げも軒高もいじらない。"
            "⚠ <b>絶対高で中奥(居間)が御殿でいちばん高い</b>のは、"
            "<b>身舎が最も広く(14 × 10間)、かつ中奥の面が表向より高い</b>ためで、"
            "⛔ <b>屋根の作りの問題ではない</b>。"
            "⭕ <b>御殿の最低の棟高(地盤上)が表長屋を下回らないこと</b>だけは "
            "<code>band_check</code> が毎回測る(規則19)— "
            "⛔ <b>御殿の内側の序列は検査にしない</b>。</p>"
            % (_line(f), _line(g)))


def roof_table(d):
    """御殿の屋根 — **帯の割り付けと、焼くのに要る寸法を棟から機械で出す**。

    ⛔ 寸法を指図に手で並べない — 棟を動かせば帯も屋根も変わる。
    ⚠ `EdoAssets.Own.GotenRoofIrimoya(wKen, dKen)` は **桁行 ≥ 梁間** で呼ぶ規約
    (足りない向きで呼ぶと大棟が短辺に架かる)。
    """
    C = d["const"]
    K = C["ken"]
    kb = C.get("kawaraKobai")
    ge = C.get("gotenEave")
    fl = C.get("gotenFloor", 0.0)
    mb = C.get("moyaBand") or {}

    def _ridge(m, a, b):
        """**大棟の向き。**⛔ 実装に選ばせない(規則5と同じ理屈)。

        ⚠ 2026-09-06 の普請検査で、居間棟(16×12間)の大棟が**12間側**に架かり
        16間 を梁間で飛ばして棟高 10.3m になっていた(中奥が御殿でいちばん高い姿)。
        向きが指図に無かったのが原因なので、`munes[].roof.ridge` を正典に立てた。
        """
        rf = m.get("roof") or {}
        r = rf.get("ridge")
        if r is None:
            return "<b>該当なし</b>(正方形)"
        ok = abs(a - b) < 1e-9 or (r == "u") == (a > b)
        return ("<b>%s 方向</b>【%s】%s"
                % (r, _cert(rf, "ridge"), "" if ok else " ⚠ 短辺に架かる"))

    def _h(m):
        """**棟高**(床上 m と絶対高)。帯に割った棟は**帯の身舎**から、割らない棟は梁間から。"""
        if kb is None or ge is None:
            return "⚠ `const` に軒高か瓦勾配が無い"
        h = mune_ridge_above(d, m, ge)
        rf = m.get("roof") or {}
        if rf.get("ridgeH") is not None:                   # 部材方の実測がある棟(厩)
            return ("棟高 <b>%.2f</b>(地盤上)/ 軒高 %.2f【%s】(部材方の実測)"
                    % (rf["ridgeH"], rf["eaveH"], _cert(rf, "height")))
        bd = rf.get("bands") or {}
        if bd.get("ridgeH"):
            # ⚠ **帯ごとに高さが違う**(4間帯と5間帯が混ざる)。⛔ 代表値ひとつに丸めない。
            return ("床上 <b>%s</b>m<br>地盤上 <b>%s</b>m<br>絶対 <b>%s</b>m<br>"
                    "帯の身舎 %s間 より【%s】"
                    % (" / ".join("%.2f" % q for q in bd["ridgeH"]),
                       " / ".join("%.2f" % q for q in bd["ridgeG"]),
                       " / ".join("%.2f" % q for q in bd["ridgeY"]),
                       "+".join("%g" % w for w in bd["ws"]), _cert(rf, "height")))
        src = ("梁間 %.4g間" % ((m["v1"] - m["v0"]) if rf.get("ridge") == "u"
                                else (m["u1"] - m["u0"]) if rf.get("ridge") == "v"
                                else min(m["u1"] - m["u0"], m["v1"] - m["v0"])))
        return ("床上 <b>%.2fm</b>(軒高 %.2f + 起り %.2f)<br>絶対 <b>%.2fm</b><br>%s より"
                % (h, ge, h - ge, m["y"] + fl + h, src))

    def _call(m):
        rf = m.get("roof") or {}
        bd = rf.get("bands") or {}
        if bd.get("n"):
            al = bd.get("moyaAlong")
            need = collections.OrderedDict()
            for w in bd["ws"]:
                need["%g×%g" % (al, w)] = need.get("%g×%g" % (al, w), 0) + 1
            return ("＋".join("<code>Irimoya(%s間)</code> ×<b>%d</b>" % (k, v)
                             for k, v in need.items())
                    + "<br>= %s ＋ <b>入側 %.4g間 は同じ流れで延ばす</b>(⛔ 段を付けない)<br>"
                      "⛔ <b>一枚屋根の FBX は使えない</b>(<code>_pending.yane</code>)"
                      % (" / ".join("%.2f × %.2fm" % (al * K, w * K) for w in sorted(set(bd["ws"]))),
                         mb.get("irikawa", 1.0)))
        if rf.get("kata"):
            return "<b>%s</b>【%s】" % (rf["kata"], _cert(rf, "kata"))
        a, b = m["u1"] - m["u0"], m["v1"] - m["v0"]
        if not m.get("goten"):
            # ⛔ **型が指図に無い棟に呼び出しを書かない**(厩)。⚠ 間数を丸めると
            #   5.5間 が 6間 に化けて、指図に無い寸法の部材を名指ししてしまう。
            return ("⚠ <b>型が指図に無い</b>【?】 — <code>_pending.yanekata</code><br>"
                    "足形 %.4g × %.4g間(⛔ 実装で型を決めない)" % (max(a, b), min(a, b)))
        if abs(a - round(a)) > 1e-9 or abs(b - round(b)) > 1e-9:
            return "⚠ <b>足形が整数の間数でない</b>(%.4g × %.4g間)" % (max(a, b), min(a, b))
        return ("<code>Own.GotenRoofIrimoya(%d, %d)</code>"
                % (int(round(max(a, b))), int(round(min(a, b)))))

    rows = []
    for m in sorted(d["munes"], key=lambda q: (not q.get("goten"), q["name"])):
        a = m["u1"] - m["u0"]
        b = m["v1"] - m["v0"]
        r0, s0, r1, s1 = moya_rect(d, m)
        nm = m["name"] + ("" if m.get("goten") else "(<b>御殿でない</b>)")
        # ⚠ 入側を持たない棟(厩)に身舎を出さない — 引き算しただけの数字は意味を持たない
        moya = ("%.4g × %.4g間" % (r1 - r0, s1 - s0)
                if (m.get("goten") or (m.get("roof") or {}).get("banded"))
                else "—(<b>入側を持たない</b>)")
        fk = (m.get("roof") or {}).get("fukizai")
        rows.append((nm, "u %.4g間 × v %.4g間" % (a, b), moya,
                     _band_desc(d, m), _tani_desc(d, m), _ridge(m, a, b), _h(m),
                     ("<b>%s</b>【%s】" % (fk, _cert(m.get("roof"), "fukizai")) if fk
                      else "—" if not (m.get("roof") or {}).get("banded")
                      else "⚠ <b>未決</b>(<code>_pending.kakusa</code>)"),
                     _call(m)))
    return _tw(("棟", "足形", "身舎", "<b>帯</b>", "<b>谷</b>", "大棟の向き",
                "<b>棟高</b>", "<b>葺材</b>", "屋根の型 / 呼び出し"), rows) + (
        "<p class='cap'>⭐⭐ <b>2026-09-06 ユーザー裁定=案C — 身舎を平行な帯に割り、"
        "帯の境は谷で受ける。</b>対象は<b>6棟</b>"
        "(御殿複合=玄関・書院・居間・奥・台所 ＋ 表役所)【線引きもU】。"
        "⛔ <b>足形・室割り・廊下・御錠口は一つも動いていない</b> — 動いたのは屋根の層だけ。"
        "⭕ 割り付けは <b>帯の身舎を %s間 の整数</b>に採り、<b>%g間 を基本</b>として"
        "<b>割り切れない棟は %g間 で吸う</b>(⛔ 5間の帯は端側へ)。<b>帯数は最小</b>"
        "(⛔ 谷を増やさない)。<code>const.moyaBand</code> が正典。"
        "帯数・帯の身舎・棟高・谷の位置は<b>すべて足形からの従属値</b>(⛔ 手で書かない)。"
        "⭕ <b>身舎 = 足形 − 入側 %.4g間 × 2</b>(2026-08-14 ユーザー裁定=外周に1間)。"
        "⛔ <b>帯の境に入側を作らない</b> — 背中合わせの2間廊下になるので、境は谷。"
        "⚠⚠ <b>台帳の実測(門・長屋の本体 2.5〜3間)を上回るのは承知のうえで、"
        "柱割を優先して 4〜5間 を採る</b>【U】。⛔ <b>江戸間 1間 = 柱の心々</b>で、"
        "<b>谷は柱通りの上にしか置けない</b> — 端数の帯は谷を柱通りから外す。"
        "⭕ [西川1959]A の 2.5〜3間 は原文が<b>「長屋の構造をみると」</b>と限定した値で、"
        "<b>御殿の身舎に当てる根拠が無い</b>(2026-09-06 考証方)。"
        "⭕ [二条城二の丸御殿]A の梁間 3〜8間・中央値6間(棟全体)とも<b>矛盾しない範囲</b>。"
        "⛔ <b>経緯は書かない</b> — 途中で採った目標幅の案は撤回済み(`git log` が持つ)。</p>"
        % ("〜".join("%g" % w for w in mb["widths"]), mb["base"], max(mb["widths"]),
           mb["irikawa"])) + (
        "<p class='cap'>⚠⚠ <b>帯幅 %s間 は恒久的に【確度U】。</b>"
        "⛔ <b>ユーザーに照会済みで、御殿の差図の心当たりは無い(2026-09-06)。</b>"
        "台帳にある梁間の実測は<b>門・長屋の4件だけ</b> — [西川1959]A「三間梁以下+庇一間」/ "
        "[根岸家長屋門修理報告書]A 3間 / [西澄寺武家屋敷門]A 2.5間 / [山脇武家屋敷門]A 4.7m で、"
        "<b>本体 2.5〜3間・3間を超える例はゼロ</b>。"
        "<b>御殿の身舎の梁間は台帳にもユーザーの手元にも無い</b>ので、"
        "⛔ <b>U から上がる見込みは無い(再照会しない)</b>。"
        "⚠ 前巡の「3〜5間なら類型と矛盾しない【B】」は<b>考証方自身が【U】へ訂正した</b> — "
        "確度Bで読まないこと。"
        "⚠ [西川1959]A の原文は<b>「片側に入側」</b>で、<b>四周に1間回すのは裁定であって"
        "史料ではない</b>【U】。</p>" % "〜".join("%g" % w for w in mb["widths"])) + (
        "<p class='cap'>⭐ <b>棟高は「軒高 %.4g + 帯の身舎 ÷ 2 × 江戸間 × 瓦勾配 %s」</b>。"
        "⛔ <b>足形の梁間で計算しない</b> — 帯に割った意味(棟を高くしない)が消える。"
        "⚠ <b>軒高 %.4g は設計値から導けない</b>【U・図示のための概略】ので "
        "<code>const.gotenEave</code> に置き、<b>同じ数字を持つ断面の <code>eaveAbove</code> と"
        "一致するかを <code>band_check</code> が毎回測る</b>(規則19)。"
        "⚠ <code>kawaraKobai</code> %s 自体も【U】 — [西川1959] の6寸は<b>長屋</b>の値で、"
        "御殿の屋根へそのまま外挿できない。"
        "⛔ <b>焼けた屋根部材の実測があるときはそちらが正</b>。</p>"
        % (ge or 0, ("%.4f" % kb) if kb else "⚠ const に無い", ge or 0,
           ("%.4f" % kb) if kb else "—")) + (
        "<p class='cap'>⭐⭐ <b>入側(外周1間)は身舎の屋根がそのまま延びた一枚の流れで覆う</b>"
         "【U・2026-09-06 普請奉行】。⛔ <b>段は付けない・「下屋」と読まない</b> — "
         "部材方が試し焼きを目で見て「<b>噛んでいる以前に境が見えない</b>。"
         "『下屋も同じ勾配』の帰結で身舎の流れと<b>一枚の平面</b>になる」と報告した。"
         "⭕ <b>幾何はこのままで正しく、誤っていたのは指図の言葉のほう</b>。"
         "⛔ 「下屋」は<b>段のある庇を焼け</b>と読める。<br>"
         "⭕ <b>入側の先の軒先高</b>(勾配 <code>const.gesyaKobai</code> %.4f)= "
         "<b>床上 %.3fm ／ 地盤上 %.3fm</b>、"
         "<b>軒の出 %.2fm の先端</b>まで下がって <b>床上 %.3fm ／ 地盤上 %.3fm</b>。"
         "⚠⚠ <b>基準を混ぜない</b> — <b>断面は御殿を床から</b>"
         "(床 = 面 + <code>gotenFloor</code> %.2f)<b>・附属屋と厩を地盤から</b>描き、"
         "<b>この表は床上・地盤上・絶対の3つを並べて刷る</b>。"
         "⛔ <b>数字だけを抜き書きしない</b> — どの基準かを必ず添える。⭕ 立位の眼高 %.2fm に対し軒先まで <b>%.3fm</b> の余裕。"
         "⛔ 「軒先が低すぎる」と読み違えない(普請奉行・部材方とも一度取り違えた)。</p>"
         % (C.get("gesyaKobai") or 0.0,
            (ge or 0) - mb.get("irikawa", 1.0) * K * (C.get("gesyaKobai") or 0.0),
            fl + (ge or 0) - mb.get("irikawa", 1.0) * K * (C.get("gesyaKobai") or 0.0),
            C.get("nokiDe", 0.0),
            (ge or 0) - (mb.get("irikawa", 1.0) * K + C.get("nokiDe", 0.0)) * (C.get("gesyaKobai") or 0.0),
            fl + (ge or 0) - (mb.get("irikawa", 1.0) * K + C.get("nokiDe", 0.0)) * (C.get("gesyaKobai") or 0.0),
            fl, C.get("eyeStand", 0.0),
            fl + (ge or 0) - (mb.get("irikawa", 1.0) * K + C.get("nokiDe", 0.0)) * (C.get("gesyaKobai") or 0.0)
            - C.get("eyeStand", 0.0))) + (
        "<p class='cap'>⭕ <b>谷は帯の境ごとに1本、大棟と平行</b>(松江松平の「軒谷」型)。"
        "谷樋は<b>中央から両端の軒先へ %s で振り分けて落とし、縦樋を立てない</b>。"
        "⚠⚠ <b>谷樋の作法は【U】で、典拠台帳に ID は無い</b> — ⛔ <b>P ではない</b>"
        "(P は「プロジェクト内実測」。この作法は一般類型で、しかも<b>松江松平の成果物に倣った</b>もの — "
        "⛔ <b>自分の成果物を基準に norm を作らない</b>=規則8。2026-09-06 考証方 中5)。"
        "⛔ 史料の裏づけがあるかのように書かない。</p>"
        % (("1/%d" % round(1.0 / C["taniFall"])) if C.get("taniFall") else "⚠ 未定")) + (
        _rank_cap(d) + (
        "<p class='cap'>⭐⭐ <b>御殿6棟はすべて桟瓦</b>【U】 — "
        "<b>安政期の中小譜代の御殿として桟瓦は無理がない</b>。"
        "⛔⛔ <b>「御殿の葺材は家格で分かれる」は撤回した</b>(2026-09-06 考証方 高3)。"
        "⑴ <b>桟瓦は延宝2年(1674)の発明</b>([桟瓦の起源]A)なので "
        "[二条城二の丸御殿]A(1626)は<b>桟瓦を選べない年代</b>で、階梯の点にならない。"
        "⑵ [高知城懐徳館]A(1749・24万石・<b>本丸</b>)と [掛川城御殿]A(1855・5万石・<b>二の丸</b>)は"
        "<b>石高・年代・本丸/二の丸が完全に交絡</b>していて、"
        "「家格で分かれる」と「年代で分かれる」が<b>同じだけ支持される</b>。"
        "⭕ <b>支えは交絡していない2点だけ</b>: (a) [掛川城御殿]A が"
        "<b>譜代・地震の翌年に竣工</b>という当家と同条件の唯一の現存例 "
        "(b) 桟瓦の普及が<b>享保5年(1720)の瓦葺奨励以降で武家屋敷から始まった</b>"
        "([桟瓦の起源]A)。"
        "⚠ <b>確度は B ではなく U</b> — 台帳の B は「複数文献から導かれる<b>型</b>」で、"
        "いまの点は<b>型を成していない</b>。"
        "⛔⛔ <b>当家の格では葺材で棟ごとの格を分けない</b>【U】 — [掛川城御殿]A は"
        "<b>広間・書院部/小書院部/諸役所部が全部1棟で全部桟瓦</b>。"
        "⛔ ただし<b>一般命題として書かない</b> — [二条城二の丸御殿]A には"
        "<b>車寄だけ檜皮葺</b>という反例がある(2026-09-06 考証方 中4)。"
        "⚠⚠ <b>表門・表長屋は本瓦のまま</b>だが、その確度は<b>【B以下】</b>であって A ではない。"
        "⛔ [山脇武家屋敷門]A が言うのは<b>山脇の門の葺材</b>であって一般則ではない — "
        "御殿側で B とした外挿と構造が同じ。⚠ さらに同門は<b>文久2年(1862)再建</b>で"
        "<b>基準年次(安政3年=1856)より後</b>、台帳自身が<b>嵩上げの可能性</b>を注記している"
        "(⛔ 弱い環を隠さない)。"
        "⚠⚠ <b>反対材料を併記する</b>: [下丸子武家屋敷門]A「とくに遺存例の少ない"
        "<b>1〜5万石の小大名格</b>の形式をよく伝えており…一重、入母屋造、<b>桟瓦葺</b>、"
        "片番所格子付、片潜門」— <b>当家と同じ石高帯の官製記録が桟瓦</b>である。"
        "⭕ <b>それでも表門・表長屋の葺材は動かさない</b>(部材が焼成済み・据え付け済み)。"
        "到達先は <code>_pending.monfuki</code>。"
        "⚠ <b>「街路に見える面は本瓦・内側は桟瓦」には典拠 ID も確度も無い</b> — "
        "<b>【U・2026-09-06 普請奉行の判断】</b>。⛔ 類型のように書かない。</p>"
        "<p class='cap'>⛔⛔ <b>屋根で格を分けない。</b>①型では分けられない(全棟が入母屋の並び)"
        "②棟高でも分けられない(帯幅の従属値なので揃う)③破風飾りは撤回(数が格の逆順・"
        "平入りで見えない)④葺材も家格で一律。⭕ <b>格を示す軸は確度Aで既に当図が持っている2つ</b>: "
        "①<b>座敷飾</b>([二条城二の丸御殿]A「上段の間があり、そこには書院造の格式である"
        "<b>床、棚、書院を構え、帳台構を設ける</b>」/ [高知城懐徳館]A「上段の間(床、棚、書院付)」)"
        "— 当図の<code>書院上段</code>が受ける ②<b>棟の配置</b>(表向 → 中奥 → 奥向・[西川1959]A)。</p>"
        "<p class='cap'>⭐ <b>書院も帯の対象</b>(身舎 4 × 12間 = <b>帯1本・谷0本</b>)。"
        "⭕ <b>棟高を身舎 4間 で測る</b> — 他の棟をすべて身舎で測る以上、書院だけ足形の梁間"
        "6間 で測るのは不整合(2026-09-06 普請奉行の裁定=U)。</p>"
        "<p class='cap'>⭐⭐ <b>棟高は梁間の従属値であって、格の表示ではない</b>【U】。"
        "身舎の広い棟ほど高くなる。⇒ 当図で最も高いのは<b>居間(身舎 14 × 10間)</b>で、"
        "<b>これは幾何の帰結</b>。⭕ [二条城二の丸御殿]A でも<b>最大の棟(大広間)が複合で最大</b>であり、"
        "<b>大きい棟が高いこと自体は現存例と矛盾しない</b>。"
        "⛔⛔ <b>棟高の序列を書いた史料は台帳に無い</b>(2026-09-06 考証方)ので、"
        "⛔ <b>序列を「正しい/誤り」と評価しない</b> — この図は<b>並べるだけ</b>にする。"
        "⛔ <b>「書院 ≧ 中奥・奥向」を検査にしない</b> — 典拠の無い規則を機械に固めることになる。</p>"
        "<p class='cap'>⛔ <b>帯に割らない棟は名指しの例外だけ</b>"
        "(<code>const.moyaBand.exempt</code>): <b>%s</b>。⛔ <b>厩・附属屋は対象外</b>【U】 — "
        "⚠ <b>厩は棟高 5.42 / 軒高 2.35</b>(2026-09-06 部材方の案B)で、"
        "⭕ 格を分けるため表長屋(棟高 5.509)より低い。"
        "⚠ 厩の<b>型</b>はまだ「板壁・桟瓦」【型=B / 姿=U】までで、切妻か寄棟かは"
        "決まっていない(<code>_pending.yanekata</code>)。⛔ 実装で型を決めない。</p>"
        % " / ".join(mb.get("exempt", []) or ["—"]))) + (
        "<p class='cap'>⛔ <b>寸法を指図に手で並べない</b> — 棟を動かせば屋根も変わるので、"
        "この表は <code>munes</code> から毎回組む。⚠ <b>桁行 ≥ 梁間 で呼ぶ</b>。"
        "⚠ <b>屋根の外形は間数より 2.14m 大きい</b>(軒の出 0.90 が四周に付く)— "
        "<b>棟の壁面で合わせない</b>。⛔ <b>隣り合う帯の軒どうしを重ねない</b> — 境は谷で受ける。"
        "無い寸法は <code>blender --background --python Tools/Blender/build_goten_roof.py -- "
        "&lt;桁行m&gt; &lt;梁間m&gt; &lt;名&gt;</code>。</p>")


def buzai_table(d):
    """**部材方への依頼票 = `bom` の「新造」の行**。⛔ 別の名簿を作らない(二重の正典を作らない)。"""
    rows = []
    for b in d.get("bom", []):
        if not b.get("build"):
            continue
        rows.append((b["item"],
                     ("<b>%s</b>" % b["how"]) if b.get("how") else "⚠ <b>手当て未定</b>",
                     "<code>%s</code>" % b.get("asset", "—"),
                     ("<code>_pending.%s</code>" % b["ask"]) if b.get("ask") else "—",
                     b.get("note", "")))
    if not rows:
        return "<p class='cap'>⭕ <b>新造を要する部材: 0 件。</b></p>"
    nh = sum(1 for b in d.get("bom", []) if b.get("build") and not b.get("how"))
    st = sum(1 for b in d.get("bom", []) if str(b.get("how", "")).startswith("焼成済"))
    return _tw(("要る物", "手当て", "名", "宿題", "断り"), rows) + (
        "<p class='cap'>⭐ <b>2026-09-06 部材方の第1段で全行に手当てが付いた</b>"
        "(手当て未定 <b>%d 行</b>)。うち <b>%d 行が焼成済</b>。"
        "⚠⚠ <b>実体はまだ <code>Assets/</code> に無く、部材方の staging に在るだけ</b> — "
        "配置と <code>EdoAssets</code> への登録は<b>第2段</b>(<code>_pending.buzai2</code>)で、"
        "⛔ <b>それまで棟梁は据えられない</b>(<code>LoadAssetAtPath</code> は例外を投げず "
        "null を返すので、無い物を指しても静かに壊れる=規則12)。"
        "⚠ <b>FBX を入れたらマテリアルを remap する</b>(やらないと全部真っ白になる)。</p>"
        % (nh, st)) + (
        "<p class='cap'>⭐ <b>これは `bom` の「新造」の行をそのまま並べた view で、別の名簿ではない</b>"
        "(⛔ 同じ事実を二重に書かない=規則4)。新造が済んだら <code>bom[].build</code> を "
        "<code>false</code> にし、<code>asset</code> を <code>EdoAssets</code> の名へ差し替える。"
        "⚠ <b>綴りは <code>Assets/Edo/Scripts/Editor/EdoAssets.cs</code> の実在名で書く</b> — "
        "<code>LoadAssetAtPath</code> は例外を投げず null を返すので、誤字は静かに壊れる"
        "(規則12)。⛔ パスの literal を指図に書かない。</p>")


def pending_table(d):
    """**未決の宿題を図に出す。**⛔ 正典に持つだけでは誰の目にも入らない(規則19)。"""
    p = d.get("_pending") or {}
    if not p:
        return ""
    live, done = [], []
    for k, v in p.items():
        t = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        (done if ("閉じた" in t[:40] or "追わない" in t[:40] or "輪に入った" in t[:40])
         else live).append((k, t))
    rows = [("<code>%s</code>" % k, t) for k, t in live]
    out = ("<p class='cap'><b>開いている宿題 %d 件 / 閉じた %d 件。</b>"
           "⛔ <b>閉じたものも消さない</b> — 消すと同じ問いが再び立つ。"
           "⚠ 2026-09-06 まで <code>_pending</code> は生成器が一度も読んでおらず、"
           "<b>宿題がユーザーの見る文書に一行も出ていなかった</b>"
           "(部材の新造依頼もここに埋もれていた)。</p>" % (len(live), len(done)))
    out += _tw(("宿題", "中身"), rows)
    out += "<h3>閉じた宿題(記録として残す)</h3>"
    out += _tw(("宿題", "顛末"), [("<code>%s</code>" % k, t) for k, t in done])
    return out


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


# ---------------------------------------------------------------- 奥庭(池庭)
# ⚠ **ここで算出する値を設計値へ写さない。**面積・水面比・周長・円形度・辺長CV・見隠れ・
#   土量・園路の全長・石段の段数・沢飛石の石数・護岸石の個数・杭の本数・汀からの離れは
#   すべて従属値で、庭方の設計書にある数字は「検算の答え合わせ用」である。
#   → 正典は `gardens.G_Okuniwa` の入力欄だけ。

_ASSET_DIM = [None]


def asset_dim(name):
    """`docs/asset-index.tsv` から目録名で W/H/D[m] を引く。**部材の実寸は目録が正典。**"""
    if _ASSET_DIM[0] is None:
        tb = {}
        p = os.path.join(os.path.dirname(DOC), "asset-index.tsv")
        if os.path.exists(p):
            for ln in open(p, encoding="utf-8"):
                c = ln.rstrip("\n").split("\t")
                if len(c) > 6:
                    try:
                        tb.setdefault(c[1], (float(c[4]), float(c[5]), float(c[6])))
                    except ValueError:
                        pass
        _ASSET_DIM[0] = tb
    return _ASSET_DIM[0].get(name)


def niwa(d):
    """池を持つ庭(=奥庭)。無ければ None。"""
    return next((g for g in d.get("gardens", []) if g.get("migiwa")), None)


def _shoelace(p):
    s = 0.0
    for i in range(len(p)):
        a, b = p[i]
        c, e = p[(i + 1) % len(p)]
        s += a * e - c * b
    return abs(s) / 2.0


def _segd(p, a, b):
    px, pz = p
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = 0.0 if (dx == 0 and dy == 0) else max(0.0, min(
        1.0, ((px - a[0]) * dx + (pz - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - a[0] - t * dx, pz - a[1] - t * dy)


def _seg_cross(p, q, r, s):
    """線分 pq と rs が交わるか(端点で触れるだけは交わりとしない)。"""
    def cr(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = cr(r, s, p), cr(r, s, q)
    d3, d4 = cr(p, q, r), cr(p, q, s)
    return (d1 * d2 < -1e-12) and (d3 * d4 < -1e-12)


def _pip(pt, poly):
    x, y = pt
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                c = not c
    return c


class Niwa(object):
    """奥庭の地形モデル。**設計値から毎回組み直す**(静的な派生値を正典に置かない)。"""

    def __init__(self, d):
        self.d = d
        self.g = niwa(d)
        self.ken = d["const"]["ken"]
        g = self.g
        self.mg = g["migiwa"]
        self.pond = [(a, b) for a, b in self.mg["pts"]]
        self.base = design_y(d, (g["u0"] + g["u1"]) / 2.0, (g["v0"] + g["v1"]) / 2.0)
        self.waterY = self.mg["waterY"]
        self.depth = self.mg["depthMax"]
        # 汀からの最大距離(池床の放物面の正規化に使う)
        self.dmax = 0.0
        for u, v in self._cells(0.1):
            if self.inpond(u, v):
                self.dmax = max(self.dmax, self.dshore(u, v))
        self.dmax = self.dmax or 1.0

    # -------- 格子
    def _cells(self, st):
        g = self.g
        u = g["u0"]
        while u <= g["u1"] + 1e-9:
            v = g["v0"]
            while v <= g["v1"] + 1e-9:
                yield (u, v)
                v += st
            u += st

    # -------- 池
    def inpond(self, u, v):
        return _pip((u, v), self.pond)

    def dshore(self, u, v):
        return min(_segd((u, v), self.pond[i], self.pond[(i + 1) % len(self.pond)])
                   for i in range(len(self.pond)))

    def bed(self, u, v):
        sh = self.mg.get("shallow")
        if sh and sh["v0"] <= v <= sh["v1"]:
            return sh["bedY"]
        return self.waterY - self.depth * (self.dshore(u, v) / self.dmax) ** 0.6

    # -------- 築山
    def mound_one(self, t, u, v):
        """**その一基だけ**の盛り上がり。⛔ 法(勾配)を測るときは `mound`(全基の max)で
        測らない — 隣に別の盛土が重なっていると**他基の斜面を自分の法として拾う**
        (2026-09-04: 蔵前の土手を短辺減衰に直した途端、築山A1/A2/C の実測が
        いずれも土手の 1:0.85 に化けた)。"""
        return self._m1(t, u, v)

    def mound(self, u, v):
        h = 0.0
        for t in self.g.get("tsukiyama", []):
            h = max(h, self._m1(t, u, v))
        return h

    def _m1(self, t, u, v):
        h = 0.0
        for t in (t,):
            if t.get("kata") == "土手":
                # ⭐ **減衰軸は `decay` が決める**(2026-09-04 庭方の第4巡)。
                #   ⛔ v 固定にしていたため、長辺が v の `Dote_Kuramae` は
                #   **両端が 0 になる蒲鉾**になり、壁の足元に一様な稜線が通っていなかった
                #   (御土蔵の見える面に 0.5% の素通しが残った原因)。
                #   ⛔ **未指定を既定へ倒さない** — `dote_check` が鳴らす。
                if t["u0"] <= u <= t["u1"] and t["v0"] <= v <= t["v1"]:
                    if t.get("decay") == "u":
                        r = abs(u - (t["u0"] + t["u1"]) / 2.0) / ((t["u1"] - t["u0"]) / 2.0)
                        a9, a0, a1 = v, t["v0"], t["v1"]      # 稜線の走る軸
                    else:
                        r = abs(v - (t["v0"] + t["v1"]) / 2.0) / ((t["v1"] - t["v0"]) / 2.0)
                        a9, a0, a1 = u, t["u0"], t["u1"]
                    # ⭐ **稜線の両端も cos で摺り付ける**(`taperEnds`[間]。2026-09-04 庭方の裁定)。
                    #   ⛔ 従前は端が**垂直に切れて**いた(蔵前 0.65m・東 0.35m の段)。
                    #   ⚠ 東の土手の端の段は主路の点#6 が踏む **0.23m の設計外の一段**になっていた。
                    #   ⭕ 端も法面なので、法の検査は摺り付けを含めて全周で見る。
                    te = t.get("taperEnds")
                    f9 = 1.0
                    if te:
                        d9 = min(a9 - a0, a1 - a9)
                        if d9 < te:
                            f9 = 0.5 * (1 - math.cos(math.pi * max(d9, 0.0) / te))
                    h = max(h, t["rise"] * f9 * 0.5 * (1 + math.cos(math.pi * min(r, 1.0))))
                continue
            ru, rv = t["dU"] / 2.0, t["dV"] / 2.0
            x, y = (u - t["u"]) / ru, (v - t["v"]) / rv
            r = math.hypot(x, y)
            # 頂の平場(床几)は**山を切った平場**として持つ。⛔ 素の楕円丘に平場を
            # 「max で足す」と平場の縁が崖になり、園路の勾配が 65% に化ける
            # (2026-09-04 に踏んだ)。⭕ 正規化半径を平場の縁から裾へ引き伸ばす。
            rd = 0.0
            da = t.get("daira")
            if da and r > 1e-9:
                a = da["dU"] / 2.0 / ru
                b = da["dV"] / 2.0 / rv
                rd = 1.0 / math.hypot(x / (r * a), y / (r * b))
                rd = min(rd, 0.95)
            if r < 1.0:
                s = 0.0 if r <= rd else (r - rd) / (1.0 - rd)
                h = max(h, t["rise"] * 0.5 * (1 + math.cos(math.pi * s)))
        return h

    def ground(self, u, v):
        """造園後の地表。池の中は池床、外は面+築山。"""
        if self.inpond(u, v):
            return self.bed(u, v)
        return self.base + self.mound(u, v)

    # -------- 見所
    def eye(self, no):
        m = next((x for x in self.g["mikoro"] if x["no"] == no), None)
        if m is None:
            return None
        md = m.get("eyeMode")
        if md == "sit":
            return self.base + self.d["const"]["gotenFloor"] + self.d["const"]["eyeSit"]
        if md == "床几":
            return self.base + self.mound(m["u"], m["v"]) + self.d["const"]["eyeSit"]
        if md == "water":
            return self.waterY
        if md == "stand" and "eyeStand" in self.d["const"]:
            return self.base + self.mound(m["u"], m["v"]) + self.d["const"]["eyeStand"]
        return None

    # -------- 御土蔵(主景の対岸)
    def kura(self):
        k = next((s for s in self.d["service"] if s["name"] == "Kura1"), None)
        if k is None:
            return None
        c = self.d["const"]
        return dict(o=k, face=k["u1"], eave=k["y"] + c["kuraEave"],
                    wall=k["y"] + c["kuraWallTop"], ridge=k["y"] + c["kuraRidge"])


_NIWA_CACHE = [None, None]


def NI(d):
    if _NIWA_CACHE[0] is not d:
        _NIWA_CACHE[0] = d
        _NIWA_CACHE[1] = Niwa(d) if niwa(d) else None
    return _NIWA_CACHE[1]


_STATS_CACHE = [None, None]


def niwa_stats(d):
    """庭の従属値を**毎回**算出する。⛔ ここで出した数字を json へ書き戻さない。

    ⚠ **同じ `d` なら使い回す。**表・図・検査から十数回呼ばれるので、
    見切りの走査(蔵の面 120×28 本の視線)を足した 2026-09-04 に生成が 10秒 → 2分半 になった。
    ⛔ キャッシュは「同じ辞書オブジェクトか」だけで判定する(値の変化は `pipeline` の後には無い)。
    """
    if _STATS_CACHE[0] is d:
        return _STATS_CACHE[1]
    n = NI(d)
    if n is None:
        _STATS_CACHE[0], _STATS_CACHE[1] = d, {}
        return {}
    K = n.ken
    g, mg = n.g, n.mg
    P = n.pond
    A = _shoelace(P)
    per = sum(math.dist(P[i], P[(i + 1) % len(P)]) for i in range(len(P)))
    seg = [math.dist(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    mu = sum(seg) / len(seg)
    cv = (sum((s - mu) ** 2 for s in seg) / len(seg)) ** 0.5 / mu
    ga = (g["u1"] - g["u0"]) * (g["v1"] - g["v0"])
    st = 0.1
    cut = fill = pa = 0.0
    a1 = st * st * K * K
    for u, v in n._cells(st):
        if n.inpond(u, v):
            cut += (n.base - n.bed(u, v)) * a1
            pa += a1
        else:
            fill += n.mound(u, v) * a1
    land = ga * K * K - pa
    o = dict(areaKen=A, areaM2=A * K * K, tsubo=A * K * K / TSUBO,
             per=per * K, circ=4 * math.pi * A / per ** 2, cv=cv,
             gardenTsubo=ga * K * K / TSUBO, gardenM2=ga * K * K,
             waterPct=100.0 * A / ga, cut=cut, fill=fill, diff=cut - fill,
             level=(cut - fill) / land if land > 0 else 0.0, pondM2=pa, landM2=land,
             segMin=min(seg) * K, segMax=max(seg) * K)
    # 汀 → 庭境 / 棟
    bb = (min(p[0] for p in P), max(p[0] for p in P),
          min(p[1] for p in P), max(p[1] for p in P))
    o["clrBound"] = min(bb[0] - g["u0"], g["u1"] - bb[1], bb[2] - g["v0"], g["v1"] - bb[3])
    o["clrBoundBy"] = ["南", "北", "東", "西"][
        [bb[0] - g["u0"], g["u1"] - bb[1], bb[2] - g["v0"], g["v1"] - bb[3]].index(o["clrBound"])]
    best, bnm = 9e9, "?"
    ex = set(mg.get("clearance", {}).get("exempt", []))
    for m in d["munes"] + d["service"]:
        if "yaw" in m or m["name"] in ex:
            continue
        for (u, v) in P:
            du = max(m["u0"] - u, 0.0, u - m["u1"])
            dv = max(m["v0"] - v, 0.0, v - m["v1"])
            q = math.hypot(du, dv)
            if q < best:
                best, bnm = q, m["name"]
    o["clrMune"], o["clrMuneBy"] = best, bnm
    # ⭐ **軒先までの値も持つ**(2026-09-06 庭方 低2)。⛔ 躯体までの値だけを刷らない。
    _bm = next((m for m in d["munes"] + d["service"] if m["name"] == bnm), None)
    o["clrMuneEave"] = best - ((_bm or {}).get("noki", {}).get("de", d["const"]["nokiDe"])) / K
    # 水面と岸の高さ関係(**余裕高**)。⭐ 2026-09-04 検図方 中-5。
    # ⚠ 従前は水面の高さを見る検査が一つも無く、`waterY` を 27.40(面 26.60 より 0.8m 高い)に
    #   しても「水面が 100% 見える」しか鳴らなかった。⛔ 水は陸より高い所には溜まらない。
    #   ⭕ 汀線の各辺の**外向き法線**へ 0.3/0.6間 出た所の地表(`Niwa.ground` = 面+築山)を測り、
    #   水面との差(=余裕高)の最小を持つ。⛔ 閾値を発明しない — **判定は「正であること」**。
    sa = 0.0
    for i in range(len(P)):
        a9, b9 = P[i], P[(i + 1) % len(P)]
        sa += a9[0] * b9[1] - b9[0] * a9[1]
    sgn = 1.0 if sa > 0 else -1.0
    fb = []
    for i in range(len(P)):
        a9, b9 = P[i], P[(i + 1) % len(P)]
        mx9, my9 = (a9[0] + b9[0]) / 2.0, (a9[1] + b9[1]) / 2.0
        dx9, dy9 = b9[0] - a9[0], b9[1] - a9[1]
        L9 = math.hypot(dx9, dy9) or 1.0
        nx9, ny9 = sgn * dy9 / L9, -sgn * dx9 / L9
        for t9 in (0.3, 0.6):
            pu, pv = mx9 + nx9 * t9, my9 + ny9 * t9
            if n.inpond(pu, pv):
                continue                       # 入江の内側へ折り返した所は岸ではない
            fb.append((n.ground(pu, pv) - n.waterY, i + 1, t9, pu, pv))
    o["freeboard"] = fb
    o["fbMin"] = min(fb)[0] if fb else 0.0
    o["fbMinAt"] = min(fb)[1:] if fb else (0, 0.0, 0.0, 0.0)
    # くびれ(水口)
    kb = 9e9
    for i in range(len(P)):
        for j in range(i + 2, len(P)):
            if i == 0 and j == len(P) - 1:
                continue
            mid = ((P[i][0] + P[j][0]) / 2.0, (P[i][1] + P[j][1]) / 2.0)
            if not n.inpond(*mid):
                continue
            q = math.dist(P[i], P[j])
            if q < kb:
                kb, o["kubire"] = q, (i + 1, j + 1)
    o["kubireM"] = kb * K
    # 園路
    o["enro"] = []
    for e in g.get("enro", []):
        pts = [(a, b) for a, b in e["pts"]]
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) * K
        mx, steps, stepL = 0.0, 0, 0.0
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            l = math.dist(a, b) * K
            dz = n.ground(*b) - n.ground(*a)
            gr = abs(dz) / l if l > 1e-9 else 0.0
            mx = max(mx, gr)
            if gr * 100 > 15.0:                   # 急な区間は野面の石段を切る
                steps += int(round(abs(dz) / e["keri"]))
                stepL += l
        # ⚠ **区間の両端だけで測ると急な中腹を見落とす**(2026-09-04 庭方の申し送り)。
        #   0.25m 刻みで実際の地表を刻み、**1m 窓の最急**を別に持つ。
        prof, s0, segOf = [], 0.0, []
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            l = math.dist(a, b) * K
            m0 = max(1, int(math.ceil(l / 0.25)))
            dz9 = n.ground(*b) - n.ground(*a)
            cut9 = (abs(dz9) / l * 100 > 15.0) if l > 1e-9 else False   # この区間に石段を切ったか
            for k in range(m0 + (1 if i == len(pts) - 2 else 0)):
                t9 = k / float(m0)
                prof.append((s0 + l * t9,
                             n.ground(a[0] + (b[0] - a[0]) * t9, a[1] + (b[1] - a[1]) * t9)))
                segOf.append((i, cut9, a[0] + (b[0] - a[0]) * t9, a[1] + (b[1] - a[1]) * t9))
            s0 += l
        # ⭐ **設計されていない段**(2026-09-04 庭方の裁定)。⛔ 「1m 窓の最急」は
        #   **短い落差を『段であって勾配ではない』として窓から落とす** — そこに石段が切って
        #   あれば正しいが、**切っていない所の段は設計外の一段**で歩く人が躓く。
        #   ⇒ 0.25m 刻みの縦断で**隣り合う標本の落差**を測り、石段を切っていない区間だけ見る。
        stepMax, stepAt = 0.0, None
        for k9 in range(len(prof) - 1):
            if segOf[k9][1] or segOf[k9 + 1][1]:
                continue                          # 石段を切った区間の落差は蹴上そのもの
            dz8 = abs(prof[k9 + 1][1] - prof[k9][1])
            if dz8 > stepMax:
                stepMax, stepAt = dz8, (segOf[k9][2], segOf[k9][3], prof[k9][0])
        # ⚠ **窓は「1m ちょうど」で滑らせる。**「1m 以内の任意の2点」にすると、
        #   土手の縁の 0.23m の段(蹴上1段ぶん)を 0.25m 幅で割って 92% に化ける
        #   — それは段であって勾配ではない(2026-09-04 に踏んだ)。
        win, at, W1 = 0.0, 0.0, 1.0

        def _zat(s9):
            if s9 <= prof[0][0]:
                return prof[0][1]
            if s9 >= prof[-1][0]:
                return prof[-1][1]
            for k9 in range(len(prof) - 1):
                if prof[k9][0] <= s9 <= prof[k9 + 1][0]:
                    dd = prof[k9 + 1][0] - prof[k9][0]
                    t8 = 0.0 if dd < 1e-9 else (s9 - prof[k9][0]) / dd
                    return prof[k9][1] + (prof[k9 + 1][1] - prof[k9][1]) * t8
            return prof[-1][1]
        if L <= W1:
            win = abs(prof[-1][1] - prof[0][1]) / max(L, 1e-9)
        else:
            s9 = 0.0
            while s9 + W1 <= L + 1e-9:
                q = abs(_zat(s9 + W1) - _zat(s9)) / W1
                if q > win:
                    win, at = q, s9
                s9 += 0.25
        wet = [p for p in pts if n.inpond(*p)]
        # 路縁(幅の半分)から汀・社地までの離れ。⚠ 終端(沢飛石の袂)は汀に寄るのが役目
        # ⭐ **幅は場所で変わる**(2026-09-04 庭方の決定: 主路は 0.90m・稲荷の隘路だけ 0.75m)。
        #   ⛔ 一本の `w` で割らない — 締めた区間の離れを緩い幅で測ると甘くなる。
        def _hw(p):
            return _enro_halfwidth(e, p[0], p[1]) / K
        ed = min(n.dshore(*p) - _hw(p) for p in pts[1:-1]) * K if len(pts) > 2 else 9e9
        sh = g.get("kaki") and next((k.get("shachi") for k in g["kaki"] if k.get("shachi")), None)
        eg = 9e9
        if sh:
            box = [(sh["u0"], sh["v0"]), (sh["u1"], sh["v0"]),
                   (sh["u1"], sh["v1"]), (sh["u0"], sh["v1"])]
            for p in pts:
                eg = min(eg, (min(_segd(p, box[i], box[(i + 1) % 4]) for i in range(4)) - _hw(p)) * K)
        o["enro"].append(dict(name=e["name"], label=e["label"], L=L, grade=mx * 100,
                              gradeWin=win * 100, gradeWinAt=at,
                              steps=steps, stepL=stepL, wet=len(wet), w=e["w"],
                              wSeg=e.get("wSeg", []), stepMax=stepMax, stepAt=stepAt,
                              edgeShore=ed, edgeShachi=eg,
                              dshore=min(n.dshore(*p) for p in pts) * K))
    # 沢飛石
    o["sawa"] = []
    for s in g.get("sawatobi", []):
        span = math.dist(s["a"], s["b"]) * K
        cnt = max(1, int(round(span / s["pitch"])))
        o["sawa"].append(dict(name=s["name"], span=span, n=cnt, pitch=span / cnt))
    # 護岸の被覆
    cover = {}
    for coll, key in (("gogan", "石組"), ("suhama", "州浜"), ("rangui", "乱杭")):
        for x in g.get(coll, []):
            i = x["frm"] - 1
            while True:
                cover.setdefault(i, []).append(x["name"])
                i = (i + 1) % len(P)
                if i == x["to"] - 1:
                    break
    tk = g.get("sawatobiTake")
    if tk:
        cover.setdefault(tk["frm"] - 1, []).append("(沢飛石の取付)")
    o["coverGap"] = [i + 1 for i in range(len(P)) if i not in cover]
    o["coverDup"] = [(i + 1, cover[i]) for i in cover if len(cover[i]) > 1]
    o["cover"] = cover
    # 乱杭の本数(汀線に沿った弧長からの従属値)
    o["rangui"] = []
    for r in g.get("rangui", []):
        i, L = r["frm"] - 1, 0.0
        while i != r["to"] - 1:
            L += math.dist(P[i], P[(i + 1) % len(P)])
            i = (i + 1) % len(P)
        o["rangui"].append(dict(name=r["name"], L=L * K, n=int(round(L * K / r["pitch"]))))
    # 護岸石の個数
    o["gogan"] = []
    for x in g.get("gogan", []):
        i, L = x["frm"] - 1, 0.0
        while i != x["to"] - 1:
            L += math.dist(P[i], P[(i + 1) % len(P)])
            i = (i + 1) % len(P)
        w = (x["lenMin"] + x["lenMax"]) / 2.0
        o["gogan"].append(dict(name=x["name"], label=x["label"], L=L * K,
                               n=int(round(L * K / (w * x["pitchRatio"]))),
                               yaku=int(round(L * K / (w * x["pitchRatio"]) / x["yakuEvery"]))))
    # 築山
    o["tsuki"] = []
    v1 = next((m for m in g["mikoro"] if m.get("main")), g["mikoro"][0])
    e1 = n.eye(v1["no"])
    # 土手の法も測る(⛔ 上限は台帳にも庭方の決定にも無いので**測って刷るだけ**・閾値を発明しない)
    o["dote"] = []
    for t in g.get("tsukiyama", []):
        if t.get("kata") != "土手":
            continue
        du9, dv9 = t["u1"] - t["u0"], t["v1"] - t["v0"]
        # ⭐ **法は footprint の全周を 2次元の勾配で測る**(2026-09-04 庭方の裁定)。
        #   ⛔ 減衰軸の一本線だけを走査しない — **稜線の端の摺り付けも法面**であり、
        #   そこは刈込に覆われないので別の上限(`batterFill`)で見る。
        #   ⇒ **覆われる区間**(刈込の footprint の中)と**覆われない区間**の最急を分けて持つ。
        # ⭐ **「覆う」は footprint の**全周の包含**で判定する**(2026-09-04 庭方の裁定②)。
        #   ⛔ `onDote` で結ばれているだけでは足りない — 部分的に載っているだけの刈込を
        #   「覆い」と数えると、覆いの条が空文になる(東の土手が実際にそうだった)。
        #   ⛔ 端の摺り付けを除外しない。土手と刈込は `onDote` で結ばれた**一つの物**で、
        #   土手が裾を引くなら刈込もそこまで下りる。
        cov9 = None
        on9 = None
        for k9 in g.get("karikomi", []):
            if k9.get("kata") == "帯" or k9.get("onDote") != t["name"]:
                continue
            on9 = k9["label"]                      # 結ばれてはいる(載っている)
            if (k9["u0"] <= t["u0"] + 1e-9 and t["u1"] <= k9["u1"] + 1e-9
                    and k9["v0"] <= t["v0"] + 1e-9 and t["v1"] <= k9["v1"] + 1e-9):
                cov9 = k9                          # **全周を覆っている**
        stp = 0.02
        mxIn = mxOut = mxEnd = 0.0
        u9 = t["u0"]
        while u9 <= t["u1"] + 1e-9:
            v9 = t["v0"]
            while v9 <= t["v1"] + 1e-9:
                gu = (n.mound_one(t, u9 + stp, v9) - n.mound_one(t, u9 - stp, v9)) / (2 * stp * K)
                gv = (n.mound_one(t, u9, v9 + stp) - n.mound_one(t, u9, v9 - stp)) / (2 * stp * K)
                gg = math.hypot(gu, gv)
                inside = bool(cov9) and (cov9["u0"] - 1e-9 <= u9 <= cov9["u1"] + 1e-9
                                         and cov9["v0"] - 1e-9 <= v9 <= cov9["v1"] + 1e-9)
                if inside:
                    mxIn = max(mxIn, gg)
                else:
                    mxOut = max(mxOut, gg)
                    # 摺り付けそのものの勾配(**稜線軸方向だけ**)。⚠ 庭方が「端の最急」と
                    #   呼んだのはこちらで、2次元の勾配より緩く出る。両方を表に刷る。
                    mxEnd = max(mxEnd, abs(gv if t.get("decay") == "u" else gu))
                v9 += stp * 5
            u9 += stp * 5
        mx9 = max(mxIn, mxOut)
        # **刈込が法面まで覆っているか** — 覆いは footprint の包含で判定する。
        # ⛔ 「載っている」では足りない(天端だけ載って法面が露出する形がある)。
        # 稜線軸の**端の段**(摺り付けずに垂直に切れる高さ)。⭕ `taperEnds` を入れれば 0 になる。
        if t.get("decay") == "u":
            p0, p1 = ((t["u0"] + t["u1"]) / 2.0, t["v0"]), ((t["u0"] + t["u1"]) / 2.0, t["v0"] - 0.01)
        else:
            p0, p1 = (t["u0"], (t["v0"] + t["v1"]) / 2.0), (t["u0"] - 0.01, (t["v0"] + t["v1"]) / 2.0)
        end9 = n.mound_one(t, p0[0], p0[1]) - n.mound_one(t, p1[0], p1[1])
        o["dote"].append(dict(name=t["name"], label=t["label"], rise=t["rise"],
                              decay=t.get("decay", "?"), w=min(du9, dv9), L=max(du9, dv9),
                              covered=(cov9["label"] if cov9 else None), onDote=on9, endStep=end9,
                              taperEnds=t.get("taperEnds"),
                              batterIn=(1.0 / mxIn if mxIn > 1e-9 else 99.0),
                              batterOut=(1.0 / mxOut if mxOut > 1e-9 else 99.0),
                              batterEnd=(1.0 / mxEnd if mxEnd > 1e-9 else 99.0),
                              batterReal=(1.0 / mx9 if mx9 > 1e-9 else 99.0)))
    for t in g.get("tsukiyama", []):
        if t.get("kata") == "土手":
            continue
        ru = t["dU"] / 2.0 * K
        bat = ru / t["rise"]
        dd = math.hypot(t["u"] - v1["u"], t["v"] - v1["v"]) * K
        # ⚠ **公称の法(直径÷高さ)では平場を見落とす。**頂を平らに切ると残りの法が急になるので、
        #   **実際の地表を刻んで最急を測る**(2026-09-04 に踏んだ)。
        # ⭐ **刻みを 0.05 → 0.01間 に細かくし、u/v の両軸を走査する**(2026-09-04 検図方 低-7)。
        #   0.05間 の割線は法を **1:1.508** のように**緩い側へ**丸めていた。上限 1:1.5 に
        #   対する余裕が 0.008 しかないので、刻みで合否が動く所に閾値がある。
        #   ⭕ 0.01間 で 3桁目まで収束する(0.005/0.002 と同値)。実測値は表に刷る。
        mxg = 0.0
        stp = 0.01
        for ax in ("u", "v"):
            R = t["dU"] if ax == "u" else t["dV"]
            for k in range(-int(R / 2 / stp) - 1, int(R / 2 / stp) + 2):
                # ⛔ **`mound`(全基の max)で測らない** — 隣の盛土が重なっていると
                #   他基の斜面を自分の法として拾う(2026-09-04: 蔵前の土手を短辺減衰へ
                #   直した途端、築山A1/A2/C の実測がいずれも土手の 1:0.85 に化けた)。
                if ax == "u":
                    a0 = t["u"] + k * stp
                    g0, g1 = n.mound_one(t, a0, t["v"]), n.mound_one(t, a0 + stp, t["v"])
                else:
                    a0 = t["v"] + k * stp
                    g0, g1 = n.mound_one(t, t["u"], a0), n.mound_one(t, t["u"], a0 + stp)
                mxg = max(mxg, abs(g1 - g0) / (stp * K))
        o["tsuki"].append(dict(name=t["name"], label=t["label"], batter=bat,
                               batterReal=(1.0 / mxg if mxg > 1e-9 else 99.0),
                               d=dd, ang=math.degrees(math.atan2(t["topY"] - e1, dd)),
                               top=t["topY"], rise=t["rise"],
                               suso=t["u"] - t["dU"] / 2.0))
    # 見隠れ(主視点から見える水面の割合)
    # ⚠ **隠す物を分けて数える。** 一つの割合にすると、座視で必ず起きる「手前の岸に隠れる」分と、
    #   設計として効かせている「築山の見隠れ」が混ざって、どちらの話か分からなくなる。
    vis = tot = 0
    byM, byB = [], []
    for u, v in n._cells(0.2):
        if not n.inpond(u, v):
            continue
        tot += 1
        dd = math.hypot(u - v1["u"], v - v1["v"]) * K
        blk = None
        nn = max(3, int(dd / 0.5))
        for k in range(1, nn):
            t9 = k / float(nn)
            uu = v1["u"] + (u - v1["u"]) * t9
            vv = v1["v"] + (v - v1["v"]) * t9
            if n.ground(uu, vv) > e1 + (n.waterY - e1) * t9 + 0.02:
                blk = (uu, vv, n.mound(uu, vv))
                break
        if blk is None:
            vis += 1
        elif blk[2] > 0.15:
            byM.append((u, v))
        else:
            byB.append((u, v))
    o["visPct"] = 100.0 * vis / tot if tot else 0.0
    o["hidMoundPct"] = 100.0 * len(byM) / tot if tot else 0.0
    o["hidBankPct"] = 100.0 * len(byB) / tot if tot else 0.0
    o["hidMoundAt"] = ((sum(p[0] for p in byM) / len(byM), sum(p[1] for p in byM) / len(byM))
                       if byM else None)
    o["eye1"] = e1
    # 主景の見切り — 御土蔵をどれだけの帯で塞ぐ必要があるか
    ku = n.kura()
    o["kura"] = ku
    # ⭐ **2026-09-04 庭方の第3巡で物差しを組み替えた(決定 中9)。**
    #   ⛔ 「常緑広葉Big 3本が自分の位置で帯を覆うか」では**面の端と低い帯が抜ける**
    #     (それで 16% を見逃した)。
    #   ⭕ 見るのは「**蔵の見える面が、長さ全長 × 高さ全高にわたって塞がるか**」。
    #     塞ぐ物は **地形(築山・土手を含む地表)/ 刈込の天端 / 樹冠(枝下〜樹高の円柱)** の3つ。
    o["screen"] = []
    cr9 = _crowns(d)
    ks9 = karikomi_stats(d)

    def _blocked(tu, tv, ty):
        """眼 → (tu, tv, ty) の視線が塞がるか。塞いだ物の名を返す(塞がらなければ None)。"""
        du, dv = tu - v1["u"], tv - v1["v"]
        for m9 in range(1, 80):
            s = m9 / 80.0
            xu, xv = v1["u"] + du * s, v1["v"] + dv * s
            if n.ground(xu, xv) > e1 + (ty - e1) * s:
                return "地形"
        for st9 in ks9:
            k9, poly, bb = st9["k"], st9.get("poly"), st9.get("bb")
            if not poly:
                continue
            for m9 in range(1, 80):
                s = m9 / 80.0
                xu, xv = v1["u"] + du * s, v1["v"] + dv * s
                # ⚠ 外接矩形で先に落とす(帯は点数が多く、素の点内判定だと桁で遅い)
                if not (bb[0] <= xu <= bb[2] and bb[1] <= xv <= bb[3]):
                    continue
                if _pip((xu, xv), poly) and \
                        n.ground(xu, xv) + k9["hMax"] > e1 + (ty - e1) * s:
                    return k9["label"]
        L2 = du * du + dv * dv
        for c in cr9:
            if L2 <= 1e-12:
                break
            s = ((c["u"] - v1["u"]) * du + (c["v"] - v1["v"]) * dv) / L2
            if not (0.0 < s < 1.0):
                continue
            if math.hypot((v1["u"] + du * s - c["u"]) * K,
                          (v1["v"] + dv * s - c["v"]) * K) >= c["r"]:
                continue
            gy = n.ground(c["u"], c["v"])
            ly = e1 + (ty - e1) * s
            if gy + c["crownFrom"] <= ly <= gy + c["h"]:
                return "%s %s" % (c["sp"], c["sz"])
        return None
    o["kuraFace"] = []
    cst = d["const"]
    for m in d["service"]:
        if not m["name"].startswith("Kura"):
            continue
        face = m["u1"]                              # 主視点側の面(+u が北・眼は +u 側)
        y0, y1 = m["y"], m["y"] + cst["kuraRidge"]
        NV, NH = 120, 28
        tot = 0
        miss = []
        for i in range(NV):
            vv = m["v0"] + (m["v1"] - m["v0"]) * (i + 0.5) / NV
            for k in range(NH):
                Y = y0 + (y1 - y0) * (k + 0.5) / NH
                tot += 1
                if _blocked(face, vv, Y) is None:
                    miss.append((round(vv, 1), round(Y, 2)))
        o["kuraFace"].append(dict(name=m["name"], v0=m["v0"], v1=m["v1"], y0=y0, y1=y1,
                              pct=100.0 * (tot - len(miss)) / tot if tot else 100.0,
                              miss=sorted(set(miss))))
    if ku:
        dk = (v1["u"] - ku["face"]) * K
        for s in g.get("shokusai", []):
            if s.get("crownFrom") is None:
                continue
            hh = max((asset_dim(x) or (0, 0, 0))[1] for x in s.get("idx", [])) * s.get("scale", 1.0)
            ww = max((asset_dim(x) or (0, 0, 0))[0] for x in s.get("idx", [])) * s.get("scale", 1.0)
            for (u, v) in s["at"]:
                dd = (v1["u"] - u) * K
                if dd <= 0 or dd >= dk:
                    continue
                gy = n.ground(u, v)
                lo = e1 + (ku["eave"] - e1) * dd / dk - gy
                hi = e1 + (ku["ridge"] - e1) * dd / dk - gy
                o["screen"].append(dict(sp=s["species"], sz=s["size"], u=u, v=v, gy=gy,
                                        lo=lo, hi=hi, h=hh, w=ww, c0=s["crownFrom"],
                                        ok=(s["crownFrom"] <= lo and hi <= hh)))
    # 水の収支
    gs = g["mizu"]["gensen"]
    inflow = (gs["yane"]["m2"] * gs["yane"]["runoff"]
              + o["areaM2"] * gs["chokusetsu"]["runoff"]) * gs["rainMmY"] / 1000.0
    out = o["areaM2"] * gs["johatsu"]["mmY"] / 1000.0
    o["water"] = dict(inflow=inflow, out=out, bal=inflow - out)
    # 水尻の縦断
    ms = g["mizu"]["mizushiri"]
    tp = [(P[ms["shiki"]["at"] - 1][0], P[ms["shiki"]["at"] - 1][1], ms["shiki"]["sill"])]
    ut = ms["umeToi"]
    for i, (u, v) in enumerate(ut["pts"]):
        y = ms["shiki"]["sill"] + (ut["outY"] - ms["shiki"]["sill"]) * (i + 1) / float(len(ut["pts"]))
        tp.append((u, v, y))
    o["toi"] = tp
    o["toiLen"] = sum(math.hypot(tp[i + 1][0] - tp[i][0], tp[i + 1][1] - tp[i][1])
                      for i in range(len(tp) - 1)) * K
    o["toiGrade"] = (tp[0][2] - tp[-1][2]) / o["toiLen"] * 100.0 if o["toiLen"] else 0.0
    _STATS_CACHE[0], _STATS_CACHE[1] = d, o
    return o


def niwa_check(d):
    """奥庭の不変条件。⛔ **検査の無い不変条件は必ず壊れる。**"""
    n = NI(d)
    if n is None:
        return []
    g, K = n.g, n.ken
    o = niwa_stats(d)
    bad = []
    mg = n.mg
    cl = mg.get("clearance", {})
    # ⭐ **乱杭の天端**(2026-09-06 検図方 中-2)。⚠ 従前 `topAbove` に検査が無く、
    #   **全没に書き換えても 0 件で歯が無かった**(旧 `topY` 25.87 = 水面 −0.33 の
    #   「頭が水没する」誤りを、8か月ぶん誰も鳴らせなかったのがまさにこれ)。
    #   条は二つ: **①水面より上に出ること ②岸を越えないこと**(杭は汀を留める物で、
    #   岸より高く突き出したら柵になる)。
    ter9 = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
    for rg in g.get("rangui", []):
        ta = rg.get("topAbove")
        if not ta or len(ta) != 2:
            bad.append("乱杭 %s に `topAbove`(水面からの天端の範囲)が無い" % rg["name"])
            continue
        if ta[0] <= 0:
            bad.append("**乱杭 %s の天端の下限が水面 %+.2f** — 頭が水没する。"
                       "杭は水面より上に出る物(`topAbove[0]` > 0)" % (rg["name"], ta[0]))
        if ta[1] < ta[0]:
            bad.append("乱杭 %s の `topAbove` が逆順 [%.2f, %.2f]" % (rg["name"], ta[0], ta[1]))
        # 岸の面 — 帯に沿った地盤のいちばん低い所と比べる(⛔ 一点で代表しない)
        bank = None
        if ter9:
            i9 = int(rg["frm"]) - 1
            m9 = len(n.pond)
            while True:
                for t9 in (0.25, 0.5, 0.75):
                    a9, b9 = n.pond[i9], n.pond[(i9 + 1) % m9]
                    nx9, ny9 = _shore_out(n, i9)
                    uu = a9[0] + (b9[0] - a9[0]) * t9 + nx9 * 0.5
                    vv = a9[1] + (b9[1] - a9[1]) * t9 + ny9 * 0.5
                    q9 = terr_at(ter9, uu, vv)
                    if q9 is not None:
                        bank = q9 if bank is None else min(bank, q9)
                if i9 == int(rg["to"]) - 1:
                    break
                i9 = (i9 + 1) % m9
        if bank is not None and n.waterY + ta[1] > bank + 1e-6:
            bad.append("**乱杭 %s の天端の上限 %.2f が岸の面 %.2f を越える** — "
                       "杭は汀を留める物で、岸より高く突き出したら柵になる"
                       % (rg["name"], n.waterY + ta[1], bank))

    # ⭐ **受け石の露出**(2026-09-06 検図方 中-1)。⚠ 基準天端とジッタが同値だと、
    #   ジッタの下振れで石の天端が地盤と面一になり「消える」。
    #   ⇒ **ジッタの最悪側でも露出 0.05m を残す**ことを条にする。
    ms9 = ((g.get("mizu") or {}).get("mizushiri") or {})
    uk9 = (ms9.get("otoshimizo") or {}).get("uke")
    if isinstance(uk9, dict) and ter9:
        to9 = (ms9.get("otoshimizo") or {}).get("to")
        gs9 = []
        for (deg, r9) in uk9.get("at", []):
            uu = to9[0] + math.cos(math.radians(deg)) * r9 / K
            vv = to9[1] + math.sin(math.radians(deg)) * r9 / K
            gs9.append(terr_at(ter9, uu, vv))
        ok9 = [q for q in gs9 if q is not None]
        if ok9:
            base9 = max(ok9) + uk9.get("capBase", 0.0)
            jit = uk9.get("capJitter", 0.0)
            # 下流(止め)の石 — 天端が `capHigh` で上に釘付けになる1個
            fx9 = to9[0] - ((ms9.get("umeToi") or {}).get("pts") or [[0, 0]])[-1][0]
            fz9 = to9[1] - ((ms9.get("umeToi") or {}).get("pts") or [[0, 0]])[-1][1]
            fl9 = math.hypot(fx9, fz9) or 1.0
            pj9 = [(math.cos(math.radians(dg)) * r0 / K * fx9
                    + math.sin(math.radians(dg)) * r0 / K * fz9) / fl9
                   for dg, r0 in uk9.get("at", [])]
            low9 = pj9.index(max(pj9)) if pj9 else -1
            for j9, q9 in enumerate(gs9):
                if q9 is None:
                    continue
                # ⛔ **露出は「元の地盤」から測る**(2026-09-06 検図方)。掘り下げ後の床で
                #   測ると、掘るほど露出が増えて**判定が緩む向き**になっていた。
                expo = base9 - jit - q9          # ジッタの最悪側(下振れ)の露出
                if expo < 0.05 - 1e-9:
                    bad.append("**受け石 #%d の露出がジッタの最悪側で %+.2fm**(下限 0.05)— "
                               "地盤 %.3f に対し基準天端 %.3f。`capBase` を上げる"
                               % (j9 + 1, expo, q9, base9))
                # ⭐ **根入れ**(2026-09-06 棟梁の第4回で式を改めた)。
                #   ⛔ **掘り下げでは根入れは増えない** — 天端が絶対高で石が剛体なら、
                #   床を掘っても**見付が増えるだけ**で 埋まり = `石丈 − 露出` のまま。
                #   ⇒ 満たすのは**石丈**。`buryMin` は「**根入れ ≥ 見付高(露出)の 1/2**」なので
                #   **石丈 ≥ (1 + buryMin) × 露出**。
                #   ⚠⚠ **`takeEach`(伏せたときの鉛直の丈)は目録から引けない** —
                #   `Own.Tateishi` は**長軸**を 1.0 に正規化しており、伏せた向きの丈は別物。
                #   ⛔ **無いのに「合格」と数えない**(規則19)。`_pending.uke2` が持ち、
                #   表には ⚠ 未測として出す。
                top9 = base9 + (uk9.get("capHigh", 0.0) if j9 == low9 else 0.0)
                expo0 = top9 - q9                                   # 元の地盤からの露出
                tk9 = (uk9.get("takeEach") or [None] * len(gs9))[j9]
                need = (1.0 + uk9.get("buryMin", 0.0)) * expo0
                if tk9 is not None and tk9 < need - 1e-9:
                    bad.append("**受け石 #%d の石丈が %.3fm**(要 %.3f = (1+%.2f)×露出 %.3f)— "
                               "根入れが見付高の %.0f%% に足りない。"
                               "⛔ **掘り下げでは増えない**(天端が絶対高・石は剛体)ので"
                               "**石を大きくする**ほかない"
                               % (j9 + 1, tk9, need, uk9.get("buryMin", 0.0), expo0,
                                  100.0 * uk9.get("buryMin", 0.0)))

    # ① 汀線の頂点が庭の内側・棟の外側
    for i, (u, v) in enumerate(n.pond):
        if not (g["u0"] <= u <= g["u1"] and g["v0"] <= v <= g["v1"]):
            bad.append("汀線 #%d (%.2f, %.2f) が庭 %s の外" % (i + 1, u, v, g["name"]))
    if o["clrBound"] < cl.get("gardenBound", 1.5) - 1e-9:
        bad.append("汀から庭境までの最小が %.2f間(%s)— 下限 %.2f間"
                   % (o["clrBound"], o["clrBoundBy"], cl.get("gardenBound", 1.5)))
    if o["clrMune"] < cl.get("mune", 1.5) - 1e-9:
        bad.append("汀から棟 %s までが %.2f間 — 下限 %.2f間"
                   % (o["clrMuneBy"], o["clrMune"], cl.get("mune", 1.5)))
    # ② 池が矩形でない(円形度・辺長のばらつき)
    if o["circ"] > 0.75:
        bad.append("池の円形度 %.3f — 丸すぎる(0.75 以下)" % o["circ"])
    if o["cv"] < 0.10:
        bad.append("汀線の辺長の変動係数 %.3f — 等間隔すぎる(0.10 以上)" % o["cv"])
    if len(n.pond) < 8:
        bad.append("汀線が %d 点 — 矩形に見える" % len(n.pond))
    # ③ 護岸が全周を覆う
    for i in o["coverGap"]:
        bad.append("汀線 #%d–#%d に護岸の指定が無い — 裸の縁を残さない" % (i, i % len(n.pond) + 1))
    for i, who in o["coverDup"]:
        bad.append("汀線 #%d–#%d を %s が二重に受け持つ"
                   % (i, i % len(n.pond) + 1, "・".join(who)))
    # ④ 園路(水中の点。棟との食い違いと勾配は `niwa_todo` が別枠で出す)
    for e in o["enro"]:
        if e["wet"]:
            bad.append("園路 %s の点が %d 個 水中にある" % (e["label"], e["wet"]))
    # ⑤ 掘削と盛土の釣り合い
    if abs(o["level"]) > 0.5:
        bad.append("掘削 − 盛土 を庭の陸地に均すと %+.2fm — 許容 ±0.5m" % o["level"])
    # ⑤b 水面が岸より低い(**余裕高が正**)。⭐ 2026-09-04 検図方 中-5。
    #    ⛔ 「水面が見えるか」は見隠れの話で、**水面の高さの検査ではない**。
    for (fbv, i9, t9, pu, pv) in o["freeboard"]:
        if fbv <= 1e-9:
            bad.append("水面 %.2f が汀 #%d の外 %.1f間 (%.2f, %.2f) の陸 %.2f より %+.2fm — "
                       "水は陸より高い所に溜まらない"
                       % (n.waterY, i9, t9, pu, pv, n.waterY + fbv, fbv))
    # ⑥ 主視点から見える水面が 100% でない(見隠れが効いている)
    if o["visPct"] >= 100.0:
        bad.append("主視点から水面が %.0f%% 見える — 見隠れが効いていない" % o["visPct"])
    if o["hidMoundPct"] <= 0.0:
        bad.append("**築山による見隠れが 0%** — 池が一望できてしまう(築山Bは西の池を切る役)")
    # ⑦ 築山の法と南裾。⭐ **2026-09-04 庭方の物差し** — 公称(直径÷高さ)だけでは
    #   1:0.53 の崖を見逃していたので、**実測の最急**を別の条として立てる。
    bf = d["const"]["batterFill"]
    for t in o["tsuki"]:
        if t["batter"] < bf - 1e-9:
            bad.append("%s の法(公称)1:%.2f が盛土の上限 1:%.1f より急" % (t["label"], t["batter"], bf))
        if t["batterReal"] < bf - 1e-9:
            bad.append("%s の法(**実測の最急**)1:%.2f が盛土の上限 1:%.1f より急 — "
                       "公称は 1:%.2f。頂の平場の切り方か山の裾を見直すこと"
                       % (t["label"], t["batterReal"], bf, t["batter"]))
    # ⭐ **庭の土工すべて(築山4基 + 土手2本)の裾から棟・付属屋まで ≥ `inubashiri`**
    #   (2026-09-04 検図方の確認巡 中-1)。
    #   ⚠ 従前は `Tsukiyama_A1` を**名指し**して御土蔵との1組だけを見ていたので、
    #   **土手+刈込①を蔵の壁面に密着(犬走り 0)させても 0 件**だった。
    #   ⛔ 名前で絞らない — 枠は `_niwa_frames` が `munes`+`service` から機械で作る。
    inu9 = d["const"]["inubashiri"] / K
    for t in g.get("tsukiyama", []):
        if t.get("kata") == "土手":
            fu0, fu1, fv0, fv1 = t["u0"], t["u1"], t["v0"], t["v1"]
        else:
            fu0, fu1 = t["u"] - t["dU"] / 2.0, t["u"] + t["dU"] / 2.0
            fv0, fv1 = t["v"] - t["dV"] / 2.0, t["v"] + t["dV"] / 2.0
        for m in _niwa_frames(d):
            if "yaw" in m:
                continue
            du = max(m["u0"] - fu1, fu0 - m["u1"])
            dv = max(m["v0"] - fv1, fv0 - m["v1"])
            gap = max(du, dv)                      # 矩形どうしの離れ(重なれば負)
            if gap < inu9 - 1e-6:
                bad.append("庭の土工 %s の裾 u[%.2f, %.2f] v[%.2f, %.2f] から %s まで %.2f間 — "
                           "犬走り %.2f間(%.2fm)を下回る(⛔ 壁の足元に土を寄せない)"
                           % (t["label"], fu0, fu1, fv0, fv1, m["name"], gap,
                              inu9, d["const"]["inubashiri"]))
        # ⛔ **土工の footprint は庭の矩形に内包されること。**はみ出すと `ground_y` が
        #   庭の外で `graded_y` に切り替わり、**境で黙って崖になる**。
        if not (g["u0"] - 1e-9 <= fu0 and fu1 <= g["u1"] + 1e-9
                and g["v0"] - 1e-9 <= fv0 and fv1 <= g["v1"] + 1e-9):
            bad.append("庭の土工 %s の footprint u[%.2f, %.2f] v[%.2f, %.2f] が庭の矩形 "
                       "u[%.2f, %.2f] v[%.2f, %.2f] からはみ出す — 庭の外は `graded_y` が"
                       "地表を返すので、境で黙って崖になる"
                       % (t["label"], fu0, fu1, fv0, fv1,
                          g["u0"], g["u1"], g["v0"], g["v1"]))
    # ⑧ 水尻 — 樋が土蔵と交わらない / 落とし口が区画線の内側
    gr = RGrid(d)
    Pg = [gr.L(x, z) for x, z in d["polygon"]]
    ms = g["mizu"]["mizushiri"]
    path = [(x, y) for x, y, _ in o["toi"]] + [tuple(ms["otoshimizo"]["to"])]
    for m in d["service"]:
        if "yaw" in m:
            continue
        box = [(m["u0"], m["v0"]), (m["u1"], m["v0"]), (m["u1"], m["v1"]), (m["u0"], m["v1"])]
        for p in path:
            if _pip(p, box):
                bad.append("水尻の樋の折れ点 (%.2f, %.2f) が %s の中" % (p[0], p[1], m["name"]))
        near = min(min(_segd(p, box[i], box[(i + 1) % 4]) for i in range(4)) for p in path)
        if m["name"].startswith("Kura") and near < 0.8 - 1e-9:
            bad.append("水尻の樋が %s へ %.2f間 まで寄る(下限 0.8間)" % (m["name"], near))
    for p in path:
        if not _pip(p, Pg):
            bad.append("水尻の経路 (%.2f, %.2f) が区画の外 — 隣家へ流し込まない" % p)
    if o["toiGrade"] <= 0.0:
        bad.append("水尻の樋の勾配が %+.2f%% — 水が流れない" % o["toiGrade"])
    # ⑨ 禁句(季節・年次)
    NG = ("ソメイヨシノ", "桜", "サクラ", "孟宗竹", "竹叢", "ポプラ", "maple_bush", "Broadleaf",
          "Spring_Sakura", "Sakura")
    for s in g.get("shokusai", []):
        t = s["species"] + " " + " ".join(s.get("idx", [])) + " " + str(s.get("asset", ""))
        for w in NG:
            if w in t:
                bad.append("植栽に禁句「%s」(%s)— 開花木・竹・幕末以降の外来種は置かない"
                           % (w, s["species"]))
    # ⑩ 稲荷が池に重ならない
    ya = g["yashiro"]["hokora"]
    for (u, v) in ((ya["u0"], ya["v0"]), (ya["u1"], ya["v0"]),
                   (ya["u0"], ya["v1"]), (ya["u1"], ya["v1"])):
        if n.inpond(u, v):
            bad.append("稲荷の祠の隅 (%.2f, %.2f) が池の中" % (u, v))
    # ⑩b 社地の垣・参道・点景の取り合い
    for k in g.get("kaki", []):
        sh = k.get("shachi")
        if not sh:
            continue
        if not (sh["u0"] <= ya["u0"] and ya["u1"] <= sh["u1"]
                and sh["v0"] <= ya["v0"] and ya["v1"] <= sh["v1"]):
            bad.append("%s の社地が祠を囲めていない" % k["label"])
        # 参道は**開ける一方**を通ること(⛔ 垣を跨いで入らない)
        for (p, q) in zip(g["yashiro"]["sando"]["pts"], g["yashiro"]["sando"]["pts"][1:]):
            for (r0, r1) in zip(k["pts"], k["pts"][1:]):
                if _seg_cross(p, q, r0, r1):
                    bad.append("稲荷の参道が %s を横切る((%.2f, %.2f)→(%.2f, %.2f))"
                               % (k["label"], p[0], p[1], q[0], q[1]))
        # 手水石・灯籠は「社地の中」か「開き口の側(参道の上)」のどちらかに在ること
        for nm, ob in (("手水石", g["yashiro"]["chozu"]), ("灯籠(社前)", g["toro"][-1])):
            pu, pv = ob["u"], ob["v"]
            if sh["u0"] <= pu <= sh["u1"] and sh["v0"] <= pv <= sh["v1"]:
                continue                           # 社地の中は可
            if pu < sh["u0"] and sh["v0"] <= pv <= sh["v1"]:
                continue                           # 開き口(−u)の側の参道まわりも可
            bad.append("%s (%.2f, %.2f) が社地の中にも開き口の側にも無い" % (nm, pu, pv))
    ir = next((s for s in d["service"] if s["name"] == ya["ref"]), None)
    if ir is None:
        bad.append("`yashiro.hokora.ref` = %s が付属屋に無い" % ya["ref"])
    elif any(abs(ir[k] - ya[k]) > 1e-9 for k in ("u0", "v0", "u1", "v1")):
        bad.append("稲荷の祠の矩形が `service.%s` と食い違う — 正典は付属屋のほう" % ya["ref"])
    # ⑪ 地なり — 設計面と江戸期復元地盤の差
    ter = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
    if ter:
        w = 0.0
        for u, v in n._cells(0.5):
            q = terr_at(ter, u, v)
            if q is not None:
                w = max(w, abs(q - n.base))
        if w > d["const"]["niwaGridTol"]:
            bad.append("`on: 地なり` の庭で設計面と復元地盤の差が最大 %.2fm(上限 %.2fm)"
                       % (w, d["const"]["niwaGridTol"]))
    # ⑪b 土手は**減衰軸**を必ず持つ。⛔ 未指定を既定へ倒さない(2026-09-04 庭方の第4巡)。
    #    ⚠ 書式をなぞって軸を落とすと、長辺方向に減衰する**蒲鉾**になって端が 0 になる。
    for t in g.get("tsukiyama", []):
        if t.get("kata") != "土手":
            continue
        if t.get("decay") not in ("u", "v"):
            bad.append("土手 %s に `decay`(減衰軸 u/v)が無い — 軸を落とすと長辺方向に減衰して"
                       "**両端が 0 の蒲鉾**になる(壁の足元の土手は一様な稜線でなければ働かない)"
                       % t["name"])
            continue
        du9, dv9 = t["u1"] - t["u0"], t["v1"] - t["v0"]
        shortax = "u" if du9 <= dv9 else "v"
        if t["decay"] != shortax:
            bad.append("土手 %s の `decay`=%s が短辺(%s: %.2f間 対 %.2f間)と食い違う — "
                       "稜線は長辺に沿って一様に通すこと"
                       % (t["name"], t["decay"], shortax, min(du9, dv9), max(du9, dv9)))
    # ⑪c 土手の法。⭐ **上限は2段**(2026-09-04 庭方の裁定)。
    #    ①裸の土手 = `batterFill`(1:1.5)【B】
    #    ②**刈込の footprint が土手の footprint を覆う**土手 = `doteBatterCovered`(1:1.0)【U・庭方】
    #    ③いかなる土手も `batterCut`(1:1.0)より立てない【台帳から引ける唯一の線】
    #    ⛔ 露出する区間が少しでもあれば①で見る。
    cst9 = d["const"]
    for q in o.get("dote", []):
        # ⭐ **区間ごとに上限が違う**(2026-09-04 庭方の裁定)。
        #   刈込に覆われる区間 → `doteBatterCovered`(1:1.0)/ 覆われない区間(摺り付けを含む)
        #   → `batterFill`(1:1.5)。⛔ ③いかなる土手も `batterCut` より立てない。
        # ⛔ **法の上限違反は `niwa_todo`(庭方へ差し戻す枠)で出す** — 直す手が
        #   「rise を変える / footprint を広げる / 刈込の範囲を変える」のいずれも**意匠**で、
        #   指図方には動かせない。ここ(`niwa_check`)で見るのは**書き漏らし**だけ。
        if q["batterReal"] < cst9["batterCut"] - 1e-9:
            bad.append("土手 %s の法 1:%.3f が切土の法 1:%.1f より急 — "
                       "盛った土が自然の土より立つことはありえない"
                       % (q["label"], q["batterReal"], cst9["batterCut"]))
        # ⛔ **端も法面。**摺り付けを持たない土手は稜線の端が垂直に切れる。
        if not q.get("taperEnds"):
            bad.append("土手 %s に `taperEnds`(稜線の端の摺り付け[間])が無い — "
                       "端が垂直に %.2fm 切れる(端も法面である)" % (q["label"], q["endStep"]))
        elif abs(q["endStep"]) > 0.01:
            bad.append("土手 %s の稜線の端に %.2fm の段が残る — `taperEnds` が効いていない"
                       % (q["label"], q["endStep"]))
    # ⑫ 主景の見切り — **蔵の見える面が全長 × 全高にわたって塞がるか**
    # ⛔ 「各樹が自分の位置で帯を覆うか」では面の端と低い帯が抜ける(2026-09-04 庭方 中9)。
    if not o.get("kuraFace"):
        bad.append("御土蔵の見切りを測っていない — `service.Kura*` が無いか検査が回っていない")
    for q in o.get("kuraFace", []):
        if q["miss"]:
            bad.append("%s の見える面が %.0f%% しか塞がらない — 素通し %d 点(例 %s)。"
                       "主景の対岸に御土蔵の白壁が残る"
                       % (q["name"], q["pct"], len(q["miss"]),
                          "、".join("v%.1f/標高%.2f" % p for p in q["miss"][:4])))
    # ⑬ 沢飛石は奇数枚・支間が跳べる幅
    for s in o["sawa"]:
        if s["n"] % 2 == 0:
            bad.append("沢飛石 %s が %d 枚(偶数)— 奇数にする" % (s["name"], s["n"]))
        if s["pitch"] > 0.75:
            bad.append("沢飛石 %s の芯々 %.2fm — 一歩で跳べない" % (s["name"], s["pitch"]))
    # ⑭ 見所が庭か棟の中にある
    for m in g["mikoro"]:
        inn = (g["u0"] - 1e-9 <= m["u"] <= g["u1"] + 1e-9
               and g["v0"] - 1e-9 <= m["v"] <= g["v1"] + 1e-9)
        inm = any(x["u0"] <= m["u"] <= x["u1"] and x["v0"] <= m["v"] <= x["v1"]
                  for x in d["munes"] if "yaw" not in x)
        if not (inn or inm):
            bad.append("見所 %d (%.2f, %.2f) が庭にも棟にも無い" % (m["no"], m["u"], m["v"]))
    return bad


def _shore_out(n, i):
    """汀線の辺 i(0起算)の**外向き法線**(単位・間)。⛔ 池心からの方向で代用しない
    — 非凸の池では内側を向く(2026-09-04 庭方の申し送り3)。"""
    P = n.pond
    m = len(P)
    a, b = P[i], P[(i + 1) % m]
    sa = 0.0
    for k in range(m):
        p, q = P[k], P[(k + 1) % m]
        sa += p[0] * q[1] - q[0] * p[1]
    sgn = 1.0 if sa > 0 else -1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    return (sgn * dy / L, -sgn * dx / L)


def karikomi_poly(d, k, step=0.05):
    """刈込の平面形。`kata` が「帯」なら**汀線のオフセット帯**、それ以外は矩形。

    帯 = 汀線の `frm`→`to` の区間を刻み、各点で**外向き法線**へ `off0`〜`off1`[間] 出た
    2本の線をつないだ多角形。`vClip` があれば v で切る。
    ⛔ **矩形に展開して正典へ書き戻さない** — 汀線が動いたら追随しなくなる(庭方の申し送り3)。
    """
    if k.get("kata") != "帯":
        # ⚠ **矩形も辺を刻んで返す。**⛔ 四隅だけを返すと、**辺の中ほどで最接近する取り合いを
        #   取りこぼす** — 刈込①と主路の離れが 2.26m と出ていたが、実際は辺どうしで 0.19m だった
        #   (2026-09-04 庭方の裁定の照合で発覚)。⭕ 帯と同じ刻みで点列にする。
        c9 = [(k["u0"], k["v0"]), (k["u1"], k["v0"]), (k["u1"], k["v1"]), (k["u0"], k["v1"])]
        out9 = []
        for i9 in range(4):
            a9, b9 = c9[i9], c9[(i9 + 1) % 4]
            L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
            ns9 = max(1, int(math.ceil(L9 / step)))
            for t9 in range(ns9):
                s9 = t9 / float(ns9)
                out9.append((a9[0] + (b9[0] - a9[0]) * s9, a9[1] + (b9[1] - a9[1]) * s9))
        return out9
    n = NI(d)
    P = n.pond
    m = len(P)
    i0 = int(k["frm"]) - 1
    i1 = int(k["to"]) - 1
    idx = []
    i = i0
    while True:
        idx.append(i)
        if i == i1:
            break
        i = (i + 1) % m
        if len(idx) > m:
            break
    vc = k.get("vClip")
    inner, outer = [], []
    for i in idx[:-1] if len(idx) > 1 else idx:
        a, b = P[i], P[(i + 1) % m]
        nx9, ny9 = _shore_out(n, i)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ns = max(1, int(math.ceil(L / step)))
        for t9 in range(ns + 1):
            s = t9 / float(ns)
            pu = a[0] + (b[0] - a[0]) * s
            pv = a[1] + (b[1] - a[1]) * s
            if vc and not (vc[0] - 1e-9 <= pv <= vc[1] + 1e-9):
                continue
            inner.append((pu + nx9 * k["off0"], pv + ny9 * k["off0"]))
            outer.append((pu + nx9 * k["off1"], pv + ny9 * k["off1"]))
    if len(inner) < 2:
        return []
    return inner + outer[::-1]


_KARI_CACHE = [None, None]


def karikomi_stats(d):
    """刈込の実測 — **水没率**と**園路の路縁までの離れ**と延長。⛔ 設計値へ写さない。

    ⚠ 帯は多角形の点数が多く、見切りの走査から毎回呼ぶと桁で遅くなる。**同じ `d` なら使い回す。**
    """
    if _KARI_CACHE[0] is d:
        return _KARI_CACHE[1]
    n = NI(d)
    if n is None:
        _KARI_CACHE[0], _KARI_CACHE[1] = d, []
        return []
    K = n.ken
    out = []
    for k in n.g.get("karikomi", []):
        poly = karikomi_poly(d, k)
        if not poly:
            out.append(dict(k=k, wet=100.0, edge=-9.9, L=0.0, bad="帯が組めない"))
            continue
        us = [p[0] for p in poly]
        vs = [p[1] for p in poly]
        tot = wet = 0
        st = 0.05
        u = min(us)
        while u <= max(us) + 1e-9:
            v = min(vs)
            while v <= max(vs) + 1e-9:
                if _pip((u, v), poly):
                    tot += 1
                    if n.inpond(u, v):
                        wet += 1
                v += st
            u += st
        eg = 9e9
        for e in n.g.get("enro", []):
            for p in poly:
                q = min(_segd(p, a, b) for a, b in zip(e["pts"], e["pts"][1:])) * K
                eg = min(eg, q - _enro_halfwidth(e, p[0], p[1]))
        # 延長 — ⚠ **矩形は長辺**(周長の半分だと短辺ぶんが足されて長く出る)。
        #   帯は内縁と外縁を往復した多角形なので周長の半分が中心線の長さになる。
        if k.get("kata") == "帯":
            L = 0.0
            for a, b in zip(poly, poly[1:]):
                L += math.hypot(b[0] - a[0], b[1] - a[1])
            L = L / 2.0
        else:
            L = max(k["u1"] - k["u0"], k["v1"] - k["v0"])
        out.append(dict(k=k, poly=poly, wet=100.0 * wet / tot if tot else 0.0,
                        edge=eg, L=L * K, bad=None,
                        bb=(min(us), min(vs), max(us), max(vs))))
    _KARI_CACHE[0], _KARI_CACHE[1] = d, out
    return out


def _crowns(d):
    """庭の**樹冠の実測**を目録から組む。⛔ 呼び寸法・想定値を使わない。

    半径 = `docs/asset-index.tsv` の **W と D の大きい方 ÷ 2 × `scale`**(個体を混ぜるので
    `idx` の最大を採る=安全側)。⚠ 樹冠幅を指図に写さない — ここで毎回引く。
    """
    n = NI(d)
    out = []
    if n is None:
        return out
    for s in n.g.get("shokusai", []):
        dims = [q for q in (asset_dim(x) for x in s.get("idx", [])) if q]
        if not dims:
            continue
        sc = s.get("scale", 1.0)
        r = max(max(q[0], q[2]) for q in dims) / 2.0 * sc
        hh = max(q[1] for q in dims) * sc
        for (u, v) in s["at"]:
            out.append(dict(sp=s["species"], sz=s["size"], u=u, v=v, r=r, h=hh,
                            crownFrom=float(s.get("crownFrom", 0.0)),
                            trunk=float(s.get("trunkR", 0.0))))
    return out


def shitakusa_regions(d):
    """**下草の散布域を言葉でなく幾何で組む**(`shitakusa.shida.where`)。

    ⚠ 2026-09-06 まで `where` は「築山A1の北面」「モミジの根方」「稲荷の社叢」という
    **文字列3つ**で、`shitakusa` は生成器が一度も読んでいなかった —
    設計値だけ在って図にも表にも検査にも出ていない状態だった(棟梁の差し戻し③)。

    ⛔ **意匠を足していない。**築山の中心と径、樹の位置と部材の実寸はすべて既に正典に在り、
    ここはそこから機械で導くだけ:
      `kata: 築山の面` … 名指した築山の楕円 footprint の **`side` 側の半分**(稜線 → 裾)
      `kata: 樹下`     … 名指した `shokusai` の層の全個体の**樹冠の円**
                         (半径は `docs/asset-index.tsv` の実測 ÷2 × `scale`。⛔ 指図に写さない)
    """
    n = NI(d)
    if n is None:
        return []
    K = d["const"]["ken"]
    tk = {t["name"]: t for t in n.g.get("tsukiyama", [])}
    cr = _crowns(d)
    out = []
    for w in ((n.g.get("shitakusa") or {}).get("shida") or {}).get("where", []):
        if not isinstance(w, dict):
            out.append(dict(w=w, name=str(w), label=str(w), kata="?", poly=[], circ=[],
                            m2=0.0, err="散布域が文字列のまま — 幾何へ落としていない"))
            continue
        o = dict(w=w, name=w.get("name", "?"), label=w.get("label", "?"),
                 kata=w.get("kata"), poly=[], circ=[], m2=0.0, err=None)
        if w.get("kata") == "築山の面":
            t = tk.get(w.get("of"))
            if t is None or t.get("dU") is None:
                o["err"] = "築山 %r が `tsukiyama` に無い(または楕円でない)" % w.get("of")
            else:
                rU, rV = t["dU"] / 2.0, t["dV"] / 2.0
                sg = 1.0 if str(w.get("side", "+u")).startswith("+") else -1.0
                pts = []
                for i in range(41):                       # 稜線 → 裾 → 稜線
                    th = math.pi * i / 40.0
                    pts.append((t["u"] + sg * rU * math.sin(th), t["v"] + rV * math.cos(th)))
                o["poly"] = pts
                o["m2"] = math.pi * rU * rV / 2.0 * K * K
        elif w.get("kata") == "樹下":
            hit = [c for c in cr if c["sp"].startswith(w.get("species", "\0"))
                   and c["sz"] == w.get("size")]
            if not hit:
                o["err"] = ("`shokusai` に「%s %s」の層が無い"
                            % (w.get("species"), w.get("size")))
            else:
                o["circ"] = [(c["u"], c["v"], c["r"] / K) for c in hit]
                o["m2"] = sum(math.pi * c["r"] ** 2 for c in hit)
        else:
            o["err"] = "知らない `kata` %r — 語彙に無い値は黙って何も描かない" % w.get("kata")
        out.append(o)
    return out


def _shitakusa_pts(o, st=0.1):
    """散布域を 0.1間 格子で刻む(内外の判定用)。"""
    if o["poly"]:
        us = [p[0] for p in o["poly"]]; vs = [p[1] for p in o["poly"]]
        u = min(us)
        while u <= max(us) + 1e-9:
            v = min(vs)
            while v <= max(vs) + 1e-9:
                if _pip((u, v), o["poly"]):
                    yield (u, v)
                v += st
            u += st
    for (cu, cv, r) in o["circ"]:
        u = cu - r
        while u <= cu + r + 1e-9:
            v = cv - r
            while v <= cv + r + 1e-9:
                if (u - cu) ** 2 + (v - cv) ** 2 <= r * r:
                    yield (u, v)
                v += st
            u += st


def _suhama_polys(d):
    """**州浜の砂利帯の平面形**(陸側 `toLand` のオフセット帯)。

    ⭐ 2026-09-06 庭方の検め直しで、下草の散布域から**水面と同じ扱いで抜く**ことになった —
    砂利帯は `bare`(そこの草は消す)と宣言しているので、下草を撒く所ではない。
    ⛔ 形をここで発明しない — `karikomi` の「帯」と**同じ器**(`karikomi_poly`)で組む。
    """
    n = NI(d)
    if n is None:
        return []
    out = []
    for s in n.g.get("suhama", []):
        out.append(karikomi_poly(d, {"kata": "帯", "frm": s["frm"], "to": s["to"],
                                     "off0": 0.0, "off1": s["toLand"] / n.ken}))
    return [p for p in out if p]


_SKC = [None, None]


def shitakusa_stats(d):
    """散布域を 0.1間 格子で測る。**水面は切る**(下草は水中に生えない)。

    ⭐ **水面で切るのは意匠でなく幾何の帰結。**築山A1 の裾は設計どおり汀へ落ちるので、
    半楕円をそのまま採ると 10.5% が池に掛かる。モミジの樹冠も汀へ差し掛ける。
    ⇒ **公称の域から陸だけを採る**のが正しく、⛔ 域を縮めて意匠を変えるのではない。
    ⚠ ただし**過半が水面なら域の取り方が間違っている**ので、そこは検査で鳴らす。
    """
    if _SKC[0] is d:
        return _SKC[1]
    n = NI(d)
    out = []
    if n is not None:
        g = n.g
        cell = 0.1 * 0.1 * d["const"]["ken"] ** 2
        for o in shitakusa_regions(d):
            o = dict(o)
            if o["err"]:
                o.update(land=0.0, wetPct=0.0, gvlPct=0.0, outPct=0.0, cells=0)
                out.append(o)
                continue
            cells = list(_shitakusa_pts(o))
            sub = _suhama_polys(d)
            wet = [1 for (u, v) in cells if n.inpond(u, v)]
            # ⭐ 砂利帯も抜く(2026-09-04 の `bare` 宣言どおり草を消す所なので撒けない)
            gvl = [1 for (u, v) in cells
                   if not n.inpond(u, v) and any(_pip((u, v), q) for q in sub)]
            outs = [1 for (u, v) in cells
                    if not (g["u0"] - 1e-9 <= u <= g["u1"] + 1e-9
                            and g["v0"] - 1e-9 <= v <= g["v1"] + 1e-9)]
            o.update(cells=len(cells),
                     land=(len(cells) - len(wet) - len(gvl)) * cell,
                     wetPct=(100.0 * len(wet) / len(cells)) if cells else 0.0,
                     gvlPct=(100.0 * len(gvl) / len(cells)) if cells else 0.0,
                     outPct=(100.0 * len(outs) / len(cells)) if cells else 0.0)
            out.append(o)
    _SKC[0], _SKC[1] = d, out
    return out


def shitakusa_check(d):
    """下草の散布域の不変条件。⛔ 参照切れ・庭の外・空の域を黙って通さない。"""
    n = NI(d)
    if n is None:
        return []
    g = n.g
    bad = []
    for o in shitakusa_stats(d):
        if o["err"]:
            bad.append("**下草 %s(%s)**: %s" % (o["name"], o["label"], o["err"]))
            continue
        if not o["cells"] or o["land"] <= 1e-9:
            bad.append("**下草 %s** の陸の散布域が 0 — 参照は解けたが撒く所が無い" % o["name"])
            continue
        if o["outPct"] > 0:
            bad.append("**下草 %s が庭 `%s` の外へ %.1f%% はみ出す** — 散布域は庭の中に納める"
                       % (o["name"], g["name"], o["outPct"]))
        if o["wetPct"] > 50.0:
            bad.append("**下草 %s の %.1f%% が水面** — 過半が水なら域の取り方が間違っている"
                       "(⛔ 水面で切って辻褄を合わせない)" % (o["name"], o["wetPct"]))
    if not ((niwa(d).get("shitakusa") or {}).get("shida") or {}).get("where"):
        bad.append("**下草の散布域 `shitakusa.shida.where` が無い** — "
                   "「樹下に散布」だけでは実装が範囲を発明する")
    return bad


def shitakusa_table(d):
    """下草の散布域 — **面積と判定を刷る**(⛔ 測って stdout に閉じ込めない)。"""
    n = NI(d)
    if n is None:
        return ""
    rows = []
    for o in shitakusa_stats(d):
        if o["poly"]:
            df = ("築山 <code>%s</code> の楕円の <b>%s 側の半分</b>(稜線 → 裾)"
                  % (o["w"].get("of"), o["w"].get("side")))
        elif o["circ"]:
            df = ("<b>%s %s</b> %d本の樹冠の下(半径 %.2f m・目録の実測)"
                  % (o["w"].get("species"), o["w"].get("size"), len(o["circ"]),
                     o["circ"][0][2] * d["const"]["ken"]))
        else:
            df = "—"
        rows.append((o["label"], "<code>%s</code>" % o["name"], o["kata"] or "?", df,
                     "%.1f m²" % o["m2"], "<b>%.1f m²</b>" % o["land"],
                     "%.1f%%" % o["wetPct"], "%.1f%%" % o.get("gvlPct", 0.0),
                     "⚠ " + o["err"] if o["err"]
                     else ("⭕" if (o["land"] > 0 and o["outPct"] <= 0
                                   and o["wetPct"] <= 50.0) else "⚠")))
    sk9 = (n.g.get("shitakusa") or {}).get("shida") or {}
    mz = (n.g.get("shitakusa") or {}).get("mizugiwa") or {}
    tail = ("<p class='cap'>⭐ <b>散布域は言葉でなく幾何で持つ。</b>"
            "築山の面は <code>tsukiyama</code> の中心と径から、樹下は "
            "<code>shokusai</code> の位置と <code>docs/asset-index.tsv</code> の樹冠幅から"
            "<b>毎回組み直す</b> — 築山を動かせば下草も動く。⛔ 範囲の数値を指図に写さない。"
            "⚠ 樹下の円は重なりを差し引いていないので面積は上限値。"
            "⭕ 水際の帯は水面から %+.2f〜%+.2f m の高さ(NatureManufacture Meadow を交差2本1組)、"
            "コケ・芝はスプラット、州浜の砂利帯は <code>bare</code> で草を消す。"
            "⭐ <b>公称の域から水面を切って「陸」を出す</b> — 築山A1 の裾は設計どおり汀へ落ち、"
            "モミジの樹冠も汀へ差し掛けるので、半楕円・樹冠の円をそのまま採ると池に掛かる。"
            "⛔ <b>域を縮めて意匠を変えるのではない</b>(撒く所が陸に限られるだけ)。"
            "⚠ ただし<b>過半が水面なら域の取り方が間違っている</b>ので、そこは検査が鳴らす。"
            "⭐ <b>撒き方</b>: 芯々 <b>%s m</b>(下限 <b>%s m</b>)・向きは<b>乱数</b>%s・"
            "株の大小は <b>×%s〜%s</b>。⚠ <b>下限は貫通よけ</b> — 芯々を ±25%% で散らすと"
            "下振れが株の径に届いて<b>株どうしが貫通する</b>。"
            "⛔ <b>格子に置かない</b>(機械で並べた列に見える)・"
            "⛔ 一律の大きさ・一律の向きにしない。"
            "⭕ 芯々は<b>部材の実寸から出す</b>(<code>JG.Fern</code> の幅の大きい方)"
            "— ⛔ 決め打ちしない【U】。"
            "⭐ <b>2026-09-06 庭方の検め直しで、州浜の砂利帯も水面と同じ扱いで抜いた</b> — "
            "砂利帯は <code>bare</code>(そこの草は消す)と宣言している所なので下草は撒けない。"
            "⚠ 実際に<b>常緑広葉 Small (−0.45, 67.75) の樹冠が州浜と重なる</b>。"
            "⛔ 樹も帯も動かさない — <b>重なった分に撒かないだけ</b>。"
            "帯の形は <code>suhama</code> の <code>frm</code>/<code>to</code> と "
            "<code>toLand</code> から <code>karikomi</code> の「帯」と同じ器で組む。</p>"
            % (mz.get("y0", 0.0), mz.get("y1", 0.0),
               ("%.2f" % sk9["pitch"]) if sk9.get("pitch") else "⚠ 無い",
               ("%.2f" % sk9["pitchMin"]) if sk9.get("pitchMin") else "⚠ 無い",
               "" if sk9.get("yawRandom") else "(⚠ <b>`yawRandom` が無い</b>)",
               ("%.2f" % sk9["scaleJitter"][0]) if sk9.get("scaleJitter") else "⚠",
               ("%.2f" % sk9["scaleJitter"][1]) if sk9.get("scaleJitter") else "⚠"))
    return _tw(("散布域", "名", "形", "定義(幾何から)", "公称", "撒く所",
                "水面で切った割合", "砂利帯で切った割合", "判定"), rows) + tail


def _niwa_frames(d, pad=12.0):
    """庭のまわりの**躯体の矩形**を `munes` + `service` から機械で作る。

    ⛔ **名前で並べない**(2026-09-04 庭方の第4巡・是正1)。手で並べた5枠に `Inari` が
    抜けていて、樹冠が祠へ 1.08m 食い込むのを見逃した。⭕ 庭の矩形を `pad`[間] 広げた
    範囲に掛かるものを全部返すので、**将来 附属屋が増えても自動で入る**。
    """
    n = NI(d)
    if n is None:
        return []
    g = n.g
    a, b = g["u0"] - pad, g["u1"] + pad
    c, e = g["v0"] - pad, g["v1"] + pad
    out = []
    for m in d["munes"] + d.get("service", []):
        if m["u1"] < a or m["u0"] > b or m["v1"] < c or m["v0"] > e:
            continue
        out.append(m)
    return out


def niwa_cover(d):
    """**樹冠の被覆率** — 水面のうち樹冠に覆われる割合と、陸の被覆率。

    ⚠ 上限は**庭方の追送待ち**【?】なので、当図は**測って刷るだけ**で合否を出さない
    (⛔ 閾値を発明しない)。⭕ ただし測った値は必ず成果物に載せる(規則19)。
    """
    n = NI(d)
    if n is None:
        return {}
    K = n.ken
    cr = _crowns(d)
    st = 0.05
    a1 = st * st * K * K
    core = (n.g.get("coverLimits") or {}).get("coreFromShore", 2.0)
    wa = wc = la = lc = ka = kc = 0.0
    for u, v in n._cells(st):
        cov = any(math.hypot(u - c["u"], v - c["v"]) * K <= c["r"] for c in cr)
        if n.inpond(u, v):
            wa += a1
            wc += a1 if cov else 0.0
            # ⭐ **水面の中央部** — 汀から `core`(m)以上内側。**水の面が空を映すこと**が
            #   この庭の要で、旧配置はここが無検査だったため水面全体の 83.7% が樹冠下だった。
            if n.dshore(u, v) * K >= core:
                ka += a1
                kc += a1 if cov else 0.0
        else:
            la += a1
            lc += a1 if cov else 0.0
    return dict(waterM2=wa, waterCov=wc, waterPct=100.0 * wc / wa if wa else 0.0,
                landM2=la, landCov=lc, landPct=100.0 * lc / la if la else 0.0,
                coreM2=ka, coreCov=kc, waterCorePct=100.0 * kc / ka if ka else 0.0,
                core=core, crownM2=sum(math.pi * c["r"] ** 2 for c in cr), n=len(cr))


def niwa_plant_check(d):
    """**庭方が要求した検査4本**(2026-09-04 第2巡の申し送り)。

    ⛔ どれも**指図方では直せない** — 座標を動かすのは意匠の判断なので `niwa_todo` へ流す。
    ⭐ **庭方の第3巡の座標が届く前に入れる**のが要点で、いまの座標では**鳴るのが正しい**
    (庭方の実測: 幹3本が池の中 / 高木6本が路心から 0.03〜0.22m / 樹冠が土蔵へ最大 2.39m)。
    """
    n = NI(d)
    if n is None:
        return []
    g, K = n.g, n.ken
    out = []
    cr = _crowns(d)
    # ⭐⭐ **申告した本数と据えた位置の数が合うこと**(2026-09-06 庭方 高1)。
    #   ⚠⚠ **常緑広葉Mid が `n:3` のまま `at` 1点になっていた** — 指図方が座標を差し替えたとき
    #   **2本を報告なしに落とした**。⛔ 表は同じ行の中で「本数 3」と刷りながら位置は1つで、
    #   **本文を読んだ棟梁は位置を2つ発明する**(前巡の受け石とまったく同じ型)。
    #   ⛔ `n` を持つ層は**必ず** `len(at)` と一致させる。
    #   ⭐⭐ **2026-09-06 検図方 中2: `shokusai` の名指しをやめ、再帰で全箇所に当てる。**
    #   ⚠ `n` と `at` を両方持つ辞書は設計値に **7箇所**あり、6箇所が `shokusai`、
    #   残る1つが **受け石**(`mizushiri.otoshimizo.uke`)。⛔ **`uke.n` を 3→5 にしても 0件**だった —
    #   **庭方が2巡続けて指摘した当の物**に、同じ型の検査が当たっていなかった。
    #   ⭕ 再帰なら将来 `n`/`at` を持つ物が増えても自動で入る。
    def _na(o9, path9):
        if isinstance(o9, dict):
            if o9.get("n") is not None and isinstance(o9.get("at"), list):
                try:
                    n9 = int(o9["n"])
                except (TypeError, ValueError):
                    n9 = None
                if n9 is not None and n9 != len(o9["at"]):
                    out.append("**%s の本数 %d と据え位置 %d 個が合わない**(`%s`)— "
                               "⛔ 数だけ書いて位置が無い物は実装が発明する【庭方の検査】"
                               % (o9.get("label") or o9.get("kata")
                                  or ("%s %s" % (o9.get("species", "?"), o9.get("size", ""))),
                                  n9, len(o9["at"]), path9))
            for k9, v9 in o9.items():
                if not k9.startswith("_"):
                    _na(v9, path9 + "." + k9)
        elif isinstance(o9, list):
            for i9, v9 in enumerate(o9):
                _na(v9, "%s[%d]" % (path9, i9))
    _na(g, "gardens.%s" % g.get("name", "?"))
    # ⭐⭐ **樹どうしの隙**(2026-09-06 庭方 高2 の物差し)。
    #   ⛔ **樹冠は交わってよいが、半分より深く重ねない** — **芯々 ≥ (r_a + r_b) ÷ 2**【庭方の意匠・U】。
    #   ⚠ 8m級の Big 2本が**幹の隙 0.15m**で立ち、樹冠が **96% 同心**だった(其八でも点と破線円が
    #   二重に刷られていた)のに、**どの検査も鳴らなかった**。
    for i9 in range(len(cr)):
        for j9 in range(i9 + 1, len(cr)):
            a9, b9 = cr[i9], cr[j9]
            dd = math.hypot((a9["u"] - b9["u"]) * K, (a9["v"] - b9["v"]) * K)
            need = (a9["r"] + b9["r"]) / 2.0
            if dd < need - 1e-6:
                out.append("**%s %s と %s %s の芯々が %.2fm**(下限 %.2fm = 樹冠 %.2f + %.2f の半分)"
                           " — 樹冠を半分より深く重ねない【庭方の物差し・U】"
                           % (a9["sp"], a9["sz"], b9["sp"], b9["sz"], dd, need, a9["r"] * 2, b9["r"] * 2))
    # ⭐ **平場に幹を掛けない**(同上)。⛔ 床几の平場に木が生えている図にしない。
    for t9 in g.get("tsukiyama", []):
        da = t9.get("daira")
        if not da:
            continue
        hu, hv = da["dU"] / 2.0, da["dV"] / 2.0
        for c in cr:
            if (abs(c["u"] - t9["u"]) <= hu + c.get("trunk", 0.0) / K
                    and abs(c["v"] - t9["v"]) <= hv + c.get("trunk", 0.0) / K):
                out.append("**%s %s の幹が %s の平場(%.2f × %.2f間)に掛かる** — "
                           "⛔ 床几の平場に木を生やさない【庭方の物差し・U】"
                           % (c["sp"], c["sz"], t9["label"], da["dU"], da["dV"]))
    # 6-① 据え位置が池の内側でない。⛔ 例外は**名指し**で持つ(`inpondExempt`)。
    ex = set(g.get("inpondExempt", []))
    pts = [("%s %s" % (c["sp"], c["sz"]), "植栽", c["u"], c["v"]) for c in cr]
    for st in karikomi_stats(d):
        k = st["k"]
        if st["wet"] > 1e-9:
            out.append("**%s(刈込)が %.1f%% 水没する** — 汀に沿う刈込は矩形でなく"
                       "**汀線のオフセット帯**で持つこと【庭方の検査 6-①】" % (k["label"], st["wet"]))
        if st["edge"] < -1e-9:
            out.append("**%s(刈込)が %s の路縁へ %.2fm 掛かる** — 路を塞がない【庭方の検査 6-①】"
                       % (k["label"], "園路", -st["edge"]))
    for t in g.get("toro", []):
        pts.append((t["name"], "灯籠", t["u"], t["v"]))
    for s in g.get("ishigumi", []):
        pts.append((s["name"], "石組", s["u"], s["v"]))
    for s in g.get("kutsunugi", []):
        pts.append((s["name"], "沓脱", s["u"], s["v"]))
    # ⭐ **飛石も対象**(2026-09-04 検図方 中-2)。⛔ 沢飛石(`sawatobi`)だけが水面を渡る物で、
    #   **飛石は陸の物**なので `inpondExempt` に入れない — 池へ落ちたら鳴らす。
    for s in g.get("tobiishi", []):
        for j9, (pu9, pv9) in enumerate(s["pts"]):
            pts.append(("%s の第%d石" % (s["name"], j9 + 1), "飛石", pu9, pv9))
    ch = g.get("yashiro", {}).get("chozu")
    if ch:
        pts.append(("Chozu_Inari", "手水石", ch["u"], ch["v"]))
    for w in d.get("wells", []):
        if g["u0"] <= w["u"] <= g["u1"] and g["v0"] <= w["v"] <= g["v1"]:
            pts.append((w["name"], "井戸", w["u"], w["v"]))
    for (nm, kind, u, v) in pts:
        if nm in ex:
            continue
        if n.inpond(u, v):
            out.append("**%s(%s)(%.2f, %.2f)が池の中**(水深 %.2fm)— "
                       "据え位置を陸へ動かすのは意匠の判断【庭方の検査 6-①】"
                       % (nm, kind, u, v, n.waterY - n.bed(u, v)))
    # 6-② 幹 → 園路の芯 ≥ **その位置の**半幅 + 幹半径
    # ⚠ 半幅は**路の上の最寄点**で読む(木の u で読むと隘路の外の木に隘路の幅が当たる)。
    for c in cr:
        for e in g.get("enro", []):
            q, hw = 9e9, e["w"] / 2.0
            for a, b in zip(e["pts"], e["pts"][1:]):
                du9, dv9 = b[0] - a[0], b[1] - a[1]
                L2 = du9 * du9 + dv9 * dv9
                t9 = 0.0 if L2 == 0 else max(0.0, min(1.0, ((c["u"] - a[0]) * du9
                                                            + (c["v"] - a[1]) * dv9) / L2))
                cu, cv = a[0] + du9 * t9, a[1] + dv9 * t9
                dd = math.hypot(c["u"] - cu, c["v"] - cv)
                if dd < q:
                    q, hw = dd, _enro_halfwidth(e, cu, cv)
            q *= K
            need = hw + c["trunk"]
            if q < need - 1e-9:
                out.append("**%s %s (%.2f, %.2f) から %s の芯まで %.2fm** — "
                           "要 %.2fm(その位置の路の半幅 %.2f + 幹半径 %.2f)%s【庭方の検査 6-②】"
                           % (c["sp"], c["sz"], c["u"], c["v"], e["label"], q, need, hw,
                              c["trunk"],
                              "。⚠ **幹半径が設計値に無いので 0 で下限だけを見ている**"
                              if c["trunk"] <= 0 else ""))
    # 6-③ 樹冠が棟・付属屋の矩形に食い込まない(部材実測・scale込み)
    # ⭕ **犬走り(矩形の外 `const.inubashiri`)への張り出しは食い込みに数えない** —
    #   枝が雨落ちの上に出るのは普通で、禁じるのは**躯体の線を越えること**(庭方の第3巡)。
    # ⛔ **枠を手で並べない**(2026-09-04 庭方の第4巡・是正1)。庭方の検算は
    #   `Oku/Ima/Daidokoro/Kura1/Kura2` の5枠を手で並べていて **`Inari` を書き漏らし**、
    #   1.08m の食い込みを見逃した。⇒ **`munes` + `service` から機械で作る** —
    #   将来 附属屋が増えても自動で入る。⭕ 対象は「庭の矩形に接するか重なるもの」まで
    #   絞ってよい(遠い棟は樹冠が届かない)が、⛔ **名前で絞らない**。
    for c in cr:
        for m in _niwa_frames(d):
            if "yaw" in m:
                continue
            du = max(m["u0"] - c["u"], 0.0, c["u"] - m["u1"])
            dv = max(m["v0"] - c["v"], 0.0, c["v"] - m["v1"])
            q = math.hypot(du, dv) * K
            if q < c["r"] - 1e-9:
                out.append("**%s %s (%.2f, %.2f) の樹冠 半径 %.2fm が %s へ %.2fm 食い込む**"
                           "(躯体の線まで %.2fm)【庭方の検査 6-③】"
                           % (c["sp"], c["sz"], c["u"], c["v"], c["r"], m["name"],
                              c["r"] - q, q))
    # 6-④ 樹冠の被覆率(陸・水面・**水面の中央部**)と単木の水平占有角
    lim = g.get("coverLimits") or {}
    o = niwa_cover(d)
    if lim and o:
        for key, got, ttl in (("landPct", o["landPct"], "陸の樹冠被覆率"),
                              ("waterPct", o["waterPct"], "水面の樹冠被覆率"),
                              ("waterCorePct", o["waterCorePct"],
                               "**水面の中央部**(汀から %.1fm 以上内側)の樹冠被覆率"
                               % lim.get("coreFromShore", 2.0))):
            if key in lim and got > lim[key] + 1e-9:
                out.append("%s が %.1f%% — 上限 %.1f%%【庭方の検査 6-④】"
                           % (ttl, got, lim[key]))
    if lim.get("singleTreeDeg"):
        # ⭐ **主景だけでなく「座敷から見る見所」すべてに回す**(2026-09-04 庭方 低-1)。
        #   ⛔ 主景だけを見ていると、別の座敷で一本が視野を塞いでいても鳴らない
        #   (見所②=奥御座敷の入側で最大 43.9°)。
        # ⛔ **庭の中に立つ見所(床几・沢飛石の上・参道の口)には当てない** — 木の脇に
        #   立つのだから一本が 85〜144° を占めるのは当然で、45° は成り立たない
        #   (⭕ 実測は見所の表に刷る。閾値だけを外す)。判定は `eyeMode` で分ける。
        for v9 in g["mikoro"]:
            if v9.get("eyeMode") != "sit":
                continue
            for c in cr:
                dd = math.hypot((c["u"] - v9["u"]) * K, (c["v"] - v9["v"]) * K)
                if dd <= 1e-6:
                    continue
                ang = 2.0 * math.degrees(math.atan2(c["r"], dd))
                if ang > lim["singleTreeDeg"] + 1e-9:
                    out.append("見所%d「%s」から見た **%s %s (%.2f, %.2f) の水平占有角が %.1f°** — "
                               "上限 %.1f°(⛔ 一本で景を塞がない)【庭方の検査】"
                               % (v9["no"], v9["label"], c["sp"], c["sz"],
                                  c["u"], c["v"], ang, lim["singleTreeDeg"]))
    # 主景に名指しした物が樹冠に隠れない
    out += mustsee_check(d)
    return out


def _mustsee_pts(d, v1=None):
    """見所から**見えなければならない物**の (label, u, v, y)。座標は正典から引く。

    ⭐ 2026-09-06 庭方 低4: **見所を引数に取る**ようにした。⚠ 従前は主視点(`main`)に
    固定で、⛔ **他の見所が `mustSee` を持っても一度も検査されなかった**。
    """
    n = NI(d)
    g = n.g
    if v1 is None:
        v1 = next((m for m in g["mikoro"] if m.get("main")), g["mikoro"][0])
    out, bad = [], []
    pool = {}
    for coll in ("ishigumi", "toro", "kutsunugi", "tobiishi", "iwajima", "sawatobi"):
        for o in g.get(coll, []):
            pool[o["name"]] = o
    for q in v1.get("mustSee", []):
        if "shore" in q:
            p = n.pond[int(q["shore"]) - 1]
            out.append((q["label"], p[0], p[1], n.waterY))
            continue
        o = pool.get(q.get("ref"))
        if o is None:
            bad.append("見所%s の `mustSee` が引く %s が庭の点景に無い"
                       % (v1.get("no"), q.get("ref")))
            continue
        if "pts" in o:
            p = o["pts"][-1 if q.get("at") == "last" else 0]
            u9, v9 = p[0], p[1]
        else:
            u9, v9 = o["u"], o["v"]
        y9 = q.get("yTop")
        if "topY" in o and y9 is not None and abs(o["topY"] - y9) > 1e-6:
            bad.append("見所%s の `mustSee`「%s」の `yTop` %.2f が %s の `topY` %.2f と食い違う"
                       % (v1.get("no"), q["label"], y9, o["name"], o["topY"]))
        out.append((q["label"], u9, v9, y9 if y9 is not None else n.waterY))
    return out, bad


def mustsee_check(d):
    """⛔ **見えると書いたものが見えない図を作らない。**見所 → 名指しの点景の視線が
    樹冠(枝下〜樹高の円柱)に切られていないか(2026-09-04 庭方の第3巡)。

    ⭐ **2026-09-06 庭方 低4: `mustSee` を持つ全見所を回す**(従前は主視点だけ)。
    ⚠ 主視点だけを回す実装は、**他の見所に `mustSee` を書いても静かに素通り**した —
    「書いたのに誰も測らない」型(規則19)。⛔ 見所の番号は指摘に必ず出す。
    """
    n = NI(d)
    if n is None:
        return []
    K = n.ken
    g = n.g
    out = []
    for v1 in g.get("mikoro", []):
        if not v1.get("mustSee"):
            continue
        out += _mustsee_one(d, n, K, v1)
    return out


def _mustsee_one(d, n, K, v1):
    """見所ひとつぶんの視線の検査。"""
    e1 = n.eye(v1["no"])
    if e1 is None:
        return []
    pts, out = _mustsee_pts(d, v1)
    cr = _crowns(d)
    for (lab, tu, tv, ty) in pts:
        du, dv = tu - v1["u"], tv - v1["v"]
        L2 = du * du + dv * dv
        if L2 <= 1e-12:
            continue
        hit = []
        for c in cr:
            s = ((c["u"] - v1["u"]) * du + (c["v"] - v1["v"]) * dv) / L2
            # ⭐⭐ **眼が樹冠の円の中にある場合を落とさない**(2026-09-06 庭方 高1)。
            #   ⚠ 最近点が眼の後ろ(s ≤ 0)になるので `0 < s < 1` で切ると**素通り**した。
            #   ⛔ 眼が円の中なら、どちらを向いても樹冠に切られる。
            eye_in = math.hypot((v1["u"] - c["u"]) * K, (v1["v"] - c["v"]) * K) < c["r"]
            if not eye_in and not (0.0 < s < 1.0):
                continue
            if not eye_in and math.hypot((v1["u"] + du * s - c["u"]) * K,
                                         (v1["v"] + dv * s - c["v"]) * K) >= c["r"]:
                continue
            gy = n.ground(c["u"], c["v"])
            ly = e1 if eye_in else e1 + (ty - e1) * s
            if gy + c["crownFrom"] <= ly <= gy + c["h"]:
                hit.append("%s %s%s" % (c["sp"], c["sz"], "(眼が樹冠の中)" if eye_in else ""))
        if hit:
            out.append("**見所%s(%s)から名指しした「%s」(%.2f, %.2f・天端 %.2f)が "
                       "%s の樹冠に隠れる** — 見えると書いたものが見えない【庭方の検査】"
                       % (v1.get("no"), v1.get("label", ""), lab, tu, tv, ty, "・".join(hit)))
    return out


def _enro_halfwidth(e, u, v):
    """園路の**その場所の**半幅[m]。`wSeg` があれば区間値、無ければ `w`。"""
    w = e["w"]
    for sg in e.get("wSeg", []):
        a0, a1 = sorted((sg["u0"], sg["u1"]))
        if a0 - 1e-9 <= u <= a1 + 1e-9:
            w = sg["w"]
    return w / 2.0


def niwa_todo(d):
    """⛔ **庭方へ差し戻す点。指図方では直せない。**

    ⚠ 指図方は「決まったことを数値へ書き起こす」役で、**意匠の判断はしない**(規則17)。
    数値へ落として初めて見えた不整合は、直さずにここへ出して庭方へ返す — ⛔ 数値を
    黙って動かして辻褄を合わせない。⭕ 出す場所は `main` の隣家の宿題と同じ「別枠」で、
    **面のはみ出し検査と混ぜない**(混ぜると指図が不成立に見える)。
    """
    n = NI(d)
    if n is None:
        return []
    g, K = n.g, n.ken
    o = niwa_stats(d)
    out = []
    # ⚠ **築山の法は `niwa_check` が「実測の最急 ≤ batterFill」で見る**(2026-09-04 庭方の
    #   物差しの差し替え)。⛔ **素の丘(公称 × 2/π)との比較はしない** — 通過条件を解くと
    #   平場の幅 ≤ 7.5cm となり、平場を持つ限り構造的に通らない検査だった。
    # 園路の勾配は**1m 窓の最急**で見る(区間の両端だけだと急な中腹を見落とす)。
    cst8 = d["const"]
    for q in o.get("dote", []):
        if q["covered"] and q["batterIn"] < cst8["doteBatterCovered"] - 1e-9:
            out.append("**土手 %s の「刈込 %s に覆われる区間」の法が 1:%.3f**(上限 1:%.1f)— "
                       "rise を下げるか footprint を広げるのは意匠の判断【庭方の裁定の条】"
                       % (q["label"], q["covered"], q["batterIn"], cst8["doteBatterCovered"]))
        if q["batterOut"] < cst8["batterFill"] - 1e-9:
            out.append("**土手 %s の「刈込に覆われない区間(摺り付けを含む)」の法が 1:%.3f**"
                       "(上限 1:%.1f)— ⚠ **摺り付けそのものの勾配(稜線軸方向)は 1:%.3f で通る**が、"
                       "摺り付けの帯には**横断方向(減衰軸)の法がそのまま残る**ので、"
                       "面の勾配で測ると立つ。⇒ 刈込の footprint を土手と揃えて覆うか、"
                       "この帯を「端の勾配で見る」と定めるかは意匠の判断【庭方の裁定の条】"
                       % (q["label"], q["batterOut"], cst8["batterFill"], q["batterEnd"]))
    lim8 = d["const"].get("enroStepMax")
    for q in o["enro"]:
        if lim8 and q["stepMax"] >= lim8 - 1e-9 and q["stepAt"]:
            out.append("**%s に設計されていない段 %.2fm**((%.2f, %.2f)・起点から %.1fm)— "
                       "石段を切っていない区間なので、歩く人が躓く一段になる(上限 %.2fm)。"
                       "⛔ 「1m 窓の最急」はこの短い落差を『段であって勾配ではない』として"
                       "窓から落とすので、別の条で見る【庭方の裁定】"
                       % (q["label"], q["stepMax"], q["stepAt"][0], q["stepAt"][1],
                          q["stepAt"][2], lim8))
    for e, q in zip(g.get("enro", []), o["enro"]):
        stepG = e["keri"] / e["fumi"]
        if q["gradeWin"] > stepG * 100 + 1e-9:
            out.append("**%s の 1m 窓の最急が %.0f%%**(起点から %.1fm)— "
                       "指定の野面の石段(蹴上 %.2f / 踏面 %.2f = %.0f%%)でも登れない"
                       % (e["label"], q["gradeWin"], q["gradeWinAt"],
                          e["keri"], e["fumi"], stepG * 100))
    for e in g.get("enro", []):
        for (a, b) in zip(e["pts"], e["pts"][1:]):
            for m in d["munes"] + d["service"] + d["links"]:
                if "yaw" in m:
                    continue
                hit = 0
                for i in range(81):
                    t9 = i / 80.0
                    pu = a[0] + (b[0] - a[0]) * t9
                    pv = a[1] + (b[1] - a[1]) * t9
                    if m["u0"] + 1e-9 < pu < m["u1"] - 1e-9 and m["v0"] + 1e-9 < pv < m["v1"] - 1e-9:
                        hit += 1
                if hit > 1:
                    out.append("**%s が %s の隅を %.0f%% の区間で掠める** — "
                               "(%.2f, %.2f)→(%.2f, %.2f)。路の点を動かすのは意匠の判断"
                               % (e["label"], m["name"], 100.0 * hit / 81, a[0], a[1], b[0], b[1]))
    for k in g.get("kaki", []):
        if k.get("cert") == "?":
            out.append("**%s の走りが決まらない** — %s"
                       % (k["label"], "社地の矩形と開ける一方が設計書に無い"
                          if k["name"].startswith("Yotsume") else "設計書に寸法が無い"))
    # 埋樋の土被り(⚠ 地表より上に出ていたら「埋樋」ではない)
    ter0 = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
    for (u, v, y) in o["toi"]:
        q = terr_at(ter0, u, v)
        if q is not None and q - y < 0.30:
            out.append("**水尻の埋樋 (%.2f, %.2f) の土被りが %+.2fm**(下限 0.30m)— "
                       "復元地盤 %.2f に対し樋の底が %.2f。⭕ 石組の吐き口はここで地表へ出る"
                       "設計なので**終点は除いてよい**が、途中の点なら樋の線形か閾の高さを"
                       "見直すのは意匠の判断" % (u, v, q - y, q, y))
    for m in g.get("mikoro", []):
        if n.eye(m["no"]) is None:
            out.append("**見所 %d「%s」の眼高が決まらない** — `eyeMode`=%s の眼高が設計書に無い"
                       % (m["no"], m["label"], m.get("eyeMode")))
    out += niwa_plant_check(d)          # 庭方が要求した4本(据え位置・園路の離れ・樹冠)
    return out


def akichi_stats(d):
    """主郭の**無名の空白**を 0.5間格子で測る。⛔ 用途を発明しない — 位置で数えるだけ。"""
    out = []
    st = 0.5
    a1 = st * st * d["const"]["ken"] ** 2 / TSUBO
    occ = []
    for m in d["munes"] + d["service"]:
        occ.append(m)
    boxes = [(x["u0"], x["v0"], x["u1"], x["v1"]) for x in d["links"] + d["gardens"]]
    boxes += [(w["u"] - 0.5, w["v"] - 0.5, w["u"] + 0.5, w["v"] + 0.5) for w in d["wells"]]
    shu = next((t for t in d["terraces"] if t["name"] == "Shu"), None)
    if shu is None:
        return out, 0.0, []
    free = []
    u = shu["u0"] + st / 2
    while u < shu["u1"]:
        v = shu["v0"] + st / 2
        while v < shu["v1"]:
            if in_parcel(d, u, v) and not any(in_obb(m, u, v) for m in occ) \
                    and not any(a <= u <= c and b <= v <= e for a, b, c, e in boxes):
                free.append((u, v))
            v += st
        u += st
    named = set()
    for a in d.get("akichi", []):
        cell = [p for p in free if a["u0"] <= p[0] <= a["u1"] and a["v0"] <= p[1] <= a["v1"]]
        named |= set(cell)
        out.append(dict(name=a["name"], label=a["label"], tsubo=len(cell) * a1,
                        u0=a["u0"], v0=a["v0"], u1=a["u1"], v1=a["v1"], cert=a["cert"]))
    rest = [p for p in free if p not in named]
    return out, len(free) * a1, rest


def akichi_check(d):
    """明地の**枠**が重なっていないか。⚠ 枠の外に残る空白は失格ではない — 表と図に出す
    (⛔ 「枠を足せば消える」形の検査にしない。空白の実測そのものが成果物)。"""
    bad = []
    for a in d.get("akichi", []):
        for b in d.get("akichi", []):
            if a["name"] >= b["name"]:
                continue
            iu = min(a["u1"], b["u1"]) - max(a["u0"], b["u0"])
            iv = min(a["v1"], b["v1"]) - max(a["v0"], b["v0"])
            if iu > 1e-9 and iv > 1e-9:
                bad.append("明地の枠 %s と %s が %.1f×%.1f間 重なる — 坪数を二重に数える"
                           % (a["name"], b["name"], iu, iv))
    return bad


def terr_at(ter, u, v):
    """回転間格子の地形を (u,v) で引く(双一次)。"""
    if not ter:
        return None
    fu = (u - ter["u0"]) / ter["step"]
    fv = (v - ter["v0"]) / ter["step"]
    iu, iv = int(math.floor(fu)), int(math.floor(fv))
    if iu < 0 or iv < 0 or iu + 1 >= ter["nu"] or iv + 1 >= ter["nv"]:
        return None
    tu, tv = fu - iu, fv - iv
    q = []
    for (a, b) in ((iu, iv), (iu + 1, iv), (iu, iv + 1), (iu + 1, iv + 1)):
        h = ter["h"][b][a]
        if h is None:
            return None
        q.append(h)
    return (q[0] * (1 - tu) + q[1] * tu) * (1 - tv) + (q[2] * (1 - tu) + q[3] * tu) * tv


# ---------------------------------------------------------------- 奥庭の図
GOGAN_COL = {"石組護岸": "#6E7A83", "石組護岸(低)": "#9AA6AE",
             "州浜": "#C9A24B", "乱杭": "#7A5C3A", "(沢飛石の取付)": "#A8452C"}
LAYER_COL = {"高木": "#3F5F3A", "中木": "#6E8C4E", "花木": "#9C6B7A"}


def _chaikin(p, k=2):
    q = list(p)
    for _ in range(k):
        r = []
        n2 = len(q)
        for i in range(n2):
            a, b = q[i], q[(i + 1) % n2]
            r.append((a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25))
            r.append((a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75))
        q = r
    return q


def _tsuki_ring(n, t, h):
    """築山 t の標高差 h の等高線(平場を切った profile の逆関数)。"""
    if h <= 0 or h >= t["rise"]:
        return []
    s = math.acos(2.0 * h / t["rise"] - 1.0) / math.pi
    ru, rv = t["dU"] / 2.0, t["dV"] / 2.0
    da = t.get("daira")
    out = []
    for i in range(73):
        th = i / 72.0 * 2 * math.pi
        cx, cy = math.cos(th), math.sin(th)
        rd = 0.0
        if da:
            a = da["dU"] / 2.0 / ru
            b = da["dV"] / 2.0 / rv
            rd = min(1.0 / math.hypot(cx / a, cy / b), 0.95)
        r = rd + s * (1.0 - rd)
        out.append((t["u"] + r * cx * ru, t["v"] + r * cy * rv))
    return out


def niwa_plan_svg(d, W=760.0):
    n = NI(d)
    g = n.g
    o = niwa_stats(d)
    pr = LProj(-14.8, 3.2, 62.6, 83.0, W, top=26.0, bottom=30.0)
    sv = _sv(pr.W, pr.H, "土井大隅守上屋敷 奥庭の平面")
    X, Y, L = pr.X, pr.Y, pr.L

    def poly(pts, **kw):
        return '<polygon points="%s" %s/>' % (
            " ".join("%.1f,%.1f" % (X(u), Y(v)) for u, v in pts),
            " ".join('%s="%s"' % (k.replace("sw", "stroke-width").replace("op", "opacity"), v)
                     for k, v in kw.items()))

    def line(pts, col, w, dash=None, op=None):
        a = '<polyline points="%s" fill="none" stroke="%s" stroke-width="%.2f"' % (
            " ".join("%.1f,%.1f" % (X(u), Y(v)) for u, v in pts), col, w)
        if dash:
            a += ' stroke-dasharray="%s"' % dash
        if op is not None:
            a += ' opacity="%.2f"' % op
        return a + ' stroke-linejoin="round"/>'
    # 庭の地
    sv.append(pr.rect(g["u0"], g["v0"], g["u1"], g["v1"], fill="var(--niwa)",
                      stroke="var(--ink)", sw=1.4))
    # まわりの棟
    for m in d["munes"] + d["service"]:
        if "yaw" in m or m["u1"] < -14.8 or m["u0"] > 3.2 or m["v1"] < 62.6 or m["v0"] > 83.0:
            continue
        # ⚠ **窓の外へはみ出す棟を素の座標で描かない** — 見出しの帯まで塗りつぶす
        #   (2026-09-04 に踏んだ。居間棟が v52 から描かれて図の題を隠していた)。
        cu0, cu1 = max(m["u0"], pr.u0), min(m["u1"], pr.u1)
        cv0, cv1 = max(m["v0"], pr.v0), min(m["v1"], pr.v1)
        sv.append(pr.rect(cu0, cv0, cu1, cv1, fill="var(--ink-mid)",
                          stroke="var(--ink)", sw=1.2))
        sv.append(T((X(cu0) + X(cu1)) / 2, (Y(cv0) + Y(cv1)) / 2 + 4,
                    MUNE_JA.get(m["name"], m.get("label", m["name"])), "rmS", "middle", 11.0))
    # 築山の等高線
    for t in g["tsukiyama"]:
        if t.get("kata") == "土手":
            sv.append(pr.rect(t["u0"], t["v0"], t["u1"], t["v1"], fill="var(--tsuki)",
                              stroke="var(--tsuki)", sw=1.0, op=0.5))
            sv.append(T(X((t["u0"] + t["u1"]) / 2), Y(t["v0"]) + 12,
                        "%s +%.2f" % (t["label"], t["rise"]), "jo", "middle"))
            continue
        h = 0.25
        first = True
        while h < t["rise"]:
            rg = _tsuki_ring(n, t, h)
            if rg:
                sv.append(poly(rg, fill="var(--tsuki)" if first else "none",
                               stroke="#8A9070", sw=0.7, op=0.30 if first else 1.0))
                first = False
            h += 0.25
        sv.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="#5A6144"/>' % (X(t["u"]), Y(t["v"])))
        sv.append(T(X(t["u"]), Y(t["v"]) - 6, "%s %.2f" % (t["label"], t["topY"]),
                    "anS2", "middle"))
    # 池
    P = n.pond
    sv.append(poly(P, fill="var(--ike)", stroke="none"))
    sv.append(line(_chaikin(P) + [_chaikin(P)[0]], "#5B8296", 1.0, dash="3 3"))
    # 護岸(区間ごとに色)
    for i in range(len(P)):
        who = o["cover"].get(i, [])
        kata = "?"
        for x in g.get("gogan", []):
            if x["name"] in who:
                kata = x["kata"]
        if any(x["name"] in who for x in g.get("suhama", [])):
            kata = "州浜"
        if any(x["name"] in who for x in g.get("rangui", [])):
            kata = "乱杭"
        if "(沢飛石の取付)" in who:
            kata = "(沢飛石の取付)"
        sv.append(line([P[i], P[(i + 1) % len(P)]], GOGAN_COL.get(kata, "#C0392B"), 4.0))
    for i, (u, v) in enumerate(P):
        sv.append('<circle cx="%.1f" cy="%.1f" r="7" fill="var(--paper)" stroke="#5B8296" stroke-width="1"/>'
                  % (X(u), Y(v)))
        sv.append(T(X(u), Y(v) + 3.5, str(i + 1), "jo", "middle", 9.0))
    # 州浜の帯
    for s in g.get("suhama", []):
        i = s["frm"] - 1
        seg = [P[i]]
        while i != s["to"] - 1:
            i = (i + 1) % len(P)
            seg.append(P[i])
        sv.append(line(seg, GOGAN_COL["州浜"], L(s["toLand"] / n.ken + s["fromWater"] / n.ken),
                       op=0.35))
    # 岩島
    for w in g.get("iwajima", []):
        sv.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#6E7A83"/>'
                  % (X(w["u"]), Y(w["v"]), L(w["hMain"] / n.ken * 0.5)))
        sv.append(T(X(w["u"]) + 9, Y(w["v"]) + 4, "岩島", "jo"))
    # 沓脱・飛石・沢飛石
    for k in g.get("kutsunugi", []):
        sv.append(pr.rect(k["u"] - k["L"] / 2 / n.ken, k["v"] - k["W"] / 2 / n.ken,
                          k["u"] + k["L"] / 2 / n.ken, k["v"] + k["W"] / 2 / n.ken,
                          fill="#8A8F94", stroke="var(--ink)", sw=0.8))
        sv.append(T(X(k["u"]) - 10, Y(k["v"]) + 4, "沓脱石", "jo", "end"))
    for t in g.get("tobiishi", []):
        for j, (u, v) in enumerate(t["pts"]):
            r = L((t["fumiwakeR"] if j == t["fumiwake"] else 0.45) / n.ken * 0.5)
            sv.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#9AA0A5" stroke="var(--ink)" stroke-width="0.6"/>'
                      % (X(u), Y(v), r))
    for s in o["sawa"]:
        sw = next(x for x in g["sawatobi"] if x["name"] == s["name"])
        for j in range(s["n"]):
            t9 = (j + 0.5) / s["n"]
            u = sw["a"][0] + (sw["b"][0] - sw["a"][0]) * t9
            v = sw["a"][1] + (sw["b"][1] - sw["a"][1]) * t9
            sv.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#9AA0A5" stroke="var(--ink)" stroke-width="0.6"/>'
                      % (X(u), Y(v), L((sw["rMin"] + sw["rMax"]) / 2 / n.ken * 0.5)))
        sv.append(T(X((sw["a"][0] + sw["b"][0]) / 2) - 6, Y((sw["a"][1] + sw["b"][1]) / 2) - 8,
                    "沢飛石 %d石" % s["n"], "jo", "end"))
    # 三尊石・灯籠
    for s in g.get("ishigumi", []):
        sv.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#4E585F"/>'
                  % (X(s["u"]), Y(s["v"]), max(2.0, L(s["h"] / n.ken * 0.4))))
    if g.get("ishigumi"):
        s0 = g["ishigumi"][0]
        sv.append(T(X(s0["u"]) - 8, Y(s0["v"]) - 8, "三尊石", "jo", "end"))
    for t in g.get("toro", []):
        sv.append('<path d="M %.1f %.1f l 5 8 h -10 Z" fill="var(--shu)"/>' % (X(t["u"]), Y(t["v"]) - 8))
        sv.append(T(X(t["u"]), Y(t["v"]) - 9, t["label"], "jo", "middle"))
    # 刈込 — 矩形2枚と**汀線のオフセット帯**3枚(2026-09-04 庭方の第3巡)
    for k in g.get("karikomi", []):
        poly = karikomi_poly(d, k)
        if not poly:
            continue
        sv.append('<polygon points="%s" fill="#7E9A5E" stroke="#5E7A3E" '
                  'stroke-width="0.8" opacity="0.55"/>'
                  % " ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in poly))
    # 下草(シダ)の散布域 — ⭐ **2026-09-06 に言葉から幾何へ落とした**ので図にも出す
    #   (⛔ 計算しただけで図に出さないと規則19違反)。植栽より先に敷いて樹の下に見せる。
    # ⚠ **水面で切る。**築山A1 の裾は設計どおり汀へ落ちるので、半楕円をそのまま塗ると
    #   池の上に草が乗る。庭の矩形から池を抜いた even-odd のクリップを噛ませる。
    _clip = "sk%d" % _SVN[0]
    sv.append('<defs><clipPath id="%s" clip-rule="evenodd"><path d="M %s Z M %s Z"/>'
              '</clipPath></defs>'
              % (_clip,
                 " L ".join("%.1f %.1f" % (X(u), Y(v)) for u, v in
                            [(g["u0"], g["v0"]), (g["u1"], g["v0"]),
                             (g["u1"], g["v1"]), (g["u0"], g["v1"])]),
                 " L ".join("%.1f %.1f" % (X(u), Y(v)) for u, v in n.pond)))
    sv.append('<g clip-path="url(#%s)">' % _clip)
    for _sk in shitakusa_regions(d):
        if _sk["poly"]:
            sv.append('<polygon points="%s" fill="#9BB07A" stroke="#6E8C4E" '
                      'stroke-width="0.7" stroke-dasharray="2 3" opacity="0.42"/>'
                      % " ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in _sk["poly"]))
        for (cu, cv, cr) in _sk["circ"]:
            sv.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#9BB07A" '
                      'stroke="#6E8C4E" stroke-width="0.7" stroke-dasharray="2 3" '
                      'opacity="0.42"/>' % (X(cu), Y(cv), L(cr)))
    sv.append('</g>')
    # 植栽
    for s in g.get("shokusai", []):
        dim = [asset_dim(x) for x in s.get("idx", [])]
        dim = [x for x in dim if x]
        wm = (max(q[0] for q in dim) * s.get("scale", 1.0)) if dim else 3.0
        hm = (max(q[1] for q in dim) * s.get("scale", 1.0)) if dim else 5.0
        for (u, v) in s["at"]:
            sv.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                      'stroke="%s" stroke-width="1" stroke-dasharray="3 3" opacity="0.65"/>'
                      % (X(u), Y(v), L(wm / 2 / n.ken), LAYER_COL.get(s["layer"], "#3F5F3A")))
            sv.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>'
                      % (X(u), Y(v), LAYER_COL.get(s["layer"], "#3F5F3A")))
            sv.append(T(X(u), Y(v) - 5, "%s%s" % (s["species"][:4], s["size"][0]),
                        "jo", "middle", 8.0))
    # 垣
    for k in g.get("kaki", []):
        if k.get("pts"):
            sh = k.get("shachi")
            if sh:
                sv.append(pr.rect(sh["u0"], sh["v0"], sh["u1"], sh["v1"], fill="none",
                                  stroke="#6B4E2E", sw=0.7, dash="3 3", op=0.7))
            sv.append(line(k["pts"], "#5F7A4E", 2.6))     # 三方(透かす垣)
            sv.append(T(X(sh["u1"]) - 6 if sh else X(k["pts"][0][0]) - 6,
                        (Y(k["pts"][0][1]) + Y(k["pts"][-1][1])) / 2,
                        "四つ目垣 h%.1f(南開き)" % k["h"], "jo", "end"))
        elif "v" in k:
            sv.append(line([(k["u0"], k["v"]), (k["u1"], k["v"])], "#6B4E2E", 3.0))
            sv.append(T(X((k["u0"] + k["u1"]) / 2), Y(k["v"]) + 13, k["label"], "jo", "middle"))
    # 稲荷
    ya = g["yashiro"]
    sv.append(line(ya["sando"]["pts"], "#C9A24B", L(ya["sando"]["w"] / n.ken), op=0.7))
    tr = ya["torii"]
    sv.append(LN(X(tr["u"]), Y(tr["v"]) - 9, X(tr["u"]), Y(tr["v"]) + 9, "var(--shu)", 2.6))
    sv.append(T(X(tr["u"]), Y(tr["v"]) + 20, "鳥居(素木)", "jo", "middle"))
    ch = ya["chozu"]
    sv.append(pr.rect(ch["u"] - ch["L"] / 2 / n.ken, ch["v"] - ch["W"] / 2 / n.ken,
                      ch["u"] + ch["L"] / 2 / n.ken, ch["v"] + ch["W"] / 2 / n.ken,
                      fill="#6E7A83", stroke="var(--ink)", sw=0.6))
    sv.append(T(X(ch["u"]), Y(ch["v"]) - 9, "手水石", "jo", "middle"))
    # 園路
    for e in g.get("enro", []):
        # ⭐ **区間ごとの幅で描く**(稲荷の隘路だけ締まる)。⛔ 一本の幅で描くと、
        #   図の上では締まっていないのに検査だけが締まった幅を見ることになる。
        for (a9, b9) in zip(e["pts"], e["pts"][1:]):
            hw9 = _enro_halfwidth(e, (a9[0] + b9[0]) / 2.0, (a9[1] + b9[1]) / 2.0)
            sv.append(line([a9, b9], "var(--michi)", L(hw9 * 2.0 / n.ken), op=0.55))
        for (a, b) in zip(e["pts"], e["pts"][1:]):
            l = math.dist(a, b) * n.ken
            if l < 1e-9:
                continue
            gr = abs(n.ground(*b) - n.ground(*a)) / l
            if gr * 100 > 15.0:
                sv.append(line([a, b], "var(--shu)", 2.0, dash="2 3"))
    # 水尻
    tp = [(u, v) for u, v, _ in o["toi"]] + [tuple(g["mizu"]["mizushiri"]["otoshimizo"]["to"])]
    sv.append(line(tp, "#3E6A8A", 2.0, dash="6 3"))
    sv.append('<circle cx="%.1f" cy="%.1f" r="4" fill="none" stroke="#3E6A8A" stroke-width="1.6"/>'
              % (X(tp[-1][0]), Y(tp[-1][1])))
    sv.append(T(X(tp[-1][0]), Y(tp[-1][1]) + 15, "受け石(浸透枡)", "jo", "middle"))
    sv.append(T(X(tp[0][0]) - 9, Y(tp[0][1]) + 4, "水尻の閾", "jo", "end"))
    # 井戸
    for w in d["wells"]:
        if not (g["u0"] - 1 <= w["u"] <= g["u1"] + 1 and g["v0"] - 1 <= w["v"] <= g["v1"] + 1):
            continue
        sv.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--paper)" stroke="var(--ink)" stroke-width="1.6"/>'
                  % (X(w["u"]), Y(w["v"])))
        sv.append(T(X(w["u"]) + 8, Y(w["v"]) + 4, "井戸", "jo"))
    # 見所
    for m in g["mikoro"]:
        col = "var(--shu)" if m.get("main") else "#7A6A50"
        sv.append('<circle cx="%.1f" cy="%.1f" r="9" fill="%s"/>' % (X(m["u"]), Y(m["v"]), col))
        sv.append(T(X(m["u"]), Y(m["v"]) + 4, str(m["no"]), "jo", "middle", 11.0,
                    fill="var(--paper)"))
        if m.get("dir") == "-u":
            sv.append(LN(X(m["u"]) + 10, Y(m["v"]), X(m["u"]) + 42, Y(m["v"]), col, 1.6, dash="5 3"))
        elif m.get("dir") == "+v":
            sv.append(LN(X(m["u"]), Y(m["v"]) + 10, X(m["u"]), Y(m["v"]) + 34, col, 1.6, dash="5 3"))
    sv.append(T(4, 15, "グリッド座標(u=北+ / v=奥(西)+)。**上=東 / 左=北 / 下=西 / 右=南**。"
                "汀線の番号は設計値の順", "anS"))
    sv.append(T(4, 27, "細い破線の輪郭=Chaikin×2(施工形状) ／ 破線の円=樹冠の実寸",
                "anS2", "start"))
    sv.append(T(4, pr.H - 6, "朱の丸=主視点 / 茶の丸=その他の見所 / 朱の破線=野面の石段を切る区間 / "
                "青の破線=水尻の埋樋 / 緑の実線=四つ目垣(三方・南開き)", "anS2", "start"))
    sv.append("</svg>")
    return "\n".join(sv)


def niwa_section_svg(d, sec, W=880.0):
    n = NI(d)
    g = n.g
    o = niwa_stats(d)
    m0 = next(x for x in g["mikoro"] if x["no"] == sec["frm"])
    e0 = n.eye(m0["no"])
    a = (m0["u"], m0["v"])
    b = tuple(sec["to"])
    Lm = math.dist(a, b) * n.ken
    ve = sec["vExag"]
    top, bot, pad = 30.0, 34.0, 54.0
    # ⚠ 縦の窓は**中身から決める**。固定にすると蔵の無い断面が空欄だらけになる
    #   (2026-09-04 の1巡目で「斜めの断面」が9割白紙だった)。
    _q = [e0, n.bed(*a) if n.inpond(*a) else n.ground(*a)]
    for _i in range(41):
        _t = _i / 40.0
        _u = a[0] + (b[0] - a[0]) * _t
        _v = a[1] + (b[1] - a[1]) * _t
        _q.append(n.ground(_u, _v))
    _ku0 = n.kura()
    if _ku0 and sec.get("kura"):
        _q += [_ku0["ridge"], _ku0["o"]["y"]]
    for _s0 in niwa_stats(d)["screen"]:
        if sec.get("kura"):
            _q.append(_s0["gy"] + _s0["h"])
    y0 = math.floor(min(_q)) - 0.5
    y1 = math.ceil(max(_q)) + 0.5
    s = (W - pad * 2) / Lm
    H = (y1 - y0) * ve * s + top + bot

    def PX(t):
        return pad + t * Lm * s

    def PY(y):
        return top + (y1 - y) * ve * s
    sv = _sv(W, H, "土井大隅守上屋敷 %s" % sec["label"])
    yy = math.ceil(y0 * 2) / 2
    while yy <= y1 + 1e-9:
        sv.append(LN(pad, PY(yy), W - pad, PY(yy), "var(--rule)", 0.6))
        sv.append(T(pad - 5, PY(yy) + 3, "%.1f" % yy, "jo", "end"))
        yy += 0.5
    N = 320
    gr = []
    for i in range(N + 1):
        t = i / float(N)
        u = a[0] + (b[0] - a[0]) * t
        v = a[1] + (b[1] - a[1]) * t
        gr.append((PX(t), PY(n.ground(u, v))))
    sv.append('<polygon points="%s" fill="var(--pl-main)"/>'
              % (" ".join("%.1f,%.1f" % p for p in gr)
                 + " %.1f,%.1f %.1f,%.1f" % (PX(1), PY(y0), PX(0), PY(y0))))
    sv.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
              % " ".join("%.1f,%.1f" % p for p in gr))
    # 池は**水面から池床まで**を塗る(水面の帯だけだと水深が読めない)
    seg = []
    for i in range(N + 1):
        t = i / float(N)
        u = a[0] + (b[0] - a[0]) * t
        v = a[1] + (b[1] - a[1]) * t
        if n.inpond(u, v):
            seg.append((t, n.bed(u, v)))
        elif seg:
            sv.append('<polygon points="%s" fill="var(--ike)" stroke="#5B8296" stroke-width="1"/>'
                      % (" ".join("%.1f,%.1f" % (PX(q), PY(n.waterY)) for q, _ in seg)
                         + " " + " ".join("%.1f,%.1f" % (PX(q), PY(bb)) for q, bb in reversed(seg))))
            seg = []
    # 御土蔵
    ku = o.get("kura")
    if ku and sec.get("kura"):
        tk = (a[0] - ku["face"]) / (a[0] - b[0]) if abs(a[0] - b[0]) > 1e-9 else 1.0
        x0 = PX(min(tk, 1.0))
        x1 = W - pad
        sv.append(R(x0, PY(ku["ridge"]), max(2.0, x1 - x0), PY(ku["o"]["y"]) - PY(ku["ridge"]),
                    fill="var(--paper2)", stroke="var(--ink)", sw=1.4))
        sv.append(LN(x0, PY(ku["eave"]), x1, PY(ku["eave"]), "var(--ink)", 1.0, dash="4 3"))
        sv.append(T(min((x0 + x1) / 2, W - pad - 4), PY(ku["ridge"]) - 6,
                    "御土蔵(文書)棟 %.2f / 軒下端 %.2f【部材の実測】" % (ku["ridge"], ku["eave"]),
                    "anS2", "end"))
        # 見切り線
        for lv, col, nm, fr in ((ku["eave"], "var(--shu)", "眼 → 蔵の軒下端 への視線", 0.62),
                                (ku["ridge"], "#C77F5A", "眼 → 蔵の棟 への視線", 0.42)):
            sv.append(LN(PX(0), PY(e0), x0, PY(lv), col, 1.4, dash="6 3"))
            sv.append(T(PX(0) + (x0 - PX(0)) * fr, PY(e0) + (PY(lv) - PY(e0)) * fr - 5,
                        nm, "jo", "middle", 9.5, fill=col))
        # 塞ぐべき帯。⚠ **切り面から遠い木を断面に描かない** — 3本とも u がほぼ同じで、
        #   そのまま描くと重なって読めない(v が 4〜7間 離れていて切り面の上に無い)。
        #   遠い木の検算は下の表が受け持つ。
        far = 0
        for sc in o["screen"]:
            t = (a[0] - sc["u"]) / (a[0] - b[0]) if abs(a[0] - b[0]) > 1e-9 else 0.0
            if not (0 < t < 1):
                continue
            vv = a[1] + (b[1] - a[1]) * t
            if abs(sc["v"] - vv) > 2.0:
                far += 1
                continue
            sv.append(R(PX(t) - 5, PY(sc["gy"] + sc["hi"]), 10,
                        PY(sc["gy"] + sc["lo"]) - PY(sc["gy"] + sc["hi"]),
                        fill="var(--shu)", op=0.30))
            sv.append(R(PX(t) - 14, PY(sc["gy"] + sc["h"]), 28,
                        PY(sc["gy"] + sc["c0"]) - PY(sc["gy"] + sc["h"]),
                        fill="#3F5F3A", op=0.22, stroke="#3F5F3A", sw=1.0))
            sv.append(T(PX(t), PY(sc["gy"] + sc["h"]) - 5,
                        "常緑広葉Big 樹冠 %.1f〜%.1fm" % (sc["c0"], sc["h"]), "jo", "middle"))
            sv.append(T(PX(t), PY(sc["gy"] + sc["lo"]) + 12,
                        "塞ぐ帯 %.2f〜%.2fm %s" % (sc["lo"], sc["hi"], "⭕" if sc["ok"] else "⚠"),
                        "jo", "middle"))
        if far:
            sv.append(T(W - pad, top + 12,
                        "⚠ 切り面から 2間 より遠い常緑広葉Big %d本 は描いていない(検算は表)"
                        % far, "jo", "end"))
    # 見切り線(眼から地表に接する視線)と、その陰に落ちる水面
    ang, tg = -9e9, 0.0
    hid = []
    for i in range(1, N + 1):
        t = i / float(N)
        u = a[0] + (b[0] - a[0]) * t
        v = a[1] + (b[1] - a[1]) * t
        gy = n.ground(u, v)
        q = (gy - e0) / (t * Lm)
        if q > ang:
            ang, tg = q, t
        if n.inpond(u, v) and n.waterY < e0 + ang * t * Lm - 0.02:
            hid.append(t)
    if hid:
        sv.append(LN(PX(0), PY(e0), PX(1), PY(e0 + ang * Lm), "#B03A2E", 1.2, dash="7 3"))
        sv.append(T(PX(min(tg + 0.06, 0.95)), PY(e0 + ang * (min(tg + 0.06, 0.95)) * Lm) - 6,
                    "見切り線(眼から地表に接する視線)", "jo", "middle", 9.5, fill="#B03A2E"))
        sv.append(R(PX(min(hid)), PY(n.waterY) - 4, max(2.0, PX(max(hid)) - PX(min(hid))), 8,
                    fill="#B03A2E", op=0.40))
        sv.append(T((PX(min(hid)) + PX(max(hid))) / 2, PY(n.waterY) + 18,
                    "見所から**見えない水面**(見隠れ)", "jo", "middle", 9.5, fill="#B03A2E"))
    # 眼
    sv.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>' % (PX(0), PY(e0)))
    sv.append(T(PX(0) + 7, PY(e0) - 6, "見所 %d %s 眼高 %.2f" % (m0["no"], m0["label"], e0), "anS2"))
    sv.append(LN(pad, PY(n.waterY), W - pad, PY(n.waterY), "#5B8296", 0.8, dash="3 4"))
    sv.append(T(W - pad + 3, PY(n.waterY) + 3, "水面 %.2f" % n.waterY, "jo"))
    sv.append(T(4, 15, "%s ／ 水平 %.1fm ／ 垂直 %.1f倍" % (sec["label"], Lm, ve), "anS"))
    sv.append(T(4, H - 6, sec.get("_", ""), "anS2", "start"))
    sv.append("</svg>")
    return "\n".join(sv)


def niwa_mizushiri_svg(d, W=820.0):
    n = NI(d)
    g = n.g
    o = niwa_stats(d)
    ter = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
    ms = g["mizu"]["mizushiri"]
    pts = [(u, v, y) for u, v, y in o["toi"]]
    to = ms["otoshimizo"]["to"]
    pts.append((to[0], to[1], None))
    acc, cum = [0.0], 0.0
    for i in range(len(pts) - 1):
        cum += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) * n.ken
        acc.append(cum)
    top, bot, pad = 28.0, 52.0, 62.0
    _gy = [terr_at(ter, u, v) for u, v, _ in pts[:-1]] + [terr_at(ter, to[0], to[1])]
    _gy = [q for q in _gy if q is not None] + [y for _, _, y in pts if y is not None]
    y0 = math.floor(min(_gy) * 5) / 5 - 0.2
    y1 = math.ceil(max(_gy) * 5) / 5 + 0.2
    ve = 18.0
    s = (W - pad * 2) / cum
    H = (y1 - y0) * ve * s + top + bot

    def PX(m):
        return pad + m * s

    def PY(y):
        return top + (y1 - y) * ve * s
    sv = _sv(W, H, "土井大隅守上屋敷 水尻の縦断")
    yy = y0
    while yy <= y1 + 1e-9:
        sv.append(LN(pad, PY(yy), W - pad, PY(yy), "var(--rule)", 0.6))
        sv.append(T(pad - 5, PY(yy) + 3, "%.1f" % yy, "jo", "end"))
        yy += 0.2
    # 復元地盤
    gp = []
    for i in range(len(pts) - 1):
        for k in range(21):
            t = k / 20.0
            u = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t
            v = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
            q = terr_at(ter, u, v)
            if q is not None:
                gp.append((PX(acc[i] + (acc[i + 1] - acc[i]) * t), PY(q)))
    if gp:
        sv.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
                  % " ".join("%.1f,%.1f" % p for p in gp))
    sv.append('<polyline points="%s" fill="none" stroke="#3E6A8A" stroke-width="2.2"/>'
              % " ".join("%.1f,%.1f" % (PX(acc[i]), PY(pts[i][2]))
                         for i in range(len(pts) - 1)))
    for i in range(len(pts) - 1):
        sv.append('<circle cx="%.1f" cy="%.1f" r="3" fill="#3E6A8A"/>'
                  % (PX(acc[i]), PY(pts[i][2])))
        sv.append(T(PX(acc[i]), PY(pts[i][2]) - 7, "%.2f" % pts[i][2], "jo", "middle"))
        sv.append(T(PX(acc[i]), H - 34 + (14 if i % 2 else 0),
                    "(%.1f, %.1f)" % (pts[i][0], pts[i][1]), "jo", "middle", 8.5))
    sv.append(T(PX(acc[0]) + 4, PY(pts[0][2]) - 20, "石の閾(余水吐)", "anS2"))
    sv.append(T(PX(acc[-2]) - 4, PY(pts[-2][2]) - 20, "石組の吐き口", "anS2", "end"))
    sv.append(T(PX(acc[-1]), H - 14, "受け石(玉石の浸透枡)", "jo", "middle"))
    sv.append(T(4, 15, "水尻の縦断 ／ 延長 %.1fm ／ 樋の勾配 %.2f%% ／ 垂直 %.0f倍 ／ "
                "細い実線=江戸期の復元地盤(確度P)" % (o["toiLen"], o["toiGrade"], ve), "anS"))
    sv.append("</svg>")
    return "\n".join(sv)


def akichi_svg(d, W=760.0):
    rows, tot, rest = akichi_stats(d)
    shu = next(t for t in d["terraces"] if t["name"] == "Shu")
    pr = LProj(shu["u0"] - 1, shu["u1"] + 1, shu["v0"] - 1, shu["v1"] + 1, W, top=24.0, bottom=22.0)
    sv = _sv(pr.W, pr.H, "土井大隅守上屋敷 主面の明地")
    sv.append(pr.rect(shu["u0"], shu["v0"], shu["u1"], shu["v1"], fill="var(--pl-main)",
                      stroke="var(--ink)", sw=1.2))
    # ⚠ **描く順**: 地 → 物 → 空白 → 枠 → 名。空白を先に塗ると棟と庭に覆われて消える
    #   (2026-09-04 の1巡目で実際に消えていた)。
    for m in d["munes"] + d["service"]:
        if "yaw" in m:
            sv.append('<polygon points="%s" fill="var(--ink-mid)" stroke="var(--ink)" stroke-width="1"/>'
                      % " ".join("%.1f,%.1f" % (pr.X(x), pr.Y(y)) for x, y in obb_pts(m)))
            continue
        sv.append(pr.rect(m["u0"], m["v0"], m["u1"], m["v1"], fill="var(--ink-mid)",
                          stroke="var(--ink)", sw=1.0))
    for l in d["links"]:
        sv.append(pr.rect(l["u0"], l["v0"], l["u1"], l["v1"], fill="var(--roka)"))
    for g in d["gardens"]:
        sv.append(pr.rect(g["u0"], g["v0"], g["u1"], g["v1"], fill="var(--niwa)",
                          stroke="var(--ink)", sw=0.8, op=0.9))
    st = 0.5
    for (u, v) in rest:
        sv.append(R(pr.X(u + st / 2), pr.Y(v - st / 2), pr.L(st), pr.L(st),
                    fill="#C0392B", op=0.32))
    for a in d.get("akichi", []):
        sv.append(pr.rect(a["u0"], a["v0"], a["u1"], a["v1"], fill="none",
                          stroke="var(--shu)", sw=1.8, dash="7 4"))
    for a in rows:
        cx = min(max((pr.X(a["u0"]) + pr.X(a["u1"])) / 2, 96.0), pr.W - 96.0)
        sv.append(T(cx, (pr.Y(a["v0"]) + pr.Y(a["v1"])) / 2,
                    "%s %.1f坪【%s】" % (a["label"], a["tsubo"], a["cert"]), "rmS", "middle", 11.0))
    if rest:
        sv.append(T(pr.W / 2, pr.H - 4,
                    "赤=どの枠にも入っていない空白 %.1f坪(枠を足せば消えるが、"
                    "空白の実測そのものが成果物)" % (len(rest) * 0.25 * d["const"]["ken"] ** 2 / TSUBO),
                    "anS2", "middle"))
    sv.append(T(4, 15, "主面 Shu の**無名の空白**を 0.5間格子で測ったもの。朱の破線=明地の枠 / "
                "赤の塗り=どの枠にも入っていない空白 / 灰=棟・付属屋 / 緑=庭", "anS"))
    sv.append(T(4, pr.H - 6, "⭐ 4枠のうち「表と中奥の間」は 2026-09-04 の考証で**中庭**【B】として名が立った / "
                "残る3枠は明地【?】— ⛔ 用途を発明しない", "anS2"))
    sv.append("</svg>")
    return "\n".join(sv)


def _tw(head, rows):
    return ("<div class='tw'><table><thead><tr>"
            + "".join("<th>%s</th>" % h for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>" for r in rows)
            + "</tbody></table></div>")


# ⚠ **入母屋の隅棟は軒先線よりさらに出る**(部材方の実測: 呼び 19.998 に対し bbox 20.323)。
#   ⛔ 軒先線だけで離れを読まない(2026-09-06 庭方 低3)。片側 **0.171m**。
SUMI = 0.171


def niwa_pond_table(d):
    o = niwa_stats(d)
    n = NI(d)
    rows = [
        ("水面", "%.1f m²(%.1f坪)" % (o["areaM2"], o["tsubo"]), "庭 %.1f坪 の <b>%.1f%%</b>"
         % (o["gardenTsubo"], o["waterPct"])),
        ("周長 / 頂点", "%.1f m / %d点" % (o["per"], len(n.pond)),
         "辺長 %.2f〜%.2f m" % (o["segMin"], o["segMax"])),
        ("円形度 4πA/P²", "<b>%.3f</b>" % o["circ"], "1.00=真円。⭕ 丸くない"),
        ("辺長の変動係数 CV", "<b>%.3f</b>" % o["cv"], "0=等間隔。⭕ 等間隔でない"),
        ("くびれ(水口)", "#%d ↔ #%d %.2f m" % (o["kubire"][0], o["kubire"][1], o["kubireM"]),
         "沢飛石が渡る"),
        ("汀 → 庭の境", "%.2f 間(%s)" % (o["clrBound"], o["clrBoundBy"]),
         "下限 %.2f 間" % n.mg["clearance"]["gardenBound"]),
        ("汀 → 最寄りの棟", "躯体まで %.2f 間(%s)<br><b>軒先まで %.2f 間</b>"
         % (o["clrMune"], o["clrMuneBy"], o["clrMuneEave"]),
         "下限 %.2f 間(稲荷の小祠は庭の点景なので除く)。"
         "⚠ <b>軒が %.2fm 出る</b>ので、⛔ 躯体までの値だけで読まない"
         "(2026-09-06 庭方 低2)。<br>⚠⚠ <b>軒先線には隅棟の飛び出し %.3fm が入っていない</b> — "
         "<b>隅まで含めると %.2f 間</b>(⭕ 下限は満たす)。"
         "⚠ 奥棟の南の両隅で庭の矩形を <b>%.2fm 越える</b>が、"
         "⭕ そこは<b>犬走り</b>なので当たりは無い(2026-09-06 庭方 低3)。"
         % (n.mg["clearance"]["mune"], d["const"]["nokiDe"], SUMI,
            o["clrMuneEave"] - SUMI / d["const"]["ken"], 0.16)),
        ("水面 → 岸の余裕高(最小)", "<b>%+.2f m</b>(汀 #%d の外 %.1f間)"
         % (o["fbMin"], o["fbMinAt"][0], o["fbMinAt"][1]),
         "水面 %.2f。⭕ <b>正=水面が岸より低い</b>(汀線 %d 辺 × 外へ 0.3/0.6間 を実測)"
         % (n.waterY, len(n.pond))),
        ("主視点から見える水面", "<b>%.0f%%</b>" % o["visPct"],
         "隠れる %.0f%% の内訳: <b>築山の見隠れ %.0f%%</b> / 手前の岸 %.0f%%(座視では必ず起きる)"
         % (100.0 - o["visPct"], o["hidMoundPct"], o["hidBankPct"])),
    ]
    return _tw(("指標", "値", "判定"), rows)


def niwa_vol_table(d):
    o = niwa_stats(d)
    n = NI(d)
    rows = [("掘削(池)", "%.0f m³" % o["cut"], "水面 %.0f m²・平均掘り %.2f m"
             % (o["pondM2"], o["cut"] / o["pondM2"]))]
    for t in n.g["tsukiyama"]:
        rows.append(("盛土 %s" % t["label"], "", "頂 %s / 盛 +%.2f m"
                     % (("%.2f" % t["topY"]) if "topY" in t else "—", t["rise"])))
    rows.append(("盛土(合計)", "%.0f m³" % o["fill"], "築山4基+東の土手+蔵前の土手"))
    # ⛔ **符号の向きは当図で一つ**(検図方 低-1)。其四の切盛表と同じく
    #   **差引 = 盛土 − 切土 / 正 = 土が足りない**で刷る。⛔ ここだけ逆向きにしない。
    rows.append(("差引(盛土 − 切土)", "<b>%+.0f m³</b>" % (-o["diff"]),
                 "正=土が足りない(其四の切盛表と同じ向き)。⭐ <b>読み下すと %s</b>"
                 % ("%.0f m³ 余る" % o["diff"] if o["diff"] > 0 else
                    "%.0f m³ 足りない" % -o["diff"])))
    rows.append(("庭の陸地に均すと", "<b>%+.3f m</b>" % o["level"],
                 "陸地 %.0f m²。許容 ±0.5m ⭕ 敷地外へ土を出さない・入れない" % o["landM2"]))
    w = o["water"]
    rows.append(("水の収支(年)", "%+.0f m³/年" % w["bal"],
                 "集水 %.0f(屋根+池面×降水 %.0fmm)− 蒸発 %.0f(%.0fmm)"
                 % (w["inflow"], n.g["mizu"]["gensen"]["rainMmY"], w["out"],
                    n.g["mizu"]["gensen"]["johatsu"]["mmY"])))
    return _tw(("項目", "量", "内訳"), rows)


def niwa_gogan_table(d):
    o = niwa_stats(d)
    n = NI(d)
    g = n.g
    rows = []
    for s in g.get("suhama", []):
        rows.append(("州浜", s["label"], "#%d–#%d" % (s["frm"], s["to"]), "—",
                     "砂利 水面下 %.1fm〜内陸 %.1fm・平石 %d個・そこの草は消す"
                     % (s["fromWater"], s["toLand"], s["stones"])))
    for x in o["gogan"]:
        q = next(y for y in g["gogan"] if y["name"] == x["name"])
        rows.append((q["kata"], q["label"], "#%d–#%d" % (q["frm"], q["to"]),
                     "%.1f m" % x["L"],
                     "%s %d 個(うち役石 %d)・1/3埋め・天端 水面+%.2f〜+%.2f"
                     % (q.get("ishi", "⚠ 石材が指図に無い"), x["n"], x["yaku"],
                        q["capMin"], q["capMax"])))
    for x in o["rangui"]:
        q = next(y for y in g["rangui"] if y["name"] == x["name"])
        rows.append(("乱杭", q["label"], "#%d–#%d" % (q["frm"], q["to"]), "%.1f m" % x["L"],
                     # ⭐ 天端は**水面からの相対の範囲**(⛔ 頭を揃えない=乱杭の作法)。
                     #   ⚠ 旧 `topY` 25.87 は水面 −0.33 で**頭が水没**していた(2026-09-06 是正)。
                     "杭 %d 本(芯々 %.3fm)・径 %.3f〜%.3f・傾±%.0f°・"
                     "天端 <b>水面 +%.2f〜+%.2f</b>(= %.2f〜%.2f)"
                     % (x["n"], q["pitch"], q["rMin"], q["rMax"], q["tilt"],
                        q["topAbove"][0], q["topAbove"][1],
                        n.waterY + q["topAbove"][0], n.waterY + q["topAbove"][1])
                     + ("<br>⛔ <b>隣どうしで毎本振らない</b>(白色ノイズは櫛の歯に見える)— "
                        "<b>%s</b>。時々1本だけ外れ値を入れる。"
                        "⭕ 傾き ±%.0f° は1本ごとに振ってよい(隣どうしの差が線として見えない)。"
                        % (q["topWave"], q["tilt"]) if q.get("topWave") else "")))
    tk = g.get("sawatobiTake")
    if tk:
        rows.append(("(素の汀)", "沢飛石の南詰の取付", "#%d–#%d" % (tk["frm"], tk["to"]), "—",
                     "⚠ ここだけ護岸を置かない(庭方の指定)"))
    return _tw(("形式", "区間の名", "汀線", "延長", "仕様"), rows)


def niwa_plant_table(d):
    n = NI(d)
    rows = []
    for s in n.g.get("shokusai", []):
        dim = [(x, asset_dim(x)) for x in s.get("idx", [])]
        got = [q for q in dim if q[1]]
        miss = [q[0] for q in dim if not q[1]]
        sc = s.get("scale", 1.0)
        h = ("%.1f〜%.1f m" % (min(q[1][1] for q in got) * sc, max(q[1][1] for q in got) * sc)
             if got else "⚠ 目録に無い")
        w = ("%.1f〜%.1f m" % (min(q[1][0] for q in got) * sc, max(q[1][0] for q in got) * sc)
             if got else "—")
        rows.append((s["layer"], s["species"], s["size"], str(s["n"]), h, w,
                     ("×%.2f " % sc if abs(sc - 1.0) > 1e-9 else "")
                     + html.escape(str(s.get("asset", "")))
                     + (" ⚠ 目録に無い: " + "・".join(miss) if miss else ""),
                     "、".join("(%.2f, %.2f)" % (u, v) for u, v in s["at"])))
    return _tw(("層", "樹種", "寸", "本数", "樹高(部材の実測)", "樹冠幅", "部材", "位置(u,v)"), rows)


def niwa_cover_table(d):
    """**樹冠の被覆率**(庭方の検査 6-④)。⛔ 上限は庭方の追送待ち【?】— 測って刷るだけ。"""
    o = niwa_cover(d)
    if not o:
        return ""
    lim = (NI(d).g.get("coverLimits") or {})

    def _row(ttl, got, key, note):
        up = lim.get(key)
        return (ttl, "<b>%.1f%%</b>" % got,
                ("上限 %.1f%% %s" % (up, "⭕" if got <= up + 1e-9 else "<b>⚠</b>")) if up else "—",
                note)
    rows = [
        _row("陸の樹冠被覆率", o["landPct"], "landPct",
             "%.0f m² / 陸 %.0f m²" % (o["landCov"], o["landM2"])),
        _row("水面の樹冠被覆率", o["waterPct"], "waterPct",
             "%.0f m² / 水面 %.0f m²" % (o["waterCov"], o["waterM2"])),
        _row("<b>水面の中央部</b>(汀から %.1fm 以上内側)" % o["core"],
             o["waterCorePct"], "waterCorePct",
             "%.0f m² / 中央部 %.0f m²" % (o["coreCov"], o["coreM2"])),
    ]
    return _tw(("被覆", "実測", "上限(庭方)", "内訳"), rows) + (
        "<p class='cap'>⭐ 樹冠は <code>docs/asset-index.tsv</code> の実測(W と D の大きい方 ÷ 2 "
        "× <code>scale</code>・個体を混ぜるので最大を採る)で、木 %d 本(樹冠の合計 %.0f m²)を "
        "0.05間格子に落として数えた。⭐ <b>本条は「水面の中央部」</b> — <b>水の面が空を映すこと</b>が"
        "この庭の要で、旧配置はここが無検査だったため水面全体の 83.7%% が樹冠下だった。"
        "上限は庭方が「開けていなければならない面」の実測から引いた値【U】。</p>"
        % (o["n"], o["crownM2"]))


def niwa_mikoro_table(d):
    n = NI(d)
    o = niwa_stats(d)
    K = n.ken
    cr = _crowns(d)
    lim = (n.g.get("coverLimits") or {}).get("singleTreeDeg")
    rows = []
    for m in n.g["mikoro"]:
        e = n.eye(m["no"])
        # ⭐ **単木の水平占有角の実測を見所ごとに刷る**(2026-09-04 庭方 低-1)。
        #   ⛔ 判定を当てるのは**座敷から見る見所**(`sit`)だけ — 庭の中に立つ見所は
        #   木の脇に立つのだから 85〜144° になるのが当然で、45° は成り立たない。
        best = max(((2.0 * math.degrees(math.atan2(
            c["r"], math.hypot((c["u"] - m["u"]) * K, (c["v"] - m["v"]) * K))),
            "%s %s" % (c["sp"], c["sz"])) for c in cr), default=(0.0, "—"))
        if m.get("eyeMode") == "sit" and lim:
            ang = "<b>%.1f°</b> %s<br><span class='note'>%s(上限 %.0f°)</span>" % (
                best[0], "⭕" if best[0] <= lim + 1e-9 else "⚠", best[1], lim)
        else:
            ang = "%.1f°<br><span class='note'>%s(庭の中に立つ見所 — 上限を当てない)</span>" % (
                best[0], best[1])
        rows.append(("%d" % m["no"],
                     m["label"] + ("　<b>主景</b>" if m.get("main") else ""),
                     "(%.2f, %.2f)" % (m["u"], m["v"]),
                     ("%.2f" % e) if e is not None else "<b>?</b>(設計書に無い)",
                     m.get("eyeMode", ""), ang, "／".join(m.get("sees", []))))
    return _tw(("見所", "名", "位置(u,v)", "眼高", "座り方",
                "単木の水平占有角(最大)", "見るもの"), rows) + (
        "<p class='cap'>⭐ <b>単木の水平占有角は「一本で景を塞がない」の物差し</b>"
        "(⛔ 旧のクロマツ Big ×1.65 は主景から 79.6° を占めていた)。"
        "⛔ <b>上限 %s を当てるのは座敷から見る見所(<code>sit</code>)だけ</b> — "
        "床几・沢飛石の上・参道の口は<b>庭の中に立つ</b>ので、木の脇で 85〜144° になるのは当然。"
        "⭕ それでも<b>実測は刷る</b>(⛔ 測って黙らない)。</p>"
        % (("%.0f°" % lim) if lim else "—"))


def niwa_tsuki_table(d):
    o = niwa_stats(d)
    bf = d["const"]["batterFill"]
    rows = []
    for t in o["tsuki"]:
        ok = t["batter"] >= bf - 1e-9 and t["batterReal"] >= bf - 1e-9
        rows.append((t["label"], "%.2f(+%.2f)" % (t["top"], t["rise"]),
                     "1:%.3f" % t["batter"], "1:%.3f" % t["batterReal"],
                     "%+.3f" % (t["batterReal"] - bf),
                     "%.1f m" % t["d"], "%+.2f°" % t["ang"], "⭕" if ok else "⚠"))
    for t in o.get("dote", []):
        dc9 = d["const"]["doteBatterCovered"]
        okIn = (not t["covered"]) or t["batterIn"] >= dc9 - 1e-9
        okOut = t["batterOut"] >= bf - 1e-9
        rows.append(("<i>%s(土手)</i>" % t["label"], "+%.2f" % t["rise"], "—",
                     "覆われる 1:%.3f<br>覆われない 1:%.3f<br><span class='note'>"
                     "摺り付けだけ 1:%.3f</span>"
                     % (t["batterIn"], t["batterOut"], t["batterEnd"]),
                     "覆 %+.3f<br>裸 %+.3f" % (t["batterIn"] - dc9, t["batterOut"] - bf),
                     "短辺 %.2f間 × 長辺 %.2f間" % (t["w"], t["L"]),
                     "減衰軸 <code>%s</code>／摺り付け %s間／端の段 %.2fm／覆い=%s"
                     % (t["decay"], ("%.2f" % t["taperEnds"]) if t["taperEnds"] else "<b>無</b>",
                        t["endStep"],
                        t["covered"] or ((t["onDote"] + "が載るが<b>全周は覆わない</b>")
                                         if t["onDote"] else "無")),
                     "⭕" if (okIn and okOut) else "⚠"))
    return _tw(("築山", "頂(盛)", "法(公称)", "法(実測の最急)", "上限との差",
                "主視点から", "仰角", "上限 1:%.1f" % bf), rows) + (
        "<p class='cap'>⚠ <b>実測の最急は 0.01間 刻みで u・v の両軸を走査した値</b>"
        "(0.005/0.002間 と 3桁目まで一致する)。⛔ 従前の 0.05間 刻みは割線なので"
        "<b>法を緩い側へ丸めていた</b> — 上限との差が 0.01 の桁なので刻みで合否が動く"
        "(2026-09-04 検図方 低-7)。"
        "⛔ <b>法は「その一基だけ」の面で測る</b>(<code>Niwa.mound_one</code>)— 全基の max で"
        "測ると<b>隣の盛土の斜面を自分の法として拾う</b>(蔵前の土手を短辺減衰へ直した途端、"
        "築山A1/A2/C の実測がいずれも土手の 1:0.85 に化けた)。"
        "<br>⭐ <b>下の斜体2行は土手</b>で、法は <b>footprint の全周を2次元の勾配で測る</b>"
        "(⛔ 減衰軸の一本線だけを走査しない — <b>稜線の端の摺り付けも法面</b>)。"
        "上限は<b>2段</b>で見る【2026-09-04 庭方の裁定】 — "
        "①<b>裸の土手</b>(法面が露出する)は 1:%.1f【B】/ "
        "②<b>刈込の footprint が土手の footprint を覆う</b>土手は 1:%.1f【U・庭方】"
        "(根が張った法面は保つ。⛔ 台帳に直接の典拠は無い)/ "
        "③いかなる土手も<b>切土の法 1:%.1f より立てない</b>(台帳から引ける唯一の線 — "
        "盛った土が自然の土より立つことはありえない)。"
        "⛔ <b>露出する区間が少しでもあれば①で見る</b>(覆いは footprint の包含で判定)。"
        "⚠ 蔵前の土手は短辺を 0.95 → 1.15間 に広げ、刈込①の footprint を土手と同一にして"
        "②の帯へ入れた。⛔ 1:1.5 に収める案(短辺 1.69間)は御土蔵との犬走りを食うので採らない。"
        "<br>⭐ <b>稜線の両端は `taperEnds` で cos に摺り付ける</b>(端の段=0.00m)。"
        "⚠ 従前は端が垂直に切れており(蔵前 0.65m・東 0.35m)、"
        "<b>東の土手の縁は主路の点#6 が踏む 0.23m の設計外の一段</b>になっていた。"
        "⚠ <b>「摺り付けだけ」の行は稜線軸方向の勾配</b>で、庭方が「端の最急」と呼んだ値。"
        "<b>面の勾配(覆われない)より緩く出る</b> — 摺り付けの帯には横断方向の法がそのまま残るため。</p>"
        % (bf, d["const"]["doteBatterCovered"], d["const"]["batterCut"]))


def niwa_enro_table(d):
    """園路。⚠ **勾配は二通り測る** — 石段を切るかは**区間**、登れるかは**1m 窓の最急**。"""
    o = niwa_stats(d)
    g = NI(d).g
    rows = []
    for e, q in zip(g.get("enro", []), o["enro"]):
        lim = e["keri"] / e["fumi"] * 100
        wtx = "%.2f m" % q["w"]
        for sg in q.get("wSeg", []):
            wtx += "<br><span class='note'>u[%.2f, %.2f] は <b>%.2f m</b>(%s)</span>" % (
                min(sg["u0"], sg["u1"]), max(sg["u0"], sg["u1"]), sg["w"], sg.get("why", ""))
        rows.append((q["label"], wtx, "%.1f m" % q["L"],
                     "%.0f%%" % q["grade"],
                     "<b>%.0f%%</b>%s(起点+%.1fm)"
                     % (q["gradeWin"], " ⚠" if q["gradeWin"] > lim else "", q["gradeWinAt"]),
                     ("%d 段(%.1fm)" % (q["steps"], q["stepL"])) if q["steps"] else "切らない",
                     "%.2f m" % q["edgeShore"],
                     ("%.2f m" % q["edgeShachi"]) if q["edgeShachi"] < 100 else "—",
                     str(q["wet"])))
    return _tw(("園路", "幅", "全長", "区間の最急", "1m 窓の最急(限 %.0f%%)"
                % (g["enro"][0]["keri"] / g["enro"][0]["fumi"] * 100),
                "野面の石段", "路縁 → 汀", "路縁 → 社地", "水中の点"), rows)


def niwa_screen_table(d):
    """主景の見切り — 樹冠が塞ぐべき帯を覆えているか。⭐ **①-a の合否はこの表と断面で決まる。**"""
    o = niwa_stats(d)
    ku = o.get("kura")
    if not ku:
        return ""
    rows = []
    for s in o["screen"]:
        rows.append(("%s %s" % (s["sp"], s["sz"]), "(%.2f, %.2f)" % (s["u"], s["v"]),
                     "%.2f" % s["gy"],
                     "<b>%.2f 〜 %.2f m</b>" % (s["lo"], s["hi"]),
                     "%.2f 〜 %.2f m" % (s["c0"], s["h"]),
                     "<b>⭕</b>" if s["ok"] else "<b>⚠ 抜ける</b>"))
    return _tw(("木", "位置(u,v)", "地表", "塞ぐべき帯(地上)", "樹冠(地上)", "判定"), rows) + (
        "<p class='cap'>⚠ <b>この表は木ごとの参考</b>で、<b>合否はこれで決めない</b> — "
        "⛔ 「各樹が自分の位置で帯を覆うか」では<b>面の端と低い帯が抜ける</b>"
        "(それで 16% を見逃した)。合否は次の「蔵の見える面」の表で決める"
        "(2026-09-04 庭方の第3巡・決定 中9)。</p>")


def niwa_kura_table(d):
    """⭐ **主景の見切りの合否はここで決まる** — 蔵の見える面が**全長 × 全高**にわたって
    塞がるか。塞ぐ物は **地形(築山・土手を含む地表)/ 刈込の天端 / 樹冠(枝下〜樹高の円柱)**。"""
    o = niwa_stats(d)
    q = o.get("kuraFace")
    if not q:
        return ""
    rows = []
    for k in q:
        rows.append((k["name"], "v %.1f〜%.1f(%.1f間)" % (k["v0"], k["v1"], k["v1"] - k["v0"]),
                     "%.2f〜%.2f m" % (k["y0"], k["y1"]),
                     "<b>%.0f%%</b>" % k["pct"],
                     "⭕" if not k["miss"] else "⚠ 素通し %d 点(例 %s)"
                     % (len(k["miss"]), "、".join("v%.1f/標高%.2f" % p for p in k["miss"][:3]))))
    return _tw(("御土蔵", "見える面の長さ", "高さの範囲", "塞げる割合", "判定"), rows) + (
        "<p class='cap'>⭐ 面を <b>長さ120 × 高さ28 の格子</b>に刻み、主視点からの視線を1本ずつ "
        "<b>地形 → 刈込の天端 → 樹冠</b>の順に当てた実測。⛔ <b>木を足して解かない</b> — "
        "眼から見て地形の見切り線と樹冠の下端のあいだに残る 1.2〜1.8m の低い帯は"
        "<b>枝下より下なので木では塞げない</b>。そこは <code>Dote_Kuramae</code>(+0.45m)に"
        "載せた刈込①が受ける(2026-09-04 庭方の第3巡・決定 中9)。</p>")


def edge_step_qa_table(d, dem):
    """**実装の `EdgeStepQA` が鳴らす縁を、指図の側から仕分ける。**

    ⚠ 2026-09-06、棟梁が「段の境で土留めが無く落差が残る 33区間は**指図の欠落**」と
    差し戻した。⛔ **大半は指図の欠落ではない** — 同名の検査 `edge_step_check` と
    **測り方が違う**ためである。⚠⚠ いちばん効くのは **probe の距離**:
    指図は縁から **±0.06間(0.11m)**、実装は **±0.5間(0.909m)**。
    ⇒ 0.909m 離れた点では**法面が正当に落ちている**(盛 1:1.5 で 0.61m / 切 1:1.0 で 0.91m)。
    そこへ `stepAbsorbMax`(0.45 = **段の縁で摺り付けられる落差**)を当てるのは
    **単位の取り違え**で、法面が在る縁はほぼ全部鳴る。

    ⛔ **ここで壁を足さない**(設計判断)。仕分けて返すところまでが指図方の仕事。
    """
    if dem is None:
        return "<p class='cap'>⚠ <code>doi_dem.json</code> が無いので仕分けられない。</p>"
    gr = RGrid(d)
    we = {t["name"]: walled_edges(d, t) for t in d["terraces"]}
    lim = d["const"]["stepAbsorbMax"]
    K = d["const"]["ken"]
    fill = 0.5 * K / d["const"]["batterFill"]      # 0.5間 の走りで盛の法が落ちる量
    cut = 0.5 * K / d["const"]["batterCut"]        # 同・切

    def gy(u, v):
        q = design_y(d, u, v)
        if q is not None:
            return q
        wx, wz = gr.W(u, v)
        nat = dem_bilinear(dem, wx, wz)
        return None if nat is None else graded_y(d, u, v, nat, we)

    rows, tally = [], {}
    for t in d["terraces"]:
        if t.get("yaw"):
            continue                               # 回転する段は別の作法
        for e, edge in enumerate(("u0", "u1", "v0", "v1")):
            vert = e < 2
            fix = t[edge]
            sgn = -1.0 if edge in ("u0", "v0") else 1.0
            q0, q1 = (t["v0"], t["v1"]) if vert else (t["u0"], t["u1"])
            run = None
            q = q0
            while q <= q1 + 1e-6:
                ui, vi = (fix - sgn * 0.5, q) if vert else (q, fix - sgn * 0.5)
                uo, vo = (fix + sgn * 0.5, q) if vert else (q, fix + sgn * 0.5)
                yi, yo = gy(ui, vi), gy(uo, vo)
                cov = _walled(we[t["name"]], edge, q)
                hit = (yi is not None and yo is not None
                       and abs(yi - yo) > lim + 1e-4 and not cov)
                if hit:
                    # ⚠⚠ **角(端点)では内側の probe が隣の段に落ちる。**この段の縁として
                    #   鳴っていても、実際に受けるのは**隣の段の壁**である(2026-09-06 に
                    #   `MonzenE` の `u0`・q=12.0 で踏んだ — あそこは `MonzenE` の v1 端点で、
                    #   内側の probe は `MaeNiwa`(21.9)に落ち、`TW_MaeS` が既に受けていた)。
                    #   ⛔ **自分の段の壁だけを見て「受けが無い」と言わない。**
                    own = design_y(d, ui, vi)
                    other = [x for x in d["terraces"]
                             if x["name"] != t["name"] and own is not None
                             and abs(x["y"] - own) < 0.01
                             and x["u0"] - 1e-9 <= ui <= x["u1"] + 1e-9
                             and x["v0"] - 1e-9 <= vi <= x["v1"] + 1e-9]
                    held = [x["name"] for x in other
                            if _walled(we[x["name"]], edge, q)]
                    if own is not None and abs(own - t["y"]) > 0.01 and held:
                        cls = "F 角の取り違え(%s の壁が受ける)" % held[0]
                    elif own is not None and abs(own - t["y"]) > 0.01:
                        cls = "F 角の取り違え(内側が %s)" % (other[0]["name"] if other else "別の段")
                    elif design_y(d, uo, vo) is not None:
                        cls = "A 外が別の段"
                    elif not in_parcel(d, uo, vo):
                        cls = "B 区画の外"
                    elif abs(yi - yo) <= max(fill, cut) + 1e-9:
                        cls = "D 素地=法面"
                    else:
                        cls = "E 法面で説明できない"
                    if run is None:
                        run = [q, q, yi - yo, cls]
                    else:
                        run[1] = q
                        if abs(yi - yo) > abs(run[2]):
                            run[2], run[3] = yi - yo, cls
                else:
                    if run:
                        rows.append((t["name"], edge, run[0], run[1], run[2], run[3]))
                        run = None
                q += 0.5
            if run:
                rows.append((t["name"], edge, run[0], run[1], run[2], run[3]))
    for r in rows:
        tally[r[5]] = tally.get(r[5], 0) + 1
    rows.sort(key=lambda r: -abs(r[4]))
    out = [(r[0], "<code>%s</code>" % r[1], "%.1f 〜 %.1f" % (r[2], r[3]),
            "<b>%+.2f m</b>" % r[4],
            ("⚠ <b>%s</b>" % r[5]) if r[5].startswith("E") else r[5]) for r in rows]
    return _tw(("段", "縁", "走り q[間]", "最大の落差", "指図の側の扱い"), out) + (
        "<p class='cap'>⚠⚠ <b>実装の <code>EdgeStepQA</code> と指図の <code>edge_step_check</code> は"
        "測り方が違う。</b>指図は縁から <b>±0.06間(0.11m)</b>、実装は <b>±0.5間(0.909m)</b> で測る。"
        "⇒ <b>0.909m 離れた点では法面が正当に落ちている</b>(盛 1:%.1f で %.2fm / 切 1:%.1f で %.2fm)。"
        "そこへ <code>stepAbsorbMax</code>(%.2f = <b>段の縁で摺り付けられる落差</b>)を当てるのは"
        "<b>単位の取り違え</b>で、法面が在る縁はほぼ全部鳴る。</p>"
        "<p class='cap'><b>仕分け %s(計 %d 区間)。</b>"
        "<b>A 外が別の段</b>=<code>adjacency_check</code> の担当(指図の網の中・⛔ 二重に鳴っている)/ "
        "<b>B 区画の外</b>=隣家・道で <code>runs</code> の基壇石垣か隣家の塀が受ける"
        "(<code>edge_step_check</code> は <code>in_parcel</code> で外している)/ "
        "<b>D 素地=法面</b>=<b>指図が法面と定めた縁</b>・設計どおり / "
        "<b>F 角の取り違え</b>=<b>段の端点で内側の probe が隣の段に落ちている</b> — "
        "受けるのは<b>隣の段の壁</b>で、⛔ 自分の段の壁だけを見て「受けが無い」と言わない / "
        "<b>E 法面で説明できない</b>=<b>ここだけが実質の検討</b>。"
        "⛔ <b>壁はまだ足さない</b>(設計判断)。⇒ 実装側は ①区画の外を除く ②外が別の段を除く "
        "③probe を縁ぎわに寄せるか法面の許容(走り × 勾配)と比べる "
        "④<b>角では隣の段の壁も見る</b>、の4つを直すこと。</p>"
        % (1.0 / d["const"]["batterFill"] * 1.0, fill, 1.0 / d["const"]["batterCut"] * 1.0, cut,
           lim,
           " / ".join("%s %d" % (k, v) for k, v in sorted(tally.items())), len(rows)))


def niwa_impl_table(d):
    """**実装の申し合わせ**(`gardens[].impl`)を図に出す。

    ⚠⚠ 2026-09-06 まで `impl` の5項は**どこにも描かれていなかった** — ⛔ `WaterBaker.Create`
    を使わない / ⛔ `Recarve` しない / ⛔ 据え位置を発明しない / Stage の順序 / 格子の3条 が
    **正典にだけ在って、指図の文書には一行も出ていなかった**。
    ⇒ 棟梁が `WaterBaker.Create` で掘った(第1回)のも、`shitakusa` を言葉のまま読んだのも、
    **読める所に無かったから**である。⛔ 実装への指示こそ図に出す(規則19)。
    """
    n = NI(d)
    if n is None:
        return ""
    im = n.g.get("impl") or {}
    if not im:
        return ""
    JA = {"waterBaker": "池を掘る手",
          "noRecarve": "⛔ `Recarve` / `RestoreTerrain` を実行しない",
          "terrainGrid": "地形の格子と池の深さ",
          "noInvent": "⛔ 据え位置を実装で発明しない",
          "stage": "Stage と順序",
          # ⭐ 2026-09-06: 街路・門外の地盤をどちらの正本から読むか(棟梁の第4回の差し戻し)。
          #   ⛔ 生の鍵名を出さない — 何の申し合わせか一行で読めるようにする(規則16)。
          "demSource": "⚠ 街路・門外の地盤は現地形 `doi_dem.json` から読む"}
    ORDER = ["stage", "waterBaker", "terrainGrid", "noRecarve", "noInvent", "demSource"]
    rows = [(JA.get(k, k) + "<br><code>%s</code>" % k, im[k])
            for k in ORDER if k in im]
    rows += [(JA.get(k, k) + "<br><code>%s</code>" % k, im[k])
             for k in im if k not in ORDER]
    # ⭐ **実装の報告値(`mizu.jissoku`)も同じ節に出す。**⚠ 2026-09-06 まで欄は在るのに
    #   どこにも描かれていなかった(規則19: 測った値は成果物に載せる)。
    jt = ""
    jj = ((n.g.get("mizu") or {}).get("jissoku") or {})
    if jj:
        mg = n.g["migiwa"]
        jr = [("地形のセル", "%.2f m" % jj.get("cellM", 0.0), "—"),
              ("池の深さ", "<b>設計 %.2f m</b>(<code>migiwa.depthMax</code>)"
               % mg["depthMax"], "格子上 <b>%.2f m</b>" % jj.get("depthMaxGrid", 0.0)),
              ("汀の内側で水面より上に残ったセル", "設計 0%", "<b>%.1f%%</b>"
               % jj.get("aboveWaterPct", 0.0))]
        for k9, l9 in (("minakuchiCells", "水口"), ("sawatobiCells", "沢飛石")):
            if jj.get(k9):
                jr.append(("%s(水面より上に残ったセル)" % l9, "設計 0", "<b>%s</b>" % jj[k9]))
        jt = ("<h3>格子の上でどう掘れたか — 実装の報告値【%s】</h3>" % jj.get("cert", "?")
              + _tw(("項", "設計", "格子上の実測"), jr)
              + "<p class='cap'>⛔ <b>これは設計値ではない</b> — 設計は "
                "<code>migiwa.waterY</code> / <code>depthMax</code> が正典で、"
                "ここは<b>そこからどれだけ離れたか</b>の記録(実測 %s)。"
                "⭐ <b>格子上の最深は、設計の椀の最深点を「最寄りのセル中心」で標本した値</b>。"
                "⛔ <b>設計が浅くなったのではない</b>(<code>depthMax</code> は %.2f のまま)。"
                "⚠ 第2回の 0.93 より<b>小さい</b>のは、<b>平床をやめて椀形を焼いたぶん"
                "最深点が一点に絞られた</b>ため — ⛔ <b>悪くなったと読まない</b>。"
                "⚠ 値は棟梁が据え直すたびに更新する。</p>"
              % (jj.get("at", "—"), mg["depthMax"]))
    return _tw(("申し合わせ", "中身"), rows) + jt + (
        "<p class='cap'>⭐ <b>これは棟梁への指示であって、意匠でも寸法でもない。</b>"
        "⚠ 2026-09-06 まで<b>この5項はどこにも描かれていなかった</b> — "
        "正典にだけ在って、指図の文書には一行も出ていなかった。"
        "⛔ <b>実装への指示こそ図に出す</b>(規則19)— 読める所に無ければ、"
        "実装は自分の判断で埋めるほかない。</p>")


def niwa_tenkei_table(d):
    """**点景(灯籠・沓脱石・稲荷の祠と鳥居と手水石)の据え位置・部材・据え向き。**

    ⚠ 2026-09-06 まで、これらの `_`(据え向き・張り出し・部材の実寸)は
    **どの表にも図にも出ていなかった** — 庭園図に名札が出るだけで、
    「長辺を参道の軸と平行に据える」「水面上へ 0.25m 出る」は誰の目にも入らなかった
    (規則19: 設計値を入れたら同じ巡でそれを描く図を出す)。
    """
    n = NI(d)
    if n is None:
        return ""
    g = n.g
    rows = []
    for t in g.get("toro", []):
        rows.append((t["label"], "(%.2f, %.2f)" % (t["u"], t["v"]),
                     "<code>%s</code>" % t.get("asset", "—"),
                     "%s型" % t.get("kata", "?"), t.get("cert", "?")))
    for k in g.get("kutsunugi", []):
        rows.append(("沓脱石", "(%.2f, %.2f)" % (k["u"], k["v"]), "—",
                     "%.2f × %.2f m・天端 %.2f" % (k["L"], k["W"], k["topY"])
                     if k.get("topY") is not None else "%.2f × %.2f m" % (k["L"], k["W"]),
                     k.get("cert", "?")))
    y = g.get("yashiro") or {}
    for key, lab in (("hokora", "稲荷の祠"), ("torii", "鳥居"), ("chozu", "手水石")):
        o = y.get(key)
        if not isinstance(o, dict):
            continue
        pos = ("(%.2f, %.2f)" % (o["u"], o["v"])) if "u" in o else \
              ("u[%.2f, %.2f] v[%.2f, %.2f]" % (o["u0"], o["u1"], o["v0"], o["v1"]))
        det = o.get("align") or o.get("kata") or ""
        if o.get("front"):
            det = ("正面 %s" % o["front"]) + ("・" + det if det else "")
        if key == "chozu":
            det = "%.2f × %.2f m ／ <b>%s</b>" % (o["L"], o["W"], o.get("align", "⚠ 据え向きが無い"))
        rows.append((lab, pos, "<code>%s</code>" % o.get("asset", "— (小物で合成)"),
                     det, y.get("cert", "?")))
    return _tw(("点景", "位置(u,v)", "部材", "据え向き・寸", "確度"), rows) + (
        "<p class='cap'>⭐ <b>据え向きは寸法と同じ設計値</b> — 手水石は"
        "<b>長辺を参道の軸(v=65.75 に沿う u 方向)と平行</b>に据える。"
        "⚠ 直交させると路縁までの空きが +0.018m しか残らず参道へ実質はみ出す"
        "(平行なら +0.128m)【庭方の実測=P】。⛔ 手水石も参道も動かさない — <b>向きだけで解く</b>。"
        "⭕ <b>雪見灯籠は据え位置の芯が陸</b>(汀の陸側 0.20m)で、"
        "笠と前脚が<b>水面上へ 0.25m</b> 張り出すのは意図"
        "(部材の奥行 0.906 ÷ 2 − 0.20)。⛔ <b>灯籠は動かさない</b>。"
        "⛔ <b>雪見は素で置かない</b> — edogoyomi なので <code>ES</code> = 1.818 を掛ける。"
        "⛔ 春日型は社前に1基だけ・参道の上に置かない・主庭へ持ち出さない。</p>")


def niwa_karikomi_table(d):
    """刈込 — **水没率**と路縁までの離れ。⛔ 汀に沿うものを矩形で持たない。"""
    st = karikomi_stats(d)
    if not st:
        return ""
    rows = []
    for q in st:
        k = q["k"]
        rows.append((k["label"], k.get("kata", "矩形"),
                     ("汀 #%d→#%d ／ 陸側 %.2f〜%.2f間%s"
                      % (k["frm"], k["to"], k["off0"], k["off1"],
                         "(v %.2f〜%.2f に切る)" % tuple(k["vClip"]) if k.get("vClip") else ""))
                     if k.get("kata") == "帯" else
                     "u[%.2f, %.2f] v[%.2f, %.2f]" % (k["u0"], k["u1"], k["v0"], k["v1"]),
                     "%.2f〜%.2f m" % (k["hMin"], k["hMax"]),
                     "<b>%.1f%%</b>" % q["wet"],
                     "%+.2f m" % q["edge"],
                     "⭕" if (q["wet"] <= 1e-9 and q["edge"] >= 0) else "⚠"))
    return _tw(("刈込", "形", "定義", "高さ", "水没", "路縁まで", "判定"), rows) + (
        "<p class='cap'>⛔ <b>汀に沿うものを矩形で持たない</b> — 旧は5枚中3枚が水没(最大 81.9%)し、"
        "1枚が主路を塞いでいた。⭕ 帯は「<b>汀線の区間 + 陸側オフセット</b>」で持ち、"
        "外向きは<b>各辺の法線のうち池に入らない側</b>で決める(⛔ 池心からの方向で代用しない — "
        "非凸の池で内側を向く)。⭐ ②を #18–#1 の一部に絞ったのは、#1 まで通すと"
        "<b>飛石の着地点と主路に掛かる</b>ため — <b>飛石が汀に降りる所は開けておく</b>。</p>")


def _se(uk, j):
    """受け石の `scaleEach[j]`。⚠ **null は「まだ決まっていない」** — ⛔ 1.0 で埋めない。"""
    q = (uk.get("scaleEach") or [uk.get("scale")] * 9)
    return q[j] if j < len(q) else None


def _uk_gap(uk, j):
    """受け石 j から**最寄りの受け石までの芯々距離**[m](平面の当たり)。

    ⭐ 2026-09-06 庭方 低3。⚠ 根入れを**石丈**で稼ぐ以上、⛔ **石を大きくすると平面で隣に触る** —
    高さだけ見て通すと据えたときに石が重なる。⇒ 芯々を刷り、⚠ **石丈が入るまでは
    「当たりは未判定」**と断る(⛔ 黙って合格にしない=規則19)。
    """
    at = uk.get("at") or []
    if j >= len(at) or len(at) < 2:
        return None
    def _xy(q):
        a = math.radians(q[0])
        return (q[1] * math.sin(a), q[1] * math.cos(a))
    x0, y0 = _xy(at[j])
    best = None
    for k, q in enumerate(at):
        if k == j:
            continue
        x1, y1 = _xy(q)
        dd = math.hypot(x1 - x0, y1 - y0)
        best = dd if best is None or dd < best else best
    return best


def _uk_bury(uk, gs, base, low, j):
    """受け石の**根入れ**の一行。⛔ **掘り下げでは根入れは増えない**(天端が絶対高・石は剛体)
    ので、満たすのは**石丈** — `石丈 ≥ (1 + buryMin) × 露出`(2026-09-06 棟梁の第4回)。
    ⚠ `takeEach` は**目録から引けない**(`Own.Tateishi` は長軸を 1.0 に正規化しており、
    伏せた向きの丈は別物)ので、無いうちは **⚠ 未測**と出す。⛔ 黙って合格にしない。"""
    if gs[j] is None:
        return ""
    top = base + (uk.get("capHigh", 0.0) if j == low else 0.0)
    expo0 = top - gs[j]
    need = (1.0 + uk.get("buryMin", 0.0)) * expo0
    tk = (uk.get("takeEach") or [None] * 9)[j] if uk.get("takeEach") else None
    gap = _uk_gap(uk, j)
    # ⭐ **平面の当たりも同じ行に出す**(2026-09-06 庭方 低3)。石丈で稼ぐ以上、
    #   ⛔ 大きくした石が隣に触らないかは**高さと同じ巡で**見る。
    gt = ("" if gap is None else
          ("・最寄りの受け石まで<b>芯々 %.3fm</b>%s"
           % (gap, "(⚠ <b>当たりは未判定</b> — 石丈が入ってから長軸の振りで見る)"
              if tk is None else "")))
    if tk is None:
        return ("・露出 %.3f ⇒ <b>要る石丈 %.3f</b> 以上(⚠ <b>石丈が未測</b>・"
                "<code>_pending.uke2</code>)" % (expo0, need)) + gt
    return ("・露出 %.3f / 石丈 %.3f(要 %.3f)%s"
            % (expo0, tk, need, " ⭕" if tk >= need - 1e-9 else " ⚠")) + gt


def niwa_toi_table(d):
    """埋樋の土被り。⚠ 樋が地表より上に出ていたら埋樋ではない。"""
    n = NI(d)
    o = niwa_stats(d)
    ter = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
    rows = []
    for (u, v, y) in o["toi"]:
        q = terr_at(ter, u, v)
        rows.append(("(%.2f, %.2f)" % (u, v), "%.2f" % y,
                     ("%.2f" % q) if q is not None else "—",
                     ("<b>%+.2f m</b>%s" % (q - y, "" if q - y >= 0.30 else " ⚠"))
                     if q is not None else "—"))
    # ⭐ **水尻の末端(受け石)も刷る。**⚠ 2026-09-06 まで `uke` は「玉石の浸透枡(受け石)」の
    #   **一語**で、数も広がりも無く、**棟梁が第2回で発明するほかなかった**(3個・0.45m)。
    #   その値を正典へ引き取ったので、⛔ 表に出さないまま持たない(規則19)。
    ms = ((n.g.get("mizu") or {}).get("mizushiri") or {})
    uk = (ms.get("otoshimizo") or {}).get("uke")
    tail = ""
    if isinstance(uk, dict):
        to9 = (ms.get("otoshimizo") or {}).get("to", [0.0, 0.0])
        # ⭐ **どれが「下流側の1個」かは幾何で決まる** — 落とし溝の流れ(吐き口 → 終点)への
        #   射影が最大の石。⛔ 指図に番号を書かない(石を動かせば入れ替わる)。
        fx = to9[0] - (ms.get("umeToi") or {}).get("pts", [[0, 0]])[-1][0]
        fz = to9[1] - (ms.get("umeToi") or {}).get("pts", [[0, 0]])[-1][1]
        fl = math.hypot(fx, fz) or 1.0
        pos = []
        for j, (deg, r9) in enumerate(uk.get("at", [])):
            du = math.cos(math.radians(deg)) * r9 / d["const"]["ken"]
            dv = math.sin(math.radians(deg)) * r9 / d["const"]["ken"]
            pos.append((j, deg, r9, (du * fx + dv * fz) / fl))
        low = max(pos, key=lambda q: q[3])[0] if pos else -1
        # ⭐ **天端は絶対高で出す**(2026-09-06 普請検査の再測)。⚠ 地盤基準だと、
        #   下流側の地盤が低いぶん「+0.05 高く」しても**絶対高では最低**になり枡が抜ける。
        ter9 = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
        gs = []
        for (j, deg, r9, _p) in pos:
            uu = to9[0] + math.cos(math.radians(deg)) * r9 / d["const"]["ken"]
            vv = to9[1] + math.sin(math.radians(deg)) * r9 / d["const"]["ken"]
            gs.append(terr_at(ter9, uu, vv) if ter9 else None)
        okg = [q for q in gs if q is not None]
        base = (max(okg) + uk.get("capBase", 0.0)) if okg else None
        caps = ""
        if base is not None:
            caps = ("<br>基準天端 = <b>3点の地盤の最高点 %.3f + %.2f = %.3f</b> ／ "
                    % (max(okg), uk.get("capBase", 0.0), base)
                    + " ・ ".join(
                        "#%d(地盤 %.3f)→ 天端 <b>%.3f</b> ／ %s%s"
                        % (j + 1, gs[j] if gs[j] is not None else float("nan"),
                           base + (uk.get("capHigh", 0.0) if j == low else 0.0),
                           # ⚠ `scale` が未定(⛔ 目録に `Tateishi` が無い)なら数字を捏造しない
                           ("×<b>%.2f</b>" % _se(uk, j)) if _se(uk, j) is not None
                           else "×<b>⚠ 未定</b>",
                           ("(<b>下流・止め</b>)" if j == low else "(±%.2f のジッタ)"
                            % uk.get("capJitter", 0.0))
                           + (" <code>%s</code>" % (uk.get("assetEach") or ["—"] * 9)[j]
                              if uk.get("assetEach") else "")
                           + (" ・<b>%s</b>" % uk["axis"] if j == low and uk.get("axis") else "")
                           + _uk_bury(uk, gs, base, low, j))
                        for (j, deg, r9, _p) in pos))
        tail = ("<p class='cap'>⭕ <b>落とし溝の末端 — %s</b>: <b>%d 個</b>を終点 (%.2f, %.2f) の"
                "まわりへ、<code>%s</code> を <b>90° 倒して</b>据え(大きさ %s)、"
                "<b>芯を地盤の高さに沈める</b>(半分埋め)。"
                "⛔ <b>等配・等半径にしない</b> — 方位と半径は %s の<b>不等辺三角</b>。"
                "⭕ 天端も揃えず出入り <b>±%.2fm</b>、うち<b>下流側の1個(%d番)だけ +%.2fm 高く</b>して"
                "水を止める(全部同高だと水が抜けて枡にならない)。"
                "⛔ <b>1種で並べない</b>(variant を3種混ぜ、yaw は乱数)。"
                "⛔ <b>「石は立てる」の条はここに当てない</b> — 受け石は<b>伏せる</b>のが役目。"
                "⛔ <b>隣家へ流し込まない</b>【数・広がり・高さの出入りとも U】。</p>"
                % (uk.get("kata", "受け石"), uk["n"], to9[0], to9[1],
                   # ⚠ **石ごとに別の部材・別の大きさなら、代表値を書き出しに出さない**
                   #   (2026-09-06 庭方 低1)。⛔ `asset`/`scale` を裸で刷ると
                   #   「3個とも S・0.55」に読めるが、正典は `assetEach`/`scaleEach`。
                   ("<b>石ごとに別</b>(内訳は下)" if uk.get("assetEach")
                    else uk.get("asset", "—")),
                   ("<b>石ごとに別</b>" if uk.get("scaleEach")
                    else "×%.2f" % uk.get("scale", 1.0)),
                   " / ".join("%.0f°･%.2fm" % (q[1], q[2]) for q in pos),
                   uk.get("capJitter", 0.0), low + 1, uk.get("capHigh", 0.0))
                + ("<p class='cap'>⭐ <b>天端は絶対高で指定する</b>(%s)。%s"
                   "<br>⚠ 従前は<b>地盤基準</b>だったので、<b>下流側の地盤が低いぶん"
                   "「+%.2f 高く」しても絶対高では3個中いちばん低くなり、枡が下流へ抜けていた</b>"
                   "(2026-09-06 普請検査の再測)。⛔ <b>地盤からの相対で据えない</b> — "
                   "沈め方(90° 倒して芯を地盤へ)は同じだが、"
                   "<b>天端がこの値になるよう沈み代を調節する</b>。"
                   "<br>⭐ <b>石の大きさを揃えない</b> — <b>当たりを受ける下流の石をいちばん大きくする</b>"
                   "のが作庭の作法【U・庭方】(水が最後に当たる石が小さいと、そこから崩れる)。"
                   "⭐ <b>根入れは見付高の %s 以上</b> — ⛔ <b>景石の 1/3 より深い</b>"
                   "(景石は立てて見せる石だが、<b>受け石は据わりが要る</b>)。"
                   "⛔⛔ <b>下流の石の天端を下げて根入れを稼がない</b>(枡が抜ける)。"
                   "⛔⛔ <b>床を掘って稼ぐ手も使えない</b> — 天端が絶対高で石は剛体なので、"
                   "掘っても<b>見付が増えるだけ</b>で埋まりは <b>石丈 − 露出</b> のまま"
                   "(2026-09-06 棟梁の第4回で撤回した)。"
                   "⇒ ⭕ <b>満たすのは石丈</b>: <b>石丈 ≥ (1 + %s) × 露出</b>。"
                   "⭕ <b>露出は元の地盤から測る</b>(⛔ 造作後の地盤で評価しない)。"
                   "⚠ <b>石丈は目録から引けない</b> — <code>Own.Tateishi</code> は長軸を 1.0 に"
                   "正規化しており、伏せたときに鉛直になる軸の実寸は別物(<code>_pending.uke2</code>)。"
                   "⛔ <b>無いのに「合格」と数えない</b> — 石ごとの行に ⚠ 未測と出す。"
                   "⭕ <code>nekatame</code>(栗石)は<b>据わりの手当て</b>として残る — "
                   "根入れの話ではない。</p>"
                   % (uk.get("capMode", "—"), caps, uk.get("capHigh", 0.0),
                      ("%g/%g" % (uk["buryMin"] * 2, 2) if uk.get("buryMin") == 0.5
                       else str(uk.get("buryMin", "—"))),
                      ("%g/%g" % (uk["buryMin"] * 2, 2) if uk.get("buryMin") == 0.5
                       else str(uk.get("buryMin", "—"))))
                   if base is not None else ""))
    elif uk is not None:
        tail = ("<p class='cap'>⚠ <b>受け石が語だけで、数も広がりも無い</b> — "
                "このままでは実装が発明する(<code>mizushiri.otoshimizo.uke</code>)。</p>")
    return _tw(("折れ点(u,v)", "樋の底", "復元地盤(P)", "土被り(下限 0.30m)"), rows) + tail


def akichi_table(d):
    rows, tot, rest = akichi_stats(d)
    a1 = 0.25 * d["const"]["ken"] ** 2 / TSUBO
    out = []
    for a in rows:
        out.append((a["label"], "u[%.1f, %.1f] v[%.1f, %.1f]" % (a["u0"], a["u1"], a["v0"], a["v1"]),
                    "%.1f 坪" % a["tsubo"], a["cert"]))
    out.append(("<b>枠の外に残る空白</b>", "u[%.1f, %.1f] v[%.1f, %.1f]"
                % (min(p[0] for p in rest), max(p[0] for p in rest),
                   min(p[1] for p in rest), max(p[1] for p in rest)) if rest else "—",
                "<b>%.1f 坪</b>" % (len(rest) * a1), "?"))
    out.append(("<b>主面の無名の空白(合計)</b>", "—", "<b>%.1f 坪</b>" % tot, "P(実測)"))
    return _tw(("明地の枠", "範囲", "坪数(0.5間格子の実測)", "確度"), out)


# ---------------------------------------------------------------- 組み立て
_PLATES = {}


def plate(h, num, title, meta=""):
    # ⚠ **章の番号を他所へ写さない。** 章を1つ挿すと以降が全部ずれる
    #   (2026-08-25: 復元地盤の図を其三に入れて 13 箇所がずれた)。
    #   参照は `KANOF("題の一部")` で引く。
    _PLATES[title] = num
    h.append('<div class="plate"><div class="phead"><h2>%s　%s</h2>%s</div>'
             % (num, title, ('<span class="meta">%s</span>' % meta) if meta else ""))


def KANOF(sub):
    """章の題の一部から「其N」を引く。

    ⚠ **その場では引かない。** 章は本文より**後で**登録されるので、その場で引くと
    まだ登録されていない章が全部フォールバックになる(2026-08-25 考証13巡の下ごしらえで
    「表門まわり」が既にそうなっていた)。**印を置いて最後にまとめて解決する。**
    """
    return "@@KAN:%s@@" % sub


def resolve_kan(html):
    """全章を登録し終えてから `@@KAN:…@@` を解決する。引けないものは⚠つきで残す
    (黙って番号を捏造しない)。"""
    def rep(m):
        sub = m.group(1)
        for t, n in _PLATES.items():
            if sub in t:
                return n
        return "⚠「%s」の章(未登録)" % sub
    return re.sub(r"@@KAN:([^@]+)@@", rep, html)


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
    "terraceWalls": ("drop", "s", "tiers", "sode", "_sodeRoom", "gapHalf", "_pitch",
                     "_exposure", "_endLow"),
    # `drop` は 2026-08-25 から**結ぶ二つの面から算出**する(検図14巡 中-3)。
    # 手で書いた落差が正典に残っていたら往復試験が拾う。
    "kaidans": ("steps", "run", "keriActual", "drop"),
    "links": ("keriActual",),
    "runs": ("s", "expose", "tiers"),
    "sections": ("natural",),
}

# ⚠ **回転物だけ** 外接矩形が派生値。回転していない物にとって `u0..v1` は**入力**なので、
#   一律に消すと生成器が地盤を引けなくなる(2026-08-25 に踏んだ)。条件つきで消す。
# ⚠ 述語は `obb_pts`/`in_obb` と**同じ**「`yaw` を持つか」にする。
#   `abs(yaw) > 1e-9` にしていたため、**yaw があって 0 の物**は描画側が `uc,vc,L,D` を
#   正典として扱うのに AABB を誰も直さない、という帯ができていた(2026-08-25 検図12巡 中-4)。
GEN_FIELDS_IF = {
    "terraces": (lambda o: "yaw" in o, ("u0", "u1", "v0", "v1")),
    "munes": (lambda o: "yaw" in o, ("u0", "u1", "v0", "v1")),
    "service": (lambda o: "yaw" in o, ("u0", "u1", "v0", "v1")),
}

# ⭐ **入れ子の算出欄**(2026-09-04 検図方 中-3)。`gardens[].migiwa.bedY` のように
#   一段深い所にある従属値は、`GEN_FIELDS`(直下の欄しか剥がさない)では往復試験に
#   掛からない。⛔ 「生成器が上書きするから腐らない」で済ませない — 往復で突き合わせる。
GEN_FIELDS_NEST = {
    "gardens": {"migiwa": ("bedY",)},
    # ⭐ **身舎の帯**(2026-09-06 ユーザー裁定=案C)。⛔ 帯数・帯の身舎・棟高・谷の位置は
    #   すべて `const.moyaBand` と足形からの従属値。手で書いた値が残っていたら往復試験が拾う。
    "munes": {"roof": ("bands", "tani")},
}


def pipeline(x):
    """算出値を正典へ書き戻す一連のパス。**ここが唯一の定義**。

    ⚠ 感度試験の台本が**自前の写し**を持っていたため、生成器に `fix_wall_exposure` を
    足したときに往復試験の台本だけが古いまま「素の状態で28件」を出した
    (2026-08-25 検図14巡)。**同じ手順を二箇所に書かない** — 台本はこれを import する。
    """
    x = fix_obb_aabb(x)
    x = fix_bands(x)                # 身舎の帯(帯数・帯の身舎・棟高・谷)
    x = fix_gardens(x)              # 庭の従属値(池床)
    x = fix_kaidans(x)
    x = fix_walls(x, load_terrain(os.path.join(DOC, "doi_edo_dem.json")))
    x = snap_openings(x)            # 開口の縁を石垣のピッチ格子へ・芯は通る物から
    x = fix_sode(x)                 # 開口の両端の袖石垣
    x = fix_edge_profile(x, load_terrain(os.path.join(DOC, "doi_dem.json")))  # 辺の地盤線
    x = fix_run_s(x, load_terrain(os.path.join(DOC, "doi_dem.json")))  # 外周の基壇の丁場
    x = fix_sections(x, load_terrain(os.path.join(DOC, "doi_edo_dem.json")),
                     load_terrain(os.path.join(DOC, "doi_dem.json")))  # 断面の現地形線
    x = fix_boundary_plinth(x, load_terrain(os.path.join(DOC, "doi_dem.json")))
    # ⚠ 露出の分布は**開口が確定した後**に測る(gapHalf が同じパスで決まるため)
    x = fix_wall_exposure(x, load_terrain(os.path.join(DOC, "doi_edo_dem.json")))
    return x


def _numnorm(q):
    """比較のために **int と float を同じ物に揃える**(入れ子も辿る)。

    ⚠ 書き戻しの `dump` は平坦な数値配列を `%g` で刷るので、`58.0` は `58` として
    読み直される。⛔ 型の違いだけで往復試験が鳴る状態にしない。
    """
    if isinstance(q, bool):
        return q
    if isinstance(q, (int, float)):
        return round(float(q), 6)
    if isinstance(q, list):
        return [_numnorm(x) for x in q]
    if isinstance(q, dict):
        return dict((k, _numnorm(v)) for k, v in q.items())
    return q


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
    for coll, (pred, keys) in GEN_FIELDS_IF.items():
        for o in stripped.get(coll, []):
            if pred(o):
                for k in keys:
                    o.pop(k, None)
    for coll, sub in GEN_FIELDS_NEST.items():
        for o in stripped.get(coll, []):
            for sk, keys in sub.items():
                if isinstance(o.get(sk), dict):
                    for k in keys:
                        o[sk].pop(k, None)
    stripped.pop("boundaryPlinth", None)
    if "edgeProfile" in stripped:                      # 値だけ消し、辺の別は残す(入力)
        stripped["edgeProfile"] = dict((k, []) for k in stripped["edgeProfile"])
    rebuilt = pipeline(stripped)
    bad = []
    # ⚠ **剥がすだけで突き合わせていない欄があった。** `boundaryPlinth` と `edgeProfile` は
    #   丸ごと剥がしていたのに、比較は `GEN_FIELDS` の欄しか回っておらず**片道**だった
    #   (2026-08-26 岡部 EDO-0026 の警告「地盤から引いた派生値を静的に持つな」を当家に当てて発覚。
    #   当家の値は毎回取り直されていて腐ってはいなかったが、生成器が将来「無ければ埋める」形に
    #   変われば**黙って静的化する**)。**剥がした物は必ず突き合わせる。**
    ra, rb = raw.get("boundaryPlinth", []), rebuilt.get("boundaryPlinth", [])
    if len(ra) != len(rb):
        bad.append("boundaryPlinth の本数が組み直しで %d → %d に変わる" % (len(ra), len(rb)))
    else:
        for i, (a0, b0) in enumerate(zip(ra, rb)):
            for k in ("edge", "s0", "s1", "coping", "drop", "s", "tiers"):
                if k in a0 and abs(float(a0[k]) - float(b0.get(k, -9e9))) > 1e-6:
                    bad.append("boundaryPlinth[%d].%s 正典=%s 組み直し=%s"
                               % (i, k, a0[k], b0.get(k)))
    ea, eb = raw.get("edgeProfile") or {}, rebuilt.get("edgeProfile") or {}
    for k in ea:
        if k not in eb:
            bad.append("edgeProfile[%s] が組み直しで消える" % k)
            continue
        if len(ea[k]) != len(eb[k]):
            bad.append("edgeProfile[%s] の点数が %d → %d" % (k, len(ea[k]), len(eb[k])))
            continue
        w = max((abs(p0[1] - q0[1]) for p0, q0 in zip(ea[k], eb[k])), default=0.0)
        if w > 1e-6:
            bad.append("edgeProfile[%s] が組み直しと最大 %.3fm 違う" % (k, w))
    for coll, sub in GEN_FIELDS_NEST.items():
        by9 = dict((o["name"], o) for o in rebuilt.get(coll, []))
        for o in raw.get(coll, []):
            r9 = by9.get(o["name"])
            for sk, keys in sub.items():
                if not isinstance(o.get(sk), dict):
                    continue
                if r9 is None or not isinstance(r9.get(sk), dict):
                    bad.append("%s %s.%s が組み直しで消える" % (coll, o["name"], sk))
                    continue
                for k in keys:
                    a9, b9 = o[sk].get(k), r9[sk].get(k)
                    # ⭐ **数でない欄も突き合わせる**(2026-09-06)。⚠ 従前は `float()` 一本で、
                    #   `bands` / `tani` のような**入れ子の辞書**を持たせた瞬間に例外か
                    #   偽の不一致になった。⛔ 数だけを比べる前提を残さない。
                    if isinstance(a9, (int, float)) and isinstance(b9, (int, float)) \
                            and not isinstance(a9, bool) and not isinstance(b9, bool):
                        if abs(float(a9) - float(b9)) > 1e-6:
                            bad.append("%s %s.%s.%s 正典=%s 組み直し=%s"
                                       % (coll, o["name"], sk, k, a9, b9))
                    elif json.dumps(_numnorm(a9), sort_keys=True, ensure_ascii=False) != \
                            json.dumps(_numnorm(b9), sort_keys=True, ensure_ascii=False):
                        bad.append("%s %s.%s.%s 正典=%s 組み直し=%s"
                                   % (coll, o["name"], sk, k,
                                      json.dumps(a9, ensure_ascii=False)[:80],
                                      json.dumps(b9, ensure_ascii=False)[:80]))
    checks = list(GEN_FIELDS.items()) + [(c, k) for c, (p, k) in GEN_FIELDS_IF.items()]
    for coll, keys in checks:
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
    else:
        for qa, qb in zip(raw.get("boundaryPlinth", []), rebuilt.get("boundaryPlinth", [])):
            for k in ("edge", "s0", "s1", "coping", "drop", "s"):
                if abs(float(qa.get(k, 0)) - float(qb.get(k, 0))) > 1e-6:
                    bad.append("boundaryPlinth 辺%s.%s 正典=%s 組み直し=%s"
                               % (qa.get("edge"), k, qa.get(k), qb.get(k)))
    pa_, pb_ = raw.get("edgeProfile") or {}, rebuilt.get("edgeProfile") or {}
    if set(pa_) != set(pb_):
        bad.append("edgeProfile の辺の集合が組み直しと違う")
    else:
        for k in sorted(pa_):
            if len(pa_[k]) != len(pb_[k]) or any(
                    abs(float(x[0]) - float(y[0])) > 1e-6 or abs(float(x[1]) - float(y[1])) > 1e-6
                    for x, y in zip(pa_[k], pb_[k])):
                bad.append("edgeProfile 辺%s が組み直しと一致しない(辺の地盤線は正本から生成する)" % k)
    return bad


def main():
    _raw = json.load(open(JSON, encoding="utf-8"))

    rtbad = roundtrip_check(_raw, pipeline)
    d = pipeline(json.load(open(JSON, encoding="utf-8")))
    write_back(d)
    print("── 往復試験の不一致: %s"
          % ("**0 件**" if not rtbad else
             "⚠ %d 件 — **正典に生成器が再現できない値が残っている**" % len(rtbad)))
    for b in rtbad:
        print("   ", b)                           # 算出した値は**正典へ戻す**(図だけが新しい状態を作らない)
    raw = open(MD, encoding="utf-8").read()
    blk, miss = sources_block(raw)
    _ka = d["kaidans"]
    _axis = [k for k in _ka if abs(k.get("gapU", 9e9)) < 2.0 and k["atWall"] in
             ("TW_Monzen", "TW_GenkanE")]
    raw = raw.replace("{{郭の数}}", str(len([p for p in d.get("planes", []) if p.get("bench")])))
    raw = raw.replace("{{棟数}}", str(len(d["munes"])))
    raw = raw.replace("{{家中長屋の棟数}}", str(len([x for x in d["service"] if x["name"].startswith("Kachu")])))
    raw = raw.replace("{{土蔵数}}", str(len([x for x in d["service"] if x["name"].startswith("Kura")])))
    raw = raw.replace("{{記事数}}", str(d.get("jishinArticles", 8)))
    raw = raw.replace("{{石段の数}}", str(len(_ka)))
    # 章の参照は題から引く(番号を写さない)
    raw = raw.replace("{{在るべき役割の章}}", KANOF("在るべき役割"))
    raw = raw.replace("{{門の軸の石段}}", str(len(_axis)))
    raw = raw.replace("{{石段の一覧}}", " / ".join(
        "`%s`(落差%.1fm・%d段)" % (k["name"], k["drop"], k["steps"]) for k in _ka)
        + " / 斜路 " + " / ".join("`%s`(落差%.1fm・1:%.1f)" % (r["name"], r["drop"], 1.0 / r["grade"])
                                  for r in d.get("ramps", [])))
    for _k, _v in (("{{記録数}}", "jishinRecords"), ("{{条数}}", "jishinConditions"),
                   ("{{一括以外の記録数}}", "jishinNonBundled"),
                   ("{{門の記録数}}", "jishinGateRecords")):
        raw = raw.replace(_k, str(d.get(_v, "?")))
    raw = raw.replace("{{典拠一覧}}", blk)
    raw = raw.replace("{{隣家の表}}", neighbour_block(
        d, load_terrain(os.path.join(DOC, "doi_edo_dem.json")),
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
    print("── 矩形の重なり: %s" % ("**0 件**" if not bad else "⚠ %d 件" % len(bad)))
    for b in bad:
        print("   ", b)
    pbad = (plane_check(d) + inubashiri_check(d) + opening_fit_check(d) + refs_check(d)
            + norms_check(d) + perimeter_check(d) + perimeter_closure_check(d)
            + mune_gap_check(d) + band_check(d) + neighbour_hash_check(d)
            + clearance_check(d) + rails_check(d)
            + ramp_check(d) + completeness_check(d) + program_check(d) + gate_overlap_check(d) + vocab_check(d)
            + terrace_overhang_check(d) + setchin_check(d)
            + route_check(d, load_terrain(os.path.join(DOC, "doi_edo_world.json")))
            + stair_bank_check(d, load_terrain(os.path.join(DOC, "doi_edo_world.json")))

            + terrain_provenance_check(d, load_terrain(os.path.join(DOC, "base_dem.json")))
            + terrain_canon_check(d, load_terrain(os.path.join(DOC, "doi_edo_dem.json")),
                                  load_terrain(os.path.join(DOC, "doi_dem.json")))
            + boundary_fill_check(d, load_terrain(os.path.join(DOC, "doi_dem.json")))
            + mune_fit_check(d)
            + edge_step_check(d, load_terrain(os.path.join(DOC, "doi_dem.json")))
            + wall_end_check(d, load_terrain(os.path.join(DOC, "doi_edo_world.json")))
            + wall_profile_check(d)
            + recon_reach_check(d)
            + niwa_check(d) + akichi_check(d) + shitakusa_check(d)
            + komon_step_check(d, load_terrain(os.path.join(DOC, "doi_dem.json")))
            + wall_needed_check(d, load_terrain(os.path.join(DOC, "doi_dem.json"))))
    # ⛔ **庭方へ差し戻す点は別枠。** 指図方は意匠を動かせないので、面のはみ出し検査と混ぜない
    #   (混ぜると「指図が不成立」に見える)。隣家の宿題と同じ扱い。
    # ⛔ **0件でも件数を出す**(0件と未実行を見分けられなくしない)。
    tbad = niwa_todo(d)
    print("── 庭方へ差し戻す点(指図方では直せない): %s"
          % ("**0 件**" if not tbad else "⚠ %d 件" % len(tbad)))
    for b in tbad:
        print("   ", b)
    # ⭐ **屋根の意匠の差し戻しも同じ扱い**(2026-09-06 ユーザー裁定=案C)。
    #   ⛔ 面のはみ出し検査と混ぜない — 混ぜると「指図が不成立」に見える。
    #   ⛔ 0件でも件数を出す(0件と未実行を見分けられなくしない)。
    rbad = band_todo(d)
    print("── 屋根で普請奉行/ユーザーの裁定を待つ点(指図方では決められない): %s"
          % ("**0 件**" if not rbad else "⚠ %d 件" % len(rbad)))
    for b in rbad:
        print("   ", b)
    nbad = (neighbour_wall_check(d, load_terrain(os.path.join(DOC, "doi_edo_dem.json")),
                                 load_terrain(os.path.join(DOC, "doi_dem.json")))
            + shared_edge_check(d, load_terrain(os.path.join(DOC, "base_dem.json"))))
    if nbad:
        print("── 隣家の宿題(当家では直せない)%d 件:" % len(nbad))
        for b in nbad:
            print("   ", b)
    # ⛔ **0件でも件数を出す**(0件と未実行を見分けられなくしない=規則19)。
    #   ⚠ 2026-09-06 検図方 中4: すぐ上のコメント自身が「0件でも件数を出す」と書いているのに、
    #   **`pbad` だけが `if pbad:` で沈黙していた**。
    print("── 指図方の機械検査(30本余りの束): %s"
          % ("**0 件**" if not pbad else "⚠ %d 件" % len(pbad)))
    for b in pbad:
        print("   ", b)
    wbad = wall_check(d)
    print("── 土留めの高さ: %s" % ("**0 件**" if not wbad else "⚠ %d 件" % len(wbad)))
    for b in wbad:
        print("   ", b)

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ['<meta charset="utf-8">', "<title>土井大隅守上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">外桜田永田町 ／ 譜代・雁間 二万三千石 上屋敷</p>')
    h.append("<h1>土井大隅守上屋敷 指図</h1>")
    h.append('<div class="box" style="border-color:var(--shu);margin-top:14px"><h3>基準年次と確度</h3><p>'
             '<b>基準年次=安政3年(1856)</b> — 2026-08-29 ユーザー裁定(全邸共通)。'
             '<b>⚠ 安政江戸地震(安政2年10月2日)の翌年</b>で、当邸は被災した当年の翌年にあたる。'
             '⭕ 描くのは<b>復旧が済んだ姿</b>【2026-08-30 ユーザー裁定=案A】。'
             '基図(尾張屋版切絵図)は嘉永3年刊なので<b>6年ぶんの外挿</b>。'
             '所在と屋敷の別は [寛政武鑑 刈谷]A の上屋敷の欄(寛政元年。安政への外挿は B)。<br>'
             '<b>当主=土井利善</b>(弘化4年家督・大隅守/嘉永5-6年は大坂加番で江戸不在/安政5年奏者番)。<br>'
             '<b>外周の構成は当屋敷の一次記録から直接言える(確度S)</b> — 安政江戸地震の被害書上'
             '%d記録が「表門倒・玄関大破」「表御長屋潰」「外構練塀潰」を記す。<b>ただし3邸一括の記事で、'
             'どの辺の塀か・誰の所有かは書かれていない</b> — 確定するのは<b>種別だけ</b>。<br>'
             '屋敷指図(建物平面)は現存未確認 — 御殿の構成は類型(B)、室名・畳数は想定(?)。'
             '書院は<b>雁間詰の城主</b>で作り、帝鑑間格へ上げない'
             '(殿席=雁間は [安政地震被害書上]S・岡本家文書が雁間の部に列挙)。'
             '区画多角形はユーザーのブックマーク角(U)。</p></div>'
             % d.get("jishinRecords", 6))
    h.append('<p class="lede"><b>この文書は現況だけを載せる。</b>過去の案・撤回した説は書かない — '
             '経緯は <code>git log docs/Sashizu/</code> で追う。'
             '寸法の正典は <code>doi_sashizu.json</code>、文章は <code>doi_kosho.md</code>、'
             'この HTML は <code>Tools/Sashizu/build_doi_sashizu.py</code> が組む。'
             '<b>数値をこの文書に書き足さないこと。</b></p>')
    h.append('<div class="box"><h3>作る順序</h3><p>'
             '① 設計=<code>json</code>/<code>md</code> を直す → ② 組む → ③ 検図(edo-kosho / edo-kenzu)'
             '→ ユーザーのレビュー → ④ 実装 → ⑤ 指図と実装を突き合わせて 0 件 → ⑥ 経緯はコミットへ。</p></div>')

    # ⚠ 章を足すと足りなくなるので**算出する**(2026-08-25: 16章目で IndexError)
    _J = "〇一二三四五六七八九"

    def _kan(n):
        # ⚠ **20 以上を潰さない。** 旧版は n≥20 をすべて「其十」に丸めており、
        #   庭の章を足して 20 章を越えた 2026-09-04 に「其十」が3つ並んだ。
        #   章の参照は `KANOF` が題から引くので番号の重複は**参照先を壊す**。
        if n < 10:
            return "其" + _J[n]
        t, u = divmod(n, 10)
        return "其" + ("" if t == 1 else _J[t]) + "十" + ("" if u == 0 else _J[u])
    KAN = [_kan(i) for i in range(1, 41)]
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
               '<span style="color:var(--shu)">┅ 帯の大棟</span>'
               '<span style="color:var(--take)">━ 谷(帯の境)</span>'
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
    # ⚠ **検査の文言と実装の集合を突き合わせる。**この行は長いあいだ「面のはみ出し検査」と
    #   名乗っていたが、`pbad` は面の被覆だけでなく参照切れ・柱割り・外周の閉じ・動線・
    #   語彙・地盤の出所など**30本余りの束**である。検査の名前が実際に測っている集合と
    #   食い違うと、0件の意味を読み違える(メモリ「検査の文言と実装の集合を突き合わせる」)。
    #   2026-09-06 に改めた。
    h.append('<p class="cap"><b>指図方の機械検査(30本余りの束): %s。</b>'
             '面の被覆(0.5間刻み — 棟・付属屋・廊下は自分の y と同じ高さの段の中に、'
             '庭・井戸はいずれかの段の中に完全に載る)を含み、ほかに参照切れ・柱割り・'
             '外周の閉じ・棟の空き・動線の勾配・語彙・地盤の出所・庭(池・園路・植栽・'
             '<b>下草の散布域</b>)を同じ束で測る。</p>'
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
        plate(h, nx(), "現況図(現代の地面)",
              "地盤の正本 base_dem.json(国土地理院 DEM 由来)／ 段彩 2m ／ 等高線 2m(太線 10m)【確度P】")
        fig(h, dem_svg(d, dem, others), legend=dem_legend(),
            cap="<b>いまの土地の姿。</b>⚠ <b>これは現代の地面であって、設計の出発点ではない。</b>"
                "日比谷高校の校庭盛土も大使館の掘削跡も含む。⛔ Unity の live terrain から採らない"
                "(正本は <code>base_dem.json</code>)。細い破線は断面の切り位置。")
        h.append("</div>")

        # ⚠ **江戸期の復元地盤の図版が1面も無かった**(2026-08-25 検図13巡 高-5)。
        #   面の高さも切盛図も断面もこの面から出ているのに、図に描かれていなかった。
        edo0 = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
        wld0 = load_terrain(os.path.join(DOC, "doi_edo_world.json"))
        if edo0 and wld0:
            plate(h, nx(), "江戸期の復元地盤 — **これが設計の出発点**",
                  "正本から近代造成を戻した面 ／ 手順は doi_edo_recon.json ／ "
                  "判定の根拠は [五千分一東京図31]A")
            fig(h, dem_svg(d, wld0, others), legend=dem_legend(),
                cap="<b>面の高さも縁の位置も、ここに見える自然のベンチと法肩から決めている。</b>"
                    "切盛図はこの地形と設計の差を塗ったもの。"
                    "⭐ 現況との差は <b>%d セル・最大 %.2fm</b>(玄関の郭の掘削跡を台地面へ戻した分)。"
                    "1883年図の台地に閉じた等高線も入江も無いことが根拠"
                    "【観測=A / 不存在からの推論=B】。⛔ <b>境界の取り合いだけは正本を読む</b> — "
                    "隣家と同じ面を読むことが要件。" % (wld0.get("_reconCells", 0),
                                                    _recon_max(wld0, dem)))
            h.append("</div>")

    ter = load_terrain(os.path.join(DOC, "doi_edo_dem.json"))
    if ter:
        cf, vf, vc = cutfill_svg(d, ter)
        we0 = dict((t["name"], walled_edges(d, t)) for t in d["terraces"])
        mf = mc = 0.0
        for iv0 in range(ter["nv"]):
            for iu0 in range(ter["nu"]):
                n0 = ter["h"][iv0][iu0]
                if n0 is None:
                    continue
                dz0 = ground_y(d, ter["u0"] + iu0 * ter["step"],
                               ter["v0"] + iv0 * ter["step"], n0, we0) - n0
                mf = max(mf, dz0); mc = max(mc, -dz0)
        plate(h, nx(), "切盛(どこを盛り、どこを切るか)",
              "盛土 %.0f m³(最大 %.1fm) ／ 切土 %.0f m³(最大 %.1fm) ／ "
              "差引(盛土 − 切土)%+.0f m³ ・正=土が足りない ／ <b>奥庭の池と築山を含む</b>"
              % (vf, mf, vc, mc, vf - vc))
        fig(h, cf, legend=cutfill_legend(),
            cap="<b>" + '<b>江戸期の復元地盤</b>(正本 base_dem.json=確度P に、近代造成を戻す復元を重ねた面。**手順=U / 根拠=1883年図の観測A + 不存在からの推論B**)' + "と造成後の地盤の差</b>を1間の格子で塗った。"
                "暖色=盛土/寒色=切土/無彩=±0.3m以内(実質さわらない)/"
                "地の色(薄い緑)のまま=<b>造成しない</b>。破線の枠は段、細い実線は御殿の棟。"
                "<b>面の高さを自然のベンチに載せてあるので、郭の大半は無彩か薄い色になる</b> — "
                "濃く出るのは門前の道なりへの摺り付け・北隅の高み・門の軸の窪みを埋める区間だけ。")
        h.append(cutfill_table(d, ter))
        h.append('<p class="cap">段の外へこぼれる法面(盛土 1:%.1f/切土 1:%.1f)も土量に含む。'
                 '土留めのある辺は壁が垂直に受けるので法面を出さない。'
                 '[菊地2003] の江戸城下67遺跡の集成では土地改変は <b>1〜4m が多数</b>で、'
                 '当屋敷は盛土 %.1fm・切土 %.1fm に収まる。'
                 '<b>差引が正=土が足りない</b>ので、切土で出た土を盛土へ回してなお不足する量。'
                 '⭐ <b>奥庭の池の掘削と築山の盛土もここに入っている</b> — 其八の土量表は'
                 '同じ土を庭の中だけで割った内訳で、<b>符号の向きも同じ(盛土 − 切土 / '
                 '正=土が足りない)</b>にしてある。</p>'
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
        cap="<b>長屋門 → 白洲 → 石段 → 前庭の白洲 → 石段 → 玄関の郭 → 御式台。</b>"
            "**門の軸の石段は二つ**(表門→前庭・前庭→玄関の郭)。"
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
        cap="<b>門の軸の踊り場と、通用門の受け皿。</b>前庭の白洲から石段で玄関の郭へ登る。"
            "北は <code>TW_Kita</code> を越えて米蔵の郭 — <b>通用門(表長屋(北)の潜り)の直近に米蔵</b>を置き、"
            "[高知2000]A の「米蔵は搬出入門の直近」に従う(⚠ 原文は大坂蔵屋敷。**江戸上屋敷への適用はB・位置はU**)。勝手はここから書院の郭を経て台所へ回り、"
            "御式台前の白洲を通らない。")
    fig(h, goten_plan(d, 16, 33, 48, 82, "家中長屋の帯(北・松平境沿い)",
                      "帯は棟ごとに自然の高さを採る。境界が斜めなので棟を継いで沿わせる"),
        cap="<b>松平出羽守との境に沿う家中長屋。</b>境界が回転間グリッドに対して斜めなので、"
            "<b>棟の長軸を境界に平行にして回転グリッドの外に置いた</b>(2026-08-23 の是正。"
            "差は生成器が測る)。棟ごとにその位置の自然の高さを面にしてある"
            "(切盛の実測は棟の表)。段が階段状に上がって見えるのが正しい。"
            "帯の内側は主面の北東肩で、造成しない。"
            "<b>⚠ 家中長屋の規模は未検算</b> — 必要床面積の典拠が無い(石高→軍役→江戸詰人数の"
            "比率に典拠がなく、当家の江戸詰人数の史料も無い)。<b>延長は外周に回した結果</b>であって、"
            "収容力から逆算した数字ではない【確度U】。")
    fig(h, goten_plan(d, -6, 20, 24, 48, "玄関の郭と書院の郭",
                      "玄関の郭と、その東の帯。**同高(26.0)でひとつの面**"),
        cap="<b>御殿の表向がひとつの面に載る所。</b>玄関棟と書院棟はどちらも台地の面(26.0)で、書院棟は"
            "北東の横長の帯に載る。**両郭に落差が無いので段は要らず、渡廊下でつなぐ**。"
            "⛔ かつてここにあった土留め <code>TW_Shoin</code> は撤去した — "
            "玄関の郭を近代の掘削跡から復元地盤へ戻した結果、受けるべき落差が消えたため。")
    fig(h, goten_plan(d, -21, -11, 54, 78, "家中長屋の帯(南・岡部境沿い)",
                      "岡部境沿いの二棟。土蔵・南庭との取り合い"),
        cap="<b>岡部内膳正との境に沿う家中長屋。</b>北の帯と同じく<b>長軸を境界に平行</b>にし、"
            "棟ごとに自然の高さを採る。高さは主面と同じなので段差は無い。"
            "東は台所棟の勝手裏で、土蔵二棟がこの間に入る。"
            "岡部との共有境界は<b>両指図の区画多角形が 0.00m で一致</b>しており、"
            "囲いは岡部が全区間に持つ(当家は建てない)。")
    h.append("</div>")

    # ---------------------------------------------------------------- 奥庭
    # ⚠ **設計値を入れたら同じ巡でそれを描く図を出す**(規則19)。庭の欄だけ足して
    #   図を出さないと、汀線も築山も園路も**誰の目にも触れないまま**正典に座る。
    if NI(d):
        _ng = NI(d).g
        _no = niwa_stats(d)
        plate(h, nx(), "奥庭(座敷前の池庭)",
              "庭方(edo-niwashi)が 2026-09-04 に設計 ／ 指図方が数値へ書き起こし ／ "
              "作庭の体=行 ／ 存在=B・形と寸法=U ／ ⛔ 回遊の大庭園にしない")
        fig(h, niwa_plan_svg(d),
            legend="".join('<span style="color:%s">━ %s</span>' % (c, k)
                           for k, c in GOGAN_COL.items())
                   + '<span style="color:var(--michi)">━ 園路(幅%.1fm)</span>'
                     % _ng["enro"][0]["w"]
                   + "".join('<span style="color:%s">● %s</span>' % (c, k)
                             for k, c in LAYER_COL.items())
                   + '<span style="color:#7E9A5E">■ 刈込</span>'
                     '<span style="color:#9BB07A">▨ 下草(シダ・破線の縁)</span>'
                     '<span style="color:var(--tsuki)">■ 築山(等高線 0.25m)</span>'
                     '<span style="color:var(--ike)">■ 池</span>',
            cap="<b>主景は一点=見所①(奥御広間の入側)。</b>他はすべてこれに従わせる。"
                "前景=沓脱石・飛石・州浜の汀／中景=東の池・岩島・北東の岬の雪見灯籠／"
                "遠景=築山A1の尾根とその上のクロマツ・常緑広葉。"
                "<b>池は掘り込み</b>(水面 %.2f・最深 %.2fm)で、⛔ 滝も遣水も置かない — "
                "主面の台地に落差の源が無いため<b>天水の止水池</b>にする。"
                "<b>園路は同心円にしない</b> — 東の帯 → 築山の稜線(上り)→ 西の池の外 → "
                "築山Bの裾 → 沢飛石(寄り)の順に離れ・寄り・上りが入る。"
                "⛔ <b>蹲踞・手水鉢・石橋・中島・堂・茶屋は置かない</b>(茶庭と下屋敷の語彙)。"
                "⭕ 稲荷の社前の手水石だけは社の作法として置く。"
                % (_ng["migiwa"]["waterY"], _ng["migiwa"]["depthMax"]))
        h.append("<h3>池(泉水)の形</h3>")
        h.append(niwa_pond_table(d))
        h.append('<p class="cap">⛔ <b>この表の数字を設計値へ写さない</b> — すべて汀線18点からの'
                 '従属値で、生成器が毎回測る。汀線は<b>平滑化前の設計値</b>で、実装では '
                 'Chaikin×%d を掛ける(平面図の細い破線が施工形状)。</p>'
                 % _ng["migiwa"]["smooth"])
        h.append("<h3>護岸 — 全周を4形式で覆う</h3>")
        h.append(niwa_gogan_table(d))
        h.append('<p class="cap">⛔ <b>裸の縁を残さない。</b>⛔ <b>輪郭点をそのまま護岸の据え位置に'
                 'しない</b> — 掘削が縁を下げるので、護岸は「外向きに進んで最初に地面が水面を'
                 '超える点」に据える。⭐ <b>石材は庭全体で一系統=伊豆石</b>(江戸の石材流通【B】)。'
                 '⛔ 産地を混ぜない。石の個数・杭の本数は延長からの従属値。</p>')
        h.append("<h3>築山と土量</h3>")
        h.append(niwa_tsuki_table(d))
        h.append(niwa_vol_table(d))
        h.append('<p class="cap"><b>掘削と盛土は釣り合わせる</b>([築山庭造伝] の'
                 '「池を掘りたる土をもって山を築く」。当てはめは <b>B</b>)。'
                 '<b>敷地外へ土を出さない・入れない。</b>庭は <code>on: 地なり</code> で'
                 '<b>切土ゼロ</b> — 動かす土は池の掘削と築山の盛土だけである。'
                 '⭐ <b>法は「実測の最急」で検め、上限は <code>const.batterFill</code>(1:1.5)。</b>'
                 '⛔ 素の丘(公称 × 2/π)との比較はしない — 平場を切れば必ず立つのは形の性質で、'
                 '欠陥ではない【2026-09-04 庭方の物差しの差し替え】。'
                 '⚠ <b>公称(直径÷高さ)だけでは足りない</b> — それだけを見ていたとき、'
                 '築山A1 の平場の縁に <b>1:0.53 の崖</b>が立っていたのを見逃していた。両方を検める。<br>'
                 '⭐ <b>主峰の優越は高さでなく「幅と頂の平場の有無」で付ける</b> — '
                 '築山A1 は頂が主視点の眼より下がるが、稜線が眼と同高だと山は地平線と重なって'
                 '<b>厚みを失う</b>ので、そのほうが良い。</p>')
        h.append("<h3>園路</h3>")
        h.append(niwa_enro_table(d))
        h.append('<p class="cap">⚠ <b>勾配は二通り測る。</b>野面の石段を切るかは<b>区間</b>の勾配で決め、'
                 '「登れるか」は<b>0.25m 刻みで地表を刻んだ 1m 窓の最急</b>で検める — '
                 '区間の両端だけで測ると<b>急な中腹を見落とす</b>(2026-09-04 庭方の申し送り)。'
                 '⛔ 窓は<b>1m ちょうど</b>で滑らせる — 「1m 以内の任意の2点」にすると、'
                 '東の土手の縁の 0.23m の段(蹴上1段ぶん)を 0.25m 幅で割って 92%% に化ける。'
                 '<b>それは段であって勾配ではない。</b><br>'
                 '⭐ <b>主路は稲荷の社地の外を隘路で抜ける</b> — 社地の南西隅と汀 #2 のあいだは '
                 '1.55m(社地の枠を 0.25 → 0.15間 に締めて広がった)なので、路を隘路の芯に通し、'
                 '<b>その区間だけ幅を 0.75m(2尺5寸)に締めた</b>(主路の幅は 0.90m)。'
                 '⭕ 0.75m を通しても両側に 0.40m 残るので、絞りは「やむを得ず」ではなく'
                 '<b>設計上の選択</b>である。⭕ <b>社の角で路が細くなり、抜けると池が開く</b>のは景として得になる。'
                 '⭐ <b>枝路は登らない</b> — 築山A1・A2 のあいだの鞍部を横に抜けて主路に落ち合う'
                 '(尾根を越えずに近道できる本当の分岐)。'
                 '⚠ 「路縁 → 汀」は<b>終端(沢飛石の袂)を除いた</b>値 — そこは汀に寄るのが役目。'
                 '⭕ 沓脱石からの第1区間には<b>飛石6石が乗る</b>(沓脱から飛石で路に入る作りで、'
                 '重なりは意図)。⭐ 芯々は台帳の目安 0.40〜0.55m に全部入る — '
                 '⛔ <b>「降り口だから歩幅が大きくなる」という旧の断りは撤回</b>'
                 '(沓脱石の縁から1石目まで 0.202m で、むしろ縮む)。</p>')
        h.append("<h3>見所</h3>")
        h.append(niwa_mikoro_table(d))
        h.append("<h3>植栽 — 常緑を骨格に、落葉を景に</h3>")
        h.append(niwa_plant_table(d))
        h.append('<p class="cap">⛔ <b>ソメイヨシノ・桜(開花木)・孟宗竹の竹叢・幕末以降の外来種を'
                 '置かない。</b>⛔ 自作の低ポリゴンの木を使わない。⛔ イロハモミジを<b>紅葉色に'
                 'しない</b>(季節は春でも秋でもない)。⛔ <b>ウメに花を咲かせない</b> — '
                 '<b>描く時点は安政3年の旧暦6月</b>に確定しており、花期(旧暦一〜二月)を'
                 '大きく過ぎているので葉姿(青梅)で置く【2026-09-04 普請奉行の裁定】。'
                 '⭐ <b>枝下 `crownFrom` と幹半径 `trunkR` を全層に持つ</b> — 前者は見切りの検査が、'
                 '後者は園路からの離れの検査が使う。'
                 '⭐ 樹高・樹冠幅は <code>docs/asset-index.tsv</code> の実測で、'
                 '<b>指図には写さない</b>。個体(01〜03)を混ぜること。</p>')
        h.append("<h3>刈込 — 汀に沿うものは矩形でなく帯</h3>")
        h.append(niwa_karikomi_table(d))
        h.append("<h3>実装の申し合わせ — 棟梁への指示</h3>")
        h.append(niwa_impl_table(d))
        h.append("<h3>点景 — 据え位置・部材・据え向き</h3>")
        h.append(niwa_tenkei_table(d))
        h.append("<h3>下草の散布域 — 言葉でなく幾何で持つ</h3>")
        h.append(shitakusa_table(d))
        h.append("<h3>樹冠の被覆率(庭方の検査 6-④)</h3>")
        h.append(niwa_cover_table(d))
        h.append("</div>")

        plate(h, nx(), "奥庭の断面 — 主景の見切り",
              "御土蔵の白壁を樹冠で切れているかを、部材の実寸から検算する")
        for _s in d.get("gardenSections", []):
            h.append('<h3>%s</h3>' % _s["label"])
            fig(h, niwa_section_svg(d, _s))
        h.append("<h3>見切りの合否 — 蔵の見える面(全長 × 全高)</h3>")
        h.append(niwa_kura_table(d))
        h.append("<h3>見切りの検算(参考)— 樹冠が塞ぐべき帯</h3>")
        h.append(niwa_screen_table(d))
        h.append('<p class="cap">⭐ <b>「主景の対岸が御土蔵の白壁」という指摘の合否はこの表で決まる。</b>'
                 '眼から蔵の<b>軒下端</b>への視線と<b>棟</b>への視線が、その木の位置で地表から'
                 '何 m の所を通るか(=塞ぐべき帯)を出し、樹冠(下端は設計書の値・'
                 '樹高は部材の実測)が覆えているかを見る。⛔ <b>築山だけでは切れない</b> — '
                 '3.6m 級の山が要って土量が破綻する。<b>木で切るのが正解</b>で、'
                 '樹冠の下端が抜ける帯は<b>`Dote_Kuramae`(+0.45m)に載せた刈込①(蔵前の帯)</b>が受ける。'
                 '⭐ <b>枝下は全層が持つ</b>ので、遮蔽から外れる層は無い。'
                 '⚠ <b>この表は木ごとの参考で、合否は上の「蔵の見える面」で決める。</b></p>')
        _ku = _no.get("kura")
        h.append('<p class="cap">⚠ <b>御土蔵の高さは部材の実寸で置き直した。</b>'
                 '庭方の仮置き(棟 32.10 / 軒下端 30.00)に対し、実測は'
                 '<b>棟 %.2f / 妻壁の頂 %.2f / 軒下端 %.2f</b>(地盤 %.2f からの内訳は'
                 '白壁 0.000〜%.3fm / 屋根 %.3f〜%.3fm)。'
                 '⭐ <b>2026-09-06 に棟高を部材方の第1段の実測へ置き直した</b> — '
                 '<code>const.kuraRidge</code> <b>6.51 → %.3f</b>。'
                 '⚠ <b>6.51 は在庫 <code>EdoAssets.Eg.Kura</code>(梁間 3.65間)の実測で、'
                 '当図の御土蔵(梁間 %d間)とは別の建物の数字だった。</b>'
                 '新しい値は梁間3間・軒下端 %.2f・瓦勾配 0.5456 からの従属値で、'
                 '部材方が焼いた 3×8間 の蔵の実寸 <b>15.582 × 6.867 × 7.071m</b> と一致する。'
                 '⛔ <b><code>kuraWallTop</code>(妻壁の頂)は据え置き</b> — '
                 'これも旧部材由来の数字だが、第1段の報告は bbox しか来ておらず、'
                 '棟高との差を持ち越すのは<b>推測であって実測ではない</b>ので置かない'
                 '(<code>_pending.kurabuzai</code>)。'
                 '⭕ <b>見切りの合否は地盤〜棟で立つ</b>ので、この一件で上の表は動かない。'
                 '⚠ <b>足形はまだ照合できていない</b>(御土蔵の矩形は %d×%d間 / '
                 '`Kura2` は 3×3間 で、焼かれた版と accessor 名が未着)。</p>'
                 % (_ku["ridge"], _ku["wall"], _ku["eave"], _ku["o"]["y"],
                    d["const"]["kuraWallTop"], d["const"]["kuraEave"], d["const"]["kuraRidge"],
                    d["const"]["kuraRidge"],
                    _ku["o"]["u1"] - _ku["o"]["u0"], d["const"]["kuraEave"],
                    _ku["o"]["u1"] - _ku["o"]["u0"], _ku["o"]["v1"] - _ku["o"]["v0"])
                 if _ku else "")
        h.append("<h3>水尻(余水吐)の縦断</h3>")
        fig(h, niwa_mizushiri_svg(d),
            cap="<b>余水は西端 #14 の石の閾から埋樋で法面の下へ落とし、受け石(玉石の浸透枡)で"
                "止める。</b>⛔ <b>隣家へ流し込まない</b> — 落とし口は岡部境の内側。"
                "⚠ <b>勾配が緩い</b>ので、樋の底と復元地盤を重ねて毎回検算する。"
                "御土蔵(什器)との最近接は検査が測る。")
        h.append(niwa_toi_table(d))
        h.append('<p class="cap">⚠ <b>土被りが 0.30m を切る点は「埋樋」として成立しない。</b>'
                 '⭕ 終点(石組の吐き口)はそこで地表へ出る設計なので除いてよい。'
                 '地盤は江戸期の復元地盤の実測【確度P】。</p>')
        # ⛔ **0件でも件数を出す。**0件と未実行を見分けられなくしない。
        h.append('<p class="cap">%s</p>'
                 % ("⭕ <b>庭方へ差し戻す点: 0 件。</b>指図方が数値へ落として見つけた5件"
                    "(築山A1 の法・枝路の勾配・主路が稲荷を掠める・四つ目垣の走り・見所5 の眼高)は"
                    "<b>2026-09-04 に庭方が決定して解消</b>した。この検査は毎回走り、"
                    "意匠の判断が要る不整合が出たら別章を立てて刷る。"
                    if not tbad else
                    "⚠ <b>庭方へ差し戻す点が %d 件ある</b> — 別章を見よ。" % len(tbad)))
        h.append("</div>")

    if d.get("akichi"):
        plate(h, nx(), "主郭の明地(用途未定)",
              "0.5間格子の実測 ／ ⛔ 用途を発明しない ／ 中庭1枠【B】+ 明地3枠【?】(2026-09-04 考証)")
        fig(h, akichi_svg(d),
            cap="<b>主面のうち、どの棟にも庭にも属さない無名の面。</b>庭方の点検(2026-09-04)で"
                "見つかった。奥庭を v64.5 まで広げてその一部を取り込み、"
                "<b>奥向の井戸</b>が北の帯に入った(従前の井戸3本は勝手・門前・表役所だけで、"
                "奥御湯殿・奥御雪隠の水の出所が指図に無かった)。残りは<b>用途を発明せず</b>、"
                "<b>位置で名を立てて明地とする</b> — 名に用途を入れない。"
                "⚠ <b>枠は「測る枠」であって面ではない</b>(枠の中の棟・庭・蔵は差し引く)。")
        h.append(akichi_table(d))
        h.append("</div>")

    # ⚠ **測った ⚠ を stdout に閉じ込めない**(規則19)。庭方へ返す点は図に載せる。
    if tbad:
        plate(h, nx(), "庭方へ差し戻す点(指図方では直せない)",
              "%d 件 ／ ⛔ 意匠の判断なので指図方は数値を動かさない" % len(tbad))
        h.append('<p class="cap">指図方は「決まったことを実装できる数値へ書き起こす」役で、'
                 '<b>意匠の判断はしない</b>(CLAUDE.md 規則17)。'
                 '数値へ落として初めて見えた不整合を、<b>直さずにここへ出して庭方へ返す</b> — '
                 '⛔ 黙って値を動かして辻褄を合わせない。</p>')
        h.append("<ul>" + "".join("<li>%s</li>" % b for b in tbad) + "</ul>")
        h.append("</div>")

    plate(h, nx(), "棟と室", "1間²=2畳 ／ 室名・畳数は【確度 ?】(土間・板敷は間²)")
    h.append(munes_table(d, load_terrain(os.path.join(DOC, "doi_edo_dem.json"))))
    h.append(links_table(d))
    kp_html, kp = kenpei(d, area)
    kp_html += gate_area_note(d)          # `_pending.kenpei` の残作業(出所を注に出す)
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
             '⚠ <b>御殿の床面積に上限の物差しは無い。</b>⛔ 従前ここは [高知2000]A の'
             '「24万2千石の上屋敷でも表御殿614坪」を上限として当てていたが、<b>24万石の値を'
             '2万3千石の上限に使うのは物差しとして働かない</b>(格が10倍離れた家の実測は、'
             '当家がそれを下回ることを何も保証しない)。⇒ <b>2026-09-04 に物差しを差し替えた</b>'
             '(考証方 中-11)。⭕ 当家の帯で突き合わせられるのは'
             '<b>[西川1959]A 所引 慶長11年 肥後人吉藩相良家(2万2千石)「江戸御屋形作日記」の'
             '<u>下限</u>9項目</b>(広間・中門・書院・台所・風呂・雪隠・廊下・局・門)だけで、'
             '当図はこの9つを<b>中門を除いてすべて満たす</b>(中門は同じ台帳の'
             '「1万石級での中門は史料未確認」と緊張関係にあるため採らない)。'
             '⛔ <b>上限のほうは台帳に無い</b> — 石高で床面積を絞る根拠が無いので、'
             '「広すぎないか」はこの図では<b>判定しない</b>【確度U】。'
             '⚠ 御殿の棟(入側とも)は隣の岡部(5万3千石)より広いが、'
             '<b>岡部の値は自作なので norm にしない</b>(規則8)。'
             '縮めていないのは設計判断で、<b>判断したことをここに書いておく</b>。</p>'
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
        h.append('<p class="cap"><b>段のつなぎ方は平面だけでは読めない。</b>地表下の色帯=面('+KANOF('敷地')+' と同じ色分け)。'
                 '<b>破線=江戸期の復元地盤</b>(手順U / 根拠A+B)なので、実線との差がそのまま切土/盛土。'
                 '区画線上には当家所有の囲い(表長屋/練塀)だけを天端と基壇石垣つきで示す — '
                 '南北の境は隣家所有のため空けてある。基壇は境界線上に垂直に立ち、道・隣地の地形には触れない。'
                 '屋根の起りは設計値からの見込み【P】(梁間÷2×瓦勾配)・実装の高さは部材が正で、実装の高さは部材が決める(突き合わせの対象外)。</p>')
        h.append("</div>")

    plate(h, nx(), "外周の展開", "天端は辺ごとに一本。段は門・頂点・郭境の延長線でのみ落とす")
    fig(h, perimeter_dev_svg(d))
    h.append(runs_table(d))
    h.append('<p class="cap">表長屋は<b>表(東辺)だけ</b> — 表=表長屋+長屋門、ジョグ・楔=練塀'
             '(当家所有の囲いはこの三辺のみ)。東辺南端は南東の低み(非造成)の前で内側に面が無いため、'
             '表長屋でなく<b>道なりの練塀</b>とする。北・西の囲いは松平所有、南は岡部所有'
             '(屋敷境の囲いは1条・隣家持ちの裁定)。<b>西辺は全区間が練塀+石垣基壇</b> — '
             '松平の指図で「相手のある屋敷境は斜面でも練塀で通す」と改められた(2026-08-23)。'
             '石垣の天端の犬走り %.2fm(=%.1f間)。</p>'
             % (d["const"]["inubashiri"] * d["const"]["ken"], d["const"]["inubashiri"]))
    # 共有辺の地盤検査は**合否を問わずここに載せる** — 2026-08-26 まで、松平の復元地盤が
    # 無いために当家の辺8・9が未検査のまま図が「0件」の顔をしていた(shared_edge_check の docstring)。
    h.append('<p class="cap">%s</p>'
             % shared_edge_html(d, load_terrain(os.path.join(DOC, "base_dem.json"))))
    h.append("</div>")

    _mf = [(m["name"], mune_fit(d, m))
           for m in d["munes"] + d["service"]]
    _mf = [(n_, r) for n_, r in _mf if r]
    _over = [(n_, r) for n_, r in _mf if abs(r[0]) > 0.5]
    h.append('<p class="cap">⚠ <b>§B-1 の運用</b> — 「棟が載る所で |設計面 − 自然地形| ≤ 0.5m」は'
             '<b>面積比 5%% で判定する</b>(0%% を求めると地形の粒度に負ける)。'
             '全 %d 棟が 5%% のゲート内(超過率の最大 %.1f%%)。'
             'ただし<b>局所の最大では %d 棟が 0.5m を超える</b>: %s。'
             '残りは全域 ±%.2fm 以内。</p>'
             % (len(_mf), max(r[1] for _, r in _mf), len(_over),
                "・".join("%s %.2fm" % (n_, abs(r[0])) for n_, r in _over) or "無し",
                max((abs(r[0]) for n_, r in _mf if (n_, r) not in _over), default=0.0)))

    plate(h, nx(), "表門まわり", "長屋門・切妻造(片番所・格子付・片潜門)。型式=B(表長屋の実在S+[山脇武家屋敷門]A)/屋根=B(型式からの帰結)/番所と潜戸=B/U(型式をまたぐ移植)/石高帯: 掲示の記載=A / 当てはめ=B / 採用=U([下丸子武家屋敷門]の都教委掲示)/実在と被災=S")
    fig(h, gate_svg(d),
        cap="<b>番所と潜戸の形式</b>は [下丸子武家屋敷門](A)の官製構造形式"
            "「<b>片番所格子付、片潜門</b>」による【B/U — 型式をまたぐ移植。下記】。東京都教育委員会の掲示が"
            "「遺存例の少ない<b>1〜5万石の小大名格</b>の形式」と明記しており、二万三千石はこの帯に入る。"
            "<b>⚠ 番所は張り出さない</b> — 官製は「格子付」で、現物でも壁面から出るのは庇付きの格子窓だけ、"
            "番所の室は躯体内に納まる。室ごと一間張り出すのは山脇門(5万石・「片流<b>面出</b>番所附属」)の姿で、"
            "下の段に持ち込むと格が1段上がる。番所と潜戸はともに<b>向かって左</b>、右は板壁のみ【現物1件=P/U】。"
            "⛔ ただし「1〜5万石」は所有者から出た数字ではなく<b>都教委が形式から下した判定</b>で、"
            "元の屋敷の伝承は三説あって互いに矛盾する — <b>独立検証ではない</b>。"
            "安政二年の被害書上は「表門倒」— <b>安政3年の姿として、倒れて復旧した門</b>を建てる"
            "【2026-08-30 ユーザー裁定=案A】。⚠ 当家の被災記録のうち <b>J2300427 は「安政三辰年」の帳</b>で"
            "「表御門倒御玄関其外大破<b>ニ付御客様方御断</b>」と記す — <b>基準年次の当年に『門は倒れている』と"
            "読める一次記録がある</b>うえで復旧済みの門を建てている。裁定の根拠は「帳の題の年 ≠ 条の事実の年」"
            "(年をまたいだ書き継ぎの可能性が消えない=読みは確度B)で、確度B一本で全邸共通則に例外を作らないこと。"
            "⛔ 復旧の程度・工期を推定して型式を落とすことはしない【U】。"
            "⚠ <b>「表門倒」と「表御長屋の被災」を独立門の証拠に使わない</b> — 二語は別々の文書に現れるもので"
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

    plate(h, nx(), "段の縁の落差 — 実装の検査との仕分け",
          "実装の `EdgeStepQA` が鳴らす縁を指図の側から仕分ける。⛔ ここで壁を足さない(設計判断)")
    h.append(edge_step_qa_table(d, load_terrain(os.path.join(DOC, "doi_dem.json"))))
    h.append("</div>")

    plate(h, nx(), "郭の土留めと竹垣")
    _hw = max(((w["name"], 4.0 * w["s"] * w.get("tiers", 1)) for w in d["terraceWalls"]),
              key=lambda q: q[1])
    _hr = max(((r["name"], r.get("expose", 0.0), r.get("tiers", 1))
               for r in d["runs"] if r.get("base") == "Ishigaki"), key=lambda q: q[1])
    h.append(walls_table(d))
    h.append('<p class="cap">造成しない斜面へ向く縁の法肩には<b>竹垣(四つ目垣)</b>を回す — '
             '落差のある生活面を素の縁にしない(岡部指図と同じ作法)。寸法・控えは取り合いの表のとおり。'
             '<b>土留めは落差のある縁にだけ置く</b> — 天端と法尻の差は 2026-08-23 に実測で確かめ、'
             '落差の無い縁(主面の南舌部の縁・主面南翼の南縁・主面の西縁)は<b>土留めを置かず竹垣だけ</b>にした'
             '(地中に埋まる壁を作らない)。<b>郭の土留めでいちばん高いのは <code>%s</code>(壁高 %.2fm)</b>。'
             '⚠ 屋敷全体では<b>外周 run の基壇石垣</b>のほうが高い — <code>%s</code> が露出 %.2fm'
             '(%d段築)。「いちばん高い石垣」は郭の中と外周とで別なので、どちらの話かを必ず書く。</p>'
             % (_hw[0], _hw[1], _hr[0], _hr[1], _hr[2]))
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
        h.append("<h3>御殿の屋根 — 帯の割り付けと要る寸法(棟から機械で出す)</h3>")
        h.append(roof_table(d))
        # ⭐ **意匠の差し戻しは図に出す**(規則19)。⛔ stdout に閉じ込めない。
        _bt = band_todo(d)
        h.append('<div class="box" style="border-color:var(--shu)"><h3>'
                 '⚠ 屋根について普請奉行/ユーザーの裁定を待っている点: %s</h3>%s</div>'
                 % (("<b>0 件</b>" if not _bt else "<b>%d 件</b>" % len(_bt)),
                    ("<p class='cap'>⭕ 無し。</p>" if not _bt else
                     "<ol>" + "".join("<li>%s</li>" % inline(q) for q in _bt) + "</ol>"
                     + "<p class='cap'>⛔ <b>これらは意匠なので指図方では決められない</b>"
                     "(規則17)。⛔ <b>実装で埋めない。</b>⭕ 裁定が付くまで"
                     "<b>屋根部材を焼かない</b> — 割り付けが動くと寸法がやり直しになる。</p>")))
        h.append("<h3>部材方(edo-buzai)への依頼票</h3>")
        h.append(buzai_table(d))
        h.append("</div>")

    # ⚠ **未決の宿題を図に出す。**2026-09-06 まで `_pending` は生成器が一度も読んでおらず、
    #   35件の宿題が**ユーザーの見る文書に一行も出ていなかった**(規則19: 書いたのに
    #   誰の目にも入らない産物を作らない)。部材の新造依頼もここに埋もれていた。
    plate(h, nx(), "未決の宿題", "`_pending` の全件。⛔ 閉じたものは「閉じた」と書いて残す(消さない)")
    h.append(pending_table(d))
    h.append("</div>")

    # ⚠ **在るべき役割と確度を図に出す。** 正典に持つだけでは
    #   **ユーザーがレビューする図に確度ラベルが一つも出ない**(2026-08-25 考証13巡 中-4)。
    #   台帳が U と裁定済みの米蔵を A へ戻していた食い違いも、人の目に触れずに残っていた。
    plate(h, nx(), "在るべき役割と確度",
          "役割 → それを満たす物 → **側面ごと**の確度と典拠。確度を役割ごとに一つへ潰さない")
    h.append(program_table(d))
    h.append("<h3>確度の裁定 — 一度下した判断を黙って巻き戻さない</h3>")
    h.append(cert_rulings_table(d))
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
    body = resolve_kan("\n".join(h))   # 全章を登録し終えてから章番号を解決する
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
    # ⚠ **設計値は「葉の文字列ごと」を段落に取る。** `json.dumps` は改行を持たないので、
    #   段落単位の極性検査に掛けると**段落が1個**になり、その1個に撤回の印が必ず含まれて
    #   **json の禁句が全部見逃されていた**(2026-08-25 考証第12巡 高⑤: 完全な恒真)。
    _leaves = []

    def _leaf(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k not in ("retracted", "_retracted"):
                    _leaf(v)
        elif isinstance(o, list):
            for v in o:
                _leaf(v)
        elif isinstance(o, str):
            _leaves.append(o)
    _leaf(d)
    flat = re.sub(r"[*~`]", "", "\n\n".join(_leaves))
    rbad = retracted_check(d, [
        ("設計値", flat),
        ("文章", re.sub(r"[*~`]", "", open(MD, encoding="utf-8").read())),
        ("生成器", re.sub(r"[*~`]", "", open(__file__, encoding="utf-8").read())),
        # ⚠ **図はタグ単位で段落に割る。** HTML は空行を持たないので、
        #   段落単位の極性検査に掛けると**全体が1段落**になり、その中に ⛔ が必ず在るため
        #   **図の禁句が全部見逃されていた**(2026-08-25 検図13巡 高-3。設計値と同じ恒真)。
        # ⚠ **閉じタグだけで切らない。** 最初の ⛔ を含む要素の閉じが遠いと段落が長く延び、
        #   その手前に差した禁句が**撤回の印で赦されて**しまう(2026-08-25 検図13巡 低-6:
        #   ⛔ の直前へ差した禁句が 0 件、印の無い所へ差すと 1 件だった)。
        #   **開きタグでも切る** — 印の効き目をその要素の中だけに閉じ込める。
        # ⚠ **改訂(git のコミット件名)は照合から外す。** コミット件名は**履歴**であって
        #   現況の記述ではなく、⛔ **書き換えられない**(規則4「経緯は git log が持つ」)。
        #   撤回の作業そのものを記録した件名(例「…の呼称を改めた」)が必ず禁句を含むので、
        #   外さないと**撤回を済ませた瞬間に検査が赤くなる**(2026-09-06 に踏んだ)。
        #   ⛔ 除外は「改訂の章まるごと」ではなく**その章だけ**に閉じる。
        ("図", re.sub(r"[*~`]", "",
                      re.sub(r"</?(p|td|th|li|h[1-6]|div|tr|table|ul|ol|section|"
                             r"figcaption|caption|svg|g|text|tspan)\b[^>]*>", "\n\n",
                             _strip_history(body)))),
        # ⚠ **実装も照合の面に入れる。** 四面(設計値・文章・生成器・図)だけを見ていたため、
        #   実装のヘッダに 2026-08-12 の考証ブロックが4か月ぶん古びたまま残り、
        #   各屋敷の指図が撤回した説を現役の根拠として保持していた
        #   (2026-08-25 考証第10巡 高①)。**「四面」という枠の取り方が狭かった。**
        ("実装", re.sub(r"[*~`]", "", _impl_text())),
        # ⚠ **台帳とメモリも面に入れる。** 撤回済みの説が現役の記述として生きていた
        #   (2026-08-25 考証第11巡 高①: メモリが撤回済みの番所の数を保持していた)。
        #   極性検査にしたので、撤回の記録そのものは偽陽性にならない。
        ("台帳", re.sub(r"[*~`]", "", _ledger_text())),
        ("メモリ", re.sub(r"[*~`]", "", _memo_text())),
    ])
    print("── 撤回の印つきで見逃した数: %d 件" % d.get("_retractedMarked", -1))
    print("── 撤回済みの説の残り: %s"
          % ("**0 件**" if not rbad else "⚠ %d 件 — **図は書き出したが要修正**" % len(rbad)))
    for b in rbad:
        print("   ", b)
    if rbad:
        sys.exit(2)
    # ⚠ **典拠 ID の照合も「図」を見る。** 文章(md)だけを照合していたため、
    #   生成器のべた書きで出る図の冒頭箱に、撤回済みの典拠(天保9年武鑑・「同時代史料2点」)が
    #   生き残っていた(2026-08-25 考証第8巡 高⑤)。**機械照合の死角を残さない。**
    #   ソースを直接走査すると Python の添字 `d["name"]` を拾うので、**出力を見る。**
    head_, tbl_ = sources_index()
    # ⚠ **正典 json も照合の対象にする。** 図と文章だけを見ていたため、
    #   json に略記(`[下丸子]` ほか)が残っていた(2026-08-25 考証第9巡 中)。
    #   ⚠ シリアライズ全体を見ると**配列リテラル `[-13, 80]` を ID と誤認する** —
    #   **文字列の値だけ**を集める。
    _sv = []

    def _collect(o):
        if isinstance(o, dict):
            for k, v in o.items():
                # ⛔ **検分役の覚え書き(`reviews`)は指図の主張ではない。**
                #   ⚠ 2026-09-06、考証方の note の略記 `[山脇][西澄寺]` を「台帳に無い ID」と
                #   誤検出した。あれは**検分の記録**で、⛔ 呼んだ側が書き換えてよい物ではない
                #   (git のコミット件名を照合から外したのと同じ理屈)。
                if k in ("retracted", "reviews"):
                    continue
                _collect(v)
        elif isinstance(o, list):
            for v in o:
                _collect(v)
        elif isinstance(o, str):
            _sv.append(o)
    _collect(d)
    # ⚠ **実装も ID・確度の照合に入れる。** 禁句表の網には足したが ID の網には入れておらず、
    #   片肺だった(2026-08-25 考証第11巡 中)。実装ヘッダは `[ID]確度` の対を持つ。
    # ⚠ ソース全体を見ると配列の添字 `[i + 1]` を ID と誤認するので、**コメントだけ**を取る
    #   (json で配列リテラルを拾ったのと同じ型)。
    _impl_cmt = "\n".join(m.group(1) for m in re.finditer(r"//(.*)", _impl_text()))
    # ⛔ **値どうしを地続きに繋がない。**⚠ 素の "\n" で連結すると、ある値の末尾
    #   (`src` の `[西川1959]`)と次の値の先頭(`certs` の `"B"`)が `[ID]\s*確度` の形に
    #   化けて**偽の不一致**になる(2026-09-06、`roof.certs` を要素別に分けた巡で発覚)。
    #   ⇒ **区切り記号を挟む**。⛔ 検査の網は緩めない — 繋ぎ目だけを断つ。
    SEP = "\n\u241f\n"
    txt_ = (re.sub(r"<[^>]+>", " ", body) + SEP + SEP.join(_sv)
            + SEP + _impl_cmt)
    # 典拠 ID に「,」は入らない(図中の軸ラベル `[s(m), 標高]` を拾わないため)
    ids_ = set(i for i in re.findall(r"\[([^\]\n]{2,24})\]", txt_) if "," not in i)
    miss2 = sorted(i for i in ids_ if i not in head_ and i not in tbl_)
    if miss2:
        print("⚠ 台帳に無い典拠 ID(図)%d 件: %s" % (len(miss2), " / ".join(miss2)))
        sys.exit(2)
    # ⚠ **確度の文字も照合する。** 「台帳に在るか」しか見ていなかったため、
    #   [福井図] を A で引いていた(台帳は B・図の目測)のを人力で見つけていた
    #   (2026-08-25 考証第10巡 中)。⚠ 当図での用途の確度は台帳と意図的に違うことがあるので、
    #   **`[ID]` の直後に letter を置く形だけ**を見る(`=` や「として」を伴う分解表記は除く)。
    cbad = []
    for m4 in re.finditer(r"\[([^\]\n]{2,24})\]\s*\(?([SABPU?])\)?(?![A-Za-z0-9])", txt_):
        _id, _c = m4.group(1), m4.group(2)
        if "," in _id or _id not in head_:
            continue
        if head_[_id] != _c:
            # ⭐ **どこかを示す**(規則16)。⛔ ID だけでは本文のどこか分からない。
            cbad.append("[%s] を %s で引いているが台帳は %s — 前後「…%s…」"
                        % (_id, _c, head_[_id],
                           re.sub(r"\s+", " ", txt_[max(0, m4.start() - 60):m4.end() + 30])))
    cbad = sorted(set(cbad))
    if cbad:
        print("⚠ 台帳と確度が食い違う典拠 %d 件:" % len(cbad))
        for b in cbad:
            print("   ", b)
        sys.exit(2)
    print("wrote %s (%.0f KB) — 図版 %d 面 — 建蔽率 %.1f%%" % (OUT, os.path.getsize(OUT) / 1024, _SVN[0], kp))
    if bad:
        print("⚠ 重なり %d 件 — 検図の前に直すこと" % len(bad))
    print("  run: 検図(edo-kosho / edo-kenzu) → ユーザーのレビュー → 実装 → 突き合わせ")


if __name__ == "__main__":
    main()
