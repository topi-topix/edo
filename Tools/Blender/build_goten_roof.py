"""御殿の屋根を棟の寸法から生成する。

    # 入母屋(棟の屋根)
    blender --background --python Tools/Blender/build_goten_roof.py -- W D [name]
    # 切妻(渡廊下の屋根)を定尺で一括生成
    blender --background --python Tools/Blender/build_goten_roof.py -- kirizuma

方式:
  瓦は Village Kit の `roof 2x2` を**実ジオメトリのまま**流し葺きにして、
  屋根面の平面ポリゴンでブーリアンに切る(テクスチャ板に置き換えると質が落ちるため)。
  キットに無い 大棟・隅棟・破風・妻壁 はここで新造する。

入母屋の作図(平面):
  外周 W'=W+2E, D'=D+2E。軒先 z=0、勾配比 ratio(水平1に対する立上り)。
  大棟は y=D'/2、高さ h=(D'/2)*ratio。妻(破風)は z=hb で立ち上がり、
  そこまでの端部は隅(寄棟面)。a = hb/ratio が妻の平面上の入り込み。
"""
import bpy, bmesh, sys, os, math, mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

MOD = "roof/roof 2x2.fbx"
# roof 2x2 の実測: 流れ方向(X)2.095 / 桁行(Y)2.004 / 立上り 1.143
MOD_RUN, MOD_LEN, MOD_RISE = 2.095, 2.004, 1.143
RATIO = MOD_RISE / MOD_RUN          # 0.5456 ≒ 5.5寸勾配
COURSE = 0.357                      # 瓦の段ピッチ(流れ方向)
STEP_RUN = COURSE * 5               # 1.785 = 5段。1段分重ねて葺くと段が通る
STEP_RISE = STEP_RUN * RATIO
OUT = "/Users/toshio/project/edo-unity/Assets/Edo/Models/Goten/Roofs"

KEN = 1.818                         # 江戸間。渡廊下は幅1間
ROKA_EAVE = 0.60                    # 渡廊下の軒の出(棟の 0.90 より浅い)
ROKA_END = 0.30                     # 妻側の出。棟の軒下へ差し込んで取り合いの隙間を消す
ROKA_KEN_SET = (2, 3, 4, 5, 6, 7, 8, 9, 12)  # 定尺。瓦の繰り返し 1.785/2.004 は江戸間と割り切れないので
                                    # 「1間モジュールを並べる」ができない → 長さごとに1本作る


def _mesh_from_poly(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def clip_convex(obj, poly2d):
    """凸ポリゴンの各辺で鉛直に bisect して外側を捨てる。
    ⚠ ブーリアンは使えない — 瓦場は重なり合った非マニフォールドの塊なので
       EXACT ソルバが「中身が詰まっている」と誤判定して型そのものを返す(実際にやった)。"""
    p = list(poly2d)
    area = sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
               for i in range(len(p)))
    if area < 0:                       # CCW に揃える(内側=各辺の左)
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
        # bisect は面を持たない頂点・辺を残す。消さないとバウンズが嘘をつく
        loose_e = [e for e in bm.edges if not e.link_faces]
        bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
        loose_v = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose_v, context='VERTS')
        bm.to_mesh(me); bm.free()
    me.update()
    return obj


def tile_field(convex_polys, eave_origin, yaw_deg, z_eave, name):
    """屋根面を瓦場で葺く。convex_polys = その面を覆う凸ポリゴンの列
    (同じ格子から切り出すので継ぎ目で瓦の段は通る)。
    yaw_deg = 上り勾配の向き(0 = +X へ上る)。eave_origin = 軒先線上の基準点。"""
    # 面の範囲を「流れ(u)・桁行(v)」のローカル系に落として、必要な枚数だけ葺く
    c, s = math.cos(math.radians(-yaw_deg)), math.sin(math.radians(-yaw_deg))
    us, vs = [], []
    for poly in convex_polys:
        for q in poly:
            dx, dy = q[0] - eave_origin[0], q[1] - eave_origin[1]
            us.append(dx * c - dy * s)
            vs.append(dx * s + dy * c)
    i0 = int(math.floor(min(us) / STEP_RUN)) - 1
    i1 = int(math.ceil(max(us) / STEP_RUN)) + 1
    j0 = int(math.floor(min(vs) / MOD_LEN)) - 1
    j1 = int(math.ceil(max(vs) / MOD_LEN)) + 1
    objs = []
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            o = V.place(MOD, 0, 0, 0, scale=1.0)
            for ob in o:
                ob.location += Vector((i * STEP_RUN, j * MOD_LEN, i * STEP_RISE))
            objs += o
    V.dedup_materials()
    field = V.join(objs, name + "_field")
    V.rotate_z([field], yaw_deg)
    field.location = Vector((eave_origin[0], eave_origin[1], z_eave))
    V.sel([field])
    bpy.ops.object.transform_apply(location=True)

    out = []
    for n, poly in enumerate(convex_polys):
        V.sel([field])
        bpy.ops.object.duplicate()
        dup = bpy.context.view_layer.objects.active
        dup.name = "%s_%d" % (name, n)
        clip_convex(dup, poly)
        if len(dup.data.polygons) == 0:
            bpy.data.objects.remove(dup, do_unlink=True)
        else:
            out.append(dup)
    bpy.data.objects.remove(field, do_unlink=True)
    return V.join(out, name) if out else None


