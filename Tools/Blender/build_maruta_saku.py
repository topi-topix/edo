"""**丸太の二段柵** — 馬場の埒・厩の平場の縁。土井大隅守上屋敷(EDO-0533)。

    blender --background --python Tools/Blender/build_maruta_saku.py -- --h 1.2 [--render]
    (--h は丈[m]。1.2 = F04 馬場の埒 / 1.1 = F05 厩の平場の縁)

【なぜ新造するか】在庫に「丸太の柱に横木二段の柵」は無い(在庫方 2026-10-03)。
  `build_maruta.py`(岡部の丸太の手すり `Own.MarutaTesuri`)と同じく、NatureManufacture の
  **本物の丸太 `wood_log_0X` を切って並べる**。⛔ 円柱を自作しない・四つ目垣/建仁寺垣で代えない。

【寸法は指図 `docs/Sashizu/doi_sashizu.json` の fences[F04]/[F05].part が正典】
  柱 丸太 φ0.12・芯々 1間(1.818)。横木 φ0.07〜0.09 を二段
  (上 φ0.09・下 φ0.08)。横木の芯 = F04 丈1.2 → 0.55/1.00 / F05 丈1.1 → 0.50/0.92
  ⇒ 丈に比例させて **下 = 0.458h・上 = 0.833h**(0.01 丸め)で両方の値に一致する。
  根入れ 0.150(`Own.YotsumeGaki` の作法。柱は Y −0.150 まで伸びる)。

【向きとピボット(Unity 座標)】⚠ Blender x = **−Unity X**、Blender −y = Unity +Z(検算は (-x,z,-y))。
  ・駒 `Maruta_Saku_<h>` … **1スパン**。幅=X(走り)/ 高さ=Y / 厚み=Z。
      ピボット = **スパンの中心・地盤レベル**。柱は **Unity −X 端**(芯 x = −0.909)、
      横木は −0.909..+0.909 で **柱の +Z 側の面に添えて**(結わえた姿)通す。
      ⇒ 1.818 ピッチで並べれば柱が芯々1間に立ち、横木は柱の前で突き付く。
      **run の +X 端には `Maruta_SakuPost_<h>` を1本**(ピボット = 柱の芯・地盤。芯を run の終端へ)。
  ・`+Z` = 見え面(横木の側)。

【材】`M_Wood_fence`(NatureManufacture の丸太の材質名)。⛔ 新規に作らない。
"""
import bpy, sys, os
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_maruta as BM

OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Maruta")
SHOT = os.path.join(V.REPO, "Screenshots")

KEN = 1.818
POST_D = 0.12
RAIL_D_HI, RAIL_D_LO = 0.09, 0.08
NEIRE = 0.150                       # Own.YotsumeGaki と同じ根入れ
EMBED = 0.01                        # 横木を柱の面へ食い込ませる分(結わえ目の隙を消す)


def fmt(h):
    s = ("%.2f" % h).rstrip("0")
    return s + "0" if s.endswith(".") else s


def rails_y(h):
    return round(h * 0.458, 2), round(h * 0.833, 2)


def rail_z(d):
    """横木の芯の Unity Z(柱の +Z の面に添える)"""
    return POST_D * 0.5 + d * 0.5 - EMBED


def _post(h, name):
    """柱1本。芯 = 原点、底 = −NEIRE、頭 = h。"""
    o = BM.upright(BM.log_piece("wood_log_04", h + NEIRE, POST_D, name, frm=0.30),
                   top_at_zero=False)
    o.data.transform(Matrix.Translation((0, 0, -NEIRE)))
    o.data.update()
    return o


def saku(h):
    name = "Maruta_Saku_" + fmt(h)
    post = _post(h, "post")
    post.data.transform(Matrix.Translation((+KEN * 0.5, 0, 0)))   # Blender +x = Unity −X 端
    post.data.update()
    ylo, yhi = rails_y(h)
    parts = [post]
    for stem, frm, d, y in (("wood_log_02", 0.40, RAIL_D_LO, ylo),
                            ("wood_log_01", 1.10, RAIL_D_HI, yhi)):
        r = BM.log_piece(stem, KEN, d, "rail", frm=frm)
        r.data.transform(Matrix.Translation((0, -rail_z(d), y)))  # Blender −y = Unity +Z
        r.data.update()
        parts.append(r)
    V.dedup_materials()
    o = V.join(parts, name)
    zf = max(rail_z(RAIL_D_HI) + RAIL_D_HI * 0.5, rail_z(RAIL_D_LO) + RAIL_D_LO * 0.5)
    pr = POST_D * 0.5
    spec = {
        "source": "blender:build_maruta_saku.py saku(h=%s, ken=1.818, post=0.12, rails=%.2f/%.2f φ%.2f/%.2f, neire=0.15)"
                  % (fmt(h), ylo, yhi, RAIL_D_LO, RAIL_D_HI),
        "yBottom": -NEIRE,
        "foot": [{"x": -KEN / 2 - pr, "y": -pr}, {"x": -KEN / 2 + pr, "y": -pr},
                 {"x": -KEN / 2 + pr, "y": pr}, {"x": -KEN / 2 - pr, "y": pr}],
        "eave": {"x0": -KEN / 2 - pr, "x1": KEN / 2, "z0": -pr, "z1": zf, "y0": -NEIRE, "y1": h},
        "faceOut": zf, "faceIn": -pr, "copingOverhang": 0.0, "height": h + NEIRE,
    }
    return o, name, spec


