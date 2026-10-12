"""**練塀を一つの閉じた断面で起こし直す**(EDO-0502 2026-10-12 施主裁定「案1です」・岡部が初例)。

    blender --background --python Tools/Blender/build_neribei.py -- --choku --render          # → Neribei_Choku(1 枚 2.990)
    blender --background --python Tools/Blender/build_neribei.py -- --kiri 5 --render         # → Neribei_Kiri_T05(瓦 5 枚分 = 1.068)
    blender --background --python Tools/Blender/build_neribei.py -- --end --render            # → Neribei_End_L / Neribei_End_R
    blender --background --python Tools/Blender/build_neribei.py -- --kado 90 --render        # → Neribei_Kado_90(腕は素 0.854)
    blender --background --python Tools/Blender/build_neribei.py -- --kado -18 --arms 0.60,0.85   # → Neribei_Kado_18M_A60x85
    blender --background --python Tools/Blender/build_neribei.py -- --kado 0M                 # → Neribei_Kado_00M(0° の鏡は名で)
    blender --background --python Tools/Blender/build_neribei.py -- --okabe                   # 岡部の一式(直線・切り 13・端 2・隅 19)
    blender --background --python Tools/Blender/build_neribei.py -- --list <file>             # 1 行 1 本(`--kado 39 --arms 0.6,0.85` の形)

【なぜ要るか】在庫の練塀 `s_hei_center` は壁も屋根も**片面の板一枚**の模型で、DobeiRun は表裏 2 枚を 0.20 ずらして
  厚みを偽っていた ⇒ 小口は中空・冠瓦が二筋・隅の駒(Dobei_Kado_*)の腕は外の板 1 枚で内から 73% 透ける
  (裁定図 https://claude.ai/artifact/F7tZdVPPYeTcyMJusSrRZH ・監査は部材方の memory dobei-pair-kado-arms-single-sheet)。

【作り】⛔ ゼロから作らない。`s_hei_center.obj` を**実寸(×1.818)**で 1 組だけ読み、
  ・屋根(yane 瓦・noki 軒・taruki 垂木・mune 棟・keta 桁)は**そのまま 1 組**(芯対称・総幅 1.15・瓦場 1.11)。
  ・壁(ishigaki 腰の石垣・shitami 下見板・san 見切り・hei 漆喰・hashira2 束)は表の面を外へ THK_SHIFT だけ押し出し
    (芯を跨ぐ天端・小口の面は両側へ広がる)、表だけの面を芯で**鏡に写して裏**を作る ⇒ 漆喰の面で厚み 0.40 の閉じた断面。
  ・駒の両端(と切り口)の壁体は**断面で塞ぐ**(腰の台形 + 壁の矩形。UV は素の ishigaki / hei の最大面の矩形 ── 一点貼りにしない)。
  ・材は `s_heimap` 一つのまま(素の UV のまま)。メッシュは**群の名のまま別オブジェクト**で書き出す
    (Unity の WallFace = hei / shitami / hashira2 で外面を測る ── 一枚に join すると犬走りへ寄せる測りが外れる)。

【割付】1 枚 = 走り P = 2.9905(素のまま)。瓦の周期 p = P/14 = 0.2136(下見板・垂木は P/8、束は P/2)。
  ⭐ 切りの駒は**瓦の枚数 k で切る**(Neribei_Kiri_T<kk>・長さ k·p)⇒ 継ぎ目で瓦が続く。走りを割るのは据える側:
     n = floor(L/P) 枚 + 端数 k = round(余り/p) の切り 1 枚 ⇒ 全部の駒に走りの倍率 L/(nP+kp)(≤ p/2/L)を掛けて割り切る。
  ⭐ 隅の腕は折れ点から瓦の周期で始まる(素の腕 = 4 枚 = 0.854)⇒ 腕の先に直線を突き付ければ瓦が続く。

【局所座標(Unity・実寸 scale 1)】幅 = X(走り)/ 高さ = Y / 厚み = Z・+Z = 見え面(断面は芯対称なので表裏は同じ姿)。
  直線・切り: ピボット = 走りの中央・壁の芯・腰の石垣の下端(Y=0)。X ∈ [−L/2, L/2]。
  端: 1 枚分の走りの中央がピボット(直線と置き換え)。`_L` は棟止め(鬼瓦・袖瓦・端の柱)が **+X**(外から見て左)・
      `_R` は **−X**。どちらも在庫 `s_hei_l` を同じ処理で厚くした物(R は L を Y 軸まわりに 180° 回しただけ)。
  隅: build_kado.py の練塀の隅と**同じ据え**(折れ点 = 両腕の芯の交点・足元 / 入りの腕は局所 −Z へ / 化粧面は局所 −X)。
      ⚠ ただし実寸(scale 1)── 旧 Dobei_Kado は局所(×ES で据えた)。腕の名は cm(`_A<入り>x<出>`・素の腕なら付けない)。
      出隅の側の留めには**隅棟**(素の mune の断面を留めの線へ流した物)、入隅の側は瓦の谷のまま。棟は留めで一筋に折れる。

【落とし穴】
  ・素の板は片面: 表は Blender +y(読み込みの向き)。鏡の裏は巻きを裏返す。
  ・芯を跨ぐ面(漆喰の天端・腰の天端・端の小口)は鏡に写さない(二重になる)。押し出しで広がるだけ。
  ・bisect は面の無い辺・頂点を残す ⇒ 消す(bounds が嘘をつく)。
  ・obj を何度も読むと s_heimap.001 ができる ⇒ dedup_materials。
"""
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ROOT = V.REPO
SRC_C = os.path.join(ROOT, "Assets/edogoyomi/es_dobei/s_hei_center.obj")
SRC_L = os.path.join(ROOT, "Assets/edogoyomi/es_dobei/s_hei_l.obj")
TEX = os.path.join(ROOT, "Assets/edogoyomi/es_dobei/s_hei.jpg")
OUT = V.out_dir(os.path.join(ROOT, "Assets/Edo/Models/Neribei"))
CANON = "Assets/Edo/Models/Neribei"            # 札の prefab(staging へ焼いても正典の道)
if os.environ.get("BUZAI_SPEC_OUT"):
    V.SPEC_DIR = os.environ["BUZAI_SPEC_OUT"]
