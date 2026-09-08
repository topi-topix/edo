"""**木の検証レンダ** — 近景で「孤立した葉の房」と「樹冠の透け」を自分の目で確かめる。

    blender --background --python Tools/Blender/check_tree.py -- near Tree_Teiboku_H20
    blender --background --python Tools/Blender/check_tree.py -- cmp

【なぜ要るか】`build_tree.py --render` の studio カメラは**引きの全景**で、丈2mの低木は
画面の 1/4 にしかならない。**枝から離れて浮いた葉の房**も**樹冠の透け**もその大きさでは読めず、
2026-09-07 に「直した」と報告した欠陥が**近景レンダで残っていた**(普請奉行の指摘)。
⇒ ①寄る ②空を大きく入れる(孤立片は背景の無地の上でしか見えない) ③在庫の同格と並べる。

⚠ 数値の関門は `build_tree.py` 側にある(葉のカードの中心から最寄りの枝の芯までの距離)。
   ⛔ **数値だけで終えない** — 密度・輪郭・株立ちの姿は目でしか判定できない。
"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

REPO = V.REPO
# ⭐ `BUZAI_OUT` が立っていれば staging の FBX を読む(Assets を汚さずに姿を検める)
TR   = V.out_dir(os.path.join(REPO, "Assets/Edo/Models/Trees"))
SHOT = os.path.join(REPO, "Screenshots")
FJG  = os.path.join(REPO, "Assets/Waldemarst/FreeJapaneseGarden/Textures/Trees")
TEX_LEAF = os.path.join(FJG, "Sakura_Summer_001/T_FJG_Sakura_Summer_001_Atlas_Albedo.png")
TEX_BARK = os.path.join(FJG, "T_FJG_Tree_Sakura_Bark_A_Albedo.png")
# ⭐ 2026-09-07 — 松は在庫のクロマツの樹皮・針葉を名乗る
TEX_PINE_LEAF = os.path.join(FJG, "BlackPine_Green_001/T_FJG_BlackPine_Green_001_Atlas_Albedo.png")
TEX_PINE_BARK = os.path.join(FJG, "T_FJG_Tree_BlackPine_Bark_Albedo.png")
# 材質名 → (アルベド, αを使うか)
TEXMAP = {
    "M_FJG_Tree_Sakura_Bark_A":            (TEX_BARK, False),
    "M_FJG_Tree_Sakura_Sprout_Summer":     (TEX_LEAF, True),
    "M_FJG_Tree_BlackPine_Bark":           (TEX_PINE_BARK, False),
    "M_FJG_Tree_BlackPine_Sprout_A_Green": (TEX_PINE_LEAF, True),
    "M_FJG_Tree_BlackPine_Sprout_B_Green": (TEX_PINE_LEAF, True),
}


import stock_mesh

# ⭐ **並べる相手**。⛔ 「在庫と並べた」と言うなら在庫の実メッシュを入れること
#   (在庫の木は .fbx を持たないので `stock_mesh` が .prefab の YAML から起こす)。
BP = ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/"
      "Tree_BlackPine_Big_Green_01.prefab")
CMP = {
    # ⭐ 2026-09-08 — **丈の刻みの梯子**。中間の2段(H16/H24)を足したので、
    #   並べる目的が「個体差を見る」から「**4段が等間隔に上がって見えるか**」へ変わった。
    #   ⛔ 12個体を1枚に入れない — 2400px に 42m 分が入って 1.2m の株が 68px になり、
    #     刈込に見えるか卵形かの判定ができない。⇒ 梯子は1個体ずつ・個体差は `var` で見る。
    "teiboku": [
        dict(name="Tree_Teiboku_H12",   col=(0.9, 0.3, 0.3, 1)),
        dict(name="Tree_Teiboku_H16",   col=(0.95, 0.55, 0.15, 1)),
        dict(name="Tree_Teiboku_H20",   col=(0.3, 0.5, 0.9, 1)),
        dict(name="Tree_Teiboku_H24",   col=(0.25, 0.7, 0.35, 1)),
        dict(name="Tree_Jouryoku_Small"),          # 上位の刻みへの繋ぎ(常緑広葉樹 3.6m)
    ],
    # 個体差(同じ刻みの3本が同じ姿に見えないか)
    "teiboku_var": [
        dict(name="Tree_Teiboku_H16"), dict(name="Tree_Teiboku_H16_02"),
        dict(name="Tree_Teiboku_H16_03"),
        dict(name="Tree_Teiboku_H24"), dict(name="Tree_Teiboku_H24_02"),
        dict(name="Tree_Teiboku_H24_03"),
    ],
    # ⚠ 3本目は **いま実装が使っている姿**(在庫を scaleY 1.94 / scaleXZ 1.15 で
    #   縦に伸ばしたもの)。⭐ これと新造を同じ絵に入れないと「何が直ったか」が見えない。
    "matsu": [
        dict(stock=BP, col=(0.9, 0.3, 0.3, 1)),
        dict(stock=BP, sy=1.94, sxz=1.15, col=(0.95, 0.55, 0.15, 1)),
        dict(name="Tree_Matsu_Mid", col=(0.3, 0.5, 0.9, 1)),
        dict(name="Tree_Matsu_Mid_02", col=(0.3, 0.5, 0.9, 1)),
        dict(name="Tree_Matsu_Mid_03", col=(0.3, 0.5, 0.9, 1)),
        dict(name="Tree_Matsu_Big", col=(0.25, 0.7, 0.35, 1)),
        dict(name="Tree_Matsu_Big_02", col=(0.25, 0.7, 0.35, 1)),
        dict(name="Tree_Matsu_Big_03", col=(0.25, 0.7, 0.35, 1)),
    ],
}


def load(name, lod=0):
    """FBX から **その LOD のメッシュだけ**を残す。
    ⛔ そのまま読むと LOD_0/1/2 が重なって焼かれ、密度の判定が嘘になる。"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(TR, name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    keep = [o for o in new
            if o.type == 'MESH' and o.name.split('.')[0] == ("LOD_%d" % lod)]
    for o in new:
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in keep:
        o.select_set(True)
    if keep:
        bpy.context.view_layer.objects.active = keep[0]
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return keep


