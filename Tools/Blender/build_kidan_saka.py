"""台の石垣(外周の基壇)の**坂なりの駒** ── 天端が勾配 g に沿う城の石垣(EDO-0502 岡部 const.heiLine.kidanCrest)。

    blender --background --python Tools/Blender/build_kidan_saka.py -- --grade 12 --render
        # → Assets/Edo/Models/Kado/Ishigaki_Choku_H0400_GU1200(局所 +Z へ 12% 上がる)
    blender --background --python Tools/Blender/build_kidan_saka.py -- --grade -2.7 [--h 4.5] [--len 1.6]
        # → Ishigaki_Choku_H0400_GD0270(局所 +Z へ下がる)/ 丈違い _H0450_ / 走りを詰めた _L160
    blender --background --python Tools/Blender/build_kidan_saka.py -- --kado 78.367 --s 0.75 --grade 0,2.7 --render
        # → Ishigaki_Kado_78_H0400_S075_GU0000xU0270(素の隅 Ishigaki_Kado_78_H0400_S075 を芯の道のりで剪断)
    blender --background --python Tools/Blender/build_kidan_saka.py -- --tome P 27.15 [--grade 9.04] [--len 1.39]
        # → Ishigaki_Choku_H0400[_GU0904][_L139]_TP136(浅い出隅の留めの版・端を角の二等分の鉛直面で切る・第149巡)
    blender --background --python Tools/Blender/build_kidan_saka.py -- --okabe-tome [--render]
        # 岡部の浅い出隅 10 か所の 18 本と、二つの駒を据えた並べ焼き Screenshots/kidan_tome_P<n>_{me,naname,ue}.png
    blender --background --python Tools/Blender/build_kidan_saka.py -- --okabe [--render]
        # 岡部の一式(練塀の坂なりの勾配 OKABE_GRADES × U/D と、坂に掛かる出隅 OKABE_KADO)

【なぜ要るか】坂なりの区間(≤1/8)で練塀の天端は坂に沿う(Neribei_Saka)が、台の Castle Wall は天端が水平なので
  1.80 ごとの段に割るしかなく、塀の底との間に最大 1.59 の隙と土の楔が見えた(第121巡)。

【作り】素の `Castle Wall`(在庫・材 `stone wall`・38 頂点)を**縦の剪断**で傾ける: Unity 局所で Y += g·Z。
  ・鉛直の線(背・小口・目地の縦)は鉛直のまま・法(1:0.25)は回らない。天端・段の目地・根石の底は勾配に沿う。
  ・剪断は全体で一次なので、同じ勾配の駒を走りの線に沿って何枚どう重ねても**面と天端が一致して閉じる**(隣の駒の面と同じ平面)。
  ・Z 一定の断面は素と同じ形 ⇒ 平らな駒・別の勾配の駒・隅の腕の先と断面がそのまま合う(継ぎ目で天端が折れるだけ)。
  ・⛔ 根石の底だけ水平に残す反らせ方(天端だけ剪断)は採らない: 0.2 の重ねで隣の駒と面が 0.25·g·1.8(12% で 5.6cm)食い違い、
    継ぎ目ごとに縦の筋が出る。根石の深さは天端の線の下 4.0·s(丈違いは --h)で一定。
  ・小口(走りの両端)は素の面のまま閉じている ⇒ 段の所の小口は塞がっている。開いているのは底だけ(素と同じ・地中)。

【局所(Unity)= 素の Castle Wall と同じ】走り Z ∈ [−2.00, 0]・背 X = 0・見え面 −X・天端の前の縁 X = −1.40・天端の幅 1.40・
  面の足 X = −2.40(足元)。**ピボット = 走りの Z = 0 の端・背・その端の足元**。
  天端(Z) = h + g·Z ・根石の底(Z) = g·Z(天端の下 h で一定)。U = 局所 +Z へ上がる / D = 下がる。倍率 s は Vector3.one·s で一様に
  (勾配は一様な倍率で変わらない)。据え: position・yaw は素と同じ / **y = その駒の Z = 0 の端の所の天端の線 − h·s**。

【隅】build_kado.py の素の隅(Ishigaki_Kado_<deg>_H0400_S<s>)を、Neribei の坂の隅と同じく**芯の道のり T** で z += g·T:
  留めの面の上 T = 0(両腕で閉じる)・腕の先は横に水平で T = ∓a(a = 腕 2.0·s)⇒ 腕の先に坂の直線の駒を突き付ければ断面が一致する。
  入りの腕 = 局所 −Z・g = 入り → 折れ点 → 出の走りに沿って上がる +。据えは素の隅と同じ(position = 折れ点 P・yaw = 入りの run・scale 1・
  y = 折れ点の天端 − h·s)。逆の走り(どちらの腕を −Z へ据えるかは PlaceRunKado の yaw の解)は (−g出, −g入) を焼く。
"""
import bpy, bmesh, sys, os, math, json, re, uuid
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_kado as K          # load / normalize / extend_down(main は __name__ で守ってある)

ROOT = V.REPO
CANON = "Assets/Edo/Models/Kado"
OUT = V.out_dir(os.path.join(ROOT, CANON))
SHOTS = os.environ.get("BUZAI_SHOTS", os.path.join(ROOT, "Screenshots"))
SPEC_OUT = os.environ.get("BUZAI_SPEC_OUT")          # 札の置き場を振る(PartSpecs が他の窓の claim 中)
META_TPL = os.path.join(ROOT, CANON, "Ishigaki_Choku_H0450.fbx.meta")   # 材 stone wall の結線済み ⇒ remap 不要
RUN = 2.0                                             # 素の Castle Wall の走り
CREST_W = 1.40; FOOT = 2.40; BATTER = 0.25

# 練塀の坂なりの勾配(Assets/Edo/Models/Neribei/Neribei_Saka_* の名から・2026-10-13)── 絶対値。U/D の両方を焼く
OKABE_GRADES = (0.0104, 0.0107, 0.0118, 0.0122, 0.0134, 0.0145, 0.0270, 0.0293, 0.0303, 0.0433, 0.0497, 0.0567,
                0.0594, 0.0614, 0.0625, 0.0762, 0.0841, 0.0866, 0.0867, 0.0878, 0.0882, 0.0883, 0.0946, 0.0948,
                0.0987, 0.1069, 0.1200, 0.1206, 0.1250,
                0.0621, 0.0757, 0.0858, 0.0872, 0.0895, 0.0903, 0.1041)   # 末尾 7 つは第149巡 S2 の ★(2026-10-16)
