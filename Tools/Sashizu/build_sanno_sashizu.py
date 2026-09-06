#!/usr/bin/env python3
"""山王権現社(日枝神社)の指図を組む。

    python3 Tools/Sashizu/build_sanno_sashizu.py

【順序】**指図が先、実装が後。** この生成器は実装を読まない。読むのは

    docs/Sashizu/sanno_sashizu.json … 設計値の正典(人が書く)
    docs/Sashizu/sanno_kosho.md     … 文章の部(人が書く・現況形)

の二つだけ。実装から指図を作ると CLAUDE.md 絶対規則2 の関門が消える。

【この社ならではの作り】参道軸が東西で、絵図の社殿・回廊・透塀がすべて軸平行に描かれるため、
グリッドは**世界軸そのもの**(u=東+/v=北+、原点=楼門の芯)。回転フレームは要らない。
断面は json の `profiles`(Unity 地形の実測)を下敷きにする。

【図版】⛔ **一覧をここに持たない**(検図5巡目 低23 — 章の増減で必ず腐る)。
        章の題と番号は `nx()` の出力が正典で、組んだら末尾の「図版 N 面」を数えること
        (図版が黙って落ちた前科がある)。
"""
import json, sys, math, os, re, subprocess, html, bisect

import sashizu_lib
from sashizu_lib import R, _pat, _SVN, Proj  # バイト同一を実証済みの共通部(_SVN は共有カウンタ)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs/Sashizu")
JSON = os.path.join(DOC, "sanno_sashizu.json")
MD = os.path.join(DOC, "sanno_kosho.md")
OUT = os.path.join(DOC, "sanno_sashizu.html")
TSUBO = 3.305785
VEX = 2.0     # 断面の垂直倍率


# ---------------------------------------------------------------- markdown(正典は sashizu_lib)
def inline(s):
    """当社の方言は確度の刻印だけ — 【S …】/【確度…】と**先頭**に置く(CERT_LEADING)。
    記法フラグは 2026-08-26 に md 側の行跨ぎ ** を直したうえで厳しい既定へ寄せた。"""
    return sashizu_lib.inline(s, cert=sashizu_lib.CERT_LEADING)


def tsubo_table(d, md):
    """kosho.md の @@TSUBO_TABLE@@ を、parcels.json から算出した坪数表で置き換える(規則4・考証 2026-09-06)。"""
    if "@@TSUBO_TABLE@@" not in md: return md
    P = {q["id"]: q["pts"] for q in json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))["parcels"]}
    tsubo = d["const"]["tsubo"]; kisai = d["const"]["keidai_kisai_tsubo"]
    def A(ids): return sum(poly_area(P[i]) for i in ids) / tsubo
    base = ["sannosha_prec"] + ["sannojubo_parcels_%d" % i for i in range(10)] + ["sannosha_kanri"]
    rows = [("社地+十坊+観理院", base), ("+樹下邸", base + ["sannobuke_juge"]),
            ("+樹下邸+社人八家", base + ["sannobuke_juge", "sannobuke_shanin"]),
            ("+樹下邸+社人八家+門前町", base + ["sannobuke_juge", "sannobuke_shanin"] + ["sanno_monzen_%d" % i for i in range(1, 5)])]
    out = ["  | 読み | 坪 | 記載値比 |", "  |---|---|---|"]
    for nm, ids in rows:
        a = A(ids); out.append("  | %s | %s | %+.1f%% |" % (nm, format(int(round(a)), ","), (a / kisai - 1) * 100))
    return md.replace("@@TSUBO_TABLE@@", "\n".join(out))


def md2html(text):
    # indent_tables は既定(=拾う)。sanno_kosho.md「拝領坪数」の字下げ表が
    # 旧変換では素の | の段落で出ていたのを、統一で表として描くようになった(実測1箇所)。
    return sashizu_lib.md2html(text, inline=inline)


# ---------------------------------------------------------------- 作図の土台
def _sv(W, H, label):
    _SVN[0] += 1
    return ['<svg viewBox="0 0 %.0f %.0f" role="img" aria-label="%s">' % (W, H, label),
            '<defs><pattern id="pi%d" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<path d="M0,4.5 h9 M4.5,0 v9" stroke="var(--ishi)" stroke-width="0.8" opacity="0.6"/></pattern>'
            '<pattern id="kr%d" width="7" height="7" patternUnits="userSpaceOnUse">'
            '<path d="M0,7 L7,0" stroke="var(--shu)" stroke-width="0.7" opacity="0.55"/></pattern>'
            '<pattern id="mr%d" width="7" height="7" patternUnits="userSpaceOnUse">'
            '<path d="M0,0 L7,7" stroke="var(--take)" stroke-width="0.7" opacity="0.55"/></pattern>'
            '<clipPath id="cl%d"><rect x="0" y="0" width="%.0f" height="%.0f"/></clipPath></defs>'
            % (_SVN[0], _SVN[0], _SVN[0], _SVN[0], W, H),
            '<g clip-path="url(#cl%d)">' % _SVN[0]]


ENDSVG = "</g></svg>"


def _cut(): return "url(#kr%d)" % _SVN[0]      # 切土
def _fill(): return "url(#mr%d)" % _SVN[0]     # 盛土


class LProj(object):
    """グリッド (u,v)[間] → SVG px。**u が画面右 / v が画面上**(v=北なので Y を反転する)。

    ⚠ **土井(build_doi_sashizu.py)の LProj と形を揃えてはならない。** あちらは回転フレームで
    v=敷地の奥を画面下に取るため X を反転しているが、この社は grid が世界軸そのもの
    (u=東 / v=北)なので、世界図 Proj と同じ「u右・v上」でなければ鏡像になる。

    【符号の検算】画面は y が下向き = 世界に対して1回反転するので
        要 screen_cross = -(world_cross)、world_cross = ux·vz - uz·vx
    この社は world_cross=+1 → 要 -1、実 (u右=+1)×(v上=-1) = -1 で一致(2026-08-23 検算)。
    """
    def __init__(self, u0, u1, v0, v1, W=900.0, top=22.0, bottom=20.0):
        self.u0, self.u1, self.v0, self.v1 = u0, u1, v0, v1
        self.s = W / float(u1 - u0)
        self.W, self.top = W, top
        self.vh = (v1 - v0) * self.s
        self.H = self.vh + top + bottom

    def X(self, u): return (u - self.u0) * self.s
    def Y(self, v): return self.top + self.vh - (v - self.v0) * self.s
    def L(self, ken): return ken * self.s

    def rect(self, u0, v0, u1, v1, **kw):
        return R(self.X(min(u0, u1)), self.Y(max(v0, v1)),
                 abs(self.X(u1) - self.X(u0)), abs(self.Y(v1) - self.Y(v0)), **kw)


def T(x, y, s, cls="sl", anchor=None, fs=None, fill=None):
    a = '<text class="%s" x="%.1f" y="%.1f"' % (cls, x, y)
    st = []
    if anchor: st.append("text-anchor:%s" % anchor)
    if fs: st.append("font-size:%.1fpx" % fs)
    if fill: st.append("fill:%s" % fill)
    if st: a += ' style="%s"' % ";".join(st)
    return a + ">%s</text>" % html.escape(s.replace("**", ""), quote=False)


def LN(x1, y1, x2, y2, stroke="var(--ink)", sw=1.0, dash=None, op=None, cap=None):
    a = '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.2f"' % (x1, y1, x2, y2, stroke, sw)
    if dash: a += ' stroke-dasharray="%s"' % dash
    if op is not None: a += ' opacity="%.2f"' % op
    if cap: a += ' stroke-linecap="%s"' % cap
    return a + "/>"


def PL(pts, stroke="var(--ink)", sw=1.0, fill="none", dash=None, op=None, close=False):
    dd = "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")
    a = '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f"' % (dd, fill, stroke, sw)
    if dash: a += ' stroke-dasharray="%s"' % dash
    if op is not None: a += ' opacity="%.2f"' % op
    return a + "/>"


def fit(txt, wpx, base=12.0, lo=8.5):
    return max(lo, min(base, wpx / (len(txt) * 0.62 + 0.8)))


def poly_area(P):
    s = 0.0
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        s += a[0] * b[1] - b[0] * a[1]
    return abs(s) / 2.0


# ---------------------------------------------------------------- グリッド
class G(object):
    def __init__(self, d):
        g = d["grid"]["keidai"]
        self.ken = d["const"]["ken"]
        self.x0, self.z0 = g["x0"], g["z0"]

    def W(self, u, v): return (self.x0 + u * self.ken, self.z0 + v * self.ken)
    def U(self, x): return (x - self.x0) / self.ken
    def V(self, z): return (z - self.z0) / self.ken


YAKU_COL = {"社殿": "var(--shu)", "廊": "var(--roka)", "堂": "var(--nagaya)",
            "蔵": "var(--ishi)", "供": "var(--nagaya)", "接続": "var(--shu-lo)"}


def gap_split(a, b, o, horiz):
    """run/wall の開口(gapU/gapV/gapHalf)で区間を割る。horiz=True なら u 方向に走る辺。

    2026-08-23 検図 — 指図が宣言した開口が図に一つも描かれていなかったので入れた。
    """
    hw = o.get("gapHalf")
    if not hw:
        return [(a, b)]
    c = o.get("gapU") if horiz else o.get("gapV")
    if c is None:
        c = o.get("gapV") if horiz else o.get("gapU")
    if c is None:
        return [(a, b)]
    i = 0 if horiz else 1
    lo, hi = min(a[i], b[i]), max(a[i], b[i])
    g0, g1 = c - hw, c + hw
    if g1 <= lo or g0 >= hi:
        return [(a, b)]
    out = []
    def pt(v):
        q = list(a)
        q[i] = v
        q[1 - i] = a[1 - i] + (b[1 - i] - a[1 - i]) * ((v - a[i]) / (b[i] - a[i]) if b[i] != a[i] else 0)
        return q
    if g0 > lo: out.append((pt(lo), pt(g0)))
    if g1 < hi: out.append((pt(g1), pt(hi)))
    return out


def clip_gaps(a, b, gaps):
    """線分から `gaps`=[(u,v,半幅)] の円い開口を抜く。折れ線の任意の向きに効く。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    if L < 1e-9: return [(a, b)]
    cut = []
    for gu, gv, hw in gaps:
        t = ((gu - a[0]) * dx + (gv - a[1]) * dz) / (L * L)
        px, pz = a[0] + dx * t, a[1] + dz * t
        dd = math.hypot(gu - px, gv - pz)
        if dd >= hw: continue
        half = math.sqrt(max(0.0, hw * hw - dd * dd)) / L
        cut.append((max(0.0, t - half), min(1.0, t + half)))
    if not cut: return [(a, b)]
    cut.sort()
    out, cur = [], 0.0
    P = lambda t: [a[0] + dx * t, a[1] + dz * t]
    for c0, c1 in cut:
        if c1 <= 0.0 or c0 >= 1.0: continue
        if c0 > cur + 1e-6: out.append((P(cur), P(c0)))
        cur = max(cur, c1)
    if cur < 1.0 - 1e-6: out.append((P(cur), P(1.0)))
    return out


def run_segs(o):
    """run/wall を開口で割った描画区間。折れ線にも対応。"""
    out = []
    for a, b in segs(o):
        horiz = abs(b[0] - a[0]) >= abs(b[1] - a[1])
        for p, q in gap_split(a, b, o, horiz):
            out += clip_gaps(p, q, o.get("gaps") or [])
    return out


def run_len_ken(o):
    """run/wall の **開口を抜いた実長**[間]。⛔ **発注量はこちら**(節点間の総和ではない)。

    ⚠ 2026-09-07 検図10巡目 中1 — 図と run の表が刷っていたのは `ken`(節点間の総和)で、
    **石段の頭・勝手口・中門・潜りの開口を一つも抜いていなかった**。`bom`「境内の外周の柵」は
    『延長は図が算出する(開口を抜いた実長)』と宣言しており、**この数がそのまま新造の発注量になる**。
    ⛔ 二本の物差しを混ぜない — 史料拘束(透塀の周長)は `run_nodes_ken` の側で読む。
    """
    if not o.get("pts") and (o.get("a") is None or o.get("b") is None): return 0.0
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in run_segs(o))


def run_nodes_ken(o):
    """run の **節点間の総和**[間](開口を含む)。⛔ **発注量ではない。**

    透塀だけはこちらが史料拘束(周長 486.01尺 = 147.28 m【S】)と突き合わせる数で、
    宣言 `ken` があればそれを、無ければ折れ線 a→b の総和を採る。
    """
    if o.get("ken"): return float(o["ken"])
    if not o.get("pts") and (o.get("a") is None or o.get("b") is None): return 0.0
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs(o))


def band(pts, PX, PY, LEN, w, fill, stroke, op=0.55, sw=0.8):
    """折れ線を実幅の帯として描く。角は法線の二等分(留め)で継ぐ。

    2026-08-23 — 参道を「適当な点線」で描いていたのをユーザーに指摘されて入れた。
    """
    import math as _m
    n = len(pts)
    left, right = [], []
    for i, q in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(n - 1, i + 1)]
        if i == 0: a = q
        if i == n - 1: b = q
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = _m.hypot(dx, dz) or 1.0
        nx, nz = -dz / L, dx / L
        hw = w / 2
        if 0 < i < n - 1:                      # 留め: 折れ角で半幅を w/2/cos(θ/2) に補正(検図 2026-09-06)
            ux, uz = q[0] - a[0], q[1] - a[1]; vx, vz = b[0] - q[0], b[1] - q[1]
            lu = _m.hypot(ux, uz) or 1.0; lv = _m.hypot(vx, vz) or 1.0
            c = _m.hypot(ux / lu + vx / lv, uz / lu + vz / lv) / 2.0
            hw = w / 2 / max(c, 0.3)
        left.append((q[0] + nx * hw, q[1] + nz * hw))
        right.append((q[0] - nx * hw, q[1] - nz * hw))
    ring = left + right[::-1]
    out = [PL([(PX(x), PY(z)) for x, z in ring], fill=fill, op=op,
              stroke=stroke, sw=sw, close=True)]
    out.append(PL([(PX(x), PY(z)) for x, z in pts], stroke=stroke, sw=0.7, dash="6 4", op=0.9))
    return out


def path_max_grade(pts, win, ds=0.5):
    """折れ線に沿って現地形を ds 刻みで採り、幅 win の窓で最大の勾配[%]を返す(平均だけでは段が読めない・検図 2026-09-06)。"""
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs)
    if L <= 0: return 0.0
    def at(s):
        for a, b in segs:
            l = math.hypot(b[0] - a[0], b[1] - a[1])
            if s <= l: t = s / l if l else 0.0; return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            s -= l
        return pts[-1]
    n = int(L / ds) + 1
    hs = [dem_h(*at(min(i * ds, L))) for i in range(n)]
    k = max(1, int(round(win / ds))); best = 0.0
    for i in range(n - k):
        if hs[i] is None or hs[i + k] is None: continue
        best = max(best, abs(hs[i + k] - hs[i]) / (k * ds) * 100.0)
    return best


def path_stats(pts):
    """折れ線の延長と平均勾配[%]を現地形から出す(数値を文章に写さないため図が算出する)。"""
    L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1))
    h0, h1 = dem_h(*pts[0]), dem_h(*pts[-1])
    gr = abs(h1 - h0) / L * 100.0 if (L and h0 is not None and h1 is not None) else 0.0
    return L, gr


def sando_band(d, PX, PY, LEN):
    sd = d["sando"]
    if sd.get("area"):
        # 2026-09-06 — 参道は敷地割の間に残った道の**領域そのもの**。帯を自分の幅で置かない(ユーザー指摘)。
        o = [PL([(PX(x), PY(z)) for x, z in sd["area"]], fill="var(--michi)", op=0.45,
                stroke="var(--shu)", sw=0.8, close=True),
             PL([(PX(x), PY(z)) for x, z in sd["pts"]], stroke="var(--shu)", sw=0.7, dash="6 4", op=0.9)]
    else:
        o = band(sd["pts"], PX, PY, LEN, sd.get("w") or 5.5, "var(--michi)", "var(--shu)", op=0.45)
    x, z = sd["pts"][-1]
    L, gr = path_stats(sd["pts"])
    g2, g5, g20 = path_max_grade(sd["pts"], 2.0), path_max_grade(sd["pts"], 5.0), path_max_grade(sd["pts"], 20.0)
    o.append(T(PX(x) - 6, PY(z) - 6, "参道 %.0f m ／ 平均 %.1f%% ／ 最大 2m窓 %.0f%%・5m窓 %.0f%%・20m窓 %.0f%%" % (L, gr, g2, g5, g20),
               fs=10, anchor="end", fill="var(--shu)"))
    return o


# ---------------------------------------------------------------- 植栽(社叢・境内の立木・参道沿い・前庭)
def garden_poly(gd):
    """gardens の面(uv)。多角形 `poly` があればそれ、無ければ矩形。面を持たない項(社叢)は None。

    ⚠ 2026-09-06 — 境内の立木3区が矩形から多角形になったので、`lp.rect` 決め打ちをやめた。
    """
    if gd.get("poly"):
        return [(q[0], q[1]) for q in gd["poly"]]
    if gd.get("uv"):                      # 社叢の帯4(多角形を持つ帯)も同じ形で読める
        return [(q[0], q[1]) for q in gd["uv"]]
    if gd.get("u0") is None:
        return None
    return [(gd["u0"], gd["v0"]), (gd["u1"], gd["v0"]),
            (gd["u1"], gd["v1"]), (gd["u0"], gd["v1"])]


def shrub_areas(d):
    """**低木を撒く面**の列 ── (名, 枠の4点[uv], 判定関数, bbox)。

    ⚠ 2026-09-06 検図5巡目 中5: 旧 `shrub_segments()` は `gardens[].shrubBand` を読んでいたが、
    その欄は 2026-09-06b に `shrubs.box` へ置き換わって **json から消えていた**。
    呼び出し3箇所(総当たり・空地の検査・表)が丸ごと空回りしていた(死にコード)。
    ⭐ 面は **枠 `shrubs.box` ∩ (帯の輪郭から `shrubs.crownRKen` 以上内)** で、
    帯が折れる区間にも追随する(検図5巡目 中12 — 低木1本が袖塀へ 0.546m めり込んでいた)。
    """
    out = []
    for gd in d["gardens"]:
        sh = gd.get("shrubs")
        if not sh or not sh.get("box"): continue
        P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
        u0, v0, u1, v1 = sh["box"]
        B = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        r = sh.get("crownRKen", 0.0)
        out.append(("低木の面:" + gd["name"].split("(")[0], B,
                    (lambda B, P, r: (lambda q: in_poly(q, B) and (not P or (
                        in_poly(q, P) and min(_pt_seg(q, P[i], P[(i + 1) % len(P)])
                                              for i in range(len(P))) >= r)))) (B, P, r),
                    (u0, v0, u1, v1)))
    return out


def shrub_ok(gd, q):
    """点が**その区の低木を撒く面**の中か(枠 ∩ 輪郭から樹冠半径以上内)。"""
    sh = gd.get("shrubs") or {}
    if not sh.get("box"): return False
    u0, v0, u1, v1 = sh["box"]
    if not (u0 <= q[0] <= u1 and v0 <= q[1] <= v1): return False
    P = [(x, y) for x, y in (gd.get("poly") or [])]
    if not P: return True
    r = sh.get("crownRKen", 0.0)
    return in_poly(q, P) and min(_pt_seg(q, P[i], P[(i + 1) % len(P)])
                                 for i in range(len(P))) >= r


# ---------------------------------------------------------------- 井戸屋形(前庭の帯の北の端)
def ido_rects(d):
    """井戸屋形の面 ── **芯と寸法からの従属値**。⛔ 矩形を json に書かない(規則4)。

    石敷・軒先・浸透枡・井桁は (u0,v0,u1,v1)、柱は点の列。
    ⭐ `nokiDeKen` / `hafuDeKen` は**柱芯からの出**で、軒先が石敷の縁と一致するように取ってある
    (雨落ちが石敷に落ちる)。一致は `ido_check` が毎回測る。
    """
    io = d.get("ido")
    if not io: return None
    u, v = io["uv"]
    ken = d["const"]["ken"]
    h = io["ishikiKen"] / 2.0
    p = io["hashiraPitchKen"] / 2.0
    # ⭐ 井桁は**外形**で採る(2026-09-07 裁定2)— 内径 `igetaShaku` 尺 + 見付の両側。
    g = io["igetaShaku"] / 6.0 / 2.0 + io.get("igetaMitsukeM", 0.0) / ken
    m = io["masuKen"] / 2.0
    mu, mv = io["masuUV"]
    return {"石敷": (u - h, v - h, u + h, v + h),
            "軒先": (u - p - io["nokiDeKen"], v - p - io["hafuDeKen"],
                     u + p + io["nokiDeKen"], v + p + io["hafuDeKen"]),
            "井桁": (u - g, v - g, u + g, v + g),
            "浸透枡": (mu - m, mv - m, mu + m, mv + m),
            "柱": [(u - p, v - p), (u + p, v - p), (u + p, v + p), (u - p, v + p)]}


def ido_clearances(d, g):
    """井戸屋形の**離隔**(⛔ 設計値ではない従属値)── (名, m) の列。

    ⭐ **起点はすべて「石敷の縁」にそろえる**(2026-09-06 検図5巡目 中8)— 旧版は
    参道の階へは「隅」から、通行帯へは「芯」から測っており、同じ表の2行で起点が違って
    通行帯までの離隔が 2.6 倍に見えていた。
    """
    R = ido_rects(d)
    if not R: return []
    ken = d["const"]["ken"]
    u0, v0, u1, v1 = R["石敷"]
    C = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    out = []
    for k in d["kaidans"]:
        if k["name"] != "参道の階(前庭へ)": continue
        hw = kaidan_wken(d, k) / 2.0
        q = (k["a"][0] - hw, k["a"][1])
        out.append(("石敷の縁 → 参道の階の開口の西の肩",
                    min(_pt_seg(q, C[i], C[(i + 1) % 4]) for i in range(4)) * ken))
    for rt in d.get("routes", []):
        if rt["name"] != "表参(参詣)": continue
        pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
        best = None
        for i in range(len(pts) - 1):
            mid = ((pts[i][0] + pts[i + 1][0]) / 2.0, (pts[i][1] + pts[i + 1][1]) / 2.0)
            te = terrace_at(d, g, mid)
            # ⛔ **前庭の区間だけを測る** — 井戸屋形は前庭の物で、参道(公道・幅 5.5m)の帯まで
            #    混ぜると「最も近い」が坂の上の道の端になり、離隔の意味が変わる
            if te != "Zentei": continue
            hw = route_w(d, rt, te, at=mid) / 2.0 / ken
            dd = min(_pt_seg(c, pts[i], pts[i + 1]) for c in C) - hw
            best = dd if best is None else min(best, dd)
        if best is not None:
            out.append(("石敷の縁 → 動線『%s』の通行帯の縁(前庭の区間)" % rt["name"], best * ken))
        break
    return out


def section_cut_check(d, g):
    """**どの断面にも切られない棟が名簿どおりか**(⛔ 黙って増えない)。

    ⭐ **2026-09-07 検図9巡目 中2 で起こした。**御供所・稲荷社・庚申堂・鐘楼・観音堂の5棟が
    どの断面にも現れず、しかもそのうち二棟は造成の裁定の当事者だった(断面で Δ が読めない)。
    ⚠ 測るのは**幾何**(切断線が棟の矩形に掛かるか)で、断面の marks が `yaku==接続` を
    描かないこととは別(⛔ 二つの物差しを混ぜない — 『作り合い』は線には載っている)。
    """
    uncut = []
    for m in d["munes"]:
        a, b = g.W(m["u0"], m["v0"]), g.W(m["u0"] + m["du"], m["v0"] + m["dv"])
        x0, x1 = sorted([a[0], b[0]]); z0, z1 = sorted([a[1], b[1]])
        hit = False
        for sec in d["sections"]:
            p = d["profiles"][sec["profile"]]
            if p["axis"] == "EW" and z0 - 1e-6 <= p["at"] <= z1 + 1e-6: hit = True
            if p["axis"] == "NS" and x0 - 1e-6 <= p["at"] <= x1 + 1e-6: hit = True
        if not hit: uncut.append(m["name"])
    bad = []
    if d.get("sectionsUncut") is None:
        bad.append("`sectionsUncut`(どの断面にも切られない棟の名簿)の宣言が無い — "
                   "宣言が無ければ棟が断面から落ちても鳴らない(規則19)")
    bad += roster_guard(d.get("sectionsUncut"), uncut,
                        "断面が切らない棟の名簿", "`sectionsUncut`")
    note = ["断面 %d 本が切る棟 %d / %d(切らない %s)【算出 — ⚠ 斜めの断面は数えない】"
            % (len(d["sections"]), len(d["munes"]) - len(uncut), len(d["munes"]),
               "・".join(uncut) or "無し")]
    return bad, note


def keidai_inubashiri_check(d, g):
    """境内の外周の囲い(**腰高の柵**)が**平場の輪郭から犬走り** `const.inubashiri` を残しているか。

    ⭐ 2026-09-07 のユーザー裁定で囲いが**板塀から柵**へ替わった。寄せ幅 `const.inubashiri` は
    板塀を前提に置いた値のままだが、**柵に替えたことによる目減りは無い**(下の〔記録〕が毎回算出する
    ── 柵は線=立子の内面で柱が `postDiaM` だけ外へ出るのに対し、板塀は `itabeiThickM` ぶん出る)。
    ⛔ 指図方は値を動かさない。

    ⭐ **2026-09-07 検図9巡目 中3 で起こした。**指図の中に犬走りは四種あるのに
    (`const._inubashiri` が四つを並べる)、この一つだけが**註も確度も検査も持たず**、
    `inubashiri_check` は前庭の西縁しか測っていなかった。
    ⛔ 宣言が無ければ止める(規則19)。⛔ 値は動かさない — 動かすと板塀の全長と開口が動く。
    ⚠ **辺の上では恒真**(検図8巡目 低5 と同じ形)— 囲いは `derive_runs` が
    `offset_poly_in(輪郭, const.inubashiri)` で作るので、辺の途中の離れは宣言と一致するほかない。
    ⭕ **恒真でないのは角**: 鋭角の隅では隣の辺のほうが近くなり、留めの頭打ち
    (`cosh` を 0.35 で止める)と相まって離れが宣言を下回る。⛔ 止めるのは
    **塀が平場の外へ出たとき**(= 犬走りが消えたとき)だけで、角の目減りは〔記録〕にする —
    直すには輪郭か寸法を動かすことになり、⛔ 指図方が決める件ではない。
    """
    ins = d["const"].get("inubashiri")
    if ins is None:
        return ["犬走り `const.inubashiri` の宣言が無い — 宣言の無い物差しは検査ごと黙って消える"
                "(規則19)"], []
    ken = d["const"]["ken"]
    by = {r["name"]: r for r in d["runs"]}
    r = by.get("Ita_Keidai")
    if not r or not r.get("pts"):
        return ["境内の外周の囲い `runs[Ita_Keidai]` に折れ線が無い — 輪郭からの生成が回っていない"], []
    P = [(q[0], q[1]) for q in d["terraces"][0]["uv"]]
    pts = [(q[0], q[1]) for q in r["pts"]]
    ds, outside = [], []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / 0.25))
        for k in range(n + 1):
            t = k / float(n)
            q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            ds.append((min(_pt_seg(q, P[j], P[(j + 1) % len(P)]) for j in range(len(P))) * ken, q))
            if not in_poly(q, P): outside.append(q)
    lo, hi = min(ds), max(ds)
    bad, note = [], []
    if outside:
        bad.append("境内の外周の囲いが平場の**外**へ出る %d 点(最初 u %.2f, v %.2f)— "
                   "犬走りが消える" % (len(outside), outside[0][0], outside[0][1]))
    short = [q for q in ds if q[0] < ins - 1e-6]
    note.append("境内の外周の囲い(腰高の柵)の**輪郭からの離れ** %.3f 〜 %.3f m(標本 %d 点／宣言 "
                "`const.inubashiri` %.2f m)── ⚠ **辺の上では恒真**(柵は輪郭をこの幅だけ内へ"
                "寄せた生成物)。⭕ 読むのは**角**で、宣言を下回る標本 %d 点・最小 %.3f m は"
                "鋭角の隅で隣の辺のほうが近くなる分【算出】" % (lo[0], hi[0], len(ds), ins,
                                                            len(short), lo[0]))
    # ⭕ **柵に替えたことによる目減りが無いこと**を毎回算出する【検図10巡目 ⭕8 の実測を検査へ結んだ】。
    #    ⛔ 数を文章に写さない(規則4)— 寄せ幅・柱の径・板塀の厚みからの従属値。
    tg = run_tamagaki(d, r)
    if tg is not None:
        eff_s = ins - tg[0]["postDiaM"]                 # 柵: 線=立子の内面。柱が外へ出る
        eff_i = ins - d["const"]["itabeiThickM"]        # 旧・板塀: 線=内法。厚みぶん外へ出る
        mn = (((d.get("planting") or {}).get("clearance") or {}).get("zentei") or {}).get("inuBashiriM")
        note.append("**輪郭から躯体の外面までの実効の犬走り** ── 柵 %.3f m(寄せ幅 %.3f − 柱 "
                    "`tamagaki.postDiaM`)／ 旧・板塀 %.3f m(− `const.itabeiThickM`)。"
                    "⭕ **柵のほうが %.3f m 広い**ので、板塀から柵への差し替えで犬走りは痩せない%s【算出】"
                    % (eff_s, ins, eff_i, eff_s - eff_i,
                       ("(スキル `perimeter.md` の既定 = `planting.clearance.zentei.inuBashiriM` "
                        "%.2f m を%s)" % (mn, "下回らない" if eff_s >= mn - 1e-9 else
                                         "⚠ **下回る** — 寸法の判断は普請奉行"))
                       if mn else ""))
    if short:
        note.append("最も痩せる隅は u %.2f, v %.2f(離れ %.3f m = 宣言の %.0f%%)"
                    "── ⛔ 直すには輪郭か寸法を動かすことになるので指図方は動かさない"
                    "(→ `_pending`「境内の囲いの留めの隅が犬走りを割る」)【算出】"
                    % (lo[1][0], lo[1][1], lo[0], 100.0 * lo[0] / ins))
    return bad, note


def saku_decl_check(d):
    """**柵の宣言** ── `kind` と丈の出所(`hFrom`)が食い違っていないか。

    ⚠ 2026-09-07 検図10巡目 中3/中4。二つの穴が同じ根から出ていた。
    (a) 囲いの展開が姿を **`hFrom` の有無**で分岐していたので、平面図(`kind` で分岐)と
        **物差しが二本**あり、丈を宣言しない `Saku_SW`・`Saku_Sando` が塗り潰しの塀の姿で出ていた。
    (b) `hFrom` は**指し先が壊れれば止まる**が、**宣言ごと消すと止まらない**
        (`run_tamagaki` の `if not hf: return None`)。丈が黙って「—」に落ち、展開図が塀の姿へ戻り、
        `bom` の「丈は `tamagaki` が正典」だけが宙に浮く。
    ⚠ 破壊試験でも `runs[Ita_Keidai].kind` を板塀へ戻して**検査が1本も鳴らなかった**。

    ⛔ **裁定を検査で受ける**(規則19)── 境内の外周は 2026-09-07 のユーザー裁定で**腰高の柵**に
    定まり、丈は前庭の玉垣 `tamagaki.hM` からの従属値である。`const.inubashiri`・`sectionsUncut`・
    `terrainCheck.saichiGai.roster` と同じ作法で、**宣言が消えたら止める**。
    戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    by = {r["name"]: r for r in d["runs"]}
    r = by.get("Ita_Keidai")
    if r is None:
        bad.append("境内の外周の囲い `runs[Ita_Keidai]` が指図に無い")
    else:
        if r.get("kind") != "柵":
            bad.append("`runs[Ita_Keidai].kind` が『%s』── 2026-09-07 のユーザー裁定は**腰高の柵**"
                       "(⛔ 板塀にも築地塀にも戻さない)。種別を替えると平面図の姿・囲いの展開の姿・"
                       "断面・`bom` の行が黙って入れ替わる" % r.get("kind"))
        if not r.get("hFrom"):
            bad.append("`runs[Ita_Keidai].hFrom` の宣言が無い ── 丈が黙って「—」に落ち、"
                       "囲いの展開が姿を失い、`bom`「丈は `tamagaki` が正典」が宙に浮く(規則19)")
    saku = [q for q in d["runs"] if q["kind"] == "柵"]
    nod = [q["name"] for q in saku if not q.get("hFrom")]
    note.append("柵 %d 本(%s)── うち丈を宣言(`hFrom` → `gardens[].tamagaki`)する %d 本。"
                "⚠ 宣言の無い %s は図が丈「—」を刷り、柱の刻みを引かない(⛔ 刻みを発明しない)【算出】"
                % (len(saku), "・".join(q["name"] for q in saku), len(saku) - len(nod),
                   "・".join(nod) or "無し"))
    return bad, note


def ido_check(d):
    """井戸屋形の取り合い ── **軒先 ≡ 石敷の縁**・石敷が帯の輪郭の内・玉垣の開口が引けるか。

    ⛔ 数値を json に置かずに済ませるための検査ではなく、**`nokiDeKen` を動かした日に鳴る**ための検査。
    戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    R = ido_rects(d)
    if R is None: return bad, note
    ken = d["const"]["ken"]
    si, no = R["石敷"], R["軒先"]
    for i, nm in ((0, "西"), (2, "東")):
        if abs(si[i] - no[i]) > 1e-6:
            bad.append("井戸屋形の軒先の%sの出が石敷の縁と %.3f m 食い違う(雨落ちが石敷から外れる)"
                       % (nm, abs(si[i] - no[i]) * ken))
    obi = [q for q in d["gardens"] if q.get("polyIsFence")]
    if obi:
        P = [(q[0], q[1]) for q in obi[0]["poly"]]
        out = [q for q in ((si[0], si[1]), (si[2], si[1]), (si[2], si[3]), (si[0], si[3]))
               if not in_poly((q[0] + (1e-4 if q[0] < (si[0] + si[2]) / 2 else -1e-4),
                               q[1] + (1e-4 if q[1] < (si[1] + si[3]) / 2 else -1e-4)), P)]
        if out:
            bad.append("井戸屋形の石敷の隅 %d 点が帯の輪郭の外へ出ている" % len(out))
        for e in (obi[0].get("tamagaki") or {}).get("edges", []):
            if not e.get("gapFrom"): continue
            a, b = P[e["i"]], P[(e["i"] + 1) % len(P)]
            if tamagaki_gap_span(d, obi[0], e, a, b) is None:
                bad.append("玉垣の辺『%s』の開口(`gapFrom`)が辺に載らない" % e["name"])
    ms = R["浸透枡"]
    ov = max(si[0] - ms[0], ms[2] - si[2], si[1] - ms[1], ms[3] - si[3])
    if ov > 1e-6:
        note.append("井戸屋形の浸透枡が石敷から %.2f m はみ出す — 枡の芯か大きさは庭方の判断"
                    % (ov * ken))
    # ⭐ **枡が帯の輪郭の内か**(2026-09-06 検図5巡目 中9)— 旧版は石敷との比較しか無く、
    #    枡を広場へ 3.21m 出しても何も鳴らなかった。⛔ 帯の外の枡は建たないので**止める**。
    if obi:
        P = [(q[0], q[1]) for q in obi[0]["poly"]]
        outm = [q for q in ((ms[0], ms[1]), (ms[2], ms[1]), (ms[2], ms[3]), (ms[0], ms[3]))
                if not in_poly((q[0] + (1e-4 if q[0] < (ms[0] + ms[2]) / 2 else -1e-4),
                                q[1] + (1e-4 if q[1] < (ms[1] + ms[3]) / 2 else -1e-4)), P)]
        if outm:
            bad.append("井戸屋形の浸透枡の隅 %d 点が帯の輪郭の外へ出ている(`ido.masuUV` を内へ寄せる)"
                       % len(outm))
    # ⭐ **井筒の三重と井桁・礎石の突き合わせ**(2026-09-07 裁定2・庭方)
    io = d["ido"]
    iz = io.get("izutsu") or {}
    # ⛔ **宣言が無ければ止める**(検図8巡目 中4)— 上限や壁厚を消せば、それを測る検査も
    #    一緒に黙って消える。「宣言が無い」を⛔にして初めて、物差しは消せなくなる
    for k, v, w in (("ido.izutsu.kabeAtsuM", iz.get("kabeAtsuM"), "井筒の石積の壁厚"),
                    ("ido.izutsu.nendoMakiTM", iz.get("nendoMakiTM"), "練り粘土の巻きの厚み(=礎石の掛かりの上限)"),
                    ("ido.igetaDanMaxN", io.get("igetaDanMaxN"), "井桁の段数の上限")):
        if v is None:
            bad.append("`%s`(%s)の宣言が無い — 宣言の無い上限は検査ごと黙って消える(規則19)" % (k, w))
    if iz.get("kabeAtsuM") is not None:
        r1, r2, r3 = izutsu_radii(d)
        gh = io["igetaShaku"] / 6.0 * ken / 2.0 + io.get("igetaMitsukeM", 0.0)   # 井桁の外形の半幅
        if gh > r2 + 1e-9:
            bad.append("井桁の外形 %.3f m 角が石積の外径 %.3f m を越える — 天端に座らない"
                       % (gh * 2.0, r2 * 2.0))
        else:
            note.append("井桁は片側 %.3f m ずつ石積の天端に座る(外形 %.3f ≤ 石積の外径 %.3f m)"
                        "・練り粘土には載らない【算出】" % (r2 - gh, gh * 2.0, r2 * 2.0))
        rp, rs = soishi_radii(d)
        if rp < r3 - 1e-9:
            bad.append("柱芯(隅で半径 %.3f m)が練り粘土の巻きの外径 %.3f m の内へ入る" % (rp, r3 * 2.0 / 2.0))
        # ⭐ **宣言した上限に検査を付ける**(2026-09-07 検図7巡目 低9)— `_soishiM` は
        #   「⛔ これより大きくしない」と書くのに、0.45 → 0.90 にしても17本すべて黙っていた。
        #   ⛔ **掛かってよい量の上限は練り粘土の巻きの厚み**(`izutsu.nendoMakiTM`)— これを超えると
        #   礎石の内隅は巻きを通り越して**石積そのものの上に載る**(荷が筒へ直に落ちる)。
        if rs < r2 - 1e-9:
            bad.append("礎石(%.2f m 角)の内隅が半径 %.3f m で**石積の外径 %.3f m の内**へ入る — "
                       "礎石が井筒の石積に載る(掛かり %.3f m > 練り粘土の巻きの厚み %.3f m)。"
                       "⛔ `ido.soishiM` を上限より大きくしない"
                       % (io.get("soishiM", 0.0), rs, r2 * 2.0, r3 - rs, r3 - r2))
        elif rs < r3 - 1e-9:
            if not iz.get("nendoMakiTop"):
                bad.append("礎石(%.2f m 角)の内隅が半径 %.3f m で練り粘土の巻き(外半径 %.3f m)へ "
                           "%.3f m 掛かる — `izutsu.nendoMakiTop` で巻きの天端を下げていない"
                           % (io.get("soishiM", 0.0), rs, r3, r3 - rs))
            else:
                note.append("礎石(%.2f m 角)の内隅は半径 %.3f m で練り粘土の巻き(外半径 %.3f m)へ "
                            "%.3f m 掛かるが(上限=巻きの厚み %.3f m)、巻きの天端を『%s』で止めて解く【算出】"
                            % (io.get("soishiM", 0.0), rs, r3, r3 - rs, r3 - r2, iz["nendoMakiTop"]))
    if io.get("igetaMitsukeM") is not None:
        # ⭐ **段数にも上限**(2026-09-07 検図7巡目 低9)— 3 → 6 にしても何も鳴らなかった。
        mx = io.get("igetaDanMaxN")
        if mx is not None and io["igetaDanN"] > mx:
            bad.append("井桁の段数 %d 段が上限 %d 段(`ido.igetaDanMaxN`)を超える — "
                       "立ち上がり %.2f m は井桁(枠)ではなく筒の続きになる"
                       % (io["igetaDanN"], mx, igeta_rise(d)))
        note.append("井桁の立ち上がり %.2f m = 見付 %.2f m × %d 段(上限 %s 段)【算出】"
                    % (igeta_rise(d), io["igetaMitsukeM"], io["igetaDanN"],
                       "%d" % mx if mx is not None else "—"))
    return bad, note


def tamagaki_gap_span(d, gd, e, a, b):
    """辺の**開口**の沿線区間 (s0, s1)[間]。`gapFrom` が指す面を辺へ射影して出す。

    ⭐ 2026-09-06b — 玉垣の東面は**井戸の口**で開く。⛔ 開口の値を json に二重に書かない。
    """
    src = e.get("gapFrom")
    if not src: return None
    if src == "ido":
        R = ido_rects(d)
        if not R: return None
        u0, v0, u1, v1 = R["石敷"]
        Q = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    else:
        raise SystemExit("玉垣の辺『%s』の gapFrom が引けない: %s" % (e["name"], src))
    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    ss = [(q[0] - a[0]) * tx + (q[1] - a[1]) * tz for q in Q]
    s0, s1 = max(0.0, min(ss)), min(ln, max(ss))
    return None if s1 - s0 <= 1e-9 else (s0, s1)


def tamagaki_gaps(d, gd, e, a, b):
    """辺の**開口**の沿線区間の列 [(s0,s1)]。井戸の口(`gapFrom`)と**木戸**の両方。

    ⭐ 2026-09-06c 裁定4 — 木戸も辺を割る(開口の両脇に柱が立つ)。⛔ 木戸を引かない実延長を刷らない。
    """
    out = []
    gp = tamagaki_gap_span(d, gd, e, a, b)
    if gp is not None: out.append(gp)
    kd = (gd.get("tamagaki") or {}).get("kido")
    if kd and kd.get("edge") == e["i"]:
        ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        s = ((kd["uv"][0] - a[0]) * (b[0] - a[0]) + (kd["uv"][1] - a[1]) * (b[1] - a[1])) / ln
        hw = kd["wM"] / 2.0 / d["const"]["ken"]
        s0, s1 = max(0.0, s - hw), min(ln, s + hw)
        if s1 - s0 > 1e-9: out.append((s0, s1))
    return sorted(out)


def tamagaki_edge_runs(d, gd, e, a, b):
    """辺の**実際に立つ区間**の列 ((a,b) の列)。開口(井戸の口・木戸)を抜く。"""
    gaps = tamagaki_gaps(d, gd, e, a, b)
    if not gaps: return [(a, b)]
    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    P = lambda s: (a[0] + tx * s, a[1] + tz * s)
    out = []
    s = 0.0
    for g0, g1 in gaps:
        if g0 - s > 1e-9: out.append((P(s), P(g0)))
        s = max(s, g1)
    if ln - s > 1e-9: out.append((P(s), b))
    return out


def tamagaki_edges(d, gd):
    """玉垣の辺 ── (名, a, b, 立てるか, **実長**[間], 立つ区間の列)。

    ⛔ 延長を json に書かない(辺と開口からの従属値)。
    ⭐ 2026-09-06b — 辺が**開口を持てる**ようになったので、長さは開口を抜いた実長を返す。
    """
    tg = gd.get("tamagaki")
    P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
    if not tg or not P: return []
    out = []
    for e in tg["edges"]:
        a, b = P[e["i"]], P[(e["i"] + 1) % len(P)]
        rs = tamagaki_edge_runs(d, gd, e, a, b) if e.get("fence") else [(a, b)]
        L = sum(math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]) for q in rs)
        out.append((e["name"], a, b, bool(e.get("fence")), L, rs))
    return out


def tamagaki_bays(gd, ei, run=None):
    """柱の位置(uv)── **隅は必ず柱**、区間の中は芯々 `postPitchKen` 以下で等分する。

    `run` を渡すとその区間だけを割る(開口で切れた辺は区間ごとに割る)。
    """
    P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
    a, b = run if run else (P[ei], P[(ei + 1) % len(P)])
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    k = max(1, int(math.ceil(ln / gd["tamagaki"]["postPitchKen"] - 1e-9)))
    return [(a[0] + (b[0] - a[0]) * i / float(k), a[1] + (b[1] - a[1]) * i / float(k))
            for i in range(k + 1)]


def tamagaki_stats(d, gd):
    """玉垣の 実延長[間] と 柱の数 ── **どちらも辺・開口・芯々からの従属値**。

    ⚠ 2026-09-06 検図4巡目 中4: 旧式は辺ごとに `floor(辺長/芯々)+1` を足しており、
    隅を共有する辺の柱を数え落としていた(5辺の島で 13本 → 12本)。
    **隅柱(立てる区間の端点の集合)+ 各区間の中間柱**として数える。
    ⭐ 2026-09-06b: 開口(井戸の口)で切れた辺は**区間ごとに**割る — 開口の両脇にも柱が要る。
    """
    eg = tamagaki_edges(d, gd)
    if not eg: return None
    L = sum(q[4] for q in eg if q[3])
    corners, mid = set(), 0
    for nm, _a, _b, fence, _ln, rs in eg:
        if not fence: continue
        for rn in rs:
            bays = tamagaki_bays(gd, None, rn)
            corners.add((round(bays[0][0], 4), round(bays[0][1], 4)))
            corners.add((round(bays[-1][0], 4), round(bays[-1][1], 4)))
            mid += len(bays) - 2
    return L, len(corners) + mid


def kido_rect(gd, ken):
    """木戸の**開口の裏へ低木を植えない矩形**(uv の4点)。開口 ± 半幅 × 内へ `insideKen` 間。"""
    tg = gd.get("tamagaki") or {}
    kd = tg.get("kido")
    P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
    if not kd or not P: return None
    a, b = P[kd["edge"]], P[(kd["edge"] + 1) % len(P)]
    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    cu = sum(q[0] for q in P) / len(P); cv = sum(q[1] for q in P) / len(P)
    nx, nz = -tz, tx
    if (cu - kd["uv"][0]) * nx + (cv - kd["uv"][1]) * nz < 0: nx, nz = tz, -tx   # 内向き
    hw = kd["wM"] / 2.0 / ken
    dp = kd.get("insideKen", 1.0)
    u0, v0 = kd["uv"][0] - tx * hw, kd["uv"][1] - tz * hw
    u1, v1 = kd["uv"][0] + tx * hw, kd["uv"][1] + tz * hw
    return [(u0, v0), (u1, v1), (u1 + nx * dp, v1 + nz * dp), (u0 + nx * dp, v0 + nz * dp)]


def kido_bay_check(d):
    """木戸の開口が**辺の中に納まっているか**(端からはみ出さず・他の開口と重ならないか)。

    ⚠ 2026-09-06 検図4巡目 中4: 島の木戸の芯が柱の割付の柱に乗っていた。
    ⭐ 2026-09-06c 裁定4 — 木戸は辺を割るようになった(`tamagaki_gaps`)ので、
    **柱に乗るか**ではなく **辺の端・井戸の口と食い合わないか**を測る。
    残った一枚が垣として成り立つかは検査『玉垣の一枚の内法』が受け持つ。
    """
    bad = []
    for gd in d["gardens"]:
        tg = gd.get("tamagaki") or {}
        kd = tg.get("kido")
        if not kd: continue
        P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
        if not P: continue
        e = [q for q in tg["edges"] if q["i"] == kd["edge"]]
        if not e:
            bad.append("%s の%s が辺 %s を指すが、その辺の宣言が無い" % (gd["name"], kd["name"], kd["edge"]))
            continue
        e = e[0]
        if not e.get("fence"):
            bad.append("%s の%s が『%s』に開くが、この辺には玉垣を立てない宣言"
                       % (gd["name"], kd["name"], e["name"]))
            continue
        a, b = P[kd["edge"]], P[(kd["edge"] + 1) % len(P)]
        ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        s = ((kd["uv"][0] - a[0]) * (b[0] - a[0]) + (kd["uv"][1] - a[1]) * (b[1] - a[1])) / ln
        hw = kd["wM"] / 2.0 / d["const"]["ken"]
        if s - hw < -1e-9 or s + hw > ln + 1e-9:
            bad.append("%s の%s(芯 %.4f 間・幅 %.2f m)が辺『%s』(%.4f 間)からはみ出す"
                       % (gd["name"], kd["name"], s, kd["wM"], e["name"], ln))
            continue
        gp = tamagaki_gap_span(d, gd, e, a, b)
        if gp and gp[0] - 1e-9 < s + hw and s - hw < gp[1] + 1e-9:
            bad.append("%s の%s(%.4f〜%.4f 間)が辺『%s』の開口(`gapFrom`)%.4f〜%.4f 間 と重なる"
                       % (gd["name"], kd["name"], s - hw, s + hw, e["name"], gp[0], gp[1]))
    return bad


def tamagaki_bay_check(d):
    """玉垣の**一枚**(柱と柱の間)の内法が `tamagaki.uchinoriMinM` 以上か。

    ⭐ 2026-09-06c 裁定4(庭方)— 内法 = 柱の芯々 − `postDiaM`。立子が1本も入らない一枚は
    垣ではなく詰め物になる。⛔ 止める — 開口の位置を動かすか区間を統合するかで必ず直る。
    戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    ken = d["const"]["ken"]
    for gd in d["gardens"]:
        tg = gd.get("tamagaki") or {}
        lo = tg.get("uchinoriMinM")
        if lo is None: continue
        worst = None
        for nm, _a, _b, fence, _ln, rs in tamagaki_edges(d, gd):
            if not fence: continue
            for rn in rs:
                bays = tamagaki_bays(gd, None, rn)
                for i in range(len(bays) - 1):
                    p, q = bays[i], bays[i + 1]
                    uchi = math.hypot(q[0] - p[0], q[1] - p[1]) * ken - tg["postDiaM"]
                    ntate = int(math.floor(max(0.0, uchi) / tg["tatekoPitchM"]))
                    if worst is None or uchi < worst[0]: worst = (uchi, nm, ntate)
                    if uchi < lo - 1e-9:
                        bad.append("%s の玉垣『%s』の一枚が内法 %.3f m(立子 %d 本)— 下限 %.2f m を割る"
                                   % (gd["name"], nm, uchi, ntate, lo))
        if worst:
            note.append("%s の玉垣の一枚の**最小の内法** %.3f m(辺『%s』・立子 %d 本／下限 %.2f m)"
                        % (gd["name"], worst[0], worst[1], worst[2], lo))
    return bad, note


def plane_y(d, pl):
    """面の**天端**[m 海抜] ── 正典は `terraces[].y`。造成しない面は None。

    ⚠ 2026-09-07 検図8巡目 中2 — 天端が `planes[].y` と `terraces[].y` の**二重持ち**で、
    幾何の側(`design_y`・切盛・法面・断面・地山)は 8 箇所とも `terraces[].y` を読むのに、
    Δ の検査と面の表だけが `planes[].y` を読んでいた。⛔ `terraces[Keidai].y` を動かしても
    検査は旧い天端を刷り続け(=物差しが図から外れている)。**`planes[].y` は落とした。**
    ⛔ 一つの面が高さの違う terrace を抱えたら検査『面の天端の出所』が⛔で止める。
    """
    ys = [t["y"] for t in d["terraces"]
          if t["name"] in (pl.get("terraces") or []) and t.get("y") is not None]
    return ys[0] if ys else None


def plane_y_check(d):
    """**面の天端の出所**(⛔)── 天端を持つ面はすべて `terraces[].y` から引けること。

    ⭐ 2026-09-07 検図8巡目 中2/中4 ── 三つを⛔で押さえる(規則19: 物差しを消して黙らせない):
    ① `planes[].y` を**復活させない**(二重持ちに戻したら止める)
    ② 一つの面が抱える terrace の `y` は**一致する**(食い違ったらどちらが天端か決まらない)
    ③ **`y` を持つ terrace は必ずどれかの `planes` に属し、その面は `planeDevRoster` を持つ**
       — 面を丸ごと消せば Δ の記録も名簿の見張りも黙って消えるので、**属していないことを⛔にする**
    """
    bad = []
    owner = {}
    for pl in d["planes"]:
        if "y" in pl:
            bad.append("面『%s』が `y` を持つ — 天端の正典は `terraces[].y`(⛔ 二重に持たない)" % pl["name"])
        ys = sorted(set(t["y"] for t in d["terraces"]
                        if t["name"] in (pl.get("terraces") or []) and t.get("y") is not None))
        if len(ys) > 1:
            bad.append("面『%s』が天端の違う terrace を抱える(%s)— どれが天端か決まらない"
                       % (pl["name"], "／".join("%.2f" % q for q in ys)))
        for nm in pl.get("terraces", []): owner.setdefault(nm, []).append(pl)
    for te in d["terraces"]:
        if te.get("y") is None: continue
        pls = owner.get(te["name"], [])
        if not pls:
            bad.append("terrace『%s』(天端 %.2f)がどの `planes` にも属さない — "
                       "Δ の記録も名簿の見張りも黙って消える(規則19)" % (te["name"], te["y"]))
            continue
        for pl in pls:
            if not pl.get("planeDevRoster"):
                bad.append("面『%s』に `planeDevRoster` が無い — 何を測るかの宣言が無い面は"
                           "Δ の行が黙って減っても鳴らない(規則19)" % pl["name"])
    return bad


def plane_dev_check(d, g):
    """**面に載る門・棟・井戸屋形**の Δ = 面の天端 − 造成前の地形【§B-1】。

    ⭐ 2026-09-06c 参考3(庭方)— 井戸屋形の盛土だけを裁くのは片手落ちで、**仁王門は切土の側で
    もっと深い**。⛔ 止めない・⛔ 天端も棟も動かさない。
    ⭐ **2026-09-07 のユーザー裁定で決着した** — 規則3(±0.5m)は屋敷の敷地内の目安であって
    **山上の社地には当てない**(→ `_pending`「前庭と境内の切盛」)。⭕ **代わりに外れている量を
    毎回刷る**のがこの検査の役で、⛔ 止めない・⛔ 名簿から名を外して黙らせない。
    ⭐ 2026-09-06 検図6巡目 中3 — 名は「門・棟」なのに**棟を一つも回していなかった**うえ、
    門を前庭の外へ出すと行が黙って消えた。⛔ `munes` も回し、**測る名簿**から名が落ちたら鳴らす。
    ⭐ 2026-09-07 検図7巡目 中1 — **前庭だけ回して境内を回していなかった。**境内(天端28.3)に
    載る棟にも `PLANE_DEV_LIM_M` を超えるものがあるのに、数が図のどこにも無く検査も無かった。
    ⛔ `planes[]` を**天端を持つ面すべて**について回し、名簿は `planes[].planeDevRoster` が持つ。
    ⭐ 2026-09-07 検図8巡目 中2 — 天端は `plane_y()` が **`terraces[].y` から**引く。
    ⛔ `planes[].y` を読まない(読んでいたので `terraces[Keidai].y` を動かしても物差しが動かなかった)。
    """
    bad, note = [], []
    byte = {t["name"]: t for t in d["terraces"]}
    R_ = ido_rects(d)
    lim = PLANE_DEV_LIM_M
    for pl in d["planes"]:
        top = plane_y(d, pl)                       # ⛔ `planes[].y` を読まない(検図8巡目 中2)
        tes = [byte[q] for q in pl.get("terraces", []) if q in byte]
        if top is None or not tes: continue        # 造成しない面(山麓の通り・社叢)は対象外
        ZP = [terrace_poly(te, g) for te in tes]
        items = []
        for gt in d["gates"]:
            hu, hv = gt["plan"]["du"] / 2.0, gt["plan"]["dv"] / 2.0
            items.append((gt["name"].split("(")[0], gt["u"] - hu, gt["v"] - hv,
                          gt["u"] + hu, gt["v"] + hv))
        # ⛔ **`yaku` で棟をふるい落とさない**(検図7巡目 中1)— 「作り合い」は本殿と幣殿を継ぐ
        #    一間で、礎石を持って地面に載る。接続と書いてあるのは役であって、載らない理由ではない。
        #    ⚠ **屋根の有無は史料が言わない**【?】(考証6巡目 中1)。⛔ 当図は幣殿型なので
        #    『石の間』と呼ばない(石の間型は東照宮系)
        for m in d["munes"]:
            items.append((m["name"], m["u0"], m["v0"], m["u0"] + m["du"], m["v0"] + m["dv"]))
        if R_: items.append(("井戸屋形の石敷", ) + tuple(R_["石敷"]))
        got, over, lines = [], [], []
        for nm, u0, v0, u1, v1 in items:
            ds = []
            n = 7
            for i in range(n + 1):
                for j in range(n + 1):
                    u = u0 + (u1 - u0) * i / float(n); v = v0 + (v1 - v0) * j / float(n)
                    x, z = g.W(u, v)
                    if not any(in_poly((x, z), P) for P in ZP): continue
                    hh = dem_h(x, z)
                    if hh is not None: ds.append(top - hh)
            if not ds: continue
            got.append(nm)
            ex = max(abs(min(ds)), abs(max(ds))) > lim + 1e-9
            if ex: over.append(nm)
            lines.append("『%s』%s の Δ(天端 %.2f − 造成前の地形)= %+.2f 〜 %+.2f m"
                        "(正=盛土/負=切土。目安 ±%.2f m)%s【算出 P】"
                        % (pl["name"], nm, top, min(ds), max(ds), lim,
                           "　⚠ **目安を超える**" if ex else ""))
        bad += roster_guard(pl.get("planeDevRoster"), got, "『%s』の Δ を測る名簿" % pl["name"],
                            "`planes[%s].planeDevRoster`" % pl["name"])
        note.append("『%s』(天端 %.2f)に載って Δ を測った物 %d 件(門 %d・棟 %d・井戸屋形 %s)"
                    "── **目安 ±%.2f m を超えるもの %d 件**%s【算出】"
                    % (pl["name"], top, len(got),
                       len([q for q in d["gates"] if q["name"].split("(")[0] in got]),
                       len([q for q in d["munes"] if q["name"] in got]),
                       "有" if "井戸屋形の石敷" in got else "無", lim, len(over),
                       (" — " + "・".join(over)) if over else ""))
        note += lines                          # ⭐ **まとめを先に**(表の上限で落ちるのは明細の側)
    return bad, note


def inubashiri_check(d, g):
    """前庭の**西縁に取り付く物**が腰石垣の壁面から犬走り(`inuBashiriM`)を残しているか。

    ⚠ 2026-09-06 検図6巡目 中4 — 犬走りは**植込みの退避**にしか効いておらず、坂下の門は
    壁面から 0.273 m で立っていた(宣言 0.30 m 割れ)。⛔ 止める — 犬走りの無い縁は歩けない。
    ⭐ 測る名簿は `planting.clearance.zentei.inuBashiriRoster` が宣言し、
    **名が落ちたら鳴らす**(⛔ 行が黙って減るのを防ぐ)。
    ⚠ 許容 `INU_TOL_M` は**浮動小数の丸めだけ**を吸う値で、⛔ 設計の余裕ではない。
    ⭐ 2026-09-07 検図8巡目 低5 — **門の行は恒真**。`gates[].uFrom` が同じ `inuBashiriM` から
    門の芯を算出しているので、値を 0.30 → 0.50 にしても門は一緒に動き⛔は出ない。
    ⛔ 恒真なのは門だけではない ── **門の面の通りに載る物**(帯の輪郭・玉垣)も一緒に動く。
    ⛔ 最小の犬走りをこれらで代表させない — **恒真の物を除いた最小**を併記して、
    実際に犬走りを拘束している物を名指しする。
    ⭐ 2026-09-07 検図7巡目 低4 — 旧註の括弧「0.165 間 = 0.29997 m」は**通り**の値であって許容ではなく、
    その 0.03 mm は門の芯を丸めて持っていたことの現れだった。芯を `gates[].uFrom` からの
    従属値にしたので**丸めの差は消え**、許容は 1 μm へ絞った(⛔ 設計の余裕として使い回さない)。
    """
    bad, note = [], []
    cz = (d["planting"]["clearance"] or {}).get("zentei") or {}
    inu = cz.get("inuBashiriM")
    # ⛔ **宣言が無ければ止める**(検図8巡目 中4)— 旧版は黙って戻り、検査が丸ごと消えても
    #    件数は 0 のままだった(物差しを消して黙らせられる形)
    if inu is None:
        return ["犬走り `planting.clearance.zentei.inuBashiriM` の宣言が無い — "
                "宣言の無い物差しは検査ごと黙って消える(規則19)"], note
    if not cz.get("inuBashiriRoster"):
        bad.append("犬走りを測る名簿 `planting.clearance.zentei.inuBashiriRoster` の宣言が無い — "
                   "何を測るかの宣言が無ければ行が黙って減っても鳴らない(規則19)")
    ken = d["const"]["ken"]
    ZP = terrace_poly(d["terraces"][1], g)
    uw = min(q[0] for q in terrace_poly_uv(d["terraces"][1]))
    # ⛔ **恒真の行を「拘束している物」と読ませない**(検図8巡目 低5)。
    #    `gates[].uFrom` がこの犬走りから門の芯を出しているので、**その門の面の通りに載る物**は
    #    `inuBashiriM` を動かすと一緒に動く(門・帯の輪郭・玉垣がそれ)。実測でも 0.30 → 0.50 で
    #    三者とも +0.20 m 動く。⛔ 最小の犬走りをこれらで代表させない
    faces = []
    for gt in d["gates"]:
        if gt.get("uFrom", {}).get("clearance") == "inuBashiriM":
            faces += [gate_face_u(d, gt["name"], "西"), gate_face_u(d, gt["name"], "東")]
    items = []                                        # (名, その物の西端 u)
    dep = set()                                       # 門の面から引いた通り=**恒真**の物
    for gt in d["gates"]:
        hu, hv = gt["plan"]["du"] / 2.0, gt["plan"]["dv"] / 2.0
        if not in_poly(g.W(gt["u"], gt["v"]), ZP): continue
        items.append(("門:" + gt["name"], gt["u"] - hu))
    for gd in d["gardens"]:
        nm = gd["name"].split("(")[0]
        P = garden_poly(gd)
        if not P or not in_poly(g.W(*P[0]), ZP): continue
        if gd.get("polyIsFence"):
            items.append(("帯の輪郭:" + nm, min(q[0] for q in P)))
        elif gd.get("noPlant"):
            items.append(("空地:" + nm, min(q[0] for q in P)))
        sb = shrub_box(gd)
        if sb: items.append(("低木を撒く面:" + nm, min(q[0] for q in sb)))
        if gd.get("tamagaki"):
            us = [q[0] for _n, _a, _b, fence, _l, rs in tamagaki_edges(d, gd) if fence
                  for rn in rs for q in rn]
            if us: items.append(("玉垣:" + nm, min(us)))
    R_ = ido_rects(d)
    if R_ and in_poly(g.W(R_["石敷"][0], R_["石敷"][1]), ZP):
        items.append(("井戸:石敷", R_["石敷"][0]))
    byprop = {}
    for nm, Q in prop_rects(d):
        base = nm.rsplit(" ", 1)[0]
        u0 = min(q[0] for q in Q)
        if not in_poly(g.W(*Q[0]), ZP): continue
        byprop[base] = min(u0, byprop.get(base, u0))
    for base, u0 in sorted(byprop.items()):
        items.append(("点景:" + base, u0))
    worst, worstF = None, None                        # 全体の最小 / **恒真の物を除いた**最小
    for nm, u0 in items:
        m = (u0 - uw) * ken
        if any(abs(u0 - f) < 1e-9 for f in faces): dep.add(nm)
        if worst is None or m < worst[1]: worst = (nm, m)
        if nm not in dep and (worstF is None or m < worstF[1]): worstF = (nm, m)
        if m < inu - INU_TOL_M:
            bad.append("%s の西端が腰石垣の壁面(u %.3f)から %.3f m — 犬走り %.2f m を割る"
                       % (nm, uw, m, inu))
    bad += roster_guard(cz.get("inuBashiriRoster"), [q[0] for q in items],
                        "犬走りを測る名簿", "`planting.clearance.zentei.inuBashiriRoster`")
    if worst:
        note.append("前庭の西縁に取り付く物 %d 件の**最小の犬走り** %.3f m(%s／下限 %.2f m)"
                    "── **恒真の物(門とその面に載る物)を除いた最小**"
                    "(= 実際に拘束している物)%s【算出】"
                    % (len(items), worst[1], worst[0], inu,
                       ("%.3f m(%s)" % (worstF[1], worstF[0])) if worstF else "—"))
    if dep:
        note.append("**恒真の行** %d 件(『%s』)── どれも `gates[].uFrom` がこの犬走りから出した"
                    "**門の面の通り**に載る物で、`inuBashiriM` を動かすと一緒に動く。"
                    "⛔ 最小の犬走りをこれらで代表させない — 実際に拘束しているのは残りの物【算出】"
                    % (len(dep), "』『".join(sorted(dep))))
    return bad, note


def roster_guard(roster, got, label, where):
    """**宣言した名簿と図の側の実物を突き合わせる。**⛔ 行が黙って減るのを防ぐ(規則19)。

    ⭐ 2026-09-07 検図8巡目 中4 — 旧版は**一方向**(名簿の名が図から落ちたら鳴るが、
    図の側に増えても鳴らない)だった。⛔ **両方向**にする — 名簿に無い物が測られていたら、
    それは「宣言していない物を検査が黙って呑んだ」ことで、名簿が物差しとして働いていない。
    ⛔ 名簿そのものが無い場合は、宣言の有無を検める側(`plane_y_check` ほか)が⛔で止める。
    """
    if not roster: return []
    out = []
    miss = [q for q in roster if q not in got]
    if miss:
        out.append("%s(%s)の『%s』を測れていない — 対象が消えたか名が変わった"
                   % (label, where, "』『".join(miss)))
    extra = [q for q in got if q not in roster]
    if extra:
        out.append("%s(%s)に無い『%s』を測っている — 宣言していない物が図に増えた(名簿へ足す)"
                   % (label, where, "』『".join(extra)))
    return out


def shisen_check(d):
    """前庭の**視線の抜き** ── 参道の芯から `shisenNukiKen` の帯に玉垣より高い物を置かない。

    ⭐ 2026-09-06c 裁定3(庭方)— 男坂の退避のキャップを外した代わりに効かせる宣言。
    u の範囲は**前庭の西縁 → 帯の東縁**(⛔ 素の数を json に置かない)。
    ⭕ 低木(`shrubs.hM`)は除く — 麓から男坂と仁王門を見せる抜きは低木の丈では塞がらない。
    ⭐ 2026-09-07 裁定1(庭方)— **基準は幹の芯・条件は枝下**。樹冠が抜きに掛かるのは可だが、
    **北の木は樹冠の南端が参道の芯より北・南の木は北端が南**でなければ芯の見通しが塞がる。
    ⛔ 幹・柱・塀・縁台は抜きに入れない(⭕ 門と、門と一体の袖塀は**抜きの終点**なので対象外)。
    ⚠ 一本立ち以外は**〔記録〕どまり** — 何を退けるかは庭方の意匠で、⛔ 指図方が裁かない。
    """
    bad, note = [], []
    cz = (d["planting"]["clearance"] or {}).get("zentei") or {}
    hk = cz.get("shisenNukiKen")
    gd = obi_garden(d)
    if hk is None or not gd: return bad, note
    ken = d["const"]["ken"]
    hlim = gd["tamagaki"]["hM"]
    u0 = min(q[0] for q in terrace_poly_uv(d["terraces"][1]))
    u1 = max(q[0] for q in gd["poly"])

    def inband(u, v): return u0 - 1e-9 <= u <= u1 + 1e-9 and abs(v) <= hk + 1e-9

    for g2 in d["gardens"]:
        if (g2.get("clearance") or "") != "zentei": continue
        for sg in g2.get("singles", []):
            u, v = sg["uv"]
            if inband(u, v) and (sg.get("h") or 0.0) > hlim + 1e-9:
                bad.append("『%s』(丈 %.1f m・(%.3f, %.3f))が視線の抜き(参道の芯から %.1f 間・"
                           "u %.3f〜%.3f)の中で玉垣 %.1f m を越える"
                           % (sg["name"], sg["h"], u, v, hk, u0, u1, hlim))
            # ⭐ 樹冠は掛かってよいが**参道の芯は越えない**(2026-09-07 裁定1)
            if not (u0 - 1e-9 <= u <= u1 + 1e-9) or abs(v) < 1e-9: continue
            r = single_crown(d, sg)
            if r is None: continue
            near = (v - r) if v > 0 else (v + r)
            if (v > 0 and near < 0) or (v < 0 and near > 0):
                bad.append("『%s』の樹冠の%sの端 v %+.4f 間が参道の芯を越える(幹 v %+.3f・樹冠 %.2f m)"
                           % (sg["name"], "南" if v > 0 else "北", near, v, r * 2.0 * ken))
            else:
                note.append("『%s』の樹冠の%sの端 v %+.4f 間(= 参道の芯から %.3f m %s)【算出】"
                            % (sg["name"], "南" if v > 0 else "北", near, abs(near) * ken,
                               "北" if v > 0 else "南"))
    # 〔記録〕 幹以外で**視線を横切る**物 — ⭕ 門とその袖塀は終点なので除く
    # ⭐ 2026-09-07 検図7巡目 中3 — 旧版は「抜きの矩形に入るか」で測っていたので、
    #   **軸に平行に並走するだけの囲い**(`Ita_ZSW` は抜きの縁から犬走り 0.25 間の内で、
    #   幾何学的に必ず入る)が毎回名を連ね、宣言『塀は抜きに入れない』を実行できなかった。
    #   ⛔ 板塀を動かして黙らせない(南縁の囲いは要る)。**物差しの側を「横切るか」へ改める。**
    def crosses(a, b):
        """その区間が**視線を横切る**か。⭕ 軸(v=0)に平行な並走は横切らない。"""
        if not (min(a[0], b[0]) <= u1 + 1e-9 and max(a[0], b[0]) >= u0 - 1e-9): return False
        du_, dv_ = b[0] - a[0], b[1] - a[1]
        if a[1] * b[1] <= 0.0 and abs(dv_) > 1e-9: return True      # 芯 v=0 を跨ぐ
        return abs(dv_) > abs(du_) and (inband(*a) or inband(*b))   # 抜きの中で軸を切る向き
    sode = set()
    for e in (gd.get("tamagaki") or {}).get("edges", []):
        if e.get("run"): sode.add(e["run"])
    stand, para = [], []
    for r in d["runs"]:
        if r["name"] in sode or not r.get("a") or not r.get("b"): continue
        segs_ = list(run_segs(r))
        if any(crosses(a, b) for a, b in segs_):
            stand.append("%s『%s』" % (r["kind"], r["name"]))
        elif any(inband(*q) for a, b in segs_ for q in (a, b)):
            para.append("%s『%s』" % (r["kind"], r["name"]))
    for nm, Q in prop_rects(d):
        if any(inband(*q) for q in Q): stand.append("点景『%s』" % nm)
    note.append("視線を**横切る**幹以外の物 %d 件%s"
                "(⭕ 門と袖塀 %s は終点なので除く。⛔ 退けるかは庭方の意匠)"
                % (len(stand), (" — " + "・".join(sorted(set(stand)))) if stand else "",
                   "／".join(sorted(sode)) or "—"))
    if para:
        note.append("抜きの帯に**並走する**(軸に平行=何も塞がない)囲い %d 件 — %s"
                    "【算出 — 抜きの縁は前庭の南縁の土留めから犬走りぶん内なので、"
                    "南縁の囲いは幾何学的に必ず帯に入る】" % (len(para), "・".join(sorted(set(para)))))
    note.append("視線の抜き = 参道の芯から %.1f 間(%.2f m)・u %.3f〜%.3f に 玉垣 %.1f m より高い物を置かない"
                "(低木は除く／樹冠は掛かってよいが芯は越えない)【算出 — u は前庭の西縁と帯の東縁から】"
                % (hk, hk * ken, u0, u1, hlim))
    return bad, note


def shrub_box(gd):
    """低木を撒く面の**枠**(uv の4点)。⚠ 枠の中がすべて撒ける訳ではない — 実際の面は
    `shrub_ok`(枠 ∩ 帯の輪郭から `crownRKen` 以上内)で、帯の折れに追随する。"""
    sh = gd.get("shrubs") or {}
    if not sh.get("box"): return None
    u0, v0, u1, v1 = sh["box"]
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def island_shrubs(gd, ken):
    """帯(旧・植込みの島)の照葉低木の位置 ── **面からの従属値**。⛔ 本数を json に書かない。

    `shrubs.box`(2026-09-06b の帯)があればその面、無ければ玉垣の芯線から**芯々の半分**だけ
    内へ寄せた面を、芯々の格子で走査する。⭐ どちらの形でも**木戸の開口の裏は空ける**。
    """
    sh = gd.get("shrubs")
    P = [(q[0], q[1]) for q in (gd.get("poly") or [])]
    if not sh or not P: return []
    st = sh["spacingM"] / ken
    # ⭐ **木戸の開口の裏は空ける**(2026-09-06 検図4巡目 中4 — 開口の真裏 0.60m に低木が立っていた)
    kr = kido_rect(gd, ken)
    B = shrub_box(gd)
    if B:
        # ⭐ **輪郭から樹冠半径以上**(2026-09-06 検図5巡目 中12 — 帯が v3.5 で折れるのを枠が見ておらず、
        #    低木1本が袖塀 `Ita_Niou_N` へ 0.546m めり込んでいた)
        src = (q for q in poly_scan(B, st) if shrub_ok(gd, q))
    else:
        ins = st / 2.0
        src = (q for q in poly_scan(P, st)
               if min(_pt_seg(q, P[i], P[(i + 1) % len(P)]) for i in range(len(P))) >= ins)
    return [q for q in src if not (kr and in_poly(q, kr))]


def sankaku_rows(d):
    """前庭の不等辺三角形 ── **三辺は三点からの従属値**。⛔ 長さを json に書かない。

    `gardens[].sankaku.pts[].from` は「gardens:<区>/<一本立ち>」「slopeBands:<帯>/<一本立ち>」。
    """
    idx = {}
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            for hold in (gd.get("name"), str(gd.get("band")) if gd.get("band") else None):
                if hold: idx[hold + "/" + sg["name"]] = sg
    for gd in d["gardens"]:
        sk = gd.get("sankaku")
        if not sk: continue
        pts = []
        for q in sk["pts"]:
            _, _, key = q["from"].partition(":")
            pts.append((q["name"], (idx.get(key) or {}).get("uv")))
        out = []
        for i in range(len(pts)):
            (na, a), (nb, b) = pts[i], pts[(i + 1) % len(pts)]
            out.append((na, nb, None if (a is None or b is None)
                        else math.hypot(a[0] - b[0], a[1] - b[1])))
        return sk, pts, out
    return None, [], []


def _single_dims(d, sg):
    """一本立ちの丈・樹冠の刷り方 ── **仮値と従属倍率を隠さない**(2026-09-07 中1・裁き2)。"""
    if not sg.get("h"): return ""
    out = " 丈%.1fm" % sg["h"]
    if sg.get("crown"):
        out += "・樹冠%.2fm%s" % (sg["crown"],
                                 "<b>(⚠ 部材未計測の仮値)</b>" if sg.get("crownProvisional") else "")
    elif sg.get("layer") == "中木":
        xz = crown_scale_xz(d, "chuboku", single_prefab(d, sg), sg["h"])
        r = single_crown(d, sg)
        out += ("・樹冠%.2fm【従属 樹冠÷丈】" % (r * 2.0 * d["const"]["ken"])) if r else ""
        out += ("・scaleXZ %.3f【従属】" % xz) if xz else ""
    return out


def sankaku_check(d):
    """**前庭の不等辺三角形**が二等辺に近づいていないか【低4 庭方 2026-09-07】。

    ⛔ 宣言(「⛔ 二等辺に近づけない」)だけあって閾値も検査も無いものは必ず破られる(規則19)。
    物差しは **最も近い二辺の差 ≥ `sankaku.minDiffKen`**(⛔ 最大/最小の比では測らない —
    比は最も長い辺と最も短い辺しか見ず、**中の二辺がそろっても気づかない**)。
    ⛔ 下限を緩めて黙らせない — 崩すなら三点の位置(意匠)を庭方が動かす。
    """
    bad, note = [], []
    sk, pts, sides = sankaku_rows(d)
    if not sk: return bad, note
    lim = sk.get("minDiffKen")
    if lim is None:
        bad.append("`gardens[].sankaku.minDiffKen`(最も近い二辺の差の下限)の宣言が無い — "
                   "宣言の無い縛りは必ず破られる(規則19)")
        return bad, note
    L = sorted(q[2] for q in sides if q[2] is not None)
    if len(L) < 3:
        bad.append("前庭の不等辺三角形の三点のうち %d 点しか引けない" % len(L))
        return bad, note
    dmin = min(L[1] - L[0], L[2] - L[1])
    if dmin < lim - 1e-9:
        bad.append("前庭の不等辺三角形の**最も近い二辺の差** %.3f 間(%.2f m)が下限 %.2f 間を割る"
                   "(⛔ 二等辺に近づけない)" % (dmin, dmin * d["const"]["ken"], lim))
    note.append("前庭の不等辺三角形 三辺 %s 間 ／ **最も近い二辺の差** %.2f 間"
                "(%.0f%% ／ 下限 %.2f 間)・最大/最小 %.2f 倍【算出】"
                % ("・".join("%.2f" % q for q in L), dmin, dmin / L[0] * 100.0, lim, L[2] / L[0]))
    return bad, note


def sekitoro_rows(d):
    """石灯籠の**隣どうしの芯々**[間] ── ⛔ 等間隔にしない(2026-09-07 低1)。従属値。"""
    for pr in d["props"]:
        if pr["name"] != "石灯籠" or not pr.get("uv"): continue
        Q = sorted(pr["uv"], key=lambda q: q[0])
        return [math.hypot(Q[i + 1][0] - Q[i][0], Q[i + 1][1] - Q[i][1])
                for i in range(len(Q) - 1)]
    return []


def sekitoro_check(d, g=None):
    """石灯籠が**寸分たがわぬ等間隔**になっていないか【低1 庭方 2026-09-07】。

    並びと数は【S】だが**位置は【U】**で、寸分たがわぬ等間隔は近代の据え方【U 設計判断】。
    ⚠ 2026-09-07 考証6巡目 中2 — 旧版は『築山庭造伝』を根拠に掲げたが、台帳の当該項に
    「等間隔を避ける」の**逐語が無く**、同項は自ら「型の名を借りるだけで当屋敷の典拠には
    ならない」と釘を刺している。石灯籠は社頭の献納物で作庭の対象でもない。⭕ 結論は動かない。
    ⛔ 止める — 揺らぎが消えたら図に出さずに黙って直る道を残さない。物差しは検査の側が持つ。
    """
    bad, note = [], []
    ds = sekitoro_rows(d)
    if len(ds) < 2: return bad, note
    if max(ds) - min(ds) < SEKITORO_JITTER_MIN_KEN - 1e-9:
        bad.append("石灯籠の芯々が %s 間で**ほぼ等間隔**(振れ %.3f 間 < 下限 %.2f 間)— "
                   "⛔ 等間隔に据えない【U 設計判断】"
                   % ("・".join("%.2f" % q for q in ds), max(ds) - min(ds), SEKITORO_JITTER_MIN_KEN))
    note.append("石灯籠の隣どうしの芯々 %s 間(振れ %.2f 間 ／ 下限 %.2f 間・⛔ 等間隔にしない)【算出】"
                % ("・".join("%.2f" % q for q in ds), max(ds) - min(ds), SEKITORO_JITTER_MIN_KEN))
    # ⭐ **台座が動線の通行帯へ出ていないか**(2026-09-07 検図9巡目 低4)。
    #    面(`planM`)を与えて初めて測れるようになった。⚠ 〔記録〕どまり — 石灯籠の**数と並びは【S】**で、
    #    動かせるのは【U】の具体の位置だけ。どれをどれだけ動かすかは庭方の意匠(⛔ 指図方が裁かない)
    if g is not None:
        ken = d["const"]["ken"]
        te = d["terraces"][0]["name"]
        for nm, Q in prop_rects(d):
            if not nm.startswith("石灯籠"): continue
            for rt in d.get("routes", []):
                pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
                dm = min(_pt_seg(q, pts[i], pts[i + 1])
                         for q in Q for i in range(len(pts) - 1)) * ken
                hw = route_w(d, rt, te) / 2.0
                if dm < hw:
                    note.append("『%s』の台座が動線『%s』の**通行帯へ %.3f m 出る**"
                                "(外形の隅 → 芯 %.3f m ／ 通行帯の半幅 %.3f m)【算出 — "
                                "⛔ 退けるかは庭方の意匠。→ `_pending`「石灯籠 其4 が御成の通行帯へ出る」】"
                                % (nm, rt["name"], hw - dm, dm, hw))
    return bad, note


# 石灯籠の芯々の振れの下限[間](**検査の物差しであって設計値ではない**ので json に置かない)。
# ⭐ 2026-09-07 庭方3巡目 低1 — 0.2〜0.4 間の揺らぎを与えるという裁きの下側を物差しに採る。
SEKITORO_JITTER_MIN_KEN = 0.2


def cluster_boxes(c):
    """塊の箱(uv の [u0,v0,u1,v1])。`box` 単数と `boxes` 複数の両方に対応。"""
    if c.get("boxes"): return [tuple(q) for q in c["boxes"]]
    if c.get("box"):   return [tuple(c["box"])]
    return []


def cluster_n(c):
    """塊の本数。範囲 [lo,hi] で書かれていれば中央を採る。"""
    n = c.get("n")
    if isinstance(n, (list, tuple)): return sum(n) / 2.0
    return float(n or 0)


def cluster_label(c):
    n = c.get("n")
    if isinstance(n, (list, tuple)): return "%s %d〜%d本" % (c["name"], n[0], n[1])
    return "%s %d本" % (c["name"], n or 0)


def edge_offset(d, idx, ins_ken):
    """`polygon` の辺 idx=[i,j] を内側へ ins_ken[間] 寄せた線分(uv)。参道の柵・高木の縁の線の正典。"""
    g = G(d)
    a, b = d["polygon"][idx[0]], d["polygon"][idx[1]]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    nx, nz = dz / L, -dx / L                       # 社地は辺の西 = 内向き
    t = ins_ken * d["const"]["ken"]
    return [(g.U(a[0] + nx * t), g.V(a[1] + nz * t)),
            (g.U(b[0] + nx * t), g.V(b[1] + nz * t))]


def sando_offset_check(d):
    """参道の柵と高木の縁の線が、宣言どおり社地の辺のオフセットになっているか。

    ⭐ 座標をベタで持たせた代わりに**辺との食い違いを組む前に鳴らす**(辺を動かした日に黙って取り残される)。
    """
    bad = []
    rs = d.get("sando", {}).get("roadside") or {}
    tgt = [(r.get("fromEdge"), r.get("insetKen"), [tuple(r["a"]), tuple(r["b"])], r["name"])
           for r in d["runs"] if r.get("fromEdge")]
    tl = rs.get("takagiEdgeLine")
    if tl and tl.get("fromEdge"):
        tgt.append((tl["fromEdge"], tl["insetKen"], [tuple(q) for q in tl["uv"]], "高木の縁の線"))
    for idx, ins, got, nm in tgt:
        want = edge_offset(d, idx, ins)
        for q in got:
            dd = min(math.hypot(q[0] - w[0], q[1] - w[1]) for w in want)
            if dd > 0.02:
                bad.append("%s の端点 (%.3f, %.3f) が 辺%s を %.1f間 寄せた線から %.3f間 ずれる"
                           % (nm, q[0], q[1], idx, ins, dd))
    return bad


def fumiishi_rects(d):
    """踏石の矩形(uv)。**`from` から従属して算出する** — 座標を二重に持たない(規則5)。"""
    g = G(d)
    ken = d["const"]["ken"]
    src = list((d["sando"].get("roadside") or {}).get("fumiishi", []))
    src += list((d["terraces"][1].get("surface") or {}).get("fumiishi", []))
    out = []
    for f in src:
        kind, _, nm = f.get("from", "").partition(":")
        dp = f.get("depthKen", 1.0)
        if kind == "torii":
            t = [q for q in d["torii"] if q["name"] == nm and q.get("pos")]
            if not t: continue
            u, v = g.U(t[0]["pos"][0]), g.V(t[0]["pos"][1])
            h = f.get("squareKen", 1.0) / 2.0
            out.append((f["name"], u - h, v - h, u + h, v + h))
        elif kind == "gate":
            gt = [q for q in d["gates"] if q["name"] == nm]
            if not gt: continue
            gt = gt[0]; pl = gt["plan"]
            # ⭐ **踏石の幅は戸口の内法**(`monguchiKen`)。三間一戸は三間の幅に戸口ひとつで、
            #    両脇間は連子。⛔ `plan.dv`(桁行の全幅)を戸口として敷かない(2026-09-06 検図4巡目 中10)
            hu, hv = pl["du"] / 2.0, gt.get("monguchiKen", pl["dv"]) / 2.0
            if f.get("side") == "E":
                out.append((f["name"], gt["u"] + hu, gt["v"] - hv, gt["u"] + hu + dp, gt["v"] + hv))
            else:
                out.append((f["name"], gt["u"] - hu - dp, gt["v"] - hv, gt["u"] - hu, gt["v"] + hv))
        elif kind == "kaidan":
            k = [q for q in d["kaidans"] if q["name"] == nm]
            if not k: continue
            k = k[0]
            hw = kaidan_wken(d, k) / 2.0
            u, v = k["a"]
            if f.get("side") == "S":
                out.append((f["name"], u - hw, v - dp, u + hw, v))
            else:
                out.append((f["name"], u - hw, v, u + hw, v + dp))
    return out


def _takagi_singles(gd):
    """その区・帯の一本立ちのうち**高木層**のもの(層は `layer`、無ければ樹種で読む)。"""
    out = []
    for sg in gd.get("singles", []):
        lay = sg.get("layer") or ("松" if "マツ" in (sg.get("kind") or "") else "落葉")
        if lay in ("松", "落葉"): out.append(sg)
    return out


def plant_rows(d, g):
    """高木の本数の内訳。**図と表が同じ関数から数える**(総数を文章に写さない)。"""
    rows = []
    for r in band_stats(d, g):
        if "b" not in r: continue
        rows.append(("社叢 帯%d %s" % (r["b"]["band"], r["b"]["name"]), int(round(r["takagi"])),
                     "有効面 × 採用密度"
                     + ("(視線の塊・一本立ち %g 本を差し引く)" % r["cut"] if r["cut"] else "")))
    for gd in d["gardens"]:
        n = sum(cluster_n(c) for c in gd.get("clusters", [])) + len(_takagi_singles(gd))
        if n: rows.append((gd["name"], int(round(n)), "塊+一本立ち"))
    for b in d["slopeBands"]:
        n = len(_takagi_singles(b))
        if n: rows.append(("社叢 帯%d の一本立ち" % b["band"], n, "帯の本数から差し引き済み"))
    for c in d["planting"].get("viewClusters", []):
        rows.append(("視線の塊 " + c["name"], int(cluster_n(c)), "帯1〜3から差し引き済み"))
    return rows


def draw_planting(d, lp, inwin, kan_forest=True):
    """境内の平面図へ植栽を落とす(社叢の帯4・立木の面・塊・一本立ち・参道沿い・踏石)。

    ⛔ **図に出ない設計値を残さない**(規則19) — json に入れた面・塊・線はここで必ず描く。
    """
    o = []
    # 社叢 帯4(多角形を持つ帯だけ面で描ける。帯1〜3 は幾何が無い → `_pending`)
    for b in d["slopeBands"]:
        if not b.get("uv"): continue
        o.append(PL([(lp.X(u), lp.Y(v)) for u, v in b["uv"]], fill="var(--take)", op=0.16,
                    stroke="var(--take)", sw=1.1, dash="9 4", close=True))
        cu = sum(q[0] for q in b["uv"]) / len(b["uv"]); cv = sum(q[1] for q in b["uv"]) / len(b["uv"])
        o.append(T(lp.X(cu), lp.Y(cv), "社叢 帯%d %s" % (b["band"], b["name"]),
                   fs=10.5, anchor="middle", fill="var(--take)"))
    return o


def draw_clusters(d, lp, inwin):
    """立木の塊(細線の箱)と一本立ち(点)、主景の固定木。"""
    o = []
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            for u0, v0, u1, v1 in cluster_boxes(c):
                if not inwin([u0, v0], [u1, v1]): continue
                o.append(lp.rect(u0, v0, u1, v1, fill="none", stroke="var(--take)", sw=0.7, dash="3 3"))
                o.append(T(lp.X((u0 + u1) / 2.0), lp.Y(v1) - 3, cluster_label(c),
                           fs=9, anchor="middle", fill="var(--take)"))
            if c.get("alongTakagiEdgeLine"):
                tl = (d["sando"].get("roadside") or {}).get("takagiEdgeLine")
                if not tl: continue
                (au, av), (bu, bv) = edge_offset(d, tl["fromEdge"], tl["insetKen"])
                w = c.get("widthKen", 1.5)
                dx, dv = bu - au, bv - av
                L = math.hypot(dx, dv) or 1.0
                nx, nz = dv / L, -dx / L            # 内側(西)へ
                ring = [(au, av), (bu, bv), (bu + nx * w, bv + nz * w), (au + nx * w, av + nz * w)]
                o.append(PL([(lp.X(u), lp.Y(v)) for u, v in ring], fill="var(--take)", op=0.28,
                            stroke="var(--take)", sw=0.7, close=True))
                o.append(T(lp.X((au + bu) / 2.0 + nx * w), lp.Y((av + bv) / 2.0 + nz * w) - 3,
                           cluster_label(c), fs=9, anchor="middle", fill="var(--take)"))
        for sg in gd.get("singles", []):
            u, v = sg["uv"]
            if not inwin([u, v], [u, v]): continue
            if sg.get("crown"):
                o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="var(--take)" opacity="0.18" '
                         'stroke="var(--take)" stroke-width="0.7" stroke-dasharray="3 3"/>'
                         % (lp.X(u), lp.Y(v), lp.L(sg["crown"] / 2.0 / d["const"]["ken"])))
            o.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--take)"/>' % (lp.X(u), lp.Y(v)))
            lab = sg["name"] + (" %.1fm" % sg["h"] if sg.get("h") else "")
            o.append(T(lp.X(u) + 4, lp.Y(v) - 4, lab, fs=9, fill="var(--take)"))
        # 低木を撒く面(⭐ 帯の輪郭とは別の面なので図に出す)。
        # ⚠ 2026-09-06 検図5巡目 中5 — ここには `shrubBand` を読む死にコードが並んでいた
        #    (その欄は json から消えている)。**撒く面は `shrub_ok` が唯一の正典**。
        _sb = shrub_box(gd)
        if _sb and inwin(_sb[0], _sb[2]):
            _st = (gd["shrubs"]["spacingM"] / d["const"]["ken"]) / 2.0
            for _q in poly_scan(_sb, _st):
                if shrub_ok(gd, _q):
                    o.append(lp.rect(_q[0] - _st / 2.0, _q[1] - _st / 2.0,
                                     _q[0] + _st / 2.0, _q[1] + _st / 2.0,
                                     fill="var(--niwa)", op=0.30, stroke="none"))
            o.append(PL([(lp.X(u), lp.Y(v)) for u, v in _sb], close=True, fill="none",
                        stroke="var(--take)", sw=0.6, dash="4 3"))
            o.append(T(lp.X((_sb[0][0] + _sb[2][0]) / 2.0), lp.Y(_sb[0][1]) - 4,
                       "低木を撒く面", fs=9, anchor="middle", fill="var(--take)"))
        # 玉垣(立てる区間は実線・立てない辺と開口は破線)と木戸の開口、帯の照葉低木
        _tge = tamagaki_edges(d, gd)
        for nm, a, b, fen, L, rs in _tge:
            if not inwin(a, b): continue
            if not fen:
                o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]),
                            stroke="var(--take)", sw=0.8, dash="3 3"))
                continue
            o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]),
                        stroke="var(--take)", sw=0.6, dash="2 4", op=0.7))   # 辺の通り
            for rn in rs:
                o.append(LN(lp.X(rn[0][0]), lp.Y(rn[0][1]), lp.X(rn[1][0]), lp.Y(rn[1][1]),
                            stroke="var(--hei)", sw=2.2))
        # ⭐ 銘「玉垣」— 図中に一度も出ていなかった(2026-09-06 検図4巡目 低14)
        _fe = [q for q in _tge if q[3] and inwin(q[1], q[2])]
        if _fe:
            _a, _b = _fe[0][5][0]
            o.append(T(lp.X((_a[0] + _b[0]) / 2.0), lp.Y((_a[1] + _b[1]) / 2.0) - 5, "玉垣",
                       fs=9.5, anchor="middle", fill="var(--hei)"))
        tg = gd.get("tamagaki")
        kd = (tg or {}).get("kido")
        if kd and inwin(kd["uv"], kd["uv"]):
            P = [(q[0], q[1]) for q in gd["poly"]]
            a, b = P[kd["edge"]], P[(kd["edge"] + 1) % len(P)]
            L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            ex, ey = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            hw = kd["wM"] / d["const"]["ken"] / 2.0
            ku, kv = kd["uv"]
            o.append(LN(lp.X(ku - ex * hw), lp.Y(kv - ey * hw), lp.X(ku + ex * hw), lp.Y(kv + ey * hw),
                        stroke="var(--paper)", sw=3.4))
            o.append(T(lp.X(ku), lp.Y(kv) + 11, kd["name"], fs=9, anchor="middle", fill="var(--hei)"))
        for q in island_shrubs(gd, d["const"]["ken"]):
            if not inwin(q, q): continue
            o.append('<circle cx="%.1f" cy="%.1f" r="1.5" fill="var(--take)" opacity="0.8"/>'
                     % (lp.X(q[0]), lp.Y(q[1])))
        sk = gd.get("shukei")
        if sk:
            tu, tv = sk["tree"]["uv"]
            fu, fv = sk["from"]
            if inwin([tu, tv], [fu, fv]):
                o.append(LN(lp.X(fu), lp.Y(fv), lp.X(tu), lp.Y(tv),
                            stroke="var(--shu)", sw=0.8, dash="10 4", op=0.7))
                o.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="none" stroke="var(--shu)" '
                         'stroke-width="1.6"/>' % (lp.X(tu), lp.Y(tv)))
                o.append(T(lp.X(tu), lp.Y(tv) + 12, "★主景の木 丈%.0fm以上" % sk["tree"]["hMin"],
                           fs=9, anchor="middle", fill="var(--shu)"))
    return o


def draw_sando_side(d, lp, inwin):
    """参道沿い ── 柵・林縁の帯・高木の縁の線。"""
    rs = d["sando"].get("roadside")
    if not rs: return []
    o = []
    w = rs["west"]
    r0 = edge_offset(d, rs["takagiEdgeLine"]["fromEdge"], w["rinenKen"][0])
    r1 = edge_offset(d, rs["takagiEdgeLine"]["fromEdge"], w["rinenKen"][1])
    ring = [r0[0], r0[1], r1[1], r1[0]]
    o.append(PL([(lp.X(u), lp.Y(v)) for u, v in ring], fill="var(--niwa)", op=0.55,
                stroke="var(--take)", sw=0.6, close=True))
    o.append(T(lp.X((r1[0][0] + r1[1][0]) / 2.0), lp.Y((r1[0][1] + r1[1][1]) / 2.0), "林縁",
               fs=9, anchor="middle", fill="var(--take)"))
    tl = rs["takagiEdgeLine"]
    (au, av), (bu, bv) = [(q[0], q[1]) for q in tl["uv"]]
    o.append(LN(lp.X(au), lp.Y(av), lp.X(bu), lp.Y(bv), stroke="var(--take)", sw=1.2, dash="8 3"))
    o.append(T(lp.X(bu) + 4, lp.Y(bv) + 10, "高木の縁の線", fs=9, fill="var(--take)"))
    for r in d["runs"]:
        if r["kind"] != "柵" or not r.get("fromEdge"): continue
        a, b = r["a"], r["b"]
        o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]),
                    stroke="var(--hei)", sw=1.6, dash="2 2"))
        o.append(T(lp.X((a[0] + b[0]) / 2.0) - 4, lp.Y((a[1] + b[1]) / 2.0), r["name"],
                   fs=9, anchor="end", fill="var(--hei)"))
    return o


def draw_fumiishi(d, lp, inwin):
    """踏石(門の敷居前・石段の頭・鳥居の足元)。"""
    o = []
    for nm, u0, v0, u1, v1 in fumiishi_rects(d):
        if not inwin([u0, v0], [u1, v1]): continue
        o.append(lp.rect(u0, v0, u1, v1, fill="url(#pi%d)" % _SVN[0],
                         stroke="var(--ishi)", sw=0.9))
        o.append(T(lp.X((u0 + u1) / 2.0), lp.Y(v0) + 10, "踏石", fs=8.5,
                   anchor="middle", fill="var(--ishi)"))
    return o


def draw_ido(d, lp, inwin):
    """井戸屋形 ── 石敷・軒先(破線)・柱4本・井桁・浸透枡。⛔ 矩形は `ido_rects` の従属値。"""
    R = ido_rects(d)
    if not R: return []
    u0, v0, u1, v1 = R["石敷"]
    if not inwin([u0, v0], [u1, v1]): return []
    o = [lp.rect(u0, v0, u1, v1, fill="var(--dan)", stroke="var(--ishi)", sw=1.1, op=0.95)]
    n0, m0, n1, m1 = R["軒先"]
    o.append(lp.rect(n0, m0, n1, m1, fill="none", stroke="var(--ink)", sw=1.0, dash="6 3"))
    g0, h0, g1, h1 = R["井桁"]
    o.append(lp.rect(g0, h0, g1, h1, fill="none", stroke="var(--ink)", sw=1.4))
    p0, q0, p1, q1 = R["浸透枡"]
    o.append(lp.rect(p0, q0, p1, q1, fill="none", stroke="var(--ishi)", sw=0.8, dash="3 2"))
    for u, v in R["柱"]:
        o.append('<circle cx="%.1f" cy="%.1f" r="2.2" fill="var(--ink)"/>' % (lp.X(u), lp.Y(v)))
    o.append(T(lp.X((u0 + u1) / 2.0), lp.Y(v1) - 5, "井戸屋形", fs=9.5,
               anchor="middle", fill="var(--ink)"))
    return o


def draw_edge_understory(d, lp):
    """平場の縁の下層(低木の帯)。**オフセット線から内側 insetKen** の帯を二本の細線で示す。"""
    pl = d.get("planting", {}).get("edgeUnderstory")
    if not pl: return []
    e = d["planting"]["clearance"]["keidai"]["terraceEdge"]
    a = offset_poly_in(d["terraces"][0]["uv"], e)
    b = offset_poly_in(d["terraces"][0]["uv"], e + pl["insetKen"])
    o = []
    for q in (a, b):
        o.append(PL([(lp.X(u), lp.Y(v)) for u, v in q], stroke="var(--take)", sw=0.6,
                    dash="2 4", op=0.9, close=True))
    return o


# ================================================================ 植栽の幾何(2026-09-06)
# ⛔ 数値の正典は json(設計値)と docs/asset-index.tsv(部材の実寸・三角数)。
#    ここには**式と作図と検査だけ**を置き、寸法も本数も書かない(CLAUDE.md 規則4)。
_AIDX = {}


def asset_index():
    """`docs/asset-index.tsv` を読む。**樹の実寸(幅×丈×奥行)・三角数の正典**。

    ⚠ 指図(json)には写さない — 部材を差し替えたら目録が変わり、写した値だけが古く残る。
    ⚠ **fbx も読む**(自作の木は prefab を持たず `EdoAssets.Own.*` が fbx を直に指す)。
    """
    if _AIDX: return _AIDX
    with open(os.path.join(ROOT, "docs/asset-index.tsv"), encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("#"): continue
            c = ln.rstrip("\n").split("\t")
            if len(c) < 12 or c[0] == "path" or c[3] not in ("prefab", "fbx"): continue
            if c[3] == "fbx" and c[1] in _AIDX: continue
            try:
                rec = {"sx": float(c[4]), "sy": float(c[5]), "sz": float(c[6]), "tris": int(c[9])}
            except ValueError:
                continue
            if c[3] == "prefab" or c[1] not in _AIDX: _AIDX[c[1]] = rec
    return _AIDX


def part_geom(pt):
    """部材1点の素の見え寸 (樹冠径 m, 丈 m, 三角数)。目録に無ければ None。"""
    rec = asset_index().get(pt.get("prefab"))
    if rec is None: return None
    return (max(rec["sx"], rec["sz"]), rec["sy"], rec["tris"])


def crown_of(d, kind, prefab, h):
    """据えたあとの樹冠径[m]。目録に無ければ None(=**測れていない**。合格ではない)。

    ⭐ 2026-09-07 庭方3巡目 裁き2 — **中木は倍率でなく樹形の規約で決まる**。
    `scaleRule[kind].crownPerH`(樹冠 ÷ 丈)があればそこから引き、⛔ 個体の倍率も
    部材の素の樹冠も見ない(**部材を差し替えても追随する**のがこの形の狙い)。
    """
    rule = d["planting"]["scaleRule"].get(kind) or {}
    cph = rule.get("crownPerH")
    if cph is not None:
        if not h: return None
        return (cph * h, cph * h)
    g0 = part_geom({"prefab": prefab})
    if g0 is None: return None
    xz = rule.get("scaleXZ") or [1.0, 1.0]
    return (g0[0] * xz[0], g0[0] * xz[1])


def crown_scale_xz(d, kind, prefab, h):
    """`crownPerH` から出る **`scaleXZ` の従属値**。⛔ json に数を置かない(規則4)。

    実装(棟梁)が使うのはこの倍率で、⛔ **指図はこれを設計値として持たない** —
    部材の素の樹冠が変われば倍率も変わる(2026-09-07 裁き2)。
    """
    rule = d["planting"]["scaleRule"].get(kind) or {}
    cph = rule.get("crownPerH")
    g0 = part_geom({"prefab": prefab})
    if cph is None or g0 is None or not h or g0[0] <= 0: return None
    return cph * h / g0[0]


# ---------------------------------------------------------------- 退避(木を植えない所)
def _pt_seg(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz)


def _shape_rect(u0, v0, u1, v1, nm):
    return ("rect", min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1), nm,
            (min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1)))


def _shape_seg(a, b, r, nm):
    return ("seg", (a[0], a[1]), (b[0], b[1]), r, nm,
            (min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r))


def _shape_band(a, b, r, nm):
    """**線分の区間だけ**の帯(端に半円のキャップを付けない)。

    ⭐ 2026-09-06c 裁定3(庭方)— 石段の退避はこれで当てる。退避の趣旨は「坂の**両側**を空ける」
    (=法線方向)であって、坂の端から先へ張り出すことではない。キャップを付けると男坂の上端が
    楼門を・下端が仁王門を呑む(構造物を2つ食う退避は形が誤っている徴候)。
    ⛔ 面の総当たり(`_ovl_shapes` の石段)も端に丸みを付けない矩形なので、**形はこれで揃う**。
    """
    return ("band", (a[0], a[1]), (b[0], b[1]), r, nm,
            (min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r))


def _pt_line_t(p, a, b):
    """点から**直線**への距離と、線分上の助変数 t(クランプしない)。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    if L2 < 1e-12: return math.hypot(p[0] - a[0], p[1] - a[1]), 0.0
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz), t


def avoid_shapes(d, g, scope):
    """**退避の宣言から障害物の buffer を組み立てる。**⛔ ここに数を書かない — 宣言が正典。

    scope="keidai" … 境内の立木3区に効く(`planting.clearance.keidai`)
    scope="zentei" … 前庭の面(帯・供待・点景)に効く(`planting.clearance.zentei`)
    scope="obi4"   … 社叢 帯4 に効く(`slopeBands[3].avoid`)

    ⚠ **2026-09-06 に zentei を実装した。**宣言はあったのに表へ刷るだけで、
    どの面にも効いていなかった(結線の欠落・規則19)。
    """
    ken = d["const"]["ken"]
    out = []
    if scope == "keidai":
        ck = d["planting"]["clearance"]["keidai"]
        p = ck["do"]
        for m in d["munes"]:
            if m["yaku"] == "接続": continue
            out.append(_shape_rect(m["u0"] - p, m["v0"] - p,
                                   m["u0"] + m["du"] + p, m["v0"] + m["dv"] + p, "棟:" + m["name"]))
        p = ck["sukibeiKairo"]
        for r in d["runs"]:
            if r["kind"] not in ("透塀", "回廊"): continue
            out.append(_shape_seg(r["a"], r["b"], p + r.get("bari", 0) / 2.0,
                                  r["kind"] + ":" + r["name"]))
        for gd in d["gardens"]:
            if gd["name"] == "白洲":
                out.append(_shape_rect(gd["u0"], gd["v0"], gd["u1"],
                                       ck["shirasuNorthFromV"] + ck["shirasuNorthKen"], "白洲(+北の退がり)"))
            elif gd["name"] == "中庭":
                out.append(_shape_rect(gd["u0"], gd["v0"], gd["u1"], gd["v1"], "中庭"))
        for rt in d.get("routes", []):
            rr = rt["w"] / 2.0 / ken + ck["routeHalfPlus"]
            pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
            for i in range(len(pts) - 1):
                out.append(_shape_seg(pts[i], pts[i + 1], rr, "動線:" + rt["name"]))
        for k in d["kaidans"]:
            rr = kaidan_wken(d, k) / 2.0 + ck["kaidanHalfPlus"]
            pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
            for i in range(len(pts) - 1):
                out.append(_shape_band(pts[i], pts[i + 1], rr, "石段:" + k["name"]))
        return out
    if scope == "zentei":
        cz = d["planting"]["clearance"]["zentei"]
        for rt in d.get("routes", []):
            # ⭐ 前庭の中は路面幅を読み替える(`wByTerrace`・庭方 2026-09-06b)
            rr = route_w(d, rt, "Zentei") / 2.0 / ken + cz["routeHalfPlus"]
            pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
            for i in range(len(pts) - 1):
                out.append(_shape_seg(pts[i], pts[i + 1], rr, "動線:" + rt["name"]))
        for k in d["kaidans"]:
            # ⭐ **端にキャップを付けない**(2026-09-06c 裁定3・庭方)— 坂の側方だけを空ける
            rr = kaidan_wken(d, k) / 2.0 + cz["kaidanHalfPlus"]
            pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
            for i in range(len(pts) - 1):
                out.append(_shape_band(pts[i], pts[i + 1], rr, "石段:" + k["name"]))
        p = cz["gate"]
        for gt in d["gates"]:
            hu, hv = gt["plan"]["du"] / 2.0, gt["plan"]["dv"] / 2.0
            out.append(_shape_rect(gt["u"] - hu - p, gt["v"] - hv - p,
                                   gt["u"] + hu + p, gt["v"] + hv + p, "門:" + gt["name"]))
        zp = terrace_poly_uv(d["terraces"][1])
        # ⭐ **西の辺だけ犬走りで受ける**(2026-09-06c 裁定2・庭方)— 帯の西縁を腰石垣 `TW_Zentei_W`
        #    の天端まで出したので、`terraceEdge`(縁の退避)ではなく `inuBashiriM` が当たる。
        #    西の辺 = **u が最小の南北の辺**として同定する(⛔ 辺の番号を json に書かない)
        uw = min(q[0] for q in zp)
        inu = cz.get("inuBashiriM")
        for i in range(len(zp)):
            a, b = zp[i], zp[(i + 1) % len(zp)]
            west = abs(a[0] - uw) < 1e-9 and abs(b[0] - uw) < 1e-9
            r = (inu / ken) if (west and inu is not None) else cz["terraceEdge"]
            out.append(_shape_seg(a, b, r, "前庭の縁" + ("(西=犬走り)" if west and inu is not None else "")))
        # ⭐ **2026-09-06 検図5巡目 中5 で足した実体** — 井戸屋形の石敷・玉垣・縁台・空地(供待)が
        #    一つも入っておらず、前庭の合法域が実際より広く出ていた。
        #    ⛔ 退避の余白は宣言が無いので**実体の輪郭そのもの**(余白 0)で当てる。
        _ir = ido_rects(d)
        if _ir:
            out.append(_shape_rect(*(list(_ir["石敷"]) + ["井戸:石敷"])))
        for gd in d["gardens"]:
            own = gd.get("tamagaki")
            for nm, a, b, fence, _ln, rs in tamagaki_edges(d, gd):
                if not fence: continue
                for rn in rs:
                    out.append(_shape_seg(rn[0], rn[1], own["postDiaM"] / 2.0 / ken, "玉垣:" + nm))
            if gd.get("noPlant") and gd.get("poly"):
                us = [q[0] for q in gd["poly"]]; vs = [q[1] for q in gd["poly"]]
                out.append(_shape_rect(min(us), min(vs), max(us), max(vs), "空地:" + gd["name"].split("(")[0]))
        for nm, Q in prop_rects(d):
            us = [q[0] for q in Q]; vs = [q[1] for q in Q]
            out.append(_shape_rect(min(us), min(vs), max(us), max(vs), "点景:" + nm))
        return out
    av = [b["avoid"] for b in d["slopeBands"] if b.get("avoid")][0]
    ot = [k for k in d["kaidans"] if k["name"] == "男坂"][0]
    out.append(_shape_seg(ot["a"], ot["b"], av["otokozakaFromAxis"], "男坂"))
    on = [k for k in d["kaidans"] if k["name"].startswith("女坂")][0]
    rr = kaidan_wken(d, on) / 2.0 + av["onnazakaFromShoulder"]
    op = [tuple(q) for q in on["pts"]]
    for i in range(len(op) - 1):
        out.append(_shape_seg(op[i], op[i + 1], rr, "女坂"))
    sp = [(g.U(x), g.V(z)) for x, z in d["sando"]["pts"]]
    for i in range(len(sp) - 1):
        out.append(_shape_seg(sp[i], sp[i + 1], av["sandoFromAxis"], "参道"))
    zp = terrace_poly_uv(d["terraces"][1])
    # ⭐ **東の辺だけ退避を緩める**(庭方 中-2 2026-09-06b)。東の辺 = **u が最大の南北の辺**として
    #    同定する(⛔ 辺の番号を json に書かない — 前庭の輪郭を直した日に取り残される)
    ue = max(q[0] for q in zp)
    for i in range(len(zp)):
        a, b = zp[i], zp[(i + 1) % len(zp)]
        east = abs(a[0] - ue) < 1e-9 and abs(b[0] - ue) < 1e-9
        r = av.get("zenteiFromEdgeEast", av["zenteiFromEdge"]) if east else av["zenteiFromEdge"]
        out.append(_shape_seg(a, b, r, "前庭の縁" + ("(東)" if east else "")))
    return out


def shape_hit(p, shapes):
    """点が退避に載っていれば障害物の名、載っていなければ None。"""
    for sh in shapes:
        bb = sh[-1]                                  # ⚠ 末尾が bbox・その前が名(rect と seg で長さが違う)
        if not (bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]): continue
        if sh[0] == "rect":
            if sh[1] < p[0] < sh[3] and sh[2] < p[1] < sh[4]: return sh[-2]
        elif sh[0] == "band":
            # ⭐ 端に半円を付けない — 線分の**区間の中**だけ、法線方向に r
            dd, t = _pt_line_t(p, sh[1], sh[2])
            if 0.0 <= t <= 1.0 and dd < sh[3]: return sh[-2]
        elif _pt_seg(p, sh[1], sh[2]) < sh[3]:
            return sh[-2]
    return None


def poly_scan(P, step):
    """多角形の中のセルの中心を走査する(セルは step[間] 角)。"""
    us = [q[0] for q in P]; vs = [q[1] for q in P]
    u = min(us) + step / 2.0
    while u < max(us):
        v = min(vs) + step / 2.0
        while v < max(vs):
            if in_poly((u, v), P): yield (u, v)
            v += step
        u += step


def cell_tsubo(d, step):
    return step * step * d["const"]["ken"] ** 2 / TSUBO


# ---------------------------------------------------------------- 社叢の帯(面と本数)
_BANDS = {}


def band_scan(d, g):
    """**帯1〜3の面を走査する**(`planting.bandDef` の規約)。⛔ 面積も本数も定数で持たない。

    法肩 = 平場の天端、法尻 = 社地の境(東〜北東は帯4の西縁)。各セルで
    t = (天端 − 現地形h) / (天端 − 最寄りの法尻のh) を出し、帯の `from`/`to` で切る。
    戻り値: ({帯番号: [(u,v)…]}, 未分類のセル数)
    """
    if _BANDS: return _BANDS["cells"], _BANDS["skip"]
    bd = d["planting"]["bandDef"]
    step = bd["stepKen"]
    top = d["terraces"][0]["y"]
    soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    keidai = terrace_poly_uv(d["terraces"][0])
    zentei = terrace_poly_uv(d["terraces"][1])
    obi4 = [(q[0], q[1]) for q in d["slopeBands"][3]["uv"]]

    def ring(P): return [(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    toe = ring(soch) + ring(obi4)
    cells = {1: [], 2: [], 3: []}
    skip = 0
    for p in poly_scan(soch, step):
        if in_poly(p, keidai) or in_poly(p, zentei) or in_poly(p, obi4): continue
        x, z = g.W(p[0], p[1])
        h = dem_h(x, z)
        if h is None: skip += 1; continue
        best, bq = 1e9, None
        for a, b in toe:
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
            q = (a[0] + dx * t, a[1] + dz * t)
            dd = math.hypot(p[0] - q[0], p[1] - q[1])
            if dd < best: best, bq = dd, q
        ht = dem_h(*g.W(bq[0], bq[1]))
        if ht is None or top - ht <= 0.5: skip += 1; continue
        t = (top - h) / (top - ht)
        for b in d["slopeBands"][:3]:
            if b["from"] <= t < b["to"] or (b["to"] >= 1.0 and t >= b["from"]):
                cells[b["band"]].append(p); break
        else:
            skip += 1
    _BANDS["cells"], _BANDS["skip"] = cells, skip
    return cells, skip


def band_density(b):
    """採用密度[本/100m²]。`takagiAdopted` があればそれ、無ければ `takagiPer100` の中央。"""
    if b.get("takagiAdopted"): return b["takagiAdopted"]
    r = b.get("takagiPer100") or [0, 0]
    return (r[0] + r[1]) / 2.0


def view_cluster_cut(d, g):
    """視線が決める塊(`planting.viewClusters`)の本数を、箱の中心が落ちる帯から差し引く。"""
    cells, _ = band_scan(d, g)
    own = {}
    for k, ps in cells.items():
        for p in ps: own[(round(p[0] * 2), round(p[1] * 2))] = k
    cut = {1: 0, 2: 0, 3: 0}
    for c in d["planting"].get("viewClusters", []):
        bx = cluster_boxes(c)
        per = cluster_n(c) / max(1, len(bx))
        for u0, v0, u1, v1 in bx:
            cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
            k = own.get((round(cu * 2), round(cv * 2)))
            if k is None:
                k = min(cut, key=lambda q: -len(cells[q]))
            cut[k] += per
    return cut


_BSTAT = []


def band_stats(d, g):
    """帯1〜4 の 面[坪]・退避[坪]・有効面[坪]・採用密度・高木/落葉/中木/低木の本数。"""
    if _BSTAT: return _BSTAT
    ken = d["const"]["ken"]
    cells, skip = band_scan(d, g)
    ct = cell_tsubo(d, d["planting"]["bandDef"]["stepKen"])
    cut = view_cluster_cut(d, g)
    for b in d["slopeBands"]:
        if b.get("uv"):
            P = [(q[0], q[1]) for q in b["uv"]]
            sh = avoid_shapes(d, g, "obi4")
            st = 0.25
            c2 = cell_tsubo(d, st)
            tot = av = rn = 0
            soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
            rin = b.get("rinen") or {}
            for p in poly_scan(P, st):
                tot += 1
                if shape_hit(p, sh): av += 1; continue
                if rin:
                    dd = min(_pt_seg(p, soch[i], soch[(i + 1) % len(soch)]) for i in range(len(soch)))
                    if rin["fromKen"] <= dd <= rin["toKen"]: rn += 1
            # ⭐ 帯の中に**位置を決めて据える一本立ち**があれば、密度から出した本数から差し引く
            #    (視線が決める塊と同じ扱い。2026-09-06 庭方 A-3b の門被りの松)
            row = {"b": b, "tsubo": tot * c2, "avoid": av * c2, "rinen": rn * c2,
                   "usable": (tot - av) * c2, "cut": float(len(b.get("singles", [])))}
        else:
            n = len(cells[b["band"]])
            row = {"b": b, "tsubo": n * ct, "avoid": 0.0, "rinen": 0.0,
                   "usable": n * ct, "cut": cut.get(b["band"], 0.0)}
        row["dens"] = band_density(b)
        row["takagi"] = row["usable"] * TSUBO * row["dens"] / 100.0 - row["cut"]
        row["rakuyo"] = row["takagi"] * (b.get("rakuyoRatio") or 0.0)
        for k, key in (("chuboku", "chubokuPer100"), ("teiboku", "teibokuPer100")):
            r = b.get(key) or [0, 0]
            row[k] = row["usable"] * TSUBO * (r[0] + r[1]) / 2.0 / 100.0
        _BSTAT.append(row)
    _BSTAT.append({"skip": skip * ct})
    return _BSTAT


def band_components(d, g):
    """帯1〜3の**連結成分**の坪数(大きい順)。0.5 間のセルの4近傍で繋ぐ。"""
    cells, _ = band_scan(d, g)
    step = d["planting"]["bandDef"]["stepKen"]
    ct = cell_tsubo(d, step)
    out = {}
    for b, ps in cells.items():
        S = set((int(round(u / step)), int(round(v / step))) for u, v in ps)
        seen, comps = set(), []
        for c in S:
            if c in seen: continue
            stack, n = [c], 0
            seen.add(c)
            while stack:
                x, y = stack.pop(); n += 1
                for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if q in S and q not in seen: seen.add(q); stack.append(q)
            comps.append(n * ct)
        out[b] = sorted(comps, reverse=True)
    return out


def band_invariants(d, g):
    """**帯の不変条件**(`bandDef.invariants`)。⛔ 面積・本数そのものは合否に使わない(④)。

    ⭐ **2026-09-06 に受入検査(庭方の実測との ±5%)を置き換えた** — 庭方が自らの実測を撤回し、
    「指図方の定義が正典」「合否は面積でなく不変条件で見る」と回答したため(B-1)。
    戻り値 [(番号, 条項, 現況, 判定, 組む条件か)]。
    """
    iv = d["planting"]["bandDef"]["invariants"]
    st = band_stats(d, g)
    ts = dict((r["b"]["band"], r["tsubo"]) for r in st if "b" in r)
    kei = poly_area([g.W(u, v) for u, v in d["terraces"][0]["uv"]]) / TSUBO
    zen = poly_area(terrace_poly(d["terraces"][1], g)) / TSUBO
    soc = poly_area(d["polygon"]) / TSUBO
    tot = sum(ts.values()) + kei + zen
    dv = tot / soc * 100.0 - 100.0
    out = [("①", "帯1+帯2+帯3+帯4+平場+前庭 = 社地の面積(±%g%%)" % iv["sumTolPct"],
            "%s 坪 ／ 社地 %s 坪 ／ 差 %+.2f%%"
            % (format(int(round(tot)), ","), format(int(round(soc)), ","), dv),
            abs(dv) <= iv["sumTolPct"], True)]
    ok2 = ts.get(1, 0) < ts.get(2, 0) < ts.get(3, 0)
    out.append(("②", "帯1 < 帯2 < 帯3(下るほど広い)",
                " < ".join("帯%d %s 坪" % (b, format(int(round(ts.get(b, 0))), ",")) for b in (1, 2, 3)),
                ok2, True))
    # ③ ⭐ 2026-09-06 検図4巡目 低11 — 「最小の成分が5%以上」は 0.5間格子が縁に作る破片に必ず
    #    引っ掛かって組む条件にできなかった。測りたいのは『帯が割れていないこと』なので**最大の成分**で見る。
    comps = band_components(d, g)
    worst, wb = None, None
    for b, cs in sorted(comps.items()):
        if not cs: continue
        r = max(cs) / sum(cs) * 100.0
        if worst is None or r < worst: worst, wb = r, b
    out.append(("③", "各帯の最大の連結成分が帯の全体の %g%% 以上(帯が割れていない)" % iv["maxCompPct"],
                "最も低いのは 帯%s の %.2f%%(成分の数 %s)"
                % (wb, worst or 0.0, "／".join("帯%d=%d" % (b, len(comps[b])) for b in sorted(comps))),
                (worst or 0.0) >= iv["maxCompPct"], True))
    return out


def band_invariant_check(d, g):
    """⛔ 組む条件にした不変条件が破れていたら組ませない(2026-09-06 から①②③の三つとも)。"""
    return ["社叢の帯の不変条件 %s が破れている — %s(%s)" % (i, cl, got)
            for i, cl, got, ok, gate in band_invariants(d, g) if gate and not ok]


# ---------------------------------------------------------------- 境内の立木3区
_MIXRE = re.compile(r"(松|欅|椋|榎)\s*(\d+)")
_MIXSP = {"欅": "ケヤキ", "椋": "ムクノキ", "榎": "エノキ"}


def cluster_mix(c):
    """塊の `mix`(「松4・欅1」)を [(種, 本数)] へ。⛔ 本数を二重に持たない。"""
    return [(k, int(n)) for k, n in _MIXRE.findall(c.get("mix") or "")]


def zone_h(d, gd):
    """区の松・落葉高木の丈[m](`hBand` の帯から引く)。"""
    b = [q for q in d["slopeBands"] if q["band"] == gd.get("hBand")]
    if not b: return None, None
    return b[0].get("matsuH"), b[0].get("rakuyoH")


def cluster_parts(d, gd, c):
    """塊の部材 — `mix` の割り前 × `planting.parts` の palette。(種, 部材, 本数, 丈, 樹冠) の列。"""
    pal = d["planting"]["parts"]
    mH, rH = zone_h(d, gd)
    out = []
    for kind, n in cluster_mix(c):
        if kind == "松":
            src, h, sk = pal["松"], mH, "matsu"
        else:
            src = [q for q in pal["落葉"] if q.get("species") == _MIXSP[kind]]
            h, sk = rH, "rakuyo"
        if not src: continue
        wt = sum(q.get("w", 1) for q in src)
        rest = n
        for i, pt in enumerate(src):
            k = n - rest if i == len(src) - 1 else int(round(n * pt.get("w", 1) / float(wt)))
            k = min(k, rest) if i < len(src) - 1 else rest
            rest -= k
            if k <= 0: continue
            out.append((kind, pt, k, h, crown_of(d, sk, pt["prefab"], h)))
    return out


def overhang_range(d):
    """参道の林縁が道へ張り出す量[m] — **樹冠からの従属値**。(lo, hi, 測れた数, 引けない数)。

    ⭐ 2026-09-07 庭方3巡目 中2 — 旧式は **正の値だけ拾って** 一つも無ければ None を返し、
    図はそれを「部材が目録に無く測れない」と刷っていた。⛔ **測れていて負だった**
    (高木の縁の線の `insetKen` に樹冠の半径が届かず、一本も道の上へ出ない)。
    ⛔ 符号を捨てない — 負は「張り出さない」という**測れた答え**であって、欠測ではない。
    """
    tl = (d["sando"].get("roadside") or {}).get("takagiEdgeLine") or {}
    ins = tl.get("insetKen")
    if ins is None: return None
    b4 = d["slopeBands"][3]
    lo = hi = None
    nmeas = nmiss = 0
    for kind, key in (("matsu", "松"), ("rakuyo", "落葉")):
        for pt in d["planting"]["parts"][key]:
            cr = crown_of(d, kind, pt["prefab"], (b4.get("matsuH") or [0, 0])[1])
            if cr is None:
                nmiss += 1
                continue
            nmeas += 1
            for r in cr:
                o = r / 2.0 - ins * d["const"]["ken"]
                lo = o if lo is None else min(lo, o)
                hi = o if hi is None else max(hi, o)
    if lo is None: return (None, None, 0, nmiss)
    return (lo, hi, nmeas, nmiss)


# ---------------------------------------------------------------- 見所と主景
def shukei_rows(d, g):
    """★主景 — 楼門の眼から見た 木・棟の仰角[°]。⛔ 数を文章に写さない。"""
    ken = d["const"]["ken"]
    gr = d["terraces"][0]["y"]
    out = []
    for gd in d["gardens"]:
        sk = gd.get("shukei")
        if not sk: continue
        fu, fv = sk["from"]; eye = sk["eyeY"]
        tu, tv = sk["tree"]["uv"]
        L = math.hypot(tu - fu, tv - fv) * ken
        top = gr + sk["tree"]["hMin"]
        out.append(("★主景の木(%s 丈%.0fm)" % (sk["tree"]["kind"], sk["tree"]["hMin"]),
                    L, top, math.degrees(math.atan2(top - eye, L))))
        for nm in sk.get("munes", []):
            m = [q for q in d["munes"] if q["name"] == nm]
            if not m or m[0].get("h") is None:
                out.append((nm + " の棟", None, None, None)); continue
            m = m[0]
            cu, cv = m["u0"] + m["du"] / 2.0, m["v0"] + m["dv"] / 2.0
            L2 = math.hypot(cu - fu, cv - fv) * ken
            t2 = gr + m["h"]
            out.append((nm + " の棟(丈 %.1f m)" % m["h"], L2, t2,
                        math.degrees(math.atan2(t2 - eye, L2))))
    return out


def viewpoint_rows(d, g):
    """見所 V1〜V3 — 眼高(従属)と、`shows` に挙げた塊の見込み角[°]。"""
    ken = d["const"]["ken"]
    rows = []
    for vp in d.get("viewpoints", []):
        u, v = vp["uv"]
        eye = vp.get("eye")
        src = "設計値"
        if eye is None:
            # ⭐ **設計地盤(平場があれば平場・無ければ現地形)+ 座面高 + eyeOver**
            #   (2026-09-06 検図5巡目 低15 — 旧版は現地形しか見ず、V2/V-Z1/V-Z3 は
            #    `eye` に `terraces[1].y + eyeOver` を書き写して二重に持っていた)
            h = design_y(d, g, *g.W(u, v))
            base = "設計地盤" if h is not None else "現地形"
            if h is None: h = dem_h(*g.W(u, v))
            seat = 0.0
            if vp.get("seatOn"):
                _k, _, _nm = vp["seatOn"].partition(":")
                for _p in d.get(_k, []):
                    if _p.get("name") == _nm: seat = (_p.get("plan") or {}).get("seatH", 0.0)
            eye = (h or 0.0) + seat + vp.get("eyeOver", 0.0)
            src = ("%s %.2f m%s + %.2f m"
                   % (base, h or 0.0,
                      " + 座面 %.2f m" % seat if seat else "", vp.get("eyeOver", 0.0)))
        shows = []
        for nm in vp.get("shows", []):
            for holder in d["gardens"] + d["slopeBands"] + [d["planting"]]:
                for c in holder.get("clusters", []) + holder.get("viewClusters", []):
                    if c["name"] != nm: continue
                    bx = cluster_boxes(c)
                    for j, (u0, v0, u1, v1) in enumerate(bx):
                        az = [math.degrees(math.atan2(cv - v, -(cu - u)))
                              for cu, cv in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
                        shows.append((nm + ("" if len(bx) == 1 else "(其%d)" % (j + 1)),
                                      min(az), max(az), max(az) - min(az)))
        rows.append((vp, eye, src, shows))
    return rows


# ---------------------------------------------------------------- 三角数の見積り
def plant_budget(d, g):
    """置く物の総数と三角数。**在庫の木は1本1万〜2万三角**なので目に見えるコスト。"""
    pal = d["planting"]["parts"]
    st = band_stats(d, g)
    n = {"松": 0.0, "落葉": 0.0, "中木": 0.0, "低木": 0.0}
    for r in st:
        if "b" not in r: continue
        n["落葉"] += r["rakuyo"]; n["松"] += r["takagi"] - r["rakuyo"]
        n["中木"] += r["chuboku"]; n["低木"] += r["teiboku"]
    for gd in d["gardens"]:
        for c in gd.get("clusters", []):
            # ⚠ 帯の塊(帯4)はここで数えない — 帯の本数は密度から出ており、塊はその内訳である
            for kind, _n in cluster_mix(c):
                n["松" if kind == "松" else "落葉"] += _n
    # ⭐ **一本立ちは別に数える**(2026-09-07 中4)— 撒く物は Terrain Tree、
    #    一本立ちは意匠上位置を決めた物なので GameObject。数を混ぜると据え方が読めない。
    sn = {"松": 0.0, "落葉": 0.0, "中木": 0.0, "低木": 0.0}
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            lay = sg.get("layer") or ("松" if "マツ" in (sg.get("kind") or "") else "落葉")
            sn[lay if lay in sn else "落葉"] += 1
        if gd.get("shrubs"): n["低木"] += len(island_shrubs(gd, d["const"]["ken"]))
    for c in d["planting"].get("viewClusters", []):
        n["松"] += cluster_n(c)
    # ★主景の木は塊(西A)の内訳なので本数には足さない(⛔ 二重に数えない)。
    #   据え方は一本立ちと同じ GameObject で、名簿は `viewClusters` と `shukei` が持つ。
    place = d["planting"]["plantRule"].get("placement") or {}
    rows = []
    for key in ("松", "落葉", "中木", "低木"):
        tri = [part_geom(pt) for pt in pal[key]]
        wt = sum(pt.get("w", 1) for pt in pal[key])
        avg = None
        if all(t is not None for t in tri) and tri:
            avg = sum(t[2] * pal[key][i].get("w", 1) for i, t in enumerate(tri)) / float(wt)
        rows.append((key, int(round(n[key])), int(round(sn[key])), avg,
                     place.get(key), place.get("singles")))
    return rows


# 犬走りの許容[m](**検査の物差しであって設計値ではない**ので json に置かない)。
# ⭐ 2026-09-07 検図7巡目 低4 — 門の芯を従属値にして丸めの差(0.03 mm)が消えたので、
# 旧 0.001 m から**浮動小数の丸めだけを吸う 1 μm** へ絞った。⛔ 設計の余裕として広げない。
INU_TOL_M = 1e-6

# 面の切盛の目安[m](CLAUDE.md 規則3「棟が載る所で |設計面 − 自然地形| ≤ 0.5m」)。
# **検査の物差しであって設計値ではない**ので json に置かない。⛔ これを緩めて黙らせない。
PLANE_DEV_LIM_M = 0.5


# ---------------------------------------------------------------- 検査(2026-09-06 検図の3本)
_FIGRE = re.compile(r'<div class="fig">(.*?)</div>', re.S)


def svg_tail_check(htm):
    """(a) **図版ごとに `</g></svg>` が末尾か。**⛔ `</svg>` の後に要素を足さない。

    ⚠ 2026-09-06 の検図で、参道と鳥居が `</svg>` の**後**に足されていて5面で描かれていなかった。
    目で見えない欠陥(ブラウザが黙って捨てる)なので、機械で押さえる。
    """
    bad = []
    for i, body in enumerate(_FIGRE.findall(htm), 1):
        b = body.strip()
        if not b.startswith("<svg"):
            bad.append("図版 %d が <svg で始まっていない" % i); continue
        if not b.endswith(ENDSVG):
            bad.append("図版 %d の末尾が `%s` でない(末尾 60字: %s)"
                       % (i, ENDSVG, b[-60:].replace("\n", " "))); continue
        if b.count("</svg>") != 1:
            bad.append("図版 %d に </svg> が %d 個ある" % (i, b.count("</svg>")))
        if b.index("</svg>") != len(b) - len("</svg>"):
            bad.append("図版 %d は </svg> の後に要素が残る" % i)
    return bad


def crown_rule_check(d):
    """(e) **高木・中木の枝下**が層ごとの `edaShitaMinM` 以上か。

    ⭐ 高木の退避を「幹の芯 + 枝下」で取ると決めた以上(2026-09-06 庭方 A-0)、
    枝下は**仕立ての条件**であって飾りではない — 割ると樹冠が縁台と動線に降りてくる。
    ⭐ 2026-09-06c 参考1(庭方)— **中木も同じ扱いへ移した**(`crownRule.chuboku`)。
    中木の樹冠が縁台・玉垣に掛かるのは可だが、**幹の芯が玉垣から `tamagakiFromTrunkKen` 以内**に
    来てはいけない(幹の肥大が柱を押す)。
    ⭐ 2026-09-07 裁定3(庭方)— 中木にさらに二つ。**幹の芯が腰石垣の壁面から
    `koshiIshigakiFromTrunkKen` 以内に来ない**(根が石垣を押す)/ **樹冠の外周が井戸屋形の
    石敷=軒先の外形に掛からない**(`idoNokiCrownClear`。軒高は中木の枝下では抜けない)。
    ⛔ どちらも止める。⛔ `scaleXZ` を下げて黙らせない — 位置で解く。
    """
    cr = d["planting"]["plantRule"].get("crownRule") or {}
    tk = cr.get("takagi") or {}
    ch = cr.get("chuboku") or {}
    lo = tk.get("edaShitaMinM")
    lo_ch = ch.get("edaShitaMinM")
    bad, note = [], []
    ken0 = d["const"]["ken"]
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            e = sg.get("edaShita")
            lim = lo_ch if (sg.get("layer") == "中木") else lo
            if lim is not None and e is not None and e < lim:
                bad.append("%s の枝下 %.2f m が下限 %.2f m を割る" % (sg["name"], e, lim))
            if sg.get("layer") == "中木" and e is None and lo_ch is not None:
                note.append("%s(%s)は中木だが枝下の宣言が無い — 仕立ての条件 %.2f m は"
                            "部材表『常緑中木』の行が受ける" % (sg["name"], gd["name"], lo_ch))
    # ⛔ **中木の幹の芯 → 玉垣の離れ**(2026-09-06c 参考1)。⛔ 止める — 幹が柱を押す位置には植えない
    tk_lo = ch.get("tamagakiFromTrunkKen")
    if tk_lo is not None:
        for gd in d["gardens"]:
            if not gd.get("tamagaki"): continue
            runs = [rn for _nm, _a, _b, fence, _ln, rs in tamagaki_edges(d, gd) if fence for rn in rs]
            if not runs: continue
            for sg in gd.get("singles", []):
                if sg.get("layer") != "中木": continue
                dd = min(_pt_seg(tuple(sg["uv"]), rn[0], rn[1]) for rn in runs)
                if dd < tk_lo - 1e-9:
                    bad.append("%s の幹の芯が玉垣から %.3f m(%.3f 間)— 下限 %.3f 間(%.2f m)を割る"
                               % (sg["name"], dd * ken0, dd, tk_lo, tk_lo * ken0))
    # ⛔ **中木の幹の芯 → 腰石垣の壁面**(2026-09-07 裁定3)。低木が 0.5 間で止まるのは根が
    #    石垣を押すからで、中木は丈が3倍・根鉢も倍以上なので離れも倍に取る。
    #    ⭕ 樹冠が壁面より外へ出るのは可(林縁の作法)なので**幹で測る**。
    g = G(d)
    ki_lo = ch.get("koshiIshigakiFromTrunkKen")
    if ki_lo is not None:
        uw = min(q[0] for q in terrace_poly_uv(d["terraces"][1]))
        ZP = terrace_poly(d["terraces"][1], g)
        for gd in d["gardens"]:
            for sg in gd.get("singles", []):
                if sg.get("layer") != "中木": continue
                if not in_poly(g.W(*sg["uv"]), ZP): continue
                dd = sg["uv"][0] - uw
                if dd < ki_lo - 1e-9:
                    bad.append("%s の幹の芯が腰石垣の壁面(u %.3f)から %.3f 間(%.3f m)— "
                               "下限 %.3f 間(%.2f m)を割る"
                               % (sg["name"], uw, dd, dd * ken0, ki_lo, ki_lo * ken0))
                else:
                    note.append("%s の幹の芯 → 腰石垣の壁面 %.3f 間(%.3f m／下限 %.3f 間)【算出】"
                                % (sg["name"], dd, dd * ken0, ki_lo))
    # ⛔ **中木の樹冠の外周が井戸屋形の石敷(=軒先の外形)に掛からない**(2026-09-07 裁定3)。
    #    軒高は中木の枝下では抜けないので、幹の芯の下限だけでは守れない。
    if ch.get("idoNokiCrownClear"):
        R_ = ido_rects(d)
        if R_:
            u0, v0, u1, v1 = R_["石敷"]
            C = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            for gd in d["gardens"]:
                for sg in gd.get("singles", []):
                    if sg.get("layer") != "中木": continue
                    r = single_crown(d, sg)
                    if r is None:
                        note.append("%s の樹冠が引けない(部材が目録に無い)— 軒先との離れを測れていない"
                                    % sg["name"])
                        continue
                    dd = min(_pt_seg(tuple(sg["uv"]), C[i], C[(i + 1) % 4]) for i in range(4))
                    if in_poly(tuple(sg["uv"]), C): dd = 0.0
                    if dd < r - 1e-9:
                        bad.append("%s の樹冠(半径 %.3f m)が井戸屋形の石敷=軒先の外形へ %.3f m 掛かる"
                                   % (sg["name"], r * ken0, (r - dd) * ken0))
                    else:
                        note.append("%s の樹冠の外周 → 井戸屋形の軒先の外形 %.3f m【算出】"
                                    % (sg["name"], (dd - r) * ken0))
    # ⭐ **中木の樹形の規約**【裁き2 庭方 2026-09-07】── 倍率は `crownPerH` からの従属値。
    #    ⛔ 宣言が無ければ止める(規約を消せば手値の倍率へ戻る・規則19)。
    #    ⛔ 個体が `scaleXZ` を持ったら止める(規約の上から手で押し戻す道を塞ぐ)。
    cbr = d["planting"]["scaleRule"].get("chuboku") or {}
    cph = cbr.get("crownPerH")
    if cph is None:
        bad.append("`planting.scaleRule.chuboku.crownPerH`(樹冠÷丈の規約)の宣言が無い — "
                   "宣言の無い規約は手値の倍率へ戻る(規則19)")
    if cbr.get("scaleXZ") is not None:
        bad.append("`planting.scaleRule.chuboku.scaleXZ` が復活している — "
                   "中木の樹冠は `crownPerH` からの従属値(⛔ 数で持たない)")
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            if sg.get("layer") != "中木": continue
            if sg.get("scaleXZ") is not None:
                bad.append("%s が個体の `scaleXZ` を持つ — 中木の樹冠は規約 `crownPerH` から出る"
                           "(⛔ 個体に倍率を持たせない。2026-09-07 裁き2)" % sg["name"])
            if cph is None: continue
            pf = single_prefab(d, sg)
            xz = crown_scale_xz(d, "chuboku", pf, sg.get("h"))
            note.append("%s の `scaleXZ` %s【従属 — 樹冠÷丈 %.2f × 丈 %.1f m ÷ 部材『%s』の素の樹冠】"
                        % (sg["name"], ("%.3f" % xz) if xz else "—(部材が目録に無い)",
                           cph, sg.get("h") or 0.0, pf or "—"))
    # ⚠ **仮値の樹冠**【中1 庭方 2026-09-07】── 目録に入った日に⛔で止める(自ら閉じる印)
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            if not sg.get("crownProvisional"): continue
            pf = single_prefab(d, sg)
            if pf and part_geom({"prefab": pf}) is not None:
                rl = {"松": "matsu", "落葉": "rakuyo"}.get(sg.get("layer") or "", "chuboku")
                bad.append("%s の `crown` が仮値のまま残っている — 部材『%s』は目録に入った。"
                           "`scaleRule.%s`(樹冠は部材からの従属値)へ戻し "
                           "`crownProvisional` を外す" % (sg["name"], pf, rl))
            else:
                note.append("%s の樹冠 %.2f m は**部材未計測の仮値**(部材『%s』が "
                            "`docs/asset-index.tsv` に無い)— 木陰の余裕はこの仮値の上に乗る。"
                            "⛔ 合格ではない【中1 庭方 2026-09-07】"
                            % (sg["name"], sg.get("crown") or 0.0, pf or "—"))
    return bad, note


def single_prefab(d, sg):
    """一本立ちが名指す部材の prefab 名。名指しが無ければ palette の先頭。無ければ None。"""
    key = {"松": "松", "落葉": "落葉", "中木": "中木", "低木": "低木"}.get(sg.get("layer") or "")
    if key is None: return None
    pal = d["planting"]["parts"].get(key) or []
    named = [pt for pt in pal if pt.get("api") == sg.get("part")]
    pal = named or pal
    return pal[0].get("prefab") if pal else None


def single_crown(d, sg):
    """一本立ちの**据えたあとの樹冠の半径[間]**。`crown` があればそれ、無ければ部材と倍率から。

    ⭐ 2026-09-06b — 一本立ちが**部材を名指し**(`part`)していればその一点だけを見る
    (⛔ palette の最大で代表させない)。個体の `scaleXZ` は `scaleRule` の倍率の**上に**掛ける
    (庭方が本数を減らさず樹冠を絞ると決めた回答がこれ)。
    """
    ken = d["const"]["ken"]
    if sg.get("crown"): return sg["crown"] / 2.0 / ken
    lay = sg.get("layer") or "落葉"
    key = {"松": ("松", "matsu"), "落葉": ("落葉", "rakuyo"),
           "中木": ("中木", "chuboku"), "低木": ("低木", "chuboku")}.get(lay)
    if key is None: return None
    pal = d["planting"]["parts"].get(key[0], [])
    named = [pt for pt in pal if pt.get("api") == sg.get("part")]
    best = None
    for pt in (named or pal):
        c = crown_of(d, key[1], pt["prefab"], sg.get("h"))
        if c is None: continue
        v = max(c) / 2.0 / ken
        best = v if best is None else max(best, v)
    rule0 = d["planting"]["scaleRule"].get(key[1]) or {}
    if best is not None and sg.get("scaleXZ") and rule0.get("crownPerH") is None:
        rule = rule0.get("scaleXZ") or [1.0, 1.0]
        best = best / max(rule) * max(sg["scaleXZ"])
    return best


def gate_at(d, q):
    """点 (u,v) が門の平面の中なら、その門。無ければ None。"""
    for gt in d["gates"]:
        hu, hv = gt["plan"]["du"] / 2.0, gt["plan"]["dv"] / 2.0
        if abs(q[0] - gt["u"]) <= hu and abs(q[1] - gt["v"]) <= hv: return gt
    return None


def terrace_at(d, g, q):
    """点 (u,v) が載る平場の名。どの平場にも載らなければ None。"""
    for te in d["terraces"]:
        if in_poly(g.W(q[0], q[1]), terrace_poly(te, g)): return te["name"]
    return None


def route_w(d, rt, terrace=None, at=None):
    """動線の路面幅[m]。**区間ごとの読み替え**。

    ⛔ 幅を二重に持たない — `w` は参道(公道)の幅で、前庭の中は門口から導いた別の値
    (庭方 2026-09-06b)。⭐ **門をくぐる区間は `gates[].monguchiKen` が幅を決める**
    (2026-09-06 検図5巡目 中7 — 宣言だけあって計算が無く、表参の通行帯 3.636m が
    門口 1.818m の2倍のまま両脇柱へ 0.909m ずつ乗っていた)。`at` は測る点 (u,v)。
    **門 > 段 > 素の `w`** の順で決まる。
    """
    if at is not None:
        gt = gate_at(d, at)
        if gt is not None and gt.get("monguchiKen"):
            return gt["monguchiKen"] * d["const"]["ken"]
    if terrace and (rt.get("wByTerrace") or {}).get(terrace) is not None:
        return rt["wByTerrace"][terrace]
    return rt["w"]


def planting_avoid_check(d, g):
    """(b) **植栽の多角形 ∩ 障害物 buffer = 0**、塊の箱が本数を置ける広さか、帯が社地の中か。

    ⚠ 2026-09-06 の検図で、立木3区の多角形が6棟と2動線を覆っていた(南区は面の47%)。
    ⛔ 面積だけを別に持って辻褄を合わせない — **輪郭そのもの**が植えられる面である。
    戻り値 (⛔止める, 〔記録〕)。**塊の箱が本数を置ける広さか**は〔記録〕— 箱の広さは庭方の意匠で、
    ⛔ 指図方が箱を広げて黙らせない。
    """
    bad, note = [], []
    ken = d["const"]["ken"]
    SH = {}
    st = 0.25
    ct = cell_tsubo(d, st)
    soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    pack = d["planting"]["plantRule"]["packRatio"]
    for gd in d["gardens"]:
        P = garden_poly(gd)
        if not P or not gd.get("poly"): continue
        if gd.get("noPlant"): continue            # 空地(供待)は植えない面なので退避を当てない
        # ⭐ **退避は区が名指しする宣言で当てる**(`gardens[].clearance`)。
        #    ⚠ 前庭の面に境内の退避を当てると、緩めた宣言(ユーザー裁定)が効かない
        sc = gd.get("clearance") or "keidai"
        if sc not in SH: SH[sc] = avoid_shapes(d, g, sc)
        sh = SH[sc]
        # ⭐ **輪郭が囲いの線である区**(`polyIsFence`・前庭の帯 2026-09-06b)は、
        #    輪郭ではなく**低木を撒く面**を測る。⛔ 止めない — 面を切るか退避を緩めるかは庭方の意匠
        #    (⛔ 指図方が面を削って黙らせない)。
        if gd.get("polyIsFence"):
            B = shrub_box(gd)
            if B:
                r = gd["shrubs"]["spacingM"] / 2.0 / ken     # 低木の樹冠の半径(芯々=樹冠)
                hb = {}
                for p in poly_scan(B, st):
                    # ⭐ 枠ではなく**実際に撒く面**で測る(枠 ∩ 輪郭から `crownRKen` 以上内)
                    if not shrub_ok(gd, p): continue
                    nm = shape_hit(p, sh)
                    for k in range(12):
                        aa = 2.0 * math.pi * k / 12.0
                        nm = shape_hit((p[0] + math.cos(aa) * r, p[1] + math.sin(aa) * r), sh) or nm
                    if nm: hb[nm] = hb.get(nm, 0) + 1
                if hb:
                    note.append("%s の**低木を撒く面**(樹冠の外周で測る)が退避に載る — %s(合計 %.2f 坪)"
                                % (gd["name"], "・".join("%s %.2f坪" % (k, v * ct) for k, v in
                                                         sorted(hb.items(), key=lambda q: -q[1])[:6]),
                                   sum(hb.values()) * ct))
            continue
        hit = {}
        for p in poly_scan(P, st):
            nm = shape_hit(p, sh)
            if nm: hit[nm] = hit.get(nm, 0) + 1
        if hit:
            bad.append("%s の多角形が退避に載る — %s(合計 %.1f 坪)"
                       % (gd["name"], "・".join("%s %.1f坪" % (k, v * ct) for k, v in
                                                sorted(hit.items(), key=lambda q: -q[1])[:6]),
                          sum(hit.values()) * ct))
        for c in gd.get("clusters", []):
            n = cluster_n(c)
            sp = (c.get("spacing") or 0.0) * pack
            need = n * sp * sp
            got = 0
            for u0, v0, u1, v1 in cluster_boxes(c):
                for p in poly_scan([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], st):
                    if in_poly(p, P): got += 1
            got *= st * st
            if need > 0 and got < need:
                note.append("%s の塊「%s」は 箱 ∩ 区 が %.1f 間²(=%.1f坪)しか無く、"
                           "%g 本 × 芯々 %.1f 間(packRatio %.2f)に要る %.1f 間² に足りない"
                           % (gd["name"], c["name"], got, got * ken * ken / TSUBO, n,
                              c.get("spacing") or 0, pack, need))
    for b in d["slopeBands"]:
        if not b.get("uv"): continue
        out = sum(1 for p in poly_scan([(q[0], q[1]) for q in b["uv"]], st)
                  if not in_poly(p, soch))
        if out * ct > 0.05:
            bad.append("社叢 帯%d の多角形が社地の外へ %.2f 坪 出ている(社地 `polygon` でクリップすること)"
                       % (b["band"], out * ct))
    return bad, note


def noplant_overlap_check(d, g):
    """空地(`gardens[].noPlant`)が**平場の外へ出ていないか**・何と重なっているか。

    ⚠ 2026-09-06 検図4巡目 中5: `planting_avoid_check` は noPlant の面を丸ごと素通ししていたので、
    供待の矩形が板塀の外へ 1.03 間² 出て低木の帯と 0.600 間² 重なっていたのを取り逃した。
    ⛔ 止めるのは**平場の輪郭の外へ出る分**だけ(そこには地面が無い)。低木の帯・動線との重なりは
    〔記録〕 — どちらを動かすかは庭方の意匠(⛔ 指図方が空地を動かして黙らせない)。
    戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    ken = d["const"]["ken"]
    st = 0.25
    ct = cell_tsubo(d, st)
    TE = dict((t["name"], [(q[0], q[1]) for q in terrace_poly_uv(t)]) for t in d["terraces"])
    bands = [(nm, f) for nm, _B, f, _bb in shrub_areas(d)]
    for gd in d["gardens"]:
        if not gd.get("noPlant"): continue
        P = garden_poly(gd)
        if not P: continue
        te = TE.get(gd.get("clip"))
        cells = list(poly_scan(P, st))
        if te:
            n = sum(1 for q in cells if not in_poly(q, te))
            if n * ct > 0.02:
                bad.append("%s が平場『%s』の輪郭の外へ %.2f 坪 出ている"
                           % (gd["name"], gd["clip"], n * ct))
        for nm, fb in bands:
            n = sum(1 for q in cells if fb(q))
            if n * ct > 0.02:
                note.append("%s が %s と %.2f 坪 重なる" % (gd["name"], nm, n * ct))
        for rt in d.get("routes", []):
            # ⭐ 空地が載る段の路面幅で測る(`wByTerrace`・庭方 2026-09-06b)
            w = route_w(d, rt, gd.get("clip"))
            rr = w / 2.0 / ken
            pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
            sh = [_shape_seg(pts[i], pts[i + 1], rr, rt["name"]) for i in range(len(pts) - 1)]
            n = sum(1 for q in cells if shape_hit(q, sh))
            if n * ct > 0.02:
                note.append("%s が 動線『%s』の通行帯(幅 %.2f m)と %.2f 坪 重なる(面の %.0f%%)"
                            % (gd["name"], rt["name"], w, n * ct, n * 100.0 / max(1, len(cells))))
    return bad, note


# **意図された接合**の白名簿。⛔ ここを増やすときは理由を書く(黙って消さない)。
# ⭐ **2026-09-06 検図5巡目 中5 で 18件 → 6件へ絞った。**残した6件は今回**実測で坪が立った**組だけで、
#    落とした12件は**0.00坪**だった(= 接するだけで重ならない/そもそも当たらない)。
#    許可は「重なってよい」という宣言なので、重なっていない組を許可しておくと、
#    将来そこが本当に重なった日に黙って通ってしまう(死んだ許可)。落としたのは
#    (門:隨身門(楼門), 白洲) (石段:向拝の階, 棟:向拝) (石段:参道の階(前庭へ), 帯4)
#    (門:坂下の門(仁王門), 帯4) 権現造の継ぎ4組(本殿/作り合い/幣殿/拝殿/向拝)
#    (玉垣:返し, 前庭の帯) (玉垣:東面 上, 前庭の帯)
#    (踏石:仁王門の敷居前, 門:坂下の門(仁王門)) (踏石:参道の階の上端, 石段:参道の階(前庭へ))。
#    ⛔ これらは**接する**のが正しい姿なので、重なりが出たら鳴ってよい。
_OVL_OK = [
    ("門:中門", "白洲"), ("門:中門", "中庭"),                      # 門は塀の線に立ち、庭の縁を噛む
    ("石段:向拝の階", "中庭"),                                     # 階は向拝から中庭へ降りる
    ("石段:男坂", "帯4"), ("石段:女坂(御成坂)", "帯4"),             # 帯4は坂を含む裾。空けるのは avoid
    ("井戸:石敷", "前庭の帯"),                                     # 井戸屋形は帯の北の端に建つ
    # ⭐ **2026-09-07 検図7巡目 中2 で2件足した。**標本を最細の見付以下へ下げて初めて立った組で、
    #    どちらも**構造上そうなるほかない**当たり(⛔ 図を動かして黙らせない):
    ("前庭の帯", "玉垣:東面 上"),      # `polyIsFence` — 玉垣は帯の**輪郭の上に立つ**ので、
                                      #   柱の見付(`postDiaM`)は必ず輪郭を跨ぐ
    ("玉垣:東面 上", "踏石:参道の階の上端"),  # 北の隅柱は帯の頂点 P4 に立ち、その通り(u)は
                                      #   参道の階の開口の西の肩=踏石の西縁と同じ。取り合いは `joints`
    # ⭐ **2026-09-07 検図8巡目 中1 で1件足した。**刻みを最細の見付の**半分**まで下げて初めて
    #    標本が立った組で、『東面 上』とまったく同じ構造(玉垣は帯の輪郭の上に立つ)。
    #    ⛔ 図を動かして黙らせる件ではない — 旧刻み 0.0625 間ではこの辺だけ標本0個で丸ごと落ちていた
    ("前庭の帯", "玉垣:返し"),        # 東面の下段と上段を継ぐ**返し**。同じく輪郭の上に立つ
    # ⭐ **2026-09-07 検図9巡目 中1 で1件足した。**『返し』と『東面 上』は**隅で柱を共有する**ので、
    #    二本の帯(幅 `postDiaM`)が直交して重なる。重なりは柱の断面の 1/4(`postDiaM²`/4)で、
    #    ⛔ 図の欠陥ではない — 隅に柱を二本立てないことの現れ。取り合いは `joints` が面で持つ
    ("玉垣:返し", "玉垣:東面 上"),    # 隅の**共有柱**(⛔ 二本立てない)
    # ⭐ **2026-09-07 検図9巡目 低4 で5件足した。**石灯籠と手水鉢に面(`planM`)を与えて総当たりへ
    #    載せた組。**白洲は砂利敷の面**で、点景はその上に立つのが正しい姿(井戸屋形 × 前庭の帯と同じ)。
    #    ⛔ これ以外の面(棟・門・石段・帯)と当たったら鳴ってよい
    ("白洲", "点景:石灯籠 其1"), ("白洲", "点景:石灯籠 其2"),
    ("白洲", "点景:石灯籠 其3"), ("白洲", "点景:石灯籠 其4"),
    ("白洲", "点景:手水鉢(白洲の△) 其1"),
]


def _ovl_shapes(d, g):
    """総当たりに載せる面 — 棟・門・庭/区・帯4・石段・塊。(名, 判定関数, bbox, 多角形 or None) の列。

    ⭐ 4つめは**走査を速くするためだけの多角形**(2026-09-07 検図9巡目 中1)。刻みを二段下げて
    収束を見るには標本が 16 倍になるので、多角形は行ごとに交点を1回だけ出して判定する
    (⛔ 判定の結果は `in_poly` と一字一句同じ — 速さのためだけで、物差しは変えていない)。
    """
    ken = d["const"]["ken"]
    out = []

    def poly_item(nm, P):
        us = [q[0] for q in P]; vs = [q[1] for q in P]
        out.append((nm, (lambda P: (lambda p: in_poly(p, P)))(P),
                    (min(us), min(vs), max(us), max(vs)), list(P)))

    def corr_item(nm, pts, hw):
        # ⚠ **端に丸みを付けない。**踏面の帯は矩形で、坂の上下の端から先は坂ではない
        #   (キャップを付けると男坂が楼門と坂下の門を 4.75 坪ずつ噛む・2026-09-06)
        def f(p):
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                dx, dz = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dz * dz
                if L2 < 1e-12: continue
                t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2
                if not (0.0 <= t <= 1.0): continue
                if math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz) < hw: return True
            return False
        us = [q[0] for q in pts]; vs = [q[1] for q in pts]
        out.append((nm, f, (min(us) - hw, min(vs) - hw, max(us) + hw, max(vs) + hw), None))

    for m in d["munes"]:
        poly_item("棟:" + m["name"], [(m["u0"], m["v0"]), (m["u0"] + m["du"], m["v0"]),
                                      (m["u0"] + m["du"], m["v0"] + m["dv"]), (m["u0"], m["v0"] + m["dv"])])
    for gt in d["gates"]:
        hu, hv = gt["plan"]["du"] / 2.0, gt["plan"]["dv"] / 2.0
        poly_item("門:" + gt["name"], [(gt["u"] - hu, gt["v"] - hv), (gt["u"] + hu, gt["v"] - hv),
                                       (gt["u"] + hu, gt["v"] + hv), (gt["u"] - hu, gt["v"] + hv)])
    for gd in d["gardens"]:
        P = garden_poly(gd)
        if P: poly_item(gd["name"].split("(")[0], P)
    for b in d["slopeBands"]:
        if b.get("uv"): poly_item("帯%d" % b["band"], [(q[0], q[1]) for q in b["uv"]])
    for k in d["kaidans"]:
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        corr_item("石段:" + k["name"], pts, kaidan_wken(d, k) / 2.0)
    for holder in d["gardens"] + d["slopeBands"] + [d["planting"]]:
        for c in holder.get("clusters", []) + holder.get("viewClusters", []):
            for j, (u0, v0, u1, v1) in enumerate(cluster_boxes(c)):
                poly_item("塊:%s%s" % (c["name"], "" if j == 0 else "(其%d)" % (j + 1)),
                          [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    # ⭐ **2026-09-06 検図4巡目 中8 で集合を広げた** — 低木の帯・玉垣・踏石・面を持つ点景が
    #    一つも入っておらず、供待と低木の帯の 1.98 m² を取り逃していた。
    for nm, _B, f, bb in shrub_areas(d):
        out.append((nm, f, bb, None))          # 枠 ∩ 輪郭の内寄せ — 多角形一つでは書けない
    for gd in d["gardens"]:
        # ⭐ 開口(井戸の口)で切れた辺は**立つ区間ごとに**載せる(2026-09-06b)
        for nm, _a, _b, fence, _ln, rs in tamagaki_edges(d, gd):
            if not fence: continue
            for rn in rs:
                corr_item("玉垣:" + nm, [rn[0], rn[1]], gd["tamagaki"]["postDiaM"] / 2.0 / ken)
    _ir = ido_rects(d)
    if _ir:
        u0, v0, u1, v1 = _ir["石敷"]
        poly_item("井戸:石敷", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    for nm, u0, v0, u1, v1 in fumiishi_rects(d):
        poly_item("踏石:" + nm, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    for pp in prop_rects(d):
        poly_item("点景:" + pp[0], pp[1])
    return out


def prop_rects(d):
    """面を持つ点景(`plan {du,dv}`[間] か `planM {du,dv}`[m] と `yaw`)の輪郭。(名, 4点[uv]) の列。

    ⚠ 2026-09-06 検図4巡目 低14 — 縁台は点だけで、図に縮尺どおりに描けず総当たりにも載らなかった。
    ⭐ **呼び名は `labels` から採る**(2026-09-06 検図6巡目 低7)— 「其N」を焼き込んでいたので、
    総当たり・退避・断面の marks が「其N」、設計値と表が「甲1/乙2」で**突き合わせられなかった**。
    ⭐ **2026-09-07 検図9巡目 低4 — `planM`(m)を足した。**石灯籠・手水鉢は寸法の出所が
    在庫部材の実測と部材表(どちらも m)なので、間へ丸めて持つと出所が消える。
    ⛔ **一つの点景が `plan` と `planM` の両方を持たない**(二本立てにしない)。
    ⚠ 面を持たない点景は `prop_rects` が矩形を作らず、**面の総当たり・犬走り・視線の抜き・
    断面の marks から丸ごと抜ける**(帯へ動かしても鳴らない)。
    """
    out = []
    ken = d["const"]["ken"]
    for p in d.get("props", []):
        pl, plm = p.get("plan"), p.get("planM")
        if pl and plm:
            raise SystemExit("点景『%s』が `plan` と `planM` の両方を持つ(⛔ 二本立て)" % p["name"])
        if plm: pl = {"du": plm["du"] / ken, "dv": plm["dv"] / ken}
        if not pl or not p.get("uv"): continue
        yaws = p.get("yaw") or [0] * len(p["uv"])
        for i, (u, v) in enumerate(p["uv"]):
            a = math.radians(yaws[i] if i < len(yaws) else 0)
            ca, sa = math.cos(a), math.sin(a)
            hu, hv = pl["du"] / 2.0, pl["dv"] / 2.0
            q = [(-hu, -hv), (hu, -hv), (hu, hv), (-hu, hv)]
            out.append(("%s %s" % (p["name"], prop_label(p, i)),
                        [(u + x * ca - y * sa, v + x * sa + y * ca) for x, y in q]))
    return out


def prop_label(p, i):
    """点景の i 番目の呼び名 ── `labels` があればそれ、無ければ「其N」。⛔ 二本立てにしない。"""
    lb = p.get("labels") or []
    return lb[i] if i < len(lb) else "其%d" % (i + 1)


def prop_rect_of(d, name, label):
    """点景の1点の輪郭[uv 4点]。無ければ None。"""
    for nm, Q in prop_rects(d):
        if nm == "%s %s" % (name, label): return Q
    return None


def obb_gap(A, B):
    """二つの凸多角形(縁台の外形)の**離れ**[間]。負なら食い合っている(SAT)。"""
    best = None
    for P in (A, B):
        for i in range(len(P)):
            ax = (P[(i + 1) % len(P)][0] - P[i][0], P[(i + 1) % len(P)][1] - P[i][1])
            L = math.hypot(-ax[1], ax[0])
            if L < 1e-12: continue
            n = (-ax[1] / L, ax[0] / L)
            pa = [q[0] * n[0] + q[1] * n[1] for q in A]
            pb = [q[0] * n[0] + q[1] * n[1] for q in B]
            v = max(min(pb) - max(pa), min(pa) - max(pb))
            best = v if best is None else max(best, v)
    return best


def ovl_step(d):
    """総当たりの標本の刻み[間] ── **図の最も細い見付以下**にする(検図7巡目 中2)。

    ⚠ 旧 0.25 間(0.4545 m)は玉垣の柱 `postDiaM`(0.12 m = 0.066 間)の **7 倍粗く**、
    柱の芯を挟む2つの標本の間を面がすり抜けていた。「真の重なり 0」は**分解能の産物**で、
    刻みを下げると帯の輪郭 × その輪郭に立つ玉垣・玉垣 × 踏石 が出る。
    ⛔ 数を決め打ちしない — **総当たりに載る最も細い物の見付**から半分ずつ落として決める。
    ⭐ **2026-09-07 検図8巡目 中1 — 物差しは見付ではなく「はみ出す幅」で決める。**
    見付そのもの(0.120 m)を上限にした 0.0625 間(0.1136 m)は、まだ**収束していなかった**:
    同じ構造の2辺のうち『東面 上』を +96% 過大に測り、『返し』を**標本0個で丸ごと落として**いた。
    輪郭に立つ玉垣が輪郭から出るのは**柱の半分**(0.060 m)なので、上限は `postDiaM/2`。
    半分ずつ落とすので実際の刻みは見付の約 1/4 に落ち着く。
    ⭐ **2026-09-07 検図9巡目 中1 — 収束の判定を「一段下げて⛔0」から改めた。**
    旧の判定は 0.015625 間で⛔0を見て収束と呼んだが、それは**足切りが標本4個ぶんで、刻みを
    下げるほど下限も下がる**からたまたま等値で黙っただけで、さらに一段下げると⛔1件が出た。
    ⛔ 一段だけ見て収束と言わない ── 判定は `rect_overlap_check` が**二段連続で件数が変わらない**
    ことで下す。足切りは `ovl_min_tsubo`(部材の見付から出す**絶対値**)へ移した。
    """
    ken = d["const"]["ken"]
    fine = []
    for gd in d["gardens"]:
        tg = gd.get("tamagaki")
        if tg and tg.get("postDiaM"): fine.append(tg["postDiaM"] / ken)
    st = 0.25
    lim = (min(fine) / 2.0) if fine else st
    while st > lim: st /= 2.0
    return st


def ovl_min_dia(d):
    """総当たりに載る**最も細い部材の見付**[m](⛔ 無ければ止める)。"""
    fine = [(gd.get("tamagaki") or {}).get("postDiaM") for gd in d["gardens"]]
    fine = [q for q in fine if q]
    if not fine:
        raise SystemExit("玉垣の柱の見付 `postDiaM` が無い — 総当たりの物差しが立たない")
    return min(fine)


def ovl_min_tsubo(d):
    """総当たりの**足切り**[坪] ── **最も細い部材の見付の二乗**(絶対値)。

    ⭐ **2026-09-07 検図9巡目 中1。**旧版は「標本4個ぶん」で、刻みを半分にすると下限も 1/4 になった。
    ⛔ **刻みに従属する足切りは恒真的に新しい行を生む** — 下げれば下げるほど下限が下がるので、
    「一段下げて⛔0だから収束した」が言えない(等値で黙っただけかもしれない)。
    ⭕ 物差しは**部材の側**から採る: 柱一本の断面 `postDiaM²` より小さい当たりは、
    面が触れているのであって**面が重なっている**とは呼ばない。刻みを変えても動かない。
    """
    dia = ovl_min_dia(d)
    return dia * dia / TSUBO


def rect_overlap_check(d, g, minTsubo=None):
    """(c) **面の総当たり** — 棟・門・庭/区・帯4・石段・塊で真の重なりが無いか。

    ⚠ 2026-09-06 の検図「矩形総当たりが生成器に無い」。意図された接合は `_OVL_OK` で除く。
    戻り値 (⛔止める, 〔記録〕)。**実体どうし(棟・門・庭・帯・石段)の重なりは止める**が、
    **塊が絡む重なりは〔記録〕**にする — 塊の箱は実体ではなく「撒く定義域」で、
    その始末は庭方の意匠(⛔ 指図方が箱を動かして黙らせない)。
    """
    it = _ovl_shapes(d, g)
    ok = set(tuple(sorted(q)) for q in _OVL_OK)
    st = ovl_step(d)
    # ⭐ **足切りは部材の見付から出す絶対値**(検図9巡目 中1)。⛔ 刻みに従属させない —
    #    従属させると刻みを下げるたびに下限も下がり、「一段下げて⛔0」が収束の証拠にならない
    if minTsubo is None: minTsubo = ovl_min_tsubo(d)
    bad, note = _ovl_scan(it, ok, st, d, minTsubo)
    # ⭐ **収束の判定 ── 二段連続で⛔の件数が変わらないこと**(検図9巡目 中1)。
    #    ⛔ 一段だけ見て収束と言わない。足切りが絶対値になったので、件数が動くのは
    #    「粗すぎて見えていなかった当たりが見えた」ときだけになる
    cnt = [len(bad)]
    fine = st
    for _k in range(2):
        fine /= 2.0
        b2, _n2 = _ovl_scan(it, ok, fine, d, minTsubo)
        cnt.append(len(b2))
        if len(b2) != len(bad):
            for q in b2:
                if q not in bad:
                    bad.append("%s(刻み %.6f 間で初めて立った — 粗い刻みでは標本が乗らない当たり)"
                               % (q, fine))
    if len(set(cnt)) != 1:
        bad.append("総当たりの標本が**収束していない** — ⛔ の件数が刻み %s で %s と動く。"
                   "⛔ 刻みを戻して黙らせない(規則19)"
                   % ("／".join("%.6f" % (st / (2.0 ** i)) for i in range(len(cnt))),
                      "→".join("%d" % q for q in cnt)))
    # ⛔ **物差しを刷る**(規則19)— 「重なり0」は刻みと足切りとセットでしか読めない
    note.append("総当たり %d 組・標本の刻み %.4f 間(%.3f m = 最細の見付 %.3f m の**半分**以下)・"
                "足切り %.4f 坪(= 最細の見付の二乗・**刻みに従属しない絶対値**)・"
                "意図された接合の白名簿 %d 組【算出】"
                % (len(it) * (len(it) - 1) // 2, st, st * d["const"]["ken"],
                   ovl_min_dia(d), minTsubo, len(ok)))
    note.append("**収束の確認** — 刻みを二段(%s 間)下げて⛔の件数は %s%s【算出 — "
                "⛔ 一段だけ見て収束と言わない(検図9巡目 中1)】"
                % ("・".join("%.6f" % (st / (2.0 ** (i + 1))) for i in range(len(cnt) - 1)),
                   "→".join("%d" % q for q in cnt),
                   "(**二段連続で変わらない = 収束**)" if len(set(cnt)) == 1
                   else "(⛔ **動いている = 収束していない**)"))
    return bad, note


def _ovl_scan(it, ok, st, d, minTsubo):
    """総当たりの一巡(刻み `st`)。戻り値 (⛔止める, 〔記録〕)。

    ⚠ **多角形は行ごとに交点を出して判定する**(2026-09-07 検図9巡目 中1)— 判定の結果は
    `in_poly` と同じで、⛔ 物差しは変えていない。収束を見るのに刻みを二段下げるので、
    素の点内外判定のままでは組み上げが数分に伸びる。
    """
    ct = cell_tsubo(d, st)
    bad, note = [], []
    for i in range(len(it)):
        for j in range(i + 1, len(it)):
            (na, fa, ba, Pa), (nb, fb, bb, Pb) = it[i], it[j]
            if tuple(sorted((na, nb))) in ok: continue
            if na.startswith("塊:") and nb.startswith("塊:"):
                pass                                   # 塊どうしは重なってはいけない
            elif na.startswith("塊:") and (nb.startswith("境内の立木") or nb.startswith("帯")):
                continue                               # 塊は区・帯の中に置く定義域
            elif nb.startswith("塊:") and (na.startswith("境内の立木") or na.startswith("帯")):
                continue
            elif ("低木の面:" + nb) == na or ("低木の面:" + na) == nb:
                continue                               # 撒く面はその区の中に取る定義域
            u0, v0 = max(ba[0], bb[0]), max(ba[1], bb[1])
            u1, v1 = min(ba[2], bb[2]), min(ba[3], bb[3])
            if u1 - u0 <= 0 or v1 - v0 <= 0: continue
            n = 0
            v = v0 + st / 2.0
            while v < v1:
                xa = _poly_row(Pa, v) if Pa is not None else None
                xb = _poly_row(Pb, v) if Pb is not None else None
                if (xa is None or xa) and (xb is None or xb):   # 交点0本の行は空
                    u = u0 + st / 2.0
                    while u < u1:
                        if (_row_in(xa, u) if xa is not None else fa((u, v))) and \
                           (_row_in(xb, u) if xb is not None else fb((u, v))): n += 1
                        u += st
                v += st
            if n * ct > minTsubo:
                # **定義域(塊・低木の帯)が絡む重なりは〔記録〕** — 撒く範囲は庭方の意匠で、
                # ⛔ 指図方が帯や箱を動かして黙らせない(2026-09-06 検図4巡目 中8 で低木の帯を足したとき、
                #    縁台 其2 が南区間の帯に 0.12 坪 掛かることが出た)
                dom = ("塊:", "低木の面:")
                (note if (na.startswith(dom) or nb.startswith(dom)) else bad).append(
                    "%s と %s が %.4f 坪(%.4f m²)重なる"
                    % (na, nb, n * ct, n * ct * TSUBO))
    return bad, note


def _poly_row(P, z):
    """多角形 `P` を z の行で切った**交点の u**(昇順)。⛔ `in_poly` と同じ判定則。"""
    xs = []
    j = len(P) - 1
    for i in range(len(P)):
        if (P[i][1] > z) != (P[j][1] > z):
            xs.append((P[j][0] - P[i][0]) * (z - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0])
        j = i
    xs.sort()
    return xs


def _row_in(xs, x):
    """行の交点列 `xs` に対する内外(= `in_poly` の「x より右の交点が奇数本」)。"""
    return (len(xs) - bisect.bisect_right(xs, x)) % 2 == 1


def kaidan_wken(d, k):
    """石段の**幅**[間] ── 正典は `wKen`(⛔ `w`[m] と二本立てにしない・検図7巡目 低5)。

    ⚠ 旧版は `wKen or w/ken` で、参道の階が 5.500 m 対 3.03 間(5.5085 m)の二本立てだった。
    **図が描く階の帯が、その階のために板塀に開けた口より 8.5 mm 狭い**という食い違いが出る。
    """
    if k.get("wKen") is None:
        raise SystemExit("石段『%s』に `wKen` が無い(幅の正典は間)" % k["name"])
    return k["wKen"]


def kaidan_wm(d, k):
    """石段の幅[m] ── `wKen` × 間。⛔ メートルの値を json に持たない。"""
    return kaidan_wken(d, k) * d["const"]["ken"]


def segs(o):
    """石段・土留めの区間。`pts`(折れ線)があればそれ、無ければ a→b の1区間。

    2026-08-23、女坂を明治16年実測図の**屈曲**へ改めたときに導入した。
    """
    p = o.get("pts")
    if p:
        return [(p[i], p[i + 1]) for i in range(len(p) - 1)]
    return [(o["a"], o["b"])]


def seg_len(o, ken):
    """折れ線の展開長[m]。"""
    return sum(math.hypot((b[0] - a[0]) * ken, (b[1] - a[1]) * ken) for a, b in segs(o))



def cut_lines(d, PX, PY, LEN, inwin=None, clip=None):
    """断面の切断線を平面図へ落とす。PX/PY = 世界座標→px、LEN = m→px。"""
    o = []
    for sec in d.get("sections", []):
        ln = sec.get("line")
        if not ln: continue
        # 折れ線の切断線(女坂など)は両端で代表させる
        (x0, z0), (x1, z1) = ln[0], ln[-1]
        if inwin and not inwin((x0, z0), (x1, z1)): continue
        ax, ay = PX(x0), PY(z0)
        bx, by = PX(x1), PY(z1)
        if clip:                      # 図の窓で切って、矢視記号を縁に置く
            cx0, cy0, cx1, cy1 = clip
            dx0, dy0 = bx - ax, by - ay
            t0, t1 = 0.0, 1.0
            for pq in ((-dx0, ax - cx0), (dx0, cx1 - ax), (-dy0, ay - cy0), (dy0, cy1 - ay)):
                pp, qq = pq
                if abs(pp) < 1e-9:
                    if qq < 0: t0, t1 = 1.0, 0.0
                    continue
                r = qq / pp
                if pp < 0: t0 = max(t0, r)
                else:      t1 = min(t1, r)
            if t0 >= t1: continue
            ax, ay, bx, by = (ax + dx0 * t0, ay + dy0 * t0, ax + dx0 * t1, ay + dy0 * t1)
        # 一点鎖線
        if len(ln) > 2:               # 折れ線の切断線は全点で引く(弦だと觀理院を横切って見えた・検図 2026-09-06)
            o.append(PL([(PX(x), PY(z)) for x, z in ln], stroke="var(--shu)", sw=1.0, dash="12 3 2 3", op=0.85))
        else:
            o.append(LN(ax, ay, bx, by, stroke="var(--shu)", sw=1.0, dash="12 3 2 3", op=0.85))
        vx, vz = sec["view"]
        nv = math.hypot(vx, vz) or 1.0
        # 矢視の向き(px 空間。z は上下反転するので Y 成分の符号に注意)
        adx = PX(x0 + vx / nv) - PX(x0)
        ady = PY(z0 + vz / nv) - PY(z0)
        an = math.hypot(adx, ady) or 1.0
        adx, ady = adx / an, ady / an
        dx, dy = bx - ax, by - ay
        dn = math.hypot(dx, dy) or 1.0
        dx, dy = dx / dn, dy / dn
        for (ex, ey, sgn) in ((ax, ay, 1.0), (bx, by, -1.0)):
            # 端部の太い線
            o.append(LN(ex, ey, ex + dx * 16 * sgn, ey + dy * 16 * sgn, stroke="var(--shu)", sw=2.6))
            # 矢視の矢
            hx, hy = ex + dx * 8 * sgn, ey + dy * 8 * sgn
            tx, ty = hx + adx * 13, hy + ady * 13
            o.append(LN(hx, hy, tx, ty, stroke="var(--shu)", sw=1.8))
            px_, py_ = -ady, adx
            o.append(PL([(tx, ty), (tx - adx * 5 + px_ * 3, ty - ady * 5 + py_ * 3),
                         (tx - adx * 5 - px_ * 3, ty - ady * 5 - py_ * 3)],
                        stroke="none", fill="var(--shu)", close=True))
            # カナの札
            cx, cy = ex - dx * 11 * sgn, ey - dy * 11 * sgn
            o.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="var(--paper2)" stroke="var(--shu)" stroke-width="1.2"/>'
                     % (cx, cy))
            o.append(T(cx, cy + 4, sec["kana"], fs=11.5, anchor="middle", fill="var(--shu)"))
    return o


# ---------------------------------------------------------------- 現況図 / 切盛図(スキル §3a・§3b)
DEM = None


def dem():
    """造成前の地形【確度P】。`docs/Sashizu/sanno_dem.json`。

    ⚠ **実体は正本 `docs/Sashizu/base_dem.json` からの切り出し**(生成器 `Tools/Sashizu/build_base_dem.py`)。
    ⛔ **Unity の live terrain から採り直さない**(CLAUDE.md 規則12)— live は自他の造成が
    乗る作業面で、**採った時刻で値が変わる**。2026-08-23 に岡部・土井が松平の造成を
    「造成前の地形」として吸い込む事故が起きた(山王は範囲が届かず無傷)。
    ⛔ `sanno_dem.json` を手で編集しない。区画を動かしたら `build_base_dem.py` を回す。
    """
    global DEM
    if DEM is None:
        DEM = json.load(open(os.path.join(DOC, "sanno_dem.json"), encoding="utf-8"))
    return DEM


# ⚠ sanno_dem.json は正本を **0.05m 刻みに量子化**して書き出される(2026-08-31 実測:
#   85%のセルが正本と ±0.05m 以内でずれ、分布は一様=丸め)。正本の粒度は 0.01m。
#   ⛔ ここを 0 にすると毎回落ちる。逆に大きくしすぎると live terrain の混入(過去の事故は
#   8m 級)を見逃す。丸め幅のすぐ上に置く。
TERRAIN_TOL = 0.06


def terrain_provenance_check():
    """地形の種地が **正本 base_dem.json から来ているか**を実測で確かめる(CLAUDE.md 規則13・EDO-0031)。

    ⛔ **宣言を信用しない。** `sanno_dem.json` の `_` は「正本からの切り出し」と*名乗って*いるが、
    名乗りは検査ではない。2026-08-23 に4邸が live terrain を「造成前」として吸い込んだ事故は、
    どの邸も同じ文言を持ったまま起きた(EDO-0029「読めなければ0件」の監査)。
    §3a 現況図・§3b 切盛図・全断面はこの地形を読むので、種地がずれていれば図の「0件」が意味を失う。

    戻り値: 不具合の文字列のリスト(空なら合格)。
    """
    try:
        base = json.load(open(os.path.join(DOC, "base_dem.json"), encoding="utf-8"))
        cut = json.load(open(os.path.join(DOC, "sanno_dem.json"), encoding="utf-8"))
    except Exception as ex:
        return ["地形の出所を照合できない — **この検査は回っていない**(合格ではない): %s" % ex]

    if base["step"] != cut["step"]:
        return ["切り出しと正本で格子の刻みが違う(正本 %s / 切り出し %s)" % (base["step"], cut["step"])]
    st = base["step"]
    fx, fz = (cut["x0"] - base["x0"]) / st, (cut["z0"] - base["z0"]) / st
    if fx != int(fx) or fz != int(fz):
        return ["切り出しの原点が正本の格子に乗っていない(dx=%.3f dz=%.3f セル)— "
                "補間が挟まるので切り出しとして扱えない" % (fx, fz)]
    dx, dz = int(fx), int(fz)
    B, C = base["h"], cut["h"]

    # ⛔ 正本の外に出た点を**黙って飛ばさない**。飛ばすと「差が小さい」に化けて見えなくなる。
    worst, wl, out, seen = 0.0, None, 0, 0
    for j in range(len(C)):
        for i in range(len(C[0])):
            bj, bi = j + dz, i + dx
            if not (0 <= bj < base["nz"] and 0 <= bi < base["nx"]):
                out += 1
                continue
            a, b = C[j][i], B[bj][bi]
            if a is None or b is None:
                continue
            seen += 1
            if abs(a - b) > worst:
                worst, wl = abs(a - b), (cut["x0"] + i * st, cut["z0"] + j * st, a, b)
    if out:
        return ["切り出しの %d セルが正本 base_dem.json の範囲の外にある — "
                "CANON_SPEC を広げて `build_base_dem.py --canon` から正本を作り直すこと(規則13)" % out]
    if seen < 200:
        return ["地形の照合の標本が %d 点しか取れない — 切り出しか正本の範囲がおかしい" % seen]
    if worst > TERRAIN_TOL:
        return ["**種地が正本から来ていない** — 切り出しが正本と最大 %.2fm 食い違う "
                "(x=%.0f z=%.0f: 切り出し %.2f / 正本 %.2f)。live terrain を吸っていないか(規則13)"
                % (worst, wl[0], wl[1], wl[2], wl[3])]

    # 担当区画が切り出しに収まっているか(欠測を黙って図に出さないための関門・EDO-0014)
    try:
        P = json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))
        P = P["parcels"] if isinstance(P, dict) and "parcels" in P else P
        P = {q["id"]: q for q in P}
    except Exception as ex:
        return ["区画を読めないので切り出しの覆いを検べられない — この検査は回っていない: %s" % ex]
    ids = ["sannosha_prec", "sannosha_kanri", "sannobuke_juge"] + \
          ["sannojubo_parcels_%d" % i for i in range(10)]
    X1 = cut["x0"] + (cut["nx"] - 1) * st
    Z1 = cut["z0"] + (cut["nz"] - 1) * st
    bad = []
    for pid in ids:
        q = P.get(pid)
        if q is None:
            bad.append("区画 %s が parcels.json に無い" % pid)
            continue
        pl = None
        for k in ("polygon", "points", "pts", "poly"):
            if k in q:
                pl = q[k]
                break
        xs = [a for a, b in pl]
        zs = [b for a, b in pl]
        m = [("西", min(xs) - cut["x0"]), ("東", X1 - max(xs)),
             ("南", min(zs) - cut["z0"]), ("北", Z1 - max(zs))]
        short = [(k, v) for k, v in m if v < 0]
        if short:
            bad.append("%s が切り出しの外へ出ている(%s)— `build_base_dem.py` の SLICES を広げること"
                       % (q.get("label", pid),
                          "・".join("%s %.1fm" % (k, v) for k, v in short)))
    return bad


def dem_h(x, z):
    D = dem()
    i = (x - D["x0"]) / D["step"]; j = (z - D["z0"]) / D["step"]
    a, b = int(math.floor(i)), int(math.floor(j))
    if a < 0 or b < 0 or a + 1 >= D["nx"] or b + 1 >= D["nz"]: return None
    fx, fz = i - a, j - b
    H = D["h"]
    return ((H[b][a] * (1 - fx) + H[b][a + 1] * fx) * (1 - fz)
            + (H[b + 1][a] * (1 - fx) + H[b + 1][a + 1] * fx) * fz)


# 段彩は地図の記号なので明暗テーマに関わらず固定(スキル §3a)
DANSAI = ["#20476B", "#2E6E93", "#4E97AE", "#7FBBBF", "#A9D2B5", "#CBE0A6",
          "#E4E3A0", "#EBD293", "#E3B47F", "#D4926B", "#BE6E56", "#9E4A42"]


def dansai(hh):
    return DANSAI[max(0, min(len(DANSAI) - 1, int((hh - 6.0) // 2.0)))]


def torii_marks(d, PX, PY):
    """鳥居の記号(位置のある物だけ)。"""
    o = []
    for t in d["torii"]:
        if not t.get("pos"): continue
        x, z = t["pos"]
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--shu)" stroke="var(--paper)" stroke-width="1"/>' % (PX(x), PY(z)))
        o.append(T(PX(x) + 6, PY(z) - 5, t["name"], fs=10, fill="var(--shu)"))
    return o


def road_draw(seg, PX, PY, LEN):
    """麓道。`area`(区画間の領域)があれば面で、無ければ実幅の帯で描く(2026-09-06)。"""
    if seg.get("area"):
        return [PL([(PX(x), PY(z)) for x, z in seg["area"]], fill="var(--michi)", op=0.45,
                   stroke="var(--michi)", sw=0.8, close=True),
                PL([(PX(x), PY(z)) for x, z in seg["pts"]], stroke="var(--ink)", sw=0.6, dash="2 4", op=0.5)]
    return band(seg["pts"], PX, PY, LEN, seg.get("w") or 4.5, "var(--michi)", "var(--michi)", op=0.6)


def _widen(d, x0, x1, z0, z1, pad=12.0):
    """現況図・切盛図の窓に参道と鳥居を入れる(辻と参道の一部が図の外だった・検図 2026-09-06)。"""
    ext = list(d["sando"]["pts"]) + [t["pos"] for t in d["torii"] if t.get("pos")]
    return (min([x0] + [q[0] - pad for q in ext]), max([x1] + [q[0] + pad for q in ext]),
            min([z0] + [q[1] - pad for q in ext]), max([z1] + [q[1] + pad for q in ext]))


def genkyo_svg(d, kan, x0, x1, z0, z1, W=900.0):
    """§3a 現況図 — 造成前の地形。段彩2m + 等高線(10m 太線)+ 隣地の区画。"""
    pr = Proj(x0, x1, z0, z1, W=W, pad=0.0, top=26.0, bottom=30.0)
    o = _sv(pr.W, pr.H, "現況図(造成前の地形)")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))
    stp = 2
    for z in range(int(z0), int(z1), stp):
        for x in range(int(x0), int(x1), stp):
            hh = dem_h(x + stp / 2.0, z + stp / 2.0)
            if hh is None: continue
            o.append(R(pr.X(x), pr.Y(z + stp), pr.L(stp) + 0.6, pr.L(stp) + 0.6,
                       fill=dansai(hh), op=0.85))
    # 等高線(2m。10m は太線+数値)
    for lv in range(8, 32, 2):
        segs_ = []
        for z in range(int(z0), int(z1), stp):
            for x in range(int(x0), int(x1), stp):
                a = dem_h(x, z); b = dem_h(x + stp, z); c = dem_h(x, z + stp)
                if None in (a, b, c): continue
                if (a - lv) * (b - lv) < 0:
                    t = (lv - a) / (b - a); segs_.append((x + stp * t, z))
                if (a - lv) * (c - lv) < 0:
                    t = (lv - a) / (c - a); segs_.append((x, z + stp * t))
        big = (lv % 10 == 0)
        for (px, pz) in segs_:
            o.append(R(pr.X(px) - (1.0 if big else 0.5), pr.Y(pz) - (1.0 if big else 0.5),
                       2.0 if big else 1.0, 2.0 if big else 1.0,
                       fill="var(--ink)", op=0.75 if big else 0.35))
    # 社地と隣地
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in d["polygon"]], stroke="var(--ink)", sw=2.0, close=True))
    for nb in d.get("neighbors", []):
        if not nb.get("polygon"): continue
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in nb["polygon"]],
                    stroke="var(--shu)", sw=1.2, dash="6 4", close=True))
        cx = sum(q[0] for q in nb["polygon"]) / len(nb["polygon"])
        cz = sum(q[1] for q in nb["polygon"]) / len(nb["polygon"])
        o.append(T(pr.X(cx), pr.Y(cz), nb["name"], fs=10.5, anchor="middle", fill="var(--shu)"))
    o += cut_lines(d, pr.X, pr.Y, pr.L)
    o.append(T(6, 15, kan + "　現況図 ─ 造成前の地形(正本 base_dem.json からの切り出し・確度P)", fs=12.5, fill="var(--dim)"))
    o.append(T(pr.W - 6, 15, "段彩 2 m ／ 等高線 2 m(10 m 太線) ／ 北が上", fs=10.5,
               anchor="end", fill="var(--dim)"))
    y = pr.H - 14
    o.append(LN(14, y, 14 + pr.L(100), y, stroke="var(--dim)", sw=1.2))
    o.append(T(14 + pr.L(100) / 2, y - 4, "100 m", fs=10.5, anchor="middle"))
    o += sando_band(d, pr.X, pr.Y, pr.L); o += torii_marks(d, pr.X, pr.Y)   # 参道と鳥居(検図 2026-09-06)
    o.append(ENDSVG)
    return "\n".join(o)


CUTFILL = [("#B4653F", 3.0), ("#D28F6B", 2.0), ("#E3B79A", 1.0), ("#EFD9C8", 0.3),
           ("#D4DEE6", -0.3), ("#AFC4D4", -1.0), ("#87A5BC", -2.0), ("#5E7F9B", -3.0)]


def _stair_y(d, g, x, z):
    """石段の通路(帯)の設計高さ。坂も造成の対象(2026-08-23 検図 — 図から丸ごと落ちていた)。"""
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        hw = kaidan_wm(d, k) / 2.0
        tot = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                  for i in range(len(pts) - 1)) or 1.0
        acc = 0.0
        for i in range(len(pts) - 1):
            ax, az = pts[i]; bx, bz = pts[i + 1]
            dx, dz = bx - ax, bz - az
            L = math.hypot(dx, dz) or 1.0
            t = ((x - ax) * dx + (z - az) * dz) / (L * L)
            if t < 0 or t > 1: acc += L; continue
            px, pz = ax + dx * t, az + dz * t
            if math.hypot(x - px, z - pz) <= hw:
                sfrac = (acc + L * t) / tot
                # ⚠ pts[0] が山上か坂下かで向きが変わる(2026-08-23 検図 — 男坂だけ上下逆だった)。
                #    第一点の自然地形が最後の点より高ければ pts[0] = 山上。
                h0 = dem_h(pts[0][0], pts[0][1]); h1 = dem_h(pts[-1][0], pts[-1][1])
                if h0 is not None and h1 is not None and h0 > h1:
                    sfrac = 1.0 - sfrac
                # ⚠ **踊り場のある坂は直線補間にならない**(2026-08-24 検図 高-4 —
                #    切盛図が男坂で断面と最大1.34m 食い違っていた)。断面と同じ割付から引く。
                return stair_y_at(k, sfrac)
            acc += L
    return None


def stair_spans(k):
    """石段の割付を **(s0, s1, 面の高さ)** の列で返す(s は坂下からの展開長)。

    断面(stair_profile)・切盛図(_stair_y)・動線の昇りが**この一つの関数**を通る。
    ⚠ 二つの式で別々に割ると蹴上1段ぶん(0.30m)ずれる(2026-08-24 検図 高-4)。
    """
    keri = k.get("keri", 0.30); fumi = k.get("fumi", 0.45); od = k.get("odoriba", 0.0)
    fl = k.get("flights") or ([k["steps"]] if k.get("steps") else None)
    if not fl: return None, None
    y0 = k["yBot"]
    out, sacc, n = [], 0.0, 0
    for fi, fn in enumerate(fl):
        for _ in range(fn):
            out.append((sacc, sacc + fumi, y0 + n * keri)); sacc += fumi; n += 1
        if fi < len(fl) - 1 and od > 0:
            out.append((sacc, sacc + od, y0 + n * keri)); sacc += od
    return out, sacc


def stair_y_at(k, sfrac):
    """石段の縦断上の高さ。sfrac は坂下 0 → 頭 1。"""
    sp, tot = stair_spans(k)
    if sp is None:                        # 斜路 — 一様勾配
        return k["yBot"] + (k["yTop"] - k["yBot"]) * max(0.0, min(1.0, sfrac))
    w = max(0.0, min(1.0, sfrac)) * tot
    if w >= tot - 1e-9: return k["yTop"]  # 頭は境内面(最後の蹴上を上がりきった高さ)
    for a, b, y in sp:
        if w <= b + 1e-9: return y
    return k["yTop"]


def stair_profile(c0, c1, y0, y1, kd):
    """断面の石段。**stair_spans と同じ割付**で踏面/蹴上のギザギザを返す(スキル §3c)。

    ⚠ 区間を c で単純にソートすると蹴上の点が入れ替わって鋸の歯が乱れる — 進行方向に
    区間を並べ直してから継ぐ(2026-08-24)。
    """
    sp, tot = stair_spans(kd)
    if sp is None:                    # 斜路 — 一様勾配(段は坂の割付の図で読む)
        return [(c0, y0), (c1, y1)]
    up = y1 > y0                      # c0 → c1 が上りか
    C = (lambda w: c0 + (c1 - c0) * (w / tot)) if up else (lambda w: c0 + (c1 - c0) * (1.0 - w / tot))
    seq = sp if up else list(reversed(sp))
    out = []
    for a, b, y in seq:
        ca, cb = (C(a), C(b)) if up else (C(b), C(a))
        if not out:
            if abs(y - y0) > 1e-9: out.append((ca, y0))     # 端の蹴上
            out.append((ca, y))
        elif abs(y - out[-1][1]) > 1e-9:
            out.append((ca, y))                             # 蹴上(垂直)
        out.append((cb, y))
    if abs(out[-1][1] - y1) > 1e-9: out.append((out[-1][0], y1))
    return out

def offset_poly_in(P, ins):
    """多角形を内側へ ins だけ寄せる(角は留め継ぎ)。板塀・柵を平場から機械生成するため。"""
    n = len(P)
    # 向きを CCW に揃える
    a2 = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    Q = P if a2 > 0 else P[::-1]
    out = []
    for i in range(len(Q)):
        p0, p1, p2 = Q[i - 1], Q[i], Q[(i + 1) % len(Q)]
        def nrm(a, b):
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz) or 1.0
            return (-dz / L, dx / L)          # CCW なら内向き
        n1, n2 = nrm(p0, p1), nrm(p1, p2)
        bx, bz = n1[0] + n2[0], n1[1] + n2[1]
        L = math.hypot(bx, bz)
        if L < 1e-6: bx, bz, L = n1[0], n1[1], 1.0
        cosh = max(0.35, (bx * n1[0] + bz * n1[1]) / L)     # 留めの伸び(鋭角で暴れないよう頭打ち)
        out.append([p1[0] + bx / L * ins / cosh, p1[1] + bz / L * ins / cosh])
    return out if a2 > 0 else out[::-1]


def gap_source(d, gf, owner):
    """`gapFrom` / `vFrom` が指す物の **芯[uv] と半幅[間]**。⛔ 口の半幅を literal で持たない。

    ・`kaidan` ── 石段。半幅 = `wKen`/2、芯 = 折れ線の第1点(平場の縁に取り付く端)
    ・`gate`   ── 門。半幅 = `plan[span]`/2(既定は桁行 `dv` の半分)、芯 = 門の芯
    """
    if gf.get("kaidan"):
        k = [q for q in d["kaidans"] if q["name"] == gf["kaidan"]]
        if not k: raise SystemExit("『%s』の `gapFrom` が引けない: %s" % (owner, gf["kaidan"]))
        k = k[0]
        p = (k.get("pts") or [k["a"], k["b"]])[0]
        return (p[0], p[1]), kaidan_wken(d, k) / 2.0
    if gf.get("gate"):
        gt = gate_by_name(d, gf["gate"])
        return (gt["u"], gt["v"]), gt["plan"][gf.get("span", "dv")] / 2.0
    raise SystemExit("『%s』の `gapFrom` が何を指すのか読めない" % owner)


def derive_gaps(d):
    """**口は、その口が通す物の幅からの従属値**にする ── 囲い(`runs`)と土留め(`terraceWalls`)の両方。

    ⚠ 2026-09-07 検図8巡目 中3 — `wKen` 一本化(7巡目 低5)が**土留めの口に届いていなかった**。
    `TW_Zentei_W`(男坂の口)・`TW_Zentei_N`(参道の階の口)・`TW_Kairo_E`/`_W`(楼門の口)の
    半幅と、男坂の側壁 `TW_Otoko_N`/`_S` の通りが literal で、**石段の幅を動かしても口は動かない**
    (1.82 m の階に 7.0 m の口が残る)形だった。差が今日 0.0 mm でも、**動かした日に破れる**。
    ⛔ どちらの軸に開くかも書かない — 辺の向き(a→b)から決める。
    """
    for o in d["runs"] + d["terraceWalls"]:
        gf = o.get("gapFrom")
        if not gf: continue
        (cu, cv), hw = gap_source(d, gf, o["name"])
        o["gapHalf"] = hw
        a, b = o.get("a"), o.get("b")
        if a is not None and b is not None and abs(a[0] - b[0]) < abs(a[1] - b[1]):
            o["gapV"] = cv; o.pop("gapU", None)    # v に走る辺 → 口は v で開く
        else:
            o["gapU"] = cu; o.pop("gapV", None)
    # 石段の**両側の側壁**の通り ── 芯 ± 半幅(⛔ ±1.925 のような数を持たない)
    for w in d["terraceWalls"]:
        vf = w.get("vFrom")
        if not vf: continue
        (_cu, cv), hw = gap_source(d, vf, w["name"])
        w["a"][1] = w["b"][1] = cv + (hw if vf["side"] == "北" else -hw)


def derive_runs(d, g):
    """平場の輪郭に従う囲いを**その場で生成する**(2026-08-23 検図 中-5)。

    囲いの座標を独立に持つと、平場を動かしたとき黙って取り残される
    (前庭を多角形にしたとき南の板塀が5m内側に残った)。
    ⭐ 境内の外周は 2026-09-07 のユーザー裁定で**腰高の柵**になった(旧・板塀)。
    ⛔ 生成の仕方は変わらない — 種別が替わっても輪郭からの従属値である。
    """
    derive_gaps(d)             # 口は通す物の幅からの従属値(囲い・土留めの両方・検図8巡目 中3)
    # ⛔ **宣言が無ければ止める**(検図9巡目 中3)— 既定値で黙って埋めると、
    #    `const.inubashiri` を消しても板塀が同じ所に立ち、検査も鳴らない
    if d["const"].get("inubashiri") is None:
        raise SystemExit("犬走り `const.inubashiri` の宣言が無い(境内の囲いの寄せ幅)")
    ins = d["const"]["inubashiri"] / d["const"]["ken"]
    by = {r["name"]: r for r in d["runs"]}
    if "Ita_Keidai" not in by: return
    uv = d["terraces"][0]["uv"]
    off = offset_poly_in(uv, ins)
    # ⚠ **回廊の基壇が東front を成すので、平場の東の張り出しには塀を回さない**
    #    (2026-08-24 検図 高-1 — 機械化したとき楼門・回廊・男坂の前を塀が塞いだ)。
    #    u>0 の頂点 = 回廊の前の辺。そこを落とし、南北の隅を直線で継ぐ。
    n = len(uv)
    drop = [i for i in range(n) if uv[i][0] > 0.0]
    # ⚠ **落とした区間を弦で結んではならない** — 回廊の後ろに南北32間の塀が立ってしまう
    #   (2026-08-24 検図 高-3 の後始末)。落とした先頭から始まる**開いた折れ線**にする。
    start = (drop[-1] + 1) % n if drop else 0
    pts = [off[(start + i) % n] for i in range(n) if uv[(start + i) % n][0] <= 0.0]
    # 開口 ── 平場の縁に取り付く石段の頭と、勝手口
    gaps = []
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        for q in ((k.get("pts") or [k["a"], k["b"]])[0], (k.get("pts") or [k["a"], k["b"]])[-1]):
            if _near_poly(q, pts, 2.0):
                gaps.append([round(q[0], 3), round(q[1], 3), round(kaidan_wken(d, k) / 2.0 + 0.2, 3)])
    for gt in d["gates"]:
        if _near_poly([gt["u"], gt["v"]], pts, 2.0):
            gaps.append([gt["u"], gt["v"], round(gt["plan"]["du"] / 2.0 + 0.3, 3)])
    # 開口の芯は**塀の線の上へ落とす** — 平場の縁に立つ門・石段は塀より 0.25間 外にあるので、
    #   芯のままでは半幅が届かず開口が切れない(2026-08-24 検図 高-1 の後始末)
    gaps = [[round(q[0], 3), round(q[1], 3), hw] for q, hw in
            ((_proj_poly(gq[:2], pts), gq[2]) for gq in gaps)]
    by["Ita_Keidai"]["pts"] = [[round(u, 3), round(v, 3)] for u, v in pts]
    by["Ita_Keidai"]["gaps"] = gaps
    by["Ita_Keidai"].pop("gapU", None); by["Ita_Keidai"].pop("gapHalf", None)
    by["Ita_Keidai"]["_"] = ("境内の外周の**腰高の柵**【U ユーザー裁定 2026-09-07】。"
                             "**平場の輪郭から犬走り(`const.inubashiri`)ぶん内へ寄せて機械生成する** — "
                             "独立の座標を持たない(2026-08-23 検図 中-5)。"
                             "⚠ **回廊の基壇が東front なので東の張り出しには回さない**。"
                             "**開口は石段の頭と勝手口で自動に開く**(2026-08-24 検図 高-1)")


def derive_routes(d):
    """`from` を持つ動線の折れ線を、名指した道 + `tail` から**その場で組み立てる**。

    ⛔ 同じ座標を二重に持たない(規則4)。賄の動線は `kattemichi[西の勝手道]` そのものだったのに、
    json が同じ 28 点を写しており、勝手道を直しても動線が古いまま残る形だった
    (2026-09-06 検図4巡目 高1)。
    """
    src = {"kattemichi": dict((q["name"], q) for q in d.get("kattemichi", [])),
           "fumotomichi": dict((q["name"], q) for q in d.get("fumotomichi", []))}
    for rt in d.get("routes", []):
        if not rt.get("from"): continue
        kind, _, nm = rt["from"].partition(":")
        base = src.get(kind, {}).get(nm)
        if base is None:
            raise SystemExit("動線『%s』の from が引けない: %s" % (rt["name"], rt["from"]))
        rt["pts"] = [list(q) for q in base["pts"]] + [list(q) for q in rt.get("tail", [])]
        # 折返しの宣言も引き継ぐ(`tail` は末尾に継ぐので頂点の番号は変わらない)
        rt["switchbacks"] = list(base.get("switchbacks", []))


def route_fork(d, na, nb):
    """二本の動線が**分かれる最後の共有点**(二股)[世界座標]。無ければ None。

    ⚠ 二本は参道の階から二股まで重なり、中門から西でまた重なる(2本の共有区間がある)ので、
    「共有点」ではなく「**共有点のうち、次の点が食い違うもの**」で二股を同定する。
    """
    R = dict((rt["name"], rt) for rt in d.get("routes", []))
    a, b = R.get(na), R.get(nb)
    if not a or not b: return None
    PA = [tuple(q) for q in a["pts"]]
    PB = [tuple(q) for q in b["pts"]]
    for i, p in enumerate(PA[:-1]):
        if p not in PB: continue
        j = PB.index(p)
        if j + 1 >= len(PB): continue
        if PA[i + 1] != PB[j + 1]: return p
    return None


def gate_by_name(d, nm):
    """名で門を引く。⛔ 番号で指さない(門が増減した日に取り違える)。"""
    for gt in d["gates"]:
        if gt["name"] == nm: return gt
    raise SystemExit("門『%s』が無い" % nm)


def gate_face_u(d, nm, face):
    """門の**面の通り**[間] ── 芯 ± 桁行の半分。⛔ 面の u を json に書き写さない。

    ⚠ 2026-09-07 検図7巡目 低4 — 門の芯を犬走りからの従属値に改めたのに、その**面の通り**は
    旧値 23.600 / 21.600 のまま4箇所に literal で残り、27.3 mm ずつずれていた。
    面に取り付く物(袖塀・帯の輪郭・動線の折れ点・断面の切断線・見所)は**すべてここから引く**。
    """
    gt = gate_by_name(d, nm)
    hu = gt["plan"]["du"] / 2.0
    return gt["u"] + (hu if face == "東" else -hu)


def derive_gates(d, g):
    """門の芯と、**その面に取り付く物の通り**を組み立てる。⛔ 面の u を二重に持たない。

    ⭐ `gates[].uFrom` ── 門の芯そのものを平場の縁と犬走りからの従属値にする
    (⛔ 丸めた芯を置くと犬走りが 0.03 mm 足りない)。
    ⭐ `runs[].uFrom` / `gardens[].polyFrom` / `routes[].uFrom` / `sections[].atFrom` /
       `viewpoints[].uFrom` ── どれも門の面の通りを引く宣言。
    """
    ken = d["const"]["ken"]
    for gt in d["gates"]:
        uf = gt.get("uFrom")
        if not uf: continue
        te = [t for t in d["terraces"] if t["name"] == uf["terrace"]][0]
        us = [q[0] for q in terrace_poly_uv(te)]
        edge = min(us) if uf["side"] == "西" else max(us)
        cl = ((d["planting"]["clearance"] or {}).get(uf["clearanceOf"]) or {})[uf["clearance"]]
        hu = gt["plan"]["du"] / 2.0
        gt["u"] = edge + (cl / ken + hu if uf["face"] == "西" else -cl / ken - hu)

    def face_u(o):
        return gate_face_u(d, o["gate"], o["face"])

    for r in d["runs"]:
        uf = r.get("uFrom")
        if not uf: continue
        r["a"][0] = r["b"][0] = face_u(uf)
    for gd in d["gardens"]:
        pf = gd.get("polyFrom")
        if not pf: continue
        for fc in ("東", "西"):
            for i in pf.get(fc, []):
                gd["poly"][i][0] = gate_face_u(d, pf["gate"], fc)
    for rt in d.get("routes", []):
        uf = rt.get("uFrom")
        if not uf: continue
        for fc in ("東", "西"):
            for i in uf.get(fc, []):
                u = gate_face_u(d, uf["gate"], fc)
                v = g.V(rt["pts"][i][1]) if rt.get("world") else rt["pts"][i][1]
                rt["pts"][i][0] = g.W(u, v)[0] if rt.get("world") else u
    for sc in d.get("sections", []):
        af = sc.get("atFrom")
        if not af: continue
        x = g.W(face_u(af), 0.0)[0]
        sc["at"] = x
        for q in sc.get("line", []): q[0] = x
    for vp in d.get("viewpoints", []):
        uf = vp.get("uFrom")
        if not uf: continue
        vp["uv"][0] = face_u(uf)


def derive_zentei(d, g):
    """前庭の**従属値**をその場で組み立てる ── 木戸の芯の v・供待の北辺。

    ⛔ 丸めた値を json に持たない(2026-09-06 検図6巡目 低6/低13)。
    ・木戸の芯 = **縁台の塊の間の中央**(`tamagaki.kido.vFrom` が指す二基の向かい合う端の中央)
    ・供待の北辺 = **表参と御成の二股の点の通り**(`gardens[].northFrom`)
    """
    for gd in d.get("gardens", []):
        kd = ((gd.get("tamagaki") or {}).get("kido"))
        if kd and kd.get("vFrom"):
            vf = kd["vFrom"]
            pr = [p for p in d.get("props", []) if p["name"] == "縁台(床几)"]
            A = prop_rect_of(d, pr[0]["name"], vf["a"]) if pr else None
            B = prop_rect_of(d, pr[0]["name"], vf["b"]) if pr else None
            if A is None or B is None:
                raise SystemExit("木戸の `vFrom` が引けない: %s / %s" % (vf["a"], vf["b"]))
            end = {"北端": max, "南端": min}
            kd["uv"] = [kd["uv"][0],
                        (end[vf["aEnd"]](q[1] for q in A) + end[vf["bEnd"]](q[1] for q in B)) / 2.0]
        nf = gd.get("northFrom")
        if nf and nf.get("kind") == "routeFork":
            p = route_fork(d, nf["a"], nf["b"])
            if p is None:
                raise SystemExit("空地『%s』の `northFrom` の二股が引けない" % gd["name"])
            v = g.V(p[1])
            vs = [q[1] for q in gd["poly"]]
            mid = (min(vs) + max(vs)) / 2.0        # 北の辺 = 芯より北の頂点(⛔ 番号で指さない)
            for q in gd["poly"]:
                if q[1] > mid: q[1] = v


# 道の形の閾値(**検査の物差しであって設計値ではない**ので json に置かない)
HAIRPIN_DEG = 120.0     # これを超える折れは「引き返し」。九十九折の折返しだけが許される
MAIGI_DEG = (0.2, 3.0)  # 0.2°未満は通過点(共線)。この間は「迷い点」= 意図の読めない折れ


def path_polys(d):
    """検査に掛ける道 ── (系統, 名, 折れ線[世界座標], 脚ごとの幅[m] の列, 折返しの頂点, 止めるか)。

    ⭐ **幅は脚ごとに引く**(2026-09-06 検図5巡目 中6/中7)— 旧版は `rt["w"]` 一本だったので
    前庭の読み替え(`wByTerrace`)も門口(`gates[].monguchiKen`)も見ておらず、
    「道幅より短い脚」を過大に報告し、`wByTerrace` を外しても何も変わらなかった。
    """
    g = G(d)
    out = []

    def legw(rt, pts):
        """脚の中点が載る段・くぐる門から幅を引く。⛔ 一本の値で測らない。"""
        ws = []
        for i in range(len(pts) - 1):
            mx = ((pts[i][0] + pts[i + 1][0]) / 2.0, (pts[i][1] + pts[i + 1][1]) / 2.0)
            q = (g.U(mx[0]), g.V(mx[1]))
            ws.append(route_w(d, rt, terrace_at(d, g, q), at=q))
        return ws

    for rt in d.get("routes", []):
        pts = [(q[0], q[1]) if rt.get("world") else g.W(q[0], q[1]) for q in rt["pts"]]
        out.append(("動線", rt["name"], pts, legw(rt, pts), set(rt.get("switchbacks", [])), True))
    for sg in d.get("fumotomichi", []):
        pts = [tuple(q) for q in sg["pts"]]
        out.append(("麓道", sg["name"], pts, [sg.get("w")] * (len(pts) - 1),
                    set(sg.get("switchbacks", [])), True))
    for k in d.get("kattemichi", []):
        pts = [tuple(q) for q in k["pts"]]
        # ⚠ 西の勝手道は動線『賄』が同じ折れ線を **⛔ 側で** 掛けるので、ここは〔記録〕どまり。
        #   東の勝手道はどの動線からも参照されていないので**誰も止めない**が、
        #   線形を引き直すには通してよい回廊の裁定が要る(→ `_pending`)。⛔ 黙って通さず毎回刷る。
        out.append(("勝手道", k["name"], pts, [k.get("w")] * (len(pts) - 1),
                    set(k.get("switchbacks", [])), False))
    return out


def path_shape_check(d):
    """道の形が建つ形か ── **道幅より短い脚**・**引き返し**・**迷い点**。

    ⚠ 2026-09-06 検図4巡目 高1: 賄の動線に 1.00〜2.24m の脚が9本、引き返し角>120°が8点あった。
    **幅 2.70m の道が 1.00m の脚で折り返す形は建たない。**
    ⛔ 止めるのは「短い脚で引き返す」形だけ — 九十九折の折返しは正しい道の作りで、
    `switchbacks`(頂点の番号)に宣言してあり、かつ**両隣の脚が道幅以上**なら通す。
    短い脚・折返し・迷い点はそれぞれ〔記録〕として毎回刷る。戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    for kind, nm, pts, W, sw, gate in path_polys(d):
        L = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
             for i in range(len(pts) - 1)]
        wa = lambda i: W[i] if 0 <= i < len(W) else None          # 脚 i の道幅
        w = max([q for q in W if q] or [0]) or None                # 表示用(最も広い区間)
        short = [i for i, l in enumerate(L) if wa(i) and l < wa(i) - 1e-9]
        turn = []
        for i in range(1, len(pts) - 1):
            a, b, c = pts[i - 1], pts[i], pts[i + 1]
            v1 = (b[0] - a[0], b[1] - a[1]); v2 = (c[0] - b[0], c[1] - b[1])
            turn.append((i, abs(math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                                        v1[0] * v2[0] + v1[1] * v2[1])))))
        hp = [(i, a) for i, a in turn if a > HAIRPIN_DEG]
        mg = [(i, a) for i, a in turn if MAIGI_DEG[0] <= a < MAIGI_DEG[1]]
        tight, undecl = [], []
        for i, a in hp:
            legs = min(L[i - 1], L[i])
            wi = min([q for q in (wa(i - 1), wa(i)) if q] or [0])   # 折返しの両隣の狭いほうの道幅
            if wi and legs < wi - 1e-9: tight.append((i, a, legs, wi))
            elif i not in sw: undecl.append((i, a))
        if gate:
            bad += ["%s『%s』の頂点%d (%.2f, %.2f) は 引き返し角 %.0f° なのに脚が %.2f m しかない"
                    "(道幅 %.2f m)— 短い脚で折り返す形は建たない"
                    % (kind, nm, i, pts[i][0], pts[i][1], a, lg, wi) for i, a, lg, wi in tight]
            bad += ["%s『%s』の頂点%d (%.2f, %.2f) の引き返し角 %.0f° が宣言されていない"
                    "(九十九折なら `switchbacks` に頂点の番号を書く)"
                    % (kind, nm, i, pts[i][0], pts[i][1], a) for i, a in undecl]
        else:
            if tight:
                note.append("%s『%s』── **短い脚で折り返す**頂点が %d 点(最短の脚 %.2f m ／ 道幅 %.2f m): %s"
                            % (kind, nm, len(tight), min(q[2] for q in tight),
                               min(q[3] for q in tight),
                               "・".join("頂点%d" % q[0] for q in tight)))
            if undecl:
                note.append("%s『%s』── 宣言の無い引き返しが %d 点: %s"
                            % (kind, nm, len(undecl), "・".join("頂点%d" % i for i, _a in undecl)))
        if short:
            note.append("%s『%s』── 道幅より短い脚が %d 本(最短 %.2f m ／ その脚の道幅 %.2f m。"
                        "道幅は脚ごとに 段(`wByTerrace`)と門口(`monguchiKen`)から引く)"
                        % (kind, nm, len(short), min(L[i] for i in short),
                           wa(min(short, key=lambda i: L[i]))))
        if hp:
            note.append("%s『%s』── 引き返し(>%g°)が %d 点%s"
                        % (kind, nm, HAIRPIN_DEG, len(hp),
                           "(うち折返しの宣言 %d 点)" % len([i for i, _a in hp if i in sw]) if sw else ""))
        if mg:
            note.append("%s『%s』── 迷い点(%g〜%g°の折れ)が %d 点: %s"
                        % (kind, nm, MAIGI_DEG[0], MAIGI_DEG[1], len(mg),
                           "・".join("頂点%d (%.2f, %.2f) %.1f°" % (i, pts[i][0], pts[i][1], a)
                                     for i, a in mg[:6])))
    return bad, note


def _proj_poly(q, pts):
    """点を折れ線へ落とす。"""
    best, bp = 1e9, q
    for a, b in zip(pts, pts[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1.0
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / L2))
        p = [a[0] + dx * t, a[1] + dz * t]
        dd = math.hypot(q[0] - p[0], q[1] - p[1])
        if dd < best: best, bp = dd, p
    return bp


def _near_poly(q, pts, tol):
    """点が折れ線から tol[間] 以内にあるか。"""
    for a, b in zip(pts, pts[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1.0
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / L2))
        if math.hypot(q[0] - (a[0] + dx * t), q[1] - (a[1] + dz * t)) <= tol: return True
    return False


def terrace_poly_uv(te):
    """平場の輪郭を uv で返す。`uv`(境内)/`poly`(前庭)/矩形 の三形に対応。"""
    if te.get("uv"): return te["uv"]
    if te.get("poly"): return te["poly"]
    return [[te["u0"], te["v0"]], [te["u1"], te["v0"]],
            [te["u1"], te["v1"]], [te["u0"], te["v1"]]]


def terrace_poly(te, g):
    """段の平面。`poly`(uv)があればそれ、無ければ u0/v0/u1/v1 の矩形。2026-08-23 に前庭が多角形になった。"""
    if te.get("poly"):
        return [g.W(u, v) for u, v in te["poly"]]
    if te["kind"] == "rect":
        return [g.W(te["u0"], te["v0"]), g.W(te["u1"], te["v0"]),
                g.W(te["u1"], te["v1"]), g.W(te["u0"], te["v1"])]
    return [g.W(u, v) for u, v in te["uv"]]


def in_poly(pt, P):
    x, z = pt; c = False; j = len(P) - 1
    for i in range(len(P)):
        if (P[i][1] > z) != (P[j][1] > z) and \
           x < (P[j][0] - P[i][0]) * (z - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0]:
            c = not c
        j = i
    return c


_LAND = {}


def slope_lands(d, near, nx, nz, top, edge_dv):
    """縁から外へ 1:batterFill で降ろした法面が **現地形に着地するか**(スキル §3b 関門3)。

    着地しない縁は崖の上に載っているので、法面ではなく**土留めで受ける**しかない。
    そこへ法面を描くと、法尻に1〜2mの垂直面が宙に残る(2026-08-23 検図 高-3)。
    """
    k = (round(near[0], 1), round(near[1], 1))
    if k in _LAND: return _LAND[k]
    bf = d["const"]["batterFill"]
    reach = d["const"].get("featherCap", 12.0)
    ok = False
    t = 0.2
    while t <= reach + 1e-9:
        h = dem_h(near[0] + nx * t, near[1] + nz * t)
        if h is None: break
        if top - t / bf <= h + 0.05: ok = True; break
        t += 0.2
    _LAND[k] = ok
    return ok


def design_y(d, g, x, z):
    """設計地盤。段(平場)・石段の通路の中なら面の高さ、縁の外は法面、届かなければ None。"""
    # ⚠ **平場が石段より優先**(2026-08-24 検図 中-5)。逆にすると、坂の帯が平場へ食い込んだ分だけ
    #    面に溝が掘れる(女坂の頭で最大2.19m)。坂は平場の外だけを受け持つ。
    for te in d["terraces"]:
        if in_poly((x, z), terrace_poly(te, g)): return te["y"]
    sy = _stair_y(d, g, x, z)
    if sy is not None: return sy
    # 法面(バッター)— 土留めの無い縁は 盛土1:1.5 / 切土1:1 で現地形へ摺り付ける(§3b)
    nat = dem_h(x, z)
    if nat is None: return None
    best = None
    for te in d["terraces"]:
        P_ = terrace_poly(te, g)
        dv = te["y"] - nat
        if abs(dv) < 0.05: continue
        # ⚠ reach を「検査点の高さ」から出すと斜面で永久に着地しない(2026-08-23 検図)。
        #    縁そのものの落差から出し、featherCap で頭打ちにする。
        reach = None
        dmin = 1e9; near = None
        for i in range(len(P_)):
            ax, az = P_[i]; bx, bz = P_[(i + 1) % len(P_)]
            ddx, ddz = bx - ax, bz - az
            L2 = ddx * ddx + ddz * ddz or 1.0
            t = max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
            qx, qz = ax + ddx * t, az + ddz * t
            dd = math.hypot(x - qx, z - qz)
            if dd < dmin: dmin, near = dd, (qx, qz)
        if near is None: continue
        # 縁そのものの落差でリーチを決める(検査点の落差ではない)
        edge_nat = dem_h(near[0], near[1])
        if edge_nat is None: continue
        edge_dv = te["y"] - edge_nat
        # ⚠ 土留めが受けている縁は法面を出さない(壁で立つ)。断面 §3c と同じ仕分け
        if on_wall(d, g, near[0], near[1]): continue
        cap = d["const"].get("featherCap", 12.0)
        if edge_dv > 0.05 and not slope_lands(d, near, (x - near[0]) / (dmin or 1.0),
                                              (z - near[1]) / (dmin or 1.0), te["y"], edge_dv):
            continue          # 崖の上の縁 — 法面が着地しないので土留めで受ける(法面を出さない)
        if edge_dv > 0.05:
            # 盛土の法面 ── **一定勾配 1:batterFill**。⚠ 旧式は reach で線形補間していたので
            #   外の地形が緩いと法尻に垂直の段差が残った(2026-08-23 検図 高-3)。
            #   広がりは **現地形に当たるまで**(featherCap で頭打ち)。当たらない縁は
            #   slope_lands が先に弾いて土留めへ回す。
            bf = d["const"]["batterFill"]
            if dmin > cap: continue
            y = te["y"] - dmin / bf
            if y <= nat + 0.05: continue                  # 現地形に着地した
            if best is None or y > best: best = y
        elif edge_dv < -0.05:
            # 切土の縁 ── **一定勾配 1:batterCut** で地山を切り上げる(const.batterCut を使う)
            bc = d["const"].get("batterCut", 1.0)
            if dmin > cap: continue
            y = te["y"] + dmin / bc
            if y >= nat - 0.05: continue                  # 地山に届いた
            best = y if best is None else min(best, y)
    return best


def cutfill_name(d, g, cx, cz, y):
    """切盛の集計でその点が属する**面の名**。⛔ 図と検査で別の名前を作らない(検図9巡目 低5)。"""
    if _stair_y(d, g, cx, cz) is not None: return "石段(男坂・女坂・参道の階)"
    return "境内(山上)" if y > 20 else "前庭(男坂下)"


def saichigai_check(d, g):
    """造成が**社地の外**へ及んでいないか(名簿つき)。

    ⭐ **2026-09-07 検図9巡目 低5 で起こした。**`sando._` は参道を「造成しない」と宣言するのに、
    参道の階の下端の法尻が社地の境を跨いでいた(切盛図は社地の内外を分けて数えていなかった)。
    ⛔ **`kaidans[参道の階].yBot` を動かして黙らせない** — 下端は着地する地盤から決まる従属値。
    ⛔ 名簿(`terrainCheck.saichiGai.roster`)と実物を**両方向**に突き合わせる:
    名簿に無い面が外へ出たら⛔、名簿にあるのに出ていなければ死んだ名簿として⛔(規則19)。
    ⚠ 走査は社地の外だけ、幅は法面のリーチ `const.featherCap` まで(それより先へは届かない)。
    """
    P = d["polygon"]
    cap = d["const"].get("featherCap", 12.0)
    sg = (d.get("terrainCheck") or {}).get("saichiGai") or {}
    bad, note = [], []
    if sg.get("roster") is None:
        bad.append("社地の外への造成を許す面の名簿 `terrainCheck.saichiGai.roster` の宣言が無い — "
                   "宣言が無ければ外へ出ても鳴らない(規則19)")
    xs = [q[0] for q in P]; zs = [q[1] for q in P]
    stp = 2
    tally = {}
    for z in range(int(min(zs) - cap), int(max(zs) + cap), stp):
        for x in range(int(min(xs) - cap), int(max(xs) + cap), stp):
            cx, cz = x + stp / 2.0, z + stp / 2.0
            if in_poly((cx, cz), P): continue
            y = design_y(d, g, cx, cz)
            if y is None: continue
            nat = dem_h(cx, cz)
            if nat is None: continue
            # ⛔ **差の小さいセルを落とさない** — 落とすと切盛図の『うち社地外』と数が食い違う
            #    (図は設計地盤が引かれたセルを数える)。⭕ 二つの表で同じ数を刷る
            t_ = tally.setdefault(cutfill_name(d, g, cx, cz, y), [0, 0.0, 0.0])
            t_[0] += stp * stp
            if y > nat: t_[1] += (y - nat) * stp * stp
            else:       t_[2] += (nat - y) * stp * stp
    bad += roster_guard(sg.get("roster"), sorted(tally.keys()),
                        "社地の外への造成を許す面の名簿", "`terrainCheck.saichiGai.roster`")
    note.append("**設計地盤が社地の外まで引かれている面** %d 件(走査は社地の外・法面のリーチ "
                "%.0f m まで・刻み %d m。⛔ 差の小さいセルも落とさない — 切盛図の『うち社地外』"
                "と同じ数を刷る)【算出】" % (len(tally), cap, stp))
    for nm in sorted(tally):
        t_ = tally[nm]
        note.append("『%s』が社地の外へ %d m²(盛 %.1f ／ 切 %.1f m³)【算出 — "
                    "⛔ 数を指図の文章に写さない。切盛図の『うち社地外』と同じ物差し】"
                    % (nm, t_[0], t_[1], t_[2]))
    return bad, note


def kirimori_svg(d, kan, x0, x1, z0, z1, W=900.0):
    """§3b 切盛図 — Δ = 設計地盤 − 現況。暖色=盛土 / 寒色=切土 / 無彩=±0.3m。"""
    g = G(d)
    pr = Proj(x0, x1, z0, z1, W=W, pad=0.0, top=26.0, bottom=30.0)
    o = _sv(pr.W, pr.H, "切盛図")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))
    stp = 2
    tally = {}
    for z in range(int(z0), int(z1), stp):
        for x in range(int(x0), int(x1), stp):
            cx, cz = x + stp / 2.0, z + stp / 2.0
            y = design_y(d, g, cx, cz)
            if y is None: continue
            nat = dem_h(cx, cz)
            if nat is None: continue
            dv = y - nat
            col = "#E9E5D6"
            for c, th in CUTFILL:
                if (th > 0 and dv >= th) or (th < 0 and dv <= th): col = c; break
            else:
                col = "#EFD9C8" if dv > 0.3 else ("#D4DEE6" if dv < -0.3 else "#E9E5D6")
            o.append(R(pr.X(x), pr.Y(z + stp), pr.L(stp) + 0.6, pr.L(stp) + 0.6, fill=col))
            nm = cutfill_name(d, g, cx, cz, y)
            t_ = tally.setdefault(nm, [0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0])
            t_[0] += stp * stp
            if dv > 0: t_[1] += dv * stp * stp; t_[3] = max(t_[3], dv)
            else:      t_[2] += -dv * stp * stp; t_[4] = max(t_[4], -dv)
            # ⭐ **社地の外へ出た分を別に数える**(2026-09-07 検図9巡目 低5)。
            #    指図は参道を「造成しない」と宣言しているのに、階の下端の法尻が境を跨いでいた
            if not in_poly((cx, cz), d["polygon"]):
                t_[5] += stp * stp
                if dv > 0: t_[6] += dv * stp * stp
                else:      t_[7] += -dv * stp * stp
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in d["polygon"]], stroke="var(--ink)", sw=1.6, close=True))
    o += cut_lines(d, pr.X, pr.Y, pr.L)
    o.append(T(6, 15, kan + "　切盛図 ─ 設計地盤 − 現況(暖色=盛土 ／ 寒色=切土 ／ 無彩=±0.3 m)",
               fs=12.5, fill="var(--dim)"))
    yy = 40.0
    for nm, t_ in tally.items():
        o.append(T(pr.W - 6, yy, "%s: %d m²　盛土 %.0f m³(最大 %.2f)　切土 %.0f m³(最大 %.2f)"
                   "　うち社地外 %d m²(盛 %.1f ／ 切 %.1f m³)"
                   % (nm, t_[0], t_[1], t_[3], t_[2], t_[4], t_[5], t_[6], t_[7]),
                   fs=10.5, anchor="end", fill="var(--dim)"))
        yy += 15
    tot = sum(t_[1] for t_ in tally.values()) - sum(t_[2] for t_ in tally.values())
    o.append(T(pr.W - 6, yy, "差引 %+.0f m³(正なら客土が要る／負なら残土が出る)" % tot, fs=10.5,
               anchor="end", fill="var(--shu)"))
    o += sando_band(d, pr.X, pr.Y, pr.L); o += torii_marks(d, pr.X, pr.Y)   # 参道と鳥居(検図 2026-09-06)
    o.append(ENDSVG)
    return "\n".join(o)


def dousen_svg(d, kan, W=900.0):
    """§3d 動線図 — 系統別に色を変え、延長・昇り・越える段数を出す。"""
    g = G(d)
    P = d["polygon"]
    ext = P + [tuple(q) if rt.get("world") else g.W(q[0], q[1]) for rt in d.get("routes", []) for q in rt["pts"]]
    pr = Proj(min(q[0] for q in ext), max(q[0] for q in ext),           # 起点(二ノ鳥居)まで窓に入れる(検図 2026-09-06)
              min(q[1] for q in ext), max(q[1] for q in ext), W=W, pad=20.0, top=26.0, bottom=30.0)
    o = _sv(pr.W, pr.H, "動線図")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in P], stroke="var(--ink)", sw=1.4,
                fill="var(--pl-slope)", op=0.4, close=True))
    kp = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in kp], fill="var(--pl-main)", op=0.7,
                stroke="var(--ink)", sw=1.0, close=True))
    zt = d["terraces"][1]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in terrace_poly(zt, g)],
                fill="var(--pl-suso)", op=0.8, stroke="var(--ink)", sw=0.9, close=True))
    rows = []
    for rt in d.get("routes", []):
        pts = [(q[0], q[1]) if rt.get("world") else g.W(q[0], q[1]) for q in rt["pts"]]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in pts], stroke=rt["color"], sw=3.2, op=0.95))
        for (x, z) in pts:
            o.append(R(pr.X(x) - 2, pr.Y(z) - 2, 4, 4, fill=rt["color"]))
        L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                for i in range(len(pts) - 1))
        mx, mz = pts[len(pts) // 2]
        o.append(T(pr.X(mx), pr.Y(mz) - 6, rt["name"], fs=11, anchor="middle", fill=rt["color"]))
        # 昇りと越える段数は via の石段から算出(手書きの値を持たない。2026-08-23 検図)
        KD = {k["name"]: k for k in d["kaidans"]}
        nstep = sum(KD[v]["steps"] for v in rt.get("via", []) if v in KD)
        # ⚠ **昇りは経路の設計地盤から積む**(2026-08-23 検図 高-4)。via の石段だけを足すと
        #    山麓からの斜路の昇り(賄)が表に出ない。
        rise, prev_y = 0.0, None
        for i in range(len(pts) - 1):
            L0 = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for q in range(max(1, int(L0 / 2.0)) + 1):
                t = q / max(1, int(L0 / 2.0))
                x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t
                z = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
                y = design_y(d, g, x, z)
                if y is None: y = dem_h(x, z)
                if y is None: continue
                if prev_y is not None and y > prev_y: rise += y - prev_y
                prev_y = y
        rows.append((rt["name"], rt["kind"], L, rise, nstep, rt.get("_", "")))
    # 山麓の勝手道(動線の一部。json は2本持つ)
    for k in d.get("kattemichi", []):
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in k["pts"]],
                    stroke="var(--take)", sw=2.2, dash="7 4", op=0.85))
        mx_, mz_ = k["pts"][len(k["pts"]) // 2]
        o.append(T(pr.X(mx_) + 5, pr.Y(mz_), k["name"], fs=10, fill="var(--take)"))
    # 石段を重ねる(どこで段を越えるか)
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in pts], stroke="var(--ishi)", sw=6.0, op=0.55))
    o.append(T(6, 15, kan + "　動線図 ─ 表参(参詣)／御成／勝手(賄)／社務", fs=12.5, fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o), rows


def _seg_x(p1, p2, p3, p4):
    """線分 p1p2 と p3p4 の交点(無ければ None)。"""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-12: return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def route_pierce(d, g):
    """動線が囲い・棟・土留めを貫通していないか(スキル §3d)。

    ⚠ **検査に落としていない不変条件は必ず壊れる。** 御成が回廊の躯体を通る欠陥は
    2026-08-23 に直したのに 2026-08-24 の検図で再発していた。
    """
    obs = []
    for r in d["runs"]:
        if r["kind"] in ("透塀", "板塀", "柵", "回廊"):
            for a, b in run_segs(r):
                obs.append((r["name"], g.W(*a), g.W(*b)))
    for w in d["terraceWalls"]:
        for a, b in run_segs(w):
            obs.append((w["name"], g.W(*a), g.W(*b)))
    rects = [(m["name"], m["u0"], m["v0"], m["u0"] + m["du"], m["v0"] + m["dv"])
             for m in d["munes"] if m["yaku"] != "接続"]
    out = []
    for rt in d.get("routes", []):
        pts = [(q[0], q[1]) if rt.get("world") else g.W(q[0], q[1]) for q in rt["pts"]]
        for i in range(len(pts) - 1):
            for nm, a, b in obs:
                if _seg_x(pts[i], pts[i + 1], a, b): out.append((rt["name"], nm))
            for nm, u0, v0, u1, v1 in rects:
                P = [g.W(u0, v0), g.W(u1, v0), g.W(u1, v1), g.W(u0, v1)]
                for k in range(4):
                    if _seg_x(pts[i], pts[i + 1], P[k], P[(k + 1) % 4]): out.append((rt["name"], nm)); break
    seen, uniq = set(), []
    for q in out:
        if q in seen: continue
        seen.add(q); uniq.append(q)
    return uniq


def routes_table(rows):
    tr = "".join("<tr><td>%s</td><td>%s</td><td>%.0f m</td><td>%+.1f m</td><td>%d 段</td>"
                 "<td class='note'>%s</td></tr>" % (a, b, c, dd, e, inline(f)) for a, b, c, dd, e, f in rows)
    return ('<div class="tw"><table><thead><tr><th>動線</th><th>系統</th><th>延長</th><th>昇り</th>'
            "<th>越える段</th><th class='note'>注記</th></tr></thead><tbody>" + tr + "</tbody></table></div>")


def draw_bands(d, g, PX, PY):
    """社叢 帯1〜3 の**面**を社地の全図へ落とす(『帯の面が図に無い』— 庭方2巡目 高3)。

    ⛔ セルを一つずつ描かない — 行ごとに走りを束ねる(図版が肥る)。
    戻り値 (塗り, 銘)。**銘は後から重ねる** — 平場や帯4の塗りに隠れるため。
    """
    cells, _ = band_scan(d, g)
    step = d["planting"]["bandDef"]["stepKen"]
    op = {1: 0.34, 2: 0.22, 3: 0.12}
    o, lab = [], []
    for b in sorted(cells):
        rows = {}
        for u, v in cells[b]: rows.setdefault(int(round(v / step)), []).append(u)
        for j, us in rows.items():
            us.sort()
            a = prev = us[0]
            for u in us[1:] + [None]:
                if u is not None and abs(u - prev - step) < 1e-6:
                    prev = u; continue
                x0, z0 = g.W(a - step / 2.0, j * step - step / 2.0)
                x1, z1 = g.W(prev + step / 2.0, j * step + step / 2.0)
                o.append(R(PX(min(x0, x1)), PY(max(z0, z1)),
                           abs(PX(x1) - PX(x0)) + 0.4, abs(PY(z0) - PY(z1)) + 0.4,
                           fill="var(--take)", op=op.get(b, 0.2)))
                if u is not None: a = prev = u
        if cells[b]:
            cu = sum(q[0] for q in cells[b]) / len(cells[b])
            cv = sum(q[1] for q in cells[b]) / len(cells[b])
            # ⚠ 帯は三日月形なので重心が帯の外に出る。**帯の中で重心に最も近いセル**へ置く
            nu, nv = min(cells[b], key=lambda q: (q[0] - cu) ** 2 + (q[1] - cv) ** 2)
            x, z = g.W(nu, nv)
            lab.append(T(PX(x), PY(z), "社叢 帯%d" % b, fs=10.5, anchor="middle", fill="var(--ink)"))
    return o, lab


def run_tamagaki(d, r):
    """run が `hFrom` で名指す玉垣の定義(丈・柱の芯々・貫の段数・立子)を引く。

    ⭐ **境内の外周の柵は前庭の玉垣と同じ作り**【ユーザー裁定 2026-09-07】なので、
    ⛔ **丈も柱の刻みも独立に持たない** — `gardens[…].tamagaki` が唯一の正典で、
    玉垣を動かせば柵も動く(規則4)。⛔ 宣言の指し先が無ければ止める(規則19)。
    """
    hf = r.get("hFrom")
    if not hf: return None
    gd = [q for q in d["gardens"] if q["name"] == hf["garden"]]
    if not gd:
        raise SystemExit("run『%s』の `hFrom` が指す区『%s』が無い" % (r["name"], hf["garden"]))
    o = gd[0]
    for seg in hf["field"].split("."):
        if not isinstance(o, dict) or seg not in o:
            raise SystemExit("run『%s』の `hFrom.field`『%s』が指図に無い" % (r["name"], hf["field"]))
        o = o[seg]
    return gd[0]["tamagaki"], o


def run_take_m(d, r):
    """run の丈[m]。⛔ 宣言(`hFrom`)を持つ物だけが値を持ち、他は None(図が『—』を刷る)。"""
    q = run_tamagaki(d, r)
    return None if q is None else q[1]


# ---------------------------------------------------------------- 其一 社地
def shachi_svg(d, kan="其一"):
    g = G(d)
    P = d["polygon"]
    # 窓は参道と鳥居まで含める(二ノ鳥居が画面外だった・検図 2026-09-06)
    ext = list(d["sando"]["pts"]) + [t["pos"] for t in d["torii"] if t.get("pos")]
    xs = [p[0] for p in P] + [q[0] for q in ext]; zs = [p[1] for p in P] + [q[1] for q in ext]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), W=900.0, pad=22.0, top=26.0, bottom=30.0)
    o = _sv(pr.W, pr.H, "社地の全図")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))

    # 社地
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in P], stroke="var(--ink)", sw=1.6,
                fill="var(--pl-slope)", op=0.55, close=True))
    # 社叢の帯(社地の内側を薄く)
    o.append(T(pr.X(-600), pr.Y(760), "社叢(造成しない)", fs=11, fill="var(--take)"))
    # 社叢 帯1〜3 の面(法肩からの下りの割合で切る。走査は band_scan)
    _bfill, _blab = draw_bands(d, g, pr.X, pr.Y)
    o += _bfill
    # 社叢 帯4(多角形を持つ帯)と 境内の立木3区・前庭の木を**面**で(2026-09-06 庭方の設計)
    for _b in d["slopeBands"]:
        if not _b.get("uv"): continue
        _w = [g.W(u, v) for u, v in _b["uv"]]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in _w], fill="var(--take)", op=0.18,
                    stroke="var(--take)", sw=1.0, dash="9 4", close=True))
        o.append(T(pr.X(sum(q[0] for q in _w) / len(_w)), pr.Y(sum(q[1] for q in _w) / len(_w)),
                   "社叢 帯%d" % _b["band"], fs=10, anchor="middle", fill="var(--take)"))
    for _gd in d["gardens"]:
        _P = garden_poly(_gd)
        if not _P or "林" not in _gd.get("kind", ""): continue
        _w = [g.W(u, v) for u, v in _P]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in _w], fill="var(--niwa)", op=0.75,
                    stroke="var(--take)", sw=0.8, close=True))

    # 境内の平場
    kp = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in kp], stroke="var(--ink)", sw=1.3,
                fill="var(--pl-main)", op=0.85, close=True))
    # 前庭
    zt = d["terraces"][1]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in terrace_poly(zt, g)],
                fill="var(--pl-suso)", stroke="var(--ink)", sw=1.0, op=0.9, close=True))

    # 透塀・回廊・社殿
    for r in d["runs"]:
        if r["kind"] not in ("透塀", "回廊"): continue
        w0 = g.W(*r["a"]); w1 = g.W(*r["b"])
        col = "var(--shu)" if r["kind"] == "透塀" else "var(--roka)"
        o.append(LN(pr.X(w0[0]), pr.Y(w0[1]), pr.X(w1[0]), pr.Y(w1[1]), stroke=col, sw=2.0))
    for m in d["munes"]:
        if m["yaku"] not in ("社殿",): continue
        w0 = g.W(m["u0"], m["v0"]); w1 = g.W(m["u0"] + m["du"], m["v0"] + m["dv"])
        o.append(R(pr.X(w0[0]), pr.Y(w1[1]), pr.X(w1[0]) - pr.X(w0[0]), pr.Y(w0[1]) - pr.Y(w1[1]),
                   fill="var(--shu)", op=0.85))
    for r in d["runs"]:                                  # 回廊(run が正典)
        if not r.get("mune"): continue
        bw = r.get("bari", 2) / 2.0
        w0 = g.W(r["a"][0] - bw, r["a"][1]); w1 = g.W(r["b"][0] + bw, r["b"][1])
        o.append(R(pr.X(min(w0[0], w1[0])), pr.Y(max(w0[1], w1[1])),
                   abs(pr.X(w1[0]) - pr.X(w0[0])), abs(pr.Y(w0[1]) - pr.Y(w1[1])),
                   fill="var(--roka)", op=0.85))

    # 石段(折れ線対応)
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in pts], stroke="var(--ishi)", sw=5.0, op=0.9))
        mid = pts[len(pts) // 2]
        o.append(T(pr.X(mid[0]), pr.Y(mid[1]) - 7, k["name"].split("(")[0], fs=10.5, anchor="middle", fill="var(--ink)"))

    # 勝手道(十坊・別当の側から山上へ上がる道。2026-08-23 追加)
    for seg in d.get("kattemichi", []):
        kp = [(pr.X(x), pr.Y(z)) for x, z in seg["pts"]]
        o.append(PL(kp, stroke="var(--take)", sw=3.0, op=0.9, dash="9 5"))
        o.append(T(kp[0][0] + 6, kp[0][1] + 4, seg["name"], fs=10, fill="var(--take)"))

    # 麓道(山裾を回る小道。**一周しない** — 常明院で行き止まり)
    for seg in d.get("fumotomichi", []):
        fp = [(pr.X(x), pr.Y(z)) for x, z in seg["pts"]]
        o += road_draw(seg, pr.X, pr.Y, pr.L)
        o.append(PL(fp, stroke="var(--ink)", sw=0.6, dash="2 4", op=0.5))
    # 行き止まりの印
    fz = [s2 for s2 in d.get("fumotomichi", []) if "終端" in s2["name"]]
    if fz:
        ex, ez = fz[0]["pts"][-1]
        o.append(LN(pr.X(ex) - 5, pr.Y(ez) - 5, pr.X(ex) + 5, pr.Y(ez) + 5, stroke="var(--shu)", sw=1.6))
        o.append(LN(pr.X(ex) - 5, pr.Y(ez) + 5, pr.X(ex) + 5, pr.Y(ez) - 5, stroke="var(--shu)", sw=1.6))
        o.append(T(pr.X(ex) - 9, pr.Y(ez) + 4, "行止", fs=10, anchor="end", fill="var(--shu)"))
    # 参道(実幅の帯 + 芯線)
    o += sando_band(d, pr.X, pr.Y, pr.L)
    # 二ノ鳥居
    for t in d["torii"]:
        if not t["pos"]: continue
        x, z = t["pos"]
        o.append(LN(pr.X(x) - 6, pr.Y(z), pr.X(x) + 6, pr.Y(z), stroke="var(--shu)", sw=2.4))
        o.append(LN(pr.X(x) - 4, pr.Y(z) + 4, pr.X(x) - 4, pr.Y(z) - 4, stroke="var(--shu)", sw=1.6))
        o.append(LN(pr.X(x) + 4, pr.Y(z) + 4, pr.X(x) + 4, pr.Y(z) - 4, stroke="var(--shu)", sw=1.6))
        o.append(T(pr.X(x) + 9, pr.Y(z) + 3, t["name"], fs=10.5, fill="var(--shu)"))

    # 参道沿い(柵・林縁・高木の縁の線)と 点景(立札)
    _rs = d["sando"].get("roadside")
    if _rs:
        _w = _rs["west"]; _fe = _rs["takagiEdgeLine"]["fromEdge"]
        _r0 = edge_offset(d, _fe, _w["rinenKen"][0]); _r1 = edge_offset(d, _fe, _w["rinenKen"][1])
        _ring = [g.W(*q) for q in (_r0[0], _r0[1], _r1[1], _r1[0])]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in _ring], fill="var(--niwa)", op=0.85,
                    stroke="var(--take)", sw=0.7, close=True))
        _tl = [g.W(q[0], q[1]) for q in _rs["takagiEdgeLine"]["uv"]]
        o.append(LN(pr.X(_tl[0][0]), pr.Y(_tl[0][1]), pr.X(_tl[1][0]), pr.Y(_tl[1][1]),
                    stroke="var(--take)", sw=1.1, dash="8 3"))
        o.append(T(pr.X(_tl[1][0]) + 5, pr.Y(_tl[1][1]) - 4, "高木の縁の線", fs=9.5, fill="var(--take)"))
    for _r in d["runs"]:
        if _r["kind"] != "柵" or not _r.get("fromEdge"): continue
        _a = g.W(*_r["a"]); _b2 = g.W(*_r["b"])
        o.append(LN(pr.X(_a[0]), pr.Y(_a[1]), pr.X(_b2[0]), pr.Y(_b2[1]),
                    stroke="var(--hei)", sw=1.6, dash="2 2"))
        o.append(T(pr.X((_a[0] + _b2[0]) / 2) - 5, pr.Y((_a[1] + _b2[1]) / 2), _r["name"],
                   fs=9.5, anchor="end", fill="var(--hei)"))
    for _nm, _u0, _v0, _u1, _v1 in fumiishi_rects(d):
        _q = [g.W(_u0, _v0), g.W(_u1, _v1)]
        o.append(R(pr.X(min(_q[0][0], _q[1][0])), pr.Y(max(_q[0][1], _q[1][1])),
                   abs(pr.X(_q[1][0]) - pr.X(_q[0][0])), abs(pr.Y(_q[0][1]) - pr.Y(_q[1][1])),
                   fill="none", stroke="var(--ishi)", sw=1.0))
    for _pp in d["props"]:
        if not _pp.get("uv") or "立札" not in _pp["name"]: continue
        for _u, _v in _pp["uv"]:
            _x, _z = g.W(_u, _v)
            o.append(LN(pr.X(_x), pr.Y(_z), pr.X(_x), pr.Y(_z) - 8, stroke="var(--ink)", sw=1.2))
            o.append(R(pr.X(_x) - 1.5, pr.Y(_z) - 11, 6.0, 4.0, fill="var(--paper)",
                       stroke="var(--ink)", sw=0.8))
            o.append(T(pr.X(_x) + 8, pr.Y(_z) - 8, _pp["name"], fs=9.5, fill="var(--ink)"))

    # 隣地
    for nb in d["neighbors"]:
        if "polygon" not in nb: continue
        Q = nb["polygon"]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in Q], stroke="var(--dim)", sw=1.0,
                    dash="4 3", fill="var(--paper)", op=0.35, close=True))
        cx = sum(p[0] for p in Q) / len(Q); cz = sum(p[1] for p in Q) / len(Q)
        o.append(T(pr.X(cx), pr.Y(cz), nb["name"].split(" ")[-1], fs=11, anchor="middle", fill="var(--dim)"))

    o += _blab                                    # 帯の銘は塗りの後から重ねる
    # 断面の切断線
    o += cut_lines(d, pr.X, pr.Y, pr.L,
                   clip=(14.0, pr.top + 10.0, pr.W - 14.0, pr.top + pr.zh - 6.0))
    # 注記
    o.append(T(6, 15, kan + "　社地 ─ 社叢の中の明地に建つ", fs=12.5, fill="var(--dim)"))
    o.append(T(pr.W - 6, 15, "北が上 ／ 東が右", fs=11, anchor="end", fill="var(--dim)"))
    kc = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
    ccx = sum(p[0] for p in kc) / len(kc); ccz = sum(p[1] for p in kc) / len(kc)
    o.append(T(pr.X(ccx), pr.Y(ccz) + 34, "境内(山上)", fs=12, anchor="middle", fill="var(--ink)"))
    o.append(T(pr.X(-443), pr.Y(858) + 4, "前庭", fs=11, anchor="middle", fill="var(--ink)"))
    # 縮尺
    y = pr.H - 14
    o.append(LN(14, y, 14 + pr.L(100), y, stroke="var(--dim)", sw=1.2))
    o.append(T(14 + pr.L(100) / 2, y - 4, "100 m", fs=10.5, anchor="middle"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其二 境内 平面
def keidai_svg(d, u0, u1, v0, v1, title, W=900.0):
    g = G(d)
    ken = d["const"]["ken"]

    def inwin(a, b, pad=3.0):
        return not (max(a[0], b[0]) < u0 - pad or min(a[0], b[0]) > u1 + pad
                    or max(a[1], b[1]) < v0 - pad or min(a[1], b[1]) > v1 + pad)

    lp = LProj(u0, u1, v0, v1, W=W, top=26.0, bottom=24.0)
    o = _sv(lp.W, lp.H, title)
    o.append(R(0, 0, lp.W, lp.H, fill="var(--paper2)"))

    # 間グリッド
    for u in range(int(math.ceil(u0)), int(u1) + 1):
        if u % 5: continue
        o.append(LN(lp.X(u), lp.top, lp.X(u), lp.top + lp.vh, stroke="var(--grid)", sw=0.5, op=0.7))
    for v in range(int(math.ceil(v0)), int(v1) + 1):
        if v % 5: continue
        o.append(LN(0, lp.Y(v), lp.W, lp.Y(v), stroke="var(--grid)", sw=0.5, op=0.7))

    # 社叢(多角形を持つ帯)── 平場より下に敷く
    o += draw_planting(d, lp, inwin)
    # 境内の平場
    o.append(PL([(lp.X(u), lp.Y(v)) for u, v in d["terraces"][0]["uv"]],
                stroke="var(--ink)", sw=1.3, fill="var(--pl-main)", op=0.55, close=True))
    # 前庭
    zt = d["terraces"][1]
    o.append(PL([(lp.X(u), lp.Y(v)) for u, v in (zt.get("poly") or [
        [zt["u0"], zt["v0"]], [zt["u1"], zt["v0"]], [zt["u1"], zt["v1"]], [zt["u0"], zt["v1"]]])],
        fill="var(--pl-suso)", close=True,
                     stroke="var(--ink)", sw=1.0, op=0.75))
    # 白洲・中庭・境内の立木(2026-09-01 是正 — 立木の帯を白洲と同じ砂利色で塗っていたため
    #   検図で「庭の種別が見分けられない」と指摘された。kind に「林」が付くものは緑系で塗り分ける)
    for gd in d["gardens"]:
        Pg = garden_poly(gd)
        if not Pg: continue
        us = [q[0] for q in Pg]; vs = [q[1] for q in Pg]
        if not inwin([min(us), min(vs)], [max(us), max(vs)]): continue
        is_forest = "林" in gd.get("kind", "") or "木" in gd.get("kind", "")
        if gd.get("noPlant"):                     # 空地(供待)── 塗らない・破線で囲うだけ
            o.append(PL([(lp.X(u), lp.Y(v)) for u, v in Pg], close=True, fill="none",
                        stroke="var(--dim)", sw=1.0, dash="6 4"))
        else:
            o.append(PL([(lp.X(u), lp.Y(v)) for u, v in Pg], close=True,
                        fill="var(--niwa)" if is_forest else "var(--shirasu)",
                        stroke="var(--take)" if is_forest else "var(--dim)", sw=0.8,
                        op=0.45 if is_forest else 0.9))
        o.append(T(lp.X(sum(us) / len(us)), lp.Y(sum(vs) / len(vs)) + 4,
                   gd["name"], fs=11, anchor="middle", fill="var(--dim)"))
    o += draw_edge_understory(d, lp)
    # 板塀・柵 ── **開口で切る**(2026-08-24 検図 高-1: 宣言した開口が図に一つも出ていなかった)
    #  ⭐ **姿で描き分ける**【ユーザー裁定 2026-09-07 — 境内の囲いは腰高の柵】。板塀は太い破線、
    #     柵は細い点線(其一の麓道の柵と同じ描き方)。⛔ 種別で描き分けないと、
    #     裁定で板塀を柵へ替えても図が同じ姿のままになる(規則19)。
    for r in d["runs"]:
        if r["kind"] not in ("板塀", "柵"): continue
        if r.get("pts") is None and (r["a"] is None or not inwin(r["a"], r["b"])): continue
        saku = r["kind"] == "柵"
        for a, b in run_segs(r):
            o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]), stroke="var(--hei)",
                        sw=1.2 if saku else 1.8, dash="2 2" if saku else "7 3"))
            #  ⛔ 柱の刻みは平面に落とさない(此の縮尺では 1間ごとの刻みが線を潰す)。
            #     柵の姿(柱+貫二段・芯々 `tamagaki.postPitchKen`)は其九の展開で読む。
        # ⭐ 銘のある板塀(袖塀)は名を出す — 図に出ない部材を残さない(規則19)
        if r.get("label") and r.get("a"):
            o.append(T(lp.X((r["a"][0] + r["b"][0]) / 2.0) + 4,
                       lp.Y((r["a"][1] + r["b"][1]) / 2.0), r["label"],
                       fs=9, fill="var(--hei)"))
    # 透塀
    for r in d["runs"]:
        if r["kind"] != "透塀": continue
        if not inwin(r["a"], r["b"]): continue
        for a, b in run_segs(r):                    # 中門・潜りの開口で切る
            o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]),
                        stroke="var(--shu)", sw=2.4))
    # 土留め(2026-08-23 検図 — 12条が平面図に一本も描かれていなかった)
    for w in d["terraceWalls"]:
        for a, b in run_segs(w):
            if not inwin(a, b): continue
            o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]),
                        stroke="var(--ishi)", sw=2.6, op=0.9))
            o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]),
                        stroke="var(--paper)", sw=0.8, dash="2 3", op=0.8))

    # 女坂の取付け(前庭の縁へ斜めに当たる分を受ける水平な三角形。2026-08-23)
    for k in d["kaidans"]:
        ap = k.get("apron")
        if ap and inwin(ap[0], ap[1]):
            o.append(PL([(lp.X(u), lp.Y(v)) for u, v in ap], fill="var(--dan)", op=0.95,
                        stroke="var(--ishi)", sw=1.2, close=True))
            cu = sum(q[0] for q in ap) / len(ap); cv = sum(q[1] for q in ap) / len(ap)
            o.append(T(lp.X(cu), lp.Y(cv) + 4, "取付け", fs=9.5, anchor="middle", fill="var(--dim)"))
    for k in d["kaidans"]:
        op_ = k.get("odoribaPoly")
        if not op_: continue
        if not inwin(op_[0], op_[3]): continue
        o.append(PL([(lp.X(u), lp.Y(v)) for u, v in op_], fill="var(--dan)", op=0.95,
                    stroke="var(--ishi)", sw=1.2, close=True))
        cu = sum(q[0] for q in op_) / len(op_); cv = sum(q[1] for q in op_) / len(op_)
        o.append(T(lp.X(cu), lp.Y(cv) + 4, "踊り場", fs=10, anchor="middle", fill="var(--dim)"))

    # 石段(折れ線の坂は区間ごとに帯を描く)
    for k in d["kaidans"]:
        ss = [s for s in segs(k) if inwin(s[0], s[1])]
        if not ss: continue
        tot = seg_len(k, ken) or 1.0
        hw = lp.L(kaidan_wken(d, k)) / 2
        for a, b in ss:
            ax, ay, bx, by = lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1])
            dx, dy = bx - ax, by - ay
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L, dx / L
            o.append(PL([(ax + nx * hw, ay + ny * hw), (bx + nx * hw, by + ny * hw),
                         (bx - nx * hw, by - ny * hw), (ax - nx * hw, ay - ny * hw)],
                        stroke="var(--ishi)", sw=1.0, fill="var(--dan)", op=0.9, close=True))
            # 段の刻み。脚ごとの steps を使い、踊り場の分は詰める
            segm = math.hypot((b[0] - a[0]) * ken, (b[1] - a[1]) * ken)
            lg = None
            if k.get("legs"):
                idx = ss.index((a, b)) if (a, b) in ss else 0
                if idx < len(k["legs"]): lg = k["legs"][idx]
            n = lg["steps"] if lg else int(round(k["steps"] * segm / tot))
            n = min(n, 60)
            for i in range(1, n):
                t = i / float(n)
                px, py = ax + dx * t, ay + dy * t
                o.append(LN(px + nx * hw, py + ny * hw, px - nx * hw, py - ny * hw,
                            stroke="var(--ishi)", sw=0.5, op=0.8))
    # 渡廊下
    for lk in d.get("links", []):
        a, b = lk["from"], lk["to"]
        if not inwin(a, b): continue
        hw = lk["w"] / 2.0
        o.append(lp.rect(a[0], a[1] - hw, b[0], b[1] + hw, fill="var(--roka)",
                         stroke="var(--ink)", sw=0.8, op=0.7))
    # 回廊(runs を正典にしたので、棟と同じ帯で描く。2026-08-23)
    for r in d["runs"]:
        if not r.get("mune"): continue
        bw = r.get("bari", 2) / 2.0
        ua, va = r["a"]; ub, vb = r["b"]
        o.append(lp.rect(ua - bw, va, ub + bw, vb, fill="var(--roka)",
                         stroke="var(--ink)", sw=0.9, op=0.85))
        o.append(T(lp.X((ua + ub) / 2.0), lp.Y((va + vb) / 2.0) + 4, "廻廊",
                   fs=10.5, anchor="middle", fill="var(--paper)"))

    # 棟
    for m in d["munes"]:
        col = YAKU_COL.get(m["yaku"], "var(--nagaya)")
        u, v, du, dv = m["u0"], m["v0"], m["du"], m["dv"]
        if u + du < u0 or u > u1 or v + dv < v0 or v > v1: continue
        dash = "3 3" if m["yaku"] == "接続" else None
        o.append(lp.rect(u, v, u + du, v + dv, fill=col, stroke="var(--ink)", sw=0.9,
                         op=0.35 if m["yaku"] == "接続" else 0.85, dash=dash))
        wpx = abs(lp.X(u + du) - lp.X(u))
        nm = m["name"].replace("附属堂 ", "").replace("回廊 ", "廊")
        o.append(T(lp.X(u + du / 2.0), lp.Y(v + dv / 2.0) + 4, nm, fs=fit(nm, wpx, 11.5),
                   anchor="middle", fill="var(--paper)"))
    # 門
    for gt in d["gates"]:
        u, v = gt["u"], gt["v"]
        if not inwin([u, v], [u, v]): continue
        pl = gt["plan"]
        o.append(lp.rect(u - pl["du"] / 2.0, v - pl["dv"] / 2.0, u + pl["du"] / 2.0, v + pl["dv"] / 2.0,
                         fill="var(--shu)", stroke="var(--ink)", sw=1.1))
        lx, la = lp.X(u), "middle"
        if gt["name"] == "中門": lx, la = lp.X(u) - lp.L(1.2), "end"
        o.append(T(lx, lp.Y(v + pl["dv"] / 2.0) - 5, gt["name"], fs=11, anchor=la, fill="var(--shu)"))
    # 井戸屋形(⭐ 2026-09-06 ユーザー裁定で採用が確定した)
    o += draw_ido(d, lp, inwin)
    # ⭐ 面を持つ点景(縁台)は**縮尺どおりの矩形**で描き、銘を出す(2026-09-06 検図4巡目 低14)
    # ⚠ 石灯籠(○)・手水鉢(△)は**原図の記号**のまま描く — 2026-09-07 検図9巡目 低4 で
    #   面(`planM`)を与えたのは検査に載せるためで、平面図では実寸のほうが記号より小さい。
    #   ⛔ 記号と矩形を二重に描かない(下の記号の輪と重なって団子になる)
    _symnm = set(p["name"] for p in d["props"] if p.get("planM"))
    _pr = [q for q in prop_rects(d) if q[0].rsplit(" ", 1)[0] not in _symnm]
    for _nm, Q in _pr:
        if not inwin([min(q[0] for q in Q), min(q[1] for q in Q)],
                     [max(q[0] for q in Q), max(q[1] for q in Q)]): continue
        o.append(PL([(lp.X(q[0]), lp.Y(q[1])) for q in Q], stroke="var(--ink)", sw=0.9,
                    fill="var(--pl-suso)", op=0.9, close=True))
    if _pr:
        _lab = [q for q in _pr if inwin([min(w[0] for w in q[1]), min(w[1] for w in q[1])],
                                        [max(w[0] for w in q[1]), max(w[1] for w in q[1])])]
        if _lab:
            Q = _lab[0][1]
            o.append(T(lp.X(sum(q[0] for q in Q) / 4.0), lp.Y(max(q[1] for q in Q)) - 4,
                       _lab[0][0].split(" 其")[0], fs=9.5, anchor="middle", fill="var(--ink)"))
    # 石灯籠
    _plan = set(p["name"] for p in d["props"] if p.get("plan"))
    for p in d["props"]:
        if not p.get("uv") or p["name"] in _plan: continue
        for u, v in p["uv"]:
            if not inwin([u, v], [u, v]): continue
            x, y = lp.X(u), lp.Y(v)
            if p["name"] == "石灯籠":
                o.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="none" stroke="var(--ink)" stroke-width="1.1"/>' % (x, y))
            elif "△" in p["name"]:
                o.append(PL([(x, y - 4), (x + 3.6, y + 2.6), (x - 3.6, y + 2.6)],
                            stroke="var(--ink)", sw=1.1, close=True))
            else:
                o.append(R(x - 3.0, y - 1.6, 6.0, 3.2, fill="none", stroke="var(--dim)", sw=0.9))
    # 植栽の塊・一本立ち・主景 / 参道沿い / 踏石(⛔ 図に出ない設計値を残さない・規則19)
    o += draw_sando_side(d, lp, inwin)
    o += draw_clusters(d, lp, inwin)
    o += draw_fumiishi(d, lp, inwin)
    # 断面の切断線
    def _win(a, b):
        ua, va = g.U(a[0]), g.V(a[1])
        ub, vb = g.U(b[0]), g.V(b[1])
        return not (max(ua, ub) < u0 - 2 or min(ua, ub) > u1 + 2
                    or max(va, vb) < v0 - 2 or min(va, vb) > v1 + 2)
    o += cut_lines(d, lambda x: lp.X(g.U(x)), lambda z: lp.Y(g.V(z)),
                   lambda m: lp.L(m / ken), inwin=_win,
                   clip=(14.0, lp.top + 10.0, lp.W - 14.0, lp.top + lp.vh - 6.0))
    o.append(T(6, 15, title, fs=12.5, fill="var(--dim)"))
    o.append(T(lp.W - 6, 15, "1目盛 = 5間 ／ 原点 = 楼門の芯", fs=11, anchor="end", fill="var(--dim)"))
    # 縮尺
    y = lp.H - 10
    o.append(LN(14, y, 14 + lp.L(10), y, stroke="var(--dim)", sw=1.2))
    o.append(T(14 + lp.L(10) / 2, y - 4, "10 間 (18.18 m)", fs=10.5, anchor="middle"))
    sd = d["sando"]                                # 参道(道の領域と芯線)を境内図・附図にも(検図 2026-09-06)
    if sd.get("area"):
        o.append(PL([(lp.X(g.U(x)), lp.Y(g.V(z))) for x, z in sd["area"]], fill="var(--michi)", op=0.35,
                    stroke="var(--shu)", sw=0.8, close=True))
        o.append(PL([(lp.X(g.U(x)), lp.Y(g.V(z))) for x, z in sd["pts"]], stroke="var(--shu)", sw=0.7, dash="6 4", op=0.9))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 断面
def _profile(d, key):
    p = d["profiles"][key]
    if p["axis"] == "EW":
        return [(p["x0"] + i * p["step"], h) for i, h in enumerate(p["h"])]
    if p["axis"] == "NS":
        return [(p["z0"] + i * p["step"], h) for i, h in enumerate(p["h"])]
    a, b = p["a"], p["b"]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return [((p["s0"] + i * p["step"]) * L, h) for i, h in enumerate(p["h"])]


BATTER_ISHI = 0.20      # 石垣の勾配(垂直1に対する水平)。土の法面 batterFill/Cut とは別物
WALL_T = 0.9            # 断面に描く土留めの見かけの厚み[m]
_WSEG = [None]


def wall_segs_world(d, g):
    """土留め(terraceWalls)を開口で割って世界座標の線分にしたもの。"""
    if _WSEG[0] is None:
        out = []
        for w in d["terraceWalls"]:
            for a, b in run_segs(w):
                out.append((g.W(a[0], a[1]), g.W(b[0], b[1])))
        _WSEG[0] = out
    return _WSEG[0]


def on_wall(d, g, x, z, tol=1.5):
    """その位置の平場の縁を土留めが受けているか。受けていなければ法面で摺り付ける。"""
    for (ax, az), (bx, bz) in wall_segs_world(d, g):
        ddx, ddz = bx - ax, bz - az
        L2 = ddx * ddx + ddz * ddz or 1.0
        t = max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
        if math.hypot(x - (ax + ddx * t), z - (az + ddz * t)) <= tol:
            return True
    return False


def prof_pos(d, key):
    """断面の座標 c → 世界座標 (x,z)。"""
    p = d["profiles"][key]
    if p["axis"] == "EW": return lambda c: (c, p["at"])
    if p["axis"] == "NS": return lambda c: (p["at"], c)
    pts = p.get("pts")
    a, b = p["a"], p["b"]
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    if not pts:
        return lambda c: (a[0] + (b[0] - a[0]) * c / L, a[1] + (b[1] - a[1]) * c / L)

    segl0 = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
             for i in range(len(pts) - 1)]
    ARC = sum(segl0) or 1.0

    def f(c):
        # ⚠ `pts` のある縦断は座標が**展開長**なので、弦 L ではなく ARC で割る
        #    (2026-08-23 検図の後始末。L で割ると図の右端で 0.35m ずれる)
        t = max(0.0, min(1.0, c / ARC))
        segl = segl0
        tot = ARC
        want = t * tot
        for i, sl in enumerate(segl):
            if want <= sl or i == len(segl) - 1:
                r = want / (sl or 1.0)
                return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * r,
                        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * r)
            want -= sl
        return pts[-1]
    return f


def series_at(series, c):
    """折れ線の値。⚠ **幅ゼロの区間(蹴上の垂直)は飛ばす** — そこで拾うと
    石段の面が一段ずれて読める(2026-08-24)。"""
    deg = None
    for i in range(len(series) - 1):
        a, b = series[i], series[i + 1]
        if a[0] - 1e-9 <= c <= b[0] + 1e-9:
            if abs(b[0] - a[0]) < 1e-9:
                if deg is None: deg = a[1]
                continue
            return a[1] + (b[1] - a[1]) * (c - a[0]) / (b[0] - a[0])
    if deg is not None: return deg
    return series[-1][1]


def design_series(d, g, key, prof, override=(), stairs=()):
    """断面の設計地盤を **design_y から直に**引く(2026-08-23 検図 高-1/中-6)。

    ⚠ 平場の範囲を断面ごとに手で書くのをやめた — 書き落とした断面が白紙になり(断面ト・チ)、
    書いた断面も平場ポリゴンと食い違っていた(断面イの西端が3.6m短い)。
    §3b の切盛図と**同じ関数**を通すので、断面と切盛図で縁の始末が食い違うことはない。
    override = [(c0,c1,y)] は基壇など design_y が知らない構造物、stairs = [(c0,c1,y0,y1,kaidan)]。
    """
    wpos = prof_pos(d, key)
    c0, c1 = prof[0][0], prof[-1][0]
    stp = max(0.25, min(0.5, (c1 - c0) / 600.0))
    cs = set(c for c, _ in prof)
    k = 0
    while c0 + k * stp <= c1:
        cs.add(round(c0 + k * stp, 4)); k += 1
    out = []
    for c in sorted(cs):
        x, z = wpos(c)
        y = design_y(d, g, x, z)
        if y is None:
            y = dem_h(x, z)
            if y is None: y = series_at(prof, c)
        for a, b, yy in override:
            if a - 1e-6 <= c <= b + 1e-6: y = yy
        out.append((c, y))
    for a, b, yy in override:
        out += [(a, yy), (b, yy)]
    # 石段は踏面/蹴上のギザギザで描き直す(§3c)。踊り場も割付どおりに入れる
    for a, b, ya, yb, kd in stairs:
        out = [(c, y) for c, y in out if not (min(a, b) - 1e-6 < c < max(a, b) + 1e-6)]
        out += stair_profile(a, b, ya, yb, kd)
    out.sort(key=lambda q: q[0])
    return out


def wall_steps(d, g, key, prof, design):
    """設計線の垂直な段差のうち **土留めが受けているもの**を拾う(§3c)。

    返り: [(縁, 外向き符号, 天端, 露出, 法尻, 切/盛)]。法尻は勾配 BATTER_ISHI の面と
    現地形の交点(二分法)で、其二十の展開図と同じ式。
    """
    wpos = prof_pos(d, key)
    c0, c1 = prof[0][0], prof[-1][0]
    nat = lambda c: series_at(prof, max(c0, min(c1, c)))
    raw = []
    for i in range(len(design) - 1):
        (ca, ya), (cb, yb) = design[i], design[i + 1]
        if cb - ca > 1.0 or abs(yb - ya) < 0.30: continue
        e = (ca + cb) / 2.0
        if e <= c0 + 0.6 or e >= c1 - 0.6: continue
        if not on_wall(d, g, *wpos(e)): continue
        ins_b = any(in_poly(wpos(cb), terrace_poly(te, g)) for te in d["terraces"])
        sgn = 1.0 if not ins_b else -1.0
        yy = ya if sgn > 0 else yb
        raw.append((e, sgn, yy))
    cand = []
    for e, sgn, yy in raw:
        hn = nat(e)
        if abs(yy - hn) < 0.30: continue
        up = yy < hn
        t, lo, hi = 0.0, 0.0, abs(yy - hn) + 14.0
        for _ in range(40):
            t = (lo + hi) / 2.0
            h = nat(e + sgn * BATTER_ISHI * t)
            if (yy + t > h) if up else (yy - t < h): hi = t
            else: lo = t
        cand.append((e, sgn, yy, t, e + sgn * BATTER_ISHI * t, "切" if up else "盛"))
    # 近接する段差は**露出の大きいほうを残す**(2026-08-23 — 基壇の0.7mが平場の縁の3.2mを消していた)
    out = []
    for q in sorted(cand, key=lambda r: -r[3]):
        if any(abs(q[0] - r[0]) < 1.2 for r in out): continue
        out.append(q)
    out.sort(key=lambda r: r[0])
    return out


def _cross(A, B, ax, at):
    """線分 A→B が切断線(EW なら z=at / NS なら x=at)を横切る座標。切らなければ None。"""
    i, j = (1, 0) if ax == "EW" else (0, 1)
    if (A[i] - at) * (B[i] - at) > 0: return None
    t = (at - A[i]) / (B[i] - A[i]) if abs(B[i] - A[i]) > 1e-9 else 0.0
    return A[j] + (B[j] - A[j]) * t


def _span(A, B, ax, at):
    """矩形(対角 A,B)が切断線に掛かる区間。掛からなければ None。"""
    i, j = (1, 0) if ax == "EW" else (0, 1)
    lo, hi = min(A[i], B[i]), max(A[i], B[i])
    if not (lo - 1e-6 <= at <= hi + 1e-6): return None
    return (min(A[j], B[j]), max(A[j], B[j]))


def section_marks(d, g, key, prof):
    """断面の切断線が**実際に切る**棟・囲い・門を拾う(2026-08-24 検図 中-1)。

    ⚠ 注記に手で「何を切るか」を書くと腐る(6件中5件が線上に無かった)。
    """
    p = d["profiles"][key]
    ax = p["axis"]
    if ax not in ("EW", "NS"): return []
    at = p["at"]
    yk = plane_y(d, d["planes"][0])
    out = []
    for m in d["munes"]:
        if m["yaku"] == "接続": continue
        a, b = g.W(m["u0"], m["v0"]), g.W(m["u0"] + m["du"], m["v0"] + m["dv"])
        x0, x1 = sorted([a[0], b[0]]); z0, z1 = sorted([a[1], b[1]])
        if ax == "EW":
            if z0 - 1e-6 <= at <= z1 + 1e-6:
                out.append((x0, x1, yk, m["name"], "社殿" if m["yaku"] == "社殿" else "堂"))
        else:
            if x0 - 1e-6 <= at <= x1 + 1e-6:
                out.append((z0, z1, yk, m["name"], "社殿" if m["yaku"] == "社殿" else "堂"))
    # ⭐ **柵も切る**【ユーザー裁定 2026-09-07】 — 境内の囲いが板塀から柵へ替わったので、
    #    種別で拾っていた断面から黙って落ちるところだった(規則19)。⛔ 天端を持たない柵
    #    (麓道・参道の柵。地形なり)は面の断面に載らないので入れない。
    for r in d["runs"]:
        if r["kind"] not in ("透塀", "板塀", "回廊") and \
           not (r["kind"] == "柵" and isinstance(r.get("seat"), (int, float))): continue
        for a, b in run_segs(r):
            A, B = g.W(*a), g.W(*b)
            if ax == "EW":
                if (A[1] - at) * (B[1] - at) > 0: continue
                t = (at - A[1]) / (B[1] - A[1]) if abs(B[1] - A[1]) > 1e-9 else 0.0
                c = A[0] + (B[0] - A[0]) * t
            else:
                if (A[0] - at) * (B[0] - at) > 0: continue
                t = (at - A[0]) / (B[0] - A[0]) if abs(B[0] - A[0]) > 1e-9 else 0.0
                c = A[1] + (B[1] - A[1]) * t
            # ⭐ 天端は run が名指す `seat`(2026-09-06 検図5巡目 中11 — 前庭の板塀を境内面 28.3 の
            #    高さに描いていた。前庭を切る断面を足したので目に見えるようになった)
            # ⭐ 丈を**宣言している物は宣言のほうを採る**(6つめ)。柵の丈は `hFrom` の従属値
            out.append((c - 0.4, c + 0.4, r.get("seat") or yk, r["kind"],
                        {"回廊": "廊", "柵": "柵"}.get(r["kind"], "塀"), run_take_m(d, r)))
    # ⭐ **前庭の新設物**(玉垣・井戸屋形・縁台・低木の面)を切る(2026-09-06 検図5巡目 中11)。
    #    ⛔ 断面に出ない物は「図に無い設計値」になる(規則19)。
    zy = d["terraces"][1]["y"]
    for gd in d["gardens"]:
        for nm, a, b, fence, _ln, rs in tamagaki_edges(d, gd):
            if not fence: continue
            for rn in rs:
                A, B = g.W(*rn[0]), g.W(*rn[1])
                c = _cross(A, B, ax, at)
                if c is not None:
                    out.append((c - 0.3, c + 0.3, zy, "玉垣 " + nm, "玉垣"))
        sh = gd.get("shrubs")
        if sh and sh.get("box"):
            u0, v0, u1, v1 = sh["box"]
            A, B = g.W(u0, v0), g.W(u1, v1)
            c = _span(A, B, ax, at)
            if c: out.append((c[0], c[1], zy, "低木を撒く面", "植込"))
    _ir = ido_rects(d)
    if _ir:
        A, B = g.W(_ir["軒先"][0], _ir["軒先"][1]), g.W(_ir["軒先"][2], _ir["軒先"][3])
        c = _span(A, B, ax, at)
        if c: out.append((c[0], c[1], zy, "井戸屋形", "屋形"))
    for nm, Q in prop_rects(d):
        W_ = [g.W(q[0], q[1]) for q in Q]
        A = (min(q[0] for q in W_), min(q[1] for q in W_))
        B = (max(q[0] for q in W_), max(q[1] for q in W_))
        c = _span(A, B, ax, at)
        # ⛔ **点景の座りを前庭の天端で代表させない**(2026-09-07 検図9巡目 低4)— 面を与えた点景は
        #    白洲(境内)にも立つ。その点を含む平場の天端を採り、どこにも載らなければ現地形
        if c:
            yq = None
            for te in d["terraces"]:
                if in_poly(W_[0], terrace_poly(te, g)): yq = te["y"]; break
            hq = ([p for p in d["props"] if nm.rsplit(" ", 1)[0] == p["name"]] or [{}])[0]
            out.append((c[0], c[1], yq if yq is not None else (dem_h(*W_[0]) or zy), nm,
                        "縁台" if yq == zy else "点景", (hq.get("planM") or {}).get("h")))
    for gt in d["gates"]:
        q = g.W(gt["u"], gt["v"])
        du, dv = gt["plan"]["du"] / 2.0 * d["const"]["ken"], gt["plan"]["dv"] / 2.0 * d["const"]["ken"]
        if ax == "EW":
            if abs(q[1] - at) <= dv: out.append((q[0] - du, q[0] + du, gt["sill"], gt["name"].split("(")[0], "門"))
        else:
            if abs(q[0] - at) <= du: out.append((q[1] - dv, q[1] + dv, gt["sill"], gt["name"].split("(")[0], "門"))
    return out


def ido_jiyama(d, g):
    """井戸屋形の**石敷4隅の地山標高**と**盛土の厚み** ── `sanno_dem.json` からの従属値。

    ⛔ 数を json に書かない(規則4)。戻り値 [(隅の名, 世界(x,z), 地山h, 盛土厚)] と 天端。
    """
    R_ = ido_rects(d)
    if not R_: return [], None
    u0, v0, u1, v1 = R_["石敷"]
    top = d["terraces"][1]["y"]
    out = []
    for nm, (u, v) in (("南西", (u0, v0)), ("南東", (u1, v0)), ("北東", (u1, v1)), ("北西", (u0, v1))):
        x, z = g.W(u, v)
        hh = dem_h(x, z)
        if hh is None: continue
        out.append((nm, (x, z), hh, top - hh))
    return out, top


def ido_section_layer(d, g, key, X, Y, y0):
    """井戸屋形を切る断面へ〈地山線〉〈盛土層の厚み〉〈井筒が地山へ入る点〉を描き足す。

    ⭐ **2026-09-06c 裁定1(b)(庭方)** — 井戸屋形は動かさない代わりに、盛土層と井筒を図に出して
    「なぜ盛土を貫いてよいか」を読ませる。⛔ 数を json に置かない — 宣言は層の厚み
    (`ido.moriLayers`)と井筒(`ido.izutsu`)だけで、地山標高も盛土の厚みも `sanno_dem.json` の従属値。
    ⛔ 深さは持たないので、井筒は地山へ入った先を破線で落として切る。
    """
    io = d.get("ido")
    R_ = ido_rects(d)
    if not io or not R_ or not io.get("moriLayers"): return []
    p = d["profiles"][key]
    ax = p.get("axis")
    if ax not in ("EW", "NS"): return []
    at = p["at"]
    ken = d["const"]["ken"]
    u0, v0, u1, v1 = R_["石敷"]
    A, B = g.W(u0, v0), g.W(u1, v1)
    x0, x1 = sorted([A[0], B[0]]); z0, z1 = sorted([A[1], B[1]])
    C = g.W(io["uv"][0], io["uv"][1])
    if ax == "EW":
        if not (z0 - 1e-6 <= at <= z1 + 1e-6): return []
        ca, cb, cc = x0, x1, C[0]
    else:
        if not (x0 - 1e-6 <= at <= x1 + 1e-6): return []
        ca, cb, cc = z0, z1, C[1]
    wpos = prof_pos(d, key)
    top = d["terraces"][1]["y"]
    o = []
    # 〈地山線〉── 石敷の下だけ太い実線で強調(図全体の破線は現地形)
    N = 24
    gl = []
    for i in range(N + 1):
        c = ca + (cb - ca) * i / float(N)
        hh = dem_h(*wpos(c))
        if hh is not None: gl.append((X(c), Y(hh)))
    if len(gl) < 2: return []
    o.append(PL(gl, stroke="var(--ishi)", sw=2.4, op=0.95))
    o.append(T(X(ca) - 5, gl[0][1] + 12, "地山線", fs=10.5, anchor="end", fill="var(--ishi)"))
    # 〈盛土層の厚み〉── 天端から下へ 板石 / 敷砂 / 割栗、その下が締固めた盛土
    yy = top
    for L in io["moriLayers"]:
        yb = yy - L["tM"]
        o.append(PL([(X(ca), Y(yy)), (X(cb), Y(yy)), (X(cb), Y(yb)), (X(ca), Y(yb))],
                    stroke="var(--ishi)", sw=0.8, fill="var(--dan3)", op=0.85, close=True))
        yy = yb
    o.append(T(X(cb) + 6, Y(top) - 2, "板石/敷砂/割栗", fs=9.5, fill="var(--ishi)"))
    o.append(PL([(X(ca), Y(yy)), (X(cb), Y(yy))] + list(reversed(gl)),
                stroke="none", fill=_fill(), op=0.9, close=True))
    o.append(T((X(ca) + X(cb)) / 2.0, Y(yy) + 13, "締固めた盛土(厚みは地山線との差)",
               fs=9.5, anchor="middle", fill="var(--take)"))
    # 〈井筒〉と〈井筒が地山へ入る点〉── ⭐ **三重**(内径 / 石積の外径 / 練り粘土の外径)
    #   2026-09-07 裁定2(庭方)。⛔ 線2本で描かない — 内径に粘土が直接接して見える。
    r1, r2, r3 = izutsu_radii(d)
    nend = (io.get("izutsu") or {}).get("nendoMakiTM", 0.0)
    hc = dem_h(*wpos(cc))
    if hc is not None:
        # 練り粘土の巻き ── 天端は `nendoMakiTop`(= 割栗の突き固めの下端 yy)で止める
        ytop_n = yy if (io.get("izutsu") or {}).get("nendoMakiTop") else top
        if nend > 0:
            for sgn in (-1, 1):
                a_, b_ = cc + sgn * r2, cc + sgn * r3
                o.append(PL([(X(a_), Y(ytop_n)), (X(b_), Y(ytop_n)), (X(b_), Y(hc)), (X(a_), Y(hc))],
                            stroke="var(--niwa)", sw=0.8, fill="var(--niwa)", op=0.35, close=True))
            o.append(T(X(cc + r3) + 5, Y((ytop_n + hc) / 2.0), "練り粘土の巻き(天端=割栗の下端)",
                       fs=9.5, fill="var(--niwa)"))
        # 石積の壁(内径 → 外径)。地山より下は破線で落として切る
        for sgn in (-1, 1):
            a_, b_ = cc + sgn * r1, cc + sgn * r2
            o.append(PL([(X(a_), Y(top)), (X(b_), Y(top)), (X(b_), Y(hc)), (X(a_), Y(hc))],
                        stroke="var(--ishi)", sw=1.2, fill="var(--ishi)", op=0.30, close=True))
            for c_ in (a_, b_):
                o.append(LN(X(c_), Y(top), X(c_), Y(hc), stroke="var(--ishi)", sw=2.0))
                o.append(LN(X(c_), Y(hc), X(c_), Y(max(y0, hc - 2.4)), stroke="var(--ishi)",
                            sw=2.0, dash="4 3"))
        o.append(LN(X(cc - r2), Y(hc), X(cc + r2), Y(hc), stroke="var(--shu)", sw=1.6))
        o.append(T(X(cc + r3) + 5, Y(hc) - 4, "井筒が地山へ入る点", fs=10, fill="var(--shu)"))
        o.append(T(X(cc), Y(max(y0, hc - 2.4)) + 12, "井筒 内径/石積/粘土の三重(深さは従属値)",
                   fs=9.5, anchor="middle", fill="var(--ishi)"))
    return o


def igeta_rise(d):
    """井桁の**石敷からの立ち上がり**[m] ── 見付 × 段数(⛔ 数を json に持たない)。"""
    io = d.get("ido") or {}
    return io.get("igetaMitsukeM", 0.0) * io.get("igetaDanN", 0)


def soishi_radii(d):
    """(柱芯の隅の半径, 礎石の内隅の半径)[m] ── 筒の芯からの距離。⛔ 数を json に持たない。"""
    io = d.get("ido") or {}
    ken = d["const"]["ken"]
    p = io["hashiraPitchKen"] / 2.0 * ken
    s = io.get("soishiM", 0.0) / 2.0
    return math.hypot(p, p), math.hypot(p - s, p - s)


def izutsu_radii(d):
    """井筒の**三重の半径**[m] ── (内径の半分, 石積の外半径, 練り粘土の外半径)。

    ⭐ 2026-09-07 裁定2(庭方)。⛔ 径を json に書かない — 内径 `naikeiShaku` 尺・壁厚
    `kabeAtsuM`・粘土 `nendoMakiTM` からの従属値。
    """
    io = d.get("ido") or {}
    iz = io.get("izutsu") or {}
    ken = d["const"]["ken"]
    r1 = iz.get("naikeiShaku", 3) / 6.0 * ken / 2.0
    r2 = r1 + iz.get("kabeAtsuM", 0.0)
    return r1, r2, r2 + iz.get("nendoMakiTM", 0.0)


def tree_section_items(d, g, key, c0, c1):
    """断面の切断線が**樹冠を切る**一本立ち ── (断面座標, 見えがかりの半幅, 枝下, 丈, 天端, 名)。

    ⭐ 2026-09-06c 参考2(庭方)— 断面レは「木陰が縁台に落ちているか」を読ませる図なので、
    **枝下(樹冠の下端)と座面高が同じ一本に出ていなければならない**。
    ⛔ 数を持たない — 丈・樹冠・枝下は `gardens[].singles[]` の宣言と部材の実寸からの従属値。
    """
    p = d["profiles"][key]
    ax = p.get("axis")
    if ax not in ("EW", "NS"): return []
    at = p["at"]
    ken = d["const"]["ken"]
    top = d["terraces"][1]["y"]
    cr = d["planting"]["plantRule"].get("crownRule") or {}
    out = []
    for gd in d["gardens"]:
        if (gd.get("clearance") or "") != "zentei": continue
        for sg in gd.get("singles", []):
            r = single_crown(d, sg)
            if not r or not sg.get("h"): continue
            wx, wz = g.W(sg["uv"][0], sg["uv"][1])
            off = abs((wz if ax == "EW" else wx) - at)
            if off > r * ken - 1e-6: continue          # 樹冠を切らない
            c = wx if ax == "EW" else wz
            if c < c0 - 1e-6 or c > c1 + 1e-6: continue
            half = math.sqrt(max(0.0, (r * ken) ** 2 - off ** 2))   # 切断線上の樹冠の見えがかりの半幅
            eda, decl = sg.get("edaShita"), True
            if eda is None:
                # ⛔ 宣言が無い木に枝下を発明しない — **層の下限**を描き、図に「以上」と断る
                decl = False
                eda = ((cr.get("chuboku") or {}) if sg.get("layer") == "中木"
                       else (cr.get("takagi") or {})).get("edaShitaMinM")
            out.append((c, half, eda or 0.0, sg["h"], top,
                        "%s(枝下 %s%.1f m)" % (sg["name"], "" if decl else "≧ ", eda or 0.0)))
    return out


def tree_section_layer(items, X, Y):
    """`tree_section_items` の一本立ちを断面へ描く(幹・枝下の線・樹冠の見えがかり)。"""
    o = []
    for c, half, eda, hh, top, nm in items:
        o.append(LN(X(c), Y(top), X(c), Y(top + hh), stroke="var(--niwa)", sw=1.6))
        o.append(PL([(X(c - half), Y(top + eda)), (X(c), Y(top + hh)), (X(c + half), Y(top + eda))],
                    stroke="var(--niwa)", sw=1.2, fill="var(--niwa)", op=0.28, close=True))
        o.append(LN(X(c - half), Y(top + eda), X(c + half), Y(top + eda),
                    stroke="var(--niwa)", sw=1.0, dash="4 3"))
        o.append(T(X(c), Y(top + hh) - 5, nm, fs=9.5, anchor="middle", fill="var(--niwa)"))
    return o


def section_svg(d, key, design, marks, title, flip=False, viewtxt="", flats=(), stairs=()):
    """design = [(coord, y), ...] 設計地盤 / marks = [(coord0, coord1, y, ラベル, 種別)]"""
    g = G(d)
    prof = _profile(d, key)
    walls = wall_steps(d, g, key, prof, design)
    c0, c1 = prof[0][0], prof[-1][0]
    trees = tree_section_items(d, g, key, c0, c1)
    ys = ([h for _, h in prof] + [y for _, y in design]
          + [t[4] + t[3] for t in trees])           # ⭐ 木の梢まで窓へ入れる(⛔ 切らない)
    y0, y1 = min(ys) - 2.0, max(ys) + 6.0
    W = 900.0
    s = W / (c1 - c0)
    Hh = min(460.0, (y1 - y0) * s * VEX)
    top = 26.0
    H = Hh + top + 26.0
    X = (lambda c: (c1 - c) * s) if flip else (lambda c: (c - c0) * s)
    vs = Hh / (y1 - y0)
    Y = lambda y: top + Hh - (y - y0) * vs
    o = _sv(W, H, title)
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    dpts = [(X(c), Y(y)) for c, y in design]
    npts = [(X(c), Y(h)) for c, h in prof]
    # 地表下の塗り
    o.append(PL(npts + [(npts[-1][0], Y(y0)), (npts[0][0], Y(y0))],
                stroke="none", fill="var(--dan3)", op=0.75, close=True))

    # 切土(設計 < 現地形)と盛土(設計 > 現地形)を塗り分ける
    cs = sorted(set([c for c, _ in prof] + [c for c, _ in design]))
    cs = [c for c in cs if prof[0][0] - 1e-6 <= c <= prof[-1][0] + 1e-6]
    at = series_at

    for i in range(len(cs) - 1):
        ca, cb = cs[i], cs[i + 1]
        if cb - ca < 1e-6: continue
        na, nb = at(prof, ca), at(prof, cb)
        da, db = at(design, ca), at(design, cb)
        if abs(na - da) < 0.05 and abs(nb - db) < 0.05: continue
        cut = (na + nb) / 2 > (da + db) / 2
        o.append(PL([(X(ca), Y(na)), (X(cb), Y(nb)), (X(cb), Y(db)), (X(ca), Y(da))],
                    stroke="none", fill=_cut() if cut else _fill(), close=True))

    o.append(PL(npts, stroke="var(--dim)", sw=1.1, dash="5 3"))

    # 無造成の区間に太い帯(§3c)。色が無いのが「触っていない」のか
    # 「反映漏れ」なのかを図の上で区別できるようにする
    run, nomu = [], []
    for c in cs:
        if abs(at(prof, c) - at(design, c)) < 0.05:
            run.append(c)
        else:
            if len(run) > 1: nomu.append((run[0], run[-1]))
            run = []
    if len(run) > 1: nomu.append((run[0], run[-1]))
    for ca, cb in nomu:
        if cb - ca < 1.5: continue
        seg = [(X(c), Y(at(prof, c))) for c in cs if ca - 1e-6 <= c <= cb + 1e-6]
        o.append(PL(seg, stroke="var(--take)", sw=6.0, op=0.8))
    o.append(PL(dpts, stroke="var(--ink)", sw=2.0))

    # 土留め ─ 天端は面の高さで一定でも法尻は地形なり(§3c)
    for e, sgn, yy, t, ctoe, kind in walls:
        if kind == "盛":
            face = [(e, yy), (ctoe, yy - t)]
            back = [(ctoe - sgn * WALL_T, yy - t), (e - sgn * WALL_T, yy)]
        else:
            face = [(e, yy), (ctoe, yy + t)]
            back = [(ctoe + sgn * WALL_T, yy + t), (e + sgn * WALL_T, yy)]
        o.append(PL([(X(c), Y(y)) for c, y in face + back], fill=_pat(), op=0.95,
                    stroke="var(--ishi)", sw=1.2, close=True))
        ym = (face[0][1] + face[1][1]) / 2.0
        xl = X(e + sgn * (BATTER_ISHI * t + WALL_T + 1.2))
        anc = "start" if (sgn > 0) != flip else "end"
        if xl > W - 150: xl, anc = X(e) - 6, "end"     # 図の端で切れないよう内側へ返す
        if xl < 150: xl, anc = X(e) + 6, "start"
        o.append(T(xl, Y(ym) + 4, "土留 露出 %.2f m" % t, fs=10, fill="var(--ishi)", anchor=anc))
    # 高さの罫(塗りの上に載せる)
    for y in range(int(math.ceil(y0 / 5.0) * 5), int(y1) + 1, 5):
        o.append(LN(0, Y(y), W, Y(y), stroke="var(--grid)", sw=0.5, op=0.55))
        o.append(T(3, Y(y) - 2, "%d m" % y, fs=9.5, fill="var(--dim)"))
    # 建物・門・石段のマーク
    # ⭐ **図の窓でクリップする**(2026-09-06 — 断面 WEST に本殿など8件が窓の外から混入していた
    #    `_pending`「section_marksのクリップ窓バグ」。前庭の東西断面を足して目に見えるようになった)
    for mk in marks:
        c0m, c1m, yb, lab, kind = mk[:5]
        if max(c0m, c1m) < c0 - 1e-6 or min(c0m, c1m) > c1 + 1e-6: continue
        c0m, c1m = max(min(c0m, c1m), c0), min(max(c0m, c1m), c1)
        xa, xb = X(c0m), X(c1m)
        if xa > xb: xa, xb = xb, xa
        # ⭐ 丈を**宣言している物は宣言のほうを採る**(6つめ・2026-09-07 検図9巡目 低4)。
        #    ⛔ 記号の丈(下の表)は宣言が無い物の見えがかりで、⛔ 設計値ではない
        hgt = mk[5] if len(mk) > 5 and mk[5] else \
            {"社殿": 7.5, "門": 9.0, "廊": 5.0, "塀": 2.1, "堂": 4.5, "柵": 1.2,
             "玉垣": 1.2, "屋形": 2.9, "縁台": 0.42, "植込": 1.6}.get(kind, 4.0)
        col = {"社殿": "var(--shu)", "門": "var(--shu)", "廊": "var(--roka)",
               "塀": "var(--hei)", "柵": "var(--hei)", "堂": "var(--nagaya)", "玉垣": "var(--take)",
               "屋形": "var(--roka)", "縁台": "var(--take)", "植込": "var(--niwa)",
               "点景": "var(--take)"}.get(kind, "var(--nagaya)")
        hpx = max(9.0, min(46.0, hgt * vs))
        o.append(R(xa, Y(yb) - hpx, xb - xa, hpx, fill=col, op=0.55, stroke="var(--ink)", sw=0.8))
        o.append(T((xa + xb) / 2, Y(yb) - hpx - 4, lab, fs=fit(lab, xb - xa, 10.5), anchor="middle"))
    # ⭐ **井戸屋形を切る断面**は盛土層と井筒を描き足す(2026-09-06c 裁定1(b)・庭方)
    o.extend(ido_section_layer(d, g, key, X, Y, y0))
    # ⭐ **一本立ちを切る断面**は幹と枝下を描く(2026-09-06c 参考2 — 断面レが『木陰が縁台に
    #    落ちているか』を読ませるには、樹冠の下端(枝下)と座面が同じ一本に出ていなければならない)
    o.extend(tree_section_layer(trees, X, Y))
    o.append(T(6, 15, title, fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "垂直 %.1f 倍" % (vs / s), fs=11, anchor="end", fill="var(--dim)"))
    o.append(T(W - 6, 30, viewtxt, fs=10.5, anchor="end", fill="var(--shu)"))
    o.append(T(W - 6, H - 8, "破線 = 造成前の地形(正本 base_dem.json) ／ 実線 = 設計地盤 ／ ╲ 切土 ／ ╱ 盛土"
               " ／ 太い緑帯 = 無造成 ／ 網掛 = 土留め(法尻は地盤なり)", fs=10.5,
               anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其八 坂の割付
def saka_svg(d, kan="其八"):
    ken = d["const"]["ken"]
    ks = [k for k in d["kaidans"] if k["name"] != "向拝の階"]
    W = 900.0
    ROW, RISE = 150.0, 78.0          # 1段あたりの行高 / 比高の描画高
    H = 46.0 + len(ks) * ROW
    o = _sv(W, H, "男坂と女坂の割付")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    Ls = [seg_len(k, ken) for k in ks]
    hs = 560.0 / max(Ls)             # 水平スケール
    for i, k in enumerate(ks):
        L, rise = Ls[i], k["yTop"] - k["yBot"]
        vs = RISE / rise             # 垂直スケール(行ごとに同じ比高なので共通)
        bx, by = 96.0, 56.0 + i * ROW
        o.append(LN(bx, by, bx + L * hs, by, stroke="var(--grid)", sw=0.6, dash="4 3"))
        o.append(LN(bx, by + rise * vs, bx + L * hs, by + rise * vs, stroke="var(--grid)", sw=0.6, dash="4 3"))
        # 実形で描く。男坂 = 段の連 + 踊り場 / 女坂 = 脚ごとの斜路に段を疎らに置く
        px, py, pts, brk = bx, by, [(bx, by)], []
        if k.get("flights"):
            # 段の連(踏面0.45)と踊り場を交互に。余る水平はすべて踊り場が持つ
            od = k.get("odoriba", 0.0)
            c = 0.0
            for fi, fn in enumerate(k["flights"]):
                for _ in range(fn):
                    c += k["fumi"]
                    px2 = bx + c * hs
                    py2 = py - k["keri"] * vs
                    pts += [(px2, py), (px2, py2)]
                    px, py = px2, py2
                if fi < len(k["flights"]) - 1:
                    c += od
                    px2 = bx + c * hs
                    pts.append((px2, py)); brk.append(px2); px = px2
        elif k.get("rMin") and not k.get("legs"):
            c = k.get("stepStart", 0.0)
            pit = k.get("stepRun", k["planeLen"]) / k["steps"]
            if c > 0:
                px2 = bx + c * hs
                pts.append((px2, py)); brk.append(px2); px = px2
            for j in range(k["steps"]):
                c += pit
                px2 = bx + c * hs
                py2 = py - k["keri"] * vs
                pts += [(px2, py), (px2, py2)]
                px, py = px2, py2
        elif k.get("legs"):
            c = 0.0
            for li, lg in enumerate(k["legs"]):
                for j in range(lg["steps"]):
                    c += lg["pitch"]
                    px2 = bx + c * hs
                    py2 = py - k["keri"] * vs
                    pts += [(px2, py), (px2, py2)]     # 斜路+段(踏面0.45の段を間隔 pitch で置く)
                    px, py = px2, py2
                if li < len(k["legs"]) - 1: brk.append(px)
        else:
            n = k["steps"]
            for j in range(n):
                px2 = bx + (j + 1) * (L * hs / n)
                py2 = by + (j + 1) * (rise * vs / n)
                pts += [(px2, py), (px2, py2)]
                px, py = px2, py2
        if k.get("flights") or k.get("legs"):
            pts = [(x, y + rise * vs) for x, y in pts]   # 下端を基線へ
        o.append(PL(pts, stroke="var(--ishi)", sw=1.3))
        for xb in brk:
            o.append(LN(xb, by, xb, by + rise * vs, stroke="var(--shu)", sw=0.8, dash="3 3"))
        if brk:
            o.append(T(brk[len(brk) // 2], by - 2,
                       "踊り場 %d 箇所" % len(brk) if k.get("flights") else "折れ(踊り場)",
                       fs=9.5, anchor="middle", fill="var(--shu)"))
        o.append(T(bx, by - 12, k["name"], fs=12.5, fill="var(--ink)"))
        o.append(T(bx + L * hs + 10, by + rise * vs * 0.42,
                   "%d 段　蹴上 %.2f ／ 踏面 %.3f" % (k["steps"], k["keri"], k["fumi"]), fs=11))
        # ⚠ 分岐に当たらない坂は副題が空になる(2026-08-23 検図 — rMin の分岐が二つあり死んでいた)
        # 折れ線・曲線の坂は必ずどれかの分岐に当たること(直線の坂は else でよい)
        if k.get("pts") and not (k.get("flights") or k.get("legs") or k.get("rMin")):
            raise SystemExit("割付図の分岐に無い石段: %s" % k["name"])
        sub = ""
        if k.get("flights"):
            sub = "段の連 %s ＋ 踊り場 %.2f m ×%d" % ("+".join(str(x) for x in k["flights"]),
                                                     k["odoriba"], len(k["flights"]) - 1)
        elif k.get("rMin") and not k.get("legs"):
            sub = "緩いカーブ ／ 最小曲率半径 %.0f m ／ 段の間隔 %.2f m" % (
                k["rMin"], k["planeLen"] / k["steps"])
        elif k.get("legs"):
            sub = " ／ ".join("%s %.1f m・%d段・%.1f%%(間隔 %.2f m)" % (lg["name"].split("(")[0], lg["len"],
                              lg["steps"], lg["grade"], lg["pitch"]) for lg in k["legs"])
        o.append(T(bx + L * hs + 10, by + rise * vs * 0.42 + 16,
                   "全体の勾配 %.1f%%  (%.1f°)" % (k["grade"], k["deg"]), fs=11, fill="var(--shu)"))
        if sub:
            o.append(T(bx + L * hs + 10, by + rise * vs * 0.42 + 31, sub, fs=10, fill="var(--dim)"))
        _up = bool(k.get("rMin")) and not k.get("legs")     # 左→右が上りに描かれる坂
        o.append(T(bx - 8, by + 4, "%.1f m" % (k["yBot"] if _up else k["yTop"]),
                   fs=10, anchor="end", fill="var(--dim)"))
        o.append(T(bx - 8, by + rise * vs + 4, "%.1f m" % (k["yTop"] if _up else k["yBot"]),
                   fs=10, anchor="end", fill="var(--dim)"))
        o.append(T(bx + L * hs / 2, by + rise * vs + 20, "平面長 %.2f m" % L, fs=10.5,
                   anchor="middle", fill="var(--dim)"))
    o.append(T(6, 15, kan + "　男坂と女坂の割付 ─ 同じ比高を、違う道のりで降ろす", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "水平・垂直とも図版内で正規化(勾配は数値で読む)", fs=10.5,
               anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其九 囲いの展開
def _zentei_kakoi(d):
    """前庭を囲う条の数と名を json から数える(数を文章に写さない)。"""
    tw = [w["name"] for w in d["terraceWalls"] if "Zentei" in w["name"]]
    # ⚠ **前庭に座る板塀**で拾う(⛔ 名前の綴りで拾わない — 袖塀 Ita_Niou_N を数え落としていた)
    it = [r["name"] for r in d["runs"]
          if r["kind"] == "板塀" and r.get("seat") == d["terraces"][1]["y"]]
    return "%d条(土留め %d ＋ 板塀 %d)" % (len(tw) + len(it), len(tw), len(it))


def kakoi_svg(d, kan="其九"):
    ken = d["const"]["ken"]
    W = 900.0
    rows = [r for r in d["runs"] if r["kind"] in ("透塀", "回廊", "板塀", "柵")]

    # ⛔ **長さは開口を抜いた実長**(`run_len_ken`)— これが発注量になる(検図10巡目 中1)。
    #    節点間の総和(`run_nodes_ken`)は**史料拘束を読むためだけ**に別に刷る。
    rows = [r for r in rows if run_len_ken(r) > 0]
    H = 76.0 + len(rows) * 46.0
    o = _sv(W, H, "囲いの展開")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    maxk = max(run_len_ken(r) for r in rows)
    for i, r in enumerate(rows):
        y = 52.0 + i * 46.0
        rk = run_len_ken(r)                             # 開口を抜いた実長[間]
        nk = run_nodes_ken(r)                           # 節点間の総和[間](開口を含む)
        L = 470.0 * rk / maxk
        col = {"透塀": "var(--shu)", "回廊": "var(--roka)"}.get(r["kind"], "var(--hei)")
        tg = run_tamagaki(d, r)
        if r["kind"] == "柵":
            # ⭐ **姿は `kind` で決める**【検図10巡目 中3】— 旧版は `hFrom` の有無で分岐していたので、
            #    同じ柵でも丈を宣言しない `Saku_SW`・`Saku_Sando` が**塗り潰しの塀の姿**で出ていた
            #    (平面図は `kind` で分岐しており物差しが二本あった)。
            #    腰高の柵は塗り潰しの塀ではなく **柱 + 貫二段**(作りは前庭の玉垣と同一)。
            #    ⛔ 丈も柱の芯々も此処に持たない — `hFrom` からの従属値。
            bh = 12.0
            for f in (0.32, 0.74):                      # 貫二段(`tamagaki.nuki`)
                o.append(LN(200, y + 20 - bh * f, 200 + L, y + 20 - bh * f,
                            stroke=col, sw=1.4, op=0.9))
            o.append(LN(200, y + 20, 200 + L, y + 20, stroke="var(--ink)", sw=0.6, op=0.5))
            if tg is not None:
                npst = max(2, int(round(rk / tg[0]["postPitchKen"])) + 1)
                # ⚠ 柱は**実数ぶん**引く(⛔ 間引かない)。紙の上で詰まる行は線を細くして潰れを避ける
                psw, pop = (1.1, 0.9) if L / (npst - 1.0) >= 4.0 else (0.4, 0.5)
                for j in range(npst):                   # 柱(芯々 `tamagaki.postPitchKen`)
                    px = 200 + L * j / (npst - 1.0)
                    o.append(LN(px, y + 20 - bh, px, y + 20, stroke=col, sw=psw, op=pop))
            # ⛔ 丈も柱の芯々も宣言しない柵は**柱を引かない**(刻みを発明しない)。
            #    宣言が無いことは丈の欄の「—」と検査「柵の宣言」が申告する。
        else:
            o.append(R(200, y, L, 20, fill=col, op=0.5, stroke="var(--ink)", sw=0.8))
            # 柱の刻み(1間ごと。折れ線の板塀は実長で刻む)
            for j in range(1, int(rk) + 1):
                o.append(LN(200 + L * j / rk, y, 200 + L * j / rk, y + 20,
                            stroke="var(--ink)", sw=0.4, op=0.5))
        o.append(T(194, y + 14, r["name"], fs=11, anchor="end"))
        seat = ("天端 %.1f m" % r["seat"]) if isinstance(r.get("seat"), (int, float)) else "地形なり"
        if tg is not None:
            take = "　丈 %.2f m(前庭の玉垣と同じ作り)" % tg[1]
        elif r["kind"] == "柵":
            take = "　丈 —(宣言が無い)"
        else:
            take = ""
        ext = ("　節点間 %.1f 間" % nk) if abs(nk - rk) > 5e-3 else ""
        o.append(T(212 + L, y + 14, "%.1f 間 = %.2f m%s　%s%s" % (rk, rk * ken, ext, seat, take),
                   fs=10.5))
        if r.get("gate"):
            o.append(T(200 + L / 2, y - 3, "◇ " + r["gate"], fs=10, anchor="middle", fill="var(--shu)"))
    tot = sum(run_nodes_ken(r) for r in rows if r["kind"] == "透塀")
    o.append(T(6, 15, kan + "　囲いの展開 ─ 長さは開口を抜いた実長(= 発注量)", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "透塀 計 %.0f 間 = %.3f m" % (tot, tot * ken), fs=11.5, anchor="end", fill="var(--shu)"))
    o.append(T(6, H - 26, "⛔ 発注量は棒の長さ(開口を抜いた実長)。「節点間」は開口を含む総和で、"
               "透塀の史料拘束だけがこちらで読む値", fs=10.5, fill="var(--dim)"))
    o.append(T(W - 6, H - 10, "透塀の史料値 147.28 m(486.01尺)との差 %.3f m(節点間で比べる)"
               % abs(tot * ken - 147.28), fs=10.5, anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


ws_cop = [29.0]


def face_toe(d, g, px, pz, nx, nz):
    """壁の外の法尻。返り (法尻の高さ, 犬走りの高さ or None)。

    ⚠ **回廊の東面は境内の平坦面の東の縁そのもの**(犬走りは 0.4間しかない)。
    壁から1.2m の点で測ると犬走りの上を拾って露出0.7mに見えてしまうので、
    **平場の縁の外に出るまで進んで、そこの地盤を法尻に採る**。縁が2mより遠ければ
    純粋に平場の中に立つ壁なので、平場の高さをそのまま法尻にする。
    """
    inside = lambda q: any(in_poly(q, terrace_poly(te, g)) for te in d["terraces"])
    bench = None
    t = 0.2
    while t <= 6.0:
        q = (px + nx * t, pz + nz * t)
        if not inside(q):
            if t > 2.0: break
            # 法尻 = 勾配 BATTER_ISHI の壁面と現地形の交点(断面 §3c の wall_steps と同じ式)
            base = dem_h(px + nx * t, pz + nz * t)
            if base is None: return (bench if bench is not None else plane_y(d, d["planes"][0])), None
            top = ws_cop[0]
            lo, hi, dep = 0.0, max(0.5, top - base) + 12.0, 0.0
            for _ in range(40):
                dep = (lo + hi) / 2.0
                h = dem_h(px + nx * (t + BATTER_ISHI * dep), pz + nz * (t + BATTER_ISHI * dep))
                if h is None: h = base
                if top - dep < h: hi = dep
                else: lo = dep
            return top - dep, bench
        for te in d["terraces"]:
            if in_poly(q, terrace_poly(te, g)): bench = te["y"]
        t += 0.2
    return (bench if bench is not None else plane_y(d, d["planes"][0])), None


# ---------------------------------------------------------------- 回廊の基壇の展開
def kidan_svg(d, kan="其十"):
    """回廊の基壇の石垣を四面ぶん展開する(スキル §3c の土留めの続き)。

    平面では露出高が読めない — 天端は 29.0 で一定でも、法尻は境内面(28.3)から
    平場の縁が退く北で深くなる。**南妻 → 東面 → 北妻 → 西面**の順に一周を伸ばす。
    """
    g = G(d)
    ken = d["const"]["ken"]
    order = ["TW_Kairo_S", "TW_Kairo_E", "TW_Kairo_N", "TW_Kairo_W"]
    ws = {w["name"]: w for w in d["terraceWalls"]}
    faces = []                                   # (名, 世界a, 世界b, 開口[(s0,s1)])
    for nm in order:
        w = ws[nm]
        a, b = w["a"], w["b"]
        if nm == "TW_Kairo_N": a, b = b, a       # 東→西へ回る
        if nm == "TW_Kairo_W": a, b = b, a       # 北→南へ回る
        faces.append((nm, g.W(a[0], a[1]), g.W(b[0], b[1]), w))
    # 一周の長さと、各面の始まりの位置
    segl = [math.hypot(b[0] - a[0], b[1] - a[1]) for _, a, b, _ in faces]
    tot = sum(segl)
    W = 900.0
    ML, MR, TOP = 74.0, 26.0, 46.0
    s = (W - ML - MR) / tot
    VEXK = 3.2
    vs = s * VEXK
    STEP = 0.5
    cop = ws["TW_Kairo_E"]["coping"]
    ws_cop[0] = cop
    kei = plane_y(d, d["planes"][0])

    rows, acc = [], 0.0
    for (nm, a, b, w), L in zip(faces, segl):
        dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -dz, dx                          # 左手法線
        # 外向きに直す(回廊の芯 u0,v0 から遠ざかる向き)
        cx, cz = g.W(0.0, 0.0)
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (mx - cx) * nx + (mz - cz) * nz < 0: nx, nz = -nx, -nz
        n = int(round(L / STEP))
        for i in range(n + 1):
            t = i * L / n
            px, pz = a[0] + dx * t, a[1] + dz * t
            dy, ben = face_toe(d, g, px, pz, nx, nz)
            nat = dem_h(px + nx * 1.2, pz + nz * 1.2)
            rows.append((acc + t, dy, nat if nat is not None else dy, nm, ben))
        acc += L

    ymin = min(r[1] for r in rows)
    y0 = min(ymin, min(r[2] for r in rows)) - 0.8
    y1 = cop + 1.6
    Hh = (y1 - y0) * vs
    H = Hh + TOP + 42.0
    X = lambda c: ML + c * s
    Y = lambda y: TOP + Hh - (y - y0) * vs
    o = _sv(W, H, "回廊の基壇の展開")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))

    # 石垣の胴(天端から法尻まで)
    body = [(X(c), Y(cop)) for c, _, _, _, _ in rows] + \
           [(X(c), Y(dy)) for c, dy, _, _, _ in reversed(rows)]
    o.append(PL(body, fill=_pat(), op=0.95, stroke="var(--ishi)", sw=1.2, close=True))
    # 石の目地 — ピッチ 1.80m / 段は 0.45m(CLAUDE.md の石垣モジュール)
    for j in range(1, 40):
        yy = cop - 0.45 * j
        seg = [(X(c), Y(yy)) for c, dy, _, _, _ in rows if dy <= yy]
        if len(seg) > 1:
            for k in range(len(seg) - 1):
                if seg[k + 1][0] - seg[k][0] < s * STEP * 1.6:
                    o.append(LN(seg[k][0], seg[k][1], seg[k + 1][0], seg[k + 1][1],
                                stroke="var(--ishi)", sw=0.5, op=0.5))
    ncol = int(tot / 1.80)
    for j in range(1, ncol + 1):
        c = j * 1.80
        dy = min(r[1] for r in rows if abs(r[0] - c) <= STEP) if any(abs(r[0] - c) <= STEP for r in rows) else None
        if dy is None or cop - dy < 0.5: continue
        yb = cop - 0.45 * int((cop - dy) / 0.45)
        o.append(LN(X(c), Y(cop), X(c), Y(max(dy, yb)), stroke="var(--ishi)", sw=0.4, op=0.35))
    # 天端・地盤
    o.append(PL([(X(c), Y(cop)) for c, _, _, _, _ in rows], stroke="var(--ink)", sw=2.0))
    o.append(PL([(X(c), Y(dy)) for c, dy, _, _, _ in rows], stroke="var(--ink)", sw=1.6))
    # 犬走り(壁の外の平場)がある区間だけ、その高さを細い線で重ねる
    bn = [(X(c), Y(bb)) for c, _, _, _, bb in rows if bb is not None]
    if len(bn) > 1:
        o.append(PL(bn, stroke="var(--take)", sw=1.4, op=0.9, dash="3 3"))
    o.append(PL([(X(c), Y(nt)) for c, _, nt, _, _ in rows], stroke="var(--dim)", sw=1.1, dash="5 3"))
    # 境内面の罫
    o.append(LN(ML, Y(kei), W - MR, Y(kei), stroke="var(--take)", sw=1.0, dash="8 5", op=0.8))
    o.append(T(ML - 6, Y(kei) + 4, "境内面 %.1f" % kei, fs=10, anchor="end", fill="var(--take)"))
    o.append(T(ML - 6, Y(cop) + 4, "天端 %.1f" % cop, fs=10, anchor="end", fill="var(--ink)"))

    # 面の境と名
    acc = 0.0
    LAB = {"TW_Kairo_S": "南妻", "TW_Kairo_E": "東面(表)", "TW_Kairo_N": "北妻", "TW_Kairo_W": "西面(裏)"}
    for (nm, a, b, w), L in zip(faces, segl):
        o.append(LN(X(acc), TOP - 6, X(acc), Y(y0), stroke="var(--shu)", sw=0.8, dash="4 4", op=0.7))
        o.append(T(X(acc + L / 2), TOP - 10, "%s %.1f 間" % (LAB[nm], L / ken), fs=11,
                   anchor="middle", fill="var(--shu)"))
        # 開口(楼門の門口)
        hw = w.get("gapHalf")
        if hw:
            cc = w.get("gapV") if abs(w["a"][0] - w["b"][0]) < abs(w["a"][1] - w["b"][1]) else w.get("gapU")
            if cc is not None:
                aa = w["a"] if nm != "TW_Kairo_N" else w["b"]
                i = 1 if abs(w["a"][0] - w["b"][0]) < abs(w["a"][1] - w["b"][1]) else 0
                g0 = acc + abs(cc - hw - aa[i]) * ken
                o.append(R(X(g0), Y(cop), abs(2 * hw * ken) * s, (Y(y0) - Y(cop)),
                           fill="var(--paper2)", op=0.95, stroke="var(--shu)", sw=1.0, dash="4 3"))
                o.append(T(X(g0 + hw * ken), Y(cop) - 5, "楼門の門口", fs=10,
                           anchor="middle", fill="var(--shu)"))
        acc += L
    o.append(LN(X(tot), TOP - 6, X(tot), Y(y0), stroke="var(--shu)", sw=0.8, dash="4 4", op=0.7))

    # 露出の最大と、面ごとの範囲
    mx = max(rows, key=lambda r: cop - r[1])
    o.append(LN(X(mx[0]), Y(cop), X(mx[0]), Y(mx[1]), stroke="var(--shu)", sw=1.6))
    o.append(T(X(mx[0]) + 5, Y((cop + mx[1]) / 2) + 4, "最大 %.2f m" % (cop - mx[1]),
               fs=11, fill="var(--shu)"))
    txt = []
    for nm in order:
        rr = [cop - r[1] for r in rows if r[3] == nm]
        txt.append("%s %.2f〜%.2f" % (LAB[nm], min(rr), max(rr)))
    o.append(T(6, 15, kan + "　回廊の基壇の展開 ─ 南妻 → 東面 → 北妻 → 西面(石垣の露出高)",
               fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "垂直 %.1f 倍 ／ 一周 %.1f 間 = %.1f m" % (VEXK, tot / ken, tot),
               fs=11, anchor="end", fill="var(--dim)"))
    o.append(T(6, H - 24, "露出高 ── " + " ／ ".join(txt), fs=10.5, fill="var(--ishi)"))
    o.append(T(W - 6, H - 8, "破線 = 現地形 ／ 細実線 = 法尻(平坦面の縁の外の地盤) ／ 点線 = 犬走り"
               " ／ 目地 = 石垣モジュール ピッチ 1.80 m・段 0.45 m", fs=10.5, anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 縁の始末
def fuchi_tally(d, g):
    """平場の縁を2m刻みで歩き、①法面で着地 / ②着地せず土留めが要る に分ける。"""
    cap = d["const"].get("featherCap", 12.0); bf = d["const"]["batterFill"]
    POLY = [(q[0], q[1]) for q in d["polygon"]]
    land, need, walled = [], [], []
    for te in d["terraces"]:
        P = terrace_poly(te, g)
        for i in range(len(P)):
            a, c = P[i], P[(i + 1) % len(P)]
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            if L < 1e-6: continue
            n = max(1, int(L / 2))
            dx, dz = (c[0] - a[0]) / L, (c[1] - a[1]) / L
            nx, nz = -dz, dx
            mid = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
            if in_poly((mid[0] + nx * 0.6, mid[1] + nz * 0.6), P): nx, nz = -nx, -nz
            for k in range(n + 1):
                q = (a[0] + dx * L * k / n, a[1] + dz * L * k / n)
                en = dem_h(*q)
                if en is None: continue
                if on_wall(d, g, *q): walled.append(te["y"] - en); continue
                dv = te["y"] - en
                if dv <= 0.05: continue
                t, hit = 0.2, None
                while t <= cap:
                    hh = dem_h(q[0] + nx * t, q[1] + nz * t)
                    if hh is None: break
                    if te["y"] - t / bf <= hh + 0.05: hit = t; break
                    t += 0.2
                if hit is None:
                    back, sft = None, 0.5
                    while sft <= 25.0:
                        hh = dem_h(q[0] - nx * sft, q[1] - nz * sft)
                        if hh is None: break
                        if hh >= te["y"] - 0.05: back = sft; break
                        sft += 0.5
                    need.append((dv, back))
                else:
                    land.append((hit, in_poly((q[0] + nx * hit, q[1] + nz * hit), POLY)))
    return land, need, walled


def fuchi_svg(d, kan="其十"):
    """縁の始末の三型。①法面 ②土留め ③引き戻し を同じ縮尺で並べる。"""
    g = G(d)
    land, need, walled = fuchi_tally(d, g)
    W, H = 900.0, 284.0
    o = _sv(W, H, "縁の始末")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    CW, CH, TOP, SC = 276.0, 148.0, 58.0, 15.0        # 枠 / 上端 / 15px = 1m
    TOPY, NAT = 6.8, 6.0                              # 平場の天端 / 縁の自然地盤(局所)

    def cell(idx, title, sub, drop, kind, note):
        ox = 12.0 + idx * 296.0
        X = lambda m: ox + 62.0 + m * SC
        Y = lambda m: TOP + CH - m * SC
        o.append(R(ox, TOP, CW, CH, fill="var(--paper)", stroke="var(--grid)", sw=0.8))
        o.append(T(ox + CW / 2, TOP - 26, title, fs=13, anchor="middle", fill="var(--shu)"))
        o.append(T(ox + CW / 2, TOP - 10, sub, fs=10.5, anchor="middle", fill="var(--dim)"))
        # 現地形(枠を出たら止める)
        gp = [(X(-4.0), Y(NAT)), (X(0.0), Y(NAT))]
        m = 0.0
        while m < 14.0:
            m += 0.25
            y = NAT - drop * m
            if Y(y) > TOP + CH: break
            gp.append((X(m), Y(y)))
        o.append(PL(gp, stroke="var(--dim)", sw=1.3, dash="5 3"))
        if kind == "slope":
            t = 0.8 / (1.0 / 1.5 - drop)
            dp = [(X(-4.0), Y(TOPY)), (X(0.0), Y(TOPY)), (X(t), Y(TOPY - t / 1.5))]
            o.append(PL(dp + [(X(t), Y(NAT - drop * t)), (X(-4.0), Y(NAT))],
                        fill=_fill(), stroke="none", close=True))
            o.append(PL(dp, stroke="var(--ink)", sw=2.2))
            o.append(T(X(t + 0.4), Y(TOPY - t / 3.0), "1:1.5 の法面", fs=10.5, fill="var(--take)"))
            o.append(T(X(t), Y(TOPY - t / 1.5) + 15, "法尻", fs=10, anchor="middle", fill="var(--dim)"))
            o.append(T(X(-3.6), Y(TOPY) - 7, "平場", fs=10.5, fill="var(--ink)"))
        elif kind == "wall":
            o.append(PL([(X(-4.0), Y(TOPY)), (X(0.0), Y(TOPY))], stroke="var(--ink)", sw=2.2))
            o.append(PL([(X(0.0), Y(TOPY)), (X(0.16), Y(NAT)), (X(-0.74), Y(NAT)),
                         (X(-0.9), Y(TOPY))], fill=_pat(), stroke="var(--ishi)", sw=1.3, close=True))
            o.append(LN(X(1.1), Y(TOPY), X(1.1), Y(NAT), stroke="var(--ishi)", sw=1.2))
            o.append(T(X(1.4), Y((TOPY + NAT) / 2) + 4, "土留めの露出", fs=10.5, fill="var(--ishi)"))
            o.append(T(X(1.4), Y(NAT - 1.6), "外が 1:1.5 より急なので", fs=10, fill="var(--dim)"))
            o.append(T(X(1.4), Y(NAT - 2.3), "法面が当たる先が無い", fs=10, fill="var(--dim)"))
            o.append(T(X(-3.6), Y(TOPY) - 7, "平場", fs=10.5, fill="var(--ink)"))
        else:
            # ③ 引き戻し ─ 肩(自然地盤が天端と同じになる点)まで縁を縮める
            gp = [(X(-4.0), Y(TOPY)), (X(-1.6), Y(TOPY))]
            m = 0.0
            while m < 14.0:
                m += 0.25
                y = TOPY - drop * m
                if Y(y) > TOP + CH: break
                gp.append((X(-1.6 + m), Y(y)))
            o.append(PL(gp, stroke="var(--dim)", sw=1.3, dash="5 3"))
            o.append(PL([(X(-4.0), Y(TOPY)), (X(-1.6), Y(TOPY))], stroke="var(--ink)", sw=2.4))
            o.append(LN(X(-1.6), Y(TOPY) - 30, X(-1.6), Y(TOPY) + 10,
                        stroke="var(--shu)", sw=1.0, dash="3 3"))
            o.append(T(X(-1.6), Y(TOPY) - 36, "肩", fs=12, anchor="middle", fill="var(--shu)"))
            o.append(PL([(X(-1.6), Y(TOPY)), (X(1.2), Y(TOPY))],
                        stroke="var(--shu)", sw=1.6, dash="5 3", op=0.9))
            o.append(LN(X(1.2), Y(TOPY), X(1.2), Y(TOPY - drop * 2.8), stroke="var(--shu)", sw=1.2))
            o.append(T(X(1.5), Y(TOPY) - 6, "旧い縁", fs=10.5, fill="var(--shu)"))
            o.append(T(X(1.5), Y(TOPY - drop * 1.7), "落差", fs=10, fill="var(--shu)"))
            o.append(T(X(-3.6), Y(TOPY) - 7, "平場(縮めた)", fs=10.5, fill="var(--ink)"))
        for li, tx in enumerate(note.split("\n")):
            o.append(T(ox + 4, TOP + CH + 20 + li * 15, tx, fs=10.5, fill="var(--ink)"))

    bk = sorted(q[1] for q in need if q[1]) or [3.5, 9.5]
    cell(0, "① 法面で摺り付ける", "外の斜面が 1:1.5 より緩い", 0.35, "slope",
         "縁の標本 %d\n法尻が社地の外へ出るもの %d" % (len(land), sum(1 for q in land if not q[1])))
    cell(1, "② 土留めで受ける", "外の斜面が 1:1.5 より急(崖の上)", 1.10, "wall",
         "土留めが受けている縁 %d 標本\n露出は断面と基壇の展開で読む ／ 受け無しの縁 %d" % (len(walled), len(need)))
    cell(2, "③ 縁を肩まで引き戻す", "落差そのものを消す", 0.90, "back",
         "2026-08-24 に 25 標本をこの手で処理\n引き戻し 中央 3.5 m ／ 最大 9.5 m(ユーザーの裁定)")
    o.append(T(6, 15, kan + "　縁の始末 ─ 平場の輪郭をどう地面に着けるか", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "破線 = 現地形 ／ 実線 = 設計地盤 ／ 縦横同率(1 m = %.0f px)" % SC,
               fs=10.5, anchor="end", fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 其十一 山麓
def sanroku_svg(d, kan="其十一"):
    g = G(d)
    pr = Proj(-505, -320, 715, 955, W=900.0, pad=6.0, top=26.0, bottom=24.0)
    o = _sv(pr.W, pr.H, "山麓 ─ 前庭・辻・別当・神主・門前町")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))
    # 社地
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in d["polygon"]], stroke="var(--ink)", sw=1.2,
                fill="var(--pl-slope)", op=0.4, close=True))
    # 前庭
    zt = d["terraces"][1]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in terrace_poly(zt, g)],
                fill="var(--pl-suso)", stroke="var(--ink)", sw=1.0, op=0.9, close=True))
    o.append(T(pr.X(-443), pr.Y(858), "前庭", fs=11.5, anchor="middle"))
    # 隣地
    for nb in d["neighbors"]:
        if "polygon" not in nb: continue
        Q = nb["polygon"]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in Q], stroke="var(--dim)", sw=1.1, dash="4 3",
                    fill="var(--paper)", op=0.5, close=True))
        cx = sum(p[0] for p in Q) / len(Q); cz = sum(p[1] for p in Q) / len(Q)
        o.append(T(pr.X(cx), pr.Y(cz), nb["name"], fs=11.5, anchor="middle", fill="var(--ink)"))
    # 境内の平場と社殿(位置の手がかり)
    kp = [g.W(u, v) for u, v in d["terraces"][0]["uv"]]
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in kp], stroke="var(--ink)", sw=1.0,
                fill="var(--pl-main)", op=0.7, close=True))
    for r in d["runs"]:
        if r["kind"] not in ("透塀", "回廊"): continue
        w0 = g.W(*r["a"]); w1 = g.W(*r["b"])
        o.append(LN(pr.X(w0[0]), pr.Y(w0[1]), pr.X(w1[0]), pr.Y(w1[1]),
                    stroke="var(--shu)" if r["kind"] == "透塀" else "var(--roka)", sw=2.0))
    # 石段(折れ線対応)
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in pts], stroke="var(--ishi)", sw=6.0, op=0.9))
        mid = pts[len(pts) // 2]
        o.append(T(pr.X(mid[0]), pr.Y(mid[1]) - 8, k["name"].split("(")[0], fs=10.5, anchor="middle"))
    # 山王門前町(CODH点)
    o.append(T(pr.X(-339), pr.Y(928), "山王門前町", fs=11.5, anchor="middle", fill="var(--ink)"))
    o.append(R(pr.X(-352), pr.Y(936), pr.L(26), pr.L(16), fill="none", stroke="var(--dim)", sw=1.0, dash="4 3"))
    # 勝手道(十坊・別当の側から山上へ上がる道。2026-08-23 追加)
    for seg in d.get("kattemichi", []):
        kp = [(pr.X(x), pr.Y(z)) for x, z in seg["pts"]]
        o.append(PL(kp, stroke="var(--take)", sw=3.0, op=0.9, dash="9 5"))
        # ⛔ 延長・比高・勾配を json に持たない — **図が現地形から算出する**(2026-09-06 検図4巡目 高1)
        _L, _gr = path_stats(seg["pts"])
        _h0, _h1 = dem_h(*seg["pts"][0]), dem_h(*seg["pts"][-1])
        o.append(T(kp[0][0] + 6, kp[0][1] + 4,
                   "%s %.0f m ／ 比高 %.1f m ／ 平均 %.1f%% ／ 最大 1m窓 %.0f%%・5m窓 %.0f%%"
                   % (seg["name"], _L, (_h1 or 0.0) - (_h0 or 0.0), _gr,
                      path_max_grade(seg["pts"], 1.0), path_max_grade(seg["pts"], 5.0)),
                   fs=10, fill="var(--take)"))

    # 麓道(山裾を回る小道。**一周しない** — 常明院で行き止まり)
    for seg in d.get("fumotomichi", []):
        fp = [(pr.X(x), pr.Y(z)) for x, z in seg["pts"]]
        o += road_draw(seg, pr.X, pr.Y, pr.L)
        o.append(PL(fp, stroke="var(--ink)", sw=0.6, dash="2 4", op=0.5))
    # 行き止まりの印
    fz = [s2 for s2 in d.get("fumotomichi", []) if "終端" in s2["name"]]
    if fz:
        ex, ez = fz[0]["pts"][-1]
        o.append(LN(pr.X(ex) - 5, pr.Y(ez) - 5, pr.X(ex) + 5, pr.Y(ez) + 5, stroke="var(--shu)", sw=1.6))
        o.append(LN(pr.X(ex) - 5, pr.Y(ez) + 5, pr.X(ex) + 5, pr.Y(ez) - 5, stroke="var(--shu)", sw=1.6))
        o.append(T(pr.X(ex) - 9, pr.Y(ez) + 4, "行止", fs=10, anchor="end", fill="var(--shu)"))
    # 参道(実幅の帯)と鳥居
    o += sando_band(d, pr.X, pr.Y, pr.L)
    sp = d["sando"]["pts"]
    for t in d["torii"]:
        if not t["pos"]: continue
        x, z = t["pos"]
        o.append(LN(pr.X(x) - 8, pr.Y(z), pr.X(x) + 8, pr.Y(z), stroke="var(--shu)", sw=2.6))
        o.append(T(pr.X(x) + 11, pr.Y(z) + 4, t["name"], fs=11, fill="var(--shu)"))
    # 坂下の門
    for gt in d["gates"]:
        if gt["name"] != "坂下の門": continue
        w = g.W(gt["u"], gt["v"])
        o.append(R(pr.X(w[0]) - 4, pr.Y(w[1]) - 6, 8, 12, fill="var(--shu)", stroke="var(--ink)", sw=1.0))
        o.append(T(pr.X(w[0]) - 8, pr.Y(w[1]) + 4, gt["name"], fs=11, anchor="end", fill="var(--shu)"))
    o += cut_lines(d, pr.X, pr.Y, pr.L,
                   clip=(14.0, pr.top + 10.0, pr.W - 14.0, pr.top + pr.zh - 6.0))
    o.append(T(6, 15, kan + "　山麓 ─ 二ノ鳥居の辻で折れて前庭へ入る", fs=12.5, fill="var(--dim)"))
    y = pr.H - 10
    o.append(LN(14, y, 14 + pr.L(50), y, stroke="var(--dim)", sw=1.2))
    o.append(T(14 + pr.L(50) / 2, y - 4, "50 m", fs=10.5, anchor="middle"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 門の立面
def mon_svg(d, kan="其十"):
    ken = d["const"]["ken"]
    W, H = 900.0, 300.0
    o = _sv(W, H, "門の立面")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    # 門の数に合わせて等間隔に割る(2026-08-23 に勝手口を足して3本固定では足りなくなった)
    ng = len(d["gates"])
    xs = [W * (i + 0.5) / ng for i in range(ng)]
    for i, gt in enumerate(d["gates"]):
        cx = xs[i]
        wk, dk = gt["plan"]["dv"], gt["plan"]["du"]      # 桁行(南北) / 梁間(東西)
        s = 20.0
        w = wk * ken * s / ken                            # px/間 = s
        bw = wk * s
        two = "楼門" in gt["kind"] or "二天門" in gt["name"]
        bh = (2.6 if two else 1.6) * s
        y0 = 232.0
        # 基壇
        o.append(R(cx - bw / 2 - 6, y0, bw + 12, 10, fill=_pat(), stroke="var(--ink)", sw=0.8))
        # 躯体
        o.append(R(cx - bw / 2, y0 - bh, bw, bh, fill="var(--shu)", op=0.35, stroke="var(--ink)", sw=1.0))
        # 柱
        for j in range(int(wk) + 1):
            px = cx - bw / 2 + bw * j / wk
            o.append(LN(px, y0, px, y0 - bh, stroke="var(--ink)", sw=1.4))
        # 屋根
        o.append(PL([(cx - bw / 2 - 14, y0 - bh), (cx, y0 - bh - 26), (cx + bw / 2 + 14, y0 - bh)],
                    stroke="var(--ink)", sw=1.2, fill="var(--hei)", op=0.55, close=True))
        if two:   # 二階の縁と腰屋根
            o.append(LN(cx - bw / 2 - 8, y0 - bh * 0.55, cx + bw / 2 + 8, y0 - bh * 0.55,
                        stroke="var(--ink)", sw=1.2))
        # 開口(一戸)
        o.append(R(cx - s * 0.5, y0 - bh * 0.62, s, bh * 0.62, fill="var(--paper)",
                   stroke="var(--ink)", sw=0.9))
        o.append(T(cx, y0 + 30, gt["name"], fs=13, anchor="middle"))
        o.append(T(cx, y0 + 46, gt["kind"], fs=10, anchor="middle", fill="var(--dim)"))
        o.append(T(cx, y0 + 60, "敷居 %.1f m ／ 桁行 %g 間 × 梁間 %g 間" % (gt["sill"], wk, dk),
                   fs=10, anchor="middle", fill="var(--dim)"))
        o.append(T(cx, y0 + 74, gt["acc"], fs=9.5, anchor="middle", fill="var(--dim)"))
    o.append(T(6, 15, kan + "　門の立面 ─ 高さと屋根は図示のための概略", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "**寸法が確度Sなのは社殿5棟+中門(旧国宝5件)**", fs=10.5, anchor="end", fill="var(--shu)"))
    o.append(ENDSVG)
    return "\n".join(o)


# ---------------------------------------------------------------- 表
def munes_table(d):
    ken = d["const"]["ken"]
    rows = []
    for m in d["munes"]:
        w = m["du"] * ken; dpt = m["dv"] * ken
        rows.append("<tr><td>%s</td><td>%s</td><td>%g 間</td><td>%g 間</td><td>%.2f×%.2f m</td>"
                    "<td>%.0f m²</td><td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (m["name"], m["yaku"], m["dv"], m["du"], w, dpt, w * dpt,
                       html.escape(m["roof"]), m["acc"]))
    return ('<div class="tw"><table><thead><tr><th>棟</th><th>役</th><th>桁行(南北)</th><th>梁間(東西)</th>'
            "<th>外形 東西×南北</th><th>面積</th><th class='note'>屋根</th><th class='note'>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def runs_table(d):
    ken = d["const"]["ken"]
    rows = []
    for r in d["runs"]:
        # ⭐ **長さは開口を抜いた実長**【検図10巡目 中1】— 旧版は `ken`(節点間の総和)を刷っており、
        #    石段の頭・勝手口・中門・潜りを一つも抜いていなかった。⛔ 発注量はこちらの欄で読む。
        rl, nk = run_len_ken(r), run_nodes_ken(r)
        L = ("%.1f 間 / %.2f m" % (rl, rl * ken)) if rl > 0 else "—"
        # ⭐ **節点間**は開口を含む総和。透塀の史料拘束(周長 147.28 m【S】)だけがこちらの数と比べる
        NK = ("%.1f 間 / %.2f m" % (nk, nk * ken)) if nk > 0 else "—"
        seat = ("%.1f m" % r["seat"]) if r.get("seat") else "地形なり"
        # ⭐ **厚み**は `const.itabeiThickM`(在庫 itabei5 の実寸 × ES)。板塀だけが持つ
        #    (2026-09-06 検図5巡目 低16 — `joints` が「塀の厚みは門より薄い」と定めるのに値が無かった)
        # ⭐ **柵は立子の径と柱の径**を刷る【検図10巡目 軽微7】— `_runs` が「柵は立子の径
        #    `tamagaki.tatekoDiaM`」と書くのに表が「—」で、実装が面で寄せる(規則5)ための数が引けなかった。
        tg = run_tamagaki(d, r)
        if r["kind"] == "板塀":
            th = "%.3f m" % d["const"]["itabeiThickM"]
        elif r["kind"] == "柵" and tg is not None:
            th = "立子 φ%.3f ／ 柱 φ%.3f m" % (tg[0]["tatekoDiaM"], tg[0]["postDiaM"])
        else:
            th = "—"
        # ⭐ **丈**は宣言(`hFrom`)を持つ物だけが持つ従属値【ユーザー裁定 2026-09-07 — 境内の柵】。
        #    ⛔ 数を json に置かない — 前庭の玉垣 `tamagaki.hM` から毎回引く(規則4)。
        tk = run_take_m(d, r)
        tk = ("%.2f m" % tk) if tk is not None else "—"
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td><td>%s</td>"
                    "<td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (r["name"], r["kind"], L, NK, th, tk, seat, r.get("base", "—"),
                       html.escape(r.get("gate", "") or "—"), r.get("acc", "—")))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>種別</th>'
            "<th>長さ(開口を抜いた実長)</th><th class='note'>節点間(開口を含む)</th><th>厚み</th>"
            "<th>丈</th><th>天端</th><th>基壇</th><th class='note'>開口</th><th class='note'>確度</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def kaidan_table(d):
    ken = d["const"]["ken"]
    rows = []
    for k in d["kaidans"]:
        L = seg_len(k, ken)
        rise = k["yTop"] - k["yBot"]
        rows.append("<tr><td>%s</td><td>%d</td><td>%.3f</td><td>%.3f</td><td>%.2f m</td><td>%.2f m</td>"
                    "<td>%.1f%%</td><td>%g 間(%.3f m)</td><td>%s</td></tr>"
                    % (k["name"], k["steps"], rise / k["steps"], L / k["steps"], rise, L,
                       rise / L * 100, kaidan_wken(d, k), kaidan_wm(d, k), k["acc"]))
    return ('<div class="tw"><table><thead><tr><th>石段</th><th>段数</th><th>蹴上</th><th>段の間隔</th>'
            "<th>比高</th><th>平面長</th><th>勾配</th><th>幅</th><th>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def _coping_txt(w):
    c = w.get("coping")
    if isinstance(c, (int, float)): return "%.1f m" % c
    return {"stair": "坂なり(石段に従う)"}.get(c, str(c))


def walls_table(d):
    rows = []
    for w in d["terraceWalls"]:
        cop = _coping_txt(w)
        sg = segs(w)
        loc = " → ".join("(%.1f, %.1f)" % (q[0], q[1]) for q in ([sg[0][0]] + [b for _, b in sg]))
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (w["name"], loc, cop, w.get("acc", "—"), inline(w.get("_", ""))))
    return ('<div class="tw"><table><thead><tr><th>土留め</th><th>グリッド (u,v)</th><th>天端</th><th>確度</th>'
            "<th class='note'>注記</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def kenpei_bottom_area(d):
    """建蔽率の**分子**(屋根の水平投影)[m²]と、その内訳の〔記録〕・宣言の⛔。

    ⚠ 2026-09-07 検図8巡目 低7 — 旧版は `yaku != "接続"` で棟をふるい落とし、
    **作り合い**(本殿と幣殿を継ぐ一間。⛔ 当図は幣殿型なので『石の間』と呼ばない)を
    分子から外していた。⚠ **分子に入れるのは【U 設計判断】** — 三棟を一続きの屋根で覆うと
    読んだ帰結で、史料は作り合いの屋根の有無を言わない【?】(考証6巡目 中1)。同じ図の `plane_dev_check` の註は
    「⛔ `yaku` で棟をふるい落とさない — 『作り合い』は屋根も礎石も持つ一棟」と書いており、
    井戸屋形を「**屋根を持つから**入れる」で足した基準(検図5巡目 低22)とも非対称だった。
    ⛔ 役の名で落とさない ── 落とすのは**屋根を持たない役**だけで、名簿は
    `const.kenpeiNoRoofYaku` が宣言する(空でよい)。⛔ 宣言が無ければ⛔で止める(規則19)。
    ⚠ 回廊は `munes` ではなく `runs[].mune` で足すので**二重に数えない**。
    """
    ken = d["const"]["ken"]
    ro = d["const"].get("kenpeiNoRoofYaku")
    bad = []
    if ro is None:
        bad.append("`const.kenpeiNoRoofYaku`(屋根を持たない役の名簿)の宣言が無い — "
                   "宣言の無いふるいは黙って棟を落とす(規則19)")
        ro = []
    unk = [q for q in ro if q not in set(m["yaku"] for m in d["munes"])]
    if unk:
        bad.append("`const.kenpeiNoRoofYaku` の『%s』が `munes[].yaku` に無い — 死んだ名簿"
                   % "』『".join(unk))
    drop = [m["name"] for m in d["munes"] if m["yaku"] in ro]
    a_m = sum(m["du"] * m["dv"] for m in d["munes"] if m["yaku"] not in ro) * ken * ken
    a_r = sum(r.get("bari", 2) * r["ken"] for r in d["runs"] if r.get("mune")) * ken * ken
    a_g = sum(gt["plan"]["du"] * gt["plan"]["dv"] for gt in d["gates"]) * ken * ken
    # ⭐ **井戸屋形は屋根を持つ建物**なので底面積に入る(2026-09-06 検図5巡目 低22)。
    #    ⛔ 呼び寸法ではなく**軒先の平面**で採る(建蔽率は屋根の水平投影)。
    a_i = 0.0
    _ir = ido_rects(d)
    if _ir:
        _no = _ir["軒先"]
        a_i = (_no[2] - _no[0]) * (_no[3] - _no[1]) * ken * ken
    note = ["建蔽率の分子 %.1f m²(棟 %d 件 %.1f ／ 屋根付きの run %.1f ／ 門 %.1f ／ 井戸屋形の軒先 %.1f)"
            "── 屋根を持たない役の名簿 %s・落とした棟 %s。⚠ **『作り合い』の屋根だけは【U 設計判断】**(三棟を一続きの屋根で覆うと読んだ帰結で、史料は屋根の有無を言わない【?】・考証6巡目 中1)【算出】"
            % (a_m + a_r + a_g + a_i,
               len([m for m in d["munes"] if m["yaku"] not in ro]), a_m, a_r, a_g, a_i,
               ("『" + "』『".join(ro) + "』") if ro else "空(すべての棟が屋根を持つ)",
               ("『" + "』『".join(drop) + "』") if drop else "無し")]
    return a_m + a_r + a_g + a_i, bad, note


def bom_table(d):
    rows = []
    for b in d["bom"]:
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td>%s</td></tr>"
                    % (inline(b["部材"]), inline(b["在庫"]), inline(b["手当"]), b["優先"]))
    return ('<div class="tw"><table><thead><tr><th>部材</th><th>在庫</th><th class="note">手当</th>'
            "<th>優先</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _rng(v, unit="", fmt="%g"):
    """[lo,hi] は「lo〜hi」、単値はそのまま、無ければ「—」。"""
    if v is None: return "—"
    if isinstance(v, (list, tuple)): return "%s〜%s%s" % (fmt % v[0], fmt % v[1], unit)
    return (fmt % v) + unit


def shaso_table(d, g):
    """社叢の帯 ── 面・密度・芯々・樹高・層。⛔ 数値を文章に写さない(この表が唯一の出口)。

    ⭐ **面積も本数も定数では持たない** — 帯1〜3 は `planting.bandDef` の走査、帯4 は多角形と
    `avoid` の宣言から算出する(2026-09-06 庭方 高3・検図 中5)。
    """
    rows = []
    for r in band_stats(d, g):
        if "b" not in r: continue
        b = r["b"]
        if b.get("uv"):
            rge = "多角形(uv %d点)" % len(b["uv"])
            if b.get("yRange"): rge += " ／ 標高 %g〜%g m" % tuple(b["yRange"])
        else:
            rge = "法肩からの下り %.0f〜%.0f%%" % (b["from"] * 100, b["to"] * 100)
        area = "%s 坪【算出】" % format(int(round(r["tsubo"])), ",")
        if r["avoid"] > 0.05:
            area += "(退避 %s → 有効 %s)" % (format(int(round(r["avoid"])), ","),
                                             format(int(round(r["usable"])), ","))
        if r["rinen"] > 0.05:
            area += " ／ うち林縁 %s 坪(高木0)" % format(int(round(r["rinen"])), ",")
        n = "%d 本" % int(round(r["takagi"]))
        if r["cut"]:
            n += "(視線の塊 %g 本を差し引き済み)" % r["cut"]
        dens = _rng(b.get("takagiPer100"))
        dens += "(採用 %g)" % r["dens"]
        rows.append("<tr><td>帯%d %s</td><td class='note'>%s</td><td>%s</td><td>%s</td>"
                    "<td>%s</td><td>%s m</td><td>%s m</td><td>%s</td>"
                    "<td>%s / %s m</td><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (b["band"], b["name"], rge, area, n, dens,
                       _rng(b.get("spacing")), _rng(b.get("matsuH")),
                       (("%.1f割 (%d 本)" % (b["rakuyoRatio"] * 10, int(round(r["rakuyo"]))))
                        + " ／ 丈 " + _rng(b.get("rakuyoH")) + " m") if b.get("rakuyoRatio") else "—",
                       _rng(b.get("chubokuPer100")), _rng(b.get("chubokuH")),
                       _rng(b.get("teibokuPer100")) + (" / %s m" % _rng(b.get("teibokuH"))
                                                       if b.get("teibokuH") else ""),
                       b.get("shitakusa", "—"), b.get("acc", "—")))
    for b in d["slopeBands"]:
        r = b.get("rinen")
        if not r: continue
        rows.append("<tr><td>└ 林縁の帯</td><td class='note'>社地の境から %g〜%g 間</td><td>—</td>"
                    "<td>0 本(高木を置かない)</td><td>%g</td><td>—</td><td>—</td><td>—</td>"
                    "<td>—</td><td>%s</td><td>%s</td><td class='note'>帯4の規定</td></tr>"
                    % (r["fromKen"], r["toKen"], r["takagiPer100"],
                       _rng(r.get("teibokuPer100")), r.get("shitakusa", "—")))
    ac = "".join("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td>%s</td>"
                 "<td class='note'>%s</td></tr>"
                 % (i, html.escape(cl), html.escape(got),      # ⚠ 条項に < があるので必ず逃がす
                    "⭕ 成り立つ" if ok else "⚠ 成り立たない",
                    "⛔ 組む条件" if gate else "〔記録〕— 組む条件にしていない")
                 for i, cl, got, ok, gate in band_invariants(d, g))
    acc = ('<div class="tw"><table><thead><tr><th>不変条件</th><th>条項</th><th class="note">現況</th>'
           "<th>判定</th><th class='note'>扱い</th></tr></thead><tbody>%s</tbody></table></div>" % ac)
    return ('<div class="tw"><table><thead><tr><th>帯</th><th class="note">範囲</th><th>面積</th>'
            "<th>高木</th><th>密度 本/100m²</th><th>芯々</th><th>松の丈</th><th>落葉 割合・本数／丈</th>"
            "<th>中木 密度／丈</th><th>低木 密度</th><th>下草</th><th class='note'>確度</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>" + acc)


def _gname(gd):
    return ("社叢 帯%d %s" % (gd["band"], gd["name"])) if gd.get("band") else gd["name"]


def tachiki_table(d, g):
    """境内の立木3区と前庭の木 ── 面・塊・部材・樹冠・一本立ち。

    ⭐ **`tsuboUsable` は持たない** — 退避は輪郭に焼き込んであるので、面積そのものが植えられる面。
    ⭐ 樹冠は部材と丈からの**従属値**(`planting.scaleRule`・目録)。
    """
    ken = d["const"]["ken"]
    rows = []
    src = list(d["gardens"]) + [b for b in d["slopeBands"] if b.get("clusters") or b.get("singles")]
    for gd in src:
        P = garden_poly(gd)
        if gd.get("noPlant"):                     # 空地(供待)── 面だけ出す
            rows.append("<tr><td>%s</td><td>%s 坪【算出】</td><td>空地(何も置かない)</td>"
                        "<td class='note'>(%g, %g)〜(%g, %g)</td><td>—</td><td>—</td><td>—</td>"
                        "<td class='note'>%s</td></tr>"
                        % (gd["name"], format(int(round(poly_area(P) * ken * ken / TSUBO)), ","),
                           P[0][0], P[0][1], P[2][0], P[2][1],
                           "御成の駕籠を降りて供が待つ場。⛔ 駕籠寄せは建てない"))
            continue
        if not (gd.get("clusters") or gd.get("singles") or gd.get("tamagaki")): continue
        ar = ("%s%s 坪【算出】" % ("囲いの内 " if gd.get("polyIsFence") else "",
                                   format(int(round(poly_area(P) * ken * ken / TSUBO)), ","))) \
            if P else "前庭の中"
        first = True
        for c in gd.get("clusters", []):
            bx = " / ".join("(%g,%g)〜(%g,%g)" % q for q in cluster_boxes(c))
            if not bx:
                bx = "高木の縁の線に沿う 幅%g間の帯 ／ v %g〜%g" % (
                    c.get("widthKen", 0), c["vRange"][0], c["vRange"][1])
            if c.get("split"): bx += " ／ " + c["split"]
            rl = c.get("role", "")
            if c.get("overhangFrom"):
                oh = overhang_range(d)
                # ⛔ **符号を捨てない**(2026-09-07 中2)— 負 = 一本も道の上へ出ない、が答え
                if oh and oh[0] is not None:
                    rl += ("(道への張り出し %+.2f〜%+.2f m【従属】"
                           "／負 = 道へ出ない・引けない部材 %d 点)" % (oh[0], oh[1], oh[3]))
                else:
                    rl += "(道への張り出しは**部材が目録に無く測れない**)"
            pt = ""
            if gd.get("hBand"):
                seg = []
                for kind, part, n, h, cr in cluster_parts(d, gd, c):
                    hh = ("丈 %s m" % _rng(h)) if h else "丈—"
                    cc = ("樹冠 %.1f〜%.1f m" % cr) if cr else "樹冠—(目録に無い)"
                    ov = ""
                    if cr and c.get("spacing"):
                        # ⭐ 2026-09-07 庭方3巡目 低6② — **`packRatio` を掛けた後の数を刷る**。
                        #   掛ける前の数(宣言の芯々)で刷ると「塊の中で樹冠が触れない」と読め、
                        #   塊が塊にならない読みになる。塊の中の実際の芯々は詰めた後の値。
                        pk = d["planting"]["plantRule"].get("packRatio", 1.0)
                        gp = c["spacing"] * ken * pk - (cr[0] + cr[1]) / 2.0
                        ov = "／ 塊内の芯々(packRatio 後)−樹冠 %+.1f m" % gp
                    seg.append("%s×%d <span class='note'>%s・%s・%s %s</span>"
                               % (part["prefab"], n, hh, cc, part["api"], ov))
                pt = "<br>".join(seg)
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td>"
                        "<td>%s</td><td>%s 間</td><td>%s</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "", c["name"], bx,
                           cluster_label(c).split(" ")[-1], _rng(c.get("spacing")),
                           pt or c.get("mix", "—"), rl))
            first = False
        for sg in gd.get("singles", []):
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='note'>(%g, %g)</td>"
                        "<td>1本</td><td>—</td><td>%s%s</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "",
                           sg["name"], sg["uv"][0], sg["uv"][1], sg.get("kind", "—"),
                           _single_dims(d, sg), sg.get("role", "")))
            first = False
        _sh = gd.get("shrubs")
        if _sh and _sh.get("box"):
            _n = len(island_shrubs(gd, ken))
            rows.append("<tr><td>%s</td><td>%s</td><td>低木を撒く面</td>"
                        "<td class='note'>枠 u %g〜%g・v %g〜%g ∩ 輪郭から %g 間 内</td><td>%d 本</td>"
                        "<td>%.2f m 芯々</td><td>%s</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "",
                           _sh["box"][0], _sh["box"][2], _sh["box"][1], _sh["box"][3],
                           _sh.get("crownRKen", 0.0), _n, _sh["spacingM"], _sh["veg"],
                           "⛔ 本数は設計値ではない — 面と芯々からの従属値(木戸の裏は空ける)"))
            first = False
        tgs = tamagaki_stats(d, gd)
        if tgs:
            tg = gd["tamagaki"]
            eg = tamagaki_edges(d, gd)
            # ⭐ **呼称は「腰高柵」に一本化した**【ユーザー裁定 2026-09-07・検図10巡目 中2】—
            #    同じ丈・同じ作りの物を、境内では「腰高の柵」、前庭では「⛔『腰高』とは呼ばない」と
            #    書いており、相反する呼称規則が二つ立っていた。⚠ 考証の指摘は註として残す。
            rows.append("<tr><td>%s</td><td>%s</td><td>玉垣(腰高柵。⚠『腰高』は形の呼び名で"
                        "寸法の主張ではない)</td>"
                        "<td class='note'>立てる辺 %s ／ ⛔ %s</td><td>柱 %d 本</td>"
                        "<td>%g 間</td><td>高 %.2f m ／ 柱 φ%.3f ／ 貫 %d 段 ／ 立子 φ%.3f を %.2f m 間隔</td>"
                        "<td class='note'>延長 %.2f 間【算出】%s ／ 辺ごとの割り【算出】%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "",
                           "・".join(q[0] for q in eg if q[3]),
                           "・".join(q[0] + "は立てない" for q in eg if not q[3]),
                           tgs[1], tg["postPitchKen"], tg["hM"], tg["postDiaM"], tg["nuki"],
                           tg["tatekoDiaM"], tg["tatekoPitchM"], tgs[0],
                           (" ／ %s 幅 %.2f m を (%g, %g)・辺『%s』に開ける"
                            % (tg["kido"]["name"], tg["kido"]["wM"],
                               tg["kido"]["uv"][0], tg["kido"]["uv"][1],
                               [q["name"] for q in tg["edges"]
                                if q["i"] == tg["kido"]["edge"]][0])) if tg.get("kido") else "",
                           " ／ ".join("『%s』%s m" % (nm, "+".join(
                               "%.3f" % (math.hypot(rn[1][0] - rn[0][0], rn[1][1] - rn[0][1]) * ken)
                               for rn in rs)) for nm, _a, _b, fence, _ln, rs in eg if fence)))
            first = False
        if gd.get("shrubs"):
            sh = gd["shrubs"]
            n = len(island_shrubs(gd, ken))
            _bx = ("撒く面 u %g〜%g × v %g〜%g(⛔ 玉垣の輪郭ではない)"
                   % (sh["box"][0], sh["box"][2], sh["box"][1], sh["box"][3])) \
                if sh.get("box") else sh.get("insetRule", "—")
            rows.append("<tr><td>%s</td><td>%s</td><td>帯の照葉低木</td>"
                        "<td class='note'>%s</td><td>%d 本【算出】</td>"
                        "<td>%.2f m</td><td>%s ／ 丈 %s m</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "", _bx,
                           n, sh["spacingM"], sh["veg"], _rng(sh["hM"]),
                           "⛔ 本数は設計値ではない — 面と芯々からの従属値(木戸の裏は空ける)"))
            first = False
        if gd.get("shitakusa") and gd.get("shrubs"):
            rows.append("<tr><td></td><td></td><td>帯の下草</td><td class='note'>—</td><td>—</td>"
                        "<td>—</td><td>%s</td><td class='note'>Terrain の Detail Mesh</td></tr>"
                        % gd["shitakusa"])
        if gd.get("clusterGapMin"):
            rows.append("<tr><td></td><td></td><td>塊間の下限</td>"
                        "<td class='note'>—</td><td>—</td><td>%g 間</td><td>—</td>"
                        "<td class='note'>塊どうしを近づけすぎない目安</td></tr>" % gd["clusterGapMin"])
    for gd in d["gardens"]:
        sk = gd.get("shukei")
        if not sk: continue
        rows.append("<tr><td></td><td></td><td>★主景の木(%s)</td>"
                    "<td class='note'>(%g, %g)・眼高 %.1f m の楼門から</td><td>1本</td><td>—</td>"
                    "<td>%s 丈 %.0f m 以上 ／ %s</td><td class='note'>%s</td></tr>"
                    % (sk["tree"]["cluster"], sk["tree"]["uv"][0], sk["tree"]["uv"][1],
                       sk["eyeY"], sk["tree"]["kind"], sk["tree"]["hMin"],
                       sk["tree"].get("part", "—"),
                       "松の丈では梢が本殿の棟に隠れる ─ 位置を固定する"))
    pl = d.get("planting", {}).get("edgeUnderstory")
    if pl:
        rows.append("<tr><td>平場の縁の下層</td><td>—</td><td>低木の帯</td>"
                    "<td class='note'>縁のオフセット線から内側 %g 間</td><td>—</td><td>%g 間</td>"
                    "<td>%s</td><td class='note'>3区が共有する辺なので一度だけ定める</td></tr>"
                    % (pl["insetKen"], pl["spacing"], pl["veg"]))
    tot = sum(n for _, n, _ in plant_rows(d, g) if n)
    br = "".join("<tr><td class='note'>%s</td><td class='note'>%s</td><td class='note'>%s 本</td></tr>"
                 % (a, c, b) for a, b, c in plant_rows(d, g))
    tally = ('<div class="tw"><table><thead><tr><th>高木の内訳</th><th>出どころ</th><th>本数</th>'
             "</tr></thead><tbody>%s<tr><td><b>計</b></td><td></td><td><b>%d 本</b></td></tr>"
             "</tbody></table></div>" % (br, tot))
    return ('<div class="tw"><table><thead><tr><th>区</th><th>面積</th><th>塊</th>'
            "<th class='note'>箱 (u,v)</th><th>本数</th><th>塊内芯々</th><th>部材・丈・樹冠</th>"
            "<th class='note'>役</th></tr></thead><tbody>" + "".join(rows)
            + "</tbody></table></div>" + tally)


def obi_garden(d):
    """前庭の帯(輪郭が囲いの線である区)。無ければ None。"""
    q = [gd for gd in d["gardens"] if gd.get("polyIsFence")]
    return q[0] if q else None


def zentei_yochi(d, g):
    """**帯の東に残る余地の内訳** ── 帯の東縁・通行帯・前庭の東縁からの従属値。

    ⛔ 内訳を json に書かない(規則4)。帯の v の中ほどで東西に切って読む。
    """
    gd = obi_garden(d)
    if not gd: return None, []
    ken = d["const"]["ken"]
    P = [(q[0], q[1]) for q in gd["poly"]]
    ue = max(q[0] for q in P)
    vm = (min(q[1] for q in P) + max(q[1] for q in P)) / 2.0
    uz = max(q[0] for q in terrace_poly_uv(d["terraces"][1]))
    band = None
    # ⛔ `wByTerrace` の有無で分岐しない(2026-09-06 検図5巡目 中6)— 幅は
    #    `route_w` が脚ごとに(段と門口から)引く。宣言を外したら**縁台が通行帯へ出て鳴る**。
    for rt in d.get("routes", []):
        pts = [(g.U(q[0]), g.V(q[1])) if rt.get("world") else (q[0], q[1]) for q in rt["pts"]]
        for i in range(len(pts) - 1):
            (ua, va), (ub, vb) = pts[i], pts[i + 1]
            if abs(vb - va) < 1e-9 or not (min(va, vb) <= vm <= max(va, vb)): continue
            u = ua + (ub - ua) * (vm - va) / (vb - va)
            mid = ((ua + ub) / 2.0, (va + vb) / 2.0)
            hw = route_w(d, rt, terrace_at(d, g, mid), at=mid) / 2.0 / ken
            if ue < u < uz: band = (rt["name"], u - hw, u + hw)
        if band: break
    rows = []
    if band:
        rows.append(("縁台の帯(帯の東縁 → 通行帯の西縁)", ue, band[1]))
        rows.append(("表参の路面(通行帯)", band[1], band[2]))
        rows.append(("東の余地(供待+東縁の犬走り)", band[2], uz))
    else:
        rows.append(("帯の東縁 → 前庭の東縁", ue, uz))
    return vm, rows


def zentei_yochi_table(d, g):
    vm, rows = zentei_yochi(d, g)
    if vm is None: return ""
    ken = d["const"]["ken"]
    tr = "".join("<tr><td>%s</td><td class='note'>u %.3f 〜 %.3f</td><td>%.3f 間</td><td>%.2f m</td></tr>"
                 % (nm, a, b, b - a, (b - a) * ken) for nm, a, b in rows)
    tot = rows[-1][2] - rows[0][1]
    tr += ("<tr><td><b>計</b></td><td class='note'>帯の東縁 → 前庭の東縁</td>"
           "<td><b>%.3f 間</b></td><td><b>%.2f m</b></td></tr>" % (tot, tot * ken))
    return ('<div class="tw"><table><thead><tr><th>帯の東に残る余地(v %.3f で切る)</th>'
            "<th class='note'>u の区間</th><th>幅</th><th>幅</th></tr></thead><tbody>"
            % vm + tr + "</tbody></table></div>")


def endai_rows(d):
    """縁台(床几) ── **玉垣からの背の隙・東の張り出し・通行帯までの余裕・隣との芯々**は従属値。

    ⛔ 等間隔にしない(庭方)ので、塊の中と塊の間の芯々の比を図が出す。
    """
    ken = d["const"]["ken"]
    gd = obi_garden(d)
    ue = max(q[0] for q in gd["poly"]) if gd else None
    pr = [p for p in d.get("props", []) if p["name"] == "縁台(床几)"]
    if not pr: return []
    pr = pr[0]
    Q = dict((nm, P) for nm, P in prop_rects(d) if nm.startswith(pr["name"]))
    out = []
    for i, (u, v) in enumerate(pr["uv"]):
        lab = prop_label(pr, i)
        P = Q.get("%s %s" % (pr["name"], lab))
        if not P: continue
        w0, w1 = min(q[0] for q in P), max(q[0] for q in P)
        prev = math.hypot(u - pr["uv"][i - 1][0], v - pr["uv"][i - 1][1]) * ken if i else None
        out.append((lab, u, v, (pr.get("yaw") or [0] * 9)[i],
                    (w0 - ue) * ken if ue is not None else None, w1, prev))
    return out


def endai_gaps(d):
    """縁台どうしの**外形の離れ**[m] ── (甲1, 甲2, 離れ) の列。負なら食い合い。

    ⭐ 2026-09-07 報告1(庭方)— 乙1 と 乙2 の外形が 0.164 m 食い合っていたのを検図が測っていなかった。
    芯々(`endai_rows` の「隣との芯々」)は**芯の距離**で、長手を向け合った二基の食い合いは映らない。
    """
    pr = [p for p in d.get("props", []) if p["name"] == "縁台(床几)"]
    if not pr: return []
    pr = pr[0]
    ken = d["const"]["ken"]
    R = [(prop_label(pr, i), prop_rect_of(d, pr["name"], prop_label(pr, i)))
         for i in range(len(pr["uv"]))]
    R = [q for q in R if q[1]]
    out = []
    for i in range(len(R)):
        for j in range(i + 1, len(R)):
            out.append((R[i][0], R[j][0], obb_gap(R[i][1], R[j][1]) * ken))
    return out


def endai_kokage(d):
    """縁台の**木陰の余裕**[m] ── (縁台, 木, 余裕) の列。負なら芯が樹冠の投影の外。

    ⭐ 2026-09-07 報告2(庭方)— 物差しを「外形の最遠隅」から**縁台の芯**へ改めた
    (`planting.plantRule.crownRule.kokage`)。木陰が要るのは午後で影は東へ伸び、縁台は4基とも
    樹の東にあるので、真昼の投影に外形の隅まで入れる必要はない。
    """
    pr = [p for p in d.get("props", []) if p["name"] == "縁台(床几)"]
    if not pr: return []
    pr = pr[0]
    ken = d["const"]["ken"]
    at = dict((prop_label(pr, i), tuple(q)) for i, q in enumerate(pr["uv"]))
    out = []
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            for lab in (sg.get("kokage") or []):
                q = at.get(lab)
                if q is None:
                    out.append((lab, sg["name"], None))
                    continue
                r = single_crown(d, sg)
                if r is None:
                    out.append((lab, sg["name"], None))
                    continue
                dd = math.hypot(q[0] - sg["uv"][0], q[1] - sg["uv"][1])
                out.append((lab, sg["name"], (r - dd) * ken))
    return out


# 縁台の並びの物差し(**検査の物差しであって設計値ではない**ので json に置かない)
ENDAI_GAP_RATIO_MIN = 1.5     # 芯々の 最大/最小。これを下回ると「等間隔の列」
ENDAI_OBB_GAP_MIN = 0.20      # 基どうしの外形の離れ[m]。2026-09-07 報告1(庭方)


def _prov_crown(d, name):
    """その一本立ちの `crown` が**部材未計測の仮値**か(2026-09-07 中1)。"""
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            if sg.get("name") == name: return bool(sg.get("crownProvisional"))
    return False


def endai_check(d, g):
    """縁台が**玉垣の東・通行帯の外**に納まっているか(ユーザー裁定 2026-09-06)。

    ⛔ 止める — 玉垣に食い込む縁台も、通行帯を塞ぐ縁台も建たない。戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    gd = obi_garden(d)
    if not gd: return bad, note
    ken = d["const"]["ken"]
    ue = max(q[0] for q in gd["poly"])
    _vm, yo = zentei_yochi(d, g)
    lim = yo[0][2] if len(yo) > 1 else None            # 通行帯の西縁
    for lab, _u, _v, _yaw, back, east, _pv in endai_rows(d):
        if back is not None and back < -1e-6:
            bad.append("縁台(床几) %s が玉垣の通り(u %.3f)へ %.2f m 食い込む" % (lab, ue, -back))
        if lim is not None and east > lim + 1e-9:
            bad.append("縁台(床几) %s の東の張り出し u %.3f が表参の通行帯の西縁 u %.3f を越える"
                       % (lab, east, lim))
        elif lim is not None:
            # ⭕ **裁き5(庭方 2026-09-07)** — 通行帯は物理の縁ではなく**動線の帯**で、床几は
            #   道端へ出す物。求めるのは「床几の角が通行帯に掛からない」ことだけ。
            #   ⛔ 余裕の下限を置かない(置くと西へ寄せる圧が生まれ、隣の基と食い合う)。
            note.append("縁台(床几) %s の東の張り出し → 表参の通行帯の西縁 %+.3f m【算出 — "
                        "⛔ 下限は置かない。掛からなければよい(裁き5)】" % (lab, (lim - east) * ken))
    # ⭐ **「等間隔にしない」「4基とも向きを違える」は設計の縛りなので機械で押さえる**
    #    (2026-09-06 検図5巡目 低19 — 等間隔・同 yaw にしても無音だった)。
    #    ⛔ 止める — 縛りを割った並びは庭方の意図した姿ではない。
    rows = endai_rows(d)
    yaws = [q[3] for q in rows]
    if len(set(yaws)) != len(yaws):
        bad.append("縁台(床几)の yaw が相異ならない(%s)— ⛔ 4基とも向きを違える(原図の縁台は揃っていない)"
                   % "・".join("%g°" % y for y in yaws))
    ds = [q[6] for q in rows if q[6]]
    if ds:
        ratio = max(ds) / max(1e-9, min(ds))
        if ratio < ENDAI_GAP_RATIO_MIN:
            bad.append("縁台(床几)の芯々が %s m で 最大/最小 %.2f 倍 — 下限 %.2f 倍を割る"
                       "(⛔ 等間隔の列にしない。2基ずつ二つの塊に分ける)"
                       % ("・".join("%.2f" % q for q in ds), ratio, ENDAI_GAP_RATIO_MIN))
        note.append("縁台(床几)の隣どうしの芯々 %s m(⛔ 等間隔にしない — 最大/最小 %.2f 倍・下限 %.2f 倍)"
                    % ("・".join("%.2f" % q for q in ds), ratio, ENDAI_GAP_RATIO_MIN))
    # ⭐ **基どうしの外形の離れ**(2026-09-07 報告1・庭方)— 芯々では食い合いが映らない。
    #    ⛔ 止める — 図の上で部材が貫通する。
    gaps = endai_gaps(d)
    for a, b, gp in gaps:
        if gp < ENDAI_OBB_GAP_MIN - 1e-9:
            bad.append("縁台(床几) %s と %s の外形の離れ %+.3f m — 下限 %.2f m を割る%s"
                       % (a, b, gp, ENDAI_OBB_GAP_MIN, "(食い合っている)" if gp < 0 else ""))
    if gaps:
        note.append("縁台(床几)どうしの外形の離れ(最小) %s %+.3f m(下限 %.2f m)"
                    % ((lambda q: "%s–%s" % (q[0], q[1]))(min(gaps, key=lambda q: q[2])),
                       min(q[2] for q in gaps), ENDAI_OBB_GAP_MIN))
    # ⭐ **木陰**(2026-09-07 報告2・庭方)— 物差しは **縁台の芯が樹冠の投影の中**。
    #    ⛔ 止める — 役『木陰を落とす』が成り立たない配置は庭方の意図した姿ではない。
    for lab, tree, mg in endai_kokage(d):
        if mg is None:
            bad.append("『%s』が木陰を落とす相手『%s』を測れない(縁台の名か樹冠が引けない)" % (tree, lab))
        elif mg < -1e-9:
            bad.append("縁台(床几) %s の芯が『%s』の樹冠の投影の外(%.3f m)— "
                       "役『木陰を落とす』が成り立たない" % (lab, tree, -mg))
        else:
            note.append("縁台(床几) %s の芯 → 『%s』の樹冠の投影の縁 %+.3f m【算出%s】"
                        % (lab, tree, mg, "" if not _prov_crown(d, tree)
                           else " — ⚠ 樹冠が**部材未計測の仮値**なので、この余裕も仮"))
    return bad, note


def endai_table(d):
    kk = {}
    for lab, tree, mg in endai_kokage(d):
        kk[lab] = (tree, mg)
    nb = {}
    for a, b, gp in endai_gaps(d):
        for x, y in ((a, b), (b, a)):
            if x not in nb or gp < nb[x][1]: nb[x] = (y, gp)
    tr = ""
    for lab, u, v, yaw, back, east, prev in endai_rows(d):
        tr += ("<tr><td>%s</td><td class='note'>(%g, %g)</td><td>%g°</td><td>%s</td>"
               "<td class='note'>u %.3f</td><td>%s</td><td>%s</td><td>%s</td></tr>"
               % (lab, u, v, yaw, "%.2f m" % back if back is not None else "—", east,
                  "%.2f m" % prev if prev else "—",
                  ("%s %+.3f m" % nb[lab]) if lab in nb else "—",
                  ("%s %+.3f m" % (kk[lab][0], kk[lab][1]))
                  if (lab in kk and kk[lab][1] is not None) else "—"))
    return ('<div class="tw"><table><thead><tr><th>縁台</th><th class="note">芯 (u,v)</th><th>yaw</th>'
            "<th>玉垣からの背の隙【算出】</th><th class='note'>東の張り出し【算出】</th>"
            "<th>隣との芯々【算出】</th><th>最も近い基との外形の離れ【算出】</th>"
            "<th>木陰の余裕(芯 → 樹冠の投影の縁)【算出】</th>"
            "</tr></thead><tbody>" + tr + "</tbody></table></div>")


def ido_depth(d):
    """掘井戸の深さの幅[m] ── **石敷の天端 − 地下水面の上限/下限**。

    ⚠ 2026-09-06 考証検分4巡目 中4: 指図が 5〜8 m を直に持っていたが、前庭の天端と東の麓道は
    ほぼ同高で「麓道以下」からは数十cmしか出ず、8m を出す一歩(溜池の水面を下限に置く)が
    図にも指図にも無かった。⛔ 数を持たず、`ido.gwBoundsM` からの引き算で出す。
    ⛔ 記号 P(プロジェクト内実測)を地下水位の推定に使わない — 確度は【U 設計値 / B 常態】。
    """
    lo, hi = d["ido"]["gwBoundsM"]
    y = d["terraces"][1]["y"]
    return (y - hi, y - lo)


def ido_table(d, g):
    """井戸屋形 ── 面・寸法・離隔。⛔ 矩形も離隔も json に持たない(`ido` からの従属値)。"""
    R = ido_rects(d)
    if not R: return ""
    io = d["ido"]
    ken = d["const"]["ken"]
    def rc(k):
        u0, v0, u1, v1 = R[k]
        return "u %.3f〜%.3f × v %.3f〜%.3f(%.2f × %.2f m)" % (
            u0, u1, v0, v1, (u1 - u0) * ken, (v1 - v0) * ken)
    rows = [("石敷(%s)" % io["ishiki"], "%g 間角" % io["ishikiKen"], rc("石敷")),
            ("柱", "%d 本・柱芯 %g 間角" % (io["hashiraN"], io["hashiraPitchKen"]),
             "・".join("(%.3f, %.3f)" % q for q in R["柱"])),
            ("井桁", "内法 %g 尺角・見付=成 %.2f m を %d 段(上限 %s 段・立ち上がり %.2f m【算出】)"
             % (io["igetaShaku"], io["igetaMitsukeM"], io["igetaDanN"],
                io.get("igetaDanMaxN", "—"), igeta_rise(d)),
             rc("井桁") + "(**外形**)"),
            ("礎石", "%.2f m 角(上限)・柱 %d 本" % (io["soishiM"], io["hashiraN"]),
             "割栗の突き固めの上に据える。⛔ これより大きくしない — 内隅が練り粘土の巻きへ掛かる量の"
             "上限は**巻きの厚み %.2f m**(超えると石積そのものに載る)。掛かりは現況 %.3f m【算出】"
             % (izutsu_radii(d)[2] - izutsu_radii(d)[1],
                max(0.0, izutsu_radii(d)[2] - soishi_radii(d)[1]))),
            ("屋根", "%s・棟は%s・軒高 %.2f m ／ 棟高 %.2f m" % (io["yane"], io["muneDir"],
                                                                io["nokiH"], io["muneH"]),
             "軒先 " + rc("軒先")),
            ("軒の出 / 破風の出", "%g 間 / %g 間(柱芯から)" % (io["nokiDeKen"], io["hafuDeKen"]),
             "⭕ 軒先の東西が石敷の縁と一致(雨落ちが石敷に落ちる)【算出】"),
            ("浸透枡", "%s %g 間角・石敷は東へ 1/%g" % ("伏せ枡", io["masuKen"], io["ishikiSlope"][1]),
             rc("浸透枡")),
            ("掘り方", "%s 深さ %.1f〜%.1f m【U 設計判断 — 上水の樋線が【? 未調査】である以上、社頭の水を井戸で賄うと決めた帰結。⚠ 新典拠が言うのは内壁の構法までで井戸の型の分布は言わない・考証6巡目 中3】"
             % ((io["horiKind"],) + ido_depth(d)),
             "石敷の天端 %.2f − 地下水面(上限=東麓の池 %.1f【S 五千分一東京図31】／"
             "下限=溜池の水面 %.1f【P】)からの引き算【算出】。"
             "⛔ 上水は引けない(玉川上水の木樋が坂下へ達したかは<b>当たっていない</b>【? 未調査 — K0105 第7図が当該範囲を含むが未読】"
             "／ 青山上水の廃止は補足で、理由にはならない【B 対になる事実】)"
             " ／ 汲み溢れは浸透枡から東縁の下へ"
             % ((d["terraces"][1]["y"],) + tuple(io["gwBoundsM"][::-1])))]
    # ⭐ **盛土層と井筒**(2026-09-06c 裁定1(b)・庭方)。⛔ 地山標高も盛土の厚みも json に書かない
    jy, top = ido_jiyama(d, g)
    if io.get("moriLayers"):
        rows.append(("石敷の下の層", " / ".join("%s %.2f m" % (L["name"], L["tM"]) for L in io["moriLayers"]),
                     "計 %.2f m【算出】。その下は締固めた盛土で、厚みは 天端 − 地山線 の差から出る"
                     % sum(L["tM"] for L in io["moriLayers"])))
    if jy:
        rows.append(("石敷4隅の地山標高【算出 P】",
                     "・".join("%s %.3f" % (nm, hh) for nm, _q, hh, _t in jy),
                     "正本 `sanno_dem.json`(造成前)からの従属値。⛔ 数を指図に書かない"))
        rows.append(("盛土の厚み(天端 %.2f − 地山)【算出】" % top,
                     "・".join("%s %.3f m" % (nm, tt) for nm, _q, _h, tt in jy),
                     "平均 %.3f m ／ 最大 %.3f m。⭕ <b>裁定1(b) — 屋形は動かさない。</b>"
                     "荷は礎石4個で、井筒(<code>ido.izutsu</code>)は<b>地山線より下から積み上げる</b>"
                     % (sum(q[3] for q in jy) / len(jy), max(q[3] for q in jy))))
    iz = io.get("izutsu")
    if iz:
        r1, r2, r3 = izutsu_radii(d)
        rows.append(("井筒(%s)" % iz["kind"],
                     "内径 %g 尺(%.3f m)・石積の壁厚 %.2f m・練り粘土の巻き 厚 %.2f m・据え始め=%s"
                     % (iz["naikeiShaku"], r1 * 2.0, iz["kabeAtsuM"], iz["nendoMakiTM"], iz["base"]),
                     "**三重の円**【算出】 内径 %.3f → 石積の外径 %.3f → 粘土の外径 %.3f m。"
                     "⛔ 盛土の中で積み始めない。⛔ 切石積にしない — 近世の掘井戸は内壁を"
                     "<b>空石積み(石または瓦)</b>で受けるのが一般型【B】で、"
                     "<b>玉石(野面)の輪積みを選ぶのは設計判断</b>【U】。"
                     "練り粘土の巻きの天端は<b>%s</b>で止める。断面ヨ・タが"
                     "〈地山線〉〈盛土層の厚み〉〈井筒が地山へ入る点〉を描く"
                     % (r1 * 2.0, r2 * 2.0, r3 * 2.0, iz.get("nendoMakiTop", "石敷の天端"))))
        rows.append(("井筒まわりの離れ【算出】",
                     "柱芯 → 筒の芯 %.3f m(隅)／礎石の内隅 → 筒の芯 %.3f m"
                     % soishi_radii(d),
                     "⭕ 柱芯は粘土の外径(%.3f m)の外。⚠ 礎石の内隅は %+.3f m 粘土に掛かるが、"
                     "**巻きを割栗の下端で止める**ことで解く(荷は割栗の突き固めが分散する)"
                     % (r3, r3 - soishi_radii(d)[1])))
        rows.append(("井桁の座り【算出】",
                     "井桁の外形 %.3f m 角 ≤ 石積の外径 %.3f m"
                     % (io["igetaShaku"] / 6.0 * ken + 2 * io["igetaMitsukeM"], r2 * 2.0),
                     "⭕ 片側 %.3f m ずつ石積の天端に座り、**練り粘土には載らない**"
                     % (r2 - (io["igetaShaku"] / 6.0 * ken / 2.0 + io["igetaMitsukeM"]))))
    for nm, m in ido_clearances(d, g):
        rows.append(("離隔【算出】", nm, "%.2f m" % m))
    gd = obi_garden(d)
    if gd:
        for nm, a, b, fence, L, rs in tamagaki_edges(d, gd):
            e = [q for q in gd["tamagaki"]["edges"] if q["name"] == nm][0]
            if not e.get("gapFrom"): continue
            gp = tamagaki_gap_span(d, gd, e, a, b)
            rows.append(("玉垣の開口(井戸の口)", "辺『%s』の %.3f〜%.3f 間" % (nm, gp[0], gp[1]),
                         "開口 %.2f m ／ 辺の実長 %.3f 間【算出】" % ((gp[1] - gp[0]) * ken, L)))
    tr = "".join("<tr><td>%s</td><td>%s</td><td class='note'>%s</td></tr>" % q for q in rows)
    return ('<div class="tw"><table><thead><tr><th>井戸屋形</th><th>宣言</th>'
            "<th class='note'>面・従属値</th></tr></thead><tbody>" + tr + "</tbody></table></div>")


def sankaku_table(d):
    """前庭の不等辺三角形 ── **三辺は三点からの従属値**(⛔ json に長さを持たない)。"""
    sk, pts, sides = sankaku_rows(d)
    if not sk: return ""
    tr = "".join("<tr><td>%s</td><td class='note'>%s</td></tr>"
                 % (nm, "(%g, %g)" % tuple(uv) if uv else "**見つからない**")
                 for nm, uv in pts)
    tr += "".join("<tr><td>%s 〜 %s</td><td><b>%s</b></td></tr>"
                  % (a, b, "%.2f 間【算出】" % L if L else "—")
                  for a, b, L in sides)
    return ('<div class="tw"><table><thead><tr><th>前庭の不等辺三角形</th>'
            "<th class='note'>位置・辺の長さ</th></tr></thead><tbody>" + tr
            + "</tbody></table></div>"
            + "<p class='cap'>%s</p>" % inline(sk.get("_", "")))


def shukei_table(d, g):
    """★主景の検算 ── 楼門の眼から見た 木と棟の仰角。⛔ 数を文章に写さない。"""
    rows = ""
    for nm, L, top, ang in shukei_rows(d, g):
        rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (nm, "%.1f m" % L if L else "—",
                    "%.1f m" % top if top else "—(棟高が未記載)",
                    "<b>%.2f°</b>" % ang if ang is not None else "—"))
    R2 = shukei_rows(d, g)
    tree = R2[0] if R2 else None
    ver = ""
    for nm, L, top, ang in R2[1:]:
        if ang is None or tree is None: continue
        dv = tree[3] - ang
        # 木の位置での「棟の稜を見る視線」の高さとの差[m] — ⛔ 数を json に持たない従属値
        eye = [gd["shukei"]["eyeY"] for gd in d["gardens"] if gd.get("shukei")][0]
        over = tree[2] - (eye + math.tan(math.radians(ang)) * tree[1])
        ver += ("<tr><td>%s を越えるか</td><td>%s %+.2f°(稜の視線より %+.2f m)</td>"
                "<td class='note'>%s</td></tr>"
                % (nm, "⭕ 越える" if dv > 0 else "⚠ 越えない", dv, over,
                   "梢が棟の稜より上に出て背景が立つ" if dv > 0
                   else "**梢が棟に隠れる** — 丈を上げるか木を東へ寄せるかは庭方の判断"))
    return ('<div class="tw"><table><thead><tr><th>見る物</th><th>楼門からの距離</th>'
            "<th>頂の標高</th><th>仰角</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
            + ('<div class="tw"><table><thead><tr><th>判定</th><th>主景の木 − 棟</th>'
               "<th class='note'>意味</th></tr></thead><tbody>%s</tbody></table></div>" % ver
               if ver else ""))


def viewpoints_table(d, g):
    """見所 V1〜V3 ── 眼高(従属)と、`shows` に挙げた塊の見込み角。"""
    rows = ""
    for vp, eye, src, shows in viewpoint_rows(d, g):
        sh = "／".join("%s 方位 %+.1f°〜%+.1f°(見込み %.1f°)" % q for q in shows) or "—"
        rows += ("<tr><td><b>%s</b> %s</td><td class='note'>(%g, %g)</td><td>%.2f m"
                 "<span class='note'>(%s)</span></td><td>%s</td><td class='note'>%s</td>"
                 "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                 % (vp["name"], vp["label"], vp["uv"][0], vp["uv"][1], eye, src,
                    vp["dir"], sh, vp.get("cert", "—"), inline(vp.get("_", ""))))
    # ⭐ 2026-09-06b — `_`(何が見えるか)を刷るようにした。前庭の見所は塊を挙げないので、
    #    刷らないと「図に出ない設計値」になる(規則19)。
    return ('<div class="tw"><table><thead><tr><th>見所</th><th class="note">位置 (u,v)</th>'
            "<th>眼高</th><th>向き</th><th class='note'>見込み角(方位は西を 0° とする)</th>"
            "<th class='note'>確度</th><th class='note'>何が見えるか</th>"
            "</tr></thead><tbody>" + rows + "</tbody></table></div>")


# 据え方の呼び名(⛔ json は識別子だけを持ち、図はここで日本語へ開く)
PLACE_JA = {"TerrainTree": "Terrain Tree(LOD+ビルボード)",
            "DetailMesh": "Terrain の Detail Mesh", "GameObject": "GameObject"}


def budget_table(d, g):
    """三角数の見積り ── 本数 × 部材の三角数。⛔ 目録に無い部材は「測れない」と書く。

    ⭐ 2026-09-07 庭方3巡目 中4 — **撒く物と一本立ちを分けて刷る**。据え方は
    `planting.plantRule.placement` からの従属値で、⛔ 図が「Detail か否か」で決め打ちしない
    (旧式は部材に `detail` が立っているかだけを見ており、**千本の松と中木が GameObject のまま**
    だった)。
    """
    rows = ""
    tot = 0
    for key, n, ns, avg, place, place_sg in plant_budget(d, g):
        pend = any(pt.get("pending") for pt in d["planting"]["parts"][key])
        t = None if avg is None else (n + ns) * avg
        if t: tot += t
        rows += ("<tr><td>%s</td><td>%s 本</td><td>%s 本</td><td>%s</td><td>%s</td>"
                 "<td class='note'>%s</td></tr>"
                 % (key, format(n, ","), format(ns, ","),
                    ("—(**新造待ち**)" if pend else "—(**目録に無い**)")
                    if avg is None else "%s 三角/本" % format(int(avg), ","),
                    "—" if t is None else "%s 三角" % format(int(t), ","),
                    "%s ／ 一本立ちは %s" % (PLACE_JA.get(place, place or "**宣言が無い**"),
                                            PLACE_JA.get(place_sg, place_sg or "**宣言が無い**"))))
    rows += ("<tr><td><b>計(測れた分)</b></td><td></td><td></td><td></td><td><b>%s 三角</b></td>"
             "<td class='note'>⚠ 落葉高木3種は目録に無く**この計に入っていない**</td></tr>"
             % format(int(tot), ","))
    return ('<div class="tw"><table><thead><tr><th>層</th><th>撒く本数</th><th>一本立ち</th>'
            "<th>部材の三角数</th><th>小計</th><th class='note'>据え方【従属】</th>"
            "</tr></thead><tbody>" + rows + "</tbody></table></div>")


def ishizai_table(d):
    """庭に使う**石材の系統**【追加 庭方 2026-09-07】。⛔ 産地を典拠なく名指ししない。"""
    iz = d.get("ishizai")
    if not iz: return ""
    rows = "".join("<tr><td>%s</td><td class='note'>%s</td></tr>" % (q, "同じ系統")
                   for q in iz.get("roster", []))
    rows += ("<tr><td><b>系統</b></td><td class='note'><b>%s</b></td></tr>" % inline(iz["togo"]))
    rows += ("<tr><td><b>産地</b></td><td class='note'><b>%s</b></td></tr>"
             % ("**決めていない**【?】" if iz.get("sanchi") is None else inline(iz["sanchi"])))
    return ('<div class="tw"><table><thead><tr><th>石を使う所</th>'
            "<th class='note'>系統</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
            + "<p class='cap'>%s</p>" % inline(iz.get("_", "")))


def joints_table(d):
    """取り合い ── どの面がどの面に接するか(CLAUDE.md 規則5)。"""
    rows = ""
    for j in d.get("joints", []):
        rows += ("<tr><td>%s<br><span class='note'>%s</span></td>"
                 "<td>%s<br><span class='note'>%s</span></td><td>%s</td><td>%.2f m</td>"
                 "<td>%+.2f / %+.2f m</td><td>%s</td><td class='note'>%s</td></tr>"
                 % (j["a"], j["aFace"], j["b"], j["bFace"], j["kind"], j["gap"],
                    j["tol"][0], j["tol"][1], j["moves"], inline(j["_"])))
    return ('<div class="tw"><table><thead><tr><th>甲</th><th>乙</th><th>納め</th><th>目標の隙</th>'
            "<th>許容</th><th>動かす側</th><th class='note'>なぜ</th></tr></thead><tbody>"
            + rows + "</tbody></table></div>")


def plant_note_table(d, g):
    """〔記録〕 ── 止めはしないが庭方の判断を待つ検査の結果。⛔ 黙って消さない。"""
    note = planting_avoid_check(d, g)[1] + rect_overlap_check(d, g)[1]
    if not note:
        return "<p class='cap'>⭕ 〔記録〕は 0 件。</p>"
    return ('<div class="tw"><table><thead><tr><th>#</th><th class="note">〔記録〕'
            "— 実体の欠陥ではないが、庭方の判断が要る</th></tr></thead><tbody>"
            + "".join("<tr><td>%d</td><td class='note'>%s</td></tr>" % (i, html.escape(q))
                      for i, q in enumerate(note, 1)) + "</tbody></table></div>")


def sando_roadside_table(d):
    """参道沿いと前庭の地表 ── 路面・側溝・路肩・柵・林縁・踏石。"""
    rs = d["sando"].get("roadside")
    if not rs: return ""
    w = rs["west"]; tl = rs["takagiEdgeLine"]
    r = []
    def row(a, b):
        r.append("<tr><td>%s</td><td class='note'>%s</td></tr>" % (a, inline(b)))
    row("路面", "幅 %g m ／ 仕上げ %s【?】" % (rs["roadWidth"], rs["surface"]))
    row("側溝", "素掘り 幅 %g 間 ／ 両側" % rs["sokkoKen"])
    row("路肩", "土。" + inline(rs.get("rokataRule", "道敷の幅から従属")))
    for sec in rs["sections"]:
        row(sec["name"], "延長 %.1f m ／ 植栽 %s" % (sec["len"], sec.get("planting", "—")))
    row("柵(社地側)", "境から %g 間 ／ run `%s`(部材は Saku_SW と同じ)"
        % (w["sakuKen"], [q["name"] for q in d["runs"] if q.get("fromEdge")][0]))
    row("林縁", "境から %g〜%g 間 ／ 低木+下草" % (w["rinenKen"][0], w["rinenKen"][1]))
    row("高木の縁の線", "境の辺 %s を内側へ %g 間 ／ (%g, %g)〜(%g, %g) ／ 第一列 芯々 %s 間(不等間隔)・内側 %s 間"
        % (tl["fromEdge"], tl["insetKen"], tl["uv"][0][0], tl["uv"][0][1], tl["uv"][1][0], tl["uv"][1][1],
           _rng(tl["firstRowSpacing"]), _rng(tl["innerSpacing"])))
    for nm, u0, v0, u1, v1 in fumiishi_rects(d):
        row("踏石 " + nm, "(%.2f, %.2f)〜(%.2f, %.2f)" % (u0, v0, u1, v1))
    if rs.get("banRule"): row("線引きの判定基準", rs["banRule"])
    row("置かない物", rs["ban"])
    if rs.get("allow"): row("置ける物", rs["allow"])
    sf = d["terraces"][1].get("surface")
    if sf:
        row("前庭の地表", "%s ／ スプラット `%s` 重み %g〜%g。⛔ 砂利敷にしない"
            % (sf["kind"], sf["splat"], sf["weight"][0], sf["weight"][1]))
    cz = d["planting"]["clearance"]["zentei"]
    row("前庭の退避", "動線=幅の半分+%g 間(**ユーザー裁定 2026-09-06**)／ 石段=半分+%g 間 ／ 門から %g 間 ／ 縁から %g 間"
        % (cz["routeHalfPlus"], cz["kaidanHalfPlus"], cz["gate"], cz["terraceEdge"]))
    ck = d["planting"]["clearance"]["keidai"]
    row("境内の退避", "堂 %g 間 ／ 透塀・回廊 %g 間 ／ 白洲は北縁 v%g から %g 間 ／ 平場の縁 %g 間 ／ 動線=半幅+%g 間 ／ 石段=半幅+%g 間"
        % (ck["do"], ck["sukibeiKairo"], ck["shirasuNorthFromV"], ck["shirasuNorthKen"],
           ck["terraceEdge"], ck["routeHalfPlus"], ck["kaidanHalfPlus"]))
    av = [b["avoid"] for b in d["slopeBands"] if b.get("avoid")]
    for a in av:
        row("帯4の退避", "男坂の芯から %g 間 ／ 女坂の路肩から %g 間 ／ 参道の芯から %g 間 ／ 前庭の縁から %g 間"
            % (a["otokozakaFromAxis"], a["onnazakaFromShoulder"], a["sandoFromAxis"], a["zenteiFromEdge"]))
    return ('<div class="tw"><table><thead><tr><th>項</th><th class="note">設計値</th></tr></thead>'
            "<tbody>" + "".join(r) + "</tbody></table></div>")


def sections_table(d):
    rows = []
    for s in d["sections"]:
        (x0, z0), (x1, z1) = s["line"][0], s["line"][-1]
        rows.append("<tr><td>%s</td><td>%s</td><td>(%.1f, %.1f) → (%.1f, %.1f)</td><td>%s</td>"
                    "<td class='note'>%s</td></tr>"
                    % (s["kana"], s["name"], x0, z0, x1, z1, s["viewText"], inline(s["_"])))
    return ('<div class="tw"><table><thead><tr><th>矢視</th><th>断面</th><th>切断線の世界座標</th>'
            "<th>向き</th><th class='note'>何が読めるか</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def planes_table(d):
    rows = []
    for p in d["planes"]:
        y = plane_y(d, p)                          # ⛔ `planes[].y` を読まない(検図8巡目 中2)
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (p["name"], ("%.1f m" % y) if y is not None else "—(造成しない)",
                       inline(p["note"])))
    return ('<div class="tw"><table><thead><tr><th>面</th><th>高さ</th><th class="note">注記</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def neighbors_table(d):
    rows = []
    for n in d["neighbors"]:
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (n["name"], n["acc"], inline(n["_"])))
    return ('<div class="tw"><table><thead><tr><th>区画</th><th>確度</th><th class="note">考証</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def pending_table(d):
    rows = []
    for k, v in d["_pending"].items():
        rows.append("<tr><td>%s</td><td class='note'>%s</td></tr>" % (k, inline(v)))
    return ('<div class="tw"><table><thead><tr><th>件</th><th class="note">状態</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def reviews_table(d):
    """検分の記録 ── 誰がいつ検め、**閉じていない件が何か**。

    ⚠ 2026-09-06 検図4巡目 低12: `reviews` は要約の一文しか持たず、閉じた件と残る件を追えなかった。
    `items[]` は呼んだ側(普請奉行)が書く器で、⛔ 検分役は read-only なので自分では書けない。
    """
    rows = []
    for key, nm in (("kosho", "考証方"), ("kenzu", "検図方"), ("niwashi", "庭方")):
        r = (d.get("reviews") or {}).get(key)
        if not r: continue
        al = r.get("items", [])
        it = [q for q in al if q.get("status") != "closed"]
        if it:
            body = ("<b>未解決 %d 件</b>(閉 %d 件): " % (len(it), len(al) - len(it))) + "・".join(
                "%s%s %s%s" % (q.get("sev", ""), q.get("n", ""), q.get("title", ""),
                               "(判断待ち)" if q.get("status") == "pending" else "")
                for q in it)
        elif al:
            body = "<b>すべて閉じている</b>(%d 件)" % len(al)
        else:
            body = "件ごとの記録は未記入"
        if r.get("_items"):
            body += "<br><span class='cert'>%s</span>" % inline(r["_items"])
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s<br>"
                    "<span class='cert'>〔その巡の要約 — ⚠ <b>閉じた件も含む</b>。"
                    "件ごとの生死は <code>items[]</code> が正典〕</span> %s</td></tr>"
                    % (nm, r.get("at", "—"),
                       {"pass": "⭕ 合", "fail": "⛔ 否"}.get(r.get("verdict"), r.get("verdict", "—")),
                       body, inline(r.get("note", ""))))
    return ('<div class="tw"><table><thead><tr><th>検分役</th><th>日付</th><th>判定</th>'
            "<th class='note'>件ごとの状態 ／ その巡の要約</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


CHECK_SHOW = 40                 # 検査の一覧に刷る行の上限(⛔ 切ったら切ったと書く)


def checks_table(rows):
    """検査の一覧 ── **0件でも必ず刷る**(規則19。2026-09-06 検図4巡目 中7)。

    ⚠ 2026-09-07 — 上限が 8 行だったので、面ごとの Δ を回した途端に**まとめの行が表から落ちた**
    (端末には出るが図には出ない = 報告経路に繋がっていない)。上限を上げ、切った件数を明記する。
    """
    tr = []
    for nm, bad, note in rows:
        qs = bad + note
        body = [html.escape(q) for q in qs[:CHECK_SHOW]]
        if len(qs) > CHECK_SHOW:
            body.append("…ほか %d 件(生成器の標準出力に全件)" % (len(qs) - CHECK_SHOW))
        tr.append("<tr><td>%s</td><td>%d</td><td>%d</td><td class='note'>%s</td></tr>"
                  % (nm, len(bad), len(note), "<br>".join(body) or "—"))
    return ('<div class="tw"><table><thead><tr><th>検査</th><th>⛔ 止める</th><th>〔記録〕</th>'
            "<th class='note'>中身</th></tr></thead><tbody>" + "".join(tr) + "</tbody></table></div>")


def history():
    try:
        log = subprocess.check_output(
            ["git", "-C", ROOT, "log", "--date=short", "--pretty=%h|%ad|%s", "--",
             "docs/Sashizu/sanno_sashizu.json", "docs/Sashizu/sanno_kosho.md"]).decode()
    except Exception:
        log = ""
    rows = []
    for ln in log.strip().split("\n"):
        if not ln.strip(): continue
        hh, dt, sub = ln.split("|", 2)
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td class='note'>%s</td></tr>"
                    % (hh, dt, html.escape(sub)))
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
    if legend: h.append('<div class="legend">%s</div>' % legend)
    if cap: h.append('<p class="cap">%s</p>' % cap)


KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十",
       "其十一", "其十二", "其十三", "其十四", "其十五", "其十六", "其十七", "其十八",
       "其十九", "其二十", "其二十一", "其二十二", "其二十三", "其二十四", "其二十五",
       "其二十六", "其二十七", "其二十八", "其二十九", "其三十", "其三十一", "其三十二",
       "其三十三", "其三十四", "其三十五", "其三十六", "其三十七", "其三十八", "其三十九", "其四十"]


_PENDRE = re.compile(r"`_pending`\u300c([^\u300d]+)\u300d")


_KEYRE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)`")


def _resolve_key(d, ref):
    """バッククォートの鍵 `a.b.c` が json の中に**実在するか**。頭が最上位の鍵でなければ対象外。"""
    seg = ref.split(".")
    if seg[0] not in d: return None            # 目録の外(ファイル名など)は判定しない
    o = d
    for q in seg:
        if isinstance(o, dict) and q in o:
            o = o[q]; continue
        if isinstance(o, list):                # 列は「どれかの要素が持っていれば実在」
            hit = [e for e in o if isinstance(e, dict) and q in e]
            if hit:
                o = hit[0][q]; continue
        return False
    return True


def pending_pointer_check(d):
    """**宣言したポインタの指し先が実在するか**(⛔)。

    ⚠ 2026-09-06 検図5巡目 高4 — `kattemichi[東の勝手道]` の註が「→ `_pending`」と書くのに
    該当する項が無かった(**指し先の無いポインタ**)。宣言だけ残して中身が無いのは規則19 の欠陥。
    ⭐ 2026-09-07 検図7巡目 低6 — 同じ欠陥が**部材の側**にもあった(`bom` の井桁の行が撤回済みの
    `ido.igetaRiseM` を指していた)。`_pending` の名だけでなく、**`bom` と `planting.parts` の
    本文中のバッククォート鍵**も指し先を確かめる。⛔ 最上位の鍵で始まらない語(`itabei.obj` など
    ファイル名)は目録の外なので判定しない。
    """
    keys = list((d.get("_pending") or {}).keys())
    bad = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items(): walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o): walk(v, path + "[%d]" % i)
        elif isinstance(o, str):
            for nm in _PENDRE.findall(o):
                if not any(k == nm or k.startswith(nm) for k in keys):
                    bad.append("%s が `_pending`\u300c%s\u300d を指すが、その項が無い" % (path, nm))
    walk(d, "")

    def walk_key(o, path):
        if isinstance(o, dict):
            for k, v in o.items(): walk_key(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o): walk_key(v, path + "[%d]" % i)
        elif isinstance(o, str):
            for ref in _KEYRE.findall(o):
                if _resolve_key(d, ref) is False:
                    bad.append("%s が `%s` を指すが、その鍵が指図に無い" % (path, ref))
    walk_key(d.get("bom"), "bom")
    walk_key((d.get("planting") or {}).get("parts"), "planting/parts")
    return bad


def run_checks():
    """図を組む前に回す検査。⛔ **落ちたら組ませない** — 「検査はあるが誰も見ていない」を作らない。

    ⚠ 山王の生成器には長く検査が1本も無かった(2026-08-31 に EDO-0031 で最初の1本を入れた)。
    以後、検査を足すときはここへ並べること。
    ⭐ **2026-09-06 検図4巡目 中7** — 0件のとき何も刷らない検査は「回っていない」のと見分けが付かない。
    **名と件数の一覧を必ず全本刷る**(規則19)。戻り値 (⛔止める, 〔記録〕, 一覧)。
    """
    d = json.load(open(JSON, encoding="utf-8"))
    derive_routes(d)
    g = G(d)
    derive_gates(d, g)         # 門の芯と、その面に取り付く物の通り(⛔ 面の u を二重に持たない)
    derive_runs(d, g)          # 板塀は輪郭からの生成物。⛔ 生成前の run を検査に掛けない
    derive_zentei(d, g)        # 木戸の芯・供待の北辺は従属値(⛔ 丸めた値を持たない)
    tp = terrain_provenance_check()
    so = sando_offset_check(d)
    pa = planting_avoid_check(d, g)
    ro = rect_overlap_check(d, g)
    np_ = noplant_overlap_check(d, g)
    bi = band_invariant_check(d, g)
    ps = path_shape_check(d)
    cw = crown_rule_check(d)
    kb = kido_bay_check(d)
    tb = tamagaki_bay_check(d)
    sn = shisen_check(d)
    py = plane_y_check(d)
    pd_ = plane_dev_check(d, g)
    ib = inubashiri_check(d, g)
    kib = keidai_inubashiri_check(d, g)   # 境内の囲いの犬走り(検図9巡目 中3)
    sd = saku_decl_check(d)               # 柵の宣言(kind と hFrom の整合。検図10巡目 中3/中4)
    sc = section_cut_check(d, g)          # 断面が切る棟(検図9巡目 中2)
    sg_ = saichigai_check(d, g)           # 造成が社地の外へ出ていないか(検図9巡目 低5)
    io = ido_check(d)
    ed = endai_check(d, g)
    sq = sankaku_check(d)         # 不等辺三角形(⛔ 二等辺に近づけない。2026-09-07 低4)
    st_ = sekitoro_check(d, g)    # 石灯籠(⛔ 等間隔に据えない。2026-09-07 低1)
    rp = ["%s が %s を貫く" % q for q in route_pierce(d, g)]
    kp = kenpei_bottom_area(d)
    pp = pending_pointer_check(d)
    # ⛔ **件数のまま運ぶ**(⛔ 文字列へ埋めない)— `rows` が print と return の両方へ届く形
    rows = []
    rows.append(("地形の出自(造成前の正本の切り出し)", tp, []))
    rows.append(("参道の柵と林縁が社地の辺のオフセットか", so, []))
    rows.append(("植栽の多角形 ∩ 退避 = 0", pa[0], pa[1]))
    rows.append(("面の総当たり(棟・門・区・帯・石段・塊・玉垣・低木の面・踏石・点景)", ro[0], ro[1]))
    rows.append(("空地(供待)が平場の中か・何と重なるか", np_[0], np_[1]))
    rows.append(("社叢の帯の不変条件 ①②③", bi, []))
    rows.append(("道の形(道幅より短い脚・引き返し・迷い点)", ps[0], ps[1]))
    rows.append(("樹冠の規約(高木の枝下・中木/低木の樹冠)", cw[0], cw[1]))
    rows.append(("玉垣の木戸が辺に納まるか(端・井戸の口と食い合わないか)", kb, []))
    rows.append(("玉垣の一枚の内法(立子が入る寸法か)", tb[0], tb[1]))
    rows.append(("前庭の視線の抜き(玉垣より高い物を置かない)", sn[0], sn[1]))
    rows.append(("面の天端の出所(`terraces[].y` 一本・面と名簿の宣言)", py, []))
    rows.append(("面に載る門・棟・井戸屋形の Δ(§B-1・裁定済 2026-09-07 — 数を刷るのが役)",
                 pd_[0], pd_[1]))
    rows.append(("前庭の西縁の犬走り(西縁に取り付く物すべて)", ib[0], ib[1]))
    rows.append(("境内の囲いの犬走り(平場の輪郭からの寄せ)", kib[0], kib[1]))
    rows.append(("柵の宣言(`kind`=柵 と丈の出所 `hFrom` の整合)", sd[0], sd[1]))
    rows.append(("断面が切る棟(⛔ 切られない棟は名簿で宣言する)", sc[0], sc[1]))
    rows.append(("造成が社地の外へ出ていないか(名簿つき)", sg_[0], sg_[1]))
    rows.append(("井戸屋形の取り合い(軒先≡石敷・石敷が帯の内・玉垣の開口)", io[0], io[1]))
    rows.append(("縁台(床几)が玉垣の東・通行帯の外か", ed[0], ed[1]))
    rows.append(("前庭の不等辺三角形(最も近い二辺の差)", sq[0], sq[1]))
    rows.append(("石灯籠の並び(⛔ 等間隔に据えない)", st_[0], st_[1]))
    rows.append(("建蔽率の分子(屋根を持たない役の名簿)", kp[1], kp[2]))
    rows.append(("動線が構造物を貫通しないか", rp, []))
    rows.append(("宣言したポインタの指し先が実在するか(`_pending`・`bom`/`parts` の鍵)", pp, []))
    bad = [q for _nm, b, _n in rows for q in b]
    note = [q for _nm, _b, n in rows for q in n]
    return bad, note, rows


def print_checks(rows):
    """⛔ **0件でも必ず刷る** — 件数が出ない検査は「回っていない」のと見分けが付かない(結線の門番)。"""
    w = max(len(nm) for nm, _b, _n in rows)
    print("── 検査 %d 本 ──────────────" % len(rows))
    for nm, b, n in rows:
        print("  %s%s ⛔ %d 件 ／ 〔記録〕 %d 件"
              % (nm, "　" * max(0, (w - len(nm))), len(b), len(n)))
    for nm, b, n in rows:
        for q in b: sys.stderr.write("  ⛔ [%s] %s\n" % (nm, q))
        for q in n: print("  〔記録〕[%s] %s" % (nm, q))


CHECK_ROWS = []


def main():
    bad, note, rows = run_checks()
    CHECK_ROWS[:] = rows
    print_checks(rows)
    if bad:
        sys.stderr.write("⛔ 指図を組めない — 検査が %d 件で落ちた\n" % len(bad))
        sys.exit(1)
    d = json.load(open(JSON, encoding="utf-8"))
    derive_routes(d)
    prose = md2html(tsubo_table(d, open(MD, encoding="utf-8").read()))
    g = G(d)
    derive_gates(d, g)         # 門の芯と、その面に取り付く物の通り(⛔ 面の u を二重に持たない)
    derive_runs(d, g)          # 板塀は平場の輪郭から生成する(独立の座標を持たせない)
    derive_zentei(d, g)        # 木戸の芯・供待の北辺は従属値(⛔ 丸めた値を持たない)
    ken = d["const"]["ken"]
    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css"), encoding="utf-8").read()

    n = [0]
    def nx():
        n[0] += 1
        return KAN[n[0] - 1]

    h = ['<meta charset="utf-8">', "<title>山王権現社 指図</title>",
         "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">永田馬場 星ノ山(読み未決) ／ 江戸郷の総氏神【B】 ／ 社領六百石【S】</p>')
    h.append("<h1>山王権現社(日枝神社) 指図</h1>")
    h.append('<p class="lede">安政三年(一八五六)の姿。社殿は万治二年造営のものが昭和二十年まで存続し、'
             '昭和六年に本殿・幣殿・拝殿・中門・透塀の五件が国宝に指定された。'
             'その指定説明を『麹町区史』が転記していて、<b>桁行×梁間・屋根形式・透塀の実延長までここで確定する</b>。'
             '境内の配置は文政三年の彩色実測図『山王御宮絵図』による。'
             '<b>数値の正典は <code>sanno_sashizu.json</code>、文章の正典は <code>sanno_kosho.md</code>。</b>'
             'この頁はその二つから組んだもので、実装は読んでいない。</p>')

    area = poly_area(d["polygon"])
    kei = poly_area([g.W(u, v) for u, v in d["terraces"][0]["uv"]])
    h.append('<div class="box"><p><b>境内 一万八千五百七十坪</b>【B — 『大江戸今昔めぐり』の記載・原典未特定】。'
             '⚠ 原画は<b>『復元・江戸情報地図』(安政三年基準)</b>であって嘉永年間の切絵図ではない'
             '(2026-08-30 訂正 — 基準年次の改訂に伴う洗い直しで判明)。<b>当図の基準年次と一致する。</b>'
             '当図の社地多角形は <b>%.0f 坪</b>【P】。<b>十坊は社地の外</b>で、社地と十坊・樹下・岡部の間に'
             '山麓を回る道の帯(十坊側のみ・3.7〜5.1m)が通り(岡部・樹下側は道ではない帰属未定の帯・2026-09-01 是正)、観理院とは前庭の東縁で接する'
             '【U ユーザーの敷地割 2026-08-26・EDO-0002】。'
             '<b>多角形の正典は parcels.json の sannosha_prec(ユーザーの敷地割)</b> — 残余法は廃止し、'
             '記載値の原典が特定できるまで多角形をこの数字に合わせて動かさない。山上の平場は %.0f m²(%.0f 坪)【P】。'
             '⚠ 俗説の「約一万坪」は出所不明【?】。</p></div>'
             % (area / TSUBO, kei, kei / TSUBO))

    # 其一 社地
    _shachi = poly_area([(q[0], q[1]) for q in d["polygon"]]) / d["const"]["tsubo"]
    plate(h, nx(), "社地",
          "北が上 ／ 当図の多角形 %s 坪【P 実測】 ／ 記載値 18,570 坪【B】— 含意は未決" % "{:,.0f}".format(_shachi))
    fig(h, shachi_svg(d, KAN[n[0] - 1]),
        legend='<span style="color:var(--shu)">■ 社殿・透塀・参道</span>'
               '<span style="color:var(--roka)">■ 回廊</span>'
               '<span style="color:var(--ishi)">■ 石段</span>'
               '<span>■ 境内(山上)</span><span>■ 前庭</span>'
               '<span style="color:var(--take)">■ 社叢 帯1(濃)／帯2／帯3(淡)／帯4(破線)</span>',
        cap="<b>社叢が境内の実体で、建物は樹林の中の明地に建つ。</b>切絵図は境内全体を"
            "「緑=山林土手馬場原」一筆で塗り、御宮絵図も外周をぐるりと濃緑で塗る【S】。"
            "石段は東へ二本だけで、<b>南西(溜池側)には降りていない</b>【S】。")
    h.append(planes_table(d))
    h.append("<h3>断面の一覧</h3>")
    h.append(sections_table(d))
    h.append('<p class="cap">切断線は其一・其二・其四の平面に<b>一点鎖線と矢視記号</b>で落としてある。'
             '<b>東西の断面は左が西・右が東で北を見る</b>／<b>南北の断面は左が南・右が北で西を見る</b>。</p>')
    h.append("</div>")

    # 現況図(§3a)/ 切盛図(§3b) — 造成の出発点と、その差
    P_ = d["polygon"]
    gx0, gx1 = min(q[0] for q in P_) - 20, max(q[0] for q in P_) + 20
    gz0, gz1 = min(q[1] for q in P_) - 20, max(q[1] for q in P_) + 20
    plate(h, nx(), "現況図(造成前の地形)", "段彩 2 m ／ 等高線 2 m(10 m 太線) ／ 正本 base_dem.json からの切り出し・確度P")
    fig(h, genkyo_svg(d, KAN[n[0] - 1], *_widen(d, gx0, gx1, gz0, gz1)),
        cap="<b>造成のすべての出発点。</b>面の高さは設計者が決めたのではなく、"
            "<b>この地形を走査して自然の平場から採った</b>(境内=山頂平坦面 h≥27.5 / 前庭=男坂下の棚)。"
            "赤の破線は隣地(別当觀理院・神主樹下邸)の区画 — <b>境の地形は隣と一続き</b>なので重ねてある。"
            "一点鎖線は断面の切り位置。"
            "<br>⚠ <b>この「現況」は今日の地面である。</b>正本 `base_dem.json` を"
            "実体は<b>正本 <code>docs/Sashizu/base_dem.json</code> からの切り出し</b>で、2026-08-22 の参照ハイトマップ(国土地理院 DEM5A/10B 由来・8m のズレを補正済)を焼いたものである"
            "(中央値 0.127m 一致)。<b>建物は入っていない</b> — 地形のハイトマップだけを読むので、"
            "社殿もホテルも道路の高架も高さには含まれない。"
            "⛔ <b>ただし「自然地形」ではない。</b>山王山の頂は上知のあと官有地になり、社殿は昭和二十年に焼けて"
            "再建されている。斜面にはホテルと道路が切り込んでいる。"
            "<b>今日の山頂が平らなのは、今日の神社の平場だから</b>で、安政三年の地面そのものではない"
            "(実測: 当図の平場の中は 59 パーセントが 28.0〜28.6 に収まる)。"
            "当図は<b>「今日の地面に安政三年の境内を載せ直す」</b>という立場を取る【確度P】。")
    h.append(planes_table(d))
    h.append("</div>")

    plate(h, nx(), "縁の始末", "法面で摺り付ける ／ 土留めで受ける ／ 縁を肩まで引き戻す")
    fig(h, fuchi_svg(d, KAN[n[0] - 1]),
        cap="<b>平場の縁は宙に浮かせられない。</b>採れる手は三つしかなく、どれを採るかで"
            "切盛図の塗りも断面の描き方も変わる。<b>当図は①を既定にし、①が成り立たない所だけを</b>"
            "<b>裁定に回す</b>(「未解決」の節)。"
            "<b>肩</b>とは、台地の平らな面が斜面に変わる折れ目のこと。"
            "<b>引き戻す</b>とは、平場の輪郭をその折れ目まで縮めて落差そのものを消すこと — "
            "壁も盛土も要らなくなる代わりに<b>境内が狭くなる</b>。"
            "南西の張り出しは実際にこの手で直した(2026-08-23)。")
    h.append("</div>")

    plate(h, nx(), "切盛図", "Δ = 設計地盤 − 現況 ／ 暖色 = 盛土 ／ 寒色 = 切土 ／ 無彩 = ±0.3 m")
    fig(h, kirimori_svg(d, KAN[n[0] - 1], *_widen(d, gx0, gx1, gz0, gz1)),
        cap="<b>どこを盛り、どこを切るか。</b>地の色のままの所は<b>造成しない</b>(社叢・山麓の通り・坂の外)。"
            "<br>⭕ <b>造成の許容はこのまま — 面の高さは取り直さず、棟も動かさない</b>【ユーザー裁定 2026-09-07】。"
            "⛔ <b>CLAUDE.md 規則3(|設計面 − 自然地形| ≤ 0.5m)は屋敷の敷地内の目安で、山上の社地には当てない</b> — "
            "①社殿の位置は絵図が縛る ②山頂の平坦面は<b>万治元年に松平主殿頭忠房の邸地を上収した</b>もので【A】"
            "<b>先行する大名屋敷の造成面である公算が高く</b>、Δ は社の普請の土工事の量を測っていない "
            "③Δ には近代の削平との差が混じる。"
            "⭕ <b>但し書きの実体は「外れている量を図に明記すること」</b> — 目安を超える棟と門は"
            "<b>この図と断面</b>が描き、検査『面に載る門・棟・井戸屋形の Δ』が面ごと・棟ごとに毎回刷る"
            "(⛔ 数を文章に写さない)。⛔ 考証方が挙げた第三の案(南列の2棟を東西に動かす)も採らない。"
            "<b>坂の通路も造成の対象に入れてある</b>(2026-08-23 の検図で落ちているのが分かった) — "
            "⛔ <b>男坂に切通しは掘らない</b>(石段は現地形なりに乗る)。<b>男坂の全長では盛土が主(最大1.4m・平均0.8m)だが、下端寄りの約13%区間は切土(最大1.2m)になる</b>。"
            "段の縁のうち土留めの無い辺は法面(盛土 1:1.5 / 切土 1:1)で現地形へ摺り付ける。"
            "<br>⛔ <b>透塀の南西の隅の盛土は、江戸の普請ではなく近代の掘削跡の埋め戻しである</b>【U】(2026-08-25 裁定)。"
            "そこの地形は <b>14.5×9.1m が ±0.30m にそろった平坦な底</b>に東端で <b>+22%</b> の急な立ち上がりで、"
            "⚠ <b>自然の窪みならV字かU字になる</b> — 人工の切り取りの形をしている。"
            "⚠ <b>図では通常の盛土と同じ色で出る</b>ので、量を江戸期の土工事として読まないこと。"
            "⛔ 復元レイヤを起こさないのは、[五千分一東京図31] の標高点が"
            "<b>高さは0.5m以内で一致するのに水平距離が約2倍ずれる</b>(明治16年 約35m ↔ 正本 72m)ためで、"
            "<b>値は使えても位置を写せない</b>から等高線を基準面にできない。")
    h.append("</div>")

    # 其二 境内 平面
    plate(h, nx(), "境内 平面", "世界軸グリッド ／ 1間 = 1.818 m ／ 原点 = 楼門の芯")
    fig(h, keidai_svg(d, -57, 36, -35, 46, "%s　境内 平面" % KAN[n[0] - 1]),
        legend='<span style="color:var(--shu)">■ 社殿・門・透塀</span>'
               '<span style="color:var(--roka)">■ 回廊</span>'
               '<span style="color:var(--nagaya)">■ 附属堂・御供所</span>'
               '<span style="color:var(--ishi)">■ 御蔵</span>'
               '<span style="color:var(--hei)">┄ 板塀(前庭)</span>'
               '<span style="color:var(--hei)">⋯ 腰高の柵(境内の外周)</span>'
               '<span>○ 石灯籠</span>',
        cap="<b>軸は一直線の東西。</b>東から 坂下の門 → 男坂 → 楼門 → 白洲 → 中門 → 向拝 → 拝殿 → 幣殿 → 本殿。"
            "<b>山上の門は楼門一基</b>で、南北に長い御廻廊二棟の中央に立ち、回廊が境内の東frontを成す【S】。"
            "⭐ <b>境内の外周を回るのは腰高の柵</b>【S 存在・形式 = 名所図会 コマ7 実見 / "
            "U 部材の選択 = ユーザー裁定 2026-09-07】 — <b>作りは前庭の玉垣と同じ</b>(柱+貫二段+立子)で、"
            "丈は玉垣からの従属値。⛔ 板塀にも築地塀にもしない(どちらも典拠がゼロ)。"
            "⛔ <b>前庭の囲いと袖塀は板塀のまま</b>(裁定は『前庭以外』が対象)。"
            "⚠ 実装は築地塀を回したままで、指図と食い違う(「未解決」の節)。"
            "社殿を囲うのは透塀で、その正面に中門【S/A】。<b>附属堂・御厩・御蔵10棟は銘をすべて判読済み</b>【S】(其一=薬師堂)。其五『カリウ堂』・其八『コマ堂』は建物としての同定が未確定【U】で、名所図会の題箋の候補では埋めない。")
    fig(h, keidai_svg(d, 9, 35, -13, 15, "%s 附図　前庭 平面" % KAN[n[0] - 1]),
        cap="<b>附図 前庭 平面。</b>前庭に囲い" + _zentei_kakoi(d) + "・坂下の門・縁台(床几)4・"
            "<b>玉垣で囲う植込みの帯</b>【S 名所図会 コマ7 実見】・"
            "<b>井戸屋形</b>【S 存在=名所図会 コマ7 実見 / U 採否=ユーザー裁定 2026-09-06】・"
            "<b>御成の供待の空地</b>(破線)・"
            "参道の取り合いが集まる面。<b>植込みは前庭の西縁に付く帯</b>で、"
            "<b>仁王門から北へ 袖塀 → 玉垣の植込み → 井戸屋形</b> の順に並ぶ"
            "【S 並びの順=名所図会 コマ7 実見 / U 向き=北・ユーザー裁定 2026-09-06】。"
            "縁台4基は<b>玉垣の前・かつ玉垣の東</b>(広場の側)。"
            "⭐ <b>帯の西面に玉垣は立てない</b>【裁定2(c) 庭方 2026-09-06c】 — "
            "西縁の腰石垣 TW_Zentei_W の天端に<b>犬走り</b>だけ残して植込みが取り付く。"
            "⭐ <b>木戸は『東面 上』の、縁台の二つの塊の間</b>に開く【裁定4(c) 同】 — "
            "⛔ 返しには開けない(一径間しか無い辺を割ると立子の入らない切れ端になる)。"
            "⭐ <b>坂の足元は『視線の抜き』が受け持つ</b>【裁定3 同】 — "
            "参道の芯から <code>planting.clearance.zentei.shisenNukiKen</code> の帯には"
            "玉垣より高い物を置かない(低木は可)。⛔ 石段の退避は端に半円を付けない。"
            "<b>表参は門口の芯を通って男坂の足へ真西から取り付く</b>。"
            "前庭の中は<b>路面幅 2.0 間</b>(門口の倍)で、<b>門をくぐる区間だけ門口の 1 間</b>。"
            "<b>北縁の中央(参道の芯線の下端)の開口が参道の入り</b>で、"
            "そこに参道の階(段数は石段の表)が取り付く。<b>南縁は女坂の口で段違い</b>になり、"
            "口の西を TW_Zentei_SW、口の東(南東の張り出し)を TW_Zentei_SE が受ける。"
            "東縁は腰石垣 TW_Zentei_E(断面リ)。数値は表と断面で読む。")

    h.append("</div>")

    # 其三 社殿 平面
    plate(h, nx(), "社殿 平面", "透塀 東西23.5間 × 南北17間 = 周長 81 間 ／ 東線 = 袖8+中門1+袖8")
    fig(h, keidai_svg(d, -49, -19, -12, 12, "%s　社殿 平面(拡大)" % KAN[n[0] - 1]),
        cap="<b>幣殿型権現造・本殿入母屋造。</b>本殿(方三間)—作り合い(一間・海老虹梁)—幣殿(三間×一間)"
            "—拝殿(七間×三間)—向拝(三間)。<b>幣殿型は向拝一間が通例だが、日枝は石の間型と同格の三間を採る</b>【A】。"
            "囲いは瑞垣のタイプX(正面に瑞垣門=中門を構え、門の両側から瑞垣=透塀が社殿を一周する)【A】。"
            "<b>透塀の矩形は史料の延長 147.28 m にちょうど合わせてある</b> — 周長が設計拘束になっている。")
    h.append(munes_table(d))
    h.append("</div>")

    # 断面
    # ---- 断面(json の sections を順に) ----
    def poly_zrange(x, at=None, te=0):
        """平場が x で覆う z の範囲(at を与えれば z=at での x の範囲)。te=1 は前庭。"""
        P = [g.W(u, v) for u, v in terrace_poly_uv(d["terraces"][te])]
        vals = []
        for i in range(len(P)):
            (x1, z1), (x2, z2) = P[i], P[(i + 1) % len(P)]
            if at is None:
                if (x1 - x) * (x2 - x) <= 0 and abs(x2 - x1) > 1e-9:
                    vals.append(z1 + (z2 - z1) * (x - x1) / (x2 - x1))
            else:
                if (z1 - at) * (z2 - at) <= 0 and abs(z2 - z1) > 1e-9:
                    vals.append(x1 + (x2 - x1) * (at - z1) / (z2 - z1))
        return (min(vals), max(vals)) if len(vals) >= 2 else (None, None)

    zt = d["terraces"][1]
    yk, yz = plane_y(d, d["planes"][0]), zt["y"]
    st = [k for k in d["kaidans"] if k["name"] == "男坂"][0]
    on = [k for k in d["kaidans"] if k["name"].startswith("女坂")][0]
    sx0, sx1 = g.W(st["a"][0], 0)[0], g.W(st["b"][0], 0)[0]
    zx0, zx1 = g.W(zt["u0"], 0)[0], g.W(zt["u1"], 0)[0]
    kr = [r for r in d["runs"] if r["name"] == "Kairo_S"][0]
    kz0, kz1 = g.W(0, kr["a"][1])[1], g.W(0, -kr["a"][1])[1]
    kcop = [w for w in d["terraceWalls"] if w["name"] == "TW_Kairo_E"][0]["coping"]
    L_on = seg_len(on, ken)                       # 女坂の展開長(折れ線)
    L_on1 = 0.0
    uo = (-463.0 - g.x0) / ken                    # 断面ホ の位置
    y_ox = yk - (uo - st["a"][0]) / (st["b"][0] - st["a"][0]) * (yk - yz)

    CAP = {
      "EW847": ("<b>この図が指図の要。</b><b>左が西(本殿)・右が東(山麓)で、北を見る断面</b>。"
                "⛔ <b>切通しは掘らない。</b>踏面0.45の決め打ちで石段を水平20.7mに押し込むと、"
                "地面の倍の急さになり<b>最大5mの切土</b>を要する。"
                "明治16年実測図の実測(<b>石段部の平面長 約35m・比高 28.2→14.2</b>)【A】と現地形の自然勾配(平均30.4%)は一致しており、"
                "<b>男坂を斜面の全長に伸ばすと切土は最大1.3mになり、切通しは消える</b>(CLAUDE.md 規則7=坂は現地形に従う)。"
                "名所図会が描く「石段の両側の笠付きの土留め側壁」【S】はこの高さで足りる。"),
      "NS560": ("<b>左が南・右が北で、西を見る断面</b>。実際に切るのは<b>薬師堂(旧・附属堂其一)</b>1棟のみ"
                "(⚠ 本殿・観音堂・御供所はこの線より 11.9〜20.1m 東で、<b>この線上には無い</b>)。"
                "⚠ この線上の盛土は最大+1.13mにとどまる — 西肩の3m級盛土は本図・切盛図で読む。"),
      "SANDO": ("<b>二ノ鳥居から前庭の中まで、道の領域の中心線に沿って展開した縦断</b>。段は前庭へ上がる石段だけ。⭕ <b>参道の急な区間に段は入れない</b>【ユーザー裁定 2026-09-07】 — 局所の起伏は<b>路面の摺り付け(±0.3m 以内)</b>で吸収する。根拠は三つ: ①御宮絵図は男坂・女坂を梯子状の記号で描き分けるのに<b>参道の帯には梯子が一本も無い</b>【S 記号の不在】、②参道は切絵図で黄=道路に塗られた<b>公道</b>で社が石段を築く根拠が無い、③摺り付けは切盛図の無彩(±0.3m)の枠内なので『造成しない』と両立する。⚠ <b>図に残る『参道の階』は別件</b> — 前庭の天端が作った段差で、同日の造成の裁定で面が一枚のままと決まったのでそのまま残る。"),
      "ONNA2": ("<b>左が前庭(北東)・右が山上(南西→西)で、展開して描いた断面</b>。"
                "<b>女坂は男坂の南で屈曲しながら登る</b>(12区間の連続カーブ・展開長55.15m)。⚠ 御宮絵図(文政3)が直線に描くのは<b>絵図が軸平行に整える作図法</b>による。"
                "『新撰東京名所図会』が「昔時将軍家御成の節、峻坂を避け、此坂のみ御通行遊ばされしにより、"
                "御成坂と申侍る」とする【B】 — <b>裏の脇道ではない</b>。"
                "⛔ <b>二勾配にしない — 一様勾配の緩いカーブ</b>【ユーザーの朱書き 2026-08-23】。"
                "勾配・最小曲率半径・現地形への乖離は<b>図と石段の表で読む</b>(数値を文章に写さない)。"
                "駕籠が通る緩い上りで、御成の道として理に適う。"),
      "NS4827": ("<b>回廊は直線で通るが、平坦面の東縁は北へ退く。</b>差は石垣の基壇(天端29.0)で受ける。"
                "名所図会は<b>両翼とも</b>石垣基壇の上に描く【S 実見 2026-08-23】。"
                "回廊を明治16年実測図の<b>29間(東面総長52.72m)</b>へ伸ばした結果、北端の基壇の露出は"
                "<b>この図と回廊の基壇の展開の節で読む</b>(⛔ 数値を文章に写さない)。この深さは未決(`_pending`)。"),
      "OTOKO_X": ("<b>男坂の横断(通路幅 7.0 m)。</b>石段が現地形の自然勾配に乗るので"
                "<b>切通しではなく</b>、路肩の土留めだけが立つ(⛔ ここにU字を掘らない)。"
                "<b>左が南・右が北で、西を見る断面</b>。<b>地形が南で高いぶん南側壁のほうが高い</b>"
                "(実測は南側壁1.16m・北側壁0.93m)。軸方向の断面イにはその姿が写らない。"),
      "ZENTEI_NS": ("<b>左が南・右が北で、西を見る断面</b>。<b>前庭は南で切土・北で盛土と符号が変わる</b>(地形が北へ下るため)。"
                "北縁の土留めは山を受ける擁壁ではなく<b>盛土の腰石垣</b>。"),
      "WEST":  ("境内の西縁のすぐ外。<b>30mで18m落ちる急崖で、造成しない</b>。"
                "切絵図はここを含めて境内全体を「緑=山林土手馬場原」一筆で塗る【S】。"),
      "NEKIRIMORI": ("<b>左が北西・右が南東で、北東を見る斜め断面</b>。境内北東部の切盛の傾向を1本で示す"
                "。⛔ <b>最大切土・最大盛土を通す線ではない</b> — 最大切土(北東の小丘 h31.6)も"
                "最大盛土(回廊基壇の北端付近)も<b>この線上には無い</b>(極値は切盛図で読む)。"
                "本図は北東部の切盛が入り混じる様子を示す断面。"),
      "NS545": ("<b>左が南・右が北で、西を見る断面</b>。<b>本殿を通す</b>(⚠ <b>柱筋ではない</b> — 柱心のどれとも一致せず柱間の中を通る)。"
                "⛔ <b>南端の盛土は近代の掘削跡の埋め戻し</b>【U】。"
                "境内面28.3と自然地形の差(§B-1)が最も出る向きで、南列の下が盛土・北東が切土になる。"
                "⚠ 2026-08-24 検図(中-2)で追加 — <b>社殿群を横断する南北断面が1本も無かった</b>。"),
      "NS510": ("<b>左が南・右が北で、西を見る断面</b>。<b>中門と中庭</b>を通す"
                "(⚠ 切断線 u=-14.30 は白洲の西縁 u=-14.25 の 0.09m 外=<b>中庭の側</b>)。⚠ この位置は透塀東線の芯からごく近く、断面上は塀の躯体の縁を掠める。"
                "2026-08-24 検図(中-2)で追加。"),
      "EW817": ("<b>左が西・右が東で、北を見る断面</b>。<b>境内の南寄り</b>を切り、女坂の帯を横切る。"
                "実際に切るのは<b>鼓楼・附属堂 其八・御蔵</b>(⚠ 観音堂・御供所はこの線上に無い)。線上は切盛が混在し、単純な盛土の支配断面ではない(数値は本図で読む)。"),
      "EW905": ("<b>左が西・右が東で、北を見る断面</b>。<b>境内の北寄り</b>を切る。"
                "北東の小丘を切った跡と、北縁の法面が読める。"),
      "ZENTEI_EW2": ("<b>左が西・右が東で、北を見る断面</b>。<b>縁台 甲2 と榎(エノキ)の通り</b>を切る"
                "(2026-09-06c 参考2・庭方)。西から <b>腰石垣 TW_Zentei_W → 犬走り → 低木を撒く面 → "
                "エノキの幹と枝下 → 玉垣『東面 上』 → 縁台 甲2 の座面 → 表参の通行帯 → 腰石垣 TW_Zentei_E</b>。"
                "<b>枝下と座面高が同じ一本に出る</b>ので、<b>木陰が縁台に落ちているか</b>を図で検められる"
                "(樹冠の三角は<b>切断線の上での見えがかり</b>で、幹から離れるほど痩せる)。"
                "⛔ <b>切断線は動かさない</b> — 甲1 と 甲2 の間には空きがあり<b>両基を切る東西の線は無い</b>。"
                "この線は 甲2 の中を通り、かつ<b>榎の幹をちょうど通す</b>(甲1 のためにもう一面を増やすと"
                "榎の幹を外れて木陰の検証に使えない)。数値は表と本図で読む。"),
      "ZENTEI_NS2": ("<b>左が南・右が北で、西を見る断面</b>。<b>前庭の帯の通り</b>(玉垣の植込みと"
                "井戸屋形を南北に貫く)。⚠ <b>井戸屋形は箱で描く</b>【低6① 庭方 2026-09-07】 — "
                "屋形の<b>棟の向きが未決</b>【?】(南北を採ってあるが東西も成り立つ)ので、"
                "宣言済みの<b>棟高・切妻の姿を図が断定しない</b>。⛔ 箱の高さは棟高で、軒高ではない。"
                "向きが決まった巡で切妻の姿へ改める(→「未解決」の節)。"
                "〈地山線〉〈盛土層の厚み〉〈井筒が地山へ入る点〉はこの図で読む。"),
      "ZENTEI_EW": ("<b>左が西・右が東で、北を見る断面</b>。<b>井戸屋形の通り</b>を東西に切る。"
                "西から <b>腰石垣 TW_Zentei_W → 犬走り → 井戸屋形(石敷・井筒) → 浸透枡 → "
                "腰石垣 TW_Zentei_E</b>。⚠ <b>井戸屋形は箱で描く</b>(理由は断面ヨと同じ — 棟の向きが未決)。"
                "<b>井筒の三重</b>(内径 → 石積の外径 → 練り粘土の巻きの外径)はこの図で読む。"),
      "EW878": ("<b>左が西・右が東で、北を見る断面</b>。<b>北列の堂の通り</b>を切る — 薬師堂・稲荷社・庚申堂・鐘楼・附属堂 其五 が一本に載る。⭐ <b>2026-09-07 に足した</b>【検図9巡目 中2】 — このうち<b>稲荷社・庚申堂・鐘楼はどの断面にも現れていなかった</b>(平場に載りながら Δ が図で読めない棟だった)。⛔ 最大切土の線ではない(北縁の法面と北東の小丘は断面ル・チで読む)。"),
      "NS538": ("<b>左が南・右が北で、西を見る断面</b>。<b>南列の御供所と観音堂</b>を切る(庚申堂と拝殿も拾う)。⚠ <b>東西では取れない</b> — 二棟は南北の区間が重ならず、東西の一本では片方を必ず外す。⭐ この二棟は<b>造成の裁定の当事者</b>で、盛土の側で §B-1 の目安を超える(数値は検査と本図で読む)。⭕ <b>2026-09-07 のユーザー裁定で面も棟も動かさないと決まった</b> — 規則3(±0.5m)は屋敷の敷地内の目安であって山上の社地には当てない。⛔ 考証方が挙げた第三の案(南列の中で東西に動かす)も採らない。<b>外れている量をこの断面と切盛図に描いて明示する</b>のが但し書きの実体である。"),
      "ZENTEI_E": ("<b>左が南・右が北で、西を見る断面</b>。<b>前庭の東縁の腰石垣 TW_Zentei_E の支配断面</b>。"
                "<b>地形都合の構造物で史料の裏づけは無い</b>【U】。北端 v6.2 から北は参道の入りとして開ける。"
                "露出高は図から読む(数値を文章に写さない)。"),
    }
    # ⚠ 設計線は design_y から直に引くので「分岐の書き忘れで白紙」は起きなくなったが、
    #   **profile の実在**と**平場を切る断面が造成を一つも持たない**ことは見張る(2026-08-24)
    miss = [q["profile"] for q in d["sections"] if q["profile"] not in d["profiles"]]
    if miss: raise SystemExit("profiles に無い断面: %s" % miss)
    blank = []
    for q in d["sections"]:
        pr_ = _profile(d, q["profile"])
        ds_ = design_series(d, g, q["profile"], pr_)
        if not any(abs(y - series_at(pr_, c)) > 0.05 for c, y in ds_):
            wp_ = prof_pos(d, q["profile"])
            if any(in_poly(wp_(c), terrace_poly(te, g)) for c, _ in pr_ for te in d["terraces"]):
                blank.append(q["kana"])
    if blank: raise SystemExit("平場を切るのに造成が一つも無い断面: %s" % blank)
    for sec in d["sections"]:
        key = sec["profile"]
        prof = _profile(d, key)
        # ⚠ 平場は design_y が知っている(切盛図と同じ関数)。ここで手書きするのは
        #   **design_y が知らない構造物だけ** = 基壇・腰石垣の天端と、石段の踏面割付。
        over, stairs, marks = [], [], []
        if key == "EW847":
            stairs = [(sx0, sx1, yk, yz, st)]
        elif key == "ONNA2":
            stairs = [(0.0, L_on, yz, yk, on)]
        elif key == "SANDO":                      # 参道の階を踏面/蹴上で描く(検図 2026-09-06)
            _k = [q for q in d["kaidans"] if q["name"].startswith("参道の階")][0]
            _pp = d["profiles"]["SANDO"]["pts"]; _bw = g.W(*_k["b"]); _s = 0.0; _sb = None
            for _i in range(len(_pp) - 1):
                if abs(_pp[_i][0] - _bw[0]) < 0.06 and abs(_pp[_i][1] - _bw[1]) < 0.06: _sb = _s
                _s += math.hypot(_pp[_i + 1][0] - _pp[_i][0], _pp[_i + 1][1] - _pp[_i][1])
            if _sb is not None:
                stairs = [(_sb, _sb + _k["planeLen"], _k["yBot"], _k["yTop"], _k)]   # 末尾は kaidan の dict(女坂と同じ)
        elif key == "NS4827":
            # 回廊の基壇。天端は境内面ではなく **coping**(2026-08-23 検図 中-1)
            over = [(kz0, kz1, kcop)]
            marks = [(kz0, g.W(0, -1.5)[1], kcop, "回廊 南翼", "廊"),
                     (g.W(0, -1.5)[1], g.W(0, 1.5)[1], yk, "楼門(敷居は境内面)", "門"),
                     (g.W(0, 1.5)[1], kz1, kcop, "回廊 北翼", "廊")]
        elif key == "OTOKO_X":
            ohw = kaidan_wken(d, st) / 2.0           # 男坂の実幅[間]
            over = [(g.W(0, -ohw)[1], g.W(0, ohw)[1], y_ox)]
            for v in (-ohw, ohw):
                z = g.W(0, v)[1]
                marks.append((z - 0.4, z + 0.4, y_ox, "側壁", "塀"))
        elif key == "ZENTEI_E":
            te_ = [w for w in d["terraceWalls"] if w["name"] == "TW_Zentei_E"][0]
            marks = [(g.W(0, te_["a"][1])[1] - 0.4, g.W(0, te_["a"][1])[1] + 0.4, te_["coping"],
                      "腰石垣", "塀"),
                     (g.W(0, te_["b"][1])[1] - 0.4, g.W(0, te_["b"][1])[1] + 0.4, te_["coping"],
                      "参道の入り", "塀")]
        # ⚠ **何を切るかは機械が拾う**(2026-08-24 検図 中-1 — 注記の6件中5件が線上に無かった)
        marks = marks + section_marks(d, g, key, prof)
        design = design_series(d, g, key, prof, override=over, stairs=stairs)
        plate(h, nx(), sec["name"],
              ("%s = %g ／ %s" % (sec["axis"], sec["at"], sec["viewText"]))
              if "at" in sec else "%s ／ %s" % (sec["axis"], sec["viewText"]))
        fig(h, section_svg(d, key, design, marks, "%s　%s" % (KAN[n[0] - 1], sec["name"]),
                           flip=False, viewtxt="矢視 " + sec["kana"] + " ／ " + sec["viewText"]),
            cap=CAP.get(key, ""))
        h.append("</div>")

    # 動線図(§3d)
    plate(h, nx(), "動線図", "参詣 ／ 御成 ／ 賄(勝手) ／ 社務")
    # ⚠ 検査に落としていない不変条件は必ず壊れる(御成が回廊を貫く欠陥は2度出た)。
    #   件数は run_checks の一覧が刷る(2026-09-06 検図4巡目 中7)
    dsvg, drows = dousen_svg(d, KAN[n[0] - 1])
    fig(h, dsvg,
        cap="<b>門を入ってからどう動く想定か。</b>石段を薄い帯で重ねてあるので、"
            "<b>どこで段を越えるか</b>が読める。"
            + ("⚠ <b>賄(勝手)は南の勝手口から入る。</b>御宮絵図の境内南辺に銘の無い朱の小構と、"
               "社叢を抜けて十坊列へ降りる径が描かれる【S】。山上に御厩があり馬は男坂を上がれないので、"
               "段でない登り口を図と独立に要求する。⚠ <b>門と読むのは当図の解釈</b>【U】。"
               if any(g["name"].startswith("勝手口") for g in d["gates"]) else
               "⚠ <b>賄(勝手)の動線が男坂を登るしかない</b> — 裏門・勝手門が無い。"))
    h.append(routes_table(drows))
    h.append("</div>")

    plate(h, nx(), "男坂と女坂の割付",
          "踊り場の無い連続階段 ── 蹴上と踏面は段数と平面長からの従属値(2026-08-24 ユーザーの裁定)")
    fig(h, saka_svg(d, KAN[n[0] - 1]),
        cap="⚠ <b>江戸期の段数の記録は無い</b>【?】ので、<b>現況53段【A 千代田区の説明板】を"
            "安政三年へ外挿した【B】</b>(2026-08-24 ユーザーの裁定)。"
            "⛔ <b>蹴上と踏面は段数と平面長からの従属値</b> — 0.30/0.45 は屋敷の中の石段の既定値で"
            "史料の裏づけが無く、参道の坂には当てない。⚠ <b>現行実装は男坂として成立していない</b> — "
            "石段の下端が法尻より外へ大きく食み出していて、勾配が緩い雁木になっている。")
    h.append(kaidan_table(d))
    h.append("</div>")

    plate(h, nx(), "囲いの展開", "透塀 = 旧国宝五件のうちの一件")
    fig(h, kakoi_svg(d, KAN[n[0] - 1]),
        cap="塀の刻みは一間ごとの柱。<b>透塀の延長 147.28 m(486.01尺)は[国宝建造物目録1941]の指定値で"
            "確度S(麹町区史はこの転記)</b>。これはちょうど八十一間で、設計の矩形はこの周長に合わせてある。"
            "<br>⛔ <b>棒の長さは開口を抜いた実長で、これが発注量である</b>【検図10巡目 中1】 — "
            "石段の頭・勝手口・中門・潜りを抜いてある。<b>史料値と比べる数は「節点間」の側</b>で、"
            "混ぜて読まない。"
            "<br>⭐ <b>柵は姿が違う</b> — 塗り潰しの塀ではなく<b>柱+貫二段の腰高柵</b>で描く"
            "【ユーザー裁定 2026-09-07】。⛔ <b>姿は種別(<code>kind</code>)で決める</b>ので、"
            "丈を宣言しない <code>Saku_SW</code>・<code>Saku_Sando</code> も同じ姿で出る"
            "(検図10巡目 中3 — 旧版は丈の宣言の有無で分岐しており、平面図と物差しが二本あった)。"
            "<b>境内の外周 <code>Ita_Keidai</code> の丈と柱の芯々は前庭の玉垣と同じ物</b>を引いており"
            "(⛔ 独立の数を持たない)、run の表の「丈」の欄も同じ値である。柱の刻みを宣言しない柵は"
            "<b>柱を引かない</b>(⛔ 刻みを発明しない)。")
    h.append(runs_table(d))
    h.append(walls_table(d))
    h.append("<h3>取り合い</h3>")
    h.append(joints_table(d))
    h.append('<p class="cap">⛔ <b>芯やピボットで位置を決めない</b>(CLAUDE.md 規則5)。'
             '<b>どの面がどの面に接するか</b>と、<b>どちらが動くか</b>を書く。')
    h.append("</div>")

    plate(h, nx(), "回廊の基壇の展開", "天端は一定・法尻は地形なり ── 平面では読めない露出高")
    fig(h, kidan_svg(d, KAN[n[0] - 1]),
        cap="<b>名所図会は回廊を両翼とも石垣の基壇の上に描く</b>【S 実見 2026-08-23】。"
            "基壇の天端は境内面より高く一定だが、<b>平坦面の東縁が北で退く</b>ので"
            "北へ行くほど石垣が深くなる。<b>どこまで深くなるかは図で読む</b>(数値は設計値ファイルにのみ置く)。"
            "⚠ 回廊の長さを明治16年実測図の29間に採ったことの帰結で、"
            "<b>基壇を深く積むか・平場を北へ補うか・回廊を短くするかは未決</b>(「未解決」の節)。"
            "石の割付は 0.45m段(コード実装の刻み)に合わせた目安。")
    h.append("</div>")

    plate(h, nx(), "門", "山上は楼門一基。もう一基は男坂の下")
    fig(h, mon_svg(d, KAN[n[0] - 1]))
    rows = []
    for gt in d["gates"]:
        w = g.W(gt["u"], gt["v"])
        rows.append("<tr><td>%s</td><td>(%.1f, %.1f)</td><td>%.1f m</td><td>%d×%d 間</td>"
                    "<td class='note'>%s</td><td>%s</td></tr>"
                    % (gt["name"], w[0], w[1], gt["sill"], gt["plan"]["du"], gt["plan"]["dv"],
                       html.escape(gt["kind"]), gt["acc"]))
    h.append('<div class="tw"><table><thead><tr><th>門</th><th>芯の世界座標 (x,z)</th><th>敷居</th>'
             "<th>外形</th><th class='note'>形式</th><th>確度</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table></div>")
    h.append('<p class="cap">⛔ <b>現行実装の「境内に仁王門と随身門の二基」は誤り。</b>'
             '絵図の銘は「樓門」、名所図会の題箋は「随身門」で、同一の門の別称と読む【S】。'
             'もう一基は男坂の下にあり、名所図会では「仁王門」と読める【S(読みは要確認)】が、'
             '<b>形式も名も確定していない</b>【?】。<b>中門は[国宝建造物目録1941]の指定に'
             '「一間平唐門・屋根銅瓦葺」とあり確度S(麹町区史はこの転記)</b>。</p>')
    h.append("</div>")

    plate(h, nx(), "山麓 ─ 別当・神主・門前町", "この指図の範囲は「山王社一式」")
    fig(h, sanroku_svg(d, KAN[n[0] - 1]),
        cap="二ノ鳥居は境内東麓の辻(北=樹下邸・山王門前町/南=観理院)に立ち、"
            "参道はそこで折れて前庭へ入る — 名所図会は前庭→別當→二ノ鳥居の順に描き、觀理院の向こう側に二ノ鳥居を置く配置と矛盾しない【S 図の実見】(順序だけでは線形を決めない)。"
            "<b>一ノ鳥居は存在が確度S、座標は切絵図からは決まらない</b>【?】ので裁定Bにより東西道の芯線上・五島邸の間口の中央に置く【U】(切絵図は非等尺で px/m 換算が効かない)。")
    h.append(neighbors_table(d))
    h.append("</div>")

    plate(h, nx(), "社叢と植栽", "面は境内の平面図と前庭の附図に描いてある(帯4と立木3区は社地の全図にも) ／ 数値の出口はこの表だけ")
    h.append("<h3>社叢の帯</h3>")
    h.append(shaso_table(d, g))
    h.append('<p class="cap"><b>社叢が境内の実体である。</b>帯1〜3は法肩からの下りの割合で切り、'
             '<b>帯4「東〜北東の裾」だけが多角形</b>を持つ — 東〜北東は幅の広い緩い棚なので、'
             '割合で切ると最下部の帯に落ちて<b>町から見える前面が薄くなる</b>。'
             '⛔ <b>杉・檜は落とした</b>(典拠無し・在庫無し)。⛔ 竹林にしない【A 橋本・堀1998 が竹薮を79例中1例の例外とする】。'
             '⛔ <b>男坂と仁王門は下から見えなければならない</b>【S 名所図会】ので、坂の両側は帯4の退避で空ける。'
             '⭐ <b>面積も本数も定数では持たない。</b>帯1〜3 は '
             '<b>法肩(平場の天端)から法尻(社地の境。東〜北東は帯4の西縁)までの下りの割合</b>を'
             '0.5 間の格子で走査して切り、帯4 は多角形と <code>avoid</code> の宣言から'
             '退避の面を引いて出す。本数は<b>有効面 × 採用密度</b>から従属する。'
             '⛔ <b>受入検査(庭方の実測との照合)は置かず、不変条件で見る</b>(庭方 B-1)— '
             '帯1〜3 の面は<b>当図の定義(東〜北東は帯4の西縁を法尻)</b>が正典。'
             '⛔ <b>面積も本数も合否には使わない</b> — 見るのは上の表の三条だけで、'
             '<b>①面の総和が社地に閉じるか ②下るほど広いか ③帯が破片に砕けていないか</b>。'
             '⭐ ③は<b>最大の連結成分</b>で測る【2026-09-06 検図4巡目 低11】 — '
             '0.5 間の格子は帯の縁に必ず 1〜2 セルの破片を作るので、'
             '<b>最小の成分で測ると組む条件にならない</b>。'
             '⛔ 閾値も定義も動かさない — 合わなければ読み違いとして表に出す。')
    h.append("<h3>境内の立木と前庭の帯</h3>")
    h.append(tachiki_table(d, g))
    h.append("<h3>前庭の帯 ─ 東に残る余地・縁台(床几)・井戸屋形</h3>")
    h.append(zentei_yochi_table(d, g))
    h.append(endai_table(d))
    h.append(ido_table(d, g))
    h.append('<p class="cap">⛔ <b>面積も延長も余地の内訳も設計値ではない</b> — '
             '帯の輪郭・動線の通行帯(前庭は <code>wByTerrace</code> で 2.0 間)・前庭の東縁から'
             '<b>図が算出する従属値</b>。⭐ <b>縁台は玉垣の前</b>【S 名所図会 コマ7 実見】'
             '<b>かつ玉垣の東</b>(広場の側)【U ユーザー裁定 2026-09-06】で、'
             '⛔ 等間隔に並べない(塊の中と塊の間の芯々の比は上の表)。'
             '⭐ <b>井戸屋形は建てる</b>【S 存在=名所図会 コマ7 実見 / U 採否=ユーザー裁定 2026-09-06】'
             ' — 軒先が石敷の縁と一致して'
             '<b>雨落ちが石敷に落ちる</b>。⚠ <b>北端は盛土の側</b>なので、'
             '<b>井戸側の石積の筒(井筒)は盛土層を貫いて地山まで下ろす</b>(石敷は突き固めの上)。'
             '⭕ <b>裁定1(b)</b>【庭方 2026-09-06c】 — <b>屋形は動かさない</b>。'
             '四本柱の覆いで荷は礎石4個、掘井戸は地山から積み上げる筒なので'
             '<b>盛土を貫くのは構法上あたりまえ</b>【U 庭方の判断】。地山より上の区間だけ筒の外周に'
             '<b>練り粘土を巻く</b>(地表水が筒に沿って落ちるのを止める)【U 設計値】。'
             '⭐ <b>断面ヨ・タ</b>が〈地山線〉〈盛土層の厚み〉〈井筒が地山へ入る点〉を描く。'
             '⛔ <b>上水は引けない</b> — 玉川上水は四谷大木戸から石樋・木樋で四谷・麹町・'
             '<b>赤坂の高台</b>へ配水するが【A 玉川上水給水域】、'
             '⛔ <b>その木樋が当社の坂下へ達したかは当たっていない</b>'
             '【? 未調査 — 樋線図 K0105 第7図が当該範囲を含むが坂下の樋線は未読】ので、'
             '<b>社頭の水は井戸で賄うものとして描く</b>【U】。'
             '⚠ <b>青山上水の廃止(享保7年)は補足</b>で理由にはならない【B 対になる事実】 — '
             '廃されたのは青山上水であって玉川上水本系統ではない。'
             '⛔ 深さは指図が数で持たない — <b>石敷の天端 − 地下水面の幅</b>(上限=東麓の池／'
             '下限=溜池の水面)からの従属値で、上の表が算出する。</p>')
    h.append(sankaku_table(d))
    h.append('<p class="cap"><b>建物は樹林の中の明地に建つ</b>【S】。'
             '境内の立木は平場の輪郭を内へ寄せた線を共有辺とする三つの多角形で、'
             '<b>白洲と中庭は開けたまま</b>(砂利敷【S】)。'
             '★<b>主景</b>は楼門から西へ〈白洲 → 石灯籠 → 中門 → 向拝 → 拝殿 → 本殿 → 背後の林〉で、'
             '松の丈では梢が本殿の棟に隠れてしまうため<b>落葉高木を一本、位置を決めて据える</b>。'
             '前庭の落葉高木は<b>縁台(床几)に木陰を落とすため</b>で、'
             '<b>木陰を作るのは榎と椋</b>(松は影を落とさない)。⛔ 刈込・灯籠・蹲踞を置かない。'
             '⭐ <b>退避は輪郭に焼き込んである</b>ので、<b>面積そのものが植えられる面</b>である'
             '(⛔ 堂と動線の上を覆ったまま「使える坪」を別に持たない)。'
             '⭐ <b>松は等方に伸ばさない</b> — 在庫の黒松は丈 ≒ 樹冠の開放樹形で、丈へ等方に合わせると'
             '林冠が閉じきる。丈は Y だけ、樹冠は XZ をわずかに広げる(<code>planting.scaleRule</code>)。'
             '⭐ <b>前庭の植込みは西縁に付く帯</b>である。こうすると帯の樹冠の上に社叢 帯4 の樹林が重なり、'
             '<b>前景=低木・中景=帯の高木・遠景=帯4の林</b>が一つの緑の塊に見え、'
             '<b>広場は開いたまま</b>残る(⛔ 中央に通すと広場が二分される)。'
             '南端を仁王門が、北端を既存の北縁の板塀が閉じるので、帯は両端とも既存部材に取り付いて浮かない。'
             '⭐ <b>仁王門から北へ 袖塀 → 玉垣の植込み → 井戸屋形</b>の順に並ぶ'
             '【S 並びの順=名所図会 コマ7 実見 / U 向き=北・ユーザー裁定 2026-09-06】。'
             '<b>門被りは帯の中のクロマツ</b>が務め、帯4の松は<b>「坂の頭の松」</b>。'
             '⛔ <b>広場に自立した高木を置かない</b>【S 原図は描かない】ので榎も椋も帯の中に立つ。'
             '<b>前庭の東縁の緑は前庭の外(帯4)の樹冠</b>が縁から立ち上がって受ける。'
             '⛔ <b>御成の駕籠寄せは建てない</b> — <b>女坂の口の真横</b>に供待の空地を取るだけにする。')
    h.append("<h3>★主景の検算 ─ 楼門から西を見る</h3>")
    h.append(shukei_table(d, g))
    h.append('<p class="cap">⛔ <b>棟高は本殿・拝殿の2棟しか持っていない</b>'
             '【U 類型 — 本殿9〜11m/拝殿10〜12m の中央】。他の14棟は類型の根拠が無いので'
             '<b>数で埋めていない</b>。棟の頂は棟の平面の中央の真上にあるものとして仰角を出す。')
    h.append("<h3>見所</h3>")
    h.append(viewpoints_table(d, g))
    h.append('<p class="cap">⛔ 仰角・見込み角は設計値ではなく<b>図が算出する従属値</b>。'
             '⚠ V1 の眼高だけは設計面が無いので<b>現地形 + 1.5 m</b>。')
    h.append("<h3>部材と三角数の見積り</h3>")
    h.append(budget_table(d, g))
    h.append('<p class="cap">⚠ <b>常緑低木は在庫0件</b>(在庫方 2026-09-06)で、部材名は仮である — '
             '<b>社叢の下層・林縁・前庭の帯・平場の縁の下層のすべてがこれ待ち</b>。'
             '⚠ <b>落葉高木3種(欅・椋・榎)は <code>docs/asset-index.tsv</code> に載っていない</b>ので、'
             '樹冠も三角数も<b>引けない</b> — 目録の再生成が要る。'
             '⭐ <b>据え方は <code>planting.plantRule.placement</code> からの従属値</b>'
             '【中4 庭方 2026-09-07】。⛔ <b>帯・区に撒く松・落葉・中木を GameObject で置かない</b> — '
             '本数が千の桁で三角数が千万の桁になる(上の表が算出する)。'
             '<b>Terrain Tree(LOD+ビルボード)</b>へ載せる。'
             '⭕ <b>GameObject に残すのは意匠上一本ずつ位置を決めた物だけ</b> = '
             '<code>singles</code> と主景の木で、⛔ 名簿を別に持たない。'
             '⛔ <b>一本立ちを Detail Mesh に落とさない</b> — Detail Mesh は影を落とさないので'
             '<b>門被りも木陰も成り立たなくなる</b>。'
             '⛔ 低木・下草は逆に GameObject にせず <b>Terrain の Detail Mesh</b> に載せる。')
    h.append("<h3>〔記録〕</h3>")
    h.append(plant_note_table(d, g))
    h.append("<h3>参道沿いと前庭の地表</h3>")
    h.append(sando_roadside_table(d))
    h.append('<p class="cap"><b>参道は公道である。</b>植えられるのは<b>社地の側(西)だけ</b>で、'
             '觀理院の側は側溝と路肩にとどまる。⛔ <b>玉垣・並木・石灯籠の列・丁石を置かない</b> — '
             'どれも典拠が無く、置けば社の格が上がってしまう【U 設計判断(保守側)】。'
             '⚠ <b>図が描かないことを否定の根拠に立てない</b>【? 否定的証拠】 — '
             '切絵図は石灯籠や並木を描く図式を持たないので、その沈黙は情報を持たない。'
             '⭐ <b>線引きの判定基準は「囲う対象が土地か、植込みか」</b>(庭方 2026-09-06 A-4)。'
             '<b>土地(社地)を囲う物は沿道に置けない</b>が、'
             '<b>植込みそのものを囲う腰高の柵は社地の内(前庭)なら置ける</b>【S 名所図会】。'
             '⛔ 前庭の外周を柵で回さない。'
             '⛔ <b>前庭を砂利敷にしない</b>(砂利は白洲の格)。'
             '⚠ <b>前庭だけ動線の退避を緩めてある</b>【ユーザー裁定 2026-09-06】 — '
             '境内と同じ退避では表参・御成・男坂が前庭を覆い尽くして植えられる場所が残らない。')
    h.append("</div>")

    plate(h, nx(), "部材", "神社建築は在庫にゼロ")
    h.append(bom_table(d))
    h.append("<h3>石材の系統</h3>")
    h.append(ishizai_table(d))
    h.append('<p class="cap">edogoyomi / Japanese Castle / Japanese Village Kit / Waldemarst の四パックとも'
             '城郭・町屋・農家・植栽しか持たない。流用できるのは<b>石段</b>(汐見坂で実績のある段石)と'
             '<b>石灯籠</b>だけ。<b>社殿本体が最優先</b> — 現況は Village Kit の民家を代用していて神社に見えない。</p>')
    h.append("</div>")

    plate(h, nx(), "考証と決めごと", "文章の正典は sanno_kosho.md")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, nx(), "検分と検査", "誰が検めたか ／ 組む前に回る検査は何本で何件か")
    h.append(reviews_table(d))
    h.append(checks_table(CHECK_ROWS))
    h.append('<p class="cap">⛔ <b>0件でも必ず刷る</b> — 件数が出ない検査は「回っていない」のと'
             '見分けが付かない(規則19)。<b>⛔ の列が1件でも立つと指図は組めない</b>。'
             '〔記録〕は<b>意匠の判断が要る</b>ので止めない(中身は「未解決」の節へ)。</p>')
    h.append("</div>")

    plate(h, nx(), "未解決", "推定で埋めない対象")
    h.append(pending_table(d))
    h.append("</div>")

    plate(h, nx(), "改訂", "経緯は git log docs/Sashizu/")
    h.append(history())
    _ma = kenpei_bottom_area(d)[0]         # ⛔ 役の名で棟をふるい落とさない(検図8巡目 低7)
    h.append('<div class="box"><p><b>面積の総括</b>(§A-4 敷地全体ベース)── '
             '社地 <b>%.0f m²(%.0f 坪)</b> ／ 山上の平場 <b>%.0f m²</b> ／ '
             '建物の底面積 <b>%.0f m²</b> ／ <b>建蔽率 %.2f%%</b>。'
             '⚠ 寺社なので <code>estate-types.md</code> の武家屋敷の建蔽率とは突き合わせない。'
             '⚠ <b>分母は社地単体(十坊・観理院を含まない。2026-08-26 のユーザーの敷地割)</b>。十坊の建物はもとより本図の対象外。記載値18,570坪の原典は考証中(「未解決」の節)。</p></div>'
             % (area, area / TSUBO, kei, _ma, _ma / area * 100))
    h.append('<p class="cap" style="margin-top:44px">@@PLATES@@。'
             '<b>組み直すときは図を落としていないか必ず数える</b>(過去に16図版→1図版へ落ちた前科がある)。</p>')
    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>sanno_sashizu.json</code> ／ '
             '文章 <code>sanno_kosho.md</code>。Y は海抜 m(Unity の Y がそのまま標高)。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    html_out = "\n".join(h)
    tail = svg_tail_check(html_out)                  # (a) </svg> の後に要素を残さない
    # ⛔ **0件でも必ず刷る** — 件数が出ない検査は「回っていない」のと見分けが付かない(結線の門番)
    print("── 検査 1 本(組んだ後)──\n  図版の末尾(</g></svg>) ⛔ %d 件 ／ 〔記録〕 0 件" % len(tail))
    if tail:
        sys.stderr.write("⛔ 図版が壊れている — %d 件:\n" % len(tail))
        for t in tail: sys.stderr.write("   ・%s\n" % t)
        sys.exit(1)
    nsvg = html_out.count("<svg")
    # ⚠ 章の数ではなく **SVG の数**を数える(2026-08-23 検図 — 章を数えても落図を検出できない)
    html_out = html_out.replace("@@PLATES@@", "章 %d ／ 図版(SVG) %d 面" % (n[0], nsvg))
    open(OUT, "w", encoding="utf-8").write(html_out)
    print("wrote %s ／ 章 %d ／ 図版(SVG) %d 面" % (OUT, n[0], nsvg))


if __name__ == "__main__":
    main()
