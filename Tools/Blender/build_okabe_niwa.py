"""**庭の点景** — 岡部筑前守上屋敷の庭(書院の泉水・長局の北の坪・奥庭・見晴らし)。

    blender --background --python Tools/Blender/build_okabe_niwa.py -- [名前...] [--render]
    (名前を省くと全部。ishigumi / tobiishi / kutsunugi / yotsume / kenninji / rangui)

【在庫を先に引いた結果】(`edo-zaiko` 照会 + 自分で実見)
  ⭕ **雪見灯籠は在庫にある** — `Assets/edogoyomi/t_yukimi/t_yukimi.obj`(生 0.43×0.50×0.50 →
     ES=1.818 で **0.784 × 0.916 × 0.906**・1,158三角・テクスチャ `t_yukimi.jpg`)。
     六角の広い笠 + 宝珠 + 火袋 + **竿を持たない三脚** = 雪見型そのもの。⛔ **新造しない。**
     ⚠ 自作の `Own.YukimiLantern`(312三角)は材質 `M_LanternStone` が**テクスチャを1枚も
       持たない**(べた塗り)ので当邸では使わない。他邸で使用中なので消しはしない。
  ⛔ 四つ目垣は**在庫の `Eg.TakeGaki`(= `bamboo garden fence B`)では代用できない** —
     実見すると**竹の菱格子(網代風)**で四つ目ではない。⭕ ただし同じキットの
     **`Bamboo garden fence`(B の付かない方)が本物の四つ目垣**(親柱2 + 立子4 + 胴縁4 +
     棕櫚縄16)。丈 0.900・スパン 1.000 で 1間に合わないので、**この竹の断面・アトラスの帯・
     結びの実体を借りて 1間 × 指定丈に組み直す**。
  ⛔ 建仁寺垣は在庫に無い(`Eg.Hogaki5` は横編みの穂垣で別意匠)。同じ竹から**割竹**を起こす。
  ⛔ 庭石・飛石・沓脱石・乱杭は寸法もピボットも合う物が無い。
     ⚠ `JG.Rock01..03` / `JG.TobiIshi01..02`(FreeJapaneseGarden)は**FBX 内のマテリアル名が
       `Test`** で、Blender から焼き直すと remap が当たらない。⭕ **NatureManufacture の
       photoscanned rock**(`M_photoscanned_rocks_01`・20個体)を使う — 名前が正しく、
       写真計測の実ジオメトリで質も上。

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` / 算出物 `okabe_impl.json` が正典】
  ・`gardens[].ishigumi` 景石 … `h` は**露出高** 0.45〜1.60、`buryRatio` 0.333
  ・`gardens[].gogan.Gogan_NE` 石組護岸 … 長軸 `lenMin` 0.45〜`lenMax` 1.20、30個
  ・`gardens[].iwajima` 岩島 … `hMain` 1.35 + 肩石 0.80、`sink` 0.10
  ・`gardens[].sawatobi` 沢飛石 … 長軸 0.55〜0.62、13枚、天端 = 水面 +0.12
  ・`gardens[].tobiishi` 飛石 … 芯々 0.42〜0.50 の不等ピッチ
  ・`gardens[].kutsunugi` 沓脱石 … 根府川石 L1.2 × W0.75(長局は 0.9×0.6・見晴らしは 1.0×0.7)
  ・`gardens[].rangui` 乱杭 … 径 0.034〜0.052・芯々 0.125・傾 4°・天端は水面 −0.33
  ・垣 … 井戸囲い h1.2(`mizu.gensen.idoKaki`)/ 稲荷の垣 h0.9 / かわやの目隠し 建仁寺垣 h1.5

【向きとピボット(Unity 座標)】幅=X / 高さ=Y / 厚み=Z。**+Z = 見え面**。
  ⚠ Blender は Z-up で、`export_fbx` は **Blender +Y を Unity −Z へ**写す(README)。
    したがって **Unity の見え面 +Z = Blender の −Y**。垣の胴縁・結びはその側へ出す。

  ・`Ishigumi_<i>` … **丈をちょうど 1.000 に正規化**。ピボット = **石の芯・底**。
      ⇒ Unity は `scale = Vector3.one * 総丈` で置く。露出高 h で 1/3 埋めるなら
        総丈 = h × 1.5、`position.y = 地盤 − 0.5h`。長軸で指定される護岸石は
        `scale = 長軸 / W_i`(下の実測表)。
  ・`Tobiishi_<i>` … **長軸をちょうど 1.000 に正規化**。ピボット = **天端の芯**(石は −Y へ垂れる)。
      ⇒ `y = topY` を直に入れられる(沢飛石は水面 +0.12、飛石は地盤 +0.03〜0.05)。
  ・`Kutsunugi` … ピボット = **天端の芯**。実寸 1.200 × 0.750、天端から下へ 0.50。
  ・`YotsumeGaki_<h>` / `KenninjiGaki_<h>` … **1スパン = 1間**。ピボット = **スパンの中心・
      地盤レベル**。柱は **−X 端**(外面が x=−0.909 = bbox がちょうど1間)。
      run の +X 端には `*Post` を1本足す(⛔ 足さないと最後の胴縁が宙で終わる)。
  ・`Rangui_<径>` … ピボット = **頭の芯**、杭は −Y へ垂れる。傾 4° は **+X へ焼き込み**。
      ⇒ yaw を乱数で振れば傾きの方位が散る。

【材】⛔ **新規マテリアルを作らない。**
  ・石 = `M_photoscanned_rocks_01`(NatureManufacture)
  ・竹垣 = `Bamboo garden fence`(Japanese Village Kit)
  ・乱杭 = `M_Wood_fence`(NatureManufacture の丸太。`build_maruta.py` と同じ)
  remap は `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`。

【落とし穴】
  ・⚠ `export_fbx` を通した後は bbox が 0 に潰れる。**測るのもレンダも書き出しの前に**
    (`build_maruta.bounds` は頂点から直に測る)。
  ・⚠ NatureManufacture の FBX は `_LOD0/1/2` が同居する。選り分けないと3重になる。
  ・⛔ 竹を長手方向へただ引き伸ばさない — **節の刻みが伸びて竹に見えなくなる**。
    `_pole()` はアトラスの帯を **`seg` ごとに折り返して(ping-pong)** 貼るので、
    どれだけ長くしても節の間隔が変わらず、折り返し点にも継ぎ目が出ない。
  ・⛔ 飛石の天端を「真っ平ら」に切らない。crown だけ落として**縁は自然石のまま**残す
    (全高の 0.90 で切る)。低く切ると人工の切石に見える。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_maruta as M

OUT  = os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa")
SHOT = os.path.join(V.REPO, "Screenshots")
NMR  = os.path.join(V.REPO, "Assets", "NatureManufacture Assets",
                    "Meadow Environment Dynamic Nature", "Rocks", "Rocks", "Models")
NMR_TEX = os.path.join(NMR, "Textures", "T_Photoscanned_rocks_01_BC.tga")
NMR_NRM = os.path.join(NMR, "Textures", "T_Photoscanned_rocks_01_N.tga")
ROCK_MAT = "M_photoscanned_rocks_01"

KEN = 1.818


# ================================================================ 石(在庫の岩を切って使う)
def _rock(stem, name, stand=False):
    """NatureManufacture の photoscanned rock を1個読む。`stand=True` なら**最長軸を鉛直へ**
    起こす(立石にする)。⛔ 円柱を自作しない — 規則1のとおり在庫の実ジオメトリを使う。"""
    objs = VM.import_fbx_abs(os.path.join(NMR, stem + ".FBX"),
                             keep=lambda n: "LOD1" not in n and "LOD2" not in n)
    o = V.join(objs, name)
    if o is None:
        raise SystemExit("[niwa] %s を読めない" % stem)
    # 材質名を元へ戻す(同じ FBX を何度も読むと `.001` が付く)
    for slot in o.material_slots:
        if slot.material and slot.material.name.split('.')[0] == ROCK_MAT:
            slot.material = bpy.data.materials.get(ROCK_MAT) or slot.material
    if stand:
        mn, mx = M.bounds([o])
        d = [mx.x - mn.x, mx.y - mn.y, mx.z - mn.z]
        k = d.index(max(d))
        if k == 0:
            o.data.transform(Matrix.Rotation(math.radians(90), 4, 'Y'))
        elif k == 1:
            o.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
        o.data.update()
    return o


def _center_xy(o, z_at=None, z_top=None):
    """X/Y を bbox の中心へ、Z を(底=0)または(天端=0)へ寄せる"""
    mn, mx = M.bounds([o])
    dz = -mn.z if z_at == 'bottom' else (-mx.z if z_top else 0.0)
    o.data.transform(Matrix.Translation((-(mn.x + mx.x) * 0.5, -(mn.y + mx.y) * 0.5, dz)))
    o.data.update()


def _norm_h(o, h=1.0):
    """丈(Z)をちょうど h に正規化(一様スケール — 岩の相をこわさない)"""
    mn, mx = M.bounds([o])
    o.data.transform(Matrix.Scale(h / max(mx.z - mn.z, 1e-6), 4))
    o.data.update()


def _norm_long(o, L=1.0):
    """長軸(X/Y の大きい方)をちょうど L に正規化"""
    mn, mx = M.bounds([o])
    o.data.transform(Matrix.Scale(L / max(mx.x - mn.x, mx.y - mn.y, 1e-6), 4))
    o.data.update()


def _cut_z(o, z, keep_below=True):
    """水平面で切る。⚠ **bisect は面を持たない頂点・辺を残す**ので必ず掃除する
    (残すと bbox が実形状より大きく出て、寸法の申告が嘘になる。README)。
    切り口は塞ぐ — 塞がないと石の中が透ける。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector((0, 0, z)), plane_no=Vector((0, 0, 1)),
                           clear_outer=keep_below, clear_inner=not keep_below)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if edges:
        # ⚠ **`sides` は「何角形まで塞ぐか」の上限**。既定の 64 では切り口の輪が
        #   64 辺を超える岩(m_rock_03 など面数の多い個体)で**塞がれずに素通り**し、
        #   沓脱石が「内壁の見える器」になった(2026-09-04 に実見)。**0 = 全部塞ぐ**。
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # ⚠ **`recalc_face_normals` だけでは内向きに揃うことがある。**元の岩は底が開いていて
    #   非閉多様体なので、切り口を塞ぐと**境界の輪が2つ**になり、どちらを外と見るかが
    #   決まらない。⇒ 沓脱石が「内側の壁が見える器」になった(2026-09-04 に実見)。
    #   ⭕ **符号付き体積**で判定して、負なら全面を裏返す。
    vol = 0.0
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for k in range(1, len(vs) - 1):
            a, b, c = vs[0], vs[k], vs[k + 1]
            vol += a.dot(b.cross(c)) / 6.0
    if vol < 0.0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free(); me.update()


