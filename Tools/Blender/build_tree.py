"""**木を在庫の作りに合わせて起こす。**

    blender --background --python Tools/Blender/build_tree.py -- jouryoku Mid --render
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
    "jouryoku": dict(label="常緑広葉樹",
                     trunk_h=0.44, trunk_r=0.040, tip_r=0.006, lean=0.030,
                     crown_z=0.70, crown_rz=0.29, wh=0.68, top=0.55,
                     attractors=420, influence=0.32, kill=0.075, step=0.055,
                     iters=42, up=0.16, jitter=0.20,
                     leaf_scale=0.105, leaf_per_tip=7),
    # ウメ — 疎で屈曲した枝、横張り、樹高が低い
    "ume":      dict(label="ウメ",
                     trunk_h=0.36, trunk_r=0.034, tip_r=0.005, lean=0.10,
                     crown_z=0.66, crown_rz=0.30, wh=0.86, top=0.74,
                     attractors=190, influence=0.40, kill=0.105, step=0.070,
                     iters=34, up=0.10, jitter=0.34,
                     leaf_scale=0.088, leaf_per_tip=4),
}
SIZE = {"Small": 3.6, "Mid": 5.8, "Big": 8.2}          # 樹高[m](在庫の同格に合わせる)
LOD  = [dict(seg=8, tip=1.00, leaf=1.00),               # LOD0
        dict(seg=6, tip=0.62, leaf=0.72),               # LOD1
        dict(seg=5, tip=0.34, leaf=0.46)]               # LOD2


def crown_points(sp, h, rnd, n):
    """樹冠の体積に誘引点を撒く。**楕円体の内側を埋める**(殻に貼らない)。
    ⛔ 枝先を輪郭へ押し込むやり方はやめた — 枝先が殻の上に並んで
      樹冠が箱に見えた(2026-08-31 の試作。ユーザー指摘『樹冠が四角い』)。"""
    cz = h * sp["crown_z"]
    rz = h * sp["crown_rz"]
    rx = h * sp["wh"] * 0.5
    pts = []
    guard = 0
    while len(pts) < n and guard < n * 60:
        guard += 1
        # 体積一様に撒く(r**(1/3))。外周をやや厚くして葉を外に寄せる
        u = rnd.random() ** (1.0 / 3.0)
        u = u * 0.55 + u ** 0.45 * 0.45
        th = rnd.uniform(0, math.tau)
        ph = math.acos(rnd.uniform(-1, 1))
        x = u * rx * math.sin(ph) * math.cos(th)
        y = u * rx * math.sin(ph) * math.sin(th)
        z = cz + u * rz * math.cos(ph)
        # 上ほど細らせる(円錐にならない程度に)
        dz = (z - cz) / rz
        if dz > 0:
            lim = rx * math.sqrt(max(0.0, 1.0 - dz * dz)) * (1.0 - (1.0 - sp["top"]) * dz)
            if math.hypot(x, y) > lim:
                continue
        if z < h * sp["trunk_h"] * 0.8:
            continue                                  # 幹の下には葉を付けない
        pts.append(Vector((x, y, z)))
    return pts


def branch_skeleton(sp, h, rnd):
    """**空間占有法(space colonisation)**で骨格を作る。
    樹冠に誘引点を撒き、いちばん近い節が引かれて伸びる。届いた点は消す。
    ⭕ 樹冠の形は「押し込み」ではなく**枝が伸びた結果**として出るので、
      輪郭が箱にならず、内部にも枝が通る。
    返すのは ([(始点, 終点, 半径始, 半径終, 深さ)], 枝先)。"""
    # --- 幹。根元を太らせ、上へ細り、少し揺らぐ
    r0 = h * sp["trunk_r"]
    nodes = [Vector((0, 0, 0))]
    parent = [-1]
    n_tr = 6
    z_lead = h * sp["trunk_h"]
    for i in range(1, n_tr + 1):
        t = i / n_tr
        sway = h * sp["lean"] * math.sin(t * 2.4 + rnd.uniform(0, 1)) * t
        nodes.append(Vector((sway * rnd.uniform(0.5, 1.5), sway * rnd.uniform(-1, 1), z_lead * t)))
        parent.append(len(nodes) - 2)

    attr = crown_points(sp, h, rnd, sp["attractors"])
    D_i = h * sp["influence"]          # 引きが届く距離
    D_k = h * sp["kill"]               # 届いたとみなす距離
    step = h * sp["step"]

    for _ in range(sp["iters"]):
        if not attr:
            break
        pull = {}
        for a in attr:
            best, bd = -1, 1e9
            for ni in range(len(nodes)):
                d = (a - nodes[ni]).length
                if d < bd: bd, best = d, ni
            if bd > D_i:
                continue
            pull.setdefault(best, Vector((0, 0, 0)))
            pull[best] += (a - nodes[best]).normalized()
        if not pull:
            break
        for ni, v in pull.items():
            if v.length < 1e-6:
                continue
            d = v.normalized()
            d.z += sp["up"]                       # 枝の立ち上がり
            d = (d + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * sp["jitter"]).normalized()
            nodes.append(nodes[ni] + d * step)
            parent.append(ni)
        attr = [a for a in attr
                if min((a - n).length for n in nodes) > D_k]

    # --- 太さ: ダ・ヴィンチ則(親の断面積 = 子の断面積の和)を末端から積み上げる
    kids = [[] for _ in nodes]
    for ni in range(1, len(nodes)):
        kids[parent[ni]].append(ni)
    rad = [0.0] * len(nodes)
    tip_r = h * sp["tip_r"]
    for ni in range(len(nodes) - 1, -1, -1):
        if not kids[ni]:
            rad[ni] = tip_r
        else:
            rad[ni] = (sum(rad[k] ** 2.2 for k in kids[ni])) ** (1 / 2.2)
    scale = r0 / max(1e-6, rad[0])
    rad = [r * scale for r in rad]

    segs = []
    depth = [0] * len(nodes)
    for ni in range(1, len(nodes)):
        pi = parent[ni]
        depth[ni] = depth[pi] + 1
        segs.append((nodes[pi].copy(), nodes[ni].copy(), rad[pi], rad[ni], depth[ni]))
    tips = [(nodes[ni], (nodes[ni] - nodes[parent[ni]]).normalized(), rad[ni], depth[ni])
            for ni in range(1, len(nodes)) if not kids[ni]]
    return segs, tips


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
    # --- 樹高を目標へ正規化。⚠ 空間占有法は誘引点の散らばりで背が伸び縮みするので、
    #     指図が樹高で層を決めている以上、**出来上がりを測って合わせる**(呼び寸法で信じない)。
    zs = [v.co.z for v in o.data.vertices]
    if zs:
        got = max(zs) - min(zs)
        if got > 1e-4:
            k = h / got
            for v in o.data.vertices:
                v.co = Vector((v.co.x * k, v.co.y * k, (v.co.z - min(zs)) * k))
            o.data.update()
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
    key = args[0] if args else "jouryoku"
    # `--var <n>` で1寸法あたり n 本の**別個体**を焼く(既定 3)。
    # ⚠ 2026-09-01 庭方の指摘:「Own.Jokuroku は Mid/Small の 2 プレハブで
    #   モッコク・モチノキ・カシ・シイの 4 樹種 43 本を代表しており、近景で
    #   同じ木の繰り返しになる」。⭕ 骨格の乱数を個体ごとに変えて姿を散らす。
    #   ⛔ 種は個体番号から決める(時刻や連番で振らない — 焼き直すたびに姿が変わると
    #      検証レンダが比較できない)。1本目は従来と同じ名前のまま(既存の参照を壊さない)。
    nvar = int(args[args.index("--var") + 1]) if "--var" in args else 3
    args = [a for a in args if a != "--var" and not a.isdigit()] if "--var" in args else args
    sizes = args[1:] or ["Mid"]
    os.makedirs(OUT, exist_ok=True)
    for size in sizes:
      for vi in range(nvar):
        V.reset()
        seed = hash((key, size, vi)) & 0xffffffff
        lods = []
        for i in range(3):
            rnd2 = random.Random(seed)                             # 同じ骨格から間引く
            lods.append(build_one(key, size, i, rnd2))
        mn, mx = V.bbox(lods)
        suffix = "" if vi == 0 else "_%02d" % (vi + 1)
        name = "Tree_%s_%s%s" % (key.capitalize(), size, suffix)
        print("[tree] %s %s%s  LOD tri=%d/%d/%d  W %.2f × H %.2f × D %.2f"
              % (SPECIES[key]["label"], size, suffix,
                 tri(lods[0]), tri(lods[1]), tri(lods[2]),
                 mx.x - mn.x, mx.z - mn.z, mx.y - mn.y))
        for i, o in enumerate(lods): o.name = "LOD_%d" % i
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx(lods, path)
        print("[tree] wrote %s" % path)
        if do_render:
            hook()
            V.studio((mn.x - (mx.x-mn.x)*1.6, mn.y - (mx.y-mn.y)*2.2, (mx.z-mn.z)*0.55),
                     ((mn.x+mx.x)/2, (mn.y+mx.y)/2, (mx.z-mn.z)*0.45), res=(1100, 1400))
            V.render(os.path.join(SHOT, "tree_%s_%s%s.png" % (key, size, suffix)))


main()
