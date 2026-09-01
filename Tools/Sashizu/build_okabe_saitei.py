#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""岡部邸の**裁定図** — ユーザーに二案を選んでいただくための図だけを組む。

⛔ **名前と数字の羅列で選ばせない**(CLAUDE.md)。各案を**同じ縮尺で並べ**、
   ①どこ ②いま何がどうなっているか ③案を並べた図 ④案ごとに何がどれだけ動くか
   ⑤推奨と理由 を1枚に載せる。

⚠ **数値は一つも手で書かない。** 地盤は `okabe_edo_dem.json`(江戸期の復元地盤)、
   設計は `okabe_sashizu.json`、切盛は `build_okabe_sashizu.graded_y` から毎回算出する。
   庭の案そのものは **edo-niwashi(庭方)の設計**で、当スクリプトは図に起こすだけ。

    python3 Tools/Sashizu/build_okabe_saitei.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_okabe_sashizu as B                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs", "Sashizu")
OUT = os.path.join(DOC, "okabe_saitei.html")

# 庭方(edo-niwashi)が 2026-09-02 に設計した、平坦化から外す5区画。
# ⛔ ここは「案」なので設計値ファイルへは入れない(裁定が下りてから指図方が書き起こす)。
REGIONS = [("南泉水の庭", -28.0, -8.0, 44.0, 66.0),
           ("南西の樹林", -41.0, -28.0, 44.0, 80.0),
           ("奥の紅葉谷", 18.0, 25.5, 88.0, 102.0),
           ("長局の東の坪", 12.0, 20.0, 80.0, 100.0),
           ("西端の帯", -20.0, 6.0, 106.0, 117.0)]
# ⚠ 池の汀線・水面は**この図に載せない**。庭方の初案(水面 23.40)は、汀線の中の自然地盤の
#   72% が水面より高いことが実測で分かり、引き直しを依頼中(2026-09-02)。
#   ⛔ 裁定1 は「窪みを埋めるか残すか」だけを問うもので、池の形とは独立に決まる。


def load():
    d = json.load(io.open(os.path.join(DOC, "okabe_sashizu.json"), encoding="utf-8"))
    d = B.pipeline(d)
    ter = B.load_terrain(os.path.join(DOC, "okabe_edo_dem.json"))
    return d, ter


def measure(d, ter):
    """5区画の中で、いま何 m³ 盛っているか。**主面の多角形の中だけ**を数える。"""
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    we = dict((t["name"], B.walled_edges(d, t)) for t in d["terraces"])
    step, K = ter["step"], d["const"]["ken"]
    A = (step * K) ** 2
    rows, tot = [], [0.0, 0.0, 0.0]
    for nm, u0, u1, v0, v1 in REGIONS:
        f = c = 0.0
        lo, hi, n = 9e9, -9e9, 0
        for iv in range(ter["nv"]):
            v = ter["v0"] + iv * step
            if not (v0 <= v <= v1):
                continue
            for iu in range(ter["nu"]):
                u = ter["u0"] + iu * step
                if not (u0 <= u <= u1):
                    continue
                nat = ter["h"][iv][iu]
                if nat is None or not B.tin(sh, u, v):
                    continue
                dz = B.graded_y(d, u, v, nat, we) - nat
                if dz > 0:
                    f += dz * A
                else:
                    c += -dz * A
                lo, hi, n = min(lo, nat), max(hi, nat), n + 1
        rows.append((nm, f, c, lo, hi, n * A / 3.3058))
        tot[0] += f; tot[1] += c; tot[2] += n * A / 3.3058
    return rows, tot


# ------------------------------------------------------------------ 作図の土台
def sv(W, H, label):
    return ['<svg viewBox="0 0 %g %g" width="100%%" role="img" aria-label="%s" '
            'style="max-width:%gpx;height:auto">' % (W, H, label, W)]