# 5個体。⭕ **立ち・臥し・塊を混ぜる** — 三石は立石2+臥石1、護岸は塊が要る
ISHI = [
    ("Rock_02_cut", True,  "立石(主石向き・板状の立ち)"),
    ("Rock_04",     True,  "立石(副石向き・やや太い)"),
    ("m_rock_03",   False, "臥石(添石・低く広い)"),
    ("Rock_06",     False, "塊石(護岸の役石)"),
    ("m_rock_02",   False, "小塊(汀石・肩石)"),
]


def ishigumi(i=0):
    """庭石1個。**丈 = 1.000 に正規化**、ピボット = **石の芯・底**。
    ⇒ Unity は `scale = Vector3.one * 総丈`。露出高 h で 1/3 埋めるなら 総丈 = 1.5h。"""
    stem, stand, note = ISHI[i]
    name = "Ishigumi_%d" % i
    o = _rock(stem, name, stand=stand)
    _norm_h(o, 1.0)
    _center_xy(o, z_at='bottom')
    o.name = o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    mn, mx = M.bounds([o])
    print("[niwa] %-12s %-28s 平 %.3f × %.3f / 丈 1.000  面%d"
          % (name, note, mx.x - mn.x, mx.y - mn.y, len(o.data.polygons)))
    return o, name


