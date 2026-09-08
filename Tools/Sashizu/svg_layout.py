#!/usr/bin/env python3
"""図の**字面**を機械で測り、重なり・枠外・**塗りへの潜り**・**小さすぎる字**を潰す。

⭐⭐ **なぜ機械で測るのか。** 2026-09-08 の検図で「文字どうしの重なり 49組/13面・
枠外へ出る文字 67件/24面」が出た。⛔ **目で一つずつ潰すと次の巡でまた増える** —
図版は毎巡ふえ、文字は設計値から組み立てられるので**値が変わるたびに幅が変わる**。
⇒ ⭕ **測る道具を図の中に置き、件数を刷る。**

⛔⛔ **2026-09-08 第5巡で分かったこと: 「重なり 0 件」は「読める」ではなかった。**
検図方が Chrome へ渡して**字あり/字なしの2枚を画素で引き算**したところ、
**銘が10件、そもそも紙に乗っていなかった** — ⚠ **後から描く塗りに上書きされて消えていた**
(f08 は面の高さの銘が5つまるごと不可視)。⭐ 原因の形は同じで、
**`text` × `text` しか測らない物差しには「文字が塗りに覆われる」が構造的に見えない**。
⇒ **0 件は「無い」ではなく「探していない」。**⭕ この版で三つ足した:

  ① **潜り(覆われた銘)** — `text` より**後ろ**に、その字面と交わる**不透明な塗り**があるか。
     ⛔ 再レンダは要らない — **描画順の照合**で出る。⭕ 直しは `relayout` が
     **銘を面の末尾へまとめて送る**(= 常に最後に描く)。
  ② **字送りの下限** — 和字を含む字面の**実効 px**(基準の窓での見え方)が `MIN_EFF` 未満。
     ⛔ 「書いてある」と「読める」は別物で、⚠ **字を小さくするほど重なりの検査には
     当たらなくなる**(宣言された寸法で箱を組むため)= 検査の向きが読めなさを罰していない。
  ③ **推定幅の安全率** — 1字の em を最小二乗で解き直した(下表)。⛔ 一般約物を 0.5em と
     見誤っており、**+92% の過小**で 8件/5面が枠から出ていた。

【この道具の物差し(近似であることを隠さない)】
指図は SVG を**ブラウザに渡す前に**組む。⛔ 生成器はフォントを持たないので、
**字送りは近似**である。⭐ 値は検図方が 1,012 字面の `getBBox()` から**最小二乗で解いた実測**:
和字/記号 0.984 / 数字 0.569 / 一般約物 0.962 / 空白 0.376 em。
⚠ それでも 1〜3% は残るので、**`SAFE` を掛けて安全側へ倒す**。
⇒ 名乗れるのは「**この物差しで 0 件**」であって「重なっていない」ではない。
⭕ 裏は検図方がレンダして目で取る。⭐ **道具の非対称**(機械は全面を網羅できるが精度が粗い /
目は精度が高いが 43 面を毎巡は見られない)を、そのまま役の分担にしてある。

【この版でも測っていないこと(⛔ 次の巡へそのまま渡す)】
⛔ **窓の幅**: 実効 px は `VIEW_W`(基準の窓)での値。⚠ 窓を狭めれば svg は縮み、
   字はそのぶん小さくなる(`.fig svg{width:100%}`)。⇒ **狭い窓での読めなさは測っていない**。
⛔ **塗りの色**: 潜りは「不透明な塗りが後ろに在るか」しか見ない。⚠ **薄い色の上の薄い字**
   (低いコントラスト)は鳴らない。
⛔ **字の形**: 字送りは幅だけで、⚠ **合字・縦組み・約物の詰め**は見ていない。

【字の大きさと寄せは `sashizu.css` が正典】
⛔ 表をここに書き写さない(CLAUDE.md 絶対規則4)。`sashizu.css` を読んで組み立てる。
⚠ CSS のクラス規則は presentation attribute に勝つので、**`style=` で上書きした分だけ**が
クラスの既定を覆す(生成器の `T()` がそう出している)。

【使い方】
    doc, rep = svg_layout.relayout(doc)   # 直してから
    rep2     = svg_layout.check(doc)      # 直った図を測る(rep2 が刷る値)
"""
import html as _html
import math
import os
import re

CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sashizu.css")

_RE_SVG = re.compile(r'(<svg\b[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"[^>]*>)(.*?)(</svg>)', re.S)
_RE_TXT = re.compile(r'<text\b([^>]*)>(.*?)</text>', re.S)
_RE_ATT = re.compile(r'([a-zA-Z-]+)="([^"]*)"')
_RE_RULE = re.compile(r'\.([A-Za-z][\w-]*)\s*\{([^}]*)\}')

TOL = 0.5          # px。この物差しの粗さより小さい当たりは数えない
MIN_AREA = 0.5     # px²。角がかすめるだけの当たりは数えない
PAD = 4.0          # px。枠の内側にこれだけ残す

