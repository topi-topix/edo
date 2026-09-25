"""城の石垣の駒(`Castle Wall`)の片端を、走りに対して斜めの**鉛直な面**で切った駒(EDO-0430)。

    blender --background --python Tools/Blender/build_ishigaki_kiri.py -- kiri_list Tools/Blender/sanno_ishigaki_kiri_set.txt --render
    blender --background --python Tools/Blender/build_ishigaki_kiri.py -- kiri 43.2 P L --render      # 1 本だけ

【なぜ要るか】山王 前庭の土留め TW_Zentei_SW / SE の端に女坂の口が開き、その袖が土留めの走りに約 43° で
  交わる。直の小口(走りに直角)では袖の面に面で当たらず、口かめり込みが残る(許容0)。⇒ 駒の端を袖の面で切る。

【作り】**ゼロから作らない。**在庫の `Castle Wall`(走り 2.0・丈 4.0・奥行 足 2.4 / 天端 1.4・法 1:0.25)を
  走りに 2 枚つないだ 4.0m の一本物を、斜めの鉛直面で切る。切り口は袖の面に当たって隠れる面で、
  素の小口と同じ柄の帯(アトラス u 0.26〜0.74 / v 0.01〜0.74)を面の座標で貼る(一点貼りにしない)。
  ⭐ 1 本物にした理由: 斜めの面は足で走り 2.55m に跨り、駒 2 枚を切る。2 枚組だと各駒のどこで切るかが
     run の割付けから決まる連続値になり、焼く組が尽きない。1 本物なら形は角と向きだけで決まり、
     据える側は**実メッシュの天端の前の縁の端**を相手の点へ当てるだけで済む(残りの直線材はこの駒に重ねる)。

【局所座標(Unity)】`Castle Wall` と同じ規約: 走り = Z(駒は Z ∈ [−4.0, 0])/ 高さ = Y(足元 0・天端 4.0)/
  控え(鉛直な背)= X = 0 / 見え面(法)は −X 側(足 X = −2.4・天端 X = −1.4)。
  ピボット = 切っていない 2 枚の枠の +Z 端・控え・足元(⛔ 切った端でピボットを決めない)。
  切る端: `P` = +Z 端(ピボットの側)/ `M` = −Z 端。
  面の向き: `L` = 見え面の側が長い(足の前が一番先へ出る)/ `S` = 見え面の側が短い(控えが一番先へ出る)。
  切り口の一番先へ出る点が 2 枚の枠の端(Z = 0 か −4.0)に来る。
  角 deg = 切る面の平面の線が走りとなす角。奥行 2.4 で走りに 2.4/tan(deg) ずれる(43.2° で 2.556)。

【落とし穴】
  ・素の駒は**底が開いている**(境界の辺 8 本)。holes_fill は底まで塞ぐ ⇒ 切り口の面の上の頂点だけで
    凸な多角形を張る(断面は台形で凸)。
  ・2 枚をつなぐ継ぎ目に向かい合う小口が 2 枚残る ⇒ 消してから頂点を溶かす(切り口から覗く)。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ROOT = V.REPO
JC = os.path.join(ROOT, "Assets/Japanese Castle")
OUT = V.out_dir(os.path.join(ROOT, "Assets/Edo/Models/Kado"))
SHOT = os.path.join(ROOT, "Screenshots")
PITCH = 2.0
NMOD = 2
DEPTH = 2.4          # 足の奥行(控え〜見え面の足)
CREST_W = 1.4        # 天端の奥行
H = 4.0
BATTER = 0.25
# 切り口に貼る帯(素の小口が使う石の帯)。1.4m → u 0.25 / 1.0m → v 0.25 が素の密度
CAP_U = (0.26, 0.74)
CAP_V = (0.01, 0.74)


def kiri_name(deg, end, face):
    return "Ishigaki_Kiri_%03d_%s%s" % (int(round(abs(deg) * 10)), end, face)


def load_module():
    V.MESH = os.path.join(JC, "Meshes"); V.TEX = os.path.join(JC, "Textures")
    o = V.join(V.imp("Exterior/Castle Wall.fbx"), "src")
    me = o.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print("[kiri] 素の bbox x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]" % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    dx, dy, dz = -min(xs), -min(ys), -min(zs)
    for v in me.vertices:
        v.co.x += dx; v.co.y += dy; v.co.z += dz
    me.update()
    return o


def tile2(o):
    """走り(Blender +Y = Unity −Z)に 2 枚つなぎ、継ぎ目の向かい合う小口を消して溶かす。"""
    parts = [o]
    for k in range(1, NMOD):
        c = o.copy(); c.data = o.data.copy(); bpy.context.collection.objects.link(c)
        for v in c.data.vertices:
            v.co.y += k * PITCH
        c.data.update(); parts.append(c)
    o = V.join(parts, "kiri")
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    seam = [f for f in bm.faces if abs(f.normal.y) > 0.99 and 0.5 < f.calc_center_median().y < NMOD * PITCH - 0.5]
    bmesh.ops.delete(bm, geom=seam, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return o


def kiri(deg, end, face):
    o = tile2(load_module())
    ct = 1.0 / math.tan(math.radians(abs(deg)))
    Y = NMOD * PITCH
    # 残す側の式(確かめやすいよう y_cut を直に書く)
    ycut = {("P", "L"): lambda x: (DEPTH - x) * ct, ("P", "S"): lambda x: x * ct,
            ("M", "L"): lambda x: Y - (DEPTH - x) * ct, ("M", "S"): lambda x: Y - x * ct}[(end, face)]
    keep_ge = end == "P"
    # 平面: y − ycut(x) = 0 ⇒ 法線 (−dycut/dx, 1, 0)、点 (0, ycut(0), 0)
    dydx = ycut(1.0) - ycut(0.0)
    nrm = Vector((-dydx, 1.0, 0.0)).normalized()
    co = Vector((0.0, ycut(0.0), 0.0))
    bm = bmesh.new(); bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                           plane_co=co, plane_no=nrm, clear_outer=not keep_ge, clear_inner=keep_ge)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # ⚠ 面が素の頂点の極く近く(1e-5)を通ると、bisect がその頂点の脇に新しい頂点を作る(M·S の控えの角で 5 組)。溶かす
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    # 切り口: 面の上の頂点で凸な多角形を張る
    on = [v for v in bm.verts if abs((v.co - co).dot(nrm)) < 5e-5]
    t = Vector((nrm.y, -nrm.x, 0.0))          # 面の中の水平
    cen = sum((v.co for v in on), Vector()) / len(on)
    on.sort(key=lambda v: math.atan2((v.co - cen).z, (v.co - cen).dot(t)))
    # 同じ位置の重複を除く
    uniq = []
    for v in on:
        if not uniq or (uniq[-1].co - v.co).length > 1e-5:
            uniq.append(v)
    f = bm.faces.new(uniq)
    bm.normal_update()
    outward = -nrm if keep_ge else nrm         # 捨てた側を向く
    if f.normal.dot(outward) < 0:
        f.normal_flip()
    f.material_index = 0
    # UV: 面の座標(水平 s・高さ z)を素の小口の帯へ。帯の幅に収まるよう一様に縮める(柄の縦横比を保つ)
    ss = [(l.vert.co - cen).dot(t) for l in f.loops]
    s0, s1 = min(ss), max(ss)
    k = min((CAP_U[1] - CAP_U[0]) / max(1e-6, (s1 - s0) * 0.25 / CREST_W),
            (CAP_V[1] - CAP_V[0]) / (H * 0.25))
    for l, s in zip(f.loops, ss):
        u = CAP_U[0] + (s - s0) * 0.25 / CREST_W * k
        v = CAP_V[0] + l.vert.co.z * 0.25 * k
        l[uvl].uv = (u, v)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    name = kiri_name(deg, end, face)
    o.name = name; o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[kiri] 切り口 %d 角形・帯の縮み %.3f" % (len(uniq), k))
    return o, name, ycut


def unity_verts(o):
    return [(-v.co.x, v.co.z, -v.co.y) for v in o.data.vertices]   # (X, Y, Z)


def check(o, deg, end, face, ycut):
    ok = []
    uv = unity_verts(o)
    X = [p[0] for p in uv]; Yv = [p[1] for p in uv]; Z = [p[2] for p in uv]
    print("[kiri] %s Unity実寸 W(X)=%.3f H(Y)=%.3f D(Z)=%.3f  X %.3f..%.3f  Y %.3f..%.3f  Z %.3f..%.3f  面=%d  材=%s"
          % (o.name, max(X) - min(X), max(Yv) - min(Yv), max(Z) - min(Z), min(X), max(X), min(Yv), max(Yv), min(Z), max(Z),
             len(o.data.polygons), [m.name for m in o.data.materials]))
    Ymax = NMOD * PITCH
    # 切った側より外に頂点が無い / 切り口に頂点が乗る
    sgn = 1.0 if end == "P" else -1.0
    bite = max(sgn * (ycut(v.co.x) - v.co.y) for v in o.data.vertices)
    ok.append(("切る面より外に頂点が無い", bite < 5e-5, "%.6f" % bite))
    on = [v for v in o.data.vertices if abs(v.co.y - ycut(v.co.x)) < 5e-5]
    ok.append(("切る面に頂点が乗る", len(on) >= 6, "%d 点" % len(on)))
    # 面の角を測り直す: 控え(x=0)と足の前(x=2.4, z=0)の切り口の走りの差
    back = [v.co.y for v in on if v.co.x < 1e-4]
    foot = [v.co.y for v in on if abs(v.co.x - DEPTH) < 1e-4 and v.co.z < 1e-4]
    if back and foot:
        dy = abs(back[0] - foot[0])
        ang = math.degrees(math.atan2(DEPTH, dy))
        ok.append(("面の角 %.1f°(控えと足の前の走りの差 %.3f)" % (deg, dy), abs(ang - abs(deg)) < 0.01, "%.3f°" % ang))
        longer = "L" if (foot[0] < back[0]) == (end == "P") else "S"
        ok.append(("見え面の側が%s" % ("長い" if face == "L" else "短い"), longer == face, longer))
    # 一番先へ出る点が枠の端
    tip = min(v.co.y for v in o.data.vertices) if end == "P" else max(v.co.y for v in o.data.vertices)
    ok.append(("一番先が 2 枚の枠の端", abs(tip - (0.0 if end == "P" else Ymax)) < 1e-4, "%.4f" % tip))
    # 反対の端は素のまま(直の小口)
    far = max(v.co.y for v in o.data.vertices) if end == "P" else min(v.co.y for v in o.data.vertices)
    ok.append(("反対の端は素の小口", abs(far - (Ymax if end == "P" else 0.0)) < 1e-4, "%.4f" % far))
    # 見え面の法が素のまま(x + 0.25 z = 2.4 の上の頂点がある・越える頂点が無い)
    over = max(v.co.x + BATTER * v.co.z - DEPTH for v in o.data.vertices)
    ok.append(("見え面の法を越えない", over < 1e-4, "%.5f" % over))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    bm = bmesh.new(); bm.from_mesh(o.data)
    bnd = [e for e in bm.edges if e.is_boundary]
    open_up = [e for e in bnd if max(v.co.z for v in e.verts) > 1e-4]
    ok.append(("底のほかに開いた辺が無い", len(open_up) == 0, "%d 本" % len(open_up)))
    bm.free()
    ok.append(("材が stone wall だけ", [m.name for m in o.data.materials] == ["stone wall"], ""))
    # 天端の前の縁の端(据える側が当てる点)を報告する
    crest = [p for p in uv if abs(p[1] - H) < 1e-4]
    if crest:
        fx = min(p[0] for p in crest)
        cf = [p for p in crest if abs(p[0] - fx) < 1e-4]
        zt = max(p[2] for p in cf) if end == "P" else min(p[2] for p in cf)
        print("[kiri]   天端の前の縁の端(局所) X %.3f Y %.3f Z %.4f" % (fx, H, zt))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    if any(not t_[1] for t_ in ok):
        raise SystemExit("[kiri] ⛔ 検算が落ちた")


def read_list(path):
    rows = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            tag, deg, end, face = ln.split()
            rows.append((tag, float(deg), end, face))
    return rows


def shots(objs, key):
    """組み絵: 焼いた駒を並べ、切り口の側から・上から・背景マゼンタで刷る。"""
    V.hook_textures()
    mn, mx = V.bbox(objs)
    c = (mn + mx) * 0.5
    r = max((mx - mn).x, (mx - mn).y, 4.0)
    outs = []
    world = bpy.context.scene.world
    for tag, cam in (("3d", (c.x - r * 1.1, c.y - r * 1.2, c.z + r * 0.9)),
                     ("cut", (c.x - r * 0.3, c.y - r * 1.6, c.z + r * 0.3)),
                     ("cutback", (c.x + r * 1.3, c.y - r * 1.2, c.z + r * 0.6)),
                     ("plan", (c.x, c.y, c.z + r * 3.0)),
                     ("magenta", (c.x - r * 0.9, c.y - r * 1.4, c.z + r * 0.4))):
        V.studio(cam, (c.x, c.y, c.z if tag != "plan" else 0.0), res=(1400, 900))
        if tag == "magenta":
            w = bpy.context.scene.world
            if w and w.use_nodes:
                bg = w.node_tree.nodes.get("Background")
                if bg:
                    bg.inputs[0].default_value = (1.0, 0.0, 1.0, 1.0)
        p = os.path.join(SHOT, "ishigaki_kiri_%s_%s.png" % (key, tag))
        V.render(p); outs.append(p)
    return outs


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    pos = [a for a in argv if not a.startswith("--")]
    what = pos[0] if pos else "kiri"
    if what == "kiri_list":
        rows = read_list(os.path.join(ROOT, pos[1]) if not os.path.isabs(pos[1]) else pos[1])
        key = os.path.splitext(os.path.basename(pos[1]))[0]
    else:
        rows = [("-", float(pos[1]), pos[2], pos[3])]
        key = kiri_name(rows[0][1], rows[0][2], rows[0][3])
    V.reset()
    made = []
    for i, (tag, deg, end, face) in enumerate(rows):
        V.reset()                                   # 読み直すと材が `stone wall.001` になる
        o, name, ycut = kiri(deg, end, face)
        check(o, deg, end, face, ycut)
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)
        print("[kiri] 書き出し %s ← %s" % (path, tag))
        made.append(path)
    if do_render:
        # export_fbx の後は bbox が潰れる ⇒ 書いた FBX を読み戻して並べる
        V.reset()
        objs = []
        for i, path in enumerate(made):
            bpy.ops.import_scene.fbx(filepath=path)
            for ob in bpy.context.selected_objects:
                if ob.type == "MESH":
                    ob.location.x += i * 6.0
                    objs.append(ob)
        for p in shots(objs, key):
            print("[kiri] 検証レンダ " + p)


main()
