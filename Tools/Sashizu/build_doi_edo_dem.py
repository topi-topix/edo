#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""土井邸の地盤レイヤの生成器 — **種地は正本 `base_dem.json`、復元は土井区画でクリップ**。

CLAUDE.md 規則12 / `docs/Sashizu/README.md` 決めごと5 /
スキル `unity-buke-yashiki` `references/sashizu.md` §3a「地形は正本から採る」。

⚠ **2026-08-25 に起こした。** それまで土井は復元レイヤを持たず、
**現代の地面をそのまま「自然の平場」として面に採っていた**。
区画内には σ=0.000 の平坦板が4枚あり(337/321/264/238 m²)、そのうち玄関の郭の
24.60 の板は、実装が「メキシコ大使館の掘り込み」と名指しして平滑化している範囲そのものだった
(2026-08-25 検図12巡 高-1)。300m² が小数2桁まで平らな地面は自然にはできない。

書くもの(いずれも派生物 — **手で編集しない**):

| ファイル | 中身 |
|---|---|
| `doi_edo_world.json` | **江戸期の復元地盤**(世界2m格子)。区画の中=正本+復元 / 外=**正本そのもの** |
| `doi_edo_dem.json`   | 上を回転間グリッド(shukaku)へ再標本。区画の外は null |

復元の**手順**は `doi_edo_recon.json` が仕様として持つ(項目ごとに典拠と確度つき)。
この生成器はその手順を**正本に対して毎回実行する** — 前の復元値を差分として写さない
(写すと種地が動いても復元が追随せず、「地形は正本から採る」が名ばかりになる)。

使い方:
    python3 Tools/Sashizu/build_doi_edo_dem.py            # 2枚を書く(冪等)
    python3 Tools/Sashizu/build_doi_edo_dem.py --check    # 書かずに差分だけ出す
