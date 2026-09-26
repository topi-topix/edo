"""山王 参道の階(前庭へ・0.250 / 0.542 / 5.509)の段石の両端と袖の背を、**相手の野面の石の見える外形に沿わせて**焼く
(EDO-0437 第10巡・2026-09-26)。

    blender --background --python Tools/Blender/build_sanno_sando_fit.py -- all --render
    blender --background --python Tools/Blender/build_sanno_sando_fit.py -- dan [--only=1,2] [--render]
    blender --background --python Tools/Blender/build_sanno_sando_fit.py -- sode [--only=W,E] [--render]
    blender --background --python Tools/Blender/build_sanno_sando_fit.py -- check        # 焼いた FBX を読み戻して相手との当たり・隙を測るだけ

なぜ平面で切らないか: 相手(前庭の縁の出隅の駒 `Sanno_Nozura_Kado90_*` と野面の駒 `Sanno_Nozura_H0600_G+000_c`)は乱積みで、
見え面は石ごとに 0.1〜0.2 出入りする。平面(法 1:0.3)で切った端・背は、最も出た石に合わせれば他で口が開き
(袖の背で中央値 0.08〜0.11)、据えで隅の石を退けると段の端に 0.12〜0.24 の隙が開いた。⇒ 駒の端そのものを石の形で刳る。

【入力】`Tools/Blender/data/sanno_sando_fit_r10.json.gz`(棟梁が据えたシーンから書き出した実測・EDO-0437 r10):
  各段・袖の FBX 名・配置(pos / euler / scale)と、相手の石の三角形(**段・袖の局所座標**・見える地表より上に頂点を持つ物)。
  三角形は隅石を段の外へ退けた(`EdoBuild.YieldWallsToSteps`)後の位置で書かれている ⇒ **`yieldOffsetLocal` を足して退ける前の位置**を相手にする
  (この焼き直しで退けは止める)。⛔ 据えを変えたら json を書き出し直してから焼き直す(形は据えの従属値)。

【作り】(局所 Unity 座標 X 幅 / Y 高さ / Z 走り(+Z 坂下)。段・袖とも既存の駒と同じ局所座標・同じピボット・同じ石の割り・同じ材)
  ・段石: `build_sanno_buzai.dan` と同じ石(同じ乱数の順で UV も同じ)。端の石だけを外へ伸ばし、Y・Z の面で 0.01 升に刻み、
    升の頂点の X を「相手の石の面(端から外へ走らせた光線の最初の当たり)− 0.002」へ詰める。
    当たりは 0.005 升で打ち、頂点の値は ±0.01 の窓の最小(升の間で石が出ても食い込まない)。
    当たりが無い所・0.40 より遠い所は小口 X = ±幅/2 のまま。袖の居る所(段 1)は ±幅/2 より外へ出さない(袖の側面に突き付く)。
    ⇒ 段の蹴上・踏面・幅・段鼻の線は変わらない。変わるのは端だけ。
  ・袖: `build_sanno_nozura.make_sode` の個体に坂上の次の個体を継ぎ(`make_sode_nnori` と同じ)、背の側を X・Y の面で 0.01 升に刻み、
    Z を「相手の面(背から坂上へ走らせた光線の最初の当たり)+ 0.002」へ寄せる(窓の最大)。当たりが無い所は今の平面の背
    (法 1:0.3・E = 据えてある駒の e)。背より坂上に丸ごと残る石は落とす。⇒ 表(見え面 X = ±0.30・天端の線)は変わらない。

【名】`DanFit_<蹴上>_<踏面>_<幅>_<a|b>_SandoKai<段>.fbx` / `IshidanSodeNozuraFit_<蹴上>_<踏面>_SandoKai<W|E><袖の番>_<a|b>.fbx`(Models/Kaidan)。
  段 0 は相手の石に見える当たりが無い(光線の当たり 0)ので焼かない(`Dan_…_a` のまま)。
【材】段 `Danishi` / 袖 `Kirishi`・`Danishi`(新規なし)⇒ Unity で `Edo/山王社/新造部材のマテリアルをremap`。
"""
import bpy, bmesh, sys, os, math, json, gzip
import numpy as np
import mathutils
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_sanno_buzai as SB
import build_sanno_nozura as NZ

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
POS = [a for a in ARGS if not a.startswith("--")]
OPT = dict((a[2:].split("=", 1) + [""])[:2] for a in ARGS if a.startswith("--"))
RENDER = "render" in OPT

FIT = OPT.get("fit") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sanno_sando_fit_r10.json.gz")
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Kaidan"))
SHOT = os.path.join(V.REPO, "Screenshots")
LOGJ = OPT.get("json") or ""

KERI, FUMI, W = 0.250, 0.542, 5.509
W2 = W / 2.0
MARGIN = 0.002        # 相手の面からの離れ(目地 ≤ 0.01 の内)
RAY = 0.0025          # 当たりを打つ升
CELL = 0.01           # 刻む升(見える帯)
COARSE = 0.04         # 刻む升(見えない帯)
CLIFF = 4             # 石の段の窓 ±CLIFF·RAY = ±0.01(刻む升一つ分)。窓の最小より 0.02 以上奥の頂点は窓の最小へ下げる
CLIFF_DZ = 0.02       # 隣の当たり(0.0025 離れ)とこれ以上違えば石の段(傾き 8 超)⇒ 段を渡る面は奥の側にだけ乗る
SAMP = 0.00125        # 食い込みを消す標本の升(測る升 0.0025 の半分 ── 石の角の細い出も拾う)
OPEN = 8              # 相手の目地を跨ぐ窓 ±OPEN·RAY = ±0.02(幅 0.04 より細い奥まり = 相手の石と石の目地は埋めずに石の面で跨ぐ)
REACH = 0.40          # 段の端を外へ伸ばす上限
SODE_E = {"W": -0.15, "E": -0.20}   # 据えてある袖の背の e(当たりの無い所の背の面)
CELL_S = 0.02         # 袖の背を刻む升(乱積みの石ごとに面が要るので段より粗く ── 三角形を 2 万前後に抑える)
SODE_REACH = 0.80     # 袖の背を坂上へ伸ばす上限(今の背の面から)── 継いだ次の個体の中に収まる


# ------------------------------------------------------------------ 座標
def u2b(p):
    return Vector((-p[0], -p[2], p[1]))


def b2u(co):
    return (-co.x, co.z, -co.y)


def rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def to_world(part, P):
    """part の局所(Unity)→ ワールド(Unity)。P: (N,3)"""
    return (rot_y(part["euler"][1]) @ (np.asarray(P) * np.array(part["scale"])).T).T + np.array(part["pos"])


