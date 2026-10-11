"""**土井大隅守上屋敷の排水の部材(EDO-0533・S9 排水)。**

    blender --background --python Tools/Blender/build_doi_haisui.py -- all --render
    blender --background --python Tools/Blender/build_doi_haisui.py -- mizo masu --render
    blender --background --python Tools/Blender/build_doi_haisui.py -- A E F    # 型ごと(深さの版は全部)
    blender --background --python Tools/Blender/build_doi_haisui.py -- AK --render   # 型 A の外壁の嵩上げ石(岡部 EDO-0502)
    blender --background --python Tools/Blender/build_doi_haisui.py -- fuchi --render  # 型 A の縁石の作り AF・吐き口 AH/AFH(岡部 EDO-0502)
    BUZAI_OUT=/path/staging blender --background --python Tools/Blender/build_doi_haisui.py -- all

【寸法の正典は `docs/Sashizu/doi_sashizu.json` の `drainKata`(型 A〜P)】⛔ ここに数字を書き写さない —
  json を読んで `K["A"]["innerW"]` のように引く。json に無い値(下の「部材方の既定」)だけここで決め、
  確度 U として EdoAssets のコメントへ書く。

【在庫で足りる物は焼かない】(在庫方の判定 2026-10-04)
  ・吐き口(埋樋の終点・石組)= `Own.DoiMizushiriHakiguchi` / 石樋 = `Own.MatsudairaIshidoi`
  ・蓋つき溝 = `Own.MatsudairaIshibuta1m`
  ・型 P 軒樋・竪樋は型(木・竹)が考証待ちなので焼かない。

【材は三つだけ・新規マテリアルは作らない】
  ・石 = `M_photoscanned_rocks_01`(泉水の石と一系統・`Own.Ishigumi` / `DoiKutsunugi` / `build_doi_niwa`)。
    切石は箱を面取りして岩アトラスの無地の灰(`ON.ROCK_PLAIN_UV`)へ平面投影。野面石・玉石・栗石は
    在庫の実岩(s_rock / m_rock)を切って使う(規則1)。
  ・土 = `M_FJG_Terrain_Ground_Soil_01`(地形のスプラット L_dirt と同じ肌)/ 玉砂利 = `M_FJG_Terrain_Ground_Gravel_01`
    (FJG の一系統・借り先は土と同じフォルダ)。
  ・木 = `M_Wood_fence`(NatureManufacture の `thick_board` / 丸太を切る)。
  remap は `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`(Models/Fuzokuya と岩・丸太・FJG を全部見る)。

【向きとピボット(Unity 座標)】幅 = X / 高さ = Y / 走り = Z、**+Z = 下流**。
  ・溝の駒(A〜F・K)は **1.000m**。ピボット = **駒の中心・溝の芯・地盤の高さ**(Y=0 = 地盤 / 路面)。
    ⇒ 地盤の高さに据えれば縁が json の `topAbove` だけ出る(A +0.02 / D・E・F +0.03)。
    天端を地盤に据え**地形の下へ潜る**作り: 底と側の内面が見え、外側は地中で隠れる。
    ⭕ bbox の Z をちょうど 1.000 にしてある(ビルダーが bbox からピッチを測る)。端数は端の1本を切る
    (`DoiOtoshimizo` と同じ作法)。⭐ 目地は駒の中だけ・端の平面に乗る稜は面取りしない
    (継いで並べると端の石が一枚に見える。UV も継ぎ目で連続させてある)。
  ・Blender は Z-up。Blender (x, y, z) → Unity (−x, z, −y)。⛔ 取り違えない(`u2b`)。

【モジュールの割り(部材方の判断・確度 U)】
  ・A の縁石は駒の中に継ぎ目を1つずつ(左 0.35・右 0.75)置き、継ぎ目を跨ぐ石の長さが 1.0 になる
    (json の lenMax 0.9 を 0.1 超える)。1m の駒で 0.6〜0.9 の石だけでは周期が組めないため。
  ・E/F の積みは faceHMax 0.25 を超える段を作らない ⇒ 深さ 0.60 は 3段(json の courses 2 は 0.30/0.45 の版)。
  ・H(段落ち)は**1段の駒 0.50m**(段鼻の線がピボット)+ **平らな駒 0.50m**(rise 0)。踏面は平らな駒で埋める。
"""
import bpy, bmesh, sys, os, math, random, json
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_okabe_niwa as ON
import build_doi_niwa as DN

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Fuzokuya"))
SHOT = os.path.join(V.REPO, "Screenshots")
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "doi_sashizu.json")
_J = json.load(open(SASHIZU, encoding="utf-8"))
K = _J["drainKata"]
RAMPS = {r["name"]: r for r in _J["ramps"]}

ROCK = ON.ROCK_MAT
SOIL = DN.SOIL
GRAVEL = "M_FJG_Terrain_Ground_Gravel_01"
WOOD = "M_Wood_fence"
PLAIN = ON.ROCK_PLAIN_UV
FENCE = os.path.join(V.REPO, "Assets", "NatureManufacture Assets", "Meadow Environment Dynamic Nature",
                     "Fence", "Models", "Construction Set Models")
FJG_TEX = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden", "Textures", "Terrain")

# ---- 部材方の既定(json に無い値・確度 U) ----
HALF = 0.5            # 溝の駒の半長(1.000m)
GAP = 0.006           # 目地の半分(目地 0.012)
BEV = 0.012           # 切石の面取り
UVD = 0.11            # 切石の UV 密度(UV/m)
SKIRT = 0.25          # 縁の無い型(B・C・D・E の裏)の土の皮の出(地形の穴の縁を覆う)
C_DEPTHS = (0.10, 0.15)
A_DEPTHS = (0.10, 0.15, 0.20, 0.25, 0.30)
D_DEPTHS = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45)
E_DEPTHS = (0.30, 0.45, 0.60)
D_BATTER = 0.20       # D の土の側の法(水平/鉛直)
E_BACK_BATTER = 0.30  # E の裏(石垣・法尻の側)の土の法
H_RISES = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45)
H_LEN = 0.50
I_RISES = (0.10, 0.15, 0.20, 0.25, 0.30)
I_NORI = (1.0, 1.5)   # 法の勾配(切 1:1.0 / 盛 1:1.5)
L_W = 0.50            # 蓋石の見込み(json wMin 0.45..wMax 0.6)
# 指図の drainKata にまだ入っていない型(普請方の設計 第45巡 2026-10-08・確度 作り B / 寸法 U)。
# ⛔ json に入ったら json が勝つ(K.get が先)── ここは json に載るまでのつなぎ。
_KATA_PENDING = {"G3": {"label": "石の桝(中・溝 E を受ける)", "inner": [0.9, 0.9],
                        "wall": {"kind": "切石4枚組", "t": 0.15}, "topAbove": 0.05, "topRef": "地盤",
                        "sumpBelowOutlet": 0.15,
                        "lid": {"kind": "石蓋", "n": 2, "size": [0.9, 0.5], "t": 0.20, "notch": None}}}
G1_FLOOR = -0.75      # G1 の底の天端(地盤から)= 吐き口の底 −0.60 − 溜め 0.15
H_WALL_TOP = 0.50     # H の野面石の天端(段の底から・json hMin 0.45..hMax 0.6)


def u2b(X, Y, Z):
    """Unity → Blender。"""
    return (-X, -Z, Y)


# ================================================================ 部品
_objs = []
_n = [0]


def _nm(p):
    _n[0] += 1
    return "%s%04d" % (p, _n[0])


def _uv_planar(bm, uvl, org, ou, ov, d=UVD):
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        a, b = {2: (0, 1), 1: (0, 2), 0: (1, 2)}[ax]
        for lp in f.loops:
            c = lp.vert.co
            lp[uvl].uv = (ou + (c[a] - org[a]) * d, ov + (c[b] - org[b]) * d)


