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
    "`nat`=造成を一切含まない現代の地面(base_dem.json の正本と同じ出自)。"
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


def side_offset(d, body, side):
    """汀線(=石垣の見え面)から run 線(ピボット線)までの距離[m]。石垣の躯体の厚みに等しい。

    ⭐ 2026-08-30 に 00002/00003 も face 基準へ揃えたので、全 run で ishigaki.faceToPivot で一定。
    """
    t = d["ishigaki"].get("faceToPivot", 4.80)
    rs = [r for r in d["ishigaki"]["runs"] if r.get("body") == body and side in r["side"]]
    if not rs:
        return t
    return max(rs, key=lambda r: r["n"]).get("offset", t)


def coping_at(d, x, z, side, body=None):
    """石垣の天端。run の端点と天端の推移から内挿する(実装は読まない)。"""
    best, bd = None, 1e9
    for r in d["ishigaki"]["runs"]:
        if side not in r["side"]:
            continue
        if body and r.get("body") != body:
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


def design_surface(np, d, cur, pre, ins, dist, floor, keep_out, coping, step, PX, PZ):
    """指図 works.rule ①〜④ をそのまま実装した設計面。

    `ins` / `dist` / `floor` は **works=true の水面だけ**から作ること。
    00001 は disposition=調査のみなので、ここへ渡さなければ1セルも動かない(規則⑤)。
    """
    w = d["works"]
    band = (~ins) & (dist <= w["outerWidth"]) & (~keep_out)
    t = np.clip((dist - w["featherFrom"]) / (w["outerWidth"] - w["featherFrom"]), 0, 1)
    # ② 岸は**最寄りの石垣の天端 − bankBelowCoping**(2026-08-30 ユーザー裁定A・EDO-0064)。
    #    ⛔ 汀線から faceToPivot(躯体の厚み)までは石垣そのものが占める帯なので触らず、種地のまま。
    tw = d["ishigaki"].get("faceToPivot", 4.80)
    bank = coping - w.get("bankBelowCoping", 0.20)
    base = np.where(dist >= tw, bank, pre)                  # ②
    des = np.where(band, base * (1 - t) + cur * t, cur)     # ②③
    des = np.where(ins, floor, des)                         # ①
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
    bodies = d["water"]
    polys = [w["outline"] for w in bodies]                       # 全水面(図と調査)
    wpolys = [w["outline"] for w in bodies if w.get("works")]    # 掘り直す水面だけ
    byid = {w["id"]: w for w in bodies}
    T = load_terrain(args.backups)
    meta = T["meta"]
    px, pz, sp = meta["posX"], meta["posZ"], meta["spacing"]

    # ---- 計算格子(地形と同じ 2m)。全水面 + 工区 + 余白の外接矩形へ丸める
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

    # 工区の判定は works=true の水面だけから作る(規則⑤)
    ins = np.zeros(PX.shape, bool)
    dist = np.full(PX.shape, 1e9)
    floor = np.zeros(PX.shape)
    for w in bodies:
        if not w.get("works"):
            continue
        m1 = in_poly(np, PX, PZ, w["outline"])
        ins |= m1
        floor = np.where(m1, w["floor"], floor)
        dist = np.minimum(dist, seg_dist(np, PX, PZ, w["outline"]))
    # 岸の帯から外す領域(規則⑤の実装。⚠ 掘る水面の内側は外さない — 土橋の水路は掘る)
    ko = np.zeros(PX.shape, bool)
    kw = d["works"].get("keepOut", {})
    for b in bodies:
        if b.get("works"):
            continue
        ko |= in_poly(np, PX, PZ, b["outline"])
        ko |= seg_dist(np, PX, PZ, b["outline"]) <= kw.get("otherWaterBank", 0.0)
    for q in kw.get("rects", []):
        r = q["rect"]
        ko |= (PX >= r[0]) & (PX <= r[1]) & (PZ >= r[2]) & (PZ <= r[3])
    ko &= ~ins
    # 最寄りの石垣の天端の場(掘る水面の run だけ。規則②が読む)
    COP = np.full(PX.shape, 0.0)
    bdd = np.full(PX.shape, 1e9)
    for r in d["ishigaki"]["runs"]:
        if not byid[r["body"]].get("works"):
            continue
        a, b2 = r["p0"], r["p1"]
        dx, dz2 = b2[0] - a[0], b2[1] - a[1]
        l2 = dx * dx + dz2 * dz2
        t = np.clip(((PX - a[0]) * dx + (PZ - a[1]) * dz2) / l2, 0, 1)
        dd = np.hypot(PX - (a[0] + t * dx), PZ - (a[1] + t * dz2))
        cp = r["copingFrom"] + (r["copingTo"] - r["copingFrom"]) * t
        sel = dd < bdd
        bdd = np.where(sel, dd, bdd)
        COP = np.where(sel, cp, COP)
    des, band = design_surface(np, d, CUR, PRE, ins, dist, floor, ko, COP, sp, PX, PZ)
    work = ins | band
    dz = des - CUR
    cell = sp * sp
    vol_cut = float(np.clip(-dz, 0, None).sum() * cell)
    vol_fill = float(np.clip(dz, 0, None).sum() * cell)

    # ⚠ 汀線の外に水面下の床が残るか。⭐ 裁定A(②が天端基準)以降、残りうるのは
    #    汀線から faceToPivot まで(=石垣の躯体の下)だけになる。
    #    checks.overshoot が「面積を記録する」と宣言していたのに測っていなかった(2026-08-28 検図 高-7)。
    wy0 = [b["waterY"] for b in bodies if b.get("works")][0]
    ovs = band & (des < wy0 - 0.1)
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
            "keepOutCells": int((ko & (np.abs(dz) > 0.01)).sum()),
            "overshoot_m2": int(ovs.sum() * cell),
            "overshootMaxOutside_m": (round(float(dist[ovs].max()), 1) if ovs.sum() else 0.0),
            "overshootMedianOutside_m": (round(float(np.median(dist[ovs])), 1) if ovs.sum() else 0.0),
            "keepOutHa": round(float(ko.sum() * cell / 1e4), 2),
        },
        "provenance": {
            "survivingGradingCells": int(surv.sum()),
            "survSamePreCurPct": (round(float(100 * (np.abs(PRE - CUR)[surv] <= 0.05).mean()), 1)
                                  if surv.sum() else 100.0),
            "survMaxPreCurDiff": (round(float(np.abs(PRE - CUR)[surv].max()), 2) if surv.sum() else 0.0),
            "survMovedInBandCells": int((surv & (np.abs(PRE - CUR) > 0.05) & band
                                         & (np.abs(dz) > 0.01)).sum()),
            "survMovedInWaterCells": int((surv & (np.abs(PRE - CUR) > 0.05) & ins
                                          & (np.abs(dz) > 0.01)).sum()),
            "survivingGradingBox": ([round(float(PX[surv].min())), round(float(PX[surv].max())),
                                     round(float(PZ[surv].min())), round(float(PZ[surv].max()))]
                                    if surv.sum() else []),
        },
    }

    # ---- 水面ごとの現況調査(00001 はこれが成果。掘る水面は掘り直しの前後)
    survey = []
    for w in bodies:
        m1 = in_poly(np, PX, PZ, w["outline"])
        fl, wy = w["floor"], w["waterY"]
        row = {"id": w["id"], "works": bool(w.get("works")),
               "areaHa": round(float(m1.sum() * cell / 1e4), 2),
               "waterY": wy, "floor": fl,
               "curSubmergedPct": round(float(100 * (CUR[m1] < wy).mean()), 1),
               "curOnFloorPct": round(float(100 * (np.abs(CUR[m1] - fl) < 0.2).mean()), 1),
               "curVsPreSamePct": round(float(100 * (np.abs(PRE - CUR)[m1] <= 0.05).mean()), 1),
               "curMedian": round(float(np.median(CUR[m1])), 2)}
        if w.get("works"):
            row["designSubmergedPct"] = round(float(100 * (des[m1] < wy).mean()), 1)
            row["designFloorMin"] = round(float(des[m1].min()), 2)
            row["designFloorMax"] = round(float(des[m1].max()), 2)
        else:
            # 調査のみ — 水面より上に出ている所を「水面より何m高いか」で測る。
            # ⚠ 初版は「汀線から4m以内か」で測っていたが、汀線が岸へ乗っていると
            #    縁に見えて実は 3m 以上の土手になる(2026-08-26 検図)。物差しを高さへ替えた。
            hi = m1 & (CUR > wy)
            row["dryCells"] = int(hi.sum())
            row["dryHa"] = round(float(hi.sum() * cell / 1e4), 3)
            row["dryOver1mCells"] = int((hi & (CUR > wy + 1.0)).sum())
            row["dryMaxOver_m"] = round(float((CUR[hi] - wy).max()), 2) if hi.sum() else 0.0
            dd = seg_dist(np, PX, PZ, w["outline"])
            row["dryMaxInsideFromEdge_m"] = round(float(dd[hi].max()), 1) if hi.sum() else 0.0
            for zn in w.get("dryZones", []):
                sel = hi & (PX >= zn["x"][0]) & (PX < zn["x"][1])
                row.setdefault("dryZoneRows", []).append(
                    {"name": zn["name"], "cells": int(sel.sum()),
                     "m2": int(sel.sum() * cell),
                     "over1m_m2": int((sel & (CUR > wy + 1.0)).sum() * cell),
                     "maxOver_m": round(float((CUR[sel] - wy).max()), 2) if sel.sum() else 0.0})
        survey.append(row)
    ter["survey"] = survey

    def samp(A, x, z):
        fx, fz = (x - x0) / sp, (z - z0) / sp
        i = int(np.clip(fx, 0, nx2 - 2))
        j = int(np.clip(fz, 0, nz2 - 2))
        tx, tz = fx - i, fz - j
        return float(A[j, i] * (1 - tx) * (1 - tz) + A[j, i + 1] * tx * (1 - tz)
                     + A[j + 1, i] * (1 - tx) * tz + A[j + 1, i + 1] * tx * tz)



    # ---- 縦断(堰の直下 = 0.0m)
    prof, ch = [], 0.0
    frames, gaps = [], []
    prev_end = None
    for gi, seg in enumerate(d["reach"]["segments"]):
        b = byid[seg["body"]]
        sw, ne = seg["sw"], seg["ne"]
        if prev_end is not None:
            # 区間と区間の隙間(土橋・継ぎ目の岸)。距離程を欠かさないよう実長を足す
            gl = math.hypot(sw[0][0] - prev_end[0], sw[0][1] - prev_end[1])
            gspec = next((g for g in d["reach"].get("gaps", [])
                          if g["after"] == d["reach"]["segments"][gi - 1]["body"]), {})
            gaps.append({"name": gspec.get("name", "—"), "from": round(ch, 1),
                         "to": round(ch + gl, 1), "length": round(gl, 1),
                         "note": gspec.get("note", "")})
            ch += gl
        prev_end = sw[1]
        ln = math.hypot(sw[1][0] - sw[0][0], sw[1][1] - sw[0][1])
        u = ((sw[1][0] - sw[0][0]) / ln, (sw[1][1] - sw[0][1]) / ln)
        n = (-u[1], u[0])
        if side_of(ne[0], sw[0], sw[1]) * side_of((sw[0][0] + n[0], sw[0][1] + n[1]), sw[0], sw[1]) < 0:
            n = (-n[0], -n[1])
        frames.append((seg["body"], sw, ne, u, n, ln, ch))
        s = 0.0
        while s <= ln + 1e-6:
            p = (sw[0][0] + s * u[0], sw[0][1] + s * u[1])
            wd = cross_width(p, n, ne)
            if wd:
                q = (p[0] + wd * n[0], p[1] + wd * n[1])
                ow, oe = side_offset(d, seg["body"], "郭外"), side_offset(d, seg["body"], "郭内")
                cs, _ = coping_at(d, p[0] - ow * n[0], p[1] - ow * n[1], "郭外", seg["body"])
                cn, _ = coping_at(d, q[0] + oe * n[0], q[1] + oe * n[1], "郭内", seg["body"])
                # 岸の標本は石垣の背後で採る(汀線から一定距離だと、石垣が汀線から
                # 10.7m 外に据わる 00001 で堀の中を拾ってしまう)
                bw, be = ow + 4.0, oe + 4.0
                prof.append([seg["body"], round(ch + s, 1), round(p[0], 2), round(p[1], 2), round(wd, 2),
                             round(samp(CUR, p[0] - bw * n[0], p[1] - bw * n[1]), 2),
                             round(samp(CUR, q[0] + be * n[0], q[1] + be * n[1]), 2),
                             round(cs, 2) if cs else None, round(cn, 2) if cn else None,
                             b["waterY"], b["floor"]])
            s += STATION
        ch += ln
    ter["reachLength"] = round(ch, 1)
    ter["gaps"] = gaps
    ter["profileCols"] = ["body", "chainage", "swX", "swZ", "width", "curSW", "curNE",
                          "copingSW", "copingNE", "waterY", "floor"]
    ter["profile"] = prof

    # ---- 横断
    secs = []
    for s in d["sections"]["list"]:
        fr = [f for f in frames if f[0] == s["body"]][0]
        _, sw, ne, u, n, ln, base = fr
        b = byid[s["body"]]
        loc = s["chainage"] - base
        p = (sw[0][0] + loc * u[0], sw[0][1] + loc * u[1])
        wd = cross_width(p, n, ne)
        row = []
        t = -SEC_OUT
        while t <= wd + SEC_OUT + 1e-6:
            x, z = p[0] + t * n[0], p[1] + t * n[1]
            row.append([round(t, 1), round(samp(CUR, x, z), 2), round(samp(des, x, z), 2)])
            t += 1.0
        ow, oe = side_offset(d, s["body"], "郭外"), side_offset(d, s["body"], "郭内")
        cs, _ = coping_at(d, p[0] - ow * n[0], p[1] - ow * n[1], "郭外", s["body"])
        cn, _ = coping_at(d, p[0] + (wd + oe) * n[0], p[1] + (wd + oe) * n[1], "郭内", s["body"])
        wl = [r[0] for r in row if r[2] < b["waterY"] - 0.05]
        secs.append({"mark": s["mark"], "body": s["body"], "chainage": s["chainage"],
                     "trueWaterlineFrom": round(min(wl), 2) if wl else None,
                     "trueWaterlineTo": round(max(wl), 2) if wl else None,
                     "trueWaterlineWidth": round(max(wl) - min(wl), 2) if wl else None,
                     "works": bool(b.get("works")),
                     "waterY": b["waterY"], "floor": b["floor"],
                     "p": [round(p[0], 2), round(p[1], 2)], "nrm": [round(n[0], 5), round(n[1], 5)],
                     "width": round(wd, 2),
                     "offsetSW": round(ow, 2), "offsetNE": round(oe, 2),
                     "copingSW": round(cs, 2) if cs else None,
                     "copingNE": round(cn, 2) if cn else None,
                     "cols": ["t", "cur", "design"], "row": row})
    ter["sections"] = secs

    # ---- 石垣の背面の検査(run 線から起こす。実装は読まない)
    back = []
    for r in d["ishigaki"]["runs"]:
        a, b2 = r["p0"], r["p1"]
        ln = math.hypot(b2[0] - a[0], b2[1] - a[1])
        u = ((b2[0] - a[0]) / ln, (b2[1] - a[1]) / ln)
        n = (-u[1], u[0])
        mid = (a[0] + 0.5 * (b2[0] - a[0]), a[1] + 0.5 * (b2[1] - a[1]))
        # +n = 陸側。汀線からの**符号つき**距離(内側を負)が大きい方を陸と採る。
        # 「内か外か」だけで決めると、入隅の短い折れ(NE3f)で両側とも外になり倒れる。
        if signed_dist((mid[0] + 6 * n[0], mid[1] + 6 * n[1]), polys) \
                < signed_dist((mid[0] - 6 * n[0], mid[1] - 6 * n[1]), polys):
            n = (-n[0], -n[1])
        # ⚠ 陸側1点だけでは土居の天端の**幅**が出ない(2026-08-26 検図)。2/4/6/8m で採る。
        offs = [2.0, 4.0, 6.0, 8.0]
        acc = {o: [] for o in offs}
        c = []
        s = 0.0
        while s <= ln + 1e-6:
            p = (a[0] + s * u[0], a[1] + s * u[1])
            for o in offs:
                acc[o].append(samp(des, p[0] + o * n[0], p[1] + o * n[1]))
            c.append(r["copingFrom"] + (r["copingTo"] - r["copingFrom"]) * (s / ln))
            s += 4.0
        med = lambda v: sorted(v)[len(v) // 2]
        gap = sorted(ci - gi for ci, gi in zip(c, acc[4.0]))
        back.append({"line": r["line"], "body": r.get("body"),
                     "works": bool(byid[r["body"]].get("works")),
                     "n": len(gap), "median": round(gap[len(gap) // 2], 2),
                     "min": round(gap[0], 2), "max": round(gap[-1], 2),
                     "byOffset": {("%.0f" % o): round(med([ci - gi for ci, gi in zip(c, acc[o])]), 2)
                                  for o in offs}})
    ter["ishigakiBack"] = back

    # ---- 石垣が土に埋まっていないか(run 線そのもので現況/設計の地盤と天端を比べる)
    bur = []
    for r in d["ishigaki"]["runs"]:
        a, b2 = r["p0"], r["p1"]
        ln = math.hypot(b2[0] - a[0], b2[1] - a[1])
        u = ((b2[0] - a[0]) / ln, (b2[1] - a[1]) / ln)
        gc, gd, cp = [], [], []
        s2 = 0.0
        while s2 <= ln + 1e-6:
            p = (a[0] + s2 * u[0], a[1] + s2 * u[1])
            gc.append(samp(CUR, *p))
            gd.append(samp(des, *p))
            cp.append(r["copingFrom"] + (r["copingTo"] - r["copingFrom"]) * (s2 / ln))
            s2 += 4.0
        over = [g - c for g, c in zip(gd, cp)]      # 設計地盤 − 天端。正 = 埋まる
        oc = [g - c for g, c in zip(gc, cp)]
        bur.append({"line": r["line"], "body": r.get("body"), "n": len(over),
                    "curOverCopingMedian": round(sorted(oc)[len(oc) // 2], 2),
                    "designOverCopingMedian": round(sorted(over)[len(over) // 2], 2),
                    "designOverCopingMax": round(max(over), 2),
                    "buriedPct": round(100.0 * sum(1 for v in over if v > 0.3) / len(over), 1)})
    ter["ishigakiBuried"] = bur

    # ---- 図版用の 4m 格子
    kx = DEM_STEP // sp
    sub = lambda A: [[round(float(v), 1) for v in row[::kx]] for row in A[::kx]]
    head = {"_": DEM_DOC % DEM_STEP, "x0": x0, "z0": z0, "step": DEM_STEP,
            "nx": len(X[::kx]), "nz": len(Z[::kx])}
    layers = {"cur": (sub(CUR), "現況(2026-08-26 溜池の掘り直し直前)。外堀の工区はこの掘り直しの手が入っていない"),
              "pre": (sub(PRE), "2026-08-22 の造成リセット直前 = 復元の種地(2026-08-10 に掘った形)"),
              "nat": (sub(NAT), "造成を一切含まない現代の地面。base_dem.json の正本と**同じ出自**"
                                "(ref_height.npy)で、種地の出所の検算(provenance)はこの層と cur の差で判定する。"
                                "⭐ これがあるので、TerrainBackups(gitignore・メインの作業ツリーのみ)が無い"
                                "worktree でも検算を再現できる")}

    v = ter["volumes"]
    print("距離程 %.1f m(堰の直下から)／ 工区 %.2f ha(掘る水面 %.2f / 岸の帯 %.2f)"
          % (ter["reachLength"], v["workAreaHa"], v["waterAreaHa"], v["bankAreaHa"]))
    print("掘削 %s m3(最大 %.2f m) / 盛土 %s m3(最大 %.2f m) / 差引 %s m3"
          % (f"{v['cut_m3']:,}", v["maxCut_m"], f"{v['fill_m3']:,}", v["maxFill_m"], f"{v['net_m3']:,}"))
    print("⚠ 汀線の外に残る水面下の床 %s m2(汀線から中央 %.1fm・最大 %.1fm 外)"
          % (f"{ter['volumes']['overshoot_m2']:,}", ter["volumes"]["overshootMedianOutside_m"],
             ter["volumes"]["overshootMaxOutside_m"]))
    print("工区の外へ出た変更セル %d ／ 凍結域で動いたセル %d(凍結 %.2f ha)"
          % (v["spillCells"], v["keepOutCells"], v["keepOutHa"]))
    pv = ter["provenance"]
    print("種地の検算: 生き残った造成 %d セル / 種地=現況 %.1f%%(最大差 %.2f m) / "
          "不一致で動くのは 帯 %d・水面の中 %d"
          % (pv["survivingGradingCells"], pv["survSamePreCurPct"], pv["survMaxPreCurDiff"],
             pv["survMovedInBandCells"], pv["survMovedInWaterCells"]))
    for r in survey:
        if r["works"]:
            print("  %-15s 掘る  %.2f ha  水没率 %.1f%% → %.1f%%  床 %.2f–%.2f"
                  % (r["id"], r["areaHa"], r["curSubmergedPct"], r["designSubmergedPct"],
                     r["designFloorMin"], r["designFloorMax"]))
        else:
            print("  %-15s 調査  %.2f ha  水没率 %.1f%%  床±0.2m %.1f%%  リセット直前と一致 %.1f%%  "
                  "乾き %.3f ha(水面+1m超 %d セル・最大 +%.2f m・汀線から最大 %.1f m 内側)"
                  % (r["id"], r["areaHa"], r["curSubmergedPct"], r["curOnFloorPct"],
                     r["curVsPreSamePct"], r["dryHa"], r["dryOver1mCells"],
                     r["dryMaxOver_m"], r["dryMaxInsideFromEdge_m"]))
            for z in r.get("dryZoneRows", []):
                print("      %-22s %5d m2(水面+1m超 %5d m2・最大 +%.2f m)"
                      % (z["name"], z["m2"], z["over1m_m2"], z["maxOver_m"]))
    print("石垣の背面(天端−地盤)の中央値: " + " ".join("%s %+.2f" % (b["line"], b["median"]) for b in back))
    bad = [b for b in bur if b["buriedPct"] > 20]
    print("⚠ 天端が設計地盤に埋まる run: " + (" ".join(
        "%s %.0f%%(中央%+.2f)" % (b["line"], b["buriedPct"], b["designOverCopingMedian"]) for b in bad)
        if bad else "なし"))
    if args.check:
        return
    write_dem(DEM_OUT, head, layers, 1)
    # ⭐ 生成器が計算できず**手で記録した実測**は、再生成で消さずに引き継ぐ(U8 の検算など)。
    if os.path.exists(TER_OUT):
        try:
            old = json.load(open(TER_OUT, encoding="utf-8"))
            for k in ("liveCheck2026_0830",):
                if k in old:
                    ter[k] = old[k]
        except Exception as e:
            print("⚠ 既存 %s の手記録を引き継げなかった: %s" % (os.path.basename(TER_OUT), e))
    json.dump(ter, open(TER_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for p in (DEM_OUT, TER_OUT):
        print("書いた %s (%.0f KB)" % (os.path.relpath(p, ROOT), os.path.getsize(p) / 1024))


if __name__ == "__main__":
    main()
