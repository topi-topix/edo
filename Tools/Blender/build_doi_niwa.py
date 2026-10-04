"""**土井大隅守上屋敷の庭の部材(EDO-0533・庭方の設計 2026-10-04)。**

    blender --background --python Tools/Blender/build_doi_niwa.py -- all --render
    blender --background --python Tools/Blender/build_doi_niwa.py -- ishibashi dobashi --render
    blender --background --python Tools/Blender/build_doi_niwa.py -- nobedan --L 3.18 --render
    blender --background --python Tools/Blender/build_doi_niwa.py -- dan chozubachi --render

【寸法の正典は `docs/Sashizu/doi_sashizu.json`】⛔ ここで値を発明しない。
  ・石橋     `gardens[G_Sensui].hashi[Hashi_Ishi]`   L3.4 × W0.75 × T0.24(径間 2.79)
  ・土橋     `gardens[G_Sensui].hashi[Hashi_Do]`     L3.4 × W1.2・反り 0.15・丸太桁 φ0.18 × 3
  ・丸太段   `gardens[G_Sensui].dan`                 蹴上 0.12〜0.15・幅 0.9(wood_log_05 を切る+留め杭2本)
  ・延段     `gardens[G_Okuniwa].nobedan`            w0.6・a→b の長さ・切石と玉石の寄せ
  ・手水鉢   `gardens[G_Okuniwa].chozu`              自然石の鉢 φ0.55 × h0.35 + 台石

【石は一系統】`gardenFields.ishiFamily` のとおり **`M_photoscanned_rocks_01`**(Own.Ishigumi /
  Tobiishi / DoiKutsunugi と同じ NatureManufacture の写真計測の岩)。
  ⛔ `M_FJG_Rock_001`(Own.Tateishi / Hiraishi / Ishibashi の系)を混ぜない。
  ⇒ 切石(橋・延段の切石)は箱を面取りして、岩アトラスの**無地の石肌**(`ON.ROCK_PLAIN_UV`)へ
    平面投影で貼る。自然石(玉石・鉢・台石)は**在庫の実岩を切って**使う(規則1)。
【木】`M_Wood_fence`(NatureManufacture の丸太 `wood_log_0X` を `build_maruta.log_piece` で切る)。
【土・芝】`M_FJG_Terrain_Ground_Soil_01` / `M_FJG_Terrain_Ground_Grass_01`(名だけ。地形の
  スプラットと同じ肌。畝 `Own.HatakeUne` と同じ借り先)。

【向きとピボット(Unity 座標)】長手 = X、高さ = Y、見え面/下手 = +Z。Blender は Z-up で
  Blender (x, y, z) → Unity (−x, z, −y)。各部材の docstring がピボットを明示する。
  remap は `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`(Models/Niwa と、岩・丸太・FJG の
  三つの借り先を全部見ているのはこのメニューだけ)。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_maruta as BM
import build_okabe_niwa as ON

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa"))
SHOT = os.path.join(V.REPO, "Screenshots")
ROCK = ON.ROCK_MAT
PLAIN = ON.ROCK_PLAIN_UV
# 長い一枚石(橋)用の帯。PLAIN と同じ灰色の岩の**中ほど**だけ(割れ目の線が入らない帯)。
#   ⚠ PLAIN を 3.4m に引き伸ばすと割れ目が「目地」に読め、一枚石が石を継いだ箱に見えた(1回目のレンダ)
SLAB_UV = (0.130, 0.575, 0.300, 0.665)
SOIL, GRASS = "M_FJG_Terrain_Ground_Soil_01", "M_FJG_Terrain_Ground_Grass_01"
FJG = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden", "Textures", "Terrain")
TEX = {SOIL: os.path.join(FJG, "Ground_Soil_01", "T_FJG_Ground_Soil_01_"),
       GRASS: os.path.join(FJG, "Ground_Grass_01", "T_FJG_Ground_Grass_01_")}

# ---- 指図の値(doi_sashizu.json)。⚠ 数字を変えるなら json が先 ----
ISHI_L, ISHI_W, ISHI_T = 3.4, 0.75, 0.24          # hashi[Hashi_Ishi]
DO_L, DO_W, DO_SORI, DO_SPAN = 3.4, 1.2, 0.15, 2.68  # hashi[Hashi_Do]
DO_KETA_D = 0.18                                   # 丸太桁 φ0.18 × 3(asset 欄)
DAN_W = 0.9                                        # dan.asset / enroShu.w
NOBE_W = 0.6                                       # nobedan.w
NOBE_A, NOBE_B = (-2.05, 65.45), (-4.85, 63.95)    # nobedan.a/b ⇒ L = 3.18
BOWL_D, BOWL_H = 0.55, 0.35                        # chozu.asset「鉢 φ0.55×h0.35」

# ---- 部材の既定値(指図に無い。⚠ 確度 U・部材方の判断) ----
DO_SOIL_T = 0.15     # 桁の天端から土の天端まで(端で)
DO_CROWN = 0.03      # 土の天端の幅方向のむくり(水を縁へ切る)
DO_SHIBA = 0.12      # 縁の芝の帯の幅
DAN_D = 0.13         # 丸太段の丸太の径 — 蹴上 0.12〜0.15 の中を採る(在庫 φ0.11 を半径方向に伸ばす)
DAN_KUI_D, DAN_KUI_L = 0.06, 0.45
NOBE_T = 0.10        # 延段の石の厚み
NOBE_KERB = 0.11     # 玉石の区画の縁に回す切石の幅
JOINT = 0.015        # 目地


def mat(name):
    m = bpy.data.materials.get(name)
    return m if m else bpy.data.materials.new(name)


def _obj(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free(); me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    for m in mats:
        me.materials.append(m)
    return o


def _volume(me):
    vol = 0.0
    for p in me.polygons:
        vs = [me.vertices[k].co for k in p.vertices]
        for t in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[t].cross(vs[t + 1])) / 6.0
    return vol


def _outward(o):
    """閉じた部品の外向きを符号付き体積で保証する(recalc は裏返すことがある・memory)。"""
    if _volume(o.data) < 0.0:
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(o.data); bm.free(); o.data.update()


def planar_uv(o, rect, d, rng, faces=None):
    """面の法線の主軸で平面投影し、矩形 `rect` の中へ収める。⛔ 一点貼りにしない(規約3)。
    `d` = UV/m。部品の最大寸法が矩形に入らなければ d を下げる(⛔ 折り返さない ── 面の中で
    UV が往復すると線形補間が嘘をつく)。矩形の中の位置は乱数でずらす(同じ斑の繰り返しを避ける)。"""
    me = o.data
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    u0, v0, u1, v1 = rect
    Wr, Hr = u1 - u0, v1 - v0
    co = [v.co for v in me.vertices]
    mn = [min(c[i] for c in co) for i in range(3)]
    ext = [max(c[i] for c in co) - mn[i] for i in range(3)]
    pairs = {2: (0, 1), 1: (0, 2), 0: (1, 2)}
    used = set()
    for f in me.polygons:
        if faces is None or f.index in faces:
            used.add(pairs[max(range(3), key=lambda k: abs(f.normal[k]))])
    su = max((ext[a] for a, b in used), default=1.0)
    sv = max((ext[b] for a, b in used), default=1.0)
    # 軸ごとに収める(u に長手・v に短手が来る面は、長手だけで密度が決まる)
    d = min(d, 0.95 * Wr / max(su, 1e-6), 0.95 * Hr / max(sv, 1e-6))
    ou = u0 + rng.uniform(0.0, max(0.0, Wr - su * d))
    ov = v0 + rng.uniform(0.0, max(0.0, Hr - sv * d))
    sel = set(faces) if faces is not None else None
    for f in me.polygons:
        if sel is not None and f.index not in sel:
            continue
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        a, b = {2: (0, 1), 1: (0, 2), 0: (1, 2)}[ax]
        for li in f.loop_indices:
            c = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (ou + (c[a] - mn[a]) * d, ov + (c[b] - mn[b]) * d)
    return d


def kiriishi(name, sx, sy, sz, bev, rng, top=0.0, cx=0.0, cy=0.0, d=0.11, rect=PLAIN):
    """**切石1枚**(箱 + 全辺の面取り)。天端 = `top`、平面の芯 = (cx, cy)。Blender 座標。
    材 = 写真計測の岩の無地の肌(⛔ M_FJG_Rock_001 ではない)。"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((cx + v.co.x * sx, cy + v.co.y * sy, top - sz * 0.5 + v.co.z * sz))
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, offset_type='OFFSET',
                    segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, [mat(ROCK)])
    _outward(o)
    planar_uv(o, rect, d, rng)
    return o


