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
# 棟もキットの実ジオメトリを継ぐ。roof top x1 = 冠瓦+熨斗瓦2段+紐が彫ってある 0.909m
RIDGE_MOD = "roof/roof top x1.fbx"
RIDGE_L, RIDGE_W, RIDGE_H = 0.909, 0.338, 0.366   # 実測(江戸間スケール後)
ONI_MOD = "roof/roof ornaments L.fbx"             # 0.437 x 0.989 x 0.593 棟端の鬼
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


def _mesh_from_poly(name, verts, faces, recalc=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) for v in verts], [], faces)
    me.update()
    if recalc:      # 閉じた立体は法線を外向きに揃える(表裏を手で数えると必ず間違える)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free(); me.update()
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


def _module(relpath, name):
    """キットのモジュールを1体だけ読んで1メッシュにする(継ぐ元)"""
    return V.join(V.place(relpath, 0, 0, 0), name)


def _frame(ax):
    """棟の軸 ax から (X=軸, Y=水平の横, Z=上) の正規直交基底の行列を作る"""
    side = ax.cross(Vector((0, 0, 1)))
    if side.length < 1e-9:
        return None
    side.normalize()
    up = side.cross(ax)
    return mathutils.Matrix(((ax.x, side.x, up.x, 0.0),
                             (ax.y, side.y, up.y, 0.0),
                             (ax.z, side.z, up.z, 0.0),
                             (0.0, 0.0, 0.0, 1.0)))


def ridge(p0, p1, name, w=0.46, h=0.38):
    """棟(大棟・隅棟)を **キットの棟モジュールを継いで**通す。返り値=オブジェクト列。

    ⚠ 以前は台形断面の押し出し箱に瓦アトラスの一点UVを貼っていた。瓦場だけが実ジオメトリで
       棟が無地の板になり、ユーザー指摘(bookmark 2026-08-15 #2「稜線の瓦が他の瓦に比べて
       リアルさを欠く」)。`roof top x1` は冠瓦・熨斗瓦2段・紐が彫り込んであるモジュールで、
       これを継げば大棟も隅棟も他の瓦と同じ密度になる。
    継ぎ目: 実長 L を整数 n で割り、モジュールを x 方向に L/n/0.909 だけ伸ばして継ぐ。
       端数が出ないので斜めの隅棟でも隙間・食い違いが出ない(以前ここで破綻した原因)。"""
    p0 = Vector(p0); p1 = Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-4:
        return []
    R = _frame(d.normalized())
    if R is None:
        return []
    n = max(1, int(round(L / RIDGE_L)))
    sx, sy, sz = (L / n) / RIDGE_L, w / RIDGE_W, h / RIDGE_H
    S = mathutils.Matrix.Diagonal((sx, sy, sz, 1.0))
    C = mathutils.Matrix.Translation((0.0, -RIDGE_W * sy / 2.0, 0.0))   # 断面を軸へ寄せる
    src = _module(RIDGE_MOD, name + "_m")
    out = []
    for i in range(n):
        o = src if i == 0 else src.copy()
        if i:
            bpy.context.scene.collection.objects.link(o)
        o.matrix_world = mathutils.Matrix.Translation(p0 + d * (float(i) / n)) @ R @ C @ S
        out.append(o)
    return out


def oni(p, out_dir, name, scale=1.0):
    """棟端の鬼瓦。p = 棟の端(軸上・屋根面レベル)、out_dir = 棟の外向き。
    ONI_MOD は長手が Y・立ちが Z で、鬼板が -Y 端に付く。-Y を外へ向ける。"""
    ax = Vector((out_dir[0], out_dir[1], out_dir[2] if len(out_dir) > 2 else 0.0))
    ax.z = 0.0
    if ax.length < 1e-9:
        return []
    ax.normalize()
    R = _frame(ax)
    o = _module(ONI_MOD, name)
    # モジュールのローカル: x 0..0.437 / y 0..0.989 / z 0..0.593。
    # 中心を軸へ寄せ、鬼板(-Y端)が外(+局所X)へ来るよう Y→-X に入れ替える
    M = mathutils.Matrix(((0.0, -1.0, 0.0, 0.0),
                          (1.0, 0.0, 0.0, 0.0),
                          (0.0, 0.0, 1.0, 0.0),
                          (0.0, 0.0, 0.0, 1.0)))
    S = mathutils.Matrix.Diagonal((scale, scale, scale, 1.0))
    C = mathutils.Matrix.Translation((-0.2185, -0.10, 0.0))   # x中心 / 鬼板を少し外へ出す
    o.matrix_world = mathutils.Matrix.Translation(Vector(p)) @ R @ M @ S @ C
    return [o]