SHOTS = os.environ.get("BUZAI_SHOTS", os.path.join(ROOT, "Screenshots"))

ES = 1.818
P = 2.9905                 # 1 枚の走り(素の s_hei_center の x 外形 0.627 − (−2.364) を ×ES)
NTILE = 14
RUN_P = P
TILE = P / NTILE           # 瓦の周期 0.2136
ARM_FULL_TILES = 4         # 隅の素の腕 = 瓦 4 枚(0.854)。90° の留めの三角(軒 0.575)を越えて断面が 0.28 残る
HALF_T = 0.20              # 漆喰の面の半厚 ⇒ t = 0.40(施主裁定)
WALL = ("ishigaki", "shitami", "san", "hei", "hashira2", "hashira")
ROOF = ("yane", "noki", "taruki", "mune", "keta", "keraba", "onigawara")
EPS = 1e-4


# ---------------------------------------------------------------- 読み・厚み
def gname(o):
    return o.get("g") or o.name.split(".")[0]


def read_groups(src):
    """obj を群ごとに読み、実寸へ。戻り値 {群名: obj}。Blender: 走り x / 表 +y / 上 z(素の向き)。"""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=src, forward_axis='Z', up_axis='Y', use_split_groups=True)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    V.sel(new); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    V.dedup_materials()
    out = {}
    for o in new:
        o.data.transform(Matrix.Scale(ES, 4)); o.data.update()
        o["g"] = o.name.split(".")[0]
        out[o["g"]] = o
    return out


def uv_rect_of(o):
    """群のいちばん大きい面の UV の外接矩形と、その面の実寸(走り m・高さ m)── build_dobei_kiri.py と同じ取り方。"""
    me = o.data; uvl = me.uv_layers.active.data
    best = None
    for p in me.polygons:
        if best is None or p.area > best[0]:
            us = [uvl[i].uv[0] for i in p.loop_indices]; vs = [uvl[i].uv[1] for i in p.loop_indices]
            co = [me.vertices[v].co for v in p.vertices]
            w = max(c.x for c in co) - min(c.x for c in co); h = max(c.z for c in co) - min(c.z for c in co)
            best = (p.area, (min(us), min(vs), max(us), max(vs)), (max(w, 1e-3), max(h, 1e-3)))
    return best[1], best[2]


