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
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Roofs"))

KEN = 1.818                         # 江戸間。渡廊下は幅1間
ROKA_EAVE = 0.60                    # 渡廊下の軒の出(棟の 0.90 より浅い)
ROKA_END = 0.30                     # 妻側の出。棟の軒下へ差し込んで取り合いの隙間を消す
ROKA_KEN_SET = (2, 3, 4, 5, 6, 7, 8, 9, 10, 12)  # 定尺。瓦の繰り返し 1.785/2.004 は江戸間と割り切れないので
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


def _frame(ax, rh=False):
    """棟の軸 ax から (X=軸, Y=水平の横, Z=上) の正規直交基底の行列を作る。

    ⛔⛔ **既定(rh=False)は行列式 −1 の左手系。**`side = ax × Z` の取り方のせいで、
      この行列で置いた駒は**鏡像**になる(2026-09-22 に det −1.83 を実測)。
      Blender は行列式が負のオブジェクトを描くとき法線を補正するので**レンダでは
      まったく気づけない**が、`V.join` が行列式 +1 の駒(瓦場など)へ join すると
      鏡だけが焼かれて**巻き順が裏返ったまま**残り、**Unity の裏面カリングで消える**。
      ⇒ 庫裏の「棟の真上に空が抜ける」の正体がこれだった(EDO-0354)。
    ⭕ <paramref name="rh"/>=True は `side = Z × ax` に取り直すだけ。**軸(X)と上(Z)の
      向きは変わらず、横(Y)の符号だけ**が返る。
    ⚠ **既定を替えていないのは `oni()` のため。**鬼瓦のモジュール(`roof ornaments L`)は
      y 鏡で **0.415m ずれる非対称**な駒なので、右手系へ替えると鬼が左右反転する。
      棟モジュール(`roof top x1`)は **y 鏡のずれ 0.000000m の完全対称**で、`C` が断面を
      軸へ寄せているから、`ridge()` は替えても**頂点が 1mm も動かない**(実測)。"""
    up_axis = Vector((0, 0, 1))
    side = up_axis.cross(ax) if rh else ax.cross(up_axis)
    if side.length < 1e-9:
        return None
    side.normalize()
    up = ax.cross(side) if rh else side.cross(ax)
    return mathutils.Matrix(((ax.x, side.x, up.x, 0.0),
                             (ax.y, side.y, up.y, 0.0),
                             (ax.z, side.z, up.z, 0.0),
                             (0.0, 0.0, 0.0, 1.0)))


def _flip_faces(o):
    """メッシュの巻き順を全部返す。**行列式が負の行列で置く駒**を、焼いたときに
    表が外を向くようにするために使う(⭕ 頂点は1つも動かない)。"""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    for f in bm.faces:
        f.normal_flip()
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return o


def ridge(p0, p1, name, w=0.46, h=0.38):
    """棟(大棟・隅棟)を **キットの棟モジュールを継いで**通す。返り値=オブジェクト列。

    ⚠ 以前は台形断面の押し出し箱に瓦アトラスの一点UVを貼っていた。瓦場だけが実ジオメトリで
       棟が無地の板になり、ユーザー指摘(bookmark 2026-08-15 #2「稜線の瓦が他の瓦に比べて
       リアルさを欠く」)。`roof top x1` は冠瓦・熨斗瓦2段・紐が彫り込んであるモジュールで、
       これを継げば大棟も隅棟も他の瓦と同じ密度になる。
    継ぎ目: 実長 L を整数 n で割り、モジュールを x 方向に L/n/0.909 だけ伸ばして継ぐ。
       端数が出ないので斜めの隅棟でも隙間・食い違いが出ない(以前ここで破綻した原因)。

    ⭕⭕ 2026-09-22(EDO-0354): **`_frame` を右手系で取る**ようにした。左手系のままだと
       棟モジュールが鏡像で置かれ、join で鏡が焼かれて**巻き順が裏返ったまま残り、
       Unity では大棟・隅棟・袖瓦が丸ごと消える**(Blender のレンダでは補正が効くので
       気づけない)。`roof top x1` は完全対称なので、**頂点は1つも動かない**。"""
    p0 = Vector(p0); p1 = Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-4:
        return []
    R = _frame(d.normalized(), rh=True)
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


def make_yosemune(W, D, name="Goten_Roof_Yosemune", eave=0.90):
    """**寄棟(四方に流れる)。** W=桁行(X) D=梁間(Y)。返り値=1メッシュ。

    【なぜ入母屋と別に要るか】土井邸の表役所 `Yakusho`(10×10間)は**役所であって御殿ではない**
      ので、御殿の入母屋より一段下げた寄棟・瓦葺とする(2026-09-06 考証方の判定【U】)。
      ⛔ **入母屋の妻を潰した代用にしない** — 妻壁・破風・木連格子・懸魚・袖瓦は
        **そもそも作らない**。四流れの瓦場と、大棟1本 + 隅棟4本だけで組む。

    【作図】軒の出 eave を四周に取った外周 W'×D'。四面とも同じ勾配 RATIO なので、
      隅の稜線は平面で **45°**、大棟の高さは h=(D'/2)·RATIO、大棟の長さは **W'−D'**。
      ⇒ 入母屋の `gable_frac` を 1.0 まで振り切った形と同じ骨格になるが、**妻が無いので
        軒先の台形2枚と三角2枚**で閉じる(入母屋の「妻から上の矩形」は現れない)。

    ⚠⚠ **正方形の平面(W=D)では大棟の長さが 0 になり、寄棟は必然的に方形造(宝形)になる。**
      これは作図の都合ではなく幾何の帰結 — 四面の勾配が等しい限り、正方形の寄棟は必ず
      隅棟4本が頂点で交わる四角錐になる。⇒ 頂点は **露盤**(方形造の常法)で塞ぐ。
      ⛔ 大棟が要るなら平面を長方形にするか入母屋に戻すしかない。**普請奉行の裁定事項。**
    """
    Wp, Dp = W + 2 * eave, D + 2 * eave
    if Dp > Wp:
        raise SystemExit("[yosemune] 桁行 %.3f < 梁間 %.3f — 桁行 ≧ 梁間 で呼ぶこと" % (W, D))
    cy = Dp / 2.0
    h = cy * RATIO                      # 大棟(=隅棟の頂点)の高さ
    a = cy                              # 隅の平面上の入り込み(45°なので梁間の半分)
    x0, y0 = -eave, -eave

    def P(px, py):
        return (x0 + px, y0 + py)

    pieces = []
    # 長手の二面 = 軒先の台形。短手の二面 = 三角(隅)
    pieces.append(tile_field([[P(0, 0), P(Wp, 0), P(Wp - a, a), P(a, a)]],
                             P(0, 0), 90, 0.0, name + "_S"))
    pieces.append(tile_field([[P(Wp, Dp), P(0, Dp), P(a, Dp - a), P(Wp - a, Dp - a)]],
                             P(0, Dp), 270, 0.0, name + "_N"))
    pieces.append(tile_field([[P(0, 0), P(a, a), P(a, Dp - a), P(0, Dp)]],
                             P(0, 0), 0, 0.0, name + "_W"))
    pieces.append(tile_field([[P(Wp, Dp), P(Wp - a, Dp - a), P(Wp - a, a), P(Wp, 0)]],
                             P(Wp, 0), 180, 0.0, name + "_E"))

    p = palette()
    r0, r1 = (x0 + a, y0 + cy, h), (x0 + Wp - a, y0 + cy, h)
    ridge_len = Wp - Dp
    if ridge_len > 0.35:
        pieces += ridge(r0, r1, name + "_omune", w=0.50, h=0.42)
        pieces += oni(r0, (-1, 0), name + "_oni0", scale=1.15)
        pieces += oni(r1, (1, 0), name + "_oni1", scale=1.15)
    # 隅棟4本。頂点は大棟の端(正方形なら1点に集まる)
    for (cx, cyy, tx, ty) in [(0, 0, a, a), (Wp, 0, Wp - a, a),
                              (0, Dp, a, Dp - a), (Wp, Dp, Wp - a, Dp - a)]:
        pieces += ridge((x0 + cx, y0 + cyy, 0.02), (x0 + tx, y0 + ty, h),
                        name + "_sumi", w=0.40, h=0.33)
    if ridge_len <= 0.35:
        # 方形造の頂点 — **露盤**で塞ぐ。⛔ 開けたままにしない(隅棟4本の小口が透ける)
        # ⚠ 材は瓦(`roof`)のまま。⛔ 新規マテリアルを作らない
        cxp, cyp = (r0[0] + r1[0]) / 2.0, r0[1]
        for (s, hgt, zb) in ((0.72, 0.16, h - 0.10), (0.52, 0.20, h + 0.06)):
            b = V.box(name + "_roban", (s, s, hgt), (cxp, cyp, zb + hgt / 2.0),
                      p['roof'], p['uv_roof'])
            pieces.append(b)

    pieces = [q for q in pieces if q]
    V.dedup_materials()
    o = V.join(pieces, name)
    V.set_origin(o, (W / 2, D / 2, 0.0))
    print("[yosemune] %s 桁行%.3f × 梁間%.3f / 軒の出%.2f / 大棟長 %.3f%s / 棟高 %.3f"
          % (name, W, D, eave, max(0.0, ridge_len),
             "(=0 → 方形造・露盤で納めた)" if ridge_len <= 0.35 else "", h))
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


# ---------------------------------------------------------------------------
# 帯割りの入母屋(make_banded)
# ---------------------------------------------------------------------------
# 【なぜ要るか】土井邸の御殿は **梁間10間超(18m超)を一枚の小屋組で飛ばして**いた。
#   現存例で最大の山脇武家屋敷門ですら梁間 4.7m で、**存在しない型**(2026-09-06 ユーザー裁定=案C)。
#   ⇒ 足形・室割り・廊下は動かさず、**身舎を帯に割って帯ごとに入母屋を架け、帯の境を谷にする**。
#
# 【幾何の要点 — ここを取り違えると全部おかしくなる】
#   ⭐ **下屋は「別の屋根」ではなく、身舎の流れの延長**になる。2026-09-06 裁定で
#     「下屋も同じ勾配」と決まったので、身舎の軒桁(z=eave)から入側の上を通って軒先まで
#     **一枚の平面**が続く。⇒ 実装上は「帯の入母屋に、外周側だけ軒の出
#     `E = irikawa×1.818 + noki_de` を付けた物」と等価。段は付かない。
#     ⭕ **欠陥ではなく裁定の帰結。2026-09-06 に「一枚の流れのままにする」で確定した。**
#     ⛔ **直さない** — 立面で入側と身舎の境が見えなくても勾配を変えないこと。
#     ⚠ 御殿の庇の勾配は【U】。[西川1959]A の「庇 4寸5分」は**長屋の構造の節**の値で、
#       御殿の庇へ当てるのは外挿。⛔ 手掛かり止まりにする。
#   ⭐ **谷は水平**。隣り合う帯はどちらも境で z=eave まで下りてくるので、谷線は
#     z=eave の水平線になる(帯の境=柱通りなので必ず整数間に乗る)。谷樋は両端で
#     妻側の下屋(x方向の流れ)へ落ちる。⛔ 谷を勾配で下げない — 帯の棟が傾く。
#   ⚠ **妻側(x方向)の下屋は、隣り合う帯どうしで完全に同一平面**なので、帯ごとに切って
#     並べても継ぎ目は出ない。ただし **瓦の格子の原点を帯ごとに取ると桁行方向にズレる**
#     (帯幅 4間=7.272 は瓦の桁行ピッチ 2.004 の整数倍でない)。⇒ 妻側の瓦場だけ
#     **全帯で共通の原点 (x0, 0)** から葺く。
VALLEY_GAP = 0.10        # 谷の左右で瓦場を引く量(谷樋の縁を瓦の下へ潜らせる代)
VALLEY_HALF = 0.30       # 谷樋の半幅


def _tile_field_fast(convex_polys, eave_origin, yaw_deg, z_eave, name):
    """`tile_field` と同じ物を作るが、瓦モジュールの **FBX 取り込みを1回だけ**にした版。

    ⚠ `tile_field` は格子の升ごとに `import_scene.fbx` を呼ぶ。帯割りの屋根は
      27×22m 級で1体あたり 500 升を超えるので、取り込みが律速になる。
      ⛔ 共有の `tile_field` は他邸(入母屋・寄棟・切妻)が使っているので触らない —
        同じ手順を写して、格子の複製だけ `o.copy()`(メッシュデータ共有)に替える。
    """
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

    unit = V.join(V.place(MOD, 0, 0, 0, scale=1.0), name + "_unit")
    objs = []
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            o = unit.copy()                       # メッシュデータは共有(join で実体化される)
            bpy.context.scene.collection.objects.link(o)
            o.location = Vector((i * STEP_RUN, j * MOD_LEN, i * STEP_RISE))
            objs.append(o)
    bpy.data.objects.remove(unit, do_unlink=True)
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