def to_local(part, Pw):
    return (rot_y(part["euler"][1]).T @ (np.asarray(Pw) - np.array(part["pos"])).T).T / np.array(part["scale"])


def load_fit():
    with gzip.open(FIT, "rt", encoding="utf-8") as fp:
        return json.load(fp)


def wall_tris(walls):
    """退ける前の位置の三角形(局所)。"""
    out = []
    for w in walls:
        off = np.array(w["yieldOffsetLocal"])
        out.append(np.array(w["tris"]) + off)
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def bvh_of(T):
    vs = [tuple(p) for t in T for p in t]
    polys = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(T))]
    return BVHTree.FromPolygons(vs, polys, all_triangles=True)


def bvh_obj(o):
    """o のメッシュ(Blender)を Unity 局所で BVH に。"""
    vs = [b2u(v.co) for v in o.data.vertices]
    return BVHTree.FromPolygons(vs, [tuple(p.vertices) for p in o.data.polygons])


def cast_grid(bvh, origin_fn, d, dist, A, B):
    """A×B の格子で光線を打ち、当たりまでの距離(無ければ inf)を返す。"""
    R = np.full((len(A), len(B)), np.inf)
    dv = Vector(d)
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            hit = bvh.ray_cast(Vector(origin_fn(a, b)), dv, dist)
            if hit[0] is not None:
                R[i, j] = hit[3]
    return R


def win_min(R, k):
    P = np.pad(R, k, mode="edge")
    out = np.full(R.shape, np.inf)
    for di in range(2 * k + 1):
        for dj in range(2 * k + 1):
            out = np.minimum(out, P[di:di + R.shape[0], dj:dj + R.shape[1]])
    return out


def opening_far(D, k):
    """「奥ほど大きい」場 D の細い山(= 相手の目地の奥まり)を落とす(最小 → 最大の窓)。結果は D を越えない。"""
    return -win_min(-win_min(D, k), k)


def cliff_safe(D, k=CLIFF):
    """奥ほど大きい場 D の石の段(隣の当たりと CLIFF_DZ 以上違う所 = 光線がほぼ掠める稜・目地の縁)の ±k 升を、
    窓の最小(手前の石の面)へ下げる。滑らかな斜面(急でも)はそのまま ⇒ 段を渡る斜めの面は奥の側にだけ乗る。"""
    C = np.zeros(D.shape, bool)
    d0 = np.abs(np.diff(D, axis=0)) > CLIFF_DZ
    d1 = np.abs(np.diff(D, axis=1)) > CLIFF_DZ
    C[:-1, :] |= d0; C[1:, :] |= d0; C[:, :-1] |= d1; C[:, 1:] |= d1
    return np.where(_dilate(C, k), win_min(D, k), D)


def bilin(A, B, F, a, b):
    """格子 (A, B) 上の F を (a, b) で双線形に引く(外は端で止める)。"""
    a = min(max(a, A[0]), A[-1]); b = min(max(b, B[0]), B[-1])
    i = min(max(int((a - A[0]) / (A[1] - A[0])), 0), len(A) - 2)
    j = min(max(int((b - B[0]) / (B[1] - B[0])), 0), len(B) - 2)
    ta = (a - A[i]) / (A[i + 1] - A[i]); tb = (b - B[j]) / (B[j + 1] - B[j])
    return ((1 - ta) * (1 - tb) * F[i, j] + ta * (1 - tb) * F[i + 1, j]
            + (1 - ta) * tb * F[i, j + 1] + ta * tb * F[i + 1, j + 1])


def planes(lo, hi, fine_lo, fine_hi, fine=CELL, coarse=COARSE):
    """lo..hi を刻む面の位置: fine_lo..fine_hi は fine、外は coarse。"""
    ps = set()
    x = fine_lo
    while x <= fine_hi + 1e-9:
        ps.add(round(x, 5)); x += fine
    x = fine_lo - coarse
    while x > lo:
        ps.add(round(x, 5)); x -= coarse
    x = fine_hi + coarse
    while x < hi:
        ps.add(round(x, 5)); x += coarse
    return sorted(p for p in ps if lo < p < hi)


def slice_faces(bm, axis_b, vals, sel_fn):
    """bm の、sel_fn(face) が真の面だけを、Blender 軸 axis_b の面 vals で刻む(捨てない)。"""
    no = [0.0, 0.0, 0.0]; no[axis_b] = 1.0
    for v in vals:
        faces = [f for f in bm.faces if sel_fn(f)]
        if not faces:
            continue
        edges = list({e for f in faces for e in f.edges})
        verts = list({vv for f in faces for vv in f.verts})
        co = [0.0, 0.0, 0.0]; co[axis_b] = v
        bmesh.ops.bisect_plane(bm, geom=verts + edges + faces, dist=1e-6, plane_co=co, plane_no=no,
                               clear_outer=False, clear_inner=False)


# ------------------------------------------------------------------ 詰めた面を相手に当てて退かす(食い込み 0 を保証する)
def settle(bm, zone, ax, sgn, samples, cell, tag, iters=12):
    """zone(頂点 index の集合)を、相手の面の標本 samples = [(u, v, w)] に対して食い込みが無くなるまで退かす。
    ax = 動かす Unity 軸(0 = X / 2 = Z)、sgn = 相手の向き(その軸で + が相手)。u, v = 残りの2軸の座標(軸の順)、w = 相手の面の座標。
    駒の面は相手の側から光線を当てて測る(三角形にしてあるので書き出した物と同じ面)。食い込んだ標本の升の角の頂点を退かす。"""
    from mathutils import kdtree
    oth = [k for k in range(3) if k != ax]
    bm.verts.ensure_lookup_table()
    zl = sorted(zone)
    kd = kdtree.KDTree(len(zl))
    for n, vi in enumerate(zl):
        U = b2u(bm.verts[vi].co)
        kd.insert((U[oth[0]], U[oth[1]], 0.0), n)
    kd.balance()
    dirv = [0.0, 0.0, 0.0]; dirv[ax] = -sgn
    worst = 0.0
    for it in range(iters):
        vs = [b2u(v.co) for v in bm.verts]
        bo = BVHTree.FromPolygons(vs, [tuple(vv.index for vv in f.verts) for f in bm.faces])
        low = {}
        worst = 0.0
        for (a, b, w) in samples:
            o_ = [0.0, 0.0, 0.0]; o_[oth[0]] = a; o_[oth[1]] = b; o_[ax] = w + sgn * 0.6
            h = bo.ray_cast(Vector(o_), Vector(dirv), 1.5)
            if h[0] is None:
                continue
            bite = sgn * (h[0][ax] - w)
            if bite <= 0.0:
                continue
            worst = max(worst, bite)
            for (_, n, _) in kd.find_range((a, b, 0.0), cell * 1.45):
                vi = zl[n]
                low[vi] = max(low.get(vi, 0.0), bite + 0.0005)
        if not low:
            break
        for vi, d in low.items():
            co = bm.verts[vi].co
            U = list(b2u(co)); U[ax] -= sgn * d
            co[:] = u2b(U)
    print("SETTLE %s: 回 %d・残りの食い込み最大 %.5f" % (tag, it + 1, worst))
    return worst


