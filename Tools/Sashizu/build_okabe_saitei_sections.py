#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""岡部邸の**裁定用の断面図**を SVG ファイルで出す(普請奉行の裁定図が inline する)。

    python3 Tools/Sashizu/build_okabe_saitei_sections.py
      → docs/Sashizu/okabe_saitei_kurumayose.svg
      → docs/Sashizu/okabe_saitei_jouguchi.svg

⛔ **意匠は決めない。**寸法と図だけを出す。案の採否は普請奉行(とユーザー)の裁定。
⚠ **数値は手で書かない** — 段・床・屋根は `okabe_sashizu.json` から、部材の実寸は
   下の `PART`(部材方の実測・出どころを欄に明記)から引く。
⭕ 3案を**同じ縮尺で横に並べる**(⛔ 案ごとに別の図にしない — 並べないと差が読めない)。
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_okabe_sashizu as B                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs", "Sashizu")

# ── 部材方の実測(2026-09-04)。⛔ ここ以外に書き写さない ────────────────
PART = {
    # 名: (実寸 X[桁行], Y[高], Z[奥行], 棟天端, 軒先, 底のオフセット, 出どころ)
    "Kurumayose": (7.146, 4.342, 4.376, 4.34, 1.89, 0.0,
                   "部材方の実測 `Okabe_Kurumayose.fbx`(2026-09-04)"),
    "Jouguchi":   (7.596, 5.858, 7.596, 5.24, None, -0.62,
                   "部材方の実測(3間角・底が床より 0.62 下がる)"),
}
ROKA_RIDGE = 2.503        # 渡廊下(幅1間)の大棟 — 床から。`EdoGotenKit` の定数
ROKA_W = 1.818



# ⛔ **単体の svg として開かれる**(普請奉行の裁定図が inline する / ブラウザで直接開く)ので、
#   指図の CSS は効かない。⭕ 使う変数とクラスだけを svg の中へ埋める。
STYLE = ("<style>"
         "svg{background:#FBFAF6;font-family:'Hiragino Sans','Noto Sans JP',sans-serif}"
         ":root,svg{--ink:#23201A;--dim:#615C4E;--rule:#D3CEBF;--shu:#A8452C;"
         "--ishi:#6E7A83;--nagaya:#7A5C3A;--ike:#A9C2CE}"
         ".jo{font-size:9.5px;fill:#615C4E}"
         ".anS2{font-size:10.5px;fill:#615C4E;text-anchor:middle}"
         "</style>")

def _num(d):
    sh = next(t for t in d["terraces"] if t["name"] == "Shumen")
    return {"plane": sh["y"], "floor": d["const"]["gotenFloor"]}


def _panel(g, X, Y, x0, title, draw, note):
    """1案ぶんの枠。⭕ どの案も**同じ X/Y**(=同じ縮尺)を使う。"""
    g.append(B.T(x0 + 150, 26, title, "anS2", "middle", 13))
    draw(x0)
    g.append(B.T(x0 + 150, 300, note, "jo", "middle", 10))


def _ground(g, X, Y, x0, y, lab):
    g.append(B.LN(X(x0, -14), Y(y), X(x0, 14), Y(y), "var(--ink)", 1.6))
    g.append(B.T(X(x0, -13.5), Y(y) + 12, lab, "jo", "start", 10))


