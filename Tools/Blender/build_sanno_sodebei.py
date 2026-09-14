# -*- coding: utf-8 -*-
"""山王権現社の**袖塀(回廊の翼 ↔ 楼門の側面)** — 瓦葺の築地塀(土塀)・長さ 4.2 m・両端を袖瓦で塞ぐ。

    blender --background --python Tools/Blender/build_sanno_sodebei.py -- [--len 4.2] [--render] [--no-export]

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
明治16年実測図 第2稿の読み(考証 2026-09-14): 回廊の翼は楼門に**取り付かない**。翼の妻と楼門の側面の間に
離れ 4.2 ± 0.5 m【A】があり、【S 名所図会・山王 コマ7】は「翼の屋根は妻で切れ、隨身門との間に**低い屋根付きの
袖塀**」を、【S 山王御宮絵図 コマ25】は「翼は別の矩形で、楼門とは**細い一本の部材**だけでつながる」を描く。
在庫の築地塀は 2 m モジュール(`Dobei2m` / `Tsuijibei2m`)で、4.2 m を割り切れない(継ぎ目で瓦の割付が崩れる)。

━━━ 形の判断 — 瓦葺の築地塀(板塀にしない)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・名所図会が**屋根**を描く。板塀の笠木は屋根に描かれない(同じ図の前庭の囲い・仁王門の袖は屋根無し)。
・御宮絵図は建物(翼・楼門)と別の**一本の線** = 棟を持たない壁。⇒ 壁の上に屋根が載る物。
・翼(銅瓦葺【U】)と楼門(本瓦)の間を塞ぐ格の塀で、板塀へ格を下げる根拠が無い。
⇒ **瓦葺の築地塀**【U 類型 — 形】。丈・腰板・軒の出は既存の練塀 `build_dobei.py`(`Dobei2m`)の断面のまま
  【U 類型 — 丈】。⛔ 木の破風を付けない(築地塀は土と瓦 — README)。

━━━ 作り(`build_dobei` の断面・材・瓦場をそのまま使う。⛔ ゼロから作らない)━━━━━━━━━━━━━━━━━━━━━━
・走りだけ `LEN` に伸ばす。瓦場の割付は**走りの中心に対称**に振る(端に 0.096 m ずつ残る端数は袖瓦が覆う)。
・両端 = 袖瓦(大棟の脇で止める)+ 大棟(`roof top x1` は小口が開いている)の小口を漆喰で2段に塗り籠める。
・材 = `Wall Exterior Defence`(Japanese Castle の漆喰)/ `Fence_B_01`(腰板)/ `roof` / `roof ornaments`。

━━━ 軸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unity ローカル: 走り = X ∈ [−LEN/2, +LEN/2] / 高さ = Y(0 = 足元) / 厚み = Z(芯を挟んで対称・表裏の別なし)。
**ピボット = 走りの中心・足元(楼門の敷居と同じ高さ)**。楼門の側面から南北へ走らせるときは yaw 90。

━━━ 当たり(`--render` のたびに刷る)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・楼門 = 実 FBX(`ROMON`)へ塀の頂点から真上に光線を当てて、最初に当たる材までの離れを測る。
  塀は楼門の芯 X=0 の通り、側柱の外面 |Z| = 3.81 + 0.18 から翼へ走ると置く【U】。
・回廊 = 部材が無いので設計値(床 29.0 = 敷居 +0.70 から 軒 2.10 / 桁 2.60 / 棟 4.02)で、梁間 4.2 の
  芯に塀が載ると置き、妻の出 `KAIRO_KERABA` と屋根の懐 `KAIRO_ROOF_T` を【U】で見る。
"""
import bpy, sys, os, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_dobei as DB

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")
ROMON = os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno",
                     "Sanno_Romon_2x3ken_5750x7620_k1075-1075-1740-1740.fbx")