def edge_samples(T, ax, keep_fn, step=0.0025):
    """相手の三角形の頂点と辺の上の点(step 刻み)を標本に(石の角・稜は升の標本の間に隠れる)。keep_fn(u, v, w) で絞る。"""
    oth = [k for k in range(3) if k != ax]
    out = []
    for t in T:
        for i in range(3):
            p, q = t[i], t[(i + 1) % 3]
            n = max(1, int(np.linalg.norm(q - p) / step))
            for k in range(n):
                c = p + (q - p) * (k / n)
                a, b, w = c[oth[0]], c[oth[1]], c[ax]
                if keep_fn(a, b, w):
                    out.append((a, b, w))
    return out


def fix_uv(bm, orig, fax, uv_of_face_axis):
    """詰めた頂点の変位(Blender)で、投影に使った軸の UV をずらす(柄を伸ばさない)。"""
    uvl = bm.loops.layers.uv.active
    for f in bm.faces:
        ax = fax.get(f.index)
        if ax is None:
            continue
        for l in f.loops:
            o = orig.get(l.vert.index)
            if o is None:
                continue
            dco = l.vert.co - o
            if dco.length_squared < 1e-14:
                continue
            du, dv = uv_of_face_axis(ax, dco)
            u, w_ = l[uvl].uv
            l[uvl].uv = (u + du, w_ + dv)


def _proj(co, ax):
    """`_stone` / `box_uv` の投影(Blender 座標・面の法線の主軸 ax): 2 → (x, y) / 1 → (x, z) / 0 → (y, z)。"""
    return (co.x, co.y) if ax == 2 else ((co.x, co.z) if ax == 1 else (co.y, co.z))


def reproject_turned(bm, old_ax, moved, tile):
    """詰めて向きが変わった面(法線の主軸が変わった面)を、新しい向きで投影し直す(面の位相は元のまま)。
    ⛔ 向きが変わった面を元の軸のまま残すと、柄が一方向に流れて縞になる(段 4 の端で実見)。"""
    uvl = bm.loops.layers.uv.active
    bm.normal_update()
    n = 0
    for f in bm.faces:
        if not any(moved(l.vert) for l in f.loops):
            continue
        a0 = old_ax(f)
        a1 = max(range(3), key=lambda k: abs(f.normal[k]))
        if a1 == a0 or f.calc_area() < 1e-10:
            continue
        l0 = f.loops[0]
        p0 = _proj(l0.vert.co, a0)
        ph = (l0[uvl].uv[0] - p0[0] / tile, l0[uvl].uv[1] - p0[1] / tile)
        for l in f.loops:
            q = _proj(l.vert.co, a1)
            l[uvl].uv = (q[0] / tile + ph[0], q[1] / tile + ph[1])
        n += 1
    return n


# ------------------------------------------------------------------ 袖の居る所(段の端で外へ出さない所)
class SodeZone:
    def __init__(self, part, A, B, F):
        self.part, self.A, self.B, self.F = part, A, B, F     # F(x, y) = 背の面の Z(袖の局所)

    def inside(self, Pw):
        q = to_local(self.part, [Pw])[0]
        if abs(q[0]) > NZ.SODE_HALF + 1e-3:
            return False
        top = NZ.SODE_HT + (FUMI / 2.0 - q[2]) * KERI / FUMI
        if q[1] > top + 0.02 or q[1] < top - NZ.SODE_DEPTH - 0.02:
            return False
        return q[2] >= bilin(self.A, self.B, self.F, q[0], q[1]) - 1e-3


# ------------------------------------------------------------------ 袖
def sode_fit_name(side, k, v):
    return "IshidanSodeNozuraFit_%.3f_%.3f_SandoKai%s%d_%s" % (KERI, FUMI, side, k, v)


def sode_side(sd):
    return "W" if "_W_" in sd["name"] else "E"


def sode_field(sd):
    """袖の背の面 Z(x, y)(袖の局所)。当たり = 背から坂上へ(−Z)走らせた光線の最初の当たり + MARGIN・窓 ±0.01 の最大。"""
    side = sode_side(sd)
    e = SODE_E[side]
    yc = NZ.sode_nnori_yc(KERI)
    zf = lambda y: -FUMI / 2.0 - e - NZ.NNORI * (y - yc)
    T = wall_tris(sd["walls"])
    bvh = bvh_of(T)
    A = np.arange(-0.32, 0.3201, RAY)
    B = np.arange(-2.00, 0.6201, RAY)
    z0 = 0.35
    D = cast_grid(bvh, lambda x, y: (x, y, z0), (0, 0, -1), 1.3, A, B)
    Hz = z0 - D
    F = np.empty_like(Hz)
    hitmask = np.zeros(Hz.shape, bool)
    for j, y in enumerate(B):
        f = zf(y)
        for i in range(len(A)):
            h = Hz[i, j]
            if np.isfinite(h) and h >= f - SODE_REACH:
                F[i, j] = h + MARGIN; hitmask[i, j] = True
            else:
                F[i, j] = min(f, FUMI / 2.0 - 0.05)      # 当たりの無い所は今の平面の背(袖が痩せ切る所は坂下の端の手前で止める)
    F = -cliff_safe(opening_far(-F, OPEN), int(round(CELL_S / RAY)))            # 奥 = −Z。目地は跨いで石の面へ・石の段は奥の側で渡る(残りの食い込みは settle が消す)
    yh = B[np.where(hitmask.any(0))[0]]
    return A, B, F, hitmask, (float(yh.min()) if len(yh) else 0.0, float(yh.max()) if len(yh) else 0.0), bvh


