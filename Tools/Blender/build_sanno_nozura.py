"""山王社の前庭の縁の土留め — **野面の乱積み**(施主が試作 A を採った・2026-09-24)の本番モジュール。

    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall  [--grade=0] [--h=1.2] [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kiri  [--render]     # 根石の打ち切り(沈む駒)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- sode  [--only=男坂] [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- mikiri [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- all --render
    blender --background --python Tools/Blender/build_sanno_nozura.py -- check                 # 継ぎ目の一致を数で検める
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado [--h=1.5] [--render]   # 出隅 90° の隅の駒
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado-check [--h=1.5]  # 隅の駒の腕の先 = 直線の切り口
    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall --grade=0.22 --h=1.5  # 段の境の勾配の駒(± 両方)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- dan --render          # 段の境の並べ焼き

試作は `proto_sanno_dodome.py`(絵だけ)。石の形(Voronoi の割り・割肌の面・円弧で切る頭・
面取り)はそこから起こし直した。⛔ 在庫に野面石・玉石が無い(試作の依頼時に在庫方が確認)ので新造。

━━━ 1. 壁の駒 `Sanno_Nozura_H<見付mm>_G<勾配‰>_<a|b|c|d>.fbx`(Models/Sanno)━━━━━━━━━━━━━━
【ピッチ】1間 = 1.818m。**両端の石(端の柱石の列)は全種類・全段で同じ形** ⇒ どの駒どうしでも継げる。
  端の石は継ぎ目の線(X = ±0.909)で**石の途中を切って**あり、隣の駒の半分と合わさって1石に見える
  (⛔ 継ぎ目で竪目地を通さない)。種類 a〜d は中の石だけが違う。並べるときは順に振る(繰り返しを隠す)。
【見付の段】0.15(根石1段)/ 0.30 / 0.60 / … / 2.40。**割りは天端から下へ測った一つの型**で、段の違いは
  下をどこで切るかだけ ⇒ **段の違う駒どうしも天端の線で継げる**(天端が揃えば目地も揃う)。
  見付 2.3 の所は 2.4 を 0.1 沈めて据える(下は地中)。
【勾配】駒を鉛直に剪断して天端を勾配に載せる(石段の袖と同じ・段に折らない)。G = 天端が Unity +X へ
  1m あたり上がる量(‰)。焼いてあるのは G0 と根石の打ち切り(H0150 の G±180)。他の勾配は `--grade=` で足す。
【軸(Unity)】幅 = X / 高さ = Y / 厚み = Z、**見え面 = +Z**。面は 3分(0.3)の法 — **天端の線から測る**
  (段の違う駒どうしで面が食い違わないように)。
【ピボット】1間の中心(X=0)・**床レベル = 中心での天端 − 見付**(Y=0)・Z=0 は**天端の線での面**。
  ⇒ 床での面(法尻)は Z = +0.3×見付 に出る。石は床の 0.20 下まで根入れ(地中)。
  頭は天端の線の ±0.08 で不揃い。芝の肩は Unity の地形側で被せる前提。
【材】`Kirishi` / `Danishi`(山王の切石と同じ暖かい灰。石ごとに 7:3 で振り、色の個体差にする)。
  ⛔ 新規マテリアルなし。UV は石ごとの箱投影(1.05m で1枚・石ごとに位相をずらす)。
  裏に目地の奥を塞ぐ板(`Danishi`)を 0.12 奥に張る ⇒ 目地から空が抜けない。

━━━ 2. 根石の打ち切り = `H0150` の `G±180` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  見付 0.2 未満で壁を終える駒。頭が 1.818m の間に 0.33 下がるので、高い側の天端を隣(見付 0.30)に
  合わせれば先端の石は床へ沈む。G+180 = +X へ上がる(−X 側の端に置く)/ G−180 = +X へ下がる(+X 側の端)。

━━━ 2b. 出隅 90° の隅の駒 `Sanno_Nozura_Kado90_H<見付mm>_<a|b>.fbx`(2026-09-25・本殿の西の土留め)━━━━━
  腕1 = 稜線から −X へ 0.909(見え面 +Z)/ 腕2 = 稜線から −Z へ 0.909(見え面 +X)。高い側は X ≤ 0・Z ≤ 0。
  ピボット = **天端の線どうしの交点(稜線)・床レベル(天端 − 見付)**。腕の先の切り口 X = −0.909 / Z = −0.909 は
  直線の駒の切り口と同じ(端の石は同じ種・同じ形)⇒ 直線の駒をそのまま継ぐ。面は法で下ほど前へ出るので、
  割りは「稜線から面に沿って測る σ」で起こし(深さ u の面の幅 = 0.909 + 0.3·(−u))、稜線に跨る石だけ σ=0 で
  割線を入れて 90° に折る(控えは留めの線 x = z へ剪断・隠れる)。行ごとに稜線に跨る石を一つ置く ⇒ 竪目地が
  稜線を通らず、隅だけの石の柱(算木)にもならない。出隅は対称なので一種で両回り(yaw で腕を選ぶ)。

━━━ 2c. 段の境の勾配の駒 = `H1500` の `G±220` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  帯の面 29.65 → 29.25 の差 0.40 を 1間で流す(0.40 / 1.818 = 0.22)。見付は**高い側の端**で取る
  (29.65 − 境内 28.3 = 1.35 ⇒ 1.50)。中心の見付で取ると(1.15 ⇒ 1.20)高い側の根入れが 0.05 しか残らない。

━━━ 3. 石段の袖 `IshidanSodeNozura_<蹴上>_<踏面>_<a|b>.fbx`(Models/Kaidan)━━━━━━━━━━━━━
  **`Own.IshidanSode` と同じ局所座標・ピボット・接する面**(厚み X ±0.30 で両面とも乱積み・
  X について鏡像対称 / +Z = 坂下 / 天端 Y = 0.30 + (踏面/2 − Z)·蹴上/踏面 / 下端 = 天端 − 2.20 /
  走り Z ±踏面/2)。⇒ ビルダーは関数を差し替えるだけで据え方は変わらない。石は X = ±0.30 の面を越えない。
  頭の不揃いは ±2.5cm・頭の丸みは R1.2〜2.0(±8cm・R0.3 だと石段に沿う天端が鋸の歯に見えた)。笠石は持たない。
  ⛔ 曲がる女坂の留めの駒(`IshidanSodeMiter`)は未だ乱積みで起こしていない。

━━━ 4. 見切り石 `Sanno_Nozura_Mikiri.fbx` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  男坂の下で城の石垣と継ぐための大きな野面石1点。面 0.86 × 0.80・控え 0.90。
  ピボット = 面の芯・床レベル・Z=0 は天端での面(壁の駒と同じ取り方)。
"""
import bpy, bmesh, sys, os, math, random
import mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
POS = [a for a in ARGS if not a.startswith("--")]
OPT = dict((a[2:].split("=", 1) + [""])[:2] for a in ARGS if a.startswith("--"))
RENDER = "render" in OPT

