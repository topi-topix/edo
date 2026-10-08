"""**木の平橋** — 岡部筑前守上屋敷 書院の泉水の橋(EDO-0502・庭方の設計 2026-10-08)。

    blender --background --python Tools/Blender/build_okabe_hashi.py -- --render
    blender --background --python Tools/Blender/build_okabe_hashi.py -- --L 8.0 --W 1.82 --render

【寸法の正典は `docs/Sashizu/okabe_sashizu.json`】⛔ ここで値を発明しない。
  ・`gardens[NiwaShoin].hosoku.hashi.asset` … 木の平橋 幅1.82・2径間・中央に丸太の橋脚1組・
     桁3本・反り無し・**L=8.0 で起こし長軸 ±6%**(据える側が実測の袂の間へ X だけ伸縮する)
  ・`gardens[NiwaShoin].hashi[0]` … from (-12.8,80.2) → to (-16.0,81.6)・
     `deckY = waterY+0.35 = 21.05`・池底 `migiwa.floorY = 19.8`(水面 20.7)

【在庫】在庫に木の平橋は無い(`Own.Ishibashi` = 切石 2.2m / `DoiIshibashi` = 切石 3.4m /
  `DoiDobashi` = 土橋 3.4m)。⇒ **在庫の材を組み直す**(規則1):
  ・桁・橋脚・梁・台木 … NatureManufacture の丸太 `wood_log_0X`(`build_maruta.log_piece`)・材 `M_Wood_fence`
  ・敷板・地覆 … Village Kit の `wood`(アトラスの木理の矩形 `WOOD_UV` を面ごとに貼る・一点貼りしない)

【部材方の既定値(指図に無い・確度 U)】板厚 0.045・板幅 ≈0.30・地覆 0.10×0.09・桁 φ0.16・
  梁 φ0.14・橋脚 φ0.20・橋脚の根入れ 0.40(池底の下)。
  ⚠ 橋面が水面の 0.35 上しか無いので、桁の下端 −0.205・梁の下端 −0.345 = **水面すれすれ**
    (梁は水に触れる程度。これより太くすると梁が水に沈む)。

【向きとピボット(Unity 座標)】長手 = X(from→to)・高さ = Y・幅 = Z(左右対称)。
  **ピボット = 橋面の平面の中心・敷板の天端**(⇒ `position.y = deckY` 21.05 を直に)。
  橋脚は Y −1.65 まで垂れる(池底 19.8 = Y −1.25 の下へ 0.40 根入れ)。
  桁の両端は X ±4.00 で切ってあり、袂の地盤(21.0)へ 0.05〜0.25 埋まる前提。
  ±6% の伸縮は **scale.x だけ**(Y・Z は 1)。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_maruta as BM
import build_okabe_niwa as ON
import build_doi_niwa as DN

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa"))
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD = "wood"
WOOD_UV = (0.600, 0.03, 0.770, 0.97)      # build_goten_roof と同じ木理(v = 木目の流れ)

# ---- 指図の値 ----
L_DEF, W_DEF = 8.0, 1.82
DECK_ABOVE_FLOOR = 21.05 - 19.8           # 橋面 − 池底 = 1.25
WATER_BELOW_DECK = 21.05 - 20.7           # 0.35

# ---- 部材方の既定値(U) ----
PLANK_T, PLANK_W, GAP = 0.045, 0.30, 0.004
JIFUKU_H, JIFUKU_W = 0.09, 0.10
KETA_D, HARI_D, KYAKU_D = 0.16, 0.14, 0.20
NEIRE = 0.40
KETA_Y = (-0.62, 0.0, 0.62)               # 桁3本(Blender y)
KYAKU_Y = 0.70                            # 橋脚の芯 ±


def wood_box(name, sx, sy, sz, c, rng):
    """角材・板。面ごとに法線に直交する2軸で投影し、**部材の長手を v(木目)へ**流す。
    矩形は WOOD_UV の中から部材ごとに少しずらして採る(板が全部同じ木目に見えないように)。"""
    o = V.box(name, (sx, sy, sz), c, mat=V.named_material(WOOD))
    me = o.data
    dims = (sx, sy, sz)
    long_ax = max(range(3), key=lambda k: dims[k])
    u0, v0, u1, v1 = WOOD_UV
    du = (u1 - u0) * 0.35
    ou = rng.uniform(0.0, (u1 - u0) - du)
    ov = rng.uniform(0.0, 0.4)
    uvl = me.uv_layers.new(name="UVMap").data
    for p in me.polygons:
        n = p.normal
        nax = max(range(3), key=lambda k: abs(n[k]))
        axes = [k for k in range(3) if k != nax]
        la = long_ax if long_ax in axes else axes[0]
        sa = [k for k in axes if k != la][0]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            fs = (co[sa] - (c[sa] - dims[sa] / 2)) / max(dims[sa], 1e-6)
            fl = (co[la] - (c[la] - dims[la] / 2))
            uvl[li].uv = (u0 + ou + du * fs, v0 + ov * (v1 - v0) + fl * 0.11)
    return o


def stretch_log(stem, L, dia, name, frm=0.0, src_len=3.0):
    """在庫の丸太は最長 3.18m。src_len を切り出し長手だけ L へ伸ばす(桁は橋の下で陰になる)。"""
    o = BM.log_piece(stem, min(src_len, L), dia, name, frm=frm)
    k = L / min(src_len, L)
    for v in o.data.vertices:
        v.co.x *= k
    o.data.update()
    return o


def hashi(L, W):
    rng = random.Random(50202)
    half, hw = L / 2.0, W / 2.0
    objs = []
    # ---- 敷板(幅方向に渡す・木目は Blender y)
    n = max(1, round(L / PLANK_W))
    pw = L / n
    for i in range(n):
        x = -half + pw * (i + 0.5)
        t = PLANK_T * rng.uniform(0.97, 1.0)
        objs.append(wood_box("ita%02d" % i, pw - GAP, W, t, (x, 0.0, -t / 2.0), rng))
    # ---- 地覆(両縁・板の上に載る低い角材)
    for s in (-1, 1):
        objs.append(wood_box("jifuku%d" % s, L, JIFUKU_W, JIFUKU_H,
                             (0.0, s * (hw - JIFUKU_W / 2.0), JIFUKU_H / 2.0), rng))
    # ---- 桁 3本 × 2径間(中央の梁の上で突き付け)
    zk = -PLANK_T - KETA_D / 2.0 + 0.012      # 丸太は真円でない。板の下へ 12mm 食い込ませて隙を消す
    for j, y in enumerate(KETA_Y):
        for s in (-1, 1):
            g = stretch_log(("wood_log_01", "wood_log_02")[(j + (s > 0)) % 2], half, KETA_D,
                            "keta%d%d" % (j, s), frm=0.05 + 0.03 * j)
            g.data.transform(Matrix.Translation((s * half / 2.0, y, zk)))
            g.data.update()
            objs.append(g)
    # ---- 梁(橋脚の頭・桁を受ける横木)
    zh = zk - KETA_D / 2.0 - HARI_D / 2.0 + 0.01
    hari = BM.log_piece("wood_log_02", 2 * KYAKU_Y + 0.40, HARI_D, "hari", frm=0.6)
    hari.data.transform(Matrix.Translation((0.0, 0.0, zh)) @ Matrix.Rotation(math.radians(90), 4, 'Z'))
    hari.data.update()
    objs.append(hari)
    # ---- 橋脚 1組(梁の芯から池底の下 NEIRE まで)
    zbot = -DECK_ABOVE_FLOOR - NEIRE
    for k, s in enumerate((-1, 1)):
        p = BM.upright(BM.log_piece("wood_log_04", zh - zbot, KYAKU_D, "kyaku%d" % k,
                                    frm=0.15 + 0.4 * k), top_at_zero=True)
        p.data.transform(Matrix.Translation((0.0, s * KYAKU_Y, zh)))
        p.data.update()
        objs.append(p)
    # ---- 袂の台木(桁の端を受ける・岸に埋まる)
    for s in (-1, 1):
        sill = BM.log_piece("wood_log_04", W + 0.10, HARI_D, "dai%d" % s, frm=0.05 if s < 0 else 0.25)
        sill.data.transform(Matrix.Translation((s * (half - 0.30), 0.0, zh))
                            @ Matrix.Rotation(math.radians(90), 4, 'Z'))
        sill.data.update()
        objs.append(sill)
    name = "Okabe_Hashi_Ita_L%.2f_W%.2f" % (L, W)
    return DN._finish(objs, name), name


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    L = float(argv[argv.index("--L") + 1]) if "--L" in argv else L_DEF
    W = float(argv[argv.index("--W") + 1]) if "--W" in argv else W_DEF
    V.reset()
    o, name = hashi(L, W)
    mn, mx = BM.bounds([o])
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    print("[hashi] %s Unity実寸 X=%.3f Y=%.3f(%.3f..%.3f) Z=%.3f tri=%d 材=%s"
          % (name, mx.x - mn.x, mx.z - mn.z, mn.z, mx.z, mx.y - mn.y, tris,
             [m.name for m in o.data.materials]))
    if "--render" in argv:
        DN.hook()
        os.makedirs(SHOT, exist_ok=True)
        # 水面の目安の板(半透明でなく青灰)を置いて据えた姿を撮る
        bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0, 0, -WATER_BELOW_DECK))
        wp = bpy.context.active_object
        wm = bpy.data.materials.new("_water_render")
        wm.use_nodes = True
        wm.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.20, 0.27, 0.30, 1)
        wp.data.materials.append(wm)
        V.studio((0.0, -14.0, -0.6), (0.0, 0.0, -0.6), ortho_scale=9.0, res=(1600, 700))
        wp.hide_render = True
        V.render(os.path.join(SHOT, "okabe_hashi_elev.png"))
        V.studio((-3.0, 6.0, -0.6), (-3.0, 0.0, -0.6), ortho_scale=3.2, res=(1000, 1000))
        V.render(os.path.join(SHOT, "okabe_hashi_side.png"))
        wp.hide_render = False
        V.studio((-7.0, -6.5, 2.6), (0.0, 0.0, -0.3), res=(1600, 1000))
        V.render(os.path.join(SHOT, "okabe_hashi_3d.png"))
        wp.hide_render = True
        V.studio((2.6, -3.4, -1.2), (0.0, 0.0, -0.5), res=(1600, 1000))
        V.render(os.path.join(SHOT, "okabe_hashi_under.png"))
        wp.hide_render = False
        V.studio((0.0, 1e-4, 12.0), (0.0, 0.0, 0.0), ortho_scale=9.0, res=(1600, 500))
        V.render(os.path.join(SHOT, "okabe_hashi_top.png"))
        bpy.data.objects.remove(wp, do_unlink=True)
    path = os.path.join(OUT, name + ".fbx")
    V.export_fbx([o], path)
    print("[hashi] 書き出し " + path)


if __name__ == "__main__":
    main()