def _valley_gutter(y_v, x_a, x_b, z_eave, kobai, p, name, half=0):
    """谷樋。(y,z) 断面を X へ押し出した実体の樋。

    ⭐ `half` = 0(全断面・帯どうしの谷)/ +1(+Y 側の半分)/ −1(−Y 側の半分)。
      **半分は「棟の外形の線で隣の棟と接する辺」のため**(2026-09-10)。両隣がそれぞれ
      半分を出すと線の上で**一本の樋**になる。⛔ 両方が全断面を出すと重なって
      z ファイティングになる(見えの面が二枚重なる)。

    断面の天端は **瓦の実体の下**へ潜らせる(瓦は名目平面より −0.03〜+0.15 でうねるので、
    名目平面から 0.04 下げた所に縁を置くと、瓦の小口が樋に食い込んで隙が出ない)。
    ⛔ 板を1枚渡すだけにしない — 瓦の切り口と樋のあいだに光の筋が出る。実体で埋める。

    ⛔ **材は木で決着(2026-09-06 裁定)。銅にしない** — 2.3万石の御殿には過ぎる
      (葺材を桟瓦に決めたのと同じ理由)。⛔ 樋・雨落ちの意匠はこれ以上決めない —
      見えない部位に確度を積まない。"""
    top = kobai * VALLEY_HALF - 0.04
    if half > 0:
        pts = [(0.0, -0.07), (VALLEY_HALF, top), (VALLEY_HALF, -0.40), (0.0, -0.40)]
    elif half < 0:
        pts = [(-VALLEY_HALF, top), (0.0, -0.07), (0.0, -0.40), (-VALLEY_HALF, -0.40)]
    else:
        pts = [(-VALLEY_HALF, top), (0.0, -0.07), (VALLEY_HALF, top),
               (VALLEY_HALF, -0.40), (-VALLEY_HALF, -0.40)]
    g = plaque(name, pts, x_a, x_b, p['wood'], None, sc=1.0, oy=y_v, oz=z_eave)
    # 木理は樋の走り(x)へ流す。⚠ WOOD_UV は v が長手なので x→v に取る
    V.set_uv_rect(g, WOOD_UV, axes=('y', 'x'))
    return g


def _norm_irikawa(irikawa):
    """入側の指定を **郭グリッドの (u0, u1, v0, v1)**(単位=間)へ正規化する。

    受け取れる形:
      ``1``                       … 四周に同じ(旧来の呼び方。土井の帯割り屋根は全部これ)
      ``{"u":[0,0],"v":[1,1]}``   … ⭐ **指図 `munes[].roof.irikawa` の生の形**。これが正典
      ``(u0, u1, v0, v1)``        … 平たい4つ組
    ⛔ 端数は受けない — 入側は柱通りに乗るので整数間。
    """
    if isinstance(irikawa, dict):
        u = irikawa.get("u", [1, 1])
        v = irikawa.get("v", [1, 1])
        q = [u[0], u[1], v[0], v[1]]
    elif isinstance(irikawa, (list, tuple)):
        if len(irikawa) != 4:
            raise SystemExit("[banded] irikawa の4つ組は (u0,u1,v0,v1)。指定=%r" % (irikawa,))
        q = list(irikawa)
    else:
        q = [irikawa] * 4
    out = []
    for t in q:
        f = float(t)
        if abs(f - round(f)) > 1e-9 or not (0 <= f <= 3):
            raise SystemExit("[banded] 入側は 0〜3 の整数間。指定=%r" % (irikawa,))
        out.append(int(round(f)))
    return tuple(out)


def _map_sides(q, along):
    """グリッドの4つ組 (u0,u1,v0,v1) を **生成器の内部軸** (x0, x1, y0, y1) へ写す。

    ⭐ 入側も軒の有無も**同じ写像**を通す(⛔ 片方だけ別に書かない — 2026-09-09 に
      入側でここを取り違えて表向4棟が融けた)。写像の根拠は `_irikawa_sides` の註。
    """
    u0, u1, v0, v1 = q
    if along == "v":
        return (v0, v1, u0, u1)
    return (u1, u0, v0, v1)


def _norm_noki(noki):
    """**辺ごとに軒を出すか**の指定を郭グリッドの (u0,u1,v0,v1) の 0/1 へ正規化する。
    **1 = 軒を出す(既定)/ 0 = その辺は軒を出さない**(⭐ 棟の外形の線で屋根が終わる)。

    受け取れる形: ``1`` / ``{"u":[1,0],"v":[1,1]}`` / ``(1,0,1,1)``。

    ⭐⭐ **なぜ要るか(2026-09-09 普請検査の差し戻し)。** 松江松平の表向4棟は棟の外形が
      隣どうし**接している**(`munes[].u1` = 次の棟の `u0`)。そこへ四周へ一様に軒
      `noki_de` を出すと、隣どうしの軒が **2×noki_de = 1.80m 食い込む**。寄りのレンダでは
      **二つの軒先の間から空が透け、桟瓦の列が空中で途切れ、軒先が何にも載らずに宙に浮き**、
      目の高さでは軒線が **X 字に交差**して単一の谷線にならなかった。
      ⭕ 接する辺の軒を落とすと、屋根の面が棟の外形の線でぴたりと終わり、
        隣の棟の流れと**境界線の上で合わさって本物の谷**になる。
      ⛔ **屋根の面そのものを短くする(身舎や入側を削る)対処は採らない** — 室割りが変わる。
        落とすのは**軒の出だけ**で、`bands`/`spanKen`/`irikawa` は 1mm も動かない。
    """
    if isinstance(noki, dict):
        u = noki.get("u", [1, 1]); v = noki.get("v", [1, 1])
        q = [u[0], u[1], v[0], v[1]]
    elif isinstance(noki, (list, tuple)):
        if len(noki) != 4:
            raise SystemExit("[banded] noki の4つ組は (u0,u1,v0,v1)。指定=%r" % (noki,))
        q = list(noki)
    else:
        q = [noki] * 4
    out = []
    for t in q:
        i = int(t)
        if i not in (0, 1):
            raise SystemExit("[banded] noki は辺ごとに 0(落とす)か 1(出す)。指定=%r" % (noki,))
        out.append(i)
    return tuple(out)


def _irikawa_sides(irikawa, along):
    """グリッドの (u0,u1,v0,v1) を **生成器の内部軸**へ写す → (x=0側, x=W側, y=0側, y=D側)。

    ⭐⭐ **ここが 2026-09-09 の差し戻し1の急所。**内部は常に「桁行を Blender +X、
      帯を Blender +Y に並べ、along=="v" なら最後に +90° 回す」で組む。
      軸の鎖(`make_banded` の註と同じもの)を辿ると:
        grid u = −(Blender X の最終値) / grid v = +(Blender Y の最終値)
      ⇒ along=="v"(+90°: 内部(x,y) → Blender(−y, x)):
           内部 x = grid v(x=0 が v 小) / 内部 y = grid u(y=0 が u 小)
         along=="u"(回さない):
           内部 x = **−grid u**(⛔ x=0 が u の**大きい**側)/ 内部 y = grid v(y=0 が v 小)
      ⛔ along=="u" で u の順をそのまま渡すと**左右が入れ替わる**。
        ⚠ 入側が u0==u1 の棟(当邸は全棟そう)では**絶対に気づけない**。
    """
    return _map_sides(_norm_irikawa(irikawa), along)


def _verify_band_order(o, bands_in, acr_c, along, name):
    """⭐⭐ **焼いた直後に、帯が本当に across の小さい側から並んでいるかを実測する。**

    ⛔⛔ **非対称の帯では必ず通すこと。** 帯の並びは**立面からは見えない**
      (上から見ないと帯が見えない)ので、`--render` の立面でも、Unity 側の
      足形・棟高の数値QAでも**素通りする** — 足形も棟高も左右対称で合ってしまう。
      2026-09-07 に `4-5x10ken_v` が鏡像のまま Unity へ据わったのはこれが無かったから。

    やること: **天端から 0.02m 以内の頂点を集めて across 座標へ落とす**。
      across 座標(across の芯からの相対・m)は `along` によらず
        along=="v": u = −(局所 X) /  along=="u": v = +(局所 Y)
      ⛔⛔ **期待値は `bands_in`(呼び出し側=指図の `ws` の並び)から独立に立てる。**
        ⛔ 中で組んだ `info` から立てない — 中で並べ替えが復活しても検算が一緒にズレて
        素通りしてしまう(検査が測る集合を実装と同じ物にしない。CLAUDE.md 規則19)。
    """
    verts = o.data.vertices
    if not verts:
        raise SystemExit("[banded] 検算: 頂点が無い(%s)" % name)
    zmax = max(v.co.z for v in verts)

    def _across(v):
        return (-v.co.x if along == "v" else v.co.y)

    # 呼び出し側の並びから独立に「どの across にどの高さの大棟が来るはずか」を立てる
    edges = [0.0]
    for b in bands_in:
        edges.append(edges[-1] + b * KEN)
    # ⚠ ピボットは **身舎+入側(=棟の外形)の中心**。入側が辺ごとに違うと
    #   身舎の中心とはズレるので、`acr_c`(内部 across 座標でのピボット位置)で引く。
    cen = [(edges[i] + edges[i + 1]) / 2.0 - acr_c for i in range(len(bands_in))]
    wmax = max(bands_in)
    # 帯の棟の高さの差は幅の差だけで決まる。天端(座・鬼とも)が同じだけ下がる
    dz = [(b - wmax) / 2.0 * KEN * RATIO for b in bands_in]

    # ⭐ **帯ごとに「その大棟の芯で屋根の頂がいくつか」を測る。**
    #   ⛔ 高さで頂点を拾って across を見る作りにしない — 広い帯の斜面や隅棟が
    #     狭い帯の棟高を通過するので、余計な塊を拾って偽陽性になる(2026-09-08 実測)。
    #   ⇒ across で切って高さを見る。並びが入れ替われば必ず高さが食い違う。
    ok = True
    for i, b in enumerate(bands_in):
        sel = [v.co.z for v in verts if abs(_across(v) - cen[i]) <= 0.25]
        if not sel:
            raise SystemExit("[banded] 検算: 帯%d の大棟の芯(across %+.3f)に頂点が無い(%s)"
                             % (i, cen[i], name))
        got, want = max(sel), zmax + dz[i]
        bad = abs(got - want) > 0.05
        print("[banded]   %s 帯%d(%d間・大棟の芯 across %+.3f): 頂の高さ 実測 %.3f / 期待 %.3f"
              % ("⛔" if bad else "⭕", i, b, cen[i], got, want))
        ok = ok and not bad
    if not ok:
        raise SystemExit(
            "[banded] ⛔ **帯が across の逆側(または違う並び)に焼けている**(%s)。\n"
            "  ⇒ `bands` の並べ替えか回転の符号を疑うこと。⛔ 据え付け側で 180° 回して"
            "辻褄を合わせない — 部材の不良は部材で直す。" % name)
    if len(set(bands_in)) == 1:
        print("[banded]   ⚠ 全帯が同幅で並びが対称 — **鏡像は無害だが「対称だから正しい」ではない**。"
              "大棟の向きと谷の位置は別に測ること")
    return cen[bands_in.index(wmax)]