OUT_WALL = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
OUT_SODE = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Kaidan"))
SHOT = os.path.join(V.REPO, "Screenshots")
MATDIR = os.path.join(V.REPO, "Assets", "Edo", "Materials", "Sanno")

L = 1.818                 # 1間
TIERS = [0.15, 0.30, 0.60, 0.90, 1.20, 1.50, 1.80, 2.10, 2.40]
VARIANTS = "abcd"
BURY = 0.20               # 床より下の根入れ
DEEP = max(TIERS) + BURY  # 型の深さ(天端から)
BATTER = 0.3
HEAD = 0.08               # 頭の不揃い ±
KIRI_G = 0.180            # 根石の打ち切りの勾配(1間で 0.33 下がる ⇒ 先端の頭が床に沈む)
TILE = 1.05               # UV 1枚の実寸

# 石段の袖(`build_sanno_buzai` の SODE_* と同じ値。⛔ 変えると差し替えで据えがずれる)
SODE_HALF = 0.30
SODE_HT = 0.30
SODE_DEPTH = 2.20


# ------------------------------------------------------------------ 2D の道具
def clip(poly, n, c):
    """半平面 dot(p, n) <= c で凸多角形を切る"""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        dp = p[0] * n[0] + p[1] * n[1] - c
        dq = q[0] * n[0] + q[1] * n[1] - c
        if dp <= 0:
            out.append(p)
        if (dp < 0) != (dq < 0) and abs(dp - dq) > 1e-12:
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def area(poly):
    a = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        a += p[0] * q[1] - q[0] * p[1]
    return a / 2


def hull(pts):
    """凸包(反時計回り)"""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def head_arc(poly, sx, top, R):
    """頭を半径 R の円弧(5本の接線)で切る。u は上向き(0 = 天端の線)"""
    for a in (-0.75, -0.4, 0.0, 0.4, 0.75):
        n = (-math.sin(a), math.cos(a))
        cx, cu = sx, top - R
        poly = clip(poly, n, n[0] * cx + n[1] * cu + R)
        if len(poly) < 3:
            return poly
    return poly


def separate(poly, seed, obst, g):
    """凸の障害 obst から、種 seed の側へ g/2 離して切る(分離線 = 種が最も外に出る辺)"""
    best, bn, bc = -1e9, None, None
    m = len(obst)
    ccw = area(obst) > 0
    for i in range(m):
        p, q = obst[i], obst[(i + 1) % m]
        ex, ey = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(ex, ey)
        if ln < 1e-9:
            continue
        n = (ey / ln, -ex / ln) if ccw else (-ey / ln, ex / ln)     # 外向き
        d = (seed[0] - p[0]) * n[0] + (seed[1] - p[1]) * n[1]
        if d > best:
            best, bn, bc = d, n, p[0] * n[0] + p[1] * n[1]
    if bn is None:
        return poly
    # 残すのは dot(x, n) >= bc + g/2  ⇔  dot(x, -n) <= -(bc + g/2)
    return clip(poly, (-bn[0], -bn[1]), -(bc + g / 2))


# ------------------------------------------------------------------ 割り(天端から下へ一つの型)
def voronoi_cell(i, pts, g, box):
    """pts[i] の Voronoi 領域(目地 g)。box = (s0, s1, u0, u1)"""
    sx, su = pts[i]
    poly = [(box[0], box[2]), (box[1], box[2]), (box[1], box[3]), (box[0], box[3])]
    for j, (tx, tu) in enumerate(pts):
        if i == j or abs(tx - sx) > 1.3 or abs(tu - su) > 1.0:
            continue
        dx, du = tx - sx, tu - su
        d = math.hypot(dx, du)
        if d < 1e-9:
            continue
        n = (dx / d, du / d)
        poly = clip(poly, n, n[0] * (sx + tx) / 2 + n[1] * (su + tu) / 2 - g / 2)
        if len(poly) < 3:
            break
    return poly


def boundary_column(seed, depth, gw, cmax, rh=(0.26, 0.40), head=HEAD, rr=(0.16, 0.32)):
    """継ぎ目(s=0)に跨る端の石の列と、その左右の「番人」の種。**全種類・全段で同じ**(seed だけで決まる)。
    端の石は **端の種 + 番人の種だけ**の Voronoi 領域 ⇒ 中の石(種類ごとに違う)に形を左右されない。
    番人は s = c ± gw 付近に置き、中の石の種は番人より外にしか置かない。
    返す: (cols [(poly(s,u), key)], guards [(s,u)], bseeds [(s,u)])。u は上向き・天端 0。"""
    rng = random.Random(seed)
    bseeds, guards, heads = [], [], []
    u = 0.0
    k = 0
    while u > -depth - 0.3:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        c = (1 if k % 2 == 0 else -1) * rng.uniform(0.02, cmax)
        bseeds.append((c, uc))
        guards.append((c - gw * rng.uniform(0.85, 1.15), uc + rng.uniform(-0.08, 0.08)))
        guards.append((c + gw * rng.uniform(0.85, 1.15), uc + rng.uniform(-0.08, 0.08)))
        heads.append((rng.uniform(-head, head), rng.uniform(*rr), rng.uniform(0.022, 0.036)))
        u -= h_
        k += 1
    pts = bseeds + guards
    cols = []
    for ci in range(len(bseeds)):
        j8, R, g = heads[ci]
        poly = voronoi_cell(ci, pts, g, (-1.0, 1.0, -depth - 0.6, HEAD + 0.12))
        poly = head_arc(poly, bseeds[ci][0], j8, R) if len(poly) >= 3 else poly
        if len(poly) >= 3:
            cols.append((poly, "B%d" % ci))
    return cols, guards, bseeds


