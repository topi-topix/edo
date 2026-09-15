# -*- coding: utf-8 -*-
"""山王権現社の**透塀(瑞垣)** — 屋根銅瓦葺・腰板+連子格子+小壁。1スパンの run 部材と、出隅・入隅の隅部材。

    blender --background --python Tools/Blender/build_sanno_sukibei.py -- [--span 2.54] [--ends nn,tn,nt,nc,cn]
                                                                         [--no-kado] [--render] [--no-export]

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在庫に無い(在庫方の判定 2026-09-14)。形式は【S [国宝建造物目録1941]】「透塀 屋根銅瓦葺」。
参考にした在庫の作り: 連子 = 楼門の連子窓(`build_sanno_romon` の竪子)、小屋根 = キットの瓦モジュール
(`GR._tile_field_fast`)を銅瓦(`SH.to_copper` → `Doukawara`)にした物。⛔ 瓦をゼロから作らない。

━━━ 丈(床 = 基壇の天端 = Y0 から)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`HT` = 【U 考証 2026-09-14】腰(板)の天端 0.75 / 透かし(連子)0.75〜1.65 / 小壁 1.65〜1.95 / 軒先 1.95 / 棟の天端 2.25。
それ以外(`G`: 柱 0.18 角・土台・貫・軒の出 0.40・棟の丈・基壇の根入れ 0.30 と幅 0.60・瓦の縮尺)は【U 部材方】。
屋根の勾配は軒先と棟の天端からの従属値(`K_ROOF` = 0.40)。

━━━ 軸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unity ローカル: 走り = X / 高さ = Y / 厚み = Z(見え面 +Z。⚠ 断面は表裏対称)/ **ピボット = スパンの中心・床レベル**。
論理 (u = X, v = Z, h = Y) で組み `SH.q` / `SH.BX` で落とす(中門と同じ)。

━━━ 部材の割り(run 側が並べる)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・**スパン** `Sanno_Sukibei_<スパンmm>_<a><b>` — X ∈ [−s/2, +s/2]。端 a(−X)・b(+X)の種類:
    n = 次のスパンへ続く。⭐ **柱は +X の端にだけ持つ**(b = n のとき)。−X の端は前のスパンの柱の面から始まる。
    t = 中門の本柱の外面(口の縁)へ**突き付け**。柱を持たず、屋根を破風板と袖の稜で閉じ、棟の端に小さな鬼。
    c = 隅部材へ続く。柱を持たず、屋根・土台・基壇を隅の芯から手前で止める(隅部材が受ける)。
    h = **口の縁の柱で止める**(南の潜り・渡廊下の取り付く口)。柱芯 = スパンの端(n と同じ通り)で、柱を棟の天端まで
        立てて頭に銅の笠。屋根は柱の塀側の面で破風板・袖の稜・小さな鬼に閉じ、基壇は柱の外面まで。
        ⭐ 渡廊下は屋根を塀の棟より上に通し、北の木口を**この柱の南の面**へ突き付ける(指図 joints)。
        `-- --kuchi <西のスパンm>,<東のスパンm> --render` で口の組み上がり(御供所と渡廊下の模型)を焼く。
・**隅** `Sanno_Sukibei_Kado_<Dezumi|Irizumi>_<基準スパンmm>` — 芯 = 隅の柱の芯 = ピボット。
    出隅 = 脚が −X と −Z(見え面の側 = 外の角が隅棟)/ 入隅 = 脚が −X と +Z(見え面の側が谷)。
    隅の柱・隅の瓦場(隅棟と谷)・野地・基壇の升を持つ。
・⭐ **瓦の縮尺**は「スパンに瓦モジュール(2.004)が整数枚」になるよう一様に掛ける(2.54 ⇒ 2 枚・0.634)。
  継ぎ目で瓦の割付が崩れない(README「モジュール長は割り切れる数に」)。隅は基準スパンの縮尺を使う。
"""
import bpy, bmesh, sys, os, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH
import build_sanno_buzai as SB
import build_sanno_chumon as CH

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
CHUMON = os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno",
                      "Sanno_Chumon_1x1ken_2540x2540_k400-400-148-148.fbx")
CHUMON_FACE = 1.27 + 0.15          # 中門の本柱の外面(柱芯 + 半径)= 透塀の口の縁

