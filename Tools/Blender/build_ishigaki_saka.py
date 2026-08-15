"""石段の法面を留める「坂の土留め」を起こす。

    blender --background --python Tools/Blender/build_ishigaki_saka.py -- [L H [名前]]
    引数なしで定尺(9x6 / 12x8)を一括生成する。

【なぜ新造したか】Japanese Castle の Castle Wall を 1.8m 刻みで据えて天端を段々に
  下げていたが、実物の石段の袖は**一直線の斜め**である(ユーザー指摘 2026-08-15、
  妙義神社本殿の石段の写真)。天端が水平なモジュールを並べる限りその形にはならない。
  「今の石垣を回転させるか、新しい部材を作る」というユーザーの指示に従い、
  勾配に沿った一枚物を起こす。

【形】走り = Unity ローカル **-Z**(0..L、-Z が坂下。Blender の +Y が Unity の -Z へ落ちる)。
  高さ = ローカル Y(0 = 下段の地面)。天端は H+KASA から KASA までの直線 —
  H は落差で、法面の平場と面一になる高さ。
  厚みは走り線を挟んで ±T/2 の**左右対称**にしてある(片側ずつ鏡像の部材を作らなくて済む)。
  天端には笠石を左右へ 0.06 ずつ出して載せる — 写真で目に入るのはこの一本の線。

【素材とUV】Japanese Castle の "stone wall" をそのまま借りる(新規マテリアルを作らない)。
  ⚠ このアトラスは **v 0.79〜1.00 が「天端の平らな笠石」** で、そこを踏むと
     ツルツルの無地の帯が出る(ユーザー指摘 2026-08-15「天端がツルツル」)。
     郭の石垣はそれを天端に使っているが、段脇の袖は写真どおり**全面を粗い石**にしたいので、
     **v は 0〜0.79(石積みの領域)しか使わない**。
  そのため面を石積み1枚分(高さ 3.26m = v 0.79 / 走り 2.0m = u 0.25→0.75)の
  **格子に割って**貼る。1枚の大きな面に連続UVを流すと v が 0.79 を越えて笠石の帯に入る。
  u は 0.25 起点で整数ずつしかずれないので、はみ出しても同じ石積みに落ちる。
"""
import bpy, sys, os
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

JC = "/Users/toshio/project/edo-unity/Assets/Japanese Castle"
SRC = "Exterior/Castle Wall.fbx"
MAT = "stone wall"
OUT = "/Users/toshio/project/edo-unity/Assets/Edo/Models/Ishigaki"

T = 0.60          # 躯体の厚み(郭の土留め 2.40m より薄い — 段脇の袖なので)
KASA = 0.45       # 笠石の天端が平場から出る高さ。段板は平場の 0.15 上なので段から 0.30
KASA_H = 0.28     # 笠石の見付
KASA_OUT = 0.06   # 笠石が躯体から左右へ出る量
SET = ((9.0, 6.0), (12.0, 8.0))   # 定尺 (走り, 落差)

# Castle Wall(2.0m x 4.0m)の実測UV: u 0.25..0.75 / v 0..0.97。
# うち v 0.79 から上はアトラス上部の「平らな笠石」なので使わない。
U0, U1, U_PER = 0.25, 0.75, 2.0
V_STONE = 0.79                    # 石積みの上端(これ以上は無地の笠石)
COURSE = 4.0 / 0.97 * V_STONE     # 石積み1枚ぶんの高さ = 3.26m


def u_of(a):
    return U0 + (a / U_PER) * (U1 - U0)


def v_of(b):
    """b は 0..COURSE の面内の高さ。0..V_STONE に収まる"""
    return (b / COURSE) * V_STONE