# ⭐ **推定幅の安全率。** 1字の em を実測で入れ替えてもなお 1〜3% は残る
#   (書体・字詰め・端末)。⛔ 端数を「たぶん入る」で通さない。
SAFE = 1.06
_WS = [1.0]        # ⚠ **破壊試験だけが振る**。既定 1.0(⛔ 生成では触らない)

# ⭐ **基準の窓での svg の実表示幅[px]。** `sashizu.css` の `.wrap{max-width:1120;padding:0 24}`
#   と `.fig{padding:14}` から 1120 − 24×2 − 14×2 = 1044。⚠ **これより狭い窓は測っていない。**
VIEW_W = 1044.0
MIN_EFF = 8.5      # px。和字を含む字面の実効 px の下限(これ未満は「読めない」)

# ⭐ 覆いの判定。⛔ 半透明の薄掛けは「覆い」と呼ばない
ALPHA_MIN = 0.5    # 塗りの実効不透明度がこれ以上なら覆う物とみなす
COVER_FR = 0.6     # 1字の箱のこれだけが塗りの下なら、その字は乗っていない


# ---------------------------------------------------------------- 字の物差し
def css_classes(path=CSS):
    """`sashizu.css` → {クラス名: (font-size, text-anchor, letter-spacing[em])}。"""
    t = open(path, encoding="utf-8").read()
    out = {}
    for m in _RE_RULE.finditer(t):
        body = m.group(2)
        fs = re.search(r"font-size:\s*([\d.]+)px", body)
        an = re.search(r"text-anchor:\s*(\w+)", body)
        ls = re.search(r"letter-spacing:\s*([\d.]+)em", body)
        if fs or an or ls:
            out[m.group(1)] = (float(fs.group(1)) if fs else None,
                               an.group(1) if an else None,
                               float(ls.group(1)) if ls else 0.0)
    return out


def _adv(ch):
    """1字の字送り[em]。⭐ 2026-09-08、検図方が 1,012 字面の実測から解き直した値。

    ⛔ **一般約物(— … ‥)を 0.5 と見誤っていた** — 実測 0.962 で **+92% の過小**。
    ⚠ 空白も 0.28 → 0.376、数字も 0.556 → 0.569 が実測。⭕ 安全側へ丸めて持つ。
    """
    o = ord(ch)
    if ch == " ":
        return 0.38                                # 実測 0.376
    if o < 0x300:                                  # 欧文・数字・約物
        if ch in ".,:;'`|!ilj()[]{}/\\-":
            return 0.32
        if ch.isdigit():
            return 0.57                            # 実測 0.569
        if ch.isupper():
            return 0.68
        return 0.56
    if 0x2000 <= o <= 0x206F:                      # 一般約物(— … ‥)
        return 1.0                                 # 実測 0.962 ⇒ 安全側へ 1.0
    if 0x2190 <= o <= 0x2BFF:                      # 記号(→ ⛔ ⭐ ⭕ ⚠ ①②)
        return 1.0
    return 1.0                                     # 和字・全角(実測 0.984)


def adv_px(ch, fs, ls=0.0):
    """1字ぶんの送り[px]。⛔ `text_w` と同じ安全率を掛ける(2つの物差しを持たない)。"""
    return fs * (_adv(ch) + ls) * SAFE * _WS[0]


def text_w(s, fs, ls=0.0):
    return fs * (sum(_adv(c) for c in s) + ls * max(0, len(s) - 1)) * SAFE * _WS[0]


def has_kana(s):
    """和字(仮名・漢字・全角)を含むか。⚠ 欧字と数字だけの識別子は下限の対象にしない。"""
    return any(0x3000 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF
               or 0xFF00 <= ord(c) <= 0xFFEF for c in s)


ASC, DESC = 0.78, 0.18     # 基線からの上下[em]


class Tx(object):
    """1個の `<text>`。"""

    __slots__ = ("i", "span", "att", "s", "cls", "fs", "an", "ls", "x", "y",
                 "lines", "drop", "moved", "x0", "y0", "par", "kept")

    def __init__(self, i, span, att, s, cls, fs, an, ls, x, y, par=-1):
        self.i, self.span, self.att, self.s = i, span, att, s
        self.cls, self.fs, self.an, self.ls = cls, fs, an, ls
        self.x, self.y = x, y
        self.x0, self.y0 = x, y      # ⭐ **もとの位置**(寄せた量はここからの差で数える)
        self.par = par               # 親の `<g>` の番号(-1 = svg 直下)
        self.lines = [s]
        self.drop = False
        self.kept = False        # 枠の外へ丸ごと出ていたが、他に無い銘なので落とさなかった
        self.moved = 0.0

    @property
    def lh(self):
        return self.fs * 1.18

    def w(self, s=None):
        return text_w(self.s if s is None else s, self.fs, self.ls)

    def box_of(self, s, y):
        w = self.w(s)
        x0 = self.x if self.an == "start" else (
            self.x - w / 2.0 if self.an == "middle" else self.x - w)
        return (x0, y - self.fs * ASC, x0 + w, y + self.fs * DESC)

    def char_boxes(self, s, y):
        """1字ずつの箱。⭐ **潜りは字ごとに測る** — ⚠ 「前庭 21.9」の『前庭』だけが
        塗りに隠れて『21.9』だけ残る、という消え方をするため。"""
        b = self.box_of(s, y)
        x = b[0]
        out = []
        for ch in s:
            w = adv_px(ch, self.fs, self.ls)
            out.append((ch, (x, b[1], x + w, b[3])))
            x += w
        return out

    def ys(self):
        """行ごとの基線 y。下端に近い文字は**上へ**積む(枠から落とさない)。"""
        n = len(self.lines)
        if n == 1:
            return [self.y]
        return [self.y - (n - 1 - k) * self.lh for k in range(n)]

    def boxes(self):
        return [self.box_of(s, y) for s, y in zip(self.lines, self.ys())]

    def eff(self, W):
        """基準の窓での実効 px。⚠ **窓がこれより狭ければさらに小さい**(測っていない)。"""
        return self.fs * VIEW_W / W