ROMON_FACE_Z = 3.81 + 0.18     # 楼門の側柱の外面(柱芯 7.62/2 + 側柱の半径)
KAIRO_UP = 0.70                # 回廊の床 29.0 − 楼門の敷居 28.3
KAIRO = dict(noki=2.10, keta=2.60, mune=4.02, half=2.10)   # 設計値(床から)。half = 梁間 4.2 の半分
KAIRO_KERABA = 0.60            # 【U】回廊の妻の出(翼の妻から袖塀の上へ)
KAIRO_ROOF_T = 0.35            # 【U】回廊の屋根の懐(瓦の面 → 垂木の下端)
ALLOWED = ("Wall Exterior Defence", "Fence_B_01", "roof", "roof ornaments")


def build(name, LEN):
    DB.L = LEN                           # ⭐ `slab` / `wall_cap` は走りをモジュール変数 L で読む
    nk = LEN / DB.MOD_LEN
    V.reset()
    wall, WALL_UV = DB.castle_mat(DB.PLASTER_SRC, DB.PLASTER_MAT, "plaster")
    wood, W_UV = DB.vk_mat(DB.WOOD_SRC, DB.WOOD_MAT, "wood")
    WALL_UV = DB.crop(WALL_UV, DB.CROP_PLASTER, DB.CROP_PLASTER_HI)
    W_UV = DB.crop(W_UV, DB.CROP_WOOD)
    if wood is None or wall is None:
        raise SystemExit("[sodebei] ⛔ マテリアルが取れない")
    m = DB.Mesh()
    # ⚠ タイリングの分割数は走りに比例させる(2 m の本数のままだと木目と漆喰の斑が 2 倍に伸びる)
    DB.slab(m, 0.0, DB.H_SHITAMI, DB.T_SHITAMI, W_UV, 0, int(round(3 * nk)), cap_top=False)
    DB.slab(m, DB.H_SHITAMI, DB.H_SHITAMI + DB.H_NUKI, DB.T_NUKI, W_UV, 0, int(round(4 * nk)), cap_top=True)
    e = DB.T_ROOF / 2.0
    h_wall_top = DB.H_KETA + (e - DB.T_WALL / 2.0) * DB.RATIO
    DB.slab(m, DB.H_SHITAMI + DB.H_NUKI, h_wall_top, DB.T_WALL, WALL_UV, 1, int(round(2 * nk)), cap_top=False)
    DB.wall_cap(m, 1, WALL_UV, e, DB.T_WALL / 2.0, DB.H_KETA)
    body = m.build(name + "_body", [wood, wall])
    z_ridge = DB.H_KETA + e * DB.RATIO
    off = (LEN - DB.MOD_LEN * math.floor(LEN / DB.MOD_LEN + 1e-9)) / 2.0   # 割付を中心に対称へ
    pieces = [body]
    f1 = DB.tile_field([(0.0, -e), (LEN, -e), (LEN, 0.0), (0.0, 0.0)], (off, -e), 90, DB.H_KETA, name + "_S")
    f2 = DB.tile_field([(LEN, e), (0.0, e), (0.0, 0.0), (LEN, 0.0)], (off, e), 270, DB.H_KETA, name + "_N")
    pieces += [q for q in (f1, f2) if q]
    roofmat = bpy.data.materials.get("roof")
    # ⚠ `sample_uv_bright` の ±0.04 の矩形は `roof` アトラスの木の帯(野地)に掛かり、袖垂れが茶色の板に
    #   なった(2026-09-14 小口のレンダで実見)。⭕ `Dobei2m_End` と同じ「高い面」の点の小矩形に揃える
    ru = V.sample_uv(DB.ROOF_MOD, pick_high=True)
    rrect = (ru[0] - 0.01, ru[1] - 0.01, ru[0] + 0.01, ru[1] + 0.01)
    mg = DB.Mesh()
    stop = DB.W_MUNE / 2.0 + 0.03        # ⛔ 袖瓦に大棟を跨がせない(README)
    for x_in, x_out in ((DB.W_SODE, 0.0), (LEN - DB.W_SODE, LEN)):
        DB.sode_gawara(mg, 0, rrect, x_in, x_out, e, DB.H_KETA, z_ridge, stop=stop)
    pieces.append(mg.build(name + "_sode", [roofmat or wood]))
    mune = DB.ridge((0.0, 0.0, z_ridge - DB.SEAT_MUNE), (LEN, 0.0, z_ridge - DB.SEAT_MUNE),
                    name + "_mune", DB.W_MUNE, DB.H_MUNE)
    for q in mune:
        q.data = q.data.copy()
        V.sel([q]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        DB.clip_convex(q, [(0.0, -1.0), (LEN, -1.0), (LEN, 1.0), (0.0, 1.0)])
    pieces += [q for q in mune if len(q.data.polygons) > 0]
    # 大棟の小口を漆喰で2段に塗り籠める(熨斗 = 幅広 / 冠 = 幅狭)。⛔ 瓦の材で塞がない(木の帯に落ちる)
    zb = z_ridge - DB.SEAT_MUNE
    for x in (0.02, LEN - 0.02):
        for k, (w, h0, h1) in enumerate(((DB.W_MUNE + 0.02, zb - 0.02, zb + 0.13),
                                         (DB.W_MUNE * 0.62, zb + 0.13, zb + DB.H_MUNE - 0.01))):
            c = V.box("%s_kuchi%d%d" % (name, int(x > 1), k), (0.04, w, h1 - h0),
                      (x, 0.0, (h0 + h1) / 2.0), wall)
            V.set_uv_rect(c, WALL_UV, axes=('y', 'z'))
            pieces.append(c)
    V.dedup_materials()
    o = V.join(pieces, name)
    V.set_origin(o, (LEN / 2.0, 0.0, 0.0))            # 走りの中心・足元
    return o


def unity_verts(o):
    return [(-v.co.x, v.co.z, -v.co.y) for v in o.data.vertices]


def report(o, LEN):
    U = unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [mm.name.split('.')[0] for mm in o.data.materials if mm]
    print("SODEBEI %s Unity W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d mats=%s"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), min(xs), max(xs),
             min(ys), max(ys), min(zs), max(zs), tris, mats))
    ok = True
    # 検算1: 走りの外形が LEN(棟・袖瓦が端から出ていない)
    if abs((max(xs) - min(xs)) - LEN) > 0.005 or abs(max(xs) + min(xs)) > 0.005:
        print("  検算 走り ⛔ 外形 %.4f が LEN %.3f と違う/中心がずれる" % (max(xs) - min(xs), LEN)); ok = False
    else:
        print("  検算 走り ⭕ X[%.4f,%.4f] = LEN %.3f・中心 0" % (min(xs), max(xs), LEN))
    # 検算2: 厚みが対称(表裏の別なし)
    if abs(max(zs) + min(zs)) > 0.01:
        print("  検算 厚みの対称 ⛔ Z[%.3f,%.3f]" % (min(zs), max(zs))); ok = False
    else:
        print("  検算 厚みの対称 ⭕ Z[%.3f,%.3f]" % (min(zs), max(zs)))
    # 検算3: 両端の小口が塞がっている — 端から 0.05 以内に、壁の高さの帯と棟の帯の両方に面がある
    for sgn in (-1, +1):
        ex = sgn * LEN / 2.0
        near = [t for t in U if abs(t[0] - ex) < 0.05]
        wall_band = any(0.3 < t[1] < DB.H_KETA - 0.2 and abs(t[2]) < DB.T_WALL / 2 + 0.01 for t in near)
        top_band = any(t[1] > DB.H_KETA + 0.25 for t in near)
        print("  検算 小口(%s端) %s 壁の帯 %s / 棟の帯 %s" % ("−X" if sgn < 0 else "+X",
              "⭕" if wall_band and top_band else "⛔", wall_band, top_band))
        ok = ok and wall_band and top_band
    bad = [mm for mm in mats if mm not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bad else "⛔ %s" % bad))
    return ok and not bad, tris, max(ys)