def stone(x0, x1, y0, y1, z0, z1, rng, bev=BEV, org=None, uvo=None, ends=True, nobot=True,
          half=HALF, mat_=ROCK):
    """**切石1個**(Unity の範囲で渡す)。全稜を面取り ── ただし駒の端の平面(Z=±half)に乗る稜と
    埋まる底の稜は取らない(継いで一枚に見せる・三角形を抑える)。
    `org`(Blender の最小隅)と `uvo`(矩形の中の位置)を2片で共有すると、継ぎ目を跨ぐ石の UV が連続する。"""
    bx0, bx1, by0, by1 = -x1, -x0, -z1, -z0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((bx0 + bx1) * 0.5 + v.co.x * (bx1 - bx0), (by0 + by1) * 0.5 + v.co.y * (by1 - by0),
                       (y0 + y1) * 0.5 + v.co.z * (y1 - y0)))

    def keep(e):
        a, b = e.verts
        if ends:
            for p in (-half, half):
                if abs(a.co.y - p) < 1e-6 and abs(b.co.y - p) < 1e-6:
                    return True
        if nobot and abs(a.co.z - y0) < 1e-6 and abs(b.co.z - y0) < 1e-6:
            return True
        return False
    eds = [e for e in bm.edges if not keep(e)]
    if bev > 0 and eds:
        bmesh.ops.bevel(bm, geom=eds, offset=bev, offset_type='OFFSET', segments=1,
                        affect='EDGES', clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.new("UVMap")
    if org is None:
        org = (bx0, by0, y0)
    if uvo is None:
        uvo = (PLAIN[0] + rng.uniform(0.0, (PLAIN[2] - PLAIN[0]) - 0.14),
               PLAIN[1] + rng.uniform(0.0, (PLAIN[3] - PLAIN[1]) - 0.14))
    _uv_planar(bm, uvl, org, uvo[0], uvo[1])
    o = DN._obj(_nm("ishi"), bm, [DN.mat(mat_)])
    DN._outward(o)
    _objs.append(o)
    return o


def prism(outline, axis, a0, a1, rng, bev=BEV, nobot=False):
    """**断面の輪郭を押し出した切石**(切り欠きのある蓋・壁)。`outline` は Unity の2軸の点列
    (axis='y' なら (X,Z)・axis='z' なら (X,Y)・axis='x' なら (Z,Y))。反時計回り/時計回りは問わない(向きは体積で直す)。"""
    bm = bmesh.new()
    vs0, vs1 = [], []
    for p, q in outline:
        if axis == 'y':
            A, B = Vector(u2b(p, a0, q)), Vector(u2b(p, a1, q))
        elif axis == 'x':                  # 輪郭 = (Z, Y)・X へ押し出す
            A, B = Vector(u2b(a0, q, p)), Vector(u2b(a1, q, p))
        else:
            A, B = Vector(u2b(p, q, a0)), Vector(u2b(p, q, a1))
        vs0.append(bm.verts.new(A)); vs1.append(bm.verts.new(B))
    bm.faces.new(vs0); bm.faces.new(list(reversed(vs1)))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    zmin = min(v.co.z for v in bm.verts)
    eds = [e for e in bm.edges
           if not (nobot and all(abs(v.co.z - zmin) < 1e-6 for v in e.verts))]
    if bev > 0:
        bmesh.ops.bevel(bm, geom=eds, offset=bev, offset_type='OFFSET', segments=1,
                        affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.new("UVMap")
    mn = [min(v.co[k] for v in bm.verts) for k in range(3)]
    _uv_planar(bm, uvl, mn, PLAIN[0] + rng.uniform(0, 0.02), PLAIN[1] + rng.uniform(0, 0.01))
    o = DN._obj(_nm("ishi"), bm, [DN.mat(ROCK)])
    DN._outward(o)
    _objs.append(o)
    return o


def course(joints, mk, length=1.0):
    """走り [0, length) を `joints` で割り、端を跨ぐ石は2片に分けて作る。mk(a, b, wrap)。
    wrap = None(中の石)/ ('A', a0, b1)(駒の終わりの片)/ ('B', a0, b1)(駒の始まりの片)。"""
    js = sorted(joints)
    for i in range(len(js) - 1):
        mk(js[i], js[i + 1], None)
    mk(js[-1], length, ('A', js[-1], js[0] + length))
    mk(0.0, js[0], ('B', js[-1], js[0] + length))


def run_stone(a, b, wrap, X0, X1, Y0, Y1, rng, length=1.0, bev=BEV, nobot=True, uvo=None):
    """走りの座標 r ∈ [0, length)(Z = r − length/2)の石を1片。継ぎ目の側だけ目地を空ける。"""
    h = length * 0.5
    za = a - h + (GAP if a > 1e-9 else 0.0)
    zb = b - h - (GAP if b < length - 1e-9 else 0.0)
    org = None
    if wrap is not None:
        _, r0, r1 = wrap
        # 論理上の石は r0..r1(r1 > length)。Blender y = −Z。片 B は1駒ぶん先(y −length)へ続く
        org = [-X1, -(r1 - h), Y0]
        if wrap[0] == 'B':
            org[1] += length
    return stone(X0, X1, Y0, Y1, za, zb, rng, bev=bev, org=org, uvo=uvo, nobot=nobot, half=h)


def joints_for(rng, lmin, lmax, length=1.0, avoid=(), clear=0.08):
    """周期 length の継ぎ目の集合(石の長さ lmin..lmax・avoid の継ぎ目から clear 以上離す)。"""
    for _ in range(400):
        n = max(1, int(round(length / ((lmin + lmax) * 0.5))))
        start = rng.uniform(0.0, length / n)
        js, ok = [], True
        for i in range(n):
            j = (start + i * length / n + rng.uniform(-0.25, 0.25) * (lmax - lmin)) % length
            js.append(j)
        js.sort()
        ls = [(js[(i + 1) % n] - js[i]) % length or length for i in range(n)]
        if any(l < lmin - 1e-6 or l > lmax + 1e-6 for l in ls):
            ok = False
        if any(min(abs(j - a), length - abs(j - a)) < clear for j in js for a in avoid):
            ok = False
        if any(min(j, length - j) < 0.03 for j in js):
            ok = False
        if ok:
            return js
    return [length * 0.37]


def surface(profile, mats, z0=-HALF, z1=HALF, nz=2, uvfn=None):
    """**断面の折れ線を走り Z に押し出した面**(土・玉砂利の片面)。profile = [(X, Y)...] 左→右。
    mats[i] = 区間 i の材。面の向きは「溝の芯の上」を向く。UV は uvfn(X, Y, Z, s, mat)。
    ⚠ 土の UV は |s|・|Z| で芯を折り返す ⇒ 芯(X=0)と Z=0 に頂点を置く(⛔ 面の中で折り返さない)。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    arc = [0.0]
    for i in range(1, len(profile)):
        arc.append(arc[-1] + math.hypot(profile[i][0] - profile[i - 1][0], profile[i][1] - profile[i - 1][1]))
    # s = 芯(X=0 に一番近い点)からの弧長
    ic = min(range(len(profile)), key=lambda i: abs(profile[i][0]))
    sarc = [a - arc[ic] for a in arc]
    zs = [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    rows = [[bm.verts.new(u2b(x, y, z)) for (x, y) in profile] for z in zs]
    mlist = sorted(set(mats))
    for k in range(nz):
        for i in range(len(profile) - 1):
            a, b, c, d = rows[k][i], rows[k][i + 1], rows[k + 1][i + 1], rows[k + 1][i]
            f = bm.faces.new((a, b, c, d))
            f.material_index = mlist.index(mats[i])
            f.normal_update()
            cen = f.calc_center_median()
            up = Vector((0.0, cen.y, 1.0)) - Vector((cen.x * 0.0, cen.y, cen.z))
            tgt = Vector((0.0, cen.y, cen.z + 1.0)) - cen
            if f.normal.dot(tgt) < 0.0:
                f.normal_flip()
            for lp in f.loops:
                ii = rows[k].index(lp.vert) if lp.vert in rows[k] else rows[k + 1].index(lp.vert)
                zz = zs[k] if lp.vert in rows[k] else zs[k + 1]
                X, Y = profile[ii]
                lp[uvl].uv = uvfn(X, Y, zz, sarc[ii], mats[i])
    o = DN._obj(_nm("men"), bm, [DN.mat(m) for m in mlist])
    for p in o.data.polygons:
        p.use_smooth = False
    _objs.append(o)
    return o


def uv_ground(X, Y, Z, s, m):
    """土 = FJG Soil の苔の無い茶の矩形(**8m 周期** = 地形の L_dirt と同じ縮尺・芯で折り返す)/
    玉砂利 = 1m 周期(駒の長さで割り切れる)。⚠ 16m 周期だと松葉が 2 倍に拡大されて橙の筋に見えた(1回目のレンダ)。"""
    if m == SOIL:
        return (0.008 + abs(s) / 8.0, 0.900 + abs(Z) / 8.0)
    return (X + 0.5, Z + 0.5)


def heightfield(fy, x0, x1, z0, z1, nx, nz, mat_=SOIL):
    """格子の面(皿の土)。Y = fy(X, Z)。上向き。UV は芯で折り返す(格子は奇数分割で芯に頂点)。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    zs = [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    g = [[bm.verts.new(u2b(x, fy(x, z), z)) for x in xs] for z in zs]
    for k in range(nz):
        for i in range(nx):
            f = bm.faces.new((g[k][i], g[k][i + 1], g[k + 1][i + 1], g[k + 1][i]))
            f.normal_update()
            if f.normal.z < 0:
                f.normal_flip()
            for lp in f.loops:
                c = lp.vert.co
                lp[uvl].uv = (0.008 + abs(c.x) / 8.0, 0.900 + abs(c.y) / 8.0)   # 8m 周期(地形と同じ縮尺)
    o = DN._obj(_nm("sara"), bm, [DN.mat(mat_)])
    _objs.append(o)
    return o


# ---------------------------------------------------------------- 実岩(野面石・玉石・栗石)
_PROTO = {}
SMALL = ("s_rock_01", "s_rock_02", "s_rock_04", "s_rock_05", "s_rock_06")


def _proto(stem):
    if stem in _PROTO:
        return _PROTO[stem]
    path = os.path.join(ON.NMR, stem + ".FBX")
    lod = "LOD2" if stem in ("s_rock_01", "s_rock_02", "m_rock_01") else "LOD1"
    objs = VM.import_fbx_abs(path, keep=lambda n: n.endswith(lod))
    o = V.join(objs, "proto_" + stem)
    for sl in o.material_slots:
        sl.material = DN.mat(ROCK)
    uls = o.data.uv_layers
    keep = uls.active if uls.active is not None else uls[0]
    for ul in [u for u in uls if u.name != keep.name]:
        uls.remove(ul)
    uls[0].name = "UVMap"
    # いちばん薄い軸を鉛直へ(玉石は寝て据わる)
    xs = [v.co for v in o.data.vertices]
    dd = [max(c[k] for c in xs) - min(c[k] for c in xs) for k in range(3)]
    k = dd.index(min(dd))
    if k == 0:
        o.data.transform(Matrix.Rotation(math.radians(90), 4, 'Y'))
    elif k == 1:
        o.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
    o.data.update()
    ON._center_xy(o, z_at='bottom')
    o.hide_render = True
    _PROTO[stem] = o
    return o


def rock(stem, size, h, X, top, Z, yaw, cut=None, zlim=None):
    """実岩1個。平面の長い径 = size・丈 = h(丈だけ別に縮める ── 寝た石の扁平は自然)。
    天端 = top(Unity Y)。cut(Unity Y)より下を落とす。zlim=(z0,z1) なら走りの外へ出ないよう寄せる。"""
    pr = _proto(stem)
    me = pr.data.copy()
    o = bpy.data.objects.new(_nm("iwa"), me)
    bpy.context.scene.collection.objects.link(o)
    o.hide_render = False
    cs = [v.co for v in me.vertices]
    L0 = max(max(c.x for c in cs) - min(c.x for c in cs), max(c.y for c in cs) - min(c.y for c in cs))
    H0 = max(c.z for c in cs) - min(c.z for c in cs)
    me.transform(Matrix.Diagonal((size / L0, size / L0, h / H0, 1.0)))
    me.transform(Matrix.Rotation(yaw, 4, 'Z'))
    bx, by, _ = u2b(X, 0.0, Z)
    zt = max(v.co.z for v in me.vertices)
    me.transform(Matrix.Translation((bx, by, top - zt)))
    if zlim is not None:
        # Unity Z ∈ zlim ⇔ Blender y ∈ (−z1, −z0)
        ys = [v.co.y for v in me.vertices]
        lo, hi = -zlim[1], -zlim[0]
        sh = 0.0
        if min(ys) < lo:
            sh = lo - min(ys)
        if max(ys) + sh > hi:
            sh = hi - max(ys)
        if abs(sh) > 0:
            me.transform(Matrix.Translation((0.0, sh, 0.0)))
        ys = [v.co.y for v in me.vertices]
        if min(ys) < lo - 1e-6 or max(ys) > hi + 1e-6:
            cy = (min(ys) + max(ys)) * 0.5
            kk = (hi - lo) / (max(ys) - min(ys)) * 0.999
            me.transform(Matrix.Translation((0, cy, 0)) @ Matrix.Diagonal((kk, kk, 1.0, 1.0))
                         @ Matrix.Translation((0, -cy, 0)))
    if cut is not None:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                               plane_co=Vector((0, 0, cut)), plane_no=Vector((0, 0, 1)), clear_inner=True)
        bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(me); bm.free()
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    _objs.append(o)
    return o


def tama_field(rng, x0, x1, z0, z1, smin, smax, fy, hk=0.55, cut_below=0.06, stems=SMALL, pitch=None,
               inside=None, fill=1.25, ycap=None):
    """玉石を敷き詰める(揺らした格子)。fy(X,Z) = 下地の高さ。石の天端 ≈ 下地 + 0.7×丈。
    ⚠ 実岩は bbox の長径で寸法を合わせるので、見えの径は 0.8 倍ほど ⇒ fill 1.25 を掛けて詰める
    (掛けないと下地の土が半分見えて「散らばった石」になった ── 1回目のレンダ)。"""
    p = pitch or (smin + smax) * 0.5 * 0.92
    nx = max(1, int(round((x1 - x0) / p)))
    nz = max(1, int(round((z1 - z0) / p)))
    px, pz = (x1 - x0) / nx, (z1 - z0) / nz
    for i in range(nx):
        for k in range(nz):
            X = x0 + px * (i + 0.5) + rng.uniform(-0.18, 0.18) * px
            Z = z0 + pz * (k + 0.5) + rng.uniform(-0.18, 0.18) * pz
            if inside is not None and not inside(X, Z):
                continue
            s = rng.uniform(smin, smax) * fill
            h = s * hk * rng.uniform(0.85, 1.1)
            base = fy(X, Z)
            r = s * 0.5
            tp = base + 0.70 * h if ycap is None else min(base + 0.70 * h, ycap - rng.uniform(0.0, 0.01))
            rock(rng.choice(stems), s, h, X, tp, Z, rng.uniform(0, math.tau),
                 cut=base - cut_below, zlim=(z0 - 1e-4 if z0 <= -HALF + 1e-6 else z0 - r,
                                             z1 + 1e-4 if z1 >= HALF - 1e-6 else z1 + r))


# ---------------------------------------------------------------- 木(thick_board を切る)
_BOARD = {}


def board(Xc, Yc, Zc, lx, ly, lz, mode):
    """**板1枚**(在庫 `thick_board` の LOD1 を寸法へ合わせる)。Unity の寸法 lx × ly × lz。
    mode = 'side'(長手 = 走り Z・幅 = 高さ Y の立てた側板)/ 'lid'(長手 = X・寝かせた蓋板)。"""
    if "p" not in _BOARD:
        objs = VM.import_fbx_abs(os.path.join(FENCE, "thick_board.FBX"), keep=lambda n: n.endswith("LOD1"))
        o = V.join(objs, "proto_board")
        for sl in o.material_slots:
            sl.material = DN.mat(WOOD)
        uls = o.data.uv_layers
        keep = uls.active if uls.active is not None else uls[0]
        for ul in [u for u in uls if u.name != keep.name]:
            uls.remove(ul)
        uls[0].name = "UVMap"
        cs = [v.co for v in o.data.vertices]
        ext = [max(c[k] for c in cs) - min(c[k] for c in cs) for k in range(3)]
        cen = [(max(c[k] for c in cs) + min(c[k] for c in cs)) * 0.5 for k in range(3)]
        o.data.transform(Matrix.Translation((-cen[0], -cen[1], -cen[2])))
        o.data.update()
        o.hide_render = True
        _BOARD["p"], _BOARD["ext"] = o, ext          # 長手 = Blender x / 幅 = y / 厚 = z
    pr, ext = _BOARD["p"], _BOARD["ext"]
    me = pr.data.copy()
    o = bpy.data.objects.new(_nm("ita"), me)
    bpy.context.scene.collection.objects.link(o)
    # Blender の寸法: x = lx, y = lz, z = ly
    if mode == 'side':
        # 新 x = 旧 z(厚)/ 新 y = 旧 x(長手)/ 新 z = 旧 y(幅)── 巡回の置換(行列式 +1)
        me.transform(Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
        me.transform(Matrix.Diagonal((lx / ext[2], lz / ext[0], ly / ext[1], 1.0)))
    else:
        me.transform(Matrix.Diagonal((lx / ext[0], lz / ext[1], ly / ext[2], 1.0)))
    me.transform(Matrix.Translation(Vector(u2b(Xc, Yc, Zc))))
    me.update()
    _objs.append(o)
    return o


def kui(X, top, Z, L=0.40, d=0.05):
    import build_maruta as BM
    k = BM.upright(BM.log_piece("wood_log_06", L, d, _nm("kui"), frm=0.05), top_at_zero=True)
    bx, by, _ = u2b(X, 0, Z)
    k.data.transform(Matrix.Translation((bx, by, top)))
    k.data.update()
    for sl in k.material_slots:
        sl.material = DN.mat(WOOD)
    uls = k.data.uv_layers
    if len(uls):
        keepn = (uls.active or uls[0]).name
        for ul in [u for u in uls if u.name != keepn]:
            uls.remove(ul)
        uls[0].name = "UVMap"
    _objs.append(k)
    return k


# ================================================================ 型 A〜F・K(溝の 1m 駒)
FUCHI_DROP = 0.55     # 縁石の作り(AF)の縁石の下端 = 天端 − 0.55(道より 0.45 上まで見せて 0.10 根入れ・岡部 EDO-0502・確度 U)
HAKI_W = None         # 吐き口(AH/AFH)の口の幅 = 型 A の内法(json innerW)── None なら内法


def mizo_A(d, fuchi=False, haki=False):
    """**型 A 切石の雨落ち溝**。内法 0.30・縁石 0.12 × 丈 0.24(天端 +0.02)・外幅 0.54・底は玉砂利。
    深さ d = 地盤 − 玉砂利の天端。縁石の下端は min(−0.22, −d−0.05)(深い版は内面に土を見せない)。

    fuchi=True(**AF 縁石の作り**・岡部 EDO-0502 grading.omoteNagayaDai.mizo の Mizo_Minami / Mizo_Hashi):
      両側の縁石を天端 −FUCHI_DROP まで下ろす ── 道が溝の底より低く、外の壁を道より 0.30〜0.45 上に見せる所。
      天端・内法・底・継ぎ目は A と同じ(A と継いで並ぶ)。左右対称なので向きを選ばない。
    haki=True(**AH / AFH 吐き口**): +X の縁石を駒の芯で内法の幅だけ切り、口の底に敷き石(天端 = 底 −d・
      見付は縁石と同じ 0.12 ── 区画の線を越えない)を入れる。口 = +X(据える側が +X を道へ向ける)。
      底は平ら・Z に対称 ⇒ 二つの溝が両側から落ち合う所(s76)にも、一つの溝の尻(s44)にも同じ駒で据わる。"""
    a = K["A"]; c = a["curb"]
    rng = random.Random(5330100 + int(d * 1000) + (7 if fuchi else 0) + (13 if haki else 0))
    hi, cw, top = a["innerW"] / 2.0, c["w"], c["topAbove"]
    cb = top - FUCHI_DROP if fuchi else min(top - c["h"], -d - 0.05)
    nw = (HAKI_W or a["innerW"]) / 2.0
    for s, j in ((-1, 0.35), (1, 0.75)):
        X0, X1 = (-hi - cw, -hi) if s < 0 else (hi, hi + cw)
        tp = top - rng.uniform(0.0, 0.004)
        uvo = (PLAIN[0] + rng.uniform(0, 0.02), PLAIN[1] + rng.uniform(0, 0.015))
        if haki and s > 0:
            # 口の両脇の石(駒の端の稜は取らない・口の側は取る)と口の敷き石
            stone(X0, X1, cb, tp, -HALF, -nw, rng, uvo=uvo)
            stone(X0, X1, cb, tp - rng.uniform(0.0, 0.003), nw, HALF, rng)
            stone(X0, X1, cb, -d, -nw, nw, rng, ends=False)
            continue
        course([j], lambda r0, r1, w: run_stone(r0, r1, w, X0, X1, cb, tp, rng, uvo=uvo))
    surface([(-hi, -d), (0.0, -d), (hi, -d)], [GRAVEL, GRAVEL], uvfn=uv_ground)
    return "Doi_Mizo_A%s%s_D%.2f" % ("F" if fuchi else "", "H" if haki else "", d)


KASA_HS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45)
KASA_COURSE = 0.25    # 1段の丈の上限(E の faceHMax と同じ)── 超えたら2段に積む
KASA_JOINTS = (0.55, 0.05)   # 段ごとの継ぎ目(走り r)。A の縁石の継ぎ目 0.35/0.75 から左右どちらでも 0.2 ずらす


def kasa_A(h):
    """**型 A の外壁の嵩上げ石**(岡部 EDO-0502 第95巡・okabe_sashizu terraces[1].roadEdge 10-10n)。
    A の縁石と同じ見付 0.12・切石・同じ材と肌で、長さ 1.000 の駒。丈 h(0.10〜0.45)。
    **ピボット = 駒の中心・見付の芯・下面**(Y=0 = 載せる縁石の天端)。上下の面は平ら(面取りは稜だけ)。
    丈 ≤ 0.25 は1段・超えたら2段(下段 = h/2 を 0.05 に丸め)、継ぎ目は段ごとに半駒ずらす。
    駒の端(Z=±0.5)の稜は面取りしない(並べて一枚に見せる)。"""
    a = K["A"]; c = a["curb"]
    rng = random.Random(5330900 + int(round(h * 1000)))
    hw = c["w"] / 2.0
    if h <= KASA_COURSE + 1e-6:
        cuts = [0.0, h]
    else:
        lo = round(h / 2.0 / 0.05) * 0.05
        cuts = [0.0, lo, h]
    for i in range(len(cuts) - 1):
        y0, y1 = cuts[i], cuts[i + 1]
        uvo = (PLAIN[0] + rng.uniform(0, 0.02), PLAIN[1] + rng.uniform(0, 0.015))
        course([KASA_JOINTS[i % 2]],
               lambda r0, r1, w, y0=y0, y1=y1, uvo=uvo: run_stone(r0, r1, w, -hw, hw, y0, y1, rng, uvo=uvo))
    return "Doi_Mizo_A_Kasa_H%.2f" % h


def _skirt(xe, ye, s):
    """縁の無い溝の肩の土の皮(xe,ye = 溝の縁 → 外へ SKIRT 出て −0.03 へ潜る)。s = ±1。"""
    return [(s * (xe + SKIRT), -0.03), (s * (xe + 0.05), 0.004)]


def mizo_B():
    """**型 B 玉石の雨落ち**。帯 0.45・玉石 0.06〜0.12・天端は地盤 −0.03。下地は土(石の間に暗く見える)。"""
    b = K["B"]
    rng = random.Random(5330200)
    hw = b["bandW"] / 2.0
    yb = -b["topBelow"] - 0.06
    prof = list(reversed(_skirt(hw, 0.0, -1)))
    prof = [(-hw - SKIRT, -0.03), (-hw - 0.05, 0.004), (-hw, -0.05), (-hw + 0.03, yb), (0.0, yb),
            (hw - 0.03, yb), (hw, -0.05), (hw + 0.05, 0.004), (hw + SKIRT, -0.03)]
    surface(prof, [SOIL] * (len(prof) - 1), uvfn=uv_ground)
    smin, smax = b["stoneDMin"], b["stoneDMax"]
    tama_field(rng, -hw + 0.02, hw - 0.02, -HALF, HALF, smin, smax,
               lambda X, Z: -b["topBelow"] - 0.045, hk=0.55, cut_below=0.03, ycap=-b["topBelow"],
               stems=("s_rock_01", "s_rock_02", "s_rock_01", "s_rock_04"))
    return "Doi_Mizo_B"


def mizo_C(d):
    """**型 C 素掘りの雨落ち**(縁なし)。底 0.30・法 1:0.5・土の面だけ。肩に土の皮を回す。"""
    c = K["C"]
    bw = c["bottomW"] / 2.0
    th = bw + c["sideBatter"] * d
    prof = [(-th - SKIRT, -0.03), (-th - 0.04, 0.003), (-th + 0.01, -0.006), (-bw - 0.015, -d + 0.008),
            (-bw + 0.02, -d), (0.0, -d), (bw - 0.02, -d), (bw + 0.015, -d + 0.008), (th - 0.01, -0.006),
            (th + 0.04, 0.003), (th + SKIRT, -0.03)]
    surface(prof, [SOIL] * (len(prof) - 1), uvfn=uv_ground)
    return "Doi_Mizo_C_D%.2f" % d


def mizo_D(d):
    """**型 D 素掘りの溝(石の縁)**。底 0.36・土の側(法 1:0.2)・両肩に野面石を半ば埋める(天端 +0.03)。"""
    dd = K["D"]; c = dd["curb"]
    rng = random.Random(5330400 + int(d * 1000))
    bw = dd["bottomW"] / 2.0
    th = bw + D_BATTER * d
    prof = [(-th - 0.30, -0.04), (-th, 0.0), (-bw, -d), (0.0, -d), (bw, -d), (th, 0.0), (th + 0.30, -0.04)]
    surface(prof, [SOIL] * (len(prof) - 1), uvfn=uv_ground)
    for s in (-1, 1):
        # 5個/m ── 岩の bbox の長径で寸法を合わせるので、見えの径は 0.8 倍ほどになる(1回目のレンダで疎に見えた)
        zs = [-0.40, -0.20, 0.0, 0.20, 0.40]
        for i, Z in enumerate(zs):
            sz = rng.uniform(c["dMin"], c["dMax"]) * 1.15
            h = sz * rng.uniform(0.62, 0.75)
            Zj = Z + rng.uniform(-0.015, 0.015)
            rock(rng.choice(("s_rock_05", "s_rock_06", "s_rock_03", "s_rock_04")), sz, h,
                 s * (th + sz * 0.32), c["topAbove"] - rng.uniform(0.0, 0.012), Zj, rng.uniform(0, math.tau),
                 zlim=(-HALF, HALF))
    return "Doi_Mizo_D_D%.2f" % d


def _wall(rng, X0, X1, d, inner_sign):
    """**割石の空積み**(E・F の側壁)。段数 = max(2, ceil((d+top)/faceHMax))・各段の継ぎ目は互い違い。
    inner_sign = 見え面の向き(+1 = 見え面が X1 側 … X0..X1 のうち内側の面を揺らす)。"""
    e = K["E"]; w = e["wall"]
    top = e["topAbove"]
    yb = -d - e["bed"]["t"]
    n = max(w["courses"], int(math.ceil((d + top) / w["faceHMax"] - 1e-6)))
    hs = [(d + top) / n] * n
    ys = [top]
    for h in hs:
        ys.append(ys[-1] - h)
    ys[-1] = yb
    prev = ()
    for c in range(n):
        js = joints_for(rng, 0.28, 0.50, avoid=prev, clear=0.10)
        prev = tuple(js)
        y1, y0 = ys[c] - (0.0 if c == 0 else 0.004), ys[c + 1] + 0.004

        def mk(r0, r1, wrap, y0=y0, y1=y1):
            inset = rng.uniform(0.0, 0.018)
            tp = y1 - (rng.uniform(0.0, 0.008) if c == 0 else 0.0)
            if inner_sign > 0:
                xa, xb = X0, X1 - inset
            else:
                xa, xb = X0 + inset, X1
            if wrap is not None:            # 跨ぐ石の2片は同じ寸法
                key = (c, wrap[1])
                if key not in mk.cache:
                    mk.cache[key] = (xa, xb, tp, (PLAIN[0] + rng.uniform(0, 0.02), PLAIN[1] + rng.uniform(0, 0.015)))
                xa, xb, tp, uvo = mk.cache[key]
            else:
                uvo = None
            run_stone(r0, r1, wrap, xa, xb, y0, tp, rng, bev=0.015, uvo=uvo)
        mk.cache = {}
        course(js, mk)
    return n


def _bed_slabs(rng, X0, X1, d, t):
    """平石張りの底(継ぎ目は駒の中・幅の割りは石ごとに乱数)。"""
    js = joints_for(rng, 0.30, 0.50)

    def mk(r0, r1, wrap):
        tp = -d - (rng.uniform(0.0, 0.004) if wrap is None else 0.002)
        if wrap is None and rng.random() < 0.5:
            xm = X0 + (X1 - X0) * rng.uniform(0.40, 0.60)
            run_stone(r0, r1, None, X0, xm - GAP, -d - t, tp, rng)
            run_stone(r0, r1, None, xm + GAP, X1, -d - t, tp - 0.002, rng)
        else:
            uvo = (PLAIN[0] + 0.01, PLAIN[1] + 0.01) if wrap is not None else None
            run_stone(r0, r1, wrap, X0, X1, -d - t, tp, rng, uvo=uvo)
    course(js, mk)


def mizo_E(d, sides=1):
    """**型 E 石組の溝(片側)/ F(両側)**。内法 0.45・割石の空積み(控え 0.30・天端 +0.03)・底は平石張り t0.08。
    E: **+X = 石組の壁(路面の側)/ −X = 石垣の根固め・法尻の側**(土の法 1:0.3 + 野面石1段)。"""
    e = K["E"]
    rng = random.Random(5330500 + sides * 100 + int(d * 1000))
    hi, wd, t = e["innerW"] / 2.0, e["wall"]["depth"], e["bed"]["t"]
    n = _wall(rng, hi, hi + wd, d, -1)
    if sides == 2:
        _wall(rng, -hi - wd, -hi, d, +1)
        _bed_slabs(rng, -hi, hi + 0.02, d, t)
    else:
        _bed_slabs(rng, -hi - 0.05, hi + 0.02, d, t)
        tx = hi + E_BACK_BATTER * d
        prof = [(-tx - SKIRT, -0.03), (-tx - 0.04, 0.003), (-tx, -0.005), (-hi - 0.04, -d + 0.01), (-hi - 0.06, -d - 0.02),
                (0.0, -d - 0.02)]
        surface(prof, [SOIL] * (len(prof) - 1), uvfn=uv_ground)
        for Z in (-0.33, 0.0, 0.33):         # 法尻の野面石1段
            sz = rng.uniform(0.26, 0.32)
            h = min(0.24, d * 0.6) * rng.uniform(0.9, 1.05)
            rock(rng.choice(("s_rock_05", "s_rock_06", "s_rock_03")), sz, h, -hi - sz * 0.42,
                 -d + h * 0.85, Z + rng.uniform(-0.03, 0.03), rng.uniform(0, math.tau), cut=-d - 0.06,
                 zlim=(-HALF, HALF))
    return ("Doi_Mizo_%s_D%.2f" % ("F" if sides == 2 else "E", d)), n


def mizo_K():
    """**型 K 板蓋の溝(どぶ板)**。底 0.30・深 0.20・杉板の側(t0.03・2枚)・横に並べた蓋板 0.24 × 0.60 × 4枚。
    蓋の天端 = 路面(Y=0)。杭は駒ごとに左右1本(json は 1間ピッチ ── 1m の駒で割れないので 1m)。"""
    k = K["K"]
    rng = random.Random(5330600)
    bw, dep, st = k["bottomW"] / 2.0, k["depth"], k["side"]["t"]
    lw, ll = k["lid"]["w"], k["lid"]["len"]
    lt = 0.03
    surface([(-bw - st, -dep), (0.0, -dep), (bw + st, -dep)], [SOIL, SOIL], uvfn=uv_ground)
    for s in (-1, 1):
        Xc = s * (bw + st * 0.5)
        hb = (dep - lt) / 2.0
        for j in range(2):
            board(Xc, -dep + hb * (j + 0.5), 0.0, st, hb - 0.004, 2 * HALF, 'side')
        kui(s * (bw - 0.03), -lt - 0.005, rng.uniform(-0.05, 0.05))
    n = int(round(2 * HALF / lw))
    pitch = 2 * HALF / n
    for i in range(n):
        Zc = -HALF + pitch * (i + 0.5)
        board(rng.uniform(-0.01, 0.01), -lt * 0.5 - rng.uniform(0, 0.003), Zc, ll, lt,
              pitch - 0.012, 'lid')
    return "Doi_Mizo_K"


# ================================================================ G 桝
def tube(hw, y0, y1, z0, z1, rng, tw=0.08, plug=True):
    """**石樋の短い筒**(口の奥を塞ぐ)。内法 2hw × (y1−y0)、Z z0..z1、奥(z1 側)を塞ぎ石で閉じる。
    ⛔ 口の奥を開けたままにしない ── 地形の下の空が口から見える。"""
    stone(-hw - tw, hw + tw, y0 - tw, y0, z0, z1, rng, ends=False, bev=0.006)
    stone(-hw - tw, hw + tw, y1, y1 + tw, z0, z1, rng, ends=False, bev=0.006)
    stone(-hw - tw, -hw, y0, y1, z0, z1, rng, ends=False, bev=0.006)
    stone(hw, hw + tw, y0, y1, z0, z1, rng, ends=False, bev=0.006)
    if plug:
        zz = (z1, z1 + tw) if z1 > z0 else (z1 - tw, z1)
        stone(-hw - tw, hw + tw, y0 - tw, y1 + tw, zz[0], zz[1], rng, ends=False, bev=0.006)


def masu(kind):
    """**型 G1 / G2 石の桝**(切石4枚組・天端 +0.05)。ピボット = 桝の芯・地盤の高さ。+Z = 吐き口の側。
    G1: 内法 0.45 角・底の天端 −0.75(吐き口の底 −0.60 − 溜め 0.15)・+Z に吐き口(埋樋の口 0.30 角)。
        ⛔ 入口の切り欠きは焼かない ── 溝の付かない口から地形の下の空が抜ける(1回目のレンダで見えた)。
        溝の駒は桝の外の面へ突き付ける(溝の端の小口は桝の石で塞がる)。
    G2: 内法 0.90 角・底の天端 −1.80(json levels masuTop 26.65 − masuBottom 24.8)・石蓋2枚(0.9 × 0.5 × 0.15)
        を Z 側の壁の段で受け、−Z の蓋に切り欠き 0.20 角・その下の壁の天端を −0.25 まで欠く(D5 の溝が入る口)。
    G3: 内法 0.90 角・外 1.20 角・底と吐き口は G1 の取り方(底の天端 −0.75)・石蓋2枚(0.9 × 0.5 × 0.20)を
        G2 と同じ Z 側の壁の段で受ける・切り欠き無し(普請方 第45巡・溝 E を受ける中の桝)。
    吐き口の奥は石樋の短い筒 0.40 + 塞ぎ石(埋樋の本体は焼かない)。"""
    g = K.get(kind) or _KATA_PENDING[kind]
    rng = random.Random(5330700 + {"G1": 1, "G2": 2, "G3": 3}[kind])
    a = g["inner"][0] / 2.0
    t = g["wall"]["t"]
    top = g["topAbove"]
    o = a + t
    floor = G1_FLOOR if kind in ("G1", "G3") else top - 1.85
    yb = floor - 0.15
    stone(-o, o, yb, floor, -o, o, rng, ends=False)                     # 底石
    out_bot = floor + 0.15
    hw = 0.15
    if kind == "G1":
        for s in (-1, 1):                                                 # X 側の壁(Z 全長)
            X0, X1 = (-o, -a) if s < 0 else (a, o)
            stone(X0, X1, floor, top, -o, o, rng, ends=False)
        stone(-a, a, floor, top, -o, -a, rng, ends=False)                 # −Z の壁(溝が突き付く面)
        stone(-a, a, floor, out_bot, a, o, rng, ends=False)               # +Z の壁(吐き口を避けて積む)
        stone(-a, -hw, out_bot, out_bot + 0.30, a, o, rng, ends=False)
        stone(hw, a, out_bot, out_bot + 0.30, a, o, rng, ends=False)
        stone(-a, a, out_bot + 0.30, top, a, o, rng, ends=False)
        tube(hw, out_bot, out_bot + 0.30, o, o + 0.40, rng)
        return "Doi_Masu_G1"
    # ---- G2 / G3
    lid = g["lid"]
    lt = lid["t"]
    ledge = top - lt
    for s in (-1, 1):                      # X 側の壁(全長)
        X0, X1 = (-o, -a) if s < 0 else (a, o)
        stone(X0, X1, floor, top, -o, o, rng, ends=False)
    lz = lid["size"][1]                    # 0.5 ⇒ 蓋2枚で Z ±0.5、壁の段 a..0.5 で受ける
    if kind == "G3":                       # 切り欠き無し: −Z の壁は段まで控え全部・その上は段の外だけ
        stone(-a, a, floor, ledge, -o, -a, rng, ends=False)
        stone(-a, a, ledge, top, -o, -lz, rng, ends=False)
    nx, nz = lid["notch"] if kind == "G2" else (0.0, 0.0)
    # −Z の壁: 段(蓋の受け)の高さまでを控え全部で・その上は外の 0.10 だけ。切り欠きは −0.25 まで
    if kind == "G2":
        prism([(-a, floor), (a, floor), (a, ledge), (nx / 2, ledge), (nx / 2, -0.25), (-nx / 2, -0.25), (-nx / 2, ledge), (-a, ledge)],
              'z', -o, -a, rng)
        stone(-a, -nx / 2, ledge, top, -o, -lz, rng, ends=False)
        stone(nx / 2, a, ledge, top, -o, -lz, rng, ends=False)
    # +Z の壁: 吐き口(0.30 角)を避けて積む
    stone(-a, a, floor, out_bot, a, o, rng, ends=False)
    stone(-a, -0.15, out_bot, out_bot + 0.30, a, o, rng, ends=False)
    stone(0.15, a, out_bot, out_bot + 0.30, a, o, rng, ends=False)
    stone(-a, a, out_bot + 0.30, ledge, a, o, rng, ends=False)
    stone(-a, a, ledge, top, lz, o, rng, ends=False)
    tube(hw, out_bot, out_bot + 0.30, o, o + 0.40, rng)
    if kind == "G3":                       # 蓋2枚(切り欠き無し)
        stone(-a, a, ledge, top, -lz, -0.004, rng, ends=False)
        stone(-a, a, ledge, top, 0.004, lz, rng, ends=False)
        return "Doi_Masu_G3"
    # 蓋2枚(−Z の蓋に切り欠き)
    prism([(-a, -lz), (-nx / 2, -lz), (-nx / 2, -lz + nz), (nx / 2, -lz + nz), (nx / 2, -lz), (a, -lz), (a, -0.004), (-a, -0.004)],
          'y', ledge, top, rng)
    stone(-a, a, ledge, top, 0.004, lz, rng, ends=False)
    return "Doi_Masu_G2"


# ================================================================ H 石組の段落ち
def danochi(rise):
    """**型 H 石組の段落ち 1段**(内法 0.60・野面石の側・平石の段鼻と水叩き)。駒の長さ 0.50。
    ピボット = **段鼻の線の芯・段鼻の天端(上の底)**。駒は Z −0.12(段鼻)… +0.38(水叩きの終わり)。
    rise = 0 は**平らな駒**(Z −0.25..+0.25・ピボット = 中心・底の天端)── 踏面の残りを埋める。"""
    h = K["H"]
    rng = random.Random(5330800 + int(rise * 1000))
    hi = h["innerW"] / 2.0
    t = 0.10
    if rise <= 1e-6:
        z0, z1 = -H_LEN / 2, H_LEN / 2
        js = [0.22]

        def mk(r0, r1, wrap):
            run_stone(r0, r1, wrap, -hi - 0.05, hi + 0.05, -t, -rng.uniform(0, 0.004) if wrap is None else -0.002,
                      rng, length=H_LEN, uvo=(PLAIN[0] + 0.01, PLAIN[1] + 0.02) if wrap else None)
        course(js, mk, length=H_LEN)
        beds = [(z0, z1, 0.0)]
    else:
        z0, z1 = -0.12, 0.38
        stone(-hi - 0.05, hi + 0.05, -t, 0.0, -0.12, 0.03, rng, ends=False)          # 段鼻(0.03 出す)
        stone(-hi, hi, -rise + 0.002, -t - 0.004, -0.12, -0.005, rng, ends=False)     # 蹴込みの面(水叩きに載る)
        # ⚠ 水叩きは蹴込みの下へ潜らせる ── 段鼻の線から始めると蹴込みの足元に 0.04 の隙が開き、
        #   地形の下の空が抜けた(1回目のレンダ)
        stone(-hi - 0.05, hi + 0.05, -rise - t, -rise, -0.12, 0.20, rng, ends=False)  # 水叩き
        stone(-hi - 0.05, hi + 0.05, -rise - t, -rise - 0.003, 0.212, z1, rng, ends=False)
        beds = [(z0, 0.0, 0.0), (0.0, z1, -rise)]
    # 側の野面石積み(各側・2段)。⛔ 実岩を立てて並べない ── 岩と岩の間から地形の下の空が抜け、
    #   丈 0.6 の岩が立石に見えた(1回目のレンダ)。⭕ 面を揺らし稜を大きく丸めた石を2段に積み、天端を続ける。
    segs = [(z0, 0.0, 0.0), (0.0, z1, -rise)] if rise > 1e-6 else [(z0, z1, 0.0)]
    for s in (-1, 1):
        for (za, zb, yb) in segs:
            ybot, ytop = yb - t - 0.06, yb + H_WALL_TOP
            ym = ybot + (ytop - ybot) * rng.uniform(0.45, 0.55)
            for (y0, y1) in ((ybot, ym - 0.004), (ym + 0.004, ytop - rng.uniform(0.0, 0.02))):
                L = zb - za
                cuts = [za, zb]
                if L > 0.30:
                    cuts = [za, za + L * rng.uniform(0.40, 0.60), zb]
                for k in range(len(cuts) - 1):
                    ca = cuts[k] + (GAP if k > 0 else 0.0)
                    cb = cuts[k + 1] - (GAP if k < len(cuts) - 2 else 0.0)
                    inset = rng.uniform(0.0, 0.035)
                    if s < 0:
                        X0, X1 = -hi - 0.30, -hi - inset
                    else:
                        X0, X1 = hi + inset, hi + 0.30
                    stone(X0, X1, y0, y1, ca, cb, rng, bev=0.028, ends=False)
    return "Doi_DanOchi_R%.2f" % rise


# ================================================================ I 張り石の落とし・水叩き
def hari_otoshi(rise, nori):
    """**型 I 張り石の落とし 1段**(法面を縦に)。幅 0.60・平石張り t0.12・両脇に縁石(w0.12・平石の天端 +0.06)。
    踏面 T = 法 × rise(1:1.5 の盛なら 1.5 × rise)。ピボット = **段鼻の線の芯・上の平石の天端**。
    駒は Z −nose … T − nose(nose = min(0.15, T/2)の段鼻をこの駒が持ち、次の駒の段鼻が踏面の終わりに来る)。"""
    i_ = K["I"]
    rng = random.Random(5330900 + int(rise * 1000) + int(nori * 10))
    hi = i_["w"] / 2.0
    t = (i_["pave"]["tMin"] + i_["pave"]["tMax"]) * 0.5 - 0.005
    T = nori * rise
    nose = min(0.15, T * 0.5)
    stone(-hi, hi, -t, 0.0, -nose, -0.003, rng, ends=False)                      # 段鼻(上の平石)
    if rise > t + 0.01:
        stone(-hi, hi, -rise - 0.04, -t - 0.004, -nose, -0.003, rng, ends=False)  # 蹴込み
    stone(-hi, hi, -rise - t, -rise, 0.003, T - nose, rng, ends=False)           # 踏面の平石
    cw, ca = 0.12, 0.06
    for s in (-1, 1):
        X0, X1 = (-hi - cw, -hi - 0.004) if s < 0 else (hi + 0.004, hi + cw)
        stone(X0, X1, -rise - 0.20, ca, -nose, 0.0, rng, ends=False)
        stone(X0, X1, -rise - 0.20, -rise + ca, 0.004, T - nose, rng, ends=False)
    return "Doi_HariOtoshi_R%.2f_N%.1f" % (rise, nori)


def mizutataki():
    """**法尻の玉石の水叩き** 0.90 × 0.90・窪み 0.10(json I.apron)。ピボット = 芯・地盤の高さ。肩に土の皮。"""
    ap = K["I"]["apron"]
    rng = random.Random(5330950)
    a = ap["size"][0] / 2.0
    dip = ap["dip"]

    def fy(X, Z):
        q = max(abs(X) / a, abs(Z) / a)
        q = min(1.0, (abs(X / a) ** 4 + abs(Z / a) ** 4) ** 0.25)
        return -dip * (1.0 - q * q) - 0.01

    heightfield(lambda X, Z: fy(X, Z) if max(abs(X), abs(Z)) <= a else
                -0.01 + 0.014 * min(1.0, (max(abs(X), abs(Z)) - a) / 0.05) - 0.044 * max(0.0, (max(abs(X), abs(Z)) - a - 0.05) / (SKIRT - 0.05)),
                -a - SKIRT, a + SKIRT, -a - SKIRT, a + SKIRT, 24, 24)
    tama_field(rng, -a + 0.04, a - 0.04, -a + 0.04, a - 0.04, 0.09, 0.15, lambda X, Z: fy(X, Z) - 0.01,
               hk=0.5, cut_below=0.03, stems=("s_rock_01", "s_rock_02", "s_rock_04", "s_rock_05"), ycap=-0.01)
    return "Doi_Mizutataki_%.2f" % ap["size"][0]


# ================================================================ J 玉石の受け
def tama_uke():
    """**型 J 玉石の受け** 2 × 3間(X 3.636 × Z 5.454)・窪み 0.30・玉石 0.15〜0.30・縁は野面石を半ば埋める。
    溢れ口 = **+Z の辺の芯**(縁石を 0.10 下げ、平たい石を 0.6 幅で並べる)。ピボット = 芯・縁の地盤の高さ。"""
    j = K["J"]
    rng = random.Random(5331000)
    ax, az = 1.818, 2.727
    ix, iz = ax - 0.22, az - 0.22
    dip = j["dip"]

    def fy(X, Z):
        q = min(1.0, ((abs(X) / ix) ** 4 + (abs(Z) / iz) ** 4) ** 0.25)
        y = -dip * (1.0 - q * q)
        # 溢れ口へ向けて縁を 0.10 下げる
        if Z > iz * 0.6 and abs(X) < 0.5:
            y = min(y, -j["overflow"]["curbDrop"] * max(0.0, (Z - iz * 0.6) / (iz * 0.4)) * (1 - abs(X) / 0.5))
        return y

    def fy_all(X, Z):
        if abs(X) <= ix and abs(Z) <= iz:
            return fy(X, Z) - 0.02
        e = max(abs(X) - ix, abs(Z) - iz)
        return -0.02 - 0.03 * min(1.0, e / (ax - ix + SKIRT))
    heightfield(fy_all, -ax - SKIRT, ax + SKIRT, -az - SKIRT, az + SKIRT, 32, 46)
    smin, smax = j["stoneDMin"], j["stoneDMax"]
    tama_field(rng, -ix + 0.10, ix - 0.10, -iz + 0.10, iz - 0.10, smin, smax, lambda X, Z: fy(X, Z) - 0.03,
               hk=0.5, cut_below=0.05, stems=("s_rock_01", "s_rock_02", "s_rock_04", "s_rock_05", "s_rock_06"),
               inside=lambda X, Z: ((abs(X) / ix) ** 4 + (abs(Z) / iz) ** 4) < 0.92, ycap=-0.02)
    # 縁の野面石(周に沿って)
    per = []
    step = 0.40
    for side in range(4):
        if side in (0, 1):                  # ±X の長辺
            s = -1 if side == 0 else 1
            n = int(2 * iz / step)
            for k in range(n + 1):
                per.append((s * (ix + 0.06), -iz + 2 * iz * k / n))
        else:
            s = -1 if side == 2 else 1
            n = int(2 * ix / step)
            for k in range(1, n):
                per.append((-ix + 2 * ix * k / n, s * (iz + 0.06)))
    for (X, Z) in per:
        low = Z > iz and abs(X) < 0.45
        sz = rng.uniform(0.30, 0.42) if not low else rng.uniform(0.28, 0.34)
        h = sz * (0.6 if not low else 0.35)
        top = 0.04 - rng.uniform(0.0, 0.02) - (j["overflow"]["curbDrop"] if low else 0.0)
        rock(rng.choice(("s_rock_03", "s_rock_05", "s_rock_06", "s_rock_02")), sz, h, X, top, Z,
             rng.uniform(0, math.tau))
    return "Doi_TamaUke_2x3ken"


# ================================================================ L 蓋石・M 暗渠の口・N 水抜き・O 水切り
def futaishi(length, t):
    """**型 L 蓋石**。長さ = 溝の外幅 + 0.30(両側 0.15 掛かり)を X・見込み 0.50 を Z・厚 t。
    ピボット = **蓋の芯・天端**(Y = 路面を直に入れる。json topTol 0.02)。"""
    rng = random.Random(5331100 + int(length * 100) + int(t * 1000))
    stone(-length / 2, length / 2, -t, 0.0, -L_W / 2, L_W / 2, rng, bev=0.015, ends=False, nobot=False)
    return "Doi_Futaishi_L%.2f_T%.2f" % (length, t)


def ankyo_kuchi(beak=True):
    """**型 M 石の暗渠の口**(内法 0.30 角)。面石を口の周りに避けて積み、奥へ 0.60 の石樋の短い筒と奥の塞ぎ石。
    beak=True: 吐口(口の下に**切石の嘴**を +Z へ 0.15 出す)/ False: 呑み口(嘴なし)。
    ピボット = **口の底(管底)の芯・面石の見え面**。+Z = 口の外(吐口なら下流・呑み口なら上流の溝の側)。"""
    m = K["M"]
    rng = random.Random(5331200 + (1 if beak else 0))
    w, hgt = m["inner"]
    hw = w / 2.0
    ft = 0.25                      # 面石の控え
    X0, X1, Yb, Yt = -0.45, 0.45, -0.25, hgt + 0.25
    stone(X0, -hw, Yb, Yt, -ft, 0.0, rng, ends=False)
    stone(hw, X1, Yb, Yt, -ft, 0.0, rng, ends=False)
    stone(-hw, hw, hgt, Yt, -ft, 0.0, rng, ends=False)
    stone(-hw, hw, Yb, 0.0, -ft, 0.0, rng, ends=False)
    tw = 0.08                      # 筒の石の厚み
    zb = -ft - 0.60
    stone(-hw - tw, hw + tw, -tw, 0.0, zb, -ft, rng, ends=False, bev=0.006)
    stone(-hw - tw, hw + tw, hgt, hgt + tw, zb, -ft, rng, ends=False, bev=0.006)
    stone(-hw - tw, -hw, 0.0, hgt, zb, -ft, rng, ends=False, bev=0.006)
    stone(hw, hw + tw, 0.0, hgt, zb, -ft, rng, ends=False, bev=0.006)
    stone(-hw - tw, hw + tw, -tw, hgt + tw, zb - 0.08, zb, rng, ends=False, bev=0.006)
    if beak:
        stone(-hw - 0.05, hw + 0.05, -0.08, -0.002, 0.0, m["outlet"]["project"], rng, ends=False, bev=0.012)
        return "Doi_Ankyo_Hakiguchi"
    return "Doi_Ankyo_Nomikuchi"


def mizunuki():
    """**型 N 塀の水抜き**(内法 0.24 角・土台を抜く切石の口・外へ嘴 0.10)。
    通し石 0.54(X)× 0.52(Y)× 控え 0.90(Z・塀の厚みを抜く)を口の周り4個で組む。
    ピボット = **口の底の芯・塀の外の面**(石は −Z へ 0.90)。+Z = 塀の外(落とし先)。"""
    n = K["N"]
    rng = random.Random(5331300)
    w, hgt = n["inner"]
    hw = w / 2.0
    X0, X1, Yb, Yt, Z0 = -0.27, 0.27, -0.12, hgt + 0.16, -0.90
    stone(X0, -hw, Yb, Yt, Z0, 0.0, rng, ends=False)
    stone(hw, X1, Yb, Yt, Z0, 0.0, rng, ends=False)
    stone(-hw, hw, hgt, Yt, Z0, 0.0, rng, ends=False)
    stone(-hw, hw, Yb, 0.0, Z0, 0.0, rng, ends=False)
    stone(-hw - 0.05, hw + 0.05, -0.06, -0.002, 0.0, n["outerBeak"], rng, ends=False, bev=0.01)
    return "Doi_Mizunuki"


def mizukiri(length):
    """**型 O 水切り石**(坂の頭を斜めに横切る)。長さ = 坂の幅 + 0.30 を X・幅 0.20 を Z・天端 +0.05。
    2本の切石を継ぐ。ピボット = 芯・路面の高さ。斜め 60° は据える側の yaw(+X の端を坂の脇へ)。"""
    o = K["O"]
    rng = random.Random(5331400 + int(length * 100))
    hw = o["w"] / 2.0
    top = o["topAbove"]
    a = rng.uniform(0.44, 0.56) * length - length / 2
    stone(-length / 2, a - GAP, top - 0.25, top, -hw, hw, rng, bev=0.015, ends=False)
    stone(a + GAP, length / 2, top - 0.25, top - 0.004, -hw, hw, rng, bev=0.015, ends=False)
    return "Doi_Mizukiri_L%.2f" % length


# ================================================================ 一覧
def _mz(fn, *a):
    def f():
        r = fn(*a)
        return r[0] if isinstance(r, tuple) else r
    return f


JOBS = []
for d in A_DEPTHS:
    JOBS.append(("A", _mz(mizo_A, d), "mizo"))
for h in KASA_HS:
    JOBS.append(("AK", _mz(kasa_A, h), "kasa"))
for d in A_DEPTHS:
    JOBS.append(("AF", _mz(mizo_A, d, True, False), "fuchi"))
    JOBS.append(("AH", _mz(mizo_A, d, False, True), "fuchi"))
    JOBS.append(("AFH", _mz(mizo_A, d, True, True), "fuchi"))
JOBS.append(("B", _mz(mizo_B), "mizo"))
for d in C_DEPTHS:
    JOBS.append(("C", _mz(mizo_C, d), "mizo"))
for d in D_DEPTHS:
    JOBS.append(("D", _mz(mizo_D, d), "mizo"))
for d in E_DEPTHS:
    JOBS.append(("E", _mz(mizo_E, d, 1), "mizo"))
    JOBS.append(("F", _mz(mizo_E, d, 2), "mizo"))
JOBS.append(("K", _mz(mizo_K), "mizo"))
JOBS.append(("G1", _mz(masu, "G1"), "masu"))
JOBS.append(("G2", _mz(masu, "G2"), "masu"))
JOBS.append(("G3", _mz(masu, "G3"), "masu"))
JOBS.append(("H", _mz(danochi, 0.0), "dan"))
for r in H_RISES:
    JOBS.append(("H", _mz(danochi, r), "dan"))
for nori in I_NORI:
    for r in I_RISES:
        JOBS.append(("I", _mz(hari_otoshi, r, nori), "dan"))
JOBS.append(("I", _mz(mizutataki), "dan"))
JOBS.append(("J", _mz(tama_uke), "uke"))
LID_LEN = {"A": K["A"]["outerW"] + 0.30,
           "D": (K["D"]["bottomW"] + 2 * D_BATTER * K["D"]["depthMax"]) + 0.30,
           "E": (K["E"]["innerW"] + K["E"]["wall"]["depth"]) + 0.30,
           "F": (K["E"]["innerW"] + 2 * K["E"]["wall"]["depth"]) + 0.30}
for L in sorted(set(round(v, 2) for v in LID_LEN.values())):
    for t in (K["L"]["tFoot"], K["L"]["tHorse"]):
        JOBS.append(("L", _mz(futaishi, L, t), "kuchi"))
JOBS.append(("M", _mz(ankyo_kuchi, True), "kuchi"))
JOBS.append(("M", _mz(ankyo_kuchi, False), "kuchi"))
JOBS.append(("N", _mz(mizunuki), "kuchi"))
for L in sorted(set(round(RAMPS[n]["w"] + 0.30, 2) for n in ("R_Tsuyomon", "R_Tomomachi"))):
    JOBS.append(("O", _mz(mizukiri, L), "kuchi"))

GROUPS = {"mizo": "ABCDEFK", "kasa": ("AK",), "fuchi": ("AF", "AH", "AFH"), "masu": ("G1", "G2", "G3"), "dan": "HI", "uke": "J", "kuchi": "LMNO"}


# ================================================================ 結線とレンダ
def hook():
    DN.hook()
    base = os.path.join(FJG_TEX, "Ground_Gravel_01", "T_FJG_Ground_Gravel_01_Albedo.png")
    m = bpy.data.materials.get(GRAVEL)
    if m is not None and os.path.exists(base):
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is not None:
            for sock in ('Alpha', 'Base Color'):
                for lk in list(b.inputs[sock].links):
                    nt.links.remove(lk)
            b.inputs['Alpha'].default_value = 1.0
            b.inputs['Roughness'].default_value = 0.95
            img = nt.nodes.new('ShaderNodeTexImage')
            img.image = bpy.data.images.load(base, check_existing=True)
            nt.links.new(img.outputs['Color'], b.inputs['Base Color'])


def _ground_strips(o, hole):
    """検め用の地面(Unity Y=0)。`hole` = (x0, x1, z0, z1) の穴を開けた4枚の板(書き出さない)。"""
    gm = bpy.data.materials.new("_ground_render")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.30, 0.26, 0.20, 1)
    x0, x1, z0, z1 = hole
    R = 4.0
    made = []
    for (a0, a1, b0, b1) in ((-R, x0, -R, R), (x1, R, -R, R), (x0, x1, -R, z0), (x0, x1, z1, R)):
        if a1 - a0 < 1e-4 or b1 - b0 < 1e-4:
            continue
        bpy.ops.mesh.primitive_plane_add(size=1.0)
        g = bpy.context.active_object
        g.scale = (a1 - a0, b1 - b0, 1.0)
        bx, by, _ = u2b((a0 + a1) * 0.5, 0, (b0 + b1) * 0.5)
        g.location = (bx, by, -0.001)
        g.data.materials.append(gm)
        made.append(g)
    return made


def _magenta_sky():
    """カメラの光線にだけマゼンタを見せる(照明は既定の灰青のまま ── 材の色を狂わせない)。"""
    w = bpy.context.scene.world
    nt = w.node_tree
    bg = nt.nodes["Background"]
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
    mg = nt.nodes.new('ShaderNodeBackground')
    mg.inputs[0].default_value = (1, 0, 1, 1)
    lp = nt.nodes.new('ShaderNodeLightPath')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(mg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])