def kurumayose_svg(d):
    n = _num(d)
    plane, fl = n["plane"], n["floor"]
    floorY = plane + fl
    rf = d["roofs"]["Goten_Genkan"]
    eaveY = floorY + rf["eaveH"]                            # 玄関の軒先(部材方の実測 2.577)
    ridgeY = floorY + rf["ridgeH"]                          # 玄関の大棟
    kw, kh, kd, kridge, keave, _b, ksrc = PART["Kurumayose"]
    W, H = 960.0, 330.0
    sc = 11.0                                               # px / m(3案 共通)
    y0 = plane - 1.0
    g = ['<svg viewBox="0 0 %g %g" width="100%%" role="img" '
         'aria-label="車寄と玄関棟の取り合い(裁定図)" style="max-width:%gpx;height:auto">'
         % (W, H, W), STYLE]

    def Y(y):
        return 250.0 - (y - y0) * sc

    def X(x0, x):
        return x0 + 150.0 + x * sc

    def genkan(x0):
        """玄関棟(東西断面・入母屋 11×11 の屋根面を右へ)。"""
        g.append(B.R(X(x0, 1.0), Y(floorY), 13 * sc, (floorY - y0) * sc,
                     "var(--nagaya)", "var(--ink)", 1.0, None, 0.55))
        g.append(B.LN(X(x0, 1.0), Y(eaveY), X(x0, 13), Y(eaveY), "var(--ink)", 1.4))
        g.append(B.LN(X(x0, 1.0), Y(eaveY), X(x0, 11.0), Y(ridgeY), "var(--shu)", 2.0))
        g.append(B.T(X(x0, 7.5), Y(ridgeY) - 6, "玄関棟 入母屋 %d×%d(大棟 %.2f)"
                     % (rf["wKen"], rf["dKen"], ridgeY), "jo", "middle", 10))
        g.append(B.T(X(x0, 1.4), Y(eaveY) - 5, "軒先 %.2f" % eaveY, "jo", "start", 10))
        g.append(B.LN(X(x0, -14), Y(floorY), X(x0, 1.0), Y(floorY), "var(--dim)", 0.8, "4 3"))
        g.append(B.T(X(x0, -13.5), Y(floorY) - 5, "床 %.2f(面 %.2f + %.2f)"
                     % (floorY, plane, fl), "jo", "start", 10))

    def draw_a(x0):
        genkan(x0)
        top = plane + kridge
        g.append(B.LN(X(x0, -kd), Y(plane + keave), X(x0, 0.0), Y(top), "var(--ike)", 2.2))
        g.append(B.LN(X(x0, 0.0), Y(top), X(x0, kd), Y(plane + keave), "var(--ike)", 2.2))
        g.append(B.T(X(x0, 0.0), Y(top) - 6, "車寄 棟 %.2f" % top, "jo", "middle", 10))
        if top > eaveY:
            g.append(B.LN(X(x0, 0.0), Y(eaveY), X(x0, 0.0), Y(top), "var(--shu)", 3.0))
            g.append(B.T(X(x0, 0.3), Y((eaveY + top) / 2), "食い込み %.2fm" % (top - eaveY),
                         "jo", "start", 11))
        _ground(g, X, Y, x0, plane, "面 %.2f" % plane)

    def draw_b(x0):
        genkan(x0)
        top = plane + 3.0                                   # 3寸勾配の緩い屋根
        g.append(B.LN(X(x0, -kd), Y(plane + keave), X(x0, 0.0), Y(top), "var(--ike)", 2.2,
                      "6 4"))
        g.append(B.LN(X(x0, 0.0), Y(top), X(x0, kd), Y(plane + keave), "var(--ike)", 2.2,
                      "6 4"))
        g.append(B.T(X(x0, 0.0), Y(top) - 6, "車寄 棟 %.2f(3寸)" % top, "jo", "middle", 10))
        g.append(B.T(X(x0, 0.3), Y((top + eaveY) / 2), "余裕 %.2fm" % (eaveY - top),
                     "jo", "start", 11))
        _ground(g, X, Y, x0, plane, "面 %.2f" % plane)

    def draw_c(x0):
        genkan(x0)
        g.append(B.R(X(x0, -1.5), Y(plane + 0.45), 3.0 * sc, 0.45 * sc,
                     "var(--ishi)", "var(--ink)", 1.0))
        g.append(B.T(X(x0, 0.0), Y(plane + 0.45) - 6, "式台のみ(屋根なし)", "jo", "middle", 10))
        _ground(g, X, Y, x0, plane, "面 %.2f" % plane)

    _panel(g, X, Y, 0, "案A 現況(部材の実寸のまま)", draw_a,
           "車寄 棟 %.2f > 玄関の軒先 %.2f → **%.2fm 食い込む**"
           % (plane + kridge, eaveY, plane + kridge - eaveY))
    _panel(g, X, Y, 320, "案B 車寄の屋根を緩勾配に", draw_b,
           "3寸(檜皮・柿葺)で棟 ≒%.2f → 軒先の下に %.2fm 収まる"
           % (plane + 3.0, eaveY - (plane + 3.0)))
    _panel(g, X, Y, 640, "案C 車寄を廃し式台だけ", draw_c,
           "屋根が無いので取り合いは消える。⛔ 格式の判断は別")
    g.append(B.T(8, 318,
                 "断面は東西・同縮尺(1m = %.1fpx)。玄関棟の軒先・大棟は指図の算出値"
                 "(`roofs.Goten_Genkan`)、車寄は %s。⛔ 意匠は決めない — 図と寸法だけ。"
                 % (sc, ksrc), "jo", "start", 10))
    g.append("</svg>")
    return "\n".join(g)