# 坂に掛かる台の出隅(≥40°・隅の駒を受ける所)── 練塀の坂の隅 Neribei_Kado_78_G* と同じ頂点 P24(辺23 平ら → 辺24 上り)。
#   (折れ, 倍率, 入り %, 出 %)。どちらの腕を局所 −Z へ据えるかで (0, +g) と (−g, 0) の両方
OKABE_KADO = [(78.367, 0.75, 0.0, 2.70), (78.367, 0.75, -2.70, 0.0), (78.367, 0.75, 0.0, 3.03), (78.367, 0.75, -3.03, 0.0)]


def grade_tag(g):
    """勾配の綴り(EdoAssets.Own.NeribeiGradeTag と同じ): U/D + 万分率 4 桁。"""
    return ("D" if g < 0 else "U") + "%04d" % int(round(abs(g) * 10000))


def write_meta(fbx_path, tpl=META_TPL):
    """新しい FBX に .meta を写す(guid だけ替える ⇒ 材 stone wall は在庫の .mat へ結線済み・remap 不要)。"""
    mp = fbx_path + ".meta"
    if os.path.exists(mp):
        return False
    t = open(tpl, encoding="utf-8").read()
    open(mp, "w", encoding="utf-8").write(re.sub(r"^guid: [0-9a-f]{32}$", "guid: " + uuid.uuid4().hex, t, count=1, flags=re.M))
    return True


def write_json_meta(json_path):
    mp = json_path + ".meta"
    if os.path.exists(mp):
        return
    open(mp, "w", encoding="utf-8").write("fileFormatVersion: 2\nguid: %s\nTextScriptImporter:\n  externalObjects: {}\n"
                                          "  userData: \n  assetBundleName: \n  assetBundleVariant: \n" % uuid.uuid4().hex)


def shear(o, g, y0=0.0):
    """縦の剪断: Unity 局所 +Z(= Blender −y)へ勾配 g で上がる。z += −g·(y − y0)。行列式 1 ⇒ 巻きは変わらない。"""
    M = Matrix(((1, 0, 0, 0), (0, 1, 0, 0), (0, -g, 1, g * y0), (0, 0, 0, 1)))
    o.data.transform(M); o.data.update()


def cut_len(o, L):
    """走りを Blender y ∈ [0, L] に詰める: y = L で切り、素の小口(y = 2.0・法線 +y)を切り口へ移して塞ぐ(柄は小口のまま)。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    cap = [f for f in bm.faces if f.normal.y > 0.99 and abs(f.calc_center_median().y - RUN) < 1e-4]
    if not cap:
        raise SystemExit("[kidan] ⛔ 小口が見つからない")
    g = bmesh.ops.duplicate(bm, geom=cap)
    cv = [e for e in g["geom"] if isinstance(e, bmesh.types.BMVert)]
    cf = set(e for e in g["geom"] if isinstance(e, bmesh.types.BMFace))
    for v in cv:
        v.co.y = L
    others = [e for e in bm.verts[:] + bm.edges[:] + bm.faces[:]
              if not (isinstance(e, bmesh.types.BMFace) and e in cf) and not (isinstance(e, bmesh.types.BMVert) and e in set(cv))
              and not (isinstance(e, bmesh.types.BMEdge) and all(v in set(cv) for v in e.verts))]
    bmesh.ops.bisect_plane(bm, geom=others, dist=1e-6, plane_co=Vector((0, L, 0)), plane_no=Vector((0, 1, 0)),
                           clear_outer=True, clear_inner=False)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(me); bm.free(); me.update()


def open_edges(o):
    """底(z が最も低い帯)の外の開いた辺の数。"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    n = 0
    for e in bm.edges:
        if not e.is_boundary:
            continue
        # 底の辺 = 根石の底の面(z = −g·y + 底)の上
        if all(abs(v.co.z - o["_bot"](v.co)) < 1e-4 for v in e.verts):
            continue
        n += 1
    bm.free()
    return n


def spec_straight(name, g, h, L, src):
    """札(fence)── 作図の値から(Unity 局所・倍率の前)。
    ⚠ この駒の局所は Castle Wall のまま(走り = Z・見え面 = −X)。札の共通の欄(yBottom・faceOut/faceIn・copingOverhang)は
    EdoPartSpec.Measure の読み(足元の水平断面の Z の両端・半分の高さの断面の X の出)と同じ値を入れてある(Verify を通す)── **据えには使わない**。
    据えに使う欄は crest*/root*/run*/face*(下の追加の欄)。"""
    Z0, Z1 = -L, 0.0                       # 走り
    ys = [g * Z0, g * Z1]                  # 根石の底の両端
    yb = min(ys); ytop = max(h + g * Z0, h + g * Z1)
    H = ytop - yb
    # 足元の断面(yb + 0.05)── 根石の底がその下にある走りの範囲
    fy = yb + 0.05
    if abs(g) < 1e-9:
        zs = (Z0, Z1)
    elif g > 0:
        zs = (Z0, min(Z1, Z0 + 0.05 / g))
    else:
        zs = (max(Z0, Z1 + 0.05 / g), Z1)
    zb0 = min(zs); zb1 = max(zs)
    xf = -(FOOT - BATTER * 0.05)           # 足元の断面の面の X(足元から 0.05 上)
    # 半分の高さの断面の面の出: その高さで最も低い素の z の所(天端が一番低い端)
    ym = yb + H * 0.5
    zlow = min(ym - g * Z0, ym - g * Z1)   # 素の高さ(剪断の前)
    zlow = max(0.0, min(h, zlow))
    xmid = -(FOOT - BATTER * zlow)
    coping = max(0.0, xmid - (-FOOT - BATTER * max(0.0, h - 4.0)))
    face_foot = FOOT + BATTER * max(0.0, h - 4.0)
    return {"source": src, "unitScale": 1.0, "yBottom": yb,
            "foot": [{"x": xf, "y": zb0}, {"x": 0.0, "y": zb0}, {"x": 0.0, "y": zb1}, {"x": xf, "y": zb1}],
            "faceOut": zb1, "faceIn": zb0, "copingOverhang": coping, "height": H,
            "frame": "Castle Wall の局所(走り Z・背 X=0・見え面 −X・ピボット = Z=0 の端の背の足元)── 共通の欄は Measure の読みに合わせた値で据えに使わない",
            "grade": g, "gradeAxis": "+Z", "h": h,
            "runZ": [Z0, Z1],
            "crestY": [h + g * Z0, h + g * Z1],       # 天端(走りの両端)= h + g·Z
            "crestFrontX": -CREST_W, "crestBackX": 0.0,
            "rootY": [g * Z0, g * Z1],                # 根石の底(走りの両端)= g·Z(天端の下 h で一定)
            "faceFootX": -face_foot, "batter": BATTER,
            "place": "position・yaw = 素の Castle Wall と同じ / scale = Vector3.one·s / y = (駒の Z=0 の端の天端の線) − h·s"}