def _finish(objs, name):
    """⛔⛔ join の前に UV の層を **1枚・同じ名前**へ揃える。在庫の丸太・岩は `UVmap_0` と
    `LightMapUV` を持ち、自作の面は `UVMap` しか持たない。そのまま join すると層が名前ごとに
    別れ、**自作の面の第1層が (0,0)** になって土も切石も無地の一色で写る(Unity も第1層を読む)。"""
    for o in objs:
        uls = o.data.uv_layers
        if not len(uls):
            continue
        keep = uls.active if uls.active is not None else uls[0]
        for ul in [u for u in uls if u.name != keep.name]:
            uls.remove(ul)
        uls[0].name = "UVMap"
    V.dedup_materials()
    o = V.join(objs, name)
    o.name = o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


# ================================================================ 1. 石橋
def ishibashi():
    """**切石の一枚橋** 3.40(X) × 0.24(Y) × 0.75(Z)(`hashi[Hashi_Ishi]`・反りなし)。
    径間 2.79 に対し両端 0.30 ずつ橋台石へ掛かる。
    ピボット = **版の平面の芯・天端**(石は Y −0.24..0)⇒ `position.y = topY`(26.4)を直に。
    長手 X を a→b へ向ける(yaw は a,b から)。版の下面は橋台石の天端に接する(硬い・abut 欄)。
    ⛔ `Own.Ishibashi()`(2.2m・M_FJG_Rock_001)とは別物 ── 石の系が違う。"""
    rng = random.Random(53301)
    o = kiriishi("Doi_Ishibashi", ISHI_L, ISHI_W, ISHI_T, 0.018, rng, rect=SLAB_UV)
    name = "Doi_Ishibashi_%.2fx%.2f" % (ISHI_L, ISHI_W)
    return _finish([o], name), name