def hook():
    """検証レンダのためだけに提供元のテクスチャを読む(FBX には材質**名**しか入らない)。
    ⚠ 同じ FBX を何度も読むと材質名に `.001` が付くので、**接頭辞で照合**する。"""
    for m in bpy.data.materials:
        base = m.name.split('.')[0]
        if base not in TEXMAP:
            continue
        tex, alpha = TEXMAP[base]
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None or not os.path.exists(tex):
            continue
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(tex, check_existing=True)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.75
        if alpha:
            nt.links.new(img.outputs['Alpha'], b.inputs['Alpha'])
            m.blend_method = 'CLIP'
            m.alpha_threshold = 0.4
            try:
                m.show_transparent_back = False
            except Exception:
                pass


def ground():
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    g = bpy.context.object
    m = bpy.data.materials.new("gnd")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.30, 0.31, 0.29, 1)
    g.data.materials.append(m)
    return g


def post(x, y, h, col):
    """丈の物差し。⛔ 数字で言うだけにしない — 並びの中で背丈を目で確かめる。"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2))
    o = bpy.context.object
    o.scale = (0.10, 0.10, h)
    m = bpy.data.materials.new("post")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = col
    o.data.materials.append(m)


def shift(objs, dx):
    for o in objs:
        o.location.x += dx


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mode = argv[0] if argv else "near"
    V.reset()
    ground()
    if mode == "near":
        name = argv[1] if len(argv) > 1 else "Tree_Teiboku_H20"
        load(name)
        hook()
        mn, mx = V.bbox([o for o in bpy.data.objects if o.type == 'MESH'
                         and o.name.startswith("LOD_")])
        h = mx.z - mn.z
        hook()
        V.studio((h * 1.45, -h * 1.70, h * 0.68), (0, 0, h * 0.50), res=(1500, 1500))
        bpy.context.scene.camera.data.lens = 62
        V.render(os.path.join(SHOT, "tree_%s_near.png" % name.replace("Tree_", "").lower()))
    elif mode == "cmp":
        # ⭐ **在庫と並べる。**引数で樹種を切り替える(既定は照葉低木)。
        key = argv[1] if len(argv) > 1 else "teiboku"
        items = CMP.get(key)
        if items is None:
            raise KeyError("cmp の並び %r が無い(%s)" % (key, list(CMP)))
        x, marks, gap = 0.0, [], 1.6
        for it in items:
            if it.get("stock"):
                objs = stock_mesh.load_prefab_lod(it["stock"], lod=it.get("lod", 0))
            else:
                objs = load(it["name"])
            mn, mx = V.bbox(objs)
            # 在庫の木は根が地面下まで伸びている ⇒ 底を 0 へ上げる
            for o in objs:
                o.location.z -= mn.z
            sy, sxz = it.get("sy", 1.0), it.get("sxz", 1.0)
            if sy != 1.0 or sxz != 1.0:
                for o in objs:
                    o.scale = (sxz, sxz, sy)
                bpy.ops.object.select_all(action='DESELECT')
                for o in objs:
                    o.select_set(True)
                bpy.context.view_layer.objects.active = objs[0]
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                mn, mx = V.bbox(objs)
                for o in objs:
                    o.location.z -= mn.z
            mn, mx = V.bbox(objs)
            w = mx.x - mn.x
            cx = x + w / 2 - (mn.x + mx.x) / 2
            shift(objs, cx)
            marks.append((x + w / 2, mx.z - mn.z, it.get("col", (0.9, 0.3, 0.3, 1))))
            x += w + gap
        for mx_, h, col in marks:
            post(mx_ - 0.0, 2.6, h, col)              # 丈の物差し(手前に立てる)
        hook()
        # ⚠ **画角は必ず端まで入るか確かめる。**焦点距離 40mm / センサ 36mm なら
        #   見える幅 = 距離 × 0.90。⇒ 距離は `span / 0.90` に余白を足して取る。
        #   ⛔ 1巡目は距離を span×0.95 にして**左端の在庫が枠外へ落ちた**(2026-09-07)。
        span = x
        cam = span / 0.90 * 1.12
        V.studio((span / 2, -cam, span * 0.20), (span / 2, 0.0, span * 0.13),
                 res=(2400, 1000))
        bpy.context.scene.camera.data.lens = 40
        V.render(os.path.join(SHOT, "tree_%s_cmp.png" % key))
    else:
        raise KeyError("mode は near / cmp")


main()