def ridge(p0, p1, name, mat=None, w=0.36, h=0.30):
    """棟(大棟・隅棟)。roof top を並べる代わりに断面を押し出した箱で作る
    — 斜めの隅棟にモジュールを並べると継ぎ目が破綻するため。"""
    p0 = Vector(p0); p1 = Vector(p1)
    d = (p1 - p0)
    L = d.length
    if L < 1e-4:
        return None
    dn = d.normalized()
    side = Vector((-dn.y, dn.x, 0)).normalized() * (w / 2)
    up = Vector((0, 0, 1)) * h
    # 台形断面(下が広い)
    verts = []
    for p in (p0, p1):
        verts += [p - side, p + side, p + side * 0.45 + up, p - side * 0.45 + up]
    faces = [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7],
             [3, 2, 1, 0], [4, 5, 6, 7]]
    o = _mesh_from_poly(name, verts, faces)
    if mat:
        o.data.materials.append(mat)
    return o


def gable(x, y0, y1, zb, apex_y, apex_z, name, wall_mat, wood_mat, thick=0.14,
          bw=0.60, bt=0.22, drop=0.5):
    """妻壁(三角)と破風板。x = 妻の位置、法線は ±X。
    bw/bt = 破風板の幅・厚み、drop = そのうち屋根面より下に垂れる割合
    (既定は入母屋の寸法。渡廊下の切妻はもっと小さい板を使う)。"""
    v = [(x, y0, zb), (x, y1, zb), (x, apex_y, apex_z)]
    wall = _mesh_from_poly(name + "_tsuma", v, [[0, 1, 2]])
    if wall_mat:
        wall.data.materials.append(wall_mat)
    sol = wall.modifiers.new("s", 'SOLIDIFY'); sol.thickness = thick
    V.sel([wall]); bpy.ops.object.modifier_apply(modifier="s")
    # 破風板: 妻の2辺に沿った板
    boards = []
    for a, b in [((x, y0, zb), (x, apex_y, apex_z)), ((x, y1, zb), (x, apex_y, apex_z))]:
        a = Vector(a); b = Vector(b)
        dn = (b - a).normalized()
        up = Vector((0, -dn.z, dn.y))
        if up.z < 0:                       # 2本目の垂木は向きが逆になる。上を上に揃える
            up = -up
        up.normalize()
        hi, lo = up * (bw * (1.0 - drop)), up * (bw * drop)       # 板幅(屋根面の上/下)
        t = Vector((bt / 2.0, 0, 0))                              # 板厚(X方向)
        vs = [a - lo - t, a + hi - t, b + hi - t, b - lo - t,
              a - lo + t, a + hi + t, b + hi + t, b - lo + t]
        fs = [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2],
              [2, 6, 7, 3], [3, 7, 4, 0]]
        bd = _mesh_from_poly(name + "_hafu", vs, fs)
        if wood_mat:
            bd.data.materials.append(wood_mat)
        boards.append(bd)
    return [wall] + boards


def palette():
    """破風・妻壁のマテリアルと代表UV。Village Kit から借りる
    — 名前を保つと Unity 側で既存の .mat に Search&Remap で当たる。"""
    return {
        'wood': V.borrow_material("Walls and floors/column A.fbx", "wood"),
        'wall': V.borrow_material("Walls and floors/wall C.fbx", "wall C"),
        'roof': {m.name: m for m in bpy.data.materials}.get('roof'),
        'uv_roof': V.sample_uv(MOD, pick_high=True),
        'uv_wall': V.sample_uv("Walls and floors/wall C.fbx", pick_high=True),   # 漆喰
        'uv_wood': V.sample_uv("Walls and floors/column A.fbx", pick_high=True),
    }