HT = dict(koshi=0.75, sukashi=1.65, kokabe=1.95, eave=1.95, ridgeTop=2.25)   # 【U 考証 2026-09-14】
G = dict(
    post=0.18,          # 柱(角)の見付
    dodaiH=0.12, dodaiW=0.16,    # 土台
    kasagi=0.06, railW=0.14,     # 腰の笠木(天端 = HT.koshi)・貫の見込み
    itaT=0.025,         # 腰板の厚みの半分
    renjiW=0.045, renjiP=0.12,   # 連子子の見付・割り
    nukiH=0.06,         # 内法貫(透かしの上)
    kabeT=0.06,         # 小壁(漆喰)の厚み
    ketaW=0.16, ketaH=0.12,      # 桁
    D=0.40,             # 軒の出(壁の芯から軒先まで)
    ridgeW=0.26, ridgeH=0.18, ridgeSeat=0.04,   # 棟(瓦場の頂から seat だけ沈める)
    kidanW=0.30, kidanDepth=0.30,               # 基壇(半幅・根入れ。天端 = Y0)
    tileSc=0.634,       # 瓦の縮尺の目安(実際はスパンに整数枚へ合わせる)
    taruP=0.30, taruW=0.05, taruT=0.06,         # 垂木
    capT=0.04,          # 口の柱(h)の銅の笠の厚み(笠の天端 = 棟の天端)
)
KUCHI_HALF = 0.5 * 1.818           # 南の潜りの口の半幅 = 指図 runs[Sukibei_S].gapHalf[間](柱芯 = 口の縁)
GOKUSHO = os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno", "Sanno_Gokusho_3x4.5ken_5454x8181.fbx")
GOKUSHO_AT = ((-30.75 + 1.5 - (-28.25)) * 1.818, (-13.0 + 2.25 - (-6.3889)) * 1.818)   # 口の芯から御供所の芯(X 東, Z 北)
K_ROOF = (HT["ridgeTop"] - (G["ridgeH"] - G["ridgeSeat"]) - HT["eave"]) / G["D"]
ALLOWED = ("wood", "wall C", "Kirishi", "Doukawara")


class Lin(object):
    def __init__(self, k):
        self.k = k

    def z(self, d):
        return self.k * d


def zr(v):
    """スパンの屋根面の名目の高さ(棟 = v 0)。"""
    return HT["eave"] + K_ROOF * (G["D"] - abs(v))


def tile_scale(s):
    n = max(1, int(round(s / (GR.MOD_LEN * G["tileSc"]))))
    return s / (n * GR.MOD_LEN)


# ==========================================================================
# 道具
# ==========================================================================
def vstrip(M, u0, u1, vs, hbot, htop, uvr, mat):
    """u0..u1 の幅で、v の折れ線に沿って下端 hbot(v)・上端 htop(v) の板。"""
    for i in range(len(vs) - 1):
        C = {}
        for iu, uu in ((0, u0), (1, u1)):
            for iv, vv in ((0, vs[i]), (1, vs[i + 1])):
                C[(iu, iv, 0)] = (uu, vv, hbot(vv))
                C[(iu, iv, 1)] = (uu, vv, htop(vv))
        CH.hexa(M, C, uvr, mat)


def prism(name, poly_uv, hbot, htop, mat, rect):
    """論理 (u,v) の凸多角形を、下端 hbot(u,v)・上端 htop(u,v) で押し出す(Blender 座標で直に組む)。"""
    bm = bmesh.new()
    bot = [bm.verts.new((SH.BX(u, v)[0], SH.BX(u, v)[1], hbot(u, v))) for (u, v) in poly_uv]
    top = [bm.verts.new((SH.BX(u, v)[0], SH.BX(u, v)[1], htop(u, v))) for (u, v) in poly_uv]
    bm.faces.new(bot)
    bm.faces.new(top)
    n = len(poly_uv)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    V.set_uv_rect(o, rect, axes=('x', 'y'))
    return o


def field(poly_uv, eave_uv, up_uv, sc, hnom, name):
    """瓦場1面。poly = 論理 (u,v) の凸多角形、eave_uv = 軒先線上の基準点(割付の原点)、up_uv = 棟へ向かう単位方向。
    ⭐ 基準点のまわりに一様に sc 倍して、勾配 `K_ROOF` へずらす。返り値 (object, 谷の深さ dmin)。"""
    org = SH.BX(*eave_uv)
    up = (-up_uv[0], -up_uv[1])                 # BX の線形部分は符号反転
    yaw = math.degrees(math.atan2(up[1], up[0])) % 360.0
    poly = [SH.BX(*p) for p in poly_uv]
    pre = [(org[0] + (p[0] - org[0]) / sc, org[1] + (p[1] - org[1]) / sc) for p in poly]
    f = GR._tile_field_fast([pre], org, yaw, HT["eave"], name)
    if f is None:
        raise SystemExit("[sukibei] ⛔ 瓦場が空: %s" % name)
    ez = HT["eave"]
    for vt in f.data.vertices:
        vt.co.x = org[0] + (vt.co.x - org[0]) * sc
        vt.co.y = org[1] + (vt.co.y - org[1]) * sc
        vt.co.z = ez + (vt.co.z - ez) * sc
    f.data.update()
    # 向きの検算(⛔ yaw の符号を取り違えると軒と棟が入れ替わる): 棟寄りの頂点ほど高いか
    ds = [((vt.co.x - org[0]) * up[0] + (vt.co.y - org[1]) * up[1], vt.co.z) for vt in f.data.vertices]
    near = [z for d, z in ds if d < 0.10]
    far = [z for d, z in ds if d > 0.25]
    if near and far and sum(far) / len(far) <= sum(near) / len(near):
        raise SystemExit("[sukibei] ⛔ 瓦場『%s』の流れが逆(yaw %.0f)" % (name, yaw))
    SH.sori_shear(f, org, up, Lin(K_ROOF))
    D = G["D"]
    dmin = 0.0
    for vt in f.data.vertices:
        d = (vt.co.x - org[0]) * up[0] + (vt.co.y - org[1]) * up[1]
        if 0.03 < d < D - 0.03:
            u, v = -vt.co.x, -vt.co.y
            dmin = min(dmin, vt.co.z - hnom(u, v))
    return f, dmin


