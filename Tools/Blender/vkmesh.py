"""面ごとに UV を決めて四角形を積む小さなメッシュビルダ。

`build_matsudaira_dewa_fuzokuya.py` が持っていた `Mesh` クラスと材の借用を、
**新しい部材スクリプトから共有できるように切り出した**もの(2026-09-03)。
⚠ fuzokuya 側は末尾で `main()` を無条件に呼ぶので **import できない** — だから
コピーではなくこちらへ出した。fuzokuya は当面そのまま(触ると松江松平の部材が焼き直しになる)。

【座標の約束】論理座標は **(走り, 高さ, 厚み)**。Blender は Z-up なので `quad` が
  (x, z, y) に入れ替える。`to_object` が **厚みを反転**して書き出す — `export_fbx` の
  `axis_forward='-Z', axis_up='Y'` が Blender +Y を Unity −Z へ写すため
  (README「書き出しの規約」)。結果、**論理 +厚み = Unity ローカル +Z = 見え面**。
⛔ 巻き順は反転しない。軸の入れ替えで鏡映1回・Y反転で2回目、そこで巻きも戻すと
  3回=奇数になって面が全部裏返る(2026-08-31 に番所で実測)。
"""
import bpy, os
from mathutils import Vector


class Mesh(object):
    """四角形を1枚ずつ積む。頂点は溶接しない(面ごとにUVを決めるため)"""

    def __init__(self):
        self.v, self.f, self.uv, self.mi = [], [], [], []

    def quad(self, pts, uv, mat=0):
        """pts は論理座標 (走り, 高さ, 厚み)。Blender は Z が上なので入れ替える"""
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2, i + 3])
        u0, v0, u1, v1 = uv
        self.uv += [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        self.mi.append(mat)

    def quad_uvs(self, pts, uvs, mat=0):
        """4隅の UV を**直に**与える四角形。⚠ `quad` は u=第1軸 / v=第2軸に固定なので、
        **木理を板の長手へ流す**ことができない(長い横板に縦木理が乗って、
        下見板が『縦縞の平板』に見えた。2026-09-04 に実見)。向きを変えたい面はこちらで出す。
        ⛔ 巻き順は pts の順のまま — ここで入れ替えると面が裏返る。"""
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2, i + 3])
        self.uv += list(uvs)
        self.mi.append(mat)

    def tri(self, pts, uv, mat=0):
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2])
        u0, v0, u1, v1 = uv
        self.uv += [(u0, v0), (u1, v0), ((u0 + u1) / 2, v1)]
        self.mi.append(mat)

    def box(self, x0, x1, y0, y1, z0, z1, uv, mat=0):
        """直方体。走り x・高さ y・厚み z"""
        self.quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], uv, mat)
        self.quad([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], uv, mat)
        self.quad([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], uv, mat)
        self.quad([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], uv, mat)
        self.quad([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], uv, mat)
        self.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], uv, mat)

    def koshi(self, x0, x1, y0, y1, z0, z1, uv, mat=0, pitch=0.13, bar=0.035, yoko=2):
        """格子窓。**板を1枚貼らない** — 竪子を実体で並べ、横子を数本渡す。
        一枚貼りにすると木のベタ板になる(番所の出格子で 2026-08-25 に踏んだ)。"""
        n = max(2, int((x1 - x0) / pitch))
        for i in range(n):
            cx = x0 + (x1 - x0) * (i + 0.5) / n
            self.box(cx - bar, cx + bar, y0, y1, z0, z1, uv, mat)
        for j in range(yoko):
            cy = y0 + (y1 - y0) * (j + 0.5) / yoko
            self.box(x0, x1, cy - bar, cy + bar, z0 - 0.008, z1 + 0.008, uv, mat)

    def shitami(self, x0, x1, y0, y1, z, out, uv, mat=0, pitch=0.20, lap=0.035):
        """**下見板張り**(南京下見)。⛔ 板を1枚貼らない — 重ねた横板を実体で積んで、
        目地の影で「板が重なっている」ことを出す(板戸で踏んだのと同じ罠。
        渋墨や漆喰は明暗が乏しいので、テクスチャでは継ぎ目が出ない)。

        z = 壁の面、out = 板が壁から手前へ出る向き(+1/−1)。板の下端が `lap` だけ
        せり出して下の板に被さる。"""
        n = max(1, int(round((y1 - y0) / pitch)))
        h = (y1 - y0) / n
        for i in range(n):
            a = y0 + i * h
            z0, z1 = sorted((z, z + out * 0.022))
            zl0, zl1 = sorted((z, z + out * (0.022 + lap)))
            self.box(x0, x1, a + h * 0.18, a + h, z0, z1, uv, mat)      # 板の身
            self.box(x0, x1, a, a + h * 0.18, zl0, zl1, uv, mat)        # 下端(せり出し)

    def frame(self, x0, x1, y0, y1, z0, z1, t, uv, mat=0):
        """中を抜いた四角い枠(井戸枠・玉垣の類)。t = 見込み"""
        self.box(x0, x1, y0, y1, z0, z0 + t, uv, mat)
        self.box(x0, x1, y0, y1, z1 - t, z1, uv, mat)
        self.box(x0, x0 + t, y0, y1, z0 + t, z1 - t, uv, mat)
        self.box(x1 - t, x1, y0, y1, z0 + t, z1 - t, uv, mat)

    def to_object(self, name, mats):
        """Blender へ落とす。厚みを反転して出す(モジュールの docstring 参照)。"""
        vs = [Vector((p.x, -p.y, p.z)) for p in self.v]
        faces, uvs, mi = [], [], []
        k = 0
        for fi, f in enumerate(self.f):
            n = len(f)
            faces.append(list(f))       # ⛔ 巻き順は反転しない
            uvs += list(self.uv[k:k + n])
            mi.append(self.mi[fi])
            k += n
        me = bpy.data.meshes.new(name)
        me.from_pydata(vs, [], faces)
        me.update()
        for m in mats:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for j, pg in enumerate(me.polygons):
            pg.material_index = mi[j]
        for j, dd in enumerate(uvl.data):
            dd.uv = uvs[j]
        o = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(o)
        return o