def shots(o, name, hole, tile, kind):
    """⚠ 書き出しの前に撮る。背景はマゼンタ(穴が1画素でも見えたら Unity で空が抜ける)。
    tile=True の溝の駒は前後に写しを2つ並べて継ぎ目を検める。返り値 = 画像の道。"""
    hook()
    os.makedirs(SHOT, exist_ok=True)
    extra = []
    if tile:
        for k in (-1, 1):
            c = o.copy(); c.data = o.data
            c.location = (0.0, -k * 2 * HALF, 0.0)
            bpy.context.scene.collection.objects.link(c)
            c.hide_render = False
            extra.append(c)
    if hole is not None:
        extra += _ground_strips(o, hole if not tile else (hole[0], hole[1], -4.0, 4.0))
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    r = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, 1.0)
    out = []
    cams = [("3d", (c.x + r * 0.9, c.y - r * 1.1, mx.z + r * 1.5), (c.x, c.y, (mn.z + mx.z) * 0.5), None)]
    if tile:
        # 小口(断面)を下流から ── 正投影
        cams.append(("koguchi", (c.x, mn.y - 6.0, (mn.z + mx.z) * 0.5), (c.x, c.y, (mn.z + mx.z) * 0.5),
                     max(mx.x - mn.x, mx.z - mn.z) * 1.5))
    elif hole is None:
        # 口の部材は見え面(+Z = Blender −y)の正面から
        cams.append(("front", (c.x + 0.4, mn.y - 3.0, c.z + 0.6), (c.x, c.y, c.z), None))
    else:
        cams.append(("top", (c.x, c.y + 1e-4, mx.z + r * 4), (c.x, c.y, mx.z), max(mx.x - mn.x, mx.y - mn.y) * 1.3))
    for tag, loc, at, ortho in cams:
        V.studio(loc, at, ortho_scale=ortho, res=(900, 640))
        _magenta_sky()
        p = os.path.join(SHOT, "doihaisui_%s_%s.png" % (name, tag))
        V.render(p)
        out.append(p)
    for e in extra:
        bpy.data.objects.remove(e, do_unlink=True)
    return out