def build_straight(g, h=4.0, L=RUN, fresh=True):
    if fresh:
        V.reset()
    o, _ = K.load("ishigaki")
    K.normalize(o, "ishigaki", [])
    if h > 4.0 + 1e-6:
        o = K.extend_down(o, h)
    if L < RUN - 1e-6:
        cut_len(o, L)
    shear(o, g)
    name = "Ishigaki_Choku_H%04d_G%s%s" % (int(round(h * 100)), grade_tag(g), "" if L >= RUN - 1e-6 else "_L%d" % int(round(L * 100)))
    o.name = name; o.data.name = name
    V.set_origin(o, (0, 0, 0))
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    nopen = sum(1 for e in bm.edges if e.is_boundary and not all(abs(v.co.z + g * v.co.y) < 1e-4 for v in e.verts))
    bm.free()
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print("[kidan] %s Unity X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] 面 %d 開いた辺(底のほか) %d"
          % (name, -max(xs), -min(xs), min(zs), max(zs), -max(ys), -min(ys), len(me.polygons), nopen))
    if nopen:
        raise SystemExit("[kidan] ⛔ 底のほかに開いた辺 %d" % nopen)
    path = os.path.join(OUT, name + ".fbx")
    src = "Tools/Blender/build_kidan_saka.py -- --grade %g" % (g * 100) + ("" if h == 4.0 else " --h %g" % h) + ("" if L >= RUN - 1e-6 else " --len %g" % L)
    spec = spec_straight(name, g, h, L, src)
    spec["prefab"] = CANON + "/" + name + ".fbx"
    if SPEC_OUT:
        V.SPEC_DIR = SPEC_OUT
    jp = V.write_spec(path, dict(spec, kind="fence"))
    write_json_meta(jp)
    V.export_fbx([o], path, kind="fence")
    write_meta(path)
    print("[kidan] wrote %s" % path)
    return o, path


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [x for x in bpy.data.objects if x not in before]
    ms = [x for x in new if x.type == 'MESH']
    V.sel(ms); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for x in new:
        if x.type != 'MESH':
            bpy.data.objects.remove(x, do_unlink=True)
    return V.join(ms, "src") if len(ms) > 1 else ms[0]


def kado_src(deg, s):
    return "Ishigaki_Kado_%02d%s_H0400%s" % (round(abs(deg)), "" if deg > 0 else "M", "" if s is None or abs(s - 1) < 1e-6 else "_S%03d" % int(round(s * 100)))


def kado_warp(o, deg, a, gA, gB):
    """隅の坂なり(build_neribei.kado_warp と同じ式): 折れ点を 0 とする芯の道のり T で z += g·T。
    入りの腕の側(n·p ≥ 0・腕 +y)は α = y、出の腕の側は留めの面で鏡に写して入りの腕の座標へ。
    留めの面の上 α_m = −tan(h)·x から腕の先 a までを T = ∓a へ一様に配る。"""
    h = math.radians(abs(deg)) * 0.5; sg = 1.0 if deg > 0 else -1.0
    n = Vector((sg * math.sin(h), math.cos(h), 0.0))
    R = Matrix([[(1.0 if i == j else 0.0) - 2.0 * n[i] * n[j] for j in range(3)] for i in range(3)])
    th = math.tan(h)
    on = 0
    for v in o.data.vertices:
        p = v.co.copy()
        if abs(n.dot(p)) < 1e-4:
            on += 1
        if n.dot(p) >= -1e-9:
            q, g, sgn = p, gA, -1.0
        else:
            q, g, sgn = R @ p, gB, 1.0
        ym = -sg * th * q.x
        T = sgn * a * max(0.0, q.y - ym) / max(a - ym, 0.05)
        v.co.z += g * T
    o.data.update()
    return on


def build_kado(deg, s, gIn, gOut):
    V.reset()
    sname = kado_src(deg, s)
    sp = os.path.join(ROOT, CANON, sname + ".fbx")
    if not os.path.exists(sp):
        raise SystemExit("[kidan] ⛔ 素の隅が無い: %s(build_kado.py --part ishigaki --deg %g --h 4 --s %g で先に焼く)" % (sp, deg, s or 1))
    o = import_fbx(sp)
    me = o.data
    ys = [v.co.y for v in me.vertices]
    a = max(ys)                                # 入りの腕の先(= 2.0·s)
    on = kado_warp(o, deg, a, gIn, gOut)
    name = sname + "_G%sx%s" % (grade_tag(gIn), grade_tag(gOut))
    o.name = name; me.name = name
    V.set_origin(o, (0, 0, 0))
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print("[kidan] %s 腕 a=%.3f 留めの面の頂点 %d  Unity X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] 面 %d  腕の先の高さ 入り %.4f / 出 %.4f"
          % (name, a, on, -max(xs), -min(xs), min(zs), max(zs), -max(ys), -min(ys), len(me.polygons), -gIn * a, gOut * a))
    path = os.path.join(OUT, name + ".fbx")
    V.export_fbx([o], path)
    write_meta(path, sp + ".meta")
    print("[kidan] wrote %s" % path)
    return o, path, a


