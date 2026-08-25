"""武家屋敷の土塀 — 腰石・下見板・貫・漆喰・柱・本瓦葺きの一体物を起こす。

    blender --background --python Tools/Blender/build_dobei.py -- [--render]

【なぜ新造するか】
  ・在庫の `edogoyomi/es_dobei/s_hei_center.obj` は**片面だけの模型**(土壁の厚み 0.083、
    下見板は +Z 側のみ)。`DobeiRun` は表(f)・裏(b)の2回置いて厚みを装っており、
    **横から見ると中が抜けて見える**(ユーザー指摘 2026-08-16)。
  ・在庫の `Japanese Castle/.../Wall Exterior Defence` は彫りもPBRも良いが、
    **城の塀**の比率(躯体 0.80 に対し軒 2.10 = 2.63倍)で、腰石も下見板も柱も無い総漆喰。
    軒を詰めようとすると瓦・垂木・破風が別部材で噛み合っているため互いに貫通して壊れる。
  ・全5パック 2,687点を当たったが、**瓦屋根付きの土塀は他に無い**(2026-08-16 の探索)。
  → 武家屋敷の塀として要る「腰石＋下見板＋貫＋漆喰＋柱」を組んだ一体物をここで起こす。

【材と UV — README の規約に従う。新規マテリアルを作らない】
  マテリアル名を Village Kit のまま保つと Unity 側で Search&Remap で既存 .mat が当たる。
  すべて Normal + Mask 付きなので、edogoyomi の平板なテクスチャより質感が出る。
    ⚠ 腰石は**置かない**。キットの布基礎は丸石積み(玉石)で、屋敷を囲う石垣
      (`Castle Wall` の切石積み)と柄が合わない(ユーザー指摘 2026-08-16)。
      そもそもこの塀は石垣の天端に載るので、塀自身の腰石は要らない。
    木部   `Fences/Fence_B_01_x2.fbx` の `Fence_B_01`。UV はその最大面から実測。
           ⚠ `wood`(柱用アトラス)は板に見えず、UVを回しても直らなかった。
             Japanese Castle の `Wall Exterior C` は太く重い。どちらも却下
             (2026-08-16)。板塀の部材のテクスチャなら継ぎ目と木目がそのまま出る。
    漆喰   `Japanese Castle/.../Wall Exterior Defence` の同名マテリアル。
           UV はそのメッシュの**最大の側面から実測**で取る。
           ⚠ Village Kit の `wall C` は無地に近く、塀の大面には物足りない。
             城塀の漆喰はクリーム地に雨だれと苔が入っていて、大面に耐える
             (ユーザー指摘 2026-08-16「土塀部分は別のマテリアルないですか」)。
    瓦     `roof/roof 2x2.fbx` を**実ジオメトリのまま**流し葺き
    棟     `roof/roof top x1.fbx`(冠瓦+熨斗瓦2段が彫ってある)を継ぐ
  ⚠ UV は**一点貼りにしない**。木はベタ塗りの茶色に、漆喰は白一色になる
     (build_goten_roof.py の WOOD_UV / WALLC_UV と同じ理由。ユーザー指摘 2026-08-15)。
  ⚠ 瓦を自前の半円筒に置き換えたら「ダサい」と却下された(2026-08-16)。**瓦は実ジオメトリ。**

【寸法】**設計書(附録資料 二・三章「Blender 版の寸法」)の表が正典**。ここで作り直さない。
  ⚠ 会話から復元しようとして走りを 3.00 → 2.00 に変えてしまった(2026-08-16)。
     寸法は必ず設計書から引くこと。
  真の m で作り、**スケール1で置く**。
  ローカル: 走り X ∈ [0, 2] ／ 高さ Y ／ 厚み Z(芯を挟んで左右対称、表裏の別なし)。
  ⚠ Blender は Z が上。論理座標(走り, 高さ, 厚み)を Mesh.quad で入れ替えて積む。
     素通しすると塀が横倒しで書き出される(2026-08-16 に実際にやった)。
"""
import bpy, bmesh, sys, os, math, mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ROOT = V.REPO
JC = os.path.join(ROOT, "Assets/Japanese Castle")
OUT = os.path.join(ROOT, "Assets/Edo/Models/Dobei")
PLASTER_SRC = "Exterior/Wall Exterior Defence.fbx"
PLASTER_MAT = "Wall Exterior Defence"
WOOD_SRC = "Fences/Fence_B_01_x2.fbx"
WOOD_MAT = "Fence_B_01"