def make_irimoya(W, D, name="Goten_Roof", eave=0.90, gable_frac=0.45):
    """W=桁行(X) D=梁間(Y) の棟に入母屋屋根を架ける。返り値=1メッシュ"""
    Wp, Dp = W + 2 * eave, D + 2 * eave
    cy = Dp / 2
    h = cy * RATIO                      # 大棟高さ(軒先からの)
    hb = h * gable_frac                 # 妻の立上り位置
    a = hb / RATIO                      # 妻の平面上の入り込み
    x0, y0, x1, y1 = -eave, -eave, W + eave, D + eave

    def P(px, py):
        return (x0 + px, y0 + py)

    pieces = []
    # 南流れ = 軒先の台形 + 妻から上の矩形(凸2枚に割って同じ格子から切る)
    south = [[P(0, 0), P(Wp, 0), P(Wp - a, a), P(a, a)],
             [P(a, a), P(Wp - a, a), P(Wp - a, cy), P(a, cy)]]
    pieces.append(tile_field(south, P(0, 0), 90, 0.0, name + "_S"))
    north = [[P(Wp, Dp), P(0, Dp), P(a, Dp - a), P(Wp - a, Dp - a)],
             [P(Wp - a, Dp - a), P(a, Dp - a), P(a, cy), P(Wp - a, cy)]]
    pieces.append(tile_field(north, P(0, Dp), 270, 0.0, name + "_N"))
    # 東西の隅(寄棟面)
    pieces.append(tile_field([[P(0, 0), P(a, a), P(a, Dp - a), P(0, Dp)]],
                             P(0, 0), 0, 0.0, name + "_W"))
    pieces.append(tile_field([[P(Wp, Dp), P(Wp - a, Dp - a), P(Wp - a, a), P(Wp, 0)]],
                             P(Wp, 0), 180, 0.0, name + "_E"))

    p = palette()
    m_wood, m_wall, m_roof = p['wood'], p['wall'], p['roof']
    uv_roof, uv_wall, uv_wood = p['uv_roof'], p['uv_wall'], p['uv_wood']

    new_geo = []
    # 大棟
    new_geo.append((ridge((x0 + a, y0 + cy, h), (x0 + Wp - a, y0 + cy, h),
                          name + "_omune", m_roof, w=0.46, h=0.38), uv_roof))
    # 隅棟 4本
    for (cx, cyy, tx, ty) in [(0, 0, a, a), (Wp, 0, Wp - a, a),
                              (0, Dp, a, Dp - a), (Wp, Dp, Wp - a, Dp - a)]:
        new_geo.append((ridge((x0 + cx, y0 + cyy, 0.02), (x0 + tx, y0 + ty, hb),
                              name + "_sumi", m_roof, w=0.38, h=0.30), uv_roof))
    # 妻(破風+妻壁)
    for gx in (x0 + a, x0 + Wp - a):
        w, h1, h2 = gable(gx, y0 + a, y0 + Dp - a, hb, y0 + cy, h,
                          name + "_g", m_wall, m_wood)
        new_geo += [(w, uv_wall), (h1, uv_wood), (h2, uv_wood)]

    for o, uv in new_geo:
        if o:
            V.set_uv(o, uv)
            pieces.append(o)

    pieces = [p for p in pieces if p]
    V.dedup_materials()
    o = V.join(pieces, name)
    V.set_origin(o, (W / 2, D / 2, 0.0))
    return o


