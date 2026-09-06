"""**つる(蔓)3種を「高木の幹に絡む」形で起こす。**岡部筑前守上屋敷 西の斜面の屋敷林。

    blender --background --python Tools/Blender/build_tsuru.py -- fuji --render
    blender --background --python Tools/Blender/build_tsuru.py -- teika kizuta --render
    blender --background --python Tools/Blender/build_tsuru.py -- all

【なぜ新造するか】指図 `nishi.hayashi.tsuru`(フジ5・テイカカズラ・キヅタ「高木の幹に絡む」)。
在庫方の判定 = **在庫に無い**。⚠ 在庫の `Japanese Village Kit/Prefabs/Foliage/Wisteria_A_01` は
**棚仕立て(藤棚)専用**で、水平の棚から花房を垂らす姿しか作れない。幹に絡む姿には使えない。
⭕ そこで **同キットの Leaves / Branches の部品を切って、螺旋に沿って並べ直す**
(材質名 `Wisteria_A_01` はそのまま。Unity 側の remap が既存 .mat を当てる)。

⛔ **開花させない**(規則10)。旧暦6月の想定でフジの花期(4〜5月)は過ぎている。
  ⇒ `Wisteria_A_Flowers_0*.fbx` は**一切読まない**。アトラス上でも花は u 0.164〜0.262 の
  別の列に居るので、葉の房(u 0.339〜0.998)しか触らない限り花は出ない。

【幹の見立て】幹径 **0.60m(半径 0.30)を基準**に作る。実装は高木の幹の位置に据えて
  `XZ` を `幹径/0.60` で伸縮する前提。⚠ 幹は上へ細るので、つるの側も
  `R(z) = 0.30·(1 − 0.055·z)` で細らせてある(実測: `Tree_Enoki_Mid` の幹は根元 R=0.40、
  `Tree_Jouryoku_Big` は R=0.33)。⭕ **常に幹へ食い込む側へ寄せる** — 浮くと隙間が見えるが、
  食い込みは見えない(門と塀の閉じと同じ判断)。

【巻きの向き】Blender で θ を増やしながら登る = **Unity では上から見て時計回り**
  (`export_fbx` の `axis_forward='-Z', axis_up='Y'` が右手系→左手系の鏡映を伴うため)。
  ノダフジ(フジ)の「右巻き」の見立て。⚠ 和名の右巻き/左巻きは文献で定義が割れる = **確度U**。

【出力(Unity 座標)】幅=X / 高さ=Y / 厚み=Z。ピボット = **幹の足元・幹の芯**、+Y が上。
⛔ LOD は入れない(1本 400〜2,300三角)。⚠ `build_tree.py` は `LOD_0/1/2` の3本を1つの FBX へ
  入れているが、Unity の自動 LODGroup は `_LOD0` 綴りしか拾わないので**3本とも同時に描かれる**。
  つるは小さいので1本にした。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

OUT  = os.path.join(V.REPO, "Assets/Edo/Models/Trees")
SHOT = os.path.join(V.REPO, "Screenshots")

MAT_FUJI = "Wisteria_A_01"                      # Village Kit(枝・葉・花が1枚のアトラス)
MAT_BARK = "M_FJG_Tree_Sakura_Bark_A"           # FJG。新造の高木と同じ材を名乗る
MAT_LEAF = "M_FJG_Tree_Sakura_Sprout_Summer"
FJG = os.path.join(V.REPO, "Assets/Waldemarst/FreeJapaneseGarden/Textures/Trees")
TEX_LEAF = os.path.join(FJG, "Sakura_Summer_001/T_FJG_Sakura_Summer_001_Atlas_Albedo.png")
TEX_BARK = os.path.join(FJG, "T_FJG_Tree_Sakura_Bark_A_Albedo.png")

# ⭐ 葉のアトラスの房の矩形。⚠ `build_tree.py` は末尾で `main()` を無条件に呼ぶので
#   **import できない**(`vkmesh` を切り出したときと同じ事情)。値を変えたら両方直すこと。
SPROUT_UV = [
    (0.2500, 0.5000, 0.4688, 0.8125), (0.7188, 0.0000, 1.0000, 0.2500),
    (0.0000, 0.2812, 0.2188, 0.5000), (0.7188, 0.5000, 1.0000, 0.6875),
    (0.5000, 0.4688, 0.6875, 0.6875), (0.5000, 0.2500, 0.6875, 0.4688),
    (0.0000, 0.0000, 0.2188, 0.2188), (0.5000, 0.7188, 0.6562, 0.9062),
    (0.5000, 0.0000, 0.6875, 0.1875), (0.2812, 0.2812, 0.4688, 0.4375),
]
# 樹皮。⚠ FJG の樹皮は**アトラスでなく1枚のタイル**なので、u は周に1周ぶん・v は長手へ
#   **折り返さずに流す**。⛔ v を 0..1 で折り返すと、折り返しの継ぎ目が**黒い帯**になって
#   蔓が竹の節のように見える(2026-09-04 の検証レンダで実見)。
#   u の両端は隣と接して縦の刻みが混じるので少しだけ内へ寄せる(README「帯の両端は使わない」)。
BARK_UV = (0.02, 0.0, 0.98, 1.0)

TRUNK_R0 = 0.30          # 基準の幹の半径[m](= 幹径 0.60)
TRUNK_TAPER = 0.055      # 1m 上がるごとに細る割合


def trunk_r(z):
    """基準の幹の半径。⚠ 実装は `XZ` を `幹径/0.60` で伸縮するので、ここは常に 0.60 基準。"""
    return max(0.16, TRUNK_R0 * (1.0 - TRUNK_TAPER * z))


# ---------------------------------------------------------------- 螺旋の枠
class Helix(object):
    """幹に巻き付く螺旋。`t`(= 立ち上がり[m])で引き、弧長 `s` からも引ける。

    ⚠ **弧長は立ち上がりより 1.4〜1.5 倍長い**(半径 0.32・1巻き 1.9m で ds/dt≈1.46)。
      つるの部材を立ち上がりの長さぶんだけ並べると**巻きの途中で足りなくなる**。"""

    def __init__(self, h, rise_per_turn, off=0.05, phase=0.0, n=400):
        self.h = h
        self.k = 2.0 * math.pi / rise_per_turn      # dθ/dt [rad/m]
        self.off = off                              # 幹の表面からの持ち出し
        self.phase = phase
        self.n = n
        # 弧長の表(数値積分)
        self.ts = [h * i / n for i in range(n + 1)]
        self.ss = [0.0]
        for i in range(1, n + 1):
            t0, t1 = self.ts[i - 1], self.ts[i]
            tm = 0.5 * (t0 + t1)
            r = trunk_r(tm) + off
            self.ss.append(self.ss[-1] + (t1 - t0) * math.hypot(1.0, r * self.k))
        self.arc = self.ss[-1]

    def t_of(self, s):
        s = min(max(s, 0.0), self.arc)
        lo, hi = 0, self.n
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.ss[mid] <= s: lo = mid
            else: hi = mid
        d = self.ss[hi] - self.ss[lo]
        f = 0.0 if d < 1e-9 else (s - self.ss[lo]) / d
        return self.ts[lo] + (self.ts[hi] - self.ts[lo]) * f

    def frame(self, t):
        """(位置, 外向き, 走り方向と直交する接面の軸, 接線)。⛔ 中心軸でなく**幹の面**を返す。"""
        th = self.phase + self.k * t
        r = trunk_r(t) + self.off
        P = Vector((r * math.cos(th), r * math.sin(th), t))
        N = Vector((math.cos(th), math.sin(th), 0.0))            # 外向き(幹から離れる)
        T = Vector((-r * self.k * math.sin(th), r * self.k * math.cos(th), 1.0)).normalized()
        B = T.cross(N).normalized()
        return P, N, B, T


# ---------------------------------------------------------------- キットの部品を切り出す
class Part(object):
    """キットの FBX から切り出した「部品」。頂点・面・UV を素のまま持つ。"""

    def __init__(self, verts, faces, uvs):
        self.v, self.f, self.uv = verts, faces, uvs
        zs = [p.z for p in verts]
        self.z0, self.z1 = min(zs), max(zs)
        self.zlen = self.z1 - self.z0
        self.cx = sum(p.x for p in verts) / len(verts)
        self.cy = sum(p.y for p in verts) / len(verts)


def split_parts(relpath, scale):
    """FBX を読み、**連結成分ごと**に切り分けて返す。
    ⚠ `Wisteria_A_Branches_01` は 24 quad = **1m ほどの縄が4本**(2本の蔓の上下)。
      1本ずつ取り出せば、螺旋に沿って好きなだけ継げる。"""
    o = V.imp(relpath)[0]
    me = o.data
    uvl = me.uv_layers.active.data
    # union-find で連結成分
    par = list(range(len(me.vertices)))
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for p in me.polygons:
        vs = list(p.vertices)
        for b in vs[1:]:
            ra, rb = find(vs[0]), find(b)
            if ra != rb: par[ra] = rb
    groups = {}
    for p in me.polygons:
        groups.setdefault(find(p.vertices[0]), []).append(p)
    parts = []
    for _, polys in groups.items():
        idx, verts, faces, uvs = {}, [], [], []
        for p in polys:
            f = []
            for li, vi in zip(p.loop_indices, p.vertices):
                if vi not in idx:
                    idx[vi] = len(verts)
                    verts.append(me.vertices[vi].co * scale)
                f.append(idx[vi])
            faces.append(f)
            uvs.append([tuple(uvl[li].uv) for li in p.loop_indices])
        parts.append(Part(verts, faces, uvs))
    bpy.data.objects.remove(o, do_unlink=True)
    parts.sort(key=lambda q: q.z0)
    return parts


# ---------------------------------------------------------------- メッシュの受け皿
class Acc(object):
    """面を貯めて1つのメッシュにする(材ごとにスロットを分ける)。"""

    def __init__(self, mats):
        self.mats = mats
        self.v, self.f, self.uv, self.mi = [], [], [], []

    def add(self, pts, uvs, mat=0):
        i = len(self.v)
        self.v += list(pts)
        self.f.append([i + k for k in range(len(pts))])
        self.uv += list(uvs)
        self.mi.append(mat)

    def to_object(self, name):
        """⚠ UV は**面の追加順に平らに**貯めてある。`from_pydata` は面の順も
        ループの順も保つので、そのまま流し込める(index を計算し直さない)。"""
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for p, m in zip(me.polygons, self.mi):
            p.material_index = m
            for li in p.loop_indices:
                uvl.data[li].uv = self.uv[k]; k += 1
        assert k == len(self.uv), "UV の数が面のループ数と合わない (%d/%d)" % (k, len(self.uv))
        for p in me.polygons:
            p.use_smooth = True          # ⛔ 6角柱の facet を出さない(カードは平面なので影響なし)
        for nm in self.mats:
            me.materials.append(bpy.data.materials.get(nm) or V.named_material(nm))
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        return o


def tube(acc, path, r0, r1, nside, mat, uv_rect, vrep=0.5, cap=True, wob=0.0):
    """細い蔓の茎。多角柱で継ぐ(先細り)。UV は u=周・v=長手。

    ⛔⛔ **断面の向きを毎区間 `rotation_difference` で作らない。**あれは接線から
      向きを1つ選ぶだけで**ねじれ(roll)が決まらない**ので、区間ごとに断面が勝手に
      回り、継ぎ目が**輪切りの節**になる(2026-09-04 に螺旋の蔓で実見。
      「UV の折り返しのせい」と2度誤診した)。⭕ **平行移動枠(parallel transport)**で
      前の区間の法線を接線の回転ぶんだけ回して引き継ぐ。
    ⛔ **`cap` を切らない。**多角柱は素のままでは両端が開いていて小口から中が透ける
      (README「`roof top x1` は両端が開いている」と同じ罠)。
    ⚠ `wob` は半径の揺らぎ。0 だと**機械で挽いた棒**に見える(蔓は太さが一様でない)。"""
    pts = [p for i, p in enumerate(path) if i == 0 or (p - path[i - 1]).length > 1e-5]
    if len(pts) < 2:
        return
    n = len(pts)
    # --- 接線
    tg = []
    for i in range(n):
        if i == 0:      d = pts[1] - pts[0]
        elif i == n - 1: d = pts[-1] - pts[-2]
        else:            d = pts[i + 1] - pts[i - 1]
        tg.append(d.normalized())
    # --- 平行移動枠
    up = Vector((0, 0, 1))
    nb = up.cross(tg[0])
    if nb.length < 1e-4: nb = Vector((1, 0, 0)).cross(tg[0])
    nb.normalize()
    frames = [nb]
    for i in range(1, n):
        q = tg[i - 1].rotation_difference(tg[i])
        v = (q @ frames[-1])
        v = (v - tg[i] * v.dot(tg[i]))
        frames.append(v.normalized() if v.length > 1e-6 else frames[-1])
    # --- 弧長
    arc = [0.0]
    for i in range(1, n):
        arc.append(arc[-1] + (pts[i] - pts[i - 1]).length)
    total = arc[-1]
    rings = []
    for i in range(n):
        f = arc[i] / max(total, 1e-6)
        r = r0 + (r1 - r0) * f
        if wob:
            r *= 1.0 + wob * math.sin(f * 11.3 + 1.7) * math.cos(f * 4.1)
        e1 = frames[i]; e2 = tg[i].cross(e1).normalized()
        rings.append([pts[i] + e1 * (r * math.cos(k / nside * math.tau))
                            + e2 * (r * math.sin(k / nside * math.tau))
                      for k in range(nside)])
    u0r, v0r, u1r, v1r = uv_rect
    for i in range(n - 1):
        va = v0r + (v1r - v0r) * (arc[i] / vrep)
        vb = v0r + (v1r - v0r) * (arc[i + 1] / vrep)    # ⛔ 0..1 で折り返さない(継ぎ目が出る)
        for k in range(nside):
            j = (k + 1) % nside
            ua = u0r + (u1r - u0r) * (k / nside)
            ub = u0r + (u1r - u0r) * ((k + 1) / nside)
            acc.add([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]],
                    [(ua, va), (ub, va), (ub, vb), (ua, vb)], mat)
    if cap:
        cu = (u0r + u1r) * 0.5; cv = (v0r + v1r) * 0.5
        acc.add(list(reversed(rings[0])), [(cu, cv)] * nside, mat)
        acc.add(rings[-1], [(cu, cv)] * nside, mat)     # ⛔ 小口を開けない(中が透ける)


# ---------------------------------------------------------------- ① フジ
# ⚠ **`Wisteria_A_Branches_01` は縄ではない。**24 quad の実測で、
#   **枝の絵を描いた平らなカード**(藤棚を下から見上げる用)だと分かった。
#   ⛔ これを螺旋に沿って回すと、幹のまわりに**板の破片が飛ぶ**(2026-09-04 の検証レンダで実見)。
#   ⭕ したがって:
#     ・**蔓の本体は多角柱で起こす**(絡む縄の太さは実体でないと出ない)。材は在庫の樹皮
#       `M_FJG_Tree_Sakura_Bark_A` — **この木に絡むのだから、隣の高木と同じ樹皮材でよい**。
#     ・⛔ **Branches のカードは使わない(`twigs=0`)。**幹の面へ巻き付けて副えの小枝に
#       できないか3度試したが、カードの絵は「藤棚を下から見上げた枝ぶり」で、
#       幹に貼ると**色の抜けた白い帯**にしか見えなかった(巻き順を戻しても同じ)。
#       ⭕ 経路は残してあるので、`twigs` に数を入れれば復活する。
#     ・**葉は Wisteria_A_Leaves_01/02 の実物**(羽状複葉の姿がフジの見分け)。
# 長さ(= 幹に沿った立ち上がり)[m] / 1巻きの立ち上がり / 葉の房 / 縄の本数 / 小枝のカード
FUJI = [dict(h=3.4, turn=1.65, sprays=22, strands=2, twigs=0,  r0=0.050, r1=0.026),
        dict(h=4.6, turn=1.95, sprays=30, strands=2, twigs=0,  r0=0.058, r1=0.028),
        dict(h=5.8, turn=2.15, sprays=40, strands=3, twigs=0,  r0=0.066, r1=0.030)]


def build_fuji(i, rnd):
    spec = FUJI[i]
    twigs = split_parts("Foliage/Wisteria_A_Branches_01.fbx", V.S)
    sprays = (split_parts("Foliage/Wisteria_A_Leaves_01.fbx", V.S)
              + split_parts("Foliage/Wisteria_A_Leaves_02.fbx", V.S))
    acc = Acc([MAT_BARK, MAT_FUJI])
    hx = []
    for k in range(spec["strands"]):
        hx.append(Helix(spec["h"], spec["turn"],
                        off=0.052 + 0.016 * k,
                        phase=math.tau * k / spec["strands"] + rnd.uniform(-0.15, 0.15)))

    # --- 蔓の本体。⭐ 2〜3本が絡み合いながら登る(フジの太い蔓の見分け)
    for k, H in enumerate(hx):
        path = []
        n = max(20, int(H.arc / 0.17))
        for j in range(n + 1):
            P, _, _, _ = H.frame(H.t_of(H.arc * j / n))
            path.append(P)
        tube(acc, path, spec["r0"] * rnd.uniform(0.85, 1.0), spec["r1"], 6, 0,
             BARK_UV, vrep=0.70, wob=0.16)

    # --- 副えの小枝(キットのカードを**幹の面へ巻き付ける**)。⛔ 空中で回さない
    for _ in range(spec["twigs"]):
        pt = twigs[rnd.randrange(len(twigs))]
        t0 = spec["h"] * rnd.uniform(0.05, 0.80)
        az = rnd.uniform(0, math.tau)
        flip = 1.0 if rnd.random() < 0.5 else -1.0
        lean = rnd.uniform(-0.55, 0.55)            # カードを幹に対して斜めに寝かせる
        cs = rnd.uniform(1.25, 1.75)               # ⚠ 素のままだと幹の上の「染み」にしか見えない
        for f, fuv in zip(pt.f, pt.uv):
            pts = []
            for vi in f:
                p = pt.v[vi]
                dx = (p.x - pt.cx) * flip * cs
                dz = ((p.z - pt.z0) - pt.zlen * 0.5) * cs
                z = t0 + dz + dx * lean
                r = trunk_r(max(0.0, z)) + 0.016 + (p.y - pt.cy) * 0.55 * cs
                a = az + dx / max(0.12, trunk_r(max(0.0, z)))
                pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
            # ⛔ 鏡像にしたら巻き順を戻す。戻さないと法線が内向きになり、
            #   表から見ると裏面が当たって**色の抜けた白い帯**に見える(2026-09-04 実見)
            if flip < 0:
                pts = list(reversed(pts)); fuv = list(reversed(fuv))
            acc.add(pts, fuv, 1)

    # --- 葉の房。⭐ 上ほど密(光を求めて樹冠へ出る)。⛔ 等間隔に並べない
    for _ in range(spec["sprays"]):
        Hs = hx[rnd.randrange(len(hx))]
        t = spec["h"] * (rnd.random() ** 0.55) * 0.95 + spec["h"] * 0.04
        P, N, B, _ = Hs.frame(t)
        out = (N + B * rnd.uniform(-0.45, 0.45)
               - Vector((0, 0, rnd.uniform(0.10, 0.55)))).normalized()
        side = Vector((0, 0, 1)).cross(out)
        if side.length < 1e-4: side = Vector((1, 0, 0))
        side.normalize()
        down = out.cross(side).normalized()
        roll = rnd.uniform(0, math.tau)
        s1 = side * math.cos(roll) + down * math.sin(roll)
        d1 = -side * math.sin(roll) + down * math.cos(roll)
        pt = sprays[rnd.randrange(len(sprays))]
        # 房の付け根 = bbox の最大Y側。そこを蔓の面へ置く(⛔ 中心で合わせると宙に浮く)
        anchor = Vector((pt.cx, max(p.y for p in pt.v), pt.z1))
        base = P + N * (spec["r0"] * 0.8)
        sc = rnd.uniform(0.55, 0.95)               # ⚠ 素の房は 0.9m。幹径 0.6 に対して大きすぎる
        M = Matrix(((s1.x, -out.x, d1.x), (s1.y, -out.y, d1.y), (s1.z, -out.z, d1.z)))
        for f, fuv in zip(pt.f, pt.uv):
            acc.add([base + M @ ((pt.v[vi] - anchor) * sc) for vi in f], fuv, 1)

    return acc.to_object("Tsuru_Fuji_%02d" % (i + 1)), spec["h"]


# ---------------------------------------------------------------- ② テイカカズラ / キヅタ
# 常緑のつる。⭐ **幹に貼り付く**(フジのように空中へ出ない)。地味に、下から上へ。
# ⭐ **覆う側は必ずローカル +X**(方位 0 を中心にした帯)。⛔ 乱数で振らない —
#   振ると個体ごとに「どちらを向いているか」が分からなくなり、検証レンダで裏側に回った
#   (2026-09-04 に実見。テイカが幹の陰に隠れて何も写らなかった)。
#   ⭕ **向きは実装が yaw で振る**(部材は向きを持たない)。
HARI = {
    "teika": dict(label="テイカカズラ",
                  hs=[2.6, 3.6], leaf=0.075, cards=[240, 310], sector=2.6,
                  runners=3, cross=0.20, reach=0.13, jitter=0.028),
    "kizuta": dict(label="キヅタ",
                   hs=[2.2, 3.2], leaf=0.160, cards=[200, 250], sector=4.2,
                   runners=4, cross=0.30, reach=0.10, jitter=0.022),
}


def build_hari(kind, i, rnd):
    sp = HARI[kind]
    h = sp["hs"][i]
    acc = Acc([MAT_BARK, MAT_LEAF])
    sector = sp["sector"]                       # 覆う方位の幅[rad]。⛔ 全周を覆わない
    az0 = -0.5 * sector                         # 帯の中心 = ローカル +X(上の注記)

    # --- 匍匐する茎(不定根で貼り付く蔓)。⛔ 直線にしない
    for k in range(sp["runners"]):
        a0 = az0 + sector * (k + 0.5) / sp["runners"] + rnd.uniform(-0.18, 0.18)
        top = h * rnd.uniform(0.80, 1.0)
        path = []
        for j in range(11):
            t = top * j / 10.0
            a = a0 + math.sin(t * rnd.uniform(1.1, 1.9) + k) * rnd.uniform(0.18, 0.42)
            r = trunk_r(t) + 0.012
            path.append(Vector((r * math.cos(a), r * math.sin(a), t)))
        tube(acc, path, 0.016, 0.006, 4, 0, BARK_UV, vrep=0.45, wob=0.22)

    # --- 葉のカード。⛔ 十字に組み過ぎない(幹に貼るので大半は外向き1枚でよい)
    n = sp["cards"][i]
    for _ in range(n):
        # ⚠ 足元から始めると、カードの下半分が**地面より下**へ潜る(実測 −0.26m)。
        #   ⭕ 葉の付き始めをカード1枚ぶん持ち上げる
        t = sp["leaf"] * 1.4 + (h - sp["leaf"] * 1.4) * (rnd.random() ** 0.85)
        a = az0 + rnd.uniform(0.0, sector) + rnd.gauss(0, 0.10)
        r = trunk_r(t)
        N = Vector((math.cos(a), math.sin(a), 0.0))
        E1 = Vector((-math.sin(a), math.cos(a), 0.0))
        E2 = Vector((0.0, 0.0, 1.0))
        roll = rnd.uniform(0, math.tau)
        e1 = E1 * math.cos(roll) + E2 * math.sin(roll)
        e2 = -E1 * math.sin(roll) + E2 * math.cos(roll)
        # 外へ起こす(葉柄が幹から浮く)。上へ行くほど「探る」枝が立つ
        tilt = rnd.uniform(0.05, 0.55) * (0.6 + 0.8 * t / max(h, 1e-6))
        e2t = e2 * math.cos(tilt) + N * math.sin(tilt)
        s = sp["leaf"] * rnd.uniform(0.70, 1.35)
        reach = sp["reach"] * rnd.random() ** 2.0
        c = N * (r - 0.022 + reach + rnd.uniform(-1, 1) * sp["jitter"]) + Vector((0, 0, t))
        u0, v0, u1, v1 = SPROUT_UV[rnd.randrange(len(SPROUT_UV))]
        ar = (v1 - v0) / max(1e-6, (u1 - u0))
        quads = [(e1, e2t)]
        if rnd.random() < sp["cross"]:
            quads.append((e2t, -e1))            # 十字の2枚目(volume 稼ぎ)
        for f1, f2 in quads:
            pts = [c - f1 * s - f2 * s * ar, c + f1 * s - f2 * s * ar,
                   c + f1 * s + f2 * s * ar, c - f1 * s + f2 * s * ar]
            acc.add(pts, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], 1)

    name = "Tsuru_%s_%02d" % ("Teika" if kind == "teika" else "Kizuta", i + 1)
    return acc.to_object(name), h


# ---------------------------------------------------------------- 検証レンダ
def probe_trunk(h):
    """⚠ **レンダ専用の当て木**(幹の見立て)。⛔ 書き出さない。
    つるが幹へ食い込んでいるか・浮いていないかは、幹を描かないと判定できない。"""
    bm = bmesh.new()
    n, m = 20, 12
    rings = []
    for j in range(m + 1):
        z = (h + 1.2) * j / m - 0.3
        r = trunk_r(max(0.0, z))
        rings.append([bm.verts.new((r * math.cos(i / n * math.tau),
                                    r * math.sin(i / n * math.tau), z)) for i in range(n)])
    for j in range(m):
        for i in range(n):
            k = (i + 1) % n
            bm.faces.new((rings[j][i], rings[j][k], rings[j + 1][k], rings[j + 1][i]))
    me = bpy.data.meshes.new("__trunk"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("__trunk", me)
    bpy.context.scene.collection.objects.link(o)
    mt = bpy.data.materials.new("__trunk_probe")
    mt.use_nodes = True
    b = next(x for x in mt.node_tree.nodes if x.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (0.20, 0.16, 0.13, 1)
    b.inputs['Roughness'].default_value = 0.9
    o.data.materials.append(mt)
    return o


def hook():
    """検証レンダのためだけにテクスチャを結ぶ。⛔ FBX には材質**名**しか入らない。

    ⚠ **`V.hook_textures()` に任せない。**(a) キットの FBX を読むと **FBX 取り込みが作った
      画像ノード**が既に居るので、`next(TEX_IMAGE)` で拾うと**そちらの α**(未読込)を繋いで
      しまう。(b) `hook_textures` は α を 1.0 に固定するので、**葉のカードが黒い矩形の板**に
      なる(2026-09-04 の検証レンダで2度実見)。⭕ 画像は**パスを名指しで**読み、
      Base Color と Alpha を自分で繋ぐ。
    ⚠ α は **Greater Than で 0/1 に丸める**。EEVEE Next の DITHERED は確率的透過なので、
      生の α を流すと半端な値が斑に残る。"""
    TEX = {MAT_FUJI: (os.path.join(V.TEX, "Wisteria_A_01_AlbedoTransparency.png"), True),
           MAT_LEAF: (TEX_LEAF, True),
           MAT_BARK: (TEX_BARK, False)}
    for nm, (tex, cut) in TEX.items():
        m = bpy.data.materials.get(nm)
        if m is None or not os.path.exists(tex):
            continue
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):                    # ⛔ 取り込みが作ったノードを残さない
            if n.type != 'OUTPUT_MATERIAL':
                nt.nodes.remove(n)
        b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.location = (-200, 0)
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
        img = nt.nodes.new('ShaderNodeTexImage'); img.location = (-700, 200)
        img.image = bpy.data.images.load(tex, check_existing=True)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.78
        if cut:
            gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'
            gt.inputs[1].default_value = 0.35; gt.location = (-450, -100)
            nt.links.new(img.outputs['Alpha'], gt.inputs[0])
            nt.links.new(gt.outputs['Value'], b.inputs['Alpha'])
            m.surface_render_method = 'DITHERED'
            try: m.show_transparent_back = False
            except Exception: pass


def tri(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    kinds = [a for a in argv if not a.startswith("--")] or ["all"]
    if kinds == ["all"]: kinds = ["fuji", "teika", "kizuta"]
    os.makedirs(OUT, exist_ok=True)
    for kind in kinds:
        n = len(FUJI) if kind == "fuji" else len(HARI[kind]["hs"])
        for i in range(n):
            V.reset()
            rnd = random.Random(1856 + 101 * i + (0 if kind == "fuji"
                                                  else 17 if kind == "teika" else 43))
            if kind == "fuji": o, h = build_fuji(i, rnd)
            else:              o, h = build_hari(kind, i, rnd)
            V.dedup_materials()
            V.set_origin(o, (0, 0, 0))                 # ピボット = 幹の足元・幹の芯
            mn, mx = V.bbox([o])
            # ⚠ **書き出しの前に測る**(export_fbx を通すと bbox が 0 に潰れる。README)
            print("[tsuru] %-18s tri=%5d  W %.2f × H %.2f × D %.2f  (Unity座標) 丈の呼び %.2f"
                  % (o.name, tri(o), mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, h))
            print("[tsuru]   材質: %s" % ", ".join(m.name for m in o.data.materials))
            if do_render:
                hook()
                probe_trunk(h)
                # ⭐ カメラは**覆う側(ローカル +X)**へ置く。⛔ 裏へ回ると何も写らない
                V.studio((3.3, -1.5, h * 0.58), (0.0, 0.0, h * 0.48), res=(900, 1300))
                V.render(os.path.join(SHOT, "tsuru_%s_%02d.png" % (kind, i + 1)))
            path = os.path.join(OUT, o.name + ".fbx")
            V.export_fbx([o], path)
            print("[tsuru] wrote %s" % path)


main()