def layout(span, depth, bseed, vseed, wr=(0.25, 0.60), gw=0.40, bcmax=0.10, rh=(0.26, 0.40),
           head=HEAD, rr=(0.16, 0.32)):
    """1駒ぶんの石の輪郭(s ∈ [−span/2, +span/2]・u ∈ [−depth, +HEAD])。
    端の石の列(両端で同じ形)+ 番人 + 中の石(vseed ごとに違う)。返す [(poly, kind, key)]
    kind = 'B-' / 'B+'(左右の端の石)/ 'I'。key は石の乱数の種(端の石は左右で同じ)。"""
    cols, guards, bseeds = boundary_column(bseed, depth, gw, bcmax, rh, head, rr)
    ends, fixed, bpts = [], [], []
    for side, off in (("B-", -span / 2), ("B+", span / 2)):
        for poly, key in cols:
            ends.append(([(p[0] + off, p[1]) for p in poly], side, key))
        bpts += [(p[0] + off, p[1]) for p in bseeds]
        fixed += [(p[0] + off, p[1]) for p in guards if -span / 2 < p[0] + off < span / 2]
    rng = random.Random(vseed)
    var = []
    u = 0.0
    k = 0
    while u > -depth - 0.05:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        s = -span / 2 - rng.uniform(0, 0.3) - (0.2 if k % 2 else 0)
        while s < span / 2 + 0.3:
            w = rng.uniform(*wr)
            sx = s + w / 2 + rng.uniform(-0.05, 0.05)
            su = uc + rng.uniform(-0.05, 0.05)
            # 番人より外(継ぎ目から gw×1.3 以上)にだけ置く
            if -span / 2 + gw * 1.3 < sx < span / 2 - gw * 1.3 and su < -0.05:
                var.append((sx, su))
            s += w
        u -= h_
        k += 1
    seeds = fixed + var
    allp = seeds + bpts
    cells = []
    for i, (sx, su) in enumerate(seeds):
        g = rng.uniform(0.022, 0.040)
        poly = voronoi_cell(i, allp, g, (sx - 1.0, sx + 1.0, -depth - 0.3, HEAD + 0.12))
        if len(poly) < 3:
            continue
        poly = clip(poly, (1, 0), span / 2 - 0.02)
        poly = clip(poly, (-1, 0), span / 2 - 0.02)
        for op, side, key in ends:        # 端の石とわずかに重なる所を落とす
            if len(poly) < 3:
                break
            cx, cu = centroid(op)
            if abs(cx - sx) < 1.0 and abs(cu - su) < 1.0:
                poly = separate(poly, (sx, su), op, g)
        if len(poly) < 3:
            continue
        poly = head_arc(poly, sx, rng.uniform(-head, head), rng.uniform(*rr))
        if len(poly) < 3 or area(poly) < 0.008:
            continue
        cells.append((poly, "I", "I%d" % i if i >= len(fixed) else "G%d" % i))
    return ends + cells


# ------------------------------------------------------------------ 材
def _stone_material(name, tint):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)          # ⛔ Unity 側の同名 .mat へ remap される入れ物
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs['Roughness'].default_value = 0.92
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = bpy.data.images.load(os.path.join(MATDIR, "T_Kirishi_Albedo.png"), check_existing=True)
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1
    nt.links.new(ti.outputs['Color'], mx.inputs[1]); mx.inputs[2].default_value = (tint, tint, tint, 1)
    nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])
    return m


def materials():
    return _stone_material("Kirishi", 1.0), _stone_material("Danishi", 0.80)


