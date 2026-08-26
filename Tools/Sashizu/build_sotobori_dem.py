#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外堀下流の掘り直しの「地盤の部」を起こす。

    python3 Tools/Sashizu/build_sotobori_dem.py          # 書く
    python3 Tools/Sashizu/build_sotobori_dem.py --check  # 書かずに数字だけ出す

読むのは二つだけ。

    docs/Sashizu/sotobori_sashizu.json … 設計値の正典(人が書く。汀線・石垣・工区の規則)
    TerrainBackups/…                   … 地形のスナップショット

書くのは二つ。

    docs/Sashizu/sotobori_dem.json     … 段彩・等高線・切盛の図が読む格子(4m刻み)
    docs/Sashizu/sotobori_terrain.json … 縦断・横断・土量・検査の実測(2m格子で計算)

⛔ **実装(シーン・プレハブ・C#)は読まない。** 図と実装がズレないよう、幾何はすべて
   sotobori_sashizu.json の世界座標から起こす(CLAUDE.md 絶対規則2・指図 README 決めごと6)。

⛔ **Unity の live terrain からは採らない**(CLAUDE.md 絶対規則12)。使うのは

   heightmap_before.bin (tameike_20260826_recarve_pre) … 現況。溜池の掘り直しの直前で、
       外堀の工区はこの掘り直しの手が入っていない
   heightmap_before_reset.bin (terrain_20260822_georef_fix) … 08-22 のリセット直前。
       この堀を 2026-08-10 に掘った形が入っている = 復元の種地
   ref_height.npy … 造成を一切含まない現代の地面。base_dem.json の正本と同じ出自で、
       「種地が他家の造成でない」ことの検算に使う

⚠ TerrainBackups は gitignore で**メインの作業ツリーにしかない**。worktree から回すときは
   `--backups /path/to/edo-unity/TerrainBackups` を渡すこと。
"""
import argparse
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SASHIZU = os.path.join(ROOT, "docs", "Sashizu")
DESIGN = os.path.join(SASHIZU, "sotobori_sashizu.json")
DEM_OUT = os.path.join(SASHIZU, "sotobori_dem.json")
TER_OUT = os.path.join(SASHIZU, "sotobori_terrain.json")

DEM_STEP = 4          # 図版用の格子[m]。計算は地形と同じ 2m で回す
DEM_MARGIN = 30       # 工区の外へ確保する余白[m]
STATION = 10.0        # 縦断の測点の間隔[m]
SEC_OUT = 22.0        # 横断を汀線の外へ延ばす長さ[m]

DEM_DOC = (
    "外堀下流の掘り直しの現況地盤と復元の種地【確度P】。世界座標 %dm 刻み(x0,z0 から)。"
    "h[iz][ix]=標高m。`cur`=現況(2026-08-26 溜池の掘り直し直前のハイトマップ。外堀の工区は無傷)。"
    "`pre`=2026-08-22 の造成リセット直前(この堀を 2026-08-10 に掘った形)。"
    "⛔ 手で編集しない・Unity の live terrain から採り直さない。生成器 Tools/Sashizu/build_sotobori_dem.py"
)
TER_DOC = (
    "外堀下流の掘り直しの実測【確度P】。縦断・横断・土量・検査の値で、"
    "**設計値ではない**(設計値は sotobori_sashizu.json)。2m 格子で計算した。"
    "生成器 Tools/Sashizu/build_sotobori_dem.py"
)


# ---------------------------------------------------------------- 幾何(指図の設計値から起こす)
def seg_dist(np, px, pz, poly):
    d = np.full(px.shape, 1e9)
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        dx, dz = x2 - x1, z2 - z1
        l2 = dx * dx + dz * dz
        t = np.clip(((px - x1) * dx + (pz - z1) * dz) / l2, 0, 1)
        d = np.minimum(d, np.hypot(px - (x1 + t * dx), pz - (z1 + t * dz)))
    return d


def in_poly(np, px, pz, poly):
    ins = np.zeros(px.shape, bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        ins ^= ((zi > pz) != (zj > pz)) & (px < (xj - xi) * (pz - zi) / ((zj - zi) + 1e-12) + xi)
        j = i
    return ins


def in_poly_pt(x, z, poly):
    ins = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if ((zi > z) != (zj > z)) and (x < (xj - xi) * (z - zi) / ((zj - zi) + 1e-12) + xi):
            ins = not ins
        j = i
    return ins


def signed_dist(p, polys):
    """汀線からの符号つき距離[m]。水面の内側を負にする。"""
    d = 1e9
    for w in polys:
        for e, f in zip(w, w[1:] + w[:1]):
            dx, dz = f[0] - e[0], f[1] - e[1]
            t = max(0.0, min(1.0, ((p[0] - e[0]) * dx + (p[1] - e[1]) * dz) / (dx * dx + dz * dz)))
            d = min(d, math.hypot(p[0] - (e[0] + t * dx), p[1] - (e[1] + t * dz)))
    return -d if any(in_poly_pt(p[0], p[1], w) for w in polys) else d


def side_of(p, a, b):
    """線分 a→b に対する p の符号つき横距離。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dz)
    return ((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / ln


def cross_width(pt, nrm, ne):
    """汀線上の点 pt から法線 nrm 方向へ、対岸の汀線 ne までの距離。"""
    lo, hi = 0.0, 90.0
    f = lambda w: side_of((pt[0] + w * nrm[0], pt[1] + w * nrm[1]), ne[0], ne[1])
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def coping_at(d, x, z, side):
    """石垣の天端。run の端点と天端の推移から内挿する(実装は読まない)。"""
    best, bd = None, 1e9
    for r in d["ishigaki"]["runs"]:
        if side not in r["side"]:
            continue
        a, b = r["p0"], r["p1"]
        dx, dz = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dz * dz
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / l2))
        q = (a[0] + t * dx, a[1] + t * dz)
        dd = math.hypot(x - q[0], z - q[1])
        if dd < bd:
            bd, best = dd, r["copingFrom"] + (r["copingTo"] - r["copingFrom"]) * t
    return best, bd