def stones_run(u0, u1, name):
    mat = SB.kirishi_material()
    L = u1 - u0
    n = max(1, int(round(L / 1.20)))
    out = []
    for i in range(n):
        a, b = u0 + L * i / n, u0 + L * (i + 1) / n
        out.append(SB._stone(a, b, -G["kidanW"], G["kidanW"], -G["kidanDepth"], 0.0, mat,
                             SB.rng_of("sukibei", name, i), "%s_kidan%d" % (name, i),
                             chamfer=SH.KAME_MEJI, tile=SB.KIRISHI_TILE))
    return out


def stone_sq(name):
    mat = SB.kirishi_material()
    w = G["kidanW"]
    return [SB._stone(-w, w, -w, w, -G["kidanDepth"], 0.0, mat, SB.rng_of("sukibei", name, "sq"),
                      name + "_kidan_sq", chamfer=SH.KAME_MEJI, tile=SB.KIRISHI_TILE)]


def to_blender(objs):
    for o in objs:                                   # 論理 → Blender(Rz180°・det +1)
        o.data.transform(Matrix.Diagonal((-1.0, -1.0, 1.0, 1.0)))
        o.data.update()
    return objs


def roof_rect():
    ru = V.sample_uv(GR.MOD, pick_high=True)
    return (ru[0] - 0.01, ru[1] - 0.01, ru[0] + 0.01, ru[1] + 0.01)


def finish(name, body, parts, stones):
    V.dedup_materials()
    o = V.join([body] + [x for x in parts if x] + stones, name)
    SH.to_copper(o)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


