"""**練塀の端を隣の辺の線で斜めに切った駒**(EDO-0502 2026-10-03・岡部 SE_Hei の始め / S_Hei_21 の終わり)。

    blender --background --python Tools/Blender/build_dobei_kiri.py -- 84.89 --render     # → Dobei_Kiri_849_L
    blender --background --python Tools/Blender/build_dobei_kiri.py -- 25.5 --render      # → Dobei_Kiri_255_L
    blender --background --python Tools/Blender/build_dobei_kiri.py -- 84.89 --R --render # → Dobei_Kiri_849_R(逆手)
    blender --background --python Tools/Blender/build_dobei_kiri.py -- 71.608 --render    # → Dobei_Kiri_716_L(門長屋の妻で切る)

【なぜ要るか】外周の練塀(`EdoBuild.DobeiRun` = edogoyomi `s_hei_center` の表裏2枚1組)の端は走りに直角。
  区画の角で隣の辺が斜めに来ると、壁体の深い側の角が先に隣の辺の線に当たり、`KeepInsidePoly` が駒を引くので
  浅い側(見え面)に楔の口が残る(辺0 の始め 0.053m)。伸ばすと区画の線を越える(硬い)。
  ⇒ 端を隣の辺の線(鉛直な面)で切った駒を一つ据え、残りの run はこの駒の直角の端へ継ぐ。

【作り】**ゼロから作らない。**`s_hei_center.obj` を DobeiRun と同じ組(表 = そのまま・裏 = 180° 回して内へ 0.20m・
  走りの外形を揃える)で**実寸(×1.818)**に焼き、1 枚分(走り 2.990)を斜めの鉛直面で切る。
  切り口の壁体(表裏の板の間)は素の板が片面ポリなので覗くと抜ける ⇒ 断面の形(腰の石垣の帯 + 板の帯)で塞ぐ。
  塞ぐ面の UV は素の `ishigaki` / `hei` の UV の矩形(一点貼りにしない)。屋根(瓦・垂木・軒)は切りっぱなし
  (直角の端の素と同じ見え)。材は `s_heimap` のまま。

【局所座標(Unity)】幅 = X(走り)/ 高さ = Y / 厚み = Z・**+Z = 見え面(区画の外)**。
  **ピボット = 切り口と壁体の外面(腰の石垣の表)の交点・足元**。切る端は **+X**、直角の端は X = −2.990。
  壁体は Z ∈ [−t, 0](t = 0.636・外面 0 / 内面 −t)。屋根は外へ 0.357・内へ 0.993(外面から)出る。
  角 deg = 切り口の平面の線が走りとなす角(IshigakiKiri と同じ測り方)。深さ w ごとに切り口は走りへ w·cot(deg) 退く。
  `L` = **見え面の側が長い**(外面の切り口がいちばん先 = ピボット)。`S` は鏡(内面が長い)。
  `--R` = **逆手**(EDO-0502 2026-10-04): 切る端を **−X** へ・走りは +X へ(直角の端は X = +2.990)。
     見え面が長いのは `L` と同じで、`L` を YZ 面で写した形(素を鏡にせず、組を −x 側へ置いて切る ── 巻きが裏返らない)。
     綴りは `R`(`L` の逆手)/ `SR`(`S` の逆手)。⭐ 手の取り方: 外から見て角が**左**(走りの終わり)なら `L`、
     **右**(走りの始め)なら `R`(局所 +X は外から見て左)。
  ⭐ 据え: position = 外面の線(犬走りへ寄せた後の壁体の外面)と隣の辺の線の交点 / yaw = 外向き法線の方位
     (+Z を外へ・+X を角の側へ)/ scale = 1(FBX は実寸 m)/ y = DobeiRun の座(SeatBottom と同じ底)。
  ⭐ DobeiRun の横の基準(表の駒の外接の中央)は、この駒の局所 Z = −0.218(外面から 0.218 内)。

【落とし穴】
  ・素は片面ポリ: 表の板の表は Blender +Y を向く ⇒ 表を 180° 回して外(Unity +Z = Blender −Y)へ向ける。
  ・bisect は面の無い辺・頂点を残す ⇒ 消す(bounds が嘘をつく)。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ROOT = V.REPO
SRC = os.path.join(ROOT, "Assets/edogoyomi/es_dobei/s_hei_center.obj")
OUT = V.out_dir(os.path.join(ROOT, "Assets/Edo/Models/Kado"))
if os.environ.get("BUZAI_SPEC_OUT"):
    V.SPEC_DIR = os.environ["BUZAI_SPEC_OUT"]
ES = 1.818            # edogoyomi の倍率(DobeiRun の sx の公称 = pitch / W = ES)
BACK_IN = 0.20        # 裏の駒を内へ寄せる量(DobeiRun の latOff −0.2・世界 m)
BODY = ("ishigaki", "shitami", "hei", "hashira2", "san")   # 壁体(屋根を除く)
PANEL = ("shitami", "hei", "hashira2", "san")


def read_groups():
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=SRC, forward_axis='Z', up_axis='Y', use_split_groups=True)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    V.sel(new); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return new


def gname(o):
    return o.name.split(".")[0]


def compose():
    """DobeiRun の組を実寸で。戻り値 (表の群, 裏の群, 走りの外形 [x0,x1])。Blender: 走り x / 内 +y / 上 z。"""
    F = read_groups()
    B = read_groups()
    V.dedup_materials()
    S = Matrix.Scale(ES, 4)
    Rz = Matrix.Rotation(math.pi, 4, 'Z')
    for o in F:                                  # 表: 板の表を −y(外)へ
        o.data.transform(Rz @ S); o.data.update()
    for o in B:
        o.data.transform(S); o.data.update()
    fx = [v.co.x for o in F for v in o.data.vertices]
    bx = [v.co.x for o in B for v in o.data.vertices]
    fy = [v.co.y for o in F for v in o.data.vertices]
    by = [v.co.y for o in B for v in o.data.vertices]
    # 裏: 走りの外形を表に揃え、外接の中央を表の中央から内へ 0.20(ButtOnRun と同じ測り)
    dx = min(fx) - min(bx)
    dy = (min(fy) + max(fy)) * 0.5 + BACK_IN - (min(by) + max(by)) * 0.5
    for o in B:
        o.data.transform(Matrix.Translation(Vector((dx, dy, 0)))); o.data.update()
    return F, B, (min(fx), max(fx))


def ext(objs, names, axis, fn):
    vals = [getattr(v.co, axis) for o in objs if gname(o) in names for v in o.data.vertices]
    return fn(vals)


def cut(o, co, no, keep_positive):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                           plane_co=co, plane_no=no, clear_outer=not keep_positive, clear_inner=keep_positive)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()


def uv_rect_of(objs, name):
    """素の群 name の**いちばん大きい面**の UV の外接矩形と、その面の実寸(走り m・高さ m)。
    ⚠ 群の全部の面の UV を束ねると隣の柄(家紋の札)を跨ぐ(ishigaki の天端の面が u 0.12〜0.80 に跨る)。"""
    best = None
    for o in objs:
        if gname(o) != name:
            continue
        me = o.data; uvl = me.uv_layers.active.data
        for p in me.polygons:
            if best is None or p.area > best[0]:
                us = [uvl[i].uv[0] for i in p.loop_indices]; vs = [uvl[i].uv[1] for i in p.loop_indices]
                co = [me.vertices[v].co for v in p.vertices]
                w = max(c.x for c in co) - min(c.x for c in co); h = max(c.z for c in co) - min(c.z for c in co)
                best = (p.area, (min(us), min(vs), max(us), max(vs)), (w, h))
    return best[1], best[2]


def build(deg, hand="L", m=1.0):
    """m = +1: 切る端 +X(Unity)/ −1: 逆手(切る端 −X)。"""
    V.reset()
    F, B, (x0, x1) = compose()
    P = x1 - x0                                   # 1 枚の走り(2.990)
    allo = F + B
    # 設計値(組の作図から)
    y_out = ext(F, ("ishigaki",), "y", min)        # 壁体の外面(腰の石垣の表)
    y_in = ext(B, ("ishigaki",), "y", max)         # 壁体の内面
    y_po = ext(F, PANEL, "y", min)                 # 表の板の外
    y_pi = ext(B, PANEL, "y", max)                 # 裏の板の内
    z_i = ext(F, ("ishigaki",), "z", max)          # 腰の石垣の天端
    z_t = ext(F, ("hei",), "z", max)               # 板(漆喰)の天端 = 桁の下
    z_top = max(v.co.z for o in allo for v in o.data.vertices)
    y_lo = min(v.co.y for o in allo for v in o.data.vertices)
    y_hi = max(v.co.y for o in allo for v in o.data.vertices)
    y_front_c = (ext(F, BODY + ("yane", "noki", "taruki", "mune", "keta"), "y", min)
                 + ext(F, BODY + ("yane", "noki", "taruki", "mune", "keta"), "y", max)) * 0.5
    ct = 1.0 / math.tan(math.radians(deg))
    sg = 1.0 if hand == "L" else -1.0
    # 原点へ: 外面を y=0・切る端(Unity +X = Blender −x)の外面の切り口を x=0。走りは +x へ P
    #   L: 深さ w(=y)で切り口が +x へ w·ct 退く。必要な −x 側の張り出し = 外へ出る屋根の深さ(y<0)·ct
    #   逆手(m=−1)は 1 枚を x ∈ [−P, 0] に置き、切る端は x = 0(Blender の +x 端 = Unity −X)
    for o in allo:
        o.data.transform(Matrix.Translation(Vector((-(x0 if m > 0 else x1), -y_out, 0)))); o.data.update()
    t = y_in - y_out
    yl, yh = y_lo - y_out, y_hi - y_out
    need = max(-yl * ct, yh * ct) if hand == "L" else max(yh * ct, -yl * ct)
    nmod = 1 + int(math.ceil((need + 0.05) / P))
    # 走りへ継ぐ: 枠 [−(nmod−1)·P, P] を覆い、直角の端は x = P(1 枚分)
    parts = []
    for k in range(nmod):
        for o in allo:
            c = o.copy(); c.data = o.data.copy(); bpy.context.collection.objects.link(c)
            c.data.transform(Matrix.Translation(Vector((-m * k * P, 0, 0)))); c.data.update()
            c["g"] = gname(o)
            parts.append(c)
    uv_is = uv_rect_of(allo, "ishigaki"); uv_hei = uv_rect_of(allo, "hei")
    for o in allo:
        bpy.data.objects.remove(o, do_unlink=True)
    # 切る: 面の線 m·x = sg·ct·y(外面 y=0 で x=0)。残すのは m·x ≥ sg·ct·y の側(走りの側)
    no = Vector((m, -sg * ct, 0.0)).normalized()
    for o in parts:
        cut(o, Vector((0, 0, 0)), no, True)
    parts = [o for o in parts if len(o.data.polygons)]
    body = [o for o in parts if o["g"] in BODY]
    tag = hand if m > 0 else ("R" if hand == "L" else "SR")
    name = "Dobei_Kiri_%03d_%s" % (int(round(deg * 10)), tag)
    o = V.join(parts, name)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(o.data); bm.free(); o.data.update()

    # 切り口の壁体を塞ぐ: 腰の帯 [0, t] × [0, z_i] と 板の帯 [y_po', y_pi'] × [z_i, z_t]
    ypo, ypi = y_po - y_out, y_pi - y_out
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active
    mi = 0
    def onplane(y, z):
        return Vector((m * sg * ct * y, y, z))
    def face(ys, zs, rect_sz):
        """切り口の上の多角形。UV は面の実寸(切り口に沿った長さ・高さ)を素の面の m あたりの密度で矩形へ。
        矩形に収まらなければ一様に縮める(柄の縦横比を保つ)。"""
        rect, (w, h) = rect_sz
        vs = [bm.verts.new(onplane(y, z)) for y, z in zip(ys, zs)]
        f = bm.faces.new(vs)
        f.material_index = mi
        bm.normal_update()
        if f.normal.dot(-no) < 0:                 # 切り捨てた側(−x)へ向ける
            f.normal_flip()
        L = math.sqrt(1.0 + ct * ct)               # 切り口に沿った長さ = y·L
        y0 = min(ys); z0 = min(zs)
        su = (rect[2] - rect[0]) / w; sv = (rect[3] - rect[1]) / h      # 素の面の uv / m
        span_u = (max(ys) - y0) * L * su; span_v = (max(zs) - z0) * sv
        k = min(1.0, (rect[2] - rect[0]) / max(span_u, 1e-6), (rect[3] - rect[1]) / max(span_v, 1e-6))
        for l in f.loops:
            l[uvl].uv = (rect[0] + (l.vert.co.y - y0) * L * su * k, rect[1] + (l.vert.co.z - z0) * sv * k)
        return f
    face([0.0, t, t, 0.0], [0.0, 0.0, z_i, z_i], uv_is)
    face([ypo, ypi, ypi, ypo], [z_i, z_i, z_t, z_t], uv_hei)
    bm.to_mesh(me); bm.free(); me.update()
    # Unity +X = Blender −x なので、+x へ延びる走りは Unity では −X(直角の端 = Unity X −P)
    V.set_origin(o, (0.0, 0.0, 0.0))
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print("[dkiri] %s 角 %.2f°(cot %.4f)P=%.3f 組 %d 枚 / x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f] 面=%d"
          % (name, deg, ct, P, nmod, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), len(me.polygons)))
    print("[dkiri] 壁体 t=%.3f(外面 0・内面 %.3f)/ 板の帯 %.3f〜%.3f / 腰の天端 %.3f / 板の天端 %.3f / 棟 %.3f / DobeiRun の横の基準 %.3f 内"
          % (t, t, ypo, ypi, z_i, z_t, z_top, y_front_c - y_out))
    print("[dkiri] 内面の切り口は外面より走りへ %.3f 退く(手 m=%+d・直角の端 Unity X = %.3f)" % (sg * ct * t, m, -m * P))
    # 札(fence)。Unity 局所: X = −x・Z = −y(外 +Z)
    foot = [{"x": 0.0, "y": 0.0}, {"x": -m * sg * ct * t, "y": -t}, {"x": -m * P, "y": -t}, {"x": -m * P, "y": 0.0}]
    if m < 0:
        foot = [foot[0]] + foot[1:][::-1]           # 巻きの向きを L と揃える
    spec = {"prefab": "Assets/Edo/Models/Kado/%s.fbx" % name, "kind": "fence",
            "source": "Tools/Blender/build_dobei_kiri.py -- %g%s%s" % (deg, "" if hand == "L" else " --S", "" if m > 0 else " --R"),
            "unitScale": 1.0, "yBottom": 0.0,
            "foot": foot,
            "faceOut": 0.0, "faceIn": -t, "copingOverhang": 0.0, "height": z_top}
    path = os.path.join(OUT, name + ".fbx")
    V.export_fbx([o], path, kind="fence", spec=spec)
    print("[dkiri] wrote %s" % path)
    return o, path, dict(t=t, P=P, ct=ct, sg=sg, m=m, yc=y_front_c - y_out)


def render(o, path, g):
    """外(見え面)から斜めに切り口を・真上から・小口を正面から。隣の辺の線を赤い細い板で重ねる。"""
    V.hook_textures()
    shots = os.environ.get("BUZAI_SHOTS", os.path.join(ROOT, "Screenshots"))
    stem = os.path.splitext(os.path.basename(path))[0]
    # 隣の辺の線(切り口の面)・外面の線を目印に
    L = 3.0
    hm = g["m"]
    d = Vector((hm * g["sg"] * g["ct"], 1.0, 0.0)).normalized()
    m = bpy.data.meshes.new("line"); ob = bpy.data.objects.new("line", m); bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    a = bm.verts.new(-d * L * 0.4); b = bm.verts.new(d * L); c = bm.verts.new(d * L + Vector((0, 0, 0.02))); e = bm.verts.new(-d * L * 0.4 + Vector((0, 0, 0.02)))
    bm.faces.new([a, b, c, e]); bm.to_mesh(m); bm.free()
    mat = bpy.data.materials.new("mark_red"); mat.diffuse_color = (1, 0, 0, 1); mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0, 0, 1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 0, 0, 1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.0
    ob.data.materials.append(mat)
    ob.scale = (1, 1, 1)
    sc = bpy.context.scene
    V.studio((-3.5 * hm, -4.5, 3.2), (0.8 * hm, 0.3, 1.0), res=(1400, 900))
    V.render(os.path.join(shots, stem + "_out.png"))
    sc.camera.location = (-3.0 * hm, 3.5, 2.6)
    dd = Vector((0.8 * hm, 0.3, 1.0)) - sc.camera.location
    sc.camera.rotation_euler = dd.to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(shots, stem + "_in.png"))
    sc.camera.location = (1.2 * hm, 0.3, 30.0); sc.camera.rotation_euler = (0, 0, 0)
    sc.camera.data.type = 'ORTHO'; sc.camera.data.ortho_scale = 5.0
    V.render(os.path.join(shots, stem + "_plan.png"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    deg = float(argv[0])
    hand = "S" if "--S" in argv else "L"
    o, path, g = build(deg, hand, -1.0 if "--R" in argv else 1.0)
    if "--render" in argv:
        render(o, path, g)


main()
