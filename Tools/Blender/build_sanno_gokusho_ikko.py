# -*- coding: utf-8 -*-
"""山王権現社の**御供所** — 文政3年『山王御宮絵図』の形の**独立の一棟**(施主の再裁定 2026-09-15)。

    blender --background --python Tools/Blender/build_sanno_gokusho_ikko.py -- [--render] [--no-export]

⛔ 明治16年図の L 字の3本(`build_sanno_gokusho.py` の主屋・北の継ぎ・東の腕)は使わない。FBX も生成器も残す。

━━━ 平面(指図 `munes[御供所]`・`links[L_Gusho]`)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・柱芯 梁間 3 間(東西 u)× 桁行 4.5 間(南北 v)= 5.454 × 8.181 m。切妻・**棟は南北**・本瓦葺。
・柱間: 東西 = 1 間 × 3【指図の間数】/ 南北 = 4.5 間を 5 等分(1.636)【U 部材方】。
・**渡廊下の口** = 北面の東の柱間(u −28.75〜−27.75)。口の東の柱 = 箱の北東の隅柱 ⇒ 渡廊下の東の柱の通りが
  箱の東面と面一(`links[L_Gusho]` の u −28.25・幅 1 間)。口は敷居・鴨居・上の小壁だけで戸を立てない(廊下が続く)。
・勝手口 = 南面の中の柱間(板戸を半ば引いた姿)【U 部材方】。東西の面の 2・4 番目の柱間に連子窓(裏に明かり障子)【U】。

━━━ 高さ(地盤 = ピボット Y0 = 平場の設計面から)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・基壇 0.45(切石・葛石の縁)・出 0.30 四周【U — 旧 御供所の値を引き継ぐ】。床(土間)= 基壇の天端。
・軒先 3.00【U — 旧 御供所の切妻(継ぎ・腕)の考証値を引き継ぐ】・軒の出 0.75・ケラバの出 0.45【U 部材方】。
・勾配 = キットの本瓦モジュールの素の勾配 `GR.RATIO`(5.5 寸)⇒ **棟高は従属値**(`const.muneHeightRule`:
  平場の設計面 → 大棟の上端・鬼を含まない)。⛔ 棟高を数で決めて勾配を曲げない(瓦場を剪断すると割付が崩れる)。

━━━ 材 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・瓦 = キットの `roof`・棟と鬼 = `roof ornaments`(= 楼門の「在庫の本瓦」と同じ材 ⇒ 南列の堂もこの材で焼く)。
  ⛔ `SH.to_copper` を通さない(銅瓦葺は社殿5棟・中門・透塀だけ)。
・木 `wood` / 漆喰 `wall C` / 板戸・障子 `door wall` / 基壇 `Kirishi`。

━━━ 軸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unity ローカル X = 東(u)/ Z = 北(v)/ Y = 上。**ピボット = 柱芯の矩形の中心・地盤**。yaw 0・scale one。
"""
import bpy, bmesh, sys, os, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH
import build_sanno_romon as RM
import build_sanno_gokusho as GK

K = 1.818
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
NU, NV = 3, 4.5                                   # 指図 munes[御供所].du / dv[間]
U0, V0 = -30.75, -13.0                            # 指図 munes[御供所].u0 / v0(組み上がりの検証だけに使う)
GUSHO_U, GUSHO_W = -28.25, 1.0                    # 指図 links[L_Gusho] の芯の u と幅[間]
G = dict(kidanH=0.45, kidanOut=0.30, post=0.18, koshi=0.90, kabeT=0.08, ketaH=0.18,
         eaveZ=3.00, eave=0.75, keraba=0.45, bayV=5,
         ridgeW=0.46, ridgeH=0.38, ridgeSeat=0.13, sodeW=0.30, sodeH=0.24,
         hafuW=0.36, hafuT=0.10, hafuDrop=0.55, uchinori=1.80)
ALLOWED = ("wood", "wall C", "door wall", "roof", "roof ornaments", "Kirishi")


def lin(a, b, n):
    return [a + (b - a) * i / float(n) for i in range(n + 1)]