def jouguchi_svg(d):
    n = _num(d)
    plane, fl = n["plane"], n["floor"]
    floorY = plane + fl
    jw, jh, jd, jridge, _e, jbase, jsrc = PART["Jouguchi"]
    W, H = 960.0, 330.0
    sc = 15.0
    y0 = plane - 1.0
    g = ['<svg viewBox="0 0 %g %g" width="100%%" role="img" '
         'aria-label="御錠口と渡廊下の取り合い(裁定図)" style="max-width:%gpx;height:auto">'
         % (W, H, W), STYLE]

    def Y(y):
        return 250.0 - (y - y0) * sc

    def X(x0, x):
        return x0 + 150.0 + x * sc

    def roka(x0, side):
        top = floorY + ROKA_RIDGE
        hw = ROKA_W / 2.0
        x1 = side * 7.5
        g.append(B.R(X(x0, x1 - hw), Y(floorY), ROKA_W * sc, (floorY - y0) * sc,
                     "var(--nagaya)", "var(--ink)", 0.8, None, 0.5))
        g.append(B.LN(X(x0, x1 - hw), Y(floorY + 1.9), X(x0, x1), Y(top), "var(--ink)", 1.6))
        g.append(B.LN(X(x0, x1), Y(top), X(x0, x1 + hw), Y(floorY + 1.9), "var(--ink)", 1.6))
        g.append(B.T(X(x0, x1), Y(top) - 6, "渡廊下 幅1間・大棟 %.2f" % top, "jo", "middle", 9))

    def body(x0, halfKen, top, lab, dash=None):
        hw = halfKen
        g.append(B.R(X(x0, -hw), Y(floorY), hw * 2 * sc, (floorY - y0) * sc,
                     "var(--nagaya)", "var(--ink)", 1.0, None, 0.6))
        g.append(B.LN(X(x0, -hw), Y(floorY + 2.2), X(x0, 0.0), Y(top), "var(--shu)", 2.2, dash))
        g.append(B.LN(X(x0, 0.0), Y(top), X(x0, hw), Y(floorY + 2.2), "var(--shu)", 2.2, dash))
        g.append(B.T(X(x0, 0.0), Y(top) - 6, lab, "jo", "middle", 10))

    def draw_a(x0):
        body(x0, 5.454 / 2, floorY + jridge, "御錠口 3間角 棟 %.2f" % (floorY + jridge))
        roka(x0, -1); roka(x0, 1)
        _ground(g, X, Y, x0, plane, "面 %.2f" % plane)

    def draw_b(x0):
        body(x0, ROKA_W / 2, floorY + ROKA_RIDGE,
             "廊下幅の建具 棟 %.2f" % (floorY + ROKA_RIDGE), "6 4")
        roka(x0, -1); roka(x0, 1)
        _ground(g, X, Y, x0, plane, "面 %.2f" % plane)

    def draw_c(x0):
        body(x0, 5.454 / 2, floorY + 3.4, "3間角・寄棟 3寸 棟 %.2f" % (floorY + 3.4), "6 4")
        roka(x0, -1); roka(x0, 1)
        _ground(g, X, Y, x0, plane, "面 %.2f" % plane)

    _panel(g, X, Y, 0, "案A 現況(3間角・棟 床+%.2f)" % jridge, draw_a,
           "渡廊下の大棟 %.2f との差 **%.2fm**" % (floorY + ROKA_RIDGE, jridge - ROKA_RIDGE))
    _panel(g, X, Y, 320, "案B 廊下幅1間の建具に縮める", draw_b,
           "棟を廊下に揃える(%.2f)。⛔ 3間角の小屋ではなくなる" % (floorY + ROKA_RIDGE))
    _panel(g, X, Y, 640, "案C 3間角のまま寄棟の低勾配", draw_c,
           "3寸で棟 ≒%.2f(差 %.2fm)" % (floorY + 3.4, 3.4 - ROKA_RIDGE))
    g.append(B.T(8, 318,
                 "断面は同縮尺(1m = %.1fpx)。床は面 %.2f + 床 %.2f。渡廊下の大棟は "
                 "`EdoGotenKit` の定数 %.3f、御錠口は %s。⛔ 意匠は決めない。"
                 % (sc, plane, fl, ROKA_RIDGE, jsrc), "jo", "start", 10))
    g.append("</svg>")
    return "\n".join(g)


def main():
    d = B.pipeline(B.json.load(io.open(os.path.join(DOC, "okabe_sashizu.json"),
                                       encoding="utf-8")))
    for nm, fn in (("okabe_saitei_kurumayose.svg", kurumayose_svg),
                   ("okabe_saitei_jouguchi.svg", jouguchi_svg)):
        p = os.path.join(DOC, nm)
        io.open(p, "w", encoding="utf-8").write(fn(d))
        print("wrote %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
