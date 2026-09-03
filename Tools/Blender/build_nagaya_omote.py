"""**長さ可変の表長屋**を、在庫の `knagaya01c/l/r` から切って・並べて・留めて起こす。

    blender --background --python Tools/Blender/build_nagaya_omote.py -- 28.5
    blender --background --python Tools/Blender/build_nagaya_omote.py -- 28.5 --render
    blender --background --python Tools/Blender/build_nagaya_omote.py -- 20.0 --ends none
    blender --background --python Tools/Blender/build_nagaya_omote.py -- 12 16.35 28.5   # まとめて
    blender --background --python Tools/Blender/build_nagaya_omote.py -- 63.18 --gate 10.18 3.0 3.0  # 長屋門

【なぜ要るか】在庫の長屋は **中部材 8.065m / 妻部材 7.910m の固定寸法**しかない。外周の run は
  「丸ごとの棟を並べる」形でしか埋められないので、端数が必ず門・隅との間に残る
  (松江松平邸 御蔵門の西に 1.66m の食い込み・東に 0.96m の隙間が同時に出た。2026-08-29 実測)。
  **ユーザー裁定 2026-08-29:「長い表長屋を Blender で作るのが一番良い」** → 長さを引数にとる。

【方針】**ゼロからモデリングしない。**素の `knagaya01c.obj`(1棟=3窓)を**一間の窓割り(＝bay)**で
  切り出して並べ、両端に `knagaya01l/r` の妻(破風・鬼・妻壁)を継ぐ。彫り・瓦の実ジオメトリ・
  海鼠の浮き彫り・マテリアル名がそのまま残るので、隣に建つ在庫の長屋と質感が揃う。

【素の作り(実測。すべて obj 単位。×ES=1.818 で m)】
  ・1棟 = 4.4347 (= 8.062m)、その中に **窓が3つ**。したがって **bay = 棟/3 = 1.47823 (= 2.6874m)**
  ・窓(koshi)は幅 0.633 (1.151m)、窓と窓の間の無地の壁(pier)は 0.845 (1.536m)
  ・**海鼠(namako)・瓦(n_hira/n_maru/n_noki)は bay で完全に周期的**(頂点一致を総当たりで確認:
    namako 1828/1828・maru 438/438・hira 438/438・noki 12488/12512)。だから bay で切って
    並べれば継ぎ目は出ない。⛔ **bay より細かい共通周期は無い**(垂木だけ 0.3409 の独自ピッチ)
  ・妻部材 `l`/`r` は `c` と**同じ座標系**(屋根群の bbox が桁まで一致)。妻側だけ壁が 0.103 内へ
    引かれ、`namako2`(妻壁)・`n_kera_*`(破風)・`n_oni`(鬼)が付く

【長さの作り方】L から bay の本数 k と **pier の詰め ε** を解く:
      L/ES = 2·(1.67561 − ε/2) + k·(1.47823 − ε)
  ε は「窓と窓の間の無地の壁を全継ぎ目で一様に詰める/広げる」量。窓・瓦・海鼠の**形は一切
  伸ばさない** — 割付の繰り返し数 k と無地の pier だけで長さを吸う(ユーザー指示 2026-08-29)。
  ソルバは |ε| が最小になる k を選ぶので **L≥12m で |ε|≤0.21m、L≥20m で |ε|≤0.08m**。

【`--ends none`】両端を切りっぱなしにして隣へ突き付ける版。⚠ **切り口の位相は ε だけずれる**ので、
  ε の違う2本を突き付けると海鼠の紋が (εA−εB)/2 だけ食い違う。同じ長さ同士か、
  素の `knagaya01c` の継ぎ目と同程度(±0.1m)に収まる長さ同士で使うこと。

【`--gate <中心m> <幅m> <高さm>`】**長屋門**(ユーザー裁定 2026-08-30)。躯体を門の上まで通し、
  足元に門口を抜き、**両開きの板戸(高さ DOOR_H=2.8m)と扉の上の小壁まで作り付ける**
  (ユーザー裁定2-A 2026-08-31。以前は Unity 側が在庫の冠木門を落とし込んでいたが、
   部材の全幅を開口幅に合わせていたため躯体が 1.56m しか無く左右に 0.72m ずつ隙間が空き、
   門の小屋根が長屋の通し屋根と二重になっていた)。
  ・中心は**出来上がりの部材のローカル +X の左端から**。⚠ 書き出す前に Z まわりに 180° 回すので
    obj 空間では**右端から**測って抜く(取り違えると門口が反対の端に出る。2026-08-30 に踏んだ)
  ・高さは**土台の底から**。⚠ obj の z は 0 が底ではない(底は負)ので、絶対 z として渡すと
    切る面が高すぎて**屋根まで抜ける**(全高の切り欠きになる。2026-08-30 に踏んだ)
  ・1階の軒の下端までおよそ 4.0m あるので 3.0m の門口が収まる
  ・⛔ **開口だけの短い部材は作れない**(妻2つ+bay で最小およそ 8.8m)。門口は長い run の中に開ける
  ・抜いたあと左右の方立と上の楣を張るので、開口の縁は透けない(検証レンダ `*_mon3d.png` で確認)

【切る場所】切断面は**必ず pier(無地の壁)の中**に取る。窓を切ると格子の小口が出る。
  bay の切り出しは `c` の中央の窓を挟んで対称に、妻の切り出しは妻寄りの窓を挟んで同じ位相で
  取るので、**継ぎ目の断面は互いに平行移動で一致する**(留め継ぎと同じ理屈)。

【出力の向き(Unity 座標)】幅=X / 高さ=Y / 厚み=Z、**見え面(街路側)= +Z**。
  ピボット = **走りの中心・土台の底・壁の外面**。壁の外面が Z=0 なので、外周線の上に
  `position = run の中点 / yaw = 外向き法線の方位 / scale = Vector3.one` で置ける。
  軒は +Z へ 0.58m 出て、躯体は −Z へ 3.12m 入る。
  ⚠ FBX 書き出しは Blender +Y を Unity −Z へ写す(README)。素の向き(表 = +Y)のままだと
    見え面が裏に出るので、書き出す前に **Z まわりに 180° 回す**(鏡映ではなく回転 —
    鏡映すると巻きが裏返るうえ窓割りが左右反転する)。

【落とし穴】
  ・obj を読んで `transform_apply` すると **X が反転する**(forward_axis='Z' の帰結)。
    素の x と符号が逆になるので、寸法は必ず読み込み後のメッシュから測ること。
  ・`bisect` は面を持たない頂点・辺を残す。消さないと bbox が嘘をつく(build_kado と同じ罠)。
  ・素は 1 マテリアル `knagayamap` で、しかも .obj の**サブアセット**として抱えられている。
    Unity の `SearchAndRemapMaterials` では当たらない → 提供元を名指しで結ぶ remap を使う
    (`Edo/長屋/表長屋のマテリアルをremap`)。
  ・素のモデルは**海鼠の浮き彫りが窓の下半分を横切っている**(z が重なっている)。これは
    在庫の意匠そのものなので直さない — 直すと隣の在庫長屋と見た目が食い違う。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ES   = 1.818                      # 江戸暦の共通スケール(EdoAssets.Eg.ES_NOTE)
SRC  = os.path.join(V.REPO, "Assets/edogoyomi/es_knagaya")
OUT  = os.path.join(V.REPO, "Assets/Edo/Models/Nagaya")
SHOT = os.path.join(V.REPO, "Screenshots")

EPS_MAX = 0.50                    # pier を詰められる上限(obj)。0.845 → 0.345 (0.63m) まで
EPS_MIN = -0.65                   # 広げられる上限。0.845 → 1.495 (2.72m) まで


# ---------------------------------------------------------------- 取り込み
def read_groups(stem):
    """.obj を群ごとに読み、Y-up→Z-up を焼いて {群名: object} で返す。
    ⚠ 焼くと **X が反転する**。以降の座標はすべてこの「焼いたあと」の系。"""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(SRC, stem + ".obj"),
                          forward_axis='Z', up_axis='Y', use_split_groups=True)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    V.sel(meshes)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return {o.name.split('.')[0]: o for o in meshes}, meshes


def xspan(o):
    xs = [v.co.x for v in o.data.vertices]
    return min(xs), max(xs)


def win_centers(koshi):
    """格子の頂点 x を隙間 0.30 で塊に割り、各窓の中心を返す(左→右)。"""
    xs = sorted(set(round(v.co.x, 4) for v in koshi.data.vertices))
    cl = [[xs[0]]]
    for a, b in zip(xs, xs[1:]):
        (cl.append([b]) if b - a > 0.30 else cl[-1].append(b))
    return [ (c[0] + c[-1]) * 0.5 for c in cl ]


# ---------------------------------------------------------------- 切る
def bisect_keep(o, axis_x, keep_ge):
    """x = axis_x の平面で切り、keep_ge なら x ≥ 側を残す。切り口は塞がない。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5,
                           plane_co=Vector((axis_x, 0, 0)), plane_no=Vector((1, 0, 0)),
                           clear_outer=not keep_ge, clear_inner=keep_ge)
    # ⚠ bisect は面を持たない頂点・辺を残す。消さないと bbox が嘘をつく
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return o


