"""練塀 `Dobei2m` の下に据える **布石(腰の石)** — 切石の布積み 1駒(EDO-0477)。

    blender --background --python Tools/Blender/build_dobei_nunoishi.py -- [--render]

【用途】斜面の区画の線に立つ練塀を**段塀**で建てる。区間ごとに塀の笠を水平にし、区間の中で
  地面が下がる所は、塀の下端と地面の間を布石の見え(0〜約1.1m)で受ける。見えない所は地面に
  埋めて隠す(一種類の丈の駒を据え、下は埋まる)。考証: 屋敷の練塀は傾けず、足元の差は
  布石・根石の見え高さで受ける【U】。呼び手は EdoBuild の練塀の段塀。

【寸法(呼び手の決定値)】
  総丈 1.30(天端 y=0・下端 y=−1.30)/ 厚み 0.56(下見板 0.42 より片側 0.07 出る)/
  走り 2.004(= Dobei2m の1駒)。
  ローカル座標は `build_dobei.py` と**同じ Blender 座標で同じ書き出し**にしてある:
  Blender X = 走り ∈ [0, L] / Blender Y = 厚み(芯0で対称)/ Blender Z = 高さ。
  ⇒ Unity でも Dobei2m と同じ軸・同じ原点(走りの起点・厚みの芯・天端)で読める。scale=1。

【形】切石の布積み 4段(上から 0.30 / 0.32 / 0.33 / 0.35)。横目地は通し、縦目地は段ごとに
  互い違い。石は厚みを通す**通し石**(両面とも見え面)。天端は平ら。
  ・縦目地は**駒の中だけ**に置き、駒の両端(x=0 / x=L)では石を**切ったまま**にする。
    ⇒ 駒を並べると端の石どうしが一枚の石として続き、継ぎ目に縦目地が揃って立たない。
    段ごとの目地の集合は [0, L) の中で決めるので、並べれば自動で周期になる。
    ⛔ 目地を端から 0.14 以内に置かない(継ぎ目の両側に細い欠片ができる)。
  ・稜の面取り 0.03(1 セグメント・下端の平面の稜は埋まるので除く)は**駒の端の平面に乗る稜を除く全稜**に掛ける。
    ⚠ 端の平面の稜まで丸めると、並べた継ぎ目ごとに縦の溝が立って目地に見える。
    端の小口は面で塞いである(段の所で小口が見える — 切石の切り口として読める)。
  ・材は `Kirishi`(`Assets/Edo/Materials/Sanno/Kirishi.mat`)。⛔ 新規の材は作らない —
    `build_sanno_buzai.kirishi_material()` は同名の入れ物に検証レンダ用の実テクスチャを結ぶだけ。
    UV はタイル貼り 1.05 m(⛔ 0.44 は normal の 2×2 の継ぎ目が 0.22m ごとに立ち小口積みに見える —
    memory kirishi-tile-and-shu-material)。面ごとに位相だけずらす(⛔ 伸縮しない)。

【検算(焼くたびに刷る)】外形 / 三角形数 / 石ごとの閉じ(非多様体の辺 0)/
  石ごとの符号付き体積 > 0(外向き)/ 縦目地の段どうしの離れ(周期で見る)。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_tateishi as BT          # ensure_outward(符号付き体積で外向き)
import build_sanno_buzai as SB       # 切石の材 `Kirishi`(⭕ main は __main__ 束縛なので安全)

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Dobei"))
NAME = "Dobei2m_Nunoishi"
SHOT = os.path.join(V.REPO, "Screenshots")

L = 2.004                 # 走り = Dobei2m の1駒(瓦1枚ぶん)
T = 0.56                  # 厚み
H = 1.30                  # 総丈(天端 0・下端 −H)
COURSES = (0.30, 0.32, 0.33, 0.35)   # 上から。和 = H
ROUND = 0.03              # 稜の丸め
ROUND_SEG = 1             # ⚠ 2 だと 1472 三角形(Dobei2m 404 の 3.6 倍)。1 で 0.03 の面取り
TILE = 1.05               # Kirishi のタイル実寸
END_MIN = 0.14            # 端から目地までの最小
# 段ごとの縦目地(x)。⭐ 上下の段と 0.24 以上ずらす(周期 L で測る)。1駒に石3枚(0.6〜0.75)。
#   1段おきにほぼ揃うのは布積みの破れ目地として正しい(少しだけ振ってある)。
JOINTS = (
    (0.25, 0.93, 1.58),      # 1段目(天端)
    (0.55, 1.22, 1.82),      # 2段目
    (0.20, 0.87, 1.50),      # 3段目
    (0.52, 1.18, 1.80),      # 4段目(ほぼ埋まる)
)
assert abs(sum(COURSES) - H) < 1e-9


def _cdist(a, b):
    d = abs(a - b) % L
    return min(d, L - d)


def check_joints():
    """縦目地の周期上の離れ。端の欠片・隣の段との揃いを見る。"""
    worst = 9.0
    for k, js in enumerate(JOINTS):
        for x in js:
            assert END_MIN <= x <= L - END_MIN, (k, x)
        if k + 1 < len(JOINTS):
            for a in js:
                for b in JOINTS[k + 1]:
                    worst = min(worst, _cdist(a, b))
    # 継ぎ目を跨ぐ端の石の見かけの長さ
    spans = []
    for js in JOINTS:
        xs = [0.0] + list(js) + [L]
        spans.append([round(b - a, 3) for a, b in zip(xs, xs[1:])])
        spans[-1].append(round(xs[1] + (L - xs[-2]), 3))   # 継ぎ目を跨いだ石
    return worst, spans


def stone(x0, x1, z0, z1, mat, rng, name):
    """通し石1枚。x0==0 / x1==L の端の平面に乗る稜は丸めない(継ぎ目で石が続く)。"""
    y0, y1 = -T / 2.0, T / 2.0
    bm = bmesh.new()
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=vs, vec=(x1 - x0, y1 - y0, z1 - z0))
    bmesh.ops.translate(bm, verts=vs, vec=((x0 + x1) / 2, 0.0, (z0 + z1) / 2))
    eps = 1e-6
    cut = []
    if x0 < eps:
        cut.append(0.0)
    if x1 > L - eps:
        cut.append(L)
    buried = z0 < -H + eps          # 下端の平面の稜は常に埋まる — 面取りしない(面数を抑える)

    def on_cut_plane(e):
        if buried and all(abs(v.co.z + H) < eps for v in e.verts):
            return True
        return any(all(abs(v.co.x - c) < eps for v in e.verts) for c in cut)

    edges = [e for e in bm.edges if not on_cut_plane(e)]
    bmesh.ops.bevel(bm, geom=edges, offset=ROUND, offset_type='OFFSET',
                    segments=ROUND_SEG, profile=0.5, affect='EDGES', clamp_overlap=True)
    BT.ensure_outward(bm)
    bm.normal_update()
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        du, dv = rng.random(), rng.random()
        for lp in f.loops:
            co = lp.vert.co
            a, b = ((co.x, co.y) if ax == 2 else (co.x, co.z) if ax == 1 else (co.y, co.z))
            lp[uvl].uv = (a / TILE + du, b / TILE + dv)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free(); me.update()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def build(name=NAME):
    mat = SB.kirishi_material()
    rng = random.Random("dobei_nunoishi")
    parts = []
    ztop = 0.0
    for k, (h, js) in enumerate(zip(COURSES, JOINTS)):
        z1, z0 = ztop, ztop - h
        xs = [0.0] + list(js) + [L]
        for i, (a, b) in enumerate(zip(xs, xs[1:])):
            parts.append(stone(a, b, z0, z1, mat, rng, "%s_%d_%d" % (name, k, i)))
        ztop = z0
    return V.join(parts, name)


def audit(o):
    """閉じ・外向き・外形を刷る。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    # 石(連結成分)ごとの符号付き体積
    seen, vols = set(), []
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        stack, comp = [f0], []
        seen.add(f0.index)
        while stack:
            f = stack.pop(); comp.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index); stack.append(g)
        vol = 0.0
        for f in comp:
            p = [v.co for v in f.verts]
            for i in range(1, len(p) - 1):
                vol += p[0].dot(p[i].cross(p[i + 1])) / 6.0
        vols.append(vol)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    bm.free()
    return dict(nonmanifold=nonman, stones=len(vols), min_vol=min(vols), vol=sum(vols),
                tris=tris, verts=len(me.vertices),
                x=(min(xs), max(xs)), y=(min(ys), max(ys)), z=(min(zs), max(zs)))