def make_sode_fit(sd, v):
    """袖を坂上へ 1 個体継ぎ、(1)当たりの帯より下(見えない)は今の平面の背で切る、(2)帯から上は背の面 F(x, y) へ詰める。"""
    side = sode_side(sd)
    k = int(sd["name"].rsplit("_", 1)[1][:3])
    A, B, F, hitmask, (yv0, yv1), _ = sode_field(sd)
    e = SODE_E[side]; yc = NZ.sode_nnori_yc(KERI)
    zf = lambda y: -FUMI / 2.0 - e - NZ.NNORI * (y - yc)
    V.reset()
    o0, _, _ = NZ.make_sode(KERI, FUMI, v, fresh=False)
    other = "b" if v == "a" else "a"
    o1, _, _ = NZ.make_sode(KERI, FUMI, other, fresh=False)
    o1.data.transform(mathutils.Matrix.Translation((0.0, FUMI, KERI))); o1.data.update()   # 坂上へ 1 駒
    V.dedup_materials()
    name = sode_fit_name(side, k, v)
    whole = V.join([o0, o1], name)
    yk = yv0 - 0.03
    up = whole.copy(); up.data = whole.data.copy(); bpy.context.scene.collection.objects.link(up)
    # (1) 帯より下: 今の平面の背(`make_sode_nnori` と同じ切り)
    NZ.bm_cut_keep(whole, (0.0, 0.0, yk), (0.0, 0.0, 1.0))
    NZ.bm_cut_keep(whole, (0.0, FUMI / 2.0 + e, yc), (0.0, 1.0, -NZ.NNORI))
    # (2) 帯から上: F より坂上の余りを平行な平面で先に落としてから刻む
    NZ.bm_cut_keep(up, (0.0, 0.0, yk), (0.0, 0.0, -1.0))
    band = (B >= yk - 0.01)
    reach = float(max(0.0, max(zf(y) - F[:, j].min() for j, y in enumerate(B) if band[j]))) + 0.04
    NZ.bm_cut_keep(up, (0.0, FUMI / 2.0 + e + reach, yc), (0.0, 1.0, -NZ.NNORI))
    bm = bmesh.new(); bm.from_mesh(up.data)
    zb = lambda x, y: bilin(A, B, F, x, y)
    near = lambda f: any((-vv.co.y) < zb(-vv.co.x, vv.co.z) + 0.03 for vv in f.verts)
    xs = [round(-0.30 + CELL_S * i, 5) for i in range(1, int(round(0.60 / CELL_S)))]
    ys = [round(yk + CELL_S * i, 5) for i in range(1, int((0.62 - yk) / CELL_S) + 1)]
    slice_faces(bm, 0, [-x for x in xs], near)
    slice_faces(bm, 2, ys, near)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if near(f)])
    bm.normal_update(); bm.faces.index_update(); bm.verts.index_update()
    # 詰める前の座標と面の投影軸を層に控える(島を落とすと index が詰まるので層で持つ)
    lx, ly, lz = (bm.verts.layers.float.new(n_) for n_ in ("ox", "oy", "oz"))
    lax = bm.faces.layers.int.new("fax")
    for vv in bm.verts:
        vv[lx], vv[ly], vv[lz] = vv.co.x, vv.co.y, vv.co.z
    for f in bm.faces:
        nx, ny, nz = (abs(c) for c in f.normal)
        f[lax] = 2 if (nz >= nx and nz >= ny) else (0 if nx >= ny else 1)
    top = lambda z: NZ.SODE_HT + (FUMI / 2.0 - z) * KERI / FUMI
    zone, moved = set(), set()
    for vv in bm.verts:
        X, Y, Z = b2u(vv.co)
        zt = zb(X, Y)
        if Z < zt + 0.02:
            zone.add(vv.index)
        if Z < zt:
            moved.add(vv.index)
            Y2 = min(Y, top(zt))                       # 坂下へ寄せた頂点は天端の線の下へ(天端の斜めの一直線を越えない)
            zt = max(zt, zb(X, Y2))
            vv.co[:] = u2b((X, Y2, zt))
    # 丸ごと F より坂上に在った島(頂点が全部寄せられた石)は落とす
    bm.verts.ensure_lookup_table()
    seen, drop = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        st, comp = [v0], []
        seen.add(v0.index)
        while st:
            a_ = st.pop(); comp.append(a_)
            for ed in a_.link_edges:
                b_ = ed.other_vert(a_)
                if b_.index not in seen:
                    seen.add(b_.index); st.append(b_)
        if all(q.index in moved for q in comp):
            drop += comp
    zone -= {q.index for q in drop}
    # 相手の面の標本に当てて食い込みを 0 に
    bw = bvh_of(wall_tris(sd["walls"]))
    samples = []
    for x in np.arange(-0.2995, 0.2996, SAMP):
        for y in np.arange(yv0 - 0.01, 0.62, SAMP):
            h = bw.ray_cast(Vector((x, y, 0.35)), Vector((0, 0, -1)), 1.3)
            if h[0] is None:
                continue
            zw = 0.35 - h[3]
            if zw < zf(y) - SODE_REACH or y > top(zw) + 0.01:
                continue
            samples.append((x, y, zw))
    samples += edge_samples(wall_tris(sd["walls"]), 2,
                            lambda x, y, z: abs(x) <= 0.3 and y >= yv0 - 0.01 and y <= top(z) + 0.01 and z >= zf(y) - SODE_REACH)
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
        bm.verts.index_update(); bm.faces.index_update()
    settle(bm, {vv.index for vv in bm.verts if (-vv.co.y) < zb(-vv.co.x, vv.co.z) + 0.02}, 2, -1, samples, CELL_S, name, iters=20)
    for vv in bm.verts:                              # settle で坂上へは動かない(Z は増えるだけ)が、念のため天端を越えさせない
        X, Y, Z = b2u(vv.co)
        if Y > top(Z) + 1e-6:
            vv.co.z = top(Z)
    # box_uv: ax 0(X 向き)は (q.y, q.z)、ax 2(Blender z 向き)は (q.x, q.y)、ax 1 は (q.x, q.z)
    uvl = bm.loops.layers.uv.active
    for f in bm.faces:
        ax = f[lax]
        for l in f.loops:
            q = l.vert
            d = q.co - Vector((q[lx], q[ly], q[lz]))
            if d.length_squared < 1e-14:
                continue
            du, dv = (d.y, d.z) if ax == 0 else ((d.x, d.y) if ax == 2 else (d.x, d.z))
            u, w_ = l[uvl].uv
            l[uvl].uv = (u + du / NZ.TILE, w_ + dv / NZ.TILE)
    reproject_turned(bm, lambda f: f[lax], lambda q: (q.co - Vector((q[lx], q[ly], q[lz]))).length_squared > 1e-14, NZ.TILE)
    bm.verts.layers.float.remove(lx); bm.verts.layers.float.remove(ly); bm.verts.layers.float.remove(lz)
    bm.faces.layers.int.remove(lax)
    bm.to_mesh(up.data); bm.free(); up.data.update()
    o = V.join([whole, up], name)
    for vt in o.data.vertices:
        vt.co.x = max(-NZ.SODE_HALF, min(NZ.SODE_HALF, vt.co.x))
    bmesh_loose(o)
    V.set_origin(o, (0, 0, 0))
    print("SFIT %s 帯 Y %.2f..0.62・余りを落とす平行面 %.3f・落とした島の頂点 %d" % (name, yk, reach, len(drop)))
    return o, name, (A, B, F)


