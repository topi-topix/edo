#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""京極備中守邸の地盤レイヤの生成器 — **種地は正本 `base_dem.json`、復元は京極区画でクリップ**。

CLAUDE.md 規則13 / `docs/Sashizu/README.md` 決めごと5 /
スキル `unity-buke-yashiki` `references/sashizu.md` §3a「地形は正本から採る」。

書くもの(いずれも派生物 — 手で編集しない):

| ファイル | 中身 |
|---|---|
| `kyogoku_bitchu_edo_world.json` | **江戸期の復元地盤**(世界2m格子)。区画の中=正本+復元 / 外=**正本そのもの** |
| `kyogoku_bitchu_edo_dem.json`   | 上を間グリッド(shukaku)へ双一次で再標本。区画の外は null |
| `kyogoku_bitchu_terrain.json`   | **現況**(近代造成を含む)を間グリッドへ。種地は正本。区画の外は null |

復元の**手順**は `kyogoku_bitchu_edo_recon.json` が仕様として持つ(区域ごとに典拠と確度つき)。
この生成器はその手順を**正本に対して毎回実行する**(前回の結果を差分として写さない)。

使い方:
    python3 Tools/Sashizu/build_kyogoku_bitchu_edo_dem.py           # 3枚を書く(冪等)
    python3 Tools/Sashizu/build_kyogoku_bitchu_edo_dem.py --check   # 書かずに差分だけ出す
