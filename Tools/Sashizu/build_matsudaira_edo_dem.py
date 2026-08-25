#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""松平出羽守邸の江戸期地盤レイヤの生成器 — **種地は正本 `base_dem.json`**。

CLAUDE.md 規則12 / `docs/Sashizu/README.md` 決めごと5 /
スキル `unity-buke-yashiki` `references/sashizu.md` §3a「地形は正本から採る」。

⚠ **2026-08-26 に起こした。** 目的は隣家(土井)の共有辺検査 —
`build_doi_sashizu.py` の `shared_edge_check` が `matsudaira_edo_world.json` を読むのに
ファイルが存在せず、**土井の辺8・9(松平に面する、一番検査したい辺)が黙って素通り**していた。

⛔ **松平の近代造成の復元(recon)は未定義。** 岡部は `okabe_edo_recon.json`、土井は
`doi_edo_recon.json` が手順を持つが、松平にはまだ無い。よってこのファイルが書く
`matsudaira_edo_world.json` は**素の正本の写し**(区画の中も外も `base_dem.json` そのもの・
`_reconCells: 0`)である。松平の復元レイヤを定義するのは**松平の屋敷セッションの仕事** —
`matsudaira_edo_recon.json` を起こしたら、この生成器に土井と同じ `reconstruct` を実装する。

⛔ **`matsudaira_terrain.json` には触れない。** あれは生成器なしの手書きデータで、
扱いはユーザー裁定待ち(2026-08-25)。このスクリプトは読みもしない。

書くもの(派生物 — **手で編集しない**):

| ファイル | 中身 |
|---|---|
| `matsudaira_edo_world.json` | **江戸期の地盤**(世界2m格子)。現状は復元ゼロ=**正本そのもの** |

使い方:
    python3 Tools/Sashizu/build_matsudaira_edo_dem.py            # 書く(冪等)
    python3 Tools/Sashizu/build_matsudaira_edo_dem.py --check    # 書かずに検査だけ
"""

import json
import math
import os
import sys

DOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "docs", "Sashizu"))
BASE = os.path.join(DOC, "base_dem.json")
SASHIZU = os.path.join(DOC, "matsudaira_sashizu.json")
RECON = os.path.join(DOC, "matsudaira_edo_recon.json")
WORLD = os.path.join(DOC, "matsudaira_edo_world.json")


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


def build(check=False):
    if os.path.exists(RECON):
        raise SystemExit("⛔ %s が現れた — 復元の手順が定義されたのに、この生成器はまだ"
                         "素の正本しか書けない。土井の build_doi_edo_dem.py の reconstruct を"
                         "移植してから回すこと。" % os.path.basename(RECON))
    seed = load(BASE)
    d = load(SASHIZU)
    poly = d["polygon"]

    # 正本の格子が松平区画を覆っているか(覆っていなければ共有辺検査が None を掴む)
    x1 = seed["x0"] + (seed["nx"] - 1) * seed["step"]
    z1 = seed["z0"] + (seed["nz"] - 1) * seed["step"]
    for (px, pz) in poly:
        if not (seed["x0"] <= px <= x1 and seed["z0"] <= pz <= z1):
            raise SystemExit("⛔ 区画頂点 (%.1f, %.1f) が正本の格子 x%.0f..%.0f / z%.0f..%.0f の外"
                             % (px, pz, seed["x0"], x1, seed["z0"], z1))
    inside = sum(1 for iz in range(seed["nz"]) for ix in range(seed["nx"])
                 if in_poly(poly, seed["x0"] + seed["step"] * ix, seed["z0"] + seed["step"] * iz))
    print("   区画内 %d セル(2m格子)/ 復元 0 セル(recon 未定義=正本そのまま)" % inside)

    world = dict(seed)
    world["_reconCells"] = 0
    world["_"] = ("**江戸期の地盤**(世界2m格子)。⛔ **松平の近代造成の復元は未定義** — "
                  "区画の中も外も正本 `base_dem.json` そのもの(復元 0 セル)。"
                  "matsudaira_edo_recon.json を起こしたら生成器に reconstruct を実装する。"
                  "⛔ **手で編集しない。** 生成器 `Tools/Sashizu/build_matsudaira_edo_dem.py` が"
                  "毎回作り直す。")

    if check:
        print("   --check: 書かずに終了")
        return
    json.dump(world, open(WORLD, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("   wrote %s" % os.path.basename(WORLD))


if __name__ == "__main__":
    build(check="--check" in sys.argv)
