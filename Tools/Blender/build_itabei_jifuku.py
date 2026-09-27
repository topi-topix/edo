"""板塀の**地覆(じふく)**と**光付けの柱** ── EDO-0437(山王 前庭の板塀 Ita_ZN・Ita_ZNE・Ita_ZSW・Ita_ZSE・施主裁定 案A 2026-09-27)。

    blender --background --python Tools/Blender/build_itabei_jifuku.py -- [--render]

⭐ **なぜ。** 在庫の板塀(`itabei.obj`)は板の下端が y=0.117(柱の根元の台=小さな礎石の底より 0.128 上)で、
   野面の天端の目地の窪みでは板の下に最大 0.35 の隙が透けた。施主の決まり(docs/oki-kata.md §4・2026-09-27)は
   地面に置く物の接地 ±0.01・部材どうしの隙 1mm 未満。

⭐ **形の決め(案A の起こし方)。** 板は在庫のまま(`Itabei_Ita_1.410`・下端 0.117)で、その下に**地覆**
   (板の下の横木=土台)を一本足し、**地覆の下端と柱の下端を、据えた所の地表・石の天端へ光付け(ひかりつけ)する**。
   光付けは柱・土台を礎石・野面石の凹凸に合わせて木の側を削り合わせる在来の大工の手(石場建て)。
   ⇒ 下端の形は**据えた場所の従属値**なので、ここでは「光付けの代(しろ)」を持った直の地覆と柱を焼き、
   削る(下端の頂点を地表まで上げる)のは Unity で据えるときに EdoBuild が測って行う(据えを変えても焼き直さない)。
   典拠: 光付け=在来の石場建ての仕口(確度 B)/ 板塀の下に地覆(土台)を通す=社寺・武家の板塀の一般類型(確度 U)。

⛔ **ゼロから起こさない。** 柱は在庫の柱身(`g pole` の 0.082×0.074 角)をそのまま使い、下へ継ぎ足すだけ
   (継ぎ足しの UV は柱身の下端から上へ折り返す=木理の密度を保つ)。根元の台(小さな礎石)は外す
   ── 地覆の小口と 0.028 重なり、野面の上では台そのものが浮くため。地覆は在庫のアトラス `itabei.jpg` の
   貫と同じ帯(右端の縦の板 u 0.858..0.975 を寝かせ、走り = v 0.030..0.724)を矩形で貼る(一点貼りにしない)。材 `itabei` 一つ。

【座標(Unity ローカル)】幅 = X(走り)/ 高さ = Y / 厚み = Z。y = 0 は**板の y = 0**(= 在庫の板塀の地盤の基準)。
   - 地覆: x −0.705..+0.705(= 板 `Itabei_Ita_1.410` と同じ幅・同じピボット=板の中心)/ y −DEPTH..0.117(上端 = 板の下端)
     / z ±0.037(= 柱身の厚みと面一)。**板と同じ変換(位置・回転・走りの縮尺)で置けば板の真下に納まる。**
     下端は走りに 141 分割(0.0100 刻み)× 厚みに NG=9 列(0.0093 刻み)の格子。
   - 柱: 柱身の芯がピボット(x = 0・z = 0)/ y −DEPTH..1.439。下端は NG×NG=9×9 の格子(刻み ≤0.010・柱身の側面は縦に 8 割)。
【光付けの印】**局所 y ≤ −DEPTH + 0.001 の頂点が削る頂点**(下端の格子)。第2の UV(Unity の `mesh.uv2`)に
   その頂点の **d(uv)/dy**(y を 1 上げたとき uv がどれだけ動くか)を入れてある ⇒ 頂点を Δy 上げたら `uv += uv2·Δy`
   で木理の密度が保たれる。下面(地に伏せる面)は 0。**削り終えたら uv2 を消す**(ライトマップの UV と取り違えない)。

リファレンス実装: この中の `scribe()` が EdoBuild の光付けの手本(窓の最大・上端の手前で止める・uv の引き直し)。
"""
import bpy, bmesh, os, sys, math, random
import mathutils
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ES = 1.818
SRC = os.path.join(V.REPO, "Assets", "edogoyomi", "obj_itabei", "itabei.obj")
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")
DEPTH = 0.60                   # 光付けの代(板の y=0 から下)
NCOL = 1                       # 地覆の下端の走り方向の分割 ── 1 = 両端だけ(施主 2026-09-27「点数は出来るかぎり少なく」)。石の形に要る所だけ Unity の EdoBuild.RefineForScribe が割り足す
NG = 2                         # 地覆の厚み・柱の下端の格子の列の数 ── 2 = 角だけ(同上。旧 9 列は目地の上を測った誤りの ±0.02 裁定に合わせた値で廃止 ── docs/oki-kata.md §0a)
UR = (0.858, 0.975)            # 地覆の高さ → u(在庫の貫が使うアトラス右端の縦の板の帯 u 0.855..0.978)
VR = (0.030, 0.724)            # 地覆の走り → v(在庫の貫と同じ v 0.030..0.724 = 1.41m)
UB = (0.26, 0.752, 0.98, 0.857)  # 柱の下面(地に伏せる面)に貼る帯
TOP_STOP = 0.02                # 削りは上端の手前 0.02 で止める(面が裏返らない)