# ------------------------------------------------------------------ 石の塊
def stone_obj(name, poly, key_rng, P, depth, face_prot=(-0.02, 0.045), double=None):
    """(s,u) の輪郭 → 野面の塊。P(s, u, d) が 3D を返す(d = 面から奥へ)。
    double = 厚み T なら両面を割肌にする(袖)。形の乱数は key_rng だけで決まる(端の石は左右で同じ)。"""
    rng = key_rng
    cs, cu = centroid(poly)
    prot = rng.uniform(*face_prot)
    ta, tb = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.12)
    bm = bmesh.new()

    def face_d(s, u):
        return -prot + ta * (s - cs) - tb * (u - cu)

    n = len(poly)
    F = [bm.verts.new(P(s, u, face_d(s, u) + rng.uniform(-0.012, 0.018))) for (s, u) in poly]
    M = [bm.verts.new(P(cs + (s - cs) * 1.03, cu + (u - cu) * 1.03, 0.13 - prot)) for (s, u) in poly]
    I = []
    for (s, u) in poly:
        ds, du = s - cs, u - cu
        dd = math.hypot(ds, du) or 1
        k = max(dd - 0.06, dd * 0.45) / dd
        si, ui = cs + ds * k, cu + du * k
        I.append(bm.verts.new(P(si, ui, face_d(si, ui) - rng.uniform(0.01, 0.03))))
    C = bm.verts.new(P(cs + rng.uniform(-0.04, 0.04), cu + rng.uniform(-0.03, 0.03),
                       face_d(cs, cu) - rng.uniform(0.015, 0.045)))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((C, I[i], I[j])))
        faces.append(bm.faces.new((I[i], F[i], F[j], I[j])))
        faces.append(bm.faces.new((F[i], M[i], M[j], F[j])))
    if double is None:
        Bk = [bm.verts.new(P(cs + (s - cs) * 0.80, cu + (u - cu) * 0.80 - 0.03, depth - prot)) for (s, u) in poly]
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((M[i], Bk[i], Bk[j], M[j])))
        faces.append(bm.faces.new(list(reversed(Bk))))
    else:
        T = double
        prot2 = rng.uniform(*face_prot)
        ta2, tb2 = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.12)

        def back_d(s, u):
            return T + prot2 - ta2 * (s - cs) + tb2 * (u - cu)
        F2 = [bm.verts.new(P(s, u, back_d(s, u) - rng.uniform(-0.012, 0.018))) for (s, u) in poly]
        M2 = [bm.verts.new(P(cs + (s - cs) * 1.03, cu + (u - cu) * 1.03, T - 0.13 + prot2)) for (s, u) in poly]
        C2 = bm.verts.new(P(cs + rng.uniform(-0.04, 0.04), cu, back_d(cs, cu) + rng.uniform(0.015, 0.04)))
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((M[i], M2[i], M2[j], M[j])))
            faces.append(bm.faces.new((M2[i], F2[i], F2[j], M2[j])))
            faces.append(bm.faces.new((F2[i], C2, F2[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    bv = o.modifiers.new("bevel", 'BEVEL')
    bv.width = 0.04; bv.segments = 2; bv.limit_method = 'ANGLE'
    bv.angle_limit = math.radians(28); bv.use_clamp_overlap = True; bv.profile = 0.6
    V.sel([o])
    bpy.ops.object.modifier_apply(modifier="bevel")
    return o


def box_uv(o, ofs):
    """石ごとの箱投影。座標は**石の重心から**測る(継ぎ目で切った端の石が左右の駒で同じ UV になる)"""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    c = sum((v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
    for p in me.polygons:
        nx, ny, nz = (abs(x) for x in p.normal)
        for li in p.loop_indices:
            q = me.vertices[me.loops[li].vertex_index].co - c
            if nz >= nx and nz >= ny:
                a, b = q.x, q.y
            elif nx >= ny:
                a, b = q.y, q.z
            else:
                a, b = q.x, q.z
            uvl[li].uv = (a / TILE + ofs[0], b / TILE + ofs[1])


def build_stones(cells, P, mats, depth_rng=(0.45, 0.75), double=None, face_prot=(-0.02, 0.045), tag=""):
    objs = []
    kir, dan = mats
    for poly, kind, key in cells:
        # ⭐ 端の石は key が左右で同じ ⇒ 形・控え・材・UV の位相まで同じ(継ぎ目で合わさる)
        rng = random.Random("nozura|%s|%s" % (tag, key))
        d = rng.uniform(*depth_rng)
        o = stone_obj("st_" + key + kind, poly, rng, P, d, face_prot=face_prot, double=double)
        o.data.materials.append(kir if rng.random() < 0.7 else dan)
        box_uv(o, (rng.random(), rng.random()))
        objs.append(o)
    return objs


def bisect_keep(o, co, no):
    """平面 co・法線 no の**裏側**(dot(x-co, no) <= 0)だけ残して口を塞ぐ。
    塞いだ口(小口)の UV は補間の崩れで縞になる(見切り石の脇で実見)⇒ 平面へ投影し直す。"""
    V.sel([o])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=co, plane_no=no, use_fill=True, clear_outer=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    me = o.data
    uvl = me.uv_layers.active.data
    n = Vector(no).normalized()
    c = Vector(co)
    ax = max(range(3), key=lambda k: abs(n[k]))
    a_, b_ = [k for k in range(3) if k != ax]
    for p in me.polygons:
        if p.normal.dot(n) > 0.99 and abs((p.center - c).dot(n)) < 1e-4:
            for li in p.loop_indices:
                q = me.vertices[me.loops[li].vertex_index].co
                uvl[li].uv = (q[a_] / TILE + 0.37, q[b_] / TILE + 0.11)


# ------------------------------------------------------------------ 壁の駒
def wall_name(h, g, v):
    gm = int(round(g * 1000))
    return "Sanno_Nozura_H%04d_G%s%03d_%s" % (int(round(h * 1000)), "+" if gm >= 0 else "-", abs(gm), v)


def wall_P(h, g):
    """(s = Unity X, u = 天端からの上向き, d = 面から奥へ) → Blender。
    Unity X = −Blender X / Unity Y = Blender Z / Unity Z = −Blender Y(README 書き出しの規約)。
    天端 Y = h + g·s。面(見え面 +Z)は天端の線から 3分で前へ出る: Unity Z = 0.3·(−u) − d。"""
    def P(s, u, d):
        return (-s, -(BATTER * (-u) - d), h + g * s + u)
    return P


def backing(name, h, g, mat):
    """目地の奥を塞ぐ板(面から 0.12 奥・天端の 0.12 下から床の下まで)"""
    bm = bmesh.new()
    P = wall_P(h, g)
    vs = []
    for s in (-L / 2, L / 2):
        for u in (-0.12, -(h + BURY)):
            vs.append(bm.verts.new(P(s, u, 0.12 + BATTER * 0)))
    # 法に沿わせる(u ごとに面が前へ出る分を足す)は P が持つ
    bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    # 見え面(−Blender Y)へ向ける
    me.update()
    if me.polygons[0].normal.y > 0:
        me.flip_normals()
    box_uv(o, (0.3, 0.7))
    return o


_LAYOUT = {}


def wall_cells(v):
    if v not in _LAYOUT:
        _LAYOUT[v] = layout(L, DEEP, "nozura-wall-B", "nozura-wall-" + v)
    return _LAYOUT[v]


def make_wall(h, g, v):
    V.reset()
    mats = materials()
    cells = []
    for poly, kind, key in wall_cells(v):
        p2 = clip(poly, (0, -1), h + BURY)            # u >= −(h+BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells.append((p2, kind, key))
    objs = build_stones(cells, wall_P(h, g), mats, tag="wall")
    objs.append(backing("back", h, g, mats[1]))
    name = wall_name(h, g, v)
    o = V.join(objs, name)
    bisect_keep(o, (-L / 2, 0, 0), (-1, 0, 0))        # Unity X ≤ +L/2 ⇔ Blender X ≥ −L/2
    bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))
    V.set_origin(o, (0, 0, 0))
    return o, name, len(cells)


# ------------------------------------------------------------------ 出隅 90° の隅の駒
KADO_VARIANTS = "ab"
KADO_TIERS = [t for t in TIERS if t >= 0.30]


def kado_name(h, v):
    return "Sanno_Nozura_Kado90_H%04d_%s" % (int(round(h * 1000)), v)


def cbat(u):
    """天端の線から u(上向き)の所で、法が面を前へ出す量"""
    return BATTER * (-u)


def kado_layout(v, depth=DEEP):
    """出隅の駒の割り。**σ = 面に沿って隅(稜線)から測った距離**(腕1 = −・腕2 = +)。
    面は法で下ほど前へ出るので、深さ u での面の幅は腕ごとに 0.909 + c(u)(c = 0.3·(−u))。
    ⇒ 継ぎ目の線は σ 空間で斜め(σ = ±(0.909 + c(u)))。端の石は直線の駒と**同じ種・同じ形**
    (`boundary_column("nozura-wall-B")`)を σ 空間へ剪断して置く(3D では剪断が消え、直線の駒の端の石と一致する)。
    隅(σ ≈ 0)には稜線に跨る石の列を置く ⇒ 竪目地が稜線を通らない。種の符号はばらばら(算木の互い違いにしない)。"""
    rh, gw = (0.26, 0.40), 0.40
    cols, guards, bseeds = boundary_column("nozura-wall-B", depth, gw, 0.10, rh, HEAD, (0.16, 0.32))
    W = lambda u: L / 2 + cbat(u)
    ends, fixed, bpts = [], [], []
    for side, sg in (("B-", -1), ("B+", 1)):
        for poly, key in cols:
            ends.append(([(p[0] + sg * W(p[1]), p[1]) for p in poly], side, key))
        bpts += [(p[0] + sg * W(p[1]), p[1]) for p in bseeds]
        for p in guards:
            q = (p[0] + sg * W(p[1]), p[1])
            if abs(q[0]) < W(q[1]):
                fixed.append(q)
    rng = random.Random("nozura-kado-" + v)
    # 行ごとに稜線に跨る種を一つ(σ ∈ ±0.06)置き、その行の他の種はそこから 0.30 以上離す
    # ⇒ 隅の石は行の中の一石として並ぶ(隅だけの石の柱にしない ── 算木の列に見える)
    corner, var = [], []
    u = 0.0
    k = 0
    while u > -depth - 0.05:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        w_ = W(uc)
        sc = rng.uniform(-0.06, 0.06)
        corner.append((sc, uc + rng.uniform(-0.05, 0.05)))
        s = -w_ - rng.uniform(0, 0.3) - (0.2 if k % 2 else 0)
        while s < w_ + 0.3:
            w = rng.uniform(0.25, 0.60)
            sx = s + w / 2 + rng.uniform(-0.05, 0.05)
            su = uc + rng.uniform(-0.05, 0.05)
            if abs(sx - sc) > 0.30 and abs(sx) < W(su) - gw * 1.3 and su < -0.05:
                var.append((sx, su))
            s += w
        u -= h_
        k += 1
    seeds = corner + fixed + var
    allp = seeds + bpts
    cells = []
    for i, (sx, su) in enumerate(seeds):
        g = rng.uniform(0.022, 0.040)
        poly = voronoi_cell(i, allp, g, (sx - 1.0, sx + 1.0, -depth - 0.3, HEAD + 0.12))
        if len(poly) < 3:
            continue
        # 継ぎ目の斜めの線(σ = ±W(u))の内へ: σ + 0.3u ≤ 0.889 / −σ + 0.3u ≤ 0.889
        poly = clip(poly, (1, BATTER), L / 2 - 0.02)
        poly = clip(poly, (-1, BATTER), L / 2 - 0.02)
        for op, side, key in ends:
            if len(poly) < 3:
                break
            cx, cu = centroid(op)
            if abs(cx - sx) < 1.0 and abs(cu - su) < 1.0:
                poly = separate(poly, (sx, su), op, g)
        if len(poly) < 3:
            continue
        poly = head_arc(poly, sx, rng.uniform(-HEAD, HEAD), rng.uniform(0.16, 0.32))
        if len(poly) < 3 or area(poly) < 0.008:
            continue
        kind = "C" if i < len(corner) else "I"
        cells.append((poly, kind, "K%s%d" % (v, i)))
    # 端の石は σ 空間の多角形でなく、直線の駒の座標(s)で返す(3D は直線の駒と同じ P で起こす)
    raw_ends = []
    for side, off in (("B-", -L / 2), ("B+", L / 2)):
        for poly, key in cols:
            raw_ends.append(([(p[0] + off, p[1]) for p in poly], side, key))
    return raw_ends, cells


def _u2b(x, y, z):
    """Unity → Blender(README 書き出しの規約: Unity X = −Bx / Y = Bz / Z = −By)"""
    return (-x, -z, y)


def _b2u(co):
    return (-co.x, co.z, -co.y)


def make_kado(h, v):
    """出隅 90° の駒。局所(Unity): 腕1 = 稜線から −X へ 0.909(見え面 +Z)/ 腕2 = 稜線から −Z へ 0.909(見え面 +X)。
    高い側(帯)は X ≤ 0・Z ≤ 0 の象限。ピボット = **天端の線の稜線(両腕の天端の線の交点)・床レベル(天端 − 見付)**。
    ⇒ 腕の先の切り口 X = −0.909 / Z = −0.909 が、直線の駒の切り口(±0.909)とそのまま一致する。
    作り: 石は σ 空間で平らに起こし(面取りまで)、稜線に跨る石だけ σ = 0 で割線を入れてから折る:
      腕1: (x, z) = (σ + c, z)  腕2: (x, z) = (z, −σ + c)   跨る石: (σ + z, z) / (z, −σ + z)(σ = 0 が留めの線 x = z)"""
    V.reset()
    mats = materials()
    raw_ends, cells = kado_layout(v)
    cut = lambda p: clip(p, (0, -1), h + BURY)
    objs = []
    # ① 端の石 ── 直線の駒と同じ鍵・同じ P(tag "wall")⇒ 形・材・UV の位相まで同じ
    ends = [(cut(p), k, key) for p, k, key in raw_ends]
    ends = [c for c in ends if len(c[0]) >= 3 and area(c[0]) > 0.004]
    for poly, side, key in ends:
        o = build_stones([(poly, side, key)], wall_P(h, 0.0), mats, tag="wall")[0]
        if side == "B+":           # 腕2 へ回す: (x, z) → (z, −x)
            for vt in o.data.vertices:
                x, y, z = _b2u(vt.co)
                vt.co = _u2b(z, y, -x)
        objs.append(o)
    # ② 中の石と隅の石 ── σ 空間(Unity X = σ・Z = c(u) − d)で起こして折る
    Pf = wall_P(h, 0.0)
    for poly, kind, key in cells:
        p2 = cut(poly)
        if len(p2) < 3 or area(p2) <= 0.004:
            continue
        smin, smax = min(p[0] for p in p2), max(p[0] for p in p2)
        o = build_stones([(p2, kind, key)], Pf, mats, tag="kado")[0]
        cross = smin < 0 < smax
        if cross:
            V.sel([o])
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(1, 0, 0), use_fill=False,
                                clear_inner=False, clear_outer=False)
            bpy.ops.object.mode_set(mode='OBJECT')
        arm1 = (smin + smax) < 0
        for vt in o.data.vertices:
            s, y, z = _b2u(vt.co)
            c = cbat(y - h)
            if cross:
                nx, nz = (s + z, z) if s <= 0 else (z, -s + z)
            elif arm1:
                nx, nz = s + c, z
            else:
                nx, nz = z, -s + c
            vt.co = _u2b(nx, y, nz)
        o.data.update()
        objs.append(o)
    # ③ 目地の奥を塞ぐ板(面から 0.12 奥・法に沿う)── 二枚が内の留めで閉じる
    for arm in (1, 2):
        bm = bmesh.new()
        vs = []
        for u in (-0.12, -(h + BURY)):
            k = cbat(u) - 0.12
            if arm == 1:
                vs += [bm.verts.new(_u2b(-L / 2, h + u, k)), bm.verts.new(_u2b(k, h + u, k))]
            else:
                vs += [bm.verts.new(_u2b(k, h + u, k)), bm.verts.new(_u2b(k, h + u, -L / 2))]
        bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
        me = bpy.data.meshes.new("back%d" % arm); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("back%d" % arm, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(mats[1])
        me.update()
        nU = _b2u(me.polygons[0].normal)
        want = (0, 0, 1) if arm == 1 else (1, 0, 0)
        if nU[0] * want[0] + nU[2] * want[2] < 0:
            me.flip_normals()
        box_uv(ob, (0.3, 0.7))
        objs.append(ob)
    name = kado_name(h, v)
    o = V.join(objs, name)
    bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))          # Unity X ≥ −L/2 ⇔ Blender X ≤ +L/2
    bisect_keep(o, (0, L / 2, 0), (0, 1, 0))          # Unity Z ≥ −L/2 ⇔ Blender Y ≤ +L/2
    V.set_origin(o, (0, 0, 0))
    return o, name


def check_kado(h=1.50):
    """⭕ 隅の駒の腕の先の切り口 = 直線の駒の切り口(天端から 0.25 まで・1mm で丸め)"""
    ow, _, _ = make_wall(h, 0.0, "a")
    ref_p = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, -L / 2)}   # 直線の +X 端(Unity X = +0.909)
    ref_m = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, L / 2)}    # 直線の −X 端
    bad = 0
    for v in KADO_VARIANTS:
        o, name = make_kado(h, v)
        # 腕1 の先 = Unity X = −0.909 ⇔ Blender X = +0.909 ── 直線の +X 端と合わさる
        a1 = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(o, L / 2)}
        # 腕2 の先 = Unity Z = −0.909 ⇔ Blender Y = +0.909。直線の −X 端と比べるため (Blender X, Z) へ写す
        a2 = set()
        for vt in o.data.vertices:
            if abs(vt.co.y - L / 2) < 1e-4:
                # 腕2 の局所: 直線の駒の Unity Z = 腕2 の Unity X ⇒ Blender Y' = −(Unity X) = Blender X
                a2.add((round(vt.co.x, 3), round(vt.co.z - h, 3)))
        top = lambda S: {p for p in S if p[1] > -0.25}
        d1 = len(top(a1) ^ top(ref_p)); d2 = len(top(a2) ^ top(ref_m))
        print("NOZURA KADO CHECK %s: 腕1の先 %d点 差%d / 腕2の先 %d点 差%d" % (name, len(top(a1)), d1, len(top(a2)), d2))
        bad += (d1 > 0) + (d2 > 0)
    return bad


