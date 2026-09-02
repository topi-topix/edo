#!/usr/bin/env python3
"""松平出羽守上屋敷(出雲松江藩)の指図を組む。

    python3 Tools/Sashizu/build_matsudaira_dewa_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/matsudaira_dewa_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/matsudaira_dewa_kosho.md     … 文章の部(人が書く・現況形)

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
import io
import ast
import copy
import inspect
import textwrap
import json, math, os, re, subprocess, html
import zlib as _zlib

import sashizu_lib
from sashizu_lib import (R, _pat, _SVN, Proj, RGrid, slope_table, links_table,
                         _edge_dir, mune_contacts_table,  # バイト同一を実証済みの共通部
                         overlap_check)  # 検査の正典(2026-08-26 統一)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "matsudaira_dewa_sashizu.json")
MD = os.path.join(DOC, "matsudaira_dewa_kosho.md")
OUT = os.path.join(DOC, "matsudaira_dewa_sashizu.html")
TSUBO = 3.305785


# ---------------------------------------------------------------- markdown(正典は sashizu_lib)
def inline(s):
    """方言なし(2026-08-26 に md 側の行跨ぎ・不対応の ** を直し、厳しい既定へ寄せた)。"""
    return sashizu_lib.inline(s)


def md2html(text):
    return sashizu_lib.md2html(text, inline=inline)


# ---------------------------------------------------------------- 作図の土台


def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, label),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.65"/>'
            '</pattern></defs>' % _SVN[0]]


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


class LabelSet(object):
    """**引き出し線でラベルを散らす。**⛔ 団子にしない(2026-09-01 庭方の図の指摘3)。

    ⚠ SVG には自動レイアウトが無いので、置き場所は自分で解く。
    `add()` で「指す点」と文字を溜め、`out()` が**重ならない位置まで下へ送って**、
    元の点から引き出し線を引く。⛔ 文字だけ動かして線を引かないと、どれがどれか分からなくなる。"""

    def __init__(self, step=10.5, pad=1.5):
        self.q = []
        self.step = step
        self.pad = pad

    def add(self, ax, ay, text, fs=9.0, fill=None, dx=6.0, dy=-3.0, anchor="start"):
        if text:
            self.q.append((ax, ay, text, fs, fill, dx, dy, anchor))

    def out(self, leader="var(--ink-lo)"):
        g, placed = [], []
        for (ax, ay, tx, fs, fill, dx, dy, anchor) in sorted(self.q, key=lambda z: (z[1], z[0])):
            w = len(tx) * fs * 0.86 + 2.0
            x, y = ax + dx, ay + dy
            x0 = x if anchor == "start" else x - w
            k = 0
            while k < 60 and any(not (x0 + w + self.pad < r[0] or r[2] + self.pad < x0
                                      or y + 2 + self.pad < r[1] or r[3] + self.pad < y - fs)
                                 for r in placed):
                y += self.step
                k += 1
            placed.append((x0, y - fs, x0 + w, y + 2))
            if abs(y - (ay + dy)) > 1.0:
                g.append(LN(ax, ay, x0 if anchor == "start" else x0 + w,
                            y - fs * 0.34, leader, 0.6, "2 2", 0.75))
            g.append(T(x, y, tx, "jo", anchor, fs, fill))
        return g


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
sashizu_lib.MUNE_JA = MUNE_JA  # lib の mune_contacts_table が引く棟名辞書を差す
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
    suso = []   # 旧「堀端の裾の整地帯」。天端9.2 の run は現存しない(2026-08-24 削除)
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

    # 中仕切塀(奥郭の結界)
    for w in d.get("nakajikiri", []):
        a2, b2 = w["a"], w["b"]
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--hei)" '
                 'stroke-width="2.0" stroke-dasharray="9 3" opacity="0.9"/>'
                 % (pr.X(a2[0]), pr.Y(a2[1]), pr.X(b2[0]), pr.Y(b2[1])))

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
            # 身舎 = 外形から**入側のある辺だけ**一間を除く。
            # ⚠ 四方決め打ちだと、妻に入側の無い棟(表向)で入側の帯が嘘の場所に描かれる。
            iri = m.get("iri", ["u0", "u1", "v0", "v1"])
            mu0 = m["u0"] + (1 if "u0" in iri else 0)
            mu1 = m["u1"] - (1 if "u1" in iri else 0)
            mv0 = m["v0"] + (1 if "v0" in iri else 0)
            mv1 = m["v1"] - (1 if "v1" in iri else 0)
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

    # 段の縁の始末は**実装(EdoMatsudairaDewaBuilder.DesignY)と同じ規則**で描く。
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
        """施工後の地盤。実装の DesignY と同じ三層 + **築山の盛土** − **御泉水の掘削**。"""
        y = design_at0(w)
        return None if y is None else y - _pond_depth(d, *_grid_pt(w))

    def design_at0(w):
        # ⭐ 築山は段でも法面でもない「盛る物」なので、どの層より先に見る
        #   (⛔ ここを入れないと断面と切盛図に築山が出ず、土量が図に現れない = 規則3 違反)
        gq = _grid_pt(w)
        for tk in d.get("tsukiyama", []):
            ty = _tk_y(d, tk, gq[0], gq[1],
                       lambda a, b: _nat_uv(_terr_json(), round(a), round(b)))
            if ty is not None:
                base = None
                for a, b, y in segs:
                    if a - 1e-6 <= w <= b + 1e-6:
                        base = y
                return ty if base is None else max(ty, base)
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
        _dp, _rn, n_st = kaidan_dr(d, k)
        rise = _dp / n_st
        tread = _rn / n_st / ken                           # m → 間
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
        _rs = seat_at(run, run.get("_sHit", run["s0"]))
        if _rs > gy + 0.05:                   # 基壇石垣
            g.append(R(X(w) - sx * 0.9, Y(_rs), sx * 1.8, (_rs - gy) * sx * ex,
                       fill=_pat(), stroke="var(--ishi)", sw=1.0))
        g.append(R(X(w) - sx * 0.7, Y(_rs + hh), sx * 1.4, hh * sx * ex,
                   fill=KC.get(run["kind"], "var(--dim)"), op=0.95))
        g.append(T(X(w), Y(_rs + hh) - 5, "%s %.1f" % (run["name"], _rs), "jo", "middle"))

    # 表門(断面Aのみ)
    if sec["axis"] == "u" and abs(sec["at"]) < 2:
        gpn = d["gate"]["plan"]
        g.append(R(X(0) - sx * gpn["monD"] / 2 / K, Y(d["gate"]["sill"] + gpn["monH"]),
                   sx * gpn["monD"] / K * 2, gpn["monH"] * sx * ex,
                   fill="var(--shu-lo)", stroke="var(--shu)", sw=1.6))
        g.append(T(X(0), Y(d["gate"]["sill"] + gpn["monH"]) - 5, "表門", "anG", "middle"))

    # ---- 御泉水 — **水面と護岸石をこの断面にも描く**(2026-09-02 庭方 中5)
    #      ⛔ 従前は掘削(地盤の線)しか出ておらず、注記が「水面 26.05 がこの断面に出る」と
    #      書いているのに **図に水面の線も護岸石も1本も無かった**(文章が図の代わりをしていた)。
    ks_ = d.get("sensui")
    if ks_:
        wy_ = float(ks_["pond"]["waterY"])
        wet = [w for w in ws if _pond_water(d, *_grid_pt(w)) is not None]
        if wet:
            wa, wb = min(wet), max(wet)
            g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#5b86a8" '
                     'opacity="0.55"/>'
                     % (X(wa), Y(wy_), X(wb) - X(wa), max(1.0, Y(y0) - Y(wy_))))
            g.append(LN(X(wa), Y(wy_), X(wb), Y(wy_), "#3f6a80", 2.0))
            g.append(T((X(wa) + X(wb)) / 2, Y(wy_) - 4,
                       "御泉水の水面 %.2fm(底 %.2fm・垂直掘り)"
                       % (wy_, float(ks_["pond"]["floorY"])), "jo", "middle"))
            # 護岸石(汀の両端)— 見え面は水面から `bands[].topAbove` まで
            bands_ = [b for b in gogan_bands(d) if b["pitch"] > 0]
            if bands_:
                tp = bands_[0]["topY"][0]
                for wx in (wa, wb):
                    g.append(R(X(wx) - 2.4, Y(tp[1]), 4.8,
                               max(1.0, Y(wy_) - Y(tp[1])), fill="#8f8a6e", op=1.0))
                g.append(T(X(wb) + 5, Y(tp[1]) - 3,
                           "護岸石の天端 %.2f〜%.2fm" % (tp[0], tp[1]), "jo", "start"))

    # 端の囲い(polygon との交点に立つ run)
    #   ⚠ **注記(`_`)はここへ流さない** — 左右へ同じ長文を出していて重なって読めなかった
    #     (2026-09-02 庭方 中5)。⭕ 注記は図版の下のキャプションが受ける。
    g.append(T(4, 15, sec["name"], "anS"))
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
    # ⭐ **駒は伸縮しない**(裁定U 2026-08-29)。基壇は天端から丈 piece[1] の箱で、
    #   地盤より下は地中。図の下端はその底まで取る — 埋まり具合が見えないと裁定が図に映らない。
    IGH = d["ishigaki"]["piece"][1]
    _btm = [min(r.get("seat0", r["seat"]), r.get("seat1", r["seat"])) - IGH
            for r in d["runs"] if r.get("base") == "Ishigaki"]
    y0 = min([min(seats), gmin] + _btm) - 1.0
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
        # 石垣の駒(丈 IGH で一定・伸縮しない)。天端から下ろした箱の全体を薄く描き、
        # そのうち地盤から上に出ている分だけを濃く塗る = 露出は「埋まり具合」の帰結。
        if r.get("base") == "Ishigaki":
            _a = seat_at(r, r["s0"]); _b = seat_at(r, r["s1"])
            g.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" '
                     'fill="var(--ishi)" opacity="0.13" stroke="var(--ishi)" '
                     'stroke-width="0.7" stroke-dasharray="3 3"/>'
                     % (xa, Y(_a), xb, Y(_b), xb, Y(_b - IGH), xa, Y(_a - IGH)))
        # 石垣基壇の見え掛かり: seat から地盤まで(地盤が seat より上=埋まりは描かない)
        if prof:
            nsm = 8
            base = []
            for k in range(nsm + 1):
                s_ = r["s0"] + (r["s1"] - r["s0"]) * k / float(nsm)
                gy = gY(r["edge"], s_)
                t_ = tt(r["edge"], s_)
                if t_ < ta - 1e-6:
                    t_ += total
                base.append((X(t_), Y(min(gy, seat_at(r, t_))) if gy is not None else Y(seat_at(r, t_))))
            pts = "%.1f,%.1f " % (xa, Y(r["seat0"] if "seat0" in r else r["seat"])) + \
                  " ".join("%.1f,%.1f" % p for p in base) + \
                  " %.1f,%.1f" % (xb, Y(r["seat1"] if "seat1" in r else r["seat"]))
            g.append('<polygon points="%s" fill="var(--ishi)" opacity="0.45"/>' % pts)
        _ym = max(r.get("seat0", r["seat"]), r.get("seat1", r["seat"]))
        g.append(R(xa, Y(_ym + h), xb - xa, h * sx * ex, fill=KC.get(r["kind"], "var(--dim)"), op=0.9))
        if r.get("nijukai"):
            w2 = min(20 * 1.818, r["s1"] - r["s0"]) * sx
            x2 = xa if ta < total / 2 else xb - w2      # 二階は門寄り(展開の起点=表門)
            g.append(R(x2, Y(r["seat"] + nagH + 2.6), w2, 2.6 * sx * ex,
                       fill=KC["Nagaya"], op=0.65))
            lab.append((x2, "門翼二階(海鼠壁)"))
        _s0 = r.get("seat0", r["seat"]); _s1 = r.get("seat1", r["seat"])
        g.append(T((xa + xb) / 2, Y((_s0 + _s1) / 2) + 11,
                   ("%.1f" % _s0) if abs(_s1 - _s0) < 0.01 else ("%.1f→%.1f" % (_s0, _s1)),
                   "jo", "middle"))
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
               "濃い塗り=石垣の見え掛かり(天端と地盤の間)、破線の薄い箱=地中に埋まる分" % (nagH, dob),
               "anS2", "start"))
    g.append(T(4, H - 8, "石垣の駒は伸縮させない(丈 %.2fm で一定)。天端は面が決め、駒は天端から"
               "丈のぶん下ろすだけ — 露出の高低は埋まり具合の差であって石の大きさの差ではない。"
               "北辺中央の鞍部でその露出が最大になる。練塀の浅い折れは留め継ぎの隅部材で納める"
               "(角度は現地が決める)" % IGH, "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


def ishigaki_detail_svg(d, edge, s0, s1, label):
    """石垣の割り付けの詳細図(実寸)。**駒は伸縮させない**【裁定U 2026-08-29】

    ⛔ 展開図(全長 600m)では駒の継ぎ目が 3px 間隔になって読めない。詳細設計は
      詳細の縮尺でしか描けないので、継ぎ目が問題になった区間を実寸で切り出す。
    """
    ig = d["ishigaki"]
    W, IGH = ig["piece"][2], ig["piece"][1]
    prof = (d.get("edgeProfiles") or {}).get(str(edge), [])
    rs = [r for r in d["runs"] if r["edge"] == edge and r["s1"] > s0 and r["s0"] < s1]
    rs.sort(key=lambda r: r["s0"])
    Wpx, HEAD, FOOT = 900.0, 30.0, 76.0
    sx = Wpx / (s1 - s0)
    tops = [seat_at(r, max(r["s0"], s0)) for r in rs] + [seat_at(r, min(r["s1"], s1)) for r in rs]
    yt = max(tops) + 0.8
    yb = min(t - IGH for t in tops) - 0.8
    H = (yt - yb) * sx + HEAD + FOOT

    def X(s): return (s - s0) * sx
    def Y(y): return HEAD + (yt - y) * sx

    def gy(s):
        if not prof:
            return None
        if s <= prof[0][0]:
            return prof[0][1]
        for i in range(len(prof) - 1):
            (sa, ya), (sb, yb_) = prof[i], prof[i + 1]
            if sa <= s <= sb:
                return ya + (yb_ - ya) * (s - sa) / max(1e-6, sb - sa)
        return prof[-1][1]

    g = _sv(Wpx, H, "石垣基壇の割り付け(%s)" % label)
    for r in rs:
        N, pitch, ov, end, over = ishigaki_layout(d, r)
        for i in range(N):
            ps = r["s0"] + i * pitch
            if ps + W < s0 or ps > s1:
                continue
            g.append(R(X(ps), Y(seat_at(r, min(max(ps, r["s0"]), r["s1"]))), W * sx, IGH * sx,
                       fill="var(--ishi)", stroke="var(--ink)", sw=0.7,
                       op=0.16 if i % 2 else 0.26))
        # 天端(座)
        g.append(LN(X(max(r["s0"], s0)), Y(seat_at(r, max(r["s0"], s0))),
                    X(min(r["s1"], s1)), Y(seat_at(r, min(r["s1"], s1))),
                    "var(--shu)", 2.0))
        xa_, xb_ = X(max(r["s0"], s0)), X(min(r["s1"], s1))
        if xb_ - xa_ >= 70.0:            # 窓の端で切れた run に札を重ねない
            _t = "%s ／ 駒%d枚・重なり%.2fm" % (r["name"], N, ov)
            g.append(T((xa_ + xb_) / 2, Y(seat_at(r, (r["s0"] + r["s1"]) / 2)) - 6,
                       _t, "jo", "middle", fit(_t, xb_ - xa_, 10.0)))
        # run の境(= 隣の run の駒とここで重なる)
        for sx_ in (r["s0"], r["s1"]):
            if s0 - 1e-6 <= sx_ <= s1 + 1e-6:
                g.append(LN(X(sx_), Y(yt), X(sx_), Y(yb), "var(--shu)", 0.9, dash="4 3", op=0.7))
    # 地盤(区画線上の現地形【P】)
    if prof:
        pts = []
        k = 0
        while True:
            s_ = s0 + 0.5 * k
            if s_ > s1:
                s_ = s1
            pts.append((X(s_), Y(gy(s_))))
            if s_ >= s1:
                break
            k += 1
        g.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4"/>'
                 % " ".join("%.1f,%.1f" % p for p in pts))
    # 目盛(辺沿い走り s)
    k = int(math.ceil(s0 / 5.0)) * 5
    while k <= s1:
        g.append(LN(X(k), Y(yb), X(k), Y(yb) - 5, "var(--dim)", 0.8))
        g.append(T(X(k), Y(yb) + 12, "s%d" % k, "jo", "middle"))
        k += 5
    g.append(T(4, H - 40, "%s ／ 辺%d の s%.1f〜%.1f を実寸で。駒 = %.2f(厚)×%.2f(丈)×%.2f(走り)m・"
               "scale=1 で固定。" % (label, edge, s0, s1, ig["piece"][0], IGH, W), "anS2", "start"))
    g.append(T(4, H - 26, "濃淡は駒の交互。重なりは run ごとに pitch=(L−W)/(N−1) で割り付けるので"
               "常に %.2fm 以上あり、隙間は出ない。破線=run の境。" % ig["overlapMin"], "anS2", "start"))
    g.append(T(4, H - 12, "太線=天端(座)、細線=区画線上の現地形【P】。"
               "駒の底は天端−%.2fm で一定 — 地面より下は地中に埋まる。" % IGH, "anS2", "start"))
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


def runs_table(d):
    """⭐ 基壇の欄は**割り付けの結果**(枚数・重なり・露出)を出す。設計値は持たない —
    駒の作法は `ishigaki` の一箇所だけで、run 側に規模の欄は無い【裁定U 2026-08-29】。"""
    rows = []
    tot = 0
    for r in d["runs"]:
        if r.get("base") == "Ishigaki":
            N, pitch, ov, end, over = ishigaki_layout(d, r)
            lo, hi = ishigaki_exposure(d, r)
            tot += N
            base = "駒 %d枚・重なり %.2f" % (N, ov)
            expo = ("%.2f〜%.2f" % (lo, hi)) if lo is not None else "—"
        else:
            base, expo = "—", "—"
        rows.append("<tr><td><code>%s</code></td><td>辺%d</td><td>%.0f–%.0f</td><td>%.1fm</td>"
                    "<td>%s</td><td>%.1f</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                    % (r["name"], r["edge"], r["s0"], r["s1"], r["s1"] - r["s0"],
                       "表長屋" if r["kind"] == "Nagaya" else "練塀", r["seat"],
                       base, expo, "整地" if r.get("bench") else "—"))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>辺</th><th>走り s</th><th>長さ</th>'
            "<th>種別</th><th>天端 seat</th><th>石垣基壇の割り付け</th><th>露出 m</th>"
            "<th>外周帯</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>"
            "<p class='cap'>基壇の欄は割り付けの<b>結果</b>(生成器が <code>ishigaki</code> の作法から算出)。"
            "駒は全周で同じ大きさ・同じ丈で、run ごとに拡大縮小しない。石垣の駒は計 %d 枚。</p></div>" % tot)


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
    """正典は sashizu_lib.kenpei。行ラベル(付属屋の顔ぶれ)だけが当邸の値。
    番所は count×w×d(json の count=2 が正典 — 旧実装の直書き 2 と同値)。"""
    return sashizu_lib.kenpei(
        d, area, TSUBO,
        svc_label="付属屋(蔵・作事・茶屋・稲荷)",
        nagaya_label="表長屋(奥行%.1fm)" % d["const"]["nagayaD"],
        ban_label="番所・隅櫓・門の躯体")


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

    def covered(u0, v0, u1, v1, y, poly=None):
        """⚠ `poly` を持つ庭は矩形ではない — 外接箱の外の点まで検めると偽陽性になる。"""
        uu = u0 + 0.25
        while uu < u1:
            vv = v0 + 0.25
            while vv < v1:
                if poly and not _pip_world((uu, vv), poly):
                    vv += 0.5
                    continue
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
        pt = covered(g["u0"], g["v0"], g["u1"], g["v1"], None,
                     [tuple(p) for p in g["poly"]] if g.get("poly") else None)
        if pt:
            bad.append("%s(庭) が段の外: (%.2f, %.2f)" % (g["name"], pt[0], pt[1]))
    for w in d["wells"]:
        pt = covered(w["u"] - 0.5, w["v"] - 0.5, w["u"] + 0.5, w["v"] + 0.5, None)
        if pt:
            bad.append("%s(井戸) が段の外: (%.2f, %.2f)" % (w["name"], pt[0], pt[1]))
    bad += run_seat_check(d)
    bad += route_pierce_check(d)
    bad += route_grade_check(d, _dem_json())
    bad += room_containment_check(d)
    bad += barrier_check(d)
    bad += kaidan_ground_check(d)
    bad += hardcode_check()
    bad += komon_sill_check(d)
    bad += neishi_check(d, _dem_json())
    bad += gate_overlap_check(d)
    bad += fuzoku_overlap_check(d)
    bad += yagura_opening_check(d)
    bad += program_check(d)
    bad += setchin_check(d)
    bad += edge_treatment_check(d)
    bad += outside_bury_check(d)
    bad += terrain_provenance_check(d)
    bad += parcel_containment_check(d)
    bad += vocab_check(d)
    bad += schema_check(d)
    bad += perimeter_closure_check(d)
    bad += perimeter_ledger_check(d)
    bad += mune_wall_clearance_check(d)
    bad += joints_check(d)
    bad += kado_stock_check(d)
    bad += kado_arm_check(d)
    bad += ishigaki_layout_check(d)
    bad += viewpoint_check(d)
    bad += tsukiyama_check(d)
    bad += sensui_check(d)
    bad += gogan_check(d)
    # ⭐ **2026-09-02(第4次・検図 高1)に配線した。**⛔ この2本は書かれていたのに
    #   `plane_check` の束にも `main()` の WARN にも入っておらず、**素の設計を報告する経路が
    #   0回**だった(呼ばれるのは `planting_sensitivity` の感度試験の中だけ)。
    #   破壊試験で枝2を落差ゼロに戻しても HTML の ⚠ が動かなかったのはこのため。
    #   → 同型の再発は `check_wiring_check` が見張る。
    bad += mizu_check(d)
    bad += taki_check(d)
    bad += cert_claim_check(d)
    bad += check_wiring_check()
    bad += kaki_crossing_check(d)
    bad += group_place_check(d)
    bad += group_pack_check(d)
    bad += crown_fallback_check(d)
    bad += garden_access_check(d)
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
    地盤は matsudaira_dewa_terrain.json(造成前)から読む。埋没(地盤>天端)は即不可、
    浮きは石垣基壇 4.0×s で受けられる範囲まで許す。"""
    try:
        terr = json.load(open(os.path.join(DOC, "matsudaira_dewa_terrain.json"), encoding="utf-8"))
    except Exception as ex:
        # ⛔ **`return []` にしない。** 地盤が読めないのは「合格」ではなく「**回っていない**」。
        #   土井が同じ形を自邸で8本見つけた(2026-08-26 EDO-0029)。当方も2本あった。
        #   `qa-and-pitfalls.md`「測れないものは 0 件になる」。
        return ["matsudaira_dewa_terrain.json が読めず **この検査は回っていない**(合格ではない): %s" % ex]
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
        # 基壇が受けられる高さ = **駒の丈そのもの**(駒は伸縮させない裁定U 2026-08-29)。
        # ⛔ run ごとの縮尺から導かない — その欄はもう無い。数値は json の `ishigaki` が正典。
        cap = d["ishigaki"]["piece"][1]
        if worstB > tol:
            out.append("%s(天端%.1f→%.1f) の背後の地盤が %.2fm 高い = 塀が埋まる" % (r["name"], y0, y1, worstB))
        elif r.get("base") == "Ishigaki" and worstF > cap:
            out.append("%s(天端%.1f→%.1f) が %.2fm 浮くが石垣の駒は丈 %.2fm しか無い"
                       % (r["name"], y0, y1, worstF, cap))
        elif r.get("base") != "Ishigaki" and worstF > tol:
            out.append("%s(天端%.1f) が %.2fm 浮くのに石垣基壇が無い" % (r["name"], r["seat"], worstF))
    return out


# overlap_check の正典は sashizu_lib(2026-08-26 統一。井戸・表門辺の run 帯・段どうし・
# 竹垣の貫通なども見る土井基準の版。当邸の「庭⊃庭の包含は可」もそこに取り込んだ)。


def nakajikiri_containment_check(d, n=200):
    """中仕切塀が**区画の外へ出ていない**か。線分の端点だけでなく途中も測る。

    ⚠ 2026-08-27 にユーザーが図を見て見つけた(奥郭の南の板塀が 15.5m はみ出していた)。
      区画の南辺は u-18 付近で内側(v63.03)へ切れ込むので、v=66 の一本では途中だけが外へ出る。
      **端点は両方とも区画の中にあった** — だから端点検査では捕まらない。"""
    gr = RGrid(d)
    P = d["polygon"]

    def pip(x, y):
        c, m = False, len(P)
        for i in range(m):
            (x1, y1), (x2, y2) = P[i], P[(i + 1) % m]
            if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
                c = not c
        return c

    bad = []
    for w in d.get("nakajikiri", []):
        a, b = w["a"], w["b"]
        outs = []
        for i in range(n + 1):
            t = i / float(n)
            u, v = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            W = gr.W(u, v)
            if not pip(W[0], W[1]):
                outs.append((u, v))
        if outs:
            L = math.hypot(b[0] - a[0], b[1] - a[1]) * len(outs) / float(n + 1) * d["const"]["ken"]
            bad.append("中仕切 %s が区画の外を %.1fm 通る(u %.2f〜%.2f)"
                       % (w["name"], L, outs[0][0], outs[-1][0]))
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
        # 身舎(外形から**入側のある辺だけ**一間を除いた内側)に収まるか。
        # ⚠ 入側の辺は棟ごとに違う(2026-08-27 — 表向は南北の二辺のみ。妻には回さない)。
        #   四方決め打ちで測ると、妻に入側の無い棟が全室「食い込む」と鳴る。
        iri = m.get("iri", ["u0", "u1", "v0", "v1"])
        lo_u = m["u0"] + (1 if "u0" in iri else 0)
        hi_u = m["u1"] - (1 if "u1" in iri else 0)
        lo_v = m["v0"] + (1 if "v0" in iri else 0)
        hi_v = m["v1"] - (1 if "v1" in iri else 0)
        for r in m.get("rooms", []):
            if (r["u0"] < lo_u or r["u1"] > hi_u or r["v0"] < lo_v or r["v1"] > hi_v):
                bad.append("室 %s(%s)が入側の帯に食い込む" % (r["name"], m["name"]))
    return bad


def seat_at(r, s_):
    """run の天端。**斜面 run は seat0→seat1 で一直線に下るので、seat(中点)を平らに読まない。**
    2026-08-24 検図: 展開図・断面・取り合い表が seat 単独読みで、
    存在しない段差を計 13.4m 実装用の表に指示していた。"""
    y0 = r.get("seat0", r["seat"]); y1 = r.get("seat1", r["seat"])
    if abs(r["s1"] - r["s0"]) < 1e-9:
        return y0
    t = max(0.0, min(1.0, (s_ - r["s0"]) / (r["s1"] - r["s0"])))
    return y0 + (y1 - y0) * t


# ------------------------------------------------ 石垣基壇 — 駒は伸縮させない【U 2026-08-29】


def ishigaki_layout(d, r):
    """run を石垣の駒で覆う割り付け。**駒は伸縮させない**(scale=1)。

    ⛔ ここに数値を書かない。作法の正典は json の `ishigaki`。
    戻り値 (N, pitch, overlap, end, over):
      N=枚数 / pitch=ピボット間隔 / overlap=継ぎ目の重なり / end=最後の駒の端 / over=s1 からのはみ出し
    """
    ig = d["ishigaki"]
    W, PM = ig["piece"][2], ig["pitchMax"]
    L = r["s1"] - r["s0"]
    if L <= W + 1e-9:                                   # 駒1枚がはみ出して覆う(重なりは可)
        return 1, 0.0, 0.0, r["s0"] + W, r["s0"] + W - r["s1"]
    N = int(math.ceil((L - W) / PM - 1e-9)) + 1
    pitch = (L - W) / (N - 1)
    return N, pitch, W - pitch, r["s0"] + (N - 1) * pitch + W, 0.0


def ishigaki_exposure(d, r, nsm=40):
    """run の石垣の露出高さ(座 − 区画線上の地盤)の最小・最大。地盤は edgeProfiles【P】。"""
    prof = d.get("edgeProfiles") or {}
    arr = prof.get(str(r["edge"]))
    if not arr:
        return None, None
    def gy(s):
        if s <= arr[0][0]:
            return arr[0][1]
        for i in range(len(arr) - 1):
            (sa, ya), (sb, yb) = arr[i], arr[i + 1]
            if sa <= s <= sb:
                return ya + (yb - ya) * (s - sa) / max(1e-6, sb - sa)
        return arr[-1][1]
    ex = [seat_at(r, r["s0"] + (r["s1"] - r["s0"]) * k / float(nsm)) -
          gy(r["s0"] + (r["s1"] - r["s0"]) * k / float(nsm)) for k in range(nsm + 1)]
    return min(ex), max(ex)


def ishigaki_layout_check(d, tol=0.001):
    """**駒の割り付けが run をちょうど覆うか。**【ユーザー裁定U 2026-08-29】

    裁定は三つ — ①駒の XYZ の長さは変えない ②run の長さは**重なり**で合わせる
    ③高さは**地面への埋まり具合**で合わせる。それぞれに対応して:

    (a) 覆い   — 最後の駒の端が s1 に乗るか(誤差 1mm)。N=1 の run は s1 を越えてはみ出すのが正で、
                 **届かない**(端が s1 に足りない)のだけを鳴らす。
                 ⭐ あわせて **run の全長を 5cm 刻みで走査し、どの点も駒の箱の中にあるか**を見る。
                 これは割り付けの式とは別口の確かめで、式が壊れれば必ず穴が出る
                 (式の値を式で検算すると恒真になる — 感度試験の probe③ がここを鳴らす)。
    (b) 継ぎ目 — 重なりが overlapMin 以上・overlapMax 以下か。かつ**枚数が最小**か
                 (1枚減らすと届かない)。⚠ run が 2W−overlapMax より短いと overlapMax は
                 幾何的に達成できないので、そこは「重なり = 2W−L ちょうど・枚数は2」を求める
                 (**これは割り付けの式から従う不変条件の言明**で、データを壊しても鳴らない。
                 短小 run が現に何本あるかを図と表に出すのが役目)。
                 ⛔ 上限を一律に緩めない — 緩めると駒を無駄に重ねる割り付けが素通りする
                 (感度試験の probe⑧ がこの分岐を鳴らす)。
    (c) 露出   — 座 − 地盤が 0 から piece[1](駒の丈)の間か。丈を超えると駒が地面に届かず
                 塀の足元が浮く。exposeSplit を超えるものは図自身の『露出が◯m を超える手前で
                 run を割る』に反する。**run 全体が地中**(最大露出 ≤ 0)なら基壇そのものが無用。

    ⛔ さらに、run が駒の規模(`s` / `ishi` / `tiers`)を持ち直していないかを見る —
       持たせた瞬間に「run ごとに石の大きさが変わる」旧作法へ戻るため。

    ⚠ **実装は run を開口(門・小門)で割ってから同じ式で並べる。**だから run が開口をまたいで
      いると図の枚数と実装の枚数が食い違う。そこは `gate_overlap_check` が別に見張っている
      ので、ここでは二重に測らない(同じ事実を二つの検査に持たせない)。
    """
    ig = d["ishigaki"]
    W, H = ig["piece"][2], ig["piece"][1]
    PM, OMIN, OMAX = ig["pitchMax"], ig["overlapMin"], ig["overlapMax"]
    SPL = ig["exposeSplit"]
    bad = []
    if abs(ig.get("scale", 1.0) - 1.0) > 1e-9:
        bad.append("`ishigaki.scale` が %.3f — 駒は伸縮させない裁定なので 1.0 以外は不可"
                   % ig.get("scale", 1.0))
    if W - PM < OMIN - tol:
        bad.append("pitchMax %.2f では重なりが %.2fm しか出ない(overlapMin %.2fm)"
                   % (PM, W - PM, OMIN))
    for r in d["runs"]:
        nm, e = r["name"], r["edge"]
        for k in ("s", "ishi", "tiers"):
            if k in r and r.get("base") == "Ishigaki":
                bad.append("%s(辺%d)が駒の規模 `%s` を持っている — 駒は伸縮させない裁定"
                           "(作法は `ishigaki` に一箇所だけ置く)" % (nm, e, k))
        if r.get("base") != "Ishigaki":
            continue
        L = r["s1"] - r["s0"]
        N, pitch, ov, end, over = ishigaki_layout(d, r)
        # (a) 覆い
        if N == 1:
            if end < r["s1"] - tol:
                bad.append("%s(辺%d s%.2f〜%.2f)が駒1枚で届かない(端 %.2f)"
                           % (nm, e, r["s0"], r["s1"], end))
        elif abs(end - r["s1"]) > tol:
            bad.append("%s(辺%d s%.2f〜%.2f)の最後の駒の端が %.3f で s1 に乗らない(差 %.3fm)"
                       % (nm, e, r["s0"], r["s1"], end, end - r["s1"]))
        # (a') 据えた駒の箱を並べ、全長を走査して穴が無いかを**式と別口で**確かめる
        boxes = [(r["s0"] + i * pitch, r["s0"] + i * pitch + W) for i in range(N)]
        holes = []
        k, s_ = 0, r["s0"]
        while s_ <= r["s1"] + 1e-9:
            if not any(b0 - tol <= s_ <= b1 + tol for b0, b1 in boxes):
                holes.append(s_)
            k += 1
            s_ = r["s0"] + 0.05 * k
        if holes:
            bad.append("%s(辺%d)の割り付けに穴が %d 点(s=%.2f〜%.2f)— 駒が届いていない"
                       % (nm, e, len(holes), holes[0], holes[-1]))
        # (b) 継ぎ目
        if N >= 2:
            if pitch > PM + tol:
                bad.append("%s(辺%d)のピッチ %.3fm が上限 %.2fm を超える = 隙間が空く"
                           % (nm, e, pitch, PM))
            if ov < OMIN - tol:
                bad.append("%s(辺%d)の重なり %.3fm が %.2fm を下回る" % (nm, e, ov, OMIN))
            if (N - 2) * PM + W >= L - tol:
                bad.append("%s(辺%d L=%.2f)の駒が %d 枚 — %d 枚で届くので1枚多い"
                           % (nm, e, L, N, N - 1))
            if L >= 2 * W - OMAX - tol:
                if ov > OMAX + tol:
                    bad.append("%s(辺%d)の重なり %.3fm が上限 %.2fm を超える"
                               % (nm, e, ov, OMAX))
            elif abs(ov - (2 * W - L)) > tol or N != 2:
                bad.append("%s(辺%d L=%.2f)は短小 run(2W−overlapMax=%.2f 未満)なので "
                           "駒2枚・重なり %.2fm ちょうどで納めること(いま %d枚・%.3fm)"
                           % (nm, e, L, 2 * W - OMAX, 2 * W - L, N, ov))
        # (c) 露出
        lo, hi = ishigaki_exposure(d, r)
        if lo is None:
            bad.append("%s(辺%d)の地盤が edgeProfiles に無く**露出を測れていない**"
                       "(合格ではない)" % (nm, e))
            continue
        if hi > H + tol:
            bad.append("%s(辺%d)の露出 %.2fm が駒の丈 %.2fm を超える = 足元が地面に届かない"
                       % (nm, e, hi, H))
        elif hi > SPL + tol:
            bad.append("%s(辺%d)の露出 %.2fm が %.2fm を超える — 手前で run を割ること"
                       % (nm, e, hi, SPL))
        if hi <= tol:
            bad.append("%s(辺%d)は全長が地中(最大露出 %.2fm)— 基壇 `base` は要らない"
                       % (nm, e, hi))
    return bad


def ishigaki_layout_sensitivity(d):
    """**感度試験** — わざと壊して `ishigaki_layout_check` が鳴るか。

    ⚠ 検査を足したら必ずこれを通す。恒真の検査は 0 件を出し続けるので、
    「0 件」が「回っている」ことの証明にならない(qa-and-pitfalls「測れないものは 0 件になる」)。
    """
    import copy
    base = len(ishigaki_layout_check(d))
    out = []

    def probe(label, mutate):
        m = copy.deepcopy(d)
        mutate(m)
        n = len(ishigaki_layout_check(m))
        out.append((label, n - base))

    def _first(m):
        return next(r for r in m["runs"] if r.get("base") == "Ishigaki" and
                    r["s1"] - r["s0"] > 6.0)

    probe("① 駒を伸縮させる(scale 1.0→1.4)",
          lambda m: m["ishigaki"].__setitem__("scale", 1.4))
    probe("② run に駒の規模 `s` を持たせる(旧作法への逆戻り)",
          lambda m: _first(m).__setitem__("s", 0.4))
    probe("③ ピッチ上限を駒の走りより長くする(継ぎ目に隙間が空く)",
          lambda m: m["ishigaki"].__setitem__("pitchMax", 2.4))
    probe("④ 重なりの下限を駒が出せる値より上げる",
          lambda m: m["ishigaki"].__setitem__("overlapMin", 0.25))
    probe("⑤ 座を 3.0m 持ち上げて露出を駒の丈より高くする",
          lambda m: [r.update(seat=r["seat"] + 3.0, seat0=r.get("seat0", r["seat"]) + 3.0,
                              seat1=r.get("seat1", r["seat"]) + 3.0) for r in [_first(m)]])
    probe("⑥ 座を 5.0m 下げて run を丸ごと地中に沈める",
          lambda m: [r.update(seat=r["seat"] - 5.0, seat0=r.get("seat0", r["seat"]) - 5.0,
                              seat1=r.get("seat1", r["seat"]) - 5.0) for r in [_first(m)]])
    probe("⑦ 地盤(edgeProfiles)を消して露出を測れなくする",
          lambda m: m.__setitem__("edgeProfiles", {}))
    probe("⑧ 重なりの上限を下げる(駒を無駄に重ねる割り付けを許さない)",
          lambda m: m["ishigaki"].__setitem__("overlapMax", 0.20))
    return base, out


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


# 附属屋・井戸・隅櫓・中仕切塀の実寸(m)。**軒の出を含む外形**。
# 部材を作り直して寸法が変わったら、ここも直す(build_matsudaira_dewa_fuzokuya.py の報告値)。
FUZOKU_SIZE = {
    "Kura1": (13.76, 8.89), "Kura2": (13.76, 8.89), "Kura3": (13.76, 8.89),
    "Sakuji": (19.32, 8.99), "Chatei": (6.55, 6.55), "Inari": (3.34, 2.50),
}
IDO_SIZE = (1.90, 1.90)
YAGURA_OUTER = 7.394        # 隅櫓の軒の出を含む外形(build_matsudaira_dewa_fuzokuya.py の報告値)
NJ_THICK = 0.25


def fuzoku_overlap_check(d):
    """郭内の造作(附属屋・井戸・中仕切塀)が互いに、また棟・廊下と食い込んでいないか。

    ⚠ **(u,v) グリッドの上で測る。** Unity の world AABB で測ってはいけない —
    回転間グリッドは斜めなので、13.8×8.9m の箱の AABB が 16.0×13.1m に膨らみ、
    実際には 4.7m 離れている蔵と厩が「食い込み」と出る(2026-08-25 に偽陽性5件)。
    """
    ken = d["const"]["ken"]
    boxes = []
    for s in d["service"]:
        ku, kv = s["u1"] - s["u0"], s["v1"] - s["v0"]
        cu, cv = (s["u0"] + s["u1"]) / 2.0, (s["v0"] + s["v1"]) / 2.0
        L, S = FUZOKU_SIZE.get(s["name"], (ku * ken, kv * ken))
        au, av = (S, L) if kv >= ku else (L, S)
        boxes.append((s["name"], "附属屋", cu - au / 2 / ken, cv - av / 2 / ken,
                      cu + au / 2 / ken, cv + av / 2 / ken))
    for w in d["wells"]:
        hu = IDO_SIZE[0] / 2 / ken
        boxes.append((w["name"], "井戸", w["u"] - hu, w["v"] - hu, w["u"] + hu, w["v"] + hu))
    for m in d["munes"]:
        boxes.append((m["name"], "棟", m["u0"], m["v0"], m["u1"], m["v1"]))
    for l in d["links"]:
        boxes.append((l["name"], "廊下", l["u0"], l["v0"], l["u1"], l["v1"]))
    for w in d["nakajikiri"]:
        a, b = w["a"], w["b"]
        t = NJ_THICK / ken / 2.0
        if abs(a[0] - b[0]) < 1e-9:
            boxes.append((w["name"], "中仕切", a[0] - t, min(a[1], b[1]), a[0] + t, max(a[1], b[1])))
        else:
            boxes.append((w["name"], "中仕切", min(a[0], b[0]), a[1] - t, max(a[0], b[0]), a[1] + t))
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, k1, a0, b0, a1, b1 = boxes[i]
            n2, k2, c0, e0, c1, e1 = boxes[j]
            ou = min(a1, c1) - max(a0, c0)
            ov = min(b1, e1) - max(b0, e0)
            if ou <= 0.06 or ov <= 0.06:
                continue
            # 御殿どうしは overlap_check の担当。中仕切の隅の突き合わせ(≤0.2間)は継ぎ手
            if k1 in ("棟", "廊下") and k2 in ("棟", "廊下"):
                continue
            if k1 == k2 == "中仕切" and max(ou, ov) < 0.2:
                continue
            if "Kido" in n1 or "Kido" in n2:      # 庭木戸は塀の線の上に乗るのが正
                continue
            bad.append("%s(%s) と %s(%s) が %.2f×%.2f 間(%.2f×%.2f m)食い込む"
                       % (n1, k1, n2, k2, ou, ov, ou * ken, ov * ken))
    return bad


def yagura_opening_check(d):
    """隅櫓の footprint を両側の辺へ射影し、外周の run がそこを塞いでいないか。

    ⚠ 「頂点から一定距離を空ける」では足りない。隅が直角でないと、櫓の四角は
    片方の辺と斜めに交わるので**左右で必要な開口が違う**(当邸は内角106°で 7.0 と 6.0)。
    2026-08-25: 開口ゼロで 6.7×5.4×5.7m 食い込み、3.5m ずつ空けてもまだ足りなかった。
    """
    P = d["polygon"]
    n = len(P)
    ken = d["const"]["ken"]
    bad = []
    for y in d.get("yagura", []):
        vi = y["vertex"]
        gA, gB = y.get("gapA"), y.get("gapB")
        if gA is None or gB is None:
            bad.append("隅櫓 %s に gapA/gapB(外周の開口)が無い" % y["name"])
            continue
        p = P[vi % n]
        a, b = P[(vi - 1) % n], P[(vi + 1) % n]

        def unit(v):
            m = math.hypot(v[0], v[1])
            return (v[0] / m, v[1] / m)

        da = unit((a[0] - p[0], a[1] - p[1]))
        db = unit((b[0] - p[0], b[1] - p[1]))
        bis = unit((da[0] + db[0], da[1] + db[1]))
        half = math.acos(max(-1.0, min(1.0, da[0] * bis[0] + da[1] * bis[1])))
        body = y["ken"] * ken
        inset = (body / 2 + 0.30) / max(0.35, math.sin(half))
        c = (p[0] + bis[0] * inset, p[1] + bis[1] * inset)
        outer = YAGURA_OUTER / 2.0                  # 軒の出を含む半幅
        ax, ay = db, (-db[1], db[0])                # 櫓の軸は辺 vi に沿う
        cor = [(c[0] + sx * outer * ax[0] + sy * outer * ay[0],
                c[1] + sx * outer * ax[1] + sy * outer * ay[1])
               for sx in (-1, 1) for sy in (-1, 1)]
        L13 = math.hypot(a[0] - p[0], a[1] - p[1])
        s_in = [L13 - ((q[0] - p[0]) * da[0] + (q[1] - p[1]) * da[1]) for q in cor]
        s_out = [(q[0] - p[0]) * db[0] + (q[1] - p[1]) * db[1] for q in cor]
        needA, needB = L13 - min(s_in), max(s_out)
        if gA + 1e-6 < needA:
            bad.append("隅櫓 %s: 辺%d の開口 %.1fm では足りない(櫓は %.2fm 要る)"
                       % (y["name"], (vi - 1) % n, gA, needA))
        if gB + 1e-6 < needB:
            bad.append("隅櫓 %s: 辺%d の開口 %.1fm では足りない(櫓は %.2fm 要る)"
                       % (y["name"], vi, gB, needB))
        # ⚠ 2026-08-29(EDO-0053)に**測るものを直した**。旧版は「開口の中に run が
        #   一本でも入っていたら不可」で、開口を空のまま保つことを求めていた。
        #   だが必要なのは「櫓と**ぶつからない**こと」であって、開口を空けることではない。
        #   その取り違えのせいで、隅の左右に 1.4m と 1.6m の穴が空いたまま合格していた
        #   (ユーザーが #6/#7 で発見)。躯体が深い長屋は入らないが、厚 1.15m の練塀は入る。
        #   → 実際の平面形どうしの重なりで測る。`qa-and-pitfalls.md`「検査の文言と実装の集合」。
        def _yq(hw):
            return [(c[0] + sx * hw * ax[0] + sy * hw * ay[0],
                     c[1] + sx * hw * ax[1] + sy * hw * ay[1])
                    for sx, sy in ((-1, -1), (-1, 1), (1, 1), (1, -1))]
        # 長屋(躯体が深く背も高い)は**軒を含む外形**と、練塀(丈 2.65m)は**躯体**と
        # 当たり判定する。塀は櫓の軒の下へ入ってよい(取り付く)。
        yq_out, yq_body = _yq(outer), _yq(body / 2.0)
        for r in d["runs"]:
            if r["edge"] not in ((vi - 1) % n, vi):
                continue
            rq = _run_quad(d, r)
            tgt = yq_out if r["kind"] == "Nagaya" else yq_body
            if _convex_overlap(yq_out if r["kind"] == "Nagaya" else tgt, rq):
                bad.append("隅櫓 %s: run %s(%s)が櫓の%sと当たる — 辺%d s%.1f〜%.1f"
                           % (y["name"], r["name"], r["kind"],
                              "外形(軒共)" if r["kind"] == "Nagaya" else "躯体",
                              r["edge"], r["s0"], r["s1"]))
    return bad


ANCHOR_MD = os.path.expanduser(
    "~/.claude/skills/unity-buke-yashiki/references/estate-types.md")


def anchor_roles():
    """`estate-types.md` の「上屋敷が備える役割」表 → [(役割, 要否)]。

    ⚠ **外の錨。** 各邸の json だけを見ていると、役割と棟を**同時に消せば検査が通る**
    (土井 EDO-0013 / 検図14巡 中-6: 表役所・米蔵・土蔵・稲荷が同時削除で無音だった)。
    行の書式は `| 役割 | 要否 | 典拠 |`。崩れたら空を返すのではなく**落とす**。
    """
    with io.open(ANCHOR_MD, encoding="utf-8") as f:
        txt = f.read()
    i = txt.find("上屋敷が備える役割")
    if i < 0:
        raise RuntimeError("錨の節が estate-types.md に無い: 上屋敷が備える役割")
    rows = []
    for ln in txt[i:].splitlines():
        c = [x.strip() for x in ln.strip().strip("|").split("|")] if ln.strip().startswith("|") else None
        if c is None:
            if rows and not ln.strip():
                continue
            if rows and ln.startswith("#"):
                break
            continue
        if len(c) != 3 or c[0] in ("役割",) or set(c[0]) <= set("-: "):
            continue
        rows.append((c[0], c[1]))
    # 床は **20行**。⚠ 表は 24 行あり、床10 では 22 行しか読めていなくても素通りする
    #   (土井の実例。行を落とす壊れ方は「ファイルも表も行も在る」ので最も静かに壊れる)。
    if len(rows) < 20:
        raise RuntimeError("錨の表が %d 行しか読めない(床20・表は24行)。"
                           "行の書式 | 役割 | 要否 | 典拠 | を崩さないこと" % len(rows))
    return rows


# 語彙で振り分ける欄。**(欄の名, 許す値, 欄が要るか)**。
# ⚠ 「無い」と「知らない値」を分ける(土井 2026-08-26)。`base` や `gardens.kind` のように
#   正当に欄が無い行があるので、不在まで鳴らすと偽陽性の山になる。
VOCAB = [
    ("runs",       "kind",  {"Nagaya", "Dobei"},                       True),
    ("runs",       "base",  {"Ishigaki", ""},                          False),
    ("links",      "kind",  {"渡廊下", "御錠口", "御膳所口"},              True),
    ("nakajikiri", "kind",  {"板塀", "庭木戸"},                          True),
    ("kaidans",    "dir",   {"+u", "-u", "+v", "-v"},                  True),
    ("fuchi",      "kind",  {"切石縁石"},                               True),
    ("fuchi",      "line",  {"u", "v"},                                True),
    ("program",    "state", {"有", "無", "兼用"},                        True),
    ("gardens",    "kind",  {"shirasu"},                               False),
]


def vocab_check(d):
    """語彙で振り分ける欄に**知らない値**が入っていないか。

    ⚠ 誰も鳴らないまま数字が変わる。実測(2026-08-26):
    `runs[].kind` を `"Nagaya "`(末尾に空白)にすると表長屋10本が計算から消え、
    **建蔽率が 19.2% → 16.5%** に落ちて指摘が 0 件のまま図が出た。
    分岐が `== "Nagaya"` や `KC.get(kind, 既定)` の形をしているので、
    知らない値は**静かに「その他」へ倒れる**(土井 EDO-0033)。

    ⛔ 「欄が無い」と「知らない値が入っている」を分ける。前者は正当なことがある。
    """
    bad = []
    for key, field, allow, need in VOCAB:
        for i, o in enumerate(d.get(key, [])):
            nm = o.get("name", "#%d" % i)
            if field not in o:
                if need:
                    bad.append("%s の %s に `%s` が無い" % (key, nm, field))
                continue
            v = o[field]
            if v not in allow:
                bad.append("%s の %s の `%s` が知らない値 %r — 許すのは %s"
                           "(語彙の欄は分岐が既定値へ静かに倒れる)"
                           % (key, nm, field, v, "/".join(sorted(x for x in allow if x))))
    # 区画は `zones` の裁定と突き合わせる(setchin_check と同じ集合を二重に持たない)
    dz = set(d.get("zones", []))
    for m in d["munes"]:
        if "zone" not in m:
            bad.append("棟 %s に `zone` が無い" % m["name"])
        elif dz and m["zone"] not in dz:
            bad.append("棟 %s の `zone` が知らない値 %r — zones の裁定は %s"
                       % (m["name"], m["zone"], "/".join(sorted(dz))))
    return bad


def need_level(need):
    """要否の欄(自然文)を 必須 / 望ましい / 任意 のどれかに分類する。分からなければ None。

    ⚠ **接頭辞の白名簿にしない。**「上屋敷は必須」「奥向があれば必須」のように条件が前に付く。
    ⛔ 分類できないものを黙って「任意」に落とすと、台帳の言い回しが増えた日に静かに免除される。
    """
    t = need.replace(" ", "").replace("　", "")
    if "必須" in t:
        return "必須"
    if "望ましい" in t:
        return "望ましい"
    if "任意" in t:
        return "任意"
    return None


def program_check(d):
    """在るべき役割が在るか。**外の錨(estate-types.md)と突き合わせる。**

    2026-08-26: この検査を入れて初めて **雪隠が一室も無い**ことが出た(湯殿だけ在った)。
    土井も同じ穴を14巡目まで抱えており、錨の無い自己検図では構造的に見えない。
    """
    CERT = ("S", "A", "B", "P", "U", "?")

    def _cert_ok(v):
        """⭐ **確度は割って書ける。**「A(位置・現存門の型式)/ B(安政3年への外挿)」のように
        **根拠ごとに割る**書き方を考証方が求めている(2026-09-01 中2)。
        ⛔ 素の1文字しか許さないと、割って書いた行が『確度が無い』と鳴る。
        ⭕ `/` で割った**どの部分も** S/A/B/P/U/? のいずれかで始まっていればよい。"""
        if not isinstance(v, str) or not v.strip():
            return False
        for part in v.split("/"):
            t = part.strip()
            if not t or not t.startswith(CERT):
                return False
        return True

    prog = d.get("program")
    if not prog:
        return ["program(在るべき役割の照合表)が無い — 外の錨と突き合わせられない"]
    have = set(o["name"] for o in d["munes"] + d.get("service", []))
    have |= set(w["name"] for w in d.get("wells", []))
    have |= set(r["name"] for r in d.get("runs", []))
    have |= set(g["name"] for g in d.get("gardens", []))
    have |= set(l["name"] for l in d.get("links", []))
    have |= set(r["name"] for r in d.get("rails", []))
    have |= set(y["name"] for y in d.get("yagura", []))
    if d.get("gate"):
        have.add("gate")
    bad = []
    mine = {p["role"]: p for p in prog}
    for role, need in anchor_roles():
        pg = mine.get(role)
        if pg is None:
            bad.append("役割「%s」(%s)が program に無い — 錨の行を落としている" % (role, need))
            continue
        lv = need_level(need)
        if lv is None:
            # ⛔ **黙って任意に落とさない。**要否の欄は自然文で書かれるので、
            #   接頭辞の白名簿にすると台帳の言い回しが増えた日に静かに免除される
            #   (土井 2026-08-26: 正規表現の先頭一致で『上屋敷は必須』『奥向があれば必須』の
            #   2行を読み飛ばし、24役割のうち22しか見ていなかった)。
            bad.append("役割「%s」の要否『%s』を分類できない — "
                       "台帳の言い回しが増えたか書式が崩れている(黙って任意に落とさない)" % (role, need))
        elif lv == "必須":
            if pg["state"].strip("*") == "無":
                bad.append("役割「%s」は %s だが指図に無い" % (role, need))
        if pg["state"].strip("*") == "無" and len(pg.get("note", "")) < 20:
            bad.append("役割「%s」を落としているのに理由が書かれていない" % role)
        if not _cert_ok(pg.get("cert")):
            bad.append("役割「%s」に確度が無い(規則6)" % role)
        miss = [n for n in pg.get("by", []) if n not in have]
        if miss:
            bad.append("役割「%s」が挙げる %s が指図に無い" % (role, "・".join(miss[:4])))
        if pg["state"].strip("*") == "有" and not pg.get("by"):
            bad.append("役割「%s」が『有』なのに満たす物(by)が空" % role)
    extra = set(mine) - set(r for r, _ in anchor_roles())
    for e in sorted(extra):
        p = mine[e]
        # ⭐ **『無』の行は数を水増しできない。**錨に無い役割でも、`state` が「無」で
        #   落とした理由と確度を持つなら、それは**不在の宣言**であって自作の水増しではない
        #   (2026-09-01 松平「池泉」— 基準年次の図に池の印が無いという裁定を役割表に載せた)。
        #   ⛔ 「有」「兼用」で錨に無いものは従来どおり鳴らす。
        #   ⛔ この免除は「錨に足さなくてよい」という意味ではない — 錨(estate-types.md)へ
        #      昇格させるかは**全邸に効く**ので、掲示板で裁定を仰ぐこと。
        if p.get("state", "").strip("*") == "無" and len(p.get("note", "")) >= 20 \
                and _cert_ok(p.get("cert")):
            continue
        bad.append("役割「%s」は錨の表に無い — 自作の役割で数を水増ししていないか" % e)
    return bad


def anchor_separate():
    """`estate-types.md` の「**別の区画に属す役割**: A / B / …」の行を読む。

    ⚠ **集合そのものを自邸の生成器に持たない。** 初版はここに tuple を直書きしていたが、
    それでは錨が**自分で書き換えられる場所**に残り、連鎖が一段しか外へ出ていない
    (土井 EDO-0029 の5段の表 ⑤)。台帳は他邸と共有で当邸だけでは変えられない。
    """
    with io.open(ANCHOR_MD, encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("**別の区画に属す役割**"):
                body = ln.split(":", 1)[1] if ":" in ln else ln.split("**", 2)[-1]
                got = tuple(x.strip() for x in body.replace("／", "/").split("/") if x.strip())
                # 床は **4個**(台帳の集合は6個。3個だと 6→3 に削って通ってしまう)。
                # ⚠ 床は「行が崩れた」を拾う煙感知器であって、意図的に削られる道を塞ぐものではない。
                #   削るほうは**名前が役割表の行に在ること**で押さえる。
                if len(got) < 4:
                    raise RuntimeError("『別の区画に属す役割』が %d 個しかない(床4): %r" % (len(got), ln))
                roles = set(r for r, _ in anchor_roles())
                unknown = [x for x in got if x not in roles]
                if unknown:
                    raise RuntimeError("『別の区画に属す役割』の %s が役割表に無い — "
                                       "台帳の中で名前が食い違っている" % "・".join(unknown))
                return got
    raise RuntimeError("『別の区画に属す役割』の行が estate-types.md に無い")


TERRAIN_TOL = 0.30      # 回転間格子の地形と正本DEMの許容差[m](格子の刻みの違いによる補間差)


def parcel_containment_check(d):
    """段・庭・棟・附属屋が**区画の中に収まっているか**。

    ⚠ はみ出しは `design_y` が区画でクリップされるので**実害が出ない**。
    そのぶん**気づけない** — 実際に松平では `ShukakuE` が宣言 u[19,112] に対し
    区画が u≈64 までしかなく、**東半分 6,295m²(面の50.3%)が敷地の外**だった。
    はみ出した面の上では地盤が引けないので、**地盤を読む検査すべての標本が黙って減る**
    (土井が同型を自邸で発見、2026-08-26)。

    棟・附属屋は 1 セルでも外に出たら不可(建物が隣地に建つ)。
    段・庭は区画線が斜めに切るぶんを許すが、面の 1% を超えたら宣言が実体と合っていない。
    """
    G = RGrid(d)
    P = d["polygon"]
    n = len(P)

    def pip(x, z):
        c = False
        for i in range(n):
            x1, z1 = P[i]
            x2, z2 = P[i - 1]
            if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
                c = not c
        return c

    ken = d["const"]["ken"]
    STEP = 0.5
    bad = []
    groups = [("段", d["terraces"], 0.01), ("庭", d["gardens"], 0.01),
              ("棟", d["munes"], 0.0), ("附属屋", d["service"], 0.0)]
    for kind, items, tol in groups:
        for b in items:
            inn = out = 0
            pol = [tuple(p) for p in b["poly"]] if b.get("poly") else None
            v = b["v0"]
            while v <= b["v1"] + 1e-9:
                u = b["u0"]
                while u <= b["u1"] + 1e-9:
                    if pol and not _pip_world((u, v), pol):
                        u += STEP
                        continue
                    x, z = G.W(u, v)
                    if pip(x, z):
                        inn += 1
                    else:
                        out += 1
                    u += STEP
                v += STEP
            if out and out > (inn + out) * tol:
                area = out * (STEP * ken) ** 2
                bad.append("%s %s が区画から %.0f m²(%.1f%%)はみ出す — "
                           "宣言の矩形が実体と合っていない(地盤を読む検査の標本が黙って減る)"
                           % (kind, b["name"], area, 100.0 * out / (inn + out)))
    return bad


def terrain_provenance_check(d):
    """回転間格子の地形が **正本 DEM から来ているか**を実測で確かめる(CLAUDE.md 規則12)。

    ⚠ 司令塔の通達(2026-08-24)は「`<屋敷>_terrain.json` は各邸の生成器が作る。
    **種地を正本へ揃えるのは各自の手当て**」と書いている。**手当てを宣言で持たない。**
    `run_seat_check` と `kaidan_ground_check` はこの地形を読むので、種地がずれていれば
    両方の「0件」が意味を失う(2026-08-23 に4邸が live terrain を『造成前』として吸い込んだ事故と同型)。
    """
    try:
        tj = json.load(open(os.path.join(DOC, "matsudaira_dewa_terrain.json"), encoding="utf-8"))
        dem = json.load(open(os.path.join(DOC, "matsudaira_dewa_dem.json"), encoding="utf-8"))
    except Exception as ex:
        return ["地形の出所を照合できない — **この検査は回っていない**(合格ではない): %s" % ex]
    g = d["grid"]["shukaku"]
    ken = d["const"]["ken"]
    x0, z0 = dem["x0"], dem["z0"]
    st = dem.get("step", dem.get("res", 2.0))
    H = dem["h"] if "h" in dem else dem["height"]
    nz, nx = len(H), len(H[0])

    def nat(x, z):
        fx, fz = (x - x0) / st, (z - z0) / st
        i, j = int(math.floor(fx)), int(math.floor(fz))
        if not (0 <= i < nx - 1 and 0 <= j < nz - 1):
            return None
        tx, tz = fx - i, fz - j
        return ((H[j][i] * (1 - tx) + H[j][i + 1] * tx) * (1 - tz)
                + (H[j + 1][i] * (1 - tx) + H[j + 1][i + 1] * tx) * tz)

    # ⚠ **区画が正本の切り出しに収まっているか**(司令塔の通達 2026-08-24 項6:
    #   「切り出しの余白が南13m・北21m と最も薄い。区画を動かすとはみ出す」)。
    #   ⛔ 下の照合ループは `nat()` が None の点を**黙って飛ばす**ので、
    #   はみ出しは「差が小さい」に化けて見えない — 検査の中に同じ穴を作らない。
    P = d["polygon"]
    xs = [q[0] for q in P]
    zs = [q[1] for q in P]
    X1, Z1 = x0 + (nx - 1) * st, z0 + (nz - 1) * st
    margins = [("西", min(xs) - x0), ("東", X1 - max(xs)), ("南", min(zs) - z0), ("北", Z1 - max(zs))]
    short = [(k, m) for k, m in margins if m < 0]
    if short:
        return ["区画が正本 DEM の切り出しからはみ出している(%s)— "
                "`python3 Tools/Sashizu/build_base_dem.py --fit` で切り出しを広げること(規則12)"
                % "・".join("%s %.1fm" % (k, m) for k, m in short)]
    T = tj["h"]
    u0, v0, du = tj["u0"], tj["v0"], tj["step"]
    worst, wu, wv, wa, wb, seen, gap = 0.0, 0, 0, 0.0, 0.0, 0, 0
    for j in range(0, len(T), 3):
        for i in range(0, len(T[0]), 3):
            t = T[j][i]
            if t is None:
                continue
            u, v = u0 + i * du, v0 + j * du
            x = g["x0"] + (g["ux"] * u + g["vx"] * v) * ken
            z = g["z0"] + (g["uz"] * u + g["vz"] * v) * ken
            y = nat(x, z)
            if y is None:
                gap += 1        # ⛔ 黙って飛ばさない。下で数える
                continue
            seen += 1
            if abs(t - y) > worst:
                worst, wu, wv, wa, wb = abs(t - y), u, v, t, y
    if seen < 200:
        return ["地形の照合の標本が %d 点しか取れない — 格子の範囲か正本の切り出しがおかしい" % seen]
    if gap > seen * 0.02:
        return ["回転間格子の %d/%d 点(%.1f%%)が正本 DEM の外に出ている — "
                "切り出しを広げるか格子の範囲を絞ること(規則12)"
                % (gap, gap + seen, 100.0 * gap / (gap + seen))]
    if worst > TERRAIN_TOL:
        return ["回転間格子の地形が正本 DEM と %.2fm 食い違う(u=%.0f v=%.0f: 格子 %.2f / 正本 %.2f)— "
                "**種地が正本から来ていない**。live terrain を吸っていないか(規則12)"
                % (worst, wu, wv, wa, wb)]
    return []


BURY_MAX = 0.30         # 外側の地盤が座より高くてよい量[m](埋没)
FLOAT_MAX = 0.35        # 基壇を持たない run の足元が地盤から浮いてよい量[m]
ISHI_MAX = 1.00         # 「根石」と呼んでよい高さの上限[m]。超えたら基壇


def outside_bury_check(d):
    """**外側の地盤**が外周の座より高くないか(塀・長屋が外から埋まらないか)。

    ⚠ `_pending.seihoDoro` に「東辺は道の肩が塀の面より最大 1.7m 高く、長屋の基壇が
    道側へ埋まる。見え方は実装後の検証レンダで確認する」と**宣言だけ**が置かれていた。
    2026-08-26 に正本 DEM で測り直すと**最大 +0.30m・超過 0 本**で、
    その心配は既に解消していた。⛔ **宣言は直っても消えない。**
    実測を要求に組み替えて、戻ったときに鳴る形にする(土井 EDO-0029)。

    ⚠ 造成前の地盤(`<屋敷>_dem.json` = 正本の切り出し)で測る。live terrain は使わない(規則12)。
    """
    try:
        dem = json.load(open(os.path.join(DOC, "matsudaira_dewa_dem.json"), encoding="utf-8"))
    except Exception:
        return ["matsudaira_dewa_dem.json が読めない — 外側の埋没を測れない(測れないものは0件になる)"]
    x0, z0 = dem["x0"], dem["z0"]
    step = dem.get("step", dem.get("res", 2.0))
    H = dem["h"] if "h" in dem else dem["height"]
    nz, nx = len(H), len(H[0])

    def nat(x, z):
        fx, fz = (x - x0) / step, (z - z0) / step
        i, j = int(math.floor(fx)), int(math.floor(fz))
        if not (0 <= i < nx - 1 and 0 <= j < nz - 1):
            return None
        tx, tz = fx - i, fz - j
        return ((H[j][i] * (1 - tx) + H[j][i + 1] * tx) * (1 - tz)
                + (H[j + 1][i] * (1 - tx) + H[j + 1][i + 1] * tx) * tz)

    P = d["polygon"]
    n = len(P)
    g = (sum(p[0] for p in P) / n, sum(p[1] for p in P) / n)
    bad = []
    for r in d["runs"]:
        e = r["edge"] % n
        a, b = P[e], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        nn = (-u[1], u[0])
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if (g[0] - mid[0]) * nn[0] + (g[1] - mid[1]) * nn[1] > 0:
            nn = (-nn[0], -nn[1])
        s0, s1 = r["s0"], r["s1"]
        hi, hs, seen = -9.0, s0, 0
        s = s0
        while s <= s1:
            px = a[0] + u[0] * s + nn[0] * 2.0
            pz = a[1] + u[1] * s + nn[1] * 2.0
            y = nat(px, pz)
            if y is not None:
                seat = seat_at(r, s)
                seen += 1
                if y - seat > hi:
                    hi, hs = y - seat, s
            s += 1.0
        if seen and hi > BURY_MAX:
            bad.append("外周 %s(辺%d)が外側の地盤に %.2fm 埋まる(s=%.0f・上限 %.2fm)— "
                       "座を上げるか、外側を削るか、基壇を足すかを設計値で決めること"
                       % (r["name"], r["edge"], hi, hs, BURY_MAX))
        # ⚠ **両方の符号で測る**(土井 EDO-0027)。埋没だけを見る検査は「浮き」を構造的に見逃す。
        #   2026-08-26: 当方も土井も埋没しか測っておらず、S_Hei_C が 1.56m 浮いたまま
        #   両家の検査が 0 件と報告していた。
        #   基壇(`base`)を持つ run は足元まで石で下ろすので浮きではない ⇒ 除外。
        #   ⚠ 基壇が無くても **根石 `ishi`(高さ[m])** を持つ run はそのぶん受けられる — 数えないと
        #   誤検出する(2026-08-26: S_Hei_Okabe5 の浮き 0.40m は根石 0.30m でほぼ受かる)。
        #   ⛔ `ishi` は**基壇を持たない run だけ**の欄。`base:Ishigaki` の run が持っていたら
        #   それは駒の規模の書き戻しなので `ishigaki_layout_check` が鳴らす。
        if seen and not r.get("base"):
            ishi = float(r.get("ishi", 0.0) or 0.0)
            # ⛔ **免除の名前を替えただけの抜け道を塞ぐ**(土井の指摘 2026-08-26)。
            #   `base` を外して `ishi` を大きく書けば浮きの判定を素通りできてしまう。
            #   根石が背丈を超えたらそれは根石ではなく基壇である。
            if ishi > ISHI_MAX:
                bad.append("外周 %s(辺%d)の根石が %.2fm ある — 背丈(%.2fm)を超える石積みは"
                           "根石でなく**基壇**。`base:Ishigaki` を持たせること"
                           % (r["name"], r["edge"], ishi, ISHI_MAX))
                ishi = ISHI_MAX
            hf, fs = -9e9, s0
            s = s0
            while s <= s1:
                px = a[0] + u[0] * s + nn[0] * 2.0
                pz = a[1] + u[1] * s + nn[1] * 2.0
                y = nat(px, pz)
                if y is not None:
                    dv = seat_at(r, s) - y
                    if dv > hf:
                        hf, fs = dv, s
                s += 1.0
            if hf - ishi > FLOAT_MAX:
                bad.append("外周 %s(辺%d)の足元が %.2fm 浮く(s=%.0f・根石 %.2fm を引いても "
                           "%.2fm・上限 %.2fm)— `base:Ishigaki` を与えるか、座を地盤なりに割ること"
                           % (r["name"], r["edge"], hf, fs, ishi, hf - ishi, FLOAT_MAX))
    return bad


def edge_treatment_check(d):
    """段どうしが接する線が、**全長にわたって**何かで納まっているか。

    ⚠ 0.30m の段差は土留めが要らないので図から抜け落ちる。松平では白洲と主郭の縁 22間 のうち
    石段が 2間 を占めるだけで、残り 20間 が**何も決まっていない**まま
    `_pending` に「縁石か緩い法面か未定」と**宣言だけ**が置かれていた。
    宣言は直さなくても消えないので、要求に組み替える(土井 EDO-0029)。
    """
    ken = d["const"]["ken"]
    segs = []          # (軸, 位置, a, b, 段差)
    T = d["terraces"]
    for i in range(len(T)):
        for j in range(len(T)):
            if i == j:
                continue
            p, q = T[i], T[j]
            dy = abs(p["y"] - q["y"])
            if dy < 1e-6:
                continue
            if abs(p["v1"] - q["v0"]) < 1e-6:
                lo, hi = max(p["u0"], q["u0"]), min(p["u1"], q["u1"])
                if hi - lo > 0.05:
                    segs.append(("v", p["v1"], lo, hi, dy))
            if abs(p["u1"] - q["u0"]) < 1e-6:
                lo, hi = max(p["v0"], q["v0"]), min(p["v1"], q["v1"])
                if hi - lo > 0.05:
                    segs.append(("u", p["u1"], lo, hi, dy))
    def covers(axis, at, a, b):
        """その区間を覆う [a,b) の一覧を石段・縁石・土留めから集める"""
        out = []
        for k in d["kaidans"]:
            if "pos" not in k:
                continue
            ku, kv = k["pos"]
            half = k["w"] / 2.0 / ken
            _rn = kaidan_dr(d, k)[1]
            if axis == "v" and abs(kv - at) <= max(0.5, _rn / ken):
                out.append((ku - half, ku + half))
            if axis == "u" and abs(ku - at) <= max(0.5, _rn / ken):
                out.append((kv - half, kv + half))
        for f in d.get("fuchi", []):
            if f["line"] == axis and abs(f["at"] - at) < 1e-6:
                out.append((min(f["a"], f["b"]), max(f["a"], f["b"])))
        for w in d.get("terraceWalls", []):
            (wa, wb) = w["a"], w["b"]
            if axis == "v" and abs(wa[1] - at) < 1e-6 and abs(wa[1] - wb[1]) < 1e-6:
                out.append((min(wa[0], wb[0]), max(wa[0], wb[0])))
            if axis == "u" and abs(wa[0] - at) < 1e-6 and abs(wa[0] - wb[0]) < 1e-6:
                out.append((min(wa[1], wb[1]), max(wa[1], wb[1])))
        return out
    bad = []
    seen = set()
    for axis, at, a, b, dy in segs:
        key = (axis, round(at, 4), round(a, 4), round(b, 4))
        if key in seen:
            continue
        seen.add(key)
        gaps = [(a, b)]
        for (c0, c1) in covers(axis, at, a, b):
            nxt = []
            for (g0, g1) in gaps:
                if c1 <= g0 or c0 >= g1:
                    nxt.append((g0, g1)); continue
                if c0 > g0:
                    nxt.append((g0, min(c0, g1)))
                if c1 < g1:
                    nxt.append((max(c1, g0), g1))
            gaps = [g for g in nxt if g[1] - g[0] > 0.05]
        if gaps:
            tot = sum(g[1] - g[0] for g in gaps)
            bad.append("段の縁 %s=%g の %.1f間(%.1fm・段差%.2fm)が納まっていない — "
                       "石段・縁石・土留めのどれで受けるか設計値に書くこと(区間 %s)"
                       % (axis, at, tot, tot * ken, dy,
                          "・".join("%g..%g" % g for g in gaps[:3])))
    return bad


def zone_separation_check(d):
    """役割表の別の役割どうしが、同じ区画に同居していないか。

    ⚠ **これが最外の錨。** 「区画ごとに雪隠が在るか」→「区画の宣言を消す」→
    「区画を統合する」→「裁定を消す」と、免除は一段ずつ外へ逃げる。
    止まるのは錨が**自分では書き換えられない場所**へ出たときだけ
    (土井 EDO-0029 / `qa-and-pitfalls.md`「錨の連鎖」)。
    ここでは分離の要求を**共有台帳の役割の名前**から組み立てる。
    """
    sep = anchor_separate()
    zone_of = {m["name"]: m.get("zone") for m in d["munes"]}
    anchor = dict(anchor_roles())
    role_zone = {}
    for pg in d.get("program", []):
        if pg["role"] not in sep or pg["role"] not in anchor:
            continue
        if pg["state"].strip("*") != "有":
            continue
        zs = set(zone_of.get(n) for n in pg.get("by", []) if n in zone_of)
        zs.discard(None)
        if zs:
            role_zone[pg["role"]] = zs
    bad = []
    names = sorted(role_zone)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            share = role_zone[a] & role_zone[b]
            if share:
                bad.append("役割「%s」と「%s」が同じ区画「%s」に同居している — "
                           "雪隠を共用する図になる(役割表がこの二つを別に立てている)"
                           % (a, b, "・".join(sorted(share))))
    return bad


SETCHIN_MAX = 40.0      # 同じ区画の最寄りの雪隠までの上限[m]


def setchin_check(d):
    """雪隠が**区画ごとに**行き渡っているか。土井 EDO-0029 の二段検査に倣う。

    ⚠ **段①だけでは自己免除ができる。** 「区画ごとに雪隠が在るか」だけを見ると、
    区画の宣言を消せば通ってしまう(土井で実際に0件になった)。段②で
    **人の居る棟が必ずどれかの区画に属すこと**を要求してラチェットにする。

    ⚠ 役割の有無(program_check)だけでは足りない。松平は雪隠を4室入れた直後の状態で
    program_check が 0 件だったが、**区画で見ると更に4室足りなかった** —
    表役所の役人の最寄りが 63m 先の**奥向の湯殿**(御錠口の向こう)、
    黒書院の客と賄いの者が**藩主の中奥**、馬役が 47m 先の玄関、という図だった。
    「在るか」ではなく「**区画をまたいで使う図になっていないか**」まで見ること。
    """
    ken = d["const"]["ken"]
    bad = []
    # 段⓪ — **区画の粗さそのものを止める。**
    # ⚠ 感度試験で「区画を統合して逃げる」道が鳴らなかったので `zones` を裁定にしたが、
    #   土井の指摘どおり**それも `zones` を書き換えれば逃げられる**(免除が一段外へ逃げるだけ)。
    #   → 錨を**共有台帳 estate-types.md** の役割表へ出す。台帳は他邸と共有で当邸だけでは
    #   変えられないので、ここで連鎖が止まる(`qa-and-pitfalls.md` の4段の表)。
    declared = d.get("zones")
    if not declared:
        bad.append("zones(区画の裁定)が無い — 区画を統合して雪隠の検査を逃げられる")
    bad += zone_separation_check(d)
    zones = {}
    for m in d["munes"]:
        z = m.get("zone")
        # 段② — 人の居る棟は必ず区画に属す(これが無いと区画を消して逃げられる)
        if not z:
            bad.append("棟 %s に区画(zone)が無い — 区画を消せば雪隠の検査を逃げられる" % m["name"])
            continue
        zones.setdefault(z, {"munes": [], "sek": []})
        zones[z]["munes"].append(m)
        for r in (m.get("rooms") or []):
            if r["name"] == "御雪隠":
                zones[z]["sek"].append(((r["u0"] + r["u1"]) / 2.0, (r["v0"] + r["v1"]) / 2.0))
    if declared:
        for z in declared:
            if z not in zones:
                bad.append("区画「%s」が zones に宣言されているのに棟が一つも属していない — "
                           "区画を溶かしていないか(溶かすなら zones と _zones を直して理由を残す)" % z)
        for z in zones:
            if z not in declared:
                bad.append("区画「%s」が zones に宣言されていない" % z)
    for z, v in sorted(zones.items()):
        # 段① — 区画ごとに雪隠が在るか
        if not v["sek"]:
            bad.append("区画「%s」に雪隠が無い(棟 %s)— 使う者が区画をまたぐ"
                       % (z, "・".join(m["name"] for m in v["munes"])))
            continue
        for m in v["munes"]:
            c = ((m["u0"] + m["u1"]) / 2.0, (m["v0"] + m["v1"]) / 2.0)
            near = min(math.hypot(c[0] - q[0], c[1] - q[1]) * ken for q in v["sek"])
            if near > SETCHIN_MAX:
                bad.append("棟 %s(区画 %s)から同じ区画の雪隠まで %.1fm — 上限 %.0fm"
                           % (m["name"], z, near, SETCHIN_MAX))
    return bad


def barrier_check(d):
    """御錠口の結界。**廊下だけでなく「面として閉じているか」を見る。**
    2026-08-23 検図: 旧版は links しか見ておらず、結界線の帯が16間開いていても合格を出していた
    (西庭を南へ回れば奥御殿の西を素通りできた)。被覆検査を足す。"""
    zone = {m["name"]: m["zone"] for m in d["munes"]}
    bad = []
    for l in d["links"]:
        z = set()
        for m in d["munes"]:
            # ⚠ **接する(重なる/突き付く)ことを要求する。**旧版は ±1間 の緩みを持っており、
            #   結界(v=47.5)の南に立つ奥向どうしの渡廊下が、1間 北の中奥の棟に「触れた」と
            #   判定されて『中奥/奥向を跨ぐ』と鳴っていた(2026-08-26 裁定Aの試作で発覚)。
            #   ⛔ 緩みを残すと、離れている棟まで拾って偽陽性を出す。突き付きは 0 で拾える。
            TOL = 0.05
            if (m["u0"] - TOL <= l["u1"] and l["u0"] <= m["u1"] + TOL
                    and m["v0"] - TOL <= l["v1"] and l["v0"] <= m["v1"] + TOL):
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
            # 長屋門(ユーザー裁定 2026-08-30 案A): 門口を **run の中に開ける** run は
            # 開口で割らない。躯体が門の上を通るのが目的なので、重なりは意図した姿。
            # ⛔ 開口だけの短い長屋部材は作れない(妻2つ+bay で最小およそ 8.8m)。
            mon = r.get("mon")
            if mon and abs(float(mon["s"]) - (a + b) / 2.0) < 0.05 \
                   and abs(float(mon["w"]) - (b - a)) < 0.05:
                continue
            ov = min(r["s1"], b) - max(r["s0"], a)
            if ov > 0.05:
                bad.append("%s が %s(s%.1f〜%.1f)と %.1fm 重なる — 実装は開口で割るので部材が入らない"
                           % (r["name"], nm, a, b, ov))
    return bad


def kaidan_dr(d, k):
    """石段の (落差, 走り[m], 段数)。⭐ **庭の段は導出値**(両端が地形で固定される)。"""
    if k.get("kind") == "庭の段":
        g = garden_step_geom(d, k)
        if g is None:
            return (0.0, 0.0, max(1, int(k["steps"])))
        return (g["drop"], g["run"], g["steps"])
    return (k["drop"], k["run"], max(1, int(k["steps"])))


def garden_step_geom(d, k):
    """**庭の段**の導出。→ {落差, 蹴上, 踏面, 走り, 水平, 両端の標高}

    ⛔ 蹴上・踏面は屋敷の既定(`const.keri` / `const.fumi`)を当てない —
      **両端が地形で固定される**ので段数からの従属値になる(汐見坂の裁定 2026-08-24 と同じ)。
      指図が持つのは **段数 `steps` と両端 `a`/`b`** だけ。"""
    terr = _terr_json()
    dem = _dem_json()
    ya = _ground_uv(d, k["a"][0], k["a"][1], terr, dem)
    yb = _ground_uv(d, k["b"][0], k["b"][1], terr, dem)
    if ya is None or yb is None:
        return None
    # ⭐ **折れ道は `via` で折れ点を持つ**(⛔ 両端の直線距離で走りを測らない)。
    #   2026-09-01: 滝見の道 `K_Takimi` は木戸から (−25.0, 68.5) を経由して V8 へ戻るので、
    #   直線 4.4m に対し実際の走りは 16m — 直線で測ると勾配が 4倍きつく出る。
    path = [tuple(k["a"])] + [tuple(p) for p in (k.get("via") or [])] + [tuple(k["b"])]
    hor = sum(math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
              for i in range(len(path) - 1)) * d["const"]["ken"]
    n = max(1, int(k["steps"]))
    drop = abs(yb - ya)
    return {"y0": min(ya, yb), "y1": max(ya, yb), "drop": drop, "hor": hor,
            "steps": n, "keri": drop / n, "fumi": hor / n, "run": hor}


def garden_steps_table(d):
    rows = ""
    for k in d.get("kaidans", []):
        if k.get("kind") != "庭の段":
            continue
        g = garden_step_geom(d, k)
        if g is None:
            continue
        rows += ("<tr><td>%s%s</td><td>u%.1f v%.1f → u%.1f v%.1f</td>"
                 "<td>%.2f → %.2f m</td><td>%.2f m</td><td>%d 段</td>"
                 "<td><b>%.3f m</b></td><td><b>%.3f m</b></td><td><b>%.3f m</b></td>"
                 "<td>%s</td><td>%.1f m</td><td class='note'>%s</td></tr>"
                 % (k["name"],
                    "<br><span class='note'>★山道の段(帯を当てない)</span>"
                    if k.get("stepRule") is False else "",
                    k["a"][0], k["a"][1], k["b"][0], k["b"][1],
                    g["y0"], g["y1"], g["drop"], g["steps"], g["keri"], g["fumi"],
                    2.0 * g["keri"] + g["fumi"],
                    ("下から %d 段目" % int(k["fumiwake"])) if k.get("fumiwake") else "—",
                    k["w"], inline(k.get("_", ""))))
    if not rows:
        return ""
    gr_ = d["const"].get("gardenStepRule") or {}
    cap = ""
    if gr_:
        cap = ("<p class='cap'>⛔ <b>段を減らしても歩きやすくならない</b> — 両端が地形で固定"
               "されるので<b>蹴上 = H/n・踏面 = L/n が同時に 1/n で動く</b>。減らすと両方が"
               "大きくなり <code>2×蹴上 + 踏面</code> が<b>悪化する</b>。"
               "庭の自然石の段の帯は 蹴上 <b>%.2f〜%.2fm</b>(4〜6寸)・"
               "踏面 <b>%.2f〜%.2fm</b>(1尺2寸〜1尺5寸)で、段数は "
               "<code>n = round((2H + L) / %.2f)</code> の従属値。"
               "⛔ 屋敷の石段の既定(蹴上 0.30 / 踏面 0.45)は<b>真の段</b>の値で、ここには当てない。"
               "⛔ 踏分石を中央に置かない(上下が対称になる)。<br>"
               "★ <b>『山道の段』(<code>stepRule: false</code>)にはこの帯を当てない</b> — "
               "台地の崖を降りる段は<b>両端(平面長と比高)が地形と実測で固定される</b>ので、"
               "<b>蹴上は屋敷の既定のまま踏面が伸びる</b>"
               "(2026-08-24 汐見坂の裁定と同じ扱い。段数は 落差 ÷ <code>const.keri</code> の丸め)。</p>"
               % (gr_["keri"][0], gr_["keri"][1], gr_["fumi"][0], gr_["fumi"][1],
                  gr_["target2RT"]))
    return ("<h3>庭の段 — <b>蹴上・踏面は段数からの従属値</b>(⛔ 屋敷の既定を当てない)</h3>"
            '<div class="tw"><table><thead><tr><th>名</th><th>両端(u,v)</th>'
            "<th>設計地盤</th><th>落差</th><th>段数</th><th>蹴上</th><th>踏面</th>"
            "<th>2×蹴上+踏面</th><th>踏分石</th><th>幅</th>"
            "<th class='note'>注記</th></tr></thead><tbody>%s</tbody></table></div>%s"
            % (rows, cap))


def kaidan_ground_check(d):
    """石段の落差が、その位置の造成前地盤と面の差に合っているか。
    2026-08-23: 御蔵門の石段が『存在しない帯』の上に置かれ、降りた先が窪地になっていた。"""
    try:
        terr = json.load(open(os.path.join(DOC, "matsudaira_dewa_terrain.json"), encoding="utf-8"))
    except Exception as ex:
        # ⛔ **`return []` にしない。** 地盤が読めないのは「合格」ではなく「**回っていない**」。
        #   土井が同じ形を自邸で8本見つけた(2026-08-26 EDO-0029)。当方も2本あった。
        #   `qa-and-pitfalls.md`「測れないものは 0 件になる」。
        return ["matsudaira_dewa_terrain.json が読めず **この検査は回っていない**(合格ではない): %s" % ex]
    bad = []
    for k in d["kaidans"]:
        if "pos" not in k:
            continue
        ku, kv = k["pos"]
        nat = _nat_uv(terr, ku, kv)
        if nat is None:
            continue
        if k.get("kind") == "庭の段":
            # ⭐ **庭の段は郭をつなぐ石段ではない。**⛔ 蹴上・踏面・落差を指図に持たせない —
            #   両端が地形で固定されるので**段数からの従属値**(汐見坂の裁定と同じ扱い)。
            #   地盤は段(terraces)でなく**設計地盤**(築山・池の掘削を織り込んだ面)で読む。
            g = garden_step_geom(d, k)
            if g is None:
                bad.append("庭の段 %s の両端の設計地盤が読めない" % k["name"])
                continue
            for f in ("drop", "keri", "fumi", "run"):
                if f in k:
                    bad.append("庭の段 %s に `%s` が書いてある — **段数からの従属値**なので"
                               "指図に持たせない(規則4。生成器が両端の設計地盤から導く)"
                               % (k["name"], f))
            # ⭐ **庭の自然石の段は屋敷の石段と別物**(庭方 2026-09-01 回答3)。
            #   蹴上 4〜6寸・踏面 1尺2寸〜1尺5寸の帯で見る(⛔ `const.keri` 0.30 を当てない)。
            if k.get("stepRule") is False:
                # ⭐ **庭の段でなく「台地の崖を降りる山道の段」**(2026-09-01 第3次・庭方 高5)。
                #   ⛔ `const.gardenStepRule` の帯は当てない — 両端(平面長と比高)が地形と実測で
                #   固定されるので、蹴上は屋敷の既定のまま**踏面が伸びる**(2026-08-24 汐見坂の裁定)。
                nn = int(round(g["drop"] / d["const"]["keri"]))
                if nn != g["steps"]:
                    bad.append("山道の段 %s: 実測の落差 %.3fm から導く段数は %d 段"
                               "(= round(落差 / `const.keri` %.2f))だが指図は %d 段 — "
                               "設計地盤が動いている。丸め直すこと"
                               % (k["name"], g["drop"], nn, d["const"]["keri"], g["steps"]))
                ori = k.get("orikaeshi")
                if ori is not None and len(k.get("via") or []) != int(ori):
                    bad.append("山道の段 %s: 折返し %s に対して `via`(折れ点)が %d 個 — "
                               "走りが折れ点を通る実長で測れない"
                               % (k["name"], ori, len(k.get("via") or [])))
                continue
            gr_ = d["const"].get("gardenStepRule")
            if gr_ is None:
                bad.append("`const.gardenStepRule` が無く**庭の段の検査が回っていない**"
                           "(合格ではない)")
            else:
                for f, lab in (("keri", "蹴上"), ("fumi", "踏面")):
                    lo, hi = gr_[f]
                    if not (lo - 1e-6 <= g[f] <= hi + 1e-6):
                        bad.append("庭の段 %s: 導いた%s %.3fm が庭の段の帯 %.2f〜%.2fm を"
                                   "外れる — 段数を `n = round((2H + L) / %.2f)` で丸め直すこと"
                                   % (k["name"], lab, g[f], lo, hi, gr_["target2RT"]))
                nn = int(round((2.0 * g["drop"] + g["hor"]) / gr_["target2RT"]))
                if nn != g["steps"]:
                    bad.append("庭の段 %s: 実測から導く段数は %d(= round((2×%.3f + %.3f) / %.2f))"
                               "だが指図は %d 段 — 実測落差が動いている"
                               % (k["name"], nn, g["drop"], g["hor"], gr_["target2RT"], g["steps"]))
                fw = k.get("fumiwake")
                if fw is not None and not (1 < int(fw) < g["steps"]):
                    bad.append("庭の段 %s: 踏分石 `fumiwake` %s が段の内に無い" % (k["name"], fw))
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


def komon_sill_check(d):
    """**門の敷居と、その門の石段の足元が同じ値か。**

    ⚠ 2026-09-01(第3次・検図 中4): 東小門の `komon.sill` 26.20 と `kaidans.K_Komon.y0` 26.10 が
      0.10m 食い違っていた。26.20 を正にすると蹴上が `const.keri` を外れ、
      2026-08-24 に是正した不良(蹴上 0.267m)が戻る。
    ⛔ **同じ事実を二箇所に持たない。**指図が敷居を二度書くなら、値が一致することを機械で見張る。
      `kaidans[].sillOf` が「この段の足元はどの敷居か」を名指しする("gate" / "komon:<名>")。
    ⭐ あわせて**造成前DEM の実測の帯**とも突き合わせる — 敷居は道なりなので、
      門口の外の地盤から離れていたら鳴らす。"""
    bad = []
    P = d["polygon"]
    for k in d.get("kaidans", []):
        ref = k.get("sillOf")
        if not ref:
            continue
        if ref == "gate":
            src, sill, lab = d.get("gate"), (d.get("gate") or {}).get("sill"), "表門 gate.sill"
        elif ref.startswith("komon:"):
            nm = ref.split(":", 1)[1]
            src = next((x for x in d.get("komon", []) if x["name"] == nm), None)
            sill = (src or {}).get("sill")
            lab = "%s komon.sill" % nm
        else:
            bad.append("石段 %s の `sillOf` %r が知らない形" % (k["name"], ref))
            continue
        if src is None or sill is None:
            bad.append("石段 %s の `sillOf` %r が指す敷居が無い" % (k["name"], ref))
            continue
        foot = min(float(k["y0"]), float(k["y1"]))
        if abs(foot - float(sill)) > 1e-6:
            bad.append("%s %.2fm と 石段 %s の足元 %.2fm が %.2fm 食い違う — "
                       "同じ事実を二箇所に持っている(どちらかが古い)"
                       % (lab, float(sill), k["name"], foot, abs(foot - float(sill))))
        n = max(1, int(k["steps"]))
        keri = abs(float(k["y1"]) - float(k["y0"])) / n
        if abs(keri - d["const"]["keri"]) > 0.02:
            bad.append("石段 %s の蹴上 %.3fm が屋敷の石段の既定 %.2fm と合わない — "
                       "敷居か段数のどちらかが誤り"
                       % (k["name"], keri, d["const"]["keri"]))
        # 敷居は道なり。門口の外の造成前地盤の帯に入っているか
        if src.get("edge") is not None and src.get("s") is not None:
            q = edge_pt(P, int(src["edge"]), float(src["s"]))
            a, b = P[int(src["edge"])], P[(int(src["edge"]) + 1) % len(P)]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz)
            if L > 1e-9:
                nx, nz = dz / L, -dx / L
                ys = [_bdem_at(q[0] + nx * o, q[1] + nz * o) for o in (-3, -2, -1, 1, 2, 3)]
                ys = [y for y in ys if y is not None]
                if ys and not (min(ys) - 0.15 <= float(sill) <= max(ys) + 0.15):
                    bad.append("%s %.2fm が門口の外の造成前地盤の帯 %.2f〜%.2fm を外れる"
                               % (lab, float(sill), min(ys), max(ys)))
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


def corners_table(d):
    """外周の隅(区画の頂点)。世界座標・折れ角・両側の run と天端差・納めを設計値から導く。"""
    P = d["polygon"]
    n = len(P)
    yag = {y["vertex"]: y for y in d["yagura"]}
    cjs = _corner_joints(d)
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
        # ⛔ 納めは**取り合い表(joints)の裁定**から引く。ここで種別から推測すると、
        #   図が裁定と別のことを言い出す(2026-08-29)。
        j = cjs.get(i)
        if j is None:
            osame = "—(取り合いの記述が無い)"
        else:
            ai, ao = _kado_arms(d, j)
            osame = "%s ／ 部材 <code>%s</code>(腕 %.2f/%.2f m)" % (
                j["kind"], _kado_name(j) or "—", ai, ao)
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
        # ⚠ 土留めに付く段だけを出していたので、terraceWalls が空になった時点で
        #   この表から石段が1本も消えていた(2026-08-25 是正)。**pos から出す**。
        _ws = [x for x in d["terraceWalls"] if x["name"] == k.get("atWall")]
        if _ws:
            w = _ws[0]
            c = gr.W(w["a"][0], k["gapV"]) if w["a"][0] == w["b"][0] else gr.W(k["gapU"], w["a"][1])
            at = "土留め <code>%s</code> に付く" % w["name"]
        elif "pos" in k:
            c = gr.W(*k["pos"])
            at = "独立(土留めなし)"
        else:
            continue
        rows.append("<tr><td><code>%s</code></td><td>石段 %d段(幅 %.2fm)</td>"
                    "<td>芯 (%.1f, %.1f)</td>"
                    "<td>落差 %.2f・走り %.2fm・蹴上 %.3f／昇り <b>%s</b>・%s</td></tr>"
                    % (k["name"], k["steps"], k["w"], c[0], c[1], kaidan_dr(d, k)[0],
                       kaidan_dr(d, k)[1],
                       kaidan_dr(d, k)[0] / max(1, k["steps"]), k.get("dir", "?"), at))
    for rl in d["rails"]:
        pts = [gr.W(u, v) for u, v in rl["pts"]]
        rows.append("<tr><td><code>%s</code></td><td>竹垣(四つ目垣 h0.9)</td>"
                    "<td class='note'>%s</td><td>法肩から内へ 0.45m</td></tr>"
                    % (rl["name"], " → ".join("(%.1f, %.1f)" % p for p in pts)))
    return ("<h3>郭内の土木の端点</h3><div class='tw'><table><thead><tr><th>名</th><th>種別</th>"
            "<th>世界座標</th><th>寸法</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


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


# ---------------------------------------------------------------- 取り合いの詳細(§3f)
#   全体設計(開口の位置)だけでは実装者は「芯を合わせる」しかできない。
#   ここは **どの面がどの面に接するか** を面の座標で描く詳細設計の図版。
#   ⚠ 2026-08-29(EDO-0053): この図が無かったので、同じ門の左右で 1.66m の食い込みと
#     0.96m の隙間が同時に起きた。


def _opening_span(d, key):
    """開口の (辺, s0, s1, 名, 部材の並び) を設計値から組む。"""
    g = d["gate"]
    if key == "omote":
        sp = g["plan"]["sPos"]
        return (g["edge"], sp["banshoW"][0], sp["banshoE"][1], "表門", sp)
    for k in d["komon"]:
        if k["name"] == key:
            nm = "御蔵門" if k["name"] == "Kuramon" else "東小門"
            return (k["edge"], k["s"] - k["w"] / 2.0, k["s"] + k["w"] / 2.0, nm, None)
    raise KeyError(key)


ES_NAGAYA = 1.818
CAP_W, BAY_W = 1.67561, 1.47823          # 素の実測(obj)。build_nagaya_omote.py と同じ値
EPS_HI, EPS_LO = 0.50, -0.65


def nagaya_eps(L):
    """長さ L[m] の表長屋を起こしたときの (窓割りの本数 k, 無地の壁の詰め ε[m])。
    ⛔ `build_nagaya_omote.py` の solve() と同じ式。**別の式を発明しない** —
       図と生成器が別々に長さを解くと、図だけ通って部材が作れない。"""
    Lo = L / ES_NAGAYA
    best = None
    for k in range(0, 400):
        e = (2 * CAP_W + k * BAY_W - Lo) / (k + 1.0)
        if e < EPS_LO or e > EPS_HI:
            continue
        if best is None or abs(e) < abs(best[1]):
            best = (k, e)
    return (best[0], best[1] * ES_NAGAYA) if best else (None, None)


def _chain_mods(d, ch):
    """鎖の中の**棟の切れ目** s。長さ可変の1本を天端の段ごとに切るだけ(端数は出ない)。"""
    return [ch["s0"]] + [round(p["s1"], 4) for p in ch["pieces"]]


def _joints_at(d, edge, s, tol=0.06):
    return [j for j in d["joints"] if j["edge"] == edge and abs(j["s"] - s) <= tol]


def opening_detail_svg(d, key):
    """開口の取り合い詳細(平面)。上=街路側 / 下=郭の内側。走り s が横軸。"""
    C = d["const"]
    e, o0, o1, nm, sp = _opening_span(d, key)
    wing = 16.5 if key == "omote" else 10.5              # 前後に描く長屋の長さ
    s0, s1 = o0 - wing, o1 + wing
    W = 940.0
    sc = W / (s1 - s0)
    DOUT, DIN = 4.4, 5.6                                 # 外/内に描く奥行[m]
    top = 26.0
    H = top + (DOUT + DIN) * sc + 62.0
    yline = top + DOUT * sc                              # 外周線
    def X(s_): return (s_ - s0) * sc
    def Y(t):  return yline + t * sc                     # t: 内向き+ / 外向き−
    g = _sv(W, H, "%s の取り合い詳細" % nm)
    # 郭の内側・街路側の地
    g.append(R(0, Y(0), W, DIN * sc, fill="var(--pl-main)", op=0.16))
    g.append(T(6, Y(DIN) - 6, "郭の内側", "jo"))
    g.append(T(6, top + 12, "街路側", "jo"))
    # 長屋の鎖(実寸の駒で描く)
    for ch in d["chains"]:
        if ch["edge"] != e:
            continue
        bnd = _chain_mods(d, ch)
        if bnd[-1] < s0 - 0.1 or bnd[0] > s1 + 0.1:
            continue
        g.append(R(X(max(bnd[0], s0)), Y(0), X(min(bnd[-1], s1)) - X(max(bnd[0], s0)),
                   C["nagayaD"] * sc, fill="var(--nagaya)", op=0.55, stroke="var(--ink)", sw=1.2))
        for k, b in enumerate(bnd):
            if not (s0 - 0.01 <= b <= s1 + 0.01):
                continue
            heavy = k in (0, len(bnd) - 1)
            g.append(LN(X(b), Y(0), X(b), Y(C["nagayaD"]), "var(--ink)",
                        2.4 if heavy else 0.9, None, None if heavy else 0.7))
        for p in ch["pieces"]:
            cm = (p["s0"] + p["s1"]) / 2.0
            if s0 + 0.6 < cm < s1 - 0.6:
                g.append(T(X(cm), Y(C["nagayaD"] / 2) + 4, "%.2fm" % p["len"],
                           "anS2", "middle", 10.5))
        lab = "鎖 %s(%.2fm ／ %d本)" % (ch["id"], ch["len"], len(ch["pieces"]))
        cm = min(max((max(bnd[0], s0) + min(bnd[-1], s1)) / 2.0, s0 + 5), s1 - 5)
        g.append(T(X(cm), Y(C["nagayaD"]) + 15, lab, "anS2", "middle"))
    # 練塀・袖塀(開口の外に来ることがある)
    for r in d["runs"]:
        if r["edge"] != e or r["kind"] != "Dobei":
            continue
        a, b = max(r["s0"], s0), min(r["s1"], s1)
        if b - a < 0.05:
            continue
        g.append(R(X(a), Y(-C["dobeiT"] / 2), X(b) - X(a), C["dobeiT"] * sc,
                   fill="var(--hei)", op=0.85, stroke="var(--ink)", sw=1.0))
        g.append(T(X((a + b) / 2), Y(-C["dobeiT"] / 2) - 5, r["name"], "anS2", "middle", 9.5))
    # 門
    if key == "omote":
        gp = d["gate"]["plan"]
        bp = gp["bansho"]
        for tag, col, dep, out in (("banshoW", "var(--dan)", bp["d"], bp["protrude"]),
                                   ("banshoE", "var(--dan)", bp["d"], bp["protrude"]),
                                   ("sodeW", "var(--hei)", C["dobeiT"], C["dobeiT"] / 2),
                                   ("sodeE", "var(--hei)", C["dobeiT"], C["dobeiT"] / 2),
                                   ("mon", "var(--ink-lo)", gp["monD"], gp["monD"] / 2)):
            a, b = sp[tag]
            g.append(R(X(a), Y(-out), X(b) - X(a), dep * sc, fill=col,
                       stroke="var(--ink)", sw=1.3))
            g.append(T(X((a + b) / 2), Y(-out) - 6,
                       {"banshoW": "番所(西)", "banshoE": "番所(東)", "sodeW": "袖塀(西)",
                        "sodeE": "袖塀(東)", "mon": "門柱・冠木"}[tag], "anS2", "middle", 10))
        lf = gp["leaf"]
        a, b = sp["mon"]
        for i, (la, lb) in enumerate(((a, (a + b) / 2), ((a + b) / 2, b))):
            g.append(R(X(la) + 1, Y(0.05), X(lb) - X(la) - 2, 0.22 * sc,
                       fill="var(--shu)", op=0.85))
        g.append(T(X((a + b) / 2), Y(0.05) + 0.22 * sc + 12,
                   "扉 %s(内開き)" % lf["kind"], "anS2", "middle", 10))
    else:
        k = [x for x in d["komon"] if x["name"] == key][0]
        post = 0.36
        for pa in (o0, o1):
            g.append(R(X(pa) - post * sc / 2, Y(-post / 2), post * sc, post * sc,
                       fill="var(--ink)", op=0.95))
        g.append(T(X((o0 + o1) / 2), top + 14, "%s(開口 %.1fm)" % (nm, k["w"]), "anS2", "middle"))
        for la, lb in ((o0, (o0 + o1) / 2), ((o0 + o1) / 2, o1)):
            g.append(R(X(la) + 1, Y(0.05), X(lb) - X(la) - 2, 0.22 * sc, fill="var(--shu)", op=0.85))
        g.append('<path d="M %.1f %.1f A %.1f %.1f 0 0 1 %.1f %.1f" fill="none" '
                 'stroke="var(--shu)" stroke-width="0.9" stroke-dasharray="3 3"/>'
                 % (X(o0 + k["w"] / 2), Y(0.16), (k["w"] / 2) * sc, (k["w"] / 2) * sc,
                    X(o0), Y(0.16 + k["w"] / 2)))
        g.append(T(X((o0 + o1) / 2), Y(0.16 + k["w"] / 2) + 13,
                   "扉 %s" % k["leaf"]["kind"], "anS2", "middle", 10))
    # 外周線
    g.append(LN(0, yline, W, yline, "var(--dim)", 0.9, dash="4 4"))
    # 接する面の指示
    for j in d["joints"]:
        if j["edge"] != e or not (s0 + 0.2 < j["s"] < s1 - 0.2):
            continue
        x = X(j["s"])
        g.append(LN(x, top - 14, x, Y(DIN) - 6, "var(--shu)", 2.0, dash="5 3", op=0.9))
        g.append(T(x, top - 18, "%s %s %+.2f (%.2f‥%.2f)"
                   % (j["id"], j["kind"], j["gap"], j["tol"][0], j["tol"][1]),
                   "anS2", "middle", 10.5, "var(--shu)"))
        g.append(T(x, Y(DIN) + 8, "動く側 = %s" % j["moves"], "anS2", "middle", 9.5))
    g.append(T(6, H - 8, "上=街路側 / 下=郭の内側。走り s は左→右。太い縦線=接する面(妻面・小口・門柱の外面)。"
                         "駒の記号 C=中部材 / L・R=妻部材(妻は 0.155m 狭い)。", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


def corner_detail_svg(d, v, span=17.0, title=""):
    """隅の取り合い詳細(平面・世界座標)。囲いの平面形を実寸で描く。"""
    P = d["polygon"]
    n = len(P)
    C = d["const"]
    cx, cz = P[v]
    pr = Proj(cx - span, cx + span, cz - span, cz + span, W=560.0, top=26.0, bottom=34.0)
    g = _sv(pr.W, pr.H, title or ("隅 P%d の取り合い" % v))
    # 区画線(窓の外まで伸ばさない — 頂点から ±span*1.4 で切る)
    for e in ((v - 1) % n, v % n):
        a, b = P[e], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        sv = (P[v][0] - a[0]) * ux + (P[v][1] - a[1]) * uz      # 頂点の走り
        t0, t1 = max(0.0, sv - span * 1.4), min(L, sv + span * 1.4)
        g.append(LN(pr.X(a[0] + ux * t0), pr.Y(a[1] + uz * t0),
                    pr.X(a[0] + ux * t1), pr.Y(a[1] + uz * t1), "var(--dim)", 1.0, dash="4 4"))
    # 囲いの平面形(検査と同じ _run_quad / _perimeter_footprints から)
    for nm, q in _perimeter_footprints(d):
        pts = " ".join("%.1f,%.1f" % (pr.X(p[0]), pr.Y(p[1])) for p in q)
        if max(abs(p[0] - cx) for p in q) > span * 1.6 or max(abs(p[1] - cz) for p in q) > span * 1.6:
            continue
        col = "var(--nagaya)" if "Nagaya" in nm else ("var(--shu)" if nm.startswith("Y_NE") and "Sode" not in nm
                                                      else "var(--hei)")
        g.append('<polygon points="%s" fill="%s" fill-opacity="0.55" stroke="var(--ink)" stroke-width="1.2"/>'
                 % (pts, col))
        mx = sum(p[0] for p in q) / 4.0
        mz = sum(p[1] for p in q) / 4.0
        if abs(mx - cx) < span and abs(mz - cz) < span:
            g.append(T(pr.X(mx), pr.Y(mz) + 4, nm, "anS2", "middle", 9.5))
    g.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="var(--shu)"/>' % (pr.X(cx), pr.Y(cz)))
    g.append(T(pr.X(cx) + 6, pr.Y(cz) - 6, "P%d" % v, "anS2", "start"))
    for j in d["joints"]:
        if j["edge"] not in ((v - 1) % n, v % n):
            continue
        w = edge_pt(P, j["edge"], j["s"])
        if abs(w[0] - cx) > span or abs(w[1] - cz) > span:
            continue
        g.append('<circle cx="%.1f" cy="%.1f" r="4.2" fill="none" stroke="var(--shu)" stroke-width="1.6"/>'
                 % (pr.X(w[0]), pr.Y(w[1])))
        g.append(T(pr.X(w[0]) + 7, pr.Y(w[1]) + 12, "%s %s" % (j["id"], j["kind"]),
                   "anS2", "start", 10, "var(--shu)"))
    g.append(T(4, 15, title or ("隅 P%d(実寸の平面形。区画線=破線)" % v), "anS"))
    g.append("</svg>")
    return "\n".join(g)


def chain_strip_svg(d):
    """長屋の割付(鎖)。辺ごとに帯で描き、固定端▲と遊び端○、駒の境目を示す。"""
    C = d["const"]
    P = d["polygon"]
    edges = sorted(set(ch["edge"] for ch in d["chains"]))
    W = 940.0
    rowH = 58.0
    H = 30.0 + rowH * len(edges) + 22.0
    g = _sv(W, H, "長屋の割付(鎖)")
    for i, e in enumerate(edges):
        a, b = P[e], P[(e + 1) % len(P)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        y = 34.0 + rowH * i
        sc = (W - 128.0) / L
        def X(s_): return 108.0 + s_ * sc
        g.append(T(6, y + 14, "辺%d" % e, "anS2", "start"))
        g.append(LN(X(0), y + 10, X(L), y + 10, "var(--dim)", 0.9, dash="4 4"))
        for r in d["runs"]:
            if r["edge"] != e or r["kind"] != "Dobei":
                continue
            g.append(R(X(r["s0"]), y + 6, X(r["s1"]) - X(r["s0"]), 8, fill="var(--hei)", op=0.9))
        for ch in d["chains"]:
            if ch["edge"] != e:
                continue
            bnd = _chain_mods(d, ch)
            g.append(R(X(ch["s0"]), y, X(ch["s1"]) - X(ch["s0"]), 20,
                       fill="var(--nagaya)", op=0.55, stroke="var(--ink)", sw=1.0))
            for bb in bnd:
                g.append(LN(X(bb), y, X(bb), y + 20, "var(--ink)", 0.8, op=0.8))
            for key in ("s0", "s1"):                       # 両端とも固定端(面へ合わせる)
                g.append('<path d="M %.1f %.1f l -5 -9 l 10 0 Z" fill="var(--shu)"/>'
                         % (X(ch[key]), y - 2))
            g.append(T(X((ch["s0"] + ch["s1"]) / 2), y + 14,
                       "%s %.2fm / %d本" % (ch["id"], ch["len"], len(ch["pieces"])),
                       "anS2", "middle", 10))
        for k in d["komon"] + ([d["gate"]] if d["gate"]["edge"] == e else []):
            if k["edge"] != e:
                continue
            if "plan" in k:
                q0, q1 = k["plan"]["sPos"]["banshoW"][0], k["plan"]["sPos"]["banshoE"][1]
            else:
                q0, q1 = k["s"] - k["w"] / 2, k["s"] + k["w"] / 2
            g.append(R(X(q0), y - 4, X(q1) - X(q0), 28, fill="var(--shu)", op=0.25,
                       stroke="var(--shu)", sw=1.2))
        for y2 in d.get("yagura", []):
            if y2["vertex"] % len(P) == e:
                g.append(R(X(0), y - 4, 6, 28, fill="var(--shu)", op=0.55))
    g.append(T(6, H - 8, "▲=固定端(門・番所・隅櫓・頂点。動かさない)/ ○=遊び端(練塀へ継ぐ端。"
                         "練塀は駒を伸縮して端数を吸えるのでこちらを動かす)。縦線=駒の境目。"
                         "朱の帯=開口。", "anS2", "start"))
    g.append("</svg>")
    return "\n".join(g)


def joints_face_table(d):
    """取り合い表(§3f)。A/Bのどの面・納め・目標と許容・可動側。"""
    rows = []
    for j in d["joints"]:
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td>辺%d s=%.2f</td>"
                    "<td><code>%s</code><br><span class='note'>%s</span></td>"
                    "<td><code>%s</code><br><span class='note'>%s</span></td>"
                    "<td>%s</td><td>%+.2f<br><span class='note'>[%.2f‥%.2f]</span></td>"
                    "<td><code>%s</code></td><td>%s</td></tr>"
                    % (j["id"], j["at"], j["edge"], j["s"],
                       j["a"], j["aFace"], j["b"], j["bFace"], j["kind"],
                       j["gap"], j["tol"][0], j["tol"][1], j["moves"], j.get("cert", "?")))
    return ("<h3>取り合い表 — 接する面で決める</h3><div class='tw'><table><thead><tr>"
            "<th>id</th><th>場所</th><th>位置</th><th>A とその面</th><th>B とその面</th>"
            "<th>納め</th><th>目標 / 許容</th><th>可動側</th><th>確度</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'>目標は<b>面と面の距離</b>(+=隙間 / −=差し込み・めり込み)。"
            "許容は<b>隙間よりめり込みを許す</b>向きに振ってある — 0 を狙い、外すならめり込む側へ外す。"
            "<b>芯・中心・ピボットで合わせない</b>: 部材を差し替えた瞬間に破れる。</p>")


def chains_table(d):
    """長屋の割付。**1区間1本** — 開口の縁から縁までを長さ指定の一体物で埋める。"""
    rows = []
    for ch in d["chains"]:
        for i, p in enumerate(ch["pieces"]):
            k, eps = nagaya_eps(p["len"])
            head = ("<td rowspan='%d'><code>%s</code></td><td rowspan='%d'>辺%d</td>"
                    "<td rowspan='%d'>%.2f–%.2f</td><td rowspan='%d'>%.2f</td>"
                    "<td rowspan='%d' class='note'>%s<br>↕<br>%s</td>"
                    % (len(ch["pieces"]), ch["id"], len(ch["pieces"]), ch["edge"],
                       len(ch["pieces"]), ch["s0"], ch["s1"], len(ch["pieces"]), ch["len"],
                       len(ch["pieces"]), ch["ends"]["s0"], ch["ends"]["s1"])) if i == 0 else ""
            warn = (eps is not None and abs(eps) > d["const"]["nagayaEpsGuar"])
            rows.append("<tr>%s<td><code>%s</code></td><td>%.2f–%.2f</td><td><b>%.2f</b></td>"
                        "<td>%s</td><td>%s%+.3f m%s</td><td><code>%s</code></td><td>%s</td></tr>"
                        % (head, p["run"], p["s0"], p["s1"], p["len"],
                           "—" if k is None else str(k),
                           "⚠ " if warn else "", 0.0 if eps is None else eps,
                           "" if not warn else "(12m 未満なので保証の外)",
                           p["asset"], ch.get("cert", "?") if i == 0 else ""))
    return ("<h3>長屋の割付(鎖)— 1区間1本</h3><div class='tw'><table><thead><tr><th>鎖</th>"
            "<th>辺</th><th>走り s</th><th>長さ</th><th class='note'>両端が接する面</th>"
            "<th>run</th><th>走り s</th><th>棟の長さ L</th><th>窓割り k</th><th>無地の壁の詰め ε</th>"
            "<th>部材</th><th>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'><b>表長屋は長さを 1cm 単位で指定して起こす</b>"
            "(<code>build_nagaya_omote.py</code>)。だから鎖は<b>開口の縁から縁まで</b>を"
            "面から面までの長さで埋め、<b>端数が出ない</b> — 隅の詰めも遊び端も要らない。"
            "長さは瓦・海鼠・格子を伸ばさず、<b>窓割りの本数 k</b> と"
            "<b>窓と窓の間の無地の壁の詰め ε</b>(素は 1.536m)だけで吸う。"
            "1本が複数行あるのは<b>天端が段で変わる点で棟を切る</b>から — "
            "段ごとに両端に妻を出した版を突き付ける(雛壇に並ぶ長屋の姿)。"
            "⛔ 実装は L を定数で置かず、<b>据えたあと実メッシュの妻面を測って</b>許容を確かめる。</p>")


def joints_check(d):
    """**開口の両側と隅に取り合いの記述があるか。**空欄を残せない形にする。

    ⚠ 2026-08-29(EDO-0053): 指図が開口の位置と幅しか持っておらず、
      「どの面がどの面に接するか」が一行も無かった。実装は芯合わせしかできず、
      同じ門の左右で 1.66m の食い込みと 0.96m の隙間が同時に起きた。
    """
    P = d["polygon"]
    n = len(P)
    bad = []
    if not d.get("joints"):
        return ["joints(取り合い表)が無い — 開口と隅の納めが空欄のまま実装へ渡る"]
    need = []
    g = d["gate"]
    sp = g["plan"]["sPos"]
    need.append((g["edge"], sp["banshoW"][0], "表門の西の縁"))
    need.append((g["edge"], sp["banshoE"][1], "表門の東の縁"))
    for k in d["komon"]:
        nm = "御蔵門" if k["name"] == "Kuramon" else "東小門"
        need.append((k["edge"], k["s"] - k["w"] / 2.0, nm + "の手前の縁"))
        need.append((k["edge"], k["s"] + k["w"] / 2.0, nm + "の先の縁"))
    for v in range(n):
        e = (v - 1) % n
        a, b = P[e], P[(e + 1) % n]
        need.append((e, math.hypot(b[0] - a[0], b[1] - a[1]), "隅 P%d" % v))
    for e, s, label in need:
        hit = [j for j in d["joints"] if j["edge"] == e and abs(j["s"] - s) <= 0.35]
        if not hit:
            bad.append("%s(辺%d s=%.2f)に joints の記述が無い — "
                       "どの面がどの面に接するかを書く(§3f)" % (label, e, s))
    # 欄の埋まりは**すべての取り合い**で見る(必須の場所に紐づく物だけ見ると、隅櫓の袖塀の
    # ように「場所の一覧に無いが実装が要る」取り合いが素通りする)
    for j in d["joints"]:
        for k2 in ("a", "aFace", "b", "bFace", "kind", "part", "procure", "gap", "tol", "moves",
                   "fixed", "cert", "_"):
            if k2 not in j or j[k2] in ("", None, []):
                bad.append("取り合い %s に %s が無い — 空欄のまま実装へ渡せない" % (j.get("id", "?"), k2))
        if isinstance(j.get("tol"), list) and len(j["tol"]) == 2:
            lo, hi = j["tol"]
            if hi > 0.0:
                bad.append("%s の許容が隙間側へ開いている(上限 %+.2f)— "
                           "閉じの許容は『隙間 > めり込み』" % (j["id"], hi))
            if not (lo <= j["gap"] <= hi):
                bad.append("%s の目標 %+.2f が許容 [%.2f‥%.2f] の外"
                           % (j["id"], j["gap"], lo, hi))
        if j["moves"] in (j["a"], j["b"]) or "(" in j["moves"] or j["moves"].startswith("両方"):
            pass
        elif j["moves"] not in (j["a"], j["b"]):
            bad.append("%s の可動側 %s が A/B のどちらでもない — 誰が動くのかが決まっていない"
                       % (j["id"], j["moves"]))
    # 鎖の算術(**1区間1本** — 面から面までを長さ指定の一体物で埋める)
    C = d["const"]
    for ch in d.get("chains", []):
        pcs = ch["pieces"]
        if not pcs:
            bad.append("鎖 %s に棟が一つも無い" % ch["id"])
            continue
        if abs(sum(p["len"] for p in pcs) - ch["len"]) > 0.005 or \
           abs((ch["s1"] - ch["s0"]) - ch["len"]) > 0.005:
            bad.append("鎖 %s の長さ %.3f が棟の合計と合わない — 端数を隅や開口へ押し出している"
                       % (ch["id"], ch["len"]))
        if abs(pcs[0]["s0"] - ch["s0"]) > 0.005 or abs(pcs[-1]["s1"] - ch["s1"]) > 0.005:
            bad.append("鎖 %s の端が棟の端と合わない(端は開口・隅の面に合わせる)" % ch["id"])
        for p, q in zip(pcs, pcs[1:]):
            if abs(q["s0"] - p["s1"]) > 0.005:
                bad.append("鎖 %s の %s → %s に隙間/重なりがある" % (ch["id"], p["run"], q["run"]))
        for p in pcs:
            rr = [r for r in d["runs"] if r["name"] == p["run"]]
            if not rr:
                bad.append("鎖 %s が知らない run %s を指している" % (ch["id"], p["run"]))
                continue
            r = rr[0]
            if abs(r["s0"] - p["s0"]) > 0.005 or abs(r["s1"] - p["s1"]) > 0.005:
                bad.append("鎖 %s の棟 %s(%.2f–%.2f)が run の s(%.2f–%.2f)と食い違う"
                           % (ch["id"], p["run"], p["s0"], p["s1"], r["s0"], r["s1"]))
            if abs(p["len"] - (p["s1"] - p["s0"])) > 0.005:
                bad.append("鎖 %s の棟 %s の長さ %.3f が走りと合わない" % (ch["id"], p["run"], p["len"]))
            k, eps = nagaya_eps(p["len"])
            if k is None:
                bad.append("鎖 %s の棟 %s は L=%.2fm が短すぎて起こせない(妻2枚が入らない)"
                           % (ch["id"], p["run"], p["len"]))
            elif p["len"] >= C["nagayaLenGuar"] and abs(eps) > C["nagayaEpsGuar"]:
                bad.append("鎖 %s の棟 %s(L=%.2fm)は無地の壁の詰め ε=%+.3fm で、"
                           "生成器が %.0fm 以上について保証する %.2fm を超えている — "
                           "長さの解き方が図と生成器でずれている(同じ式を使うこと)"
                           % (ch["id"], p["run"], p["len"], eps,
                              C["nagayaLenGuar"], C["nagayaEpsGuar"]))
            if "EdoAssets.Own.NagayaOmote" not in p.get("asset", ""):
                bad.append("鎖 %s の棟 %s が部材を名指ししていない(EdoAssets.Own.NagayaOmote)"
                           % (ch["id"], p["run"]))
        if not ch.get("ends", {}).get("s0") or not ch.get("ends", {}).get("s1"):
            bad.append("鎖 %s の両端がどの面に接するか書いていない" % ch["id"])
    # 長屋 run が必ずどれかの鎖に入っているか(割付の書き漏らし)
    inch = set()
    for ch in d.get("chains", []):
        inch |= set(p["run"] for p in ch["pieces"])
    for r in d["runs"]:
        if r["kind"] == "Nagaya" and r["name"] not in inch:
            bad.append("長屋 run %s が鎖(chains)に入っていない — 割付が決まっていない" % r["name"])
    return bad


def _kado_deg(d, v):
    """頂点 v の折れ角[deg]。実装の EdoOkabeYashikiBuilder.KadoDeg と同じ定義
    (yaw = atan2(x, z) の DeltaAngle。負=鏡像=名前の末尾 M)。"""
    P = d["polygon"]
    n = len(P)
    def yaw(e):
        a, b = P[e % n], P[(e + 1) % n]
        return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))
    return (yaw(v % n) - yaw((v - 1) % n) + 540.0) % 360.0 - 180.0


def _kado_path(part, deg):
    """EdoAssets.Own.Kado と同じ規則でパスを組む。⛔ ここを実装と違う綴りにしない。"""
    return ("Assets/Edo/Models/Kado/%s_Kado_%02d%s.fbx"
            % (part, int(round(abs(deg))), "M" if deg < 0 else ""))


def _kado_name(j):
    """取り合い j が使う隅部材の**名前**(`kado` を持たない継ぎ目は None)。"""
    kd = j.get("kado")
    if not kd:
        return None
    return "%s_Kado_%02d%s" % (kd["part"], int(round(abs(kd["deg"]))), "M" if kd["deg"] < 0 else "")


def _kado_arms(d, j):
    """取り合い j の腕の長さ(入り, 出)[**世界座標 m**]。

    ⛔ **joints は腕の数値を持たない**(規則4)。正典は json の `kado`(部材の実測表)で、
      素の実測 `armRaw` に `scale`(=ES 1.818。隅部材は ES 倍で据える)を掛けて導く。
      ⚠ 2026-08-30 に素の腕(2.27前後)を世界の腕と取り違えた指図を出しかけた。
    留め継ぎは折れ角を二等分するので**入りと出の腕は同じ長さ**。
    """
    nm = _kado_name(j)
    K = d.get("kado") or {}
    e = (K.get("parts") or {}).get(nm)
    if not e:
        return 0.0, 0.0
    a = round(e["armRaw"] * K["scale"], 3)
    return a, a


def _corner_joints(d):
    """隅の取り合いを {頂点: joint} で返す。"""
    n = len(d["polygon"])
    out = {}
    for j in d["joints"]:
        if not j["at"].startswith("隅 P"):
            continue
        out[(j["edge"] + 1) % n] = j
    return out


def _kado_scope(d, j):
    """隅部材の採否の規則が効く隅か。**木柵の隅と隅櫓の隅は規則の外。**
    ⚠ kind の文字列(「重ね」)で判定すると、隅部材を使わない練塀の隅(P4/P5)まで
      規則の外へ落ちて検査が素通りする(2026-08-29 に感度試験で発覚)。
      **何が接しているか**で判定する。"""
    if "置き換え" in j["kind"]:
        return False                                   # 隅櫓が隅を置き換える
    fen = set(f["name"] for f in d.get("fences", []))
    return not (j["a"] in fen or j["b"] in fen)        # 木柵は互いに越えて敷く


def kado_measure_table(d):
    """**隅部材の実測表**(json の `kado` がそのまま出る)。素の値と倍率を必ず併記する。"""
    K = d.get("kado")
    if not K:
        return ""
    C = d["const"]
    rows = []
    for nm, e in K["parts"].items():
        pth = "Assets/Edo/Models/Kado/%s.fbx" % nm
        ok = os.path.exists(os.path.join(ROOT, pth))
        rows.append("<tr><td><code>%s</code></td><td>%+.2f°</td><td>%.3f</td><td><b>%.3f</b></td>"
                    "<td>%s</td><td>%s</td></tr>"
                    % (nm, e["degMeasured"], e["armRaw"], e["armRaw"] * K["scale"],
                       "・".join(e["use"]), "在る" if ok else "<b>無い</b>"))
    return ("<h3>隅部材の実測(腕と丈の正典)</h3><div class='tw'><table><thead><tr>"
            "<th>部材</th><th>折れ角(実測)</th><th>腕 素の単位</th><th>腕 世界 [m]</th>"
            "<th>使う隅</th><th>実在</th></tr></thead><tbody>" + "".join(rows)
            + "</tbody></table></div>"
            "<p class='cap'><b>倍率 %.3f(=ES)。</b>隅部材は <code>scale = ES</code> で据えるので、"
            "<b>素の実測を %.3f 倍したものが世界の腕</b>。⚠ 2026-08-30 に素の腕(2.3前後)を"
            "世界の腕と取り違えた指図を出しかけた — <b>単位を必ず併記する</b>。"
            "丈は素 %.3f × %.3f = <b>%.3fm</b> で、<code>const.dobeiH</code> の %.2fm は丸めた呼び値"
            "(取り合いに効くのは実部材の側。直線材も同じ素材・同じ倍率なので天端は揃う)。"
            "腕は入り・出とも同じ長さ — 留め継ぎは折れ角を二等分するので左右対称。"
            "⛔ この数値を取り合い表へ写さない(絶対規則4)。取り合いは部材名を指すだけで、"
            "腕はここから導く。</p>"
            % (K["scale"], K["scale"], K["heightRaw"], K["scale"],
               K["heightRaw"] * K["scale"], C["dobeiH"]))


def kado_parts_table(d):
    """**隅部材の採否**(頂点ごと)。折れ角・突き付けたときの開き・採否・部材・実在。"""
    C = d["const"]
    P = d["polygon"]
    n = len(P)
    cj = _corner_joints(d)
    rows = []
    for v in range(n):
        j = cj.get(v)
        deg = _kado_deg(d, v)
        opn = C["dobeiWallT"] * math.tan(math.radians(abs(deg)) / 2.0)
        if j is None:
            rows.append("<tr><td>P%d</td><td>%+.2f°</td><td>%.3f m</td><td colspan='4' class='note'>"
                        "取り合いの記述が無い</td></tr>" % (v, deg, opn))
            continue
        inscope = _kado_scope(d, j)
        pp = _kado_path(j["kado"]["part"], j["kado"]["deg"]) if j.get("kado") else None
        ok = bool(pp) and os.path.exists(os.path.join(ROOT, pp))
        ai, ao = _kado_arms(d, j)
        if not inscope:
            saihi = "規則の外(%s)" % ("木柵は重ねる" if "重ね" in j["kind"] else "隅櫓が隅を置き換える")
        else:
            saihi = "<b>要る</b>" if abs(deg) >= C["kadoDegMin"] else "使わない"
        rows.append("<tr><td>P%d</td><td>%+.2f°</td><td>%.3f m</td><td>%s</td>"
                    "<td class='note'>%s</td><td><code>%s</code></td><td>%s</td>"
                    "<td>%.2f / %.2f</td></tr>"
                    % (v, deg, opn, saihi, j["kind"], pp or "—",
                       ("在る" if ok else "<b>無い</b>") if pp else "—", ai, ao))
    return ("<h3>隅部材の採否(頂点ごと)</h3><div class='tw'><table><thead><tr><th>頂点</th>"
            "<th>折れ角 Δ</th><th>突き付けの開き</th><th>規則の判定</th><th class='note'>納め</th>"
            "<th>部材のパス</th><th>実在</th><th>腕 入/出</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<p class='cap'><b>規則(2026-08-29 ユーザー裁定)</b>: 折れ角が "
            "<code>const.kadoDegMin</code> 未満なら<b>隅部材を使わず</b>、直線材の突き付け＋重ねで"
            "吸う。以上なら隅部材を挟む。根拠は<b>突き付けたときに外面へ開く量</b> = "
            "<code>dobeiWallT · tan(Δ/2)</code>(表の3列目)。"
            "部材は在庫の正規隅ではなく<b>実測の折れ角から起こした留め継ぎ</b>を使う"
            "(⛔ 折れ角を決め打ちしてはならない — 当邸の「90°級」は実は +90.95° と −87.76°)。"
            "<b>腕</b>は隅部材が兼ねる長さ(<b>世界座標</b>。正典は <code>kado</code> の素の実測 × "
            "<code>scale</code>=ES 1.818)で、<b>両隣の run は腕ぶん退がる</b> — "
            "入りの run は <code>辺長 − 腕 + |gap|</code> で止め、出の run は <code>腕 − |gap|</code> から始める。"
            "⛔ <code>LoadAssetAtPath</code> は例外を投げず null を返すので、"
            "在庫に無い物を名指しすると<b>隅だけが黙って建たない</b>(絶対規則11)。"
            "木柵どうしの隅は隅部材を使わず互いに越えて敷く。</p>")


def kado_stock_check(d):
    """隅部材の**採否が規則どおりか**と、名指しした部材が**実在するか**。
    ⛔ 綴り違いは静かに壊れる(絶対規則11)。⛔ 規則と採否がずれたら、図だけが正しくなる。"""
    C = d["const"]
    P = d["polygon"]
    n = len(P)
    bad = []
    cj = _corner_joints(d)
    for v in range(n):
        j = cj.get(v)
        if j is None:
            bad.append("隅 P%d に取り合いの記述が無い" % v)
            continue
        pp = _kado_path(j["kado"]["part"], j["kado"]["deg"]) if j.get("kado") else None
        if not _kado_scope(d, j):
            continue
        deg = _kado_deg(d, v)
        need = abs(deg) >= C["kadoDegMin"]
        has = bool(pp)
        if need != has:
            bad.append("隅 P%d(%s・折れ %+.1f°)は規則では隅部材が%s のに、指図は%s — "
                       "規則は『折れ角 %.0f° 未満なら使わない』(開き %.3fm)"
                       % (v, j["id"], deg, "要る" if need else "要らない",
                          "名指ししている" if has else "名指ししていない",
                          C["kadoDegMin"],
                          C["dobeiWallT"] * math.tan(math.radians(abs(deg)) / 2.0)))
        if has and not os.path.exists(os.path.join(ROOT, pp)):
            bad.append("隅 P%d(%s)の部材 %s が**無い** — LoadAssetAtPath は null を返すので、"
                       "隅だけが黙って建たない(絶対規則11)" % (v, j["id"], pp))
        if has and "留め継ぎ" in j["kind"]:
            want = _kado_path("Dobei", deg)
            if pp != want:
                bad.append("隅 P%d(%s)は留め継ぎなのに部材が %s — 折れ角から導けば %s"
                           % (v, j["id"], pp, want))
        if has and abs(j["kado"]["deg"] - deg) > 0.5:
            bad.append("隅 P%d(%s)の `kado.deg` %+.2f° が区画から導いた折れ角 %+.2f° と食い違う — "
                       "折れ角は区画が決める(決め打ちしない)" % (v, j["id"], j["kado"]["deg"], deg))
        if has and j.get("procure") != "在庫" and os.path.exists(os.path.join(ROOT, pp)):
            bad.append("隅 P%d(%s)の部材は在るのに調達が「%s」になっている"
                       % (v, j["id"], j.get("procure")))
        ai, ao = _kado_arms(d, j)
        if not has and (ai or ao):
            bad.append("隅 P%d(%s)は隅部材を使わないのに腕が 0 でない" % (v, j["id"]))
        # 腕は隣の run より短いこと(腕が run を食い切ると帯が消える)
        for arm, e in ((ai, j["edge"]), (ao, (j["edge"] + 1) % n)):
            if arm <= 0:
                continue
            rs = [r for r in d["runs"] if r["edge"] == e]
            if rs and max(r["s1"] for r in rs) - min(r["s0"] for r in rs) < arm:
                bad.append("隅 P%d(%s)の腕 %.2fm が辺%d の囲いより長い" % (v, j["id"], arm, e))
    return bad


def kado_arm_check(d, tol=0.02):
    """**隅の腕の検査。**全頂点 P0〜P(n-1) を、三つの観点で検める。

      (a) **腕の長さが部材の実測と一致するか** — 正典は json の `kado`(素の実測 armRaw)。
          世界の腕 = `armRaw × scale`(scale=ES 1.818。隅部材は ES 倍で据える)。
          あわせて丈 `heightRaw × scale` が `const.dobeiH` と合うか、
          `kado.parts[].degMeasured` が区画から導いた折れ角と合うかを見る。
      (b) **隣の run の端が腕の端面に来ているか** — 入りの run は `辺長 − 腕 + |gap|` で止まり、
          出の run は `腕 − |gap|` から始まる(gap は負=めり込み。⛔ 隙間は不可)。
          隅部材が兼ねる腕と直線材が**二重**になっていないか、逆に**離れて**いないかを測る。
      (c) **腕が実装へ渡る形で持たれているか** — `EdoMatsudairaDewaBuilder.PlaceKado` は
          joints を舐めて `kado`(part/deg/seat)を持つ継ぎ目だけを据える。
          `kado` の無い腕は図の上にしか無い。

    ⚠ 2026-08-29(EDO-0053 の後): 隅 P13 の腕は joints にしか無く実装へ渡らず、
      辺13 s0.7〜2.6 に 2.25m の口が開いた。⚠ 2026-08-30: その腕の長さが部材の実寸と
      違い(`armIn=2.99`)、しかも**素の単位を世界座標と取り違えた**まま出しかけた。
      → 腕の数値は joints から抜いて `kado` 一箇所に集め、この検査で三方から縛る。
    """
    C = d["const"]
    P = d["polygon"]
    n = len(P)
    K = d.get("kado")
    bad = []
    if not K:
        return ["`kado`(隅部材の実測表)が無い — 腕の長さが導けない"]
    if abs(K["heightRaw"] * K["scale"] - C["dobeiH"]) > 0.01:
        bad.append("隅部材の丈 %.3f × %.3f = %.3fm が const.dobeiH %.2fm と 0.01m 以上ちがう — "
                   "隅と直線材で天端が段になる(倍率の取り違えを疑う)"
                   % (K["heightRaw"], K["scale"], K["heightRaw"] * K["scale"], C["dobeiH"]))
    R = dict((r["name"], r) for r in d["runs"])
    cj = _corner_joints(d)
    used = set()
    for v in range(n):
        j = cj.get(v)
        if j is None:
            bad.append("隅 P%d に取り合い(joints)が無い — 腕を検めようがない" % v)
            continue
        deg = _kado_deg(d, v)
        need = _kado_scope(d, j) and abs(deg) >= C["kadoDegMin"]
        nm = _kado_name(j)
        if not need:
            if nm:
                bad.append("隅 P%d(%s)は隅部材が要らない折れ(%+.2f°)のに `kado` を持っている"
                           % (v, j["id"], deg))
            continue
        # (c) 実装へ渡る形か
        if not nm:
            bad.append("隅 P%d(%s・折れ %+.2f°)の腕が**実装へ渡らない** — 取り合いに `kado` "
                       "(part/deg/seat)が無く、`EdoMatsudairaDewaBuilder.PlaceKado` は据えない。"
                       "2026-08-29 に P13 でこの形のまま 2.25m の口が開いた" % (v, j["id"], deg))
            continue
        used.add(nm)
        ent = (K.get("parts") or {}).get(nm)
        if not ent:
            bad.append("隅 P%d(%s)の部材 %s が実測表 `kado.parts` に無い — 腕の長さが導けない"
                       % (v, j["id"], nm))
            continue
        # (a) 実測との一致
        if abs(ent["degMeasured"] - deg) > 0.5:
            bad.append("隅 P%d(%s)の部材 %s の実測の折れ %+.2f° が区画の折れ %+.2f° と食い違う — "
                       "部材が別の角度で起こされている" % (v, j["id"], nm, ent["degMeasured"], deg))
        ai, ao = _kado_arms(d, j)
        # ⛔ ここで `ai == armRaw × scale` を測らない — 同じ式で導いた値を同じ式で検算する
        #   恒真の検査になる(qa-and-pitfalls「測れないものは 0 件になる」)。
        #   実測表と実物の突き合わせは (b) の**隣の run の端**が担う。
        # (b) 隣の run の端
        g = abs(j["gap"])
        for side, want_name, e, at_end, arm in (("入り", j["a"], j["edge"] % n, True, ai),
                                                ("出", j["b"], (j["edge"] + 1) % n, False, ao)):
            r = R.get(want_name)
            if r is None:
                bad.append("隅 P%d(%s)の%s側 %s が runs に無い — 端を測れない"
                           % (v, j["id"], side, want_name))
                continue
            a, b = P[e], P[(e + 1) % n]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if at_end:
                want, got, lab = L - arm + g, r["s1"], "s1"
            else:
                want, got, lab = arm - g, r["s0"], "s0"
            if abs(got - want) > tol:
                bad.append("隅 P%d(%s)の%s側 %s の %s が %.2f — 腕 %.3fm と gap %+.2f から導けば "
                           "%.2f(辺%d・差 %+.2fm。%s)"
                           % (v, j["id"], side, want_name, lab, got, arm, j["gap"], want, e,
                              got - want,
                              "隅部材と二重" if (got - want) * (1 if at_end else -1) > 0
                              else "隅部材との間に口が開く"))
        # (d) 座は入りの run の端の座を写す(隅で天端が揃うのが正典)
        rin = R.get(j["a"])
        if rin is not None:
            want = seat_at(rin, rin["s1"])
            if abs(j["kado"]["seat"] - want) > 0.005:
                bad.append("隅 P%d(%s)の `kado.seat` %.2f が入りの run %s の端の座 %.2f と違う — "
                           "隅部材は入りの run の天端に合わせる"
                           % (v, j["id"], j["kado"]["seat"], j["a"], want))
    for nm in (K.get("parts") or {}):
        if nm not in used:
            bad.append("実測表 `kado.parts` の %s をどの隅も使っていない — 使わない部材を表に残さない" % nm)
    return bad


def kado_arm_sensitivity(d):
    """**感度試験** — わざと壊して `kado_arm_check` が鳴るか。
    ⛔ 鳴らない probe があれば、その壊れ方は検査で捕まらない。"""
    base = len(kado_arm_check(d))
    probes = []

    def run(label, mut):
        m = copy.deepcopy(d)
        mut(m)
        probes.append((label, len(kado_arm_check(m)) - base))

    def _j(m, jid):
        return [x for x in m["joints"] if x["id"] == jid][0]

    def _r(m, nm):
        return [x for x in m["runs"] if x["name"] == nm][0]

    run("① 隅 P13 の `kado` を消す(腕が実装へ渡らない形へ戻す)",
        lambda m: _j(m, "J_P13").pop("kado"))
    run("② 部材の実測の腕を 2.30→2.60 に書き換える",
        lambda m: m["kado"]["parts"]["Dobei_Kado_19"].__setitem__("armRaw", 2.60))
    run("③ 倍率を ES→1.0 にする(素の単位を世界座標と取り違える)",
        lambda m: m["kado"].__setitem__("scale", 1.0))
    run("④ 入りの run の端を 0.50m 伸ばして腕と二重にする",
        lambda m: _r(m, "N_Hei_E").__setitem__("s1", _r(m, "N_Hei_E")["s1"] + 0.50))
    run("⑤ 出の run の始まりを 0.50m 遅らせて腕との間に口を開ける",
        lambda m: _r(m, "S_Hei_C").__setitem__("s0", _r(m, "S_Hei_C")["s0"] + 0.50))
    run("⑥ 隅の座を 0.50m ずらす(隅で天端が段になる)",
        lambda m: _j(m, "J_P1")["kado"].__setitem__("seat", _j(m, "J_P1")["kado"]["seat"] + 0.50))
    run("⑦ 部材の丈を 1.455→1.30 にする(隅だけ天端が下がる)",
        lambda m: m["kado"].__setitem__("heightRaw", 1.30))
    run("⑧ 折れ角の実測を +18.54→+30.0 に書き換える(別の角度の部材を当てる)",
        lambda m: m["kado"]["parts"]["Dobei_Kado_19"].__setitem__("degMeasured", 30.0))
    return base, probes


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
             "--pretty=%h|%ad|%s", "--", "docs/Sashizu/matsudaira_dewa_sashizu.json",
             "docs/Sashizu/matsudaira_dewa_kosho.md"]).decode()
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


# ---------------------------------------------------------------- 外周の閉じ
def _seg_d(p, a, b):
    ex, ez = b[0] - a[0], b[1] - a[1]
    L2 = ex * ex + ez * ez
    if L2 < 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ez) / L2))
    return math.hypot(p[0] - (a[0] + ex * t), p[1] - (a[1] + ez * t))


def _quad(cx, cz, ux, uz, half_l, half_t):
    """中心 (cx,cz)・長手方向 (ux,uz)・長さ 2*half_l・厚み 2*half_t の矩形の四隅。"""
    nx, nz = -uz, ux
    return [(cx + ux * half_l + nx * half_t, cz + uz * half_l + nz * half_t),
            (cx + ux * half_l - nx * half_t, cz + uz * half_l - nz * half_t),
            (cx - ux * half_l - nx * half_t, cz - uz * half_l - nz * half_t),
            (cx - ux * half_l + nx * half_t, cz - uz * half_l + nz * half_t)]


def _run_quad(d, r):
    """run の平面形。**長屋は区画線から内側へ nagayaD、練塀は線をまたいで dobeiT。**
    ⚠ 帯を線の上に中心を置いて組むと、長屋が外へ 2.25m はみ出した形で測ってしまい、
      隅櫓との当たり判定が偽陽性になる(2026-08-29)。"""
    P = d["polygon"]
    n = len(P)
    C = d["const"]
    a, b = P[r["edge"] % n], P[(r["edge"] + 1) % n]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, nz = -uz, ux
    cx = sum(q[0] for q in P) / n
    cz = sum(q[1] for q in P) / n
    mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if (cx - mx) * nx + (cz - mz) * nz < 0:
        nx, nz = -nx, -nz                              # 内向き
    if r["kind"] == "Nagaya":
        half_t = C["nagayaD"] / 2.0
        off = half_t                                   # 外面を線に置く
    else:
        half_t = C["dobeiT"] / 2.0
        off = 0.0                                      # 線をまたぐ
    mid = (r["s0"] + r["s1"]) / 2.0
    c = (a[0] + ux * mid + nx * off, a[1] + uz * mid + nz * off)
    return _quad(c[0], c[1], ux, uz, (r["s1"] - r["s0"]) / 2.0, half_t)


def _convex_overlap(A, B, gap=0.0):
    """凸多角形どうしが(隙間 gap 未満まで詰めて)重なるか。分離軸法。"""
    for poly in (A, B):
        k = len(poly)
        for i in range(k):
            ex = poly[(i + 1) % k][0] - poly[i][0]
            ez = poly[(i + 1) % k][1] - poly[i][1]
            L = math.hypot(ex, ez)
            if L < 1e-12:
                continue
            nx, nz = -ez / L, ex / L
            a0 = min(q[0] * nx + q[1] * nz for q in A)
            a1 = max(q[0] * nx + q[1] * nz for q in A)
            b0 = min(q[0] * nx + q[1] * nz for q in B)
            b1 = max(q[0] * nx + q[1] * nz for q in B)
            if a1 + gap <= b0 or b1 + gap <= a0:
                return False
    return True


def _seg_x(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return False
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0


def _perimeter_footprints(d):
    """外周を塞ぐ物の平面形(世界座標の四角形)を、**指図の設計値だけ**から組む。
    ここに入らない物は「塞いでいない」— 門の開口は扉を申告するまで穴として数える。"""
    P = d["polygon"]
    C = d["const"]
    n = len(P)
    out = []

    def edge(e):
        a, b = P[e % n], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return a, ((b[0] - a[0]) / L, (b[1] - a[1]) / L), L

    for r in d["runs"]:
        out.append((r["name"], _run_quad(d, r)))
    for f in d.get("fences", []):
        a, u, L = edge(f["edge"])
        s0, s1 = f["s0"], f["s1"]
        c = ((a[0] + u[0] * (s0 + s1) / 2), (a[1] + u[1] * (s0 + s1) / 2))
        out.append((f["name"], _quad(c[0], c[1], u[0], u[1], (s1 - s0) / 2.0, 0.10)))
    g = d.get("gate")
    if g:
        a, u, L = edge(g["edge"])
        for nm, (s0, s1) in g["plan"].get("sPos", {}).items():
            c = ((a[0] + u[0] * (s0 + s1) / 2), (a[1] + u[1] * (s0 + s1) / 2))
            t = g["plan"]["bansho"]["d"] / 2.0 if "bansho" in nm else C["dobeiT"] / 2.0
            # 門の開口そのもの(mon)は、扉 leaf を申告した時だけ塞いだと数える
            if nm == "mon" and not g["plan"].get("leaf"):
                continue
            out.append(("表門/" + nm, _quad(c[0], c[1], u[0], u[1], (s1 - s0) / 2.0, t)))
    for k in d.get("komon", []):
        if not k.get("leaf"):
            continue                                  # 扉が無い門は穴
        a, u, L = edge(k["edge"])
        c = (a[0] + u[0] * k["s"], a[1] + u[1] * k["s"])
        out.append((k["name"], _quad(c[0], c[1], u[0], u[1], k["w"] / 2.0, C["dobeiT"] / 2.0)))
    # 隅部材(腕)。**外周を塞ぐ実体**なので閉じの検査に入れる — 入れ忘れると、
    # 長屋の側を腕ぶん切った途端に隅が「穴」として鳴る。
    for j in d.get("joints", []):
        if not j["at"].startswith("隅 P"):
            continue
        vtx = (j["edge"] + 1) % n
        ai, ao = _kado_arms(d, j)
        for arm, e, at_end in ((ai, j["edge"], True),
                               (ao, (j["edge"] + 1) % n, False)):
            if arm <= 0:
                continue
            a, u, L = edge(e)
            s0, s1 = (L - arm, L) if at_end else (0.0, arm)
            c = (a[0] + u[0] * (s0 + s1) / 2, a[1] + u[1] * (s0 + s1) / 2)
            out.append(("Kado_P%d/辺%d" % (vtx, e),
                        _quad(c[0], c[1], u[0], u[1], arm / 2.0, C["dobeiT"] / 2.0)))
    for y in d.get("yagura", []):
        v = y["vertex"] % n
        a, u, L = edge(v)                             # 頂点から出る辺(=辺14)に軸を沿わせる
        pa = P[(v - 1) % n]
        ua = (P[v][0] - pa[0], P[v][1] - pa[1])
        La = math.hypot(*ua)
        ua = (ua[0] / La, ua[1] / La)
        bis = (u[0] - ua[0], u[1] - ua[1])            # 内角の二等分線(内向き)
        Lb = math.hypot(*bis)
        if Lb < 1e-9:
            continue
        bis = (bis[0] / Lb, bis[1] / Lb)
        half = y["ken"] * C["ken"] / 2.0
        off = (half + C["inubashiri"]) / math.sin(math.radians(53.0))
        c = (P[v][0] + bis[0] * off, P[v][1] + bis[1] * off)
        out.append((y["name"], _quad(c[0], c[1], u[0], u[1], half, half)))
    return out


def schema_check(d):
    """**同じ配列の要素が同じキーを持っているか。**欠けたキーは実装を黙って落とす。

    ⚠ 2026-08-29(EDO-0053): 中仕切を区画で割ったとき(7985cd7)、新しい2本に `h`(塀の丈)と
      `grid` を付け忘れていた。ビルダーの Stage6 が `KeyNotFoundException` で落ち、
      **中仕切がシーンに一度も建たず、旧い1本が区画外へ 2.63m 出たまま残った**。
      指図の側は「直った」ことになっていて、実装が落ちたことに誰も気づかなかった。
      → 図の検査で捕まえる。実装の例外は人が見ていないと消える。
    ⛔ 「大半の要素が持つキー」を必須とみなす。全要素が欠けているキーは任意扱いにする。
    """
    bad = []
    groups = []
    for arr in ("runs", "fences", "nakajikiri", "munes", "links", "komon", "yagura",
                "terraces", "kaidans", "rails", "wells", "gardens", "service"):
        items = [x for x in d.get(arr, []) if isinstance(x, dict)]
        if arr == "kaidans":
            # ⚠ **庭の段は郭をつなぐ石段と持ち物が違う**(蹴上・踏面・落差を持たない=導出値)。
            #   同じ籠で比べると「欠けている」と誤って鳴る。
            for kd in sorted(set(x.get("kind") for x in items), key=lambda z: str(z)):
                groups.append((arr + "/" + str(kd), [x for x in items if x.get("kind") == kd]))
            continue
        groups.append((arr, items))
    for arr, items in groups:
        if len(items) < 2:
            continue
        cnt = {}
        for it in items:
            for k in it:
                cnt[k] = cnt.get(k, 0) + 1
        # 註記の類(実装が引かないキー)は必須にしない
        DOC = ("_", "cert", "ruling", "src", "note", "on")
        need = [k for k, c in cnt.items()
                if k not in DOC and c >= len(items) * 0.75 and c < len(items)]
        for it in items:
            miss = [k for k in need if k not in it]
            if miss:
                bad.append("%s の %s に %s が無い(他の %d/%d 件は持っている)— "
                           "実装がキーを引いて落ちる"
                           % (arr, it.get("name", "?"), "/".join(sorted(miss)),
                              max(cnt[k] for k in miss), len(items)))
    return bad


def perimeter_closure_check(d, tol=0.4, step=0.2):
    """**外周が閉じているか** — 区画線をまたぐ線が、どこかで外周の物に当たるかを全長で測る。

    ⚠ 2026-08-29(EDO-0053)にユーザーが4箇所の穴を見つけて追加した。それまで外周の
      「閉じ」を測る検査は**一つも無かった** — barrier_check が見ていたのは内側の
      御錠口の結界だけで、その 0 件を外周の閉じの保証と読んでいた。
      `qa-and-pitfalls.md`「検査の文言と実装の集合を突き合わせる」。
    ⛔ **門の開口は、扉(`leaf`)を申告するまで穴として数える。**開口幅と敷居しか
      書いていない門は、建てれば素通しになる(御蔵門・東小門が実際そうだった)。
      ⭐ 扉の**出どころ**(`leaf.by`: 門の躯体に含まれる / 別部材)は閉じの判定を変えない —
      どちらでも開口は閉じる。出どころは実装が別部材を据えるかどうかだけを決める
      (2026-08-29: 冠木門は自前の扉を持つのに別部材を重ねて門の顔が白い板で覆われた)。
    ⛔ 隅櫓は**実際の平面形**で数える。「隅を置き換える」と書いても、辺と斜めに
      交わる矩形は辺の開口を端まで塞がない(北東隅で 1.41m と 0.34m 残っていた)。
    ⚠ **この検査は「図の上で何かが当たるか」しか見ない。**建てる対象の一覧(runs)に
      無い物 — 隅部材の腕のような joints にしか居ない物 — でも当たれば合格になる。
      **帳簿の側は `perimeter_ledger_check` が見る。**両方を回すこと。
    """
    P = d["polygon"]
    n = len(P)
    fps = _perimeter_footprints(d)
    cx = sum(q[0] for q in P) / n
    cz = sum(q[1] for q in P) / n
    bad = []
    for e in range(n):
        a, b = P[e], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -uz, ux
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (cx - mx) * nx + (cz - mz) * nz < 0:
            nx, nz = -nx, -nz                         # 内向き
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
                bad.append("辺%d の s%.1f〜%.1f(%.2fm)が外周として閉じていない — "
                           "塞ぐ物を指図に書く(門なら扉 leaf、隅なら隅部材)"
                           % (e, s0, s1, s1 - s0 + step))
    return bad


def _perimeter_spans(d):
    """**外周を塞ぐ物の s 区間の帳簿。**{辺: [(s0, s1, 名, 級)]} を返す。

    級は三つ:
      **遮蔽** — 人が越えられない囲い(表長屋・練塀・門扉・隅櫓)。`runs` / 門 / 櫓。
      **標示** — 境を示すだけの木柵(`fences`)。基礎も整地も持たない。
      **腕**   — 隅部材が兼ねる腕で、`joints` に `kado`(部材・折れ角・座)を持つもの。
                 `EdoMatsudairaDewaBuilder.PlaceKado` が joints を舐めて据えるので**実装へ渡る**。
      **腕(実装へ渡らない)** — 腕は宣言されているのに `kado` が無いもの。
                 ⛔ **閉じに数えない。**据える処理が読む欄が無いので、隅がそのまま口として残る。
    ⚠ 2026-08-29(EDO-0053 の後): 隅 P13 の辺13 側は腕だけが塞いだことになっていて、
      実装では隅がそのまま口として残った(外から敷地内へ 1m 踏み込める唯一の箇所)。
      面の当たりを見る `perimeter_closure_check` は腕を実体として数えるので鳴らなかった。
      2026-08-30 に腕を `kado` として実装が読む形へ移し、**読める腕だけ**を閉じに数えるようにした。
    """
    P = d["polygon"]
    C = d["const"]
    n = len(P)
    sp = dict((e, []) for e in range(n))

    def edge(e):
        a, b = P[e % n], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return a, ((b[0] - a[0]) / L, (b[1] - a[1]) / L), L

    for r in d["runs"]:
        sp[r["edge"] % n].append((r["s0"], r["s1"], r["name"], "遮蔽"))
    for f in d.get("fences", []):
        sp[f["edge"] % n].append((f["s0"], f["s1"], f["name"], "標示"))
    g = d.get("gate")
    if g:
        for nm, (s0, s1) in g["plan"].get("sPos", {}).items():
            if nm == "mon" and not g["plan"].get("leaf"):
                continue                              # 扉を申告しない開口は穴
            sp[g["edge"] % n].append((s0, s1, "表門/" + nm, "遮蔽"))
    for k in d.get("komon", []):
        if not k.get("leaf"):
            continue
        sp[k["edge"] % n].append((k["s"] - k["w"] / 2.0, k["s"] + k["w"] / 2.0, k["name"], "遮蔽"))
    fps = dict(_perimeter_footprints(d))
    for y in d.get("yagura", []):                     # 櫓は平面形を両隣の辺へ射影する
        q = fps.get(y["name"])
        if not q:
            continue
        v = y["vertex"] % n
        for e in ((v - 1) % n, v):
            a, u, L = edge(e)
            pr = [(p[0] - a[0]) * u[0] + (p[1] - a[1]) * u[1] for p in q]
            s0, s1 = max(0.0, min(pr)), min(L, max(pr))
            if s1 - s0 > 0.05:
                sp[e].append((s0, s1, y["name"], "遮蔽"))
    for j in d.get("joints", []):                     # 隅部材の腕
        if not j["at"].startswith("隅 P"):
            continue
        v = (j["edge"] + 1) % n
        ai, ao = _kado_arms(d, j)
        # **実装が読む形か**で級を分ける。`EdoMatsudairaDewaBuilder.PlaceKado` は joints を舐めて
        # `kado` を持つ継ぎ目だけ据えるので、`kado` の無い腕は図の上にしか無い。
        cls = "腕" if j.get("kado") else "腕(実装へ渡らない)"
        for arm, e, at_end in ((ai, j["edge"] % n, True),
                               (ao, (j["edge"] + 1) % n, False)):
            if arm <= 0:
                continue
            _, _, L = edge(e)
            s0, s1 = (L - arm, L) if at_end else (0.0, arm)
            sp[e].append((s0, s1, "Kado_P%d" % v, cls))
    return sp


def perimeter_ledger_check(d, tol=0.20):
    """**外周の帳簿検査** — 全ての頂点と全ての辺を、区間の帳簿で検める。

    見るのは三つ:
      1. **辺**: 建てる対象(`runs`/門扉/櫓/木柵)の s 区間の和が辺長を覆うか。
         覆わない区間は s の範囲つきで挙げる。腕しか跨いでいない区間は
         「腕は runs に無いので実装へ渡らない」と名指しする。
      2. **頂点**: 入ってくる端と出ていく端が `joints` の記述と同じ物か。
         隅の取り合いが無い / A・B が指図のどの物でもない / 実際に隅へ来る run と
         食い違う、のいずれも挙げる(=接する相手が joints に無い頂点)。
      3. **宣言**: 木柵だけの辺・意図した開放区間は `perimeterClosure` に宣言が要る。
         宣言の無い辺は既定=遮蔽として扱い、足りなければ挙げる。
         ⛔ **黙って見逃す形にしない** — 宣言を消せば検査が鳴る。

    ⚠ `perimeter_closure_check`(面の当たり)と役目が違う。あちらは「図の上で何かが
      当たるか」、こちらは「**建てる対象の帳簿で覆えているか**」。腕だけの隅は
      あちらを素通りする(2026-08-29 EDO-0053 の隅 P13)。
    """
    P = d["polygon"]
    n = len(P)
    sp = _perimeter_spans(d)
    decl = d.get("perimeterClosure", [])
    bad = []

    def declared(e, cls, s0=None, s1=None):
        for k in decl:
            if e not in k.get("edges", []) or k.get("class") != cls:
                continue
            if s0 is None or ("s0" not in k and "s1" not in k):
                return True
            if k.get("s0", -1e9) - 1e-6 <= s0 and s1 <= k.get("s1", 1e9) + 1e-6:
                return True
        return False

    # 1. 辺の被覆
    for e in range(n):
        a, b = P[e], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        segs = sorted([x for x in sp[e] if x[3] != "腕(実装へ渡らない)"], key=lambda x: x[0])
        holes, cur = [], 0.0
        for s0, s1, nm, cls in segs:
            if s0 > cur + 1e-9:
                holes.append((cur, min(s0, L)))
            cur = max(cur, s1)
        if cur < L - 1e-9:
            holes.append((cur, L))
        for h0, h1 in holes:
            if h1 - h0 < tol or declared(e, "開放", h0, h1):
                continue
            arms = [x for x in sp[e] if x[3].startswith("腕") and x[0] < h1 - 1e-6 and x[1] > h0 + 1e-6]
            why = ("隅部材の腕 %s が図の上では跨いでいるが、その取り合いに `kado` が無いので"
                   "**実装(PlaceKado)が据えない** — joints へ `kado`(part/deg/seat)を書くこと"
                   % arms[0][2]) if arms else \
                  ("塞ぐ物を指図に書くか、開けておく意図なら perimeterClosure に"
                   "『開放』として辺と s を宣言すること")
            bad.append("辺%d の s%.2f〜%.2f(%.2fm)が外周の帳簿で覆われていない — %s"
                       % (e, h0, h1, h1 - h0, why))
        if segs and all(x[3] == "標示" for x in segs) and not declared(e, "標示"):
            bad.append("辺%d は木柵(標示)だけで閉じている — 遮蔽でない旨を perimeterClosure に"
                       "宣言すること(法面で守るなら、その旨を宣言に書く)" % e)
    for k in decl:                                    # 効かなくなった宣言を残さない
        for e in k.get("edges", []):
            if k.get("class") != "標示":
                continue
            if any(x[3] == "遮蔽" for x in sp[e % n]):
                bad.append("perimeterClosure が辺%d を『標示』と宣言しているが、遮蔽の囲いが"
                           "置かれている — 宣言と実物が食い違う" % e)

    # 2. 頂点の取り合い
    known = set(r["name"] for r in d["runs"]) | set(f["name"] for f in d.get("fences", []))
    known |= set(y["name"] for y in d.get("yagura", [])) | set(k["name"] for k in d.get("komon", []))
    if d.get("gate"):
        known |= set("表門/" + nm for nm in d["gate"]["plan"].get("sPos", {}))
    cj = _corner_joints(d)
    for v in range(n):
        j = cj.get(v)
        if j is None:
            bad.append("隅 P%d に取り合い(joints)が無い — 接する二者とその面が決まっていない" % v)
            continue
        ein, eout = (v - 1) % n, v % n
        inn = [x for x in sp[ein] if not x[3].startswith("腕")]
        out = [x for x in sp[eout] if not x[3].startswith("腕")]
        last = max(inn, key=lambda x: x[1]) if inn else None
        first = min(out, key=lambda x: x[0]) if out else None
        for side, x, want, face, e in (("入り", last, j["a"], j["aFace"], ein),
                                       ("出", first, j["b"], j["bFace"], eout)):
            if want.startswith("—"):
                continue                              # 頂点そのもの(隅櫓が置き換える側)
            if want not in known:
                bad.append("隅 P%d(%s)の%s側が指図のどの物でもない物 %r を指している — "
                           "名前が食い違っていると実装は面を測れない" % (v, j["id"], side, want))
                continue
            if not face or "面" not in face and "小口" not in face and "端" not in face:
                bad.append("隅 P%d(%s)の%s側の面 %r が面として読めない — "
                           "芯・ピボットでなく面で書くこと(絶対規則5)" % (v, j["id"], side, face))
            if x is None:
                bad.append("隅 P%d(%s)の%s側(辺%d)に外周の物が一つも無い" % (v, j["id"], side, e))
            elif x[2] != want:
                bad.append("隅 P%d(%s)の%s側は joints が %s と書くのに、辺%d で隅へ来るのは %s — "
                           "取り合い表と帳簿が別のことを言っている" % (v, j["id"], side, want, e, x[2]))

    # 3. 門扉の出どころ
    gates = [("表門", d["gate"]["plan"].get("leaf"))] if d.get("gate") else []
    gates += [(k["name"], k.get("leaf")) for k in d.get("komon", [])]
    for nm, lf in gates:
        if not lf:
            bad.append("門 %s に扉(leaf)が無い — 開口が素通しになる" % nm)
        elif not lf.get("by"):
            bad.append("門 %s の扉に出どころ(leaf.by)が無い — 躯体が持つのか別部材を据えるのかが"
                       "決まらず、実装が扉を二重に重ねる(2026-08-29 に冠木門で実際に起きた)" % nm)
    return bad


def mune_wall_clearance_check(d):
    """**棟の軒先と外周の塀の内面の離れ**が const wallNear 以上か。
    ⚠ wallNear は前からあったのに、それを測る検査が無く飾りになっていた。
      2026-08-29 に長局(南)の屋根が土井境の土塀と 0.28m しか離れていないのを
      ユーザーが見つけた(EDO-0053)。"""
    C = d["const"]
    gr = RGrid(d)
    P = d["polygon"]
    n = len(P)
    lim = C["wallNear"]
    bad = []
    for m in d["munes"]:
        worst, at = 1e9, None
        u = m["u0"]
        while u <= m["u1"] + 1e-9:
            for v in (m["v0"], m["v1"]):
                w = gr.W(u, v)
                dd = min(_seg_d(w, P[i], P[(i + 1) % n]) for i in range(n))
                if dd < worst:
                    worst, at = dd, (u, v)
            u += 0.5
        v = m["v0"]
        while v <= m["v1"] + 1e-9:
            for u2 in (m["u0"], m["u1"]):
                w = gr.W(u2, v)
                dd = min(_seg_d(w, P[i], P[(i + 1) % n]) for i in range(n))
                if dd < worst:
                    worst, at = dd, (u2, v)
            v += 0.5
        clear = worst - C["nokiE"] - C["dobeiT"] / 2.0
        if clear < lim:
            bad.append("棟 %s の軒先と外周の塀の内面が %.2fm(規定 wallNear %.2fm)— u%.1f v%.1f"
                       % (m["name"], clear, lim, at[0], at[1]))
    return bad


# ---------------------------------------------------------------- 外周の閉じ(検査)
def _corner_path(d, ea, back, eb, fwd):
    """隅をまたぐ展開の道筋。辺 ea の終端から back[m] 手前 → 隅 → 辺 eb の fwd[m] 先。"""
    P = d["polygon"]
    n = len(P)
    La = math.hypot(P[(ea + 1) % n][0] - P[ea][0], P[(ea + 1) % n][1] - P[ea][1])
    return [(ea, La - back, La), (eb, 0.0, fwd)], back


def _dem_at(dem, x, z):
    """正本DEMの切り出し(世界2m格子)から造成前の地盤を双一次で拾う(規則12)。"""
    fx = (x - dem["x0"]) / dem["step"]
    fz = (z - dem["z0"]) / dem["step"]
    i, j = int(math.floor(fx)), int(math.floor(fz))
    if i < 0 or j < 0 or i + 1 >= dem["nx"] or j + 1 >= dem["nz"]:
        return None
    tx, tz = fx - i, fz - j
    q = [dem["h"][j][i], dem["h"][j][i + 1], dem["h"][j + 1][i], dem["h"][j + 1][i + 1]]
    if any(v is None for v in q):
        return None
    return (q[0] * (1 - tx) + q[1] * tx) * (1 - tz) + (q[2] * (1 - tx) + q[3] * tx) * tz


def _ground_along(d, dem, path, off=1.5, step=0.5):
    """道筋に沿って、内側 off[m] の造成前の地盤を拾う。x は展開の通し距離[m]。
    ⚠ 地盤は **正本DEMの切り出し** から採る。matsudaira_dewa_terrain.json は穴があり、
      辺1 の内側 1.5m では null しか返らなかった(2026-08-29)。"""
    P = d["polygon"]
    n = len(P)
    out = []
    x = 0.0
    for e, s0, s1 in path:
        a, b = P[e % n], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -uz, ux
        cx = sum(q[0] for q in P) / n
        cz = sum(q[1] for q in P) / n
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (cx - mx) * nx + (cz - mz) * nz < 0:
            nx, nz = -nx, -nz
        sv = s0
        while sv <= s1 + 1e-9:
            wx, wz = a[0] + ux * sv + nx * off, a[1] + uz * sv + nz * off
            h = _dem_at(dem, wx, wz)
            if h is not None:
                out.append((x + (sv - s0), h))
            sv += step
        x += (s1 - s0)
    return out


def corner_elev_svg(d, dem, ea, back, eb, fwd, title):
    """隅をまたぐ塀の展開立面。**設計値どおりに描く**(案は描かない)。
    2026-08-29 の裁定で辺0/辺1/辺2 の天端は隅で揃った — その通りを図で確かめられるようにする。"""
    C = d["const"]
    path, xc = _corner_path(d, ea, back, eb, fwd)
    W_ = back + fwd
    g = _ground_along(d, dem, path)
    g3 = _ground_along(d, dem, path, off=4.5)
    ys = [h for _, h in g] + [h for _, h in g3]
    tops = []
    P = d["polygon"]
    n = len(P)
    for r in d["runs"]:
        if r["edge"] not in (ea % n, eb % n):
            continue
        tops += [r.get("seat0", r["seat"]) + C["dobeiH"], r.get("seat1", r["seat"]) + C["dobeiH"]]
    y0 = min(ys) - 0.6
    y1 = max(tops) + 0.6 if tops else max(ys) + 3
    S = 30.0
    LEFT, TOP, BOT = 46.0, 20.0, 26.0
    Wpx = LEFT + W_ * S + 14
    Hpx = TOP + (y1 - y0) * S + BOT
    X = lambda m_: LEFT + m_ * S
    Y = lambda h_: TOP + (y1 - h_) * S
    o = _sv(Wpx, Hpx, title)
    h_ = math.ceil(y0)
    while h_ <= y1:
        o.append(LN(LEFT - 4, Y(h_), Wpx - 8, Y(h_), "var(--rule)", 0.6, None, 0.55))
        o.append(T(LEFT - 7, Y(h_) + 3.4, "%g" % h_, "sl", "end", 9.0))
        h_ += 1.0
    for pts, sw, dash, op in ((g, 1.2, "4 3", 1.0), (g3, 0.9, "2 3", 0.6)):
        o.append('<polyline points="%s" fill="none" stroke="var(--dim)" stroke-width="%.1f" '
                 'stroke-dasharray="%s" opacity="%.1f"/>'
                 % (" ".join("%.1f,%.1f" % (X(x_), Y(h_)) for x_, h_ in pts), sw, dash, op))
    o.append(T(X(0.6), Y(g[0][1]) + 13, "地面(塀の内側 1.5m ─ / 4.5m ┈)", "sl", "start", 9.0))

    for r in d["runs"]:
        if r["edge"] == ea % n:
            La = math.hypot(P[(ea + 1) % n][0] - P[ea % n][0], P[(ea + 1) % n][1] - P[ea % n][1])
            xa, xb = r["s0"] - (La - back), r["s1"] - (La - back)
        elif r["edge"] == eb % n:
            xa, xb = xc + r["s0"], xc + r["s1"]
        else:
            continue
        xa, xb = max(0.0, xa), min(W_, xb)
        if xb - xa < 0.2:
            continue
        t0 = r.get("seat0", r["seat"])
        t1 = r.get("seat1", r["seat"])
        # run 内の一次補間で天端を引く
        def seat_at(xx):
            if r["edge"] == ea % n:
                sv = xx + (La - back)
            else:
                sv = xx - xc
            f = (sv - r["s0"]) / max(1e-9, r["s1"] - r["s0"])
            return t0 + (t1 - t0) * max(0.0, min(1.0, f))
        sa, sb = seat_at(xa), seat_at(xb)
        o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="var(--hei)" '
                 'stroke="var(--ink)" stroke-width="0.8" opacity="0.30"/>'
                 % (X(xa), Y(sa + C["dobeiH"]), X(xb), Y(sb + C["dobeiH"]),
                    X(xb), Y(sb), X(xa), Y(sa)))
        gs = [(x_, h_) for x_, h_ in (g + g3) if xa - 0.6 <= x_ <= xb + 0.6]
        if gs:
            lo = min(h_ for _, h_ in gs)
            o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="url(#pi%d)" '
                     'stroke="var(--ishi)" stroke-width="0.8"/>'
                     % (X(xa), Y(sa), X(xb), Y(sb), X(xb), Y(lo), X(xa), Y(lo), _SVN[0]))
        if (xb - xa) >= 3.0:                          # 窓の端で切れた run に札は付けない
            lbl = "%s　足元 %.2f→%.2f" % (r["name"], t0, t1) if abs(t1 - t0) > 0.005 \
                else "%s　足元 %.2f" % (r["name"], t0)
            o.append(T((X(xa) + X(xb)) / 2, Y(max(sa, sb) + C["dobeiH"]) - 6, lbl, "sl", "middle",
                       max(8.0, min(10.5, (xb - xa) * S / (len(lbl) * 0.62)))))
    o.append(LN(X(xc), TOP + 2, X(xc), Hpx - BOT + 4, "var(--shu)", 1.0, "3 3", 0.8))
    o.append(T(X(xc), Hpx - 8, "▲ 敷地の角", "sl", "middle", 9.5, "var(--shu)"))
    o.append(T(LEFT, Hpx - 8, "角で塀のてっぺんが揃っている(段差なし)", "sl", "start", 9.5))
    o.append("</svg>")
    return "\n".join(o)


def nagatsubone_svg(d):
    """長局(南)と土井境の離れ。**設計値どおりに描く**(案は描かない)。"""
    C = d["const"]
    gr = RGrid(d)
    P = d["polygon"]
    m = [x for x in d["munes"] if x["name"] == "NagatsuboneS"][0]
    mn = [x for x in d["munes"] if x["name"] == "NagatsuboneN"][0]
    u0, u1, v0, v1 = m["u0"], m["u1"], m["v0"], m["v1"]
    pr = LProj(-28, 2, 46, 66, W=430.0)
    o = _sv(pr.W + 54, pr.H + 16, "長局(南)と土井境")
    OX = 46.0
    PX = lambda u: OX + pr.X(u)
    PY = lambda v: pr.Y(v)
    gpts = [gr.L(*q) for q in P]
    seg = []
    for i2 in range(len(gpts)):
        a, b = gpts[i2], gpts[(i2 + 1) % len(gpts)]
        if max(a[1], b[1]) < 44 or min(a[1], b[1]) > 70:
            continue
        seg.append((a, b))
    for a, b in seg:
        dx, dv = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dv)
        if L < 1e-6:
            continue
        t = (C["dobeiT"] / 2.0) / C["ken"]
        nx_, nv_ = -dv / L * t, dx / L * t
        o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="var(--hei)" opacity="0.28"/>'
                 % (PX(a[0] + nx_), PY(a[1] + nv_), PX(b[0] + nx_), PY(b[1] + nv_),
                    PX(b[0] - nx_), PY(b[1] - nv_), PX(a[0] - nx_), PY(a[1] - nv_)))
        o.append(LN(PX(a[0]), PY(a[1]), PX(b[0]), PY(b[1]), "var(--ink)", 1.6))
    o.append(R(PX(mn["u0"]), PY(mn["v0"]), (mn["u1"] - mn["u0"]) * pr.s,
               (mn["v1"] - mn["v0"]) * pr.s, fill="var(--ink-lo)", stroke="var(--dim)", sw=0.8))
    o.append(T(PX((mn["u0"] + mn["u1"]) / 2.0), PY((mn["v0"] + mn["v1"]) / 2.0) + 4,
               "長局(北)", "sl", "middle", 10.0))
    o.append(R(PX(u0), PY(v0), (u1 - u0) * pr.s, (v1 - v0) * pr.s,
               fill="var(--nagaya)", stroke="var(--ink)", sw=1.2, op=0.30))
    e = C["nokiE"] / C["ken"]
    o.append(R(PX(u0 - e), PY(v0 - e), (u1 - u0 + 2 * e) * pr.s, (v1 - v0 + 2 * e) * pr.s,
               fill="none", stroke="var(--shu)", sw=0.9, dash="3 2"))
    o.append(T(PX((u0 + u1) / 2.0), PY((v0 + v1) / 2.0) + 4,
               "長局(南) %d間×%d間　局 %d室 %d畳" % (u1 - u0, v1 - v0, len(m.get("rooms", [])),
                                              sum(r["tatami"] for r in m.get("rooms", []))),
               "sl", "middle", 10.5))
    # 中仕切の板塀
    for w in d.get("nakajikiri", []):
        a, b = w["a"], w["b"]
        if max(a[1], b[1]) < 44 or min(a[1], b[1]) > 70:
            continue
        o.append(LN(PX(a[0]), PY(a[1]), PX(b[0]), PY(b[1]), "var(--nagaya)", 2.0))
    o.append(T(PX(-26), PY(66) - 5, "中仕切の板塀", "sl", "start", 9.0, "var(--nagaya)"))
    # 一番詰まる所の離れ
    def _dl(w):
        return min(_seg_d(w, P[i2], P[(i2 + 1) % len(P)]) for i2 in range(len(P)))
    worst, at = 1e9, None
    uu = u0
    while uu <= u1 + 1e-9:
        dd = _dl(gr.W(uu, v1))
        if dd < worst:
            worst, at = dd, uu
        uu += 0.25
    clear = worst - C["nokiE"] - C["dobeiT"] / 2.0
    col = "var(--shu)" if clear < C["wallNear"] else "var(--take)"
    o.append(LN(PX(at), PY(v1), PX(at), PY(v1 + worst / C["ken"]), col, 1.6))
    o.append(T(PX(at) + 5, PY(v1 + worst / C["ken"] * 0.5) + 3.5,
               "屋根の先から塀まで %.2fm(空けたい %.2fm)" % (clear, C["wallNear"]),
               "sl", "start", 10.0, col))
    gap = (v0 - mn["v1"]) * C["ken"] - 2 * C["nokiE"]
    gcol = "var(--shu)" if gap < 0.30 else "var(--take)"
    xg = PX(max(u0, mn["u0"]) + 2.0)
    o.append(LN(xg, PY(mn["v1"]), xg, PY(v0), gcol, 1.6))
    o.append(T(xg + 5, (PY(mn["v1"]) + PY(v0)) / 2 + 3.5,
               "北隣の建物と屋根の先どうしの空き %.2fm" % gap, "sl", "start", 10.0, gcol))
    for v in range(46, 67, 2):
        o.append(T(OX - 6, PY(v) + 3.4, "v%d" % v, "sl", "end", 8.5))
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- 裁定図(EDO-0053)
# ⚠ **この節は裁定が出たら丸ごと差し替える。**規則4「指図は現況だけを載せる」に対する
#   例外は「まだ決まっていない選択肢を並べて見せる図」だけで、決まった後に残すと両論併記になる。
def _corner_path(d, ea, back, eb, fwd):
    """隅をまたぐ展開の道筋。辺 ea の終端から back[m] 手前 → 隅 → 辺 eb の fwd[m] 先。"""
    P = d["polygon"]
    n = len(P)
    La = math.hypot(P[(ea + 1) % n][0] - P[ea][0], P[(ea + 1) % n][1] - P[ea][1])
    return [(ea, La - back, La), (eb, 0.0, fwd)], back


def _dem_at(dem, x, z):
    """正本DEMの切り出し(世界2m格子)から造成前の地盤を双一次で拾う(規則12)。"""
    fx = (x - dem["x0"]) / dem["step"]
    fz = (z - dem["z0"]) / dem["step"]
    i, j = int(math.floor(fx)), int(math.floor(fz))
    if i < 0 or j < 0 or i + 1 >= dem["nx"] or j + 1 >= dem["nz"]:
        return None
    tx, tz = fx - i, fz - j
    q = [dem["h"][j][i], dem["h"][j][i + 1], dem["h"][j + 1][i], dem["h"][j + 1][i + 1]]
    if any(v is None for v in q):
        return None
    return (q[0] * (1 - tx) + q[1] * tx) * (1 - tz) + (q[2] * (1 - tx) + q[3] * tx) * tz


def _ground_along(d, dem, path, off=1.5, step=0.5):
    """道筋に沿って、内側 off[m] の造成前の地盤を拾う。x は展開の通し距離[m]。
    ⚠ 地盤は **正本DEMの切り出し** から採る。matsudaira_dewa_terrain.json は穴があり、
      辺1 の内側 1.5m では null しか返らなかった(2026-08-29)。"""
    P = d["polygon"]
    n = len(P)
    out = []
    x = 0.0
    for e, s0, s1 in path:
        a, b = P[e % n], P[(e + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -uz, ux
        cx = sum(q[0] for q in P) / n
        cz = sum(q[1] for q in P) / n
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (cx - mx) * nx + (cz - mz) * nz < 0:
            nx, nz = -nx, -nz
        sv = s0
        while sv <= s1 + 1e-9:
            wx, wz = a[0] + ux * sv + nx * off, a[1] + uz * sv + nz * off
            h = _dem_at(dem, wx, wz)
            if h is not None:
                out.append((x + (sv - s0), h))
            sv += step
        x += (s1 - s0)
    return out


def corner_elev_svg(d, dem, ea, back, eb, fwd, title):
    """隅をまたぐ塀の展開立面。**設計値どおりに描く**(案は描かない)。
    2026-08-29 の裁定で辺0/辺1/辺2 の天端は隅で揃った — その通りを図で確かめられるようにする。"""
    C = d["const"]
    path, xc = _corner_path(d, ea, back, eb, fwd)
    W_ = back + fwd
    g = _ground_along(d, dem, path)
    g3 = _ground_along(d, dem, path, off=4.5)
    ys = [h for _, h in g] + [h for _, h in g3]
    tops = []
    P = d["polygon"]
    n = len(P)
    for r in d["runs"]:
        if r["edge"] not in (ea % n, eb % n):
            continue
        tops += [r.get("seat0", r["seat"]) + C["dobeiH"], r.get("seat1", r["seat"]) + C["dobeiH"]]
    y0 = min(ys) - 0.6
    y1 = max(tops) + 0.6 if tops else max(ys) + 3
    S = 30.0
    LEFT, TOP, BOT = 46.0, 20.0, 26.0
    Wpx = LEFT + W_ * S + 14
    Hpx = TOP + (y1 - y0) * S + BOT
    X = lambda m_: LEFT + m_ * S
    Y = lambda h_: TOP + (y1 - h_) * S
    o = _sv(Wpx, Hpx, title)
    h_ = math.ceil(y0)
    while h_ <= y1:
        o.append(LN(LEFT - 4, Y(h_), Wpx - 8, Y(h_), "var(--rule)", 0.6, None, 0.55))
        o.append(T(LEFT - 7, Y(h_) + 3.4, "%g" % h_, "sl", "end", 9.0))
        h_ += 1.0
    for pts, sw, dash, op in ((g, 1.2, "4 3", 1.0), (g3, 0.9, "2 3", 0.6)):
        o.append('<polyline points="%s" fill="none" stroke="var(--dim)" stroke-width="%.1f" '
                 'stroke-dasharray="%s" opacity="%.1f"/>'
                 % (" ".join("%.1f,%.1f" % (X(x_), Y(h_)) for x_, h_ in pts), sw, dash, op))
    o.append(T(X(0.6), Y(g[0][1]) + 13, "地面(塀の内側 1.5m ─ / 4.5m ┈)", "sl", "start", 9.0))

    for r in d["runs"]:
        if r["edge"] == ea % n:
            La = math.hypot(P[(ea + 1) % n][0] - P[ea % n][0], P[(ea + 1) % n][1] - P[ea % n][1])
            xa, xb = r["s0"] - (La - back), r["s1"] - (La - back)
        elif r["edge"] == eb % n:
            xa, xb = xc + r["s0"], xc + r["s1"]
        else:
            continue
        xa, xb = max(0.0, xa), min(W_, xb)
        if xb - xa < 0.2:
            continue
        t0 = r.get("seat0", r["seat"])
        t1 = r.get("seat1", r["seat"])
        # run 内の一次補間で天端を引く
        def seat_at(xx):
            if r["edge"] == ea % n:
                sv = xx + (La - back)
            else:
                sv = xx - xc
            f = (sv - r["s0"]) / max(1e-9, r["s1"] - r["s0"])
            return t0 + (t1 - t0) * max(0.0, min(1.0, f))
        sa, sb = seat_at(xa), seat_at(xb)
        o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="var(--hei)" '
                 'stroke="var(--ink)" stroke-width="0.8" opacity="0.30"/>'
                 % (X(xa), Y(sa + C["dobeiH"]), X(xb), Y(sb + C["dobeiH"]),
                    X(xb), Y(sb), X(xa), Y(sa)))
        gs = [(x_, h_) for x_, h_ in (g + g3) if xa - 0.6 <= x_ <= xb + 0.6]
        if gs:
            lo = min(h_ for _, h_ in gs)
            o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="url(#pi%d)" '
                     'stroke="var(--ishi)" stroke-width="0.8"/>'
                     % (X(xa), Y(sa), X(xb), Y(sb), X(xb), Y(lo), X(xa), Y(lo), _SVN[0]))
        lbl = "%s　足元 %.2f→%.2f" % (r["name"], t0, t1) if abs(t1 - t0) > 0.005 \
            else "%s　足元 %.2f" % (r["name"], t0)
        o.append(T((X(xa) + X(xb)) / 2, Y(max(sa, sb) + C["dobeiH"]) - 6,
                   fit(lbl, (xb - xa) * S) and lbl, "sl", "middle",
                   max(8.0, min(10.5, (xb - xa) * S / (len(lbl) * 0.62)))))
    o.append(LN(X(xc), TOP + 2, X(xc), Hpx - BOT + 4, "var(--shu)", 1.0, "3 3", 0.8))
    o.append(T(X(xc), Hpx - 8, "▲ 敷地の角", "sl", "middle", 9.5, "var(--shu)"))
    o.append(T(LEFT, Hpx - 8, "角で塀のてっぺんが揃っている(段差なし)", "sl", "start", 9.5))
    o.append("</svg>")
    return "\n".join(o)


# ================================================================ 植栽(2026-08-30)
# ⛔ 数値の正典は json(設計値)と docs/asset-index.tsv(部材の実寸・三角数)。
#    ここには**式と作図だけ**を置き、寸法も本数も書かない(CLAUDE.md 規則4)。
_AIDX = {}


def asset_index():
    """`docs/asset-index.tsv` を読む。**樹の実寸・ピボット・三角数の正典**。

    ⚠ 指図(json)にはこの値を**写さない** — 部材を差し替えたら tsv が変わり、
      写した値だけが古いまま残るため。図も表もここから引く。"""
    if _AIDX:
        return _AIDX
    with io.open(os.path.join(ROOT, "docs/asset-index.tsv"), encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("#"):
                continue
            c = ln.rstrip("\n").split("\t")
            # ⚠ **fbx も読む。**自作の部材(`Assets/Edo/Models/…`)は prefab を持たず
            #   `EdoAssets.Own.*` が fbx を直に指すので、prefab だけに絞ると
            #   **自作の木が丸ごと目録から落ち、庭園図に円が描かれない**(2026-09-01)。
            #   同じ名が両方にあるときは prefab を優先する(先勝ちにしない)。
            if len(c) < 12 or c[0] == "path" or c[3] not in ("prefab", "fbx"):
                continue
            if c[3] == "fbx" and c[1] in _AIDX:
                continue
            try:
                rec = {"path": c[0], "sx": float(c[4]), "sy": float(c[5]),
                       "sz": float(c[6]), "piv": float(c[7]),
                       "tris": int(c[9]), "rend": int(c[10])}
            except ValueError:
                continue
            if c[3] == "prefab" or c[1] not in _AIDX:
                _AIDX[c[1]] = rec
    return _AIDX


def part_geom(pt):
    """部材 1 点の据えたあとの見え寸。(樹冠径 m, 樹高 m, 三角数)。無い部材は None。"""
    rec = asset_index().get(pt["prefab"])
    if rec is None:
        return None
    s = float(pt.get("scale", 1.0))
    return (max(rec["sx"], rec["sz"]) * s, rec["sy"] * s, rec["tris"])


def crown_r(d, pt):
    """部材 1 点の**樹冠の半径[間]**。引けなければ None。

    ⭐ 正典は `docs/asset-index.tsv`(据えた実寸)。⚠ **自作の木がまだ目録に無い**あいだだけ
      `plantRule.crownFallback`(FBX の頂点から直に測った径[m])で繋ぐ。"""
    K = d["const"]["ken"]
    g = part_geom(pt)
    if g is not None:
        return g[0] / 2.0 / K
    fb = d["plantRule"].get("crownFallback") or {}
    w = fb.get(pt.get("prefab"))
    if w is None:
        return None
    return float(w) * float(pt.get("scale", 1.0)) / 2.0 / K


def layer_crown_r(d, pl):
    """層の**いちばん大きい樹冠の半径[間]**(引けない部材は飛ばす)。全部引けなければ 0。"""
    rs = [crown_r(d, pt) for pt in pl.get("parts", [])]
    rs = [r for r in rs if r is not None]
    return max(rs) if rs else 0.0


def crown_fallback_check(d):
    """⚠ **仮値の自動失効。**目録に入った部材が `crownFallback` に残っていたら鳴らす
    (⛔ 同じ事実が二箇所に残る=規則4)。あわせて `crownRule` の役の部材が
    **一つも測れていない**ときは「合格」でなく「**回っていない**」と言う。"""
    bad = []
    fb = d["plantRule"].get("crownFallback") or {}
    idx = asset_index()
    for nm in fb:
        if nm in idx:
            bad.append("`plantRule.crownFallback` の %s が **目録に入った** — "
                       "仮値を消して `asset-index.tsv` へ一本化すること(規則4)" % nm)
    roles = set((d["plantRule"].get("crownRule") or {}).get("roles", []))
    for pl in d.get("planting", []):
        if pl.get("role") not in roles and pl.get("pondClr") != "crown":
            continue
        if not any(crown_r(d, pt) is not None for pt in pl.get("parts", [])):
            bad.append("植栽 %s/%s は `crownRule` の役だが**樹冠が一つも測れない** — "
                       "この層の退避は**検査が回っていない**(合格ではない)"
                       % (pl["zone"], pl["layer"]))
    return bad


def layer_parts(layer):
    """層の `parts` を 1 本ずつに展開する(本数ぶんの部材の列)。順は指図のまま。"""
    out = []
    for pt in layer.get("parts", []):
        out += [pt] * int(pt.get("n", 0))
    return out


def _rng(key):
    """層の名から決まる乱数。⚠ str の hash() はプロセスごとに塩が変わるので crc32。"""
    import random as _r
    return _r.Random(_zlib.crc32(key.encode("utf-8")) & 0xffffffff)


# ---------------------------------------------------------------- 退避(木を植えない所)
def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - (a[0] + dx * t), p[1] - (a[1] + dy * t))


def keepout_shapes(d):
    """**木を植えてはいけない物**を (種別, 幾何[uv 間], 退避[間], 名) で並べる。

    退避の値は `plantRule.keepout` が正典。⛔ ここで数値を作らない。
    グリッドは回転だけ(拡大縮小なし)なので、uv[間]×ken = 世界の m と等長。"""
    ko = d["plantRule"]["keepout"]
    gr = RGrid(d)
    out = []
    for m in d["munes"]:
        out.append(("rect", (m["u0"], m["v0"], m["u1"], m["v1"]), ko["mune"], "棟 " + m["name"], "mune"))
    for l in d["links"]:
        out.append(("rect", (l["u0"], l["v0"], l["u1"], l["v1"]), ko["link"], "渡廊下 " + l["name"], "link"))
    for s in d["service"]:
        out.append(("rect", (s["u0"], s["v0"], s["u1"], s["v1"]), ko["service"], "附属屋 " + s["name"], "service"))
    for w in d.get("wells", []):
        out.append(("pt", (w["u"], w["v"]), ko["well"], "井戸 " + w["name"], "well"))
    for k in d.get("kaidans", []):
        # ⚠ **庭の段は点として二重に取らない** — 載っている園路の退避(`route`)が受ける。
        #   幅 0.9m の自然石の段に石段の退避(2間)を掛けると、築山の中腹に木が一本も
        #   置けなくなる(2026-09-01)。
        if "pos" in k and k.get("kind") != "庭の段":
            out.append(("pt", tuple(k["pos"]), ko["kaidan"], "石段 " + k["name"], "kaidan"))
    for nj in d.get("nakajikiri", []):
        out.append(("seg", (tuple(nj["a"]), tuple(nj["b"])), ko["nakajikiri"], "中仕切 " + nj["name"], "nakajikiri"))
    for r in d.get("rails", []):
        pts = r["pts"]
        for i in range(len(pts) - 1):
            out.append(("seg", (tuple(pts[i]), tuple(pts[i + 1])), ko["rail"], "竹垣 " + r["name"], "rail"))
    for t in d.get("tenkei", []):
        if "pts" in t:
            for i in range(len(t["pts"]) - 1):
                out.append(("seg", (tuple(t["pts"][i]), tuple(t["pts"][i + 1])),
                            ko["roji"], "露地 " + t["name"], "roji"))
        elif "a" in t:
            out.append(("seg", (tuple(t["a"]), tuple(t["b"])), ko["kaki"], "垣 " + t["name"], "kaki"))
        else:
            out.append(("pt", (t["u"], t["v"]), ko["tenkei"], "点景 " + t["name"], "tenkei"))
    for r in d.get("routes", []):
        for i in range(len(r["pts"]) - 1):
            out.append(("seg", (tuple(r["pts"][i]), tuple(r["pts"][i + 1])),
                        ko["route"], "園路 " + r["label"], "route"))
    # ⭐ **遣水の野筋**(2026-09-02 庭方 回答1)。退避の幅は `nosuji.w` の**半幅**(従属値)で、
    #   効く役は `plantRule.keepoutRolesOnly.nosuji` が決める(高木・中木だけ)。
    #   ⛔ 低木・刈込と下草には掛けない — 根が浅く、**野筋の肩がむしろ定位置**。
    ym = ((d.get("sensui") or {}).get("yarimizu") or {})
    if ym.get("pts") and ym.get("nosuji"):
        half = float(ym["nosuji"]["w"]) / 2.0
        q = [tuple(x) for x in ym["pts"]]
        for i in range(len(q) - 1):
            out.append(("seg", (q[i], q[i + 1]), half, "野筋 " + ym.get("name", "MZ_Yarimizu"),
                        "nosuji"))
    for nm, q in _perimeter_footprints(d):
        mg = ko["fence"] if nm.startswith("F_") else ko["run"]
        out.append(("poly", [gr.L(p[0], p[1]) for p in q], mg, "外周 " + nm, "run"))
    return out


def _ko_value(d, v):
    """退避の値。数なら間、文字列なら `const` の欄を**間に直して**使う
    (`\"nokiE\"` → 軒の出 0.90m ÷ 1間)。⛔ 間に直した数を指図へ書き写さない。"""
    if isinstance(v, str):
        return float(d["const"][v]) / float(d["const"]["ken"])
    return float(v)


def free_fn(d):
    """`free(u, v, clr)` — その点に木を立ててよいか。clr は層ごとの上乗せ[間]。

    ⛔ 中心どうしの距離では見ない。**退避は物の外形から測る**(規則5と同じ考え方)。
    戻り値は当たった物の名(当たらなければ None)— どれに載ったかを検査が言えるように。"""
    shapes = []
    for kind, g, mg, nm, kk in keepout_shapes(d):
        if kind == "rect":
            bb = (g[0], g[1], g[2], g[3])
        elif kind == "pt":
            bb = (g[0], g[1], g[0], g[1])
        elif kind == "seg":
            bb = (min(g[0][0], g[1][0]), min(g[0][1], g[1][1]),
                  max(g[0][0], g[1][0]), max(g[0][1], g[1][1]))
        else:
            bb = (min(q[0] for q in g), min(q[1] for q in g),
                  max(q[0] for q in g), max(q[1] for q in g))
        shapes.append((kind, g, mg, nm, bb, kk))
    P = d["polygon"]
    gr = RGrid(d)
    par = d["plantRule"]["keepout"]["parcel"]
    byrole = d["plantRule"].get("keepoutByRole", {})
    onlyrole = d["plantRule"].get("keepoutRolesOnly", {})
    exempt = set(d["plantRule"].get("clrExempt", []))
    ks = (d.get("sensui") or {}).get("pond")
    _cru = d["plantRule"].get("crownRule") or {}
    crole = set(_cru.get("roles", []))
    cmode = _cru.get("mode", "max")

    def hit(u, v, clr, role=None, skip=None, pondClr=None, crownR=0.0, ovr=None):
        """clr = 層ごとの上乗せ[間] / role = 層の役(退避の上書き) /
        skip = **その層だけ退避を外す物の名**(生垣の内側へ植える等) /
        pondClr = 池の汀からの離れ[間]。`"crown"` なら**樹冠の半径**(層が上書きするとき) /
        crownR = 層の**樹冠の半径[間]**(`plantRule.crownRule.roles` の役だけ退避に足す)

        ⭐ **退避は樹冠の外周から取る**(庭方 2026-09-01 回答2-②)— 芯で測ると
          樹冠が棟・塀・州へ食い込む。⛔ `clrExempt` の欄には足さない(枝は張り出してよい)。"""
        ov = byrole.get(role or "", {})
        # `mode` = **`max`**(樹冠の半径と `clr` の大きい方)/ `add`(`clr` に足す)
        addC = 0.0
        if role in crole and crownR:
            addC = (float(crownR) - clr) if cmode == "max" else float(crownR)
            addC = max(0.0, addC)
        for kind, g, mg, nm, bb, kk in shapes:
            if skip and any(x in nm for x in skip):
                continue
            # ⭐ **その欄が効く役が決まっているなら、外の役には掛けない**
            #   (`plantRule.keepoutRolesOnly`。⛔ 例: 野筋は高木・中木だけ)
            if kk in onlyrole and role not in onlyrole[kk]:
                continue
            # ⭐ **樹冠が掛かってよい物には `clr` を足さない**(`plantRule.clrExempt`)。
            #   枝が灯籠・飛石・園路・垣の上へ張り出すのは庭の正しい姿で、避ける物ではない。
            #   ⛔ 軒(棟・渡廊下・附属屋・外周)と石段・井戸には足す — 枝が屋根に入る/道具が使えない
            # ⭐ 層ごとの上書き(`planting[].keepoutByLayer`)> 役ごとの上書き > 既定
            base = mg
            if kk in ov:
                base = _ko_value(d, ov[kk])
            if ovr and kk in ovr:
                base = _ko_value(d, ovr[kk])
            r = base + (0.0 if kk in exempt else clr + addC)
            if u < bb[0] - r or u > bb[2] + r or v < bb[1] - r or v > bb[3] + r:
                continue                                    # 大まかな箱で先に落とす
            if kind == "rect":
                if g[0] - r < u < g[2] + r and g[1] - r < v < g[3] + r:
                    return nm
            elif kind == "pt":
                if math.hypot(u - g[0], v - g[1]) < r:
                    return nm
            elif kind == "seg":
                if _seg_dist((u, v), g[0], g[1]) < r:
                    return nm
            else:
                if _pip_world((u, v), g):
                    return nm
                if min(_seg_dist((u, v), g[i], g[(i + 1) % len(g)]) for i in range(len(g))) < r:
                    return nm
        # 御泉水 — **水面の中には何も植えない**。汀からの離れは役ごと(層が上書きできる)
        if ks:
            po = [tuple(p) for p in ks["outline"]]
            if _pip_world((u, v), po):
                return "御泉水(水面)"
            # ⭐ `pondClr: "crown"` =「**樹冠が水面にかからないこと**」
            if pondClr == "crown":
                sb = float(crownR)
            elif pondClr is not None:
                sb = float(pondClr)
            else:
                sb = float(ks["keepout"].get(role or "", 0.0))
            if sb > 0 and min(_seg_dist((u, v), po[i], po[(i + 1) % len(po)])
                              for i in range(len(po))) < sb:
                return "御泉水の汀"
        w = gr.W(u, v)
        if not _pip_world(w, P):
            return "区画の外"
        if not (skip and any("区画線" in x for x in skip)) and \
                min(_seg_dist(w, P[i], P[(i + 1) % len(P)])
                    for i in range(len(P))) < (par + clr) * gr.ken:
            return "区画線"
        return None
    return hit


def _pip_world(p, poly):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a[1] > y) != (b[1] > y):
            if x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
                c = not c
    return c


# ---------------------------------------------------------------- 庭の散布
_GSC = {}
_GCENT = {}          # (zone, layer) → 塊の重心[間]。`groupGap` の実測に使う


def _in_zone(z, u, v):
    """庭の中か。⚠ **`poly` を持つ庭は矩形ではない**(`u0..v1` はその外接箱)。"""
    if z.get("poly"):
        return _pip_world((u, v), [tuple(p) for p in z["poly"]])
    return z["u0"] - 1e-9 <= u <= z["u1"] + 1e-9 and z["v0"] - 1e-9 <= v <= z["v1"] + 1e-9


def _in_avoid(z, u, v, role):
    """庭の中の**置かない帯**(`gardens[].avoid`)。役で効き方が変わる。"""
    for a in z.get("avoid", []):
        if a.get("roles") and role and role not in a["roles"]:
            continue
        b = a.get("box")
        if b and b[0] <= u <= b[2] and b[1] <= v <= b[3]:
            return a.get("where", "置かない帯")
    return None


def _tk_ray(tk, ang):
    """築山の頂から方位 ang[rad] へ出た半直線が裾の輪郭と交わるまでの距離[間]。"""
    a = (tk["u"], tk["v"])
    dx, dy = math.cos(ang), math.sin(ang)
    S = [tuple(p) for p in tk["skirt"]]
    best = None
    for i in range(len(S)):
        p, q = S[i], S[(i + 1) % len(S)]
        ex, ey = q[0] - p[0], q[1] - p[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((p[0] - a[0]) * ey - (p[1] - a[1]) * ex) / den
        u_ = ((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / den
        if t > 1e-9 and -1e-9 <= u_ <= 1 + 1e-9:
            best = t if best is None else max(best, t)
    return best


def _tk_t(tk, u, v):
    """築山の上での位置。0=頂 / 1=裾。輪郭の外は None。"""
    du, dv = u - tk["u"], v - tk["v"]
    L = math.hypot(du, dv)
    if L < 1e-9:
        return 0.0
    R = _tk_ray(tk, math.atan2(dv, du))
    if R is None or L > R:
        return None
    return L / R


def _tk_y(d, tk, u, v, nat):
    """築山の盛土の面(標高)。頂から裾へ**直線**で降ろす。裾の外・DEM 外は None。

    ⛔ 盛土量・裾の面積を指図に持たせない — この面と造成前 DEM の差から測る。"""
    t = _tk_t(tk, u, v)
    if t is None:
        return None
    R = _tk_ray(tk, math.atan2(v - tk["v"], u - tk["u"]) if (u, v) != (tk["u"], tk["v"]) else 0.0)
    if R is None:
        return None
    ru = tk["u"] + math.cos(math.atan2(v - tk["v"], u - tk["u"])) * R
    rv = tk["v"] + math.sin(math.atan2(v - tk["v"], u - tk["u"])) * R
    yr = nat(ru, rv)
    if yr is None:
        return None
    return tk["y"] + t * (yr - tk["y"])


def _line_pts(d, spec):
    """`along` が指す折れ線(園路 or 遣水・澪筋)を [(u,v)…] で返す。"""
    if "route" in spec:
        for r in d.get("routes", []):
            if r["name"] == spec["route"]:
                return [tuple(p) for p in r["pts"]]
    ln = spec.get("line", "")
    if ln.startswith("sensui."):
        o = d["sensui"][ln.split(".", 1)[1]]
        pts = [tuple(p) for p in o["pts"]]
        for nm in o.get("via", []):
            for t in d["tenkei"]:
                # ⚠ **`pts` に既に入っている点は差し込まない**(2026-09-02 に遣水を6点へ
                #   組み替えて、石橋の点が線形そのものに入った)。二重に入れると線が折れる。
                if t["name"] == nm and not any(abs(q[0] - t["u"]) < 1e-6 and
                                               abs(q[1] - t["v"]) < 1e-6 for q in pts):
                    pts.insert(1, (t["u"], t["v"]))
        return pts
    return None


def _along_band(d, pts, al, blocked, lo, hi, side, pip=lambda q: True):
    """`along` の**帯の合法域**を、線に沿って刻んで返す(検査と散布で同じ規則を使う)。

    ⭐ 折れを名指しする `atVertex`(`vMin`=最も北 / `vMax`=最も南)の解釈も**ここ**に置く。
      ⛔ 検査と散布で別々に書くと、検査が通っても実装で 0本 になる(2026-09-01 検図 高6)。
    → (選んだ区間の index の list, `blocked` を通った点の list)"""
    segs = list(range(len(pts) - 1))
    av = al.get("atVertex")
    if av in ("vMin", "vMax"):
        cand_i = [i for i in range(len(pts)) if pip(pts[i])] or list(range(len(pts)))
        cand_i.sort(key=lambda i: pts[i][1], reverse=(av == "vMax"))

        def _room(vi_):
            sg = [x for x in (vi_ - 1, vi_) if 0 <= x < len(pts) - 1]
            cnt = 0
            for x in sg:
                a2, b2 = pts[x], pts[x + 1]
                dx2, dy2 = b2[0] - a2[0], b2[1] - a2[1]
                L2 = math.hypot(dx2, dy2)
                if L2 < 1e-9:
                    continue
                nx2, ny2 = -dy2 / L2, dx2 / L2
                for t2 in (0.15, 0.4, 0.65, 0.9):
                    bx2, by2 = a2[0] + dx2 * t2, a2[1] + dy2 * t2
                    for sg2 in (1.0, -1.0):
                        for of in (lo, (lo + hi) / 2.0, hi):
                            u2 = bx2 + nx2 * sg2 * of
                            v2 = by2 + ny2 * sg2 * of
                            if side in ("in", "out") and \
                                    (side == "in") != _pip_world((u2, v2), pts[:-1]):
                                continue
                            if not blocked(u2, v2):
                                cnt += 1
            return cnt
        pick_i = next((i for i in cand_i if _room(i) >= 4), cand_i[0])
        segs = [i for i in (pick_i - 1, pick_i) if 0 <= i < len(pts) - 1] or segs
    return segs


def _band_step(area, step, pitch, cap=4000.0):
    """帯・斜面の走査の刻み。⭐ **芯々 `pitch` の 1/4 より細かく刻んでも判定は変わらない**
    (求めているのは「芯々以上離して何点置けるか」だけ)。⛔ 0.10 間で全面を舐めると
    感度試験(53 probe)が現実的な時間で回らなくなる — 面積に応じて刻みを粗くする。"""
    st = max(step, pitch / 4.0)
    if area > 0:
        st = max(st, math.sqrt(area / cap))
    return st


def _along_cells(d, z, pts, al, blocked, lo, hi, step, pitch=0.0):
    """`along` の帯を刻んで走査し、置ける格子点を**走査順に流す**(`group_pack_check` 用)。"""
    side = al.get("side", "both")
    segs = _along_band(d, pts, al, blocked, lo, hi, side,
                       lambda q: _in_zone(z, q[0], q[1]))
    tot = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
              for i in segs) * 2.0 * max(1e-6, hi - lo)
    step = _band_step(tot, step, pitch)
    for i in segs:
        a, b = pts[i], pts[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        nx, ny = -dy / L, dx / L
        nt = max(2, int(L / step) + 1)
        no = max(2, int((hi - lo) / step) + 1)
        for it in range(nt + 1):
            t = it / float(nt)
            bx, by = a[0] + dx * t, a[1] + dy * t
            for io_ in range(no + 1):
                off = lo + (hi - lo) * io_ / float(no)
                for sgn in (1.0, -1.0):
                    u, v = bx + nx * sgn * off, by + ny * sgn * off
                    if side in ("in", "out"):
                        if (side == "in") != _pip_world((u, v), pts[:-1]):
                            continue
                    elif side in ("+v", "-v"):
                        if (side == "+v") != (v > by):
                            continue
                    if blocked(u, v):
                        continue
                    yield (u, v)


def _ref_cells(d, z, rf, blocked, step, pitch=0.0):
    """`ref`(築山の斜面の帯)の合法域を極座標で刻んで**走査順に流す**。"""
    tks = {t["name"]: t for t in d.get("tsukiyama", [])}
    tk = tks.get(rf.get("tsukiyama"))
    if tk is None:
        return
    t0, t1 = rf.get("t", [0.0, 1.0])
    R0 = max([_tk_ray(tk, 6.2832 * k / 16.0) or 0.0 for k in range(16)] or [1.0])
    area = 3.1416 * (R0 * t1) ** 2 - 3.1416 * (R0 * t0) ** 2
    step = _band_step(max(1e-6, area), step, pitch)
    na = max(24, int(6.2832 * R0 * t1 / max(1e-6, step)))
    nt = max(4, int((t1 - t0) * R0 / max(1e-6, step)))
    for ia in range(na):
        ang = 6.2832 * ia / float(na)
        R = _tk_ray(tk, ang)
        if R is None:
            continue
        for it in range(nt + 1):
            t = t0 + (t1 - t0) * it / float(nt)
            u = tk["u"] + math.cos(ang) * R * t
            v = tk["v"] + math.sin(ang) * R * t
            if rf.get("half") == "east" and u < tk["u"]:
                continue
            if rf.get("half") == "west" and u > tk["u"]:
                continue
            if blocked(u, v):
                continue
            yield (u, v)


def scatter_gardens(d):
    """庭の植栽を決定論的に散らす。→ {(zone, layer): [(u, v, part)]}

    ⚠ **位置は設計値ではない。**指図が決めるのは規則・本数・部材・退避・**塊の置き場所**で、
      実装は同じ規則の別の乱数で散らす(図と実装で木の位置は一致しない)。
      検査はここで散らした標本に対して「退避に載った本数」を数える —
      **規則そのものが安全か**を測っている。
    ⭐ 例外は `at`(一本ずつ位置が決まっている木)。**これは設計値**なのでそのまま置く。"""
    if _GSC:
        return _GSC
    hit = free_fn(d)
    K = d["const"]["ken"]
    ko = d["plantRule"]["keepout"]
    zones = {g["name"]: g for g in d["gardens"]}
    tks = {t["name"]: t for t in d.get("tsukiyama", [])}
    placed = {}                                   # zone → [(u,v,spacing間,role)]
    for pl in d.get("planting", []):
        z = zones.get(pl["zone"])
        key = (pl["zone"], pl["layer"])
        _GSC[key] = []
        if z is None:
            continue
        rg = _rng(pl["zone"] + "/" + pl["layer"])
        parts = layer_parts(pl)
        rg.shuffle(parts)
        sp = float(pl.get("spacing", 2.0)) / K     # m → 間
        clr = float(pl.get("clr", 1.0))
        pack = float(d["plantRule"].get("packRatio", 0.7))
        mine = placed.setdefault(pl["zone"], [])
        role = pl.get("role", "")
        skip = pl.get("keepoutSkip")
        pclr = pl.get("pondClr")
        cr = layer_crown_r(d, pl)                  # 層の樹冠の半径[間](⭐ 退避は外周から)
        ovr = pl.get("keepoutByLayer")             # 層だけの退避の上書き(2026-09-02)
        gap = (float(pl["groupGap"][0]) / K) if pl.get("groupGap") else 0.0

        def blocked(u, v, extra=0.0):
            return (hit(u, v, clr + extra, role, skip, pclr, cr, ovr)
                    or (None if _in_zone(z, u, v) else "庭の外")
                    or _in_avoid(z, u, v, role))

        def ok(u, v, f=None):
            f = pack if f is None else f
            if blocked(u, v):
                return False
            for (pu, pv, ps, pr_) in mine:
                # ⚠ 下草は**樹下に置く**もの。木との離れで弾いてはいけない
                if (role == "下草") != (pr_ == "下草"):
                    continue
                if math.hypot(u - pu, v - pv) < (sp + ps) / 2.0 * f:
                    return False
            return True

        def put(u, v, i):
            _GSC[key].append((u, v, parts[i]))
            mine.append((u, v, sp, role))

        # --- 塊の置き場所ごとの候補点(規則は指図の `groups[]` が持つ)
        def sampler(gs, n):
            spread = math.sqrt(max(int(n), 1) / 3.0) * sp
            if gs.get("near"):
                c = gs["near"]
                return lambda: (c[0] + (rg.random() - 0.5) * 2 * spread,
                                c[1] + (rg.random() - 0.5) * 2 * spread)
            if gs.get("box"):
                b = gs["box"]
                return lambda: (b[0] + rg.random() * (b[2] - b[0]),
                                b[1] + rg.random() * (b[3] - b[1]))
            if gs.get("ref"):
                rf = gs["ref"]
                tk = tks[rf["tsukiyama"]]
                t0, t1 = rf.get("t", [0.0, 1.0])

                def pk_tk():
                    for _ in range(200):
                        a = rg.random() * 6.2832
                        R = _tk_ray(tk, a)
                        if R is None:
                            continue
                        t = t0 + rg.random() * (t1 - t0)
                        u = tk["u"] + math.cos(a) * R * t
                        v = tk["v"] + math.sin(a) * R * t
                        if rf.get("half") == "east" and u < tk["u"]:
                            continue
                        if rf.get("half") == "west" and u > tk["u"]:
                            continue
                        return (u, v)
                    return (tk["u"], tk["v"])
                return pk_tk
            if gs.get("along"):
                al = gs["along"]
                pts = _line_pts(d, al)
                if not pts or len(pts) < 2:
                    return lambda: (z["u0"] + rg.random() * (z["u1"] - z["u0"]),
                                    z["v0"] + rg.random() * (z["v1"] - z["v0"]))
                # ⭐ **`offset` があればそれが帯**(2026-09-02 庭方 回答1)。
                #   ⛔ 既定の「園路の退避 + `clr`」は**園路沿いの塊のための値**で、
                #   遣水のような線に当てると帯が線から 2〜3.6間 も離れ、庭の外を指す。
                of = al.get("offset")
                lo = float(of[0]) if of else ko["route"] + clr
                hi = float(of[1]) if of else lo + 2.0 * sp
                side = al.get("side", "both")
                # ⭐ **どの折れか**を名指しする指定(庭方 2026-09-01 回答2-④)。
                #   `vMin` = v がいちばん小さい頂点(= **最も北**)/ `vMax` = 最も南。
                #   ⚠ このグリッドは **v が増える向きが南**。折れの前後の辺だけを引く。
                #   ⭐ 規則は
                #   `_along_band` に一本化した — ⛔ 検査(`group_pack_check`)と散布で
                #   別々に書くと、検査が通っても実装で 0本 になる(2026-09-01 検図 高6)。
                segs = _along_band(d, pts, al, blocked, lo, hi, side,
                                   lambda q: _in_zone(z, q[0], q[1]))

                def pk_al():
                    for _ in range(200):
                        i = segs[rg.randrange(len(segs))]
                        a, b = pts[i], pts[i + 1]
                        t = rg.random()
                        bx, by = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                        dx, dy = b[0] - a[0], b[1] - a[1]
                        L = math.hypot(dx, dy)
                        if L < 1e-9:
                            continue
                        nx, ny = -dy / L, dx / L
                        sgn = 1.0 if rg.random() < 0.5 else -1.0
                        off = lo + rg.random() * (hi - lo)
                        u, v = bx + nx * sgn * off, by + ny * sgn * off
                        if side in ("in", "out"):
                            inside = _pip_world((u, v), pts[:-1])
                            if (side == "in") != inside:
                                continue
                        elif side in ("+v", "-v"):
                            if (side == "+v") != (v > by):
                                continue
                        return (u, v)
                    return (pts[0][0], pts[0][1])
                return pk_al
            return lambda: (z["u0"] + rg.random() * (z["u1"] - z["u0"]),
                            z["v0"] + rg.random() * (z["v1"] - z["v0"]))

        n = len(parts)
        made = 0
        cents = []                                 # 塊の重心(`groupGap` の検査に使う)
        if pl.get("at"):                           # **一本ずつ位置が決まっている木**
            for (u, v) in pl["at"]:
                if made < n:
                    put(u, v, made)
                    made += 1
        elif pl.get("under"):                      # 下草 — 樹下に散らす
            # ⭐ `under` は **数** か **役ごとの数の辞書**【庭方 2026-09-01 回答9】。
            #   ⛔ 「残りは実装が置く」は指図の外へ意匠を逃がす — 下草は樹下だけの物でなく、
            #   刈込の足元(根締め)・石組の際・遣水の岸にも入れるのが作法。
            und = pl["under"]
            if isinstance(und, dict):
                trees = [p for p in mine if p[3] in und]
            else:
                trees = [p for p in mine if p[3] in ("高木", "中木")]
            for (tu, tv, _s, _r) in trees:
                per = int(und[_r]) if isinstance(und, dict) else int(und)
                for _ in range(per):
                    for _t in range(120):
                        u = tu + (rg.random() - 0.5) * 2.4
                        v = tv + (rg.random() - 0.5) * 2.4
                        if ok(u, v, 1.0) and made < n:
                            put(u, v, made)
                            made += 1
                            break
        elif pl.get("groups"):                     # 塊で置く(奇数の塊)
            # ⭐ 塊が `size` を持つときは**その寸法の部材だけ**を引く(庭方 2026-09-01 回答2-④)
            #   — Mid の塊と Small の塊で見え隠れを二度効かせる指定。
            pool = {}
            for gi, gs in enumerate(pl["groups"]):
                if gs.get("size"):
                    pool[gi] = [i for i, pt in enumerate(parts)
                                if ("_" + gs["size"]) in pt["prefab"]]
            used = set()
            for gi, gs in enumerate(pl["groups"]):
                g = int(gs["n"])
                spread = math.sqrt(max(g, 1) / 3.0)
                pick = sampler(gs, g)
                # ⚠ **芯を1つ引いて終わりにしない。**空きの狭い庭では塊の半分が
                #   退避に当たって落ち、本数が揃わない(2026-08-30 実測で 10/14)。
                for _try in range(10):
                    c = None
                    # ⚠ **芯に余裕 1.0 間を求めるのは『まず』だけ。**狭い帯(奥庭は4間)では
                    #   余裕つきの芯が一つも取れず、**塊が丸ごと落ちて 0/n になる**
                    #   (2026-09-01 実測)。株は個別に検めるので、芯は緩めて探し直す。
                    for _t in range(900):
                        cu, cv = pick()
                        if blocked(cu, cv, 1.0 if _t < 450 else 0.0):
                            continue
                        _oth = [q for q in cents
                                if q[2] != json.dumps(gs.get("box")) + "/" + str(gs.get("where"))]
                        if gap and _t < 600 and _oth and \
                           min(math.hypot(cu - q[0], cv - q[1]) for q in _oth) < gap:
                            continue                # **塊の重心の間隔**を空ける
                        c = (cu, cv)
                        break
                    if c is None:
                        break
                    cand = []
                    for _i in range(g):
                        for _t in range(200):
                            a = rg.random() * 6.2832
                            rr = sp * (0.45 + rg.random() * 0.75) * spread
                            u, v = c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr
                            if ok(u, v) and not any(math.hypot(u - q[0], v - q[1]) < sp * pack
                                                    for q in cand):
                                cand.append((u, v))
                                break
                    if len(cand) >= g or _try == 9:
                        for (u, v) in cand:
                            idx = None
                            if gi in pool:
                                free_i = [i for i in pool[gi] if i not in used]
                                if free_i:
                                    idx = free_i[0]
                            if idx is None:
                                free_i = [i for i in range(n) if i not in used]
                                idx = free_i[0] if free_i else None
                            if idx is not None:
                                used.add(idx)
                                put(u, v, idx)
                                made += 1
                        if cand:
                            # ⚠ **同じ場所を指す塊どうしには `groupGap` を効かせない**
                            #   (庭方が『北東の隅に 3+2』のように一箇所へ二群置くことがある)
                            cents.append((sum(q[0] for q in cand) / len(cand),
                                          sum(q[1] for q in cand) / len(cand),
                                          json.dumps(gs.get("box")) + "/" + str(gs.get("where"))))
                        break
        else:
            for _i in range(n):
                for _t in range(4000):
                    u = z["u0"] + rg.random() * (z["u1"] - z["u0"])
                    v = z["v0"] + rg.random() * (z["v1"] - z["v0"])
                    if ok(u, v, 1.0):
                        put(u, v, made)
                        made += 1
                        break
        _GCENT[key] = cents
    return _GSC


# ---------------------------------------------------------------- 西斜面
_SLP = {}


def slope_samples(d, dem, step=1.0):
    """西斜面の適用域を 1m 刻みで走査する。→ [(x, z, u, v, y, t, 帯名)]

    域と t の定義は json の `_slopeArea`。**面積はここで数え、指図には持たせない。**"""
    key = ("s", step)
    if key in _SLP:
        return _SLP[key]
    sa = d["slopeArea"]
    gr = RGrid(d)
    P = d["polygon"]
    CR = [tuple(p) for p in sa["crest"]]
    TOE = sa["toeEdges"]
    bands = d["slopeBands"]

    def crest_near(uv):
        best = (1e18, None, 0)
        for i in range(len(CR) - 1):
            a, b = CR[i], CR[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((uv[0] - a[0]) * dx + (uv[1] - a[1]) * dy) / L2))
            q = (a[0] + dx * t, a[1] + dy * t)
            dd = math.hypot(uv[0] - q[0], uv[1] - q[1])
            if dd < best[0]:
                best = (dd, q, i)
        return best

    def outside(uv):
        dd, q, i = crest_near(uv)
        a, b = CR[i], CR[i + 1]
        du, dv = b[0] - a[0], b[1] - a[1]
        L = math.hypot(du, dv)
        return (du / L) * (uv[1] - a[1]) - (dv / L) * (uv[0] - a[0]) > 0, dd, q

    def toe_near(w):
        best = (1e18, None)
        for i in TOE:
            a, b = P[i], P[(i + 1) % len(P)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((w[0] - a[0]) * dx + (w[1] - a[1]) * dy) / L2))
            q = (a[0] + dx * t, a[1] + dy * t)
            dd = math.hypot(w[0] - q[0], w[1] - q[1])
            if dd < best[0]:
                best = (dd, q)
        return best

    def near_edge(w):
        best = (1e18, -1)
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((w[0] - a[0]) * dx + (w[1] - a[1]) * dy) / L2))
            q = (a[0] + dx * t, a[1] + dy * t)
            dd = math.hypot(w[0] - q[0], w[1] - q[1])
            if dd < best[0]:
                best = (dd, i)
        return best

    out = []
    xs = [q[0] for q in P]
    zs = [q[1] for q in P]
    x = min(xs)
    while x <= max(xs):
        z = min(zs)
        while z <= max(zs):
            w = (x, z)
            uv = gr.L(x, z)
            ok, dc, qc = outside(uv)
            if ok and _pip_world(w, P):
                if near_edge(w)[1] in TOE:
                    yc = _dem_at(dem, *gr.W(qc[0], qc[1]))
                    dt, qt = toe_near(w)
                    yt = _dem_at(dem, qt[0], qt[1])
                    y = _dem_at(dem, x, z)
                    if None not in (yc, yt, y):
                        H = max(yc - yt, 0.5)
                        t = max(0.0, min(1.0, (yc - y) / H))
                        bn = bands[-1]["name"]
                        for b in bands:
                            if b["from"] <= t < b["to"]:
                                bn = b["name"]
                                break
                        out.append((x, z, uv[0], uv[1], y, t, bn, dc * gr.ken, yc, yt))
            z += step
        x += step
    _SLP[key] = out
    return out


def slope_band_area(d, dem, step=1.0):
    """帯ごとの平面積[m²]。走査の標本数 × 刻み²。"""
    a = {}
    for s in slope_samples(d, dem, step):
        a[s[6]] = a.get(s[6], 0.0) + step * step
    return a


def crest_stations(d, dem, step):
    """法肩に沿った検査点。→ [(uv, 外向き法線uv, 進み m)]

    **斜面が続いていて、かつ落差が `screen.minDrop` 以上の区間だけ**を返す。
    ⚠ 北西の登り(辺11)は落差が浅く、その内側は御殿でなく西の明地なので遮蔽の役が無い。
      ここを含めると『置けない所に置け』という検査になる。"""
    sa = d["slopeArea"]
    gr = RGrid(d)
    P = d["polygon"]
    CR = [tuple(p) for p in sa["crest"]]
    TOE = sa["toeEdges"]
    out = []
    run = 0.0
    for i in range(len(CR) - 1):
        a, b = CR[i], CR[i + 1]
        du, dv = b[0] - a[0], b[1] - a[1]
        L = math.hypot(du, dv)
        du, dv = du / L, dv / L
        nu, nv = -dv, du                                    # cross>0 側 = 斜面側
        Lm = L * gr.ken
        k = 0
        while k * step < Lm:
            f = (k * step) / Lm
            uv = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            q = (uv[0] + nu * 2.0 / gr.ken, uv[1] + nv * 2.0 / gr.ken)
            w = gr.W(q[0], q[1])
            if _pip_world(w, P):
                dd = 1e18
                ei = -1
                for j in range(len(P)):
                    x = _seg_dist(w, P[j], P[(j + 1) % len(P)])
                    if x < dd:
                        dd, ei = x, j
                if ei in TOE:
                    yc = _dem_at(dem, *gr.W(uv[0], uv[1]))
                    a2, b2 = P[ei], P[(ei + 1) % len(P)]
                    dx2, dy2 = b2[0] - a2[0], b2[1] - a2[1]
                    L22 = dx2 * dx2 + dy2 * dy2
                    tt = 0.0 if L22 < 1e-12 else max(0.0, min(1.0, ((w[0] - a2[0]) * dx2 + (w[1] - a2[1]) * dy2) / L22))
                    yt = _dem_at(dem, a2[0] + dx2 * tt, a2[1] + dy2 * tt)
                    if yc is not None and yt is not None and (yc - yt) >= float(sa["screen"].get("minDrop", 0.0)):
                        out.append((uv, (nu, nv), run + k * step))
            k += 1
        run += Lm
    return out


_SPL = {}


def scatter_slope(d, dem):
    """西斜面の植栽を決定論的に散らす。→ {層名: [(u, v, part)]}"""
    if _SPL:
        return _SPL
    gr = RGrid(d)
    K = gr.ken
    hit = free_fn(d)
    sa = d["slopeArea"]
    sc = sa["screen"]
    smp = slope_samples(d, dem)
    by_band = {}
    for s in smp:
        by_band.setdefault(s[6], []).append(s)
    mine = []

    def ok(u, v, clr, sp):
        if hit(u, v, clr):
            return False
        for (pu, pv, ps) in mine:
            if math.hypot(u - pu, v - pv) < (sp + ps) / 2.0 * 0.85:
                return False
        return True

    for lay in d.get("slopePlanting", []):
        nm = lay["layer"]
        _SPL[nm] = []
        rg = _rng("slope/" + nm)
        parts = layer_parts(lay)
        rg.shuffle(parts)
        sp = float(lay.get("spacing", 3.0)) / K
        clr = float(lay.get("clr", 1.0))
        made = 0
        if lay.get("placement") == "crestLine":
            st = crest_stations(d, dem, 0.5)
            if not st:
                continue
            w0, Lm = st[0][2], st[-1][2]           # **検査点のある区間だけ**を割り付ける
            pitch, jit = float(sc["pitch"]), float(sc["jitter"])
            o0, o1 = float(sc["offset"][0]), float(sc["offset"][1])
            k = 0
            while made < len(parts) and k < len(parts) * 4:
                want = w0 + (k + 0.5) * pitch + (rg.random() - 0.5) * 2 * jit
                k += 1
                if want < w0 or want > Lm:
                    continue
                base = min(st, key=lambda q: abs(q[2] - want))
                done = False
                for _t in range(24):
                    off = (o0 + rg.random() * (o1 - o0)) / K
                    u = base[0][0] + base[1][0] * off
                    v = base[0][1] + base[1][1] * off
                    if ok(u, v, clr, sp):
                        _SPL[nm].append((u, v, parts[made]))
                        mine.append((u, v, sp))
                        made += 1
                        done = True
                        break
                if not done:
                    continue
        else:
            pool = by_band.get(lay["band"], [])
            if not pool:
                continue
            for _i in range(len(parts)):
                for _t in range(600):
                    s = pool[rg.randrange(len(pool))]
                    u = s[2] + (rg.random() - 0.5) * 1.0 / K
                    v = s[3] + (rg.random() - 0.5) * 1.0 / K
                    if ok(u, v, clr, sp):
                        _SPL[nm].append((u, v, parts[made]))
                        mine.append((u, v, sp))
                        made += 1
                        break
    return _SPL


# ---------------------------------------------------------------- 検査
_EDOASSETS = {}


def edoassets_members():
    """`EdoAssets.cs` の static class ごとの member 名。**api が実在するかの照合用**。

    ⛔ ここに書式(パスの組み立て)は写さない — 写すと EdoAssets と二重管理になる。
      照合するのは「その名の関数/定数があるか」だけ。"""
    if _EDOASSETS:
        return _EDOASSETS
    p = os.path.join(ROOT, "Assets/Edo/Scripts/Editor/EdoAssets.cs")
    if not os.path.exists(p):
        return _EDOASSETS
    src = io.open(p, encoding="utf-8").read()
    cls = [(m.start(), m.group(1)) for m in re.finditer(r"static\s+class\s+(\w+)", src)]
    for i, (pos, name) in enumerate(cls):
        end = cls[i + 1][0] if i + 1 < len(cls) else len(src)
        body = src[pos:end]
        _EDOASSETS[name] = set(re.findall(r"(?:const|static)\s+string\s+(\w+)", body))
    return _EDOASSETS


PACK_OF = {"JG": "Waldemarst/FreeJapaneseGarden", "JC": "Japanese Castle",
           "VK": "Japanese Village Kit", "Eg": "edogoyomi",
           "NM": "NatureManufacture Assets", "Own": "Assets/Edo"}


def _walk_strings(node, skip_id, path=""):
    """json を歩いて (パス, 文字列) を出す。**注記(先頭 `_` のキー)は歩かない。**"""
    if id(node) in skip_id:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.startswith("_"):
                continue
            for r in _walk_strings(v, skip_id, path + "/" + str(k)):
                yield r
    elif isinstance(node, list):
        for i, v in enumerate(node):
            for r in _walk_strings(v, skip_id, "%s[%d]" % (path, i)):
                yield r
    elif isinstance(node, str):
        yield (path, node)


def planting_stock_check(d):
    """**植栽が在庫の実物を名指ししているか。**

    (a) 使用禁止の部材を指図が参照していないか(`plantRule.forbidden`)
    (b) 各層に `parts`(=部材)と `n` があり、`n` = Σ parts.n か
    (c) `prefab` が `docs/asset-index.tsv` に実在するか
    (d) `api` が `EdoAssets.cs` に実在するか、無ければ `assetRequests` に登録依頼があるか
    (e) `api` の引数が `prefab` の名と噛み合っているか(大きさ・番号の取り違え)
    (f) 在庫に無い樹種の層は `pending` と `provisional` を持ち、`plantPending` に材料があるか
    """
    bad = []
    idx = asset_index()
    mem = edoassets_members()
    rule = d.get("plantRule", {})
    forb = rule.get("forbidden", [])
    skip = set([id(forb)])
    for pth, s in _walk_strings(d, skip):
        for f in forb:
            if f and f in s:
                bad.append("(a) 使用禁止の部材が指図に残っている: %s ← %s" % (f, pth))
    reqs = set(r["api"].split("(")[0] for r in d.get("assetRequests", []))
    pend = d.get("plantPending", {})
    for arr in ("planting", "slopePlanting"):
        for lay in d.get(arr, []):
            who = "%s の %s / %s" % (arr, lay.get("zone", lay.get("band", "?")), lay.get("layer", "?"))
            parts = lay.get("parts", [])
            if not parts:
                bad.append("(b) %s に parts が無い — 実装が樹種を選ぶことになる" % who)
                continue
            tot = 0
            for pt in parts:
                for k in ("api", "prefab", "n", "scale"):
                    if k not in pt:
                        bad.append("(b) %s の部材に %s が無い" % (who, k))
                tot += int(pt.get("n", 0))
                nm = pt.get("prefab", "")
                if nm not in idx:
                    bad.append("(c) %s の部材 %s が asset-index.tsv に無い" % (who, nm))
                api = pt.get("api", "")
                kls = api.split(".")[0]
                fn = api.split(".")[-1].split("(")[0]
                if kls not in PACK_OF:
                    bad.append("(d) %s の api %s のクラスが目録に無い" % (who, api))
                elif fn not in mem.get(kls, set()):
                    if ("%s.%s" % (kls, fn)) not in reqs:
                        bad.append("(d) %s の api %s が EdoAssets.cs に無く、assetRequests にも"
                                   "登録依頼が無い — 実装が literal を直書きすることになる" % (who, api))
                if nm in idx and PACK_OF.get(kls) and PACK_OF[kls] not in idx[nm]["path"]:
                    bad.append("(e) %s: api %s(%s)と部材 %s のパックが違う"
                               % (who, api, PACK_OF[kls], nm))
                if "(" not in api:
                    # 定数を名指しした形(`JC.Azalea03` のような)は、名の末尾の数字が
                    # 部材の名にも現れることを求める(01/03/04 の取り違えを捕まえる)
                    m9 = re.search(r"(\d+)$", fn)
                    if m9 and m9.group(1) not in nm:
                        bad.append("(e) %s: api %s の末尾 %s が部材名 %s に現れない"
                                   % (who, api, m9.group(1), nm))
                for a in re.findall(r'"([^"]+)"|(?<![\w"])(\d+)(?![\w"])', api):
                    lit = a[0] or a[1]
                    if not lit:
                        continue
                    ok = lit in nm or (a[1] and ("0" + a[1]) in nm)
                    if not ok:
                        bad.append("(e) %s: api %s の引数 %s が部材名 %s に現れない"
                                   % (who, api, lit, nm))
            if "n" not in lay:
                bad.append("(b) %s に n が無い" % who)
            elif int(lay["n"]) != tot:
                bad.append("(b) %s の n=%d と parts の合計 %d が合わない" % (who, lay["n"], tot))
            if lay.get("pending"):
                if not any(pt.get("provisional") for pt in parts):
                    bad.append("(f) %s は %s 待ちなのに provisional の部材が無い — "
                               "裁定が下りるまで実装が欠品で落ちる" % (who, lay["pending"]))
                if not any(v.get("what", "").startswith(lay["pending"]) for v in pend.values()):
                    bad.append("(f) %s の pending「%s」が plantPending に起票されていない"
                               % (who, lay["pending"]))
    for b in d.get("slopeBands", []):
        for role in ("高木", "中木", "低木", "下草"):
            if role not in b.get("dens", {}):
                bad.append("(b) 帯 %s の dens に %s の範囲が無い" % (b["name"], role))
    return bad


def planting_clearance_check(d, dem, extra=None):
    """**木が棟・廊下・井戸・石段・園路の上に載っていないか。**

    指図の規則どおりに散らした標本を、退避(`plantRule.keepout` + 層の `clr`)で測り直す。
    ⚠ 測っているのは**規則が安全か**であって、実装の木の位置ではない
    (位置は設計値でない)。規則が甘ければここで鳴る。
    あわせて **本数を置ききれるか**(庭が狭い・退避が多すぎる)も見る。"""
    bad = []
    hit = free_fn(d)
    K = d["const"]["ken"]
    zones = {g["name"]: g for g in d["gardens"]}
    gs = scatter_gardens(d)
    for pl in d.get("planting", []):
        key = (pl["zone"], pl["layer"])
        got = list(gs.get(key, []))
        if extra and extra[0] == key:
            got.append(extra[1])
        z = zones.get(pl["zone"])
        role = pl.get("role", "")
        for (u, v, pt) in got:
            nm = hit(u, v, float(pl.get("clr", 1.0)), role,
                     pl.get("keepoutSkip"), pl.get("pondClr"), layer_crown_r(d, pl),
                     pl.get("keepoutByLayer"))
            if nm:
                bad.append("植栽 %s/%s の木が %s に載っている(u%.1f v%.1f)"
                           % (pl["zone"], pl["layer"], nm, u, v))
            if z and not _in_zone(z, u, v):
                bad.append("植栽 %s/%s の木が庭の外(u%.1f v%.1f)" % (pl["zone"], pl["layer"], u, v))
            av = _in_avoid(z, u, v, role) if z else None
            if av:
                bad.append("植栽 %s/%s の木が『%s』(置かない帯)に入っている(u%.1f v%.1f)"
                           % (pl["zone"], pl["layer"], av, u, v))
        if len(gs.get(key, [])) < int(pl["n"]):
            bad.append("植栽 %s/%s が %d/%d しか置けない — 庭が狭いか退避が多すぎる"
                       % (pl["zone"], pl["layer"], len(gs.get(key, [])), pl["n"]))
        # **塊の重心の間隔**(`groupGap`)— ⛔ これが効いていないと均一散布に戻る
        #   ⚠ **`groupGapExempt` を持つ層は下限を免除する**(2026-09-02 庭方 確認5)—
        #     二群が同じ平面に並んでいないときは、平面上の距離で読む指標が意味を持たない。
        #     ⛔ 免除の理由は json に文で残す(空の真偽値にしない)。
        if pl.get("groupGap") and not pl.get("groupGapExempt"):
            lo = float(pl["groupGap"][0]) / K
            cs = _GCENT.get(key, [])
            for a in range(len(cs)):
                for b in range(a + 1, len(cs)):
                    if cs[a][2] == cs[b][2]:
                        continue                   # 同じ場所を指す塊どうしは離さない
                    dd = math.hypot(cs[a][0] - cs[b][0], cs[a][1] - cs[b][1])
                    if dd < lo - 0.05:
                        bad.append("植栽 %s/%s の塊の重心が %.1f 間しか離れていない"
                                   "(`groupGap` の下限 %.1f 間)— 塊が溶けて林に見える"
                                   % (pl["zone"], pl["layer"], dd, lo))
    sp = scatter_slope(d, dem)
    for lay in d.get("slopePlanting", []):
        got = list(sp.get(lay["layer"], []))
        if extra and extra[0] == lay["layer"]:
            got.append(extra[1])
        for (u, v, pt) in got:
            nm = hit(u, v, float(lay.get("clr", 1.0)))
            if nm:
                bad.append("斜面 %s の木が %s に載っている(u%.1f v%.1f)" % (lay["layer"], nm, u, v))
        if len(sp.get(lay["layer"], [])) < int(lay["n"]):
            bad.append("斜面 %s が %d/%d しか置けない" % (lay["layer"], len(sp.get(lay["layer"], [])), lay["n"]))
    return bad


def slope_planting_check(d, dem):
    """**斜面の帯ごとの密度**と、**外から御殿を隠せているか**。

    ・帯ごと役ごとの本/100m² が `slopeBands[].dens` の範囲に入るか
      (面積は造成前 DEM の走査。指図は面積を持たない)
    ・`noPlanting` の帯に木が入っていないか
    ・法肩に沿った検査点から `screen.reach` 以内に樹高 `screen.minH` 以上の木があるか
      — **無ければ対岸から御殿の軒が抜ける**"""
    bad = []
    sa = d["slopeArea"]
    sc = sa["screen"]
    K = d["const"]["ken"]
    area = slope_band_area(d, dem)
    sp = scatter_slope(d, dem)
    smp = {}
    for s in slope_samples(d, dem):
        smp.setdefault(s[6], []).append(s)
    cnt = {}
    for lay in d.get("slopePlanting", []):
        if lay["band"] not in area:
            bad.append("斜面 %s の band「%s」が slopeBands に無い" % (lay["layer"], lay["band"]))
            continue
        cnt.setdefault(lay["band"], {}).setdefault(lay.get("role", "?"), 0)
        cnt[lay["band"]][lay.get("role", "?")] += len(sp.get(lay["layer"], []))
    for b in d["slopeBands"]:
        A = area.get(b["name"], 0.0)
        if A <= 0:
            bad.append("帯 %s の面積が 0 — 帯の区切り(t)が地形と噛み合っていない" % b["name"])
            continue
        for role, (lo, hi) in b["dens"].items():
            n = cnt.get(b["name"], {}).get(role, 0)
            dn = n / A * 100.0
            if dn < lo - 1e-6 or dn > hi + 1e-6:
                bad.append("帯 %s の %s が %.2f 本/100m²(%d本 / %.0f m²)で範囲 %.2f〜%.2f の外"
                           % (b["name"], role, dn, n, A, lo, hi))
        if b.get("noPlanting") and sum(cnt.get(b["name"], {}).values()) > 0:
            bad.append("帯 %s は noPlanting なのに木が %d 本入っている"
                       % (b["name"], sum(cnt.get(b["name"], {}).values())))
    # 遮蔽 — 法肩の検査点。⭐ **求める樹高は区間で変わる**(`screen.minHBySpan`)
    trees = []
    jit0 = d["plantRule"]["scaleJitter"][0]
    for lay in d.get("slopePlanting", []):
        lo = float(lay.get("scaleJitter", [jit0])[0])          # **縮んだときの樹高**で測る
        for (u, v, pt) in sp.get(lay["layer"], []):
            g = part_geom(pt)
            if g:
                trees.append((u, v, g[1] * lo))
    miss = {}
    st = crest_stations(d, dem, float(sc["step"]))
    for (uv, nrm, run) in st:
        h = screen_minh(d, uv[1])
        if not any(math.hypot(uv[0] - u, uv[1] - v) * K <= float(sc["reach"]) and t >= h
                   for (u, v, t) in trees):
            miss[h] = miss.get(h, 0) + 1
    for h, n in sorted(miss.items()):
        bad.append("法肩の遮蔽が %d/%d 点で切れている(樹高 %.1fm 以上の木が %.1fm 以内に無い)"
                   " — 対岸から御殿が抜ける" % (n, len(st), h, sc["reach"]))
    return bad


def screen_minh(d, v):
    """法肩のその点で求める樹高[m]。⭐ **区間で変える**(`slopeArea.screen.minHBySpan`)。

    ⛔ 全長を一律 6.5m の壁にすると、庭に**空を見る場所が一つも無くなる**(庭方 2026-09-01)。
    ⛔ ただし御茶屋の正面と奥向の正面は落とさない — 露地は閉じるのが作法。"""
    sc = d["slopeArea"]["screen"]
    for sp in sc.get("minHBySpan", []):
        if sp["v"][0] <= v <= sp["v"][1]:
            return float(sp["minH"])
    return float(sc["minH"])


# ---------------------------------------------------------------- 庭の検査(2026-09-01)
_TERR = {}


def _terr_json():
    """造成前の地形(回転間格子)。⛔ live terrain から採らない(CLAUDE.md 規則13)。"""
    if not _TERR:
        _TERR.update(json.load(open(os.path.join(DOC, "matsudaira_dewa_terrain.json"),
                                    encoding="utf-8")))
    return _TERR


_DEMJ = {}


def _dem_json():
    """区画まわりの造成前 DEM(世界格子)。⛔ live terrain から採らない(規則13)。"""
    if not _DEMJ:
        _DEMJ.update(json.load(open(os.path.join(DOC, "matsudaira_dewa_dem.json"),
                                    encoding="utf-8")))
    return _DEMJ


def _garden_pts(z, step=0.5):
    u = z["u0"]
    while u <= z["u1"] + 1e-9:
        v = z["v0"]
        while v <= z["v1"] + 1e-9:
            if _in_zone(z, u, v):
                yield (u, v)
            v += step
        u += step


def _all_paths(d):
    """人が歩ける線 — 動線(`routes.kind != niwa`)+ 園路(`kind == niwa`)。"""
    return [(r["label"], [tuple(p) for p in r["pts"]]) for r in d.get("routes", [])]


def garden_access_check(d, lim=20.0, bad_ratio=0.15):
    """**庭に道が通っているか。**⛔ 2026-09-01 に庭方が『1,638坪の観賞の庭のうち
    座敷から見えるのは48坪だけで、そこに道が通っていない』と不合格を出した検査項目。

    庭の面を 0.5間で走査し、**最寄りの動線・園路まで `lim` m を超える点の割合**を測る。
    ⛔ 明地(`cert == "?"`)と白洲・供待は観賞の庭ではないので除く。"""
    K = d["const"]["ken"]
    paths = _all_paths(d)
    bad = []
    for z in d["gardens"]:
        if z.get("cert") == "?" or z.get("kind") == "shirasu" or z["name"] == "G_Tomomachi":
            continue
        if z["name"] in ("G_Baba", "G_HigashiSaien", "G_SakujiAkichi", "G_BabaAkichi",
                         "G_Shintan", "G_Koedame", "G_KatteNiwa", "G_GenkanE",
                         "G_MaeAkichi", "G_Inubashiri"):
            continue
        tot = far = 0
        for (u, v) in _garden_pts(z):
            tot += 1
            dmin = 1e9
            for _nm, pts in paths:
                for i in range(len(pts) - 1):
                    dmin = min(dmin, _seg_dist((u, v), pts[i], pts[i + 1]) * K)
            if dmin > lim:
                far += 1
        if tot and far > tot * bad_ratio:
            bad.append("庭 %s の %.0f%%(%.0f m²)が道から %.0fm を超えて離れている — "
                       "『歩けない庭』(園路 `routes.kind=niwa` を通すこと)"
                       % (z["name"], 100.0 * far / tot, far * (0.5 * K) ** 2, lim))
    return bad


def group_place_check(d):
    """**塊の置き場所が来ているか。**⭐ 2026-09-01 の庭方の直しの本体は
    『塊があって、塊と塊の間が空いている』こと。⛔ 場所の来ていない塊は庭の中を自由に散るので、
    **本数を減らしても林のまま**になる(均一散布への逆戻り)。

    ⛔ `where` を名指ししているのに `box`/`near`/`ref`/`along` が無い塊を鳴らす。
    ⭕ `where` が null の塊(梅林のように『塊間◯間』だけが設計)は欠けではない。"""
    bad = []
    for pl in d.get("planting", []):
        for gs in pl.get("groups", []):
            if gs.get("where") is None:
                continue
            if gs.get("box") or gs.get("near") or gs.get("ref") or gs.get("along"):
                continue
            bad.append("植栽 %s/%s の塊『%s』(%d本)に置き場所の座標が無い — "
                       "庭の中を自由に散る=均一散布のまま(庭方へ差し戻し中 `_pending.kataMitei`)"
                       % (pl["zone"], pl["layer"], gs["where"], int(gs["n"])))
    return bad


def group_pack_check(d, step=0.10, trials=400):
    """⭐ **塊が入るだけの空きが残っているか**【庭方 2026-09-01 の要求】。

    ⛔ これが無いと「座標はあるのに入らない塊」が通る(2026-09-01 に主木2塊・
      モミジ1塊・中木(常緑)2塊で実際に起きた)。
    ⭐ **2026-09-01 改訂(庭方 回答5)— 面積の比較をやめ、「最大充填数 ≥ n」で判定する。**
      ⛔ 面積の式は**2次元の塊**を前提にしていて、**幅が芯々より狭い帯**(生垣の内側・
      汀沿い・壁際)を必ず落とす。**庭の塊の半分は帯である。**
      ⭕ 合法域の格子に対し、**芯々以上離して何点置けるか**を数える
      — **実装の散布器がやることそのもの**なので、検査と実装が食い違わない。
    ⭐ **2026-09-01 第2次検分の直し(庭方)— 充填が最大充填の「下界」しか出していなかった。**
      ⛔ 格子を u→v の走査順に舐める貪欲は**必ず下界**で、刻み 0.20間 では**隅を取り損ねる**
        (主庭『北東の隅』が 2 と出て、実際は 3 本入った)。
      ⭕ 刻みを **0.10間**に、充填を **無作為順 `trials` 回の最良**に直した。
      ⚠ 走査順の貪欲も候補の一つとして必ず試す(下界だが最良になることもある)。
      ⚠ **n 本置けた時点で打ち切る** — 判定は「最大充填 ≥ n」なので、それ以上数える意味が無い
        (通る塊は 1〜2 回で終わるので、刻みを細かくしても実行時間は増えない)。
    ・測るのは **`box`(または `near`)を塊の届く半径だけ広げた域**。
      ⚠ 生成器は box の中から**塊の芯を1つ引き**、そこから半径 `sp×(0.45〜1.2)×√(n/3)` に
      散らす — つまり box は**芯の域**であって木の域ではない。box そのものだけで測ると
      狭い箱がすべて不合格になる。
    ・そこから `avoid`・`keepout`(層の `clr` と樹冠を含む)・園路の退避・庭の外を引く。
    ・芯々は **`spacing` × `plantRule.packRatio`**(塊は疎に撒くときより詰めてよい)。
    ⭐ **2026-09-01(第3次)に `along` と `ref` へ広げた**(検図 高6)。
      ⛔ 従前は `box` と `near` しか測らず、**帯の塊(園路沿い・遣水の岸)と斜面の塊が
        丸ごと対象外**だった。そのため「退避規則の上で1本も置けない塊」が2つ通っていた。
      ⭕ 帯は**線に沿って刻んで数える**(`_along_cells`)、斜面は**極座標で刻む**(`_ref_cells`)
        — どちらも合法域の格子になるので、`box` と同じ最大充填の手が使える。
      ⚠ 折れの選び方(`atVertex`)は散布器と**同じ関数** `_along_band` を通す。"""
    bad = []
    hit = free_fn(d)
    K = d["const"]["ken"]
    ko = d["plantRule"]["keepout"]
    zones = {g["name"]: g for g in d["gardens"]}
    for pl in d.get("planting", []):
        z = zones.get(pl["zone"])
        if z is None:
            continue
        clr = float(pl.get("clr", 1.0))
        role = pl.get("role", "")
        skip, pclr = pl.get("keepoutSkip"), pl.get("pondClr")
        ovr = pl.get("keepoutByLayer")
        cr = layer_crown_r(d, pl)
        sp = float(pl.get("spacing", 2.0)) / K
        for gs in pl.get("groups", []):
            n = int(gs["n"])
            # ⭐ 域は **`box`(または `near` の円)そのもの**【庭方 2026-09-01 回答5】。
            #   ⛔ 散布の届く半径まで広げない — 広げると**池の上に浮いた box**でも
            #   まわりの空きを拾って通ってしまう(2026-09-01 に感度試験が鳴らなくなった)。
            sp_m = float(pl.get("spacing", 2.0))
            pk = float(d["plantRule"].get("packRatio", 0.7))

            def blocked(u, v):
                return bool(hit(u, v, clr, role, skip, pclr, cr, ovr)) or \
                    (not _in_zone(z, u, v)) or bool(_in_avoid(z, u, v, role))

            cell = (step * K) ** 2

            def _cand():
                """候補点を**走査順に流す**(⛔ 全部materializeしない)。
                ⭐ 走査順の貪欲で n 本置けた時点で打ち切れるので、通る塊は数十点で終わる。"""
                if gs.get("box") or gs.get("near"):
                    if gs.get("box"):
                        u0, v0, u1, v1 = gs["box"]
                    else:
                        c = gs["near"]
                        rr = float(gs.get("r", 0.0))
                        u0, v0, u1, v1 = c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr
                    u = u0
                    while u <= u1 + 1e-9:
                        v = v0
                        while v <= v1 + 1e-9:
                            if gs.get("near"):
                                c = gs["near"]
                                if math.hypot(u - c[0], v - c[1]) > float(gs.get("r", 0.0)) + 1e-9:
                                    v += step
                                    continue
                            if not blocked(u, v):
                                yield (u, v)
                            v += step
                        u += step
                elif gs.get("along"):
                    pts = _line_pts(d, gs["along"])
                    if not pts or len(pts) < 2:
                        return
                    of = gs["along"].get("offset")   # ⭐ 帯の明示(2026-09-02)
                    lo = float(of[0]) if of else ko["route"] + clr
                    hi = float(of[1]) if of else lo + 2.0 * sp
                    for q in _along_cells(d, z, pts, gs["along"], blocked, lo, hi, step,
                                          sp_m * pk / K):
                        yield q
                elif gs.get("ref"):
                    for q in _ref_cells(d, z, gs["ref"], blocked, step, sp_m * pk / K):
                        yield q

            if not (gs.get("box") or gs.get("near") or gs.get("along") or gs.get("ref")):
                continue
            pitch0 = sp_m * pk / K                     # 芯々[間]
            put, cells = [], []
            for q in _cand():
                cells.append(q)
                if all((q[0] - r[0]) ** 2 + (q[1] - r[1]) ** 2 >= pitch0 * pitch0 - 1e-9
                       for r in put):
                    put.append(q)
                    if len(put) >= n:
                        break
            if len(put) >= n:
                continue                            # ⭕ 走査順の貪欲だけで入った = 合格
            free = len(cells) * cell
            best = _max_pack(cells, pitch0, n, trials,
                             "%s/%s/%s" % (pl["zone"], pl["layer"], gs.get("where")))
            if best < n:
                bad.append("植栽 %s/%s の塊『%s』(%d本): 退避を引いた合法域に "
                           "**芯々 %.2fm で置けるのは最大 %d 本**(合法域 %.1f m²)— "
                           "**置き場所はあるのに入らない塊**"
                           % (pl["zone"], pl["layer"], gs.get("where") or "(場所未指定)",
                              n, sp_m * pk, best, free))
    return bad


def _max_pack(cells, pitch, need, trials, seed):
    """合法域の格子 `cells` へ**芯々 `pitch` 以上**離して置ける最大本数(の最良の見積り)。

    ⛔ 走査順の貪欲は最大充填の**下界**にすぎない。⭕ 無作為順の貪欲を `trials` 回まわして
      最良を採る。⚠ `need` 本置けたら打ち切る(判定は「最大充填 ≥ n」だけなので)。"""
    if not cells:
        return 0

    def greedy(order):
        put = []
        for (cu, cv) in order:
            ok = True
            for (pu, pv) in put:
                if (cu - pu) ** 2 + (cv - pv) ** 2 < pitch * pitch - 1e-9:
                    ok = False
                    break
            if ok:
                put.append((cu, cv))
                if len(put) >= need:
                    break
        return put

    best = len(greedy(cells))                     # ①走査順(下界。再現性のため必ず試す)
    if best >= need:
        return best
    rg = _rng("pack/" + seed)                     # ②無作為順の最良(決定論的な種)
    arr = list(cells)
    for _ in range(int(trials)):
        rg.shuffle(arr)
        m = len(greedy(arr))
        if m > best:
            best = m
        if best >= need:
            break
    return best


def kaki_crossing_check(d, tol=0.25):
    """**垣が園路と水を塞いでいないか。**門の無い垣は道を塞ぎ、切れ目の無い垣は流れを堰き止める。
    ⛔ 2026-09-01: 外露地の四つ目垣が露地の道と主庭の道を横切っていた(口を空けて解消)。
    ⭐ **2026-09-02(第4次)に「水」を足した**(庭方 中3)— 生垣 `T_Ikegaki_Oku_W` が
      **遣水を横切るのに切れ目が無かった**。道と同じで、垣は水も跨げない。"""
    bad = []
    lines = [("園路 " + r["label"], [tuple(p) for p in r["pts"]]) for r in d.get("routes", [])]
    ym = ((d.get("sensui") or {}).get("yarimizu") or {})
    if ym.get("pts"):
        lines.append(("遣水", [tuple(p) for p in ym["pts"]]))
    for t in d.get("tenkei", []):
        if "a" not in t or "垣" not in t["kind"]:
            continue
        a, b = tuple(t["a"]), tuple(t["b"])
        for lab, pts in lines:
            for i in range(len(pts) - 1):
                p = _x_seg(a, b, pts[i], pts[i + 1])
                if p is not None:
                    bad.append("垣 %s を %s が横切る(u%.2f v%.2f)— 口を空けるか垣を切ること"
                               % (t["name"], lab, p[0], p[1]))
    return bad


def _x_seg(a, b, c, e):
    """線分 ab と ce の交点(無ければ None)。"""
    r = (b[0] - a[0], b[1] - a[1])
    s2 = (e[0] - c[0], e[1] - c[1])
    den = r[0] * s2[1] - r[1] * s2[0]
    if abs(den) < 1e-12:
        return None
    t = ((c[0] - a[0]) * s2[1] - (c[1] - a[1]) * s2[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return (a[0] + r[0] * t, a[1] + r[1] * t)
    return None


EYE = {"座視": 0.95, "立視": 1.55}


def _vp_ground(d, vp, terr):
    """主視点の**下の地盤**(段 → 築山の盛土 → 池の掘削 → 法面)。棟の中なら床は足さない。"""
    ground = _design_at_uv(d, vp["u"], vp["v"], terr)
    for tk in d.get("tsukiyama", []):
        y = _tk_y(d, tk, vp["u"], vp["v"], lambda a, b: _nat_uv(terr, round(a), round(b)))
        if y is not None and (ground is None or y > ground):
            ground = y
    return ground


def fill_viewpoint_eyes(d):
    """⭐ **`eye`(眼高)を持たない主視点の眼高を、下の設計地盤 + 姿勢から埋める。**

    ⛔ **指図に眼高を直書きさせないため**の入口(2026-09-01 第3次・庭方 高5)。
    眼高は「地盤(+棟の中なら床)+ 姿勢」の**従属値**で、床几のように地形の上に直に置く
    視点では、地盤が動けば眼高も動く。⛔ 指図に数値で持たせると、地形を測り直した日に
    黙って古い値が残る。⭕ 生成器がここで埋め、`viewpoint_check` は同じ規則で突き合わせる。
    ⚠ 埋めた視点には `_eyeDerived` を立て、表で「(従属値)」と出す。"""
    terr = _terr_json()
    fl = d["const"]["gotenFloor"]
    for vp in d.get("viewpoints", []):
        if vp.get("eye") is not None:
            continue
        g = _vp_ground(d, vp, terr)
        if g is None:
            continue
        inside = any(m["u0"] <= vp["u"] <= m["u1"] and m["v0"] <= vp["v"] <= m["v1"]
                     for m in d["munes"])
        vp["eye"] = round(g + (fl if inside else 0.0) + EYE.get(vp["posture"], 0.0), 2)
        vp["_eyeDerived"] = True
_EYE_ = ("目の高さ[m]。座視=正座の目(床から)/ 立視=立った目(地面から)。"
         "⛔ 指図に写さない — 生成器が `viewpoints[].eye` と突き合わせる材料")


def viewpoint_check(d, tol=0.35):
    """**主視点が成り立っているか。**⛔ 主景が無い庭は『棟の裏の空地』になる。

    ・`main: true`(主景)がちょうど1つあるか
    ・前景・中景・遠景の三層が埋まっているか(遠景『無し』は露地だけ許す)
    ・眼高が**下の地盤+姿勢**と合うか(座敷は 面 + `const.gotenFloor` + 座視)
    """
    bad = []
    vps = d.get("viewpoints", [])
    if not vps:
        return ["viewpoints(主視点)が無い — 庭の主景が設計値になっていない"]
    terr = _terr_json()
    fl = d["const"]["gotenFloor"]
    if sum(1 for v in vps if v.get("main")) != 1:
        bad.append("主景(`main: true`)が %d 個 — ちょうど1つにする"
                   % sum(1 for v in vps if v.get("main")))
    for vp in vps:
        for k in ("fore", "mid", "far"):
            if not vp.get(k):
                bad.append("主視点 %s に %s(前景/中景/遠景)が無い" % (vp["name"], k))
        if vp["posture"] not in EYE:
            bad.append("主視点 %s の姿勢 %r が知らない値" % (vp["name"], vp["posture"]))
            continue
        # 下の地盤 — 棟の中なら床(面+gotenFloor)、外なら地盤。築山の上なら盛土の面
        ground = _vp_ground(d, vp, terr)
        if ground is None:
            bad.append("主視点 %s の下の地盤が読めない" % vp["name"])
            continue
        inside = any(m["u0"] <= vp["u"] <= m["u1"] and m["v0"] <= vp["v"] <= m["v1"]
                     for m in d["munes"])
        want = ground + (fl if inside else 0.0) + EYE[vp["posture"]]
        if vp.get("eye") is None:
            bad.append("主視点 %s の眼高が読めない(地盤が測れず従属値も埋まっていない)" % vp["name"])
            continue
        if abs(want - float(vp["eye"])) > tol:
            bad.append("主視点 %s の眼高 %.2f が地盤 %.2f%s+%s %.2f と %.2fm 食い違う"
                       % (vp["name"], vp["eye"], ground, ("+床%.2f" % fl) if inside else "",
                          vp["posture"], EYE[vp["posture"]], abs(want - vp["eye"])))
    return bad


def tsukiyama_check(d):
    """**築山**。頂が点景と同じ点か / 裾が庭の中か / **法が輪郭と噛み合うか**。"""
    bad = []
    terr = _terr_json()
    tk_pt = {t["name"]: t for t in d.get("tenkei", [])}
    for tk in d.get("tsukiyama", []):
        top = tk.get("top", {}).get("tenkei")
        if top:
            t = tk_pt.get(top)
            if t is None:
                bad.append("築山 %s の頂の点景 %s が tenkei に無い" % (tk["name"], top))
            elif abs(t["u"] - tk["u"]) > 1e-6 or abs(t["v"] - tk["v"]) > 1e-6:
                bad.append("築山 %s の頂と点景 %s の位置が違う(座標を二重に持っている)"
                           % (tk["name"], top))
        nat = _nat_uv(terr, round(tk["u"]), round(tk["v"]))
        if nat is None:
            bad.append("築山 %s の頂の造成前地盤が読めない" % tk["name"])
            continue
        if tk["y"] - nat <= 0:
            bad.append("築山 %s の頂 %.2f が造成前地盤 %.2f より低い" % (tk["name"], tk["y"], nat))
        for p in tk["skirt"]:
            if not any(_in_zone(z, p[0], p[1]) for z in d["gardens"]):
                bad.append("築山 %s の裾 (u%.1f v%.1f) がどの庭にも入っていない"
                           % (tk["name"], p[0], p[1]))
        # --- ⭐ **輪郭は真円でも階段でもないか**(庭方 2026-09-01 の直しの本体)
        rs = [math.hypot(p[0] - tk["u"], p[1] - tk["v"]) for p in tk["skirt"]]
        if max(rs) - min(rs) < 0.5:
            bad.append("築山 %s の裾が**真円**(半径の振れ %.2f 間)— 盛った山に見えない"
                       % (tk["name"], max(rs) - min(rs)))
        jump = max(abs(rs[i] - rs[(i + 1) % len(rs)]) for i in range(len(rs)))
        if jump > 0.5 * (max(rs) - min(rs)):
            bad.append("築山 %s の裾が**階段状**に切り替わっている(隣の点との半径差 最大 %.2f 間 / "
                       "全振れ %.2f 間)— 東西を連続に振ること"
                       % (tk["name"], jump, max(rs) - min(rs)))
        # --- ⭐ **土の出所が宣言されているか**(`_pending.tsukiyamaDo` の決着 2026-09-01)
        do = tk.get("do")
        if not do:
            bad.append("築山 %s に土の出所(`do`)が無い — **盛土の出どころが指図に無い**"
                       % tk["name"])
        else:
            names = set(t["name"] for t in d["terraces"])
            for k in ("first", "then"):
                sc = do.get(k, {}).get("src")
                if sc and sc not in names and sc != d["sensui"]["pond"]["name"]:
                    bad.append("築山 %s の土の出所 %s(%s)が段にも池にも無い"
                               % (tk["name"], k, sc))
                if sc and sc in do.get("forbidden", []):
                    bad.append("築山 %s が**回してはいけない段 %s** から土を取っている"
                               % (tk["name"], sc))
        # --- ⭐ **法の測る区間が宣言されているか / 東西の差が保たれているか**
        bt = tk.get("batter", {})
        if not bt.get("measure"):
            bad.append("築山 %s の `batter` に測る区間(`measure`)が無い — "
                       "『東1:2.5 / 西1:5』がどこを指すのか検算できない" % tk["name"])
        elif bt.get("east") and bt.get("west") and bt["east"] >= bt["west"]:
            bad.append("築山 %s の法が東 ≥ 西 — この築山は**東が立ち西が流れる**" % tk["name"])
        else:
            nori = [x for (_t, _A, _V, x) in tsukiyama_measure(d, _dem_json())
                    if _t["name"] == tk["name"]]
            if nori:
                ev = [x[1] for x in nori[0] if x[0].startswith("東")]
                wv = [x[1] for x in nori[0] if x[0].startswith("西")]
                for ar in bt["measure"]:
                    if not [x for x in nori[0] if x[0] == ar["where"]]:
                        bad.append("築山 %s の法の区間『%s』に裾の点が1つも無い"
                                   % (tk["name"], ar["where"]))
                if ev and wv and max(ev) >= min(wv):
                    bad.append("築山 %s の法が**東と西で重なっている**(東 1:%.2f〜%.2f / "
                               "西 1:%.2f〜%.2f)— 東が立ち西が流れる形になっていない"
                               % (tk["name"], min(ev), max(ev), min(wv), max(wv)))
    return bad


def tsukiyama_measure(d, dem):
    """築山の**実測** — 裾の面積・盛土量・法の勾配。⛔ 指図に書かない(ここで測る)。"""
    terr = _terr_json()
    gr = RGrid(d)
    K = d["const"]["ken"]
    out = []
    for tk in d.get("tsukiyama", []):
        step = 0.25
        us = [p[0] for p in tk["skirt"]]
        vs = [p[1] for p in tk["skirt"]]
        A = V = 0.0
        u = min(us)
        while u <= max(us):
            v = min(vs)
            while v <= max(vs):
                y = _tk_y(d, tk, u, v, lambda a, b: _nat_uv(terr, round(a), round(b)))
                if y is not None:
                    n = _dem_at(dem, *gr.W(u, v))
                    if n is not None:
                        A += (step * K) ** 2
                        V += max(0.0, y - n) * (step * K) ** 2
                v += step
            u += step
        nori = []
        arcs = tk.get("batter", {}).get("measure") or [
            {"where": "東", "deg": [-90, 90]}, {"where": "西", "deg": [90, 270]}]
        for p in tk["skirt"]:
            L = math.hypot(p[0] - tk["u"], p[1] - tk["v"]) * K
            n = _nat_uv(terr, round(p[0]), round(p[1]))
            h = tk["y"] - (n if n is not None else tk["y"])
            if h <= 0.05:
                continue
            a = math.degrees(math.atan2(p[1] - tk["v"], p[0] - tk["u"]))
            for ar in arcs:                        # 区間は `batter.measure` が持つ
                lo, hi = ar["deg"]
                aa = a
                while aa < lo:
                    aa += 360.0
                if aa <= hi:
                    nori.append((ar["where"], L / h))
                    break
        out.append((tk, A, V, nori))
    return out


def pond_measure(d):
    """御泉水の**実測** — 汀線の内の面積[m²]と掘削の土量[m³]。
    ⛔ 指図に書かない(`sensui.pond.floorY` と `outline` と段の面から出る従属値)。"""
    ks = d.get("sensui")
    if not ks:
        return (0.0, 0.0)
    K = d["const"]["ken"]
    po = [tuple(p) for p in ks["pond"]["outline"]]
    us = [p[0] for p in po]
    vs = [p[1] for p in po]
    step = 0.1
    A = V = 0.0
    u = min(us)
    while u <= max(us):
        v = min(vs)
        while v <= max(vs):
            if _pip_world((u, v), po):
                A += (step * K) ** 2
                V += _pond_depth(d, u, v) * (step * K) ** 2
            v += step
        u += step
    return (A, V)


def _poly_area(pts, K):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0 * K * K


def _poly_perim(pts, K):
    return sum(math.hypot(pts[(i + 1) % len(pts)][0] - pts[i][0],
                          pts[(i + 1) % len(pts)][1] - pts[i][1]) * K
               for i in range(len(pts)))


def mounds_measure(d):
    """**掘った後に隆起させる三つ**(岬2・中島)の土量[m³]。⛔ 指図に書かない。

    近似 = 平面積 ×(天端 − 裾)/ 2(頂から裾へ直線で降ろした錐台の平均)。"""
    ks = d.get("sensui")
    if not ks:
        return []
    K = d["const"]["ken"]
    po = [tuple(p) for p in ks["pond"]["outline"]]
    out = []
    for m in ks.get("mounds", {}).get("items", []):
        if m.get("where", "").startswith("`sensui.island"):
            pts = [tuple(p) for p in ks["island"]["outline"]]
        else:
            # 汀線の三点の三角(marks に載る岬)
            idx = [int(x) for x in re.findall(r"#(\d+)", m.get("where", ""))]
            if len(idx) < 3:
                continue
            pts = [po[i - 1] for i in idx]
        A = _poly_area(pts, K)
        out.append((m["label"], A, A * (float(m["topY"]) - float(m["skirtY"])) / 2.0))
    return out


def sebiyama_measure(d):
    """滝の背山(吐き口の背後4間)の盛土[m³]。⛔ 指図に書かない。"""
    mz = d.get("mizu")
    if not mz or "sebiyama" not in mz:
        return 0.0
    K = d["const"]["ken"]
    y = float(mz["sebiyama"]["y"])
    t = {x["name"]: x for x in d.get("tenkei", [])}.get("T_Iwagumi_Iwaya")
    if t is None:
        return 0.0
    terr = _terr_json()
    A = V = 0.0
    step = 0.25
    for a in range(-16, 17):
        for b in range(-16, 17):
            u = t["u"] + a * step
            v = t["v"] + b * step
            if math.hypot(a * step, b * step) > 4.0:
                continue
            base = _design_at_uv0(d, u, v, terr)
            if base is None:
                continue
            A += (step * K) ** 2
            V += max(0.0, y - base) * (step * K) ** 2
    return V


def tsukiyama_do_table(d, dem, stats):
    """**築山の土の出所**を数で示す。⛔ 数は json に書かない — ここで測る。

    ⭐ **B案(2026-09-01 改)で『池を掘りたる土をもって山を築く』が成立した。**
      A案の `then`(主郭東翼から運ぶ)は消え、`first`(池を掘った土)だけで足りる。
      余りは `do.spread`(主庭・西庭の野筋)へ均す — その厚さもここで測る。"""
    A, Vp = pond_measure(d)
    need = sum(V for (_tk, _A, V, _n) in tsukiyama_measure(d, dem))
    rows = ("<tr><td>① <b>御泉水の掘削</b>(垂直掘り・底 <code>floorY</code> 一定)</td>"
            "<td>%.0f m²</td><td><b>+%.0f m³</b></td>"
            "<td class='note'>出る土</td></tr>" % (A, Vp))
    use = [("築山の盛土", need, "造成前 DEM と盛土の面の差(上の表の計)")]
    for (lb, Am, Vm) in mounds_measure(d):
        use.append(("%s の隆起" % lb, Vm, "掘削の後にハイトマップ直書き(%.0f m²)" % Am))
    sv = sebiyama_measure(d)
    if sv > 0:
        use.append(("滝の背山", sv, "石樋の被りを取るため面 27.0 → 27.25"))
    tot = 0.0
    for (lb, V, note) in use:
        tot += V
        rows += ("<tr><td>② %s</td><td>—</td><td><b>−%.0f m³</b></td>"
                 "<td class='note'>%s</td></tr>" % (lb, V, note))
    rest = Vp - tot
    zs = [z for z in d["gardens"] if z["name"] in ("G_Sensui", "G_NishiNiwa")]
    Ay = 0.0
    for z in zs:
        Ay += _poly_area([tuple(p) for p in (z.get("poly") or
              [[z["u0"], z["v0"]], [z["u1"], z["v0"]], [z["u1"], z["v1"]], [z["u0"], z["v1"]]])],
              d["const"]["ken"])
    Ay -= A
    rows += ("<tr><td><b>差引</b></td><td></td><td><b>%+.0f m³</b></td>"
             "<td class='note'>①−②。%s</td></tr>"
             % (rest,
                ("余りは <code>do.spread</code>(主庭+西庭の野筋 %.0f m²)へ均す = "
                 "<b>厚さ %.2f m</b>(許容 ±0.5m)" % (Ay, rest / max(1.0, Ay)))
                if rest >= 0 else "<b>足りない — 庭方へ差し戻す</b>"))
    return ('<div class="tw"><table><thead><tr><th>勘定</th><th>面積</th><th>土量</th>'
            "<th class='note'>出どころ・行き先</th></tr></thead><tbody>%s</tbody></table></div>" % rows)


def gogan_bands(d):
    """護岸の区間ごとの実寸。→ [{where, L[m], 石数, 天端の標高, 水面上の見え面}]

    ⭐ **B案(2026-09-01 改)で天端は `bands[].topAbove` の設計値**になった
      (= 水面からの高さ)。⛔ 石の丈から導かない・⛔ 独立乱数で振らない。
    ⭐ 芯々は**天端石**の長軸で取る(根石は下段で隠れる)。
    ⚠ `bands[].from/to` は汀線 `pond.outline` の**1始まりの番号**で、環をその向きに辿った区間。"""
    ks = d.get("sensui")
    if not ks:
        return []
    go, po = ks["gogan"], [tuple(p) for p in ks["pond"]["outline"]]
    K, n = d["const"]["ken"], len(po)
    wy = float(ks["pond"]["waterY"])
    out = []
    for bd in go["bands"]:
        i, j, L = int(bd["from"]) - 1, int(bd["to"]) - 1, 0.0
        while i != j:
            i2 = (i + 1) % n
            L += math.hypot(po[i2][0] - po[i][0], po[i2][1] - po[i][1]) * K
            i = i2
        ya = bd.get("yakuishi")
        ev = int(bd.get("yakuEvery") or 0)
        tb = bd["tenbaishi"]
        mn = (tb[0] + tb[1]) / 2.0
        if ya and ev > 1:
            mn = (mn * (ev - 1) + (ya[0] + ya[1]) / 2.0) / ev
        pitch = mn * float(go["gapRatio"])
        rows = [("常石", bd["neishi"], tb, bd["topAbove"])]
        if ya:
            rows.append(("役石", bd["neishi"], ya, bd.get("yakuTopAbove") or bd["topAbove"]))
        out.append({"where": bd["where"], "L": L, "seatY": float(bd["seatY"]),
                    "n": int(round(L / pitch)), "pitch": pitch, "rows": rows,
                    "long": tb, "yaku": ya, "every": ev,
                    "wall": [(wy + t[0] - float(bd["seatY"]), wy + t[1] - float(bd["seatY"]))
                             for (_k, _ne, _tb, t) in rows],
                    "topY": [(wy + t[0], wy + t[1]) for (_k, _ne, _tb, t) in rows],
                    "show": [(t[0], t[1]) for (_k, _ne, _tb, t) in rows]})
    ta = go.get("tateishi")
    if ta:
        out.append({"where": "立石 " + ta["at"], "L": 0.0, "seatY": None, "n": int(ta.get("n", 1)),
                    "pitch": 0.0, "rows": [("立石", None, [ta["h"], ta["h"]], None)],
                    "long": [ta["h"], ta["h"]], "yaku": None, "every": 0,
                    "wall": [(ta["h"], ta["h"])],
                    "topY": [(None, None)], "show": [(None, None)]})
    return out


def gogan_check(d):
    """**護岸石の三条件**【庭方 2026-09-01(改)・設計4】。
      ① 天端が `topCheck`(= 汀の設計地盤 −0.30 〜 +0.25)の帯に入る
      ② 各石の**水面上の見え面 ≥ `showMin`**(0.60m)
      ③ 据え付け位置の規則 `seatRule` が書かれている(⛔ 輪郭点そのものではない)
    ⛔ A案の遺物(`dig` 基準・`topJitter`・run 全体の `long`)が残っていないかも見る。"""
    ks = d.get("sensui")
    if not ks:
        return []
    go = ks["gogan"]
    bad = []
    if "topJitter" in go:
        bad.append("`gogan.topJitter` が残っている — **天端は `bands[].topAbove` の設計値**"
                   "(2026-09-01)")
    for key in ("long", "yakuishi", "yakuEvery"):
        if key in go:
            bad.append("`gogan.%s` が run 全体の値として残っている — 汀は区間で振り分ける"
                       "(`gogan.bands`)" % key)
    if go.get("buryFrom") != "据え付け面(汀の棚)":
        bad.append("`gogan.buryFrom` が『据え付け面(汀の棚)』でない — "
                   "⛔ A案の『枯池の床から』は B案で廃止した(池底は水の下で見えない)")
    if not go.get("seatRule"):
        bad.append("`gogan.seatRule` が無い — **据え付け位置が輪郭点そのものになる**。"
                   "掘削は被覆率で丸まるので、輪郭点の真上が水面より下のことがある")
    wy = float(ks["pond"]["waterY"])
    lo, hi = go["topCheck"]
    smin = float(go.get("showMin") or 0.0)
    # ⭐ **B案では『遠い区間ほど大きく』を要求しない**(汀の立ち上がり 0.95m が見え面を作る)。
    #   ⛔ 逆に**発掘の寸法帯を超えないこと**を見張る【庭方 設計4】。
    LIM = 1.20     # 常石(汐留・市谷・戸山の発掘)
    LIMY = 1.50    # 役石
    for bd in go["bands"]:
        for key, lim in (("neishi", LIM), ("tenbaishi", LIM), ("yakuishi", LIMY)):
            v = bd.get(key)
            if v and float(v[1]) > lim + 1e-9:
                bad.append("護岸『%s』の `%s` の上限 %.2fm が発掘の寸法帯 %.2fm を超える — "
                           "⛔ **水の池では石を大きくする必要が無く、超えてはいけない**"
                           "(庭方 2026-09-01 設計4)" % (bd["where"], key, float(v[1]), lim))
        if float(bd["seatY"]) >= wy:
            bad.append("護岸『%s』の据え付け面 `seatY` %.2fm が水面 %.2fm より上 — "
                       "根石が水から出る" % (bd["where"], float(bd["seatY"]), wy))
        if float(bd["seatY"]) < float(ks["pond"]["floorY"]) - 1e-9:
            bad.append("護岸『%s』の据え付け面 `seatY` %.2fm が池底 %.2fm より下"
                       % (bd["where"], float(bd["seatY"]), float(ks["pond"]["floorY"])))
    for b in gogan_bands(d):
        for (kd, _ne, _tb, ta), tp, sh in zip(b["rows"], b["topY"], b["show"]):
            if tp[0] is None:
                continue
            if sh[0] < smin - 1e-3:
                bad.append("護岸 %s の%s: 水面上の見え面の下限 %.2fm が `showMin` %.2fm に届かない"
                           % (b["where"], kd, sh[0], smin))
            if tp[0] < lo - 1e-3 or tp[1] > hi + 1e-3:
                bad.append("護岸 %s の%s: 天端 %.3f〜%.3fm が `topCheck` の帯 %.2f〜%.2fm を外れる"
                           % (b["where"], kd, tp[0], tp[1], lo, hi))
    return bad


def gogan_table(d):
    ks = d.get("sensui")
    if not ks:
        return ""
    go = ks["gogan"]
    wy = float(ks["pond"]["waterY"])
    bs = gogan_bands(d)
    rows = ""
    tot = 0
    for b in bs:
        for i, ((kd, ne, lg, ta), tp, wl, sh) in enumerate(zip(b["rows"], b["topY"],
                                                               b["wall"], b["show"])):
            cnt = ""
            if i == 0:
                cnt = ("<td rowspan='%d'>%.1f m</td><td rowspan='%d'><b>%d 個</b></td>"
                       % (len(b["rows"]), b["L"], len(b["rows"]), b["n"]))
                tot += b["n"]
            rows += ("<tr><td>%s</td><td>%s</td>%s<td>%s</td><td>%.2f〜%.2f m</td>"
                     "<td>%s</td><td><b>%s</b></td><td>%s</td></tr>"
                     % (b["where"] if i == 0 else "", kd, cnt,
                        ("%.2f〜%.2f m" % (ne[0], ne[1])) if ne else "—",
                        lg[0], lg[1],
                        ("%.2f m" % b["seatY"]) if b["seatY"] is not None else "—",
                        ("%.2f〜%.2f m" % (tp[0], tp[1])) if tp[0] is not None else "—",
                        ("+%.2f〜+%.2f m" % (sh[0], sh[1])) if sh[0] is not None else "—"))
    note = ("<p class='cap'>⭐ <b>天端は設計値</b>(<code>bands[].topAbove</code> = 水面 %.2fm からの高さ)。"
            "⛔ 石の丈から導かない・⛔ <code>topJitter</code> の独立乱数は使わない。<br>"
            "⭐ <b>据え付け面 <code>seatY</code>(汀の棚)から 1/3(<code>bury</code> %.4f)が埋まる</b> — "
            "⛔ A案の『枯池の床から』は廃止。据え付け位置は <code>seatRule</code>「%s」。<br>"
            "石数は <code>L ÷(天端石の平均の長軸 × gapRatio %.2f)</code>の導出値 — "
            "<b>合計 %d 個</b>(立石を含む)。"
            "検査 <code>gogan_check</code> は①天端 ∈ <code>topCheck</code> %.2f〜%.2fm "
            "②水面上の見え面 ≥ <code>showMin</code> %.2fm "
            "③石の長軸が発掘の寸法帯(常石 1.20 / 役石 1.50m)を超えないこと、の三本立て。</p>"
            % (wy, float(go["bury"]), go.get("seatRule", ""), float(go["gapRatio"]), tot,
               go["topCheck"][0], go["topCheck"][1], float(go.get("showMin") or 0)))
    return ('<div class="tw"><table><thead><tr><th>区間</th><th>石</th><th>延長</th>'
            "<th>石数</th><th>根石の長軸</th><th>天端石の長軸</th><th>据え付け面</th>"
            "<th>天端(標高)</th><th>水面上の見え面</th></tr></thead><tbody>%s</tbody></table></div>%s"
            % (rows, note))


def sensui_metrics_table(d):
    """**美観の代理指標**(⛔ 指図に書かない従属値)。円形度 = 4πA/L²。"""
    ks = d.get("sensui")
    if not ks:
        return ""
    K = d["const"]["ken"]
    po = [tuple(p) for p in ks["pond"]["outline"]]
    A = _poly_area(po, K)
    L = _poly_perim(po, K)
    circ = 4 * math.pi * A / (L * L)
    isl = [tuple(p) for p in ks["island"]["outline"]]
    Ai = _poly_area(isl, K)
    Li = _poly_perim(isl, K)
    ci = 4 * math.pi * Ai / (Li * Li)
    segs = [math.hypot(po[(i + 1) % len(po)][0] - po[i][0],
                       po[(i + 1) % len(po)][1] - po[i][1]) * K for i in range(len(po))]
    mu = sum(segs) / len(segs)
    sd = (sum((x - mu) ** 2 for x in segs) / len(segs)) ** 0.5
    def zarea(nm):
        z = [x for x in d["gardens"] if x["name"] == nm][0]
        pts = [tuple(p) for p in (z.get("poly") or
               [[z["u0"], z["v0"]], [z["u1"], z["v0"]], [z["u1"], z["v1"]], [z["u0"], z["v1"]]])]
        return _poly_area(pts, K)
    As = zarea("G_Sensui")
    An = zarea("G_NishiNiwa")
    # 汀から庭境の最小
    zz = [x for x in d["gardens"] if x["name"] == "G_Sensui"][0]
    zp = [tuple(p) for p in zz["poly"]]
    dmin = min(min(_seg_dist(p, zp[i], zp[(i + 1) % len(zp)]) for i in range(len(zp)))
               for p in po)
    r = ("<tr><td>水面(設計汀線の内)</td><td><b>%.0f m²</b></td><td class='note'>掘削後の実測は"
         "被覆率の丸めで少し縮む(庭方の模擬掘削 228 m²)</td></tr>"
         "<tr><td>水面 / 主庭 %.0f m²</td><td><b>%.0f%%</b></td><td class='note'></td></tr>"
         "<tr><td>水面 /(主庭+西庭 %.0f m²)</td><td><b>%.0f%%</b></td><td class='note'></td></tr>"
         "<tr><td>汀線の頂点間隔</td><td><b>平均 %.2f m</b></td>"
         "<td class='note'>%.2f〜%.2f m・変動係数 <b>%.2f</b>(⛔ 等間隔にしない)</td></tr>"
         "<tr><td>池の円形度 4πA/L²</td><td><b>%.2f</b></td>"
         "<td class='note'>1.0 = 真円</td></tr>"
         "<tr><td>中島の円形度</td><td><b>%.2f</b></td>"
         "<td class='note'>面積 %.1f m²。⚠ A案の7点は 0.85 で『碁石』だった</td></tr>"
         "<tr><td>汀から庭境の最小</td><td><b>%.2f 間(%.2f m)</b></td>"
         "<td class='note'>⚠ 目安 1.5間 をわずかに割る(西境 u−46 と汀線 #19)</td></tr>"
         % (A, As, A / As * 100.0, As + An, A / (As + An) * 100.0,
            mu, min(segs), max(segs), sd / mu, circ, ci, Ai, dmin, dmin * K))
    return ('<div class="tw"><table><thead><tr><th>指標</th><th>実測</th>'
            "<th class='note'>読み</th></tr></thead><tbody>%s</tbody></table></div>"
            "<p class='cap'>⛔ <b>これらは全部従属値</b>(CLAUDE.md 規則4)— json にも kosho.md にも"
            "写さない。⭐ 真行草は <b>行</b>。</p>" % r)


def _taki_feet(d):
    """台地端の滝の**各段の下端**と、その下端が載る**滝壺の位置**を返す。

    ⭐ 段 k の滝壺は**次の段の位置**そのもの(次の段の天端がそこに座る)。
      最下段だけは下流に段が無いので、**段の刻みの平均ベクトルを一つ延ばした点**を採る。
    → [(段, 下端[m], (u,v))]"""
    ts = ((d.get("mizu") or {}).get("takiDaichi") or {}).get("tiers") or []
    out = []
    if len(ts) >= 2:
        du = sum(ts[i + 1]["u"] - ts[i]["u"] for i in range(len(ts) - 1)) / (len(ts) - 1)
        dv = sum(ts[i + 1]["v"] - ts[i]["v"] for i in range(len(ts) - 1)) / (len(ts) - 1)
    else:
        du = dv = 0.0
    for k, t in enumerate(ts):
        bot = float(t["topY"]) - float(t["fall"])
        if k + 1 < len(ts):
            pt = (float(ts[k + 1]["u"]), float(ts[k + 1]["v"]))
        else:
            pt = (float(t["u"]) + du, float(t["v"]) + dv)
        out.append((t, bot, pt))
    return out


def taki_check(d, tol=0.30):
    """**台地端の滝(三段)**。⭐ **各段の下端が「設計地盤」に載っているか**(|Δ| ≤ 0.30m)。

    ⚠ **2026-09-01(第3次)に当て先を替えた**(庭方 中7・検図 中2)— 従前は
      **造成前DEM** と、しかも**最下段だけ**を比べていた。三段は段 `Shukaku` の南縁から出る
      1:1.5 の**設計盛土法面の中に組む**ので、造成前DEM との比較には意味が無い
      (指図の注記「盛土も切土もほとんど要らない」もそれで誤っていた)。
    ⭕ 当て先は**設計地盤**、対象は**全段**。造成前DEM との差は参考値として表に残す。"""
    mz = d.get("mizu")
    if not mz or "takiDaichi" not in mz:
        return []
    terr, dm = _terr_json(), _dem_json()
    bad = []
    tiers = mz["takiDaichi"]["tiers"]
    for k, t in enumerate(tiers):
        bot = float(t["topY"]) - float(t["fall"])
        if k + 1 < len(tiers) and abs(float(tiers[k + 1]["topY"]) - bot) > 1e-6:
            bad.append("台地端の滝 %s の下端 %.2fm と次の段の天端 %.2fm が続いていない"
                       % (t["label"], bot, float(tiers[k + 1]["topY"])))
    for (t, bot, pt) in _taki_feet(d):
        y = _ground_uv(d, pt[0], pt[1], terr, dm)
        if y is None:
            bad.append("台地端の滝 %s の滝壺 (u%.1f v%.1f) の設計地盤が読めない"
                       % (t["label"], pt[0], pt[1]))
            continue
        if abs(y - bot) > tol:
            bad.append("台地端の滝 %s の下端 %.2fm が滝壺の設計地盤 %.2fm から %.2fm 離れている"
                       "(帯 ±%.2fm)— 段の位置か落差を庭方へ差し戻す"
                       % (t["label"], bot, y, abs(y - bot), tol))
    # 頭の水位が遣水の落ち口と続いているか
    if d.get("sensui"):
        nod = {n["id"]: n for n in mz["nodes"]}
        if "MZ12" in nod and abs(float(nod["MZ12"]["waterY"]) - float(tiers[0]["topY"])) > 1e-6:
            bad.append("遣水の落ち口 %.2fm と台地端の滝の一の段の天端 %.2fm が続いていない"
                       % (float(nod["MZ12"]["waterY"]), float(tiers[0]["topY"])))
    return bad


def _toi_pts(d, t):
    """樋の平面の線。⭐ **`pts`(折れ線)/ `a`+`b`(2点)/ 節点 `from`→`to` の順に採る。**

    ⚠ **2026-09-02(第4次)に折れ線を許した**【庭方 高1】— 暗渠 `MZ_Ankyo` は
      奥御殿の真下を直線で潜っていたので、棟の外を回る折れ線へ替えた。
      ⛔ 2点しか読まない書き方に戻すと、**折れが黙って無視されて長さも土被りも狂う**。"""
    if t.get("pts"):
        return [tuple(q) for q in t["pts"]]
    nod = {n["id"]: n for n in d["mizu"]["nodes"]}
    if t.get("a") and t.get("b"):
        return [tuple(t["a"]), tuple(t["b"])]
    out = []
    for i in (t.get("from"), t.get("to")):
        n = nod.get(i)
        if n is None or n.get("u") is None:
            return None
        out.append((n["u"], n["v"]))
    return out


def _toi_ends(d, t):
    """樋の**上端・下端の水位**(または床)と、平面長[m]。→ (上, 下, 長さ, どちらで測ったか)"""
    K = d["const"]["ken"]
    nod = {n["id"]: n for n in d["mizu"]["nodes"]}

    def uv(i):
        n = nod.get(i)
        if n is None:
            return None
        if n.get("u") is not None:
            return (n["u"], n["v"])
        return None
    pts = _toi_pts(d, t)
    if pts and len(pts) >= 2:
        L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                for i in range(len(pts) - 1)) * K
    else:
        L = None
    for key, lab in (("waterY", "水面"), ("floorY", "床")):
        v = t.get(key)
        if isinstance(v, list) and len(v) == 2:
            return (float(v[0]), float(v[1]), L, lab)
    return (None, None, L, None)


def _toi_cover(d, t, step=0.5):
    """樋の**土被り**[m]を線に沿って測る。→ [((u,v), 被り)]

    ⛔ 指図に宣言させない(2026-09-02 検図 中6: 経路を変えた後も旧経路の値が残っていた)。
    被り = **設計地盤 − 樋の天端**(天端 = 床 + 内法 `h`)。床は上下端の `floorY` を線形で割る。
    ⚠ 上流端の `coverSkipHead`[m] は測らない — そこは越流堰の口で、地盤から出ているのが正。"""
    pts = _toi_pts(d, t)
    fy = t.get("floorY")
    if not pts or len(pts) < 2 or not isinstance(fy, list):
        return []
    K = d["const"]["ken"]
    terr, dm = _terr_json(), _dem_json()
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) * K
           for i in range(len(pts) - 1)]
    tot = sum(seg) or 1.0
    skip = float(t.get("coverSkipHead") or 0.0)
    h = float(t.get("h") or 0.0)
    out, acc = [], 0.0
    for i in range(len(pts) - 1):
        n = max(1, int(seg[i] / step))
        for k in range(n + 1):
            r = k / float(n)
            s_ = acc + seg[i] * r
            if s_ < skip - 1e-9:
                continue
            u = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * r
            v = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * r
            y = _ground_uv(d, u, v, terr, dm)
            if y is None:
                continue
            out.append(((u, v), y - (float(fy[0]) + (float(fy[1]) - float(fy[0])) * s_ / tot + h)))
        acc += seg[i]
    return out


def mizu_check(d):
    """**水の系**。上流から下流へ水位が単調に下がるか / 節点が指図の物と噛み合うか。

    ⭐ **2026-09-01(第3次)に対象を広げた**(検図 高2・高3)— 従前は **MZ1〜MZ7 の本流しか
      単調性を見ておらず**、枝(MZ_Eda1 / MZ_Eda2)と暗渠(MZ_Ankyo)、および遣水から滝への
      流れ(MZ10〜MZ15)が**丸ごと対象外**だった。そのため
      ①枝の落差ゼロ(枝2は 60m を無勾配)②余水が上流へ昇る、が二つとも素通りした。
    ⭕ いまは **①本流 MZ1〜MZ7 ②枝の流れ MZ10〜MZ15 ③`toi` 全本**の三本立てで見る。"""
    mz = d.get("mizu")
    if not mz:
        return ["`mizu`(水の系)が無い — **池に水を入れる筋と余水の行き先が指図に無い**"]
    ks = d["sensui"]
    bad = []
    nod = {n["id"]: n for n in mz["nodes"]}

    def wy(n):
        w = n.get("waterY")
        if w is None:
            w = n.get("weirY")
        if w is None:
            w = n.get("y")                       # 末端(溜池の汀)は `y` で持つ
        if isinstance(w, list):
            return w
        return [w, w] if w is not None else None

    for seq, lab in ((["MZ1", "MZ2", "MZ3", "MZ4", "MZ5", "MZ6", "MZ7"], "本流(取入口→池→水尻)"),
                     (["MZ3", "MZ10", "MZ11", "MZ12", "MZ13", "MZ14", "MZ15"],
                      "枝2の流れ(落し枡C→遣水→台地端の滝→溜池)")):
        prev, prevn = None, None
        for i in seq:
            n = nod.get(i)
            if n is None:
                bad.append("水の系の節点 %s が無い" % i)
                continue
            w = wy(n)
            if w is None:
                continue
            if prev is not None and w[0] > prev + 1e-9:
                bad.append("水の系 %s: %s(%s)の水面 %.2fm が一つ上流の %s %.2fm より高い — 水が逆流する"
                           % (lab, i, n["label"], w[0], prevn, prev))
            prev, prevn = w[-1], n["label"]

    # ---- 樋(木樋・石樋・暗渠)は**全本**を見る。⛔ 落差ゼロは「流れない」= 不合格
    for t in mz.get("toi", []):
        hi, lo, L, kind = _toi_ends(d, t)
        if hi is None:
            continue
        if lo > hi + 1e-9:
            bad.append("樋 %s の%sが下流で %.2fm 高い(%.2f → %.2f)— 水が逆流する"
                       % (t["name"], kind, lo - hi, hi, lo))
        elif abs(hi - lo) < 1e-9:
            bad.append("樋 %s の%sが上下端とも %.2fm で**落差ゼロ**(平面長 %.1fm)— 水が流れない"
                       % (t["name"], kind, hi, L or 0.0))
        elif L and L > 0.5:
            g = L / (hi - lo)
            if g > 2000.0:
                bad.append("樋 %s の勾配が 1/%.0f(平面長 %.1fm・落差 %.3fm)— 流れない"
                           % (t["name"], g, L, hi - lo))
            dec = t.get("grade")
            if dec:
                m = re.match(r"1/(\d+(?:\.\d+)?)$", str(dec).strip())
                if m and abs(float(m.group(1)) - g) > 0.10 * g:
                    bad.append("樋 %s の宣言 `grade` %s が実測 1/%.0f と食い違う"
                               "(平面長 %.1fm・落差 %.3fm)— 定義か値のどちらかが古い"
                               % (t["name"], dec, g, L, hi - lo))
        # 上下端が、つなぐ節点の値と噛み合っているか
        for end, nid in ((hi, t.get("from")), (lo, t.get("to"))):
            n = nod.get(nid)
            if n is None or kind != "水面":
                continue
            w = wy(n)
            if w is None:
                continue
            if min(abs(end - w[0]), abs(end - w[-1])) > 1e-6:
                bad.append("樋 %s の端 %.2fm が節点 %s(%s)の水面 %s と噛み合わない"
                           % (t["name"], end, nid, n["label"], w))
    # ---- 暗渠は**吐き先より高い所で吐く**か(床どうし)
    ak = next((t for t in mz.get("toi", []) if t["name"] == "MZ_Ankyo"), None)
    if ak and mz.get("takiDaichi"):
        feet = _taki_feet(d)
        if feet:
            pool = feet[0][1]                      # 一の段の滝壺
            if float(ak["floorY"][1]) < pool - 1e-9:
                bad.append("暗渠 %s の末の床 %.2fm が一の段の滝壺 %.2fm より低い — 吐けない"
                           % (ak["name"], float(ak["floorY"][1]), pool))
    # 池の水面と節点の一致
    if nod.get("MZ6") and abs(float(nod["MZ6"]["waterY"]) - float(ks["pond"]["waterY"])) > 1e-9:
        bad.append("`mizu` の御泉水の水面と `sensui.pond.waterY` が食い違う")
    if nod.get("MZ7") and abs(float(nod["MZ7"]["weirY"]) - float(ks["pond"]["waterY"])) > 1e-9:
        bad.append("水尻の堰の天端が `sensui.pond.waterY` と一致しない — 越流堰にならない")
    if nod.get("MZ4") and abs(float(nod["MZ4"]["waterY"]) - float(ks["iwaya"]["inletY"])) > 1e-9:
        bad.append("`mizu` の吐き口の水面と `sensui.iwaya.inletY` が食い違う")
    dr = ks["iwaya"]["drops"]
    if abs(float(ks["iwaya"]["inletY"]) - sum(dr) - float(ks["pond"]["waterY"])) > 1e-6:
        bad.append("落ち口 %s の合計が 吐き口 %.2f − 水面 %.2f = %.2fm と合わない"
                   % (dr, float(ks["iwaya"]["inletY"]), float(ks["pond"]["waterY"]),
                      float(ks["iwaya"]["inletY"]) - float(ks["pond"]["waterY"])))
    # ---- 遣水は**湧き口と落ち口の節点**と噛み合うか(枝2の末 → 滝の頭)
    ym = ks.get("yarimizu")
    if ym and isinstance(ym.get("waterY"), list):
        for end, nid in ((ym["waterY"][0], "MZ10"), (ym["waterY"][-1], "MZ12")):
            n = nod.get(nid)
            if n is not None and abs(float(end) - float(n["waterY"])) > 1e-6:
                bad.append("遣水の端 %.2fm が節点 %s(%s)の水面 %.2fm と噛み合わない"
                           % (end, nid, n["label"], float(n["waterY"])))
        if isinstance(ym.get("floorY"), list):
            for k2, (w2, f2) in enumerate(zip(ym["waterY"], ym["floorY"])):
                if float(w2) - float(f2) < 0.05:
                    bad.append("遣水の%s端: 水面 %.2fm と床 %.2fm の差が浅すぎる"
                               % ("上" if k2 == 0 else "下", float(w2), float(f2)))
    # 汀線上の節点が汀線に載っているか
    po = [tuple(p) for p in ks["pond"]["outline"]]
    for i in ("MZ4", "MZ7"):
        n = nod.get(i)
        if n is None or "shore" not in n:
            continue
        p = po[int(n["shore"]) - 1]
        if abs(p[0] - n["u"]) > 1e-6 or abs(p[1] - n["v"]) > 1e-6:
            bad.append("%s(%s)の座標が汀線 #%s と一致しない" % (i, n["label"], n["shore"]))
    # 暗渠が中仕切塀を潜るか(⚠ **折れ線の全区間**を見る。2026-09-02 に折れ線へ替えた)
    if ak:
        aks = _toi_pts(d, ak) or []
        nj = [x for x in d["nakajikiri"] if x["name"] == "NJ_Oku_N_W"]
        if nj and len(aks) >= 2:
            c, e = tuple(nj[0]["a"]), tuple(nj[0]["b"])
            if not any(_seg_x(aks[i], aks[i + 1], c, e) for i in range(len(aks) - 1)):
                bad.append("暗渠 MZ_Ankyo が中仕切塀 NJ_Oku_N_W と交わらない — "
                           "『塀の下を潜る』が幾何と合わない")
        # ⭐ **棟の下を潜っていないか**【庭方 2026-09-02 高1】— 礎石・布基礎と同じ深さ帯を
        #   排水が横切ると、詰まっても掃除の手が入らない。⛔ 直線に戻すとここで鳴る。
        for i in range(len(aks) - 1):
            for m in d["munes"] + d["service"]:
                q = [(m["u0"], m["v0"]), (m["u1"], m["v0"]), (m["u1"], m["v1"]), (m["u0"], m["v1"])]
                inside = _pip_world(aks[i], q) or _pip_world(aks[i + 1], q)
                cross = any(_seg_x(aks[i], aks[i + 1], q[k], q[(k + 1) % 4]) for k in range(4))
                if inside or cross:
                    bad.append("暗渠 %s が %s の下を潜っている — **礎石・布基礎と同じ深さ帯**で、"
                               "詰まっても掃除の手が入らない(庭方 2026-09-02 高1)"
                               % (ak["name"], m.get("name", m.get("label"))))
                    break
    # ---- 樋の**土被り**は宣言せず**測る**【検図 2026-09-02 中6】
    #      ⛔ 旧版は `cover` を宣言値で持ち、経路を変えた後も旧経路の値のまま残っていた。
    #      ⚠ 上流端は水尻の越流堰そのものなので `coverSkipHead`[m] のぶん測らない。
    for t in mz.get("toi", []):
        if t.get("floorY") is None or "coverBand" not in t:
            continue
        cov = _toi_cover(d, t)
        if not cov:
            bad.append("樋 %s の土被りが測れない(設計地盤が読めない)" % t["name"])
            continue
        lo2 = min(c[1] for c in cov)
        if lo2 <= 0.0:
            bad.append("樋 %s の土被りが %.2fm(≤0)— **石樋が地表へ出る**(u%.1f v%.1f)"
                       % (t["name"], lo2, *[c[0] for c in cov if c[1] == lo2][0]))
        band = t.get("coverBand")
        if band:
            hi2 = max(c[1] for c in cov)
            if lo2 < float(band[0]) - 1e-9 or hi2 > float(band[1]) + 1e-9:
                bad.append("樋 %s の土被り実測 %.2f〜%.2fm が `coverBand` %s を外れる"
                           % (t["name"], lo2, hi2, band))
    # ---- 遣水が結界を横切る所の始末【庭方 2026-09-02 中3】
    ym2 = ks.get("yarimizu")
    kg = (ym2 or {}).get("kuguri")
    if ym2 and not kg:
        bad.append("遣水が中仕切塀を横切るのに `sensui.yarimizu.kuguri`(塀の下の水抜き)が無い")
    if ym2 and kg:
        nj2 = [x for x in d["nakajikiri"] if x["name"] == kg.get("nakajikiri")]
        yp = [tuple(q) for q in ym2["pts"]] + [(float(nod["MZ13"]["u"]) if nod.get("MZ13", {}).get("u")
                                                else mz["takiDaichi"]["tiers"][0]["u"],
                                                mz["takiDaichi"]["tiers"][0]["v"])]             if mz.get("takiDaichi") else [tuple(q) for q in ym2["pts"]]
        xp = None
        if nj2:
            c, e = tuple(nj2[0]["a"]), tuple(nj2[0]["b"])
            for i in range(len(yp) - 1):
                if xp is None:
                    xp = _x_seg(yp[i], yp[i + 1], c, e)   # ⭐ 交点そのもの(⛔ 真偽ではない)
        if nj2 and xp is None:
            bad.append("遣水が `%s` と交わらない — `kuguri`(塀の下の水抜き)の宣言が幾何と合わない"
                       % kg.get("nakajikiri"))
        # ⛔ 木戸と水抜きが同じ口を取り合っていないか(木戸を開けると足元が流れになる)
        kdn2 = (mz.get("takiDaichi") or {}).get("kido")
        kd2 = [x for x in d["nakajikiri"] if x["name"] == kdn2] if kdn2 else []
        if xp and kd2:
            a2, b2 = tuple(kd2[0]["a"]), tuple(kd2[0]["b"])
            if min(a2[0], b2[0]) - 1e-9 <= xp[0] <= max(a2[0], b2[0]) + 1e-9:
                bad.append("滝見口 %s の開口の中を遣水が横切っている — "
                           "**木戸を開けると足元が流れ**になる(庭方 2026-09-02 中3)" % kdn2)
    # 滝見口が中仕切塀の span の中にあるか
    kdn = (mz.get("takiDaichi") or {}).get("kido")
    kd = [x for x in d["nakajikiri"] if x["name"] == kdn] if kdn else []
    sw = [x for x in d["nakajikiri"] if x["name"] == "NJ_Oku_S_W"]
    if kdn and not kd:
        bad.append("滝見口 %s が `nakajikiri` に無い — **台地端の滝は結界の外**なので、"
                   "口が無いと奥庭からは 2.4m の板塀に隠れて見えない" % kdn)
    if kd and sw:
        if not (min(sw[0]["a"][0], sw[0]["b"][0]) <= kd[0]["a"][0]
                and kd[0]["b"][0] <= max(sw[0]["a"][0], sw[0]["b"][0])):
            bad.append("滝見口 NJ_Taki_Kido が NJ_Oku_S_W の span の外にある")
    return bad


def sensui_check(d):
    """**御泉水**。汀線が主庭の中か / 島と岩屋が汀線と噛み合うか / 水を張っているか /
    掘削の作法(`baker`)が図の消えない設定か。"""
    ks = d.get("sensui")
    if not ks:
        return []
    bad = []
    po = [tuple(p) for p in ks["pond"]["outline"]]
    if len(po) < 8:
        bad.append("御泉水の汀線が %d 点しか無い — 池の形にならない" % len(po))
    zs = [z for z in d["gardens"] if z["name"] == "G_Sensui"]
    for p in po:
        if not zs or not _in_zone(zs[0], p[0], p[1]):
            bad.append("御泉水の汀 (u%.1f v%.1f) が主庭 G_Sensui の外" % (p[0], p[1]))
    for p in ks["island"]["outline"]:
        if not _pip_world((p[0], p[1]), po):
            bad.append("中島の点 (u%.1f v%.1f) が池の外" % (p[0], p[1]))
    tk_pt = {t["name"]: t for t in d.get("tenkei", [])}
    for nm in (ks["iwaya"]["tenkei"],):
        t = tk_pt.get(nm)
        if t is None:
            bad.append("御泉水の %s が tenkei に無い" % nm)
            continue
        dd = min(_seg_dist((t["u"], t["v"]), po[i], po[(i + 1) % len(po)])
                 for i in range(len(po)))
        if dd > 1.0:
            bad.append("%s が汀線から %.2f 間 離れている(汀の上に据える)" % (nm, dd))
    # ---- 水位・深さ・底
    pd = ks["pond"]
    for k in ("waterY", "depth", "floorY"):
        if k not in pd:
            bad.append("`sensui.pond.%s` が無い — **B案は水を張る**" % k)
    if "dig" in pd:
        bad.append("`sensui.pond.dig` が残っている — A案(枯池)の欄。"
                   "B案は `waterY` / `depth` / `floorY` で持つ")
    if "surface" in pd:
        bad.append("`sensui.pond.surface`(白砂利の州)が残っている — 水面になるので廃止した")
    if all(k in pd for k in ("waterY", "depth", "floorY")):
        if abs(float(pd["waterY"]) - float(pd["depth"]) - float(pd["floorY"])) > 1e-9:
            bad.append("`waterY` − `depth` ≠ `floorY`(%.2f − %.2f ≠ %.2f)"
                       % (float(pd["waterY"]), float(pd["depth"]), float(pd["floorY"])))
    # ---- 掘削の作法(ここを外すと岬と入江が消える)
    bk = ks.get("baker") or {}
    if not bk.get("verticalWalls"):
        bad.append("`sensui.baker.verticalWalls` が true でない — "
                   "**4パスの平滑化(σ≒2.8m)で岬(出2.2m)と入江(出3.2m)が消え、"
                   "水面が +30% に膨らむ**(庭方の模擬掘削)")
    if not bk.get("levelFloor"):
        bad.append("`sensui.baker.levelFloor` が true でない — 旧掘り込みが段になり水色が斑になる")
    if bk.get("raiseBanks"):
        bad.append("`sensui.baker.raiseBanks` が true — `bankWidth` の輪が "
                   "`G_NishiNiwa` の自然地盤(造成しない帯)を持ち上げる")
    if abs(float(bk.get("inset") or 0.0)) > 1e-9:
        bad.append("`sensui.baker.inset` が 0 でない — 汀線は被覆率 f の等値線に立つので"
                   "設計線にそのまま載る")
    if bk.get("vertexY") is not None and abs(float(bk["vertexY"]) - float(pd["waterY"])) > 1e-9:
        bad.append("`sensui.baker.vertexY` が `waterY` と違う — "
                   "下げると汀線が内陸へずれる(`shoreline-walls.md`)")
    if "waterY" not in str(bk.get("api", "")):
        bad.append("`sensui.baker.api` に `wb.waterY` の代入が書かれていない — "
                   "`WaterBaker.Create` は水位を『汀の中央値 − 0.3』に自動で決めるので、"
                   "**Create のあと代入して Recarve をもう一度呼ばないと落差が消える**")
    # ---- 掘った後に隆起させる三つ
    mnd = (ks.get("mounds") or {}).get("items") or []
    if len(mnd) < 3:
        bad.append("`sensui.mounds` が %d 件 — 岬2・中島の**掘削後の隆起**が要る"
                   "(垂直掘りでも先端は 2m格子に載らない)" % len(mnd))
    for m in mnd:
        if float(m["topY"]) <= float(pd["waterY"]):
            bad.append("隆起 %s の天端 %.2fm が水面 %.2fm を超えない — 水没する"
                       % (m["label"], float(m["topY"]), float(pd["waterY"])))
    isl = [m for m in mnd if "island" in m.get("where", "")]
    if isl:
        tops = [float(b["topAbove"][1]) + float(pd["waterY"]) for b in ks["gogan"]["bands"]]
        if float(isl[0]["topY"]) > min(tops) + 1e-9:
            bad.append("中島の天端 %.2fm が護岸の天端(最小 %.2fm)より高い — "
                       "島が対岸より高いと遠近が壊れる" % (float(isl[0]["topY"]), min(tops)))
    # ---- 澪筋
    ms = ks.get("miosuji")
    if ms:
        if float(ms["floorY"]) >= float(pd["floorY"]):
            bad.append("澪筋の床 %.2fm が池底 %.2fm より下がっていない — 流れが一筋に通らない"
                       % (float(ms["floorY"]), float(pd["floorY"])))
        for p in ms["pts"]:
            # ⚠ 端の2点は汀線の頂点(#14 / #21)そのものなので、**辺の上を「外」と判定しない**
            on = min(_seg_dist((p[0], p[1]), po[i], po[(i + 1) % len(po)])
                     for i in range(len(po)))
            if not _pip_world((p[0], p[1]), po) and on > 0.02:
                bad.append("澪筋の点 (u%.1f v%.1f) が池の外" % (p[0], p[1]))
    # ---- 役割表
    ip = [p for p in d.get("program", []) if p["role"] == "池泉"]
    if ip and ip[0]["state"] != "有":
        bad.append("役割「池泉」が『%s』になっている — B案(池を掘る)の裁定"
                   "(2026-09-01 改)に反する" % ip[0]["state"])
    if not ip:
        bad.append("役割「池泉」が program に無い")
    if ip and "A" == str(ip[0].get("cert", "")).strip():
        bad.append("役割「池泉」の確度が A — ⛔ **当邸について年次を持つ史料が一つも無い**ので "
                   "B を超えない(考証方 2026-09-01)")
    return bad


def cert_claim_check(d):
    """⭐ **確度 A の僭称を見張る**(考証方 2026-09-01 の要求)。

    ⛔ 従前は `program` の「池泉」の1行しか見ていなかった。⭕ **`sensui.*` と
      `mizu.nodes[*].cert` にも回す** — 池の存在そのものが【B】なのに、部品(吐き口の型・
      落ち口・護岸)を【A】と書くと**前提より結論が強くなる**。
    ⭕ 判定は「**A を名乗る欄が、史料を名指ししているか**」。史料の名(`[…]` か『…』)を
      伴わない A は、型・位置・一般則を A と称している疑いがあるので鳴らす。
    ⚠ 『裁定=U』は史実確度と別レイヤーなので対象外(U/P/B は素通し)。"""
    bad = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "cert" and isinstance(v, str):
                    for part in v.split("/"):
                        t = part.strip()
                        if not t.startswith("A"):
                            continue
                        if "[" in t or "『" in t:
                            continue
                        bad.append("%s.cert の『%s』が史料を名指しせずに確度 A を名乗っている — "
                                   "⛔ **池の存在が B なのに部品が A** だと前提より結論が強くなる"
                                   "(考証方 2026-09-01)。型・位置・一般則は A にしない"
                                   % (path, t))
                elif not k.startswith("_"):
                    walk(v, path + "." + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + "[%d]" % i)

    if d.get("sensui"):
        walk(d["sensui"], "sensui")
    # ⭐ **2026-09-02(第4次)に適用範囲を docstring に合わせた**(考証方 中1)—
    #   ⛔ 従前は `mizu` 直下の `nodes` しか見ておらず、`mizu.takiDaichi` / `mizu.sebiyama` /
    #     `mizu.cert` と、`gardens` / `planting` / `program` の全行が対象外だった。
    for key in ("mizu", "gardens", "planting", "program", "tenkei", "tsukiyama",
                "viewpoints", "nakajikiriRule", "gardenSections"):
        if d.get(key):
            walk(d[key], key)
    # ⭐ **文章(`kosho.md`)も見る**(考証方 中1-(c))。
    #   ⛔ 検査が md を見ない限り、**json だけ B に落として本文に A が残る**型が再発する
    #     (2026-09-02: 撤回済みの「型=A」が本文に残ったまま html に公開されていた)。
    try:
        md = open(MD, encoding="utf-8").read()
    except OSError:
        md = ""
    for m in re.finditer(r"【[^】]*確度\s*A[^】]*】|【型\s*=\s*A】|=\s*A】", md):
        ln = md[:m.start()].count("\n") + 1
        # ⚠ **その行ぜんたい**を見る(史料の名は A の前にも後にも来る)。
        a = md.rfind("\n", 0, m.start()) + 1
        b = md.find("\n", m.end())
        seg = md[a: b if b > 0 else len(md)]
        if "[" in seg or "『" in seg:
            continue                     # 史料を名指ししている A は素通し
        bad.append("kosho.md L%d の『%s』が史料を名指しせずに確度 A を名乗っている — "
                   "⛔ **json だけ落として本文に A が残る**のがこの型(考証方 2026-09-02 中1)"
                   % (ln, m.group(0)))
    return bad


def _plant_cache_clear():
    _GSC.clear()
    _GCENT.clear()
    _SPL.clear()


def _L2(e, name):
    for t in e["tenkei"]:
        if t["name"] == name:
            return t
    raise KeyError(name)


def _garden_checks(e, dem):
    """庭の検査の**文言そのもの**を返す。

    ⚠ **2026-09-01(B案)に「件数」から「文言の集合」へ替えた。**件数の差で感度を測ると、
      **壊したことで別の検査が1件減る**と差引 0 になって「鳴らない」と誤診する
      (実例: 塊の box を池の上へ戻すと `group_pack` が +1 する一方
      `planting_clearance` が −1 して、実際は鳴っているのに ⛔ と表示された)。"""
    return (planting_stock_check(e) + planting_clearance_check(e, dem)
            + slope_planting_check(e, dem) + viewpoint_check(e)
            + tsukiyama_check(e) + sensui_check(e) + gogan_check(e)
            + mizu_check(e) + taki_check(e)
            + kaki_crossing_check(e) + group_place_check(e)
            + group_pack_check(e) + crown_fallback_check(e)
            + [x for x in kaidan_ground_check(e) if "庭の段" in x]
            + garden_access_check(e))


def _calls(fn):
    """関数の本文が**名前で呼んでいる関数**の集合。⛔ 実行はしない — ソースを読むだけ。"""
    t = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return {n.func.id for n in ast.walk(t)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


def check_wiring_check():
    """⭐ **感度試験にしか出てこない検査を鳴らす検査**(2026-09-02 第4次・検図 高1)。

    ⚠ **同じ型が3度起きた** — ①`garden_east_svg` と ②`garden_section_svg`/`neishi_table` が
      書かれたのに `main()` から呼ばれていなかった(第3次 高4・高5)。③その2件を直すために
      書いた `mizu_check` / `taki_check` 自身が、**`plane_check` の束にも `main()` の `WARN`
      にも入っていなかった**(第4次 高1)。呼ばれるのは `planting_sensitivity` の感度試験の
      中だけで、**素の設計を報告する経路が0回**。壊しても HTML の ⚠ が動かない。

    ⭕ そこで **`_garden_checks` の構成要素が、報告経路(`plane_check` の束 か
      `main()` の `WARN` に載る変数)へ入っているか**をソースの走査で機械照合する。
    ⛔ 「書いたはず」を人の目で確かめない。"""
    g = globals()
    want = {n for n, f in g.items()
            if n.endswith("_check") and inspect.isfunction(f)
            and f.__module__ == __name__ and n != "check_wiring_check"}
    mt = ast.parse(textwrap.dedent(inspect.getsource(main)))
    warn = set()                                     # WARN の要素に出てくる変数名
    for nd in ast.walk(mt):
        if isinstance(nd, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WARN"
                                              for t in nd.targets):
            warn |= {x.id for x in ast.walk(nd.value) if isinstance(x, ast.Name)}
    roots = set(_calls(plane_check))                 # `plane_check` の束(= WARN の pbad)
    for nd in ast.walk(mt):                          # `X = foo_check(...)` で X が WARN に載る
        if (isinstance(nd, ast.Assign) and isinstance(nd.value, ast.Call)
                and isinstance(nd.value.func, ast.Name)
                and isinstance(nd.targets[0], ast.Name) and nd.targets[0].id in warn):
            roots.add(nd.value.func.id)
    # WARN へ直に積む形(`WARN.append((..., foo_check(d)))`)も根に数える
    for nd in ast.walk(mt):
        if (isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute)
                and nd.func.attr == "append" and isinstance(nd.func.value, ast.Name)
                and nd.func.value.id == "WARN"):
            roots |= {x.func.id for x in ast.walk(nd)
                      if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)}
    # ⭐ 根から**推移的に**辿る(検査の中から呼ばれる検査も報告経路を持つ)
    seen, stack = set(), [n for n in roots if n in want]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for m2 in _calls(g[n]):
            if m2 in want and m2 not in seen:
                stack.append(m2)
    return ["検査 `%s()` は**どこからも報告されない** — 素の設計に対して一度も走らないか、"
            "走っても結果が `plane_check` の束にも `main()` の `WARN` にも入らない"
            "(感度試験の中だけで呼ばれている類)。⛔ 報告経路の無い検査は"
            "「壊しても ⚠ が動かない」= 検査に見えるだけの飾りになる"
            "(2026-09-02 第4次・検図 高1)" % n
            for n in sorted(want - seen)]


def planting_sensitivity(d, dem):
    """**感度試験** — わざと壊して検査が鳴るか。鳴らない probe は検査の穴。

    ⭐ 判定は「**素には無かった文言が出たか**」。⛔ 件数の差で測らない(上の注記)。"""
    base = _garden_checks(d, dem)
    bset = set(base)
    out = []

    def probe(label, fn):
        _plant_cache_clear()
        e = copy.deepcopy(d)
        fn(e)
        try:
            msg = _garden_checks(e, dem)
            n = len([x for x in msg if x not in bset])
        except Exception as ex:                       # 落ちるのも「鳴った」に数える
            n = 99
        _plant_cache_clear()
        out.append((label, n))

    def _L(e, zone, layer):
        """⚠ **層は名で引く。**添字で指すと層を足した日に別の層を壊す probe になる
        (2026-09-01 に 10層 → 27層 へ組み替えたとき、[9] が別の庭を指した)。"""
        for i, x in enumerate(e["planting"]):
            if x["zone"] == zone and x["layer"] == layer:
                return x
        raise KeyError(zone + "/" + layer)

    probe("使用禁止の部材を植栽へ戻す",
          lambda e: _L(e, "G_NishiNiwa", "中木(常緑)")["parts"][0].__setitem__(
              "prefab", "BroadleafTree") or _L(e, "G_NishiNiwa", "中木(常緑)")["parts"][0]
          .__setitem__("api", "EdoAssets.Own.Broadleaf"))
    probe("層から parts を落とす", lambda e: _L(e, "G_NishiNiwa", "主木").__setitem__("parts", []))
    probe("n と parts の合計を食い違わせる",
          lambda e: _L(e, "G_NishiNiwa", "主木").__setitem__("n", 99))
    probe("在庫に無い部材を名指しする",
          lambda e: _L(e, "G_NishiNiwa", "主木")["parts"][0].__setitem__("prefab", "Tree_Mokkoku_Big_01"))
    probe("api の番号を取り違える",
          lambda e: _L(e, "G_NishiNiwa", "主木")["parts"][0].__setitem__("api", 'JG.Pine("Small", 3)'))
    probe("裁定待ちの層に provisional を付けずに pending を立てる",
          lambda e: _L(e, "G_NishiNiwa", "主木").__setitem__("pending", "アカマツ"))
    probe("主景(main)を消す",
          lambda e: [v.pop("main", None) for v in e["viewpoints"]])
    probe("主視点の眼高を 1m 上げる",
          lambda e: e["viewpoints"][0].__setitem__("eye", e["viewpoints"][0]["eye"] + 1.0))
    probe("御泉水の汀を主庭の外へ出す",
          lambda e: e["sensui"]["pond"]["outline"][0].__setitem__(0, -20.0))
    probe("役割「池泉」の行を落とす",
          lambda e: e.__setitem__("program", [p for p in e["program"] if p["role"] != "池泉"]))
    probe("築山の頂と床几の点景をずらす",
          lambda e: _L2(e, "T_Shogi").__setitem__("u", -50.0))
    probe("垣の口をふさぐ(露地の道を垣が横切る)",
          lambda e: _L2(e, "T_Kaki_Yotsume_E1")["b"].__setitem__(1, 31.5))
    probe("園路を全部落とす(庭が歩けなくなる)", lambda e: e.__setitem__("routes", []))
    probe("塊の置き場所を全部 null にする(均一散布へ戻す)",
          lambda e: [gs.__setitem__("box", None) or gs.pop("near", None) or
                     gs.pop("ref", None) or gs.pop("along", None)
                     for pl in e["planting"] for gs in pl.get("groups", [])])
    probe("法肩の遮蔽木を間引く(pitch を倍に)",
          lambda e: e["slopeArea"]["screen"].__setitem__("pitch",
                                                         e["slopeArea"]["screen"]["pitch"] * 2))
    probe("帯Bへ高木を入れる",
          lambda e: e["slopePlanting"][1].__setitem__("band", "帯B 中部"))
    probe("庭を狭めて本数を置ききれなくする",
          lambda e: e["gardens"].__setitem__(
              [i for i, g in enumerate(e["gardens"]) if g["name"] == "G_NishiNiwa"][0],
              dict(e["gardens"][[i for i, g in enumerate(e["gardens"])
                                 if g["name"] == "G_NishiNiwa"][0]], u1=-70.0)))
    probe("池の水面を掘削の底へ下げる(`waterY` = `floorY`)",
          lambda e: e["sensui"]["pond"].__setitem__("waterY", e["sensui"]["pond"]["floorY"]))
    probe("A案の欄(`pond.dig`)を生やす",
          lambda e: e["sensui"]["pond"].__setitem__("dig", 0.45))
    probe("掘削を既定(なだらか)へ戻す(岬と入江が平滑化で消える)",
          lambda e: e["sensui"]["baker"].__setitem__("verticalWalls", False))
    probe("土手を盛る(`raiseBanks`)— 造成しない西庭の地盤を持ち上げる",
          lambda e: e["sensui"]["baker"].__setitem__("raiseBanks", True))
    probe("輪郭を内へオフセットする(`baker.inset`)",
          lambda e: e["sensui"]["baker"].__setitem__("inset", 0.5))
    probe("`WaterBaker.Create` の自動水位のまま流す(`baker.api` から waterY 代入を消す)",
          lambda e: e["sensui"]["baker"].__setitem__("api", "WaterBaker.Create(outline, depth)"))
    probe("掘削後の隆起(`mounds`)を落とす(岬の先端と中島が水没する)",
          lambda e: e["sensui"]["mounds"].__setitem__("items", []))
    probe("中島を護岸の天端より高くする(遠近が壊れる)",
          lambda e: e["sensui"]["mounds"]["items"][2].__setitem__("topY", 27.60))
    probe("澪筋の床を池底と同じにする(流れが一筋に通らない)",
          lambda e: e["sensui"]["miosuji"].__setitem__(
              "floorY", e["sensui"]["pond"]["floorY"]))
    probe("水尻の堰の天端を水面より上げる(越流しない)",
          lambda e: [n.__setitem__("weirY", 26.60) for n in e["mizu"]["nodes"]
                     if n["id"] == "MZ7"])
    probe("落し枡C を池の水面より下げる(水が逆流する)",
          lambda e: [n.__setitem__("waterY", 25.90) for n in e["mizu"]["nodes"]
                     if n["id"] == "MZ3"])
    probe("水の系(`mizu`)を丸ごと落とす",
          lambda e: e.pop("mizu", None))
    probe("台地端の滝の段を続かなくする(二の段の天端をずらす)",
          lambda e: e["mizu"]["takiDaichi"]["tiers"][1].__setitem__("topY", 24.20))
    probe("滝見口 `NJ_Taki_Kido` を落とす(滝が板塀に隠れる)",
          lambda e: e.__setitem__("nakajikiri",
                                  [x for x in e["nakajikiri"] if x["name"] != "NJ_Taki_Kido"]))
    probe("築山の土の出所(`do`)を落とす",
          lambda e: e["tsukiyama"][0].pop("do", None))
    probe("築山の法を測る区間(`batter.measure`)を落とす",
          lambda e: e["tsukiyama"][0]["batter"].pop("measure", None))
    probe("築山の裾を真円にする(輪郭を締めた意味が消える)",
          lambda e: e["tsukiyama"][0].__setitem__(
              "skirt", [[e["tsukiyama"][0]["u"] + 4.0 * math.cos(i * 0.5712),
                         e["tsukiyama"][0]["v"] + 4.0 * math.sin(i * 0.5712)]
                        for i in range(11)]))
    probe("護岸の天端を水面すれすれへ下げる(見え面が `showMin` に足りない)",
          lambda e: [b.__setitem__("topAbove", [0.10, 0.20])
                     for b in e["sensui"]["gogan"]["bands"]])
    probe("護岸の据え付け面を水面より上げる(根石が水から出る)",
          lambda e: [b.__setitem__("seatY", 26.40) for b in e["sensui"]["gogan"]["bands"]])
    probe("`gogan.seatRule` を落とす(据え付けが輪郭点そのものになる)",
          lambda e: e["sensui"]["gogan"].pop("seatRule", None))
    probe("天端を独立乱数で振る作法へ戻す(`topJitter` を生やす)",
          lambda e: e["sensui"]["gogan"].__setitem__("topJitter", [0.1, 0.6]))
    probe("`bury` の基準面を A案の『枯池の床』へ戻す",
          lambda e: e["sensui"]["gogan"].__setitem__("buryFrom", "枯池の床"))
    probe("塊の box を旧の『池の西縁の背後』へ戻す(座標はあるのに入らない塊)",
          lambda e: [p["groups"][0].__setitem__("box", [-45, 40, -43, 44])
                     for p in e["planting"]
                     if p["zone"] == "G_Sensui" and p["layer"] == "中木(落葉)"])
    # ⭐ **2026-09-02 に差し替えた。**旧 probe「樹冠の仮値を落とす」は、目録が焼き直されて
    #   `plantRule.crownFallback`(繋ぎの仮値)を**消した**ので**空振りになった**
    #   (壊す対象そのものが無い = 検査の穴ではない)。⛔ 空振りの probe を残さない。
    #   ⭕ 同じ性質(**樹冠が測れないまま退避を合格にしない**)を、目録に無い部材を
    #     名指しする形で突く。
    probe("`crownRule` の役の部材を目録に無い名前にする(樹冠が測れなくなる)",
          lambda e: [pt.__setitem__("prefab", "Tree_Nai_Mono")
                     for p in e["planting"]
                     if p["zone"] == "G_Sensui" and p["layer"] == "中木(常緑)"
                     for pt in p["parts"]])
    probe("築山の段を 12 段へ戻す(踏面が庭の段の帯を外れる)",
          lambda e: [k.__setitem__("steps", 12) for k in e["kaidans"]
                     if k["name"] == "K_Tsukiyama"])
    probe("庭の段の帯(`const.gardenStepRule`)を落とす(検査が回らなくなる)",
          lambda e: e["const"].pop("gardenStepRule", None))
    probe("護岸石を発掘の寸法帯より大きくする(A案の『遠いほど大きく』へ戻す)",
          lambda e: e["sensui"]["gogan"]["bands"][1].__setitem__("tenbaishi", [1.15, 1.45]))
    probe("役割「池泉」の確度を A に上げる(当邸に年次を持つ史料は無い)",
          lambda e: [p.__setitem__("cert", "A") for p in e["program"] if p["role"] == "池泉"])
    # 退避に載せる probe だけは「散らし方」でなく「測り方」を試す —
    # 規則を変えずに木を1本だけ棟の真上へ置き、検査が名指しで鳴るか見る
    _plant_cache_clear()
    m0 = d["munes"][0]
    ex = (("G_NishiNiwa", "主木"), ((m0["u0"] + m0["u1"]) / 2.0, (m0["v0"] + m0["v1"]) / 2.0,
                                  d["planting"][0]["parts"][0]))
    ex_msg = planting_clearance_check(d, dem, ex)
    out.append(("木を1本 棟の真上に置く", len([x for x in ex_msg if x not in bset])))
    _plant_cache_clear()
    return len(base), out


# ---------------------------------------------------------------- 樹の姿(作図)
TREE_COL = {
    "松":   ("#3B5A3C", "#2C4630", "#6B5637"),
    "広葉": ("#6E8B49", "#5A7439", "#6B5637"),
    "常緑": ("#33512F", "#25401F", "#4E4030"),
    "梅":   ("#5E7A4E", "#4A6440", "#3A322A"),
    "灌木": ("#7E9A55", "#68843F", "#6B5637"),
    "常緑材質": ("#33512F", "#25401F", "#6B5637"),
    "低ポリ": ("#8FB36A", "#7BA055", "#8A7350"),
}


def tree_glyph(x, y0, hpx, wpx, kind, rg, op=1.0):
    """1本の樹影。x=幹の芯 / y0=地面 / hpx=樹高 / wpx=樹冠径(すべて px)。"""
    c, c2, tc = TREE_COL.get(kind, TREE_COL["広葉"])
    g = []
    tw = max(1.2, wpx * 0.055)
    if kind == "松":
        th = hpx * 0.55
        lean = (rg.random() - 0.5) * wpx * 0.16
        g.append('<path d="M%.1f %.1f Q%.1f %.1f %.1f %.1f" stroke="%s" stroke-width="%.1f" '
                 'fill="none" stroke-linecap="round" opacity="%.2f"/>'
                 % (x, y0, x + lean * 0.6, y0 - th * 0.6, x + lean, y0 - th, tc, tw, op))
        n = 4
        for i in range(n):
            f = i / float(n - 1)
            cy = y0 - hpx * (0.42 + 0.56 * f)
            cw = wpx * (0.50 - 0.30 * f) * (0.9 + 0.2 * rg.random())
            cx = x + lean * (0.5 + 0.5 * f) + (rg.random() - 0.5) * wpx * 0.22
            g.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity="%.2f"/>'
                     % (cx, cy, cw, cw * 0.40, c if i % 2 else c2, op * 0.95))
    elif kind == "常緑":
        th = hpx * 0.36
        g.append(R(x - tw / 2, y0 - th, tw, th, fill=tc, op=op))
        g.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity="%.2f"/>'
                 % (x, y0 - hpx * 0.64, wpx * 0.46, hpx * 0.36, c, op))
        for i in range(3):
            g.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity="%.2f"/>'
                     % (x + (rg.random() - 0.5) * wpx * 0.4, y0 - hpx * (0.5 + 0.35 * rg.random()),
                        wpx * 0.24, hpx * 0.16, c2, op * 0.8))
    elif kind == "梅":
        th = hpx * 0.34
        g.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="%.1f" opacity="%.2f"/>'
                 % (x, y0, x + wpx * 0.04, y0 - th, tc, tw * 1.5, op))
        for i in range(5):
            a = -2.4 + i * 0.75 + (rg.random() - 0.5) * 0.3
            L = hpx * (0.30 + 0.20 * rg.random())
            px, py = x + wpx * 0.04, y0 - th
            pth = "M%.1f %.1f" % (px, py)
            for k in range(3):
                a += (rg.random() - 0.5) * 0.9
                px += math.cos(a) * L / 3.0
                py += math.sin(a) * L / 3.0
                pth += " L%.1f %.1f" % (px, py)
            g.append('<path d="%s" stroke="%s" stroke-width="%.1f" fill="none" opacity="%.2f"/>'
                     % (pth, tc, max(0.8, tw * 0.6), op))
            g.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity="%.2f"/>'
                     % (px, py, wpx * 0.16, wpx * 0.12, c, op * 0.85))
    elif kind == "灌木":
        for i in range(3):
            g.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity="%.2f"/>'
                     % (x + (i - 1) * wpx * 0.22, y0 - hpx * (0.42 + 0.18 * rg.random()),
                        wpx * 0.32, hpx * 0.44, c if i % 2 else c2, op))
    elif kind == "低ポリ":
        th = hpx * 0.34
        g.append(R(x - tw, y0 - th, tw * 2, th, fill=tc, op=op))
        r = wpx * 0.5
        cy = y0 - hpx * 0.66
        pts = []
        for i in range(6):
            a = i * 1.0472
            pts.append("%.1f,%.1f" % (x + math.cos(a) * r, cy + math.sin(a) * r * 0.72))
        g.append('<polygon points="%s" fill="%s" opacity="%.2f"/>' % (" ".join(pts), c, op))
    else:                                                     # 広葉 / 常緑材質(樹形は広葉のまま)
        th = hpx * 0.40
        g.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="%.1f" opacity="%.2f"/>'
                 % (x, y0, x + wpx * 0.05, y0 - th, tc, tw, op))
        g.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity="%.2f"/>'
                 % (x + wpx * 0.05, y0 - hpx * 0.66, wpx * 0.5, hpx * 0.34, c, op))
        for i in range(3):
            g.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity="%.2f"/>'
                     % (x + (rg.random() - 0.5) * wpx * 0.5, y0 - hpx * (0.55 + 0.28 * rg.random()),
                        wpx * 0.26, hpx * 0.15, c2, op * 0.75))
    return "".join(g)


def part_kind(pt):
    """部材から樹影の種別を決める(作図のためだけ)。"""
    nm = pt.get("prefab", "")
    if "BlackPine" in nm or "Pine" in nm:
        return "松"
    if "Jouryoku" in nm:
        return "常緑"
    if "Momiji" in nm or "Ume" in nm or "Sakura" in nm:
        return "広葉"
    if "Broadleaf" in nm:
        return "低ポリ"
    return "灌木"


# ---------------------------------------------------------------- 其◯ 西斜面の植栽(平面)
def slope_plan_svg(d, dem):
    """西斜面の植栽の平面。**グリッドを倒して描く**(v=左右・u=上下)。

    ⚠ 世界の向きのまま描くと 74m×190m の細長い短冊になり、940px 幅では
      縦 1,800px を超えて樹冠が実寸で読めない。ここは向きより**読めること**を採る
      (方位は図の隅に明記する)。"""
    gr = RGrid(d)
    K = gr.ken
    P = d["polygon"]
    smp = slope_samples(d, dem)
    sp = scatter_slope(d, dem)
    us = [q[2] for q in smp]
    vs = [q[3] for q in smp]
    u0, u1 = min(us) - 3.0, max(us) + 3.0
    v0, v1 = min(vs) - 3.0, max(vs) + 3.0
    W = 940.0
    sc = W / ((v1 - v0) * K)                          # px/m
    H = (u1 - u0) * K * sc + 74.0
    X = lambda u, v: (v - v0) * K * sc
    Y = lambda u, v: 30.0 + (u1 - u) * K * sc
    g = _sv(W, H, "松平出羽守上屋敷 西斜面の植栽")
    g.append(R(0, 0, W, H, fill="var(--paper2)"))
    puv = [gr.L(q[0], q[1]) for q in P]
    g.append('<polygon points="%s" fill="var(--paper)" stroke="var(--ink-lo)" stroke-width="1"/>'
             % " ".join("%.1f,%.1f" % (X(*q), Y(*q)) for q in puv))
    BC = {d["slopeBands"][0]["name"]: "#8CA86A",
          d["slopeBands"][1]["name"]: "#C6C08A",
          d["slopeBands"][2]["name"]: "#DFE2CC"}
    st = 1.0
    for q in smp:
        g.append(R(X(q[2], q[3]) - st * K * sc / 2, Y(q[2], q[3]) - st * K * sc / 2,
                   st * K * sc + 0.5, st * K * sc + 0.5, fill=BC.get(q[6], "#ccc"), op=0.9))
    for m in d["munes"] + d["service"]:
        if m["u1"] < u0 or m["u0"] > u1 or m["v1"] < v0 or m["v0"] > v1:
            continue
        g.append(R(X(m["u1"], m["v0"]), Y(m["u1"], m["v0"]),
                   (m["v1"] - m["v0"]) * K * sc, (m["u1"] - m["u0"]) * K * sc,
                   fill="var(--ink-mid)", stroke="var(--ink)", sw=0.7, op=0.85))
        g.append(T(X(m["u1"], (m["v0"] + m["v1"]) / 2) + (m["v1"] - m["v0"]) * K * sc / 2,
                   Y((m["u0"] + m["u1"]) / 2, 0) + 4,
                   MUNE_JA.get(m["name"], m.get("label", m["name"])), "rmS", "middle", 10))
    for e in d["slopeArea"]["toeEdges"]:
        a2, b2 = gr.L(*P[e % len(P)]), gr.L(*P[(e + 1) % len(P)])
        g.append(LN(X(*a2), Y(*a2), X(*b2), Y(*b2), "var(--nagaya)", 2.2))
        g.append(T(X((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2),
                   Y((a2[0] + b2[0]) / 2, 0) + 14, "辺%d" % e, "anS", "middle", 9,
                   "var(--nagaya)"))
    cs = crest_stations(d, dem, 1.0)
    if cs:
        g.append('<polyline points="%s" fill="none" stroke="var(--take)" stroke-width="2.4" '
                 'stroke-dasharray="7 4"/>'
                 % " ".join("%.1f,%.1f" % (X(*q[0]), Y(*q[0])) for q in cs))
        g.append(T(X(*cs[len(cs) // 2][0]), Y(*cs[len(cs) // 2][0]) - 6,
                   "法肩(竹垣 R_West/R_South)", "anS", "middle", 9, "var(--take)"))
    for r in d.get("rails", []):
        pts = r["pts"]
        g.append('<polyline points="%s" fill="none" stroke="var(--take)" stroke-width="1.2" '
                 'stroke-dasharray="3 3" opacity="0.7"/>'
                 % " ".join("%.1f,%.1f" % (X(q[0], q[1]), Y(q[0], q[1])) for q in pts))
    tot = 0
    for lay in d.get("slopePlanting", []):
        for (u, v, pt) in sp.get(lay["layer"], []):
            gm = part_geom(pt)
            if not gm:
                continue
            tot += 1
            kd = part_kind(pt)
            col = "#3B5A3C" if kd == "松" else ("#6E8B49" if kd == "広葉" else "#93A863")
            g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.40"/>'
                     % (X(u, v), Y(u, v), gm[0] / 2.0 * sc, col))
            g.append('<circle cx="%.1f" cy="%.1f" r="1.6" fill="%s"/>' % (X(u, v), Y(u, v), col))
    area = slope_band_area(d, dem)
    g.append(R(8, H - 40, 470, 32, fill="var(--paper)", stroke="var(--ink-lo)", sw=1.0, op=0.94))
    x = 18
    for b in d["slopeBands"]:
        g.append(R(x, H - 30, 12, 12, fill=BC.get(b["name"], "#ccc"), op=0.9))
        g.append(T(x + 16, H - 20, "%s %.0f m²" % (b["name"], area.get(b["name"], 0)),
                   "anS", "start", 10))
        x += 158
    g.append(T(4, 16, "**グリッドを倒した図** — 左=北(v小)／右=南(v大)／上=御殿の側(u大)／"
                      "下=溜池の側(u小)。円は樹冠の実寸", "anS", "start"))
    g.append(T(W - 4, 16, "帯は法肩からの落差の割合 ／ 樹 %d 本" % tot, "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其◯ 西斜面の断面(遮蔽)
def slope_section_svg(d, dem, vcut, half=6.0):
    """v=vcut で切った西斜面の断面。**垂直と水平は同縮尺**(遮蔽の当たりを目で取るため)。"""
    gr = RGrid(d)
    K = gr.ken
    C = d["const"]
    sa = d["slopeArea"]
    sp = scatter_slope(d, dem)
    mune = None
    for m in d["munes"]:
        if m["v0"] <= vcut <= m["v1"] and (mune is None or m["u0"] < mune["u0"]):
            mune = m                                  # **その断面を跨ぐ棟のうち一番西**
    u1 = (mune["u0"] + 6.0) if mune else -44.0
    u0 = -95.0
    prof = []
    u = u0
    while u <= u1:
        w = gr.W(u, vcut)
        y = _dem_at(dem, w[0], w[1])
        if y is not None:
            prof.append((u, y))
        u += 0.25
    if not prof:
        return ""
    ys = [p[1] for p in prof]
    ridge = 0.0
    if mune:
        ru0, ru1, rv0, rv1, a, hh = _roof_geom(d, mune)
        ridge = mune["y"] + C["gotenFloor"] + C["muneEave"] + hh
    ytop = max(max(ys), ridge) + 4
    ybot = min(ys) - 2
    W = 940.0
    s = W / ((u1 - u0) * K)
    H = (ytop - ybot) * s + 74
    g = _sv(W, H, "西斜面の断面 v=%g" % vcut)
    g.append(R(0, 0, W, H, fill="var(--paper2)"))
    X = lambda uu: (uu - u0) * K * s
    Y = lambda yy: H - 46 - (yy - ybot) * s
    g.append('<polygon points="%s %.1f,%.1f %.1f,%.1f" fill="var(--dan3)" stroke="var(--ink)" '
             'stroke-width="1.1"/>'
             % (" ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in prof),
                X(u1), Y(ybot), X(u0), Y(ybot)))
    # 帯の境
    cu = sa["crest"]
    ycrest = None
    for i in range(len(cu) - 1):
        if min(cu[i][1], cu[i + 1][1]) <= vcut <= max(cu[i][1], cu[i + 1][1]) and cu[i][0] == cu[i + 1][0]:
            ycrest = _dem_at(dem, *gr.W(cu[i][0], vcut))
            ucrest = cu[i][0]
    if ycrest is None:
        ycrest, ucrest = prof[-1][1], u1
    ytoe = min(ys)
    for b in d["slopeBands"]:
        for tt in (b["from"], b["to"]):
            yy = ycrest - tt * (ycrest - ytoe)
            uu = None
            for p in reversed(prof):                  # **法肩から法尻へ**下って探す
                if p[0] <= ucrest and p[1] <= yy:
                    uu = p[0]
                    break
            if uu is None:
                continue
            g.append(LN(X(uu), Y(yy), X(uu), Y(yy) - 22, "var(--shu)", 0.9, "3 3"))
            g.append(T(X(uu) - 4, Y(yy) - 26, "t=%.2f" % tt, "anS", "end", 8.5, "var(--shu)"))
    # 造成後の面(段) — **地盤線は造成前の DEM** なので、埋め戻す穴が口を開けて見える。
    # 何を埋めるのかが読めるように、面の高さを重ねる。
    for t in d["terraces"]:
        if not (t["v0"] <= vcut <= t["v1"]):
            continue
        a, b = max(t["u0"], u0), min(t["u1"], u1)
        if b <= a:
            continue
        g.append(LN(X(a), Y(t["y"]), X(b), Y(t["y"]), "var(--shu)", 1.4, "6 3"))
        g.append(T((X(a) + X(b)) / 2, Y(t["y"]) - 5, "面 %s %.1fm" % (t["name"], t["y"]),
                   "anS", "middle", 8.5, "var(--shu)"))
    # 御殿(西面)
    if mune:
        eave = mune["y"] + C["gotenFloor"] + C["muneEave"]
        mu = mune["u0"]
        g.append(R(X(mu), Y(eave), X(u1) - X(mu), (eave - mune["y"]) * s,
                   fill="var(--ink-mid)", stroke="var(--ink)", sw=0.8))
        g.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="var(--hei)" opacity="0.85"/>'
                 % (X(mu) - C["nokiE"] * s, Y(eave), X(u1), Y(eave), X(u1), Y(ridge)))
        g.append(T(X(mu) - 6, Y(eave) - 8, "%s の西面(軒 %.1fm・大棟 %.1fm)"
                   % (MUNE_JA.get(mune["name"], mune["name"]), eave, ridge), "anS", "end", 10))
    # 樹
    rg = _rng("sec/%g" % vcut)
    drawn = 0
    for lay in d.get("slopePlanting", []):
        for (u, v, pt) in sp.get(lay["layer"], []):
            if abs(v - vcut) > half / K:
                continue
            w = gr.W(u, v)
            y = _dem_at(dem, w[0], w[1])
            gm = part_geom(pt)
            if y is None or gm is None:
                continue
            drawn += 1
            g.append(tree_glyph(X(u), Y(y), gm[1] * s, gm[0] * s, part_kind(pt), rg,
                                0.55 + 0.45 * (1.0 - abs(v - vcut) * K / max(half, 0.1))))
    # 見通し線 — 対岸から御殿の軒が見えるか
    if mune:
        eave = mune["y"] + C["gotenFloor"] + C["muneEave"]
        mu = mune["u0"]
        toe_u = prof[0][0]
        need = []
        for Dv, col in ((100.0, "#A8452C"), (250.0, "#B8763A"), (600.0, "#7A5C3A")):
            vu = toe_u - Dv / K
            vy = ytoe + 1.6
            f = (ucrest - vu) / (mu - vu)
            need.append((Dv, vy + (eave - vy) * f - ycrest))
            g.append(LN(X(max(vu, u0)), Y(vy + (eave - vy) * (max(vu, u0) - vu) / (mu - vu)),
                        X(mu), Y(eave), col, 1.0, "5 4"))
        g.append(T(4, H - 26, "破線=対岸(法尻から 100/250/600m)の目の高さ %.1fm から %s の軒 "
                              "%.1fm への見通し。**法肩で必要な樹高 %s**(遮蔽木の最低樹高は"
                              "これを上回る)"
                   % (ytoe + 1.6, MUNE_JA.get(mune["name"], mune["name"]), eave,
                      " / ".join("%.1fm" % max(n, 0) for _D, n in need)),
                   "anS", "start", 10.5, "var(--shu)"))
    g.append(LN(X(ucrest), Y(ycrest), X(ucrest), Y(ycrest) - 0.9 * s, "var(--take)", 2.4))
    g.append(T(X(ucrest) + 5, Y(ycrest) - 0.9 * s - 5, "竹垣(法肩)", "anS", "start", 8.5, "var(--take)"))
    g.append(LN(X(prof[0][0]), Y(prof[0][1]), X(prof[0][0]), Y(prof[0][1]) - 1.4 * s,
                "var(--take)", 2.0))
    g.append(T(X(prof[0][0]) + 4, Y(prof[0][1]) - 1.4 * s - 4, "木柵(区画線)", "anS", "start", 8.5,
               "var(--take)"))
    g.append(T(W - 4, 18, "v=%g の断面(帯 ±%.0fm の樹を投影)／ 左=溜池 ／ 垂直・水平とも実寸 ／ 樹 %d 本"
               % (vcut, half, drawn), "anS", "end"))
    g.append(T(4, H - 10, "u%.0f(法尻)← → u%.0f(御殿の西面)" % (u0, u1), "anS", "start", 9.5))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 其◯ 樹影くらべ(裁定図)
def tree_compare_svg(d):
    """**裁定図。**使用禁止になった自作の木・在庫の木・案A/B/C を**同じ縮尺**で並べる。"""
    idx = asset_index()
    ROWS = [
        ("使用禁止", [("BroadleafTree", 1.0, "低ポリ", "⛔ 自作(使用禁止)")]),
        ("在庫の高木", [("Tree_BlackPine_Big_Green_02", 1.65, "松", "黒松 Big"),
                    ("Tree_BlackPine_Mid_Green_01", 1.65, "松", "黒松 Mid"),
                    ("Tree_BlackPine_Small_Green_03", 1.65, "松", "黒松 Small"),
                    ("Tree_Sakura_Big_Summer_05", 1.4, "広葉", "桜(夏)Big"),
                    ("Tree_Sakura_Mid_Summer_01", 1.4, "広葉", "桜(夏)Mid"),
                    ("Tree_Sakura_Small_Summer_01", 1.0, "広葉", "桜(夏)Small 等倍")]),
        ("在庫の低木", [("prefab_maple_bush_04", 1.0, "灌木", "カエデの灌木"),
                    ("prefab_grey_willow_04", 1.0, "灌木", "ヤナギの灌木"),
                    ("Azalea A 03", 1.0, "灌木", "躑躅"),
                    ("Plant_Boxwood_Spring_02", 1.0, "灌木", "柘植"),
                    ("Plant_PaintedFern_Spring_01", 1.0, "灌木", "羊歯")]),
    ]
    W = 940.0
    LBL = 118.0                                   # 行見出しの幅(px)
    scale = 9.0                                   # px/m(全行で共通 = 同じ縮尺)
    rowH = [0.0] * len(ROWS)
    for i, (_lb, items) in enumerate(ROWS):
        hm = 0.0
        for nm, sc, _k, _t in items:
            r = idx.get(nm)
            if r:
                hm = max(hm, r["sy"] * sc)
        rowH[i] = hm * scale + 46
    Hplans = 250.0
    H = sum(rowH) + Hplans + 30
    g = _sv(W, H, "樹影くらべ(裁定図)")
    g.append(R(0, 0, W, H, fill="var(--paper2)"))
    rg = _rng("compare")
    y = 6.0
    for i, (lb, items) in enumerate(ROWS):
        base = y + rowH[i] - 22
        g.append(LN(LBL, base, W - 10, base, "var(--ink-lo)", 1.0))
        g.append(T(LBL - 8, base - 4, lb, "anS", "end", 11.5))
        x = LBL + 16.0
        for nm, sc, kind, tag in items:
            r = idx.get(nm)
            if not r:
                continue
            hm, wm = r["sy"] * sc, max(r["sx"], r["sz"]) * sc
            g.append(tree_glyph(x + wm * scale / 2, base, hm * scale, wm * scale, kind, rg))
            g.append(T(x + wm * scale / 2, base + 12, tag, "anS", "middle", 9.5))
            g.append(T(x + wm * scale / 2, base + 22, "%.1fm ／ %s三角" % (hm, "{:,}".format(r["tris"])),
                       "anS", "middle", 8.5, "var(--dim)"))
            x += max(wm * scale, 74.0) + 22
        y += rowH[i]
    # 人(尺度)
    _b1 = 6 + rowH[0] + rowH[1] - 22                       # 高木の行の地面
    g.append(LN(LBL + 4, _b1, LBL + 4, _b1 - 1.6 * scale, "var(--shu)", 2.6))
    g.append(T(LBL + 8, _b1 - 1.6 * scale - 3, "人 1.6m", "anS", "start", 8.5, "var(--shu)"))
    # 案の比較
    g.append(LN(10, y + 4, W - 10, y + 4, "var(--ink-lo)", 1.0))
    _n1 = sum(l["n"] for l in d.get("planting", []) + d.get("slopePlanting", [])
              if l.get("pending") == "常緑広葉樹")
    _n2 = sum(l["n"] for l in d.get("planting", []) if l.get("pending") == "ウメ")
    g.append(T(10, y + 22, "穴①常緑広葉樹(%d本)・穴②ウメ(%d本)の埋め方 — "
                           "同じ縮尺で並べた見え方" % (_n1, _n2), "anS", "start", 12))
    PL = [("案A 在庫で代用", [("Tree_Sakura_Small_Summer_01", 1.4, "広葉")], "広葉",
           "枝ぶりも葉の色も桜のまま。夏の遠景なら通る"),
          ("案B 材質だけ替える", [("Tree_Sakura_Small_Summer_01", 1.4, "常緑材質")], "広葉",
           "葉は照葉樹の濃緑になるが枝ぶりは桜のまま"),
          ("案C 新造する", [(None, 1.0, "常緑")], "梅",
           "枝の分岐から起こす。在庫と並べても見劣りしない")]
    x = 30.0
    for title, items, umek, note in PL:
        bx = x
        g.append(R(bx, y + 34, 280, 190, fill="var(--paper)", stroke="var(--ink-lo)", sw=1.0))
        g.append(T(bx + 12, y + 54, title, "anS", "start", 12))
        base = y + 196
        gx = bx + 70
        for nm, sc, kind in items:
            if nm:
                r = idx.get(nm)
                hm, wm = r["sy"] * sc, max(r["sx"], r["sz"]) * sc
            else:
                hm, wm = 6.2, 4.6
            g.append(tree_glyph(gx, base, hm * scale, wm * scale, kind, rg))
            g.append(T(gx, base + 14, "%.1fm" % hm, "anS", "middle", 9))
        # ウメの姿も並べる
        g.append(tree_glyph(bx + 205, base, 5.4 * scale, 5.4 * scale, umek, rg))
        g.append(T(bx + 205, base + 14, "梅の見え方", "anS", "middle", 9))
        for k, ln in enumerate(_wrap_ja(note, 20)):
            g.append(T(bx + 12, y + 76 + k * 15, ln, "anS", "start", 10, "var(--dim)"))
        x += 300
    g.append(T(W - 6, 16, "同じ縮尺(1m = %.1fpx)" % scale, "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


def _wrap_ja(s, n):
    return [s[i:i + n] for i in range(0, len(s), n)]




# ---------------------------------------------------------------- 表
def _parts_cell(lay):
    out = []
    for pt in lay.get("parts", []):
        g = part_geom(pt)
        tag = "<code>%s</code>×%d" % (html.escape(pt["api"]), pt["n"])
        if pt.get("scale", 1.0) != 1.0:
            tag += " ×%.2f" % pt["scale"]
        if pt.get("provisional"):
            tag = "<span style='color:var(--shu)'>▲</span>" + tag
        if pt.get("apiPending"):
            tag += "<span style='color:var(--shu)'>*</span>"
        if g is None:
            tag += " <b style='color:var(--shu)'>(在庫に無い)</b>"
        out.append(tag)
    return " ／ ".join(out)


def _size_cell(lay):
    hs, ws, tr = [], [], 0
    for pt in lay.get("parts", []):
        g = part_geom(pt)
        if not g:
            continue
        ws.append(g[0])
        hs.append(g[1])
        tr += g[2] * pt["n"]
    if not hs:
        return "—", "—"
    return ("%.1f〜%.1f m" % (min(hs), max(hs)) if max(hs) - min(hs) > 0.05 else "%.1f m" % hs[0],
            "{:,}".format(tr))


def planting_table(d):
    rows = ""
    for pl in d.get("planting", []):
        hh, tr = _size_cell(pl)
        rows += ("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td>%d</td>"
                 "<td class='note'>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                 % (pl["zone"], pl["layer"], pl["species"], pl["n"], _parts_cell(pl),
                    hh, tr, inline(pl.get("_", ""))))
    return ('<div class="tw"><table><thead><tr><th>庭</th><th>層</th><th class="note">樹種</th>'
            '<th>本</th><th class="note">部材(EdoAssets の呼び出し)</th><th>樹高</th>'
            '<th>三角</th><th class="note">置き方</th></tr></thead><tbody>%s</tbody></table></div>'
            % rows)


def slope_band_table(d, dem):
    area = slope_band_area(d, dem)
    sp = scatter_slope(d, dem)
    cnt = {}
    for lay in d.get("slopePlanting", []):
        cnt.setdefault(lay["band"], {}).setdefault(lay.get("role", "?"), 0)
        cnt[lay["band"]][lay.get("role", "?")] += len(sp.get(lay["layer"], []))
    rows = ""
    for b in d["slopeBands"]:
        A = area.get(b["name"], 0.0)
        dn = []
        for role in ("高木", "中木", "低木"):
            n = cnt.get(b["name"], {}).get(role, 0)
            lo, hi = b["dens"][role]
            dn.append("%s %d本 = %.2f <span class='note'>(%.2f〜%.2f)</span>"
                      % (role, n, (n / A * 100.0) if A else 0.0, lo, hi))
        rows += ("<tr><td>%s</td><td>%.2f〜%.2f</td><td>%.0f m²</td>"
                 "<td class='note'>%s</td><td class='note'>%s</td><td class='note'>%s</td></tr>"
                 % (b["name"], b["from"], b["to"], A, "<br>".join(dn),
                    inline(b["veg"]), inline(b.get("ground", ""))))
    return ('<div class="tw"><table><thead><tr><th>帯</th><th>t(落差の割合)</th>'
            '<th>平面積</th><th class="note">本/100m²(許容)</th><th class="note">植生</th>'
            '<th class="note">地表</th></tr></thead><tbody>%s</tbody></table></div>' % rows)


def slope_planting_table(d, dem):
    sp = scatter_slope(d, dem)
    rows = ""
    for lay in d.get("slopePlanting", []):
        hh, tr = _size_cell(lay)
        rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td>"
                 "<td class='note'>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                 % (lay["band"], lay["layer"], lay.get("role", ""), lay["n"],
                    lay.get("placement", ""), _parts_cell(lay), hh, inline(lay.get("_", ""))))
    return ('<div class="tw"><table><thead><tr><th>帯</th><th>層</th><th>役</th><th>本</th>'
            '<th>置き方</th><th class="note">部材</th><th>樹高</th>'
            '<th class="note">注記</th></tr></thead><tbody>%s</tbody></table></div>' % rows)


def _pending_state(txt):
    """`_pending` の1項が**いまどの状態か**を、書き出しの語から機械で読む。
    → (並び順, 状態, 誰の番か)。⛔ 人が別表を持たない(二重の台帳を作らない)。"""
    head = txt[:60]
    who = ""
    for k, w in (("庭方", "庭方(edo-niwashi)"), ("考証方", "考証方(edo-kosho)"),
                 ("検図", "検図方(edo-kenzu)"), ("在庫方", "在庫方(edo-zaiko)"),
                 ("部材方", "部材方(edo-buzai)"), ("実装", "実装(edo-toryo)"),
                 ("ユーザー裁定", "ユーザー")):
        if k in head:
            who = w
            break
    # ⚠ **語の順が意味を決める。**「現物確認が未了」は宿題であって判断待ちではないので、
    #   `未了` / `未確認` を `確認待ち` より先に見る(⛔ 素の「確認」で拾わない)。
    for key, (rank, st) in (("差し戻し", (0, "差し戻し中")), ("裁定待ち", (0, "裁定待ち")),
                            ("未決", (0, "未決")),
                            ("未了", (1, "未了")), ("未確認", (1, "未確認")),
                            ("未実施", (1, "未実施")), ("未処理", (1, "未処理")),
                            ("検算待ち", (1, "検算待ち")), ("宿題", (1, "宿題")),
                            ("確認待ち", (0, "確認待ち")), ("へ確認", (0, "確認待ち")),
                            ("記録", (2, "記録")), ("決着", (3, "決着"))):
        if key in head:
            return (rank, st, who)
    return (1, "宿題", who)


def pending_table(d):
    """⭐ **「未解決」の章を `_pending` から自動で組む**(2026-09-02 検図 低9・中4)。

    ⛔ **散文で書き写さない。**従前は `kosho.md` に手で書いた散文があり、
      **49項目のうち図に出るのは1項目だけ**だった(今回新設した5項目は図を読む人に見えない)。
      おまけに散文が図版番号を直書きしていて3件がずれた。
    ⭕ 正典は `_pending` の1本だけ。状態(未決/宿題/記録/決着)は書き出しの語から読む。"""
    pd = d.get("_pending") or {}
    if not pd:
        return ""
    rows = {0: [], 1: [], 2: [], 3: []}
    for key, v in pd.items():
        txt = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        rank, st, who = _pending_state(txt)
        rows[rank].append((key, st, who, txt))
    HEAD = {0: ("いま判断を待っている", "var(--shu)",
                "⛔ <b>この版で埋まっていない意匠の判断。</b>指図方は数値を作らない — "
                "決めるのは名指しした役(庭方・考証方・ユーザー)。"),
            1: ("宿題(調べ・検算・実装の段取り)", "#7a5c3a",
                "⚠ <b>判断は要らないが、まだ済んでいない。</b>史料の実見・目録の焼き直し・"
                "実装側の起票など。"),
            2: ("記録(この版で分かったこと・将来の申し送り)", "#5f7a4e",
                "⭕ この版の合否は止めないが、次に触る人が知らないと踏む事柄。"),
            3: ("決着(経緯は git log。⛔ 蒸し返さない)", "var(--take)",
                "⭕ 決まった項。<b>何が決まったか</b>だけを残し、撤回した案は書かない(規則4)。")}
    out = []
    n_open = len(rows[0])
    out.append("<p class='cap'>⛔ <b>正典は <code>_pending</code>(設計値ファイル)の1本。</b>"
               "この章は生成器がそこから組む — <b>散文で書き写さない</b>"
               "(2026-09-02 検図 低9: 49項目のうち図に出るのが1項目だけで、"
               "新設した5項目は<b>図を読む人に見えなかった</b>)。"
               "いま<b>判断を待っている項が %d 件</b>。</p>" % n_open)
    for rank in (0, 1, 2, 3):
        if not rows[rank]:
            continue
        title, col, lede = HEAD[rank]
        out.append('<h3 style="color:%s">%s — %d 件</h3><p class="cap">%s</p>'
                   % (col, title, len(rows[rank]), lede))
        tr = ""
        for key, st, who, txt in rows[rank]:
            tr += ("<tr><td><code>%s</code></td><td><b>%s</b></td><td>%s</td>"
                   "<td class='note'>%s</td></tr>"
                   % (key, st, who or "—", inline(txt)))
        out.append('<div class="tw"><table><thead><tr><th>キー</th><th>状態</th>'
                   "<th>誰の番か</th><th class='note'>中身</th></tr></thead>"
                   "<tbody>%s</tbody></table></div>" % tr)
    return "".join(out)


def plant_pending_table(d):
    out = []
    for key, v in d.get("plantPending", {}).items():
        out.append("<h3>穴 — %s</h3><p class='cap'>%s<br><b>どこ</b>: %s<br><b>なぜ埋まらない</b>: %s</p>"
                   % (inline(v["what"]), "", inline(v["where"]), inline(v["why"])))
        rows = ""
        for pn in v["plans"]:
            rows += ("<tr><td><b>%s</b> %s</td><td class='note'>%s</td><td class='note'>%s</td>"
                     "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                     % (pn["id"], inline(pn["title"]), inline(pn["look"]), inline(pn["cost"]),
                        inline(pn["rule"]), inline(pn["spread"])))
        out.append('<div class="tw"><table><thead><tr><th>案</th><th class="note">①見え方の違い</th>'
                   '<th class="note">②作る手間</th><th class="note">③在庫の規約に触れるか</th>'
                   '<th class="note">④他邸への波及</th></tr></thead><tbody>%s</tbody></table></div>'
                   % rows)
        out.append("<p class='cap'>⛔ <b>指図方は選ばない。</b>%s</p>" % inline(v["_recommend"]))
    return "".join(out)


def plant_budget(d, dem):
    """置く物の総数と三角数。**在庫の木は 1 本 1 万〜2 万三角**なので目に見えるコスト。"""
    n = tri = 0
    for pl in d.get("planting", []):
        for pt in pl.get("parts", []):
            g = part_geom(pt)
            if g:
                n += pt["n"]
                tri += g[2] * pt["n"]
    for lay in d.get("slopePlanting", []):
        for pt in lay.get("parts", []):
            g = part_geom(pt)
            if g:
                n += pt["n"]
                tri += g[2] * pt["n"]
    return n, tri


# ---------------------------------------------------------------- 組み立て
# 図版の採番の台帳 — **題 → (番, アンカー)**。⛔ 本文へ番号を直書きしない(L143 の禁)。
_PLATES = {}


def plate(h, num, title, meta=""):
    """図版の見出し。⭐ **採番を台帳に控え、見出しにアンカーを打つ**(2026-09-02 検図 中4)。

    ⛔ **副題(meta)を素で流し込まない** — `**強調**` が生のまま出る(庭方 2026-09-02 低6)。
    ⭐ 本文からこの図を指すときは **`{{図:題}}`** と書く。番号は生成器が差し込む
      (⛔ 「其廿三」と直書きすると図版を1面足した日に別の図を指す — 実際に3件ずれた)。"""
    aid = "pl%d" % (len(_PLATES) + 1)
    if title:
        _PLATES[title] = (num, aid)
    h.append('<div class="plate" id="%s"><div class="phead"><h2>%s　%s</h2>%s</div>'
             % (aid, num, inline(title),
                ('<span class="meta">%s</span>' % inline(meta)) if meta else ""))


_PLREF = re.compile(r"\{\{図:([^}]+)\}\}")


def plate_refs(html):
    """本文の **`{{図:題}}`** を、`plate()` が採った番号への**リンク**へ差し替える。
    ⛔ 見つからない題はそのまま残し、`plate_ref_check` が鳴らす(黙って消さない)。"""
    def sub(m):
        t = m.group(1)
        if t not in _PLATES:
            return m.group(0)
        num, aid = _PLATES[t]
        return '<a href="#%s"><b>%s</b>「%s」</a>' % (aid, num, inline(t))
    return _PLREF.sub(sub, html)


def plate_ref_check(d):
    """⭐ **図版番号の直書きを止める検査**(2026-09-02 検図 中4。3件が別の図を指していた)。

    ① `kosho.md` と `_pending` に **其◯ の直書き**が残っていないか
    ② `{{図:題}}` の題が**実在する図版**か(採番の台帳と突き合わせる)
    ⛔ 生成器自身が L143 で「番号を本文へ直書きしない」と禁じている形なので、
      禁を検査にする(散文の禁は破れる)。"""
    bad = []
    KAN_RE = re.compile(r"其[一二三四五六七八九十廿卅]+")
    srcs = [("kosho.md", open(MD, encoding="utf-8").read())]
    for k, v in (d.get("_pending") or {}).items():
        srcs.append(("`_pending.%s`" % k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)))
    for nm, txt in srcs:
        for m in KAN_RE.finditer(txt):
            bad.append("%s に図版番号の直書き「%s」が残っている — **`{{図:題}}`** で書くこと"
                       "(図版を1面足すと番号が全部ずれる。2026-09-02 に3件が別の図を指していた)"
                       % (nm, m.group(0)))
        for m in _PLREF.finditer(txt):
            if m.group(1) not in _PLATES:
                bad.append("%s の図版参照 `{{図:%s}}` に当たる図版が無い — "
                           "題は `plate()` の題と**一字一句同じ**にすること" % (nm, m.group(1)))
    return bad


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
        """section_svg / 実装の DesignY と同じ規則
        (**築山** → **御泉水** → 段 → 土留めの有無 → 法面)。
        ⚠ 2026-09-01 検図(致命4): 築山と池がこの表に入っておらず、
          断面図(section_svg)の面と内訳表の面が食い違っていた。"""
        gq0 = (at, w) if sec["axis"] == "u" else (w, at)
        for tk in d.get("tsukiyama", []):
            ty = _tk_y(d, tk, gq0[0], gq0[1],
                       lambda a, b: _nat_uv(_terr_json(), round(a), round(b)))
            if ty is not None:
                base = None
                for a, b, y in segs:
                    if a - 1e-6 <= w <= b + 1e-6:
                        base = y
                return (ty if base is None else max(ty, base)) - _pond_depth(d, *gq0)
        for a, b, y in segs:
            if a - 1e-6 <= w <= b + 1e-6:
                return y - _pond_depth(d, *gq0)
        nz = nat_at(w)
        if nz is None:
            return None
        g = gq0
        dT, yT, cp = 1e9, None, None
        for t in d["terraces"]:
            cu = max(t["u0"], min(g[0], t["u1"]))
            cv = max(t["v0"], min(g[1], t["v1"]))
            dd = math.hypot(g[0] - cu, g[1] - cv) * K
            if dd < dT:
                dT, yT, cp = dd, t["y"], (cu, cv)
        if yT is None:
            return nz - _pond_depth(d, *g)
        for wl in d["terraceWalls"]:
            if _dseg(cp, tuple(wl["a"]), tuple(wl["b"])) <= WALLNEAR:
                return nz - _pond_depth(d, *g)
        cpn = nat_at(cp[1] if sec["axis"] == "u" else cp[0])
        if cpn is None or yT - cpn <= 0.05:
            return nz - _pond_depth(d, *g)
        if dT > CAP or not _daylights(cp, g, yT, nat_at, BFILL, CAP, K):
            return nz - _pond_depth(d, *g)
        slack = dT / max(0.5, BFILL if yT > nz else BCUT)
        return max(yT - slack, min(nz, yT + slack)) - _pond_depth(d, *g)

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


_PONDR = {}


def _pond_depth(d, u, v):
    """**御泉水の掘り下げ**[m]。汀線の内は **`floorY` 一定**(垂直掘り・底ならし)。

    ⭐ **B案(2026-09-01 ユーザー裁定の変更)で水を張る池に戻った。**
      `sensui.baker.verticalWalls = true` / `levelFloor = true` なので、
      掘削後の池底は **`sensui.pond.floorY` の一枚**になる。
      掘り下げ = **汀の設計地盤(主庭が載る段の面)− `floorY`**。
    ⛔ A案の『皿(汀で0・芯で `dig`)』は撤回した。
    ⛔ ここで数を作らない — 正典は `sensui.pond.floorY` と段の面。
    ⚠ 澪筋(`sensui.miosuji`)の 0.25m はこの土量に**含めない**(掘削の後で庭師が掻く筋で、
      `Recarve` のたびに打ち直す。土量としては誤差)。"""
    ks = d.get("sensui")
    if not ks:
        return 0.0
    po = [tuple(p) for p in ks["pond"]["outline"]]
    if not _pip_world((u, v), po):
        return 0.0
    fl = float(ks["pond"]["floorY"])
    base = None
    for t in d["terraces"]:
        if t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9:
            base = t["y"]
    if base is None:
        base = _nat_uv(_terr_json(), round(u), round(v))
    if base is None:
        return 0.0
    return max(0.0, base - fl)


def _pond_water(d, u, v):
    """その点が**水面の下**なら `waterY`、そうでなければ None。断面図と面図が使う。"""
    ks = d.get("sensui")
    if not ks:
        return None
    po = [tuple(p) for p in ks["pond"]["outline"]]
    return float(ks["pond"]["waterY"]) if _pip_world((u, v), po) else None


def _terr_at(d, u, v):
    """その点が**どの段の勘定に入るか**。⭐ 築山と御泉水は段ではないが、
    土量表で『段の外(法面・帯)』に紛れると図に現れないので独立の行にする
    (2026-09-01 検図 改善②)。"""
    for tk in d.get("tsukiyama", []):
        if _tk_t(tk, u, v) is not None:
            return "築山"
    if _pond_depth(d, u, v) > 0.0:
        return "御泉水(掘削)"
    for t in d["terraces"]:
        if t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9:
            return TERR_JA.get(t["name"], t["name"])
    return None


def _nat_uv(terr, u, v):
    i = int(round((u - terr["u0"]) / terr["step"])); j = int(round((v - terr["v0"]) / terr["step"]))
    if i < 0 or j < 0 or i >= terr["nu"] or j >= terr["nv"]: return None
    return terr["h"][j][i]


def _design_at_uv(d, u, v, terr):
    """面図と同じ規則(**築山** → **御泉水** → 段 → 土留めの有無 → 法面)。断面の 2次元版。"""
    y = _design_at_uv0(d, u, v, terr)
    if y is None:
        return None
    return y - _pond_depth(d, u, v)


def _design_at_uv0(d, u, v, terr):
    K = d["const"]["ken"]
    for tk in d.get("tsukiyama", []):
        ty = _tk_y(d, tk, u, v, lambda a, b: _nat_uv(terr, round(a), round(b)))
        if ty is not None:
            for t in d["terraces"]:
                if t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9:
                    return max(ty, t["y"])
            return ty
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
ROUTE_COL = {"omote": "#a8452c", "yaku": "#3d6ea8", "katte": "#7a5c3a", "oku": "#5f7a4e",
             "niwa": "#7a6a3d"}   # 園路(庭道)。⚠ 動線とは別の物なので色を分ける
_BDEM = {}
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

    def gpoly(pts, fill, op=1.0, stroke="none", sw=0.0):
        return ('<polygon points="%s" fill="%s" opacity="%.2f" stroke="%s" stroke-width="%.1f"/>'
                % (" ".join("%.1f,%.1f" % gpt(a, b) for (a, b) in pts), fill, op, stroke, sw))

    GLB = LabelSet()                      # ⛔ ラベルを団子にしない
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
    # 植栽 — **指図の規則どおりに散らした標本**を、樹冠の実寸で描く。
    # ⚠ 位置は設計値ではない(規則・本数・部材・退避が設計値)。円の大きさは部材の実測値。
    PLC = {"高木": "#3B5A3C", "中木": "#5E7A4E", "低木": "#8FA36B", "下草": "#A8B98A"}
    gs = scatter_gardens(d)
    for pl in d.get("planting", []):
        col = PLC.get(pl.get("role", ""), "#5E7A4E")
        for (uu, vv, pt) in gs.get((pl["zone"], pl["layer"]), []):
            gm = part_geom(pt)
            if gm is None:
                continue
            x, y = gpt(uu, vv)
            g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.34"/>'
                     % (x, y, pr.L(gm[0] / 2.0), col))
            g.append('<circle cx="%.1f" cy="%.1f" r="1.4" fill="%s"/>' % (x, y, col))

    # ⭐ **庭の本体**(御泉水・築山・護岸・澪筋・中島)。
    #   ⛔ 2026-09-01 の庭方の指摘1「庭園図と名乗る唯一の平面に庭の本体が無い」
    #   — 主庭が『緑地に赤い点とラベル』としてしか出ていなかった。
    draw_tsukiyama(d, g, gpt, gpoly, GLB)
    draw_sensui(d, g, gpt, pr, gpoly, GLB)
    draw_mizu(d, g, gpt, pr, gpoly, GLB)
    # 点景(露地の飛石道・中門・蹲踞・灯籠・石組・垣)
    TK = {"露地(飛石道)": "var(--michi)", "建仁寺垣": "var(--take)"}
    for t in d.get("tenkei", []):
        # ⛔ **画面の外の点景を描かない**(2026-09-01 庭方の指摘2 — 稲荷の鳥居が
        #   viewBox の外に描かれていて、図の上では『無い』のと同じだった)
        qs = t.get("pts") or ([t["a"], t["b"]] if "a" in t else [[t["u"], t["v"]]])
        if not any(u0 <= q[0] <= u1 and v0 <= q[1] <= v1 for q in qs):
            continue
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
            GLB.add(x, y, t["kind"], dx=5.0, dy=4.0)
    for vp in d.get("viewpoints", []):
        if not (u0 <= vp["u"] <= u1 and v0 <= vp["v"] <= v1):
            continue
        x, y = gpt(vp["u"], vp["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--paper)" stroke="var(--shu)" '
                 'stroke-width="2.2"/>' % (x, y))
        g.append(T(x, y + 4, vp["name"], "rmS", "middle", 10.0, "var(--shu)"))
        GLB.add(x, y, vp["label"], dx=9.0, dy=-7.0)
    g.extend(GLB.out())
    g.append(T(4, 16, "西の帯は露地・芝野・築山。**池は置かない**(裁定の理由は考証の章)", "anS", "start"))
    g.append(T(pr.W - 4, 16, "北 ↑　左=西(溜池・崖)", "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


def garden_east_svg(d):
    """**庭園図(東庭・梅林・稲荷)。**⭐ 2026-09-01 の庭方の指摘2 —
    「東の庭に平面図が1枚も無い」(`G_OkuNiwa` / 梅林 `G_OkuNiwaSE` / `G_Inari`)。
    ⛔ **図の無い庭は検分できない**(庭方は合法域マップを自作して代用した)。
    ⚠ 庭園図(西庭)は見出しどおり西だけを写す図で、東は載らない。"""
    gr = RGrid(d)
    K = d["const"]["ken"]
    NAMES = ("G_OkuNiwa", "G_OkuNiwaSE", "G_Inari", "G_Ume_Hiroba")
    gz = [g for g in d["gardens"] if g["name"] in NAMES]
    if not gz:
        return ""
    u0 = min(g["u0"] for g in gz) - 3; u1 = max(g["u1"] for g in gz) + 3
    v0 = min(g["v0"] for g in gz) - 4; v1 = max(g["v1"] for g in gz) + 4
    corners = [gr.W(a, b) for a in (u0, u1) for b in (v0, v1)]
    pr = Proj(min(q[0] for q in corners) - 4, max(q[0] for q in corners) + 4,
              min(q[1] for q in corners) - 4, max(q[1] for q in corners) + 4,
              W=940.0, top=26.0, bottom=40.0)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 庭園図(東庭・梅林・稲荷)")
    LBE = LabelSet(step=10.0)

    def P(u, v):
        q = gr.W(u, v)
        return pr.X(q[0]), pr.Y(q[1])

    def poly(pts, fill, op=1.0, stroke="none", sw=0.0):
        return ('<polygon points="%s" fill="%s" opacity="%.2f" stroke="%s" stroke-width="%.1f"/>'
                % (" ".join("%.1f,%.1f" % P(a, b) for (a, b) in pts), fill, op, stroke, sw))

    def rect(z, fill, op=1.0, stroke="none", sw=0.0):
        return poly([(z["u0"], z["v0"]), (z["u1"], z["v0"]),
                     (z["u1"], z["v1"]), (z["u0"], z["v1"])], fill, op, stroke, sw)

    def vis(z):
        return not (z["u1"] < u0 or z["u0"] > u1 or z["v1"] < v0 or z["v0"] > v1)

    for t in d["terraces"]:
        if vis(t):
            g.append(rect(t, "var(--pl-main)", 0.45))
    for n in d["gardens"]:
        if not vis(n):
            continue
        pts = [tuple(p) for p in n["poly"]] if n.get("poly") else \
              [(n["u0"], n["v0"]), (n["u1"], n["v0"]), (n["u1"], n["v1"]), (n["u0"], n["v1"])]
        col = "var(--shirasu)" if n.get("kind") == "shirasu" else "var(--niwa)"
        g.append(poly(pts, col, 0.9, "var(--ink-lo)", 1.0))
        x, y = P((n["u0"] + n["u1"]) / 2.0, (n["v0"] + n["v1"]) / 2.0)
        g.append(T(x, y + 4, n["label"], "rmS", "middle",
                   fit(n["label"], pr.L((n["u1"] - n["u0"]) * K), 12.0)))
    for m in d["munes"] + d["service"]:
        if not vis(m):
            continue
        g.append(rect(m, "var(--ink-mid)", 0.85, "var(--ink)", 0.7))
        x, y = P((m["u0"] + m["u1"]) / 2.0, (m["v0"] + m["v1"]) / 2.0)
        lb2 = MUNE_JA.get(m["name"], m.get("label", m["name"]))
        g.append(T(x, y + 4, lb2, "rmS", "middle",
                   fit(lb2, pr.L((m["u1"] - m["u0"]) * K), 11.0)))
    # --- 中仕切(板塀・庭木戸)。⭐ **根石が付く列**を太く描く
    ne = (d.get("nakajikiriRule") or {}).get("neishi") or {}
    for nj in d.get("nakajikiri", []):
        a, b = tuple(nj["a"]), tuple(nj["b"])
        if not any(u0 <= q[0] <= u1 and v0 <= q[1] <= v1 for q in (a, b)):
            continue
        has = nj.get("kind") in (ne.get("applyKind") or [])
        xa, ya = P(*a); xb, yb = P(*b)
        g.append(LN(xa, ya, xb, yb, "#7a6a55" if has else "var(--shu)",
                    3.4 if has else 2.6, None, 0.95, "butt"))
    for w in d.get("wells", []):
        if not (u0 <= w["u"] <= u1 and v0 <= w["v"] <= v1):
            continue
        x, y = P(w["u"], w["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="var(--paper)" stroke="var(--ink)" '
                 'stroke-width="1.4"/>' % (x, y))
        LBE.add(x, y, "井戸 " + w["name"], dx=6.0, dy=4.0)
    for r in d["routes"]:
        pts = [tuple(p) for p in r["pts"]]
        if not any(u0 <= q[0] <= u1 and v0 <= q[1] <= v1 for q in pts):
            continue
        g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.8" '
                 'stroke-linejoin="round" stroke-linecap="round"%s opacity="0.9"/>'
                 % (" ".join("%.1f,%.1f" % P(a, b) for (a, b) in pts),
                    ROUTE_COL.get(r["kind"], "var(--ink)"),
                    ' stroke-dasharray="7 4"' if r.get("kind") == "niwa" else ""))
    PLC = {"高木": "#3B5A3C", "中木": "#5E7A4E", "低木": "#8FA36B", "下草": "#A8B98A"}
    gs = scatter_gardens(d)
    for pl in d.get("planting", []):
        col = PLC.get(pl.get("role", ""), "#5E7A4E")
        for (uu, vv, pt) in gs.get((pl["zone"], pl["layer"]), []):
            if not (u0 <= uu <= u1 and v0 <= vv <= v1):
                continue
            x, y = P(uu, vv)
            gm = part_geom(pt)
            if gm is not None:
                g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.34"/>'
                         % (x, y, pr.L(gm[0] / 2.0), col))
            else:
                g.append('<circle cx="%.1f" cy="%.1f" r="7" fill="none" stroke="%s" '
                         'stroke-width="1.0" stroke-dasharray="3 3" opacity="0.7"/>' % (x, y, col))
            g.append('<circle cx="%.1f" cy="%.1f" r="1.6" fill="%s"/>' % (x, y, col))
    for t in d.get("tenkei", []):
        qs = t.get("pts") or ([t["a"], t["b"]] if "a" in t else [[t["u"], t["v"]]])
        if not any(u0 <= q[0] <= u1 and v0 <= q[1] <= v1 for q in qs):
            continue
        if "pts" in t:
            g.append('<polyline points="%s" fill="none" stroke="var(--michi)" '
                     'stroke-width="2.4" stroke-dasharray="3 4" stroke-linecap="round"/>'
                     % " ".join("%.1f,%.1f" % P(q[0], q[1]) for q in t["pts"]))
        elif "a" in t:
            xa, ya = P(*t["a"]); xb, yb = P(*t["b"])
            g.append(LN(xa, ya, xb, yb, "var(--take)", 2.2, "6 3"))
        else:
            x, y = P(t["u"], t["v"])
            g.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--shu)"/>' % (x, y))
            LBE.add(x, y, t["kind"].split("(")[0], dx=5.0, dy=4.0)
    for k in d.get("kaidans", []):
        if "pos" not in k or not (u0 <= k["pos"][0] <= u1 and v0 <= k["pos"][1] <= v1):
            continue
        x, y = P(k["pos"][0], k["pos"][1])
        g.append('<rect x="%.1f" y="%.1f" width="9" height="9" fill="none" '
                 'stroke="var(--shu)" stroke-width="1.6"/>' % (x - 4.5, y - 4.5))
        LBE.add(x, y, "%s(%d段)" % (k["name"], k["steps"]), dx=6.0, dy=-4.0)
    for vp in d.get("viewpoints", []):
        if not (u0 <= vp["u"] <= u1 and v0 <= vp["v"] <= v1):
            continue
        x, y = P(vp["u"], vp["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--paper)" stroke="var(--shu)" '
                 'stroke-width="2.2"/>' % (x, y))
        g.append(T(x, y + 4, vp["name"], "rmS", "middle", 10.0, "var(--shu)"))
        LBE.add(x, y, vp["label"], dx=9.0, dy=-7.0)
    draw_mizu(d, g, P, pr, poly, LBE)
    g.extend(LBE.out())
    g.append(T(4, 16, "奥庭 → 梅林 → 稲荷の杜。北 ↑　左=西", "anS", "start"))
    g.append(T(pr.W - 4, 16, "太い茶の線=根石の付く板塀", "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


def _base_dem():
    """造成前の**広い**地盤(区画の外まで)。借景の検算に要る。"""
    if "h" not in _BDEM:
        _BDEM.update(json.load(open(os.path.join(DOC, "base_dem.json"), encoding="utf-8")))
    return _BDEM


def _bdem_at(x, z):
    b = _base_dem()
    i = int(round((x - b["x0"]) / b["step"]))
    j = int(round((z - b["z0"]) / b["step"]))
    if i < 0 or j < 0 or i >= b["nx"] or j >= b["nz"]:
        return None
    return b["h"][j][i]


def tameike_water_y():
    """**溜池の水面。**⛔ 松平の指図に写さない — 正典は外堀の指図
    (`sotobori_sashizu.json` の `system.steps`「溜池」)。借景の検算のためだけに読む。"""
    o = json.load(open(os.path.join(DOC, "sotobori_sashizu.json"), encoding="utf-8"))
    for st in o["system"]["steps"]:
        if st["name"] == "溜池":
            return float(st["waterY"])
    return None


def _ground_uv(d, u, v, terr, dem):
    """設計の地盤(段 → 築山の盛土 → 法面 → 現況)。区画の外は造成前の広い DEM。"""
    y = _design_at_uv(d, u, v, terr)
    for tk in d.get("tsukiyama", []):
        t = _tk_y(d, tk, u, v, lambda a, b: _nat_uv(terr, round(a), round(b)))
        if t is not None and (y is None or t > y):
            y = t
    if y is None:
        gr = RGrid(d)
        y = _bdem_at(*gr.W(u, v))
    return y


def draw_tsukiyama(d, g, P, poly, lb=None):
    """**築山**を等高の輪で描く。⚠ 主庭の平面・庭園図の両方が呼ぶ(⛔ 図ごとに書き写さない)。"""
    for tk in d.get("tsukiyama", []):
        for t in (1.0, 0.75, 0.5, 0.25):
            ring = []
            for k in range(72):
                a = k / 72.0 * 6.2832
                R = _tk_ray(tk, a)
                if R is None:
                    continue
                ring.append((tk["u"] + math.cos(a) * R * t, tk["v"] + math.sin(a) * R * t))
            if ring:
                g.append(poly(ring, "#C8BE96", 0.30 + 0.14 * (1.0 - t), "#8a7f52", 1.0))
        x, y = P(tk["u"], tk["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="3" fill="var(--shu)"/>' % (x, y))
        if lb is not None:
            lb.add(x, y, "築山の頂 %.1fm" % tk["y"])


def draw_sensui(d, g, P, pr, poly, lb=None, gogan=True):
    """**御泉水・石組護岸・中島・澪筋・遣水・台地端の滝**を描く。

    ⚠ 主庭の平面(大縮尺)と庭園図(西庭)の**両方が呼ぶ** — 2026-09-01 の庭方の指摘1
    「庭園図と名乗る唯一の平面に庭の本体が無い」。
    ⛔ 図ごとに作画を書き写さない(片方だけ古くなる)。"""
    ks = d.get("sensui")
    if not ks:
        return
    po = [tuple(p) for p in ks["pond"]["outline"]]
    g.append(poly(po, "#9fbfd0", 1.0, "#3f6a80", 1.6))      # ⭐ 水面(⛔ 砂利の州ではない)
    # ⭐ **護岸石を実寸で並べる**(⛔ 汀線を太い線で描くだけでは『石組護岸』が図に出ない)。
    #   個数と芯々は `gogan_bands` の従属値。半径は天端石の長軸の半分。
    if gogan:
        n = len(po)
        for b in gogan_bands(d):
            if b["pitch"] <= 0:
                continue
            rr = pr.L((b["long"][0] + b["long"][1]) / 4.0)
            bd = [x for x in ks["gogan"]["bands"] if x["where"] == b["where"]][0]
            i, j = int(bd["from"]) - 1, int(bd["to"]) - 1
            walk = []
            while i != j:
                i2 = (i + 1) % n
                walk.append((po[i], po[i2]))
                i = i2
            acc = 0.0
            for (a2, b2) in walk:
                L = math.hypot(b2[0] - a2[0], b2[1] - a2[1]) * d["const"]["ken"]
                while acc < L:
                    t = acc / L
                    x, y = P(a2[0] + (b2[0] - a2[0]) * t, a2[1] + (b2[1] - a2[1]) * t)
                    g.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#8f8a6e" '
                             'opacity="0.9"/>' % (x, y, max(1.0, rr)))
                    acc += b["pitch"]
                acc -= L
    for i, (a, b) in enumerate(po, 1):
        x, y = P(a, b)
        g.append('<circle cx="%.1f" cy="%.1f" r="1.6" fill="#3f6a80"/>' % (x, y))
        mk = ks["pond"].get("marks", {}).get(str(i))
        if mk and lb is not None:
            lb.add(x, y, "%d %s" % (i, mk))
    # ⭐ 中島(磯島)— **掘った後に隆起させる**ので水面の上に載る
    isl = [tuple(p) for p in ks["island"]["outline"]]
    g.append(poly(isl, "#BFB79A", 1.0, "#6b6446", 1.2))
    x, y = P(*[sum(c) / len(isl) for c in zip(*isl)])
    if lb is not None:
        lb.add(x, y, "中島(磯島・松1)", anchor="middle", dx=0.0, dy=4.0)
    # ⭐ 池底の澪筋 — **水の下**なので破線と薄い帯で描く
    na = [tuple(p) for p in ks["miosuji"]["pts"]]
    wa = ks["miosuji"].get("wAt")
    sc = float(ks["miosuji"].get("wScale") or 1.0)
    if wa and len(wa) == len(na):
        KEN = d["const"]["ken"]
        lf, rt = [], []
        for i, (a, b) in enumerate(na):
            j0, j1 = max(0, i - 1), min(len(na) - 1, i + 1)
            dx = na[j1][0] - na[j0][0]
            dy = na[j1][1] - na[j0][1]
            L = math.hypot(dx, dy) or 1.0
            hw = (wa[i] * sc / KEN) / 2.0
            lf.append((a - dy / L * hw, b + dx / L * hw))
            rt.append((a + dy / L * hw, b - dx / L * hw))
        g.append(poly(lf + rt[::-1], "#7ba2b8", 0.85, "#3f6a80", 0.8))
    g.append('<polyline points="%s" fill="none" stroke="#2f5468" stroke-width="1.2" '
             'stroke-dasharray="2 4"/>' % " ".join("%.1f,%.1f" % P(a, b) for (a, b) in na))
    x, y = P((na[0][0] + na[-1][0]) / 2, (na[0][1] + na[-1][1]) / 2)
    if lb is not None:
        lb.add(x, y, "池底の澪筋", anchor="end", dx=-4.0, dy=0.0)


def draw_mizu(d, g, P, pr, poly, lb=None):
    """**水の系**(樋・遣水・台地端の滝・水尻)を平面へ描く。⛔ 図ごとに書き写さない。"""
    mz = d.get("mizu")
    if not mz:
        return
    nod = {n["id"]: n for n in mz["nodes"]}
    # 樋(木樋・石樋・暗渠)
    for t in mz.get("toi", []):
        q = _toi_pts(d, t)                      # ⭐ 折れ線(2026-09-02)
        if not q or len(q) < 2:
            continue
        xy = [P(a, b) for (a, b) in q]
        g.append('<polyline points="%s" fill="none" stroke="#3f6a80" stroke-width="1.2" '
                 'stroke-dasharray="5 4" opacity="0.9"/>'
                 % " ".join("%.1f,%.1f" % p for p in xy))
        if lb is not None:
            mx, my = xy[len(xy) // 2]
            lb.add(mx, my, t["name"].replace("MZ_", ""), anchor="middle", dy=-3.0)
    # 遣水
    ks = d.get("sensui") or {}
    ym = ks.get("yarimizu")
    if ym:
        pts = [tuple(p) for p in ym["pts"]]
        g.append('<polyline points="%s" fill="none" stroke="#3f6a80" stroke-width="2.2"/>'
                 % " ".join("%.1f,%.1f" % P(a, b) for (a, b) in pts))
        if lb is not None:
            x, y = P(*pts[len(pts) // 2])
            lb.add(x, y, "遣水(野筋の底)", anchor="middle", dy=-4.0)
    # 台地端の滝
    td = mz.get("takiDaichi")
    if td:
        pts = [(t["u"], t["v"]) for t in td["tiers"]]
        for k, (a, b) in enumerate(pts, 1):
            x, y = P(a, b)
            g.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--shu)"/>' % (x, y))
            if lb is not None:
                lb.add(x, y, "%s %.2fm" % (td["tiers"][k - 1]["label"],
                                           td["tiers"][k - 1]["topY"]))
    # 節点
    for n in mz["nodes"]:
        if n.get("u") is None:
            continue
        x, y = P(n["u"], n["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="2.0" fill="none" stroke="#3f6a80" '
                 'stroke-width="1.2"/>' % (x, y))
        if lb is not None:
            lb.add(x, y, n["label"])


def _mizu_chain(d):
    """**水の系を上流から下流へ一列に並べる。**→ [(累加距離[m], 水面[m], 名, 種別)]

    ⛔ 距離も勾配も指図に書かない — ここで測る従属値。
    ⭐ 末端は**区画の南西の出口 P4**まで引く。『滝の末は赤坂の溜池へ落ち』(貞享4)が
      設計として成立していることを、図の上で最後まで追えるようにするため。"""
    mz = d.get("mizu")
    ks = d.get("sensui")
    if not mz or not ks:
        return []
    K = d["const"]["ken"]
    gr = RGrid(d)
    nod = {n["id"]: n for n in mz["nodes"]}
    po = [tuple(p) for p in ks["pond"]["outline"]]

    def uv(i):
        n = nod[i]
        if n.get("u") is not None:
            return (n["u"], n["v"])
        if n.get("shore"):
            return po[int(n["shore"]) - 1]
        return None

    seq = []
    for i, lab, y, kind in (
            ("MZ1", None, None, "枡"), ("MZ2", None, None, "枡"), ("MZ3", None, None, "枡"),
            ("MZ4", None, None, "岩屋")):
        p = uv(i)
        seq.append((p, nod[i]["label"], float(nod[i]["waterY"]), kind))
    # 落ち口の二段
    p4 = uv("MZ4")
    y = float(ks["iwaya"]["inletY"])
    for k, dr in enumerate(ks["iwaya"]["drops"], 1):
        y -= float(dr)
        seq.append((p4, "落ち口 %d段目(−%.2fm)" % (k, dr), y, "落ち口"))
    # 池(汀線 #14 → #21 の澪筋に沿った距離)
    ms = [tuple(p) for p in ks["miosuji"]["pts"]]
    for k, p in enumerate(ms[1:], 1):
        seq.append((p, "御泉水" if k == len(ms) - 1 else None,
                    float(ks["pond"]["waterY"]), "池"))
    seq.append((uv("MZ7"), nod["MZ7"]["label"], float(nod["MZ7"]["weirY"]), "堰"))
    # 暗渠 — ⭐ **末は一の段の滝壺へ吐く**(2026-09-01 第3次。⛔ 遣水へは合流しない)
    ak = [t for t in mz["toi"] if t["name"] == "MZ_Ankyo"][0]
    akp = _toi_pts(d, ak) or []
    for q in akp[1:-1]:
        seq.append((q, None, None, "暗渠"))     # 折れ点(標高は補間)
    seq.append((akp[-1], "暗渠の末(一の段の滝壺へ吐く)", float(ak["floorY"][1]), "暗渠"))
    # 台地端の滝 — 本流は**一の段の滝壺**から入るので、一の段の天端は枝(遣水)の側に置く
    for k2, (t, bot, pt) in enumerate(_taki_feet(d)):
        if k2 > 0:
            seq.append(((t["u"], t["v"]), t["label"] + " 天端", float(t["topY"]), "滝"))
        seq.append((pt, ("%s の滝壺" % t["label"]) if k2 == 0 else None, bot, "滝"))
    # 南西の谷 → 区画の南西の出口 P4(この先は区画外の自然の谷)
    out = _mizu_outlet(d)
    if out:
        seq.append(((-29.0, 70.0), "南西の谷(自然の沢・造成しない)", None, "沢"))
        seq.append((out, "区画の南西の出口 P4(この先は区画外の谷を下って溜池の汀へ)",
                    float(nod["MZ15"]["y"]), "溜池"))
    out, acc, prev = [], 0.0, None
    for (p, lab, y, kind) in seq:
        if p is None:
            continue
        w = gr.W(p[0], p[1])
        if prev is not None:
            acc += math.hypot(w[0] - prev[0], w[1] - prev[1])
        prev = w
        out.append((acc, y, lab, kind))
    # 沢の中間点は標高が無いので直線で補間して描く
    for k, (a, y, lab, kind) in enumerate(out):
        if y is None:
            lo = [q for q in out[:k] if q[1] is not None]
            hi = [q for q in out[k + 1:] if q[1] is not None]
            if lo and hi:
                t = (a - lo[-1][0]) / max(1e-6, hi[0][0] - lo[-1][0])
                out[k] = (a, lo[-1][1] + (hi[0][1] - lo[-1][1]) * t, lab, kind)
    return out


def _mizu_branch(d):
    """**枝2の縦断**(落し枡C → 石樋 → 遣水の湧き口 → 石橋 → 落ち口 → 一の段の天端)。

    ⭐ 本流(`_mizu_chain`)は池を通るので、**遣水は別の列**になる。
    ⛔ 一本の線に混ぜない — 2026-09-01 の第2次までは暗渠を遣水へ合流させて一本にしていたが、
      **遣水は池の水面より上を流れる**ので合流は原理的に不可だった(庭方 高2)。
    ⚠ 距離は**取入口からの累加**(本流と同じ原点)で返す — 図で並べて読めるようにするため。"""
    mz, ks = d.get("mizu"), d.get("sensui")
    if not mz or not ks:
        return []
    gr = RGrid(d)
    nod = {n["id"]: n for n in mz["nodes"]}
    # 取入口 → 落し枡C までの距離(本流と共有)
    acc = 0.0
    prev = None
    for i in ("MZ1", "MZ2", "MZ3"):
        w = gr.W(nod[i]["u"], nod[i]["v"])
        if prev is not None:
            acc += math.hypot(w[0] - prev[0], w[1] - prev[1])
        prev = w
    seq = [((nod["MZ3"]["u"], nod["MZ3"]["v"]), nod["MZ3"]["label"],
            float(nod["MZ3"]["waterY"]), "枡")]
    ym = ks.get("yarimizu") or {}
    pts = [tuple(q) for q in ym.get("pts", [])]
    for nm in ym.get("via", []):
        for t in d.get("tenkei", []):
            if t["name"] == nm:
                pts.insert(1, (t["u"], t["v"]))
    wy = ym.get("waterY") or [None, None]
    seq.append(((nod["MZ10"]["u"], nod["MZ10"]["v"]), nod["MZ10"]["label"],
                float(nod["MZ10"]["waterY"]), "遣水"))
    if len(pts) > 2:
        _ib = next((t for t in d.get("tenkei", []) if t["name"] == "T_Ishibashi"), None)
        for q in pts[1:-1]:
            lab = ("石橋" if _ib and abs(q[0] - _ib["u"]) < 1e-6 and abs(q[1] - _ib["v"]) < 1e-6
                   else None)
            seq.append((q, lab, None, "遣水"))
    seq.append(((nod["MZ12"]["u"], nod["MZ12"]["v"]), nod["MZ12"]["label"],
                float(nod["MZ12"]["waterY"]), "遣水"))
    t0 = mz["takiDaichi"]["tiers"][0]
    seq.append(((t0["u"], t0["v"]), t0["label"] + " 天端", float(t0["topY"]), "滝"))
    out, prev = [], None
    for (q, lab, y, kind) in seq:
        w = gr.W(q[0], q[1])
        if prev is not None:
            acc += math.hypot(w[0] - prev[0], w[1] - prev[1])
        prev = w
        out.append((acc, y, lab, kind))
    for k, (a, y, lab, kind) in enumerate(out):
        if y is None:
            lo = [q for q in out[:k] if q[1] is not None]
            hi = [q for q in out[k + 1:] if q[1] is not None]
            if lo and hi:
                t = (a - lo[-1][0]) / max(1e-6, hi[0][0] - lo[-1][0])
                out[k] = (a, lo[-1][1] + (hi[0][1] - lo[-1][1]) * t, lab, kind)
    return out


def _mizu_outlet(d):
    """**余水の出口**(区画の頂点)を (u,v) で返す。⛔ 座標は `polygon` が正典。

    `mizu.nodes.MZ15.parcelPt`(例 `"P4"`)が**どの頂点か**の設計値で、
    座標そのものは `d["polygon"]` から引く(規則10 — 区画の座標を写さない)。"""
    mz = d.get("mizu")
    if not mz:
        return None
    n = [x for x in mz["nodes"] if x.get("parcelPt")]
    if not n:
        return None
    m = re.match(r"P(\d+)$", n[0]["parcelPt"])
    if not m:
        return None
    k = int(m.group(1))
    if k >= len(d["polygon"]):
        return None
    gr = RGrid(d)
    w = d["polygon"][k]
    return gr.L(w[0], w[1])


def mizu_table(d):
    """**水の系**の節点表(勾配・距離は従属値)。⭐ 本流と**枝2(遣水)**の二列。"""
    ch = _mizu_chain(d)
    if not ch:
        return ""
    rows = ""
    prev = None
    for (a, y, lab, kind) in [(None, None, "本流(取入口 → 御泉水 → 水尻 → 暗渠 → 台地端の滝 → 溜池)",
                               "__head__")] + list(ch) \
            + [(None, None, "枝2(落し枡C → 石樋 → 遣水 → 台地端の滝の頭)", "__head__")] \
            + list(_mizu_branch(d)):
        if kind == "__head__":
            rows += "<tr><td colspan='5'><b>%s</b></td></tr>" % lab
            prev = None
            continue
        if lab is None:
            prev = (a, y)
            continue
        gr = ""
        if prev is not None and y is not None and prev[1] is not None:
            dl = a - prev[0]
            dy = prev[1] - y
            if dl > 0.5:
                gr = ("1/%.0f" % (dl / dy)) if dy > 1e-6 else "—"
            elif dy > 1e-6:
                gr = "落差 %.2fm" % dy
        rows += ("<tr><td>%s</td><td>%s</td><td>%.0f m</td><td><b>%s</b></td>"
                 "<td class='note'>%s</td></tr>"
                 % (kind, lab, a, ("%.2f m" % y) if y is not None else "—", gr))
        prev = (a, y)
    return ('<div class="tw"><table><thead><tr><th>種別</th><th>地点</th>'
            "<th>取入口からの距離</th><th>水面</th><th class='note'>一つ上流からの勾配・落差</th>"
            "</tr></thead><tbody>%s</tbody></table></div>"
            "<p class='cap'>⛔ <b>距離も勾配もすべて従属値</b>(座標と水面の設計値から生成器が測る)— "
            "指図にも kosho.md にも写さない(規則4)。"
            "⭐ <b>末端は区画の南西の出口 P4</b>まで引いてある(⚠ <b>ここはまだ溜池の汀ではない</b> — "
            "最も南西の頂点は P6 で、P4 の地盤は溜池の水面より高い。考証方 2026-09-01 高2 の是正)。"
            "この先は<b>区画外の自然の谷</b>を下って汀へ達する — "
            "貞享4年(1687)『江戸鹿子』の「滝の末は赤坂の溜池へ落ち」が"
            "設計として成立していることを図の上で最後まで追えるようにするため。</p>" % rows)


def mizu_profile_svg(d):
    """**水の系の縦断**(取入口 → 池 → 余水 → 台地端の滝 → 南西の谷 → 溜池)。"""
    ch = _mizu_chain(d)
    br = _mizu_branch(d)
    if not ch:
        return ""
    W = 980.0
    HEAD, FOOT = 26.0, 46.0
    smax = max([a for (a, _y, _l, _k) in ch] + [a for (a, _y, _l, _k) in br])
    ys = [y for (_a, y, _l, _k) in ch + br if y is not None]
    y0, y1 = min(ys) - 2.0, max(ys) + 2.0
    EX = 8.0
    sx = W / max(1.0, smax)
    H = (y1 - y0) * sx * EX + HEAD + FOOT
    g = _sv(W, H, "松平出羽守上屋敷 水の系の縦断")
    X = lambda a: a * sx
    Y = lambda y: HEAD + (y1 - y) * sx * EX
    pts = [(X(a), Y(y)) for (a, y, _l, _k) in ch if y is not None]
    g.append('<polygon points="%s %.1f,%.1f %.1f,%.1f" fill="#9fbfd0" opacity="0.55"/>'
             % (" ".join("%.1f,%.1f" % p for p in pts), X(smax), Y(y0), 0.0, Y(y0)))
    g.append('<polyline points="%s" fill="none" stroke="#3f6a80" stroke-width="2.0"/>'
             % " ".join("%.1f,%.1f" % p for p in pts))
    if br:
        bp = [(X(a), Y(y)) for (a, y, _l, _k) in br if y is not None]
        g.append('<polyline points="%s" fill="none" stroke="#5f7a4e" stroke-width="2.0" '
                 'stroke-dasharray="7 4"/>' % " ".join("%.1f,%.1f" % q for q in bp))
    LB = LabelSet(step=11.0)
    COL = {"枡": "#3d6ea8", "岩屋": "var(--shu)", "落ち口": "var(--shu)", "池": "#3f6a80",
           "堰": "#7a5c3a", "暗渠": "#5f7a4e", "遣水": "#3f6a80", "滝": "var(--shu)",
           "沢": "#7a6a3d", "溜池": "#3d6ea8"}
    for (a, y, lab, kind) in list(ch) + list(br):
        if y is None:
            continue
        x, yy = X(a), Y(y)
        g.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="%s"/>'
                 % (x, yy, COL.get(kind, "var(--ink)")))
        if lab:
            LB.add(x, yy, "%s %.2fm" % (lab, y), fs=8.5, dy=-5.0)
    for yy in [y0 + (y1 - y0) * t for t in (0.0, 0.25, 0.5, 0.75, 1.0)]:
        g.append(LN(0, Y(yy), W, Y(yy), "var(--ink-lo)", 0.5, "2 4", 0.45))
        g.append(T(2, Y(yy) - 2, "%.1fm" % yy, "jo"))
    g.extend(LB.out())
    g.append(T(4, 16, "水の系の縦断 ／ 水平 %.0fm ／ 垂直 %.0f 倍 ／ 実線=本流(池を通る)"
               " ／ 破線=枝2(遣水)" % (smax, EX), "anS", "start"))
    g.append("</svg>")
    return "\n".join(g)


def taki_table(d):
    """**台地端の滝(三段)**。⛔ 地盤は指図に書かない — ここで測る。

    ⭐ **当て先は設計地盤**(2026-09-01 第3次)。三段は段 `Shukaku` の南縁から出る
      1:1.5 の盛土法面の中に組むので、**造成前DEM との比較は参考値**にとどめる。"""
    mz = d.get("mizu")
    if not mz or "takiDaichi" not in mz:
        return ""
    terr, dm = _terr_json(), _dem_json()
    rows = ""
    for (t, bot, pt) in _taki_feet(d):
        des = _ground_uv(d, pt[0], pt[1], terr, dm)
        nat = _nat_uv(terr, round(pt[0]), round(pt[1]))
        rows += ("<tr><td>%s</td><td>u%.1f v%.1f</td><td>%.2f m</td><td>%.2f m</td>"
                 "<td><b>%.2f m</b></td><td>u%.1f v%.1f</td><td>%s</td><td><b>%s</b></td>"
                 "<td class='note'>%s</td></tr>"
                 % (t["label"], t["u"], t["v"], float(t["topY"]), float(t["fall"]), bot,
                    pt[0], pt[1],
                    ("%.2f m" % des) if des is not None else "—",
                    ("%+.2f m" % (bot - des)) if des is not None else "—",
                    ("造成前 DEM %.2f m(差 %+.2f m)【参考】" % (nat, bot - nat))
                    if nat is not None else "造成前 DEM の標本が無い"))
    return ('<div class="tw"><table><thead><tr><th>段</th><th>水落石の位置</th><th>天端</th>'
            "<th>落差</th><th>下端</th><th>滝壺の位置</th><th>滝壺の設計地盤</th>"
            "<th>Δ(下端 − 設計地盤)</th>"
            "<th class='note'>造成前 DEM(参考)</th></tr></thead><tbody>%s</tbody></table></div>"
            "<p class='cap'>⭐ <b>三段は 1:1.5 の設計盛土法面の中に組み、滝石組がそのまま"
            "法面の土留めを兼ねる</b>(庭方 2026-09-01 中7)。⛔ <b>『盛土も切土もほとんど要らない』"
            "は誤りだった</b> — 盛土を張ると決めた場所で造成前 DEM と比べても意味が無い。"
            "検査 <code>taki_check</code> は <b>|下端 − 設計地盤| ≤ 0.30m を全段</b>に回す"
            "(従前は最下段だけ・当て先も造成前 DEM だった)。<br>"
            "⭐ <b>滝壺の位置は次の段の位置</b>(次の段の天端がそこに座る)。最下段だけは"
            "段の刻みの平均を一つ延ばした点で測る。<br>"
            "⭐ <b>一の段・二の段の滝壺と水受石は盛土の上に据えない</b>【B=庭師の作法(類型)】— "
            "基礎を切って<b>自然地盤まで根入れ</b>し、壺は練り基礎+敷石で受ける。"
            "盛土の上の滝壺は<b>沈下と抜け水で涸れる</b>。<br>"
            "⭐ <b>水落石の口は %.1f間(%.2fm)に絞る</b>【B】— 上水の分水は細流なので、"
            "口が広いと水膜が切れて「濡れた石」にしか見えない。"
            "⚠ 中仕切塀 <code>NJ_Oku_S_W</code> が滝の真上を横切るので、"
            "<b>滝見口 <code>NJ_Taki_Kido</code>(庭木戸・1間)</b>を開けて"
            "滝見の床几 <b>V8</b> へ <code>K_Takimi</code> で降りる。</p>"
            % (rows, float(mz["takiDaichi"]["mouth"]),
               float(mz["takiDaichi"]["mouth"]) * d["const"]["ken"]))


def shutei_plan_svg(d, dem):
    """**主庭の平面** — 枯池・築山・園路・主視点 V1 の位置と視線。
    敷地図の縮尺では汀線も飛石も石組も読めないので、主庭だけを大縮尺で出す。"""
    gr = RGrid(d)
    K = d["const"]["ken"]
    terr = _terr_json()
    u0, u1, v0, v1 = -62.0, -27.0, 26.0, 50.0
    corners = [gr.W(a, b) for a in (u0, u1) for b in (v0, v1)]
    pr = Proj(min(q[0] for q in corners) - 4, max(q[0] for q in corners) + 4,
              min(q[1] for q in corners) - 4, max(q[1] for q in corners) + 4,
              W=940.0, top=26.0, bottom=46.0)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 主庭の平面")

    def P(u, v):
        q = gr.W(u, v)
        return pr.X(q[0]), pr.Y(q[1])

    def poly(pts, fill, op=1.0, stroke="none", sw=0.0, dash=None):
        return ('<polygon points="%s" fill="%s" opacity="%.2f" stroke="%s" stroke-width="%.1f"%s/>'
                % (" ".join("%.1f,%.1f" % P(a, b) for (a, b) in pts), fill, op, stroke, sw,
                   ' stroke-dasharray="%s"' % dash if dash else ""))

    LB = LabelSet()                       # ⛔ ラベルを団子にしない(引き出し線で散らす)

    for t in d["terraces"]:
        g.append(poly([(t["u0"], t["v0"]), (t["u1"], t["v0"]),
                       (t["u1"], t["v1"]), (t["u0"], t["v1"])], "var(--pl-main)", 0.45))
    for n in d["gardens"]:
        if n["u1"] < u0 or n["u0"] > u1 or n["v1"] < v0 or n["v0"] > v1:
            continue
        pts = [tuple(p) for p in n["poly"]] if n.get("poly") else \
              [(n["u0"], n["v0"]), (n["u1"], n["v0"]), (n["u1"], n["v1"]), (n["u0"], n["v1"])]
        g.append(poly(pts, "var(--niwa)", 0.9, "var(--ink-lo)", 1.0))
    draw_tsukiyama(d, g, P, poly, LB)
    # --- 棟
    for m in d["munes"] + d["service"]:
        if m["u1"] < u0 or m["u0"] > u1 or m["v1"] < v0 or m["v0"] > v1:
            continue
        g.append(poly([(m["u0"], m["v0"]), (m["u1"], m["v0"]),
                       (m["u1"], m["v1"]), (m["u0"], m["v1"])],
                      "var(--ink-mid)", 0.85, "var(--ink)", 0.7))
        x, y = P((m["u0"] + m["u1"]) / 2.0, (m["v0"] + m["v1"]) / 2.0)
        mlb = MUNE_JA.get(m["name"], m.get("label", m["name"]))
        g.append(T(x, y + 4, mlb, "rmS", "middle",
                   fit(mlb, pr.L((m["u1"] - m["u0"]) * K), 12.0)))
    draw_sensui(d, g, P, pr, poly, LB)
    draw_mizu(d, g, P, pr, poly, LB)
    # --- 園路
    for r in d["routes"]:
        if r.get("kind") != "niwa":
            continue
        pts = [tuple(p) for p in r["pts"]]
        if not any(u0 <= q[0] <= u1 and v0 <= q[1] <= v1 for q in pts):
            continue
        g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.8" '
                 'stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="7 4"/>'
                 % (" ".join("%.1f,%.1f" % P(a, b) for (a, b) in pts), ROUTE_COL["niwa"]))
    # --- 植栽(樹冠の実寸)
    PLC = {"高木": "#3B5A3C", "中木": "#5E7A4E", "低木": "#8FA36B", "下草": "#A8B98A"}
    gs = scatter_gardens(d)
    for pl in d.get("planting", []):
        col = PLC.get(pl.get("role", ""), "#5E7A4E")
        for (uu, vv, pt) in gs.get((pl["zone"], pl["layer"]), []):
            if not (u0 <= uu <= u1 and v0 <= vv <= v1):
                continue
            gm = part_geom(pt)
            x, y = P(uu, vv)
            if gm is not None:
                g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.34"/>'
                         % (x, y, pr.L(gm[0] / 2.0), col))
            g.append('<circle cx="%.1f" cy="%.1f" r="1.6" fill="%s"/>' % (x, y, col))
    # --- 点景
    for t in d.get("tenkei", []):
        if "a" in t:
            xa, ya = P(*t["a"]); xb, yb = P(*t["b"])
            g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--take)" '
                     'stroke-width="2.2" stroke-dasharray="6 3"/>' % (xa, ya, xb, yb))
            continue
        if not (u0 <= t["u"] <= u1 and v0 <= t["v"] <= v1):
            continue
        x, y = P(t["u"], t["v"])
        g.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--shu)"/>' % (x, y))
        LB.add(x, y, t["kind"].split("(")[0], dx=5.0, dy=4.0)
    # --- 主視点と視線
    for vp in d.get("viewpoints", []):
        if not (u0 <= vp["u"] <= u1 and v0 <= vp["v"] <= v1):
            continue
        x, y = P(vp["u"], vp["v"])
        dv = {"-u": (-1, 0), "+u": (1, 0), "-v": (0, -1), "+v": (0, 1)}.get(vp.get("dir"))
        if dv:
            for a in (-30.0, 0.0, 30.0):
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                du = dv[0] * ca - dv[1] * sa
                dvv = dv[0] * sa + dv[1] * ca
                x2, y2 = P(vp["u"] + du * 26, vp["v"] + dvv * 26)
                g.append(LN(x, y, x2, y2, "var(--shu)", 1.2 if a else 2.0,
                            "4 4" if a else None, 0.85))
        g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--paper)" stroke="var(--shu)" '
                 'stroke-width="2.2"/>' % (x, y))
        g.append(T(x, y + 4, vp["name"], "rmS", "middle", 10.0, "var(--shu)"))
        LB.add(x, y, vp["label"], dx=9.0, dy=-7.0)
    g.extend(LB.out())
    g.append(T(4, 16, "★ V1 = 主景(御休息之間・座視 %.1fm)／実線=視線の芯・破線=視野±30°"
               % d["viewpoints"][0]["eye"], "anS", "start"))
    g.append(T(pr.W - 4, 16, "北 ↑　左=西(築山・崖・溜池)", "anS", "end"))
    g.append("</svg>")
    return "\n".join(g)


# ---------------------------------------------------------------- 板塀の根石(2026-09-01)
def _ray_dir(deg):
    """`gardenSections[].deg` = **−u から南(+v)へ振る角**[°] → グリッドの単位ベクトル。"""
    r = math.radians(float(deg))
    return (-math.cos(r), math.sin(r))


def garden_section_geom(d, dem, gs):
    """斜めの庭断面の実測。→ {eye, dir, 汀の交点, 板塀の交点, 見切り線, 露出}

    ⛔ 数値は指図に書かない(規則4)— **すべてここで測る従属値**。
    ⭐ **地物への視線は樹冠の下をくぐる。遮蔽は必ず断面(仰角の帯)で見る**
      — 2026-09-01 に平面の方位の帯だけで沢渡の遮蔽を判じて誤った。"""
    vps = {v["name"]: v for v in d.get("viewpoints", [])}
    vp = vps.get(gs.get("from"))
    ks = d.get("sensui")
    if vp is None or not ks:
        return None
    K = d["const"]["ken"]
    terr, dm = _terr_json(), _dem_json()
    du, dv = _ray_dir(gs["deg"])
    smax = float(gs.get("smax", 30.0)) / K                 # [間]
    A = (vp["u"], vp["v"])
    B = (vp["u"] + du * smax, vp["v"] + dv * smax)
    out = {"vp": vp, "dir": (du, dv), "smax": smax, "K": K}

    def hit(seg_a, seg_b):
        p = _x_seg(A, B, seg_a, seg_b)
        if p is None:
            return None
        return (math.hypot(p[0] - A[0], p[1] - A[1]), p)

    # ① 枯池の汀 — **いちばん遠い交点**(そこから先に板塀がある)
    po = [tuple(p) for p in ks["pond"]["outline"]]
    far, edge = None, None
    for i in range(len(po)):
        h = hit(po[i], po[(i + 1) % len(po)])
        if h and (far is None or h[0] > far[0]):
            far, edge = h, i + 1
    out["pond"] = far
    out["pondEdge"] = edge
    # ② 板塀 — 汀より遠い最初の交点
    rule = (d.get("nakajikiriRule") or {}).get("neishi") or {}
    kinds = rule.get("applyKind") or []
    best = None
    for nj in d.get("nakajikiri", []):
        if nj.get("kind") not in kinds:
            continue
        h = hit(tuple(nj["a"]), tuple(nj["b"]))
        if h and (far is None or h[0] > far[0] + 1e-6) and (best is None or h[0] < best[0]):
            best = (h[0], h[1], nj)
    out["hei"] = best
    if far is None or best is None:
        return out
    out["yPond"] = _ground_uv(d, far[1][0], far[1][1], terr, dm)
    out["yHei"] = _ground_uv(d, best[1][0], best[1][1], terr, dm)
    # ③ 見切り線 — 眼から護岸石の天端を掠め、板塀の位置で何処を通るか
    #   ⭐ **B案(2026-09-01 改)で天端は設計値**(水面 + `bands[].topAbove`)。
    #     ⛔ A案の『石の丈 ×(1−bury) − dig』は撤回した。
    wy = float(ks["pond"]["waterY"])
    band = None
    for b in gogan_bands(d):
        if b["pitch"] > 0 and band is None:
            band = b                                        # 手前の帯(bands の先頭)
    lo, hi = band["show"][0]                                # topAbove の下限・上限
    out["band"] = band
    out["waterY"] = wy
    out["rows"] = []
    # ⭐ **遮蔽体は「視線に沿って仰角が最大の地物」**【庭方 2026-09-02 回答4】。
    #   ⛔ 護岸石の天端を無条件に遮蔽体へ採ってはいけない — その線は**内側の地山に潜って**
    #     塀へ届く(図で破線が黒い地山を貫いていたのがそれ)。地山より低い角度の物は
    #     何も遮蔽しない。⭕ 設計地盤も候補に入れ、**仰角の最大**を採る。
    gsl, gat = None, None
    ss = 0.5
    while ss < best[0] - 1e-9:
        yg = _ground_uv(d, A[0] + du * ss, A[1] + dv * ss, terr, dm)
        if yg is not None:
            sl = (yg - vp["eye"]) / (ss * K)                # 下向きが負 → 大きいほど高い仰角
            if gsl is None or sl > gsl:
                gsl, gat = sl, ss
        ss += 0.10
    out["ground"] = {"slope": gsl, "at": gat,
                     "y": None if gat is None else
                     _ground_uv(d, A[0] + du * gat, A[1] + dv * gat, terr, dm)}
    for (lab, lg) in (("下限", lo), ("平均", (lo + hi) / 2.0), ("上限", hi)):
        top = wy + lg
        ssl = (top - vp["eye"]) / (far[0] * K)              # 護岸石の天端への仰角
        if gsl is not None and gsl > ssl:
            yl, by = vp["eye"] + gsl * best[0] * K, "汀の地盤の稜"
        else:
            yl, by = vp["eye"] + ssl * best[0] * K, "護岸石の天端"
        out["rows"].append({"lab": lab, "long": lg, "top": top, "line": yl,
                            "exp": out["yHei"] - yl, "by": by})
    out["show"] = rule.get("show", [0.15, 0.20])
    return out


def neishi_check(d, dem):
    """**板塀の足元が納まっているか**【庭方 2026-09-01 第2次検分 6-①】。

    ⛔ 池の護岸では板塀の足元は隠せない — V1 から手前の護岸石の天端を掠める見切り線は、
      板塀の位置では足元より**下**を通る。⭕ 隠さずに**根石**で納める。
    検査は ①根石の規則が有るか ②露出(平均の石で測る)が根石の見え高に収まるか。
    ⚠ 露出は**石の丈の帯のぶん振れる**ので、下限・上限も表に出す(判定は平均で行う)。"""
    bad = []
    rule = (d.get("nakajikiriRule") or {}).get("neishi")
    if rule is None:
        return ["`nakajikiriRule.neishi`(板塀の根石)が無い — 板の裾を土へ直接落とすことになる"
                "(裾が腐る)。池の護岸では隠せないので**根石で納める**"]
    for nj in d.get("nakajikiri", []):
        if nj.get("kind") in (rule.get("applyKind") or []):
            break
    else:
        bad.append("`nakajikiriRule.neishi.applyKind` %s に当たる中仕切が1本も無い — "
                   "**この検査は回っていない**(合格ではない)" % rule.get("applyKind"))
    for gs in d.get("gardenSections", []):
        gm = garden_section_geom(d, dem, gs)
        if gm is None or not gm.get("rows"):
            bad.append("庭の断面『%s』が測れない(主視点か池か板塀の交点が無い)" % gs["name"])
            continue
        lo, hi = gm["show"]
        av = [r for r in gm["rows"] if r["lab"] == "平均"][0]
        if av["exp"] < -1e-9:
            bad.append("庭の断面『%s』: 板塀の足元が護岸石の見切り線より %.3fm 下 — "
                       "護岸で隠れている。根石の設計が要らないか見直すこと"
                       % (gs["name"], -av["exp"]))
        elif av["exp"] > hi + 1e-9:
            bad.append("庭の断面『%s』: 板塀の足元の露出 %.3fm が根石の見え高の上限 %.2fm を"
                       "超える — 根石で納まらない(`nakajikiriRule.neishi.show` か"
                       "護岸の丈を見直す)" % (gs["name"], av["exp"], hi))
    return bad


def neishi_table(d, dem):
    rule = (d.get("nakajikiriRule") or {}).get("neishi")
    if rule is None:
        return ""
    out = []
    for gs in d.get("gardenSections", []):
        gm = garden_section_geom(d, dem, gs)
        if gm is None or not gm.get("rows"):
            continue
        K = gm["K"]
        rows = ""
        for r in gm["rows"]:
            rows += ("<tr><td>%s</td><td>%.3f m</td><td>%.3f m</td><td>%s</td><td>%.3f m</td>"
                     "<td><b>%+.3f m</b></td></tr>"
                     % (r["lab"], r["long"], r["top"], r.get("by", "—"), r["line"], r["exp"]))
        out.append("<h3>%s — <b>板塀の足元は隠せるか</b></h3>"
                   "<p class='cap'>主視点 <b>%s</b>(眼高 %.2fm)から −u より南へ <b>%.1f°</b>。"
                   "御泉水の汀(汀線 #%d)まで <b>%.2f m</b>・板塀 <b>%s</b> まで <b>%.2f m</b>。"
                   "見切り線 = 眼から出て<b>仰角が最大の地物</b>を掠める線"
                   "(⛔ 護岸石の天端を無条件に採らない)。</p>"
                   "<div class='tw'><table><thead><tr><th>護岸石の天端</th><th><code>topAbove</code></th>"
                   "<th>石の天端</th><th>遮蔽体(仰角が最大)</th><th>板塀の位置での見切り線</th>"
                   "<th>塀の足元(%.3fm)の露出</th></tr></thead><tbody>%s</tbody></table></div>"
                   "<p class='cap'>⚠ <b>2026-09-02(第4次)に測り方を直した</b>【庭方 回答4】— "
                   "従前は<b>護岸石の天端を遮蔽体に採っていた</b>が、その線は"
                   "<b>汀の内側の地山に潜って</b>塀へ届く(図で破線が黒い地山を貫いていた)。"
                   "⛔ 地山より低い角度の物は何も遮蔽しない。⭕ 正しい遮蔽体は"
                   "<b>視線に沿って仰角が最大の地物</b>で、ここでは<b>汀の地盤の稜</b>。<br>"
                   "⭕ <b>設計は一つも動かない</b>(根石の見え高・<code>gogan.topCheck</code>・"
                   "<code>bands[].topAbove</code> はすべて据え置き)。"
                   "汀と塀のあいだは 27.00 の平場が連続するので、"
                   "<b>見えるのは根石(%s・見え高 %.2f〜%.2fm)の見え面だけ</b>で、"
                   "<b>『土に刺さった板の裾』でなく『石の腰の上に立つ板塀』</b>として読める。"
                   "⛔ 板塀の裾を土に直接落とすのは実際の作りとしても誤り(裾が腐る)。</p>"
                   % (gs["name"], gm["vp"]["name"], gm["vp"]["eye"], float(gs["deg"]),
                      gm["pondEdge"], gm["pond"][0] * K, gm["hei"][2]["name"],
                      gm["hei"][0] * K, gm["yHei"], rows,
                      rule["kind"], rule["show"][0], rule["show"][1]))
    return "".join(out)


def garden_section_svg(d, dem, gs):
    """**斜めの庭断面**(V1 → 奥向の板塀)。池の水面と底・護岸石の見え面・見切り線・板塀の足元。

    ⛔ 主庭の V1 断面(−u 真西)ではこの判定はできない — 板塀は真西の断面に載らない
      (2026-09-01 の庭方の指摘 6-①)。"""
    gm = garden_section_geom(d, dem, gs)
    if gm is None or not gm.get("rows"):
        return ""
    K, vp = gm["K"], gm["vp"]
    du, dv = gm["dir"]
    terr, dm = _terr_json(), _dem_json()
    smax = gm["smax"]
    prof, ss = [], 0.0
    while ss <= smax + 1e-9:
        y = _ground_uv(d, vp["u"] + du * ss, vp["v"] + dv * ss, terr, dm)
        if y is not None:
            prof.append((ss, y))
        ss += 0.05
    ys = [p[1] for p in prof] + [vp["eye"]]
    y0, y1 = min(ys) - 0.8, max(ys) + 0.8
    W, EX = 980.0, float(gs.get("vExag", 6.0))
    sx = W / (smax * K)
    HEAD, FOOT = 26.0, 40.0
    H = (y1 - y0) * sx * EX + HEAD + FOOT
    g = _sv(W, H, "松平出羽守上屋敷 " + gs["name"])
    X = lambda t: t * K * sx
    Y = lambda y: HEAD + (y1 - y) * sx * EX
    g.append('<polygon points="%s %.1f,%.1f %.1f,%.1f" fill="var(--jiban)" opacity="0.9"/>'
             % (" ".join("%.1f,%.1f" % (X(a), Y(b)) for (a, b) in prof),
                X(smax), Y(y0), 0.0, Y(y0)))
    LBS = LabelSet(step=10.0)
    ex, ey = X(0.0), Y(vp["eye"])
    g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>' % (ex, ey))
    LBS.add(ex, ey, "%s %s 眼高 %.2fm" % (vp["name"], vp["label"], vp["eye"]), dx=6.0, dy=-6.0)
    # --- 護岸石(手前帯)の丈の3つと、その天端を掠める見切り線
    sp, sh = gm["pond"][0], gm["hei"][0]
    COL = {"下限": "#b06a3a", "平均": "var(--shu)", "上限": "#4a7a52"}
    PD = d["sensui"]["pond"]
    for r in gm["rows"]:
        g.append(LN(X(sp), Y(float(PD["waterY"])),
                    X(sp), Y(r["top"]), COL[r["lab"]], 3.0, None, 0.85, "butt"))
        g.append(LN(ex, ey, X(sh), Y(r["line"]), COL[r["lab"]], 1.2, "5 4", 0.9))
        if gm.get("ground") and gm["ground"].get("at") is not None and r["lab"] == "平均":
            g.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="none" stroke="var(--shu)" '
                     'stroke-width="1.6"/>' % (X(gm["ground"]["at"]), Y(gm["ground"]["y"])))
            LBS.add(X(gm["ground"]["at"]), Y(gm["ground"]["y"]),
                    "遮蔽体(仰角が最大)= 汀の地盤の稜 %.2fm" % gm["ground"]["y"],
                    fs=8.5, dx=4.0, dy=-6.0)
        LBS.add(X(sh), Y(r["line"]), "見切り線(遮蔽体=%s)→ 露出 %+.3fm"
                % (r.get("by", "—"), r["exp"]), fs=8.5, fill=COL[r["lab"]],
                anchor="end", dx=-4.0, dy=-2.0)
    # --- 御泉水(水面と底)
    wy, fl = float(PD["waterY"]), float(PD["floorY"])
    g.append(LN(X(sp) - 26.0, Y(wy), X(sp), Y(wy), "#3f6a80", 2.0, None, 0.95))
    g.append(LN(X(sp), Y(wy), X(sp), Y(fl), "#6b6446", 1.0, "2 3", 0.9))
    LBS.add(X(sp), Y(wy), "水面 %.2fm(汀の立ち上がり %.2fm)"
            % (wy, gm["yPond"] - wy), fs=8.5, dx=-4.0, dy=-4.0, anchor="end")
    LBS.add(X(sp), Y(fl), "池底 %.2fm(深さ %.2fm・垂直掘り)"
            % (fl, float(PD["depth"])), fs=8.5, dx=-4.0, dy=10.0, anchor="end")
    # --- 板塀
    hei = gm["hei"][2]
    hh = float(hei.get("h", 2.4))
    g.append(R(X(sh) - 1.6, Y(gm["yHei"] + hh), 3.2, max(1.0, Y(gm["yHei"]) - Y(gm["yHei"] + hh)),
               fill="#7a6a55", op=0.95))
    ne = (d["nakajikiriRule"]["neishi"])
    g.append(R(X(sh) - 3.0, Y(gm["yHei"] + ne["show"][1]), 6.0,
               max(1.0, Y(gm["yHei"]) - Y(gm["yHei"] + ne["show"][1])), fill="#8f8a6e", op=1.0))
    LBS.add(X(sh), Y(gm["yHei"]), "%s の足元 %.3fm ／ 根石 見え高 %.2f〜%.2fm"
            % (hei["name"], gm["yHei"], ne["show"][0], ne["show"][1]), fs=8.5, dx=6.0, dy=6.0)
    for yy in [y0 + (y1 - y0) * t for t in (0.0, 0.25, 0.5, 0.75, 1.0)]:
        g.append(LN(0, Y(yy), W, Y(yy), "var(--ink-lo)", 0.5, "2 4", 0.45))
        g.append(T(2, Y(yy) - 2, "%.1fm" % yy, "jo"))
    g.extend(LBS.out())
    g.append(T(4, 16, "%s ／ −u から南へ %.1f° ／ 垂直 %.0f 倍"
               % (gs["name"], float(gs["deg"]), EX), "anS", "start"))
    g.append("</svg>")
    return "\n".join(g)


def shutei_section_svg(d, dem):
    """**主庭の見通し**(V1 の断面)。前景/中景/遠景の三層と、
    ⛔ **溜池が見えないこと**を断面で示す。"""
    gr = RGrid(d)
    K = d["const"]["ken"]
    terr = _terr_json()
    vp = [x for x in d["viewpoints"] if x.get("main")][0]
    wy = tameike_water_y()
    u_lo, u_hi = -118.0, vp["u"] + 2.0
    prof = []
    u = u_hi
    while u >= u_lo:
        y = _ground_uv(d, u, vp["v"], terr, dem)
        if y is not None:
            prof.append((u, y))
        u -= 0.25
    ys = [p[1] for p in prof] + [vp["eye"], wy or 6.6]
    y0, y1 = min(ys) - 2.0, max(ys) + 6.0
    W, EX = 980.0, 2.2
    sx = W / (u_hi - u_lo) / K
    HEAD, FOOT = 26.0, 52.0
    H = (y1 - y0) * sx * EX + HEAD + FOOT
    g = _sv(W, H, "松平出羽守上屋敷 主庭の見通し(V1)")

    def X(u):
        return (u_hi - u) * K * sx
    def Y(y):
        return HEAD + (y1 - y) * sx * EX

    g.append('<polygon points="%s %.1f,%.1f %.1f,%.1f" fill="var(--jiban)" opacity="0.9"/>'
             % (" ".join("%.1f,%.1f" % (X(a), Y(b)) for (a, b) in prof),
                X(u_lo), Y(y0), X(u_hi), Y(y0)))
    if wy is not None:
        g.append('<rect x="0" y="%.1f" width="%.1f" height="%.1f" fill="#5b86a8" opacity="0.5"/>'
                 % (Y(wy), X(u_lo) - X(prof[-1][0]) + 1, max(1.0, Y(y0) - Y(wy))))
        g.append(T(6, Y(wy) - 4, "溜池の水面 %.1fm(正典=外堀の指図)" % wy, "jo", "start"))
    # 見通し線 — 眼から出て、**地面に当たった所で止まる**
    ex, ey = X(vp["u"]), Y(vp["eye"])
    g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>' % (ex, ey))
    g.append(T(ex + 6, ey - 6, "%s %s 眼高 %.2fm" % (vp["name"], vp["label"], vp["eye"]), "jo"))
    best = None
    for (u, y) in prof:
        if u >= vp["u"] - 0.5:
            continue
        sl = (y - vp["eye"]) / ((vp["u"] - u) * K)      # 下向きが負
        if best is None or sl > best[0]:
            best = (sl, u, y)
    sl, bu, by = best
    fx, fy = X(u_lo), Y(vp["eye"] + sl * (vp["u"] - u_lo) * K)
    g.append(LN(ex, ey, fx, fy, "var(--shu)", 2.0, "6 4"))
    g.append(LN(X(bu), Y(by), X(bu), Y(y0), "var(--shu)", 1.0, "2 3", 0.7))
    g.append(T(X(bu), Y(by) - 8, "見通しを切る肩(u%.0f・%.2fm)" % (bu, by), "jo", "middle"))
    floor = vp["eye"] + sl * (vp["u"] - u_lo) * K
    g.append(T(fx + 4, fy - 6, "この線より下は見えない", "jo", "start"))
    if wy is not None:
        g.append(T(fx + 4, fy + 12, "⛔ 溜池の水面は %.1fm 下 — **借景に取れない**" % (floor - wy),
                   "jo", "start"))
    # ---- ⭐ **三層を支える物を断面に描く**(2026-09-01 検図 改善⑯)
    #      ⛔ 地形のシルエットだけでは『前景=沓脱石・中景=御泉水と築山』という主張が図に無い。
    #      ⚠ 寸法の分からない部材は描かない(⛔ 見た目のために寸法を発明しない)。
    BAND = 3.0                                    # 断面線から左右この間まで拾う[間]
    def _gy(u):
        y = _ground_uv(d, u, vp["v"], terr, dem)
        return Y(y if y is not None else y0)
    SLB = LabelSet(step=10.0)              # ⛔ 断面の点景ラベルを団子にしない
    #  ① 点景(沓脱石・石組・灯籠)— 名前と位置だけ。丈は指図が持たないので棒で示さない
    for t in d.get("tenkei", []):
        if "u" not in t or abs(t["v"] - vp["v"]) > BAND or not (u_lo <= t["u"] <= u_hi):
            continue
        x, yg = X(t["u"]), _gy(t["u"])
        sz = t.get("size")
        if sz:                                    # 寸法のある物(沓脱石)は実寸で
            g.append(R(x - sz[0] / 2.0 * K * sx / K, yg - sz[2] * sx * EX,
                       sz[0] * sx, sz[2] * sx * EX, fill="#6b6446", op=0.95))
        else:
            g.append('<circle cx="%.1f" cy="%.1f" r="3" fill="#6b6446"/>' % (x, yg - 3))
        SLB.add(x, yg + 4, t["kind"], fs=8.5, anchor="middle", dx=0.0, dy=8.0)
    #  ② 植栽 — **樹冠と樹高の実寸が引ける部材だけ**(目録待ちの自作木は描けない)
    gsc = scatter_gardens(d)
    rgv = _rng("section/V1")
    for pl in d.get("planting", []):
        if pl.get("role") == "下草":
            continue                              # 丈 0.3m — この縮尺では地面の色でしかない
        for (uu, vv, pt) in gsc.get((pl["zone"], pl["layer"]), []):
            if abs(vv - vp["v"]) > BAND or not (u_lo <= uu <= u_hi):
                continue
            gm = part_geom(pt)
            if gm is None:
                continue
            g.append("".join(tree_glyph(X(uu), _gy(uu), gm[1] * sx * EX, gm[0] * sx,
                                        part_kind(pt), rgv, 0.85)))
    #  ③ 池 — 汀線が断面線を切る所に印(掘削は地盤の線に出ている)
    ks0 = d.get("sensui")
    if ks0:
        po = [tuple(p) for p in ks0["pond"]["outline"]]
        xs = []
        for i in range(len(po)):
            a, b = po[i], po[(i + 1) % len(po)]
            if (a[1] - vp["v"]) * (b[1] - vp["v"]) < 0:
                uu = a[0] + (b[0] - a[0]) * (vp["v"] - a[1]) / (b[1] - a[1])
                xs.append(uu)
                g.append(LN(X(uu), _gy(uu) - 6, X(uu), _gy(uu) + 6, "#3f6a80", 1.6))
        # ⭐ **水面を引く**(B案)— 汀の交点のあいだを `waterY` で結ぶ
        wyp = float(ks0["pond"]["waterY"])
        if len(xs) >= 2:
            g.append(LN(X(max(xs)), Y(wyp), X(min(xs)), Y(wyp), "#3f6a80", 2.2, None, 0.95))
            g.append(LN(X(max(xs)), Y(float(ks0["pond"]["floorY"])),
                        X(min(xs)), Y(float(ks0["pond"]["floorY"])),
                        "#6b6446", 1.0, "2 3", 0.8))
        SLB.add(X(min(p[0] for p in po)), _gy(min(p[0] for p in po)) + 16,
                "御泉水 水面 %.2fm(汀の立ち上がり 0.95m を石組護岸が受ける)" % wyp,
                fs=8.5, dx=4.0, dy=8.0)
    g.extend(SLB.out())
    # 三層(前景・中景・遠景)の帯 — **物の位置から測る**(言葉で書かない)
    ks = d.get("sensui")
    if ks:
        pu = [p[0] for p in ks["pond"]["outline"]]
        for (a, b, lb) in ((max(pu), vp["u"], "前景"), (min(pu), max(pu), "中景")):
            g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="10" fill="var(--shu)" '
                     'opacity="0.18"/>' % (X(b), H - FOOT + 8, X(a) - X(b)))
            g.append(T((X(a) + X(b)) / 2, H - FOOT + 17, lb, "jo", "middle"))
    for tk in d.get("tsukiyama", []):
        us = [p[0] for p in tk["skirt"]]
        g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="10" fill="#8a7f52" '
                 'opacity="0.20"/>' % (X(max(us)), H - FOOT + 8, X(min(us)) - X(max(us))))
        g.append(T((X(min(us)) + X(max(us))) / 2, H - FOOT + 17, "築山", "jo", "middle"))
    g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="10" fill="#3B5A3C" opacity="0.18"/>'
             % (X(-76.0), H - FOOT + 8, X(u_lo) - X(-76.0)))
    g.append(T((X(-76.0) + X(u_lo)) / 2, H - FOOT + 17, "遠景=西斜面の樹林", "jo", "middle"))
    for yy in range(int(y0 // 5 * 5), int(y1) + 5, 5):
        if y0 <= yy <= y1:
            g.append(LN(0, Y(yy), W, Y(yy), "var(--ink-lo)", 0.5, "2 4", 0.5))
            g.append(T(2, Y(yy) - 2, "%dm" % yy, "jo"))
    g.append(T(4, 16, "V1 から西(−u 249.7°)を見る。垂直 %.1f 倍" % EX, "anS", "start"))
    g.append("</svg>")
    return "\n".join(g)


def viewpoints_table(d):
    gr = RGrid(d)
    deg = {"-u": 180.0, "+u": 0.0, "-v": 270.0, "+v": 90.0}
    g0 = d["grid"]["shukaku"]
    base = math.degrees(math.atan2(g0["ux"], g0["uz"]))
    rows = ""
    for v in d["viewpoints"]:
        w = gr.W(v["u"], v["v"])
        dd = {"-u": base + 180.0, "+u": base, "-v": base + 270.0, "+v": base + 90.0}\
            .get(v.get("dir"))
        rows += ("<tr><td>%s%s</td><td>%s</td><td>u%.1f v%.1f<br><span class='note'>"
                 "(%.1f, %.1f)</span></td><td>%.2f m<br><span class='note'>%s</span></td>"
                 "<td>%s</td><td class='note'>%s</td><td class='note'>%s</td>"
                 "<td class='note'>%s</td><td>%s</td></tr>"
                 % ("★" if v.get("main") else "", v["name"], v["label"], v["u"], v["v"],
                    w[0], w[1], v["eye"],
                    v["posture"] + ("(従属値)" if v.get("_eyeDerived") else ""),
                    ("%.1f°" % (dd % 360.0)) if dd is not None else v.get("dir", ""),
                    inline(v["fore"]), inline(v["mid"]), inline(v["far"]), v["cert"]))
    return ('<div class="tw"><table><thead><tr><th>視点</th><th>場所</th>'
            '<th>グリッド / 世界</th><th>眼高</th><th>方位</th><th class="note">前景</th>'
            '<th class="note">中景</th><th class="note">遠景</th><th>確度</th></tr></thead>'
            "<tbody>%s</tbody></table></div>" % rows)


def tsukiyama_table(d, dem):
    """築山の実測。**法は `batter.measure` の区間ごとに測る**(2026-09-01 検図 改善⑬)。
    ⛔ 法の数値を指図に書き写さない — 輪郭と造成前地盤から出る従属値。"""
    rows = ""
    for (tk, A, V, nori) in tsukiyama_measure(d, dem):
        rows += ("<tr><td>%s</td><td>u%.1f v%.1f</td><td>%.1f m</td><td>%.0f m²</td>"
                 "<td><b>%.0f m³</b></td><td class='note'>%s</td></tr>"
                 % (tk["name"], tk["u"], tk["v"], tk["y"], A, V, inline(tk["_"])))
    out = ('<div class="tw"><table><thead><tr><th>築山</th><th>頂</th><th>頂の標高</th>'
           '<th>裾の面積</th><th>盛土</th>'
           '<th class="note">注記</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    r2 = ""
    for (tk, _A, _V, nori) in tsukiyama_measure(d, dem):
        for ar in (tk.get("batter", {}).get("measure") or []):
            v = [x[1] for x in nori if x[0] == ar["where"]]
            if not v:
                continue
            r2 += ("<tr><td>%s</td><td>%d°〜%d°</td><td>%d 点</td>"
                   "<td><b>1:%.2f 〜 1:%.2f</b></td></tr>"
                   % (ar["where"], ar["deg"][0], ar["deg"][1], len(v), min(v), max(v)))
    return out + ('<div class="tw"><table><thead><tr><th>法を測る区間</th><th>方位</th>'
                  '<th>裾の点</th><th>法(実測)</th></tr></thead><tbody>%s</tbody></table></div>'
                  % r2)


def garden_access_table(d, lim=20.0):
    """**庭のどこまで道が届くか。**⛔ 2026-09-01 の庭方の不合格の第一項を数で示す表。"""
    K = d["const"]["ken"]
    paths = _all_paths(d)
    rows = ""
    for z in d["gardens"]:
        if z.get("cert") == "?" or z.get("kind") == "shirasu":
            continue
        if z["name"] in ("G_Baba", "G_HigashiSaien", "G_SakujiAkichi", "G_BabaAkichi",
                         "G_Shintan", "G_Koedame", "G_KatteNiwa", "G_GenkanE",
                         "G_MaeAkichi", "G_Inubashiri", "G_Tomomachi"):
            continue
        tot = far = 0
        dmax = 0.0
        for (u, v) in _garden_pts(z):
            tot += 1
            dmin = 1e9
            for _nm, pts in paths:
                for i in range(len(pts) - 1):
                    dmin = min(dmin, _seg_dist((u, v), pts[i], pts[i + 1]) * K)
            dmax = max(dmax, dmin)
            if dmin > lim:
                far += 1
        if not tot:
            continue
        rows += ("<tr><td>%s</td><td>%s</td><td>%.0f 坪</td><td>%.1f m</td>"
                 "<td%s>%.0f%%</td></tr>"
                 % (z["name"], z["label"], tot * (0.5 ** 2), dmax,
                    ' style="color:var(--shu)"' if far > tot * 0.15 else "",
                    100.0 * far / tot))
    return ('<div class="tw"><table><thead><tr><th>庭</th><th>名</th><th>面積</th>'
            '<th>最寄りの道までの最大</th><th>%.0fm 超の割合</th></tr></thead>'
            "<tbody>%s</tbody></table></div>" % (lim, rows))


def route_profile(d, r, dem, step=0.1):
    """動線・園路の**縦断**を設計地盤から実測する。→ (延長m, 総昇りm, 総降りm, 最急勾配, 標高の両端)

    ⚠ 2026-09-01 検図(致命3): 従前は『石段(`kaidans`)の落差の合計』を昇りとしていたので、
      **石段の無い園路は必ず 0.0m / 0段**になった(主庭の道は築山の頂を越えるのに 0.0m)。
      ⭕ 昇りは**地盤から測る**(構造で直す)。石段は別の欄で数える。"""
    terr = _terr_json()
    K = d["const"]["ken"]
    pts = [tuple(p) for p in r["pts"]]
    prof, L = [], 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(seg / step))
        for j in range(n + (1 if i == len(pts) - 2 else 0)):
            t = j / float(n)
            u, v = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            y = _ground_uv(d, u, v, terr, dem)
            if y is not None:
                prof.append((L + seg * t, y))
        L += seg
    up = dn = 0.0
    grade = 0.0
    for i in range(len(prof) - 1):
        dl = (prof[i + 1][0] - prof[i][0]) * K
        dy = prof[i + 1][1] - prof[i][1]
        if dy > 0:
            up += dy
        else:
            dn += -dy
        if dl > 1e-6:
            grade = max(grade, abs(dy) / dl)
    return (L * K, up, dn, grade,
            (prof[0][1] if prof else None, prof[-1][1] if prof else None))


def route_grade_check(d, dem):
    """**歩ける勾配か。**⛔ 段の無い区間が『階段の勾配』より急なら、そこは歩けない。

    しきい値は `const.keri / const.fumi`(蹴上÷踏面)から出す — ⛔ ここで数を作らない。
    石段(`kaidans`)の近くは段が受けるので除く。
    ⚠ 2026-09-01 検図(致命3): 昇りを石段の落差の合計で出していたので、
      **石段の無い園路は必ず 0.0m** になり、急な区間が図にも表にも出なかった。"""
    K = d["const"]["ken"]
    lim = float(d["const"]["keri"]) / float(d["const"]["fumi"])
    terr = _terr_json()
    bad = []
    for r in d.get("routes", []):
        pts = [tuple(p) for p in r["pts"]]
        worst = None
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            n = max(1, int(seg / 0.2))
            for j in range(n):
                t0, t1 = j / float(n), (j + 1) / float(n)
                p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
                p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
                mid = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
                if any("pos" in k and math.hypot(mid[0] - k["pos"][0],
                                                 mid[1] - k["pos"][1]) <= 3.0
                       for k in d.get("kaidans", [])):
                    continue                      # 段が受ける区間
                y0 = _ground_uv(d, p0[0], p0[1], terr, dem)
                y1 = _ground_uv(d, p1[0], p1[1], terr, dem)
                dl = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * K
                if y0 is None or y1 is None or dl < 1e-6:
                    continue
                gg = abs(y1 - y0) / dl
                if worst is None or gg > worst[0]:
                    worst = (gg, mid)
        if worst and worst[0] > lim:
            bad.append("動線 %s が u%.1f v%.1f で 1:%.1f — 段の無い区間で"
                       "階段の勾配(1:%.1f)より急。**歩けない**(石段を起こすか"
                       "土留め・法面で受けること)"
                       % (r["label"], worst[1][0], worst[1][1], 1.0 / worst[0], 1.0 / lim))
    return bad


def routes_table(d, dem):
    rows = ""
    for r in d["routes"]:
        L, up, dn, grade, ends = route_profile(d, r, dem)
        uniq = [k for k in d["kaidans"] if k["name"] in
                [x["kaidan"] for x in r.get("steps", [])]]
        for k in d["kaidans"]:                     # 位置から3間以内を通る石段も拾う
            if "pos" not in k or k in uniq:
                continue
            ku, kv = k["pos"]
            for i in range(len(r["pts"]) - 1):
                a, b = r["pts"][i], r["pts"][i + 1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dy * dy
                t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((ku - a[0]) * dx + (kv - a[1]) * dy) / L2))
                if math.hypot(ku - (a[0] + dx * t), kv - (a[1] + dy * t)) <= 3.0:
                    uniq.append(k)
                    break
        steps = sum(k["steps"] for k in uniq)
        rows += ("<tr><td>%s</td><td>%.0f m</td><td>%.2f → %.2f m</td><td>%.2f m</td>"
                 "<td>%.2f m</td><td>1:%.1f</td><td>%d 段</td><td class='note'>%s</td></tr>"
                 % (r["label"], L,
                    ends[0] if ends[0] is not None else 0.0,
                    ends[1] if ends[1] is not None else 0.0,
                    up, dn, (1.0 / grade) if grade > 1e-6 else 99.9, steps,
                    " / ".join(k["name"] for k in uniq) if uniq else "石段なし"))
    return ('<div class="tw"><table><thead><tr><th>系統</th><th>延長</th><th>標高(始→終)</th>'
            "<th>総昇り</th><th>総降り</th><th>最急</th>"
            "<th>石段</th><th class='note'>越える石段</th></tr></thead><tbody>%s</tbody></table></div>"
            % rows)


FUKUGEN_JA = TERR_JA["Fukugen"]


def cutfill_stats_table(d, stats):
    """段ごとの土量。⭐ **拝領時造成と復元レイヤを二段に分ける**(2026-09-01 検図 改善①)。

    ⛔ 一段で出すと差引が復元レイヤに支配され、『江戸の普請は土が足りない』という
      誤った読みになる。⭕ 復元(`Fukugen` = 1883年以降の掘削跡の埋め戻し)は
      **拝領時造成とは別勘定**で、築山の土の出所(`tsukiyama.M_Tsukiyama.do`)の
      根拠がここに出る。"""
    K2 = (d["const"]["ken"]) ** 2

    def block(title, keys, note=""):
        r = "<tr><td colspan='6'><b>%s</b>%s</td></tr>" % (
            title, ("<span class='note'> — %s</span>" % note) if note else "")
        f = c = 0.0
        for k in sorted(keys, key=lambda x: -stats[x][0]):
            f2, fm, c2, cm, n = stats[k]
            f += f2; c += c2
            r += ("<tr><td>　%s</td><td>%.0f m²</td><td>%.0f m³</td><td>%.2f m</td>"
                  "<td>%.0f m³</td><td>%.2f m</td></tr>" % (k, n * K2, f2, fm, c2, cm))
        r += ("<tr><td>　<b>小計</b></td><td></td><td><b>%.0f m³</b></td><td></td>"
              "<td><b>%.0f m³</b></td><td></td></tr>" % (f, c))
        r += ("<tr><td>　<b>差引</b></td><td colspan='5' class='note'>盛土 − 切土 = "
              "<b>%.0f m³</b>%s</td></tr>"
              % (f - c, "(正なら土が足りない=客土が要る)" if f > c else ""))
        return r, f, c

    fk = [k for k in stats if k == FUKUGEN_JA]
    ed = [k for k in stats if k != FUKUGEN_JA]
    r1, f1, c1 = block("① 拝領時造成(江戸の普請)", ed,
                       "築山・御泉水を含む。⭕ ここが釣り合っていれば土は屋敷の中で回る")
    r2, f2_, c2_ = block("② 復元レイヤ(近代掘削跡の埋め戻し)", fk,
                         "⛔ 江戸の普請ではない。⛔ ここの客土を築山へ回さない")
    rows = r1 + r2 + ("<tr><td><b>総計</b></td><td></td><td><b>%.0f m³</b></td><td></td>"
                      "<td><b>%.0f m³</b></td><td></td></tr>" % (f1 + f2_, c1 + c2_))
    return ('<div class="tw"><table><thead><tr><th>段</th><th>面積</th><th>盛土量</th><th>最大盛土</th>'
            "<th>切土量</th><th>最大切土</th></tr></thead><tbody>%s</tbody></table></div>" % rows)


def mune_grading_table(d, step=0.5):
    """⭐ **棟ごとに「規則3(|設計面 − 自然地形| ≤ 0.5m)」を測る**(2026-09-01 検図 中7)。

    ⛔ 段全体の割合だけでは、**どの棟が盛土に載るか**が図に出ない。
      2026-08-23 のユーザー裁定「御殿の一体性を採り主平面を一枚で通す」は
      **段全体の不合格 6% という数字の上で**下されており、棟別の数字は指図のどこにも無かった。
    ⭕ 裁定そのものは動かさない。⭕ **棟別の数字を出して、再確認の要否をユーザーが判断できる形**にする。
    ⚠ 測るのは棟の外形を 0.5間 刻みで走査した標本(⛔ 指図には持たせない)。"""
    terr = _terr_json()
    lim = 0.5
    rows, tot, over = "", 0, 0
    recs = []
    for m in d["munes"] + d["service"]:
        n = bad = 0
        mx = 0.0
        u = m["u0"] + step / 2.0
        while u < m["u1"]:
            v = m["v0"] + step / 2.0
            while v < m["v1"]:
                nat = _nat_uv(terr, round(u), round(v))
                if nat is not None:
                    dz = float(m["y"]) - nat
                    n += 1
                    if abs(dz) > lim:
                        bad += 1
                    if abs(dz) > abs(mx):
                        mx = dz
                v += step
            u += step
        if n:
            recs.append((m, n, bad, mx))
            tot += n
            over += bad
    for (m, n, bad, mx) in sorted(recs, key=lambda r: -(r[2] / float(r[1]))):
        lb = MUNE_JA.get(m["name"], m.get("label", m["name"]))
        rows += ("<tr><td>%s</td><td>%.1f m</td><td>%d</td><td>%d</td>"
                 "<td><b>%.1f %%</b></td><td><b>%+.2f m</b></td></tr>"
                 % (lb, float(m["y"]), n, bad, 100.0 * bad / n, mx))
    return ('<h3>棟別の造成 — <b>規則3(|設計面 − 自然地形| ≤ %.1fm)</b>を棟ごとに測る</h3>'
            '<div class="tw"><table><thead><tr><th>棟</th><th>面の高さ</th><th>標本</th>'
            "<th>%.1fm 超</th><th>割合</th><th>最大Δ(+は盛土)</th></tr></thead>"
            "<tbody>%s<tr><td><b>計</b></td><td></td><td><b>%d</b></td><td><b>%d</b></td>"
            "<td><b>%.1f %%</b></td><td></td></tr></tbody></table></div>"
            "<p class='cap'>⚠ <b>この表は 2026-08-23 のユーザー裁定の帰結を棟別に開いたもの</b>"
            "(検図 2026-09-01 中7)。裁定は<b>「御殿の一体性を採り、主平面を一枚で通す」</b>で、"
            "⛔ <b>裁定そのものは動かさない</b>。⚠ ただし裁定は<b>段全体の割合</b>の上で下されており、"
            "<b>棟別の数字が指図のどこにも出ていなかった</b> — 一枚の面で通すことの代償が"
            "どの棟にどれだけ乗るかは、この表で読む。<br>"
            "⭕ <b>再確認が要るかどうかはユーザーが決める</b>(指図方も検図方も裁定を覆さない)。"
            "⚠ 面を割る案を採るなら、御殿の入側の通し・屋根の谷・動線がすべて連動する"
            "(屋根伏図と谷・動線の図)。</p>"
            % (lim, lim, rows, tot, over, 100.0 * over / max(1, tot)))


# ---------------------------------------------------------------- 屋根伏図と谷
GABLE_FRAC = 0.45          # 破風の立上り比(Tools/Blender/build_goten_roof.py の make_irimoya)


def _roof_geom(d, m):
    """棟の屋根の平面。谷になる辺には軒を出さない。→ (ru0, ru1, rv0, rv1, a, h)"""
    E = d["const"]["nokiE"] / d["const"]["ken"]                 # 軒の出[間]
    V = [t for t in d.get("valleys", []) if t.get("axis", "v") == "v"]   # 妻谷だけが軒を落とす
    noW = set(t["east"] for t in V)                             # 西辺が谷になる棟
    noE = set(t["west"] for t in V)                             # 東辺が谷になる棟
    ru0 = m["u0"] - (0.0 if m["name"] in noW else E)
    ru1 = m["u1"] + (0.0 if m["name"] in noE else E)
    rv0, rv1 = m["v0"] - E, m["v1"] + E
    a = GABLE_FRAC * (rv1 - rv0) / 2.0                          # 破風の入り込み[間]
    h = (rv1 - rv0) / 2.0 * d["const"]["ken"] * d["const"]["roofRatio"]   # 軒先→大棟[m]
    return ru0, ru1, rv0, rv1, a, h


def roof_plan_svg(d):
    """屋根伏図 — 大棟・隅棟・破風・谷。棟の間数は動かさず、谷の辺の軒だけ落とす。"""
    u0, u1, v0, v1 = -52, 16, 12, 66
    pr = LProj(u0, u1, v0, v1, 900.0)
    g = _sv(pr.W, pr.H, "松平出羽守上屋敷 屋根伏図")
    g.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))

    for m in d["munes"]:
        if m["v1"] < v0 or m["v0"] > v1 or m["u1"] < u0 or m["u0"] > u1:
            continue
        ru0, ru1, rv0, rv1, a, h = _roof_geom(d, m)
        vc = (rv0 + rv1) / 2.0
        X, Y = pr.X, pr.Y
        g.append(pr.rect(ru0, rv0, ru1, rv1, fill="var(--paper)", stroke="var(--ink)", sw=1.1))
        # 隅棟(45°) → 破風の端
        for (cx, cy, gx, gy) in ((ru0, rv0, ru0 + a, rv0 + a), (ru0, rv1, ru0 + a, rv1 - a),
                                 (ru1, rv0, ru1 - a, rv0 + a), (ru1, rv1, ru1 - a, rv1 - a)):
            g.append(LN(X(cx), Y(cy), X(gx), Y(gy), "var(--ink)", 0.8, op=0.75))
        # 破風(妻)
        for gx in (ru0 + a, ru1 - a):
            if ru0 + a < ru1 - a:
                g.append(LN(X(gx), Y(rv0 + a), X(gx), Y(rv1 - a), "var(--ink)", 1.4, op=0.9))
        # 大棟
        if ru0 + a < ru1 - a:
            g.append(LN(X(ru0 + a), Y(vc), X(ru1 - a), Y(vc), "var(--ink)", 2.6, cap="round"))
        nm = MUNE_JA.get(m["name"], m["name"])
        g.append(T((X(ru0) + X(ru1)) / 2, Y(vc) - 5, nm, "rmS", "middle",
                   fit(nm, pr.L(ru1 - ru0), 11.0)))
        g.append(T((X(ru0) + X(ru1)) / 2, Y(vc) + 10, "大棟 +%.2f" % h, "anS", "middle", 8.5))

    # 谷 — 妻谷は v 方向、軒谷は u 方向へ走る
    E = d["const"]["nokiE"] / d["const"]["ken"]
    _labelled = set()
    for t in d.get("valleys", []):
        if t.get("axis", "v") == "v":
            a = (pr.X(t["u"]), pr.Y(t["v0"] - E)), (pr.X(t["u"]), pr.Y(t["v1"] + E))
        else:
            a = (pr.X(t["u0"]), pr.Y(t["v"])), (pr.X(t["u1"]), pr.Y(t["v"]))
        (x0, y0), (x1, y1) = a
        g.append(LN(x0, y0, x1, y1, "var(--shu)", 3.4, cap="round"))
        xm, ym = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        for (ex, ey) in ((x0, y0), (x1, y1)):                    # 中央から両端へ落とす
            dx, dy = (ex - xm), (ey - ym)
            L = max(1e-6, (dx * dx + dy * dy) ** 0.5)
            ux, uy = dx / L, dy / L
            nx2, ny2 = -uy * 4.5, ux * 4.5                       # 谷から少しずらす
            g.append(LN(xm + ux * 7 + nx2, ym + uy * 7 + ny2,
                        ex - ux * 5 + nx2, ey - uy * 5 + ny2, "var(--shu)", 0.9))
            tipx, tipy = ex - ux * 1 + nx2, ey - uy * 1 + ny2
            g.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="var(--shu)"/>'
                     % (tipx, tipy,
                        ex - ux * 5 + nx2 - ny2 * 0.45, ey - uy * 5 + ny2 + nx2 * 0.45,
                        ex - ux * 5 + nx2 + ny2 * 0.45, ey - uy * 5 + ny2 - nx2 * 0.45))
        if t.get("axis", "v") == "v":
            g.append(T(x0, y0 - 5, t["name"].replace("V_", "谷 "), "anS", "middle", 8.5,
                       "var(--shu)"))
        elif t["v"] not in _labelled:                            # 一続きの軒谷は一度だけ名を出す
            _labelled.add(t["v"])
            g.append(T(x0 - 4, y0 + 3, "軒谷(結界の帯)", "anS", "end", 8.5, "var(--shu)"))
    g.append("</svg>")
    return "".join(g)


def roof_section_svg(d):
    """屋根の縦断面(桁行) — 各棟の大棟通りで切って一列に展開。谷は軒先の高さで出会う。"""
    KEN = d["const"]["ken"]
    EAVE = d["const"]["gotenFloor"] + d["const"]["muneEave"]      # 面から軒先[m]
    ROWS = [("表向", [m for m in d["munes"]
                     if m.get("zone") in ("表向", "表役所") and m["name"] != "Umaya"]),
            ("奥向", [m for m in d["munes"] if m.get("zone") == "奥向" and m["name"] != "NagatsuboneS"])]
    su0, su1 = -48, 14
    s = 900.0 / (su1 - su0)                                      # px/間(水平・垂直とも実寸)
    mpx = s / KEN                                                # px/m
    rowH = 13.0 * mpx + 34
    g = _sv(900.0, rowH * len(ROWS) + 10, "松平出羽守上屋敷 屋根の縦断面")
    g.append(R(0, 0, 900.0, rowH * len(ROWS) + 10, fill="var(--paper2)"))
    X = lambda u: (u - su0) * s
    for ri, (label, ms) in enumerate(ROWS):
        base = rowH * (ri + 1) - 12                              # 面(y=27.0)の線
        Y = lambda z: base - z * mpx
        g.append(LN(0, base, 900.0, base, "var(--ink)", 1.0, op=0.5))
        g.append(T(4, base + 10, "%s — 面 27.0" % label, "anS", "start", 9.0))
        for m in sorted(ms, key=lambda q: q["u0"]):
            ru0, ru1, rv0, rv1, a, h = _roof_geom(d, m)
            hb = GABLE_FRAC * h
            pts = [(ru0, EAVE), (ru0 + a, EAVE + hb), (ru0 + a, EAVE + h),
                   (ru1 - a, EAVE + h), (ru1 - a, EAVE + hb), (ru1, EAVE)]
            g.append('<polygon points="%s" fill="var(--paper)" stroke="var(--ink)" '
                     'stroke-width="1.2"/>' % " ".join("%.1f,%.1f" % (X(u), Y(z)) for u, z in pts))
            # 軒下(壁と入側)
            g.append(R(X(m["u0"]), Y(EAVE), X(m["u1"]) - X(m["u0"]), EAVE * mpx,
                       fill="var(--paper)", stroke="var(--ink)", sw=0.7, op=0.9))
            g.append(T((X(ru0) + X(ru1)) / 2, Y(EAVE + h) - 4,
                       "%.2f" % (EAVE + h), "anS", "middle", 8.5))
            nm = MUNE_JA.get(m["name"], m["name"])
            g.append(T((X(m["u0"]) + X(m["u1"])) / 2, Y(EAVE) + 13, nm, "rmS", "middle",
                       fit(nm, (X(m["u1"]) - X(m["u0"])), 10.0)))
        for t in d.get("valleys", []):
            if t.get("axis", "v") != "v" or t["west"] not in [q["name"] for q in ms]:
                continue
            g.append(LN(X(t["u"]), Y(EAVE) - 3, X(t["u"]), Y(EAVE) + 6, "var(--shu)", 2.4))
            g.append(T(X(t["u"]), Y(EAVE) - 7, "谷", "anS", "middle", 9.0, "var(--shu)"))
    g.append("</svg>")
    return "".join(g)


def valleys_table(d):
    if not d.get("valleys"):
        return ""
    E = d["const"]["nokiE"] / d["const"]["ken"]
    KEN = d["const"]["ken"]
    r = ""
    for t in d["valleys"]:
        if t.get("axis", "v") == "v":
            L = ((t["v1"] - t["v0"]) + 2 * E) * KEN
            rng = "u %g ／ v %g 〜 %g" % (t["u"], t["v0"], t["v1"])
            side = "%s +%.2f ／ %s +%.2f" % (MUNE_JA.get(t["west"], t["west"]), t["hW"],
                                             MUNE_JA.get(t["east"], t["east"]), t["hE"])
        else:
            L = (t["u1"] - t["u0"]) * KEN
            rng = "v %g ／ u %.1f 〜 %.1f" % (t["v"], t["u0"], t["u1"])
            side = "%s +%.2f ／ %s +%.2f" % (MUNE_JA.get(t["north"], t["north"]), t["hN"],
                                             MUNE_JA.get(t["south"], t["south"]), t["hS"])
        r += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%.1f m</td><td>%s</td>"
              "<td class='note'>%s</td></tr>"
              % (t["name"], t["kind"], rng, L, side, t["fall"]))
    return ("<h3>谷</h3><div class='tw'><table><thead><tr><th>谷</th><th>種</th><th>位置</th>"
            "<th>樋の長さ</th><th>両側の大棟(軒先から)</th><th class='note'>水の落とし方</th>"
            "</tr></thead><tbody>%s</tbody></table></div>" % r)



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
    dem = json.load(open(os.path.join(DOC, "matsudaira_dewa_dem.json"), encoding="utf-8"))
    DAN = dan_map(d)
    # ⭐ **`eye` を持たない主視点の眼高を、下の設計地盤+姿勢から埋める**(⛔ 指図に眼高を直書きさせない)
    fill_viewpoint_eyes(d)
    terr = json.load(open(os.path.join(DOC, "matsudaira_dewa_terrain.json"), encoding="utf-8"))
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
    nbad = nakajikiri_containment_check(d)
    if nbad:
        print("⚠ 中仕切塀の区画はみ出し %d 件:" % len(nbad))
        for b in nbad:
            print("   ", b)
    pbad = plane_check(d)
    if pbad:
        print("⚠ 面のはみ出し %d 件:" % len(pbad))
        for b in pbad:
            print("   ", b)
    # 外周の閉じは**件数を必ず出す。**0 件でないなら理由を添える(黙って通さない)。
    cbad = perimeter_closure_check(d)
    lbad = perimeter_ledger_check(d)
    print("外周の閉じ: 面の当たり %d 件 / 帳簿(頂点・辺・宣言) %d 件" % (len(cbad), len(lbad)))
    for b in cbad + lbad:
        print("   ⚠", b)
    # 石垣の割り付けも**件数を無条件に出す**。0 件を黙って通さない(qa-and-pitfalls)。
    ibad = ishigaki_layout_check(d)
    nrun = len([r for r in d["runs"] if r.get("base") == "Ishigaki"])
    print("石垣基壇の割り付け(基壇つき %d run): %d 件" % (nrun, len(ibad)))
    for b in ibad:
        print("   ⚠", b)
    ibase, iprobe = ishigaki_layout_sensitivity(d)
    print("  感度試験(素の件数 %d):" % ibase)
    for label, delta in iprobe:
        print("    %s %s → %+d 件" % ("○" if delta > 0 else "⛔鳴らない", label, delta))
    if any(delta <= 0 for _, delta in iprobe):
        print("    ⛔ 鳴らない probe がある = その壊れ方は検査で捕まらない。検査を直すこと")
    # 隅の腕も**件数を無条件に出す**(0 件を黙って通さない)。
    kbad = kado_arm_check(d)
    print("隅の腕(全 %d 頂点 — 実測との一致・隣の run の端・実装へ渡る形): %d 件"
          % (len(d["polygon"]), len(kbad)))
    for b in kbad:
        print("   ⚠", b)
    kbase, kprobe = kado_arm_sensitivity(d)
    print("  感度試験(素の件数 %d):" % kbase)
    for label, delta in kprobe:
        print("    %s %s → %+d 件" % ("○" if delta > 0 else "⛔鳴らない", label, delta))
    if any(delta <= 0 for _, delta in kprobe):
        print("    ⛔ 鳴らない probe がある = その壊れ方は検査で捕まらない。検査を直すこと")

    # 植栽も**件数を無条件に出す**(0 件を黙って通さない)。
    pb1 = planting_stock_check(d)
    pb2 = planting_clearance_check(d, dem)
    pb3 = slope_planting_check(d, dem)
    _pn, _ptri = plant_budget(d, dem)
    _area = slope_band_area(d, dem)
    print("植栽(木・株 %d 点 / %s 三角・斜面 %.0f m²): 在庫 %d 件 / 退避 %d 件 / 斜面の密度と遮蔽 %d 件"
          % (_pn, "{:,}".format(_ptri), sum(_area.values()), len(pb1), len(pb2), len(pb3)))
    for b in pb1 + pb2 + pb3:
        print("   ⚠", b)
    pbase, pprobe = planting_sensitivity(d, dem)
    print("  感度試験(素の件数 %d ／ 判定は**素に無かった文言が出たか**):" % pbase)
    for label, delta in pprobe:
        print("    %s %s → 新しい指摘 %+d 件" % ("○" if delta > 0 else "⛔鳴らない", label, delta))
    if any(delta <= 0 for _, delta in pprobe):
        print("    ⛔ 鳴らない probe がある = その壊れ方は検査で捕まらない。検査を直すこと")

    # ⭐ **⚠ を一箇所に集めて HTML にも載せる**【検図 2026-09-01 の指摘】。
    #   ⛔ 従前は stdout にしか出ておらず、**指図が自分の検査結果を持っていない図**だった
    #   (65行の ⚠ が artifact のどこにも無かった)。
    WARN = [("面・重なり・動線・段・水・庭(`plane_check` の束)", pbad),
            ("矩形の総当たり重なり", bad),
            ("中仕切塀の区画はみ出し", nbad),
            ("外周の閉じ(面の当たり)", cbad),
            ("外周の閉じ(帳簿)", lbad),
            ("石垣基壇の割り付け", ibad),
            ("隅の腕", kbad),
            ("植栽の在庫(部材が目録に無い)", pb1),
            ("植栽の退避", pb2),
            ("西斜面の密度と遮蔽", pb3)]
    NWARN = sum(len(x) for _t, x in WARN)

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()
    h = ['<meta charset="utf-8">', "<title>松平出羽守上屋敷 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">外桜田永田町 ／ 親藩国主・大広間 十八万六千石 上屋敷</p>')
    h.append("<h1>松平出羽守上屋敷 指図</h1>")
    h.append('<div class="box" style="border-color:var(--shu);margin-top:14px"><h3>基準年次と確度</h3><p>'
             '<b>「松平出羽守」は斉貴(〜嘉永6年9月)と定安(嘉永6年9月〜)のどちらも指す。</b>'
             '<b>シーンの基準年次は安政3年(1856)</b>(2026-08-29 ユーザー裁定)なので、'
             '<b>当主は定安</b>。⛔ 嘉永前半の斉貴についての記述を基準年次へ読み替えない。<br>'
             '<b>当屋敷の指図・絵図は散逸</b>(藩主家の史料自体が散逸)。表門まわりの部材・意匠は'
             '明治初期の実写真(江戸東京博物館 温古写真集11)から起こした<b>確度A</b>'
             '(表門=屋根なし冠木門+両唐破風番所【写真A+日本案内記A/安政3年への外挿はB】、位置=明治16年実測図【A寄りB】)。御殿の構成は<b>類型(確度B)</b>、'
             '室名・畳数は<b>想定(確度?)</b>。区画の多角形は<b>ユーザーのブックマーク角(確度U)</b>。'
             '石井戸枠は存在A・奥庭という位置は?。</p></div>')
    h.append('<p class="lede"><b>この文書は現況だけを載せる。</b>過去の案・撤回した説は書かない — '
             '経緯は <code>git log docs/Sashizu/</code> で追う。'
             '寸法の正典は <code>matsudaira_dewa_sashizu.json</code>、文章は <code>matsudaira_dewa_kosho.md</code>、'
             'この HTML は <code>Tools/Sashizu/build_matsudaira_dewa_sashizu.py</code> が組む。'
             '<b>数値をこの文書に書き足さないこと。</b></p>')
    h.append('<div class="box"><h3>作る順序</h3><p>'
             '① 設計=<code>json</code>/<code>md</code> を直す → ② 組む → ③ 検図(edo-kosho / edo-kenzu / edo-niwashi)'
             '→ ユーザーのレビュー → ④ 実装 → ⑤ 指図と実装を突き合わせて 0 件 → ⑥ 経緯はコミットへ。</p></div>')
    # ⭐ **この指図が自分の検査結果を持つ**(2026-09-01 第3次・検図の指摘)
    #   ⚠ **箱は最後に埋める。**図版の採番を見る検査(`plate_ref_check`)は、
    #     図版を全部組んだ後でないと回せない — 場所だけ取っておいて末尾で差し替える。
    _WARNPOS = len(h)
    h.append("")

    KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
           "其十一", "其十二", "其十三", "其十四", "其十五",
           "其十六", "其十七", "其十八", "其十九", "其二十",
           "其廿一", "其廿二", "其廿三", "其廿四", "其廿五",
           "其廿六", "其廿七", "其廿八", "其廿九", "其三十",
           # ⚠ 図版を足すと後ろが全部ずれる。**番号を本文へ直書きしない**
           #   (2026-08-30: 植栽で4面足したら「池の裁定は其廿二」が別の図を指した)。
           "其卅一", "其卅二", "其卅三", "其卅四", "其卅五",
           "其卅六", "其卅七", "其卅八", "其卅九", "其四十"]
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
            "【確度B — 溜池の水辺の樹木は松、竹薮は江戸の水辺79事例中1例。西斜面の林の図と考証の章】。"
            "鞍部の盛土(量は段の note を正とする)で表長屋の石垣基壇が大通りへ露出する。"
            "西斜面の近代掘削の埋め戻しは拝領時造成と別勘定の復元【出自判定は ?】。"
            "<b>街路・隣地への影響はゼロ</b> — 面の造成は区画線で切り(図の色もその形)、"
            "境界の高低差は垂直の基壇石垣で受けるので、法尻が道や隣地へ出ることもない。")
    h.append(planes_table(d))
    # ⚠ 斜面の3帯は**植栽の図版**で面積・密度つきの表に出す(slope_table は旧い形の1行表)。
    #   ここで二重に出さない — 数字が二箇所に出ると片方が古くなる。
    h.append('<p class="cap">斜面の植生の3帯(法肩〜上部/中部/下部〜裾)は'
             '<b>「西斜面の林」の図版</b>に、帯ごとの平面積・本数・密度つきで出す。</p>')
    h.append('<p class="cap"><b>面のはみ出し検査(0.5間刻みの被覆・区画内包も判定): %s。</b>'
             '棟・付属屋・廊下は自分の y と同じ高さの段の中に、庭・井戸はいずれかの段の中に'
             '完全に載っていること+**区画多角形の内側にあること**を機械検査している'
             '(造成しない斜面に載る庭=西庭の斜面部だけ除外)。'
             '<b>矩形の総当たり重なり: %s。</b>'
             '<b>中仕切塀の区画はみ出し(線分の途中も0.5%%刻みで測る): %s。</b></p>'
             % ("<b>0 件</b>" if not pbad else "⚠ %d 件 — %s" % (len(pbad), " / ".join(pbad)),
                "<b>0 件</b>" if not bad else "⚠ %d 件" % len(bad),
                "<b>0 件</b>" if not nbad else "⚠ %d 件 — %s" % (len(nbad), " / ".join(nbad))))
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
    h.append(mune_grading_table(d))
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
            "御成を受けた加賀本郷邸の幕末プランにも御成門は無い(考証の章)。")
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
    if d.get("kenzan"):
        K2 = d["const"]["ken"]
        om = [m for m in d["munes"] if m.get("zone") == "表向" and m["name"] != "Umaya"]
        al = [m for m in d["munes"] if m["name"] != "Umaya"]
        f = lambda ms: sum((m["u1"] - m["u0"]) * (m["v1"] - m["v0"]) for m in ms)
        area2 = abs(sum(d["polygon"][i][0] * d["polygon"][(i + 1) % len(d["polygon"])][1]
                        - d["polygon"][(i + 1) % len(d["polygon"])][0] * d["polygon"][i][1]
                        for i in range(len(d["polygon"])))) / 2.0 / TSUBO
        rows = ("<tr><td>当図 表向(玄関・大広間・黒書院・表役所)</td><td>%.0f 坪</td>"
                "<td>%.0f 坪</td><td>%.1f %%</td><td class='note'>—</td></tr>"
                "<tr><td>当図 御殿計(厩を除く)</td><td>%.0f 坪 / %.0f 畳</td><td>%.0f 坪</td>"
                "<td>%.1f %%</td><td class='note'>—</td></tr>"
                % (f(om), area2, 100.0 * f(om) / area2,
                   f(al), f(al) * 2, area2, 100.0 * f(al) / area2))
        for r in d["kenzan"]["refs"]:
            rows += ("<tr><td>%s</td><td>%s 坪</td><td>%s</td><td>%s</td>"
                     "<td class='note'>%s</td></tr>"
                     % (r["name"], format(r["hyo"], ","),
                        (format(r["shikichi"], ",") + " 坪") if r["shikichi"] else "—",
                        ("%.1f %%" % (100.0 * r["hyo"] / r["shikichi"])) if r["shikichi"] else "—",
                        r["_"]))
        h.append("<h3>御殿の総量 — 格の検算</h3><div class='tw'><table><thead><tr>"
                 "<th>対象</th><th>御殿</th><th>敷地</th><th>比</th><th class='note'>注記</th>"
                 "</tr></thead><tbody>%s</tbody></table></div>" % rows)
        h.append("<p class='cap'>%s</p>" % d["kenzan"]["note"])
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

    plate(h, nx(), "屋根伏図と谷", "大棟は桁行(u)に架かる ／ 軒の出 0.90m ／ 5.5寸勾配(0.5456)")
    fig(h, roof_plan_svg(d),
        legend='<span>━ 大棟</span><span>─ 隅棟・破風</span>'
               '<span style="color:var(--shu)">━ 妻谷(列の中) ／ ━ 軒谷(行と行の間) ／ ↓ 水の流れ</span>',
        cap="<b>棟は入側の外縁で接していて、壁は共有しない。</b>各棟の大棟は桁行=u に架かるので、"
            "接合部では<b>両棟の妻側の屋根面が向かい合い、谷になる</b>。"
            "<b>谷の辺には軒を出さない</b>(両棟とも外形の縁で切る) — こうすると屋根面は軒先の高さのまま"
            "突き合い、そこに谷樋が走る。<b>棟の間数は一つも動かない。</b>"
            "⛔ <b>棟を離して渡廊下を挟む案(2026-08-26 の暫定裁定A)は撤回した</b>【ユーザー裁定U 2026-08-27】 — "
            "離すと入側1間＋渡廊下＋入側1間で廊下の帯が4間(7.3m)になり廊下として広すぎる。"
            "一間の隙間では渡廊下の屋根が両隣の軒に完全に隠れる"
            "(<code>buildings.md</code>「渡廊下は1間では成立しない」)。"
            "渡廊下は<b>離れた棟をつなぐ部材</b>であって、連なる棟の継ぎ目に使うものではない。<br>"
            "<b>谷は二種。</b>①<b>妻谷</b>=列の中で妻側の屋根面が向かい合う所(表向3・奥向3)。"
            "軒を出さずに突き合わせる。②<b>軒谷</b>=中奥と奥向が<b>結界の帯(1間)</b>を挟んで"
            "平行な長辺の軒で向かい合う所(5区間・計69m)。ここは軒の出 0.90×2 が帯をほぼ埋めて"
            "<b>18mm で出会う</b>ので、軒はそのままにして合わせ目の下へ樋を寄せて吊る。"
            "帯の下を通るのは御錠口と御膳所口だけで、渡廊下は架けない。")
    fig(h, roof_section_svg(d),
        cap="<b>屋根の縦断面(桁行)。</b>棟ごとに大棟通りで切って一列に展開した"
            "(棟の奥行が違うので大棟の通りも 1間 ずれる)。"
            "谷は<b>軒先の高さ</b>で出会い、そこから両側の屋根が登る。"
            "大棟の高さは梁間で決まるので、奥行 14間 と 12間 が交互に並ぶ表向は"
            "<b>大棟が約 1m 上下する</b>。")
    h.append(valleys_table(d))
    h.append("<p class='cap'><b>谷樋は縦樋を立てず、両端の軒先へ落とす</b>【確度P=一般類型】。"
             "勾配は中央から両端へ 1/100。屋根部材は<b>辺ごとに軒の出を落とせる版</b>が要る"
             "(現行の <code>build_goten_roof.py</code> は W'=W+2E の対称生成) — 部材表を参照。</p>")
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
                   "量もこの精度で読むこと。" if s.get("naturalProvisional") else "")
            + ("<br>" + inline(s["_"]) if s.get("_") else ""))
        h.append(cutfill_table(d, s))
        h.append("</div>")

    plate(h, nx(), "動線", "門を入ってからどう動く想定か(§3d)")
    fig(h, routes_svg(d),
        legend='<span style="color:#a8452c">━ 表向(客・使者)</span><span style="color:#3d6ea8">━ 役方(日勤)</span>'
               '<span style="color:#7a5c3a">━ 勝手(賄・物資)</span><span style="color:#5f7a4e">━ 奥向</span>'
               '<span style="color:#7a6a3d">╌ 園路(庭道・2026-09-01 新設)</span>',
        cap="平面と断面だけでは<b>建てた後に人がどう動くか</b>が読めない。"
            "<b>勝手の動線は御蔵門から引いた</b> — これが無いと米も薪も表門から入ることになる。"
            "奥向へ入る経路は<b>御錠口ただ一本</b>で、表・勝手とは交わらない。")
    h.append(routes_table(d, dem))
    h.append(garden_steps_table(d))
    h.append("</div>")

    # ------------------------------------------------------------ 主庭(2026-09-01)
    if d.get("sensui"):
        plate(h, nx(), "主庭の平面(御泉水・築山・園路・主視点)",
              "**池を掘る**【裁定=U(ユーザー 2026-09-01 改)/ 史実の裏づけ=B】")
        fig(h, shutei_plan_svg(d, dem),
            legend='<span style="color:#3f6a80">▨ 御泉水(水面)</span>'
                   '<span style="color:#6b6446">▨ 中島(磯島)</span>'
                   '<span style="color:#8a7f52">▨ 築山(等高の輪 t=0.25/0.5/0.75/裾)</span>'
                   '<span style="color:#7a6a3d">╌ 園路(庭道)</span>'
                   '<span style="color:var(--shu)">● 点景 ／ ○ 主視点と視線</span>'
                   '<span style="color:#3B5A3C">○ 樹冠の実寸</span>',
            cap="<b>★V1(御休息之間)が主景。</b>中奥は四方入側なので"
                "<b>西入側がこの庭へ正面から向く</b> — 屋敷で唯一そう作れる場所。"
                "汀線の番号は <code>sensui.pond.outline</code> の順で、"
                "<b>#5 岬の付け根に傾ける松ただ一本</b>(幹を池の中心へ 8°)。"
                "⭐ <b>汀線 22点は A案(枯池)から一点も動いていない</b> — "
                "A案は B案の輪郭を枯池に流用したもので、戻したのは中身だけ。"
                "⭐ <b>池底の澪筋</b>(破線と薄い帯)は水の下で、落ち口から水尻へ流れを一筋に通す。"
                "⚠ 木の<b>位置は設計値ではない</b>(規則・本数・部材・退避・<b>塊の置き場所</b>が設計値)。")
        h.append("<h3>主視点【すべて確度 P/B=類型。当屋敷の一次史料は無い】</h3>")
        h.append(viewpoints_table(d))
        h.append("<p class='cap'>⭐ <b>真行草</b>: 白洲・前庭=<b>真</b> / 主庭=<b>行</b> / "
                 "露地=<b>草</b>(『築山庭造伝』の三体)。"
                 "方位は grid の回転から出る<b>従属値</b>なので指図には持たせない。"
                 "⭐ <b>V8(滝見の床几)は B案で新設</b> — 台地端の滝を見る場所で、"
                 "中仕切塀に開けた滝見口 <code>NJ_Taki_Kido</code> から降りる。</p>")
        h.append("<h3>庭の姿の代理指標 — <b>すべて生成器の実測</b>(⛔ 指図に書かない)</h3>")
        h.append(sensui_metrics_table(d))
        h.append("<h3>築山 — 面積と土量は<b>造成前 DEM から測る</b>(指図に書かない)</h3>")
        h.append(tsukiyama_table(d, dem))
        h.append(tsukiyama_do_table(d, dem, _cf_stats))
        h.append("<p class='cap'>⭐ <b>B案で『池を掘りたる土をもって山を築く』"
                 "([築山庭造伝])が成立した</b>(設計値は <code>tsukiyama.M_Tsukiyama.do</code>)— "
                 "<b>A案の『主郭東翼から 90〜200m 運ぶ』は丸ごと不要</b>になり、"
                 "池を掘った土だけで築山・岬の復旧・中島の盛り・滝の背山を賄って<b>なお余る</b>。"
                 "余りは主庭・西庭の野筋へ均す。"
                 "⛔ 復元レイヤ(近代掘削跡の埋め戻し)の客土からは相変わらず回さない。"
                 "⭐ <b>法は輪郭と地盤から出る従属値</b>で、"
                 "<code>batter.measure</code> と上の実測を突き合わせている。"
                 "⛔ 注記に法の数値を書き写さない(規則4)。</p>")
        h.append("<h3>御泉水の護岸 — <b>天端は設計値・見え面は水面から測る</b></h3>")
        h.append(gogan_table(d))
        h.append("<p class='cap'>⭐ <b>A案の診断『遠い対岸ほど石を大きく』は B案で取り下げた</b>"
                 "(庭方 2026-09-01 設計4)— 枯池では見え面が掘り下げ 0.45m しか無かったので"
                 "石を大きくするしか手が無かったが、"
                 "<b>水の池は汀の立ち上がりが 0.95m あり、23m 先の俯角 2.3° でも 2.4°分の帯として"
                 "読める(枯池 0.45m の 2.1倍)。加えて水面が対岸の石を映して見かけの量を倍にする。</b>"
                 "⛔ <b>したがって発掘の寸法帯(常石 1.20 / 役石 1.50m)を超えて大きくする必要は"
                 "もう無く、超えてはいけない</b>(検査が鳴る)。<br>"
                 "⭕ <b>A案から残したのは二つ</b> — ①汀を「対岸 #11→#21 / 手前 #21→#11」に割ること "
                 "②<code>topJitter</code> を廃して天端を設計値にすること。"
                 "⭐ 据え付けは <b>輪郭点そのものではなく</b>"
                 "「外向きに進んで最初に地面が水面を超える点」(<code>gogan.seatRule</code>)。</p>")
        plate(h, nx(), "主庭の見通し — V1 の断面",
              "**垂直・水平とも実寸**(見通しの当たりを目で取るため)/ ⛔ 溜池は借景に取れない")
        fig(h, shutei_section_svg(d, dem),
            cap="<b>V1 から西を見た断面。</b>前景=沓脱石と水面、中景=御泉水と築山、"
                "遠景=西斜面の樹林。⛔ <b>溜池の水面は見えない</b> — "
                "眼から出た見通しの線は西の自然の肩に切られ、その線より下はすべて隠れる。"
                "「西に溜池があるから借景」という誤解を断つためにこの断面を置く。"
                "⭕ ただし<b>水は溜池へ抜ける</b>(水尻 → 暗渠 → 台地端の滝 → 南西の谷 → "
                "区画の南西の出口 P4 → 区画外の谷)— "
                "貞享4年『江戸鹿子』の「滝の末は赤坂の溜池へ落ち」と一致する。")
        h.append("</div>")

        if d.get("gardenSections"):
            plate(h, nx(), "庭の斜め断面 — 板塀の足元は納まるか",
                  "**垂直・水平とも実寸** ／ `sections` は u/v 軸に平行なものだけなので斜めはここ")
            for gsx in d["gardenSections"]:
                fig(h, garden_section_svg(d, dem, gsx),
                    cap="<b>%s。</b>眼から出て<b>仰角が最大の地物</b>を掠める"
                        "<b>見切り線</b>を、板塀の位置まで延ばして足元との差を測る。"
                        "⚠ <b>2026-09-02(第4次)に遮蔽体の取り方を直した</b>【庭方 回答4】— "
                        "護岸石の天端を採ると線が<b>汀の内側の地山に潜って</b>塀へ届く"
                        "(破線が黒い地山を貫いていた)。正しい遮蔽体は<b>汀の地盤の稜</b>で、"
                        "汀と塀のあいだは平場が連続するので<b>見えるのは根石の見え面だけ</b>。"
                        "⛔ 設計は一つも動かない。"
                        % inline(gsx["name"]))
            h.append(neishi_table(d, dem))
            h.append("<p class='cap'>⛔ <b>この判定は主庭の V1 断面(−u 真西)ではできない</b> — "
                     "板塀は真西の断面に<b>最初から載らない</b>(2026-09-01 庭方 6-①)。"
                     "⚠ この図と表は 2026-09-01 の第3次まで<b>書かれていたのに "
                     "<code>main()</code> から呼ばれておらず</b>、判定の図が artifact に"
                     "存在しなかった(検図 高5)。</p>")
            h.append("</div>")

        plate(h, nx(), "水の系 — 取入口から溜池まで(縦断)",
              "**余水は敷地内で消えず、溜池へ抜ける** ／ 玉川上水の分水【型=B / 位置=U】")
        fig(h, mizu_profile_svg(d),
            cap="<b>取入口(玉川上水の分水枡)から区画の南西の出口 P4 まで、"
                "水面の高さを一列に並べた縦断。</b>"
                "⭐ <b>A案のときの難点『水尻の行き先が谷で余水吐が敷地内で消える』は前提が誤りだった</b> — "
                "現況 20.1m の窪みは <code>Fukugen</code> の段(1883年以降の掘削跡)で、"
                "埋め戻して 27.0 に復す対象。埋め戻した後に水が向かうのは"
                "<b>南西の谷</b>(谷底が 24.1 → 10.0 と連続して下る自然の谷)で、"
                "出口は<b>区画の南西の出口 P4</b>で、その先は区画外の谷を下って汀へ達する。"
                "⭐ 1687年『江戸鹿子』の「<b>滝の末は赤坂の溜池へ落ち</b>」と一致する。")
        h.append(mizu_table(d))
        h.append("<h3>台地端の滝(三段)— <b>下端が自然地盤に載っているか</b></h3>")
        h.append(taki_table(d))
        h.append("<p class='cap'>⭐ <b>確度は三段に割る</b>(考証方 2026-09-01)— "
                 "①上水が邸へ来ていた(基準年次)= <b>B</b> "
                 "②その上水が池へ給水していた = <b>B</b>"
                 "(一般則の 73% ではなく<b>当邸の文化年間の記録が「上水樋と接続した池泉」と"
                 "明言している</b>ことに拠るので、他邸より強い)"
                 "③取入口 = 型 <b>B</b>(隣接同型実例 [内藤2024] の松平安藝守/春秋園=当邸と同じ"
                 "淀橋台南東縁 <b>A</b> + 一般則 <b>A</b> からの外挿)/ "
                 "標高の高い側 <b>P</b>(造成前DEM 実測)/ <b>隅の指名 U</b>。<br>"
                 "⛔ <b>『玉川上水留』を追っても位置は出ない</b> — [内藤2024] 自身が"
                 "「同書から引くのは分水口断面の寸法比較だけで標高値は無い」と明言。"
                 "⭐ 絞り込みは東京都水道歴史館 <b>K0136「麹町区霞ヶ関町・永田町・三年町 上水樋線之図」</b>"
                 "の実見待ち(<code>_pending.torinyuguchi</code>)。"
                 "⛔ <b>①が B である以上、池そのものも B を超えない</b> — 指図のどこかで池を A と書かない。</p>")
        h.append("</div>")

        plate(h, nx(), "庭に道が通っているか",
              "座敷から見える庭に人が入れるか(§B-6)")
        h.append("<h3>庭に道が通っているか — 最寄りの園路・動線までの距離</h3>")
        h.append(garden_access_table(d))
        h.append("<p class='cap'>⛔ 2026-09-01 に庭方が<b>『座敷から見える庭は48坪、"
                 "そこに道が通っていない』</b>と不合格を出した項目。"
                 "明地(確度?)・白洲・供待・作業の庭は観賞の庭ではないので除いてある。"
                 "検査 <code>garden_access_check</code> が 20m 超の割合を見張る。</p>")
        h.append("</div>")

    if any(g["name"] == "G_NishiNiwa" for g in d["gardens"]):
        plate(h, nx(), "庭園図(西庭)",
              "露地・芝野・樹林・築山 ／ **西の帯には池を置かない**(池は主庭の一つだけ)")
        fig(h, garden_svg(d),
            cap="<b>敷地図の縮尺では飛石も植栽も読めないので庭だけを大縮尺で出す。</b>"
                "西の帯は御殿複合と崖の間に残る面で、<b>造成しない</b>(西縁 v15..36 だけ土留め TW_Nishi が受ける)。"
                "役所・奥御殿の西面がここに向き、竹垣の先は崖と溜池。"
                "⚠ <b>円は樹冠の実寸</b>(<code>asset-index.tsv</code> の実測値)。"
                "木の<b>位置は設計値ではない</b> — 指図が決めるのは"
                "<b>規則・本数・部材・退避</b>で、図はその規則どおりに散らした"
                "<b>標本</b>。実装は同じ規則の別の乱数で散らすので位置は一致しない。"
                "<b>3・5・7 の奇数の塊で不等辺三角</b>に組む(等間隔に並べない)。")
        if d.get("planting"):
            h.append("<h3>植栽【すべて確度B=類型。当屋敷の一次史料は無い】</h3>")
            h.append(planting_table(d))
            h.append("<p class='cap'>※ <b>樹高・樹冠・三角数は <code>docs/asset-index.tsv</code> の"
                     "実測値</b>で、指図には持たせない(部材を差し替えたら自動で追従する)。"
                     "⚠ <b>(在庫に無い)</b> と出ている部材は<b>目録の焼き直し待ち</b> — "
                     "自作の木(<code>Own.Jouryoku</code> / <code>Own.Ume</code>)は Unity の "
                     "<code>Edo ▸ アセット目録 ▸ 目録を再生成</code> を回すまで実寸が引けない"
                     "(<code>_pending.mokuroku</code>)。図では「大きさ不明」の破線で描いてある。</p>")
            _n9, _t9 = plant_budget(d, dem)
            h.append("<p class='cap'>この指図が置く木・株の合計 <b>%d 点 / %s 三角</b>"
                     "(LOD0。在庫の木はすべて LOD を持つ)。⛔ 使用禁止の自作低ポリ(1本 2,384三角)は"
                     "在庫の同格 6,662〜24,701三角と<b>桁がひとつ違う</b>。</p>"
                     % (_n9, "{:,}".format(_t9)))
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

        plate(h, nx(), "庭園図(東庭・梅林・稲荷)",
              "奥庭(平庭)→ 梅林と宴の平場 → 稲荷の杜と鳥居2基 ／ **東の庭の平面図**")
        fig(h, garden_east_svg(d),
            legend='<span style="color:var(--niwa)">▨ 庭</span>'
                   '<span style="color:#7a6a55">━ 板塀(太い=根石が付く列)</span>'
                   '<span style="color:var(--shu)">━ 庭木戸 ／ ● 点景 ／ ○ 主視点</span>'
                   '<span style="color:#7a6a3d">╌ 園路(庭道)</span>'
                   '<span style="color:#3B5A3C">○ 樹冠の実寸</span>',
            cap="⚠ <b>この図は 2026-09-01 の第3次まで書かれていたのに "
                "<code>main()</code> から呼ばれていなかった</b>(検図 高4)。"
                "そのため<b>東の庭に平面図が1枚も無く</b>、奥庭・梅林・宴の平場・"
                "稲荷の杜と鳥居2基・台地端の滝が全部この穴に落ちていた。<br>"
                "<b>奥庭は平庭(ひらにわ)</b> — 高木を用いず、石・刈込・苔・下草で構成する"
                "([築山庭造伝]。奥御殿の座敷 <b>V2</b> から見る庭の形式)。"
                "<b>梅林は正月の宴の場</b>で、床几の据石から東へ稲荷の鳥居2基を見る(<b>V7</b>)。"
                "⚠ 円は<b>樹冠の実寸</b>で、木の<b>位置は設計値ではない</b> — "
                "指図が決めるのは規則・本数・部材・退避・<b>塊の置き場所</b>。")
        h.append("</div>")

    # ------------------------------------------------------------ 西斜面の林
    if d.get("slopePlanting"):
        plate(h, nx(), "西斜面の林(平面)",
              "溜池東岸へ落ちる法面 ／ 帯は法肩からの落差の割合 ／ **法面全体を樹林で埋めない**")
        fig(h, slope_plan_svg(d, dem),
            legend='<span style="color:#8CA86A">▨ 帯A 法肩〜上部(樹林)</span>'
                   '<span style="color:#C6C08A">▨ 帯B 中部(灌木と下草)</span>'
                   '<span style="color:#D9DCC4">▨ 帯C 下部〜裾(草地)</span>'
                   '<span style="color:var(--take)">╌ 法肩(竹垣 R_West/R_South の線)</span>'
                   '<span style="color:var(--nagaya)">━ 法尻(区画の西辺=堀端通り)</span>',
            cap="<b>『江戸名所図会』溜池の崖は 稜線=樹林 / 法面=ハッチング</b>で、"
                "<b>樹は稜線と法面上部に集まる</b>。それを帯の密度に落とした。"
                "⛔ <b>竹叢を置かない</b>(江戸の水辺79事例中1例)。"
                "⛔ ポプラ(在庫の広葉高木)は江戸に使えない。"
                "円は<b>樹冠の実寸</b>で、位置は規則どおりに散らした標本(設計値ではない)。")
        h.append(slope_band_table(d, dem))
        h.append(slope_planting_table(d, dem))
        plate(h, nx(), "西斜面の断面 — 林が御殿を隠せているか",
              "**垂直・水平とも実寸**(遮蔽の当たりを目で取るため)")
        for vc in (24.0, 40.0, 58.0):
            fig(h, slope_section_svg(d, dem, vc),
                cap="<b>v=%g の断面。</b>破線は対岸から御殿の軒への見通し。"
                    "法肩の樹がこの線を越えていれば御殿は隠れる。" % vc)
        _sc = d["slopeArea"]["screen"]
        h.append('<div class="box" style="border-color:var(--take)"><h3>遮蔽は法面だけでは足りない</h3><p>'
                 '<code>perimeterClosure</code> は西辺6辺を<b>「標示」</b>と宣言し、'
                 '「遮蔽は法面が受け、木柵は境の標示にとどまる」と書いている。'
                 'これは<b>法面と樹林</b>が受けるという意味で、素の崖だけでは対岸から御殿の軒が抜ける'
                 '(上の断面の見通し線)。⭐ そこで<b>法肩に沿った遮蔽の列</b>を設計値にした — '
                 '検査 <code>slope_planting_check</code> が法肩に沿って %.1fm ごとに'
                 '「樹高 %.1fm 以上の木が %.1fm 以内にあるか」を測り、'
                 '<b>切れていれば鳴る</b>。⚠ 落差 %.1fm 未満の区間(北西の登り・辺11)は外してある — '
                 'その内側は御殿でなく西の明地なので隠す物が無い。</p></div>'
                 % (_sc["step"], _sc["minH"], _sc["reach"], _sc["minDrop"]))
        h.append("</div>")

    # ------------------------------------------------------------ 裁定図(植栽の穴)
    if d.get("plantPending"):
        plate(h, nx(), "樹影くらべ — 在庫で埋まらない2つの穴【裁定要請】",
              "常緑広葉樹51本とウメ22本をどう埋めるか ／ **同じ縮尺で並べた図**")
        fig(h, tree_compare_svg(d),
            cap="<b>⛔ 一番左の『自作』は 2026-08-30 に使用禁止になった部材</b>"
                "(ユーザー指示「2度と使わないでください。見た目がしょぼすぎます」)。"
                "在庫の木と<b>同じ縮尺</b>で並べると、樹形の粗さと三角数の桁違いがそのまま出る。"
                "旧版の指図はこれを66本呼んでいた。")
        h.append(plant_pending_table(d))
        _n, _tri = plant_budget(d, dem)
        h.append("<p class='cap'>この指図が置く木・株の合計 <b>%d 点 / %s 三角</b>"
                 "(LOD0。在庫の木はすべて LOD を持つ)。"
                 "禁止部材は 1 本 2,384 三角で、在庫の同格は 6,662〜24,701 三角 — "
                 "<b>桁がひとつ違う</b>のが「しょぼい」の正体。</p>"
                 % (_n, "{:,}".format(_tri)))
        h.append("</div>")

    plate(h, nx(), "外周の展開", "天端は辺ごとに一本。段は門・頂点・郭境の延長線でのみ落とす")
    fig(h, perimeter_dev_svg(d))
    h.append(runs_table(d))
    h.append('<p class="cap">長屋は<b>表門の両翼と北東・東辺だけ</b>。南(土井境の台地上)と北辺西は練塀、'
             '<b>斜面・谷・水際は塀を立てず地形なりの木柵</b>(囲いの実体は崖と樹林+法肩の竹垣)。'
             '土井境の囲いは1条・松平が持つ(区画トポロジの裁定)。犬走り %.2fm。</p>'
             % d["const"]["inubashiri"])
    _ig = d["ishigaki"]
    h.append('<div class="box" style="border-color:var(--shu)"><h3>石垣基壇 — 駒は伸縮させない'
             '【ユーザー裁定U 2026-08-29】</h3><p>'
             '①1つの石垣オブジェクトの XYZ の長さは<b>変えない</b>(<code>scale</code> は全周で固定)／'
             '②run の長さは駒の<b>重なり</b>で合わせる／③石垣の高さは地面への<b>埋まり具合</b>で合わせる。<br>'
             '<code>runs[].base:"Ishigaki"</code> は「この run に基壇が付く」という宣言だけで、'
             '<b>駒の規模を run が持たない</b>。作法と実寸は設計値の <code>ishigaki</code> に一箇所だけ置き、'
             'ここにも図にも<b>数値を写さない</b>。割り付けの検算は生成器の '
             '<code>ishigaki_layout_check</code>(覆い・継ぎ目・露出の三本立て+感度試験)。<br>'
             '⛔ run ごとに駒を拡大縮小すると、隣り合う run で石の大きさが変わり、'
             '<b>ずれ量が駒の大きさに比例する</b>ので継ぎ目に隙間と食い込みが同時に出る。'
             '<code>runs</code> に <code>s</code> / <code>ishi</code> / <code>tiers</code> を'
             '書き戻したら検査が鳴る。</p></div>')
    fig(h, ishigaki_detail_svg(d, 12, 56.0, 112.0, "北辺 表門の西"),
        cap="<b>北辺(辺12)の s56〜112 — 練塀 <code>N_Hei_W3</code> と表長屋 <code>N_Nagaya_W</code> の継ぎ目(s75.8)。</b>"
            "旧作法ではこの一点で石の大きさが 2.1 倍変わり、実装に 0.66m の隙間が出ていた。"
            "駒を伸縮させないので、いまは両側とも同じ大きさの石が並び、継ぎ目は重なりで閉じる。")
    fig(h, ishigaki_detail_svg(d, 0, 24.0, 75.7, "土井境の東(段で登る区間)"),
        cap="<b>辺0 の s24〜75.7 — <code>S_Hei_E2</code> から <code>S_Hei_E3d</code> まで、"
            "水平な run を段で継いで登る区間。</b>座が段ごとに上がっても駒の大きさは変わらず、"
            "地面への埋まり具合だけが変わる。段の落差は石垣の小口で納める。")
    h.append("</div>")

    # ------------------------------------------------------------ 土井境の納まり
    _dem_s = json.load(open(os.path.join(DOC, "matsudaira_dewa_dem.json"), encoding="utf-8"))
    plate(h, nx(), "土井境の納まり", "隅は塀のてっぺんを揃える(2026-08-29 ユーザー裁定・EDO-0053)")
    h.append('<p class="cap">土井家との境の塀は、内側の自然地盤が高いので足元を 27.93m に置いている'
             '(2026-08-24。土井側と突き合わせて決めた高さで動かせない — EDO-0025)。'
             'その両隣の塀は 27.00m なので、<b>隅で 0.93m ずつ食い違っていた</b>。'
             '裁定により<b>隅では塀のてっぺんを揃え</b>、その差は隣の塀の中で段に割って吸わせる。<br>'
             '⛔ <b>塀は傾けない。</b>段ごとに水平な塀を継ぐ(瓦も柱も水平)。'
             'だから<b>一段は「読める大きさ」でなければならない</b> — 0.25〜0.60m を目安にする。'
             'これより小さい段は棟瓦の厚み(0.17m)を下回り、段ではなく据え付けのずれに見える'
             '(2026-08-29 に土井境で実測 0.06m 刻みが見つかった。EDO-0053)。</p>')
    fig(h, corner_elev_svg(d, _dem_s, 0, 28.0, 1, 10.0, "隅P1"),
        cap="<b>隅 P1(辺0 ↔ 辺1)。</b>東から来る塀が 0.31m ずつ三段で登り切って、土井境の塀と同じ高さで角を回る。"
            "塀そのものは段ごとに水平で、傾けない(瓦も柱も水平のまま)。段のぶん足元が浮くところは石垣が受ける。")
    fig(h, corner_elev_svg(d, _dem_s, 1, 15.0, 2, 14.0, "隅P2"),
        cap="<b>隅 P2(辺1 ↔ 辺2)。</b>角では同じ高さで、そこから西の塀が 0.31m ずつ三段で下って"
            "台地の肩(s12)で次の塀に継ぐ。角に段差は残らない。")
    fig(h, nagatsubone_svg(d),
        cap="<b>長局(南)。</b>屋根の先が土井境の塀に 0.28m まで迫っていたので、"
            "南の縁(入側)一列を落として離れを取った(2026-08-29 ユーザー裁定)。"
            "<b>局は一室も減っていない</b> — 落ちたのは縁だけで、残る縁は北(通り道)と両妻。"
            "奥郭の中仕切(板塀)は端を練塀へ 0.30m 差し込んで継ぐ(隙間を作らない)。")
    h.append("</div>")

    plate(h, nx(), "表門まわり", "冠木門(屋根なし)+両唐破風番所【写真A+日本案内記A/安政3年への外挿はB】")
    fig(h, gate_svg(d),
        cap="<b>江戸東京博物館 温古写真集11「旧雲州松江藩松平候上屋敷門」(88005761・明治初撮影)から。</b>"
            "昭和14年時点の現存5大名門の一つで、東京大空襲で焼失。"
            "屋根なし冠木門は焼失規定(焼失後は冠木門しか再建できず番所の唐破風で格式を示す)と整合 — "
            "切妻小屋根を載せる前案は撤回(2026-08-23)。当門の焼失・改築の年次が基準年次(安政3年)の前か後かが残る宿題。"
            "両唐破風番所は国持の格(加賀赤門・鳥取黒門と同格)。石垣畳出は親藩ゆえ制限外。")
    h.append("</div>")

    plate(h, nx(), "郭の土留めと竹垣")
    h.append(walls_table(d))
    h.append('<p class="cap">西斜面・南西の谷の法肩には<b>竹垣(四つ目垣)</b>を回す — '
             '落差のある生活面を素の縁にしない(岡部指図と同じ作法)。高さ0.9m・法肩から内へ0.45m。'
             '茶庭の縁もこの竹垣で、座敷と茶亭から溜池を垣越しに望む。</p>')
    h.append("</div>")

    # ------------------------------------------------------------ 取り合いの詳細(§3e/§3f)
    plate(h, nx(), "取り合いの詳細(開口と隅)",
          "全体設計では足りない粒度 — **どの面がどの面に接するか**を面の座標で決める")
    h.append('<p class="cap"><b>全体設計(開口の位置と幅)だけを渡すと、実装者は「中心を合わせる」しか'
             'できない。</b>2026-08-29 にそれが起きた — 門は開口の芯に、長屋は run の頭から丸ごとの'
             'モジュールを並べていて、<b>同じ門の左右で食い込みと隙間が同時に</b>出た。'
             'ユーザーの言葉「オブジェクト同士の位置関係は常に<b>どの点同士を接するか</b>を厳密に'
             '考えないと隙間が空く」。以下は<b>詳細設計</b>: 接する面を名前で決め、目標値と許容と'
             '<b>可動側</b>を書く。⛔ 芯・中心・ピボットで合わせない — 部材を差し替えた瞬間に破れる。</p>')
    fig(h, chain_strip_svg(d),
        cap="<b>長屋の割付。</b>表長屋は在庫部材の実寸でしか置けないので、鎖の長さは棟数×実寸で"
            "決まる。<b>固定端(▲)を開口・隅櫓・頂点の面に合わせ、端数は遊び端(○)の練塀が吸う。</b>"
            "鎖を run の中央へ寄せると、両端が同時に成り行きになる。")
    for key, cap in (("omote", "<b>表門。</b>番所は外周線から街路側へ張り出すので、外周線より内は"
                               "浅い。長屋のほうが奥行があり、番所の背後で長屋の妻が露出するのが正 — "
                               "塞ごうとして番所を深くしない。"),
                     ("Kuramon", "<b>御蔵門。</b>門柱の外面(開口の縁)へ長屋の妻面を突き付ける。"
                                 "門柱が妻壁へ浅くめり込むのは可、隙間は不可。"),
                     ("Higashi_Komon", "<b>東小門。</b>同じく開口の縁へ両側の長屋の妻面を突き付ける。"
                                       "鎖はこの面を起点に割り付け、端数は反対の端へ送る。")):
        fig(h, opening_detail_svg(d, key), cap=cap)
    for v, cap in ((0, "<b>隅 P0(敷地の南東の角)。</b>折れ角は直角ではないので、在庫の正規90°隅では"
                       "回らない — <b>実測の折れ角から起こした留め継ぎ</b>で回す。ここで囲いの種別が"
                       "変わる: 辺14 は腕の端面まで表長屋、腕から先が練塀。"),
                   (1, "<b>隅 P1(南辺の折れ)。</b>両側とも練塀。折れ角が浅く、小口どうしを"
                       "突き付けると外面に口が開くので留め継ぎで回す。"),
                   (2, "<b>隅 P2(土井境の南東の角)。</b>ここだけ<b>入隅</b>(区画が内へ切れ込む)で、"
                       "部材は鏡像。腕が旧 S_Hei_W0 を丸ごと兼ねるので、その run は廃した。"),
                   (3, "<b>隅 P3(土井境の折れ)。</b>入りの練塀が斜面を下るので、隅部材の座は"
                       "腕の付け根の天端を採る。段は腕の端に落ちる。"),
                   (13, "<b>隅 P13(北の隅)。</b>折れ角が浅いので<b>留め継ぎの隅部材</b>が要る — "
                        "小口どうしを突き付けると折れ角のぶんだけ隅に口が開く。ここで囲いの種別が"
                        "変わる: 腕の端面から東が表長屋。")):
        fig(h, corner_detail_svg(d, v, 15.0, "隅 P%d の取り合い" % v), cap=cap)
    fig(h, corner_detail_svg(d, 14, 15.0, "隅 P14(隅櫓 Y_NE)の取り合い"),
        cap="<b>隅櫓 Y_NE。</b>櫓は隅を<b>置き換える</b>(内側に重ねない)。辺と斜めに交わるので"
            "両脇に楔形が残り、その受けが袖塀。袖塀の小口は櫓の面と長屋の妻へ差し込む。")
    h.append(chains_table(d))
    h.append(joints_face_table(d))
    h.append(kado_measure_table(d))
    h.append(kado_parts_table(d))
    h.append('<div class="box"><h3>実装の順序(この詳細設計が効く工程)</h3><p>'
             'すべて<b>外周のステージ(塀・長屋・木柵)</b>の中で完結する。造成のステージには触れない '
             '(面の高さも run の天端も動かしていないので、<b>非冪等な造成を流し直す必要は無い</b>)。</p>'
             '<ol><li><b>先行</b>: 留め継ぎの隅部材を Blender で起こす(角度ごと。上表で「無い」と'
             '出ている分)。⛔ これを飛ばすと<b>隅だけが黙って建たない</b> — '
             '<code>LoadAssetAtPath</code> は例外を投げず null を返す。</li>'
             '<li><b>隅部材を頂点に据える</b>: 位置=頂点 / yaw=入りの辺の走り / '
             '<b>scale=ES</b> / y=座−0.10(直線材の沈めに合わせる)。'
             '<code>PlaceKado</code> は取り合いの <code>kado</code> を舐める。'
             '⛔ 素の単位のまま置くと丈が 1.46m に潰れる。</li>'
             '<li><b>固定側を先に置く</b>: 表門一式・御蔵門・東小門・隅櫓。位置は開口の芯と頂点の'
             '二等分線で決まる。</li>'
             '<li><b>可動側の鎖を割り付ける</b>: 上の「長屋の割付」の固定端から、駒を'
             '<b>面一で積む</b>(中央寄せをやめる)。端数は遊び端へ送る。</li>'
             '<li><b>練塀・袖塀を、鎖と隅部材の腕が空けた残りへ通す</b>。練塀の駒は伸縮するので'
             '端数をそのまま吸う。⛔ <b>腕の区間へ直線材を重ねない</b> — 腕は隅部材が持つ。</li>'
             '<li><b>置いたあと実メッシュから面を測って寄せる</b>(定数で寄せない)。'
             'ピボットが芯に無い・軒が出ている・スケールが掛かっている、のどれかで面は必ずずれる。</li>'
             '<li><b>面と面の距離を測って合否を出す</b>: 上の取り合い表の許容に入らなければ落とす。</li>'
             '</ol></div>')
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

    plate(h, nx(), "未解決と申し送り",
          "**判断を待っている項・宿題・記録・決着** ／ 正典は設計値の `_pending`(⛔ 散文で書き写さない)")
    h.append(pending_table(d))
    h.append("</div>")

    plate(h, nx(), "考証と決めごと")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, "改訂", "", "経緯はここに書かず git で追う")
    h.append(history())
    h.append("</div>")

    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>matsudaira_dewa_sashizu.json</code> ／ '
             '文章 <code>matsudaira_dewa_kosho.md</code>。Y は海抜 m(Unity の Y がそのまま標高)。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    # ⭐ **図版の採番を見る検査は、図版を全部組んだ後に回す**(2026-09-02 検図 中4)
    WARN.append(("図版番号の直書きと参照(`{{図:題}}`)", plate_ref_check(d)))
    NWARN = sum(len(x) for _t, x in WARN)
    _wb = []
    for _t, _x in WARN:
        if not _x:
            continue
        _wb.append("<h4>%s — %d 件</h4><ul>%s</ul>"
                   % (inline(_t), len(_x), "".join("<li>%s</li>" % inline(str(q)) for q in _x)))
    h[_WARNPOS] = ('<div class="box" style="border-color:%s"><h3>この指図の検査結果 — ⚠ %d 件</h3><p>'
                   '生成器が組むたびに走る検査の<b>すべての ⚠ をここに載せる</b>。'
                   '⛔ <b>従前は stdout にしか出ておらず、artifact のどこにも無かった</b> — '
                   '検図方の言葉で「<b>いまの指図は自分の検査結果を持っていない図</b>」だった'
                   '(2026-09-01)。⭕ 0 件でないなら、下の一覧が<b>いま指図に残っている穴の全部</b>。'
                   '⚠ 個々の検査の合否と内訳は、それぞれの図版の下の表にも出る。</p>%s</div>'
                   % ("var(--shu)" if NWARN else "var(--take)", NWARN,
                      "".join(_wb) or "<p><b>0 件</b>。</p>"))
    for _t, _x in WARN[-1:]:
        for _q in _x:
            print("   ⚠", _q)
    # ⭐ 本文の `{{図:題}}` を、採番した図版へのリンクへ差し替える(⛔ 番号を本文へ直書きしない)
    open(OUT, "w", encoding="utf-8").write(plate_refs("\n".join(h)))
    print("wrote %s (%.0f KB) — 図版 %d 面 — 建蔽率 %.1f%%" % (OUT, os.path.getsize(OUT) / 1024, _SVN[0], kp))
    if bad:
        print("⚠ 重なり %d 件 — 検図の前に直すこと" % len(bad))
    print("  run: 検図(edo-kosho / edo-kenzu) → ユーザーのレビュー → 実装 → 突き合わせ")


if __name__ == "__main__":
    main()
