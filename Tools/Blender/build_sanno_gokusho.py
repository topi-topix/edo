# -*- coding: utf-8 -*-
"""山王権現社の**御供所** — 明治16年実測図のL字(施主の裁定 2026-09-15)。3本の部材に分ける。

    blender --background --python Tools/Blender/build_sanno_gokusho.py -- [--render] [--no-export]

━━━ 平面(考証の読み + 普請奉行の裁定 ①② 案A)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・**主屋**   u −38.9〜−35.2 / v 北面 〜 −10.2。北面 = 拝殿の縁の外面の通り(東の腕の北面と同じ)。入母屋・棟は南北【S】。
・**北の継ぎ** 主屋と同じ幅 / v 主屋の北面 〜 本殿の縁の外面。別の低い棟(切妻・棟は南北)【S 定性】。
・**東の腕** u −35.2(主屋の東の壁)〜 −29.2 / v 拝殿の縁の外面 〜 −4.8。一段低い別棟(切妻・棟は東西)【S 定性】。
  ⭐ 縁の外面は**実メッシュから測る**(拝殿・本殿の FBX の縁の帯の外接 − 柱芯の半幅)。⛔ 数を写さない。
・柱間 = 江戸間 1.818 に近い等分(主屋 4×8・継ぎ 4×3・腕 6×3)【部材方の判断 — 附属の棟は大工の標準間で建てる】。

━━━ 屋根(考証 ③ 案A・確度 B)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・主屋 = 反りの入母屋(`SH.irimoya`)。軒 3.3・大棟の上端 6.3【U 考証】⇒ 反りの平均勾配は従属値。
・東の腕 = 切妻。軒 3.0・大棟の上端 5.0【U 考証】。**主屋の東の屋根面へ谷で取り付く**(棟は回さない)。
  西の端は主屋の屋根の中まで伸ばして隠す(屋根面どうしの交線 = 谷)。拝殿側は拝殿の軒の下へ突き付け【U】。
・北の継ぎ = 切妻。軒 3.0・大棟の上端 5.0【U 部材方 — 腕と同じ格。範囲「主屋の軒 3.3 < 棟 < 主屋の棟 6.3」の内】。
  南の端は主屋の北の妻壁の奥まで伸ばして隠す。北の端は本殿の縁の外面で止め、妻壁で塞ぐ(ケラバの出 0)。
・銅瓦葺【U】= 社殿の `Doukawara`。

━━━ 基壇・軸部 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・基壇 = 丈 0.45 の縁付き(葛石+羽目石)の切石、石段なし【S 形/U 数】。出は取り合いの無い面だけ 0.30【U】、
  隣の棟の縁の外面・透塀(主屋の西)・部材どうしの継ぎ目は 0。
・床 = 基壇の天端 0.45。角柱 0.18・腰板(裏板付き)0.90・漆喰の壁・桁【U】。賄の口 = 主屋の東面 v −9.0 の柱間【U 庭方】。
・高さはすべて**地盤(ピボット Y0)から**。

━━━ 軸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
各部材: Unity ローカル X = 東(u)/ Z = 北(v)/ Y = 上 / **ピボット = その部材の柱芯の矩形の中心・地盤**。yaw 0・scale one。
"""
import bpy, bmesh, sys, os, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH
import build_sanno_romon as RM
import build_sanno_chumon as CH

K = 1.818
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
MD = os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno")
NB = dict(   # 隣の棟(指図 munes の u0/v0/du/dv[間] と partFrom)
    honden=(-41.8011, 1.0396, 4.1914, 4.1914, "Sanno_Honden_3x3ken_7620x7620"),
    tsukuriai=(-37.6097, 1.0396, 1.1001, 4.1914, "Sanno_Tsukuriai_1x1ken_2000x7620"),
    heiden=(-36.5096, 1.0396, 4.1914, 4.1914, "Sanno_Heiden_3x1ken_7620x7620"),
    haiden=(-32.3182, -1.7602, 5.0605, 9.791, "Sanno_Haiden_3x7ken_9200x17800"),
)
PLAN = dict(omoyaU=(-38.9, -35.2), omoyaS=-10.2, wingU=(-35.2, -29.2), wingS=-4.8)   # 考証の読み[間]
H = dict(omoyaEave=3.3, omoyaRidge=6.3, wingEave=3.0, wingRidge=5.0, tsugiEave=3.0, tsugiRidge=5.0)  # U 考証(継ぎは部材方)
G = dict(kidanH=0.45, kidanOut=0.30, post=0.18, koshi=0.90, kabeT=0.08, ketaH=0.18,
         eaveOmoya=0.90, gf=0.45, eaveWing=0.60, eaveTsugi=0.45, keraba=0.35, cap=0.421, capK=0.13)
ALLOWED = ("wood", "wall C", "door wall", "Doukawara", "Kirishi")


# ==========================================================================
# 取り合いの面 — 実メッシュから
# ==========================================================================
def import_abs(path, name):
    objs = VM.import_fbx_abs(path)
    o = V.join(objs, name) if len(objs) > 1 else objs[0]
    o.name = name
    return o