"""

import json
import math
import os
import sys

DOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "docs", "Sashizu"))
BASE = os.path.join(DOC, "base_dem.json")
PARCELS = os.path.join(DOC, "parcels.json")
SASHIZU = os.path.join(DOC, "kyogoku_bitchu_sashizu.json")
RECON = os.path.join(DOC, "kyogoku_bitchu_edo_recon.json")
WORLD = os.path.join(DOC, "kyogoku_bitchu_edo_world.json")
ROT_EDO = os.path.join(DOC, "kyogoku_bitchu_edo_dem.json")
ROT_CUR = os.path.join(DOC, "kyogoku_bitchu_terrain.json")

# 世界2m格子の窓(`kyogoku_bitchu_dem.json` と同じ範囲 — 現況図と同じ枠で読めるように)
WIN = dict(x0=-320, z0=640, step=2, nx=111, nz=96)
# 間グリッドの範囲(区画を覆う。0.5間刻み)
ROT = dict(u0=-2.0, v0=-2.0, step=0.5, nu=178, nv=126)


def load(p):
    return json.load(open(p, encoding="utf-8"))


def dedup(pts):
    o = []
    for pt in pts:
        if not o or abs(pt[0] - o[-1][0]) > 1e-6 or abs(pt[1] - o[-1][1]) > 1e-6:
            o.append(pt)
    return o


def in_poly(poly, x, z):
    n, c = len(poly), False
    for i in range(n):
        (ax, az), (bx, bz) = poly[i], poly[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (bx - ax) * (z - az) / (bz - az):
            c = not c
    return c


def bilinear(S, x, z):
    fx = (x - S["x0"]) / float(S["step"])
    fz = (z - S["z0"]) / float(S["step"])
    i0, j0 = int(math.floor(fx)), int(math.floor(fz))
    if not (0 <= i0 < S["nx"] - 1 and 0 <= j0 < S["nz"] - 1):
        return None
    tx, tz = fx - i0, fz - j0
    q = [S["h"][j0][i0], S["h"][j0][i0 + 1], S["h"][j0 + 1][i0], S["h"][j0 + 1][i0 + 1]]
    if any(v is None for v in q):
        return None
    return (q[0] * (1 - tx) + q[1] * tx) * (1 - tz) + (q[2] * (1 - tx) + q[3] * tx) * tz


def window(base):
    """正本から WIN を切り出す(値はそのまま)。"""
    h = []
    for jz in range(WIN["nz"]):
        z = WIN["z0"] + jz * WIN["step"]
        row = []
        for ix in range(WIN["nx"]):
            x = WIN["x0"] + ix * WIN["step"]
            v = bilinear(base, x, z)
            if v is None:
                raise SystemExit("正本の範囲が窓に足りない: world(%s,%s)" % (x, z))
            row.append(round(v, 2))
        h.append(row)
    return h


def edge_dist(poly, x, z):
    """多角形の縁までの距離[m]。"""
    best = 1e18
    n = len(poly)
    for i in range(n):
        (ax, az), (bx, bz) = poly[i], poly[(i + 1) % n]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        best = min(best, math.hypot(x - (ax + t * dx), z - (az + t * dz)))
    return best


def relax(h, zones, poly, iters, taper):
    """区域の中を、区域のすぐ外の値を境界としてラプラス緩和で埋め直す。
    ⚠ **境界は区画の外からも読む(読むだけ)。書き込みは区画の中だけ。**"""
    free = []
    for jz in range(WIN["nz"]):
        z = WIN["z0"] + jz * WIN["step"]
        for ix in range(WIN["nx"]):
            x = WIN["x0"] + ix * WIN["step"]
            for zn in zones:
                if zn["x"][0] <= x <= zn["x"][1] and zn["z"][0] <= z <= zn["z"][1]:
                    free.append((jz, ix, in_poly(poly, x, z)))
                    break
    g = [row[:] for row in h]
    for _ in range(iters):
        for jz, ix, _inside in free:
            a = g[jz - 1][ix] if jz > 0 else g[jz][ix]
            b = g[jz + 1][ix] if jz < WIN["nz"] - 1 else g[jz][ix]
            c = g[jz][ix - 1] if ix > 0 else g[jz][ix]
            d = g[jz][ix + 1] if ix < WIN["nx"] - 1 else g[jz][ix]
            g[jz][ix] = (a + b + c + d) / 4.0
    # 区画の外へは書かない。区画線に近い帯では効きを 0 まで落とす(共有辺に段差を作らないため)
    out = 0
    for jz, ix, inside in free:
        if not inside:
            if abs(g[jz][ix] - h[jz][ix]) > 1e-9:
                out += 1
            g[jz][ix] = h[jz][ix]
            continue
        x = WIN["x0"] + ix * WIN["step"]
        z = WIN["z0"] + jz * WIN["step"]
        w = 1.0 if taper <= 0 else max(0.0, min(1.0, edge_dist(poly, x, z) / taper))
        g[jz][ix] = h[jz][ix] + w * (g[jz][ix] - h[jz][ix])
    return g, len(free), out


def clamp_floor(h, floors, poly, taper):
    """`floor` より低いセルだけを floor まで引き上げ、smooth 回の緩和で周りへなじませる。
    ⛔ floor より高いセルには触れない(谷・斜面をそのまま残すため)。区画の外へは書かない。"""
    g = [row[:] for row in h]
    for fz_ in floors:
        raised = []
        band = []
        for jz in range(WIN["nz"]):
            z = WIN["z0"] + jz * WIN["step"]
            if not (fz_["z"][0] <= z <= fz_["z"][1]):
                continue
            for ix in range(WIN["nx"]):
                x = WIN["x0"] + ix * WIN["step"]
                if not (fz_["x"][0] <= x <= fz_["x"][1]):
                    continue
                if not in_poly(poly, x, z):
                    continue
                band.append((jz, ix, x, z))
                if g[jz][ix] < fz_["floor"]:
                    g[jz][ix] = fz_["floor"]
                    raised.append((jz, ix))
        # なじませ: 引き上げたセルだけを緩和し、下限は floor で押さえる
        for _ in range(int(fz_.get("smooth", 0))):
            for jz, ix in raised:
                a = g[jz - 1][ix] if jz > 0 else g[jz][ix]
                b = g[jz + 1][ix] if jz < WIN["nz"] - 1 else g[jz][ix]
                c = g[jz][ix - 1] if ix > 0 else g[jz][ix]
                dd = g[jz][ix + 1] if ix < WIN["nx"] - 1 else g[jz][ix]
                g[jz][ix] = max(fz_["floor"], (a + b + c + dd) / 4.0)
        # 区画線へ向けて効きを落とす(共有辺に段差を作らない)
        for jz, ix, x, z in band:
            w = 1.0 if taper <= 0 else max(0.0, min(1.0, edge_dist(poly, x, z) / taper))
            g[jz][ix] = h[jz][ix] + w * (g[jz][ix] - h[jz][ix])
    return g


def rot_sample(S, d, poly, clip=True):
    """世界格子 S を間グリッドへ双一次で再標本する。区画の外は null。"""
    g = d["grid"]["shukaku"]
    ken = d["const"]["ken"]
    h = []
    for jv in range(ROT["nv"]):
        v = ROT["v0"] + jv * ROT["step"]
        row = []
        for iu in range(ROT["nu"]):
            u = ROT["u0"] + iu * ROT["step"]
            x = g["x0"] + (g["ux"] * u + g["vx"] * v) * ken
            z = g["z0"] + (g["uz"] * u + g["vz"] * v) * ken
            if clip and not in_poly(poly, x, z):
                row.append(None)
                continue
            y = bilinear(S, x, z)
            row.append(None if y is None else round(y, 2))
        h.append(row)
    return h


def write(path, obj, check):
    new = json.dumps(obj, ensure_ascii=False, indent=1)
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    same = (old == new)
    tag = "変わらず" if same else ("**新規**" if old is None else "**書き換え**")
    print("   %-40s %s" % (os.path.basename(path), tag))
    if not check and not same:
        open(path, "w", encoding="utf-8").write(new)
    return same


def main():
    check = "--check" in sys.argv
    base = load(BASE)
    d = load(SASHIZU)
    rec = load(RECON)
    poly = dedup({p["id"]: p["pts"] for p in load(PARCELS)["parcels"]}[rec["clip"]])
    if [list(map(float, p)) for p in poly] != [list(map(float, p)) for p in d["polygon"]]:
        raise SystemExit("⛔ 区画が parcels.json と指図で食い違う。parcels.json が正典 — 指図の polygon を直すこと")

    cur = window(base)
    edo, nfree, nout = relax(cur, rec["zones"], poly, rec["iters"], rec.get("edgeTaper", 0.0))
    edo = clamp_floor(edo, rec.get("floors", []), poly,
                      rec.get("edgeTaperFloor", rec.get("edgeTaper", 0.0)))

    # 検算
    fill = mx = 0.0
    cells = 0
    for jz in range(WIN["nz"]):
        z = WIN["z0"] + jz * WIN["step"]
        for ix in range(WIN["nx"]):
            x = WIN["x0"] + ix * WIN["step"]
            dv = edo[jz][ix] - cur[jz][ix]
            if abs(dv) > 1e-6:
                cells += 1
                fill += max(0.0, dv) * WIN["step"] ** 2
                mx = max(mx, dv)
                if not in_poly(poly, x, z):
                    raise SystemExit("⛔ 復元が区画の外へ出た: world(%s,%s)" % (x, z))
    print("復元 — 区域のセル %d / 区画の中で動いた %d / 埋めた土量 %.0f m³ / 最大盛 %.2f m"
          % (nfree, cells, fill, mx))
    print("   ⭐ 区画の外へは1セルも書いていない(緩和で動いた区画外 %d セルは現況へ戻した)" % nout)

    # 共有辺の段差(西辺=丹羽)
    worst = 0.0
    at = None
    for jz in range(WIN["nz"]):
        z = WIN["z0"] + jz * WIN["step"]
        if not (682 <= z <= 789):
            continue
        for ix in range(WIN["nx"] - 1):
            x = WIN["x0"] + ix * WIN["step"]
            a_in = in_poly(poly, x, z)
            b_in = in_poly(poly, x + WIN["step"], z)
            if a_in == b_in:
                continue
            g = abs(edo[jz][ix] - edo[jz][ix + 1])
            if g > worst:
                worst, at = g, (x, z)
    print("   共有辺をまたぐ隣り合うセルの最大の段差 %.2f m at %s(現況の地形の起伏を含む)" % (worst, at))

    ok = True
    ok &= write(WORLD, {
        "_": ("**江戸期の復元地盤**【確度P(種地)+U(復元の範囲=2026-08-31 ユーザー裁定B)】。"
              "世界座標 2m 格子。h[iz][ix]=標高m。区画の中は正本 base_dem.json に "
              "kyogoku_bitchu_edo_recon.json の手順を当てたもの、**区画の外は正本そのもの**。"
              "⛔ 手で編集しない。生成器 Tools/Sashizu/build_kyogoku_bitchu_edo_dem.py"),
        "x0": WIN["x0"], "z0": WIN["z0"], "step": WIN["step"],
        "nx": WIN["nx"], "nz": WIN["nz"], "h": edo}, check)
    ok &= write(ROT_EDO, {
        "_": ("江戸期の復元地盤を**間グリッド**(shukaku)へ再標本したもの。区画の外は null。"
              "指図の切盛図・断面・接地検査はこれを『造成前』として読む。"
              "⛔ 手で編集しない。生成器 Tools/Sashizu/build_kyogoku_bitchu_edo_dem.py"),
        "grid": "shukaku", "u0": ROT["u0"], "v0": ROT["v0"], "step": ROT["step"],
        "nu": ROT["nu"], "nv": ROT["nv"],
        "h": rot_sample({"x0": WIN["x0"], "z0": WIN["z0"], "step": WIN["step"],
                         "nx": WIN["nx"], "nz": WIN["nz"], "h": edo}, d, poly)}, check)
    ok &= write(ROT_CUR, {
        "_": ("**現況**(近代造成を含む今日の地面)を間グリッドへ再標本したもの。区画の外は null。"
              "現況図と、復元の効きを見るための対照に使う。種地は正本 base_dem.json。"
              "⛔ 手で編集しない。生成器 Tools/Sashizu/build_kyogoku_bitchu_edo_dem.py"),
        "grid": "shukaku", "u0": ROT["u0"], "v0": ROT["v0"], "step": ROT["step"],
        "nu": ROT["nu"], "nv": ROT["nv"],
        "h": rot_sample({"x0": WIN["x0"], "z0": WIN["z0"], "step": WIN["step"],
                         "nx": WIN["nx"], "nz": WIN["nz"], "h": cur}, d, poly)}, check)
    if check and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
