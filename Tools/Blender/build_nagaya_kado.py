"""**90° の出隅に据える隅長屋**(L 字の長屋の角)を、在庫の `knagaya01c` を折って起こす。

    blender --background --python Tools/Blender/build_nagaya_kado.py -- --arms 6.0,6.0 --render
    blender --background --python Tools/Blender/build_nagaya_kado.py -- --arms 5.2,7.4         # 腕違い
    blender --background --python Tools/Blender/build_nagaya_kado.py -- --range                # 作れる腕の長さの表
    blender --background --python Tools/Blender/build_nagaya_kado.py -- --deg 90.9 --arms 10.05,9.19 --tsuma negZ --render
        # 内角 90.9°(+X の腕は固定・−Z の腕が回る)・−Z の腕の先を妻(knagaya01r の妻の端)で閉じる → Nagaya_Kado_90p9_A1005x919_TZ
        # 名前: 内角は 0.1° 単位(90 → `90`・90.9 → `90p9`)・腕は cm・妻は `_TZ` / `_TX` / `_TZX`(EdoAssets.Own.NagayaKado と同じ綴り)
        # 妻の腕の長さは**妻壁の外面**(namako2 の表)まで。土台の端は 0.030 内・破風と鬼は 0.322 外へ出る。
    blender --background --python Tools/Blender/build_nagaya_kado.py -- --straight 8.07 --render
        # 折らない真っ直ぐの一棟を**両端とも妻**で閉じる(−X 端 = knagaya01r の妻・+X 端 = knagaya01l の妻)→ Models/Nagaya/Nagaya_Tsuma2_L807
        # 長さ = 妻壁の外面どうし。ピボット = 長さの中央・外面(海鼠の浮き彫りの表)・土台の底。表 = Unity +Z(在庫 01c と同じ向き)。隅棟なし。
        # 観理院 表門の西脇で、孤立した区間に妻の無い c が置かれて両端の小口が開いた(施主指摘 2026-10-02)ための版。
    blender --background --python Tools/Blender/build_nagaya_kado.py -- --straight-range      # 作れる長さ(1.28m〜)

【なぜ要るか】観理院(類型 sannosha_kanri)の北東で、北辺と東辺の長屋が直角に出会う。
  `EdoBuild.NagayaRun` は各辺の鎖の端に妻(l/r)を置いて片方の妻をもう片方の躯体に突っ込むので、
  屋根が変に重なり、窓が途中で切れて見えた(施主指摘 2026-10-01)。
  `build_kado.py --part nagaya` の留め継ぎは 1 モジュールを鏡に映して接ぐので、
  ①腕の先の位相が素の棟の端と合わない(鏡に映すと片方の腕の先の pier が 0.97m/0.57m 入れ替わる)、
  ②腕の長さが 4.296 の倍で決まり端数を吸えない。⇒ 別の生成器にした。

【方針】**ゼロから作らない。**素の `knagaya01c` を周期のまま走りに延ばした一本の帯
  (= 窓 1 つ + 無地の壁(pier)の bay 2.6874m が並んだもの)を作り、**pier の真ん中で 90° に折る**。
  折る点 = 外隅の稜。両腕とも素と同じ向き(表が外)のまま残るので、
    ・外隅の稜は pier の芯 ⇒ 稜の両側に 0.77m ずつ無地の壁、**窓は切れない**
    ・内面(境内側)は素が盲壁(窓が無い)⇒ 内隅の位置は気にしなくてよい
    ・素は pier の芯に対してほぼ鏡対称(格子・海鼠は 0.000、瓦 ≤0.016m、垂木 ≤0.04m の食い違い)
      ⇒ 留め面の両側の断面はほぼ一致する。1.2cm 以内の食い違いは留め面の上だけで溶接する
  屋根は留め面で連続し、外に**隅棟**(素の `n_mune` を回して伸ばす)、内に**谷**が自然に出る。
  妻(破風・鬼)は付けない。

【腕の先の位相(据え側の要件 A)】腕の先は**素の `knagaya01c` の土台の端と同じ位相**で終わる。
  先の一切れは素のモジュールの端そのもの(`[d1−y, d1]` / `[d0, d0+y]`)を切り出して継ぐので、
  先の断面(壁の箱の小口・海鼠・瓦・垂木)は素の棟の端と頂点まで一致する。
  素の棟は端から窓までの無地が**右端 0.571m / 左端 0.961m**(表から見て)と非対称なので、
    ・+X の腕(見え面 +Z)の先は 素の **左端(d1・0.961m 側)** の断面 ⇒ 続く素の棟は**右端**を当てる
    ・−Z の腕(見え面 −X)の先は 素の **右端(d0・0.571m 側)** の断面 ⇒ 続く素の棟は**左端**を当てる
  在庫の棟を表(+Z)を外へ向けて並べれば、どちらの腕でも勝手にこの向きになる(回すと表が内を向く)。

【腕の長さ(据え側の要件 B)】外隅の稜から腕の先までの**外面の長さ** a[m] を腕ごとに引数で取る。
  build_nagaya_omote と同じく、窓・瓦・海鼠の形は伸ばさず **窓の数 n と無地の壁の詰め ε** で吸う:
      a/ES = W2 + wh + (n−2)·(bay − ε) + (T − ε_t)
  W2 = 外隅から 2 つ目の窓の芯 / wh = 窓の半幅 / T = 素の先の無地 / ε_t = 先の無地の詰め。
  ⭐ **外隅から 2 つ目の窓の先の pier までは素のまま**(詰めない)。留め面の断面は外隅から
    奥行+内の軒(2.05 ×ES = 3.73m)まで素の帯を使うので、ここを詰めると谷で両腕の瓦がずれる。
  ⇒ 腕ごとに窓は**2 つ以上**丸ごと見える。最小の腕はおよそ 4.79m(`--range` で表を出す)。

【出力の向き(Unity 局所)】ピボット = **外隅の稜**(両腕の外面 = 足元の帯の最も外の面の交線)・
  **土台の底**。外面は海鼠の浮き彫りの表(海鼠壁の地の面より 0.030m 外・土台の面より 0.033m 外)で、
  `NagayaRun` が「長屋の外面」として測る足元の帯の外端と同じ面。
    ・**+X の腕**: ピボットから +X へ a_posX。見え面 = **+Z**(軒が +Z へ 0.57m 出る)
    ・**−Z の腕**: ピボットから −Z へ a_negZ。見え面 = **−X**
    ・躯体は X ≥ 0・Z ≤ 0 の象限。position = 外面の交点 / yaw = **+X の腕の外向き方位**(= +Z が外)/ scale = 1
  名前の腕の順は石垣の隅(`IshigakiKado(deg,h,armNegZ,armPosX)`)と同じ (−Z の腕, +X の腕) の cm。

【落とし穴】
  ・素の .obj を読んで transform_apply すると X が反転する(build_nagaya_omote と同じ)。寸法は必ず読んだ後のメッシュで測る。
  ・素の窓は厳密には周期でない(窓どうしの芯々が 1.4807 / 1.4783 / 1.4757 とばらつく)。
    芯を bay で決め打ちせず、帯に並んだ実際の窓の塊から測る。
  ・5 棟つないだ帯は、つなぎ目の箱の小口(壁・海鼠壁・土台の ±X の面)が中に残る。消してからつなぐ。
    先の一切れは素の 1 棟から取るので、先の小口は素のまま残る(= 在庫の棟の端と同じ)。
  ・bisect は面を持たない頂点・辺を残す(bbox が嘘をつく)。毎回消す。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ES   = 1.818
SRC  = os.path.join(V.REPO, "Assets/edogoyomi/es_knagaya")
OUT  = V.out_dir(os.path.join(V.REPO, "Assets/Edo/Models/Kado"))
SHOT = os.path.join(V.REPO, "Screenshots")

# 詰めの範囲(obj 単位)。中の pier は build_nagaya_omote と同じ 0.345〜1.495(0.63〜2.72m)
P_MIN, P_MAX = 0.345, 1.495
T_MIN = 0.10                      # 腕の先の無地の下限(0.18m)。続く素の棟の無地と合わせて 0.75m 以上になる
WELD = 0.012                      # 留め面の上だけで溶接する距離(obj)。素の鏡対称のずれ ≤0.0086


# ---------------------------------------------------------------- 取り込み・切る
def read_module(stem="knagaya01c"):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(SRC, stem + ".obj"),
                          forward_axis='Z', up_axis='Y', use_split_groups=True)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    V.sel(meshes)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return {o.name.split('.')[0]: o for o in meshes}


def span(o, ax):
    vs = [v.co[ax] for v in o.data.vertices]
    return min(vs), max(vs)


def clean(bm):
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')


def bisect(o, co, no, keep_pos):
    """平面(co, no)で切り、keep_pos なら no 側を残す。切り口は塞がない。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=Vector(no),
                           clear_outer=not keep_pos, clear_inner=keep_pos)
    clean(bm)
    bm.to_mesh(me); bm.free(); me.update()
    return o