# 飛石3種。(元の岩, 天端を切る高さの割合, 目標の 厚/長軸, 説明)
TOBI = [
    ("s_rock_01", 0.62, 0.30, "飛石(薄手)"),
    ("m_rock_02", 0.58, 0.36, "飛石(厚手)"),
    ("Rock_04",   0.66, 0.95, "沢飛石(丈があって池床に据わる)"),
]


def tobiishi(i=0):
    """飛石・沢飛石1枚。**長軸 = 1.000 に正規化**、ピボット = **天端の芯**(石は −Z へ垂れる)。
      ⚠ **逆に高い位置で切っても駄目** — 0.90 で切ったら丸い転石のままで、天端が平らに
      見えなかった(2026-09-04 に実見)。⭕ 全高の **0.6 前後**で丸い頭ごと落とすと、
      平らな天端と自然石の縁が両立する。"""
    stem, cut, ratio, note = TOBI[i]
    name = "Tobiishi_%d" % i
    o = _rock(stem, name)
    _center_xy(o, z_at='bottom')
    mn, mx = M.bounds([o])
    _cut_z(o, mn.z + (mx.z - mn.z) * cut, keep_below=True)
    # 厚み(=Z)を目標の比へ。⚠ 長軸の正規化は最後にやる(Zだけ非一様に触るため)
    mn, mx = M.bounds([o])
    L0 = max(mx.x - mn.x, mx.y - mn.y)
    t0 = mx.z - mn.z
    o.data.transform(Matrix.Diagonal((1.0, 1.0, (ratio * L0) / max(t0, 1e-6), 1.0)))
    o.data.update()
    _norm_long(o, 1.0)
    _center_xy(o, z_top=True)
    o.name = o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    mn, mx = M.bounds([o])
    print("[niwa] %-12s %-28s 平 %.3f × %.3f / 厚 %.3f(天端0・底 %.3f) 面%d"
          % (name, note, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, mn.z, len(o.data.polygons)))
    return o, name


def kutsunugi(name="Kutsunugi"):
    """**沓脱石**(根府川石 1.2 × 0.75)。天端を平らに落とし、平面の縦横だけ寸法へ合わせる。
    ピボット = **天端の芯**。天端から下へ 0.50(露出 0.35 + 根 0.15)。
    ⇒ Unity は `y = 天端の高さ`、寸法違いは `scale = L/1.2` の一様で(0.9→W0.56 / 1.0→W0.63)。"""
    L, W, H = 1.2, 0.75, 0.50
    o = _rock("m_rock_03", name)          # 平面の比 1.51:1 が 1.2:0.75 = 1.6:1 に近い
    _center_xy(o, z_at='bottom')
    mn, mx = M.bounds([o])
    _cut_z(o, mn.z + (mx.z - mn.z) * 0.60, keep_below=True)
    mn, mx = M.bounds([o])
    o.data.transform(Matrix.Diagonal((L / (mx.x - mn.x), W / (mx.y - mn.y),
                                      H / (mx.z - mn.z), 1.0)))
    o.data.update()
    _center_xy(o, z_top=True)
    V.set_origin(o, (0.0, 0.0, 0.0))
    mn, mx = M.bounds([o])
    print("[niwa] %-12s 沓脱石(根府川石)      %.3f × %.3f / 丈 %.3f(天端0・底 %.3f) 面%d"
          % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, mn.z, len(o.data.polygons)))
    return o, name