def _mat_neutral(nm, rgb):
    m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*rgb, 1.0)
    b.inputs['Roughness'].default_value = 1.0
    return m


def render(o):
    """単体・並べた段塀(Dobei2m を載せ地面で埋める)・マゼンタ背景で穴を見る。"""
    dob = os.path.join(V.REPO, "Assets", "Edo", "Models", "Dobei", "Dobei2m.fbx")
    ground = _mat_neutral("_ground_preview", (0.07, 0.055, 0.035))

    def put(src, x, z, name):
        c = src.copy(); c.data = src.data; c.name = name
        bpy.context.scene.collection.objects.link(c)
        c.location = Vector((x, 0.0, z))
        c.hide_render = False       # ⚠ 元を隠してから写すと写しも隠れる
        return c

    # 単体
    V.studio((3.4, -2.6, 0.55), (1.0, 0.0, -0.65), res=(1400, 900))
    V.render(os.path.join(SHOT, "dobei_nunoishi_persp.png"))
    V.studio((1.0, -5.0, -0.65), (1.0, 0.0, -0.65), ortho_scale=2.4, res=(1400, 900))
    V.render(os.path.join(SHOT, "dobei_nunoishi_elev.png"))
    V.studio((-1.6, -1.5, 0.35), (0.3, 0.0, -0.55), res=(1300, 950))
    V.render(os.path.join(SHOT, "dobei_nunoishi_end.png"))

    # 段塀: 区間A(3駒)天端 0 / 区間B(3駒)天端 −0.60。地面は斜面を折れ線で。
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=dob)
    dparts = [q for q in bpy.data.objects if q not in before and q.type == 'MESH']
    for q in [q for q in bpy.data.objects if q not in before and q.type != 'MESH']:
        bpy.data.objects.remove(q, do_unlink=True)
    V.sel(dparts); bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    dsrc = V.join(dparts, "Dobei2m_src")
    V.hook_textures()
    keep = V.TEX
    V.TEX = os.path.join(V.REPO, "Assets", "Japanese Castle", "Textures")
    V.hook_textures()
    V.TEX = keep
    o.location = Vector((0, 0, 0))
    o.hide_render = True
    dsrc.hide_render = True
    run = []
    for i in range(6):
        top = 0.0 if i < 3 else -0.60
        run.append(put(o, L * i, top, "nuno_%d" % i))
        run.append(put(dsrc, L * i, top, "dobei_%d" % i))
    # 地面: x=0 で −0.05 から x=12 で −1.25 へ下がる(区間ごとに見えが 0.05→0.65 と変わる)
    gv = [(-3, -8, 0.10), (13, -8, -1.25), (13, 8, -1.25), (-3, 8, 0.10)]
    me = bpy.data.meshes.new("ground"); me.from_pydata([Vector(p) for p in gv], [], [[0, 1, 2, 3]])
    me.materials.append(ground)
    g = bpy.data.objects.new("ground", me); bpy.context.scene.collection.objects.link(g)
    # ⚠ 地面の勾配 1.35/16 は緩いので、塀の足元で見えが 0〜0.6 に収まる
    V.studio((-2.8, -7.5, 1.6), (6.0, 0.0, 0.2), res=(1600, 900))
    V.render(os.path.join(SHOT, "dobei_nunoishi_dan_eye.png"))
    V.studio((7.2, -3.2, 0.2), (6.0, 0.0, -0.4), res=(1500, 950))
    V.render(os.path.join(SHOT, "dobei_nunoishi_dan_step.png"))
    V.studio((7.0, 3.6, 0.4), (6.0, 0.0, -0.4), res=(1500, 950))   # 裏(区画の内)から段を見る
    V.render(os.path.join(SHOT, "dobei_nunoishi_dan_back.png"))
    # マゼンタ背景 + 地面を外して、並べた布石だけで穴・継ぎ目を見る
    g.hide_render = True
    for c in run:
        if c.name.startswith("dobei_"):
            c.hide_render = True
    V.studio((2.0, -3.4, 0.2), (4.0, 0.0, -0.65), res=(1500, 950))
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
    V.render(os.path.join(SHOT, "dobei_nunoishi_seam_magenta.png"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    V.reset()
    worst, spans = check_joints()
    print("[nunoishi] 縦目地の段どうしの最小の離れ %.3f m" % worst)
    for k, s in enumerate(spans):
        print("[nunoishi]  段%d 石の長さ %s(最後は継ぎ目を跨いだ石)" % (k + 1, s))
    o = build()
    a = audit(o)
    print("[nunoishi] 石 %d 個 / 三角形 %d / 頂点 %d / 非多様体の辺 %d / 石の体積の最小 %.4f / 総体積 %.4f (箱 %.4f)"
          % (a["stones"], a["tris"], a["verts"], a["nonmanifold"], a["min_vol"], a["vol"], L * T * H))
    print("[nunoishi] Blender 外形 x[%.4f, %.4f] y[%.4f, %.4f] z[%.4f, %.4f]" % (a["x"] + a["y"] + a["z"]))
    print("[nunoishi] ⇒ Unity 論理 走り %.4f / 厚み ±%.4f / 高さ [%.4f, %.4f]"
          % (a["x"][1] - a["x"][0], (a["y"][1] - a["y"][0]) / 2, a["z"][0], a["z"][1]))
    print("[nunoishi] mats: %s" % ", ".join(m.name for m in o.data.materials if m))
    assert a["nonmanifold"] == 0 and a["min_vol"] > 0
    if "--render" in argv:
        render(o)
        o.hide_render = False
    # ⚠ export_fbx の後は bbox が潰れる — 測りとレンダは先に済ませてある
    for q in [q for q in bpy.data.objects if q is not o]:
        q.select_set(False)
    path = os.path.join(OUT, NAME + ".fbx")
    V.export_fbx([o], path)
    print("[nunoishi] wrote %s" % path)


if __name__ == "__main__":
    main()
