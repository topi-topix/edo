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

【図版】其一 社地/其二 境内 平面(附図 前庭)/其三 社殿 平面/其四〜其十三 断面イ〜ヌ(10枚)/
        其十四 男坂と女坂の割付/其十五 囲いの展開/其十六 門/其十七 山麓/其十八 社僧十坊/
        以降 棟の表・囲いと石段の表・部材・考証・未解決。
        組んだら「図版 N 面」を数え、nx() の実結果と照合すること(図版が黙って落ちた前科がある)。
"""
import json, sys, math, os, re, subprocess, html

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
            hu, hv = pl["du"] / 2.0, pl["dv"] / 2.0
            if f.get("side") == "E":
                out.append((f["name"], gt["u"] + hu, gt["v"] - hv, gt["u"] + hu + dp, gt["v"] + hv))
            else:
                out.append((f["name"], gt["u"] - hu - dp, gt["v"] - hv, gt["u"] - hu, gt["v"] + hv))
        elif kind == "kaidan":
            k = [q for q in d["kaidans"] if q["name"] == nm]
            if not k: continue
            k = k[0]
            hw = (k.get("wKen") or k["w"] / ken) / 2.0
            u, v = k["a"]
            if f.get("side") == "S":
                out.append((f["name"], u - hw, v - dp, u + hw, v))
            else:
                out.append((f["name"], u - hw, v, u + hw, v + dp))
    return out


def plant_rows(d):
    """高木の本数の内訳。**図と表が同じ関数から数える**(総数を文章に写さない)。"""
    rows = []
    for b in d["slopeBands"]:
        n = b.get("takagi") if b.get("takagi") is not None else b.get("takagiApprox")
        rows.append(("社叢 帯%d %s" % (b["band"], b["name"]), n,
                     "概算" if b.get("takagi") is None else "採用密度から"))
    for gd in d["gardens"]:
        n = sum(cluster_n(c) for c in gd.get("clusters", [])) + len(gd.get("singles", []))
        if n: rows.append((gd["name"], int(round(n)), "塊+一本立ち"))
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
        sb = gd.get("shrubBand")
        if sb and inwin([sb["u"] - sb["widthKen"], sb["v"][0]], [sb["u"], sb["v"][1]]):
            o.append(lp.rect(sb["u"] - sb["widthKen"], sb["v"][0], sb["u"], sb["v"][1],
                             fill="var(--niwa)", op=0.75, stroke="var(--take)", sw=0.7))
            o.append(T(lp.X(sb["u"] - sb["widthKen"] / 2.0),
                       lp.Y((sb["v"][0] + sb["v"][1]) / 2.0), "低木の帯",
                       fs=9, anchor="middle", fill="var(--take)"))
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
        hw = k["w"] / 2.0
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


def derive_runs(d, g):
    """平場の輪郭に従う囲いを**その場で生成する**(2026-08-23 検図 中-5)。

    板塀の座標を独立に持つと、平場を動かしたとき黙って取り残される
    (前庭を多角形にしたとき南の板塀が5m内側に残った)。
    """
    ins = d["const"].get("inubashiri", 0.45) / d["const"]["ken"]
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
                gaps.append([round(q[0], 3), round(q[1], 3), round(k["w"] / 2.0 / d["const"]["ken"] + 0.2, 3)])
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
    by["Ita_Keidai"]["_"] = ("境内の外周の板塀。**平場の輪郭から0.25間(犬走り)内へ寄せて機械生成する** — "
                             "独立の座標を持たない(2026-08-23 検図 中-5)。"
                             "⚠ **回廊の基壇が東front なので東の張り出しには回さない**。"
                             "**開口は石段の頭と勝手口で自動に開く**(2026-08-24 検図 高-1)")


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
            sy = _stair_y(d, g, cx, cz)
            if sy is not None: nm = "石段(男坂・女坂・参道の階)"
            else: nm = "境内(山上)" if y > 20 else "前庭(男坂下)"
            t_ = tally.setdefault(nm, [0, 0.0, 0.0, 0.0, 0.0])
            t_[0] += stp * stp
            if dv > 0: t_[1] += dv * stp * stp; t_[3] = max(t_[3], dv)
            else:      t_[2] += -dv * stp * stp; t_[4] = max(t_[4], -dv)
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in d["polygon"]], stroke="var(--ink)", sw=1.6, close=True))
    o += cut_lines(d, pr.X, pr.Y, pr.L)
    o.append(T(6, 15, kan + "　切盛図 ─ 設計地盤 − 現況(暖色=盛土 ／ 寒色=切土 ／ 無彩=±0.3 m)",
               fs=12.5, fill="var(--dim)"))
    yy = 40.0
    for nm, t_ in tally.items():
        o.append(T(pr.W - 6, yy, "%s: %d m²　盛土 %.0f m³(最大 %.2f)　切土 %.0f m³(最大 %.2f)"
                   % (nm, t_[0], t_[1], t_[3], t_[2], t_[4]), fs=10.5, anchor="end", fill="var(--dim)"))
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
        o.append(PL([(lp.X(u), lp.Y(v)) for u, v in Pg], close=True,
                    fill="var(--niwa)" if is_forest else "var(--shirasu)",
                    stroke="var(--take)" if is_forest else "var(--dim)", sw=0.8,
                    op=0.45 if is_forest else 0.9))
        o.append(T(lp.X(sum(us) / len(us)), lp.Y(sum(vs) / len(vs)) + 4,
                   gd["name"], fs=11, anchor="middle", fill="var(--dim)"))
    o += draw_edge_understory(d, lp)
    # 板塀 ── **開口で切る**(2026-08-24 検図 高-1: 宣言した開口が図に一つも出ていなかった)
    for r in d["runs"]:
        if r["kind"] != "板塀": continue
        if r.get("pts") is None and (r["a"] is None or not inwin(r["a"], r["b"])): continue
        for a, b in run_segs(r):
            o.append(LN(lp.X(a[0]), lp.Y(a[1]), lp.X(b[0]), lp.Y(b[1]),
                        stroke="var(--hei)", sw=1.8, dash="7 3"))
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
        hw = lp.L(k["w"] / ken) / 2
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
    # 石灯籠
    for p in d["props"]:
        if not p.get("uv"): continue
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


def section_marks(d, g, key, prof):
    """断面の切断線が**実際に切る**棟・囲い・門を拾う(2026-08-24 検図 中-1)。

    ⚠ 注記に手で「何を切るか」を書くと腐る(6件中5件が線上に無かった)。
    """
    p = d["profiles"][key]
    ax = p["axis"]
    if ax not in ("EW", "NS"): return []
    at = p["at"]
    yk = d["planes"][0]["y"]
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
    for r in d["runs"]:
        if r["kind"] not in ("透塀", "板塀", "回廊"): continue
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
            out.append((c - 0.4, c + 0.4, yk, r["kind"], "廊" if r["kind"] == "回廊" else "塀"))
    for gt in d["gates"]:
        q = g.W(gt["u"], gt["v"])
        du, dv = gt["plan"]["du"] / 2.0 * d["const"]["ken"], gt["plan"]["dv"] / 2.0 * d["const"]["ken"]
        if ax == "EW":
            if abs(q[1] - at) <= dv: out.append((q[0] - du, q[0] + du, gt["sill"], gt["name"].split("(")[0], "門"))
        else:
            if abs(q[0] - at) <= du: out.append((q[1] - dv, q[1] + dv, gt["sill"], gt["name"].split("(")[0], "門"))
    return out


def section_svg(d, key, design, marks, title, flip=False, viewtxt="", flats=(), stairs=()):
    """design = [(coord, y), ...] 設計地盤 / marks = [(coord0, coord1, y, ラベル, 種別)]"""
    g = G(d)
    prof = _profile(d, key)
    walls = wall_steps(d, g, key, prof, design)
    c0, c1 = prof[0][0], prof[-1][0]
    ys = [h for _, h in prof] + [y for _, y in design]
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
    for c0m, c1m, yb, lab, kind in marks:
        xa, xb = X(c0m), X(c1m)
        if xa > xb: xa, xb = xb, xa
        hgt = {"社殿": 7.5, "門": 9.0, "廊": 5.0, "塀": 2.1, "堂": 4.5}.get(kind, 4.0)
        col = {"社殿": "var(--shu)", "門": "var(--shu)", "廊": "var(--roka)",
               "塀": "var(--hei)", "堂": "var(--nagaya)"}.get(kind, "var(--nagaya)")
        hpx = max(9.0, min(46.0, hgt * vs))
        o.append(R(xa, Y(yb) - hpx, xb - xa, hpx, fill=col, op=0.55, stroke="var(--ink)", sw=0.8))
        o.append(T((xa + xb) / 2, Y(yb) - hpx - 4, lab, fs=fit(lab, xb - xa, 10.5), anchor="middle"))
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
    it = [r["name"] for r in d["runs"] if r["kind"] == "板塀" and r["name"].startswith("Ita_Z")]
    return "%d条(土留め %d ＋ 板塀 %d)" % (len(tw) + len(it), len(tw), len(it))


def kakoi_svg(d, kan="其九"):
    ken = d["const"]["ken"]
    W = 900.0
    rows = [r for r in d["runs"] if r["kind"] in ("透塀", "回廊", "板塀", "柵")]

    def run_ken(r):
        if r.get("ken"):
            return r["ken"]
        pts = r.get("pts") or ([r["a"], r["b"]] if r.get("a") and r.get("b") else None)
        if not pts:
            return 0.0
        return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                   for i in range(len(pts) - 1))

    rows = [r for r in rows if run_ken(r) > 0]
    H = 60.0 + len(rows) * 46.0
    o = _sv(W, H, "囲いの展開")
    o.append(R(0, 0, W, H, fill="var(--paper2)"))
    maxk = max(run_ken(r) for r in rows)
    for i, r in enumerate(rows):
        y = 52.0 + i * 46.0
        rk = run_ken(r)
        L = 470.0 * rk / maxk
        col = {"透塀": "var(--shu)", "回廊": "var(--roka)"}.get(r["kind"], "var(--hei)")
        o.append(R(200, y, L, 20, fill=col, op=0.5, stroke="var(--ink)", sw=0.8))
        # 柱の刻み(1間ごと。折れ線の板塀・柵は展開長で刻む)
        for j in range(1, int(rk) + 1):
            o.append(LN(200 + L * j / rk, y, 200 + L * j / rk, y + 20,
                        stroke="var(--ink)", sw=0.4, op=0.5))
        o.append(T(194, y + 14, r["name"], fs=11, anchor="end"))
        seat = ("天端 %.1f m" % r["seat"]) if isinstance(r.get("seat"), (int, float)) else "地形なり"
        o.append(T(212 + L, y + 14, "%.1f 間 = %.2f m　%s" % (rk, rk * ken, seat), fs=10.5))
        if r.get("gate"):
            o.append(T(200 + L / 2, y - 3, "◇ " + r["gate"], fs=10, anchor="middle", fill="var(--shu)"))
    tot = sum(r["ken"] for r in rows if r["kind"] == "透塀")
    o.append(T(6, 15, kan + "　囲いの展開 ─ 透塀の延長は史料値がそのまま設計拘束", fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "透塀 計 %.0f 間 = %.3f m" % (tot, tot * ken), fs=11.5, anchor="end", fill="var(--shu)"))
    o.append(T(W - 6, H - 10, "史料値 147.28 m(486.01尺)との差 %.3f m" % abs(tot * ken - 147.28),
               fs=10.5, anchor="end", fill="var(--dim)"))
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
            if base is None: return (bench if bench is not None else d["planes"][0]["y"]), None
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
    return (bench if bench is not None else d["planes"][0]["y"]), None


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
    kei = d["planes"][0]["y"]

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
        if r.get("ken"):
            L = "%.1f 間 / %.2f m" % (r["ken"], r["ken"] * ken)
        elif r.get("pts"):
            pl = sum(math.hypot(r["pts"][i + 1][0] - r["pts"][i][0], r["pts"][i + 1][1] - r["pts"][i][1])
                     for i in range(len(r["pts"]) - 1))
            L = "%.1f 間 / %.2f m" % (pl, pl * ken)
        else:
            L = "—"
        seat = ("%.1f m" % r["seat"]) if r.get("seat") else "地形なり"
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (r["name"], r["kind"], L, seat, r.get("base", "—"),
                       html.escape(r.get("gate", "") or "—"), r.get("acc", "—")))
    return ('<div class="tw"><table><thead><tr><th>run</th><th>種別</th><th>長さ</th><th>天端</th>'
            "<th>基壇</th><th class='note'>開口</th><th class='note'>確度</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def kaidan_table(d):
    ken = d["const"]["ken"]
    rows = []
    for k in d["kaidans"]:
        L = seg_len(k, ken)
        rise = k["yTop"] - k["yBot"]
        rows.append("<tr><td>%s</td><td>%d</td><td>%.3f</td><td>%.3f</td><td>%.2f m</td><td>%.2f m</td>"
                    "<td>%.1f%%</td><td>%s</td></tr>"
                    % (k["name"], k["steps"], rise / k["steps"], L / k["steps"], rise, L,
                       rise / L * 100, k["acc"]))
    return ('<div class="tw"><table><thead><tr><th>石段</th><th>段数</th><th>蹴上</th><th>段の間隔</th>'
            "<th>比高</th><th>平面長</th><th>勾配</th><th>確度</th></tr></thead><tbody>"
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


def shaso_table(d):
    """社叢の帯 ── 密度・芯々・樹高・層。⛔ 数値を文章に写さない(この表が唯一の出口)。"""
    rows = []
    for b in d["slopeBands"]:
        if b.get("uv"):
            ar = poly_area([tuple(q) for q in b["uv"]]) * d["const"]["ken"] ** 2 / TSUBO
            area = "%s 坪【算出】" % format(int(round(ar)), ",")
            if b.get("tsuboAvoid"):
                area += "(退避 %s → 有効 %s)" % (format(int(b["tsuboAvoid"]), ","),
                                                 format(int(b["tsuboUsable"]), ","))
            rge = "多角形(uv %d点)" % len(b["uv"])
            if b.get("yRange"): rge += " ／ 標高 %g〜%g m" % tuple(b["yRange"])
        else:
            area = "約 %s 坪【概算】" % format(int(round(b.get("tsuboApprox") or 0)), ",")
            rge = "法肩からの下り %.0f〜%.0f%%" % (b["from"] * 100, b["to"] * 100)
        n = b.get("takagi") if b.get("takagi") is not None else b.get("takagiApprox")
        dens = _rng(b.get("takagiPer100"))
        if b.get("takagiAdopted"): dens += "(採用 %g)" % b["takagiAdopted"]
        rows.append("<tr><td>帯%d %s</td><td class='note'>%s</td><td>%s</td><td>%s 本</td>"
                    "<td>%s</td><td>%s m</td><td>%s m</td><td>%s / %s m</td>"
                    "<td>%s / %s m</td><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (b["band"], b["name"], rge, area, n, dens,
                       _rng(b.get("spacing")), _rng(b.get("matsuH")),
                       (("%.1f割" % (b["rakuyoRatio"] * 10)) +
                        (" (%d 本)" % b["rakuyo"] if b.get("rakuyo") else "")) if b.get("rakuyoRatio") else "—",
                       _rng(b.get("rakuyoH")),
                       _rng(b.get("chubokuPer100")), _rng(b.get("chubokuH")),
                       _rng(b.get("teibokuPer100")) + (" / %s m" % _rng(b.get("teibokuH"))
                                                       if b.get("teibokuH") else ""),
                       b.get("shitakusa", "—"), b.get("acc", "—")))
    rn = [b.get("rinen") for b in d["slopeBands"] if b.get("rinen")]
    for r in rn:
        rows.append("<tr><td>└ 林縁の帯</td><td class='note'>社地の境から %g〜%g 間</td><td>—</td>"
                    "<td>0 本(高木を置かない)</td><td>%g</td><td>—</td><td>—</td><td>—</td>"
                    "<td>—</td><td>%s</td><td>%s</td><td class='note'>帯4の規定</td></tr>"
                    % (r["fromKen"], r["toKen"], r["takagiPer100"],
                       _rng(r.get("teibokuPer100")), r.get("shitakusa", "—")))
    return ('<div class="tw"><table><thead><tr><th>帯</th><th class="note">範囲</th><th>面積</th>'
            "<th>高木</th><th>密度 本/100m²</th><th>芯々</th><th>松の丈</th><th>落葉 割合／丈</th>"
            "<th>中木 密度／丈</th><th>低木 密度</th><th>下草</th><th class='note'>確度</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _gname(gd):
    return ("社叢 帯%d %s" % (gd["band"], gd["name"])) if gd.get("band") else gd["name"]


def tachiki_table(d):
    """境内の立木3区と前庭の木 ── 面・合法域・塊・一本立ち。"""
    ken2 = d["const"]["ken"] ** 2
    rows = []
    src = list(d["gardens"]) + [b for b in d["slopeBands"] if b.get("clusters")]
    for gd in src:
        P = garden_poly(gd)
        if not (gd.get("clusters") or gd.get("singles")): continue
        ar = ("%s 坪" % format(int(round(poly_area(P) * ken2 / TSUBO)), ",")) if P else "前庭の中"
        us = ("%s 坪" % format(int(round(gd["tsuboUsable"])), ",")) if gd.get("tsuboUsable") else "—"
        first = True
        for c in gd.get("clusters", []):
            bx = " / ".join("(%g,%g)〜(%g,%g)" % q for q in cluster_boxes(c))
            if not bx:
                bx = "高木の縁の線に沿う 幅%g間の帯 ／ v %g〜%g" % (
                    c.get("widthKen", 0), c["vRange"][0], c["vRange"][1])
            if c.get("fromAxisKen"): bx += " ／ 坂の芯から %s 間" % _rng(c["fromAxisKen"])
            if c.get("split"): bx += " ／ " + c["split"]
            rl = c.get("role", "")
            if c.get("overhang"): rl += "(道への張り出し %s m)" % _rng(c["overhang"])
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td>"
                        "<td>%s</td><td>%s 間</td><td>%s</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "", us if first else "",
                           c["name"], bx, cluster_label(c).split(" ")[-1],
                           _rng(c.get("spacing")), c.get("mix", "—"), rl))
            first = False
        for sg in gd.get("singles", []):
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='note'>(%g, %g)</td>"
                        "<td>1本</td><td>—</td><td>%s%s</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "", us if first else "",
                           sg["name"], sg["uv"][0], sg["uv"][1], sg.get("kind", "—"),
                           (" 丈%.1fm・樹冠%.2fm" % (sg["h"], sg["crown"]))
                           if sg.get("crown") else ("" if not sg.get("h") else " 丈%.1fm" % sg["h"]),
                           sg.get("role", "")))
            first = False
        sb = gd.get("shrubBand")
        if sb:
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>東縁の低木の帯</td>"
                        "<td class='note'>u %g(内側へ幅 %g 間)・v %g〜%g</td><td>—</td>"
                        "<td>%g 間</td><td>%s</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "", us if first else "",
                           sb["u"], sb["widthKen"], sb["v"][0], sb["v"][1], sb["spacing"],
                           sb["veg"], "板塀が無い区間(崖の肩)を低木で塞ぐ"))
            first = False
        if gd.get("clusterGapMin"):
            rows.append("<tr><td></td><td></td><td></td><td>塊間の下限</td>"
                        "<td class='note'>—</td><td>—</td><td>%g 間</td><td>—</td>"
                        "<td class='note'>塊どうしを近づけすぎない目安</td></tr>" % gd["clusterGapMin"])
        sk = gd.get("shukei")
        if sk:
            rows.append("<tr><td></td><td></td><td></td><td>★主景の木(%s)</td>"
                        "<td class='note'>(%g, %g)・眼高 %.1f m の楼門から</td><td>1本</td><td>—</td>"
                        "<td>%s 丈 %.0f m 以上</td><td class='note'>%s</td></tr>"
                        % (sk["tree"]["cluster"], sk["tree"]["uv"][0], sk["tree"]["uv"][1],
                           sk["eyeY"], sk["tree"]["kind"], sk["tree"]["hMin"],
                           "松の丈では梢が本殿の棟に隠れる ─ 位置を固定する"))
    pl = d.get("planting", {}).get("edgeUnderstory")
    if pl:
        rows.append("<tr><td>平場の縁の下層</td><td>—</td><td>—</td><td>低木の帯</td>"
                    "<td class='note'>縁のオフセット線から内側 %g 間</td><td>—</td><td>%g 間</td>"
                    "<td>%s</td><td class='note'>3区が共有する辺なので一度だけ定める</td></tr>"
                    % (pl["insetKen"], pl["spacing"], pl["veg"]))
    tot = sum(n for _, n, _ in plant_rows(d) if n)
    br = "".join("<tr><td class='note'>%s</td><td class='note'>%s</td><td class='note'>%s 本</td></tr>"
                 % (a, c, b) for a, b, c in plant_rows(d))
    tally = ('<div class="tw"><table><thead><tr><th>高木の内訳</th><th>出どころ</th><th>本数</th>'
             "</tr></thead><tbody>%s<tr><td><b>計</b></td><td></td><td><b>%d 本</b></td></tr>"
             "</tbody></table></div>" % (br, tot))
    return ('<div class="tw"><table><thead><tr><th>区</th><th>面積</th><th>退避後</th><th>塊</th>'
            "<th class='note'>箱 (u,v)</th><th>本数</th><th>塊内芯々</th><th>樹種・寸法</th>"
            "<th class='note'>役</th></tr></thead><tbody>" + "".join(rows)
            + "</tbody></table></div>" + tally)


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
    row("置かない物", rs["ban"])
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
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td></tr>"
                    % (p["name"], ("%.1f m" % p["y"]) if p["y"] else "—(造成しない)",
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
       "其二十六", "其二十七", "其二十八", "其二十九", "其三十", "其三十一", "其三十二"]


def run_checks():
    """図を組む前に回す検査。⛔ **落ちたら組ませない** — 「検査はあるが誰も見ていない」を作らない。

    ⚠ 山王の生成器には長く検査が1本も無かった(2026-08-31 に EDO-0031 で最初の1本を入れた)。
    以後、検査を足すときはここへ並べること。
    """
    bad = []
    bad += terrain_provenance_check()
    bad += sando_offset_check(json.load(open(JSON, encoding="utf-8")))
    return bad


def main():
    bad = run_checks()
    if bad:
        sys.stderr.write("⛔ 指図を組めない — 検査が %d 件で落ちた:\n" % len(bad))
        for b in bad:
            sys.stderr.write("   ・%s\n" % b)
        sys.exit(1)
    d = json.load(open(JSON, encoding="utf-8"))
    prose = md2html(tsubo_table(d, open(MD, encoding="utf-8").read()))
    g = G(d)
    derive_runs(d, g)          # 板塀は平場の輪郭から生成する(独立の座標を持たせない)
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
               '<span>■ 境内(山上)</span><span>■ 前庭</span><span>■ 社叢(造成しない)</span>',
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
            "<b>坂の通路も造成の対象に入れてある</b>(2026-08-23 の検図で落ちているのが分かった) — "
            "旧図が掘っていた5mの切通しは廃した。<b>男坂の全長では盛土が主(最大1.4m・平均0.8m)だが、下端寄りの約13%区間は切土(最大1.2m)になる</b>(2026-09-01 是正 — 旧文『全長に1.0〜1.5mの盛土』は実測と食い違っていた)。"
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
               '<span style="color:var(--hei)">┄ 板塀</span><span>○ 石灯籠</span>',
        cap="<b>軸は一直線の東西。</b>東から 坂下の門 → 男坂 → 楼門 → 白洲 → 中門 → 向拝 → 拝殿 → 幣殿 → 本殿。"
            "<b>山上の門は楼門一基</b>で、南北に長い御廻廊二棟の中央に立ち、回廊が境内の東frontを成す【S】。"
            "社殿を囲うのは透塀で、その正面に中門【S/A】。<b>附属堂・御厩・御蔵10棟は銘をすべて判読済み</b>【S】(其一=薬師堂)。其五『カリウ堂』・其八『コマ堂』は建物としての同定が未確定【U】で、名所図会の題箋の候補では埋めない。")
    fig(h, keidai_svg(d, 9, 35, -13, 15, "%s 附図　前庭 平面" % KAN[n[0] - 1]),
        cap="<b>附図 前庭 平面。</b>前庭に囲い" + _zentei_kakoi(d) + "・坂下の門・茶店の縁台4・"
            "参道の取り合いが集まる面。<b>北縁の中央(参道の芯線の下端)の開口が参道の入り</b>で、"
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
    yk, yz = d["planes"][0]["y"], zt["y"]
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
                "⚠ <b>2026-08-23 全面改訂 — 切通しを廃した。</b>旧図は踏面0.45の決め打ちで石段を水平20.7mに"
                "押し込んでいたため、地面の倍の急さになり<b>最大5mの切土</b>を要していた。"
                "明治16年実測図の実測(<b>石段部の平面長 約35m・比高 28.2→14.2</b>)【A】と現地形の自然勾配(平均30.4%)は一致しており、"
                "<b>男坂を斜面の全長に伸ばすと切土は最大1.3mになり、切通しは消える</b>(CLAUDE.md 規則7=坂は現地形に従う)。"
                "名所図会が描く「石段の両側の笠付きの土留め側壁」【S】はこの高さで足りる。"),
      "NS560": ("<b>左が南・右が北で、西を見る断面</b>。実際に切るのは<b>薬師堂(旧・附属堂其一)</b>1棟のみ"
                "(2026-09-01 是正 — 旧文は観音堂・御供所・本殿を挙げていたが、切断線 x=-560 は"
                "それらより11.9〜20.1m西(本殿11.92m・観音堂17.82m・御供所20.10m)で、この線上には無かった)。"
                "⚠ この線上の盛土は最大+1.13mにとどまる(2026-09-01 是正 — 旧文『3m級の盛土』は線から"
                "離れた地点(平場西端付近)の値が混入していた)。西肩の3m級盛土は本図・切盛図で読む。"),
      "SANDO": ("<b>二ノ鳥居から前庭の中まで、道の領域の中心線に沿って展開した縦断</b>。段は前庭へ上がる石段だけ。途中の局所の起伏は段を設けず路面の摺り付け(±0.3m)で吸収する — 緩い坂を土のまま置くのが近世の常態で、公道に社が石段を築く典拠は無い(考証方の推奨・ユーザー確認待ち)。"),
      "ONNA2": ("<b>左が前庭(北東)・右が山上(南西→西)で、展開して描いた断面</b>。"
                "<b>女坂は男坂の南で屈曲しながら登る</b>(12区間の連続カーブ・展開長55.15m。2026-09-01 是正 — "
                "旧文『南西へ34m上り、折れて西へ28m』は明治16年実測図の値で、当図の設計線(2026-08-23に"
                "一様勾配の緩いカーブへ改めた)とは別)。⚠ 御宮絵図(文政3)が直線に描くのは<b>絵図が軸平行に整える作図法</b>による。"
                "『新撰東京名所図会』が「昔時将軍家御成の節、峻坂を避け、此坂のみ御通行遊ばされしにより、"
                "御成坂と申侍る」とする【B】 — <b>裏の脇道ではない</b>。"
                "⚠ <b>2026-08-23 に二勾配をやめ、ユーザーの朱書きに従って一様勾配の緩いカーブにした。</b>"
                "勾配・最小曲率半径・現地形への乖離は<b>図と石段の表で読む</b>(数値を文章に写さない)。"
                "駕籠が通る緩い上りで、御成の道として理に適う。"),
      "NS4827": ("<b>回廊は直線で通るが、平坦面の東縁は北へ退く。</b>差は石垣の基壇(天端29.0)で受ける。"
                "名所図会は<b>両翼とも</b>石垣基壇の上に描く【S 実見 2026-08-23】。"
                "回廊を明治16年実測図の<b>29間(東面総長52.72m)</b>へ伸ばした結果、北端の基壇の露出は"
                "<b>この図と回廊の基壇の展開の節で読む</b>(2026-09-01 是正 — 旧文の『54m』『約7m』は"
                "実測(52.72m・最大5.08m)と食い違っていたため削除)。この深さは未決(`_pending`)。"),
      "OTOKO_X": ("<b>男坂の横断(通路幅 7.0 m)。</b>⚠ 2026-08-23 改訂 — 石段が現地形の自然勾配に乗ったので"
                "<b>切通しではなくなり</b>、路肩の土留めだけになった。旧図はここに3m級のU字を掘っていた。"
                "<b>左が南・右が北で、西を見る断面</b>。<b>地形が南で高いぶん南側壁のほうが高い</b>"
                "(2026-09-01 是正 — 旧文は同じキャプションの中で『北側壁が高い』と自己矛盾していた。"
                "実測は南側壁1.16m・北側壁0.93m)。軸方向の断面イにはその姿が写らない。"),
      "ZENTEI_NS": ("<b>左が南・右が北で、西を見る断面</b>。<b>前庭は南で切土・北で盛土と符号が変わる</b>(地形が北へ下るため)。"
                "北縁の土留めは山を受ける擁壁ではなく<b>盛土の腰石垣</b>。"),
      "WEST":  ("境内の西縁のすぐ外。<b>30mで18m落ちる急崖で、造成しない</b>。"
                "切絵図はここを含めて境内全体を「緑=山林土手馬場原」一筆で塗る【S】。"),
      "NEKIRIMORI": ("<b>左が北西・右が南東で、北東を見る斜め断面</b>。境内北東部の切盛の傾向を1本で示す"
                "(2026-09-01 是正 — 旧文『最大切土・最大盛土を1本で通す』は誤り。真の最大切土(北東の小丘"
                "h31.6・切盛図参照)・真の最大盛土(回廊基壇の北端付近・切盛図参照)は<b>どちらもこの線上には無い</b>。"
                "極値は切盛図で読み、本図は北東部の切盛が入り混じる様子を示す断面として位置づける)。"
                "2026-08-22 検図の指摘で追加。"),
      "NS545": ("<b>左が南・右が北で、西を見る断面</b>。<b>本殿を通す</b>(2026-09-01 是正: 柱心のどれとも一致せず柱間の中を通るため『柱筋』の呼称を外した)。"
                "⛔ <b>南端の盛土は近代の掘削跡の埋め戻し</b>【U】。"
                "境内面28.3と自然地形の差(§B-1)が最も出る向きで、南列の下が盛土・北東が切土になる。"
                "⚠ 2026-08-24 検図(中-2)で追加 — <b>社殿群を横断する南北断面が1本も無かった</b>。"),
      "NS510": ("<b>左が南・右が北で、西を見る断面</b>。<b>中門と中庭</b>を通す"
                "(2026-09-01 是正 — 旧文の『白洲』は誤り。切断線 u=-14.30 は白洲の西縁 u=-14.25 の"
                "0.09m外=中庭側)。⚠ この位置は透塀東線の芯からごく近く、断面上は塀の躯体の縁を掠める。"
                "2026-08-24 検図(中-2)で追加。"),
      "EW817": ("<b>左が西・右が東で、北を見る断面</b>。<b>境内の南寄り</b>を切り、女坂の帯を横切る。"
                "実際に切るのは<b>鼓楼・附属堂 其八・御蔵</b>(2026-09-01 是正 — 旧文『観音堂・鼓楼・御供所』は"
                "この線上に無かった)。線上は切盛が混在し、単純な盛土の支配断面ではない(数値は本図で読む)。"),
      "EW905": ("<b>左が西・右が東で、北を見る断面</b>。<b>境内の北寄り</b>を切る。"
                "北東の小丘を切った跡と、北縁の法面が読める。"),
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
            ohw = st["w"] / ken / 2.0                # 男坂の実幅(±1.925間)
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
    pierce = route_pierce(d, g)
    if pierce:
        # ⚠ 検査に落としていない不変条件は必ず壊れる(御成が回廊を貫く欠陥は2度出た)
        raise SystemExit("動線が構造物を貫通: %s" % pierce)
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
        cap="刻みは一間ごとの柱。<b>透塀の延長 147.28 m(486.01尺)は[国宝建造物目録1941]の指定値で確度S(麹町区史はこの転記)</b>。"
            "これはちょうど八十一間で、設計の矩形はこの周長に合わせてある。")
    h.append(runs_table(d))
    h.append(walls_table(d))
    h.append("</div>")

    plate(h, nx(), "回廊の基壇の展開", "天端は一定・法尻は地形なり ── 平面では読めない露出高")
    fig(h, kidan_svg(d, KAN[n[0] - 1]),
        cap="<b>名所図会は回廊を両翼とも石垣の基壇の上に描く</b>【S 実見 2026-08-23】。"
            "基壇の天端は境内面より高く一定だが、<b>平坦面の東縁が北で退く</b>ので"
            "北へ行くほど石垣が深くなる。<b>どこまで深くなるかは図で読む</b>(数値は設計値ファイルにのみ置く)。"
            "⚠ 回廊の長さを明治16年実測図の29間に採ったことの帰結で、"
            "<b>基壇を深く積むか・平場を北へ補うか・回廊を短くするかは未決</b>(「未解決」の節)。"
            "石の割付は 0.45m段(コード実装の刻み)に合わせた目安(2026-09-01 是正 — 旧文『重ね0.20m』はコードで使われていない値だった)。")
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
    h.append(shaso_table(d))
    h.append('<p class="cap"><b>社叢が境内の実体である。</b>帯1〜3は法肩からの下りの割合で切り、'
             '<b>帯4「東〜北東の裾」だけが多角形</b>を持つ — 東〜北東は幅の広い緩い棚なので、'
             '割合で切ると最下部の帯に落ちて<b>町から見える前面が薄くなる</b>。'
             '⛔ <b>杉・檜は落とした</b>(典拠無し・在庫無し)。⛔ 竹林にしない【A 橋本・堀1998 が竹薮を79例中1例の例外とする】。'
             '⛔ <b>男坂と仁王門は下から見えなければならない</b>【S 名所図会】ので、坂の両側は帯4の退避で空ける。'
             '⚠ <b>帯1〜3は面積・本数とも概算</b> — 帯を当てる幾何(法肩線・法尻線)をまだ持っていない(「未解決」の節)。')
    h.append("<h3>境内の立木と前庭の木</h3>")
    h.append(tachiki_table(d))
    h.append('<p class="cap"><b>建物は樹林の中の明地に建つ</b>【S】。'
             '境内の立木は平場の輪郭を内へ寄せた線を共有辺とする三つの多角形で、'
             '<b>白洲と中庭は開けたまま</b>(砂利敷【S】)。'
             '★<b>主景</b>は楼門から西へ〈白洲 → 石灯籠 → 中門 → 向拝 → 拝殿 → 本殿 → 背後の林〉で、'
             '松の丈では梢が本殿の棟に隠れてしまうため<b>落葉高木を一本、位置を決めて据える</b>。'
             '前庭の木は<b>茶店の縁台に木陰を落とすため</b>で、'
             '<b>木陰を作るのは榎</b>(松は影を落とさない)。⛔ 刈込・灯籠・蹲踞を置かない。')
    h.append("<h3>参道沿いと前庭の地表</h3>")
    h.append(sando_roadside_table(d))
    h.append('<p class="cap"><b>参道は公道である。</b>植えられるのは<b>社地の側(西)だけ</b>で、'
             '觀理院の側は側溝と路肩にとどまる。⛔ <b>玉垣・並木・石灯籠の列・丁石を置かない</b> — '
             'どれも典拠が無く、置けば社の格が上がってしまう。'
             '⛔ <b>前庭を砂利敷にしない</b>(砂利は白洲の格)。'
             '⚠ <b>前庭だけ動線の退避を緩めてある</b>【ユーザー裁定 2026-09-06】 — '
             '境内と同じ退避では表参・御成・男坂が前庭を覆い尽くして植えられる場所が残らない。')
    h.append("</div>")

    plate(h, nx(), "部材", "神社建築は在庫にゼロ")
    h.append(bom_table(d))
    h.append('<p class="cap">edogoyomi / Japanese Castle / Japanese Village Kit / Waldemarst の四パックとも'
             '城郭・町屋・農家・植栽しか持たない。流用できるのは<b>石段</b>(汐見坂で実績のある段石)と'
             '<b>石灯籠</b>だけ。<b>社殿本体が最優先</b> — 現況は Village Kit の民家を代用していて神社に見えない。</p>')
    h.append("</div>")

    plate(h, nx(), "考証と決めごと", "文章の正典は sanno_kosho.md")
    h.append('<div class="prose">%s</div>' % prose)
    h.append("</div>")

    plate(h, nx(), "未解決", "推定で埋めない対象")
    h.append(pending_table(d))
    h.append("</div>")

    plate(h, nx(), "改訂", "経緯は git log docs/Sashizu/")
    h.append(history())
    _ma = sum(m["du"] * m["dv"] for m in d["munes"] if m["yaku"] != "接続") * ken * ken
    _ma += sum(r.get("bari", 2) * r["ken"] for r in d["runs"] if r.get("mune")) * ken * ken
    _ma += sum(gt["plan"]["du"] * gt["plan"]["dv"] for gt in d["gates"]) * ken * ken
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
    nsvg = html_out.count("<svg")
    # ⚠ 章の数ではなく **SVG の数**を数える(2026-08-23 検図 — 章を数えても落図を検出できない)
    html_out = html_out.replace("@@PLATES@@", "章 %d ／ 図版(SVG) %d 面" % (n[0], nsvg))
    open(OUT, "w", encoding="utf-8").write(html_out)
    print("wrote %s ／ 章 %d ／ 図版(SVG) %d 面" % (OUT, n[0], nsvg))


if __name__ == "__main__":
    main()