# ---------------------------------------------------------------- 地形
def load_terrain(backups):
    import numpy as np
    gf = os.path.join(backups, "terrain_20260822_georef_fix")
    tf = os.path.join(backups, "tameike_20260826_recarve_pre")
    meta = json.load(open(os.path.join(gf, "meta.json")))
    r = meta["R"]
    rd = lambda p: np.fromfile(p, dtype=np.float32).reshape(r, r).astype(float)
    return dict(meta=meta,
                cur=rd(os.path.join(tf, "heightmap_before.bin")),
                pre=rd(os.path.join(gf, "heightmap_before_reset.bin")),
                nat=np.load(os.path.join(gf, "ref_height.npy")).astype(float))


def design_surface(np, d, cur, pre, ins, dist, step, PX, PZ):
    """指図 works.rule ①〜④ をそのまま実装した設計面。"""
    w = d["works"]
    band = (~ins) & (dist <= w["outerWidth"])
    t = np.clip((dist - w["featherFrom"]) / (w["outerWidth"] - w["featherFrom"]), 0, 1)
    des = np.where(band, pre * (1 - t) + cur * t, cur)     # ②③
    des = np.where(ins, w["floor"], des)                    # ①
    for q in w.get("patches", []):                          # ②' 附則(局所の盛り)
        r = q["rect"]
        sel = (band & (PX >= r[0]) & (PX <= r[1]) & (PZ >= r[2]) & (PZ <= r[3])
               & (dist >= q["minDist"]) & (pre < q["srcBelow"]))
        des = np.where(sel, q["to"], des)
    fea = band & (dist > w["featherFrom"])                  # ④ 摺り付け帯だけ 45°
    for _ in range(80):
        lim = np.minimum(np.minimum(np.roll(des, 1, 0), np.roll(des, -1, 0)),
                         np.minimum(np.roll(des, 1, 1), np.roll(des, -1, 1))) + step
        new = np.where(fea, np.minimum(des, lim), des)
        if np.allclose(new, des):
            break
        des = new
    return des, band


