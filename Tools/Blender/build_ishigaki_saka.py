"""石段の法面を留める「坂の土留め」を起こす。

    blender --background --python Tools/Blender/build_ishigaki_saka.py -- [L H [名前]]
    引数なしで定尺(9x6 / 12x8)を一括生成する。

【なぜ新造したか】Japanese Castle の Castle Wall を 1.8m 刻みで据えて天端を段々に
  下げていたが、実物の石段の袖は**一直線の斜め**である(ユーザー指摘 2026-08-15、
  妙義神社本殿の石段の写真)。天端が水平なモジュールを並べる限りその形にはならない。
  「今の石垣を回転させるか、新しい部材を作る」というユーザーの指示に従い、
  勾配に沿った一枚物を起こす。

【形】走り = Unity ローカル Z(0..L、+Z が坂下)。高さ = ローカル Y(0 = 下段の地面)。
  天端は H+KASA から KASA までの直線 — H は落差で、法面の平場と面一になる高さ。
  厚みは走り線を挟んで ±T/2 の**左右対称**にしてある(片側ずつ鏡像の部材を作らなくて済む。
  据えるときは芯線を平場の縁から T/2 だけ外へ出す)。
  天端には笠石(袖石)を左右へ 0.06 ずつ出して載せる — 写真で目に入るのはこの一本の線。

【素材】Japanese Castle の "stone wall" をそのまま借りる(新規マテリアルを作らない)。
  UV は Castle Wall と同じ密度: 走り 2.0m で u 0.25→0.75 / 高さ 4.12m で v 0→0.97。
  どちらも整数だけずれて繰り返すので、はみ出しても同じ石の柄に落ちる。
"""
import bpy, sys, os
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

# Castle Wall は Village Kit ではなく Japanese Castle の側にある
JC = "/Users/toshio/project/edo-unity/Assets/Japanese Castle"
SRC = "Exterior/Castle Wall.fbx"
MAT = "stone wall"
OUT = "/Users/toshio/project/edo-unity/Assets/Edo/Models/Ishigaki"

T = 0.60          # 躯体の厚み(郭の土留め 2.40m より薄い — 段脇の袖なので)
KASA = 0.45       # 笠石の天端が平場から出る高さ。段板は平場の 0.15 上なので段から 0.30
KASA_H = 0.28     # 笠石の見付
KASA_OUT = 0.06   # 笠石が躯体から左右へ出る量
SET = ((9.0, 6.0), (12.0, 8.0))   # 定尺 (走り, 落差)

U0, U1, U_PER = 0.25, 0.75, 2.0   # 走り 2.0m で u を 0.25→0.75
V_PER, V_SPAN = 4.12, 0.97        # 高さ 4.12m で v を 0→0.97


def uv_of(y, z):
    """走り y・高さ z を Castle Wall と同じ密度の UV へ。整数ずれで繰り返す"""
    return (U0 + (y / U_PER) * (U1 - U0), (z / V_PER) * V_SPAN)


def prism(name, halfx, top_at, z0_at, mat):
    """走り(Y)に沿って断面が変わらない角柱。上端 top_at(y) / 下端 z0_at(y) は y の関数。
    UV は面ごとでなく**頂点の (y,z) から**引くので、側面で柄が通る。"""
    ys = [0.0, LEN]
    v, f = [], []
    for y in ys:                       # 0,1,2,3 / 4,5,6,7
        for x in (-halfx, halfx):
            v.append((x, y, z0_at(y)))
        for x in (halfx, -halfx):
            v.append((x, y, top_at(y)))
    # 0,1 = 下端(-x,+x) / 2,3 = 上端(+x,-x)  (y=0 側)  / 4..7 が y=L 側
    f = [[0, 1, 2, 3], [7, 6, 5, 4],           # 妻(両端)
         [0, 4, 5, 1], [1, 5, 6, 2],           # 底 / +x の面
         [2, 6, 7, 3], [3, 7, 4, 0]]           # 天端 / -x の面
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(p) for p in v], [], f)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    for p in me.polygons:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl[li].uv = uv_of(co.y, co.z)
    return o


def build(L, H, name):
    global LEN
    LEN = L
    V.reset()
    V.MESH = os.path.join(JC, "Meshes")
    V.TEX = os.path.join(JC, "Textures")
    mat = V.borrow_material(SRC, MAT)
    if mat is None:
        raise SystemExit("マテリアル '%s' が %s に無い" % (MAT, SRC))
    V.hook_textures()

    crest = lambda y: H * (1.0 - y / L)          # 法面(平場)の高さ
    body = prism(name + "_body", T / 2.0,
                 lambda y: crest(y) + KASA - KASA_H, lambda y: 0.0, mat)
    kasa = prism(name + "_kasa", T / 2.0 + KASA_OUT,
                 lambda y: crest(y) + KASA, lambda y: crest(y) + KASA - KASA_H, mat)
    o = V.join([body, kasa], name)
    V.set_origin(o, (0.0, 0.0, 0.0))             # 原点 = 坂上の端・下段の地面
    mn, mx = V.bbox([o])
    print("SAKA %-28s %.2f x %.2f x %.2f  tris=%d"
          % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z,
             sum(len(q.vertices) - 2 for q in o.data.polygons)))
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
