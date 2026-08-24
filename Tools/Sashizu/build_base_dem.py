#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""地盤の正本(base_dem.json)を起こし、各邸の世界格子DEMをその切り出しとして書き出す。

**正本は Unity の live terrain ではない。**
2026-08-22 のジオリファレンス補正で Unity へ書き戻した参照ハイトマップ
(国土地理院 DEM5A/10B 由来 / `TerrainBackups/terrain_20260822_georef_fix/ref_height.npy`)が正本で、
これは「造成を一切含まない現代の地面」である。

⛔ **live terrain から `Terrain.SampleHeight` で採らないこと。** 採った時刻までに他家が流した造成が
そのまま「造成前の地形」として焼き込まれる。実際 2026-08-23 に、松平が 08:54 に流した造成を
岡部・土井が 13:52 の標本で吸い込み、土井の DEM は松平区画の 68% が松平の設計面 27.0 になっていた。

使い方:
    python3 Tools/Sashizu/build_base_dem.py --canon   # ref_height.npy → docs/Sashizu/base_dem.json
    python3 Tools/Sashizu/build_base_dem.py           # base_dem.json → 各邸の *_dem.json
    python3 Tools/Sashizu/build_base_dem.py --check   # 書かずに差分だけ報告する

`--canon` は `TerrainBackups/`(gitignore・メインの作業ツリーにしか無い)を読むので、worktree では
走らない。切り出し(既定の動作)は base_dem.json だけを読むので、どこでも走る。
"""
import argparse
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SASHIZU = os.path.join(ROOT, "docs", "Sashizu")
BACKUP = os.path.join(ROOT, "TerrainBackups", "terrain_20260822_georef_fix")
CANON = os.path.join(SASHIZU, "base_dem.json")

# 正本の範囲 — 岡部・土井・松平・山王の全 DEM を余裕をもって覆う
CANON_SPEC = dict(x0=-800, z0=600, step=2, nx=236, nz=371, nd=2)

CANON_DOC = (
    "**地盤の正本。造成を一切含まない現代の地面(海抜m)。**"
    "出自=2026-08-22 のジオリファレンス補正で Unity へ書き戻した参照ハイトマップ"
    "(国土地理院 DEM5A/10B → `JapanPlaneRectIX`。`TerrainBackups/terrain_20260822_georef_fix/ref_height.npy`)を"
    "世界座標の2m格子へ双一次補間したもの。h[iz][ix]=標高m。確度P(参照との |差| 中央値 0.127m)。"
    "⛔ **Unity の live terrain から採り直さないこと** — live は自他の造成が乗る作業面で、"
    "採る時刻によって値が変わる(2026-08-23 に松平の造成が岡部・土井の『造成前』へ焼き込まれた)。"
    "⚠ これは**現代**の地面であって江戸の地面ではない — 日比谷高校の校庭盛土も議長公邸の掘削跡も含む。"
    "近代造成を戻した面が要るなら、各邸が考証で復元レイヤを別に持つ(岡部の okabe_edo_world.json)。"
    "生成器 Tools/Sashizu/build_base_dem.py"
)

# 各邸の切り出し。extent は現行ファイルと同一(nd=小数桁も現行に合わせ、差分を汚染セルだけに保つ)
SLICES = [
    dict(
        name="okabe_dem.json", x0=-720, z0=930, step=2, nx=186, nz=100, nd=1, style="rows",
        doc="造成前の地形【確度P】。**世界座標**の格子。h[iz][ix]=標高m。指図の現況図(段彩+等高線)に使う。"
            "⚠ 岡部の敷地内は日比谷高校の近代造成(校庭の盛土16.0・校舎の盛土27〜28.8)を含む — "
            "江戸期の復元地盤は okabe_edo_dem.json / okabe_edo_world.json。",
    ),
    dict(
        name="doi_dem.json", x0=-700, z0=1030, step=2, nx=146, nz=90, nd=1, style="rows",
        doc="造成前の地形【確度P】。**世界座標**の格子。h[iz][ix]=標高m。指図の現況図(段彩+等高線)に使う。",
    ),
    dict(
        name="matsudaira_dem.json", x0=-770, z0=1020, step=2, nx=170, nz=150, nd=2, style="compact",
        doc="松平・土井・岡部まわりの造成前の地形【確度P】。世界座標 2m 刻み(x0,z0 から)。"
            "現況図(段彩+等高線)はこれを読む。標高は海抜m。",
    ),
    dict(
        name="sanno_dem.json", x0=-660, z0=636, step=2, nx=146, nz=171, nd=1, style="compact",
        doc="山王権現社まわりの造成前の地形【確度P】。世界座標の格子。h[iz][ix]=標高m。"
            "生成器 build_sanno_sashizu.py が §3a 現況図・§3b 切盛図でこれを読む。",
    ),
]

SLICE_DOC = (
    " **正本 docs/Sashizu/base_dem.json からの切り出し**(生成器 Tools/Sashizu/build_base_dem.py)。"
    "⛔ 手で編集しない・Unity の live terrain から採り直さない。"
)


def load_ref():
    """ref_height.npy と meta.json を読む。numpy が要る。"""
    import numpy as np  # noqa: F401  (--canon のときだけ要る)

    meta = json.load(open(os.path.join(BACKUP, "meta.json")))
    ref = np.load(os.path.join(BACKUP, "ref_height.npy"))
    if ref.shape != (meta["R"], meta["R"]):
        raise SystemExit(f"ref_height.npy の形が meta と合わない: {ref.shape} vs R={meta['R']}")
    return ref, meta


def bilinear(h, nx, nz, fx, fz):
    """h[iz][ix] を双一次補間する。範囲外は None。"""
    i0, j0 = math.floor(fx), math.floor(fz)
    if not (0 <= i0 < nx - 1 and 0 <= j0 < nz - 1):
        # 端はクランプで拾う(格子の最終行・最終列)
        if not (0 <= fx <= nx - 1 and 0 <= fz <= nz - 1):
            return None
        i0 = min(i0, nx - 2)
        j0 = min(j0, nz - 2)
    tx, tz = fx - i0, fz - j0
    a, b = h[j0][i0], h[j0][i0 + 1]
    c, d = h[j0 + 1][i0], h[j0 + 1][i0 + 1]
    return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + d * tx) * tz


def build_canon():
    ref, meta = load_ref()
    px, pz, sp = meta["posX"], meta["posZ"], meta["spacing"]
    s = CANON_SPEC
    h = []
    for jz in range(s["nz"]):
        z = s["z0"] + jz * s["step"]
        fz = (z - pz) / sp
        row = []
        for ix in range(s["nx"]):
            x = s["x0"] + ix * s["step"]
            fx = (x - px) / sp
            v = bilinear(ref, meta["R"], meta["R"], fx, fz)
            if v is None:
                raise SystemExit(f"正本の範囲が地形の外に出た: world({x},{z})")
            row.append(round(float(v), s["nd"]))
        h.append(row)
    out = {"_": CANON_DOC, "x0": s["x0"], "z0": s["z0"], "step": s["step"],
           "nx": s["nx"], "nz": s["nz"], "h": h}
    write_json(CANON, out, style="rows", nd=s["nd"])
    print(f"正本 {os.path.relpath(CANON, ROOT)} を書いた — "
          f"x[{s['x0']},{s['x0'] + s['step'] * (s['nx'] - 1)}] z[{s['z0']},{s['z0'] + s['step'] * (s['nz'] - 1)}] "
          f"{s['nx']}×{s['nz']}={s['nx'] * s['nz']:,}セル")


def fmt_rows(h, nd):
    return ",\n  ".join("[" + ",".join(fmt_num(v, nd) for v in row) + "]" for row in h)


def fmt_num(v, nd):
    if v is None:
        return "null"
    s = f"{v:.{nd}f}"
    return s


def write_json(path, obj, style, nd):
    h = obj["h"]
    head = {k: obj[k] for k in ("_", "x0", "z0", "step", "nx", "nz")}
    if style == "rows":
        body = "{\n"
        body += ' "_": ' + json.dumps(head["_"], ensure_ascii=False) + ",\n"
        body += (f' "x0": {head["x0"]}, "z0": {head["z0"]}, "step": {head["step"]},'
                 f' "nx": {head["nx"]}, "nz": {head["nz"]},\n')
        body += ' "h": [\n  ' + fmt_rows(h, nd) + "\n ]\n}\n"
    else:
        rows = ",".join("[" + ",".join(fmt_num(v, nd) for v in row) + "]" for row in h)
        body = ("{" + '"_":' + json.dumps(head["_"], ensure_ascii=False)
                + f',"x0":{head["x0"]},"z0":{head["z0"]},"step":{head["step"]}'
                + f',"nx":{head["nx"]},"nz":{head["nz"]},"h":[' + rows + "]}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def build_slices(check_only=False):
    canon = json.load(open(CANON, encoding="utf-8"))
    ch, cnx, cnz = canon["h"], canon["nx"], canon["nz"]
    cx0, cz0, cstep = canon["x0"], canon["z0"], canon["step"]
    for s in SLICES:
        path = os.path.join(SASHIZU, s["name"])
        old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
        h = []
        for jz in range(s["nz"]):
            z = s["z0"] + jz * s["step"]
            row = []
            for ix in range(s["nx"]):
                x = s["x0"] + ix * s["step"]
                v = bilinear(ch, cnx, cnz, (x - cx0) / cstep, (z - cz0) / cstep)
                if v is None:
                    raise SystemExit(f"{s['name']}: 正本の範囲の外 world({x},{z})")
                row.append(round(v, s["nd"]))
            h.append(row)
        # 差分の報告
        if old:
            diffs = [(s["x0"] + ix * s["step"], s["z0"] + jz * s["step"], old["h"][jz][ix], h[jz][ix])
                     for jz in range(s["nz"]) for ix in range(s["nx"])
                     if old["h"][jz][ix] is not None
                     and abs(old["h"][jz][ix] - h[jz][ix]) > 10 ** (-s["nd"]) / 2]
            big = [d for d in diffs if abs(d[2] - d[3]) > 0.5]
            worst = max(diffs, key=lambda d: abs(d[2] - d[3]), default=None)
            msg = (f"{s['name']:20s} {s['nx'] * s['nz']:6,}セル 変わる {len(diffs):5d} "
                   f"(うち>0.5m {len(big):4d})")
            if worst:
                msg += f" 最大 {worst[2]}→{worst[3]} ({worst[3] - worst[2]:+.2f}m) @({worst[0]},{worst[1]})"
            print(msg)
        if check_only:
            continue
        doc = s["doc"] + SLICE_DOC
        out = {"_": doc, "x0": s["x0"], "z0": s["z0"], "step": s["step"],
               "nx": s["nx"], "nz": s["nz"], "h": h}
        write_json(path, out, style=s["style"], nd=s["nd"])
    if not check_only:
        print("各邸の DEM を正本からの切り出しで書き直した。")


def main():
    ap = argparse.ArgumentParser(description="地盤の正本と各邸DEMの生成器")
    ap.add_argument("--canon", action="store_true",
                    help="ref_height.npy から正本 base_dem.json を作り直す(メインの作業ツリーのみ)")
    ap.add_argument("--check", action="store_true", help="書かずに差分だけ報告する")
    a = ap.parse_args()
    if a.canon:
        build_canon()
    if not os.path.exists(CANON):
        raise SystemExit(f"正本が無い: {os.path.relpath(CANON, ROOT)} — 先に --canon で起こすこと")
    build_slices(check_only=a.check)


if __name__ == "__main__":
    main()