def make_banded(bands, span, along="u", irikawa=1.0, eave=3.4, kobai=RATIO,
                noki_de=0.90, tsuma_end=0.30, fukizai="sangawara",
                gable_frac=0.45, noki=1, name=None):
    """**身舎を帯に割り、帯ごとに入母屋を架けて境を谷にした屋根**を1メッシュで焼く。

    ⭐ **単位: `bands` / `span` / `irikawa` は「間」(整数間)。それ以外は m。**
      中で 1間 = 1.818m を掛ける。⛔ Village Kit の 2.0m/間 と混ぜない。

    引数:
      bands      帯の**身舎**の幅の配列(間・整数)。例 [4,4] [4,5] [5,5] [4] [3,3,4,4]。**1〜4 帯**
                 ⭐⭐ **並びは常に「across 軸(帯の並ぶ向き)の小さい側から」**。
                    `along` が u でも v でも変わらない(軸の鎖の帰結。下の註を読むこと)。
                    ⇒ 指図の `ws` をそのまま渡してよい。例) 土井の奥棟は across=u で
                    **u の小さい側から 4 → 5** なので `[4,5]`(名も `4-5x10ken_v`)。
      span       長手方向の**身舎**の長さ(間)。大棟はこの向きに架かる
      along      "u" = 大棟が Blender +X(= Unity +X)/ "v" = Blender +Y(= Unity −Z)。
                 ⚠ 帯は長手に**直交**する方向へ並ぶ(along="u" なら across は v、逆も同様)。
                 ⚠ 中身は常に「帯を Blender +Y へ並べ、"v" なら最後に +90° 回す」で組む。
                    ⛔ **`bands` を並べ替えてはいけない** — +90° の裏返しは
                    書き出しの `Unity X = −(Blender X)` がちょうど打ち消す(下の軸の鎖の註)。
                    2026-09-06 に入れた `bands[::-1]` は Blender 空間しか見ておらず、
                    `4-5x10ken_v` を鏡像で焼いた(2026-09-07 撤去)。
      irikawa    入側(=下屋)の幅(間)。⭐ **辺ごとに違ってよい**(2026-09-09)。
                 受ける形は3つ: `1`(四周同じ)/ `{"u":[u0,u1],"v":[v0,v1]}`(⭐ 指図の生の形)/
                 `(u0,u1,v0,v1)`。**単位は間・整数**で、**郭グリッドの軸**で数える。
                 ⛔ 生成器の内部軸で渡さない(`_irikawa_sides` が along を見て写す)。
                 ⚠ 入側の無い辺でも軒の出 `noki_de` は付く。総寸 = 身舎 + 入側(辺ごと) + 軒。
      eave       **軒高**(m・既定 3.4)= 身舎の軒桁の高さ。**床レベルからの値**
      kobai      瓦勾配(既定 0.5456)。⛔ **これ以外は受け付けない** —
                 瓦は `roof 2x2` の実ジオメトリで、立上りがモジュールに彫り込まれている
      noki_de    軒の出(m・既定 0.90)。入側の外の柱通りから先へ出る量
      tsuma_end  妻の出(m・既定 0.30)= **破風板の見付が妻壁面から外へ出る量**。
                 ⚠ 瓦場は妻壁面で切る(既存の入母屋と同じ)。板だけが外へ出る
      noki       ⭐ **辺ごとに軒を出すか**(2026-09-10)。`1`(四周出す・既定)/
                 `{"u":[1,0],"v":[1,1]}` / `(u0,u1,v0,v1)`。**0 = その辺は軒を出さない**。
                 ⇒ その辺では屋根の面が**棟の外形の線でぴたりと終わる**ので、外形が接する
                 隣の棟の流れと**境界線の上で合わさって本物の谷**になる。
                 ⛔ **妻側(大棟の両端 = `along` の軸の辺)は落とせない** — そこには
                   破風・懸魚・妻壁が付き、軒だけ落とすと板が宙に浮く。生成器が止める。
                 ⚠ 落としても `bands`/`span`/`irikawa` は動かない ⇒ **ピボットも棟の外形も不動**。
      fukizai    "sangawara"(桟瓦)| "hongawara"(本瓦)。**格の出し分け**。⛔ 懸魚では分けない
      gable_frac 妻の立上りが棟高に占める割合(既定 0.45)。既存の入母屋と同じ。
                 ⛔ **指図の欄にしない**(2026-09-06 裁定)— 御殿の妻を強調する典拠が無く、
                    摘みにすると根拠なくいじれる値が増える。**部材の既定値のまま**

    高さ(既定値・帯 4間 のとき。**すべて床上**):
      床 0 → 軒高 3.4 → 入側の外の柱通り 3.4 − 1.818×0.5456 = **2.408**
           → 軒先(0.90 先)**1.917** → 帯の棟 3.4 + 2×1.818×0.5456 = **5.384**
      ⚠ 「軒先高 2.408」は入側の外の柱通りの高さで、軒の出の先端はさらに 0.491 下がる。
        流れが同じ勾配で続く以上これは幾何の帰結。
      ⛔⛔ **床上と地盤上を取り違えない。** 御殿の床は地盤より `const.gotenFloor` = **0.62m**
        高いので、軒先の先端は **地盤上 2.537m**。立位の眼高 `const.eyeStand` = 1.45 に対し
        1.09m の余裕があり、**江戸の軒として低くない**。2026-09-06 に部材方も普請奉行も
        床上のまま読んで「低いのでは」と誤読した。⇒ **軒の出も軒高も動かさない**(同日裁定)。

    ピボット = **足形の中心・床レベル(z=0)**。
      ⚠⚠ **既存の `make_irimoya` / `make_yosemune` は z=0 が「軒先」**で、Unity 側が
        軒先高に置いている。**この関数だけ z=0 が床**。軒高を引数に取る以上そうするしかない。
        据えるときは棟の**床の高さ**に置く(軒先高を足さない)。
    """
    if fukizai not in ("sangawara", "hongawara"):
        raise SystemExit("[banded] fukizai は sangawara / hongawara のいずれか: %r" % fukizai)
    if fukizai == "hongawara":
        # ⛔ 黙って桟瓦で焼かない。キットの瓦材は `roof`(桟瓦)**1種だけ**で、
        #    もう1つの `Roof B` は瓦ではなく**板葺・茅のアトラス**(実測 2026-09-06)。
        #    本瓦の当てがあるのは Japanese Castle の `Roof Castle 6x8.fbx`
        #    (材 `Roof Castle A` / 8×6 キット単位 / **勾配 0.500**)で、
        #    勾配が 0.5456 と違うので **RATIO まわりを葺材ごとに分ける改修が要る**。
        raise SystemExit(
            "[banded] 本瓦はまだ焼けない。キットの瓦材は `roof`(桟瓦)1種のみ。\n"
            "  本瓦の候補 = Japanese Castle/Meshes/Exterior/Roof Castle 6x8.fbx\n"
            "  (材 `Roof Castle A` / 勾配 0.500 ≠ RATIO 0.5456)。\n"
            "  ⇒ 葺材ごとに勾配とモジュール寸法を持たせる改修が要る。部材方へ差し戻すこと。")
    if abs(kobai - RATIO) > 1e-3:
        raise SystemExit("[banded] 勾配は %.4f 固定(`roof 2x2` の実ジオメトリの立上り)。"
                         "変えると瓦モジュールが平面に乗らない。指定=%.4f" % (RATIO, kobai))
    bands = [int(b) for b in bands]
    bands_in = list(bands)              # ⭐ 検算の期待値はここから立てる(中の並びを見ない)
    if not 1 <= len(bands) <= 4:
        # ⚠ 上限は「谷が増えすぎて屋根が櫛になる」ことへの歯止めであって幾何の限界ではない
        #   (帯のループも谷のループも N 一般で書いてある)。2026-09-08 に松江松平の
        #   表役所 3-3-4-4 / 大台所 3-3-4-4 のために 3 → 4 へ広げた。⛔ さらに広げない —
        #   5帯だと谷が4本になり、御殿の小屋組として説明が付かない。
        raise SystemExit("[banded] 帯数は 1〜4。指定=%d" % len(bands))
    if any(b < 2 for b in bands):
        raise SystemExit("[banded] 帯の身舎は 2間 以上(1間だと妻が破綻する)。指定=%s" % bands)
    span = int(span)
    nk = _norm_noki(noki)                     # 郭グリッド (u0,u1,v0,v1)。1=軒を出す
    name = name or banded_name(bands, span, along, fukizai, irikawa, nk)

    # ⭐⭐ **`bands` の先頭は、`along` が u でも v でも「across 軸の小さい側」**。
    #   中身は常に「帯を Blender +Y へ並べ、along=="v" なら最後に +90° 回す」で組む。
    #   ⛔⛔ **並べ替えは要らない。** 2026-09-06 に「+90° で並びが裏返る」と見て
    #     `bands[::-1]` を入れたが、それは **Blender 空間だけを見た誤り**で、
    #     `Goten_Roof_Banded_4-5x10ken_v` が鏡像で焼かれた(2026-09-07 実測で判明)。
    #     ⇒ **軸の鎖を最後まで辿ること。**
    #
    #   【軸の鎖 — ここを端折ると必ず鏡像になる】
    #     (1) 書き出し: `V.export_fbx` は axis_up='Y' / axis_forward='-Z' なので
    #         **Unity X = −(Blender X) / Unity Y = Blender Z / Unity Z = −(Blender Y)**。
    #         ⚠ 右手系→左手系は行列式 −1 でしか繋がらない。「Blender +X = Unity +X」は誤り。
    #         典拠: `build_ishigaki_saka.py` の「Blender の +Y が Unity の −Z へ落ちる」
    #         (実装済み・実測済みの非対称部材)。
    #     (2) 据え付け: 屋根は `roofYaw = DeltaAngle(muneYaw, yawU)` で格子へ戻すので
    #         **モデル局所 +X = 格子の +u / 局所 +Z = 格子の −v**(EdoDoiBuilder の註)。
    #
    #   【帰結】内部で +Y に並べた先頭 i=0 は、along が u でも v でも across の小さい側に落ちる:
    #     ・along=="v": 内部 y=ym → +90° で Blender x=−ym → Unity x=+ym → u は ym の昇順。✓
    #     ・along=="u": 内部 y=ym → Unity z=−ym → v = −(局所 z) = +ym の昇順。✓
    #     ⇒ **どちらも `across 座標(across の芯からの相対) = ym − D/2`**。反転は不要。
    #   ⭕ 焼いた後に `_verify_band_order()` が実測で検算する(⛔ この註だけに頼らない)。

    W = span * KEN
    ys = [0.0]
    for b in bands:
        ys.append(ys[-1] + b * KEN)
    D = ys[-1]
    # ⭐⭐ **入側は辺ごと**(2026-09-09・松江松平の差し戻し1)。
    #   ⛔ **以前はスカラ1つを四周に当てていた。**指図の `bands`/`spanKen` は
    #     `munes[].roof.irikawa`(**軸ごとに [手前, 奥]**)を辺ごとに引いた**身舎**なので、
    #     `irikawa` が [1,1] でない軸では屋根が **1間ずつ過大**になる。松江松平では
    #     表向4棟が隣どうし 3.18間(5.78m)重なり、真上から見ると4棟が1枚の巨大な
    #     屋根に融けていた(棟梁の実測 2026-09-09)。
    #   ⛔ **横に縮めて辻褄を合わせない** — 瓦の目と破風が潰れる。総寸を作り直す。
    ir = _irikawa_sides(irikawa, along)       # 内部軸ごとの入側(間)
    # ⭐ **軒は辺ごとに出す/出さない**(2026-09-10・普請検査の差し戻し1)。
    #   ⛔ 妻側(内部 ±X = 大棟の両端)は落とせない — 破風・懸魚・妻壁が付く辺で、
    #     軒だけ落とすと板が何にも載らずに宙に浮く。⇒ ここで止める。
    nks = _map_sides(nk, along)               # 内部軸ごとの 0/1
    if not (nks[0] and nks[1]):
        raise SystemExit(
            "[banded] ⛔ **妻側の軒は落とせない**(along=%r・指定 noki=%s)。\n"
            "  妻側 = 大棟の両端で、破風・懸魚・妻壁・袖瓦が付く辺。軒だけ落とすと\n"
            "  破風板が何にも載らずに宙に浮く(2026-09-09 普請検査が画で捕まえた不良と同じ姿)。\n"
            "  ⇒ 棟の外形が妻側で隣と接するなら、それは屋根の形(両下・招き)の問題なので\n"
            "     指図方へ差し戻すこと。⛔ ここで軒だけ落として辻褄を合わせない。"
            % (along, list(nk)))
    EX0 = ir[0] * KEN + (noki_de if nks[0] else 0.0)   # 内部 x=0 の側の出(下屋 + 軒の出)
    EX1 = ir[1] * KEN + (noki_de if nks[1] else 0.0)   # 内部 x=W の側
    EY0 = ir[2] * KEN + (noki_de if nks[2] else 0.0)   # 内部 y=0(帯0)の側
    EY1 = ir[3] * KEN + (noki_de if nks[3] else 0.0)   # 内部 y=D(最終帯)の側
    x0, x1 = -EX0, W + EX1
    N = len(bands)
    # ⭐ **軒を落とした平の辺は、隣の棟と一本の谷を作る。**⇒ 帯どうしの谷と同じ作りにする:
    #   瓦場を `VALLEY_GAP` 引いて、**半分の谷樋**を線の上に出す(両隣が半分ずつ)。
    #   ⚠ 成立するのは **その辺の入側が 0**(=身舎の縁が外形の縁)のときだけ。
    #     入側がある辺で軒を落とすと屋根の縁は下屋の途中になり、谷樋の座が定まらない
    #     ⇒ 樋は出さずに突き付けるだけにして、⚠ を刷って呼び出し元へ返す。
    drop_y0 = (not nks[2]) and ir[2] == 0
    drop_y1 = (not nks[3]) and ir[3] == 0
    for _s, _nk, _ir in (("v0/u0 側", nks[2], ir[2]), ("v1/u1 側", nks[3], ir[3])):
        if (not _nk) and _ir:
            print("[banded] ⚠ 軒を落とした %s は入側 %d間 を持つので **谷樋を出さない**"
                  "(屋根の縁が下屋の途中で、樋の座が定まらない)。突き付けのみ。" % (_s, _ir))

    pieces = []
    info = []
    for i, b in enumerate(bands):
        ya, yb = ys[i], ys[i + 1]
        bw = yb - ya
        ym = (ya + yb) / 2.0
        zr = eave + (bw / 2.0) * kobai            # 大棟の天端(座を除く)
        a = gable_frac * (bw / 2.0)               # 妻の平面上の入り込み
        zg = eave + a * kobai                     # 妻の足元
        if W - 2 * a < 0.35:
            raise SystemExit("[banded] 帯%d: 大棟が残らない(桁行 %.2fm・妻の入り %.2fm)。"
                             "span を増やすこと" % (i, W, a))
        ey0 = EY0 if i == 0 else 0.0
        ey1 = EY1 if i == N - 1 else 0.0
        # 谷側は瓦場を VALLEY_GAP だけ引いて、谷樋の縁を瓦の下へ潜らせる。
        # ⭐⭐ **引くのは「帯どうしの境(内側の谷)」だけ。**外周の辺は、軒を落として
        #   ey が 0 になっても **引かない**(2026-09-10)。引くと隣の棟との境で
        #   左右 0.10 ずつ = **0.20m の空が抜ける** — 直そうとした不良そのものに戻る。
        #   ⚠ 内側の谷には `_valley_gutter` が実体で入るが、外周の辺には入らない
        #     (両隣の棟が同じ線でそれぞれ樋を出すと重なって z ファイティングになる)。
        inner0, inner1 = (i > 0), (i < N - 1)
        gy0 = VALLEY_GAP if ((inner0 and ey0 <= 0) or (i == 0 and drop_y0)) else 0.0
        gy1 = VALLEY_GAP if ((inner1 and ey1 <= 0) or (i == N - 1 and drop_y1)) else 0.0
        ylo, yhi = ya - ey0 + gy0, yb + ey1 - gy1
        tag = "%s_b%d" % (name, i)

        # --- 平の二面(±Y)。軒先の台形 + 妻から上の矩形 -------------------
        # 軒先線 y=ylo における隅棟の足元は、外周側なら x0/x1(軒の出の隅)、
        # 谷側なら x = ±VALLEY_GAP(隅棟は谷の端から立ち上がる)
        # ⭐ **隅棟は身舎の隅から 45°** なので、辺ごとに出が違うと隅棟は
        #   **短い方の軒先線で尽きる**。長い方の面はその先へ張り出す(＝隅で軒先線が折れる)。
        #   ⛔ 隅を (x0, ya−E) の1点で済ませない — 斜辺が 45° を外れ、
        #     二つの流れ面が食い違って隅に隙が開く(二平面の交線は必ず 45°)。
        #   ⭕ 出が四周同じなら下の式は元の1点に潰れる(既存の屋根は1頂点も動かない)。
        if ey0:
            t0, t1 = min(EX0, EY0), min(EX1, EY0)
            sl = [(-t0, ya - t0)] + ([(x0, ylo)] if EX0 < EY0 - 1e-9 else [])
            sr = ([(x1, ylo)] if EX1 < EY0 - 1e-9 else []) + [(W + t1, ya - t1)]
        else:
            sl, sr = [(gy0, ylo)], [(W - gy0, ylo)]
        south = [sl + sr + [(W - a, ya + a), (a, ya + a)],
                 [(a, ya + a), (W - a, ya + a), (W - a, ym), (a, ym)]]
        pieces.append(_tile_field_fast(south, (x0, ya), 90, eave, tag + "_S"))

        if ey1:
            t2, t3 = min(EX0, EY1), min(EX1, EY1)
            nr = [(W + t3, yb + t3)] + ([(x1, yhi)] if EX1 < EY1 - 1e-9 else [])
            nl = ([(x0, yhi)] if EX0 < EY1 - 1e-9 else []) + [(-t2, yb + t2)]
        else:
            nr, nl = [(W - gy1, yhi)], [(gy1, yhi)]
        north = [nr + nl + [(a, yb - a), (W - a, yb - a)],
                 [(W - a, yb - a), (a, yb - a), (a, ym), (W - a, ym)]]
        pieces.append(_tile_field_fast(north, (x0, yb), 270, eave, tag + "_N"))

        # --- 妻の二面(±X)= 隅(寄棟面)+ そのまま妻側の下屋 ---------------
        # ⚠ 瓦の格子の原点は **全帯で共通の (x0, 0)**。帯ごとに取ると桁行方向にズレる
        if ey0:
            wa = ([(x0, ylo), (-min(EX0, EY0), ya - min(EX0, EY0))]
                  if EY0 < EX0 - 1e-9 else [(x0, ya - EX0)])
        else:
            wa = [(x0, ya), (0.0, ya)]
        if ey1:
            wb = ([(-min(EX0, EY1), yb + min(EX0, EY1)), (x0, yhi)]
                  if EY1 < EX0 - 1e-9 else [(x0, yb + EX0)])
        else:
            wb = [(0.0, yb), (x0, yb)]
        wp = wa + [(a, ya + a), (a, yb - a)] + wb
        pieces.append(_tile_field_fast([wp], (x0, 0.0), 0, eave + kobai * x0, tag + "_W"))

        if ey0:
            ea = ([(x1, ylo), (W + min(EX1, EY0), ya - min(EX1, EY0))]
                  if EY0 < EX1 - 1e-9 else [(x1, ya - EX1)])
        else:
            ea = [(x1, ya), (W, ya)]
        if ey1:
            eb = ([(W + min(EX1, EY1), yb + min(EX1, EY1)), (x1, yhi)]
                  if EY1 < EX1 - 1e-9 else [(x1, yb + EX1)])
        else:
            eb = [(W, yb), (x1, yb)]
        ep = ea + [(W - a, ya + a), (W - a, yb - a)] + eb
        # ⚠ 東面の軒先の高さは **EX1** で決まる(⛔ `eave + kobai*x0` は西面の値)
        pieces.append(_tile_field_fast([ep], (x1, 0.0), 180, eave - kobai * EX1, tag + "_E"))

        info.append(dict(i=i, ken=b, ya=ya, yb=yb, ym=ym, zr=zr, a=a, zg=zg,
                         ridge_len=W - 2 * a))

    p = palette()

    for d in info:
        ya, yb, ym, zr, a, zg = d['ya'], d['yb'], d['ym'], d['zr'], d['a'], d['zg']
        i = d['i']
        ey0 = EY0 if i == 0 else 0.0
        ey1 = EY1 if i == N - 1 else 0.0
        tag = "%s_b%d" % (name, i)
        # 大棟 + 鬼
        pieces += ridge((a, ym, zr), (W - a, ym, zr), tag + "_omune", w=0.50, h=0.42)
        pieces += oni((a, ym, zr), (-1, 0), tag + "_oni0", scale=1.15)
        pieces += oni((W - a, ym, zr), (1, 0), tag + "_oni1", scale=1.15)
        # 隅棟4本。外周側は軒先の隅(z = 軒先高)から、
        # 谷側は **谷の端**(x=0 / x=W・z=eave)から立ち上がる
        # ⚠ 隅棟の足元は **短い方の出**で尽きる(z も min の出で決まる)
        ta, tb = min(EX0, EY0), min(EX1, EY0)
        tc, td = min(EX0, EY1), min(EX1, EY1)
        for s_pt, t_pt in [
                (((-ta, ya - ta), eave - kobai * ta) if ey0 else ((0.0, ya), eave), (a, ya + a)),
                (((W + tb, ya - tb), eave - kobai * tb) if ey0 else ((W, ya), eave), (W - a, ya + a)),
                (((-tc, yb + tc), eave - kobai * tc) if ey1 else ((0.0, yb), eave), (a, yb - a)),
                (((W + td, yb + td), eave - kobai * td) if ey1 else ((W, yb), eave), (W - a, yb - a))]:
            (sx, sy), zs = s_pt
            pieces += ridge((sx, sy, zs + 0.02), (t_pt[0], t_pt[1], zg),
                            tag + "_sumi", w=0.40, h=0.33)

        # 妻(妻壁+木連格子+破風+懸魚)。破風の見付の出 = tsuma_end
        bt = tsuma_end / 1.15
        new_geo = gable(a, +1, ya + a, yb - a, zg, ym, zr, tag + "_gW", p,
                        bw=0.62, bt=bt, drop=0.55)
        new_geo += gable(W - a, -1, ya + a, yb - a, zg, ym, zr, tag + "_gE", p,
                         bw=0.62, bt=bt, drop=0.55)
        # 袖瓦(破風の天端に被る瓦)。瓦の実体は名目平面より上にあるので 0.22 持ち上げる
        for gx, inward in ((a, +1), (W - a, -1)):
            sx2 = gx - inward * 0.06
            for uy in (ya + a, yb - a):
                pieces += ridge((sx2, uy, zg + 0.22), (sx2, ym, zr + 0.22),
                                tag + "_sode", w=0.36, h=0.28)
        for o, uv in new_geo:
            if o:
                if uv:
                    V.set_uv(o, uv)
                pieces.append(o)

    # --- 谷樋。帯の境 = 柱通りに乗る -----------------------------------------
    valleys = []
    for i in range(1, N):
        yv = ys[i]
        pieces.append(_valley_gutter(yv, -0.05, W + 0.05, eave, kobai, p,
                                     "%s_tani%d" % (name, i)))
        valleys.append(yv)
    # ⭐ 外形の線で隣と接する辺の **半分の谷樋**(隣が残りの半分を出す)
    if drop_y0:
        pieces.append(_valley_gutter(0.0, -0.05, W + 0.05, eave, kobai, p,
                                     "%s_tani_soto0" % name, half=+1))
    if drop_y1:
        pieces.append(_valley_gutter(D, -0.05, W + 0.05, eave, kobai, p,
                                     "%s_tani_soto1" % name, half=-1))

    pieces = [q for q in pieces if q]
    V.dedup_materials()
    o = V.join(pieces, name)
    # ⭐⭐ **ピボット = 「身舎 + 入側」= 棟の外形の中心・床レベル。**
    #   ⛔ 身舎の中心ではない。入側が辺ごとに違うと両者はズレる(長局南 v[1,0] で 0.909m)。
    #   ⭕ こう採ると屋根の外形は**常にピボットについて対称**(棟の外形の各辺に軒の出
    #     `noki_de` が一様に付くだけ)なので、据える側は棟の外形の中心へ置けばよい。
    #   ⚠ 入側が四周同じなら身舎の中心と一致する ⇒ **既存の屋根のピボットは動かない**。
    xmid = (W + (ir[1] - ir[0]) * KEN) / 2.0
    ymid = (D + (ir[3] - ir[2]) * KEN) / 2.0
    if along == "v":
        V.rotate_z([o], 90)                 # 大棟を Blender +Y(= Unity −Z)へ
        V.set_origin(o, (-ymid, xmid, 0.0))
    else:
        V.set_origin(o, (xmid, ymid, 0.0))

    q = _norm_irikawa(irikawa)
    print("[banded] %s 帯=%s 桁行=%d間(%.3f) 入側 u=[%d,%d] v=[%d,%d] 軒の出=%.2f 葺材=%s along=%s"
          % (name, bands, span, W, q[0], q[1], q[2], q[3], noki_de, fukizai, along))
    print("[banded]   軒 u0=%s u1=%s v0=%s v1=%s(0=落とす ⇒ 棟の外形の線で屋根が終わる)"
          % tuple("出す" if t else "**落とす**" for t in nk))
    print("[banded]   足形(身舎+入側+軒の出) %.3f × %.3f m / 身舎 %.3f × %.3f m"
          % (W + EX0 + EX1, D + EY0 + EY1, W, D))
    print("[banded]   棟の外形(身舎+入側) %.3f × %.3f m ⇒ 屋根はその四周に軒の出 %.2f"
          % (W + (ir[0] + ir[1]) * KEN, D + (ir[2] + ir[3]) * KEN, noki_de))
    print("[banded]   軒高 %.3f / 軒先の先端 x0 %.3f x1 %.3f y0 %.3f y1 %.3f"
          % (eave, eave - EX0 * kobai, eave - EX1 * kobai,
             eave - EY0 * kobai, eave - EY1 * kobai))
    for d in info:
        print("[banded]   帯%d %d間: 棟高 %.3f(座を除く) 大棟長 %.3f 妻の入り %.3f 妻の足元 %.3f"
              % (d['i'], d['ken'], d['zr'], d['ridge_len'], d['a'], d['zg']))
    print("[banded]   谷 %d本: y = %s(身舎の南端から・柱通りに乗る)"
          % (len(valleys), ", ".join("%.3f(%g間)" % (v, v / KEN) for v in valleys)))
    _verify_band_order(o, bands_in, ymid, along, name)
    _verify_eaves(o, bands_in, span, along, _norm_irikawa(irikawa), nk, noki_de, name)
    return o