# ---------------------------------------------------------------- 浅い出隅の留めの版(第149巡 2026-10-16)
# 台の Castle Wall の浅い出隅(隅の駒を置かない折れ 1°〜40°)で、頂点に来る端の駒の端を**角の二等分の鉛直面**で切った版。
#   名 = 元の駒の名 + `_T<P|M><切り角×10 の 3 桁>`(例 Ishigaki_Choku_H0400_GU0904_TP080 / 平らは Ishigaki_Choku_H0400_TM136)。
#   P = 局所 Z = 0 の端(ピボットの側)を切る / M = Z = −len の端を切る。切り角 c = 折れ/2。出隅だけ(見え面の側が長い)。
#   切る面(Unity 局所・倍率の前): P 端 Z = −(X + 2.40)·tan c / M 端 Z = −len + (X + 2.40)·tan c
#     ⇒ 足元の前の角(X = −2.40)が素の枠の端(Z = 0 か −len)に残り、背(X = 0)は 2.40·tan c 詰まる。⭐ 枠は素と同じ(はみ出さない)。
#   坂なり(g ≠ 0)は剪断でなく**芯の道のり**で反らす(build_kado の坂の隅と同じ考え・式は warp_tome): 切る面の上で天端が一定・切らない端の断面は直線の駒と一致。
#     切り口の上の天端 = P は h / M は h − g·len(どちらも直線の駒の「Z = 0 の端の天端 = h」の据えと同じ規約)。
#     ⚠ 切り口が背の側で切らない端の小口まで届く短い駒(P35 の L41)は道のりが二つの値を持つ ⇒ 素の剪断(切り口の上の天端は 1.3cm 変わる)。
#   切り口は素の小口の柄の帯(build_ishigaki_kiri と同じ CAP_U/CAP_V)を面の座標で貼る(一点貼りにしない)。
TOME_CAP_U = (0.26, 0.74); TOME_CAP_V = (0.01, 0.74)
# 岡部の浅い出隅 10 か所(S2 の待ち r149/need_versions_s2.txt §2・base_ends.txt)── (頂点, 折れ[°], 前の辺の端の駒 (g, len), 次の辺の端の駒 (g, len))
#   前の辺の端の駒は P 端を、次の辺の端の駒は M 端を切る(岡部の区画は時計回り ⇒ 駒の局所 +Z = 辺の走りの向き)。折れは parcels.json okabe の多角形から。
OKABE_TOME = [
    ("P8", 27.15, (0.0, 2.0), (0.0, 2.0)),
    ("P9", 38.51, (0.0, 2.0), (0.0, 2.0)),
    ("P13", 11.47, (0.0, 2.0), (0.0, 2.0)),
    ("P14", 3.40, (0.0, 2.0), (0.0, 2.0)),
    ("P19", 12.96, (0.0, 2.0), (-0.0625, 2.0)),
    ("P29", 15.99, (0.0904, 2.0), (0.0857, 2.0)),
    ("P31", 12.09, (0.0894, 2.0), (0.0125, 2.0)),
    ("P35", 22.19, (-0.0396, 1.39), (-0.0623, 0.41)),
    ("P39", 18.39, (-0.0870, 2.0), (0.0, 2.0)),
    ("P41", 38.60, (0.0, 2.0), (0.0, 2.0)),
]
# 並べ焼きの両脇の倍率と角の天端(base_ends / s2_basewait の値)
OKABE_TOME_SCENE = {"P8": (0.75, 0.75, 18.82, 18.82), "P9": (0.75, 0.75, 18.87, 18.87), "P13": (1.0, 1.0, 19.60, 19.60),
                    "P14": (1.0, 0.5, 19.60, 19.60), "P19": (0.25, 0.75, 17.70, 18.00), "P29": (0.75, 0.75, 16.90, 16.90),
                    "P31": (0.75, 0.75, 24.05, 24.05), "P35": (0.75, 0.75, 23.56, 23.56), "P39": (0.75, 0.75, 18.06, 16.50),
                    "P41": (0.25, 0.5, 12.60, 12.60)}


def tome_tag(c):
    return "%03d" % int(round(abs(c) * 10))


def tome_name(g, c, end, h=4.0, L=RUN):
    n = "Ishigaki_Choku_H%04d" % int(round(h * 100))
    if abs(g) > 1e-9:
        n += "_G" + grade_tag(g)
    if L < RUN - 1e-6:
        n += "_L%d" % int(round(L * 100))
    return n + "_T%s%s" % (end, tome_tag(c))


def tome_ym(x, c, end, L):
    """切る面の Blender y(Blender x = 見え面へ +・足元の前 x = 2.40)。P: y = (2.4 − x)·t / M: y = L − (2.4 − x)·t。"""
    t = math.tan(math.radians(c))
    return (FOOT - x) * t if end == "P" else L - (FOOT - x) * t