# ------------------------------------------------------------------ 石段の袖
def sode_name(keri, fumi, v):
    return "IshidanSodeNozura_%.3f_%.3f_%s" % (keri, fumi, v)


def make_sode(keri, fumi, v):
    """`IshidanSode` と同じ枠。s = Unity Z(+ = 坂下)・天端 Y = 0.30 + (f/2 − s)·k/f。
    厚み X ±0.30 の両面を割肌に(d = +X 面から奥へ 0..0.60)。"""
    V.reset()
    mats = materials()
    f = fumi
    cells = layout(f, SODE_DEPTH, "nozura-sode-B-%.3f" % f, "nozura-sode-%.3f-%s" % (f, v),
                   wr=(0.22, 0.45), gw=min(0.30, f * 0.36), bcmax=0.04,
                   head=0.025, rr=(1.2, 2.0))     # 袖の天端は石段に沿う一本の線 ⇒ 頭の不揃いは ±2.5cm・頭はほぼ平ら

    def P(s, u, d):
        # Unity X = +0.30 − d(両面)⇒ Blender X = −(0.30 − d)
        top = SODE_HT + (f / 2 - s) * keri / f
        return (-(SODE_HALF - d), -s, top + u)
    cells = [(clip(p, (0, -1), SODE_DEPTH), k, key) for p, k, key in cells]
    cells = [c for c in cells if len(c[0]) >= 3 and area(c[0]) > 0.004]
    objs = build_stones(cells, P, mats, double=2 * SODE_HALF, face_prot=(-0.04, -0.005),
                        tag="sode%.3f" % f)
    # 芯の板(両面の目地の奥を塞ぐ・X = ±0.18)
    for sx_ in (1, -1):
        bm = bmesh.new()
        vs = [bm.verts.new(P(s_, u_, SODE_HALF - sx_ * 0.18)) for s_, u_ in
              ((-f / 2, -0.10), (f / 2, -0.10), (f / 2, -SODE_DEPTH), (-f / 2, -SODE_DEPTH))]
        bm.faces.new(vs)
        me = bpy.data.meshes.new("core"); bm.to_mesh(me); bm.free()
        oc = bpy.data.objects.new("core", me); bpy.context.scene.collection.objects.link(oc)
        me.update()
        if me.polygons[0].normal.x * (-sx_) < 0:     # 外(Unity ±X)へ向ける
            me.flip_normals()
        oc.data.materials.append(mats[1]); box_uv(oc, (0.3, 0.6))
        objs.append(oc)
    name = sode_name(keri, fumi, v)
    o = V.join(objs, name)
    # ⛔ 石は X = ±0.30 の面を越えない(段石の小口に突き付く面)
    for vt in o.data.vertices:
        vt.co.x = max(-SODE_HALF, min(SODE_HALF, vt.co.x))
    bisect_keep(o, (0, -f / 2, 0), (0, -1, 0))        # Unity Z ≤ +f/2
    bisect_keep(o, (0, f / 2, 0), (0, 1, 0))
    V.set_origin(o, (0, 0, 0))
    return o, name, len(cells)