# ==========================================================================
# 屋根 — キットの本瓦の切妻(素の勾配)。Blender 座標で組み、大棟を Blender −Y(Unity +Z)へ回す
# ==========================================================================
def kirizuma_hon(name, run, span, eave, keraba, eaveZ):
    """run = 大棟の長さ(柱芯)・span = 梁間(柱芯)。返り値 (object, half, k)。
    ⭐ `GR.make_kirizuma` は渡廊下用で、**妻壁をケラバの端に立て**・破風と棟が小振り。
      ここでは破風・袖瓦・鬼を棟の大きさへ上げ、妻壁は軸部の側(壁の通り)で別に立てる。"""
    x0, x1 = -keraba, run + keraba
    y0, y1 = -eave, span + eave
    ym = (y0 + y1) / 2.0
    h = (y1 - y0) / 2.0 * GR.RATIO
    pieces = [GR._tile_field_fast([[(x0, y0), (x1, y0), (x1, ym), (x0, ym)]], (x0, y0), 90, 0.0, name + "_S"),
              GR._tile_field_fast([[(x1, y1), (x0, y1), (x0, ym), (x1, ym)]], (x0, y1), 270, 0.0, name + "_N")]
    p = GR.palette()
    zr = h - G["ridgeSeat"]
    pieces += GR.ridge((x0, ym, zr), (x1, ym, zr), name + "_omune", w=G["ridgeW"], h=G["ridgeH"])
    pieces += GR.oni((x0 + 0.12, ym, zr), (-1, 0), name + "_oni0", scale=1.0)
    pieces += GR.oni((x1 - 0.12, ym, zr), (1, 0), name + "_oni1", scale=1.0)
    geo = []
    for gx, inward in ((x0, +1), (x1, -1)):
        g = GR.gable(gx, inward, y0, y1, 0.0, ym, h, name + "_g", p, thick=0.10,
                     bw=G["hafuW"], bt=G["hafuT"], drop=G["hafuDrop"], lattice=False, gegyo=False)
        bpy.data.objects.remove(g[0][0], do_unlink=True)      # 妻壁(先頭)はケラバの端に立つので捨てる
        geo += g[1:]
        # 袖瓦 — 破風の天端に被る列。⛔ 大棟を跨がせない(棟幅の半分 + 0.03 で止める)
        sx = gx + inward * 0.06
        for uy, sg in ((y0, +1), (y1, -1)):
            stop = ym - sg * (G["ridgeW"] / 2.0 + 0.03)
            zst = (abs(stop - y0) if sg > 0 else abs(y1 - stop)) * GR.RATIO
            pieces += GR.ridge((sx, uy, 0.22), (sx, stop, zst + 0.22), name + "_sode", w=G["sodeW"], h=G["sodeH"])
    for o, uv in geo:
        if o:
            if uv:
                V.set_uv(o, uv)
            pieces.append(o)
    V.dedup_materials()
    o = V.join([q for q in pieces if q], name)
    V.set_origin(o, (run / 2.0, span / 2.0, 0.0))
    o.location = (0.0, 0.0, 0.0)                     # ⭐ メッシュは中心に居る(set_origin 済み)
    o.data.transform(Matrix.Translation((0.0, 0.0, eaveZ)))
    o.data.transform(Matrix.Rotation(math.radians(90.0), 4, 'Z'))   # 大棟 Blender X → Blender Y(Unity Z)
    o.data.update()
    bpy.context.view_layer.update()
    return o, (y1 - y0) / 2.0, GR.RATIO