def en_depth(key):
    """縁の出[m] = 縁・高欄の帯(Y 1.5〜3.0)の外接の Z の半幅 − 柱芯の半幅(dv/2)。"""
    u0, v0, du, dv, part = NB[key]
    o = import_abs(os.path.join(MD, part + ".fbx"), "__en_" + key)
    zs = [-(o.matrix_world @ vt.co).y for vt in o.data.vertices if 1.5 < (o.matrix_world @ vt.co).z < 3.0]
    d = max(abs(min(zs)), abs(max(zs))) - dv * K / 2.0
    bpy.data.objects.remove(o, do_unlink=True)
    return d


def plan():
    V.reset()
    en_h, en_b = en_depth("haiden"), en_depth("honden")
    vN = NB["haiden"][1] - en_h / K               # 拝殿の縁の外面の通り
    vB = NB["honden"][1] - en_b / K               # 本殿の縁の外面の通り
    P = dict(en_h=en_h, en_b=en_b, vN=vN, vB=vB)
    u0, u1 = PLAN["omoyaU"]
    P["omoya"] = dict(u=(u0, u1), v=(PLAN["omoyaS"], vN))
    P["tsugi"] = dict(u=(u0, u1), v=(vN, vB))
    P["wing"] = dict(u=PLAN["wingU"], v=(PLAN["wingS"], vN))
    for k in ("omoya", "tsugi", "wing"):
        r = P[k]
        r["c"] = ((r["u"][0] + r["u"][1]) / 2.0, (r["v"][0] + r["v"][1]) / 2.0)
        r["W"] = (r["u"][1] - r["u"][0]) * K
        r["L"] = (r["v"][1] - r["v"][0]) * K
    print("[gokusho] 縁の出 拝殿 %.3f / 本殿 %.3f ⇒ 主屋の北面 v %.4f・継ぎの北面 v %.4f" % (en_h, en_b, vN, vB))
    for k in ("omoya", "tsugi", "wing"):
        r = P[k]
        print("  %-6s u %.3f〜%.3f / v %.4f〜%.4f ⇒ %.3f × %.3f m" % (k, r["u"][0], r["u"][1], r["v"][0], r["v"][1], r["W"], r["L"]))
    return P


# ==========================================================================
# 道具
# ==========================================================================
def vstrip_v(M, u0, u1, vs, hbot, htop, uvr, mat):
    for i in range(len(vs) - 1):
        C = {}
        for iu, uu in ((0, u0), (1, u1)):
            for iv, vv in ((0, vs[i]), (1, vs[i + 1])):
                C[(iu, iv, 0)] = (uu, vv, hbot(vv))
                C[(iu, iv, 1)] = (uu, vv, htop(vv))
        CH.hexa(M, C, uvr, mat)


def vstrip_u(M, us, v0, v1, hbot, htop, uvr, mat):
    for i in range(len(us) - 1):
        C = {}
        for iu, uu in ((0, us[i]), (1, us[i + 1])):
            for iv, vv in ((0, v0), (1, v1)):
                C[(iu, iv, 0)] = (uu, vv, hbot(uu))
                C[(iu, iv, 1)] = (uu, vv, htop(uu))
        CH.hexa(M, C, uvr, mat)


def kidan(hu, hv, out, finish, name):
    objs = RM.kidan(hu, hv, out, G["kidanH"], name, finish=finish)
    for o in objs:
        o.data.transform(Matrix.Translation((0.0, 0.0, G["kidanH"]))); o.data.update()
    return objs


def wall_run(M, uv, along, fixed, a0, a1, nodes, floor, top, doors=()):
    """柱間ごとの壁。along = "u"(X へ走る)/"v"。nodes = 柱芯の並び(a0..a1 を含む)。doors = 口にする柱間の番号。"""
    pr = G["post"] / 2.0
    for i in range(len(nodes) - 1):
        s0, s1 = nodes[i] + pr, nodes[i + 1] - pr
        if s1 <= s0:
            continue
        zk = floor + G["koshi"]
        if i in doors:
            # 賄の口: 敷居・鴨居・上の小壁、板戸1枚を半分引いた姿
            box = lambda b0, b1, h0, h1, uvr, m, t: (
                SH.box3(M, b0, b1, fixed - t, fixed + t, h0, h1, uvr, m, grain="u") if along == "u"
                else SH.box3(M, fixed - t, fixed + t, b0, b1, h0, h1, uvr, m, grain="v"))
            box(s0, s1, floor, floor + 0.05, uv["wood_h"], SH.W, 0.06)
            box(s0, s1, floor + 1.80, floor + 1.90, uv["wood_h"], SH.W, 0.06)
            box(s0, s1, floor + 1.90, top, uv["wall"], SH.WC, G["kabeT"] / 2)
            mid = (s0 + s1) / 2.0
            if along == "u":
                SH.box3(M, s0, mid + 0.04, fixed - 0.10, fixed - 0.06, floor + 0.05, floor + 1.80, uv["itado"], SH.DW, grain="h")
            else:
                SH.box3(M, fixed - 0.10, fixed - 0.06, s0, mid + 0.04, floor + 0.05, floor + 1.80, uv["itado"], SH.DW, grain="h")
            continue
        if along == "u":
            SH.panel_ita(M, s0, s1, "u", fixed, floor, zk, uv["wood"], SH.W, t=0.025)
            SH.box3(M, s0, s1, fixed - 0.012, fixed + 0.012, floor, zk, uv["wood_h"], SH.W, grain="u")
            SH.box3(M, s0, s1, fixed - G["kabeT"] / 2, fixed + G["kabeT"] / 2, zk, top, uv["wall"], SH.WC, grain="u")
        else:
            SH.panel_ita(M, s0, s1, "v", fixed, floor, zk, uv["wood"], SH.W, t=0.025)
            SH.box3(M, fixed - 0.012, fixed + 0.012, s0, s1, floor, zk, uv["wood_h"], SH.W, grain="v")
            SH.box3(M, fixed - G["kabeT"] / 2, fixed + G["kabeT"] / 2, s0, s1, zk, top, uv["wall"], SH.WC, grain="v")