# ==========================================================================
# スパン
# ==========================================================================
def build_span(s, ends, name, sc=None):
    a, b = ends[0], ends[1]
    if a not in "ntch" or b not in "ntch":
        raise SystemExit("[sukibei] ⛔ 端の種類は n/t/c/h: %s" % ends)
    hs, pr, D = s / 2.0, G["post"] / 2.0, G["D"]
    ms, uv = SH.mats()
    W, WC = SH.W, SH.WC
    M = VM.Mesh()
    # h = 口の縁の柱で止める: 柱芯 = スパンの端(n と同じ位置)・屋根は柱の塀側の面で破風に閉じる・基壇は柱の外面まで
    m_lo = -hs + (0.0 if a == "t" else pr); m_hi = hs - (0.0 if b == "t" else pr)
    d_lo = -hs + (pr if a == "c" else 0.0); d_hi = hs - (pr if b == "c" else 0.0)
    r_lo = -hs + {"c": D, "h": pr}.get(a, 0.0); r_hi = hs - {"c": D, "h": pr}.get(b, 0.0)
    k_lo = -hs + {"c": G["kidanW"], "h": -pr}.get(a, 0.0); k_hi = hs - {"c": G["kidanW"], "h": -pr}.get(b, 0.0)
    sc = sc or tile_scale(s)

    # --- 瓦場(先に焼いて谷の深さを測る)-------------------------------------
    fields, dmin = [], 0.0
    for sg in (1, -1):
        poly = [(r_lo, 0.0), (r_hi, 0.0), (r_hi, sg * D), (r_lo, sg * D)]
        f, dm = field(poly, (-hs, sg * D), (0.0, -float(sg)), sc, lambda u, v: zr(v), "%s_f%d" % (name, sg))
        fields.append(f); dmin = min(dmin, dm)
    noji_top = dmin - 0.01
    noji_bot = noji_top - 0.03
    under = lambda v: zr(v) + noji_bot

    # --- 軸部 ---------------------------------------------------------------
    SH.box3(M, d_lo, d_hi, -G["dodaiW"] / 2, G["dodaiW"] / 2, 0.0, G["dodaiH"], uv["wood_h"], W, grain="u")
    SH.panel_ita(M, m_lo, m_hi, "u", 0.0, G["dodaiH"], HT["koshi"] - G["kasagi"], uv["wood"], W, t=G["itaT"])
    # ⛔ 腰板の目地(8 mm)から向こうの光が白い筋に抜けた(2026-09-14 立面で実見)⇒ 板の芯に裏板を通す
    SH.box3(M, m_lo, m_hi, -G["itaT"] * 0.4, G["itaT"] * 0.4, G["dodaiH"], HT["koshi"] - G["kasagi"],
            uv["wood_h"], W, grain="u")
    SH.box3(M, m_lo, m_hi, -G["railW"] / 2, G["railW"] / 2, HT["koshi"] - G["kasagi"], HT["koshi"],
            uv["wood_h"], W, grain="u")
    L = m_hi - m_lo
    nr = max(2, int(round(L / G["renjiP"])))
    for i in range(nr):
        c = m_lo + L * (i + 0.5) / nr
        SH.box3(M, c - G["renjiW"] / 2, c + G["renjiW"] / 2, -G["renjiW"] / 2, G["renjiW"] / 2,
                HT["koshi"], HT["sukashi"], uv["wood"], W, grain="h")
    SH.box3(M, m_lo, m_hi, -G["railW"] / 2, G["railW"] / 2, HT["sukashi"], HT["sukashi"] + G["nukiH"],
            uv["wood_h"], W, grain="u")
    kw = G["ketaW"] / 2.0
    kbot = under(kw) - G["ketaH"]
    SH.box3(M, m_lo, m_hi, -G["kabeT"] / 2, G["kabeT"] / 2, HT["sukashi"] + G["nukiH"], kbot + 0.01,
            uv["wall"], WC, grain="u")
    vstrip(M, m_lo, m_hi, [-kw, 0.0, kw], lambda v: kbot, under, uv["wood_h"], W)       # 桁(上端は野地なり)
    if b == "n":
        SH.box3(M, hs - pr, hs + pr, -pr, pr, G["dodaiH"], under(pr), uv["wood"], W, grain="h")
    # --- 口の縁の柱(h)— 棟の天端まで立て、頭に銅の笠。⭐ 渡廊下の北の木口はこの柱の南の面へ突き付く ---
    caps = []
    for end, sgn in ((a, -1), (b, +1)):
        if end != "h":
            continue
        uc0 = sgn * hs
        SH.box3(M, uc0 - pr, uc0 + pr, -pr, pr, 0.0, HT["ridgeTop"] - G["capT"], uv["wood"], W, grain="h")
        cw = pr + 0.03
        caps.append(prism("%s_kasa%d" % (name, sgn), [(uc0 - cw, -cw), (uc0 + cw, -cw), (uc0 + cw, cw), (uc0 - cw, cw)],
                          lambda u, v: HT["ridgeTop"] - G["capT"], lambda u, v: HT["ridgeTop"],
                          bpy.data.materials.get("roof") or V.borrow_material(GR.MOD, "roof"), roof_rect()))
    # --- 野地・垂木 -----------------------------------------------------------
    vstrip(M, r_lo, r_hi, [-D, 0.0, D], lambda v: zr(v) + noji_bot, lambda v: zr(v) + noji_top, uv["wood_h"], W)
    nt = max(1, int(round((r_hi - r_lo) / G["taruP"])))
    for i in range(nt):
        uu = r_lo + (r_hi - r_lo) * (i + 0.5) / nt
        for sg in (-1, 1):
            vv = sg * (D - 0.02)
            SH.stick(M, (uu, vv, zr(vv) + noji_bot - G["taruT"] / 2), (uu, 0.0, zr(0.0) + noji_bot - G["taruT"] / 2),
                     G["taruW"], G["taruT"], uv["wood_h"], W)
    # --- 突き付けの端(t)・柱止めの端(h)= 破風板 ---------------------------------------
    for end, sgn in ((a, -1), (b, +1)):
        if end not in "th":
            continue
        ue = sgn * (hs if end == "t" else hs - pr)
        u0, u1 = sorted((ue, ue - sgn * 0.035))
        vstrip(M, u0, u1, [-D - 0.02, 0.0, D + 0.02], lambda v: zr(v) + noji_bot - 0.08,
               lambda v: zr(v) + 0.02, uv["wood_h"], W)
    body = M.to_object(name + "_body", ms)

    # --- 棟・袖の稜・鬼 -----------------------------------------------------------
    parts = list(fields)
    zR = zr(0.0) - G["ridgeSeat"]
    p0, p1 = SH.BX(r_lo, 0.0), SH.BX(r_hi, 0.0)
    parts += GR.ridge((p0[0], p0[1], zR), (p1[0], p1[1], zR), name + "_mune", w=G["ridgeW"], h=G["ridgeH"])
    for end, sgn in ((a, -1), (b, +1)):
        if end not in "th":
            continue
        he = hs if end == "t" else hs - pr          # 屋根の端 = 中門の本柱の外面(t)/ 口の柱の塀側の面(h)
        uc = sgn * (he - 0.07)
        for sv in (-1, 1):
            q0, q1 = SH.BX(uc, sv * (D + 0.02)), SH.BX(uc, 0.0)
            parts += GR.ridge((q0[0], q0[1], zr(D + 0.02) - 0.01), (q1[0], q1[1], zr(0.0) - 0.01),
                              "%s_sode%d%d" % (name, sgn, sv), w=0.14, h=0.10)
        pc = SH.BX(sgn * (he - 0.20), 0.0)
        oni = GR.oni((pc[0], pc[1], zr(0.0) - 0.04), (-float(sgn), 0.0), "%s_oni%d" % (name, sgn), scale=0.30)
        for g in oni:                                # ⛔ 本柱・口の柱の面を越えさせない
            V.sel([g]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            us = [-vt.co.x for vt in g.data.vertices]
            over = (max(us) - (he - 0.005)) if sgn > 0 else ((-he + 0.005) - min(us))
            if over > 0:
                g.data.transform(Matrix.Translation((sgn * over, 0.0, 0.0)))   # Blender X = −u
                g.data.update()
        parts += oni
    parts += caps
    stones = to_blender(stones_run(k_lo, k_hi, name))
    o = finish(name, body, parts, stones)
    info = dict(kind="span", s=s, ends=ends, hs=hs, foot=(r_lo + 0.02, r_hi - 0.02, -D + 0.02, D - 0.02),
                noji=(noji_bot, noji_top), dmin=dmin, sc=sc)
    return o, info


# ==========================================================================
# 隅(出隅: 脚が −X と −Z。入隅はそれを Z で鏡映)
# ==========================================================================
def build_kado(dezumi, ref, name):
    D, pr = G["D"], G["post"] / 2.0
    sc = tile_scale(ref)
    ms, uv = SH.mats()
    W = SH.W
    E, K = HT["eave"], K_ROOF
    regions = [   # (名, 多角形, 軒先の基準点, 棟への向き, 名目の高さ)
        ("Ap", [(-D, 0.0), (0.0, 0.0), (D, D), (-D, D)], (0.0, D), (0.0, -1.0), lambda u, v: E + K * (D - v)),
        ("Am", [(-D, 0.0), (-D, -D), (0.0, 0.0)], (0.0, -D), (0.0, 1.0), lambda u, v: E + K * (D + v)),
        ("Bp", [(0.0, 0.0), (0.0, -D), (D, -D), (D, D)], (D, 0.0), (-1.0, 0.0), lambda u, v: E + K * (D - u)),
        ("Bm", [(0.0, 0.0), (-D, -D), (0.0, -D)], (-D, 0.0), (1.0, 0.0), lambda u, v: E + K * (D + u)),
    ]
    parts, dmin = [], 0.0
    for tag, poly, org, up, hn in regions:
        f, dm = field(poly, org, up, sc, hn, "%s_f%s" % (name, tag))
        parts.append(f); dmin = min(dmin, dm)
    noji_top = dmin - 0.01
    noji_bot = noji_top - 0.03
    noji = [prism("%s_noji%s" % (name, tag), poly, (lambda hn: lambda u, v: hn(u, v) + noji_bot)(hn),
                  (lambda hn: lambda u, v: hn(u, v) + noji_top)(hn), ms[0], uv["wood_h"])
            for tag, poly, org, up, hn in regions]
    M = VM.Mesh()
    top = E + K * (D - pr) + noji_bot
    SH.box3(M, -pr, pr, -pr, pr, 0.0, top, uv["wood"], W, grain="h")        # 隅の柱(土台の升を兼ねる)
    body = M.to_object(name + "_body", ms)
    zR = E + K * D - G["ridgeSeat"]
    for q0, q1 in (((-D, 0.0), (G["ridgeW"] / 2, 0.0)), ((0.0, -D), (0.0, G["ridgeW"] / 2))):
        a0, a1 = SH.BX(*q0), SH.BX(*q1)
        parts += GR.ridge((a0[0], a0[1], zR), (a1[0], a1[1], zR), name + "_mune", w=G["ridgeW"], h=G["ridgeH"])
    h0, h1 = SH.BX(0.05, 0.05), SH.BX(D + 0.02, D + 0.02)                    # 隅棟(外の角)
    parts += GR.ridge((h0[0], h0[1], E + K * D - 0.03), (h1[0], h1[1], E - K * 0.02 - 0.03),
                      name + "_sumi", w=0.18, h=0.12)
    # 谷の銅板(内の角)。瓦場は谷の線で切れるので、野地の上に銅の板を敷く
    roofmat = bpy.data.materials.get("roof")
    rr = roof_rect()
    bm = bmesh.new()
    nvec = (1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0))
    pts = []
    for t, side in ((D + 0.02, -1), (0.0, -1), (0.0, 1), (D + 0.02, 1)):
        u, v = -t + side * 0.08 * nvec[0], -t + side * 0.08 * nvec[1]
        bx = SH.BX(u, v)
        pts.append(bm.verts.new((bx[0], bx[1], E + K * (D - t) + noji_top + 0.004)))
    fc = bm.faces.new(pts)
    bm.normal_update()
    if fc.normal.z < 0:
        fc.normal_flip()
    me = bpy.data.meshes.new(name + "_tani"); bm.to_mesh(me); bm.free()
    tani = bpy.data.objects.new(name + "_tani", me)
    bpy.context.scene.collection.objects.link(tani)
    me.materials.append(roofmat)
    V.set_uv_rect(tani, rr, axes=('x', 'y'))
    parts.append(tani)
    stones = to_blender(stone_sq(name))
    o = finish(name, body, parts + noji, stones)
    if not dezumi:
        o.data.transform(Matrix.Diagonal((1.0, -1.0, 1.0, 1.0)))            # Z(Blender −Y)で鏡映
        o.data.flip_normals()
        o.data.update()
    info = dict(kind="kado", dezumi=dezumi, foot=(-D + 0.02, D - 0.02, -D + 0.02, D - 0.02),
                noji=(noji_bot, noji_top), dmin=dmin, sc=sc)
    return o, info


