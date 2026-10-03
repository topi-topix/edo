"""菜園の畝(うね)1本・1間 — 樹下邸の菜園(EDO-0532)。

    blender --background --python Tools/Blender/build_hatake_une.py -- [--render]

・在庫に畝・畑の駒は無い(asset-index で確認済み・呼び出し元)。土の盛りは**キットの
  メッシュを切って作れる形が無い**ので断面を掃引して起こす。⛔ 材は新規に作らない —
  FJG の **`M_FJG_Terrain_Ground_Soil_01`**(地形のスプラット L_dirt と同じ肌)の名だけを名乗る。
  Unity の remap が同名の .mat へ結ぶ(借り先 `Assets/Waldemarst/FreeJapaneseGarden/Materials` は
  `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap` の並びに既に在り、対象に `Models/Niwa` も在る)。
  ⛔ Village Kit の `Paving` は使わない — その土の象限は灰色の砂利で、85 駒並べると
  畝が灰色のコンクリートの丸太に見えた(2026-10-03 普請奉行の検証レンダ)。
  ⛔ Meadow の `M_Ground_Meadow_Wet_Soil_01` / `_Soil_01` も試して退けた — 平均色の R−B が
  16 / 27(FJG は 68)で、並べると同じく灰色の丸太に見える(`--soil wet` で再現できる)。
・UV: 平面のタイル材(タイル 1×1)。**UV 1.0 = 8m** = 地形の L_dirt と同じ縮尺(粒の大きさが揃う)。
  1間の駒は u 0.114×v 0.095 しか使わないので、苔(緑)の少ない**落ち葉と土の茶の矩形**
  (左下 u0.008 / v0.900・緑の画素 0.1%)を選ぶ。u は**芯で折り返す**(両端の小口が同じ u ⇒
  継いだ駒どうしで柄が切れない)。周りは断面の弧長を同じ縮尺で v に取る。
・断面: 底幅 0.60・天端幅 0.35・高さ 0.18 の台形〜かまぼこ。表面に ±0.02 の土塊の起伏。
・**継いで並べる駒**なので両端 0.10m で幅を 0.05 だけ絞り、起伏も端で 0 に落とす
  (どの駒の小口も同じ断面になり、継ぎ目で段がつかない)。
・軸(Unity): 長手 = X / 高さ = Y / 幅 = Z。ピボット = 底面の中心・地盤レベル。
・作物は載せない(Unity 側で在庫の草を散らす)。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

KEN = 1.818
L = KEN                    # 長手 1間
B0, B1, H = 0.60, 0.35, 0.18
PINCH, PINCH_LEN = 0.05, 0.10
BUMP = 0.02
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa"))
SHOT = os.path.join(V.REPO, "Screenshots")
_NM = os.path.join(V.REPO, "Assets", "NatureManufacture Assets",
                   "Meadow Environment Dynamic Nature", "Ground", "T_ground_meadow_soil_wet_01_")
_FJG = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden", "Textures",
                    "Terrain", "Ground_Soil_01", "T_FJG_Ground_Soil_01_")
# 土の候補(材は名だけ。tex はレンダ用)。uv0 = 矩形の左下、m = UV 1.0 の実長
SOILS = {
    "fjg": dict(mat="M_FJG_Terrain_Ground_Soil_01", albedo=_FJG + "Albedo.png", normal=_FJG + "Normal.png",
                uv0=(0.008, 0.900), m=8.0, mirror=True),
    "wet": dict(mat="M_Ground_Meadow_Wet_Soil_01", albedo=_NM + "BC_SM.TGA", normal=_NM + "N.png",
                uv0=(0.0, 0.0), m=L),
}
SOIL = "fjg"

# 半断面(横の距離 y ≥ 0, 高さ z)。底の角 → 肩 → 天端。かまぼこに丸めた台形
HALF = [(B0 / 2, 0.0), (0.27, 0.06), (0.235, 0.12), (B1 / 2, 0.165),
        (0.12, 0.176), (0.06, 0.180), (0.0, 0.181)]


def profile():
    pts = [(-y, z) for (y, z) in HALF] + [(y, z) for (y, z) in reversed(HALF[:-1])]
    return pts   # −y の底 → 頂 → +y の底


def build():
    prof = profile()
    nx = 37
    me = bpy.data.meshes.new("Hatake_Une_1ken")
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    # 断面の弧長(UV の v)
    arc = [0.0]
    for a, b in zip(prof, prof[1:]):
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    rows = []
    for i in range(nx):
        x = -L / 2 + L * i / (nx - 1)
        e = min(x + L / 2, L / 2 - x)              # 端からの距離
        k = max(0.0, 1.0 - e / PINCH_LEN)          # 端で1
        k = k * k * (3 - 2 * k)
        shrink = 1.0 - (PINCH / B0) * k            # 端で幅 −0.05
        hfac = 1.0 - 0.06 * k                      # 端で丸く落とす(高さ −6%。15% では継ぎ目が節に見えた)
        fade = 1.0 - k
        row = []
        for j, (y, z) in enumerate(prof):
            yy, zz = y * shrink, z * hfac
            if 0 < j < len(prof) - 1 and z > 0.0:
                n = noise.noise(Vector((x * 9.0, y * 9.0, 3.7)))
                n += 0.5 * noise.noise(Vector((x * 23.0, y * 23.0, 11.1)))
                zz += BUMP * 0.67 * n * fade * min(1.0, z / 0.05)
            row.append(bm.verts.new((x, yy, max(0.0, zz))))
        rows.append(row)
    bm.verts.ensure_lookup_table()

    sd = SOILS[SOIL]

    def uv(x, s):
        u0, v0 = sd["uv0"]
        if sd.get("mirror"):          # 芯で折り返す: 両端の小口が同じ u ⇒ 継いだ駒で柄が切れない
            return (u0 + abs(x) / sd["m"], v0 + s / sd["m"])
        return (u0 + (x + L / 2) / sd["m"], v0 + s / sd["m"])

    for i in range(nx - 1):
        for j in range(len(prof) - 1):
            a, b = rows[i][j], rows[i + 1][j]
            c, d = rows[i + 1][j + 1], rows[i][j + 1]
            f = bm.faces.new((a, b, c, d))
            for lp in f.loops:
                ii = 0 if lp.vert in (a, d) else 1
                jj = 0 if lp.vert in (a, b) else 1
                lp[uvl].uv = uv(-L / 2 + L * (i + ii) / (nx - 1), arc[j + jj])
    # 小口(両端)と底
    for i, sgn in ((0, -1), (nx - 1, 1)):
        vs = rows[i][:]
        f = bm.faces.new(vs if sgn > 0 else list(reversed(vs)))
        for lp in f.loops:
            co = lp.vert.co
            lp[uvl].uv = uv(co.y + 0.3, co.z + 0.5)   # 小口は折り返さない(n角形の扇で u が化ける)
    bot = [rows[i][0] for i in range(nx)] + [rows[i][-1] for i in reversed(range(nx))]
    f = bm.faces.new(bot)
    for lp in f.loops:
        lp[uvl].uv = uv(lp.vert.co.x, lp.vert.co.y + 0.3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Hatake_Une_1ken", me)
    bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(V.named_material(SOILS[SOIL]["mat"]))
    return o


def check_outward(o):
    """符号付き体積で外向きを確かめる(recalc が裏返す前例あり)"""
    vol = 0.0
    me = o.data
    for p in me.polygons:
        vs = [me.vertices[k].co for k in p.vertices]
        for t in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[t].cross(vs[t + 1])) / 6.0
    return vol


def hook_soil(m, albedo, normal=None, roughness=0.9):
    """キット外(TEX に無い)のタイル材をレンダ用にだけ結線する。FBX には名前しか載らない。"""
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(albedo, check_existing=True)
    nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = roughness
    if normal and os.path.exists(normal):
        ni = nt.nodes.new('ShaderNodeTexImage')
        ni.image = bpy.data.images.load(normal, check_existing=True)
        ni.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])


def ground_plane():
    """比べ用の地面: シーンの地形 L_dirt と同じ FJG Soil_01 を 8m 周期で(レンダ専用・書き出さない)"""
    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 0, -0.002))
    g = bpy.context.active_object
    for d in g.data.uv_layers.active.data:
        d.uv = (d.uv[0] * 12.0 / 8.0, d.uv[1] * 12.0 / 8.0)
    m = bpy.data.materials.new("_ground_L_dirt")
    fjg = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden", "Textures",
                       "Terrain", "Ground_Soil_01", "T_FJG_Ground_Soil_01_")
    hook_soil(m, fjg + "Albedo.png", fjg + "Normal.png", 0.95)
    g.data.materials.append(m)
    return g


def shots(o):
    V.hook_textures()
    hook_soil(o.data.materials[0], SOILS[SOIL]["albedo"], SOILS[SOIL]["normal"])
    os.makedirs(SHOT, exist_ok=True)
    # 3本並べて継ぎ目を見る
    copies = []
    for dx in (-L, L):
        c = o.copy(); c.location.x = dx
        bpy.context.scene.collection.objects.link(c); copies.append(c)
    V.studio((-2.6, -3.2, 1.5), (0, 0, 0.05), res=(1600, 900))
    V.render(os.path.join(SHOT, "une_3d.png"))
    # 地形の土(L_dirt と同じ肌・8m 周期)の上に 3 条並べて、周りと並べた見え方を確かめる
    rows = []
    for dy in (-0.9, 0.9):
        for c in [o] + copies:
            r = c.copy(); r.location.y = dy
            bpy.context.scene.collection.objects.link(r); rows.append(r)
    g = ground_plane()
    V.studio((-3.2, -4.2, 1.7), (0.4, 0, 0.0), res=(1600, 900))
    V.render(os.path.join(SHOT, "une_field.png"))
    V.studio((-6.5, -7.5, 2.4), (0.6, 0.8, 0.0), res=(1600, 900))   # 普請奉行の近景(katte_3)ほどの引き
    V.render(os.path.join(SHOT, "une_field_far.png"))
    for r in rows + [g]:
        bpy.data.objects.remove(r, do_unlink=True)
    V.studio((0, -4.0, 0.09), (0, 0, 0.09), ortho_scale=1.0, res=(1400, 600))
    V.render(os.path.join(SHOT, "une_side.png"))
    V.studio((-4.0, 0, 0.09), (0, 0, 0.09), ortho_scale=0.9, res=(1200, 600))
    V.render(os.path.join(SHOT, "une_koguchi.png"))
    V.studio((0, -1.2, 0.9), (0, 0, 0.08), res=(1600, 900))
    V.render(os.path.join(SHOT, "une_close.png"))
    for c in copies:
        bpy.data.objects.remove(c, do_unlink=True)


def main():
    global SOIL
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--soil" in argv:            # 見比べ用。既定は SOIL
        SOIL = argv[argv.index("--soil") + 1]
    V.reset()
    o = build()
    mn, mx = V.bbox([o])
    print("[une] Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  底=%.3f  面=%d  体積=%.4f"
          % (mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons), check_outward(o)))
    print("[une] 材質=%s" % [m.name for m in o.data.materials])
    path = os.path.join(OUT, "Hatake_Une_1ken.fbx")
    V.export_fbx([o], path)
    print("[une] 書き出し " + path)
    if "--render" in argv:
        shots(o)


if __name__ == "__main__":
    main()