# ================================================================ 竹(在庫の四つ目垣から借りる)
BAMBOO_FBX = "Fences/Bamboo garden fence.fbx"
BAMBOO_MAT = "Bamboo garden fence"

# アトラスの帯(`Bamboo garden fence.fbx` の実測。u=竹の周・v=竹の長手で節が刻んである)
#   親柱(太竹) 2本ぶん / 立子(細竹) 4本ぶん / 胴縁(細竹) 4本ぶん / 棕櫚縄の結び
U_HASHIRA = [(0.005, 0.118), (0.123, 0.237)]
U_TATEKO  = [(0.611, 0.692), (0.873, 0.954), (0.698, 0.779), (0.786, 0.867)]
U_DOEN    = [(0.244, 0.329), (0.335, 0.420), (0.515, 0.602), (0.424, 0.511)]
V_TATEKO, SEG_TATEKO = (0.005, 0.583), 0.900     # 0.900m ぶんで v をひと巡り
V_DOEN,   SEG_DOEN   = (0.005, 0.614), 1.000
V_HASHIRA, SEG_HASHIRA = (0.006, 0.638), 0.900


class Take(object):
    """竹の稈(かん)を積むメッシュ。**節の刻みはアトラスの帯を折り返して**貼るので、
    どれだけ長くしても節の間隔が変わらない(⛔ 引き伸ばすと竹に見えなくなる)。"""

    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def _ring(self, c, r, axis, n, half):
        """断面の n 角形。axis は稈の向き('x'/'z')。half=True なら**割竹**(D 形)。

        ⚠ **割竹の丸みは見え面(Blender −Y)へ向ける。**+Y へ膨らませると平らな背(弦)が
          表に来て、建仁寺垣が**横縞の平板**に見えた(2026-09-04 に実見)。"""
        pts = []
        a0, a1 = (-math.pi / 2, math.pi / 2) if half else (0.0, math.pi * 2)
        m = n if not half else n
        sgn = -1.0 if half else 1.0
        for i in range(m):
            t = a0 + (a1 - a0) * (i / float(m - 1 if half else m))
            b, d = sgn * math.cos(t) * r, math.sin(t) * r
            if axis == 'x':
                pts.append(Vector((c[0], c[1] + d, c[2] + b)))   # 走り=X、断面は Y-Z
            else:
                pts.append(Vector((c[0] + d, c[1] + b, c[2])))   # 立て=Z、断面は X-Y
        return pts

    def pole(self, p0, p1, r, urange, vrange, seg, n=8, half=False, uflip=False,
             vphase=0.0):
        """p0→p1 の竹1本。`seg` ごとにアトラスの v を折り返す(継ぎ目が出ない)。

        `vphase` は**節の高さの位相**。⛔ 0 のまま並べると 35 本の割竹が**同じ高さで
        いっせいに折り返して**、垣の中ほどに横一文字の帯が出る(2026-09-04 に実見)。"""
        p0, p1 = Vector(p0), Vector(p1)
        axis = 'x' if abs(p1.x - p0.x) > abs(p1.z - p0.z) else 'z'
        L = (p1 - p0).length
        u0, u1 = urange
        v0, v1 = vrange
        # 折り返し点(s が整数を跨ぐ所)に必ずリングを立てる
        s0, s1 = vphase, vphase + L / seg
        cuts = [s0] + [float(k) for k in range(int(math.floor(s0)) + 1,
                                               int(math.ceil(s1)))] + [s1]
        ts = [max(0.0, min(1.0, (cs - s0) * seg / L)) for cs in cuts]
        rings, vs = [], []
        for t, cs in zip(ts, cuts):
            c = p0.lerp(p1, t)
            rings.append(self._ring(c, r, axis, n, half))
            k = int(math.floor(cs + 1e-9))
            fr = cs - k
            vs.append(v0 + (v1 - v0) * (fr if k % 2 == 0 else 1.0 - fr))
        m = len(rings[0])
        # 周方向の u。⭕ **行って戻る**ので帯の両端で継ぎ目が出ない
        def uu(j):
            g = j / float(m - 1) if half else abs(1.0 - abs(2.0 * j / m - 1.0))
            return (u1 - (u1 - u0) * g) if uflip else (u0 + (u1 - u0) * g)
        side = m - 1 if half else m
        for k in range(len(rings) - 1):
            A, B = rings[k], rings[k + 1]
            for j in range(side):
                j2 = (j + 1) % m
                i = len(self.v)
                self.v += [A[j], A[j2], B[j2], B[j]]
                self.f.append([i, i + 1, i + 2, i + 3])
                self.uv += [(uu(j), vs[k]), (uu(j + 1), vs[k]),
                            (uu(j + 1), vs[k + 1]), (uu(j), vs[k + 1])]
        if half:   # 割竹の背(平らな面)を塞ぐ。⛔ 塞がないと裏から透ける
            for k in range(len(rings) - 1):
                A, B = rings[k], rings[k + 1]
                i = len(self.v)
                self.v += [A[-1], A[0], B[0], B[-1]]
                self.f.append([i, i + 1, i + 2, i + 3])
                uc = (u0 + u1) * 0.5
                self.uv += [(uc, vs[k]), (uc, vs[k]), (uc, vs[k + 1]), (uc, vs[k + 1])]
        # 両木口(⛔ 塞がないと竹の中が透ける)
        for (ring, vv, rev) in ((rings[0], vs[0], True), (rings[-1], vs[-1], False)):
            i = len(self.v)
            pts = list(reversed(ring)) if rev else list(ring)
            self.v += pts
            self.f.append(list(range(i, i + len(pts))))
            self.uv += [((u0 + u1) * 0.5, vv)] * len(pts)

    def to_object(self, name, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        me.materials.append(mat)
        uvl = me.uv_layers.new(name="UVMap")
        for j, d in enumerate(uvl.data):
            d.uv = self.uv[j]
        o = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(o)
        return o


def _bamboo_mat():
    """⛔ 新規に作らない。キットの `Bamboo garden fence` を借りる"""
    return V.borrow_material(BAMBOO_FBX, BAMBOO_MAT)


def _nawa_proto():
    """**棕櫚縄の結び**をキットの四つ目垣から実体で借りる(⛔ 自作しない)。
    元は X −0.025..−0.008 / Y 0.153 / Z 0.092 の小片が16個ある。1個だけ採って原点へ寄せる。"""
    objs = V.imp(BAMBOO_FBX)
    o = V.join(objs, "__fence")
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.mesh.separate(type='LOOSE')
    parts = [x for x in bpy.context.selected_objects if x.type == 'MESH']
    best = None
    for x in parts:
        mn, mx = M.bounds([x])
        d = (mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
        if len(x.data.polygons) == 3 and 0.13 < d[1] < 0.18 and 0.07 < d[2] < 0.11:
            best = x; break
    if best is None:
        raise SystemExit("[niwa] 縄の結びが見つからない")
    mn, mx = M.bounds([best])
    # 元は「胴縁が Y に走り、結びが −X 側に出る」。当スクリプトの走りは X なので Z まわりに90°
    best.data.transform(Matrix.Translation((-(mn.x + mx.x) * 0.5, -(mn.y + mx.y) * 0.5,
                                            -(mn.z + mx.z) * 0.5)))
    best.data.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))
    best.data.update()
    me = best.data.copy()
    for x in parts:
        bpy.data.objects.remove(x, do_unlink=True)
    return me


