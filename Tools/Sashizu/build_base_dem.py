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

# 正本の範囲 — 岡部・土井・松平・山王 + 山王坂の武家4区画(丹羽/京極/内藤/社人)を余裕をもって覆う
# ⚠ 2026-08-30 に東と南へ広げた(x1 -330→-12 / z0 600→478)。**既存セルの標高は1つも動かない**
#   (再生成の突き合わせで 87,556 セルすべて 0 差を確認済)。京極・内藤の区画は旧範囲の完全に外側に
#   あり、切り出せなかった。広げただけでセルが増えている。
CANON_SPEC = dict(x0=-800, z0=478, step=2, nx=395, nz=432, nd=2)

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
        parcels=["okabe"],
        doc="造成前の地形【確度P】。**世界座標**の格子。h[iz][ix]=標高m。指図の現況図(段彩+等高線)に使う。"
            "⚠ 岡部の敷地内は日比谷高校の近代造成(校庭の盛土16.0・校舎の盛土27〜28.8)を含む — "
            "江戸期の復元地盤は okabe_edo_dem.json / okabe_edo_world.json。",
    ),
    dict(
        name="doi_dem.json", x0=-700, z0=1030, step=2, nx=146, nz=90, nd=1, style="rows",
        parcels=["doi"],
        doc="造成前の地形【確度P】。**世界座標**の格子。h[iz][ix]=標高m。指図の現況図(段彩+等高線)に使う。",
    ),
    dict(
        name="matsudaira_dewa_dem.json", x0=-770, z0=1020, step=2, nx=170, nz=150, nd=2, style="compact",
        parcels=["matsudaira_dewa"],
        doc="松平・土井・岡部まわりの造成前の地形【確度P】。世界座標 2m 刻み(x0,z0 から)。"
            "現況図(段彩+等高線)はこれを読む。標高は海抜m。",
    ),
    dict(
        name="kyogoku_bitchu_dem.json", x0=-320, z0=640, step=2, nx=111, nz=96, nd=2, style="compact",
        parcels=["sannobuke_kyogoku"],
        doc="京極備中守上屋敷(丹後峯山藩)まわりの造成前の地形【確度P】。世界座標 2m 刻み(x0,z0 から)。"
            "h[iz][ix]=標高m。指図の現況図(段彩+等高線)・切盛図・断面がこれを読む。"
            "⚠ **現代**の地面で、跡地(国会前庭〜議員会館まわり)の近代造成を含む。",
    ),
    dict(
        name="sanno_dem.json", x0=-660, z0=636, step=2, nx=146, nz=171, nd=1, style="compact",
        parcels=["sannosha_prec", "sannosha_kanri", "sannobuke_juge"]
                + [f"sannojubo_parcels_{i}" for i in range(10)],
        doc="山王権現社まわりの造成前の地形【確度P】。世界座標の格子。h[iz][ix]=標高m。"
            "生成器 build_sanno_sashizu.py が §3a 現況図・§3b 切盛図でこれを読む。",
    ),
]

FIT_MARGIN = 40   # --fit で区画のまわりに確保する余白[m]
WARN_MARGIN = 20  # これを下回ったら「区画を動かすと溢れる」と知らせる[m]

SLICE_DOC = (
    " **正本 docs/Sashizu/base_dem.json からの切り出し**(生成器 Tools/Sashizu/build_base_dem.py)。"
    "⛔ 手で編集しない・Unity の live terrain から採り直さない。"
)


def load_parcels():
    """町割の正典 parcels.json を読む(区画の正典は敷地割ツール。ここは読むだけ)。"""
    j = json.load(open(os.path.join(SASHIZU, "parcels.json"), encoding="utf-8"))
    return {p["id"]: p["pts"] for p in j["parcels"] if p.get("pts")}


def parcel_bbox(pids, parcels):
    """担当区画をまとめた外接矩形。区画が1つも無ければ None。"""
    pts = [pt for pid in pids for pt in parcels.get(pid, [])]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    return min(xs), max(xs), min(zs), max(zs)


def snap_out(x0, x1, z0, z1, step):
    """格子の外側へ丸める。"""
    return (math.floor(x0 / step) * step, math.ceil(x1 / step) * step,
            math.floor(z0 / step) * step, math.ceil(z1 / step) * step)


def extent(spec):
    return (spec["x0"], spec["x0"] + spec["step"] * (spec["nx"] - 1),
            spec["z0"], spec["z0"] + spec["step"] * (spec["nz"] - 1))


def fit_extent(spec, parcels, margin):
    """担当区画 + 余白を覆うところまで extent を**広げる**(縮めない)。"""
    bb = parcel_bbox(spec["parcels"], parcels)
    if bb is None:
        return spec, 0
    need = snap_out(bb[0] - margin, bb[1] + margin, bb[2] - margin, bb[3] + margin, spec["step"])
    cur = extent(spec)
    x0, x1 = min(cur[0], need[0]), max(cur[1], need[1])
    z0, z1 = min(cur[2], need[2]), max(cur[3], need[3])
    grown = (x0, x1, z0, z1) != cur
    out = dict(spec)
    out["x0"], out["z0"] = x0, z0
    out["nx"] = (x1 - x0) // spec["step"] + 1
    out["nz"] = (z1 - z0) // spec["step"] + 1
    return out, grown