# ==========================================================================
# 軸部
# ==========================================================================
def wall_run(M, uv, along, fixed, nodes, floor, top, kinds, out):
    """柱間ごとの壁。kinds = {柱間の番号: "open" | "itado" | "mado"}。out = 外の向き(±1)。"""
    pr = G["post"] / 2.0
    kt = G["kabeT"] / 2.0

    def box(b0, b1, h0, h1, t0, t1, uvr, m):
        if along == "u":
            SH.box3(M, b0, b1, fixed + t0, fixed + t1, h0, h1, uvr, m, grain="u")
        else:
            SH.box3(M, fixed + t0, fixed + t1, b0, b1, h0, h1, uvr, m, grain="v")
    zk = floor + G["koshi"]
    zu = floor + G["uchinori"]
    for i in range(len(nodes) - 1):
        s0, s1 = nodes[i] + pr, nodes[i + 1] - pr
        kind = kinds.get(i)
        if kind in ("open", "itado"):
            box(s0, s1, floor, floor + 0.05, -0.06, 0.06, uv["wood_h"], SH.W)             # 敷居
            box(s0, s1, zu, zu + 0.10, -0.06, 0.06, uv["wood_h"], SH.W)                  # 鴨居
            box(s0, s1, zu + 0.10, top, -kt, kt, uv["wall"], SH.WC)                       # 上の小壁
            if kind == "itado":
                mid = (s0 + s1) / 2.0
                box(s0, mid + 0.04, floor + 0.05, zu, -out * 0.10, -out * 0.06, uv["itado"], SH.DW)
            continue
        if along == "u":
            SH.panel_ita(M, s0, s1, "u", fixed, floor, zk, uv["wood"], SH.W, t=0.025)
        else:
            SH.panel_ita(M, s0, s1, "v", fixed, floor, zk, uv["wood"], SH.W, t=0.025)
        box(s0, s1, floor, zk, -0.012, 0.012, uv["wood_h"], SH.W)                           # 腰板の裏板
        if kind == "mado":
            box(s0, s1, zk, zk + 0.06, -0.07, 0.07, uv["wood_h"], SH.W)                    # 窓台
            box(s0, s1, zu, zu + 0.08, -0.07, 0.07, uv["wood_h"], SH.W)                    # 窓の鴨居
            L = s1 - s0
            n = max(3, int(round(L / 0.12)))
            for j in range(n):
                c = s0 + L * (j + 0.5) / n
                box(c - 0.0225, c + 0.0225, zk + 0.06, zu, out * 0.01, out * 0.055, uv["wood"], SH.W)   # 連子子
            # ⛔ 格子だけだと素通し ⇒ 裏に明かり障子(README)
            box(s0, s1, zk + 0.06, zu, -out * 0.04, -out * 0.02, uv["shoji"], SH.DW)
            box(s0, s1, zu + 0.08, top, -kt, kt, uv["wall"], SH.WC)
            continue
        box(s0, s1, zk, top, -kt, kt, uv["wall"], SH.WC)


