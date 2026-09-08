#!/usr/bin/env python3
"""図の**字面**を機械で測り、重なりと枠外を潰す。

⭐⭐ **なぜ機械で測るのか。** 2026-09-08 の検図で「文字どうしの重なり 49組/13面・
枠外へ出る文字 67件/24面」が出た。⛔ **目で一つずつ潰すと次の巡でまた増える** —
図版は毎巡ふえ、文字は設計値から組み立てられるので**値が変わるたびに幅が変わる**。
⇒ ⭕ **測る道具を図の中に置き、件数を刷る。**

【この道具の物差し(近似であることを隠さない)】
指図は SVG を**ブラウザに渡す前に**組む。⛔ 生成器はフォントを持たないので、
**字送りは近似**である。和字=1.0em / 記号(⛔⭐⚠→)=1.0em / 欧数字=0.56〜0.68em /
約物=0.32em。⚠ **実測ではない** — だから閾値は 0.5px² と甘めに取り、
「**この物差しで 0 件**」と名乗る(⛔ 「重なっていない」とは名乗らない)。
⭕ 検図方はレンダして目で裏を取る。⭐ **道具の非対称**(機械は全面を網羅できるが精度が粗い /
目は精度が高いが 43 面を毎巡は見られない)を、そのまま役の分担にしてある。

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
    """1字の字送り[em]。⚠ 近似(この道具の粗さの出どころ)。"""
    o = ord(ch)
    if ch == " ":
        return 0.28
    if o < 0x300:                                  # 欧文・数字・約物
        if ch in ".,:;'`|!ilj()[]{}/\\-":
            return 0.32
        if ch.isdigit():
            return 0.556
        if ch.isupper():
            return 0.68
        return 0.56
    if 0x2000 <= o <= 0x206F:                      # 一般約物(— … ‥)
        return 0.5
    if 0x2190 <= o <= 0x2BFF:                      # 記号(→ ⛔ ⭐ ⭕ ⚠ ①②)
        return 1.0
    return 1.0                                     # 和字・全角


def text_w(s, fs, ls=0.0):
    return fs * (sum(_adv(c) for c in s) + ls * max(0, len(s) - 1))


ASC, DESC = 0.78, 0.18     # 基線からの上下[em]


class Tx(object):
    """1個の `<text>`。"""

    __slots__ = ("i", "span", "att", "s", "cls", "fs", "an", "ls", "x", "y",
                 "lines", "drop", "moved")

    def __init__(self, i, span, att, s, cls, fs, an, ls, x, y):
        self.i, self.span, self.att, self.s = i, span, att, s
        self.cls, self.fs, self.an, self.ls = cls, fs, an, ls
        self.x, self.y = x, y
        self.lines = [s]
        self.drop = False
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

    def ys(self):
        """行ごとの基線 y。下端に近い文字は**上へ**積む(枠から落とさない)。"""
        n = len(self.lines)
        if n == 1:
            return [self.y]
        return [self.y - (n - 1 - k) * self.lh for k in range(n)]

    def boxes(self):
        return [self.box_of(s, y) for s, y in zip(self.lines, self.ys())]


def parse(body, cls_tab):
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
        out.append(Tx(i, m.span(), a, _html.unescape(m.group(2)), cls, fs, an, ls,
                      float(a.get("x", 0.0)), float(a.get("y", 0.0))))
    return out


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
    placed, moved = [], 0
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
        t.moved = abs(t.x - base_x) + abs(t.y - base_y)
        moved += 1
        placed.extend(t.boxes())
    return moved


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


def relayout(doc, cls_tab=None):
    """重なりと枠外を潰した文書を返す。⭕ 冪等(2度掛けても同じ)。"""
    tab = cls_tab or css_classes()
    rep = {"dropped": 0, "wrapped": 0, "moved": 0, "grown": 0, "figs": 0,
           "droppedList": [], "movedMax": 0.0, "movedFar": 0}
    out, at = [], 0
    for m in _RE_SVG.finditer(doc):
        W, H = float(m.group(2)), float(m.group(3))
        body = m.group(4)
        ts = parse(body, tab)
        rep["figs"] += 1
        for t in ts:
            b = t.box_of(t.s, t.y)
            if b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H:
                t.drop = True                       # ⭕ 枠の外に**丸ごと**出た字は見えていない
                rep["dropped"] += 1
                rep["droppedList"].append((rep["figs"], t.s))
                continue
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
            H = float(math.ceil(H + grow))   # ⚠ viewBox は整数で出す(丸めで冪等が崩れる)
            rep["grown"] += 1
        for t in ts:
            if not t.drop:
                clamp(t, W, H)
        rep["moved"] += deoverlap(ts, W, H)
        rep["movedMax"] = max([rep["movedMax"]] + [t.moved for t in ts if not t.drop])
        rep["movedFar"] += sum(1 for t in ts if not t.drop and t.moved > 40.0)
        nb, prev = [], 0
        for t in ts:
            nb.append(body[prev:t.span[0]])
            nb.append("" if t.drop else _emit(t))
            prev = t.span[1]
        nb.append(body[prev:])
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
    """⛔ 直した後の文書を測る。返すのは**件数と実例**。"""
    tab = cls_tab or css_classes()
    ov, of, figs, nt = [], [], 0, 0
    for m in _RE_SVG.finditer(doc):
        figs += 1
        W, H = float(m.group(2)), float(m.group(3))
        ts = parse(m.group(4), tab)
        bs = []
        for t in ts:
            for b in t.boxes():
                bs.append((b, t.s))
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
    return {"figs": figs, "texts": nt, "overlap": ov, "outframe": of,
            "ovFigs": len(set(x[0] for x in ov)),
            "ofFigs": len(set(x[0] for x in of))}


# ---------------------------------------------------------------- 破壊試験
def probes(doc, cls_tab=None):
    """⭐⭐ **この検査が生きていることを毎回見せる**(規則19)。

    ⛔⛔ **「0 件」だけを刷ると、検査が死んでいても 0 と読める。**⇒ ⭕ 直した文書へ
    **わざと欠陥を差し込み**、鳴ることを確かめる。⛔ 乱数を使わない(決定的)。
    返すのは `[(題, 実測(重なり, 枠外), 期待)]`。
    """
    tab = cls_tab or css_classes()
    out = []

    def _first(dc):
        m = _RE_SVG.search(dc)
        return m

    m = _first(doc)
    if m is None:
        return [("⛔ 図版が1面も無い — **この検査は回っていない**", (-1, -1), (0, 0))]
    W, H, body = float(m.group(2)), float(m.group(3)), m.group(4)
    ts = parse(body, tab)
    if len(ts) < 2:
        return [("⛔ 1面目の字面が2つ未満 — **試験を差し込めない**", (-1, -1), (0, 0))]
    a, b = ts[0], ts[1]

    def _mut(rep_from, rep_to):
        nb = body[:a.span[0]] + rep_to + body[a.span[1]:]
        dc = doc[:m.start()] + m.group(1) + nb + m.group(5) + doc[m.end():]
        r = check(dc, tab)
        return (len(r["overlap"]), len(r["outframe"]))

    # ① 1つ目の字面を2つ目の**真上へ重ねる** ⇒ 重なりが鳴る
    ov = _mut(None, '<text class="%s" x="%.1f" y="%.1f" style="%s">%s</text>'
              % (b.cls, b.x, b.y, "text-anchor:%s" % b.an, _html.escape(b.s, quote=False)))
    out.append(("① ⭐ 1つ目の字面を2つ目の**真上へ重ねる** — ⚠ **重なりが鳴る**",
                ov, ("≥1", "0")))
    # ② 1つ目の字面を**枠の外へ出す** ⇒ 枠外が鳴る
    of = _mut(None, '<text class="%s" x="%.1f" y="%.1f" style="%s">%s</text>'
              % (a.cls, W + 40.0, a.y, "text-anchor:start", _html.escape(a.s, quote=False)))
    out.append(("② ⭐ 1つ目の字面を**枠の外へ出す** — ⚠ **枠外が鳴る**", of, ("0", "≥1")))
    # ③ 触らない ⇒ 鳴らない
    r0 = check(doc, tab)
    out.append(("③ いまの図(基準)— ⛔ **鳴らない**",
                (len(r0["overlap"]), len(r0["outframe"])), ("0", "0")))
    return out


def probe_ok(rows):
    """`probes` の各行が期待どおりか。⛔ 期待は「≥1」か「0」の語で持つ。"""
    out = []
    for title, got, want in rows:
        ok = all((g >= 1 if w == "≥1" else g == 0) for g, w in zip(got, want))
        out.append((title, got, want, ok))
    return out


if __name__ == "__main__":
    import sys
    doc = open(sys.argv[1], encoding="utf-8").read()
    r0 = check(doc)
    print("直す前: 重なり %d 組 / %d 面 ・ 枠外 %d 件 / %d 面"
          % (len(r0["overlap"]), r0["ovFigs"], len(r0["outframe"]), r0["ofFigs"]))
    doc2, rep = relayout(doc)
    r1 = check(doc2)
    print("直した後: 重なり %d 組 / %d 面 ・ 枠外 %d 件 / %d 面 ・ %s"
          % (len(r1["overlap"]), r1["ovFigs"], len(r1["outframe"]), r1["ofFigs"], rep))
    for x in sorted(r1["overlap"], key=lambda z: -z[1])[:15]:
        print("  OV f%02d %8.1f  %s || %s" % (x[0], x[1], x[2][:30], x[3][:30]))
    for x in sorted(r1["outframe"], key=lambda z: -z[1])[:15]:
        print("  OUT f%02d %8.1f  %s" % (x[0], x[1], x[2][:40]))
    doc3, _ = relayout(doc2)
    print("冪等: %s" % ("⭕" if doc3 == doc2 else "⛔ 2度目で変わった"))
    for t, g, w, ok in probe_ok(probes(doc2)):
        print("  %s %s 実測%s 期待%s" % ("⭕" if ok else "⛔", t[:44], g, w))