# ================================================================ 2. 土橋
def _soil_uv(m, x, s, kind):
    """土 = FJG Soil の茶の矩形(8m 周期・u を芯で折り返す)/ 芝 = FJG Grass(4m 周期)。"""
    if kind == SOIL:
        # ⚠ 苔と松葉の無い茶の矩形(u 0.008..0.122 × v 0.900..0.995・畝と同じ)に収めるため 16m 周期
        #   (8m のままだと矩形をはみ出して苔の緑の斑が土の上に出た ── 2回目のレンダ)
        return (0.008 + abs(x) / 16.0, 0.900 + s / 16.0)
    return (abs(x) / 4.0, s / 4.0)


def dobashi():
    """**土橋** L3.40(X) × W1.20(Z)(`hashi[Hashi_Do]`)。丸太桁 φ0.18 × 3 の上に土 0.15 を載せ、
    幅方向の縁 0.12 と側面を芝で包む(縁に芝の見立て)。桁は反り 0.15 なりに撓めてある
    (径間の中央で天端が +0.15)。両端の岸(径間 2.68 の外)に **台木の丸太 + 土留めの杭5本**。

    ピボット = **平面の芯・橋の端の土の天端**(`endTopY` 26.38 を直に)。中央は +0.15+むくり0.03。
    ⚠ 下へは杭が −1.1 まで垂れる(岸の法に埋まる・汀の内側に立つ)。
    長手 X を a→b へ向ける。土の端の小口(X=±1.70)は岸の地盤へ埋まる前提。"""
    rng = random.Random(53302)
    half, hw, T = DO_L / 2.0, DO_W / 2.0, DO_SOIL_T

    def h(x):
        t = min(abs(x), half) / half
        return DO_SORI * (1.0 - t * t)

    objs = []
    # ---- 丸太桁 3本(長さ 3.10 = 径間 2.68 + 掛かり 0.21×2)
    gL = 3.10
    for k, (y, stem, frm) in enumerate(((-0.40, "wood_log_02", 0.03), (0.0, "wood_log_01", 0.0),
                                        (0.40, "wood_log_02", 0.0))):
        g = BM.log_piece(stem, gL, DO_KETA_D, "keta%d" % k, frm=frm)
        for v in g.data.vertices:
            v.co.y += y
            v.co.z += -T - DO_KETA_D * 0.5 + h(v.co.x)
        g.data.update()
        objs.append(g)
    # ---- 岸の台木(桁を受ける横木)と土留めの杭
    for s in (-1, 1):
        xs = s * (DO_SPAN / 2.0 + 0.10)
        zb = -T - DO_KETA_D + h(xs)                  # 桁の下端
        sill = BM.log_piece("wood_log_05", DO_W + 0.06, 0.12, "dai%d" % s, frm=0.05)
        sill.data.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))
        sill.data.transform(Matrix.Translation((xs, 0.0, zb - 0.06)))
        sill.data.update()
        objs.append(sill)
        for j, y in enumerate((-0.48, -0.24, 0.0, 0.24, 0.48)):
            kui = BM.upright(BM.log_piece("wood_log_04", 0.60, 0.08, "kui%d%d" % (s, j),
                                          frm=0.1 + 0.25 * j), top_at_zero=True)
            kui.data.transform(Matrix.Translation((xs - s * 0.10, y, zb - 0.02 - rng.uniform(0, 0.03))))
            kui.data.update()
            objs.append(kui)
    # ---- 土(芝の縁つき)。断面 = 下左 → 側 → 天端(芝帯・土・芝帯)→ 側 → 下右
    # 肩は丸めて芝で包む(⛔ 角の立った箱にしない ── 1回目のレンダで「土の板」に見えた)
    P = [(-hw + 0.03, -T), (-hw, -T * 0.45), (-hw + 0.025, -0.012), (-hw + 0.07, None),
         (-hw + DO_SHIBA + 0.02, None), (-0.25, None), (0.0, None), (0.25, None),
         (hw - DO_SHIBA - 0.02, None), (hw - 0.07, None), (hw - 0.025, -0.012),
         (hw, -T * 0.45), (hw - 0.03, -T)]
    P = [(y, (DO_CROWN * (1.0 - (y / hw) ** 2)) if z is None else z) for y, z in P]
    kinds = [GRASS] * 4 + [SOIL] * 4 + [GRASS] * 4 + [SOIL]             # 区間 j = P[j]→P[j+1]
    arc = [0.0]
    for j in range(1, len(P)):
        arc.append(arc[-1] + math.hypot(P[j][0] - P[j - 1][0], P[j][1] - P[j - 1][1]))
    arc.append(arc[-1] + 2 * hw)                                         # 底(閉じる区間)
    NX = 24
    xs_ = [-half + DO_L * i / NX for i in range(NX + 1)]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = [[bm.verts.new((x, y, z + h(x))) for (y, z) in P] for x in xs_]
    np_ = len(P)
    mats = [mat(SOIL), mat(GRASS)]
    for i in range(NX):
        for j in range(np_):
            j2 = (j + 1) % np_
            a, b, c, d = rows[i][j], rows[i + 1][j], rows[i + 1][j2], rows[i][j2]
            f = bm.faces.new((a, b, c, d))
            f.material_index = 0 if kinds[j] == SOIL else 1
            for lp in f.loops:
                ii = 0 if lp.vert in (a, d) else 1
                s_ = arc[j] if lp.vert in (a, b) else arc[j + 1]
                lp[uvl].uv = _soil_uv(None, xs_[i + ii], s_, kinds[j])
    for i, sgn in ((0, -1), (NX, 1)):
        vs = rows[i][:]
        f = bm.faces.new(vs if sgn > 0 else list(reversed(vs)))
        f.material_index = 0
        for lp in f.loops:
            co = lp.vert.co
            lp[uvl].uv = (0.008 + (co.y + hw) / 16.0, 0.900 + (co.z + T) / 16.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    soil = _obj("tsuchi", bm, mats)
    _outward(soil)
    for p in soil.data.polygons:
        p.use_smooth = False
    objs.append(soil)
    name = "Doi_Dobashi_%.2fx%.2f" % (DO_L, DO_W)
    return _finish(objs, name), name


# ================================================================ 3. 丸太段
def marutadan():
    """**丸太の土留め段 1段**(`gardens[G_Sensui].dan`)。丸太 φ0.13 × 0.90 を X に寝かせ、
    下手(Unity **+Z**)に留め杭 φ0.06 × 0.45 を2本打つ。
    ピボット = **丸太の芯の平面・丸太の天端** = 上段の踏面の高さ。⇒ `position.y = 上段の踏面`。
    蹴上は据える側が 0.12〜0.15 で割る(丸太の下端 −0.13 が下段の踏面とほぼ揃う)。
    走り(上り)は Unity −Z。踏面 ≥0.60 は駒の間隔で取る(駒には踏面の土を含めない)。"""
    o = BM.log_piece("wood_log_05", DAN_W, DAN_D, "dan", frm=0.20)
    o.data.transform(Matrix.Translation((0.0, 0.0, -DAN_D * 0.5)))
    o.data.update()
    objs = [o]
    for k, x in enumerate((-0.32, 0.31)):
        kui = BM.upright(BM.log_piece("wood_log_06", DAN_KUI_L, DAN_KUI_D, "kui%d" % k,
                                      frm=0.05 + 0.2 * k), top_at_zero=True)
        # Blender −Y = Unity +Z(下手)。杭の頭は丸太の天端より 0.015 下
        kui.data.transform(Matrix.Translation((x, -(DAN_D * 0.5 + DAN_KUI_D * 0.5 + 0.003), -0.015)))
        kui.data.update()
        objs.append(kui)
    name = "Doi_MarutaDan_%.2f" % DAN_W
    return _finish(objs, name), name


# ================================================================ 4. 延段
_TAMA = {}


def _tama_proto(stem):
    """玉石の原型。在庫の小岩を LOD2(軽い方)で読み、底を切り落とす(見えるのは頭だけ)。"""
    if stem in _TAMA:
        return _TAMA[stem]
    path = os.path.join(ON.NMR, stem + ".FBX")
    objs = VM.import_fbx_abs(path, keep=lambda n: n.endswith("LOD1"))
    if not objs:
        objs = VM.import_fbx_abs(path, keep=lambda n: "LOD1" not in n and "LOD2" not in n)
    o = V.join(objs, "proto_" + stem)
    # ⚠ 小岩は板状に**立って**いる個体がある(平面で見ると細い欠片になった ── 2回目のレンダ)。
    #   ⭕ いちばん薄い軸を鉛直へ寝かせる(玉石は寝て据わる)
    mn, mx = BM.bounds([o])
    dd = [mx.x - mn.x, mx.y - mn.y, mx.z - mn.z]
    k = dd.index(min(dd))
    if k == 0:
        o.data.transform(Matrix.Rotation(math.radians(90), 4, 'Y'))
    elif k == 1:
        o.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
    o.data.update()
    ON._center_xy(o, z_at='bottom')
    o.hide_render = True
    _TAMA[stem] = o
    return o


def _tama(name, proto, size, top, x, y, yaw):
    me = proto.data.copy()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    mn, mx = BM.bounds([proto])
    L0 = max(mx.x - mn.x, mx.y - mn.y)
    k = size / L0
    # ⚠ 天端だけ合わせると頭の小さな断面しか床(−0.02)の上に出ず、玉石が「散らばった欠片」に
    #   見えた(1回目のレンダ)。⭕ 丈を 0.065 に揃え、**胴の芯を −0.035** に置く ⇒ 床の上に出る
    #   断面は最大幅の約 9 割・頭は `top`(−0.003 前後)。
    me.transform(Matrix.Diagonal((k, k, 1.0, 1.0)))
    zs = [v.co.z for v in me.vertices]
    kz = 0.065 / max(max(zs) - min(zs), 1e-6)
    me.transform(Matrix.Diagonal((1.0, 1.0, kz, 1.0)))
    me.transform(Matrix.Rotation(yaw, 4, 'Z'))
    zs = [v.co.z for v in me.vertices]
    me.transform(Matrix.Translation((x, y, top - max(zs))))
    # 床(-0.06)より下を落とす。蓋はしない(土の床に隠れる)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector((0, 0, -0.06)), plane_no=Vector((0, 0, 1)),
                           clear_inner=True)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    for p in me.polygons:
        p.use_smooth = True
    return o


