# -*- coding: utf-8 -*-
"""山王権現社の**楼門(隨身門)と坂下の門(仁王門)** — 三間一戸・単層・入母屋造・組物付き。

    blender --background --python Tools/Blender/build_sanno_romon.py -- [--render] [--no-export]

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指図 `docs/Sashizu/sanno_sashizu.json` の `bom`「楼門(三間一戸)」は Japanese Castle の
`Yaguramon A` で代用中。⛔ 城郭の櫓門で、据わる外形が `gates[].plan` の約2倍・通り抜けが
長辺側(在庫方 2026-09-13「在庫に適う物なし・新造」)。

━━━ 1点で2基を兼ねる ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`gates[]` の楼門と坂下の門は **`bom` が同じ行**(楼門(三間一戸))・**`plan` が同じ**(du 2 × dv 3)・
`monguchiKen` も同じ。違いは**安置像**(随身/仁王・二天の両論)だけで、像は作らない ⇒ 幾何が同じ。
⇒ **FBX は1本**。`main()` が指図から2基の plan と bom を読み、食い違えば止まる
(⛔ 指図が作り分けへ改まったら黙って兼用しない)。

━━━ 軸(指図 2026-09-13「部材の軸」= `bom[楼門].axis`)━━━━━━━━━━━━━━━━━━━━━━━
・**ピボット = 門の芯・敷居の高さ**(Y=0 = 基壇の天端 = 通路の踏み面)。基壇は下へ 0.60 根入れ。
・**通り抜け = ローカル X** / **正面 = ローカル +X**(両脇間の連子窓が +X 面、扉は −X へ開く)。
・論理 (u=通り抜け・正面が +, v=門の幅, h=上) で組み、`build_sanno_shaden` の写像
  (`BX`/`q`、Rz180° = 行列式 +1)で落とす ⇒ **Unity ローカル = (u, h, v)**。
・焼いた直後に**メッシュから**検算する(`check_axes`)— 通り抜けの素通し・連子の偏り・
  扉の開く向き。陰性試験(X 鏡映で必ず止まる)を毎回回す。

━━━ 寸法の出所 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・平面(間数)= 指図 `gates[].plan`(du = 梁間 = 通り抜けの奥行 / dv = 桁行 = 幅)、
  1間 = `const.ken`、戸口 = `monguchiKen`。⛔ ここに書かない。
・⚠ 柱間は江戸間の均等割り【U 要改訂 — `_pending`「境内の柱間モジュール」】。明治16年実測の
  間口 約11m とは合わない(指図が承知の上で推定値のまま進める裁定 2026-09-09)。
・下の `G` は**すべて【U 類型で埋めた設計値】**。
"""
import bpy, sys, os, math, json
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
BOM_ROW = "楼門(三間一戸)"

# ==========================================================================
# 高さ・部材の丈 — ⛔ すべて【U 類型で埋めた設計値】(史料は数を言わない)
# ==========================================================================
G = dict(
    colH=3.10,      # 基壇天端 → 頭貫上端
    kumi=0.47,      # 頭貫上端 → 軒先の名目平面(出組)。⚠ 1.10 だと垂木の下端が壁通りで丸桁の
                    #   0.61 上を通り、組物と屋根の間に空が抜けた(2026-09-13 立面で実見)。
                    #   丸桁は `SH.kumimono` で頭貫上端+0.95 固定、屋根は反りで壁通り(軒先から
                    #   eave−0.30)に z(d)≈0.57 上がる ⇒ kumi ≈ 0.95 − 0.57 + 0.105 − 0.02
    kumiKind="degumi",   # 組物の格【U】— 名所図会の「深い組物の帯」を出組で埋めた
    colD=0.36,      # 側柱(総円柱)
    honD=0.42,      # 本柱(扉を吊る中の通り)
    uchinori=2.40,  # 内法(長押の位置)
    koshi=0.95,     # 脇間の腰(連子窓の窓台)
    eave=1.40,      # 軒の出
    gf=0.45,        # 入母屋の妻の立上り比(社殿と同じ)
    sobanH=0.15,    # 礎盤の丈
    kidanDepth=0.60,  # 基壇の根入れ(天端 = Y0 から下へ)
    kidanSkirt=0.45,  # 基壇の出(側柱の芯から)
)


