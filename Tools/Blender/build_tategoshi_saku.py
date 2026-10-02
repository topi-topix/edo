"""**竪格子の柵 1間** — 町木戸の袖(竪格子の固定柵)を 1スパンの駒にした物(EDO-0503)。

    blender --background --python Tools/Blender/build_tategoshi_saku.py -- [--h 2.12] [--render]
    blender --background --python Tools/Blender/build_tategoshi_saku.py -- --h 1.82 [--render]

【用途】町屋の表店の列の端に残った空き(店の妻と隣の塀の間 1〜3m)を閉じる仕切り。
  施主「この門前町の入り口の区切りで使ってるような仕切りのイメージ」= 町木戸の袖の竪格子。
【意匠】⛔ ここに書かない。**`build_machikido.py` の袖の部品(sode_post / sode_kasagi / sode_jifuku /
  sode_koshi / sode_uvs)をそのまま呼ぶ** — 竪子のピッチ・見付・見込、地覆・笠木の断面、柱の根入れ 0.26、
  材の UV 矩形が町木戸と一つ。袖の意匠を直すなら build_machikido.py の方を直し、両方を焼き直す。
  柱は町木戸の端柱と同じ 5寸角(EP 0.150)。駒の柱は run の途中では中柱を兼ねる(太さを揃えて端と中を見分けない)。

【駒】(Unity 局所: 幅 = X 走り / 高さ = Y / 厚み = Z・+Z = 見え面 = 通り側・格子は表裏対称)
  ・`TategoshiSaku_<h>` … 1スパン = 1間 1.818。ピボット = **スパンの中心・地盤レベル**。
      柱は **−X 端**(柱の外の面が x = −0.909)・地覆と笠木は −0.909..+0.909 を通す。
      ⇒ **bbox の X がちょうど 1.818**。重ねずに 1.818 ちょうどのピッチで突き付ける(重ねると笠木が z-fighting)。
      竪子は柱の面から +X 端までを等分(11本・芯々 0.152)。端の空きは両端とも半ピッチなので継ぎ目を跨いで間隔が通る。
  ・`TategoshiSakuPost_<h>` … run の **+X 端を受ける端柱 1本**(笠木つき)。
      ピボット = **柱の +X 面・地盤レベル**(柱は x ∈ [−0.150, 0])。⛔ 足さないと最後の格子が宙で終わる。
  ・丈 h = 笠木の天端(既定 2.12 = 7尺 = 町木戸の袖)。柱は掘立で **0.26 埋める**(底 y = −0.26)。
      ⛔ `SeatBottom` で据えない(根入れぶん浮く)— y = 0 を地盤に合わせる。
  ⚠ VM.Mesh の走り x は Unity X の逆(Unity X = −x)。ここでは Unity の値で考え `U()` で写す。

【材】`wood`(Village Kit)。⛔ 新規マテリアルを作らない。出力 `Assets/Edo/Models/Hei/`
  ⇒ remap は **Edo ▸ 山王社 ▸ 新造部材のマテリアルをremap**(`Models/Hei` を見ている・借り先に Village Kit/Materials)。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_obi_nagaya as N
import build_machikido as MK         # 袖の意匠の正典

OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")
if os.environ.get("BUZAI_SPEC_OUT"):
    V.SPEC_DIR = os.environ["BUZAI_SPEC_OUT"]

KEN  = MK.KEN          # 1.818
POST = MK.EP           # 柱 5寸角(町木戸の端柱)
WOOD = MK.WOOD


def U(a, b):
    """Unity 局所 X の区間 [a, b] → VM.Mesh の走り x の区間"""
    return (-b, -a)


def fmt(h):
    return "%.2f" % h


def _finish(m, name, P):
    o = m.to_object(name, [P['wood'], P['wall'], P['stone']])
    V.sel([o])
    bpy.ops.object.material_slot_remove_unused()
    V.dedup_materials()
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


def grid_xs(h):
    """竪子の芯(Unity X)— build_machikido.sode_koshi → VM.Mesh.koshi と同じ割り"""
    a, b = -KEN / 2 + POST, KEN / 2
    n = max(2, int((b - a) / MK.SODE_PITCH))
    return [a + (b - a) * (i + 0.5) / n for i in range(n)]


def saku(h=MK.SODE_TOP):
    name = "TategoshiSaku_" + fmt(h)
    P = N.palette()
    SU = MK.sode_uvs(P['wuv'])
    m = VM.Mesh()
    ky0 = h - MK.SODE_KASA[0]
    x0 = -KEN / 2                     # 柱の外の面
    xi = x0 + POST                    # 柱の内の面
    x1 = KEN / 2
    MK.sode_post(m, *U(x0, xi), ky0, POST, SU)
    MK.sode_kasagi(m, *U(x0, x1), h, SU)
    MK.sode_jifuku(m, *U(xi, x1), SU)
    MK.sode_koshi(m, *U(xi, x1), ky0, SU)
    o = _finish(m, name, P)
    xs = grid_xs(h)
    print("[tategoshi] %s 1スパン %.3f / 丈 %.2f / 根入れ %.2f / 柱 %.3f角 / 竪子 %d本 芯々 %.4f / 端の空き %.4f"
          % (name, KEN, h, MK.NEIRE, POST, len(xs), xs[1] - xs[0], xs[0] - xi - MK.SODE_BAR))
    return o, name, saku_spec(name, h)


def post(h=MK.SODE_TOP):
    name = "TategoshiSakuPost_" + fmt(h)
    P = N.palette()
    SU = MK.sode_uvs(P['wuv'])
    m = VM.Mesh()
    ky0 = h - MK.SODE_KASA[0]
    MK.sode_post(m, *U(-POST, 0.0), ky0, POST, SU)
    MK.sode_kasagi(m, *U(-POST, 0.0), h, SU)
    o = _finish(m, name, P)
    print("[tategoshi] %s 端柱 %.3f角 / 丈 %.2f / 根入れ %.2f" % (name, POST, h, MK.NEIRE))
    return o, name, post_spec(name, h)


# ---------------------------------------------------------------- 札(作図の変数から・メッシュを測らない)
def _fence_spec(name, h, x0, x1, body_x0, body_x1, src):
    hz = max(POST / 2, MK.SODE_KASA[1])
    foot = [{"x": x0 if px < 0 else x1, "y": pz} for (px, pz) in ((-1, -POST / 2), (1, -POST / 2),
                                                                 (1, POST / 2), (-1, POST / 2))]
    return {
        "prefab": "Assets/Edo/Models/Hei/%s.fbx" % name,
        "kind": "fence", "source": src, "unitScale": 1.0,
        "yBottom": -MK.NEIRE, "foot": foot,
        "eave": {"x0": x0, "x1": x1, "z0": -hz, "z1": hz, "y0": -MK.NEIRE, "y1": h},
        # 外・内の面 = 足元(地際)の柱の面。地覆(±0.06)と竪子(±0.022)はこの内に納まる
        "faceOut": POST / 2, "faceIn": -POST / 2,
        # 笠木の出 = 丈の半ばの断面(柱と竪子)の端から外形の端まで(EdoPartSpec.Measure と同じ定義)
        "copingOverhang": max(0.0, body_x0 - x0, x1 - body_x1),
        "height": h + MK.NEIRE,
    }


def saku_spec(name, h):
    xs = grid_xs(h)
    src = ("blender:build_tategoshi_saku.py saku(h=%g, ken=%g, post=%g, neire=%g, pitch=%g, bar=%g)"
           " ── 袖の意匠は build_machikido.sode_*" % (h, KEN, POST, MK.NEIRE, MK.SODE_PITCH, MK.SODE_BAR))
    # 地際の足元は柱だけだが、走りは駒の全長で持つ(地覆が y 0..0.12 で全長に通る)
    d = _fence_spec(name, h, -KEN / 2, KEN / 2, -KEN / 2, xs[-1] + MK.SODE_BAR, src)
    d["foot"] = [{"x": -KEN / 2, "y": -POST / 2}, {"x": -KEN / 2 + POST, "y": -POST / 2},
                 {"x": -KEN / 2 + POST, "y": POST / 2}, {"x": -KEN / 2, "y": POST / 2}]
    return d


def post_spec(name, h):
    src = ("blender:build_tategoshi_saku.py post(h=%g, post=%g, neire=%g) ── 袖の意匠は build_machikido.sode_*"
           % (h, POST, MK.NEIRE))
    return _fence_spec(name, h, -POST, 0.0, -POST, 0.0, src)


# ---------------------------------------------------------------- 検め画像
def _dup(o, dx):
    c = o.copy(); c.data = o.data.copy()
    bpy.context.collection.objects.link(c)
    c.location.x += dx
    return c


def _magenta():
    w = bpy.context.scene.world
    w.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 0.0, 1.0, 1)


def shots(o, p, h):
    """① 1駒の正面(マゼンタ・透け)② 3駒+端柱の run の正面・斜め・裏 ③ 町木戸の袖と並べ比べ"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    key = fmt(h)
    p.hide_render = True                         # 元の端柱は原点に居る(駒の中に重なる)— 写しだけ写す
    # ① 1駒
    mn, mx = V.bbox([o]); c = (mn + mx) * 0.5
    V.studio((c.x, mn.y - 8.0, c.z), (c.x, c.y, c.z), ortho_scale=(mx.z - mn.z) * 1.15, res=(1100, 1300))
    _magenta()
    V.render(os.path.join(SHOT, "tategoshi_%s_elev1.png" % key))
    # ② run: Unity X で −0.909 → 3間 + 端柱。Blender x = −Unity X ⇒ 駒は −x 方向へ並ぶ
    run = [_dup(o, -KEN * i) for i in (1, 2)]
    pe = _dup(p, -(KEN * 2.5 + POST))            # 端柱の −X 面を run の終端(Unity X = 2.5間)へ突き付ける
    pe.hide_render = False                       # ⚠ 写しは hide_render を継ぐ
    allo = [o] + run + [pe]
    mn, mx = V.bbox(allo); c = (mn + mx) * 0.5; W = mx.x - mn.x
    V.studio((c.x, mn.y - 20.0, c.z), (c.x, c.y, c.z), ortho_scale=W * 1.08, res=(1800, 800))
    _magenta()
    V.render(os.path.join(SHOT, "tategoshi_%s_run_elev.png" % key))
    V.studio((mx.x + 1.5, mn.y - 4.5, 1.6), (c.x, c.y, 1.0), res=(1800, 1100))
    V.render(os.path.join(SHOT, "tategoshi_%s_run_3d.png" % key))
    V.studio((mn.x - 1.5, mx.y + 4.5, 1.6), (c.x, c.y, 1.0), res=(1800, 1100))
    V.render(os.path.join(SHOT, "tategoshi_%s_run_ura.png" % key))
    # 継ぎ目と端柱の寄り
    V.studio((mn.x + 0.6, mn.y - 2.2, 0.9), (mn.x + 0.4, 0.0, 0.8), res=(1200, 1100))
    V.render(os.path.join(SHOT, "tategoshi_%s_hashi.png" % key))
    # ③ 町木戸(10.54)の袖と並べる(左 = 町木戸の −側の袖・右 = 新造の run)
    k, _nm = MK.build(10.54, "L", True)
    kmn, kmx = V.bbox([k])
    k.location.x += (mx.x + 0.8) - kmn.x
    bpy.context.view_layer.update()
    mn2, mx2 = V.bbox(allo + [k])
    tx0, tx1 = mn2.x, mx.x + 0.8 + 4.0           # 町木戸は袖の 1本ぶん(端柱から 4m)だけ入れる
    cx = (tx0 + tx1) / 2
    V.studio((cx, mn2.y - 30.0, 1.4), (cx, 0.0, 1.4), ortho_scale=(tx1 - tx0) * 1.04, res=(2000, 700))
    _magenta()
    V.render(os.path.join(SHOT, "tategoshi_%s_narabe.png" % key))
    for x in run + [pe, k]:
        bpy.data.objects.remove(x, do_unlink=True)
    p.hide_render = False


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    h = float(argv[argv.index("--h") + 1]) if "--h" in argv else MK.SODE_TOP
    V.reset()
    o, name, spec = saku(h)
    p, pname, pspec = post(h)
    p.location.x += 5.0                          # レンダ・測りで重ならないよう(書き出し前に戻す)
    bpy.context.view_layer.update()
    for ob, sp in ((o, spec), (p, pspec)):
        mn, mx = V.bbox([ob])
        print("[tategoshi] %s Unity実寸 W(X)=%.4f  H(Y)=%.4f  D(Z)=%.4f  底=%.3f  Unity X %.4f..%.4f  面=%d  材=%s"
              % (ob.name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z,
                 -(mx.x - ob.location.x), -(mn.x - ob.location.x), len(ob.data.polygons),
                 [mm.name for mm in ob.data.materials]))
    if "--render" in argv:
        p.location.x -= 5.0
        bpy.context.view_layer.update()
        shots(o, p, h)
        p.location.x += 5.0
    p.location.x -= 5.0
    bpy.context.view_layer.update()
    for ob, nm, sp in ((o, name, spec), (p, pname, pspec)):
        path = os.path.join(OUT, nm + ".fbx")
        V.export_fbx([ob], path, kind="fence", spec=sp)
        print("[tategoshi] 書き出し " + path)


if __name__ == "__main__":
    main()
