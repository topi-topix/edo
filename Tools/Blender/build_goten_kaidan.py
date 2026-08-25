"""御殿の「階段廊下」— 木の段になった渡廊下を起こす。

    blender --background --python Tools/Blender/build_goten_kaidan.py -- [走り 落差 [名前]]
    引数なしで定尺(9x6 / 12x8)を一括生成する。

【なぜ新造したか】郭をまたぐ登廊の床を屋外の石段のままにしていたが、
  ・石段の幅(4m)と回廊の幅(一間=1.818m)が合わず見た目が破綻する
  ・廊下なのに一旦外の石段を踏むことになる
  というユーザー指摘(2026-08-15)を受けて、**幅一間の木の階段廊下**を別部材で起こす。
  石段は屋外用としてそのまま残し、同じ法面の上に並べて置く。

【形】幅は他の渡廊下と同じ一間。原点 = 坂上の**上段の廊下の床の高さ**で、
  ローカル +Y が坂下(Unity では -Z へ落ちる)。z は下るので負。
  段は蹴上=落差/段数・踏面=走り/段数。両縁に勾配なりの高欄(笠木・地覆・束)を通す。
  床下は Unity 側で束を入れる(地面の高さはビルダーが知っている)。

【素材】Village Kit のものを借りる — 踏板 "Floor" / 側桁・蹴込・高欄 "wood"。
  新規マテリアルは作らない(Unity 側の Search&Remap が同名の .mat を拾う)。
"""
import bpy, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Parts")
KEN = 1.818
KERI_MAX = 0.30          # 蹴上の上限。これを超えないよう段数を決める
TREAD_T = 0.064          # 踏板の厚み(Goten_FloorBoard と同じ)
KERI_T = 0.030           # 蹴込板の厚み
SIDE_W, SIDE_H = 0.180, 0.300    # 側桁の見付・成
KORAN_H = 1.158          # 高欄の高さ(Goten_Koran_1ken と同じ)
KASA = 0.090             # 笠木の断面
JIFUKU = 0.070           # 地覆の断面
TSUKA = 0.055            # 高欄の束の見付
SET = ((9.0, 6.0), (12.0, 8.0))

FLOOR_UV = (0.05, 0.05, 0.45, 0.45)   # floor アトラスの板目
WOOD_UV = (0.600, 0.03, 0.770, 0.97)  # build_goten_roof と同じ木理


def slant_box(name, p0, p1, w, h, mat, uv):
    """p0→p1(XZ平面で斜め、Y方向は一定)に沿う角柱。断面 w(X) x h(Z)。
    高欄の笠木・地覆・側桁のように**勾配なりに寝る材**に使う。"""
    (x0, y0, z0), (x1, y1, z1) = p0, p1
    import math
    dy, dz = y1 - y0, z1 - z0
    L = math.hypot(dy, dz)
    uy, uz = dy / L, dz / L          # 材の長手方向
    ny, nz = -uz, uy                 # 断面の「成」方向(長手に直交)
    v = []
    for sx in (-1, 1):
        for t in (0.0, 1.0):
            for sh in (-0.5, 0.5):
                v.append((x0 + sx * w / 2.0,
                          y0 + dy * t + ny * h * sh,
                          z0 + dz * t + nz * h * sh))
    # v: [(-x,t0,-h),(-x,t0,+h),(-x,t1,-h),(-x,t1,+h),(+x,...)...]
    f = [[0, 1, 3, 2], [6, 7, 5, 4], [0, 2, 6, 4], [1, 5, 7, 3],
         [0, 4, 5, 1], [2, 3, 7, 6]]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(q) for q in v], [], f)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    V.set_uv_rect(o, uv, axes=('y', 'z'))
    return o


def build(run, drop, name):
    V.reset()
    m_floor = V.borrow_material("Walls and floors/floor.fbx", "floor")
    m_wood = V.borrow_material("Walls and floors/column A.fbx", "wood")
    if m_floor is None or m_wood is None:
        raise SystemExit("マテリアルが取れない")
    V.hook_textures()

    import math
    n = int(math.ceil(drop / KERI_MAX))
    keri, fumi = drop / n, run / n
    half = KEN / 2.0
    parts = []

    for i in range(1, n + 1):
        z = -keri * i                               # この段の踏面の天端
        y0, y1 = fumi * (i - 1), fumi * i
        o = V.box(name + "_fumi%d" % i, (KEN, fumi, TREAD_T),
                  (0.0, (y0 + y1) / 2.0, z - TREAD_T / 2.0), m_floor)
        V.set_uv_rect(o, FLOOR_UV, axes=('x', 'y'))
        parts.append(o)
        # 蹴込板 — 一つ上の段の踏面の下端からこの段の天端まで
        o = V.box(name + "_keri%d" % i, (KEN, KERI_T, keri),
                  (0.0, y0 + KERI_T / 2.0, z + keri / 2.0), m_wood)
        V.set_uv_rect(o, WOOD_UV, axes=('x', 'z'))
        parts.append(o)

    # 側桁 — 段鼻を結ぶ勾配なりの材。左右
    for sx in (-1, 1):
        x = sx * (half - SIDE_W / 2.0)
        parts.append(slant_box(name + "_gawa", (x, 0.0, -SIDE_H / 2.0),
                               (x, run, -drop - SIDE_H / 2.0), SIDE_W, SIDE_H, m_wood, WOOD_UV))
        # 高欄 — 笠木・地覆・束
        parts.append(slant_box(name + "_kasagi", (x, 0.0, KORAN_H),
                               (x, run, KORAN_H - drop), KASA, KASA, m_wood, WOOD_UV))
        parts.append(slant_box(name + "_jifuku", (x, 0.0, 0.12),
                               (x, run, 0.12 - drop), JIFUKU, JIFUKU, m_wood, WOOD_UV))
        for i in range(n + 1):
            t = float(i) / n
            yy, zz = run * t, -drop * t
            o = V.box(name + "_tsuka%d" % i, (TSUKA, TSUKA, KORAN_H - 0.12),
                      (x, yy, zz + (0.12 + KORAN_H) / 2.0), m_wood)
            V.set_uv_rect(o, WOOD_UV, axes=('x', 'z'))
            parts.append(o)

    V.dedup_materials()
    o = V.join(parts, name)
    V.set_origin(o, (0.0, 0.0, 0.0))         # 原点 = 坂上・上段の廊下の床
    mn, mx = V.bbox([o])
    print("KAIDAN %-26s %.2f x %.2f x %.2f  段=%d 蹴上%.3f 踏面%.3f  tris=%d"
          % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, n, keri, fumi,
             sum(len(q.vertices) - 2 for q in o.data.polygons)))
    V.export_fbx(o, os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) >= 2:
        r, d = float(argv[0]), float(argv[1])
        build(r, d, argv[2] if len(argv) > 2 else "Goten_KaidanRoka_%gx%g" % (r, d))
    else:
        for r, d in SET:
            build(r, d, "Goten_KaidanRoka_%gx%g" % (r, d))
    print("BUILT -> %s" % OUT)