def posts(M, uv, pts, floor, top):
    pr = G["post"] / 2.0
    for (uu, vv) in pts:
        SH.box3(M, uu - pr, uu + pr, vv - pr, vv + pr, floor, top, uv["wood"], SH.W, grain="h")


def noji_slab(name, pred, bbox, zfun, off, cell=0.25):
    """**野地の板**(厚み 0.03)。⭐ 上面は銅瓦の材 — 瓦の段の継ぎ目の隙から覗いても屋根の色に見える。
    下面は木 — 軒の下から見上げて板に見える。⛔ 瓦の裏(緑)を軒裏に見せない(2026-09-14 中門・社殿で踏んだ)。
    pred(X,Z) = 板を張る範囲、zfun(X,Z) = 名目の屋根面の高さ、off = 瓦の谷の深さ − 0.01(負)。座標は Unity ローカル。"""
    roofmat = bpy.data.materials.get("roof")
    ms, uv = SH.mats()
    ru = V.sample_uv(GR.MOD, pick_high=True)
    rtop = (ru[0] - 0.01, ru[1] - 0.01, ru[0] + 0.01, ru[1] + 0.01)
    rb = uv["wood_h"]
    X0, X1, Z0, Z1 = bbox
    nx, nz = max(1, int(math.ceil((X1 - X0) / cell))), max(1, int(math.ceil((Z1 - Z0) / cell)))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for i in range(nx):
        for j in range(nz):
            xa, xb = X0 + (X1 - X0) * i / nx, X0 + (X1 - X0) * (i + 1) / nx
            za, zb = Z0 + (Z1 - Z0) * j / nz, Z0 + (Z1 - Z0) * (j + 1) / nz
            if not pred((xa + xb) / 2.0, (za + zb) / 2.0):
                continue
            ring = [(xa, za), (xb, za), (xb, zb), (xa, zb)]
            for face, dz, rect, mi in (("top", 0.0, rtop, 0), ("bot", -0.03, rb, 1)):
                pts = ring if face == "top" else ring[::-1]
                vs = [bm.verts.new((-X, -Z, zfun(X, Z) + off + dz)) for (X, Z) in pts]
                f = bm.faces.new(vs)
                f.material_index = mi
                for lp, (X, Z) in zip(f.loops, pts):
                    t, w = (X % 1.8) / 1.8, (Z % 1.8) / 1.8
                    lp[uvl].uv = (rect[0] + (rect[2] - rect[0]) * t, rect[1] + (rect[3] - rect[1]) * w)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(roofmat); me.materials.append(ms[0])
    return o


def roof_dmin(o, pred, zfun):
    """瓦(材 `roof`)の頂点が名目の屋根面からどれだけ下がるか(最小・負)。座標は Unity ローカル。"""
    bpy.context.view_layer.update()                   # ⛔ location を触った直後は matrix_world が古い(1.6 m ずれた)
    idx = {i for i, m in enumerate(o.data.materials) if m and m.name.split('.')[0] == "roof"}
    vs = set()
    for pg in o.data.polygons:
        if pg.material_index in idx:
            vs.update(pg.vertices)
    mw = o.matrix_world
    dm = 0.0
    for i in vs:
        c = mw @ o.data.vertices[i].co
        X, Z = -c.x, -c.y
        if pred(X, Z):
            dm = min(dm, c.z - zfun(X, Z))
    return dm


def lin(a, b, n):
    return [a + (b - a) * i / float(n) for i in range(n + 1)]


def kirizuma_roof(name, length, depth, eave, end, eaveZ, ridgeTop):
    """キットの切妻(`GR.make_kirizuma`・妻壁なし)を、軒 eaveZ・大棟の上端 ridgeTop の直線勾配へずらす。
    返り値は Blender 座標で **大棟 = Blender X・中心 0・軒先 z = eaveZ**。"""
    o = GR.make_kirizuma(length, depth, name=name, eave=eave, end=end, tsuma=False)
    half = depth / 2.0 + eave
    k = (ridgeTop - G["capK"] - eaveZ) / half
    o.location = (0.0, 0.0, 0.0)                     # ⭐ make_kirizuma は set_origin 済み = メッシュは中心に居る
    for vt in o.data.vertices:
        d = half - abs(vt.co.y)
        vt.co.z += (k - GR.RATIO) * d + eaveZ
    o.data.update()
    # 野地(Blender 座標のまま: Unity X = −x・Unity Z = −y)。大棟の方向 = Blender X
    xr = length / 2.0 + end
    zf = lambda X, Z: eaveZ + k * (half - abs(Z))
    # ⛔ 妻の端(破風・袖の役物が同じ `roof` の材を持つ)と軒先・棟の際は測らない — 1.6 m 下の頂点を拾って野地が落ちた
    inside = lambda X, Z: abs(X) <= xr - 0.8 and 0.30 < abs(Z) < half - 0.30
    off = roof_dmin(o, inside, zf) - 0.01
    slab = noji_slab(name + "_noji", lambda X, Z: abs(X) <= xr and abs(Z) <= half, (-xr, xr, -half, half), zf, off)
    V.dedup_materials()
    o = V.join([o, slab], name)
    o.location = (0.0, 0.0, 0.0)
    return o, k, half, off