def cut_tome(o, c, end, L):
    """切る面で落とし、面の上の頂点で凸な切り口を張る(素の駒は凸 ⇒ 断面は凸)。切り口の UV は小口の柄の帯。"""
    t = math.tan(math.radians(c))
    # 平面: P は y − (2.4 − x)·t ≥ 0 を残す ⇒ 法線 (t, 1, 0)。M は L − (2.4 − x)·t − y ≥ 0 を残す ⇒ 法線 (t, −1, 0)… を外向きに
    if end == "P":
        nrm = Vector((t, 1.0, 0.0)).normalized(); co = Vector((FOOT, 0.0, 0.0)); keep_pos = True
    else:
        nrm = Vector((-t, 1.0, 0.0)).normalized(); co = Vector((FOOT, L, 0.0)); keep_pos = False
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6, plane_co=co, plane_no=nrm,
                           clear_outer=not keep_pos, clear_inner=keep_pos)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    #   浅い切り角(1.7°)では素の小口が足元の前の角で面に接し、面の上に小口の欠片が残る ⇒ 面の上に載り切った面を消してから張る
    pd = lambda v: abs((v.co - co).dot(nrm))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(pd(v) < 5e-5 for v in f.verts)], context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    on = [v for v in bm.verts if abs((v.co - co).dot(nrm)) < 5e-5]
    tv = Vector((nrm.y, -nrm.x, 0.0))
    cen = sum((v.co for v in on), Vector()) / len(on)
    on.sort(key=lambda v: math.atan2((v.co - cen).z, (v.co - cen).dot(tv)))
    uniq = []
    for v in on:
        if not uniq or (uniq[-1].co - v.co).length > 1e-5:
            uniq.append(v)
    if len(uniq) > 2 and (uniq[0].co - uniq[-1].co).length < 1e-5:
        uniq.pop()
    f = bm.faces.new(uniq)
    bm.normal_update()
    outward = -nrm if keep_pos else nrm
    if f.normal.dot(outward) < 0:
        f.normal_flip()
    f.material_index = 0
    ss = [(l.vert.co - cen).dot(tv) for l in f.loops]
    s0, s1 = min(ss), max(ss)
    k = min((TOME_CAP_U[1] - TOME_CAP_U[0]) / max(1e-6, (s1 - s0) * 0.25 / CREST_W), (TOME_CAP_V[1] - TOME_CAP_V[0]) / (4.0 * 0.25))
    for l, s in zip(f.loops, ss):
        l[uvl].uv = (TOME_CAP_U[0] + (s - s0) * 0.25 / CREST_W * k, TOME_CAP_V[0] + l.vert.co.z * 0.25 * k)
    bm.to_mesh(me); bm.free(); me.update()
    return len(uniq)


def warp_tome(o, g, c, end, L):
    """坂なり: Blender z に足す量。直線の駒(z += −g·y)と切らない端で一致し、切り口の上で一定。
    P: −g·L·(y − ym)/(L − ym)(切り口 0・y = L で −g·L)/ M: −g·L·y/ym(y = 0 で 0・切り口 −g·L)。"""
    ymb = tome_ym(0.0, c, end, L)
    if (end == "M" and ymb <= 1e-6) or (end == "P" and ymb >= L - 1e-6):
        #   切り口が背の側で切らない端の小口まで届く短い駒(P35 の L41)── 道のりは切り口と端の小口の交わる所で二つの値を持つ ⇒ 素の剪断
        shear(o, g)
        return False
    for v in o.data.vertices:
        ym = tome_ym(v.co.x, c, end, L)
        if end == "P":
            den = L - ym
            r = (v.co.y - ym) / den if den > 1e-6 else 1.0
        else:
            r = v.co.y / ym if ym > 1e-6 else 1.0
        v.co.z += -g * L * max(0.0, min(1.0, r))
    o.data.update()
    return True


def _section(tris, y):
    pts = []
    for tr in tris:
        for i in range(3):
            a, b = tr[i], tr[(i + 1) % 3]
            if (a[1] - y) * (b[1] - y) < 0:
                u = (y - a[1]) / (b[1] - a[1]); pts.append(tuple(a[k] + (b[k] - a[k]) * u for k in range(3)))
            elif abs(a[1] - y) < 1e-7:
                pts.append(a)
    return pts


def _hull(p2):
    p2 = sorted(set((round(x, 6), round(z, 6)) for x, z in p2))
    if len(p2) < 3:
        return p2
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in p2:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(p2):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def spec_tome(o, name, g, c, end, h, L, src, warped=True):
    """札(fence)。据えに使うのは tome* と crest*/runZ(作図の値)。共通の欄(yBottom・foot・faceOut/faceIn・copingOverhang)は
    EdoPartSpec.Measure と同じ手続き(足元 +0.05 / 半分の高さの断面)を Python で写した読み ── 据えに使わない(spec_straight と同じ扱い)。"""
    me = o.data; me.calc_loop_triangles()
    U = lambda v: (-v.co.x, v.co.z, -v.co.y)
    tris = [[U(me.vertices[i]) for i in lt.vertices] for lt in me.loop_triangles]
    ys = [p[1] for tr in tris for p in tr]; xs = [p[0] for tr in tris for p in tr]
    yb, yt = min(ys), max(ys); x0, x1 = min(xs), max(xs)
    foot = _section(tris, yb + 0.05)
    hull = _hull([(p[0], p[2]) for p in foot])
    mid = _section(tris, yb + (yt - yb) * 0.5)
    coping = max(0.0, max(min(p[0] for p in mid) - x0, x1 - max(p[0] for p in mid))) if mid else 0.0
    t = math.tan(math.radians(c))
    if end == "P":
        plane = "Z = −(X + 2.40)·tan c(足元の前の角 X=−2.40 が Z=0・背 X=0 は Z=−2.40·tan c)"
        cf = {"x": -CREST_W, "y": h, "z": -1.0 * t}; crest_miter = h; crest_far = h - g * L
    else:
        plane = "Z = −len + (X + 2.40)·tan c(足元の前の角が Z=−len・背は Z=−len+2.40·tan c)"
        cf = {"x": -CREST_W, "y": h - g * L, "z": -L + 1.0 * t}; crest_miter = h - g * L; crest_far = h
    if not warped:   # 素の剪断(短い駒)── 切り口の上の天端は一定でない: 天端の前の角の所の値
        cf["y"] = h + g * cf["z"]; crest_miter = cf["y"]
    return {"source": src, "unitScale": 1.0, "yBottom": yb, "height": yt - yb,
            "foot": [{"x": a, "y": b} for a, b in hull],
            "faceOut": max(p[2] for p in foot) if foot else 0.0, "faceIn": min(p[2] for p in foot) if foot else 0.0,
            "copingOverhang": coping,
            "frame": "Castle Wall の局所(走り Z・背 X=0・見え面 −X・ピボット = Z=0 の端の背の足元)── 共通の欄は Measure の読みで据えに使わない",
            "grade": g, "gradeAxis": "+Z", "h": h, "runZ": [-L, 0.0],
            "tomeEnd": end, "tomeCutDeg": c, "tomeTurnDeg": 2 * c, "tomePlane": plane,
            "tomeFootCorner": {"x": -FOOT, "z": 0.0 if end == "P" else -L},
            "tomeCrestFrontCorner": cf,
            "crestOnMiter": crest_miter, "crestFarEnd": crest_far, "crestConstOnMiter": bool(warped),
            "crestFrontX": -CREST_W, "crestBackX": 0.0, "faceFootX": -FOOT, "batter": BATTER,
            "place": "yaw・倍率は直線の駒と同じ / 切り口の面を角の鉛直な二等分の面(両脇の天端の前の縁の線の交点を通る)へ: "
                     "tomeCrestFrontCorner を交点へ・y = 角の天端 − crestOnMiter·s(坂なりは切り口の上で天端が一定)"}