def _nawa_at(mesh, pts, mat, y=None, dz=-0.027):
    """結びを各交点へ。⚠ 全部同じ向きだと機械的に並ぶので少しだけ振る。

    ⚠ **キットでの結びの座付きをそのまま写す。**元は 桟の芯より **0.027 下**(結びの
      尻の垂れがそのぶん下がる)、見込みは**桟の前面をまたぐ**位置にある。bbox の芯で
      置くと**桟の上に載った黒い羽**に見えた(2026-09-04 に実見)。"""
    out = []
    y = (FACE - R_DOEN) if y is None else y
    rnd = random.Random(1856)
    for k, (x, z) in enumerate(pts):
        o = bpy.data.objects.new("nawa%d" % k, mesh.copy())
        bpy.context.collection.objects.link(o)
        if not o.data.materials:
            o.data.materials.append(mat)
        # ⚠ **振る軸は「見え面の法線」= Y。**結びは X-Z 面のカードなので、X(長手)まわりに
        #   振るとカードが面外へ倒れ、立面で**桟の上に載った小さな庇**に見えた
        #   (2026-09-04 に実見)。⭕ Y まわりなら面内の傾き(結び目の癖)になる。
        o.data.transform(Matrix.Rotation(math.radians(rnd.uniform(-8, 8)), 4, 'Y'))
        o.data.transform(Matrix.Translation((x, y, z + dz)))
        o.data.update()
        out.append(o)
    return out


# ---- 作りの値【U — 指図に無い。四つ目垣の常法と在庫の竹の径に合わせた】
R_HASHIRA, R_TATEKO, R_DOEN = 0.032, 0.017, 0.017   # 親柱 φ64 / 立子・胴縁 φ34
ROOT = 0.15          # 根入れ(y<0 へ出る)
FACE = -0.030        # 見え面側の Blender y(⚠ Unity +Z = Blender −Y)