# 隅棟(`ridge` の断面 w=0.40)は軒先の隅から 45° で立ち上がるので、**その断面の半幅**が
# 軒先線の外へ出る。実測 0.171m(2026-09-10・松江松平の 6 本すべてで同じ値)。
# ⭐ これは不良ではなく隅棟の冠瓦の見付そのもの。⛔ ただし **呼び寸法と混ぜない** —
#   「四辺とも 1.071 出ている」は「入側が効いていない」ではなく「0.900 + 隅棟の 0.171」。
SUMI_CAP = 0.18


def _verify_eaves(o, bands_in, span, along, ir_grid, nk, noki_de, name):
    """⭐⭐ **焼いた直後に「辺ごとの軒の出」を実測する**(2026-09-10)。

    ⛔⛔ **これが無かったので、普請検査が「長局南だけ入側が効いていない」と読み違えた。**
      実測は四辺とも 1.071 で、内訳は **軒 0.900 + 隅棟の冠瓦の見付 0.171**(`SUMI_CAP`)。
      隅棟は軒先の隅から 45° で立つので、**隣り合う二辺の出が等しい隅**では
      その断面の半幅が**両方の辺**の外へ出る(出が違う隅では短い方の辺にしか出ない)。
      ⇒ 「長局南 `_i1110` だけ四辺とも 1.071」は **EX と EY がたまたま等しい**ことの帰結で、
        入側は正しく効いていた。**測る集合を先に確かめる**(CLAUDE.md 規則19)。

    測り方: 焼いた**ローカル座標**で見る。⛔ `matrix_world` を見ない(`set_origin` を
      通した部材はノードに location が残る。README「その3」)。
      写像は `along` によらず **grid u = −(局所 X) / grid v = +(局所 Y)**。
    """
    across = sum(bands_in)
    if along == "v":                      # 大棟が v ⇒ 帯は u へ並ぶ
        out_u, out_v = across, int(span)
    else:
        out_u, out_v = int(span), across
    out_u += ir_grid[0] + ir_grid[1]      # 棟の外形(身舎 + 入側)
    out_v += ir_grid[2] + ir_grid[3]
    hu, hv = out_u * KEN / 2.0, out_v * KEN / 2.0

    us = [-v.co.x for v in o.data.vertices]
    vs = [v.co.y for v in o.data.vertices]
    got = (-min(us) - hu, max(us) - hu, -min(vs) - hv, max(vs) - hv)
    want = tuple(noki_de if t else 0.0 for t in nk)
    ok = True
    print("[banded]   棟の外形 u=%d間(%.3f) v=%d間(%.3f)。**辺ごとの軒の出**(ピボット=外形の中心):"
          % (out_u, out_u * KEN, out_v, out_v * KEN))
    for k, lbl in enumerate(("u0", "u1", "v0", "v1")):
        d = got[k] - want[k]
        bad = not (-0.01 <= d <= SUMI_CAP + 0.01)
        ok = ok and not bad
        print("[banded]     %s %s 呼び %.3f / 実測 %.3f(差 %+.3f = 隅棟の冠瓦 ≤ %.3f)%s"
              % ("⛔" if bad else "⭕", lbl, want[k], got[k], d, SUMI_CAP,
                 "  ← **軒を落とした辺**" if not nk[k] else ""))
    if not ok:
        raise SystemExit(
            "[banded] ⛔ 辺ごとの軒の出が呼び寸法と合わない(%s)。\n"
            "  ⇒ `irikawa` / `noki` の軸の写像(`_map_sides`)を疑うこと。\n"
            "  ⛔ 据え付け側で寄せて辻褄を合わせない — 部材の不良は部材で直す。" % name)