NAME_J = "Itabei_Jifuku_1.410_Hk%.2f" % DEPTH
NAME_H = "Itabei_Hashira_Hk%.2f" % DEPTH

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DO_RENDER = "--render" in argv


# ───────────────────────── 在庫の読み込みと切り分け(build_itabei_bunkatsu と同じ) ─────────────────────────
def load_src():
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=SRC)          # 既定 forward −Z / up Y = Unity の .obj 取り込みと同じ向き
    got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    o = V.join(got, "src") if len(got) > 1 else got[0]
    o.name = "src"; o.scale = (ES, ES, ES)
    V.sel([o]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def ext(o):
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    return (min(w.x for w in ws), max(w.x for w in ws), min(w.y for w in ws), max(w.y for w in ws),
            min(w.z for w in ws), max(w.z for w in ws))


def split_parts(o):
    V.sel([o]); bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = [p for p in bpy.data.objects if p.type == 'MESH' and (p is o or p.name.startswith("src"))]
    post = foot = None; boards = []
    for p in parts:
        x0, x1, y0, y1, z0, z1 = ext(p)
        if z1 < 0.06: foot = p
        elif x1 - x0 < 0.1 and z1 - z0 > 1.0: post = p
        else: boards.append(p)
    assert post is not None and foot is not None and len(boards) == 11, (post, foot, len(boards))
    return post, foot, boards


# ───────────────────────── 柱(光付けの代つき) ─────────────────────────
def build_hashira(post):
    """柱身の下端の面を外し、側面を縦に 2 割り、下へ DEPTH まで継ぐ。継ぎ足しの UV は柱身の下端から上へ折り返す。"""
    me = post.data
    px0, px1, py0, py1, pz0, pz1 = ext(post)
    cx = (px0 + px1) / 2
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    uv2 = bm.loops.layers.uv.new("scribe_duv")
    eps = 1e-4
    # 下端の面を外す
    bot = [f for f in bm.faces if all(abs(v.co.z - pz0) < eps for v in f.verts)]
    assert len(bot) == 1, len(bot)
    bmesh.ops.delete(bm, geom=bot, context='FACES_ONLY')
    # 側面の上下の水平辺を NG−1 割り(下端の NG×NG 格子と継ぎ目で頂点が揃うように)
    hed = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < eps]
    assert len(hed) == 8, len(hed)
    if NG > 2: bmesh.ops.subdivide_edges(bm, edges=hed, cuts=NG - 2, use_grid_fill=False)
    # 柱身の側面ごとに、下端の uv と d(uv)/dz を読む
    xs = [px0 + (px1 - px0) * i / (NG - 1) for i in range(NG)]; ys = [py0 + (py1 - py0) * j / (NG - 1) for j in range(NG)]
    sides = []   # (法線, [(下端の点, uv_bot, g=d(uv)/dz)])
    for f in bm.faces:
        n = f.normal
        if abs(n.z) > 0.5: continue
        lo = [l for l in f.loops if abs(l.vert.co.z - pz0) < eps]
        hi = [l for l in f.loops if abs(l.vert.co.z - pz1) < eps]
        assert len(lo) == 2 and len(hi) == 2
        pts = []
        for l in lo:
            # 同じ縦の辺の上の頂点
            h = min(hi, key=lambda k: (k.vert.co.xy - l.vert.co.xy).length)
            g = (h[uv].uv - l[uv].uv) / (pz1 - pz0)
            pts.append((l.vert.co.copy(), l[uv].uv.copy(), g))
        sides.append((n.copy(), pts))
    for f in bm.faces:
        for l in f.loops: l[uv2].uv = (0.0, 0.0)
    # 継ぎ足しの頂点(柱身とは分ける = 柱身の UV を触らない)
    zb = -DEPTH
    top = {}; btm = {}
    def key(x, y): return (round(x, 5), round(y, 5))
    L = NG - 1
    for i in range(NG):
        for j in range(NG):
            if 0 < i < L and 0 < j < L:
                btm[(i, j)] = bm.verts.new((xs[i], ys[j], zb)); continue   # 下面の内の点
            top[(i, j)] = bm.verts.new((xs[i], ys[j], pz0))
            btm[(i, j)] = bm.verts.new((xs[i], ys[j], zb))
    # 周の並び(i, j)を反時計回りで
    ring = [(i, 0) for i in range(L)] + [(L, j) for j in range(L)] + [(i, L) for i in range(L, 0, -1)] + [(0, j) for j in range(L, 0, -1)]
    newf = []
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        f = bm.faces.new((btm[a], btm[b], top[b], top[a]))
        newf.append(f)
        # 外向きに揃える
        mid = (mathutils.Vector((xs[a[0]], ys[a[1]], 0)) + mathutils.Vector((xs[b[0]], ys[b[1]], 0))) / 2
        out = mid - mathutils.Vector((cx, (py0 + py1) / 2, 0))
        f.normal_update()
        if f.normal.dot(out) < 0: f.normal_flip()
        # UV: この面と向きの揃う柱身の側面の、同じ位置の下端の uv と g から折り返す
        # ⚠ 柱身の側面は縦に NG−1 割ってあるので、同じ向きの帯が面ごとに NG−1 本ある。「向きの一番揃う帯」を
        #   一本だけ拾って距離で外挿すると、その帯の外の点の u が柱の帯の外(アトラスの白い余白 u 0.25..0.27)へ
        #   はみ出した(2026-09-27 EDO-0437 柱の足元の白い四角)。⇒ 点ごとに**その点を含む帯**を引き、帯の中で内挿する。
        n = f.normal
        strips = [s for s in sides if s[0].dot(n) > 0.99]
        def seg_at(p):
            best = None
            for s in strips:
                (p0, u0, g0), (p1, u1, g1) = s[1]
                ab = p1.xy - p0.xy; L2 = max(ab.length_squared, 1e-12)
                t = (p.xy - p0.xy).dot(ab) / L2
                dist = (p.xy - (p0.xy + ab * min(max(t, 0.0), 1.0))).length
                if best is None or dist < best[0]: best = (dist, min(max(t, 0.0), 1.0), u0, u1, g0, g1)
            assert best[0] < 1e-4, best[0]
            return best
        for l in f.loops:
            p = l.vert.co
            _, t, u0, u1, g0, g1 = seg_at(p)
            ub = u0.lerp(u1, t); g = g0.lerp(g1, t)
            d = pz0 - p.z                                 # 下へ d 継いだ所 = 上へ d 折り返した所
            l[uv].uv = ub + g * d
            l[uv2].uv = -g                                # y を上げると折り返しの uv は下端の側へ戻る
    # 下面(NG×NG 格子の (NG−1)² 枚)── 地に伏せる面。uv は帯の端、uv2 = 0
    for i in range(NG - 1):
        for j in range(NG - 1):
            f = bm.faces.new((btm[(i, j)], btm[(i, j + 1)], btm[(i + 1, j + 1)], btm[(i + 1, j)]))
            f.normal_update()
            if f.normal.z > 0: f.normal_flip()
            for l in f.loops:
                p = l.vert.co
                l[uv].uv = (UB[0] + 0.05 * (p.x - px0) / (px1 - px0), UB[1] + 0.02 * (p.y - py0) / (py1 - py0))
                l[uv2].uv = (0.0, 0.0)
    # 継ぎ目の環を溶接(uv は面の角ごとに持つので崩れない)── 閉じた体にする(光線の内外の判定が効くように)
    ring_v = [v for v in bm.verts if abs(v.co.z - pz0) < eps]
    bmesh.ops.remove_doubles(bm, verts=ring_v, dist=1e-5)
    bm.to_mesh(me); bm.free()
    for v in me.vertices: v.co.x -= cx
    post.location = (0, 0, 0); post.name = NAME_H; me.name = NAME_H
    return post