class Mesh(object):
    """四角形を1枚ずつ積んで作る。頂点は溶接しない — 面ごとにUVを決めたいので"""
    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def quad(self, pts, uvs):
        i = len(self.v)
        self.v += [Vector(p) for p in pts]
        self.f.append([i, i + 1, i + 2, i + 3])
        self.uv += list(uvs)

    def build(self, name, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        me.materials.append(mat)
        me.uv_layers.new(name="UVMap")
        uvl = me.uv_layers.active.data
        for p in me.polygons:
            for k, li in enumerate(p.loop_indices):
                uvl[li].uv = self.uv[p.loop_start + k]
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        return o


def prism(m, half, zbot, ztop, L, ncol):
    """走り Y に沿った角柱を、走り 2.0m × 石積み1枚(COURSE)の格子で貼る。
    zbot/ztop は y の関数(上端は勾配なので y で変わる)。"""
    ys = [L * i / ncol for i in range(ncol + 1)]
    zmax = max(ztop(0.0), ztop(L))
    ncourse = max(1, int(zmax / COURSE) + 1)

    for j in range(ncol):
        y0, y1 = ys[j], ys[j + 1]
        for k in range(ncourse):
            c0, c1 = k * COURSE, (k + 1) * COURSE
            # 段の中でのこの列の上下端。**必ず [c0,c1] に丸める** —
            # 丸めないと笠石(zbot が段より上)で v が 0.79 を越えて無地の帯を踏む
            a0, a1 = min(max(zbot(y0), c0), c1), min(max(zbot(y1), c0), c1)
            b0, b1 = min(max(ztop(y0), c0), c1), min(max(ztop(y1), c0), c1)
            if b0 - a0 < 1e-4 and b1 - a1 < 1e-4:
                continue
            for sx in (-1, 1):                     # 長手の両側面
                x = sx * half
                pts = [(x, y0, a0), (x, y1, a1), (x, y1, b1), (x, y0, b0)]
                uvs = [(u_of(y0), v_of(a0 - c0)), (u_of(y1), v_of(a1 - c0)),
                       (u_of(y1), v_of(b1 - c0)), (u_of(y0), v_of(b0 - c0))]
                m.quad(pts if sx > 0 else pts[::-1], uvs if sx > 0 else uvs[::-1])
        # 天端(勾配なり)と底 — 幅0.72mなので1枚で足りる。v は厚みから引く
        for z_at, flip in ((ztop, False), (zbot, True)):
            pts = [(-half, y0, z_at(y0)), (half, y0, z_at(y0)),
                   (half, y1, z_at(y1)), (-half, y1, z_at(y1))]
            uvs = [(u_of(y0), v_of(0.0)), (u_of(y0), v_of(2 * half)),
                   (u_of(y1), v_of(2 * half)), (u_of(y1), v_of(0.0))]
            m.quad(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs)
    # 妻(両端)。こちらも石積み1枚ごとに割る
    for y, flip in ((0.0, True), (L, False)):
        zb, zt = zbot(y), ztop(y)
        k = int(zb / COURSE)
        while k * COURSE < zt:
            c0, c1 = k * COURSE, (k + 1) * COURSE
            a = min(max(zb, c0), c1); b = min(max(zt, c0), c1)
            if b - a > 1e-4:
                pts = [(-half, y, a), (half, y, a), (half, y, b), (-half, y, b)]
                uvs = [(u_of(0.0), v_of(a - k * COURSE)), (u_of(2 * half), v_of(a - k * COURSE)),
                       (u_of(2 * half), v_of(b - k * COURSE)), (u_of(0.0), v_of(b - k * COURSE))]
                m.quad(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs)
            k += 1


def build(L, H, name):
    V.reset()
    V.MESH = os.path.join(JC, "Meshes")
    V.TEX = os.path.join(JC, "Textures")
    mat = V.borrow_material(SRC, MAT)
    if mat is None:
        raise SystemExit("マテリアル '%s' が %s に無い" % (MAT, SRC))
    V.hook_textures()

    crest = lambda y: H * (1.0 - y / L)              # 法面(平場)の高さ
    ncol = max(1, int(round(L / U_PER)))
    m = Mesh()
    prism(m, T / 2.0, lambda y: 0.0, lambda y: crest(y) + KASA - KASA_H, L, ncol)
    prism(m, T / 2.0 + KASA_OUT,
          lambda y: crest(y) + KASA - KASA_H, lambda y: crest(y) + KASA, L, ncol)
    o = m.build(name, mat)
    V.set_origin(o, (0.0, 0.0, 0.0))                 # 原点 = 坂上の端・下段の地面
    mn, mx = V.bbox([o])
    print("SAKA %-24s %.2f x %.2f x %.2f  quads=%d"
          % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, len(o.data.polygons)))
    V.export_fbx(o, os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) >= 2:
        L, H = float(argv[0]), float(argv[1])
        build(L, H, argv[2] if len(argv) > 2 else "Ishigaki_Saka_%gx%g" % (L, H))
    else:
        for L, H in SET:
            build(L, H, "Ishigaki_Saka_%gx%g" % (L, H))
    print("BUILT -> %s" % OUT)