def build_tome(g, c, end, h=4.0, L=RUN):
    V.reset()
    o, _ = K.load("ishigaki")
    K.normalize(o, "ishigaki", [])
    if h > 4.0 + 1e-6:
        o = K.extend_down(o, h)
    if L < RUN - 1e-6:
        cut_len(o, L)
    ncap = cut_tome(o, c, end, L)
    bm = bmesh.new(); bm.from_mesh(o.data)
    nopen = sum(1 for e in bm.edges if e.is_boundary and not all(abs(v.co.z) < 1e-4 for v in e.verts))
    bm.free()
    warped = True
    if abs(g) > 1e-9:
        warped = warp_tome(o, g, c, end, L)
    name = tome_name(g, c, end, h, L)
    o.name = name; o.data.name = name
    V.set_origin(o, (0, 0, 0))
    me = o.data
    # 検算: 切る面の外に頂点が無い・切り口の上の天端が一定・切らない端の天端が直線の駒と同じ
    sg = 1.0 if end == "P" else -1.0
    bite = max(sg * (tome_ym(v.co.x, c, end, L) - v.co.y) for v in me.vertices)
    onm = [v for v in me.vertices if abs(v.co.y - tome_ym(v.co.x, c, end, L)) < 5e-5]
    tops = [v.co.z for v in onm if v.co.z > 2.0]
    ctop = max(tops) - min([z for z in tops if z > max(tops) - 0.5]) if tops else 0.0
    far = [v for v in me.vertices if abs(v.co.y - (L if end == "P" else 0.0)) < 1e-5 and v.co.z > 3.0]
    far_dz = max(abs(v.co.z - (h + (-g * L if end == "P" else 0.0))) for v in far if abs(v.co.z - max(w.co.z for w in far)) < 1e-4) if far else 0.0
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print("[tome] %s 切り口 %d 角形 Unity X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] 面 %d 開いた辺(底のほか) %d 面の外 %.6f 切り口の天端の差 %.5f 端の天端の差 %.5f"
          % (name, ncap, -max(xs), -min(xs), min(zs), max(zs), -max(ys), -min(ys), len(me.polygons), nopen, bite, ctop, far_dz))
    if not warped:
        print("[tome]   ⚠ 素の剪断(切り口が端の小口まで届く)── 切り口の上の天端は走りに沿って %.4f 変わる" % ctop)
        ctop = 0.0
    if nopen or bite > 5e-5 or ctop > 1e-4 or far_dz > 1e-4:
        raise SystemExit("[tome] ⛔ 検算が落ちた %s" % name)
    path = os.path.join(OUT, name + ".fbx")
    src = "Tools/Blender/build_kidan_saka.py -- --tome %s %g" % (end, 2 * c) + ("" if abs(g) < 1e-9 else " --grade %g" % (g * 100)) \
          + ("" if h == 4.0 else " --h %g" % h) + ("" if L >= RUN - 1e-6 else " --len %g" % L)
    spec = spec_tome(o, name, g, c, end, h, L, src, warped)
    spec["prefab"] = CANON + "/" + name + ".fbx"
    if SPEC_OUT:
        V.SPEC_DIR = SPEC_OUT
    jp = V.write_spec(path, dict(spec, kind="fence"))
    write_json_meta(jp)
    V.export_fbx([o], path, kind="fence")
    write_meta(path)
    print("[tome] wrote %s" % path)
    return path


def okabe_tome_rows():
    """(頂点, 側, g, c, end, L)。c = 折れ/2 を 0.1° に丸める(名の 3 桁と同じ)。"""
    rows = []
    for vtx, turn, (gA, LA), (gB, LB) in OKABE_TOME:
        c = round(turn * 5) / 10.0
        rows.append((vtx, "A", gA, c, "P", LA)); rows.append((vtx, "B", gB, c, "M", LB))
    return rows