# ==========================================================================
# 検算
# ==========================================================================
def verts_of(o, names):
    mats = o.data.materials
    idx = [i for i, m in enumerate(mats) if m and m.name.split('.')[0] in names]
    vs = set()
    for pg in o.data.polygons:
        if pg.material_index in idx:
            vs.update(pg.vertices)
    U = SH.unity_verts(o)
    return [U[i] for i in vs]


def report(o, info):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    print("SUKIBEI %s Unity W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d mats=%s"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), min(xs), max(xs), min(ys), max(ys),
             min(zs), max(zs), tris, mats))
    ok = True
    cu = verts_of(o, ("Doukawara",))
    ridge_top = max(t[1] for t in cu)
    eave = [t[1] for t in cu if (abs(t[2]) > G["D"] - 0.03 if info["kind"] == "span" else
                                 max(abs(t[0]), abs(t[2])) > G["D"] - 0.03)]
    print("  丈 銅瓦の頂 %.3f(棟の天端 %.2f)/ 軒先の銅瓦の最低 %.3f(軒先 %.2f)/ 瓦の縮尺 %.3f / 谷の深さ %.3f / 野地 %.3f〜%.3f"
          % (ridge_top, HT["ridgeTop"], min(eave) if eave else float("nan"), HT["eave"], info["sc"], info["dmin"],
             info["noji"][0], info["noji"][1]))
    if ridge_top > HT["ridgeTop"] + 0.01:
        print("  ⛔ 棟が天端 %.2f を越える" % HT["ridgeTop"]); ok = False
    if info["kind"] == "span":
        wd = verts_of(o, ("wood",))
        kasa = max(t[1] for t in wd if 0.5 < t[1] < 0.9)
        bars = len(set(round(t[0], 3) for t in wd if abs(t[1] - 1.2) < 1e-3))
        print("  帯 腰の笠木の天端 %.3f / 透かし %.2f〜%.2f / 厚み Z[%.3f,%.3f](対称 %s)"
              % (kasa, HT["koshi"], HT["sukashi"], min(zs), max(zs), "⭕" if abs(max(zs) + min(zs)) < 0.005 else "⛔"))
    bad = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bad else "⛔ %s" % bad))
    ok = ok and not bad
    return ok, tris