def parse(body, cls_tab, parents=None):
    out = []
    for i, m in enumerate(_RE_TXT.finditer(body)):
        a = dict(_RE_ATT.findall(m.group(1)))
        cls = a.get("class", "")
        fs, an, ls = cls_tab.get(cls, (None, None, 0.0))
        fs = fs or 12.0
        an = an or "start"
        st = a.get("style", "")
        m2 = re.search(r"font-size:\s*([\d.]+)px", st)
        if m2:
            fs = float(m2.group(1))
        m3 = re.search(r"text-anchor:\s*(\w+)", st)
        if m3:
            an = m3.group(1)
        par = parents.get(m.start(), -1) if parents else -1
        out.append(Tx(i, m.span(), a, _html.unescape(m.group(2)), cls, fs, an, ls,
                      float(a.get("x", 0.0)), float(a.get("y", 0.0)), par))
    return out


# ---------------------------------------------------------------- 図形の読み取り
_RE_EL = re.compile(r'<(text|rect|polygon|polyline|path|circle|line|g|/g|defs|/defs'
                    r'|clipPath|/clipPath|pattern|/pattern)\b([^>]*?)(/?)>', re.S)
_RE_NUM = re.compile(r'-?[\d.]+(?:[eE]-?\d+)?')


def _alpha(a):
    try:
        return float(a.get("opacity", 1.0) or 1.0) * float(a.get("fill-opacity", 1.0) or 1.0)
    except ValueError:
        return 1.0