def bmesh_loose(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[vv for vv in bm.verts if not vv.link_faces], context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()


def _drop_flat_parts(bm, axis):
    """詰めて厚みが 0.002 未満になった島(背より向こうに丸ごと在った石)を落とす。"""
    bm.verts.ensure_lookup_table()
    seen, drop = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        st, comp = [v0], []
        seen.add(v0.index)
        while st:
            a = st.pop(); comp.append(a)
            for ed in a.link_edges:
                b = ed.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); st.append(b)
        ext = sorted(max(q.co[i] for q in comp) - min(q.co[i] for q in comp) for i in range(3))
        if ext[0] < 0.002 and len(comp) > 3:
            # 板(芯の板は厚み 0 の一枚もの)は落とさない: 面積が大きく、法線が X を向く物
            nrm = [f.normal for q in comp for f in q.link_faces]
            if nrm and all(abs(n.x) > 0.9 for n in nrm):
                continue
            drop += comp
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
    return len(drop)


# ------------------------------------------------------------------ 段石
def dan_fit_name(i, v):
    return "DanFit_%s_%s_%s_%s_SandoKai%d" % (SB.cs_f3(KERI), SB.cs_f3(FUMI), SB.cs_f3(W), v, i)


def end_field(st, end, zones):
    """段の端 s の X 面 V(y, z)(s 側で見た s·X)。"""
    s = -1 if end["side"] == "-X" else 1
    T = wall_tris(end["walls"])
    bvh = bvh_of(T)
    lap, _ = SB.lap_of(KERI, FUMI, W)
    ybot = -(KERI + SB.BODY)
    A = np.arange(ybot - 0.01, 0.0101, RAY)
    B = np.arange(-(FUMI / 2 + lap) - 0.01, FUMI / 2 + 0.0101, RAY)
    x0 = W2 - 0.70
    D = cast_grid(bvh, lambda y, z: (s * x0, y, z), (s, 0, 0), 0.70 + REACH + 0.05, A, B)
    Q = x0 + D
    R = np.empty_like(Q)
    nhit = 0
    for i, y in enumerate(A):
        for j, z in enumerate(B):
            q = Q[i, j]
            r = (q - MARGIN) if (np.isfinite(q) and q <= W2 + REACH) else W2
            if np.isfinite(q) and q <= W2 + REACH:
                nhit += 1
            R[i, j] = r
    R = opening_far(R, OPEN)
    for i, y in enumerate(A):
        for j, z in enumerate(B):
            if R[i, j] > W2:
                Pw = to_world(st, [(s * (W2 + 0.004), y, z)])[0]
                if any(zn.inside(Pw) for zn in zones):
                    R[i, j] = W2                            # 袖の居る所は小口のまま(袖の側面に突き付く)
    return s, A, B, cliff_safe(R), nhit, bvh


