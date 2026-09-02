#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""岡部邸の地盤レイヤの生成器 — **種地は正本 `base_dem.json`、復元は岡部区画でクリップ**。

CLAUDE.md 規則12 / `docs/Sashizu/README.md` 決めごと5 /
スキル `unity-buke-yashiki` `references/sashizu.md` §3a「地形は正本から採る」。

⚠ **2026-08-24 まで、この3枚には生成器が無かった。** 手で起こしたまま据え置かれ、
種地は Unity の live terrain から採った標本(= 松平の造成を含む)で、しかも復元が
区画の外へ 33 セル滲んで**樹下邸の地盤を最大 +2.78m 持ち上げていた**。
§3a が要求する「生成器は冪等にする。再実行で1セルも動かないことを毎回確かめる」を
満たしていなかったので、この道具を起こした。

書くもの(いずれも派生物 — 手で編集しない):

| ファイル | 中身 |
|---|---|
| `okabe_edo_world.json` | **江戸期の復元地盤**(世界2m格子)。区画の中=正本+復元差分 / 外=**正本そのもの** |
| `okabe_edo_dem.json`   | 上を回転間グリッド(shukaku)へ双一次で再標本。区画の外は null |
| `okabe_terrain.json`   | **現況**(近代造成を含む)を回転間グリッドへ。種地は正本。区画の外は null |

復元の**手順**は `okabe_edo_recon.json` が仕様として持つ(パラメータごとに典拠と確度つき)。
この生成器はその手順を**正本に対して毎回実行する** — ⚠ 2026-08-25 に「前の復元値を差分として
写す」やり方をやめた。写していると種地(正本)が動いても復元が追随せず、
「地形は正本から採る」が名ばかりになる。

使い方:
    python3 Tools/Sashizu/build_okabe_edo_dem.py            # 3枚を書く(冪等)
    python3 Tools/Sashizu/build_okabe_edo_dem.py --check    # 書かずに差分だけ出す