# ---------------------------------------------------------------- 書き出し
def fmt(v, nd):
    s = ("%%.%df" % nd) % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def write_dem(path, head, layers, nd):
    body = "{\n \"_\": " + json.dumps(head["_"], ensure_ascii=False) + ",\n"
    body += (' "x0": %d, "z0": %d, "step": %d, "nx": %d, "nz": %d,\n'
             % (head["x0"], head["z0"], head["step"], head["nx"], head["nz"]))
    for k, (grid, doc) in layers.items():
        rows = ",\n  ".join("[" + ",".join(fmt(v, nd) for v in row) + "]" for row in grid)
        body += ' "%s_": %s,\n "%s": [\n  %s\n ],\n' % (k, json.dumps(doc, ensure_ascii=False), k, rows)
    body = body.rstrip(",\n") + "\n}\n"
    open(path, "w", encoding="utf-8").write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backups", default=os.path.join(ROOT, "TerrainBackups"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    import numpy as np

    d = json.load(open(DESIGN, encoding="utf-8"))
    polys = [w["outline"] for w in d["water"]]
    T = load_terrain(args.backups)
    meta = T["meta"]
    px, pz, sp = meta["posX"], meta["posZ"], meta["spacing"]

    # ---- 計算格子(地形と同じ 2m)。工区+余白の外接矩形へ丸める
    xs = [p[0] for q in polys for p in q]
    zs = [p[1] for q in polys for p in q]
    m = d["works"]["outerWidth"] + DEM_MARGIN
    x0 = math.floor((min(xs) - m) / DEM_STEP) * DEM_STEP
    x1 = math.ceil((max(xs) + m) / DEM_STEP) * DEM_STEP
    z0 = math.floor((min(zs) - m) / DEM_STEP) * DEM_STEP
    z1 = math.ceil((max(zs) + m) / DEM_STEP) * DEM_STEP
    c0, r0 = int(round((x0 - px) / sp)), int(round((z0 - pz) / sp))
    nx2, nz2 = int((x1 - x0) / sp) + 1, int((z1 - z0) / sp) + 1
    X = x0 + np.arange(nx2) * sp
    Z = z0 + np.arange(nz2) * sp
    PX, PZ = np.meshgrid(X, Z)
    cut = lambda A: A[r0:r0 + nz2, c0:c0 + nx2]
    CUR, PRE, NAT = cut(T["cur"]), cut(T["pre"]), cut(T["nat"])

    ins = np.zeros(PX.shape, bool)
    dist = np.full(PX.shape, 1e9)
    for q in polys:
        ins |= in_poly(np, PX, PZ, q)
        dist = np.minimum(dist, seg_dist(np, PX, PZ, q))
    des, band = design_surface(np, d, CUR, PRE, ins, dist, sp, PX, PZ)
    work = ins | band
    dz = des - CUR
    cell = sp * sp
    vol_cut = float(np.clip(-dz, 0, None).sum() * cell)
    vol_fill = float(np.clip(dz, 0, None).sum() * cell)
    wy = d["water"][0]["waterY"]

    surv = work & (np.abs(CUR - NAT) > 0.3)
    ter = {
        "_": TER_DOC,
        "grid": {"x0": x0, "z0": z0, "step": sp, "nx": nx2, "nz": nz2},
        "volumes": {
            "workAreaHa": round(float(work.sum() * cell / 1e4), 2),
            "waterAreaHa": round(float(ins.sum() * cell / 1e4), 2),
            "bankAreaHa": round(float(band.sum() * cell / 1e4), 2),
            "cut_m3": round(vol_cut), "fill_m3": round(vol_fill),
            "net_m3": round(vol_cut - vol_fill),
            "maxCut_m": round(float(np.clip(-dz, 0, None).max()), 2),
            "maxFill_m": round(float(np.clip(dz, 0, None).max()), 2),
            "spillCells": int(((~work) & (np.abs(dz) > 0.01)).sum()),
        },
        "submerged": {
            "beforePct": round(float(100 * (CUR[ins] < wy).mean()), 1),
            "afterPct": round(float(100 * (des[ins] < wy).mean()), 1),
            "floorMin": round(float(des[ins].min()), 2),
            "floorMax": round(float(des[ins].max()), 2),
        },
        "provenance": {
            "survivingGradingCells": int(surv.sum()),
            "survivingGradingBox": ([round(float(PX[surv].min())), round(float(PX[surv].max())),
                                     round(float(PZ[surv].min())), round(float(PZ[surv].max()))]
                                    if surv.sum() else []),
            "survivingGradingMaxPreCurDiff": (round(float(np.abs(PRE - CUR)[surv].max()), 2)
                                              if surv.sum() else 0.0),
        },
    }

    def samp(A, x, z):
        fx, fz = (x - x0) / sp, (z - z0) / sp
        i = int(np.clip(fx, 0, nx2 - 2))
        j = int(np.clip(fz, 0, nz2 - 2))
        tx, tz = fx - i, fz - j
        return float(A[j, i] * (1 - tx) * (1 - tz) + A[j, i + 1] * tx * (1 - tz)
                     + A[j + 1, i] * (1 - tx) * tz + A[j + 1, i + 1] * tx * tz)

    # ---- 縦断
    prof, ch = [], 0.0
    frames = []
    for seg in d["reach"]["segments"]:
        sw, ne = seg["sw"], seg["ne"]
        ln = math.hypot(sw[1][0] - sw[0][0], sw[1][1] - sw[0][1])
        u = ((sw[1][0] - sw[0][0]) / ln, (sw[1][1] - sw[0][1]) / ln)
        n = (-u[1], u[0])
        if side_of(ne[0], sw[0], sw[1]) * side_of((sw[0][0] + n[0], sw[0][1] + n[1]), sw[0], sw[1]) < 0:
            n = (-n[0], -n[1])
        frames.append((seg["body"], sw, ne, u, n, ln, ch))
        s = 0.0
        while s <= ln + 1e-6:
            p = (sw[0][0] + s * u[0], sw[0][1] + s * u[1])
            w = cross_width(p, n, ne)
            if w:
                q = (p[0] + w * n[0], p[1] + w * n[1])
                cs, _ = coping_at(d, p[0] - 4.81 * n[0], p[1] - 4.81 * n[1], "郭外")
                cn, _ = coping_at(d, q[0] + 4.81 * n[0], q[1] + 4.81 * n[1], "郭内")
                prof.append([seg["body"], round(ch + s, 1), round(p[0], 2), round(p[1], 2), round(w, 2),
                             round(samp(CUR, p[0] - 8 * n[0], p[1] - 8 * n[1]), 2),
                             round(samp(CUR, q[0] + 8 * n[0], q[1] + 8 * n[1]), 2),
                             round(cs, 2), round(cn, 2)])
            s += STATION
        ch += ln
    ter["reachLength"] = round(ch, 1)
    ter["profileCols"] = ["body", "chainage", "swX", "swZ", "width", "curSW", "curNE", "copingSW", "copingNE"]
    ter["profile"] = prof

    # ---- 横断
    secs = []
    for s in d["sections"]["list"]:
        fr = [f for f in frames if f[0] == s["body"]][0]
        _, sw, ne, u, n, ln, base = fr
        loc = s["chainage"] - base
        p = (sw[0][0] + loc * u[0], sw[0][1] + loc * u[1])
        w = cross_width(p, n, ne)
        row = []
        t = -SEC_OUT
        while t <= w + SEC_OUT + 1e-6:
            x, z = p[0] + t * n[0], p[1] + t * n[1]
            row.append([round(t, 1), round(samp(CUR, x, z), 2), round(samp(des, x, z), 2)])
            t += 1.0
        cs, _ = coping_at(d, p[0] - 4.81 * n[0], p[1] - 4.81 * n[1], "郭外")
        cn, _ = coping_at(d, p[0] + (w + 4.81) * n[0], p[1] + (w + 4.81) * n[1], "郭内")
        secs.append({"mark": s["mark"], "body": s["body"], "chainage": s["chainage"],
                     "p": [round(p[0], 2), round(p[1], 2)], "nrm": [round(n[0], 5), round(n[1], 5)],
                     "width": round(w, 2), "copingSW": round(cs, 2), "copingNE": round(cn, 2),
                     "cols": ["t", "cur", "design"], "row": row})
    ter["sections"] = secs

    # ---- 石垣の背面の検査(run 線から起こす。実装は読まない)
    back = []
    for r in d["ishigaki"]["runs"]:
        a, b = r["p0"], r["p1"]
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        u = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
        n = (-u[1], u[0])
        mid = (a[0] + 0.5 * (b[0] - a[0]), a[1] + 0.5 * (b[1] - a[1]))
        # +n = 陸側。汀線からの**符号つき**距離(内側を負)が大きい方を陸と採る。
        # 「内か外か」だけで決めると、入隅の短い折れ(NE3f)で両側とも外になり倒れる。
        if signed_dist((mid[0] + 6 * n[0], mid[1] + 6 * n[1]), polys) \
                < signed_dist((mid[0] - 6 * n[0], mid[1] - 6 * n[1]), polys):
            n = (-n[0], -n[1])
        g, c = [], []
        s = 0.0
        while s <= ln + 1e-6:
            p = (a[0] + s * u[0], a[1] + s * u[1])
            g.append(samp(des, p[0] + 4 * n[0], p[1] + 4 * n[1]))
            c.append(r["copingFrom"] + (r["copingTo"] - r["copingFrom"]) * (s / ln))
            s += 4.0
        gap = [ci - gi for ci, gi in zip(c, g)]
        gap.sort()
        back.append({"line": r["line"], "n": len(gap),
                     "median": round(gap[len(gap) // 2], 2),
                     "min": round(gap[0], 2), "max": round(gap[-1], 2)})
    ter["ishigakiBack"] = back

    # ---- 図版用の 4m 格子
    kx = DEM_STEP // sp
    sub = lambda A: [[round(float(v), 1) for v in row[::kx]] for row in A[::kx]]
    head = {"_": DEM_DOC % DEM_STEP, "x0": x0, "z0": z0, "step": DEM_STEP,
            "nx": len(X[::kx]), "nz": len(Z[::kx])}
    layers = {"cur": (sub(CUR), "現況(2026-08-26 溜池の掘り直し直前)。外堀の工区はこの掘り直しの手が入っていない"),
              "pre": (sub(PRE), "2026-08-22 の造成リセット直前 = 復元の種地(2026-08-10 に掘った形)")}

    v = ter["volumes"]
    print("工区 %.2f ha(汀線内 %.2f / 岸の帯 %.2f) 距離程 %.1f m"
          % (v["workAreaHa"], v["waterAreaHa"], v["bankAreaHa"], ter["reachLength"]))
    print("掘削 %s m3(最大 %.2f m) / 盛土 %s m3(最大 %.2f m) / 差引 %s m3"
          % (f"{v['cut_m3']:,}", v["maxCut_m"], f"{v['fill_m3']:,}", v["maxFill_m"], f"{v['net_m3']:,}"))
    print("水没率 %.1f%% → %.1f%% / 工区の外へ出た変更セル %d"
          % (ter["submerged"]["beforePct"], ter["submerged"]["afterPct"], v["spillCells"]))
    print("石垣の背面(天端−地盤)の中央値: " + " ".join("%s %+.2f" % (b["line"], b["median"]) for b in back))
    if args.check:
        return
    write_dem(DEM_OUT, head, layers, 1)
    json.dump(ter, open(TER_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for p in (DEM_OUT, TER_OUT):
        print("書いた %s (%.0f KB)" % (os.path.relpath(p, ROOT), os.path.getsize(p) / 1024))


if __name__ == "__main__":
    main()