def nobedan(L):
    """**延段**(切石と玉石の寄せ・幅 0.60)を長さ `L` で一体に焼く(`gardens[G_Okuniwa].nobedan`)。
    ⭕ 両端は**幅いっぱいの切石**で始め・止める(延段の端の作法)。間は「幅いっぱいの切石」
    「幅を二つに割った切石の対」「縁に細い切石を回した玉石の区画」を乱数で寄せる。
    目地 0.015 の下は土の床(天端 −0.02)。
    ピボット = **平面の芯・切石の天端**(石は Y −0.10..0)⇒ `position.y = 地盤 + 0.03` 程度。
    長手 X を a→b へ向ける。⛔ X を伸縮して長さを合わせない(石が伸びる)── 長さごとに焼く。"""
    rng = random.Random(int(round(L * 1000)) + 5330)
    hw = NOBE_W / 2.0
    objs = []
    n = [0]

    def nm(p):
        n[0] += 1
        return "%s%03d" % (p, n[0])

    def slab(x0, x1, y0, y1):
        objs.append(kiriishi(nm("kiri"), x1 - x0, y1 - y0, NOBE_T, 0.010, rng,
                             top=-rng.uniform(0.0, 0.004), cx=(x0 + x1) * 0.5, cy=(y0 + y1) * 0.5))

    def tama_field(x0, x1):
        # 縁の細い切石(両側)
        for ys in ((-hw, -hw + NOBE_KERB), (hw - NOBE_KERB, hw)):
            x = x0
            while x1 - x > 1e-3:
                ln = min(rng.uniform(0.18, 0.34), x1 - x)
                if x1 - (x + ln) < 0.12:
                    ln = x1 - x
                slab(x + JOINT * 0.5, x + ln - JOINT * 0.5, ys[0] + JOINT * 0.5, ys[1] - JOINT * 0.5)
                x += ln
        # 中の玉石(揺らした格子)
        yi0, yi1 = -hw + NOBE_KERB + JOINT, hw - NOBE_KERB - JOINT
        pitch = 0.092
        nxi = max(1, int(round((x1 - x0 - JOINT) / pitch)))
        nyi = max(1, int(round((yi1 - yi0) / pitch)))
        px, py = (x1 - x0 - JOINT) / nxi, (yi1 - yi0) / nyi
        stems = ("s_rock_03", "s_rock_04", "s_rock_05", "s_rock_06")
        for i in range(nxi):
            for j in range(nyi):
                cx = x0 + JOINT * 0.5 + px * (i + 0.5) + rng.uniform(-0.15, 0.15) * px
                cy = yi0 + py * (j + 0.5) + rng.uniform(-0.15, 0.15) * py
                sz = min(px, py) * rng.uniform(1.08, 1.22)
                objs.append(_tama(nm("tama"), _tama_proto(rng.choice(stems)), sz,
                                  -rng.uniform(0.002, 0.008), cx, cy, rng.uniform(0, math.tau)))

    # 床(土)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * (L - 0.004), v.co.y * (NOBE_W - 0.004), -0.065 + v.co.z * 0.06))  # 床の天端 −0.035(玉石の胴が出る高さ)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            lp[uvl].uv = (0.008 + (co.x + L / 2) / 32.0, 0.900 + (co.y + co.z + hw) / 32.0)  # ⛔ 折り返さない(床は1枚の四角で芯に頂点が無い)
    objs.append(_obj("toko", bm, [mat(SOIL)]))
    _outward(objs[-1])

    # 並び。端の切石 → [玉石 | 切石 | 切石の対] … → 端の切石
    x, xe = -L / 2.0, L / 2.0
    e0, e1 = rng.uniform(0.30, 0.40), rng.uniform(0.30, 0.40)
    slab(x + JOINT * 0.5, x + e0 - JOINT * 0.5, -hw + JOINT * 0.5, hw - JOINT * 0.5)
    x += e0
    seq = ["tama", "pair", "tama", "slab"]
    k = 0
    while (xe - e1) - x > 0.30:
        kind = seq[k % len(seq)]
        k += 1
        room = (xe - e1) - x
        ln = {"tama": rng.uniform(0.45, 0.70), "pair": rng.uniform(0.32, 0.46),
              "slab": rng.uniform(0.30, 0.42)}[kind]
        if room - ln < 0.30:
            ln = room
        if kind == "tama" and ln >= 0.30:
            tama_field(x, x + ln)
        elif kind == "pair":
            w1 = rng.uniform(0.24, 0.34)
            off = 0.0   # ⛔ 対の端をずらすと次の石へ食い込む
            slab(x + JOINT * 0.5, x + ln - JOINT * 0.5 + off, -hw + JOINT * 0.5, -hw + w1 - JOINT * 0.5)
            slab(x + JOINT * 0.5, x + ln - JOINT * 0.5 - off, -hw + w1 + JOINT * 0.5, hw - JOINT * 0.5)
        else:
            slab(x + JOINT * 0.5, x + ln - JOINT * 0.5, -hw + JOINT * 0.5, hw - JOINT * 0.5)
        x += ln
    slab(x + JOINT * 0.5, xe - JOINT * 0.5, -hw + JOINT * 0.5, hw - JOINT * 0.5)
    for p in _TAMA.values():
        bpy.data.objects.remove(p, do_unlink=True)
    _TAMA.clear()
    name = "Doi_Nobedan_W%.2f_L%.2f" % (NOBE_W, L)
    return _finish(objs, name), name


