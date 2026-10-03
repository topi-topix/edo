"""板塀を「板(柱なし)1間」と「柱1本」に分けた組 ── EDO-0437(山王 前庭の南の板塀 `Ita_ZSE`)。

    blender --background --python Tools/Blender/build_itabei_bunkatsu.py -- [--render]

⭐ **なぜ分けたか。** `Ita_ZSE` は切土の法肩の上に建ち、在庫の板塀 `Eg.Itabei5`(柱と板が一体の 5間の駒)を
   傾けて据えている。柱 5本の足の床の外れが最良の傾きでも 0.154 あり、根入れ 0.10 を超えて
   柱の浮き 0.013〜0.061 が 5本・埋まり 0.105 が 1本残る(棟梁の実測 2026-09-26・040b4353)。
   ⇒ 柱は 1本ずつ足を床に据え、板はその柱の間に掛ける。

⛔ **ゼロから起こさない。** 元は在庫の `Assets/edogoyomi/obj_itabei/itabei.obj`(= `itabei5.obj` の 1スパン。
   `itabei5` は同じ 121 頂点をピッチ 0.82023(素寸)で 5つ並べた物 ── 頂点・面を一つずつ突き合わせて確かめた)。
   それを ES=1.818 倍して、柱(`g pole` の柱身と根元の台)と板(`g hei` の貫3段・羽目板7枚・笠木)に**切り分けるだけ**。
   ジオメトリ・UV・材 `itabei` は一切変えない(柱の地中の継ぎ足しだけが新しい面)。

【柱の継ぎ足し】柱身の下端(地際の台の中 y=+0.038)から **y=−0.300 まで**同じ断面で継ぐ(根入れを取るため)。
   地上の柱身はそのまま(UV も元のまま)。継ぎ足しは柱身の箱を複製して縦に詰めた物で、UV は柱身と同じ矩形
   (地中に入る所なので縦に詰まって見えることは無い)。

【座標(Unity ローカル)】幅 = X(走り)/ 高さ = Y / 厚み = Z。y = 0 は**元の駒の y = 0**(板塀の地盤の基準)。
   ピボット = 板は**1間の板の中心**、柱は**柱の芯**(どちらも y = 0・z = 0)。
   柱の芯は板の中心から **±0.7456**(= ピッチ 1.4912 の半分)。板の端 = 柱の面(±0.7051)で、隙も重なりも無い。

【材】`itabei`(edogoyomi の .obj が**サブアセットとして抱えている**材)。独立した .mat が無いので
   `Edo/山王社/新造部材のマテリアルをremap` は `Eg.Itabei5` の中の材を直接借り先に足してある。
"""
import bpy, os, sys, math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ES = 1.818
SRC = os.path.join(V.REPO, "Assets", "edogoyomi", "obj_itabei", "itabei.obj")
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")
ROOT_BOT = -0.300              # 柱の継ぎ足しの下端(y)
PITCH = 0.820225 * ES          # 柱間(itabei5 の 1スパン)= 1.4912

NAME_ITA = "Itabei_Ita_1.410"
NAME_HASHIRA = "Itabei_Hashira_N0.30"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DO_RENDER = "--render" in argv