# ───────────────────────── 地覆 ─────────────────────────
def build_jifuku(zt, hl, hw, mat):
    """x −hl..hl / y −hw..hw / z −DEPTH..zt の直の横木。前後・下面・小口とも格子で張る(下端の頂点を個別に削れるように)。
    UV は在庫の貫と同じ取り方 ── アトラス右端の縦の板の帯を 90° 寝かせて、走り = v・高さ = u(木理が走りに流れる)。"""
    zb = -DEPTH
    Ku = (UR[1] - UR[0]) / (zt - zb)                 # du/dy(y を上げると u が上端の側へ)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    uv2 = bm.loops.layers.uv.new("scribe_duv")
    xs = [-hl + 2 * hl * i / NCOL for i in range(NCOL + 1)]
    ys = [-hw + 2 * hw * j / (NG - 1) for j in range(NG)]
    T = [[bm.verts.new((x, y, zt)) for y in ys] for x in xs]
    B = [[bm.verts.new((x, y, zb)) for y in ys] for x in xs]
    def Vx(x, flip=False):
        t = (x + hl) / (2 * hl)
        return VR[0] + (VR[1] - VR[0]) * ((1 - t) if flip else t)
    def Uz(z): return UR[1] - (zt - z) * Ku
    def put(f, fn, d):
        f.normal_update()
        for l in f.loops:
            l[uv].uv = fn(l.vert.co); l[uv2].uv = d
    for i in range(NCOL):
        # 前(y = −hw・Blender 法線 −Y)/ 後(y = +hw・法線 +Y)
        f = bm.faces.new((B[i][0], B[i + 1][0], T[i + 1][0], T[i][0]))
        put(f, lambda c: (Uz(c.z), Vx(c.x)), (Ku, 0.0))
        f = bm.faces.new((T[i][NG - 1], T[i + 1][NG - 1], B[i + 1][NG - 1], B[i][NG - 1]))
        put(f, lambda c: (Uz(c.z), Vx(c.x, True)), (Ku, 0.0))
        for j in range(NG - 1):
            # 上面(法線 +Z)
            f = bm.faces.new((T[i][j], T[i + 1][j], T[i + 1][j + 1], T[i][j + 1]))
            put(f, lambda c: (UR[1] - 0.012 * (c.y + hw) / (2 * hw), Vx(c.x)), (0.0, 0.0))
            # 下面(法線 −Z)── 地に伏せる面
            f = bm.faces.new((B[i][j + 1], B[i + 1][j + 1], B[i + 1][j], B[i][j]))
            put(f, lambda c: (UR[0] + 0.012 * (c.y + hw) / (2 * hw), Vx(c.x)), (0.0, 0.0))
    for j in range(NG - 1):
        # 小口 x = −hl(法線 −X)/ x = +hl(法線 +X)── 柱の面に突き付くので見えないが閉じておく
        f = bm.faces.new((B[0][j + 1], B[0][j], T[0][j], T[0][j + 1]))
        put(f, lambda c: (Uz(c.z), VR[0] + 0.03 * (c.y + hw) / (2 * hw)), (Ku, 0.0))
        f = bm.faces.new((B[NCOL][j], B[NCOL][j + 1], T[NCOL][j + 1], T[NCOL][j]))
        put(f, lambda c: (Uz(c.z), VR[1] - 0.03 * (c.y + hw) / (2 * hw)), (Ku, 0.0))
    me = bpy.data.meshes.new(NAME_J); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(NAME_J, me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o, Ku


# ───────────────────────── 光付け(EdoBuild の手本) ─────────────────────────
def scribe(o, bed, sa, sc, step=0.0025):
    """o の削る頂点(局所 y ≤ −DEPTH+0.001 = Blender z)を地表・石の天端へ上げる(= 光付け)。EdoBuild の手本。
    1. 削る頂点を**厚みの列**(局所 z が同じ = 前・芯・後)ごとに走りの順に並べる。
    2. 列ごとの床の線 B(x) = 厚みの窓 [z−sc, z+sc] の床の最大(sc = 列の間隔。窓は部材の足跡で切る)を走りに step 刻みで引く。
    3. 格子点の高さ h_i = B(x_i) から始め、隣の格子点との間の下端の線が B より下になる所があれば、その点に近い方の
       端を足りない分だけ上げる(線形の重み 1/(1−t)・1/t)── 下がる所は無いので繰り返せば収まる(= 食い込み 0)。
    ⛔ 足跡の外(面の外・小口の先)を標本しない ── 外の床の高い所で持ち上がり、面の下に隙が出る。
    上端の手前 TOP_STOP で止める。uv を uv2·Δy だけ引き直す。返り値 = (床が代より深く届かなかった頂点, 動かした頂点)。"""
    me = o.data; mw = o.matrix_world; loc = mw.translation
    xs_all = [v.co.x for v in me.vertices]; ys_all = [v.co.y for v in me.vertices]
    x0, x1, y0, y1 = min(xs_all), max(xs_all), min(ys_all), max(ys_all)
    ztop = max(v.co.z for v in me.vertices)
    rows = {}
    for v in me.vertices:
        if v.co.z <= -DEPTH + 0.001: rows.setdefault(round(v.co.y, 5), []).append(v)
    short = 0; moved = {}
    nx = max(1, int(math.ceil((x1 - x0) / step)))
    for yr, vs in rows.items():
        vs.sort(key=lambda v: v.co.x)
        ya, yb = max(yr - sc, y0), min(yr + sc, y1)
        nc = max(1, int(math.ceil((yb - ya) / step)))
        X = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
        Bx = []
        for x in X:
            m = None
            for c in range(nc + 1):
                hh = bed(loc.x + x, loc.y + ya + (yb - ya) * c / nc)
                if hh is not None and (m is None or hh > m): m = hh
            Bx.append(None if m is None else m - loc.z)
        # 標本の間に立つ石の壁(急な目地)で食い込まないよう、隣の標本との最大で膨らませる
        Bx = [None if Bx[i] is None else max(b for b in Bx[max(0, i - 1):i + 2] if b is not None) for i in range(len(Bx))]
        def Bat(x):
            i = min(nx, max(0, int(round((x - x0) / (x1 - x0) * nx)))); return Bx[i]
        h = [Bat(v.co.x) for v in vs]
        h = [(-DEPTH if hh is None else hh) for hh in h]
        # 上げの上限 = 隣の格子点までの窓の床の最大(ここまで上げれば必ず収まる ⇒ 上げ過ぎない)
        cap = []
        for k, v in enumerate(vs):
            xa = vs[k - 1].co.x if k > 0 else v.co.x; xb = vs[k + 1].co.x if k + 1 < len(vs) else v.co.x
            i0 = int(math.floor((xa - x0) / (x1 - x0) * nx)); i1 = int(math.ceil((xb - x0) / (x1 - x0) * nx))
            vals = [Bx[i] for i in range(max(0, i0), min(nx, i1) + 1) if Bx[i] is not None]
            cap.append(max(vals) if vals else h[k])
        for _ in range(200):
            changed = False
            for k in range(len(vs) - 1):
                xa, xb = vs[k].co.x, vs[k + 1].co.x
                i0 = int(math.ceil((xa - x0) / (x1 - x0) * nx)); i1 = int(math.floor((xb - x0) / (x1 - x0) * nx))
                worst, wt = 0.0, 0.5
                for i in range(i0, i1 + 1):
                    if Bx[i] is None: continue
                    t = (X[i] - xa) / max(xb - xa, 1e-9)
                    d = Bx[i] - (h[k] + (h[k + 1] - h[k]) * t)
                    if d > worst + 1e-7: worst, wt = d, t
                if worst > 1e-6:
                    # 近い方の端を上限まで上げ、足りない分は遠い方の端で
                    near, far, wn, wf = (k, k + 1, 1 - wt, wt) if wt < 0.5 else (k + 1, k, wt, 1 - wt)
                    up = min(worst / max(wn, 1e-6), cap[near] - h[near]); h[near] += max(up, 0.0)
                    rest = worst - max(up, 0.0) * wn
                    if rest > 1e-7: h[far] = min(h[far] + rest / max(wf, 1e-6), cap[far])
                    changed = True
            if not changed: break
        for v, hh in zip(vs, h):
            if hh < v.co.z - 1e-6: short += 1; continue      # 床が代より深い ⇒ 動かさない(⚠)
            hh = min(hh, ztop - TOP_STOP)
            moved[v.index] = hh - v.co.z; v.co.z = hh
    uvl = me.uv_layers["UVMap"].data; d2 = me.uv_layers["scribe_duv"].data
    for li, lp in enumerate(me.loops):
        dz = moved.get(lp.vertex_index)
        if dz: uvl[li].uv = uvl[li].uv + d2[li].uv * dz
    me.update()
    return short, len(moved)


# ───────────────────────── 検算用の床(野面の天端に似せる) ─────────────────────────
def stone_bed_fn():
    """走り x に沿って石(長さ 0.25〜0.55・頭が丸い)と目地(幅 0.03〜0.12・深さ 0.10〜0.35)を並べ、全体に勾配と横の傾き。"""
    rnd = random.Random(7)
    segs = []; x = -1.0
    while x < 6.0:
        L = rnd.uniform(0.25, 0.55); J = rnd.uniform(0.03, 0.12); D = rnd.uniform(0.10, 0.35)
        top = rnd.uniform(-0.03, 0.04)
        segs.append((x, x + L, top, J, D)); x += L + J
    def h(x, y):
        base = 0.06 * x + 0.10 * y
        for (a, b, top, J, D) in segs:
            if a <= x < b:
                t = (x - a) / (b - a)
                return base + top - 0.05 * (2 * t - 1) ** 4 - 0.03 * (y / 0.3) ** 2
            if b <= x < b + J:
                t = (x - b) / J
                return base + top - 0.05 - D * math.sin(math.pi * t) ** 0.5
        return base
    return h


def make_ground(h, x0, x1, y0, y1, res=0.005):
    nx, ny = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    verts = [(x0 + i * res, y0 + j * res, h(x0 + i * res, y0 + j * res)) for i in range(nx) for j in range(ny)]
    faces = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(nx - 1) for j in range(ny - 1)]
    me = bpy.data.meshes.new("ground"); me.from_pydata(verts, [], faces); me.update()
    g = bpy.data.objects.new("ground", me); bpy.context.scene.collection.objects.link(g)
    return g


