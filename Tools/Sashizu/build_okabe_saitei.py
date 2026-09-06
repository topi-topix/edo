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
    h.append("<h1>裁定図 — 岡部筑前守上屋敷(%d件)</h1>" % len(SAITEI_STATUS))
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

    # ---------------------------------------------------------- 第二次 3件
    dA2 = B.pipeline(json.loads(json.dumps(raw)))
    dB2 = _variant2(raw, batterFill=1.0)
    dC2 = _variant2(raw, featherCap=25.0)

    def _tot(dd):
        we = dict((t["name"], B.walled_edges(dd, t)) for t in dd["terraces"])
        st, K9 = ter["step"], dd["const"]["ken"]
        A9 = (st * K9) ** 2
        f = c = 0.0
        for iv in range(ter["nv"]):
            v = ter["v0"] + iv * st
            for iu in range(ter["nu"]):
                u = ter["u0"] + iu * st
                n = ter["h"][iv][iu]
                if n is None:
                    continue
                dz = B.graded_y(dd, u, v, n, we) - n
                if dz > 0:
                    f += dz * A9
                else:
                    c += -dz * A9
        return f - c

    nA, nB, nC = len(B.batter_check(dA2, ter)), len(B.batter_check(dB2, ter)), len(B.batter_check(dC2, ter))
    tA, tB2, tC = _tot(dA2), _tot(dB2), _tot(dC2)
    rows2 = _step_line(dA2, ter)
    K9 = dA2["const"]["ken"]
    wallL = (rows2[-1][0] - rows2[0][0]) * K9 if rows2 else 0.0
    wallH = (min(r[2] for r in rows2), max(r[2] for r in rows2),
             sum(r[2] for r in rows2) / len(rows2)) if rows2 else (0, 0, 0)

    h.append('<hr style="margin:44px 0 8px;border:0;border-top:2px solid var(--rule)">')
    h.append('<h2 style="margin-top:0">第二次の裁定 — 3件(2026-09-02)</h2>')
    h.append('<p class="lede">3役(考証・検図・庭方)の初回検分で出た55件のうち、'
             '<b>46件は指図方が直し</b>、9件が残った。そのうち<b>意匠の判断が要る3件</b>を図にする。'
             '⛔ 指図方には値を入れさせていないので、いまの指図は'
             '<b>この3件を「未解決」として毎回刷る</b>状態にしてある。</p>')

    h.append('<div class="plate"><div class="phead"><h2>裁定3　西の法尻の段差をどう受けるか</h2>'
             '<span class="meta">どこ=敷地北西 グリッド u−8〜+16.5 / v113〜115。指図の切盛図と断面②③</span></div>')
    h.append('<div class="box"><h3>いま何がどうなっているか(実測)</h3>'
             '<p>主面(24.80)の西縁から出る盛土(法 1:%.1f)が、'
             '<b>自然斜面より緩いため到達距離 %.0fm の中で着地しません</b>。'
             '行き場を失った設計面はそこで打ち切られ、<b>延長 %.1fm・丈 %.2f〜%.2fm(平均 %.2fm)の'
             '垂直の段差</b>が残ります。法面の検査が <b>%d 件</b>出しているのがこれです。'
             '⚠ これは庭の追加が原因ではなく、<b>以前から潜んでいたもの</b>です。</p></div>'
             % (dA2["const"]["batterFill"], dA2["const"]["featherCap"], wallL,
                wallH[0], wallH[1], wallH[2], nA))
    h.append('<div class="fig">%s</div>' % toe_section(dA2, dB2, dC2, ter))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A</th><th>案B</th><th>案C</th>'
             '</tr></thead><tbody>'
             '<tr><td>やること</td><td><b>土留めを立てる</b><br>(法面は 1:%.1f のまま)</td>'
             '<td><b>盛土を 1:1.0 へ</b><br>急にする</td>'
             '<td><b>法面の到達を</b><br>25m へ延ばす</td></tr>'
             '<tr><td>法面の検査</td><td>%d件 → <b>0件</b><br>(段差を壁が受ける)</td>'
             '<td>%d件 → <b>%d件</b></td><td>%d件 → <b>%d件</b></td></tr>'
             '<tr><td>客土</td><td>%s m³ のまま</td><td><b>%s m³</b>(%+.0f)</td>'
             '<td><b>%s m³</b>(%+.0f)</td></tr>'
             '<tr><td>新しく要る物</td><td><b>石垣</b><br>延長%.0fm・丈 最大%.2fm</td>'
             '<td>無し(定数1つ)</td><td>無し(定数1つ)</td></tr>'
             '</tbody></table></div>'
             % (dA2["const"]["batterFill"], nA, nA, nB, nA, nC,
                "{:,}".format(int(tA)), "{:,}".format(int(tB2)), tB2 - tA,
                "{:,}".format(int(tC)), tC - tA, wallL, wallH[1]))
    h.append('<p class="cap"><b>⛔ 案ごとに引っかかること</b><br>'
             '<b>案A</b> … 石垣が1本増え、図・断面・部材表・実装のすべてに波及する。'
             '⚠ 郭内の土留めは 2026-08-23 に全廃しており、これを立てると<b>その方針が戻る</b>。<br>'
             '<b>案B</b> … ⛔ <b>1:1.0 の裸の盛土は崩れる。</b>'
             '当図が 1:1.5 を採っているのはそれが安全側の標準だから。⭕ 土留めとの併用なら成り立つ。<br>'
             '<b>案C</b> … ⛔ <b>西斜面を 25m 造成する</b>ことになり、'
             'CLAUDE.md 規則9「地形は現地形に従う・造成は最小限」に触れる。</p>')
    h.append('<p class="cap"><b>推奨=案A(土留め)。</b>案Bは客土が %s m³ 減って魅力的に見えますが、'
             '⛔ <b>1:1.0 の裸の盛土は崩れる</b>ので、結局は土留めが要ります。'
             '案Cは検査こそ通るものの、⛔ <b>造成を西斜面へ 25m 広げる</b>ので規則9に触れます。'
             '⭕ 案Aは「造成した以上、その足元は自分で受ける」という素直な形で、'
             '<b>44.5m の石垣は当屋敷の外周(約780m)に比べれば小さい</b>。'
             '⚠ ただし郭内の土留めを全廃した 2026-08-23 の方針が戻ることになります。</p>'
             % "{:,}".format(int(abs(tB2 - tA))))
    h.append("</div>")

    zones = {}
    for m in dA2["munes"]:
        zones.setdefault(m.get("zone", "—"), []).append(m)
    h.append('<div class="plate"><div class="phead"><h2>裁定4　「表役所」を作るか、作らない理由を書くか</h2>'
             '<span class="meta">どこ=表向(車寄・玄関棟・書院)。指図「在るべき役割との照合」の表</span></div>')
    h.append('<div class="box"><h3>いま何がどうなっているか</h3>'
             '<p>スキルの役割表(外の錨)が<b>「表役所」を必須</b>とするのに、'
             '当図には<b>棟も室もありません</b>。'
             '⛔ この行はつい先ほどまで「○(達成)」と刷られていました — '
             '検査が <code>json</code> の文字列一致で、'
             '<b>「当図に表役所という棟は無く」という否定文に一致していた</b>ためです'
             '(当邸4例目の同型)。いまは正しく <b>⛔</b> が出ます。</p></div>')
    h.append('<div class="tw"><table><thead><tr><th>ゾーン</th><th>棟</th><th>室</th>'
             '</tr></thead><tbody>'
             + "".join("<tr><td>%s</td><td><code>%s</code></td><td class='note'>%s</td></tr>"
                       % (z, m["name"], "・".join(r["name"] for r in m.get("rooms", [])) or "—")
                       for z in ("表向", "中奥", "奥向") for m in zones.get(z, []))
             + "</tbody></table></div>")
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A</th><th>案B</th><th>案C</th>'
             '</tr></thead><tbody>'
             '<tr><td>やること</td><td><b>表役所の棟を新設</b>する(表向・玄関棟の北)</td>'
             '<td><b>玄関棟の中に室として設ける</b>(使者之間の隣)</td>'
             '<td><b>作らない</b>と決め、理由を指図に書く</td></tr>'
             '<tr><td>建蔽率</td><td>上がる(棟が1つ増える)</td><td><b>変わらない</b></td>'
             '<td>変わらない</td></tr>'
             '<tr><td>波及</td><td>棟と室の表・建蔽率・切盛・実装</td>'
             '<td>玄関棟の室割りだけ</td><td>文章だけ</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap">⚠ <b>史実はどの案も確度U</b> — 当屋敷の指図は現存未確認です。'
             '⭕ ただし案Bは<b>室割りが図面だけの情報</b>で実装との突き合わせ対象外なので、'
             '間違っていたときの影響がいちばん小さい。'
             '⛔ 案Cを採る場合は「<b>無かった</b>」も推定であると明記が要ります。</p>')
    h.append('<p class="cap"><b>推奨=案B(玄関棟の室として設ける)。</b>'
             '表役所は留守居・用人が詰める事務の場で、'
             '<b>当家の石高(5万3千石)では独立した棟を構える規模ではない</b>と考えられます。'
             '⭕ 玄関棟には既に<b>使者之間</b>があり、来客の応対と事務は同じ棟に納まるのが自然です。'
             '⚠ いずれの案も<b>確度U(当方の設計判断)</b>で、当屋敷の指図は現存未確認です。</p>')
    h.append("</div>")

    h.append('<div class="plate"><div class="phead"><h2>裁定5　屋敷の西の端をどこまで「奥」とするか</h2>'
             '<span class="meta">どこ=結界塀 W6 の西端(グリッド u−19, v111.25)から西</span></div>')
    h.append('<div class="box"><h3>まず、何の話か</h3>'
             '<p>大名屋敷は<b>表</b>(玄関・書院・客が入る所)と<b>奥</b>(藩主の居間・女中の部屋)を'
             '分けます。建物の中では<b>御錠口</b>という一口の戸で分け、'
             '<b>屋外では塀を回して分ける</b> — これが「結界」です。'
             '当図は結界塀を7区間まわし、中門と木戸を一口ずつ開けました。</p>'
             '<p>⛔ <b>問題は、その一口を両方閉めても、屋敷の西側を回れば表から奥へ行けることです。</b>'
             '下の断面を見てください — 主面(24.80)の西の縁で<b>崖が33mで16m下り</b>、'
             'その先に<b>幅およそ56mの平らな帯(標高8.5・溜池の岸)</b>があります。'
             '⭕ <b>この帯は屋敷の敷地の中で、平らで歩けます。</b>'
             '崖を下りてこの帯を通れば、結界塀の西の端を回り込めます。</p></div>')
    h.append('<div class="fig">%s</div>' % kekkai_section(dA2))
    h.append('<p class="cap"><b>西の縦断</b> — 結界塀 W6 の線をそのまま西へ延ばして切った断面。'
             '塀は崖の上(v=111.25)で終わっています。⭕ <b>崖そのものは急(最急71%)ですが、'
             'その下の帯は平ら</b>で、屋敷の中を歩いて回れます。</p>')
    h.append('<div class="fig">%s</div>' % kekkai_plan(dA2))
    h.append('<p class="cap"><b>平面(上の断面と同じグリッド)</b> — '
             '朱の破線が、開口を両方閉めても残る回り込みです。</p>')
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A 塀を崖の下まで延ばす</th>'
             '<th>案B 崖の上で結界を終える</th></tr></thead><tbody>'
             '<tr><td>やること</td><td>W6 を<b>崖に沿って約76m 延ばし</b>、'
             '平らな帯を横切って外周の木柵まで届かせる</td>'
             '<td>結界塀はいまのまま。<b>崖から下は「表でも奥でもない外構の地」</b>とする</td></tr>'
             '<tr><td>屋敷はどうなるか</td><td>表と奥が<b>屋外でも完全に分かれる</b></td>'
             '<td>⛔ <b>回り込みは残る</b>(崖を下って登る道)</td></tr>'
             '<tr><td>建てる物</td><td><b>のし塀 h1.8m を 76m</b><br>うち33mは最急71%の崖</td>'
             '<td>無し</td></tr>'
             '<tr><td>指図の書き方</td><td>「屋外で閉じている」と書ける</td>'
             '<td>⛔ 「結界は<b>崖の上まで</b>」へ書き直す</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap">⚠ <b>典拠はどちらも確度U(当方の設計判断)。</b>'
             '「表と奥を分ける」ことの実体は<b>御錠口=確度A</b>で、'
             '<b>屋外にも結界を回すこと自体がもともと当方の外挿</b>です。</p>')
    h.append('<p class="cap"><b>推奨=案B(崖の上で終える)。</b>'
             '⭕ 崖は平場でも歩く道でもなく、屋敷の実際の境は<b>外周の木柵(溜池の堤)</b>です。'
             '⛔ 内部を分けるための塀を、最急71%の崖に76m下ろすのは'
             '<b>5万3千石の屋敷の格に合わず、そうした例の典拠もありません</b>。'
             '⚠ 案Bを採ると「屋外で閉じている」とは書けなくなりますが、'
             '⭕ <b>もともと屋外の結界は当方の外挿</b>なので、'
             '「崖の上まで塀を回した」と正直に書くほうが図として強くなります。</p>')
    h.append("</div>")

    # ---------------------------------------------------------- 第三次 裁定6
    ter6 = B.load_terrain(os.path.join(DOC, "okabe_edo_dem.json"))
    svg6, ar6 = hojiri_plan(dA2, ter6)
    tot6 = (ar6["mado"] + ar6["S"] + ar6["N"]) / 3.3058
    h.append('<hr style="margin:44px 0 8px;border:0;border-top:2px solid var(--rule)">')
    h.append('<h2 style="margin-top:0">第三次の裁定 — 1件(2026-09-02)</h2>')
    h.append('<div class="plate"><div class="phead"><h2>裁定6　溜池の岸の平らな帯に、建物を置くか</h2>'
             '<span class="meta">どこ=西の法尻から柵まで(v134〜165)。指図「西の斜面と溜池の岸」</span></div>')
    h.append('<div class="box"><h3>まず、何の話か</h3>'
             '<p>屋敷の西は、平場から林の斜面を下りると<b>溜池の岸に平らな帯</b>(勾配 2〜7%%)があり、'
             'それが区画の中に <b>%.0f坪</b> あります。いまの指図はここを<b>刈草地に榎3本</b>で空けています。'
             '⛔ ところが「なぜ空けるのか」の理由も典拠も書いてありません。'
             '考証方は「<b>江戸の上屋敷がこの規模の平場を草地のまま空けた例を知らない</b>」と言い、'
             '庭方も「<b>建物があるほうが尤もらしい</b>」と見ています。</p>'
             '<p>⭕ 同時代の図(江戸名所図会「溜池」)は、<b>同じ崖の裾に長屋の屋根の列</b>を描いています。'
             '⚠ それは南隣の十坊のものである可能性が高く、当邸の裾と断定はできません。'
             '⛔ ただし「断定できない」は「無かった」ではありません。</p>'
             '<p>⛔ <b>見透しの窓の扇の中(%.0f坪)は、どちらの案でも空けたまま</b>です — '
             '屋根が窓へ入ると溜池の借景が壊れます。置ける余地は<b>南 %.0f坪・北 %.0f坪</b>。</p></div>'
             % (tot6, ar6["mado"] / 3.3058, ar6["S"] / 3.3058, ar6["N"] / 3.3058))
    h.append('<div class="fig">%s</div>' % svg6)
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A 草地のまま</th>'
             '<th>案B 南北の余地に建物を置く</th></tr></thead><tbody>'
             '<tr><td>やること</td><td>いまのまま。<b>「空けるのは当方の裁定(U)」</b>と理由を書く</td>'
             '<td>窓の外の南北に<b>家臣長屋・厩・土蔵</b>の類を置く</td></tr>'
             '<tr><td>見た目</td><td>林の裾に開けた草地と大木3本、<br>その先に柵と葦と水面</td>'
             '<td>林の裾に長屋の屋根が並ぶ<br>(名所図会の「裾の屋根の列」に近づく)</td></tr>'
             '<tr><td>史料</td><td>⚠ 空地であった典拠は無い(U)</td>'
             '<td>⚠ 当邸の裾に建物があった典拠も無い(U)</td></tr>'
             '<tr><td>建蔽率</td><td>11.2% のまま</td><td>上がる(棟数による)</td></tr>'
             '<tr><td>波及</td><td>文章だけ</td><td>棟と室の表・建蔽率・動線・部材</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>推奨=案B。</b>⭕ 理由は「江戸のその土地として尤もらしいか」の一点です — '
             '<b>千坪の平場を上屋敷が空けておく例が無く</b>、建蔽率 11.2% の低さの一因もここにあります。'
             '⚠ ただし置く物と位置は<b>屋敷の型(家臣長屋は外周・土蔵は勝手の側)から決める意匠判断</b>で、'
             '典拠はどちらの案も U です。⭕ 案Bなら、次の巡で「何をどこに」を図にしてお諮りします。</p>')
    h.append("</div>")

    # ---------------------------------------------------------- 第四次 裁定7
    svg7 = mado_plan(dA2, ter6)
    h.append('<hr style="margin:44px 0 8px;border:0;border-top:2px solid var(--rule)">')
    h.append('<h2 style="margin-top:0">第四次の裁定 — 1件(2026-09-03)</h2>')
    h.append('<div class="plate"><div class="phead"><h2>裁定7　見透しの窓を、どこまで細めるか</h2>'
             '<span class="meta">どこ=西の斜面の林の中、床几(u+0.5/v107.8)から溜池へ開く扇(v108.5〜165)。'
             '指図「西の斜面と溜池の岸」</span></div>')
    h.append('<div class="box"><h3>まず、何の話か</h3>'
             '<p>西の崖の林には、床几から溜池を見透すための<b>扇形の切れ目(見透しの窓)</b>が開けてあります。'
             '⚠ この窓は<b>当方の設計判断(確度U)</b>で、当邸にあった典拠はありません(⛔ 無かった典拠もありません)。'
             '同時代の絵(江戸名所図会「溜池」)がこの崖について保証するのは「<b>上=樹林・下=草地の二層</b>」までで、'
             '切れ目の有無は読めません。</p>'
             '<p>⛔ ただし、いまの窓は<b>法肩の松を置かない区間が稜線の24%・林の下端の口が35%</b>あり、'
             '絵の「上部が密で連続した林」の印象と並べると大きい — <b>「崖に鬱蒼とした林」というご認識に直接ぶつかります</b>。'
             '庭方は「窓を残すか」ではなく「<b>どこまで細めるか</b>」が争点だと見ています。</p>'
             '<p>⭐ 庭方の算出で分かった大事な一点: <b>視野を決めているのは林の下端(v130)での扇の幅</b>で、'
             'その先の刈草地には何も遮る物がない。⛔ したがって<b>区画界の側(下端)だけ細めても見える水面は 1m² も減らず</b>、'
             '細めるなら<b>扇ぜんたいを相似に</b>細めるしかありません。下の表はその前提です。</p></div>')
    h.append('<div class="fig">%s</div>' % svg7)
    rows = "".join(
        '<tr><td><b>%.0f間</b>%s</td><td>%.1f間</td><td>%.1f°</td><td>%s m</td><td>%s m</td>'
        '<td><b>%s</b>%s</td><td>%.1f間(%d%%)</td><td>%.1f間(%d%%)</td><td>%d坪</td><td>%d%% / %d%%</td></tr>'
        % (r[0], "(現行)" if i == 0 else "", r[1], r[2], r[3], r[4], "{:,}".format(r[5]),
           "" if i == 0 else "(−%d%%)" % round(100 - 100.0 * r[5] / MADO_TBL[0][5]),
           r[6], r[7], r[8], r[9], r[10], r[11], r[12])
        for i, r in enumerate(MADO_TBL))
    h.append('<div class="tw"><table><thead><tr><th>区画界の開き</th><th>林の下端 v130 の幅<br>(効く所)</th>'
             '<th>開き角</th><th>水面が見えはじめる</th><th>見える水面の幅<br>近 / 遠</th><th>見える水面 m²</th>'
             '<th>法肩の松を置かない区間<br>(稜線に対し)</th><th>林の下端の口<br>(下端に対し)</th><th>窓の面積</th>'
             '<th>対岸から見える<br>奥向棟 / 見晴らしの台</th></tr></thead><tbody>%s'
             '<tr><td>下端だけ細める<br>(18/14/10間)</td><td>15.0間</td><td>37.5°</td><td>130〜162 m</td>'
             '<td>93 / 122 m</td><td><b>4,627</b>(変わらず)</td><td>11.8間(24%%)</td><td>17.0間(35%%)</td>'
             '<td>857〜734坪</td><td>—</td></tr></tbody></table></div>' % rows)
    h.append('<p class="cap">庭方4巡目の算出(眼=床几 眼高25.55 / 汀の柵の天端 12.51 / 水面 6.60・方位 0.25°刻み)。'
             '⚠ 「見えはじめる」は方位ごとの幅。⚠ どの案でも<b>奥向棟の北端(u+3.0)は対岸から隠れません</b> — '
             '対岸の汀が北へ伸びて斜めに覗けるためで、扇を細めても解けない。'
             '北の松の帯を延ばすか扇の芯を南へ振るかは<b>裁定を要しない設計判断として庭方に決めさせます</b>。</p>')
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A 23間のまま(現行)</th>'
             '<th>案B 14間に細める</th><th>案C 10間に細める</th></tr></thead><tbody>'
             '<tr><td>崖の見た目(溜池側から)</td><td>稜線の1/4に松が無く、林の下端の1/3が口</td>'
             '<td>稜線の 16%、下端の 23% が口。<br>「密で連続した林」に近づき、切れ目はまだ読める</td>'
             '<td>稜線の 12%、下端の 17%。<br>林はほぼ連続。切れ目は細い筋</td></tr>'
             '<tr><td>床几からの景</td><td>水面 93〜122m 幅・4,627m²</td>'
             '<td>水面 59〜74m 幅・2,464m²(−47%)。<br>対岸の町並みまで一望は残る</td>'
             '<td>水面 43〜53m 幅・1,705m²(−63%)。<br>「筋の向こうに水」の景</td></tr>'
             '<tr><td>御殿が対岸から見える割合</td><td>奥向 89% / 台 86%</td><td>奥向 67% / 台 57%</td><td>奥向 56% / 台 41%</td></tr>'
             '<tr><td>動く物</td><td>無し</td><td>扇3点・法肩の松の区間・林の下端の口・見所の表</td><td>同左</td></tr>'
             '<tr><td>他邸への波及</td><td>無し</td><td>無し(区画の中だけ)</td><td>無し</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>推奨=案B(14間)。</b>⭕ 理由は「江戸のその土地として尤もらしいか」の一点です — '
             '絵が保証する「上部が密で連続した林」に稜線の 84%・下端の 77% で近づきながら、'
             '床几からはなお 60〜70m 幅の水面と対岸が見え、<b>窓を開けた意味(借景)が残る</b>幅です。'
             '⚠ 案Cは林としては最も尤もらしいが、窓が「細い筋」になり、窓を設けた設計自体の意味が薄れる — '
             'それなら窓を閉じる(林を連続させる)ほうが素直で、それは別の裁定になります。'
             '⛔ 窓の有無・幅ともに典拠は U で、どの案も史料が否定するものではありません。</p>')
    h.append("</div>")

    # ---------------------------------------------------------- 第五次 裁定8
    svg8 = obi_plan(dA2, ter6)
    site_m2 = B.polygon_area_m2(dA2) if hasattr(B, "polygon_area_m2") else 34093.2
    built0 = 3803.0
    h.append('<hr style="margin:44px 0 8px;border:0;border-top:2px solid var(--rule)">')
    h.append('<h2 style="margin-top:0">第五次の裁定 — 1件(2026-09-03)</h2>')
    h.append('<div class="plate"><div class="phead"><h2>裁定8　法尻の帯に、何をどこに置くか</h2>'
             '<span class="meta">どこ=溜池の岸の平らな帯(v131〜165)、見透しの窓の扇の南と北。指図「西の斜面と溜池の岸」</span></div>')
    h.append('<div class="box"><h3>まず、何の話か — 裁定6=B(建物を置く)を受けて</h3>'
             '<p>置く物の<b>型は考証方が史料で決めました</b>: 隣街区の丹羽邸(二本松10万石)の発掘で「台地の上に御殿 / 西の低地は'
             '<b>詰人(中間・足軽)の長屋地区</b>(長屋・井戸・かわや・排水溝)」という型が出ています(確度S。当邸へ当てるのは外挿でB)。'
             '⛔ <b>厩は不可</b>(切絵図に崖の西・北に道が無く馬の出入口が取れない=S)、土蔵の主群・舟蔵・離れ・畑も型に合いません。'
             '棟は<b>水に背を向け</b>(水側は盲の板壁・開口は山側)、屋根は<b>桟瓦の黒</b>、外へ出る門は無く'
             '<b>勝手の坂1本で上と繋がる袋の一画</b>です。</p>'
             '<p>景の制約は<b>庭方</b>: 林の裾(v131〜145)に置き汀寄りに置かない(対岸から「林→屋根→榎→草→葭→水」の層になる)/'
             '長手は等高線なり・奥行2.5〜3間(切盛±0.5m以内)/ <b>榎3本は残し軒から幹まで6m</b>/ 南隅(勾配11.6%)には建てない/'
             '北の余地は幅8.5間で榎が中央なので小さく寄せるか建てない。</p>'
             '<p>⭐ 同時に、<b>窓の中の芝の小径は廃します</b>(庭方の提案を採用)— 14間の窓には折り返しの路が入らず、'
             '勝手の坂が木戸への道も兼ねるので、窓は芝だけの切れ込みになり景が良くなります。</p></div>')
    h.append('<div class="fig">%s</div>' % svg8)
    rows = []
    for nm in ("A", "B", "C"):
        mm, ss = OBI_VARIANTS[nm]
        st = _obi_stats(dA2, ter6, mm)
        area = sum(x["area"] for x in st); dzmax = max(x["dz"] for x in st)
        hh = sum(int(x["ken"] / 1.5) for x in st if x["use"].startswith("詰人"))
        gaps = _enoki_gap(dA2, mm)
        rows.append('<tr><td><b>案%s</b></td><td>%d棟(%s)</td><td>%.0f m² = %.0f坪</td><td>約%d世帯</td>'
                    '<td>%.1f%% → <b>%.1f%%</b></td><td>%.2f m</td><td>%s</td><td>%s</td></tr>'
                    % (nm, len(mm), "・".join(x["id"] for x in st), area, area / 3.3058, hh,
                       100 * built0 / site_m2, 100 * (built0 + area) / site_m2, dzmax,
                       " / ".join("%s %.1fm" % g for g in gaps),
                       "・".join(s[0] for s in ss)))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>棟</th><th>建坪</th><th>詰人(1.5間/世帯)</th>'
             '<th>建蔽率</th><th>棟の下の切盛の最大</th><th>榎の幹から軒まで</th><th>小物</th></tr></thead><tbody>%s</tbody></table></div>'
             % "".join(rows))
    h.append('<p class="cap">どの案も勝手の坂は同じ1本(仮の折れで %.0fm・林を幅2mで抜く=約 %.0f m²・林の3%%前後)。'
             '切盛は棟ごとに面を持つ前提(帯全体は平らにしない)。⚠ 棟の座標は裁定のための仮置きで、'
             '決まったら指図方が書き起こし、切盛±0.5m・榎の離れ6m・窓の視野(棟の頂点も総当たり)の検査で検めます。'
             '⛔ 詰人の人数の典拠(軍役→江戸詰人数)は当プロジェクトに無く、世帯数は U のままです。</p>'
             % (_saka_len(dA2), _saka_len(dA2) * 2.0))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A 南に一組(長屋2棟+物置)</th>'
             '<th>案B 南に一組+北に1棟</th><th>案C 南に1棟だけ</th></tr></thead><tbody>'
             '<tr><td>対岸から見える屋根</td><td>林の裾に黒瓦の低い線が2本、榎E1が間を切る</td>'
             '<td>同左+北にもう1本(窓の両側に屋根が並ぶ)</td><td>1本だけ。裾はほぼ草地のまま</td></tr>'
             '<tr><td>尤もらしさ</td><td>丹羽の型(詰人の一画)に最も近く、控えめ。井戸端に大木</td>'
             '<td>裾の景は最も名所図会に近いが、北は幅8.5間で榎E3に迫り窮屈</td><td>「一画」と呼ぶには小さい。裁定6=Bの意図に届きにくい</td></tr>'
             '<tr><td>典拠の強さ</td><td>B(型)+U(棟数・位置)</td><td>同左。北の棟は景観の担保だけ(名所図会は根拠に使わない)</td><td>同左</td></tr>'
             '<tr><td>動く物</td><td>棟3・小物2・坂1・排水溝・帯DをD1/D2に</td><td>+棟1・かわや1</td><td>棟1・小物2・坂1</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>推奨=案A。</b>⭕ 理由は「江戸のその土地として尤もらしいか」の一点です — '
             '隣街区で発掘された「低地=詰人の長屋地区」の型を、当邸の帯の広さ(南583坪)に合う最小の一組で写し、'
             '<b>榎3本を残して屋根の列を大木が切る</b>裾の景になります。⚠ 案Bの北の棟は景としては良いが、'
             '幅8.5間の余地の中央に榎E3が立ち、6mの離れを取ると4.5間の小棟しか入らず、窮屈さが目立ちます。'
             '⛔ 当邸のこの帯についての典拠はBとUだけなので、控えめに置くのが典拠の強さに見合います。</p>')
    h.append("</div>")

    # ---------------------------------------------------------- 第六次 裁定10・11(部材の実寸が出て初めて見えた高さの矛盾)
    import base64 as _b64
    def _svg_img(fn):
        raw = io.open(os.path.join(DOC, fn), "rb").read()
        if b"xmlns=" not in raw[:300]:
            raw = raw.replace(b"<svg ", b'<svg xmlns="http://www.w3.org/2000/svg" ', 1)
        return '<img alt="%s" style="width:100%%;max-width:960px;display:block" src="data:image/svg+xml;base64,%s">' % (fn, _b64.b64encode(raw).decode("ascii"))
    h.append('<hr style="margin:44px 0 8px;border:0;border-top:2px solid var(--rule)">')
    h.append('<h2 style="margin-top:0">第六次の裁定 — 2件(2026-09-04)。⚠ 部材を焼いて初めて見えた高さの矛盾</h2>')
    h.append('<div class="plate"><div class="phead"><h2>裁定9　検分の輪をどう扱うか(三巡則)</h2>'
             '<span class="meta">どこ=指図全体と検図関門の扱い。掲示板 EDO-0118 / EDO-0125</span></div>'
             '<div class="box"><p>5巡目の新規が 49 件で閾値 20 を超えたため手を止め、A(関門2本を足し設計を凍結して6巡目1回・新規10未満でなければB)/ '
             'B(検分の輪を止め関門赤のまま実装へ)/ C(寝かす)を表で諮った(空間の裁定ではないので図は無い)。'
             '<b>ユーザー裁定=A</b>。6巡目は 34 件(全件が図と文章の側・設計値は3役とも「決定は全部届いた」)で閾値を超え、<b>約束どおり案Bへ移った</b>(2026-09-03)。</p></div></div>')
    h.append('<div class="plate"><div class="phead"><h2>裁定10　車寄の屋根が玄関棟の屋根面に食い込む — どう納めるか</h2>'
             '<span class="meta">どこ=玄関棟(11×11間)の参道側(v0 の面)に付く車寄(3×2間)。指図「主郭」其十九の取り合い</span></div>')
    h.append('<div class="box"><h3>まず、何の話か</h3>'
             '<p>車寄は玄関の前に張り出す屋根つきの寄せです。部材方が桟瓦の勾配 5.5寸(在庫の瓦の実測)で焼いたところ、'
             '3間の幅では<b>棟の天端が 4.34m</b>になり、玄関棟の軒先(床 0.62+2.577=地盤+3.20)より <b>1.14m 高く</b>、'
             '背面の屋根が玄関棟の屋根面へ食い込みます。⭕ 実物の車寄は母屋の屋根へ差し込んで納めるのが普通で、'
             '食い込み自体は誤りではありません。⛔ ただし瓦の勾配を寝かせて逃げる道は「自作の瓦の凹凸が歪む」で却下された前例があり、採っていません。</p></div>')
    h.append('<div class="fig">%s</div>' % _svg_img("okabe_saitei_kurumayose.svg"))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A 桟瓦のまま母屋へ差し込む(現況)</th>'
             '<th>案B 屋根を檜皮か杮葺の緩勾配(3寸)に</th><th>案C 車寄を廃し式台だけ</th></tr></thead><tbody>'
             '<tr><td>棟と軒先</td><td>棟 4.34・玄関棟の軒先 3.20 → 食い込み 1.14m</td><td>棟 ≒3.0 → 軒先の下に 0.20m の余裕</td><td>—</td></tr>'
             '<tr><td>見た目</td><td>参道から見て車寄の切妻が玄関の屋根面に刺さる。格式の高い玄関の姿</td>'
             '<td>屋根材が母屋と変わる(瓦の御殿に板葺の寄せ)。低く軽い</td><td>玄関が平坦になる。5万石の上屋敷の玄関としては寂しい</td></tr>'
             '<tr><td>典拠</td><td>U(車寄の存在自体が [西川1959]A にも [高知2000]A にも無い)</td><td>U</td><td>U</td></tr>'
             '<tr><td>動く物</td><td>無し(据えるだけ)</td><td>部材の焼き直し(屋根材)</td><td>部材を捨て、式台の部材が要る</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>推奨=案A。</b>母屋の屋根面へ差し込む納まりは実物どおりで、瓦の御殿に瓦の車寄が最も尤もらしい。'
             '⚠ 食い込みの線は其十九に寸法で書き、実装は玄関棟の屋根面より内側の面を切り欠く。</p>')
    h.append("</div>")
    h.append('<div class="plate"><div class="phead"><h2>裁定11　御錠口(3間角)の屋根が渡廊下より 2.7m 高い — どう納めるか</h2>'
             '<span class="meta">どこ=中奥棟と奥向棟をつなぐ渡廊下の途中、御錠口 L_Jouguchi(3×3間)。其十九</span></div>')
    h.append('<div class="box"><h3>まず、何の話か</h3>'
             '<p>御錠口は表向と奥向を隔てる関門で、指図は 3間角の一画として持っています。部材方が入母屋 5.5寸で焼くと'
             '<b>棟が床+5.24m</b>になり、幅一間の渡廊下(大棟 床+2.50)より <b>2.74m 高い</b>塔のような姿になります。'
             '⭕ 御錠口を一段高い屋根で標す作りは有り得ますが、当邸の指図に典拠は無く(U)、高さは部材の勾配の帰結です。</p></div>')
    h.append('<div class="fig">%s</div>' % _svg_img("okabe_saitei_jouguchi.svg"))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A 3間角・入母屋のまま(現況)</th>'
             '<th>案B 御錠口を廊下幅(1間)の建具に縮める</th><th>案C 3間角のまま寄棟の緩勾配(3寸)</th></tr></thead><tbody>'
             '<tr><td>棟の高さ</td><td>床+5.24(廊下+2.74)</td><td>廊下と同じ 床+2.50</td><td>≒床+3.4(廊下+0.9)</td></tr>'
             '<tr><td>見た目</td><td>廊下の途中に小さな塔が立つ</td><td>廊下の中の戸だけ。外からは見えない</td><td>低い屋根が少し盛り上がる</td></tr>'
             '<tr><td>典拠</td><td>U</td><td>U(御錠口=建具という理解に近い)</td><td>U</td></tr>'
             '<tr><td>動く物</td><td>無し</td><td>links の寸法(3×3→1×1)・部材を捨てる</td><td>部材の焼き直し(屋根)</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>推奨=案B。</b>御錠口は本来「錠を下ろす口」=建具であって独立の棟ではなく、'
             '廊下幅に縮めれば高さの矛盾ごと消え、外観に塔が立たない。⚠ 焼いた部材は捨てます(規模は小)。</p>')
    h.append("</div>")

    # ---------------------------------------------------------- 裁定12
    h.append('<div class="plate"><div class="phead"><h2>裁定12　表長屋の階と表門の棟高 — 「二階と名乗る5.3mの長屋」をどうするか</h2>'
             '<span class="meta">どこ=辺12(三べ坂)の表長屋 E_Nagaya_S/N と表門(長屋門)。其十六・其十七</span></div>')
    h.append('<div class="box"><h3>まず、何の話か</h3>'
             '<p>指図は表長屋を「二階瓦葺窓付」([西川1959]A)と宣言しながら棟高を <b>5.30m</b> で持っています。在庫の部材は平屋 5.51 / 二階 7.18 で、'
             '5.30 はどちらにも合わず、考証方は「平屋級の高さ」と判定しました(岡山藩の仕様書で二階長屋の軒高だけで 5.06m、根岸家長屋門の実測で二階の棟 7.51m)。'
             '表門の棟高 7.30 は 2026-08-31 に「袖の長屋 5.30 より高く」でご裁定いただいた値で、<b>袖の高さに従属</b>しています。'
             '⭕ 史実の型は「上屋敷の表長屋は二階(鳶魚B・松江上屋敷の明治写真A)、門の棟は袖と同高かやや高い」。'
             '⚠ 5〜10万石級の現存長屋門(山脇・西澄寺・因州池田)は官製記載に高さが無く、門の棟高そのものは U のままです。</p></div>')
    h.append('<div class="fig">%s</div>' % omote_elev(dA2))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A 袖=二階・門 8.5</th><th>案B 袖=二階・門 9.2</th><th>案C 袖=平屋・門 7.30(現行の裁定)</th></tr></thead><tbody>'
             '<tr><td>袖の棟(絶対)</td><td>20.48</td><td>20.48</td><td>18.81</td></tr>'
             '<tr><td>門の棟(絶対)</td><td>20.75(袖+0.27)</td><td>21.43(袖+0.95)</td><td>19.55(袖+0.74)</td></tr>'
             '<tr><td>史料との整合</td><td>⭕ 二階=[西川1959]A・鳶魚B・松江写真A。門は「同高かやや高い」の型</td><td>⭕ 同左。門は大きく見える(9.2m は5.3万石にはやや過大か・U)</td><td>⛔ 表長屋「二階」の宣言と [西川1959]A を落とす</td></tr>'
             '<tr><td>部材</td><td>表長屋は二階の生成器(7.18・上段の窓あり)で焼き直し2本。門は長屋門の生成器で 8.5</td><td>同左・門 9.2</td><td>表長屋は平屋(焼き済みの生成器)。門 7.30</td></tr>'
             '<tr><td>動く物</td><td>const.nagayaH・roofs・門の棟高</td><td>同左</td><td>roofs.OmoteNagaya.kai と cert</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>推奨=案A。</b>史料が支える「二階の表長屋」を守り、門はそれよりやや高い 8.5m。'
             '2026-08-31 のご裁定の趣旨(門が袖より高い)は保ち、数字だけ袖の実寸に追随させる形です。案B は差を保つ代わりに門が 9.2m になり、5.3万石の門としては大きめ。'
             '案C は現行の数字を守るが A 級の史料を落とす。⚠ 門の棟高の典拠はどの案も U(現存例に高さの記載が無い)。</p>')
    h.append("</div>")

    h.append('<div class="box" style="border-color:var(--shu)"><h3>⚠ この図で決まらないこと</h3>'
             '<p>第一次(庭)の2件のほかに、主景の位置・汀線の形・石組・飛石・植栽・結界塀・稲荷社の'
             '位置などを含むが、それらは<b>裁定を要しない設計判断</b>として指図方が書き起こす。'
             'いずれも<b>確度U(当方の設計判断・史料の裏づけ無し)</b>で、指図にそう明記する。'
             '⛔ 「馬場を置かない」「池を一つに絞る」「蹲踞を置かない」も当方の裁定であって、'
             '史料が否定しているわけではない。</p></div>')
    h.append("</div>")
    io.open(OUT, "w", encoding="utf-8").write(apply_status("\n".join(h)))
    print("wrote %s (%d KB)" % (OUT, os.path.getsize(OUT) // 1024))
    print("裁定1の効き目 %+.0f m³ / 客土 案B %d → 案A %d m³(−%.0f%%)"
          % (-save, int(netB), int(netA), 100.0 * save / netB))




# ================================================================ 第二次(2026-09-02)
# 3役の検分55件のうち、意匠の判断が要って指図方に値を入れさせなかった3件。
# ⛔ 数値は一つも手で書かない — すべて設計を実際に組み直して測る。

def _variant2(raw, **kw):
    """const を差し替えた設計を組む。"""
    import copy
    d = copy.deepcopy(raw)
    d["const"].update(kw)
    return B.pipeline(d)


def _step_line(d, ter):
    """設計面が自然より高いまま打ち切られる線(=土留めが要る線)。u ごとに最大の段差。"""
    we = dict((t["name"], B.walled_edges(d, t)) for t in d["terraces"])
    rows = []
    u = -16.0
    while u <= 17.0 + 1e-9:
        best = None
        v = 106.0
        while v <= 122.0:
            n1 = B._dem_at(d, u, v); n2 = B._dem_at(d, u, v + 0.5)
            if n1 is not None and n2 is not None:
                g1 = B.graded_y(d, u, v, n1, we); g2 = B.graded_y(d, u, v + 0.5, n2, we)
                dr = (g1 - g2) - (n1 - n2)
                if dr > 0.5 and (best is None or dr > best[1]):
                    best = (v, dr, g1, n1)
            v += 0.5
        if best:
            rows.append((u,) + best)
        u += 0.5
    return rows


def toe_section(dA, dB, dC, ter, at_u=5.0, v0=105.0, v1=118.0):
    """裁定3の断面 — **1枚の枠に4本**(自然/現況/案B/案C)。縮尺を揃えるため重ねる。"""
    W, H = 940.0, 330.0
    y0, y1 = 14.0, 26.5
    sx = (W - 130) / (v1 - v0)

    def X(v):
        return 80 + (v - v0) * sx

    def Y(y):
        return H - 58 - (y - y0) / (y1 - y0) * (H - 108)

    g = sv(W, H, "裁定3 西の法尻の断面")
    RC(g, 70, 34, W - 100, H - 96, "var(--paper2)", "var(--rule)", 0.8, 0.55)
    for yy in range(14, 27, 2):
        LN(g, 76, Y(yy), W - 34, Y(yy), "var(--rule)", 0.6, "3 4", 0.8)
        T(g, 72, Y(yy) + 3, "%d" % yy, "anS2", "end", 9)
    nat = []
    v = v0
    while v <= v1 + 1e-9:
        z = B._dem_at(dA, at_u, v)
        if z is not None:
            nat.append((v, z))
        v += 0.25
    g.append('<polyline points="%s" fill="none" stroke="var(--ink)" stroke-width="1.6" '
             'stroke-dasharray="6 3" opacity="0.9"/>'
             % " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in nat))
    for dd, col, wd, lab in ((dA, "var(--shu)", 2.4, "現況(盛土 1:1.5)— 着地せず打ち切られる"),
                             (dB, "#2E6E7A", 1.8, "案B 盛土を 1:1.0 へ急にする"),
                             (dC, "#6E5A2E", 1.8, "案C 法面の到達を 25m へ延ばす")):
        we = dict((t["name"], B.walled_edges(dd, t)) for t in dd["terraces"])
        pts = [(a, B.graded_y(dd, at_u, a, b, we)) for a, b in nat]
        g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g"/>'
                 % (" ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in pts), col, wd))
    # 案A の土留め
    rows = _step_line(dA, ter)
    hit = [r for r in rows if abs(r[0] - at_u) < 0.26]
    if hit:
        vw, dr, gy, ny = hit[0][1], hit[0][2], hit[0][3], hit[0][4]
        RC(g, X(vw) - 4, Y(gy), 8, Y(ny) - Y(gy), "var(--ishi)", "var(--ink)", 1.0, 0.85)
        T(g, X(vw) + 10, Y(gy) - 6, "案A 土留め(この断面で丈 %.2fm)" % dr, "anS2", "start", 11)
    for v9 in range(int(v0), int(v1) + 1, 2):
        LN(g, X(v9), H - 54, X(v9), H - 48, "var(--dim)", 0.8)
        T(g, X(v9), H - 38, "v%d" % v9, "anS2", "middle", 9)
    T(g, 6, 16, "断面 u=+5(西の法尻を南北に切る)／縦横同一縮尺・単位 m(海抜)／"
      "破線=江戸期の復元地盤。⛔ 4本を**同じ枠に重ねて**ある — 別々の図にすると差が読めない",
      "anS2", "start", 11)
    for i, (col, lab) in enumerate((("var(--ink)", "江戸期の復元地盤(破線)"),
                                    ("var(--shu)", "現況(盛土 1:1.5)"),
                                    ("#2E6E7A", "案B 1:1.0"),
                                    ("#6E5A2E", "案C 到達25m"))):
        LN(g, 90 + i * 210, H - 14, 118 + i * 210, H - 14, col, 2.4)
        T(g, 124 + i * 210, H - 10, lab, "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


def kekkai_section(d, at_u=-19.0, v0=104.0, v1=170.0):
    """裁定5 — **西の縦断**。崖と、その下の平らな帯(溜池の岸)を一枚で見せる。
    ⛔ 「抜けられる」を言葉で言わない。**どこをどう歩けるか**を地形で見せる。"""
    W, H = 940.0, 300.0
    y0, y1 = 5.0, 27.0
    sx = (W - 110) / (v1 - v0)

    def X(v):
        return 70 + (v - v0) * sx

    def Y(y):
        return H - 56 - (y - y0) / (y1 - y0) * (H - 100)

    g = sv(W, H, "裁定5 西の縦断")
    RC(g, 60, 32, W - 90, H - 92, "var(--paper2)", "var(--rule)", 0.8, 0.55)
    for yy in range(5, 28, 5):
        LN(g, 66, Y(yy), W - 30, Y(yy), "var(--rule)", 0.6, "3 4", 0.8)
        T(g, 62, Y(yy) + 3, "%d" % yy, "anS2", "end", 9)
    pts, v = [], v0
    while v <= v1 + 1e-9:
        z = B._dem_at(d, at_u, v)
        if z is not None:
            pts.append((v, z))
        v += 0.5
    g.append('<polygon points="%s" fill="rgba(150,140,120,0.28)" stroke="var(--ink)" stroke-width="1.6"/>'
             % (" ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in pts)
                + " %.1f,%.1f %.1f,%.1f" % (X(pts[-1][0]), Y(y0), X(pts[0][0]), Y(y0))))
    # 溜池の水面
    RC(g, X(160.0), Y(6.6), X(v1) - X(160.0), Y(y0) - Y(6.6), "rgba(90,140,170,0.45)")
    # 結界塀 W6 の西端
    LN(g, X(111.25), Y(24.38), X(111.25), Y(24.38) - 30, "var(--hei)", 5.0)
    T(g, X(111.25), Y(24.38) - 36, "結界塀 W6 の西端(いまここで終わる)", "anS2", "middle", 11)
    # 帯の注記
    LN(g, X(129.0), Y(8.55) - 6, X(160.0), Y(8.55) - 6, "var(--shu)", 2.4)
    T(g, X(144.0), Y(8.55) - 12, "平らな帯 幅 約56m・標高 8.5 — **ここを歩いて回り込める**",
      "anS2", "middle", 11)
    T(g, X(120.0), Y(17.0), "崖 33m で 16m 下る(最急 71%)", "anS2", "middle", 11)
    T(g, X(165.0), Y(6.6) - 8, "溜池", "anS2", "middle", 11)
    for v9 in range(int(v0), int(v1) + 1, 8):
        LN(g, X(v9), H - 52, X(v9), H - 46, "var(--dim)", 0.8)
        T(g, X(v9), H - 36, "v%d" % v9, "anS2", "middle", 9)
    T(g, 6, 16, "西の縦断(u=−19・結界塀 W6 の線をそのまま西へ延ばした断面)／"
      "縦横同一縮尺・単位 m(海抜)。灰=江戸期の復元地盤", "anS2", "start", 11)
    T(g, 6, H - 8, "⭕ 案A はこの崖に沿って塀を建てる。⭕ 案B は W6 の西端(崖の上)で結界を終える。",
      "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


def kekkai_plan(d):
    """裁定5 — 平面。結界の線と、崖の下の平らな帯を通る回り込み。"""
    W, H = 940.0, 430.0
    u0, u1, v0, v1 = -44.0, 32.0, 70.0, 170.0
    sc = min((W - 60) / (v1 - v0), (H - 90) / (u1 - u0))

    def X(v):
        return 30 + (v1 - v) * sc

    def Y(u):
        return 52 + (u1 - u) * sc

    g = sv(W, H, "裁定5 平面")
    P = d["polygon"]
    gr = B.RGrid(d)
    pl = [gr.L(q[0], q[1]) for q in P]
    g.append('<polygon points="%s" fill="none" stroke="var(--dim)" stroke-width="1.4" stroke-dasharray="7 4"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in pl))
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    g.append('<polygon points="%s" fill="rgba(150,140,120,0.20)" stroke="var(--ink)" stroke-width="1.2"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in B.tpoly(sh)))
    for m in d["munes"]:
        RC(g, X(m["v1"]), Y(m["u1"]), (m["v1"] - m["v0"]) * sc, (m["u1"] - m["u0"]) * sc,
           "var(--nagaya)", "var(--ink)", 0.7, 0.85)
    for w in d.get("kekkai", []):
        a, b = w["a"], w["b"]
        LN(g, X(a[1]), Y(a[0]), X(b[1]), Y(b[0]), "var(--hei)", 4.5)
    esc = [(-14.0, 84.0), (-21.0, 100.0), (-24.0, 112.0), (-28.0, 124.0), (-32.0, 134.0),
           (-30.0, 145.0), (-20.0, 145.0), (-6.0, 138.0), (2.0, 126.0), (6.0, 112.0), (9.0, 92.0)]
    g.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="2.8" '
             'stroke-dasharray="10 6"/>' % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in esc))
    T(g, X(145.0), Y(-34.0) + 14, "崖を下りて平らな帯を通れば、塀の西を回れる", "anS2", "middle", 11)
    T(g, X(88.0), Y(20.0), "表", "anS2", "middle", 13)
    T(g, X(95.0), Y(-12.0), "奥", "anS2", "middle", 13)
    T(g, X(140.0), Y(-36.0) - 16, "平らな帯(溜池の岸・標高8.5)", "anS2", "middle", 11)
    T(g, X(112.0), Y(-19.0) - 10, "結界塀 W6 はここで終わる", "anS2", "middle", 10)
    T(g, 6, 16, "結界(v=79 の線と u=−19 の線)と、崖の下の平らな帯を通る回り込み。"
      "灰=主面(24.80)/ 破線=区画線(屋敷の外周)/ 茶=御殿の棟。向き: u+ が北(上)・v+ が西(左)",
      "anS2", "start", 11)
    g.append("</svg>")
    return "\n".join(g)

def hojiri_plan(d, ter):
    """裁定6 — 法尻の帯(千坪の桁)。窓の扇は空けたまま、南北の余地に建物を置くか。"""
    W, H = 940.0, 520.0
    u0, u1, v0, v1 = -30.0, 32.0, 100.0, 172.0
    sc = min((W - 60) / (v1 - v0), (H - 100) / (u1 - u0))

    def X(v):
        return 30 + (v1 - v) * sc

    def Y(u):
        return 60 + (u1 - u) * sc

    def half(v):
        if v <= 134.4:
            return 5.0 + 3.0 * (v - 108.5) / (134.4 - 108.5)
        return 8.0 + 3.5 * (v - 134.4) / (165.0 - 134.4)

    g = sv(W, H, "裁定6 法尻の帯")
    step, K = ter["step"], d["const"]["ken"]
    A = (step * K) ** 2
    area = {"mado": 0.0, "S": 0.0, "N": 0.0}
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * step
        if not (100.0 <= v <= 172.0):
            continue
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * step
            z = ter["h"][iv][iu]
            if z is None or not B.in_parcel(d, u, v):
                continue
            if z > 24.0:
                col = "rgba(150,140,120,0.35)"          # 主面
            elif z > 12.9:
                col = "rgba(110,150,105,0.30)"          # 斜面(林)
            else:
                col = "rgba(214,196,120,0.45)"          # 法尻の帯(草地)
                if v >= 134.4:
                    h = half(v)
                    if abs(u - 0.5) <= h:
                        area["mado"] += A; col = "rgba(214,196,120,0.20)"
                    elif u < 0.5 - h:
                        area["S"] += A; col = "rgba(198,93,58,0.35)"
                    else:
                        area["N"] += A; col = "rgba(46,110,122,0.35)"
            RC(g, X(v + step), Y(u + step), step * sc + 0.6, step * sc + 0.6, col)
    P = d["polygon"]; gr = B.RGrid(d)
    pl = [gr.L(q[0], q[1]) for q in P]
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4" stroke-dasharray="7 4"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in pl))
    # 扇の縁
    fan = [(0.5 - half(v), v) for v in (108.5, 134.4, 165.0)] + \
          [(0.5 + half(v), v) for v in (165.0, 134.4, 108.5)]
    g.append('<polygon points="%s" fill="none" stroke="var(--shu)" stroke-width="2.0"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in fan))
    for m in d["munes"]:
        RC(g, X(m["v1"]), Y(m["u1"]), (m["v1"] - m["v0"]) * sc, (m["u1"] - m["u0"]) * sc,
           "var(--nagaya)", "var(--ink)", 0.7, 0.85)
    T(g, X(150.0), Y(0.5) + 4, "見透しの窓(扇)— 空けたまま %.0f坪" % (area["mado"] / 3.3058), "anS2", "middle", 11)
    T(g, X(147.0), Y(-17.0) + 4, "南の余地 %.0f坪" % (area["S"] / 3.3058), "anS2", "middle", 12)
    T(g, X(150.0), Y(19.0) + 4, "北の余地 %.0f坪" % (area["N"] / 3.3058), "anS2", "middle", 12)
    T(g, X(120.0), Y(-24.0), "斜面(林)", "anS2", "middle", 11)
    T(g, X(104.0), Y(-12.0), "主面 24.8", "anS2", "middle", 11)
    T(g, X(168.0), Y(28.0), "溜池", "anS2", "middle", 11)
    T(g, 6, 16, "法尻の帯(標高 9.6〜12.9・勾配 2〜7%)。灰=主面 / 緑=斜面の林 / 黄=刈草地 / "
      "朱の枠=見透しの窓の扇(⛔ ここには建てない)/ 橙・青=建物を置ける余地", "anS2", "start", 11)
    T(g, 6, 32, "向き: u+ が北(上)・v+ が西(左)。破線=区画線。", "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g), area


# 庭方4巡目(2026-09-03)の算出 — 眼=床几(u+0.5/v107.8)・眼高25.55・汀の柵の天端12.51・水面6.60。
# 扇ぜんたいを相似に細めた場合。⛔ 数値は庭方の表からそのまま(当方の再計算ではない)。
MADO_TBL = [
    # 下端間, v130幅間, 角, 見えはじめ, 可視水面幅近/遠, 面積m2, 松を置かない間, %, 林の下端の口間, %, 窓坪, 奥向%, 台%
    (23.0, 15.0, 37.5, "130〜162", "93 / 122", 4627, 11.8, 24, 17.0, 35, 933, 89, 86),
    (18.0, 11.7, 30.0, "130〜162", "76 / 96",  3421,  9.5, 19, 13.7, 28, 730, 78, 75),
    (14.0,  9.1, 23.3, "132〜162", "59 / 74",  2464,  7.7, 16, 11.1, 23, 568, 67, 57),
    (10.0,  6.5, 16.8, "132〜159", "43 / 53",  1705,  5.8, 12,  8.5, 17, 406, 56, 41),
]


def mado_plan(d, ter):
    """裁定7 — 見透しの窓をどこまで細めるか。4案の扇を同じ縮尺で重ねる。"""
    W, H = 940.0, 560.0
    u0, u1, v0, v1 = -30.0, 32.0, 100.0, 172.0
    sc = min((W - 60) / (v1 - v0), (H - 120) / (u1 - u0))

    def X(v):
        return 30 + (v1 - v) * sc

    def Y(u):
        return 80 + (u1 - u) * sc

    m = d["nishi"]["mado"]
    fc, fl = m["fanCenter"], m["fanLimitV"]
    fan0 = m["fan"]                                  # [[v,u0,u1],...] 現行

    def half(v, r=1.0):
        pts = [(f[0], (f[2] - f[1]) / 2.0 * r) for f in fan0]
        for (va, ha), (vb, hb) in zip(pts, pts[1:]):
            if va <= v <= vb:
                return ha + (hb - ha) * (v - va) / (vb - va)
        return pts[-1][1]

    g = sv(W, H, "裁定7 見透しの窓")
    step = ter["step"]
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * step
        if not (100.0 <= v <= 172.0):
            continue
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * step
            z = ter["h"][iv][iu]
            if z is None or not B.in_parcel(d, u, v):
                continue
            if z > 24.0:
                col = "rgba(150,140,120,0.35)"
            elif v <= fl:
                col = "rgba(70,120,70,0.45)"           # 林(法肩〜林の下端)
            else:
                col = "rgba(214,196,120,0.35)"         # 刈草地
            RC(g, X(v + step), Y(u + step), step * sc + 0.6, step * sc + 0.6, col)
    P = d["polygon"]; gr = B.RGrid(d)
    pl = [gr.L(q[0], q[1]) for q in P]
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4" stroke-dasharray="7 4"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in pl))
    cols = ["var(--shu)", "#c8891a", "#2e6e7a", "#6a3fa0"]
    vs = [f[0] for f in fan0]
    for (w165, *_), col in zip(MADO_TBL, cols):
        r = w165 / (fan0[-1][2] - fan0[-1][1])
        fan = [(fc - half(v, r), v) for v in vs] + [(fc + half(v, r), v) for v in reversed(vs)]
        g.append('<polygon points="%s" fill="%s" fill-opacity="0.10" stroke="%s" stroke-width="2.0"/>'
                 % (" ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in fan), col, col))
        T(g, X(166.5), Y(fc + half(165.0, r)) - 3, "%.0f間" % w165, "anS2", "start", 11)
    # 効く所=林の下端 v130 と、床几からの限界の光線
    LN(g, X(130.0), Y(u0), X(130.0), Y(u1), "var(--ink)", 0.8, "3 3")
    T(g, X(130.0) + 4, Y(u1) + 12, "林の下端 v130 — ここの幅が視野を決める", "anS2", "start", 10)
    ex, ev = fc, 107.8
    for sgn in (-1, 1):
        ue = fc + sgn * half(130.0)
        k = (172.0 - ev) / (130.0 - ev)
        LN(g, X(ev), Y(ex), X(172.0), Y(ex + (ue - ex) * k), "var(--shu)", 0.8, "6 3")
    g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)"/>' % (X(ev), Y(ex)))
    T(g, X(ev) + 6, Y(ex) - 6, "床几(眼 25.55)", "anS2", "start", 10)
    for mu in d["munes"]:
        RC(g, X(mu["v1"]), Y(mu["u1"]), (mu["v1"] - mu["v0"]) * sc, (mu["u1"] - mu["u0"]) * sc,
           "var(--nagaya)", "var(--ink)", 0.7, 0.85)
    T(g, X(120.0), Y(-24.0), "斜面の林", "anS2", "middle", 11)
    T(g, X(104.0), Y(-12.0), "主面 24.8", "anS2", "middle", 11)
    T(g, X(150.0), Y(-24.0), "刈草地(法尻の帯)", "anS2", "middle", 11)
    T(g, X(168.0), Y(28.0), "溜池", "anS2", "middle", 11)
    T(g, 6, 16, "4案の扇を同じ縮尺で重ねた(朱=23間・現行 / 橙=18 / 青=14 / 紫=10)。"
      "数字は区画界(v165)での開き。緑=林 / 黄=刈草地 / 灰=主面 / 破線=区画線", "anS2", "start", 11)
    T(g, 6, 32, "朱の点線=床几から林の下端 v130 の扇の縁を掠める限界の光線。"
      "⛔ v130 より先(刈草地)は何も遮らないので、下端だけ細めても視野は変わらない", "anS2", "start", 10)
    T(g, 6, 48, "向き: u+ が北(上)・v+ が西(左)。", "anS2", "start", 10)
    g.append("</svg>")
    return "\\n".join(g)


# 裁定の状態 — ⛔ ここだけが正典。図の見出し・冒頭の一覧・板の左縁の色はすべてここから刷る。
# (番号, 題, 状態 done/open/void, 決定, 日付, 一言)
SAITEI_STATUS = [
    (1, "主面の5区画を「平坦化しない」ことを認めるか", "done", "A", "2026-09-02", "平坦化しない(自然地盤なり)"),
    (2, "長局の西庭をどう始末するか", "done", "A", "2026-09-02", "実用の庭「長局の物干」に改める"),
    (3, "西の法尻の段差をどう受けるか", "void", "—", "2026-09-02", "撤回 — 前提(現代地形の71%の崖)が江戸期地盤の復元で消えた"),
    (4, "「表役所」を作るか、作らない理由を書くか", "done", "B", "2026-09-02", "表役所は玄関棟の室として置く"),
    (5, "屋敷の西の端をどこまで「奥」とするか", "done", "B", "2026-09-02", "結界は崖の上まで。崖から下は外構の地"),
    (6, "溜池の岸の平らな帯に、建物を置くか", "done", "B", "2026-09-03", "窓の外の南北の余地に家臣長屋・厩・土蔵の類を置く → 何をどこには裁定8"),
    (7, "見透しの窓を、どこまで細めるか", "done", "B", "2026-09-03", "扇ぜんたいを相似に 23間 → 14間"),
    (8, "法尻の帯に、何をどこに置くか", "done", "A", "2026-09-03", "南に詰人長屋2棟+物置・井戸・かわや、勝手の坂1本。窓の小径は廃止。前提の「溜池の渡し船」は考証で実質否定(渡船は明治5年の許可)"),
    (9, "検分の輪をどう扱うか(三巡則)", "done", "A→B", "2026-09-03", "関門2本を足し6巡目1回(34件で閾値超え)→ 約束どおり案B=実装の輪へ"),
    (10, "車寄の屋根が玄関棟の屋根面に食い込む", "done", "A", "2026-09-04", "桟瓦のまま母屋へ差し込む(食い込み1.14m・実物の納まり)"),
    (11, "御錠口(3間角)の屋根が渡廊下より2.7m高い", "done", "B", "2026-09-04", "御錠口を廊下幅(1間)の建具に縮める"),
    (12, "表長屋の階と表門の棟高", "done", "A", "2026-09-04", "袖=二階 7.18(部材の実寸)・門 8.5(袖より+0.27)"),
]
_ST_LABEL = {"done": ("✅ 裁定済", "st-done"), "open": ("⏳ 未決 — お返事をお待ちしています", "st-open"),
             "void": ("⛔ 撤回(裁定不要)", "st-void")}
_ST_CSS = ("<style>.st{display:inline-block;font-size:12px;font-weight:600;padding:3px 9px;border-radius:4px;"
           "margin-right:10px;vertical-align:middle;letter-spacing:.02em}.st-done{background:#2e6e7a;color:#fff}"
           ".st-open{background:var(--shu);color:#fff}.st-void{background:#8a8a8a;color:#fff}"
           ".plate.done{border-left:8px solid #2e6e7a}.plate.open{border-left:8px solid var(--shu)}"
           ".plate.void{border-left:8px solid #8a8a8a}"
           ".stidx{width:100%;border-collapse:collapse;table-layout:auto}.stidx td,.stidx th{padding:5px 9px;border-bottom:1px solid var(--rule);vertical-align:top;text-align:left;white-space:normal}.stidx td:first-child,.stidx td:nth-child(4){white-space:nowrap}"
           ".stidx tr.open td{background:rgba(198,93,58,.08)}</style>")


def apply_status(html):
    """板の見出しに状態の札を差し、冒頭に一覧を置く。⛔ 見出しの文字列で板を探すので、題を変えたら SAITEI_STATUS も直す。"""
    for n, title, st, dec, day, memo in SAITEI_STATUS:
        key = '<div class="plate"><div class="phead"><h2>裁定%d　' % n
        assert html.count(key) == 1, "裁定%d の板が %d 個" % (n, html.count(key))
        lab, cls = _ST_LABEL[st]
        badge = '<span class="st %s">%s%s</span>' % (cls, lab, ("　案%s(%s)" % (dec, day)) if st == "done" else "")
        html = html.replace(key, '<div class="plate %s" id="saitei-%d"><div class="phead"><h2>%s裁定%d　' % (st, n, badge, n))
    n_open = sum(1 for r in SAITEI_STATUS if r[2] == "open")
    rows = "".join('<tr class="%s"><td><a href="#saitei-%d">裁定%d</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                   % (st, n, n, title, _ST_LABEL[st][0], ("案%s(%s)" % (dec, day)) if st == "done" else day, memo)
                   for n, title, st, dec, day, memo in SAITEI_STATUS)
    idx = ('<div class="box" style="margin:12px 0 28px"><h3>裁定の一覧 — 未決 %d 件 / 済 %d 件 / 撤回 %d 件</h3>'
           '<table class="stidx"><thead><tr><th>　</th><th>題</th><th>状態</th><th>決定</th><th>決めたこと</th></tr></thead>'
           '<tbody>%s</tbody></table>'
           '<p class="cap">⭕ 済の板は記録として残しています(番号は振り直しません)。⏳ の板だけお返事をください。'
           '板の左縁の色も同じ: 青緑=済 / 朱=未決 / 灰=撤回。</p></div>'
           % (n_open, sum(1 for r in SAITEI_STATUS if r[2] == "done"), sum(1 for r in SAITEI_STATUS if r[2] == "void"), rows))
    i = html.find("</h1>")
    assert i > 0
    html = html[:i + 5] + idx + html[i + 5:]
    j = html.find("</style>")
    assert j > 0
    return html[:j + 8] + _ST_CSS + html[j + 8:]


# ================================================================ 第五次(2026-09-03) 裁定8
# 法尻の帯に「何をどこに」。型は考証方(K198: 詰人の平屋長屋+井戸・かわや・物置・排水溝、水に背を向ける)、
# 景の制約は庭方(林の裾・等高線なり・奥行2.5〜3間・榎3本は残す・軒から幹6m・南隅は建てない・厩は不可)。
# ⛔ 棟の座標は裁定のための仮置き(普請奉行)。決まったら指図方が書き起こし、検査(切盛±0.5・榎の離れ・窓)で検める。
FAN8 = [(108.5, -0.87, 2.37), (134.4, -3.87, 5.87), (165.0, -6.00, 8.00)]      # 庭方 K187(14間・上端2.74間・芯+1.0)
ENOKI_CLEAR_M = 6.0
OBI_VARIANTS = {
    # name: (棟の一覧 [(id, u0,u1,v0,v1, 用途)], 小物 [(id,u,v,用途)])
    "A": ([("N1", -12.0, -4.5, 137.1, 139.6, "詰人長屋(南1)"), ("N2", -22.0, -14.5, 133.0, 135.5, "詰人長屋(南2)"),
           ("M1", -10.0, -7.0, 143.5, 145.0, "物置")],
          [("井戸", -13.0, 142.5), ("かわや", -6.0, 141.8)]),
    "B": ([("N1", -12.0, -4.5, 137.1, 139.6, "詰人長屋(南1)"), ("N2", -22.0, -14.5, 133.0, 135.5, "詰人長屋(南2)"),
           ("M1", -10.0, -7.0, 143.5, 145.0, "物置"), ("N3", 5.5, 10.0, 131.0, 133.5, "詰人長屋(北)")],
          [("井戸", -13.0, 142.5), ("かわや", -6.0, 141.8), ("かわや", 7.5, 136.5)]),
    "C": ([("N1", -12.0, -4.5, 137.1, 139.6, "詰人長屋(南1)")],
          [("井戸", -13.0, 142.5), ("かわや", -6.0, 141.8)]),
}
OBI_SAKA = [(-19.0, 108.5), (-25.5, 118.5), (-16.5, 127.5), (-23.0, 133.5)]    # 勝手の坂(幅1間・段なし)の仮の折れ


def _obi_stats(d, ter, munes):
    """棟ごとに 面積・地盤の平均(=面)・|地盤−面| の最大 を実測する。"""
    K = d["const"]["ken"]; step = ter["step"]
    out = []
    for mid, u0, u1, v0, v1, use in munes:
        zs = []
        for iv in range(ter["nv"]):
            v = ter["v0"] + iv * step
            if not (v0 <= v <= v1):
                continue
            for iu in range(ter["nu"]):
                u = ter["u0"] + iu * step
                if u0 <= u <= u1 and ter["h"][iv][iu] is not None:
                    zs.append(ter["h"][iv][iu])
        pad = sum(zs) / len(zs) if zs else float("nan")
        dz = max(abs(z - pad) for z in zs) if zs else float("nan")
        area = (u1 - u0) * (v1 - v0) * K * K
        out.append(dict(id=mid, use=use, area=area, pad=pad, dz=dz, ken=(u1 - u0)))
    return out


def _enoki_gap(d, munes):
    """棟の縁から榎の幹までの最短距離(m)。"""
    K = d["const"]["ken"]; res = []
    for e in d["nishi"]["hojiri"]["enoki"]:
        best = 1e9
        for mid, u0, u1, v0, v1, use in munes:
            du = max(u0 - e["u"], 0, e["u"] - u1); dv = max(v0 - e["v"], 0, e["v"] - v1)
            best = min(best, (du * du + dv * dv) ** 0.5 * K)
        res.append((e["name"], best))
    return res


def _saka_len(d):
    K = d["const"]["ken"]; L = 0.0
    for (a, b), (c, e) in zip(OBI_SAKA, OBI_SAKA[1:]):
        L += ((a - c) ** 2 + (b - e) ** 2) ** 0.5 * K
    return L


def obi_plan(d, ter):
    """裁定8 — 法尻の帯の棟を3案重ねる(同じ縮尺)。実線=案A / 青破線=案Bで足す棟 / 斜線=案Cで置かない棟。"""
    W, H = 940.0, 600.0
    u0, u1, v0, v1 = -30.0, 32.0, 100.0, 176.0
    sc = min((W - 60) / (v1 - v0), (H - 130) / (u1 - u0))

    def X(v):
        return 30 + (v1 - v) * sc

    def Y(u):
        return 90 + (u1 - u) * sc

    g = sv(W, H, "裁定8 法尻の帯の棟")
    step = ter["step"]
    for iv in range(ter["nv"]):
        v = ter["v0"] + iv * step
        if not (v0 <= v <= v1):
            continue
        for iu in range(ter["nu"]):
            u = ter["u0"] + iu * step
            z = ter["h"][iv][iu]
            if z is None or not B.in_parcel(d, u, v):
                continue
            col = "rgba(150,140,120,0.35)" if z > 24.0 else ("rgba(70,120,70,0.40)" if z > 14.0 else "rgba(214,196,120,0.35)")
            RC(g, X(v + step), Y(u + step), step * sc + 0.6, step * sc + 0.6, col)
    P = d["polygon"]; gr = B.RGrid(d)
    pl = [gr.L(q[0], q[1]) for q in P]
    g.append('<polygon points="%s" fill="none" stroke="var(--ink)" stroke-width="1.4" stroke-dasharray="7 4"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in pl))
    # 汀線(杭列)・木戸
    mz = d["nishi"]["tsutsumi"].get("mizugiwaM", 10.0) / d["const"]["ken"]
    LN(g, X(165.0 + mz), Y(-27.0), X(165.0 + mz), Y(13.5), "#2e6e7a", 1.2, "2 3")
    T(g, X(165.0 + mz) + 4, Y(13.5) - 6, "汀線=杭列(区画界から %.1fm)" % (mz * d["const"]["ken"]), "anS2", "start", 10)
    g.append('<rect x="%.1f" y="%.1f" width="8" height="8" fill="var(--shu)"/>' % (X(165.28) - 4, Y(1.0) - 4))
    T(g, X(165.28) + 6, Y(1.0) + 14, "木戸", "anS2", "start", 10)
    # 窓の扇(14間・上端2.74間・芯+1.0) — ここには建てない
    fan = [(a, v) for v, a, b in FAN8] + [(b, v) for v, a, b in reversed(FAN8)]
    g.append('<polygon points="%s" fill="var(--shu)" fill-opacity="0.08" stroke="var(--shu)" stroke-width="1.6"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in fan))
    T(g, X(140.0), Y(4.2), "見透しの窓(14間・上端2.74間)— 芝のみ・建てない・路も通さない", "anS2", "middle", 10)
    # 榎と離れの円
    K = d["const"]["ken"]
    for e in d["nishi"]["hojiri"]["enoki"]:
        cx, cy = X(e["v"]), Y(e["u"])
        g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#3a6b2a" stroke-width="0.8" stroke-dasharray="3 3"/>'
                 % (cx, cy, ENOKI_CLEAR_M / K * sc))
        g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="#3a6b2a"/>' % (cx, cy))
        T(g, cx - 9, cy + 4, "榎 %s(%d〜%dm)" % (e["name"], e["hMin"], e["hMax"]), "anS2", "end", 10)
    # 林の下端
    ed = d["nishi"]["hayashi"]["edge"]
    g.append('<polyline points="%s" fill="none" stroke="#3a6b2a" stroke-width="1.2"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in ed))
    T(g, X(ed[0][1]) + 4, Y(ed[0][0]) + 12, "林の下端", "anS2", "start", 10)
    # 棟 — 案A 実線 / 案B の追加は青破線 / 案C は N1 のみ(N2・M1 に斜線)
    A_m, A_s = OBI_VARIANTS["A"]; B_m, B_s = OBI_VARIANTS["B"]; C_m, C_s = OBI_VARIANTS["C"]
    c_ids = {m[0] for m in C_m}
    for mid, mu0, mu1, mv0, mv1, use in A_m:
        RC(g, X(mv1), Y(mu1), (mv1 - mv0) * sc, (mu1 - mu0) * sc, "var(--nagaya)", "var(--ink)", 1.0, 0.9)
        if mid not in c_ids:
            for k in range(1, 6):
                t = k / 6.0
                LN(g, X(mv1) + (mv1 - mv0) * sc * t, Y(mu1), X(mv1), Y(mu1) + (mu1 - mu0) * sc * t, "var(--ink)", 0.6)
        T(g, X(mv1) - 4, Y(mu1) - 4, "%s %s %.1f×%.1f間" % (mid, use, mu1 - mu0, mv1 - mv0), "anS2", "end", 10)
    for mid, mu0, mu1, mv0, mv1, use in B_m:
        if mid in {m[0] for m in A_m}:
            continue
        RC(g, X(mv1), Y(mu1), (mv1 - mv0) * sc, (mu1 - mu0) * sc, "#2e6e7a", "#2e6e7a", 1.4, 0.25, "5 3")
        T(g, X(mv0) + 4, Y(mu0) + 12, "%s %s %.1f×%.1f間(案Bだけ)" % (mid, use, mu1 - mu0, mv1 - mv0), "anS2", "start", 10)
    for sid, su, sv_, in B_s:
        g.append('<rect x="%.1f" y="%.1f" width="7" height="7" fill="none" stroke="var(--ink)" stroke-width="1"/>' % (X(sv_) - 3.5, Y(su) - 3.5))
        T(g, X(sv_) - 6, Y(su) + 4, sid, "anS2", "end", 9)
    # 勝手の坂
    g.append('<polyline points="%s" fill="none" stroke="#7a4a1a" stroke-width="3" stroke-linejoin="round"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in OBI_SAKA))
    T(g, X(116.0), Y(-19.5), "勝手の坂(幅1間・段なし・≤20%・林を筋で抜く)", "anS2", "middle", 10)
    for mu in d["munes"]:
        RC(g, X(mu["v1"]), Y(mu["u1"]), (mu["v1"] - mu["v0"]) * sc, (mu["u1"] - mu["u0"]) * sc,
           "var(--nagaya)", "var(--ink)", 0.7, 0.85)
    T(g, X(104.0), Y(-12.0), "主面 24.8", "anS2", "middle", 11)
    T(g, X(172.0), Y(28.0), "溜池", "anS2", "middle", 11)
    T(g, 6, 16, "実線の棟=案A(南に長屋2棟+物置・井戸・かわや)/ 青破線=案Bで足す北の1棟 / 斜線=案Cでは置かない棟。"
      "朱の扇=窓(建てない)/ 緑の破線円=榎の幹から6m(軒を入れない)", "anS2", "start", 11)
    T(g, 6, 32, "緑=林(地盤14以上)/ 黄=法尻の帯(刈草地)/ 灰=主面 / 茶の太線=勝手の坂 / 青緑の点線=汀線(杭列)。"
      "向き: u+ が北(上)・v+ が西(左)。⛔ 棟の座標は裁定のための仮置き", "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


# ================================================================ 裁定12(2026-09-04) 表長屋の階と表門の棟高
# 数値: 門の敷居 gate.plan.sill 12.25(街路)/ 袖の座 13.30(門前面)/ 門の桁行 16.362 / 南袖 6.189 / 北袖 73.439(図は 30m で切る)
# 部材の実寸(在庫方 2026-09-04): 表長屋 平屋 5.509 / 二階 7.183(生成器 build_nagaya_omote.py)。現行の指図: 袖 5.30(二階と宣言)・門 7.30
OMOTE_VARIANTS = [
    ("A", "袖=二階(7.18)・門 8.5(袖よりやや高い)", 7.183, 8.5),
    ("B", "袖=二階(7.18)・門 9.2(従来の差 0.95 を保つ)", 7.183, 9.18),
    ("C", "袖=平屋(5.51)・門 7.30(現行の裁定のまま)", 5.509, 7.30),
]


def omote_elev(d):
    """裁定12 — 辺12(三べ坂)の立面。3案を同じ縮尺で並べる。"""
    W, H = 960.0, 300.0
    plan = d["gate"].get("plan") if isinstance(d.get("gate"), dict) else None
    sill = float(plan.get("sill", 12.25)) if isinstance(plan, dict) else 12.25
    seat = 13.30
    gateL, sodeS, sodeN = 16.362, 6.189, 30.0
    span = sodeS + gateL + sodeN
    pw = (W - 40) / 3.0; sc = (pw - 20) / span
    g = sv(W, H, "裁定12 表長屋の階と表門の棟高")
    y0 = 250.0
    for k, (nm, title, sodeH, monH) in enumerate(OMOTE_VARIANTS):
        x0 = 20 + k * pw + 10
        def X(s, x0=x0): return x0 + s * sc
        def Y(z): return y0 - (z - 12.0) * sc
        T(g, x0 + pw / 2 - 10, 16, "案%s %s" % (nm, title), "anS2", "middle", 10.5)
        LN(g, X(0), Y(seat), X(sodeS), Y(seat), "var(--ink)", 1.0)
        LN(g, X(sodeS + gateL), Y(seat), X(span), Y(seat), "var(--ink)", 1.0)
        LN(g, X(sodeS), Y(sill), X(sodeS + gateL), Y(sill), "var(--ink)", 1.0)
        for a, b in ((0, sodeS), (sodeS + gateL, span)):
            RC(g, X(a), Y(seat + sodeH), (b - a) * sc, sodeH * sc, "var(--nagaya)", "var(--ink)", 0.8, 0.85)
            if sodeH > 6.0:
                LN(g, X(a), Y(seat + sodeH * 0.55), X(b), Y(seat + sodeH * 0.55), "#fff", 0.8, "3 2", 0.8)
        RC(g, X(sodeS), Y(sill + monH), gateL * sc, monH * sc, "#8a6a40", "var(--ink)", 1.2, 0.9)
        RC(g, X(sodeS + 5.0), Y(sill + 3.6), 3.636 * sc, 3.6 * sc, "#FBFAF6", "var(--ink)", 0.6)
        T(g, X(sodeS + gateL / 2), Y(sill + monH) - 4, "門 棟 %.2f(%.2f)" % (sill + monH, monH), "anS2", "middle", 9.5)
        T(g, X(sodeS + gateL + sodeN / 2), Y(seat + sodeH) - 4, "袖 棟 %.2f(%.2f)" % (seat + sodeH, sodeH), "anS2", "middle", 9.5)
        dz = (sill + monH) - (seat + sodeH)
        T(g, x0 + pw / 2 - 10, y0 + 22, "門−袖 = %+.2f m%s" % (dz, "" if dz > 0 else " ⛔ 袖が高い"), "anS2", "middle", 10)
        T(g, X(sodeS + gateL / 2), Y(sill) + 12, "街路 %.2f" % sill, "jo", "middle", 9)
        T(g, X(span - 2), Y(seat) + 12, "門前面 %.2f" % seat, "jo", "end", 9)
    T(g, 6, H - 8, "辺12(三べ坂)の立面・同縮尺(1m=%.1fpx)。門は街路の敷居 %.2f、袖は門前面 %.2f に載る(1.05m の段差)。二階は白の破線=胴差の目安。北袖は 30m で切った(実長 73.4m)" % (sc, sill, seat), "jo", "start", 9)
    g.append("</svg>")
    return "\n".join(g)



if __name__ == "__main__":
    main()