# ⚠ モジュール長は**瓦の割付 MOD_LEN の整数倍**にする。設計書は 3.00 だが、
#   3.00 / 2.004 = 1.497 で割り切れず、モジュール境ごとに瓦の間隔が崩れる
#   (ユーザー指摘 2026-08-16、1枚目の赤丸)。設計書の 3.00 はここで撤回する。
L = 2.004                         # = 瓦1枚ぶん。継ぎ目で段が通る
T_WALL = 0.36                     # 土壁の厚み(1.2尺)
T_SHITAMI = 0.42                  # 下見板
T_NUKI = 0.46                     # 貫(水切り)
T_KETA = 0.44                     # 軒桁
# ⚠ 柱(縦の仕切り枠)は**入れない**。モジュールを横に並べると柱の間隔が
#   モジュール境で詰まって歪に見える(ユーザー指摘 2026-08-16)。
#   横に通る貫と桁だけで面を割る。
T_ROOF = 1.00                     # 屋根の総幅。軒の出 片側 0.32
H_KOSHI = 0.00                    # 腰石は置かない。下見板を足元まで下ろす
# ⚠ 設計書の 下見板 1.30 / 漆喰 0.62 では**木が勝ちすぎる**(ユーザー指摘 2026-08-16
#   「白塀部分が少なすぎる」)。腰板は壁高の 1/3 程度に留め、漆喰を主面にする。
H_SHITAMI = 0.70                  # 下見板の上端(腰板)
H_NUKI = 0.06                     # 貫 0.70–0.76
# ⚠ 軒桁は**置かない**。キットの瓦モジュールが自前の軒裏(垂木・野地)を持っており、
#   その下に細い桁を足すと、見上げたとき**ペラペラの板が1枚浮いて見える**
#   (ユーザー指摘 2026-08-16)。漆喰を軒先まで通す。
H_WALL = 2.05                     # 土壁の上端(= 軒先)
H_KETA = 2.05

ROOF_MOD = "roof/roof 2x2.fbx"
MOD_LEN = 2.004                   # 瓦の桁行の繰り返し
MOD_RUN, MOD_RISE = 2.095, 1.143
RATIO = MOD_RISE / MOD_RUN        # 0.5456 ≒ 5.5寸勾配
RIDGE_MOD = "roof/roof top x1.fbx"
RIDGE_L, RIDGE_W, RIDGE_H = 0.909, 0.338, 0.366
W_MUNE, H_MUNE, SEAT_MUNE = 0.30, 0.22, 0.06

# アトラスの下端は苔・土汚れが強い。矩形の下側を切って使う
# ⚠ 最大面の矩形をそのまま貼ると**カビすぎに見える**(ユーザー指摘 2026-08-16)
CROP_PLASTER = 0.42               # 漆喰: v 範囲の下 42% を捨てる
CROP_WOOD = 0.30                  # 木  : 同 30%
# ⚠ `Wall Exterior Defence` のアトラスは、漆喰の**上端に軒の影が波々と描き込んである**
#   (城塀の瓦の影を焼き込んだもの)。こちらの軒とは位置が合わないので、
#   v 範囲の上側も切る。切らないと「灰色の波々したテクスチャ」が壁の上に出る
#   (ユーザー指摘 2026-08-16)。影はレンダ/実行時に瓦が落とすので描き込みは不要。
CROP_PLASTER_HI = 0.18            # 漆喰: v 範囲の上 18% を捨てる


def crop(rect, lo=0.0, hi=0.0):
    """UV矩形の v を下から lo・上から hi だけ詰める"""
    u0, v0, u1, v1 = rect
    d = v1 - v0
    return (u0, v0 + d * lo, u1, v1 - d * hi)