# ================================================================ 5. 縁先手水鉢
def _cut_top(o, frac):
    mn, mx = BM.bounds([o])
    ON._cut_z(o, mn.z + (mx.z - mn.z) * frac, keep_below=True)


def chozubachi():
    """**縁先手水鉢**(`gardens[G_Okuniwa].chozu`)。自然石の鉢 φ0.55 × h0.35(在庫の実岩
    `Rock_07`(平面 1.25×1.11 の丸い塊・中性の灰)の頭を落として水穴を彫り込む)を、
    台石(`Rock_05_cut` の頭を均した物 0.85 × 0.60 × 0.32 ── `Own.DoiKutsunugi` と同じ元石)に載せる。
    ピボット = **鉢の平面の芯・鉢の縁の天端** ⇒ `position.y = rimY`(長局の縁板の天端 −0.10)。
    鉢の底 −0.35 / 台石は −0.33 … −0.65(地盤が縁板 −0.6 前後なら台石の見え 0.15〜0.2・残りは根入れ)。
    水穴 = 縁の幅 0.08 前後・深さ 0.15。役石(清浄石・水揚石)は含めない(yaku 欄が Own.Ishigumi で据える)。
    ⚠ 1回目は `m_rock_02`(淡桃)で焼き、切り口だけ灰の無地を貼ったら継ぎはぎの斑に見えた ──
      ⭕ 元石は**無地の肌(ROCK_PLAIN_UV)と同じ灰**の個体から選ぶ(平均色 R−B ≈ 0)。"""
    rng = random.Random(53305)
    # ---- 鉢
    bowl = ON._rock("Rock_07", "hachi")
    ON._center_xy(bowl, z_at='bottom')
    _cut_top(bowl, 0.55)        # 低く切るほど天端が広い(0.72 では水穴 φ0.18 しか取れなかった)
    mn, mx = BM.bounds([bowl])
    s = BOWL_D / max(mx.x - mn.x, mx.y - mn.y)
    bowl.data.transform(Matrix.Diagonal((s, s, BOWL_H / (mx.z - mn.z), 1.0)))
    bowl.data.update()
    ON._center_xy(bowl, z_top=True)
    # 水穴。⛔ boolean は使わない(底の開いた岩で解けない)。⛔ 切り口の n角形を inset しない ──
    #   岩の切り口の輪郭はぎざぎざで、inset が棘の三角を吐いた(2回目のレンダ)。
    #   ⭕ 切り口の面を消し、芯に**円の輪**を新しく置いて輪郭と円をジッパー状に三角で綴じ(縁)、
    #     円から下へ輪を3段すぼめて底へ閉じる(水穴)。面の向きは1枚ずつ決める
    #     (⛔ 底の開いた岩に符号付き体積の向き直しを掛けない ── 閉じていないので符号が当てにならない)。
    bm = bmesh.new(); bm.from_mesh(bowl.data)
    caps = set(f for f in bm.faces if f.normal.z > 0.9 and f.calc_center_median().z > -0.004)
    bnd = [e for e in bm.edges if sum(1 for f in e.link_faces if f in caps) == 1]
    ring = list(set(v for e in bnd for v in e.verts))
    bmesh.ops.delete(bm, geom=list(caps), context='FACES_ONLY')
    # 芯は輪郭の重心でなく**内接円の芯**(格子で探す)── 重心だと切り口の歪みで穴が片寄り小さくなった
    xs_r = [v.co.x for v in ring]; ys_r = [v.co.y for v in ring]
    best = (-1.0, 0.0, 0.0)
    for gi in range(21):
        for gj in range(21):
            px = min(xs_r) + (max(xs_r) - min(xs_r)) * (0.2 + 0.6 * gi / 20)
            py = min(ys_r) + (max(ys_r) - min(ys_r)) * (0.2 + 0.6 * gj / 20)
            dmin = min(math.hypot(v.co.x - px, v.co.y - py) for v in ring)
            if dmin > best[0]:
                best = (dmin, px, py)
    rmin, cx, cy = best
    ang = lambda co: math.atan2(co.y - cy, co.x - cx)
    ring.sort(key=lambda v: ang(v.co))
    r = max(0.6 * rmin, rmin - 0.07)          # 縁は 0.07 前後残す
    NR = 40
    th = [-math.pi + math.tau * (k + 0.5) / NR for k in range(NR)]
    rings = []
    for z, kr in ((0.0, 1.0), (-0.04, 0.96), (-0.11, 0.80), (-0.15, 0.52)):
        rings.append([bm.verts.new((cx + r * kr * math.cos(t), cy + r * kr * math.sin(t), z)) for t in th])
    fresh_f = []
    # 縁: 輪郭(ring)と円(rings[0])を角度順に綴じる
    E0 = rings[0]
    i = j = 0
    n, m = len(ring), NR
    while i < n or j < m:
        a_i = ang(ring[(i + 1) % n].co) + (math.tau if i + 1 >= n else 0.0)
        a_j = th[(j + 1) % m] + (math.tau if j + 1 >= m else 0.0)
        if (a_i <= a_j and i < n) or j >= m:
            tri = (ring[i % n], ring[(i + 1) % n], E0[j % m]); i += 1
        else:
            tri = (ring[i % n], E0[(j + 1) % m], E0[j % m]); j += 1
        if len(set(tri)) == 3:
            try:
                fresh_f.append(bm.faces.new(tri))
            except ValueError:
                pass
    # 水穴の壁と底
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for q in range(NR):
            fresh_f.append(bm.faces.new((A[q], A[(q + 1) % NR], B[(q + 1) % NR], B[q])))
    cb = bm.verts.new((cx, cy, -0.16))
    for q in range(NR):
        fresh_f.append(bm.faces.new((rings[-1][q], rings[-1][(q + 1) % NR], cb)))
    for f in fresh_f:
        f.normal_update()
        cen = f.calc_center_median()
        want = Vector((cx - cen.x, cy - cen.y, 0.0)) * (0.0 if cen.z > -0.001 else 1.0) + Vector((0, 0, 0.3))
        if f.normal.dot(want) < 0.0:
            f.normal_flip()
    bm.faces.index_update()
    fresh = [f.index for f in fresh_f]
    rim_w = rmin - r
    bm.to_mesh(bowl.data); bm.free(); bowl.data.update()
    print("[doiniwa] 鉢の水穴: 径 %.3f・縁の幅(最小)%.3f・深さ 0.16・綴じた面 %d" % (2 * r, rim_w, len(fresh)))
    planar_uv(bowl, PLAIN, 0.11, rng, faces=fresh)
    # ---- 台石
    dai = ON._rock("Rock_05_cut", "dai")
    ON._center_xy(dai, z_at='bottom')
    _cut_top(dai, 0.60)
    mn, mx = BM.bounds([dai])
    dai.data.transform(Matrix.Diagonal((0.85 / (mx.x - mn.x), 0.60 / (mx.y - mn.y),
                                        0.32 / (mx.z - mn.z), 1.0)))
    dai.data.update()
    ON._center_xy(dai, z_top=True)
    ON._cap_uv(dai, PLAIN[0], PLAIN[1], 0.110)
    dai.data.transform(Matrix.Translation((0.04, -0.02, -BOWL_H + 0.02)))
    dai.data.update()
    name = "Doi_Chozubachi_Ensaki"
    return _finish([bowl, dai], name), name


