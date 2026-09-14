# -*- coding: utf-8 -*-
"""山王権現社の**小庭の井戸** — 井筒(玉石の輪積み)と井桁だけ。井戸屋形・釣瓶・石敷は持たない。

    blender --background --python Tools/Blender/build_sanno_ido.py -- [--render] [--no-export]

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
庭方の設計(確度 U): 「前庭の井戸と同じ作り」= 指図 `ido.izutsu`(野面(玉石)の輪積み・内径 3 尺・壁厚 0.24)と
井桁(内法 3 尺・見付 0.15 × 3 段 = `ido.igetaShaku` / `igetaMitsukeM` / `igetaDanN`)。
在庫の `Doi_Ido` / `Matsudaira_Ido` はどちらも**切石の角井戸枠 + 桁 + 釣瓶**で、玉石の輪も井桁も持たない
(切り出しても形が違う)⇒ 新造。材は Village Kit の `Foundation_A_01`(アトラス全面が玉石積み)と `wood`。⛔ 新規マテリアルなし。

━━━ 軸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unity ローカル: 高さ = Y / 平面 = X・Z(円形・井桁は X と Z に対称)/ **ピボット = 井戸の芯・地盤レベル**。
・井筒: 天端 +0.05(地盤から石の輪を覗かせる)〜 根入れ −1.50、底は石の円板【U 部材方】。
・井桁: 井筒の天端から 3 段(0.05〜0.50)。段ごとに向きを互い違いにし、木口を 0.06 出す【U 部材方】。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
SHAKU = 1.818 / 6.0
SPEC = dict(naikeiShaku=3, kabeAtsuM=0.24, igetaShaku=3, igetaMitsukeM=0.15, igetaDanN=3)   # 指図 `ido`(前庭の井戸)
G = dict(top=0.05, depth=1.50, koguchi=0.06, nSeg=36, texM=1.82)   # 【U 部材方】
ALLOWED = ("wood", "Foundation_A_01")


def stone_mat():
    m, rect = VM.vk_mat(V, "Foundations/Foundation_A_01_2x2.fbx", "Foundation_A_01", (0.0, 0.0, 1.0, 1.0))
    if m is None:
        raise SystemExit("[ido] ⛔ Foundation_A_01 が取れない")
    return m, rect


def ring(name, r_in, r_out, y0, y1, mat, rect):
    """玉石の輪(閉じた筒)。頂点を溶接して法線を外向きに揃え、UV は円周を 3 分割してアトラスの矩形の中へ写す。"""
    n = G["nSeg"]
    per = n // 3
    bm = bmesh.new()
    V4 = {}
    for i in range(n):
        a = 2 * math.pi * i / n
        for key, r in (("o", r_out), ("i", r_in)):
            for yk, y in (("b", y0), ("t", y1)):
                bx, by = SH.BX(r * math.cos(a), r * math.sin(a))
                V4[(key, yk, i)] = bm.verts.new((bx, by, y))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append(("o", bm.faces.new((V4[("o", "b", i)], V4[("o", "b", j)], V4[("o", "t", j)], V4[("o", "t", i)])), i))
        faces.append(("i", bm.faces.new((V4[("i", "b", j)], V4[("i", "b", i)], V4[("i", "t", i)], V4[("i", "t", j)])), i))
        faces.append(("t", bm.faces.new((V4[("o", "t", i)], V4[("o", "t", j)], V4[("i", "t", j)], V4[("i", "t", i)])), i))
        faces.append(("b", bm.faces.new((V4[("i", "b", i)], V4[("i", "b", j)], V4[("o", "b", j)], V4[("o", "b", i)])), i))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    uvl = bm.loops.layers.uv.new("UVMap")
    u0, v0, u1, v1 = rect
    tex = G["texM"]
    for kind, f, i in faces:
        for lp in f.loops:
            co = lp.vert.co
            if kind in ("o", "i"):
                r = r_out if kind == "o" else r_in
                seg_arc = 2 * math.pi * r / 3.0
                a = math.atan2(-co.y, -co.x) % (2 * math.pi)     # 論理の角度(BX の逆)
                k = min(2, int(i // per))
                t = a / (2 * math.pi / 3.0) - k
                if abs(t) > 1.5:                                    # 周の継ぎ目(i=n-1 → j=0)
                    t += 3.0
                t = max(0.0, min(1.0, t))
                uu = u0 + (u1 - u0) * t * min(1.0, seg_arc / tex)
                vv = v0 + (v1 - v0) * min(1.0, (co.z - y0) / tex)
            else:
                uu = u0 + (u1 - u0) * (0.5 + co.x / tex)
                vv = v0 + (v1 - v0) * (0.5 + co.y / tex)
            lp[uvl].uv = (uu, vv)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    return o


def disc(name, r, y, mat, rect):
    bm = bmesh.new()
    n = G["nSeg"]
    vs = []
    for i in range(n):
        a = 2 * math.pi * i / n
        bx, by = SH.BX(r * math.cos(a), r * math.sin(a))
        vs.append(bm.verts.new((bx, by, y)))
    f = bm.faces.new(vs)
    bm.normal_update()
    if f.normal.z < 0:
        f.normal_flip()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    V.set_uv_rect(o, rect, axes=('x', 'y'))
    return o


def build(name):
    V.reset()
    r_in = SPEC["naikeiShaku"] * SHAKU / 2.0
    r_out = r_in + SPEC["kabeAtsuM"]
    sm, srect = stone_mat()
    srect = VM.sub(srect, 0.05, 0.05, 0.95, 0.95)
    stones = [ring(name + "_izutsu", r_in, r_out, -G["depth"], G["top"], sm, srect),
              disc(name + "_soko", r_in + 0.01, -G["depth"] + 0.05, sm, VM.sub(srect, 0.2, 0.2, 0.6, 0.6))]
    ms, uv = SH.mats()
    M = VM.Mesh()
    w = SPEC["igetaMitsukeM"]
    half_in = SPEC["igetaShaku"] * SHAKU / 2.0          # 井桁の内法の半分
    c = half_in + w / 2.0                                # 材の芯
    L = half_in + w + G["koguchi"]                       # 材の半長(木口の出まで)
    for k in range(SPEC["igetaDanN"]):
        h0, h1 = G["top"] + k * w, G["top"] + (k + 1) * w
        for sg in (-1, 1):
            if k % 2 == 0:          # X へ走る 2 本
                SH.box3(M, -L, L, sg * c - w / 2, sg * c + w / 2, h0, h1, uv["wood_h"], SH.W, grain="u")
            else:                   # Z へ走る 2 本
                SH.box3(M, sg * c - w / 2, sg * c + w / 2, -L, L, h0, h1, uv["wood_h"], SH.W, grain="v")
    body = M.to_object(name + "_igeta", ms)
    V.dedup_materials()
    o = V.join([body] + stones, name)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, dict(r_in=r_in, r_out=r_out, half_in=half_in, L=L)


def report(o, info):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    print("IDO %s Unity W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d mats=%s"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), min(xs), max(xs), min(ys), max(ys),
             min(zs), max(zs), tris, mats))
    idx = {i for i, m in enumerate(o.data.materials) if m and m.name.split('.')[0] == "wood"}
    wv = set()
    for pg in o.data.polygons:
        if pg.material_index in idx:
            wv.update(pg.vertices)
    W = [U[i] for i in wv]
    inner = min(abs(t[2]) for t in W if t[1] < G["top"] + SPEC["igetaMitsukeM"] + 1e-4)   # 1 段目は X へ走る ⇒ 内面は |Z|
    sv = [U[i] for i in range(len(U)) if i not in wv and abs(U[i][1] - G["top"]) < 1e-4]
    rr = [math.hypot(t[0], t[2]) for t in sv]
    print("  井筒 内径 %.3f(3尺 %.3f)/ 外径 %.3f / 天端 %.3f / 根入れ %.2f"
          % (2 * min(rr), SPEC["naikeiShaku"] * SHAKU, 2 * max(rr), G["top"], -G["depth"]))
    print("  井桁 内法 %.3f(3尺 %.3f)/ 天端 %.3f / 木口の端 ±%.3f"
          % (2 * inner, SPEC["igetaShaku"] * SHAKU, max(t[1] for t in W), max(abs(t[0]) for t in W)))
    bad = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bad else "⛔ %s" % bad))
    return not bad, tris


def shots(o):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0.0))
    pl = bpy.context.view_layer.objects.active
    bm = bmesh.new(); bm.from_mesh(pl.data)             # 井戸の穴を地面から抜く
    bmesh.ops.delete(bm, geom=[f for f in bm.faces], context='FACES')
    bm.free()
    bpy.data.objects.remove(pl, do_unlink=True)
    out = []

    def one(cam, look, fn, ortho=None, res=(1400, 1000)):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_ido_%s.png" % fn)
        V.render(f); out.append(f)
    one((-2.6, -2.0, 1.5), (0.0, 0.0, 0.1), "oblique")
    one((0.0, -0.01, 4.0), (0.0, 0.0, 0.0), "top", ortho=2.2, res=(1000, 1000))
    one((-3.5, 0.0, 0.35), (0.0, 0.0, 0.25), "elev", ortho=1.8, res=(1400, 900))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    naikei = int(round(SPEC["naikeiShaku"] * SHAKU * 1000.0))
    hgt = int(round(SPEC["igetaMitsukeM"] * SPEC["igetaDanN"] * 1000.0))
    name = "Sanno_Ido_Igeta_%dx%d" % (naikei, hgt)
    o, info = build(name)
    ok, tris = report(o, info)
    if not ok:
        raise SystemExit("[ido] ⛔ 想定外の材")
    if "--render" in argv:
        for f in shots(o):
            print("RENDER " + f)
    if "--no-export" not in argv:
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)
        print("[ido] 書き出し %s (tris %d)" % (path, tris))


if __name__ == "__main__":
    main()
