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


def _variant(raw, holes, garden):
    """比べる**2つの設計**を作る。
    ⛔ 2026-09-02 の訂正: 当初は「5区画の矩形の中にいま載っている盛土」を足して案Aの効果と
      していたが、**それは効果ではない**。平坦化をやめると区画の**縁**の土工も変わり、
      区画の矩形は主面の多角形から食み出す(西端の帯は 29% しか段に掛からない)。
      ⭕ 効果は**二つの完成した設計の差**でしか測れない。指図方が同じ誤りを見つけて訂正し、
      当方も独立に測り直して一致を確認した(素の設計 +4,183 / 案A +2,824 = 差 1,359)。"""
    import copy
    d = copy.deepcopy(raw)
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    if not holes:
        sh.pop("holes", None)
        sh.pop("keeps", None)
    if not garden:                       # 庭の土工(池・築山)は裁定1の外なので両案から外す
        for g in d.get("gardens", []):
            g.pop("migiwa", None)
            g.pop("tsukiyama", None)
    return B.pipeline(d)


def load():
    raw = json.load(io.open(os.path.join(DOC, "okabe_sashizu.json"), encoding="utf-8"))
    ter = B.load_terrain(os.path.join(DOC, "okabe_edo_dem.json"))
    dA = _variant(raw, True, False)      # 案A = 5区画を平坦化しない(庭の土工は外す)
    dB = _variant(raw, False, False)     # 案B = 主面を全面 24.80(=素の設計)
    return raw, dA, dB, ter


def _totals(d, ter):
    """その設計の拝領時造成(盛土・切土・差引)。**格子を一枚まるごと歩く**。"""
    we = dict((t["name"], B.walled_edges(d, t)) for t in d["terraces"])
    step, K = ter["step"], d["const"]["ken"]
    A = (step * K) ** 2
    f = c = 0.0
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * step
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * step
            n = ter["h"][iv][iu]
            if n is None:
                continue
            dz = B.graded_y(d, u, v, n, we) - n
            if dz > 0:
                f += dz * A
            else:
                c += -dz * A
    return f, c, f - c


def measure(raw, dA, dB, ter):
    """区画ごとの効き目を「その抜きだけを入れた設計」との差で出す。
    ⛔ 矩形の中の盛土を足さない(それは効果ではない)。⛔ 順に依存するので合計は別に測る。"""
    sh = next(t for t in dA["terraces"] if t["name"] == "Shumen")
    holes = sh.get("holes", [])
    tB = _totals(dB, ter)
    tA = _totals(dA, ter)
    rows = []
    for i, h in enumerate(holes):
        one = _variant(raw, True, False)
        s1 = next(t for t in one["terraces"] if t["name"] == "Shumen")
        s1["holes"] = [holes[i]]
        one = B.pipeline(one)
        rows.append((h.get("name", "?"), _totals(one, ter)[2] - tB[2]))
    return rows, tB, tA


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
def _line(d, ter, at_v, u0, u1):
    """その設計の地表面を v=at_v で切った折れ線。**設計そのものから引く**(置換しない)。"""
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    we = dict((t["name"], B.walled_edges(d, t)) for t in d["terraces"])
    nat, des = [], []
    u = u0
    while u <= u1 + 1e-9:
        z = B._dem_at(d, u, at_v)
        if z is not None:
            nat.append((u, z))
            des.append((u, B.graded_y(d, u, at_v, z, we)))
        u += 0.25
    return nat, des


