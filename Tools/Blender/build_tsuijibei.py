"""武家屋敷の築地塀 — キットの城塀から軒を詰めて小口を塞いだ派生を起こす。

    blender --background --python Tools/Blender/build_tsuijibei.py -- [--eave 0.30] [--render]

【なぜ派生が要るか】在庫の `Japanese Castle/.../Wall Exterior Defence` は彫りもPBRも
  申し分ないが、**城の塀**の比率で作られている(実測 2026-08-16):
      躯体 0.80 ／ 軒の総幅 2.10 ／ 軒の出 片側 0.65 = 躯体の 0.81倍
  軒が躯体の **2.63倍** も張り出す。城の石垣を雨から守る形で、武家屋敷の築地塀としては
  深すぎる(実物の築地塀は軒の出が躯体と同程度)。横から見ると躯体が板に見える。
  さらに **小口(X両端の面)が1枚も無い** ため、run の端で中が抜けて見える
  (ユーザー指摘 2026-08-16「表裏で重ねて使っていて、横から見ると中身がなくなってる」)。
  → 表裏の面は揃っている(−Z 42面 / +Z 42面)ので、2枚重ねではない。抜けるのは端だけ。

【方針】**ゼロから作らない。** 自前の瓦は「ダサい」と却下されている(2026-08-16)。
  キットのメッシュをそのまま取り込み、
    ① 躯体より外の頂点だけ Z を圧縮して軒を詰める(瓦の彫りは保つ。丸瓦は
       流れ方向=Z に走っているので、詰めると瓦が「短く」なるだけで太らない)
    ② 躯体の小口を塞ぐ
  マテリアルはキットのまま3つ(`Wall Exterior Defence` / `Roof Castle A` / `Roof Details`)。

【寸法】Unity ローカル: 走り X ∈ [-1, 1](2m モジュール) ／ 高さ Y 0..2.57 ／ 厚み Z。
  ⚠ Blender に取り込むと **Y と Z が入れ替わる**(FBX は Y-up、Blender は Z-up)。
     スクリプト内では **厚み = Blender Y ／ 高さ = Blender Z**。
     ここを取り違えて高さのほうを圧縮し、全高 2.57 が 1.60 に潰れた(2026-08-16)。
  ピボットは走りの中央・足元。**Unity 側は素の prefab と同じ置き方で差し替えられる。**
"""
import bpy, bmesh, sys, os
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ROOT = V.REPO
JC = os.path.join(ROOT, "Assets/Japanese Castle")
SRC = "Exterior/Wall Exterior Defence.fbx"
OUT = os.path.join(ROOT, "Assets/Edo/Models/Tsuijibei")

Z_WALL = 0.40        # 躯体の半厚(実測)。ここまでは触らない
EAVE_TGT = 0.0       # 0 = 軒に触らない(既定)。>0 で圧縮を試みる
# ⚠ 軒の圧縮は**破綻する**。屋根は瓦・垂木・破風が別部材で噛み合っており、
#   厚み方向に部分的な倍率をかけると相対位置が崩れて互いに貫通する
#   (2026-08-16、0.30 に詰めたら軒が原型を留めなかった)。
#   キットの軒の比率(躯体 0.80 に対し軒 2.10)は据え置くのが安全。
WALL_MAT = "Wall Exterior Defence"


def shrink_eave(o, eave_tgt):
    """躯体より外(|厚み| > Z_WALL)の頂点だけ厚み方向を圧縮する。躯体はそのまま。
    厚み = Blender Y"""
    me = o.data
    tmax = max(abs(v.co.y) for v in me.vertices)
    cur = tmax - Z_WALL
    if cur <= 1e-6:
        return 1.0
    k = eave_tgt / cur
    for v in me.vertices:
        t = v.co.y
        if abs(t) > Z_WALL:
            s = 1.0 if t > 0 else -1.0
            v.co.y = s * (Z_WALL + (abs(t) - Z_WALL) * k)
    me.update()
    return k


def wall_top(o):
    """躯体がどこまで立ち上がっているか = 厚みが Z_WALL を超えない頂点の最大の高さ。
    ⚠ 「|厚み| ≈ Z_WALL の頂点」で探すと、素のメッシュは足元の4点しか該当せず 0.00 が返る
       (躯体は足元 ±0.40 から軒へ向かって広がる断面をしている)。"""
    # 軒がどこから始まるか = 厚みが Z_WALL を超える頂点の最低の高さ。そこまでを躯体とする
    zs = [v.co.z for v in o.data.vertices if abs(v.co.y) > Z_WALL + 0.01]
    return min(zs) if zs else 1.6