"""

import json
import math
import os
import sys

DOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "docs", "Sashizu"))
BASE = os.path.join(DOC, "base_dem.json")
SASHIZU = os.path.join(DOC, "doi_sashizu.json")
RECON = os.path.join(DOC, "doi_edo_recon.json")
WORLD = os.path.join(DOC, "doi_edo_world.json")
ROT_EDO = os.path.join(DOC, "doi_edo_dem.json")


def load(p):
    return json.load(open(p, encoding="utf-8"))


def in_poly(poly, x, z):
    c = False
    n = len(poly)
    for i in range(n):
        (ax, az), (bx, bz) = poly[i], poly[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (bx - ax) * (z - az) / (bz - az):
            c = not c
    return c


def bilinear(S, x, z):
    fx = (x - S["x0"]) / S["step"]
    fz = (z - S["z0"]) / S["step"]
    ix, iz = int(math.floor(fx)), int(math.floor(fz))
    if ix < 0 or iz < 0 or ix + 1 >= S["nx"] or iz + 1 >= S["nz"]:
        return None
    tx, tz = fx - ix, fz - iz
    q = [S["h"][iz][ix], S["h"][iz][ix + 1], S["h"][iz + 1][ix], S["h"][iz + 1][ix + 1]]
    if any(w is None for w in q):
        return None
    return (q[0] * (1 - tx) + q[1] * tx) * (1 - tz) + (q[2] * (1 - tx) + q[3] * tx) * tz


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def flats(grid, poly, tol, minCells):
    """**近代造成の平坦を形で拾う。** 高さを決め打ちせず、隣と tol 以内で連なる面の連結成分。
    返すのは 成分ごとの {cells, y, n}。"""
    nx, nz, h = grid["nx"], grid["nz"], grid["h"]
    seen = [[False] * nx for _ in range(nz)]
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
                comps.append({"cells": set(got), "y": round(y, 2), "n": len(got)})
    comps.sort(key=lambda c: -c["n"])
    return comps


def reconstruct(seed, poly, spec):
    """近代造成を戻して江戸期の地盤を起こす。返すのは (h, ログ)。⛔ 土井区画の中だけを触る。"""
    log = []
    nx, nz, st = seed["nx"], seed["nz"], seed["step"]
    h = [[seed["h"][iz][ix] for ix in range(nx)] for iz in range(nz)]
    inside = {}
    for iz in range(nz):
        for ix in range(nx):
            x = seed["x0"] + st * ix
            z = seed["z0"] + st * iz
            if in_poly(poly, x, z):
                inside[(ix, iz)] = (x, z)

    # ⑤ 触らない範囲(南辺・東辺・西縁)。判定不能を判定不能のまま持つ
    mk = spec["mask"]

    def masked(x, z):
        return z < mk["zMin"] or x > mk["xMax"] or x < mk["xMin"]

    # ③ 近代の平坦を形で検出 — **①②より先に回す。** 検出した平坦は「自然の台地」の
    #    母集団からも補間の種からも外す。⛔ §A-6「平らだから自然地形」は循環論法であり、
    #    平らな板を種にすれば**近代の造成面を江戸期の地盤として塗り広げる**ことになる
    #    (2026-08-25 検図13巡 中-3)。
    fd = spec["flatDetect"]
    comps = flats(seed, poly, fd["tol"], fd["minCells"])
    flatcells = set()
    for c in comps:
        flatcells |= c["cells"]
    log.append("③ 広い平坦 %d 面(上位: %s)— **②以外は自動では触らない**"
               % (len(comps), " / ".join("%.2f×%d" % (c["y"], c["n"]) for c in comps[:5])))

    # ① 台地の自然面 = 正本の実測セルの中央値(値は仕様に持たない)
    pl = spec["plateau"]
    def _plateau_pop(drop_flat):
        return [seed["h"][iz][ix] for (ix, iz), (x, z) in inside.items()
                if seed["h"][iz][ix] is not None and z >= pl["zMin"] and not masked(x, z)
                and pl["cellMin"] <= seed["h"][iz][ix] <= pl["cellMax"]
                and not (drop_flat and (ix, iz) in flatcells)]
    sel_all = _plateau_pop(False)
    sel = _plateau_pop(True)
    py = round(median(sel), 2) if sel else None
    log.append("① 台地の自然面 = 実測 %d セルの中央値 **%.2f**(振れ %.2f〜%.2f)"
               % (len(sel), py, min(sel), max(sel)))
    # ⚠ **中央値は fallback にしか使わない。** 数値だけ載せると是正が効いたように読めるが、
    #   種の入替が地盤に与える差は 2桁丸めの粒度と同じで、棟の接地は動かない
    #   (2026-08-25 検図14巡 低-1)。**効いたのは掘削跡の埋め戻しのほうである。**
    log.append("   ③の平坦 %d セルを母集団から外した(外さなければ %d セル・中央値 %.2f)"
               % (len(sel_all) - len(sel), len(sel_all), median(sel_all)))
    log.append("   ⚠ 中央値は逆距離加重が届かないセルの fallback にのみ使う。"
               "種の入替による地盤の変動は**最大 0.03m**(§B-1 の予算 0.5m の 1/17)で、"
               "棟の接地は 17棟とも ≤0.03pt しか動かない。"
               "**玄関棟の合否を 100%%→3%% に反転させたのは掘削跡の埋め戻しのほう。**")

    # ② 玄関の郭の掘削跡を、周囲の台地セルから逆距離加重で埋め戻す
    cf = spec["cutFlat"]
    bx = cf["box"]
    target = set()
    for (ix, iz), (x, z) in inside.items():
        y = seed["h"][iz][ix]
        if y is None or masked(x, z):
            continue
        if not (bx[0] <= x <= bx[1] and bx[2] <= z <= bx[3]):
            continue
        if cf["cellMin"] <= y <= cf["cellMax"]:
            target.add((ix, iz))
    log.append("② 掘削跡と判定したセル **%d**(箱 x%.0f..%.0f / z%.0f..%.0f・%.1f〜%.1fm)"
               % (len(target), bx[0], bx[1], bx[2], bx[3], cf["cellMin"], cf["cellMax"]))

    kl = spec["keepLow"]["box"]
    ip = spec["interp"]
    rad = int(math.ceil(ip["radius"] / float(st)))
    # 補間の種は「台地の窓に入る、掘削跡でない、南東の谷でない、マスク外」のセルだけ
    src = {}
    for (ix, iz), (x, z) in inside.items():
        y = seed["h"][iz][ix]
        if y is None or (ix, iz) in target or masked(x, z):
            continue
        if kl[0] <= x <= kl[1] and kl[2] <= z <= kl[3]:
            continue                       # ④ 南東の谷は種に使わない(低いので窪みが残る)
        if (ix, iz) in flatcells:
            continue                       # ③ 近代の平坦は種にしない(§A-6 の循環論法を断つ)
        if pl["cellMin"] <= y <= pl["cellMax"]:
            src[(ix, iz)] = y
    n3 = 0
    for (ix, iz) in target:
        num = den = 0.0
        for dx in range(-rad, rad + 1):
            for dz in range(-rad, rad + 1):
                q = (ix + dx, iz + dz)
                if q not in src:
                    continue
                dd = math.hypot(dx, dz) * st
                if dd > ip["radius"] or dd < 1e-9:
                    continue
                w = 1.0 / (dd ** ip["power"])
                num += src[q] * w
                den += w
        h[iz][ix] = round(num / den, 2) if den > 0 else py
        n3 += 1
    log.append("   → 台地の種 %d セルからの逆距離加重(冪%.1f・半径%.0fm)で **%d セル**を埋め戻した"
               % (len(src), ip["power"], ip["radius"], n3))

    # ⑥ 変えたセルとその周り1セルだけを平滑化
    sm = spec["smooth"]
    zone = set()
    for (ix, iz) in target:
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                q = (ix + dx, iz + dz)
                if q in inside and not masked(*inside[q]):
                    zone.add(q)
    # ⛔ **平滑化は掘削跡の外を作り直す道具ではない。** `zone` は target ±1 なので
    #   掘削跡でないセルを必ず含む。そこは**継ぎ目を撫でるぶんだけ**動かしてよく、
    #   `haloMax` を超えて動かすなら、それは平滑化ではなく無宣言の造成である
    #   (2026-08-25 検図13巡 中-5: 非対象 66 セルが最大 +1.03m 動いていた)。
    hal = sm.get("haloMax", 0.30)
    before = {(ix, iz): h[iz][ix] for (ix, iz) in zone}
    for _ in range(sm["passes"]):
        h2 = [row[:] for row in h]
        for (ix, iz) in zone:
            n = [h[iz + dz][ix + dx] for dx in (-1, 0, 1) for dz in (-1, 0, 1)
                 if 0 <= iz + dz < nz and 0 <= ix + dx < nx and h[iz + dz][ix + dx] is not None]
            if n:
                h2[iz][ix] = round(sum(n) / len(n), 2)
        h = h2
    clip = 0
    worst = 0.0
    for (ix, iz) in zone:
        if (ix, iz) in target or before[(ix, iz)] is None or h[iz][ix] is None:
            continue
        dv = h[iz][ix] - before[(ix, iz)]
        worst = max(worst, abs(dv))
        if abs(dv) > hal:
            h[iz][ix] = round(before[(ix, iz)] + math.copysign(hal, dv), 2)
            clip += 1
    log.append("⑥ 境目を %d 回平滑化(対象 %d セル)— 掘削跡でない %d セルを "
               "上限 %.2fm で頭打ちにした(素の最大 %.2fm)"
               % (sm["passes"], len(zone), clip, hal, worst))
    return h, log


def build(check=False):
    seed = load(BASE)
    d = load(SASHIZU)
    spec = load(RECON)
    poly = d["polygon"]
    h, log = reconstruct(seed, poly, spec)
    for line in log:
        print("   " + line)

    diff = [(abs(h[iz][ix] - seed["h"][iz][ix]), seed["x0"] + seed["step"] * ix,
             seed["z0"] + seed["step"] * iz)
            for iz in range(seed["nz"]) for ix in range(seed["nx"])
            if h[iz][ix] is not None and seed["h"][iz][ix] is not None
            and abs(h[iz][ix] - seed["h"][iz][ix]) > 1e-9]
    out_ = [q for q in diff if not in_poly(poly, q[1], q[2])]
    print("   変わったセル %d / 最大 %.2fm / **区画の外へ滲んだセル %d**"
          % (len(diff), max((q[0] for q in diff), default=0.0), len(out_)))
    if out_:
        raise SystemExit("⛔ 復元が区画の外へ滲んでいる — 隣家の地盤を動かしてはならない")

    world = dict(seed)
    world["h"] = h
    # 触ったセルの外接箱を**実測で**記録する。検査が推測の余白を持たなくて済む
    if diff:
        world["_reconBox"] = [round(min(q[1] for q in diff), 1), round(max(q[1] for q in diff), 1),
                              round(min(q[2] for q in diff), 1), round(max(q[2] for q in diff), 1)]
        world["_reconCells"] = len(diff)
    world["_"] = ("**江戸期の復元地盤**(世界2m格子)。区画の中=正本+復元 / 外=正本そのもの。"
                  "手順は `doi_edo_recon.json`、種地は `base_dem.json`。"
                  "⛔ **手で編集しない。** 生成器 `Tools/Sashizu/build_doi_edo_dem.py` が毎回作り直す。")

    # 回転間グリッドへ再標本(区画の外は null)
    cur = load(os.path.join(DOC, "doi_terrain.json"))
    # 回転の基底は指図の生成器が持つ(二重に実装しない)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_doi_sashizu as BD
    gr = BD.RGrid(d)
    rot = {"_": ("**江戸期の復元地盤**を回転間グリッド shukaku の1間格子へ。区画の外は null。"
                 "⛔ 手で編集しない — `build_doi_edo_dem.py` が作る。"),
           "grid": "shukaku", "u0": cur["u0"], "v0": cur["v0"], "step": cur["step"],
           "nu": cur["nu"], "nv": cur["nv"], "h": []}
    for iv in range(cur["nv"]):
        row = []
        v = cur["v0"] + iv * cur["step"]
        for iu in range(cur["nu"]):
            u = cur["u0"] + iu * cur["step"]
            x, z = gr.W(u, v)
            row.append(None if cur["h"][iv][iu] is None else
                       (lambda q: None if q is None else round(q, 2))(bilinear(world, x, z)))
        rot["h"].append(row)

    if check:
        print("   --check: 書かずに終了")
        return
    json.dump(world, open(WORLD, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(rot, open(ROT_EDO, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("   wrote %s / %s" % (os.path.basename(WORLD), os.path.basename(ROT_EDO)))


if __name__ == "__main__":
    build(check="--check" in sys.argv)
