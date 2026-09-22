#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""丹羽左京大夫上屋敷の**江戸期の復元地盤**を起こす。

    python3 Tools/Sashizu/build_niwa_sakyo_recon.py           # 書く(冪等)
    python3 Tools/Sashizu/build_niwa_sakyo_recon.py --check   # 書かずに差分だけ出す

読むもの:
    docs/Sashizu/niwa_sakyo_edo_recon.json … 復元の**手順の仕様**(人が書く。錨と確度つき)
    docs/Sashizu/niwa_sakyo_dem.json       … 種地(現況。build_base_dem.py が正本から切り出す)
    docs/Sashizu/parcels.json              … 区画の正典

書くもの(派生物 — 手で編集しない):
    docs/Sashizu/niwa_sakyo_edo_world.json … 世界2m格子。`h`=A案の面 / `hB`=B案の面

⭐ **錨は明治16年の五千分一東京図の実測**であって現況DEM ではない。
   現況DEM の「造成前」は『当プロジェクトが流した造成の前』の意味で、**近代開発の前ではない**。
⛔ **値を持ち越さない** — 手順を種地に対して毎回実行する(岡部が 2026-08-25 に是正した作法)。
⛔ **復元は区画の中だけ**。区画の外は種地をそのまま返す。
⚠ **崖は南北の直線ではなく折れ線**(2026-09-01 訂正)。算法は `Tools/Sashizu/cliff_polyline.py`。
"""
import json
import math
import os
import sys

from cliff_polyline import Cliff, signed_dist

DOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "docs", "Sashizu"))
SPEC = os.path.join(DOC, "niwa_sakyo_edo_recon.json")
DEMF = os.path.join(DOC, "niwa_sakyo_dem.json")
SASHIZU = os.path.join(DOC, "niwa_sakyo_sashizu.json")
PARCELS = os.path.join(DOC, "parcels.json")
OUT = os.path.join(DOC, "niwa_sakyo_edo_world.json")


def load(p):
    return json.load(open(p, encoding="utf-8"))


def in_poly(P, x, z):
    c = False
    n = len(P)
    for i in range(n):
        (ax, az), (bx, bz) = P[i], P[(i + 1) % n]
        if (az > z) != (bz > z) and x < (bx - ax) * (z - az) / (bz - az) + ax:
            c = not c
    return c


def fit_plane(pts):
    """最小二乗平面 h = a + b·x + c·z。返り値 (a, b, c, 残差の一覧)。"""
    n = len(pts)
    Sx = sum(p[0] for p in pts)
    Sz = sum(p[1] for p in pts)
    Sy = sum(p[2] for p in pts)
    A = [[float(n), Sx, Sz],
         [Sx, sum(p[0] * p[0] for p in pts), sum(p[0] * p[1] for p in pts)],
         [Sz, sum(p[0] * p[1] for p in pts), sum(p[1] * p[1] for p in pts)]]
    B = [Sy, sum(p[0] * p[2] for p in pts), sum(p[1] * p[2] for p in pts)]
    M = [A[i][:] + [B[i]] for i in range(3)]
    for i in range(3):
        q = max(range(i, 3), key=lambda r: abs(M[r][i]))
        M[i], M[q] = M[q], M[i]
        for r in range(3):
            if r != i:
                f = M[r][i] / M[i][i]
                for c2 in range(i, 4):
                    M[r][c2] -= f * M[i][c2]
    a, b, c = [M[i][3] / M[i][i] for i in range(3)]
    res = [(p[3], (a + b * p[0] + c * p[1]) - p[2]) for p in pts]
    return a, b, c, res


def main():
    spec = load(SPEC)
    dem = load(DEMF)
    P = [tuple(q) for q in [p for p in load(PARCELS)["parcels"]
                            if p["id"] == load(SASHIZU)["parcelId"]][0]["pts"]]
    x0, z0, st = dem["x0"], dem["z0"], dem["step"]
    nx, nz = dem["nx"], dem["nz"]
    cur = dem["h"]

    # ---- ① 谷底の平面(錨への最小二乗)。⛔ 係数は毎回当てはめる ----------------
    # ⛔ `y` が null の錨(判読不能)は当てはめに入れない。
    vp = [(a["xz"][0], a["xz"][1], a["y"], a["id"])
          for a in spec["anchors"] if a["use"] == "valley" and a["y"] is not None]
    a0, b0, c0, res = fit_plane(vp)
    grad = math.hypot(b0, c0)

    def valley(x, z):
        return a0 + b0 * x + c0 * z

    # ---- ② 崖(折れ線)。算法は cliff_polyline.py が持つ ------------------------
    CL = Cliff(spec["cliff"])
    PY = spec["plateau"]["y"]

    def full(x, z):
        """A案の面 — ①〜⑤ を区画の全域へ当てる。"""
        return CL.height(x, z, valley, PY)

    def cur_at(x, z):
        fx, fz = (x - x0) / st, (z - z0) / st
        i = min(max(int(math.floor(fx)), 0), nx - 2)
        j = min(max(int(math.floor(fz)), 0), nz - 2)
        tx, tz = fx - i, fz - j
        return ((cur[j][i] * (1 - tx) + cur[j][i + 1] * tx) * (1 - tz)
                + (cur[j + 1][i] * (1 - tx) + cur[j + 1][i + 1] * tx) * tz)

    # ---- B案の台地面 = **現況の台地セルの中央値**(掘削矩形を除く)。⛔ 手で持たない ------
    pv = sorted(cur[j][i] for j in range(nz) for i in range(nx)
                if in_poly(P, x0 + i * st, z0 + j * st)
                and CL.frac(x0 + i * st, z0 + j * st)[0] == "plateau"
                and cur[j][i] >= spec["plateau"]["curMin"])
    PYB = round(pv[len(pv) // 2], 2) if pv else PY

    def fullB(x, z):
        """B案の面 — **台地面だけが違う**。谷底(①)と崖(②)は A案と同じ手順・同じ錨で、
        台地は明治の読みへ落とさず**現況の台地の中央値**で受ける。"""
        return CL.height(x, z, valley, PYB)

    hA = [row[:] for row in cur]
    hB = [row[:] for row in cur]
    inside = [[False] * nx for _ in range(nz)]
    kind = [[None] * nx for _ in range(nz)]
    for j in range(nz):
        z = z0 + j * st
        for i in range(nx):
            x = x0 + i * st
            if not in_poly(P, x, z):
                continue
            inside[j][i] = True
            kind[j][i] = CL.frac(x, z)[0]
            hA[j][i] = full(x, z)
            hB[j][i] = fullB(x, z)

    # ---- 継ぎ目(法尻・法肩)の帯だけ平滑化。区画の外は参照しない -----------------
    sb = spec["smooth"].get("band", 6.0)
    near = [[False] * nx for _ in range(nz)]
    for j in range(nz):
        z = z0 + j * st
        for i in range(nx):
            if not inside[j][i]:
                continue
            x = x0 + i * st
            near[j][i] = (abs(signed_dist(CL.toe, (x, z))) <= sb
                          or abs(signed_dist(CL.crest, (x, z))) <= sb)
    for _ in range(spec["smooth"]["passes"]):
        for H in (hA, hB):
            src = [row[:] for row in H]
            for j in range(nz):
                for i in range(nx):
                    if not (inside[j][i] and near[j][i]):
                        continue
                    ns = [src[j][i]]
                    for dj, di in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        jj, ii = j + dj, i + di
                        if 0 <= jj < nz and 0 <= ii < nx and inside[jj][ii]:
                            ns.append(src[jj][ii])
                    H[j][i] = sum(ns) / len(ns)

    for H in (hA, hB):
        for j in range(nz):
            for i in range(nx):
                H[j][i] = round(H[j][i], 3)

    # ---- 算出値(⛔ 手で持たない) ---------------------------------------------
    ncell = sum(1 for j in range(nz) for i in range(nx) if inside[j][i])
    kn = {k: sum(1 for j in range(nz) for i in range(nx) if kind[j][i] == k)
          for k in ("valley", "cliff", "plateau")}
    dA = [hA[j][i] - cur[j][i] for j in range(nz) for i in range(nx) if inside[j][i]]
    ups = [v for v in dA if v > 0.3]
    dns = [v for v in dA if v < -0.3]
    # 錨での残差(復元面 − 明治の読み)。⛔ `y` が null の錨は残差を出さない。
    anc = []
    for a in spec["anchors"]:
        x, z = a["xz"]
        k, f = CL.frac(x, z)
        anc.append({"id": a["id"], "y": a["y"], "in": in_poly(P, x, z),
                    "zone": k, "f": round(f, 3),
                    "recon": round(full(x, z), 2), "cur": round(cur_at(x, z), 2),
                    "resid": (None if a["y"] is None
                              else round(full(x, z) - a["y"], 2))})
    # 崖の比高と勾配 — 法肩に沿って標本を採り、法尻の折れ線への足で測る
    prof = CL.profiles(lambda x, z: in_poly(P, x, z), ds=4.0)
    cl = [{"crest": [round(c[0], 1), round(c[1], 1)],
           "toe": [round(t[0], 1), round(t[1], 1)],
           "w": round(w, 1),
           "toeY": round(valley(t[0], t[1]), 2), "crestY": PY,
           "rise": round(PY - valley(t[0], t[1]), 2),
           "slope": round(100.0 * (PY - valley(t[0], t[1])) / w, 1)}
          for c, t, w in prof]
    # 区画線の上の段(復元 − 現況)。⚠ 摺り付けないので、そのまま隣家との食い違い
    seam = []
    for j in range(nz):
        z = z0 + j * st
        for i in range(nx):
            if not inside[j][i]:
                continue
            x = x0 + i * st
            if any(not in_poly(P, x + dx, z + dz)
                   for dx, dz in ((-st, 0), (st, 0), (0, -st), (0, st))):
                seam.append((abs(hA[j][i] - cur[j][i]), x, z))
    seam.sort(reverse=True)
    # ---- 「骨格(①②)だけに留める中間案」が図として成立するかの判定 ------------------
    # ⛔ 指図方が先に「成立する/しない」と決めない。**手順を字義どおり当てて数える。**
    #    ③④(台地面と掘削矩形)に手を付けないと、崖の法肩が**現況の掘削矩形の底**に
    #    なる区間が出る。そこでは法肩が法尻より低い=**崖が逆勾配**になる。
    binv = []
    for c, t, w in prof:
        top = cur_at(c[0], c[1])                # ③④ をしない = 法肩は現況のまま
        base = valley(t[0], t[1])               # ① はする = 法尻は復元した谷底
        if top < base:
            binv.append((round(base - top, 2), round(c[0], 1), round(c[1], 1)))
    # ---- 谷底の外挿の距離 -----------------------------------------------------
    # ⛔ **「錨から最遠で約150m」と手で書かない**(2026-09-01 検図 K15 で実測とずれていた)。
    #    区画の中で `valley` 区分のセルについて、最寄りの谷底の錨までの距離を毎回測る。
    vex = None
    for j in range(nz):
        z = z0 + j * st
        for i in range(nx):
            x = x0 + i * st
            if not inside[j][i] or kind[j][i] != "valley":
                continue
            dmin = min(math.hypot(x - q[0], z - q[1]) for q in vp)
            if vex is None or dmin > vex[0]:
                vex = (dmin, x, z)

    # 台地面の感度 — 帯の両端に振ったとき、区画内の Δ(復元 − 現況)の中央値がどう動くか
    sens = {}
    for py in sorted(set(spec["plateau"]["band"] + [PY, PYB])):
        ds = sorted(CL.height(x0 + i * st, z0 + j * st, valley, py) - cur[j][i]
                    for j in range(nz) for i in range(nx) if inside[j][i])
        sens["%.2f" % py] = {"medianDelta": round(ds[len(ds) // 2], 2),
                             "maxUp": round(max(ds), 2), "maxDown": round(min(ds), 2)}

    out = {
        "_": ("**江戸期の復元地盤**(世界座標 2m 格子)。⛔ **これは派生物** — 手で編集せず、"
              "`Tools/Sashizu/build_niwa_sakyo_recon.py` が "
              "`niwa_sakyo_edo_recon.json` の手順を `niwa_sakyo_dem.json` へ実行して書く。"
              "**区画の中 = 明治16年の実測を錨にした復元面 / 区画の外 = 種地(現況)そのもの**。"
              "`h` = A案の面(台地面=明治の読み)/ `hB` = B案の面(台地面=現況の中央値)。"),
        "x0": x0, "z0": z0, "step": st, "nx": nx, "nz": nz,
        "_computed": {
            "_": ("生成器が書く算出値。**手で持たない**(CLAUDE.md 規則4)。"
                  "指図の図と表はここではなく面そのものから毎回算出する — "
                  "ここに置くのは仕様の当てはまり具合を一目で見るため。"),
            "cells": ncell,
            "zoneCells": kn,
            "zonePct": {k: round(100.0 * v / max(ncell, 1), 1) for k, v in kn.items()},
            "valleyExtrap": {
                "maxDist": round(vex[0], 1) if vex else None,
                "at": [round(vex[1], 1), round(vex[2], 1)] if vex else None,
                "anchors": len(vp),
                "_": ("**谷底の外挿の距離。** 区画の中で谷底に分類されたセルのうち、"
                      "最寄りの谷底の錨から最も遠いものまでの距離[m]とその位置。"
                      "⛔ 手で持たない(2026-09-01 検図 K15)。南の脚と北帯の東には"
                      "標高点が1点も無いので、そこは平面という形の仮定に全面的に依存する。")},
            "valleyPlane": {"a": round(a0, 4), "b": round(b0, 6), "c": round(c0, 6),
                            "gradPct": round(grad * 100, 2),
                            "resid": [[q[0], round(q[1], 2)] for q in res],
                            "residMax": round(max(abs(q[1]) for q in res), 2)},
            "cliff": {
                "samples": len(cl),
                "widthMin": min(q["w"] for q in cl) if cl else 0.0,
                "widthMax": max(q["w"] for q in cl) if cl else 0.0,
                "riseMin": min(q["rise"] for q in cl) if cl else 0.0,
                "riseMax": max(q["rise"] for q in cl) if cl else 0.0,
                "slopeMin": min(q["slope"] for q in cl) if cl else 0.0,
                "slopeMax": max(q["slope"] for q in cl) if cl else 0.0,
                "profiles": cl,
            },
            "anchors": anc,
            "delta": {"up": len(ups), "down": len(dns),
                      "maxUp": round(max(dA), 2), "maxDown": round(min(dA), 2),
                      "volUp": round(sum(ups) * st * st, 0),
                      "volDown": round(-sum(dns) * st * st, 0)},
            "seamMax": [[round(q[0], 2), q[1], q[2]] for q in seam[:5]],
            "seamCells": len(seam),
            "plateauB": PYB,
            "skeletonInverted": {
                "cells": len(binv),
                "max": (max(q[0] for q in binv) if binv else 0.0),
                "zRange": ([min(q[2] for q in binv), max(q[2] for q in binv)]
                           if binv else None),
                "_": ("**「骨格(①②)だけに留める中間案」が図として成立するか**の判定。"
                      "⛔ 指図方が先に決めない — 法肩(③④ をしないので現況のまま)が"
                      "法尻(① で復元した谷底)より**低い**標本の数。"
                      "0 でなければ崖が逆勾配になる区間があるということ。")},
            "plateauSens": sens,
        },
        "h": hA, "hB": hB,
    }

    if "--check" in sys.argv:
        c2 = dict(out["_computed"])
        c2["cliff"] = {k: v for k, v in c2["cliff"].items() if k != "profiles"}
        print(json.dumps(c2, ensure_ascii=False, indent=1))
        return

    old = load(OUT) if os.path.exists(OUT) else None
    open(OUT, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    same = old is not None and old.get("h") == out["h"] and old.get("hB") == out["hB"]
    print("書いた: %s" % os.path.relpath(OUT, os.path.dirname(DOC)))
    print("  区画内 %d セル(谷底 %.1f%% / 崖 %.1f%% / 台地 %.1f%%)"
          % (ncell, out["_computed"]["zonePct"]["valley"],
             out["_computed"]["zonePct"]["cliff"],
             out["_computed"]["zonePct"]["plateau"]))
    print("  谷底の平面 h = %.4f %+.6f·x %+.6f·z(勾配 %.2f%% / 残差 最大 %.2f m / 錨 %d 点)"
          % (a0, b0, c0, grad * 100, max(abs(q[1]) for q in res), len(vp)))
    print("  崖(折れ線)標本 %d / 水平幅 %.1f〜%.1f m / 比高 %.2f〜%.2f m / 勾配 %.0f〜%.0f %%"
          % (len(cl), out["_computed"]["cliff"]["widthMin"],
             out["_computed"]["cliff"]["widthMax"],
             out["_computed"]["cliff"]["riseMin"], out["_computed"]["cliff"]["riseMax"],
             out["_computed"]["cliff"]["slopeMin"], out["_computed"]["cliff"]["slopeMax"]))
    for q in anc:
        if q["resid"] is None:
            print("    錨 %-7s 値=判読不能  区分 %-7s (当てはめ・判定に使わない)"
                  % (q["id"], q["zone"]))
        else:
            print("    錨 %-7s 読み %5.1f  復元 %6.2f  残差 %+.2f  区分 %-7s %s"
                  % (q["id"], q["y"], q["recon"], q["resid"], q["zone"],
                     "内" if q["in"] else "外"))
    print("  Δ 上げ %d セル(最大 %+.2f m・%s m³) / 下げ %d セル(最大 %+.2f m・%s m³)"
          % (len(ups), max(dA), "{:,.0f}".format(sum(ups) * st * st),
             len(dns), min(dA), "{:,.0f}".format(-sum(dns) * st * st)))
    print("  区画線の段 最大 %.2f m(%d セル)⚠ 摺り付けない — 隣家との食い違いそのもの"
          % (seam[0][0] if seam else 0.0, len(seam)))
    print("  B案の台地面 %.2f m(現況の台地セル %d の中央値)/ A案 %.2f m" % (PYB, len(pv), PY))
    print("  「骨格だけ」の中間案: 崖の逆勾配 %d 標本(最大 %.2f m)%s"
          % (len(binv), max([q[0] for q in binv] or [0.0]),
             "⛔ 図として成立しない" if binv else "⭕"))
    print("  冪等: %s" % ("1セルも動かず" if same else "更新あり(前回と違う)"))


if __name__ == "__main__":
    main()