def render_tome_pair(vtx, paths):
    """角の並べ: 前の辺の端の駒(P を切った版)+ その一つ奥の直線の駒 / 次の辺の端の駒(M を切った版)+ 一つ先の直線の駒。
    世界 = Blender。角の天端の前の縁の線の交点を原点・前の辺は −y へ進み見え面 +x・次の辺は右へ折れ(時計回りの区画の出隅)。"""
    turn = [r for r in OKABE_TOME if r[0] == vtx][0][1]
    c = round(turn * 5) / 10.0; t = math.tan(math.radians(c)); phi = math.radians(turn)
    sA, sB, CA, CB = OKABE_TOME_SCENE[vtx]
    (_, _, (gA, LA), (gB, LB)) = [r for r in OKABE_TOME if r[0] == vtx][0]
    V.reset()
    def imp(p):
        before = set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=p)
        new = [x for x in bpy.data.objects if x not in before]
        ms = [x for x in new if x.type == 'MESH']
        V.sel(ms); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        for x in new:
            if x.type != 'MESH':
                bpy.data.objects.remove(x, do_unlink=True)
        return ms[0]
    def straight_obj(g):
        if abs(g) < 1e-9:
            o, _ = K.load("ishigaki"); K.normalize(o, "ishigaki", []); return o
        return imp(os.path.join(OUT, "Ishigaki_Choku_H0400_G%s.fbx" % grade_tag(g)))
    K.load("ishigaki")[0].hide_render = True      # V.TEX を城のテクスチャへ
    objs = []
    # 前の辺: 切った版 A(局所 y ∈ [0, LA])の天端の前の角 (1.4, 1.0·t) を原点へ・z: 切り口の天端 h → CA
    a = imp(paths[(vtx, "A")])
    M = Matrix.Translation((-1.4 * sA, -1.0 * t * sA, CA - 4.0 * sA)) @ Matrix.Scale(sA, 4)
    a.data.transform(M); objs.append(a)
    a2 = straight_obj(gA)
    y0 = LA - 0.2
    M2 = Matrix.Translation((-1.4 * sA, -1.0 * t * sA + y0 * sA, CA - 4.0 * sA - gA * y0 * sA)) @ Matrix.Scale(sA, 4)
    a2.data.transform(M2); objs.append(a2)
    # 次の辺: 切った版 B(局所 y ∈ [0, LB])の天端の前の角 (1.4, LB − 1.0·t) を原点へ・時計回りに φ 回す・z: 切り口の天端 4 − gB·LB → CB
    R = Matrix.Rotation(-phi, 4, 'Z')
    b = imp(paths[(vtx, "B")])
    Mb = R @ Matrix.Translation((-1.4 * sB, -(LB - 1.0 * t) * sB, CB - (4.0 - gB * LB) * sB)) @ Matrix.Scale(sB, 4)
    b.data.transform(Mb); objs.append(b)
    b2 = straight_obj(gB)
    y1 = -(2.0 - 0.2)
    Mb2 = R @ Matrix.Translation((-1.4 * sB, -(LB - 1.0 * t) * sB + y1 * sB, CB - (4.0 - gB * LB) * sB - gB * y1 * sB)) @ Matrix.Scale(sB, 4)
    b2.data.transform(Mb2); objs.append(b2)
    for o in objs:
        o.matrix_world = Matrix.Identity(4)
    # 視点: 外(二等分の外向き = +x を φ/2 だけ時計回り)から目の高さ・斜め上・真上
    out = Vector((math.cos(-phi / 2), math.sin(-phi / 2), 0.0))
    ctop = max(CA, CB)
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    cen = Vector((0.0, 0.0, ctop - 1.2))
    R0 = max((hi - lo).length * 0.9, 5.0)
    cam = V.studio(tuple(cen + out * R0), tuple(cen), res=(1400, 900))
    hook_and_bg()
    files = []
    for nm, loc, look, ortho in (("me", cen + out * R0 * 0.9 + Vector((0, 0, 0.3)), cen, None),
                                 ("naname", cen + out * R0 * 0.8 + Vector((0, 0, R0 * 0.6)), cen, None),
                                 ("ue", Vector((0.0, 0.0, ctop + 30.0)), Vector((0.0, 0.0, ctop)), 8.0 * max(sA, sB) + 2.0)):
        cam.location = loc
        cam.rotation_euler = (look - loc).to_track_quat('-Z', 'Y').to_euler()
        if ortho:
            cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
        else:
            cam.data.type = 'PERSP'; cam.data.lens = 35
        p = os.path.join(SHOTS, "kidan_tome_%s_%s.png" % (vtx, nm)); V.render(p); files.append(p)
    print("[tome] 検め %s %s" % (vtx, json.dumps(files, ensure_ascii=False)))
    return files


# ---------------------------------------------------------------- 検め(並べ焼き)
def hook_and_bg():
    V.hook_textures()
    wt = bpy.context.scene.world.node_tree
    bg = wt.nodes["Background"]; bg.inputs[0].default_value = (0.6, 0.62, 0.66, 1); bg.inputs[1].default_value = 1.0
    mg = wt.nodes.new("ShaderNodeBackground"); mg.inputs[0].default_value = (1, 0, 1, 1)
    lp = wt.nodes.new("ShaderNodeLightPath"); mx = wt.nodes.new("ShaderNodeMixShader")
    wt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); wt.links.new(bg.outputs[0], mx.inputs[1]); wt.links.new(mg.outputs[0], mx.inputs[2])
    wt.links.new(mx.outputs[0], wt.nodes["World Output"].inputs[0])


def shots(objs, stem, views):
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2; R = max((hi - lo).length * 1.15, 5.0)
    cam = V.studio((c.x + R, c.y, c.z), tuple(c), res=(1400, 800))
    hook_and_bg()
    for o in bpy.data.objects:          # 床は見えの邪魔(底の開きを見る)── 隠す
        if o.type == 'MESH' and o not in objs:
            o.hide_render = True
    os.makedirs(SHOTS, exist_ok=True)
    files = []
    for nm, off, look_dz, ortho in views:
        loc = c + Vector(off) * R
        cam.location = loc
        cam.rotation_euler = (c + Vector((0, 0, look_dz)) - loc).to_track_quat('-Z', 'Y').to_euler()
        if ortho:
            cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho * R
        else:
            cam.data.type = 'PERSP'; cam.data.lens = 35
        p = os.path.join(SHOTS, "%s_%s.png" % (stem, nm)); V.render(p); files.append(p)
    print("[kidan] 検め " + json.dumps(files, ensure_ascii=False))
    return files


VIEWS = [   # Blender: 見え面 = +x・走り = y
    ("omote", (1.0, -0.35, 0.18), 0.0, None),
    ("omote_hikui", (0.9, -0.15, -0.05), 0.0, None),
    ("ura", (-1.0, 0.35, 0.25), 0.0, None),
    ("koguchi", (0.25, 1.1, 0.25), 0.0, None),
    ("ue", (0.001, 0.0, 1.0), 0.0, 1.1),
    ("shita", (0.35, -0.2, -0.6), 0.0, None),
]


def place_copy(src, M):
    c = src.copy(); c.data = src.data.copy(); bpy.context.collection.objects.link(c)
    c.data.transform(M); c.data.update(); c.matrix_world = Matrix.Identity(4)
    return c