def slab(o, x0, x1):
    bisect_keep(o, x0, True)
    bisect_keep(o, x1, False)
    return o


def shift_x(o, dx):
    for v in o.data.vertices:
        v.co.x += dx
    o.data.update()


def dup(o, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name
    bpy.context.collection.objects.link(c)
    return c


def zspan(o):
    zs = [v.co.z for v in o.data.vertices]
    return min(zs), max(zs)


def bisect_z(o, z, keep_ge):
    """z = z の平面で切り、keep_ge なら z ≥ 側を残す。切り口は塞がない。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5,
                           plane_co=Vector((0, 0, z)), plane_no=Vector((0, 0, 1)),
                           clear_outer=not keep_ge, clear_inner=keep_ge)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return o


def shift_z(o, dz):
    for v in o.data.vertices:
        v.co.z += dz
    o.data.update()


def fill_seam(o, z, tol=2e-4):
    """z の高さに残った境界の穴だけを塞ぐ(2階の窓の下端 = 窓台になる)。
    ⛔ 全部の境界を塞がない — 素の .obj は軒裏などが元から開いている。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    edges = [e for e in bm.edges
             if len(e.link_faces) == 1
             and abs(e.verts[0].co.z - z) < tol and abs(e.verts[1].co.z - z) < tol]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=64)
    bm.to_mesh(me); bm.free(); me.update()
    return len(edges)