def post(h):
    name = "Maruta_SakuPost_" + fmt(h)
    o = _post(h, name)
    V.dedup_materials()                 # ⚠ 同じ FBX を再度読むと M_Wood_fence.001 ができる
    o.name = name; o.data.name = name
    pr = POST_D * 0.5
    spec = {
        "source": "blender:build_maruta_saku.py post(h=%s, post=0.12, neire=0.15)" % fmt(h),
        "yBottom": -NEIRE,
        "foot": [{"x": -pr, "y": -pr}, {"x": pr, "y": -pr}, {"x": pr, "y": pr}, {"x": -pr, "y": pr}],
        "eave": {"x0": -pr, "x1": pr, "z0": -pr, "z1": pr, "y0": -NEIRE, "y1": h},
        "faceOut": pr, "faceIn": -pr, "copingOverhang": 0.0, "height": h + NEIRE,
    }
    return o, name, spec


def _dup(o, dx):
    c = o.copy(); c.data = o.data.copy()
    bpy.context.scene.collection.objects.link(c)
    c.location.x += dx
    c.hide_render = False
    return c


def shots(o, p, h):
    BM.hook()
    os.makedirs(SHOT, exist_ok=True)
    key = fmt(h)
    world = bpy.context.scene.world
    # ① 1駒の正面・斜め
    mn, mx = BM.bounds([o]); c = (mn + mx) * 0.5
    V.studio((c.x, mn.y - 8.0, c.z), (c.x, c.y, c.z), ortho_scale=2.4, res=(1300, 1000))
    V.render(os.path.join(SHOT, "marutasaku_%s_elev1.png" % key))
    # ② 4駒 + 端柱の run。Unity +X = Blender −x ⇒ 駒は −x へ並べ、端柱は Unity X = 3.5間 + 0.909
    p.hide_render = True
    run = [_dup(o, -KEN * i) for i in (1, 2, 3)]
    pe = _dup(p, -(KEN * 3.5))
    allo = [o] + run + [pe]
    mn, mx = BM.bounds(allo); c = (mn + mx) * 0.5; W = mx.x - mn.x
    V.studio((c.x, mn.y - 20.0, c.z), (c.x, c.y, c.z), ortho_scale=W * 1.08, res=(1800, 700))
    V.render(os.path.join(SHOT, "marutasaku_%s_run_elev.png" % key))
    V.studio((mn.x - 1.2, mn.y - 4.0, 1.7), (c.x, c.y, 0.6), res=(1800, 1100))
    V.render(os.path.join(SHOT, "marutasaku_%s_run_3d.png" % key))
    V.studio((mx.x + 1.2, mx.y + 4.0, 1.7), (c.x, c.y, 0.6), res=(1800, 1100))
    V.render(os.path.join(SHOT, "marutasaku_%s_run_ura.png" % key))
    # 端柱の寄り(Unity +X 端 = Blender の min x)
    V.studio((mn.x + 0.7, mn.y - 1.8, 1.3), (mn.x + 0.2, 0.0, 0.7), res=(1200, 1100))
    V.render(os.path.join(SHOT, "marutasaku_%s_hashi.png" % key))
    for x in run + [pe]:
        bpy.data.objects.remove(x, do_unlink=True)
    p.hide_render = False


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    h = float(argv[argv.index("--h") + 1]) if "--h" in argv else 1.2
    V.reset()
    o, name, spec = saku(h)
    p, pname, pspec = post(h)
    for ob in (o, p):
        mn, mx = BM.bounds([ob])
        print("[marutasaku] %-22s Unity実寸 W(X)=%.3f H(Y)=%.3f D(Z)=%.3f  Unity X %.3f..%.3f  "
              "Y %.3f..%.3f  Z %.3f..%.3f  面=%d 材=%s"
              % (ob.name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, -mx.x, -mn.x, mn.z, mx.z,
                 -mx.y, -mn.y, len(ob.data.polygons), [m.name for m in ob.data.materials]))
    if "--render" in argv:
        shots(o, p, h)
    for ob, nm, sp in ((o, name, spec), (p, pname, pspec)):
        path = os.path.join(OUT, nm + ".fbx")
        V.export_fbx([ob], path, kind="fence", spec=sp)
        print("[marutasaku] 書き出し " + path)


if __name__ == "__main__":
    main()