def sashizu_plan():
    with open(SH.SASHIZU) as f:
        d = json.load(f)
    K = float(d["const"]["ken"])
    gs = [g for g in d["gates"] if g.get("bom") == BOM_ROW]
    if len(gs) < 2:
        raise SystemExit("[romon] ⛔ bom『%s』の門が %d 基しかない" % (BOM_ROW, len(gs)))
    keys = {(g["plan"]["du"], g["plan"]["dv"], g.get("monguchiKen")) for g in gs}
    if len(keys) != 1:
        raise SystemExit("[romon] ⛔ 同じ bom の門で plan/monguchiKen が違う — 兼用できない: %s"
                         % [(g["name"], g["plan"], g.get("monguchiKen")) for g in gs])
    du, dv, mk = keys.pop()
    row = next(b for b in d["bom"] if b.get("部材") == BOM_ROW)
    print("[romon] 兼用する門: %s / plan du %s × dv %s / 戸口 %s 間 / 1間 %.3f / axis %s"
          % ([g["name"] for g in gs], du, dv, mk, K, row.get("axis")))
    if row.get("axis") != {"pass": "X", "front": "+X"}:
        raise SystemExit("[romon] ⛔ bom の axis が宣言と違う: %s" % row.get("axis"))
    return dict(K=K, du=int(du), dv=int(dv), monguchi=float(mk),
                roof=row.get("屋根", ""), names=[g["name"] for g in gs])