def fill_boundary(o, pred, sides=64):
    """境界(片面しか接していない辺)のうち、両端が pred を満たすものだけを塞ぐ。
    ⛔ 全部の境界を塞がない — 素の .obj は軒裏などが元から開いている。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    edges = [e for e in bm.edges
             if len(e.link_faces) == 1 and pred(e.verts[0].co) and pred(e.verts[1].co)]
    n = len(edges)
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=sides)
    bm.to_mesh(me); bm.free(); me.update()
    return n


DOOR_H = 2.8                 # 指図 komon[].leaf の板戸の高さ[m]
DOOR_SETBACK = 0.25          # 扉の表を壁の外面から内へ引く量[m](戸当たり・方立の見込み)
# 板戸の板目 — knagaya.jpg を 16x16 に割って「縦筋が強く横筋がほぼ無い暗い区画」を
# 探して採った(輝度 40.3 / 縦筋 24.5 / 横筋 0.57)。⛔ 新しいテクスチャは作らない。
# ⚠ 海鼠壁の帯から採ると**真っ黒な板**になる(2026-08-31 の1回目)。
DOOR_UV = (0.3125, 0.3125, 0.3750, 0.3750)


def board_uv(o, z_lo, z_hi):
    """腰の下見板の帯から UV 矩形を借りる。**新しい材質もテクスチャも作らない。**
    扉の板は長屋の下見板と同じ材なので、既にある面の UV をそのまま使う。"""
    me = o.data
    uvl = me.uv_layers.active.data
    best, ba, bmi = None, 0.0, 0
    for p in me.polygons:
        if abs(p.normal.y) < 0.9:
            continue
        zc = sum(me.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        if not (z_lo <= zc <= z_hi):
            continue
        if p.area > ba:
            ba, best, bmi = p.area, p, p.material_index
    if best is None:
        return (0.0, 0.0, 1.0, 1.0), 0
    us = [uvl[i].uv[0] for i in best.loop_indices]
    vs = [uvl[i].uv[1] for i in best.loop_indices]
    return (min(us), min(vs), max(us), max(vs)), bmi


def hang_doors(o, x0, x1, z_bot, z_top, leaf_h):
    """**門口に両開きの板戸を吊り、扉の上に小壁を張る(ユーザー裁定2-A 2026-08-31)。**

    ⚠ それまでは Unity 側が在庫の冠木門(`es_kmon/k_mon.obj`)を開口へ落とし込んでいた。
      ところが実装が**部材の全幅(屋根の出と袖塀を含む 14.413m)**を開口幅 3.0m に
      合わせて縮めていたため、壁に接すべき躯体は 7.53m×0.208 = **1.56m** しかなく、
      左右に **0.72m ずつ隙間**が空いていた(ユーザー指摘 2026-08-31)。
      さらに冠木門は自前の小屋根を持つので、長屋の通し屋根と**二重**になっていた。
      → 規則5「部材どうしを中心で合わせない/呼び寸法で合わせない」。
      扉は**長屋の躯体に作り付ける**ことにして、合わせる面を開口の実寸そのものにした。

    座標は obj 単位・Blender Z-up(走り=X / 厚み=Y / 高さ=Z)。carve_gate の直後に呼ぶ。
    """
    me = o.data
    # 開口の左右の小口(方立)から**壁の実厚み**を測る。呼び寸法を使わない
    ys = [v.co.y for v in me.vertices
          if abs(v.co.x - x0) < 2e-3 and z_bot - 1e-3 <= v.co.z <= z_top + 1e-3]
    if len(ys) < 2:
        ys = [v.co.y for v in me.vertices]
    y_in, y_out = min(ys), max(ys)
    t = 0.09 / ES                                   # 板戸の厚み 90mm
    # ⚠ **壁厚の中央に吊らない。** carve_gate は門口の高さの躯体を**建物の全奥行**に
    #   わたって抜くので、方立の y は 3.7m 幅になる。その中央に吊ると扉が建物の
    #   奥まで引っ込み、外から見て門に見えない(2026-08-31 の1回目・実測で
    #   外面から 1.88m 奥にあった)。長屋門の扉は**方立の内側**に吊るものなので、
    #   表(素では +Y)の面から DOOR_SETBACK だけ内へ引いた位置に据える。
    yd1 = y_out - DOOR_SETBACK / ES
    yd0 = yd1 - t

    # 扉は板戸の板目、扉の上の小壁は**開口より上の壁と同じ面**から UV を借りる
    _, mi = board_uv(o, z_bot, z_top)
    u0, v0, u1, v1 = DOOR_UV
    kabe_uv, _mi2 = board_uv(o, z_top, z_top + (z_top - z_bot))

    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new()

    def box(bx0, bx1, by0, by1, bz0, bz1, rect=None):
        a0, b0, a1, b1 = rect if rect else (u0, v0, u1, v1)
        vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for v in vs:
            v.co.x = bx0 if v.co.x < 0 else bx1
            v.co.y = by0 if v.co.y < 0 else by1
            v.co.z = bz0 if v.co.z < 0 else bz1
        for f in set(f for v in vs for f in v.link_faces):
            f.material_index = mi
            for l in f.loops:
                # 走り方向を u・高さを v に取る(板目が縦に立つ)
                fu = (l.vert.co.x - bx0) / max(1e-6, bx1 - bx0)
                fv = (l.vert.co.z - bz0) / max(1e-6, bz1 - bz0)
                l[uvl].uv = (a0 + (a1 - a0) * fu, b0 + (b1 - b0) * fv)

    xm = (x0 + x1) * 0.5
    zl = z_bot + leaf_h / ES                        # 扉の頭
    gap = 0.012 / ES                                # 召し合わせの隙
    box(x0, xm - gap, yd0, yd1, z_bot, zl)          # 左の扉
    box(xm + gap, x1, yd0, yd1, z_bot, zl)          # 右の扉

    # ---- 縦板張りと桟。**形で出す。**
    # ⚠ 板戸は渋墨で真っ黒なので、テクスチャの明暗では板の継ぎ目が出ない
    #   (2026-08-31 の1回目・2回目とも、扉が「黒い板1枚」に見えた)。
    #   板の見付けを 15mm 起こし、桟を 35mm 起こして**陰影で目地を出す**。
    pitch = 0.30 / ES                               # 板の見付け 300mm
    bw = 0.275 / ES                                 # 板の幅(残り 25mm が目地)
    proud = 0.015 / ES
    for lx0, lx1 in ((x0, xm - gap), (xm + gap, x1)):
        nb = max(1, int(round((lx1 - lx0) / pitch)))
        for b in range(nb):
            bc = lx0 + (lx1 - lx0) * (b + 0.5) / nb
            box(bc - bw * 0.5, bc + bw * 0.5, yd1, yd1 + proud, z_bot, zl)
            box(bc - bw * 0.5, bc + bw * 0.5, yd0 - proud, yd0, z_bot, zl)
    sh = 0.13 / ES                                  # 桟の丈 130mm
    sp = 0.035 / ES
    for fz in (0.18, 0.52, 0.86):                   # 下・中・上の三本の桟
        zc = z_bot + (zl - z_bot) * fz
        for lx0, lx1 in ((x0, xm - gap), (xm + gap, x1)):
            box(lx0, lx1, yd1 + proud, yd1 + proud + sp, zc - sh * 0.5, zc + sh * 0.5)
            box(lx0, lx1, yd0 - proud - sp, yd0 - proud, zc - sh * 0.5, zc + sh * 0.5)
    if zl < z_top - 1e-4:                           # 扉の上の小壁(楣まで)
        # ⚠ 建物の全奥行を塞がない。壁と同じ見付けの板 1 枚にする
        box(x0, x1, y_out - 0.30 / ES, y_out, zl, z_top, rect=kabe_uv)
    bm.normal_update()
    bm.to_mesh(me); bm.free(); me.update()
    # 実測して報告する — 「壁の外面から何 m 内側に吊れたか」を目で確かめられるように
    from collections import defaultdict
    acc = defaultdict(float)
    for pg in me.polygons:
        if abs(pg.normal.y) < 0.9:
            continue
        acc[round(me.vertices[me.loops[pg.loop_start].vertex_index].co.y, 3)] += pg.area
    order = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
    print("[nagaya] 壁に平行な面の y(面積の大きい順・m): "
          + " / ".join("%.3f(%.1fm2)" % (y * ES, a * ES * ES) for y, a in order))
    print("[nagaya] 方立から採った y_in %.3f  y_out %.3f  → 扉の表 %.3f (m)"
          % (y_in * ES, y_out * ES, yd1 * ES))
    print("[nagaya] 扉を吊った: 両開き 幅 %.3fm × 高 %.3fm / 上の小壁 %.3fm / 厚み %.3fm"
          % ((x1 - x0) * ES, leaf_h, (z_top - zl) * ES, t * ES))
    return o


def carve_gate(o, x0, x1, z_top, tol=1e-4):
    """**長屋門の門口を抜く(ユーザー裁定 2026-08-30)。**
    走り方向 x の [x0, x1]、高さ z < z_top の躯体を抜き、屋根・軒・二階はそのまま残す。
    抜いたあと左右に方立(小口)と上に楣を張るので、開口の縁が透けない。

    ⚠ 座標は **obj 単位・Blender Z-up**(走り=X / 厚み=Y / 高さ=Z)。呼ぶのは
    向きを直す前・スケールを掛ける前(組み上がった直後)。
    ⛔ 門の躯体(冠木門・扉)はここでは作らない — Unity 側が開口の中へ据える。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    for co, no in ((Vector((x0, 0, 0)), Vector((1, 0, 0))),
                   (Vector((x1, 0, 0)), Vector((1, 0, 0))),
                   (Vector((0, 0, z_top)), Vector((0, 0, 1)))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no,
                               clear_inner=False, clear_outer=False)
    kill = [f for f in bm.faces
            if all((x0 - tol) < v.co.x < (x1 + tol) and v.co.z < (z_top + tol) for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()

    n = 0
    for x in (x0, x1):                                    # 方立(開口の左右の小口)
        n += fill_boundary(o, lambda c, x=x: abs(c.x - x) < 2e-3 and c.z < z_top + tol)
    n += fill_boundary(o, lambda c: abs(c.z - z_top) < 2e-3           # 楣(開口の天井)
                       and (x0 - tol) < c.x < (x1 + tol))
    z_bottom = min(v.co.z for v in o.data.vertices)
    print("[nagaya] 門口を抜いた: 幅 %.3fm / 有効高 %.3fm(土台の底から) / 塞いだ辺 %d"
          % ((x1 - x0) * ES, (z_top - z_bottom) * ES, n))
    return o


def add_floor(o, z_namako_top, z_cut, floors):
    """**二階を積む(案A・ユーザー裁定 2026-08-29)。**
    海鼠壁は腰壁のまま動かさず、白壁の帯 [海鼠の天端 → 壁の天端] を上へ積み増して階を作る。
    屋根と妻の破風・鬼はそのぶん持ち上げる。
    ⛔ 海鼠を二階の腰まで立ち上げない(案B)— 平屋の区間との継ぎ目で帯が段になる。"""
    if floors < 2:
        return o
    dz = z_cut - z_namako_top               # 積む帯の高さ(海鼠の天端 → 屋根の下端)
    for _ in range(floors - 1):
        upper = dup(o, "upper")             # 壁の天端から上(屋根・破風・鬼)
        bisect_z(upper, z_cut, True)
        shift_z(upper, dz)
        band = dup(o, "band")               # 白壁の帯(窓の上半分を含む)
        bisect_z(band, z_namako_top, True)
        bisect_z(band, z_cut, False)
        shift_z(band, dz)
        bisect_z(o, z_cut, False)           # 元は屋根の下端までにする
        o = V.join([o, band, upper], o.name)
        me = o.data
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
        bm.to_mesh(me); bm.free(); me.update()
        n = fill_seam(o, z_cut)             # 2階の窓の下端に窓台を張る
        print("[nagaya] 二階を積んだ: 帯 %.4f (%.3fm) / 窓台を張った辺 %d"
              % (dz, dz * ES, n))
        z_cut += dz
    return o


# ---------------------------------------------------------------- 棟を上げる
BANSHO_OUT   = 0.30      # 出格子の出[m](躯体内の番所の物見)。⛔ 指図に数値なし【確度U】
BANSHO_FRAME = 0.05      # 出格子の枠が窓の外へ回る量[m]【確度U】


def raise_eaves(o, z_cuts, blank_h, extra):
    """**棟を上げる。瓦の勾配は一切触らない — 上げた分はすべて軒高で稼ぐ。**

    上げ代 extra を**各階に等分**し、階ごとに「窓の頭 〜 その階の天端」の
    **無地の白壁**を積んで、その上をまるごと持ち上げる。
    ⛔ 上げ代を全部いちばん上(軒の下)へ積まない — 二階の窓の上に 2.3m の
      のっぺりした白壁が残り、門でなく土蔵に見える(2026-09-04 の1回目で実見)。
    z_cuts は**下の階から順に**並べたその階の天端(=素の軒の下端 + 階の帯 × 階数)。
    ⛔ 帯を1段に伸ばして引き伸ばさない — 漆喰のテクスチャが縦に伸びる。
    無地の帯 blank_h より薄い切片を n = ceil(extra/blank_h) 段に割る。
    ⚠ 座標はすべて obj 単位(×ES=1.818 で m)。**階を積んだ後**に呼ぶこと
      (z_cut は積んだ後の軒の下端)。

    【なぜ要るか】長屋門は両袖の表長屋より棟が高いのが型(ユーザー裁定12-A 2026-09-04:
      表長屋の棟 7.183 に対し**門は 8.5**)。瓦モジュールの勾配 0.5456 は動かせないので、
      梁間を変えずに棟だけ上げるには軒高で稼ぐしかない。
    """
    per = extra / len(z_cuts)
    n = max(1, int(math.ceil(per / blank_h - 1e-9)))
    t = per / n
    off = 0.0
    for zc in z_cuts:                   # 下の階から順に(上の階は前の挿入ぶん持ち上がっている)
        z = zc + off
        upper = dup(o, "eaves_up")      # その階より上(上階の壁・屋根・軒・破風・鬼)
        bisect_z(upper, z, True)
        shift_z(upper, per)
        bisect_z(o, z, False)
        parts = [o]
        for i in range(n):
            b = dup(o, "eband%02d" % i) # 無地の白壁の切片(窓の頭より上・その階の天端まで)
            bisect_z(b, z - t, True)
            shift_z(b, t * (i + 1))
            parts.append(b)
        parts.append(upper)
        o = V.join(parts, o.name)
        me = o.data
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
        bm.to_mesh(me); bm.free(); me.update()
        off += per
    print("[nagaya] 軒を上げた: +%.4f (%.3fm) = 各階 %.3fm(無地の帯 %.3fm x %d 段)x %d 階"
          "(瓦の勾配は不変)" % (extra, extra * ES, per * ES, t * ES, n, len(z_cuts)))
    return o


# ---------------------------------------------------------------- 出格子番所・冠木
def _boxer(o, z_lo, z_hi, rect=None, inset=0.12):
    """新しい箱を **既にある材質のまま** 足すための小道具を返す。
    ⛔ 新しい材質もテクスチャも作らない(規約2)。UV は矩形で借りる(規約3)。

    ⚠ **面ごとに軸を選んで貼る。** 全部の面を u=x / v=z で貼ると、妻面(法線が±X)は
      u が潰れて矩形の**縁の1本の線**を舐め、隣の区画(白い漆喰)が滲んで
      **側板だけ真っ白**になる(2026-09-04 の1回目で実見)。
    ⚠ 借りる矩形は 12% 内側へ寄せる — アトラスは区画の境目で隣へ滲む。
    """
    me = o.data
    _, mi = board_uv(o, z_lo, z_hi)
    r = DOOR_UV if rect is None else rect
    du, dv = (r[2] - r[0]) * inset, (r[3] - r[1]) * inset
    u0, v0, u1, v1 = r[0] + du, r[1] + dv, r[2] - du, r[3] - dv
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new()

    def box(x0, x1, y0, y1, z0, z1, z0o=None, z1o=None):
        """z0o/z1o を渡すと **外側(y1)の高さだけ** そこへ落ちる(庇の勾配)。"""
        z0o = z0 if z0o is None else z0o
        z1o = z1 if z1o is None else z1o
        vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for v in vs:
            outer = v.co.y > 0
            v.co.x = x0 if v.co.x < 0 else x1
            v.co.z = (z0o if outer else z0) if v.co.z < 0 else (z1o if outer else z1)
            v.co.y = y0 if not outer else y1
        for f in set(f for v in vs for f in v.link_faces):
            f.material_index = mi
            n = f.normal
            if abs(n.z) > 0.7:        ia, ib = 0, 1     # 水平面(庇の上下)
            elif abs(n.x) > 0.7:      ia, ib = 1, 2     # 妻面(袖板の小口)
            else:                     ia, ib = 0, 2     # 正面・背面
            aa = [l.vert.co[ia] for l in f.loops]
            bb = [l.vert.co[ib] for l in f.loops]
            a0, a1 = min(aa), max(aa)
            b0, b1 = min(bb), max(bb)
            for l in f.loops:
                fu = (l.vert.co[ia] - a0) / max(1e-6, a1 - a0)
                fv = (l.vert.co[ib] - b0) / max(1e-6, b1 - b0)
                l[uvl].uv = (u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv)

    def done():
        bm.normal_update(); bm.to_mesh(me); bm.free(); me.update()
    return box, done


def add_degoshi(o, centers, y_front, z_sill, z_head, half_w):
    """**両端の番所に出格子を付ける(指図 gate.plan.bansho「躯体内の出格子番所」)。**

    ⛔ **張り出しの番所(別棟)は作らない** — 指図が 2026-08-31 に「躯体内」へ改めており、
      桁行9間 = 門戸6間 + 番所 1.5間×2 が閉じる必要がある(別棟にすると建蔽率も二重計上)。
    ⭕ したがって番所は躯体の中にあり、**外へ出るのは物見の出格子だけ**。

    ⚠ **素の窓は1間に上下2段ある**(下 1.07〜1.65m / 上 2.74〜3.32m・実測)。
      出格子は**下段だけ**を覆う — 2段まとめて覆うと 1.25m 幅 × 2.25m 丈の
      電話ボックスになる(2026-09-04 の1回目で実見)。上段は武者窓のまま残す。

    座標は obj 単位・Blender Z-up(走り=X / 厚み=Y / 高さ=Z)。**向きを直す前**に呼ぶ
    (この段階では表が +Y)。centers は窓の中心 x の並び。
    """
    box, done = _boxer(o, z_sill, z_head)
    p  = BANSHO_OUT / ES                        # 出
    hw = half_w + BANSHO_FRAME / ES             # 枠まで含む半幅
    for xc in centers:
        x0, x1 = xc - hw, xc + hw
        y0, y1 = y_front, y_front + p
        # 膳板(持ち出しの下枠)。少し大きめに回して雨仕舞いに見せる
        box(x0 - 0.02, x1 + 0.02, y0, y1 + 0.02, z_sill - 0.10 / ES, z_sill)
        # 左右の袖板(出格子の側面。ここが開いていると中が透ける)
        for a, b in ((x0, x0 + 0.05 / ES), (x1 - 0.05 / ES, x1)):
            box(a, b, y0, y1, z_sill, z_head)
        # 縦格子(前面)。⛔ 一枚板で塞がない — 番所は外を見る所
        pitch = 0.105 / ES
        bw_   = 0.032 / ES
        nb = max(2, int(round((x1 - x0 - 0.10 / ES) / pitch)))
        for i in range(nb):
            bc = x0 + 0.05 / ES + (x1 - x0 - 0.10 / ES) * (i + 0.5) / nb
            box(bc - bw_ * 0.5, bc + bw_ * 0.5, y1 - 0.05 / ES, y1, z_sill, z_head)
        # 上枠(楣)と小庇。庇は外へ 0.10m 下がる(勾配を付けないと板が浮いて見える)
        box(x0, x1, y0, y1, z_head, z_head + 0.09 / ES)
        zt = z_head + 0.09 / ES
        box(x0 - 0.09 / ES, x1 + 0.09 / ES, y0, y1 + 0.14 / ES,
            zt, zt + 0.06 / ES, z0o=zt - 0.10 / ES, z1o=zt - 0.04 / ES)
    done()
    print("[nagaya] 出格子番所 %d ケ所: 幅 %.3fm x 丈 %.3fm / 出 %.3fm(躯体内・張出しなし)"
          % (len(centers), hw * 2 * ES, (z_head - z_sill) * ES, BANSHO_OUT))
    return o


def add_kabuki(o, x0, x1, z_head, h, y_front, out=0.07, over=0.25):
    """**門口の頭に冠木(横木)を見せる。** 開口の有効高は変えない —
    冠木の**下端が開口の頭**で、そこから上へ h だけ木を出す。
    ⛔ 白壁のままだと 3.64m の開口が「壁の抜け」にしか見えない(2026-09-04 に実見)。
    ⚠ 既存の小門(`--kabuki` を渡さない)には付かないので出力は変わらない。"""
    box, done = _boxer(o, z_head - 1.0, z_head)
    box(x0 - over / ES, x1 + over / ES, y_front, y_front + out / ES,
        z_head, z_head + h / ES)
    done()
    print("[nagaya] 冠木を出した: 幅 %.3fm x 丈 %.3fm / 壁面より %.3fm 前へ"
          % ((x1 - x0 + 2 * over / ES) * ES, h, out))
    return o


def win_extent(koshi):
    """(半幅, 下段の窓の下端, 出格子の頭, **窓の一番上**) を返す(obj 単位)。

    ⚠ 素の窓は1間に**上下2段**ある。出格子は下段だけを覆うので頭は**上段の窓の下**。
    ⛔ **この「出格子の頭」を無地の帯の下端に流用しない。** 流用すると棟上げで積む
      切片が上段の窓を掠め、**窓の上枠が壁の途中に複製されて黒い横棒**が出る
      (2026-09-04 に実見)。無地の帯は必ず**窓の一番上 → 軒の下端**で測ること。"""
    xs = sorted(set(round(v.co.x, 4) for v in koshi.data.vertices))
    cl = [[xs[0]]]
    for a, b in zip(xs, xs[1:]):
        (cl.append([b]) if b - a > 0.30 else cl[-1].append(b))
    hw = max((c[-1] - c[0]) for c in cl) * 0.5
    zs = sorted(set(round(v.co.z, 4) for v in koshi.data.vertices))
    cz = [[zs[0]]]
    for a, b in zip(zs, zs[1:]):
        (cz.append([b]) if b - a > 0.05 else cz[-1].append(b))
    z0 = cz[0][0]
    z1 = (cz[2][0] - 0.02) if len(cz) >= 3 else cz[-1][-1]
    return hw, z0, z1, cz[-1][-1]


# ---------------------------------------------------------------- 割付を解く
def solve(Lm, cap_w, bay, ncap):
    """L[m] から (bay 本数 k, pier の詰め ε) を出す。ε は obj 単位。

        L/ES = ncap·cap_w + k·bay − ε·(k + ncap/2)

    ncap は妻の数(both=2 / left・right=1 / none=0)。継ぎ目 1 箇所につき pier が ε 詰まり、
    妻を出さない端の切り口は半分(ε/2)ぶん詰まる。|ε| が最小になる k を選ぶ。"""
    Lo = Lm / ES
    best = None
    for k in range(0 if ncap == 2 else 1, 400):
        eps = (ncap * cap_w + k * bay - Lo) / (k + ncap / 2.0)
        if eps < EPS_MIN or eps > EPS_MAX:
            continue
        if best is None or abs(eps) < abs(best[1]):
            best = (k, eps)
    if best is None:
        raise SystemExit("[nagaya] L=%.3fm は ends=%d では作れない(短すぎる)。最小はおよそ %.2fm"
                         % (Lm, ncap, ES * (ncap * cap_w + max(1, 1) * bay
                                            - EPS_MAX * (1 + ncap / 2.0))))
    return best


# ---------------------------------------------------------------- 組む
def build(Lm, ends="both", name=None, floors=1, gate=None,
          ridge=None, doorh=None, bansho=0, kabuki=0.0):
    V.reset()
    gc, mc = read_groups("knagaya01c")
    gl, ml = read_groups("knagaya01l")
    gr, mr = read_groups("knagaya01r")
    V.dedup_materials()

    # 寸法は必ずメッシュから測る(素の x とは符号が逆なので決め打ちしない)
    d0, d1 = xspan(gc["n_dodai"])
    W   = d1 - d0                       # 1棟の継ぎピッチ
    bay = W / 3.0                       # 窓ひとつぶん = 割付の単位
    cwin = win_centers(gc["koshi"])[1]  # `c` の真ん中の窓
    # 妻部材: 破風(n_kera_top)がある側が妻。`l` は +x 側、`r` は −x 側(読み込みで X が反転する)
    lk0, lk1 = xspan(gl["n_kera_top"]);  l_gab = lk1
    rk0, rk1 = xspan(gr["n_kera_top"]);  r_gab = rk0
    lwin = max(win_centers(gl["koshi"]))   # 妻に一番近い窓
    rwin = min(win_centers(gr["koshi"]))
    cap_w = (l_gab - lwin) + bay / 2.0     # 妻の外端から継ぎ目までの長さ(ε=0のとき)
    # ⚠ **帯の高さは join の前に測る。** V.join は素のオブジェクトを消費するので、
    #   後から gc["namako"] を触ると ReferenceError になる(2026-08-29 に踏んだ)。
    z_namako_top = zspan(gc["namako"])[1]
    # ⚠ 積む帯の天端は**屋根の下端**にする。壁の天端(n_wall)で切ると軒瓦・垂木まで
    #   複製されて、中途半端な庇と、妻で行き場を失った瓦の破片が出る(2026-08-29 に実見)。
    z_roof_bot = min(zspan(gc[k])[0] for k in ("n_taruki", "n_noki", "n_hira", "n_maru")
                     if k in gc)
    # 出格子・棟上げに要る素の実測(join が素を食う前に採る)
    win_hw, z_win0, z_win1, z_win_top = win_extent(gc["koshi"])
    y_wall_front = max(v.co.y for v in gc["n_wall"].data.vertices)   # 壁の外面(素では +Y)
    blank_h = z_roof_bot - z_win_top     # **窓の一番上** 〜 軒の下端 = 無地の白壁の帯
    # 妻の出 = 破風の外端が土台の小口より外へ出る量(棟梁が呼び寸法を組むのに要る)
    tsuma_out = l_gab - max(v.co.x for v in gl["n_dodai"].data.vertices)
    print("[nagaya] 素の実測: 棟 %.5f (%.4fm) / bay %.5f (%.4fm) / 妻 %.5f (%.4fm)"
          % (W, W * ES, bay, bay * ES, cap_w, cap_w * ES))
    print("[nagaya] 妻の出(破風の外端 − 土台の小口)= %.4f (%.3fm) / 片側。"
          "呼び寸法 L は**破風まで含む全幅**" % (tsuma_out, tsuma_out * ES))

    ncap = {"both": 2, "left": 1, "right": 1, "none": 0}[ends]
    k, eps = solve(Lm, cap_w, bay, ncap)
    bw = bay - eps
    pier = 0.845 - eps
    print("[nagaya] L=%.3fm → bay %d 本 / pier の詰め ε=%+.4f (%.3fm) → 無地の壁 %.3fm"
          % (Lm, k, eps, eps * ES, pier * ES))
    if pier < 0.30:
        print("[nagaya] ⚠ 無地の壁が %.2fm しか残らない" % (pier * ES))

    pieces = []
    # --- bay(中部材から切り出す): 中央の窓を挟んで対称に
    b0 = cwin - bay / 2.0 + eps / 2.0
    b1 = cwin + bay / 2.0 - eps / 2.0
    bay_src = V.join(mc, "bay_src")
    slab(bay_src, b0, b1)
    for i in range(k):
        c = dup(bay_src, "bay%02d" % i)
        shift_x(c, i * bw - b0)
        pieces.append(c)
    bpy.data.objects.remove(bay_src, do_unlink=True)

    # --- 妻(左 = `r` の妻を −x 側に / 右 = `l` の妻を +x 側に)
    cap_r = V.join(mr, "capL")          # 妻が −x 側にある部材 → 走りの左端
    cap_l = V.join(ml, "capR")          # 妻が +x 側にある部材 → 走りの右端
    xR = rwin + bay / 2.0 - eps / 2.0   # `r` の内側の切断面
    xL = lwin - bay / 2.0 + eps / 2.0   # `l` の内側の切断面
    if ends in ("both", "left"):
        bisect_keep(cap_r, xR, False)   # 妻側(x ≤ xR)を残す
        shift_x(cap_r, -xR)
        pieces.append(cap_r)
    else:
        bpy.data.objects.remove(cap_r, do_unlink=True)
    if ends in ("both", "right"):
        bisect_keep(cap_l, xL, True)
        shift_x(cap_l, k * bw - xL)
        pieces.append(cap_l)
    else:
        bpy.data.objects.remove(cap_l, do_unlink=True)

    o = V.join(pieces, "nagaya")
    # 継ぎ目の頂点を溶かす(隣り合う切り口は平行移動で一致している)
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
    bm.to_mesh(me); bm.free(); me.update()

    # --- 階を積む(案A)。帯の高さは**素の実測**から取る
    if floors > 1:
        print("[nagaya] 素の帯: 海鼠の天端 %.4f (%.3fm) / 屋根の下端 %.4f (%.3fm)"
              % (z_namako_top, z_namako_top * ES, z_roof_bot, z_roof_bot * ES))
        o = add_floor(o, z_namako_top, z_roof_bot, floors)
    dzf = z_roof_bot - z_namako_top
    z_cuts = [z_roof_bot + dzf * i for i in range(floors)]   # 下の階から順に各階の天端

    # --- 棟の目標高さ(土台の底から m)。⛔ 瓦の勾配は触らず軒高だけで稼ぐ
    if ridge is not None:
        me = o.data
        zs0 = [v.co.z for v in me.vertices]
        h_now = max(zs0) - min(zs0)
        extra = ridge / ES - h_now
        if extra < -1e-4:
            raise SystemExit("[nagaya] 棟 %.3fm は既定の %.3fm より低い — 軒では下げられない"
                             % (ridge, h_now * ES))
        if extra > 1e-4:
            print("[nagaya] 棟 %.3fm へ(いま %.3fm)/ 無地の帯は %.3fm ある"
                  % (ridge, h_now * ES, blank_h * ES))
            o = raise_eaves(o, z_cuts, blank_h, extra)
            me = o.data

    # --- 長屋門の門口(ユーザー裁定 2026-08-30)。**階を積み、棟を上げた後**に抜く。
    #   ⛔ 2026-09-04 まで積む前に抜いていた。`add_floor` は白壁の帯
    #   [海鼠の天端 → 軒の下端] を丸ごと複製するので、**門口の空洞と板戸まで二階へ複製され**、
    #   二階の壁の同じ位置に「もう一枚の門扉」が現れていた(岡部の表門の検証レンダで実見)。
    #   ⭕ 積んでから抜けば二階の壁は無傷のまま、門口は一階だけに開く。
    #   ⚠ 平屋(floors=1)では順序を変えても結果は同じなので、既存の小門の出力は変わらない。
    if gate is not None:
        # gc_m は **出来上がりの部材のローカル +X の左端からの距離**[m]。
        # ⚠ 書き出す前に Z まわりに 180° 回すので **obj 空間では X が反転する** —
        #   obj の右端から測って抜かないと、門口が反対の端に出る(2026-08-30 に踏んだ)。
        gc_m, gw_m, gh_m = gate                    # 中心[m](出来上がりの左端から) / 幅[m] / 有効高[m]
        xs_all = [v.co.x for v in o.data.vertices]
        cx = max(xs_all) - gc_m / ES
        # ⚠ 高さは**土台の底からの高さ**。obj 空間の z は 0 が底ではない
        #   (底は負)。絶対 z として渡すと切る面が高すぎて**屋根まで抜ける**
        #   (2026-08-30 に踏んだ — 門口が全高の切り欠きになった)
        z_bottom = min(v.co.z for v in o.data.vertices)
        gx0, gx1 = cx - (gw_m / ES) * 0.5, cx + (gw_m / ES) * 0.5
        gz_top = z_bottom + gh_m / ES
        carve_gate(o, gx0, gx1, gz_top)
        # 扉は**長屋に作り付ける**(ユーザー裁定2-A 2026-08-31)。指図 komon[].leaf の
        # 「両開きの板戸 h=2.8」。⛔ Unity 側で在庫の門を開口へ落とし込まない
        hang_doors(o, gx0, gx1, z_bottom, gz_top,
                   DOOR_H if doorh is None else doorh)
        if kabuki:
            add_kabuki(o, gx0, gx1, gz_top, kabuki, y_wall_front)

    # --- 両端の出格子番所(長屋門)。窓は x = (j+0.5)·bw に並ぶ(j = −1 … k)
    if bansho:
        bwid = bay - eps
        cen = [-bwid * 0.5, (k + 0.5) * bwid]
        add_degoshi(o, cen[:bansho] if bansho < 2 else cen,
                    y_wall_front, z_win0, z_win1, win_hw)
        me = o.data

    # --- 向き: 表(素では +Y)を Blender −Y へ。**回転**で行う(鏡映は巻きが裏返る)
    o.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    # --- 江戸間の実寸(m)へ
    o.data.transform(Matrix.Scale(ES, 4))
    o.data.update()

    # --- ピボット = 走りの中心 / 土台の底 / 壁の外面
    xs = [v.co.x for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    px = (min(xs) + max(xs)) * 0.5
    pz = min(zs)                                   # 土台の底
    py = wall_face_y(o)                            # 壁の外面(= 走りに平行な最も外の大面)
    for v in me.vertices:
        v.co.x -= px; v.co.y -= py; v.co.z -= pz
    me.update()

    ys = [v.co.y for v in me.vertices]
    xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    L_real = max(xs) - min(xs)
    print("[nagaya] 出来上がり(m) W %.3f × H %.3f × D %.3f   軒の出 %.3f / 躯体 %.3f"
          % (L_real, max(zs) - min(zs), max(ys) - min(ys), -min(ys), max(ys)))
    print("[nagaya] 目標 %.3fm との差 %+.4fm  面=%d" % (Lm, L_real - Lm, len(me.polygons)))

    nm = name or ("Nagaya_Omote_" + fmt(Lm)
                  + ("" if gate is None else "_mon%s" % fmt(gate[0]))
                  + ("" if floors < 2 else "_%df" % floors)
                  + ("" if ends == "both" else "_" + ends))
    o.name = nm; o.data.name = nm
    path = os.path.join(OUT, nm + ".fbx")
    V.export_fbx([o], path)
    print("[nagaya] wrote %s" % path)
    return o, path, L_real


def wall_face_y(o):
    """壁の外面の y。表側(y の小さいほう)で、走りに平行な大きな面が集まる位置を採る。
    ⚠ 軒(y がさらに外へ出る)を掴まないよう、**面積で重み付けした最頻値**で取る。"""
    from collections import defaultdict
    acc = defaultdict(float)
    for p in o.data.polygons:
        if abs(p.normal.y) < 0.9:
            continue
        y = o.data.vertices[o.data.loops[p.loop_start].vertex_index].co.y
        acc[round(y, 3)] += p.area
    if not acc:
        return min(v.co.y for v in o.data.vertices)
    ys = sorted(acc.items(), key=lambda kv: -kv[1])
    # 表側に面する候補のうち、面積が最大のもの
    front = [y for y, a in ys if a > ys[0][1] * 0.15]
    return min(front)


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


# ---------------------------------------------------------------- テクスチャ / レンダ
def hook():
    for m in bpy.data.materials:
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        b.inputs['Alpha'].default_value = 1.0        # FBX の TransparencyFactor 対策
        b.inputs['Roughness'].default_value = 0.8
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(os.path.join(SRC, "knagaya.jpg"), check_existing=True)
        img.location = (-600, 300)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])


def shots(o, tag, gate=None, bansho=0):
    hook()
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    L = (mx - mn).x
    if gate is not None:
        # ⑤ 門口の寄り(表・裏)。**縁の小口が透けていないか**をここで見る
        gx = mn.x + gate[0]
        V.studio((gx, c.y - 10, mn.z + 2.4), (gx, c.y, mn.z + 2.4), ortho_scale=9.0, res=(1500, 1100))
        V.render(os.path.join(SHOT, "nagaya_%s_mon.png" % tag))
        V.studio((gx - 5.0, c.y - 7.0, mn.z + 2.0), (gx + 1.0, c.y + 2.0, mn.z + 1.8), res=(1500, 1100))
        V.render(os.path.join(SHOT, "nagaya_%s_mon3d.png" % tag))
    os.makedirs(SHOT, exist_ok=True)
    # ① 正面の立面(全長)。⚠ 高さが入る画角にする — 二階・棟上げの部材は 700px では
    #    上下が切れて「軒より上が見えない」レンダになる(2026-09-04 に踏んだ)
    H = (mx - mn).z
    wpx, hpx = 1900, 1900 * (H * 1.14) / (L * 1.08)
    if hpx > 1200:                      # 短くて背の高い部材は**幅を縮める** —
        wpx, hpx = wpx * 1200 / hpx, 1200   # 縦を頭打ちにすると棟が切れる
    # ⚠ `ortho_scale` は**画像の長いほうの辺**に効く。縦長になったら縦の実寸を渡す —
    #   横の実寸を渡すと縦横とも足りず、6m級の短い部材で土台も棟も切れる(2026-09-04)
    V.studio((c.x, c.y - L, c.z), (c.x, c.y, c.z),
             ortho_scale=(L * 1.08 if wpx >= hpx else H * 1.14),
             res=(int(wpx), int(hpx)))
    V.render(os.path.join(SHOT, "nagaya_%s_elev.png" % tag))
    # ② 継ぎ目の寄り(左の妻から3本目の継ぎ目あたり)
    xj = mn.x + min(L * 0.5, 9.0)
    V.studio((xj, c.y - 9, mn.z + 2.2), (xj, c.y, mn.z + 2.2), ortho_scale=7.0, res=(1500, 1000))
    V.render(os.path.join(SHOT, "nagaya_%s_joint.png" % tag))
    # ③ 妻(端部)を斜め前から。小口が透けていないかを見る
    V.studio((mn.x - 9.0, c.y - 9.0, mn.z + 5.5), (mn.x + 2.0, c.y + 1.5, mn.z + 2.2), res=(1500, 1000))
    V.render(os.path.join(SHOT, "nagaya_%s_tsuma.png" % tag))
    # ③' 妻を裏(敷地の内側)から。裏の壁と妻の納まりを見る
    V.studio((mn.x - 8.0, c.y + 11.0, mn.z + 5.0), (mn.x + 3.0, c.y + 1.5, mn.z + 2.2), res=(1500, 1000))
    V.render(os.path.join(SHOT, "nagaya_%s_ura.png" % tag))
    if bansho:
        # ⑥ 出格子番所の寄り(左端)。格子が透けているか・庇が浮いていないかを見る
        V.studio((mn.x + 1.2, c.y - 6.0, mn.z + 2.6), (mn.x + 1.2, c.y, mn.z + 2.2),
                 ortho_scale=4.2, res=(1300, 1200))
        V.render(os.path.join(SHOT, "nagaya_%s_bansho.png" % tag))
        V.studio((mn.x - 3.4, c.y - 5.6, mn.z + 3.4), (mn.x + 1.4, c.y + 0.5, mn.z + 2.0),
                 res=(1400, 1100))
        V.render(os.path.join(SHOT, "nagaya_%s_bansho3d.png" % tag))
    # ④ 街路から見た斜め(人の目の高さ)
    V.studio((mn.x - 6.0, c.y - 16.0, 1.7), (c.x, c.y, 2.4), res=(1900, 900))
    V.render(os.path.join(SHOT, "nagaya_%s_street.png" % tag))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    ends = "both"
    if "--ends" in argv:
        ends = argv[argv.index("--ends") + 1]
    name = argv[argv.index("--name") + 1] if "--name" in argv else None
    # --gate <中心m(左端から)> <幅m> <有効高m> — 長屋門の門口を抜く
    gate = None
    if "--gate" in argv:
        i = argv.index("--gate")
        gate = (float(argv[i + 1]), float(argv[i + 2]), float(argv[i + 3]))
    # --ridge <m>   棟天端の目標高さ(土台の底 = 敷居から)。軒高だけで稼ぐ
    # --doorh <m>   板戸の丈(既定 DOOR_H=2.8)。楣まで通すなら門口の有効高と同じ値を渡す
    # --bansho <n>  両端に出格子番所を付ける(長屋門。0=付けない)
    ridge  = float(argv[argv.index("--ridge") + 1])  if "--ridge"  in argv else None
    doorh  = float(argv[argv.index("--doorh") + 1])  if "--doorh"  in argv else None
    bansho = int(argv[argv.index("--bansho") + 1])   if "--bansho" in argv else 0
    # --kabuki <丈m>  門口の頭に冠木(横木)を見せる。0 = 出さない(既存の小門は従来どおり)
    kabuki = float(argv[argv.index("--kabuki") + 1]) if "--kabuki" in argv else 0.0
    skip = set()
    for f in ("--ends", "--name", "--floors", "--ridge", "--doorh", "--bansho",
              "--kabuki"):
        if f in argv:
            skip.add(argv.index(f)); skip.add(argv.index(f) + 1)
    if "--gate" in argv:
        i = argv.index("--gate")
        skip.update((i, i + 1, i + 2, i + 3))
    lens = [float(a) for i, a in enumerate(argv)
            if i not in skip and not a.startswith("--")]
    if not lens:
        lens = [28.5]
    floors = int(argv[argv.index("--floors") + 1]) if "--floors" in argv else 1
    for Lm in lens:
        o, path, L_real = build(Lm, ends=ends, name=name, floors=floors, gate=gate,
                                ridge=ridge, doorh=doorh, bansho=bansho,
                                kabuki=kabuki)
        if do_render:
            shots(o, fmt(Lm) + ("" if gate is None else "_mon%s" % fmt(gate[0]))
                  + ("" if floors < 2 else "_%df" % floors)
                  + ("" if ends == "both" else "_" + ends), gate=gate, bansho=bansho)


main()