def load_src():
    """元の 1スパンを ES 倍で読む(Blender: X=走り / Z=高さ / −Y=厚み ⇒ Unity へは (−X, Z, −Y) で出る)。"""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=SRC)          # 既定 forward −Z / up Y = Unity の .obj 取り込みと同じ向き
    got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    o = V.join(got, "src") if len(got) > 1 else got[0]
    o.name = "src"
    o.scale = (ES, ES, ES)
    V.sel([o]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def ext(o):
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    return (min(w.x for w in ws), max(w.x for w in ws), min(w.y for w in ws), max(w.y for w in ws),
            min(w.z for w in ws), max(w.z for w in ws))


def split_parts(o):
    V.sel([o]); bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = [p for p in bpy.data.objects if p.type == 'MESH' and (p is o or p.name.startswith("src"))]
    post = foot = None; boards = []
    for p in parts:
        x0, x1, y0, y1, z0, z1 = ext(p)
        if z1 < 0.06: foot = p                                  # 根元の台(y −0.011..0.041)
        elif x1 - x0 < 0.1 and z1 - z0 > 1.0: post = p          # 柱身(0.081 角・丈 1.40)
        else: boards.append(p)                                  # 貫3・羽目板7・笠木
    assert post is not None and foot is not None and len(boards) == 11, (post, foot, len(boards))
    return post, foot, boards


def build():
    V.reset()
    src = load_src()
    ref = src.copy(); ref.data = src.data.copy(); bpy.context.scene.collection.objects.link(ref)
    ref.name = "ref"                                            # 検算用の元の姿
    post, foot, boards = split_parts(src)

    # ── 板 ──
    ita = V.join(boards, NAME_ITA)
    bx0, bx1 = ext(ita)[0:2]
    cb = (bx0 + bx1) / 2
    # ── 柱: 柱身の地中の継ぎ足し ──
    px0, px1, _, _, pz0, pz1 = ext(post)
    low = post.copy(); low.data = post.data.copy(); bpy.context.scene.collection.objects.link(low)
    for v in low.data.vertices:
        t = (v.co.z - pz0) / (pz1 - pz0)                        # 0..1 を ROOT_BOT..pz0 へ詰める
        v.co.z = ROOT_BOT + t * (pz0 - ROOT_BOT)
    global LOW_KEYS
    LOW_KEYS = [(v.co.x, v.co.y, v.co.z) for v in low.data.vertices]
    hashira = V.join([post, foot, low], NAME_HASHIRA)
    cp = (px0 + px1) / 2
    # ── 原点へ寄せる(set_origin だけにしない ── FBX ノードに平行移動が残る)──
    for o, c in ((ita, cb), (hashira, cp)):
        for v in o.data.vertices: v.co.x -= c
        o.location = (0, 0, 0)
    bpy.ops.object.select_all(action='DESELECT')
    # 孤立頂点・重複の掃除(bisect は使っていないが念のため数える)
    for o in (ita, hashira):
        V.sel([o]); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
        bpy.ops.object.mode_set(mode='OBJECT')
    global CP
    CP = cp
    return ita, hashira, ref, cb - cp


def report(ita, hashira, ref, off):
    import collections
    def ms(o, dx=0.0, skip=None):
        c = collections.Counter()
        for v in o.data.vertices:
            w = v.co
            if skip and skip(w): continue
            c[(round(w.x + dx, 4), round(w.y, 4), round(w.z, 4))] += 1
        return c
    want = ms(ref, -CP)
    got = ms(ita, off) + ms(hashira)
    extra = collections.Counter((round(x - CP, 4), round(y, 4), round(z, 4)) for x, y, z in LOW_KEYS)
    got_above = got - extra
    miss = want - got_above; more = got_above - want
    lines = []
    for o in (ita, hashira):
        x0, x1, y0, y1, z0, z1 = ext(o)
        lines.append("%s: Unity x %.4f..%.4f  y %.4f..%.4f  z %.4f..%.4f  頂点 %d 面 %d 材 %s" % (
            o.name, -x1, -x0, z0, z1, -y1, -y0, len(o.data.vertices), len(o.data.polygons),
            sorted({m.name for m in o.data.materials})))
    lines.append("柱芯→板の中心 (Unity x) = %.4f / ピッチ %.4f" % (-off, PITCH))
    lines.append("元の1スパンとの頂点の多重集合: 欠け %d / 余り %d / 継ぎ足し %d" % (
        sum(miss.values()), sum(more.values()), sum(extra.values())))
    return lines


def open_edges(o):
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    n = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    iso = sum(1 for v in bm.verts if not v.link_edges)
    bm.free(); return n, iso


def main():
    ita, hashira, ref, off = build()
    for l in report(ita, hashira, ref, off): print("[itabei]", l)
    for o in (ita, hashira): print("[itabei] 開いた辺/孤立頂点", o.name, open_edges(o))
    print("[itabei] 元の開いた辺", open_edges(ref))
    V.export_fbx([ita], os.path.join(OUT, NAME_ITA + ".fbx"))
    V.export_fbx([hashira], os.path.join(OUT, NAME_HASHIRA + ".fbx"))
    print("[itabei] 出した:", NAME_ITA, NAME_HASHIRA)
    if DO_RENDER:
        do_render(ita, hashira, ref, off)


def do_render(ita, hashira, ref, off):
    """① 上段: 分けた組を平らに 3間(柱4本)/ 下段: 元の 1スパン×3(同じ柱芯)── 同じ姿か。
    ② 分けた組を柱ごとに床の高さ違い(0 / +0.12 / +0.05 / +0.22)で据え、板は両側の柱の低い方に合わせて水平に掛ける。
    ③ 足元の寄り(柱の地中の継ぎ足し)。"""
    V.hook_textures()
    for o in (ita, hashira, ref): o.hide_render = True
    def put(src, x, z, y=0.0):
        c = src.copy(); c.data = src.data; bpy.context.scene.collection.objects.link(c)
        c.location = (x, y, z); c.hide_render = False; return c
    for k in range(4):
        put(hashira, k * PITCH, 1.8)
        if k < 3: put(ita, k * PITCH + off, 1.8)      # 板の中心 = 柱芯 + 0.7456(Blender。Unity では x が逆で −0.7456)
    for k in range(3):
        put(ref, k * PITCH - CP, 0.0)
    V.studio((2.2, -7.0, 1.7), (2.2, 0.0, 1.7), ortho_scale=6.6, res=(1600, 900))
    V.render(os.path.join(SHOT, "itabei_bunkatsu_1.png"))
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.data in (ita.data, hashira.data, ref.data) and o not in (ita, hashira, ref):
            bpy.data.objects.remove(o, do_unlink=True)
    hs = [0.00, 0.12, 0.05, 0.22]
    for k, h in enumerate(hs):
        put(hashira, k * PITCH, h - 0.10)
        if k < 3: put(ita, k * PITCH + off, min(h, hs[k + 1]) - 0.10)
        bpy.ops.mesh.primitive_cube_add(size=1)
        g = bpy.context.active_object; g.scale = (PITCH, 0.8, 0.4); g.location = (k * PITCH, 0, h - 0.2)
    cam = bpy.context.scene.camera
    cam.location = (2.2, -7.0, 0.9); cam.data.ortho_scale = 5.6
    V.render(os.path.join(SHOT, "itabei_bunkatsu_2.png"))
    for o in list(bpy.data.objects):
        if o.name.startswith("Cube"): bpy.data.objects.remove(o, do_unlink=True)
    cam.data.type = 'PERSP'
    cam.location = (PITCH + 0.9, -2.2, 0.25)
    d = mathutils.Vector((PITCH, 0, 0.1)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(SHOT, "itabei_bunkatsu_3.png"))


main()