def banded_name(bands, span, along="u", fukizai="sangawara", irikawa=1.0, noki=1):
    """規約名: Goten_Roof_Banded_<帯>x<桁行>ken[_v][_i<u0><u1><v0><v1>][_n<u0><u1><v0><v1>][_hon]
    例: [4,5] span12 → `Goten_Roof_Banded_4-5x12ken`

    ⭐ **入側が四周1間でないときだけ `_i` の綴りが付く**(2026-09-09)。
      ⛔ 入側を名前に入れずに焼くと、**同じ名前で幾何の違う屋根**ができて静かに上書きし合う
        (松江松平の表向は入側 u=[0,0]、土井は四周1間で、どちらも `4-4-4x10ken_v` になる)。
      ⚠ 綴りは **郭グリッドの順 u0,u1,v0,v1**(指図 `roof.irikawa` の並びそのまま)。
        ⛔ 生成器の内部軸(x0,x1,y0,y1)の順で綴らない — along で入れ替わる。"""
    s = "Goten_Roof_Banded_%sx%dken" % ("-".join(str(int(b)) for b in bands), int(span))
    if along == "v":
        s += "_v"
    q = _norm_irikawa(irikawa)
    if q != (1, 1, 1, 1):
        s += "_i%d%d%d%d" % q
    # ⭐ **軒を落とした辺があるときだけ `_n<u0><u1><v0><v1>`(1=出す / 0=落とす)。**
    #   ⛔ 入れずに焼くと、`_i` と同じ事故が起きる — 松江松平の黒書院(両隣が接する)と
    #     玄関(片側だけ接する)はどちらも `4-4-4x10ken_v_i0011` になり、静かに上書きし合う。
    k = _norm_noki(noki)
    if k != (1, 1, 1, 1):
        s += "_n%d%d%d%d" % k
    if fukizai == "hongawara":
        s += "_hon"
    return s