# ==========================================================================
# 部材
# ==========================================================================
def build_omoya(P, name):
    r = P["omoya"]
    hu, hv = r["W"] / 2.0, r["L"] / 2.0
    ms, uv = SH.mats()
    M = VM.Mesh()
    floor = G["kidanH"]
    eave = G["eaveOmoya"]
    half = hu + eave
    mean = (H["omoyaRidge"] - G["cap"] - H["omoyaEave"]) / half
    sori = SH.Sori(half, mean=mean)
    p = GR.palette()
    s = dict(eave=eave, gf=G["gf"])
    roof = SH.irimoya(name + "_roof", hu, hv, eave, H["omoyaEave"], G["gf"], p, sori)
    UE, VE = hu + eave, hv + eave
    nzf = SH.Nokizori(-UE, UE, -VE, VE)
    zf = lambda X, Z: H["omoyaEave"] + sori.z(max(0.0, min(UE - abs(X), VE - abs(Z)))) + nzf(-X, -Z)
    band = lambda X, Z: abs(X) <= UE - 0.02 and abs(Z) <= VE - 0.02 and not (abs(X) < hu - 0.15 and abs(Z) < hv - 0.15)
    off = roof_dmin(roof, lambda X, Z: band(X, Z) and min(UE - abs(X), VE - abs(Z)) > 0.05, zf) - 0.01
    slab = noji_slab(name + "_noji", lambda X, Z: abs(X) <= UE and abs(Z) <= VE and not (abs(X) < hu - 0.15 and abs(Z) < hv - 0.15),
                     (-UE, UE, -VE, VE), zf, off)
    drop = min(0.0, (off - 0.03) + 0.0525)           # 垂木の天端(面 −0.0525)を野地の下面まで下げる量
    keta_top = H["omoyaEave"] + sori.z(eave) - 0.16 + drop
    top = keta_top - G["ketaH"]
    us, vs = lin(-hu, hu, 4), lin(-hv, hv, 8)
    pts = [(uu, vs[0]) for uu in us] + [(uu, vs[-1]) for uu in us] + \
          [(us[0], vv) for vv in vs[1:-1]] + [(us[-1], vv) for vv in vs[1:-1]]
    posts(M, uv, pts, floor, keta_top)
    zdoor = (-9.0 - r["c"][1]) * K
    di = next(i for i in range(8) if vs[i] <= zdoor <= vs[i + 1])
    wall_run(M, uv, "u", -hv, -hu, hu, us, floor, top)
    wall_run(M, uv, "u", hv, -hu, hu, us, floor, top)
    wall_run(M, uv, "v", -hu, -hv, hv, vs, floor, top)
    wall_run(M, uv, "v", hu, -hv, hv, vs, floor, top, doors=(di,))
    MK = VM.Mesh()                                   # 桁(軒反りを掛けるので別体)
    for vv in (-hv, hv):
        SH.box3(MK, -hu - 0.12, hu + 0.12, vv - 0.08, vv + 0.08, top, keta_top, uv["wood_h"], SH.W, grain="u")
    for uu in (-hu, hu):
        SH.box3(MK, uu - 0.08, uu + 0.08, -hv - 0.12, hv + 0.12, top, keta_top, uv["wood_h"], SH.W, grain="v")
    body = M.to_object(name + "_body", ms)
    keta = MK.to_object(name + "_keta", ms)
    SH.nokizori_apply(keta, SH.Nokizori(-(hu + eave), hu + eave, -(hv + eave), hv + eave))
    taru = SH._taruki_obj(name, hu, hv, H["omoyaEave"], s, uv, ms, sori)
    taru.data.transform(Matrix.Translation((0.0, 0.0, drop))); taru.data.update()
    stones = kidan(hu, hv, {"+X": G["kidanOut"], "-X": 0.0, "+Z": 0.0, "-Z": G["kidanOut"]}, ("+X", "-X", "-Z"), name + "_kidan")
    o = finish(name, [body, keta, taru, roof, slab] + stones)
    a = half * G["gf"]
    info = dict(hu=hu, hv=hv, eave=eave, sori=sori, gableIn=a - eave, ridgeK=mean, door=(di, vs[di], vs[di + 1]),
                hb=H["omoyaEave"] + sori.z(a))
    print("[gokusho] 主屋 反りの平均勾配 %.3f / 瓦の谷 %.3f ⇒ 垂木・桁を %.3f 下げる / 桁の上端 %.3f / 妻壁は北の壁から %.3f 内 / 賄の口 柱間 %d(Z %.2f〜%.2f)"
          % (mean, off + 0.01, drop, keta_top, a - eave, di, vs[di], vs[di + 1]))
    return o, info