# ==========================================================================
# 組み立て(論理 u=通り抜け・正面+ / v=幅 / h=上)
# ==========================================================================
def build(P, name):
    K = P["K"]
    hu, hv = P["du"] * K / 2.0, P["dv"] * K / 2.0
    if abs(P["monguchi"] - 1.0) > 1e-6 or P["dv"] != 3:
        raise SystemExit("[romon] ⛔ 三間一戸・中央一間の戸口しか組めない(dv=%s 戸口=%s)"
                         % (P["dv"], P["monguchi"]))
    b = hv / 3.0                         # 中の間の半幅(= 本柱の v)
    ms, uv = SH.mats()
    W, WC, DW = SH.W, SH.WC, SH.DW
    p = GR.palette()
    M = VM.Mesh()
    colH, UC = G["colH"], G["uchinori"]
    z_sill = 0.24                        # 地覆の天端 / 脇間の床下

    # --- 基壇(切石・天端 Y0 から根入れ)+ 礎盤 ---------------------------
    stones = SH.kamebara(hu, hv, G["kidanDepth"], name + "_kidan",
                         batter=0.10, skirt=G["kidanSkirt"], course=0.30, th=0.42)
    for o in stones:
        o.data.transform(Matrix.Translation((0.0, 0.0, -G["kidanDepth"])))
        o.data.update()
    us = SH.bay_lines(hu, P["du"])      # [-hu, 0, hu]
    vs = SH.bay_lines(hv, P["dv"])      # [-hv, -b, b, hv]
    pts = [(uu, vv) for uu in us for vv in vs]          # 12本(八脚門の割り)
    stones += SH.soban(pts, 0.0, G["sobanH"], 0.27, name + "_soban")

    # --- 柱: 側柱10本(四周)+ 本柱2本(中の通りの内側)---------------------
    SH.columns(M, hu, hv, P["du"], P["dv"], 0.0, colH, G["colD"], uv["wood"], W,
               base=G["sobanH"])
    for sg in (-1, +1):
        SH.cyl(M, 0.0, sg * b, G["sobanH"], colH, G["honD"] / 2.0, uv["wood"], W,
               n=12, taper=0.94)

    # --- 組物(出組)+ 頭貫 + 台輪 + 丸桁、中の通りの頭貫 ----------------
    SH.kumimono(M, us, vs, 0.0, colH, G["kumi"], uv["wood_h"], W, kind=G["kumiKind"])
    SH.box3(M, -0.09, 0.09, -hv - 0.10, hv + 0.10, colH - 0.30, colH, uv["wood_h"], W,
            grain="v")
    # 軒小壁(組物の間を塞ぐ板。⛔ 無いと組物の帯の隙から反対側の空が素通しで見える
    #   — 2026-09-13 の正面立面で実見)。台輪の上 → 丸桁の下、壁通りに置く
    for vv in (vs[0], vs[-1]):
        SH.box3(M, us[0], us[-1], vv - 0.04, vv + 0.04, colH + 0.10, colH + 0.76,
                uv["wall"], WC, grain="u")
    for uu in (us[0], us[-1]):
        SH.box3(M, uu - 0.04, uu + 0.04, vs[0], vs[-1], colH + 0.10, colH + 0.76,
                uv["wall"], WC, grain="v")
    # 繋ぎ虹梁(通路の両側の通りで、側柱 → 本柱 → 側柱)
    for sg in (-1, +1):
        SH.kouryou(M, -hu, hu, sg * b, colH - 0.62, colH - 0.62, 0.20, 0.30,
                   uv["wood_h"], W, n=10, sag=0.10)
    # 小壁 + 長押 + 連子欄間(四周)
    SH.kokabe(M, us, vs, 0.0, colH, uv["wall"], WC, uc=UC, renji=(uv["wood"], W))
    # 鏡天井(組物の内側を塞ぐ — 屋根の裏と空を見せない)
    SH.box3(M, -hu + 0.10, hu - 0.10, -hv + 0.10, hv - 0.10, colH + 0.02, colH + 0.06,
            uv["wood_h"], W, grain="u")

    # --- 両脇間(v ∈ ±[b, hv])-------------------------------------------
    r_s, r_h = G["colD"] / 2.0, G["honD"] / 2.0
    for sg in (-1, +1):
        v_in, v_out = sg * b, sg * hv
        a0, a1 = sorted((v_in + sg * r_h, v_out - sg * r_s))   # 脇間の内法(v)
        # 地覆(四辺)
        SH.box3(M, -hu, hu, v_out - 0.09, v_out + 0.09, 0.0, z_sill, uv["wood_h"], W, grain="u")
        SH.box3(M, -hu, hu, v_in - 0.09, v_in + 0.09, 0.0, z_sill, uv["wood_h"], W, grain="u")
        for uu in (-hu, hu):
            SH.box3(M, uu - 0.09, uu + 0.09, a0, a1, 0.0, z_sill, uv["wood_h"], W, grain="v")
        # 床(像の間。⛔ 像は作らない)
        SH.box3(M, -hu + 0.09, hu - 0.09, a0, a1, z_sill - 0.06, z_sill + 0.06,
                uv["wood_h"], W, grain="u")
        # 正面(+u)= 腰板 + 連子窓 ⭐ 正面の合図
        SH.panel_ita(M, a0, a1, "v", hu, z_sill, G["koshi"], uv["wood"], W)
        SH.box3(M, hu - 0.08, hu + 0.08, a0, a1, G["koshi"], G["koshi"] + 0.10,
                uv["wood_h"], W, grain="v")                       # 窓台
        z_r0, z_r1 = G["koshi"] + 0.10, UC - 0.13
        n = max(6, int(round((a1 - a0) / 0.115)))
        for i in range(1, n):
            c = a0 + (a1 - a0) * i / float(n)
            SH.box3(M, hu - 0.035, hu + 0.035, c - 0.028, c + 0.028, z_r0, z_r1,
                    uv["wood"], W, grain="h")                    # 連子子
        # 背面(−u)= 板壁 / 外の側面 = 板壁 / 通路側 = 板壁
        SH.panel_ita(M, a0, a1, "v", -hu, z_sill, UC, uv["wood"], W)
        for (u0, u1) in ((-hu + r_s, -r_h), (r_h, hu - r_s)):
            SH.panel_ita(M, u0, u1, "u", v_out, z_sill, UC, uv["wood"], W)
            SH.panel_ita(M, u0, u1, "u", v_in, z_sill, UC, uv["wood"], W)

    # --- 中の間: 本柱に吊る板扉2枚。⭐ **背面(−u)へ開き、通路側の板壁に沿う** ---
    leaf = b - r_h - 0.03
    for sg in (-1, +1):
        vv = sg * (b - r_h - 0.04)
        u0, u1 = -0.08 - leaf, -0.08
        SH.box3(M, u0, u1, vv - 0.025, vv + 0.025, 0.05, UC - 0.16, uv["itado"], DW,
                grain="h")
        vin = vv - sg * 0.025                              # 通路側の面
        for zz in (0.30, (UC - 0.16) / 2.0, UC - 0.40):   # 端喰の桟
            lo, hi = sorted((vin, vin - sg * 0.035))
            SH.box3(M, u0 + 0.03, u1 - 0.03, lo, hi, zz, zz + 0.09, uv["wood_h"], W,
                    grain="u")
    # 中の通りの内法(扉の上の鴨居)
    SH.box3(M, -0.10, 0.10, -b, b, UC - 0.16, UC, uv["wood_h"], W, grain="v")

    # --- 屋根(反り入母屋・大棟は v = 幅の向き)+ 垂木 ----------------------
    ez = colH + G["kumi"]
    s = dict(eave=G["eave"], gf=G["gf"])
    sori = SH.Sori(hu + G["eave"])
    body = M.to_object(name + "_body", ms)
    taru = SH._taruki_obj(name, hu, hv, ez, s, uv, ms, sori)
    roof = SH.irimoya(name + "_roof", hu, hv, G["eave"], ez, G["gf"], p, sori)

    V.dedup_materials()
    o = V.join([body, taru, roof] + stones, name)
    V.set_origin(o, (0.0, 0.0, 0.0))                    # 門の芯・敷居の高さ
    return o, dict(hu=hu, hv=hv, b=b, ez=ez, ridge=ez + sori.z(sori.half))