def sub(uv, u0, v0, u1, v1):
    """借りた矩形の中をさらに割る。**同じ矩形を全面に貼ると板がベタ塗りになる**"""
    a, b, c, d = uv
    return (a + (c - a) * u0, b + (d - b) * v0, a + (c - a) * u1, b + (d - b) * v1)


def rect_of(o, mat_name, fallback):
    """オブジェクトの、その材で一番大きい面の UV 矩形を返す。
    ⚠ 一点貼り(`set_uv`)はアトラスの1画素を伸ばして完全な無地になる。"""
    me = o.data
    uvl = me.uv_layers.active.data
    names = [mm.name if mm else "" for mm in me.materials]
    mi = names.index(mat_name) if mat_name in names else 0
    best, ba = None, -1.0
    for pg in me.polygons:
        if pg.material_index == mi and pg.area > ba:
            ba, best = pg.area, pg
    if best is None:
        return fallback
    us = [uvl[i].uv[0] for i in best.loop_indices]
    vs = [uvl[i].uv[1] for i in best.loop_indices]
    return (min(us), min(vs), max(us), max(vs))


def vk_mat(V, src, mat_name, fallback):
    """Village Kit の部材を一度読んで (material, uv矩形) を取り、オブジェクトは捨てる。
    **新規マテリアルを作らない** — 名前を保つと Unity 側の remap が既存 .mat を当てる。"""
    o = V.join(V.imp(src), "__src")
    m = bpy.data.materials.get(mat_name)
    rect = rect_of(o, mat_name, fallback)
    bpy.data.objects.remove(o, do_unlink=True)
    return m, rect


def ext_mat(V, root_mesh_dir, root_tex_dir, src, mat_name, fallback):
    """Village Kit 以外(Japanese Castle など)から借りる。V.MESH/V.TEX を一時的に差し替える。
    ⚠ import しないとマテリアルが存在せず、名前だけのスロットに落ちる(2026-08-25 に表門で踏んだ)"""
    keep_m, keep_t = V.MESH, V.TEX
    V.MESH, V.TEX = root_mesh_dir, root_tex_dir
    try:
        o = V.join(V.imp(src), "__srcext")
    except Exception as ex:
        V.MESH, V.TEX = keep_m, keep_t
        print("[vkmesh] ⚠ 材の借用に失敗: %s" % ex)
        return V.named_material(mat_name), fallback
    V.MESH, V.TEX = keep_m, keep_t
    m = bpy.data.materials.get(mat_name) or V.named_material(mat_name)
    rect = rect_of(o, mat_name, fallback)
    bpy.data.objects.remove(o, do_unlink=True)
    return m, rect


def import_fbx_abs(path, keep=None):
    """絶対パスの FBX を読み、メッシュだけ残して world 変換を焼く。
    keep(name)->bool で LOD の選り分けができる(NatureManufacture は `_LOD0/1/2` を1本に持つ)。"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    if meshes:
        bpy.ops.object.select_all(action='DESELECT')
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    out = []
    for o in new:
        if o.type != 'MESH' or (keep is not None and not keep(o.name)):
            bpy.data.objects.remove(o, do_unlink=True)
        else:
            out.append(o)
    return out
