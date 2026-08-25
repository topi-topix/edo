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

JC = os.path.join(V.REPO, "Assets", "Japanese Castle")
SRC = "Exterior/Castle Wall.fbx"
MAT = "stone wall"
OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Ishigaki")

T = 0.60          # 躯体の厚み(郭の土留め 2.40m より薄い — 段脇の袖なので)
KASA = 0.45       # 笠石の天端が平場から出る高さ。段板は平場の 0.15 上なので段から 0.30
KASA_H = 0.28     # 笠石の見付
KASA_OUT = 0.06   # 笠石が躯体から左右へ出る量
KASA_BEVEL = 0.05 # 笠石の面取り(天端を左右 0.05 ずつ細くする)。角が立ちすぎるのを殺す
BATTER = 0.015    # 反り。1m 上がるごとに片側 0.015 内へ入る
EMBED = 2.0       # 坂上の端を上段の地中へ差し込む長さ。端面を露出させない
V_KASA = 0.30     # 笠石はこの v から自分の帯を使う(段の格子に載せない)
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


def prism(m, half_at, zbot, ztop, y0g, y1g, ncol, band=None, kinks=None):
    """走り Y に沿った角柱。半厚 half_at(z)・下端 zbot(y)・上端 ztop(y) はすべて関数。

    band=None のとき側面は**石積み1枚(COURSE)の格子**に割って貼る。
    band=(v0, 高さ) を渡すと格子に載せず、その帯の中で相対的に貼る —
    ⚠ 笠石のような薄い帯を格子に割ると、段の境をまたぐ列で片端が潰れ、
      その1列だけ v が 0→0.79 に走って**テクスチャが引き伸ばされる**
      (ユーザー指摘 2026-08-15「一部テクスチャが引き伸ばされてる」)。

    ⚠⚠ 列は「u の割り(2.0m)」だけでなく **上端が段の境をまたぐ y** でも割る。
      割らずに段ごとに上端を丸めると、丸めた折れ線が本来の直線の下を通り、
      その間が**穴**になる(地面が透けて見え、引き伸ばされた面に見えた)。
      kink(勾配の折れ点)も同じ理由で割る。"""
    ys = set(y0g + (y1g - y0g) * i / ncol for i in range(ncol + 1))
    for yk in (kinks or []):
        if y0g < yk < y1g:
            ys.add(yk)
    if band is None:                                   # 上端が段の境をまたぐ y を足す
        N = 400
        for i in range(N):
            ya = y0g + (y1g - y0g) * i / N
            yb = y0g + (y1g - y0g) * (i + 1) / N
            ka, kb2 = int(ztop(ya) / COURSE), int(ztop(yb) / COURSE)
            if ka == kb2:
                continue
            lo, hi = ya, yb                            # 二分法で境界の y を詰める
            for _ in range(30):
                mid = (lo + hi) / 2.0
                if int(ztop(mid) / COURSE) == ka:
                    lo = mid
                else:
                    hi = mid
            ys.add((lo + hi) / 2.0)
    ys = sorted(ys)
    ncol = len(ys) - 1

    def vv(z, y):
        if band is None:
            return None
        return band[0] + ((z - zbot(y)) / COURSE) * V_STONE

    def hf(z, y):
        """その点の半厚。frac = 部材の中での高さ比(0=下端 1=上端)を面取りに渡す"""
        span = ztop(y) - zbot(y)
        frac = 0.0 if span < 1e-6 else min(1.0, max(0.0, (z - zbot(y)) / span))
        return half_at(z, frac)

    for j in range(ncol):
        y0, y1 = ys[j], ys[j + 1]
        if band is not None:
            spans = [(zbot(y0), ztop(y0), zbot(y1), ztop(y1), None)]
        else:
            zmax = max(ztop(y0), ztop(y1))
            spans = []
            k = 0
            while k * COURSE < zmax:
                c0, c1 = k * COURSE, (k + 1) * COURSE
                spans.append((min(max(zbot(y0), c0), c1), min(max(ztop(y0), c0), c1),
                              min(max(zbot(y1), c0), c1), min(max(ztop(y1), c0), c1), c0))
                k += 1
        for a0, b0, a1, b1, c0 in spans:
            if b0 - a0 < 1e-4 and b1 - a1 < 1e-4:
                continue
            V = (lambda z, y: vv(z, y)) if band is not None else (lambda z, y: v_of(z - c0))
            for sx in (-1, 1):                     # 長手の両側面(反りで x が z で変わる)
                pts = [(sx * hf(a0, y0), y0, a0), (sx * hf(a1, y1), y1, a1),
                       (sx * hf(b1, y1), y1, b1), (sx * hf(b0, y0), y0, b0)]
                uvs = [(u_of(y0), V(a0, y0)), (u_of(y1), V(a1, y1)),
                       (u_of(y1), V(b1, y1)), (u_of(y0), V(b0, y0))]
                m.quad(pts if sx > 0 else pts[::-1], uvs if sx > 0 else uvs[::-1])
        # 天端(勾配なり)と底。v は厚みから引く
        for z_at, flip in ((ztop, False), (zbot, True)):
            h0, h1 = hf(z_at(y0), y0), hf(z_at(y1), y1)
            pts = [(-h0, y0, z_at(y0)), (h0, y0, z_at(y0)),
                   (h1, y1, z_at(y1)), (-h1, y1, z_at(y1))]
            uvs = [(u_of(y0), v_of(0.0)), (u_of(y0), v_of(2 * h0)),
                   (u_of(y1), v_of(2 * h1)), (u_of(y1), v_of(0.0))]
            m.quad(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs)
    # 妻(下端のみ。上端は EMBED で上段の地中へ差し込むので面を作らない)
    y = y1g
    zb, zt = zbot(y), ztop(y)
    k = int(zb / COURSE)
    while k * COURSE < zt:
        c0, c1 = k * COURSE, (k + 1) * COURSE
        a = min(max(zb, c0), c1); b = min(max(zt, c0), c1)
        if b - a > 1e-4:
            ha, hb = hf(a, y), hf(b, y)
            va = vv(a, y) if band is not None else v_of(a - c0)
            vb = vv(b, y) if band is not None else v_of(b - c0)
            pts = [(-ha, y, a), (ha, y, a), (hb, y, b), (-hb, y, b)]
            uvs = [(u_of(0.0), va), (u_of(2 * ha), va), (u_of(2 * hb), vb), (u_of(0.0), vb)]
            m.quad(pts, uvs)
        k += 1