def thicken(o, shift):
    """壁の群: 表の面を外へ shift(芯を跨ぐ面は両側へ広がる)・表だけの面を芯で鏡に写して裏を作る。"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        if abs(v.co.y) > EPS:
            v.co.y += math.copysign(shift, v.co.y)
    uvl = bm.loops.layers.uv.active
    front = [f for f in bm.faces if all(v.co.y > EPS for v in f.verts)]
    vmap = {}
    for f in front:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm.verts.new(Vector((v.co.x, -v.co.y, v.co.z)))
            vs.append(vmap[v])
        uvs = [l[uvl].uv.copy() for l in f.loops]
        nf = bm.faces.new(list(reversed(vs)))
        nf.material_index = f.material_index
        for l, uv in zip(nf.loops, list(reversed(uvs))):
            l[uvl].uv = uv
    bm.normal_update()
    bm.to_mesh(o.data); bm.free(); o.data.update()


def section(groups):
    """作図の値(実寸・厚くした後): 腰の下端・天端の半幅、腰の天端の高さ、壁の天端、棟の天端。"""
    ish = groups["ishigaki"].data
    zs = [v.co.z for v in ish.vertices]
    zi = max(zs)
    yb = max(v.co.y for v in ish.vertices if v.co.z < 0.01)
    yt = max(v.co.y for v in ish.vertices if v.co.z > zi - 0.01)
    zt = max(v.co.z for v in groups["hei"].data.vertices)
    zh = min(v.co.z for v in groups["hei"].data.vertices)                    # 漆喰の下端(見切りの上)
    yd = max(v.co.y for k in ("shitami", "san") for v in groups[k].data.vertices)   # 下見板・見切りの表
    ztop = max(v.co.z for o in groups.values() for v in o.data.vertices)
    return dict(yb=yb, yt=yt, zi=zi, zt=zt, ztop=ztop, zh=zh, yd=yd)


def load(src):
    """群を読み、厚くし、走りの始め(素の x 最小)を x=0 に。戻り値 (groups, sec, uv_is, uv_hei)。"""
    g = read_groups(src)
    uv_is = uv_rect_of(g["ishigaki"]); uv_hei = uv_rect_of(g["hei"])
    uv_sh_glob[0] = uv_rect_of(g["shitami"])
    hei_face = max(v.co.y for v in g["hei"].data.vertices)
    shift = HALF_T - hei_face
    for k, o in g.items():
        if k in WALL:
            thicken(o, shift)
    g["shin"] = core(g, uv_sh_glob[0][0])
    return g, shift, uv_is, uv_hei


def core(g, rect, inset=0.025):
    """壁の芯の裏打ち: 板の裏(表の板の裏面 − inset)に外向きの面を一枚ずつ。素の下見板は押縁の脇に細い隙があり、
    厚くした壁では隙から中が抜けて背景が見えた(2026-10-12 継ぎ目の寄りで実測)⇒ 隙の奥を塞ぐ。WallFace の名ではない。"""
    hs = g["hei"].data
    x0 = min(v.co.x for v in hs.vertices); x1 = max(v.co.x for v in hs.vertices)
    zi = max(v.co.z for v in g["ishigaki"].data.vertices)
    zt = max(v.co.z for v in hs.vertices)
    yb = min(v.co.y for v in g["shitami"].data.vertices if v.co.y > 0) - inset
    me = bpy.data.meshes.new("shin"); o = bpy.data.objects.new("shin", me); bpy.context.collection.objects.link(o)
    me.materials.append(hs.materials[0])
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    for sy in (1.0, -1.0):
        vs = [bm.verts.new(Vector((x, sy * yb, z))) for x, z in ((x0, zi), (x1, zi), (x1, zt), (x0, zt))]
        f = bm.faces.new(vs); f.normal_update()
        if f.normal.y * sy < 0:
            f.normal_flip()
        for l in f.loops:
            l[uvl].uv = (rect[0] + (rect[2] - rect[0]) * (l.vert.co.x - x0) / (x1 - x0),
                         rect[1] + (rect[3] - rect[1]) * (l.vert.co.z - zi) / (zt - zi))   # 矩形(一点貼りにしない)
    bm.to_mesh(me); bm.free(); me.update()
    o["g"] = "shin"
    return o


uv_sh_glob = [None]


# ---------------------------------------------------------------- 幾何の道具
def xform(o, M):
    o.data.transform(M)
    if M.to_3x3().determinant() < 0:
        for p in o.data.polygons:
            p.flip()
    o.data.update()


def dup(o, suffix=""):
    c = o.copy(); c.data = o.data.copy(); c["g"] = gname(o)
    bpy.context.collection.objects.link(c)
    return c


def cut(o, co, no, keep_positive=True):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                           plane_co=Vector(co), plane_no=Vector(no),
                           clear_outer=not keep_positive, clear_inner=keep_positive)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()


def merge_groups(objs):
    """群ごとに一つへ join(群名のオブジェクト)。空は捨てる。"""
    by = {}
    for o in objs:
        if len(o.data.polygons) == 0:
            bpy.data.objects.remove(o, do_unlink=True); continue
        by.setdefault(gname(o), []).append(o)
    out = []
    for k, lst in by.items():
        j = V.join(lst, k) if len(lst) > 1 else lst[0]
        j["g"] = k
        bm = bmesh.new(); bm.from_mesh(j.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bm.to_mesh(j.data); bm.free(); j.data.update()
        out.append(j)
    for j in out:
        j.name = j["g"]; j.data.name = j["g"]
    return out


def tile_run(groups, x0, x1, src_x0):
    """素の 1 枚(x ∈ [src_x0, src_x0 + P])を走りへ継いで [x0, x1] を覆い、[x0, x1] で切る(端は塞がない)。
    瓦の位相: 枚の始めが x = 0 の倍数 P に来る(x0 が負でもよい)。戻り値は群の複製の列(元は残す)。"""
    parts = []
    k0 = int(math.floor(x0 / P + 1e-6)); k1 = int(math.ceil(x1 / P - 1e-6))
    for k in range(k0, k1):
        for g, o in groups.items():
            c = dup(o)
            xform(c, Matrix.Translation(Vector((k * P - src_x0, 0, 0))))
            parts.append(c)
    for c in parts:
        cut(c, (x0, 0, 0), (1, 0, 0), True)
        cut(c, (x1, 0, 0), (1, 0, 0), False)
    return [c for c in parts if len(c.data.polygons)]


def cap(bm, uvl, sec, uv_is, uv_hei, plane_pt, along, lateral, outward, mi=0):
    """壁体の断面(腰の台形 + 壁の矩形)を平面の上に貼る。along = 走りの向き(面の法線は outward)、
    lateral = 厚みの向き(単位)。UV は素の面の m あたりの密度で矩形へ(収まらなければ一様に縮める)。"""
    yb, yt, zi, zt = sec["yb"], sec["yt"], sec["zi"], sec["zt"]
    yd, zh = sec["yd"], sec["zh"]
    made = []
    # 腰の台形 / 下見板の帯(板の表 yd まで ── 漆喰の 0.20 で切ると板の小口 6mm が抜けて筋に見えた)/ 漆喰の帯
    for poly, (rect, (w, h)) in (([(-yb, 0.0), (yb, 0.0), (yt, zi), (-yt, zi)], uv_is),
                                 ([(-yd, zi), (yd, zi), (yd, zh), (-yd, zh)], uv_sh_glob[0]),
                                 ([(-HALF_T, zh), (HALF_T, zh), (HALF_T, zt), (-HALF_T, zt)], uv_hei)):
        vs = [bm.verts.new(Vector(plane_pt) + Vector(lateral) * s + Vector((0, 0, z))) for s, z in poly]
        f = bm.faces.new(vs); f.material_index = mi
        f.normal_update()
        if f.normal.dot(Vector(outward)) < 0:
            f.normal_flip()
        su = (rect[2] - rect[0]) / w; sv = (rect[3] - rect[1]) / h
        s0 = min(s for s, _ in poly); z0 = min(z for _, z in poly)
        span_u = (max(s for s, _ in poly) - s0) * su; span_v = (max(z for _, z in poly) - z0) * sv
        kk = min(1.0, (rect[2] - rect[0]) / max(span_u, 1e-6), (rect[3] - rect[1]) / max(span_v, 1e-6))
        for l in f.loops:
            s = (l.vert.co - Vector(plane_pt)).dot(Vector(lateral)); z = l.vert.co.z
            l[uvl].uv = (rect[0] + (s - s0) * su * kk, rect[1] + (z - z0) * sv * kk)
        made.append(f)
    return made


def cap_object(name, mat, caps, sec, uv_is, uv_hei):
    """caps = [(plane_pt, along, lateral, outward), ...] を一つのオブジェクト "koguchi" に。"""
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    me.materials.append(mat)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    for c in caps:
        cap(bm, uvl, sec, uv_is, uv_hei, *c)
    bm.to_mesh(me); bm.free(); me.update()
    o["g"] = name
    return o


def mat_of(groups):
    return next(iter(groups.values())).data.materials[0]


def clear_src(groups):
    for o in groups.values():
        bpy.data.objects.remove(o, do_unlink=True)


# ---------------------------------------------------------------- 書き出し(Blender x 走り → Unity は X = −x・Z = −y)
def finish(objs, name, kind_spec=None):
    """原点はもう合わせてある前提。群名のオブジェクトのまま書き出す。"""
    for o in objs:
        o.location = (0, 0, 0)
    path = os.path.join(OUT, name + ".fbx")
    if kind_spec is not None:
        spec = dict(kind_spec); spec["prefab"] = CANON + "/" + name + ".fbx"
        V.export_fbx(objs, path, kind="fence", spec=spec)
    else:
        V.export_fbx(objs, path)
    xs = [v.co.x for o in objs for v in o.data.vertices]; ys = [v.co.y for o in objs for v in o.data.vertices]
    zs = [v.co.z for o in objs for v in o.data.vertices]
    nf = sum(len(o.data.polygons) for o in objs)
    print("[neri] %s  Unity X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] 面 %d → %s"
          % (name, -max(xs), -min(xs), min(zs), max(zs), -max(ys), -min(ys), nf, path))
    return path


def fence_spec(sec, x_lo, x_hi, coping, top, source):
    """札(fence)── 作図の値から。Unity 局所: X = −x・Z = −y。足元 = 腰の石垣の Y 0.05 の断面(芯対称)。"""
    hf = sec["yb"] - (sec["yb"] - sec["yt"]) * (0.05 / sec["zi"])
    X0, X1 = -x_hi, -x_lo
    return {"source": source, "unitScale": 1.0, "yBottom": 0.0,
            "foot": [{"x": X0, "y": -hf}, {"x": X1, "y": -hf}, {"x": X1, "y": hf}, {"x": X0, "y": hf}],
            "faceOut": hf, "faceIn": -hf, "copingOverhang": coping, "height": top}


# ---------------------------------------------------------------- 直線・切り
def build_straight(k_tiles=NTILE):
    """k 枚分(瓦の周期)の直線。k = 14 は 1 枚(Neribei_Choku)。両端の壁体を断面で塞ぐ。"""
    V.reset()
    g, shift, uv_is, uv_hei = load(SRC_C)
    sec = section(g)
    src_x0 = min(v.co.x for o in g.values() for v in o.data.vertices)
    L = k_tiles * TILE
    parts = tile_run(g, 0.0, L, src_x0)
    mat = mat_of(g)
    clear_src(g)
    objs = merge_groups(parts)
    objs.append(cap_object("koguchi", mat, [((0, 0, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)),
                                            ((L, 0, 0), (1, 0, 0), (0, 1, 0), (1, 0, 0))], sec, uv_is, uv_hei))
    for o in objs:
        xform(o, Matrix.Translation(Vector((-L / 2, 0, 0))))
    name = "Neribei_Choku" if k_tiles == NTILE else "Neribei_Kiri_T%02d" % k_tiles
    src = "Tools/Blender/build_neribei.py -- " + ("--choku" if k_tiles == NTILE else "--kiri %d" % k_tiles)
    path = finish(objs, name, fence_spec(sec, -L / 2, L / 2, 0.0, sec["ztop"], src))
    print("[neri]   厚み: 漆喰 %.3f・腰の下端 %.3f・腰の天端 %.3f(高 %.3f)・壁の天端 %.3f・棟 %.3f・押し出し %.3f"
          % (2 * HALF_T, 2 * sec["yb"], 2 * sec["yt"], sec["zi"], sec["zt"], sec["ztop"], shift))
    return objs, path


# ---------------------------------------------------------------- 端(棟止め)
def build_end(on_done=None):
    """在庫 s_hei_l(1 枚 + 端の柱・袖瓦・鬼瓦・腰の小口)を同じ処理で厚くする。素の端は +x(Unity −X)。
    走りの側の端は断面で塞ぐ。ピボット = 1 枚分の走りの中央。R = そのまま / L = z まわり 180°。"""
    out = []
    for hand in ("R", "L"):
        V.reset()
        g, shift, uv_is, uv_hei = load(SRC_L)
        sec = section(g)
        x_run0 = min(v.co.x for v in g["hei"].data.vertices)          # 走りの始め(−2.326)
        x_run1 = max(v.co.x for v in g["shitami"].data.vertices)      # 1 枚の終わり = 端の柱の内面(0.662)
        x_post = max(v.co.x for v in g["hashira"].data.vertices)      # 端の柱の外面
        x_end = max(v.co.x for o in g.values() for v in o.data.vertices)   # 鬼瓦の先
        x_koshi = max(v.co.x for v in g["ishigaki"].data.vertices)
        mat = mat_of(g)
        objs = list(g.values())
        objs.append(cap_object("koguchi", mat, [((x_run0, 0, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0))], sec, uv_is, uv_hei))
        for o in objs:
            o["g"] = gname(o)
        objs = merge_groups(objs)
        xc = 0.5 * (x_run0 + x_run1)
        M = Matrix.Translation(Vector((-xc, 0, 0)))
        if hand == "L":
            M = Matrix.Rotation(math.pi, 4, 'Z') @ M
        for o in objs:
            xform(o, M)
        lo, hi = (x_run0 - xc, x_koshi - xc) if hand == "R" else (-(x_koshi - xc), -(x_run0 - xc))
        coping = x_end - max(x_post, x_koshi)
        name = "Neribei_End_" + hand
        path = finish(objs, name, fence_spec(sec, lo, hi, max(0.0, x_end - x_post), sec["ztop"],
                                             "Tools/Blender/build_neribei.py -- --end"))
        print("[neri]   %s: 1 枚の走り %.3f・端の柱の外面まで %.3f・腰の小口 %.3f・鬼瓦の先 %.3f(ピボットから・端の側)"
              % (name, x_run1 - x_run0, x_post - xc, x_koshi - xc, x_end - xc))
        out.append((objs, path))
        if on_done:
            on_done(objs, path)
    return out


# ---------------------------------------------------------------- 隅(留め)
def reflect_m(n):
    nx, ny, nz = n
    return Matrix(((1 - 2 * nx * nx, -2 * nx * ny, -2 * nx * nz, 0),
                   (-2 * ny * nx, 1 - 2 * ny * ny, -2 * ny * nz, 0),
                   (-2 * nz * nx, -2 * nz * ny, 1 - 2 * nz * nz, 0),
                   (0, 0, 0, 1)))


def hip(mune_src, mat, h, s, sec):
    """出隅の側(横 s = ±1 の屋根面)の留めの線へ隅棟を流す。素の mune の断面(芯からの (q, z))を
    留めの水平線 t = (s·cos h ... ) に沿わせ、高さは瓦の天端の勾配で下げる。下端は断面で塞ぐ。"""
    # 素の mune の帯の断面(芯からの横 q・高さ z)── 6 面の折れの順
    chain = [(-0.095, 2.485), (-0.067, 2.558), (-0.076, 2.613), (0.0, 2.646), (0.076, 2.613), (0.067, 2.558), (0.095, 2.485)]
    zb = 2.485
    slope = sec["roof_slope"]
    half_w = sec["eave_half"]
    t = Vector((s * math.cos(h), -math.sin(h), 0.0))        # 留めの線(出隅の外へ)
    perp = Vector((math.sin(h), s * math.cos(h), 0.0))      # 留めの面の法線(水平)
    u1 = half_w / math.cos(h)
    def pt(u, q, z):
        lat = u * math.cos(h)
        return t * u + perp * q + Vector((0, 0, z - slope * lat))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rect, _ = uv_rect_of(mune_src)
    A = [bm.verts.new(pt(0.0, q, z)) for q, z in chain]
    B = [bm.verts.new(pt(u1, q, z)) for q, z in chain]
    L3 = (pt(u1, 0, zb) - pt(0, 0, zb)).length
    for i in range(len(chain) - 1):
        f = bm.faces.new([A[i], A[i + 1], B[i + 1], B[i]])
        f.normal_update()
        mid = (A[i].co + A[i + 1].co + B[i].co + B[i + 1].co) / 4
        ax = (pt(u1 * 0.5, 0, zb) - pt(u1 * 0.5, 0, zb - 1.0)).normalized()
        cen = pt(u1 * 0.5, 0.0, zb - 0.05)
        if f.normal.dot(mid - cen) < 0:
            f.normal_flip()
        v0 = rect[1] + (rect[3] - rect[1]) * i / (len(chain) - 1); v1 = rect[1] + (rect[3] - rect[1]) * (i + 1) / (len(chain) - 1)
        uL = rect[0] + (rect[2] - rect[0]) * min(1.0, L3 / RUN_P)
        for l in f.loops:
            a = l.vert in B; j = A.index(l.vert) if l.vert in A else B.index(l.vert)
            l[uvl].uv = (uL if a else rect[0], v0 if j == i else v1)
    # 下端の小口(断面 + 底の線)
    f = bm.faces.new(B)
    f.normal_update()
    if f.normal.dot(t) < 0:
        f.normal_flip()
    for l in f.loops:
        j = B.index(l.vert)
        l[uvl].uv = (rect[0] + (rect[2] - rect[0]) * 0.02 * j, rect[1] + (rect[3] - rect[1]) * 0.5)
    o = bpy.data.objects.new("sumimune", bpy.data.meshes.new("sumimune"))
    bpy.context.collection.objects.link(o)
    bm.to_mesh(o.data); bm.free(); o.data.materials.append(mat); o.data.update()
    o["g"] = "sumimune"
    return o


def soffit_z(objs, h, sgn, depth=0.12):
    """留めの線の上で、屋根(軒裏)の下面を光線で測った z_of(lat) = (下面 − 3mm, 下面 + depth)。
    線の真上は割れ目を抜けるので、留めの面の両側へ 3mm ずらした 2 本の低い方。"""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new(); t.from_mesh(o.data); me = bpy.data.meshes.new("t"); t.to_mesh(me); bm.from_mesh(me); t.free(); bpy.data.meshes.remove(me)
    bvh = BVHTree.FromBMesh(bm)
    m = Vector((math.cos(h), -sgn * math.sin(h), 0.0)); n = Vector((sgn * math.sin(h), math.cos(h), 0.0))
    def z_of(l, side=1.0):
        best = None
        for d in (0.003, -0.003):
            p = m * (side * l / math.cos(h)) + n * d
            r = bvh.ray_cast(Vector((p.x, p.y, 0.5)), Vector((0, 0, 1)), 10.0)
            if r[0] is not None and (best is None or r[0].z < best):
                best = r[0].z
        if best is None:
            best = 2.0
        return (best - 0.003, best + depth)
    return z_of


def miter_plate(mat, rect, h, sgn, z_of, lat0, lat1, name="tome_ita"):
    """留めの面の中に、屋根の裏(軒裏)から瓦の中までの細い板を両面で立てる。
    ⚠ 両腕の瓦場・軒裏は留めの面でちょうど切れて接するだけで、頂点を共有しない(T 字)⇒ 軒裏を見上げると留めの線に
       背景が細く抜けた(2026-10-12 Dobei2_Kado_90 の見上げで実見)。面の中の板なので、真横(面に沿って)以外からは見えない。
    z_of(lat) = (下, 上) ── 横 lat(腕の芯から)での板の下端・上端。lat0..lat1 を両側(±)に。"""
    m = Vector((math.cos(h), -sgn * math.sin(h), 0.0))      # 留めの面の水平の向き(腕 A の横 x と cos h で結ぶ)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    for side in (1.0, -1.0):
        ls = [lat0 + (lat1 - lat0) * i / 6.0 for i in range(7)]
        zz = [z_of(l, side) for l in ls]
        top = [m * (side * l / math.cos(h)) + Vector((0, 0, z[1])) for l, z in zip(ls, zz)]
        bot = [m * (side * l / math.cos(h)) + Vector((0, 0, z[0])) for l, z in zip(ls, zz)]
        for i in range(6):
            q = [bot[i], bot[i + 1], top[i + 1], top[i]]
            for flip in (False, True):
                vs = [bm.verts.new(c) for c in (q[::-1] if flip else q)]
                f = bm.faces.new(vs)
                for l, (a, b) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    l[uvl].uv = (rect[0] + (rect[2] - rect[0]) * a, rect[1] + (rect[3] - rect[1]) * b)
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name)); bpy.context.collection.objects.link(o)
    bm.to_mesh(o.data); bm.free(); o.data.materials.append(mat); o.data.update()
    o["g"] = name
    return o


def kado_name(deg, arms, neg_zero=False):
    hand = "M" if (deg < 0 or neg_zero) else ""
    a = "" if arms is None else "_A%dx%d" % (int(round(arms[0] * 100)), int(round(arms[1] * 100)))
    return "Neribei_Kado_%02d%s%s" % (int(round(abs(deg))), hand, a)


def build_kado(deg, arms=None, neg_zero=False):
    """留め継ぎの隅。Blender の作り(build_kado.py と同じ): 入りの腕 = +y(走りは −y)/ 化粧面 = +x / 原点 = 折れ点・足元。
    留め面の法線 n = (sgn·sin(Δ/2), cos(Δ/2), 0)(deg > 0 で Unity の yaw が増える折れ)。入りの腕は n 側を残し、
    出の腕は「腕の長さ b で切った入りの腕」を留め面で鏡に写した物。"""
    V.reset()
    g, shift, uv_is, uv_hei = load(SRC_C)
    sec = section(g)
    # 瓦の天端の勾配と軒の半幅(yane の外形から)
    ya = g["yane"].data
    ym = max(abs(v.co.y) for v in ya.vertices)
    zn = max(v.co.z for v in ya.vertices if abs(v.co.y) < 0.12)
    zf = max(v.co.z for v in ya.vertices if abs(v.co.y) > ym - 0.06)
    sec["roof_slope"] = (zn - zf) / (ym - 0.03 - 0.06)
    sec["eave_half"] = max(abs(v.co.y) for v in ya.vertices)
    sec["ridge_top"] = zn
    nk = g["noki"].data
    sec["eave_z"] = min(v.co.z for v in nk.vertices if abs(v.co.y) > max(abs(w.co.y) for w in nk.vertices) - 0.03) + 0.01
    g_noki = dup(g["noki"])
    src_x0 = min(v.co.x for o in g.values() for v in o.data.vertices)
    full = ARM_FULL_TILES * TILE
    aIn, aOut = (full, full) if arms is None else arms
    sgn = -1.0 if (deg < 0 or neg_zero) else 1.0
    h = math.radians(max(abs(deg), 1e-3)) * 0.5
    n = (sgn * math.sin(h), math.cos(h), 0.0)
    mat = mat_of(g)
    mune_src = dup(g["mune"])
    back = max(sec["eave_half"], sec["yb"]) * math.tan(h) + 0.3   # 折れ点の手前に要る長さ
    arm_objs = []
    for which, a in (("A", aIn), ("B", aOut)):
        # 走り x の帯 [−back, a] を作り、走りを +y へ回す(x → y・y → −x)
        parts = tile_run(g, -back, a, src_x0)
        R = Matrix.Rotation(math.pi / 2, 4, 'Z')
        for c in parts:
            xform(c, R)
            cut(c, (0, 0, 0), n, True)
        parts = [c for c in parts if len(c.data.polygons)]
        cp = cap_object("koguchi", mat, [((0, a, 0), (0, 1, 0), (-1, 0, 0), (0, 1, 0))], sec, uv_is, uv_hei)
        parts.append(cp)
        if which == "B":
            Mr = reflect_m(n)
            for c in parts:
                xform(c, Mr)
        arm_objs += parts
    clear_src(g)
    if abs(deg) >= 5.0:
        arm_objs.append(hip(mune_src, mat, h, sgn, sec))
    if abs(deg) >= 1.0:
        # 軒裏の留めの板: 壁の面(HALF_T・壁の天端)から軒先(軒の半幅・軒の下端 + 0.01)へ、上は瓦の天端 − 0.03
        ym = sec["eave_half"]
        zf = soffit_z([o for o in arm_objs if gname(o) in ("noki", "taruki", "yane")], h, sgn, 0.08)
        arm_objs.append(miter_plate(mat, uv_rect_of(g_noki)[0], h, sgn, zf, HALF_T, ym - 0.01))
    bpy.data.objects.remove(mune_src, do_unlink=True)
    bpy.data.objects.remove(g_noki, do_unlink=True)
    objs = merge_groups(arm_objs)
    arms_n = None if (abs(aIn - full) < 1e-6 and abs(aOut - full) < 1e-6) else (aIn, aOut)
    name = kado_name(deg, arms_n, neg_zero)
    path = finish(objs, name)
    xs = [v.co.x for o in objs for v in o.data.vertices]; ys = [v.co.y for o in objs for v in o.data.vertices]
    print("[neri]   隅 Δ=%+.3f° 腕(入り %.3f・出 %.3f・素 %.3f)・張り出し(折れ点より先)%.3f・瓦の勾配 %.3f・軒の半幅 %.3f"
          % (deg if not neg_zero else -0.0, aIn, aOut, full, max(0.0, -min(ys)), sec["roof_slope"], sec["eave_half"]))
    return objs, path


# ---------------------------------------------------------------- 検め(背景マゼンタ・光線・四方)
def hook_s_heimap():
    for m in bpy.data.materials:
        if m.name.startswith("s_heimap"):
            m.use_nodes = True; nt = m.node_tree
            bsdf = next((nd for nd in nt.nodes if nd.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                img = nt.nodes.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(TEX, check_existing=True)
                nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
                bsdf.inputs['Alpha'].default_value = 1.0
        m.use_backface_culling = True
        try:
            m.use_backface_culling_shadow = False
        except Exception:
            pass


def front_rays(objs, lo, hi):
    """表を向いた面だけ当たる(Unity の裏面カリング)光線で、壁体の高さの格子が抜ける割合を向きごとに数える。"""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world)
        me = bpy.data.meshes.new("t"); t.to_mesh(me); bm.from_mesh(me); t.free(); bpy.data.meshes.remove(me)
    bvh = BVHTree.FromBMesh(bm)
    def hit(o, d):
        for _ in range(80):
            r = bvh.ray_cast(o, d, 60.0)
            if r[0] is None:
                return False
            if r[1].dot(d) < 0:
                return True
            o = r[0] + d * 1e-4
        return False
    res = {}
    for nm, d in (("外から(+y)", (0, 1, 0)), ("内から(−y)", (0, -1, 0)), ("斜め45 内", (0.707, -0.707, 0)),
                  ("斜め45 外", (0.707, 0.707, 0)), ("小口 +x", (1, 0, 0)), ("小口 −x", (-1, 0, 0)), ("上から", (0, 0, -1)),
                  ("下から(軒裏)", (0, 0, 1))):
        dv = Vector(d).normalized(); tot = ok = 0
        for i in range(60):
            for j in range(20):
                if nm.startswith("小口"):
                    y = -HALF_T + 0.02 + (2 * HALF_T - 0.04) * (i + 0.5) / 60.0; z = 0.05 + 2.25 * (j + 0.5) / 20.0
                    o = Vector((lo.x - 1 if d[0] > 0 else hi.x + 1, y, z))
                elif nm == "上から":
                    x = lo.x + 0.1 + (hi.x - lo.x - 0.2) * (i + 0.5) / 60.0; y = -0.5 + 1.0 * (j + 0.5) / 20.0
                    o = Vector((x, y, hi.z + 1))
                elif nm.startswith("下から"):
                    x = lo.x + 0.1 + (hi.x - lo.x - 0.2) * (i + 0.5) / 60.0; y = -0.55 + 1.1 * (j + 0.5) / 20.0
                    o = Vector((x, y, -1.0))
                else:
                    x = lo.x + 0.3 + (hi.x - lo.x - 0.6) * (i + 0.5) / 60.0; z = 0.05 + 2.25 * (j + 0.5) / 20.0
                    o = Vector((x, 0.0, z)) - dv * 6.0
                tot += 1; ok += hit(o, dv)
        res[nm] = round(1.0 - ok / max(tot, 1), 4)
    bm.free()
    return res


def boundary_edges(objs):
    n = 0
    for o in objs:
        bm = bmesh.new(); bm.from_mesh(o.data)
        n += sum(1 for e in bm.edges if e.is_boundary); bm.free()
    return n


def render_views(objs, stem, rays=True):
    """表・裏・両小口・上・下・内の斜め低い目線。背景はカメラにだけマゼンタ(照明は灰)。"""
    hook_s_heimap()
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    info = {"bbox_blender": [[round(lo[i], 3), round(hi[i], 3)] for i in range(3)]}
    if rays:
        info["抜け(光線)"] = front_rays(objs, lo, hi)
    c = (lo + hi) / 2; R = max((hi - lo).length * 0.7, 3.0) + 1.0
    cam = V.studio((0, -10, 2), tuple(c), res=(1100, 720))
    wt = bpy.context.scene.world.node_tree
    bg = wt.nodes["Background"]; bg.inputs[0].default_value = (0.6, 0.62, 0.66, 1); bg.inputs[1].default_value = 1.0
    mg = wt.nodes.new("ShaderNodeBackground"); mg.inputs[0].default_value = (1, 0, 1, 1)
    lp = wt.nodes.new("ShaderNodeLightPath"); mx = wt.nodes.new("ShaderNodeMixShader")
    wt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); wt.links.new(bg.outputs[0], mx.inputs[1]); wt.links.new(mg.outputs[0], mx.inputs[2])
    wt.links.new(mx.outputs[0], wt.nodes["World Output"].inputs[0])
    os.makedirs(SHOTS, exist_ok=True)
    def shot(nm, loc, look, ortho=None):
        cam.location = loc
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        if ortho:
            cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
        else:
            cam.data.type = 'PERSP'; cam.data.lens = 35
        p = os.path.join(SHOTS, "%s_%s.png" % (stem, nm)); V.render(p); return p
    files = []
    # Blender −y = Unity +Z(外)
    files.append(shot("omote", (c.x - R * 0.35, c.y - R, c.z + 0.6), (c.x, c.y, c.z)))
    files.append(shot("ura", (c.x + R * 0.35, c.y + R, c.z + 0.6), (c.x, c.y, c.z)))
    files.append(shot("koguchiA", (lo.x - R * 0.8, c.y - 0.5, c.z + 0.3), (lo.x, c.y, c.z)))
    files.append(shot("koguchiB", (hi.x + R * 0.8, c.y + 0.5, c.z + 0.3), (hi.x, c.y, c.z)))
    files.append(shot("ue", (c.x, c.y, hi.z + 25), (c.x, c.y, 0), ortho=max(hi.x - lo.x, hi.y - lo.y) * 1.15))
    files.append(shot("shita", (c.x + 0.4, c.y - 1.4, 0.25), (c.x, c.y, 2.25)))
    files.append(shot("uchi_naname", (c.x + R * 0.7, c.y + R * 0.6, 0.9), (c.x, c.y, 1.3)))
    info["files"] = files
    json.dump(info, open(os.path.join(SHOTS, stem + "_info.json"), "w"), ensure_ascii=False, indent=1)
    print("[neri] 検め " + json.dumps(info, ensure_ascii=False))
    return info


# ---------------------------------------------------------------- 岡部の一式
OKABE_KADO = ["00", "00M", "01", "01M", "07M", "12", "12M", "16", "16M", "18M", "19M", "22", "22M", "27", "35M",
              "39", "76M", "78", "90"]    # 区画 okabe の練塀の隅 25 基の折れ(KadoDeg の四捨五入・M = 負)。prefab の Dobei_Kado_* と同じ 19 種


def parse_kado(tok):
    neg = tok.endswith("M")
    v = float(tok[:-1] if neg else tok)
    if neg:
        return -abs(v) if v != 0 else 0.0, v == 0
    return v, False


def run_job(argv, do_render):
    if "--choku" in argv:
        objs, path = build_straight(NTILE)
        if do_render: render_views(objs, "Neribei_Choku")
    if "--kiri" in argv:
        k = int(argv[argv.index("--kiri") + 1])
        assert 1 <= k < NTILE, "--kiri は瓦 1〜13 枚"
        objs, path = build_straight(k)
        if do_render: render_views(objs, "Neribei_Kiri_T%02d" % k)
    if "--end" in argv:
        build_end((lambda objs, path: render_views(objs, os.path.splitext(os.path.basename(path))[0])) if do_render else None)
    if "--kado" in argv:
        deg, nz = parse_kado(argv[argv.index("--kado") + 1])
        arms = None
        if "--arms" in argv:
            arms = tuple(float(t) for t in argv[argv.index("--arms") + 1].split(","))
        objs, path = build_kado(deg, arms, nz)
        if do_render: render_views(objs, os.path.splitext(os.path.basename(path))[0])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    if "--okabe" in argv:
        jobs = [["--choku"], ["--end"]] + [["--kiri", str(k)] for k in range(1, NTILE)] + [["--kado", t] for t in OKABE_KADO]
        for j in jobs:
            run_job(j, do_render and j[0] in ("--choku", "--end"))
        return
    if "--list" in argv:
        for line in open(argv[argv.index("--list") + 1], encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                run_job(line.split(), do_render)
        return
    run_job(argv, do_render)


if __name__ == "__main__":      # build_dobei2.py が道具を import する
    main()