def wall_face_uv(o):
    """躯体の側面(法線 ±Y)の最大面から、u の幅と **高さ→v の対応** を取り出す。
    戻り値 (u0, u1, z0, v0, z1, v1)。
    ⚠ 小口を UV 1点で貼るとアトラスの無地(白)を踏んで**真っ白な板**になる。
    ⚠ 矩形の v をそのまま伸ばして貼ると、漆喰の**雨だれの帯が隣の壁面と揃わず**、
       上端に灰色の模様が出て貼り付けたのがバレる(2026-08-16 に指摘された)。
       **同じ高さには同じ v** が来るよう、高さから v を引くこと。"""
    me = o.data
    uvl = me.uv_layers.active.data
    best, ba = None, -1.0
    for p in me.polygons:
        if p.material_index != 0 or abs(p.normal.y) < 0.9:
            continue
        if p.area > ba:
            ba, best = p.area, p
    if best is None:
        return (0.0, 0.2, 0.0, 0.0, 1.0, 1.0)
    pts = [(me.vertices[me.loops[li].vertex_index].co.z, uvl[li].uv[1]) for li in best.loop_indices]
    us = [uvl[li].uv[0] for li in best.loop_indices]
    lo = min(pts, key=lambda q: q[0])
    hi = max(pts, key=lambda q: q[0])
    return (min(us), max(us), lo[0], lo[1], hi[0], hi[1])


def cap_ends(o, y_top, u0, u1, z0, v0, z1, v1):
    """躯体の小口(X 両端)を塞ぐ。run の端で中が抜けるのを止める。
    u は厚み 0.8m ぶんに切り詰め、v は**高さから引く**ので雨だれが隣の壁面と揃う"""
    def v_at(z):
        if abs(z1 - z0) < 1e-6:
            return v0
        return v0 + (v1 - v0) * (z - z0) / (z1 - z0)
    du = (u1 - u0) * (Z_WALL * 2.0) / 2.0          # モジュール長 2m に対する厚み 0.8m の比
    me = o.data
    xmin = min(v.co.x for v in me.vertices)
    xmax = max(v.co.x for v in me.vertices)
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new("UVMap")
    for x, flip in ((xmin, True), (xmax, False)):
        pts = [(x, -Z_WALL, 0.0), (x, Z_WALL, 0.0), (x, Z_WALL, y_top), (x, -Z_WALL, y_top)]
        vb, vt = v_at(0.0), v_at(y_top)
        uvs = [(u0, vb), (u0 + du, vb), (u0 + du, vt), (u0, vt)]
        if flip:
            pts, uvs = pts[::-1], uvs[::-1]
        vs = [bm.verts.new(Vector(p)) for p in pts]
        f = bm.faces.new(vs)
        f.material_index = 0
        for lp, uv in zip(f.loops, uvs):
            lp[uvl].uv = uv
    bm.to_mesh(me); bm.free(); me.update()
    return xmin, xmax


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    eave = EAVE_TGT
    if "--eave" in argv:
        eave = float(argv[argv.index("--eave") + 1])
    do_render = "--render" in argv

    V.reset()
    V.MESH = os.path.join(JC, "Meshes")
    V.TEX = os.path.join(JC, "Textures")
    objs = V.imp(SRC)
    o = V.join(objs, "Tsuijibei2m")
    # 躯体マテリアルが index 0 に来るよう並べ替える(小口をそこへ張る)
    names = [m.name if m else "" for m in o.data.materials]
    if WALL_MAT in names and names.index(WALL_MAT) != 0:
        i = names.index(WALL_MAT)
        for p in o.data.polygons:
            if p.material_index == 0:
                p.material_index = i
            elif p.material_index == i:
                p.material_index = 0
        o.data.materials[0], o.data.materials[i] = o.data.materials[i], o.data.materials[0]

    k = shrink_eave(o, eave) if eave > 0.0 else 1.0
    yt = wall_top(o)
    cap_ends(o, yt, *wall_face_uv(o))

    zmax = max(abs(v.co.y) for v in o.data.vertices)   # 厚みの片側
    ymax = max(v.co.z for v in o.data.vertices)        # 全高
    print("[tsuiji] 軒の圧縮 k=%.3f  躯体 %.2f  軒の総幅 %.2f  全高 %.2f  躯体の立上り %.2f"
          % (k, Z_WALL * 2, zmax * 2, ymax, yt))
    print("[tsuiji] 軒の出 片側 %.2f = 躯体の %.2f倍" % (zmax - Z_WALL, (zmax - Z_WALL) / (Z_WALL * 2)))
    print("[tsuiji] 軒は %s" % ("圧縮した(k=%.3f)" % k if eave > 0 else "素のまま"))

    path = os.path.join(OUT, "Tsuijibei2m.fbx")
    V.export_fbx([o], path)
    print("[tsuiji] wrote %s" % path)

    if do_render:
        V.hook_textures()
        V.studio((3.6, -3.0, 2.2), (0.0, 0.0, 1.15), res=(1400, 900))
        V.render(os.path.join(ROOT, "Screenshots", "tsuiji_persp.png"))
        V.studio((-3.4, 0.0, 1.5), (0.0, 0.0, 1.20), res=(1300, 950))
        V.render(os.path.join(ROOT, "Screenshots", "tsuiji_end.png"))
        V.studio((1.7, -1.5, 2.75), (0.0, 0.0, 2.05), res=(1400, 950))
        V.render(os.path.join(ROOT, "Screenshots", "tsuiji_eave.png"))
        V.studio((-2.0, -0.9, 1.95), (-0.95, 0.0, 1.45), res=(1400, 950))
        V.render(os.path.join(ROOT, "Screenshots", "tsuiji_cap.png"))


main()