def dup(o, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name
    bpy.context.collection.objects.link(c)
    return c


def take(src, x0, x1, dx, name):
    """src の x∈[x0,x1] を切り出し、x へ dx だけ動かした複製を返す。"""
    c = dup(src, name)
    bisect(c, (x0, 0, 0), (1, 0, 0), True)
    bisect(c, (x1, 0, 0), (1, 0, 0), False)
    c.data.transform(Matrix.Translation((dx, 0, 0)))
    c.data.update()
    return c


def windows(koshi):
    """格子の頂点 x を隙間 0.30 で塊に割り、各窓の (左端, 右端) を返す(左→右)。"""
    xs = sorted(set(round(v.co.x, 4) for v in koshi.data.vertices))
    cl = [[xs[0]]]
    for a, b in zip(xs, xs[1:]):
        (cl.append([b]) if b - a > 0.30 else cl[-1].append(b))
    return [(c[0], c[-1]) for c in cl]


# ---------------------------------------------------------------- 素の実測
class Src:
    pass


def measure(g):
    s = Src()
    s.d0, s.d1 = span(g["n_dodai"], 0)
    s.W = s.d1 - s.d0
    s.bay = s.W / 3.0
    s.win = windows(g["koshi"])                       # 1 棟に 3 つ
    s.wh = sum(b - a for a, b in s.win) / len(s.win) / 2.0
    s.P = s.bay - 2 * s.wh                            # 窓と窓の間の無地(平均)
    s.p = (s.win[1][1] + s.win[2][0]) * 0.5           # 折る点 = 真ん中と右の窓の間の pier の芯
    s.T_A = s.d1 - s.win[2][1]                        # 素の d1 端の無地(+X の腕の先)
    s.T_B = s.win[0][0] - s.d0                        # 素の d0 端の無地(−Z の腕の先)
    # 外面 = 足元の帯の最も外(海鼠の浮き彫りの表)。NagayaRun の外面の測りと同じ面
    s.y_f = span(g["namako"], 1)[1]
    s.y_namako_box = span(g["n_namako"], 1)[1]
    s.y_namako_box_in = span(g["n_namako"], 1)[0]
    s.y_dodai_out, s.y_dodai_in = span(g["n_dodai"], 1)[1], span(g["n_dodai"], 1)[0]
    s.y_wall_in = span(g["n_wall"], 1)[0]
    s.y_koshi = span(g["koshi"], 1)[1]
    s.x_box = span(g["n_namako"], 0)                  # 海鼠壁の地の箱の走りの端(札の脇の面)
    s.x_relief = span(g["namako"], 0)                 # 海鼠の浮き彫りの走りの端(土台の端より 1.7mm 外へ出る)
    s.y_eave_out, s.y_eave_in = span(g["n_noki"], 1)[1], span(g["n_noki"], 1)[0]
    s.z_bot = span(g["n_dodai"], 2)[0]
    s.mune_z = span(g["n_mune"], 2)
    s.mune_y = span(g["n_mune"], 1)
    s.depth_all = s.y_f - s.y_eave_in                 # 外隅から内の軒先までの奥行(留めの断面が要る長さ)
    return s


def measure_tsuma(s, gl, gr):
    """妻部材 `knagaya01l`(妻が +x)/ `knagaya01r`(妻が −x)の妻の端。窓は c と同じ x に並ぶ(l)/ x を反転して並ぶ(r)。
    腕の長さは**妻壁の外面**(`namako2` の浮き彫りの表 = 足元の帯の走りの端)まで測る。破風・鬼はその外へ出る。"""
    s.e_l = span(gl["namako2"], 0)[1]
    s.T_l = s.e_l - max(b for a, b in windows(gl["koshi"]))
    s.l_foot = max(span(gl["n_dodai"], 0)[1], span(gl["n_namako"], 0)[1])     # 帯の最下段(0.30m)の端
    s.l_dodai = span(gl["n_dodai"], 0)[1]
    s.l_kera = max(span(gl[k], 0)[1] for k in gl if k.startswith("n_kera") or k.startswith("n_oni"))
    s.e_r = span(gr["namako2"], 0)[0]
    s.T_r = min(a for a, b in windows(gr["koshi"])) - s.e_r
    s.r_foot = min(span(gr["n_dodai"], 0)[0], span(gr["n_namako"], 0)[0])
    s.r_dodai = span(gr["n_dodai"], 0)[0]
    s.r_kera = min(span(gr[k], 0)[0] for k in gr if k.startswith("n_kera") or k.startswith("n_oni"))
    s.kera_out = (s.l_kera - s.e_l) * ES                # 破風が妻壁の外面より外へ出る量
    return s


def seal_gable(gl, gr, s):
    """在庫 l/r の妻の端の**素通しの隙**を塞ぐ(検査 r9 2026-10-02・観理院 隅長屋 +X の妻)。
    素の妻は ①海鼠の帯(h 0.31〜2.22)で長手の地の箱 `n_namako` が妻壁の外面の 0.036m 手前で終わり、
    妻の浮き彫り `namako2` は外面から 0.026m までの裏の無い殻 ⇒ 間に幅 0.010 の縦の隙が躯体を貫いて開く。
    ②その上の白壁 `n_wall` の妻の面は外面より 0.033 引っ込む ⇒ 外面に突き付けた隣の棟との間に隙が出る。
    ⇒ `n_namako` の端を浮き彫りの殻の中(外面から 0.013 obj)まで延ばし、`n_wall` の妻の端(水切りの帯ごと)を
      外面へ揃える。外面・長さ・破風・土台の端(札の値)は変えない。measure_tsuma の後に呼ぶ。"""
    for g, e, sg in ((gl, s.e_l, +1), (gr, s.e_r, -1)):
        for name, to in (("n_namako", e - sg * 0.013), ("n_wall", e)):
            me = g[name].data
            for v in me.vertices:
                if sg * (v.co.x - e) > -0.025:
                    v.co.x = to
            me.update()
        # ③(検査 r10)n_namako の端を殻の中で止めただけだと、端から外面までの 0.024m の帯に長手の面が無く、
        #   面に直角に見ると浮き彫りの殻の裏が見える(目地の交点ごとの小穴)。
        #   ⇒ 端の面を複製して殻の中に残し、元の端の面を外面まで押し出してその蓋だけ消す
        #     (= 長手の外・内・上・下の面だけが外面まで届き、浮き彫りの窪みは今までどおり見える)。
        me = g["n_namako"].data
        bm = bmesh.new(); bm.from_mesh(me)
        bm.normal_update()
        x_cap = e - sg * 0.013
        caps = [f for f in bm.faces if sg * f.normal.x > 0.99 and all(abs(v.co.x - x_cap) < 1e-5 for v in f.verts)]
        if len(caps) != 1:
            raise SystemExit("[nagaya_kado] ⛔ seal_gable: n_namako の端の面が %d 枚(1 枚の筈)" % len(caps))
        bmesh.ops.duplicate(bm, geom=[caps[0]])
        ext = bmesh.ops.extrude_face_region(bm, geom=[caps[0]])
        nv = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
        for v in nv:
            v.co.x = e
        nf = [f for f in ext["geom"] if isinstance(f, bmesh.types.BMFace)]
        bmesh.ops.delete(bm, geom=nf, context='FACES_ONLY')
        bmesh.ops.delete(bm, geom=[caps[0]], context='FACES_ONLY')
        bm.to_mesh(me); bm.free(); me.update()


def periodic_source(g, s, ncopy=2):
    """素を ±ncopy 棟つないだ帯。つなぎ目に残る箱の小口(±X を向く面)は消してからつなぐ。"""
    base = V.join(list(g.values()), "mod")
    parts = []
    for k in range(-ncopy, ncopy + 1):
        c = dup(base, "src%+d" % k)
        bm = bmesh.new(); bm.from_mesh(c.data)
        bm.normal_update()
        caps = [f for f in bm.faces
                if abs(f.normal.x) > 0.99
                and (all(abs(v.co.x - s.d0) < 2.5e-3 for v in f.verts)
                     or all(abs(v.co.x - s.d1) < 2.5e-3 for v in f.verts))]
        bmesh.ops.delete(bm, geom=caps, context='FACES')
        clean(bm)
        bm.to_mesh(c.data); bm.free()
        c.data.transform(Matrix.Translation((k * s.W, 0, 0)))
        c.data.update()
        parts.append(c)
    src = V.join(parts, "src")
    bm = bmesh.new(); bm.from_mesh(src.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
    bm.to_mesh(src.data); bm.free(); src.data.update()
    return base, src


# ---------------------------------------------------------------- 腕の割付を解く
def arm_consts(s, side, tsuma=False):
    """side = +1(+X の腕・素の +x へ延びる)/ −1(−Z の腕・素の −x へ延びる)。
    戻り値 (W2 = 外隅から 2 つ目の窓の近い端まで, T = 素の先の無地)。obj 単位。"""
    if side > 0:
        w2 = (s.win[0][0] + s.W - s.p)                # 次の棟の左の窓(= 外隅から 2 つ目)の左端
        # 1 つ目の窓 = s.win[2]
        return w2, (s.T_l if tsuma else s.T_A)
    w2 = s.p - (s.win[0][1])                          # 外隅から 2 つ目の窓(= s.win[0])の右端
    return w2, (s.T_r if tsuma else s.T_B)


def solve_arm(s, a_m, side, tsuma=False):
    """a[m] → (窓の数 n, 中の pier の詰め ε, 先の無地の詰め ε_t)。"""
    a = a_m / ES
    w2, T = arm_consts(s, side, tsuma)
    T_MAX = T + s.P - 0.02
    best = None
    for n in range(2, 80):
        base = w2 + 2 * s.wh + (n - 2) * s.bay + T     # ε=0 のときの長さ(2 つ目の窓の近い端 + 窓 + …)
        D = base - a                                   # 詰める量の合計
        cands = []
        if n == 2:
            et = D
            if T_MIN <= T - et <= T_MAX:
                cands.append((abs(et), 0.0, et))
        else:
            e = D / (n - 1)
            if P_MIN <= s.P - e <= P_MAX and T_MIN <= T - e <= T_MAX:
                cands.append((abs(e), e, e))
            else:
                Tp = min(max(T - e, T_MIN), T_MAX)
                et = T - Tp
                e = (D - et) / (n - 2)
                if P_MIN <= s.P - e <= P_MAX:
                    cands.append((max(abs(e), abs(et)), e, et))
        for sc, e, et in cands:
            if best is None or sc < best[0]:
                best = (sc, n, e, et)
    if best is None:
        return None
    return best[1], best[2], best[3]


# ---------------------------------------------------------------- 帯を組む
def build_strip(s, src, mod, aA, aB, plans, tsu=(), lmod=None, rmod=None):
    """素の座標で、外隅(p)から +x へ +X の腕・−x へ −Z の腕を並べた一本の帯を組む。
    戻り値の帯は x = 0 が外隅(p を原点へ寄せてある)。"""
    pieces = []
    info = {}
    # 帯に並ぶ実際の窓(5 棟ぶん)
    wins = sorted((a + k * s.W, b + k * s.W) for k in range(-2, 3) for a, b in s.win)

    def win_at(x):
        return min(wins, key=lambda w: abs((w[0] + w[1]) * 0.5 - x))

    ends = {}
    for side, a_m in ((+1, aA), (-1, aB)):
        n, e, et = plans[side]
        a = a_m / ES
        w2, T = arm_consts(s, side, side in tsu)
        Tp = T - et
        y = min(Tp * 0.5, T - 0.01)                    # 先の一切れ(素の端)の長さ
        Pp = s.P - e
        # 2 つ目の窓(素のまま)の遠い端
        if side > 0:
            w2win = win_at(s.p + w2 + s.wh)
            far2 = w2win[1] - s.p
        else:
            w2win = win_at(s.p - w2 - s.wh)
            far2 = s.p - w2win[0]
        # 窓 j≥3 の芯の u(外隅からの距離)
        cen = [(far2 - s.wh) + (j - 2) * (s.bay - e) for j in range(3, n + 1)]
        u_last_far = (cen[-1] + s.wh) if cen else far2
        far_last = a - u_last_far - y                  # 最後の窓の先の無地のうち、窓の切片が持つ分(端数を吸う)
        info[side] = dict(n=n, eps=e, eps_t=et, pier=Pp, tip=Tp, y=y, far_last=far_last,
                          far2=far2, cen=cen)
        if far_last < 0.01 or far_last > s.P - 0.005:
            raise SystemExit("[nagaya_kado] ⛔ 先の無地の割付が崩れた side=%d far=%.4f" % (side, far_last))
        # 外隅の切片の端(素の x)
        ends[side] = (far2 + (Pp * 0.5 if n >= 3 else far_last))
        # 窓 j≥3 の切片
        for j, uc in enumerate(cen, start=3):
            ww = win_at(s.p)                           # 切り出す元の窓(帯の真ん中あたりのどれでもよい)
            wc = (ww[0] + ww[1]) * 0.5
            near = Pp * 0.5
            farm = Pp * 0.5 if j < n else far_last
            if side > 0:
                x0, x1 = ww[0] - near, ww[1] + farm
                dx = (s.p + uc) - wc
            else:
                x0, x1 = ww[0] - farm, ww[1] + near
                dx = (s.p - uc) - wc
            pieces.append(take(src, x0, x1, dx, "w%+d_%d" % (side, j)))
        # 先の一切れ: 素の 1 棟の端そのもの(小口ごと)。妻で閉じる腕は妻部材の妻の端(破風・鬼・妻壁ごと)
        if side in tsu and side > 0:
            pieces.append(take(lmod, s.e_l - y, s.e_l + 2.0, (s.p + a) - s.e_l, "tsumaA"))
        elif side in tsu:
            pieces.append(take(rmod, s.e_r - 2.0, s.e_r + y, (s.p - a) - s.e_r, "tsumaB"))
        elif side > 0:
            pieces.append(take(mod, s.d1 - y, s.d1 + 1.0, (s.p + a) - s.d1, "tipA"))
        else:
            pieces.append(take(mod, s.d0 - 1.0, s.d0 + y, (s.p - a) - s.d0, "tipB"))
    # 外隅の切片(両腕の 2 つ目の窓まで素のまま)
    pieces.append(take(src, s.p - ends[-1], s.p + ends[+1], 0.0, "corner"))
    o = V.join(pieces, "strip")
    o.data.transform(Matrix.Translation((-s.p, -s.y_f, -s.z_bot)))   # 外隅の稜・土台の底を原点へ
    o.data.update()
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return o, info


# ---------------------------------------------------------------- 折る(留め)
def fold_consts(deg):
    """内角 deg の出隅。−x の腕を原点まわりに φ = 180 − deg 回す。留め面の法線 nA(+x の腕が残す側)・nB(回す前の −x の腕)。"""
    phi = math.radians(180.0 - deg)
    c, sn = math.cos(phi * 0.5), math.sin(phi * 0.5)
    if abs(deg - 90.0) < 1e-9:
        R = Matrix(((0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))   # 整数だけ(6e-17 の汚れを入れない)
    else:
        R = Matrix.Rotation(phi, 4, 'Z')
    return phi, (c, sn, 0.0), (-c, sn, 0.0), R


def fold(strip, deg=90.0):
    """帯を外隅(原点)で折る。+x の腕は素のまま、−x の腕は原点まわりに φ = 180 − deg 回す(90° なら −y へ)。
    留め面は折れ角の二等分(nA·p = 0。+x の腕は nA·p ≥ 0 を残す)。"""
    phi, nA, nB, R = fold_consts(deg)
    A = dup(strip, "armA")
    bisect(A, (0, 0, 0), nA, True)
    B = dup(strip, "armB")
    bisect(B, (0, 0, 0), nB, True)
    B.data.transform(R); B.data.update()
    bpy.data.objects.remove(strip, do_unlink=True)
    o = V.join([A, B], "kado")
    # 留め面の上の頂点だけ溶接(素の鏡対称のずれ ≤1.6cm を閉じる)
    bm = bmesh.new(); bm.from_mesh(o.data)
    on = [v for v in bm.verts if abs(v.co.x * nA[0] + v.co.y * nA[1]) < 1e-4]
    bmesh.ops.remove_doubles(bm, verts=on, dist=WELD)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    clean(bm)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return o, len(on)


def hip_ridge(o, mune_src, s, deg=90.0):
    """外の隅棟。留め面(x + y = 0)の上で、大棟の頂から外の軒の隅へ。素の n_mune を回して伸ばす。
    ⚠ 起点(大棟の天端)と終点(軒の隅)を結んだ線へ天端を合わせると、軒の側で棟が瓦に埋まる。
      ⇒ 終点を棟の丈ぶん上げ、瓦の面と平行に走らせる。"""
    _, nA, _, _ = fold_consts(deg)
    ox, oy = -nA[1], nA[0]                             # 留め面の上で外へ向かう向き(90° なら (−1,+1)/√2)
    top, out, best = None, None, -1e9
    for v in o.data.vertices:
        if abs(v.co.x * nA[0] + v.co.y * nA[1]) > 0.03:
            continue
        if top is None or v.co.z > top.z:
            top = v.co.copy()
        pr = v.co.x * ox + v.co.y * oy                 # 外へ向かう量
        if pr > best:
            best, out = pr, v.co.copy()
    mh = s.mune_z[1] - s.mune_z[0]
    end = out + Vector((0, 0, mh * 0.6))
    seg = end - top
    c = dup(mune_src, "hip")
    me = c.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    x0, L0 = min(xs), max(xs) - min(xs)
    yc, zt = (min(ys) + max(ys)) * 0.5, max(zs)
    k = seg.length / L0
    e1 = seg.normalized()
    e2 = Vector((0, 0, 1)).cross(e1).normalized()
    e3 = e1.cross(e2)
    if e3.z < 0:
        e2 = -e2; e3 = e1.cross(e2)
    for v in me.vertices:
        lx, ly, lz = (v.co.x - x0) * k, v.co.y - yc, v.co.z - zt
        v.co = top + e1 * lx + e2 * ly + e3 * lz
    # 基底の向きで巻きが裏返っていたら直す(行列式で判定)
    det = Matrix((e1, e2, e3)).determinant()
    if det < 0:
        for p in me.polygons:
            p.flip()
    me.update()
    print("[nagaya_kado] 隅棟 実長 %.3fm (雛形 %.3f を %.2f 倍)  起点 z=%.3f → 終点 z=%.3f(m)"
          % (seg.length * ES, L0 * ES, k, top.z * ES, end.z * ES))
    return c


# ---------------------------------------------------------------- 組む
def deg_token(deg):
    """名前の折れ角。0.1° 単位で 90 → `90`・90.9 → `90p9`(EdoAssets.Own.NagayaKado と同じ綴り)。"""
    dd = int(math.floor(deg * 10.0 + 0.5))
    return "%d" % (dd // 10) if dd % 10 == 0 else "%dp%d" % (dd // 10, dd % 10)


def part_name(deg, aB, aA, tsu):
    t = ("Z" if -1 in tsu else "") + ("X" if +1 in tsu else "")
    return "Nagaya_Kado_%s_A%dx%d%s" % (deg_token(deg), int(math.floor(aB * 100 + 0.5)),
                                        int(math.floor(aA * 100 + 0.5)), "_T" + t if t else "")


def build(aB, aA, deg=90.0, tsu=(), render=False):
    """aB = −Z の腕 / aA = +X の腕[m] / deg = 出隅の内角 / tsu = 妻で閉じる腕(−1 = −Z・+1 = +X)。"""
    V.reset()
    g = read_module()
    gl = read_module("knagaya01l")
    gr = read_module("knagaya01r")
    V.dedup_materials()
    s = measure(g)
    measure_tsuma(s, gl, gr)
    seal_gable(gl, gr, s)
    mune_src = dup(g["n_mune"], "mune_tpl")
    print("[nagaya_kado] 素: 棟 %.4f bay %.5f (%.4fm) 窓 %.4fm pier %.4fm / 外隅 = pier の芯 x=%.4f"
          % (s.W, s.bay, s.bay * ES, 2 * s.wh * ES, s.P * ES, s.p))
    print("[nagaya_kado] 素の端の無地: d1 側 %.4fm(+X の腕の先)/ d0 側 %.4fm(−Z の腕の先)/ 妻の端 %.4fm"
          % (s.T_A * ES, s.T_B * ES, s.T_l * ES))
    print("[nagaya_kado] 妻: 破風・鬼が妻壁の外面より %.4fm 外へ / 土台の端は %.4fm 内"
          % (s.kera_out, (s.e_l - s.l_dodai) * ES))
    print("[nagaya_kado] 奥行: 外面→内壁 %.4fm / 外の軒 %.4fm / 内の軒 %.4fm(外面から)"
          % ((s.y_f - s.y_wall_in) * ES, (s.y_eave_out - s.y_f) * ES, s.depth_all * ES))
    phi, nA, nB, R = fold_consts(deg)
    # 留めの断面は外隅から内の軒先まで素の帯の中(2 つ目の窓の先まで)に収まっていること
    need = s.depth_all * math.tan(phi * 0.5)
    have = min(arm_consts(s, +1)[0], arm_consts(s, -1)[0]) + 2 * s.wh
    if need > have:
        raise SystemExit("[nagaya_kado] ⛔ 内角 %.1f° では留めの断面(%.2fm)が素の帯(%.2fm)を越える" % (deg, need * ES, have * ES))
    plans = {}
    for side, a_m in ((+1, aA), (-1, aB)):
        pl = solve_arm(s, a_m, side, side in tsu)
        if pl is None:
            raise SystemExit("[nagaya_kado] ⛔ 腕 %.3fm は作れない(--range で範囲を見る)" % a_m)
        plans[side] = pl
    mod, src = periodic_source(g, s)
    lmod = V.join(list(gl.values()), "lmod")
    rmod = V.join(list(gr.values()), "rmod")
    strip, info = build_strip(s, src, mod, aA, aB, plans, tsu, lmod, rmod)
    for side, nm in ((+1, "+X"), (-1, "−Z")):
        it = info[side]
        print("[nagaya_kado] %s の腕 %.3fm%s: 窓 %d / 中の無地 %.3fm(ε %+.4fm)/ 先の無地 %.3fm(素 %.3f)"
              % (nm, aA if side > 0 else aB, "(妻)" if side in tsu else "", it["n"], it["pier"] * ES, it["eps"] * ES,
                 it["tip"] * ES, arm_consts(s, side, side in tsu)[1] * ES))
    # 並べ焼き用の在庫の棟(妻の無い腕の先へ)。帯と同じ座標で置いて、同じ折り・向きを掛ける
    nbs = []
    if render:
        for side, a_m in ((+1, aA), (-1, aB)):
            if side in tsu:
                continue
            m = dup(mod, "nb%+d" % side)
            dx = (s.p + a_m / ES - s.d0) if side > 0 else (s.p - a_m / ES - s.d1)
            m.data.transform(Matrix.Translation((dx - s.p, -s.y_f, -s.z_bot)))
            if side < 0:
                m.data.transform(R)
            m.data.update()
            nbs.append(m)
    for ob in (src, mod, lmod, rmod):
        bpy.data.objects.remove(ob, do_unlink=True)
    o, nweld = fold(strip, deg)
    # 隅棟の雛形も原点へ寄せた座標系に(素の座標 → 帯の座標)
    mune_src.data.transform(Matrix.Translation((-s.p, -s.y_f, -s.z_bot))); mune_src.data.update()
    hip = hip_ridge(o, mune_src, s, deg)
    bpy.data.objects.remove(mune_src, do_unlink=True)
    o = V.join([o, hip], "kado")
    # --- 向き: +X の腕の表を Blender −Y(= Unity +Z)へ。**回転**で(鏡映しない)。整数だけの行列
    F = Matrix.Scale(ES, 4) @ Matrix(((-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    for ob in [o] + nbs:
        ob.data.transform(F); ob.data.update()
    nm = part_name(deg, aB, aA, tsu)
    o.name = nm; o.data.name = nm
    me = o.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    # Unity 局所 = (−x, z, −y)
    print("[nagaya_kado] 出来上がり(Unity 局所 m): X[%.3f, %.3f] Y[%.3f, %.3f] Z[%.3f, %.3f]  面 %d  留めで溶接 %d 点"
          % (-max(xs), -min(xs), min(zs), max(zs), -max(ys), -min(ys), len(me.polygons), nweld))
    dB = (-math.cos(phi), -math.sin(phi))
    print("[nagaya_kado] −Z の腕の向き(Unity XZ)= (%.5f, %.5f)・+X の腕となす角 %.2f°"
          % (dB[0], dB[1], math.degrees(math.acos(dB[0]))))
    path = os.path.join(OUT, nm + ".fbx")
    spec = make_spec(s, aA, aB, deg, tsu, o, path)
    V.export_fbx([o], path, kind="building", spec=spec)
    print("[nagaya_kado] wrote %s" % path)
    if render:
        for ob in nbs:
            ob.hide_render = True
        shots(o, nm)
        for ob in nbs:
            ob.hide_render = False
        narabe(o, nm, aA, aB, deg, tsu)
    return o, path, s, info


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def make_spec(s, aA, aB, deg, tsu, o, path):
    """札(取り合いのデータ)。値は作図の変数(素の実測の寸法 × ES・腕の長さ・折れ角)から。Unity 局所・倍率 1。
    kind は building(門・塀の駒の型に L 字は無い)。

    帯の断面は、腕ごとに「外面の線(留め面から腕の先まで)・内面の線・腕の先の端」の角の点で表し、
    −Z の腕は折れ角ぶん回す。Unity 局所の (X, Z) は帯の座標 (u, y') そのもの(+X の腕)/ その回転(−Z の腕)。
    ⚠ 帯の最下段(+0.30m)は海鼠の浮き彫りの下端(+0.3016)より下 ⇒ 外面は地の箱まで引っ込み、腕の先は土台・地の箱の端。"""
    phi, nA, nB, R = fold_consts(deg)
    t2 = math.tan(phi * 0.5)
    cphi, sphi = math.cos(phi), math.sin(phi)
    rot = lambda u, y: (u * cphi - y * sphi, u * sphi + y * cphi)
    dO = (s.y_f - s.y_dodai_out) * ES
    dI = (s.y_f - s.y_dodai_in) * ES
    kf = (s.y_koshi - s.y_f) * ES
    jb = (s.y_f - s.y_namako_box) * ES
    Dn = (s.y_f - span_box_in(s)) * ES                 # 帯の内面(海鼠壁の地の箱の内)
    z_relief = 0.3016

    def tip_ext(side, low, foot=False):
        """腕の先の端が腕の長さの位置からどれだけ外へ出るか[m](負 = 内)。"""
        if side in tsu:
            if foot:
                return ((s.l_dodai - s.e_l) if side > 0 else (s.e_r - s.r_dodai)) * ES
            return ((s.l_foot - s.e_l) if side > 0 else (s.e_r - s.r_foot)) * ES if low else 0.0
        if foot:
            return 0.0
        if side > 0:
            return (max(s.d1, s.x_box[1]) - s.d1) * ES if low else (max(s.x_relief[1], s.x_box[1]) - s.d1) * ES
        return (s.d0 - min(s.d0, s.x_box[0])) * ES if low else (s.d0 - min(s.x_relief[0], s.x_box[0])) * ES

    def outline(o_face, d_in, low, foot=False):
        pts = []
        for side, a in ((+1, aA), (-1, aB)):
            t = a + tip_ext(side, low, foot)
            for y in (o_face, -d_in):
                mu = -y * t2                           # 留め面の上の u
                if side > 0:
                    pts += [(mu, y), (t, y)]
                else:
                    pts += [rot(-mu, y), rot(-t, y)]
        return pts

    secs = []
    h = 0.30
    while h <= 1.80 + 1e-6:
        low = h < z_relief
        secs.append(outline(-jb if low else 0.0, Dn, low))
        h += 0.25
    front = max(kf, max(max(p[1] for p in sc) for sc in secs))
    back = min(min(p[1] for p in sc) for sc in secs)
    jl = max(min(p[0] for p in sc) for sc in secs)
    jr = min(max(p[0] for p in sc) for sc in secs)
    foot = _hull([(round(x, 6), round(z, 6)) for x, z in outline(-dO, dI, True, foot=True)])
    me = o.data
    xs = [-v.co.x for v in me.vertices]; zs = [-v.co.y for v in me.vertices]; hs = [v.co.z for v in me.vertices]
    rel = os.path.relpath(os.path.join(V.REPO, "Assets/Edo/Models/Kado", os.path.basename(path)), V.REPO)
    tz = ("negZ" if -1 in tsu else "") + ("," if len(tsu) == 2 else "") + ("posX" if +1 in tsu else "")
    return dict(prefab=rel.replace(os.sep, "/"),
                source="blender:build_nagaya_kado.py(--deg %g --arms %g,%g%s)" % (deg, aB, aA, " --tsuma " + tz if tz else ""),
                unitScale=1.0, yBottom=0.0, foot=[dict(x=x, y=z) for x, z in foot],
                front=front, back=back,
                jambL=dict(x=jl, z0=back, z1=0.0, y0=0.30, y1=1.80),
                jambR=dict(x=jr, z0=-Dn, z1=0.0, y0=0.30, y1=1.80),
                eave=dict(x0=min(xs), x1=max(xs), z0=min(zs), z1=max(zs), y0=0.0, y1=max(hs)),
                faceOut=0.0, faceIn=-(s.y_f - s.y_wall_in) * ES, height=max(hs))


def span_box_in(s):
    return s.y_namako_box_in


# ---------------------------------------------------------------- レンダ
def hook(magenta=False):
    for m in bpy.data.materials:
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.8
        if not any(n.type == 'TEX_IMAGE' for n in nt.nodes):
            img = nt.nodes.new('ShaderNodeTexImage')
            img.image = bpy.data.images.load(os.path.join(SRC, "knagaya.jpg"), check_existing=True)
            nt.links.new(img.outputs['Color'], b.inputs['Base Color'])


def bg(col):
    w = bpy.context.scene.world
    w.node_tree.nodes["Background"].inputs[0].default_value = col


def shots(o, nm):
    hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    # Blender 座標: +X の腕は −x へ、−Z の腕は +y へ。躯体は x≤0・y≥0
    L = max(-mn.x, mx.y)
    # ① 外から隅(外の対角から・少し上)
    V.studio((L * 1.6, -L * 1.6, 4.5), (-L * 0.3, L * 0.3, 2.6), res=(1800, 1100))
    V.render(os.path.join(SHOT, "%s_soto.png" % nm))
    # ② 外から隅の寄り(窓と稜・海鼠・軒の留め・隅棟)
    V.studio((7.5, -7.5, 3.0), (-0.8, 0.8, 3.0), res=(1600, 1100))
    V.render(os.path.join(SHOT, "%s_soto_yori.png" % nm))
    # ③ 内(境内側)から、谷を見下ろす
    V.studio((-L * 2.2, L * 2.2, 11.0), (-L * 0.3, L * 0.3, 2.5), res=(1800, 1100))
    V.render(os.path.join(SHOT, "%s_uchi.png" % nm))
    # ④ 上から(平面・正射影)
    c = (mn + mx) * 0.5
    V.studio((c.x, c.y, mx.z + 20), (c.x, c.y + 1e-3, 0), ortho_scale=max(mx.x - mn.x, mx.y - mn.y) * 1.1,
             res=(1400, 1400))
    V.render(os.path.join(SHOT, "%s_ue.png" % nm))
    # ⑤ 穴探し: 背景をマゼンタにして内から低く/外から高く(腕の先の小口・留め・谷)
    V.studio((-L * 1.9, L * 1.9, 1.7), (-L * 0.3, L * 0.3, 3.4), res=(1600, 1000))
    bg((1.0, 0.0, 1.0, 1.0))
    V.render(os.path.join(SHOT, "%s_uchi_magenta.png" % nm))
    V.studio((L * 1.3, -L * 0.4, 9.0), (-L * 0.3, L * 0.3, 3.8), res=(1600, 1000))
    bg((1.0, 0.0, 1.0, 1.0))
    V.render(os.path.join(SHOT, "%s_soto_magenta.png" % nm))


def narabe(o, nm, aA, aB, deg, tsu):
    """妻の無い腕の先に**在庫の knagaya01c を 1 棟ずつ**突き付けて並べ焼く(据え側の要件 A の検め)。
    在庫の棟は帯と同じ座標で腕の先の続きに置き、同じ折り・向きを掛けてある(build の nbs)。"""
    hook()
    L = max(aA, aB) + 8.065
    V.studio((L * 0.9, -L * 0.9, 6.0), (-L * 0.32, L * 0.32, 2.4), res=(1900, 1100))
    V.render(os.path.join(SHOT, "%s_narabe.png" % nm))
    phi = math.radians(180.0 - deg)
    # Blender の最終座標: +X の腕の先 = (−aA, 0)・−Z の腕の先 = aB·(cosφ, sinφ)
    tipB = (aB * math.cos(phi), aB * math.sin(phi))
    outB = (math.sin(phi), -math.cos(phi))            # −Z の腕の外向き(Blender)
    for tag, tip, out in (("A", (-aA, 0.0), (0.0, -1.0)), ("B", tipB, outB)):
        cam = (tip[0] + out[0] * 7.0, tip[1] + out[1] * 7.0, 2.6)
        V.studio(cam, (tip[0], tip[1], 2.6), ortho_scale=6.5, res=(1500, 1100))
        V.render(os.path.join(SHOT, "%s_narabe_%s%s.png" % (nm, tag, "_tsuma" if (+1 if tag == "A" else -1) in tsu else "")))
    # 妻の腕の先を斜めから(破風・鬼・妻壁)
    for tag, tip, out, along in (("A", (-aA, 0.0), (0.0, -1.0), (-1.0, 0.0)), ("B", tipB, outB, (math.cos(phi), math.sin(phi)))):
        if (+1 if tag == "A" else -1) not in tsu:
            continue
        cam = (tip[0] + out[0] * 6.0 + along[0] * 6.0, tip[1] + out[1] * 6.0 + along[1] * 6.0, 4.0)
        V.studio(cam, (tip[0] - out[0] * 1.5, tip[1] - out[1] * 1.5, 3.0), res=(1500, 1100))
        V.render(os.path.join(SHOT, "%s_tsuma_%s.png" % (nm, tag)))
        cam = (tip[0] - out[0] * 9.0 + along[0] * 6.0, tip[1] - out[1] * 9.0 + along[1] * 6.0, 6.0)
        V.studio(cam, (tip[0] - out[0] * 1.5, tip[1] - out[1] * 1.5, 3.0), res=(1500, 1100))
        V.render(os.path.join(SHOT, "%s_tsuma_%s_ura.png" % (nm, tag)))
        # 妻と長手の壁の継ぎ目を、外の面・内の面に直交して正射影で(背景マゼンタ ⇒ 縦の隙があれば桃色の線が出る)
        for side_tag, sgn in (("soto", 1.0), ("uchi", -1.0)):
            c0 = (tip[0] - out[0] * 1.5, tip[1] - out[1] * 1.5)
            cam = (c0[0] + sgn * out[0] * 12.0, c0[1] + sgn * out[1] * 12.0, 2.2)
            V.studio(cam, (c0[0], c0[1], 2.2), ortho_scale=3.0, res=(1200, 1400))
            bg((1.0, 0.0, 1.0, 1.0))
            V.render(os.path.join(SHOT, "%s_tsuma_%s_seam_%s_magenta.png" % (nm, tag, side_tag)))
        # 妻を正面(走りの向き)から
        cam = (tip[0] + along[0] * 12.0 - out[0] * 1.5, tip[1] + along[1] * 12.0 - out[1] * 1.5, 2.6)
        V.studio(cam, (tip[0] - out[0] * 1.5, tip[1] - out[1] * 1.5, 2.6), ortho_scale=7.0, res=(1200, 1100))
        bg((1.0, 0.0, 1.0, 1.0))
        V.render(os.path.join(SHOT, "%s_tsuma_%s_shomen_magenta.png" % (nm, tag)))


# ---------------------------------------------------------------- 真っ直ぐ・両端妻(--straight)
OUT_N = V.out_dir(os.path.join(V.REPO, "Assets/Edo/Models/Nagaya"))


def straight_consts(s, gl, gr):
    """両端妻の一棟の定数(obj 単位)。窓の切片は帯の真ん中の窓 s.win[1] から取る。
    妻の一切れ y は破風・鬼・妻壁(l/r にだけある部材)の内端より 0.01 内から切る(破風を切らない)。"""
    ww = s.win[1]
    k = dict(ww=ww, wW=ww[1] - ww[0],
             availL=ww[0] - s.win[0][1] - 0.02, availR=s.win[2][0] - ww[1] - 0.02)
    gable = lambda g: [g[n] for n in g if n.startswith("n_kera") or n.startswith("n_oni") or n == "namako2"]
    # 妻の側だけ壁(n_wall)が内へ引かれている ⇒ その端より内で切る(素の c の壁が妻壁の中へ突き出さないように)
    k["ymin_l"] = max(s.e_l - min(span(o, 0)[0] for o in gable(gl)), s.e_l - span(gl["n_wall"], 0)[1]) + 0.01
    k["ymin_r"] = max(max(span(o, 0)[1] for o in gable(gr)) - s.e_r, span(gr["n_wall"], 0)[0] - s.e_r) + 0.01
    for side, key, T in ((+1, "l", s.T_l), (-1, "r", s.T_r)):
        ymin = k["ymin_" + key]
        avail = k["availR"] if side > 0 else k["availL"]
        k["tip_" + key] = (ymin + 0.01, (T - 0.01) + avail)          # 先の無地の取れる幅
    return k


def solve_straight(s, k, L_m):
    """L[m](妻壁の外面どうし)→ (窓の数 n, 中の pier の詰め ε, 左の先の無地, 右の先の無地)。obj 単位。
    詰め ε は中の pier と両端の無地に一様に配る(端が範囲を外れたら端を止めて残りを pier へ)。"""
    a = L_m / ES
    best = None
    for n in range(1, 60):
        base = s.T_r + s.T_l + n * k["wW"] + (n - 1) * s.P
        D = base - a
        e = D / (n + 1)
        lo_r, hi_r = k["tip_r"]; lo_l, hi_l = k["tip_l"]
        tr = min(max(s.T_r - e, lo_r), hi_r)
        tl = min(max(s.T_l - e, lo_l), hi_l)
        if n == 1:
            rest = a - k["wW"] - tr - tl
            if abs(rest) > 1e-6:                        # 端だけで吸う: 両端に半分ずつ
                tr2, tl2 = tr + rest / 2, tl + rest / 2
                if not (lo_r <= tr2 <= hi_r and lo_l <= tl2 <= hi_l):
                    continue
                tr, tl = tr2, tl2
            ep = 0.0
        else:
            ep = (base - a - (s.T_r - tr) - (s.T_l - tl)) / (n - 1)
            if not (P_MIN <= s.P - ep <= P_MAX):
                continue
        sc = max(abs(ep), abs(s.T_r - tr), abs(s.T_l - tl))
        if best is None or sc < best[0]:
            best = (sc, n, ep, tr, tl)
    return None if best is None else best[1:]


def build_straight(L_m, render=False):
    """折らない真っ直ぐの帯を、−x 端に knagaya01r の妻・+x 端に knagaya01l の妻を継いで閉じる。
    ピボット = 長さの中央・外面(海鼠の浮き彫りの表)の線・土台の底。表 = Unity +Z(在庫 knagaya01c と同じ向き)。"""
    V.reset()
    g = read_module()
    gl = read_module("knagaya01l")
    gr = read_module("knagaya01r")
    V.dedup_materials()
    s = measure(g)
    measure_tsuma(s, gl, gr)
    k = straight_consts(s, gl, gr)
    seal_gable(gl, gr, s)
    print("[nagaya_tsuma2] 妻の一切れの下限: l %.4fm / r %.4fm(破風・鬼・妻壁の内端から)/ 先の無地の範囲 l %.3f〜%.3fm r %.3f〜%.3fm"
          % (k["ymin_l"] * ES, k["ymin_r"] * ES, k["tip_l"][0] * ES, k["tip_l"][1] * ES, k["tip_r"][0] * ES, k["tip_r"][1] * ES))
    print("[nagaya_tsuma2] 素の妻の端の無地: l %.4fm / r %.4fm  窓 %.4fm  pier %.4fm"
          % (s.T_l * ES, s.T_r * ES, k["wW"] * ES, s.P * ES))
    pl = solve_straight(s, k, L_m)
    if pl is None:
        raise SystemExit("[nagaya_tsuma2] ⛔ 長さ %.3fm は作れない(--straight-range で範囲を見る)" % L_m)
    n, ep, tr, tl = pl
    a = L_m / ES
    Pp = s.P - ep
    print("[nagaya_tsuma2] 長さ %.3fm: 窓 %d / 中の無地 %.4fm(ε %+.4fm)/ 先の無地 −X %.4fm(素 %.4f)・+X %.4fm(素 %.4f)"
          % (L_m, n, Pp * ES, ep * ES, tr * ES, s.T_r * ES, tl * ES, s.T_l * ES))
    mod, src = periodic_source(g, s)
    lmod = V.join(list(gl.values()), "lmod")
    rmod = V.join(list(gr.values()), "rmod")
    ww = k["ww"]; wc = (ww[0] + ww[1]) * 0.5
    y_r = max(k["ymin_r"], min(tr * 0.5, s.T_r - 0.01))
    y_l = max(k["ymin_l"], min(tl * 0.5, s.T_l - 0.01))
    y_r = min(y_r, tr - 0.01); y_l = min(y_l, tl - 0.01)
    pieces = []
    for j in range(1, n + 1):
        uc = tr + k["wW"] * 0.5 + (j - 1) * (k["wW"] + Pp)
        lb = Pp * 0.5 if j > 1 else tr - y_r
        rb = Pp * 0.5 if j < n else tl - y_l
        if lb > ww[0] - s.win[0][1] or rb > s.win[2][0] - ww[1]:
            raise SystemExit("[nagaya_tsuma2] ⛔ 窓 %d の無地が素の pier を越える(%.3f/%.3f)" % (j, lb, rb))
        pieces.append(take(src, ww[0] - lb, ww[1] + rb, uc - wc, "w%d" % j))
    pieces.append(take(rmod, s.e_r - 2.0, s.e_r + y_r, 0.0 - s.e_r, "tsumaR"))
    pieces.append(take(lmod, s.e_l - y_l, s.e_l + 2.0, a - s.e_l, "tsumaL"))
    o = V.join(pieces, "strip")
    o.data.transform(Matrix.Translation((-a * 0.5, -s.y_f, -s.z_bot)))
    o.data.update()
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
    clean(bm)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    nb = None
    if render:                                          # 向きの検め用: 在庫の knagaya01c を +X の先へ 2m 離して並べる
        nb = dup(mod, "nb")
        nb.data.transform(Matrix.Translation((a * 0.5 + 2.0 / ES - s.d0, -s.y_f, -s.z_bot))); nb.data.update()
    for ob in (src, mod, lmod, rmod):
        bpy.data.objects.remove(ob, do_unlink=True)
    # 向き: 表(素の +y)を Blender −Y(= Unity +Z)へ。Z まわり 180° の**回転**(隅長屋の +X の腕と同じ)
    F = Matrix.Scale(ES, 4) @ Matrix(((-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    for ob in [o] + ([nb] if nb else []):
        ob.data.transform(F); ob.data.update()
    nm = "Nagaya_Tsuma2_L%d" % int(math.floor(L_m * 100 + 0.5))
    o.name = nm; o.data.name = nm
    me = o.data
    xs = [-v.co.x for v in me.vertices]; ys = [v.co.z for v in me.vertices]; zs = [-v.co.y for v in me.vertices]
    print("[nagaya_tsuma2] 出来上がり(Unity 局所 m): X[%.3f, %.3f] Y[%.3f, %.3f] Z[%.3f, %.3f]  面 %d  材 %s"
          % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), len(me.polygons),
             sorted(m.name for m in me.materials if m)))
    path = os.path.join(OUT_N, nm + ".fbx")
    spec = make_spec_straight(s, L_m, o, path)
    V.export_fbx([o], path, kind="building", spec=spec)
    print("[nagaya_tsuma2] wrote %s" % path)
    if render:
        nb.hide_render = True
        shots_straight(o, nm, L_m)
        nb.hide_render = False
        hook()
        V.studio((L_m * 0.2 + 3.0, -14.0, 4.0), (L_m * -0.5 - 3.0, 0.0, 2.6), res=(1900, 1000))
        V.render(os.path.join(SHOT, "%s_narabe.png" % nm))
    return o, path


def make_spec_straight(s, L_m, o, path):
    """札。値は作図の変数(素の実測 × ES と長さ L)から。Unity 局所・倍率 1。+X 端 = l の妻・−X 端 = r の妻。
    帯の最下段(+0.30m)は浮き彫りの下端(+0.3016)より下 ⇒ 外面は地の箱まで引っ込み、端は妻の帯の最下段の端。"""
    h2 = L_m * 0.5
    dO = (s.y_f - s.y_dodai_out) * ES
    dI = (s.y_f - s.y_dodai_in) * ES
    kf = (s.y_koshi - s.y_f) * ES
    jb = (s.y_f - s.y_namako_box) * ES
    Dn = (s.y_f - s.y_namako_box_in) * ES
    z_relief = 0.3016
    xl_low, xr_low = (s.e_r - s.r_foot) * ES, (s.l_foot - s.e_l) * ES      # 最下段で端が外へ出る量(負 = 内)
    secs = []
    h = 0.30
    while h <= 1.80 + 1e-6:
        low = h < z_relief
        x0 = -h2 - (xl_low if low else 0.0)
        x1 = h2 + (xr_low if low else 0.0)
        secs.append((x0, x1, -jb if low else 0.0, -Dn))
        h += 0.25
    front = max(kf, max(c[2] for c in secs))
    back = min(c[3] for c in secs)
    jl = max(c[0] for c in secs)
    jr = min(c[1] for c in secs)
    fx0 = -h2 - (s.e_r - s.r_dodai) * ES
    fx1 = h2 + (s.l_dodai - s.e_l) * ES
    foot = [(fx0, -dO), (fx1, -dO), (fx1, -dI), (fx0, -dI)]
    me = o.data
    xs = [-v.co.x for v in me.vertices]; zs = [-v.co.y for v in me.vertices]; hs = [v.co.z for v in me.vertices]
    rel = os.path.relpath(os.path.join(V.REPO, "Assets/Edo/Models/Nagaya", os.path.basename(path)), V.REPO)
    return dict(prefab=rel.replace(os.sep, "/"),
                source="blender:build_nagaya_kado.py(--straight %g)" % L_m,
                unitScale=1.0, yBottom=0.0, foot=[dict(x=x, y=z) for x, z in foot],
                front=front, back=back,
                jambL=dict(x=jl, z0=back, z1=0.0, y0=0.30, y1=1.80),
                jambR=dict(x=jr, z0=back, z1=0.0, y0=0.30, y1=1.80),
                eave=dict(x0=min(xs), x1=max(xs), z0=min(zs), z1=max(zs), y0=0.0, y1=max(hs)),
                faceOut=0.0, faceIn=-(s.y_f - s.y_wall_in) * ES, height=max(hs))


def shots_straight(o, nm, L_m):
    """Blender の最終座標: 走り = −x が Unity +X(l の妻)/ 表 = −y(Unity +Z)。"""
    hook()
    os.makedirs(SHOT, exist_ok=True)
    h2 = L_m * 0.5
    V.studio((h2 * 0.9, -13.0, 4.0), (0.0, 1.0, 2.6), res=(1800, 1000))            # ① 表から斜め
    V.render(os.path.join(SHOT, "%s_omote.png" % nm))
    V.studio((-h2 * 0.9, 15.0, 7.0), (0.0, -1.0, 2.6), res=(1800, 1000))           # ② 裏から斜め上
    V.render(os.path.join(SHOT, "%s_ura.png" % nm))
    for tag, sx in (("PX", -1.0), ("MX", 1.0)):                                       # ③ 妻を斜めから(Unity +X 端 / −X 端)
        V.studio((sx * (h2 + 6.5), -6.0, 3.5), (sx * (h2 - 1.0), 1.0, 3.0), res=(1500, 1100))
        V.render(os.path.join(SHOT, "%s_tsuma_%s.png" % (nm, tag)))
        V.studio((sx * (h2 + 6.5), 8.0, 5.0), (sx * (h2 - 1.0), 1.0, 3.0), res=(1500, 1100))
        bg((1.0, 0.0, 1.0, 1.0))
        V.render(os.path.join(SHOT, "%s_tsuma_%s_ura_magenta.png" % (nm, tag)))
        bg((0.05, 0.05, 0.05, 1.0))
    V.studio((h2 + 12.0, 1.6, 2.0), (0.0, 1.6, 2.6), ortho_scale=7.5, res=(1200, 1100))   # ④ 小口を正面から(素通しが無いか)
    bg((1.0, 0.0, 1.0, 1.0))
    V.render(os.path.join(SHOT, "%s_koguchi_MX_magenta.png" % nm))
    V.studio((-(h2 + 12.0), 1.6, 2.0), (0.0, 1.6, 2.6), ortho_scale=7.5, res=(1200, 1100))
    V.render(os.path.join(SHOT, "%s_koguchi_PX_magenta.png" % nm))


def print_range_straight():
    V.reset()
    g = read_module()
    gl = read_module("knagaya01l")
    gr = read_module("knagaya01r")
    s = measure(g)
    measure_tsuma(s, gl, gr)
    k = straight_consts(s, gl, gr)
    ok, a = [], 0.5
    while a <= 30.0001:
        ok.append((a, solve_straight(s, k, a) is not None))
        a = round(a + 0.01, 2)
    segs, cur = [], None
    for a, f in ok:
        if f and cur is None:
            cur = [a, a]
        elif f:
            cur[1] = a
        elif cur is not None:
            segs.append(cur); cur = None
    if cur:
        segs.append(cur)
    print("[nagaya_tsuma2] 作れる長さ(m・妻壁の外面どうし): %s" % ", ".join("%.2f〜%.2f" % (a, b) for a, b in segs))
    print("[nagaya_tsuma2] 破風・鬼の出(妻壁の外面から): %.4fm" % s.kera_out)
    for a in (3.0, 4.0, 5.0, 6.0, 7.91, 8.07, 10.0, 12.0):
        pl = solve_straight(s, k, a)
        if pl:
            print("    L=%.3f → 窓 %d / ε %+.3fm / 先の無地 −X %.3f +X %.3fm" % (a, pl[0], pl[1] * ES, pl[2] * ES, pl[3] * ES))


def print_range(s_only=True):
    V.reset()
    g = read_module()
    s = measure(g)
    for side, nm in ((+1, "+X の腕"), (-1, "−Z の腕")):
        ok = []
        a = 3.00
        while a <= 20.0001:
            ok.append((a, solve_arm(s, a, side) is not None))
            a = round(a + 0.01, 2)
        segs, cur = [], None
        for a, f in ok:
            if f and cur is None:
                cur = [a, a]
            elif f:
                cur[1] = a
            elif cur is not None:
                segs.append(cur); cur = None
        if cur:
            segs.append(cur)
        print("[nagaya_kado] %s 作れる長さ(m): %s" % (nm, ", ".join("%.2f〜%.2f" % (a, b) for a, b in segs)))
        for a in (4.79, 5.0, 6.0, 8.065, 10.0):
            pl = solve_arm(s, a, side)
            if pl:
                print("    a=%.3f → 窓 %d / ε %+.3fm / 先の無地の詰め %+.3fm" % (a, pl[0], pl[1] * ES, pl[2] * ES))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--range" in argv:
        print_range()
        return
    if "--straight-range" in argv:
        print_range_straight()
        return
    if "--straight" in argv:
        build_straight(float(argv[argv.index("--straight") + 1]), render="--render" in argv)
        return
    arms = (6.0, 6.0)
    if "--arms" in argv:
        arms = tuple(float(t) for t in argv[argv.index("--arms") + 1].split(","))
        assert len(arms) == 2, "--arms aNegZ,aPosX"
    deg = float(argv[argv.index("--deg") + 1]) if "--deg" in argv else 90.0
    tsu = ()
    if "--tsuma" in argv:
        t = argv[argv.index("--tsuma") + 1]
        tsu = {"negZ": (-1,), "posX": (+1,), "both": (-1, +1)}[t]
    build(arms[0], arms[1], deg=deg, tsu=tsu, render="--render" in argv)


main()
