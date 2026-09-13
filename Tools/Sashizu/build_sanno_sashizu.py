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
import json, sys, math, os, re, subprocess, html, bisect, collections, copy, hashlib

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


_NOTE_TD = re.compile(r"(<t[dh][^>]*>)(.*?)(</t[dh]>)", re.S)


def note_cells(html_out):
    """**註のセルの行内記法を html へ直す**【検図12巡目 低4 → 2026-09-07】。

    ⚠ 公開 html の `**` の大半は表のセル(とくに `<td class='note'>`)の中に居た ── 読者は
    `**輪郭からの離れ**` や `` `const.inubashiri` `` を**生のまま**読まされていた。
    ⛔ `inline()` は使えない ── あちらは html を escape するので、`<b>`/`<br>`/`<code>` を
    既に含む註のセル(`inline()` を通した producer が在る)を壊す。
    ⭕ ここで直すのは**マークダウンの取りこぼしだけ**で、html には触れない。
    ⛔ 図形にも数値にも影響しない(セルの中身の綴りだけ)。
    ⭐ **註のセルだけでなく表のセル全部に掛ける** ── 確度の欄(`<td>`)にも `**U 要改訂…**` が
    生のまま出ていた。同じ欠陥なので同じ所で直す。⛔ `md2html` が組んだ表のセルは既に
    `inline()` を通っているので、ここでは何も当たらない(取りこぼしだけを拾う)。
    """
    def one(m):
        t = m.group(2)
        t = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
        t = re.sub(r"~~([^~\n]+)~~", r"<s>\1</s>", t)
        return m.group(1) + t + m.group(3)
    return _NOTE_TD.sub(one, html_out)


def note_md_check(html_out):
    """組んだ後 ── **表のセルに未変換のマークダウンが残っていないか**(検図12巡目 低4)。

    ⛔ `**…**` の**対**が残っていたら止める(`note_cells` が届いていないセルが在る)。
    ⭕ 対になっていない `**` は〔記録〕 ── 本文が記号そのものを引いている行(git log の
    コミット題など)で、変換できないし、してはいけない。戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note, odd = [], [], 0
    for m in _NOTE_TD.finditer(html_out):
        t = m.group(2)
        if re.search(r"\*\*(.+?)\*\*", t, flags=re.S):
            bad.append("表のセルに未変換の太字記法(アスタリスク二つの対)が残る: %s" % t[:60])
        odd += t.count("**")
    note.append("表のセル %d 個 ── 未変換の太字記法(アスタリスク二つの対)%d 件 ／ "
                "対になっていないアスタリスク二つ %d 個"
                "(記号そのものを引いている行。⛔ 変換しない)【算出】"
                % (len(_NOTE_TD.findall(html_out)), len(bad), odd))
    return bad, note


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


def txt_w(s, fs):
    """銘の見積り幅[px] ── 和字 = `font-size` ／ 欧文 = 0.55 倍。

    ⛔ **組版の実測ではない**(見積り)。⛔ 物差しを二箇所に持たない ── 図の中で銘を窓へ
    収めるのも、`label_overlap_check` が重なりを数えるのも、この一本を使う
    【低1 庭方14巡目 → 2026-09-08】。
    """
    return sum(fs if ord(c) > 0x2000 else fs * 0.55 for c in re.sub(r"<[^>]+>", "", s))


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


# 口の縁に残る**切れ端**の下限[間](1.8 mm)。⛔ 設計値ではなく数値の残りかすを落とす閾値。
# ⚠ 2026-09-07 検図11巡目 高1 の後始末 — 口の芯と半幅を丸めると、抜いたはずの区間の端に
#   0.1 mm 級の断片が残り、**そこだけが透塀の 0.149 m 隣に立っている**ように測れた。
SEG_MIN_KEN = 0.001


def run_segs(o):
    """run/wall を開口で割った描画区間。折れ線にも対応。⛔ 1 mm 級の切れ端は run ではない。"""
    out = []
    for a, b in segs(o):
        horiz = abs(b[0] - a[0]) >= abs(b[1] - a[1])
        for p, q in gap_split(a, b, o, horiz):
            out += clip_gaps(p, q, o.get("gaps") or [])
    return [(a, b) for a, b in out if math.hypot(b[0] - a[0], b[1] - a[1]) > SEG_MIN_KEN]


def run_len_ken(o):
    """run/wall の **開口を抜いた実長**[間]。⛔ **発注量はこちら**(節点間の総和ではない)。

    ⚠ 2026-09-07 検図10巡目 中1 — 図と run の表が刷っていたのは `ken`(節点間の総和)で、
    **石段の頭・勝手口・中門・潜りの開口を一つも抜いていなかった**。`bom`「境内の外周の柵」は
    『延長は図が算出する(開口を抜いた実長)』と宣言しており、**この数がそのまま新造の発注量になる**。
    ⛔ 二本の物差しを混ぜない — 史料拘束(透塀の周長)は `run_nodes_ken` の側で読む。
    """
    if not o.get("pts") and (o.get("a") is None or o.get("b") is None): return 0.0
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in run_segs(o))


def gap_ledger(o):
    """run の**切れ目の内訳**[間] ── 折れ線 / 宣言した口 / 宣言していない切れ目(`skips`)。

    ⭐ **2026-09-07 検図12巡目 低1 で起こした。**口は**芯まわりの円**で切るので、平場の折れ返しに
    載った口は**複数の区間をまとめて食う**。⛔ そのため「折れ線 − 宣言した開口幅 − skip」は実長に
    ならず、**読者が足し算で検算できない**。⛔ 宣言幅と**実際に抜けた長さ**の両方を刷る。
    ⛔ 数を json に持たない — すべて折れ線と口の半幅からの従属値。
    """
    gs = o.get("gaps") or []
    sk = o.get("skips") or []
    dec = [q for q in gs if q not in sk]

    def L(g2):
        q = dict(o); q["gaps"] = g2
        return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in run_segs(q))
    L0 = L([])
    return {"折れ線": L0, "実長": L(gs),
            "口の宣言幅": sum(2 * q[2] for q in dec), "口が抜いた": L0 - L(dec), "口の数": len(dec),
            "skip の宣言幅": sum(2 * q[2] for q in sk), "skip が抜いた": L0 - L(sk), "skip の数": len(sk)}


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


def _site_cross(d, axis, at):
    """社地の境 `polygon` を軸平行の直線 (`axis`,`at`) が横切る点 [(座標, 辺の番号), …]。

    ⛔ 辺の番号を json へ書かない — ここで幾何から同定する(検図の作法)。
    """
    P = d["polygon"]; n = len(P); out = []
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        if axis == "EW":
            if abs(b[1] - a[1]) < 1e-12: continue
            t = (at - a[1]) / (b[1] - a[1])
            if 0.0 <= t < 1.0: out.append((a[0] + (b[0] - a[0]) * t, i))
        else:
            if abs(b[0] - a[0]) < 1e-12: continue
            t = (at - a[0]) / (b[0] - a[0])
            if 0.0 <= t < 1.0: out.append((a[1] + (b[1] - a[1]) * t, i))
    return sorted(out)


def size_spelling_check(d):
    """**`sizeRule.sizes` の綴りが目録で解けるか**(⛔ 目録に無い綴りは黙って落ちる)。

    ⭐ **2026-09-08(軽微4 考証15巡目)で起こした。**`sizes` は `H12`/`H20` を並べるが、
    目録には低木の `Small`(1.2 m)/`Mid`(2.0 m)しか無い。`part_variants` は解けない綴りを
    **`continue` で黙って飛ばす**ので、⛔ 読む側からは『四刻みが解けている』ようにしか見えない
    (`_sizes` の註にだけ「リネーム未了」と書いてあった = 註を読まねば分からない形)。
    ⇒ **綴り × 雛形の解決を毎回一本ずつ刷り**、一つの雛形にも当たらない綴りは
    `sizesPendingRef` が指す `_pending` の項で猶予する(項が無ければ⛔)。
    """
    sr = size_rule(d) or {}
    bad, note = [], []
    if not sr.get("sizes"): return bad, note
    ref = sr.get("sizesPendingRef")
    tpl = [(lay, pt) for lay in sr.get("layers", [])
           for pt in d["planting"]["parts"].get(lay, []) if part_is_tpl(pt)]
    for sz in sr["sizes"]:
        hit = [lay for lay, pt in tpl
               if part_geom({"prefab": (pt.get("prefab") or "").replace(_SIZE_HOLE, sz)})
               is not None]
        if hit:
            note.append("綴り『%s』── 目録で解ける雛形 %d 点(層 %s)【算出】"
                        % (sz, len(hit), "・".join(sorted(set(hit)))))
        elif ref and ref in (d.get("_pending") or {}):
            note.append("⚠ 綴り『%s』── **目録に一点も無い**(→ `_pending`「%s」)"
                        "【算出 — ⛔ 猶予であって合格ではない。項が消えれば⛔】" % (sz, ref))
        else:
            bad.append("`sizeRule.sizes` の綴り『%s』は**目録に一点も無い**のに、猶予の項"
                       "(`sizesPendingRef`)を宣言していない — ⛔ 目録に無い綴りは "
                       "`LoadAssetAtPath` が黙って null を返す(規則12)" % sz)
    note.append("`sizeRule.sizes` の綴り %d 個 × 雛形 %d 点 ── 目録で解ける綴り %d ／ "
                "解けない綴り %d(猶予)【算出 — ⛔ `_sizes` の註だけに『過渡措置』と書かない。"
                "**読む側から見える所で毎回数える**】"
                % (len(sr["sizes"]), len(tpl),
                   len([q for q in note if q.startswith("綴り")]),
                   len([q for q in note if q.startswith("⚠ 綴り")])))
    return bad, note


def section_window_check(d):
    """**断面の窓が社地の境を跨ぐか**(⛔ 片側だけ境まで写して他方を切り落とさない)。

    ⭐ **2026-09-08(低1 検図17巡目)で起こした。**この不変条件は 2026-09-08 に**文章として**
    断面ルの註へ入っただけで、**機械検査に落ちていなかった** ── 手で直した一面だけが従い、
    残りは誰も測っていない状態だった(§B-5「検査が無い不変条件は必ず壊れる」)。
    ⛔ 実際、書いた翌日に**断面ソ**(東端だけが境を跨ぎ、西端は境の内側 25.1 m)と
    **断面ロ**(南端だけが跨ぎ、北端は 38.2 m 内側)の二面が同じ形で残っていた。

    **測る集合** ── `axis` が EW/NS の断面**すべて**の**両端**。ただし ⛔ に問うのは
    **片側が境を跨いでいる面だけ**である ── 両端とも境の内で閉じる面(社殿まわりの寄りの断面)は
    「境まで写す」と名乗っていないので、この条項の対象ではない。⚠ **この線引きを図に明記する**
    (⛔ 黙って狭い集合を測らない・規則19)。

    ⭕ **逃げ道は一つだけ** ── `sections[].edgeRecv`(受け手の断面)を名指しし、その断面が
    **同じ境の辺**を跨いでいること。⛔ 宣言が実体と合わなければ⛔。
    """
    bad, note = [], []
    P = d["polygon"]
    _wpt = lambda ax, at, c: (c, at) if ax == "EW" else (at, c)
    allsec = d.get("sections", [])
    secs = [q for q in allsec if q.get("axis") in ("EW", "NS")]
    skip = [q["kana"] for q in allsec if q.get("axis") not in ("EW", "NS")]
    # 辺ごとに「その辺を跨ぐ断面」を先に集める(受け手の資格はこれで決まる)。
    # ⭐ **どこで跨ぐかも一緒に持つ**【低3 検図18巡目 → 2026-09-08】── 旧版は名前だけを集めており、
    #    **同じ辺の反対の端を跨ぐだけの面**を受け手に立てても通った(辺7 は 56 m ある)。
    #    ⛔ 数は締めない ── ⭕ 隔たりが〔記録〕に出れば読む人が見て判じられる。
    cover = {}
    for s in secs:
        ln = s["line"]
        k = 0 if s["axis"] == "EW" else 1
        e0, e1 = sorted([ln[0][k], ln[-1][k]])
        cr = _site_cross(d, s["axis"], s["at"])
        if not cr: continue
        for c, ei in cr:
            if e0 - 1e-9 <= c <= e1 + 1e-9:
                cover.setdefault(ei, []).append((s["kana"], _wpt(s["axis"], s["at"], c)))
    n_open, cross, thin, n_mark = 0, [], [], 0
    for s in secs:
        ln = s["line"]
        k = 0 if s["axis"] == "EW" else 1
        e0, e1 = sorted([ln[0][k], ln[-1][k]])
        stp = float(d["profiles"][s["profile"]]["step"])
        cr = _site_cross(d, s["axis"], s["at"])
        if not cr:
            note.append("断面%s ── 切断線が社地の境を一度も横切らない(社地の外の面)"
                        "【算出 — この条項の対象外】" % s["kana"])
            continue
        (lo, ilo), (hi, ihi) = cr[0], cr[-1]
        sides = [("西" if s["axis"] == "EW" else "南", e0 <= lo + 1e-9, lo - e0, ilo, lo),
                 ("東" if s["axis"] == "EW" else "北", e1 >= hi - 1e-9, e1 - hi, ihi, hi)]
        if not any(q[1] for q in sides):
            note.append("断面%s ── 両端とも社地の境の内で閉じる(寄りの断面)"
                        "【算出 — ⛔ この条項の対象外。『境まで写す』と名乗っていない】"
                        % s["kana"])
            continue
        n_open += 1
        rcv = s.get("edgeRecv") or {}
        for nm, ok, dd, ei, cc in sides:
            if ok:
                # ⭐ **跨ぎ量を出す**【低2 検図18巡目 → 2026-09-08】── 閾は 0 のままなので
                #    「形式だけ跨いだ面」と「法尻まで写した面」が同じ⭕になる。⛔ ⛔にはしない
                #    (窓を締めるのは意匠の判断)が、⚠ **刻み1つに満たない跨ぎは名指しする**。
                cross.append((s["kana"], nm, dd))
                thn = dd < stp - 1e-9
                if thn: thin.append("断面%s の%s端(%.1f m < 刻み %.1f m)" % (s["kana"], nm, dd, stp))
                note.append("断面%s の%s端 ── 社地の境を **%.1f m 跨ぐ**(縦断の刻み %.1f m)%s【算出】"
                            % (s["kana"], nm, dd, stp,
                               " ⚠ **刻み1つ分に満たない** — 境の外の標本が1点しかない"
                               if thn else ""))
                continue
            r = rcv.get(nm)
            if r:
                got = [q for q in (cover.get(ei) or []) if q[0] == r]
                if got:
                    W_ = _wpt(s["axis"], s["at"], cc)
                    gap = min(math.hypot(q[1][0] - W_[0], q[1][1] - W_[1]) for q in got)
                    a_, b_ = P[ei], P[(ei + 1) % len(P)]
                    eln = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
                    note.append("断面%s の%s端 ── 境の内側 %.1f m で切れるが、**断面%s が同じ境の辺"
                                "(辺%d・長さ %.1f m)を跨いで受ける**。⚠ **受け手との隔たり %.1f m**"
                                "【算出 — 受け手の宣言 `edgeRecv`。⛔ 隔たりに閾は置かない ── "
                                "同じ辺のどこで受けるかは読む人が判じる】"
                                % (s["kana"], nm, -dd, r, ei, eln, gap))
                else:
                    bad.append("断面%s の%s端が受け手に立てた『断面%s』は、**その端が切り落とした"
                               "境の辺を跨いでいない** — 受け手になっていない宣言である"
                               % (s["kana"], nm, r))
            else:
                bad.append("断面%s は%sと反対の端で社地の境を跨ぐのに、%s端は**境の内側 %.1f m で"
                           "切れており**、受け手の断面(`edgeRecv`)も宣言していない — "
                           "⛔ 『社地の境まで写す』判断を片側だけに当てない"
                           % (s["kana"], nm, nm, -dd))
        # ⭐ **図の上に境の銘が立つか**【中1 検図18巡目 → 2026-09-08】── 不変条件を新設して窓を
        #    動かしても、⛔ 図に境が出ていなければ読む人は跨いだかどうかを確かめられない(規則19)。
        ed = section_site_edges(d, s["profile"], _profile(d, s["profile"]))
        n_mark += len(ed)
        if not ed:
            bad.append("断面%s は社地の境を跨ぐ面なのに、**図の上に境の銘が一本も立たない** — "
                       "⛔ 測ったのに図に出ていない(規則19 第3型)" % s["kana"])
    if cross:
        _mn = min(cross, key=lambda q: q[2])
        note.append("跨ぎ量 ── **最小 %.1f m(断面%s の%s端)／ 最大 %.1f m** ／ 刻み1つ分に"
                    "満たない端 %d 箇所%s【算出 — ⛔ 閾は 0 のまま(『跨いだか』だけを⛔にする)。"
                    "⭕ **どれだけ跨いだかはここで毎回刷る** ── 形式だけ跨いだ面と法尻まで写した面を"
                    "同じ⭕として読まないため】"
                    % (_mn[2], _mn[0], _mn[1], max(q[2] for q in cross), len(thin),
                       "(%s)" % "・".join(thin) if thin else ""))
    note.append("断面 %d 面のうち EW/NS は %d 面 ── 片側以上が社地の境を跨ぐ面 %d 面"
                "(この条項の対象・図の上に境の銘 %d 本が立つ)／ 両端とも境の内で閉じる面 %d 面"
                "(対象外)／ **軸平行でない %d 面(%s)は対象外**(`_site_cross` は軸平行の直線しか"
                "解かない)【算出 — ⛔ 対象外の面を『合格』と読まない。測っていないだけである。"
                "⛔ 黙って狭い集合を測らない(規則19)】"
                % (len(allsec), len(secs), n_open, n_mark,
                   len(secs) - n_open, len(skip), "・".join(skip)))
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
    ⛔ **標本は `run_segs`(開口と skip を抜いた実体)から採る**【検図12巡目 中1 → 2026-09-07】。
    ⚠ 旧版は `pts`(開口を抜く前の生の折れ線)を標本しており、**柵が一本も立っていない開口の中**を
    「最も痩せる隅」として刷っていた(女坂の頭の口の内側)。⛔ 同じ図の中に二本の物差しを置かない —
    同じ巡に入れた `kakoi_cross_check` は最初から `run_segs` を使っていた。
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
    # ⛔ **`pts`(開口を抜く前の生の折れ線)を標本しない**【検図12巡目 中1 → 2026-09-07】。
    #    旧版は生の折れ線を測っていたので、**柵が一本も立っていない開口の中**を最も痩せる隅として
    #    刷り、その幻の値が公開 html に 11 箇所と `_pending` の本文へ回っていた。
    #    ⭕ 測るのは **`run_segs`(開口と skip を抜いた、実際に建つ区間)**。
    ds, outside = [], []
    for a, b in run_segs(r):
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
                "`const.inubashiri` %.2f m)── ⛔ 標本は **`run_segs`(開口と skip を抜いた、"
                "実際に建つ区間)**から採る(⛔ 生の折れ線 `pts` を測らない・検図12巡目 中1)。"
                "⚠ **辺の上では恒真**(柵は輪郭をこの幅だけ内へ寄せた生成物)。⭕ 読むのは**角**で、"
                "宣言を下回る標本 %d 点・最小 %.3f m は鋭角の隅で隣の辺のほうが近くなる分【算出】"
                % (lo[0], hi[0], len(ds), ins, len(short), lo[0]))
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
        note.append("**柵が実際に立っている所**で最も痩せる隅は u %.2f, v %.2f"
                    "(離れ %.3f m = 宣言の %.0f%% ／ 不足 %.3f m)"
                    "── ⛔ 直すには輪郭か寸法を動かすことになるので指図方は動かさない"
                    "(→ `_pending`「境内の囲いの留めの隅が犬走りを割る」)【算出】"
                    % (lo[1][0], lo[1][1], lo[0], 100.0 * lo[0] / ins, ins - lo[0]))
    return bad, note


def terrace_shape_check(d):
    """**平場の輪郭の健全性** ── ⛔ 重複頂点 / 零長辺 / 自己交差。〔記録〕に最鋭の内角。

    ⭐ **2026-09-07 検図12巡目 中2 で起こした。**検図11巡目 高1(平場の南縁の**作図の縮退** ──
    同じ点が二つ並び、幅 0.22 間の外部スリットを作っていた)は**検図が手で総当たりして見つけた**
    もので、⛔ **輪郭の縮退という原因を見ている検査は一本も無かった**。破壊試験(重複頂点を戻す)
    でも ⛔ は一件も鳴らず、柵の実長だけが黙って変わった ── 症状が消えて原因が見えなくなった形。
    ⛔ **全ての `terraces` に掛ける**(矩形の段も 4 頂点の輪郭として測る)。
    ⛔ **内角は⛔にしない** ── 鋭いこと自体は欠陥ではない。⭕ **痩せの源を名指すための〔記録〕**で、
    境内の囲いの犬走りが隅で宣言を下回るのはここから来る(→ `_pending`
    「境内の囲いの留めの隅が犬走りを割る」)。
    戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    for te in d["terraces"]:
        nm = te.get("name", "?")
        P = [(q[0], q[1]) for q in terrace_poly_uv(te)]
        n = len(P)
        if n < 3:
            bad.append("平場『%s』の輪郭が %d 頂点 — 多角形にならない" % (nm, n))
            continue
        # ⛔ 零長辺(隣り合う二点が重なる)
        zero = [i for i in range(n)
                if math.hypot(P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1])
                < TERRACE_DEGEN_KEN]
        for i in zero:
            bad.append("平場『%s』の輪郭に**零長辺** — 頂点 %d と %d が uv(%.3f, %.3f) で重なる。"
                       "⛔ 輪郭からの生成物(囲い・犬走り)がここで暴れる"
                       % (nm, i, (i + 1) % n, P[i][0], P[i][1]))
        # ⛔ 重複頂点(隣り合っていない二点が同じ所に来る)
        for i in range(n):
            for j in range(i + 1, n):
                if (j - i) % n in (1, n - 1): continue
                if math.hypot(P[j][0] - P[i][0], P[j][1] - P[i][1]) < TERRACE_DEGEN_KEN:
                    bad.append("平場『%s』の輪郭に**重複頂点** — 頂点 %d と %d が "
                               "uv(%.3f, %.3f) で重なる。⛔ 輪郭が自分自身に触れている"
                               % (nm, i, j, P[i][0], P[i][1]))
        # ⛔ 自己交差(隣り合わない辺どうし)
        for i in range(n):
            for j in range(i + 1, n):
                if (j - i) % n in (1, n - 1): continue
                x = _seg_cross(P[i], P[(i + 1) % n], P[j], P[(j + 1) % n])
                if x:
                    bad.append("平場『%s』の輪郭が**自己交差する** — 辺 %d-%d と 辺 %d-%d が "
                               "uv(%.3f, %.3f) で交わる"
                               % (nm, i, (i + 1) % n, j, (j + 1) % n, x[0][0], x[0][1]))
        ang = []
        for i in range(n):
            p0, p1, p2 = P[i - 1], P[i], P[(i + 1) % n]
            v1 = (p0[0] - p1[0], p0[1] - p1[1]); v2 = (p2[0] - p1[0], p2[1] - p1[1])
            l1, l2 = math.hypot(*v1), math.hypot(*v2)
            if l1 < 1e-12 or l2 < 1e-12: continue
            c = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))
            ang.append((math.degrees(math.acos(c)), i, p1))
        # ⭐ **輪郭の首**(隣り合わない辺どうしの最小距離)【検図12巡目 → 2026-09-08】。
        #    ⛔ ⛔にはしない ── 鋭い角と同じで、痩せの源を名指すための〔記録〕である。
        neck, npair = None, None
        for i in range(n):
            for j in range(i + 1, n):
                if (j - i) % n in (0, 1, n - 1): continue
                dd = _seg_seg_dist(P[i], P[(i + 1) % n], P[j], P[(j + 1) % n])
                if neck is None or dd < neck:
                    neck, npair = dd, (i, (i + 1) % n, j, (j + 1) % n)
        if neck is not None:
            note.append("平場『%s』の**輪郭の首**(隣り合わない辺どうしの最小距離) %.3f 間 = %.3f m"
                        "(辺 %d-%d ↔ 辺 %d-%d)【算出 — ⛔ ⛔にはしない。⭕ 囲い・犬走り・"
                        "低木の面が隅で痩せる源を名指すための〔記録〕】"
                        % (nm, neck, neck * d["const"]["ken"], npair[0], npair[1],
                           npair[2], npair[3]))
        if ang:
            ang.sort()
            note.append("平場『%s』── 頂点 %d ／ 零長辺 %d ／ 最も鋭い角 %s"
                        "【算出 — ⛔ 鋭いこと自体は欠陥ではない。⭕ **境内の囲いの犬走りが隅で"
                        "宣言を下回るのはここが源**(→ 検査『境内の囲いの犬走り』)】"
                        % (nm, n, len(zero),
                           "／".join("%.1f° 頂点%d uv(%.3f, %.3f)" % (a_, i_, q[0], q[1])
                                     for a_, i_, q in ang[:3])))
    return bad, note


def kaidan_close_check(d):
    """石段の**閉合**〔記録〕 ── 蹴上×段数 と 比高 の差を、どの段が吸うか。

    ⭐ 2026-09-08 ── `stair_y_at` は**頭で寄せる**(最後の蹴上を上がりきった高さ=`yTop`)ので、
    丸めの差は**最上段の蹴上**に全部乗る。⛔ 設計値は動かさない(蹴上・踏面は段数と平面長からの
    従属値=2026-08-24 ユーザー裁定)。⛔ ⛔にはしない ── 図が黙って持っている量を出すだけ。
    """
    bad, note = [], []
    for k in d["kaidans"]:
        n = k.get("steps")
        ke = k.get("keri")
        if not n or not ke: continue
        rise = k["yTop"] - k["yBot"]
        dv = ke * n - rise
        last = rise - ke * (n - 1)
        note.append("石段『%s』── 比高 %.3f m ／ 蹴上 %.3f m × %d 段 = %.3f m ／ **閉合差 %+.3f m**"
                    " ／ 丸めの吸収先=**最上段の蹴上 %.3f m**(`stair_y_at` は頭で寄せる)"
                    "【算出 — ⛔ 設計値は動かさない】" % (k["name"], rise, ke, n, ke * n, -dv, last))
    # ⭐⭐ **本殿の木階が `const.shadenHondenStepM` を負っているか**【B-8 検図22巡目 →
    #   2026-09-09 十九巡目】── ⚠ 旧図は段そのものが `kaidans` に無く、⛔ **図の中で唯一、
    #   閉合(蹴上 × 段数 = 比高)が検算されない段**だった(⛔ 0 件は合格ではなく未測定・規則19)。
    kz8 = [q["name"] for q in d["kaidans"] if q.get("kizahashi")]
    note.append("坂の割付図(其八)に描かない段 **%d 本**(%s)── ⭕ **木階**(`kizahashi`)なので"
                "『参道の坂の段割り』の物差しの対象外。⛔ 黙って図から落とさない(規則19)"
                "【算出 — B-8 検図22巡目 → 2026-09-09】"
                % (len(kz8), "・".join(kz8) or "—"))
    st9 = d["const"].get("shadenHondenStepM")
    kz9 = [q for q in d["kaidans"] if q["name"].startswith("本殿の木階")]
    if st9 is None:
        bad.append("`const.shadenHondenStepM`(幣殿の床 → 本殿の床の段)の宣言が無い")
    elif not kz9:
        bad.append("`const.shadenHondenStepM` %.2f m を負う段が `kaidans` に無い — ⛔ 宣言だけ"
                   "あって閉合が検算されない段を残さない(B-8 検図22巡目・規則19)" % st9)
    else:
        k9 = kz9[0]
        r9 = k9["yTop"] - k9["yBot"]
        if abs(r9 - st9) > 1e-6:
            bad.append("本殿の木階の比高 %.3f m が `const.shadenHondenStepM` %.3f m と違う — "
                       "⛔ 同じ段に正典を二つ持たない(規則4)" % (r9, st9))
        else:
            note.append("本殿の木階 ⭕ ── 比高 %.3f m は `const.shadenHondenStepM` そのもの ／ "
                        "蹴上 %.3f m × %d 級(登高欄付き)／ 踏面 %.3f m(= 作り合いの一間 ÷ 段数)"
                        "【算出 — B-8 検図22巡目 → 2026-09-09。⛔ 数を文章に写さない】"
                        % (r9, k9["keri"], k9["steps"], k9["fumi"]))
    return bad, note


def saku_order_rows(d):
    """**腰高の柵(玉垣と同じ部材)の発注量**[m]の内訳 ── ⛔ 数を json に持たない。

    ⭐ 2026-09-07 庭方4巡目 裁き1 ── 法尻の柵2本(`Saku_SW`・`Saku_Sando`)に丈の宣言も
    部材の行も無く、**発注量から丸ごと抜けていた**。玉垣・境内の外周の柵・法尻の柵は
    **同じ部材**なので、`fence: true` の辺と柵 run の**開口を抜いた実長**(`run_len_ken`)から
    ここで合算する。⛔ `bom` にベタ書きしない。
    """
    ken = d["const"]["ken"]
    rows = []
    for gd in d["gardens"]:
        if not gd.get("tamagaki"): continue
        s = 0.0
        for _nm, _a, _b, fence, _ln, rs in tamagaki_edges(d, gd):
            if not fence: continue
            s += sum(math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]) for q in rs)
        if s > 1e-9: rows.append(("玉垣(%s)" % gd["name"], s * ken))
    for r in d["runs"]:
        if r["kind"] != "柵" or run_tamagaki(d, r) is None: continue
        rows.append((r["name"], run_len_ken(r) * ken))
    return rows


def roof_decl_check(d):
    """**屋根を持つ run が葺材を宣言しているか**【高1 考証19巡目 → 2026-09-09】。

    ⛔ `mune: true`(棟として建蔽率の分子に入る run = 回廊)が `roof` を宣言していなければ、
      ⛔ **材を発明した状態で実装へ渡る**。⚠ 旧図の `runs[Kairo_*]` がまさにそれで、
      `acc` は 存在S/総長A/梁間U だけ、屋根材はどこにも書かれていなかった。
    ⛔ **【S】を名乗れない材を【S】で書かせない** ── 旧国宝の指定は本殿・幣殿・拝殿・中門・
      透塀の5件のみで、`[国宝建造物目録1941]` 自身が『楼門・回廊・随身門は指定外』と書く。
    """
    bad, note = [], []
    n9 = 0
    for r in d["runs"]:
        if not r.get("mune"): continue
        n9 += 1
        rf = r.get("roof")
        if not rf:
            bad.append("屋根を持つ run『%s』(`mune: true`)が `roof`(葺材)を宣言していない — "
                       "⛔ **材を発明した状態で実装へ渡る**(高1 考証19巡目 2026-09-09)"
                       % r["name"])
            continue
        acc9 = r.get("acc") or ""
        if "【S" in rf and "指定" not in acc9:
            bad.append("run『%s』の `roof` が【S】を名乗るのに `acc` が典拠を持たない — "
                       "⛔ 指定外の物件に指定説明の格を当てない(高1 考証19巡目)" % r["name"])
        note.append("屋根を持つ run『%s』── 葺材 %s【算出 — ⛔ 0 件は合格ではなく未測定。"
                    "⚠ **回廊は旧国宝の指定外**なので、社殿と同材にするのは【U 設計判断】である】"
                    % (r["name"], rf.split("(")[0][:60]))
    note.append("屋根を持つ run **%d 本**のうち葺材を宣言する %d 本【算出 — 高1 考証19巡目】"
                % (n9, n9 - len([q for q in bad if "宣言していない" in q])))
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

    ⭐ **2026-09-07 庭方4巡目 裁き1 で三方へ広げた。**
    (c) **柵はすべて丈を宣言する** ── `Saku_SW`・`Saku_Sando` は丈も部材の行も持たず、
        合わせて 200 m を超える延長が**発注量から丸ごと抜けていた**。
    (d) **丈を玉垣から引く run は `kind`=柵でなければならない** ── 破壊試験で
        `Saku_Sando` を板塀へ書き換えたら**一本も鳴らなかった**(名指しで守っていたのは
        `Ita_Keidai` だけだった)。
    (e) **発注量の合計を刷る** ── 玉垣・境内の外周・法尻の柵は同じ部材で、新造は一度で足りる。
    戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
    ken = d["const"]["ken"]
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
    # ⛔ **丈を玉垣から引く run は柵でなければならない**【裁き1 の破壊試験 (3) で開いた穴を塞ぐ】
    #    ── `Ita_Keidai` だけを名指しで守っていたので、`Saku_SW`・`Saku_Sando` の `kind` を
    #    板塀へ書き換えても**検査が1本も鳴らず、発注量が黙って痩せた**。
    for q in d["runs"]:
        if q.get("hFrom") and q["kind"] != "柵":
            bad.append("`runs[%s]` が丈を玉垣(`hFrom`)から引くのに `kind` が『%s』── "
                       "玉垣と同じ丈・同じ作りの物は**腰高の柵**である【裁き1 庭方 2026-09-07】。"
                       "種別を替えると平面図の姿・囲いの展開の姿・`bom` の行・**発注量**が黙って入れ替わる"
                       % (q["name"], q["kind"]))
    saku = [q for q in d["runs"] if q["kind"] == "柵"]
    nod = [q["name"] for q in saku if not q.get("hFrom")]
    # ⛔ **柵はすべて丈を宣言する**【裁き1 庭方 2026-09-07】── 宣言の無い柵は図が丈「—」を刷り、
    #    柱の刻みを引かず、`bom` の行にも載らないので**発注量から丸ごと抜ける**(規則19)。
    for q in nod:
        bad.append("`runs[%s].hFrom` の宣言が無い ── 柵は玉垣と同じ部材なので丈は "
                   "`gardens[].tamagaki.hM` からの従属値で持つ【裁き1 庭方 2026-09-07】。"
                   "宣言が無いと図が丈「—」を刷り、柱の刻みを引かず、**発注量から抜ける**" % q)
    note.append("柵 %d 本(%s)── うち丈を宣言(`hFrom` → `gardens[].tamagaki`)する %d 本"
                "(⛔ 宣言の無い柵: %s)【算出】"
                % (len(saku), "・".join(q["name"] for q in saku), len(saku) - len(nod),
                   "・".join(nod) or "無し"))
    ordr = saku_order_rows(d)
    if ordr:
        note.append("**腰高の柵(玉垣と同じ部材)の発注量 計 %.2f m** ── %s。⛔ この数を `bom` に"
                    "書かない — `fence: true` の辺と柵 run の**開口を抜いた実長**からの従属値で、"
                    "新造(edo-buzai)は一度で足りる【算出】"
                    % (sum(q[1] for q in ordr), " ＋ ".join("%s %.2f" % q for q in ordr)))
    # ⭐ **切れ目の内訳を刷る**【検図12巡目 低1 → 2026-09-07】── 口は**芯まわりの円**で切るので、
    #    折れ返しに載った口は複数の区間をまとめて食う。⛔ 「折れ線 − 宣言幅 − skip」は実長にならず、
    #    **読者が上の発注量を足し算で検算できない**。⛔ 発注量の側は正しい(実体の長さだから)。
    for q in d["runs"]:
        if not (q.get("gaps") or q.get("skips")): continue
        lg = gap_ledger(q)
        note.append("『%s』の**切れ目の内訳** ── 折れ線 %.3f m ／ 宣言した口 %d 箇所"
                    "(宣言幅 計 %.3f m ／ **実際に抜けた長さ 計 %.3f m**)／ "
                    "宣言していない切れ目 `skips` %d 箇所(宣言幅 計 %.3f m ／ 実際に抜けた %.3f m)"
                    "→ **実長 %.3f m**。⚠ **宣言幅と実際に抜けた長さは一致しない** — 口は芯まわりの"
                    "円で切るので、平場の折れ返しに載った口は複数の区間をまとめて食う"
                    "【算出 — ⛔ 数を json に持たない】"
                    % (q["name"], lg["折れ線"] * ken, lg["口の数"], lg["口の宣言幅"] * ken,
                       lg["口が抜いた"] * ken, lg["skip の数"], lg["skip の宣言幅"] * ken,
                       lg["skip が抜いた"] * ken, lg["実長"] * ken))
    # ⭐ **部材として建たない長さの区間が残っていないか**【庭方6巡目 低2 → 2026-09-07】。
    #    ⛔ ⛔にしない — いま 1 本あるので止めると図が組めず、直すには口の寸法(石段の幅からの
    #    従属値)が動く。⛔ 下限を数で持たない — **立子の割付 `tamagaki.tatekoPitchM` からの従属値**。
    for q in saku:
        tg = run_tamagaki(d, q)
        if tg is None: continue
        lim = tg[0].get("tatekoPitchM")
        if lim is None: continue
        stub = [(a, b) for a, b in run_segs(q)
                if math.hypot(b[0] - a[0], b[1] - a[1]) * ken < lim - 1e-9]
        note.append("『%s』の区間 %d 本のうち、**立子の割付 %.2f m(`tamagaki.tatekoPitchM`)より"
                    "短い区間 %d 本**%s ── ⛔ 柵一枚より短い区間は部材として建たない"
                    "【算出 — ⛔ 下限を数で持たない。⚠ ⛔にはしない(直すには口の寸法が動く)"
                    "→ `_pending`「境内の外周の柵に部材として建たない切れ端が1本残る」】"
                    % (q["name"], len(run_segs(q)), lim, len(stub),
                       ("(最短 %.3f m ／ uv(%.3f, %.3f)→(%.3f, %.3f))"
                        % ((lambda t: (math.hypot(t[1][0] - t[0][0], t[1][1] - t[0][1]) * ken,
                                       t[0][0], t[0][1], t[1][0], t[1][1]))
                           (min(stub, key=lambda t: math.hypot(t[1][0] - t[0][0],
                                                               t[1][1] - t[0][1]))))) if stub else ""))
    return bad, note


def _kakoi_items(d):
    """**線でできている物**(囲い・土留め)と、**帯を持つ物**(回廊の屋根・石段の踏面)の名簿。

    戻り (線の列, 帯の列)。線は (呼び名, 開口を抜いた区間)、帯は (呼び名, 区間, 半幅[間])。
    ⛔ 半幅を数で持たない ── 回廊は `runs[].bari`、石段は `kaidans[].wKen` からの従属値。
    """
    lines = [(r["kind"] + ":" + r["name"], run_segs(r)) for r in d["runs"]]
    lines += [("土留め:" + w["name"], run_segs(w)) for w in d["terraceWalls"]]
    lines = [q for q in lines if q[1]]
    bands = [("回廊の屋根:" + r["name"], run_segs(r), r.get("bari", 2) / 2.0)
             for r in d["runs"] if r.get("mune")]
    for k in d["kaidans"]:
        pt = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        bands.append(("石段:" + k["name"], [(pt[i], pt[i + 1]) for i in range(len(pt) - 1)],
                      kaidan_wken(d, k) / 2.0))
    return lines, [q for q in bands if q[1]]


def _band_rects(sgs, hw):
    """帯を**区間ごとの矩形**にする。⛔ 端に丸みを付けない(坂の上下の先は坂ではない)。"""
    out = []
    for a, b in sgs:
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz)
        if L < 1e-12: continue
        nx, nz = -dz / L * hw, dx / L * hw
        out.append([(a[0] + nx, a[1] + nz), (b[0] + nx, b[1] + nz),
                    (b[0] - nx, b[1] - nz), (a[0] - nx, a[1] - nz)])
    return out


def _line_band_gap(sgs, rects):
    """線と帯の**符号つきの離れ**[間]。負なら線が帯へ**食い込む**(深さ)。

    ⭐ **2026-09-07 検図12巡目 低3 で起こした。**⛔ 芯線どうしの距離では測れない ── 帯は幅を持つ。
    ⚠ **測っているのは「線の点が帯の内へどれだけ入るか」**である。
    ⭕ **帯を真横に突き抜ける線は正しく捕まる** ── 端点が帯の外にあっても線は縁を横切るので
    `dd ≤ BAND_TOUCH_KEN` が立ち、食い込みの深さ(半幅ぶん)が負で返る。⛔ 旧版の docstring は
    ここを「0.000 と読む」と書いていたが**事実ではなかった**(2026-09-08 に実測して差し替えた)。
    ⛔ **実在する限界は逆側**: **線が帯の内へ丸ごと入り、どの縁にも `BAND_TOUCH_KEN` まで
    近づかない**とき ── `dd` は縁までの正の距離になり、**食い込みが『離れ』と読まれて黙る**。
    ⚠ この形は当図の 156 組に 0 件だが、⛔ **0 件は『起きない』の意ではない**(規則19)。
    """
    best = None
    for a, b in sgs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        for R in rects:
            dd = min(_seg_seg_dist(a, b, R[k], R[(k + 1) % 4]) for k in range(4))
            if dd <= BAND_TOUCH_KEN:
                n = max(1, int(L / 0.05))
                pen = 0.0
                for i in range(n + 1):
                    t = i / float(n)
                    q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                    if in_poly(q, R):
                        pen = max(pen, min(_pt_seg(q, R[k], R[(k + 1) % 4]) for k in range(4)))
                if pen > BAND_TOUCH_KEN: dd = -pen
            best = dd if best is None else min(best, dd)
    return best


# 交点が折れ線の「途中」か「端」かを分ける許容[間]。⛔ 設計値ではなく判別の物差し。
KAKOI_END_KEN = 0.02

# 線が帯の縁に**接する**のか**食い込む**のかを分ける許容[間](1.8 mm)。⛔ 設計値ではなく判別の物差し。
# ⚠ 石段の側壁は自分の踏面の帯の縁の上に立つのが正しい姿で、そこは 0.000 で接する(検図12巡目 低3)。
BAND_TOUCH_KEN = 0.001

# 平場の輪郭の**縮退**(同じ点・零長辺)を判別する許容[間](1.8 mm)。⛔ 設計値ではなく判別の物差し。
TERRACE_DEGEN_KEN = 0.001


def kakoi_cross_check(d, g):
    """**囲い・土留め・屋根の帯どうしの交差と離れ**【検図11巡目 中1 → 2026-09-07】。

    ⭐ **なぜ要るか。** 面の総当たり `rect_overlap_check` の集合は棟・門・区・帯・石段・塊・
    玉垣・低木の面・踏石・点景まで広げてあるが、**囲い(`runs`)・土留め(`terraceWalls`)・
    回廊の屋根の帯は一つも入っていない**。検査名はその集合を正直に名乗っているので偽陽性は
    無いが、⛔ **この class は誰も測っておらず、境内の柵が透塀を2回横切る欠陥がそこへ落ちた**。

    **物差しは四つ。**
    ① **真の交差** ── 芯線どうしの交点が**両方の折れ線の途中**(端から `KAKOI_END_KEN` 超)に
       ある組。端で交わる組は**隅の突き付け**(塀は門・棟・土留めに取り付くのが正しい姿)で、
       〔記録〕に数だけ刷る。
    ② **帯の重なり** ── 回廊の屋根・石段の踏面は**幅を持つ**ので、区間ごとの矩形どうしの
       離れ(SAT)が負なら重なり。⛔ 芯線の距離で測らない(直交する帯で嘘が出る)。
    ③ **離れ** ── 交差しない組の芯線どうしの最小の離れが犬走り `const.inubashiri` を割る組。
    ④ **線 × 帯** ── 囲い・土留め(線)と 回廊の屋根・石段の踏面(帯)の**積**
       【検図12巡目 低3 → 2026-09-07】。⛔ **旧版はこの積を誰も測っていなかった**(線×線 と
       帯×帯 だけ)。⭕ 石段の側壁が自分の踏面の帯の縁に立つ 0.000 m の接触は**設計上の姿**なので
       数だけ刷り、⛔ 食い込みと犬走り割れは名簿を要求する。
    ⛔ **どれも名簿 `kakoiCross.roster` に無ければ止める。**名簿は `_pending` を指し、
       `roster_guard` が**両方向**に突き合わせる(死んだ名簿も⛔・規則19)。
    ⛔ 名簿そのものの宣言が無ければ止める ── 宣言を消せば何が起きても鳴らなくなる。
    """
    ken = d["const"]["ken"]
    ins = d["const"]["inubashiri"] / ken
    sp = d.get("kakoiCross") or {}
    bad, note = [], []
    if sp.get("roster") is None:
        bad.append("囲い・土留め・屋根の帯の**許した交差と近接の名簿** `kakoiCross.roster` の"
                   "宣言が無い — 宣言が無ければ何が交わっても鳴らない(規則19)")
    ros = {}
    for q in sp.get("roster") or []:
        if not q.get("pending"):
            bad.append("`kakoiCross.roster` の『%s × %s』に `pending`(差し戻し先)が無い — "
                       "許した交差は必ず宿題として名指す" % (q.get("a"), q.get("b")))
        elif q["pending"] not in (d.get("_pending") or {}):
            bad.append("`kakoiCross.roster` の『%s × %s』が `_pending`「%s」を指すが、"
                       "その項が無い(指し先の無いポインタ)" % (q.get("a"), q.get("b"), q["pending"]))
        ros["|".join(sorted((q["a"], q["b"])))] = q
    # ⭐ **柵を回さない区間**(`derive_runs` が透塀との離れから決める従属値)を刷る。
    #    ⛔ 「回さないと決めた」ことが図と数のどちらにも出ないと、宣言だけの決めごとになる(規則19)。
    for r in d["runs"]:
        for q in r.get("skips") or []:
            note.append("『%s』は uv(%.3f, %.3f) を中心に **%.3f m を回さない** ── "
                        "他の囲いへ犬走り %.2f m より近く並走する区間【算出 — "
                        "`derive_runs` が輪郭と他の囲いの離れから決める従属値。⛔ 数で持たない】"
                        "【U 設計判断 — 図の姿としてそう決めた。⚠ 柵の存在自体が `U(設計値)` である"
                        "以上、切れ目も設計判断である(考証10巡目 軽微3)】"
                        % (r["name"], q[0], q[1], 2 * q[2] * ken, d["const"]["inubashiri"]))
    # ⛔ **`skips` の合計に頭打ちを置く**【検図12巡目 中2 → 2026-09-07】。
    #    ⚠ skip 規則には**上限も ⛔ で止まる条件も無かった**ので、他の囲いが寄れば任意の長さが
    #    〔記録〕1行だけで消える形だった。
    #    ⭐ **頭打ちは宣言の意味から出す。**囲いの切れ目には二種ある ──
    #    ① **口**(`gapFrom` で石段の幅・門口から従属する、**何を通すかという理由を持つ**切れ目)
    #    ② **skip**(相手の囲いが寄ったという**成り行き**で決まり、〔記録〕1行しか残らない切れ目)。
    #    ⛔ **理由を持たない切れ目が、理由を持つ切れ目より長い囲いは、もう宣言どおりの姿ではない。**
    #    ⛔ 現況の比(2.7%)からは決めていない ── 両辺とも算出値で、⛔ 数を持たない。
    #    ⛔ 両辺は**同じ物差し**(折れ線から実際に抜けた長さ)で測る(検図12巡目 低1 と同じ)。
    for r in d["runs"]:
        if not (r.get("skips")): continue
        lg = gap_ledger(r)
        if lg["skip が抜いた"] > lg["口が抜いた"] + 1e-9:
            bad.append("『%s』の**宣言していない切れ目(`skips`)の合計 %.3f m** が、"
                       "**宣言した口の合計 %.3f m** を超える ── 成り行きで消える長さが、"
                       "何を通すかという理由を持つ口より長い。⛔ この柵はもう宣言どおりの姿ではない"
                       % (r["name"], lg["skip が抜いた"] * ken, lg["口が抜いた"] * ken))
        note.append("『%s』の **`skips` の頭打ち** ── 宣言していない切れ目 %.3f m ／ "
                    "宣言した口 %.3f m(**この比が 1 を超えたら⛔**)／ 折れ線に対して %.2f%%"
                    "【算出 — ⛔ 両辺とも従属値。⛔ 現況の比を根拠に閾値を置いていない】"
                    % (r["name"], lg["skip が抜いた"] * ken, lg["口が抜いた"] * ken,
                       100.0 * lg["skip が抜いた"] / (lg["折れ線"] or 1.0)))
    lines, bands = _kakoi_items(d)
    got, corner, near = [], 0, []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            ni, si = lines[i]; nj, sj = lines[j]
            Li = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in si)
            Lj = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in sj)
            xs, tip, best = [], False, None
            ai = 0.0
            for a, b in si:
                La = math.hypot(b[0] - a[0], b[1] - a[1]); aj = 0.0
                for c, e in sj:
                    Lb = math.hypot(e[0] - c[0], e[1] - c[1])
                    r_ = _seg_cross(a, b, c, e)
                    if r_:
                        _x, t, u = r_
                        mid_i = KAKOI_END_KEN < ai + t * La < Li - KAKOI_END_KEN
                        mid_j = KAKOI_END_KEN < aj + u * Lb < Lj - KAKOI_END_KEN
                        (xs.append(_x) if (mid_i and mid_j) else None)
                        if not (mid_i and mid_j): tip = True
                    dd = _seg_seg_dist(a, b, c, e)
                    best = dd if best is None else min(best, dd)
                    aj += Lb
                ai += La
            key = "|".join(sorted((ni, nj)))
            if xs:
                got.append(key)
                if key not in ros:
                    bad.append("『%s』と『%s』が**平面で交差する**(交点 %s)── 二つの囲いが"
                               "交わる図は成立しない。⛔ 名簿 `kakoiCross.roster` に無い"
                               % (ni, nj, "／".join("uv(%.3f, %.3f)" % q for q in xs)))
                else:
                    note.append("『%s』×『%s』の**真の交差** %d 点(%s)── ⭕ 名簿ずみ"
                                "(→ `_pending`「%s」)【算出】"
                                % (ni, nj, len(xs), "／".join("uv(%.3f, %.3f)" % q for q in xs),
                                   ros[key].get("pending", "—")))
            elif tip:
                corner += 1
            elif best is not None and best < ins - 1e-9:
                got.append(key)
                if key not in ros:
                    bad.append("『%s』と『%s』の離れ %.3f m が犬走り %.2f m を割る — "
                               "二つの囲いの間に人の通れない溝が残る。⛔ 名簿に無い"
                               % (ni, nj, best * ken, d["const"]["inubashiri"]))
                else:
                    note.append("『%s』×『%s』の離れ %.3f m(犬走り %.2f m 未満)── ⭕ 名簿ずみ"
                                "(→ `_pending`「%s」)【算出】"
                                % (ni, nj, best * ken, d["const"]["inubashiri"],
                                   ros[key].get("pending", "—")))
            elif best is not None and best * ken < 0.60:
                near.append((ni, nj, best * ken))
    # ② 帯どうし(回廊の屋根 × 石段の踏面 ほか)── 矩形で測る
    for i in range(len(bands)):
        for j in range(i + 1, len(bands)):
            ni, si, hi = bands[i]; nj, sj, hj = bands[j]
            A, gapm = 0.0, None
            for Ra in _band_rects(si, hi):
                for Rb in _band_rects(sj, hj):
                    gp = obb_gap(Ra, Rb)
                    gapm = gp if gapm is None else min(gapm, gp)
                    if gp < 0: A += poly_area(_poly_clip(Ra, Rb))
            if A <= 1e-12: continue
            key = "|".join(sorted((ni, nj)))
            got.append(key)
            if key not in ros:
                bad.append("帯『%s』と『%s』が %.4f m² 重なる(食い込み %.3f m)── ⛔ 名簿に無い"
                           % (ni, nj, A * ken * ken, -gapm * ken))
            else:
                note.append("帯『%s』×『%s』の重なり %.4f m²(食い込み %.3f m)── ⭕ 名簿ずみ"
                            "(→ `_pending`「%s」)【算出】"
                            % (ni, nj, A * ken * ken, -gapm * ken, ros[key].get("pending", "—")))
    # ③ 線 × 帯(囲い・土留め × 回廊の屋根・石段の踏面)── ⛔ **積を黙って抜かない**
    #    【検図12巡目 低3 → 2026-09-07】。旧版は 線×線 と 帯×帯 だけを測り、**その積は誰も
    #    測っていなかった**(黙って抜けているのが規則19 の欠陥の形)。
    #    ⭕ **石段の側壁が自分の踏面の帯の縁の上に立つ 0.000 m の接触は設計上の姿**なので
    #    〔記録〕に数だけ刷る(⛔ 名簿で1件ずつ許さない — 名簿が接触の一覧に化ける)。
    lb_touch, lb_far = 0, []
    for ni, si in lines:
        for nj, sj, hj in bands:
            if ni.split(":", 1)[-1] == nj.split(":", 1)[-1]: continue   # run とその屋根は同じ物
            gp = _line_band_gap(si, _band_rects(sj, hj))
            if gp is None: continue
            key = "|".join(sorted((ni, nj)))
            if abs(gp) <= BAND_TOUCH_KEN:
                lb_touch += 1
                continue
            if gp >= ins - 1e-9:
                if gp * ken < 0.60: lb_far.append((ni, nj, gp * ken))
                continue
            got.append(key)
            kd = "食い込み %.3f m" % (-gp * ken) if gp < 0 else "離れ %.3f m" % (gp * ken)
            if key not in ros:
                bad.append("線『%s』と帯『%s』の%s ── 帯は幅を持つので芯線では測れない。"
                           "⛔ 名簿 `kakoiCross.roster` に無い" % (ni, nj, kd))
            else:
                note.append("線『%s』×帯『%s』の%s(犬走り %.2f m 未満)── ⭕ 名簿ずみ"
                            "(→ `_pending`「%s」)【算出】"
                            % (ni, nj, kd, d["const"]["inubashiri"], ros[key].get("pending", "—")))
    # ④ 囲い・土留めが棟の矩形を貫いていないか(⛔ 名簿を置かない — 貫いてよい理由が無い)
    npier = 0
    for m in d["munes"]:
        R = [(m["u0"], m["v0"]), (m["u0"] + m["du"], m["v0"]),
             (m["u0"] + m["du"], m["v0"] + m["dv"]), (m["u0"], m["v0"] + m["dv"])]
        for nm, sgs in lines:
            for a, b in sgs:
                if any(_seg_cross(a, b, R[k], R[(k + 1) % 4]) for k in range(4)) \
                   or in_poly(a, R) or in_poly(b, R):
                    npier += 1
                    bad.append("囲い『%s』が棟『%s』の平面を貫く" % (nm, m["name"]))
                    break
    bad += roster_guard([q for q in ros], sorted(set(got)),
                        "許した交差・近接の名簿", "`kakoiCross.roster`")
    tal = {}
    for k in set(got):
        kd = ros[k]["kind"] if k in ros else "⛔ 名簿の外"
        tal[kd] = tal.get(kd, 0) + 1
    note.append("囲い %d 本・土留め %d 本の**総当たり** %d 組 ＋ 帯 %d 本の総当たり %d 組 "
                "＋ **線 × 帯 %d 組**(検図12巡目 低3 で足した)── "
                "真の交差 %d 組 ／ 帯の重なり %d 組 ／ 犬走り %.2f m 未満 %d 組 ／ "
                "**線 × 帯 の食い込み %d 組・離れ %d 組**(合わせて名簿 %d 件・"
                "⛔ 名簿の外は 0 でなければ組めない)／ 隅の突き付け(端点で接する)%d 組 ／ "
                "**線が帯の縁に接する(0.000 m)%d 組 — 石段の側壁が自分の踏面の帯の縁に立つ"
                "設計上の姿** ／ 囲い×棟の貫通 %d 件"
                "【算出 — 交点が端か途中かで分ける。物差しは %.2f 間・帯の接触は %.3f 間】"
                % (len(d["runs"]), len(d["terraceWalls"]), len(lines) * (len(lines) - 1) // 2,
                   len(bands), len(bands) * (len(bands) - 1) // 2, len(lines) * len(bands),
                   tal.get("交差", 0), tal.get("帯の重なり", 0), d["const"]["inubashiri"],
                   tal.get("離れ", 0), tal.get("線と帯の重なり", 0), tal.get("線と帯の離れ", 0),
                   len(ros), corner, lb_touch, npier, KAKOI_END_KEN, BAND_TOUCH_KEN))
    for ni, nj, dd in sorted(lb_far, key=lambda q: q[2]):
        note.append("線『%s』×帯『%s』の離れ %.3f m(⭕ 犬走り %.2f m 以上)【算出】"
                    % (ni, nj, dd, d["const"]["inubashiri"]))
    if tal.get("⛔ 名簿の外"):
        note.append("**名簿の外** %d 組 ── ⛔ 上の⛔で止まっている【算出】" % tal["⛔ 名簿の外"])
    for ni, nj, dd in sorted(near, key=lambda q: q[2]):
        note.append("『%s』×『%s』の離れ %.3f m(⭕ 犬走り %.2f m 以上)【算出】"
                    % (ni, nj, dd, d["const"]["inubashiri"]))
    return bad, note


def _poly_clip(sub, clip):
    """凸多角形どうしの共通部分(Sutherland–Hodgman)。⛔ 面積のためだけに使う。"""
    def ccw(P):
        s2 = sum((P[(i + 1) % len(P)][0] - P[i][0]) * (P[(i + 1) % len(P)][1] + P[i][1])
                 for i in range(len(P)))
        return P if s2 < 0 else P[::-1]
    out, clip = ccw(list(sub)), ccw(list(clip))
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        if not out: return []
        inp, out = out, []
        side = lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        for j in range(len(inp)):
            c, e = inp[j], inp[(j + 1) % len(inp)]
            sc, se = side(c), side(e)
            if sc >= 0: out.append(c)
            if (sc >= 0) != (se >= 0):
                t = sc / (sc - se)
                out.append((c[0] + (e[0] - c[0]) * t, c[1] + (e[1] - c[1]) * t))
    return out


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
    # ⚠ **測るのは平側(西・東)の二辺だけ**【庭方6巡目 低1 → 2026-09-07】── 妻側(南北)の軒先は
    #    `hashiraPitchKen`/2 + `hafuDeKen` で石敷の半幅 `ishikiKen`/2 より内に入る。
    #    ⭕ **切妻は妻側に雨落ちが無い**ので、石敷が破風より出るのは屋根の作法として正しい。
    #    ⛔ 妻側を測る検査を足さない。⛔ 黙って抜かない — 下の〔記録〕が毎回そう名乗る。
    note.append("**軒先 ≡ 石敷** を測るのは**平側(西・東)の二辺だけ** ── 妻側(南北)は "
                "軒先の半幅 %.3f m(`hashiraPitchKen`/2 + `hafuDeKen`)＜ 石敷の半幅 %.3f m"
                "(`ishikiKen`/2)で %.3f m 内に入るが、⭕ **切妻は妻側に雨落ちが無い**ので"
                "石敷が破風より出るのは正しい【算出 — 庭方6巡目 低1】"
                % ((d["ido"]["hashiraPitchKen"] / 2.0 + d["ido"]["hafuDeKen"]) * ken,
                   d["ido"]["ishikiKen"] / 2.0 * ken,
                   (d["ido"]["ishikiKen"] / 2.0
                    - (d["ido"]["hashiraPitchKen"] / 2.0 + d["ido"]["hafuDeKen"])) * ken))
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
    """木戸の開口が**辺の中に納まっているか**(端からはみ出さず・他の開口と重ならないか)、
    および **裏 `insideKen` へ入る樹冠と、その所の枝下**。

    ⚠ 2026-09-06 検図4巡目 中4: 島の木戸の芯が柱の割付の柱に乗っていた。
    ⭐ 2026-09-06c 裁定4 — 木戸は辺を割るようになった(`tamagaki_gaps`)ので、
    **柱に乗るか**ではなく **辺の端・井戸の口と食い合わないか**を測る。
    残った一枚が垣として成り立つかは検査『玉垣の一枚の内法』が受け持つ。
    ⭐ **2026-09-07 庭方4巡目 低2 — `insideKen` の射程を樹冠まで広げた。**
    旧版の宣言は『低木を植えない奥行』だけで**樹冠には効いておらず、検査も測っていなかった**
    (規則19 の欠陥の形)。⛔ 樹冠も裏へ入れない、**ただし枝下が
    `plantRule.crownRule.chuboku.edaShitaMinM` 以上なら可**(頭上を抜けるので出入りを妨げない)。
    ⚠ **測り方は「樹冠の円 ∩ 裏の矩形」**。⛔ u の張り出しだけで測らない — それでは
    円が矩形へ届かない木(門被りのクロマツ)まで数えてしまう。戻り値 (⛔止める, 〔記録〕)。
    """
    bad, note = [], []
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
    # ⭐ **裏 `insideKen` へ入る樹冠と枝下**【低2 庭方 2026-09-07】
    cr = d["planting"]["plantRule"].get("crownRule") or {}
    lo_ch = (cr.get("chuboku") or {}).get("edaShitaMinM")
    lo_tk = (cr.get("takagi") or {}).get("edaShitaMinM")
    ken0 = d["const"]["ken"]
    for gd in d["gardens"]:
        tg = gd.get("tamagaki") or {}
        kd = tg.get("kido")
        if not kd: continue
        # ⛔ **矩形を二度作らない**(規則4)── 低木を空ける矩形 `kido_rect` がそのまま射程の面
        R = kido_rect(gd, ken0)
        if R is None or kd.get("insideKen") is None: continue
        hit = 0
        for sg in gd.get("singles", []):
            r = single_crown(d, sg)
            if r is None: continue
            dd = 0.0 if in_poly(tuple(sg["uv"]), R) else \
                min(_pt_seg(tuple(sg["uv"]), R[i], R[(i + 1) % 4]) for i in range(4))
            if dd >= r - 1e-9: continue
            hit += 1
            eda, src = sg.get("edaShita"), "宣言"
            if eda is None:
                eda = lo_ch if sg.get("layer") == "中木" else lo_tk
                src = "仕立ての条件(`crownRule`)"
            if lo_ch is None or eda is None:
                bad.append("%s の樹冠が%sの裏(`insideKen` %g 間)へ %.3f m 入るが、枝下の条件"
                           "(`plantRule.crownRule.chuboku.edaShitaMinM`)が引けない — "
                           "宣言の無い条件は検査にならない(規則19)"
                           % (sg["name"], kd["name"], kd["insideKen"], (r - dd) * ken0))
            elif eda < lo_ch - 1e-9:
                bad.append("%s の樹冠が%sの裏(`insideKen` %g 間)へ %.3f m 入り、枝下 %.2f m が"
                           "下限 %.2f m を割る — ⛔ 木戸の出入りを樹冠が塞ぐ【低2 庭方 2026-09-07】"
                           % (sg["name"], kd["name"], kd["insideKen"], (r - dd) * ken0, eda, lo_ch))
            else:
                note.append("%s の樹冠が%sの裏(`insideKen` %g 間)へ **%.3f m 入る**(樹冠の半径 %.3f m)"
                            "── ⭕ **可** 枝下 %.2f m【%s】≥ 下限 %.2f m で頭上を抜ける"
                            "【算出 — 測り方は樹冠の円 ∩ 裏の矩形。⛔ u の張り出しだけで測らない】"
                            % (sg["name"], kd["name"], kd["insideKen"], (r - dd) * ken0,
                               r * ken0, eda, src, lo_ch))
        note.append("%s の%sの裏(`insideKen` %g 間)へ樹冠が入る一本立ち %d / %d 本"
                    "(⛔ 低木だけでなく樹冠にも効く射程。枝下が下限以上なら可)【算出】"
                    % (gd["name"], kd["name"], kd["insideKen"], hit, len(gd.get("singles", []))))
    return bad, note


def mitsuke_fill_check(d):
    """**腰高の柵の見付けの充実率**【指5 庭方 2026-09-09 十八巡目】。

    充実率 = (柱 + 貫 + 立子 の見付けの投影面積)÷(延長 × 丈 `hM`)。⭕ **透けがその残り**で、
    『腰高で透ける柵だから参道の両側の社叢が切れずに続いて見える』(`sando.roadside.banRule`)
    という景の理由の**測れる形**である。
    ⛔ **貫の見付は当図にも目録にも宣言が無い**ので、今日刷れるのは**柱と立子だけの下限値**で
      ある。⛔ 下限値を『充実率』と名乗って通さない ── 毎回『貫を数えていない』と名乗る。
    ⚠ 一枚(柱と柱の間)で測る ── 延長は約分で消えるので、⛔ 実延長は要らない。
    """
    bad, note = [], []
    for gd in d["gardens"]:
        tg = gd.get("tamagaki")
        if not tg or tg.get("mitsukeFillMaxPct") is None: continue
        ken = d["const"]["ken"]
        pitch = float(tg["postPitchKen"]) * ken
        hM = float(tg["hM"])
        pd, td, tp = tg["postDiaM"], tg["tatekoDiaM"], tg["tatekoPitchM"]
        uchi = pitch - pd
        n = int(math.floor(uchi / tp + 1e-9))
        area = pitch * hM
        fill = (pd * hM + n * td * hM) / area * 100.0
        lim = float(tg["mitsukeFillMaxPct"])
        nuki = tg.get("nukiMitsukeM")
        if nuki:
            fill += (float(tg.get("nuki") or 0) * float(nuki) * pitch) / area * 100.0
        txt = ("腰高の柵の**見付けの充実率 %.1f%%**(透け %.1f%%)／ 受入値 **%g%% 以下** ── "
               "一枚 %.3f m × 丈 %.2f m に 柱 1 本(径 %g m)+ 立子 %d 本(径 %g m・"
               "刻み %g m)%s【算出 — 指5 庭方 2026-09-09 十八巡目。⛔ 数を json に書かない】"
               % (fill, 100.0 - fill, lim, pitch, hM, pd, n, td, tp,
                  ("+ 貫 %d 段(見付 %g m)" % (tg.get("nuki") or 0, nuki)) if nuki else
                  "。⚠ **貫 %d 段は数えていない**(見付が当図にも目録にも無い)⇒ これは"
                  "**下限値**である → `_pending`「腰高の柵の貫の見付が宣言も目録も持たない」"
                  % (tg.get("nuki") or 0)))
        if fill > lim + 1e-9:
            bad.append("**" + txt + " ⛔ 受入値を超える** — ⛔ 立子を細かくして塞がない"
                       "(透けが景の理由である)")
        else:
            note.append(txt)
    if not note and not bad:
        bad.append("`tamagaki.mitsukeFillMaxPct`(見付けの充実率の上限)を宣言した柵が一つも無い — "
                   "⛔ 0 件は合格ではなく未測定(指5 庭方 2026-09-09・規則19)")
    return bad, note


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
    # ⭐ **合格の側も一行刷る**【B-5 検図22巡目 → 2026-09-09 十九巡目】
    note = ["面の天端の出所 ⭕ ── 天端を持つ面 %d(`planes[].y` の二重持ち 0 件)／ "
            "天端を持つ terrace %d はすべてどれかの面に属し、その面は `planeDevRoster` と "
            "`devEnvelopeM` を持つ【算出 — ⛔ 0 件は合格ではなく未測定なので、"
            "**何を数えたか**を刷る】"
            % (len([q for q in d["planes"] if plane_y(d, q) is not None]),
               len([q for q in d["terraces"] if q.get("y") is not None]))]
    for pl in d["planes"]:
        if plane_y(d, pl) is None: continue
        if pl.get("devEnvelopeM") is None: continue
        note.append("面『%s』── 天端 %.2f m(`terraces[].y`)／ Δ の名簿 %d 件 ／ "
                    "**Δ の包絡 ±%.2f m**【算出】"
                    % (pl["name"], plane_y(d, pl), len(pl.get("planeDevRoster") or []),
                       pl["devEnvelopeM"]))
    return bad, note


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
        # ⭐⭐ **裁定の射程を数で囲う**【B-2 検図22巡目 → 2026-09-09 十九巡目】── 裁定
        #    (2026-09-07 案A)は『規則3(±0.5 m)を山上の社地には当てない』であって
        #    **『上限なし』ではない**。⚠ 旧図の⛔は `roster_guard`(名簿)からしか出ず、
        #    ⛔ **Δ の大きさでは構造上⛔にできなかった** ── 破壊試験で平場の天端を +5.7 m
        #    盛っても Δ の側は一行も⛔にならなかった(⛔ 0 件は合格ではなく未測定・規則19)。
        env = pl.get("devEnvelopeM")
        if env is None:
            bad.append("面『%s』が **`devEnvelopeM`(Δ の包絡)を宣言していない** — ⛔ 宣言が"
                       "無ければ Δ はどれだけ大きくても⛔にできず、裁定(2026-09-07 案A)の"
                       "射程が数で囲われていない(B-2 検図22巡目)" % pl["name"])
        got, over, lines, outenv = [], [], [], []
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
            amax = max(abs(min(ds)), abs(max(ds)))
            ex = amax > lim + 1e-9
            if ex: over.append(nm)
            oe = (env is not None and amax > env + 1e-9)
            if oe: outenv.append((nm, amax))
            lines.append("『%s』%s の Δ(天端 %.2f − 造成前の地形)= %+.2f 〜 %+.2f m"
                        "(正=盛土/負=切土。目安 ±%.2f m ／ 包絡 ±%s m)%s%s【算出 P】"
                        % (pl["name"], nm, top, min(ds), max(ds), lim,
                           ("%.2f" % env) if env is not None else "—(**未宣言**)",
                           "　⚠ **目安を超える**" if ex else "",
                           "　⛔ **包絡を超える**" if oe else ""))
        if outenv:
            bad.append("面『%s』── **Δ が包絡 `devEnvelopeM` %.2f m を超える %d 件** ── %s。"
                       "⛔ 数を緩めて黙らせない ── 面の天端か棟の位置を**普請奉行が裁く**"
                       "(⛔ 上限を上げて通さない。B-2 検図22巡目)"
                       % (pl["name"], env, len(outenv),
                          "・".join("%s %.2f m" % q for q in sorted(outenv, key=lambda r: -r[1]))))
        bad += roster_guard(pl.get("planeDevRoster"), got, "『%s』の Δ を測る名簿" % pl["name"],
                            "`planes[%s].planeDevRoster`" % pl["name"])
        note.append("『%s』(天端 %.2f)に載って Δ を測った物 %d 件(門 %d・棟 %d・井戸屋形 %s)"
                    "── **目安 ±%.2f m を超えるもの %d 件**%s ／ **包絡 ±%s m を超えるもの %d 件**"
                    "【算出 — 包絡は裁定時(2026-09-07)の実測そのもの。⛔ 緩めない】"
                    % (pl["name"], top, len(got),
                       len([q for q in d["gates"] if q["name"].split("(")[0] in got]),
                       len([q for q in d["munes"] if q["name"] in got]),
                       "有" if "井戸屋形の石敷" in got else "無", lim, len(over),
                       (" — " + "・".join(over)) if over else "",
                       ("%.2f" % env) if env is not None else "—(**未宣言**)", len(outenv)))
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
            # ⭐ **樹冠は傾いた芯で測る**(2026-09-08 中3)── 門被りの松は門へ傾けるので、
            #    樹冠は参道の芯の側へ寄る。⛔ 幹の芯のままで測ると甘い数が出る。
            cu, cv = single_crown_center(d, sg)
            lean = "" if abs(cv - v) < 1e-9 else \
                (" ／ 傾き %s° で樹冠の芯が %.3f m 寄っている" %
                 (_rng(sg.get("leanDeg")), math.hypot(cu - u, cv - v) * ken))
            near = (cv - r) if v > 0 else (cv + r)
            if (v > 0 and near < 0) or (v < 0 and near > 0):
                bad.append("『%s』の樹冠の%sの端 v %+.4f 間が参道の芯を越える(幹 v %+.3f・樹冠 %.2f m%s)"
                           % (sg["name"], "南" if v > 0 else "北", near, v, r * 2.0 * ken, lean))
            else:
                note.append("『%s』の樹冠の%sの端 v %+.4f 間(= 参道の芯から %.3f m %s%s)【算出】"
                            % (sg["name"], "南" if v > 0 else "北", near, abs(near) * ken,
                               "北" if v > 0 else "南", lean))
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
    # ⭐ **千鳥に据える**【B-5 庭方 2026-09-08 十六巡目】── 一列おきに芯々の**半分**だけ u をずらす。
    #    ⛔ 面も芯々も変えない(⛔ ずらし量を json に持たない — `spacingM` の半分)。
    #    ⚠ 旧式は u 3 列 × v 1.2 m ちょうど刻みの**直交格子**で、⛔ 図の中で唯一、目に格子と映った。
    stag = st / 2.0 if sh.get("stagger") else 0.0
    # ⭐ **正三角の格子**【中7 庭方 2026-09-09 十七巡目】── ⛔ 行の間隔を数で持たない
    vst = (st * math.sqrt(3.0) / 2.0) if "正三角" in (sh.get("lattice") or "") else None
    scan = ((lambda Q: _stagger_scan(Q, st, stag, vst)) if (stag or vst)
            else (lambda Q: poly_scan(Q, st)))
    if B:
        # ⭐ **輪郭から樹冠半径以上**(2026-09-06 検図5巡目 中12 — 帯が v3.5 で折れるのを枠が見ておらず、
        #    低木1本が袖塀 `Ita_Niou_N` へ 0.546m めり込んでいた)
        src = (q for q in scan(B) if shrub_ok(gd, q))
    else:
        ins = st / 2.0
        src = (q for q in scan(P)
               if min(_pt_seg(q, P[i], P[(i + 1) % len(P)]) for i in range(len(P))) >= ins)
    return [q for q in src if not (kr and in_poly(q, kr))]


def _stagger_scan(P, step, shift, vstep=None):
    """**千鳥の走査** ── v の一列おきに u を `shift` だけずらす(⛔ 面も芯々も変えない)。

    ⭐ **行の間隔 `vstep`**【中7 庭方 2026-09-09 十七巡目】── 宣言が `正三角` なら
      芯々 × √3/2(⛔ 数を json に持たない)。⚠ 旧式は行の間隔も芯々のままだったので、
      斜めの芯々が芯々の 1.12 倍あり(√(1 + 1/4))、**塊にならなかった**。
    """
    us = [q[0] for q in P]; vs = [q[1] for q in P]
    vs9 = vstep or step
    v = min(vs) + vs9 / 2.0
    row = 0
    while v < max(vs):
        u = min(us) + step / 2.0 + (shift if row % 2 else 0.0)
        while u < max(us):
            if in_poly((u, v), P): yield (u, v)
            u += step
        v += vs9
        row += 1


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
    """一本立ちの丈・部材・樹冠の刷り方 ── **仮値と従属倍率を隠さない**(2026-09-07 中1・裁き2)。

    ⭐ 2026-09-07 八巡目 中1 ── **宣言が無いことを空欄で表さない**。丈も層も無い一本立ちは
    「—(**宣言が無い**)」と刷って検査へ回す(⛔ 何も刷らないと『測れている』と読める)。
    """
    out = (" 丈%.1fm" % sg["h"]) if sg.get("h") else " 丈—(**宣言が無い**)"
    lay = sg.get("layer")
    if lay is None:
        return out + "・樹冠—(**層の宣言が無い**)"
    pf = single_prefab(d, sg)
    if pf: out += "・部材『%s』" % pf
    if sg.get("crown"):
        out += "・樹冠%.2fm%s" % (sg["crown"],
                                 "<b>(⚠ 部材未計測の仮値)</b>" if sg.get("crownProvisional") else "")
        return out
    # ⛔ **層を問わず樹冠を刷る**(2026-09-07)── 旧式は中木しか刷らず、落葉高木が
    #    仮値 `crown` を外した日に**樹冠が図から消えた**(規則19: 図に出ない値は検められない)。
    r = single_crown(d, sg)
    if r is None:
        return out + "・樹冠—(**部材が目録に無い**)"
    kd = _SG_LAYER[lay][1]
    xz = crown_scale_xz(d, kd, pf, sg.get("h"), iso=True)
    out += ("・樹冠%.2fm【従属 部材の素の樹冠 × `scaleXZ`】" % (r * 2.0 * d["const"]["ken"]))
    # ⭕ **一本立ちは孤立木なので `isolatedXZ`**(2026-09-08 十六巡目 中6・庭方)。
    #    ⛔ 松はこの規約の外(範囲がもともと部材寄り)なので、そう刷り分ける。
    out += (("・scaleXZ %.3f【従属 — %s】"
             % (xz, "松は `scaleRule.matsu.scaleXZ` の中央(孤立木の規約の外)"
                if kd == "matsu" else "孤立木 `isolatedXZ`")) if xz else "")
    q = pick_variant(d, (single_parts(d, sg) or [{}])[0], sg.get("h"))
    if q and q[3]: out += "・scaleY %.3f【従属】" % q[3]
    return out


def sankaku_elev_rows(d, g):
    """**前庭の立面の三尊** ── 見所からの梢の仰角【A-5 庭方 2026-09-09 十九巡目】。

    ⛔ 数を json に持たない ── 三点の (u,v)・丈・造成後の地盤と、見所の眼高からの従属値。
    戻り (見所の名, 見所, 眼高, 眼高の出所, [(役, 名, 距離, 梢の標高, 仰角, 丈)], 引けない点)。
    """
    sk, _pts, _sides = sankaku_rows(d)
    if not sk: return (None, None, None, None, [], [])
    vnm = sk.get("from")
    vp = ([q for q in d.get("viewpoints", []) if q.get("name") == vnm] or [None])[0]
    if vp is None: return (vnm, None, None, None, [], [])
    eye, esrc = viewpoint_eye(d, g, vp)
    ken = d["const"]["ken"]
    idx = {}
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []): idx[sg["name"]] = sg
    rows, miss = [], []
    for q in sk["pts"]:
        sg = idx.get(q["name"])
        if sg is None or sg.get("h") is None or not sg.get("uv"):
            miss.append((q["name"], q.get("yaku") or "—")); continue
        u9, v9 = sg["uv"]
        x9, z9 = g.W(u9, v9)
        gy = _design_y_cold(d, g, x9, z9)
        if gy is None: gy = dem_h(x9, z9) or 0.0
        L9 = math.hypot(u9 - vp["uv"][0], v9 - vp["uv"][1]) * ken
        top = gy + sg["h"]
        ang = math.degrees(math.atan2(top - eye, L9)) if L9 > 1e-9 else 90.0
        rows.append((q.get("yaku") or "—", q["name"], L9, top, ang, sg["h"]))
    return (vnm, vp, eye, esrc, rows, miss)


def sankaku_check(d, g):
    """**前庭の立面の三尊**が立面として成り立っているか【A-5 庭方 2026-09-09 十九巡目】。

    ⛔⛔ **『平面の不等辺三角形』では測らない** ── 帯の幅が高木の樹冠より狭いので、
      平面の三角形は**幾何として作れない**(実測で三点は面積も高さも潰れて実質一直線)。
      ⛔ 帯の外へ三点目を立て直さない(それは帯の意味を壊す)。
    ⭕ **物差しは `sankaku.from` の見所からの梢の仰角** ── 三つとも異なり、最も近い二つの差が
      `minDiffDeg` 以上あること。⛔ 平面の面積・三辺の長さでは測らない。
    """
    bad, note = [], []
    sk, pts, sides = sankaku_rows(d)
    if not sk: return bad, note
    lim = sk.get("minDiffDeg")
    if lim is None:
        bad.append("`gardens[].sankaku.minDiffDeg`(梢の仰角の、最も近い二つの差の下限)の"
                   "宣言が無い — 宣言の無い縛りは必ず破られる(規則19)")
        return bad, note
    vnm, vp, eye, esrc, rows, miss = sankaku_elev_rows(d, g)
    if vp is None:
        bad.append("`gardens[].sankaku.from`『%s』の見所が `viewpoints` に無い — "
                   "**死んだポインタ**(⛔ 立面の受入値が測れない)" % vnm)
        return bad, note
    for nm9, yk9 in miss:
        bad.append("立面の三尊の『%s』(役 %s)の位置か丈が引けない — ⛔ 受入値を測れない"
                   % (nm9, yk9))
    if len(rows) < 3:
        bad.append("立面の三尊 ── **%d 点しか引けない**(三点が要る)" % len(rows))
        return bad, note
    A = sorted(r[4] for r in rows)
    dmin = min(A[1] - A[0], A[2] - A[1])
    if dmin < lim - 1e-9:
        bad.append("立面の三尊 ── **梢の仰角の最も近い二つの差** %.2f° が下限 %.2f° を割る"
                   "(⛔ 三つの頭が一つの高さに並んで見える)。見所 %s(眼高 %.2f m)"
                   % (dmin, lim, vnm, eye))
    for yk, nm9, L9, top, ang, h9 in rows:
        note.append("立面の三尊 **%s = %s** ── %s から %.2f m ／ 丈 %.1f m ／ 梢の標高 %.2f m ／ "
                    "**仰角 %.2f°**【算出 — ⛔ 数を json にも文章にも写さない】"
                    % (yk, nm9, vnm, L9, h9, top, ang))
    note.append("立面の三尊 ── 仰角 %s ／ **最も近い二つの差 %.2f°**(下限 %.2f°)／ "
                "見所 %s 眼高 %.2f m(%s)【算出 — A-5 庭方 2026-09-09 十九巡目。"
                "⛔ 平面の面積・三辺の長さでは測らない】"
                % ("・".join("%.2f°" % q for q in A), dmin, lim, vnm, eye, esrc))
    return bad, note


def sekitoro_rows(d):
    """石灯籠の**隣どうしの芯々**[間] ── ⛔ 等間隔にしない(2026-09-07 低1)。従属値。"""
    for pr in d["props"]:
        if pr["name"] != "石灯籠" or not pr.get("uv"): continue
        Q = sorted(pr["uv"], key=lambda q: q[0])
        return [math.hypot(Q[i + 1][0] - Q[i][0], Q[i + 1][1] - Q[i][1])
                for i in range(len(Q) - 1)]
    return []


def route_narrowest(d, rt, pts, terrace=None, step=0.05):
    """動線の**最狭部**の路面幅[m]と、そこを決めている物の名。⛔ 数で持たない(門口からの従属値)。

    ⭐ 裁き2(庭方 2026-09-07)── **固定物**が通行帯へ出てよいかは「掛かるか」ではなく
    **「その動線の最狭部より狭くしないか」**で測る。通行帯は動線の帯であって物理の縁ではない。
    """
    best = None
    for i in range(len(pts) - 1):
        a, c = pts[i], pts[i + 1]
        L = math.hypot(c[0] - a[0], c[1] - a[1])
        n = max(2, int(L / step))
        for j in range(n + 1):
            t = j / float(n)
            q = (a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t)
            w = route_w(d, rt, terrace, at=q)
            if best is None or w < best[0] - 1e-12:
                gt = gate_at(d, q)
                best = (w, ("門『%s』の門口" % gt["name"]) if gt else "路面(`routes[].w`)")
    return best


def _obj_vs_route(Q, pts, hw, ken):
    """固定物の外形 `Q`[uv] が動線の通行帯(芯線 `pts`・半幅 `hw`[m])をどれだけ塞ぐか。

    戻り (`dm`, `eff`)[m]。
    ・`dm` = **物と芯線の距離。⛔ 跨いだら負**(跨いだ側の食い込みの深さ)
    ・`eff` = **残る有効幅** = 芯線の左右に残る帯のうち**広いほう**

    ⚠ **2026-09-07 検図11巡目 中2 で入れ替えた物差し。**旧式は `dm` を「外形の4隅から芯線までの
    **最小距離**」で採っていたので、⛔ **物が芯線を跨いだ瞬間に `dm` がまた増え、有効幅が
    大きく出た**(破壊試験で台座を芯へ載せても 3.0 m 角にしても一本も鳴らなかった)。
    ⛔ また `eff = w −(片側の食い込み)` も誤り — 物は**通り抜けられない**ので、残るのは
    塞がれた側を除いた**片側の帯**であって、両側の合計ではない。
    """
    dm, eff = None, None
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz)
        if L < 1e-12: continue
        ux, uz = dx / L, dz / L
        ts = [((q[0] - a[0]) * ux + (q[1] - a[1]) * uz) for q in Q]      # 芯線に沿う位置
        ss = [(-(q[0] - a[0]) * uz + (q[1] - a[1]) * ux) for q in Q]     # 芯線からの符号つき離れ
        if max(ts) < 0.0 or min(ts) > L: continue                        # 区間の外(縦に外れる)
        s0, s1 = min(ss) * ken, max(ss) * ken
        d_ = s0 if s0 >= 0 else (-s1 if s1 <= 0 else -max(-s0, s1))      # ⛔ 跨いだら負
        e_ = max(min(2 * hw, s0 + hw), min(2 * hw, hw - s1), 0.0)        # 残る広いほうの帯
        if dm is None or d_ < dm: dm = d_
        if eff is None or e_ < eff: eff = e_
    if dm is None: return (hw, 2 * hw)
    return (dm, eff)


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
                w = route_w(d, rt, te)
                hw = w / 2.0
                dm, eff = _obj_vs_route(Q, pts, hw, ken)
                if dm >= hw: continue
                # ⭕ **裁き2(庭方 2026-09-07)— 据置。物差しは「最狭部より狭くしないか」**。
                #   ⛔ 石を動かして数字を合わせに行かない(数と一列は【S】)。
                nw, nwnm = route_narrowest(d, rt, pts, te)
                if eff < nw - 1e-9:
                    bad.append("『%s』の台座が動線『%s』を**最狭部より狭くする** — 残る有効幅 "
                               "%.3f m < 最狭部 %.3f m(%s)。⛔ 通行帯へ出ること自体ではなく"
                               "**律速になること**を止める【裁き2 庭方 2026-09-07 の物差し】"
                               % (nm, rt["name"], eff, nw, nwnm))
                else:
                    note.append("『%s』の台座が動線『%s』の**通行帯へ %.3f m 出る**"
                                "(外形の隅 → 芯 %.3f m ／ 通行帯の半幅 %.3f m)── ⭕ **据置**"
                                "【裁き2 庭方 2026-09-07】: 通行帯は動線の帯であって物理の縁ではないので、"
                                "**固定物**は『掛かるか』でなく**『その動線の最狭部より狭くしないか』**で測る。"
                                "残る有効幅 %.3f m ＞ 最狭部 %.3f m(%s)・余裕 %+.3f m【算出】"
                                % (nm, rt["name"], hw - dm, dm, hw, eff, nw, nwnm, eff - nw))
    # ⛔ **一般化しない**【裁き2 庭方 2026-09-07】── **可動の物と固定の物で物差しが違う**。
    #    どちらも現況で成り立つことを、それぞれの実測から刷る(⛔ 言葉だけで宣言しない)。
    if g is not None:
        _vm, yo = zentei_yochi(d, g)
        lim = yo[0][2] if len(yo) > 1 else None           # 通行帯の西縁
        mg = [(lim - east) * d["const"]["ken"]
              for _l, _u, _v, _y, _bk, east, _pv in endai_rows(d)] if lim is not None else []
        if mg:
            note.append("⛔ **一般化しない** — **可動の物**(縁台(床几) %d 基)は『掛からないこと』で測り"
                        "最小の余裕 %+.3f m、**固定の物**(石灯籠)は『その動線の最狭部より狭くしないこと』"
                        "で測る。**物差しが違うのは退けられるかどうかが違うから**で、"
                        "⭕ 両方とも現況で成り立つ【算出 — 裁き2 庭方 2026-09-07】" % (len(mg), min(mg)))
    return bad, note


# 石灯籠の芯々の振れの下限[間](**検査の物差しであって設計値ではない**ので json に置かない)。
# ⭐ 2026-09-07 庭方3巡目 低1 — 0.2〜0.4 間の揺らぎを与えるという裁きの下側を物差しに採る。
SEKITORO_JITTER_MIN_KEN = 0.2


def cluster_boxes(c):
    """塊の箱(uv の [u0,v0,u1,v1])。`box` 単数と `boxes` 複数の両方に対応。"""
    if c.get("boxes"): return [tuple(q) for q in c["boxes"]]
    if c.get("box"):   return [tuple(c["box"])]
    return []


def cluster_polys(c):
    """塊の**輪郭**(uv の多角形の列)。⭐ 2026-09-08 十六巡目 C-1 で起こした。

    ⛔ **軸平行の箱で代表させない** ── 参道の林縁は『高木の縁の線に沿う平行四辺形』で、
    箱で囲むと幅が 9.1 間になって林縁でなくなる(**焼き出しが `unresolved` になった真因**)。
    `poly`(`derive_clusters` が線から起こす)があればそれ、無ければ箱の四隅。
    """
    if c.get("poly"): return [[(q[0], q[1]) for q in c["poly"]]]
    return [[(u0, v0), (u1, v0), (u1, v1), (u0, v1)] for u0, v0, u1, v1 in cluster_boxes(c)]


def cluster_spacing(d, c):
    """塊の中の**芯々**[間]。`spacing` があればそれ、無ければ `spacingFrom` の従属値。

    ⛔ 数を二重に持たない(規則4)。⭐ **2026-09-09 十八巡目に `spacingFrom`
    (`takagiEdgeLine.firstRowSpacing` の下端)の道を落とした**【指4 庭方】── 参道の林縁は
    一列でなくなり、芯々の正典は `groups` の `groupSpacingKen` / `groupGapKen` になった。
    """
    if c.get("spacing"): return float(c["spacing"])
    return None


def cluster_n(c):
    """塊の本数。範囲 [lo,hi] で書かれていれば中央を採る。

    ⭐ **`n` が無ければ `mix` の割り前の和**(2026-09-08)── ⛔ 同じ本数を `n` と `mix` の
    二箇所に持たない(規則4)。⚠ `mix` を持つ塊は `mix` が正典。
    """
    n = c.get("n")
    if isinstance(n, (list, tuple)): return sum(n) / 2.0
    if n is None and c.get("mix"): return float(sum(q[1] for q in cluster_mix(c)))
    return float(n or 0)


def cluster_label(c):
    n = c.get("n")
    if isinstance(n, (list, tuple)): return "%s %d〜%d本" % (c["name"], n[0], n[1])
    return "%s %d本" % (c["name"], int(round(cluster_n(c))))


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


def sando_suritsuke_check(d):
    """参道の縦断の**局所段差**が摺り付けで吸収できる範囲に収まっているか【考証8巡目 低10 → 2026-09-07】。

    ⭐ **なぜ要るか。** 2026-09-07 のユーザー裁定3は「参道の急な区間に**段は入れない** ／
    局所の起伏は**路面の摺り付け ±0.3m 以内**で吸収する」だった。図は最大勾配(2m/5m/20m 窓)を
    刷るが、**摺り付け量そのもの**はどこにも出ていなかった — 裁定の前提を支える量が
    **どの目にも入らない**まま残っていた(規則19)。

    **測り方。** 参道の芯線 `sando.pts` に沿って**造成前の地盤**(正本 = base_dem 切り出し)を
    `ds` 刻みで採り、**設計路面 = その地盤を `const.suritsukeWinM` の窓で移動平均した線**とする
    (参道は⛔ **造成しない**ので、路面は地盤に従う線以外に置きようが無い)。
    **局所段差 = |地盤 − 設計路面| の最大** = その窓の尺度で路面を通すのに要る摺り付け量。
    ⛔ 窓が切れる両端(半窓ぶん)は測らない — 片側だけの平均は段差を作り出す。

    **拘束するのは `suritsukeWinM` の窓だけ。** `suritsukeRefWinM`(20m)は〔記録〕に刷るだけで
    ⛔ 拘束しない — 20m の起伏は「局所」ではなく**道の線形そのもの**で、これを摺り付けで均すのは
    造成に当たり「参道は公道なので社が造成しない」に反する。
    ⚠ **この切り分け自体は【U 当方の読み】**(考証9巡目 2026-09-07 裁き2 で拘束しない参考値と裁いた)。
    ⛔ **ユーザー裁定3から導かれたものとして書かない** — 裁定は「段を入れない／±0.3 m で吸収する」
    までで、**窓の長さを定めていない**。

    ⛔ **越えたら段を入れて黙らせない — 裁定へ差し戻す。** 段を入れれば【S 記号の不在】
    (御宮絵図は男坂・女坂を梯子状の記号で描き分けるのに、参道の帯には梯子が一本も無い)に反し、
    造成で均せば「公道」に反する。**どちらを崩すかはユーザーの裁定**であって、指図方が選ぶ話ではない。
    """
    c = d["const"]
    lim = c["suritsukeM"]
    pts = d["sando"]["pts"]
    ds = 0.5
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs)

    def at(t):
        for a, b in segs:
            l = math.hypot(b[0] - a[0], b[1] - a[1])
            if t <= l:
                u = t / l if l else 0.0
                return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
            t -= l
        return pts[-1]

    n = int(L / ds) + 1
    hs = [dem_h(*at(min(i * ds, L))) for i in range(n)]
    bad, note = [], []
    if any(h is None for h in hs):
        bad.append("参道の縦断に地盤を採れない点が %d 点(正本 base_dem の窓の外)"
                   % sum(1 for h in hs if h is None))
        return bad, note

    def worst(win):
        k = max(1, int(round(win / ds)))
        half = k // 2
        w = (0.0, 0.0)
        for i in range(half, n - half):
            mean = sum(hs[i - half:i + half + 1]) / float(2 * half + 1)
            dv = hs[i] - mean
            if abs(dv) > abs(w[0]): w = (dv, i * ds)
        return w

    for win in c["suritsukeWinM"]:
        dv, at_s = worst(win)
        note.append("参道の縦断の**局所段差**(%.0f m 窓)%+.3f m ／ 許容 ±%.2f m ── "
                    "芯線の下端から %.1f m の地点【算出 P — 造成前の地盤の正本から】" % (win, dv, lim, at_s))
        if abs(dv) > lim + 1e-9:
            bad.append("参道の局所段差(%.0f m 窓)が %+.3f m で摺り付けの許容 ±%.2f m を超える ── "
                       "⛔ 段を入れて黙らせない。裁定へ差し戻す(段=【S 記号の不在】に反する ／ "
                       "造成=『参道は公道』に反する。どちらを崩すかはユーザーの裁定)" % (win, dv, lim))
    for win in c.get("suritsukeRefWinM") or []:
        dv, at_s = worst(win)
        note.append("(参考・**⛔ 拘束しない**)%.0f m 窓では %+.3f m ── これは『局所』ではなく"
                    "**道の線形そのもの**で、均せば造成に当たる(参道は公道)"
                    "【算出 P ／ ⛔ **拘束しないという切り分けは【U 当方の読み — 考証9巡目 "
                    "2026-09-07 裁き2】**。⛔ ユーザー裁定3から導かれたものとして読まない — "
                    "裁定は『段を入れない/±0.3 m で吸収』までで、窓の長さを定めていない】"
                    % (win, dv))
    # ⭐ **「段が無い」ことの直接の証拠**【検図11巡目 低2 → 2026-09-07】── 摺り付け量は
    #    「窓の尺度で路面を通すのに要る量」であって、**段(不連続)が無いこと自体は言っていない**。
    #    隣り合う標本(`ds`)の高さ差の最大がその直接の証拠で、⛔ これが蹴上級なら段が在る。
    dj = max(((abs(hs[i + 1] - hs[i]), hs[i + 1] - hs[i], i * ds) for i in range(n - 1)))
    note.append("参道の縦断の**隣り合う標本(%.1f m)の高さ差の最大** %+.3f m(芯線の下端から "
                "%.1f m)── ⭕ **段(不連続)は存在しない**(蹴上の既定 %.2f m の %.0f%%)。"
                "⚠ 摺り付け量は『窓の尺度で路面を通すのに要る量』であって、"
                "**段が無いことはこの数が言う**【算出 P — 造成前の地盤の正本から】"
                % (ds, dj[1], dj[2], d["const"]["keri"], 100.0 * dj[0] / d["const"]["keri"]))
    note.append("最大勾配(現況図が刷るのと同じ物差し)2m窓 %.0f%% ／ 5m窓 %.0f%% ／ 20m窓 %.0f%% ── "
                "⭕ 裁定3 の文言『2m窓で2割超の段』はこの 2m窓の値を指す【算出 P】"
                % (path_max_grade(pts, 2.0), path_max_grade(pts, 5.0), path_max_grade(pts, 20.0)))
    return bad, note


def touch_edge_idx(d, areas_src):
    """**道敷に接する社地の辺**を番号つきで返す [(i, a, b, 長さ[m])]。⛔ 辺の番号を書かせない。

    ⭐ **同定の式は `planting.bandDef.rinenEdgeRule` 一本**(辺の中点と両三分点がすべて道敷から
      `rinenEdgeTouchKen` 以内)【決4 庭方 2026-09-09 十八巡目】── ⛔ 二つ持たない。
    ⚠ 引数は `areasFrom` の綴り(`sando.area` / `fumotomichi[].area`)。
    """
    g = G(d)
    soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    A = []
    for s9 in (areas_src or []):
        if s9.startswith("sando") and d.get("sando", {}).get("area"):
            A.append([(g.U(x), g.V(z)) for x, z in d["sando"]["area"]])
        elif s9.startswith("fumotomichi"):
            A += [[(g.U(x), g.V(z)) for x, z in f["area"]]
                  for f in d.get("fumotomichi", []) if f.get("area")]
    tol = (d["planting"]["bandDef"].get("rinenEdgeTouchKen") or _TOUCH_KEN)
    ken = d["const"]["ken"]
    out = []
    for i in range(len(soch)):
        a, b = soch[i], soch[(i + 1) % len(soch)]
        for Q in A:
            ok = True
            for t in (1.0 / 3.0, 0.5, 2.0 / 3.0):
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                dd = 0.0 if in_poly(p, Q) else min(_pt_seg(p, Q[j], Q[(j + 1) % len(Q)])
                                                   for j in range(len(Q)))
                if dd > tol: ok = False; break
            if ok:
                out.append((i, a, b, math.hypot(b[0] - a[0], b[1] - a[1]) * ken))
                break
    return out


_EDGE_NOTE = []


def derive_edges(d):
    """`edgeFrom` を宣言した物の **`fromEdge`(辺の番号)を毎回引き直す**【決4 庭方 十八巡目】。

    ⛔ **番号を json に書かない。**同定は `touch_edge_idx`、**どの辺を張るか**は `spanFrom` の
      とおり「宣言の `uv`(または run の a/b)がその辺の `insetKen` オフセットに載る辺」。
    ⛔ **一致する辺が無ければ番号を立てない** ── `sando_offset_check` が⛔で止める
      (⛔ 黙って近い辺を当てて図を組ませない)。
    〔記録〕同定した辺を**全部、長さつきで**残す(⛔ 黙って一本だけ使わない・規則19)。
    """
    del _EDGE_NOTE[:]
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    items = [(tl, [tuple(q) for q in (tl.get("uv") or [])], "高木の縁の線")] if tl.get("edgeFrom") else []
    for r in d["runs"]:
        if r.get("edgeFrom"): items.append((r, [tuple(r["a"]), tuple(r["b"])], r["name"]))
    for o, pts, nm in items:
        src = o.get("areasFrom")
        if src is None and o is not tl: src = tl.get("areasFrom")
        E = touch_edge_idx(d, src)
        _EDGE_NOTE.append((nm, [(i, L) for i, _a, _b, L in E]))
        ins = o.get("insetKen")
        if ins is None: ins = tl.get("insetKen")
        hit = None
        for i, _a, _b, _L in E:
            want = edge_offset(d, [i, (i + 1) % len(d["polygon"])], ins)
            if pts and max(min(math.hypot(q[0] - w[0], q[1] - w[1]) for w in want)
                           for q in pts) <= 0.02:
                hit = i; break
        o["fromEdge"] = ([hit, (hit + 1) % len(d["polygon"])] if hit is not None else None)


def edge_ident_rows(d):
    """〔記録〕同定した辺(番号・長さ・張った辺)。⛔ 数を json に写さない。"""
    out = []
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    used = dict([("高木の縁の線", (tl.get("fromEdge") or [None])[0])] +
                [(r["name"], (r.get("fromEdge") or [None])[0])
                 for r in d["runs"] if r.get("edgeFrom")])
    for nm, E in _EDGE_NOTE:
        u9 = used.get(nm)
        rest = [q for q in E if q[0] != u9]
        out.append("『%s』── 道敷に接する辺 **%d 本**(%s)／ 張ったのは **辺%s**%s"
                   "【算出 — ⛔ 番号を json に書かない(決4 庭方 2026-09-09 十八巡目)】"
                   % (nm, len(E), "・".join("辺%d %.1f m" % q for q in E), u9,
                      ("。⛔ **%s には張っていない** ── 猶予『高木の縁の線を二本目の辺まで"
                       "伸ばすか』は **2026-09-09 十九巡目 A-6 で閉じた**(⛔ 伸ばさない ── "
                       "二本目へ `insetKen` だけ内へ寄せた線が落ちる先は井戸屋形の板石敷・"
                       "前庭の帯・御成の供待で、高木の縁の線を通せる場所ではない)。"
                       "⭕ **同定した辺は二本とも長さつきで刷り続ける** ── "
                       "『測ったうえで張らない』と『測っていない』を混ぜない(規則19)"
                       % "・".join("辺%d(%.1f m)" % q for q in rest)) if rest else ""))
    return out


def sando_offset_check(d):
    """参道の柵と高木の縁の線が、宣言どおり社地の辺のオフセットになっているか。

    ⭐ 座標をベタで持たせた代わりに**辺との食い違いを組む前に鳴らす**(辺を動かした日に黙って取り残される)。
    """
    bad = []
    rs = d.get("sando", {}).get("roadside") or {}
    tgt = [(r.get("fromEdge"), r.get("insetKen"), [tuple(r["a"]), tuple(r["b"])], r["name"])
           for r in d["runs"] if r.get("fromEdge") or r.get("edgeFrom")]
    tl = rs.get("takagiEdgeLine")
    if tl and tl.get("edgeFrom"):
        tgt.append((tl.get("fromEdge"), tl["insetKen"], [tuple(q) for q in tl["uv"]], "高木の縁の線"))
    for idx, ins, got, nm in tgt:
        if not idx:
            bad.append("%s の `edgeFrom`(道敷に接する辺)が**一本も当たらない** — "
                       "⛔ 宣言の `uv`/`a`,`b` がどの辺の %s 間オフセットにも載らない"
                       "(決4 庭方 2026-09-09 十八巡目。⛔ 近い辺を黙って当てない)" % (nm, ins))
            continue
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
    # ⭐ **名指しの木も区の内訳**【A-1 庭方 2026-09-09 十九巡目】── ★主景は塊から出て
    #    名指しの木になったので、⛔ 区の本数から黙って消えないよう区ごとに数え直す。
    nmz = {}
    for r9 in named_tree_rows(d, g):
        if r9.get("zone") and r9.get("layer") in ("松", "落葉"):
            nmz[r9["zone"]] = nmz.get(r9["zone"], 0) + 1
    for gd in d["gardens"]:
        k9 = nmz.get(gd["name"], 0)
        n = sum(cluster_n(c) for c in gd.get("clusters", [])) + len(_takagi_singles(gd)) + k9
        if n: rows.append((gd["name"], int(round(n)),
                           "塊+一本立ち" + ("+名指しの木 %d 本" % k9 if k9 else "")))
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
    """立木の塊(細線の箱)と一本立ち(点)、主景の固定木。

    ⭐ **2026-09-08 に `planting.viewClusters` を描画へ載せた** ── 旧式は
    `gardens` と `slopeBands` の `clusters` しか回しておらず、**男坂の見切りはどの図にも
    描かれていなかった**(html に名は5回出るが SVG の中は 0 回)。⛔ 図に出ない設計値を残さない(規則19)。
    """
    o = []
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            for u0, v0, u1, v1 in cluster_boxes(c):
                if not inwin([u0, v0], [u1, v1]): continue
                o.append(lp.rect(u0, v0, u1, v1, fill="none", stroke="var(--take)", sw=0.7, dash="3 3"))
                _lo = c.get("labelOff") or [0, 0]     # ⛔ 設計値ではない — 銘の逃がし(px)
                o.append(T(lp.X((u0 + u1) / 2.0) + _lo[0], lp.Y(v1) - 3 + _lo[1], cluster_label(c),
                           fs=9, anchor="middle", fill="var(--take)"))
            if c.get("alongTakagiEdgeLine") and c.get("poly"):
                # ⭐ **輪郭そのものを描く**(2026-09-08 C-1)── ⛔ 旧式は `vRange` で切っていない
                #    線の全長で平行四辺形を描いており、**図が塊の実形を刷っていなかった**。
                ring = [(q[0], q[1]) for q in c["poly"]]
                if not inwin([min(q[0] for q in ring), min(q[1] for q in ring)],
                             [max(q[0] for q in ring), max(q[1] for q in ring)]): continue
                o.append(PL([(lp.X(u), lp.Y(v)) for u, v in ring], fill="var(--take)", op=0.28,
                            stroke="var(--take)", sw=0.7, close=True))
                cu = sum(q[0] for q in ring) / len(ring)
                cv = sum(q[1] for q in ring) / len(ring)
                o.append(T(lp.X(cu), lp.Y(cv) - 3, cluster_label(c),
                           fs=9, anchor="middle", fill="var(--take)"))
        for sg in gd.get("singles", []):
            u, v = sg["uv"]
            if not inwin([u, v], [u, v]): continue
            # ⛔ **樹冠は `single_crown` から描く**(2026-09-07)── 旧式は個体の `crown`(手値)が
            #    あるときだけ円を描いており、落葉高木が仮値を外して**従属値へ戻った日に、
            #    図から樹冠の円が丸ごと消えた**(規則19: 図に出ない値は誰も検められない)。
            #    ⭕ 中木・松の樹冠もこれで初めて図に出る(検査は前から測っていた)。
            _r = single_crown(d, sg)
            if _r:
                # ⭐ **傾きの宣言があれば樹冠の円はその分だけ寄る**(2026-09-08 中3 庭方)
                _cu, _cv = single_crown_center(d, sg)
                o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="var(--take)" opacity="0.18" '
                         'stroke="var(--take)" stroke-width="0.7" stroke-dasharray="3 3"/>'
                         % (lp.X(_cu), lp.Y(_cv), lp.L(_r)))
                if math.hypot(_cu - u, _cv - v) > 1e-9:
                    o.append(LN(lp.X(u), lp.Y(v), lp.X(_cu), lp.Y(_cv),
                                stroke="var(--take)", sw=0.9, dash="2 2"))
            o.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--take)"/>' % (lp.X(u), lp.Y(v)))
            lab = sg["name"] + (" %.1fm" % sg["h"] if sg.get("h") else "")
            # ⛔ `labelOff` は**設計値ではない** — 図の銘が他の銘と重なるのを逃がす px の値
            #    (2026-09-08 検図12巡目・ラベル衝突)。⛔ 木の位置は動かさない。
            _lo = sg.get("labelOff") or [0, 0]
            if math.hypot(_lo[0], _lo[1]) > 16.0:      # 逃がしが大きい銘は引出線で木へ結ぶ
                o.append(LN(lp.X(u) + 2, lp.Y(v) - 2,
                            lp.X(u) + 4 + _lo[0] + (6 if _lo[0] < 0 else 0),
                            lp.Y(v) - 4 + _lo[1] + 2,
                            stroke="var(--take)", sw=0.6, op=0.8))
            o.append(T(lp.X(u) + 4 + _lo[0], lp.Y(v) - 4 + _lo[1], lab, fs=9, fill="var(--take)"))
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
                _hm = shukei_hmin(d, sk)   # ⛔ 数を json から読まない(2026-09-08 A-2)
                o.append(T(lp.X(tu), lp.Y(tv) + 12,
                           "★主景の木 丈%s以上" % ("—" if _hm is None else "%.1fm" % _hm),
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


def edge_understory_stats(d):
    """平場の縁の下層 ── (帯の面[間²], 本数)。⛔ 数を json に持たない(面 ÷ 芯々²)。

    ⭐ 2026-09-08 中2(庭方)── 旧図は破線を二本描くだけで、**面も本数も丈も一度も刷って
    いなかった**。面は二本のオフセット線が囲む帯そのもの。
    """
    pl = (d.get("planting") or {}).get("edgeUnderstory")
    if not pl: return (None, None)
    e = d["planting"]["clearance"]["keidai"]["terraceEdge"]
    a = offset_poly_in(d["terraces"][0]["uv"], e)
    b = offset_poly_in(d["terraces"][0]["uv"], e + pl["insetKen"])
    ar = abs(poly_area(a)) - abs(poly_area(b))
    sp = pl.get("spacing") or 0.0
    return (ar, (ar / (sp * sp)) if sp else None)


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


# 部材名・API の雛形に開けてある「大きさ」の穴。⛔ 綴りは json の `sizeRule.sizes` が正典。
_SIZE_HOLE = "{size}"


def mune_ornament(d, m=None):
    """**棟飾り(鬼板・置千木)の丈**[m] と その出所。⛔ 数を図に写さない(規則4)。

    ⭐ **目録 `docs/asset-index.tsv` の丈は『鬼の頂』であって大棟ではない**
    【高2 考証19巡目 → 2026-09-09】── `const.muneHeightRule` は棟飾りを含まないと定めたので、
    棟高は **目録の丈 − ここ** の従属値になる。
    ⚠ **部材方の報告が届くまでは暫定値**(`const.muneOrnamentProvisionalM`)で、
      ⛔ **『暫定』と名乗ったまま**使う(⛔ 設計値として通さない)。
    戻り (丈[m], 出所の語) — どちらも無ければ (None, None)。
    """
    c = d["const"]
    if m is not None and m.get("muneOrnamentM") is not None:
        return float(m["muneOrnamentM"]), "棟ごとの宣言(部材方の実測)"
    # ⭐ **棟ごとの暫定値**【B-1 検図22巡目 → 2026-09-09 十九巡目】── ⛔ **`const` の一律で
    #   引いてはならない**。部材の生成器が自ら『引けない』と言っている棟が三つある
    #   (向拝は大棟を持たない ／ 両下造は鬼が無いので値は変わらない)。
    if m is not None and m.get("muneOrnamentProvisionalM") is not None:
        return (float(m["muneOrnamentProvisionalM"]),
                "⚠ **暫定値 — この棟の棟飾りは測られていない**(部材方の報告待ち)")
    if c.get("muneOrnamentM") is not None:
        return float(c["muneOrnamentM"]), "`const.muneOrnamentM`"
    return None, None


def mune_h(d, m):
    """棟高[m]。⛔ **測り方の正典は `const.muneHeightRule` 一本**(裁定 2026-09-09)。

    ⭐ 出所は二つだけ ── ① `munes[].h`(実測が返って**数で決まった**棟)
    ② `munes[].partFrom` が指す**目録の部材の丈 − 棟飾りの丈**(⛔ 図が写さない・規則4)。
    どちらも無ければ None(= 棟高が引けない)。⛔ 類型で埋めない(規則7)。
    ⭐ **棟飾りを引く**【高2 考証19巡目 → 2026-09-09】── ⛔ 目録が測っているのは**鬼の頂**で、
      物差しが『⛔ 棟飾りを含まない』と定めた値ではなかった(⛔ 定義を書いただけで測る対象は
      変わっていなかった)。
    """
    if m.get("h") is not None: return float(m["h"])
    pf = m.get("partFrom")
    if not pf: return None
    g0 = part_geom({"prefab": pf})
    if not g0: return None
    orn, _src = mune_ornament(d, m)
    return g0[1] - (orn or 0.0)


def mune_height_check(d):
    """**棟高の物差しと、部材の丈との突き合わせ**【高3 検図21巡目 → 裁3/裁4 2026-09-09】。

    ⛔ 止める三つ:
      ① `const.muneHeightRule`(測り方)の宣言が無い ── 同じ棟高に三つの数ができる出所
      ② `partFrom` の指し先が**目録 `docs/asset-index.tsv` で解けない** ──
         ⚠ **解けないのが正しい状態のこともある**(目録の再生成は Unity が要る)。
         ⛔ それでも黙らせない ── 図が現物を説明していないことは⛔で出す。
      ③ `h` と `partFrom` の**両方**を持つ棟で、二つが食い違う(= 正典が二つ)
    〔記録〕棟ごとの丈と出所。⛔ 数を文章にも json にも写さない(規則4)。
    """
    bad, note = [], []
    if not (d["const"].get("muneHeightRule")):
        bad.append("`const.muneHeightRule`(棟高の測り方)の宣言が無い — ⛔ 『棟高とは何を測るか』"
                   "が書かれていないと、同じ棟高に**三つの数**ができる(高3 検図21巡目 — "
                   "検図の測りと普請奉行の測りが 0.68 m 食い違った)")
    # ⭕ **社殿の床高**【⑥ 考証18巡目 中9 → 2026-09-09】── `shadenHondenFloor` は式なので、
    #    ⛔ **解けることを測る**(規則19 — 宣言だけで誰も読まない値を作らない)。
    c9 = d["const"]
    fr9 = c9.get("shadenHondenFloor")
    if fr9 is None:
        bad.append("`const.shadenHondenFloor`(本殿の床高)の宣言が無い — 本殿は『石造亀腹に"
                   "土台立てとし、縁を腰組で支持する』【A 加藤2018 6-1】ので、⛔ 幣殿・拝殿と"
                   "同床高では誤り(考証18巡目 中9)")
    elif isinstance(fr9, str):
        try:
            hv9 = eval(fr9, {"__builtins__": {}},                     # noqa: S307
                       dict((k8, v8) for k8, v8 in c9.items() if isinstance(v8, (int, float))))
        except Exception:
            hv9 = None
        if hv9 is None:
            bad.append("`const.shadenHondenFloor` の式『%s』が解けない — 指し先の無い従属は"
                       "誰も辿れない(規則19)" % fr9)
        else:
            note.append("社殿の床高 ── 幣殿・拝殿・向拝 **%.2f m**(`shadenFloor`)／ "
                        "**本殿 %.2f m**(`shadenHondenFloor` = %s ＝ 幣殿の床 + 段 %.2f m)"
                        "【⑥ 考証18巡目 中9 → 2026-09-09。⭕ 本殿は『石造亀腹に土台立て』"
                        "【A 加藤2018 6-1】で幣殿・拝殿より高い。段は根津断面の実測からの外挿"
                        "【A 相当】。⛔ 数を文章に写さない(規則4)】"
                        % (c9.get("shadenFloor") or 0.0, hv9, fr9,
                           c9.get("shadenHondenStepM") or 0.0))
    # ⭐ **棟飾りの丈が引けるか**【高2 考証19巡目 → 2026-09-09】── ⛔ 引けなければ棟高は
    #    **鬼の頂**のままで、物差しの文言と測る対象が食い違ったままになる(⛔ 定義を書いた
    #    だけで直っていない、という前巡の欠陥そのもの)。
    # ⭐ **棟ごとに測る**【B-1 検図22巡目 → 2026-09-09 十九巡目】── ⛔ `const` の一律の暫定値は
    #    廃した(棟ごとに違うと判った時点で `const` は正典の格を失う)。
    if c9.get("muneOrnamentProvisionalM") is not None:
        bad.append("`const.muneOrnamentProvisionalM`(棟飾りの暫定値)が**復活している** — "
                   "⛔ **一律に引いてはならない**。部材の生成器が自ら『引けない』と言っている棟が"
                   "三つある(向拝は大棟を持たない ／ 両下造は鬼が無いので値は変わらない)。"
                   "⇒ `munes[].muneOrnamentProvisionalM` へ棟ごとに降ろすこと(B-1 検図22巡目)")
    pr9 = c9.get("muneOrnamentPendingRef")
    nprov = 0
    for m9 in d["munes"]:
        if not m9.get("partFrom"): continue
        o9, s9 = mune_ornament(d, m9)
        if o9 is None:
            bad.append("棟『%s』の棟飾りの丈が引けない — ⛔ **目録の丈は『鬼の頂』**であって "
                       "`const.muneHeightRule` が定めた『大棟の上端』ではない(高2 考証19巡目)。"
                       "⛔ 引けないまま棟高を刷らない(規則19)" % m9["name"])
            continue
        if s9.startswith("⚠"): nprov += 1
    if nprov and not (pr9 and pr9 in (d.get("_pending") or {})):
        bad.append("棟飾りの**暫定値**を %d 棟で使っているのに、`const.muneOrnamentPendingRef` の"
                   "指し先が `_pending` に無い — ⛔ 指し先の無い猶予は誰も辿れない(規則19)" % nprov)
    elif nprov:
        note.append("棟飾り(鬼板・置千木)── **%d 棟が暫定値**(部材方の実測待ち・猶予『%s』)／ "
                    "実測が入った棟 %d。⛔ **一律の `const` は廃した**(棟ごとに違う ── 向拝は"
                    "大棟を持たず、両下造は鬼が無い)。棟高 = **目録の丈 − その棟の棟飾り**"
                    "(`const.muneHeightRule`)【算出 — B-1 検図22巡目 → 2026-09-09。"
                    "⛔ 数を図にも json の文章にも写さない(規則4)】"
                    % (nprov, pr9,
                       sum(1 for m9 in d["munes"]
                           if m9.get("partFrom") and m9.get("muneOrnamentM") is not None)))
    n9 = 0
    for m in d["munes"]:
        pf = m.get("partFrom")
        if not pf:
            # ⛔ **社殿は必ず部材を指す** ── 5棟とも新造済みなので、指し先が落ちれば
            #    棟高が引けなくなり、主景の仰角が黙って欠ける(規則19)。
            if m.get("yaku") == "社殿":
                bad.append("棟『%s』(社殿)が `partFrom`(部材への指し先)を持たない — "
                           "棟高が引けず、主景の仰角の行が黙って落ちる(⛔ 0 件は合格ではなく"
                           "未測定・規則19)" % m["name"])
            if m.get("h") is not None:
                note.append("棟『%s』── 丈 %.2f m(出所 `munes[].h` の宣言・⛔ 部材への指し先が"
                            "無いので現物と照合できない)【算出】" % (m["name"], m["h"]))
            continue
        n9 += 1
        g0 = part_geom({"prefab": pf})
        if g0 is None:
            bad.append("棟『%s』の `partFrom`『%s』が**目録 `docs/asset-index.tsv` で解けない** — "
                       "⛔ 図が現物を説明していない(高3 検図21巡目)。⚠ 目録の再生成は Unity が"
                       "要るので普請奉行の手当てを待つ状態だが、⛔ 待っている間も黙らせない"
                       % (m["name"], pf))
            continue
        h9 = m.get("h")
        if h9 is not None and abs(float(h9) - (g0[1] - (mune_ornament(d, m)[0] or 0.0))) > 0.05:
            bad.append("棟『%s』── 宣言 `h` %.2f m と部材『%s』の丈 %.2f m が **%.2f m 食い違う**"
                       "(物差しは `const.muneHeightRule`)。⛔ 同じ棟高に正典を二つ持たない(規則4)"
                       % (m["name"], float(h9), pf, g0[1], abs(float(h9) - g0[1])))
        o9, os9 = mune_ornament(d, m)
        # ⭐ **目録の丈の呼び名は棟による**【B-1 検図22巡目 → 2026-09-09 十九巡目】── ⛔ 鬼を
        #    持たない棟(両下造)・大棟を持たない棟(向拝)の丈を『鬼の頂』と呼ぶのは**名前も誤り**。
        top9 = "**鬼の頂**" if (o9 or 0.0) > 1e-9 else "**棟の頂**(鬼板・置千木を持たない)"
        note.append("棟『%s』── 部材『%s』の丈(%s)%.2f m − 棟飾り %s = "
                    "**棟高 %.2f m**(桁行 %.2f m × 三角数 %s)／ 棟飾りの出所 %s ／ 丈の出所 %s"
                    "【算出 — 物差しは `const.muneHeightRule`(平場の設計面 → 大棟の上端・"
                    "⛔ 棟飾りを含まない)。⛔ 実寸を図にも json にも写さない(規則4)】"
                    % (m["name"], pf, top9, g0[1],
                       ("%.3f m" % o9) if o9 is not None else "**引けない**",
                       g0[1] - (o9 or 0.0), g0[0], format(g0[2], ","), os9 or "—",
                       ("宣言 `h` と一致" if h9 is not None else "**目録**(`h` は撤回・裁4)")))
    note.append("`partFrom` を持つ棟 **%d**(社殿)／ 持たない棟 %d(⛔ 類型の根拠が無い所を数で"
                "埋めない・規則7)【算出 — 裁4 2026-09-09】" % (n9, len(d["munes"]) - n9))
    return bad, note


def part_is_tpl(pt):
    """palette の一点が**大きさを持たない雛形**か(`{size}` を含む)。"""
    return _SIZE_HOLE in (pt.get("prefab") or "") or _SIZE_HOLE in (pt.get("api") or "")


def size_rule(d):
    """`planting.scaleRule.sizeRule` ── 大きさ(変種)を丈から選ぶ規約。無ければ None。"""
    return (d["planting"].get("scaleRule") or {}).get("sizeRule")


def part_variants(d, pt):
    """雛形 `pt` の**目録に在る変種**の列 [(size, prefab, api, 素の丈, 素の樹冠, 三角数)]。

    ⛔ 変種を json に書かない(規則4)── `sizeRule.sizes` の綴りで目録を引くだけ。
    """
    sr = size_rule(d)
    if not sr: return []
    out = []
    for sz in sr.get("sizes", []):
        pf = (pt.get("prefab") or "").replace(_SIZE_HOLE, sz)
        g0 = part_geom({"prefab": pf})
        if g0 is None: continue
        out.append((sz, pf, (pt.get("api") or "").replace(_SIZE_HOLE, sz), g0[1], g0[0], g0[2]))
    return out


def part_variant_count(d, pt):
    """**別々のプレハブ**として在る変種の数。⛔ 行の数で数えない。

    ⭐ 2026-09-07 九巡目 中4 ── `part_variants` は `sizes` の綴りを順に当てるので、
    **大きさを名指しした部材**(松・低木)では同じプレハブが `sizes` の数だけ返る。
    それを「変種が3種ある」と読むと、選びようの無い部材に大きさの照合を当ててしまう。
    """
    return len(set(q[1] for q in part_variants(d, pt)))


def species_h_cap(d, pt):
    """**樹種ごとの丈の上端**[m] = その樹種の**最大変種の素の丈** × `sizeRule.scaleYMax`。

    ⭐ 2026-09-08 庭方12巡目 裁定1 ── 帯は層(落葉高木)に**一つの**丈の範囲を宣言するが、
    部材の素の丈は樹種で違う。**帯の上端が悪いのではなく、帯が三樹種に同じ天井を当てているのが
    悪い** — 実際の樹高もケヤキ ＞ ムクノキで、**部材はそれを正しく写している**。
    ⇒ 各樹種の丈をここで頭打ちにする。⛔ `rakuyoH` そのものを下げない(下げるとケヤキ・エノキまで
    連れて下がり、社叢から最も高い抜け木が消える)。
    ⛔ **規約 `sizeRule.speciesHCap` の宣言が無ければ効かせない** — 宣言の無い頭打ちは
    「黙って丈を縮める道」であって、それこそ規則19 が禁じる形。無ければ None。
    """
    sr = size_rule(d) or {}
    if not sr.get("speciesHCap"): return None
    cap = sr.get("scaleYMax")
    vs = part_variants(d, pt)
    if cap is None or not vs: return None
    return max(q[3] for q in vs) * cap


def pick_variant(d, pt, h):
    """**`sizeRule` — 丈 h[m] に対して選ぶ変種**。(size, prefab, api, scaleY) か None。

    ⭐ 2026-09-07 庭方8巡目 裁定1 ── 「`scaleY` ≤ `scaleYMax` を満たす変種のうち
    |ln(scaleY)| が最小。満たす変種が無ければ**最も大きい変種**」。
    ⛔ 雛形でない(大きさを名指しした)部材はそのまま返す。
    """
    if not part_is_tpl(pt):
        g0 = part_geom(pt)
        return (None, pt.get("prefab"), pt.get("api"),
                (h / g0[1]) if (g0 and h and g0[1]) else None)
    vs = part_variants(d, pt)
    if not vs or not h: return None
    cap = (size_rule(d) or {}).get("scaleYMax")
    cand = [(sz, pf, api, h / hh) for sz, pf, api, hh, _cr, _t in vs if hh]
    ok = [q for q in cand if cap is None or q[3] <= cap + 1e-12]
    if ok: return min(ok, key=lambda q: abs(math.log(q[3])))
    big = max(vs, key=lambda q: q[3])
    return (big[0], big[1], big[2], h / big[3])


def part_tris(d, pt):
    """palette の一点の三角数。雛形なら**変種の平均**(⛔ どの変種が何本かはここでは決まらない)。"""
    g0 = part_geom(pt)
    if g0 is not None: return float(g0[2])
    vs = part_variants(d, pt)
    return (sum(q[5] for q in vs) / float(len(vs))) if vs else None


_GRP = {}


def derive_cluster_groups(d):
    """**`groups` を持つ塊を、弧長の割り付けから兄弟の塊へ展開する**
    【中6 庭方 2026-09-09 十七巡目】。

    ⭐ **一列を三塊に割る。**⛔ 位置の数を json に持たない ── 塊の中の芯々
      (`groupSpacingKen` の中央)から各塊の弧長を出し、残りを塊と塊で等分する。
    ⛔ 展開した兄弟は親の宣言(`alongTakagiEdgeLine` / `widthKen` / `layers` / `hFrom` /
      `variantRule` / `overhangFrom` / `edaShitaOverRoadM`)をそのまま引き継ぐ。
    〔記録〕割り付けた離れは `_gapKen` に載せ、検査『塊が塊として組めるか』が刷る。
    """
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    for gd in d["gardens"] + d["slopeBands"]:
        cs = gd.get("clusters")
        if not cs: continue
        out = []
        for c in cs:
            gp = c.get("groups")
            if not gp or not c.get("vRange"):
                out.append(c); continue
            v0, v1 = c["vRange"]
            V = float(v1 - v0)
            # 弧長 → v の換算(線の向きから・⛔ 数を持たない)
            kv = 1.0
            if tl.get("fromEdge") and tl.get("insetKen") is not None:
                A, B = edge_offset(d, tl["fromEdge"], tl["insetKen"])
                L9 = math.hypot(B[0] - A[0], B[1] - A[1]) or 1.0
                kv = abs(B[1] - A[1]) / L9
            sp = c.get("groupSpacingKen") or [0.0, 0.0]
            # ⭐ **上端で置く**【A-7 庭方 2026-09-09 十九巡目 ── ⛔ 十七巡目の『幅は上端・
            #   芯々は下端 × `packRatio`』は撤回された】。線に沿う塊は**弧長を芯々で刻んで
            #   据える**ので、塊の弧長も据える刻みも `groupSpacingKen` の**上端**そのもの。
            #   ⛔ 詰めない ── 詰めると宣言の下限を割り、しかも誰も鳴らさない。
            s9, sx9 = sp[1], sp[1]
            ext = [(len(cluster_mix(q)) and float(sum(k for _k, k in cluster_mix(q))) - 1.0
                    or 0.0) * sx9 * kv for q in gp]
            gap = ((V - sum(ext)) / (len(gp) - 1)) if len(gp) > 1 else 0.0
            at = v0
            for i, q in enumerate(gp):
                ch = collections.OrderedDict()
                ch["name"] = "%s %s" % (c["name"], q.get("name") or (i + 1))
                for k9 in ("alongTakagiEdgeLine", "shape", "layers", "widthKen", "hFrom",
                           "variantRule", "overhangFrom", "role", "edaShitaOverRoadM"):
                    if c.get(k9) is not None: ch[k9] = c[k9]
                ch["mix"] = q["mix"]
                ch["spacing"] = s9
                ch["vRange"] = [round(at, 4), round(at + ext[i], 4)]
                ch["_"] = ("**親の塊『%s』の `groups` からの展開**(⛔ 位置も芯々も数で持たない)。"
                           "⚠ 兄弟との離れは残りの等分で、下限は親の `groupGapKen`。" % c["name"])
                ch["_ofGroup"] = c["name"]
                ch["_gapKen"] = round(gap / (kv or 1.0), 4)
                ch["_gapMinKen"] = c.get("groupGapKen")
                # ⭐ **親の芯々の宣言を子へ運ぶ**【A-7 庭方 2026-09-09 十九巡目】── ⛔ 親は
                #   この展開で `clusters` から消えるので、⛔ 運ばないと**焼き出しの芯々を
                #   宣言と突き合わせる検査が黙る**(規則19)。
                ch["_spacingRangeKen"] = list(sp)
                out.append(ch)
                at += ext[i] + gap
        gd["clusters"] = out


def derive_clusters(d):
    """`boxFrom` を持つ塊の**箱を宣言から起こす**(⛔ 箱の数を json に持たない・規則4)。

    ⭐ 2026-09-07 八巡目 中3 ── 辻の留めの箱は「東縁=高木の縁の線・西へ `widthKen`・
    v は `vRange`」の従属値。箱は軸に平行なので、**東縁は v の範囲で線がいちばん西へ来る
    値に取る**(こうすれば林縁の帯へ一切食い込まない)。
    """
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            bf = c.get("boxFrom")
            if not bf or c.get("box"): continue
            if bf.get("eastEdge") != "sando.roadside.takagiEdgeLine": continue
            if not tl.get("fromEdge") or tl.get("insetKen") is None: continue
            A, B = edge_offset(d, tl["fromEdge"], tl["insetKen"])
            v0, v1 = bf["vRange"]
            if abs(B[1] - A[1]) < 1e-9: continue
            uu = [A[0] + (v - A[1]) * (B[0] - A[0]) / (B[1] - A[1]) for v in (v0, v1)]
            u1 = min(uu)
            c["box"] = [u1 - bf["widthKen"], v0, u1, v1]
    # ⭐ **線に沿う平行四辺形**(2026-09-08 十六巡目 C-1・庭方)── 東縁 = `takagiEdgeLine` の
    #    `vRange` の区間そのもの、西縁 = 法線方向へ `widthKen` 寄せた線。
    #    ⛔ 四隅の座標を json に持たない。⛔ 内向きは決め打ちしない — **同じ `edge_offset` を
    #    1 間ぶん深く引いた差**を内向きに採る(社地の内外の判定と食い違う道を作らない)。
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            if not c.get("alongTakagiEdgeLine") or c.get("poly"): continue
            if not tl.get("fromEdge") or tl.get("insetKen") is None: continue
            if not c.get("vRange") or c.get("widthKen") is None: continue
            A, B = edge_offset(d, tl["fromEdge"], tl["insetKen"])
            A2, _B2 = edge_offset(d, tl["fromEdge"], tl["insetKen"] + 1.0)
            if abs(B[1] - A[1]) < 1e-9: continue
            v0, v1 = c["vRange"]
            at = lambda v: (A[0] + (v - A[1]) * (B[0] - A[0]) / (B[1] - A[1]), v)
            a0, a1 = at(v0), at(v1)
            nx, nz = A2[0] - A[0], A2[1] - A[1]          # 1 間ぶんの**内向き**
            w = c["widthKen"]
            c["poly"] = [[a0[0], a0[1]], [a1[0], a1[1]],
                         [a1[0] + nx * w, a1[1] + nz * w], [a0[0] + nx * w, a0[1] + nz * w]]
            c["_lineLenKen"] = math.hypot(a1[0] - a0[0], a1[1] - a0[1])


_VH = []


def derive_view_clusters(d, g):
    """**視線が決める塊の丈を、箱が跨ぐ帯から起こす**(`hFrom`)。⛔ 数を json に持たない。

    ⭐ 2026-09-08 ── `planting.viewClusters` は本数と箱と役だけを持ち、**丈も層も無かった**ので、
    部材も樹冠も `scaleY` も一行も刷られていなかった(⛔ 0 件は合格ではなく未測定・規則19)。
    ⭐ **丈は箱が跨ぐ帯の `matsuH` の共通部分**【庭方 2026-09-07 十巡目】── 額縁は
    **自分が立っている林を超えない**ので、跨ぐ帯のどちらでも成り立つ丈=共通部分を採る。
    ⛔ 幅が狭いのは額縁として正しい(稜線を作るのは主景の側)。
    """
    cells, _sk = band_scan(d, g)
    for c in d["planting"].get("viewClusters", []):
        if not c.get("hFrom"): continue
        bx = cluster_boxes(c)
        bs = set()
        for k, ps in cells.items():
            for u, v in ps:
                if any(u0 <= u <= u1 and v0 <= v <= v1 for u0, v0, u1, v1 in bx):
                    bs.add(k); break
        hs = [b.get("matsuH") for b in d["slopeBands"] if b["band"] in bs and b.get("matsuH")]
        c["_bands"] = sorted(bs)
        if hs:
            c["matsuH"] = [max(q[0] for q in hs), min(q[1] for q in hs)]


def view_holders(d):
    """`viewClusters` を **塊を持つ holder** の形で返す(⛔ 名簿を別に持たない)。

    ⚠ `cluster_parts` は holder の `zone_h()` から丈を引くので、丈が holder まで届く道が要る。
    """
    out = []
    for c in d["planting"].get("viewClusters", []):
        h = {"name": "視線の塊", "clusters": [c]}
        if c.get("matsuH"): h["matsuH"] = c["matsuH"]
        if c.get("rakuyoH"): h["rakuyoH"] = c["rakuyoH"]
        out.append(h)
    return out


def _h_pair(h):
    """丈の宣言(数 or [lo,hi])を (lo, hi) へ。宣言が無ければ (None, None)。"""
    if isinstance(h, (list, tuple)):
        return (float(h[0]), float(h[1])) if len(h) >= 2 else (None, None)
    return (float(h), float(h)) if h else (None, None)


def pick_variants_over(d, pt, h, n=201):
    """丈が**範囲**のとき、その範囲に現れる変種と `scaleY` の幅。

    ⚠ **変種は一本ずつ選ぶ** — 帯の丈は範囲なので、同じ樹種でも丈で変種が変わる。
    戻り ([(size, prefab, api)], scaleY 最小, scaleY 最大)。
    """
    lo, hi = _h_pair(h)
    if lo is None: return ([], None, None)
    # ⭐ **樹種ごとの頭打ち**(`sizeRule.speciesHCap`・裁定1 庭方 2026-09-08)。⛔ ここだけに置く —
    #    一本立ちの `h` は意匠が名指しした丈なので縮めない(縮めたら宣言を黙って書き換えたことになる)。
    cp = species_h_cap(d, pt)
    if cp is not None and hi > cp: hi = max(lo, cp)
    seen, ylo, yhi = [], None, None
    for i in range(n if hi > lo else 1):
        hh = lo + (hi - lo) * i / float(max(1, n - 1))
        q = pick_variant(d, pt, hh)
        if q is None: continue
        if (q[0], q[1], q[2]) not in seen: seen.append((q[0], q[1], q[2]))
        y = q[3]
        if y is None: continue
        ylo = y if ylo is None else min(ylo, y)
        yhi = y if yhi is None else max(yhi, y)
    return (seen, ylo, yhi)


def h_eff_txt(d, pt, h):
    """丈の刷り ── **帯の宣言**と、`speciesHCap` で頭打ちにした**実際に立つ丈**を両方出す。

    ⭐ 庭方 2026-09-08 裁定1 の但し書き ── 「帯は 13.0〜16.0 と宣言し、実際に立つムクノキは
    13.0〜15.40」。**この食い違いが図に出ないと、次の巡で同じ事故になる**(帯が何を宣言している
    かと、何が建つかが離れたまま渡る)。戻り (刷り, 頭打ちが効いたか)。
    """
    lo, hi = _h_pair(h)
    if lo is None: return ("—", False)
    cp = species_h_cap(d, pt)
    if cp is None or hi <= cp + 1e-9: return ("%s m" % _rng(h), False)
    cap = (size_rule(d) or {}).get("scaleYMax") or 0.0
    return ("%s m(帯の宣言)→ **%s m**(樹種ごとの頭打ち = 最大変種の素の丈 × 箍 %.2f)"
            % (_rng(h), _rng([lo, max(lo, cp)], fmt="%.2f"), cap), True)


def _vsjoin(vs):
    """変種の刷り。⛔ 大きさを名指しした部材(松・低木)は `size` が無いので `—` を出す。"""
    return "/".join((q[0] or "\u2014") for q in vs) or "\u2014"


def layer_xz(d, kind, iso=False):
    """層 `kind` の `scaleXZ`(範囲)。⛔ 数をここに書かない — `scaleRule` が正典。

    ⭐ **2026-09-08 十六巡目 中6(庭方)** ── 落葉・中木は `crownPerH`(樹冠÷丈)から
    **部材 × `scaleXZ`** へ移した。⛔ 同じ量に二つの宣言を置かない(規則4)。
    ⭕ `iso=True`(一本立ち・`isolatedCrown` の塊)は `scaleRule.isolatedXZ` を当てる ──
    孤立木は**野に一本で育った開いた形が正しい**。⛔ 松はこの規約の外(範囲は部材寄り)。
    """
    rule = d["planting"]["scaleRule"].get(kind) or {}
    if iso and kind != "matsu":
        v = d["planting"]["scaleRule"].get("isolatedXZ")
        if v is not None: return [float(v), float(v)]
    return rule.get("scaleXZ") or [1.0, 1.0]


def crown_of(d, kind, prefab, h, iso=False):
    """据えたあとの樹冠径[m]。目録に無ければ None(=**測れていない**。合格ではない)。

    ⭐ **2026-09-08 十六巡目 中6(庭方)** ── **樹冠 = 部材の素の樹冠 × `scaleXZ`** の一本に
    揃えた(松がもともとこの形)。⛔ 旧 `crownPerH`(樹冠÷丈)は落とした ── 同じ量に二つの
    宣言を置かない(規則4)。⚠ 引数 `h` は `sizeRule` が選んだ変種を通じてのみ効く。
    ⚠ 旧宣言が残っていれば**そちらを優先して**返す(⛔ 黙って二重にしない — 検査が止める)。
    """
    rule = d["planting"]["scaleRule"].get(kind) or {}
    cph = rule.get("crownPerH")
    if cph is not None:
        lo, hi = _h_pair(h)
        if lo is None: return None
        return (cph * lo, cph * hi)
    g0 = part_geom({"prefab": prefab})
    if g0 is None: return None
    xz = layer_xz(d, kind, iso)
    return (g0[0] * xz[0], g0[0] * xz[1])


def crown_scale_xz(d, kind, prefab, h, iso=False):
    """その木に掛かる **`scaleXZ`(範囲の中央)**。⛔ json に個体の数を置かない(規則4)。

    実装(棟梁)が使うのはこの倍率。⭐ 2026-09-08 以後は `scaleRule[kind].scaleXZ`
    (孤立木は `isolatedXZ`)そのもので、⛔ 部材の素の樹冠からの逆算ではない。
    """
    if part_geom({"prefab": prefab}) is None: return None
    xz = layer_xz(d, kind, iso)
    return (xz[0] + xz[1]) / 2.0


# ---------------------------------------------------------------- 退避(木を植えない所)
def _pt_seg(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz)


def _seg_cross(a, b, c, e):
    """線分 a→b と c→e の交点(**パラメタ付き**)。交わらなければ None。戻り (点, t, u)。

    ⚠ `_seg_x` とは別物 — あちらは点だけを返す(交差の有無を見る用)。こちらは交点が
    それぞれの折れ線の**端か途中か**を判じるために t / u が要る(検図11巡目 中1)。
    """
    d1 = (b[0] - a[0], b[1] - a[1]); d2 = (e[0] - c[0], e[1] - c[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12: return None
    t = ((c[0] - a[0]) * d2[1] - (c[1] - a[1]) * d2[0]) / den
    u = ((c[0] - a[0]) * d1[1] - (c[1] - a[1]) * d1[0]) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return ((a[0] + d1[0] * t, a[1] + d1[1] * t), t, u)
    return None


def _seg_seg_dist(a, b, c, e):
    """線分どうしの最小距離[間]。交われば 0。"""
    if _seg_cross(a, b, c, e): return 0.0
    return min(_pt_seg(a, c, e), _pt_seg(b, c, e), _pt_seg(c, a, b), _pt_seg(e, a, b))


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


def _shape_disc(c, r, nm):
    """点まわりの円。**折れ線の内側の節の丸み**にだけ使う(⛔ 端には付けない)。"""
    return ("disc", (c[0], c[1]), r, nm, (c[0] - r, c[1] - r, c[0] + r, c[1] + r))


def _band_chain(pts, r, nm):
    """折れ線に沿う帯 ── **内側の節にだけ丸みを付ける**。⛔ 端の二つには付けない。

    ⭐ **2026-09-08 十六巡目 A-5(庭方)**。`_shape_band` は `0≤t≤1` の区間でしか当たらないので、
    折れ線が折れる**節の外側に楔形の穴**が開き、女坂の頭の喉で 幹が敷きの半幅の内側(芯から横
    2.07 m)に立っていた。⛔ 節の丸みを落としたまま「端にキャップを付けない」で済ませない。
    ⚠ **端の二つはこれまで通りキャップ無し**(2026-09-06c 裁定3・庭方)── あれは
    「坂の**両側**を空ける」趣旨で、**坂の端から先へ張り出さない**ための決めであり、
    折れ線の**内側の節**までは及ばない(男坂の上端が楼門を・下端が仁王門を呑む話である)。
    """
    out = [_shape_band(pts[i], pts[i + 1], r, nm) for i in range(len(pts) - 1)]
    out += [_shape_disc(pts[i], r, nm) for i in range(1, len(pts) - 1)]
    return out


def _shape_poly(P, m, nm):
    """多角形 + 余白 m。**設計された塊の箱を走査面から落とす**のに使う(2026-09-08 A-3)。"""
    us = [q[0] for q in P]; vs = [q[1] for q in P]
    return ("poly", [(q[0], q[1]) for q in P], m, nm,
            (min(us) - m, min(vs) - m, max(us) + m, max(vs) + m))


def _pt_line_t(p, a, b):
    """点から**直線**への距離と、線分上の助変数 t(クランプしない)。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    if L2 < 1e-12: return math.hypot(p[0] - a[0], p[1] - a[1]), 0.0
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz), t


def band_shoulder(d, lay=None):
    """帯1〜3 の石段の**肩**[間]。層ごとの宣言 `bandDef.avoid.kaidanShoulderKen` を引く。

    ⭐ **2026-09-08 に層ごとへ刻んだ**【裁き1 庭方】── 低木 0.5 ／ 中木 1.0 ／ 高木 1.5 間。
    旧式は一本の指し先(腰石垣からの離れ)を全層へ当てており、石段の両側に**下草だけの縁**を
    残す一方で**高木の根株は擁壁の上まで寄れた**。⛔ 数をここに書かない(json が正典)。
    `lay=None` は**最も大きい肩**(=高木)を返す — 層を渡し忘れた側が甘い面を得ないため。
    """
    sh = ((d["planting"].get("bandDef") or {}).get("avoid") or {}).get("kaidanShoulderKen") or {}
    if not sh: return None
    return sh.get(lay) if lay else max(sh.values())


def kattemichi_shoulder(d, lay=None):
    """**勝手道の肩**[間]。⛔ 石段の `kaidanShoulderKen` を借りない
    【高1 庭方 2026-09-09 十七巡目 → `bandDef.avoid.kattemichiShoulderKen`】。

    ⚠ 肩の根拠は『**幹の根が擁壁を押さない**』で、⭕ **勝手道は土の小径・擁壁が無い**。
      石段の肩(高木 1.5 間)を借りていたので、九十九折で隣の脚の退避が融合して**島が消え**、
      南面に幅 10〜17 m の裸の斜め筋(1,043 m²・最大内接半径 8.7 m)が残った。
    ⛔ 宣言が無ければ**石段の肩へ落ちない** ── None を返し、検査が⛔で止める(規則19)。
    """
    sh = ((d["planting"].get("bandDef") or {}).get("avoid") or {}).get("kattemichiShoulderKen")
    if not sh: return None
    return sh.get(lay) if lay else max(sh.values())


def kyoukai_shoulder(d, lay=None):
    """**社地の境からの幹の離れ**[間]【中5 庭方 2026-09-09 十七巡目 → `avoid.kyoukaiKen`】。

    ⛔ 林縁(`rinen`)とは別物 ── 林縁は『道に接する辺だけ』の意匠で、こちらは**全周**に効く。
    ⚠ 宣言が無かったので幹が境界線に乗っていた(実測 最短 松 0.09 m ／ 中木 0.03 ／ 低木 0.00 m)。
    """
    sh = ((d["planting"].get("bandDef") or {}).get("avoid") or {}).get("kyoukaiKen")
    if not sh: return None
    return sh.get(lay) if lay else max(sh.values())


def kyoukai_avoid_shapes(d, g, sh_ken):
    """**社地の境 `polygon` の内側 `sh_ken`[間] の帯**(幹を退ける面)。⛔ 数を持たない。

    ⭕ **樹冠は境の外へ張り出してよい** ── 退けるのは幹だけ(`plantRule.crownRule` と同じ物差し)。
    """
    if not sh_ken: return []
    P = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    out = []
    for i in range(len(P)):
        out.append(_shape_band(P[i], P[(i + 1) % len(P)], sh_ken, "社地の境:辺%d" % i))
    return out


def max_takagi_crown_r(d):
    """**当図に現れる高木(松・落葉)の樹冠の半径の最大**[m]。無ければ None(=測れていない)。

    ⭐ 帯を架ける(石段の上で樹冠が触れる)条件はこの量で測る【高3 庭方 2026-09-09 十七巡目】。
    ⛔ 数を json に持たない — 部材の素の樹冠 × `scaleRule.<層>.scaleXZ` の上限からの従属値。
    """
    ws = []
    for lay, key in (("松", "matsu"), ("落葉", "rakuyo")):
        xz = (d["planting"]["scaleRule"].get(key) or {}).get("scaleXZ") or [1.0, 1.0]
        for pf in (used_prefabs(d).get(lay) or set()):
            g0 = part_geom({"prefab": pf})
            if g0: ws.append(g0[0] * max(xz))
    return (max(ws) / 2.0) if ws else None


def near_takagi_crown_r(d, g, k):
    """**その石段に差し掛かる高木**の樹冠の半径の最大[m](焼き出しの点から測る)。

    ⭐ 「差し掛かる」= 樹冠が**敷きの縁に届く**(幹から芯線への距離 ≤ 敷きの半幅 + 樹冠の半径)。
    ⛔ 図の全体の最大で代表させない ── 男坂の脇は `viewClusters` の宣言により**松だけ**で、
      林の他所に大きな落葉が在ることは男坂の帯を架ける理由にならない(高3 庭方 2026-09-09)。
    無ければ None(= 差し掛かる高木が一本も無い)。
    """
    if not os.path.exists(IMPL_OUT): return None
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    P = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
    W = [g.W(u, v) for u, v in P]
    hw = kaidan_wken(d, k) / 2.0 * d["const"]["ken"]
    best = None
    for q in ((im.get("planting") or {}).get("points") or []):
        if q.get("layer") not in ("松", "落葉") or not q.get("crownM") or not q.get("world"):
            continue
        r9 = q["crownM"] / 2.0
        dd = min(_pt_seg((q["world"][0], q["world"][1]), W[i], W[i + 1])
                 for i in range(len(W) - 1))
        if dd <= hw + r9 and (best is None or r9 > best): best = r9
    return best


def min_matsu_crown_r(d):
    """**当図に現れる最も細い松の樹冠の半径**[m]。無ければ None(=測れていない)。

    ⭐ 肩(高木)の**上限**を決めるのはこの量である【裁き1 庭方 2026-09-08】── 肩がこれを越えると
    最も細い松でも樹冠が笠石の上へ届かず、男坂が**林を割る溝**になる。⛔ 数を json に持たない
    (部材の素の樹冠 × `scaleRule.matsu.scaleXZ` の下限からの従属値)。
    """
    xz = (d["planting"]["scaleRule"].get("matsu") or {}).get("scaleXZ") or [1.0, 1.0]
    ws = []
    for pf in (used_prefabs(d).get("松") or set()):
        g0 = part_geom({"prefab": pf})
        if g0: ws.append(g0[0] * min(xz))
    return (min(ws) / 2.0) if ws else None


def avoid_shapes(d, g, scope):
    """**退避の宣言から障害物の buffer を組み立てる。**⛔ ここに数を書かない — 宣言が正典。

    scope="keidai" … 境内の立木3区に効く(`planting.clearance.keidai`)
    scope="zentei" … 前庭の面(帯・供待・点景)に効く(`planting.clearance.zentei`)
    scope="obi4"   … 社叢 帯4 に効く(**多角形を持つ帯**の `avoid`)
    scope="obi123:<層>" … 社叢 帯1〜3 に効く(`planting.bandDef.avoid` ── 三本で共通の規約なので
                     ⛔ 帯ごとに写さない。帯の側は `avoidFrom` で指し先だけを持つ)。
                     ⭐ **肩は層ごと**なので面も層ごとに違う(2026-09-08 裁き1)

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
            out += _band_chain(pts, rr, "石段:" + k["name"])   # ⭐ 内側の節に丸み(A-5)
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
            out += _band_chain(pts, rr, "石段:" + k["name"])   # ⭐ 内側の節に丸み(A-5)
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
    if scope.startswith("obi123"):
        # ⭐ **帯1〜3 の石段の退避**(2026-09-08)。⛔ 数を持たない ──
        #    芯からの半径 = 石段の敷きの半幅(`kaidans[].wKen`/2)+ **その層の肩**。
        # ⭐ **肩は層ごと**【裁き1 庭方 2026-09-08】── `scope` は "obi123:<層>"。
        #    ⛔ 層を省いた呼び方は**最も大きい肩**(=高木)で代表する — 層を渡し忘れた側が
        #    黙って甘い面を得る道を作らない。
        sh = band_shoulder(d, scope.partition(":")[2] or None)
        if sh is None: return []
        for k in d["kaidans"]:
            rr = kaidan_wken(d, k) / 2.0 + sh
            pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
            out += _band_chain(pts, rr, "石段:" + k["name"])   # ⭐ 内側の節に丸み(A-5)
        # ⭐ **勝手道・囲い・土留め・塊の箱**(2026-09-08 十六巡目 A-1/A-3/B-4・庭方)
        #    ⛔ 数はどれも宣言からの従属値(`kattemichiRule` / `kakoiRule` / `clusterRule`)
        av123 = d["planting"]["bandDef"]["avoid"]
        lay9 = scope.partition(":")[2] or None
        # ⭐ **勝手道の肩は石段とは別の宣言**【高1 庭方 2026-09-09 十七巡目】
        if av123.get("kattemichiRule"):
            out += kattemichi_apron_shapes(d, g, kattemichi_shoulder(d, lay9) or 0.0)
        if av123.get("kakoiRule"): out += kakoi_avoid_shapes(d, sh)
        # ⭐ **社地の境からの幹の離れ**(全周)【中5 庭方 2026-09-09 十七巡目】
        if av123.get("kyoukaiRule"):
            out += kyoukai_avoid_shapes(d, g, kyoukai_shoulder(d, lay9))
        # ⛔ **塊の箱はここへ入れない** — 塊の本数は既に帯から差し引いてあるので、面まで引くと
        #    二重に引くことになる(⛔ 本数の配り方は変えない・庭方 A-3)。落とすのは
        #    **撒くときの候補セル**だけで、それは `scatter_pts` が `cluster_keepout_shapes` で行う。
        return out
    # ⚠ **多角形を持つ帯**(帯4)の宣言を採る ── ⛔ 「最初に `avoid` を持つ帯」で拾わない
    #    (帯1〜3 が指し先を持った日に、帯4 の額縁が黙って入れ替わる)
    av = [b["avoid"] for b in d["slopeBands"] if b.get("avoid") and b.get("uv")][0]
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
    # ⭐ **柵と塊の箱**(2026-09-08 十六巡目 B-4/A-3)。⛔ **前庭の縁の土留め・板塀は外す** ──
    #    帯4 は上の `zenteiFromEdge`/`zenteiFromEdgeEast` で同じ縁を測っている(⛔ 二重に効かせない)
    av4 = d["planting"]["bandDef"]["avoid"]
    sh4 = band_shoulder(d, "松")
    if av4.get("kakoiRule") and sh4 is not None:
        out += kakoi_avoid_shapes(d, sh4, skip_zentei=True)
    # ⭐ **社地の境からの幹の離れ**(全周)【中5 庭方 2026-09-09 十七巡目】。⚠ 帯4 は層で
    #    分けない額縁の宣言だが、境の離れは**層ごと**なので最も大きい肩(高木)で代表させる
    #    ── ⛔ 甘い側へ倒さない。
    if av4.get("kyoukaiRule"):
        out += kyoukai_avoid_shapes(d, g, kyoukai_shoulder(d, "松"))
    # ⛔ 塊の箱はここへ入れない(理由は obi123 と同じ)── `scatter_pts` が候補から落とす
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
        elif sh[0] == "disc":
            # ⭐ **折れ線の内側の節の丸み**(2026-09-08 A-5)
            if math.hypot(p[0] - sh[1][0], p[1] - sh[1][1]) < sh[2]: return sh[-2]
        elif sh[0] == "poly":
            # ⭐ **塊の箱 + 余白**(2026-09-08 A-3)。内か、辺から余白の内か
            Q = sh[1]
            if in_poly(p, Q): return sh[-2]
            if sh[2] > 0.0 and min(_pt_seg(p, Q[i], Q[(i + 1) % len(Q)])
                                   for i in range(len(Q))) < sh[2]: return sh[-2]
        elif _pt_seg(p, sh[1], sh[2]) < sh[3]:
            return sh[-2]
    return None


# **焼き出しの `u`/`v` の丸めの幅**[間](`_tree_row` は 4 桁で丸める ≒ 0.18 mm)。
# ⛔ **設計の余裕ではない** — 図が走査に使う生の座標と、焼き出しへ書いた丸めた座標の差である。
# ⚠ 2026-09-09 に起こした: 生の走査点は退避の**外**(0.250006 間)にあるのに、丸めた 0.2500 が
#   内側へ落ちて⛔が立ち、0.1 mm の丸めで『幹が境界線に乗っている』と報告した。
BAKE_ROUND_KEN = 1e-4


def _shrink_shape(sh, eps):
    """退避の形を `eps`[間] だけ**内側へ縮める**(丸めの幅を吸うため)。"""
    if sh[0] == "rect":
        return ("rect", sh[1] + eps, sh[2] + eps, sh[3] - eps, sh[4] - eps) + tuple(sh[5:])
    if sh[0] in ("seg", "band"):
        return (sh[0], sh[1], sh[2], sh[3] - eps) + tuple(sh[4:])
    if sh[0] in ("disc", "poly"):
        return (sh[0], sh[1], sh[2] - eps) + tuple(sh[3:])
    return sh


def shape_hit_baked(p, shapes):
    """**焼き出しの点**(丸めた `u`/`v`)を退避に当てる。⛔ 丸めの幅ぶん内側で判定する。

    ⛔ **余裕を広げない** ── `BAKE_ROUND_KEN` は丸めの幅そのもので、設計値ではない。
    ⛔ 生の走査点(`scatter_pts` の候補)には使わない — あちらは丸めていない。
    """
    return shape_hit(p, [_shrink_shape(q, BAKE_ROUND_KEN) for q in shapes])


def deref(d, path):
    """`"planting.plantRule.crownRule.chuboku.koshiIshigakiFromTrunkKen"` の形の指し先を引く。

    ⛔ **数を二重に持たないための道具**(規則4)── 宣言が別の宣言を指すとき、指図に数を写さず
    ここで引く。指し先が無ければ None(= **未測定**。合格ではない)。
    """
    q = d
    for k in (path or "").split("."):
        if not isinstance(q, dict) or k not in q: return None
        q = q[k]
    return q


def kaidan_apron_shapes(d):
    """石段の**敷き**(踏面の帯)。⛔ 端にキャップを付けない(2026-09-06c 裁定3・庭方)。

    ⭐ 2026-09-08 ── 帯1〜3 は石段の敷きを一度も見ておらず、**踏面の上に木が立っていた**。
    敷きの半幅は `kaidans[].wKen` からの従属値で、⛔ 数を別に持たない。
    """
    out = []
    for k in d["kaidans"]:
        hw = kaidan_wken(d, k) / 2.0
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        out += _band_chain(pts, hw, "石段:" + k["name"])       # ⭐ 内側の節に丸み(A-5)
    return out


def kattemichi_apron_shapes(d, g, sh_ken=0.0):
    """**勝手道の敷き(+ 層の肩)**。⛔ 数を持たない — `kattemichi[].w` と肩の宣言からの従属値。

    ⭐ **2026-09-08 十六巡目 A-1(庭方)。**`avoid_shapes(…, "obi123:<層>")` が見ていたのは
    `d["kaidans"]` だけで、**勝手道(西・東、幅 `w`)が退避に一つも入っていなかった** ──
    芯からの最短 0.01 m、松でも 0.38 m で、⛔ **動線図が道として描く九十九折が木で塞がっていた**。
    ⛔ 端にキャップは付けない・**内側の節には丸みを付ける**(`_band_chain`)。
    """
    out = []
    ken = d["const"]["ken"]
    for k in d.get("kattemichi", []):
        pts = [(g.U(x), g.V(z)) for x, z in k["pts"]]
        if len(pts) < 2: continue
        out += _band_chain(pts, k["w"] / 2.0 / ken + sh_ken, "勝手道:" + k["name"])
    return out


def kakoi_avoid_shapes(d, sh_ken, skip_zentei=False):
    """**柵・板塀・土留めの線 + その層の肩**。⛔ 厚みを発明しない(宣言があるのは柵の柱だけ)。

    ⭐ **2026-09-08 十六巡目 B-4(庭方)。**幹が柵・土留めに当たっていた(`Saku_Sando` に8本・
    最短 0.09 m ／ `Ita_Keidai` に22本 ／ `TW_Zentei_E` に5本)── 10〜12 m の松の幹は径
    0.3〜0.4 m あるので ⛔ **柵はそこに建たない**。
    `skip_zentei=True` は**前庭の縁の土留め**を外す ── 帯4 は `avoid.zenteiFromEdge` /
    `zenteiFromEdgeEast` という**別の宣言**(庭方 中-2 の緩め)で同じ縁を測っているので、
    ⛔ 二重に効かせて裁定済みの意匠を黙って上書きしない。
    """
    out = []
    ken = d["const"]["ken"]
    post = 0.0
    for gd in d["gardens"]:
        tg = gd.get("tamagaki")
        if tg and tg.get("postDiaM"): post = max(post, tg["postDiaM"] / 2.0 / ken)
    for r in d["runs"]:
        if r.get("kind") not in ("柵", "板塀"): continue
        if skip_zentei and r["name"].startswith("Ita_Z"): continue
        # ⛔ **生成前の run を測らない** — `Ita_Keidai`/`Saku_SW` は `derive_runs` が形を入れる
        if not r.get("pts") and (r.get("a") is None or r.get("b") is None): continue
        half = post if r.get("kind") == "柵" else 0.0
        for a, b in run_segs(r):
            out.append(_shape_band(a, b, half + sh_ken, r.get("kind") + ":" + r["name"]))
    for w in d.get("terraceWalls", []):
        if skip_zentei and w["name"].startswith("TW_Zentei"): continue
        pts = [tuple(q) for q in (w.get("pts") or [w.get("a"), w.get("b")])]
        if any(q is None for q in pts) or len(pts) < 2: continue
        out += _band_chain(pts, sh_ken, "土留め:" + w["name"])
    return out


def cluster_keepout_shapes(d):
    """**設計された塊の箱 + 芯々 × `packRatio` の余白**。⛔ 帯の走査面から落とすための形。

    ⭐ **2026-09-08 十六巡目 A-3(庭方)。**`view_cluster_cut` は塊のぶんの**本数**を帯から
    引くが、**箱を走査面から落としていなかった** ── 『男坂の見切り』(額縁・設計6本)へ帯から
    24 本が撒き込み、⛔ **『主景は一点』を測る見込み角がもう額縁を測っていなかった**。
    ⛔ 本数の配り方は変えない(引くのは面であって密度ではない)。
    ⚠ **『変えない』が当たるのは総数だけ**【低3 検図21巡目 → 2026-09-09】── 面が縮むと
      層ごとの整数配分(`_apportion`)の丸めが動くので、⛔ **層の割り前は 1〜十数本ずれる**。
      ⭕ 検図の再現でも旧の松の本数は再現しなかった(原因は帯3 林縁の再配分と塊の
      `n` → `nFrom` 化)。⛔ 「層の内訳まで不変」と読ませない。
    """
    pack = d["planting"]["plantRule"]["packRatio"]
    out = []
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            sp = cluster_spacing(d, c)
            m = (sp or 0.0) * pack
            for Q in cluster_polys(c):
                out.append(_shape_poly(Q, m, "塊:" + c["name"]))
    return out


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
# 帯に撒く層。⛔ 綴りは `planting.parts` と `bandDef.avoid.layers` の鍵そのもの
_LAYS = ("松", "落葉", "中木", "低木")


def band_scan(d, g):
    """**帯1〜3の面を走査する**(`planting.bandDef` の規約)。⛔ 面積も本数も定数で持たない。

    法肩 = 平場の天端、法尻 = 社地の境(東〜北東は帯4の西縁)。各セルで
    t = (天端 − 現地形h) / (天端 − 最寄りの法尻のh) を出し、帯の `from`/`to` で切る。
    ⭐ **2026-09-08 ── `exclude` が名指しする石段の敷きを落とす。**旧式は男坂・女坂の踏面を
    帯の面に数えており、そこへ密度どおりに木が撒かれていた(⛔ 0 件は合格ではなく未測定)。
    敷きの分は `_BANDS["kai"]` に別に数え、**不変条件①の和に足す**(社地は 平場+前庭+帯+敷き で閉じる)。
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
    # ⭐ **石段の敷き**は `bandDef.exclude` の宣言で落とす(⛔ 生成器に焼き込まない)。
    #    宣言を外すと踏面が帯の面へ戻り、検査『植栽の面と退避』が鳴る(規則19)。
    kai_sh = kaidan_apron_shapes(d) if any("石段" in q for q in (bd.get("exclude") or [])) else []
    cells = {1: [], 2: [], 3: []}
    kai_n = [0]
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
                # ⭐ **敷きのセルは帯の面から落とし、不変条件①の第五の部分に数える。**
                #    ⛔ **『橋として渡す』細工は 2026-09-09 十八巡目に廃した**【決3 庭方】──
                #    帯ごとの連結を測ること自体が誤りだったので、橋も要らなくなった。
                if kai_sh and shape_hit(p, kai_sh):
                    kai_n[0] += 1
                else:
                    cells[b["band"]].append(p)
                break
        else:
            skip += 1
    _BANDS["cells"], _BANDS["skip"] = cells, skip
    _BANDS["kai"] = kai_n[0]           # 不変条件①の第五の部分(石段の敷き)
    return cells, skip


# 「**接する**」の数値の許容[間]。⛔ **設計値ではない** — 丸めの幅(≒18 mm)。
_TOUCH_KEN = 0.01


def rinen_areas(d, g, b):
    """林縁が『接するか』を測る**相手の道敷**(uv の多角形の列)。⛔ 辺の番号を書かない。"""
    src = (b.get("rinen") or {}).get("areasFrom") or []
    out = []
    for s in src:
        if s.startswith("fumotomichi"):
            out += [[(g.U(x), g.V(z)) for x, z in f["area"]]
                    for f in d.get("fumotomichi", []) if f.get("area")]
        elif s.startswith("sando"):
            if d.get("sando", {}).get("area"):
                out.append([(g.U(x), g.V(z)) for x, z in d["sando"]["area"]])
    return out


def rinen_edge_idx(d, g, b):
    """帯の**林縁が距離を測る社地の辺**を**番号つき**で返す [(i, a, b)]。

    ⭐ **同定は『辺の中点と両三分点がすべて道敷から `rinenEdgeTouchKen` 以内』**
    【中4 庭方 2026-09-09 十七巡目 → `bandDef.rinenEdgeRule`】。
    ⚠ **旧式は辺を11点に刻んで一点でも触れれば採っていた**ので、⛔ **頂点で触れるだけの辺**を
      拾った ── 帯3 の林縁が『道に接しない2辺』(東の境 110 m・南西の境 83 m)へ掛かり、
      **幅 2.73 m の高木の空白が 193 m 続いていた**(帯3 自身の註と矛盾)。
    ⛔ 宣言(`rinen.edgeFrom` / `areasFrom`)が無ければ**社地の境の全部**を返す。
    """
    soch = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    E = [(i, soch[i], soch[(i + 1) % len(soch)]) for i in range(len(soch))]
    ef = (b.get("rinen") or {}).get("edgeFrom")
    if not ef: return E
    areas = rinen_areas(d, g, b)
    tol = (d["planting"]["bandDef"].get("rinenEdgeTouchKen") or _TOUCH_KEN)
    out = []
    for i, a, b_ in E:
        for Q in areas:
            ok = True
            for t in (1.0 / 3.0, 0.5, 2.0 / 3.0):        # ⛔ 端点は見ない(頂点接触を落とす)
                p = (a[0] + (b_[0] - a[0]) * t, a[1] + (b_[1] - a[1]) * t)
                dd = 0.0 if in_poly(p, Q) else min(_pt_seg(p, Q[j], Q[(j + 1) % len(Q)])
                                                   for j in range(len(Q)))
                if dd > tol: ok = False; break
            if ok: out.append((i, a, b_)); break
    return out


def rinen_edges(d, g, b):
    """`rinen_edge_idx` の辺だけ(番号を落とした形)。⛔ 同定の式を二つ持たない。"""
    return [(a, b_) for _i, a, b_ in rinen_edge_idx(d, g, b)]


_RLAY = {"松": "takagi", "落葉": "takagi", "中木": "chuboku", "低木": "teiboku"}


def rinen_tiers(b):
    """林縁の**段**【④ 庭方 2026-09-09 十七巡目】。⛔ 宣言が無ければ一段(`rinen` そのもの)。

    ⚠ **林縁は独立の密度を持つ**(帯の `teibokuPer100` の範囲では二段に割れない — 実測で
      林縁 5.64 本/100 m² 対 帯の本体 4.90 の 15% 増、丈も 2.16 対 2.15 でほぼ同じだった)。
    """
    rin = b.get("rinen") or {}
    if not rin: return []
    ts = rin.get("tiers")
    if not ts: return [{"name": "一段", "fromKen": rin.get("fromKen", 0.0),
                        "toKen": rin["toKen"]}]
    return list(ts)


def _rinen_pick(d, b, t, lay, suffix):
    """段 → 林縁 → 帯 の順に宣言を引く(⛔ 段が持たない量は上位へ落ちる)。"""
    rin = b.get("rinen") or {}
    k = _RLAY[lay] + suffix
    for src in ([t, rin] if t is not rin else [rin]):
        if src.get(k) is not None: return src[k]
        fr = src.get(k + "From")
        if fr and "上端" in fr:
            q = b.get(k)
            return [q[1], q[1]] if isinstance(q, (list, tuple)) else q
        if fr and ("本体" in fr or "帯の" in fr):
            return b.get(k)
    return None


def rinen_dens_t(d, b, t, lay):
    """段 `t` の林縁の密度[本/100 m²]。⛔ 数を作らない。"""
    v = _rinen_pick(d, b, t, lay, "Per100")
    if v is None: return None
    return (v[0] + v[1]) / 2.0 if isinstance(v, (list, tuple)) else float(v)


def rinen_h_t(d, b, t, lay):
    """段 `t` の林縁の丈[lo,hi]。⛔ 新しい丈を作らない。"""
    return _rinen_pick(d, b, t, lay, "H")


def rinen_dens(d, b, lay):
    """林縁**全段**の平均の密度[本/100 m²](表と旧来の呼び出しのため)。"""
    ts = rinen_tiers(b)
    vs = [rinen_dens_t(d, b, t, lay) for t in ts]
    vs = [q for q in vs if q is not None]
    return (sum(vs) / len(vs)) if vs else None


def rinen_range_t(b, t, lay):
    """段 `t` にとっての範囲 (内, 外)[間]。⛔ 高木は段に分けない(林縁の全幅で 0 本)。"""
    rin = b.get("rinen") or {}
    if not rin: return None
    if lay in ("松", "落葉"): return (0.0, rin["toKen"])
    return (t["fromKen"], t["toKen"])


def rinen_range(b, lay):
    """層 `lay` にとっての林縁の帯の**全体**の範囲 (内, 外)[間]。⛔ 数を作らない。

    ⭐ **高木は境から `toKen` まで一本も置かない**(⛔ `fromKen` の内側も含む)── `fromKen` は
    **下層を撒き始める線**(内側は柵の帯 `sando.roadside.west.sakuKen`)であって、
    高木の境ではない。⚠ 旧図は高木を 0〜`fromKen` の 0.5 間へ落としており、
    社地の境から 0.09 m に松が立っていた(2026-09-08 十六巡目 A-4・庭方)。
    """
    rin = b.get("rinen") or {}
    if not rin: return None
    ts = rinen_tiers(b)
    if lay in ("松", "落葉") or not ts: return (0.0 if lay in ("松", "落葉")
                                                else rin["fromKen"], rin["toKen"])
    return (min(t["fromKen"] for t in ts), max(t["toKen"] for t in ts))


_RDECL = (("松", "takagiPer100", "matsuH"), ("落葉", "rakuyoRatio", "rakuyoH"),
          ("中木", "chubokuPer100", "chubokuH"), ("低木", "teibokuPer100", "teibokuH"))


def rinen_decl_rows(d, b):
    """林縁の宣言を**段ごとに**、`slopeBands` と同じ鍵の形で返す [(銘, 宣言の辞書)]。

    ⭐ **④ 庭方 2026-09-09 十七巡目で林縁が二段になった。**⛔ 段の宣言を検査が見落とす道を
      塞ぐ ── 密度と丈の対の照合・樹種の頭打ち・落葉の丈の順序は、**段ごとに**当てる
      (旧版は `b["rinen"]` の平らな鍵しか見ておらず、段へ移した瞬間に黙る・規則19)。
    """
    rin = b.get("rinen") or {}
    if not rin: return []
    ts = rinen_tiers(b)
    out = []
    for t in ts:
        o = {}
        for lay, dk, hk in _RDECL:
            if lay in ("松", "落葉"):
                if rin.get(dk) is not None: o[dk] = rin[dk]
                if rin.get(hk) is not None: o[hk] = rin[hk]
                continue
            dv = rinen_dens_t(d, b, t, lay)
            hv = rinen_h_t(d, b, t, lay)
            if dv is not None: o[dk] = dv
            if hv is not None: o[hk] = hv
        out.append(("の林縁の帯(%s)" % t.get("name") if len(ts) > 1 else "の林縁の帯", o))
    return out


def rinen_h(d, b, lay):
    """林縁**全段**を包む丈[lo,hi](表と旧来の呼び出しのため)。⛔ 新しい丈を作らない。"""
    hs = [rinen_h_t(d, b, t, lay) for t in rinen_tiers(b)]
    hs = [q for q in hs if q]
    if not hs: return None
    return [min(q[0] for q in hs), max(q[1] for q in hs)]


def band_density(b):
    """採用密度[本/100m²]。`takagiAdopted` があればそれ、無ければ `takagiPer100` の中央。"""
    if b.get("takagiAdopted"): return b["takagiAdopted"]
    r = b.get("takagiPer100") or [0, 0]
    return (r[0] + r[1]) / 2.0


_VCUT = {"fall": []}


def view_cluster_cut(d, g):
    """視線が決める塊(`planting.viewClusters`)の本数を、箱の中心が落ちる帯から差し引く。

    ⭐ **落ちなかった箱は記録する**【低3 検図15巡目 → 2026-09-08】── 旧式は既定で
    「セル数最大の帯」へ**黙って落として**おり、`avoid` や敷きを動かした日に本数が黙って移った。
    ⛔ 黙って移す道を塞ぐ ── 検査『塊が塊として組めるか』が ⛔ で止める。
    """
    cells, _ = band_scan(d, g)
    own = {}
    for k, ps in cells.items():
        for p in ps: own[(round(p[0] * 2), round(p[1] * 2))] = k
    cut = {1: 0, 2: 0, 3: 0}
    _VCUT["fall"], _VCUT["on"] = [], []
    for c in d["planting"].get("viewClusters", []):
        bx = cluster_boxes(c)
        per = cluster_n(c) / max(1, len(bx))
        for j, (u0, v0, u1, v1) in enumerate(bx):
            cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
            k = own.get((round(cu * 2), round(cv * 2)))
            if k is None:
                k = min(cut, key=lambda q: -len(cells[q]))
                _VCUT["fall"].append((c["name"], j + 1, k, per))
            else:
                _VCUT["on"].append((c["name"], j + 1, k, per))
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
            tot = av = 0
            rin = b.get("rinen") or {}
            E = rinen_edges(d, g, b) if rin else []
            dds = []
            for p in poly_scan(P, st):
                tot += 1
                if shape_hit(p, sh): av += 1; continue
                # ⭐ **林縁は帯の中の小領域**(2026-09-08 十六巡目 A-4)── ⛔ 有効面から落とし、
                #    層ごとに別の密度と丈で撒く。⛔ 高木は林縁へ一本も入れない。
                if rin and E: dds.append(min(_pt_seg(p, q[0], q[1]) for q in E))
            # ⭐ 帯の中に**位置を決めて据える一本立ち**があれば、密度から出した本数から差し引く
            #    (視線が決める塊と同じ扱い。2026-09-06 庭方 A-3b の門被りの松)
            row = {"b": b, "tsubo": tot * c2, "avoid": av * c2,
                   "cut": float(len(b.get("singles", []))),
                   "usableBy": {}, "avoidBy": {}, "rinenBy": {}}
            # ⚠ 帯4 の退避は**額縁**(見え掛かり)の宣言なので層で分けない ── ⛔ 帯1〜3 の
            #    層ごとの肩をここへ写さない(測っている物が違う)。
            #    ⭐ **林縁の範囲だけは層で違う**(高木は境から `toKen` まで全部・A-4)
            row["rinenTier"] = {}
            for k in _LAYS:
                rg = rinen_range(b, k)
                rn = sum(1 for q in dds if rg[0] <= q <= rg[1]) if rg else 0
                row["avoidBy"][k] = av * c2
                row["rinenBy"][k] = rn * c2
                row["usableBy"][k] = (tot - av - rn) * c2
                # ⭐ **段ごとの面**(④ 庭方 2026-09-09)── ⛔ 合算だけを持たない
                for ti, t in enumerate(rinen_tiers(b)):
                    rgt = rinen_range_t(b, t, k)
                    row["rinenTier"][(ti, k)] = (
                        sum(1 for q in dds if rgt[0] <= q <= rgt[1]) * c2) if rgt else 0.0
            row["usable"], row["rinen"] = row["usableBy"]["松"], row["rinenBy"]["松"]
        else:
            # ⭐ **2026-09-08 ── 帯1〜3 も退避を引く。**旧式は `avoid` が 0 坪 固定で、
            #    石段の脇の肩がまるごと有効面に入っていた(⛔ 0 は合格ではなく未測定)。
            # ⭐ **退避は層ごとに違う**【裁き1 庭方 2026-09-08】── 肩が 低木 0.5 / 中木 1.0 /
            #    高木 1.5 間 と刻まれたので、有効面も層ごとに出す。⛔ 一つの `usable` で
            #    三層を代表させない(高木の不足と低木の過剰は**逆向き**の欠陥である)。
            ps = cells[b["band"]]
            row = {"b": b, "tsubo": len(ps) * ct, "rinen": 0.0,
                   "cut": cut.get(b["band"], 0.0), "usableBy": {}, "avoidBy": {},
                   "rinenBy": {}}
            # ⭐ **林縁は帯の中の小領域**(2026-09-08 十六巡目 C-2)── 帯3 の南面がこれ。
            rin = b.get("rinen") or {}
            E = rinen_edges(d, g, b) if rin else []
            dmap = {}
            if rin and E:
                for p in ps: dmap[p] = min(_pt_seg(p, q[0], q[1]) for q in E)
            row["rinenTier"] = {}
            for lay in _LAYS:
                sh = avoid_shapes(d, g, "obi123:" + lay)
                hit = set(p for p in ps if shape_hit(p, sh)) if sh else set()
                rg = rinen_range(b, lay)
                inrin = set(p for p, q in dmap.items() if rg[0] <= q <= rg[1]) if rg else set()
                rn = sum(1 for p in inrin if p not in hit)
                row["avoidBy"][lay] = len(hit) * ct
                row["rinenBy"][lay] = rn * ct
                row["usableBy"][lay] = (len(ps) - len(hit) - rn) * ct
                for ti, t in enumerate(rinen_tiers(b)):
                    rgt = rinen_range_t(b, t, lay)
                    row["rinenTier"][(ti, lay)] = (
                        len([p for p, q in dmap.items()
                             if rgt[0] <= q <= rgt[1] and p not in hit]) * ct) if rgt else 0.0
            # ⚠ 素の `avoid`/`usable` は**高木**の値(表と検査が層ごとに刷る)
            row["avoid"], row["usable"] = row["avoidBy"]["松"], row["usableBy"]["松"]
            row["rinen"] = row["rinenBy"]["松"]
        row["dens"] = band_density(b)
        row["takagi"] = row["usableBy"]["松"] * TSUBO * row["dens"] / 100.0 - row["cut"]
        row["rakuyo"] = row["takagi"] * (b.get("rakuyoRatio") or 0.0)
        for k, key, lay in (("chuboku", "chubokuPer100", "中木"),
                            ("teiboku", "teibokuPer100", "低木")):
            r = b.get(key) or [0, 0]
            row[k] = row["usableBy"][lay] * TSUBO * (r[0] + r[1]) / 2.0 / 100.0
            # ⭐ **林縁の本数は独立の行**(2026-09-08 十六巡目 C-2)── ⛔ 帯の本体の行へ混ぜない
            #    (混ぜたら誰も見ない = 旧の状態)。密度は `rinen` の宣言か帯の上端の従属値。
            # ⭐ **段ごとに別の密度**(④ 庭方 2026-09-09 十七巡目)── ⛔ 合算の密度で掛けない
            nr9 = 0.0
            for ti, t in enumerate(rinen_tiers(b)):
                dr = rinen_dens_t(d, b, t, lay)
                if not dr: continue
                nr9 += (row.get("rinenTier") or {}).get((ti, lay), 0.0) * TSUBO * dr / 100.0
            row[k + "Rinen"] = nr9
        _BSTAT.append(row)
    _BSTAT.append({"skip": skip * ct})
    return _BSTAT


def _band_layer_n(b, lay):
    """帯 `b` の層 `lay` に**何本撒くか**。`band_stats` の走査が済んでいなければ None。

    ⭐ 2026-09-07 九巡目 中3 ── 検査に「その行が何本の木を代表しているか」を持たせるため。
    ⛔ 数を json に持たない(密度と有効面からの従属値)。
    """
    # ⚠ **同一性だけで引かない**【2026-09-08】── 生成器は json を**二度**読む(検査の巡と
    #    図を組む巡)ので、`_BSTAT` に載っている帯の辞書は図を組む側の辞書と**別の物**である。
    #    ⛔ `is` だけで引くと図の側で黙って None が返り、銘から本数だけが落ちる
    #    (0 件ではなく『測っていない』の形・規則19)。⇒ 帯の番号で引き当てる。
    bn = b.get("band")
    for r in _BSTAT:
        rb = r.get("b")
        if rb is not b and not (bn is not None and (rb or {}).get("band") == bn): continue
        if lay == "松": return r["takagi"] - r["rakuyo"]
        return r.get({"落葉": "rakuyo", "中木": "chuboku", "低木": "teiboku"}.get(lay))
    return None


def _rinen_layer_n(b, rin, lay="低木"):
    """**林縁の帯**に撒く層 `lay` の本数。⛔ 帯の本体の数で代用しない(面も密度も別)。

    ⭐ 2026-09-08 十六巡目 ── 中木も返す(⛔ **低木だけの縁にしない**・庭方 C-2)。
    ⚠ **帯の番号で引き当てる**(⛔ `is` だけで引かない ── 生成器は json を二度読む)。
    """
    bn = b.get("band")
    for r in _BSTAT:
        rb = r.get("b")
        if rb is not b and not (bn is not None and (rb or {}).get("band") == bn): continue
        return r.get({"中木": "chubokuRinen", "低木": "teibokuRinen"}.get(lay), 0.0)
    return None


def band_components(d, g):
    """帯1〜3の**連結成分**の坪数(大きい順)。0.5 間のセルの4近傍で繋ぐ。

    ⚠ **2026-09-09 十八巡目から、これは〔記録〕であって合否ではない**【決3 庭方】──
    不変条件③ は『社叢ぜんぶの木の最大の連結成分』(`shaso_components`)へ移った。
    ⛔ 帯は**密度の処方**であって物体ではないので、帯ごとに連結を測ると細い環は必ず割れる。
    """
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


def shaso_components(d, g):
    """**社叢ぜんぶの木**の連結成分(本数・大きい順)【決3 庭方 2026-09-09 十八巡目】。

    ⭕ 木と木は**樹冠が触れ合えば繋がっている**(芯々 ≤ 半径の和)。⛔ 面(セル)で測らない ──
      林が一つに繋がっているかは**木と木の間**の話である。
    ⚠ 測る層は `bandDef.invariants.shasoCompLayers`(低木は林冠を作らないので入れない)。
    戻り (成分の本数の列, 全本数)。焼き出しが無ければ ([], 0)。
    """
    if not os.path.exists(IMPL_OUT): return ([], 0)
    lay = set((d["planting"]["bandDef"]["invariants"].get("shasoCompLayers") or []))
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    T = [(q["world"][0], q["world"][1], q["crownM"] / 2.0)
         for q in ((im.get("planting") or {}).get("points") or [])
         if q.get("layer") in lay and q.get("crownM") and q.get("world")]
    n = len(T)
    if not n: return ([], 0)
    # ⭐ 格子で近傍だけ見る(総当たりは 879² で遅い)。格子の目は最大の樹冠の直径。
    rmax = max(q[2] for q in T)
    cell = max(rmax * 2.0, 1.0)
    grid = {}
    for i, (x, z, r) in enumerate(T):
        grid.setdefault((int(x // cell), int(z // cell)), []).append(i)
    par = list(range(n))

    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for i, (x, z, r) in enumerate(T):
        cx, cz = int(x // cell), int(z // cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in grid.get((cx + dx, cz + dz), []):
                    if j <= i: continue
                    x2, z2, r2 = T[j]
                    if (x - x2) ** 2 + (z - z2) ** 2 <= (r + r2) ** 2:
                        a, b = find(i), find(j)
                        if a != b: par[a] = b
    cnt = {}
    for i in range(n): cnt[find(i)] = cnt.get(find(i), 0) + 1
    return (sorted(cnt.values(), reverse=True), n)


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
    # ⭐ **石段の敷きは第五の部分**(2026-09-08)── `bandDef.exclude` が帯から落とした分。
    #    ⛔ 和から落とすと社地に閉じない(帯の面が痩せた分だけ差が開く)。
    kai = _BANDS.get("kai", 0) * cell_tsubo(d, d["planting"]["bandDef"]["stepKen"])
    tot = sum(ts.values()) + kei + zen + kai
    dv = tot / soc * 100.0 - 100.0
    out = [("①", "帯1+帯2+帯3+帯4+平場+前庭+**石段の敷き** = 社地の面積(±%g%%)" % iv["sumTolPct"],
            "%s 坪(うち石段の敷き %s 坪)／ 社地 %s 坪 ／ 差 %+.2f%%"
            % (format(int(round(tot)), ","), format(int(round(kai)), ","),
               format(int(round(soc)), ","), dv),
            abs(dv) <= iv["sumTolPct"], True)]
    ok2 = ts.get(1, 0) < ts.get(2, 0) < ts.get(3, 0)
    out.append(("②", "帯1 < 帯2 < 帯3(下るほど広い)",
                " < ".join("帯%d %s 坪" % (b, format(int(round(ts.get(b, 0))), ",")) for b in (1, 2, 3)),
                ok2, True))
    # ③ ⭐ **2026-09-09 十八巡目に『帯ごと』から『社叢ぜんぶ』へ移した**【決3 庭方】──
    #    帯1 は法肩を巻く細い環なので**単体では必ず割れる**(帯という密度の処方を物体として
    #    測っていた)。⛔ 帯ごとの成分は〔記録〕として刷り続ける(⛔ 測るのをやめない)。
    comps = band_components(d, g)
    sc, sn = shaso_components(d, g)
    lim3 = iv["shasoMaxCompPct"]
    if sn:
        r3 = sc[0] * 100.0 / sn
        got3 = ("最大の成分 **%d / %d 本 = %.1f%%**(成分の数 %d ／ 次は %s)"
                "　〔記録〕帯ごとの成分(⛔ 合否ではない): %s"
                % (sc[0], sn, r3, len(sc),
                   "・".join(str(q) for q in sc[1:5]) or "無し",
                   "／".join("帯%d %d 個・最大 %.0f%%"
                             % (b, len(comps[b]),
                                (max(comps[b]) / sum(comps[b]) * 100.0) if comps[b] else 0.0)
                             for b in sorted(comps))))
        ok3 = r3 >= lim3
    else:
        got3, ok3 = "焼き出しが無いので測れていない(⛔ 0 は合格ではなく未測定)", False
    out.append(("③", "**社叢ぜんぶ**(%s)の最大の連結成分が全本数の %g%% 以上"
                "(= 林が一つに繋がっている)" % ("・".join(iv.get("shasoCompLayers") or []), lim3),
                got3, ok3, True))
    return out


def band_invariant_check(d, g):
    """⛔ 組む条件にした不変条件が破れていたら組ませない(2026-09-06 から①②③の三つとも)。

    ⭐ **2026-09-09 十八巡目に③の猶予は消えた**【決3 庭方】── 物差しが『帯ごと』から
      『社叢ぜんぶ』へ移り、⛔ **猶予で凌いでいた条項そのものが誤りだった**ことが判った。
    """
    bad, note = [], []
    for i, cl, got, ok, gate in band_invariants(d, g):
        if ok:
            note.append("不変条件 %s ⭕ — %s(%s)【算出】" % (i, cl, got)); continue
        msg = "社叢の帯の不変条件 %s が破れている — %s(%s)" % (i, cl, got)
        (bad if gate else note).append(msg if gate else ("⚠ " + msg + "【算出 — 猶予の内。"
                                                        "⛔ 受入値を下げて黙らせない】"))
    return bad, note


# ---------------------------------------------------------------- 境内の立木3区
_MIXRE = re.compile(r"(松|欅|椋|榎)\s*(\d+)")
_MIXSP = {"欅": "ケヤキ", "椋": "ムクノキ", "榎": "エノキ"}


def cluster_mix(c):
    """塊の `mix`(「松4・欅1」)を [(種, 本数)] へ。⛔ 本数を二重に持たない。"""
    return [(k, int(n)) for k, n in _MIXRE.findall(c.get("mix") or "")]


def zone_h(d, gd):
    """区の松・落葉高木の丈[m]。

    区(`gardens`)は `hBand` の帯から引き、**帯そのもの(`slopeBands`)は自分の宣言を使う**。
    ⚠ 2026-09-07 八巡目 中3 ── 旧式は `hBand` しか見ず、帯4の塊(辻の留め)は
    **部材・丈・樹冠の欄が丸ごと刷られなかった**(いちばん混んだ塊だけが黙っていた)。
    """
    if gd.get("matsuH") or gd.get("rakuyoH"):
        return gd.get("matsuH"), gd.get("rakuyoH")
    b = [q for q in d["slopeBands"] if q["band"] == gd.get("hBand")]
    if not b: return None, None
    return b[0].get("matsuH"), b[0].get("rakuyoH")


def cluster_parts(d, gd, c):
    """塊の部材 — `mix` の割り前 × `planting.parts` の palette。

    戻り (種, palette の点, 本数, 丈, 樹冠, 層の鍵, 変種の列, scaleY 下, scaleY 上)。
    ⭐ **大きさ(変種)は名指しでなく `sizeRule` が丈から選ぶ**(2026-09-07 裁定1)。
    帯の丈は範囲なので、同じ樹種でも丈で変種が変わる — 現れる変種は**全部**返す。
    """
    pal = d["planting"]["parts"]
    mH, rH = zone_h(d, gd)
    # ⭐ **塊が棟高からの下限を宣言していれば松の丈の下端を上げる**
    #    【中8 庭方 2026-09-09 十七巡目 / 書き方は裁4】── ⛔ 数を持たない。
    # ⭐ **上端を部材の箍まで開く塊がある**【決5 庭方 2026-09-09 十八巡目】── ⛔ 帯の `matsuH`
    #    の上端で切ると 4 本が全部その一つの値へ張り付き、棟に対して横一線の『生垣』になる。
    #    上端 = `sizeRule.speciesHCap`(その樹種の最大変種の素の丈 × `scaleYMax`)。⛔ 数を持たない。
    if c.get("matsuHMaxFrom") and mH:
        caps = [q for q in (species_h_cap(d, pt) for pt in pal["松"]) if q]
        if caps:
            a9, b9 = _h_pair(mH)
            mH = [a9, max(b9, max(caps))]
    mf = c.get("matsuHMinFrom")
    if mf and mH:
        m9 = ([q for q in d["munes"] if q["name"] == mf.get("mune")] or [None])[0]
        h9 = mune_h(d, m9) if m9 else None
        if h9 is not None:
            lo9 = h9 * float(mf.get("factor") or 1.0)
            a9, b9 = _h_pair(mH)
            # ⛔ **上端は越えない** ── 越えるなら帯の丈の宣言と衝突しているということで、
            #    検査『塊の松の丈の下限(棟高からの従属)』が⛔で名指しする(⛔ 黙って伸ばさない)。
            if a9 is not None: mH = [min(max(a9, lo9), b9), b9]
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
            vs, ylo, yhi = pick_variants_over(d, pt, h)
            pf = vs[0][1] if vs else pt.get("prefab")
            out.append((kind, pt, k, h, crown_of(d, sk, pf, h), sk, vs, ylo, yhi))
    return out


_CPH_KEY = {"落葉": "rakuyo", "中木": "chuboku"}


# 樹冠 ÷ 丈 の照合の**丸めの幅**。⛔ **設計値ではない** — 焼き出しが小数3桁で丸めた分。
_CPH_TOL = 0.001


def is_named_group(gn):
    """焼き出しの群の名が**名指しの木**(位置を意匠が決めた木)か。⛔ 物差しは一本だけ。

    ⭐ 一本立ち(`gardens[].singles`)／ 差し掛け(`planting.sashikake`)／
      名指しの木(`planting.namedTrees`)／ **★主景**(`gardens[].shukei.tree`)。
    ⛔ **判定を写さない**【規則4】── ⚠ 十九巡目まで同じ条件が二箇所に別々に書かれており、
      A-1 で ★主景 が名指しの木へ移ったとき**片方だけが取り残された**。
    """
    gn = gn or ""
    return (gn.endswith("(一本立ち)") or gn.startswith("差し掛け(")
            or gn.startswith("名指しの木(") or gn.startswith("★主景("))


def crown_per_h_check(d, g):
    """**社叢の中の 樹冠 ÷ 丈 の上限**【低9/低10 庭方 2026-09-09 十七巡目】。

    ⛔ **旧 `crownPerH`(樹冠を丈から作る規約)の復活ではない** ── 樹冠は
      `部材の素の樹冠 × scaleXZ` から出る(規則4)。ここが測るのは**上限**だけである。
    ⛔ **一本立ち・`isolatedCrown` の塊には当てない** ── 孤立木は開いた形が正しい。
    ⛔ 密度は動かさない(低10)。始末は `_pending`「社叢の落葉と中木の 樹冠 ÷ 丈 の超過」へ。
    """
    if not os.path.exists(IMPL_OUT): return ([], [])
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    sr = d["planting"]["scaleRule"]
    bad, note = [], []
    # 一本立ち・差し掛け・`isolatedCrown` の塊の群は測らない(⛔ 孤立木の形は別)
    iso = set()
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            if c.get("isolatedCrown"): iso.add("%s／%s" % (gd["name"], c["name"]))
    for lay, key in sorted(_CPH_KEY.items()):
        cap = (sr.get(key) or {}).get("crownPerHMax")
        if cap is None:
            bad.append("`scaleRule.%s.crownPerHMax`(社叢の中の 樹冠 ÷ 丈 の上限)の宣言が無い — "
                       "⛔ 宣言の無い縛りは必ず破られる(規則19)" % key)
            continue
        rows = []
        for q in ((im.get("planting") or {}).get("points") or []):
            if q.get("layer") != lay or not q.get("crownM") or not q.get("h"): continue
            gn = q.get("group") or ""
            # ⛔ **孤立木は上限の対象外**【指3 庭方 2026-09-09 十八巡目】── 一本立ち・差し掛け・
            #    名指しの木・`isolatedCrown` の塊。⚠ 十七巡目はここで名簿を取り違え、
            #    **上限の対象でない 7 本を『超過』に数えていた**(⛔ 規則19 の欠陥)。
            if is_named_group(gn) or gn in iso: continue
            rows.append((q["crownM"] / float(q["h"]), q))
        if not rows:
            note.append("%s の 樹冠 ÷ 丈 ── 測れる点が 0(⛔ 0 件は合格ではなく未測定)【算出】"
                        % lay)
            continue
        # ⛔ **丸めの幅**(⛔ 設計値ではない)── 焼き出しの `crownM`/`h` は小数3桁で丸めて
        #    あるので、⛔ 1e-9 で当てると**頭打ちちょうどの個体**が全部『超過』に化ける。
        over = [q for q in rows if q[0] > cap + _CPH_TOL]
        rs = sorted(r[0] for r in rows)
        if over:
            sp9 = {}
            for r9, q9 in over: sp9[q9.get("species")] = sp9.get(q9.get("species"), 0) + 1
            m9 = ("%s の **樹冠 ÷ 丈 が上限 %.2f を超える点 %d / %d 本**(最大 %.2f・"
                  "樹種の内訳 %s)— ⛔ 上限を上げて黙らせない・⛔ 密度を動かして逃げない"
                  "(低9/低10 庭方 2026-09-09)"
                  % (lay, cap, len(over), len(rows), max(r[0] for r in over),
                     "・".join("%s %d" % (k9, v9) for k9, v9 in sorted(sp9.items()))))
            pr9 = (sr.get(key) or {}).get("crownPerHMaxPendingRef")
            if pr9 and pr9 in (d.get("_pending") or {}):
                note.append("⚠ " + m9 + "。⭕ **猶予**『%s』の内(当たり先は庭方・部材方)【算出】"
                            % pr9)
            else:
                bad.append(m9)
        note.append("%s の 樹冠 ÷ 丈 ── 中央 **%.2f** ／ 最大 **%.2f** ／ 上限 %.2f ／ "
                    "超過 **%d / %d 本**(⛔ 一本立ち・差し掛け・名指しの木・`isolatedCrown` の塊は"
                    "測らない ── "
                    "孤立木は開いた形が正しい)【算出 — 低9/低10 庭方 2026-09-09。⛔ 0 件は"
                    "合格ではなく未測定】"
                    % (lay, rs[len(rs) // 2], rs[-1], cap, len(over), len(rows)))
    return bad, note


def single_gap_roster(d, g):
    """`planting.singleGapRoster` が名指しする木 [(名, (u,v), 樹冠の半径[間])]。

    ⭐ **役が『一本で立つこと』である木だけ**【指2③ 庭方 2026-09-09 十八巡目】── ⛔ 一本立ちを
      総当たりしない(役の違う対を偽の⛔で埋め、役の同じ対を見落とす)。
    ⚠ 指し先は `gardens:<区>/<名>` か `slopeBands:<帯>/<塊>(この塊の松)`。
    """
    ros = d["planting"].get("singleGapRoster") or []
    out = []
    pts = []
    if os.path.exists(IMPL_OUT):
        im = json.load(open(IMPL_OUT, encoding="utf-8"))
        pts = (im.get("planting") or {}).get("points") or []
    ken = d["const"]["ken"]
    for r in ros:
        nm = r.split("/", 1)[-1]
        base = nm.split("(")[0].strip()
        hit = [q for q in pts if q.get("name") == base or
               (q.get("name", "").startswith(base + " ") and q.get("layer") == "松")]
        if not hit: out.append((r, None, None)); continue
        for q in hit:
            out.append((q["name"], (q["u"], q["v"]),
                        (q["crownM"] / 2.0 / ken) if q.get("crownM") else None))
    return out


def single_gap_check(d, g):
    """**役が『一本で立つ』木どうしが対に見えないか**(奇数の作法)【指2 庭方 十八巡目】。

    ⛔ 受入値は**従属値** `planting.singleGapFrom`(二本の樹冠の半径の和 + 1.0 間)── ⛔ 平値の
      10 間は撤回された(庭方が置いた数で根拠が無かった)。
    ⛔ 効かせる相手は `singleGapRoster` の名簿だけ。⛔ 名簿を増やすのは意匠(庭方)。
    〔記録〕名簿に無い一本立ちの最も近い対も**刷り続ける**(⛔ 測らないのと求めないを混ぜない)。
    """
    pl = d["planting"]
    if not pl.get("singleGapFrom") or not pl.get("singleGapRoster"):
        return (["`planting.singleGapFrom` / `singleGapRoster`(一本立ちの離れの物差しと名簿)の"
                 "宣言が無い — ⛔ 宣言の無い縛りは必ず破られる(規則19)"], [])
    ken = d["const"]["ken"]
    R = single_gap_roster(d, g)
    bad, note = [], []
    miss = [q[0] for q in R if q[1] is None]
    if miss:
        bad.append("`singleGapRoster` の『%s』が焼き出しに見当たらない — **死んだポインタ**"
                   "(⛔ 名簿が図に届いていない・規則19)" % "』『".join(miss))
    P = [q for q in R if q[1] is not None]
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            (a9, pa, ra), (b9, pb, rb) = P[i], P[j]
            if ra is None or rb is None:
                bad.append("『%s』か『%s』の樹冠が引けない — 受入値(樹冠の半径の和 + 1 間)が"
                           "測れない(⛔ 0 は合格ではなく未測定)" % (a9, b9)); continue
            dd = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            lim = ra + rb + 1.0
            if dd < lim - 1e-9:
                bad.append("『%s』と『%s』が **%.2f 間 = %.2f m** しか離れておらず、"
                           "受入値 **%.2f 間**(樹冠の半径の和 %.2f + 1.0 間)を割る — "
                           "⛔ **紙の上でだけ違う二つの役が、現物では一つの頭に潰れている**"
                           "(⛔ 受入値を下げて黙らせない ── 離すか片方を落とすかは意匠)"
                           % (a9, b9, dd, dd * ken, lim, ra + rb))
            else:
                note.append("『%s』×『%s』── 芯々 **%.2f 間 = %.2f m** ≥ 受入値 %.2f 間"
                            "(樹冠の半径の和 %.2f + 1.0 間)【算出 — 指2 庭方 2026-09-09 十八巡目。"
                            "⛔ 数を json に書かない】" % (a9, b9, dd, dd * ken, lim, ra + rb))
    if len(P) < 2:
        note.append("名簿の木が **%d 本**なので対が作れない【算出】" % len(P))
    # 〔記録〕**名簿の外**の一本立ちも刷る(⛔『測らない』と『求めない』を混ぜない・規則19)
    S = []
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            S.append((sg.get("layer"), sg["name"], tuple(sg["uv"])))
    for lay in sorted(set(q[0] for q in S)):
        Q = [q for q in S if q[0] == lay]
        pr = [(math.hypot(Q[i][2][0] - Q[j][2][0], Q[i][2][1] - Q[j][2][1]), Q[i][1], Q[j][1])
              for i in range(len(Q)) for j in range(i + 1, len(Q))]
        if not pr:
            note.append("一本立ち『%s』%d 本 ── 対が作れない【算出】" % (lay, len(Q))); continue
        pr.sort()
        note.append("〔名簿の外〕一本立ち『%s』%d 本 ── 最も近い対 **%.2f 間 = %.2f m**"
                    "(『%s』×『%s』)。⛔ **受入値の対象ではない**(役が『一本で立つこと』では"
                    "ないため・指2③ 庭方 2026-09-09)が、⛔ 測るのはやめない【算出】"
                    % (lay, len(Q), pr[0][0], pr[0][0] * ken, pr[0][1], pr[0][2]))
    return bad, note


def cluster_hmin_check(d):
    """**塊の松の丈の下限(棟高からの従属)が帯の丈に納まるか**【中8 庭方 2026-09-09 十七巡目】。

    ⛔ 役が『棟の背後の背景』である塊は、⛔ **棟に競ってはならない**ので下限を棟高から起こす。
    ⚠ **棟高は部材の丈からの従属値**(裁4)なので、⛔ **部材が変われば下限も動く** ──
      下限が帯の丈の上端を越えたら、それは『棟が高くなりすぎた』か『帯の丈が低すぎる』かで、
      ⛔ **どちらを直すかは意匠**である(⛔ 指図方が黙って伸ばさない/縮めない)。
    """
    bad, note = [], []
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            mf = c.get("matsuHMinFrom")
            if not mf: continue
            m9 = ([q for q in d["munes"] if q["name"] == mf.get("mune")] or [None])[0]
            if m9 is None:
                bad.append("塊『%s』の `matsuHMinFrom.mune`『%s』が引けない — **死んだポインタ**"
                           % (c["name"], mf.get("mune"))); continue
            h9 = mune_h(d, m9)
            if h9 is None:
                bad.append("塊『%s』の下限が引けない — 棟『%s』の棟高が引けない"
                           "(`h` も `partFrom` も無い/目録に無い)" % (c["name"], m9["name"]))
                continue
            lo9 = h9 * float(mf.get("factor") or 1.0)
            mH, _rH = zone_h(d, gd)
            a9, b9 = _h_pair(mH)
            if b9 is None: continue
            # ⭐ **上端を開けた塊はその上端で測る**【決5 庭方 2026-09-09 十八巡目】
            if c.get("matsuHMaxFrom"):
                caps = [q for q in (species_h_cap(d, pt)
                                    for pt in d["planting"]["parts"]["松"]) if q]
                if caps:
                    b0 = b9
                    b9 = max(b9, max(caps))
                    note.append("塊『%s』の松の**上端を部材の箍まで開いた** ── 区の `matsuH` の"
                                "上端 %.2f m → **%.2f m**(`sizeRule.speciesHCap` = 最大変種の"
                                "素の丈 × `scaleYMax`)【算出 — 決5 庭方 2026-09-09 十八巡目。"
                                "⛔ 数を json に書かない。⛔ 他の区・帯には当てない】"
                                % (c["name"], b0, b9))
            msg = ("塊『%s』の松の丈の下限 **%.2f m**(= 棟『%s』の棟高 %.2f m × %g)が、"
                   "区の `matsuH` の上端 %.2f m を**越える**" % (c["name"], lo9, m9["name"],
                                                                h9, mf.get("factor"), b9))
            if lo9 > b9 + 1e-9:
                pr9 = mf.get("pendingRef")
                if pr9 and pr9 in (d.get("_pending") or {}):
                    note.append("⚠ " + msg + "。⭕ **猶予**『%s』の内(⛔ 下限を下げて"
                                "黙らせない ── 当たり先は庭方)。図は上端で頭打ちにして刷る"
                                "【算出】" % pr9)
                else:
                    bad.append(msg + " — ⛔ 下限を下げて黙らせない(⛔ 帯の丈を伸ばすのも意匠)")
            else:
                note.append("塊『%s』の松 ── 丈 **%.2f〜%.2f m**(下限は棟『%s』の棟高 %.2f m × "
                            "%g からの従属値)【算出 — ⛔ 数を json に書かない。⚠ 部材方が屋根を"
                            "作り直しているので、棟が変われば下限も追随する】"
                            % (c["name"], max(a9 or 0.0, lo9), b9, m9["name"], h9,
                               mf.get("factor")))
    return bad, note


def cluster_part_label(pt, vs):
    """部材の刷り名 ── 雛形なら**丈の範囲に現れる変種を全部**並べる。"""
    if not vs: return pt.get("prefab") or "—", pt.get("api") or "—"
    if len(vs) == 1: return vs[0][1], vs[0][2]
    base = (pt.get("prefab") or "").replace(_SIZE_HOLE, "")
    return ("%s〔%s〕" % (base.rstrip("_"), "/".join(q[0] for q in vs)),
            "%s〔%s〕" % ((pt.get("api") or "").split("(")[0], "/".join(q[0] for q in vs)))


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
    # ⛔ **層ごとにその層の丈を渡す**【中2 庭方 2026-09-07 八巡目】── 旧式は落葉の行にも
    #    `matsuH[1]` を渡していた。害が出なかったのは落葉の樹冠が丈と無関係だった間だけで、
    #    `rakuyo.crownPerH`(裁定1)が入った瞬間に**落葉の樹冠が丈13の値で刷られる**。
    for kind, key, hkey in (("matsu", "松", "matsuH"), ("rakuyo", "落葉", "rakuyoH")):
        hh = (b4.get(hkey) or [0, 0])[1]
        for pt in d["planting"]["parts"][key]:
            q = pick_variant(d, pt, hh)
            cr = crown_of(d, kind, (q[1] if q else pt.get("prefab")), hh)
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


def sando_edge_uv(d):
    """**社地の境**のうち参道に面する辺(`takagiEdgeLine.fromEdge`)を uv の線分で。"""
    tl = (d["sando"].get("roadside") or {}).get("takagiEdgeLine") or {}
    if not tl.get("fromEdge"): return None
    return edge_offset(d, tl["fromEdge"], 0.0)


def sando_far_edge(d):
    """参道の道敷 `sando.area` のうち**社地の境の向かい側の縁**(觀理院の西縁)。

    ⛔ 辺の番号を書かない(検図の作法)── **社地の境の辺と最も平行な辺**を幾何で同定する
    (その辺自身は端点の一致で除く)。戻り (世界座標の2点)。
    """
    ar = d["sando"].get("area")
    tl = (d["sando"].get("roadside") or {}).get("takagiEdgeLine") or {}
    if not ar or not tl.get("fromEdge"): return None
    a, b = d["polygon"][tl["fromEdge"][0]], d["polygon"][tl["fromEdge"][1]]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    best = None
    for k in range(len(ar)):
        p, q = ar[k], ar[(k + 1) % len(ar)]
        ex, ez = q[0] - p[0], q[1] - p[1]
        le = math.hypot(ex, ez)
        if le < 1e-6: continue
        if min(math.hypot(p[0] - a[0], p[1] - a[1]), math.hypot(q[0] - a[0], q[1] - a[1]),
               math.hypot(p[0] - b[0], p[1] - b[1]), math.hypot(q[0] - b[0], q[1] - b[1])) < 0.3:
            continue                                   # 社地の境の辺そのもの
        dot = abs((ex * dx + ez * dz) / (le * L))
        if best is None or dot > best[0]: best = (dot, p, q)
    return None if best is None else (best[1], best[2])


def sando_road_width(d, v):
    """**局所の道敷幅[m]** ── 社地の境の v の点から、向かいの縁の**直線**までの垂距。

    ⚠ 楔形の区間は道敷の幅が場所で変わる。⛔ 代表値(最も狭い東西の帯の値)を当てない。
    """
    eg = sando_edge_uv(d)
    fe = sando_far_edge(d)
    if eg is None or fe is None: return None
    (au, av), (bu, bv) = eg
    if abs(bv - av) < 1e-9: return None
    t = (v - av) / (bv - av)
    g = G(d)
    px, pz = g.W(au + t * (bu - au), v)
    (e0, e1) = fe
    ex, ez = e1[0] - e0[0], e1[1] - e0[1]
    le = math.hypot(ex, ez) or 1.0
    return abs((px - e0[0]) * ez - (pz - e0[1]) * ex) / le


def sando_rokata(d, v):
    """局所の (路肩[m], 路肩+側溝[m])。`rokataRule` の従属値。⛔ 数を json に持たない。"""
    rs = d["sando"].get("roadside") or {}
    W_ = sando_road_width(d, v)
    if W_ is None or rs.get("roadWidth") is None or rs.get("sokkoKen") is None: return None
    sk = rs["sokkoKen"] * d["const"]["ken"]
    ro = (W_ - rs["roadWidth"] - 2.0 * sk) / 2.0
    return (ro, ro + sk)


def overhang_limit(d, c):
    """林縁の塊の **張り出しの上限[m]** = 局所の(路肩+側溝)− `marginM`。

    ⭐ 2026-09-07 八巡目 裁定2 ── ⛔ **上だけを置く**(下限は置かない)。
    戻り [(v, 上限)] を塊の `vRange` の両端で。
    """
    oh = c.get("overhangFrom") or {}
    mg = oh.get("marginM")
    vr = c.get("vRange")
    if mg is None or not vr: return []
    out = []
    for v in (vr[0], vr[1]):
        q = sando_rokata(d, v)
        if q is None: continue
        out.append((v, q[1] - mg, q[0], q[1]))
    return out


# ---------------------------------------------------------------- 見所と主景
def shukei_hmin(d, sk):
    """★主景の木の**丈の下限**[m]。⛔ 数を json に持たない(`tree.hMinFrom` の従属値)。

    ⭐ **2026-09-08 に従属値へ移した**【A-2 の裁き 庭方】── 旧値 18.0 m は部材と箍では届かない
    丈で、`scaleY` が `sizeRule.scaleYMax` を超えていた(⛔ 松で閉じたのと同じ欠陥)。
    **落葉高木の最も高い変種の素の丈 × `sizeRule.scaleYMax`** = 箍の内で出せる最も高い丈。
    ⛔ 部材を新造しない・⛔ 箍を上げない。引けなければ None(= 測れていない)。
    """
    if not (sk.get("tree") or {}).get("hMinFrom"): return None
    cap = (size_rule(d) or {}).get("scaleYMax")
    hs = [q[3] for pt in d["planting"]["parts"].get("落葉", []) for q in part_variants(d, pt)]
    if not hs or cap is None: return None
    return max(hs) * cap


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
        hm = shukei_hmin(d, sk)         # ⛔ 数を json から読まない(2026-09-08 A-2)
        if hm is None:
            out.append(("★主景の木(%s)" % sk["tree"]["kind"], None, None, None)); continue
        top = gr + hm
        out.append(("★主景の木(%s 丈 %.1f m 以上【従属 — 落葉の最も高い変種 × 箍】)"
                    % (sk["tree"]["kind"], hm),
                    L, top, math.degrees(math.atan2(top - eye, L))))
        for nm in sk.get("munes", []):
            m = [q for q in d["munes"] if q["name"] == nm]
            # ⭐ **棟高は `mune_h`**(宣言 `h` か `partFrom` の指す目録の丈)【裁3/裁4 2026-09-09】
            h9 = mune_h(d, m[0]) if m else None
            if h9 is None:
                out.append((nm + " の棟(⛔ 棟高が引けない — `h` も `partFrom` も無い/目録に無い)",
                            None, None, None)); continue
            m = m[0]
            cu, cv = m["u0"] + m["du"] / 2.0, m["v0"] + m["dv"] / 2.0
            L2 = math.hypot(cu - fu, cv - fv) * ken
            t2 = gr + h9
            out.append((nm + " の棟(丈 %.1f m【従属 — %s】)"
                        % (h9, "宣言 `h`" if m.get("h") is not None else "目録の部材の丈"),
                        L2, t2, math.degrees(math.atan2(t2 - eye, L2))))
    return out


# 方位の語 → 真北からの角[°](時計回り・世界 +Z=北 / +X=東)。⛔ 設計値ではない — 語の辞書。
_DIR_DEG = {"北": 0.0, "北北東": 22.5, "北東": 45.0, "東北東": 67.5, "東": 90.0,
            "東南東": 112.5, "南東": 135.0, "南南東": 157.5, "南": 180.0,
            "南南西": 202.5, "南西": 225.0, "西南西": 247.5, "西": 270.0,
            "西北西": 292.5, "北西": 315.0, "北北西": 337.5}


def _azim(du, dv):
    """uv の向きの**真北からの角**[°]。当社のグリッドは u=東+ / v=北+(世界軸そのもの)。"""
    return math.degrees(math.atan2(du, dv)) % 360.0


def viewpoint_eye(d, g, vp):
    """見所の**眼高**[m]とその出所。⛔ 数を json に持たない(規則4)。

    ⭐ **設計地盤(平場があれば平場・無ければ現地形)+ 座面高 + `eyeOver`**
    (2026-09-06 検図5巡目 低15 — 旧版は現地形しか見ず、V2/V-Z1/V-Z3 は `eye` に
    `terraces[1].y + eyeOver` を書き写して二重に持っていた)。
    """
    u, v = vp["uv"]
    if vp.get("eye") is not None: return vp["eye"], "設計値"
    h = design_y(d, g, *g.W(u, v))
    base = "設計地盤" if h is not None else "現地形"
    if h is None: h = dem_h(*g.W(u, v))
    seat = 0.0
    if vp.get("seatOn"):
        _k, _, _nm = vp["seatOn"].partition(":")
        for _p in d.get(_k, []):
            if _p.get("name") == _nm: seat = (_p.get("plan") or {}).get("seatH", 0.0)
    return ((h or 0.0) + seat + vp.get("eyeOver", 0.0),
            "%s %.2f m%s + %.2f m" % (base, h or 0.0,
                                      " + 座面 %.2f m" % seat if seat else "",
                                      vp.get("eyeOver", 0.0)))


def viewpoint_target(d, vp):
    """見所が**見ている先**の (u,v) と出所。`shows` の対象の芯 → 無ければ None。"""
    for nm in vp.get("shows", []):
        if nm.startswith("★主景"):
            for gd in d["gardens"]:
                sk = gd.get("shukei")
                if sk and sk.get("tree", {}).get("uv"):
                    return tuple(sk["tree"]["uv"]), "shows:★主景の木"
            continue
        for holder in d["gardens"] + d["slopeBands"] + [d["planting"]]:
            for c in holder.get("clusters", []) + holder.get("viewClusters", []):
                if c["name"] != nm: continue
                Q = [p for P_ in cluster_polys(c) for p in P_]
                if not Q: continue
                return ((sum(q[0] for q in Q) / len(Q), sum(q[1] for q in Q) / len(Q)),
                        "shows:" + nm)
    return None, None


def derive_viewpoints(d, g):
    """見所の **`eyeH`(眼高)と `look`(向き)を起こす**【B-3 庭方 2026-09-08 十六巡目】。

    ⛔ **数を json に置かない**(規則4)── 焼き出しが持つのは算出値である。
    ⚠ 旧図は焼き出しの `eyeH`/`look` が両方 `null` で、⛔ **検証レンダを図の見所に合わせられなかった**
    (規則19)。⚠ **算出すると `dir` の散文と食い違う点が出る** — ⛔ 黙って `dir` を書き換えない
    (向きは庭方の意匠)。食い違いは検査が毎回刷る。
    """
    for vp in d.get("viewpoints", []):
        eye, src = viewpoint_eye(d, g, vp)
        vp["eyeH"] = round(eye, 3)
        vp["_eyeFrom"] = src
        tgt, tsrc = viewpoint_target(d, vp)
        tu, tv = tgt if tgt else (None, None)
        dd = _DIR_DEG.get(vp.get("dir") or "")
        if tu is not None:
            az = _azim(tu - vp["uv"][0], tv - vp["uv"][1])
            frm = tsrc
        elif dd is not None:
            az, frm = dd, "dir:" + vp["dir"]
        else:
            vp["look"] = None
            continue
        vp["look"] = {"azDeg": round(az, 2), "from": frm,
                      "world": [round(math.sin(math.radians(az)), 4),
                                round(math.cos(math.radians(az)), 4)],
                      "_": "**真北からの角**[°](時計回り)。`world` は世界の (x, z) の単位ベクトル"}
        vp["_dirDeg"] = dd


def viewpoint_rows(d, g):
    """見所 V1〜V3 — 眼高(従属)と、`shows` に挙げた塊の見込み角[°]。"""
    ken = d["const"]["ken"]
    rows = []
    for vp in d.get("viewpoints", []):
        u, v = vp["uv"]
        eye, src = viewpoint_eye(d, g, vp)
        shows = []
        for nm in vp.get("shows", []):
            for holder in d["gardens"] + d["slopeBands"] + [d["planting"]]:
                for c in holder.get("clusters", []) + holder.get("viewClusters", []):
                    if c["name"] != nm: continue
                    # ⭐ 箱でなく**輪郭**で見込む(2026-09-08 C-1)── 平行四辺形の塊がある
                    QS = cluster_polys(c)
                    for j, Q in enumerate(QS):
                        az = [math.degrees(math.atan2(cv - v, -(cu - u))) for cu, cv in Q]
                        shows.append((nm + ("" if len(QS) == 1 else "(其%d)" % (j + 1)),
                                      min(az), max(az), max(az) - min(az)))
        rows.append((vp, eye, src, shows))
    return rows


# ---------------------------------------------------------------- 三角数の見積り
def plant_budget(d, g):
    """置く物の総数と三角数。**在庫の木は1本1万〜2万三角**なので目に見えるコスト。"""
    pal = d["planting"]["parts"]
    st = band_stats(d, g)
    n = {"松": 0.0, "落葉": 0.0, "中木": 0.0, "低木": 0.0}
    # ⭐ **林縁は別の面・別の密度なので別に丸める**(2026-09-08 十六巡目 C-2)── ⛔ 合算してから
    #    丸めると、`scatter_pts` が本体と林縁を**別々に**配る整数と 1 本ずれる(検査が止める)。
    nr = {"松": 0.0, "落葉": 0.0, "中木": 0.0, "低木": 0.0}
    for r in st:
        if "b" not in r: continue
        n["落葉"] += r["rakuyo"]; n["松"] += r["takagi"] - r["rakuyo"]
        n["中木"] += r["chuboku"]; n["低木"] += r["teiboku"]
        nr["中木"] += r.get("chubokuRinen", 0.0); nr["低木"] += r.get("teibokuRinen", 0.0)
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
    # ⭐ **差し掛けの高木は一本立ちと同じ数え方**(高2 庭方 2026-09-09 十七巡目)── 位置を
    #    意匠が決めた木なので GameObject。⛔ 帯の密度からは出ないので帯からは差し引かない。
    for sk in sashikake_rows(d, g):
        sn[sk.get("layer") or "落葉"] = sn.get(sk.get("layer") or "落葉", 0.0) + 1
    # ⭐ **名指しの木も一本立ちと同じ数え方**(決1③ 庭方 2026-09-09 十八巡目)── ⛔ ただし
    #    こちらは**帯の面に立つので帯から差し引く**(⛔ 密度を動かさないのが決1 の要である)。
    #   ⭐ **差し引くのは帯に落ちる木だけ**【A-1 庭方 2026-09-09 十九巡目】── ★主景は
    #   **区**の中に立つので帯からは引かない(区の側は塊の `mix` から 1 本抜いてある)。
    nm_cut = {}
    for r9 in named_tree_rows(d, g):
        lay9 = r9.get("layer") or "落葉"
        sn[lay9] = sn.get(lay9, 0.0) + 1
        if r9.get("band"): nm_cut[lay9] = nm_cut.get(lay9, 0) + 1
    place = d["planting"]["plantRule"].get("placement") or {}
    rows = []
    for key in ("松", "落葉", "中木", "低木"):
        # ⚠ **雛形(大きさを持たない palette の点)は変種の平均で見積る**(2026-09-07 裁定1)──
        #   どの変種が何本になるかは丈が決めるので、ここでは決まらない。
        tri = [part_tris(d, pt) for pt in pal[key]]
        wt = sum(pt.get("w", 1) for pt in pal[key])
        avg = None
        if all(t is not None for t in tri) and tri:
            avg = sum(t * pal[key][i].get("w", 1) for i, t in enumerate(tri)) / float(wt)
        # ⛔ **丸めの順を撒き方と揃える**(⛔ 先に引いてから丸めると 1 本ずれる)──
        #    `scatter_pts` は 帯の和を丸めてから塊・名指しの木を引く。
        rows.append((key, int(math.floor(n[key] + 0.5)) - nm_cut.get(key, 0)
                     + int(math.floor(nr[key] + 0.5)),
                     int(round(sn[key])), avg, place.get(key), place.get("singles")))
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


def label_overlap_check(htm):
    """図版の**銘の重なり**〔記録〕【2026-09-08 検図12巡目 低・ラベル衝突】。

    ⛔ ⛔にはしない ── 幅は等幅の見積り(和字=`font-size`・欧文=0.55倍)で、**組版の実測ではない**。
    ⭕ 役は『重なりが増えたら気づける』こと(規則19)。逃がしは `labelOff`(px・⛔ 設計値ではない)。
    """
    tx = re.compile(r'<text([^>]*)>(.*?)</text>', re.S)

    # ⛔ **銘の属性は `style=` の中にある** ── `T()` は `text-anchor` も `font-size` も
    #    属性ではなく `style="text-anchor:end;font-size:9.5px"` として刷る。旧版は属性しか
    #    見ておらず、⛔ **全605個の銘を「左寄せ・12px」と読んで**重なりを数えていた
    #    (物差しが図を測っていない形・規則19)【2026-09-08 検図18巡目の着地を検めていて発覚】。
    def at(a, k, dv=None):
        m = re.search(r'\b%s="([^"]*)"' % k, a)
        if m: return m.group(1)
        st = re.search(r'style="([^"]*)"', a)
        if st:
            m = re.search(r'(?:^|;)\s*%s\s*:\s*([^;]+)' % k, st.group(1))
            if m: return m.group(1).strip()
        return dv

    def px(v, dv):
        try: return float(str(v).replace("px", "").strip())
        except Exception: return dv
    note, tot = [], 0
    for m in re.finditer(r'<svg[^>]*aria-label="([^"]*)"(.*?)</svg>', htm, re.S):
        lab, body = m.group(1), m.group(2)
        bx = []
        for q in tx.finditer(body):
            a, t = q.group(1), q.group(2)
            s_ = re.sub(r"<[^>]+>", "", t).strip()
            if not s_: continue
            x = float(at(a, "x", 0)); y = float(at(a, "y", 0))
            fs = px(at(a, "font-size", "12"), 12.0)
            anc = at(a, "text-anchor", "start")
            w = txt_w(s_, fs)
            x0 = x if anc == "start" else (x - w / 2 if anc == "middle" else x - w)
            bx.append((x0, y - fs * 0.85, x0 + w, y + fs * 0.2, s_))
        n = 0
        for i in range(len(bx)):
            for j in range(i + 1, len(bx)):
                a_, b_ = bx[i], bx[j]
                if min(a_[2], b_[2]) - max(a_[0], b_[0]) > 1.0 and \
                   min(a_[3], b_[3]) - max(a_[1], b_[1]) > 1.0:
                    n += 1
        tot += n
        if n: note.append("『%s』の銘の重なり %d 組 ／ 銘 %d 個【算出】" % (lab, n, len(bx)))
    note.append("**図版 %d 面の銘の重なり 計 %d 組**【算出 — ⛔ ⛔にはしない(幅は等幅の見積り)。"
                "⭕ 増えたら気づくための数。逃がしは `labelOff`(px・⛔ 設計値ではない)】"
                % (len(re.findall(r"<svg", htm)), tot))
    return [], note


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
    # ⭐ **傾けた木の枝下は鉛直で目減りする**【低4 庭方 2026-09-08 十二巡目】── 下限
    #    (`edaShitaMinM`)は**鉛直で測る**(`edaShitaBasis`)ので、幹を倒せば最下枝の付け根の
    #    鉛直の高さは cos(傾き)だけ下がる。⛔ 〔記録〕にとどめる ── 目減りをどう埋めるかは
    #    仕立ての話で、指図方が下限を動かす話ではない。⛔ 黙らせない(規則19)。
    if tk.get("edaShitaBasis"):
        for gd in d["gardens"] + d["slopeBands"]:
            for sg in gd.get("singles", []):
                q = single_lean(d, sg)
                if not q: continue
                lim = lo_ch if (sg.get("layer") == "中木") else lo
                e0 = sg.get("edaShita") or lim
                if e0 is None: continue
                dgm = max(q[0])
                note.append("%s の**枝下は鉛直で測る**(`edaShitaBasis`)── 傾き %s° で "
                            "%.2f m → **%.2f m**(目減り %.2f m)。⛔ 下限 %.2f m を保つのは"
                            "**仕立ての側**(最下枝の付け根を幹に沿って上げる)であって、"
                            "下限を下げることではない【算出】"
                            % (sg["name"], _rng(q[0]), e0,
                               e0 * math.cos(math.radians(dgm)),
                               e0 * (1 - math.cos(math.radians(dgm))), lim or 0.0))
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
                    _c = single_crown_center(d, sg)
                    dd = min(_pt_seg(_c, C[i], C[(i + 1) % 4]) for i in range(4))
                    if in_poly(_c, C): dd = 0.0
                    if dd < r - 1e-9:
                        bad.append("%s の樹冠(半径 %.3f m)が井戸屋形の石敷=軒先の外形へ %.3f m 掛かる"
                                   % (sg["name"], r * ken0, (r - dd) * ken0))
                    else:
                        note.append("%s の樹冠の外周 → 井戸屋形の軒先の外形 %.3f m【算出】"
                                    % (sg["name"], (dd - r) * ken0))
    # ⭐ **高木は `idoNokiCrownClear` の射程の外**【中1 庭方 2026-09-07】。
    #    ⛔ 除外していること**だけ**を宣言して終わらせない — 樹冠が井戸屋形へ掛かってよいのは
    #    **枝下が屋形の棟高を越える**からで(⛔ 一般則ではない・考証10巡目 中3)、
    #    そこは誰も測っていなかった(10 m の椋の下枝が
    #    下がれば屋形の棟に当たる)。⛔ 宣言(`idoMuneClear`)が消えたら止める(規則19)。
    if tk.get("idoMuneClear") is None:
        bad.append("`planting.plantRule.crownRule.takagi.idoMuneClear` の宣言が無い — "
                   "**高木を `idoNokiCrownClear` から外している理由**(枝下が棟高を越える)が"
                   "どこにも書かれず、条件も測られない(規則19)")
    elif tk.get("idoMuneClear"):
        R_ = ido_rects(d)
        io_ = d.get("ido") or {}
        if R_ and io_.get("muneH") is not None:
            u0, v0, u1, v1 = R_["軒先"]
            C = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            for gd in d["gardens"]:
                for sg in gd.get("singles", []):
                    if sg.get("layer") not in ("落葉", "松"): continue
                    r = single_crown(d, sg)
                    if r is None:
                        note.append("%s の樹冠が引けない(部材が目録に無い)— 井戸屋形の軒先との"
                                    "関係を測れていない" % sg["name"])
                        continue
                    _c = single_crown_center(d, sg)
                    dd = 0.0 if in_poly(_c, C) else \
                        min(_pt_seg(_c, C[i], C[(i + 1) % 4]) for i in range(4))
                    if dd >= r - 1e-9:
                        note.append("%s の樹冠の外周 → 井戸屋形の軒先の外形 %.3f m(⭕ 掛からない)"
                                    "【算出】" % (sg["name"], (dd - r) * ken0))
                        continue
                    e = sg.get("edaShita")
                    if e is None:
                        bad.append("%s の樹冠が井戸屋形の軒先へ %.3f m 掛かるのに枝下の宣言が無い — "
                                   "高木が屋形に掛かってよいのは枝下が棟高を越えるからで、"
                                   "宣言が無ければその条件を測れない" % (sg["name"], (r - dd) * ken0))
                    elif e <= io_["muneH"] + 1e-9:
                        bad.append("%s の枝下 %.2f m が井戸屋形の棟高 %.2f m を越えない — "
                                   "樹冠が軒先へ %.3f m 掛かっているので、下枝が棟に当たる。"
                                   "⛔ 樹冠を絞って黙らせない(位置か仕立てで解く)"
                                   % (sg["name"], e, io_["muneH"], (r - dd) * ken0))
                    else:
                        note.append("%s の樹冠が井戸屋形の軒先の外形へ %.3f m 掛かる ── ⭕ **可**"
                                    "(枝下 %.2f m ＞ 屋形の棟高 %.2f m・余裕 %+.2f m)"
                                    "【U 設計判断 — ⛔ 根拠は幾何のこの一行だけで、"
                                    "『社頭の井戸が大樹の下に在るのは常態』という一般則は "
                                    "2026-09-07 考証10巡目 中3 で落とした(典拠が無い)。"
                                    "⛔ 余裕はこれだけしか無い】"
                                    % (sg["name"], (r - dd) * ken0, e, io_["muneH"],
                                       e - io_["muneH"]))
    # ⭐ **中木の樹形の規約**【裁き2 庭方 2026-09-07】── 倍率は `crownPerH` からの従属値。
    #    ⛔ 宣言が無ければ止める(規約を消せば手値の倍率へ戻る・規則19)。
    #    ⛔ 個体が `scaleXZ` を持ったら止める(規約の上から手で押し戻す道を塞ぐ)。
    cbr = d["planting"]["scaleRule"].get("chuboku") or {}
    cxz = cbr.get("scaleXZ")
    if cxz is None:
        bad.append("`planting.scaleRule.chuboku.scaleXZ`(部材の素の樹冠に掛ける倍率)の宣言が"
                   "無い — 宣言の無い規約は等倍(部材の素の開いた形)へ戻る(規則19)")
    if cbr.get("crownPerH") is not None:
        bad.append("`planting.scaleRule.chuboku.crownPerH` が復活している — 中木の樹冠は "
                   "`scaleXZ` の一本で決まる(⛔ 同じ量に二つの宣言を置かない・規則4。"
                   "2026-09-08 十六巡目 中6)")
    if d["planting"]["scaleRule"].get("isolatedXZ") is None:
        bad.append("`planting.scaleRule.isolatedXZ`(孤立木の倍率)の宣言が無い — "
                   "宣言が無いと**前庭の一本立ちと『辻の留め』の欅まで林の形へ痩せる**"
                   "(⛔ 孤立木は開いた形が正しい。2026-09-08 十六巡目 中6)")
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            if sg.get("layer") != "中木": continue
            if sg.get("scaleXZ") is not None:
                bad.append("%s が個体の `scaleXZ` を持つ — 中木の樹冠は規約 `scaleRule` から出る"
                           "(⛔ 個体に倍率を持たせない。2026-09-07 裁き2)" % sg["name"])
            if cxz is None: continue
            pf = single_prefab(d, sg)
            xz = crown_scale_xz(d, "chuboku", pf, sg.get("h"), iso=True)
            note.append("%s の `scaleXZ` %s【従属 — 孤立木なので `isolatedXZ`。⛔ 林の中の中木は "
                        "%g〜%g】" % (sg["name"], ("%.3f" % xz) if xz else "—(部材が目録に無い)",
                                       cxz[0], cxz[1]))
    # ⭐ **中木の丈を動かした日に鳴る二つ**【低1 庭方 2026-09-07 に丈を落としたので結線した】
    #   (a) **中景の塊** — 帯の中木どうしの樹冠が重なって初めて「二本で一つの塊」に読める。
    #   (b) **段(低木 → 中木 → 高木)** — 層の丈の順が崩れたら塊も段も読めない。⛔ 止める。
    for gd in d["gardens"]:
        ch_sg = [q for q in gd.get("singles", []) if q.get("layer") == "中木"]
        for i in range(len(ch_sg)):
            for j in range(i + 1, len(ch_sg)):
                a, b_ = ch_sg[i], ch_sg[j]
                ra, rb = single_crown(d, a), single_crown(d, b_)
                if ra is None or rb is None: continue
                dd = math.hypot(a["uv"][0] - b_["uv"][0], a["uv"][1] - b_["uv"][1])
                note.append("%s の中木 %s–%s の芯々 %.3f m ／ 樹冠の重なり %+.3f m"
                            "(⭕ 正なら**二本で一つの塊**に読める。⛔ 下限は置かない — 塊の姿は庭方の意匠)"
                            "【算出 — 丈を動かすと従属で動く】"
                            % (gd["name"], a["name"], b_["name"], dd * ken0,
                               (ra + rb - dd) * ken0))
        sh = (gd.get("shrubs") or {}).get("hM")
        if not sh or not ch_sg: continue
        sh_hi = sh[1] if isinstance(sh, (list, tuple)) else sh
        ch_lo = min(q["h"] for q in ch_sg if q.get("h"))
        tk = [q["h"] for q in gd.get("singles", [])
              if q.get("layer") in ("落葉", "松") and q.get("h")]
        tk_lo = min(tk) if tk else None
        ch_hi = max(q["h"] for q in ch_sg if q.get("h"))
        if ch_lo <= sh_hi + 1e-9:
            bad.append("%s の段が崩れる — 中木の最低の丈 %.2f m が低木の上限 %.2f m を上回らない"
                       "(低木 → 中木 → 高木の段が読めなくなる)" % (gd["name"], ch_lo, sh_hi))
        if tk_lo is not None and tk_lo <= ch_hi + 1e-9:
            bad.append("%s の段が崩れる — 高木の最低の丈 %.2f m が中木の最高 %.2f m を上回らない"
                       % (gd["name"], tk_lo, ch_hi))
        note.append("%s の段(丈) 低木 %.2f 〜 %.2f ／ 中木 %.2f 〜 %.2f ／ 高木 %s m ── "
                    "⭕ 低木 → 中木 → 高木の順【算出】"
                    % (gd["name"], sh[0] if isinstance(sh, (list, tuple)) else sh, sh_hi,
                       ch_lo, ch_hi,
                       ("%.2f 〜 %.2f" % (tk_lo, max(tk))) if tk_lo is not None else "無し"))
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
    # ⭐ **傾き(門被り)**【中3 庭方 2026-09-08】── 部材が『林の松(直立・段)』に替わったので、
    #    ⛔ **指図が言わなければ棟梁は真っ直ぐ立てる**。役名と姿を食い違わせない。
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            # ⚠ **役名で見る**(⛔ 註の本文で拾わない)── 『坂の頭の松』の役は「⛔ 門被りでは
            #    ない」と**否定**で書かれており、本文を拾うと逆に読める。
            q = single_lean(d, sg)
            kaburi = ("門被り" in (sg.get("name") or "")
                      or (sg.get("role") or "").startswith("門被り"))
            if kaburi and q is None:
                bad.append("『%s』は役が**門被り**なのに傾き(`leanDeg`)の宣言が無い — "
                           "指図が言わなければ部材(林の松・直立)はそのまま真っ直ぐ立つ。"
                           "⛔ 傾けないなら役名を改めること(名と姿を食い違わせない。"
                           "中3 庭方 2026-09-08)" % sg["name"])
            if q is None: continue
            if q[1] is None:
                bad.append("『%s』の `leanToward`「%s」が門に解けない — 傾ける先が引けなければ"
                           "向きは測れない" % (sg["name"], sg.get("leanToward") or "—"))
                continue
            cu, cv = single_crown_center(d, sg)
            r = single_crown(d, sg)
            gt = [x for x in d["gates"] if x.get("u") is not None
                  and abs(x["u"] - q[1][0]) < 1e-9 and abs(x["v"] - q[1][1]) < 1e-9]
            ov = "—"
            if gt and r is not None:
                hu, hv = gt[0]["plan"]["du"] / 2.0, gt[0]["plan"]["dv"] / 2.0
                C = [(gt[0]["u"] - hu, gt[0]["v"] - hv), (gt[0]["u"] + hu, gt[0]["v"] - hv),
                     (gt[0]["u"] + hu, gt[0]["v"] + hv), (gt[0]["u"] - hu, gt[0]["v"] + hv)]
                dd = 0.0 if in_poly((cu, cv), C) else \
                    min(_pt_seg((cu, cv), C[i], C[(i + 1) % 4]) for i in range(4))
                ov = "%+.3f m" % ((r - dd) * ken0)
            note.append("『%s』の**傾き** %s°(`leanToward`「%s」)── 樹冠の芯が幹の芯から "
                        "%.3f m 寄る ／ 門の平面への樹冠の掛かり %s(正=掛かる=**門被りの役**)"
                        "【算出 — 寄りは (枝下と丈の中央の高さ)× sin(傾きの最大)。"
                        "⛔ 数を json に書かない】"
                        % (sg["name"], _rng(sg.get("leanDeg")), sg.get("leanToward") or "—",
                           math.hypot(cu - sg["uv"][0], cv - sg["uv"][1]) * ken0, ov))
    return bad, note


_SG_LAYER = {"松": ("松", "matsu"), "落葉": ("落葉", "rakuyo"),
             "中木": ("中木", "chuboku"), "低木": ("低木", "chuboku")}


def single_parts(d, sg):
    """一本立ちが指す palette の点。`part` の名指しがあればその一点、無ければ層の全部。

    ⭐ 名指しは**樹種と個体**だけを指す — 大きさ(変種)は `sizeRule` が丈から選ぶので、
    `part` に大きさは書かない(2026-09-07 裁定1)。層の宣言が無ければ空(=**測れていない**)。
    """
    key = _SG_LAYER.get(sg.get("layer") or "")
    if key is None: return []
    pal = d["planting"]["parts"].get(key[0], [])
    named = [pt for pt in pal if pt.get("api") == sg.get("part")]
    return named or pal


def single_prefab(d, sg):
    """一本立ちが据える部材の prefab 名(**大きさまで解いた実名**)。無ければ None。"""
    pal = single_parts(d, sg)
    if not pal: return None
    q = pick_variant(d, pal[0], sg.get("h"))
    return q[1] if q else pal[0].get("prefab")


def single_crown(d, sg):
    """一本立ちの**据えたあとの樹冠の半径[間]**。`crown` があればそれ、無ければ部材と規約から。

    ⭐ 2026-09-06b — 一本立ちが**部材を名指し**(`part`)していればその一点だけを見る
    (⛔ palette の最大で代表させない)。個体の `scaleXZ` は `scaleRule` の倍率の**上に**掛ける。
    ⛔ **層の宣言が無ければ None を返す**【中1 庭方 2026-09-07 八巡目】── 旧式は既定を
    「落葉」に落としており、層も部材も丈も宣言していない一本立ちに**落葉 palette の最大**を
    当てて「樹冠 16.31 m の落葉高木」の円を描いていた。⛔ **既定で最大の落葉樹冠を当てるのは
    『測れていない物を測れたことにする』形**(規則19)。
    """
    ken = d["const"]["ken"]
    if sg.get("crown"): return sg["crown"] / 2.0 / ken
    key = _SG_LAYER.get(sg.get("layer") or "")
    if key is None: return None
    best = None
    for pt in single_parts(d, sg):
        q = pick_variant(d, pt, sg.get("h"))
        # ⭕ **一本立ちは孤立木**なので `isolatedXZ`(2026-09-08 中6・庭方)
        c = crown_of(d, key[1], (q[1] if q else pt.get("prefab")), sg.get("h"), iso=True)
        if c is None: continue
        v = max(c) / 2.0 / ken
        best = v if best is None else max(best, v)
    rule0 = d["planting"]["scaleRule"].get(key[1]) or {}
    if best is not None and sg.get("scaleXZ") and rule0.get("crownPerH") is None:
        rule = rule0.get("scaleXZ") or [1.0, 1.0]
        best = best / max(rule) * max(sg["scaleXZ"])
    return best


def single_lean(d, sg):
    """一本立ちの**傾き**(度の範囲, 傾ける先の (u,v))。宣言が無ければ None。

    ⭐ 2026-09-08 中3(庭方)── 部材が『林の松(直立・段)』に替わったので、⛔ **指図が言わなければ
    棟梁は真っ直ぐ立てる**。`leanDeg`(度の範囲)と `leanToward`(門の名)で宣言する。
    ⛔ 傾きの数をここに書かない(json が正典)。
    """
    dg = sg.get("leanDeg")
    if not dg: return None
    tw = sg.get("leanToward") or ""
    for gt in d["gates"]:
        if gt["name"] and gt["name"] in tw and gt.get("u") is not None:
            return (dg, (gt["u"], gt["v"]))
    return (dg, None)


def single_crown_center(d, sg):
    """樹冠の**芯**の (u,v)。傾きの宣言があれば、その分だけ寄せる(⛔ 幹の芯とは別)。

    ⭐ 樹冠の芯は幹の足元から (枝下と丈の中央の高さ)× sin(傾き) だけ傾ける先へ寄る。
    ⚠ **最も大きい傾き**で測る(範囲の悪い側)。⛔ 余裕の数を json に書かない。
    """
    u, v = sg["uv"]
    q = single_lean(d, sg)
    if not q or not q[1]: return (u, v)
    (lo, hi), (gu, gv) = q
    cr = d["planting"]["plantRule"].get("crownRule") or {}
    key = "chuboku" if sg.get("layer") == "中木" else "takagi"
    eda = sg.get("edaShita") or (cr.get(key) or {}).get("edaShitaMinM") or 0.0
    hh = sg.get("h") or 0.0
    zc = (eda + hh) / 2.0                               # 樹冠の芯の高さ[m]
    sh = zc * math.sin(math.radians(max(lo, hi))) / d["const"]["ken"]   # [間]
    dx, dy = gu - u, gv - v
    L = math.hypot(dx, dy) or 1.0
    return (u + dx / L * sh, v + dy / L * sh)


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
            sp = (cluster_spacing(d, c) or 0.0) * pack
            need = n * sp * sp
            got = 0
            for Q in cluster_polys(c):        # ⭐ 箱でなく輪郭(2026-09-08 C-1)
                for p in poly_scan(Q, st):
                    if in_poly(p, Q) and in_poly(p, P): got += 1
            got *= st * st
            if need > 0 and got < need:
                note.append("%s の塊「%s」は 輪郭 ∩ 区 が %.1f 間²(=%.1f坪)しか無く、"
                           "%g 本 × 芯々 %.2f 間(packRatio %.2f)に要る %.1f 間² に足りない"
                           % (gd["name"], c["name"], got, got * ken * ken / TSUBO, n,
                              cluster_spacing(d, c) or 0, pack, need))
    for b in d["slopeBands"]:
        if not b.get("uv"): continue
        out = sum(1 for p in poly_scan([(q[0], q[1]) for q in b["uv"]], st)
                  if not in_poly(p, soch))
        if out * ct > 0.05:
            bad.append("社叢 帯%d の多角形が社地の外へ %.2f 坪 出ている(社地 `polygon` でクリップすること)"
                       % (b["band"], out * ct))
    bad2, note2 = _kaidan_band_clauses(d, g)
    return bad + bad2, note + note2


def _g(v):
    """数の刷り(⛔ 無いものを 0 と刷らない)。"""
    return "—" if v is None else ("%g" % v)


def _decl_chains(d, g, lay):
    """**宣言から組み直した**帯1〜3 の退避の**折れ線の列** [(点列, 半径)]。

    ⛔ `avoid_shapes`/`shape_hit` を通さない ── 条項⑤(二つの道の答えの照合)のための**独立の道**。

    ⭐ 条項⑤(二つの道の答えの照合)のための**独立の道**。`kaidans[].wKen` /
    `kattemichi[].w` / 囲い・土留めの線と `bandDef.avoid.kaidanShoulderKen` から半径を組み直す。
    ⛔ 片方だけ足すと⑤が鳴る = **結線の抜けをそのまま検査が拾う**(2026-09-08 十六巡目)。
    """
    sh = band_shoulder(d, lay)
    if sh is None: return []
    ken = d["const"]["ken"]
    av = d["planting"]["bandDef"]["avoid"]
    out = []
    for k in d["kaidans"]:
        out.append(([tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])],
                    kaidan_wken(d, k) / 2.0 + sh))
    if av.get("kattemichiRule"):
        # ⭐ **勝手道の肩は石段とは別の宣言**【高1 庭方 2026-09-09 十七巡目】
        shk = kattemichi_shoulder(d, lay)
        if shk is not None:
            for k in d.get("kattemichi", []):
                out.append(([(g.U(x), g.V(z)) for x, z in k["pts"]],
                            k["w"] / 2.0 / ken + shk))
    if av.get("kakoiRule"):
        post = 0.0
        for gd in d["gardens"]:
            tg = gd.get("tamagaki")
            if tg and tg.get("postDiaM"): post = max(post, tg["postDiaM"] / 2.0 / ken)
        for r in d["runs"]:
            if r.get("kind") not in ("柵", "板塀"): continue
            if not r.get("pts") and (r.get("a") is None or r.get("b") is None): continue
            rr = (post if r.get("kind") == "柵" else 0.0) + sh
            for a, b in run_segs(r): out.append(([a, b], rr))
        for w in d.get("terraceWalls", []):
            pt = [tuple(q) for q in (w.get("pts") or [w.get("a"), w.get("b")])]
            if any(q is None for q in pt) or len(pt) < 2: continue
            out.append((pt, sh))
    # ⭐ **社地の境からの幹の離れ**(全周)【中5 庭方 2026-09-09 十七巡目】
    if av.get("kyoukaiRule"):
        shy = kyoukai_shoulder(d, lay)
        if shy:
            P9 = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
            out.append((P9 + [P9[0]], shy))
    return [(pt, rr) for pt, rr in out if len(pt) >= 2]


def _shoulder_tsubo_from_decl(d, g, ps, lay):
    """**宣言から組み直した**石段の退避に載るセルの数(層 `lay`)。

    ⭐ 2026-09-08 検図15巡目 中2 ── 条項⑤は `band_stats` と**同じ式**を引いていたため
    恒真で、一度も発火し得なかった。⛔ だからここは `avoid_shapes`/`shape_hit` を**通さない**
    ── `kaidans[].wKen` と `bandDef.avoid.kaidanShoulderKen` から半径を組み直し、線分の
    区間の中だけで法線距離を測る(端にキャップを付けないのは 2026-09-06c 裁定3 のとおり)。
    ⛔ 二つの道の答えが違えば、どちらかの結線が切れている。
    """
    chains = _decl_chains(d, g, lay)
    if not chains: return 0

    def on(p):
        for pt, rr in chains:
            for i in range(len(pt) - 1):
                a, b = pt[i], pt[i + 1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dy * dy
                if L2 < 1e-12: continue
                t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
                if 0.0 <= t <= 1.0 and \
                   abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / math.sqrt(L2) < rr:
                    return True
            # ⭐ **内側の節の丸み**(2026-09-08 A-5)── ⛔ 端の二つには付けない
            for i in range(1, len(pt) - 1):
                if math.hypot(p[0] - pt[i][0], p[1] - pt[i][1]) < rr: return True
        return False
    return sum(1 for p in ps if on(p))


def _kaidan_band_clauses(d, g):
    """**石段の敷きの上に木を立てない**(帯1〜3)。⭐ 2026-09-08 に起こした。

    ⛔ ① `planting.bandDef.exclude` が**石段の敷き**を名指ししていない
    ⛔ ② `planting.bandDef.avoid.kaidanShoulderKen`(層ごとの肩)の宣言が無い / 層が欠けている
    ⛔ ③ 帯1〜3 が `avoidFrom`(退避の指し先)を宣言していない
    ⛔ ④ **帯1〜3 の面が石段の敷きに掛かる**(①の結線が切れている)
    ⛔ ⑤ **`band_stats` が引いた退避が、宣言から組み直した退避と一致しない**(②の結線)
    ⛔ ⑥⑦ **2026-09-09 十八巡目に廃した宣言**(`kaidanShoulderMaxRule` ／ `invariants.bridge`
       ほか)が残っている【決3 庭方】── ⛔ 廃した機構が黙って生き返る道を塞ぐ。
       〔記録〕肩と樹冠の関係は**受入値ではなくなったが測り続ける**(⛔ 見えなくしない)。

    ⚠ **なぜ帯4 と別の宣言か。** 帯4 の `avoid.otokozakaFromAxis` は『麓から男坂と仁王門を
    見せる額縁』【S 名所図会】で、**見え掛かり**を測っている。ここで測るのは**踏面と擁壁の物理**
    ── ⚠ **2026-09-08 に読みを改めた**【検図15巡目 低4】: 男坂は『切通し』ではなく**切盛の擁壁で
    受けた坂**(切通しは下端の区間だけ)で、裏込めは段の下(内側)にある。よって肩が守るのは
    『幹が側壁の裏込めの上に立たないこと』ではなく『**幹の根が擁壁を押さないこと**』である。
    ⛔ だから帯4 の数を写さない(⛔ 現況から逆算もしない)。
    〔記録〕**敷きの上に立っていたはずの本数**を層ごとに刷る ── ⛔ 直した後も刷り続ける
    (欠陥が見えなくなると、戻ったときに気づけない・規則19)。
    """
    bad, note = [], []
    bd = d["planting"]["bandDef"]
    if not any("石段" in q for q in (bd.get("exclude") or [])):
        bad.append("`planting.bandDef.exclude` が**石段の敷き**を名指ししていない — "
                   "男坂・女坂の踏面が社叢の帯の面に数えられ、密度どおりに木が撒かれる"
                   "(⛔ 0 件は合格ではなく未測定・規則19)")
    av = bd.get("avoid") or {}
    shk_by = av.get("kaidanShoulderKen") or {}
    shk = band_shoulder(d)
    if not shk_by:
        bad.append("`planting.bandDef.avoid.kaidanShoulderKen`(層ごとの石段の肩)の宣言が無い — "
                   "宣言が無ければ幹は踏面の縁まで寄れる。⛔ 帯4 の額縁の数で代用しない"
                   "(測っている物が違う)")
    else:
        miss = [q for q in (av.get("layers") or []) if shk_by.get(q) is None]
        if miss:
            bad.append("`planting.bandDef.avoid.kaidanShoulderKen` に層『%s』の肩が無い — "
                       "退避する層として名を挙げながら肩を宣言しないと、その層だけ**退避 0** で"
                       "撒かれる(⛔ 0 件は合格ではなく未測定・規則19)" % "』『".join(miss))
    # ⭐ **勝手道と社地の境の肩は別の宣言**【高1/中5 庭方 2026-09-09 十七巡目】。
    #    ⛔ 規約を宣言しながら肩を宣言しないと、その層だけ**退避 0** で撒かれる(規則19)。
    for rule9, key9, nm9 in (("kattemichiRule", "kattemichiShoulderKen", "勝手道"),
                             ("kyoukaiRule", "kyoukaiKen", "社地の境")):
        if not av.get(rule9): continue
        by9 = av.get(key9) or {}
        if not by9:
            bad.append("`planting.bandDef.avoid.%s` を宣言しながら `%s`(層ごとの肩)が無い — "
                       "%sの退避が**全層 0** になる(⛔ 0 は合格ではなく未測定・規則19)。"
                       "⛔ 石段の `kaidanShoulderKen` で代用しない(擁壁の有無が違う)"
                       % (rule9, key9, nm9))
            continue
        miss9 = [q for q in (av.get("layers") or []) if by9.get(q) is None]
        if miss9:
            bad.append("`planting.bandDef.avoid.%s` に層『%s』の肩が無い — その層だけ%sの"
                       "退避 0 で撒かれる(⛔ 0 件は合格ではなく未測定・規則19)"
                       % (key9, "』『".join(miss9), nm9))
    # ⭐ **林縁の段が下層の密度を持つか**【④ 庭方 2026-09-09 十七巡目】── ⛔ 林縁は
    #    『低木だけの縁にしない(中木を入れる)』と宣言してあるので、段のどれかが密度を持たねば
    #    ⛔ **林縁が消える**(⛔ 0 は合格ではなく未測定・規則19)。
    for b9 in d["slopeBands"]:
        if not (b9.get("rinen") or {}): continue
        ts9 = rinen_tiers(b9)
        for lay9 in ("中木", "低木"):
            if not any(rinen_dens_t(d, b9, t9, lay9) for t9 in ts9):
                bad.append("社叢 帯%d の林縁 ── **どの段も『%s』の密度を宣言していない**"
                           "(段 %s)。⛔ 林縁が黙って消える(規則19)── `tiers` を落とすなら "
                           "`rinen` の側に `%sPer100`/`…From` を戻すこと"
                           % (b9["band"], lay9,
                              "・".join(str(t9.get("name")) for t9 in ts9),
                              {"中木": "chuboku", "低木": "teiboku"}[lay9]))
    # ⭐ **林縁の辺の同定の規約**【中4 庭方 2026-09-09 十七巡目】
    if not bd.get("rinenEdgeRule") or bd.get("rinenEdgeTouchKen") is None:
        bad.append("`planting.bandDef.rinenEdgeRule` / `rinenEdgeTouchKen`(林縁が測る辺の同定)"
                   "の宣言が無い — 端点で触れるだけの辺を拾い、道に接しない面へ林縁が回る"
                   "(中4 庭方 2026-09-09。⛔ 旧式は幅 2.73 m の高木の空白を 193 m 作っていた)")
    # ⑥⑦ ⭐ **2026-09-09 十八巡目に二つの条項を廃した**【決3 庭方】──
    #    `avoid.kaidanShoulderMaxRule`(肩 + 半幅 < 樹冠の半径)は**四つの石段すべてで不成立**で、
    #    ⭕ 肩 1.5 間(擁壁の物理として正しい)を置いた時点で**撒く層が石段を跨ぐ道は全部塞がって
    #    いる**ことが判った。⇒ 跨ぎは常に**名指しの木**の仕事で、受入値は `planting.crownCover`
    #    が持つ。`invariants.bridge` / `bridgeKaidanSkip` / `bridgeShoulderFrom` は、
    #    ⛔ **帯ごとに連結を測るという誤った物差しを支えるためだけの機構**だったので同時に廃した。
    #    ⛔ **宣言が残っていたら鳴らす**(⛔ 廃した機構が黙って生き返る道を塞ぐ)。
    av9 = bd.get("avoid") or {}
    iv9 = bd.get("invariants") or {}
    for k9, o9, why9 in (("kaidanShoulderMaxRule", av9, "肩の上限"),
                         ("kaidanShoulderMaxPendingRef", av9, "肩の上限の猶予"),
                         ("bridge", iv9, "橋に数える物の名簿"),
                         ("bridgeKaidanSkip", iv9, "橋を架けない石段の名簿"),
                         ("bridgeShoulderFrom", iv9, "橋の正当性の指し先"),
                         ("maxCompPct", iv9, "帯ごとの最大成分の受入値")):
        if o9.get(k9) is not None:
            bad.append("`%s`(%s)が残っている — ⛔ **2026-09-09 十八巡目に廃した宣言**"
                       "(決3 庭方)。⛔ 廃した機構を黙って生き返らせない(規則4・規則19)"
                       % (k9, why9))
    # 〔記録〕**肩と樹冠の関係は測り続ける**(⛔ 上限として縛らないだけで、見えなくしない)
    rmin = min_matsu_crown_r(d)
    ken9 = d["const"]["ken"]
    for k in d["kaidans"]:
        hw9 = kaidan_wken(d, k) / 2.0 * ken9
        rmax = near_takagi_crown_r(d, g, k)
        for lay in ("松", "落葉"):
            s_ = shk_by.get(lay)
            if s_ is None: continue
            need = hw9 + s_ * ken9
            note.append("石段『%s』── 敷きの半幅 %.3f m + 肩(%s)%g 間 = **%.3f m** ／ "
                        "**この石段に差し掛かる高木**の樹冠の半径 最大 %s ／ 差 **%+.3f m**"
                        "【算出 — ⛔ **これは受入値ではない**(決3 庭方 2026-09-09 十八巡目で"
                        "上限の条項は廃した)。⭕ 撒く層が跨げないことは**正しい**ので、"
                        "跨ぎは `planting.sashikake` / `planting.namedTrees` の名指しの木が作る】"
                        % (k["name"], hw9, lay, s_, need,
                           ("%.3f m" % rmax) if rmax is not None else "**一本も無い**",
                           (rmax if rmax is not None else 0.0) - need))
    for b in d["slopeBands"][:3]:
        if not b.get("avoidFrom"):
            bad.append("社叢 帯%d が `avoidFrom`(退避の指し先)を宣言していない — "
                       "帯の側から退避へ辿れないと、宣言が帯へ届いていないことに誰も気づけない"
                       % b["band"])
    cells, _sk = band_scan(d, g)
    ct = cell_tsubo(d, bd["stepKen"])
    ap = kaidan_apron_shapes(d)
    st = band_stats(d, g)
    kai_cells = _BANDS.get("kai", 0)
    for b in d["slopeBands"][:3]:
        ps = cells[b["band"]]
        n1 = sum(1 for p in ps if shape_hit(p, ap))
        if n1:
            bad.append("社叢 帯%d の**面**が石段の敷きに %.2f 坪 掛かる — "
                       "踏面の上は林床ではない(`bandDef.exclude`)" % (b["band"], n1 * ct))
        row = [r for r in st if r.get("b") is b]
        # ⑤ ⭐ **2026-09-08 に組み直した**【検図15巡目 中2】── 旧式は `band_stats` と
        #    **一字一句同じ式**で数えており(`avoid == n2*ct` が恒に成り立つ)、条件は入力に
        #    よらず偽で**一度も発火し得なかった**。⛔ 「検査はあるが誰も見ていない」を残さない。
        #    ⇒ **宣言(敷きの半幅 + その層の肩)から組み直した独立の面**と突き合わせる。
        for lay in _LAYS:
            ind = _shoulder_tsubo_from_decl(d, g, ps, lay) * ct
            got = (row[0]["avoidBy"].get(lay) if row else None)
            if got is None:
                bad.append("社叢 帯%d の層『%s』の退避が `band_stats` に無い — "
                           "層ごとの肩が有効面へ届いていない" % (b["band"], lay))
            elif abs(got - ind) > 1e-6:
                bad.append("社叢 帯%d の層『%s』── `band_stats` が引いた退避 %.3f 坪 が、"
                           "**宣言(敷きの半幅 + 肩 %s 間)から組み直した %.3f 坪 と一致しない** — "
                           "②の結線が切れている(⛔ 数を合わせず結線を直す)"
                           % (b["band"], lay, got, _g(band_shoulder(d, lay)), ind))
        if row:
            note.append("社叢 帯%d ── 面 %.1f 坪 ／ 石段の退避(高木 %.1f ／ 中木 %.1f ／ "
                        "低木 %.1f 坪)／ 有効面(高木 %.1f ／ 中木 %.1f ／ 低木 %.1f 坪)"
                        "【算出 — 退避は 敷きの半幅 + **層ごとの肩** 高木 %s ／ 中木 %s ／ "
                        "低木 %s 間(裁き1 庭方 2026-09-08)】"
                        % (b["band"], row[0]["tsubo"],
                           row[0]["avoidBy"]["松"], row[0]["avoidBy"]["中木"],
                           row[0]["avoidBy"]["低木"], row[0]["usableBy"]["松"],
                           row[0]["usableBy"]["中木"], row[0]["usableBy"]["低木"],
                           _g(band_shoulder(d, "松")), _g(band_shoulder(d, "中木")),
                           _g(band_shoulder(d, "低木"))))
    # 〔記録〕**敷きの上に立っていたはずの本数**(= 落とした面 × 採用密度)。帯ごとに出す。
    kaic = _BANDS.get("kaic") or {}
    if kai_cells:
        seg, T = [], [0.0, 0.0, 0.0]
        for b in d["slopeBands"][:3]:
            m2 = len(kaic.get(b["band"]) or []) * ct * TSUBO
            if m2 <= 0: continue
            r_ = lambda k: sum(b.get(k) or [0, 0]) / 2.0
            q = (m2 * band_density(b) / 100.0, m2 * r_("chubokuPer100") / 100.0,
                 m2 * r_("teibokuPer100") / 100.0)
            for i in range(3): T[i] += q[i]
            seg.append("帯%d %.0f m²(高木 %.1f ／ 中木 %.1f ／ 低木 %.1f)" % ((b["band"], m2) + q))
        note.append("**石段の敷き %.1f 坪 = %.0f m²** を帯1〜3 の面から落とした ── %s。"
                    "旧図はここを林床として数えており、採用密度で **高木 %.1f 本・中木 %.1f 本・"
                    "低木 %.1f 本 = 計 %.0f 本**が**男坂・女坂の踏面の上に立っていた**"
                    "【算出 — ⛔ この行を消さない。消すと戻ったときに誰も気づけない(規則19)】"
                    % (kai_cells * ct, kai_cells * ct * TSUBO, " ／ ".join(seg),
                       T[0], T[1], T[2], sum(T)))
    # 〔記録〕**帯ごとの連結成分**【決3 庭方 2026-09-09 十八巡目 ── ⛔ もう合否ではない】。
    #    ⛔ この行を消さない(44 本の行と同じ理由 — 消すと戻ったときに誰も気づけない)。
    cb = band_components(d, g)
    sg_ = []
    for b in sorted(cb):
        cs = cb[b]
        if not cs: continue
        sg_.append("帯%d %.1f%%(成分 %d)" % (b, max(cs) / sum(cs) * 100.0, len(cs)))
    if sg_:
        note.append("**帯ごとの最大の連結成分** ── %s。⛔ **これは合否ではない**"
                    "(決3 庭方 2026-09-09 十八巡目 ── 帯は**密度の処方**であって物体ではないので、"
                    "帯1 のような細い環は単体では必ず割れる)。⭕ 不変条件③ が測るのは"
                    "**社叢ぜんぶの木の最大の連結成分**である【算出 — ⛔ この行を消さない】"
                    % " ／ ".join(sg_))
    return bad, note


# 変種の照合の許容の**下限**(**検査の物差しであって設計値ではない**ので json に置かない)。
# ⭐ 2026-09-07 庭方8巡目 裁定1 ── 「同じ樹種に複数の変種が在るのに `scaleY` がこの帯を
#    外れる」= **部材の変種の幅では届かない丈**を宣言している、ということ。⛔ 緩めて黙らせない。
SCALEY_LO = 0.75

def scaley_band(d):
    """`scaleY` の照合の帯 (下, 上)。**上は `sizeRule.scaleYMax` そのもの**。

    ⭐ **2026-09-08 に上を箍へ寄せた**【低1 検図15巡目】── 検査の帯の上が 1.15、大きさを選ぶ
    箍が 1.10 で食い違っており、**その隙間に ★主景の 1.125 が落ちていた**(= A-2 の根)。
    ⛔ 二つの物差しを並べて持たない ── 箍を超える `scaleY` は、そもそも `sizeRule` が選ばない。
    """
    cap = (size_rule(d) or {}).get("scaleYMax")
    return (SCALEY_LO, cap if cap is not None else 1.15)


def _scaley_rows(d):
    """`sizeRule` に載る部材が、どの丈で・どの変種を・どの `scaleY` で使われるか。

    戻り [(どこ, 樹種の api, 丈の刷り, 変種の刷り, scaleY 下, scaleY 上, 変種の数, palette の点)]。
    ⛔ 「同じ樹種に変種が一つしか無い」ものは照合の対象外(選びようが無い)。
    ⭐ 丈の刷りは `h_eff_txt` ── **帯の宣言と、樹種ごとの頭打ちで実際に立つ丈の両方**を出す。
    """
    out = []
    lays = (size_rule(d) or {}).get("layers") or []
    key = {"落葉": "rakuyo", "中木": "chuboku", "松": "matsu", "低木": "chuboku"}
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            if not any(zone_h(d, gd)): continue
            for kind, pt, n, h, _cr, _sk, vs, ylo, yhi in cluster_parts(d, gd, c):
                if not part_is_tpl(pt): continue
                out.append(("%s の塊「%s」" % (_gname(gd), c["name"]), pt.get("api"),
                            h_eff_txt(d, pt, h)[0], _vsjoin(vs), ylo, yhi,
                            part_variant_count(d, pt), pt))
        for sg in gd.get("singles", []):
            if (sg.get("layer") or "") not in lays: continue
            for pt in single_parts(d, sg)[:1]:
                if not part_is_tpl(pt): continue
                q = pick_variant(d, pt, sg.get("h"))
                if q is None: continue
                out.append(("一本立ち『%s』" % sg["name"], pt.get("api"),
                            "%.2f m" % (sg.get("h") or 0.0), q[0], q[3], q[3],
                            part_variant_count(d, pt), pt))
    # ⭐ **帯の撒き木**【中3 庭方 2026-09-07 九巡目】── 旧式は**塊と一本立ちしか見ておらず**、
    #    帯に撒く数百本は一本も照合されていなかった。⛔ **丈の宣言が無い層は行が立たない**
    #    (= 未測定。0 件は合格ではない・規則19)。⚠ 大きさを名指しした層(松・低木)も行は立てる
    #    — 「選びようが無い」ことが読めるようにするため(松の箍は `matsu_scale_check` が持つ)。
    for b in d["slopeBands"]:
        src = [("社叢 帯%d の撒き木" % b["band"], k, b.get(hk))
               for k, hk in (("松", "matsuH"), ("落葉", "rakuyoH"),
                             ("中木", "chubokuH"), ("低木", "teibokuH"))]
        src = [(w, k, h, _band_layer_n(b, k)) for w, k, h in src]
        rin = b.get("rinen") or {}
        # ⭐ **林縁は中木も撒く**(2026-09-08 十六巡目 C-2)── ⛔ 低木だけの縁にしない
        for ti_, t_ in enumerate(rinen_tiers(b)):
            for lay_ in ("中木", "低木"):
                hh_ = rinen_h_t(d, b, t_, lay_)
                if not hh_ or not rinen_dens_t(d, b, t_, lay_): continue
                src.append(("社叢 帯%d の林縁の帯(%s)の撒き木" % (b["band"], t_.get("name")),
                            lay_, hh_, _rinen_layer_n(b, rin, lay_)))
        for where, lay, h, nb in src:
            if not h: continue
            wh = "%s(%s%s)" % (where, lay, "" if nb is None else " %d 本" % int(round(nb)))
            for pt in d["planting"]["parts"].get(lay, []):
                vs, ylo, yhi = pick_variants_over(d, pt, h)
                out.append((wh, pt.get("api"), h_eff_txt(d, pt, h)[0], _vsjoin(vs), ylo, yhi,
                            part_variant_count(d, pt), pt))
    # ⭐ **★主景の一本**【A-2 の裁き 庭方 2026-09-08】── ⚠ 旧式はこの節を**帯の走査の中**に
    #    置いており、`gd` が最後の区(主景を持たない)に固定されて**一度も立たなかった**
    #    (= 社頭で最も重い一本が条項④の外にあった。⛔ 0 件は合格ではなく未測定・規則19)。
    for gd in d["gardens"]:
        sk_ = gd.get("shukei")
        if not (sk_ and sk_["tree"].get("part")): continue
        pal = [pt for pt in d["planting"]["parts"]["落葉"]
               if pt.get("api") == sk_["tree"]["part"]]
        for pt in pal[:1]:
            if not part_is_tpl(pt): continue
            _hm = shukei_hmin(d, sk_)
            q = pick_variant(d, pt, _hm)
            if q is None: continue
            out.append(("★主景の木", pt.get("api"),
                        "%.2f m 以上" % (_hm or 0.0), q[0], q[3], q[3],
                        part_variant_count(d, pt), pt))
    return out


def tree_size_check(d):
    """**樹の大きさの規約**(`crownPerH` と `sizeRule`)が効いているか【裁定1 庭方 2026-09-07】。

    ⛔ ① 落葉高木の樹形の規約 `rakuyo.crownPerH` の宣言が無い/`scaleXZ` が復活している
    ⛔ ② `sizeRule.layers` の palette に**大きさが焼き込まれている**(名指しと丈が食い違う道)
    ⛔ ③ **一本立ちが層を宣言していない**(既定で落葉 palette の最大が当たる — 中1)
    ⛔ ④ 同じ樹種に複数の変種が在るのに `scaleY` が照合の帯(`scaley_band`)を外れる
    ⛔ ⑤ **帯が密度を宣言している層に丈の宣言が無い**(= 変種も樹冠も選べない・中3)
    ⛔ ⑥ **丈を宣言する層の部材が目録に無いのに `pending` が立っていない**/ 指す `_pending` が実在しない
       ／ 逆に **部材が目録に在るのに `pending` が残っている**(条項④の照合が引き継がない)
    ⛔ ⑧ **★主景の木が丈を数で持っている**/`hMinFrom` の宣言が無い(A-2 庭方 2026-09-08)
    ⛔ ⑨ **層の宣言の上端へ届く部材が palette に一つも無い**(A-1 のカナリヤ・裁定1 庭方 2026-09-08)

    ⭐ **④の猶予は `pendingRef` を立てた部材の行だけに効く**【中2 検図16巡目 → 2026-09-08】。
    ⛔ 「落葉 palette のどれか」で通していた旧式は、項の内訳が名指ししていない部材まで
    (超過量の上限も無しに)黙って通した。**猶予は項の文言より広くしない。**
    ⭐ **④は落葉について恒真である**(`sizeRule.speciesHCap` が `scaleY` ≤ 箍 を常に満たす)ので、
    出鱈目な上端を捕まえるのは⑨の役目。⛔ ⑨を消すと帯に何を書いても図は黙る。
    """
    bad, note = [], []
    # ⑤ ⭐ 2026-09-07 九巡目 中3 ── 帯4 は `chubokuPer100`・`teibokuPer100` を宣言しながら
    #    `chubokuH`・`teibokuH` を持たず、**撒き木が一本も照合に載っていなかった**。
    #    ⛔ 0 件は合格ではなく未測定(規則19)。密度と丈は対で宣言する。
    LAY = (("松", "takagiPer100", "matsuH"), ("落葉", "rakuyoRatio", "rakuyoH"),
           ("中木", "chubokuPer100", "chubokuH"), ("低木", "teibokuPer100", "teibokuH"))
    for b in d["slopeBands"]:
        for where, o in ([("社叢 帯%d" % b["band"], b)]
                         + [("社叢 帯%d %s" % (b["band"], tg), o9)
                            for tg, o9 in rinen_decl_rows(d, b)]):
            for lay, dkey, hkey in LAY:
                dv = o.get(dkey)
                if dv is None: continue
                if isinstance(dv, (list, tuple)):
                    dv = (dv[0] + dv[1]) / 2.0
                if not dv: continue                     # 密度 0 の層は丈を要らない
                if o.get(hkey): continue
                bad.append("%s は `%s`(%s の密度)を宣言しているのに **`%s`(丈)の宣言が無い** — "
                           "丈が無ければ変種も樹冠も選べず、この帯の撒き木は**一本も照合に載らない**。"
                           "⛔ 0 件は合格ではなく未測定(中3 庭方 2026-09-07・規則19)"
                           % (where, dkey, lay, hkey))
    # ⑤-b ⭐ **視線が決める塊(`planting.viewClusters`)も同じ条件に載せる**【2026-09-08】──
    #     箱と本数と `mix` を持つ以上「密度を宣言している」のと同じで、丈が無ければ変種も樹冠も
    #     選べない。⛔ 帯だけを見て 0 件と言わない(規則19)。
    for c in d["planting"].get("viewClusters", []):
        mh, rh = (c.get("matsuH"), c.get("rakuyoH"))
        for kind, n in cluster_mix(c):
            if not n: continue
            h = mh if kind == "松" else rh
            if h: continue
            bad.append("視線の塊『%s』は `mix` で %s を %d 本 宣言しているのに **丈の宣言が無い** — "
                       "丈が無ければ変種も樹冠も選べず、この塊は**一本も照合に載らない**。"
                       "⛔ 0 件は合格ではなく未測定(規則19)。⭕ 丈は `hFrom` の宣言から"
                       "**箱が跨ぐ帯の共通部分**として図が算出する(⛔ 数で持たない)"
                       % (c["name"], kind, n))
    # ⑥ ⭐ **部材の欠と `pending` の対応**【2026-09-08】── 旧図は `parts.低木[].pending` を
    #    立てていたが、それは**表の刷り分けにしか効いておらず**、外しても何も鳴らなかった
    #    (破壊試験で全6検査が ⛔0 で黙った)。⛔ 部材が入った瞬間に条項④が引き継ぐ形にする。
    pend = d.get("_pending") or {}
    declared = []
    for b in d["slopeBands"]:
        for o in (b, b.get("rinen") or {}):
            for lay, dkey, hkey in LAY:
                if o.get(hkey) and lay not in declared: declared.append(lay)
    for lay in declared:
        for pt in d["planting"]["parts"].get(lay, []):
            got = (part_geom(pt) is not None) or bool(part_variants(d, pt))
            ref = pt.get("pendingRef")
            if not got:
                if not pt.get("pending"):
                    bad.append("`planting.parts.%s` の『%s』は**目録に無い**のに `pending` が"
                               "立っていない — 測れない部材が測れたことになる"
                               "(⛔ 0 件は合格ではなく未測定・規則19)" % (lay, pt.get("api")))
                elif not ref or ref not in pend:
                    bad.append("`planting.parts.%s` の『%s』は `pending` を立てているが、"
                               "`pendingRef`『%s』が `_pending` に実在しない — "
                               "猶予の出所が無い宣言は、誰も畳めない" % (lay, pt.get("api"), ref))
            elif pt.get("pending"):
                bad.append("`planting.parts.%s` の『%s』は**目録に在る**のに `pending` が"
                           "残っている — 猶予は終わっており、条項④(`scaleY` の照合)が"
                           "引き継がねばならない(⛔ 立てたままにすると照合を素通りする)"
                           % (lay, pt.get("api")))
            # ⭐ **`pendingRef` は目録に在る部材にも立つ**【中2 検図16巡目 → 2026-09-08】──
            #    ④の猶予(⛔→⚠)の射程を項の文言へ縛るための指し先なので、**指し先が実在
            #    しない宣言は猶予の抜け穴になる**。⛔ `pending` の有無に関わらず確かめる。
            if got and ref and ref not in pend:
                bad.append("`planting.parts.%s` の『%s』の `pendingRef`『%s』が `_pending` に"
                           "実在しない — 出所の無い猶予は誰も畳めない" % (lay, pt.get("api"), ref))
    lays_sz = (size_rule(d) or {}).get("layers") or []
    for lay in declared:
        n_ = 0
        for b in d["slopeBands"]:
            q = _band_layer_n(b, lay)
            if q: n_ += q
            rin = b.get("rinen") or {}
            if lay in ("中木", "低木") and rin:
                q2 = _rinen_layer_n(b, rin, lay)
                if q2: n_ += q2
        note.append("層『%s』── 撒き木 %d 本 ／ palette %d 点(目録に在る %d 点・`pending` %d 点)／ "
                    "%s【算出 — 大きさの照合が効くのは `sizeRule.layers` の層だけ】"
                    % (lay, int(round(n_)), len(d["planting"]["parts"].get(lay, [])),
                       sum(1 for pt in d["planting"]["parts"].get(lay, [])
                           if (part_geom(pt) is not None) or part_variants(d, pt)),
                       sum(1 for pt in d["planting"]["parts"].get(lay, []) if pt.get("pending")),
                       ("条項④(`scaleY` の照合)を受ける" if lay in lays_sz
                        else "`sizeRule` の対象外 ── `scaleY` は刷るが選び分けは効かない")))
    # ⑧ ⭐ **★主景の木の丈は従属値**【A-2 の裁き 庭方 2026-09-08】── ⛔ 数で持つと、部材と箍では
    #    届かない丈がそのまま残る(旧 18.0 m がそれで、`scaleY` が箍を超えていた)。
    for gd in d["gardens"]:
        sk_ = gd.get("shukei")
        if not sk_: continue
        if sk_["tree"].get("hMin") is not None:
            bad.append("%s の ★主景の木が **`hMin` を数で持っている** — 丈の下限は"
                       "『落葉高木の最も高い変種の素の丈 × `sizeRule.scaleYMax`』の従属値で、"
                       "数で持つと**部材と箍では届かない丈**が黙って残る(A-2 庭方 2026-09-08)"
                       % _gname(gd))
        elif not sk_["tree"].get("hMinFrom"):
            bad.append("%s の ★主景の木に **`hMinFrom`(丈の下限の出所)の宣言が無い** — "
                       "宣言が無ければ丈が引けず、この一本は部材も大きさも樹冠も測れない"
                       "(⛔ 0 件は合格ではなく未測定・規則19)" % _gname(gd))
        elif shukei_hmin(d, sk_) is None:
            bad.append("%s の ★主景の木の丈が引けない(落葉の palette か箍が無い)— "
                       "従属値の出所が欠けている" % _gname(gd))
        else:
            note.append("%s の ★主景の木 ── 丈 %.2f m 以上【従属 — 落葉高木の最も高い変種の"
                        "素の丈 × 箍 %.2f。⛔ 数で持たない】"
                        % (_gname(gd), shukei_hmin(d, sk_),
                           (size_rule(d) or {}).get("scaleYMax") or 0.0))
    sr = d["planting"]["scaleRule"]
    rk = sr.get("rakuyo") or {}
    if rk.get("scaleXZ") is None:
        bad.append("`planting.scaleRule.rakuyo.scaleXZ`(部材の素の樹冠に掛ける倍率)の宣言が"
                   "無い — 宣言の無い規約は『丈は Y だけ・樹冠は等倍』へ戻り、**部材の"
                   "野に一本で育った形がそのまま林の天端を作る**(2026-09-08 十六巡目 中6)")
    if rk.get("crownPerH") is not None:
        bad.append("`planting.scaleRule.rakuyo.crownPerH` が復活している — 落葉高木の樹冠は "
                   "`scaleXZ` の一本で決まる(⛔ 同じ量に二つの宣言を置かない・規則4)")
    sz = size_rule(d)
    if sz is None:
        bad.append("`planting.scaleRule.sizeRule`(大きさを丈から選ぶ規約)の宣言が無い — "
                   "宣言が無ければ palette が大きさを名指しする形へ戻る(規則19)")
    else:
        for lay in sz.get("layers", []):
            for pt in d["planting"]["parts"].get(lay, []):
                if not part_is_tpl(pt):
                    bad.append("`planting.parts.%s` の『%s』が**大きさを名指ししている** — "
                               "palette は樹種と個体差だけを持ち、大きさは `sizeRule` が丈から"
                               "選ぶ(裁定1 庭方 2026-09-07)" % (lay, pt.get("api")))
                    continue
                vs = part_variants(d, pt)
                if len(vs) < 2:
                    note.append("`planting.parts.%s` の『%s』は目録に変種が %d 種しか無い — "
                                "**大きさの照合は効かない**(選びようが無い)【算出】"
                                % (lay, pt.get("api"), len(vs)))
                else:
                    note.append("`planting.parts.%s` の『%s』の変種 %s【算出 — 素の丈 %s m】"
                                % (lay, pt.get("api"), "/".join(q[0] for q in vs),
                                   "・".join("%.1f" % q[3] for q in vs)))
    # ③ 層の宣言(⛔ 既定で落葉の最大を当てない)
    nsg = 0
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            nsg += 1
            if sg.get("layer"): continue
            bad.append("一本立ち『%s』(%s)が**層(`layer`)を宣言していない** — "
                       "層が引けなければ樹冠は測れない。⛔ 既定で落葉 palette の最大を"
                       "当てるのは『測れていない物を測れたことにする』形(中1 庭方 2026-09-07)"
                       % (sg["name"], _gname(gd)))
        for sg in gd.get("singles", []):
            if sg.get("layer") and not sg.get("h"):
                bad.append("一本立ち『%s』(%s)が**丈(`h`)を宣言していない** — "
                           "丈が無ければ樹冠も倍率も段の検査も測れない" % (sg["name"], _gname(gd)))
    note.append("一本立ち %d 本すべてが層と丈を宣言している【算出 — ⛔ 0 件は"
                "『宣言が無い物が無い』の意で、樹冠が正しいことの証明ではない】" % nsg)
    # ⑨ ⭐ **層の宣言の上端に届く部材が palette に一つも無い**【A-1 のカナリヤ・2026-09-08】
    #    ── `sizeRule.speciesHCap`(樹種ごとの頭打ち)は、構成上 `scaleY` ≤ 箍 を**常に**満たす。
    #    つまり条項④は落葉について**恒真**になり、帯にどんな上端を書いても黙る。
    #    ⇒ 頭打ちは「その樹種が届く所まで」しか許さないのだから、**層としては誰か一樹種が
    #    宣言の上端へ届いていなければならない**。届く部材が一つも無ければ、その宣言は
    #    **部材では建たない丈**である。⛔ この節を消すと出鱈目な上端が黙って通る。
    if (size_rule(d) or {}).get("speciesHCap"):
        for b in d["slopeBands"]:
            for o, tag in ([(b, "")] + [(o9, tg) for tg, o9 in rinen_decl_rows(d, b)]):
                for lay, _dk, hkey in LAY:
                    hh = o.get(hkey)
                    lo0, hi0 = _h_pair(hh)
                    if hi0 is None: continue
                    caps = [(pt.get("api"), species_h_cap(d, pt))
                            for pt in d["planting"]["parts"].get(lay, [])]
                    caps = [q for q in caps if q[1] is not None]
                    if not caps:
                        # ⭐ **飛ばしたことを黙って隠さない**【低4 検図17巡目 → 2026-09-08】──
                        #    ⑥ が backstop なので穴ではないが、**「解けなかったので測っていない」**
                        #    は「測って合格した」とは別の状態である(規則19)。
                        note.append("社叢 帯%d%s の『%s』── **上端を測れない**"
                                    "(palette の部材がどれも目録に無く、樹種ごとの上端が解けない)"
                                    "【算出 — ⛔ 条項⑨はこの層を飛ばした。⭕ 部材そのものの不在は"
                                    "条項⑥(palette の部材が目録に在るか)が受ける】"
                                    % (b["band"], tag, lay))
                        continue
                    best = max(q[1] for q in caps)
                    if best < hi0 - 1e-9:
                        bad.append("社叢 帯%d%s の『%s』は丈の上端 %.2f m を宣言しているが、"
                                   "**palette のどの樹種もそこへ届かない**(最も高く立てられるのは "
                                   "%.2f m)— 部材では建たない丈である。⛔ 樹種ごとの頭打ち "
                                   "(`sizeRule.speciesHCap`)は『届く樹種はそこまで』の規約で、"
                                   "**層ぜんぶが届かない宣言を通す規約ではない**"
                                   % (b["band"], tag, lay, hi0, best))
                    else:
                        note.append("社叢 帯%d%s の『%s』── 宣言の上端 %.2f m に届く部材 %s"
                                    "【算出 — 樹種ごとの上端 = 最大変種の素の丈 × 箍】"
                                    % (b["band"], tag, lay, hi0,
                                       "・".join("%s %.2f m" % (a_, c_) for a_, c_ in caps
                                                 if c_ >= hi0 - 1e-9)))
    # ⑩ ⭐ **落葉の上端は帯を下るほど上がる**【低2 庭方13巡目 → 2026-09-08】
    #    ── 条項⑨は**帯ごとの物差しにならない**(四つの帯が同じ palette を共有するので、
    #    課すのは『どの帯にも共通の一本の天井』だけ)。⚠ 実際、帯1 に上端 17.0 を書いても⑨は
    #    黙る ── 法肩の帯に 5 m の振れ幅は社叢として明らかに誤りなのに通る。
    #    ⭕ **庭方の代案**: 林として正しいのは『**法肩(帯1)の抜け木がいちばん低い**』こと。
    #    風衝と土層の薄さで肩は伸びず、下るほど高くなる。⇒ 帯1 の上端 ≤ 他の帯の上端。
    #    ⛔ 数を持たない — 帯の宣言どうしの大小だけを見る(帯の値を動かせば追随する)。
    # ⭐ **林縁の帯も同じ物差しで測る**【低5 検図18巡目 → 2026-09-08】── 旧版は
    #    `slopeBands[].rakuyoH` だけを見て `rinen` を見ておらず(⑨ は見る)、現況は帯4の林縁の
    #    `takagiPer100` が 0 なので無害だが、**そこが 0 でなくなった日に黙る**。
    _rk = []
    for b in d["slopeBands"]:
        for o, tag in ([(b, "")] + [(o9, tg) for tg, o9 in rinen_decl_rows(d, b)]):
            if o.get("rakuyoH"):
                _rk.append(("帯%d%s" % (b["band"], tag), _h_pair(o["rakuyoH"])))
    _b1 = ([q for q in _rk if q[0] == "帯1"] or [None])[0]
    if _b1 and _b1[1][1] is not None:
        _top1 = _b1[1][1]
        _oth = [q for q in _rk if q[0] != "帯1" and q[1][1] is not None]
        _low = [q for q in _oth if q[1][1] < _top1 - 1e-9]
        if _low:
            bad.append("社叢 帯1(法肩)の『落葉』の上端 %.2f m が、**下の帯 %s より高い** — "
                       "林として逆である(風衝と土層の薄さで肩の木は伸びず、**下るほど抜け木は"
                       "高くなる**)。⛔ 条項⑨は四つの帯に同じ palette の天井を当てるだけなので"
                       "この誤りを通す【低2 庭方 2026-09-08 十三巡目の代案】"
                       % (_top1, "・".join("%s(%.2f m)" % (nm_, q_[1]) for nm_, q_ in _low)))
        else:
            note.append("⭕ 落葉の上端 ── **帯1(法肩)%.2f m ≤ %s**(林縁の帯を含めて %d 口)"
                        "【算出 ／ 条項の由来は U 庭方の裁き — 低2 2026-09-08 十三巡目。"
                        "⛔ 『帯1 がいちばん低いことが林として正しい』のは意匠の裁きであって"
                        "算出の結論ではない(規則7)。⛔ 帯2〜4 の間の順序は問わない。"
                        "⛔ 帯1 を上げて⑨をすり抜ける形はここが捕まえる】"
                        % (_top1, "・".join("%s %.2f m" % (nm_, q_[1]) for nm_, q_ in _oth)
                           or "(比べる相手が無い)", len(_rk)))
    # ④ scaleY の照合
    lo_, hi_ = scaley_band(d)
    _rk_over, _capped = [], []
    for where, api, hs, vs, ylo, yhi, nv, pt in _scaley_rows(d):
        if ylo is None:
            note.append("%s の『%s』は `scaleY` を測れない(部材が目録に無い)" % (where, api))
            continue
        if "樹種ごとの頭打ち" in hs: _capped.append("%s の『%s』" % (where, api))
        if nv < 2:
            note.append("%s の『%s』変種 %s ／ scaleY %.3f〜%.3f【算出 — 変種が %d 種なので"
                        "照合は効かない】" % (where, api, vs, ylo, yhi, nv))
            continue
        if ylo < lo_ - 1e-9 or yhi > hi_ + 1e-9:
            # ⭐ **猶予の射程は『項の文言』に縛る**【中2 検図16巡目 → 2026-09-08】── 旧式は
            #    「落葉 palette のどれか」かつ「その項が在る」で通しており、**項の内訳が名指しして
            #    いない部材まで(超過量の上限も無しに)黙って通した**。破壊試験で帯1 の丈を
            #    [12.0, 30.0] にしても ⛔ 0 件・行が 9 → 23 に増えるだけだった。
            #    ⇒ ⚠ へ落とせるのは、**その部材の行が `pendingRef` で実在する項を指すとき**だけ。
            ref = pt.get("pendingRef") if isinstance(pt, dict) else None
            if (yhi > hi_ + 1e-9 and ylo >= lo_ - 1e-9
                    and ref and ref in (d.get("_pending") or {})):
                _rk_over.append(where)
                note.append("⚠ %s の『%s』(丈 %s)は変種 %s を選んでも `scaleY` %.3f〜%.3f で、"
                            "箍 %.2f を**超える** — **部材の刻みでは届かない丈**(→ `_pending`"
                            "「%s」)【算出 — ⛔ 猶予であって合格ではない。項が消えれば⛔】"
                            % (where, api, hs, vs, ylo, yhi, hi_, ref))
            else:
                bad.append("%s の『%s』(丈 %s)は変種 %s を選んでも `scaleY` %.3f〜%.3f で、"
                           "許容 %.2f〜%.2f を外れる — **部材の変種の幅では届かない丈**である"
                           "(⛔ 倍率で押し込まない)" % (where, api, hs, vs, ylo, yhi, lo_, hi_))
        else:
            note.append("%s の『%s』丈 %s → 変種 %s ／ scaleY %.3f〜%.3f"
                        "(許容 %.2f〜%.2f)【従属 — `sizeRule` が丈から選ぶ】"
                        % (where, api, hs, vs, ylo, yhi, lo_, hi_))
    # ⭐ **頭打ちが効いた行を必ず数える**(A-1 のカナリヤ・庭方 2026-09-08)── 頭打ちは
    #    条項④を落葉について恒真にするので、**効いていること自体が図に出ていなければ**
    #    「規約が死んでも誰も気づかない」状態になる(規則19)。
    if (size_rule(d) or {}).get("speciesHCap"):
        note.append("⭕ **樹種ごとの頭打ちが効いた行 %d** ── %s【算出 — ⛔ これが 0 に落ちたら"
                    "規約が死んだか、帯の上端が下がったかのどちらかである。⛔ 頭打ちを外すと"
                    "この行数がそのまま条項④の超過へ戻る】"
                    % (len(_capped), "・".join(sorted(set(_capped))) or "無し"))
    if _rk_over:
        note.append("⚠ **部材の刻みに届かず猶予で通した行 %d** ── %s【算出 — ⛔ 猶予は"
                    "`pendingRef` を立てた部材の行だけに効く。⛔ 指図方は決めない】"
                    % (len(_rk_over), "・".join(sorted(set(_rk_over)))))
    else:
        _refs = sorted(set(pt.get("pendingRef") for lay in d["planting"]["parts"]
                           for pt in d["planting"]["parts"][lay]
                           if isinstance(pt, dict) and pt.get("pendingRef")))
        if _refs:
            note.append("⭕ `pendingRef` を立てた部材(→ `_pending`「%s」)で `scaleY` が箍 %.2f を"
                        "超える行は 0【算出 — ⚠ 猶予が要らない状態であって、項が閉じた証明ではない】"
                        % ("」「".join(_refs), hi_))
    return bad, note


def single_repeat_check(d):
    """**同じ部材の一本立ちが近すぎないか**【中2 庭方 2026-09-07 九巡目】。

    ⛔ ① 一本立ちが据える部材(**大きさまで解いた実名**)を引けない
    ⛔ ② **同じ部材の一本立ちが二本、閾より近くに立つ**

    ⭐ **閾の出所** ── 区が宣言する「塊どうしを近づけすぎない目安」(`gardens[].clusterGapMin`)の
    **最小値**を採る。これは『これより近い二つは別々の塊として読まれない』という宣言なので、
    **同じ部材が二本これより近くに立てば、一つの塊の中で姿が繰り返される**ことになる。
    ⛔ **現況の離れから作った数ではない**(自分の成果物を基準に norm を作らない・§A-5)。
    ⚠ **測るのは平面の離れだけ** ── 段の違いも、間に立つ棟による遮蔽も測らない。
    ⛔ だから 0 件は『景として同じ画に入らない』の証明ではない(規則19)。
    ⚠ **丈が違えば変種も変わり、別のプレハブになる**(`sizeRule`)ので、比べるのは api ではなく
    **解けた prefab** である ── これを api で比べると、丈で分かれた中木の対まで拾ってしまう。
    """
    bad, note = [], []
    ken = d["const"]["ken"]
    lims = [gd["clusterGapMin"] for gd in d["gardens"] if gd.get("clusterGapMin")]
    if not lims:
        bad.append("`gardens[].clusterGapMin`(塊どうしを近づけすぎない目安)の宣言が一つも無い — "
                   "同じ部材の一本立ちの閾はここからの従属値なので、宣言が無いと測れない")
        return bad, note
    lim = min(lims)
    rows = []
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            pf = single_prefab(d, sg)
            if pf is None:
                note.append("一本立ち『%s』(%s)の部材を解けない — **離れは測れない**"
                            "(⛔ 測れないことは合格ではない)" % (sg["name"], _gname(gd)))
                continue
            rows.append((sg["name"], _gname(gd), pf, sg.get("uv")))
    seen = {}
    for nm, where, pf, uv in rows:
        seen.setdefault(pf, []).append((nm, where, uv))
    npair = 0
    for pf, qs in sorted(seen.items()):
        if len(qs) < 2:
            continue
        for i in range(len(qs)):
            for j in range(i + 1, len(qs)):
                (n1, w1, a), (n2, w2, b) = qs[i], qs[j]
                if not a or not b: continue
                npair += 1
                dk = math.hypot(a[0] - b[0], a[1] - b[1])
                if dk < lim - 1e-9:
                    bad.append("一本立ち『%s』(%s)と『%s』(%s)が**同じ部材 %s** で、"
                               "離れ %.2f 間 = %.2f m ＜ 閾 %.1f 間 = %.2f m — "
                               "**幹の癖と枝の出が同じ一体**なので、同じ画に入ると姿が繰り返される"
                               "(中2 庭方 2026-09-07)"
                               % (n1, w1, n2, w2, pf, dk, dk * ken, lim, lim * ken))
                else:
                    note.append("一本立ち『%s』(%s)と『%s』(%s)は同じ部材 %s だが、"
                                "離れ %.2f 間 = %.2f m ≥ 閾 %.1f 間 = %.2f m【算出】"
                                % (n1, w1, n2, w2, pf, dk, dk * ken, lim, lim * ken))
    note.append("一本立ち %d 本 ── 別々の部材 %d 種 ／ 同じ部材の対 %d 組 ／ "
                "閾 %.1f 間 = %.2f m(`gardens[].clusterGapMin` の最小値からの従属値)【算出】"
                % (len(rows), len(seen), npair, lim, lim * ken))
    return bad, note


def matsu_scale_check(d):
    """**松の縦伸ばしの箍**【中4 庭方 2026-09-07 九巡目】。

    ⛔ ① `planting.scaleRule.matsu.scaleYMax`(箍)の宣言が無い
    ⛔ ② 箍を超えているのに `_pending` の項が無い(= **猶予が切れているのに超過が残っている**)

    ⭐ **なぜ ⛔ が『超過そのもの』ではないか** ── 在庫の黒松は素の丈が当図の松の丈の半分ほどしか
    無く、⛔ **丈を下げて逃げてはいけない**(9.5〜13.0 m は社叢として正しい)。直せるのは部材の側
    だけなので、超過は**部材が入るまでの猶予**として `_pending` が持つ。⛔ だから
    **`_pending` の項が消えた瞬間に超過はそのまま⛔になる** ── 黙って伸びる道はこれで塞がる。
    ⚠ **帯に撒く松の縦伸ばしは庭方が『可』と裁いた**(中景遠景で効くのは幹と梢の輪郭)。
    ⛔ 不可なのは**近景の一本立ち**で、これは行の名で読む。
    """
    bad, note = [], []
    rule = d["planting"]["scaleRule"].get("matsu") or {}
    cap = rule.get("scaleYMax")
    xz = rule.get("scaleXZ") or [1.0, 1.0]
    key = "松の縦伸ばしが部材の丈の2倍近い"
    if cap is None:
        bad.append("`planting.scaleRule.matsu.scaleYMax`(松の縦伸ばしの箍)の宣言が無い — "
                   "宣言が無ければ松はいくらでも縦に伸ばせる(中4 庭方 2026-09-07)")
        return bad, note
    rows = []
    for b in d["slopeBands"]:
        h = b.get("matsuH")
        if not h: continue
        n = _band_layer_n(b, "松")
        wh = "社叢 帯%d の撒き木%s" % (b["band"], "" if n is None else "(%d 本)" % int(round(n)))
        for pt in d["planting"]["parts"]["松"]:
            _vs, ylo, yhi = pick_variants_over(d, pt, h)
            rows.append((wh, pt.get("api"), _rng(h), ylo, yhi, False))
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            if not any(zone_h(d, gd)): continue
            for kind, pt, k, h, _cr, sk, _vs, ylo, yhi in cluster_parts(d, gd, c):
                if sk != "matsu": continue
                rows.append(("%s の塊「%s」(%d 本)" % (_gname(gd), c["name"], k),
                             pt.get("api"), _rng(h), ylo, yhi, False))
        for sg in gd.get("singles", []):
            if (sg.get("layer") or "") != "松": continue
            pal = single_parts(d, sg)
            if not pal: continue
            q = pick_variant(d, pal[0], sg.get("h"))
            if q is None: continue
            rows.append(("一本立ち『%s』(%s)" % (sg["name"], _gname(gd)), pal[0].get("api"),
                         "%.2f" % (sg.get("h") or 0.0), q[3], q[3], True))
    over = ovsg = 0
    for wh, api, hs, ylo, yhi, is_sg in rows:
        if ylo is None:
            note.append("%s の『%s』は `scaleY` を測れない(部材が目録に無い)" % (wh, api))
            continue
        aniso = (ylo / xz[1], yhi / xz[0])
        if yhi > cap + 1e-9:
            over += 1
            ovsg += 1 if is_sg else 0
            note.append("%s の『%s』(丈 %s m)── `scaleY` %.3f〜%.3f ／ 異方比 %.2f〜%.2f で、"
                        "箍 %.2f を**超える**%s(→ `_pending`「%s」)【算出 — ⛔ 箍を上げて"
                        "黙らせない・⛔ 丈を下げて逃げない】"
                        % (wh, api, hs, ylo, yhi, aniso[0], aniso[1], cap,
                           " ⛔ **近景の一本立ち**" if is_sg else " ⚠ 撒き木(庭方の裁き=可)",
                           key))
        else:
            note.append("%s の『%s』(丈 %s m)── `scaleY` %.3f〜%.3f ／ 異方比 %.2f〜%.2f "
                        "⭕ 箍 %.2f の内【算出】"
                        % (wh, api, hs, ylo, yhi, aniso[0], aniso[1], cap))
    if over and key not in (d.get("_pending") or {}):
        bad.append("松の `scaleY` が箍 %.2f を **%d 行**で超えているのに、`_pending`「%s」が無い — "
                   "猶予の出所が消えたのだから超過は直さねばならない(⛔ 箍を上げて黙らせない・"
                   "⛔ 丈を下げて逃げない。中4 庭方 2026-09-07)" % (cap, over, key))
    if not over and key in (d.get("_pending") or {}):
        note.append("⭕ 箍 %.2f の超過は 0 行 — `_pending`「%s」は畳んでよい【算出】" % (cap, key))
    note.append("松 %d 行(うち近景の一本立ち %d 行)── 箍 %.2f を超えるのは **%d 行"
                "(うち一本立ち %d 行)**。⚠ `planting.viewClusters` の松は帯の本数から"
                "差し引かれた内訳なので、帯の行が代表している(⛔ 二重に数えない)【算出】"
                % (len(rows), sum(1 for q in rows if q[5]), cap, over, ovsg))
    return bad, note


def cluster_capacity(d, c):
    """塊の輪郭に **芯々の下限で何本入るか**。⛔ 面積で近似しない(一列の帯が落ちる)。

    ⭐ `scatter_pts` と**同じ走査・同じ芯々**で貪欲に詰める。⛔ **緩めない**(`_scatter_take` は
    採りきれないと `rmin` を 0.9 倍するので、そのまま呼ぶと『何本でも入る』になる)。
    種は固定(⛔ 流すたびに答えが動く道を作らない)。⚠ 貪欲・無作為順なので**下界**である。
    """
    import random
    sp = cluster_spacing(d, c)
    QS = cluster_polys(c)
    if sp is None or not QS: return None
    # ⭐ **線に沿う塊は弧長を芯々で刻んで据える**【A-7 庭方 2026-09-09 十九巡目】── ⛔ 面へ
    #    撒く詰まり(`packRatio`)を当てない。⛔ 二つの物差しを持たない ── `scatter_pts` の
    #    据え方(`line9`)と**同じ式**で数える。
    if c.get("alongTakagiEdgeLine") and c.get("poly") and len(c["poly"]) == 4:
        P4 = c["poly"]
        a0 = ((P4[0][0] + P4[3][0]) / 2.0, (P4[0][1] + P4[3][1]) / 2.0)
        a1 = ((P4[1][0] + P4[2][0]) / 2.0, (P4[1][1] + P4[2][1]) / 2.0)
        L9 = math.hypot(a1[0] - a0[0], a1[1] - a0[1])
        return int(math.floor(L9 / sp + 1e-9)) + 1 if sp > 0 else None
    rmin = sp * d["planting"]["plantRule"]["packRatio"]
    step = max(rmin / 4.0, 0.05)
    cand = [p for Q in QS for p in poly_scan(Q, step)]
    if not cand: return 0
    random.Random(0).shuffle(cand)
    out = []
    for p in cand:
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= rmin * rmin for q in out):
            out.append(p)
    return len(out)


def _rect_seg_dist(rect, a, b):
    """矩形と線分の距離[間](交わっていれば 0)。⛔ 端にキャップを付けない扱いはしない
    ── ここで測るのは『箱がどの石段にいちばん近いか』であって退避ではない。"""
    u0, v0, u1, v1 = min(rect[0], rect[2]), min(rect[1], rect[3]), \
        max(rect[0], rect[2]), max(rect[1], rect[3])
    C = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    ds = [_pt_seg(q, a, b) for q in C]
    for q in (a, b):
        du = max(u0 - q[0], 0.0, q[0] - u1)
        dv = max(v0 - q[1], 0.0, q[1] - v1)
        ds.append(math.hypot(du, dv))
    return min(ds)


def view_cluster_crown(d, c):
    """視線の塊の**松の樹冠径**(最小, 最大)[m]。⛔ 数を json に持たない(丈と部材からの従属値)。"""
    h = c.get("matsuH")
    if not h: return None
    cr = crown_of(d, "matsu", None, h)
    if cr is not None: return cr
    vs = []
    for pt in d["planting"]["parts"]["松"]:
        v2, _a, _b = pick_variants_over(d, pt, h)
        vs += v2
    if not vs: return None
    xz = d["planting"]["scaleRule"]["matsu"].get("scaleXZ") or [1.0, 1.0]
    w = [part_geom({"prefab": q[1]})[0] for q in vs]
    return (min(w) * xz[0], max(w) * xz[1])


def view_cluster_eda_rows(d, c):
    """視線の塊 × その樹冠が差し掛かる石段 ── [(箱の番号, 石段, どちら, 幹の離れ m, 掛かり m,
    勾配 %, 要る枝下 m)]。

    ⭐ **`edaShitaFrom` の規約はここが唯一の実装**【中2 庭方 2026-09-08 十二巡目】── 図が刷る値と
    検査が測る値と、指図が宣言する枝下が**同じ一本の式**から出るようにする。
    ⚠ **石段は登る**ので、幹の足元で測った枝下は、樹冠が差し掛かる先の踏面の上では
    **樹冠の張り出し × その石段の勾配**だけ目減りする。
    ⛔ 対象は `axis` の一本だけにしない【低5 検図15巡目】── **箱に最も近い石段**も測る。
    """
    ken = d["const"]["ken"]
    eda = ((d["planting"]["plantRule"].get("crownRule") or {}).get("takagi") or {}).get("edaShitaMinM")
    cr = view_cluster_crown(d, c)
    bx = cluster_boxes(c)
    if eda is None or cr is None or not bx: return []
    rr = cr[1] / 2.0
    kd = [k for k in d["kaidans"] if k["name"] == c.get("axis")]
    out = []
    for j, rect in enumerate(bx):
        seen = []
        near = _kaidan_near_box(d, rect)
        for tag, k in (("軸", kd[0] if kd else None),
                       ("箱に最も近い", near[0] if near else None)):
            if k is None or k["name"] in seen: continue
            seen.append(k["name"])
            pts = [tuple(x) for x in (k.get("pts") or [k["a"], k["b"]])]
            dd = min(_rect_seg_dist(rect, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            hw2 = kaidan_wken(d, k) / 2.0
            gr = (k.get("grade") or 0.0) / 100.0
            out.append((j + 1, k, tag, (dd - hw2) * ken, (rr / ken - (dd - hw2)) * ken,
                        k.get("grade") or 0.0, eda + max(0.0, rr) * gr))
    return out


def derive_view_eda(d):
    """`viewClusters[].edaShitaFrom` から**枝下**を起こす【中2 庭方 2026-09-08 十二巡目】。

    ⛔ 数を json に持たない ── 樹冠(部材と丈からの従属値)と石段の勾配から毎回算出する。
    ⛔ **宣言(`edaShitaFrom`)が無い塊には何も入れない** — 既定で高木の下限へ落ちると、
    棟梁は平地の値で建て、坂の踏面の上に枝が来る(検査が『宣言していない』と刷る)。
    """
    for c in d["planting"].get("viewClusters", []):
        if not c.get("edaShitaFrom") or c.get("edaShita") is not None: continue
        rows = view_cluster_eda_rows(d, c)
        if rows: c["edaShita"] = max(q[6] for q in rows)


def _kaidan_near_box(d, rect):
    """箱に**最も近い石段**と、その敷きの縁までの離れ(間)。⛔ `axis` の一本で代表させない
    【低5 検図15巡目 → 2026-09-08】── 額縁の樹冠は女坂の踏面へも掛かる。"""
    best = None
    for k in d["kaidans"]:
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        dd = min(_rect_seg_dist(rect, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        hw = kaidan_wken(d, k) / 2.0
        if best is None or dd - hw < best[1]: best = (k, dd - hw, dd, hw)
    return best


def _mikomi_half_deg(d, vp, c):
    """視点 `vp` から『**見えていなければならない物**』を見込む半角[°]。

    ⭐ **軸の石段の上端の敷きの隅**と、**眼から見てその先に立つ門の平面の隅**の envelope。
    ⛔ 数を持たない(石段の幅・門の平面・視点からの従属値)。⛔ 門の名を焼き込まない ──
    『軸線の上に立ち、石段の上端より遠い門』として図が同定する。
    """
    kd = [k for k in d["kaidans"] if k["name"] == c.get("axis")]
    if not kd or not vp: return (None, [])
    k = kd[0]
    eu, ev = vp["uv"]
    pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
    far = max(pts, key=lambda q: math.hypot(q[0] - eu, q[1] - ev))
    hw = kaidan_wken(d, k) / 2.0
    src = [("石段『%s』の上端の敷き" % k["name"], far[0], far[1] + hw),
           ("石段『%s』の上端の敷き" % k["name"], far[0], far[1] - hw)]
    for gt in d["gates"]:
        if gt.get("u") is None: continue
        hu, hv = gt["plan"]["du"] / 2.0, gt["plan"]["dv"] / 2.0
        if abs(gt["v"] - ev) > hv + hw: continue          # 軸線の上に立っていない
        if math.hypot(gt["u"] - eu, gt["v"] - ev) < math.hypot(far[0] - eu, far[1] - ev): continue
        for su in (-1, 1):
            for sv in (-1, 1):
                src.append(("門『%s』" % gt["name"], gt["u"] + su * hu, gt["v"] + sv * hv))
    rows = []
    for nm, u, v in src:
        du = abs(u - eu)
        if du < 1e-6: continue
        rows.append((math.degrees(math.atan2(abs(v - ev), du)), nm))
    if not rows: return (None, [])
    return (max(q[0] for q in rows), rows)


def _view_cluster_rows(d):
    """視線の塊の**幾何**── 幹の離れ・樹冠・石段の縁からの余裕・頭の抜け・軸の抜け。

    ⭐ 2026-09-08 ── 額縁が額縁として成り立っているかは**箱の縁と樹冠の半径**で読む。
    ⛔ 数を json に持たない(箱・丈・部材からの従属値)。⚠ 見込み角は「視点」の表も刷る。
    ⭐ **物差しの符号を直した**【裁き4 庭方 2026-09-08】── 旧版は「樹冠が笠石の上へ出たら
    額縁が踏面へ被る」と読んで**負を欠陥**にしていたが、⭕ **樹冠が笠石の上へ出るのは役そのもの**
    である。⇒ 代わりに**役を測る二条項**を置く:
      ① **頭の抜け** ── 樹冠が石段の上へ差し掛かる所で(枝下 − その位置の踏面の上がり)が
         高木の `edaShitaMinM` 以上。⚠ **石段は登る**ので、幹の足元で測った枝下では足りない。
      ② **軸の抜け** ── 視点から見た樹冠の内縁の方位が、**見えていなければならない物**
         (石段の上端の敷きと、その先の門)の見込みへ食い込まない。
    ⚠ ①で塊が `edaShita` を宣言していないときは**要る枝下**を刷る(⛔ 発明しない・仕立ての条件)。
    ⛔ 対象は `axis` の一本だけにしない【低5 検図15巡目】── **箱に最も近い石段**も測る。
    戻り値 (⛔止める, 〔記録〕)。
    """
    bad, out = [], []
    ken = d["const"]["ken"]
    eda = ((d["planting"]["plantRule"].get("crownRule") or {}).get("takagi") or {}).get("edaShitaMinM")
    for c in d["planting"].get("viewClusters", []):
        bx = cluster_boxes(c)
        if not bx: continue
        ax = c.get("axis")
        kd = [k for k in d["kaidans"] if k["name"] == ax]
        hw = (kaidan_wken(d, kd[0]) / 2.0 * ken) if kd else None
        vmin = min(min(abs(q[1]), abs(q[3])) for q in bx) * ken
        vmax = max(max(abs(q[1]), abs(q[3])) for q in bx) * ken
        h = c.get("matsuH")
        cr = view_cluster_crown(d, c)
        rr = (cr[1] / 2.0) if cr else None
        seg = ("塊『%s』── 跨ぐ帯 %s ／ 丈 %s m【従属 — 跨ぐ帯の `matsuH` の共通部分】"
               % (c["name"], "・".join("帯%d" % q for q in (c.get("_bands") or [])) or "—",
                  _rng(h)))
        seg += " ／ 幹は軸から %.2f〜%.2f m" % (vmin, vmax)
        if rr is not None:
            seg += (" ／ 樹冠の半径 %.2f〜%.2f m(変種で振れる)／ 樹冠の内縁は軸から "
                    "%.2f〜%.2f m" % (cr[0] / 2.0, rr, vmin - rr, vmin - cr[0] / 2.0))
            if hw is not None:
                # ⭐ **符号は「掛かり」正の一本に揃える**【低3 庭方 2026-09-08 十二巡目】──
                #    同じ量に二通りの符号が同居していると、裁き4 で向きを反転させたばかりの
                #    箇所だけに危険が集まる。⛔ 「内縁の位置」と「掛かり」を並べて刷らない。
                seg += ("(石段『%s』の敷きの縁 半幅 %.2f m への **掛かり %+.2f〜%+.2f m** ── "
                        "⭕ **正(=笠石の上へ出る)のは役そのもの**であって事故ではない"
                        "【裁き4 庭方 2026-09-08】)"
                        % (ax, hw, hw - (vmin - cr[0] / 2.0), hw - (vmin - rr)))
        if c.get("spacing"):
            pk = d["planting"]["plantRule"].get("packRatio", 1.0)
            seg += " ／ 塊内の芯々(packRatio 後) %.2f m" % (c["spacing"] * ken * pk)
            if cr: seg += " ＜ 樹冠径 %.2f〜%.2f m = **一続きの側壁**" % (cr[0], cr[1])
        out.append(seg + "【算出】")
        # ── ① 頭の抜け(⛔ `axis` の一本で代表させない・低5 検図15巡目)
        for j, k, tag, gap, over, grade, need in view_cluster_eda_rows(d, c):
            txt = ("塊『%s』の箱 其%d × 石段『%s』(%s)── 幹の離れ %.2f m ／ "
                   "樹冠の敷きへの **掛かり %+.2f m**(正=踏面の上へ差し掛かる)／ 勾配 %g%% ／ "
                   "**要る枝下 %.2f m**(= 高木の枝下の下限 %.2f + 樹冠の張り出し %.2f × 勾配)"
                   % (c["name"], j, k["name"], tag, gap, over, grade, need, eda or 0.0,
                      rr or 0.0))
            de = c.get("edaShita")
            if de is None:
                bad.append(txt + " ／ ⛔ **塊が枝下を宣言していない** — 宣言が無ければ棟梁は"
                                 "高木の下限で建て、坂の踏面の上に枝が来る。⛔ 発明しない ── "
                                 "`viewClusters[].edaShitaFrom` に**規約**で宣言する"
                                 "(中2 庭方 2026-09-08)")
            elif de < need - 1e-9:
                bad.append(txt + " ／ ⛔ 宣言された枝下 %.2f m では届かない" % de)
            else:
                out.append(txt + " ／ 枝下 %.2f m ⭕【算出 — 枝下は `edaShitaFrom` の従属値"
                                 "(⛔ 数で持たない)。⚠ 石段は登るので幹の足元で測った枝下では"
                                 "足りない】" % de)
        de = c.get("edaShita")
        if de is not None and h:
            out.append("塊『%s』の**枝下 %.2f m**(= 差し掛かるすべての石段の『要る枝下』の最大)"
                       "／ 枝下 ÷ 丈 %.2f〜%.2f【算出 — ⛔ 数で持たない。⚠ **枝下は鉛直で測る**"
                       "(`plantRule.crownRule.takagi.edaShitaBasis`)。⚠ **部材の枝下は目録に"
                       "無い**ので、この値は部材と突き合わせられない → `_pending`"
                       "「目録に部材の枝下が無い」】" % (c["name"], de, de / h[1], de / h[0]))
        # ── ② 軸の抜け
        vps = [q for q in d.get("viewpoints", []) if c["name"] in (q.get("shows") or [])]
        for vp in vps:
            mk, rows = _mikomi_half_deg(d, vp, c)
            if mk is None or rr is None: continue
            eu, ev = vp["uv"]
            az = None
            for rect in bx:
                u1 = max(rect[0], rect[2]) + rr / ken
                vi = min(abs(rect[1]), abs(rect[3])) - rr / ken
                du = eu - u1
                if du <= 1e-6: continue
                a_ = math.degrees(math.atan2(max(0.0, vi), du))
                az = a_ if az is None else min(az, a_)
            if az is None: continue
            src = max(rows, key=lambda q: q[0])[1]
            if az <= mk + 1e-9:
                bad.append("塊『%s』── %s から見た**樹冠の内縁の方位 %.1f°** が、見えていなければ"
                           "ならない物の見込み ±%.1f°(%s)へ食い込む — 額縁が軸を塞ぐ"
                           "(裁き4 庭方 2026-09-08)" % (c["name"], vp["name"], az, mk, src))
            else:
                out.append("塊『%s』の**軸の抜け** ── %s から 樹冠の内縁の方位 %.1f° ＞ 見込み "
                           "±%.1f°(最も外まで来るのは %s)／ 余裕 %+.1f°【算出 — ⛔ 樹冠は"
                           "箱を樹冠の半径だけ広げた矩形の隅で測る(円の接線より辛い側)】"
                           % (c["name"], vp["name"], az, mk, src, az - mk))
    return bad, out


def cluster_pack_check(d, g):
    """**塊が塊として組めるか**【中3 庭方 2026-09-07 八巡目】。

    ⛔ ① 箱を持つ塊に `spacing` の宣言が無い(= 測れない)
    ⛔ ② **箱の面積 ≥ n ×(spacing × packRatio × 間)²**
    ⛔ ③ **一つの塊に落葉高木は一本まで**(頭は一つ。⛔ 欅と椋を同じ塊に入れない)
    ⛔ ④ `boxFrom` を宣言していながら箱が解けていない
    〔記録〕**林冠閉鎖度**(Σπr² ÷ 箱の面積)── ⛔ 合否に使わない。箱は幹の定義域であって
    樹冠の定義域ではないので、100% を超えるのは欠陥ではない(低3 庭方 2026-09-07)。
    """
    bad, note = [], []
    ken = d["const"]["ken"]
    pack = d["planting"]["plantRule"]["packRatio"]
    # ⚠ **視線の塊(`planting.viewClusters`)も同じ条件に載せる** — 区にも帯にも属さないが
    #    箱と本数と芯々を持つ以上、噛み合っていなければ塊にならない(⛔ 輪の外に置かない)。
    src = (list(d["gardens"]) + [b for b in d["slopeBands"] if b.get("clusters")]
           + view_holders(d))
    _vb, _vn = _view_cluster_rows(d)
    bad += _vb
    note += _vn
    # ⭐ **視線の塊の本数がどの帯から引かれたか**【低3 検図15巡目 → 2026-09-08】
    band_stats(d, g)                                  # ⚠ 走査を先に済ませる(_VCUT を満たす)
    for nm, j, k, per in _VCUT.get("fall", []):
        bad.append("視線の塊『%s』の箱 其%d の芯が**どの帯の面にも落ちない**のに、既定で 帯%d へ "
                   "%g 本 落としている — ⛔ 黙って移す道は塞ぐ(`avoid` や敷きを動かした日に"
                   "本数が黙って移る。低3 検図15巡目 2026-09-08)" % (nm, j, k, per))
    for nm, j, k, per in _VCUT.get("on", []):
        note.append("視線の塊『%s』の箱 其%d ── 芯が落ちる 帯%d から %g 本 差し引く【算出】"
                    % (nm, j, k, per))
    for gd in src:
        for c in gd.get("clusters", []):
            nm = "%s の塊「%s」" % (_gname(gd), c["name"])
            # ⭐ **輪郭で測る**(2026-09-08 C-1)── 参道の林縁は**線に沿う平行四辺形**で、
            #    軸平行の箱で囲むと幅が 9.1 間になり、⛔ 広さの条件が意味を失う。
            QS = cluster_polys(c)
            if (c.get("boxFrom") or c.get("alongTakagiEdgeLine")) and not QS:
                bad.append("%s は宣言(`boxFrom`/`alongTakagiEdgeLine`)から**輪郭が解けていない** — "
                           "指し先(`sando.roadside.takagiEdgeLine`)を確かめる" % nm)
                continue
            n = cluster_n(c)
            if not QS: continue
            sp = cluster_spacing(d, c)
            if sp is None:
                bad.append("%s は輪郭を持つのに **芯々(`spacing`/`spacingFrom`)の宣言が無い** — "
                           "宣言が無いと『塊の中で樹冠がどう重なるか』も『輪郭に何本入るか』も"
                           "測れず、**いちばん混んだ塊だけが黙る**(中3 庭方 2026-09-07)" % nm)
                continue
            sp_ = sp
            A = sum(poly_area(Q) for Q in QS) * ken * ken
            # ⭐ **『何本入るか』は面積ではなく実際の詰みで測る**【2026-09-08 十六巡目 C-1】──
            #    ⛔ `n × 芯々²` の面積の条件は**塊(2次元の塊)にしか当たらない**。参道の林縁は
            #    幅 1 間の**一列の帯**で、面積では落ちるが線に沿えば余裕で入る。
            #    ⭕ `scatter_pts` と**同じ詰み方**(`_scatter_take`)で数える ── ⛔ 二つの物差しを
            #    持たない(検査が通って撒けない、撒けて検査が落ちる、のどちらも作らない)。
            # ⭐ **線に沿う塊は `packRatio` を掛けない**【A-7 庭方 2026-09-09 十九巡目】
            onl = bool(c.get("alongTakagiEdgeLine") and c.get("poly"))
            sp_eff = sp if onl else sp * pack
            how = ("弧長を芯々で刻む(⛔ `packRatio` は面へ撒くときの詰まりなので当てない)"
                   if onl else "packRatio %.2f" % pack)
            cap_n = cluster_capacity(d, c)
            if cap_n is not None and cap_n < int(math.ceil(n - 1e-9)):
                bad.append("%s の輪郭には 芯々 %.2f 間(%s = %.2f m)で **%d 本しか"
                           "入らない**のに %g 本を宣言している(輪郭 %.1f m²)— "
                           "**輪郭・本数・芯々が噛み合っていない**"
                           % (nm, sp, how, sp_eff * ken, cap_n, n, A))
            else:
                note.append("%s の輪郭 %.1f m² ── 芯々 %.2f m(%s)で **%s 本**入る ≥ 宣言 %g 本"
                            "【算出 — ⛔ 面積の条件では測らない(一列の帯が落ちる)】"
                            % (nm, A, sp_eff * ken, how, "—" if cap_n is None else cap_n, n))
            # ④ ⭐ **`nFrom` の従属値と `mix` の和の照合**【C-1 庭方 2026-09-08 十六巡目】
            #    ⛔ 本数を `n` と `mix` の二箇所に持たない。線が動けばここが鳴る。
            if c.get("nFrom"):
                bad.append("%s が `nFrom`(本数の従属値)を宣言しているが、その出所だった "
                           "`takagiEdgeLine.firstRowSpacing` は **2026-09-09 十八巡目に廃した**"
                           "(指4 庭方)— ⛔ 引けない従属は誰も辿れない(規則19)" % nm)
            # ⭐ **塊と塊の離れ**(`groups` から展開した兄弟)【中6 庭方 2026-09-09 十七巡目】
            if c.get("_gapMinKen") is not None:
                gk9, gm9 = c.get("_gapKen"), c["_gapMinKen"]
                if gk9 is None or gk9 < gm9 - 1e-9:
                    bad.append("%s ── 親『%s』の `groups` を弧長へ割り付けた結果、塊と塊の離れが "
                               "**%s 間** で下限 `groupGapKen` %g 間 を割る。⛔ 離れを詰めると"
                               "**一列に戻る**(中6 庭方 2026-09-09)── `vRange` を伸ばすか、"
                               "塊の中の芯々(`groupSpacingKen`)を詰めるかは意匠"
                               % (nm, c.get("_ofGroup"),
                                  ("%.2f" % gk9) if gk9 is not None else "引けない", gm9))
                else:
                    note.append("%s ── 親『%s』の `groups` からの展開。塊と塊の離れ **%.2f 間 = "
                                "%.2f m**(下限 %g 間)／ 塊の中の芯々 %.2f 間【算出 — "
                                "⛔ 位置も芯々も数で持たない(中6 庭方 2026-09-09)】"
                                % (nm, c.get("_ofGroup"), gk9, gk9 * ken, gm9, sp_ or 0.0))
            # ③ 落葉高木は一塊に一本
            nrk = sum(k for kd, k in cluster_mix(c) if kd != "松")
            if nrk > 1:
                bad.append("%s に落葉高木が %d 本入っている — **一つの塊に落葉高木は一本まで**"
                           "(社叢は松の林冠の上に落葉の大木がまばらに頭を出す姿で、頭が二つに"
                           "なると『主景は一点』を破る。低3 庭方 2026-09-07)" % (nm, nrk))
            # 〔記録〕同層の芯々−樹冠 と 林冠閉鎖度
            if not any(zone_h(d, gd)): continue
            sig = 0.0
            lay = {}
            for kind, pt, k, h, cr, sk, vs, _a, _b in cluster_parts(d, gd, c):
                if cr is None: continue
                r = (cr[0] + cr[1]) / 4.0
                sig += k * math.pi * r * r
                lay.setdefault(sk, []).append((kind, k, (cr[0] + cr[1]) / 2.0))
            for sk, qs in lay.items():
                tot = sum(q[1] for q in qs)
                if tot < 2:
                    note.append("%s の%s層は 1 本 — **同層に相手が居ないので芯々−樹冠は測らない**"
                                "(⛔ 跨層で測らない。低3 庭方 2026-09-07)"
                                % (nm, "松" if sk == "matsu" else "落葉"))
                    continue
                cw = sum(q[1] * q[2] for q in qs) / float(tot)
                sp = sp_ * (1.0 if onl else pack) * ken
                note.append("%s の%s層 %d 本 ── 同層の芯々(%s)%.3f m ／ 樹冠(加重平均)"
                            "%.3f m ／ 差 %+.3f m ／ 芯々÷樹冠 %.2f【算出 — ⛔ 下限は置かない】"
                            % (nm, "松" if sk == "matsu" else "落葉", tot,
                               "弧長の刻み" if onl else "packRatio 後", sp, cw, sp - cw,
                               sp / cw if cw else 0.0))
            # ⭐ **頭が一つになるか**【2026-09-08】── 二本の塊は「箱の隅と隅に落ちても樹冠が触れる」
            #    ことで役が成り立つ(庭方9巡目 中1 が `widthKen` を半分にしたのはこの理屈)。
            #    ⛔ ⛔にしない ── 箱を縮めるかどうかは庭方の意匠。⭕ 数を毎回刷って見えるようにする。
            if int(round(n)) == 2 and len(QS) == 1 and lay:
                _us = [q[0] for q in QS[0]]; _vs = [q[1] for q in QS[0]]
                diag = math.hypot(max(_us) - min(_us), max(_vs) - min(_vs)) * ken
                rs = sorted((q[2] / 2.0 for qs in lay.values() for q in qs), reverse=True)
                if len(rs) >= 2:
                    note.append("%s の**頭が一つになるか** ── 箱の対角 %.2f m ／ 樹冠の半径の和 "
                                "%.2f + %.2f = %.2f m ／ **差 %+.2f m**(正=隅と隅に落ちても"
                                "樹冠が触れて頭が一つになる)【算出 — ⛔ 合否に使わない。"
                                "箱を縮めるかどうかは庭方の意匠(→ `_pending`"
                                "「目録の樹の幅がビルボードの板の寸法である疑い」)】"
                                % (nm, diag, rs[0], rs[1], rs[0] + rs[1], rs[0] + rs[1] - diag))
            if sig > 0 and A > 0:
                note.append("%s の**林冠閉鎖度** %.0f%%(Σπr² %.1f m² ÷ 箱 %.1f m²)"
                            "【〔記録〕— ⛔ 合否に使わない。箱は**幹の定義域**であって樹冠の"
                            "定義域ではない(低3 庭方 2026-09-07)。⚠ **樹冠は丈の範囲の中央で採る**"
                            "(⛔ 上端で採らない)── 閉鎖度が測るのは『その帯に立つ林の"
                            "**期待される**姿』であり、丈は範囲に一様に現れるのだから中央が正しい"
                            "統計である。上端で採った値は**上界**にすぎない(低8 庭方 2026-09-07)】"
                            % (nm, 100.0 * sig / A, sig, A))
    # ⭐ **塊を「またぐ」同層の芯々**【中6 検図21巡目 → 2026-09-09】── ⛔ 塊の中だけを測る版では
    #    継ぎ目が見えない。実測で『辻の留め 松01』と『参道の林縁 松02』が芯々 3.24 m(樹冠の
    #    半径の和 9.77 m)で**完全に一つの塊に融合**しており、⛔ 『主景は一点』(辻の留め)と
    #    『林縁は一列』(参道の林縁)がこの継ぎ目で**同時に**破れていた。
    #    ⛔ **⛔にしない** ── 始末(箱を切るか役を分けるか)は庭方の意匠。検査は**鳴らすまで**。
    if os.path.exists(IMPL_OUT):
        im9 = json.load(open(IMPL_OUT, encoding="utf-8"))
        own9 = {}
        for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
            for c in gd.get("clusters", []):
                own9["%s／%s" % (gd["name"], c["name"])] = cluster_spacing(d, c)
        P9 = [q for q in ((im9.get("planting") or {}).get("points") or [])
              if q.get("group") in own9 and q.get("layer") in ("松", "落葉")]
        worst9, npair9 = None, 0
        for i in range(len(P9)):
            for j in range(i + 1, len(P9)):
                a9, b9 = P9[i], P9[j]
                if a9["group"] == b9["group"]: continue      # 塊の中は上で測っている
                dd = math.hypot(a9["world"][0] - b9["world"][0],
                                a9["world"][1] - b9["world"][1])
                # 二つの塊の宣言のうち**厳しいほう**(芯々 × packRatio)を閾に採る
                lim9 = min(q for q in (own9[a9["group"]], own9[b9["group"]]) if q) * pack * ken
                if dd < lim9 - 1e-9:
                    npair9 += 1
                    if worst9 is None or (lim9 - dd) > (worst9[0] - worst9[1]):
                        worst9 = (lim9, dd, a9, b9)
        if worst9 is not None:
            a9, b9 = worst9[2], worst9[3]
            note.append("⚠ **塊をまたぐ同層の芯々が宣言を割る対 %d 組** ── 最も辛いのは"
                        "『%s』(%s)×『%s』(%s)で 芯々 **%.2f m** ＜ 閾 %.2f m"
                        "(二つの塊の `spacing` の厳しいほう × `packRatio`)／ "
                        "樹冠の半径の和 %.2f m【算出 — 中6 検図21巡目。⛔ ⛔にしない ── "
                        "始末(箱を切るか役を分けるか)は庭方の意匠なので `_pending`"
                        "「塊どうしが継ぎ目で融合している」へ。⛔ 閾を緩めて黙らせない】"
                        % (npair9, a9["name"], a9["group"], b9["name"], b9["group"],
                           worst9[1], worst9[0],
                           ((a9.get("crownM") or 0.0) + (b9.get("crownM") or 0.0)) / 2.0))
        else:
            note.append("塊をまたぐ同層の芯々 ── 宣言を割る対 **0 組**(測った点 %d・"
                        "総当たり %d 対)【算出 — 中6 検図21巡目。⛔ 0 件は合格ではなく未測定"
                        "なので、測った数を必ず添える】"
                        % (len(P9), len(P9) * (len(P9) - 1) // 2))
    return bad, note


def rinen_overhang_check(d):
    """**参道への林縁の張り出し**が路面へ出ていないか【裁定2 庭方 2026-09-07 八巡目】。

    ⭕ 枝が**路肩の上へ差し掛かるのは景として正**(役「路肩に影を落とす林縁」そのもの)。
    ⛔ **下限は置かない**(張り出しが正でなければならない、とはしない)。
    ⛔ 上限だけ ── 樹冠が路面(側溝の外)の上に出ないこと
       = 張り出し ≤ **局所の**(路肩+側溝)− `marginM`。⛔ 代表値を当てない。
    """
    bad, note = [], []
    for b in d["slopeBands"]:
        for c in b.get("clusters", []):
            if not c.get("overhangFrom"): continue
            oh = overhang_range(d)
            lim = overhang_limit(d, c)
            if not oh or oh[0] is None:
                note.append("参道の林縁の張り出しを測れない(部材が目録に無い %d 点)"
                            % (oh[3] if oh else 0))
                continue
            if not lim:
                bad.append("参道の林縁の張り出しの**上限を測れない** — "
                           "`overhangFrom.marginM` か `vRange`、または参道の道敷 `sando.area` の"
                           "宣言が足りない(⛔ 代表値を当てない)")
                continue
            for v, mx, ro, rs in lim:
                note.append("参道の林縁 v %.1f ── 道敷 %.3f m ／ 路肩 %.3f m ／ 路肩+側溝 %.3f m "
                            "→ 張り出しの上限 %.3f m【従属 — ⛔ 代表値ではなく局所の道敷幅から】"
                            % (v, sando_road_width(d, v) or 0.0, ro, rs, mx))
            mn = min(q[1] for q in lim)
            vmn = [q[0] for q in lim if q[1] == mn][0]
            if oh[1] > mn + 1e-9:
                bad.append("参道の林縁の張り出し %+.3f m が、v %.1f の上限 %.3f m を越える — "
                           "樹冠が路面(側溝の外)の上へ出る" % (oh[1], vmn, mn))
            else:
                note.append("参道の林縁の張り出し %+.3f〜%+.3f m ／ 最も厳しい上限 %.3f m"
                            "(v %.1f)── 余裕 %+.3f m。⭕ **正=路肩の上へ差し掛かるのは景として正**"
                            "(役『路肩に影を落とす林縁』)・⛔ 下限は置かない【算出 — 裁定2】"
                            % (oh[0], oh[1], mn, vmn, mn - oh[1]))
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
        # ⭐ **合格の側も一行刷る**【B-5 検図22巡目 → 2026-09-09 十九巡目】── ⛔ 「⛔0/〔記録〕0」
        #    では**測って綺麗なのか早々に `return` したのか**が区別できない(規則19)。
        note.insert(0, "空地『%s』 ⭕ ── %.2f 坪(%d セル・刻み %g 間)を全数走査 ── "
                       "平場『%s』の輪郭の外 0 坪 ／ 低木の帯 %d 本・動線 %d 本と突き合わせ済み"
                       "【算出 — ⛔ 0 件は合格ではなく未測定なので、**何をどれだけ測ったか**を刷る】"
                    % (gd["name"], len(cells) * ct, len(cells), st,
                       gd.get("clip") or "—", len(bands), len(d.get("routes") or [])))
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
    # ⭐ **2026-09-09 十九巡目 B-8 で1件足した。**幣殿の床から本殿の床へ上がる木階は
    #    **本殿と幣殿を継ぐ一間(作り合い)の中にある** ── 屋根の下の内法の段なので、
    #    棟と重なるのが正しい姿である(⛔ 向拝の階は外へ張り出すので事情が違う)。
    ("棟:作り合い", "石段:本殿の木階(幣殿の床 → 本殿の床)"),
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
            for j, Q in enumerate(cluster_polys(c)):   # ⭐ 箱でなく輪郭(2026-09-08 C-1)
                poly_item("塊:%s%s" % (c["name"], "" if j == 0 else "(其%d)" % (j + 1)), Q)
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
    bad, note, okarea = _ovl_scan(it, ok, st, d, minTsubo)
    # ⭐ **収束の判定 ── 二段連続で⛔の件数が変わらないこと**(検図9巡目 中1)。
    #    ⛔ 一段だけ見て収束と言わない。足切りが絶対値になったので、件数が動くのは
    #    「粗すぎて見えていなかった当たりが見えた」ときだけになる
    cnt = [len(bad)]
    fine = st
    for _k in range(2):
        fine /= 2.0
        b2, _n2, _o2 = _ovl_scan(it, ok, fine, d, minTsubo)
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
    # ⭐ **白名簿にも両方向の見張りを掛ける**【検図12巡目 低2 → 2026-09-07】。
    #    ⚠ `kakoiCross.roster` は `pending` の指し先を要求し `roster_guard` が両方向で見張るのに、
    #    `_OVL_OK` は**コード内のベタ列で片方向の見張りも無かった**。
    #    ⛔ **名の消えた許可**(指す面が図から無くなった組)と **死んだ許可**(幾何として一点も
    #    重ならない組)は⛔で止める。⭕ **足切りの下の空振り**は〔記録〕で名指す ── ⛔ ⛔にすると
    #    「足切りを下げた日にだけ通る」という逆立ちした条件になる(足切りは部材の見付から出る絶対値)。
    nms = set(q[0] for q in it)
    gone = [q for q in sorted(ok) if q[0] not in nms or q[1] not in nms]
    for q in gone:
        bad.append("意図された接合の白名簿 `_OVL_OK` の『%s × %s』が指す面が図に無い — "
                   "名が変わったか消えた(死んだポインタ)" % q)
    live = ["%s × %s" % q for q in sorted(ok) if okarea.get(q, 0.0) > 0.0]
    bad += roster_guard(["%s × %s" % q for q in sorted(ok) if q not in gone], live,
                        "意図された接合の白名簿", "`_OVL_OK`")
    karaburi = [(q, okarea.get(q, 0.0)) for q in sorted(ok)
                if q not in gone and 0.0 < okarea.get(q, 0.0) <= minTsubo]
    note.append("**意図された接合の白名簿 `_OVL_OK` の実測** %d 組 ── 走査で坪が立つ %d 組 ／ "
                "**足切り %.4f 坪(%.5f m²)の下で空振り %d 組**%s ／ 幾何として一点も重ならない"
                "(死んだ許可)%d 組【算出 — ⛔ 許可は『重なってよい』という宣言なので、重なって"
                "いない組を許可しておくと、そこが本当に重なった日に黙って通る】"
                % (len(ok), sum(1 for q in sorted(ok) if okarea.get(q, 0.0) > minTsubo),
                   minTsubo, minTsubo * TSUBO, len(karaburi),
                   (" — " + "／".join("『%s × %s』%.5f m²" % (q[0], q[1], a_ * TSUBO)
                                      for q, a_ in karaburi)) if karaburi else "",
                   sum(1 for q in sorted(ok) if q not in gone and okarea.get(q, 0.0) <= 0.0)))
    note.append("**収束の確認** — 刻みを二段(%s 間)下げて⛔の件数は %s%s【算出 — "
                "⛔ 一段だけ見て収束と言わない(検図9巡目 中1)】"
                % ("・".join("%.6f" % (st / (2.0 ** (i + 1))) for i in range(len(cnt) - 1)),
                   "→".join("%d" % q for q in cnt),
                   "(**二段連続で変わらない = 収束**)" if len(set(cnt)) == 1
                   else "(⛔ **動いている = 収束していない**)"))
    return bad, note


def _ovl_pair_area(A_, B_, st, d):
    """二つの面の重なり[坪]。⛔ 判定則は `_ovl_scan` と一字一句同じ(刻みだけ引数)。"""
    (na, fa, ba, Pa), (nb, fb, bb, Pb) = A_, B_
    u0, v0 = max(ba[0], bb[0]), max(ba[1], bb[1])
    u1, v1 = min(ba[2], bb[2]), min(ba[3], bb[3])
    if u1 - u0 <= 0 or v1 - v0 <= 0: return 0.0
    ct = cell_tsubo(d, st)
    n = 0
    v = v0 + st / 2.0
    while v < v1:
        xa = _poly_row(Pa, v) if Pa is not None else None
        xb = _poly_row(Pb, v) if Pb is not None else None
        if (xa is None or xa) and (xb is None or xb):
            u = u0 + st / 2.0
            while u < u1:
                if (_row_in(xa, u) if xa is not None else fa((u, v))) and \
                   (_row_in(xb, u) if xb is not None else fb((u, v))): n += 1
                u += st
        v += st
    return n * ct


def _ovl_bbox_side(A_, B_):
    """二つの面の bbox の共通部分の短辺[間]。⛔ 白名簿を測り直す刻みを出すためだけ。"""
    ba, bb = A_[2], B_[2]
    return min(min(ba[2], bb[2]) - max(ba[0], bb[0]), min(ba[3], bb[3]) - max(ba[1], bb[1]))


def _ovl_scan(it, ok, st, d, minTsubo):
    """総当たりの一巡(刻み `st`)。戻り値 (⛔止める, 〔記録〕)。

    ⚠ **多角形は行ごとに交点を出して判定する**(2026-09-07 検図9巡目 中1)— 判定の結果は
    `in_poly` と同じで、⛔ 物差しは変えていない。収束を見るのに刻みを二段下げるので、
    素の点内外判定のままでは組み上げが数分に伸びる。
    """
    ct = cell_tsubo(d, st)
    bad, note, okarea = [], [], {}
    for i in range(len(it)):
        for j in range(i + 1, len(it)):
            (na, fa, ba, Pa), (nb, fb, bb, Pb) = it[i], it[j]
            if tuple(sorted((na, nb))) in ok:
                # ⭐ **白名簿の組も測る**【検図12巡目 低2 → 2026-09-07】── 旧版は走査ごと飛ばして
                #    いたので、⛔ **死んだ許可**(重なっていない組を許可したまま)が見張られていなかった。
                #    ⚠ 足切りの下でも**幾何としては重なっている**組があるので、0 と出たら
                #    **共通 bbox の短辺から刻みを取り直して**測る(⛔ 判定則は変えない)。
                A_ = _ovl_pair_area(it[i], it[j], st, d)
                if A_ <= 0.0:
                    side = _ovl_bbox_side(it[i], it[j])
                    if side > 0:
                        A_ = _ovl_pair_area(it[i], it[j], min(st, side / 64.0), d)
                # ⚠ **同じ名の面が複数ある**(玉垣は口で分かれるので『東面 上』が3片)。
                #    ⛔ 上書きしない — 一片でも重なっていればその許可は生きている。
                k_ = tuple(sorted((na, nb)))
                okarea[k_] = max(okarea.get(k_, 0.0), A_)
                continue
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
    return bad, note, okarea


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

    ⭐ **合格の側も一行刷る**【B-5 検図22巡目 → 2026-09-09 十九巡目】── ⛔ 「⛔0/〔記録〕0」では
      **測って綺麗なのか早々に `return` したのか区別が付かない**(規則19)。
      ⚠ この検査は**全数照合**をしているのに、その事実が図に一行も出ていなかった。
    戻り値: (⛔止める, 〔記録〕)。
    """
    try:
        base = json.load(open(os.path.join(DOC, "base_dem.json"), encoding="utf-8"))
        cut = json.load(open(os.path.join(DOC, "sanno_dem.json"), encoding="utf-8"))
    except Exception as ex:
        return (["地形の出所を照合できない — **この検査は回っていない**(合格ではない): %s" % ex], [])

    if base["step"] != cut["step"]:
        return (["切り出しと正本で格子の刻みが違う(正本 %s / 切り出し %s)"
                 % (base["step"], cut["step"])], [])
    st = base["step"]
    fx, fz = (cut["x0"] - base["x0"]) / st, (cut["z0"] - base["z0"]) / st
    if fx != int(fx) or fz != int(fz):
        return (["切り出しの原点が正本の格子に乗っていない(dx=%.3f dz=%.3f セル)— "
                 "補間が挟まるので切り出しとして扱えない" % (fx, fz)], [])
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
        return (["切り出しの %d セルが正本 base_dem.json の範囲の外にある — "
                 "CANON_SPEC を広げて `build_base_dem.py --canon` から正本を作り直すこと"
                 "(規則13)" % out], [])
    if seen < 200:
        return (["地形の照合の標本が %d 点しか取れない — 切り出しか正本の範囲がおかしい" % seen], [])
    if worst > TERRAIN_TOL:
        return (["**種地が正本から来ていない** — 切り出しが正本と最大 %.2fm 食い違う "
                 "(x=%.0f z=%.0f: 切り出し %.2f / 正本 %.2f)。live terrain を吸っていないか"
                 "(規則13)" % (worst, wl[0], wl[1], wl[2], wl[3])], [])

    # 担当区画が切り出しに収まっているか(欠測を黙って図に出さないための関門・EDO-0014)
    try:
        P = json.load(open(os.path.join(DOC, "parcels.json"), encoding="utf-8"))
        P = P["parcels"] if isinstance(P, dict) and "parcels" in P else P
        P = {q["id"]: q for q in P}
    except Exception as ex:
        return (["区画を読めないので切り出しの覆いを検べられない — この検査は回っていない: %s"
                 % ex], [])
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
    note = ["地形の出自 ⭕ ── 切り出し `sanno_dem.json` %d×%d セル(刻み %g m)を正本 "
            "`base_dem.json` と **全数照合**(照合できた %d セル・**最大差 %.3f m** ≤ 許容 %.3f m)"
            "／ 担当区画 %d 件がすべて切り出しの内【算出 — B-5 検図22巡目 → 2026-09-09。"
            "⛔ 0 件は合格ではなく未測定なので、**測った量そのものを刷る**】"
            % (cut["nx"], cut["nz"], st, seen, worst, TERRAIN_TOL, len(ids))]
    return bad, note


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


def _stair_hit(d, g, x, z):
    """石段の通路(帯)に載る点なら **(石段の名, 設計高さ)**。載らなければ (None, None)。

    ⭐ **どの石段か**を返す【低4 検図16巡目 → 2026-09-08】── 切盛図の註が『男坂の盛土/切土』を
    語るのに、集計は『石段(男坂・女坂・参道の階)』の一括りしか持っておらず、**註の数がどの計算
    からも出ていなかった**。⛔ 註へ数を直書きしない ── 坂ごとに数えて刷る。
    """
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
                return (k["name"], stair_y_at(k, sfrac))
            acc += L
    return (None, None)


def _stair_y(d, g, x, z):
    """石段の通路(帯)の設計高さ。坂も造成の対象(2026-08-23 検図 — 図から丸ごと落ちていた)。"""
    return _stair_hit(d, g, x, z)[1]


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
    # ⛔ **他の囲いへ犬走りより近く並走する区間には柵を回さない**【検図11巡目 高1 → 2026-09-07】。
    #    平場の南西の縁は社殿を囲う透塀のすぐ外を通るので、輪郭を `ins` だけ内へ寄せた線が
    #    透塀と 0.15 m まで寄り、**二本の囲いの間に人の通れない溝**が残る。
    #    ⛔ 輪郭を南へ出して犬走りを取らない — 造成の量が動き、面を動かさないという裁定に触れる。
    #    ⭕ **回廊の前の東側と同じ作法**で、その区間だけ柵を回さない(⛔ 弦で結ばない)。
    #    ⛔ 区間を数で持たない — **節点間の区間ごとに他の囲いとの離れを測って決める従属値**。
    #    ⛔ **区間を「節点から節点まで」で落とさない** — 隅で一点だけ寄る辺まで丸ごと消える。
    #    ⭕ **近い所だけを落とす**(0.01 間で歩き、`ins` を割る連続した範囲をそのまま口にする)。
    osegs = [s for q in d["runs"] if q["name"] != "Ita_Keidai" for s in run_segs(q)]
    skips = []
    for i in range(len(pts) - 1):
        a, b_ = pts[i], pts[i + 1]
        L = math.hypot(b_[0] - a[0], b_[1] - a[1])
        if L < 1e-9: continue
        n = max(2, int(L / 0.01))
        at = lambda t: (a[0] + (b_[0] - a[0]) * t, a[1] + (b_[1] - a[1]) * t)
        #    ⛔ **点で測らない** — 相手の端が柵の線の脇に来る所は点どうしでは拾えない。
        #    刻みの小片と相手の区間の**線分どうしの距離**で測り、口は前後へ一刻み広げる
        #    (⛔ 口の縁ぎりぎりに 0.44 m の切れ端を残さない)。
        near = [min(_seg_seg_dist(at(j / float(n)), at((j + 1) / float(n)), c, e)
                    for c, e in osegs) < ins - 1e-9 for j in range(n)]
        j = 0
        while j < n:
            if not near[j]: j += 1; continue
            k = j
            while k + 1 < n and near[k + 1]: k += 1
            j0, k1 = max(0, j - 1), min(n, k + 2)
            cm = at((j0 + k1) / 2.0 / n)
            skips.append([cm[0], cm[1], L * (k1 - j0) / 2.0 / n])
            j = k + 1
    by["Ita_Keidai"]["pts"] = [[round(u, 3), round(v, 3)] for u, v in pts]
    by["Ita_Keidai"]["gaps"] = gaps + skips
    by["Ita_Keidai"]["skips"] = skips
    by["Ita_Keidai"].pop("gapU", None); by["Ita_Keidai"].pop("gapHalf", None)
    by["Ita_Keidai"]["_"] = ("境内の外周の**腰高の柵**【U ユーザー裁定 2026-09-07】。"
                             "**平場の輪郭から犬走り(`const.inubashiri`)ぶん内へ寄せて機械生成する** — "
                             "独立の座標を持たない(2026-08-23 検図 中-5)。"
                             "⚠ **回廊の基壇が東front なので東の張り出しには回さない**。"
                             "**開口は石段の頭と勝手口で自動に開く**(2026-08-24 検図 高-1)。"
                             "⚠ **他の囲いへ犬走りより近く並走する区間には回さない**"
                             "(南西の透塀の外・検図11巡目 高1)")


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


def slope_lands(d, near, nx, nz, top):
    """縁から外へ 1:batterFill で降ろした法面が **現地形に着地するか**(スキル §3b 関門3)。

    着地しない縁は崖の上に載っているので、法面ではなく**土留めで受ける**しかない。
    そこへ法面を描くと、法尻に1〜2mの垂直面が宙に残る(2026-08-23 検図 高-3)。

    ⭐ **覚え書きの鍵は「法尻の点 + 向き + 面の高さ」**【低1 検図20巡目 → 2026-09-09】。
      ⚠ 旧図は**法尻の点だけ**を鍵にしていたので、同じ法尻へ**別の向き**から当てた答え、
      **別の面の高さ**で出した答えを再利用し、`design_y` が**呼んだ順で答えを変えた**
      (実測 23 セル・体積 8.18 m³ ぶん、図の側にだけ盛土が生えていた)。
      ⛔ 引数のうち答えを決める物が鍵に入っていなければ、覚え書きは覚え書きではない。
      ⭕ 検図が全 55,660 セルを引き直して、冷えた値と完全一致(null 反転 0・最大差 0.0000 m)。
    ⚠ 旧引数 `edge_dv` は**本文で一度も使っていなかった**ので落とした(死んだ引数を鍵の
      議論に残さない)。
    """
    k = (round(near[0], 1), round(near[1], 1),
         round(nx, 3), round(nz, 3), round(top, 3))
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
                                              (z - near[1]) / (dmin or 1.0), te["y"]):
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
    """§3b 切盛図 — Δ = 設計地盤 − 現況。暖色=盛土 / 寒色=切土 / 無彩=±0.3m。

    戻り値 (svg, {石段の名: [セル数, 盛土セル, 切土セル, 最大盛土, 最大切土, 盛土の和]})。
    ⭐ **坂ごとの切盛を返す**【低4 検図16巡目 → 2026-09-08】── 註が語る数は**この集計から
    算出して刷る**。⛔ caption に直書きしない(規則4)。⛔ 数を合わせるのでなく算出へ替える。
    """
    g = G(d)
    pr = Proj(x0, x1, z0, z1, W=W, pad=0.0, top=26.0, bottom=30.0)
    o = _sv(pr.W, pr.H, "切盛図")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))
    stp = 2
    tally, st = {}, {}
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
            kn = _stair_hit(d, g, cx, cz)[0] if cutfill_name(d, g, cx, cz, y).startswith("石段") else None
            if kn:
                q_ = st.setdefault(kn, [0, 0, 0, 0.0, 0.0, 0.0])
                q_[0] += 1
                if dv > 0: q_[1] += 1; q_[3] = max(q_[3], dv); q_[5] += dv
                else:      q_[2] += 1; q_[4] = max(q_[4], -dv)
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
    _STAIR_CF.clear(); _STAIR_CF.update(st)   # ⛔ 註は同じ集計から刷る(規則4)
    return ("\n".join(o), st)


_STAIR_CF = {}      # 切盛図が数えた坂ごとの切盛(⛔ 設計値ではない。図の副産物)
_STAIR_CF_N = []    # この一文を刷った**場所の名簿**(⛔ 図を組んだあとの検査が数える)
# ⚠ **括弧の中身も従属値**【低1 検図18巡目 → 2026-09-08】── 旧版は数だけを従属値にして
#    「(切盛図の銘・断面イ・断面ホ)」を literal で並べており、破壊試験で「2」と刷りながら
#    三つ並べても誰も気づかなかった。⛔ 名簿は呼ぶ側が名乗り、ここが受ける。

# ⭐ **読みの署名句**【中1 検図18巡目 → 2026-09-08】── 旧版の検査は「留保が付いているか」しか
#    見ておらず、**読みそのものを手書きの文へ差し替えても黙った**(断面ホを差し替えると
#    ⛔0件・exit 0 で通った)。⇒ 留保と**読みの両方**を数え、名簿の丈と突き合わせる。
# ⛔ 数えるのは**この関数だけが出す言い回し**にする ── 「切盛の擁壁で受けた坂」という語そのものは
#    考証の地の文と検査の〔記録〕にも在り(計4箇所)、そちらは銘ではないので数に混ぜない。
_STAIR_CF_SIG = "は切通しではなく、切盛の擁壁で受けた坂である。</b>"

# ⭐ **留保は読みと同じ場所から刷る**【中1 考証15巡目 → 2026-09-08】── 是正した読みは
#   json / 考証 / 切盛図の註では留保付きだったのに、**印刷される断面の銘では無銘・無留保**で
#   現れていた。⭐ **ユーザーが実際に読むのは銘のほう。**⛔ 三枚を個別に直すと四巡目に同じ件が
#   出る(既に三巡連続)ので、**読みと留保を一本の関数から刷る**。
_STAIR_CF_CAVEAT = (
    "⚠ <b>これは安政三年の地盤の復元ではない</b> — 差を測っている相手は<b>今日の地面</b>"
    "(上知のあとの官有地・昭和の再建・ホテルと道路の切り込みを含む)であって、安政三年の"
    "地面ではない。名所図会【S】が支えるのは<b>「石段の両側に笠付きの土留め側壁がある」ことまで</b>"
    "で、<b>切通しか切盛かは支えない</b>【P 実測 — 造成前の地盤の正本 `sanno_dem.json` ／ "
    "U 当方の読み(当図の設計面がその面に対してどう据わるか)】。")


def stair_cutfill_txt(name, st=None, where="(名乗りの無い呼び出し)"):
    """坂ごとの切盛を**文へ組む**【低4 検図16巡目 → 2026-09-08】。

    ⛔ **註に数を直書きしない** — `kirimori_svg` の集計からの従属値で、土量表を変えれば追随する。
    ⛔ 「男坂に切通しは掘らない」と書かない ── 実測は**下端の区間だけが切土**である。
    ⭐ **留保の一文を必ず連れて出る**【中1 考証15巡目 → 2026-09-08】── ⛔ 呼ぶ側で書き足さない。
    ⭐ `where` = **この文が載る場所の名**【低1 検図18巡目】── 〔記録〕の名簿はここから組む。
    """
    _STAIR_CF_N.append(where)
    q = (st if st is not None else _STAIR_CF).get(name)
    if not q or not q[0]:
        return ("<b>%s の切盛は測れていない</b>(切盛図の走査に一セルも載らない)。" % name
                + _STAIR_CF_CAVEAT)
    n, nf, nc, mf, mc, sf = q
    t = ("<b>%s " % name + _STAIR_CF_SIG
         + ("石段は現地形なりに乗り、"
            "盛土が主(平面で <b>%.0f%%</b> ／ 最大 <b>%.2f m</b> ／ 盛土の区間の平均 <b>%.2f m</b>)で、"
            % (100.0 * nf / n, mf, (sf / nf) if nf else 0.0)))
    if nc:
        t += ("下端寄りの <b>%.0f%%</b> の区間だけが切土(最大 <b>%.2f m</b>)になる。" 
              % (100.0 * nc / n, mc))
    else:
        t += "切土になる区間は無い。"
    return (t + "【算出 — 切盛図の 2 m 格子から坂ごとに数える。⛔ この数を註へ直書きしない】"
            + _STAIR_CF_CAVEAT)


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
_SCAT_N = [None]        # 散布図が描いた焼き出しの本数(⛔ 組んだ後の検査が図の中で数え直す)
_SCAT = [("帯(本体)", "#5F7A4E", 0.55),
         ("林縁", "#8AA36B", 0.55),
         ("塊(設計)", "#A8452C", 0.85),
         ("景(視線の塊)", "#C9A24B", 0.9),
         ("一本立ち", "#3E4A55", 0.95),
         ("区・前庭の帯", "#8C7F5E", 0.7)]


def scatter_class(gn):
    """焼いた点の**別**(帯 / 林縁 / 塊 / 景 / 一本立ち / 区・前庭)。⛔ 名簿を別に持たない。"""
    if gn.endswith("(一本立ち)"): return "一本立ち"
    if gn.startswith("視線の塊"): return "景(視線の塊)"
    if gn.endswith(" の林縁"): return "林縁"
    if "／" in gn: return "塊(設計)"
    if gn.startswith("社叢 帯"): return "帯(本体)"
    return "区・前庭の帯"


def scatter_svg(d, g, kan="其X"):
    """**焼き出した木の点をそのまま描く**【低2 検図20巡目 → 2026-09-09】。

    ⚠ **見つかった穴**: 図は面と密度と本数の表しか持たず、**焼いた点の位置を描く図版が
      一面も無かった**(規則19 — 焼いた値が誰の目にも触れずに実装へ渡る)。
    ⛔ **ここで撒き直さない** ── 読むのは `sanno_impl.json` の `planting.points` だけで、
      **実装がそのまま置く点**を描く。図と現物が別の並びになる道を作らない。
    ⛔ 退避の面も重ねる ── 「点が退避に載っていないか」は数(検査)で守るが、**目でも読める**
      ようにしておく(数だけだと、退避そのものが空になった日に気づけない)。
    """
    if not os.path.exists(IMPL_OUT):
        o9 = _sv(900.0, 60.0, "焼き出し無し")
        o9.append(T(10, 34, "⛔ `sanno_impl.json` が無い — `--export-impl` を回すこと",
                    fs=13, fill="var(--shu)"))
        o9.append(ENDSVG)
        return "\n".join(o9)
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    P9 = (im.get("planting") or {}).get("points") or []
    poly = d["polygon"]
    xs = [q[0] for q in poly]; zs = [q[1] for q in poly]
    pr = Proj(min(xs), max(xs), min(zs), max(zs), W=900.0, pad=14.0, top=26.0, bottom=52.0)
    o = _sv(pr.W, pr.H, "焼き出した木の散布")
    o.append(R(0, 0, pr.W, pr.H, fill="var(--paper2)"))
    o.append(PL([(pr.X(x), pr.Y(z)) for x, z in poly], stroke="var(--ink)", sw=1.6,
                fill="var(--pl-slope)", op=0.45, close=True))
    # 平場・石段・勝手道 ── 位置を読むための下敷き(⛔ ここで新しい形を作らない)
    for te in d["terraces"]:
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in terrace_poly(te, g)],
                    fill="var(--pl-main)", stroke="var(--ink)", sw=1.0, op=0.75, close=True))
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        kp = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in kp], stroke="var(--ishi)",
                    sw=max(1.5, pr.L(kaidan_wm(d, k))), op=0.75))
    for seg in d.get("kattemichi", []):
        o.append(PL([(pr.X(x), pr.Y(z)) for x, z in seg["pts"]], stroke="var(--ishi)",
                    sw=max(1.2, pr.L(seg.get("wM") or 2.7)), op=0.55))
    # 退避の面(全 scope を重ねる。⛔ 名簿を手で持たない — `avoid_shapes` の口をそのまま回す)
    scopes = ["keidai", "zentei", "obi4"] + ["obi123:" + lay for lay in _LAYS]
    shp = []
    for sc in scopes: shp += avoid_shapes(d, g, sc)
    shp += cluster_keepout_shapes(d)
    for sh in shp:
        if sh[0] == "rect":
            a = g.W(sh[1], sh[2]); b = g.W(sh[3], sh[4])
            o.append(R(pr.X(min(a[0], b[0])), pr.Y(max(a[1], b[1])),
                       abs(pr.X(b[0]) - pr.X(a[0])), abs(pr.Y(a[1]) - pr.Y(b[1])),
                       fill="var(--shu)", op=0.10))
        elif sh[0] in ("band", "seg"):
            a = g.W(*sh[1]); b = g.W(*sh[2])
            o.append(LN(pr.X(a[0]), pr.Y(a[1]), pr.X(b[0]), pr.Y(b[1]),
                        stroke="var(--shu)", sw=max(1.0, pr.L(sh[3] * 2.0 * d["const"]["ken"])),
                        op=0.10, cap="butt"))
        elif sh[0] == "disc":
            c = g.W(*sh[1])
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="var(--shu)" opacity="0.10"/>'
                     % (pr.X(c[0]), pr.Y(c[1]), max(0.8, pr.L(sh[2] * d["const"]["ken"]))))
        elif sh[0] == "poly":
            W9 = [g.W(*q) for q in sh[1]]
            o.append(PL([(pr.X(x), pr.Y(z)) for x, z in W9], fill="var(--shu)", op=0.12,
                        stroke="var(--shu)", sw=0.6, close=True))
    # 焼いた点 ── **樹冠の実寸**の円で描く(⛔ 一律の点にしない。密度が読めなくなる)
    col = dict((k9, c9) for k9, c9, _op in _SCAT)
    tal = {}
    for q in P9:
        cl = scatter_class(q["group"])
        tal[cl] = tal.get(cl, 0) + 1
        x9, z9 = q["world"]
        r9 = max(0.7, pr.L((q.get("crownM") or 1.0) / 2.0))
        o.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="%s" opacity="%.2f" '
                 'stroke="none"/>' % (pr.X(x9), pr.Y(z9), r9, col.get(cl, "#5F7A4E"),
                                      0.22 if cl in ("帯(本体)", "林縁") else 0.42))
        # ⭐ 幹の点に印を付ける ── 組んだ後の検査が**図の中で数え直す**(規則19)。
        #   ⛔ 「描いたつもり」を許さない — 焼き出しの本数と図の点の数を突き合わせる。
        o.append('<circle class="tp" cx="%.1f" cy="%.1f" r="0.9" fill="%s" opacity="0.95"/>'
                 % (pr.X(x9), pr.Y(z9), col.get(cl, "#5F7A4E")))
    _SCAT_N[0] = len(P9)
    o.append(T(6, 15, kan + "　焼き出した木の散布 ─ `sanno_impl.json` の点をそのまま描く",
               fs=12.5, fill="var(--dim)"))
    o.append(T(pr.W - 6, 15, "円 = 樹冠の実寸 ／ 芯の点 = 幹 ／ 淡赤 = 退避の面",
               fs=11, anchor="end", fill="var(--dim)"))
    y9 = pr.H - 34
    x9 = 8.0
    for nm9, c9, _op in _SCAT:
        o.append('<circle cx="%.1f" cy="%.1f" r="4.0" fill="%s" opacity="0.85"/>' % (x9 + 5, y9, c9))
        lab = "%s %d" % (nm9, tal.get(nm9, 0))
        o.append(T(x9 + 13, y9 + 4, lab, fs=10.5, fill="var(--ink)"))
        x9 += 15 + txt_w(lab, 10.5) + 14
    o.append(T(8, pr.H - 12, "計 %d 本 ── ⛔ この図は撒き直していない(焼き出しを読むだけ)。"
               "点が淡赤の面に載っていれば⛔で、検査『退避の表 keepoutFrom …』が数で止める"
               % len(P9), fs=10.5, fill="var(--dim)"))
    o.append(ENDSVG)
    return "\n".join(o)


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


# ⭐ 石垣の勾配(垂直1に対する水平)は **`const.batterIshi` が正典**【低3 検図20巡目 → 2026-09-09】。
#   ⛔ module 定数に写さない ── 旧図は module 定数を持ち、json の `batterIshi` 0.2 を生成器が
#   一度も読まなかった(同じ数の正典が二つ・規則4)。土の法面 batterFill/Cut とは別物。
def batter_ishi(d): return d["const"]["batterIshi"]


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

    返り: [(縁, 外向き符号, 天端, 露出, 法尻, 切/盛)]。法尻は勾配 `const.batterIshi` の面と
    現地形の交点(二分法)で、其二十の展開図と同じ式。
    """
    bi = batter_ishi(d)
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
            h = nat(e + sgn * bi * t)
            if (yy + t > h) if up else (yy - t < h): hi = t
            else: lo = t
        cand.append((e, sgn, yy, t, e + sgn * bi * t, "切" if up else "盛"))
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
            # ⭐ **樹冠は傾いた芯で切る**【低1 庭方 2026-09-08 十二巡目】── 平面は傾いた芯で円を
            #    描くのに、断面が直立の三角形では**同じ木が二通りの姿で図に出る**。
            cu, cv = single_crown_center(d, sg)
            wx, wz = g.W(cu, cv)
            tx, tz = g.W(sg["uv"][0], sg["uv"][1])
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
                        "%s(枝下 %s%.1f m)" % (sg["name"], "" if decl else "≧ ", eda or 0.0),
                        (tx if ax == "EW" else tz), (sg.get("layer") or "")))
    return out


def forest_tier_series(d, g, key):
    """社叢の**層の稜線**(松・中木・低木)を断面の線に沿って起こす。

    ⭐ **2026-09-08 に起こした。**32 面の断面のうち「中木」を含む面は **0 面**、「低木」は前庭の
    3 面だけで、**社叢の垂直構造を描く図が一面も無かった** ── 庭方が『帯4 の下層(町から山を見る
    前面)が景として成立しているか』を判定できないと明言した(見ずに成立とは言わない)。
    ⛔ **個体を描かない — 層の帯として描く。**撒き木は密度で決まる物なので、断面に一本ずつ
    立てるのは誤り。稜線は**帯の `matsuH`/`chubokuH`/`teibokuH` の下端〜上端**を地盤へ積んだ
    **帯**で、⛔ 中央値の一本線にしない(宣言と図が食い違い、林冠が定規で引いたように読める)。
    ⛔ 数を持たない(帯の宣言と現地形からの従属値)。描くのは `sections[].forestTiers` を
    宣言した面だけ(⛔ 生成器に面の名を焼き込まない)。
    ⭐ **2026-09-08 に帯4 を引けるようにした**【A-1 庭方11巡目】── `band_scan` は帯4 のセルを
    **一つも作らない**(`exclude` が落とす)ので、旧式は**帯4 の上で必ず `None` を返し、層が
    一つも描かれなかった** ── それが「町から山を見る前面」を判定できない、と庭方が言った当の物。
    ⛔ 「閉じた」と名乗ったまま描けていない状態を残さない(規則19)。
    ⭐ **稜線は地形の平行移動ではない**【低2 検図15巡目】── 下側の木が稜へ向かって伸びるので
    林冠は斜面より**平ら**で、凹まない。実装は**上側の凸包**(⛔ 丸みの量を数で持たない)。
    ⭐ **帯ごとの覆う長さを返す**【中3 検図16巡目 → 2026-09-08】── 旧式は「1標本掠めただけの帯」
    も跨いだ帯に数えていたが、稜線は 2 標本以上でしか起きないので、**図に一本も描かれない帯が
    『描いた』側に載っていた**。⇒ 数えるのは**実際に描かれた長さ**だけ。
    ⭐ **層集合は `planting.bandDef.avoid.layers` から採る**【中1 庭方13巡目 → 2026-09-08】──
    生成器に `松/中木/低木` を焼き込んでいたので、**帯表が宣言する落葉(抜け木)が図に一本も
    出ていなかった**(検査が名乗る集合より測る集合が狭い・規則19)。
    戻り値 [(層の名, 丈の刷り, [[(c, h, ylo, yhi), …], …], {帯: 覆う長さ m}, 描き方)]。
    """
    if not any(q["profile"] == key and q.get("forestTiers") for q in d.get("sections", [])):
        return []
    prof = _profile(d, key)
    pos = prof_pos(d, key)
    c0, c1 = prof[0][0], prof[-1][0]
    cells, _sk = band_scan(d, g)
    step = d["planting"]["bandDef"]["stepKen"]
    own = {}
    for k, ps in cells.items():
        for u, v in ps: own[(int(round(u / step)), int(round(v / step)))] = k
    for k, ps in (_BANDS.get("kaic") or {}).items():
        for u, v in ps: own.setdefault((int(round(u / step)), int(round(v / step))), k)

    # ⭐ **帯4(多角形を持つ帯)は多角形そのもので引く**(2026-09-08 A-1)── `band_scan` の
    #    セルには帯4 が一つも無いので、走査の格子では永久に引けない。
    poly4 = [(b4["band"], [(q[0], q[1]) for q in b4["uv"]])
             for b4 in d["slopeBands"] if b4.get("uv")]

    def band_of(c):
        x, z = pos(c)
        u, v = g.U(x), g.V(z)
        for bn, P4 in poly4:
            if in_poly((u, v), P4): return bn
        ku, kv = int(round(u / step)), int(round(v / step))
        for du in (0, 1, -1):
            for dv in (0, 1, -1):
                q = own.get((ku + du, kv + dv))
                if q: return q
        return None

    out = []
    for lay, lab_lay, hk in forest_layers(d):
        segs, cur, curb, blen = [], [], [], {}
        dlo = dhi = mlo = mhi = None
        elo = ehi = None                       # 頭打ちのあとの**実際に立つ**丈

        def flush(cur, curb):
            """⛔ **描かれた区間だけを数える** — 稜線は 2 標本以上でしか起きない(中3 検図16巡目)。"""
            if len(cur) < 2: return
            segs.append(_crown_convex(cur))
            for i in range(len(cur) - 1):
                blen[curb[i]] = blen.get(curb[i], 0.0) + (cur[i + 1][0] - cur[i][0])

        n = max(2, int((c1 - c0) / 1.0))
        for i in range(n + 1):
            c = c0 + (c1 - c0) * i / float(n)
            b = band_of(c)
            x, z = pos(c)
            h = dem_h(x, z)
            hh = None
            if b is not None:
                hh = ([q for q in d["slopeBands"] if q["band"] == b] or [{}])[0].get(hk)
            if hh and h is not None:
                # ⭐ **描くのは『実際に立つ丈』**【中1 庭方13巡目 → 2026-09-08】── 帯の宣言の
                #    上端をそのまま積むと、頭打ち(`sizeRule.speciesHCap`)で届かない樹種の分だけ
                #    図が高く出る。⛔ 逆に頭打ちを無視して低く刷ると**棟梁が稜線を低く建てる**。
                eh = layer_stand_hi(d, lay, hh)
                m = (hh[0] + eh) / 2.0
                dlo = hh[0] if dlo is None else min(dlo, hh[0])
                dhi = hh[1] if dhi is None else max(dhi, hh[1])
                elo = hh[0] if elo is None else min(elo, hh[0])
                ehi = eh if ehi is None else max(ehi, eh)
                mlo = m if mlo is None else min(mlo, m)
                mhi = m if mhi is None else max(mhi, m)
                cur.append((c, h, h + hh[0], h + eh)); curb.append(b)
            else:
                flush(cur, curb); cur, curb = [], []
        flush(cur, curb)
        if segs:
            # ⭐ **抜け木の銘は「天端」と名乗る**【低2 庭方14巡目 → 2026-09-08】── 破線は
            #    `layer_stand_hi`(= **実際に立つ**上端)に引かれているのに、旧版の銘は「宣言」
            #    としか名乗らず、⛔ 両者が一致する間は「→ 実際」節が抑止されて**どちらに線が
            #    引かれているかが図から読めなかった**。⛔ 数は動かさない(先頭語だけ)。
            lab = ("%s %s m" % ("天端(破線)" if lab_lay == "抜け木" else "宣言",
                                ("%.1f" % dlo) if abs(dhi - dlo) < 0.05
                                else "%.1f〜%.1f" % (dlo, dhi)))
            if abs(ehi - dhi) > 0.005:
                lab += ("→ 実際 %.1f〜%.2f m" % (elo, ehi))
            lab += ("(中央 %s)" % (("%.1f" % mlo) if abs(mhi - mlo) < 0.05
                                    else "%.1f〜%.1f" % (mlo, mhi)))
            if lab_lay == "抜け木":
                lab += forest_nukigi_note(d, blen)
            out.append((lay, lab, segs, blen, lab_lay))
    return out


# 層の描き方 ── 「帯」= 下端〜上端を塗る ／ 「抜け木」= 天端の破線一本だけ。
# ⭐ **落葉は帯にしない**【中1 庭方 2026-09-08 十三巡目】── 帯4 で 1.5 割、密度ではなく
#   **林冠の上に散る抜け木**なので、帯で塗ると「落葉が層をなして詰まっている」と読めてしまう。
#   ⛔ しかし描かないのはもっと悪い ── 帯表が宣言する上端は松より高く、**社叢が生垣でなく
#   社叢に見えるのは林冠の上に抜け木が散るから**である。⇒ 天端の破線一本 + 銘。
_FOREST_STYLE = {"松": "帯", "落葉": "抜け木", "中木": "帯", "低木": "帯"}
_FOREST_LABEL = {"松": "松(上木)"}


def forest_layers(d):
    """断面へ立てる層 [(刷る名, 描き方, 丈の鍵)] ── **`bandDef` の層集合をそのまま採る**。

    ⭐ **2026-09-08(中1 庭方13巡目)**── 旧式は `松/中木/低木` を生成器に**焼き込んで**おり、
    `planting.bandDef.avoid.layers` が宣言する四層(松・落葉・中木・低木)と食い違っていた。
    **検査が名乗る集合より測る集合が狭い**形(規則19)で、⛔ 帯表が宣言する落葉は
    断面ル・トの SVG に一本も出ていなかった。⛔ 層の名を生成器で決めない。
    """
    HK = {"松": "matsuH", "落葉": "rakuyoH", "中木": "chubokuH", "低木": "teibokuH"}
    lays = ((d["planting"]["bandDef"].get("avoid") or {}).get("layers")
            or list(HK.keys()))
    return [(_FOREST_LABEL.get(q, q), _FOREST_STYLE.get(q, "帯"), HK[q])
            for q in lays if q in HK]


def _lay_key(lay):
    """断面の刷り名 → `planting.parts` の層の鍵(⛔ 逆引きを二箇所に書かない)。"""
    for k, v in _FOREST_LABEL.items():
        if v == lay: return k
    return lay


def layer_stand_hi(d, lay, hh):
    """その層が**実際に立てる**上端[m]= max(樹種ごとの頭打ち ∧ 帯の宣言の上端)。

    ⛔ 数を持たない ── 目録の素の丈 × 箍(`sizeRule.speciesHCap`)と帯の宣言からの従属値。
    ⚠ palette の丈が一つも解けなければ**宣言のまま**(⛔ 黙って縮めない)。
    """
    caps = [species_h_cap(d, pt) for pt in d["planting"]["parts"].get(_lay_key(lay), [])]
    caps = [q for q in caps if q is not None]
    if not caps: return hh[1]
    return max(hh[0], min(hh[1], max(caps)))


def forest_nukigi_note(d, blen):
    """抜け木の銘に添える**割合と本数**(帯ごと)。⛔ 数を持たない(帯の宣言と有効面の従属値)。

    ⚠ 本数は `band_stats` の走査の産物なので、**図より先に走らせる**(走っていないと銘から
    本数だけが黙って落ちる ── ⛔ 0 件ではなく『測っていない』の形)。
    """
    band_stats(d, G(d))
    o = []
    for bn in sorted(blen):
        b = ([q for q in d["slopeBands"] if q["band"] == bn] or [None])[0]
        if not b or not b.get("rakuyoRatio"): continue
        n = _band_layer_n(b, "落葉")
        o.append("帯%d は %.1f 割%s" % (bn, b["rakuyoRatio"] * 10,
                                       ("・%d 本" % int(round(n))) if n else ""))
    return ("(%s)" % " ／ ".join(o)) if o else ""


def _hull_y(sg, k):
    """`sg` の第 k 成分を**上側の凸包**へ均した列を返す(要素数はそのまま)。"""
    hull = []
    for q in sg:
        c, y = q[0], q[k]
        while len(hull) >= 2:
            (c0, y0), (c1, y1) = hull[-2], hull[-1]
            if (y1 - y0) * (c - c0) >= (y - y0) * (c1 - c0): break   # 上に凸でなければ捨てる
            hull.pop()
        hull.append((c, y))
    out, j = [], 0
    for q in sg:
        c = q[0]
        while j + 1 < len(hull) - 1 and hull[j + 1][0] < c - 1e-9: j += 1
        (ca, ya), (cb, yb) = hull[j], hull[min(j + 1, len(hull) - 1)]
        t = 0.0 if abs(cb - ca) < 1e-9 else (c - ca) / (cb - ca)
        out.append(ya + (yb - ya) * t)
    return out


def _crown_convex(sg):
    """林冠を**上側の凸包**へ均す【低2 検図15巡目 → 2026-09-08】。

    ⛔ 地形の平行移動のままにしない ── 下側の木が稜へ向かって伸びるので、実際の林冠は斜面より
    **平ら**で、地形の窪みでも凹まない。⛔ **丸みの量を数で持たない**(凸包は形が決める)。
    地盤 `h` はそのまま(帯の下端は地面である)。
    ⭐ **稜線は一本ではなく帯である**【中1 庭方 2026-09-08 十二巡目】── 帯が宣言するのは丈の
    **範囲**なので、中央値の一本線で描くと**宣言と図が食い違い**、しかも林冠が定規で引いたように
    読める(『地質断面』に見える原因)。⇒ 下端(`ylo`)と上端(`yhi`)の**両方**を均して帯で塗る。
    入出力とも [(c, 地盤, ylo, yhi), …]。
    """
    a = _hull_y(sg, 2); b = _hull_y(sg, 3)
    return [(q[0], q[1], a[i], b[i]) for i, q in enumerate(sg)]


def forest_tier_wiring_check(d):
    """**丈を宣言した帯 × 層に、その層を描く断面があるか**【A-3 庭方11巡目・規則19】。

    ⛔ ① 丈を宣言している(帯, 層)の組を描く断面が**一面も無い**
    ⛔ ② `sections[].forestTiers` を立てながら**一本も稜線が起きない**面がある(死んだ宣言)

    ⭐ **落葉も検める**【中1 庭方13巡目 → 2026-09-08】── 旧註は「落葉高木は層の帯を持たない
    ので上木(松)が林冠を代表する」としていたが、**それは誤り**である。帯が宣言する落葉の上端は
    松より高く(抜け木)、⛔ 図の稜線の天端が実際に立つ最高木より低く刷られていた。
    ⇒ **層集合は `bandDef` の四層**、落葉は**天端の破線一本**として描く(帯では塗らない)。
    ⚠ **破壊試験**: 全 `sections[].forestTiers` を落とすと①が全組で鳴る(2026-09-08 に実測)。
    旧図はここが**⛔ 0 件**で黙っており、「帯が丈を宣言しているのに描く断面が一面も無い」
    という状態を誰も見ていなかった。
    """
    g = G(d)
    # ⭐ **層集合は `bandDef` から採る**【中1 庭方13巡目 → 2026-09-08】── 焼き込んだ三層では
    #    **題目(帯 × 層)より測る集合が狭く**、帯が宣言する落葉が一度も検められていなかった。
    LAY = [(nm, hk) for nm, _sty, hk in forest_layers(d)]
    got, drawn = {}, {}
    for s in d.get("sections", []):
        if not s.get("forestTiers"): continue
        t = forest_tier_series(d, g, s["profile"])
        drawn[s["kana"]] = t
        for lay, _lab, segs, blen in [(q[0], q[1], q[2], q[3]) for q in t]:
            # ⛔ **1標本掠めただけの帯を「描いた」に数えない**【中3 検図16巡目 → 2026-09-08】
            for bn, L in blen.items():
                if L > 1e-9: got.setdefault((bn, lay), []).append((s["kana"], L))
    bad, note = [], []
    for b in d["slopeBands"]:
        for lay, hk in LAY:
            if not b.get(hk): continue
            k = (b["band"], lay)
            if k in got:
                note.append("社叢 帯%d の『%s』── %s【算出 — ⛔ **覆う長さ 0 の帯は数えない**"
                            "(1標本掠めただけでは稜線が一本も描かれない)】"
                            % (b["band"], lay,
                               " ／ ".join("断面%s ── 覆う長さ %.1f m" % (q, L) for q, L in got[k])))
            else:
                bad.append("社叢 帯%d は『%s』の丈を宣言しているのに、**その層を描く断面が一面も"
                           "無い** — 宣言だけあって図に出ない値は『未検査』であって合格ではない"
                           "(A-3 庭方 2026-09-08・規則19)" % (b["band"], lay))
    for kana, t in sorted(drawn.items()):
        if not t:
            bad.append("断面%s は `forestTiers` を立てているのに稜線が一本も起きない — "
                       "死んだ宣言(切断線が帯を跨いでいないか、帯が丈を宣言していない)" % kana)
        else:
            note.append("断面%s の層 ── %s【算出 — 覆う長さは**帯ごと**に出す(⛔ 面の合計だけを"
                        "刷ると、どの帯が閉じているかが図から読めない)】"
                        % (kana, " ／ ".join(
                            "%s %s(%s)" % (q[0], q[1],
                                           "・".join("帯%d 覆う長さ %.1f m" % (bn, L)
                                                     for bn, L in sorted(q[3].items())))
                            for q in t)))
    return bad, note


# 断面の層の銘 ── 段の高さ[px]と、抜け木の銘だけを持ち上げる量[px]。
# ⛔ **設計値ではない**(図の逃がし)ので json に置かない【低3 庭方14巡目 → 2026-09-08】。
LBL_H = 12.0
NUKI_DY = 24.0


def forest_tier_layer(tiers, X, Y):
    """層の稜線を断面へ描く ── 地盤から順に **低木 → 中木 → 松** を重ねる(⛔ 個体は描かない)。

    ⭐ **落葉だけは帯にせず天端の破線一本で描く**【中1 庭方 2026-09-08 十三巡目】── 1.5 割の
    **抜け木**なので帯で塗ると層をなして詰まって読める。⛔ 描かないのはもっと悪い(社叢が
    生垣に見える。棟梁が稜線を低く建てる)。
    """
    o, lbl = [], []
    OP = {"松(上木)": 0.14, "中木": 0.20, "低木": 0.30}
    for q in reversed(tiers):                     # 松を先に敷き、下層を上へ重ねる
        lay, lab, segs, _bd = q[0], q[1], q[2], q[3]
        sty = q[4] if len(q) > 4 else "帯"
        for sg in segs:
            lo_ = [(X(c), Y(a)) for c, _h, a, _b in sg]
            hi_ = [(X(c), Y(b)) for c, _h, _a, b in sg]
            base = [(X(c), Y(h)) for c, h, _a, _b in reversed(sg)]
            if sty == "抜け木":
                # ⛔ 塗らない・胴を引かない ── 林冠の上に**散る**ものなので面にしない。
                o.append(PL(hi_, stroke="var(--take)", sw=1.4, dash="9 5", op=0.9))
                continue
            # 地盤 → 宣言の下端(林の胴)
            o.append(PL(lo_ + base, close=True, fill="var(--take)", op=OP.get(lay, 0.2),
                        stroke="none"))
            # ⭐ **宣言の下端〜上端を帯で塗る**【中1 庭方 2026-09-08】── 林冠は一本の線ではない
            o.append(PL(hi_ + list(reversed(lo_)), close=True, fill="var(--take)",
                        op=OP.get(lay, 0.2) * 1.6, stroke="none"))
            dsh = None if lay.startswith("松") else "5 3"
            o.append(PL(hi_, stroke="var(--take)", sw=1.2, dash=dsh, op=0.85))
            o.append(PL(lo_, stroke="var(--take)", sw=0.9, dash="3 3", op=0.65))
        c_, _h_, _a_, b_ = segs[-1][-1]
        lbl.append([Y(b_) - 3 - (NUKI_DY if sty == "抜け木" else 0.0), X(c_) - 4,
                    "%s %s" % (("抜け木(%s)" % lay) if sty == "抜け木" else lay, lab)])
    # ⭐ **層の銘を一段ずつずらす**【低3 庭方14巡目 → 2026-09-08】── 旧版は銘をそれぞれの
    #    稜線の右端へ置くだけで、丈の近い層どうし(断面ト の抜け木と松)が重なっていた。
    #    ⛔ 逃がしを一つずつ手で持たない ── 上から順に **`LBL_H` 以上の間隔**へ押し広げる。
    lbl.sort(key=lambda q: q[0])
    for i in range(1, len(lbl)):
        if lbl[i][0] - lbl[i - 1][0] < LBL_H: lbl[i][0] = lbl[i - 1][0] + LBL_H
    for y_, x_, t_ in lbl:
        o.append(T(x_, y_, t_, fs=9.5, anchor="end", fill="var(--take)"))
    return o


# 落葉高木の**壺形(傘形)**の見えがかり ── (枝下から梢までの割合, 半幅の割合)。
# ⛔ 円錐(針葉樹形)で描かない【低2 庭方 2026-09-08 十二巡目】── 欅・椋・榎は下で細く、
# 上半でいちばん広がり、梢は丸い。⛔ 数は姿の記号であって設計値ではない。
RAKUYO_GLYPH = [(0.00, 0.18), (0.15, 0.48), (0.30, 0.72), (0.45, 0.88),
                (0.60, 0.97), (0.72, 1.00), (0.84, 0.94), (0.93, 0.72), (1.00, 0.0)]


def tree_section_layer(items, X, Y):
    """`tree_section_items` の一本立ちを断面へ描く(幹・枝下の線・樹冠の見えがかり)。

    ⭐ **傾けた木は傾けて描く**【低1 庭方 2026-09-08】── 幹は足元から樹冠の芯へ倒し、樹冠は
    傾いた芯の上に載せる。⛔ 平面と断面で同じ木を別の姿に描かない。
    ⭐ **層で字形を変える**【低2 同】── 松(針葉)は円錐、落葉高木は壺形(傘形)。
    """
    o = []
    for c, half, eda, hh, top, nm, tc, lay in items:
        o.append(LN(X(tc), Y(top), X(c), Y(top + hh), stroke="var(--niwa)", sw=1.6))
        if lay == "落葉":
            L = [(X(c - half * w), Y(top + eda + (hh - eda) * t)) for t, w in RAKUYO_GLYPH]
            R = [(X(c + half * w), Y(top + eda + (hh - eda) * t)) for t, w in reversed(RAKUYO_GLYPH)]
            o.append(PL(L + R, stroke="var(--niwa)", sw=1.2, fill="var(--niwa)", op=0.28,
                        close=True))
        else:
            o.append(PL([(X(c - half), Y(top + eda)), (X(c), Y(top + hh)),
                         (X(c + half), Y(top + eda))],
                        stroke="var(--niwa)", sw=1.2, fill="var(--niwa)", op=0.28, close=True))
        o.append(LN(X(c - half), Y(top + eda), X(c + half), Y(top + eda),
                    stroke="var(--niwa)", sw=1.0, dash="4 3"))
        o.append(T(X(c), Y(top + hh) - 5, nm, fs=9.5, anchor="middle", fill="var(--niwa)"))
    return o


_SITE_EDGE_N = []       # 断面に立てた「社地の◯境」の銘(⛔ 組んだ後の検査が図の中で数え直す)


def section_site_edges(d, key, prof):
    """断面の切断線が**社地の境**を横切る点 [(座標, 銘, 辺の番号), …]。窓の中に入る点だけ。

    ⭐ **2026-09-08 中1 検図18巡目で起こした。**『窓は社地の境を跨ぐ』という不変条件を新設して
    三面の窓を動かしたのに、**図の上に「境がどこか」を示す銘が無かった** ── 読む人は跨いだか
    どうかを目で確かめられない(規則19 第3型 — 測ったのに図に出ていない)。
    ⛔ **銘の位置を手で持たない** ── `section_window_check` が跨ぎ量を測るのと**同じ**
    `_site_cross` の交点をそのまま使う(⛔ 図と検査で別々に境を持たない)。
    ⚠ 軸平行でない断面(ハ・チ・カ)は `_site_cross` の対象外なので銘も立たない ── その線引きは
    検査の総括が毎回名指しする。
    """
    p = d["profiles"][key]
    if p.get("axis") not in ("EW", "NS"): return []
    cr = _site_cross(d, p["axis"], p["at"])
    if not cr: return []
    lo, hi = min(prof[0][0], prof[-1][0]), max(prof[0][0], prof[-1][0])
    ns = ("西", "東") if p["axis"] == "EW" else ("南", "北")
    out = []
    for i, (c, ei) in enumerate(cr):
        if not (lo - 1e-6 <= c <= hi + 1e-6): continue
        nm = ns[0] if i == 0 else (ns[1] if i == len(cr) - 1 else "")
        out.append((c, "社地の%s境" % nm if nm else "社地の境", ei))
    return out


def section_svg(d, key, design, marks, title, flip=False, viewtxt="", flats=(), stairs=()):
    """design = [(coord, y), ...] 設計地盤 / marks = [(coord0, coord1, y, ラベル, 種別)]"""
    g = G(d)
    prof = _profile(d, key)
    walls = wall_steps(d, g, key, prof, design)
    c0, c1 = prof[0][0], prof[-1][0]
    trees = tree_section_items(d, g, key, c0, c1)
    tiers = forest_tier_series(d, g, key)
    ys = ([h for _, h in prof] + [y for _, y in design]
          + [t[4] + t[3] for t in trees]                   # 梢(top + 丈)
          + [y for _t in tiers for sg in _t[2] for _c, _h, _a, y in sg])
                                                   # ⭐ 木の梢まで窓へ入れる(⛔ 切らない)
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
        xl = X(e + sgn * (batter_ishi(d) * t + WALL_T + 1.2))
        anc = "start" if (sgn > 0) != flip else "end"
        if xl > W - 150: xl, anc = X(e) - 6, "end"     # 図の端で切れないよう内側へ返す
        if xl < 150: xl, anc = X(e) + 6, "start"
        o.append(T(xl, Y(ym) + 4, "土留 露出 %.2f m" % t, fs=10, fill="var(--ishi)", anchor=anc))
    # 高さの罫(塗りの上に載せる)
    for y in range(int(math.ceil(y0 / 5.0) * 5), int(y1) + 1, 5):
        o.append(LN(0, Y(y), W, Y(y), stroke="var(--grid)", sw=0.5, op=0.55))
        o.append(T(3, Y(y) - 2, "%d m" % y, fs=9.5, fill="var(--dim)"))
    # ⭐ **社地の境を図の上に立てる**【中1 検図18巡目 → 2026-09-08】── 窓が境を跨いだか
    #    どうかを、読む人が図の上で確かめられるようにする。⛔ 位置は `section_site_edges`
    #    (= 検査と同じ `_site_cross`)からの従属値で、⛔ 手で持たない。
    for _c, _lab, _ei in section_site_edges(d, key, prof):
        _x = X(_c)
        o.append(LN(_x, top, _x, top + Hh, stroke="var(--shu)", sw=0.9, dash="4 3", op=0.85))
        # ⚠ 銘は**上の罫から一段下げる** ── 図の右上には「矢視 …」が右寄せで入るので、
        #    top+12 に置くと東(北)の境の銘とぶつかる(`label_overlap_check` で実測)。
        _an = "end" if _x > W - 78.0 else "start"
        o.append(T(_x + (-4.0 if _an == "end" else 4.0), top + 24, _lab, fs=10,
                   fill="var(--shu)", anchor=_an))
        _SITE_EDGE_N.append("%s の%s" % (title.split("　")[-1], _lab))
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
        # ⭐ **銘を図の窓の外へ出さない**【低1 庭方14巡目 → 2026-09-08】── 窓の縁に寄った物
        #    (参道の帯・境の外の地形)は中央寄せだと右へはみ出て、⛔ **註の答そのものが
        #    クリップされて読めなくなる**。⛔ 逃がしは数で持たず、見積り幅から機械で返す。
        _fs = fit(lab, xb - xa, 10.5)
        _xm, _anc, _w = (xa + xb) / 2.0, "middle", txt_w(lab, _fs)
        if _xm - _w / 2.0 < 2.0: _xm, _anc = 2.0, "start"
        elif _xm + _w / 2.0 > W - 2.0: _xm, _anc = W - 2.0, "end"
        o.append(T(_xm, Y(yb) - hpx - 4, lab, fs=_fs, anchor=_anc))
    # ⭐ **井戸屋形を切る断面**は盛土層と井筒を描き足す(2026-09-06c 裁定1(b)・庭方)
    o.extend(ido_section_layer(d, g, key, X, Y, y0))
    # ⭐ **一本立ちを切る断面**は幹と枝下を描く(2026-09-06c 参考2 — 断面レが『木陰が縁台に
    #    落ちているか』を読ませるには、樹冠の下端(枝下)と座面が同じ一本に出ていなければならない)
    o.extend(forest_tier_layer(tiers, X, Y))
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
    # ⭐ **木階は描かない**【B-8 検図22巡目 → 2026-09-09 十九巡目】── ⛔ 名指しで外さない。
    #    この図が測るのは『参道の坂の段割り(踊り場・脚・曲率)』で、屋根の下の内法の段は
    #    その物差しの対象ではない。⛔ 外した旨は検査『石段の閉合』が毎回刷る(規則19)。
    ks = [k for k in d["kaidans"] if not k.get("kizahashi")]
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
    H = 92.0 + len(rows) * 46.0
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
    o.append(T(6, H - 42, "⛔ 発注量は棒の長さ(開口を抜いた実長)。「節点間」は開口を含む総和で、"
               "透塀の史料拘束だけがこちらで読む値", fs=10.5, fill="var(--dim)"))
    o.append(T(W - 6, H - 26, "透塀の史料値 147.28 m(486.01尺)との差 %.3f m(節点間で比べる)"
               % abs(tot * ken - 147.28), fs=10.5, anchor="end", fill="var(--dim)"))
    # ⭐ **腰高の柵(玉垣と同じ部材)の発注量**【裁き1 庭方 2026-09-07】── 玉垣・境内の外周・
    #    法尻の2本は同じ部材で、新造(edo-buzai)は一度で足りる。⛔ `bom` にベタ書きしない。
    ordr = saku_order_rows(d)
    if ordr:
        o.append(T(6, H - 10, "腰高の柵(玉垣と同じ部材)の発注量 計 %.2f m ＝ %s ── ⛔ 数は `bom` に"
                   "持たず、この図が算出する(新造は一度で足りる)"
                   % (sum(q[1] for q in ordr), " ＋ ".join("%s %.2f" % q for q in ordr)),
                   fs=10.5, fill="var(--shu)"))
    o.append(ENDSVG)
    return "\n".join(o)


def wall_ground(d, g, px, pz, nx, nz):
    """土留めの一点の**両側の地盤**(造成後)。返り (低い側, 高い側, 犬走り or None)。

    ⭐ **物差しは二つの量**【裁定 2026-09-09 普請奉行 = 検図21巡目 A案】── 旧図の `face_toe`
      は**符号を持つ一つの量**(天端 − 外の地盤)で、三つの穴があった:
      ① 基準面が同じ壁の中ですり替わる(平場の内は造成後 `terraces[].y`・外は造成前 `dem_h`)
      ② 切土を受ける壁で 0 を返し、⛔ **未測定と区別が付かない**
      ③ 外向きを固定するので、女坂の頭のように途中で切盛が入れ替わる壁で符号が反転する
    ⭕ **基準面は造成後 `design_y` 一本**(造成しない所は現地形 `dem_h` — これが『造成後の
      地盤』の定義そのものである)。**両側を採り、どちらが外かで場合分けしない**。
      ・**見付高** `faceH` = 天端 − min(両側) …… 壁が見せる面
      ・**受け高** `backH` = max(両側) − 天端 …… 壁が背に負う土
    ⛔ **判定は焼かない** ── 判定則(擁壁として正常/埋まっている壁/段差が無い)は検査が持つ。
      ⛔ 「埋まっている壁」を地形を削って直さない(天端が自然地盤より下 ── スキル
      `unity-modular-stonewall` terrain-grading。始末は `_pending`「埋まっている土留めの始末」)。
    ⚠ 採る距離は `const.wallProbeM`(⛔ 設計値ではなく物差しの刻み)。
    """
    pr = d["const"]["wallProbeM"]
    ys, ben = [], None
    for sg in (1.0, -1.0):
        qx, qz = px + nx * pr * sg, pz + nz * pr * sg
        y = design_y(d, g, qx, qz)
        if y is None: y = dem_h(qx, qz)
        if y is None: y = plane_y(d, d["planes"][0])
        ys.append(y)
    # 犬走り ── **外向き**の側が平場の中なら、その面の高さ(展開図が細点線で重ねる)
    qo = (px + nx * pr, pz + nz * pr)
    for te in d["terraces"]:
        if in_poly(qo, terrace_poly(te, g)): ben = te["y"]
    return min(ys), max(ys), ben


# ================================================================ 土留めの縦断(中4 検図20巡目)
# ⭐ **なぜ焼くか**【中4 検図20巡目 → 2026-09-09】。旧図は土留め13本に**天端の y も露出高も
#   法尻も一つも焼いていなかった**。とりわけ `coping:"stair"` の4本(男坂・女坂の側壁)は
#   ⛔ 天端が数値ですらなく("stair" という語)、実装は「壁の走り → 石段の割付の y」の対応を
#   自力で作るしかなかった。それは⛔ この巡が避けようとした型そのもの(切盛図と断面が男坂で
#   1.34 m 食い違い、段割りを `stair_spans` 一つへ寄せて直した)の再発である。
# ⛔ **石段の側壁の天端は `stair_spans` から引く** — 別々に計算して正典を二つにしない。


def wall_nodes(d, w):
    """土留めの節点(uv)。⛔ `pts` と `a`/`b` の二通りをここ一箇所で吸う。"""
    return [tuple(q) for q in (w.get("pts") or [w["a"], w["b"]])]


def wall_stair(d, w):
    """`coping:"stair"` の土留めが**天端を引く石段**。⛔ 石段の名を数のように持たない ──
    指し先は `copingFrom.kaidan`、無ければ通りの従属元 `vFrom.kaidan`(男坂の側壁)。
    """
    if w.get("coping") != "stair": return None
    nm = ((w.get("copingFrom") or {}).get("kaidan")
          or (w.get("vFrom") or {}).get("kaidan"))
    if not nm: return None
    return ([k for k in d["kaidans"] if k["name"] == nm] or [None])[0]


def stair_first_is_top(d, g, k):
    """石段の第一点が**山上**か。⛔ 向きを手で決めない — 現地形が決める。

    ⚠ `_stair_hit` と**同じ判定**をここ一箇所に置く(2026-08-23 検図 — 男坂だけ上下逆だった)。
    """
    pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
    h0 = dem_h(pts[0][0], pts[0][1]); h1 = dem_h(pts[-1][0], pts[-1][1])
    return h0 is not None and h1 is not None and h0 > h1


def stair_sfrac(d, g, k, x, z):
    """点を石段の折れ線へ落とし、**坂下 0 → 頭 1** の走りの割合を返す(最も近い投影)。"""
    pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
    tot = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
              for i in range(len(pts) - 1)) or 1.0
    acc, best = 0.0, None
    for i in range(len(pts) - 1):
        ax, az = pts[i]; bx, bz = pts[i + 1]
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz) or 1.0
        t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (L * L)))
        dd = math.hypot(x - (ax + dx * t), z - (az + dz * t))
        if best is None or dd < best[0]: best = (dd, (acc + L * t) / tot)
        acc += L
    sf = best[1]
    return (1.0 - sf) if stair_first_is_top(d, g, k) else sf


_WCOMP = [None]


def wall_components(d):
    """土留めを**節点を共有する連なり**へ分ける。⛔ 群の名を json に書かない。

    ⭐ 回廊の基壇の4面(南妻・東面・北妻・西面)は閉じた一周をなすので、外向きは
      **その一周の重心から遠ざかる側**として機械的に決まる(⛔ 「回廊の芯 u0,v0」という
      literal を作図の中に持たない)。
    """
    if _WCOMP[0] is not None: return _WCOMP[0]
    W = d["terraceWalls"]
    par = list(range(len(W)))

    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    key = lambda q: (round(q[0], 4), round(q[1], 4))
    seen = {}
    for i, w in enumerate(W):
        for q in wall_nodes(d, w):
            k9 = key(q)
            if k9 in seen:
                a, b = find(seen[k9]), find(i)
                if a != b: par[a] = b
            else:
                seen[k9] = i
    comp = {}
    for i, w in enumerate(W):
        comp.setdefault(find(i), []).append(i)
    out = {}
    for _r, idx in comp.items():
        P = [q for i in idx for q in wall_nodes(d, W[i])]
        c = (sum(q[0] for q in P) / len(P), sum(q[1] for q in P) / len(P))
        for i in idx: out[W[i]["name"]] = c
    _WCOMP[0] = out
    return out


def wall_outward(d, g, w, a, b, k=None):
    """土留めの**外向き**(法尻を測る側)の単位法線[世界]。⛔ 符号を手で書かない。

    ① **石段の側壁** ── 石段の芯から遠ざかる側(`coping:"stair"`)
    ② **平場を受ける壁** ── 片側だけが平場の中なら、**平場でない**側(前庭の縁の5本)
    ③ ①②が決めない壁 ── **節点を共有する連なりの重心**から遠ざかる側(回廊の基壇の4面)
    """
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    nx, nz = -dz / L, dx / L
    mx, mz = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    if k is not None:                                    # ① 石段の芯から遠ざかる
        sp = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        best = None
        acc = 0.0
        for i in range(len(sp) - 1):
            ax, az = sp[i]; bx, bz = sp[i + 1]
            ddx, ddz = bx - ax, bz - az
            LL = math.hypot(ddx, ddz) or 1.0
            t = max(0.0, min(1.0, ((mx - ax) * ddx + (mz - az) * ddz) / (LL * LL)))
            q = (ax + ddx * t, az + ddz * t)
            dd = math.hypot(mx - q[0], mz - q[1])
            if best is None or dd < best[0]: best = (dd, q)
            acc += LL
        if best and ((mx - best[1][0]) * nx + (mz - best[1][1]) * nz) < 0: nx, nz = -nx, -nz
        return nx, nz
    ins = lambda q: any(in_poly(q, terrace_poly(te, g)) for te in d["terraces"])
    pr = d["const"]["wallProbeM"]                        # ⛔ 歩幅を二箇所に書かない(規則4)
    pa = ins((mx + nx * pr, mz + nz * pr))
    pb = ins((mx - nx * pr, mz - nz * pr))
    if pb and not pa: return nx, nz                      # ② 平場でない側
    if pa and not pb: return -nx, -nz
    cu, cv = wall_components(d)[w["name"]]               # ③ 連なりの重心から遠ざかる
    cx, cz = g.W(cu, cv)
    if (mx - cx) * nx + (mz - cz) * nz < 0: nx, nz = -nx, -nz
    return nx, nz


def wall_samples(d, g, w, step=1.0):
    """土留めの走りを `step`[m] 刻みに歩く。

    返り [(s, 天端, 低い側の地盤, 高い側の地盤, 見付高, 受け高, 犬走り or None, 建つか)]
    ── s は**節点の第一点から**の走り[m]。
    ⭐ **地盤は両側を採る**(`wall_ground`)【裁定 2026-09-09 = 検図21巡目 A案】── 見付高 =
      天端 − 低い側 ／ 受け高 = 高い側 − 天端。⛔ **一つの符号付きの量に畳まない**
      (0 が『段差が無い』なのか『未測定』なのか区別が付かなくなる)。
    ⭐ 天端 ── `coping` が数ならその値、`"stair"` なら**石段の割付 `stair_spans` から引く**
      (点を石段の折れ線へ落として走りの割合を出し、`stair_y_at` を通す)。
      ⛔ 側壁のためにもう一つの段割りを書かない(⚠ 二つの式で割ると蹴上1段ぶんずれる —
      2026-08-24 検図 高-4、男坂で最大 1.34 m)。
    ⭐ 「建つか」── `run_segs`(開口を抜いた実際に建つ区間)の上にあるか。⛔ 開口を実装に
      切り直させない。
    """
    P = [g.W(*q) for q in wall_nodes(d, w)]
    segU = run_segs(w)                                   # uv・開口を抜いた区間
    k = wall_stair(d, w)
    cop = w.get("coping")
    out, acc = [], 0.0
    for i in range(len(P) - 1):
        ax, az = P[i]; bx, bz = P[i + 1]
        L = math.hypot(bx - ax, bz - az)
        if L < 1e-9: continue
        nx, nz = wall_outward(d, g, w, P[i], P[i + 1], k)
        n = max(1, int(math.ceil(L / step)))
        for j in range(n + 1):
            if i and j == 0: continue                    # 節点の重複を落とす
            t = min(L, j * L / n)
            px, pz = ax + (bx - ax) * t / L, az + (bz - az) * t / L
            top = (stair_y_at(k, stair_sfrac(d, g, k, px, pz))
                   if k is not None else float(cop))
            glo, ghi, ben = wall_ground(d, g, px, pz, nx, nz)
            u9, v9 = g.U(px), g.V(pz)
            st = any(_pt_seg((u9, v9), q[0], q[1]) < 1e-3 for q in segU) if segU else False
            out.append((acc + t, top, glo, ghi, top - glo, ghi - top, ben, st))
        acc += L
    return out


def wall_profile(d, g, w, step=1.0):
    """焼き出し用の縦断 **6列** `[[s, top, groundLo, groundHi, faceH, backH], ...]`。

    ⛔ 実装が引き直さない。⭐ 6列である理由は `wall_ground` の docstring(裁定 2026-09-09)。
    """
    return [[round(q[i], 3) for i in range(6)] for q in wall_samples(d, g, w, step)]


def wall_gaps_s(sm, step=1.0):
    """`wall_samples` の列から、**建たない区間**(開口)の s の範囲 [[s0,s1], ...]。

    ⛔ 開口を数で持たない ── 出所は `run_segs`(= `gaps`/`gapFrom` からの従属値)そのもの。
    """
    out, run = [], False
    for q9 in sm:
        s9, st = q9[0], q9[-1]
        if st:
            run = False; continue
        if run and out and s9 - out[-1][1] <= step * 1.001 + 1e-6:
            out[-1][1] = s9
        else:
            out.append([s9, s9]); run = True
    return [[round(a, 3), round(b, 3)] for a, b in out]


# ---------------------------------------------------------------- 回廊の基壇の展開
def kidan_svg(d, kan="其十"):
    """回廊の基壇の石垣を四面ぶん展開する(スキル §3c の土留めの続き)。

    平面では**見付高**が読めない — 天端は `coping` で一定でも、地盤は平場の縁が退く北で深く
    なる。**南妻 → 東面 → 北妻 → 西面**の順に一周を伸ばす。
    ⭐ **地盤の線は `wall_samples` の『両側の低い側』**【裁定 2026-09-09 = 検図21巡目 A案】──
      ⛔ 旧図は西面(裏)を平場の高さで一定に描き、**まっすぐな矩形**として刷っていた
      (中4 検図21巡目・`sashizu.md` §3c『土留めは設計高さの矩形で描かない。その位置の地盤まで
      描く』)。⛔ 数値を文章へ写さない — 数の正典は焼き出しの `runs[].profile` である。
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
    kei = plane_y(d, d["planes"][0])

    # ⭐ **法尻は `wall_samples` から引く**【中4 検図20巡目 → 2026-09-09】── 焼き出しが実装へ
    #   渡す縦断と**同じ関数**を通す。⛔ 展開図が自前で外向きを決めて自前で法尻を解かない
    #   (旧図はここだけが `ws_cop` に天端を書き込み、`face_toe` がそれを読んでいた)。
    rows, acc = [], 0.0
    for (nm, a, b, w), L in zip(faces, segl):
        dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = wall_outward(d, g, w, a, b, wall_stair(d, w))
        sm = wall_samples(d, g, w, STEP)
        rev = (nm in ("TW_Kairo_N", "TW_Kairo_W"))     # 一周の向きに合わせて s を返す
        for s9, _top, glo, _ghi, _fh, _bh, ben, _st in sm:
            t = (L - s9) if rev else s9
            px, pz = a[0] + dx * t, a[1] + dz * t
            nat = dem_h(px + nx * 1.2, pz + nz * 1.2)
            # ⭐ **法尻は『両側の低い側の造成後の地盤』**【裁定 2026-09-09 = 検図21巡目 A案】。
            #   ⛔ 旧図は西面(裏)を平場の高さで一定に描き、**まっすぐな矩形**として刷っていた
            #   (中4 検図21巡目・`sashizu.md` §3c『設計高さの矩形で描かない。地盤まで描く』)。
            rows.append((acc + t, glo, nat if nat is not None else glo, nm, ben))
        rows.sort(key=lambda r: r[0])
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
    o.append(T(6, 15, kan + "　回廊の基壇の展開 ─ 南妻 → 東面 → 北妻 → 西面(石垣の見付高)",
               fs=12.5, fill="var(--dim)"))
    o.append(T(W - 6, 15, "垂直 %.1f 倍 ／ 一周 %.1f 間 = %.1f m" % (VEXK, tot / ken, tot),
               fs=11, anchor="end", fill="var(--dim)"))
    o.append(T(6, H - 24, "見付高(天端 − 両側の低い側の地盤)── " + " ／ ".join(txt),
               fs=10.5, fill="var(--ishi)"))
    o.append(T(W - 6, H - 8, "破線 = 現地形 ／ 細実線 = 地盤(両側の低い側・造成後) ／ 点線 = 犬走り"
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


def used_prefabs(d):
    """**当図が実際に据える prefab** ── 層 → {prefab}。⛔ 数を json に持たない。

    ⚠ 「目録に在る変種の全部」ではない ── 大きさは `sizeRule` が**丈から**選ぶので、
    当図の丈の範囲に現れない変種は据えない。⭐ 走査する先は `_scaley_rows` と同じ
    (帯の撒き木・林縁・塊・一本立ち・主景・視線の塊)。
    """
    out = {}

    def add(lay, pt, h):
        if not pt: return
        vs, _a, _b = pick_variants_over(d, pt, h)
        st = out.setdefault(lay, set())
        if vs:
            for q in vs: st.add(q[1])
        elif pt.get("prefab") and _SIZE_HOLE not in pt["prefab"]:
            st.add(pt["prefab"])

    LAY = (("松", "matsuH"), ("落葉", "rakuyoH"), ("中木", "chubokuH"), ("低木", "teibokuH"))
    for b in d["slopeBands"]:
        for o in (b, b.get("rinen") or {}):
            for lay, hk in LAY:
                if not o.get(hk): continue
                for pt in d["planting"]["parts"].get(lay) or []: add(lay, pt, o[hk])
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            if not any(zone_h(d, gd)): continue
            for kind, pt, _n, h, _cr, sk, _vs, _a, _b in cluster_parts(d, gd, c):
                add("松" if sk == "matsu" else "落葉", pt, h)
        for sg in gd.get("singles", []):
            for pt in single_parts(d, sg)[:1]: add(sg.get("layer") or "落葉", pt, sg.get("h"))
        sk_ = gd.get("shukei")
        if sk_ and sk_["tree"].get("part"):
            for pt in d["planting"]["parts"]["落葉"]:
                if pt.get("api") == sk_["tree"]["part"]: add("落葉", pt, shukei_hmin(d, sk_))
    # 下草は丈を宣言しない層(連続の林床)なので palette そのものが据える点
    for pt in d["planting"]["parts"].get("下草") or []:
        if pt.get("prefab"): out.setdefault("下草", set()).add(pt["prefab"])
    return out


def palette_table(d):
    """**部材の palette**(層 × 個体 × 用いる prefab)。⭐ 2026-09-08 に起こした。

    ⛔ 数を json に写さない ── 「用いる prefab」は `sizeRule` が丈から選んだ変種の**和集合**で、
    図が毎回算出する。⚠ **下草の3点は html に一度も出ていなかった**(規則19: 図に出ない宣言)。
    """
    rows, tot = [], 0
    U = used_prefabs(d)
    for lay in ("松", "落葉", "中木", "低木", "下草"):
        pal = d["planting"]["parts"].get(lay) or []
        used = U.get(lay) or set()
        tot += len(used)
        got = sum(1 for pt in pal
                  if (part_geom(pt) is not None) or part_variants(d, pt))
        rows.append("<tr><td>%s</td><td>%d 点</td><td>%s</td><td><b>%d 種</b>【算出】</td>"
                    "<td class='note'>%s</td><td class='note'>%s</td></tr>"
                    % (lay, len(pal),
                       "目録に在る %d 点／`pending` %d 点"
                       % (got, sum(1 for pt in pal if pt.get("pending"))),
                       len(used),
                       "<br>".join(inline(pt.get("api") or "—") for pt in pal),
                       "／".join(sorted(used)) or "—"))
    return ('<div class="tw"><table><thead><tr><th>層</th><th>palette の点</th>'
            '<th class="note">目録との照合</th><th>用いる prefab</th>'
            "<th class='note'>api</th><th class='note'>解けた prefab</th></tr></thead><tbody>"
            + "".join(rows)
            + "<tr><td><b>計</b></td><td></td><td></td><td><b>%d 種</b>【算出】</td>"
              "<td class='note'></td><td class='note'></td></tr>" % tot
            + "</tbody></table></div>")


def bom_table(d):
    """部材表。⭐ **葺材の欄を足した**【中10 考証19巡目 → 2026-09-09】── ⛔ 旧表は屋根材を
    `munes[].roof` の**文字列にしか持たず、部材の当たりへ一度も降りていなかった**
    (`bom` に『本瓦』が 0 件)⇒ **銅瓦と本瓦の格差が絵に出ない**(規則19)。
    """
    rows = []
    n9 = 0
    for b in d["bom"]:
        rf = b.get("屋根")
        if rf: n9 += 1
        rows.append("<tr><td>%s</td><td>%s</td><td class='note'>%s</td><td class='note'>%s</td>"
                    "<td>%s</td></tr>"
                    % (inline(b["部材"]), inline(b["在庫"]), inline(rf or "—"),
                       inline(b["手当"]), b["優先"]))
    return ('<div class="tw"><table><thead><tr><th>部材</th><th>在庫</th>'
            '<th class="note">屋根(葺材)</th><th class="note">手当</th>'
            "<th>優先</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            + '<p class="cap">⭐ <b>葺材の欄は 2026-09-09 に足した</b>【中10 考証19巡目】── '
              '⛔ 旧表は屋根材を <code>munes[].roof</code> の文字列にしか持たず、'
              '<b>部材の当たりへ一度も降りていなかった</b>ので、<b>銅瓦(社殿5棟+中門+透塀)と'
              '本瓦(境内の堂宇・供の棟)の格差が絵に出なかった</b>。'
              '⚠ 葺材を宣言する行は <b>%d 行</b>で、⛔ <b>瓦材の部材名は目録にも '
              '<code>EdoAssets.cs</code> にも無い</b>(→ 未決の表)。'
              '⛔ この巡で「格差が出た」と記録しない ── 比較対象(境内9棟の部材)がまだ無い。</p>'
              % n9
            # ⭐⭐ **葺材の根拠は一箇所に置いて参照させる**【C-1 考証20巡目 → 2026-09-09 十九巡目】
            #    ⛔ 同じ文を 9 棟へ写さない(規則4)。⛔ 置いただけで図に出ない宣言も作らない(規則19)。
            + ('<p class="cap">%s</p>' % inline(d.get("_roofMaterialBasis") or ""))
            + ("<p class='cap'>⚠ **葺材を宣言する棟** %d／%d ── ⛔ 欄の空いた棟を残さない"
               "(葺材の一覧がどこでも引けなくなる)。</p>"
               % (sum(1 for m in d["munes"] if m.get("roof")), len(d["munes"]))))


def _rng(v, unit="", fmt="%g"):
    """[lo,hi] は「lo〜hi」、単値はそのまま、無ければ「—」。"""
    if v is None: return "—"
    if isinstance(v, (list, tuple)): return "%s〜%s%s" % (fmt % v[0], fmt % v[1], unit)
    return (fmt % v) + unit


def species_h_note(d, lay, h):
    """帯の宣言に対して**樹種ごとの頭打ち**が効く樹種を刷る(効かなければ空)。

    ⭐ 庭方 2026-09-08 裁定1 の但し書き ── 「帯は 13.0〜16.0 と宣言し、実際に立つムクノキは
    13.0〜15.40」。**この食い違いが図に出ないと、次の巡で同じ事故になる。**
    ⛔ 数を json に持たない ── 目録の素の丈 × 箍 からの従属値。
    """
    lo, hi = _h_pair(h)
    if lo is None: return ""
    seen, out = set(), []
    for pt in d["planting"]["parts"].get(lay, []):
        sp = pt.get("species") or pt.get("api")
        if sp in seen: continue
        cp = species_h_cap(d, pt)
        if cp is None or cp >= hi - 1e-9: continue
        seen.add(sp)
        out.append("%s %.1f〜%.2f m" % (sp, lo, max(lo, cp)))
    if not out: return ""
    return ("<br><b>実際に立つのは %s</b>(樹種ごとの頭打ち = その樹種の最大変種の素の丈 × 箍"
            "【従属】)" % " ／ ".join(out))


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
            # ⭐ **退避は層ごと**【裁き1 庭方 2026-09-08】── 一つの数で三層を代表させない。
            #    ⚠ 帯4 は額縁の宣言(層で分けない)なので三つとも同じ値が出る。
            area += ("(退避 高木 %s ／ 中木 %s ／ 低木 %s → 有効 高木 %s ／ 中木 %s ／ 低木 %s)"
                     % tuple(format(int(round(r[k][q])), ",")
                             for k in ("avoidBy", "usableBy") for q in ("松", "中木", "低木")))
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
                        + " ／ 丈 " + _rng(b.get("rakuyoH")) + " m"
                        + species_h_note(d, "落葉", b.get("rakuyoH"))) if b.get("rakuyoRatio") else "—",
                       _rng(b.get("chubokuPer100")), _rng(b.get("chubokuH")),
                       _rng(b.get("teibokuPer100")) + (" / %s m" % _rng(b.get("teibokuH"))
                                                       if b.get("teibokuH") else ""),
                       b.get("shitakusa", "—"), b.get("acc", "—")))
    for b in d["slopeBands"]:
        r = b.get("rinen")
        if not r: continue
        # ⭐ **林縁の面と本数を刷る**(2026-09-08 十六巡目 A-4/C-2)── 旧図は密度と丈しか出さず、
        #    **面も本数もどこにも無かった**ので「効いていない」ことが図から読めなかった(規則19)。
        rw = ([q for q in band_stats(d, g) if (q.get("b") or {}).get("band") == b["band"]] or [{}])[0]
        ar_ = rw.get("rinenBy", {}).get("低木", rw.get("rinen", 0.0))
        rows.append("<tr><td>└ 林縁の帯(帯%d)</td><td class='note'>%s から %g〜%g 間</td>"
                    "<td>%s 坪【算出】</td><td>0 本(高木を置かない)</td><td>%g</td>"
                    "<td>—</td><td>—</td><td>—</td><td>%s / %s m</td><td>%s / %s m</td>"
                    "<td>%s</td><td class='note'>%s</td></tr>"
                    % (b["band"], (r.get("edgeFrom") or "社地の境"), r["fromKen"], r["toKen"],
                       format(int(round(ar_)), ","), r.get("takagiPer100", 0.0),
                       # ⭐ 2026-09-07 九巡目 中3 ── 林縁の丈も刷る(⛔ 密度だけ刷ると
                       #    『丈は測っていない』ことが図から読めない・規則19)。
                       ("%g (%d 本)" % (rinen_dens(d, b, "中木") or 0.0,
                                        int(round(_rinen_layer_n(b, r, "中木") or 0.0)))),
                       _rng(rinen_h(d, b, "中木")),
                       ("%g (%d 本)" % (rinen_dens(d, b, "低木") or 0.0,
                                        int(round(_rinen_layer_n(b, r, "低木") or 0.0)))),
                       _rng(rinen_h(d, b, "低木")),
                       r.get("shitakusa", "—"), r.get("acc", "帯4の規定")))
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
    src = (list(d["gardens"]) + [b for b in d["slopeBands"] if b.get("clusters") or b.get("singles")]
           + view_holders(d))
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
            if c.get("alongTakagiEdgeLine"):
                # ⭐ **平行四辺形**(2026-09-08 C-1)── ⛔ 軸平行の箱で刷らない
                bx = ("高木の縁の線に沿う**平行四辺形** 幅 %g 間 ／ v %g〜%g ／ 線の実長 %s m"
                      "【算出】" % (c.get("widthKen", 0), c["vRange"][0], c["vRange"][1],
                                    "—" if c.get("_lineLenKen") is None
                                    else "%.2f" % (c["_lineLenKen"] * ken)))
            if c.get("split"): bx += " ／ " + c["split"]
            rl = c.get("role", "")
            if c.get("overhangFrom"):
                oh = overhang_range(d)
                # ⛔ **符号を捨てない**(2026-09-07 中2)— 負 = 一本も道の上へ出ない、が答え
                if oh and oh[0] is not None:
                    rl += ("(道への張り出し %+.2f〜%+.2f m【従属】"
                           "／負 = 道へ出ない・引けない部材 %d 点" % (oh[0], oh[1], oh[3]))
                    # ⭐ **上限を同じ欄に刷る**【裁定2 庭方 2026-09-07】── 量だけ刷って
                    #   「どこまで出てよいか」を刷らないと、正の値が欠陥に読める。
                    lm = overhang_limit(d, c)
                    if lm:
                        mn = min(q[1] for q in lm)
                        rl += ("／ **上限** %.2f〜%.2f m【局所の(路肩+側溝)− %.2f m】"
                               "・余裕 %+.2f m ／ ⭕ 正 = 路肩の上へ差し掛かる(役)・"
                               "⛔ 下限は置かない"
                               % (mn, max(q[1] for q in lm),
                                  (c["overhangFrom"] or {}).get("marginM") or 0.0, mn - oh[1]))
                    rl += ")"
                else:
                    rl += "(道への張り出しは**部材が目録に無く測れない**)"
            pt = ""
            rows_p = cluster_parts(d, gd, c) if any(zone_h(d, gd)) else []
            if rows_p:
                seg = []
                # ⭐ **芯々−樹冠は同じ層の中だけで測る**【中3/低3 庭方 2026-09-07 八巡目】──
                #   社叢は松の林冠の上に落葉の大木がまばらに頭を出す姿で、**跨層の重なりは
                #   欠陥ではなく構造**。層に1本しか居なければ測る相手が居ない。
                nlay = {}
                for kind, _p, n, _h, _cr, sk, _v, _a, _b in rows_p:
                    nlay[sk] = nlay.get(sk, 0) + n
                for kind, part, n, h, cr, sk, vs, ylo, yhi in rows_p:
                    hh = ("丈 %s m" % _rng(h)) if h else "丈—"
                    cc = ("樹冠 %.1f〜%.1f m" % cr) if cr else "樹冠—(目録に無い)"
                    ov = ""
                    if cr and c.get("spacing") and nlay.get(sk, 0) >= 2:
                        # ⭐ 2026-09-07 庭方3巡目 低6② — **`packRatio` を掛けた後の数を刷る**。
                        #   掛ける前の数(宣言の芯々)で刷ると「塊の中で樹冠が触れない」と読め、
                        #   塊が塊にならない読みになる。塊の中の実際の芯々は詰めた後の値。
                        pk = d["planting"]["plantRule"].get("packRatio", 1.0)
                        gp = c["spacing"] * ken * pk - (cr[0] + cr[1]) / 2.0
                        ov = "／ **同層**の芯々(packRatio 後)−樹冠 %+.1f m" % gp
                    elif cr and nlay.get(sk, 0) < 2:
                        ov = "／ 芯々−樹冠は測らない(この層はこの塊に 1 本 — **跨層で測らない**)"
                    nm_pf, nm_api = cluster_part_label(part, vs)
                    sy = ("・scaleY %.3f〜%.3f【従属】" % (ylo, yhi)) if ylo else ""
                    seg.append("%s×%d <span class='note'>%s・%s・%s%s %s</span>"
                               % (nm_pf, n, hh, cc, nm_api, sy, ov))
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
        # ⭐ **林床の宣言を刷る**【低7 庭方 2026-09-07 九巡目】── 旧版は区の `asset` の行が
        #    中木・低木・下草を名指ししながら、区は密度をどこにも持っていなかった。
        #    ⛔ **沈黙で済ませない** — 名指しだけあって到達しない宣言は規則19 の欠陥である。
        if gd.get("_asset"):
            rows.append("<tr><td>%s</td><td>%s</td><td>林床</td><td class='note'>—</td>"
                        "<td>—</td><td>—</td><td>%s</td><td class='note'>%s</td></tr>"
                        % (_gname(gd) if first else "", ar if first else "",
                           inline(gd.get("asset", "—")), inline(gd["_asset"])))
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
    # ⭐ **★主景の一本も部材・大きさ・`scaleY`・樹冠まで刷る**【A-2 の裁き 庭方 2026-09-08】──
    #    旧図はこの行だけ丈と api しか刷らず、**社頭で最も重い一本が照合に載っていなかった**。
    #    ⭐ **2026-09-09 十九巡目 A-1 で『名指しの木』へ移した** ── ⛔ 塊の内訳ではないので、
    #    行は `named_tree_rows` から組む(⛔ 塊の丈の範囲・`scaleRule.rakuyo.scaleXZ` を当てない)。
    for r9 in named_tree_rows(d, g):
        if not r9.get("shukei"): continue
        sk = ([gd.get("shukei") for gd in d["gardens"]
               if gd.get("shukei") and gd["shukei"]["tree"]["name"] == r9["name"]] or [None])[0]
        rows.append("<tr><td></td><td></td><td>★主景の木(%s)</td>"
                    "<td class='note'>(%g, %g)・眼高 %.1f m の楼門から・区『%s』</td>"
                    "<td>1本</td><td>—</td>"
                    "<td>%s 丈 %s m 以上【従属 — 落葉の最も高い変種 × 箍 `sizeRule.scaleYMax`】 ／ "
                    "%s ／ 大きさ %s ／ scaleY %s ／ 樹冠 %s(`scaleRule.isolatedXZ`)</td>"
                    "<td class='note'>%s</td></tr>"
                    % (r9["name"], r9["u"], r9["v"], (sk or {}).get("eyeY") or 0.0,
                       r9.get("zone") or "—", r9["kind"],
                       "—" if r9["h"] is None else "%.1f" % r9["h"],
                       r9.get("part") or "—", r9.get("size") or "—",
                       ("%.3f" % r9["scaleY"]) if r9.get("scaleY") is not None else "—",
                       ("%.2f m" % r9["crownM"]) if r9.get("crownM") else "—",
                       "名指しの木 ── ⛔ 区の塊の一本として撒かない(丈の範囲が宣言を切り落とす)"))
    pl = d.get("planting", {}).get("edgeUnderstory")
    if pl:
        # ⭐ **丈・部材・本数を刷る**【中2 庭方 2026-09-08】── 旧図は `insetKen`/`spacing`/`veg`
        #    だけで、丈も部材も本数もどこにも出ていなかった(⛔ 0 件は合格ではなく未測定)。
        ar, nn = edge_understory_stats(d)
        rows.append("<tr><td>平場の縁の下層</td><td>%s</td><td>低木の帯</td>"
                    "<td class='note'>縁のオフセット線から内側 %g 間</td><td>%s</td><td>%g 間</td>"
                    "<td>%s ／ 丈 %s m ／ 部材 %s</td>"
                    "<td class='note'>3区が共有する辺なので一度だけ定める</td></tr>"
                    % ("—" if ar is None else "%.0f 坪【算出】" % (ar * ken * ken / TSUBO),
                       pl["insetKen"],
                       "—" if nn is None else "%d 本【算出 — 面 ÷ 芯々²】" % int(round(nn)),
                       pl["spacing"], pl["veg"], _rng(pl.get("hM")),
                       "／".join(inline(q.get("api") or "—")
                                 for q in d["planting"]["parts"].get("低木", [])) or "—"))
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
    ⛔ 記号 P(プロジェクト内実測)を地下水位の推定に使わない — 確度は【U 設計値】。
    ⚠ 旧版はここに【B 常態】と書いていたが、『台地の縁の掘井戸は江戸の常態【B】』は
    2026-09-07 考証7巡目 中1 で取り下げられている(掃き残し・検図12巡目 の巡で直した)。
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
             "石敷の天端 %.2f − 地下水面(上限=東麓の池 %.1f"
             "【A `[五千分一東京図31]` ／ P 当方の図上の読み】"
             "／下限=溜池の水面 %.1f【P】)からの引き算【算出】。"
             "⚠ 上限の格は**台帳の格 A**で、水面の数字そのものは**当方が明治十六年の図から読んだ値**"
             "【P】── ⛔ 台帳より高い格(S)を当図が勝手に名乗らない【低1 考証16巡目 → 2026-09-08】。"
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


def sankaku_table(d, g):
    """前庭の**立面の三尊** ── 梢の仰角は三点と見所からの従属値(⛔ json に数を持たない)。

    ⭐ **2026-09-09 十九巡目 A-5 で平面から立面へ物差しを替えた**。⛔ 三辺の長さで測らない
    (帯の幅が高木の樹冠より狭いので、平面の三角形は幾何として作れない)。
    """
    sk, pts, _sides = sankaku_rows(d)
    if not sk: return ""
    vnm, vp, eye, esrc, rows, miss = sankaku_elev_rows(d, g)
    tr = "".join("<tr><td><b>%s</b> %s</td><td class='note'>%s</td><td>%s</td><td>%s</td>"
                 "<td><b>%s</b></td></tr>"
                 % (yk, nm, "%.1f m 先" % L, "丈 %.1f m" % h, "梢 %.2f m" % top, "%.2f°" % ang)
                 for yk, nm, L, top, ang, h in rows)
    for nm9, yk9 in miss:
        tr += ("<tr><td><b>%s</b> %s</td><td colspan='4' class='note'>**位置か丈が引けない**"
               "</td></tr>" % (yk9, nm9))
    A = sorted(r[4] for r in rows)
    cap = ""
    if len(A) >= 3:
        cap = ("見所 <b>%s</b>(眼高 %.2f m ／ %s)から、梢の仰角の<b>最も近い二つの差 %.2f°</b>"
               "(下限 %.2f°)【算出 — ⛔ 平面の面積・三辺の長さでは測らない】<br>"
               % (vnm, eye or 0.0, esrc or "—", min(A[1] - A[0], A[2] - A[1]),
                  sk.get("minDiffDeg") or 0.0))
    return ('<div class="tw"><table><thead><tr><th>前庭の立面の三尊</th>'
            "<th class='note'>見所からの距離</th><th>丈</th><th>梢の標高</th><th>仰角</th>"
            "</tr></thead><tbody>" + tr + "</tbody></table></div>"
            + "<p class='cap'>%s%s</p>" % (cap, inline(sk.get("_", ""))))


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
    miss = []
    for key, n, ns, avg, place, place_sg in plant_budget(d, g):
        pend = any(pt.get("pending") for pt in d["planting"]["parts"][key])
        t = None if avg is None else (n + ns) * avg
        if t: tot += t
        if avg is None:
            miss.append("%s(%s)" % (key, "新造待ち" if pend else "目録に無い"))
        rows += ("<tr><td>%s</td><td>%s 本</td><td>%s 本</td><td>%s</td><td>%s</td>"
                 "<td class='note'>%s</td></tr>"
                 % (key, format(n, ","), format(ns, ","),
                    ("—(**新造待ち**)" if pend else "—(**目録に無い**)")
                    if avg is None else "%s 三角/本" % format(int(avg), ","),
                    "—" if t is None else "%s 三角" % format(int(t), ","),
                    "%s ／ 一本立ちは %s" % (PLACE_JA.get(place, place or "**宣言が無い**"),
                                            PLACE_JA.get(place_sg, place_sg or "**宣言が無い**"))))
    # ⛔ **どの層が計に入っていないかを数え直して刷る**(⛔ 名を書き写さない・2026-09-07)。
    #   落葉高木3種が目録に入った日に、この行が「落葉は入っていない」と嘘を刷り続けた。
    rows += ("<tr><td><b>計(測れた分)</b></td><td></td><td></td><td></td><td><b>%s 三角</b></td>"
             "<td class='note'>%s</td></tr>"
             % (format(int(tot), ","),
                ("⚠ **この計に入っていない層** — " + "・".join(miss)) if miss
                else "⭕ **すべての層が目録から引けている**(計に入っていない層は無い)"))
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
    # ⭐ **局所の値を刷る**【裁定2 庭方 2026-09-07 八巡目】── ⛔ 代表値だけを刷ると
    #   「路肩は 2.3 m」と読まれ、林縁の張り出しの判定に最も狭い東西の帯の値が当たる。
    _lo = _hi = None
    for _c in d["slopeBands"][3].get("clusters", []):
        for _v, _mx, _ro, _rs in overhang_limit(d, _c):
            _q = (sando_road_width(d, _v), _ro, _rs, _mx, _v)
            _lo = _q if _lo is None or _q[1] < _lo[1] else _lo
            _hi = _q if _hi is None or _q[1] > _hi[1] else _hi
    _s = "土。" + inline(rs.get("rokataRule", "道敷の幅から従属"))
    if _lo:
        _s += ("　⭐ **楔形の区間の局所値【算出】** ── 道敷 %.2f〜%.2f m ／ 片側の路肩 "
               "%.2f〜%.2f m ／ 社地の境から路面の西縁まで %.2f〜%.2f m ／ "
               "**林縁の張り出しの上限 %.2f〜%.2f m**(v %g〜%g)"
               % (_lo[0], _hi[0], _lo[1], _hi[1], _lo[2], _hi[2], _lo[3], _hi[3],
                  _lo[4], _hi[4]))
    row("路肩", _s)
    for sec in rs["sections"]:
        row(sec["name"], "延長 %.1f m ／ 植栽 %s" % (sec["len"], sec.get("planting", "—")))
    row("柵(社地側)", "境から %g 間 ／ run `%s`(部材は Saku_SW と同じ)"
        % (w["sakuKen"], [q["name"] for q in d["runs"] if q.get("edgeFrom")][0]))
    row("林縁", "境から %g〜%g 間 ／ 低木+下草" % (w["rinenKen"][0], w["rinenKen"][1]))
    row("高木の縁の線",
        "**道敷に接する辺**(⛔ 番号を持たない — `edgeFrom` が毎回同定する)を内側へ %g 間 ／ "
        "(%g, %g)〜(%g, %g) ／ 芯々の正典は `slopeBands[3].clusters[参道の林縁]` の "
        "`groupSpacingKen` / `groupGapKen`(⛔ 旧 `firstRowSpacing`/`innerSpacing` は "
        "2026-09-09 十八巡目に廃した・指4 庭方)"
        % (tl["insetKen"], tl["uv"][0][0], tl["uv"][0][1], tl["uv"][1][0], tl["uv"][1][1]))
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
    av = [b["avoid"] for b in d["slopeBands"] if b.get("avoid") and b.get("uv")]
    for a in av:
        row("帯4の退避", "男坂の芯から %g 間 ／ 女坂の路肩から %g 間 ／ 参道の芯から %g 間 ／ 前庭の縁から %g 間"
            % (a["otokozakaFromAxis"], a["onnazakaFromShoulder"], a["sandoFromAxis"], a["zenteiFromEdge"]))
    ba = (d["planting"]["bandDef"] or {}).get("avoid") or {}
    if ba.get("kaidanShoulderKen"):
        rmin_ = min_matsu_crown_r(d)
        sh_ = ba["kaidanShoulderKen"]
        row("帯1〜3の退避(石段)",
            "石段の芯から **敷きの半幅 + その層の肩**【従属 — 半幅は `kaidans[].wKen`/2】 ／ "
            "肩 %s ／ 退避する層 %s ／ ⛔ 下草は敷きの外なら可(石段の目地の草は掃く場所)／ "
            "**上限**: 肩(高木)＜ 当図に現れる最も細い松の樹冠の半径 %s"
            % ("・".join("%s %g 間" % (k, sh_[k]) for k in ("松", "落葉", "中木", "低木")
                         if k in sh_),
               "・".join(ba.get("layers") or []),
               "—" if rmin_ is None else
               ("%.3f m(余裕 %+.3f m)【算出】"
                % (rmin_, rmin_ - (sh_.get("松") or 0.0) * d["const"]["ken"]))))
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


CHECK_SHOW = 60                 # 検査の一覧に刷る行の上限(⛔ 切ったら切ったと書く)


def checks_table(rows):
    """検査の一覧 ── **0件でも必ず刷る**(規則19。2026-09-06 検図4巡目 中7)。

    ⚠ 2026-09-07 — 上限が 8 行だったので、面ごとの Δ を回した途端に**まとめの行が表から落ちた**
    (端末には出るが図には出ない = 報告経路に繋がっていない)。上限を上げ、切った件数を明記する。
    """
    tr = []
    for nm, bad, note in rows:
        # ⭐ **⚠ と ⭕ の行を先に刷る**【2026-09-08】── 上限で切ると、いちばん読まれねばならない
        #    猶予の行(⚠)が末尾に居て落ちる。`wiring_gate.py --surfaced` が
        #    「測ったのに図に出ていない」で捕まえた(規則19・第3型)。
        # ⭐ **⭕ を ⚠ と同格へ上げた**【中1 検図17巡目 → 2026-09-08・案A】── ⚠ だけを前へ出す
        #    並べ替えでは、**カナリヤの集計行(⭕ で始まる)が対象外**だった。検査11 は〔記録〕が
        #    `CHECK_SHOW` を超えるので、末尾に居る『⭕ 樹種ごとの頭打ちが効いた行 N』と
        #    『⭕ `pendingRef` を立てた部材で箍を超える行は 0』が「…ほか N 件」に切られて
        #    **図から落ちていた** ── ⛔ **カナリヤ自身が図に出ていなければ、規約が死んでも
        #    誰も気づかない**(庭方 裁定1 の但し書き・規則19)。
        # ⛔ `CHECK_SHOW` を上げて凌がない(切られる 93 件がそのまま図へ雪崩れる)。
        _FRONT = ("⚠", "⭕")
        qs = bad + [q for q in note if q.startswith(_FRONT)] + [q for q in note
                                                                if not q.startswith(_FRONT)]
        body = [html.escape(q) for q in qs[:CHECK_SHOW]]
        if len(qs) > CHECK_SHOW:
            body.append("…ほか %d 件(生成器の標準出力に全件)" % (len(qs) - CHECK_SHOW))
        # ⭐ **検査名を機械抽出できる形で持たせる**【高3 考証19巡目の帰結 → 2026-09-09】──
        #    ⛔ 銘の中に `<code>` が入るので、素朴な正規表現では **47 本中 29 本しか拾えない**。
        #    ⭕ `data-check` に**印付けを外した素の名**を置き、抽出が漏れない形にする(規則19)。
        tr.append("<tr data-check=\"%s\"><td>%s</td><td>%d</td><td>%d</td>"
                  "<td class='note'>%s</td></tr>"
                  % (html.escape(re.sub(r"[`*]", "", nm)), nm, len(bad), len(note),
                     "<br>".join(body) or "—"))
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

    ⭐ **何本を検めたのかを毎回刷る**【低2 検図17巡目 → 2026-09-08】── 旧式は ⛔ 0 件 ／
    〔記録〕 0 件で、**測った集合の大きさが図に一度も出ていなかった**(規則19 — 0 件は
    「緩い条件で通った」証拠にしかならない)。
    ⚠ **前方一致(略題で引く)は残す** ── 実測で 7 本が長い題の項を略題で指しており、
    ⛔ 完全一致だけへ締めると図が壊れる。⭕ ただし**題目より広い集合を測っていること**は
    隠さない — 前方一致どまりで通った参照を**一本ずつ名指しする**。
    """
    keys = list((d.get("_pending") or {}).keys())
    bad = []
    _exact, _pref = [], []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items(): walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o): walk(v, path + "[%d]" % i)
        elif isinstance(o, str):
            for nm in _PENDRE.findall(o):
                if any(k == nm for k in keys):
                    _exact.append(nm)
                elif any(k.startswith(nm) for k in keys):
                    _pref.append((path, nm))
                else:
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
    note = ["`_pending` への参照 **%d 本** ── **完全一致 %d ／ 前方一致どまり %d**"
            "【算出 — ⚠ 前方一致は『題目より広い集合を測っている』ことを意味する。"
            "⛔ 締めない(7 本が略題で引いている)が、隠さない】"
            % (len(_exact) + len(_pref), len(_exact), len(_pref))]
    for path, nm in sorted(set(_pref)):
        note.append("⚠ 前方一致で通った参照 %s ── 略題「%s」が指す項の題は「%s」"
                    "【算出 — ⛔ 完全一致ではない】"
                    % (path, nm, "／".join(k for k in keys if k.startswith(nm) and k != nm)))
    return bad, note


# ================================================================ 実装が読む算出物(`--export-impl`)
# ⭐ **なぜ焼くか**(2026-09-08 棟梁が Stage 1 の一手目で止まった)。
#   造成後の地盤 `design_y`・境内の囲いの折れ線(平場の輪郭からの生成物)・石段の割付
#   `stair_spans`・社叢に撒く木の位置は、**指図の json には一つも入っておらず**、
#   この生成器だけが持っている。C# へ移植すると正典が二つになって黙ってドリフトするので
#   (⚠ 実例 — 切盛図と断面が男坂で最大 1.34 m 食い違い、段割りを `stair_spans` 一つへ
#   寄せて直した)、**2026-09-03 ユーザー裁定1=A の作法**に倣ってここから焼き出す。
#   ⛔ 焼き出し用に別の実装を書かない — **図が使うのと同じ関数の返り値**をそのまま書くこと。
IMPL_OUT = os.path.join(DOC, "sanno_impl.json")
DEM_JSON = os.path.join(DOC, "sanno_dem.json")
# 焼き出しの地盤の格子[m]。⛔ **設計値ではない** — 地形のハイトマップが世界軸の格子なので、
# 回転させず世界座標のまま 1 m で刻む(この社のグリッドは世界軸そのものなので回転は元より無い)。
IMPL_STEP = 1.0
# 土留めの縦断を焼く走りの刻み[m]。⛔ **設計値ではない**(検図20巡目 中4 の求めが「1m 刻み」)。
IMPL_WALL_STEP = 1.0
# ⭐ **物差しは二つある。混ぜない**【中3 検図20巡目 → 2026-09-09】。
#   どちらも ⛔ **検査の物差しであって設計値ではない**(だから json ではなくここに置く。
#   岡部も `("checks", {"gradeTol": 0.30, "baseMin": bmin})` を生成器側に持つ)。
# ① `exportTol` ── **図の側**。焼き出した `graded` と `design_y` の許容差[m]。
#   同じ関数から出ている以上、丸めの 0.001 m 以外は出ないはず(⛔ 緩めて黙らせない)。
# ② `gradeTol`  ── **実装側**。造成した Unity の地形と設計面の許容差[m]。
#   ⚠ ハイトマップは 16bit 正規化なので量子が 0.003〜0.009 m あり、⛔ ここへ 0.001 を
#   入れると棟梁の造成後QAが**全セル不合格**になる。意味の正典は
#   `EdoOkabeYashikiBuilder.IMPL` の doc コメント(岡部は 0.30)で、同じ値に揃える。
IMPL_EXPORT_TOL = 0.001
IMPL_GRADE_TOL = 0.30


def _sha256(path):
    """ファイルの**バイト列**の SHA-256(小文字hex)。⛔ 中身を読み直して作り直さない。"""
    import hashlib
    h9 = hashlib.sha256()
    with open(path, "rb") as f9:
        h9.update(f9.read())
    return h9.hexdigest()


def _seed_rnd(d, name, lay):
    """撒く乱数の種 ── **`planting.plantRule.seed` の宣言そのもの**(「帯・区の名 + '/' + 層の名」)。

    ⛔ 時刻や連番で振らない(流し直すたびに木が動くと検証レンダが比較できない)。
    ⛔ 宣言が無ければ止める — 種の出所が指図に無いまま撒くと、**同じ指図から別の林**が出る。
    """
    import hashlib, random
    if not (d["planting"].get("plantRule") or {}).get("seed"):
        raise SystemExit("`planting.plantRule.seed` の宣言が無い — 撒く種の出所が指図に無い")
    key = "%s/%s" % (name, lay)
    return random.Random(int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)), key


def _apportion(vals, tot):
    """実数の列 `vals` を、和が `tot` になる整数へ**最大剰余法**で配る。

    ⛔ 帯ごとに丸めない — 帯ごとに丸めると和が予算表(`plant_budget`)と食い違い、
    「焼いた点の数 = 図が刷った本数」の検査が立たなくなる。
    """
    fl = [int(math.floor(max(0.0, v))) for v in vals]
    rest = tot - sum(fl)
    order = sorted(range(len(vals)), key=lambda i: (-(max(0.0, vals[i]) - fl[i]), i))
    for i in order[:max(0, rest)]:
        fl[i] += 1
    return fl


def _scatter_take(rnd, cells, n, rmin, seeded=()):
    """候補のセル(uv)から **n 点**を決定論的に採る。芯々の下限は `rmin`[間]。

    ⭕ 位置は**セルの中心のまま**(⛔ 揺らぎを足さない)── セルは退避を引いた面の走査結果で、
      中心を外すと退避へはみ出す点が出る(図が測った面と別物になる)。
    ⚠ 採りきれなければ `rmin` を 0.9 倍して採り直す。**緩めた回数は記録に残す**
      (⛔ 黙って詰めない — 密度と芯々が両立しないことは指図の側の欠陥である)。
    戻り (点, 実際の rmin, 緩めた回数)。
    """
    cs = list(cells)
    rnd.shuffle(cs)
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
            gr.setdefault(c, []).append(p)
            out.append(p)
            if len(out) >= n: return out, r, relax
        if len(out) >= n or relax >= 40 or r < 1e-3:
            return out, r, relax
        r *= 0.9
        relax += 1


def _pick_part(rnd, pal):
    """palette の一点を**宣言の重み `w`** で引く。⛔ 重みを発明しない。"""
    tot = sum(q.get("w", 1) for q in pal)
    x = rnd.uniform(0.0, tot)
    for pt in pal:
        x -= pt.get("w", 1)
        if x <= 0.0: return pt
    return pal[-1]


_LAY_KIND = {"松": "matsu", "落葉": "rakuyo", "中木": "chuboku"}


def _variant_under(d, pt, h, kind, xz, rmax):
    """**樹冠の半径が `rmax`[m] 以下の変種**から引く(`clusters[].variantRule`)。

    ⭐ 2026-09-08 十六巡目 C-1(庭方)── 素のまま `sizeRule` に任せると
    『張り出し ≤ 局所の(路肩+側溝) − `marginM`』の条項を割る個体が出る。
    ⛔ 数を持たない ── 上限は局所の道敷幅からの従属値。
    ⚠ 満たす変種が一つも無ければ**最も細い変種**を返す(⛔ 黙って通さない — 検査が名で刷る)。
    戻り (size, prefab, api, scaleY) か None。
    """
    vs = part_variants(d, pt)
    if not vs: return pick_variant(d, pt, h)
    ok = [q for q in vs if q[4] * xz / 2.0 <= rmax]
    src = ok or vs
    pick = max(src, key=lambda q: q[4]) if ok else min(src, key=lambda q: q[4])
    return (pick[0], pick[1], pick[2], (h / pick[3]) if pick[3] else None)


def _xz_capped(d, kind, xz, xzr, h, g0, iso=False):
    """個体の `scaleXZ` を **`scaleRule.scaleXZCapFrom`** で頭打ちにする【指3 庭方 十八巡目】。

    上端 = `crownPerHMax` × **その個体の丈** ÷ **部材の素の樹冠**。
    ⛔ **孤立木(`isolatedXZ` の側)には当てない** ── そもそも `crownPerHMax` の対象外である。
    ⛔ 下限(範囲の下端)は割らない ── 割るなら**部材と丈の組み合わせ**の問題で、検査が名で刷る。
    """
    sr = d["planting"]["scaleRule"]
    if xz is None or iso or not sr.get("scaleXZCapFrom") or not kind: return xz
    cap = (sr.get(kind) or {}).get("crownPerHMax")
    if cap is None or not g0 or not g0[0] or not h: return xz
    lim = cap * h / g0[0]
    lo = xzr[0] if xzr else 0.0
    return max(lo, min(xz, lim))


def _tree_row(d, g, rnd, name, group, lay, pal, hrng, u, v, iso=False, rmax=None):
    """撒いた一本。丈は宣言の範囲から、**大きさ(変種)は `sizeRule` が丈から選ぶ**。

    ⭐ **2026-09-08 十六巡目 B-2(庭方)── `scaleXZ` を点ごとに焼く。**旧式は点が `scaleY`
    しか持たず、**樹冠 = 部材の樹冠 × `scaleXZ`** に乗る三つ(①退避の可否 ②参道への張り出しの
    条項 ③石段の肩の上限)が全部、⛔ **図が測った樹冠と現物の樹冠が別**になる形だった。
    ⛔ `plantRule.scaleJitter` は 2026-09-08 に廃した(裁き3・庭方)── `scaleY` へ二重に掛けると
    箍と樹冠が黙って動く。役『同じ大きさの木を並べない』は丈を範囲から引くことが果たす。
    """
    pt = _pick_part(rnd, pal)
    lo, hi = _h_pair(hrng)
    if lo is None:
        raise SystemExit("『%s』の %s の丈の宣言が無い — 撒けない" % (group, lay))
    h = rnd.uniform(lo, hi)
    cap = species_h_cap(d, pt)               # 樹種ごとの丈の上端(`sizeRule.speciesHCap`)
    if cap is not None: h = min(h, cap)
    kind = _LAY_KIND.get(lay)
    xzr = layer_xz(d, kind, iso) if kind else None
    # ⭐ **点ごとに引く**(⛔ 範囲の中央で代表させない — 図が測るのは個体の樹冠である)
    xz = rnd.uniform(xzr[0], xzr[1]) if xzr else None
    q = (_variant_under(d, pt, h, kind, xz or 1.0, rmax) if (rmax is not None and kind)
         else pick_variant(d, pt, h))
    g0 = part_geom({"prefab": (q[1] if q else pt.get("prefab"))})
    # ⭐ **`scaleXZ` の上端を個体ごとに頭打ちにする**【指3 庭方 2026-09-09 十八巡目】──
    #    `sizeRule` が目標より高い部材を採って丈を Y で縮めた個体(`scaleY` < 1)は、
    #    樹冠 ÷ 丈 が `素の比 × scaleXZ ÷ scaleY` で膨れる。⛔ 上限(`crownPerHMax`)を緩めず、
    #    ⛔ 密度も部材も動かさず、**倍率の側**で収める。⛔ 下限は範囲の下端のまま。
    xz = _xz_capped(d, kind, xz, xzr, h, g0, iso)
    x, z = g.W(u, v)
    dy = _design_y_cold(d, g, x, z)
    nat = dem_h(x, z)
    return {"name": name, "group": group, "layer": lay,
            "species": pt.get("species"), "part": (q[2] if q else pt.get("api")),
            "prefab": (q[1] if q else pt.get("prefab")), "size": (q[0] if q else None),
            "h": round(h, 3), "scaleY": (round(q[3], 4) if q and q[3] else None),
            "scaleXZ": (round(xz, 4) if xz is not None else None),
            "crownM": (round(g0[0] * xz, 3) if (g0 and xz is not None) else None),
            "u": round(u, 4), "v": round(v, 4),
            "world": [round(x, 3), round(z, 3)],
            "y": round(dy if dy is not None else (nat if nat is not None else 0.0), 3),
            "ground": "design" if dy is not None else "terrain",
            "place": (d["planting"]["plantRule"].get("placement") or {}).get(lay)}


def cluster_crown_cap(d, c):
    """`clusters[].variantRule` の**樹冠の半径の上限**[m]。⛔ 数を持たない(局所の道敷幅から)。"""
    if not c.get("variantRule"): return None
    lim = overhang_limit(d, c)
    tl = (d.get("sando", {}).get("roadside") or {}).get("takagiEdgeLine") or {}
    ins = tl.get("insetKen")
    if not lim or ins is None: return None
    return min(q[1] for q in lim) + ins * d["const"]["ken"]


_ZONE_RE = re.compile(r"(南|北)\s*1\s*/\s*(\d+)")


def cluster_zone(c, kind):
    """`mixZone` が樹種 `kind` に切る**v の小領域**(lo, hi)。⛔ v の数を書かない(`vRange` から)。"""
    z = (c.get("mixZone") or {}).get(kind)
    vr = c.get("vRange")
    if not z or not vr: return None
    m = _ZONE_RE.search(z)
    if not m: return None
    f = 1.0 / float(m.group(2))
    v0, v1 = vr
    return (v0, v0 + (v1 - v0) * f) if m.group(1) == "南" else (v1 - (v1 - v0) * f, v1)


def scatter_pts(d, g):
    """**撒いた木の点**。実装(棟梁)はこれをそのまま置く。

    ⛔ 「帯1に松 N 本」と数だけ渡して実装に撒かせない ── 撒き方が実装ごとに変わると、
      指図の検査(退避・樹冠・林縁の張り出し・不変条件)が見ている面と現物が別になる。
    ⭕ 出所はすべて宣言:面 = `band_scan`/`poly_scan`、退避 = `avoid_shapes`、
      本数 = `band_stats`(密度 × 有効面)、芯々 = 帯の `spacing` × `plantRule.packRatio`、
      丈 = 帯の `matsuH`/`rakuyoH`/`chubokuH`/`teibokuH`、種 = `plantRule.seed` の宣言。
    戻り (点の列, 帯ごとの記録, 塊の記録)。
    """
    ken = d["const"]["ken"]
    pal = d["planting"]["parts"]
    pack = d["planting"]["plantRule"]["packRatio"]
    st = band_stats(d, g)
    cells, _skip = band_scan(d, g)
    rows = [r for r in st if "b" in r]
    # ---- 塊(位置を決めて据える物)を先に解く。⛔ 帯の塊は帯の本数の**内訳**なので後で差し引く
    cl_pts, cl_note, cl_cut, rc = [], [], {}, {}
    gapd = []           # 間合い(`gapDiscFrom`)の円 [(u, v, 半径[間], 塊の名)]

    def _in_gap(p, skip=None):
        """間合いの円の中か(⛔ 円を出した塊自身は除く)。"""
        for u9, v9, r9, nm9 in gapd:
            if skip == nm9: continue
            if (p[0] - u9) ** 2 + (p[1] - v9) ** 2 < r9 * r9: return True
        return False

    def rnd_of(name, lay):
        """種は**一つの (名, 層) につき一本**の流れ。⛔ 部材ごとに引き直さない
        (引き直すと同じ並びが繰り返され、丈まで同じ値が出る)。"""
        if (name, lay) not in rc: rc[(name, lay)] = _seed_rnd(d, name, lay)
        return rc[(name, lay)]
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            polys = cluster_polys(c)          # ⭐ 箱でなく**輪郭**(2026-09-08 C-1)
            parts = cluster_parts(d, gd, c)
            sp = cluster_spacing(d, c)
            nm = "%s／%s" % (gd["name"], c["name"])
            if not polys or not parts or sp is None:
                cl_note.append({"name": nm, "n": cluster_n(c), "boxes": cluster_boxes(c),
                                "points": None,
                                "unresolved": ("輪郭が引けない" if not polys else
                                               "芯々(`spacing`/`spacingFrom`)の宣言が無い"
                                               if sp is None else
                                               "`mix`(樹種の割り前)の宣言が無い")})
                continue
            rmin = sp * pack                                # [間]。⛔ 数を作らない
            step = max(rmin / 4.0, 0.05)
            cand0 = [p for Q in polys for p in poly_scan(Q, step)]
            cand = [p for p in cand0 if not _in_gap(p, c["name"])]  # 指1 辻の留めの間合い
            # ⭐ **間合いに食われたら線に沿ってずらす**【指1 庭方 2026-09-09 十八巡目】──
            #    ⛔ **本数を減らして黙らせない。**⛔ ずらす量を json に持たない ── 「その塊の木が
            #    全部、間合いの外に立てる最小の移動」として図が毎回求める。
            #    ⭕ 林縁が辻の手前で切れるのは**留めの木の作法どおり**である。
            slid, seed0 = 0.0, []
            if len(cand) < len(cand0) and c.get("poly"):
                need = int(math.ceil(cluster_n(c) - 1e-9))
                Pq = c["poly"]
                du9 = Pq[1][0] - Pq[0][0]; dv9 = Pq[1][1] - Pq[0][1]
                Ln9 = math.hypot(du9, dv9) or 1.0
                du9, dv9 = du9 / Ln9, dv9 / Ln9
                # ⛔ **向きを決め打ちしない**(⚠ 間合いの芯は線から横へ外れているので、
                #    線に沿った射影だけで『遠ざかる向き』を決めると逆を選ぶ)。
                #    ⭕ **両方向を同じ刻みで試し、先に成り立ったほう**(= 移動が小さいほう)を採る。
                # ⭕ **先に据えた塊の木も避ける**(⛔ 兄弟の塊と融合した位置へ滑らせない)。
                prev9 = [(q["u"], q["v"]) for q in cl_pts]
                # ⭕ **滑らせた先が退避へ載らないことも測る**【低2 検図20巡目 の指摘の射程】──
                #    ⛔ 塊の候補セルは箱の走査だけで作られていて退避を一度も引いていないので、
                #    ⛔ **箱を動かせば黙って社地の外や石段の敷きへ入る**。
                sh9 = avoid_shapes(d, g, "obi4" if gd.get("uv") else
                                   ("obi123:松" if gd.get("band") else "keidai"))
                t9 = 0.0
                while t9 < 8.0 and not slid:
                    t9 += step
                    for sgn9 in (1.0, -1.0):
                        QS = [[(q[0] + du9 * sgn9 * t9, q[1] + dv9 * sgn9 * t9) for q in Q]
                              for Q in polys]
                        cd = [p for Q in QS for p in poly_scan(Q, step)]
                        cd = [p for p in cd if not _in_gap(p, c["name"])
                              and not (sh9 and shape_hit(p, sh9))]
                        # ⛔ **緩めた置き方で『入った』と読まない**(`_scatter_take` は入らないと
                        #    `rmin` を 0.9 倍して採り直す)── 芯々の下限を割ったまま滑らせると、
                        #    ⛔ 幹が二本同じ株から生えて見える。
                        _t9 = _scatter_take(rnd_of(nm, "松")[0], cd, need, rmin, seeded=prev9)
                        if len(_t9[0]) >= need and _t9[2] == 0:
                            polys, cand, slid, seed0 = QS, cd, sgn9 * t9, prev9
                            break
            cap = cluster_crown_cap(d, c)                   # `variantRule` の上限[m]
            iso = bool(c.get("isolatedCrown"))              # 孤立木の樹冠(⛔ 林の形にしない)
            got = []
            # ⛔ **通し番号は塊 × 樹種で一本** ── ⚠ 2026-09-09: palette の点ごとに `i` を
            #   振り直していたので、塊が小さいと**同じ名が二本**出た(『参道の林縁 中 松01』が
            #   二つ)。⛔ 名が衝突すると実装が木を指せず、検査の対も潰れる。
            seq9 = {}
            # ⭐⭐ **線に沿う塊は『撒く』のではなく『弧長を芯々で刻んで据える』**
            #   【A-7 庭方 2026-09-09 十九巡目】── ⛔ `planting.plantRule.packRatio` は
            #   **面へ撒くときの詰まり**であって、一列に据える塊には当たらない。⚠ 掛けたまま
            #   撒いていたので、宣言した芯々 [1.8, 2.4] 間に対し実測は 2.36〜2.92 m で
            #   **5 対すべてが下限を割っていた**(⛔ 検査は鳴っていなかった)。
            #   ⛔ 位置の数を json に持たない ── 平行四辺形の芯線と `spacing` からの従属値。
            line9 = None
            if c.get("alongTakagiEdgeLine") and c.get("poly") and len(c["poly"]) == 4:
                P4 = c["poly"]
                a0 = ((P4[0][0] + P4[3][0]) / 2.0, (P4[0][1] + P4[3][1]) / 2.0)  # 南端の芯
                a1 = ((P4[1][0] + P4[2][0]) / 2.0, (P4[1][1] + P4[2][1]) / 2.0)  # 北端の芯
                L9 = math.hypot(a1[0] - a0[0], a1[1] - a0[1])
                need9 = int(round(cluster_n(c)))
                run9 = (need9 - 1) * sp
                t09 = max(0.0, (L9 - run9) / 2.0)
                ux9 = ((a1[0] - a0[0]) / L9, (a1[1] - a0[1]) / L9) if L9 > 1e-9 else (0.0, 1.0)
                line9 = [(a0[0] + ux9[0] * (t09 + i * sp), a0[1] + ux9[1] * (t09 + i * sp))
                         for i in range(need9)]
                # ⛔ **間合い(辻の留め)の中へ据えない** ── 受入値②『高木の縁の線の s の範囲を
                #   出ないこと』。⚠ 入ってしまう本は据えずに `gapHit` で数える(⛔ 黙って詰めない)。
                gh9 = [p for p in line9 if _in_gap(p, c["name"])]
                if gh9:
                    line9 = [p for p in line9 if not _in_gap(p, c["name"])]
                    cl_note.append({"name": nm, "gapHit": len(gh9),
                                    "runKen": round(run9, 3), "lineKen": round(L9, 3)})
                cl_note.append({"name": nm, "alongLine": True, "spacingKen": sp,
                                "runKen": round(run9, 3), "lineKen": round(L9, 3),
                                "slackKen": round(L9 - run9, 3)})
            for kind, pt, k, hh, _cr, sk, _vs, _lo, _hi in parts:
                lay = "松" if kind == "松" else "落葉"
                rnd, _key = rnd_of(nm, lay)
                if line9 is not None:
                    # ⭕ **`mix` の並びがそのまま南→北の順**(⛔ `mixZone` は当てない)
                    pts, r_, rx = line9[:k], sp, 0
                    line9 = line9[k:]
                else:
                    # ⭐ **樹種を v の小領域へ寄せる**(`mixZone`・2026-09-08 C-1)
                    zn = cluster_zone(c, kind)
                    cz = [p for p in cand if zn[0] <= p[1] <= zn[1]] if zn else cand
                    pts, r_, rx = _scatter_take(rnd, cz, k, rmin, seeded=got + seed0)
                for (u9, v9) in pts:
                    got.append((u9, v9))
                    seq9[kind] = seq9.get(kind, 0) + 1
                    q = _tree_row(d, g, rnd, "%s %s%02d" % (c["name"], kind, seq9[kind]),
                                  nm, lay, [pt], hh, u9, v9, iso=iso, rmax=cap)
                    cl_pts.append(q)
                if len(pts) < k:
                    cl_note.append({"name": nm, "short": k - len(pts)})
            cl_note.append({"name": nm, "n": cluster_n(c), "boxes": cluster_boxes(c),
                            "points": len(got),
                            "rmin": round(sp if line9 is not None else rmin, 3),
                            "slidKen": (round(slid, 3) if slid else None)})
            # ⭐ **間合いを宣言した塊は、据えたあとの幹から円を切る**【指1 庭方 十八巡目】──
            #    ⛔ 帯・ほかの塊の高木の幹をこの円に入れない(⛔ この塊自身は除く)。
            #    ⭕ 役『路の終端を一点でふさぐ』は、隣の塊の頭が寄り添うと成り立たない。
            if c.get("gapDiscFrom"):
                rq = [q for q in cl_pts if q["group"] == nm and q.get("crownM")]
                rr = max((q["crownM"] / 2.0 / ken) for q in rq) if rq else None
                if rr:
                    for (u9, v9) in got:
                        gapd.append((u9, v9, rr, c["name"]))
            if gd.get("band"):                              # 帯の塊 = 帯の本数の内訳
                for kind, _pt, k, _h, _c, _s, _v, _l, _hi in parts:
                    key = (gd["band"], "松" if kind == "松" else "落葉")
                    cl_cut[key] = cl_cut.get(key, 0) + k
    # ⭐ **名指しの木も帯の本数の内訳**【決1③ 庭方 2026-09-09 十八巡目】── 帯の面に立つ以上、
    #    ⛔ 帯の本数に上積みしない(⛔ 密度は動かさない、が決1 の要である)。
    _NT9 = named_tree_rows(d, g)
    for r9 in _NT9:
        if r9.get("band"):
            k9 = (r9["band"], r9.get("layer") or "落葉")
            cl_cut[k9] = cl_cut.get(k9, 0) + 1
    # ---- 帯に撒く。⭐ **層ごとに四帯を一度に引く**(2026-09-08 十六巡目 A-2・庭方)──
    #    旧式は帯ごとに独立で、**帯どうし・帯と塊が互いを知らないまま**撒いており、
    #    芯々の下限を割る対が 229(すべて『別の帯・区どうし』)出た。⛔ 本数の配り方は変えない。
    #    ⭕ 松と落葉は**同じ林冠**なので互いの芯々も守る(一つの `seeded` に積む)。
    n_f, n_rf = {}, {}
    for lay in _LAYS:
        for i, r in enumerate(rows):
            v = (r["takagi"] - r["rakuyo"]) if lay == "松" else \
                r["rakuyo"] if lay == "落葉" else \
                r["chuboku"] if lay == "中木" else r["teiboku"]
            n_f.setdefault(lay, []).append(v)
            # ⭐ **林縁は別の面・別の密度・別の丈**(2026-09-08 A-4/C-2)。高木は 0。
            n_rf.setdefault(lay, []).append(r.get({"中木": "chubokuRinen",
                                                   "低木": "teibokuRinen"}.get(lay), 0.0) or 0.0)
    n_i = dict((lay, _apportion(n_f[lay], int(math.floor(sum(n_f[lay]) + 0.5))))
               for lay in _LAYS)
    n_ir = dict((lay, _apportion(n_rf[lay], int(math.floor(sum(n_rf[lay]) + 0.5))))
                for lay in _LAYS)
    # ⭐ **塊の箱を候補セルから落とす**(2026-09-08 A-3)。⛔ 本数は既に差し引いてあるので
    #    面(`band_stats`)からは落とさない ── ここは**撒く場所**だけを外す。
    keep = cluster_keepout_shapes(d)
    # ⭐ **位置の決まった木を種として渡す**(A-2)── 塊の点と一本立ち。⛔ 帯より先に確定している
    #    ものを知らないまま撒かない(『別の帯・区どうし』が 229 対の全部だった)。
    seeded = {"canopy": [], "中木": [], "低木": []}

    def _bucket(lay): return "canopy" if lay in ("松", "落葉") else lay
    for q in cl_pts:
        seeded.setdefault(_bucket(q["layer"]), []).append((q["u"], q["v"]))
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            seeded.setdefault(_bucket(sg.get("layer") or "松"), []).append(tuple(sg["uv"]))
    # ⭐ **差し掛けの高木も位置が決まっている**(高2 庭方 2026-09-09 十七巡目)
    _SK9 = sashikake_rows(d, g)
    for sk in _SK9:
        seeded.setdefault(_bucket(sk.get("layer") or "落葉"), []).append((sk["u"], sk["v"]))
    # ⭐ **名指しの木も位置が決まっている**(決1③ 庭方 2026-09-09 十八巡目)
    for r9 in _NT9:
        seeded.setdefault(_bucket(r9.get("layer") or "落葉"), []).append((r9["u"], r9["v"]))
    bd_note, out = [], []
    HK = {"松": "matsuH", "落葉": "rakuyoH", "中木": "chubokuH", "低木": "teibokuH"}
    for lay in _LAYS:
        bk = _bucket(lay)
        for i, r in enumerate(rows):
            b = r["b"]
            bn = b["band"]
            if b.get("uv"):
                P = [(q[0], q[1]) for q in b["uv"]]
                step = 0.25
                src = list(poly_scan(P, step))
            else:
                step = d["planting"]["bandDef"]["stepKen"]
                src = list(cells[bn])
            sh = avoid_shapes(d, g, "obi4" if b.get("uv") else ("obi123:" + lay))
            cand = [p for p in src if not (sh and shape_hit(p, sh)) and not shape_hit(p, keep)]
            # ⭐ **間合いは高木にだけ効く**【指1 庭方 2026-09-09 十八巡目】── 測っているのは
            #    『同じ頭が二つ並ばないこと』なので、下層(中木・低木)は入ってよい。
            if lay in ("松", "落葉"): cand = [p for p in cand if not _in_gap(p)]
            # ⭐ **林縁は帯の中の小領域**(A-4)── 高木は本体だけ、中木・低木は両方(別の丈)
            rin = b.get("rinen") or {}
            E = rinen_edges(d, g, b) if rin else []
            cand_t = []
            if rin and E:
                rg = rinen_range(b, lay)          # ⭐ 高木は境から `toKen` まで全部(A-4)
                inr = dict((p, min(_pt_seg(p, q[0], q[1]) for q in E)) for p in cand)
                cand_r = [p for p in cand if rg[0] <= inr[p] <= rg[1]]
                cand = [p for p in cand if p not in set(cand_r)]
                # ⭐ **段ごとの候補**(④ 庭方 2026-09-09 十七巡目)
                for t in rinen_tiers(b):
                    rgt = rinen_range_t(b, t, lay)
                    cand_t.append((t, [p for p in cand_r if rgt[0] <= inr[p] <= rgt[1]]
                                   if rgt else []))
            else:
                cand_r = []
            # ⭐ **芯々の下限は『中央』で揃える**(2026-09-08 裁き4・庭方)。⛔ 高木だけ下端を使わない
            if lay in ("松", "落葉") and b.get("spacing"):
                sp = b["spacing"]
                rmin = (sp[0] + sp[1]) / 2.0 * pack / ken     # 宣言の芯々[m]の中央 × packRatio
            else:
                dens = {"中木": "chubokuPer100", "低木": "teibokuPer100"}.get(lay)
                q = (b.get(dens) or [0, 0]) if dens else [0, 0]
                dm = (q[0] + q[1]) / 2.0
                rmin = (math.sqrt(100.0 / dm) * pack / ken) if dm > 0 else step
            rnd, key = rnd_of("帯%d %s" % (bn, b["name"]), lay)
            n = n_i[lay][i] - cl_cut.get((bn, lay), 0)
            pts, r_, rx = _scatter_take(rnd, cand, max(0, n), rmin, seeded=seeded[bk])
            seeded[bk] += list(pts)
            for j, (u9, v9) in enumerate(pts):
                out.append(_tree_row(d, g, rnd, "帯%d_%s%04d" % (bn, lay, j + 1),
                                     "社叢 帯%d %s" % (bn, b["name"]), lay,
                                     pal[lay], b.get(HK[lay]), u9, v9))
            bd_note.append({"band": bn, "layer": lay, "seed": key, "want": n,
                            "got": len(pts), "cells": len(cand), "step": step,
                            "rmin": round(rmin, 4), "rminUsed": round(r_, 4), "relax": rx})
            # ---- 林縁(同じ層・別の面・**段ごとに別の密度と丈**)
            nr = n_ir[lay][i]
            if nr <= 0 or not cand_r: continue
            # ⭐ **段ごとの本数**は面 × その段の密度。⛔ 合算してから割らない(丸めが動く)。
            want_t = []
            for ti, (t, cs) in enumerate(cand_t):
                dr = rinen_dens_t(d, b, t, lay) or 0.0
                m2 = len(cs) * cell_tsubo(d, step) * TSUBO
                want_t.append(m2 * dr / 100.0)
            if not want_t:
                want_t, cand_t = [float(nr)], [({"name": "一段"}, cand_r)]
            # ⛔ **和を `nr` へ正規化してから配る** ── `_apportion` は最大剰余法なので、
            #   桶より余りが多いと配りきれない(⚠ 2026-09-09: 帯4 の一段へ 3 本のはずが 1 本しか
            #   配られず、焼き出しと予算表が 2 本食い違った)。⛔ 帯ごとの丸めと同じ轍を踏まない。
            tw9 = sum(want_t)
            n_t = _apportion([(w9 / tw9 * nr) if tw9 > 0 else (float(nr) / len(want_t))
                              for w9 in want_t], nr)
            jj = 0
            for ti, (t, cs) in enumerate(cand_t):
                if n_t[ti] <= 0 or not cs: continue
                dr = rinen_dens_t(d, b, t, lay) or 0.0
                rminr = (math.sqrt(100.0 / dr) * pack / ken) if dr > 0 else step
                ptsr, rr_, rxr = _scatter_take(rnd, cs, max(0, n_t[ti]), rminr,
                                               seeded=seeded[bk])
                seeded[bk] += list(ptsr)
                for (u9, v9) in ptsr:
                    jj += 1
                    out.append(_tree_row(d, g, rnd, "帯%d林縁_%s%04d" % (bn, lay, jj),
                                         "社叢 帯%d %s の林縁(%s)"
                                         % (bn, b["name"], t.get("name") or "一段"), lay,
                                         pal[lay], rinen_h_t(d, b, t, lay), u9, v9))
                bd_note.append({"band": bn, "layer": "%s(林縁 %s)" % (lay, t.get("name") or "一段"),
                                "seed": key, "want": n_t[ti], "got": len(ptsr),
                                "cells": len(cs), "step": step, "rmin": round(rminr, 4),
                                "rminUsed": round(rr_, 4), "relax": rxr})
    # ---- 帯の低木の面(区の植込み)と一本立ち ── 位置は指図が持つので**写すだけ**
    for gd in d["gardens"] + d["slopeBands"]:
        if gd.get("shrubs"):
            sh = gd["shrubs"]
            rnd, _k = rnd_of(gd["name"], "低木")
            for j, (u9, v9) in enumerate(island_shrubs(gd, ken)):
                out.append(_tree_row(d, g, rnd, "%s_低木%03d" % (gd["name"], j + 1),
                                     gd["name"], "低木", pal["低木"], sh.get("hM"), u9, v9))
        for sg in gd.get("singles", []):
            u9, v9 = sg["uv"]
            x9, z9 = g.W(u9, v9)
            dy = _design_y_cold(d, g, x9, z9)
            nat = dem_h(x9, z9)
            ln = single_lean(d, sg)
            # ⭐ **一本立ちにも `scaleXZ` を焼く**(2026-09-08 B-2)── 孤立木なので `isolatedXZ`
            _pf = single_prefab(d, sg)
            _kd = _LAY_KIND.get(sg.get("layer") or "")
            _xz = crown_scale_xz(d, _kd, _pf, sg.get("h"), iso=True) if _kd else None
            _cr = single_crown(d, sg)
            out.append({"name": sg["name"], "group": gd["name"] + "(一本立ち)",
                        "layer": sg.get("layer"), "species": sg.get("kind"),
                        "part": sg.get("part"), "prefab": _pf,
                        "size": None, "h": sg.get("h"), "scaleY": None,
                        "scaleXZ": (round(_xz, 4) if _xz is not None else None),
                        "crownM": (round(_cr * 2.0 * ken, 3) if _cr is not None else None),
                        "u": u9, "v": v9, "world": [round(x9, 3), round(z9, 3)],
                        "y": round(dy if dy is not None else (nat or 0.0), 3),
                        "ground": "design" if dy is not None else "terrain",
                        "place": (d["planting"]["plantRule"].get("placement") or {}).get("singles"),
                        "leanDeg": (ln[0] if ln else None),
                        "leanToward": (list(ln[1]) if ln and ln[1] else None),
                        "edaShita": sg.get("edaShita")})
    # ---- 名指しの木(位置は庭方の名指し・据え方は一本立ちと同じ GameObject)
    for r9 in _NT9:
        x9, z9 = g.W(r9["u"], r9["v"])
        dy = _design_y_cold(d, g, x9, z9)
        nat = dem_h(x9, z9)
        out.append({"name": r9["name"],
                    "group": ("★主景(区『%s』)" % r9.get("zone") if r9.get("shukei")
                              else "名指しの木(帯%s)" % r9.get("band")),
                    "layer": r9.get("layer"), "species": r9.get("kind"),
                    "part": r9.get("part"), "prefab": r9.get("prefab"),
                    "size": r9.get("size"), "h": r9.get("h"), "scaleY": r9.get("scaleY"),
                    "scaleXZ": r9.get("scaleXZ"), "crownM": r9.get("crownM"),
                    "u": r9["u"], "v": r9["v"],
                    "world": [round(x9, 3), round(z9, 3)],
                    "y": round(dy if dy is not None else (nat or 0.0), 3),
                    "ground": "design" if dy is not None else "terrain",
                    "place": (d["planting"]["plantRule"].get("placement") or {}).get("singles")})
    # ---- 差し掛けの高木(位置は宣言からの従属値・据え方は一本立ちと同じ GameObject)
    for sk in _SK9:
        x9, z9 = g.W(sk["u"], sk["v"])
        dy = _design_y_cold(d, g, x9, z9)
        nat = dem_h(x9, z9)
        g0 = part_geom({"prefab": sk.get("prefab")})
        xz = sk.get("scaleXZ")
        out.append({"name": sk["name"], "group": "差し掛け(%s)" % sk["of"],
                    "layer": sk.get("layer"), "species": sk.get("kind"),
                    "part": sk.get("part"), "prefab": sk.get("prefab"),
                    "size": sk.get("size"), "h": sk.get("h"), "scaleY": sk.get("scaleY"),
                    "scaleXZ": xz,
                    "crownM": (round(g0[0] * xz, 3) if (g0 and xz) else None),
                    "u": sk["u"], "v": sk["v"],
                    "world": [round(x9, 3), round(z9, 3)],
                    "y": round(dy if dy is not None else (nat or 0.0), 3),
                    "ground": "design" if dy is not None else "terrain",
                    "place": (d["planting"]["plantRule"].get("placement") or {}).get("singles"),
                    "kaidan": sk.get("kaidan"), "sM": sk.get("sM"), "side": sk.get("side")})
    return out + cl_pts, bd_note, cl_note


def sashikake_offset(d, sk, k):
    """差し掛けの**芯からの離れ**[間]。⛔ 数を持たない【決2① 庭方 2026-09-09 十八巡目】。

    = `kaidans[].wKen`/2 + `planting.bandDef.avoid.kaidanShoulderKen`[その層] の従属値。
    ⚠ 幹は敷きの縁から肩のぶんだけ退く = 擁壁の物理(肩の由来)そのもの。
    """
    if sk.get("offsetKen") is not None: return float(sk["offsetKen"])
    shk = ((d["planting"]["bandDef"].get("avoid") or {}).get("kaidanShoulderKen") or {})
    sh = shk.get(sk.get("layer"))
    if sh is None:
        raise SystemExit("差し掛け『%s』の肩(`kaidanShoulderKen`[%s])が引けない"
                         % (sk.get("name"), sk.get("layer")))
    return kaidan_wken(d, k) / 2.0 + float(sh)


def sashikake_xz(d, sk):
    """差し掛けの `scaleXZ`。⭕ **林縁木なので `scaleRule.isolatedXZ`**【決2② 庭方 十八巡目】。"""
    if sk.get("scaleXZFrom"):
        return d["planting"]["scaleRule"].get("isolatedXZ")
    return sk.get("scaleXZ")


def sashikake_rows(d, g):
    """**差し掛けの高木**(`planting.sashikake`)の据え所を組み立てる。

    ⭐ **位置は宣言からの従属値**【高2 庭方 2026-09-09 十七巡目】── 石段の折れ線の**弧長**を
      `n`+1 等分した内側 `n` 点で、芯から `offsetFrom`(敷きの半幅 + 肩)の法線上、
      **南(進行方向の右)のみ**【決2 庭方 2026-09-09 十八巡目】。
      ⛔ 弧長の数も座標も json に書かない(坂の折れ線が動けば追随する)。
    ⚠ **帯の密度からは出ない** ── 帯は面で撒くので、坂の脇という細い線には確率的にしか
      当たらない(実測 女坂の芯線 55 点中 樹冠に覆われるのは 3 点)。
    戻り [{name, kaidan, u, v, layer, kind, h, scaleXZ, part, prefab, side, sM}]。
    """
    out = []
    for sk in d["planting"].get("sashikake", []):
        k = ([q for q in d["kaidans"] if q["name"] == sk["kaidan"]] or [None])[0]
        if k is None: continue
        P = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        ken = d["const"]["ken"]
        L = [0.0]
        for i in range(len(P) - 1):
            L.append(L[-1] + math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) * ken)
        tot = L[-1]
        n = int(sk["n"])
        # 樹種の割り前(`mix`)を順に配る。⛔ 本数を別に持たない
        sp9 = []
        for kind, cnt in cluster_mix(sk):
            sp9 += [_MIXSP.get(kind, kind)] * int(cnt)
        pal = d["planting"]["parts"].get(sk["layer"]) or []
        for j in range(1, n + 1):
            s9 = tot * j / float(n + 1)
            seg = None
            for i in range(len(P) - 1):
                if L[i] <= s9 <= L[i + 1] + 1e-9: seg = i; break
            if seg is None: continue
            t9 = (s9 - L[seg]) / ((L[seg + 1] - L[seg]) or 1.0)
            u9 = P[seg][0] + (P[seg + 1][0] - P[seg][0]) * t9
            v9 = P[seg][1] + (P[seg + 1][1] - P[seg][1]) * t9
            du, dv = P[seg + 1][0] - P[seg][0], P[seg + 1][1] - P[seg][1]
            nn = math.hypot(du, dv) or 1.0
            nx9, nz9 = -dv / nn, du / nn                  # 法線(向きは次の行で南北へ揃える)
            # ⭐ **南のみ**【決2③ 庭方 2026-09-09 十八巡目 ── 十七巡目の『片側に寄せない』は
            #    撤回】。北隣は男坂の額縁で、交互にすると偶数番が `viewClusters` へ食い込む。
            # ⛔ **『進行方向の右』で決めない** ── 折れ線の向きが変われば右も変わる。
            #    ⭕ **南は v が小さくなる側**として法線そのものから決める(⛔ 符号を決め打ちしない)。
            #    ⚠ 旧式は左法線を『v が増える側 = 北』と決め打ちしており、⛔ **この坂では逆**で
            #    あった(据え位置が庭方の宣言した表と 2 × 離れ だけ食い違い、北側の額縁へ
            #    食い込んでいた)。
            s_south = -1.0 if nz9 > 0 else 1.0
            sgn = s_south if "南" in (sk.get("sides") or "") else -s_south
            if "交互" in (sk.get("sides") or ""):
                sgn = s_south if (j % 2) == 1 else -s_south
            sp = sp9[(j - 1) % len(sp9)] if sp9 else None
            cand = [pt for pt in pal if pt.get("species") == sp] or pal
            pt = cand[(j - 1) % len(cand)] if cand else None
            lo, hi = _h_pair(sk.get("h"))
            h9 = lo + (hi - lo) * ((j - 1) / float(max(1, n - 1))) if lo is not None else None
            q = pick_variant(d, pt, h9) if (pt and h9) else None
            off9 = sashikake_offset(d, sk, k)
            out.append({"name": "%s %02d" % (sk["name"], j), "of": sk["name"],
                        "kaidan": sk["kaidan"], "sM": round(s9, 3),
                        "side": ("南" if sgn * nz9 < 0 else "北"),
                        "u": round(u9 + nx9 * off9 * sgn, 4),
                        "v": round(v9 + nz9 * off9 * sgn, 4),
                        "layer": sk["layer"], "kind": sp, "h": (round(h9, 3) if h9 else None),
                        "scaleXZ": sashikake_xz(d, sk),
                        "part": (q[2] if q else (pt or {}).get("api")),
                        "prefab": (q[1] if q else (pt or {}).get("prefab")),
                        "size": (q[0] if q else None),
                        "scaleY": (round(q[3], 4) if q and q[3] else None)})
    return out


def band_at(d, g, u, v):
    """点 (u,v) が落ちる**帯**を同定する【決1③ 庭方 2026-09-09 十八巡目】。

    ⛔ **帯の番号を json に書かせない**ための一本 ── 名指しの木の丈は『その木が落ちる帯の
      `rakuyoH` の上端』という従属値なので、帯の同定は図の仕事である。
    ⭕ 帯4 は多角形、帯1〜3 は `band_scan` が刻んだセルの**最寄り**で決める。
    """
    b4 = d["slopeBands"][3]
    if b4.get("uv") and in_poly((u, v), [(q[0], q[1]) for q in b4["uv"]]): return b4
    cells, _sk = band_scan(d, g)
    step = d["planting"]["bandDef"]["stepKen"]
    best, bb = None, None
    for bn, ps in cells.items():
        for p in ps:
            dd = (p[0] - u) ** 2 + (p[1] - v) ** 2
            if best is None or dd < best: best, bb = dd, bn
            if dd <= (step * 0.75) ** 2: return [q for q in d["slopeBands"] if q["band"] == bn][0]
    if bb is None: return None
    return [q for q in d["slopeBands"] if q["band"] == bb][0]


def shukei_named(d):
    """**★主景の木を『名指しの木』として引く**【A-1 庭方 2026-09-09 十九巡目】。

    ⛔⛔ **区の塊の一本として撒くと、区の丈の範囲(`hBand` の `rakuyoH` / `matsuHMaxFrom`)が
      掛かって `shukei.tree.hMinFrom` を切り落とす。**⚠ 実測で丈は宣言より 4.22 m 低く、
      位置は名指しの点から 8.20 m 離れ、V3 からの仰角は西Aの木でいちばん低かった ──
      ⛔ **『★主景の検算』は宣言から計算した紙の上の数で、棟梁が読む焼き出しに対応物が無かった。**
    ⭕ 戻りは `planting.namedTrees.trees[]` と同じ形(`hMinFrom` を持つ点だけが違う)。
    """
    out = []
    for gd in d["gardens"]:
        sk = gd.get("shukei")
        if not sk or not sk.get("tree"): continue
        t = dict(sk["tree"])
        t["zone"] = t.get("zone") or gd["name"]
        out.append(t)
    return out


def named_tree_rows(d, g):
    """**名指しの木**(`planting.namedTrees` と ★主景)の据え所【決1③ 庭方 十八巡目 / A-1 十九巡目】。

    ⛔ 位置は庭方が名指しした (u,v) そのもの(意匠)。⭕ **丈・部材・樹冠は従属値** ──
      丈は `hFrom`(その木が落ちる帯の `rakuyoH` の上端)か `hMinFrom`(★主景 ── 落葉の
      最も高い変種の素の丈 × 箍)、大きさは `sizeRule` が丈から選ぶ。
    ⛔ 帯の番号も丈の数も json に書かない。
    """
    nt = ((d["planting"].get("namedTrees") or {}).get("trees") or []) + shukei_named(d)
    out = []
    for t in nt:
        u9, v9 = t["uv"]
        lay = t.get("layer") or "落葉"
        hk = {"松": "matsuH", "落葉": "rakuyoH", "中木": "chubokuH", "低木": "teibokuH"}[lay]
        if t.get("hMinFrom"):
            # ⭐ ★主景 ── **丈は帯からではなく `hMinFrom` から**(⛔ 区の丈の範囲を掛けない)
            b = None
            h9 = shukei_hmin(d, {"tree": t})
        else:
            b = band_at(d, g, u9, v9)
            rng = (b or {}).get(hk)
            h9 = _h_pair(rng)[1] if rng else None
        pal = [q for q in (d["planting"]["parts"].get(lay) or [])
               if q.get("species") == t.get("kind")]
        pt = pal[0] if pal else None
        if h9 is not None and pt is not None:
            cap = species_h_cap(d, pt)
            if cap is not None: h9 = min(h9, cap)
        q = pick_variant(d, pt, h9) if (pt and h9) else None
        kind = _LAY_KIND.get(lay)
        xz = (d["planting"]["scaleRule"].get("isolatedXZ")
              if t.get("scaleXZFrom") else None)
        g0 = part_geom({"prefab": (q[1] if q else (pt or {}).get("prefab"))})
        out.append({"name": t["name"], "of": ("★主景" if t.get("hMinFrom") else "名指しの木"),
                    "shukei": bool(t.get("hMinFrom")),
                    "zone": t.get("zone"), "band": (b or {}).get("band"),
                    "hSrc": ("`hMinFrom`(落葉の最も高い変種の素の丈 × 箍)"
                             if t.get("hMinFrom") else "帯の `rakuyoH` の上端"),
                    "u": u9, "v": v9, "layer": lay, "kind": t.get("kind"),
                    "h": (round(h9, 3) if h9 else None), "scaleXZ": xz,
                    "part": (q[2] if q else (pt or {}).get("api")),
                    "prefab": (q[1] if q else (pt or {}).get("prefab")),
                    "size": (q[0] if q else None),
                    "scaleY": (round(q[3], 4) if q and q[3] else None),
                    "crownM": (round(g0[0] * xz, 3) if (g0 and xz) else None),
                    "role": t.get("role")})
    return out


def named_tree_check(d, g):
    """**名指しの木が宣言どおり引けているか**【決1③ 庭方 2026-09-09 十八巡目・規則19】。

    ⛔ 帯が同定できない / 丈が引けない / 部材が palette に無い ── どれも**黙らせない**。
    ⭐ **★主景の木もこの名簿に載る**【A-1 庭方 2026-09-09 十九巡目】── ⛔ 帯には落ちない
      (区の中に立つ)ので、帯の同定は求めない。代わりに**丈の出所が `hMinFrom` であること**を測る。
    """
    nt = (d["planting"].get("namedTrees") or {}).get("trees") or []
    if not nt: return ([], ["`planting.namedTrees` の宣言が無い【算出】"])
    bad, note = [], []
    for r in named_tree_rows(d, g):
        if r["band"] is None and not r.get("shukei"):
            bad.append("名指しの木『%s』が落ちる**帯を同定できない** — 丈(`hFrom`)が引けない"
                       "(⛔ 0 件は合格ではなく未測定・規則19)" % r["name"]); continue
        if r["h"] is None or not r["prefab"]:
            bad.append("名指しの木『%s』の丈か部材が引けない(帯%s ／ 樹種 %s)"
                       % (r["name"], r["band"], r["kind"])); continue
        note.append("名指しの木『%s』── %s ／ %s ／ 丈 **%.2f m**(%s)／ "
                    "部材 `%s` ／ 樹冠 **%.2f m**(`isolatedXZ`)／ 役『%s』"
                    "【算出 — ⛔ 丈も帯の番号も json に書かない(決1③ 庭方 2026-09-09)】"
                    % (r["name"],
                       ("区『%s』" % r["zone"]) if r.get("shukei") else ("帯%s" % r["band"]),
                       r["kind"], r["h"], r["hSrc"], r["prefab"],
                       r["crownM"] or 0.0, r.get("role") or "—"))
    return bad, note


def shukei_bake_check(d, g):
    """**★主景の木が焼き出しに在り、受入値(仰角)を満たすか**【A-1 庭方 2026-09-09 十九巡目】。

    ⛔⛔ **宣言だけがあって焼き出しに対応物が無い設計値を残さない**(規則19)── ⚠ 旧図は
      ★主景を区の塊『西A』の `mix` の一本として撒いており、⛔ **区の丈の範囲が `hMinFrom` を
      切り落として**、焼き出しには宣言より 4.22 m 低い木が 8.20 m ずれた所に立っていた。
    ① 名指しの木として引けているか(丈が `hMinFrom` から出ているか)。
    ② **焼き出し(`sanno_impl.json`)にその名の木が在り**、位置と丈が図の算出と一致するか。
    ③ **受入値**(`shukei.acceptFrom`)── V3 から見た仰角が `munes` の各棟を越えるか。
    """
    bad, note = [], []
    rows = [r for r in named_tree_rows(d, g) if r.get("shukei")]
    if not rows:
        return (["★主景の木が**名指しの木として引けない** — `gardens[].shukei.tree` の宣言が"
                 "欠けているか、丈(`hMinFrom`)が引けない(⛔ 0 件は合格ではなく未測定)"], [])
    for r in rows:
        # ① 丈の出所
        if not r.get("hSrc", "").startswith("`hMinFrom`"):
            bad.append("★主景の木『%s』の丈が `hMinFrom` から出ていない — "
                       "⛔ 区の丈の範囲を掛けると宣言が黙って切り落とされる" % r["name"])
        # ② 焼き出しに在るか
        if not os.path.exists(IMPL_OUT):
            note.append("★主景の木『%s』── 焼き出しがまだ無いので照合は**未測定**"
                        "(⛔ 合格ではない)" % r["name"])
        else:
            im = json.load(open(IMPL_OUT, encoding="utf-8"))
            P9 = (im.get("planting") or {}).get("points") or []
            hit = [q for q in P9 if q.get("name") == r["name"]]
            if not hit:
                bad.append("★主景の木『%s』が**焼き出しに無い** — ⛔ 図の『★主景の検算』は"
                           "宣言から計算した紙の上の数になり、棟梁が読む `sanno_impl.json` には"
                           "対応物が無い(A-1 庭方 2026-09-09 十九巡目)" % r["name"])
            else:
                q9 = hit[0]
                du = math.hypot(q9["u"] - r["u"], q9["v"] - r["v"]) * d["const"]["ken"]
                dh = abs((q9.get("h") or 0.0) - (r["h"] or 0.0))
                if du > 1e-6 or dh > 1e-6:
                    bad.append("★主景の木『%s』の焼き出しが図の算出と食い違う — "
                               "位置の差 %.3f m ／ 丈の差 %.3f m" % (r["name"], du, dh))
                else:
                    note.append("★主景の木『%s』── 焼き出しに在り、位置も丈も図の算出と一致"
                                "(丈 **%.2f m** ／ 樹冠 **%.2f m** ／ 部材 `%s`)【算出】"
                                % (r["name"], r["h"], r["crownM"] or 0.0, r["prefab"]))
    # ③ 受入値 ── V3 から見た仰角が棟を越えるか
    for gd in d["gardens"]:
        sk = gd.get("shukei")
        if not sk: continue
        if not sk.get("acceptFrom"):
            bad.append("★主景に**受入値(`acceptFrom`)の宣言が無い** — ⚠ 旧図はこの比較を"
                       "表に ⭕/⚠ で刷るだけで、割っても組み上がった(⛔ 0 件は合格ではなく未測定)")
            continue
        R = shukei_rows(d, g)
        if not R or R[0][3] is None:
            bad.append("★主景の仰角が引けない — 受入値を測れない"); continue
        ang0 = R[0][3]
        for nm9, _L, _top, ang9 in R[1:]:
            if ang9 is None:
                bad.append("★主景の受入値 ── 『%s』の棟の仰角が引けない(棟高が無い)" % nm9)
                continue
            if ang0 <= ang9:
                bad.append("★主景の受入値を割る ── 主景の仰角 **%.2f°** が『%s』の頂 %.2f° を"
                           "**越えない**(差 %+.2f°)。⛔ 梢が棟に隠れて背景が立たない"
                           % (ang0, nm9, ang9, ang0 - ang9))
            else:
                note.append("★主景の受入値 ⭕ ── 主景 **%.2f°** > 『%s』の頂 %.2f°"
                            "(差 **%+.2f°**)【算出 — ⛔ 数を json にも文章にも写さない】"
                            % (ang0, nm9, ang9, ang0 - ang9))
    return bad, note


def kyoukai_inside_check(d, g):
    """**設計された塊と名指しの木の幹が社地 `polygon` の内にあるか**(符号つき・全数)
    【A-2 庭方 2026-09-09 十九巡目・`plantRule.kyoukaiInsideRule`】。

    ⛔⛔ **`bandDef.avoid.kyoukaiRule` では捕まらない** ── あちらは**符号の無い距離**なので、
      境から外へ 1.95 m 出ていても『1.818 m 以上離れている』を満たして通る。
    ⚠ 実測で高木 3 本(いずれも『参道の林縁 北』)が社地の外・**麓の辻の道の上**に立っていた。
    ⭕ **撒き木も数える**(帯の多角形が定義域なので受入値の対象外だが、⛔ 0 件を『測っていない』
      と混ぜない・規則19)。
    """
    rule = (d["planting"].get("plantRule") or {}).get("kyoukaiInsideRule")
    if not rule:
        return (["`planting.plantRule.kyoukaiInsideRule`(幹が社地の内にあること)の宣言が無い — "
                 "⛔ 符号の無い距離だけでは**社地の外に立つ木**を捕まえられない(A-2 庭方)"], [])
    if not os.path.exists(IMPL_OUT):
        return ([], ["社地の内外 ── 焼き出しがまだ無いので**未測定**(⛔ 合格ではない)"])
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    P9 = (im.get("planting") or {}).get("points") or []
    if not P9:
        return (["社地の内外 ── 焼き出しの木が 0 本(⛔ 0 件は合格ではなく未測定)"], [])
    SP = [(g.U(x), g.V(z)) for x, z in d["polygon"]]
    ken = d["const"]["ken"]

    def outm(q):
        p = (q["u"], q["v"])
        if in_poly(p, SP): return 0.0
        return min(_pt_seg(p, SP[i], SP[(i + 1) % len(SP)])
                   for i in range(len(SP))) * ken
    own = set()
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []): own.add("%s／%s" % (gd["name"], c["name"]))
    tgt = [q for q in P9 if (q.get("group") in own) or is_named_group(q.get("group"))]
    oth = [q for q in P9 if q not in tgt]
    bad, note = [], []
    ov = [(outm(q), q) for q in tgt]
    ov = [(m, q) for m, q in ov if m > 1e-9]
    if ov:
        bad.append("**幹が社地 `polygon` の外にある %d 本**(設計された塊・名指しの木の全数 %d 本中)"
                   " ── %s。⛔ 符号つきで測る(`bandDef.avoid.kyoukaiRule` の距離は符号を持たない"
                   "ので、外へ出ていても『離れている』を満たして通る)"
                   % (len(ov), len(tgt),
                      "・".join("%s %.2f m 外" % (q["name"], m)
                                for m, q in sorted(ov, reverse=True)[:6])))
    else:
        note.append("社地の内外(符号つき)── 設計された塊・名指しの木 **%d 本すべてが社地の内**"
                    "【算出 — 受入値 `plantRule.kyoukaiInsideRule`(A-2 庭方 2026-09-09)】" % len(tgt))
    o2 = [(outm(q), q) for q in oth]
    o2 = [(m, q) for m, q in o2 if m > 1e-9]
    note.append("⚠ **撒き木(帯の密度から出る木)は受入値の対象外** ── %d 本中 社地の外 %d 本"
                "%s【算出 — ⛔ 対象外を『合格』と読まない。⛔ 数を出さないと『測っていない』と"
                "区別が付かない(規則19)】"
                % (len(oth), len(o2),
                   ("(最遠 %.2f m ── %s)" % (max(m for m, _q in o2),
                                              max(o2)[1]["name"])) if o2 else ""))
    return bad, note


def named_vs_cluster_check(d, g):
    """**名指しの木が設計された塊の余白に入らないか**【A-3 庭方 2026-09-09 十九巡目】。

    ⭐ **格は ⛔**。⭕ 格の根拠 ── 額縁の役『麓から男坂と仁王門を見せる』は
      【S [名所図会・山王]】で、当図の植栽で**いちばん典拠の格が高い受入値**である。
      ⛔ **同じ箱を撒き木には⛔・名指しの木には⚠ にしてはいけない**(撒き木は既に
      `bandDef.avoid.clusterRule` で同じ余白を⛔で守っており、しかも名指しの木は
      `isolatedCrown` で樹冠が大きい)。
    ⭕ **物差しは箱の輪郭 + その塊の芯々 × `packRatio`・測るのは幹の芯**
      = `bandDef.avoid.clusterRule` と**同一の式**(⛔ 二つ目の余白の数を作らない)。
      ⛔ **樹冠では測らない。**
    ⭕ **適用範囲はすべての設計された塊 × すべての名指しの木**
      (`sashikake` / `namedTrees` / `gardens[].singles` / `slopeBands[].singles` / ★主景)。
      ⛔ 『男坂の見切り』だけを名簿にしない。
    ⚠ **例外は `withinCluster` を宣言した木だけ**(★主景は塊の中に立つことが役)。
    ⛔ **設計の側で測る**(⛔ 焼き出しの写しを測らない)── 位置は宣言からの従属値なので、
      ここで測れば**焼き出しを回さずに毎回検べられる**(破壊試験が同じ式を叩ける)。
    """
    rule = (d["planting"].get("plantRule") or {}).get("namedVsClusterRule")
    if not rule:
        return (["`planting.plantRule.namedVsClusterRule`(名指しの木と塊の余白)の宣言が無い — "
                 "⛔ 宣言の無い縛りは必ず破られる(A-3 庭方 2026-09-09 十九巡目・規則19)"], [])
    ken = d["const"]["ken"]
    shp = cluster_keepout_shapes(d)
    exempt = set()
    pts = []
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []):
            if sg.get("uv"): pts.append((sg["name"], tuple(sg["uv"])))
    for sk in sashikake_rows(d, g):
        pts.append((sk["name"], (sk["u"], sk["v"])))
    for r9 in named_tree_rows(d, g):
        pts.append((r9["name"], (r9["u"], r9["v"])))
    for gd in d["gardens"]:
        t9 = (gd.get("shukei") or {}).get("tree") or {}
        if t9.get("withinCluster"): exempt.add(t9.get("name"))
    bad, note = [], []
    hit = [(nm, shape_hit(p, shp)) for nm, p in pts if nm not in exempt]
    hit = [q for q in hit if q[1]]
    if not shp:
        bad.append("設計された塊の余白の面が**一つも組めない** — ⛔ 面が空なら違反 0 は"
                   "『合格』ではなく**未測定**(規則19)")
    elif hit:
        bad.append("**名指しの木が設計された塊の余白に入る %d 本** ── %s。"
                   "⛔ 物差しは『箱の輪郭 + その塊の芯々 × `packRatio`・幹の芯』"
                   "(= `bandDef.avoid.clusterRule` と同一の式)。⛔ 樹冠では測らない。"
                   "⛔ 余白を緩めて黙らせない(A-3 庭方 2026-09-09 十九巡目)"
                   % (len(hit), "・".join("『%s』→ %s" % q for q in sorted(hit))))
    else:
        note.append("名指しの木 × 設計された塊の余白 ── **0 本**(測った名指しの木 %d 本 × "
                    "塊の面 %d ／ 例外 `withinCluster` %d 本)【算出 — 受入値は A-3 庭方 "
                    "2026-09-09 十九巡目。⛔ 物差しは `clusterRule` と同一。⛔ 樹冠では測らない】"
                    % (len(pts) - len(exempt), len(shp), len(exempt)))
    for w9 in sorted(exempt):
        note.append("⚠ **『%s』は `withinCluster` を宣言しているので余白の対象外** ── 庭方が"
                    "『塊の中に一本入れ、位置を固定する』と決めた木である"
                    "【A-1/A-3 の交点。⛔ 黙って外さない → `_pending`「名指しの木と設計された"
                    "塊の取り合い」】" % w9)
    return bad, note


def cluster_place_bake_check(d, g):
    """**設計した塊が焼き出しで宣言どおり据わったか**【A-2②/A-7 庭方 2026-09-09 十九巡目】。

    ⛔⛔ **旧図は `short`(据えきれなかった本数)を `cl_note` に積むだけで誰も読んでいなかった**
      ── 宣言した本数が立たなくても図は組み上がった(規則19)。
    ① 据えきれなかった本(`short`)・輪郭が解けない塊(`unresolved`)は⛔。
    ② **線に沿う塊**は『高木の縁の線の s の範囲を出ないこと』(A-2 受入値②)── 辻の留めの
       間合いに掛かって据えられなかった本(`gapHit`)は⛔。
    ③ **隣り合う幹の芯々が宣言の範囲(`groupSpacingKen`)に入るか**(⛔ `packRatio` は掛けない)。
    """
    if not os.path.exists(IMPL_OUT):
        return ([], ["塊の据わり ── 焼き出しがまだ無いので**未測定**(⛔ 合格ではない)"])
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    CL = (im.get("planting") or {}).get("clusters") or []
    P9 = (im.get("planting") or {}).get("points") or []
    ken = d["const"]["ken"]
    bad, note = [], []
    for r in CL:
        if r.get("short"):
            bad.append("塊『%s』── 宣言した本数のうち **%d 本が据えられなかった**"
                       "(⛔ 本数を減らして黙らせない・規則19)" % (r["name"], r["short"]))
        if r.get("unresolved"):
            bad.append("塊『%s』── **%s**(⛔ 輪郭が解けない塊を図に残さない)"
                       % (r["name"], r["unresolved"]))
        if r.get("gapHit"):
            bad.append("塊『%s』── **%d 本が『辻の留めの間合い』の中に落ちて据えられない** — "
                       "⛔ 受入値②『高木の縁の線の s の範囲を出ないこと』を割る(A-2 庭方)。"
                       "⛔ 間合いを緩めない ── `vRange` を縮めるか本数を庭方が決め直す"
                       % (r["name"], r["gapHit"]))
        if r.get("alongLine"):
            note.append("塊『%s』(線に沿う)── 芯々 **%.2f 間 = %.2f m**(⛔ `packRatio` を"
                        "掛けない)／ 要る走り %.2f 間 ／ 線の長さ %.2f 間 ／ **余り %+.2f 間**"
                        "【算出 — A-7 庭方 2026-09-09。⛔ 位置も余りも json に持たない】"
                        % (r["name"], r["spacingKen"], r["spacingKen"] * ken,
                           r["runKen"], r["lineKen"], r["slackKen"]))
    # ②' ⭐ **受入値②『高木の縁の線の s の範囲を出ないこと』を焼き出しで測る**
    #    【A-2 庭方 2026-09-09 十九巡目】── ⛔ `gapHit`(据えられなかった本)が 0 でも、
    #    ⛔ **測っていないのと区別が付かない**。⭕ 留めの木の間合いと実際の芯々を毎回刷る。
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            if not c.get("gapDiscFrom"): continue
            nm9 = "%s／%s" % (gd["name"], c["name"])
            src = [q for q in P9 if q.get("group") == nm9]
            if not src: continue
            rr = max((q.get("crownM") or 0.0) / 2.0 for q in src) / ken
            oth = [q for q in P9 if q.get("group") != nm9 and q.get("layer") in ("松", "落葉")]
            ds = [(math.hypot(a9["u"] - b9["u"], a9["v"] - b9["v"]), a9["name"], b9["name"])
                  for a9 in src for b9 in oth]
            if not ds: continue
            m9 = min(ds)
            if m9[0] < rr - 1e-6:
                bad.append("塊『%s』の間合い(`gapDiscFrom` %.2f 間 = %.2f m)の中に、ほかの高木の"
                           "幹がある ── 最短 %.2f 間(『%s』×『%s』)。⛔ 間合いを緩めない"
                           % (c["name"], rr, rr * ken, m9[0], m9[1], m9[2]))
            else:
                note.append("塊『%s』の間合い ⭕ ── 半径 **%.2f 間 = %.2f m**(`gapDiscFrom`)に対し、"
                            "ほかの高木の幹の最短 **%.2f 間 = %.2f m**(『%s』×『%s』)／ "
                            "測った相手 %d 本【算出 — A-2 受入値② 庭方 2026-09-09 十九巡目。"
                            "⛔ 数を json に持たない(樹冠が動けば間合いも動く)】"
                            % (c["name"], rr, rr * ken, m9[0], m9[0] * ken, m9[1], m9[2], len(oth)))
    # ③ 焼き出しの隣り合う幹の芯々 vs 宣言の範囲
    decl = {}
    for gd in d["gardens"] + d["slopeBands"]:
        for c in gd.get("clusters", []):
            rng = c.get("_spacingRangeKen")
            if rng and c.get("alongTakagiEdgeLine"):
                decl["%s／%s" % (gd["name"], c["name"])] = rng
    for nm, rng in sorted(decl.items()):
        ps = sorted([q for q in P9 if q.get("group") == nm], key=lambda q: q["v"])
        if len(ps) < 2:
            note.append("塊『%s』── 焼き出しが %d 本なので隣どうしの芯々は測らない【算出】"
                        % (nm, len(ps)))
            continue
        ds = [math.hypot(ps[i + 1]["u"] - ps[i]["u"], ps[i + 1]["v"] - ps[i]["v"])
              for i in range(len(ps) - 1)]
        lo, hi = min(ds), max(ds)
        # ⛔ **丸めの幅**(⛔ 設計値ではない)── 焼き出しの (u,v) は小数4桁で丸めてあるので、
        #    ⛔ 1e-6 で当てると**宣言ちょうどに据えた塊**が『範囲の外』に化ける。
        _TOL9 = 1e-3
        if lo < rng[0] - _TOL9 or hi > rng[1] + _TOL9:
            bad.append("塊『%s』── 焼き出しの隣どうしの芯々 **%.3f〜%.3f 間** が宣言 "
                       "[%g, %g] 間 の外へ出る(⛔ `packRatio` は面へ撒くときの詰まりで、"
                       "一列に据える塊には当たらない・A-7 庭方 2026-09-09)"
                       % (nm, lo, hi, rng[0], rng[1]))
        else:
            note.append("塊『%s』── 焼き出しの隣どうしの芯々 **%.3f〜%.3f 間 = %.2f〜%.2f m**"
                        "(宣言 [%g, %g] 間・⛔ `packRatio` を掛けない)【算出 — A-7 庭方】"
                        % (nm, lo, hi, lo * ken, hi * ken, rng[0], rng[1]))
    return bad, note


def crown_cover(d, g, pts_uv, layers=None, step=0.5, within=False):
    """折れ線(uv)の芯線を `step`[m] 刻みに歩き、**焼き出しの木の樹冠に入る点の割合**[%]。

    ⛔ 樹冠は焼き出しの `crownM`(= 部材の樹冠 × `scaleXZ`)そのもの — ⛔ 図が別に組み立てない。
    ⭐ 測る層は宣言(`crownCover[].layers`)。⛔ 低木は数に入れない(道を覆うのではなく塞ぐ)。
    ⭐ `within=True` なら**社地 `polygon` の内側の区間だけ**を測る【決1① 庭方 十八巡目】。
    戻り (割合[%], 測った点, 覆われた点, **最長の空白**[m], 社地の外の延長[m])。
    """
    if not os.path.exists(IMPL_OUT): return (None, 0, 0, None, None)
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    T = [(q["world"][0], q["world"][1], (q.get("crownM") or 0.0) / 2.0)
         for q in ((im.get("planting") or {}).get("points") or [])
         if q.get("world") and (not layers or q.get("layer") in layers)]
    T = [q for q in T if q[2] > 0]
    W = [g.W(u, v) for u, v in pts_uv]
    # ⭐ **社地の外の延長は `within` によらず必ず数える**【指6 庭方 2026-09-09 十八巡目】──
    #    ⛔ 除く行だけを測ると、**将来ほかの芯線が社地から出た日に黙る**(規則19)。
    soch = d["polygon"]
    n = c = 0
    gap = run = 0
    out9 = 0
    for i in range(len(W) - 1):
        ax, az = W[i]; bx, bz = W[i + 1]
        L = math.hypot(bx - ax, bz - az)
        m = max(1, int(math.ceil(L / step)))
        for j in range(m + 1):
            if i and j == 0: continue
            t = j / float(m)
            px, pz = ax + (bx - ax) * t, az + (bz - az) * t
            # ⭐ **社地の外は分母に入れない**【決1① 庭方 2026-09-09 十八巡目】── 東の勝手道の
            #    起点の側は長明院前の**町地**で、当図の社叢の外である。⛔ そこを数えた被覆は
            #    受入値の意味を持たない。
            if not in_poly((px, pz), soch):
                out9 += 1
                if within:
                    run = 0                  # ⛔ 外の区間を『続いた空き』に数えない
                    continue
            n += 1
            hit = False
            for x9, z9, r9 in T:
                if (px - x9) ** 2 + (pz - z9) ** 2 <= r9 * r9: hit = True; break
            if hit: c += 1; run = 0
            else:
                run += 1; gap = max(gap, run)
    return ((c * 100.0 / n) if n else None, n, c, gap * step, out9 * step)


def crown_cover_paths(d, g, spec):
    """`crownCover[].pathFrom` の指し先 → 芯線(uv)の列 [(銘, [(u,v)…])]。"""
    p = spec.get("pathFrom") or ""
    out = []
    if p.startswith("kattemichi"):
        for k in d.get("kattemichi", []):
            out.append((k["name"], [(g.U(x), g.V(z)) for x, z in k["pts"]]))
    elif p.startswith("kaidans"):
        nm = p.partition("[")[2].partition("]")[0]
        for k in d["kaidans"]:
            if k["name"] == nm:
                out.append((k["name"], [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]))
    return out


def crown_gap_limit(d, g, pts_uv):
    """**芯線の連続した無被覆区間の上限**[m]。⛔ 数を持たない【決1② 庭方 2026-09-09 十八巡目】。

    = (その芯線が通る帯のうち `spacing` の**上端が最大**の帯の値) + **松の樹冠の半径の中央値**。
    ⚠ 覆いが最も痩せる区間が支配するので、通る帯が複数なら**最も疎な帯**を採る。
    ⚠ 松の樹冠は**焼き出しの実物**から引く(⛔ 部材が細くなれば上限も自動で締まる)。
    戻り (上限[m], 採った帯, 芯々[m], 樹冠の半径の中央値[m]) — 引けなければ (None,…)。
    """
    bs, seen = [], set()
    for u, v in pts_uv:
        b = band_at(d, g, u, v)
        if b and b["band"] not in seen and b.get("spacing"):
            seen.add(b["band"]); bs.append(b)
    if not bs: return (None, None, None, None)
    b = max(bs, key=lambda q: q["spacing"][1])
    R = []
    if os.path.exists(IMPL_OUT):
        im = json.load(open(IMPL_OUT, encoding="utf-8"))
        R = sorted((q["crownM"] / 2.0) for q in ((im.get("planting") or {}).get("points") or [])
                   if q.get("layer") == "松" and q.get("crownM"))
    if not R: return (None, b["band"], b["spacing"][1], None)
    r = R[len(R) // 2]
    return (b["spacing"][1] + r, b["band"], b["spacing"][1], r)


def crown_cover_theoretical(d, g, pts_uv, layers=None, dM=None):
    """**肩ゼロ換算の理論上限**[%]【決1① 庭方 2026-09-09 十八巡目・規則19】。

    芯線の一点が覆われる確率 = 1 − exp(−Σ λ·A(d))。λ はその帯の宣言密度[本/100 m²]、
    A(d) は半径 r の円から**幅 2d の帯**(道の敷き)を除いた面積 =
    2·(r²·arccos(d/r) − d·√(r²−d²))(d ≥ r なら 0)。
    ⛔ **これは『肩を詰めれば届く』という読みを塞ぐための量**である ── 帯の密度のままでは
      受入値へ届かないことを図に並べて刷る(⛔ 差を埋めるのは名指しの木)。
    戻り (割合[%], 採った帯, d[m]) — 引けなければ (None,…)。
    """
    bs, seen = [], set()
    for u, v in pts_uv:
        b = band_at(d, g, u, v)
        if b and b["band"] not in seen:
            seen.add(b["band"]); bs.append(b)
    if not bs or dM is None: return (None, None, None)
    b = max(bs, key=lambda q: (q.get("spacing") or [0, 0])[1])
    R = {}
    if os.path.exists(IMPL_OUT):
        im = json.load(open(IMPL_OUT, encoding="utf-8"))
        for q in ((im.get("planting") or {}).get("points") or []):
            if q.get("crownM"): R.setdefault(q.get("layer"), []).append(q["crownM"] / 2.0)
    tot = 0.0
    for lay in (layers or ["松", "落葉", "中木"]):
        key = {"松": "takagiPer100", "落葉": "takagiPer100", "中木": "chubokuPer100"}.get(lay)
        rng = b.get(key)
        if not rng: continue
        lam = (rng[0] + rng[1]) / 2.0 / 100.0
        if lay == "松":   lam *= (1.0 - float(b.get("rakuyoRatio") or 0.0))
        if lay == "落葉": lam *= float(b.get("rakuyoRatio") or 0.0)
        rs = sorted(R.get(lay) or [])
        if not rs: continue
        r = rs[len(rs) // 2]
        if r <= dM: continue
        A = 2.0 * (r * r * math.acos(dM / r) - dM * math.sqrt(r * r - dM * dM))
        tot += lam * A
    return ((1.0 - math.exp(-tot)) * 100.0, b["band"], dM)


def crown_cover_check(d, g):
    """**道・坂の芯線が樹冠の下を通るか**【高1/高2 庭方 2026-09-09 十七巡目 → `planting.crownCover`】。

    ⛔ 受入値 `minPct` を下回れば止める。⛔ `minPct` が `null` の行は**求めないが刷る**
      (⛔ 『測らない』と『求めない』を混ぜない・規則19)。
    ⚠ 覆いは**数を増やして作る物ではない** ── 勝手道は肩(`kattemichiShoulderKen`)、
      女坂は名指しの差し掛け(`planting.sashikake`)が作る。
    """
    cc = d["planting"].get("crownCover") or []
    if not cc:
        return (["`planting.crownCover`(芯線の樹冠被覆の受入値)の宣言が無い — "
                 "⛔ 受入値が無ければ『林の中の道』は測られていない(規則19)"], [])
    bad, note = [], []
    for spec in cc:
        paths = crown_cover_paths(d, g, spec)
        if not paths:
            bad.append("`crownCover`「%s」の指し先 `%s` から芯線が引けない — **死んだポインタ**"
                       % (spec.get("name"), spec.get("pathFrom"))); continue
        pr9 = spec.get("pendingRef")
        if pr9 and pr9 not in (d.get("_pending") or {}):
            bad.append("`crownCover`「%s」の猶予 `pendingRef`『%s』が `_pending` に無い — "
                       "⛔ 指し先の無い猶予は誰も辿れない(規則19)" % (spec.get("name"), pr9))
            pr9 = None
        for nm, P in paths:
            wi = bool(spec.get("withinFrom"))
            pct, n, c, gap, outM = crown_cover(d, g, P, spec.get("layers"), within=wi)
            if pct is None:
                bad.append("`crownCover`「%s／%s」の被覆が測れない(焼き出しが無い)"
                           % (spec.get("name"), nm)); continue
            lim = spec.get("minPct")
            if lim is not None and pct < lim - 1e-9:
                msg = ("**%s(%s)の芯線の樹冠被覆 %.1f%%** が受入値 %g%% を下回る"
                       "(%d/%d 点・最長の空白 %.1f m)— ⛔ **数を増やして解かない**"
                       "(名指しの木 `planting.namedTrees` と差し掛けが作る)"
                       % (spec.get("name"), nm, pct, lim, c, n, gap))
                if pr9:
                    note.append("⚠ " + msg + "。⭕ **猶予**『%s』の内(⛔ 受入値を下げて"
                                "黙らせない ── 当たり先は庭方)【算出】" % pr9)
                else:
                    bad.append(msg)
            # ⭐ **決1② 連続した無被覆区間の上限**(従属値)── 麓から筋に読めるのは平均ではない
            gl, gb, gsp, gr = (None, None, None, None)
            if spec.get("maxGapFrom"):
                gl, gb, gsp, gr = crown_gap_limit(d, g, P)
                if gl is None:
                    bad.append("`crownCover`「%s／%s」の `maxGapFrom` が引けない"
                               "(帯の `spacing` か焼き出しの松の樹冠が無い)— ⛔ 0 は合格では"
                               "なく未測定(規則19)" % (spec.get("name"), nm))
                elif gap is not None and gap > gl + 1e-9:
                    m8 = ("**%s(%s)の連続した無被覆区間 %.1f m** が上限 **%.1f m**"
                          "(帯%s の芯々の上端 %.2f m + 松の樹冠の半径の中央値 %.2f m)を超える"
                          " — ⛔ **平均の被覆が足りていても、続いた空きは山を割る裸の筋になる**"
                          % (spec.get("name"), nm, gap, gl, gb, gsp, gr))
                    if pr9:
                        note.append("⚠ " + m8 + "。⭕ **猶予**『%s』の内(当たり先は庭方)【算出】"
                                    % pr9)
                    else:
                        bad.append(m8)
                else:
                    note.append("%s(%s)── 連続した無被覆区間 **%.1f m** ≤ 上限 **%.1f m**"
                                "(帯%s の `spacing` の上端 %.2f m + 松の樹冠の半径の中央値 "
                                "%.2f m)【算出 — 決1② 庭方 2026-09-09 十八巡目。⛔ 数を json に"
                                "書かない】" % (spec.get("name"), nm, gap, gl, gb, gsp, gr))
            # ⭐ **決1① 肩ゼロ換算の理論上限**を並べて刷る(⛔『肩を詰めれば届く』を塞ぐ)
            th = ""
            if spec.get("theoreticalFrom"):
                dm = None
                for k9 in d.get("kattemichi", []):
                    if k9["name"] == nm and k9.get("w"): dm = k9["w"] / 2.0
                tp, tb, td = crown_cover_theoretical(d, g, P, spec.get("layers"), dm)
                if tp is not None:
                    th = ("／ **肩ゼロ換算の理論上限 %.1f%%**(帯%s の宣言密度・d = 道幅/2 = "
                          "%.2f m)⛔ **肩では受入値へ届かない ── 差を埋めるのは名指しの木**"
                          % (tp, tb, td))
                else:
                    th = "／ 理論上限は引けない(⛔ 0 は合格ではなく未測定)"
            note.append("%s(%s)── 芯線の樹冠被覆 **%.1f%%**(%d/%d 点・刻み 0.5 m・"
                        "**最長の空白 %.1f m**)／ 受入値 %s ／ 測った層 %s%s%s"
                        "【算出 — ⛔ 0 件は合格ではなく未測定。⭕ `minPct` が無い行は"
                        "**求めないが刷る**(男坂は額縁の意匠で裸でよい)】"
                        % (spec.get("name"), nm, pct, c, n, gap,
                           ("**%g%% 以上**" % lim) if lim is not None else "**求めない**",
                           "・".join(spec.get("layers") or ["全層"]),
                           ("／ ⭕ **社地の外 %.1f m は分母から外した**(決1①)" % outM)
                           if (wi and outM) else
                           ("／ ⛔ **社地の外 %.1f m を分母に入れたまま**(⛔ `withinFrom` の"
                            "宣言が無い ── 指6 庭方 2026-09-09)" % outM) if outM else
                           "／ ⭕ **全区間が社地の内**(社地の外 0.0 m)", th))
    # ⭐ **全数当たり**【指6 庭方 2026-09-09 十八巡目】── ⛔ 『社地の外を分母に入れる検査は
    #    他にも無いか』を**毎回この一行で数える**(⛔ 一度当たって終わりにしない)。
    tot9 = [0, 0, 0.0]
    naked = []
    for spec in cc:
        wi9 = bool(spec.get("withinFrom"))
        for nm, Pp in crown_cover_paths(d, g, spec):
            _p, _n, _c, _gp, o9 = crown_cover(d, g, Pp, spec.get("layers"), within=wi9)
            tot9[0] += 1
            if o9:
                tot9[1] += 1
                tot9[2] += o9
                if not wi9: naked.append("%s(%.1f m)" % (nm, o9))
    if naked:
        bad.append("`crownCover` の芯線『%s』が**社地の外を分母に入れたまま** — "
                   "⛔ `withinFrom` を宣言していない(指6 庭方 2026-09-09 十八巡目。"
                   "⛔ 社地の外に樹冠が無いのは当たり前で、その区間を数えた被覆は受入値の"
                   "意味を持たない)" % "』『".join(naked))
    note.append("〔全数当たり〕`crownCover` の芯線 **%d 本**を全部当たった ── **社地の外へ出る"
                "芯線 %d 本**(外の延長の合計 %.1f m)／ そのうち `withinFrom` を宣言していない"
                "**%d 本**(= 欠陥)。⭕ 残る %d 本は**全区間が社地の内**である"
                "【算出 — 指6 庭方 2026-09-09 十八巡目『社地の外を分母に入れる検査は、他にも"
                "あれば同じ欠陥です』。⛔ 一度当たって終わりにしない ── 毎回この一行で数える。"
                "⛔ 0 件は合格ではなく未測定 ── 本数を必ず添える】"
                % (tot9[0], tot9[1], tot9[2], len(naked), tot9[0] - tot9[1]))
    return bad, note


def _design_y_cold(d, g, x, z):
    """`design_y` を**呼び出し順に依存しない形**で引く(焼き出しの定義)。

    ⭐ **揺れは 2026-09-09 に根で直した**【低1 検図20巡目】── `slope_lands` の覚え書きの鍵を
      「法尻の点 + 向き + 面の高さ」まで完全にしたので、`design_y` は呼び出し順に依らない。
      ⛔ それでもここは覚え書きを空にしてから引く ── **焼き出しの定義**は「冷えた値」であり、
      定義を『たまたま今は一致する』に寄りかからせない。⭕ 一致は `graded.orderDrift` が
      毎回全セルで測り、⛔ **一セルでも食い違えば検査が止める**(規則19 — 直したから測るのを
      やめる、をしない)。
    ⚠ 旧図はここで揺れを吸っていた。⛔ 吸うのは応急で、検図の判定は
      『**焼き出しは正しい。誤っているのは図の側**』── 図の切盛と体積表は 8.18 m³ ぶん
      余計な盛土を描いていた。
    """
    _LAND.clear()
    return design_y(d, g, x, z)


def graded_grid(d, g):
    """造成後の地盤 ── **図の切盛図と同じ `design_y`** を世界座標 1 m 格子へ焼く。

    ⛔ 実装側で計算し直さない(段・石段の割付・法面・崖の上の縁の仕分けが全部ここに入る)。
    ⚠ `null` は「造成しない」= **現地形のまま**であって、穴ではない
    (この社は面が2枚しかなく、社地の大半は自然の斜面 = 社叢の帯である)。
    """
    P = d["polygon"]
    cap = d["const"].get("featherCap", 12.0)
    x0 = math.floor(min(p[0] for p in P) - cap)
    x1 = math.ceil(max(p[0] for p in P) + cap)
    z0 = math.floor(min(p[1] for p in P) - cap)
    z1 = math.ceil(max(p[1] for p in P) + cap)
    nx = int((x1 - x0) / IMPL_STEP) + 1
    nz = int((z1 - z0) / IMPL_STEP) + 1
    H, n9 = [], 0
    for iz in range(nz):
        row = []
        for ix in range(nx):
            y9 = _design_y_cold(d, g, x0 + ix * IMPL_STEP, z0 + iz * IMPL_STEP)
            row.append(None if y9 is None else round(y9, 3))
            if y9 is not None: n9 += 1
        H.append(row)
    # ⭕ **揺れそのものを測って残す**(規則19)── 同じ格子を「覚え書きを積んだまま」= 図が
    #    実際に描く順で引き直し、冷えた値と何セル食い違うかを数える。⛔ 数を文章に書かない —
    #    検査『焼き出しの造成後の地盤…』がこの欄を読んで刷り、⛔ **0 でなければ止める**。
    #    ⚠ 2026-09-09 に鍵を直して 0 になったが、測るのはやめない(戻ったら鳴る所が要る)。
    _LAND.clear()
    flip, dmax = 0, 0.0
    for iz in range(nz):
        for ix in range(nx):
            y8 = design_y(d, g, x0 + ix * IMPL_STEP, z0 + iz * IMPL_STEP)
            y9 = H[iz][ix]
            if (y8 is None) != (y9 is None): flip += 1
            elif y8 is not None: dmax = max(dmax, abs(round(y8, 3) - y9))
    _LAND.clear()
    return {"x0": float(x0), "z0": float(z0), "step": IMPL_STEP,
            "nx": nx, "nz": nz, "filled": n9, "h": H,
            "orderDrift": {"cells": nx * nz, "nullFlip": flip, "maxDiff": round(dmax, 4),
                           "_": "**`design_y` が呼び出し順で答えを変えるセルの数**。"
                                "⭕ **0 が正**【低1 検図20巡目 → 2026-09-09】── `slope_lands` の"
                                "覚え書きの鍵を『法尻の点 + 向き + 面の高さ』まで完全にして直した。"
                                "⛔ 0 でなければ検査が止める(覚え書きが答えを変えている = "
                                "切盛図・断面・社地外の集計が呼ぶ順で動くということ)"}}


def _w(g, p):
    x, z = g.W(p[0], p[1])
    return [round(x, 3), round(z, 3)]


def _w_segs(g, o):
    """`run_segs`(= 開口を抜いた実際に建つ区間)を世界座標へ。⛔ 実装が開口を切り直さない。"""
    return [[_w(g, a), _w(g, b)] for a, b in run_segs(o)]


def impl_runs(d, g):
    """囲い(`runs`)と土留め(`terraceWalls`)の**建つ区間**を世界座標で焼く。

    ⭐ `Ita_Keidai` は `a`/`b` が null で、**平場の輪郭からの生成物**(`derive_runs`)なので
      指図からは引けない。`Saku_SW`(法尻の柵)・`Saku_Sando`(参道の柵)も同じく折れ線が要る。
    ⭐ 口(`gaps`)は石段の頭・門の口・並走の切れ(`skips`)からの従属値(`derive_gaps`)。
    """
    out = []
    for o in d["runs"]:
        gl = gap_ledger(o)
        out.append({"name": o["name"], "of": "run", "kind": o.get("kind"),
                    "seat": o.get("seat"), "h": run_take_m(d, o),
                    "nodes": [_w(g, q) for q in (o.get("pts") or
                                                 ([o["a"], o["b"]] if o.get("a") else []))],
                    "segs": _w_segs(g, o),
                    "gaps": [[_w(g, q)[0], _w(g, q)[1], round(q[2] * d["const"]["ken"], 3)]
                             for q in (o.get("gaps") or [])],
                    "skips": len(o.get("skips") or []),
                    "lenM": round(run_len_ken(o) * d["const"]["ken"], 3),
                    "nodeLenM": round(run_nodes_ken(o) * d["const"]["ken"], 3),
                    "gapLedgerM": dict((k9, round(v9 * d["const"]["ken"], 3))
                                       for k9, v9 in gl.items() if not k9.endswith("の数"))})
    for o in d["terraceWalls"]:
        sm = wall_samples(d, g, o, IMPL_WALL_STEP)
        k9 = wall_stair(d, o)
        fh = [q[4] for q in sm] or [0.0]                  # 見付高
        bh = [q[5] for q in sm] or [0.0]                  # 受け高
        out.append({"name": o["name"], "of": "wall", "kind": "土留め",
                    "coping": o.get("coping"),
                    "copingFrom": (k9["name"] if k9 is not None else None),
                    "nodes": [_w(g, q) for q in wall_nodes(d, o)],
                    "segs": _w_segs(g, o),
                    "lenM": round(run_len_ken(o) * d["const"]["ken"], 3),
                    # ⭐ **走り 1 m 刻みの 6 列**【中4 検図20巡目 → 裁定 2026-09-09(A案)】。
                    #   ⛔ `coping:"stair"` の4本は **`stair_spans` から天端を引く** ── 実装が
                    #   「壁の走り → 石段の割付の y」の対応を自力で作る道を塞ぐ。
                    "profileStep": IMPL_WALL_STEP,
                    "profile": wall_profile(d, g, o, IMPL_WALL_STEP),
                    "gapsS": wall_gaps_s(sm, IMPL_WALL_STEP),
                    "faceM": [round(min(fh), 3), round(max(fh), 3)],
                    "backM": [round(min(bh), 3), round(max(bh), 3)],
                    "_": "`profile` = **[走り s[m], 天端 y[m], 低い側の地盤 y[m], "
                         "高い側の地盤 y[m], 見付高[m], 受け高[m]]** を `profileStep` 刻みで。"
                         "s は `nodes[0]` からの走り。⛔ 実装が引き直さない ── 天端は `coping` "
                         "が数ならその値、`\"stair\"` なら `copingFrom` が指す石段の割付"
                         "(`stair_spans`)から引いてある。**地盤は造成後 `design_y` 一本を基準に"
                         "壁の両側で採る**(`const.wallProbeM`)。見付高 = 天端 − 低い側 ／ "
                         "受け高 = 高い側 − 天端【裁定 2026-09-09 普請奉行 = 検図21巡目 A案】。"
                         "⛔ **見付≦0 かつ 受け>0 の区間は『埋まっている壁』**で、⛔ 実装が"
                         "地形を削って直さない(始末は指図が持つ)。`gapsS` は**建たない区間**(開口)の "
                         "s の範囲で、`segs` と同じ出所"})
    return out


def impl_stairs(d, g):
    """石段 ── 折れ線・幅・**割付**(`stair_spans`)。⛔ 実装が段を割り直さない。

    ⚠ 切盛図・断面・動線の昇りが**この一つの関数**を通る(二つの式で別々に割ると
      蹴上1段ぶんずれる — 2026-08-24 検図 高-4、男坂で最大 1.34 m)。
    """
    out = []
    for k in d["kaidans"]:
        sp, tot = stair_spans(k)
        pts = [tuple(q) for q in (k.get("pts") or [k["a"], k["b"]])]
        out.append({"name": k["name"], "wM": round(kaidan_wm(d, k), 4),
                    "yBot": k["yBot"], "yTop": k["yTop"],
                    "keri": k.get("keri"), "fumi": k.get("fumi"),
                    "steps": k.get("steps"), "flights": k.get("flights"),
                    "odoriba": k.get("odoriba"),
                    "nodes": [_w(g, q) for q in pts],
                    "runM": (round(tot * 1.0, 4) if tot else None),
                    "spans": ([[round(a, 4), round(b, 4), round(y, 4)] for a, b, y in sp]
                              if sp else None)})
    return out


def impl_gates(d, g):
    """門の芯 ── **`uFrom` を持つ門は芯が従属値**(仁王門は前庭の西縁+犬走りから)。"""
    return [{"name": gt["name"], "u": gt["u"], "v": gt["v"], "yaw": gt.get("yaw"),
             "sill": gt.get("sill"), "plan": gt["plan"],
             "monguchiKen": gt.get("monguchiKen"),
             "world": _w(g, (gt["u"], gt["v"]))} for gt in d["gates"]]


def impl_routes(d, g):
    """動線の折れ線(世界座標)。⭐ `from` を持つ動線は勝手道からの組み立て(`derive_routes`)。"""
    out = []
    for rt in d.get("routes", []):
        pts = [[round(q[0], 3), round(q[1], 3)] if rt.get("world") else _w(g, q)
               for q in rt["pts"]]
        out.append({"name": rt["name"], "kind": rt.get("kind"), "w": rt.get("w"),
                    "wByTerrace": rt.get("wByTerrace"), "world": pts})
    return out


def impl_tamagaki(d, g):
    """玉垣の**建つ区間**(辺ごと・木戸の開口を抜いた実長)。⛔ 実装が辺を割り直さない。"""
    out = []
    for gd in d["gardens"]:
        if not gd.get("tamagaki"): continue
        for nm, a, b, fence, ln, rs in tamagaki_edges(d, gd):
            out.append({"garden": gd["name"], "edge": nm, "fence": bool(fence),
                        "a": _w(g, a), "b": _w(g, b),
                        "segs": [[_w(g, q[0]), _w(g, q[1])] for q in rs],
                        "lenM": round(ln * d["const"]["ken"], 3),
                        "spec": gd["tamagaki"]})
    return out


def impl_props(d, g):
    """点景・踏石・井戸屋形・区の輪郭・見所 ── どれも**宣言からの従属値**で、
    指図に矩形が入っていない(規則4)。⛔ 実装が組み立て直さない。

    ・`props`      … `prop_rects`(芯 + `plan`/`planM` + `yaw` から回した4点)
    ・`fumiishi`   … `fumiishi_rects`(門の戸口の内法・石段の幅からの従属値)
    ・`ido`        … `ido_rects` / `ido_depth` / 井桁・礎石・井筒の径
    ・`gardens`    … 区の輪郭(`polyFrom` を持つ区は門の面から従属)
    ・`viewpoints` … 見所(`uFrom` を持つ見所は門の面から従属)。検証レンダの視点でもある
    """
    io9 = ido_rects(d)
    return {
        "props": [{"name": nm, "world": [_w(g, q) for q in Q]} for nm, Q in prop_rects(d)],
        "fumiishi": [{"name": q[0], "world": [_w(g, (q[1], q[2])), _w(g, (q[3], q[2])),
                                              _w(g, (q[3], q[4])), _w(g, (q[1], q[4]))]}
                     for q in fumiishi_rects(d)],
        "ido": (None if not io9 else
                {"rects": dict((k9, ([_w(g, q) for q in v9] if k9 == "柱" else
                                     [_w(g, (v9[0], v9[1])), _w(g, (v9[2], v9[1])),
                                      _w(g, (v9[2], v9[3])), _w(g, (v9[0], v9[3]))]))
                               for k9, v9 in io9.items()),
                 "depthM": [round(q, 3) for q in ido_depth(d)],
                 "igetaRise": igeta_rise(d), "soishiR": soishi_radii(d),
                 "izutsuR": izutsu_radii(d)}),
        "gardens": [{"name": gd["name"],
                     "world": [_w(g, q) for q in (gd.get("poly") or [])],
                     "rect": ([gd.get("u0"), gd.get("v0"), gd.get("u1"), gd.get("v1")]
                              if gd.get("u0") is not None else None)}
                    for gd in d["gardens"]],
        "viewpoints": [{"name": vp["name"], "u": vp["uv"][0], "v": vp["uv"][1],
                        "world": _w(g, vp["uv"]), "eyeH": vp.get("eyeH"),
                        "look": vp.get("look")} for vp in d.get("viewpoints", [])],
    }


def export_impl(d, g):
    """**実装が読む算出物を焼く**(`docs/Sashizu/sanno_impl.json`)。

    ⭕ スキーマの正典は棟梁の `EdoOkabeYashikiBuilder.IMPL` の doc コメント(岡部が先例)。
    ⛔ **指図か造成前の地盤が変われば焼き直しが要る** — `src.sha256` / `dem.sha256` を入れ、
      実装も図(`impl_fresh_check`)も同じ照合をして、食い違えば止まる。
    ⛔ ここで設計値を作らない ── すべて図が使うのと**同じ関数**の返り値である。
    """
    import datetime
    pts, bd, cl = scatter_pts(d, g)
    gr = graded_grid(d, g)
    out = dict([
        ("of", "sanno_sashizu.json"),
        ("src", {"sha256": _sha256(JSON), "bytes": os.path.getsize(JSON),
                 "_": "**`docs/Sashizu/sanno_sashizu.json` のバイト列**の SHA-256(小文字hex)。"
                      "⛔ 一致しなければ**古い焼き**なので建てない"}),
        ("dem", {"sha256": _sha256(DEM_JSON), "bytes": os.path.getsize(DEM_JSON),
                 "_": "**`docs/Sashizu/sanno_dem.json`(造成前の地盤の正本)のバイト列**の "
                      "SHA-256。⛔ 地盤が変われば `graded` も社叢の帯も変わる"}),
        ("generator", {"path": "Tools/Sashizu/build_sanno_sashizu.py --export-impl",
                       "sha256": _sha256(os.path.abspath(__file__)),
                       "_": "⚠ 生成器の版。⛔ 一致の照合には使わない(図の作り替えで毎回変わる)"}),
        ("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
        ("checks", {"exportTol": IMPL_EXPORT_TOL, "gradeTol": IMPL_GRADE_TOL,
                    "_": "⭐ **物差しは二つ。混ぜない**【中3 検図20巡目 → 2026-09-09】。"
                         "`exportTol` = **図の側** ── 焼いた `graded` と `design_y` の許容差[m]"
                         "(同じ関数から出るので丸めの 0.001 m 以外は出ない。図は**全セル**を"
                         "引き直して突き合わせる ⛔ 標本で済ませない)。"
                         "`gradeTol` = **実装側** ── 造成した地形と設計面の許容差[m]で、意味の"
                         "正典は `EdoOkabeYashikiBuilder.IMPL` の doc コメント(岡部と同じ 0.30)。"
                         "⚠ ハイトマップは 16bit 正規化で量子が 0.003〜0.009 m あるので、"
                         "⛔ ここへ 0.001 を入れると造成後QAが全セル不合格になる。"
                         "⛔ どちらも検査の物差しであって設計値ではない。"
                         "⚠ **`gradeTol` は当図の側に消費者がゼロ**【低1 検図21巡目 → 2026-09-09】"
                         "── 図は `exportTol` しか使わない。⭕ **設計としては正しい**(実装側の"
                         "造成後QAの許容差で、意味の正典は岡部の `IMPL` の doc コメント)ので、"
                         "⛔ 落とさない。⚠ **輪に入るのは棟梁が造成した地形をこの値で測る所**で、"
                         "そこまでは『**焼いてあるが誰も読んでいない値**』である(規則19)── "
                         "実装の着手時に消費点を作ること"}),
        ("grid", {"x0": d["grid"]["keidai"]["x0"], "z0": d["grid"]["keidai"]["z0"],
                  "ken": d["const"]["ken"],
                  "_": "x = x0 + u×ken ／ z = z0 + v×ken(u=東+/v=北+・軸は世界軸)"}),
        ("terraces", [{"name": t["name"], "y": t["y"],
                       "world": [[round(q[0], 3), round(q[1], 3)]
                                 for q in terrace_poly(t, g)]} for t in d["terraces"]]),
        ("graded", gr),
        ("stairs", impl_stairs(d, g)),
        ("runs", impl_runs(d, g)),
        ("gates", impl_gates(d, g)),
        ("routes", impl_routes(d, g)),
        ("tamagaki", impl_tamagaki(d, g)),
        ("setae", impl_props(d, g)),
        ("planting", {"points": pts, "bands": bd, "clusters": cl,
                      "seedRule": d["planting"]["plantRule"]["seed"],
                      "placement": d["planting"]["plantRule"].get("placement"),
                      "_": "**撒いた木の点**。⛔ 実装側で撒き直さない — 別の乱数で撒けば"
                           "退避も林冠も図が測った物と別になる。種は `seedRule` の宣言から"
                           "決定論的に作るので、同じ指図からは同じ配置が出る"}),
    ])
    json.dump(out, open(IMPL_OUT, "w", encoding="utf-8"), ensure_ascii=False)
    return {"graded": gr["filled"], "cells": gr["nx"] * gr["nz"],
            "runs": len(out["runs"]), "stairs": len(out["stairs"]),
            "gates": len(out["gates"]), "routes": len(out["routes"]),
            "tamagaki": len(out["tamagaki"]), "points": len(pts),
            "props": len(out["setae"]["props"]), "fumiishi": len(out["setae"]["fumiishi"]),
            "viewpoints": len(out["setae"]["viewpoints"]),
            "bands": len(bd), "clusters": len(cl)}


def impl_fresh_check(d):
    """**焼いた算出物が今の指図・今の地盤から焼かれた物か**【2026-09-08 棟梁の診断 → 規則19】。

    ⛔ 古い焼きで建てると、指図では直っているはずの物が現物にだけ残る
      (2026-09-01 に松江松平の Stage7 で起きた型)。
    ⭕ 照合するのは**バイト列の SHA-256** 二本 ── 指図 `sanno_sashizu.json` と
      造成前の地盤の正本 `sanno_dem.json`。⛔ 生成器の版は照合に使わない(図の作り替えで
      毎回変わるので、照合に使うと常に赤になる)。
    """
    if not os.path.exists(IMPL_OUT):
        return (["実装が読む算出物 `sanno_impl.json` がまだ焼かれていない — "
                 "`python3 Tools/Sashizu/build_sanno_sashizu.py --export-impl` を回すこと"], [])
    try:
        im = json.load(open(IMPL_OUT, encoding="utf-8"))
    except Exception as e9:
        return (["算出物が読めない: %s: %s" % (type(e9).__name__, e9)], [])
    bad, note = [], []
    for key, path, what in (("src", JSON, "指図"), ("dem", DEM_JSON, "造成前の地盤の正本")):
        got = _sha256(path)
        was = str((im.get(key) or {}).get("sha256"))
        if was != got:
            bad.append("算出物が**古い焼き**(%s の sha256 %s… に対し、算出物が名乗る元 %s…)— "
                       "`--export-impl` を回し直す" % (what, got[:12], was[:12]))
    note.append("算出物 `sanno_impl.json` %.0f KB ／ 焼いた日 %s ／ 元 指図 %s… ・ 地盤 %s…"
                "【算出 — ⛔ 照合はバイト列の SHA-256。生成器の版は照合に使わない】"
                % (os.path.getsize(IMPL_OUT) / 1024.0, im.get("at"),
                   str((im.get("src") or {}).get("sha256"))[:12],
                   str((im.get("dem") or {}).get("sha256"))[:12]))
    pl = (im.get("planting") or {})
    note.append("焼いた木の点 **%d** 本 ／ 造成後の地盤 %d セル(格子 %g m・値の入るセル %d)"
                "【算出 — ⛔ 実装側で撒き直さない・計算し直さない】"
                % (len(pl.get("points") or []), (im.get("graded") or {}).get("nx", 0)
                   * (im.get("graded") or {}).get("nz", 0),
                   (im.get("graded") or {}).get("step", 0),
                   (im.get("graded") or {}).get("filled", 0)))
    return bad, note


def _keepout_deref(d, ref):
    """`planting.clearance.keidai` / `slopeBands[3].avoid` / `slopeBands[2].rinen(散文)` を引く。

    ⛔ 指し先が引けなければ None(= **死んだポインタ**。合格ではない)。
    """
    ref = re.split(r"[((]", str(ref or ""))[0].strip()
    o = d
    for tok in ref.split("."):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]$", tok)
        if m:
            if not isinstance(o, dict) or m.group(1) not in o: return None
            o = o[m.group(1)]
            i = int(m.group(2))
            if not isinstance(o, list) or i >= len(o): return None
            o = o[i]
        else:
            if not isinstance(o, dict) or tok not in o: return None
            o = o[tok]
    return o


def keepout_wiring_check(d, g):
    """**`keepoutFrom` の一項ごとに、指し先が生きていて・面になり・焼き出しの点が守っているか**
    【中2 検図20巡目 → 2026-09-09】。

    ⚠ **見つかった穴**: `keepoutFrom` は「どこを見るか」の表なのに、**生成器がこの表を一度も
      読んでいなかった**。表が指す先の鍵が改名されても・散文の中に宣言が留まっていても、
      ⛔ 何も鳴らずに焼き出しへ違反が流れた(実測 — 帯3 の高木が社地の境から 0.00 m)。
    ⭕ **表そのものを名簿にして輪へ入れる。**一項ごとに三つを測る:
      ① **指し先が引ける**(`slopeBands[3].avoid` の形も引く)⛔ 死んだポインタを通さない
      ② **面が組める**(退避の形が**一つ以上**出る)⛔ 鍵が改名されて面が空になった日に、
         違反 0 が「合格」に見える道を塞ぐ ── **0 件は未測定である**(規則19)
      ③ **焼き出しの点が一本も載っていない**(⛔ 標本で済ませない・全点 × 全形)
    ⛔ **表に項を足して測り方を書き忘れる道も塞ぐ** ── 測り方の名簿と `keepoutFrom` の鍵が
      食い違えば⛔ で止まる(片方だけ足しても通らない)。
    """
    if not os.path.exists(IMPL_OUT): return ([], [])
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    P = (im.get("planting") or {}).get("points") or []
    if not P: return ([], [])
    kf = (d["planting"]["plantRule"].get("keepoutFrom") or {})
    ken = d["const"]["ken"]
    bad, note = [], []
    uv = dict((q["name"], (q["u"], q["v"])) for q in P)
    b3 = ([b for b in d["slopeBands"] if b["band"] == 3] or [None])[0]

    def pts_of(pred): return [q for q in P if pred(q["group"])]
    obi123 = pts_of(lambda gn: any(gn.startswith("社叢 帯%d " % i) for i in (1, 2, 3)))

    def sh_scope(sc): return avoid_shapes(d, g, sc)

    def sh_lay(fn):
        """層ごとの肩で組んだ形を層ごとに返す(帯1〜3 は肩が層で違う)。"""
        return dict((lay, fn(band_shoulder(d, lay))) for lay in _LAYS)

    # ⛔ **測り方の名簿**。鍵は `keepoutFrom` と**一字一句同じ**でなければならない
    wire = {
        "境内の立木3区": ("scope", lambda: sh_scope("keidai"),
                          lambda gn: gn.startswith("境内の立木")),
        "前庭": ("scope", lambda: sh_scope("zentei"),
                 lambda gn: gn.startswith("前庭の帯")),
        "社叢 帯4": ("scope", lambda: sh_scope("obi4"),
                     lambda gn: gn.startswith("社叢 帯4")),
        "社叢 帯3(南面)": ("rinen", None, None),
        "勝手道(西・東)": ("lay2", lambda lay: kattemichi_apron_shapes(
            d, g, kattemichi_shoulder(d, lay) or 0.0), None),
        "社地の境(全周)": ("lay2", lambda lay: kyoukai_avoid_shapes(
            d, g, kyoukai_shoulder(d, lay)), None),
        "囲い・土留め(柵・板塀・`TW_*`)": ("lay", lambda sh: kakoi_avoid_shapes(d, sh or 0.0), None),
        "設計された塊の箱": ("cluster", None, None),
    }
    # ⛔ **項ごとの『下位の源』の名簿**【中1 検図21巡目 → 2026-09-09】。
    #   ⚠ **旧版の関門は `n_sh <= 0`(合算)だけ**だったので、⛔ 下位の源が一つでも生き残れば
    #     通った ── `avoid_shapes` を「先頭1個だけ返す」版に差し替えて退避の形が 108 → 1 に
    #     なっても 0 件だった。鍵の改名で 1 クラスの障害物(石段だけ・棟だけ)が黙って落ちる
    #     道が開いたままだった。
    #   ⭕ **源ごとに『指図が宣言しているか』と『形が一つ以上出たか』の両方を測る。**
    #     ⛔ 宣言があるのに形が 0 の源は⛔で止める。⛔ 名簿に無いクラスの形が出たら
    #     (= 源を足して名簿を書き忘れた)これも止める ── 片側だけ足しても通らない。
    _fence = [1 for gd in d["gardens"] if gd.get("tamagaki")
              for _n, _a, _b, f9, _l, _r in tamagaki_edges(d, gd) if f9]
    src = {
        "境内の立木3区": [
            ("棟", [m for m in d["munes"] if m.get("yaku") != "接続"]),
            ("透塀", [r for r in d["runs"] if r.get("kind") == "透塀"]),
            ("回廊", [r for r in d["runs"] if r.get("kind") == "回廊"]),
            ("白洲", [gd for gd in d["gardens"] if gd["name"] == "白洲"]),
            ("中庭", [gd for gd in d["gardens"] if gd["name"] == "中庭"]),
            ("動線", d.get("routes") or []),
            ("石段", d["kaidans"]),
        ],
        "前庭": [
            ("動線", d.get("routes") or []),
            ("石段", d["kaidans"]),
            ("門", d["gates"]),
            ("前庭の縁", d["terraces"][1:2]),
            ("井戸", [1] if ido_rects(d) else []),
            ("玉垣", _fence),
            ("空地", [gd for gd in d["gardens"] if gd.get("noPlant") and gd.get("poly")]),
            ("点景", prop_rects(d)),
        ],
        "社叢 帯4": [
            ("男坂", [k for k in d["kaidans"] if k["name"] == "男坂"]),
            ("女坂", [k for k in d["kaidans"] if k["name"].startswith("女坂")]),
            ("参道", [d["sando"]] if d.get("sando") else []),
            ("前庭の縁", d["terraces"][1:2]),
            # ⚠ 帯4 は `kakoi_avoid_shapes(skip_zentei=True)` を通すので、**前庭の縁の柵・板塀・
            #   土留めは源から外れる**(帯4 は `avoid.zenteiFromEdge` で同じ縁を測っている)
            ("柵", [r for r in d["runs"] if r.get("kind") == "柵"
                    and not r["name"].startswith("Ita_Z")]),
            ("板塀", [r for r in d["runs"] if r.get("kind") == "板塀"
                      and not r["name"].startswith("Ita_Z")]),
            ("土留め", [w9 for w9 in d["terraceWalls"]
                        if not w9["name"].startswith("TW_Zentei")]),
            ("社地の境", d["polygon"]),
        ],
        "勝手道(西・東)": [("勝手道:" + k9["name"], [k9]) for k9 in d.get("kattemichi", [])],
        "社地の境(全周)": [("社地の境", d["polygon"])],
        "囲い・土留め(柵・板塀・`TW_*`)": [
            ("柵", [r for r in d["runs"] if r.get("kind") == "柵"]),
            ("板塀", [r for r in d["runs"] if r.get("kind") == "板塀"]),
            ("土留め", d["terraceWalls"]),
        ],
        "設計された塊の箱": [("塊:" + c9["name"], [c9])
                             for gd in d["gardens"] + d["slopeBands"] + view_holders(d)
                             for c9 in gd.get("clusters", [])],
    }

    def _cls(nm9):
        """形の名から**源の類**を採る(「類:名」の類、括弧書きは落とす)。"""
        return nm9.split(":")[0] if ":" in nm9 else re.split(r"[((]", nm9)[0]

    def _src_check(label, shp):
        """項の**下位の源**が一つ残らず形を出したか(⛔ 合算で済ませない)。"""
        rost = src.get(label)
        if rost is None: return
        # 名簿の鍵が「類:名」なら名指しで、そうでなければ類で数える
        cnt = {}
        for sh9 in shp:
            nm9 = sh9[-2]
            cnt[nm9] = cnt.get(nm9, 0) + 1
            cnt[_cls(nm9)] = cnt.get(_cls(nm9), 0) + 1
        miss = [k9 for k9, decl in rost if decl and not cnt.get(k9)]
        if miss:
            bad.append("`keepoutFrom`「%s」── 指図が宣言している**下位の源 %d 件が退避の形を"
                       "一つも出していない**(%s)。⛔ 合算で 1 個でも形があれば通る関門では、"
                       "鍵の改名で 1 クラスの障害物が黙って落ちる(中1 検図21巡目)"
                       % (label, len(miss), "・".join(miss[:6])))
        known = set(k9 for k9, _dc in rost) | set(_cls(k9) for k9, _dc in rost)
        extra = sorted(set(_cls(sh9[-2]) for sh9 in shp) - known)
        if extra:
            bad.append("`keepoutFrom`「%s」の退避に、**名簿に無い源の形**がある(%s)— "
                       "⛔ 源を足して測り方の名簿に書き忘れる道を塞ぐ(規則19)"
                       % (label, "・".join(extra[:6])))
        note.append("`keepoutFrom`「%s」の**下位の源** ── 宣言 %d 件 / 形を出した %d 件"
                    "(%s)【算出 — ⛔ 合算 `n_sh` では鳴らない(中1 検図21巡目)】"
                    % (label, len([1 for k9, dc in rost if dc]),
                       len([1 for k9, dc in rost if dc and cnt.get(k9)]),
                       "・".join("%s %d" % (k9, cnt.get(k9, 0)) for k9, dc in rost if dc)))

    if sorted(wire.keys()) != sorted(kf.keys()):
        bad.append("`keepoutFrom` の項と、検査が測り方を持つ項が食い違う(表 %d 項 / 測り方 %d 項"
                   "・差 %s)— ⛔ 表に項を足して測り方を書き忘れる道を塞ぐ(規則19)"
                   % (len(kf), len(wire), "／".join(sorted(set(kf) ^ set(wire))) or "並び"))
    for label in sorted(kf.keys()):
        ref = kf[label]
        tgt = _keepout_deref(d, ref)
        if tgt is None or tgt is False or tgt == {} or tgt == []:
            bad.append("`keepoutFrom`「%s」の指し先 `%s` が引けない/空 — **死んだポインタ**"
                       "(宣言だけ残って面にならない・規則19)" % (label, ref))
            continue
        w = wire.get(label)
        if w is None: continue
        kind, mk, pred = w
        if kind == "scope":
            shp = mk()
            hits = [q["name"] for q in P if pred(q["group"])
                    and shape_hit_baked(uv[q["name"]], shp)]
            n_sh = len(shp)
            tested = len(pts_of(pred))
            _src_check(label, shp)
        elif kind in ("lay", "lay2"):
            n_sh, hits, tested, big = 0, [], len(obi123), []
            for lay in _LAYS:
                shp = mk(lay) if kind == "lay2" else mk(band_shoulder(d, lay))
                if len(shp) > len(big): big = shp
                n_sh = max(n_sh, len(shp))
                hits += [q["name"] for q in obi123 if q["layer"] == lay
                         and shape_hit_baked(uv[q["name"]], shp)]
            _src_check(label, big)
        elif kind == "cluster":
            shp = cluster_keepout_shapes(d)
            n_sh = len(shp)
            _src_check(label, shp)
            own = set()
            for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
                for c in gd.get("clusters", []): own.add("%s／%s" % (gd["name"], c["name"]))
            # ⭐ **名指しで据えた木は『撒き込み』ではない** ── `clusterRule` が落とすのは
            #   帯から**撒く**候補セルであって(`scatter_pts` の `cluster_keepout_shapes`)、
            #   意匠が位置を決めた木(一本立ち・差し掛け・名指しの木・★主景)はそもそも
            #   帯の本数に含まれない。物差しは `is_named_group` 一本(⛔ 写さない)。
            named = is_named_group
            tested = len([q for q in P if q["group"] not in own and not named(q["group"])])
            hits = [q["name"] for q in P if q["group"] not in own and not named(q["group"])
                    and shape_hit_baked(uv[q["name"]], shp)]
            # ⭐⭐ **名指しの木が設計された塊の余白へ入るのは ⛔ である**
            #   【A-3 庭方 2026-09-09 十九巡目 ── ⛔ 十八巡目の ⚠(〔記録〕どまり)は覆された】。
            #   ⭕ 格の根拠 ── 額縁の役『麓から男坂と仁王門を見せる』は【S [名所図会・山王]】で、
            #     当図の植栽でいちばん典拠の格が高い受入値である。⛔ **同じ箱を撒き木には⛔・
            #     名指しの木には⚠ にしてはいけない**(撒き木は既に `clusterRule` で同じ余白を
            #     ⛔ で守っており、しかも名指しの木は `isolatedCrown` で樹冠が大きい)。
            #   ⭕ **物差しは箱の輪郭 + その塊の芯々 × `packRatio`・測るのは幹の芯**
            #     = `bandDef.avoid.clusterRule` と同一の式(⛔ 二つ目の余白の数を作らない)。
            #   ⭕ **適用範囲はすべての設計された塊 × すべての名指しの木**
            #     (⛔ 『男坂の見切り』だけを名簿にしない)。
            #   ⚠ **`withinCluster` を宣言した木だけは除く** ── ★主景は庭方が
            #     「西Aに hMin 以上の落葉高木を1本必ず入れ、位置を固定する」と決めた木で、
            #     ⛔ 塊の**中に立つことが役**である。⛔ 黙って外さない(下で名を刷る)。
            wc9 = set()
            for gd9 in d["gardens"]:
                sk9 = gd9.get("shukei") or {}
                t9 = sk9.get("tree") or {}
                if t9.get("withinCluster"): wc9.add(t9["name"])
            nmd9 = ["%s(%s)" % (q["name"], shape_hit_baked(uv[q["name"]], shp))
                    for q in P if named(q["group"]) and q["name"] not in wc9
                    and shape_hit_baked(uv[q["name"]], shp)]
            # ⛔ **正典を二つ持たない**(規則4)── **受入値の⛔は設計の側**
            #    (`named_vs_cluster_check`)が持つ。ここが測るのは**焼き出しが設計と同じか**で、
            #    ⛔ 食い違えば⛔で止める(焼き直し忘れ・撒き方の取りこぼしはここでしか出ない)。
            dv9 = named_vs_cluster_check(d, g)[0]
            if bool(nmd9) != bool(dv9):
                bad.append("名指しの木 × 塊の余白 ── **設計の側と焼き出しの側で答えが違う**"
                           "(設計 %d 件 ／ 焼き出し %d 本)。⛔ `--export-impl` を回し直すか、"
                           "撒き方の取りこぼしを疑う(規則19)" % (len(dv9), len(nmd9)))
            note.append("名指しの木 × 設計された塊の余白(**焼き出しの側**)── **%d 本**"
                        "(測った名指しの木 %d 本 × 塊の面 %d ／ 例外 `withinCluster` %d 本)%s"
                        "【算出 — ⛔ 受入値の⛔は設計の側 `named_vs_cluster_check` が持つ"
                        "(⛔ 同じ受入値に正典を二つ持たない・規則4)。ここは**設計と焼き出しの"
                        "突き合わせ**である】"
                        % (len(nmd9), len([q for q in P if named(q["group"])]), n_sh, len(wc9),
                           ("── " + "・".join(sorted(nmd9))) if nmd9 else ""))
        else:   # rinen ── 帯3 の**南面**(林縁が測る社地の辺)から高木を退ける宣言
            if b3 is None or not (b3.get("rinen") or {}):
                bad.append("`keepoutFrom`「%s」── 帯3 に `rinen` の宣言が無い" % label); continue
            E = rinen_edges(d, g, b3)
            n_sh = len(E)
            if not E:
                # ⛔ **空判定を `min()` のループの前へ**【中2 検図21巡目 → 2026-09-09】── 旧図は
                #   ②の関門(`n_sh <= 0`)がループの後ろにあり、`rinen_edges` が空になると
                #   ⛔ ではなく `ValueError: min() iterable argument is empty` で落ちていた。
                bad.append("`keepoutFrom`「%s」の宣言から**退避の面が一つも組めない**(指し先 "
                           "`%s` は引けるのに林縁が測る辺が 0)— ⛔ 面が空なら違反 0 は"
                           "『合格』ではなく**未測定**" % (label, ref))
                continue
            to = b3["rinen"]["toKen"]
            tg = [q for q in P if q["group"].startswith("社叢 帯3 ")
                  and q["layer"] in ("松", "落葉")]
            tested = len(tg)
            hits, mn = [], None
            for q in tg:
                dd = min(_pt_seg(uv[q["name"]], a9, c9) for a9, c9 in E)
                mn = dd if mn is None else min(mn, dd)
                if dd <= to: hits.append(q["name"])
            note.append("`keepoutFrom`「%s」── 帯3 の高木 %d 本の、林縁が測る社地の辺 **%d 本**"
                        "からの最短 **%.3f m**(宣言 `rinen.toKen` %g 間 = %.3f m)"
                        "【算出 — ⛔ 旧図は生成器に『南面』の語が一つも無く、境から 0.00〜0.45 m に"
                        "松と椋が立っていた(中2 検図20巡目)】"
                        % (label, tested, n_sh, (mn or 0.0) * ken, to, to * ken))
        if n_sh <= 0:
            bad.append("`keepoutFrom`「%s」の宣言から**退避の面が一つも組めない**(指し先 `%s` は"
                       "引けるのに形が 0)— ⛔ 面が空なら違反 0 は『合格』ではなく**未測定**"
                       % (label, ref))
        if hits:
            bad.append("`keepoutFrom`「%s」の退避に焼き出しの木が **%d 本**載っている(例 %s)"
                       % (label, len(hits), "・".join(sorted(hits)[:3])))
        note.append("`keepoutFrom`「%s」→ `%s` ── 退避の形 **%d** ／ 測った点 **%d** ／ "
                    "載っている点 **%d**【算出 — ⛔ 標本で済ませない(全点 × 全形)。"
                    "⛔ 形 0 で通る道を塞いである】" % (label, re.split(r"[((]", str(ref))[0],
                                                       n_sh, tested, len(hits)))
    return bad, note


def impl_wall_profile_check(d, g):
    """**土留めの縦断が焼かれ、その一つ一つが図の算出と同じ数か**
    【中4 検図20巡目 → 高2 検図21巡目 → 裁定 2026-09-09(A案)】。

    ⛔ 焼いた値を誰も測らなければ、それは「合格」ではなく**未測定**である(規則19)。
    ⚠ **20巡目に足した版は天端しか測っていなかった** ── 法尻を1点 +1.0 m しても・露出を全点 0
      にしても・走り `s` を2倍にしても・縦断を2点に間引いても・`gapsS` を消しても⛔ 0 件だった
      (高2 検図21巡目・破壊試験5本すべて無音)。⇒ **`wall_profile` を引き直して要素ごとに**
      `exportTol` で突き合わせる(`impl_graded_check` が地盤格子でやっている形をそのまま)。
    ⛔ 止める七つ:
      ① 名簿 ── 土留め13本が**一本残らず**焼き出しに在り、余りが無い
      ② 節点・**建つ区間**の座標が図と一致(⛔ 実長のスカラだけで済ませない)
      ③ 縦断が空でない・刻みが `profileStep` どおり・**列が6列**
      ④ 縦断の**全点 × 全列**が `wall_profile` の引き直しと一致(許容 `exportTol`)
      ⑤ `gapsS`(開口の走り)が `wall_gaps_s` の引き直しと一致
      ⑥ `coping` が数の壁 ── 天端が**全点でその数**
      ⑦ `coping:"stair"` の壁 ── 指し先の石段が解け、天端が**その石段の割付の値そのもの**
         (`stair_spans` の踏面の高さの集合に入る)かつ [`yBot`, `yTop`] の内
    〔記録〕壁ごとの見付高・受け高の範囲と、**裁定 2026-09-09 の判定則**による仕分け:
      見付>0 かつ 受け≦0 → 擁壁として正常 ／ 見付≦0 かつ 受け>0 → **埋まっている壁** ／
      両方≦0 → 段差が無い ／ 両方>0 → 天端より高い土を背負う区間がある。
      ⛔ **どれも⛔にしない** ── 壁の要否は `wall_step_check`(裁定 EDO-0182 (b))、
      天端の決め方は `_pending`「埋まっている土留めの始末」(同 (a))。⛔ 地形を壁に合わせて削らない。
    """
    if not os.path.exists(IMPL_OUT): return ([], [])
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    by = dict((q["name"], q) for q in (im.get("runs") or []) if q.get("of") == "wall")
    bad, note = [], []
    want = [w["name"] for w in d["terraceWalls"]]
    if sorted(by.keys()) != sorted(want):
        bad.append("焼き出しの土留めの名簿が図と違う(焼き %d 本 / 図 %d 本・差 %s)"
                   % (len(by), len(want), "／".join(sorted(set(want) ^ set(by.keys()))) or "並び"))
    COL = ["走り s", "天端", "低い側の地盤", "高い側の地盤", "見付高", "受け高"]
    kind_n = {"擁壁として正常": [], "埋まっている壁": [], "段差が無い": [], "天端より高い土を背負う": []}
    buried = []          # ⭐ **壁ごとの埋没**(名, 埋没点, 全点, 率%, 延長 m)【B-4 検図22巡目】
    for w in d["terraceWalls"]:
        q = by.get(w["name"])
        if q is None: continue
        # ② 節点の座標
        nd = [_w(g, p9) for p9 in wall_nodes(d, w)]
        if q.get("nodes") != nd:
            bad.append("土留め『%s』の節点が焼き出しと図で食い違う(焼き %d 点 / 図 %d 点)"
                       % (w["name"], len(q.get("nodes") or []), len(nd)))
        sw9 = _w_segs(g, w)
        if q.get("segs") != sw9:
            bad.append("土留め『%s』の**建つ区間**の座標が焼き出しと図で食い違う" % w["name"])
        # ③ 縦断
        pr = q.get("profile") or []
        if len(pr) < 2:
            bad.append("土留め『%s』に走りの縦断 `profile` が無い(実装が天端・法尻を"
                       "自力で作ることになる)" % w["name"]); continue
        if abs((q.get("profileStep") or 0) - IMPL_WALL_STEP) > 1e-9:
            bad.append("土留め『%s』の縦断の刻みが %s(図は %g m)"
                       % (w["name"], q.get("profileStep"), IMPL_WALL_STEP))
        # ④ **全点 × 全列**を引き直して突き合わせる(高2 検図21巡目)
        pw = wall_profile(d, g, w, IMPL_WALL_STEP)
        if len(pr) != len(pw):
            bad.append("土留め『%s』の縦断の点の数が焼き %d / 図 %d で食い違う"
                       "(⛔ 間引かれた縦断で石を積ませない)" % (w["name"], len(pr), len(pw)))
        else:
            wc, wat, ncol = 0.0, None, 0
            for r9, r8 in zip(pr, pw):
                if len(r9) != 6:
                    ncol += 1; continue
                for j in range(6):
                    dv = abs(float(r9[j]) - float(r8[j]))
                    if dv > wc: wc, wat = dv, (r8[0], COL[j], r9[j], r8[j])
            if ncol:
                bad.append("土留め『%s』の縦断が **6 列でない**行を %d 行持つ ── 図は "
                           "[s, 天端, 低い側の地盤, 高い側の地盤, 見付高, 受け高](裁定 2026-09-09)"
                           % (w["name"], ncol))
            if wc > IMPL_EXPORT_TOL:
                bad.append("土留め『%s』の縦断が図の算出と **%.3f m** 食い違う"
                           "(許容 `exportTol` %.3f m・走り %.1f m の『%s』欄 焼き %.3f / 図 %.3f)"
                           % (w["name"], wc, IMPL_EXPORT_TOL, wat[0], wat[1], wat[2], wat[3]))
        # ⑤ 開口の走り
        gw = wall_gaps_s(wall_samples(d, g, w, IMPL_WALL_STEP), IMPL_WALL_STEP)
        if (q.get("gapsS") or []) != gw:
            bad.append("土留め『%s』の開口の走り `gapsS` が焼き %s / 図 %s で食い違う"
                       "(⛔ 実装に開口を切り直させない)" % (w["name"], q.get("gapsS"), gw))
        k9 = wall_stair(d, w)
        tops = [r[1] for r in pr]
        if w.get("coping") == "stair":
            # ⑦ 石段の割付そのものか
            if k9 is None:
                bad.append("土留め『%s』は `coping:\"stair\"` だが、天端を引く石段の指し先"
                           "(`copingFrom.kaidan` / `vFrom.kaidan`)が無い — **天端が数値ですら"
                           "ない**まま実装へ渡る" % w["name"]); continue
            if q.get("copingFrom") != k9["name"]:
                bad.append("土留め『%s』の天端の出所が焼き %s / 図 %s で食い違う"
                           % (w["name"], q.get("copingFrom"), k9["name"]))
            sp9, _t9 = stair_spans(k9)
            lv = set([round(k9["yBot"], 6), round(k9["yTop"], 6)]
                     + [round(y9, 6) for _a, _b, y9 in (sp9 or [])])
            off = [t9 for t9 in tops if round(t9, 6) not in lv]
            if off:
                bad.append("土留め『%s』の天端 %d 点が石段『%s』の割付(`stair_spans`)に無い値"
                           "(例 %.3f)— ⛔ 段割りの正典を二つ作らない(2026-08-24 検図 高-4 で"
                           "男坂が 1.34 m 食い違った型)" % (w["name"], len(off), k9["name"], off[0]))
            lo9, hi9 = min(k9["yBot"], k9["yTop"]), max(k9["yBot"], k9["yTop"])
            oob = [t9 for t9 in tops if t9 < lo9 - 1e-6 or t9 > hi9 + 1e-6]
            if oob:
                bad.append("土留め『%s』の天端 %d 点が石段『%s』の [%.2f, %.2f] の外(例 %.3f)"
                           % (w["name"], len(oob), k9["name"], lo9, hi9, oob[0]))
        else:
            # ⑥ 数の天端
            cp9 = float(w.get("coping"))
            off = [t9 for t9 in tops if abs(t9 - cp9) > 1e-6]
            if off:
                bad.append("土留め『%s』の天端 %d 点が宣言 `coping` %.3f と違う(例 %.3f)"
                           % (w["name"], len(off), cp9, off[0]))
        # 〔記録〕**判定則**(裁定 2026-09-09)── 区間ごとに仕分けて数える
        fh = [r[4] for r in pr if len(r) == 6]
        bh = [r[5] for r in pr if len(r) == 6]
        if not fh:
            # ⛔ 6 列を一行も持たない縦断は、ここから先を測れない(既に⛔で名指し済み)。
            #   ⚠ 旧版はここで `min()` が空列で落ち、**⛔ ではなく例外**になっていた
            #   (中2 と同じ型 — 関門が算出の後ろにあると、鳴るはずの所で止まらない)。
            continue
        tal = {"擁壁として正常": 0, "埋まっている壁": 0, "段差が無い": 0, "天端より高い土を背負う": 0}
        for a9, b9 in zip(fh, bh):
            if a9 > 1e-6 and b9 <= 1e-6: tal["擁壁として正常"] += 1
            elif a9 <= 1e-6 and b9 > 1e-6: tal["埋まっている壁"] += 1
            elif a9 <= 1e-6 and b9 <= 1e-6: tal["段差が無い"] += 1
            else: tal["天端より高い土を背負う"] += 1
        top9 = max(tal, key=lambda k8: tal[k8])
        kind_n[top9].append(w["name"])
        # ⭐⭐ **壁ごとの埋没率と延長を数として焼く**【B-4 検図22巡目 → 2026-09-09 十九巡目】──
        #   ⛔ 多数決の仕分けだけだと、⚠ **全長が埋まっている壁と 1 割だけの壁が同じ一語**になる。
        #   ⛔ このまま棟梁へ渡すと**土に埋まった壁が建つ**。⛔ 始末は指図方が決めない。
        _n9 = len(fh)
        _bur = tal["埋まっている壁"]
        if _bur:
            _L9 = pr[-1][0] * _bur / float(_n9)
            buried.append((w["name"], _bur, _n9, _bur * 100.0 / _n9, _L9))
        # ⭐ **両側の地盤が同じ高さの点**= 造成後の平場の中に立つ区間。⚠ ここは見付高が
        #   天端 − 平場 で一定になるが、それは**地盤なりに描いた結果そのもの**であって
        #   旧図の「bench をそのまま法尻に採る」分岐の名残ではない(中4 検図21巡目 → 裁定 A案)。
        nflat = len([1 for r in pr if abs(r[3] - r[2]) < 1e-6])
        note.append("土留め『%s』── 走り **%.1f m**(%d 点・刻み %g m)／ 天端 %.2f〜%.2f m"
                    "(出所 %s)／ 地盤 %.2f〜%.2f m ／ **見付高 %.2f〜%.2f m** ／ "
                    "**受け高 %.2f〜%.2f m** ／ 開口 %d ／ 区間の仕分け %s"
                    " ／ 両側の地盤が同高の点 %d/%d(= 造成後の**平場の中に立つ**区間)"
                    "【算出 — ⛔ 実装が引き直さない。⛔ 6列すべてを `exportTol` で測ってある。"
                    "⭐ 基準面は**造成後 `design_y` 一本**で、両側を `const.wallProbeM` の"
                    "距離で採る(裁定 2026-09-09 = 検図21巡目 A案)】"
                    % (w["name"], pr[-1][0], len(pr), q.get("profileStep"),
                       min(tops), max(tops),
                       ("石段『%s』の割付" % k9["name"]) if k9 is not None else "`coping`",
                       min(r[2] for r in pr), max(r[3] for r in pr),
                       min(fh), max(fh), min(bh), max(bh),
                       len(q.get("gapsS") or []),
                       "・".join("%s %d" % (k8, v8) for k8, v8 in tal.items() if v8),
                       nflat, len(pr)))
    note.append("土留め **%d** 本すべてに走り %g m 刻みの "
                "`[s, 天端, 低い側の地盤, 高い側の地盤, 見付高, 受け高]` を焼き、"
                "**全点 × 全6列**を図の `wall_profile` で引き直して突き合わせた"
                "(うち天端が**石段の割付からの従属値**の壁 %d 本)【算出 — 高2 検図21巡目。"
                "⛔ 天端だけを測る版へ戻さない】"
                % (len(want), IMPL_WALL_STEP,
                   len([w for w in d["terraceWalls"] if w.get("coping") == "stair"])))
    note.append("**判定則による壁の仕分け**(区間の多数決)── " + " ／ ".join(
        "%s **%d** 本%s" % (k8, len(v8), ("(%s)" % "・".join(v8) if v8 else ""))
        for k8, v8 in kind_n.items())
        + "【算出 — 裁定 2026-09-09 普請奉行(検図21巡目 A案)。⛔ ⛔にしない ── "
          "壁の要否は検査『埋まっている区間に段差が在るか』、天端の決め方は "
          "`_pending`「埋まっている土留めの始末」(裁定 EDO-0182)。⛔ 地形を壁に合わせて削らない】")
    # ⭐⭐ **埋没は率と延長で刷る**【B-4 検図22巡目 → 2026-09-09 十九巡目】── ⛔ 多数決の一語では
    #   『全長が埋まる壁』と『一部だけの壁』が同じに見える。⛔ **この数を見てから裁くこと。**
    if buried:
        note.append("**埋まっている区間(見付高 ≦ 0 かつ 受け高 > 0)の壁ごとの内訳** ── "
                    + " ／ ".join("%s **%.0f%%**(%d/%d 点・**%.1f m**)" % (q[0], q[3], q[1], q[2], q[4])
                                  for q in sorted(buried, key=lambda r: -r[3]))
                    + " ／ **合計 %.1f m**【算出 — B-4 検図22巡目 → 2026-09-09。"
                      "⛔⛔ **このまま棟梁へ渡すと土に埋まった壁がこの延長ぶん建つ。**"
                      "⛔ 実装の着手前に決着が要る(`_pending`「埋まっている土留めの始末」)── "
                      "裁定 EDO-0182 ── (a) 天端 = max(石段の割付, 外側の地盤 + 天端の出)、"
                      "(b) 段差の無い区間は落とす。⚠ **天端の出が未決のため (a) は未適用**。"
                      "⛔ 地形を壁に合わせて削らない】" % sum(q[4] for q in buried))
    else:
        note.append("埋まっている区間(見付高 ≦ 0 かつ 受け高 > 0)── **0 本・0.0 m**"
                    "【算出 — ⛔ 0 件は合格ではなく未測定なので、**測った物差し**を刷る】")
    return bad, note


def wall_step_check(d, g):
    """**埋まっている区間に『段差が在るか』**── 壁の要否の名簿【裁定 EDO-0182 (b) 普請奉行】。

    ⭐ 判定則は裁2 の二量のまま(見付高 = 天端 − 低い側 ／ 受け高 = 高い側 − 天端)。
      『埋まっている』(見付高 ≦ 0 かつ 受け高 > 0)点を、**両側の地盤のどちらが天端より上か**で割る:
      ・**両側**(見付高 < 0)── 天端の両側とも地盤が上 = その位置に壁の段差が無い ⇒ **壁は要らない**
      ・**片側**(見付高 = 0)── 片側だけ地盤が上 = 段差は在る ⇒ 壁は要る。天端の決め方は (a) と同じ
        (`_pending`「埋まっている土留めの始末」)
    ⛔ 一括で短縮も削除もしない ── 区間ごとに名簿を刷る。⛔ 地形を壁に合わせて削らない。
    ⛔ 止める: **数の天端**(`coping` が数)の壁の**建つ区間**に『両側』の点が残る
      (要らない壁が建つ)。⚠ `coping:"stair"` の側壁は (a) の天端で始末するので〔記録〕。
    ⭐ 数は `wall_samples` を `wall_profile` と同じ桁で丸めて読む(⛔ 物差しを二つにしない)。
    """
    E9 = 1e-6
    bad, note = [], []
    tot = {"両側": 0.0, "片側": 0.0}
    for w in d["terraceWalls"]:
        sm = wall_samples(d, g, w, IMPL_WALL_STEP)
        if len(sm) < 2: continue
        n9 = len(sm)
        Ls = sm[-1][0]
        two, one, two_built = 0, 0, 0
        for q9 in sm:
            fh, bh = round(q9[4], 3), round(q9[5], 3)
            if not (fh <= E9 and bh > E9): continue
            if fh < -E9:
                two += 1
                if q9[-1]: two_built += 1
            else:
                one += 1
        if not (two or one): continue
        Lt, Lo = Ls * two / float(n9), Ls * one / float(n9)
        tot["両側"] += Lt; tot["片側"] += Lo
        stair = w.get("coping") == "stair"
        if two_built and not stair:
            bad.append("土留め『%s』の**建つ区間**に、天端の両側とも地盤が上の点(= 段差が無い)が "
                       "%d 点残る ── ⛔ 要らない壁が建つ。区間ごとに落とす【裁定 EDO-0182 (b)】"
                       % (w["name"], two_built))
        note.append("土留め『%s』の埋まっている点 %d/%d ── **片側 %d 点・%.1f m**(段差が在る ⇒ 壁は要る・"
                    "天端は (a) の扱い)／ **両側 %d 点・%.1f m**(段差が無い ⇒ 壁は要らない%s)"
                    "【算出 — 裁定 EDO-0182 (b)】"
                    % (w["name"], one + two, n9, one, Lo, two, Lt,
                       "。⚠ 石段の側壁は (a) の天端で始末するので〔記録〕" if (two and stair) else ""))
    note.append("埋まっている区間の段差の名簿 ── **片側 %.1f m ／ 両側 %.1f m**"
                "【算出 — 裁定 EDO-0182 (b)。⛔ 両側の区間だけが『壁が要らない』】"
                % (tot["片側"], tot["両側"]))
    return bad, note


def impl_planting_check(d, g):
    """**焼き出した木が、指図の宣言した面と離れを守っているか**【庭方 2026-09-08 十六巡目】。

    ⭐ **点になって初めて見える欠陥を、点で捕まえる。**面と密度の表は 15 巡のあいだ⛔ 0 件だったが、
    焼き出しの点を測ったら **勝手道の上に 84 本・芯々の下限を割る対が 229・設計した塊の中へ帯から
    40 本・林縁に高木 16 本**が出た。⛔ **0 件は合格ではなく未測定**(規則19)。
    ⛔ **標本で済ませない** — 全点 × 全障害物を突き合わせる。
    ⛔ **測るのは焼き出し**(`sanno_impl.json`)── 実装が実際に置く点そのもの。鮮度は
    `impl_fresh_check` が別に見張る。

    ⛔ 止める七つ:
      ① **勝手道の敷きの上に幹が立つ**(A-1)⛔ 動線図が道として描く道を植栽が塞がない
      ② **芯々の下限を割る対**(A-2)⛔ 帯どうし・帯と塊が互いを知らないまま撒かない
      ③ **設計された塊の輪郭の中に帯の撒き木**(A-3)⛔ 額縁・主景を撒き木で埋めない
      ④ **林縁(`rinen`)の中に高木**(A-4)⛔ 宣言を逆向きに破らない
      ⑤ **石段の敷きの上に幹**(A-5)⛔ 折れ線の節に楔形の穴を残さない
      ⑥ **柵・板塀・土留めの線に幹**(B-4)⛔ 柵が建たない所に木を立てない
      ⑦ **`scaleXZ` を持たない点**(B-2)⛔ 図が測る樹冠と現物の樹冠を別にしない
      ⑧ **設計された塊の点が、その塊の属する面の退避に載る**(低2 検図20巡目 → 2026-09-09)
         ⛔ 塊の候補セルは `poly_scan`(箱)だけで作っていて**退避を一度も引いていない**ので、
         箱を動かせば黙って退避の中へ入る。撒き木は `scatter_pts` が退避を引くのに、
         **意匠で位置を決めた塊だけが素通り**していた ── 面ではなく**点**で捕まえる
    〔記録〕落葉の林冠面積の割合(B-1)・前庭の低木の千鳥(B-5)・見所の眼高と向き(B-3)。
    """
    if not os.path.exists(IMPL_OUT): return ([], [])
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    P = (im.get("planting") or {}).get("points") or []
    if not P: return (["算出物に撒いた木 `planting.points` が無い"], [])
    bad, note = [], []
    ken = d["const"]["ken"]
    pack = d["planting"]["plantRule"]["packRatio"]
    uv = [(q["u"], q["v"]) for q in P]

    def tally(shapes, what):
        hit = {}
        for i, p in enumerate(uv):
            nm = shape_hit(p, shapes)
            if nm: hit.setdefault(nm, []).append(P[i]["name"])
        n = sum(len(v) for v in hit.values())
        return n, hit

    # ① 勝手道 ── **肩を 0 にして敷きそのもの**で測る(⛔ 肩は層別なので別に刷る)
    n1, h1 = tally(kattemichi_apron_shapes(d, g, 0.0), "勝手道")
    (bad if n1 else note).append(
        "**勝手道の敷きの上に立つ幹 %d 本**%s【算出 — ⛔ 動線図が道として描く九十九折を植栽が"
        "塞がない(A-1 庭方 2026-09-08。旧図は 84 本・芯からの最短 0.01 m)】"
        % (n1, ("── " + " ／ ".join("%s %d本" % (k, len(v)) for k, v in h1.items())) if n1 else ""))
    # ② 芯々の下限 ── 同じ林冠(松+落葉)・中木・低木の三つの群
    def bucket(lay): return "canopy" if lay in ("松", "落葉") else lay

    def rmin_of(p):
        grp, lay = p["group"], p["layer"]
        for b in d["slopeBands"]:
            nm = "社叢 帯%d %s" % (b["band"], b["name"])
            if grp == nm + " の林縁":
                dr = rinen_dens(d, b, lay)
                return (math.sqrt(100.0 / dr) * pack / ken) if dr else None
            if grp != nm: continue
            if lay in ("松", "落葉") and b.get("spacing"):
                sp = b["spacing"]
                return (sp[0] + sp[1]) / 2.0 * pack / ken
            q = b.get({"中木": "chubokuPer100", "低木": "teibokuPer100"}.get(lay)) or [0, 0]
            dm = (q[0] + q[1]) / 2.0
            return (math.sqrt(100.0 / dm) * pack / ken) if dm > 0 else None
        for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
            for c in gd.get("clusters", []):
                if grp == "%s／%s" % (gd["name"], c["name"]):
                    sp = cluster_spacing(d, c)
                    return (sp * pack) if sp else None
        return None
    grp = {}
    for i, p in enumerate(P):
        if p["group"].endswith("(一本立ち)") or "前庭の帯" in p["group"]: continue
        r = rmin_of(p)
        if r is None: continue
        grp.setdefault(bucket(p["layer"]), []).append((uv[i], r, p["name"]))
    # ⭐ **設計された塊どうしの対は別に数える**【中6 検図21巡目 → 2026-09-09】── ⛔ どちらも
    #   意匠が箱を置いた塊なので、⛔ 撒き方(`_scatter_take`)では直せない ── 直すのは箱か役で、
    #   それは庭方の意匠である。⛔ **黙って除かない**:別の欄で数え、猶予の指し先を要求する。
    own9 = set()
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []): own9.add("%s／%s" % (gd["name"], c["name"]))
    gof = dict((p["name"], p["group"]) for p in P)
    n2, w2, n2c, w2c = 0, None, 0, None
    for bk, ps in grp.items():
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                dd = math.hypot(ps[i][0][0] - ps[j][0][0], ps[i][0][1] - ps[j][0][1])
                th = min(ps[i][1], ps[j][1])
                if dd >= th - 1e-9: continue
                ga, gb = gof.get(ps[i][2]), gof.get(ps[j][2])
                if ga in own9 and gb in own9 and ga != gb:
                    n2c += 1
                    if w2c is None or dd < w2c[0]: w2c = (dd, ps[i][2], ps[j][2], th, ga, gb)
                else:
                    n2 += 1
                    if w2 is None or dd < w2[0]: w2 = (dd, ps[i][2], ps[j][2], th)
    (bad if n2 else note).append(
        "**芯々の下限を割る対 %d**%s【算出 — 群は『松+落葉(同じ林冠)』『中木』『低木』の三つ。"
        "⛔ 帯どうし・帯と塊が互いを知らないまま撒かない(A-2 庭方 2026-09-08。旧図は 229 対・"
        "最短 0.37 m で、10〜12 m の松が二本同じ株から生えて見えた)。"
        "⚠ **設計された塊どうしの対はこの数に入れない**(下の欄で数える)】"
        % (n2, ("── 最短 %.2f m(『%s』×『%s』／ 下限 %.2f m)"
                % (w2[0] * ken, w2[1], w2[2], w2[3] * ken)) if w2 else ""))
    if n2c:
        m9 = ("**設計された塊どうしが継ぎ目で融合している対 %d** ── 最短 %.2f m"
              "(『%s』(%s)×『%s』(%s)／ 下限 %.2f m)。⛔ 撒き方では直せない ── "
              "どちらも意匠が箱を置いた塊なので、直すのは**箱か役**である(中6 検図21巡目)"
              % (n2c, w2c[0] * ken, w2c[1], w2c[4], w2c[2], w2c[5], w2c[3] * ken))
        pr9 = (d["planting"]["plantRule"].get("clusterOverlapPendingRef") or None)
        if pr9 and pr9 in (d.get("_pending") or {}):
            note.append("⚠ " + m9 + "。⭕ **猶予**『%s』の内(当たり先は庭方)【算出】" % pr9)
        else:
            bad.append(m9)
    else:
        # ⭐⭐ **物差しの名を報告の言葉に合わせる**【B-6 検図22巡目 → 2026-09-09 十九巡目】──
        #   ⚠ 『0 対』は**宣言した間合い(芯々の下限)の物差しでの 0 対**であって、
        #   ⛔ **樹冠が離れたという意味ではない。**⛔ 次に読む人が「樹冠が離れた」と読む。
        #   ⭕ そこで**樹冠の重なりも同じ行で数える**(⛔ ⛔にしない ── 間合いは庭方の受入値で
        #   通っており、留めの木の作法として許容されている)。
        crn = dict((q["name"], (q.get("crownM") or 0.0) / 2.0 / ken) for q in P)
        ov9 = []
        for bk, ps in grp.items():
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    ga, gb = gof.get(ps[i][2]), gof.get(ps[j][2])
                    if not (ga in own9 and gb in own9 and ga != gb): continue
                    dd = math.hypot(ps[i][0][0] - ps[j][0][0], ps[i][0][1] - ps[j][0][1])
                    rr = crn.get(ps[i][2], 0.0) + crn.get(ps[j][2], 0.0)
                    if dd < rr - 1e-9:
                        ov9.append(((rr - dd) * ken, ps[i][2], ps[j][2], ga, gb))
        note.append("設計された塊どうし ── **宣言した間合い(芯々の下限)を全対が通る:融合 0 対**"
                    "(測った塊 %d)。%s【算出 — 中6 検図21巡目 / 言葉の是正 = B-6 検図22巡目 "
                    "2026-09-09。⛔⛔ **『0 対』は間合いの物差しでの 0 対であって、"
                    "『樹冠が離れた』という意味ではない。**⛔ 0 件は合格ではなく未測定】"
                    % (len(own9),
                       ("⚠ **樹冠はなお重なる %d 対** ── %s(留めの木の作法として許容・"
                        "⛔ 数を動かす件ではない)"
                        % (len(ov9), " ／ ".join("『%s』×『%s』 **%.2f m**" % (q[1], q[2], q[0])
                                                 for q in sorted(ov9, reverse=True)[:4])))
                       if ov9 else "⭕ 樹冠の重なりも 0 対"))
    # ③ 塊の輪郭の中の撒き木
    n3 = {}
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            own = "%s／%s" % (gd["name"], c["name"])
            for Q in cluster_polys(c):
                for i, p in enumerate(P):
                    if p["group"] == own or not p["group"].startswith("社叢 帯"): continue
                    if in_poly(uv[i], Q): n3[c["name"]] = n3.get(c["name"], 0) + 1
    (bad if n3 else note).append(
        "**設計された塊の輪郭の中に立つ帯の撒き木 %d 本**%s【算出 — ⛔ 額縁(男坂の見切り)・"
        "路の終端(辻の留め)・境内の立木を撒き木で埋めない(A-3 庭方 2026-09-08。旧図は"
        "『男坂の見切り』へ 24 本・『辻の留め』へ 3 本・境内の立木へ 13 本)】"
        % (sum(n3.values()),
           ("── " + " ／ ".join("『%s』%d本" % q for q in n3.items())) if n3 else ""))
    # ④ 林縁の中の高木
    n4 = []
    for b in d["slopeBands"]:
        rin = b.get("rinen")
        if not rin: continue
        E = rinen_edges(d, g, b)
        nm = "社叢 帯%d %s" % (b["band"], b["name"])
        k, mn = 0, None
        for i, p in enumerate(P):
            if p["group"] != nm or p["layer"] not in ("松", "落葉"): continue
            dd = min(_pt_seg(uv[i], a, c) for a, c in E)
            if dd <= rin["toKen"]:
                k += 1
                mn = dd if mn is None else min(mn, dd)
        n4.append((b["band"], k, mn, len(E)))
    for bn, k, mn, ne in n4:
        (bad if k else note).append(
            "**帯%d の林縁(境から %g 間まで)の中の高木 %d 本**%s ／ 林縁が測る社地の辺 %d 本"
            "【算出 — ⛔ 宣言 `takagiPer100: 0.0` を逆向きに破らない(A-4 庭方 2026-09-08。"
            "旧図は帯4 に 16 本・最短 0.09 m ／ 帯3 の『南面』は生成器に語すら無かった)】"
            % (bn, (b for b in d["slopeBands"] if b["band"] == bn).__next__()["rinen"]["toKen"],
               k, ("── 最短 %.3f 間" % mn) if mn is not None else "", ne))
    # ⑤ 石段の敷き
    n5, h5 = tally(kaidan_apron_shapes(d), "石段")
    (bad if n5 else note).append(
        "**石段の敷きの上に立つ幹 %d 本**%s【算出 — ⛔ 折れ線の**内側の節**に楔形の穴を残さない"
        "(A-5 庭方 2026-09-08。旧図は女坂の折れと端で 3 本、うち丈 12.8 m の落葉が"
        "敷きの半幅の内側に立っていた)】"
        % (n5, ("── " + " ／ ".join("%s %d本" % (k, len(v)) for k, v in h5.items())) if n5 else ""))
    # ⑥ 柵・板塀・土留め(線そのもの。肩は層別なので別に測る)
    n6, h6 = tally(kakoi_avoid_shapes(d, 0.0), "囲い")
    (bad if n6 else note).append(
        "**柵・板塀・土留めの線に幹が載る %d 本**%s【算出 — 10〜12 m の松の幹は径 0.3〜0.4 m あり、"
        "⛔ **柵はそこに建たない**(B-4 庭方 2026-09-08。旧図は `Saku_Sando` に8本・最短 0.09 m ／ "
        "`Ita_Keidai` に22本 ／ `TW_Zentei_E` に5本)】"
        % (n6, ("── " + " ／ ".join("%s %d本" % (k, len(v)) for k, v in h6.items())) if n6 else ""))
    # ⑦ `scaleXZ` の焼き
    need = [p["name"] for p in P
            if p["layer"] in _LAY_KIND and p.get("scaleXZ") is None]
    (bad if need else note).append(
        "**`scaleXZ` を持たない点 %d(松・落葉・中木)**%s【算出 — 樹冠 = 部材の樹冠 × `scaleXZ` に "
        "①退避の可否 ②参道への張り出しの条項 ③石段の肩の上限 が全部乗るので、⛔ 焼かなければ"
        "**図が測った樹冠と現物の樹冠が別になる**(B-2 庭方 2026-09-08)】"
        % (len(need), ("── 例 " + "・".join(need[:3])) if need else ""))
    # ⑧ 塊の点 × その塊の属する面の退避(低2 検図20巡目 → 2026-09-09)
    _sc = {}

    def sc_of(name):
        if name not in _sc: _sc[name] = avoid_shapes(d, g, name)
        return _sc[name]
    n8, t8 = {}, 0
    for gd in d["gardens"] + d["slopeBands"] + view_holders(d):
        for c in gd.get("clusters", []):
            own = "%s／%s" % (gd["name"], c["name"])
            for i, p in enumerate(P):
                if p["group"] != own: continue
                t8 += 1
                # ⛔ 面の名簿を手で持たない ── 帯4 は多角形を持つ帯、帯1〜3 と視線の塊は
                #    斜面(層ごとの肩)、区は境内の立木の面
                scope = ("obi4" if gd.get("uv") else
                         "keidai" if gd.get("kind") else "obi123:" + p["layer"])
                nm9 = shape_hit(uv[i], sc_of(scope))
                if nm9: n8.setdefault("%s ⟂ %s" % (own, nm9), []).append(p["name"])
    (bad if n8 else note).append(
        "**設計された塊の点のうち、その塊が属する面の退避に載るもの %d 本**(測った塊の点 %d)"
        "%s【算出 — ⛔ 塊の候補セルは `poly_scan`(箱)だけで作られていて**退避を一度も"
        "引いていない**ので、箱を動かせば黙って入る(低2 検図20巡目 → 2026-09-09)。"
        "⛔ 0 件は合格ではなく未測定 — 測った点の数を必ず添える】"
        % (sum(len(v) for v in n8.values()), t8,
           ("── " + " ／ ".join("%s %d本" % (k9, len(v9)) for k9, v9 in n8.items())) if n8 else ""))
    # 〔記録〕B-1 落葉の林冠面積の割合
    A = {"松": 0.0, "落葉": 0.0}
    N = {"松": 0, "落葉": 0}
    for p in P:
        if p["layer"] not in A or not p["group"].startswith("社叢 帯"): continue
        cr = p.get("crownM")
        if cr is None: continue
        A[p["layer"]] += math.pi * (cr / 2.0) ** 2
        N[p["layer"]] += 1
    tA, tN = sum(A.values()), sum(N.values())
    if tA > 0:
        note.append("社叢の帯の高木 ── 松 %d 本(%.1f%%)が樹冠面積の **%.1f%%**、落葉 %d 本(%.1f%%)が"
                    " **%.1f%%**【算出 — ⛔ 判定しない(意匠は庭方)。⭐ 旧図は落葉が 35.6% で、"
                    "**南からの立面で林の天端を作っていたのが落葉**だった(B-1)。`scaleRule.rakuyo."
                    "scaleXZ` / `chuboku.scaleXZ` を宣言して部材の**野に一本で育った形**を狭めた】"
                    .replace("35.6%", "35.6%%")
                    % (N["松"], 100.0 * N["松"] / tN, 100.0 * A["松"] / tA,
                       N["落葉"], 100.0 * N["落葉"] / tN, 100.0 * A["落葉"] / tA))
    # 〔記録〕B-5 前庭の低木の千鳥
    zs = [p for p in P if "前庭の帯" in p["group"] and p["layer"] == "低木"]
    if zs:
        cols = sorted(set(round(p["u"], 3) for p in zs))
        note.append("前庭の帯の低木 %d 本 ── u の相異なる列 **%d**【算出 — ⛔ 面も本数も芯々も"
                    "変えていない。⭐ 旧図は u 3 列 × v 1.2 m ちょうど刻みの**直交格子**で、"
                    "図の中で唯一、目に格子と映った(B-5 庭方 2026-09-08)】" % (len(zs), len(cols)))
    # 〔記録〕B-3 見所の眼高と向き
    for vp in ((im.get("setae") or {}).get("viewpoints") or []):
        src = ([q for q in d.get("viewpoints", []) if q["name"] == vp["name"]] or [{}])[0]
        lk = vp.get("look") or {}
        if vp.get("eyeH") is None or not lk:
            bad.append("見所『%s』の %s が焼かれていない — ⛔ **検証レンダを図の見所に合わせられない**"
                       "(B-3 庭方 2026-09-08・規則19)"
                       % (vp["name"], "眼高 `eyeH`" if vp.get("eyeH") is None else "向き `look`"))
            continue
        dd = src.get("_dirDeg")
        gap = None if dd is None else abs((lk["azDeg"] - dd + 180.0) % 360.0 - 180.0)
        note.append("見所『%s』── 眼高 **%.2f m**(%s)／ 向き **%.1f°**(真北から時計回り・出所 %s)"
                    "%s【算出 — ⛔ `dir` の語を書き換えない(向きは庭方の意匠)】"
                    % (vp["name"], vp["eyeH"], src.get("_eyeFrom", "—"), lk["azDeg"],
                       lk.get("from", "—"),
                       "" if gap is None else
                       (" ／ 散文 `dir`『%s』= %.1f° と **%.1f° 食い違う**" % (src.get("dir"), dd, gap)
                        if gap > 11.25 else " ／ 散文 `dir`『%s』と %.1f° 差(⭕ 一目盛の内)"
                        % (src.get("dir"), gap))))
    return bad, note


def impl_graded_check(d, g):
    """**焼き出しの造成後の地盤が、図の算出(`design_y`)と同じ物か**【規則19 → 2026-09-08】。

    ⛔ 焼き出しと図が別々の数を持つ道を塞ぐ ── 切盛図・断面・社地外の集計は `design_y` を
      毎回呼ぶが、実装は焼いた格子しか見ない。**同じ関数から出ていること**を確かめる。
    ⛔ **標本で済ませない**【破壊試験 2026-09-08】── 400 点を抜いた版では、地盤を 1 セル
      0.05 m ずらしても・造成する/しないを 1 セル入れ替えても**鳴らなかった**(見ているのは
      全体の 0.7%)。全セルを引き直して突き合わせる(9 秒)。
    ⛔ 値だけでなく **null の一致**も見る ── null は『造成しない』であって欠測ではないので、
      片方だけ値を持てば実装はそこを平らに均してしまう。
    """
    if not os.path.exists(IMPL_OUT): return ([], [])
    im = json.load(open(IMPL_OUT, encoding="utf-8"))
    gr = im.get("graded") or {}
    if not gr.get("h"): return (["算出物に造成後の地盤 `graded` が無い"], [])
    nx, nz, stp = gr["nx"], gr["nz"], gr["step"]
    sv9 = dict(_LAND)                       # ⛔ 検査が図の覚え書きを書き換えない(引いたら戻す)
    worst, wat, wnul, nmis, n = 0.0, None, None, 0, 0
    for iz in range(nz):
        row = gr["h"][iz]
        for ix in range(nx):
            was = row[ix]
            got = _design_y_cold(d, g, gr["x0"] + ix * stp, gr["z0"] + iz * stp)
            n += 1
            if (was is None) != (got is None):
                nmis += 1
                if nmis <= 3:
                    wnul = "(%.1f, %.1f) 焼き %s / 図 %s" % (gr["x0"] + ix * stp,
                                                            gr["z0"] + iz * stp, was, got)
                continue
            if was is None: continue
            dv = abs(was - got)
            if dv > worst:
                worst = dv
                wat = "(%.1f, %.1f) 焼き %.3f / 図 %.3f" % (gr["x0"] + ix * stp,
                                                           gr["z0"] + iz * stp, was, got)
    _LAND.clear(); _LAND.update(sv9)
    dr9 = gr.get("orderDrift") or {}
    bad = []
    if nmis:
        bad.append("焼き出しの地盤と図の設計面で**造成する/しないの別が %d セルで食い違う**"
                   "(全 %d セル・例 %s)— `--export-impl` を回し直す" % (nmis, n, wnul))
    if worst > IMPL_EXPORT_TOL:
        bad.append("焼き出しの地盤が図の設計面と **%.3f m** 食い違う(許容 `exportTol` %.3f m・%s)"
                   % (worst, IMPL_EXPORT_TOL, wat))
    note = ["焼き出しの造成後の地盤 ── **全 %s セル**を `design_y` で引き直して突き合わせ、"
            "最大の差 **%.4f m**(許容 `exportTol` %.3f m)／ 造成する・しないの別の食い違い **%d** セル"
            "【算出 — ⛔ 図と焼き出しが別々の数を持つ道を塞ぐ検査。⛔ 標本で済ませない】"
            % (format(n, ","), worst, IMPL_EXPORT_TOL, nmis),
            "**`design_y` が呼び出し順で答えを変えるセル** ── 全 %s セル中 **%d** セル"
            "(値そのものの差は最大 %.4f m)【算出 — 数は焼き出しの `graded.orderDrift` が持つ。"
            "⛔ ここに数を書かない】。⭕ **0 が正**【低1 検図20巡目 → 2026-09-09】── "
            "`slope_lands` の覚え書きの鍵を『法尻の点 + 向き + 面の高さ』まで完全にした"
            "(旧図は法尻の点だけを鍵にし、同じ法尻へ別の向きから当てた答えを再利用していた。"
            "食い違った 23 セルはすべて**図の側にだけ盛土を生やす向き**で、体積 8.18 m³)。"
            "⛔ 直したから測るのをやめる、をしない"
            % (format(dr9.get("cells", 0), ","), dr9.get("nullFlip", 0), dr9.get("maxDiff", 0.0))]
    if dr9.get("nullFlip") or (dr9.get("maxDiff") or 0.0) > 0.0:
        bad.append("`design_y` が**呼び出し順で答えを変える** ── %d セルで『造成する/しない』が"
                   "入れ替わり、値の差は最大 %.4f m。覚え書き `slope_lands`/`_LAND` の鍵に"
                   "**答えを決める引数が全部入っていない**(低1 検図20巡目 → 2026-09-09)"
                   % (dr9.get("nullFlip", 0), dr9.get("maxDiff", 0.0)))
    # ⭕ **焼き出しの世界座標を、図が引くのと同じ式で引き直して一つ残らず突き合わせる**
    #    【高1 検図21巡目 → 2026-09-09。20巡目 中1 の指示漏れの再掲でもある】。
    #    ⚠ **旧版はスカラの実長 `lenM` しか見ていなかった** ── +10 m 平行移動しても実長は
    #    変わらないので、⛔ 塀・石段・門・動線・玉垣・点景・**撒いた木 1,735 本**のどれが
    #    丸ごと別の所へ移っても鳴らなかった(破壊試験7本すべて無音)。⛔ **実装が読むのは
    #    この座標そのもの**である。⚠ 木は `u`/`v` だけが輪に入っていて `world` は素通り
    #    だった ── `u`/`v` が正しくても `world` が別なら全部ずれて建つ。
    def _xy_bad(a9, b9):
        """入れ子の座標列の**最大の差**。形が違えば None(=形の食い違い)。"""
        if isinstance(a9, (int, float)) and isinstance(b9, (int, float)):
            return abs(float(a9) - float(b9))
        if not isinstance(a9, list) or not isinstance(b9, list) or len(a9) != len(b9):
            return None
        w9 = 0.0
        for p9, q9 in zip(a9, b9):
            r9 = _xy_bad(p9, q9)
            if r9 is None: return None
            w9 = max(w9, r9)
        return w9

    def _cmp(label, got, wnt):
        """焼きと図の座標を突き合わせる。⛔ 許容は `exportTol`(同じ式から出るので丸めだけ)。"""
        r9 = _xy_bad(got, wnt)
        if r9 is None:
            bad.append("%s の座標の**形**が焼き出しと図で違う(焼き %s / 図 %s)"
                       % (label, json.dumps(got, ensure_ascii=False)[:60],
                          json.dumps(wnt, ensure_ascii=False)[:60]))
            return False
        if r9 > IMPL_EXPORT_TOL:
            bad.append("%s の**世界座標**が焼き出しと図で **%.3f m** 食い違う"
                       "(許容 `exportTol` %.3f m)— ⛔ 実装が読むのはこの座標そのもの"
                       % (label, r9, IMPL_EXPORT_TOL))
            return False
        return True

    by = dict((q["name"], q) for q in (im.get("runs") or []))
    nb, ncmp = 0, 0
    for o in d["runs"]:
        q = by.get(o["name"])
        if q is None:
            bad.append("焼き出しに囲い『%s』が無い" % o["name"]); continue
        L9 = run_len_ken(o) * d["const"]["ken"]
        if abs((q.get("lenM") or 0.0) - L9) > 1e-3:
            bad.append("囲い『%s』の実長が焼き %.3f m / 図 %.3f m で食い違う"
                       % (o["name"], q.get("lenM"), L9))
        # ⭕ **節点と『建つ区間』の座標**(⛔ スカラの実長で済ませない)
        nd9 = [_w(g, q9) for q9 in (o.get("pts") or ([o["a"], o["b"]] if o.get("a") else []))]
        _cmp("囲い『%s』の節点" % o["name"], q.get("nodes"), nd9); ncmp += 1
        _cmp("囲い『%s』の建つ区間" % o["name"], q.get("segs"), _w_segs(g, o)); ncmp += 1
        nb += 1
    note.append("囲い **%d** 本 ── 開口を抜いた実長・**節点の世界座標**・**建つ区間の世界座標**を"
                "突き合わせた(⛔ `Ita_Keidai`・`Saku_SW`・`Saku_Sando` は指図が座標を持たない"
                "生成物なので、ここが黙ると塀が丸ごと別の所に立つ)【算出 — 高1 検図21巡目】" % nb)
    # ⭕ 石段・門・動線・玉垣 ── どれも `_w(g, uv)` で引き直す
    sby = dict((q["name"], q) for q in (im.get("stairs") or []))
    for k9 in d["kaidans"]:
        q = sby.get(k9["name"])
        if q is None:
            bad.append("焼き出しに石段『%s』が無い" % k9["name"]); continue
        P9 = [tuple(p9) for p9 in (k9.get("pts") or [k9["a"], k9["b"]])]
        _cmp("石段『%s』の折れ線" % k9["name"], q.get("nodes"), [_w(g, p9) for p9 in P9]); ncmp += 1
    gby = dict((q["name"], q) for q in (im.get("gates") or []))
    for gt in d["gates"]:
        q = gby.get(gt["name"])
        if q is None:
            bad.append("焼き出しに門『%s』が無い" % gt["name"]); continue
        _cmp("門『%s』の芯" % gt["name"], q.get("world"), _w(g, (gt["u"], gt["v"]))); ncmp += 1
    rby = dict((q["name"], q) for q in (im.get("routes") or []))
    for rt in d.get("routes", []):
        q = rby.get(rt["name"])
        if q is None:
            bad.append("焼き出しに動線『%s』が無い" % rt["name"]); continue
        wp = [[round(p9[0], 3), round(p9[1], 3)] if rt.get("world") else _w(g, p9)
              for p9 in rt["pts"]]
        _cmp("動線『%s』の折れ線" % rt["name"], q.get("world"), wp); ncmp += 1
    tw = []
    for gd in d["gardens"]:
        if not gd.get("tamagaki"): continue
        for nm9, a9, b9, _f9, _l9, rs9 in tamagaki_edges(d, gd):
            tw.append(("%s／%s" % (gd["name"], nm9), _w(g, a9), _w(g, b9),
                       [[_w(g, r9[0]), _w(g, r9[1])] for r9 in rs9]))
    tby = dict(("%s／%s" % (q.get("garden"), q.get("edge")), q) for q in (im.get("tamagaki") or []))
    for nm9, a9, b9, rs9 in tw:
        q = tby.get(nm9)
        if q is None:
            bad.append("焼き出しに玉垣の辺『%s』が無い" % nm9); continue
        _cmp("玉垣『%s』の両端" % nm9, [q.get("a"), q.get("b")], [a9, b9]); ncmp += 1
        _cmp("玉垣『%s』の建つ区間" % nm9, q.get("segs"), rs9); ncmp += 1
    note.append("石段 **%d** ／ 門 **%d** ／ 動線 **%d** ／ 玉垣の辺 **%d** ── "
                "折れ線・芯・両端・建つ区間の**世界座標**を `_w(g, uv)` で引き直して突き合わせた"
                "【算出 — 高1 検図21巡目。⛔ 名簿の一致だけで済ませない】"
                % (len(d["kaidans"]), len(d["gates"]), len(d.get("routes", [])), len(tw)))
    # ⭕ **撒いた木の数が予算表(`plant_budget`)と層ごとに一致するか**。
    #   ⛔ 焼き出しが図より一本でも多い/少ないと、三角数の見積りも林冠の読みも別物になる。
    #   ⚠ 帯の塊(帯4)は**帯の本数の内訳**なので予算表には足されない — 焼き出しの側でも
    #     同じだけ帯から差し引いてある(⛔ 二重に数えない)。
    got9 = {}
    for q in (im.get("planting") or {}).get("points") or []:
        got9[q.get("layer")] = got9.get(q.get("layer"), 0) + 1
    for lay, nsc, nsg, _t, _p, _ps in plant_budget(d, g):
        if got9.get(lay, 0) != nsc + nsg:
            bad.append("焼き出しの %s が **%d 本**、図の予算表は %d 本(撒く %d + 一本立ち %d)"
                       " — 数が合わない" % (lay, got9.get(lay, 0), nsc + nsg, nsc, nsg))
    note.append("焼いた木 ── " + " ／ ".join(
        "%s **%d** 本" % (lay, got9.get(lay, 0)) for lay in _LAYS)
        + "(⛔ 予算表と層ごとに一致すること。⛔ 実装側で撒き直さない — 別の乱数で撒けば"
          "退避も林冠も図が測った物と別になる)【算出】")
    # ⭕ **設え(点景・踏石・井戸屋形・区の輪郭・見所)の名簿が図と一致するか**。
    #   ⛔ 数だけでなく**名**で突き合わせる — 数が合っていても別の物が入れ替わっていれば
    #     実装は違う場所へ据える(名は総当たり・退避・断面の marks と同じ呼び名である)。
    se = im.get("setae") or {}
    _fu = fumiishi_rects(d)
    for key, want in (("props", [nm for nm, _Q in prop_rects(d)]),
                      ("fumiishi", [q[0] for q in _fu]),
                      ("gardens", [gd["name"] for gd in d["gardens"]]),
                      ("viewpoints", [vp["name"] for vp in d.get("viewpoints", [])])):
        got = [q.get("name") for q in (se.get(key) or [])]
        if got != want:
            bad.append("焼き出しの `setae.%s` の名簿が図と違う(焼き %d 件 / 図 %d 件・"
                       "差 %s)" % (key, len(got), len(want),
                                   "／".join(sorted(set(want) ^ set(got))) or "並び"))
    # ⭕ **設えの世界座標も引き直す**【高1 検図21巡目 → 2026-09-09】── ⛔ 名簿の一致だけでは
    #    「名は合っているが別の場所に据わる」道が開いたままになる(+10 m 平行移動で無音だった)。
    _sb = dict((q.get("name"), q) for q in (se.get("props") or []))
    for nm9, Q9 in prop_rects(d):
        q = _sb.get(nm9)
        if q is not None:
            _cmp("点景『%s』の外形" % nm9, q.get("world"), [_w(g, p9) for p9 in Q9]); ncmp += 1
    _fb = dict((q.get("name"), q) for q in (se.get("fumiishi") or []))
    for q9 in _fu:
        q = _fb.get(q9[0])
        if q is not None:
            _cmp("踏石『%s』の外形" % q9[0], q.get("world"),
                 [_w(g, (q9[1], q9[2])), _w(g, (q9[3], q9[2])),
                  _w(g, (q9[3], q9[4])), _w(g, (q9[1], q9[4]))]); ncmp += 1
    _gb = dict((q.get("name"), q) for q in (se.get("gardens") or []))
    for gd in d["gardens"]:
        q = _gb.get(gd["name"])
        if q is not None:
            _cmp("区『%s』の輪郭" % gd["name"], q.get("world"),
                 [_w(g, p9) for p9 in (gd.get("poly") or [])]); ncmp += 1
    _vb = dict((q.get("name"), q) for q in (se.get("viewpoints") or []))
    for vp in d.get("viewpoints", []):
        q = _vb.get(vp["name"])
        if q is not None:
            _cmp("見所『%s』の位置" % vp["name"], q.get("world"), _w(g, vp["uv"])); ncmp += 1
    _io = ido_rects(d)
    _ir = (se.get("ido") or {}).get("rects") or {}
    if _io:
        for k8, v8 in _io.items():
            _cmp("井戸屋形『%s』の面" % k8, _ir.get(k8),
                 ([_w(g, p9) for p9 in v8] if k8 == "柱" else
                  [_w(g, (v8[0], v8[1])), _w(g, (v8[2], v8[1])),
                   _w(g, (v8[2], v8[3])), _w(g, (v8[0], v8[3]))])); ncmp += 1
    # ⭕ **撒いた木の `world` を一本残らず引き直す**【高1 検図21巡目】── ⚠ 旧図は `u`/`v` だけが
    #    輪に入っていて、**実装が読む `world` は素通り**だった(1,735 本を +10 m 動かして⛔0件)。
    _P9 = (im.get("planting") or {}).get("points") or []
    wmax, wat9, nw = 0.0, None, 0
    for q9 in _P9:
        if q9.get("u") is None or not q9.get("world"): continue
        x8, z8 = _w(g, (q9["u"], q9["v"]))
        dv9 = max(abs(q9["world"][0] - x8), abs(q9["world"][1] - z8))
        nw += 1
        if dv9 > wmax: wmax, wat9 = dv9, q9["name"]
    # ⚠ **ここだけは丸めが二重に乗る** ── 焼き出しの `world` は生の (u,v) から出して 3 桁で
    #   丸めた値、引き直しは **4 桁で丸めた `u`/`v`** から出して 3 桁で丸めた値なので、
    #   両者は最大『世界座標の丸め 1 mm + `u`/`v` の丸め 0.2 mm』だけ離れうる。
    #   ⛔ 設計の余裕ではない(丸めの幅そのもの)。⛔ これ以上広げない。
    _tol9 = IMPL_EXPORT_TOL + 0.001 + BAKE_ROUND_KEN * d["const"]["ken"]
    if wmax > _tol9:
        bad.append("撒いた木の **`world` が `u`/`v` から引き直した世界座標と %.4f m 食い違う**"
                   "(許容 %.4f m = `exportTol` + 二重の丸め・例『%s』・測った %d 本)— "
                   "⛔ 実装が読むのは `world` であって `u`/`v` ではない(高1 検図21巡目)"
                   % (wmax, _tol9, wat9, nw))
    note.append("撒いた木 **%s 本**の `world` を `_w(g, (u, v))` で**全点**引き直して突き合わせ、"
                "最大の差 **%.4f m**(許容 %.4f m = `exportTol` + **二重の丸め**"
                "(世界座標 1 mm + `u`/`v` 0.2 mm))【算出 — 高1 検図21巡目。"
                "⚠ 旧図は `u`/`v` だけが輪に入っており、`world` が別でも鳴らなかった。"
                "⛔ 許容を丸めの幅より広げない】"
                % (format(nw, ","), wmax, _tol9))
    # ⭕ **名指しで据えた木**(一本立ち・差し掛け)は位置が宣言からの従属値なので、
    #    ⛔ **一本ずつ引き直して突き合わせる**【高1/高2 2026-09-09】── 撒き木と違って
    #    座標が決定論的に出るので、ここが黙ると「意匠が決めた木」が黙って別の所へ動く。
    want9 = {}
    for gd in d["gardens"] + d["slopeBands"]:
        for sg in gd.get("singles", []): want9[sg["name"]] = tuple(sg["uv"])
    for sk9 in sashikake_rows(d, g): want9[sk9["name"]] = (sk9["u"], sk9["v"])
    by9 = dict((q["name"], q) for q in _P9)
    for nm9 in sorted(want9):
        q9 = by9.get(nm9)
        if q9 is None:
            bad.append("焼き出しに**名指しで据えた木**『%s』が無い(一本立ち・差し掛けは位置が"
                       "宣言からの従属値なので、必ず焼かれていなければならない)" % nm9); continue
        _cmp("名指しの木『%s』の位置" % nm9, q9.get("world"), _w(g, want9[nm9])); ncmp += 1
    nmd9 = [q["name"] for q in _P9 if q["group"].startswith("差し掛け(")
            or q["group"].endswith("(一本立ち)")]
    if sorted(nmd9) != sorted(want9.keys()):
        bad.append("焼き出しの**名指しで据えた木**の名簿が図と違う(焼き %d 本 / 図 %d 本・差 %s)"
                   % (len(nmd9), len(want9),
                      "／".join(sorted(set(want9) ^ set(nmd9))[:4]) or "並び"))
    # ⭕ **林縁の段が焼き出しに現れているか**【④ 庭方 2026-09-09 十七巡目】── ⛔ 段ごとに
    #    別の密度と丈を宣言したのだから、⛔ **段ごとの群と丈が焼き出しに無ければ未測定**である
    #    (規則19 — 宣言だけあって撒き方に届いていない道を塞ぐ)。
    for b9 in d["slopeBands"]:
        ts9 = rinen_tiers(b9)
        if not ts9: continue
        for t9 in ts9:
            for lay9 in ("中木", "低木"):
                dr9 = rinen_dens_t(d, b9, t9, lay9)
                if not dr9: continue
                gnm = "社叢 帯%d %s の林縁(%s)" % (b9["band"], b9["name"], t9.get("name"))
                got9 = [q for q in _P9 if q.get("group") == gnm and q.get("layer") == lay9]
                if not got9:
                    bad.append("林縁の段『%s／%s』は密度 %g 本/100m² を宣言しているのに、"
                               "**焼き出しに一本も無い**(群『%s』)— ⛔ 宣言が撒き方へ届いて"
                               "いない(規則19)" % (t9.get("name"), lay9, dr9, gnm))
                    continue
                hr9 = rinen_h_t(d, b9, t9, lay9)
                lo9, hi9 = _h_pair(hr9)
                off9 = [q["name"] for q in got9
                        if lo9 is not None and not (lo9 - 1e-6 <= (q.get("h") or 0) <= hi9 + 1e-6)]
                if off9:
                    bad.append("林縁の段『%s／%s』の焼き出しの丈 %d 本が宣言 [%g, %g] m の外"
                               "(例 %s)" % (t9.get("name"), lay9, len(off9), lo9, hi9, off9[0]))
                note.append("林縁の段『帯%d／%s／%s』── 焼き出し **%d 本** ／ 密度 %g 本/100m² ／ "
                            "丈 %g〜%g m【算出 — ④ 庭方 2026-09-09。⛔ 段ごとに別の密度と丈を"
                            "宣言したので、段ごとに焼かれていることを測る(規則19)】"
                            % (b9["band"], t9.get("name"), lay9, len(got9), dr9,
                               lo9 or 0.0, hi9 or 0.0))
    note.append("名指しで据えた木 **%d 本**(一本立ち + 差し掛け)の位置を宣言から引き直して"
                "突き合わせた【算出 — 高1/高2 2026-09-09。⛔ 名簿の一致だけで済ませない】"
                % len(want9))
    note.append("**世界座標を引き直して突き合わせた組 %d**(囲い・石段・門・動線・玉垣・点景・"
                "踏石・区・見所・井戸屋形)+ 撒いた木 %s 本【算出 — 高1 検図21巡目。"
                "⛔ 0 件は合格ではなく未測定(規則19)】" % (ncmp, format(nw, ",")))
    # ⭕ **散文が名簿を写し直していないか**【低4 検図20巡目 → 2026-09-09】。
    #   ⚠ `_gardens` は『白洲・中庭・社叢・境内の立木3区・…・井戸屋形・…』と数えており、
    #     **6 項の名簿に読めた**(実体は 8)。名簿は二箇所に持てば必ず食い違う(規則4)ので、
    #     ⛔ 区の名が二つ以上並んでいたら「名簿を写した」と見て止める。
    _gp = str(d.get("_gardens") or "")
    _hit = [gd["name"] for gd in d["gardens"] if gd["name"] in _gp]
    if len(_hit) >= 2:
        bad.append("`_gardens` の散文が**区の名簿を写している**(%d 件 — %s)。⛔ 名簿の正典は "
                   "`gardens[]` の並びだけ(規則4)── 数え方の違いで『区 6』『区 8』の二重申告が"
                   "起きた出所(低4 検図20巡目)" % (len(_hit), "・".join(_hit[:4])))
    note.append("`_gardens` の散文が写している区の名 **%d**(⭕ 0 が正 — 名簿の正典は `gardens[]` "
                "の並びだけ)【算出 — 低4 検図20巡目 → 2026-09-09】" % len(_hit))
    note.append("設え ── 点景 **%d** ／ 踏石 **%d** ／ 区 **%d** ／ 見所 **%d** ／ "
                "井戸屋形の面 **%d**(⛔ どれも指図に矩形が無い従属値。名簿で突き合わせる)【算出】"
                % (len(se.get("props") or []), len(se.get("fumiishi") or []),
                   len(se.get("gardens") or []), len(se.get("viewpoints") or []),
                   len((se.get("ido") or {}).get("rects") or {})))
    return bad, note


def main_export_impl():
    """`--export-impl` ── 実装が読む算出物だけを焼く。

    ⚠ この生成器は指図へ書き戻さない(`json.dump` で `sanno_sashizu.json` を触らない)ので、
      図を組む前でも後でも `src.sha256` は同じ物を指す。⭕ **指図を直したら先にここを回す**
      (図の側の検査『実装が読む算出物の鮮度』が古い焼きで止まる)。
    """
    d = json.load(open(JSON, encoding="utf-8"))
    derive_routes(d)
    g = G(d)
    derive_edges(d)             # ⭐ 道敷に接する辺を毎回同定(決4 庭方 2026-09-09 十八巡目)
    derive_gates(d, g)
    derive_runs(d, g)
    derive_zentei(d, g)
    derive_cluster_groups(d)    # ⭐ 塊の `groups` を兄弟へ展開(中6 庭方 2026-09-09)
    derive_clusters(d)
    derive_view_clusters(d, g)
    derive_view_eda(d)
    derive_viewpoints(d, g)     # ⭐ 見所の `eyeH`/`look` を焼く(2026-09-08 B-3・庭方)
    st = export_impl(d, g)
    print("wrote %s (%.0f KB)" % (IMPL_OUT, os.path.getsize(IMPL_OUT) / 1024))
    print("  造成後の地盤 %d/%d セル(格子 %g m)／ 石段 %d ／ 囲い・土留め %d ／ 門 %d ／ "
          "動線 %d ／ 玉垣の辺 %d" % (st["graded"], st["cells"], IMPL_STEP, st["stairs"],
                                     st["runs"], st["gates"], st["routes"], st["tamagaki"]))
    print("  点景 %d ／ 踏石 %d ／ 見所 %d ／ 井戸屋形の面 5"
          % (st["props"], st["fumiishi"], st["viewpoints"]))
    print("  撒いた木 %d 本(帯 × 層 %d 口 ／ 塊 %d)" % (st["points"], st["bands"], st["clusters"]))
    print("  src.sha256 = %s" % _sha256(JSON))
    print("  dem.sha256 = %s" % _sha256(DEM_JSON))



# ================================================================ 破壊試験(2026-09-09 十九巡目 B-3)
# ⭐⭐ **土井の方式を山王へ移した**【B-3 検図22巡目 → 2026-09-09 十九巡目】。
#   ⛔⛔ **変異が一つも当たらない破壊試験は、検査が死んでいても「期待どおり」と刷る。**
#   ⛔ 手作業の一度きりで終わらせない ── 「22 本中 21 本発火」はコミット文にしか残らず、
#     **再現も回帰もできない**(規則19)。⭕ **毎回組むたびに図へ刷る。**
#   ⛔ `wiring_gate.py` 自身が「**恒真の検査 → 破壊試験でしか出ない**」と書いている。
#
# ⚠⚠ **モジュール級のキャッシュを跨がせない**【検図の警告 2026-09-09】── 同一プロセスで回すと
#   `_BANDS` ほかの覚え書きが汚染され、**全変異が同じ件数を出す偽陽性**になる。
#   ⇒ ⭕ **束ごとに覚え書きを退避 → 消去 → 復元**する(`_probe_caches`)。
_PROBE_CACHES = ("_BANDS", "_BSTAT", "_VCUT", "_GRP", "_VH", "_LAND", "_EDGE_NOTE",
                 "_WSEG", "_WCOMP", "_STAIR_CF", "_STAIR_CF_N", "_SCAT_N", "_SITE_EDGE_N")
_PROBE_SLOTS = ("_WSEG", "_WCOMP", "_SCAT_N")   # `[None]` の一枠 ── 退避中は `[None]` に戻す


def _probe_caches(fn):
    """覚え書きを退避して消し、`fn()` を回し、必ず戻す。⛔ 破壊試験が本編の答えを汚さない。"""
    G = globals()
    save = {}
    for k in _PROBE_CACHES:
        o = G.get(k)
        if isinstance(o, dict): save[k] = dict(o); o.clear()
        elif k in _PROBE_SLOTS: save[k] = list(o); o[:] = [None]   # ⚠ 一枠の覚え書きは空にしない(`[0]` で引く)
        elif isinstance(o, list): save[k] = list(o); del o[:]
    try:
        return fn()
    finally:
        for k, v in save.items():
            o = G[k]
            if isinstance(o, dict): o.clear(); o.update(v)
            else: del o[:]; o.extend(v)


def _probe(d, mut, pick=None):
    """**破壊試験の変異をひとつ当てる。**返すのは (壊した図の写し, 変異が当たったか)。

    ⭕ **当たったかは「図が1バイトでも変わったか」で機械に見せる** ── ⛔ 束ごとに
      「何件に当たるはず」と書き写さない(⛔ それ自体が二重の正典になる=規則4)。
    """
    e = copy.deepcopy(d)
    mut(pick(e) if pick else e)
    return e, (json.dumps(e, ensure_ascii=False, sort_keys=True, default=str)
               != json.dumps(d, ensure_ascii=False, sort_keys=True, default=str))


def _probe_verdict(probes, what=""):
    """**束の合否**。束は `(名, 実測, 期待, 当たったか)` で、`当たったか` が `None` は**基準**。

    ⛔ **鳴った件数そのものは比べない** ── 比べるのは**鳴る/鳴らない**(⚠ 件数を固定すると、
      無関係な行が1件増えただけで赤くなる)。
    """
    bad = []
    for nm, got, want, mv in probes:
        g = tuple(got) if isinstance(got, (tuple, list)) else (got,)
        w = tuple(want) if isinstance(want, (tuple, list)) else (want,)
        if mv is False:
            bad.append("**%s の変異が空振り** — ⛔⛔ **図が1バイトも変わっていない**。"
                       "⚠ 0 件にマッチする変異は、検査が死んでいても「期待どおり」と刷る"
                       "(規則19)%s" % (nm, ("。" + what) if what else ""))
            continue
        if [q > 0 for q in g] != [q > 0 for q in w]:
            bad.append("**%s**: 実測 %s — 期待 %s"
                       % (nm, " / ".join("%d件" % q for q in g),
                          " / ".join("鳴る" if q else "鳴らない" for q in w)))
    return bad


_PROBE_ROSTER = [None, None]


def probe_roster(d, g):
    """**今巡の変異の束を一枚に並べる**【B-3 検図22巡目 → 2026-09-09 十九巡目】。

    ⛔⛔ **「変異が当たったか」を各表の隅に閉じ込めない** ── ⭕ **一覧が在って初めて
      「どの束が空振りか」を人が数えられる**(規則19)。
    ⚠ 束は**その検査だけ**を回す(⛔ 50 本を回し直さない ── 毎回組むたびに刷る値にする)。
    戻り ((検査, 束の名, 実測, 期待, 当たったか) の並び, 不合格の並び)。
    """
    key = hashlib.sha1(json.dumps(d, ensure_ascii=False, sort_keys=True,
                                  default=str).encode("utf-8")).hexdigest()
    if _PROBE_ROSTER[0] == key: return _PROBE_ROSTER[1]

    def run(fn, e):
        return _probe_caches(lambda: len(fn(e, g)[0]))

    def run1(fn, e):                      # 戻りが (bad, note) でなく bad だけの検査
        return _probe_caches(lambda: len(fn(e)[0]))

    out, bad = [], []

    # ---- ① ★主景の木(A-1)
    n0 = run(shukei_bake_check, d)
    out.append(("★主景の木", "基準(壊さない)", n0, 0, None))

    def m1(e):
        for gd in e["gardens"]:
            if gd.get("shukei"): gd["shukei"]["tree"]["uv"] = [-52.0, 8.0]
    e1, mv1 = _probe(d, m1)
    out.append(("★主景の木", "主景の木を西Aの隅へ動かす(焼き出しと食い違わせる)",
                run(shukei_bake_check, e1), 1, mv1))

    def m2(e):
        for gd in e["gardens"]:
            if gd.get("shukei"): gd["shukei"].pop("acceptFrom", None)
    e2, mv2 = _probe(d, m2)
    out.append(("★主景の木", "受入値(`acceptFrom`)の宣言を落とす",
                run(shukei_bake_check, e2), 1, mv2))

    # ---- ② 幹が社地の内か(A-2)
    n3 = run(kyoukai_inside_check, d)
    out.append(("塊と名指しの木の幹が社地の内にあるか", "基準(壊さない)", n3, 0, None))

    def m3(e):
        cu = sum(q[0] for q in e["polygon"]) / len(e["polygon"])
        cz = sum(q[1] for q in e["polygon"]) / len(e["polygon"])
        e["polygon"] = [[cu + (q[0] - cu) * 0.5, cz + (q[1] - cz) * 0.5] for q in e["polygon"]]
    e3, mv3 = _probe(d, m3)
    out.append(("塊と名指しの木の幹が社地の内にあるか", "社地の輪郭を半分に縮める",
                run(kyoukai_inside_check, e3), 1, mv3))

    def m4(e):
        (e["planting"].get("plantRule") or {}).pop("kyoukaiInsideRule", None)
    e4, mv4 = _probe(d, m4)
    out.append(("塊と名指しの木の幹が社地の内にあるか", "受入値(`kyoukaiInsideRule`)を落とす",
                run(kyoukai_inside_check, e4), 1, mv4))

    # ---- ③ 名指しの木 × 設計された塊(A-3)
    n5 = run(named_vs_cluster_check, d)
    out.append(("名指しの木と設計された塊の余白", "基準(壊さない)", n5, 0, None))

    def m5(e):
        for sk in e["planting"].get("sashikake", []):
            sk["sides"] = "南北交互"
    e5, mv5 = _probe(d, m5)
    out.append(("名指しの木と設計された塊の余白", "差し掛けを南北交互へ戻す(⛔ 十七巡目の姿)",
                run(named_vs_cluster_check, e5), 1, mv5))

    def m6(e):
        (e["planting"].get("plantRule") or {}).pop("namedVsClusterRule", None)
    e6, mv6 = _probe(d, m6)
    out.append(("名指しの木と設計された塊の余白", "受入値(`namedVsClusterRule`)を落とす",
                run(named_vs_cluster_check, e6), 1, mv6))

    # ---- ④ 前庭の立面の三尊(A-5)
    n7 = run(sankaku_check, d)
    out.append(("前庭の立面の三尊", "基準(壊さない)", n7, 0, None))

    def m7(e):
        for gd in e["gardens"]:
            if gd.get("sankaku"): gd["sankaku"]["minDiffDeg"] = 20.0
    e7, mv7 = _probe(d, m7)
    out.append(("前庭の立面の三尊", "仰角の差の下限を 20° へ上げる(現況を割らせる)",
                run(sankaku_check, e7), 1, mv7))

    def m8(e):
        for gd in e["gardens"]:
            if gd.get("sankaku"): gd["sankaku"]["from"] = "V-Z9(在りもしない見所)"
    e8, mv8 = _probe(d, m8)
    out.append(("前庭の立面の三尊", "見所の指し先を死なせる",
                run(sankaku_check, e8), 1, mv8))

    # ---- ⑤ 面に載る物の Δ の包絡(B-2)
    n9 = run(plane_dev_check, d)
    out.append(("面に載る物の Δ(包絡)", "基準(壊さない)", n9, 0, None))

    def m9(e):
        e["terraces"][0]["y"] = e["terraces"][0]["y"] + 5.7
    e9, mv9 = _probe(d, m9)
    out.append(("面に載る物の Δ(包絡)", "境内の天端を +5.7 m 盛る",
                run(plane_dev_check, e9), 1, mv9))

    def m10(e):
        for pl in e["planes"]: pl.pop("devEnvelopeM", None)
    e10, mv10 = _probe(d, m10)
    out.append(("面に載る物の Δ(包絡)", "包絡(`devEnvelopeM`)の宣言を落とす",
                run(plane_dev_check, e10), 1, mv10))

    # ---- ⑥ 棟飾りを棟ごとに引くか(B-1)
    n11 = run1(mune_height_check, d)
    out.append(("棟高の物差しと部材の丈", "基準(壊さない)", n11, 0, None))

    def m11(e):
        for m in e["munes"]:
            m.pop("muneOrnamentProvisionalM", None); m.pop("muneOrnamentM", None)
    e11, mv11 = _probe(d, m11)
    out.append(("棟高の物差しと部材の丈", "棟ごとの棟飾りの宣言を全部落とす",
                run1(mune_height_check, e11), 1, mv11))

    def m12(e):
        e["const"]["muneOrnamentProvisionalM"] = 0.687
    e12, mv12 = _probe(d, m12)
    out.append(("棟高の物差しと部材の丈", "`const` の一律の暫定値を復活させる",
                run1(mune_height_check, e12), 1, mv12))

    # ---- ⑦ 線に沿う塊の芯々(A-7)
    n13 = run(cluster_pack_check, d)
    out.append(("塊が塊として組めるか", "基準(壊さない)", n13, 0, None))

    def m13(e):
        for gd in e["gardens"] + e["slopeBands"]:
            for c in gd.get("clusters", []):
                if c.get("alongTakagiEdgeLine"): c["spacing"] = 5.0
    e13, mv13 = _probe(d, m13)
    out.append(("塊が塊として組めるか", "線に沿う塊の芯々を 5.0 間へ広げる(輪郭に入らなくする)",
                run(cluster_pack_check, e13), 1, mv13))

    # ---- ⑧ 本殿の木階の閉合(B-8)
    n14 = run1(kaidan_close_check, d)
    out.append(("石段の閉合", "基準(壊さない)", n14, 0, None))

    def m14(e):
        e["kaidans"] = [q for q in e["kaidans"] if not q["name"].startswith("本殿の木階")]
    e14, mv14 = _probe(d, m14)
    out.append(("石段の閉合", "本殿の木階を `kaidans` から抜く",
                run1(kaidan_close_check, e14), 1, mv14))

    def m15(e):
        e["const"]["shadenHondenStepM"] = 1.5
    e15, mv15 = _probe(d, m15)
    out.append(("石段の閉合", "`const.shadenHondenStepM` を段の比高と食い違わせる",
                run1(kaidan_close_check, e15), 1, mv15))

    # ---- ⑨ 埋まっている区間の段差(裁定 EDO-0182 (b))
    n16 = run(wall_step_check, d)
    out.append(("埋まっている区間に段差が在るか", "基準(壊さない)", n16, 0, None))

    def m16(e):
        for w in e["terraceWalls"]:
            if w["name"] == "TW_Zentei_SE": w["coping"] = w["coping"] - 1.0
    e16, mv16 = _probe(d, m16)
    out.append(("埋まっている区間に段差が在るか",
                "`TW_Zentei_SE` の天端を前庭の面より下げる(両側とも地盤が上になる)",
                run(wall_step_check, e16), 1, mv16))

    bad = _probe_verdict([(nm, got, want, mv) for _ck, nm, got, want, mv in out])
    _PROBE_ROSTER[0], _PROBE_ROSTER[1] = key, (out, bad)
    return out, bad


def probe_misfire_check(d, g):
    """**変異が一つも当たっていない破壊試験が無いか**【B-3 検図22巡目 → 2026-09-09 十九巡目】。

    ⛔⛔ **これは「検査の検査」である** ── ⚠ 空振りの束は**検査が死んでいても「期待どおり」と
      刷る**ので、⛔ **束の数を数えても捕まらない**(規則19)。
    """
    ros, bad = probe_roster(d, g)
    hit = sum(1 for q in ros if q[4] is True)
    mis = sum(1 for q in ros if q[4] is False)
    base = sum(1 for q in ros if q[4] is None)
    note = ["破壊試験 ── **変異の束 %d**(当たり %d ／ **空振り %d**)／ 基準の束 %d ／ "
            "**不合格 %d 件**【算出 — B-3 検図22巡目 → 2026-09-09。"
            "⛔ 手作業の一度きりで終わらせない(毎回組むたびに回る)。"
            "⛔ 0 件にマッチする変異は、検査が死んでいても『期待どおり』と刷る】"
            % (hit + mis, hit, mis, base, len(bad))]
    for ck, nm, got, want, mv in ros:
        note.append("[%s] %s ── 実測 **%d 件** ／ 期待 %s ／ %s【算出】"
                    % (ck, nm, got, ("鳴る" if want else "鳴らない"),
                       "基準(変異ではない)" if mv is None
                       else ("⭕ 変異が図に当たった" if mv else "⚠⚠ **空振り**")))
    return bad, note


def probe_roster_table(d, g):
    """**破壊試験の総覧** — どの束が「当たった/空振り」かを一枚に。"""
    ros, vbad = probe_roster(d, g)
    hit = sum(1 for q in ros if q[4] is True)
    mis = sum(1 for q in ros if q[4] is False)
    base = sum(1 for q in ros if q[4] is None)

    def _ok(nm9, g9, w9, mv9):
        return not _probe_verdict([(nm9, g9, w9, mv9)])
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td class='note'>%s</td>"
                   "<td>%s</td><td>%s</td></tr>"
                   % (ck, inline(nm), "%d 件" % got, ("鳴る" if want else "鳴らない"),
                      ("— 基準(変異ではない)" if mv is None else
                       ("⭕ 当たった" if mv else "⚠⚠ <b>空振り</b>")),
                      ("⭕" if _ok(nm, got, want, mv) else "⚠⚠ <b>不合格</b>"))
                   for ck, nm, got, want, mv in ros)
    return ('<div class="tw"><table><thead><tr><th>検査</th><th>破壊試験の束</th><th>実測</th>'
            "<th class='note'>期待</th><th>変異が図に当たったか</th><th>束の合否</th>"
            "</tr></thead><tbody>" + rows + "</tbody></table></div>") + (
        "<p class='cap'>⭐⭐ <b>破壊試験は「変異が当たったか」まで見て初めて意味を持つ</b>"
        "【B-3 検図22巡目 → 2026-09-09 十九巡目・土井の方式を移した】— "
        "⛔⛔ <b>0 件にマッチする変異は、検査が死んでいても「期待どおり」と刷る。</b><br>"
        "⭕ <b>判定は「図が1バイトでも変わったか」</b>(共通の仕掛け <code>_probe</code>)— "
        "⛔ 束ごとに「何件に当たるはず」と書き写さない(⛔ それ自体が二重の正典になる=規則4)。<br>"
        "⭕ <b>変異の束 %d</b>(当たり %d ／ <b>空振り %d</b>)／ 基準の束 %d ／ "
        "<b>不合格 %d 件</b>は <code>probe_misfire_check</code> から機械検査へ出る。"
        "⛔ <b>空振りも不合格も 1 件でもあれば赤くなる。</b><br>"
        "⚠⚠ <b>同一プロセスで回すので覚え書きを束ごとに退避・消去・復元する</b>"
        "(<code>_probe_caches</code>)— ⛔ 汚染したまま回すと<b>全変異が同じ件数を出す偽陽性</b>に"
        "なる(検図の警告 2026-09-09)。</p>"
        % (hit + mis, hit, mis, base, len(vbad)))


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
    derive_edges(d)            # 道敷に接する辺を毎回同定(⛔ 辺の番号を json に書かない・決4)
    derive_gates(d, g)         # 門の芯と、その面に取り付く物の通り(⛔ 面の u を二重に持たない)
    derive_runs(d, g)          # 板塀は輪郭からの生成物。⛔ 生成前の run を検査に掛けない
    derive_zentei(d, g)        # 木戸の芯・供待の北辺は従属値(⛔ 丸めた値を持たない)
    derive_cluster_groups(d)   # 塊の `groups` を兄弟へ展開(中6 庭方 2026-09-09)
    derive_clusters(d)         # 塊の箱は宣言(`boxFrom`)からの従属値(2026-09-07 中3)
    derive_view_clusters(d, g)  # 視線の塊の丈は跨ぐ帯の共通部分(2026-09-08)
    derive_view_eda(d)          # 視線の塊の枝下は `edaShitaFrom` の従属値(2026-09-08 中2)
    derive_viewpoints(d, g)     # 見所の眼高と向きは算出値(2026-09-08 B-3)
    tp = terrain_provenance_check()
    so = sando_offset_check(d)
    ss = sando_suritsuke_check(d)   # 参道の摺り付け(裁定3 を支える量。考証8巡目 低10)
    pa = planting_avoid_check(d, g)
    ro = rect_overlap_check(d, g)
    np_ = noplant_overlap_check(d, g)
    bi = band_invariant_check(d, g)
    ps = path_shape_check(d)
    cw = crown_rule_check(d)
    tz = tree_size_check(d)               # 樹の大きさの規約(裁定1 庭方 2026-09-07 八巡目)
    ft = forest_tier_wiring_check(d)      # 社叢の層を描く断面があるか(A-3 庭方 11巡目)
    sr = single_repeat_check(d)           # 同じ部材の一本立ちが近すぎないか(中2 庭方 九巡目)
    ms = matsu_scale_check(d)             # 松の縦伸ばしの箍(同 中4 → `_pending`)
    cp = cluster_pack_check(d, g)         # 塊が塊として組めるか(同 中3・低3)
    ro_ = rinen_overhang_check(d)         # 参道への林縁の張り出しの上限(同 裁定2)
    kb = kido_bay_check(d)
    tb = tamagaki_bay_check(d)
    mfl = mitsuke_fill_check(d)        # 柵の見付けの充実率(指5 庭方18巡目)
    sn = shisen_check(d)
    py = plane_y_check(d)
    pd_ = plane_dev_check(d, g)
    ib = inubashiri_check(d, g)
    kib = keidai_inubashiri_check(d, g)   # 境内の囲いの犬走り(検図9巡目 中3)
    ts = terrace_shape_check(d)           # 平場の輪郭の健全性(検図12巡目 中2)
    kc = kaidan_close_check(d)            # 石段の閉合(丸めの吸収先。検図12巡目 → 2026-09-08)
    sd = saku_decl_check(d)               # 柵の宣言(kind と hFrom の整合。検図10巡目 中3/中4)
    rd = roof_decl_check(d)               # 屋根を持つ run の葺材(高1 考証19巡目)
    kx = kakoi_cross_check(d, g)          # 囲い・土留め・屋根の帯どうしの交差と離れ(検図11巡目 中1)
    sc = section_cut_check(d, g)          # 断面が切る棟(検図9巡目 中2)
    sw = section_window_check(d)          # 断面の窓が社地の境を跨ぐか(検図17巡目 低1)
    szs = size_spelling_check(d)          # sizes の綴りが目録で解けるか(考証15巡目 軽微4)
    # ⚠ 変数名は `ss`(参道の摺り付け)と衝突させない — 2026-09-08 に一度上書きして
    #    参道の摺り付けの〔記録〕を丸ごと落としかけた。⛔ 短い受けを使い回さない。
    sg_ = saichigai_check(d, g)           # 造成が社地の外へ出ていないか(検図9巡目 低5)
    io = ido_check(d)
    ed = endai_check(d, g)
    sq = sankaku_check(d, g)      # 立面の三尊(A-5 庭方19巡目・⛔ 平面では測らない)
    st_ = sekitoro_check(d, g)    # 石灯籠(⛔ 等間隔に据えない。2026-09-07 低1)
    # ⭐ **合格の側も一行刷る**【B-5 検図22巡目 → 2026-09-09 十九巡目】
    _rpq = route_pierce(d, g)
    rp = ["%s が %s を貫く" % q for q in _rpq]
    rpn = ["動線が構造物を貫通しないか ⭕ ── 動線 %d 本 × 構造物(棟 %d・門 %d・囲い %d・"
           "土留め %d)を総当たり ── 貫通 %d 件【算出 — ⛔ 0 件は合格ではなく未測定なので、"
           "**何を何と突き合わせたか**を刷る(B-5 検図22巡目)】"
           % (len(d.get("routes") or []), len(d["munes"]), len(d["gates"]),
              len(d["runs"]), len(d.get("terraceWalls") or []), len(_rpq))]
    kp = kenpei_bottom_area(d)
    pp = pending_pointer_check(d)
    mh = mune_height_check(d)          # 棟高の物差しと部材の丈(高3 検図21巡目 → 裁3/裁4)
    chm = cluster_hmin_check(d)        # 塊の松の丈の下限(中8 庭方17巡目)
    ifr = impl_fresh_check(d)          # 実装が読む算出物の鮮度(2026-09-08 棟梁の診断)
    # ⭐⭐ **焼き出しが古いときは「未測定」と刷る**【B-7 検図22巡目 → 2026-09-09 十九巡目】──
    #   ⛔ `([], [])` を返すと表の上で「**測って綺麗**」と区別が付かない。⚠ `impl_fresh_check` が
    #   ⛔ で止めるので抜け道ではないが、⛔ **0 件は合格ではなく未測定**(規則19)。
    _STALE = ("— **未測定**(焼き出しの鮮度が⛔なので見送り)── ⛔ 0 件は合格ではない。"
              "`--export-impl` を回してから読むこと")

    def _gated(fn):
        return fn(d, g) if not ifr[0] else ([], [_STALE])
    sgp = _gated(single_gap_check)   # 一本立ちの離れ(指2 庭方18巡目)
    ntc = named_tree_check(d, g)       # 名指しの木(決1③ 庭方18巡目)
    skb = shukei_bake_check(d, g)      # ★主景(名指し・焼き出し・仰角の受入値。A-1 庭方19巡目)
    nvc = named_vs_cluster_check(d, g)  # 名指しの木 × 設計された塊の余白(A-3 庭方19巡目)
    pmf = probe_misfire_check(d, g)     # 破壊試験の総覧(B-3 検図22巡目)
    kin = _gated(kyoukai_inside_check)   # 幹が社地の内か(A-2 庭方19巡目)
    cpb = _gated(cluster_place_bake_check)  # 塊の据わり(A-2②/A-7)
    igc = _gated(impl_graded_check)  # ⛔ 無い焼きを測らない
    ipc = _gated(impl_planting_check)  # 撒いた木の面と離れ(2026-09-08)
    iwp = _gated(impl_wall_profile_check)  # 土留めの縦断(中4 20巡目)
    wsc = wall_step_check(d, g)            # 埋まっている区間の段差(裁定 EDO-0182 (b))
    kwc = _gated(keepout_wiring_check)     # 退避の表の結線(中2 20巡目)
    cph = _gated(crown_per_h_check)  # 樹冠÷丈(低9/低10 庭方17巡目)
    ccv = _gated(crown_cover_check)  # 芯線の樹冠被覆(高1/高2 庭方17巡目)
    # ⛔ **件数のまま運ぶ**(⛔ 文字列へ埋めない)— `rows` が print と return の両方へ届く形
    rows = []
    rows.append(("地形の出自(造成前の正本の切り出し)", tp[0], tp[1]))
    rows.append(("参道の柵と林縁が社地の辺のオフセットか(⛔ 辺の番号は毎回同定する)",
                 so, edge_ident_rows(d)))
    rows.append(("参道の縦断の局所段差(摺り付け ≤ `const.suritsukeM` で吸収できるか)",
                 ss[0], ss[1]))
    rows.append(("植栽の多角形 ∩ 退避 = 0", pa[0], pa[1]))
    rows.append(("面の総当たり(棟・門・区・帯・石段・塊・玉垣・低木の面・踏石・点景)", ro[0], ro[1]))
    rows.append(("空地(供待)が平場の中か・何と重なるか", np_[0], np_[1]))
    rows.append(("社叢の帯の不変条件 ①②③", bi[0], bi[1]))
    rows.append(("道の形(道幅より短い脚・引き返し・迷い点)", ps[0], ps[1]))
    rows.append(("樹冠の規約(高木の枝下・中木/低木の樹冠)", cw[0], cw[1]))
    rows.append(("樹の大きさの規約(`crownPerH` ／ `sizeRule` の照合 ／ 一本立ちの層と丈)",
                 tz[0], tz[1]))
    rows.append(("社叢の層の稜線を描く断面があるか(帯 × 層。⛔ 宣言だけで図に出ない値を作らない)",
                 ft[0], ft[1]))
    rows.append(("同じ部材の一本立ちが近すぎないか(閾は `clusterGapMin` の最小値)", sr[0], sr[1]))
    rows.append(("松の縦伸ばしの箍(`scaleRule.matsu.scaleYMax` ／ 猶予は `_pending`)", ms[0], ms[1]))
    rows.append(("塊が塊として組めるか(箱の広さ・落葉は一塊に一本・同層の芯々・塊をまたぐ芯々)",
                 cp[0], cp[1]))
    rows.append(("樹冠 ÷ 丈 の上限(社叢の中)", cph[0], cph[1]))
    rows.append(("一本立ちの離れ(奇数の作法 ── 名簿つき・受入値は樹冠からの従属値)",
                 sgp[0], sgp[1]))
    rows.append(("塊の松の丈の下限(棟高からの従属)", chm[0], chm[1]))
    rows.append(("参道への林縁の張り出し(⛔ 上限だけ・局所の道敷幅から)", ro_[0], ro_[1]))
    rows.append(("玉垣の木戸(辺に納まるか・裏 `insideKen` へ入る樹冠と枝下)", kb[0], kb[1]))
    rows.append(("玉垣の一枚の内法(立子が入る寸法か)", tb[0], tb[1]))
    rows.append(("腰高の柵の見付けの充実率(透けが景の理由 ── ⛔ 貫は未宣言)",
                 mfl[0], mfl[1]))
    rows.append(("前庭の視線の抜き(玉垣より高い物を置かない)", sn[0], sn[1]))
    rows.append(("面の天端の出所(`terraces[].y` 一本・面と名簿の宣言)", py[0], py[1]))
    rows.append(("面に載る門・棟・井戸屋形の Δ(§B-1・裁定済 2026-09-07 — 数を刷るのが役)",
                 pd_[0], pd_[1]))
    rows.append(("前庭の西縁の犬走り(西縁に取り付く物すべて)", ib[0], ib[1]))
    rows.append(("境内の囲いの犬走り(平場の輪郭からの寄せ)", kib[0], kib[1]))
    rows.append(("平場の輪郭の健全性(重複頂点・零長辺・自己交差／最鋭の内角・輪郭の首)", ts[0], ts[1]))
    rows.append(("石段の閉合(蹴上×段数 と比高の差・丸めの吸収先)", kc[0], kc[1]))
    rows.append(("柵の宣言(`kind`=柵 と丈の出所 `hFrom` の整合)", sd[0], sd[1]))
    rows.append(("屋根を持つ run の葺材(⛔ 材を発明した状態で実装へ渡さない)",
                 rd[0], rd[1]))
    rows.append(("囲い・土留め・屋根の帯どうしの交差と離れ", kx[0], kx[1]))
    rows.append(("断面が切る棟(⛔ 切られない棟は名簿で宣言する)", sc[0], sc[1]))
    rows.append(("断面の窓が社地の境を跨ぐか(⛔ 片側だけ写して他方を切り落とさない)",
                 sw[0], sw[1]))
    rows.append(("`sizeRule.sizes` の綴りが目録で解けるか(⛔ 解けない綴りは猶予の項が要る)",
                 szs[0], szs[1]))
    rows.append(("造成が社地の外へ出ていないか(名簿つき)", sg_[0], sg_[1]))
    rows.append(("井戸屋形の取り合い(軒先≡石敷・石敷が帯の内・玉垣の開口)", io[0], io[1]))
    rows.append(("縁台(床几)が玉垣の東・通行帯の外か", ed[0], ed[1]))
    rows.append(("前庭の立面の三尊(V-Z3 からの梢の仰角の差)", sq[0], sq[1]))
    rows.append(("石灯籠の並び(⛔ 等間隔に据えない)", st_[0], st_[1]))
    rows.append(("建蔽率の分子(屋根を持たない役の名簿)", kp[1], kp[2]))
    rows.append(("動線が構造物を貫通しないか", rp, rpn))
    rows.append(("宣言したポインタの指し先が実在するか(`_pending`・`bom`/`parts` の鍵)",
                 pp[0], pp[1]))
    rows.append(("棟高の物差し(`const.muneHeightRule`)と `partFrom` の指す部材の丈",
                 mh[0], mh[1]))
    rows.append(("実装が読む算出物の鮮度(`sanno_impl.json` の `src`/`dem` の sha256)",
                 ifr[0], ifr[1]))
    rows.append(("焼き出しの造成後の地盤と**世界座標**が図の算出と一致するか",
                 igc[0], igc[1]))
    rows.append(("焼き出した木が宣言した面と離れを守っているか(勝手道・芯々・塊・林縁・"
                 "石段・囲い・`scaleXZ`)", ipc[0], ipc[1]))
    rows.append(("土留めの縦断が図の算出と一つ残らず同じ数か"
                 "(名簿・節点と区間の座標・6列の縦断・開口)", iwp[0], iwp[1]))
    rows.append(("埋まっている区間に段差が在るか(両側 = 壁が要らない ／ 片側 = 天端の扱い)",
                 wsc[0], wsc[1]))
    rows.append(("退避の表 `keepoutFrom` の一項ごとに、指し先が生きて・面になり・"
                 "焼き出しの点が守っているか", kwc[0], kwc[1]))
    rows.append(("道・坂の芯線が樹冠の下を通るか(`planting.crownCover` の受入値・"
                 "社地の内だけ・続いた空きの上限・肩ゼロ換算の理論上限)", ccv[0], ccv[1]))
    rows.append(("名指しの木が宣言どおり引けているか(帯の同定・丈・部材・樹冠)", ntc[0], ntc[1]))
    rows.append(("★主景の木(名指しであること・焼き出しに在ること・仰角の受入値)", skb[0], skb[1]))
    rows.append(("名指しの木が設計された塊の余白に入らないか(⛔ 樹冠では測らない)",
                 nvc[0], nvc[1]))
    rows.append(("破壊試験(変異が図に当たったか・束の合否)", pmf[0], pmf[1]))
    rows.append(("塊と名指しの木の幹が社地の内にあるか(符号つき・全数)", kin[0], kin[1]))
    rows.append(("設計した塊が焼き出しで据わったか(据え残し・間合い・隣どうしの芯々)",
                 cpb[0], cpb[1]))
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
    derive_edges(d)            # 道敷に接する辺を毎回同定(⛔ 辺の番号を json に書かない・決4)
    derive_gates(d, g)         # 門の芯と、その面に取り付く物の通り(⛔ 面の u を二重に持たない)
    derive_runs(d, g)          # 板塀は平場の輪郭から生成する(独立の座標を持たせない)
    derive_zentei(d, g)        # 木戸の芯・供待の北辺は従属値(⛔ 丸めた値を持たない)
    derive_cluster_groups(d)   # 塊の `groups` を兄弟へ展開(中6 庭方 2026-09-09)
    derive_clusters(d)         # 塊の箱は宣言(`boxFrom`)からの従属値(2026-09-07 中3)
    derive_view_clusters(d, g)  # 視線の塊の丈は跨ぐ帯の共通部分(2026-09-08)
    derive_view_eda(d)          # 視線の塊の枝下は `edaShitaFrom` の従属値(2026-09-08 中2)
    derive_viewpoints(d, g)     # 見所の眼高と向きは算出値(2026-09-08 B-3)
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
    _km_svg, _km_st = kirimori_svg(d, KAN[n[0] - 1], *_widen(d, gx0, gx1, gz0, gz1))
    fig(h, _km_svg,
        cap="<b>どこを盛り、どこを切るか。</b>地の色のままの所は<b>造成しない</b>(社叢・山麓の通り・坂の外)。"
            "<br>⭕ <b>造成の許容はこのまま — 面の高さは取り直さず、棟も動かさない</b>【ユーザー裁定 2026-09-07】。"
            "⛔ <b>CLAUDE.md 規則3(|設計面 − 自然地形| ≤ 0.5m)は屋敷の敷地内の目安で、山上の社地には当てない</b> — "
            "①社殿の位置は絵図が縛る ②山頂の平坦面は<b>松平主殿頭忠房の邸地を上収した</b>もので【B Web二次・原典未確認／<b>年次は【?】</b> — 市史稿の目次は万治元年4月11日「山王社営造」、遷座は万治2年4月25日とされ1年ずれる】"
            "<b>先行する大名屋敷の造成面である公算が高く</b>、Δ は社の普請の土工事の量を測っていない "
            "③Δ には近代の削平との差が混じる。"
            "⭕ <b>但し書きの実体は「外れている量を図に明記すること」</b> — 目安を超える棟と門は"
            "<b>この図と断面</b>が描き、検査『面に載る門・棟・井戸屋形の Δ』が面ごと・棟ごとに毎回刷る"
            "(⛔ 数を文章に写さない)。⛔ 考証方が挙げた第三の案(南列の2棟を東西に動かす)も採らない。"
            "<b>坂の通路も造成の対象に入れてある。</b>"
            + stair_cutfill_txt("男坂", _km_st, where="切盛図の銘") +
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
            "⭐ <b>境内の外周を回るのは腰高の柵</b>【S 存在・腰高の柵であること = 名所図会 コマ7 実見 / "
            "? 形式(格子・木柵・矢来の別) / U 部材の選択 = ユーザー裁定 2026-09-07】 — "
            "<b>作りは前庭の玉垣と同じ</b>(柱+貫二段+立子)で、"
            "丈は玉垣からの従属値。⛔ 板塀にも築地塀にもしない(どちらも典拠がゼロ)。"
            "⛔ <b>前庭の囲いと袖塀は板塀のまま</b>(裁定は『前庭以外』が対象)。"
            "⚠ 実装は築地塀を回したままで、指図と食い違う(「未解決」の節)。"
            "社殿を囲うのは透塀で、その正面に中門【S/A】。<b>10棟すべての銘に字が当たった</b>【S 字】(其一=薬師堂)。⚠ <b>鼓楼は上字が読めていない</b>【?】／<b>其五『カリウ堂』・其八『コマ堂』は建物としての同定が未確定</b>【U】で、名所図会の題箋の候補では埋めない。")
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
    uo = (-463.0 - g.x0) / ken                    # 断面ホ の位置
    y_ox = yk - (uo - st["a"][0]) / (st["b"][0] - st["a"][0]) * (yk - yz)

    CAP = {
      "EW847": ("<b>この図が指図の要。</b><b>左が西(本殿)・右が東(山麓)で、北を見る断面</b>。"
                "明治16年実測図の実測(<b>石段部の平面長 約35m・比高 28.2→14.2</b>)"
                "【A <code>[五千分一東京図31]</code> ／ P 当方の実測(図上)】と"
                "現地形の自然勾配(平均30.4%)【P — 造成前の地盤の正本】は一致しており、"
                "<b>男坂は斜面の全長に伸ばして現地形なりに乗せる</b>(CLAUDE.md 規則7=坂は現地形に従う)。"
                + stair_cutfill_txt("男坂", where="断面イ の銘") +
                "名所図会が描く「石段の両側の笠付きの土留め側壁」【S】はこの高さで足りる"
                "(⛔ 留保は `stair_cutfill_txt` が刷る一文が正典 — ここへ写さない)。"),
      "NS560": ("<b>左が南・右が北で、西を見る断面</b>。実際に切るのは<b>薬師堂(旧・附属堂其一)</b>1棟のみ"
                "(⚠ 本殿・観音堂・御供所はこの線より 11.9〜20.1m 東で、<b>この線上には無い</b>)。"
                "⚠ この線上の盛土は最大+1.13mにとどまる — 西肩の3m級盛土は本図・切盛図で読む。"),
      "SANDO": ("<b>二ノ鳥居から前庭の中まで、道の領域の中心線に沿って展開した縦断</b>。段は前庭へ上がる石段だけ。⭕ <b>参道の急な区間に段は入れない</b>【ユーザー裁定 2026-09-07】 — 局所の起伏は<b>路面の摺り付け(±0.3m 以内)</b>で吸収する。根拠は三つ: ①御宮絵図は男坂・女坂を梯子状の記号で描き分けるのに<b>参道の帯には梯子が一本も無い</b>【S 記号の不在】、②参道は切絵図で黄=道路に塗られた<b>公道</b>であり【S 切絵図の彩色】、<b>だから社が石段を築かない</b>【U 当方の読み — 公道の普請の主体を言う史料は無い】、③摺り付けは切盛図の無彩(±0.3m)の枠内なので『造成しない』と両立する【U 当方の読み — 『造成しない』の外延を当方が定めている】。⭕ <b>摺り付け量そのものは検査「参道の縦断の局所段差」が毎回刷る</b>【考証8巡目 低10 → 2026-09-07】 — ⛔ 数をここに写さない(許容と窓は `const.suritsukeM` / `const.suritsukeWinM` が正典)。⚠ <b>図に残る『参道の階』は別件</b> — 前庭の天端が作った段差で、同日の造成の裁定で面が一枚のままと決まったのでそのまま残る。"),
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
      "OTOKO_X": ("<b>男坂の横断(通路幅 7.0 m)。</b>"
                + stair_cutfill_txt("男坂", where="断面ホ の銘") +
                "路肩の土留めだけが立つ(⛔ ここにU字を掘らない)。"
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
                "北東の小丘を切った跡と、北縁の法面が読める。"
                "⭐ <b>2026-09-08 に両端を伸ばした</b>【中2・低1 庭方13巡目】 — "
                "西は<b>西の法尻の外</b>まで(旧端は法尻の手前で切れ、註が『法尻を写す』と"
                "書くのに写っていなかった)、東は同じ向きの断面イ・ヌ・ソ と<b>同じ通り</b>まで。"
                "<br>⚠ <b>東端の側は参道の路面を『縦に』切っている</b>【算出 — `sando.area` と"
                "造成前の地盤の正本】 — 社地の東境のすぐ外から参道の道敷(東西の帯)に入り、"
                "この線は<b>路面の中を長手に走る</b>。⛔ したがって<b>路肩と側溝はこの面には"
                "現れない</b>(北と南にある)。⛔ 庭方 裁定2『枝は路肩の上へ差し掛かるのは正・"
                "路面の上へは出さない』を<b>この断面で読ませようとしない</b> — それを測るのは"
                "平面の側の検査(参道の林縁の<b>張り出しの上限</b>=局所の路肩+側溝 − 余裕)で、"
                "その数は検査の一覧が v ごとに毎回刷る(⛔ 数をここに写さない)。"),
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
        elif key == "EW905":
            # ⭐ **窓の東端が何を写しているかを図の上で名指しする**【中2 庭方13巡目 → 2026-09-08】
            #    ── 旧図の SVG の文字は『柵・各層の銘・凡例』だけで、参道が銘を持たなかった
            #    (⛔ 註にしか無い判断は図では読めない)。
            # ⛔ 位置は数で持たない ── `sando.area` と `sando.roadside` からの従属値。
            # ⚠ **社地の境の銘は当図だけの飾りではない** ── `section_site_edges` が全断面へ
            #    一本の作法で立てる【中1 検図18巡目】。⛔ ここで重ねて描かない。
            _cr = _site_cross(d, "EW", sec["at"])
            _ce = _cr[-1][0]
            _rk = sando_rokata(d, g.V(sec["at"]))
            _ro = ("路肩 %.2f m ／ 側溝 %.2f m は**北と南**" % (_rk[0], _rk[1] - _rk[0])) \
                if _rk else "路肩と側溝は北と南"
            marks.append((_ce, prof[-1][0],
                          (series_at(prof, _ce) + series_at(prof, prof[-1][0])) / 2.0,
                          "参道 東西の帯 ── 路面を縦に切る(%s)" % _ro, "道", 0.25))
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
            "安政三年へ外挿した【U】</b>(2026-08-24 ユーザーの裁定 ── "
            "⛔ <b>プロジェクト内の推論なので B を名乗らない</b>。確度の別は 現況53段=【A】／"
            "安政3年への外挿=【U】／江戸期の段数=【?】。考証8巡目 中3)。"
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
            "【ユーザー裁定 2026-09-07】。⛔ <b>姿は種別(<code>kind</code>)で決める</b>"
            "(検図10巡目 中3 — 旧版は丈の宣言の有無で分岐しており、平面図と物差しが二本あった)。"
            "<br>⭐ <b>柵三本とも丈を宣言する</b>【裁き1 庭方 2026-09-07】 — "
            "<code>Ita_Keidai</code>(境内の外周)に加え、<code>Saku_SW</code>(社叢の法尻)と "
            "<code>Saku_Sando</code>(参道の楔形)も前庭の玉垣と同じ丈・同じ柱の芯々を引く"
            "(⛔ 独立の数を持たない)。それまで二本は丈も部材の行も持たず、<b>発注量から丸ごと"
            "抜けていた</b>。⭕ <b>玉垣・境内の外周・法尻の三者は同じ部材</b>なので、"
            "図の末尾に出る合計がそのまま<b>新造(edo-buzai)の発注量</b>で、⛔ この数は "
            "<code>bom</code> に持たない。")
    h.append(runs_table(d))
    h.append(walls_table(d))
    h.append("<h3>取り合い</h3>")
    h.append(joints_table(d))
    h.append('<p class="cap">⛔ <b>芯やピボットで位置を決めない</b>(CLAUDE.md 規則5)。'
             '<b>どの面がどの面に接するか</b>と、<b>どちらが動くか</b>を書く。')
    h.append("</div>")

    plate(h, nx(), "回廊の基壇の展開",
          "天端は `coping` 一定・**地盤なり**に描く ── 平面では読めない見付高(裁定 2026-09-09)")
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
             '絵図の銘は「樓門」【S 字 — 原図実見】、名所図会の題箋は「随身門」【S 字 — 原図実見】で、'
             '<b>この二つを同一の門の別称と読むのは当方の同定</b>【U】'
             '(位置が同一なので同定は堅いが、別称であると述べる史料は無い)。'
             'もう一基は男坂の下にあり、名所図会の題箋は「◯王門」=仁王門と読める【S 実見】。'
             '<b>実装名は「仁王門」</b>【U ユーザー判読 2026-09-01】だが、'
             '<b>御宮絵図の銘「二天門」(⚠ 上字はユーザー判読で自信なし)との食い違いは未決</b>【?】 — '
             '文政3と天保では年代が違い名が変わった可能性を潰せないので<b>両論のまま残す</b>'
             '(→ 未決の表「坂下の門の名」)。<b>形式も確定していない</b>【?】。<b>中門は[国宝建造物目録1941]の指定に'
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
    # ⭐ **焼いた点を描く図版**【低2 検図20巡目 → 2026-09-09】── 旧図は面と密度と本数の表しか
    #   持たず、焼いた 1,700 本余りの位置を描く図が**一面も無かった**(規則19)。
    h.append("<h3>焼き出した木の散布</h3>")
    fig(h, scatter_svg(d, g, KAN[n[0] - 1] + " 附図"),
        legend='<span style="color:#5F7A4E">● 帯(本体)</span>'
               '<span style="color:#8AA36B">● 林縁</span>'
               '<span style="color:#A8452C">● 塊(設計)</span>'
               '<span style="color:#C9A24B">● 景(視線の塊)</span>'
               '<span style="color:#3E4A55">● 一本立ち</span>'
               '<span style="color:#8C7F5E">● 区・前庭の帯</span>',
        cap='<b>この図は撒き直していない。</b>読んでいるのは <code>sanno_impl.json</code> の '
            '<code>planting.points</code> だけで、<b>実装がそのまま置く点</b>である。'
            '円は<b>樹冠の実寸</b>(部材の樹冠 × <code>scaleXZ</code>)、芯の点が幹。'
            '淡赤は<b>退避の面</b>(<code>keepoutFrom</code> が指す全ての宣言から組んだもの) — '
            '⛔ 点がそこに載っていれば不良で、検査「退避の表 <code>keepoutFrom</code> の一項ごとに…」が'
            '<b>全点 × 全形</b>で数えて止める。⛔ <b>0 件は合格ではなく未測定</b>なので、'
            '同じ検査が<b>退避の形が一つでも組めているか</b>も併せて見る'
            '(鍵が改名されて面が空になれば、違反 0 は「緩い条件で通った」証拠にしかならない)。')
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
    h.append(sankaku_table(d, g))
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
    h.append("<h4>部材の palette(用いる prefab)</h4>")
    h.append(palette_table(d))
    h.append('<p class="cap">⭐ <b>「用いる prefab」は算出値</b> — '
             '雛形(<code>{size}</code>)の点は <code>sizeRule</code> が丈から選ぶ変種の和集合で、'
             '⛔ 数を <code>json</code> にも文章にも写さない。'
             '⭕ <b>下草の3点をここで初めて刷る</b>【2026-09-08】 — '
             '宣言はあったのに html に一度も出ておらず、誰も検められなかった(規則19)。'
             '⭕ <b><code>Spring</code> を選ぶのは正しい</b> — この羊歯は目録に '
             '<code>Fall</code> と <code>Spring</code> の2変種しか無く、<b><code>Spring</code> が緑葉</b>。'
             '<code>Fall</code> は紅葉で当図の季節に合わない。'
             '⛔ <b>CLAUDE.md 規則10「季節は春ではない」を当てて <code>Fall</code> へ直さないこと</b> — '
             'あの規則が禁じているのは<b>開花木</b>であって部材名の綴りではない。</p>')
    h.append('<p class="cap">⭕ <b>植栽の部材は 2026-09-08 に全層そろった</b> — '
             '<b>常緑低木</b>(社叢の下層・林縁・前庭の帯・平場の縁の下層が待っていた唯一の欠品)は'
             '自作 <code>Own.Teiboku</code> が目録へ入って閉じ、'
             '<b>松</b>は在庫の黒松(丈が半分で箍を満たせない)から自作 <code>Own.Matsu</code> へ移した。'
             '⭕ <b>落葉高木3種(欅・椋・榎)は 2026-09-07 に <code>docs/asset-index.tsv</code> へ入った</b>'
             '(EDO-0150)ので、樹冠も三角数も部材から引ける — ⛔ 手値の樹冠へ戻さない。'
             '⚠ <b>仮値のときより樹冠は広い</b>ので、木陰・井戸屋形・木戸の裏・'
             '<b>参道への林縁の張り出し</b>の数は入れ替わった(⛔ 旧い数を引かない)。'
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
    # ⭐⭐ **破壊試験の総覧**【B-3 検図22巡目 → 2026-09-09 十九巡目】── ⛔ 手作業の一度きりで
    #    終わらせない。⛔ 「変異が図に当たったか」まで刷って初めて意味を持つ(規則19)。
    h.append('<h3 class="sub">破壊試験(検査が生きているか)</h3>')
    h.append(probe_roster_table(d, g))
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
             '<b>組み直すときは図を落としていないか必ず数える</b>(過去に16図版→1図版へ落ちた前科がある)。'
             '<br>@@NOTEMD@@</p>')
    h.append('<div class="foot">組んだ日 %s ／ 設計値 <code>sanno_sashizu.json</code> ／ '
             '文章 <code>sanno_kosho.md</code>。Y は海抜 m(Unity の Y がそのまま標高)。</div>'
             % subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip())
    h.append("</div>")
    html_out = note_cells("\n".join(h))          # 表のセルの行内記法(検図12巡目 低4)
    nmd = note_md_check(html_out)                # 通し残しが無いか
    tail = svg_tail_check(html_out)                  # (a) </svg> の後に要素を残さない
    lov = label_overlap_check(html_out)              # (c) 図版の銘の重なり(2026-09-08)
    # (d) ⭐ **男坂の読みの留保が、その読みを刷るすべての銘に出ているか**
    #     【中1 考証15巡目 → 2026-09-08】── 是正した読みが json/考証/切盛図では留保付きなのに、
    #     **印刷される断面の銘に無銘・無留保で現れていた**。⛔ 三枚を個別に直さない ── 一本の
    #     関数から刷り、**刷った回数と本文に現れる回数が一致すること**をここで数える。
    # ⚠ 数えるのは**関数だけが出す言い回し**にする ── 「これは安政三年の…」の一文そのものは
    #    考証(`sanno_kosho.md`)の地の文にも在り、そちらは銘ではないので数に混ぜない。
    _cvn = len(_STAIR_CF_N)
    _cvt = html_out.count("当図の設計面がその面に対してどう据わるか")
    # ⭐ **読みそのものが関数を経ているか**も数える【中1 検図18巡目 → 2026-09-08】── 旧版は
    #    留保の数しか見ておらず、⛔ **断面ホの読みを手書きの文へ差し替えても ⛔0件で通った**
    #    (記録は「刷った箇所 2 / 留保 2」で整合してしまう)。⛔ 註が「一本の関数から刷り」と
    #    宣言している以上、**読みの署名句の数も名簿の丈と一致しなければならない**。
    _sgt = html_out.count(_STAIR_CF_SIG)
    # (f) ⭐ **散布図が焼き出しの全点を描いているか**【低2 検図20巡目 → 2026-09-09】
    #     ⛔ 「図版を足した」で終わらせない ── 図の中の幹の点を数え直し、焼き出しの本数と
    #     一致しなければ止める(規則19 — 描いたつもりを許さない)。
    _spn = html_out.count('class="tp"')
    _spbad = []
    if _SCAT_N[0] is None:
        _spbad.append("焼き出した木の散布図が組まれていない — ⛔ 焼いた点を描く図版が図に無い"
                      "(低2 検図20巡目・規則19)")
    elif _spn != _SCAT_N[0]:
        _spbad.append("散布図の幹の点が図の中に %d、焼き出しの本数は %d — ⛔ 図が焼き出しの点を"
                      "全部描いていない" % (_spn, _SCAT_N[0]))
    _cvbad = []
    if _cvt != _cvn:
        _cvbad.append("男坂の切盛の読みを %d 箇所で刷ったのに、留保の一文は本文に %d 箇所しか無い — "
                      "⛔ 銘を一箇所から刷る形が壊れている" % (_cvn, _cvt))
    if _sgt != _cvn:
        _cvbad.append("男坂の切盛の読みを %d 箇所で刷ったのに、**読みの署名句**は本文に %d 箇所ある — "
                      "⛔ `stair_cutfill_txt` を経ずに読みを書いた銘があるか、銘が落ちている"
                      % (_cvn, _sgt))
    # (e) ⭐ **社地の境が断面の図の上に立っているか**【中1 検図18巡目 → 2026-09-08】
    #     ── 『窓は社地の境を跨ぐ』という不変条件を新設して三面の窓を動かしたのに、⛔ 図の上に
    #     境の銘が無く、読む人は跨いだかどうかを目で確かめられなかった(規則19 第3型)。
    #     ⛔ 作図側が立てた銘の数と、**組み上がった図の <text> にある銘の数**を突き合わせる。
    # ⛔ **突き合わせる相手は作図の副産物ではなく「立つはずの本数」**にする ── 作図の呼び出しを
    #    落としても、作図が数えた本数と図の本数は 0 と 0 で一致してしまう(⛔ 自分の出力を
    #    自分の物差しにしない)。立つはずの本数は `section_site_edges`(= 検査と同じ交点)から。
    _sexp = sum(len(section_site_edges(d, q["profile"], _profile(d, q["profile"])))
                for q in d["sections"])
    _sen = len(re.findall(r">社地の[西東南北]?境</text>", html_out))
    _sebad = []
    if _sen != _sexp:
        _sebad.append("社地の境の銘は断面に **%d 本**立つはずだが、図の中には **%d 本**しかない — "
                      "⛔ 作図が境の銘を立てていないか、銘が図から落ちている(規則19 第3型)"
                      % (_sexp, _sen))
    if len(_SITE_EDGE_N) != _sexp:
        _sebad.append("作図が立てた銘 %d 本と、立つはずの %d 本が食い違う — "
                      "⛔ 図と検査が別々の境を持っている" % (len(_SITE_EDGE_N), _sexp))
    # ⛔ **0件でも必ず刷る** — 件数が出ない検査は「回っていない」のと見分けが付かない(結線の門番)
    print("── 検査 6 本(組んだ後)──\n  図版の末尾(</g></svg>) ⛔ %d 件 ／ 〔記録〕 0 件\n"
          "  表のセルの行内記法(未変換のマークダウン)  ⛔ %d 件 ／ 〔記録〕 %d 件\n"
          "  図版の銘の重なり(⛔ にはしない)          ⛔ 0 件 ／ 〔記録〕 %d 件\n"
          "  男坂の読みと留保が同じ数だけ出るか        ⛔ %d 件 ／ 〔記録〕 1 件\n"
          "  社地の境の銘が断面の図に立っているか      ⛔ %d 件 ／ 〔記録〕 1 件\n"
          "  散布図が焼き出しの全点を描いているか      ⛔ %d 件 ／ 〔記録〕 1 件"
          % (len(tail), len(nmd[0]), len(nmd[1]), len(lov[1]), len(_cvbad), len(_sebad),
             len(_spbad)))
    print("  〔記録〕[散布図と焼き出し] 図の中の幹の点 **%s** ／ 焼き出しの本数 **%s**"
          "【算出 — ⛔ 図版を足しただけで終わらせない(低2 検図20巡目)】"
          % (_spn, _SCAT_N[0]))
    print("  〔記録〕[男坂の読みと留保] 読みを刷った箇所 **%d**(%s)／ 読みの署名句 **%d** ／ "
          "本文に現れる留保の一文 **%d**【算出 — ⛔ 銘を一箇所(`stair_cutfill_txt`)から刷る。"
          "⛔ 呼ぶ側で留保を書き足さない。⛔ 括弧の名簿も数と同じ名乗りからの従属値】"
          % (_cvn, "・".join(_STAIR_CF_N), _sgt, _cvt))
    print("  〔記録〕[社地の境の銘] 立つはずの銘 **%d** 本 ／ 作図が立てた銘 **%d** 本(%s)／ "
          "図の中の銘 **%d** 本【算出 — 位置は `_site_cross` の交点(検査『断面の窓が社地の境を"
          "跨ぐか』と同じ値)。⛔ 手で置かない】"
          % (_sexp, len(_SITE_EDGE_N), "・".join(_SITE_EDGE_N), _sen))
    for q in _spbad: sys.stderr.write("  ⛔ [散布図と焼き出し] %s\n" % q)
    for q in _cvbad: sys.stderr.write("  ⛔ [男坂の読みと留保] %s\n" % q)
    for q in _sebad: sys.stderr.write("  ⛔ [社地の境の銘] %s\n" % q)
    for q in lov[1]: print("  〔記録〕[図版の銘の重なり] %s" % q)
    for q in nmd[1]: print("  〔記録〕[表のセルの行内記法] %s" % q)
    for q in nmd[0]: sys.stderr.write("  ⛔ [表のセルの行内記法] %s\n" % q)
    if nmd[0]:
        sys.stderr.write("⛔ 表のセルに未変換のマークダウンが残っている — %d 件\n" % len(nmd[0]))
        sys.exit(1)
    if tail:
        sys.stderr.write("⛔ 図版が壊れている — %d 件:\n" % len(tail))
        for t in tail: sys.stderr.write("   ・%s\n" % t)
        sys.exit(1)
    if _cvbad:
        sys.stderr.write("⛔ 男坂の読みと留保の数が合わない — %d 件\n" % len(_cvbad))
        sys.exit(1)
    if _sebad:
        sys.stderr.write("⛔ 社地の境の銘が図に立っていない — %d 件\n" % len(_sebad))
        sys.exit(1)
    if _spbad:
        sys.stderr.write("⛔ 散布図が焼き出しの点を全部描いていない — %d 件\n" % len(_spbad))
        sys.exit(1)
    # ⛔ **組んだ後の検査も図に出す**(規則19・`wiring_gate --surfaced`)── stdout にしか無い
    #    検査結果は、読む人にとって存在しない。⚠ 註の変換は html を組んでからでないと測れないので、
    #    差し込み口(`@@NOTEMD@@`)を置いて後から埋める(`@@PLATES@@` と同じ作法)。
    html_out = html_out.replace(
        "@@NOTEMD@@",
        "組んだ後の検査(6本)── 図版の末尾(&lt;/g&gt;&lt;/svg&gt;)の残り <b>%d 件</b> ／ %s"
        " ／ %s ／ 男坂の読みを刷った箇所 <b>%d</b>・読みの署名句 <b>%d</b>・留保の一文 <b>%d</b>"
        " ／ <b>社地の境</b>の銘は 立つはず <b>%d</b> 本・図の中 <b>%d</b> 本"
        " ／ <b>散布図</b>の幹の点は 図の中 <b>%d</b>・焼き出し <b>%s</b> 本"
        "(⛔ どれも一致しなければ組ませない)"
        % (len(tail), html.escape(nmd[1][0]).replace("`", ""),
           html.escape(lov[1][-1]).replace("`", ""), _cvn, _sgt, _cvt,
           _sexp, _sen, _spn, _SCAT_N[0]))
    nsvg = html_out.count("<svg")
    # ⚠ 章の数ではなく **SVG の数**を数える(2026-08-23 検図 — 章を数えても落図を検出できない)
    html_out = html_out.replace("@@PLATES@@", "章 %d ／ 図版(SVG) %d 面" % (n[0], nsvg))
    open(OUT, "w", encoding="utf-8").write(html_out)
    print("wrote %s ／ 章 %d ／ 図版(SVG) %d 面" % (OUT, n[0], nsvg))


if __name__ == "__main__":
    if "--export-impl" in sys.argv:
        main_export_impl()
    else:
        main()