# ==========================================================================
# 検算 — ⛔ 期待値はメッシュから(規則19・EDO-0161)
# ==========================================================================
def check_axes(o, hu, hv, b, label, quiet=False):
    uvw = SH.unity_verts(o)                     # (X, Y, Z) Unity ローカル
    mats = o.data.materials
    clear = G["honD"] / 2.0 + 0.30              # 戸口の芯からの見込み
    ylo, yhi = 0.35, G["uchinori"] - 0.20
    blockX = sum(1 for (x, y, z) in uvw if abs(z) < clear and ylo < y < yhi)
    blockZ = sum(1 for (x, y, z) in uvw if abs(x) < clear and ylo < y < yhi)
    pass_x = blockX == 0 and blockZ > 0
    # 正面の符号: 脇間の +X 面と −X 面の、窓の高さの頂点の数(連子子の数が効く)
    zr = lambda z: b + 0.25 < abs(z) < hv - 0.25
    # ⚠ 連子子は箱なので頂点は**上下の端**(窓台の上 / 長押の下)にしか無い — 窓はその両端を含める
    #   (帯の中だけを見て 0 対 0 で落ちた。2026-09-13)
    yr = lambda y: G["koshi"] + 0.05 < y < G["uchinori"] - 0.10
    fp = sum(1 for (x, y, z) in uvw if zr(z) and yr(y) and x > hu - 0.12)
    fm = sum(1 for (x, y, z) in uvw if zr(z) and yr(y) and x < -hu + 0.12)
    front_px = fp > 3 * max(1, fm)
    # 扉(door wall)の面の重心: 背面(−X)へ開いているか。扉の長手は X
    di = [i for i, m in enumerate(mats) if m and m.name.split('.')[0] == "door wall"]
    dv_ = set()
    for pg in o.data.polygons:
        if pg.material_index in di:
            dv_.update(pg.vertices)
    dx = [uvw[i][0] for i in dv_]; dz = [uvw[i][2] for i in dv_]
    door_ok = bool(dx) and (sum(dx) / len(dx) < -0.2)
    door_long_x = bool(dx) and (max(dx) - min(dx)) > 3 * 0.05
    ok = pass_x and front_px and door_ok
    if not quiet:
        print("  検算[%s] 通り抜け=X %s(X の通路に頂点 %d / Z の通路に %d)"
              % (label, "⭕" if pass_x else "⛔", blockX, blockZ))
        print("  検算[%s] 正面=+X  %s(連子の高さの頂点 +X面 %d / −X面 %d)"
              % (label, "⭕" if front_px else "⛔", fp, fm))
        if dx:
            print("  検算[%s] 扉        %s 重心 X=%+.3f(背面へ開く)/ 長手 X %.2f m・"
                  "吊元 |Z| %.3f〜%.3f"
                  % (label, "⭕" if door_ok else "⛔", sum(dx) / len(dx),
                     max(dx) - min(dx), min(abs(z) for z in dz), max(abs(z) for z in dz)))
        else:
            print("  検算[%s] 扉 ⛔ door wall の面が無い" % label)
    return ok and door_long_x