def plaque(name, pts, xa, xb, mat, uv, sc=1.0, oy=0.0, oz=0.0):
    """(y,z) の閉多角形を X 方向 xa..xb に押し出した板。懸魚・鰭に使う。"""
    v = [(xa, oy + u * sc, oz + w * sc) for (u, w) in pts]
    v += [(xb, oy + u * sc, oz + w * sc) for (u, w) in pts]
    n = len(pts)
    f = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    f += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    o = _mesh_from_poly(name, v, f, recalc=True)
    if mat:
        o.data.materials.append(mat)
    if uv:
        V.set_uv(o, uv)
    return o


# wood アトラスの縦木理の一枚。**長さ方向を v(縦)に取る**。
# 一点貼りだとベタ塗りの茶色になって「木に見えない」(ユーザー指摘 2026-08-15 第2回)
WOOD_UV = (0.600, 0.03, 0.770, 0.97)


# wall C アトラスの無地の漆喰面。妻壁を一点貼りにすると白一色で「空が抜けている」
# ように見えるので、こちらも矩形で貼って地の斑を出す
WALLC_UV = (0.55, 0.34, 0.95, 0.62)


def _uv_by_vertex(o, table):
    """頂点インデックス -> (u,v) の表でUVを貼る。
    斜めに寝た板は軸で投影できないので、作図時の頂点の並びから直に決める。"""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    for pg in me.polygons:
        for li in pg.loop_indices:
            uvl[li].uv = table[me.loops[li].vertex_index]


# 蕪懸魚の輪郭(取り付き上端中央が原点。1.0 = 高さの目安)
GEGYO = [(0.24, 0.00), (0.30, -0.12), (0.31, -0.30), (0.25, -0.46),
         (0.14, -0.58), (0.07, -0.72), (0.00, -0.80),
         (-0.07, -0.72), (-0.14, -0.58), (-0.25, -0.46), (-0.31, -0.30),
         (-0.30, -0.12), (-0.24, 0.00)]
ROKUYO = [(0.10, -0.30), (0.05, -0.21), (-0.05, -0.21), (-0.10, -0.30),
          (-0.05, -0.39), (0.05, -0.39)]     # 六葉(懸魚の留め金具)