def make_dan_fit(st, i, zones):
    v = "ab"[i % 2]
    name = dan_fit_name(i, v)
    fields = [end_field(st, e, zones) for e in st["ends"]]
    V.reset()
    mat = SB.danishi_material()
    rng = SB.rng_of("dan", "%.3f" % KERI, "%.3f" % FUMI, "%.3f" % W, v)
    cuts = SB._cuts(W, v)
    lap, drop = SB.lap_of(KERI, FUMI, W)
    assert drop == 0.0
    objs = []
    for k in range(len(cuts) - 1):
        objs.append(SB._stone(cuts[k], cuts[k + 1], -FUMI / 2.0, FUMI / 2.0 + lap, -(KERI + SB.BODY), 0.0,
                              mat, rng, "%s_s%d" % (name, k), tile=SB.DANISHI_TILE, tile_jit=True))
    log = []
    fields_bw = {f[0]: f[5] for f in fields}
    for (s, A, B, Vf, nhit, _) in fields:
        so = objs[-1] if s < 0 else objs[0]          # Blender x = −Unity X ⇒ cuts の先頭が Unity +X の端
        ext = float(Vf.max()) - W2
        if ext > -1e-6:
            SB._stretch_end(so, s, W, max(0.0, ext) + 0.02)
        bm = bmesh.new(); bm.from_mesh(so.data)
        lim = min(float(Vf.min()), W2) - 0.05
        endish = lambda f: any(s * (-vv.co.x) > lim for vv in f.verts)
        ybot = -(KERI + SB.BODY)
        ys = planes(ybot, 0.0, -0.27, -0.01)
        zs = planes(-(FUMI / 2 + lap), FUMI / 2, -0.28, FUMI / 2 - 0.01)
        slice_faces(bm, 2, ys, endish)
        slice_faces(bm, 1, [-z for z in zs], endish)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if endish(f)])
        bm.normal_update(); bm.faces.index_update(); bm.verts.index_update()
        fax = {f.index: max(range(3), key=lambda kk: abs(f.normal[kk])) for f in bm.faces}
        orig = {vv.index: vv.co.copy() for vv in bm.verts}
        zone = set()
        for vv in bm.verts:
            X, Y, Z = b2u(vv.co)
            xt = bilin(A, B, Vf, Y, Z)
            if s * X > xt - 0.02:
                zone.add(vv.index)
            if s * X > xt:
                vv.co.x = -s * xt
        # 相手の面の標本(0.0025 升・見える帯と少しの外)に当てて食い込みを 0 に(袖の居る所は数えない)
        bw = fields_bw[s]
        samples = []
        x0 = W2 - 0.70
        for y in np.arange(-0.26, 0.0, SAMP):
            for z in np.arange(-0.28, FUMI / 2 + 0.001, SAMP):
                h = bw.ray_cast(Vector((s * x0, y, z)), Vector((s, 0, 0)), 0.70 + REACH)
                if h[0] is None:
                    continue
                samples.append((y, z, s * (x0 + h[3])))
        # 石の角・稜(頂点と辺の上の点)も。袖の居る所・小口より 0.40 遠い所は数えない
        def _keep(y, z, x, s=s):
            if not (-0.26 <= y <= 0.0 and -0.28 <= z <= FUMI / 2 + 0.001) or s * x > W2 + REACH or s * x < W2 - 0.70:
                return False
            if s * x > W2:
                Pw = to_world(st, [(s * (W2 + 0.004), y, z)])[0]
                if any(zn.inside(Pw) for zn in zones):
                    return False
            return True
        ends_ = [e_ for e_ in st["ends"] if (e_["side"] == "+X") == (s > 0)]
        samples += [(a, b, w) for (a, b, w) in edge_samples(wall_tris(ends_[0]["walls"]), 0, lambda a, b, w: _keep(a, b, w))]
        settle(bm, zone, 0, s, samples, CELL, "%s %s" % (name, "LR"[s > 0]))
        # _stone の UV: ax 2(Blender z 向き)は (x, y)、ax 1 は (x, z)、ax 0 は (y, z)
        fix_uv(bm, orig, fax, lambda ax, d: ((0.0, 0.0) if ax == 0 else (d.x / SB.DANISHI_TILE, 0.0)))
        reproject_turned(bm, lambda f: fax.get(f.index, 0), lambda q: (q.co - orig[q.index]).length_squared > 1e-14, SB.DANISHI_TILE)
        # (溶かさない: 潰れた面は面積 0 のまま残す ── 溶かすと多角形の割り方が変わり、測った面と書き出す面が食い違う)
        bmesh.ops.delete(bm, geom=[vv for vv in bm.verts if not vv.link_faces], context='VERTS')
        bm.to_mesh(so.data); bm.free(); so.data.update()
        vis = Vf[(A >= -KERI) & (A <= 0.0)][:, (B >= -FUMI / 2) & (B <= FUMI / 2)]
        log.append("%s 端: 当たり %d 本・見える帯の端 s·X %.3f〜%.3f(小口 %.4f)" % ("LR"[s > 0], nhit, vis.min(), vis.max(), W2))
    V.dedup_materials()
    o = V.join(objs, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    for l_ in log:
        print("DFIT %s %s" % (name, l_))
    return o, name, fields


# ------------------------------------------------------------------ 測る(焼いた駒 × 相手の三角形)
def _dilate(M, k):
    P = np.pad(M, k, mode="constant")
    out = np.zeros(M.shape, bool)
    for di in range(2 * k + 1):
        for dj in range(2 * k + 1):
            out |= P[di:di + M.shape[0], dj:dj + M.shape[1]]
    return out


def _summ(G, J, keep, Dw, U, Vc):
    """G = 隙(> 0)/ めり込み(< 0)の升、J = 相手の目地の升、keep = 数える升、Dw = 相手の面(奥ほど大)、U・Vc = 升の座標。
    「縁」= 相手の目地・石の段(隣の升と 0.02 以上違う)から 0.01 以内の帯(刻む升 0.01 の一つ分 ── 詰めた面はそこで斜めに渡る)。"""
    fin = np.isfinite(Dw)
    cl = np.zeros(Dw.shape, bool)
    d0 = np.abs(np.diff(np.where(fin, Dw, 0.0), axis=0)) > 0.02
    d1 = np.abs(np.diff(np.where(fin, Dw, 0.0), axis=1)) > 0.02
    cl[:-1, :] |= d0; cl[1:, :] |= d0; cl[:, :-1] |= d1; cl[:, 1:] |= d1
    band = _dilate(J | cl | ~fin, 4)
    ok = keep & np.isfinite(G)
    g_in = G[ok & ~band]
    g_j = G[ok & J]
    r = {"n": int(ok.sum()), "n_face": int(g_in.size), "n_joint": int(g_j.size), "n_edge": int((ok & band & ~J).sum())}
    if ok.any():
        k = np.where(ok, G, np.inf)
        ia = np.unravel_index(np.argmin(k), k.shape)
        r["bite_max"] = round(float(max(0.0, -G[ia])), 4)
        r["bite_at"] = [round(float(U[ia[0]]), 4), round(float(Vc[ia[1]]), 4)]
        r["bite_on_face"] = round(float(max(0.0, -g_in.min())) if g_in.size else 0.0, 4)
    r["gap_face_max"] = round(float(g_in.max()) if g_in.size else 0.0, 4)
    r["gap_face_p99"] = round(float(np.percentile(g_in, 99)) if g_in.size else 0.0, 4)
    r["gap_face_median"] = round(float(np.median(g_in)) if g_in.size else 0.0, 4)
    r["gap_face_over_0.01"] = int((g_in > 0.01).sum())
    ge = G[ok & band & ~J]
    r["gap_edge_over_0.01"] = int((ge > 0.01).sum())
    r["gap_edge_max"] = round(float(ge.max()) if ge.size else 0.0, 4)
    r["gap_joint_max"] = round(float(g_j.max()) if g_j.size else 0.0, 4)
    return r


def _joint_mask(Dw, k=8, tol=0.01):
    """相手の石の面の場(奥ほど大きい)で、幅 ±k 升より細く tol より深い奥まり = 石と石の目地。"""
    Dm = np.where(np.isfinite(Dw), Dw, np.nan)
    fill = np.where(np.isfinite(Dm), Dm, np.nanmax(Dm) if np.isfinite(np.nanmax(Dm)) else 0.0)
    return np.isfinite(Dm) & (fill - opening_far(fill, k) > tol)


def measure_dan(o, st, fields):
    """見える帯(Y −蹴上..0・Z ±踏面/2)を 0.0025 升で、相手の面の当たり xw と段の端 xs を X に沿って測る。
    隙 = xw − xs(> 0 が口)、めり込み = xs − xw。相手の当たりが無い所・0.40 より遠い所・袖の居る所は数えない。
    相手の石と石の目地(幅 0.04 より細い奥まり)は別に数える(段の端は目地を埋めず石の面で跨ぐ)。"""
    bo = bvh_obj(o)
    res = []
    ys = np.arange(-KERI + 0.00125, 0.0, 0.0025)
    zs = np.arange(-FUMI / 2 + 0.00125, FUMI / 2, 0.0025)
    for (s, A, B, Vf, nhit, bw) in fields:
        XW = np.full((len(ys), len(zs)), np.inf); XS = XW.copy(); keep = np.zeros(XW.shape, bool)
        x0 = W2 - 0.70
        for a, y in enumerate(ys):
            for b, z in enumerate(zs):
                hw = bw.ray_cast(Vector((s * x0, y, z)), Vector((s, 0, 0)), 0.70 + REACH)
                if hw[0] is None:
                    continue
                xw = x0 + hw[3]; XW[a, b] = xw
                hs = bo.ray_cast(Vector((s * (xw + 0.6), y, z)), Vector((-s, 0, 0)), 2.0)
                if hs[0] is None:
                    continue
                XS[a, b] = xw + 0.6 - hs[3]
                keep[a, b] = True
                if XS[a, b] >= W2 - 1e-4 and xw > W2 + 1e-4:
                    Pw = to_world(st, [(s * (W2 + 0.004), y, z)])[0]
                    if any(zn.inside(Pw) for zn in ZONES):
                        keep[a, b] = False
        r = _summ(XW - XS, _joint_mask(XW), keep, XW, ys, zs)
        r["end"] = "LR"[s > 0]
        res.append(r)
    return res


def measure_sode(o, sd):
    """袖の背: 相手の面の当たり zw(背から −Z へ)と袖の背 zs(相手の向こうから +Z へ最初の当たり)。隙 = zs − zw・めり込み = zw − zs。
    天端より上(袖が無い所)・袖の芯の目地(0.017 前後)で奥まで抜ける所は、袖の側の目地として除く(袖の石どうしの間)。"""
    T = wall_tris(sd["walls"])
    bw = bvh_of(T)
    bo = bvh_obj(o)
    xs_ = np.arange(-0.29875, 0.299, 0.0025)
    ys_ = np.arange(-2.0, 0.62, 0.0025)
    e = SODE_E[sode_side(sd)]; yc = NZ.sode_nnori_yc(KERI)
    ZWf = np.full((len(xs_), len(ys_)), np.inf); ZS = ZWf.copy(); keep = np.zeros(ZWf.shape, bool)
    NZa = np.zeros(ZWf.shape)
    for a, x in enumerate(xs_):
        for b, y in enumerate(ys_):
            hw = bw.ray_cast(Vector((x, y, 0.35)), Vector((0, 0, -1)), 1.3)
            if hw[0] is None:
                continue
            zw = 0.35 - hw[3]
            if zw < -FUMI / 2 - e - NZ.NNORI * (y - yc) - SODE_REACH:
                continue
            ZWf[a, b] = -zw
            hs = bo.ray_cast(Vector((x, y, zw - 0.6)), Vector((0, 0, 1)), 1.5)
            if hs[0] is None:
                continue
            zs = zw - 0.6 + hs[3]
            topy = NZ.SODE_HT + (FUMI / 2.0 - max(zs, zw)) * KERI / FUMI
            if y > topy - 0.005:
                continue
            ZS[a, b] = zs
            keep[a, b] = True
            NZa[a, b] = abs(hs[1][2])
    G = ZS + ZWf            # zs − zw
    # 袖の石どうしの目地(当たった面が背の面でなく石の脇 = 法線が Z を向かない)は袖の側の目地で、相手との隙でない
    ZSf = np.where(np.isfinite(ZS), ZS, -np.inf)
    own = keep & (((NZa < 0.5) & (G > 0.01)) | _joint_mask(np.where(keep, ZS, np.inf)))
    r = _summ(np.where(own, np.nan, G), _joint_mask(ZWf), keep & ~own, ZWf, xs_, ys_)
    r["n_sode_own_joint"] = int(own.sum())
    return r


def check_common(o, kind):
    ok = []
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats = sorted({m.name for m in o.data.materials})
    want = {"Danishi"} if kind == "dan" else {"Kirishi", "Danishi"}
    ok.append(("材は %s だけ" % "/".join(sorted(want)), set(mats) <= want, ",".join(mats)))
    U = [b2u(v.co) for v in o.data.vertices]
    if kind == "dan":
        ok.append(("踏面 Y 最大 = 0", abs(max(u[1] for u in U)) < 1e-4, "%.5f" % max(u[1] for u in U)))
        ok.append(("蹴上の面 Z 最大 = +踏面/2", abs(max(u[2] for u in U) - FUMI / 2) < 1e-3, "%.4f" % max(u[2] for u in U)))
        ok.append(("底 Y = −(蹴上+胴)", abs(min(u[1] for u in U) + KERI + SB.BODY) < 1e-4, "%.4f" % min(u[1] for u in U)))
    else:
        ok.append(("石は X = ±0.30 を越えない", max(abs(u[0]) for u in U) <= NZ.SODE_HALF + 1e-6, "%.4f" % max(abs(u[0]) for u in U)))
        top = lambda z: NZ.SODE_HT + (FUMI / 2.0 - z) * KERI / FUMI
        over = max(u[1] - top(u[2]) for u in U)
        ok.append(("天端が段鼻の線 +0.30 の斜めの一直線を越えない(≤ 0.005)", over <= 0.005, "%.5f" % over))
        ok.append(("坂下の端は Z = +踏面/2", abs(max(u[2] for u in U) - FUMI / 2) < 1e-4, "%.4f" % max(u[2] for u in U)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t in ok if not t[1])


def tri_count(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def ubounds(o):
    U = np.array([b2u(v.co) for v in o.data.vertices])
    return [[round(float(U[:, k].min()), 4), round(float(U[:, k].max()), 4)] for k in range(3)]


# ------------------------------------------------------------------ 撮る
REF = None


def world_b(Pw):
    return Vector((-(Pw[0] - REF[0]), -(Pw[2] - REF[2]), Pw[1] - REF[1]))


def import_placed(path, part):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    sx, sy, sz = part["scale"]
    S = mathutils.Matrix.Diagonal((sx, sz, sy, 1.0))
    R = mathutils.Matrix.Rotation(math.radians(-part["euler"][1]), 4, 'Z')
    T = mathutils.Matrix.Translation(world_b(part["pos"]))
    for o in new:
        o.matrix_world = T @ R @ S @ o.matrix_world
    return new


def wall_soup(fit):
    """相手の石の三角形(退ける前・ワールドで重複を除く)を一つのメッシュに(撮るためだけ・書き出さない)。"""
    seen = set(); vs = []; fs = []
    parts = list(fit["steps"]) + list(fit["sodeBacks"])
    for part in parts:
        groups = [e["walls"] for e in part["ends"]] if "ends" in part else [part["walls"]]
        for walls in groups:
            T = wall_tris(walls)
            if not len(T):
                continue
            Wt = to_world(part, T.reshape(-1, 3)).reshape(-1, 3, 3)
            for t in Wt:
                key = tuple(sorted(tuple(np.round(p, 3)) for p in t))
                if key in seen:
                    continue
                seen.add(key)
                b = len(vs)
                vs += [tuple(world_b(p)) for p in t]
                fs.append((b, b + 1, b + 2))
    me = bpy.data.meshes.new("WallSoup"); me.from_pydata(vs, [], fs); me.update()
    o = bpy.data.objects.new("WallSoup", me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new("WallSoupShot"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Base Color'].default_value = (0.55, 0.50, 0.44, 1); b.inputs['Roughness'].default_value = 0.95
    m.use_backface_culling = False
    me.materials.append(m)
    return o


def _ortho_shot(cam, foc, scale, path):
    """真上の正投影・マゼンタの背景(抜けがあれば桃色が見える)。"""
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1400
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.25
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); sun.data.energy = 3.0
    sun.rotation_euler = (0.3, 0.2, 0.5); sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new("Cam"); cd.type = 'ORTHO'; cd.ortho_scale = scale
    co_ = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(co_); sc.camera = co_
    co_.location = cam
    co_.rotation_euler = (Vector(foc) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
    V.render(path)


def render_all(fit, made):
    """段 0〜4 と袖 2 本を据えた位置で読み、相手の石(退ける前の三角形・茶)と一緒に撮る。
    (名, 基準の駒, カメラ(局所・sx を掛ける前), 見る点, レンズ mm(負 = 真上の正投影の幅 m))。"""
    global REF
    V.reset()
    REF = fit["steps"][2]["pos"]
    for part, path in made:
        import_placed(path, part)
    NZ.hook_stone_textures()
    ws = wall_soup(fit)
    ws.data.materials[0].node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.30, 0.24, 0.18, 1)
    views = [
        ("ends_obl", 3, (2.0, 1.1, 1.6), (W2 + 0.0, -0.1, -0.2), 28),
        ("sode_in", 1, (2.2, 0.9, 1.2), (W2 + 0.1, 0.0, -0.15), 35),
        ("sode_out", 1, (3.9, 1.0, 1.2), (W2 + 0.45, 0.05, -0.2), 35),
        ("top_ends", 3, (W2, 3.0, 0.0), (W2, 0.0, 0.001), -2.2),
        ("top_sode", 1, (W2 + 0.25, 3.0, -0.1), (W2 + 0.25, 0.0, -0.101), -1.4),
    ]
    shots = []
    for side, sx in (("W", -1), ("E", 1)):
        for tag, k, c, f, lens in views:
            st = fit["steps"][k]
            cam = world_b(to_world(st, [(sx * c[0], c[1], c[2])])[0])
            focus = world_b(to_world(st, [(sx * f[0], f[1], f[2])])[0])
            p = os.path.join(SHOT, "sanno_sando_fit_%s_%s.png" % (side, tag))
            if lens < 0:
                _ortho_shot(tuple(cam), tuple(focus), -lens, p)
            else:
                NZ.studio_run([], tuple(cam), tuple(focus), lens, p)
            for ob in [o for o in bpy.data.objects if o.type in ('LIGHT', 'CAMERA')]:
                bpy.data.objects.remove(ob)
            shots.append(p)
    return shots


# ------------------------------------------------------------------ 本体
ZONES = []


def main():
    global ZONES
    fit = load_fit()
    what = POS[0] if POS else "all"
    only = set(OPT.get("only", "").split(",")) - {""}
    report = {"dan": [], "sode": []}
    bad = 0
    # 袖の背の面を先に決める(段 1 の端で「袖の居る所」を知るため)
    ZONES = []
    fields_s = {}
    for sd in fit["sodeBacks"]:
        A, B, F, hm, yv, _ = sode_field(sd)
        fields_s[sd["name"]] = (A, B, F)
        ZONES.append(SodeZone(sd, A, B, F))
    made = []
    if what in ("sode", "all"):
        for sd in fit["sodeBacks"]:
            side = sode_side(sd)
            if only and side not in only:
                continue
            v = sd["fbx"].rsplit("_", 1)[1][0]
            o, name, _ = make_sode_fit(sd, v)
            print("SFIT 検算 %s" % name)
            bad += check_common(o, "sode")
            m = measure_sode(o, sd)
            print("SFIT 当たり %s %s" % (name, m))
            report["sode"].append({"name": name, "for": sd["name"], "tris": tri_count(o), "bounds": ubounds(o), "measure": m})
            path = os.path.join(OUT, name + ".fbx")
            V.export_fbx([o], path)
            print("SFIT 書き出し " + path)
            made.append((sd, path))
    if what in ("dan", "all"):
        for i, st in enumerate(fit["steps"]):
            if only and str(i) not in only:
                continue
            fields = [end_field(st, e, ZONES) for e in st["ends"]]
            vis_hits = sum(int(np.isfinite(f[3]).sum() and ((f[3][(f[1] >= -KERI) & (f[1] <= 0)][:, (f[2] >= -FUMI / 2) & (f[2] <= FUMI / 2)] < W2 - 1e-4).sum()
                                                            + (f[3][(f[1] >= -KERI) & (f[1] <= 0)][:, (f[2] >= -FUMI / 2) & (f[2] <= FUMI / 2)] > W2 + 1e-4).sum())) for f in fields)
            if vis_hits == 0:
                print("DFIT 段 %d: 相手の石に当たりが無い ⇒ 焼かない(%s のまま)" % (i, st["fbx"]))
                report["dan"].append({"step": i, "name": None, "keep": st["fbx"]})
                made.append((st, os.path.join(V.REPO, st["fbx"])))
                continue
            o, name, fields = make_dan_fit(st, i, ZONES)
            print("DFIT 検算 %s" % name)
            bad += check_common(o, "dan")
            m = measure_dan(o, st, fields)
            print("DFIT 当たり %s %s" % (name, m))
            report["dan"].append({"step": i, "name": name, "for": st["name"], "was": st["fbx"], "tris": tri_count(o),
                                  "bounds": ubounds(o), "measure": m})
            path = os.path.join(OUT, name + ".fbx")
            V.export_fbx([o], path)
            print("DFIT 書き出し " + path)
            made.append((st, path))
    if LOGJ:
        with open(LOGJ, "w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=1)
    if RENDER and what == "all":
        for p in render_all(fit, made):
            print("FIT 検証レンダ " + p)
    if bad:
        sys.exit("FIT ⛔ 検算が %d 件落ちた" % bad)


if __name__ == "__main__":
    main()