def selftest(o, LEN):
    """⛔ 0件は合格ではない — 片端の小口を消すと検算3が止まるか。"""
    c = o.copy(); c.data = o.data.copy()
    bpy.context.collection.objects.link(c)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(c.data)
    # Unity X = −Blender X ⇒ Unity の +X 端 = Blender の −LEN/2
    kill = [f for f in bm.faces if all(abs(v.co.x + LEN / 2.0) < 0.05 for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    # 端に接する長い面(壁・瓦場)の頂点は残るので、端から 0.05 の頂点も消して「開いた端」を作る
    edge_v = [v for v in bm.verts if abs(v.co.x + LEN / 2.0) < 0.05]
    bmesh.ops.delete(bm, geom=edge_v, context='VERTS')
    bm.to_mesh(c.data); bm.free()
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        hit, _, _ = report(c, LEN)
    bpy.data.objects.remove(c, do_unlink=True)
    print("  陰性試験 +X 端を開ける %s" % ("⛔ 通ってしまった" if hit else "⭕ 止まった"))
    return not hit


def clearances(o, LEN):
    """塀の頂点から真上へ — 楼門の実 FBX の最初の材までの離れ、回廊の設計値の屋根裏までの離れ。"""
    objs = VM.import_fbx_abs(ROMON)
    rm = V.join(objs, "romon_check") if len(objs) > 1 else objs[0]
    bvh = BVHTree.FromObject(rm, bpy.context.evaluated_depsgraph_get())
    U = unity_verts(o)
    worst_r, worst_k, pen = None, None, []
    for (x, y, z) in U:
        # 塀のローカル → 楼門のローカル(+Z の側。対称なので −Z も同じ): 走り X → 楼門 Z / 厚み Z → 楼門 X
        Xr, Yr, Zr = z, y, ROMON_FACE_Z + LEN / 2.0 + x
        h = bvh.ray_cast(Vector((-Xr, -Zr, Yr + 1e-4)), Vector((0.0, 0.0, 1.0)))
        # ⚠ 足元の頂点は礎盤(丈 0.15)に当たる — それは下の「礎盤への食い込み」で別に数える。
        #   軒との当たりは地面から 1.0 m より上の材だけで測る(0.150 が最小と出て軒の値が隠れた)
        if h[0] is not None and h[0].z > 1.0:
            g = h[0].z - Yr
            if worst_r is None or g < worst_r[0]:
                worst_r = (g, Xr, Yr, Zr, h[0].z)
        # 回廊: 翼の妻 = 楼門の面 + LEN、妻の出 KAIRO_KERABA の下
        if Zr >= ROMON_FACE_Z + LEN - KAIRO_KERABA:
            ax = min(abs(Xr), KAIRO["half"])
            surf = KAIRO["mune"] - (KAIRO["mune"] - KAIRO["keta"]) * ax / KAIRO["half"]
            under = KAIRO_UP + surf - KAIRO_ROOF_T
            g = under - Yr
            if worst_k is None or g < worst_k[0]:
                worst_k = (g, Xr, Yr, Zr, under)
        # 楼門の礎盤(側柱の芯 ±0.27・丈 0.15)への食い込み
        if abs(Xr) < 0.27 and Zr < 3.81 + 0.27 and Yr < 0.15:
            pen.append((Xr, Yr, Zr))
    bpy.data.objects.remove(rm, do_unlink=True)
    top = max(t[1] for t in U)
    print("  当たり 楼門(実 FBX・真上の光線)最小の離れ %.3f m — 塀の点 X %.2f Y %.3f Z %.2f → 楼門の材 Y %.3f"
          % worst_r if worst_r else "  当たり 楼門 — 真上に材なし")
    print("  当たり 回廊(設計値・妻の出 %.2f・懐 %.2f【U】)最小の離れ %.3f m — 塀の点 X %.2f Y %.3f Z %.2f → 屋根裏 Y %.3f"
          % ((KAIRO_KERABA, KAIRO_ROOF_T) + worst_k))
    print("  並べ 塀の頂 %.3f / 回廊の軒先 %.2f(敷居から)/ 回廊の桁 %.2f / 楼門の軒裏の最低(塀の帯)%.3f"
          % (top, KAIRO_UP + KAIRO["noki"], KAIRO_UP + KAIRO["keta"],
             worst_r[4] if worst_r else float("nan")))
    print("  当たり 楼門の礎盤(|X|<0.27・Z<4.08・Y<0.15)に入る塀の頂点 %d 点%s"
          % (len(pen), "" if not pen else " — 最も深い Z %.3f(食い込み %.3f)"
             % (min(p[2] for p in pen), 3.81 + 0.27 - min(p[2] for p in pen))))
    return worst_r, worst_k, pen


def shots(o, LEN):
    V.hook_textures()
    keep = V.TEX
    V.TEX = os.path.join(DB.JC, "Textures")
    V.hook_textures()
    V.TEX = keep
    os.makedirs(SHOT, exist_ok=True)
    out = []
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.01))

    def one(cam, look, fn, ortho=None, res=(1500, 1000)):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_sodebei_%s.png" % fn)
        V.render(f); out.append(f)
    one((0.0, -9.0, 1.4), (0.0, 0.0, 1.4), "elev", ortho=5.2)
    one((6.0, 0.0, 1.5), (0.0, 0.0, 1.4), "end", ortho=3.2, res=(1000, 1000))
    one((4.2, -4.6, 3.4), (0.0, 0.0, 1.3), "oblique")
    # 楼門と並べる(楼門の +Z 側)。塀の走り X → 楼門 Z(Blender −Y)
    objs = VM.import_fbx_abs(ROMON)
    for ob in objs:
        ob.name = "romon_" + ob.name
    o2 = o.copy(); o2.data = o.data
    bpy.context.collection.objects.link(o2)
    o2.rotation_euler = (0.0, 0.0, math.radians(90.0))
    o2.location = (0.0, -(ROMON_FACE_Z + LEN / 2.0), 0.0)
    o.location = (0.0, 0.0, -50.0)                   # 単体は画から外す
    V.hook_textures()
    zc = -(ROMON_FACE_Z + LEN / 2.0)
    one((9.0, zc - 1.0, 2.2), (0.0, zc + 1.5, 2.4), "with_romon", res=(1600, 1100))
    one((0.0, zc - 9.0, 2.5), (0.0, zc + 2.0, 3.0), "with_romon_along", res=(1600, 1100))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    LEN = float(argv[argv.index("--len") + 1]) if "--len" in argv else 4.2
    name = "Sanno_Sodebei_%d" % int(round(LEN * 1000.0))
    o = build(name, LEN)
    ok, tris, top = report(o, LEN)
    if not ok:
        raise SystemExit("[sodebei] ⛔ 検算に落ちた")
    if not selftest(o, LEN):
        raise SystemExit("[sodebei] ⛔ 陰性試験に失敗")
    print("[sodebei] 断面 = build_dobei(土壁 %.2f / 腰板 %.2f / 軒 %.2f / 屋根の総幅 %.2f / 棟の瓦場 %.3f)【U 類型】"
          % (DB.T_WALL, DB.H_SHITAMI, DB.H_KETA, DB.T_ROOF, DB.H_KETA + DB.T_ROOF / 2.0 * DB.RATIO))
    clearances(o, LEN)
    if "--no-export" not in argv:
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)
        print("[sodebei] 書き出し %s (tris %d)" % (path, tris))
    if "--render" in argv:
        # ⚠ export の後は bbox が潰れることがある — レンダは組み直した物で撮る
        o = build(name, LEN)
        for f in shots(o, LEN):
            print("RENDER " + f)


if __name__ == "__main__":
    main()