def build_tsugi(P, name, omoya_info):
    r = P["tsugi"]
    hu, hv = r["W"] / 2.0, r["L"] / 2.0
    ms, uv = SH.mats()
    M = VM.Mesh()
    floor = G["kidanH"]
    eave = G["eaveTsugi"]
    ext = omoya_info["gableIn"] + 0.10                # 主屋の北の妻壁の奥まで
    length = r["L"] + ext
    roof, k, half, off = kirizuma_roof(name + "_roof", length, r["W"], eave, 0.0, H["tsugiEave"], H["tsugiRidge"])
    # 大棟を北(Unity +Z)へ: Blender (x,y) → (y, −x)。北の端(Unity Z = +hv)= 元の x = +length/2 − ext… を合わせる
    roof.data.transform(Matrix.Translation((hv - length / 2.0, 0.0, 0.0)))
    roof.data.transform(Matrix.Rotation(math.radians(-90.0), 4, 'Z'))
    roof.data.update()
    surf = lambda v_abs: H["tsugiEave"] + k * (half - v_abs)
    keta_top = surf(hu) + off - 0.03                   # ⭐ 桁の天端 = 野地の下面(瓦を突き抜けない)
    top = keta_top - G["ketaH"]
    us, vs = lin(-hu, hu, 4), lin(-hv, hv, 3)
    pts = [(us[0], vv) for vv in vs[1:]] + [(us[-1], vv) for vv in vs[1:]] + [(uu, vs[-1]) for uu in us[1:-1]]
    posts(M, uv, pts, floor, keta_top)
    wall_run(M, uv, "v", -hu, -hv, hv, vs, floor, top)
    wall_run(M, uv, "v", hu, -hv, hv, vs, floor, top)
    wall_run(M, uv, "u", hv, -hu, hu, us, floor, top)
    for uu in (-hu, hu):                              # 桁(東西の軒の壁の上)
        SH.box3(M, uu - 0.08, uu + 0.08, -hv - ext, hv, top, keta_top, uv["wood_h"], SH.W, grain="v")
    # 北の妻壁(壁の通り)— 上端は屋根の裏なり
    vstrip_u(M, [-hu, 0.0, hu], hv - 0.04, hv + 0.04, lambda u: top, lambda u: surf(abs(u)) + off - 0.04, uv["wall"], SH.WC)
    body = M.to_object(name + "_body", ms)
    stones = kidan(hu, hv, {"+X": G["kidanOut"], "-X": 0.0, "+Z": 0.0, "-Z": 0.0}, ("+X", "-X", "+Z"), name + "_kidan")
    o = finish(name, [body, roof] + stones)
    print("[gokusho] 継ぎ 勾配 %.3f / 桁の上端 %.3f / 南へ主屋の中へ %.3f 伸ばす" % (k, keta_top, ext))
    return o, dict(hu=hu, hv=hv, k=k, ext=ext)


def build_wing(P, name, omoya_info):
    r = P["wing"]
    hu, hv = r["W"] / 2.0, r["L"] / 2.0
    ms, uv = SH.mats()
    M = VM.Mesh()
    floor = G["kidanH"]
    eave, ker = G["eaveWing"], G["keraba"]
    ext = omoya_info["hu"] - 0.30 - ker               # 主屋の棟の手前まで(+ケラバの出)
    length = r["W"] + ext
    roof, k, half, off = kirizuma_roof(name + "_roof", length, r["L"], eave, ker, H["wingEave"], H["wingRidge"])
    # 東の壁(Unity X +hu)= Blender x −hu。元の東の端 x = −length/2 を −hu へ
    roof.data.transform(Matrix.Translation((-hu + length / 2.0, 0.0, 0.0)))
    roof.data.update()
    surf = lambda v_abs: H["wingEave"] + k * (half - v_abs)
    keta_top = surf(hv) + off - 0.03
    top = keta_top - G["ketaH"]
    us, vs = lin(-hu, hu, 6), lin(-hv, hv, 3)
    # ⛔ 北西の隅の柱は主屋の北東の隅の柱と同じ位置 ⇒ 立てない(面が重なって z が争う)。南西は主屋の柱間の途中なので立てる
    pts = [(uu, vs[0]) for uu in us] + [(uu, vs[-1]) for uu in us[1:]] + [(us[-1], vv) for vv in vs[1:-1]]
    posts(M, uv, pts, floor, keta_top)
    wall_run(M, uv, "u", -hv, -hu, hu, us, floor, top)
    wall_run(M, uv, "u", hv, -hu, hu, us, floor, top)
    wall_run(M, uv, "v", hu, -hv, hv, vs, floor, top)
    for vv in (-hv, hv):
        SH.box3(M, -hu - ext, hu, vv - 0.08, vv + 0.08, top, keta_top, uv["wood_h"], SH.W, grain="u")
    vstrip_v(M, hu - 0.04, hu + 0.04, [-hv, 0.0, hv], lambda v: top, lambda v: surf(abs(v)) + off - 0.04, uv["wall"], SH.WC)
    body = M.to_object(name + "_body", ms)
    # ⭐ 南の出 0 — 透塀 `Sukibei_SS` が南面へ突き付く(指図 endButt)。北の出 0 — 拝殿の縁の外面
    stones = kidan(hu, hv, {"+X": G["kidanOut"], "-X": -G["kidanOut"], "+Z": 0.0, "-Z": 0.0},
                   ("+X", "-Z", "+Z"), name + "_kidan")
    o = finish(name, [body, roof] + stones)
    print("[gokusho] 腕 勾配 %.3f / 桁の上端 %.3f / 西へ主屋の中へ %.3f 伸ばす" % (k, keta_top, ext))
    return o, dict(hu=hu, hv=hv, k=k, ext=ext)