def soffit_check(o, info):
    """屋根の下から真上へ光線 — 銅瓦に先に当たる/何にも当たらない(空が抜ける)を数える。"""
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    mats = o.data.materials
    u0, u1, v0, v1 = info["foot"]
    cu = miss = tot = 0
    n = 20
    for i in range(n + 1):
        for j in range(n + 1):
            u = u0 + (u1 - u0) * i / float(n)
            v = v0 + (v1 - v0) * j / float(n)
            bx = SH.BX(u, v)
            loc, nrm, idx, dist = bvh.ray_cast(Vector((bx[0], bx[1], 1.0)), Vector((0, 0, 1)), 5.0)
            tot += 1
            if idx is None:
                miss += 1; continue
            m = mats[o.data.polygons[idx].material_index]
            if m and m.name.split('.')[0] == "Doukawara":
                cu += 1
    ok = cu == 0 and miss == 0
    print("  検算 軒裏 %s(真上の光線 %d 本: 銅瓦に先に当たる %d / 空へ抜ける %d)" % ("⭕" if ok else "⛔", tot, cu, miss))
    return ok


# ==========================================================================
# 組み上がり(中門 + スパン2 + 出隅 + スパン1)— 当たりと検証レンダ
# ==========================================================================
def assembly(s, render):
    V.reset()
    hs = s / 2.0
    sp1, _ = build_span(s, "tn", "A_tn")
    sp2, _ = build_span(s, "nc", "A_nc")
    kd, _ = build_kado(True, s, "A_kado")
    sp3, _ = build_span(s, "cn", "A_cn")
    zv = CHUMON_FACE + 2 * s
    # 走り X → 中門の +Z(Blender −Y): Rz +90°
    for ob, y in ((sp1, -(CHUMON_FACE + hs)), (sp2, -(CHUMON_FACE + s + hs)), (kd, -zv)):
        ob.rotation_euler = (0.0, 0.0, math.radians(90.0))
        ob.location = (0.0, y, 0.0)
    sp3.location = (-hs, -zv, 0.0)                  # 隅の脚 −Z → 中門の +X(Blender −X)へ
    objs = VM.import_fbx_abs(CHUMON)
    cm = V.join(objs, "chumon") if len(objs) > 1 else objs[0]
    bpy.context.view_layer.update()
    # 当たり: 中門に接するスパンの頂点から真上へ
    bvh = BVHTree.FromObject(cm, bpy.context.evaluated_depsgraph_get())
    worst = None
    mw = sp1.matrix_world
    top = -1.0
    for vt in sp1.data.vertices:
        w = mw @ vt.co
        top = max(top, w.z)
        if w.z < 1.0:
            continue
        h = bvh.ray_cast(Vector((w.x, w.y, w.z + 1e-4)), Vector((0, 0, 1)), 10.0)
        if h[0] is not None:
            g = h[0].z - w.z
            if worst is None or g < worst[0]:
                worst = (g, -w.x, w.z, -w.y, h[0].z)
    wd = [vt for vt in verts_of(cm, ("wood",)) if abs(vt[0]) < 0.13 and 2.0 < vt[1] < 2.5]
    kabuki = min(t[1] for t in wd) if wd else float("nan")
    minZ = min(-(mw @ vt.co).y for vt in sp1.data.vertices)
    print("  当たり 中門: 透塀の頂 %.3f < 冠木の下端 %.3f %s / 真上の最小の離れ %s / 透塀の中門側の端 Z %.3f(口の縁 %.3f)"
          % (top, kabuki, "⭕" if top < kabuki else "⛔",
             ("%.3f m(X %.2f Y %.3f Z %.2f → 中門の材 Y %.3f)" % worst) if worst else "真上に材なし", minZ, CHUMON_FACE))
    ok = top < kabuki
    out = []
    if render:
        V.hook_textures()
        os.makedirs(SHOT, exist_ok=True)
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, -4.0, -0.005))

        def one(cam, look, fn, ortho=None, res=(1600, 1100)):
            V.studio(cam, look, ortho_scale=ortho, res=res)
            f = os.path.join(SHOT, "sanno_sukibei_%s.png" % fn)
            V.render(f); out.append(f)
        one((-14.0, -4.4, 1.3), (0.0, -4.4, 1.3), "elev", ortho=8.0)
        one((-8.5, 1.5, 2.4), (0.0, -3.5, 1.4), "gate_oblique")
        one((-2.4, -0.3, 1.6), (0.0, -1.7, 1.9), "junction", res=(1400, 1100))
        one((3.2, -zv - 3.4, 2.9), (0.0, -zv, 1.7), "corner_out", res=(1400, 1100))
        one((-3.0, -zv + 3.0, 3.4), (0.0, -zv, 1.8), "corner_in", res=(1400, 1100))
        one((-0.5, -(CHUMON_FACE + hs) + 0.2, 0.9), (-0.05, -(CHUMON_FACE + hs) - 0.3, 2.4), "soffit", res=(1400, 1100))
    return ok, out


