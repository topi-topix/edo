"""松江松平邸の表門 — **屋根なしの冠木門**(角柱・冠木・内開き扉)を起こす。

    blender --background --python Tools/Blender/build_matsudaira_omotemon.py -- [--render]

【なぜ新造するか】
  ・在庫の `edogoyomi/es_kmon`(薬医門)は**切妻の小屋根を持つ**。当門は屋根が無い。
  ・在庫の `es_kabukimon` は冠木門だが**柱高 3.74m** で、指図の 5.2m に届かない
    (`docs/asset-catalog.md` 照会 2026-08-23)。
  → 角柱・冠木・扉・潜り戸まで一体で起こす。

【姿の典拠】確度A。指図 `gate._` の通り:
  ・温古写真集11(88005761・明治初撮影)の実見 — **屋根が無く、冠木の上に何も載らない**
  ・『日本案内記 関東篇』昭和5年「冠木門に属し、両側に唐破風造の番所を附属」
  ⚠ 切妻小屋根を載せる前案(2026-08-22)は**撤回済み**。ここで復活させないこと。
  ⚠ 番所は別部材(`build_matsudaira_bansho.py`)。この門は**門柱と袖塀まで**。

【寸法】**指図 `gate.plan` が正典。ここで作り直さない。**
  monW 4.5 / monH 5.2 / monD 1.2 / sode 4.25 / kuguri true
  ローカル: 走り X ∈ [0, monW]、高さ Y(=Blender Z)、厚み Z(=Blender Y、芯で対称)。
  **ピボットは門の芯・敷居レベル**(据える側が `gate.pos` と `sill` をそのまま使えるように)。

【材と UV — README の規約。新規マテリアルを作らない】
  木部  `Fences/Fence_B_01_x2.fbx` の `Fence_B_01`(build_dobei.py と同じ借り先)
  漆喰  Japanese Castle の `Wall Exterior Defence`(袖塀の大面。同上)
  ⚠ UV は一点貼りにしない。木がベタ塗りの茶色になる(2026-08-15 の指摘)。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

PROJ = "/Users/toshio/project/edo-unity"
JC = os.path.join(PROJ, "Assets", "Japanese Castle")

WOOD_SRC = "Fences/Fence_B_01_x2.fbx"
WOOD_MAT = "Fence_B_01"
PLASTER_SRC = "Exterior/Wall Exterior Defence.fbx"   # build_dobei.py と同じ借り先
PLASTER_MAT = "Wall Exterior Defence"

WOOD_UV = (0.600, 0.03, 0.770, 0.97)     # build_goten_roof.py に記録済み
WALLC_UV = (0.55, 0.34, 0.95, 0.62)

# ---- 指図から引く寸法(既定値。--spec で json を読ませる)
MON_W, MON_H, MON_D = 4.5, 5.2, 1.2      # 門柱の間・柱高・奥行
SODE = 4.25                              # 袖塀の長さ(片側)
POST = 0.42                              # 角柱の見付(江戸の大門の柱。1尺4寸相当)
KANUKI_H = 0.55                          # 冠木の丈
KANUKI_OUT = 0.35                        # 冠木が柱の外へ出る長さ
DOOR_H = 4.45                            # 扉の高さ(冠木の下端まで)。冠木の上端が柱頭 5.20 に納まる
SODE_H = 2.65                            # 袖塀の高さ(指図 const.dobeiH と同じ)
KUGURI_W, KUGURI_H = 0.95, 1.85          # 潜り戸


class Mesh(object):
    """四角形を1枚ずつ積む。頂点は溶接しない(面ごとにUVを決めるため)"""

    def __init__(self):
        self.v, self.f, self.uv, self.mi = [], [], [], []

    def quad(self, pts, uv, mat=0):
        """pts は論理座標 (走り, 高さ, 厚み)。Blender は Z が上なので入れ替える"""
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2, i + 3])
        u0, v0, u1, v1 = uv
        self.uv += [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        self.mi.append(mat)

    def box(self, x0, x1, y0, y1, z0, z1, uv, mat=0):
        """直方体。走り x・高さ y・厚み z"""
        self.quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], uv, mat)  # 前
        self.quad([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], uv, mat)  # 後
        self.quad([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], uv, mat)  # 右
        self.quad([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], uv, mat)  # 左
        self.quad([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], uv, mat)  # 上
        self.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], uv, mat)  # 下

    def to_object(self, name, mats):
        """Blender へ落とす。

        ⚠ **厚みの向きを反転してから出す。** `export_fbx` の
        `axis_forward='-Z', axis_up='Y'` は Blender +Y を Unity の **−Z** へ写すので、
        論理座標のまま出すと「表」が Unity のローカル −Z に出る
        (README の規約は 表=+Z)。2026-08-25 に番所が街路へ背を向け、
        出格子と唐破風が敷地の内側を向いていたのがこれ。
        面の巻き順と UV も一緒に反転して、法線を外向きに保つ。
        """
        vs = [Vector((p.x, -p.y, p.z)) for p in self.v]
        faces, uvs, mi = [], [], []
        k = 0
        for fi, f in enumerate(self.f):
            n = len(f)
            faces.append(list(reversed(f)))
            uvs += list(reversed(self.uv[k:k + n]))
            mi.append(self.mi[fi])
            k += n
        me = bpy.data.meshes.new(name)
        me.from_pydata(vs, [], faces)
        me.update()
        for m in mats:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for j, pg in enumerate(me.polygons):
            pg.material_index = mi[j]
        for j, dd in enumerate(uvl.data):
            dd.uv = uvs[j]
        o = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(o)
        return o



def vk_mat(src, mat_name, tag):
    """Village Kit の部材からマテリアルと、その最大面の UV 矩形を取る"""
    o = V.join(V.imp(src), "__src_" + tag)
    mat = bpy.data.materials.get(mat_name)
    me = o.data
    uvl = me.uv_layers.active.data
    names = [mm.name if mm else "" for mm in me.materials]
    mi = names.index(mat_name) if mat_name in names else 0
    best, ba = None, -1.0
    for pg in me.polygons:
        if pg.material_index != mi:
            continue
        if pg.area > ba:
            ba, best = pg.area, pg
    rect = WOOD_UV
    if best is not None:
        us = [uvl[i].uv[0] for i in best.loop_indices]
        vs = [uvl[i].uv[1] for i in best.loop_indices]
        rect = (min(us), min(vs), max(us), max(vs))
    bpy.data.objects.remove(o, do_unlink=True)
    return mat, rect


def castle_mat(src, mat_name, tag):
    """Japanese Castle の部材から漆喰のマテリアルと、その最大側面の UV 矩形を取る。
    ⚠ import しないとマテリアルが存在せず、木材に落ちて袖塀が板塀に見える(2026-08-25)"""
    keep_m, keep_t = V.MESH, V.TEX
    V.MESH, V.TEX = os.path.join(JC, "Meshes"), os.path.join(JC, "Textures")
    try:
        o = V.join(V.imp(src), "__src_" + tag)
    except Exception as ex:
        V.MESH, V.TEX = keep_m, keep_t
        print("[omotemon] ⚠ 漆喰の借用に失敗: %s" % ex)
        return None, WALLC_UV
    V.MESH, V.TEX = keep_m, keep_t
    mat = bpy.data.materials.get(mat_name)
    me = o.data
    uvl = me.uv_layers.active.data
    names = [mm.name if mm else "" for mm in me.materials]
    mi = names.index(mat_name) if mat_name in names else 0
    best, ba = None, -1.0
    for pg in me.polygons:
        if pg.material_index != mi or abs(pg.normal.y) < 0.9:
            continue
        if pg.area > ba:
            ba, best = pg.area, pg
    rect = WALLC_UV
    if best is not None:
        us = [uvl[i].uv[0] for i in best.loop_indices]
        vs = [uvl[i].uv[1] for i in best.loop_indices]
        rect = (min(us), min(vs), max(us), max(vs))
    bpy.data.objects.remove(o, do_unlink=True)
    return mat, rect


def build(name="Matsudaira_Omotemon"):
    V.reset()
    wood, W_UV = vk_mat(WOOD_SRC, WOOD_MAT, "wood")
    if wood is None:
        raise SystemExit("木部のマテリアルが取れない")
    wall, WA_UV = castle_mat(PLASTER_SRC, PLASTER_MAT, "plaster")
    if wall is None:
        raise SystemExit("袖塀の漆喰が取れない — 木に落として板塀にしてはいけない")

    m = Mesh()
    half = MON_W / 2.0                      # 門の芯を x=0 に置く
    d2 = MON_D / 2.0
    p2 = POST / 2.0

    # ---- 門柱 2本(角柱・柱頭は銅冠を想い、わずかに絞る)
    for sgn in (-1, 1):
        cx = sgn * (half - p2)
        m.box(cx - p2, cx + p2, 0.0, MON_H, -p2, p2, W_UV, 0)
        # 柱頭の銅冠(少しだけ大きい笠)
        m.box(cx - p2 - 0.04, cx + p2 + 0.04, MON_H, MON_H + 0.10, -p2 - 0.04, p2 + 0.04, W_UV, 0)

    # ---- 冠木(柱の外へ KANUKI_OUT だけ出る。**上に屋根は載せない**)
    kx0 = -half - KANUKI_OUT
    kx1 = half + KANUKI_OUT
    ky0 = DOOR_H
    m.box(kx0, kx1, ky0, ky0 + KANUKI_H, -p2 * 0.9, p2 * 0.9, W_UV, 0)

    # ---- 内開きの扉 2枚(閉じた姿。筋金具は板の分割で表す)
    inner = half - POST
    for sgn in (-1, 1):
        x0 = 0.0 if sgn > 0 else -inner
        x1 = inner if sgn > 0 else 0.0
        m.box(x0, x1, 0.0, DOOR_H, -0.06, 0.06, W_UV, 0)
        # 横桟 3本(筋金具の見立て。UV を変えて板と質を分ける)
        for hy in (0.85, 1.95, 3.05):
            m.box(x0, x1, hy, hy + 0.11, -0.10, 0.10, W_UV, 0)

    # ---- 袖塀(片側 SODE。潜り戸は東側に1つ)
    for sgn in (-1, 1):
        sx0 = sgn * half
        sx1 = sgn * (half + SODE)
        a, b = (min(sx0, sx1), max(sx0, sx1))
        if sgn > 0:
            # 潜り戸を開ける — 袖塀の門寄りに寄せる
            g0 = a + 0.55
            g1 = g0 + KUGURI_W
            m.box(a, g0, 0.0, SODE_H, -0.18, 0.18, WA_UV, 1)
            m.box(g1, b, 0.0, SODE_H, -0.18, 0.18, WA_UV, 1)
            m.box(g0, g1, KUGURI_H, SODE_H, -0.18, 0.18, WA_UV, 1)   # 楣
            m.box(g0, g1, 0.0, KUGURI_H, -0.05, 0.05, W_UV, 0)       # 潜り戸の板
        else:
            m.box(a, b, 0.0, SODE_H, -0.18, 0.18, WA_UV, 1)
        # 袖塀の笠木(木)
        m.box(a - 0.06, b + 0.06, SODE_H, SODE_H + 0.14, -0.26, 0.26, W_UV, 0)

    o = m.to_object(name, [wood, wall])
    # ピボット = 門の芯・敷居レベル(既に x=0, z=0 に組んである)
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = build()
    mn, mx = V.bbox([o])
    print("[omotemon] 実寸 W(X)=%.3f  D(Y)=%.3f  H(Z)=%.3f" % (mx.x - mn.x, mx.y - mn.y, mx.z - mn.z))
    print("[omotemon] 門柱の間 %.2f / 柱高 %.2f / 袖塀 %.2f×2 / 屋根なし" % (MON_W, MON_H, SODE))
    out = os.path.join(PROJ, "Assets", "Edo", "Models", "Mon", "Matsudaira_Omotemon.fbx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    V.export_fbx([o], out)
    print("[omotemon] 書き出し " + out)
    if "--render" in argv:
        V.hook_textures()
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.02))
        V.studio((-9.0, -12.0, 7.5), (0.0, 0.0, 2.6), res=(1500, 1000))
        V.render(os.environ.get("GOTEN_PREVIEW", "/tmp/omotemon.png"))


main()