def _poly_area(p):
    s = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _clip_box(poly, box):
    """Sutherland–Hodgman。⛔ 乱数もサンプリングも使わない(決定的・厳密)。"""
    x0, y0, x1, y1 = box
    edges = [(lambda q: q[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
             (lambda q: q[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
             (lambda q: q[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
             (lambda q: q[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1))]
    p = poly
    for ins, inter in edges:
        if not p:
            return []
        out = []
        n = len(p)
        for i in range(n):
            a, b = p[i], p[(i + 1) % n]
            ia, ib = ins(a), ins(b)
            if ia:
                out.append(a)
                if not ib:
                    out.append(inter(a, b))
            elif ib:
                out.append(inter(a, b))
        p = out
    return p


def _path_polys(d):
    """`M/L/H/V/Z` だけの path を多角形へ。⛔ 曲線が出たら **None**(= 測れないと申告)。"""
    toks = re.findall(r'[A-Za-z]|-?[\d.]+(?:[eE]-?\d+)?', d)
    polys, cur = [], []
    x = y = sx = sy = 0.0
    i, cmd = 0, None
    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t
            i += 1
            if cmd in ("Z", "z"):
                if cur:
                    polys.append(cur)
                    cur = []
                x, y = sx, sy
                continue
            if cmd not in ("M", "m", "L", "l", "H", "h", "V", "v"):
                return None
            if i >= len(toks):
                break
        if cmd in ("M", "m"):
            if cur:
                polys.append(cur)
                cur = []
            nx, ny = float(toks[i]), float(toks[i + 1])
            i += 2
            x, y = (nx, ny) if cmd == "M" else (x + nx, y + ny)
            sx, sy = x, y
            cur = [(x, y)]
            cmd = "L" if cmd == "M" else "l"
        elif cmd in ("L", "l"):
            nx, ny = float(toks[i]), float(toks[i + 1])
            i += 2
            x, y = (nx, ny) if cmd == "L" else (x + nx, y + ny)
            cur.append((x, y))
        elif cmd in ("H", "h"):
            nx = float(toks[i])
            i += 1
            x = nx if cmd == "H" else x + nx
            cur.append((x, y))
        elif cmd in ("V", "v"):
            ny = float(toks[i])
            i += 1
            y = ny if cmd == "V" else y + ny
            cur.append((x, y))
        else:
            return None
    if cur:
        polys.append(cur)
    return [p for p in polys if len(p) >= 3]


def _shape_polys(tag, a):
    """塗りとして紙を覆う多角形。⛔ 線(`line`)と塗り無しは覆わない。"""
    if tag == "rect":
        try:
            x, y = float(a.get("x", 0)), float(a.get("y", 0))
            w, h = float(a.get("width", 0)), float(a.get("height", 0))
        except ValueError:
            return []
        return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]] if w > 0 and h > 0 else []
    if tag in ("polygon", "polyline"):
        v = [float(q) for q in _RE_NUM.findall(a.get("points", ""))]
        p = list(zip(v[0::2], v[1::2]))
        return [p] if len(p) >= 3 else []
    if tag == "circle":
        try:
            cx, cy, r = float(a.get("cx", 0)), float(a.get("cy", 0)), float(a.get("r", 0))
        except ValueError:
            return []
        if r <= 0:
            return []
        return [[(cx + r * math.cos(k * math.pi / 12), cy + r * math.sin(k * math.pi / 12))
                 for k in range(24)]]
    if tag == "path":
        return _path_polys(a.get("d", "")) or []
    return []


def _scan_els(body):
    """面の中の要素を**描画順**で拾う。⛔ `<defs>/<pattern>/<clipPath>` の中は紙に出ない。

    戻り: `(els, parents, groups)`
      els     = [(tag, 位置, 属性, 親の番号)] — text も含む(描画順の照合に要る)
      parents = {text の開始位置: 親の番号}
      groups  = {番号: (開き札の属性, 閉じ札の位置)}
    """
    els, parents, groups = [], {}, {}
    stack, gid, indefs = [-1], 0, 0
    for em in _RE_EL.finditer(body):
        tag, astr = em.group(1), em.group(2)
        if tag in ("defs", "pattern", "clipPath"):
            indefs += 1
            continue
        if tag in ("/defs", "/pattern", "/clipPath"):
            indefs -= 1
            continue
        if indefs > 0:
            continue
        if tag == "g":
            gid += 1
            groups[gid] = (dict(_RE_ATT.findall(astr)), None)
            stack.append(gid)
            continue
        if tag == "/g":
            g = stack.pop()
            if g in groups:
                groups[g] = (groups[g][0], em.start())
            continue
        els.append((tag, em.start(), dict(_RE_ATT.findall(astr)), stack[-1]))
        if tag == "text":
            parents[em.start()] = stack[-1]
    return els, parents, groups


def _clip_defs(body):
    """`<clipPath id=…>` → その中身の文字列。"""
    return {m.group(1): m.group(2)
            for m in re.finditer(r'<clipPath[^>]*\bid="([^"]+)"[^>]*>(.*?)</clipPath>', body, re.S)}


def _group_open(att, clips, W, H):
    """その `<g>` から銘を**外へ出してよい**か。

    ⭕ 出してよいのは「紙の見え方を変えない群」だけ — ⛔ `transform`/`opacity`/`mask`/
    `filter`/`style` を持つ群からは出さない。⚠ `clip-path` は**枠いっぱいの矩形**なら
    (= 単に画枠で切っているだけなので)出してよい。
    """
    for k in att:
        if k not in ("clip-path", "id", "class"):
            return False
    cp = att.get("clip-path", "")
    if not cp:
        return True
    m = re.match(r'url\(#([^)]+)\)', cp)
    if not m or m.group(1) not in clips:
        return False
    inner = clips[m.group(1)]
    rs = re.findall(r'<rect\b([^>]*)>', inner)
    if len(rs) != 1 or "<path" in inner or "<polygon" in inner or "<circle" in inner:
        return False
    a = dict(_RE_ATT.findall(rs[0]))
    try:
        x, y = float(a.get("x", 0)), float(a.get("y", 0))
        w, h = float(a.get("width", 0)), float(a.get("height", 0))
    except ValueError:
        return False
    return x <= 0.01 and y <= 0.01 and x + w >= W - 0.01 and y + h >= H - 0.01


# ---------------------------------------------------------------- 是正
_BRK = "、。・)】」』/ →—"          # ここの直後で折る


def wrap(t, avail):
    """幅 `avail` に収まるよう折り返す。⛔ 語の途中で折るのは最後の手段。

    ⚠ **文中の改行は硬い折れ目**として先に割る(和文の注記に素で入っている)。
    """
    if "\n" in t.s:
        out = []
        for seg in t.s.split("\n"):
            out.extend(_wrap1(t, seg.strip(), avail) if seg.strip() else [""])
        return [x for x in out if x != ""] or [t.s]
    return _wrap1(t, t.s, avail)


def _wrap1(t, s0, avail):
    if text_w(s0, t.fs, t.ls) <= avail or avail < t.fs * 3:
        return [s0]
    lines, cur, last = [], "", -1
    for ch in s0:
        if text_w(cur + ch, t.fs, t.ls) > avail and cur:
            if last > 0 and last < len(cur) - 1:
                lines.append(cur[:last + 1])
                cur = cur[last + 1:]
            else:
                lines.append(cur)
                cur = ""
            last = -1
        cur += ch
        if ch in _BRK:
            last = len(cur) - 1
    if cur:
        lines.append(cur)
    return lines or [s0]


def clamp(t, W, H):
    """箱が枠に収まるよう x と y を寄せる(寄せ方は変えない)。"""
    bs = t.boxes()
    dx = 0.0
    lo = min(b[0] for b in bs) + dx
    hi = max(b[2] for b in bs) + dx
    if lo < PAD:
        dx += PAD - lo
    hi = max(b[2] for b in bs) + dx
    if hi > W - PAD:
        dx -= hi - (W - PAD)
    if min(b[0] for b in bs) + dx < PAD:            # 幅が枠より広い(折れなかった)
        dx = PAD - min(b[0] for b in bs)
    t.x += dx
    ys = t.ys()
    dy = 0.0
    if min(ys) - t.fs * ASC < PAD:
        dy = PAD - (min(ys) - t.fs * ASC)
    if max(ys) + t.fs * DESC + dy > H - PAD:
        dy = (H - PAD) - (max(ys) + t.fs * DESC)
    t.y += dy


def _ov(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _hits(bs, placed):
    return sum(_ov(a, b) for a in bs for b in placed)


def deoverlap(ts, W, H):
    """当たったら**縦へ寄せる**。⛔ 乱数を使わない(決定的)。

    ⭐ 置く順は**幅の広い順**(同幅は文書順)。⚠ 文書順に置くと、最後に来る長い注記が
    先に置かれた短い銘に阻まれて**動く先を失う** — 動かすべきは短い銘のほうである。
    """
    placed = []
    for t in sorted([q for q in ts if not q.drop],
                    key=lambda q: (-max(b[2] - b[0] for b in q.boxes()), q.i)):
        if not _hits(t.boxes(), placed):
            placed.extend(t.boxes())
            continue
        base_y, base_x = t.y, t.x
        cands = []
        for k in range(1, 9):                       # まず縦へ(1/2 行ずつ)
            for sg in (1, -1):
                cands.append((0.0, sg * k * t.lh * 0.5))
        for k in range(1, 9):                       # それでも駄目なら横も
            for sg in (1, -1):
                for dy in (0.0, t.lh, -t.lh, 2 * t.lh, -2 * t.lh):
                    cands.append((sg * k * 6.0, dy))
        for k in range(9, 61):                      # 最後は縦へ大きく探す
            for sg in (1, -1):
                cands.append((0.0, sg * k * t.lh * 0.5))
        best, bestpen = None, None
        for dx, dy in cands:
            t.x, t.y = base_x + dx, base_y + dy
            clamp(t, W, H)
            pen = _hits(t.boxes(), placed)
            d = abs(t.x - base_x) + abs(t.y - base_y)
            if pen <= 0.0:
                best = (t.x, t.y)
                break
            if bestpen is None or (pen, d) < bestpen:
                bestpen, best = (pen, d), (t.x, t.y)
        t.x, t.y = best
        placed.extend(t.boxes())


def _emit(t):
    att = dict(t.att)
    out = []
    for s, y in zip(t.lines, t.ys()):
        a = '<text'
        for k in ("class", "x", "y", "style"):
            if k == "x":
                a += ' x="%.1f"' % t.x
            elif k == "y":
                a += ' y="%.1f"' % y
            elif k in att:
                a += ' %s="%s"' % (k, att[k])
        for k, v in att.items():
            if k not in ("class", "x", "y", "style"):
                a += ' %s="%s"' % (k, v)
        out.append(a + ">%s</text>" % _html.escape(s, quote=False))
    return "".join(out)


def _fig_strings(doc, tab):
    """面ごとの字面の集合。⭐ **落としてよいかの判定に要る** — 枠外へ丸ごと出た字でも、
    ⛔ **その銘が他の面のどこにも無ければ、落とすと情報が消える。**"""
    out = []
    for m in _RE_SVG.finditer(doc):
        out.append(set(t.s for t in parse(m.group(4), tab)))
    return out


def relayout(doc, cls_tab=None):
    """重なり・枠外・潜りを潰した文書を返す。⭕ 冪等(2度掛けても同じ)。"""
    tab = cls_tab or css_classes()
    figstr = _fig_strings(doc, tab)
    rep = {"dropped": 0, "wrapped": 0, "moved": 0, "grown": 0, "figs": 0,
           "droppedList": [], "movedMax": 0.0, "movedFar": 0,
           "kept": 0, "keptList": [], "keptMoveMax": 0.0,
           "reordered": 0, "reordFigs": 0}
    out, at = [], 0
    for m in _RE_SVG.finditer(doc):
        W, H = float(m.group(2)), float(m.group(3))
        body = m.group(4)
        _els, parents, groups = _scan_els(body)
        clips = _clip_defs(body)
        ts = parse(body, tab, parents)
        rep["figs"] += 1
        fi = rep["figs"] - 1
        for t in ts:
            b = t.box_of(t.s, t.y)
            if b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H:
                # ⭐⭐ **落としてよいのは「同じ銘が他の面に残っている」ときだけ**
                #   (2026-09-08 検図方)。⛔ 従前の規則(枠外なら落とす)には
                #   その条件が入っておらず、**情報の喪失を検査していなかった**。
                elsewhere = any(t.s in s for j, s in enumerate(figstr) if j != fi)
                if elsewhere:
                    t.drop = True
                    rep["dropped"] += 1
                    rep["droppedList"].append((rep["figs"], t.s))
                    continue
                t.kept = True
                rep["kept"] += 1
                rep["keptList"].append((rep["figs"], t.s))
            t.lines = wrap(t, W - 2 * PAD)
            if len(t.lines) > 1:
                rep["wrapped"] += 1
        # ⭐ **下端の注記が折れた分だけ枠を下へ伸ばす。** ⛔ 図の上へ被せて逃げない —
        #   折った注記を絵の上に積むと、字は読めても**絵が読めなくなる**。
        grow = sum((len(t.lines) - 1) * t.lh for t in ts
                   if not t.drop and len(t.lines) > 1 and t.y > H - 3 * t.lh)
        if grow:
            for t in ts:
                if not t.drop and t.y > H - 3 * t.lh:
                    t.y += grow
                    t.y0 += grow          # ⚠ 枠を伸ばした分は「寄せた」に数えない
            H = float(math.ceil(H + grow))   # ⚠ viewBox は整数で出す(丸めで冪等が崩れる)
            rep["grown"] += 1
        for t in ts:
            if not t.drop:
                clamp(t, W, H)
        deoverlap(ts, W, H)
        # ⭐⭐ **「寄せた」は最初の位置からの実移動で数える**(2026-09-08 検図方 中4)。
        #   ⛔⛔ 従前は `deoverlap` の移動だけを数え、**`clamp`(枠内へ押し込む横移動)を
        #   数えていなかった** — ⚠ 押し込みのほうが「銘が指す物から離れる」危険は大きい。
        #   ⚠ **枠の外から拾い上げた銘は別勘定**にする — 何百 px も動くのは当たり前で、
        #   ⛔ 混ぜると「寄せの最大」が読めなくなる(上の行が別に数えている)。
        for t in ts:
            if t.drop:
                continue
            t.moved = abs(t.x - t.x0) + abs(t.y - t.y0)
            if t.kept:
                rep["keptMoveMax"] = max(rep["keptMoveMax"], t.moved)
                continue
            if t.moved > 0.05:
                rep["moved"] += 1
        rep["movedMax"] = max([rep["movedMax"]]
                              + [t.moved for t in ts if not t.drop and not t.kept])
        rep["movedFar"] += sum(1 for t in ts if not t.drop and not t.kept and t.moved > 40.0)
        # ⭐⭐ **銘は最後にまとめて描く**(2026-09-08 検図方 高2)。
        #   ⛔⛔ 従前は作図した順のまま出していたので、**後から描く面の塗りが銘を上塗り**して
        #   いた(f08 は面の高さの銘が5つまるごと不可視)。⇒ 面の末尾へ送る。
        #   ⚠ **紙の見え方を変える群**(transform/opacity/mask など)からは出さない。
        keep_in = {}
        tail = []
        for t in ts:
            if t.drop:
                continue
            g = t.par
            if g != -1 and not _group_open(groups.get(g, ({}, None))[0], clips, W, H):
                keep_in.setdefault(g, []).append(t)
            else:
                tail.append(t)
        rep["reordered"] += len(tail)
        acts = [(t.span[0], t.span[1], None) for t in ts]
        for g, lst in keep_in.items():
            p = groups[g][1]
            if p is not None:
                acts.append((p, p, lst))
        acts.sort(key=lambda a: a[0])
        nb, prev = [], 0
        for a0, a1, lst in acts:
            nb.append(body[prev:a0])
            if lst:
                nb.append("".join(_emit(q) for q in lst))
            prev = a1
        nb.append(body[prev:])
        nb.append("".join(_emit(q) for q in tail))
        if tail:
            rep["reordFigs"] += 1
        out.append(doc[at:m.start()])
        head = m.group(1)
        if H != float(m.group(3)):
            head = head.replace('viewBox="0 0 %s %s"' % (m.group(2), m.group(3)),
                                'viewBox="0 0 %s %.0f"' % (m.group(2), H))
        out.append(head + "".join(nb) + m.group(5))
        at = m.end()
    out.append(doc[at:])
    return "".join(out), rep


# ---------------------------------------------------------------- 検査
def check(doc, cls_tab=None):
    """⛔ 直した後の文書を測る。返すのは**件数と実例**。

    測るのは四つ — ⑴ 字どうしの重なり ⑵ 枠の外 ⑶ **塗りに潜った銘** ⑷ **小さすぎる字**。
    """
    tab = cls_tab or css_classes()
    ov, of, cv, tn, figs, nt = [], [], [], [], 0, 0
    for m in _RE_SVG.finditer(doc):
        figs += 1
        W, H = float(m.group(2)), float(m.group(3))
        body = m.group(4)
        els, parents, groups = _scan_els(body)
        ts = parse(body, tab, parents)
        tpos = {t.span[0]: t for t in ts}
        bs = []
        for t in ts:
            for b in t.boxes():
                bs.append((b, t.s))
            if has_kana(t.s) and t.eff(W) < MIN_EFF - 1e-9:
                tn.append((figs, t.eff(W), t.s))
        nt += len(bs)
        for j in range(len(bs)):
            for k in range(j + 1, len(bs)):
                a = _ov(bs[j][0], bs[k][0])
                if a > MIN_AREA:
                    ov.append((figs, a, bs[j][1], bs[k][1]))
        for b, s in bs:
            d = max(-b[0], -b[1], b[2] - W, b[3] - H)
            if d > TOL:
                of.append((figs, d, s))
        # ⑶ **潜り** — 描画順で自分より後ろにある不透明な塗りが、字の箱を覆っているか。
        #   ⛔ **z 順は文書順**(親の群は関係ない)ので、群の中の銘も外の塗りに覆われる。
        paints = [(i9, e) for i9, e in enumerate(els)
                  if e[0] not in ("text", "line")
                  and e[2].get("fill", "") not in ("", "none")
                  and _alpha(e[2]) >= ALPHA_MIN]
        for i9, e in enumerate(els):
            if e[0] != "text":
                continue
            t = tpos.get(e[1])
            if t is None:
                continue
            for line, y in zip(t.lines, t.ys()):
                cb = t.char_boxes(line, y)
                hit = []
                for j9, e2 in paints:
                    if j9 <= i9:
                        continue
                    for pg in _shape_polys(e2[0], e2[2]):
                        xs = [q[0] for q in pg]
                        ys = [q[1] for q in pg]
                        if (max(xs) < cb[0][1][0] or min(xs) > cb[-1][1][2]
                                or max(ys) < cb[0][1][1] or min(ys) > cb[0][1][3]):
                            continue
                        for k9, (ch, box) in enumerate(cb):
                            if k9 in hit or ch == " ":
                                continue
                            ar = (box[2] - box[0]) * (box[3] - box[1])
                            if ar <= 0:
                                continue
                            cp = _clip_box(pg, box)
                            if cp and _poly_area(cp) / ar >= COVER_FR:
                                hit.append(k9)
                if hit:
                    cv.append((figs, line, len(hit), len(line),
                               "".join(cb[k9][0] for k9 in sorted(set(hit)))))
    return {"figs": figs, "texts": nt, "overlap": ov, "outframe": of,
            "covered": cv, "tiny": tn,
            "ovFigs": len(set(x[0] for x in ov)),
            "ofFigs": len(set(x[0] for x in of)),
            "cvFigs": len(set(x[0] for x in cv)),
            "tnFigs": len(set(x[0] for x in tn))}


def counts(r):
    """`check` の四つの件数。⛔ 順を他所で並べ替えない。"""
    return (len(r["overlap"]), len(r["outframe"]), len(r["covered"]), len(r["tiny"]))


# ---------------------------------------------------------------- 破壊試験
def probes(doc, raw=None, cls_tab=None):
    """⭐⭐ **この検査が生きていることを毎回見せる**(規則19)。

    ⛔⛔ **「0 件」だけを刷ると、検査が死んでいても 0 と読める。**⇒ ⭕ 直した文書へ
    **わざと欠陥を差し込み**、鳴ることを確かめる。⛔ 乱数を使わない(決定的)。
    返すのは `[(題, 実測(重なり, 枠外, 潜り, 小字), 期待)]`。

    ⚠ `raw` = **直す前**の文書。⭐ 「推定幅を 0.95 倍する」束はこれが要る —
    ⛔ 直した後の図を 0.95 で組み直しても、`clamp` は内へしか押さないので鳴らない。
    """
    tab = cls_tab or css_classes()
    out = []
    m = _RE_SVG.search(doc)
    if m is None:
        return [("⛔ 図版が1面も無い — **この検査は回っていない**", (-1, -1, -1, -1),
                 ("0", "0", "0", "0"))]
    W, H, body = float(m.group(2)), float(m.group(3)), m.group(4)
    ts = parse(body, tab)
    if len(ts) < 2:
        return [("⛔ 1面目の字面が2つ未満 — **試験を差し込めない**", (-1, -1, -1, -1),
                 ("0", "0", "0", "0"))]
    a, b = ts[0], ts[1]

    def _mut(nb):
        dc = doc[:m.start()] + m.group(1) + nb + m.group(5) + doc[m.end():]
        return counts(check(dc, tab))

    def _repl(span, s):
        return body[:span[0]] + s + body[span[1]:]

    # ① 1つ目の字面を2つ目の**真上へ重ねる** ⇒ 重なりが鳴る
    out.append(("① ⭐ 1つ目の字面を2つ目の**真上へ重ねる** — ⚠ **重なりが鳴る**",
                _mut(_repl(a.span, '<text class="%s" x="%.1f" y="%.1f" style="%s">%s</text>'
                           % (b.cls, b.x, b.y, "text-anchor:%s" % b.an,
                              _html.escape(b.s, quote=False)))),
                ("≥1", "0", "0", "0")))
    # ② 1つ目の字面を**枠の外へ出す** ⇒ 枠外が鳴る
    out.append(("② ⭐ 1つ目の字面を**枠の外へ出す** — ⚠ **枠外が鳴る**",
                _mut(_repl(a.span, '<text class="%s" x="%.1f" y="%.1f" style="%s">%s</text>'
                           % (a.cls, W + 40.0, a.y, "text-anchor:start",
                              _html.escape(a.s, quote=False)))),
                ("0", "≥1", "0", "0")))
    # ③ ⭐⭐ 1つ目の銘の上へ**不透明な塗りを後から被せる** ⇒ 潜りが鳴る
    ab = a.box_of(a.s, a.y)
    out.append(("③ ⭐⭐ 1つ目の銘の上へ**不透明な塗りを後から被せる**"
                "(=2026-09-08 まで 10 件あった消え方)— ⚠ **潜りが鳴る**",
                _mut(body + '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                            'fill="var(--paper)" opacity="1.00"/>'
                            % (ab[0] - 1, ab[1] - 1, (ab[2] - ab[0]) + 2, (ab[3] - ab[1]) + 2)),
                ("0", "0", "≥1", "0")))
    # ④ ⭐⭐ 1つ目の銘を**下限より小さく**する ⇒ 小字が鳴る
    out.append(("④ ⭐⭐ 1つ目の銘を**字送りの下限より小さく**する — ⚠ **小字が鳴る**",
                _mut(_repl(a.span, '<text class="%s" x="%.1f" y="%.1f" style="font-size:%.1fpx">'
                           '%s</text>' % (a.cls, a.x, a.y, MIN_EFF * W / VIEW_W * 0.5,
                                          _html.escape("室名の見本", quote=False)))),
                ("0", "0", "0", "≥1")))
    # ⑤ ⭐⭐ **推定幅を 0.95 倍して組み直す** ⇒ 枠外が鳴る
    #    ⛔⛔ この巡に実際に残った régime(幅を 5% 見誤る)を鳴らす束が一つも無かった。
    if raw is not None:
        _WS[0] = 0.95
        try:
            d95, _ = relayout(raw, tab)
        finally:
            _WS[0] = 1.0
        out.append(("⑤ ⭐⭐ **推定幅を 0.95 倍して組み直す**"
                    "(=一般約物を 0.5em と見誤っていた régime)— ⚠ **枠外が鳴る**",
                    counts(check(d95, tab)), ("—", "≥1", "0", "0")))
    # ⑥ 触らない ⇒ 鳴らない
    out.append(("⑥ いまの図(基準)— ⛔ **鳴らない**", counts(check(doc, tab)),
                ("0", "0", "0", "0")))
    return out


def probe_ok(rows):
    """`probes` の各行が期待どおりか。⛔ 期待は「≥1」「0」「—」(不問)の語で持つ。

    ⚠ **「—」は逃げ道ではない** — その束が**その筋では鳴ると言い切れない**ときだけ使う
    (例: 幅を 0.95 倍して組み直すと、枠外だけでなく重なりも副次的に出る)。
    """
    out = []
    for title, got, want in rows:
        ok = all(True if w == "—" else (g >= 1 if w == "≥1" else g == 0)
                 for g, w in zip(got, want))
        out.append((title, got, want, ok))
    return out


if __name__ == "__main__":
    import sys
    doc = open(sys.argv[1], encoding="utf-8").read()
    r0 = check(doc)
    print("直す前: 重なり %d 組 / 枠外 %d 件 / 潜り %d 件 / 小字 %d 件" % counts(r0))
    doc2, rep = relayout(doc)
    r1 = check(doc2)
    print("直した後: 重なり %d 組 / 枠外 %d 件 / 潜り %d 件 / 小字 %d 件 ・ %s"
          % (counts(r1) + (rep,)))
    for x in sorted(r1["overlap"], key=lambda z: -z[1])[:15]:
        print("  OV f%02d %8.1f  %s || %s" % (x[0], x[1], x[2][:30], x[3][:30]))
    for x in sorted(r1["outframe"], key=lambda z: -z[1])[:15]:
        print("  OUT f%02d %8.1f  %s" % (x[0], x[1], x[2][:40]))
    for x in r1["covered"][:15]:
        print("  COV f%02d %d/%d  %s" % (x[0], x[2], x[3], x[1][:40]))
    for x in sorted(r1["tiny"])[:20]:
        print("  TNY f%02d %.2fpx  %s" % (x[0], x[1], x[2][:40]))
    doc3, _ = relayout(doc2)
    print("冪等: %s" % ("⭕" if doc3 == doc2 else "⛔ 2度目で変わった"))
    # ⚠ ここでは `raw` に**直した後の図**しか渡せない(この入口は完成した html を読むため)
    #   ⇒ **束⑤は必ず落ちる**。⭕ 生成器の中では直す前の文書が渡るので通る。
    for t, g, w, ok in probe_ok(probes(doc2, doc)):
        print("  %s %s 実測%s 期待%s%s"
              % ("⭕" if ok else "⛔", t[:44], g, w,
                 "  ⚠ この入口では束⑤だけは落ちて正しい" if (not ok and t.startswith("⑤")) else ""))