def build(name):
    hu, hv = NU * K / 2.0, NV * K / 2.0
    ms, uv = SH.mats()
    floor = G["kidanH"]
    eave, ker = G["eave"], G["keraba"]
    roof, half, k = kirizuma_hon(name + "_roof", 2 * hv, 2 * hu, eave, ker, G["eaveZ"])
    surf = lambda x_abs: G["eaveZ"] + k * (half - x_abs)        # 名目の屋根面(Unity |X| の関数)
    zf = lambda X, Z: surf(abs(X))
    inside = lambda X, Z: abs(Z) <= hv + ker - 0.8 and 0.30 < abs(X) < half - 0.30
    off = GK.roof_dmin(roof, inside, zf) - 0.01
    slab = GK.noji_slab(name + "_noji", lambda X, Z: abs(X) <= half and abs(Z) <= hv + ker,
                        (-half, half, -(hv + ker), hv + ker), zf, off)
    keta_top = surf(hu) + off - 0.03                   # ⭐ 桁の天端 = 野地の下面(瓦を突き抜けない)
    top = keta_top - G["ketaH"]
    M = VM.Mesh()
    us, vs = lin(-hu, hu, NU), lin(-hv, hv, G["bayV"])
    pts = [(uu, vs[0]) for uu in us] + [(uu, vs[-1]) for uu in us] + \
          [(us[0], vv) for vv in vs[1:-1]] + [(us[-1], vv) for vv in vs[1:-1]]
    GK.posts(M, uv, pts, floor, keta_top)
    # 口の柱間(北面): 渡廊下の u 範囲に一致する柱間を探す(⛔ 番号を決め打ちしない)
    uc = U0 + NU / 2.0
    gu0, gu1 = (GUSHO_U - GUSHO_W / 2.0 - uc) * K, (GUSHO_U + GUSHO_W / 2.0 - uc) * K
    gi = next((i for i in range(NU) if abs(us[i] - gu0) < 1e-3 and abs(us[i + 1] - gu1) < 1e-3), None)
    if gi is None:
        raise SystemExit("[gokusho] ⛔ 渡廊下の口 u %.3f〜%.3f が北面の柱間に乗らない(柱芯 %s)" % (gu0, gu1, us))
    wall_run(M, uv, "u", hv, us, floor, top, {gi: "open"}, +1)
    wall_run(M, uv, "u", -hv, us, floor, top, {NU // 2: "itado"}, -1)
    wall_run(M, uv, "v", hu, vs, floor, top, {1: "mado", 3: "mado"}, +1)
    wall_run(M, uv, "v", -hu, vs, floor, top, {1: "mado", 3: "mado"}, -1)
    # 桁(平の壁の上 — ケラバの下まで通す)・妻梁(妻の壁の上)
    for uu in (-hu, hu):
        SH.box3(M, uu - 0.08, uu + 0.08, -(hv + ker - 0.05), hv + ker - 0.05, top, keta_top, uv["wood_h"], SH.W, grain="v")
    for vv in (-hv, hv):
        SH.box3(M, -hu + 0.08, hu - 0.08, vv - 0.08, vv + 0.08, top, keta_top, uv["wood_h"], SH.W, grain="u")
        # 妻壁(壁の通り)— 上端は野地の下なり
        GK.vstrip_u(M, [-hu, 0.0, hu], vv - 0.04, vv + 0.04, lambda u: keta_top - 0.02,
                    lambda u: surf(abs(u)) + off - 0.04, uv["wall"], SH.WC)
    body = M.to_object(name + "_body", ms)
    out = {s: G["kidanOut"] for s in ("+X", "-X", "+Z", "-Z")}
    stones = GK.kidan(hu, hv, out, ("+X", "+Z", "-Z"), name + "_kidan")
    V.dedup_materials()
    o = V.join([body, roof, slab] + stones, name)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    info = dict(hu=hu, hv=hv, half=half, k=k, off=off, keta_top=keta_top, gate=(gi, us[gi], us[gi + 1]),
                floor=floor)
    print("[gokusho] 柱芯 %.3f × %.3f / 勾配 %.4f / 瓦の谷 %.3f / 桁の上端 %.3f / 渡廊下の口 = 北面の柱間 %d(X %.3f〜%.3f)"
          % (2 * hu, 2 * hv, k, off + 0.01, keta_top, gi, us[gi], us[gi + 1]))
    return o, info


# ==========================================================================
# 検算
# ==========================================================================
def band_outline(o, bands):
    U = SH.unity_verts(o)
    rows = []
    for lab, h0, h1 in bands:
        pts = [p for p in U if h0 - 1e-4 <= p[1] <= h1 + 1e-4]
        if not pts:
            continue
        rows.append(dict(band=lab, hM=[round(h0, 3), round(h1, 3)],
                         xM=[round(min(p[0] for p in pts), 3), round(max(p[0] for p in pts), 3)],
                         zM=[round(min(p[2] for p in pts), 3), round(max(p[2] for p in pts), 3)]))
    return rows


def report(o, info):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    mt, ot = RM.mune_top_roof(o)
    print("GOKUSHO %s W(X)%.3f × H(Y)%.3f × D(Z)%.3f X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), min(xs), max(xs), min(ys), max(ys),
             min(zs), max(zs), tris))
    print("  棟高(平場の設計面 → 大棟の上端・棟の中央 ±0.6)%.3f / 鬼の頂 %.3f / 棟飾りの丈 %.3f" % (mt, ot, ot - mt))
    # 北面の口の位置(Unity X)と面
    hu, hv = info["hu"], info["hv"]
    # ⚠ 軸部の帯は軒先(3.00)と破風の垂れより下で切る — 上端を桁にすると軒・ケラバの頂点が混ざる
    rows = band_outline(o, [("基壇", -0.30, info["floor"]), ("軸部(床〜2.70)", info["floor"] + 0.01, 2.70),
                            ("屋根", 2.70, max(ys))])
    for r in rows:
        print("  外形 %-14s h %s X %s Z %s" % (r["band"], r["hM"], r["xM"], r["zM"]))
    print("  北面: 壁の芯 Z %.3f / 壁の面 Z %.3f / 柱の外面 Z %.3f / 基壇の面 Z %.3f / 口の柱芯 X %.3f〜%.3f(東の柱 = 東面の柱芯 X %.3f)"
          % (hv, hv + G["kabeT"] / 2.0, hv + G["post"] / 2.0, hv + G["kidanOut"], info["gate"][1], info["gate"][2], hu))
    bad = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bad else "⛔ %s" % bad))
    return not bad, dict(W=max(xs) - min(xs), H=max(ys) - min(ys), D=max(zs) - min(zs), mune=mt, oni=ot, outline=rows)