# ================================================================ 材の結線とレンダ
def hook():
    ON.hook()                                       # 岩・丸太・Village Kit
    for mname, base in TEX.items():
        m = bpy.data.materials.get(mname)
        if m is None or not os.path.exists(base + "Albedo.png"):
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        for sock in ('Alpha', 'Base Color'):
            for lk in list(b.inputs[sock].links):
                nt.links.remove(lk)
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.92
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(base + "Albedo.png", check_existing=True)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])


def shots(o, key, ground=None):
    """⚠ 書き出しの前に撮る(export 後は bbox が潰れる)。立面・斜め・真俯瞰(+据えた姿)。"""
    hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = BM.bounds([o])
    c = (mn + mx) * 0.5
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    r = max(W, H, D)
    gz = mn.z - 0.02 if ground is None else ground
    bpy.ops.mesh.primitive_plane_add(size=max(40.0, r * 20), location=(c.x, c.y, gz))
    g = bpy.context.active_object
    gm = bpy.data.materials.new("_ground_render")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.36, 0.31, 0.24, 1)
    g.data.materials.append(gm)
    asp = 1.25 * H / max(W * 1.15, 1e-6)
    res = (1500, max(300, min(1100, int(1500 * asp))))
    V.studio((c.x, mn.y - r * 3.0, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W * 1.15, H * 1.25 * res[0] / res[1]), res=res)
    V.render(os.path.join(SHOT, "doiniwa_%s_elev.png" % key))
    V.studio((c.x - r * 0.9, mn.y - r * 1.2, mx.z + r * 1.3), (c.x, c.y, c.z), res=(1500, 1000))
    V.render(os.path.join(SHOT, "doiniwa_%s_3d.png" % key))
    V.studio((c.x, c.y + 1e-4, mx.z + r * 4.0), (c.x, c.y, mx.z),
             ortho_scale=max(W, D) * 1.15, res=(1500, max(300, int(1500 * max(D / W, 0.25)))))
    V.render(os.path.join(SHOT, "doiniwa_%s_top.png" % key))
    if ground is not None:
        V.studio((c.x + W * 0.4, mn.y - max(2.4, r * 1.1), ground + 1.5),
                 (c.x, c.y, ground + 0.1), res=(1500, 1000))
        V.render(os.path.join(SHOT, "doiniwa_%s_sueru.png" % key))
    bpy.data.objects.remove(g, do_unlink=True)