def build(L, H, name):
    V.reset()
    V.MESH = os.path.join(JC, "Meshes")
    V.TEX = os.path.join(JC, "Textures")
    mat = V.borrow_material(SRC, MAT)
    if mat is None:
        raise SystemExit("マテリアル '%s' が %s に無い" % (MAT, SRC))
    V.hook_textures()

    # 坂上の端は EMBED だけ上段の地中へ差し込む。y は -EMBED から L まで。
    # 差し込んだ区間は平場と同じ高さのまま(上端は水平)なので、端面が地表に出ない
    crest = lambda y: H * (1.0 - max(y, 0.0) / L)    # 法面(平場)の高さ
    ncol = max(1, int(round((L + EMBED) / U_PER)))
    m = Mesh()
    # 躯体 — 上へ行くほど BATTER だけ内へ入る(反り)
    body_h = lambda z, frac: max(0.10, T / 2.0 - BATTER * z)
    prism(m, body_h, lambda y: 0.0, lambda y: crest(y) + KASA - KASA_H, -EMBED, L, ncol,
          kinks=[0.0])
    # 笠石 — 天端へ向かって KASA_BEVEL だけ細める(面取り)。角が立ちすぎるのを殺す。
    # v は自分の帯で貼る(段の格子に載せると境をまたぐ列で引き伸ばされる)
    kasa_h = lambda z, frac: T / 2.0 + KASA_OUT - BATTER * z - KASA_BEVEL * frac
    prism(m, kasa_h, lambda y: crest(y) + KASA - KASA_H, lambda y: crest(y) + KASA,
          -EMBED, L, ncol, band=(V_KASA, KASA_H), kinks=[0.0])
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
