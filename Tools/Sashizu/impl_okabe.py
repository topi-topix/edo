"""岡部の算出物の器(EDO-0407)。`bake_impl.py okabe --write` が呼ぶ。

⭕ `graded` はいまの生成器(`build_sashizu.Model.graded_y` → `sashizu_lib.graded_y`)で
  世界の 1m 格子を焼く。指図の面・穴・法面の取り決めは生成器の検査(C04・C20 ほか)と同じ式を通るので、
  図で検めた地盤と建てる地盤が同じ物になる。
⭕ `corners` は bake_impl の共通の焼き手をそのまま使う。
⭕ `base`(塀・長屋の石垣基壇の露出)は消えた岡部の生成器(afb529c2^ の build_okabe_sashizu.py の run_base と
  --export-impl の base 節)を移した。外の地盤は当時 edgeProfile(静的な写しで腐った)から引いていたが、
  ここでは区画線から OUT m 外のいまの地盤(M.nat)を毎回測る。
⛔ planting / rails / kui / migiwa / gardens はまだ器が無い — 返さない(bake_impl が据え置きとして名指しで刷る)。
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_sashizu as B  # noqa: E402
import bake_impl as BI     # noqa: E402

EST = "okabe"
STEP = 1.0
MARGIN = 6.0


def bake_graded(M, poly):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    x0 = float(int(min(xs) - MARGIN))
    z0 = float(int(min(zs) - MARGIN))
    nx = int((max(xs) + MARGIN - x0) / STEP) + 1
    nz = int((max(zs) + MARGIN - z0) / STEP) + 1
    rows, holes = [], 0
    for j in range(nz):
        z = z0 + j * STEP
        row = []
        for i in range(nx):
            x = x0 + i * STEP
            u, v = M.UV(x, z)
            nat = M.nat(u, v)
            y = M.graded_y(u, v, nat)
            if y is None:
                if M.in_parcel(u, v):
                    holes += 1
                row.append(None)
            else:
                row.append(round(float(y), 3))
        rows.append(row)
    return {"x0": x0, "z0": z0, "step": STEP, "nx": nx, "nz": nz, "holes": holes, "h": rows}


OUT = 1.0          # 外の地盤を測る、区画線からの距離(m)


def _edge_frame(M, poly, e):
    n = len(poly)
    a, b = poly[e], poly[(e + 1) % n]
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, nz = -tz, tx
    if M.in_parcel(*M.UV(mx + nx * OUT, mz + nz * OUT)):
        nx, nz = -nx, -nz                              # 外向きへ
    return a, (tx, tz), (nx, nz)


def bake_base(M, poly, d):
    bmin = d["const"]["baseMin"]
    unit = d["const"]["baseUnit"]
    out = []
    for r in d["runs"]:
        if not r.get("base"):
            continue
        a, (tx, tz), (nx, nz) = _edge_frame(M, poly, r["edge"])

        def ex(sv):
            x = a[0] + tx * sv + nx * OUT
            z = a[1] + tz * sv + nz * OUT
            g = M.nat(*M.UV(x, z))
            return BI.rseat(r, sv) - g if g is not None else 0.0
        n = max(2, int((r["s1"] - r["s0"]) / 0.5))
        vs = [ex(r["s0"] + (r["s1"] - r["s0"]) * i / n) for i in range(n + 1)]
        segs, thin, cur = [], [], None
        sv = r["s0"]
        while sv <= r["s1"] + 1e-9:
            if ex(sv) >= bmin:
                cur = sv if cur is None else cur
            elif cur is not None:
                segs.append([round(cur, 3), round(sv, 3)])
                cur = None
            sv += 0.5
        if cur is not None:
            segs.append([round(cur, 3), round(r["s1"], 3)])
        prev = r["s0"]
        for a9, b9 in segs:
            if a9 - prev > 0.5:
                thin.append([round(prev, 3), round(a9, 3)])
            prev = b9
        if r["s1"] - prev > 0.5:
            thin.append([round(prev, 3), round(r["s1"], 3)])
        s = r.get("s")
        if s is None:                                  # 案1: 指図は sFrom(天端 − 法尻の地形)だけ ── 露出の最大を 1/4 刻みで切り上げ
            s = max(0.25, math.ceil(max(vs) / unit * 4 - 1e-9) / 4)
        out.append({"run": r["name"], "s": s, "cap": round(unit * s, 3),
                    "lo": round(min(vs), 3), "hi": round(max(vs), 3), "segs": segs, "thin": thin})
    return out


def bake():
    M = B.Model(EST)
    poly = BI.parcel_poly(EST)
    d = json.load(open(os.path.join(B.DOC, EST + "_sashizu.json"), encoding="utf-8"))
    im = json.load(open(os.path.join(B.DOC, EST + "_impl.json"), encoding="utf-8"))
    return {"graded": bake_graded(M, poly), "corners": BI.bake_corners(poly, d, im), "base": bake_base(M, poly, d)}
