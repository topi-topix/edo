"""**土塀 Dobei2m の系を練塀と同じ型で揃える**(EDO-0502 2026-10-12 施主「土塀も作り直したほうがよい。土塀の端には棟止め瓦が必要」)。

    blender --background --python Tools/Blender/build_dobei2.py -- --end --render       # → Dobei2_End_L / Dobei2_End_R(袖瓦 + 鬼瓦)
    blender --background --python Tools/Blender/build_dobei2.py -- --kiri 3 --render    # → Dobei2_Kiri_E3(1/8 枚 × 3 = 0.752)
    blender --background --python Tools/Blender/build_dobei2.py -- --kado 90 --render   # → Dobei2_Kado_90(腕は素 1.002)
    blender --background --python Tools/Blender/build_dobei2.py -- --kado 12M --arms 0.6,1.0
    blender --background --python Tools/Blender/build_dobei2.py -- --all                # 端 2・切り 7・隅(岡部と同じ 19 種)

【なぜ要るか】一体物の土塀 `Dobei2m`(build_dobei.py・白漆喰 + 腰板・瓦は `roof 2x2`・棟は `roof top x1`)は断面は閉じているが、
  ・端の駒 `Dobei2m_End` は袖瓦だけで**棟の端が開いたまま**(鬼瓦・巴が無い。build_dobei.oni() は定数が無く死んでいた)。
  ・隅(留め)と切り(端数)の駒が無い ⇒ 囲いの角で塀を突っ込むしかなかった(NeribeiRun の注)。
  ⇒ 直線 `Dobei2m` は**そのまま**(断面・材・寸法を変えない。8 か所の据えも変えない)。足すのは端・切り・隅。

【作り】⛔ ゼロから作らない。build_dobei.py の部品(壁体 slab・瓦場 tile_field・棟 ridge・袖瓦 sode_gawara)で 1 枚を組み、
  build_neribei.py の道具(継ぐ・切る・留め・鏡)で並べ替える。切り口の壁体は**断面の輪を面で塞ぐ**(壁体はもともと閉じた箱の列)。
  棟止めは build_goten_roof.oni(在庫 `roof ornaments L` の鬼 ── 御殿の棟端と同じ駒)を棟の幅へ縮めて据える。
  隅棟は在庫 `roof top x1` を留めの線へ継ぐ(build_dobei.ridge ── 大棟と同じ冠瓦)。材は全部在庫の名のまま
  (Fence_B_01 / Wall Exterior Defence / roof / roof ornaments)⇒ remap は Dobei2m と同じ。

【局所座標(Unity・実寸 scale 1)】⚠ **Dobei2m と同じ**: 走り +X ∈ [0, len](ピボット = 走りの始めの端・芯・足元)・+Y 上・厚み Z は芯対称。
  端: `_L` は棟止め(袖瓦・鬼瓦)が **X = 0 の側**(Dobei2m_End と同じ側)・`_R` は **X = 2.004 の側**。
  隅: build_neribei の隅と同じ据え(折れ点 = 両腕の芯の交点・足元 / 入りの腕は局所 −Z / 化粧面 −X)。
  切り: 長さ k·L/8(瓦の割付は 2.004 にしか周期が無いので継ぎ目で瓦の位相は合わない ── 走りの倍率で割り切る)。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_dobei as BD
import build_goten_roof as GR
import build_neribei as NB

ROOT = V.REPO
OUT = V.out_dir(os.path.join(ROOT, "Assets/Edo/Models/Dobei"))
CANON = "Assets/Edo/Models/Dobei"
if os.environ.get("BUZAI_SPEC_OUT"):
    V.SPEC_DIR = os.environ["BUZAI_SPEC_OUT"]
SHOTS = os.environ.get("BUZAI_SHOTS", os.path.join(ROOT, "Screenshots"))
L = BD.L                     # 2.004
NE = 8                       # 切りの刻み L/8
ARM_FULL = L / 2.0           # 隅の素の腕 1.002(90° の留めの三角 = 屋根の半幅 0.50 を越える)
ONI_H = 0.42                 # 鬼瓦の高さ(棟 0.22 の上へ立つ・Dobei2m の棟の幅 0.30 に合わせ在庫 0.593 を縮める)


def module(gable=None):
    """build_dobei.build() と同じ 1 枚を、群(body / tiles / mune / sode)のまま返す。Blender: 走り x ∈ [0, L]・厚み y・上 z。"""
    V.reset()
    wall, WALL_UV = BD.castle_mat(BD.PLASTER_SRC, BD.PLASTER_MAT, "plaster")
    wood, W_UV = BD.vk_mat(BD.WOOD_SRC, BD.WOOD_MAT, "wood")
    WALL_UV = BD.crop(WALL_UV, BD.CROP_PLASTER, BD.CROP_PLASTER_HI)
    W_UV = BD.crop(W_UV, BD.CROP_WOOD)
    m = BD.Mesh()
    BD.slab(m, 0.0, BD.H_SHITAMI, BD.T_SHITAMI, W_UV, 0, 3, cap_top=False)
    BD.slab(m, BD.H_SHITAMI, BD.H_SHITAMI + BD.H_NUKI, BD.T_NUKI, W_UV, 0, 4, cap_top=True)
    e0 = BD.T_ROOF / 2.0
    h_wall_top = BD.H_KETA + (e0 - BD.T_WALL / 2.0) * BD.RATIO
    BD.slab(m, BD.H_SHITAMI + BD.H_NUKI, h_wall_top, BD.T_WALL, WALL_UV, 1, 2, cap_top=False)
    BD.wall_cap(m, 1, WALL_UV, e0, BD.T_WALL / 2.0, BD.H_KETA)
    body = m.build("body", [wood, wall])
    e = BD.T_ROOF / 2.0
    z_ridge = BD.H_KETA + e * BD.RATIO
    f1 = BD.tile_field([(0.0, -e), (L, -e), (L, 0.0), (0.0, 0.0)], (0.0, -e), 90, BD.H_KETA, "S")
    f2 = BD.tile_field([(L, e), (0.0, e), (0.0, 0.0), (L, 0.0)], (0.0, e), 270, BD.H_KETA, "N")
    tiles = V.join([q for q in (f1, f2) if q], "kawara")
    g = {"body": body, "kawara": tiles}
    if gable is not None:
        roofmat = bpy.data.materials.get("roof")
        ruv = V.sample_uv(BD.ROOF_MOD, pick_high=True)
        rrect = (ruv[0] - 0.01, ruv[1] - 0.01, ruv[0] + 0.01, ruv[1] + 0.01)
        mg = BD.Mesh()
        x_in, x_out = (BD.W_SODE, 0.0) if gable == 'L' else (L - BD.W_SODE, L)
        BD.sode_gawara(mg, 0, rrect, x_in, x_out, e, BD.H_KETA, z_ridge)
        g["sode"] = mg.build("sode", [roofmat or wood])
    mune = BD.ridge((0.0, 0.0, z_ridge - BD.SEAT_MUNE), (L, 0.0, z_ridge - BD.SEAT_MUNE), "mune", BD.W_MUNE, BD.H_MUNE)
    for q in mune:
        q.data = q.data.copy()
        V.sel([q]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        BD.clip_convex(q, [(0.0, -1.0), (L, -1.0), (L, 1.0), (0.0, 1.0)])
    g["mune"] = V.join([q for q in mune if len(q.data.polygons)], "mune")
    V.dedup_materials()
    for k, o in g.items():
        o["g"] = k; o.name = k
    return g, dict(z_ridge=z_ridge, e=e, mats=(wood, wall), uv=(W_UV, WALL_UV))


def section_cap(x, outward, info):
    """壁体の断面(build_dobei の作図の値: 腰板 ±T_SHITAMI/2・貫 ±T_NUKI/2・土壁 ±T_WALL/2・天端の三角)を x の平面に貼る。
    ⚠ 素の slab は面ごとに頂点を溶接しない(UV のため)ので、切り口の辺は輪にならず holes_fill では塞げない ⇒ 作図の値で貼る。"""
    (wood, wall), (W_UV, WALL_UV) = info["mats"], info["uv"]
    e0 = BD.T_ROOF / 2.0
    hw = BD.T_WALL / 2.0
    h_top = BD.H_KETA + (e0 - hw) * BD.RATIO
    zt = lambda t: BD.H_KETA + (e0 - abs(t)) * BD.RATIO
    y1 = BD.H_SHITAMI; y2 = y1 + BD.H_NUKI
    polys = [([(-BD.T_SHITAMI / 2, 0.0), (BD.T_SHITAMI / 2, 0.0), (BD.T_SHITAMI / 2, y1), (-BD.T_SHITAMI / 2, y1)], 0, W_UV),
             ([(-BD.T_NUKI / 2, y1), (BD.T_NUKI / 2, y1), (BD.T_NUKI / 2, y2), (-BD.T_NUKI / 2, y2)], 0, W_UV),
             ([(-hw, y2), (hw, y2), (hw, h_top), (-hw, h_top)], 1, WALL_UV),
             ([(-hw, h_top), (hw, h_top), (0.0, zt(0.0))], 1, WALL_UV)]
    me = bpy.data.meshes.new("koguchi"); o = bpy.data.objects.new("koguchi", me); bpy.context.collection.objects.link(o)
    me.materials.append(wood); me.materials.append(wall)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    for poly, mi, rect in polys:
        vs = [bm.verts.new(Vector((x, yy, zz))) for yy, zz in poly]
        f = bm.faces.new(vs); f.material_index = mi; f.normal_update()
        if f.normal.x * outward < 0:
            f.normal_flip()
        ys = [q[0] for q in poly]; zs = [q[1] for q in poly]
        for l in f.loops:   # 矩形へ写す(一点貼りにしない)
            l[uvl].uv = (rect[0] + (rect[2] - rect[0]) * (l.vert.co.y - min(ys)) / (max(ys) - min(ys)),
                         rect[1] + (rect[3] - rect[1]) * (l.vert.co.z - min(zs)) / (max(zs) - min(zs)))
    bm.to_mesh(me); bm.free(); me.update()
    o["g"] = "koguchi"
    return o


def tile(g, x0, x1, info=None):
    """1 枚 [0, L] を継いで [x0, x1] を覆い、切る(切り口の壁体は塞ぐ)。"""
    # ⚠ 枚の始めを x0 に置く(枚の継ぎ目を駒の中に作らない)。素の瓦場は枚の境で軒の鼻の板が突き付けになり、
    #   隅の駒の折れ点に継ぎ目が来ると見上げで割れ目が抜けた(2026-10-12 Dobei2_Kado_90)。
    parts = []
    nk = int(math.ceil((x1 - x0) / L - 1e-6))
    for k in range(nk):
        for name, o in g.items():
            c = NB.dup(o); NB.xform(c, Matrix.Translation(Vector((x0 + k * L, 0, 0)))); parts.append(c)
    for c in parts:
        NB.cut(c, (x0, 0, 0), (1, 0, 0), True)
        NB.cut(c, (x1, 0, 0), (1, 0, 0), False)
    parts = [c for c in parts if len(c.data.polygons)]
    if info is not None:
        if abs((x1 - x0) / L - round((x1 - x0) / L)) > 1e-6:
            parts.append(section_cap(x1, 1.0, info))
    return parts


def spec(x0, x1, top, source):
    hf = BD.T_SHITAMI / 2.0
    # Unity X = −x。Dobei2m の資産の局所は走り +X ∈ [0, len] ⇒ 書き出し前に x → −x で戻す(finish の前に鏡にしない ── 下の put_unity)
    return {"source": source, "unitScale": 1.0, "yBottom": 0.0,
            "foot": [{"x": x0, "y": -hf}, {"x": x1, "y": -hf}, {"x": x1, "y": hf}, {"x": x0, "y": hf}],
            "faceOut": hf, "faceIn": -hf, "copingOverhang": 0.0, "height": top}


def finish(objs, name, sp=None):
    path = os.path.join(OUT, name + ".fbx")
    if sp is not None:
        sp = dict(sp); sp["prefab"] = CANON + "/" + name + ".fbx"
        V.export_fbx(objs, path, kind="fence", spec=sp)
    else:
        V.export_fbx(objs, path)
    xs = [v.co.x for o in objs for v in o.data.vertices]; ys = [v.co.y for o in objs for v in o.data.vertices]
    zs = [v.co.z for o in objs for v in o.data.vertices]
    print("[dobei2] %s  Unity X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] 面 %d → %s"
          % (name, -max(xs), -min(xs), min(zs), max(zs), -max(ys), -min(ys), sum(len(o.data.polygons) for o in objs), path))
    return path


def build_kiri(k):
    g, info = module()
    Lk = k * L / NE
    parts = tile(g, 0.0, Lk, info)
    NB.clear_src(g)
    objs = NB.merge_groups(parts)
    top = max(v.co.z for o in objs for v in o.data.vertices)
    return objs, finish(objs, "Dobei2_Kiri_E%d" % k, spec(-Lk, 0.0, top, "Tools/Blender/build_dobei2.py -- --kiri %d" % k))


def build_end(on_done=None):
    """Dobei2m_End と同じ袖瓦の 1 枚 + 棟の端に鬼瓦(在庫 roof ornaments L)。
    L = 棟止めが Blender x = 0(Unity X = 0)の側 = Dobei2m_End と同じ側 / R = x = L(Unity X = −2.004)の側。"""
    out = []
    for hand in ("L", "R"):
        g, info = module(gable=hand)
        z0 = info["z_ridge"] - BD.SEAT_MUNE
        xe, d = (0.0, -1.0) if hand == "L" else (L, 1.0)
        oo = GR.oni((xe, 0.0, z0), (d, 0.0, 0.0), "onigawara", scale=ONI_H / 0.593)[0]
        V.sel([oo]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        oo["g"] = "onigawara"
        g["onigawara"] = oo
        objs = NB.merge_groups(list(g.values()))
        V.dedup_materials()
        xs = [v.co.x for o in objs for v in o.data.vertices]
        top = max(v.co.z for o in objs for v in o.data.vertices)
        name = "Dobei2_End_" + hand
        cop = max(0.0, -min(xs)) if hand == "L" else max(0.0, max(xs) - L)
        p = finish(objs, name, dict(spec(-L, 0.0, top, "Tools/Blender/build_dobei2.py -- --end"), copingOverhang=cop))
        print("[dobei2]   %s: 棟止めの側 Unity X = %s・鬼の出 %.3f・鬼の天 %.3f" % (name, "0" if hand == "L" else "-2.004", cop, top))
        out.append((objs, p))
        if on_done:
            on_done(objs, p)
    return out


def build_kado(deg, arms=None, neg_zero=False):
    """build_neribei.build_kado と同じ留め(入りの腕 +y・化粧面 +x・原点 = 折れ点)。出隅の側の留めの線に隅棟(roof top x1)。"""
    g, info = module()
    aIn, aOut = (ARM_FULL, ARM_FULL) if arms is None else arms
    sgn = -1.0 if (deg < 0 or neg_zero) else 1.0
    h = math.radians(max(abs(deg), 1e-3)) * 0.5
    n = (sgn * math.sin(h), math.cos(h), 0.0)
    e = info["e"]
    back = e * math.tan(h) + 0.3
    objs = []
    for which, a in (("A", aIn), ("B", aOut)):
        parts = tile(g, -back, a, info)
        R = Matrix.Rotation(math.pi / 2, 4, 'Z')
        for c in parts:
            NB.xform(c, R)
            NB.cut(c, (0, 0, 0), n, True)
        parts = [c for c in parts if len(c.data.polygons)]
        if which == "B":
            for c in parts:
                NB.xform(c, NB.reflect_m(n))
        objs += parts
    NB.clear_src(g)
    if abs(deg) >= 5.0:
        # 隅棟: 留めの水平線 t(出隅の外へ)に沿い、大棟の座の高さから軒の出の端まで勾配で下げる
        t = Vector((sgn * math.cos(h), -math.sin(h), 0.0))
        u1 = (e - 0.04) / math.cos(h)
        zr = info["z_ridge"] - BD.SEAT_MUNE
        p0 = Vector((0, 0, zr)); p1 = t * u1 + Vector((0, 0, zr - (e - 0.04) * BD.RATIO))
        hip = BD.ridge(tuple(p0), tuple(p1), "sumimune", BD.W_MUNE * 0.85, BD.H_MUNE * 0.85)
        for q in hip:
            q.data = q.data.copy()
            V.sel([q]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            q["g"] = "sumimune"
        objs += hip
    if abs(deg) >= 1.0:
        # 軒裏の留めの板(build_neribei.miter_plate): 壁の天端の線(wall_cap と同じ屋根の裏)から瓦の中へ 0.10
        roofmat = bpy.data.materials.get("roof")
        ruv = V.sample_uv(BD.ROOF_MOD, pick_high=True)
        rr = (ruv[0] - 0.01, ruv[1] - 0.01, ruv[0] + 0.01, ruv[1] + 0.01)
        zf = NB.soffit_z([o for o in objs if NB.gname(o) == "kawara"], h, sgn, 0.10)
        objs.append(NB.miter_plate(roofmat, rr, h, sgn, zf, BD.T_WALL / 2.0, e - 0.01))
    objs = NB.merge_groups(objs)
    V.dedup_materials()
    name = "Dobei2_Kado_%02d%s%s" % (int(round(abs(deg))), "M" if (deg < 0 or neg_zero) else "",
                                      "" if arms is None else "_A%dx%d" % (int(round(aIn * 100)), int(round(aOut * 100))))
    return objs, finish(objs, name)


def hook():
    V.hook_textures()
    keep = V.TEX; V.TEX = os.path.join(BD.JC, "Textures"); V.hook_textures(); V.TEX = keep
    for m in bpy.data.materials:
        m.use_backface_culling = True


def render(objs, path):
    NB.TEX = None
    hook()
    stem = os.path.splitext(os.path.basename(path))[0]
    keep = NB.hook_s_heimap
    NB.hook_s_heimap = lambda: None
    NB.SHOTS = SHOTS
    try:
        NB.render_views(objs, stem)
    finally:
        NB.hook_s_heimap = keep


def run_job(argv, do_render):
    if "--kiri" in argv:
        k = int(argv[argv.index("--kiri") + 1]); assert 1 <= k < NE
        objs, p = build_kiri(k)
        if do_render: render(objs, p)
    if "--end" in argv:
        build_end((lambda o, p: render(o, p)) if do_render else None)
    if "--kado" in argv:
        deg, nz = NB.parse_kado(argv[argv.index("--kado") + 1])
        arms = tuple(float(t) for t in argv[argv.index("--arms") + 1].split(",")) if "--arms" in argv else None
        objs, p = build_kado(deg, arms, nz)
        if do_render: render(objs, p)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    if "--all" in argv:
        for j in [["--end"]] + [["--kiri", str(k)] for k in range(1, NE)] + [["--kado", t] for t in NB.OKABE_KADO]:
            run_job(j, do_render and j[0] == "--end")
        return
    run_job(argv, do_render)


if __name__ == "__main__":
    main()