def open_edges(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    n = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    iso = sum(1 for v in bm.verts if not v.link_edges)
    bm.free(); return n, iso


def outward_ok(o):
    """符号付き体積 > 0(外向き)"""
    me = o.data; vol = 0.0
    for p in me.polygons:
        vs = [me.vertices[i].co for i in p.vertices]
        for k in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[k].cross(vs[k + 1])) / 6.0
    return vol


def main():
    V.reset()
    src = load_src()
    mat = src.data.materials[0]
    post, foot, boards = split_parts(src)
    ita = V.join(boards, "ita")
    bx0, bx1, by0, by1, bz0, bz1 = ext(ita)
    cb = (bx0 + bx1) / 2
    for v in ita.data.vertices: v.co.x -= cb
    ita.location = (0, 0, 0)
    px0, px1, py0, py1, pz0, pz1 = ext(post)
    hw = (py1 - py0) / 2
    hl = (bx1 - bx0) / 2
    hashira = build_hashira(post)
    jif, K = build_jifuku(bz0, hl, hw, mat)
    bpy.data.objects.remove(foot, do_unlink=True)
    for o in (jif, hashira):
        e = ext(o)
        print("[jifuku] %s: Unity x %.4f..%.4f y %.4f..%.4f z %.4f..%.4f 頂点 %d 面 %d 材 %s 開いた辺/孤立 %s 体積 %.5f" % (
            o.name, -e[1], -e[0], e[4], e[5], -e[3], -e[2], len(o.data.vertices), len(o.data.polygons),
            sorted({m.name for m in o.data.materials}), open_edges(o), outward_ok(o)))
    print("[jifuku] 板の下端 %.4f = 地覆の上端 / 板の幅 %.4f / 柱身 %.4f×%.4f / Ku(地覆の du/dy) %.5f" % (
        bz0, bx1 - bx0, px1 - px0, py1 - py0, K))
    V.export_fbx([jif], os.path.join(OUT, NAME_J + ".fbx"))
    V.export_fbx([hashira], os.path.join(OUT, NAME_H + ".fbx"))
    print("[jifuku] 出した:", NAME_J, NAME_H)
    if DO_RENDER:
        check_and_render(ita, jif, hashira, px1 - px0, hl)