def make_kirizuma(W, D=KEN, name="Goten_Roof_Kirizuma", eave=ROKA_EAVE,
                  end=ROKA_END, tsuma=False):
    """W=桁行(X・大棟の方向) D=梁間(Y) の低い切妻。渡廊下の屋根。返り値=1メッシュ

    雁行する棟どうしの屋根の取り合いは **(a) 渡廊下の低い切妻で処理する**(ユーザー裁定
    2026-08-14)。谷・隅は作らず、この屋根を棟の軒下へ潜らせる。福井図・二条城も同じ形。
      → 大棟の天端は棟の軒先より低く納めること。EdoGotenKit.Roka が高さを決める。

    作図(平面): 外周 y は -eave .. D+eave、x は -end .. W+end。
    大棟は y=(D)/2、高さ h=(D/2+eave)*RATIO。両流れなので寄棟面は無い。
    妻(X両端)は破風板だけ立てる。**妻壁は既定オフ** — 端部は棟に突き付いて見えないため
    (tsuma=True にすると三角の漆喰壁が付く。片方が外に出る廊下用)。
    ピボットは廊下の中心・軒先レベル。端の出 end はピボットに含めない。
    """
    x0, x1 = -end, W + end
    y0, y1 = -eave, D + eave
    ym = (y0 + y1) / 2.0
    h = (y1 - y0) / 2.0 * RATIO

    pieces = []
    # 南流れ(+Yへ上る)/ 北流れ(-Yへ上る)。矩形1枚ずつ
    pieces.append(tile_field([[(x0, y0), (x1, y0), (x1, ym), (x0, ym)]],
                             (x0, y0), 90, 0.0, name + "_S"))
    pieces.append(tile_field([[(x1, y1), (x0, y1), (x0, ym), (x1, ym)]],
                             (x0, y1), 270, 0.0, name + "_N"))

    p = palette()
    new_geo = []
    # 大棟 — 端の出まで通して妻を塞ぐ。棟の軒下をくぐるので入母屋より一回り小さく。
    # 座を 0.13 下げて瓦に食い込ませる。棟幅0.36 の端では屋根面が 0.098 下がるので、
    # 浮かせると棟の脇に隙間が抜けて見える
    new_geo.append((ridge((x0, ym, h - 0.13), (x1, ym, h - 0.13), name + "_omune",
                          p['roof'], w=0.36, h=0.26), p['uv_roof']))
    # 破風(+ 妻壁)。渡廊下なので板は入母屋より小振りにして、大半を屋根面より下へ垂らす
    for gx in (x0, x1):
        wall, b1, b2 = gable(gx, y0, y1, 0.0, ym, h, name + "_g", p['wall'], p['wood'],
                             thick=0.10, bw=0.22, bt=0.06, drop=0.72)
        new_geo += [(b1, p['uv_wood']), (b2, p['uv_wood'])]
        if tsuma:
            new_geo.append((wall, p['uv_wall']))
        else:
            bpy.data.objects.remove(wall, do_unlink=True)

    for o, uv in new_geo:
        if o:
            V.set_uv(o, uv)
            pieces.append(o)

    pieces = [q for q in pieces if q]
    V.dedup_materials()
    o = V.join(pieces, name)
    V.set_origin(o, (W / 2, D / 2, 0.0))
    return o


def report(o, name):
    mn, mx = V.bbox([o])
    print("ROOF %-30s %6.2f x %6.2f x %6.2f  tris=%d  mats=%s"
          % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z,
             sum(len(q.vertices) - 2 for q in o.data.polygons),
             [m.name for m in o.data.materials]))
    return mn, mx


def build_kirizuma_set():
    """渡廊下の屋根を定尺で一括生成 → Goten_Roof_Kirizuma_<n>ken.fbx"""
    for n in ROKA_KEN_SET:
        V.reset()
        name = "Goten_Roof_Kirizuma_%dken" % n
        o = make_kirizuma(n * KEN, KEN, name)
        report(o, name)
        V.export_fbx(o, os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argv and argv[0] == "kirizuma":
        if len(argv) > 1:                       # 単発: -- kirizuma <間数>
            n = int(argv[1])
            V.reset()
            name = "Goten_Roof_Kirizuma_%dken" % n
            o = make_kirizuma(n * KEN, KEN, name)
            mn, mx = report(o, name)
            V.export_fbx(o, os.path.join(OUT, name + ".fbx"))
            W, D = n * KEN, KEN
        else:
            build_kirizuma_set()
            raise SystemExit(0)
    else:
        W = float(argv[0]) if argv else 1.818 * 8
        D = float(argv[1]) if len(argv) > 1 else 1.818 * 5
        name = argv[2] if len(argv) > 2 else "Goten_Roof_Irimoya"
        V.reset()
        o = make_irimoya(W, D, name)
        mn, mx = report(o, name)
        V.export_fbx(o, os.path.join(OUT, name + ".fbx"))

    if os.environ.get("GOTEN_PREVIEW"):
        V.hook_textures()
        bpy.ops.mesh.primitive_plane_add(size=120, location=(W / 2, D / 2, -0.05))
        r = max(W, D)
        V.studio((W / 2 - r * 1.5, D / 2 - r * 2.1, mx.z + r * 1.15),
                 (W / 2, D / 2, mx.z * 0.4), res=(1600, 1000))
        V.render(os.environ["GOTEN_PREVIEW"])