def report_margins(spec, parcels):
    """区画のまわりに何mの余白があるかを出し、足りなければ知らせる。戻り値=覆えていない件数。"""
    bb = parcel_bbox(spec["parcels"], parcels)
    if bb is None:
        print(f"   ⚠ {spec['name']}: 担当区画 {spec['parcels']} が parcels.json に無い")
        return 1
    x0, x1, z0, z1 = extent(spec)
    m = (bb[0] - x0, x1 - bb[1], bb[2] - z0, z1 - bb[3])   # 西 東 南 北
    tag = "   "
    bad = 0
    if min(m) < 0:
        tag, bad = " ⛔", 1
    elif min(m) < WARN_MARGIN:
        tag = " ⚠ "
    print(f"{tag}{spec['name']:20s} 区画の余白 西{m[0]:+5.0f} 東{m[1]:+5.0f} 南{m[2]:+5.0f} 北{m[3]:+5.0f} m")
    if bad:
        need, _ = fit_extent(spec, parcels, FIT_MARGIN)
        nx0, nx1, nz0, nz1 = extent(need)
        print(f"      → 区画が切り出しの外へ出ている。x[{nx0},{nx1}] z[{nz0},{nz1}] "
              f"(nx={need['nx']} nz={need['nz']}) へ広げること — `--fit` で自動的に広げられる")
    return bad


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


def build_slices(check_only=False, fit=False):
    canon = json.load(open(CANON, encoding="utf-8"))
    ch, cnx, cnz = canon["h"], canon["nx"], canon["nz"]
    cx0, cz0, cstep = canon["x0"], canon["z0"], canon["step"]
    parcels = load_parcels()
    print("区画との突き合わせ(町割 parcels.json が正典):")
    specs = []
    skipped = []
    for spec in SLICES:
        ok = True
        if fit:
            spec, grown = fit_extent(spec, parcels, FIT_MARGIN)
            if grown:
                x0, x1, z0, z1 = extent(spec)
                print(f"   ↔ {spec['name']:20s} 区画に合わせて x[{x0},{x1}] z[{z0},{z1}] へ広げた")
        if report_margins(spec, parcels):
            ok = False
        cx1 = cx0 + cstep * (cnx - 1)
        cz1 = cz0 + cstep * (cnz - 1)
        ex = extent(spec)
        if ex[0] < cx0 or ex[1] > cx1 or ex[2] < cz0 or ex[3] > cz1:
            print(f"   ⛔ {spec['name']}: 正本の範囲 x[{cx0},{cx1}] z[{cz0},{cz1}] の外へ出る。"
                  f"CANON_SPEC を広げて `--canon` から作り直すこと")
            ok = False
        if ok:
            specs.append(spec)
        else:
            skipped.append(spec["name"])
    if skipped:
        print(f"\n⛔ 覆えていない切り出しは書かない(据え置き): {', '.join(skipped)}")
        print("   ⚠ 据え置いた邸の DEM は**担当区画の一部を欠いたまま**である。上の指示に従って範囲を直すこと。")
        print("   他の邸は下で書き直す — 1邸の不足で全邸を止めない(EDO-0014)。")
    print()
    for s in specs:
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
        # 差分の報告(範囲が変わっていることがあるので世界座標で引き当てる)
        if old:
            def old_at(x, z):
                if (x - old["x0"]) % old["step"] or (z - old["z0"]) % old["step"]:
                    return None
                oi = (x - old["x0"]) // old["step"]
                oj = (z - old["z0"]) // old["step"]
                if not (0 <= oi < old["nx"] and 0 <= oj < old["nz"]):
                    return None
                return old["h"][oj][oi]

            diffs = []
            added = 0
            for jz in range(s["nz"]):
                z = s["z0"] + jz * s["step"]
                for ix in range(s["nx"]):
                    x = s["x0"] + ix * s["step"]
                    ov = old_at(x, z)
                    if ov is None:
                        added += 1
                        continue
                    if abs(ov - h[jz][ix]) > 10 ** (-s["nd"]) / 2:
                        diffs.append((x, z, ov, h[jz][ix]))
            big = [d for d in diffs if abs(d[2] - d[3]) > 0.5]
            worst = max(diffs, key=lambda d: abs(d[2] - d[3]), default=None)
            msg = (f"{s['name']:20s} {s['nx'] * s['nz']:6,}セル 変わる {len(diffs):5d} "
                   f"(うち>0.5m {len(big):4d})" + (f" / 新しく増える {added:,}セル" if added else ""))
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
        print(f"{len(specs)}邸の DEM を正本からの切り出しで書き直した。")
    if skipped:
        raise SystemExit(f"⛔ 据え置いた切り出しが {len(skipped)} 件ある: {', '.join(skipped)}")


def main():
    ap = argparse.ArgumentParser(description="地盤の正本と各邸DEMの生成器")
    ap.add_argument("--canon", action="store_true",
                    help="ref_height.npy から正本 base_dem.json を作り直す(メインの作業ツリーのみ)")
    ap.add_argument("--check", action="store_true", help="書かずに差分だけ報告する")
    ap.add_argument("--fit", action="store_true",
                    help="担当区画+余白を覆うところまで切り出しの範囲を広げる(縮めはしない)")
    a = ap.parse_args()
    if a.canon:
        build_canon()
    if not os.path.exists(CANON):
        raise SystemExit(f"正本が無い: {os.path.relpath(CANON, ROOT)} — 先に --canon で起こすこと")
    build_slices(check_only=a.check, fit=a.fit)


if __name__ == "__main__":
    main()
