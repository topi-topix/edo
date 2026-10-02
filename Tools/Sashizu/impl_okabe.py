"""岡部の算出物の器(EDO-0407)。`bake_impl.py okabe --write` が呼ぶ。

⭕ `graded` はいまの生成器(`build_sashizu.Model.graded_y` → `sashizu_lib.graded_y`)で
  世界の 1m 格子を焼く。指図の面・穴・法面の取り決めは生成器の検査(C04・C20 ほか)と同じ式を通るので、
  図で検めた地盤と建てる地盤が同じ物になる。
⭕ `corners` は bake_impl の共通の焼き手をそのまま使う。
⛔ planting / rails / base / kui / migiwa / gardens はまだ器が無い — 返さない(bake_impl が据え置きとして名指しで刷る)。
"""
import json
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


def bake():
    M = B.Model(EST)
    poly = BI.parcel_poly(EST)
    d = json.load(open(os.path.join(B.DOC, EST + "_sashizu.json"), encoding="utf-8"))
    im = json.load(open(os.path.join(B.DOC, EST + "_impl.json"), encoding="utf-8"))
    return {"graded": bake_graded(M, poly), "corners": BI.bake_corners(poly, d, im)}
