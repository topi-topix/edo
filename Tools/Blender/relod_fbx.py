"""**焼いた FBX の LOD の子の名だけを `<名>_LOD<n>` に付け替える**(形は一切触らない)。

    blender --background --python Tools/Blender/relod_fbx.py -- Assets/Edo/Models/Trees/Tree_Ume_Mid.fbx ...

【なぜ要るか】2026-09-23 EDO-0401。`build_tree.py` は長く子を `LOD_0/1/2` と名づけて出していた。
Unity の自動 LODGroup の綴りは `<名>_LOD0` なので、根が空の Transform になり、
地形の木として `TreePrototype.Validate` に落とされ(山王の社叢 1,030 本が一本も描かれなかった)、
GameObject で置けば 3 枚重ねで描かれていた。

【なぜ焼き直さないか】⛔ `build_tree.py` を回し直すと、**エノキ・常緑・ケヤキ・モミジ・ムク・ウメの
51 点は姿が変わる**(焼いた後に骨格の作りが進んだため。頂点の多重集合で読み比べて確かめた)。
形は変えない約束なので、この 51 点は読み込み → 子の名だけ付け替え → 同じ設定で書き出す。
クロマツ・照葉低木の 18 点は `build_tree.py` で焼き直して頂点・UV まで一致したのでそちらで出した。

【守ること】
  ・メッシュ(data)の名は `LOD_%d` のまま(build_tree.py の書き出しと同じ)。⚠ ただし Unity の
    メッシュ名と fileID は**ノード名**から付くので、改名で fileID は変わる — Mesh を fileID で直に
    指す物(土井邸の庭に解いた木 14 本 = 42 本の MeshFilter)は張り替えた(2026-09-23)
  ・書き出しは `vklib.export_fbx`(部材の書き出しの正典)をそのまま使う
  ・書き戻す前に、元の版と頂点・UV・ループ法線の点群(両向きの最寄り距離)と三角数・材質名を
    読み比べ、ずれが 頂点 0.1mm / UV 1e-4 / 法線 1e-3 を超えたら書き戻さない(このスクリプトが自分で行う)
"""
import bpy, sys, os, re, shutil, tempfile
from mathutils import Vector, Matrix, kdtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V


def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    # ⛔ 材質も消す。残すと次の読み込みで `M_FJG_…​.001` と名が変わり、Unity の remap が外れる
    #   (2026-09-23 に一度そう書き出した。材質名は名前の完全一致で比べる)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)


def sig(path):
    """LOD ごとの中身: 世界座標の頂点・UV・ループ法線の点群、三角数、材質名。"""
    clear()
    bpy.ops.import_scene.fbx(filepath=path)
    out = {}
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        lod = int(re.search(r"LOD_?(\d)$", o.name.split('.')[0]).group(1))
        M = o.matrix_world; R = M.to_3x3()
        me = o.data
        uvl = me.uv_layers.active
        out[lod] = dict(
            tri=sum(len(p.vertices) - 2 for p in me.polygons),
            # ピボット(ノードの置き場と向き)も比べる — 頂点の世界座標が同じでも原点が動けば Unity で据わる位置が変わる
            node=tuple(round(c, 5) for row in M for c in row),
            parent=o.parent.name if o.parent else None,
            mats=tuple(m.name for m in me.materials),
            v=[(M @ v.co).copy() for v in me.vertices],
            uv=[Vector((l.uv[0], l.uv[1], 0)) for l in uvl.data] if uvl else [],
            n=[(R @ l.normal).normalized() for l in me.loops])
    return out


def far(a, b):
    """点群 a の各点から b の最寄りまでの距離の最大(両向きで取る)。
    ⛔ 丸めて md5 を取ると、書き出しの往復の 1e-7 の揺れが丸めの境を跨いで偽の差になる。"""
    def one(p, q):
        if not p: return 0.0
        t = kdtree.KDTree(len(q))
        for i, x in enumerate(q): t.insert(x, i)
        t.balance()
        return max(t.find(x)[2] for x in p)
    if len(a) != len(b): return float("inf")
    return max(one(a, b), one(b, a))


def same(a, b):
    if sorted(a) != sorted(b): return False, "LOD の組が違う"
    worst = []
    for k in a:
        if a[k]["tri"] != b[k]["tri"] or a[k]["mats"] != b[k]["mats"]:
            return False, "LOD%d 三角数か材質名が違う" % k
        if a[k]["node"] != b[k]["node"] or (a[k]["parent"] is None) != (b[k]["parent"] is None):
            return False, "LOD%d ノードの置き場・向き・親が違う %s → %s" % (k, a[k]["node"], b[k]["node"])
        dv, du, dn = far(a[k]["v"], b[k]["v"]), far(a[k]["uv"], b[k]["uv"]), far(a[k]["n"], b[k]["n"])
        worst.append((dv, du, dn))
        if dv > 1e-4 or du > 1e-4 or dn > 1e-3:
            return False, "LOD%d 頂点 %.2e / UV %.2e / 法線 %.2e" % (k, dv, du, dn)
    w = [max(x[i] for x in worst) for i in range(3)]
    return True, "最大のずれ 頂点 %.1e m / UV %.1e / 法線 %.1e" % tuple(w)


def relod(path):
    name = os.path.splitext(os.path.basename(path))[0]
    before = sig(path)
    clear()
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in objs:
        lod = int(re.search(r"LOD_?(\d)$", o.name.split('.')[0]).group(1))
        o.name = "%s_LOD%d" % (name, lod)
        o.data.name = "LOD_%d" % lod                    # data 名は build_tree.py と同じ綴り
        # ⭐ 読み込んだノードは 0.01 倍と軸の回転を抱えている。そのまま書き出すとノードの縮尺が
        #   0.0001 倍・向きも別になる(頂点の世界座標は同じでも Unity の子の Transform が変わる)。
        #   build_tree.py が書き出した時と同じ「単位行列のノード+世界座標の頂点」へ戻してから出す。
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    for o in [o for o in bpy.data.objects if o.type != 'MESH']:
        bpy.data.objects.remove(o, do_unlink=True)
    tmp = os.path.join(tempfile.mkdtemp(), name + ".fbx")
    V.export_fbx(objs, tmp)
    after = sig(tmp)
    ok, why = same(before, after)
    print("[relod] %-24s %s  %s" % (name, "SAME" if ok else "DIFF — 書き戻さない", why))
    if not ok:
        return False
    shutil.copyfile(tmp, path)
    return True


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
res = [relod(os.path.join(V.REPO, p) if not os.path.isabs(p) else p) for p in argv]
print("[relod] 書き戻し %d / %d" % (sum(res), len(res)))