def gable(x, inward, y0, y1, zb, apex_y, apex_z, name, p, thick=0.14,
          bw=0.60, bt=0.22, drop=0.5, lattice=True, gegyo=True):
    """入母屋・切妻の妻。x = 妻壁の面、inward = 棟の内側の向き(+1/-1)。返り値 = [(obj, uv)]。

    ユーザー指摘(bookmark 2026-08-15 #3,4,5)「破風・妻壁がただのポリゴンでリアルさを欠く」
    への手当て。二条城二の丸御殿・福井城御座所の妻飾りに倣って、
      ・妻壁は **木連格子**(縦の組子を1尺ピッチ + 貫3段)で埋める
      ・拝みに **蕪懸魚 + 六葉**、両下端に **桁隠しの懸魚**
      ・破風板は化粧板 + 裏甲の二枚重ねにして見付の影を出す
    を足す。渡廊下の切妻は lattice=False / gegyo=False(小屋根なので飾らない)。

    ⚠ 妻壁は **内側にだけ**厚みを持たせる(以前は SOLIDIFY で両側に出ていて、外側の
       0.07 が瓦の上に白い筋になって見えていた — bookmark の 3 と 5 はその筋)。"""
    m_wall, m_wood = p['wall'], p['wood']
    uv_wall, uv_wood, uv_dark = p['uv_wall'], p['uv_wood'], p['uv_dark']
    xi = x + inward * thick
    out = []

    # --- 妻壁(三角柱。厚みは内側だけ) ---
    v = [(x, y0, zb), (x, y1, zb), (x, apex_y, apex_z),
         (xi, y0, zb), (xi, y1, zb), (xi, apex_y, apex_z)]
    f = [[0, 1, 2], [5, 4, 3], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]]
    tw = _mesh_from_poly(name + "_tsuma", v, f, recalc=True)
    tw.data.materials.append(m_wall)
    if lattice:
        V.set_uv_rect(tw, WALLC_UV, axes=('y', 'z'))
        out.append((tw, None))
    else:
        out.append((tw, uv_wall))

    gh = apex_z - zb                      # 妻の高さ
    hw = (y1 - y0) / 2.0                  # 半幅
    xf = x                                # 飾り(組子)が乗る妻壁の面
    xout = x - inward * (bt * 1.15)       # 破風板の外面。懸魚はここへ打つ

    def edge_z(u):
        """妻の中心から u 離れた所の破風の内法(妻壁の上端)"""
        return apex_z - gh * (abs(u) / hw)

    # --- 妻壁の足元の水切り板 ---------------------------------------------
    # 妻壁は寄棟面の天端(z=zb)に載る。瓦の実体は名目平面より 0.15 ほど上にあるので、
    # 何も入れないと **瓦の波形が直接壁と組子に食い込んで、木ではありえない
    # グニャグニャの縁**になる(ユーザー指摘 2026-08-15 第2回)。
    # 実物と同じく横一文字の水切り(雨押え)板を壁面に打って瓦の口を隠す。
    z_base = zb + 0.20                              # 組子はこの板の上から立てる
    if lattice:
        mz = V.box(name + "_mizukiri", (0.22, y1 - y0, 0.34),
                   (x - inward * 0.11, (y0 + y1) / 2.0, zb + 0.03), m_wood)
        V.set_uv_rect(mz, WOOD_UV, axes=('z', 'y'))   # 木理は長手(y)方向へ
        out.append((mz, None))

    # --- 木連格子(縦の組子 + 貫)------------------------------------------
    if lattice:
        pitch, sw, sd = 0.303, 0.055, 0.05          # 1尺ピッチ / 見付 / 出
        def slat(u):
            z1 = edge_z(u) - 0.20
            if z1 <= z_base + 0.12:
                return False
            o = V.box(name + "_koshi", (sd, sw, z1 - z_base),
                      (xf - inward * sd / 2.0, apex_y + u, (z_base + z1) / 2.0), m_wood)
            V.set_uv_rect(o, WOOD_UV, axes=('x', 'z'))
            out.append((o, None))
            return True
        slat(0.0)
        k = 1
        while k * pitch < hw - 0.35:
            for s in (-1, 1):
                if not slat(s * k * pitch):
                    break
            k += 1
        for fr in (0.18, 0.46, 0.74):               # 貫3段。その高さでの妻の幅に切る
            z = zb + gh * fr
            wdt = 2.0 * hw * (1.0 - fr) - 0.30
            if wdt < 0.4 or z < z_base:
                continue
            o = V.box(name + "_nuki", (sd * 1.2, wdt, 0.075),
                      (xf - inward * sd * 0.6, apex_y, z), m_wood)
            V.set_uv_rect(o, WOOD_UV, axes=('x', 'y'))
            out.append((o, None))

    # --- 破風板(化粧板 + 下端の眉)+ 桁隠しの懸魚 --------------------------
    sc = max(0.50, min(1.50, gh * 0.50))       # 懸魚の丈(妻の高さの半分を目安)
    for a0, b0 in [((x, y0, zb), (x, apex_y, apex_z)), ((x, y1, zb), (x, apex_y, apex_z))]:
        a0 = Vector(a0); b0 = Vector(b0)
        dn = (b0 - a0).normalized()
        up = Vector((0, -dn.z, dn.y))
        if up.z < 0:                       # 2本目は向きが逆になる。上を上に揃える
            up = -up
        up.normalize()
        a = a0 - dn * (bw * 0.15)          # 軒側へ少し出す
        b = b0 + dn * 0.06                 # 拝みで少し交差させる
        # (名前, 板幅, 板厚, 面のオフセット, 板の中心のずれ)
        for tag, wid, thk, off, ctr in [
                ("_hafu", bw, bt, 0.0, (0.5 - drop) * bw),
                ("_mayu", bw * 0.20, bt * 0.55, bt * 0.60, (0.10 - drop) * bw)]:
            d = Vector((-inward * (thk / 2.0 + off), 0, 0))
            lo, hi = up * ctr - up * (wid / 2.0), up * ctr + up * (wid / 2.0)
            t = Vector((thk / 2.0, 0, 0))
            vs = [a + d + lo - t, a + d + hi - t, b + d + hi - t, b + d + lo - t,
                  a + d + lo + t, a + d + hi + t, b + d + hi + t, b + d + lo + t]
            fs = [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2],
                  [2, 6, 7, 3], [3, 7, 4, 0]]
            bd = _mesh_from_poly(name + tag, vs, fs, recalc=True)
            bd.data.materials.append(m_wood)
            # 頂点の並びは [a-lo, a+hi, b+hi, b-lo] × 表裏。長さ(a→b)を v、幅を u に取る
            u0, v0, u1, v1 = WOOD_UV
            if tag == "_mayu":                       # 眉は板の中でも端の一筋を使う
                u1 = u0 + (u1 - u0) * 0.25
            _uv_by_vertex(bd, {0: (u0, v0), 1: (u1, v0), 2: (u1, v1), 3: (u0, v1),
                               4: (u0, v0), 5: (u1, v0), 6: (u1, v1), 7: (u0, v1)})
            out.append((bd, None))
        # 桁隠しの懸魚は付けない — 妻の下端は隅棟と軒がすぐ下にあり、
        # 垂れ下がった板が瓦を突き抜ける(実際に試して debris に見えた)

    # --- 拝みの懸魚(蕪懸魚 + 六葉)---------------------------------------
    if gegyo:
        g = plaque(name + "_gegyo", GEGYO, xout - inward * 0.07, xout,
                   m_wood, None, sc=sc, oy=apex_y, oz=apex_z - 0.03)
        V.set_uv_rect(g, WOOD_UV, axes=('y', 'z'))
        out.append((g, None))
        out.append((plaque(name + "_rokuyo", ROKUYO, xout - inward * 0.105, xout - inward * 0.07,
                           m_wood, uv_dark, sc=sc, oy=apex_y, oz=apex_z - 0.03), uv_dark))
    return out


