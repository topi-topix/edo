"""御殿の建具と座敷飾りを作る(キットに無いので新造)。

    blender --background --python Tools/Blender/build_goten_fittings.py
    GOTEN_PREVIEW=/path/sheet.png blender --background --python Tools/Blender/build_goten_fittings.py

作るもの: 襖 / 欄間 / 雨戸 / 上段框 / 床の間 / 違い棚 / 帳台構

寸法の骨格(江戸間):
  1間 = 1.818 / 内法高 = **1.818(6尺)** / その上の欄間 = **0.909(半間)**
  → 襖(内法まで) + 欄間 = 2.727 = 障子・柱の高さ。格子に乗る。

⚠ 座標: Blender で作り、FBX 書き出し(axis_forward='-Z', axis_up='Y')で
   **Unity X = Blender X / Unity Y = Blender Z / Unity Z = −Blender Y**。
   規約の「表 = Unity +Z」は **Blender の −Y 向き**。表に付く物(引手・床框)は −Y 側に置く。
マテリアルは Village Kit のものを借りる(新規に作らない)。紙面は wall C の漆喰面を流用。
"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

K = V.KEN                 # 1.818
UCHINORI = K              # 内法高 = 6尺
RANMA_H = K / 2           # 欄間 = 半間
FULL = UCHINORI + RANMA_H # 2.727 = 障子・柱の高さ
OUT = "/Users/toshio/project/edo-unity/Assets/Edo/Models/Goten/Parts"
BUILT = []


class Pal:
    """借りてくるマテリアルと、そのアトラス上の代表UV"""
    def __init__(self):
        self.wood = V.borrow_material("Walls and floors/column A.fbx", "wood")
        self.wall = V.borrow_material("Walls and floors/wall C.fbx", "wall C")
        # 襖の紙は障子と同じ紙にする(door wall アトラスの紙面を一点で拾う。
        # 一点なので障子の組子の柄は乗らず、無地の紙面になる)
        self.paper = V.borrow_material("Walls and floors/door wall.fbx", "door wall")
        self.uv_wood = V.sample_uv("Walls and floors/column A.fbx", pick_high=True)
        self.uv_paper = V.sample_uv_bright("Walls and floors/door wall.fbx", "door wall")
        self.uv_wall = V.sample_uv_bright("Walls and floors/wall C.fbx", "wall C")          # 漆喰
        self.uv_dark = V.sample_uv_bright("Walls and floors/wall C.fbx", "wall C", 'dark')  # 腰板=漆塗り


def finish(objs, name, pivot):
    V.dedup_materials()
    o = V.join([x for x in objs if x], name)
    V.set_origin(o, pivot)
    mn, mx = V.bbox([o])
    V.export_fbx(o, os.path.join(OUT, name + ".fbx"))
    print("PART %-26s %6.3f x %6.3f x %6.3f  tris=%d  mats=%s"
          % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z,
             sum(len(p.vertices) - 2 for p in o.data.polygons),
             [m.name for m in o.data.materials]))
    BUILT.append(name)
    return o


def leaf(tag, cx, w, h, p, z0=0.0, th=0.032, hikite=True):
    """建具1枚(框+紙面+引手)。表は −Y。"""
    fr = 0.045                                    # 框の見付
    o = []
    o.append(V.box(tag + "_paper", (w - 2 * fr, th * 0.6, h - 2 * fr),
                   (cx, 0, z0 + h / 2), p.paper, p.uv_paper))
    o.append(V.box(tag + "_fL", (fr, th, h), (cx - w / 2 + fr / 2, 0, z0 + h / 2), p.wood, p.uv_wood))
    o.append(V.box(tag + "_fR", (fr, th, h), (cx + w / 2 - fr / 2, 0, z0 + h / 2), p.wood, p.uv_wood))
    o.append(V.box(tag + "_fB", (w, th, fr), (cx, 0, z0 + fr / 2), p.wood, p.uv_wood))
    o.append(V.box(tag + "_fT", (w, th, fr), (cx, 0, z0 + h - fr / 2), p.wood, p.uv_wood))
    if hikite:
        o.append(V.box(tag + "_hikite", (0.085, 0.014, 0.045),
                       (cx + w / 2 - 0.13, -th / 2, z0 + 0.95), p.wood, p.uv_dark))
    return o


def build_fusuma(p):
    """襖 一間 = 2枚建て(内法まで)"""
    V.reset(); p = Pal()
    o = []
    lw = K / 2 + 0.02                      # 2枚は中央で少し重なる
    for i in (0, 1):
        cx = (-0.5 + i) * (K - lw)
        o += leaf("F%d" % i, cx, lw, UCHINORI, p)
    return finish(o, "Goten_Fusuma_1ken", (0, 0, 0)), p


def build_ranma(p):
    """欄間 一間 = 鴨居 + 筬欄間(縦の組子)。襖の上に載せる(z0=内法高)"""
    V.reset(); p = Pal()
    o = [V.box("kamoi", (K, 0.11, 0.10), (0, 0, 0.05), p.wood, p.uv_wood),
         V.box("uwaba", (K, 0.11, 0.07), (0, 0, RANMA_H - 0.035), p.wood, p.uv_wood)]
    n = 17
    zc, hh = RANMA_H / 2, RANMA_H - 0.20
    for i in range(n):
        x = -K / 2 + K * (i + 0.5) / n
        o.append(V.box("osa%d" % i, (0.022, 0.055, hh), (x, 0, zc), p.wood, p.uv_wood))
    o.append(V.box("nuki", (K, 0.03, 0.028), (0, 0, zc), p.wood, p.uv_wood))
    return finish(o, "Goten_Ranma_1ken", (0, 0, 0)), p


def build_amado():
    """雨戸 = 板戸。Wall D 1(板壁)をそのまま江戸間に起こす"""
    V.reset()
    o = V.place("Walls and floors/Wall D 1.fbx", 0, 0, 0)
    mn, mx = V.bbox(o)
    if (mx.y - mn.y) > (mx.x - mn.x):          # 幅がYに出ていたらXへ回す
        V.reset()
        o = V.place("Walls and floors/Wall D 1.fbx", 0, 0, 0, rot=90)
        mn, mx = V.bbox(o)
    return finish(o, "Goten_Amado_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0))


def build_jodan(p):
    """上段框 — 上段の間の一段(0.15)の縁"""
    V.reset(); p = Pal()
    o = [V.box("kamachi", (K, 0.14, 0.15), (0, 0, 0.075), p.wood, p.uv_dark),
         V.box("yuka", (K, 0.55, 0.04), (0, 0.345, 0.13), p.wood, p.uv_wood)]
    return finish(o, "Goten_JodanKamachi_1ken", (0, 0, 0)), p


def alcove_shell(p, depth, name):
    """床の間・違い棚に共通の三方の壁と小壁。開口は −Y、奥は +Y。"""
    o = [V.box(name + "_back", (K, 0.06, FULL), (0, depth, FULL / 2), p.wall, p.uv_wall),
         V.box(name + "_sideL", (0.06, depth, FULL), (-K / 2 + 0.03, depth / 2, FULL / 2), p.wall, p.uv_wall),
         V.box(name + "_sideR", (0.06, depth, FULL), (K / 2 - 0.03, depth / 2, FULL / 2), p.wall, p.uv_wall),
         # 小壁(落掛から上)
         V.box(name + "_kokabe", (K, 0.05, FULL - UCHINORI), (0, 0.02, (FULL + UCHINORI) / 2), p.wall, p.uv_wall),
         # 天井板と底板(壁の外へ出る箱なので、塞がないと光が漏れる)
         V.box(name + "_ten", (K, depth, 0.05), (0, depth / 2, UCHINORI - 0.02), p.wood, p.uv_wood),
         V.box(name + "_soko", (K, depth, 0.06), (0, depth / 2, 0.03), p.wood, p.uv_wood)]
    return o


def build_tokonoma(p):
    """床の間 一間(奥行 0.85)"""
    V.reset(); p = Pal()
    d = 0.85
    o = alcove_shell(p, d, "toko")
    o += [V.box("toko_yuka", (K - 0.12, d, 0.05), (0, d / 2, 0.22), p.wood, p.uv_wood),
          V.box("toko_kamachi", (K, 0.13, 0.24), (0, 0.02, 0.12), p.wood, p.uv_dark),     # 床框(漆)
          V.box("toko_otoshigake", (K, 0.13, 0.15), (0, 0.02, UCHINORI - 0.075), p.wood, p.uv_wood),
          V.box("toko_bashira", (0.15, 0.15, UCHINORI), (-K / 2 + 0.075, -0.02, UCHINORI / 2), p.wood, p.uv_wood)]
    return finish(o, "Goten_Tokonoma_1ken", (0, 0, 0)), p


def build_chigaidana(p):
    """違い棚 一間(奥行 0.85)"""
    V.reset(); p = Pal()
    d = 0.85
    o = alcove_shell(p, d, "tana")
    o += [V.box("tana_jiita", (K - 0.12, d, 0.045), (0, d / 2, 0.36), p.wood, p.uv_wood),
          V.box("tana_up", (K / 2 - 0.02, d - 0.12, 0.035), (-K / 4, d / 2, 1.26), p.wood, p.uv_wood),
          V.box("tana_lo", (K / 2 - 0.02, d - 0.12, 0.035), (K / 4, d / 2, 1.00), p.wood, p.uv_wood),
          V.box("tana_ebi", (0.055, 0.10, 0.28), (0.0, d / 2, 1.13), p.wood, p.uv_wood),   # 海老束
          V.box("tana_fude", (0.05, d - 0.12, 0.07), (-K / 2 + 0.05, d / 2, 1.31), p.wood, p.uv_wood),
          V.box("tana_otoshigake", (K, 0.13, 0.15), (0, 0.02, UCHINORI - 0.075), p.wood, p.uv_wood)]
    return finish(o, "Goten_Chigaidana_1ken", (0, 0, 0)), p


def build_chodaigamae(p):
    """帳台構 — 上段の間の脇に立つ格式の建具。太い枠+框の高い襖4枚(ここは2枚で表現)"""
    V.reset(); p = Pal()
    fw, sill = 0.17, 0.14              # 枠の見付 / 敷居の立上り
    o = [V.box("cd_sill", (K + 2 * fw, 0.20, sill), (0, 0, sill / 2), p.wood, p.uv_dark),
         V.box("cd_head", (K + 2 * fw, 0.20, 0.22), (0, 0, UCHINORI + 0.11), p.wood, p.uv_dark),
         V.box("cd_L", (fw, 0.20, UCHINORI), (-(K + fw) / 2, 0, sill + (UCHINORI - sill) / 2), p.wood, p.uv_dark),
         V.box("cd_R", (fw, 0.20, UCHINORI), ((K + fw) / 2, 0, sill + (UCHINORI - sill) / 2), p.wood, p.uv_dark),
         # 小壁 — 妻壁を開けて据えるので、内法から上を塞がないと空が抜ける
         V.box("cd_kokabe", (K + 2 * fw, 0.06, FULL - UCHINORI - 0.22),
               (0, 0, (FULL + UCHINORI + 0.22) / 2), p.wall, p.uv_wall)]
    lw = K / 2 + 0.02
    for i in (0, 1):
        o += leaf("CD%d" % i, (-0.5 + i) * (K - lw), lw, UCHINORI - sill, p, z0=sill)
    return finish(o, "Goten_Chodaigamae_1ken", (0, 0, 0)), p


p = None
build_fusuma(p); build_ranma(p); build_amado()
build_jodan(p); build_tokonoma(p); build_chigaidana(p); build_chodaigamae(p)
print("BUILT %d fittings -> %s" % (len(BUILT), OUT))

if os.environ.get("GOTEN_PREVIEW"):
    # 確認用: 作った物を並べて1枚にレンダ
    V.reset()
    import mathutils
    x = 0.0
    for n in BUILT:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(OUT, n + ".fbx"))
        new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
        V.sel(new)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        for o in [o for o in bpy.data.objects if o not in before and o.type != 'MESH']:
            bpy.data.objects.remove(o, do_unlink=True)
        mn, mx = V.bbox(new)
        for o in new:
            o.location += mathutils.Vector((x - mn.x, -mn.y, -mn.z))
        x += (mx.x - mn.x) + 1.0
    bpy.ops.mesh.primitive_plane_add(size=90, location=(x / 2, 0, -0.01))
    V.hook_textures()
    V.studio((x / 2 - 3.0, -14.0, 7.0), (x / 2, 0.5, 1.1),
             ortho_scale=x + 2.0, res=(2000, 900))
    V.render(os.environ["GOTEN_PREVIEW"])