def render_banded(o, path_dir, tag, eave=3.4):
    """帯割りの屋根の検証レンダ。⭕ **見るのは4点** —
    谷が通っているか / 下屋が身舎に噛んでいるか / 軒先が水平か / 妻が破綻していないか。
    ⚠ `export_fbx` を通すと bbox が 0 に潰れるので、**書き出しの前に**呼ぶこと。"""
    V.hook_textures()
    mn, mx = V.bbox([o])
    cx, cy = (mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0
    W, D, H = mx.x - mn.x, mx.y - mn.y, mx.z
    r = max(W, D)
    os.makedirs(path_dir, exist_ok=True)
    out = []

    def shot(sub, cam, look, ortho=None, res=(1600, 1000)):
        for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
            bpy.data.objects.remove(c, do_unlink=True)
        for pl in [c for c in bpy.data.objects if c.name.startswith("Plane")]:
            bpy.data.objects.remove(pl, do_unlink=True)
        bpy.ops.mesh.primitive_plane_add(size=r * 6, location=(cx, cy, 0.0))
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(path_dir, "%s_%s.png" % (tag, sub))
        V.render(f)
        out.append(f)

    # 1) 俯瞰 — 谷と帯の並びを見る
    shot("01_fukan", (cx - r * 0.75, cy - r * 1.0, mx.z + r * 0.95), (cx, cy, eave * 0.6))
    # 2) 妻側の立面(正射影)— 妻・下屋・軒先の水平を見る
    shot("02_tsuma", (cx - r * 3.0, cy, eave * 0.75), (cx, cy, eave * 0.75),
         ortho=max(D, mx.z) * 1.25)
    # 3) 平側の立面(正射影)— 軒先が一直線か・下屋の取り付きを見る
    shot("03_hira", (cx, cy - r * 3.0, eave * 0.75), (cx, cy, eave * 0.75),
         ortho=max(W, mx.z) * 1.15)
    # 4) 谷の寄り(俯瞰)— 谷樋が通っているか、瓦の小口が透けないか
    shot("04_tani", (cx - W * 0.30, cy - D * 0.10, mx.z + 3.2), (cx + W * 0.10, cy, eave))
    # 5) 真上(正射影)— ⭐ **帯の並びと大棟の向きはここでしか読めない。**
    #    立面(02/03)も俯瞰(01)も左右対称に見えるので、非対称の帯の並び違いが素通りする
    #    (2026-09-07 の `4-5x10ken_v` の鏡像はこれが無かったのが一因)。
    shot("05_shinjo", (cx, cy, mx.z + r * 1.2), (cx, cy, 0.0),
         ortho=max(W, D) * 1.06, res=(1400, 1400))
    return out


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


# ---------------------------------------------------------------------------
# 平入り + 庇(make_hirairi)と 渡廊下の差し掛けの下屋(make_rokageya)
# ---------------------------------------------------------------------------
# 【なぜ要るか】松江松平邸の**奥向の棟4棟と厩**(御湯殿・長局北・奥台所・長局南・厩)は
#   梁間の外形が帯割り(4/5 の和)で作れないので `make_banded` が使えず、入母屋の定尺を
#   当てると屋根の型そのものが指図と違う物になる(2026-09-18 ユーザー裁定A ／
#   2026-09-19 裁定2=A・3=A ⇒ `const.nagayaGataRoof`)。
#   ⇒ **身舎(梁間 `moyaKen`)に平入りの切妻を架け、その外を一間の庇が回る**型を起こす。
#   渡廊下はユーザー裁定A(2026-09-17)で**独立の大棟を持たない差し掛けの下屋(両流れ)**に
#   改まったので、`make_kirizuma`(独立の切妻・勾配 5.5寸・軒 0.60)では当たらない。
#
# 【勾配】この二つの型は **瓦モジュールの素の勾配 RATIO(5.5寸)を使わない** —
#   本屋根 6寸 / 庇 4寸5分 / 下屋 4寸(指図の `const`)。⇒ `_tile_field_k` が
#   **瓦の形を変えずに面ごと傾ける**(⛔ z を縮めて勾配を作らない。README の注も参照)。
#
# 【軸の鎖 — ここを取り違えると三方庇が鏡像で焼ける】
#   書き出し: **Unity X = −(Blender X) / Unity Y = Blender Z / Unity Z = −(Blender Y)**
#   据え付け(`EdoMatsudairaDewaBuilder.YawAlongU`): **Unity 局所 +X = 格子 +u /
#   局所 +Z = 格子 −v**。
#   ⇒ **格子 +u = Blender −X / 格子 +v = Blender +Y**。
#   ⇒ 辺の対応は  u0 = Blender **+X 端** / u1 = **−X 端** / v0 = **−Y 端** / v1 = **+Y 端**。
#   ⛔ 左右対称な棟では絶対に気づけないので、非対称(`hisashiOmit` のある棟)を焼いたら
#     `_verify_hirairi` が**辺ごとの軒先の高さ**で検算する(bbox では見抜けない —
#     庇を断った辺は本屋根の軒が 0.9 出るので**外形は対称のまま**)。

HIRA_OVER = 0.35        # 庇の瓦場を身舎の屋根の下へ差し込む量[m](光の筋を消す重ね代)
HIRA_MIZU = 0.18        # 雨押え(水切り)板の見付[m]
HIRA_SODE = 0.20        # 袖瓦の持ち上げ[m](瓦の実体は名目平面より上にある)
NOTCH_T = 0.08          # 切り欠きの奥・脇の塞ぎ板の厚[m]
NOTCH_BASE_T = 0.00909  # 切り欠きの**受け板**の厚[m] = 3分(化粧の面戸板)
#   ⛔⛔ **ここを厚くしない。** 受け面(軒桁の天端)に廊下の桁が掛かるが、当たりの測り方は
#     「切り欠きの中を鉛直に貫いた**最も低い交点**」なので、拾われるのは**板の下端**。
#     ⇒ 板厚がそのまま頭上の余裕を食う(2026-09-20: 厚 0.08 で `roka.zujoMin` を 65mm 割り、
#     『切り欠きが効いていない』と読まれた)。柱筋の頭上 = 1.7423 − 厚 ⇒ **厚 ≤ 0.0153**。
#   ⛔ 0 厚(板なし)にもしない — 受け面と瓦場の間に隙が開く。
NOTCH_H = 0.20          # 切り欠きの奥の塞ぎの立ち上がり[m](瓦の小口を隠す)
NOTCH_KEN = 1.0         # 切り欠きの幅[間](= 渡廊下の幅)


def KenTag(n):
    """間数の綴り。整数は `3`、端数は `1.5`(C# の `EdoAssets.Goten.KenTag` と同じ)"""
    return ("%g" % n) if abs(n - int(n)) > 1e-6 else "%d" % int(n)


def hirairi_name(wk, dk, eave, omit=(), notches=()):
    """平入り+庇の部材名。⚠ **mm は `round`**(`floor` は浮動小数で 1mm 落ちる)。
    `_o<辺>` は庇を断った辺(格子の綴り・並びは u0,u1,v0,v1)、`_e<mm>` は**床上の**身舎の軒桁。
    `_k<辺>-<間>` は**渡廊下の取り付きで庇の軒先を切り欠いた**位置(中心の間数・棟の格子基準)。"""
    s = "Goten_Roof_Hirairi_%sx%sken" % (KenTag(wk), KenTag(dk))
    q = [k for k in ("u0", "u1", "v0", "v1") if k in set(omit or ())]
    if q:
        s += "_o" + "".join(q)
    for side, c in sorted(notches or [], key=lambda z: (("u0", "u1", "v0", "v1").index(z[0]), z[1])):
        s += "_k%s-%s" % (side, KenTag(c))
    return s + "_e%d" % int(round(eave * 1000.0))


def _tile_field_k(convex_polys, eave_origin, yaw_deg, z_eave, name, kobai):
    """`_tile_field_fast` の **勾配可変**版。⭕ **瓦の形は一切変えず、葺く面ごと傾ける。**

    ⛔ **z を縮めて勾配を作らない** — 4寸勾配なら桟瓦の起伏が 27% 潰れて、
      実ジオメトリの瓦を使う意味が無くなる(「自作の瓦はダサい」で却下された道へ戻る)。
    ⭕ 瓦モジュール `roof 2x2` は**それ自体が 5.5寸勾配の一枚の面**なので、
      軒先の線(ローカル Y 軸)まわりに Δθ = atan(kobai) − atan(RATIO) だけ回し、
      葺きの進み `(STEP_RUN, 0, STEP_RISE)` も同じだけ回して送れば、
      **瓦の形も重なりも保ったまま**別勾配の面になる(実物で瓦を寝かせるのと同じ)。
    ⚠ 送りは**面に沿った長さが不変**なので、平面上の進みは `step.x = 送り×cosθ` に縮む。
      格子の枚数はそちらで数えること(`STEP_RUN` で数えると足りない)。
    ⚠ ⭕ 位置は **`+=`** で置く(⛔ `=` で上書きしない)— 格子の原点は (i0, j0) の駒に
      あるので、代入すると格子が i0·送り だけずれて**ポリゴンを覆い損ねる**ことがある。"""
    if abs(kobai - RATIO) < 1e-9:
        return _tile_field_fast(convex_polys, eave_origin, yaw_deg, z_eave, name)
    dth = math.atan(kobai) - math.atan(RATIO)
    R = mathutils.Matrix.Rotation(-dth, 4, 'Y')          # +X が上る向きへ回す
    step = R @ Vector((STEP_RUN, 0.0, STEP_RISE))
    pr = step.x                                          # 1段送りの**平面上の**進み
    c, s = math.cos(math.radians(-yaw_deg)), math.sin(math.radians(-yaw_deg))
    us, vs = [], []
    for poly in convex_polys:
        for q in poly:
            dx, dy = q[0] - eave_origin[0], q[1] - eave_origin[1]
            us.append(dx * c - dy * s)
            vs.append(dx * s + dy * c)
    i0 = int(math.floor(min(us) / pr)) - 1
    i1 = int(math.ceil(max(us) / pr)) + 1
    j0 = int(math.floor(min(vs) / MOD_LEN)) - 1
    j1 = int(math.ceil(max(vs) / MOD_LEN)) + 1

    unit = V.join(V.place(MOD, 0, 0, 0, scale=1.0), name + "_unit")
    base = unit.matrix_world.copy()
    base.translation = Vector((0.0, 0.0, 0.0))
    objs = []
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            o = unit.copy()                    # メッシュデータは共有(join で実体化される)
            bpy.context.scene.collection.objects.link(o)
            t = step * float(i) + Vector((0.0, j * MOD_LEN, 0.0))
            o.matrix_world = mathutils.Matrix.Translation(t) @ R @ base
            objs.append(o)
    bpy.data.objects.remove(unit, do_unlink=True)
    field = V.join(objs, name + "_field")
    V.rotate_z([field], yaw_deg)
    field.location = field.location + Vector((eave_origin[0], eave_origin[1], z_eave))
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


def _rake_boards(x, inward, y_end, z_end, apex_y, apex_z, name, p, bw=0.34, bt=0.10):
    """妻の**片側だけ**の破風板(化粧板 + 眉)。返り値 = [(obj, uv)]。

    ⭐ `gable()` は y0/y1 の**両側**に板を出すが、庇を断った辺では
      その側だけ軒が 0.9 出て**鼻先が下がる**ので左右で長さも下端も違う。
      ⇒ 反対側を y_end の鏡像に置いて呼び、**手前の一組だけ残して捨てる**。
      ⛔ 片側だけ短い板で済ませない(瓦場の小口が 0.9m 剥き出しになる)。"""
    g = gable(x, inward, y_end, 2.0 * apex_y - y_end, z_end, apex_y, apex_z,
              name, p, thick=0.12, bw=bw, bt=bt, drop=0.55, lattice=False, gegyo=False)
    keep = g[1:3]                              # [妻壁, 破風a, 眉a, 破風b, 眉b]
    for o, _ in [g[0]] + list(g[3:]):
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    return keep


def _prism_uz(P, t_a, t_b, pts_uz, mat, name):
    """`(u, z)` の閉多角形を **t 方向 t_a..t_b へ押し出した板**。`P` は (t,u)→(x,y) の写像。
    ⭐ 切り欠きの脇板のように**屋根の流れに沿って下る板**に使う
      (⛔ `V.box` で作ると矩形なので軒下へ 0.4m 垂れ、庇の下から見上げると鰭になる)。"""
    v = []
    for tt in (t_a, t_b):
        for (u, z) in pts_uz:
            x, y = P(tt, u)
            v.append((x, y, z))
    n = len(pts_uz)
    f = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    f += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    o = _mesh_from_poly(name, v, f, recalc=True)
    if mat:
        o.data.materials.append(mat)
    return o


def _hirairi_sides(W, D, omit, hken, ken=KEN):
    """庇の張り出し[m]を **Blender の四辺** (minx, maxx, miny, maxy) で返す。
    ⭐ 対応は  minx = 格子 u1 / maxx = u0 / miny = v0 / maxy = v1(軸の鎖は章頭の註)。"""
    o = set(omit or ())
    h = hken * ken
    return (0.0 if "u1" in o else h, 0.0 if "u0" in o else h,
            0.0 if "v0" in o else h, 0.0 if "v1" in o else h)


def make_hirairi(W, D, eave, omit=(), name="Goten_Roof_Hirairi",
                 hon=0.60, his=0.45, noki=0.90, hken=1, ken=KEN, oni_on=True,
                 notches=(), notch_w=None):
    """**平入り + 庇**(`const.nagayaGataRoof`)。返り値 = 1メッシュ。

    W = 桁行の外形[m](大棟が走る側)/ D = 梁間の外形[m] / eave = **身舎の軒桁**の高さ
    (ピボットの面=床から)/ omit = 庇を回さない辺の集合(格子の綴り "u0","u1","v0","v1")。

    ⭐⭐ **ピボットの z=0 は「床」**(`make_banded` と同じ・⛔ `make_irimoya` の軒先ではない)。
      平面のピボットは**足形(庇を含む外形)の中心**。⇒ 棟梁は `new Vector3(cx, floor, cz)`。
    ⭐ 高さはすべてこの z=0 から:  身舎の軒桁 = eave /
      大棟(瓦の頂)= eave + 身舎の梁間/2 × hon / 庇の軒桁 = eave − hken×ken×his /
      庇の軒先の下端 = eave − (hken×ken + noki)×his /
      庇を断った辺の軒先の下端 = eave − noki×hon。
    ⛔ **bbox の丈をピボットからの高さとして使わない**(大棟の座と瓦の起伏が上へ出る)。

    ⭐⭐ **`notches` = 渡廊下が取り付く辺の切り欠き** `[(辺, 中心の間数), ...]`。
      指図の取り合い(`_roka` ④「廊下の**桁の下端** ↔ **庇の軒桁の天端**」)を成り立たせるため、
      **その幅だけ庇の軒先を切り詰め**、底に**軒桁の天端の水平面**を出す。
      ⛔ 軒先の下へ潜らせる納めは指図が採らない(`_roka` ③)。
      中心の数え方は**棟の格子基準** — u の辺は `munes[].v0` から、v の辺は `munes[].u0` からの間数。
      ⇒ 棟梁は `links[]` の矩形の中心 − 棟の u0/v0 をそのまま渡せる。"""
    if notch_w is None:
        notch_w = NOTCH_KEN * ken
    hxm, hxp, hym, hyp = _hirairi_sides(W, D, omit, hken, ken)
    mx0, mx1 = hxm, W - hxp                     # 身舎の壁の通り
    my0, my1 = hym, D - hyp
    if mx1 - mx0 < ken or my1 - my0 < ken:
        raise SystemExit("⛔ 身舎が残らない: %gx%g ken の外形に庇 %g" % (W / ken, D / ken, hken))
    ridge_y = (my0 + my1) / 2.0
    z_ridge = eave + (my1 - my0) / 2.0 * hon
    # 庇の無い辺だけ本屋根が軒を出す(ある辺は庇が覆うので身舎の壁で終わる)
    exm = noki if hxm == 0 else 0.0
    exp = noki if hxp == 0 else 0.0
    eym = noki if hym == 0 else 0.0
    eyp = noki if hyp == 0 else 0.0
    rx0, rx1 = mx0 - exm, mx1 + exp
    ry0, ry1 = my0 - eym, my1 + eyp
    z_ry0, z_ry1 = eave - eym * hon, eave - eyp * hon

    p = palette()
    pieces = []
    notch_world = []                            # 切り欠きの芯(検証レンダの狙い所)

    # --- 身舎の本屋根(平入りの切妻。両流れ)--------------------------------
    pieces.append(_tile_field_k([[(rx0, ry0), (rx1, ry0), (rx1, ridge_y), (rx0, ridge_y)]],
                                (rx0, ry0), 90, z_ry0, name + "_S", hon))
    pieces.append(_tile_field_k([[(rx1, ry1), (rx0, ry1), (rx0, ridge_y), (rx1, ridge_y)]],
                                (rx0, ry1), 270, z_ry1, name + "_N", hon))
    # 大棟 — 庇のある辺は妻壁の面まで、庇を断った辺(ケラバ)は軒先まで通す
    gx0 = mx0 - 0.02 if hxm > 0 else rx0
    gx1 = mx1 + 0.02 if hxp > 0 else rx1
    pieces += ridge((gx0, ridge_y, z_ridge - 0.13), (gx1, ridge_y, z_ridge - 0.13),
                    name + "_omune", w=0.44, h=0.36)
    if oni_on:
        pieces += oni((gx0, ridge_y, z_ridge), (-1, 0), name + "_oni0", scale=1.0)
        pieces += oni((gx1, ridge_y, z_ridge), (1, 0), name + "_oni1", scale=1.0)

    new_geo = []
    # --- 妻(身舎の両端)— 妻壁は身舎の柱通りの間だけ・破風は軒先まで -------
    for gx, inward in ((mx0, +1), (mx1, -1)):
        g = gable(gx, inward, my0, my1, eave, ridge_y, z_ridge, name + "_g%d" % (gx > mx0),
                  p, thick=0.14, bw=0.34, bt=0.10, drop=0.55, lattice=False, gegyo=False)
        new_geo.append(g[0])                       # 妻壁(漆喰)だけ残す
        for o, _ in g[1:]:
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
        new_geo += _rake_boards(gx, inward, ry0, z_ry0, ridge_y, z_ridge,
                                name + "_bS%d" % (gx > mx0), p)
        new_geo += _rake_boards(gx, inward, ry1, z_ry1, ridge_y, z_ridge,
                                name + "_bN%d" % (gx > mx0), p)
        # 袖瓦 — 破風の天端に被せる。入れないと瓦場の切り口と板の天端が白い筋になる
        sx = gx - inward * 0.06
        for (ye, ze) in ((ry0, z_ry0), (ry1, z_ry1)):
            pieces += ridge((sx, ye, ze + HIRA_SODE), (sx, ridge_y, z_ridge + HIRA_SODE),
                            name + "_sode", w=0.34, h=0.26)

    # --- 庇(四辺 − 断った辺)。隅は 45°の隅棟でつなぐ -----------------------
    # ⭐ 辺ごとに **(t, u) の局所座標**で組む: t = 辺に沿う / u = 身舎の壁からの深さ(外向き)。
    #   u = 0 身舎の壁 / u = hken×ken **庇の軒桁の線(足形の縁)** / u = run 庇の軒先。
    #   隅の留めは「深さ u だけ t を伸ばす」45°の線なので、どの辺も同じ式で書ける。
    run = hken * ken + noki                     # 身舎の壁 → 庇の軒先(平面上)
    keta_u = hken * ken                         # 軒桁の線の深さ = 足形の縁
    z_keta = eave - keta_u * his                # **庇の軒桁の天端**(= 渡廊下の桁が掛かる面)
    z_tip = eave - run * his
    SIDES = {                                   # 辺 → (写像, t の両端, 隣の辺の庇, yaw)
        "v0": (lambda t, u: (t, my0 - u), (mx0, mx1), (hxm, hxp), 90),
        "v1": (lambda t, u: (t, my1 + u), (mx0, mx1), (hxm, hxp), 270),
        "u1": (lambda t, u: (mx0 - u, t), (my0, my1), (hym, hyp), 0),
        "u0": (lambda t, u: (mx1 + u, t), (my0, my1), (hym, hyp), 180),
    }
    HAS = {"v0": hym, "v1": hyp, "u1": hxm, "u0": hxp}

    def _notch_t(side, center_ken):
        """切り欠きの中心を **その辺の t 座標**へ直す。
        ⭐ 呼び方は棟の**格子**基準 — u の辺(u0/u1)は `munes[].v0` からの間数、
          v の辺(v0/v1)は `munes[].u0` からの間数(⛔ どちらも Blender の軸ではない)。
        ⚠ **格子 +u = Blender −X** なので、v の辺だけ `W − 中心` へ折り返す。"""
        return (center_ken * ken) if side in ("u0", "u1") else (W - center_ken * ken)

    notch_by_side = {}
    for side, center_ken in (notches or []):
        if side not in SIDES:
            raise SystemExit("⛔ 切り欠きの辺が読めない: %s" % side)
        if HAS[side] <= 0:
            raise SystemExit("⛔ %s は庇を断った辺なので切り欠けない(そこの軒は本屋根)" % side)
        tc = _notch_t(side, center_ken)
        notch_by_side.setdefault(side, []).append((tc - notch_w / 2.0, tc + notch_w / 2.0))

    for side in ("v0", "v1", "u1", "u0"):
        P, (t_lo, t_hi), (h_lo, h_hi), yaw = SIDES[side]
        if HAS[side] <= 0:
            continue
        long_axis = 'x' if side in ("v0", "v1") else 'y'

        def start(u, _lo=t_lo, _h=h_lo):
            return _lo - u if _h > 0 else _lo

        def finish(u, _hi=t_hi, _h=h_hi):
            return _hi + u if _h > 0 else _hi

        cuts = sorted(notch_by_side.get(side, []))
        if not cuts:
            # ⭕ 切り欠きが無い辺は**一枚のまま**葺く — 軒桁の線で割ると切り口が二重になり
            #   三角が 1 割増える(姿は同じ)。既に焼いた部材と幾何を揃える意味でも割らない
            polys = [[P(start(-HIRA_OVER), -HIRA_OVER), P(finish(-HIRA_OVER), -HIRA_OVER),
                      P(finish(run), run), P(start(run), run)]]
            segs = []
        else:
            polys = [[P(start(-HIRA_OVER), -HIRA_OVER), P(finish(-HIRA_OVER), -HIRA_OVER),
                      P(finish(keta_u), keta_u), P(start(keta_u), keta_u)]]
            # 外(軒桁の線 → 軒先)は切り欠きで分かれる。⛔ 切り欠きの中へ瓦を残さない
            segs, a = [], start(run)
            for (n0, n1) in cuts:
                segs.append((a, n0)); a = n1
            segs.append((a, finish(run)))
        for (s0, s1) in segs:
            q = [(max(start(keta_u), s0), keta_u), (min(finish(keta_u), s1), keta_u),
                 (min(finish(run), s1), run), (max(start(run), s0), run)]
            if min(q[1][0] - q[0][0], q[2][0] - q[3][0]) < 0.01:
                continue                        # 潰れた断片は葺かない
            polys.append([P(t, u) for (t, u) in q])
        tag = {"v0": "_hS", "v1": "_hN", "u1": "_hW", "u0": "_hE"}[side]
        pieces.append(_tile_field_k(polys, P(start(run), run), yaw, z_tip, name + tag, his))

        # --- 切り欠き(渡廊下が取り付く辺)— 底・奥・両脇を塞ぐ。⛔ 素通しにしない ---
        for (n0, n1) in cuts:
            # ① 受け板 — **天端 = 庇の軒桁の天端 z_keta** の水平面。渡廊下の桁はここへ掛かる
            e0 = P(n0, keta_u - 0.06)
            e1 = P(n1, run)
            o_ = V.box(name + "_kbase",
                       (max(abs(e1[0] - e0[0]), NOTCH_BASE_T), max(abs(e1[1] - e0[1]), NOTCH_BASE_T),
                        NOTCH_BASE_T),
                       ((e0[0] + e1[0]) / 2.0, (e0[1] + e1[1]) / 2.0, z_keta - NOTCH_BASE_T / 2.0),
                       p['wood'])
            V.set_uv_rect(o_, WOOD_UV, axes=('z', long_axis))
            new_geo.append((o_, None))
            notch_world.append(P((n0 + n1) / 2.0, keta_u + noki * 0.5) + (z_keta,))
            # ② 奥の塞ぎ — 軒桁の線に立てて、切った瓦場の小口を隠す
            b0 = P(n0, keta_u)
            b1 = P(n1, keta_u + NOTCH_T)
            o_ = V.box(name + "_kback",
                       (max(abs(b1[0] - b0[0]), NOTCH_T), max(abs(b1[1] - b0[1]), NOTCH_T), NOTCH_H),
                       ((b0[0] + b1[0]) / 2.0, (b0[1] + b1[1]) / 2.0, z_keta + NOTCH_H / 2.0),
                       p['wood'])
            V.set_uv_rect(o_, WOOD_UV, axes=('z', long_axis))
            new_geo.append((o_, None))
            # ③ 両脇の塞ぎ — ⛔ 箱で作らない(軒下へ垂れる)。**流れに沿って下る板**を押し出す
            uz = [(keta_u, z_keta + 0.18), (run, z_tip + 0.18),
                  (run, z_tip - 0.10), (keta_u, z_keta - 0.10)]
            for (tn, sgn) in ((n0, -1.0), (n1, +1.0)):
                o_ = _prism_uz(P, tn, tn + sgn * NOTCH_T, uz, p['wood'], name + "_kside")
                V.set_uv_rect(o_, WOOD_UV, axes=('z', 'y' if side in ("v0", "v1") else 'x'))
                new_geo.append((o_, None))

    # 隅棟(庇どうしが出会う隅だけ)
    for (hx, hy, cx_, cy_, ox, oy) in ((hxm, hym, mx0, my0, mx0 - run, my0 - run),
                                       (hxp, hym, mx1, my0, mx1 + run, my0 - run),
                                       (hxm, hyp, mx0, my1, mx0 - run, my1 + run),
                                       (hxp, hyp, mx1, my1, mx1 + run, my1 + run)):
        if hx > 0 and hy > 0:
            pieces += ridge((ox, oy, z_tip + 0.02), (cx_, cy_, eave),
                            name + "_sumi", w=0.34, h=0.28)
    # 庇を断った辺で切れる庇の小口 — 袖瓦で塞ぐ(切りっぱなしだと瓦の断面が見える)
    for (hx, sx_in, sx_out) in ((hxm, mx0, mx0 - run), (hxp, mx1, mx1 + run)):
        if hx <= 0:
            continue
        for (hy, ycut) in ((hym, my0), (hyp, my1)):
            if hy > 0:
                continue
            pieces += ridge((sx_in, ycut, eave + HIRA_SODE * 0.8),
                            (sx_out, ycut, z_tip + HIRA_SODE * 0.8),
                            name + "_hsode", w=0.30, h=0.24)
    for (hy, sy_in, sy_out) in ((hym, my0, my0 - run), (hyp, my1, my1 + run)):
        if hy <= 0:
            continue
        for (hx, xcut) in ((hxm, mx0), (hxp, mx1)):
            if hx > 0:
                continue
            pieces += ridge((xcut, sy_in, eave + HIRA_SODE * 0.8),
                            (xcut, sy_out, z_tip + HIRA_SODE * 0.8),
                            name + "_hsode", w=0.30, h=0.24)

    #   ⛔ 入れないと、本屋根を切った断面が庇の瓦の上に剥き出しで載る(白い筋になる)。
    #   ⚠ 隅で天端が同一平面で重なると z-fighting するので、x の板は y の板のぶん詰める。
    for (h_, yb, sgn) in ((hym, my0, -1.0), (hyp, my1, +1.0)):
        if h_ <= 0:
            continue
        o_ = V.box(name + "_mizuY", (mx1 - mx0, HIRA_MIZU, 0.25),
                   ((mx0 + mx1) / 2.0, yb + sgn * HIRA_MIZU / 2.0, eave + 0.005), p['wood'])
        V.set_uv_rect(o_, WOOD_UV, axes=('z', 'x'))
        new_geo.append((o_, None))
    for (h_, xb, sgn) in ((hxm, mx0, -1.0), (hxp, mx1, +1.0)):
        if h_ <= 0:
            continue
        ya = my0 + (HIRA_MIZU if hym > 0 else 0.0)
        yb2 = my1 - (HIRA_MIZU if hyp > 0 else 0.0)
        o_ = V.box(name + "_mizuX", (HIRA_MIZU, yb2 - ya, 0.25),
                   (xb + sgn * HIRA_MIZU / 2.0, (ya + yb2) / 2.0, eave + 0.005), p['wood'])
        V.set_uv_rect(o_, WOOD_UV, axes=('z', 'y'))
        new_geo.append((o_, None))

    for o, uv in new_geo:
        if o:
            if uv:
                V.set_uv(o, uv)
            pieces.append(o)
    pieces = [q for q in pieces if q]
    V.dedup_materials()
    o = V.join(pieces, name)
    V.set_origin(o, (W / 2.0, D / 2.0, 0.0))
    if notch_world:                             # 検証レンダが寄る先(⛔ 人が座標を書かない)
        o["notch_pts"] = [c for pt in notch_world for c in pt]
    _verify_hirairi(o, W, D, eave, omit, hon, his, noki, hken, ken, name,
                    notches=notches, notch_w=notch_w)
    return o


def _verify_hirairi(o, W, D, eave, omit, hon, his, noki, hken, ken, name,
                    notches=(), notch_w=None):
    """⛔⛔ **非対称(`hisashiOmit` のある)棟を焼いたら必ず回す検算。**

    ⚠ **外形(bbox)では見抜けない** — 庇を断った辺は本屋根の軒が 0.9 出るので、
      庇のある辺(庇一間 + 軒 0.9)と**外形が対称のまま**になる。
      ⇒ 辺ごとに**軒先の手前 0.30m の屋根面の高さ**を測る(庇なら深く下がり、
        本屋根の軒なら浅い)。ピボット基準(z=0 が床)。"""
    hxm, hxp, hym, hyp = _hirairi_sides(W, D, omit, hken, ken)
    px, py = W / 2.0, D / 2.0            # ピボット(足形の中心)
    vs = [(v.co.x + px, v.co.y + py, v.co.z) for v in o.data.vertices]
    run = hken * ken + noki
    probe = 0.30
    rows, bad = [], 0
    for tag, h_, axis, sgn, inner, outer in (
            ("v0(-Y)", hym, 1, -1.0, hym, hym - run),
            ("v1(+Y)", hyp, 1, +1.0, D - hyp, D - hyp + run),
            ("u1(-X)", hxm, 0, -1.0, hxm, hxm - run),
            ("u0(+X)", hxp, 0, +1.0, W - hxp, W - hxp + run)):
        if h_ > 0:
            line = outer + (probe if sgn < 0 else -probe)
            want = eave - (run - probe) * his
        else:
            line = inner + sgn * (noki - probe)
            want = eave - (noki - probe) * hon
        cut = [v for v in vs if abs(v[axis] - line) < 0.06
               and abs(v[1 - axis] - (py if axis == 0 else px)) < min(W, D) * 0.25]
        got = max((v[2] for v in cut), default=float('nan'))
        # ⚠ 瓦の実体は名目平面に対し −0.15〜+0.15 でうねる(位相しだい)。⇒ 下は緩く上は締める。
        ng = not (want - 0.16 <= got <= want + 0.30)
        bad += 1 if ng else 0
        rows.append("    %-8s 庇%s  軒先手前0.3m の天端 %.3f(従属値 %.3f)%s"
                    % (tag, "有" if h_ > 0 else "無", got, want, "  <<" if ng else ""))
    # --- 切り欠き(渡廊下の取り付き)------------------------------------------
    #   ⭐ **軒先の側で測る** — 切り欠きが効いていれば天端は**軒桁の天端 z_keta** の水平な棚、
    #     効いていなければ瓦の流れ(z_tip ≒ 0.4 低い)。⛔ 軒桁の線の近くで測ると差が出ない。
    keta_u = hken * ken
    z_keta = eave - keta_u * his
    z_tip = eave - (keta_u + noki) * his
    print("VERIFY %s  ピボット=足形の中心/床  **庇の軒桁の天端 z=%.4f**(桁の掛かる面)" % (name, z_keta))
    for (side, ck) in (notches or []):
        tc = (ck * ken) if side in ("u0", "u1") else (W - ck * ken)
        half = (notch_w or ken) / 2.0
        # ⚠⚠ **頂点では測れない** — 受け板は箱なので頂点が隅にしかなく、帯で拾うと空になる
        #   (2026-09-20 に nan を出して「板が焼けていない」と誤診しかけた)。
        #   ⭕ **真上から光線を落として当たりの高さを読む**(ピボット基準 = オブジェクト局所)。
        # ⚠ 深さ u は **身舎の壁**から測る(⛔ 足形の縁からでも 0 からでもない)
        depth = keta_u + noki - 0.25                 # 軒先寄り(切り欠きが効けば棚・効かねば瓦)
        if side == "v0":
            wp = (tc, hym - depth)
        elif side == "v1":
            wp = (tc, (D - hyp) + depth)
        elif side == "u1":
            wp = (hxm - depth, tc)
        else:
            wp = ((W - hxp) + depth, tc)
        loc = mathutils.Vector((wp[0] - px, wp[1] - py, 12.0))
        hit, hp, _n, _i = o.ray_cast(loc, mathutils.Vector((0.0, 0.0, -1.0)), distance=30.0)
        got = hp.z if hit else float('nan')
        # ⭐⭐ **当たりは「最も低い交点」** — 受け面の**下**にもう一枚(板の下端)が在る。
        #   棟梁の実機はそちらを拾うので、**板の下端まで測って刷る**
        #   (2026-09-20: 厚 0.08 の板の下端が拾われ『切り欠きが効いていない』と読まれた)。
        low, guard = got, 0
        while hit and guard < 8:
            hit, hp, _n, _i = o.ray_cast(mathutils.Vector((loc.x, loc.y, low - 1e-4)),
                                         mathutils.Vector((0.0, 0.0, -1.0)), distance=30.0)
            if hit:
                low = hp.z
            guard += 1
        ng = not (z_keta - 0.12 <= got <= z_keta + 0.02)
        bad += 1 if ng else 0
        rows.append("    切欠 %-3s @%-5g間  受け面 %.4f / **板の下端 %.4f**(厚 %.4f)"
                    "(従属値 %.4f / 切らねば %.3f)%s"
                    % (side, ck, got, low, got - low, z_keta, z_tip, "  <<" if ng else ""))
    for r in rows:
        print(r)
    if bad:
        raise SystemExit("⛔ %s: 辺ごとの軒先の高さが従属値と合わない(%d 辺)— 軸の鎖を疑え" % (name, bad))


def make_rokageya(L, width=KEN, name="Goten_Roof_RokaGeya",
                  kobai=0.40, noki=0.90, end=0.10):
    """**渡廊下の差し掛けの下屋(両流れ)**。返り値 = 1メッシュ。

    L = 桁行[m](`links` の矩形の長辺)/ width = 幅[m](短辺)/ kobai = `const.sashikakeKobai`。

    ⭐⭐ **ピボットの z=0 は「頭」**(= 葺き下ろしの線 = 廊下の芯の屋根面の頂)。
      ⛔ 床でも軒先でもない — 頭の高さは**相手の棟ごとに違う従属値**(その端の当たり −
      `roka.clear`)で、部材の中には持てない。⇒ 棟梁は **y = その値**にそのまま置く。
      大棟(冠瓦)はその上へ 0.13 出る(当たりまでの `clear` 0.1 に収まらない分は、
      指図④の「庇の軒先を取り付く幅だけ切り詰める」notch の中へ入る)。
    ⭕ 頭は**廊下の芯**に通し、幅の両側へ下る(2026-09-18 普請奉行の決定5)。
      ⛔ 片流れにしない — 柱筋の頭上の有効高が下限を大きく割る。
    ⚠ 両端は主屋の面へ **0.10 差し込む**(`end`)。ピボットは呼び寸 L の中心で、
      bbox は L + 0.20 になる。⛔ bbox から桁行を読まない。"""
    x0, x1 = -end, L + end
    y0, y1 = -noki, width + noki
    ym = width / 2.0
    zl = -(ym + noki) * kobai                  # 軒先(頭から下がる量)
    pieces = []
    pieces.append(_tile_field_k([[(x0, y0), (x1, y0), (x1, ym), (x0, ym)]],
                                (x0, y0), 90, zl, name + "_S", kobai))
    pieces.append(_tile_field_k([[(x1, y1), (x0, y1), (x0, ym), (x1, ym)]],
                                (x0, y1), 270, zl, name + "_N", kobai))
    p = palette()
    # 大棟 — 座を 0.13 下げて瓦へ食い込ませる(浮かせると棟の脇に隙が抜ける)
    pieces += ridge((x0, ym, -0.13), (x1, ym, -0.13), name + "_omune", w=0.34, h=0.26)
    new_geo = []
    for gx, inward in ((x0, +1), (x1, -1)):
        g = gable(gx, inward, y0, y1, zl, ym, 0.0, name + "_g", p,
                  thick=0.10, bw=0.22, bt=0.06, drop=0.72, lattice=False, gegyo=False)
        bpy.data.objects.remove(g[0][0], do_unlink=True)   # 妻壁は捨てる(両端とも主屋へ突き付く)
        new_geo += g[1:]
    for o, uv in new_geo:
        if o:
            if uv:
                V.set_uv(o, uv)
            pieces.append(o)
    pieces = [q for q in pieces if q]
    V.dedup_materials()
    o = V.join(pieces, name)
    V.set_origin(o, (L / 2.0, ym, 0.0))
    return o


def render_hirairi(o, path_dir, tag, eave=2.744):
    """平入り+庇の検証レンダ。⭕ **見るのは5点** — 庇が身舎を回っているか /
    庇と本屋根の継ぎ目(雨押え)が通っているか / 妻が破綻していないか /
    軒先が一直線か / **どの辺の庇を断ったか(真上)**。
    ⚠ `export_fbx` を通すと bbox が 0 に潰れるので、**書き出しの前に**呼ぶこと。"""
    V.hook_textures()
    mn, mx = V.bbox([o])
    cx, cy = (mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0
    W, D = mx.x - mn.x, mx.y - mn.y
    r = max(W, D)
    os.makedirs(path_dir, exist_ok=True)
    out = []

    def shot(sub, cam, look, ortho=None, res=(1600, 1000)):
        for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
            bpy.data.objects.remove(c, do_unlink=True)
        for pl in [c for c in bpy.data.objects if c.name.startswith("Plane")]:
            bpy.data.objects.remove(pl, do_unlink=True)
        # ⚠ 地面は **部材の最下端の下**へ置く(⛔ z=0 に置かない)— 下屋はピボットが
        #   「頭」で本体が z<0 に在るので、z=0 の板が屋根を切って**大棟しか写らない**
        #   (2026-09-20 に踏んだ。「瓦場が焼けていない」と誤診しかけた)
        bpy.ops.mesh.primitive_plane_add(size=r * 6, location=(cx, cy, mn.z - 0.05))
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(path_dir, "%s_%s.png" % (tag, sub))
        V.render(f)
        out.append(f)

    # ⚠ 画角は**部材の実測から**取る(⛔ 軒高の引数で組まない)— ピボットが「頭」の
    #   下屋は本体が z<0 に在るので、軒高で組むと被写体が画面の外へ落ちる
    zc, zh = (mn.z + mx.z) / 2.0, max(0.6, mx.z - mn.z)
    shot("01_fukan", (cx - r * 0.72, cy - r * 0.95, mx.z + r * 0.85), (cx, cy, zc))
    shot("02_tsuma", (cx - r * 3.0, cy, zc), (cx, cy, zc), ortho=max(D, zh) * 1.3)
    shot("03_hira", (cx, cy - r * 3.0, zc), (cx, cy, zc), ortho=max(W, zh) * 1.15)
    shot("04_yori", (cx - W * 0.22, cy - D * 0.85, mx.z + zh * 0.5),
         (cx - W * 0.30, cy - D * 0.2, zc), res=(1500, 1000))
    shot("05_shinjo", (cx, cy, mx.z + r * 1.2), (cx, cy, mn.z),
         ortho=max(W, D) * 1.06, res=(1400, 1400))
    # 6) ⭐ **切り欠きの寄り** — 桁の掛かる面(軒桁の天端)が平らに出ているか・脇と奥が塞がっているか
    pts = list(o.get("notch_pts") or [])
    for k in range(0, len(pts), 3):
        q = mathutils.Vector((pts[k], pts[k + 1], pts[k + 2]))
        d = mathutils.Vector((q.x - cx, q.y - cy, 0.0))
        d = d.normalized() if d.length > 1e-6 else mathutils.Vector((1.0, 0.0, 0.0))
        shot("06_kirikaki%d" % (k // 3), (q.x + d.x * 3.1 + d.y * 1.2,
                                          q.y + d.y * 3.1 - d.x * 1.2, q.z + 1.35),
             (q.x - d.x * 0.6, q.y - d.y * 0.6, q.z - 0.10), res=(1500, 1000))
        # 7) ⭐ **見上げ** — 受け板の**厚**(3分)と下端が見える角度。⛔ 上からの絵では読めない
        # 7) ⭐ **切り欠きの正面(正射影)** — 受け板の**厚**が実寸で読める唯一の絵。
        #   ⚠ 斜めの見上げでは 3分(9mm)の小口は読めない。⚠ カメラは地面板より上に置く。
        shot("07_kirikaki%d_seimen" % (k // 3),
             (q.x + d.x * 5.0, q.y + d.y * 5.0, q.z - 0.02), (q.x, q.y, q.z - 0.02),
             ortho=2.4, res=(1500, 900))
    return out


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
    if argv and argv[0] == "hirairi":
        # 平入り + 庇 — `-- hirairi <桁行間数> <梁間間数> <身舎の軒桁m(床上)> [名前]`
        #   --omit v1[,u0...]  庇を回さない辺(格子の綴り)/ --hon <勾配> / --his <勾配>
        #   --notch u1-2.5[,v1-4.5]  渡廊下が取り付く辺の切り欠き(辺-中心の間数)
        #   --noki <m> / --hisashi-ken <間> / --render [<出力ディレクトリ>]
        wk = float(argv[1]); dk = float(argv[2]); ev = float(argv[3])
        rest = argv[4:]
        nm = rest[0] if rest and not rest[0].startswith("--") else None
        kw = dict(hon=0.60, his=0.45, noki=0.90, hken=1)
        omit, notch, rdir = [], [], None
        i = 0
        while i < len(rest):
            t = rest[i]
            if t == "--omit":   omit = [q for q in rest[i + 1].split(",") if q]; i += 2
            elif t == "--notch":
                # ⭐ `u1-2.5,v1-4.5` = 辺と**中心の間数**(u の辺は棟の v0 から / v の辺は u0 から)
                for tok in rest[i + 1].split(","):
                    if not tok.strip():
                        continue
                    sd, _, cc = tok.partition("-")
                    notch.append((sd.strip(), float(cc)))
                i += 2
            elif t == "--hon":  kw['hon'] = float(rest[i + 1]); i += 2
            elif t == "--his":  kw['his'] = float(rest[i + 1]); i += 2
            elif t == "--noki": kw['noki'] = float(rest[i + 1]); i += 2
            elif t == "--hisashi-ken": kw['hken'] = int(rest[i + 1]); i += 2
            elif t == "--render":
                if i + 1 < len(rest) and not rest[i + 1].startswith("--"):
                    rdir = rest[i + 1]; i += 2
                else:
                    rdir = os.path.join(V.REPO, "Screenshots"); i += 1
            else: i += 1
        if nm is None:
            nm = hirairi_name(wk, dk, ev, omit, notch)
        V.reset()
        o = make_hirairi(wk * KEN, dk * KEN, ev, omit=omit, name=nm, notches=notch, **kw)
        report(o, nm)
        if rdir:
            for f in render_hirairi(o, rdir, nm, eave=ev):
                print("RENDER %s" % f)
        V.export_fbx(o, os.path.join(OUT, nm + ".fbx"))
        raise SystemExit(0)
    if argv and argv[0] == "geya":
        # 渡廊下の差し掛けの下屋(両流れ)— `-- geya <桁行間数> [名前]`
        #   --width <間> / --kobai <勾配> / --noki <m> / --render [<dir>]
        nk = float(argv[1])
        rest = argv[2:]
        nm = rest[0] if rest and not rest[0].startswith("--") else None
        kw = dict(kobai=0.40, noki=0.90)
        wid = 1.0
        rdir = None
        i = 0
        while i < len(rest):
            t = rest[i]
            if t == "--width":  wid = float(rest[i + 1]); i += 2
            elif t == "--kobai": kw['kobai'] = float(rest[i + 1]); i += 2
            elif t == "--noki":  kw['noki'] = float(rest[i + 1]); i += 2
            elif t == "--render":
                if i + 1 < len(rest) and not rest[i + 1].startswith("--"):
                    rdir = rest[i + 1]; i += 2
                else:
                    rdir = os.path.join(V.REPO, "Screenshots"); i += 1
            else: i += 1
        if nm is None:
            nm = "Goten_Roof_RokaGeya_%sken" % KenTag(nk)
        V.reset()
        o = make_rokageya(nk * KEN, wid * KEN, name=nm, **kw)
        report(o, nm)
        if rdir:
            for f in render_hirairi(o, rdir, nm, eave=1.2):
                print("RENDER %s" % f)
        V.export_fbx(o, os.path.join(OUT, nm + ".fbx"))
        raise SystemExit(0)
    if argv and argv[0] == "banded":
        # 帯割りの入母屋 — `-- banded <帯(例 4,4)> <桁行間数> [名前] [旗...]`
        #   --along u|v / --irikawa <間> / --eave <m> / --noki <m> / --tsuma <m>
        #   --noki-edges u0,u1,v0,v1(1=軒を出す / 0=落とす。接する辺は 0)
        #   --fukizai sangawara|hongawara / --render <出力ディレクトリ>
        bands = [int(t) for t in argv[1].split(",") if t.strip()]
        span = int(argv[2])
        rest = argv[3:]
        nm = rest[0] if rest and not rest[0].startswith("--") else None
        kw = dict(along="u", irikawa=1.0, eave=3.4, noki_de=0.90,
                  tsuma_end=0.30, fukizai="sangawara")
        rdir = None
        i = 0
        while i < len(rest):
            t = rest[i]
            if t == "--along":   kw['along'] = rest[i + 1]; i += 2
            elif t == "--irikawa":
                # ⭐ スカラ(四周同じ)か、**グリッド順の4つ組 u0,u1,v0,v1**
                #   例) --irikawa 0,0,1,1 = 指図 {"u":[0,0],"v":[1,1]}
                v_ = rest[i + 1]
                kw['irikawa'] = ([float(t_) for t_ in v_.split(",")]
                                 if "," in v_ else float(v_)); i += 2
            elif t == "--noki-edges":
                # ⭐ 辺ごとに軒を出すか。**グリッド順 u0,u1,v0,v1**(1=出す / 0=落とす)
                #   例) --noki-edges 1,0,1,1 = u1 の辺(隣の棟と接する辺)だけ軒を落とす
                kw['noki'] = [int(t_) for t_ in rest[i + 1].split(",")]; i += 2
            elif t == "--eave":  kw['eave'] = float(rest[i + 1]); i += 2
            elif t == "--noki":  kw['noki_de'] = float(rest[i + 1]); i += 2
            elif t == "--tsuma": kw['tsuma_end'] = float(rest[i + 1]); i += 2
            elif t == "--fukizai": kw['fukizai'] = rest[i + 1]; i += 2
            elif t == "--render":
                if i + 1 < len(rest) and not rest[i + 1].startswith("--"):
                    rdir = rest[i + 1]; i += 2
                else:
                    rdir = os.path.join(V.REPO, "Screenshots"); i += 1
            else: i += 1
        V.reset()
        o = make_banded(bands, span, name=nm, **kw)
        name = o.name
        mn, mx = report(o, name)
        # ⚠ 検証レンダは **書き出しの前**に撮る(export_fbx を通すと bbox が 0 に潰れる)
        if rdir:
            for f in render_banded(o, rdir, name, eave=kw['eave']):
                print("RENDER %s" % f)
        V.export_fbx(o, os.path.join(OUT, name + ".fbx"))
        raise SystemExit(0)
    if argv and argv[0] == "yosemune":
        # 寄棟 — `-- yosemune <桁行m> <梁間m> [名前]`。⚠ 桁行 ≧ 梁間 で呼ぶ
        W = float(argv[1]); D = float(argv[2])
        name = argv[3] if len(argv) > 3 else "Goten_Roof_Yosemune"
        V.reset()
        o = make_yosemune(W, D, name)
        mn, mx = report(o, name)
        V.export_fbx(o, os.path.join(OUT, name + ".fbx"))
    elif argv and argv[0] == "kirizuma":
        if len(argv) > 1:                       # 単発: -- kirizuma <間数(端数可)>
            n = float(argv[1])
            V.reset()
            # ⚠ 端数の間数(渡廊下 1.5間など)は `1.5ken` と刷る。整数は従来どおり `3ken`
            name = "Goten_Roof_Kirizuma_%sken" % (("%g" % n) if n != int(n) else "%d" % int(n))
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
