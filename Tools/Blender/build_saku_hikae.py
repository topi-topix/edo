"""**控柱つきの木柵 1間**(松江松平 谷の境の柵 F_Tani_* / F_Okabe_*・EDO-0554)。

    blender --background --python Tools/Blender/build_saku_hikae.py -- [--render]

【用途】指図 `matsudaira_dewa_sashizu.json` fences の 13 run(谷の境・岡部境)。施主の像は「水のそばに木の柵」。
  型 = 「1条の控柱付きの塀」([成瀬・外来診療棟] SA155・加賀/大聖寺の境)。丈 1.4m 前後・基礎なし・地形なり。
  `assetRequests.Saku_Hikae` ── 在庫の汀の木柵 `HoriSaku`(h1.40)には控柱が無いので、**その板柵の意匠をそのまま
  借りて**(`build_hori_saku._post/_rails/_boards/_plank`)屋敷側へ控柱を足した。⛔ 意匠をここで二重に持たない。
  板柵の意匠を直すなら build_hori_saku.py を直し、両方を焼き直す。

【駒】(Unity 局所: 幅 = X 走り / 高さ = Y / 厚み = Z・**+Z = 見え面 = 外(水・隣家の側)**・控柱は −Z = 屋敷側)
  ・`Saku_Hikae` … 1スパン = 1間 1.818。ピボット = **スパンの中心・地盤レベル**。
      杭は **Unity −X 端**(杭の外の面が x = −0.909)。貫・横板は −0.909..+0.909 を通す ⇒ **bbox の X がちょうど 1.818**。
      控柱は杭の真裏(屋敷側)で板の内の面に当たり、−Z へ 0.73 寝て地へ 0.12 埋まる。根元の控貫で板の面へ繋ぐ。
  ・`Saku_Hikae_Mizukoshi` … 水越しの 1間(F_Tani_6 `mizukoshi`「下桟なしで開け、底に石を敷く」)。
      下の横板 2 枚と下の貫を抜き、**地盤 + 0.63m まで素通し**。控柱は付けない(流れの中に立つので)。底の石は据える側。
  ・`Saku_HikaePost` … run の **+X 端を受ける端の杭**(控柱つき)。ピボット = **杭の +X 面・地盤レベル**(杭は x ∈ [−0.11, 0])。
      ⛔ 足さないと最後の板が宙で終わる。
  ・根入れ 0.12(杭・控柱とも底 y = −0.12)。⛔ `SeatBottom` で据えない(根入れぶん浮く)— y = 0 を地盤へ。
  ・重ねずに 1.818 ちょうどのピッチで突き付ける(重ねると板が z-fighting)。

【材】`wood`(Village Kit)だけ。⛔ 新規マテリアルを作らない。出力 `Assets/Edo/Models/Hei/`
  ⇒ remap は `Models/Hei` を見ているもの(HoriSaku と同じ)。
⚠ VM.Mesh の走り x は Unity X の逆(Unity X = −x)。ここでは Unity の値で考え `U()` で写す(tategoshi と同じ)。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_obi_nagaya as N
import build_hori_saku as HS          # 板柵の意匠の正典

OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")
if os.environ.get("BUZAI_SPEC_OUT"):
    V.SPEC_DIR = os.environ["BUZAI_SPEC_OUT"]

KEN, H, ROOT, POST = HS.KEN, HS.H, HS.ROOT, HS.POST
WOOD = HS.WOOD
# ---- 控柱(【U】指図に無い。部材方の決め)----
HB      = 0.09            # 控柱の見付・見込(杭 0.11 より一回り細く)
HK_TOP  = 1.00            # 控柱が板の内の面に当たる高さ
HK_FOOT = 0.73            # 地際で板の面から屋敷側へ出る量(控柱の芯)
HK_Z0   = HS.BACK - HS.LAP_M + 0.005     # 控柱の頭の当たり面(横板の内の面へ 5mm 食い込ませて隙を出さない)
TIE_Y   = (0.27, 0.33)    # 控貫(根元で控柱を板の面へ繋ぐ)
MIZU_OPEN = 2             # 水越しで抜く下の横板の枚数(地盤 + 0.12 + 2×0.256 = 0.632 まで素通し)


def U(x):
    """Unity 局所 X → VM の走り x"""
    return -x


def _axis():
    """控柱の芯の線(Unity の (y, z))。頭 (HK_TOP, HK_Z0) → 地際 (0, HK_Z0 − HK_FOOT)。"""
    d = Vector((0.0, -HK_TOP, -HK_FOOT)).normalized()     # (x, y, z)
    return d


def _quad(m, pts_u, uvs, center_u):
    """Unity 座標の 4 点を VM へ写して積む。向きは部品の芯から外へ(VM 論理で右手系の法線)。"""
    pv = [Vector((U(p[0]), p[1], p[2])) for p in pts_u]
    c = Vector((U(center_u[0]), center_u[1], center_u[2]))
    n = (pv[1] - pv[0]).cross(pv[2] - pv[1])
    fc = sum(pv, Vector()) / 4.0
    if n.dot(fc - c) < 0:
        pv = pv[::-1]; uvs = uvs[::-1]
    m.quad_uvs([tuple(p) for p in pv], uvs, WOOD)


def _hikae(m, P, xc):
    """控柱 1本(見付 HB・芯の線は _axis)+ 根元の控貫。xc = Unity X の芯。
    頭は横板の内の面(z = HK_Z0)で切り、足は y = −ROOT で切る(どちらも芯の線に斜めの面)。"""
    m.group()
    d = _axis()
    en = Vector((0.0, -d.z, d.y))                           # 断面の y-z の向き(芯に直交)
    if en.z > 0:
        en = -en
    ex = Vector((1.0, 0.0, 0.0))
    A = Vector((xc, HK_TOP, HK_Z0))
    corners = []
    for sx, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        o = A + ex * (sx * HB / 2) + en * (sn * HB / 2)
        # 頭: z = HK_Z0 の面との交点 / 足: y = −ROOT の面との交点
        tt = (HK_Z0 - o.z) / d.z
        tb = (-ROOT - o.y) / d.y
        corners.append((o + d * tt, o + d * tb))
    rect = VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98)
    u0, v0, u1, v1 = rect
    ctr = A + d * ((HK_TOP + ROOT) / -d.y * 0.5)
    for i in range(4):
        (ta, ba), (tb_, bb) = corners[i], corners[(i + 1) % 4]
        _quad(m, [ta, tb_, bb, ba], [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], ctr)
    e = VM.sub(rect, 0.0, 0.0, 0.25, 0.25)
    eu = [(e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3])]
    _quad(m, [c[0] for c in corners], eu, ctr)
    _quad(m, [c[1] for c in corners], eu, ctr)
    # 控貫: 横板の内の面から控柱の芯まで(控柱へ食い込ませる)
    yc = sum(TIE_Y) / 2
    zc = HK_Z0 + d.z * ((yc - HK_TOP) / d.y)
    tw = 0.075
    x0, x1 = xc - tw / 2, xc + tw / 2
    m.box(U(x1), U(x0), TIE_Y[0], TIE_Y[1], zc - HB * 0.3, HK_Z0,
          VM.sub(P['wuv'], 0.20, 0.05, 0.42, 0.95), WOOD)
    return zc


def _boards(m, P, a0, a1, skip=0):
    """`HS._boards` と同じ割り(NB 枚・南京下見)。skip = 下から抜く枚数(水越し)。"""
    h = (H - HS.Y0) / HS.NB
    for i in range(skip, HS.NB):
        a = HS.Y0 + i * h
        lo, hi = 0.10, 0.90
        u0 = lo + (hi - lo) * i / float(HS.NB)
        u1 = lo + (hi - lo) * (i + 1) / float(HS.NB)
        rect = VM.sub(P['wuv'], u0 + 0.008, 0.02, u1 - 0.008, 0.98)
        for (ylo, yhi, dd) in ((a + h * 0.26, a + h, HS.LAP_M), (a, a + h * 0.26, HS.LAP_S)):
            HS._plank(m, rect, a0, a1, ylo, yhi, HS.BACK - dd, HS.BACK)


def _rails(m, P, a0, a1, lower=True):
    for k, y in enumerate(HS.RAILS):
        if k == 0 and not lower:
            continue
        HS._plank(m, VM.sub(P['wuv'], 0.20, 0.05, 0.42, 0.95),
                  a0, a1, y - HS.RAIL_H / 2, y + HS.RAIL_H / 2, HS.BACK, HS.FACE - 0.045)
    HS._plank(m, VM.sub(P['wuv'], 0.46, 0.05, 0.70, 0.95),
              a0, a1, HS.KASA_Y, H, HS.BACK, HS.FACE - 0.040)


def _finish(m, name, P):
    o = m.to_object(name, [P['wood']])
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


def saku(mizu=False):
    name = "Saku_Hikae_Mizukoshi" if mizu else "Saku_Hikae"
    P = N.palette()
    m = VM.Mesh()
    xc = -KEN / 2 + POST / 2                                # 杭の芯(Unity)
    HS._post(m, P, U(xc))
    _rails(m, P, -KEN / 2, KEN / 2, lower=not mizu)         # 対称なので写しは要らない
    _boards(m, P, -KEN / 2, KEN / 2, skip=MIZU_OPEN if mizu else 0)
    if not mizu:
        _hikae(m, P, xc)
    o = _finish(m, name, P)
    return o, name, spec(name, -KEN / 2, KEN / 2, xc, hikae=not mizu,
                         src="saku(mizukoshi=%s)" % mizu)


def post():
    name = "Saku_HikaePost"
    P = N.palette()
    m = VM.Mesh()
    xc = -POST / 2
    HS._post(m, P, U(xc))
    _hikae(m, P, xc)
    o = _finish(m, name, P)
    return o, name, spec(name, -POST, 0.0, xc, hikae=True, post_only=True, src="post()")


# ---------------------------------------------------------------- 札(作図の変数から)
def _brace_z(y, side):
    """控柱の断面の y における z の外端(side=+1)・内端(side=−1)。芯の線 ± 断面の半分の z 成分。"""
    d = _axis()
    zc = HK_Z0 + d.z * ((y - HK_TOP) / d.y)
    half = HB / 2 / abs(d.y)                          # 斜めの角材を水平に切った断面の z の半幅
    # 頭は z = HK_Z0 で切ってあるので外端はそこで頭打ち
    return min(HK_Z0, zc + half) if side > 0 else zc - half


def spec(name, x0, x1, xc, hikae, src, post_only=False):
    yb = -ROOT
    yfoot = yb + 0.05                                    # EdoPartSpec.Measure の足元の断面
    pz = (HS.BACK, HS.FACE)                              # 杭の z
    foot = [(xc - POST / 2, pz[0]), (xc + POST / 2, pz[0]), (xc + POST / 2, pz[1]), (xc - POST / 2, pz[1])]
    zin = pz[0]
    if hikae:
        zb0, zb1 = _brace_z(yfoot, -1), _brace_z(yfoot, +1)
        foot = [(xc - POST / 2, pz[1]), (xc - POST / 2, pz[0]),
                (xc - HB / 2, zb1), (xc - HB / 2, zb0), (xc + HB / 2, zb0), (xc + HB / 2, zb1),
                (xc + POST / 2, pz[0]), (xc + POST / 2, pz[1])]
        zin = zb0
    # 丈の帯(底 +0.30 〜 min(1.80, 丈×0.95))の断面の内端 = 控柱の内の面の一番下(帯の下端)
    hgt = H + ROOT
    back = HS.BACK - HS.LAP_S if not post_only else pz[0]
    if hikae:
        back = min(back, _brace_z(yb + 0.30, -1))
    zmin = min(zin, back, _brace_z(yb, -1) if hikae else zin)
    return {
        "prefab": "Assets/Edo/Models/Hei/%s.fbx" % name, "kind": "fence",
        "source": "blender:build_saku_hikae.py %s ── 板柵は build_hori_saku(h %g・杭 %g・根入れ %g)・控柱 %g角 頭 %g 出 %g"
                  % (src, H, POST, ROOT, HB, HK_TOP, HK_FOOT),
        "unitScale": 1.0, "yBottom": yb, "foot": [{"x": x, "y": z} for x, z in foot],
        "front": HS.FACE, "back": back,
        "eave": {"x0": x0, "x1": x1, "z0": zmin, "z1": HS.FACE, "y0": yb, "y1": H},
        "faceOut": HS.FACE, "faceIn": zin,
        "copingOverhang": 0.0, "height": hgt,
    }


# ---------------------------------------------------------------- 検め画像
def _dup(o, dx):
    c = o.copy(); c.data = o.data.copy()
    bpy.context.collection.objects.link(c)
    c.location.x += dx
    c.hide_render = False
    return c


def _bg(col):
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = col


def shots(o, w, p):
    """run = 素の駒 2 + 水越し 1 + 素の駒 1 + 端の杭(Unity +X へ並ぶ = Blender −x)。"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    for ob in (o, w, p):
        ob.hide_render = True
    # Unity X = −Blender x。駒 i の中心は Unity X = i·KEN ⇒ Blender x = −i·KEN
    seq = [o, o, w, o]
    run = [_dup(src, -KEN * i - src.location.x) for i, src in enumerate(seq)]
    pe = _dup(p, -(KEN * 3.5) - p.location.x)               # 端の杭の +X 面を run の終端(Unity X = 3.5間)へ
    allo = run + [pe]
    mn, mx = V.bbox(allo); c = (mn + mx) * 0.5; W = mx.x - mn.x
    # 外(水側 = Unity +Z = Blender −Y)から立面
    V.studio((c.x, mn.y - 20.0, 0.7), (c.x, c.y, 0.7), ortho_scale=W * 1.08, res=(1800, 700))
    _bg((1.0, 0.0, 1.0, 1))
    V.render(os.path.join(SHOT, "saku_hikae_run_elev.png"))
    V.studio((mx.x + 2.0, mn.y - 4.5, 1.8), (c.x, c.y, 0.7), res=(1800, 1000))
    V.render(os.path.join(SHOT, "saku_hikae_run_soto.png"))
    # 内(屋敷側 = Blender +Y)から ── 控柱
    V.studio((mn.x - 2.0, mx.y + 4.5, 1.8), (c.x, c.y, 0.7), res=(1800, 1000))
    V.render(os.path.join(SHOT, "saku_hikae_run_uchi.png"))
    # 横から(走りの向き)── 控柱の勾配・根入れ
    V.studio((mn.x - 8.0, c.y, 0.6), (c.x, c.y, 0.6), ortho_scale=2.6, res=(1100, 1100))
    _bg((1.0, 0.0, 1.0, 1))
    V.render(os.path.join(SHOT, "saku_hikae_side.png"))
    # 控柱の頭と根元の寄り
    V.studio((mx.x - 0.4, mx.y + 1.8, 1.3), (mx.x - 0.9, -0.3, 0.5), res=(1300, 1100))
    V.render(os.path.join(SHOT, "saku_hikae_yori.png"))
    for x in allo:
        bpy.data.objects.remove(x, do_unlink=True)
    for ob in (o, w, p):
        ob.hide_render = False


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    V.reset()
    o, n0, s0 = saku(False)
    w, n1, s1 = saku(True)
    p, n2, s2 = post()
    w.location.x += 5.0; p.location.x += 10.0
    bpy.context.view_layer.update()
    for ob in (o, w, p):
        mn, mx = V.bbox([ob])
        print("[saku_hikae] %-22s Unity実寸 W(X)=%.4f H(Y)=%.4f D(Z)=%.4f 底=%.3f  Unity X %.4f..%.4f  Z %.4f..%.4f  面=%d 材=%s"
              % (ob.name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z,
                 -(mx.x - ob.location.x), -(mn.x - ob.location.x), -mx.y, -mn.y,
                 len(ob.data.polygons), [mm.name for mm in ob.data.materials]))
    if "--render" in argv:
        shots(o, w, p)
    w.location.x -= 5.0; p.location.x -= 10.0
    bpy.context.view_layer.update()
    for ob, nm, sp in ((o, n0, s0), (w, n1, s1), (p, n2, s2)):
        path = os.path.join(OUT, nm + ".fbx")
        V.export_fbx([ob], path, kind="fence", spec=sp)
        print("[saku_hikae] 書き出し " + path)


if __name__ == "__main__":
    main()