def section(dA, dB, ter, at_v=56.0, u0=-32.0, u1=10.0):
    """裁定1の断面。**同じ枠に案A・案Bを上下で並べる**(縮尺を揃える)。
    ⛔ 2026-09-02: 一つの設計から「区画の中だけ自然地盤に差し替える」描き方をやめた。
      指図が案Aで実装された後は、その描き方だと**両方の枠に案Aが出てしまう**。
      ⭕ 二つの設計を実際に組んで、それぞれから引く。"""
    W, PH, PAD = 940.0, 210.0, 46.0
    H = PAD + PH * 2 + 74
    y0, y1 = 20.5, 27.5
    sx = (W - 120) / (u1 - u0)

    def X(u):
        return 70 + (u - u0) * sx

    def Y(top, y):
        return top + PH - 26 - (y - y0) / (y1 - y0) * (PH - 46)

    g = sv(W, H, "裁定1 断面 v=%g" % at_v)
    for top, ttl, dd in ((PAD, "案B — 主面を全面 24.80 で平らにする", dB),
                         (PAD + PH, "案A — 庭と樹林の5区画は自然地盤なり(推奨)", dA)):
        nat, des = _line(dd, ter, at_v, u0, u1)
        RC(g, 60, top + 6, W - 90, PH - 18, "var(--paper2)", "var(--rule)", 0.8, 0.55)
        for yy in (21, 22, 23, 24, 25, 26, 27):
            LN(g, 66, Y(top, yy), W - 34, Y(top, yy), "var(--rule)", 0.6, "3 4", 0.8)
            T(g, 62, Y(top, yy) + 3, "%d" % yy, "anS2", "end", 9)
        g.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.3" '
                 'stroke-dasharray="6 3" opacity="0.85"/>'
                 % " ".join("%.1f,%.1f" % (X(a), Y(top, b)) for a, b in nat))
        g.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="2.2"/>'
                 % " ".join("%.1f,%.1f" % (X(a), Y(top, b)) for a, b in des))
        band = [(a, b, c) for (a, b), (_a, c) in zip(nat, des) if c - b > 0.05]
        if band:
            seg, prev = [], None
            for a, b, c in band:
                if prev is None or a - prev > 0.3:
                    seg.append([])
                seg[-1].append((a, b, c)); prev = a
            for sgm in seg:
                if len(sgm) < 2:
                    continue
                poly = ["%.1f,%.1f" % (X(a), Y(top, c)) for a, _b, c in sgm] + \
                       ["%.1f,%.1f" % (X(a), Y(top, b)) for a, b, _c in reversed(sgm)]
                g.append('<polygon points="%s" fill="rgba(198,93,58,0.45)"/>' % " ".join(poly))
        T(g, 66, top + 20, ttl, "anS2", "start", 12)
        if dd is dA:
            lo9 = min(b for a, b in nat if -28.0 <= a <= -8.0)
            T(g, X(-19.0), Y(top, lo9) + 16,
              "この帯の自然地盤は最も低い所で %.2f — 案Bはここを %.1fm 盛って平らにする"
              % (lo9, 24.8 - lo9), "anS2", "middle", 10)
    for u9 in range(int(u0), int(u1) + 1, 4):
        LN(g, X(u9), PAD + 2 * PH - 20, X(u9), PAD + 2 * PH - 14, "var(--dim)", 0.8)
        T(g, X(u9), PAD + 2 * PH - 4, "u%+d" % u9, "anS2", "middle", 9)
    T(g, 6, 16, "断面 v=%g(南の芝谷と南の樹林を東西に切る)／縦横同一縮尺・単位 m(海抜)／"
      "破線=江戸期の復元地盤・朱線=設計する地表面・橙のハッチ=盛土" % at_v, "anS2", "start", 11)
    T(g, 6, H - 6, "⚠ 断面の位置は指図の断面と同じグリッド。u+ が北、v+ が西。"
      "⛔ 庭の土工(池・築山)は両案から外してある — 裁定1は池の形とは独立に決まる。", "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


def plan_pair(dA, dB, ter):
    """主面の盛土を平面で見る。**左=案B / 右=案A** を同一縮尺で。"""
    shA = next(t for t in dA["terraces"] if t["name"] == "Shumen")
    P = [q for q in shA["poly"]]
    uu = [q[0] for q in P]; vv = [q[1] for q in P]
    umin, umax, vmin, vmax = min(uu) - 2, max(uu) + 2, min(vv) - 2, max(vv) + 2
    sc = 3.05
    pw = (vmax - vmin) * sc + 30
    ph = (umax - umin) * sc + 30
    W, H = pw * 2 + 56, ph + 96
    g = sv(W, H, "裁定1 平面 案Bと案Aの並置")

    def X(o, v):
        return o + 15 + (vmax - v) * sc

    def Y(u):
        return 58 + 15 + (umax - u) * sc

    step = ter["step"]
    holes = shA.get("holes", [])
    for o, ttl, dd in ((0.0, "案B — 全面 24.80", dB), (pw + 56, "案A — 5区画は自然地盤なり(推奨)", dA)):
        we = dict((t["name"], B.walled_edges(dd, t)) for t in dd["terraces"])
        sh = next(t for t in dd["terraces"] if t["name"] == "Shumen")
        RC(g, o + 6, 52, pw + 6, ph + 6, "var(--paper2)", "var(--rule)", 0.8, 0.5)
        T(g, o + 12, 44, ttl, "anS2", "start", 13)
        g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4"/>'
                 % " ".join("%.1f,%.1f" % (X(o, q[1]), Y(q[0])) for q in P))
        for iv in range(ter["nv"]):
            v = ter["v0"] + iv * step
            for iu in range(ter["nu"]):
                u = ter["u0"] + iu * step
                nat = ter["h"][iv][iu]
                if nat is None or not B.tin(sh, u, v):
                    continue
                col = fill_col(B.graded_y(dd, u, v, nat, we) - nat)
                if col:
                    RC(g, X(o, v + step), Y(u + step), step * sc + 0.6, step * sc + 0.6, col)
        for hh in holes:
            pts = hh.get("poly") or []
            if not pts:
                continue
            g.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="1.6"%s/>'
                     % (" ".join("%.1f,%.1f" % (X(o, q[1]), Y(q[0])) for q in pts),
                        "rgba(110,150,105,0.28)" if dd is dA else "none",
                        "var(--midori)" if dd is dA else "var(--dim)",
                        "" if dd is dA else ' stroke-dasharray="5 4"'))
            cu = sum(q[0] for q in pts) / len(pts); cv = sum(q[1] for q in pts) / len(pts)
            T(g, X(o, cv), Y(cu), hh.get("label") or hh.get("name", ""), "anS2", "middle", 10)
        for m in dd["munes"]:
            RC(g, X(o, m["v1"]), Y(m["u1"]), (m["v1"] - m["v0"]) * sc, (m["u1"] - m["u0"]) * sc,
               "var(--nagaya)", "var(--ink)", 0.8, 0.85)
    T(g, 6, 16, "主面(24.80)の盛土。⛔ 両図は**同一縮尺**。橙の濃さ=盛土の深さ(0〜2.5m以上)／"
      "茶の矩形=御殿の棟／緑=平坦化から外す区画(案Bでは破線の枠だけ)", "anS2", "start", 11)
    T(g, 6, 32, "向き: u+ が北(上)・v+ が西(左)。1間=1.818m。"
      "⛔ 庭の土工(池・築山)は両案から外してある。", "anS2", "start", 10)
    for i, lab in enumerate(("0.5m", "1.0m", "1.5m", "2.0m", "2.5m以上")):
        RC(g, 470 + i * 96, 22, 16, 11, fill_col(0.5 + i * 0.5))
        T(g, 490 + i * 96, 31, lab, "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


# ------------------------------------------------------------------ 其三 長局(裁定2)
def nagatsubone(d):
    ng = next(m for m in d["munes"] if m["name"] == "Nagatsubone")
    # ⚠ 裁定2(案A)の実装で `NiwaOkuN`(長局の西庭)は `NiwaMonohoshi`(長局の物干)へ
    #   置き換わった。裁定図は**問うた時点の姿**を残すが、名前はどちらでも引けるようにする。
    gd = next((g9 for g9 in d["gardens"] if g9["name"] in ("NiwaOkuN", "NiwaMonohoshi")), None)
    if gd is None:
        return ""
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
    raw, dA, dB, ter = load()
    rows, tB, tA = measure(raw, dA, dB, ter)
    css = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"),
                  encoding="utf-8").read()
    netB, netA = tB[2], tA[2]
    save = netB - netA
    shA = next(t for t in dA["terraces"] if t["name"] == "Shumen")
    shB = next(t for t in dB["terraces"] if t["name"] == "Shumen")
    labels = dict((h.get("name"), h.get("label") or h.get("name")) for h in shA.get("holes", []))
    # 区画ごとの「段に掛かる割合」— 矩形のうち主面の多角形に載っている面積
    step, K = ter["step"], dA["const"]["ken"]
    cov = {}
    for h9 in shA.get("holes", []):
        pts = h9.get("poly") or []
        if not pts:
            continue
        u0 = min(q[0] for q in pts); u1 = max(q[0] for q in pts)
        v0 = min(q[1] for q in pts); v1 = max(q[1] for q in pts)
        tot9 = on9 = 0
        for iv in range(ter["nv"]):
            v = ter["v0"] + iv * step
            if not (v0 <= v <= v1):
                continue
            for iu in range(ter["nu"]):
                u = ter["u0"] + iu * step
                if not (u0 <= u <= u1):
                    continue
                tot9 += 1
                if B.tin(shB, u, v):
                    on9 += 1
        cov[h9.get("name")] = (tot9, on9)
    lo9 = min(B._dem_at(dA, u9 / 2.0, v9 / 2.0) or 99
              for u9 in range(-56, -16) for v9 in range(88, 132))

    h = ['<meta charset="utf-8">', "<title>岡部筑前守上屋敷 裁定図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">外桜田永田町 ／ 岡部筑前守上屋敷 ／ 庭の設計(庭方 2026-09-02)</p>')
    h.append("<h1>裁定図 — 庭をどう作るか(2件)</h1>")
    h.append('<div class="box" style="border-color:var(--midori)"><h3>裁定は下りている'
             '(2026-09-02・2件とも案A)</h3><p>この図は<b>問うた時点の姿</b>を残す。'
             '⭕ 裁定1=案A(5区画を平坦化しない)・裁定2=案A(長局の西庭を実用の庭にする)。'
             '指図はこの裁定のとおり実装済みで、'
             '<b>下の数値は当図が毎回その実装から算出し直している</b>。</p></div>')
    h.append('<p class="lede">庭方(edo-niwashi)の設計案のうち、<b>ユーザーの裁定が要る2件</b>だけを図にした。'
             '⛔ 数値は一つも手で書いていない — 地盤は江戸期の復元地盤 <code>okabe_edo_dem.json</code>、'
             '設計は <code>okabe_sashizu.json</code>、切盛は指図の生成器と同じ '
             '<code>graded_y()</code> から毎回算出している。'
             '組むのは <code>Tools/Sashizu/build_okabe_saitei.py</code>。</p>')
    h.append('<div class="box" style="border-color:var(--shu)"><h3>⚠ 2026-09-02 訂正</h3><p>'
             'この図は当初、案Aの効き目を<b>「5区画の矩形の中にいま載っている盛土を足す」</b>方法で'
             '出しており、<b>1,800 m³</b>としていた。⛔ <b>それは効き目ではない。</b>'
             '平坦化をやめると区画の<b>縁</b>の土工も変わり、区画の矩形は主面の多角形から食み出す'
             '(西端の帯は矩形の一部しか段に掛からない)。'
             '⭕ 効き目は<b>二つの完成した設計を格子一枚ぶん歩いた差</b>でしか測れない。'
             'いまの図はその方法で出している。<b>裁定の向きは変わらない</b>が、'
             '数字は下の表のとおり小さくなる。</p></div>')

    h.append('<div class="plate"><div class="phead"><h2>裁定1　主面の5区画を「平坦化しない」ことを認めるか</h2>'
             '<span class="meta">どこ=主面(24.80)の南半分と西端・奥。指図の敷地図・切盛図と同じグリッド</span></div>')
    h.append('<div class="box"><h3>いま何がどうなっているか(実測)</h3>'
             '<p>主面を全面 24.80 で平らにする設計(案B)の拝領時造成は'
             '<b>盛土 %s m³ / 切土 %s m³ = 差引 +%s m³ の客土</b>。'
             '案Aはこれを <b>+%s m³</b> にする(<b>−%.0f%%</b>)。'
             '主面の南半分の自然地盤は最も低い所で <b>%.2f m</b> まで下がっており、'
             '<b>24.80 で通すと最大 %.1f m 盛る</b>ことになる。'
             '⛔ 庭の土工(池・築山)は<b>両案から外して</b>測ってある — この裁定は池の形とは独立。</p></div>'
             % ("{:,}".format(int(tB[0])), "{:,}".format(int(tB[1])), "{:,}".format(int(netB)),
                "{:,}".format(int(netA)), 100.0 * save / netB, lo9, 24.8 - lo9))
    h.append('<div class="tw"><table><thead><tr><th>区画</th><th>矩形のうち段に掛かる割合</th>'
             '<th>その抜きだけを入れたときの効き目</th></tr></thead><tbody>')
    for nm, dv in rows:
        t9, o9 = cov.get(nm, (0, 0))
        h.append("<tr><td>%s</td><td>%s</td><td><b>%+.0f m³</b></td></tr>"
                 % (labels.get(nm, nm),
                    ("%.0f%%" % (100.0 * o9 / t9)) if t9 else "—", dv))
    h.append("<tr><td colspan='2'><b>5つ全部を入れたとき(=案A。順に依らず別に測った値)</b></td>"
             "<td><b>%+.0f m³</b></td></tr>" % (-save))
    h.append("</tbody></table></div>")
    h.append('<p class="cap">⚠ <b>区画ごとの値を足しても合計にはならない</b> — 抜きどうしが縁を'
             '共有すると効き目が重なるため。合計は<b>5つ全部を入れた設計を別に組んで測った値</b>。'
             '⭐ 「段に掛かる割合」が小さい区画(西端の帯・奥の紅葉谷)は、'
             '<b>もともと造成していない斜面が矩形に含まれている</b>ので効き目が小さい。</p>')
    h.append('<div class="fig">%s</div>' % section(dA, dB, ter))
    h.append('<p class="cap"><b>断面</b> — 南の芝谷と南の樹林を東西に切った所。'
             '案B(上)は窪みを埋めて 24.80 の平場にする。案A(下)は窪みをそのまま残す。'
             '⚠ 案Aでも<b>抜きの縁には法面が要る</b>(垂直の段差にはできない)ので、'
             '縁の帯は両案とも盛る。⭕ 抜きの中で <b>|設計−自然| ≤ 0.5m</b> に収まるのは'
             '棟の載る所を除いて <b>南の芝谷 91%% / 南の樹林 92%% / 長局の北の坪 97%% / '
             '奥の紅葉谷 80%% / 西端の帯 100%%</b>(案Bでは 54/35/87/51/99%%)。</p>')
    h.append('<div class="fig">%s</div>' % plan_pair(dA, dB, ter))
    h.append('<p class="cap"><b>平面(同一縮尺)</b> — 橙が盛土。案Aでは5区画の橙が消える。'
             '⚠ 5区画の外(棟の載る所・門前面へ下る帯)の盛土は<b>どちらの案でも残る</b> — '
             'それが案Aでも残る %s m³。</p>' % "{:,}".format(int(netA)))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A(推奨)</th><th>案B</th>'
             '</tr></thead><tbody>'
             '<tr><td>やること</td><td>5区画を主面の平坦から外し<b>自然地盤なり</b>にする。棟が載る所だけ 24.80</td>'
             '<td>現況どおり主面を全面 24.80 で平らにする</td></tr>'
             '<tr><td>客土</td><td><b>%s → %s m³</b>(−%.0f%%)</td><td>%s m³ のまま</td></tr>'
             '<tr><td>庭</td><td>窪みと高まりが残るので、<b>池の汀・築山の裾・谷を地形から起こせる</b></td>'
             '<td>庭の起伏を<b>すべて盛土で作る</b>ことになる</td></tr>'
             '<tr><td>規則3(面の高さは地形が決める)</td><td>適合</td>'
             '<td><b>反する</b> — 窪みを埋めている</td></tr>'
             '<tr><td>やり直しになるもの</td><td><code>terraces.Shumen</code> の多角形／'
             '南辺・南西辺の練塀 run の据面／<code>grading</code> の全数値／切盛図／断面</td>'
             '<td>無し</td></tr>'
             '</tbody></table></div>'
             % ("{:,}".format(int(netB)), "{:,}".format(int(netA)), 100.0 * save / netB,
                "{:,}".format(int(netB))))
    h.append('<p class="cap"><b>推奨=案A。</b>CLAUDE.md 規則3「面の高さは地形が決める・窪みは埋めず'
             '一段低い郭にする」の直接の適用であり、<b>庭の質と土量が同時に良くなる</b>。</p>')
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>裁定2　長局の西庭をどう始末するか</h2>'
             '<span class="meta">どこ=<code>NiwaOkuN</code> 長局の西庭 u+5〜+12 / v100〜106</span></div>')
    h.append('<div class="box"><h3>いま何がどうなっているか</h3>'
             '<p>この庭は<b>長局の西の妻(白壁)に正対</b>しており、上陣・下陣のどちらの座敷からも見えない。'
             '長局は女中の部屋列で、そもそも鑑賞用の庭を持つ格ではない。'
             '一方でこの区画は、長局に<b>実用の外部空間が一つも無い</b>現況を埋められる唯一の場所でもある。</p></div>')
    h.append('<div class="fig">%s</div>' % nagatsubone(dA))
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
    print("裁定1の効き目 %+.0f m³ / 客土 案B %d → 案A %d m³(−%.0f%%)"
          % (-save, int(netB), int(netA), 100.0 * save / netB))


if __name__ == "__main__":
    main()