def yotsume(h=1.2, name=None):
    """**四つ目垣 1スパン(1間)**。親柱1 + 立子5 + 胴縁 + 棕櫚縄。
    ⭕ 竹の断面・アトラスの帯・結びの実体は**在庫の四つ目垣から借りている**。
    柱は **−X 端**(外面が x=−0.909)なので **bbox がちょうど1間** — 1.818 ピッチで突き付ける。"""
    name = name or ("YotsumeGaki_%.1f" % h)
    mat = _bamboo_mat()
    nawa = _nawa_proto()
    t = Take()
    a0, a1 = -KEN / 2.0, KEN / 2.0
    # 親柱(−X 端。外面を a0 に合わせて bbox をちょうど1間に)
    cx = a0 + R_HASHIRA
    t.pole((cx, 0, -ROOT), (cx, 0, h), R_HASHIRA, U_HASHIRA[0], V_HASHIRA, SEG_HASHIRA)
    # 立子 5本(芯々 1間/6 = 0.303)。⛔ 等間隔でよい(四つ目垣は割付が命)
    ntate = 5
    xs = [a0 + KEN * (k + 1) / (ntate + 1.0) for k in range(ntate)]
    for k, x in enumerate(xs):
        t.pole((x, 0, -0.06), (x, 0, h), R_TATEKO, U_TATEKO[k % 4], V_TATEKO, SEG_TATEKO)
    # 胴縁(見え面側へ出す = Blender −Y)。h1.2 で4段・h0.9 で3段・h0.6 で2段
    # ⚠ 段数を丈に比例させないと、低い垣で胴縁が詰まって**建仁寺垣のように塞がって見える**。
    #   h0.6 で3段だと芯々 0.18 になり、視軸の窓の足元が抜けない(`nishi.mado.railH`)。
    nrow = 4 if h >= 1.05 else (3 if h >= 0.75 else 2)
    zs = [h - 0.06 - (h - 0.24) * k / float(nrow - 1) for k in range(nrow)]
    for k, z in enumerate(zs):
        t.pole((a0, FACE, z), (a1, FACE, z), R_DOEN, U_DOEN[k % 4], V_DOEN, SEG_DOEN)
    o = t.to_object(name, mat)
    ns = _nawa_at(nawa, [(x, z) for x in xs for z in zs], mat)
    V.dedup_materials()      # ⚠ 縄を借りるのに FBX を2度読むので `Bamboo garden fence.001` ができる
    o = V.join([o] + ns, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    mn, mx = M.bounds([o])
    print("[niwa] %-16s 四つ目垣 h%.2f  1スパン %.3f / 立子%d本 胴縁%d段 結び%d  面%d"
          % (name, h, mx.x - mn.x, ntate, nrow, len(xs) * len(zs), len(o.data.polygons)))
    return o, name


def yotsume_post(h=1.2, name=None):
    """四つ目垣の run の +X 端に足す親柱1本。⛔ 足さないと最後の胴縁が宙で終わる。
    ピボット = **run の終端(柱の +X 面)・地盤レベル** ⇒ `s = s1` をそのまま渡せる。"""
    name = name or ("YotsumeGakiPost_%.1f" % h)
    t = Take()
    t.pole((-R_HASHIRA, 0, -ROOT), (-R_HASHIRA, 0, h), R_HASHIRA,
           U_HASHIRA[1], V_HASHIRA, SEG_HASHIRA)
    o = t.to_object(name, _bamboo_mat())
    V.set_origin(o, (0.0, 0.0, 0.0))
    mn, mx = M.bounds([o])
    print("[niwa] %-16s 四つ目垣の端の柱 φ%.3f 丈 %.2f(根入れ %.2f)"
          % (name, R_HASHIRA * 2, h, ROOT))
    return o, name


# ---- 建仁寺垣【U】割竹の立子を隙間なく詰め、押縁3段+玉縁で押さえる
R_OSHIBUCHI, R_TAMABUCHI = 0.019, 0.024
W_WARIDAKE = 0.052         # 割竹1枚の見付(芯々もこれ = 隙間なく詰める)


def kenninji(h=1.5, name=None):
    """**建仁寺垣 1スパン(1間)**。親柱1 + 胴縁3(裏) + **割竹の立子を隙間なく** +
    押縁3段 + 玉縁。⛔ **立子に目地を空けない** — 7mm でも空けると向こうが透けて
    立面に白い筋が入る(汀の木柵で実見。目隠しの垣なので前提が崩れる)。
    柱は **−X 端**(外面が x=−0.909)。**bbox がちょうど1間**。"""
    name = name or ("KenninjiGaki_%.1f" % h)
    mat = _bamboo_mat()
    nawa = _nawa_proto()
    t = Take()
    a0, a1 = -KEN / 2.0, KEN / 2.0
    cx = a0 + R_HASHIRA
    t.pole((cx, 0, -ROOT), (cx, 0, h), R_HASHIRA, U_HASHIRA[0], V_HASHIRA, SEG_HASHIRA)
    # ⭕ 見込みの積み上げ(Blender −Y が見え面):
    #    胴縁 +0.017 … 割竹の背 0.000 … 割竹の表 −0.026 … 押縁 −0.045 … 玉縁は表をまたぐ
    r = W_WARIDAKE * 0.5
    zs_do = [h * f for f in (0.15, 0.52, 0.88)]
    for k, z in enumerate(zs_do):
        t.pole((a0, R_DOEN, z), (a1, R_DOEN, z), R_DOEN, U_DOEN[k % 4], V_DOEN, SEG_DOEN)
    # 割竹の立子。⛔ 芯々 = 見付で**隙間ゼロ**(目地を空けると向こうが透ける)
    n = int(round(KEN / W_WARIDAKE))
    rnd = random.Random(1856)
    for k in range(n):
        x = a0 + KEN * (k + 0.5) / n
        t.pole((x, 0.0, -0.04), (x, 0.0, h - 0.02), r,
               U_TATEKO[k % 4], V_TATEKO, SEG_TATEKO, n=7, half=True,
               uflip=(k % 2 == 1), vphase=rnd.uniform(0.0, 2.0))
    # 押縁(表。立子を押さえる横竹)
    zs_os = [h * f for f in (0.16, 0.53, 0.89)]
    yo = -r * 2.0 + r - R_OSHIBUCHI
    for k, z in enumerate(zs_os):
        t.pole((a0, yo, z), (a1, yo, z), R_OSHIBUCHI,
               U_DOEN[(k + 2) % 4], V_DOEN, SEG_DOEN)
    # 玉縁(天端の笠竹)。⭕ これが無いと立子の木口が並んで見える
    t.pole((a0, -r + 0.004, h + R_TAMABUCHI - 0.012),
           (a1, -r + 0.004, h + R_TAMABUCHI - 0.012), R_TAMABUCHI,
           U_HASHIRA[1], V_HASHIRA, SEG_HASHIRA)
    o = t.to_object(name, mat)
    # 結び(押縁を胴縁へ縛る。⭕ 押縁1段につき4箇所)
    pts = [(a0 + KEN * (j + 0.5) / 4.0, z) for z in zs_os for j in range(4)]
    ns = _nawa_at(nawa, pts, mat, y=yo - R_OSHIBUCHI)
    V.dedup_materials()      # ⚠ 縄を借りるのに FBX を2度読むので `Bamboo garden fence.001` ができる
    o = V.join([o] + ns, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    mn, mx = M.bounds([o])
    print("[niwa] %-16s 建仁寺垣 h%.2f  1スパン %.3f / 割竹%d枚(芯々%.3f・隙間0) "
          "押縁%d段 玉縁1 結び%d  面%d"
          % (name, h, mx.x - mn.x, n, W_WARIDAKE, len(zs_os), len(pts),
             len(o.data.polygons)))
    return o, name


def kenninji_post(h=1.5, name=None):
    """建仁寺垣の run の +X 端に足す親柱1本。ピボット = run の終端(柱の +X 面)・地盤。"""
    name = name or ("KenninjiGakiPost_%.1f" % h)
    t = Take()
    t.pole((-R_HASHIRA, 0, -ROOT), (-R_HASHIRA, 0, h), R_HASHIRA,
           U_HASHIRA[1], V_HASHIRA, SEG_HASHIRA)
    o = t.to_object(name, _bamboo_mat())
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[niwa] %-16s 建仁寺垣の端の柱 φ%.3f 丈 %.2f(根入れ %.2f)"
          % (name, R_HASHIRA * 2, h, ROOT))
    return o, name


# ================================================================ 乱杭
RANGUI_DIA = (0.034, 0.043, 0.052)     # 指図 `rangui.rMin`..`rMax`(径)
RANGUI_L   = 0.66                      # 全長【U — 指図に無い】
# ⚠ **太い丸太から縮めない。**`wood_log_01/02/04`(径 0.11〜0.12)を径 0.034 まで
#   絞ると半径だけ 0.29 倍になり、樹皮の刻みが実寸で 1/3 になって「つるつるの棒」になる。
#   ⭕ 在庫の**細丸太 `wood_log_06..09`(径 0.062〜0.069)**から採る — 縮み 0.5〜0.8 倍で済む。
#   ⚠ ただし細丸太は実長 0.718〜0.729m しか無いので、全長はそれを超えられない。
RANGUI_TILT = 4.0                      # `rangui.tilt`


def rangui(dia=0.043, name=None):
    """**乱杭1本**。ピボット = **頭の芯**、杭は −Z へ `RANGUI_L` 垂れる。
    傾 4° は **+X へ焼き込んである**ので **yaw を乱数で振れば傾きの方位が散る**。
    ⭕ 在庫の丸太(NatureManufacture `wood_log_0X`)を**半径方向だけ**縮めて切り出す
    (⛔ 一様スケールにしない — 長さが変わって樹皮の密度が杭ごとに食い違う)。"""
    name = name or ("Rangui_" + ("%.3f" % dia))
    stem, frm = {0.034: ("wood_log_09", 0.03), 0.043: ("wood_log_06", 0.05),
                 0.052: ("wood_log_08", 0.04)}.get(round(dia, 3), ("wood_log_09", 0.03))
    o = M.upright(M.log_piece(stem, RANGUI_L, dia, name, frm=frm), top_at_zero=True)
    M.tilt_x(o, RANGUI_TILT, pivot_z=0.0)
    mn, mx = M.bounds([o])
    print("[niwa] %-14s 乱杭 φ%.3f 全長 %.2f 傾%.0f°  bbox %.3f × %.3f × %.3f  面%d"
          % (name, dia, RANGUI_L, RANGUI_TILT, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z,
             len(o.data.polygons)))
    return o, name


# ================================================================ 材の結線とレンダ
def hook():
    """石(NatureManufacture)・竹(Village Kit)・丸太(NatureManufacture)を材質名で振り分ける。
    ⚠ **Alpha の既定値を書くだけでは効かない** — FBX の取り込みが TransparencyFactor を
      Alpha ソケットに**リンクしている**ので、先にリンクを切る(`build_maruta.hook` と同じ罠)。"""
    V.hook_textures()                      # Village Kit(竹垣)はこれで当たる
    for m in bpy.data.materials:
        base = m.name.split('.')[0]
        tex = None
        if base == ROCK_MAT:
            tex, nrm = NMR_TEX, NMR_NRM
        elif base == "M_Wood_fence":
            tex, nrm = M.TEX, None
        if tex is None or not os.path.exists(tex):
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        for sock in ('Alpha', 'Base Color'):
            for lk in list(b.inputs[sock].links):
                nt.links.remove(lk)
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.85
        try:
            m.surface_render_method = 'DITHERED'
        except Exception:
            pass
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(tex, check_existing=True)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        if nrm and os.path.exists(nrm):
            ni = nt.nodes.new('ShaderNodeTexImage')
            ni.image = bpy.data.images.load(nrm, check_existing=True)
            ni.image.colorspace_settings.name = 'Non-Color'
            nm = nt.nodes.new('ShaderNodeNormalMap')
            nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])


