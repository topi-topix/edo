"""Village Kit を Blender で扱う共通ヘルパ。
FBX には Unity 側のマテリアル設定が入っていないので、マテリアル名から
textures/ の PNG を引いて手で結線する。"""
import bpy, os, mathutils

ROOT = "/Users/toshio/project/edo-unity/Assets/Japanese Village Kit"
MESH = os.path.join(ROOT, "Meshes")
TEX  = os.path.join(ROOT, "textures")
KEN  = 1.818          # 江戸間 1間
VK_KEN = 2.0          # Village Kit の1間相当
S    = KEN / VK_KEN   # 0.909


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def hook_textures():
    """マテリアル名 -> <name>_AlbedoTransparency / _Normal / _MaskMap を結線"""
    for m in bpy.data.materials:
        base = m.name.split('.')[0]
        # ⚠ Village Kit の FBX は TransparencyFactor が入っていて Alpha=0 で読まれる。
        #    直さないと「オブジェクトはあるのに何も写らない」レンダになる。
        if m.use_nodes:
            b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b:
                b.inputs['Alpha'].default_value = 1.0
        m.surface_render_method = 'DITHERED'
        base = {"roof ornaments": "roof ornament"}.get(base, base)   # 部材名とテクスチャ名の綴り違い
        alb = os.path.join(TEX, base + "_AlbedoTransparency.png")
        if not os.path.exists(alb):
            alb = os.path.join(TEX, base + "_Albedo.png")
        if not os.path.exists(alb):
            continue
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(alb, check_existing=True)
        img.location = (-600, 300)
        nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.75
        nrm = os.path.join(TEX, base + "_Normal.png")
        if os.path.exists(nrm):
            ni = nt.nodes.new('ShaderNodeTexImage')
            ni.image = bpy.data.images.load(nrm, check_existing=True)
            ni.image.colorspace_settings.name = 'Non-Color'
            ni.location = (-600, -100)
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.location = (-300, -100)
            nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])


