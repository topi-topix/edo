#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""松平出羽守邸の江戸期地盤レイヤの生成器 — **種地は正本 `base_dem.json`、復元は松平区画でクリップ**。

CLAUDE.md 規則13 / `docs/Sashizu/README.md` 決めごと5 /
スキル `unity-buke-yashiki` `references/sashizu.md` §3a「地形は正本から採る」。

⚠ **2026-08-26 に起こし、2026-09-02 に復元を実装した。**
2026-08-26 版は隣家(土井)の共有辺検査のための**素の正本の写し**(復元 0 セル)だった。
⛔ 復元の定義は「松平の屋敷セッションの仕事」と書かれたまま 8 日放置され、
掲示板 EDO-0114(岡部 2026-09-02)で **溜池側の西斜面が江戸期の復元の当たっていない
現代の地面のまま**であることが全邸で発覚した。当邸の指図の西斜面(帯・遮蔽木)は
すべて現代の地面(外堀通りの切土・溜池の陸化を含む)の上に立っていた。

⭐ **復元の手順は `matsudaira_dewa_edo_recon.json`(仕様・確度U/B)が持つ。**
本生成器はその仕様を正本に対して実行するだけで、**値を持たない**。
仕様が無ければ 2026-08-26 版と同じく**素の正本の写し**を書く(復元 0 セル)。

⛔ **`matsudaira_dewa_terrain.json`(手書き・2026-08-25 ユーザー裁定待ち)には触れない。**
本生成器は **別名**で回転格子版を書く(下表)。指図の生成器の読み替えは別途。

書くもの(派生物 — **手で編集しない**):

| ファイル | 中身 |
|---|---|
| `matsudaira_dewa_edo_world.json` | **江戸期の復元地盤**(世界2m格子)。区画の中=正本+復元 / 外=**正本そのもの** |
| `matsudaira_dewa_edo_dem.json`   | 上を回転間グリッド(shukaku)へ双一次で再標本。区画の外は null |
| `matsudaira_dewa_cur_dem.json`   | **現況**(近代造成を含む)を回転間グリッドへ。種地は正本。区画の外は null |

使い方:
    python3 Tools/Sashizu/build_matsudaira_dewa_edo_dem.py            # 書く(冪等)
    python3 Tools/Sashizu/build_matsudaira_dewa_edo_dem.py --check    # 書かずに検査だけ