def shots(objs, key, box=None):
    """⚠ **書き出しの前に**撮る(`export_fbx` を通すと bbox が 0 に潰れて画角が壊れる)"""
    hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box if box else M.bounds(objs)
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    c = (mn + mx) * 0.5
    S = max(W, H, D)
    # 立面(見え面 = Blender −Y の側から)
    V.studio((c.x, mn.y - S * 3.0, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H * 1500.0 / 1100) * 1.18, res=(1500, 1100))
    V.render(os.path.join(SHOT, "niwa_%s_elev.png" % key))
    # 斜め
    V.studio((c.x - S * 0.9, mn.y - S * 1.3, mx.z + S * 0.55), (c.x, c.y, c.z),
             res=(1500, 1100))
    V.render(os.path.join(SHOT, "niwa_%s_3d.png" % key))


PARTS = {
    "ishigumi":  None, "tobiishi": None, "rangui": None,     # 個体は main が回す
    "kutsunugi": lambda: kutsunugi(),
    "yotsume":   None, "kenninji": None,
}


def _emit(o, name, key, do_render, extra=None):
    objs = [o] + list(extra or [])
    mn, mx = M.bounds(objs)
    print("[niwa] → %-18s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f   "
          "Y範囲 %.3f..%.3f  材質=%s"
          % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, mx.z,
             sorted(set(mm.name for ob in objs for mm in ob.data.materials if mm))))
    if do_render:
        shots(objs, key, box=(mn, mx))
    V.export_fbx(objs, os.path.join(OUT, name + ".fbx"))
    print("[niwa] 書き出し " + os.path.join(OUT, name + ".fbx"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or list(PARTS.keys())
    do_render = "--render" in argv
    for key in want:
        if key not in PARTS:
            print("[niwa] ⚠ 知らない部材: %s" % key); continue
        if key == "ishigumi":
            for i in range(len(ISHI)):
                V.reset(); o, n = ishigumi(i); _emit(o, n, "%s%d" % (key, i), do_render)
        elif key == "tobiishi":
            for i in range(len(TOBI)):
                V.reset(); o, n = tobiishi(i); _emit(o, n, "%s%d" % (key, i), do_render)
        elif key == "rangui":
            for d in RANGUI_DIA:
                V.reset(); o, n = rangui(d); _emit(o, n, "%s%.3f" % (key, d), do_render)
        elif key in ("yotsume", "kenninji"):
            fn, fp = (yotsume, yotsume_post) if key == "yotsume" else (kenninji, kenninji_post)
            # ⚠ **0.6 は `nishi.mado.railH`(視軸の区間 u−0.92〜2.92・庭方 K210)**。
            #   竹垣 h0.9 は床几の視線を切る(余裕 −0.08m)ので、その区間だけ 0.6 に落とす
            hs = (1.2, 0.9, 0.6) if key == "yotsume" else (1.5,)
            for h in hs:
                V.reset(); o, n = fn(h); _emit(o, n, "%s%.1f" % (key, h), do_render)
                V.reset(); o, n = fp(h); _emit(o, n, "%s%.1f_post" % (key, h), do_render)
            if do_render:
                # ⭕ **並べた姿を必ず見る** — 1枚だけでは継ぎ目と端部の不良が見つからない
                V.reset()
                objs = []
                for i in range(3):
                    o, _ = fn(hs[0], "run%d" % i)
                    o.data.transform(Matrix.Translation((i * KEN, 0, 0)))
                    o.data.update(); objs.append(o)
                p, _ = fp(hs[0], "runpost")
                p.data.transform(Matrix.Translation((2.5 * KEN, 0, 0)))
                p.data.update(); objs.append(p)
                shots(objs, key + "_run")
        else:
            V.reset(); o, n = PARTS[key](); _emit(o, n, key, do_render)


if __name__ == "__main__":
    main()