def finish(name, parts):
    V.dedup_materials()
    o = V.join([x for x in parts if x], name)
    SH.to_copper(o)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


# ==========================================================================
# 検算
# ==========================================================================
def mat_verts(o, names, world=False):
    idx = {i for i, m in enumerate(o.data.materials) if m and m.name.split('.')[0] in names}
    vs = set()
    for pg in o.data.polygons:
        if pg.material_index in idx:
            vs.update(pg.vertices)
    mw = o.matrix_world
    out = []
    for i in vs:
        c = (mw @ o.data.vertices[i].co) if world else o.data.vertices[i].co
        out.append((-c.x, c.z, -c.y))
    return out


def report(o, label, ridge_axis):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    cu = mat_verts(o, ("Doukawara",))
    j = 2 if ridge_axis == "Z" else 0
    core = [t[1] for t in cu if abs(t[j] - (max(q[j] for q in cu) + min(q[j] for q in cu)) / 2.0) < 0.6]
    print("GOKUSHO %s W(X)%.3f × H(Y)%.3f × D(Z)%.3f X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d mats=%s"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), min(xs), max(xs), min(ys), max(ys),
             min(zs), max(zs), tris, mats))
    print("  %s 大棟の上端(棟の中央 ±0.6 の帯)%.3f / 銅瓦の最低 %.3f" % (label, max(core), min(t[1] for t in cu)))
    bad = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bad else "⛔ %s" % bad))
    return not bad, tris, dict(ext=(min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)), ridge=max(core))


def soffit(o, rect, label, skip=(), band=0.7):
    """軒の帯(壁の外 〜 軒先)の下から真上へ — 銅瓦に先に当たる/空へ抜ける を数える。rect = (x0,x1,z0,z1) 壁の外形。"""
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    mats = o.data.materials
    x0, x1, z0, z1 = rect
    cu = miss = tot = 0
    n = 40
    for i in range(n + 1):
        for jj in range(n + 1):
            X = x0 - band + (x1 - x0 + 2 * band) * i / float(n)
            Z = z0 - band + (z1 - z0 + 2 * band) * jj / float(n)
            inside = x0 + 0.05 < X < x1 - 0.05 and z0 + 0.05 < Z < z1 - 0.05
            if inside or ("-X" in skip and X < x0) or ("+X" in skip and X > x1) or ("-Z" in skip and Z < z0) or ("+Z" in skip and Z > z1):
                continue                                   # 主屋の中へ伸ばして隠した側は数えない
            loc, nrm, idx, dist = bvh.ray_cast(Vector((-X, -Z, 1.5)), Vector((0, 0, 1)), 10.0)
            tot += 1
            if idx is None:
                miss += 1; continue
            m = mats[o.data.polygons[idx].material_index]
            if m and m.name.split('.')[0] == "Doukawara":
                cu += 1
    print("  検算 %s 軒裏(壁の外 %.2f の帯)真上の光線 %d: 銅瓦に先に当たる %d / 空へ抜ける %d %s"
          % (label, band, tot, cu, miss, "⭕" if cu == 0 and miss == 0 else "⛔"))
    return cu, miss


# ==========================================================================
# 組み上がり — 隣の棟を実 FBX で置いて当たりを測る
# ==========================================================================
def place(o, P, key_center):
    u, v = key_center
    uc, vc = P["omoya"]["c"]
    o.location = (-(u - uc) * K, -(v - vc) * K, 0.0)