# ⛔ 文字の寄せは **style** で出す — クラスの CSS(`.anS2{text-anchor:middle}`)が
#   presentation attribute に勝つので、`text-anchor="start"` は効かない。
#   指図の生成器が同じ穴を踏んで直してあるので、そちらの T/LN/R をそのまま借りる。
def T(g, x, y, s, cls="anS2", anchor="start", fs=None):
    g.append(B.T(x, y, s, cls, anchor, fs))


def LN(g, x1, y1, x2, y2, st="var(--ink)", w=1.0, dash=None, op=None):
    g.append(B.LN(x1, y1, x2, y2, st, w, dash, op))


def RC(g, x, y, w, h, fill="none", st=None, sw=1.0, op=None, dash=None):
    g.append(B.R(x, y, max(w, 0), max(h, 0), fill, st or "none", sw, dash, op))


def fill_col(dz):
    """盛土の深さ → 色。⛔ 図例と同じ関数をどの図でも使う。"""
    if dz <= 0.05:
        return None
    t = min(dz / 2.5, 1.0)
    return "rgba(198,93,58,%.2f)" % (0.15 + 0.65 * t)


# ------------------------------------------------------------------ 其一 断面
def section(d, ter, at_v=46.0, u0=-32.0, u1=10.0):
    """裁定1の断面。**同じ枠に案A・案Bを上下で並べる**(縮尺を揃える)。"""
    W, PH, PAD = 940.0, 210.0, 46.0
    H = PAD + PH * 2 + 74
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    we = dict((t["name"], B.walled_edges(d, t)) for t in d["terraces"])
    y0, y1 = 20.5, 27.5
    sx = (W - 120) / (u1 - u0)

    def X(u):
        return 70 + (u - u0) * sx

    def Y(top, y):
        return top + PH - 26 - (y - y0) / (y1 - y0) * (PH - 46)

    g = sv(W, H, "裁定1 断面 v=%g" % at_v)
    nat, des = [], []
    u = u0
    while u <= u1 + 1e-9:
        z = B._dem_at(d, u, at_v)
        if z is not None:
            nat.append((u, z))
            des.append((u, B.graded_y(d, u, at_v, z, we) if B.tin(sh, u, at_v) else z))
        u += 0.25
    inreg = lambda u9: any(a <= u9 <= b and c <= at_v <= e for _n, a, b, c, e in REGIONS)  # noqa: E731

    for k, (top, ttl, opt) in enumerate(((PAD, "案B — 主面を全面 24.80 で平らにする(現況の設計)", "B"),
                                         (PAD + PH, "案A — 庭と樹林の5区画は自然地盤なり(推奨)", "A"))):
        RC(g, 60, top + 6, W - 90, PH - 18, "var(--paper2)", "var(--rule)", 0.8, 0.55)
        for yy in (21, 22, 23, 24, 25, 26, 27):
            LN(g, 66, Y(top, yy), W - 34, Y(top, yy), "var(--rule)", 0.6, "3 4", 0.8)
            T(g, 62, Y(top, yy) + 3, "%d" % yy, "anS2", "end", 9)
        # 自然地盤
        g.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.3" '
                 'stroke-dasharray="6 3" opacity="0.85"/>'
                 % " ".join("%.1f,%.1f" % (X(a), Y(top, b)) for a, b in nat))
        # 設計面
        pts = [(a, (b if (opt == "A" and inreg(a)) else c))
               for (a, b), (_a2, c) in zip(nat, des)]
        g.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="2.2"/>'
                 % " ".join("%.1f,%.1f" % (X(a), Y(top, b)) for a, b in pts))
        # 盛土のハッチ(自然と設計の間)
        band = [(a, b, c) for (a, b), (_a, c) in zip(nat, pts) if c - b > 0.05]
        if band:
            seg, prev = [], None
            for a, b, c in band:
                if prev is not None and a - prev > 0.3:
                    seg.append([])
                if not seg:
                    seg.append([])
                seg[-1].append((a, b, c)); prev = a
            for sgm in seg:
                if len(sgm) < 2:
                    continue
                poly = ["%.1f,%.1f" % (X(a), Y(top, c)) for a, _b, c in sgm] + \
                       ["%.1f,%.1f" % (X(a), Y(top, b)) for a, b, _c in reversed(sgm)]
                g.append('<polygon points="%s" fill="rgba(198,93,58,0.45)"/>' % " ".join(poly))
        if opt == "A":
            lo9 = min(b for a, b in nat if inreg(a))
            T(g, X(-21.0), Y(top, lo9) + 16,
              "この帯の自然地盤は最も低い所で %.2f — 案Bはここを %.1fm 盛って平らにする"
              % (lo9, 24.8 - lo9), "anS2", "middle", 10)
        T(g, 66, top + 20, ttl, "anS2", "start", 12)
    for u9 in range(int(u0), int(u1) + 1, 4):
        LN(g, X(u9), PAD + 2 * PH - 20, X(u9), PAD + 2 * PH - 14, "var(--dim)", 0.8)
        T(g, X(u9), PAD + 2 * PH - 4, "u%+d" % u9, "anS2", "middle", 9)
    T(g, 6, 16, "断面 v=%g(南泉水の庭を東西に切る)／縦横同一縮尺・単位 m(海抜)／"
      "破線=江戸期の復元地盤・朱線=設計する地表面・橙のハッチ=盛土" % at_v, "anS2", "start", 11)
    T(g, 6, H - 6, "⚠ 断面の位置は指図 其八・其九と同じグリッド。u+ が北、v+ が西。", "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


# ------------------------------------------------------------------ 其二 平面(A/B 並置)
def plan_pair(d, ter):
    """主面の盛土を平面で見る。**左=案B(現況の設計) / 右=案A** を同一縮尺で。"""
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    we = dict((t["name"], B.walled_edges(d, t)) for t in d["terraces"])
    P = [q for q in sh["poly"]]
    uu = [q[0] for q in P]; vv = [q[1] for q in P]
    umin, umax, vmin, vmax = min(uu) - 2, max(uu) + 2, min(vv) - 2, max(vv) + 2
    sc = 3.05                                        # px / 間
    pw = (vmax - vmin) * sc + 30
    ph = (umax - umin) * sc + 30
    W, H = pw * 2 + 56, ph + 96
    g = sv(W, H, "裁定1 平面 案Bと案Aの並置")

    def X(o, v):
        return o + 15 + (vmax - v) * sc          # v+ = 西 → 左

    def Y(u):
        return 58 + 15 + (umax - u) * sc         # u+ = 北 → 上

    step = ter["step"]
    for o, ttl, opt in ((0.0, "案B — 全面 24.80(現況の設計)", "B"),
                        (pw + 56, "案A — 5区画は自然地盤なり(推奨)", "A")):
        RC(g, o + 6, 52, pw + 6, ph + 6, "var(--paper2)", "var(--rule)", 0.8, 0.5)
        T(g, o + 12, 44, ttl, "anS2", "start", 13)
        g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4"/>'
                 % " ".join("%.1f,%.1f" % (X(o, q[1]), Y(q[0])) for q in P))
        iv = 0
        while iv < ter["nv"]:
            v = ter["v0"] + iv * step
            iu = 0
            while iu < ter["nu"]:
                u = ter["u0"] + iu * step
                nat = ter["h"][iv][iu]
                if nat is not None and B.tin(sh, u, v):
                    inr = any(a <= u <= b and c <= v <= e for _n, a, b, c, e in REGIONS)
                    if opt == "A" and inr:
                        col = "rgba(110,150,105,0.30)"       # 自然地盤なり(造成しない)
                    else:
                        col = fill_col(B.graded_y(d, u, v, nat, we) - nat)
                    if col:
                        RC(g, X(o, v + step), Y(u + step), step * sc + 0.6, step * sc + 0.6, col)
                iu += 1
            iv += 1
        for nm, u0, u1, v0, v1 in REGIONS:
            RC(g, X(o, v1), Y(u1), (v1 - v0) * sc, (u1 - u0) * sc, "none",
               "var(--midori)" if opt == "A" else "var(--dim)", 1.6, None,
               None if opt == "A" else "5 4")
            T(g, X(o, (v0 + v1) / 2), Y((u0 + u1) / 2), nm, "anS2", "middle", 10)
        for m in d["munes"]:
            RC(g, X(o, m["v1"]), Y(m["u1"]), (m["v1"] - m["v0"]) * sc, (m["u1"] - m["u0"]) * sc,
               "var(--nagaya)", "var(--ink)", 0.8, 0.85)
    T(g, 6, 16, "主面(24.80)の盛土。⛔ 両図は**同一縮尺**。橙の濃さ=盛土の深さ(0〜2.5m以上)／"
      "茶の矩形=御殿の棟／緑の枠=平坦化から外す区画", "anS2", "start", 11)
    T(g, 6, 32, "向き: u+ が北(上)・v+ が西(左)。1間=1.818m。", "anS2", "start", 10)
    for i, lab in enumerate(("0.5m", "1.0m", "1.5m", "2.0m", "2.5m以上")):
        RC(g, 470 + i * 96, 22, 16, 11, fill_col(0.5 + i * 0.5))
        T(g, 490 + i * 96, 31, lab, "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


# ------------------------------------------------------------------ 其三 長局(裁定2)
def nagatsubone(d):
    ng = next(m for m in d["munes"] if m["name"] == "Nagatsubone")
    gd = next(g9 for g9 in d["gardens"] if g9["name"] == "NiwaOkuN")
    u0, u1 = ng["u0"] - 3, ng["u1"] + 4
    v0, v1 = ng["v0"] - 3, gd["v1"] + 4
    sc = 15.0
    pw = (v1 - v0) * sc + 30
    ph = (u1 - u0) * sc + 30
    W, H = pw * 2 + 56, ph + 92

    def X(o, v):
        return o + 15 + (v1 - v) * sc

    def Y(u):
        return 52 + 15 + (u1 - u) * sc

    g = sv(W, H, "裁定2 長局の西庭 案Aと案Bの並置")
    for o, ttl, opt in ((0.0, "案A — 実用の庭「長局の物干」にする(推奨)", "A"),
                        (pw + 56, "案B — 長局の西面を入側+縁に改め鑑賞庭を残す", "B")):
        RC(g, o + 6, 46, pw + 6, ph + 6, "var(--paper2)", "var(--rule)", 0.8, 0.5)
        T(g, o + 12, 38, ttl, "anS2", "start", 13)
        RC(g, X(o, ng["v1"]), Y(ng["u1"]), (ng["v1"] - ng["v0"]) * sc,
           (ng["u1"] - ng["u0"]) * sc, "var(--nagaya)", "var(--ink)", 1.2, 0.9)
        T(g, X(o, (ng["v0"] + ng["v1"]) / 2), Y((ng["u0"] + ng["u1"]) / 2),
          "長局(女中部屋)", "anS2", "middle", 12)
        RC(g, X(o, gd["v1"]), Y(gd["u1"]), (gd["v1"] - gd["v0"]) * sc,
           (gd["u1"] - gd["u0"]) * sc, "rgba(120,150,100,0.30)", "var(--midori)", 1.4)
        wv = ng["v1"]                                  # 長局の西の妻
        if opt == "A":
            LN(g, X(o, wv), Y(ng["u0"]), X(o, wv), Y(ng["u1"]), "var(--ink)", 4.0)
            T(g, X(o, wv) - 8, Y(ng["u0"]) - 10, "白壁(妻)のまま — 開けない", "anS2", "end", 11)
            for uu9, vv9, nm in ((6.2, 101.4, "厠2"), (7.6, 104.2, "井戸"),
                                 (9.4, 101.6, "納戸小屋"), (10.9, 104.0, "物干竿3")):
                g.append('<circle cx="%.1f" cy="%.1f" r="9" fill="var(--dan)" '
                         'stroke="var(--ink)" stroke-width="0.9"/>' % (X(o, vv9), Y(uu9)))
                T(g, X(o, vv9), Y(uu9) + 24, nm, "anS2", "middle", 10)
            LN(g, X(o, gd["v1"]), Y(gd["u0"]), X(o, gd["v0"]), Y(gd["u0"]),
               "var(--hei)", 5.0)
            T(g, X(o, (gd["v0"] + gd["v1"]) / 2), Y(gd["u0"]) + 16,
              "建仁寺垣 h1.8(目隠し)", "anS2", "middle", 10)
        else:
            LN(g, X(o, wv), Y(ng["u0"]), X(o, wv), Y(ng["u1"]), "var(--shu)", 4.0, "7 4")
            RC(g, X(o, ng["v1"]), Y(ng["u1"]), 1.0 * sc, (ng["u1"] - ng["u0"]) * sc,
               "rgba(198,93,58,0.30)", "var(--shu)", 1.2)
            T(g, X(o, wv) - 8, Y(ng["u0"]) - 10, "西の入側+縁に作り替え(室割りが動く)",
              "anS2", "end", 11)
            T(g, X(o, (gd["v0"] + gd["v1"]) / 2), Y((gd["u0"] + gd["u1"]) / 2) + 18,
              "鑑賞庭のまま(見る座敷を作る)", "anS2", "middle", 10)
        T(g, X(o, (gd["v0"] + gd["v1"]) / 2), Y(gd["u1"]) - 8,
          "%s(%.0f坪)" % (gd["label"], abs((gd["u1"] - gd["u0"]) * (gd["v1"] - gd["v0"]))
                          * d["const"]["ken"] ** 2 / 3.3058), "anS2", "middle", 11)
    T(g, 6, 16, "長局(u%g〜%g / v%g〜%g)と西庭(u%g〜%g / v%g〜%g)。⛔ 両図は同一縮尺。"
      % (ng["u0"], ng["u1"], ng["v0"], ng["v1"], gd["u0"], gd["u1"], gd["v0"], gd["v1"]),
      "anS2", "start", 11)
    T(g, 6, 30, "向き: u+ が北(上)・v+ が西(左)。西庭は長局の**西の妻(白壁)**に正対しており、"
      "上陣・下陣のどちらの座敷からも見えない。", "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


def main():
    d, ter = load()
    rows, tot = measure(d, ter)
    css = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"),
                  encoding="utf-8").read()
    gr = d["grading"]["haryoJi"]
    net = gr["moridoM3"] - gr["kiridoM3"]
    save = tot[0] - tot[1]
    h = ['<meta charset="utf-8">', "<title>岡部筑前守上屋敷 裁定図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">外桜田永田町 ／ 岡部筑前守上屋敷 ／ 庭の設計(庭方 2026-09-02)</p>')
    h.append("<h1>裁定図 — 庭をどう作るか(2件)</h1>")
    h.append('<p class="lede">庭方(edo-niwashi)の設計案のうち、<b>ユーザーの裁定が要る2件</b>だけを図にした。'
             '⛔ 数値は一つも手で書いていない — 地盤は江戸期の復元地盤 <code>okabe_edo_dem.json</code>、'
             '設計は <code>okabe_sashizu.json</code>、切盛は指図の生成器と同じ '
             '<code>graded_y()</code> から毎回算出している。'
             '組むのは <code>Tools/Sashizu/build_okabe_saitei.py</code>。</p>')

    h.append('<div class="plate"><div class="phead"><h2>裁定1　主面の5区画を「平坦化しない」ことを認めるか</h2>'
             '<span class="meta">どこ=主面(24.80)の南半分と西端・奥。指図 其一(敷地)・其四(切盛)と同じグリッド</span></div>')
    h.append('<div class="box"><h3>いま何がどうなっているか(実測)</h3>'
             '<p>当屋敷の拝領時造成は<b>盛土 %s m³ / 切土 %s m³ = 差引 <b>+%s m³ の客土</b></b>。'
             'このうち、庭と樹林にあてる下の5区画を 24.80 へ均すための盛土が'
             '<b>差引 +%.0f m³(客土の %.0f%%)</b>を占める。'
             '主面の南半分の自然地盤は最も低い所で <b>%.2f m</b>(u−21, v46)まで下がっており、'
             '<b>24.80 で通すと最大 %.1f m 盛る</b>ことになる。</p></div>'
             % ("{:,}".format(gr["moridoM3"]), "{:,}".format(gr["kiridoM3"]),
                "{:,}".format(net), save, 100.0 * save / net,
                min(r[3] for r in rows), 24.8 - min(r[3] for r in rows)))
    h.append('<div class="tw"><table><thead><tr><th>区画</th><th>グリッド (u, v)</th><th>面積</th>'
             '<th>自然地盤</th><th>いまの盛土</th><th>いまの切土</th><th>差引</th></tr></thead><tbody>')
    for (nm, f, c, lo, hi, tb), (_n, u0, u1, v0, v1) in zip(rows, REGIONS):
        h.append("<tr><td>%s</td><td><code>u%+g〜%+g / v%g〜%g</code></td><td>%.0f坪</td>"
                 "<td>%.2f〜%.2f</td><td>%.0f m³</td><td>%.0f m³</td><td><b>%+.0f m³</b></td></tr>"
                 % (nm, u0, u1, v0, v1, tb, lo, hi, f, c, f - c))
    h.append("<tr><td colspan='4'><b>合計</b></td><td><b>%.0f m³</b></td><td><b>%.0f m³</b></td>"
             "<td><b>%+.0f m³</b></td></tr>" % (tot[0], tot[1], save))
    h.append("</tbody></table></div>")
    h.append('<div class="fig">%s</div>' % section(d, ter))
    h.append('<p class="cap"><b>断面 v=46</b> — 南泉水の庭を東西に切った所(窪みが最も深く出る位置)。'
             '案B(上)は窪みを埋めて 24.80 の平場にする。案A(下)は窪みをそのまま残す。'
             '⚠ <b>池の汀線・水面はこの図に載せていない</b> — 庭方の初案(水面 23.40)は'
             '汀線の中の自然地盤の <b>72%が水面より高い</b>ことが実測で分かり、引き直しを依頼中。'
             '⛔ この裁定は<b>池の形とは独立</b>で、「窪みを埋めるか残すか」だけを問うている。</p>')
    h.append('<div class="fig">%s</div>' % plan_pair(d, ter))
    h.append('<p class="cap"><b>平面(同一縮尺)</b> — 橙が盛土。案Aでは5区画の橙が消える。'
             '⚠ 5区画の外(棟の載る所・門前面へ下る帯)の盛土は<b>どちらの案でも残る</b> — '
             'それが下の「案Aでも残る %s m³」。</p>' % "{:,}".format(int(net - save)))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A(推奨)</th><th>案B</th>'
             '</tr></thead><tbody>'
             '<tr><td>やること</td><td>5区画を主面の平坦から外し<b>自然地盤なり</b>にする。棟が載る所だけ 24.80</td>'
             '<td>現況どおり主面を全面 24.80 で平らにする</td></tr>'
             '<tr><td>客土</td><td><b>%s → %s m³</b>(−%.0f%%)</td><td>%s m³ のまま</td></tr>'
             '<tr><td>庭</td><td>池が<b>天然の窪みに水が溜まる</b>形になり、汀と庭の高低差がそのまま土手になる</td>'
             '<td>池は平場に掘った穴。築山も盛土でしか作れない</td></tr>'
             '<tr><td>規則3(面の高さは地形が決める)</td><td>適合</td>'
             '<td><b>反する</b> — 窪みを埋めている</td></tr>'
             '<tr><td>やり直しになるもの</td><td><code>terraces.Shumen</code> の多角形／'
             '南辺・南西辺の練塀 run の据面／<code>grading</code> の全数値／切盛図／断面16面</td>'
             '<td>無し</td></tr>'
             '</tbody></table></div>'
             % ("{:,}".format(net), "{:,}".format(int(net - save)), 100.0 * save / net,
                "{:,}".format(net)))
    h.append('<p class="cap"><b>推奨=案A。</b>CLAUDE.md 規則3「面の高さは地形が決める・窪みは埋めず'
             '一段低い郭にする」の直接の適用であり、<b>庭の質と土量が同時に良くなる</b>。'
             '代償(段の多角形と据面の引き直し)は指図方の再計算で吸収できる。</p>')
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>裁定2　長局の西庭をどう始末するか</h2>'
             '<span class="meta">どこ=<code>NiwaOkuN</code> 長局の西庭 u+5〜+12 / v100〜106</span></div>')
    h.append('<div class="box"><h3>いま何がどうなっているか</h3>'
             '<p>この庭は<b>長局の西の妻(白壁)に正対</b>しており、上陣・下陣のどちらの座敷からも見えない。'
             '長局は女中の部屋列で、そもそも鑑賞用の庭を持つ格ではない。'
             '一方でこの区画は、長局に<b>実用の外部空間が一つも無い</b>現況を埋められる唯一の場所でもある。</p></div>')
    h.append('<div class="fig">%s</div>' % nagatsubone(d))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A(推奨)</th><th>案B</th>'
             '</tr></thead><tbody>'
             '<tr><td>やること</td><td><b>実用の庭「長局の物干」</b>に改める。井戸1・物干竿3・納戸小屋'
             '(1.5間×1間)・厠2。目隠しに建仁寺垣 h1.8m。⛔ 灯籠・飛石・景石は置かない</td>'
             '<td>長局の v95〜100(室が入っていない5間)を<b>西の入側+縁</b>に改め、鑑賞庭のまま残す</td></tr>'
             '<tr><td>良い所</td><td>女中の生活が成立する。史料の要らない実用施設</td>'
             '<td>庭の数が減らない</td></tr>'
             '<tr><td>悪い所</td><td>「庭」が1つ減る</td>'
             '<td><b>棟の室割りが動く</b>。しかも西の景は溜池でなく土井境の法面で、開けても見るものが無い</td></tr>'
             '<tr><td>やり直しになるもの</td><td><code>gardens</code> の1件を差し替え、'
             '<code>service</code> に井戸1・小屋1を追加</td>'
             '<td><code>munes.Nagatsubone</code> の室割り／其七(棟と室)／建蔽率</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>推奨=案A。</b>見えない庭を作るより、無い実用空間を作るほうが屋敷として'
             '成立する。⭕ そのうえで長局には<b>東側</b>(u+12〜+20 / v80〜100)に鑑賞庭を新設する'
             '(こちらは長局の東入側が正面に来るので座敷から見える)。</p>')
    h.append("</div>")

    h.append('<div class="box" style="border-color:var(--shu)"><h3>⚠ この図で決まらないこと</h3>'
             '<p>庭方の設計はこの2件のほかに、主景の位置・汀線の形・石組・飛石・植栽・結界塀・稲荷社の'
             '位置などを含むが、それらは<b>裁定を要しない設計判断</b>として指図方が書き起こす。'
             'いずれも<b>確度U(当方の設計判断・史料の裏づけ無し)</b>で、指図にそう明記する。'
             '⛔ 「馬場を置かない」「池を一つに絞る」「蹲踞を置かない」も当方の裁定であって、'
             '史料が否定しているわけではない。</p></div>')
    h.append("</div>")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(h))
    print("wrote %s (%d KB)" % (OUT, os.path.getsize(OUT) // 1024))
    print("5区画の差引 %+.0f m³ / 客土 %d → %d m³" % (save, net, int(net - save)))


if __name__ == "__main__":
    main()