def soffit(o, info):
    """軒・ケラバの帯の下から真上へ — 瓦(`roof`)に先に当たる/空へ抜ける を数える。"""
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    mats = o.data.materials
    hu, hv = info["hu"], info["hv"]
    x1, z1 = hu + G["eave"] - 0.05, hv + G["keraba"] - 0.05
    cu = miss = tot = 0
    n = 48
    for i in range(n + 1):
        for j in range(n + 1):
            X = -x1 + 2 * x1 * i / float(n)
            Z = -z1 + 2 * z1 * j / float(n)
            if abs(X) < hu + 0.10 and abs(Z) < hv + 0.10:
                continue
            loc, nrm, idx, dist = bvh.ray_cast(Vector((-X, -Z, 2.0)), Vector((0, 0, 1)), 10.0)
            tot += 1
            if idx is None:
                miss += 1; continue
            m = mats[o.data.polygons[idx].material_index]
            if m and m.name.split('.')[0] == "roof":
                cu += 1
    ok = cu == 0 and miss == 0
    print("  検算 軒裏・ケラバ裏 真上の光線 %d: 瓦に先に当たる %d / 空へ抜ける %d %s" % (tot, cu, miss, "⭕" if ok else "⛔"))
    return ok


def shots(o, info):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.005))
    hu, hv = info["hu"], info["hv"]
    out = []

    def one(cam, look, fn, res=(1600, 1100), ortho=None):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_gokusho_ikko_%s.png" % fn)
        V.render(f); out.append(f)
    # Blender = (−X, −Z, Y)
    one((-13.0, -15.0, 8.5), (0.0, 0.0, 2.6), "ne_oblique")                  # 北東(口と東面)
    one((13.0, 15.0, 8.5), (0.0, 0.0, 2.6), "sw_oblique")                    # 南西(勝手口・西面)
    gx = -(info["gate"][1] + info["gate"][2]) / 2.0
    one((gx - 1.0, -(hv + 6.0), 1.7), (gx, -hv, 2.0), "north_gate", res=(1400, 1100))
    one((-(hu + 0.3), -(hv - 1.0), 1.2), (-(hu + 0.6), -(hv + 0.2), 3.3), "soffit_ne", res=(1400, 1100))
    one((0.0, -(hv + 16.0), 2.6), (0.0, 0.0, 2.6), "north_elev", ortho=11.0)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    name = "Sanno_Gokusho_%gx%gken_%dx%d" % (NU, NV, round(NU * K * 1000), round(NV * K * 1000))
    V.reset()
    o, info = build(name)
    ok, meas = report(o, info)
    sok = soffit(o, info)
    shotfiles = []
    if "--render" in argv:
        shotfiles = shots(o, info)
    for f in shotfiles:
        print("RENDER " + f)
    if not (ok and sok) and "--allow" not in argv:
        raise SystemExit("[gokusho] ⛔ 材か軒裏の検算に落ちた")
    if "--no-export" not in argv:
        o.location = (0.0, 0.0, 0.0)
        path = os.path.join(OUT, o.name + ".fbx")
        V.export_fbx([o], path)
        print("[gokusho] 書き出し %s" % path)


if __name__ == "__main__":
    main()
