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

復元の中身(何を戻したか)は `okabe_edo_recon.json` が持つ — **区画内の差分だけ**の疎な層で、
出自は 2026-08-23〜24 の考証(下の `_` を読むこと)。この生成器は差分を解釈しない。

使い方:
    python3 Tools/Sashizu/build_okabe_edo_dem.py            # 3枚を書く(冪等)
    python3 Tools/Sashizu/build_okabe_edo_dem.py --check    # 書かずに差分だけ出す
    python3 Tools/Sashizu/build_okabe_edo_dem.py --extract  # 現行の world から差分層を起こす(初回のみ)
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


def extract():
    """現行の `okabe_edo_world.json` から**区画内の復元差分**を取り出して層に起こす(初回のみ)。

    差分の基準は「正本を小数1桁に丸めた値」— 従前の world はその精度の標本の上に
    載っていたので、こう取ると現行の復元値が 1:1 で再現できる。
    ⚠ 区画の外は**捨てる**。捨てるのがこの是正の本体である。"""
    base = load(BASE)
    old = load(WORLD)
    poly = load(SASHIZU)["polygon"]
    ix0 = (old["x0"] - base["x0"]) // base["step"]
    iz0 = (old["z0"] - base["z0"]) // base["step"]
    cells = []
    dropped = 0
    dmax = 0.0
    for iz in range(old["nz"]):
        for ix in range(old["nx"]):
            x = old["x0"] + old["step"] * ix
            z = old["z0"] + old["step"] * iz
            b = base["h"][iz + iz0][ix + ix0]
            e = old["h"][iz][ix]
            if b is None or e is None:
                continue
            dl = e - round(b, 1)
            if abs(dl) <= 0.051:
                continue
            if not in_poly(poly, x, z):
                dropped += 1
                dmax = max(dmax, abs(dl))
                continue
            cells.append([ix, iz, round(dl, 2)])
    out = dict(WIN)
    out["_"] = (
        "**岡部区画の中だけの『近代造成を戻す』差分層**(単位 m・正本 `base_dem.json` に足す)。"
        "確度 U/B — 復元の判断であって実測ではない。`d` は [ix, iz, Δ] の疎な並びで、"
        "格子は `okabe_edo_world.json` と同じ。⛔ **区画の外には1セルも置かない** — "
        "2026-08-24 に復元が境界を越えて滲み、樹下邸(`sannobuke_juge`)の地盤を最大 +2.78m "
        "持ち上げていた(通達)。\\n"
        "**何を戻したか**(2026-08-23〜24 の考証): ① 校庭の帯(v≦41・u≦17 の低い平坦)は "
        "[五千分一東京図31](明治16・確度A)の三帯(台地24〜26／崖／低地12〜14)から起こした崖のモデルへ。"
        "② 校舎の盛土(v≧41 で 25.3 超)は台地の自然面へ。③ 台地南の『22.70 の平坦』は"
        "明治16年図に閉じた等高線が無く近代の切土平場と判定し、周囲の実測台地セルからの"
        "逆距離加重補間で埋め直した(設計面と同じ 24.80 を入れると『|設計面−地盤|≦0.5m』の"
        "検査が恒真になるため)。④ **街路(辺12 三べ坂・辺10 袋小路)と斜面は現況のまま**(規則8)。\\n"
        "生成器 `Tools/Sashizu/build_okabe_edo_dem.py`。")
    out["d"] = cells
    json.dump(out, open(RECON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("差分層を起こした: 区画内 %d セル / **区画外の %d セルを捨てた**(最大 %.2fm)"
          % (len(cells), dropped, dmax))


def build(check=False):
    base = load(BASE)
    sz = load(SASHIZU)
    poly = sz["polygon"]
    recon = load(RECON)
    for k in ("x0", "z0", "step", "nx", "nz"):
        if recon[k] != WIN[k]:
            sys.exit("⛔ 差分層の格子が窓と違う(%s: %s ≠ %s)" % (k, recon[k], WIN[k]))
    dmap = dict(((c[0], c[1]), c[2]) for c in recon["d"])

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

    # ── ① 江戸期の復元地盤(世界2m格子)
    hw = []
    inside = 0
    for iz in range(WIN["nz"]):
        row = []
        for ix in range(WIN["nx"]):
            b = base["h"][iz + iz0][ix + ix0]
            if b is None:
                row.append(None)
                continue
            x = WIN["x0"] + WIN["step"] * ix
            z = WIN["z0"] + WIN["step"] * iz
            if in_poly(poly, x, z):
                inside += 1
                row.append(round(round(b, 1) + dmap.get((ix, iz), 0.0), 2))
            else:
                row.append(round(b, 2))          # ⛔ 区画の外は正本そのもの
        hw.append(row)
    world = dict(WIN)
    world["_"] = (
        "**江戸期の復元地盤**を世界座標2m格子で出したもの(確度U/B)。指図の現況図(段彩+等高線)="
        "**造成の出発点**に使う。**区画の中 = 正本 `base_dem.json` + 復元差分 `okabe_edo_recon.json`／"
        "区画の外 = 正本そのもの**(近代造成を戻す判断は岡部の敷地内でのみ行う)。"
        "⛔ 手で編集しない・Unity の live terrain から採り直さない(CLAUDE.md 規則12)。"
        "生成器 `Tools/Sashizu/build_okabe_edo_dem.py`。")
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
        if not check:
            json.dump(new, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("   区画内 %d セル / 復元差分 %d セル" % (inside, len(dmap)))
    if check:
        print("   (--check なので書いていない)")


if __name__ == "__main__":
    if "--extract" in sys.argv:
        extract()
    else:
        build(check="--check" in sys.argv)
