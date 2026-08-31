"""**木を在庫の作りに合わせて起こす。**

    blender --background --python Tools/Blender/build_tree.py -- jokuroku Mid --render
    blender --background --python Tools/Blender/build_tree.py -- ume Small Mid Big

【なぜ要るか】⛔ **自作の低ポリゴンの木は使用禁止**(2026-08-30 ユーザー指示
「これは2度と使わないでください。見た目がしょぼすぎます」)。
在庫(Waldemarst FreeJapaneseGarden)には**黒松・桜・竹しか無く**、松江松平邸の指図が要求する
**常緑広葉樹 51本**(モッコク・モチノキ・カシ・シイ)と**ウメ 22本**が埋まらない。
ユーザー裁定 2026-08-31 は **案C = 在庫を参考に新造**。

【在庫の作り(実測 2026-08-30。これに合わせる)】
  ・LOD **4段** — screenRelativeTransitionHeight 0.80 / 0.60 / 0.40 / 0.04
  ・三角数 LOD0 **5,960〜6,575** / LOD1 3,672〜4,228 / LOD2 1,678〜2,600 / LOD3 ビルボード16
  ・構成 = **樹皮の実ジオメトリ**(幹と枝)+ **葉のカード**。サブメッシュ 2〜3
  ・シェーダ `URP/Nature/SpeedTree8_PBRLit`

【材質】⛔ **新規に作らない。**在庫の材質名をそのまま名乗らせ、Unity 側で remap して
提供元の .mat へ結ぶ(長屋・隅部材と同じ作法)。
  樹皮 = `M_FJG_Tree_Sakura_Bark_A` / 葉 = `M_FJG_Tree_Sakura_Sprout_Summer`
⚠ 葉のテクスチャは在庫の物なので、**枝ぶりと葉の付き方**で樹種を描き分ける
(常緑広葉樹=密で丸い樹冠・立ち枝 / 梅=疎で屈曲した枝・横張り)。

【出力の向き(Unity 座標)】幅=X / 高さ=Y / 厚み=Z。ピボット = **幹の芯・地面**。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

OUT  = os.path.join(V.REPO, "Assets/Edo/Models/Trees")
SHOT = os.path.join(V.REPO, "Screenshots")
MAT_BARK  = "M_FJG_Tree_Sakura_Bark_A"
MAT_LEAF  = "M_FJG_Tree_Sakura_Sprout_Summer"
# 提供元(検証レンダ用に読むだけ。FBX には材質**名**しか入れない)
FJG = os.path.join(V.REPO, "Assets/Waldemarst/FreeJapaneseGarden/Textures/Trees")
TEX_LEAF = os.path.join(FJG, "Sakura_Summer_001/T_FJG_Sakura_Summer_001_Atlas_Albedo.png")
TEX_BARK = os.path.join(FJG, "T_FJG_Tree_Sakura_Bark_A_Albedo.png")

# ⭐ 葉のアトラスの房の位置(2026-08-31 実測。32x32 グリッドで α>0.5 の連結成分)。
#   ⛔ **UV を張らないと葉が出ない** — アトラスなので、カードを房の矩形へ写す。
SPROUT_UV = [
    (0.2500, 0.5000, 0.4688, 0.8125), (0.7188, 0.0000, 1.0000, 0.2500),
    (0.0000, 0.2812, 0.2188, 0.5000), (0.7188, 0.5000, 1.0000, 0.6875),
    (0.5000, 0.4688, 0.6875, 0.6875), (0.5000, 0.2500, 0.6875, 0.4688),
    (0.0000, 0.0000, 0.2188, 0.2188), (0.5000, 0.7188, 0.6562, 0.9062),
    (0.5000, 0.0000, 0.6875, 0.1875), (0.2812, 0.2812, 0.4688, 0.4375),
]

# 樹種のプロファイル。⚠ 寸法は在庫の同格に合わせる(桜 Mid = 5.8×5.7m / Big = 8.6×7.3m)
SPECIES = {
    # 常緑広葉樹(モッコク・モチノキ・カシ・シイ)— 密で丸い樹冠、立ち枝、葉が枝先に集まる
    "jokuroku": dict(label="常緑広葉樹", trunk_h=0.46, lean=0.04, spread=0.34,
                     ang=(22, 40), levels=4, kids=(3, 4), taper=0.66,
                     leaf_scale=0.115, leaf_per_tip=9, crown=1.30,
                     wh=0.80, top=0.55),
    # ウメ — 疎で屈曲した枝、横張り、樹高が低い
    "ume":       dict(label="ウメ",       trunk_h=0.30, lean=0.14, spread=0.44,
                     ang=(34, 62), levels=4, kids=(2, 3), taper=0.60,
                     leaf_scale=0.095, leaf_per_tip=5, crown=0.95,
                     wh=0.95, top=0.72),
}
SIZE = {"Small": 3.6, "Mid": 5.8, "Big": 8.2}          # 樹高[m](在庫の同格に合わせる)
LOD  = [dict(seg=8, tip=1.00, leaf=1.00),               # LOD0
        dict(seg=6, tip=0.62, leaf=0.72),               # LOD1
        dict(seg=5, tip=0.34, leaf=0.46)]               # LOD2


def branch_skeleton(sp, h, rnd):
    """枝の骨格を作る。返すのは [(始点, 終点, 半径始, 半径終, 深さ)]。
    ⛔ 円錐を積まない — **実際に分岐させる**(在庫の木はそうなっている)。"""
    segs = []
    r0 = h * 0.030                                       # 幹の根元の半径
    trunk_top = Vector((rnd.uniform(-1, 1) * h * sp["lean"], rnd.uniform(-1, 1) * h * sp["lean"],
                        h * sp["trunk_h"]))
    segs.append((Vector((0, 0, 0)), trunk_top, r0, r0 * sp["taper"], 0))
    frontier = [(trunk_top, (trunk_top - Vector((0, 0, 0))).normalized(), r0 * sp["taper"], 0)]
    for lv in range(1, sp["levels"] + 1):
        nxt = []
        for base, dirv, rad, _ in frontier:
            k = rnd.randint(*sp["kids"])
            for i in range(k):
                a = math.radians(rnd.uniform(*sp["ang"]))
                az = (i / k) * math.tau + rnd.uniform(-0.5, 0.5)
                # 親の向きから a だけ開き、方位 az へ振る
                side = Vector((math.cos(az), math.sin(az), 0))
                if side.length < 1e-6: side = Vector((1, 0, 0))
                d = (dirv * math.cos(a) + side.normalized() * math.sin(a)).normalized()
                # 上位ほど短く。樹冠の丸みは crown で調整
                ln = h * (0.30 * sp["spread"]) * (sp["taper"] ** lv) * rnd.uniform(0.8, 1.25)
                tip = base + d * ln
                # 外側ほど上を向かせる(枝の立ち上がり)
                tip.z += ln * 0.22 * sp["crown"]
                # ⛔ **樹冠の輪郭に押し込める。** これが無いと枝先が同じ高さに並び、
                #    横に広い「板」の樹冠になる(2026-08-31 の最初の試作がそうだった)。
                #    楕円体: 高さ h、幅 h*wh、頂部は top の高さで細る
                cz = h * 0.62                      # 樹冠の中心の高さ
                rz = h * 0.46                      # 樹冠の縦半径
                rx = h * sp["wh"] * 0.5            # 樹冠の横半径
                dz = (tip.z - cz) / rz
                if dz > 1.0: tip.z = cz + rz; dz = 1.0
                lim = rx * math.sqrt(max(0.04, 1.0 - dz * dz))
                if dz > 0: lim *= (1.0 - (1.0 - sp["top"]) * dz)   # 上ほど細る
                r_xy = math.hypot(tip.x, tip.y)
                if r_xy > lim and r_xy > 1e-6:
                    tip.x *= lim / r_xy; tip.y *= lim / r_xy
                r1 = rad * sp["taper"]
                segs.append((base.copy(), tip, rad, r1, lv))
                nxt.append((tip, d, r1, lv))
        frontier = nxt
    return segs, frontier


def add_branches(bm, segs, nseg):
    """枝を多角柱で起こす(先細り)。"""
    for a, b, r0, r1, lv in segs:
        d = (b - a); ln = d.length
        if ln < 1e-4: continue
        q = d.normalized().rotation_difference(Vector((0, 0, 1))).inverted()
        ring0, ring1 = [], []
        for i in range(nseg):
            t = i / nseg * math.tau
            p = Vector((math.cos(t), math.sin(t), 0))
            ring0.append(bm.verts.new(a + q @ (p * r0)))
            ring1.append(bm.verts.new(b + q @ (p * r1)))
        for i in range(nseg):
            j = (i + 1) % nseg
            bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))


def add_leaves(bm, tips, sp, h, rnd, per_tip, scale):
    """葉のカード(十字に組んだ板)。⛔ 一枚板にしない — 横から見て消える。"""
    s0 = h * sp["leaf_scale"] * scale
    for base, dirv, rad, lv in tips:
        for _ in range(per_tip):
            s = s0 * rnd.uniform(0.72, 1.28)          # 大きさを散らす(均一だと板に見える)
            c = base + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1),
                               rnd.uniform(-0.7, 1.1))) * s0 * 2.2
            yaw = rnd.uniform(0, math.tau); pit = rnd.uniform(-0.5, 0.5)
            R = Euler((pit, 0, yaw)).to_matrix()
            u0, v0, u1, v1 = SPROUT_UV[rnd.randrange(len(SPROUT_UV))]
            ar = (v1 - v0) / max(1e-6, (u1 - u0))         # 房の縦横比を保つ
            for k in range(2):                            # 十字の2枚
                Rk = Euler((pit, 0, yaw + k * math.pi / 2)).to_matrix()
                pts = [c + Rk @ Vector((x * s, 0, y * s * ar)) for x, y in
                       ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                vs = [bm.verts.new(v) for v in pts]
                f = bm.faces.new(vs)
                uvl = bm.loops.layers.uv.verify()
                for lp, (uu, vv) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                    lp[uvl].uv = (uu, vv)


def build_one(key, size, lod, rnd):
    sp = SPECIES[key]; h = SIZE[size]; L = LOD[lod]
    segs, tips = branch_skeleton(sp, h, rnd)
    # --- 樹皮
    me_b = bpy.data.meshes.new("bark")
    bm = bmesh.new(); add_branches(bm, segs, L["seg"]); bm.to_mesh(me_b); bm.free()
    ob_b = bpy.data.objects.new("bark", me_b); bpy.context.collection.objects.link(ob_b)
    # --- 葉(枝先を間引く)
    keep = [t for t in tips if rnd.random() < L["tip"]]
    me_l = bpy.data.meshes.new("leaf")
    bm = bmesh.new()
    add_leaves(bm, keep, sp, h, rnd, max(1, int(round(sp["leaf_per_tip"] * L["leaf"]))), 1.0)
    bm.to_mesh(me_l); bm.free()
    ob_l = bpy.data.objects.new("leaf", me_l); bpy.context.collection.objects.link(ob_l)
    # --- 材質(名前だけ。中身は Unity で remap して在庫の .mat へ結ぶ)
    for ob, nm in ((ob_b, MAT_BARK), (ob_l, MAT_LEAF)):
        m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        ob.data.materials.append(m)
    o = V.join([ob_b, ob_l], "LOD_%d" % lod)
    # --- 向き: Blender Z-up → Unity Y-up は FBX 書き出しが行う。ピボットは幹の芯・地面
    return o


def hook():
    """検証レンダのためだけに提供元のテクスチャを読む。
    ⛔ FBX には材質**名**しか入らない — Unity 側の remap が本番。"""
    for nm, tex, alpha in ((MAT_BARK, TEX_BARK, False), (MAT_LEAF, TEX_LEAF, True)):
        m = bpy.data.materials.get(nm)
        if m is None or not os.path.exists(tex): continue
        m.use_nodes = True; nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None: continue
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(tex, check_existing=True)
        img.location = (-600, 300)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.75
        if alpha:
            nt.links.new(img.outputs['Alpha'], b.inputs['Alpha'])
            m.blend_method = 'CLIP'; m.alpha_threshold = 0.4
            try: m.show_transparent_back = False
            except Exception: pass


def tri(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    args = [a for a in argv if not a.startswith("--")]
    key = args[0] if args else "jokuroku"
    sizes = args[1:] or ["Mid"]
    os.makedirs(OUT, exist_ok=True)
    for size in sizes:
        V.reset()
        rnd = random.Random(hash((key, size)) & 0xffffffff)
        lods = []
        for i in range(3):
            rnd2 = random.Random(hash((key, size)) & 0xffffffff)   # 同じ骨格から間引く
            lods.append(build_one(key, size, i, rnd2))
        for i, o in enumerate(lods):
            print("[tree] %s %s LOD%d  tri=%d" % (key, size, i, tri(o)))
        mn, mx = V.bbox(lods)
        print("[tree] %s %s 出来上がり(m) W %.2f × H %.2f × D %.2f"
              % (SPECIES[key]["label"], size, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y))
        name = "Tree_%s_%s" % (key.capitalize(), size)
        for i, o in enumerate(lods): o.name = "LOD_%d" % i
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx(lods, path)
        print("[tree] wrote %s" % path)
        if do_render:
            hook()
            V.studio((mn.x - (mx.x-mn.x)*1.6, mn.y - (mx.y-mn.y)*2.2, (mx.z-mn.z)*0.55),
                     ((mn.x+mx.x)/2, (mn.y+mx.y)/2, (mx.z-mn.z)*0.45), res=(1100, 1400))
            V.render(os.path.join(SHOT, "tree_%s_%s.png" % (key, size)))


main()