⚠ 岡部 `build_okabe_edo_dem.py` からの移植。⛔ **岡部の低地の帯モデル(v 方向の三帯)は
持ち込まない** — 岡部は「幅56m の平場が拝領地の中」、当邸は「平場は区画の外・区画の中は
ほぼ斜面」で地形が違う(2026-09-02 実測)。当邸の復元は**法肩(指図の `slopeArea.crest`)→
法尻(区画の西辺 `toeEdges`)**の斜面モデル一本で、法尻の高さを明治16年図の ○ から取る。
"""

import json
import math
import os
import sys

DOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "docs", "Sashizu"))
BASE = os.path.join(DOC, "base_dem.json")
SASHIZU = os.path.join(DOC, "matsudaira_dewa_sashizu.json")
RECON = os.path.join(DOC, "matsudaira_dewa_edo_recon.json")      # ⚠ 旧名 matsudaira_edo_recon は規則15違反
WORLD = os.path.join(DOC, "matsudaira_dewa_edo_world.json")
ROT_EDO = os.path.join(DOC, "matsudaira_dewa_edo_dem.json")
ROT_CUR = os.path.join(DOC, "matsudaira_dewa_cur_dem.json")
ROT_SRC = os.path.join(DOC, "matsudaira_dewa_terrain.json")      # 回転格子の諸元だけ借りる(読むだけ)

# 世界2m格子の窓 — `matsudaira_dewa_dem.json` と同じ範囲(現況図が同じ枠で読めるように)
WIN = dict(x0=-770, z0=1020, step=2, nx=170, nz=150)


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
    """回転間グリッド (u,v)[間] ↔ 世界座標。指図の grid をそのまま使う。"""

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
        dx, dz = x - self.x0, z - self.z0
        return ((dx * self.ux + dz * self.uz) / self.ken,
                (dx * self.vx + dz * self.vz) / self.ken)


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _pl_dist(P, x, z, closed=False):
    """折れ線(閉じるなら多角形)の辺までの最短距離と、その足の弧長パラメタ s[m]。"""
    best, bs, acc = None, 0.0, 0.0
    n = len(P) if closed else len(P) - 1
    for i in range(n):
        a, b = P[i], P[(i + 1) % len(P)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        dd = math.hypot(x - (a[0] + dx * t), z - (a[1] + dz * t))
        if best is None or dd < best:
            best, bs = dd, acc + math.sqrt(L2) * t
        acc += math.sqrt(L2)
    return best, bs


def flats(grid, tol, minCells, poly=None):
    """**近代造成の平坦を形で拾う。** 高さを決め打ちせず、隣と tol 以内で連なる面の連結成分を取る。
    ⭐ `poly` を渡さなければ**窓の全体**で拾う — 当邸の近代の平坦(外堀通り・陸化した岸)は
    **区画の外**にあり、その縁の切土が区画の中の斜面を作っている(岡部と違う点)。"""
    nx, nz, h = grid["nx"], grid["nz"], grid["h"]
    seen = [[False] * nx for _ in range(nz)]
    cells, comps = set(), []
    for iz in range(nz):
        for ix in range(nx):
            y = h[iz][ix]
            if y is None or seen[iz][ix]:
                continue
            if poly and not in_poly(poly, grid["x0"] + grid["step"] * ix, grid["z0"] + grid["step"] * iz):
                seen[iz][ix] = True
                continue
            stack, got = [(ix, iz)], []
            seen[iz][ix] = True
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
                    if poly and not in_poly(poly, grid["x0"] + grid["step"] * p, grid["z0"] + grid["step"] * q):
                        seen[q][p] = True
                        continue
                    seen[q][p] = True
                    stack.append((p, q))
            if len(got) >= minCells:
                comps.append((len(got), round(y, 2)))
                cells |= set(got)
    comps.sort(reverse=True)
    return cells, comps


def reconstruct(seed, sz, spec):
    """**近代造成を戻して江戸期の地盤を起こす。** 仕様の手順を正本(seed)に対して実行する。
    返すのは (h, ログ, 触ったセル)。⛔ 松平区画の中だけを触る。

    手順(仕様 `order` と一致させること):
      ① 近代の平坦を**窓の全体**で形から拾う(外堀通り・陸化した岸は区画の外)
      ② その平坦の縁 `edgeCap` 以内はまるごと・`feather` かけて現況へ摺り付ける重みを作る
      ③ 法肩(`slopeArea.crest`・高さは正本のまま)→ 法尻(`toeEdges`・高さは明治16年図の ○ を
         岸に沿って内挿)を **一定勾配**で結ぶ斜面モデルで、重みのある所だけ置き換える
      ④ 変えたセル+周り1セルを平滑化
      ⑤ 区画線から `edgeClip` はまるごと正本(隣家と同じ面を読む協定)"""
    log = []
    poly = sz["polygon"]
    gr = RGrid(sz)
    nx, nz, st = seed["nx"], seed["nz"], seed["step"]
    h = [[seed["h"][iz][ix] for ix in range(nx)] for iz in range(nz)]
    inside = {}
    for iz in range(nz):
        for ix in range(nx):
            x = seed["x0"] + st * ix
            z = seed["z0"] + st * iz
            if in_poly(poly, x, z):
                inside[(ix, iz)] = (x, z)

    # ① 近代の平坦(窓の全体)
    fd = spec["flatDetect"]
    scope_poly = None if fd.get("scope", "window") == "window" else poly
    flatset, comps = flats(seed, fd["tol"], fd["minCells"], scope_poly)
    log.append("① 近代の平坦 %d 面 %d セル(%s。上位: %s)"
               % (len(comps), len(flatset), "窓の全体" if scope_poly is None else "区画の中",
                  " / ".join("%.2f×%d" % (y, n) for n, y in comps[:4])))

    # ② 平坦からの距離の重み
    mk = spec["mask"]
    cap = mk["edgeCap"] / float(st)
    fea = mk["feather"] / float(st)
    rad = int(math.ceil(cap + fea))
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

    # ③ 斜面モデル — **1883 の法肩と法尻**(考証方の断面の px→X)を端にする。
    #   ⛔ 2026-09-02 の初版は端を指図の設計線(法肩=木柵の線・法尻=区画線)に置いており、
    #   ①法肩が smoothing で 0.94m 下がる ②法尻の高さ 10.0 を区画線に当てて 1883 の法尻(区画の
    #   0.7〜4.7m 外)より低く復元する ③門の外へ 25 セル漏れる、の3つが出た。
    #   ⭕ 端 = `slope.crestSpots` / `slope.toeSpots`(世界座標の折れ線)。高さは法肩=正本(P)・法尻=仕様(U)。
    #   ⭕ 適用域 = 両折れ線に挟まれた帯 × 折れ線の Z 範囲(± `spanFeather`)。法肩の直近 `crestFeather` は正本へ摺り付け。
    sl = spec["slope"]
    sa = sz["slopeArea"]
    cr = sorted([(sp["xz"][0], sp["xz"][1]) for sp in sl["crestSpots"]], key=lambda q: q[1])
    tw = sorted([(sp["xz"][0], sp["xz"][1], float(sp["y"])) for sp in sl["toeSpots"]], key=lambda q: q[1])
    crest_w = cr
    toe_w = [(x, z) for x, z, _ in tw]
    z_lo = min(q[1] for q in cr + toe_w); z_hi = max(q[1] for q in cr + toe_w)
    spf = float(sl.get("spanFeather", 6.0))
    cfe = float(sl.get("crestFeather", 6.0))
    toe_rise = float(sl.get("toeRise", 0.0))
    # 法尻の高さ: Z で一次内挿(端の外は端の値)
    def toe_y(z):
        if z <= tw[0][1]: return tw[0][2]
        if z >= tw[-1][1]: return tw[-1][2]
        for (x0, z0, y0), (x1, z1, y1) in zip(tw, tw[1:]):
            if z0 <= z <= z1:
                return y0 + (y1 - y0) * (z - z0) / max(z1 - z0, 1e-9)
        return tw[-1][2]
    # 折れ線の x を Z で一次内挿(帯の判定を x の大小で行う — 西面は南北に走るので十分)
    def _x_at(line, z):
        if z <= line[0][1]: return line[0][0]
        if z >= line[-1][1]: return line[-1][0]
        for (x0, z0), (x1, z1) in zip(line, line[1:]):
            if z0 <= z <= z1:
                return x0 + (x1 - x0) * (z - z0) / max(z1 - z0, 1e-9)
        return line[-1][0]
    changed, n3 = set(), 0
    for (ix, iz), (x, z) in inside.items():
        if h[iz][ix] is None:
            continue
        # Z の門(折れ線の範囲 ± spanFeather)
        if z < z_lo - spf or z > z_hi + spf:
            continue
        wz = 1.0
        if z < z_lo: wz = (z - (z_lo - spf)) / spf
        if z > z_hi: wz = ((z_hi + spf) - z) / spf
        xc, xt = _x_at(crest_w, z), _x_at(toe_w, z)      # 法肩 x(東)・法尻 x(西)
        if not (xt <= x <= xc):                            # 帯の外(台地・区画外の岸)は触らない
            continue
        t = (x - xt) / max(xc - xt, 1e-9)                   # 0=法尻 … 1=法肩
        cy = bilinear(seed, xc, z)                          # 法肩の高さ = 正本(1883 と ±0.8m で一致)
        if cy is None:
            continue
        ty = toe_y(z) + toe_rise
        y = ty + (cy - ty) * t if sl.get("profile", "grade") == "grade" else None
        if y is None:
            raise SystemExit("⛔ slope.profile=%r は未実装" % sl.get("profile"))
        wc = min(1.0, (xc - x) / cfe) if cfe > 0 else 1.0  # 法肩の直近は正本へ
        w = wc * wz
        if w <= 0.0:
            continue
        y = y * w + h[iz][ix] * (1.0 - w)
        if abs(h[iz][ix] - y) > 0.005:
            changed.add((ix, iz))
        h[iz][ix] = y
        n3 += 1
    log.append("③ 斜面モデル(1883 の法肩 %d 点→法尻 %d 点・一定勾配・法尻 %.1f〜%.1f m【U】・toeRise %.2f)を "
               "%d セルに当てた(Z %.0f〜%.0f ± %.0fm・法肩の直近 %.0fm は正本へ)"
               % (len(cr), len(tw), min(q[2] for q in tw), max(q[2] for q in tw), toe_rise, n3,
                  z_lo, z_hi, spf, cfe))
    # ④ 平滑化(変えたセル+周り1セル)。⛔ 変えていないセルは haloMax 以上動かさない
    sm = spec["smooth"]
    # ⭕ 平滑化は**変えたセルどうしの継ぎ目**だけ — 周りへ広げると法肩(正本)を引き下げ、門の外へ漏れる
    #   (2026-09-02 初版: 法肩 −0.94m・門の外 25 セル)。
    soft = set(changed)
    before = {q: h[q[1]][q[0]] for q in soft}
    for _ in range(sm["passes"]):
        cur = {q: h[q[1]][q[0]] for q in soft}
        for ix, iz in soft:
            acc = []
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    p, q = ix + dx, iz + dz
                    if 0 <= p < nx and 0 <= q < nz and h[q][p] is not None:
                        acc.append(cur.get((p, q), h[q][p]))
            if acc:
                h[iz][ix] = sum(acc) / len(acc)
    hal = float(sm.get("haloMax", 0.30))
    clip = 0
    for q in soft:
        if q in changed or before[q] is None or h[q[1]][q[0]] is None:
            continue
        dv = h[q[1]][q[0]] - before[q]
        if abs(dv) > hal:
            h[q[1]][q[0]] = before[q] + math.copysign(hal, dv)
            clip += 1
    log.append("④ 変えた %d セル+周り = %d セルを %d 回平滑化(変えていないセルの動きは上限 %.2fm・頭打ち %d)"
               % (len(changed), len(soft), sm["passes"], hal, clip))

    # ⑤ 区画線の上は正本(隣家と同じ面を読む協定)
    ec = float(spec.get("edgeClip", {}).get("m", 0.0))
    n5 = 0
    if ec > 0:
        toe_set = set(sa["toeEdges"])
        share = [poly[i] for i in range(len(poly))]     # 閉多角形の全辺のうち法尻辺を除いた距離
        def _dist_nontoe(x, z):
            best = None
            for i in range(len(poly)):
                if i in toe_set:
                    continue
                a, b = poly[i], poly[(i + 1) % len(poly)]
                ddx, ddz = b[0] - a[0], b[1] - a[1]
                L2 = ddx * ddx + ddz * ddz or 1e-9
                tt = max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[1]) * ddz) / L2))
                dq = math.hypot(x - (a[0] + ddx * tt), z - (a[1] + ddz * tt))
                best = dq if best is None else min(best, dq)
            return best
        for (ix, iz), (x, z) in inside.items():
            if h[iz][ix] is None or seed["h"][iz][ix] is None:
                continue
            # ⛔ 法尻の辺(堀端通り・溜池側)は協定の相手が隣家でないので edgeClip の対象外
            dd = _dist_nontoe(x, z)
            if dd >= 2.0 * ec:
                continue
            w = max(0.0, min(1.0, (dd - ec) / ec))
            b4 = h[iz][ix]
            h[iz][ix] = seed["h"][iz][ix] * (1.0 - w) + h[iz][ix] * w
            if abs(b4 - h[iz][ix]) > 0.005:
                n5 += 1
    log.append("⑤ 区画線から %.1fm はまるごと正本・そこから %.1fm で復元へ摺り付け(%d セル)" % (ec, ec, n5))
    return h, log, changed | soft


def _crest_height(seed, crest_w, x, z):
    """法肩線の最寄り点の**正本**の高さ。⛔ 復元しない(台地の縁は近代に動いていない前提【U】)。"""
    best = None
    for i in range(len(crest_w) - 1):
        a, b = crest_w[i], crest_w[i + 1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        px, pz = a[0] + dx * t, a[1] + dz * t
        dd = math.hypot(x - px, z - pz)
        if best is None or dd < best[0]:
            best = (dd, px, pz)
    return bilinear(seed, best[1], best[2]) if best else None


def _rot(sz, src, world_like, poly):
    """世界格子 → 回転間グリッド(諸元は `src`)。区画の外は null。"""
    gr = RGrid(sz)
    out = dict((k, src[k]) for k in ("grid", "u0", "v0", "step", "nu", "nv"))
    hh = []
    for iv in range(src["nv"]):
        row = []
        for iu in range(src["nu"]):
            u = src["u0"] + src["step"] * iu
            v = src["v0"] + src["step"] * iv
            x, z = gr.W(u, v)
            y = bilinear(world_like, x, z)
            row.append(round(y, 2) if (in_poly(poly, x, z) and y is not None) else None)
        hh.append(row)
    out["h"] = hh
    return out


def build(check=False):
    base = load(BASE)
    sz = load(SASHIZU)
    poly = sz["polygon"]

    xs = [p[0] for p in poly]; zs = [p[1] for p in poly]
    marg = (min(xs) - WIN["x0"], WIN["x0"] + WIN["step"] * (WIN["nx"] - 1) - max(xs),
            min(zs) - WIN["z0"], WIN["z0"] + WIN["step"] * (WIN["nz"] - 1) - max(zs))
    if min(marg) < 0:
        sys.exit("⛔ 松平区画が窓の外へ出ている(余白 西%+.0f 東%+.0f 南%+.0f 北%+.0f m)" % marg)
    print("   区画の余白 西%+4.0f 東%+4.0f 南%+4.0f 北%+4.0f m%s"
          % (marg + ("  ⚠ 20m 未満" if min(marg) < 20 else "",)))

    ix0 = int((WIN["x0"] - base["x0"]) // base["step"])
    iz0 = int((WIN["z0"] - base["z0"]) // base["step"])
    seed = dict(WIN)
    seed["h"] = [[base["h"][iz + iz0][ix + ix0] for ix in range(WIN["nx"])]
                 for iz in range(WIN["nz"])]

    if os.path.exists(RECON):
        spec = load(RECON)
        hw, log, touched = reconstruct(seed, sz, spec)
        for line in log:
            print("   " + line.replace("**", ""))
        recon_note = ("区画の中 = 正本 `base_dem.json` に復元の手順(`matsudaira_dewa_edo_recon.json`)"
                      "を実行した面／区画の外 = 正本そのもの")
    else:
        hw = [row[:] for row in seed["h"]]
        touched = set()
        print("   ⚠ %s が無い — 復元 0 セル(正本そのまま)。西斜面は**現代の地面のまま**である"
              "(EDO-0114)" % os.path.basename(RECON))
        recon_note = "⛔ 復元は未定義 — 区画の中も外も正本 `base_dem.json` そのもの(復元 0 セル)"

    inside = 0
    for iz in range(WIN["nz"]):
        for ix in range(WIN["nx"]):
            x = WIN["x0"] + WIN["step"] * ix
            z = WIN["z0"] + WIN["step"] * iz
            if in_poly(poly, x, z):
                inside += 1
            else:
                hw[iz][ix] = seed["h"][iz][ix]           # ⛔ 区画の外は正本そのもの
            if hw[iz][ix] is not None:
                hw[iz][ix] = round(hw[iz][ix], 2)
    print("   区画内 %d セル(2m格子)/ 復元が値を作った %d セル" % (inside, len(touched)))

    world = dict(WIN)
    world["_"] = ("**江戸期の復元地盤**(世界2m格子・確度U/B)。指図の現況図と造成の出発点に使う。"
                  + recon_note + "。⛔ 手で編集しない・live terrain から採り直さない(規則13)。"
                  "生成器 `Tools/Sashizu/build_matsudaira_dewa_edo_dem.py`。")
    world["_reconCells"] = len(touched)
    world["h"] = hw

    src = load(ROT_SRC)                                   # 諸元だけ借りる(読むだけ)
    edo_rot = _rot(sz, src, world, poly)
    edo_rot["_"] = ("**江戸期の復元地盤**(回転間グリッド shukaku の1間格子)。h[iv][iu]=標高m、区画の外は null。"
                    "**`matsudaira_dewa_edo_world.json` の双一次再標本**であって、別々に復元を走らせない。"
                    "面の高さ・石垣基壇・拝領時造成の切盛・西斜面の帯はこの面に対して出す。"
                    "⛔ 手で編集しない。生成器 `Tools/Sashizu/build_matsudaira_dewa_edo_dem.py`。")
    cur_rot = _rot(sz, src, seed, poly)
    cur_rot["_"] = ("**造成前の現地形**(近代造成を含む現代の地面)を回転間グリッド shukaku で持つ。"
                    "区画の外は null。切盛図と断面の切盛ハッチに使う。**種地は正本 `base_dem.json`**(確度P)。"
                    "⛔ 手で編集しない。生成器 `Tools/Sashizu/build_matsudaira_dewa_edo_dem.py`。")

    for path, new in ((WORLD, world), (ROT_EDO, edo_rot), (ROT_CUR, cur_rot)):
        nm = os.path.basename(path)
        if os.path.exists(path):
            old = load(path)
            oh, nh = old.get("h"), new["h"]
            diff = mx = 0
            for iz in range(min(len(oh), len(nh))):
                for ix in range(min(len(oh[iz]), len(nh[iz]))):
                    a, b = oh[iz][ix], nh[iz][ix]
                    if a is None or b is None:
                        if a != b:
                            diff += 1
                        continue
                    if abs(a - b) > 0.005:
                        diff += 1
                        mx = max(mx, abs(a - b))
            print("   %-34s 前回との差 %d セル(最大 %.2fm)" % (nm, diff, mx))
        else:
            print("   %-34s 新規" % nm)
        if not check:
            json.dump(new, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("   --check: 書かずに終了" if check else "   wrote 3 files")


if __name__ == "__main__":
    build(check="--check" in sys.argv)