# build_goten_roof.py に記録済みの矩形。一点貼りを避けるためのもの
WOOD_UV = (0.600, 0.03, 0.770, 0.97)
WALLC_UV = (0.55, 0.34, 0.95, 0.62)


class Mesh(object):
    """四角形を1枚ずつ積む。頂点は溶接しない — 面ごとにUVを決めたいので"""

    def __init__(self):
        self.v, self.f, self.uv, self.mi = [], [], [], []

    def quad(self, pts, uvs, mat=0):
        """pts は論理座標 (走り, 高さ, 厚み)。Blender は Z が上なので入れ替えて積む"""
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2, i + 3])
        self.uv += list(uvs)
        self.mi.append(mat)

    def tri(self, pts, uvs, mat=0):
        """三角面。⚠ 四角形の頂点を1つ重ねて三角の代わりにすると、退化面になって
        Blender が妙な形に張る(2026-08-16、破風板が巨大な折れ面になった)"""
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2])
        self.uv += list(uvs)
        self.mi.append(mat)

    def build(self, name, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        for m in mats:
            me.materials.append(m)
        me.uv_layers.new(name="UVMap")
        uvl = me.uv_layers.active.data
        for k, p in enumerate(me.polygons):
            p.material_index = self.mi[k]
            for j, li in enumerate(p.loop_indices):
                uvl[li].uv = self.uv[p.loop_start + j]
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        return o


def slab(m, y0, y1, t, rect, mat, ncol, cap_top=True, rot=False):
    """走り X に沿った直方体。厚みは ±t/2。ncol はタイリングの分割数。
    rot=True で UV の軸を入れ替える。
    ⚠ `wood` アトラスの矩形は**縦木理**(柱用に長さを v に取る規約)。下見板は
       横板の羽重ねなので、そのまま貼ると縦縞が並んで木に見えない
       (ユーザー指摘 2026-08-16「木の質感がイマイチ」)。腰板は rot=True。"""
    u0, v0, u1, v1 = rect
    h = t / 2.0
    for j in range(ncol):
        x0, x1 = L * j / ncol, L * (j + 1) / ncol
        for sz in (-1, 1):
            pts = [(x0, y0, sz * h), (x1, y0, sz * h), (x1, y1, sz * h), (x0, y1, sz * h)]
            if rot:
                uvs = [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
            else:
                uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            m.quad(pts if sz > 0 else pts[::-1], uvs if sz > 0 else uvs[::-1], mat)
    if cap_top:
        m.quad([(0, y1, -h), (L, y1, -h), (L, y1, h), (0, y1, h)],
               [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat)
    for x, flip in ((0.0, True), (L, False)):        # 小口
        pts = [(x, y0, -h), (x, y0, h), (x, y1, h), (x, y1, -h)]
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        m.quad(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs, mat)


def wall_cap(m, mat, rect, e, half, z_eave):
    """壁の天端を屋根の裏面なりに立ち上げる。
    ⚠ 壁を軒先の高さで水平に切ると、屋根は棟へ向かって上がるので
       **壁の上と屋根の裏の間に楔形の隙間**が空く(ユーザー指摘 2026-08-16)。"""
    u0, v0, u1, v1 = rect
    zt = lambda t: z_eave + (e - abs(t)) * RATIO
    n = 6
    for j in range(n):
        xa, xb = L * j / n, L * (j + 1) / n
        for a, b in ((-half, 0.0), (0.0, half)):
            pts = [(xa, zt(a), a), (xb, zt(a), a), (xb, zt(b), b), (xa, zt(b), b)]
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            m.quad(pts, uvs, mat)
    for x, flip in ((0.0, True), (L, False)):
        tri = [(-half, z_eave), (0.0, zt(0.0)), (half, z_eave)]
        pts = [(x, q[1], q[0]) for q in tri]
        uvs = [(u0, v0), (u1, v0), (u1, v1)]
        m.tri(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs, mat)


T_TILE = 0.055                    # 袖瓦の厚み
D_SODE = 0.20                     # 袖垂れの下がり(屋根面から)
T_FLANGE = 0.05                   # 袖垂れの見付
W_SODE = 0.13                     # 袖瓦の幅(走り方向)


def sode_gawara(m, mat, rect, x_in, x_out, e, z_eave, z_ridge):
    """袖瓦 — ケラバの最端に葺く役物。他の瓦と同じ向きに葺き、外側に **袖垂れ** が
    下がって屋根下地の木口を覆う。断面は L 形。
    【典拠】袖瓦=けらば瓦・妻瓦。袖垂れが外側になるように葺き、垂れが下地の断面を守る
      (屋根業者の役物瓦解説より。一般類型・確度B。築地塀の一次図面は未入手)
    ⚠ 木の破風板は誤り。築地塀は土と瓦だけで、木の破風は付かない(2026-08-16 に改めた)。"""
    u0, v0, u1, v1 = rect
    sgn = 1.0 if x_out > x_in else -1.0
    xf = x_out - sgn * T_FLANGE
    # 断面(走り x, 屋根面からの下がり dz)。外側の端が袖垂れとして下がる
    sec = [(x_in, 0.0), (x_out, 0.0), (x_out, -D_SODE),
           (xf, -D_SODE), (xf, -T_TILE), (x_in, -T_TILE)]
    ns = len(sec)
    path = [(-e, z_eave), (0.0, z_ridge), (e, z_eave)]
    for k in range(len(path) - 1):
        (t0, z0), (t1, z1) = path[k], path[k + 1]
        for i in range(ns):
            a, b = sec[i], sec[(i + 1) % ns]
            pts = [(a[0], z0 + a[1], t0), (b[0], z0 + b[1], t0),
                   (b[0], z1 + b[1], t1), (a[0], z1 + a[1], t1)]
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            m.quad(pts, uvs, mat)
    # 両端(軒先)の小口を塞ぐ
    for (t, z), flip in ((path[0], True), (path[-1], False)):
        for q in ([sec[0], sec[1], sec[4], sec[5]], [sec[1], sec[2], sec[3], sec[4]]):
            pts = [(w[0], z + w[1], t) for w in q]
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            m.quad(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs, mat)


def clip_convex(obj, poly2d):
    """凸ポリゴンの各辺で鉛直に bisect して外側を捨てる(build_goten_roof と同じ)"""
    p = list(poly2d)
    area = sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
               for i in range(len(p)))
    if area < 0:
        p.reverse()
    me = obj.data
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        d = Vector((b[0] - a[0], b[1] - a[1], 0.0))
        if d.length < 1e-6:
            continue
        outward = Vector((d.y, -d.x, 0.0)).normalized()
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.bisect_plane(
            bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            plane_co=Vector((a[0], a[1], 0.0)), plane_no=outward,
            clear_outer=True, dist=1e-5)
        # ⚠ 辺と頂点を先にまとめて取ると、辺を消した時点で頂点参照が死ぬ
        loose_e = [e for e in bm.edges if not e.link_faces]
        bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
        loose_v = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose_v, context='VERTS')
        bm.to_mesh(me); bm.free()
    me.update()
    return obj


def tile_field(poly, eave_origin, yaw_deg, z_eave, name):
    """屋根面をキットの瓦で葺いて poly で切る。
    ⚠ 塀の流れは 0.5m でモジュール1枚(2.095m)に満たない。段は **1枚だけ** 置く。
       勾配方向に積むと、平面図では範囲内でも上の段が残って屋根が 1.7m 高くなる。"""
    c, s_ = math.cos(math.radians(-yaw_deg)), math.sin(math.radians(-yaw_deg))
    vs = []
    for q in poly:
        dx, dy = q[0] - eave_origin[0], q[1] - eave_origin[1]
        vs.append(dx * s_ + dy * c)
    j0 = int(math.floor(min(vs) / MOD_LEN)) - 1
    j1 = int(math.ceil(max(vs) / MOD_LEN)) + 1
    objs = []
    for j in range(j0, j1 + 1):
        o = V.place(ROOF_MOD, 0, 0, 0, scale=1.0)
        for ob in o:
            ob.location += Vector((0.0, j * MOD_LEN, 0.0))
        objs += o
    V.dedup_materials()
    field = V.join(objs, name + "_field")
    V.rotate_z([field], yaw_deg)
    field.location = Vector((eave_origin[0], eave_origin[1], z_eave))
    V.sel([field])
    bpy.ops.object.transform_apply(location=True)
    clip_convex(field, poly)
    if len(field.data.polygons) == 0:
        bpy.data.objects.remove(field, do_unlink=True)
        return None
    return field


def _frame(ax):
    side = ax.cross(Vector((0, 0, 1)))
    if side.length < 1e-9:
        return None
    side.normalize()
    up = side.cross(ax)
    return mathutils.Matrix(((ax.x, side.x, up.x, 0.0),
                             (ax.y, side.y, up.y, 0.0),
                             (ax.z, side.z, up.z, 0.0),
                             (0.0, 0.0, 0.0, 1.0)))


def ridge(p0, p1, name, w, h):
    """棟をキットの `roof top x1` を継いで通す。無地の箱にしない"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    Ln = d.length
    R = _frame(d.normalized())
    if R is None:
        return []
    n = max(1, int(round(Ln / RIDGE_L)))
    S = mathutils.Matrix.Diagonal(((Ln / n) / RIDGE_L, w / RIDGE_W, h / RIDGE_H, 1.0))
    C = mathutils.Matrix.Translation((0.0, -w / 2.0, 0.0))
    src = V.join(V.place(RIDGE_MOD, 0, 0, 0, scale=1.0), name + "_m")
    out = []
    for i in range(n):
        o = src if i == 0 else src.copy()
        if i:
            bpy.context.scene.collection.objects.link(o)
        o.matrix_world = mathutils.Matrix.Translation(p0 + d * (float(i) / n)) @ R @ C @ S
        out.append(o)
    return out


def castle_mat(src, mat_name, tag):
    """Japanese Castle の部材からマテリアルと、その最大側面の UV 矩形を取る。
    ⚠ 矩形を目分量で決めない。アトラスの余白や刻印を踏む"""
    keep_m, keep_t = V.MESH, V.TEX
    V.MESH, V.TEX = os.path.join(JC, "Meshes"), os.path.join(JC, "Textures")
    o = V.join(V.imp(src), "__src_" + tag)
    mat = bpy.data.materials.get(mat_name)
    PLASTER_MAT = mat_name
    me = o.data
    uvl = me.uv_layers.active.data
    names = [mm.name if mm else "" for mm in me.materials]
    mi = names.index(PLASTER_MAT) if PLASTER_MAT in names else 0
    best, ba = None, -1.0
    for pg in me.polygons:
        if pg.material_index != mi or abs(pg.normal.y) < 0.9:
            continue
        if pg.area > ba:
            ba, best = pg.area, pg
    if best is None:
        rect = (0.05, 0.05, 0.45, 0.30)
    else:
        us = [uvl[li].uv[0] for li in best.loop_indices]
        vs = [uvl[li].uv[1] for li in best.loop_indices]
        rect = (min(us), min(vs), max(us), max(vs))
    bpy.data.objects.remove(o, do_unlink=True)
    V.MESH, V.TEX = keep_m, keep_t
    return mat, rect


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
    if best is None:
        rect = (0.55, 0.5, 0.95, 0.95)
    else:
        us = [uvl[li].uv[0] for li in best.loop_indices]
        vs = [uvl[li].uv[1] for li in best.loop_indices]
        rect = (min(us), min(vs), max(us), max(vs))
    bpy.data.objects.remove(o, do_unlink=True)
    return mat, rect


def oni(x, out_sign, z_base, name):
    """鬼瓦を棟の端に据える。out_sign=+1 で +X 側の端。
    【典拠】ユーザー提供の写真(2026-08-16)— 棟の端に鬼瓦、その下に冠瓦の端を塞ぐ巴瓦。
    ⚠ 巴瓦は軒先の全長に並ぶものではない。この写真では**冠瓦の走りの端を塞ぐ円板**で、
       鬼瓦と同じく棟の端に1組だけ付く。"""
    o = V.join(V.place(ONI_MOD, 0, 0, 0, scale=1.0), name)
    mn, mx = V.bbox([o])
    k = H_ONI / (mx.z - mn.z)
    o.scale = (k, k, k)
    V.sel([o]); bpy.ops.object.transform_apply(scale=True)
    mn, mx = V.bbox([o])
    o.location = Vector((x - (mn.x + mx.x) / 2.0 + out_sign * (mx.x - mn.x) * 0.30,
                         -(mn.y + mx.y) / 2.0,
                         z_base - mn.z))
    V.sel([o]); bpy.ops.object.transform_apply(location=True)
    return o


def build(name="Dobei2m", gable=None):
    V.reset()
    wall, WALL_UV = castle_mat(PLASTER_SRC, PLASTER_MAT, "plaster")
    wood, W_UV = vk_mat(WOOD_SRC, WOOD_MAT, "wood")
    WALL_UV = crop(WALL_UV, CROP_PLASTER, CROP_PLASTER_HI)
    W_UV = crop(W_UV, CROP_WOOD)
    if wood is None or wall is None:
        raise SystemExit("マテリアルが取れない")

    m = Mesh()
    slab(m, 0.0, H_SHITAMI, T_SHITAMI, W_UV, 0, 3, cap_top=False)
    slab(m, H_SHITAMI, H_SHITAMI + H_NUKI, T_NUKI, W_UV, 0, 4, cap_top=True)
    e0 = T_ROOF / 2.0
    h_wall_top = H_KETA + (e0 - T_WALL / 2.0) * RATIO     # 壁の面での屋根裏の高さ
    slab(m, H_SHITAMI + H_NUKI, h_wall_top, T_WALL, WALL_UV, 1, 2, cap_top=False)
    wall_cap(m, 1, WALL_UV, e0, T_WALL / 2.0, H_KETA)
    body = m.build(name + "_body", [wood, wall])

    e = T_ROOF / 2.0
    z_ridge = H_KETA + e * RATIO
    pieces = [body]
    f1 = tile_field([(0.0, -e), (L, -e), (L, 0.0), (0.0, 0.0)], (0.0, -e), 90, H_KETA, name + "_S")
    f2 = tile_field([(L, e), (0.0, e), (0.0, 0.0), (L, 0.0)], (0.0, e), 270, H_KETA, name + "_N")
    pieces += [q for q in (f1, f2) if q]
    if gable is not None:
        # ⚠ 妻を**木の破風板**で塞いだが、築地塀は土と瓦だけで木の破風は付かない。
        #    正しくは袖瓦 — 瓦がケラバで折れて端を覆う(2026-08-16 に改めた)。
        roofmat = bpy.data.materials.get("roof")
        ruv = V.sample_uv(ROOF_MOD, pick_high=True)
        rrect = (ruv[0] - 0.01, ruv[1] - 0.01, ruv[0] + 0.01, ruv[1] + 0.01)
        mg = Mesh()
        x_in, x_out = (W_SODE, 0.0) if gable == 'L' else (L - W_SODE, L)
        sode_gawara(mg, 0, rrect, x_in, x_out, e, H_KETA, z_ridge)
        pieces.append(mg.build(name + "_sode", [roofmat or wood]))
    mune = ridge((0.0, 0.0, z_ridge - SEAT_MUNE), (L, 0.0, z_ridge - SEAT_MUNE),
                 name + "_mune", W_MUNE, H_MUNE)
    # ⚠ 棟の部材は公称長より外へ出る。切らないと走りが 3.00 → 3.10 になり、
    #   run の端で瓦が壁から浮いて見える(ユーザー指摘 2026-08-16、2枚目の赤丸)
    for q in mune:
        q.data = q.data.copy()          # ⚠ ridge() は mesh を共有する。複製しないと apply が落ちる
        V.sel([q]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        clip_convex(q, [(0.0, -1.0), (L, -1.0), (L, 1.0), (0.0, 1.0)])
    pieces += [q for q in mune if len(q.data.polygons) > 0]
    V.dedup_materials()
    return V.join(pieces, name)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    # 端部(妻を塞いだもの)も一緒に書き出す。run の両端に使う
    for g, nm in (('L', "Dobei2m_End"),):
        e_o = build(nm, gable=g)
        V.export_fbx([e_o], os.path.join(OUT, nm + ".fbx"))
        print("[dobei] wrote %s.fbx (妻を塞いだ端部)" % nm)
    o = build()
    mn, mx = V.bbox([o])
    print("[dobei] 走り %.2f / 総幅 %.2f / 全高 %.2f / 土壁 %.2f"
          % (mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, T_WALL))
    print("[dobei] mats: %s" % ", ".join(mm.name for mm in o.data.materials if mm))
    path = os.path.join(OUT, "Dobei2m.fbx")
    V.export_fbx([o], path)
    print("[dobei] wrote %s" % path)
    if "--render" in argv:
        V.hook_textures()                     # Village Kit
        keep = V.TEX
        V.TEX = os.path.join(JC, "Textures")  # Japanese Castle の漆喰も結線する
        V.hook_textures()
        V.TEX = keep
        SH = os.path.join(ROOT, "Screenshots")
        # --- 単体 ---
        V.studio((3.8, -3.2, 2.3), (1.5, 0.0, 1.15), res=(1400, 900))
        V.render(os.path.join(SH, "dobei_persp.png"))
        V.studio((1.5, -5.0, 1.25), (1.5, 0.0, 1.25), ortho_scale=3.4, res=(1200, 1050))
        V.render(os.path.join(SH, "dobei_elev.png"))
        V.studio((-2.4, -1.6, 1.8), (0.1, 0.0, 1.05), res=(1300, 950))
        V.render(os.path.join(SH, "dobei_end.png"))
        V.studio((1.5, -1.1, 0.35), (1.5, 0.0, 2.30), res=(1300, 950))
        V.render(os.path.join(SH, "dobei_up.png"))
        # --- 4枚並べた run ---
        for i in range(1, 4):
            c = o.copy(); c.data = o.data
            bpy.context.scene.collection.objects.link(c)
            c.location = Vector((L * i, 0.0, 0.0))
        V.studio((-3.2, -5.4, 1.60), (5.6, 0.0, 1.30), res=(1500, 900))
        V.render(os.path.join(SH, "dobei_run_eye.png"))
        V.studio((-4.6, -6.6, 5.4), (5.0, 0.0, 1.10), res=(1500, 900))
        V.render(os.path.join(SH, "dobei_run_obl.png"))
        V.studio((6.0, 0.0, 1.55), (0.0, 0.0, 1.45), res=(1500, 900))
        V.render(os.path.join(SH, "dobei_run_along.png"))
        V.studio((-1.9, -1.6, 2.85), (0.1, 0.0, 2.15), res=(1400, 950))
        V.render(os.path.join(SH, "dobei_run_end.png"))
        # 端部を左端に差し替えて撮り直す
        for ob in [x for x in bpy.data.objects if x.name.startswith("Dobei2m") and x.type == 'MESH']:
            if abs(ob.location.x) < 1e-6:
                bpy.data.objects.remove(ob, do_unlink=True)
        eo = build("Dobei2m_End", gable='L')
        eo.location = Vector((0.0, 0.0, 0.0))
        V.hook_textures(); V.TEX = os.path.join(JC, "Textures"); V.hook_textures(); V.TEX = keep
        V.studio((-1.9, -1.6, 2.85), (0.1, 0.0, 2.15), res=(1400, 950))
        V.render(os.path.join(SH, "dobei_end_fixed.png"))
        V.studio((-2.6, -2.4, 1.75), (1.2, 0.0, 1.35), res=(1500, 900))
        V.render(os.path.join(SH, "dobei_end_eye.png"))
        # 端から瓦と壁の取り合いを見る
        V.studio((-1.35, -1.45, 1.98), (0.35, 0.0, 2.08), res=(1500, 950))
        V.render(os.path.join(SH, "dobei_joint_a.png"))
        V.studio((-0.85, -1.25, 1.62), (0.30, 0.0, 2.12), res=(1500, 950))
        V.render(os.path.join(SH, "dobei_joint_b.png"))


main()