def report(o, info):
    uvw = SH.unity_verts(o)
    xs = [t[0] for t in uvw]; ys = [t[1] for t in uvw]; zs = [t[2] for t in uvw]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    print("ROMON %s Unity W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] "
          "Z[%.3f,%.3f] tris=%d mats=%s"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), tris,
             [m.name for m in o.data.materials]))
    body = [t for t in uvw if 0.2 < t[1] < G["colH"] - 0.4]
    print("  柱の外面まで(内法の帯) X[%.3f,%.3f] Z[%.3f,%.3f] / 柱芯 X ±%.3f Z ±%.3f"
          % (min(t[0] for t in body), max(t[0] for t in body),
             min(t[2] for t in body), max(t[2] for t in body), info["hu"], info["hv"]))
    print("  軒高(名目)%.3f / 大棟(瓦場の頂)%.3f / 上端 %.3f / 基壇の根入れ下端 %.3f"
          % (info["ez"], info["ridge"], max(ys), min(ys)))
    print("  指紋 %s" % SH.fingerprint(o))
    return tris


def selftest(o, info):
    """⛔ 0件は合格ではない — X を鏡映すると必ず止まるか。"""
    c = o.copy(); c.data = o.data.copy()
    bpy.context.collection.objects.link(c)
    c.data.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))   # Blender X = −Unity X
    c.data.update()
    hit = check_axes(c, info["hu"], info["hv"], info["b"], "鏡映", quiet=True)
    bpy.data.objects.remove(c, do_unlink=True)
    print("  陰性試験 X 鏡映 %s" % ("⛔ 通ってしまった" if hit else "⭕ 止まった"))
    return not hit


# ==========================================================================
# 検証レンダ(カメラは bbox から)
# ==========================================================================
def shots(o, info):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    top = mx.z
    span = max(mx.x - mn.x, mx.y - mn.y)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.02))
    out = []

    def one(cam, look, fn, ortho=None, res=(1600, 1200)):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_romon_%s.png" % fn)
        V.render(f); out.append(f)

    # Unity +X(正面)= Blender −X / Unity −Z(南)= Blender +Y
    one((-40.0, 0.0, top * 0.5), (0.0, 0.0, top * 0.5), "front", ortho=top * 1.35)
    one((0.0, 40.0, top * 0.5), (0.0, 0.0, top * 0.5), "side", ortho=top * 1.35)
    one((-span * 1.25, span * 0.95, top * 1.45), (0.0, 0.0, top * 0.35), "oblique")
    one((-9.0, 2.6, 1.6), (0.0, 0.0, 2.3), "near_front")
    one((7.5, -3.2, 1.6), (0.0, 0.0, 2.0), "near_back")
    one((-12.0, 9.0, 1.7), (0.0, 0.0, 3.2), "eye_oblique")
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    P = sashizu_plan()
    name = "Sanno_Romon_%dx%dken" % (P["du"], P["dv"])
    print("[romon] 屋根 = 在庫の本瓦(`roof`)— bom: %s" % P["roof"][:60])
    V.reset()
    o, info = build(P, name)
    tris = report(o, info)
    if not check_axes(o, info["hu"], info["hv"], info["b"], "正"):
        raise SystemExit("[romon] ⛔ 軸の検算に落ちた")
    if not selftest(o, info):
        raise SystemExit("[romon] ⛔ 陰性試験に失敗")
    bad = [m.name for m in o.data.materials if m and m.name.split('.')[0]
           not in ("wood", "wall C", "door wall", "roof", "roof ornaments", "Kirishi")]
    print("  材 %s %s" % ([m.name for m in o.data.materials], "⭕" if not bad else "⛔ %s" % bad))
    if bad:
        raise SystemExit("[romon] ⛔ 想定外の材")
    if "--render" in argv:
        for f in shots(o, info):
            print("RENDER " + f)
    if "--no-export" not in argv:
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)
        print("[romon] 書き出し %s (tris %d)" % (path, tris))


if __name__ == "__main__":
    main()