def palette():
    """破風・妻壁のマテリアルと代表UV。Village Kit から借りる
    — 名前を保つと Unity 側で既存の .mat に Search&Remap で当たる。"""
    return {
        'wood': V.borrow_material("Walls and floors/column A.fbx", "wood"),
        'wall': V.borrow_material("Walls and floors/wall C.fbx", "wall C"),
        'roof': {m.name: m for m in bpy.data.materials}.get('roof'),
        'uv_roof': V.sample_uv(MOD, pick_high=True),
        'uv_wall': V.sample_uv_bright("Walls and floors/wall C.fbx", "wall C"),          # 漆喰
        'uv_wood': V.sample_uv("Walls and floors/column A.fbx", pick_high=True),
        'uv_dark': V.sample_uv_bright("Walls and floors/wall C.fbx", "wall C", 'dark'),  # 組子・裏甲
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

    # 大棟・隅棟 — キットの棟モジュールを継ぐ(UVは触らない)
    pieces += ridge((x0 + a, y0 + cy, h), (x0 + Wp - a, y0 + cy, h),
                    name + "_omune", w=0.50, h=0.42)
    for (cx, cyy, tx, ty) in [(0, 0, a, a), (Wp, 0, Wp - a, a),
                              (0, Dp, a, Dp - a), (Wp, Dp, Wp - a, Dp - a)]:
        pieces += ridge((x0 + cx, y0 + cyy, 0.02), (x0 + tx, y0 + ty, hb),
                        name + "_sumi", w=0.40, h=0.33)
    # 大棟の両端の鬼(妻の拝みの上に載る)
    pieces += oni((x0 + a, y0 + cy, h), (-1, 0), name + "_oni0", scale=1.15)
    pieces += oni((x0 + Wp - a, y0 + cy, h), (1, 0), name + "_oni1", scale=1.15)

    # 妻(妻壁+木連格子+破風+懸魚)。inward = 棟の内側
    # 破風は drop=0.55 = 板の 45% を屋根面より上へ出す。瓦の実体は名目平面より 0.15 上に
    # あるので、これより低いと板の天端を瓦の波形が食って縁がグニャグニャになる
    new_geo = gable(x0 + a, +1, y0 + a, y0 + Dp - a, hb, y0 + cy, h, name + "_gW", p,
                    bw=0.62, drop=0.55)
    new_geo += gable(x0 + Wp - a, -1, y0 + a, y0 + Dp - a, hb, y0 + cy, h, name + "_gE", p,
                     bw=0.62, drop=0.55)
    # 袖瓦(破風の天端に被る瓦の列)。妻の稜線に沿って小さい棟モジュールを通す。
    # これが無いと瓦場を切った断面と破風板の天端が白い筋になって見える(bookmark #3/#5)。
    # 屋根面の名目平面より瓦の実体が上にあるので 0.22 持ち上げ、破風板の外面へ寄せて被せる
    for gx, inward in ((x0 + a, +1), (x0 + Wp - a, -1)):
        sx = gx - inward * 0.06
        for uy in (y0 + a, y0 + Dp - a):
            pieces += ridge((sx, uy, hb + 0.22), (sx, y0 + cy, h + 0.22),
                            name + "_sode", w=0.36, h=0.28)

    for o, uv in new_geo:
        if o:
            if uv:                       # uv=None は既に矩形貼り済み(木理を出す板)
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
    # 大棟 — 端の出まで通して妻を塞ぐ。棟の軒下をくぐるので入母屋より一回り小さく。
    # 座を 0.13 下げて瓦に食い込ませる。棟幅0.36 の端では屋根面が 0.098 下がるので、
    # 浮かせると棟の脇に隙間が抜けて見える
    # ⚠ 高さ 0.26 は EdoGotenKit.ROKA_RIDGE(=0.953)の内訳。変えると棟の軒下をくぐる
    #   高さの予算(README の表)が狂うので、C# 側の定数と一緒に直すこと
    pieces += ridge((x0, ym, h - 0.13), (x1, ym, h - 0.13), name + "_omune",
                    w=0.36, h=0.26)
    # 破風(+ 妻壁)。渡廊下なので板は入母屋より小振りにして、大半を屋根面より下へ垂らす。
    # 小屋根なので木連格子・懸魚は付けない
    new_geo = []
    for gx, inward in ((x0, +1), (x1, -1)):
        g = gable(gx, inward, y0, y1, 0.0, ym, h, name + "_g", p,
                  thick=0.10, bw=0.22, bt=0.06, drop=0.72, lattice=False, gegyo=False)
        if not tsuma:
            bpy.data.objects.remove(g[0][0], do_unlink=True)   # 妻壁(先頭)は捨てる
            g = g[1:]
        new_geo += g

    for o, uv in new_geo:
        if o:
            if uv:                       # uv=None は既に矩形貼り済み(木理を出す板)
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


def build_irimoya_existing():
    """OUT にある入母屋を **同じ寸法で全部作り直す**。
    棟・妻の作りを変えたら屋根は寸法ごとに1本なので全数を焼き直す必要がある。
        blender --background --python Tools/Blender/build_goten_roof.py -- rebuild"""
    import re
    jobs = []
    for f in sorted(os.listdir(OUT)):
        if f == "Goten_Roof_Irimoya.fbx":
            jobs.append((f[:-4], 8, 5))                     # 既定の 8間x5間
        else:
            m = re.match(r"Goten_Roof_Irimoya_(\d+)x(\d+)(?:ken)?\.fbx$", f)
            if m:
                jobs.append((f[:-4], int(m.group(1)), int(m.group(2))))
    for name, w, d in jobs:
        V.reset()
        o = make_irimoya(w * KEN, d * KEN, name)
        report(o, name)
        V.export_fbx(o, os.path.join(OUT, name + ".fbx"))
    print("REBUILT %d irimoya" % len(jobs))


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
    if argv and argv[0] == "rebuild":
        build_irimoya_existing()
        build_kirizuma_set()
        raise SystemExit(0)
    if argv and argv[0] == "noboriro":
        # 登廊(階段廊下)の屋根 — 切妻を斜長ぶん通し、幅は石段の平場ぶん取る。
        # 据えるときに勾配ぶん傾けるので、屋根そのものは平らに作ってよい。
        #   -- noboriro <斜長> <幅> [名前]
        W = float(argv[1]); D = float(argv[2])
        name = argv[3] if len(argv) > 3 else "Goten_Roof_Noboriro_%gx%g" % (W, D)
        V.reset()
        o = make_kirizuma(W, D, name)
        mn, mx = report(o, name)
        V.export_fbx(o, os.path.join(OUT, name + ".fbx"))
        raise SystemExit(0)
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