def check_and_render(ita, jif, hashira, bodyW, hl):
    """野面に似せた床に 3 間並べ、据え(板・地覆 = 足跡の床の最高 / 柱 = 両隣の高い方)と光付けを本番と同じ手で回して、
    ① 食い込み(下端 < 床)② 下の隙 ③ 代の不足 を数え、正面(背景マゼンタ)と寄りを刷る。"""
    V.hook_textures()
    h = stone_bed_fn()
    P = 2 * hl + bodyW
    nb = 3
    x_end = nb * P + 0.2
    g = make_ground(h, -0.3, x_end, -0.25, 0.25)
    bvh = BVHTree.FromPolygons([v.co.copy() for v in g.data.vertices], [tuple(pl.vertices) for pl in g.data.polygons])
    def bed(x, y):
        hit = bvh.ray_cast(mathutils.Vector((x, y, 50.0)), mathutils.Vector((0, 0, -1)))
        return hit[0].z if hit[0] else None
    def footmax(xa, xb, hy):
        m = -1e9; x = xa
        while x <= xb + 1e-6:
            for y in (-hy, 0.0, hy):
                b = bed(x, y)
                if b is not None: m = max(m, b)
            x += 0.005
        return m
    print("[jifuku] 床の標本", bed(0.5, 0.0), bed(1.0, 0.1), len(g.data.polygons))
    for o in (ita, jif, hashira): o.hide_render = True
    made = []; y0s = []; stats = []
    hy = (max(v.co.y for v in hashira.data.vertices) - min(v.co.y for v in hashira.data.vertices)) / 2
    for k in range(nb):
        c = bodyW / 2 + k * P + bodyW / 2 + hl          # 板の中心(柱芯 0 から)
        y0 = footmax(c - hl, c + hl, hy)
        y0s.append(y0)
        b = ita.copy(); b.data = ita.data; bpy.context.scene.collection.objects.link(b)
        b.location = (c, 0, y0); b.hide_render = False
        j = jif.copy(); j.data = jif.data.copy(); bpy.context.scene.collection.objects.link(j)
        j.location = (c, 0, y0); j.hide_render = False
        made += [b, j]
    for k in range(nb + 1):
        cx = bodyW / 2 + k * P
        adj = [y0s[i] for i in (k - 1, k) if 0 <= i < nb]
        y0 = max(adj + [footmax(cx - bodyW / 2, cx + bodyW / 2, hy)])
        p = hashira.copy(); p.data = hashira.data.copy(); bpy.context.scene.collection.objects.link(p)
        p.location = (cx, 0, y0); p.hide_render = False
        made.append(p)
    bpy.context.view_layer.update()
    short = 0; n_moved = 0
    for o in made:
        if o.data.name.startswith("Itabei_Jifuku"):
            s, n = scribe(o, bed, 2 * hl / NCOL, hy)
        elif o.data.name.startswith("Itabei_Hashira"):
            s, n = scribe(o, bed, bodyW / 2, hy)
        else: continue
        short += s; n_moved += n
    bpy.context.view_layer.update()
    # 検算: 下端の線(前・芯・後の 3 列)を 0.002 刻みで、床との差を測る
    worst_pen = 0.0; gaps = []; worst_at = None; widths = []
    for o in made:
        if not (o.data.name.startswith("Itabei_Jifuku") or o.data.name.startswith("Itabei_Hashira")): continue
        mw = o.matrix_world
        # 削った頂点は z が変わっているので「元の下端の格子」を位置で拾い直す: 下面の面の頂点
        me = o.data
        low = set()
        for poly in me.polygons:
            if poly.normal.z < -0.5: low.update(poly.vertices)
        pts = sorted({(round((mw @ me.vertices[i].co).x, 5), round((mw @ me.vertices[i].co).y, 5)): (mw @ me.vertices[i].co).z
                      for i in low}.items())
        rows = {}
        for (x, y), z in pts: rows.setdefault(y, []).append((x, z))
        for y, arr in rows.items():
            arr.sort()
            run = 0.0
            for (xa, za), (xb, zb) in zip(arr, arr[1:]):
                x = xa
                while x <= xb:
                    z = za + (zb - za) * (x - xa) / max(xb - xa, 1e-9)
                    b = bed(x, y)
                    if b is not None:
                        d = z - b
                        if d < worst_pen: worst_pen = d; worst_at = (o.data.name, round(x, 4), y, round(z, 4), round(b, 4))
                        gaps.append(d)
                        run = run + 0.002 if d > 0.01 else 0.0
                        widths.append((run, o.data.name[:14], round(x, 3), y))
                    x += 0.002
    gaps.sort()
    n = len(gaps)
    print("[jifuku] 標本", n, "光付け", n_moved, short, "最深の所", worst_at)
    le01 = sum(1 for d in gaps if d <= 0.01) / n
    q = lambda f: gaps[min(n - 1, int(f * n))]
    print("[jifuku] 隙 >0.01 の続く幅の最大(走り方向) %.3f m" % max(widths)[0], max(widths))
    print("[jifuku] 下の隙の分位: p50 %.4f p75 %.4f p90 %.4f p95 %.4f p99 %.4f" % (q(.5), q(.75), q(.9), q(.95), q(.99)))
    # 板の下端 − 地覆の上端(同じ変換なので 0 のはず)
    print("[jifuku] 検算: 光付けした頂点 %d / 代が足りない頂点 %d / 食い込みの最深 %.4f / 下の隙 中央値 %.4f・≤0.01 の割合 %.1f%%・最大 %.4f" % (
        n_moved, short, worst_pen, gaps[n // 2], le01 * 100, gaps[-1]))
    print("[jifuku] 間ごとの据え高(床の最高): %s / 床の最低からの深さ(代 %.2f に対し): %s" % (
        ["%.3f" % y for y in y0s], DEPTH,
        ["%.3f" % (y0s[k] - min(h(x / 100.0, 0) for x in range(int(100 * (bodyW + k * P)), int(100 * (bodyW + k * P + 2 * hl))))) for k in range(nb)]))
    # 正面・背景マゼンタ
    cam = V.studio((nb * P / 2, -8.0, 0.55), (nb * P / 2, 0.0, 0.55), ortho_scale=nb * P + 0.6, res=(1800, 900))
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 0.0, 1.0, 1)
    V.render(os.path.join(SHOT, "itabei_jifuku_1_front_magenta.png"))
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1)
    cam.data.ortho_scale = 1.6
    cam.location = (bodyW / 2 + P, -8.0, 0.15)
    V.render(os.path.join(SHOT, "itabei_jifuku_2_front_near.png"))
    cam.data.type = 'PERSP'
    cam.location = (bodyW / 2 + P * 1.4, -1.9, 0.9)
    d = mathutils.Vector((bodyW / 2 + P * 1.0, 0, 0.2)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(SHOT, "itabei_jifuku_3_persp.png"))
    cam.location = (bodyW / 2 + P * 1.5, 2.6, 1.3)
    d = mathutils.Vector((bodyW / 2 + P * 1.3, 0, 0.3)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(SHOT, "itabei_jifuku_4_back.png"))


main()