def kasa_shots(o, name):
    """嵩上げ石を型 A(D0.15)の +X の縁石の天端に載せ、前後に写しを並べて撮る(検め用・書き出さない)。
    背景はマゼンタ。地面は道の側(+X の外)を嵩上げ石の天端 −0.02 に、溝の内側の側(−X の外)を A の地盤 0 に。"""
    saved = list(_objs)
    _objs.clear()
    mizo_A(0.15)
    ctx = DN._finish(_objs, "_ctx")
    _objs.clear(); _objs.extend(saved)
    a = K["A"]; c = a["curb"]
    cx = a["innerW"] / 2.0 + c["w"] / 2.0           # +X の縁石の見付の芯
    o.location = Vector(u2b(cx, c["topAbove"], 0.0))
    hook()
    extra = [ctx]
    for k in (-1, 1):
        for src in (o, ctx):
            cc = src.copy(); cc.data = src.data
            cc.location = src.location + Vector((0.0, -k * 1.0, 0.0))
            bpy.context.scene.collection.objects.link(cc)
            cc.hide_render = False
            extra.append(cc)
    mn, mx = V.bbox([o])
    htop = mx.z
    gm = bpy.data.materials.new("_ground_render")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.30, 0.26, 0.20, 1)
    R = 4.0
    xo = cx + c["w"] / 2.0
    for (a0, a1, y) in ((xo, R, htop - 0.02), (-R, -(a["innerW"] / 2.0 + c["w"]), 0.0)):
        bpy.ops.mesh.primitive_plane_add(size=1.0)
        g = bpy.context.active_object
        g.scale = (a1 - a0, 2 * R, 1.0)
        bx, by, _ = u2b((a0 + a1) * 0.5, 0, 0)
        g.location = (bx, by, y - 0.001)
        g.data.materials.append(gm)
        extra.append(g)
    os.makedirs(SHOT, exist_ok=True)
    out = []
    bx, _, _ = u2b(cx, 0, 0)
    # 3d = 溝の内(−X)から外の壁の見え面と天端を / koguchi = 下流からの正投影の断面 / road = 道の側から
    for tag, loc, at, ortho in (("3d", (bx + 1.4, -1.9, 1.3), (bx, 0.0, htop * 0.5), None),
                                ("koguchi", (bx + 0.2, -6.0, htop * 0.4), (bx + 0.2, 0.0, htop * 0.4), 1.2),
                                ("road", (bx - 1.6, -1.5, htop + 0.9), (bx, 0.0, htop * 0.5), None)):
        V.studio(loc, at, ortho_scale=ortho, res=(900, 640))
        _magenta_sky()
        p = os.path.join(SHOT, "doihaisui_%s_%s.png" % (name, tag))
        V.render(p)
        out.append(p)
    for e in extra:
        bpy.data.objects.remove(e, do_unlink=True)
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    return out