def render_run(g, step=0.6):
    """走りの並べ: 平ら 2 枚 → 坂 g の 3 枚(重ね)→ 段 step → 坂 g の 2 枚。Blender の y へ進む(天端は Blender y へ −g で ── U の駒は y へ下がる)。
    ⇒ D の駒(Blender y へ上がる)で組む: 天端(y) = 4 + |g|·(y − 3.8)。"""
    V.reset()
    gd = -abs(g)
    o_s, _ = build_straight(gd, fresh=False)        # 焼いた駒そのもの(書き出し済み)
    flat = K.load("ishigaki")[0]; K.normalize(flat, "ishigaki", [])
    objs = []
    T = lambda dx, dy, dz: Matrix.Translation((dx, dy, dz))
    for y0 in (0.0, 1.8):
        objs.append(place_copy(flat, T(0, y0, 0)))
    line = lambda y: abs(g) * (y - 3.8)
    # 坂の区間 [3.8, 9.2]: 3 枚・送り 1.7
    for y0 in (3.8, 5.5, 7.2):
        objs.append(place_copy(o_s, T(0, y0, line(y0))))
    # 段 step・区間 [9.2, 12.8]: 2 枚・送り 1.6
    for y0 in (9.2, 10.8):
        objs.append(place_copy(o_s, T(0, y0, line(y0) + step)))
    for o in (flat, o_s):
        o.hide_render = True; o.hide_viewport = True
    return shots(objs, "kidan_saka_run_" + grade_tag(gd), VIEWS)


def render_kado(deg, s, gIn, gOut):
    """隅の並べ: 入りの run(素の Castle Wall ×s・勾配 gIn)── 隅 ── 出の run(坂の駒 ×s・勾配 gOut)。"""
    V.reset()
    o_k, _, a = build_kado(deg, s, gIn, gOut)
    Sm = Matrix.Scale(s, 4)
    objs = [o_k]
    D = math.radians(abs(deg))
    # 入りの腕: 局所 +y へ(Blender)。走り(入り→出)は −y の向き ⇒ 入りの駒は z += gIn·(−(y − a))·… 入りの腕の先 (0, a) の高さ −gIn·a
    o_in, _ = build_straight(gIn, fresh=False) if abs(gIn) > 1e-9 else (None, None)
    if o_in is None:
        o_in = K.load("ishigaki")[0]; K.normalize(o_in, "ishigaki", [])
    # 入りの駒の局所 +y = 折れ点から離れる向き・Unity +Z = Blender −y = 折れ点へ向かう = 走り(入り→出)⇒ U = 走りに沿って上がる = gIn そのまま
    for k in range(2):
        y0 = a + k * 1.8 * s
        objs.append(place_copy(o_in, T3(0, y0, -gIn * y0) @ Sm))
    # 出の腕: 先 = a·(−sinΔ, −cosΔ)。直線の駒は R(−Δ) で回す(局所 +y が折れ点へ向く・見え面が出の腕の面と同じ側)
    o_out, _ = build_straight(gOut, fresh=False) if abs(gOut) > 1e-9 else (None, None)
    if o_out is None:
        o_out = K.load("ishigaki")[0]; K.normalize(o_out, "ishigaki", [])
    Rm = Matrix.Rotation(-D, 4, 'Z')
    tip = Vector((-math.sin(D), -math.cos(D), 0.0)) * a
    dout = Vector((-math.sin(D), -math.cos(D), 0.0))
    # 局所 +y が折れ点へ向く ⇒ 局所の Unity +Z(Blender −y)は折れ点から離れる = 走り(入り→出)⇒ U = 上がる = gOut そのまま
    for k in range(2):
        far = tip + dout * (k * 1.8 * s)           # この駒の局所 y = 2 の端(折れ点の側)
        u = a + k * 1.8 * s                       # 折れ点からの道のり
        P = far - (Rm @ Sm @ Vector((0, 2.0, 0)).to_4d()).to_3d()
        z = gOut * u - (-gOut * 2.0 * s)          # 局所 y = 2 の端の天端 4s − 2s·g ⇒ そこを 4s + g·u に
        objs.append(place_copy(o_out, T3(P.x, P.y, z) @ Rm @ Sm))
    for o in (o_in, o_out):
        o.hide_render = True; o.hide_viewport = True
    stem = os.path.splitext(os.path.basename(_))[0] if False else "kidan_saka_kado_%02d_G%sx%s" % (round(deg), grade_tag(gIn), grade_tag(gOut))
    views = [("omote", (0.7, -0.75, 0.2), 0.0, None), ("omote_out", (0.2, -1.0, 0.15), 0.0, None),
             ("ura", (-0.8, 0.6, 0.35), 0.0, None), ("ue", (0.001, 0.0, 1.0), 0.0, 1.1), ("shita", (0.5, -0.5, -0.5), 0.0, None)]
    return shots(objs, stem, views)


def T3(dx, dy, dz):
    return Matrix.Translation((dx, dy, dz))


T = T3


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    h = float(argv[argv.index("--h") + 1]) if "--h" in argv else 4.0
    L = float(argv[argv.index("--len") + 1]) if "--len" in argv else RUN
    s = float(argv[argv.index("--s") + 1]) if "--s" in argv else None
    if "--okabe" in argv:
        for g in OKABE_GRADES:
            for sg in (1, -1):
                build_straight(sg * g)
        for deg, sk, gi, go in OKABE_KADO:
            build_kado(deg, sk, gi / 100.0, go / 100.0)
        if do_render:
            render_run(0.125); render_run(0.027)
            render_kado(78.367, 0.75, 0.0, 0.027)
        return
    if "--okabe-tome" in argv:
        paths = {}
        done = {}
        for vtx, side, g, c, end, LL in okabe_tome_rows():
            key = (round(g, 4), c, end, LL)
            if key not in done:
                done[key] = build_tome(g, c, end, 4.0, LL)
            paths[(vtx, side)] = done[key]
        print("[tome] 焼いた版 %d 本" % len(done))
        if do_render:
            for vtx, *_ in OKABE_TOME:
                render_tome_pair(vtx, paths)
        return
    gr = [float(t) / 100.0 for t in argv[argv.index("--grade") + 1].split(",")] if "--grade" in argv else [0.0]
    if "--tome" in argv:
        i = argv.index("--tome")
        end, turn = argv[i + 1], float(argv[i + 2])
        build_tome(gr[0], round(turn * 5) / 10.0, end, h, L)
        return
    if "--kado" in argv:
        deg = float(argv[argv.index("--kado") + 1])
        if len(gr) == 1:
            gr = [gr[0], gr[0]]
        if do_render:
            render_kado(deg, s, gr[0], gr[1])
        else:
            build_kado(deg, s, gr[0], gr[1])
        return
    if do_render:
        render_run(abs(gr[0]))
    build_straight(gr[0], h, L)


if __name__ == "__main__":
    main()
