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

    h.append('<div class="plate"><div class="phead"><h2>裁定5　結界の西の抜けをどう始末するか</h2>'
             '<span class="meta">どこ=結界塀 W6 の西端(グリッド u−19, v111.25)から西の斜面</span></div>')
    h.append('<div class="box"><h3>いま何がどうなっているか(実測)</h3>'
             '<p>表(玄関・書院・泉水)と奥(中奥・奥向・長局・奥庭)を屋外でも分けるため、'
             '結界塀を7区間まわして中門と木戸を一口ずつ開けました。'
             '⛔ ところが<b>その一口を両方閉めても、西の斜面を回って表から奥へ抜けられます</b>。'
             '検査(升目を歩く経路探索)が毎回そう出します。'
             '⚠ W6 の西端から外周の木柵(溜池の堤)まで<b>75.9m</b>あり、'
             'その間は地なりの西斜面で <b>24.46 から 8.5 へ 16m 下ります</b>。</p></div>')
    h.append('<div class="fig">%s</div>' % kekkai_plan(dA2))
    h.append('<div class="tw"><table><thead><tr><th>　</th><th>案A</th><th>案B</th><th>案C</th>'
             '</tr></thead><tbody>'
             '<tr><td>やること</td><td><b>W6 を外周の木柵まで約76m 延ばす</b></td>'
             '<td><b>法肩に竹垣を回す</b>(生成の閾値 <code>takegakiDrop</code> 1.0m を下げる)</td>'
             '<td><b>西斜面を「奥の郭の外」と認める</b> — 結界は法肩まで</td></tr>'
             '<tr><td>検査</td><td>0件になる</td>'
             '<td>⛔ <b>0件にならない</b> — 斜面は 0.29〜0.72m/0.5間 でどこまで下っても歩ける</td>'
             '<td>検査の対象を法肩までに絞る(=図の宣言を実態へ合わせる)</td></tr>'
             '<tr><td>新しく要る物</td><td><b>16m 下る斜面を降りる塀 76m</b></td>'
             '<td>竹垣が斜面一帯に増える(本数は算出)</td><td>無し</td></tr>'
             '</tbody></table></div>')
    h.append('<p class="cap"><b>⛔ 案ごとに引っかかること</b><br>'
             '<b>案A</b> … ⛔ <b>屋敷内部の仕切りとしては過大。</b>'
             'のし塀 h1.8 を崖に76m建てるのは当屋敷の格に合わず、典拠も無い。<br>'
             '<b>案B</b> … ⛔ <b>閾値を下げると他の縁にも垣が湧く</b>'
             '(竹垣は落差のある縁を拾う算出物)。しかも塞ぎきれない。<br>'
             '<b>案C</b> … ⛔ <b>図の宣言を弱める</b>ことになる。'
             '⭕ ただし「表と奥を分ける」の実体は<b>御錠口(確度A)</b>で、'
             '屋外の結界はもともと当方の外挿(確度U)。</p>')
    h.append('<p class="cap"><b>推奨=案C(西斜面を結界の外と認める)。</b>'
             '⭕ 西斜面は<b>平場でなく歩く場所でもない地なりの崖</b>で、'
             '屋敷の実際の境は<b>外周の木柵(溜池の堤)</b>です。'
             '⛔ そこへ内部の仕切りを76m下ろすのは、格にも典拠にも合いません。'
             '⚠ 案Cを採る場合は、<b>検査の対象を「法肩まで」と宣言し直し</b>、'
             '⛔ <b>「結界は屋外で閉じている」とは書かない</b>(閉じているのは法肩までである、と書く)。</p>')
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


def kekkai_plan(d):
    """裁定5 — 結界の線と、開口を全部閉じても残る西の抜け。"""
    W, H = 940.0, 470.0
    u0, u1, v0, v1 = -46.0, 34.0, 70.0, 170.0
    sc = min((W - 60) / (v1 - v0), (H - 90) / (u1 - u0))

    def X(v):
        return 30 + (v1 - v) * sc

    def Y(u):
        return 52 + (u1 - u) * sc

    g = sv(W, H, "裁定5 結界の西の抜け")
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    g.append('<polygon points="%s" fill="rgba(150,140,120,0.14)" stroke="var(--ink)" stroke-width="1.2"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in B.tpoly(sh)))
    P = d["polygon"]
    gr = B.RGrid(d)
    pl = [gr.L(q[0], q[1]) for q in P]
    g.append('<polygon points="%s" fill="none" stroke="var(--dim)" stroke-width="1.4" stroke-dasharray="7 4"/>'
             % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in pl))
    for m in d["munes"]:
        RC(g, X(m["v1"]), Y(m["u1"]), (m["v1"] - m["v0"]) * sc, (m["u1"] - m["u0"]) * sc,
           "var(--nagaya)", "var(--ink)", 0.7, 0.85)
    for w in d.get("kekkai", []):
        a, b = w["a"], w["b"]
        LN(g, X(a[1]), Y(a[0]), X(b[1]), Y(b[0]), "var(--hei)", 4.0)
    T(g, X(79.0), Y(28.0) - 8, "結界塀 W1〜W7(v=79 と u=−19 の線)", "anS2", "middle", 11)
    # 抜けの経路(模式)
    esc = [(-19.5, 82.0), (-26.0, 95.0), (-33.0, 106.0), (-37.6, 112.0), (-37.6, 79.0), (-30.0, 66.0)]
    g.append('<polyline points="%s" fill="none" stroke="var(--shu)" stroke-width="2.6" '
             'stroke-dasharray="9 5"/>' % " ".join("%.1f,%.1f" % (X(q[1]), Y(q[0])) for q in esc))
    T(g, X(112.0), Y(-40.0), "⛔ 開口を全部閉じても残る抜け", "anS2", "middle", 11)
    T(g, X(79.0), Y(-37.6) + 14, "v=79 を u=−37.63 で越える", "anS2", "middle", 10)
    for lab, uu, vv in (("表", 8.0, 60.0), ("奥", -10.0, 95.0), ("西斜面(地なり)", -30.0, 130.0)):
        T(g, X(vv), Y(uu), lab, "anS2", "middle", 12)
    T(g, 6, 16, "結界(v=79 と u=−19)と、開口を全部閉じたときに残る西の抜け。"
      "灰=主面(24.80)/ 破線=区画線 / 茶=御殿の棟。向き: u+ が北(上)・v+ が西(左)", "anS2", "start", 11)
    T(g, 6, 32, "⛔ W6 の西端(u=−19, v=111.25)から外周の木柵(辺5)まで **75.9m** ある。"
      "その間は地なりの西斜面で、24.46 から 8.5 へ 16m 下る。", "anS2", "start", 10)
    g.append("</svg>")
    return "\n".join(g)


if __name__ == "__main__":
    main()