"""

import json
import math
import os
import sys

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "Sashizu")
DOC = os.path.normpath(DOC)

BASE = os.path.join(DOC, "base_dem.json")
SASHIZU = os.path.join(DOC, "okabe_sashizu.json")
RECON = os.path.join(DOC, "okabe_edo_recon.json")
WORLD = os.path.join(DOC, "okabe_edo_world.json")
ROT_EDO = os.path.join(DOC, "okabe_edo_dem.json")
ROT_CUR = os.path.join(DOC, "okabe_terrain.json")

# 世界2m格子の窓(`okabe_dem.json` と同じ範囲に揃える — 現況図が同じ枠で読めるように)
WIN = dict(x0=-720, z0=930, step=2, nx=186, nz=100)


def load(p):
    return json.load(open(p, encoding="utf-8"))


def in_poly(poly, x, z):
    n = len(poly)
    c = False
    for i in range(n):
        (ax, az), (bx, bz) = poly[i], poly[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (bx - ax) * (z - az) / (bz - az):
            c = not c
    return c


def bilinear(S, x, z):
    """h[iz][ix] を双一次補間する。範囲外・欠測は None。"""
    fx = (x - S["x0"]) / float(S["step"])
    fz = (z - S["z0"]) / float(S["step"])
    i0, j0 = int(math.floor(fx)), int(math.floor(fz))
    if not (0 <= i0 < S["nx"] - 1 and 0 <= j0 < S["nz"] - 1):
        if 0 <= round(fx) < S["nx"] and 0 <= round(fz) < S["nz"]:
            return S["h"][int(round(fz))][int(round(fx))]
        return None
    tx, tz = fx - i0, fz - j0
    q = [S["h"][j0][i0], S["h"][j0][i0 + 1], S["h"][j0 + 1][i0], S["h"][j0 + 1][i0 + 1]]
    if any(v is None for v in q):
        return S["h"][j0][i0]
    return (q[0] * (1 - tx) + q[1] * tx) * (1 - tz) + (q[2] * (1 - tx) + q[3] * tx) * tz


class RGrid(object):
    """回転間グリッド (u,v)[間] → 世界座標。`okabe_sashizu.json` の grid をそのまま使う。"""

    def __init__(self, d, name="shukaku"):
        g = d["grid"][name]
        self.ken = d["const"]["ken"]
        self.x0, self.z0 = g["x0"], g["z0"]
        self.ux, self.uz, self.vx, self.vz = g["ux"], g["uz"], g["vx"], g["vz"]

    def W(self, u, v):
        um, vm = u * self.ken, v * self.ken
        return (self.x0 + self.ux * um + self.vx * vm,
                self.z0 + self.uz * um + self.vz * vm)

    def L(self, x, z):
        """世界座標 → (u,v)[間]。"""
        dx, dz = x - self.x0, z - self.z0
        return ((dx * self.ux + dz * self.uz) / self.ken,
                (dx * self.vx + dz * self.vz) / self.ken)


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def flats(grid, poly, tol, minCells):
    """**近代造成の平坦を形で拾う。** 高さを決め打ちせず、隣と tol 以内で連なる面の連結成分を取る。
    返すのは {(ix,iz)} の集合と、成分ごとの (セル数, 代表の高さ)。"""
    nx, nz, h = grid["nx"], grid["nz"], grid["h"]
    seen = [[False] * nx for _ in range(nz)]
    cells = set()
    comps = []
    for iz in range(nz):
        for ix in range(nx):
            y = h[iz][ix]
            if y is None or seen[iz][ix]:
                continue
            x = grid["x0"] + grid["step"] * ix
            z = grid["z0"] + grid["step"] * iz
            if not in_poly(poly, x, z):
                seen[iz][ix] = True
                continue
            stack = [(ix, iz)]
            seen[iz][ix] = True
            got = []
            while stack:
                a, b = stack.pop()
                got.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    p, q = a + da, b + db
                    if not (0 <= q < nz and 0 <= p < nx) or seen[q][p]:
                        continue
                    zz = h[q][p]
                    if zz is None or abs(zz - y) > tol:
                        continue
                    xx = grid["x0"] + grid["step"] * p
                    zw = grid["z0"] + grid["step"] * q
                    if not in_poly(poly, xx, zw):
                        seen[q][p] = True
                        continue
                    seen[q][p] = True
                    stack.append((p, q))
            if len(got) >= minCells:
                comps.append((len(got), round(y, 2)))
                cells |= set(got)
    comps.sort(reverse=True)
    return cells, comps


def _poly_dist(P, x, z, skip=()):
    """多角形の辺までの最短距離。`skip` に挙げた辺は**数えない**。
    ⭕ クリップの規約の目的は『隣家と境の高さが食い違わない』ことなので、
      **隣家の無い辺は外す**(岡部の辺5=溜池の岸。2026-09-02)。"""
    best = None
    n = len(P)
    for i in range(n):
        if i in skip:
            continue
        a, b = P[i], P[(i + 1) % n]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        dd = math.hypot(x - (a[0] + dx * t), z - (a[1] + dz * t))
        best = dd if best is None else min(best, dd)
    return best


def _tin(t, u, v):
    """(u,v) が段の中か(指図の tin と同じ。多角形なら crossing number)。"""
    p = t.get("poly")
    if not p:
        return t["u0"] - 1e-9 <= u <= t["u1"] + 1e-9 and t["v0"] - 1e-9 <= v <= t["v1"] + 1e-9
    n = len(p); c = False
    for i in range(n):
        (au, av), (bu, bv) = p[i], p[(i + 1) % n]
        if (av > v) != (bv > v) and u < au + (bu - au) * (v - av) / (bv - av):
            c = not c
    return c


def reconstruct(seed, poly, gr, spec):
    """**近代造成を戻して江戸期の地盤を起こす。** 仕様 `okabe_edo_recon.json` の手順を
    正本(seed)に対して実行する。返すのは (h, ログ)。⛔ 岡部区画の中だけを触る。"""
    log = []
    nx, nz, st = seed["nx"], seed["nz"], seed["step"]
    h = [[seed["h"][iz][ix] for ix in range(nx)] for iz in range(nz)]
    inside = [[False] * nx for _ in range(nz)]
    uv = {}
    for iz in range(nz):
        for ix in range(nx):
            x = seed["x0"] + st * ix
            z = seed["z0"] + st * iz
            if in_poly(poly, x, z):
                inside[iz][ix] = True
                uv[(ix, iz)] = gr.L(x, z)

    # ① 近代造成の平坦を形で検出
    fd = spec["flatDetect"]
    flatset, comps = flats(seed, poly, fd["tol"], fd["minCells"])
    log.append("① 広い平坦 %d 面 %d セル(上位: %s)"
               % (len(comps), len(flatset),
                  " / ".join("%.2f×%d" % (y, n) for n, y in comps[:4])))

    # ④ 台地の自然面を**正本から算出**(盛土を免れた実測セルの中央値)
    pl = spec["plateau"]
    cf = spec["cutFlat"]
    sel = []
    for (ix, iz), (u, v) in uv.items():
        y = seed["h"][iz][ix]
        if y is None or v < pl["vMin"]:
            continue
        if not (pl["cellMin"] <= y <= pl["cellMax"]):
            continue
        if abs(y - cf["y"]) <= cf["tol"]:
            continue
        sel.append(y)
    py = round(median(sel), 2)
    log.append("④ 台地の自然面 = 盛土を免れた実測 %d セルの中央値 **%.2f**(振れ %.2f〜%.2f)"
               % (len(sel), py, min(sel), max(sel)))
    mk0 = spec["mask"]

    mk, lb, cl, sf = spec["mask"], spec["lowband"], spec["cliff"], spec["schoolFill"]
    if abs(lb["vToe"] - cl["v0"]) > 1e-9:      # 帯の上端 = 崖の法尻。二重管理を機械で止める
        raise SystemExit("⛔ lowband.vToe(%.2f) ≠ cliff.v0(%.2f) — 帯と崖の間に段ができる"
                         % (lb["vToe"], cl["v0"]))
    changed = set()

    # ②③ 低地の帯と崖 — マスクの中の、**近代造成が現に及んでいる所だけ**を
    #    1883年図の三帯から起こす。造成が届いていない斜面は現況のまま残す(規則8)。
    cap = mk["edgeCap"] / float(st)
    fea = mk["feather"] / float(st)
    rad = int(math.ceil(cap + fea))
    # 平坦からの距離を測る(近代造成が及ぶ度合い)。cap 以内=まるごとモデル、
    # そこから feather かけて現況へ摺り付け、外は現況のまま。
    wmap = {}
    for ix, iz in flatset:
        for dx in range(-rad, rad + 1):
            for dz in range(-rad, rad + 1):
                dd = math.hypot(dx, dz)
                if dd > cap + fea:
                    continue
                w = 1.0 if dd <= cap else 1.0 - (dd - cap) / fea
                q = (ix + dx, iz + dz)
                if w > wmap.get(q, 0.0):
                    wmap[q] = w
    # ○ 二点は **sources.md の実座標**からフレームへ落とす。
    # ⛔ 散文の「区画の外へ約20m」から再導出しない(2026-08-25 考証: 基線が 187.0m → 213.3m に伸び、
    #    勾配が 1.069% → 0.938% と12%寝ていた)。
    uN = gr.L(*lb["spotN"]["xz"])[0]
    uS = gr.L(*lb["spotS"]["xz"])[0]
    n2 = n3 = 0
    for (ix, iz), (u, v) in uv.items():
        w = wmap.get((ix, iz), 0.0)
        if u > mk["uMax"] or v > mk["vMax"] or w <= 0.0 or h[iz][ix] is None:
            continue
        street = lb["spotS"]["y"] + (lb["spotN"]["y"] - lb["spotS"]["y"]) * \
            (u - uS) / (uN - uS)                       # 通り沿いの内挿(1883の ○ 二点)
        toe = street + lb["toeRise"]
        if v <= lb["vToe"]:
            y = street + (toe - street) * max(v, 0.0) / lb["vToe"]
            n2 += 1
        else:
            t = (v - cl["v0"]) / (cl["v1"] - cl["v0"])
            y = toe + (py - toe) * min(max(t, 0.0), 1.0)
            n3 += 1
        y = y * w + h[iz][ix] * (1.0 - w)          # 縁は現況へ摺り付ける
        if abs(h[iz][ix] - y) > 0.005:
            changed.add((ix, iz))
        h[iz][ix] = y
    log.append("②③ 低地の帯 %d セル / 崖 %d セル をモデルへ置き換え"
               "(平坦とその縁 %.0fm 以内はまるごと、そこから %.0fm で現況へ摺り付け)"
               % (n2, n3, mk["edgeCap"], mk["feather"]))

    # ②' **西の崖と低い帯** — 1883年図の標高点から起こす(2026-09-02)。
    #    ⛔ ここは 2026-09-02 まで復元が当たっておらず**現代の地面のまま**だった。
    #    溜池が明治7〜8年に陸化し外堀通りが切られた、区画で最も改変の大きい一帯である。
    wb, wc = spec.get("westBand"), spec.get("westCliff")
    if wb and wc:
        def _plane(sp):
            """錨の (u,v,y) に平面 y=a+b·u+c·v を**最小二乗**で当てる。"""
            S = [[0.0] * 4 for _ in range(3)]
            for q in sp:
                r = [1.0, q["uv"][0], q["uv"][1]]
                for i in range(3):
                    for j in range(3):
                        S[i][j] += r[i] * r[j]
                    S[i][3] += r[i] * q["y"]
            for i in range(3):
                pv = max(range(i, 3), key=lambda k: abs(S[k][i]))
                S[i], S[pv] = S[pv], S[i]
                for k in range(3):
                    if k == i:
                        continue
                    f = S[k][i] / S[i][i]
                    for cc in range(i, 4):
                        S[k][cc] -= f * S[i][cc]
            return [S[i][3] / S[i][i] for i in range(3)]
        pa, pb, pc = _plane(wb["spots"])
        res = [(q["uv"][0], q["uv"][1], q["y"], pa + pb * q["uv"][0] + pc * q["uv"][1] - q["y"])
               for q in wb["spots"]]

        def band(u, v):
            return pa + pb * u + pc * v

        def hsamp(u, v):
            """(u,v) の現在の面を双一次で拾う。"""
            x, z = gr.W(u, v)
            fx = (x - seed["x0"]) / float(st); fz = (z - seed["z0"]) / float(st)
            i0, j0 = int(math.floor(fx)), int(math.floor(fz))
            tx, tz = fx - i0, fz - j0
            acc = wt = 0.0
            for dj, wv in ((0, 1 - tz), (1, tz)):
                for di, wu in ((0, 1 - tx), (1, tx)):
                    i, j = i0 + di, j0 + dj
                    if 0 <= j < nz and 0 <= i < nx and h[j][i] is not None:
                        acc += h[j][i] * wu * wv; wt += wu * wv
            return acc / wt if wt > 1e-9 else None
        # **法肩を u ごとに拾う** — 復元後の面が「台地の自然面 −drop」を下回る最初の v。
        # ⛔ 一定の v0 を置くと、主面が西へ張り出す南西側で台地を削る。
        us = sorted(set(round(q[0] * 2) / 2.0 for q in uv.values()))
        hig = {}
        for u in us:
            vq = wc["vScan0"]
            while vq <= wc["v1"]:
                y0 = hsamp(u, vq)
                if y0 is not None and y0 < py - wc["drop"]:
                    hig[u] = (vq, y0)
                    break
                vq += 0.25
        n2w = n3w = 0
        for (ix, iz), (u, v) in uv.items():
            if v < wc["vScan0"] or h[iz][ix] is None:
                continue
            key = min(hig, key=lambda q: abs(q - u)) if hig else None
            if key is None or abs(key - u) > 1.0:
                continue
            vh, yh = hig[key]
            if v < vh:
                continue                                  # まだ台地の上
            if v <= wc["v1"]:
                t = (v - vh) / max(wc["v1"] - vh, 1e-9)
                y = yh + (band(u, wc["v1"]) - yh) * t      # 崖 — 法肩から帯の上端へ一定勾配
                n3w += 1
            else:
                y = band(u, v)                             # 低い帯 — 1883の標高点の平面
                n2w += 1
            if abs(h[iz][ix] - y) > 0.005:
                changed.add((ix, iz))
            h[iz][ix] = y
        log.append("②' 西の崖 %d セル / 西の低い帯 %d セル を 1883年図から起こした。"
                   "帯の平面 y = %.4f %+.5f·u %+.5f·v(u %+.3f%%/m・v %+.3f%%/m)／"
                   "錨の残差 %s"
                   % (n3w, n2w, pa, pb, pc, pb / 1.818 * 100, pc / 1.818 * 100,
                      " / ".join("○%.1f %+.2f" % (q[2], q[3]) for q in res)))
        if hig:
            hv = [q[0] for q in hig.values()]
            log.append("②'  法肩は u ごとに算出(台地の自然面 %.2f −%.2f を下回る最初の v)"
                       " — v %.1f〜%.1f。崖の落差は %.2f〜%.2fm"
                       % (py, wc["drop"], min(hv), max(hv),
                          min(q[1] for q in hig.values()) - band(0, wc["v1"]),
                          max(q[1] for q in hig.values()) - band(0, wc["v1"])))

    # ④ 校舎の盛土を台地の自然面へ
    n4 = 0
    for (ix, iz), (u, v) in uv.items():
        if v <= mk["vMax"]:
            continue
        y = h[iz][ix]
        if y is None or y <= sf["above"]:
            continue
        h[iz][ix] = py
        changed.add((ix, iz))
        n4 += 1
    log.append("④ 1883年図の帯の上端 %.1f を超える %d セル(=明治16年以後の盛土)を %.2f へ落とした"
               % (sf["above"], n4, py))

    # ⑤ 台地の中の近代の切土平場を、周囲の実測台地セルからの逆距離加重補間で埋める
    holes = [(ix, iz) for (ix, iz), (u, v) in uv.items()
             if v > mk["vMax"] and (ix, iz) in flatset
             and seed["h"][iz][ix] is not None and abs(seed["h"][iz][ix] - cf["y"]) <= cf["tol"]]
    donors = [(ix, iz) for (ix, iz), (u, v) in uv.items()
              if v > mk["vMax"] and (ix, iz) not in holes
              and h[iz][ix] is not None and pl["cellMin"] <= h[iz][ix] <= pl["cellMax"]]
    hset = set(holes)
    rr = cf["radius"] / float(st)
    for ix, iz in holes:
        num = den = 0.0
        for jx, jz in donors:
            dd = math.hypot(jx - ix, jz - iz)
            if dd > rr or dd < 1e-9:
                continue
            w = 1.0 / dd ** cf["power"]
            num += w * h[jz][jx]
            den += w
        if den:
            h[iz][ix] = num / den
            changed.add((ix, iz))
    log.append("⑤ 近代の切土平場 %d セルを周囲の実測 %d セルから逆距離加重補間で埋めた"
               % (len(holes), len(donors)))

    # ⑦ 変えたセルとその周り1セルを平滑化(⑥ 街路・斜面は触っていない)
    soft = set()
    for ix, iz in changed:
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if inside[min(max(iz + dz, 0), nz - 1)][min(max(ix + dx, 0), nx - 1)]:
                    soft.add((ix + dx, iz + dz))
    soft = set(q for q in soft if 0 <= q[0] < nx and 0 <= q[1] < nz and inside[q[1]][q[0]])
    # ⛔ **クリップを外した辺(`edgeClip.skipEdges`)の外側は、平滑化の平均にも混ぜない。**
    #   ⚠ 2026-09-03 の庭方4巡目で見つかった:2026-09-02 の K078 は「辺5でクリップを外す」と
    #     書きながら、外したのは⑧のクリップだけで**⑦の平滑化は外していなかった**。
    #     その結果、区画の外の近代の地面(約 8.9m)が縁の3〜4セルへ滲み、
    #     1883年図では 11.25→11.08 のほぼ水平な岸が **最大 1.33m 沈んだ段**に見えていた。
    #     ⛔ 見かけの段に階段を刻みかけた(庭方が『地覆丸太の段』を提案する寸前だった)。
    #   ⭕ **規約の目的は「隣家と境の高さが食い違わない」ことなので、隣家の無い辺では
    #     ⑦⑧ とも外す。**⛔ 隣家のある辺(3・4・6・7)では従来どおり混ぜる。
    skip_e9 = set(spec.get("edgeClip", {}).get("skipEdges", []) or [])
    banned = set()
    if skip_e9:
        def _near_edge9(x9, z9):
            best = (1e18, -1)
            for i9 in range(len(poly)):
                a9, b9 = poly[i9], poly[(i9 + 1) % len(poly)]
                ex9, ez9 = b9[0] - a9[0], b9[1] - a9[1]
                L9 = ex9 * ex9 + ez9 * ez9 or 1e-9
                tt9 = max(0.0, min(1.0, ((x9 - a9[0]) * ex9 + (z9 - a9[1]) * ez9) / L9))
                dx9, dz9 = x9 - (a9[0] + ex9 * tt9), z9 - (a9[1] + ez9 * tt9)
                dd9 = dx9 * dx9 + dz9 * dz9
                if dd9 < best[0]:
                    best = (dd9, i9)
            return best[1]
        for q9 in range(nz):
            for p9 in range(nx):
                if inside[q9][p9]:
                    continue
                if _near_edge9(seed["x0"] + st * p9, seed["z0"] + st * q9) in skip_e9:
                    banned.add((p9, q9))
    for _ in range(spec["smooth"]["passes"]):
        cur = dict(((ix, iz), h[iz][ix]) for ix, iz in soft)
        for ix, iz in soft:
            acc = []
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    p, q = ix + dx, iz + dz
                    if 0 <= p < nx and 0 <= q < nz and h[q][p] is not None \
                       and (p, q) not in banned:
                        acc.append(cur.get((p, q), h[q][p]))
            if acc:
                h[iz][ix] = sum(acc) / len(acc)
    log.append("⑦ 変えた %d セル + 周り = %d セルを %d 回平滑化"
               "(⛔ クリップを外した辺の外側 %d セルは平均に混ぜない%s)"
               % (len(changed), len(soft), spec["smooth"]["passes"], len(banned),
                  ("・" + "辺" + "/辺".join(str(q) for q in sorted(skip_e9))) if skip_e9 else ""))

    # ⑧ **区画線の上は正本と一致させる**(2026-08-25 土井の申し入れ / 08-24 通達)。
    #    境から edgeClip[m] かけて復元へ摺り付ける。⛔ 境の線そのものは seed(=正本)。
    ec = spec.get("edgeClip", {}).get("m", 0.0)
    skip = set(spec.get("edgeClip", {}).get("skipEdges", []) or [])
    if ec > 0:
        n8 = 0
        for (ix, iz), (u, v) in uv.items():
            if h[iz][ix] is None or seed["h"][iz][ix] is None:
                continue
            x = seed["x0"] + st * ix
            z = seed["z0"] + st * iz
            dd = _poly_dist(poly, x, z, skip)
            if dd >= 2.0 * ec:
                continue
            # 区画線から ec までは**まるごと正本**(双一次で線の上を拾っても正本になるように)、
            # そこから ec かけて復元へ摺り付ける。
            w = max(0.0, min(1.0, (dd - ec) / ec))
            before = h[iz][ix]
            h[iz][ix] = seed["h"][iz][ix] * (1.0 - w) + h[iz][ix] * w
            if abs(before - h[iz][ix]) > 0.005:
                n8 += 1
        log.append("⑧ 区画線から %.1fm はまるごと正本・そこから %.1fm で復元へ摺り付け(%d セル)"
               " — 境の線は正本と一致。**外した辺: %s**(隣家が無い辺)"
               % (ec, ec, n8, ("辺" + "・辺".join(str(q) for q in sorted(skip))) if skip else "なし"))
    return h, log, py, changed | soft, len(sel)


def _near_edge_i(poly, x, z):
    """点 (x,z) にいちばん近い辺の番号。差分を辺ごとに割って刷るのに使う。"""
    best = (1e18, -1)
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ex, ez = b[0] - a[0], b[1] - a[1]
        L = ex * ex + ez * ez or 1e-9
        tt = max(0.0, min(1.0, ((x - a[0]) * ex + (z - a[1]) * ez) / L))
        dx, dz = x - (a[0] + ex * tt), z - (a[1] + ez * tt)
        dd = dx * dx + dz * dz
        if dd < best[0]:
            best = (dd, i)
    return best[1]


def build(check=False):
    base = load(BASE)
    sz = load(SASHIZU)
    poly = sz["polygon"]
    spec = load(RECON)

    # ── 区画が窓に収まっているか(build_base_dem.py と同じ関門)
    xs = [p[0] for p in poly]; zs = [p[1] for p in poly]
    m = (xs[0] - WIN["x0"], WIN["x0"] + WIN["step"] * (WIN["nx"] - 1) - max(xs),
         min(zs) - WIN["z0"], WIN["z0"] + WIN["step"] * (WIN["nz"] - 1) - max(zs))
    marg = (min(xs) - WIN["x0"], WIN["x0"] + WIN["step"] * (WIN["nx"] - 1) - max(xs),
            min(zs) - WIN["z0"], WIN["z0"] + WIN["step"] * (WIN["nz"] - 1) - max(zs))
    if min(marg) < 0:
        sys.exit("⛔ 岡部区画が窓の外へ出ている(余白 西%+.0f 東%+.0f 南%+.0f 北%+.0f m)。"
                 "WIN を広げること" % marg)
    print("   区画の余白 西%+4.0f 東%+4.0f 南%+4.0f 北%+4.0f m%s"
          % (marg + ("  ⚠ 20m 未満" if min(marg) < 20 else "",)))

    ix0 = (WIN["x0"] - base["x0"]) // base["step"]
    iz0 = (WIN["z0"] - base["z0"]) // base["step"]

    # ── ① 正本をこの窓へ切り出し、**復元の手順をその上で実行する**
    seed = dict(WIN)
    seed["h"] = [[base["h"][iz + iz0][ix + ix0] for ix in range(WIN["nx"])]
                 for iz in range(WIN["nz"])]
    gr = RGrid(sz)
    hw, log, py, touched, ncell = reconstruct(seed, poly, gr, spec)
    for line in log:
        print("   " + line.replace("**", ""))
    inside = 0
    for iz in range(WIN["nz"]):
        for ix in range(WIN["nx"]):
            x = WIN["x0"] + WIN["step"] * ix
            z = WIN["z0"] + WIN["step"] * iz
            if in_poly(poly, x, z):
                inside += 1
            else:
                hw[iz][ix] = seed["h"][iz][ix]   # ⛔ 区画の外は正本そのもの
            if hw[iz][ix] is not None:
                hw[iz][ix] = round(hw[iz][ix], 2)
    # **復元がどれだけ値を作ったか**を段ごとに数えて書き出す。
    # ⚠ 「復元地盤が面の高さとちょうど一致するセルの割合」は、帯を傾け平滑化すれば
    #    構成上ゼロに近づく量で、依存度の指標にならない(2026-08-25 考証)。
    frac = {}
    for t in sz["terraces"]:
        tot = hit = 0
        for iz in range(WIN["nz"]):
            for ix in range(WIN["nx"]):
                x = WIN["x0"] + WIN["step"] * ix
                z = WIN["z0"] + WIN["step"] * iz
                u, v = gr.L(x, z)
                if not (in_poly(poly, x, z) and _tin(t, u, v)):
                    continue
                tot += 1
                if (ix, iz) in touched:
                    hit += 1
        if tot:
            frac[t["name"]] = round(100.0 * hit / tot, 1)
    spec["plateau"]["y"] = py                    # 算出値を仕様へ書き戻す(手で持たない)
    if not check:
        json.dump(spec, open(RECON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    world = dict(WIN)
    world["_"] = (
        "**江戸期の復元地盤**を世界座標2m格子で出したもの(確度U/B)。指図の現況図(段彩+等高線)="
        "**造成の出発点**に使う。**区画の中 = 正本 `base_dem.json` に復元の手順"
        "(`okabe_edo_recon.json` の仕様)を実行した面／区画の外 = 正本そのもの**"
        "(近代造成を戻す判断は岡部の敷地内でのみ行う)。"
        "⛔ 手で編集しない・Unity の live terrain から採り直さない(CLAUDE.md 規則12)。"
        "生成器 `Tools/Sashizu/build_okabe_edo_dem.py`。")
    world["_computed"] = {"plateauY": py, "plateauCells": ncell, "modelPct": frac,
                          "_": "生成器が書く算出値。**手で持たない**。plateauY=台地の自然面"
                               "(盛土を免れた実測 plateauCells セルの中央値)/ "
                               "modelPct=段ごとに**復元が値を作ったセルの割合[%]** — "
                               "これが復元への依存度の指標(『面の高さとちょうど一致する割合』ではない)"}
    world["h"] = hw

    # ── ② 復元地盤の回転間グリッド版(world の再標本。復元の正典は world 一枚)
    gr = RGrid(sz)
    rot = load(ROT_EDO)
    he = []
    for iv in range(rot["nv"]):
        row = []
        for iu in range(rot["nu"]):
            u = rot["u0"] + rot["step"] * iu
            v = rot["v0"] + rot["step"] * iv
            x, z = gr.W(u, v)
            row.append(round(bilinear(world, x, z), 2)
                       if in_poly(poly, x, z) and bilinear(world, x, z) is not None else None)
        he.append(row)
    edo_rot = dict((k, rot[k]) for k in ("grid", "u0", "v0", "step", "nu", "nv"))
    edo_rot["_"] = (
        "**江戸期の復元地盤**(回転間グリッド shukaku の1間格子)。h[iv][iu]=標高m、区画の外は null。"
        "**`okabe_edo_world.json` の双一次再標本**であって、別々に復元を走らせない"
        "(2026-08-23 の検図: 同じ『江戸期地盤』を名乗って最大4.0m 食い違っていた)。"
        "**面の高さ・石垣基壇・拝領時造成の切盛はこの面に対して出す**。"
        "⛔ 手で編集しない。生成器 `Tools/Sashizu/build_okabe_edo_dem.py`。")
    edo_rot["h"] = he

    # ── ③ 現況(近代造成を含む)の回転間グリッド版。**種地は正本**
    cur = load(ROT_CUR)
    hc = []
    for iv in range(cur["nv"]):
        row = []
        for iu in range(cur["nu"]):
            u = cur["u0"] + cur["step"] * iu
            v = cur["v0"] + cur["step"] * iv
            x, z = gr.W(u, v)
            y = bilinear(base, x, z)
            row.append(round(y, 2) if (in_poly(poly, x, z) and y is not None) else None)
        hc.append(row)
    cur_rot = dict((k, cur[k]) for k in ("grid", "u0", "v0", "step", "nu", "nv"))
    cur_rot["_"] = (
        "**造成前の現地形**(近代造成を含む現代の地面)を回転間グリッド shukaku で持つ。"
        "h[iv][iu]=標高m、区画の外は null。指図の生成器が切盛図と断面の切盛ハッチに使う。"
        "**種地は正本 `base_dem.json`**(確度P) — ⚠ 2026-08-24 まで 2026-08-23 に Unity の "
        "live terrain から採った標本で、松平の造成を含んでいた(CLAUDE.md 規則12)。"
        "⛔ 手で編集しない。生成器 `Tools/Sashizu/build_okabe_edo_dem.py`。")
    cur_rot["h"] = hc

    # ── 差分の報告(冪等の確認を兼ねる)
    for path, new, old in ((WORLD, world, load(WORLD)),
                           (ROT_EDO, edo_rot, load(ROT_EDO)),
                           (ROT_CUR, cur_rot, load(ROT_CUR))):
        nm = os.path.basename(path)
        key = "h"
        n = big = 0
        mx = 0.0
        for r1, r2 in zip(new[key], old[key]):
            for a, b in zip(r1, r2):
                if a is None and b is None:
                    continue
                if a is None or b is None:
                    n += 1; big += 1
                    continue
                if abs(a - b) > 0.005:
                    n += 1
                    mx = max(mx, abs(a - b))
                    if abs(a - b) > 0.5:
                        big += 1
        print("   %-24s 変わる %5d セル (うち>0.5m %4d / 最大 %.2fm)" % (nm, n, big, mx))
        if path == WORLD and n:
            # ⭐ **辺ごとに割って刷る。**⛔ 「縁だけが動いた」を言葉で言わずに数で示す
            #   (2026-09-03: ⑦の除外を入れたときに、隣家のある辺が 0.000m のままであることを
            #    確かめるために足した)。
            per = {}
            for iz9, (r1, r2) in enumerate(zip(new[key], old[key])):
                for ix9, (a9, b9) in enumerate(zip(r1, r2)):
                    if a9 is None or b9 is None or abs(a9 - b9) <= 0.005:
                        continue
                    x9 = new["x0"] + new["step"] * ix9
                    z9 = new["z0"] + new["step"] * iz9
                    e9 = _near_edge_i(poly, x9, z9)
                    p9 = per.setdefault(e9, [0, 0.0])
                    p9[0] += 1
                    p9[1] = max(p9[1], abs(a9 - b9))
            for e9 in range(len(poly)):
                c9, m9 = per.get(e9, (0, 0.0))
                print("      辺%-2d %5d セル / 最大 %.3fm%s"
                      % (e9, c9, m9, "" if c9 else "   ⭕ 動いていない"))
        if not check:
            json.dump(new, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("   区画内 %d セル / 台地の自然面 %.2f(正本から算出)" % (inside, py))
    if check:
        print("   (--check なので書いていない)")


if __name__ == "__main__":
    if "--extract" in sys.argv:
        extract()
    else:
        build(check="--check" in sys.argv)