def _bvh_world(o):
    bm = bmesh.new(); bm.from_object(o, bpy.context.evaluated_depsgraph_get()); bm.transform(o.matrix_world)
    t = BVHTree.FromBMesh(bm); bm.free()
    return t


def assembly_kuchi(sw, se, render):
    """**南の潜りの口**: 西の 2 スパン(nn・nh)+ 口(柱芯 1 間)+ 東の 2 スパン(hn・nn)。
    御供所(焼いてあれば)と、**検証専用の渡廊下の模型**(柱・桁・切妻。⛔ 書き出さない)を重ねて当たりを数える。"""
    V.reset()
    g = KUCHI_HALF
    lay = [(build_span(sw, "nn", "W_nn")[0], -(g + sw + sw / 2.0)), (build_span(sw, "nh", "W_nh")[0], -(g + sw / 2.0)),
           (build_span(se, "hn", "E_hn")[0], g + se / 2.0), (build_span(se, "nn", "E_nn")[0], g + se + se / 2.0)]
    for ob, X in lay:
        ob.location = (-X, 0.0, 0.0)
    bpy.context.view_layer.update()
    fence = [ob for ob, _ in lay]
    # 口の柱の内面の離れ(= 通れる幅)と、塀の屋根の端(銅瓦・破風・鬼)が柱の塀側の面を越えないか
    wv = [(-(ob.matrix_world @ vt.co).x, (ob.matrix_world @ vt.co).z) for ob in fence[1:3] for vt in ob.data.vertices]
    roofW = max(x for x, y in wv if x < 0 and y > HT["koshi"] + 0.05 and not (abs(x + g) <= G["post"] / 2 + 0.031))
    roofE = min(x for x, y in wv if x > 0 and y > HT["koshi"] + 0.05 and not (abs(x - g) <= G["post"] / 2 + 0.031))
    print("  口: 柱芯 X %.3f / %.3f(芯々 %.3f)・柱の内面の離れ %.3f / 塀の軸部と屋根の端 X %.3f / %.3f(柱の塀側の面 %.3f / %.3f)"
          % (-g, g, 2 * g, 2 * g - G["post"], roofW, roofE, -g - G["post"] / 2, g + G["post"] / 2))
    out = []
    if render:
        V.hook_textures()
        os.makedirs(SHOT, exist_ok=True)
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 4.0, -0.005))

        def one(cam, look, fn, res=(1500, 1100)):
            V.studio(cam, look, res=res)
            f = os.path.join(SHOT, "sanno_sukibei_kuchi_%s.png" % fn)
            V.render(f); out.append(f)
        one((-4.2, 5.2, 2.6), (0.0, 0.0, 1.6), "south")            # 南東の外から(Blender +Y = Unity 南)
        one((3.0, -4.8, 2.4), (0.0, 0.0, 1.5), "north")            # 北西の内から
        one((0.2, 1.7, 1.9), (0.95, 0.0, 1.95), "post_w")          # 西の口の柱と屋根の端の寄り
    # --- 御供所と渡廊下の模型 ---
    hits = {}
    gk = None
    if os.path.exists(GOKUSHO):
        objs = VM.import_fbx_abs(GOKUSHO)
        gk = V.join(objs, "gokusho") if len(objs) > 1 else objs[0]
        gk.location = (-GOKUSHO_AT[0], -GOKUSHO_AT[1], 0.0)
    zN = GOKUSHO_AT[1] + 4.0905 + 0.09                              # 御供所の北面の柱の外面(Unity Z)
    zS = -G["post"] / 2.0                                          # 口の柱の南の面
    L = zS - zN
    pw, eh = 0.075, 2.55
    M = VM.Mesh()
    ms, uv = SH.mats()
    for X in (-g, g):
        for Z in (zN + pw, zS - pw):
            SH.box3(M, X - pw, X + pw, Z - pw, Z + pw, 0.0, eh, uv["wood"], SH.W, grain="h")
        SH.box3(M, X - 0.07, X + 0.07, zN, zS, eh - 0.15, eh, uv["wood_h"], SH.W, grain="v")
    rou = M.to_object("rouka_mock", ms)
    rr = GR.make_kirizuma(L, 2 * g, name="rouka_mock_roof", eave=0.45, end=0.30, tsuma=False)
    rr.location = (0.0, -(zN + zS) / 2.0, eh)
    rr.rotation_euler = (0.0, 0.0, math.radians(90.0))
    bpy.context.view_layer.update()
    tr, tp = _bvh_world(rr), _bvh_world(rou)
    for ob in fence + ([gk] if gk else []):
        tb = _bvh_world(ob)
        hits[ob.name] = (len(tb.overlap(tp)), len(tb.overlap(tr)))
    for k2, (hp, hr) in hits.items():
        print("  当たり(検証の模型)%s ↔ 渡廊下の柱・桁 %d 面対 / 屋根 %d 面対" % (k2, hp, hr))
    if render:
        one((-5.5, 7.5, 3.6), (0.0, 0.5, 2.0), "rouka")
        one((-11.0, 17.0, 10.0), (0.5, 4.5, 2.0), "overview", res=(1600, 1100))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--kuchi" in argv:
        sw, se = (float(x) for x in argv[argv.index("--kuchi") + 1].split(","))
        for f in assembly_kuchi(sw, se, "--render" in argv):
            print("RENDER " + f)
        return
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    s = float(opt("--span", "2.54"))
    ends = opt("--ends", "nn,tn,nt,nc,cn").split(",")
    smm = int(round(s * 1000.0))
    print("[sukibei] スパン %.3f / 瓦の縮尺 %.4f(モジュール %d 枚)/ 勾配 %.3f / 軒の出 %.2f"
          % (s, tile_scale(s), int(round(s / (tile_scale(s) * GR.MOD_LEN))), K_ROOF, G["D"]))
    jobs = [("span", e, "Sanno_Sukibei_%d_%s" % (smm, e)) for e in ends]
    if "--no-kado" not in argv:
        jobs += [("kado", True, "Sanno_Sukibei_Kado_Dezumi_%d" % smm),
                 ("kado", False, "Sanno_Sukibei_Kado_Irizumi_%d" % smm)]
    for kind, arg, name in jobs:
        V.reset()
        o, info = build_span(s, arg, name) if kind == "span" else build_kado(arg, s, name)
        ok, tris = report(o, info)
        sok = soffit_check(o, info)
        if not ok or (not sok and "--allow-soffit" not in argv):
            raise SystemExit("[sukibei] ⛔ 検算に落ちた: %s" % name)
        if "--no-export" not in argv:
            path = os.path.join(OUT, name + ".fbx")
            V.export_fbx([o], path)
            print("[sukibei] 書き出し %s (tris %d)" % (path, tris))
    ok, shots = assembly(s, "--render" in argv)
    for f in shots:
        print("RENDER " + f)
    if not ok:
        raise SystemExit("[sukibei] ⛔ 中門との当たり")


if __name__ == "__main__":
    main()