# ------------------------------------------------------------------ 見切り石
def make_mikiri():
    V.reset()
    mats = materials()
    rng = random.Random("nozura-mikiri")
    w, hh = 0.86, 0.80
    poly = [(-w / 2 + 0.10, -hh), (w / 2 - 0.06, -hh), (w / 2, -hh + 0.15), (w / 2 - 0.02, -0.18),
            (w / 2 - 0.16, 0.0), (-w / 2 + 0.20, 0.02), (-w / 2, -0.20), (-w / 2 + 0.02, -hh + 0.12)]
    poly = head_arc(poly, 0.0, 0.0, 0.55)
    P = wall_P(hh - BURY, 0.0)   # 床から 0.60 見え・0.20 根入れ
    o = stone_obj("Sanno_Nozura_Mikiri", poly, rng, P, 0.90, face_prot=(0.0, 0.02))
    o.data.materials.append(mats[0])
    box_uv(o, (0.2, 0.4))
    V.set_origin(o, (0, 0, 0))
    return o, "Sanno_Nozura_Mikiri"


# ------------------------------------------------------------------ 測る・書く・撮る
def tris(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def unity_bounds(o):
    xs = [-v.co.x for v in o.data.vertices]; ys = [v.co.z for v in o.data.vertices]
    zs = [-v.co.y for v in o.data.vertices]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


REPORT = []


def export(o, name, outdir):
    path = os.path.join(outdir, name + ".fbx")
    V.export_fbx([o], path)
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    REPORT.append((name, tris(o), x0, x1, y0, y1, z0, z1))
    print("NOZURA %s tris=%d X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f]" % (name, tris(o), x0, x1, y0, y1, z0, z1))
    return path


def seam_verts(o, x_b, tol=1e-4):
    """Blender X = x_b の切り口に乗る頂点(Y,Z)の集合(1mm で丸め)"""
    return sorted({(round(v.co.y, 3), round(v.co.z, 3)) for v in o.data.vertices if abs(v.co.x - x_b) < tol})


def check():
    """⭕ 継ぎ目の一致を数で検める: どの種類・どの段でも、+X 端の切り口 = −X 端の切り口(上から共通の深さまで)"""
    res = []
    prof = {}
    for h in (0.30, 1.20, 2.40):
        for v in VARIANTS:
            o, name, _ = make_wall(h, 0.0, v)
            lo = [p for p in seam_verts(o, L / 2) if p[1] > h - 0.25]      # Unity −X 端(天端から 0.25)
            hi = [p for p in seam_verts(o, -L / 2) if p[1] > h - 0.25]     # Unity +X 端
            lo = [(y, round(z - h, 3)) for y, z in lo]; hi = [(y, round(z - h, 3)) for y, z in hi]
            prof[(h, v)] = (lo, hi)
    ref = prof[(1.20, "a")][1]
    bad = 0
    for k, (lo, hi) in prof.items():
        # 天端から測った切り口の頂点が、どの駒の −X 端とも・+X 端とも一致するか
        if set(lo) != set(ref) or set(hi) != set(ref):
            bad += 1
            res.append("⛔ %s: −X端 %d点 / +X端 %d点 / 基準 %d点 (差 %d / %d)" % (
                k, len(lo), len(hi), len(ref), len(set(lo) ^ set(ref)), len(set(hi) ^ set(ref))))
    print("NOZURA CHECK seam: %d/%d 不一致" % (bad, len(prof)))
    for r in res:
        print("NOZURA CHECK", r)
    return bad


def studio_run(objs, cam, look, lens=35, path=None, magenta=False):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.eevee.taa_render_samples = 48
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1) if magenta else (0.62, 0.70, 0.80, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.2; sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-40))
    sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new("Cam"); cd.lens = lens; cd.clip_start = 0.05
    c = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(c); sc.camera = c
    c.location = cam
    c.rotation_euler = (Vector(look) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
    V.render(path)


def place_copy(src_fbx, x_u, y_u):
    """FBX を読み、Unity (x, y) へ置く(検証レンダ用・Blender 座標へ戻す)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=src_fbx)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type == 'MESH':
            o.location.x += -x_u
            o.location.z += y_u
    return new


def ground(z=0.0, y0=-30, y1=0.5, name="Yard", col=(0.20, 0.26, 0.12)):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(-30, y0, z), (30, y0, z), (30, y1, z), (-30, y1, z)]]
    bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs['Base Color'].default_value = col + (1,)
    bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Specular IOR Level'].default_value = 0.0
    me.materials.append(m)
    return o


def hook_stone_textures():
    """読み込んだ FBX の Kirishi / Danishi にテクスチャを結ぶ(検証レンダ用)"""
    for m in bpy.data.materials:
        base = m.name.split(".")[0]
        if base not in ("Kirishi", "Danishi"):
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not b:
            continue
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.92
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = bpy.data.images.load(os.path.join(MATDIR, "T_Kirishi_Albedo.png"), check_existing=True)
        t = 1.0 if base == "Kirishi" else 0.80
        mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1
        nt.links.new(ti.outputs['Color'], mx.inputs[1]); mx.inputs[2].default_value = (t, t, t, 1)
        nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])


def render_wall_run(tag, magenta=False):
    """⭐ 焼いた FBX を読み戻して並べる(= Unity が読む物を撮る)。
    上段: 見付 1.2 を a,b,c,d,a,b,c と 7駒(継ぎ目・繰り返し)。
    下段: 天端の線を一本(Y = 0.9 → 勾配なしで段の違う駒を沈めて継ぐ)— 0.9,1.2,1.5,2.4,0.15 …"""
    V.reset()
    seq = "abcdabc"
    x0 = -3 * L
    for i, v in enumerate(seq):
        place_copy(os.path.join(OUT_WALL, wall_name(1.20, 0.0, v) + ".fbx"), x0 + i * L, 0.0)
    hook_stone_textures()
    ground()
    # 上の地面(天端の 0.10 上・頭の後ろ)
    ground(1.25, 0.25, 12, "Upper", (0.18, 0.24, 0.11))
    studio_run([], (-4.0, -8.5, 1.5), (0.5, 0, 0.7), 28,
               os.path.join(SHOT, "sanno_nozura_run%s.png" % tag), magenta)
    # 寄り(継ぎ目 x=±L/2 の2本が入る)
    studio_run([], (-0.6, -2.4, 1.3), (0.2, 0, 0.75), 30,
               os.path.join(SHOT, "sanno_nozura_seam%s.png" % tag), magenta)


def render_tier_mix(tag):
    """① 段の違う駒を天端の線で継ぐ: 天端 Y = 0.9 一定で 0.9/1.2/2.4/1.5/0.9 を沈めて並べる。
    ② 打ち切り: 天端 0.30 の駒の両端に根石の打ち切り(G±180)を継ぐ。"""
    V.reset()
    top = 0.9
    seq = [(0.90, "a"), (1.20, "b"), (2.40, "c"), (1.50, "d"), (0.90, "a")]
    x0 = -2 * L
    for i, (h, v) in enumerate(seq):
        place_copy(os.path.join(OUT_WALL, wall_name(h, 0, v) + ".fbx"), x0 + i * L, top - h)
    hook_stone_textures()
    ground()
    ground(top + 0.06, 0.45, 12, "Upper", (0.18, 0.24, 0.11))
    studio_run([], (-1.5, -6.0, 1.5), (0.0, 0, 0.55), 26, os.path.join(SHOT, "sanno_nozura_tiers%s.png" % tag))

    V.reset()
    top = 0.30
    xk = -2 * L
    # 左の打ち切り(+X へ上がる): 右端(s=+L/2)の天端を 0.30 に ⇒ 中心の天端 = 0.30 − 0.909·G
    items = [(wall_name(0.15, KIRI_G, "a"), top - 0.909 * KIRI_G - 0.15),
             (wall_name(0.30, 0, "b"), 0.0), (wall_name(0.30, 0, "c"), 0.0), (wall_name(0.30, 0, "d"), 0.0),
             (wall_name(0.15, -KIRI_G, "a"), top - 0.909 * KIRI_G - 0.15)]
    for i, (nm, y) in enumerate(items):
        place_copy(os.path.join(OUT_WALL, nm + ".fbx"), xk + i * L, y)
    hook_stone_textures()
    ground()
    studio_run([], (-0.5, -8.0, 1.5), (0.0, 0, 0.1), 26, os.path.join(SHOT, "sanno_nozura_kiri%s.png" % tag))


def render_sode(keri, fumi, name_tag, n=8):
    """袖の駒を段ごとに i%2 で並べ(天端が勾配の一直線に載るか)、坂の横から見る"""
    V.reset()
    for i in range(n):
        v = "a" if i % 2 == 0 else "b"
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(OUT_SODE, sode_name(keri, fumi, v) + ".fbx"))
        for o in [o for o in bpy.data.objects if o not in before and o.type == 'MESH']:
            # 段 i: Unity Z = −(i+0.5)·踏面(坂上へ)、Y = 蹴上·(i+1)
            o.location.y += (i + 0.5) * fumi
            o.location.z += keri * (i + 1)
    hook_stone_textures()
    ground(0.0, -30, 30)
    run = n * fumi
    studio_run([], (4.5, run * 0.5 - 1.0, 1.6 + keri * n * 0.5), (0, run * 0.5, keri * n * 0.55), 30,
               os.path.join(SHOT, "sanno_nozura_sode_%s.png" % name_tag))


def render_mikiri():
    V.reset()
    place_copy(os.path.join(OUT_WALL, "Sanno_Nozura_Mikiri.fbx"), 0.0, 0.0)
    place_copy(os.path.join(OUT_WALL, wall_name(0.60, 0, "a") + ".fbx"), -(L / 2 + 0.43), 0.0)
    hook_stone_textures()
    ground()
    studio_run([], (-0.8, -3.0, 1.4), (-0.4, 0, 0.35), 35, os.path.join(SHOT, "sanno_nozura_mikiri.png"))


def _import_at(path, x_u, z_u, y_u, yaw_u=0.0):
    """FBX を読み、Unity の yaw(度・+Z→+X が +90)で回して Unity (x, y, z) へ置く(検証レンダ用)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    R = mathutils.Matrix.Rotation(math.radians(-yaw_u), 4, 'Z')
    T = mathutils.Matrix.Translation(Vector(_u2b(x_u, y_u, z_u)))
    for o in new:
        o.matrix_world = T @ R @ o.matrix_world
    return new


def render_kado(h=1.50, tag=""):
    """隅の駒を直線の駒で挟んで撮る: 腕1 の先に直線 2駒(見え面 +Z)、腕2 の先に直線 2駒(yaw 90・見え面 +X)。
    隅の外(+X +Z)の低い地面と、帯(X ≤ 0・Z ≤ 0)の上の地面。"""
    for v in KADO_VARIANTS:
        V.reset()
        _import_at(os.path.join(OUT_WALL, kado_name(h, v) + ".fbx"), 0, 0, 0)
        for i, wv in enumerate("ab"):
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, wv) + ".fbx"), -L * (i + 1), 0, 0)
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "cd"[i]) + ".fbx"), 0, -L * (i + 1), 0, 90.0)
        hook_stone_textures()
        ground()
        # 帯の上(天端 + 0.06・X ≤ 0 かつ Z ≤ 0 ⇔ Blender X ≥ 0 かつ Y ≥ 0)
        bm = bmesh.new()
        vs = [bm.verts.new(q) for q in [(0.05, 0.05, h + 0.06), (12, 0.05, h + 0.06), (12, 12, h + 0.06), (0.05, 12, h + 0.06)]]
        bm.faces.new(vs); me = bpy.data.meshes.new("Upper"); bm.to_mesh(me); bm.free()
        ou = bpy.data.objects.new("Upper", me); bpy.context.scene.collection.objects.link(ou)
        mu = bpy.data.materials.new("Upper"); mu.use_nodes = True
        mu.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.18, 0.24, 0.11, 1)
        me.materials.append(mu)
        # 隅の外(対角)から
        studio_run([], _u2b(4.2, 1.7, 4.2), _u2b(-0.6, h * 0.5, -0.6), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s%s.png" % (v, tag)))
        studio_run([], _u2b(4.2, 1.7, 4.2), _u2b(-0.6, h * 0.5, -0.6), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s_magenta%s.png" % (v, tag)), magenta=True)
        # 腕1 の継ぎ目の寄り
        studio_run([], _u2b(-0.4, 1.2, 2.6), _u2b(-0.9, h * 0.5, 0), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s_seam%s.png" % (v, tag)))
        # 真上から(平面の留め)── 帯の地面を消す
        bpy.data.objects.remove(ou)
        sc = bpy.context.scene
        cam = sc.camera
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = 5.0
        cam.location = _u2b(-0.8, 8.0, -0.8); cam.rotation_euler = (0, 0, 0)
        V.render(os.path.join(SHOT, "sanno_nozura_kado_%s_plan%s.png" % (v, tag)))


def render_dan(g=0.22, h=1.50):
    """段の境: 天端 T の直線 H1.50 → 勾配の駒(1間で 0.40 下がる)→ 天端 T − 0.40 の直線 H1.20。床は Y=0 の地面に沈める。"""
    V.reset()
    T = 1.35
    items = [(wall_name(1.50, 0, "a"), -L, T - 1.50),
             (wall_name(h, -g, "b"), 0.0, T - 0.909 * g - h),
             (wall_name(1.20, 0, "c"), L, T - 2 * 0.909 * g - 1.20),
             (wall_name(1.20, 0, "d"), 2 * L, T - 2 * 0.909 * g - 1.20)]
    for nm, x, y in items:
        place_copy(os.path.join(OUT_WALL, nm + ".fbx"), x, y)
    hook_stone_textures()
    ground()
    studio_run([], (-0.6, -5.5, 1.3), (-0.6, 0, 0.8), 30, os.path.join(SHOT, "sanno_nozura_dan.png"))
    studio_run([], (-0.6, -5.5, 1.3), (-0.6, 0, 0.8), 30, os.path.join(SHOT, "sanno_nozura_dan_magenta.png"), magenta=True)


# ------------------------------------------------------------------ 本体
def do_kado():
    hs = [float(OPT["h"])] if OPT.get("h") else KADO_TIERS
    for h in hs:
        for v in KADO_VARIANTS:
            o, name = make_kado(h, v)
            export(o, name, OUT_WALL)


def do_wall():
    grades = [float(OPT["grade"])] if OPT.get("grade") else [0.0]
    hs = [float(OPT["h"])] if OPT.get("h") else TIERS
    for g in grades:
        for h in hs:
            for v in VARIANTS:
                o, name, n = make_wall(h, g, v)
                export(o, name, OUT_WALL)


def do_kiri():
    for g in (KIRI_G, -KIRI_G):
        for v in VARIANTS:
            o, name, n = make_wall(0.15, g, v)
            export(o, name, OUT_WALL)


def do_sode():
    import build_sanno_buzai as SB
    for nm, keri, fumi, w in SB.kaidan_specs(OPT.get("only") or None):
        # ⭐ 袖が焼けている石段(= 旧 `IshidanSode_<蹴上>_<踏面>_a` がある組)だけ差し替える
        old = os.path.join(OUT_SODE, "IshidanSode_%.3f_%.3f_a.fbx" % (keri, fumi))
        if not os.path.exists(old) and not OPT.get("only"):
            continue
        for v in "ab":
            o, name, n = make_sode(keri, fumi, v)
            export(o, name, OUT_SODE)
        if RENDER:
            render_sode(keri, fumi, nm)


def do_mikiri():
    o, name = make_mikiri()
    export(o, name, OUT_WALL)


if __name__ == "__main__":
    what = POS[0] if POS else "all"
    if what == "check":
        sys.exit(1 if check() else 0)
    if what == "kado-check":
        sys.exit(1 if check_kado(float(OPT.get("h") or 1.5)) else 0)
    if what == "kado":
        do_kado()
        if RENDER:
            render_kado(float(OPT.get("h") or 1.5))
    if what == "dan" and RENDER:
        render_dan()
    if what in ("wall", "all"):
        do_wall()
    if what in ("kiri", "all"):
        do_kiri()
    if what in ("mikiri", "all"):
        do_mikiri()
    if what in ("sode", "all"):
        do_sode()
    if RENDER:
        if what in ("wall", "all", "kiri"):
            render_wall_run("")
            render_wall_run("_magenta", magenta=True)
            render_tier_mix("")
        if what in ("mikiri", "all"):
            render_mikiri()
    for r in REPORT:
        print("NOZURA_SUM %s %d" % (r[0], r[1]))