def assembly(P, parts, render):
    om, ts, wg = parts
    place(om, P, P["omoya"]["c"]); place(ts, P, P["tsugi"]["c"]); place(wg, P, P["wing"]["c"])
    nb = {}
    for key, (u0, v0, du, dv, part) in NB.items():
        ob = import_abs(os.path.join(MD, part + ".fbx"), "nb_" + key)
        place(ob, P, (u0 + du / 2.0, v0 + dv / 2.0))
        nb[key] = ob
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()

    def world_verts(o):
        mw = o.matrix_world
        return [mw @ vt.co for vt in o.data.vertices]

    def bvh_world(o, with_mats=False):
        bm = bmesh.new(); bm.from_object(o, dg); bm.transform(o.matrix_world)
        bm.faces.ensure_lookup_table()
        mi = [f.material_index for f in bm.faces]
        t = BVHTree.FromBMesh(bm); bm.free()
        return (t, mi) if with_mats else t
    res = {}
    # (a) 東の腕の屋根 → 拝殿(真上の光線)
    th = bvh_world(nb["haiden"])
    gap = None
    for w in world_verts(wg):
        if w.z < 2.5:
            continue
        h = th.ray_cast(Vector((w.x, w.y, w.z + 1e-4)), Vector((0, 0, 1)), 10.0)
        if h[0] is not None and (gap is None or h[0].z - w.z < gap[0]):
            gap = (h[0].z - w.z, w.z, h[0].z)
    res["wing_haiden"] = gap
    # (b) 北の継ぎ → 本殿(真上)・作り合い/幣殿(平面の離れ・Y>2.5 の材どうし)
    tb = bvh_world(nb["honden"])
    gap = None
    for w in world_verts(ts):
        if w.z < 2.5:
            continue
        h = tb.ray_cast(Vector((w.x, w.y, w.z + 1e-4)), Vector((0, 0, 1)), 10.0)
        if h[0] is not None and (gap is None or h[0].z - w.z < gap[0]):
            gap = (h[0].z - w.z, w.z, h[0].z)
    res["tsugi_honden"] = gap
    tsN = max(-w.y for w in world_verts(ts) if w.z > 2.5)           # 継ぎの北の最も出た点(Unity Z)
    xs_t = [-w.x for w in world_verts(ts)]
    band_s = {}
    for key in ("tsukuriai", "heiden"):
        vz = [(-w.y, w.z) for w in world_verts(nb[key]) if w.z > 2.5 and min(xs_t) < -w.x < max(xs_t)]
        band_s[key] = (min(z for z, y in vz), min(y for z, y in vz)) if vz else None
    res["tsugi_band"] = (tsN, band_s)
    # (c) 谷の頭: 腕の棟の線・継ぎの棟の線を主屋の屋根へ下ろし、主屋の屋根面 = 棟の高さになる所
    tm, tmi = bvh_world(om, with_mats=True)
    cu_idx = {i for i, m in enumerate(om.data.materials) if m and m.name.split('.')[0] == "Doukawara"}

    def copper_down(x, y):
        z = 20.0
        for _ in range(12):                              # 銅瓦以外(破風・袖の木部)は通り抜けて次を探す
            h = tm.ray_cast(Vector((x, y, z)), Vector((0, 0, -1)), 30.0)
            if h[0] is None:
                return None
            if tmi[h[2]] in cu_idx:
                return h[0].z
            z = h[0].z - 1e-3
        return None

    def valley(line_pts, ridge_top):
        for (x, y) in line_pts:
            zc = copper_down(x, y)
            if zc is not None and zc >= ridge_top - G["capK"]:
                return (x, y, zc)
        return None
    # 継ぎ → 主屋(真上の光線)
    gap = None
    for w in world_verts(ts):
        if w.z < 3.0 or -w.y < P["omoya"]["L"] / 2.0 + 0.05:      # 主屋の中へ伸ばして隠した部分は数えない
            continue
        h = tm.ray_cast(Vector((w.x, w.y, w.z + 1e-4)), Vector((0, 0, 1)), 10.0)
        if h[0] is not None and (gap is None or h[0].z - w.z < gap[0]):
            gap = (h[0].z - w.z, w.z, h[0].z)
    res["tsugi_omoya"] = gap
    uc, vc = P["omoya"]["c"]
    hu_o = P["omoya"]["W"] / 2.0
    wing_y = -(P["wing"]["c"][1] - vc) * K
    east_wall_x = -hu_o
    pts = [(east_wall_x - 1.0 + 0.02 * i, wing_y) for i in range(0, int((hu_o + 1.0) / 0.02))]
    vh = valley(sorted(pts, key=lambda p: p[0]), H["wingRidge"])       # Blender x 小 = 東
    res["valley_wing"] = None if vh is None else ((-vh[0]) - hu_o, vh[2])
    res["valley_tsugi"] = None
    # 透塀の t の端を建物へ突き付けて当てる(指図 runs の endButt)。突き付けの面 = 柱の外面(壁の芯 + 柱の半分)
    pr = G["post"] / 2.0
    butt = []
    for part, s_mm, ends, target, u_run, v_run, face in (
            ("Sanno_Sukibei_2423_nt", 2423, "nt", ts, None, -1.1634, "継ぎの西面"),
            ("Sanno_Sukibei_2889_tc", 2889, "tc", wg, -34.3181, None, "腕の南面")):
        fp = os.path.join(MD, part + ".fbx")
        if not os.path.exists(fp):
            continue
        fo = import_abs(fp, "fence_" + part)
        sm = s_mm / 1000.0
        if v_run is not None:           # 西から東へ走り、+X の端(t)が継ぎの西の柱の外面
            X = (PLAN["omoyaU"][0] - uc) * K - pr - sm / 2.0
            Z = (v_run - vc) * K
            fo.rotation_euler = (0.0, 0.0, 0.0)
        else:                           # 北から南へ走り、−X の端(t)が腕の南の柱の外面
            X = (u_run - uc) * K
            Z = (PLAN["wingS"] - vc) * K - pr - sm / 2.0
            fo.rotation_euler = (0.0, 0.0, math.radians(-90.0))
        fo.location = (-X, -Z, 0.0)
        bpy.context.view_layer.update()
        tb2 = bvh_world(target)
        pen, near = 0.0, None
        for w in world_verts(fo):
            hit = tb2.find_nearest(w, 0.5)
            if hit[0] is None:
                continue
            dvec = w - hit[0]
            inside = dvec.dot(hit[1]) < -1e-4
            if inside:
                pen = max(pen, hit[3])
            elif near is None or hit[3] < near:
                near = hit[3]
        butt.append((part, face, pen, near))
        bpy.data.objects.remove(fo, do_unlink=True)
    res["butt"] = butt
    out = []
    if render:
        V.hook_textures()
        os.makedirs(SHOT, exist_ok=True)
        bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, -0.005))
        cx, cy = 0.0, 0.0

        def one(cam, look, fn, res_=(1600, 1100)):
            V.studio(cam, look, res=res_)
            f = os.path.join(SHOT, "sanno_gokusho_%s.png" % fn)
            V.render(f); out.append(f)
        wx, wy = -(P["wing"]["c"][0] - uc) * K, -(P["wing"]["c"][1] - vc) * K
        tx, ty = -(P["tsugi"]["c"][0] - uc) * K, -(P["tsugi"]["c"][1] - vc) * K
        one((wx - 14.0, wy + 16.0, 11.0), (wx + 3.0, wy - 2.0, 3.0), "se_oblique")
        one((wx - 5.0, wy + 7.0, 4.5), (-hu_o, wy, 4.3), "valley_wing", (1400, 1100))
        one((tx + 10.0, ty - 9.0, 9.0), (tx, ty - 1.0, 3.2), "nw_tsugi")
        one((tx + 5.5, ty - 1.0, 2.6), (tx - 0.5, ty - 3.6, 3.4), "tsugi_band", (1400, 1100))
        one((20.0, 14.0, 13.0), (0.0, -2.0, 2.5), "sw_oblique")
        one((-hu_o - 1.2, 3.0, 1.3), (-hu_o + 0.3, 1.0, 3.6), "soffit_east", (1400, 1100))
    return res, out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    P = plan()
    names = dict(omoya="Sanno_Gokusho_Omoya_%dx%d" % (round(P["omoya"]["W"] * 1000), round(P["omoya"]["L"] * 1000)),
                 tsugi="Sanno_Gokusho_Tsugi_%dx%d" % (round(P["tsugi"]["W"] * 1000), round(P["tsugi"]["L"] * 1000)),
                 wing="Sanno_Gokusho_Higashi_%dx%d" % (round(P["wing"]["W"] * 1000), round(P["wing"]["L"] * 1000)))
    V.reset()
    om, oi = build_omoya(P, names["omoya"])
    ts, ti = build_tsugi(P, names["tsugi"], oi)
    wg, wi = build_wing(P, names["wing"], oi)
    ok = True
    for o, lab, ax, info, sk, bd in ((om, "主屋", "Z", oi, ("+Z",), G["eaveOmoya"] - 0.05),
                                     (ts, "継ぎ", "Z", ti, ("-Z", "+Z"), G["eaveTsugi"] - 0.05),
                                     (wg, "腕", "X", wi, ("-X",), G["keraba"] - 0.05)):
        good, tris, meas = report(o, lab, ax)
        cu, miss = soffit(o, (-info["hu"], info["hu"], -info["hv"], info["hv"]), lab, sk, bd)
        ok = ok and good and cu == 0 and miss == 0
    res, shots = assembly(P, (om, ts, wg), "--render" in argv)
    print("  突き付け 継ぎの棟 %.2f %s 主屋の北の妻の裾 %.3f ⇒ %s" % (
        H["tsugiRidge"], ">" if H["tsugiRidge"] - G["capK"] > oi["hb"] else "≤", oi["hb"],
        "妻壁(北の壁から %.3f 内)へ突き付け" % oi["gableIn"] if H["tsugiRidge"] - G["capK"] > oi["hb"] else "寄棟面の下へ潜る"))
    g = res["tsugi_omoya"]
    print("  当たり 北の継ぎ → 主屋(真上): %s" % ("真上に材なし" if g is None else "最小の離れ %.3f(継ぎ Y %.3f → 主屋 Y %.3f)" % g))
    g = res["wing_haiden"]
    print("  当たり 東の腕の屋根 → 拝殿の軒裏: %s" % ("真上に材なし" if g is None else "最小の離れ %.3f(腕 Y %.3f → 拝殿 Y %.3f)" % g))
    g = res["tsugi_honden"]
    print("  当たり 北の継ぎ → 本殿の屋根: %s" % ("真上に材なし" if g is None else "最小の離れ %.3f(継ぎ Y %.3f → 本殿 Y %.3f)" % g))
    tsN, bs = res["tsugi_band"]
    for key, v in bs.items():
        if v:
            print("  当たり 北の継ぎの北端 Z %.3f ↔ %s の南の出(Y>2.5)Z %.3f・その最低 Y %.3f ⇒ 平面の離れ %.3f"
                  % (tsN, key, v[0], v[1], tsN - v[0] if False else v[0] - tsN))
    vw, vt = res["valley_wing"], res["valley_tsugi"]
    print("  谷 腕の棟が主屋の屋根面に入る所: %s" % ("—" if vw is None else "主屋の東の壁から内へ %.3f・高さ %.3f" % (-vw[0], vw[1])))
    print("  谷 継ぎの棟が主屋の北の端に入る所: %s" % ("—" if vt is None else "主屋の北の壁から内へ %.3f・高さ %.3f" % (vt[0], vt[1])))
    for part, face, pen, near in res.get("butt", []):
        print("  突き付け 透塀 %s → %s(柱の外面): めり込み %.3f / 最小の離れ %s" % (part, face, pen, "—" if near is None else "%.3f" % near))
    for f in shots:
        print("RENDER " + f)
    if not ok and "--allow" not in argv:
        raise SystemExit("[gokusho] ⛔ 材か軒裏の検算に落ちた")
    if "--no-export" not in argv:
        for o in (om, ts, wg):
            o.location = (0.0, 0.0, 0.0)
            path = os.path.join(OUT, o.name + ".fbx")
            V.export_fbx([o], path)
            print("[gokusho] 書き出し %s" % path)


if __name__ == "__main__":
    main()
