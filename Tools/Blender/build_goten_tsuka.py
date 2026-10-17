"""御殿の**床下の足元** — 縁束・縁桁・束石と、柱の足元(柱の根継ぎ+礎石)を起こす(EDO-0502 2026-10-03)。

    blender --background --python Tools/Blender/build_goten_tsuka.py -- [--floor 0.62] [--render]

【なぜ要るか】御殿の部材キット(`Assets/Edo/Models/Goten/Parts`)には地面へ触れる部材が無い。
  `EdoGotenKit.Mune` は柱を床(floor = 0.62)から上にしか立てず、いちばん低いのは濡縁
  (`Goten_Nureen_1ken` の下端 = floor − 0.28 = 地盤 + 0.34)。岡部の御殿 5 棟が地面から 0.341m
  浮いて見えた(棟梁の実測)。⇒ 濡縁の下に**縁桁・縁束・束石**、柱の下に**根継ぎ・礎石**を入れる。

【焼くもの】(すべて Unity 局所: 幅 X / 高さ Y / 奥行 Z、表 = +Z。f = 床高 floor)
  ・`Goten_EnKeta_1ken_f<mm>` 濡縁 1間ぶんの**縁桁 + 縁束 1本 + 束石**。
      ピボット = **`Goten_Nureen_1ken` と同じ**(1間の中心・濡縁の下端・建物側の線)。
      ⇒ 濡縁と**同じ位置・同じ yaw** で据える。縁束はこの間の **−X 端**(柱通り)に立つ。
      縁桁は濡縁の根太の先(Z = −0.80)の下に 1間通す。
  ・`Goten_EnTsuka_f<mm>` 縁束 1本 + 束石だけ。ピボット = **束の芯・濡縁の下端の高さ**。
      run の **+X 端**(最後の間の先)と、濡縁の**入隅の升目の外の角**に据える。
      束の頭は濡縁の下端(Y=0)まで届く(隅の升目には縁桁が無いので)。
  ・`Goten_Soseki_f<mm>` 柱の根継ぎ(0.182 角)+ 礎石。ピボット = **`Goten_Column` と同じ**
      (柱の芯・床の高さ)。⇒ 柱と同じ位置へ据える。
  束石・礎石の天端は名目の地盤(床 − f)より 0.06 / 0.09 上、**下端は地盤より 0.30 下**
  (根入れの余裕。地盤が名目より 0.30 低くても石が浮かない)。地盤が高ければ埋まる(埋めて隠すが基本)。

【材】木は Village Kit の `column A` を**切って**使う(材 `wood`・素の UV のまま。断面だけ縮める)。
  石は `Kirishi`(山王の切石の材 `Assets/Edo/Materials/Sanno/Kirishi.mat`。`build_sanno_buzai._stone`
  の箱+面取り・タイル貼り 0.44)。⛔ 新しい材を作らない。
  remap: `Edo/御殿/新しい御殿FBXのマテリアルをremap`(BasedOnMaterialName + Everywhere で
  `wood.mat` と `Kirishi.mat` の両方を拾う)。

【寸法の確度】縁束 3寸5分角・縁桁 3寸5分×4寸・束石 8寸角・礎石 1尺2寸角は**一般類型【U】**。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_sanno_buzai as SB

K = V.KEN
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Parts"))
SHOT = os.environ.get("BUZAI_SHOT") or os.path.join(V.REPO, "Screenshots")

NUREEN_DROP = 0.28      # 濡縁の下端は床より 0.28 下(EdoGotenKit.NUREEN_DROP と同じ)
EN_T = 0.105            # 縁束の見付(3寸5分)【U】
KETA_W, KETA_H = 0.105, 0.12   # 縁桁 3寸5分 × 4寸【U】
EN_Z = -0.80            # 縁桁・縁束の芯の奥行(Unity z)。濡縁の根太は z = 0 → −0.852 なので根太の先の下
TSUKAISHI = 0.24        # 束石の天端の見付(8寸)【U】
SOSEKI = 0.36           # 礎石の天端の見付(1尺2寸)【U】
COL = 0.182             # 柱(Goten_Column)の見付
SHOW_T, SHOW_S = 0.06, 0.09    # 束石・礎石の天端が地盤より上に出る量
NEIRE = 0.30            # 石の根入れ(地盤より下)
BITE = 0.03             # 木が石へ食い込む量(継ぎ目の光を消す)


def U2B(x, y, z):
    """Unity 局所 (x 右, y 上, z 表) → Blender (X, Y, Z-up)。Unity X = −Blender X、Unity Z = −Blender Y。"""
    return Vector((-x, -z, y))


# ---------------------------------------------------------------- 木: column A を切る
def wood_piece(name, length, sec_x, sec_y, axis):
    """`column A` から長さ length を切り出し、断面を (sec_x, sec_y) に縮めた材を返す(Blender 座標)。
    axis='v' は鉛直(下端 z=0・芯 x=y=0)、axis='x' は Blender X 走り(左端 x=0・芯 y=z=0)。
    ⛔ 長さ方向は伸縮しない(木目の密度を保つ)。素の下端の木口を残し、上の切り口は開いたまま
    (切り口は必ず相手の材・石の中に入る)。"""
    objs = V.place("Walls and floors/column A.fbx", 0, 0, 0)
    o = V.join(objs, name)
    me = o.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    w0, d0, h0 = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    if length > h0 + 1e-6:
        raise SystemExit("[tsuka] column A は %.3fm しかない(要 %.3f)" % (h0, length))
    me.transform(Matrix.Translation((-cx, -cy, -z0)))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                           plane_co=(0, 0, length), plane_no=(0, 0, 1), clear_outer=True)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free()
    me.transform(Matrix.Diagonal((sec_x / w0, sec_y / d0, 1.0, 1.0)))
    if axis == 'x':
        me.transform(Matrix.Rotation(math.pi / 2, 4, 'Y'))     # +Z → +X
    me.update()
    return o


def place_wood(o, at):
    o.data.transform(Matrix.Translation(at)); o.data.update()
    return o


def post(name, ux, uz, y_top, y_bot):
    """縁束・根継ぎ(Unity 局所の芯 ux,uz・下端 y_bot → 上端 y_top)。"""
    t = EN_T if name.startswith("en") else COL
    o = wood_piece(name, y_top - y_bot, t, t, 'v')
    return place_wood(o, U2B(ux, y_bot, uz))


def keta(name, ux0, ux1, uz, y_top):
    """縁桁(Unity x ux0 → ux1・芯 uz・天端 y_top)。Unity +X = Blender −X なので Blender では ux1 側が左端。"""
    o = wood_piece(name, ux1 - ux0, KETA_H, KETA_W, 'x')     # 回すと sec_x が高さ・sec_y が奥行
    return place_wood(o, U2B(ux1, y_top - KETA_H / 2, uz))


# ---------------------------------------------------------------- 石
def stone(name, ux, uz, w, y_top, y_bot, rng):
    c = U2B(ux, 0, uz)
    return SB._stone(c.x - w / 2, c.x + w / 2, c.y - w / 2, c.y + w / 2, y_bot, y_top,
                     SB.kirishi_material(), rng, name, chamfer=0.012,
                     tile=SB.KIRISHI_TILE, tile_jit=True)


# ---------------------------------------------------------------- 組む
def finish(objs, name):
    V.dedup_materials()
    o = V.join(objs, name)
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)     # 凸な部品の寄せ集めなので外向きに揃う
    bm.to_mesh(me); bm.free(); me.update()
    path = os.path.join(OUT, name + ".fbx")
    V.export_fbx([o], path)
    xs = [-v.co.x for v in me.vertices]; ys = [v.co.z for v in me.vertices]; zs = [-v.co.y for v in me.vertices]
    print("[tsuka] %-26s Unity 局所 X[%.3f, %.3f] Y[%.3f, %.3f] Z[%.3f, %.3f]  面 %d  材 %s"
          % (name, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), len(me.polygons),
             sorted(m.name for m in me.materials if m)))
    print("[tsuka] 書き出し " + path)
    return o


def build(floor):
    fm = int(math.floor(floor * 1000 + 0.5))
    g_en = -(floor - NUREEN_DROP)          # 濡縁の下端から見た名目の地盤(f=0.62 で −0.34)
    g_col = -floor                         # 床から見た名目の地盤
    rng = random.Random(502)
    made = {}

    # ① 縁桁 + 縁束(−X 端)+ 束石 — 濡縁と同じピボット
    V.reset()
    ys_top = g_en + SHOW_T
    objs = [keta("en_keta", -K / 2, K / 2, EN_Z, 0.0),
            post("en_tsuka", -K / 2, EN_Z, -KETA_H, ys_top - BITE),
            stone("en_ishi", -K / 2, EN_Z, TSUKAISHI, ys_top, g_en - NEIRE, rng)]
    made["EnKeta"] = finish(objs, "Goten_EnKeta_1ken_f%d" % fm)

    # ② 縁束 + 束石だけ(run の +X 端・隅の升目の外の角)。束の頭は濡縁の下端まで
    V.reset()
    objs = [post("en_tsuka", 0.0, 0.0, 0.0, ys_top - BITE),
            stone("en_ishi", 0.0, 0.0, TSUKAISHI, ys_top, g_en - NEIRE, rng)]
    made["EnTsuka"] = finish(objs, "Goten_EnTsuka_f%d" % fm)

    # ③ 柱の根継ぎ + 礎石 — Goten_Column と同じピボット
    V.reset()
    ss_top = g_col + SHOW_S
    objs = [post("col_foot", 0.0, 0.0, 0.0, ss_top - BITE),
            stone("soseki", 0.0, 0.0, SOSEKI, ss_top, g_col - NEIRE, rng)]
    made["Soseki"] = finish(objs, "Goten_Soseki_f%d" % fm)
    print("[tsuka] 床 %.3f / 濡縁の下端 = 地盤 + %.3f / 束石の天端 = 地盤 + %.2f・礎石 = + %.2f / 根入れ %.2f"
          % (floor, floor - NUREEN_DROP, SHOW_T, SHOW_S, NEIRE))
    return fm


# ---------------------------------------------------------------- 検め: 濡縁・柱と並べて焼く
def assemble_and_render(fm, floor):
    """在庫の濡縁・隅・柱と並べ、3間 × 2間の角を組んで地面の上で撮る(Unity 局所を Blender へ写して置く)。"""
    V.reset()
    P = os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Parts")
    parts = os.path.join(OUT)

    def put(path, ux, uy, uz, yaw):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        root = [o for o in new if o.parent is None]
        # Unity の yaw(上から見て時計回り)は Blender では −Z まわり
        for r in root:
            # ⚠ Unity は据えるとき根の平行移動を上書きする(Put が localPosition を入れる)。
            #   在庫の御殿部材は根に (0.909,0,0) や (0.091,0.091,0) の平行移動を抱えているので、
            #   それを捨てないと柱が 0.09 ずれて見える(1回目のレンダで実見)。回転・倍率だけ残す
            m = r.matrix_world.copy()
            m.translation = Vector((0, 0, 0))
            r.matrix_world = (Matrix.Translation(U2B(ux, uy, uz)) @ Matrix.Rotation(math.radians(-yaw), 4, 'Z') @ m)
        return new

    nx, nz = 3, 2
    W, D = nx * K, nz * K
    # 棟の原点 = 南西角・地盤。床 = floor
    yn = floor - NUREEN_DROP
    for i in range(nx):
        put(os.path.join(P, "Goten_Nureen_1ken.fbx"), i * K + K / 2, yn, 0.0, 0)
        put(os.path.join(parts, "Goten_EnKeta_1ken_f%d.fbx" % fm), i * K + K / 2, yn, 0.0, 0)
    for j in range(nz):
        put(os.path.join(P, "Goten_Nureen_1ken.fbx"), 0.0, yn, j * K + K / 2, 90)
        put(os.path.join(parts, "Goten_EnKeta_1ken_f%d.fbx" % fm), 0.0, yn, j * K + K / 2, 90)
    put(os.path.join(P, "Goten_NureenCorner.fbx"), 0.0, yn, 0.0, 0)
    # run の端と隅の外の角
    put(os.path.join(parts, "Goten_EnTsuka_f%d.fbx" % fm), W, yn, EN_Z, 0)        # 前の run の +X 端
    put(os.path.join(parts, "Goten_EnTsuka_f%d.fbx" % fm), EN_Z, yn, 0.0, 0)      # 妻の run の +X 端(yaw 90 の局所 +X = 世界 −Z ⇒ z=0 の端)
    put(os.path.join(parts, "Goten_EnTsuka_f%d.fbx" % fm), EN_Z, yn, EN_Z, 0)     # 隅の升目の外の角
    for i in range(nx + 1):
        for j in range(nz + 1):
            if i in (0, nx) or j in (0, nz):
                put(os.path.join(P, "Goten_Column.fbx"), i * K, floor, j * K, 0)
                put(os.path.join(parts, "Goten_Soseki_f%d.fbx" % fm), i * K, floor, j * K, 0)
    for i in range(nx):
        for j in range(nz):
            put(os.path.join(P, "Goten_FloorBoard_1ken.fbx"), i * K + K / 2, floor, j * K + K / 2, 0)
    # 地面(名目の地盤 y=0)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    gp = bpy.context.active_object
    gm = bpy.data.materials.new("ground_preview")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.36, 0.28, 1)
    gp.data.materials.append(gm)
    V.hook_textures()
    # ⚠ 読み直した FBX の `Kirishi` はテクスチャの道が切れて桃色に刷れる ⇒ 実テクスチャを結んだ入れ物へ差し替える
    for m in list(bpy.data.materials):
        if m.name.split('.')[0] == SB.KIRISHI:
            m.name = "Kirishi_imported"
    kir = SB.kirishi_material()
    for o in bpy.data.objects:
        if o.type == 'MESH':
            for sl in o.material_slots:
                if sl.material and sl.material.name.startswith("Kirishi_imported"):
                    sl.material = kir
    SB._hook_cut_stone()
    os.makedirs(SHOT, exist_ok=True)
    # Blender 座標: 前の run は Unity z<0 = Blender +Y 側、x は反転
    c = U2B(W / 2, 0.4, D / 2)
    V.studio(U2B(-3.5, 1.3, -6.5), U2B(0.6, 0.3, 0.2), res=(1600, 1000))
    V.render(os.path.join(SHOT, "goten_tsuka_f%d_corner.png" % fm))
    V.studio(U2B(W / 2, 0.45, -7.0), U2B(W / 2, 0.35, 0.0), res=(1600, 900))
    V.render(os.path.join(SHOT, "goten_tsuka_f%d_front.png" % fm))
    V.studio(U2B(W + 1.2, 0.15, -2.6), U2B(W - 0.5, 0.25, -0.4), res=(1500, 1000))
    V.render(os.path.join(SHOT, "goten_tsuka_f%d_end.png" % fm))
    print("[tsuka] 検証レンダ " + SHOT)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    floor = float(argv[argv.index("--floor") + 1]) if "--floor" in argv else 0.62
    fm = build(floor)
    if "--render" in argv:
        assemble_and_render(fm, floor)


if __name__ == "__main__":
    main()