def imp(relpath):
    """FBX を1つ読み込み、メッシュを親(Empty)から外して world 変換を焼き込んで返す。
    ⚠ 外さずに o.location を触ると、親の回転/スケール込みでどこかへ飛ぶ。"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MESH, relpath))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return meshes


def bbox(objs):
    # ⚠ o.location を書いただけでは matrix_world は古いまま(depsgraph 未更新)。
    #    これで畳のピボットが半畳ずれた。測る前に必ず更新する。
    bpy.context.view_layer.update()
    mn = mathutils.Vector((1e9,) * 3); mx = mathutils.Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    return mn, mx


def sel(objs, active=0):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[active]


def place(relpath, x=0.0, y=0.0, z=0.0, rot=0.0, scale=None, drop_lod=True):
    """FBX を江戸間スケールで読み、bbox最小角を原点に正規化 → Z回転 → (x,y,z)。
    戻り値はオブジェクト列。位置指定は常に「フットプリントの最小角」基準。"""
    import math
    objs = imp(relpath)
    if drop_lod:
        keep = [o for o in objs
                if not o.name.startswith('C_') and not o.name.endswith('_LOD1')]
        for o in objs:
            if o not in keep:
                bpy.data.objects.remove(o, do_unlink=True)
        objs = keep
    if not objs:
        return []
    s = S if scale is None else scale
    sel(objs)
    if abs(s - 1.0) > 1e-9:
        bpy.ops.transform.resize(value=(s, s, s), center_override=(0, 0, 0))
        bpy.ops.object.transform_apply(scale=True)
    _zero(objs)
    if abs(rot) > 1e-6:
        rotate_z(objs, rot)
        _zero(objs)
    for o in objs:
        o.location += mathutils.Vector((x, y, z))
    return objs


def rotate_z(objs, deg):
    """Z軸まわりに反時計回りで回して焼き込む。
    ⚠ bpy.ops.transform.rotate は正の値で**時計回り**に回る(ギズモの符号)。
       屋根面が90°ずれて原因究明に時間を使ったので ops は使わない。"""
    import math
    R = mathutils.Matrix.Rotation(math.radians(deg), 4, 'Z')
    for o in objs:
        o.matrix_world = R @ o.matrix_world
    sel(objs)
    bpy.ops.object.transform_apply(rotation=True)


def _zero(objs):
    mn, _ = bbox(objs)
    for o in objs:
        o.location -= mn
    sel(objs)
    bpy.ops.object.transform_apply(location=True)


def dedup_materials():
    """同じ FBX を複数回読むと 'floor.001' のような複製ができる。
    Unity 側の Search&Remap は名前一致なので、必ず元の名前へ寄せてから join する。"""
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        for slot in o.material_slots:
            m = slot.material
            if m is None or '.' not in m.name:
                continue
            base = m.name.rsplit('.', 1)[0]
            if base in bpy.data.materials and m.name.rsplit('.', 1)[1].isdigit():
                slot.material = bpy.data.materials[base]


def join(objs, name):
    """複数メッシュを1つに。マテリアルスロットは維持される。"""
    objs = [o for o in objs if o and o.name in bpy.data.objects]
    if not objs:
        return None
    sel(objs)
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    o.data.name = name
    return o


def set_origin(o, point):
    """オブジェクト原点(=Unityのピボット)をワールド座標 point に置く"""
    bpy.context.scene.cursor.location = point
    sel([o])
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.context.scene.cursor.location = (0, 0, 0)


def borrow_material(src_fbx, mat_name):
    """部材を一度読んでマテリアルだけ取り、オブジェクトは捨てる。
    新規マテリアルを作らずキットのものを使い回すため(リアルさを既存建物と揃える)"""
    m = bpy.data.materials.get(mat_name)
    if m:
        return m
    objs = imp(src_fbx)
    m = bpy.data.materials.get(mat_name)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return m


def sample_uv(src_fbx, pick_high=True):
    """部材のUVから代表点を1つ取る。新造ジオメトリはアトラス内の狙った領域に**一点で**貼る
    — 平面投影するとアトラスを跨いで柄が混ざる。
    ⚠ 複数面のUVを平均すると別領域(腰板など)に落ちる。最大面1枚だけ見る。"""
    objs = imp(src_fbx)
    me = objs[0].data
    uvl = me.uv_layers.active.data
    zs = [p.center.z for p in me.polygons]
    lo, hi = min(zs), max(zs)
    thr = lo + (hi - lo) * (0.65 if pick_high else 0.15)
    cand = [p for p in me.polygons
            if (p.center.z > thr if pick_high else p.center.z < thr)] or list(me.polygons)
    p = max(cand, key=lambda q: q.area)
    us = [uvl[li].uv for li in p.loop_indices]
    uv = (sum(u[0] for u in us) / len(us), sum(u[1] for u in us) / len(us))
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return uv


def sample_uv_bright(src_fbx, mat_name=None, want='bright'):
    """アトラスから「明るい面(紙・漆喰)」または「暗い面(漆・腰板)」の代表UVを取る。
    ⚠ 高さで選ぶ sample_uv は当てが外れる(door wall の上部を取ったら襖が真っ黒になった)。
       実際にアルベド画像を読んで、面の中心UVの明るさで選ぶ。"""
    import numpy as np
    objs = imp(src_fbx)
    me = objs[0].data
    uvl = me.uv_layers.active.data
    base = (mat_name or me.materials[0].name).split('.')[0]
    base = {"roof ornaments": "roof ornament"}.get(base, base)
    path = os.path.join(TEX, base + "_AlbedoTransparency.png")
    if not os.path.exists(path):
        path = os.path.join(TEX, base + "_Albedo.png")
    img = bpy.data.images.load(path, check_existing=True)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    buf = buf.reshape(h, w, 4)
    best, best_score = None, None
    for p in me.polygons:
        us = [uvl[li].uv for li in p.loop_indices]
        u = sum(q[0] for q in us) / len(us)
        v = sum(q[1] for q in us) / len(us)
        px = int(min(max(u, 0.0), 0.999) * (w - 1))
        py = int(min(max(v, 0.0), 0.999) * (h - 1))
        lum = float(buf[py, px, :3].mean())
        score = (lum if want == 'bright' else (1.0 - lum)) * (p.area ** 0.25)
        if best_score is None or score > best_score:
            best_score, best = score, (u, v)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return best


def set_uv(obj, uv):
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    for d in me.uv_layers.active.data:
        d.uv = uv


def box(name, size, center, mat=None, uv=None):
    """軸平行の直方体。size/center は (x,y,z)"""
    sx, sy, sz = (s / 2.0 for s in size)
    cx, cy, cz = center
    v = [(cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
         (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
         (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
         (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)]
    f = [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4],
         [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    me = bpy.data.meshes.new(name)
    me.from_pydata([mathutils.Vector(x) for x in v], [], f)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    if mat:
        o.data.materials.append(mat)
    if uv:
        set_uv(o, uv)
    return o


def export_fbx(objs, path):
    """Unity 向け FBX 書き出し。マテリアル名は Village Kit のまま残すので
    Unity 側で既存の .mat に Search&Remap できる。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sel(objs if isinstance(objs, list) else [objs])
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, apply_unit_scale=True,
        global_scale=1.0, apply_scale_options='FBX_SCALE_NONE',
        axis_forward='-Z', axis_up='Y', bake_space_transform=True,
        object_types={'MESH'}, use_mesh_modifiers=True,
        mesh_smooth_type='FACE', path_mode='STRIP', embed_textures=False)
    return path


def studio(cam_loc, look_at, ortho_scale=None, res=(1600, 900)):
    """カメラ+3灯+床。EEVEE でレンダする準備"""
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.1

    cam_data = bpy.data.cameras.new("C")
    if ortho_scale:
        cam_data.type = 'ORTHO'; cam_data.ortho_scale = ortho_scale
    cam = bpy.data.objects.new("C", cam_data)
    sc.collection.objects.link(cam); sc.camera = cam
    cam.location = cam_loc
    d = mathutils.Vector(look_at) - mathutils.Vector(cam_loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

    sun = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN'))
    sun.data.energy = 3.0; sun.data.angle = 0.15
    sun.rotation_euler = (0.85, 0.15, 1.05)
    sc.collection.objects.link(sun)
    fill = bpy.data.objects.new("F", bpy.data.lights.new("F", 'SUN'))
    fill.data.energy = 1.0
    fill.rotation_euler = (1.1, 0.0, -2.2)
    sc.collection.objects.link(fill)
    return cam


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