def fuchi_shots(o, name):
    """縁石の作り(AF)・吐き口(AH/AFH)の検め(書き出さない)。吐き口は前後に同じ深さの AF / A を継いで並べる
    (AF は自分の写しを並べる)。地面は道の側(+X の外)を天端 −0.40(AF の見せ)/ −0.02(A)に、溝の内の側(−X の外)を天端 −0.02 に。
    背景はマゼンタ(穴が見えたら Unity で空が抜ける)。3d = 道の側から口と外の壁 / koguchi = 下流からの断面 / top = 真上。"""
    fuchi = "_AF" in name
    d = float(name.rsplit("_D", 1)[1])
    nb = None
    if "H_D" in name:
        saved = list(_objs)
        _objs.clear()
        mizo_A(d, fuchi, False)
        nb = DN._finish(_objs, "_nb")
        _objs.clear(); _objs.extend(saved)
    hook()
    extra = [nb] if nb is not None else []
    for k in (-1, 1):
        src = nb if nb is not None else o
        cc = src.copy(); cc.data = src.data
        cc.location = (0.0, -k * 1.0, 0.0)
        bpy.context.scene.collection.objects.link(cc)
        cc.hide_render = False
        extra.append(cc)
    if nb is not None:
        nb.hide_render = True
    a = K["A"]; c = a["curb"]
    xo = a["innerW"] / 2.0 + c["w"]
    top = c["topAbove"]
    road = top - (0.40 if fuchi else 0.02)
    gm = bpy.data.materials.new("_ground_render")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.30, 0.26, 0.20, 1)
    R = 4.0
    for (a0, a1, y) in ((xo, R, road), (-R, -xo, top - 0.02)):
        bpy.ops.mesh.primitive_plane_add(size=1.0)
        g = bpy.context.active_object
        g.scale = (a1 - a0, 2 * R, 1.0)
        bx, by, _ = u2b((a0 + a1) * 0.5, 0, 0)
        g.location = (bx, by, y - 0.001)
        g.data.materials.append(gm)
        extra.append(g)
    os.makedirs(SHOT, exist_ok=True)
    out = []
    bxo, _, _ = u2b(xo, 0, 0)
    for tag, loc, at, ortho in (("3d", (bxo - 1.8, -1.6, 1.1), (0.0, 0.0, -0.15), None),
                                ("koguchi", (0.0, -6.0, -0.15), (0.0, 0.0, -0.15), 1.4),
                                ("top", (0.0, 1e-4, 4.0), (0.0, 0.0, 0.0), 2.4)):
        V.studio(loc, at, ortho_scale=ortho, res=(900, 640))
        _magenta_sky()
        p = os.path.join(SHOT, "doihaisui_%s_%s.png" % (name, tag))
        V.render(p)
        out.append(p)
    for e in extra:
        bpy.data.objects.remove(e, do_unlink=True)
    bpy.context.view_layer.update()
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    words = [a for a in argv if not a.startswith("--")] or ["all"]
    want = set()
    for w in words:
        if w == "all":
            want |= set(k for k, _, _ in JOBS)
        elif w in GROUPS:
            want |= set(GROUPS[w])
        else:
            want.add(w)
    do_render = "--render" in argv
    only = None
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))
    rows = []
    for key, fn, grp in JOBS:
        if key not in want:
            continue
        V.reset()
        _objs.clear(); _PROTO.clear(); _BOARD.clear()
        name = fn()
        if only and name not in only:
            continue
        for p in list(_PROTO.values()) + list(_BOARD.values()):
            if isinstance(p, bpy.types.Object):
                bpy.data.objects.remove(p, do_unlink=True)
        o = DN._finish(_objs, name)
        mn, mx = V.bbox([o])
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        mats = [m.name for m in o.data.materials]
        bad = [m for m in mats if m not in (ROCK, SOIL, GRAVEL, WOOD)]
        row = (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, mx.z, -mx.y, -mn.y, tris, mats)
        rows.append(row)
        print("[haisui] %-30s Unity W(X)=%.3f H(Y)=%.3f D(Z)=%.3f  Y %.3f..%.3f  Z %.3f..%.3f  tri=%d  材=%s%s"
              % (row[:9] + (mats, "  ⛔ 想定外の材 %s" % bad if bad else "")))
        if do_render:
            tile = grp == "mizo"
            hw = (mx.x - mn.x) * 0.5
            # 地面の穴 = 部材の外形(Y=0 の高さで)。溝は走りに通す。桝は天端の外形だけ・口の部材は地面なし
            hole = (-hw, hw, -mx.y, -mn.y)
            if name.startswith("Doi_Masu_"):
                gk = K.get(name[-2:]) or _KATA_PENDING[name[-2:]]
                oo = gk["inner"][0] / 2.0 + gk["wall"]["t"]
                hole = (-oo, oo, -oo, oo)
            elif name.startswith(("Doi_Ankyo", "Doi_Mizunuki")):
                hole = None
            for p in (kasa_shots(o, name) if grp == "kasa" else fuchi_shots(o, name) if grp == "fuchi"
                      else shots(o, name, hole, tile, grp)):
                print("RENDER " + p)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[haisui] 書き出し " + os.path.join(OUT, name + ".fbx"))
    js = os.environ.get("HAISUI_JSON")
    if js:
        with open(js, "w", encoding="utf-8") as f:
            json.dump([dict(name=r[0], W=round(r[1], 3), H=round(r[2], 3), D=round(r[3], 3),
                            y0=round(r[4], 3), y1=round(r[5], 3), z0=round(r[6], 3), z1=round(r[7], 3),
                            tri=r[8], mats=r[9]) for r in rows], f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