def report(o, name):
    mn, mx = BM.bounds([o])
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    print("[doiniwa] %-28s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  Y %.3f..%.3f  tri=%d  材質=%s"
          % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, mx.z, tris,
             [m.name for m in o.data.materials]))
    bad = [m.name for m in o.data.materials if m.name not in (ROCK, SOIL, GRASS, "M_Wood_fence")]
    if bad:
        print("[doiniwa] ⛔ 想定外の材: %s" % bad)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    Ls = []
    if "--L" in argv:
        Ls = [float(a) for a in argv[argv.index("--L") + 1].split(",")]
    skip = {argv[argv.index("--L") + 1]} if "--L" in argv else set()
    want = [a for a in argv if not a.startswith("--") and a not in skip] or ["all"]
    if "all" in want:
        want = ["ishibashi", "dobashi", "dan", "nobedan", "chozubachi"]
    do_render = "--render" in argv
    nobe_default = math.hypot(NOBE_A[0] - NOBE_B[0], NOBE_A[1] - NOBE_B[1])
    jobs = []
    for k in want:
        if k == "nobedan":
            for L in (Ls or [nobe_default, 1.818]):
                jobs.append((k, L))
        else:
            jobs.append((k, None))
    for k, L in jobs:
        V.reset()
        if k == "ishibashi":
            o, name = ishibashi(); gnd = None
        elif k == "dobashi":
            o, name = dobashi(); gnd = None
        elif k == "dan":
            o, name = marutadan(); gnd = -0.13
        elif k == "nobedan":
            o, name = nobedan(L); gnd = -0.03
        elif k == "chozubachi":
            o, name = chozubachi(); gnd = -0.50
        else:
            print("[doiniwa] ⚠ 知らない部材: %s" % k); continue
        report(o, name)
        if do_render:
            shots(o, name, ground=gnd)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[doiniwa] 書き出し " + os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    main()
