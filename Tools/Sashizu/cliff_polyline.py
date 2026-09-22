#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""**折れ線の崖**を評価する小さな道具。復元の生成器と指図の生成器の**両方**が読む。

⛔ 同じ算法を二重に書かない(CLAUDE.md 規則4)。丹羽の崖は南北の直線ではなく
**WNW–ESE の斜めの崖 → 東西の崖**と向きを変える折れ線なので、
「法尻 X」「法肩 X」のような一つの数では表せない。

**表し方** — 法肩(crest)と法尻(toe)を**それぞれ世界座標の折れ線**で持つ。
どちらも「北西の端 → 東の端」の順に並べ、**進行方向の左が高い側(北東)**になるようにする。

ある点 p について
    s_toe   = 法尻の折れ線からの符号つき距離(左=高い側が正)
    s_crest = 法肩の折れ線からの符号つき距離(同)
とすると

    s_toe   ≤ 0            … 谷底
    s_crest ≥ 0            … 台地
    それ以外               … 崖の面。法尻からの割合 f = s_toe / (s_toe − s_crest)
                             (f = 0 が法尻・f = 1 が法肩)

⭐ **f は距離の比なので、崖の幅が場所ごとに変わっても自然に効く。**
⛔ 折れ線は**区画より十分外まで**伸ばしておくこと(端で符号が壊れないように)。
"""
import math


def _seg_dist(a, b, p):
    """線分 a→b と点 p の距離と、符号(左が正)を返す。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2
    t = max(0.0, min(1.0, t))
    qx, qz = a[0] + dx * t, a[1] + dz * t
    d = math.hypot(p[0] - qx, p[1] - qz)
    cr = dx * (p[1] - a[1]) - dz * (p[0] - a[0])
    return d, (1.0 if cr >= 0 else -1.0)


def _seg_foot(a, b, p):
    """線分 a→b の上で p に最も近い点。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2
    t = max(0.0, min(1.0, t))
    return (a[0] + dx * t, a[1] + dz * t)


def signed_dist(line, p):
    """折れ線からの符号つき距離。**最寄りの線分**の符号を採る(左=正)。"""
    best = None
    for i in range(len(line) - 1):
        d, s = _seg_dist(line[i], line[i + 1], p)
        if best is None or d < best[0]:
            best = (d, s)
    return best[0] * best[1]


def nearest(line, p):
    """折れ線の上で p に最も近い点。"""
    best = None
    for i in range(len(line) - 1):
        q = _seg_foot(line[i], line[i + 1], p)
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        if best is None or d < best[0]:
            best = (d, q)
    return best[1]


class Cliff(object):
    """法尻・法肩の折れ線から、点ごとの区分と割合を出す。"""

    def __init__(self, spec):
        self.toe = [tuple(q) for q in spec["toe"]]
        self.crest = [tuple(q) for q in spec["crest"]]

    def frac(self, x, z):
        """(区分, f) を返す。区分は 'valley' / 'cliff' / 'plateau'、f は 0(法尻)〜1(法肩)。"""
        p = (x, z)
        st = signed_dist(self.toe, p)
        sc = signed_dist(self.crest, p)
        if st <= 0.0:
            return "valley", 0.0
        if sc >= 0.0:
            return "plateau", 1.0
        return "cliff", st / (st - sc)

    def width(self, x, z):
        """その点での崖の水平幅[m](法尻の折れ線 ↔ 法肩の折れ線)。"""
        p = (x, z)
        return abs(signed_dist(self.toe, p)) + abs(signed_dist(self.crest, p))

    def height(self, x, z, valley, plateau):
        """復元面の高さ。`valley` は (x,z)→谷底の高さ を返す関数、`plateau` は台地の高さ[m]。"""
        k, f = self.frac(x, z)
        v = valley(x, z)
        if k == "valley":
            return v
        if k == "plateau":
            return plateau
        return v + (plateau - v) * f

    def profiles(self, inside, ds=4.0):
        """法肩に沿って `ds` m ごとに標本を採り、**(法肩の点, 法尻の点, 水平幅)** を返す。
        `inside(x, z)` が真になる標本だけを返す(区画の中で測るため)。
        ⭐ **崖の比高と勾配はこれを足場に毎回測る** — 手で持たない(規則4)。"""
        out = []
        L = self.crest
        for i in range(len(L) - 1):
            a, b = L[i], L[i + 1]
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            m = max(1, int(round(seg / ds)))
            for k in range(m + (1 if i == len(L) - 2 else 0)):
                t = k / float(m)
                c = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                q = nearest(self.toe, c)
                if not (inside(c[0], c[1]) and inside(q[0], q[1])):
                    continue
                out.append((c, q, math.hypot(c[0] - q[0], c[1] - q[1])))
        return out
