"""松江松平邸の表門の番所 — **向唐破風・出格子・切石畳出の基壇**を起こす。

    blender --background --python Tools/Blender/build_matsudaira_bansho.py -- [--render]

【なぜ新造するか】
  在庫の `edogoyomi/es_dbansho`(3.6×2.1m)は**規模も意匠も足りない**。
  指図は 5.5×3.6m・張出2.0m・向唐破風・出格子・石垣畳出の基壇(`gate.plan.bansho`)。

【姿の典拠】確度A。
  ・温古写真集11(88005761・明治初撮影)の実見 — 冠木門の両側に唐破風造の番所
  ・『日本案内記 関東篇』昭和5年「冠木門に属し、両側に**唐破風造の番所**を附属」
  ⚠ 「両番所=国主の格」は反証済み([武家屋敷門の格式階梯]B)。
    唐破風の両番所は **10万石以上の帯**の意匠で、当家18.6万石はその帯に入る。
    ただし**当門の形式の典拠は帯ではなく写真そのもの**。

【寸法】**指図 `gate.plan.bansho` が正典。ここで作り直さない。**
  w 5.5 / d 3.6 / protrude 2.0(門の面より前へ張り出す量)
  ローカル: 走り X ∈ [0, w]、高さ Y(=Blender Z)、奥行 Z(=Blender Y)。
  **ピボット = 番所の走り方向の芯・基壇の下端**(据える側が s と敷居をそのまま使える)。

【向唐破風】むくり(凸)の曲線。**照り(凹)の千鳥破風と取り違えない。**
  弦長 = 桁行いっぱい、起り(むくり)の矢高 = 弦の 1/7 を頂点に取り、
  弧を 12 分割した折れ面で葺く(瓦は実ジオメトリを流すには曲率が強すぎるので、
  破風板+瓦坂の板で表す。⚠ 半円筒の自作瓦は 2026-08-16 に却下されている作法なので、
  ここでは**瓦の粒を作らず、破風板と葺き面の見切りで唐破風の輪郭を出す**)。

【材と UV — README の規約。新規マテリアルを作らない】
  木部   `Fences/Fence_B_01_x2.fbx` の `Fence_B_01`
  漆喰   Japanese Castle `Exterior/Wall Exterior Defence.fbx` の同名マテリアル
  瓦     `roof/roof 2x2.fbx` の `roof`(葺き面の色味を借りる。ジオメトリは使わない)
  石垣   Japanese Castle `Exterior/Castle Wall.fbx` があればその材、無ければ漆喰で代用
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

PROJ = V.REPO
JC = os.path.join(PROJ, "Assets", "Japanese Castle")

WOOD_SRC, WOOD_MAT = "Fences/Fence_B_01_x2.fbx", "Fence_B_01"
PLASTER_SRC, PLASTER_MAT = "Exterior/Wall Exterior Defence.fbx", "Wall Exterior Defence"
ROOF_SRC, ROOF_MAT = "roof/roof 2x2.fbx", "roof"

WOOD_UV = (0.600, 0.03, 0.770, 0.97)
WALLC_UV = (0.55, 0.34, 0.95, 0.62)
ROOF_UV = (0.10, 0.10, 0.90, 0.90)

W, D, PROTRUDE = 5.5, 3.6, 2.0        # 指図 gate.plan.bansho
BASE_H = 0.55                          # 切石畳出の基壇
BODY_H = 2.45                          # 軸部(基壇の上から桁まで)
KOSHI_H = 0.85                         # 腰壁(下見板)
KARA_RISE = 0.78                       # 向唐破風の起り(むくり)の矢高
EAVE = 0.55                            # 軒の出
SEG = 12                               # 唐破風の折れ数


class Mesh(object):
    def __init__(self):
        self.v, self.f, self.uv, self.mi = [], [], [], []

    def quad(self, pts, uv, mat=0):
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2, i + 3])
        u0, v0, u1, v1 = uv
        self.uv += [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        self.mi.append(mat)

    def tri(self, pts, uv, mat=0):
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2])
        u0, v0, u1, v1 = uv
        self.uv += [(u0, v0), (u1, v0), ((u0 + u1) / 2, v1)]
        self.mi.append(mat)

    def box(self, x0, x1, y0, y1, z0, z1, uv, mat=0):
        self.quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], uv, mat)
        self.quad([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], uv, mat)
        self.quad([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], uv, mat)
        self.quad([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], uv, mat)
        self.quad([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], uv, mat)
        self.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], uv, mat)

    def to_object(self, name, mats):
        """Blender へ落とす。

        ⚠ **厚みの向きを反転してから出す。** `export_fbx` の
        `axis_forward='-Z', axis_up='Y'` は Blender +Y を Unity の **−Z** へ写すので、
        論理座標のまま出すと「表」が Unity のローカル −Z に出る
        (README の規約は 表=+Z)。2026-08-25 に番所が街路へ背を向け、
        出格子と唐破風が敷地の内側を向いていたのがこれ。
        ⛔ **巻き順は反転しない。** 反転が1回多くなり、**面が全部裏返る**。
        `quad` が `(x, z, y)` と軸を入れ替えて積む時点で1回、ここの Y 反転で1回、
        合わせて偶数回の鏡映になっているので、巻きはそのままで法線が外を向く。
        ⚠ 2026-08-31 実測: 巻きを反転していたため **背面 4/4・出格子の表 60/60 が裏返り**、
        裏面は描かれないので**閉じているのに中が透けて見えた**
        (ユーザーのブックマーク #3「袖番所の中が透けて見える」の正体)。
        """
        vs = [Vector((p.x, -p.y, p.z)) for p in self.v]
        faces, uvs, mi = [], [], []
        k = 0
        for fi, f in enumerate(self.f):
            n = len(f)
            faces.append(list(f))
            uvs += list(self.uv[k:k + n])
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



def borrow(src, mat_name, tag, castle=False, fallback=WOOD_UV):
    """部材からマテリアルと最大面の UV 矩形を取る。**新規マテリアルを作らない**"""
    keep = (V.MESH, V.TEX)
    if castle:
        V.MESH, V.TEX = os.path.join(JC, "Meshes"), os.path.join(JC, "Textures")
    try:
        o = V.join(V.imp(src), "__src_" + tag)
    except Exception as ex:
        V.MESH, V.TEX = keep
        print("[bansho] ⚠ %s の借用に失敗: %s" % (mat_name, ex))
        return None, fallback
    V.MESH, V.TEX = keep
    mat = bpy.data.materials.get(mat_name)
    me, uvl = o.data, o.data.uv_layers.active.data
    names = [mm.name if mm else "" for mm in me.materials]
    mi = names.index(mat_name) if mat_name in names else 0
    best, ba = None, -1.0
    for pg in me.polygons:
        if pg.material_index == mi and pg.area > ba:
            ba, best = pg.area, pg
    rect = fallback
    if best is not None:
        us = [uvl[i].uv[0] for i in best.loop_indices]
        vs = [uvl[i].uv[1] for i in best.loop_indices]
        rect = (min(us), min(vs), max(us), max(vs))
    bpy.data.objects.remove(o, do_unlink=True)
    return mat, rect


def kara_profile(t):
    """向唐破風の稜線。**中央が起り(凸)・両端が照り(凹)で反り上がる S 字**。
    ⚠ 単純な sin(半円)にすると樽屋根になる(2026-08-25 の1回目)。
      唐破風は「中央の膨らみ」と「両端の跳ね」の二つで出来ている。"""
    c = math.sin(math.pi * t) ** 1.35          # 中央の起り(裾を細く)
    e = 0.30 * (math.cos(math.pi * t) ** 2) ** 3.0   # 両端の照り(跳ね上がり)
    return KARA_RISE * (c + e)


def build(name="Matsudaira_Bansho"):
    V.reset()
    wood, W_UV = borrow(WOOD_SRC, WOOD_MAT, "wood")
    if wood is None:
        raise SystemExit("木部が取れない")
    wall, WA_UV = borrow(PLASTER_SRC, PLASTER_MAT, "plaster", castle=True, fallback=WALLC_UV)
    if wall is None:
        raise SystemExit("漆喰が取れない — 木に落として板小屋にしてはいけない")
    roof, R_UV = borrow(ROOF_SRC, ROOF_MAT, "roof", fallback=ROOF_UV)
    if roof is None:
        roof, R_UV = wall, WA_UV

    m = Mesh()
    x0, x1 = -W / 2.0, W / 2.0        # 走りの芯を x=0 に
    z0, z1 = -D / 2.0, D / 2.0        # 奥行の芯を z=0 に。門の面より前へ出すのは据える側

    # ---- 切石畳出の基壇(躯体より各面 0.18 出る)
    m.box(x0 - 0.18, x1 + 0.18, 0.0, BASE_H, z0 - 0.18, z1 + 0.18, WA_UV, 1)

    yb = BASE_H
    yt = yb + BODY_H
    # ---- 腰壁(下見板)+ 上部の漆喰
    m.box(x0, x1, yb, yb + KOSHI_H, z0, z1, W_UV, 0)
    m.box(x0, x1, yb + KOSHI_H, yt, z0, z1, WA_UV, 1)

    # ---- 出格子(正面 +Z と 側面。腰壁の上に方立を並べる)
    # 出格子は**細い竪子を密に**。太い方立を疎に並べると牢格子に見える(2026-08-25 の1回目)
    gy0, gy1 = yb + KOSHI_H + 0.10, yb + KOSHI_H + 0.95     # 窓の帯だけ(軒まで通さない)
    gx0, gx1 = x0 + 0.45, x1 - 0.45
    m.box(gx0 - 0.08, gx1 + 0.08, gy0 - 0.12, gy0, z1, z1 + 0.22, W_UV, 0)   # 出格子の腰(受け)
    m.box(gx0 - 0.08, gx1 + 0.08, gy1, gy1 + 0.14, z1, z1 + 0.22, W_UV, 0)   # 上枠
    nb = 23                                                                   # 竪子
    for k in range(nb):
        gx = gx0 + (gx1 - gx0) * k / float(nb - 1)
        m.box(gx - 0.022, gx + 0.022, gy0, gy1, z1 + 0.09, z1 + 0.20, W_UV, 0)
    m.box(gx0, gx1, gy0, gy1, z1 + 0.005, z1 + 0.03, WA_UV, 1)               # 格子の奥の面
    ny = 4                                                                    # 横子
    for k in range(ny):
        hy = gy0 + (gy1 - gy0) * (k + 0.5) / ny
        m.box(gx0, gx1, hy - 0.018, hy + 0.018, z1 + 0.10, z1 + 0.19, W_UV, 0)
    for k in range(9):                                                        # 側面(-X)にも
        gz = z0 + 0.55 + (D - 1.10) * k / 8.0
        m.box(x0 - 0.20, x0 - 0.09, gy0, gy1, gz - 0.022, gz + 0.022, W_UV, 0)
    m.box(x0 - 0.22, x0 - 0.14, gy0 - 0.12, gy0, z0 + 0.45, z1 - 0.45, W_UV, 0)
    m.box(x0 - 0.22, x0 - 0.14, gy1, gy1 + 0.14, z0 + 0.45, z1 - 0.45, W_UV, 0)

    # ---- 桁
    m.box(x0 - 0.10, x1 + 0.10, yt, yt + 0.20, z0 - 0.10, z1 + 0.10, W_UV, 0)

    # ---- 向唐破風(正面 +Z 側。むくりの稜線を SEG 分割して葺く)
    ey = yt + 0.20
    ze = z1 + EAVE                       # 軒先
    prev = None
    for k in range(SEG + 1):
        t = k / float(SEG)
        px = x0 + W * t
        ph = ey + kara_profile(t)        # 棟の稜線
        cur = (px, ph)
        if prev is not None:
            (ax, ah), (bx, bh) = prev, cur
            # 葺き面(棟から軒先へ下る)
            m.quad([(ax, ah, z1 - 0.15), (bx, bh, z1 - 0.15),
                    (bx, ey - 0.30, ze), (ax, ey - 0.30, ze)], R_UV, 2)
            # 破風板(見付け)
            m.quad([(ax, ah, ze), (bx, bh, ze),
                    (bx, bh - 0.22, ze), (ax, ah - 0.22, ze)], W_UV, 0)
        prev = cur
    # 唐破風の背後(棟から後ろへ落とす片流れ)
    m.quad([(x0, ey + kara_profile(0.0), z1 - 0.15), (x1, ey + kara_profile(1.0), z1 - 0.15),
            (x1, ey + 0.05, z0 - EAVE), (x0, ey + 0.05, z0 - EAVE)], R_UV, 2)
    # 両妻の小口(棟と軒先を結ぶ三角)
    for px in (x0, x1):
        m.tri([(px, ey + kara_profile(0.0 if px == x0 else 1.0), z1 - 0.15),
               (px, ey - 0.30, ze), (px, ey + 0.05, z0 - EAVE)], W_UV, 0)

    o = m.to_object(name, [wood, wall, roof])
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = build()
    mn, mx = V.bbox([o])
    print("[bansho] 実寸 W(X)=%.3f  D(Y)=%.3f  H(Z)=%.3f" % (mx.x - mn.x, mx.y - mn.y, mx.z - mn.z))
    print("[bansho] 指図 w=%.1f d=%.1f 張出=%.1f / 向唐破風の起り %.2f" % (W, D, PROTRUDE, KARA_RISE))
    out = os.path.join(PROJ, "Assets", "Edo", "Models", "Mon", "Matsudaira_Bansho.fbx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    V.export_fbx([o], out)
    print("[bansho] 書き出し " + out)
    if "--render" in argv:
        V.hook_textures()
        bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.02))
        V.studio((-6.0, 9.5, 4.6), (0.0, 0.6, 1.9), res=(1500, 1000))   # 正面(+Y=論理+Z)から
        V.render(os.environ.get("GOTEN_PREVIEW", "/tmp/bansho.png"))


main()
