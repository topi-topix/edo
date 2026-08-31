"""松江松平邸の附属屋・工作物を起こす — 土蔵・作事小屋・数寄屋・稲荷社・石井戸枠・隅櫓。

    blender --background --python Tools/Blender/build_matsudaira_dewa_fuzokuya.py -- [名前...] [--render]
    (名前を省くと全部。--render で /tmp/fuzokuya_<名前>.png に検証レンダ)

【なぜ新造するか】`docs/asset-catalog.md` §10「無い物」の照会結果:
  ・**井戸**   … 無い。「合成する」とだけ書かれている → 石井戸枠として一体で起こす
  ・**鳥居・社殿・祠** … 無い。「稲荷は Castle の Gate 等では代用不能 — 自作が要る」
  ・**隅櫓**   … 二層櫓は無い(`es_hinomi` は火の見櫓で別物、Castle の `Gate Yagura` は
                 門の上の櫓の**部材**で、独立した隅櫓にはならない)
  ・**土蔵**   … `es_kura` はあるが ES 後 6.2×6.6m。指図の 4×7間(7.27×12.73m)に
                 1.92倍の引き伸ばしが要る → 棟が伸びて破綻するので寸法どおり起こす
  ・**作事小屋・数寄屋** … 無い(`Small House` は 13.2×9.5m で 10×4間にも 2.5間角にも合わない)

【寸法】**指図 `matsudaira_dewa_sashizu.json` の service / wells / yagura が正典。ここで決めない。**
  Dozo 4×7間 / Koya 10×4間 / Sukiya 2.5×2.5間 / Inari 2×2間 / Yagura 3間角。
  ⚠ 指図の間数を変えたら、ここの既定値ではなく**指図を直してから**引数で焼き直すこと。

【姿の確度】
  ・土蔵・作事小屋・石井戸枠 …【B】江戸の一般類型。当家の一次史料は無い
  ・数寄屋(四畳半+水屋)   …【B】同上。指図 service.Chatei の note を参照
  ・稲荷社                  …【B】邸内稲荷は武家屋敷の常。当家の祭神・社殿形式は未確認
  ・隅櫓                    …【?】**当家に櫓があった典拠は無い**(指図 yagura._ のまま)。
                                置くこと自体が推定なので、姿も一般的な二重櫓に留める

【材と UV — README の規約。新規マテリアルを作らない】
  木部   Village Kit `Fences/Fence_B_01_x2.fbx` の `Fence_B_01`
  石     Village Kit `Foundations/Foundation_A_01_2x2.fbx` の `Foundation_A_01`
  漆喰   Japanese Castle `Exterior/Wall Exterior Defence.fbx` の `Wall Exterior Defence`
  屋根   `build_goten_roof.make_kirizuma / make_irimoya` が Village Kit の実瓦を葺く
  ⚠ UV は一点貼りにしない(2026-08-15 の指摘)。面ごとに矩形を割り当てる。

【座標】論理 (走り, 高さ, 厚み) → Blender (X, Z, Y)。書き出し後の Unity は
  幅=X / 高さ=Y / 奥行=Z。**ピボットは footprint の中心・地盤レベル**
  (据える側が (u,v) 矩形の中心をそのまま使えるように)。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_goten_roof as R

PROJ = V.REPO
JC = os.path.join(PROJ, "Assets", "Japanese Castle")
OUT = os.path.join(PROJ, "Assets", "Edo", "Models", "Fuzokuya")
KEN = 1.818

WOOD_SRC, WOOD_MAT = "Fences/Fence_B_01_x2.fbx", "Fence_B_01"
STONE_SRC, STONE_MAT = "Foundations/Foundation_A_01_2x2.fbx", "Foundation_A_01"
PLASTER_SRC, PLASTER_MAT = "Exterior/Wall Exterior Defence.fbx", "Wall Exterior Defence"

# 借用に失敗したときの控えの UV(build_matsudaira_omotemon.py と同じ値)
WOOD_UV_FB = (0.600, 0.03, 0.770, 0.97)
WALL_UV_FB = (0.55, 0.34, 0.95, 0.62)
STONE_UV_FB = (0.05, 0.05, 0.45, 0.45)


# ---------------------------------------------------------------- 面ごとに貼る箱
class Mesh(object):
    """四角形を1枚ずつ積む。頂点は溶接しない(面ごとにUVを決めるため)"""

    def __init__(self):
        self.v, self.f, self.uv, self.mi = [], [], [], []

    def quad(self, pts, uv, mat=0):
        """pts は論理座標 (走り, 高さ, 厚み)。Blender は Z が上なので入れ替える"""
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2, i + 3])
        u0, v0, u1, v1 = uv
        self.uv += [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        self.mi.append(mat)

    def tri(self, pts, uv, mat=0):
        i = len(self.v)
        self.v += [Vector((p[0], p[2], p[1])) for p in pts]
        self.f.append([i, i + 1, i + 2])
        u0, v0, u1, v1 = uv
        self.uv += [(u0, v0), (u1, v0), ((u0 + u1) / 2, v1)]
        self.mi.append(mat)

    def box(self, x0, x1, y0, y1, z0, z1, uv, mat=0):
        """直方体。走り x・高さ y・厚み z"""
        self.quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], uv, mat)
        self.quad([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], uv, mat)
        self.quad([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], uv, mat)
        self.quad([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], uv, mat)
        self.quad([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], uv, mat)
        self.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], uv, mat)

    def koshi(self, x0, x1, y0, y1, z0, z1, uv, mat=0, pitch=0.13, bar=0.035, yoko=2):
        """格子窓。**板を1枚貼らない** — 竪子を実体で並べ、横子を数本渡す。
        一枚貼りにすると木のベタ板になる(番所の出格子で 2026-08-25 に踏んだ)。"""
        n = max(2, int((x1 - x0) / pitch))
        for i in range(n):
            cx = x0 + (x1 - x0) * (i + 0.5) / n
            self.box(cx - bar, cx + bar, y0, y1, z0, z1, uv, mat)
        for j in range(yoko):
            cy = y0 + (y1 - y0) * (j + 0.5) / yoko
            self.box(x0, x1, cy - bar, cy + bar, z0 - 0.008, z1 + 0.008, uv, mat)

    def koshi_z(self, z0, z1, y0, y1, x0, x1, uv, mat=0, pitch=0.13, bar=0.035, yoko=2):
        """格子窓(奥行き方向に並ぶ面用)"""
        n = max(2, int((z1 - z0) / pitch))
        for i in range(n):
            cz = z0 + (z1 - z0) * (i + 0.5) / n
            self.box(x0, x1, y0, y1, cz - bar, cz + bar, uv, mat)
        for j in range(yoko):
            cy = y0 + (y1 - y0) * (j + 0.5) / yoko
            self.box(x0 - 0.008, x1 + 0.008, cy - bar, cy + bar, z0, z1, uv, mat)

    def frame(self, x0, x1, y0, y1, z0, z1, t, uv, mat=0):
        """中を抜いた四角い枠(井戸枠・玉垣の類)。t = 見込み"""
        self.box(x0, x1, y0, y1, z0, z0 + t, uv, mat)
        self.box(x0, x1, y0, y1, z1 - t, z1, uv, mat)
        self.box(x0, x0 + t, y0, y1, z0 + t, z1 - t, uv, mat)
        self.box(x1 - t, x1, y0, y1, z0 + t, z1 - t, uv, mat)

    def to_object(self, name, mats):
        """Blender へ落とす。

        ⚠ **厚みの向きを反転してから出す。** `export_fbx` の
        `axis_forward='-Z', axis_up='Y'` は Blender +Y を Unity の **−Z** へ写すので、
        論理座標のまま出すと「表」が Unity のローカル −Z に出る
        (README の規約は 表=+Z)。2026-08-25 に番所が街路へ背を向け、
        出格子と唐破風が敷地の内側を向いていたのがこれ。
        面の巻き順と UV も一緒に反転して、法線を外向きに保つ。
        """
        vs = [Vector((p.x, -p.y, p.z)) for p in self.v]
        faces, uvs, mi = [], [], []
        k = 0
        for fi, f in enumerate(self.f):
            n = len(f)
        # ⛔ **巻き順は反転しない。** 反転が1回多くなり、**面が全部裏返る**。
        #   `quad` の軸の入れ替え `(x, z, y)` が鏡映1回、下の Y 反転が2回目。
        #   ここで巻きも戻すと3回=奇数になり、裏面は描画されないので
        #   **閉じた箱なのに中が透けて見える**(2026-08-31 に番所で実測・
        #   背面 4/4・出格子の表 60/60 が裏返っていた。ブックマーク #3 の正体)。
            faces.append(list(f))
            uvs += list(self.uv[k:k + n])
            mi.append(self.mi[fi])
            k += n
        me = bpy.data.meshes.new(name)
        me.from_pydata(vs, [], faces)
        me.update()
        for m in mats:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for j, pg in enumerate(me.polygons):
            pg.material_index = mi[j]
        for j, dd in enumerate(uvl.data):
            dd.uv = uvs[j]
        o = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(o)
        return o



# ---------------------------------------------------------------- マテリアルの借用
def _rect_of(o, mat_name, fallback):
    me = o.data
    uvl = me.uv_layers.active.data
    names = [mm.name if mm else "" for mm in me.materials]
    mi = names.index(mat_name) if mat_name in names else 0
    best, ba = None, -1.0
    for pg in me.polygons:
        if pg.material_index == mi and pg.area > ba:
            ba, best = pg.area, pg
    if best is None:
        return fallback
    us = [uvl[i].uv[0] for i in best.loop_indices]
    vs = [uvl[i].uv[1] for i in best.loop_indices]
    return (min(us), min(vs), max(us), max(vs))


def vk_mat(src, mat_name, fallback):
    o = V.join(V.imp(src), "__src")
    m = bpy.data.materials.get(mat_name)
    rect = _rect_of(o, mat_name, fallback)
    bpy.data.objects.remove(o, do_unlink=True)
    return m, rect


def castle_mat(src, mat_name, fallback):
    """⚠ import しないとマテリアルが存在せず木材に落ちる(2026-08-25 に表門で踏んだ)"""
    keep_m, keep_t = V.MESH, V.TEX
    V.MESH, V.TEX = os.path.join(JC, "Meshes"), os.path.join(JC, "Textures")
    try:
        o = V.join(V.imp(src), "__srcjc")
    except Exception as ex:
        V.MESH, V.TEX = keep_m, keep_t
        print("[fuzokuya] ⚠ 漆喰の借用に失敗: %s" % ex)
        return V.named_material(mat_name), fallback
    V.MESH, V.TEX = keep_m, keep_t
    m = bpy.data.materials.get(mat_name) or V.named_material(mat_name)
    rect = _rect_of(o, mat_name, fallback)
    bpy.data.objects.remove(o, do_unlink=True)
    return m, rect


def palette():
    """(木, 石, 漆喰) の (material, uv) を返す。**必ずこの順でスロットに入れる**"""
    wood, wuv = vk_mat(WOOD_SRC, WOOD_MAT, WOOD_UV_FB)
    stone, suv = vk_mat(STONE_SRC, STONE_MAT, STONE_UV_FB)
    plas, puv = castle_mat(PLASTER_SRC, PLASTER_MAT, WALL_UV_FB)
    return (wood, wuv), (stone, suv), (plas, puv)


WOOD, STONE, PLAS, SHU = 0, 1, 2, 3   # マテリアルスロットの番号


def shu_mat():
    """鳥居の朱。**キットに朱が無い**ので名前だけのスロットを立て、Unity 側の
    `Assets/Edo/Materials/Shu_Torii.mat` を Search&Remap で当てる
    (自作の .mat をプロジェクトに置くのは既存の GateWood/M_Kido と同じ扱い。
     ⛔ 禁じられているのは **Blender 側でキットの材を複製すること**であって、
     キットに無い材を自前の .mat として持つことではない)。"""
    m = V.named_material("Shu_Torii")
    try:
        m.diffuse_color = (0.62, 0.11, 0.06, 1.0)     # Blender のプレビュー用
    except Exception:
        pass
    return m


def _sub(uv, u0, v0, u1, v1):
    """借りた矩形の中をさらに割る。**同じ矩形を全面に貼ると板がベタ塗りになる**"""
    a, b, c, d = uv
    return (a + (c - a) * u0, b + (d - b) * v0, a + (c - a) * u1, b + (d - b) * v1)


def _roof(kind, W, D, name, z, **kw):
    """屋根を1枚焼いて軒先レベル z へ上げる。生成器のピボットは footprint 中心・軒先"""
    o = (R.make_irimoya if kind == "irimoya" else R.make_kirizuma)(W, D, name, **kw)
    o.location = (0.0, 0.0, z)
    bpy.context.view_layer.update()
    V.sel([o])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return o


def _finish(name, m, mats, extra):
    o = m.to_object(name + "_body", mats)
    o = V.join([o] + [e for e in extra if e], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


# ================================================================ 土蔵
def dozo(uk=4, vk=7, name="Matsudaira_Dozo"):
    """土蔵。長手(棟)= vk 間 = ローカル X。据えは yawV(ローカル +X → +v)。
    腰は石の basement、上は白漆喰の大壁。妻に観音扉一対。【確度B=江戸の一般類型】"""
    (wm, wuv), (sm, suv), (pm, puv) = palette()
    W, D = vk * KEN, uk * KEN          # X=桁行(長手) Y=梁間
    BASE, EAVE = 0.40, 4.60            # 基壇高 / 軒高
    hw, hd = W / 2, D / 2
    m = Mesh()
    # 基壇(切石積み)
    m.box(-hw - 0.22, hw + 0.22, 0.0, BASE, -hd - 0.22, hd + 0.22, _sub(suv, 0, 0, 1, .5), STONE)
    # 大壁(白漆喰)。四周を1枚ずつ、UV を面ごとにずらして継ぎ目を目立たせない
    for k, (x0, x1, z0, z1) in enumerate([(-hw, hw, hd - 0.18, hd),
                                          (-hw, hw, -hd, -hd + 0.18)]):
        m.box(x0, x1, BASE, EAVE, z0, z1, _sub(puv, 0, 0, 1, 1), PLAS)
    for k, x in enumerate((-hw, hw - 0.18)):
        m.box(x, x + 0.18, BASE, EAVE, -hd + 0.18, hd - 0.18, _sub(puv, .1, 0, .9, 1), PLAS)
    # 観音扉一対(妻の -X 側)。扉は木、周りに漆喰の額縁
    dw, dh = 1.55, 2.55
    m.box(-hw - 0.10, -hw + 0.02, BASE, BASE + dh + 0.16, -dw / 2 - 0.16, dw / 2 + 0.16,
          _sub(puv, .2, .2, .6, .6), PLAS)
    for s in (-1, 1):
        z0 = 0.0 if s > 0 else -dw / 2
        z1 = dw / 2 if s > 0 else 0.0
        m.box(-hw - 0.14, -hw - 0.04, BASE, BASE + dh, z0, z1, _sub(wuv, .1, 0, .5, 1), WOOD)
    # 窓(妻の +X 側に小窓2つ)。漆喰の額縁の中に竪子を並べる
    for s in (-1, 1):
        zc = s * 0.9
        m.box(hw + 0.01, hw + 0.09, EAVE - 1.97, EAVE - 1.03, zc - 0.46, zc + 0.46,
              _sub(puv, .2, .2, .5, .5), PLAS)
        m.koshi_z(zc - 0.34, zc + 0.34, EAVE - 1.85, EAVE - 1.15, hw + 0.05, hw + 0.13,
                  _sub(wuv, .5, .2, .8, .8), WOOD, pitch=0.10, bar=0.026, yoko=1)
    # 水切り(腰の上に一段。土蔵の顔)
    m.box(-hw - 0.16, hw + 0.16, BASE + 1.55, BASE + 1.70, -hd - 0.16, hd + 0.16,
          _sub(puv, .3, .3, .7, .5), PLAS)
    roof = _roof("kirizuma", W, D, name + "_roof", EAVE, eave=0.75, end=0.45, tsuma=True)
    return _finish(name, m, [wm, sm, pm], [roof])


# ================================================================ 作事小屋
def koya(uk=10, vk=4, name="Matsudaira_Koya"):
    """御作事小屋。長手(棟)= uk 間 = ローカル X。据えは yawU。
    片側の長手を開けた**開き小屋**(材と道具を出し入れする)。【確度B】"""
    (wm, wuv), (sm, suv), (pm, puv) = palette()
    W, D = uk * KEN, vk * KEN
    EAVE, POST = 2.95, 0.16
    hw, hd = W / 2, D / 2
    m = Mesh()
    # 玉石の礎石
    nx = uk + 1
    for i in range(nx):
        x = -hw + W * i / (nx - 1.0)
        for z in (-hd, hd):
            m.box(x - 0.24, x + 0.24, 0.0, 0.22, z - 0.24, z + 0.24, _sub(suv, 0, 0, .5, .5), STONE)
    # 柱(通し)
    for i in range(nx):
        x = -hw + W * i / (nx - 1.0)
        for z in (-hd, hd):
            m.box(x - POST / 2, x + POST / 2, 0.20, EAVE, z - POST / 2, z + POST / 2,
                  _sub(wuv, .2, 0, .35, 1), WOOD)
    # 桁(2本)+ 妻梁
    for z in (-hd, hd):
        m.box(-hw - 0.2, hw + 0.2, EAVE - 0.26, EAVE, z - 0.11, z + 0.11,
              _sub(wuv, .4, .1, .9, .5), WOOD)
    for x in (-hw, hw):
        m.box(x - 0.11, x + 0.11, EAVE - 0.26, EAVE, -hd, hd, _sub(wuv, .4, .5, .9, .9), WOOD)
    # 板壁 — 背面(-Z)と両妻。正面(+Z)は開け放つ
    m.box(-hw, hw, 0.20, EAVE - 0.26, -hd - 0.06, -hd + 0.06, _sub(wuv, 0, 0, 1, 1), WOOD)
    for x in (-hw, hw - 0.12):
        m.box(x, x + 0.12, 0.20, EAVE - 0.26, -hd, hd, _sub(wuv, .1, .1, .9, .9), WOOD)
    # 正面の腰板(膝までの押さえ)
    m.box(-hw, hw, 0.20, 0.85, hd - 0.06, hd + 0.06, _sub(wuv, 0, .2, 1, .6), WOOD)
    # 妻壁 — **漆喰にしない**(作事の小屋なので板張り)。屋根の tsuma は切ってここで張る
    # 大棟の高さは生成器と同じ式で出す(合わないと妻が屋根から出る/透ける)
    # ⚠ 三角の底辺は**軒先の線**(z=±(hd+0.80)・y=EAVE)に置く。壁幅で切ると
    #   軒先へ行くほど屋根との間が開き、実際に 0.73m の隙間が空いた(2026-08-25)。
    rise = (D / 2 + 0.80) * R.RATIO
    ze = hd + 0.80
    for x, t in ((-hw, -0.07), (hw, 0.07)):
        m.box(min(x, x + t), max(x, x + t), EAVE - 0.34, EAVE, -ze, ze,
              _sub(wuv, .1, .1, .9, .3), WOOD)
        for face in (0.0, t):
            m.tri([(x + face, EAVE, -ze), (x + face, EAVE, ze),
                   (x + face, EAVE + rise, 0.0)], _sub(wuv, .1, .1, .9, .9), WOOD)
    roof = _roof("kirizuma", W, D, name + "_roof", EAVE, eave=0.80, end=0.50, tsuma=False)
    return _finish(name, m, [wm, sm, pm], [roof])


# ================================================================ 数寄屋(御茶屋)
def sukiya(ken=2.5, name="Matsudaira_Sukiya"):
    """四畳半+水屋の数寄屋。**宝形(方形)の柿葺**。瓦は載せない — 数寄屋は瓦葺きにしない。
    縁側を +Z 側に一間分。躙口は +X 側。【確度B=一般類型。当家の茶屋の姿は未確認】"""
    (wm, wuv), (sm, suv), (pm, puv) = palette()
    S = ken * KEN                       # 4.545
    hs = S / 2
    FLOOR, EAVE = 0.46, 2.30
    OV = 1.00                           # 軒の出。**縁側の先(半間)まで掛ける**
    m = Mesh()
    # 玉石+土台
    for x in (-hs, 0.0, hs):
        for z in (-hs, 0.0, hs):
            m.box(x - 0.22, x + 0.22, 0.0, 0.24, z - 0.22, z + 0.22, _sub(suv, 0, 0, .5, .5), STONE)
    m.box(-hs, hs, 0.24, FLOOR, -hs, hs, _sub(wuv, .3, 0, .6, .4), WOOD)
    # 土壁(-Z と両側面)。+Z は障子
    m.box(-hs, hs, FLOOR, EAVE, -hs, -hs + 0.13, _sub(puv, 0, 0, 1, 1), PLAS)
    for x in (-hs, hs - 0.13):
        m.box(x, x + 0.13, FLOOR, EAVE, -hs, hs, _sub(puv, .1, .1, .9, .9), PLAS)
    # 障子(+Z の全面)。**板を1枚貼らない** — 紙は漆喰の白面、桟は木を実体で組む
    m.box(-hs + 0.13, hs - 0.13, FLOOR + 0.30, EAVE - 0.12, hs - 0.035, hs - 0.015,
          _sub(puv, .3, .3, .7, .7), PLAS)                       # 紙
    m.box(-hs + 0.13, hs - 0.13, FLOOR, FLOOR + 0.30, hs - 0.05, hs, _sub(wuv, .3, 0, .5, .3), WOOD)  # 腰板
    for i in range(1, 8):                                        # 竪桟
        x = -hs + 0.13 + (S - 0.26) * i / 8.0
        m.box(x - 0.018, x + 0.018, FLOOR + 0.30, EAVE - 0.12, hs - 0.05, hs,
              _sub(wuv, .2, 0, .3, 1), WOOD)
    for j in range(1, 5):                                        # 横桟
        y = FLOOR + 0.30 + (EAVE - 0.42) * j / 5.0
        m.box(-hs + 0.13, hs - 0.13, y - 0.018, y + 0.018, hs - 0.05, hs,
              _sub(wuv, .4, .2, .9, .4), WOOD)
    for (x0, x1, y0, y1) in [(-hs + 0.13, hs - 0.13, EAVE - 0.12, EAVE),
                             (-hs + 0.13, -hs + 0.19, FLOOR, EAVE),
                             (hs - 0.19, hs - 0.13, FLOOR, EAVE)]:  # 鴨居・方立
        m.box(x0, x1, y0, y1, hs - 0.06, hs + 0.01, _sub(wuv, .5, .3, .8, .6), WOOD)
    # 柱4本
    for x in (-hs, hs - 0.13):
        for z in (-hs, hs - 0.13):
            m.box(x, x + 0.13, FLOOR, EAVE + 0.10, z, z + 0.13, _sub(wuv, .25, 0, .4, 1), WOOD)
    # 縁側(+Z 側・半間)+ 濡縁の束
    m.box(-hs, hs, FLOOR - 0.06, FLOOR, hs, hs + KEN / 2, _sub(wuv, 0, .3, 1, .7), WOOD)
    for x in (-hs + 0.2, 0.0, hs - 0.2):
        m.box(x - 0.07, x + 0.07, 0.0, FLOOR - 0.06, hs + KEN / 2 - 0.14, hs + KEN / 2,
              _sub(wuv, .3, 0, .4, 1), WOOD)
    # 躙口(+X の壁を切って小さな板戸)
    m.box(hs - 0.16, hs - 0.02, FLOOR + 0.10, FLOOR + 0.76, -0.36, 0.36,
          _sub(wuv, .5, .2, .8, .6), WOOD)
    # ---- 宝形の柿葺(4枚の三角。瓦は使わない)
    ap = EAVE + 1.98                    # 頂点(勾配 6寸強。柿葺は瓦より急に葺く)
    e0, e1 = -hs - OV, hs + OV
    ez = EAVE + 0.06
    for (a, b) in [((e0, e0), (e1, e0)), ((e1, e0), (e1, e1)),
                   ((e1, e1), (e0, e1)), ((e0, e1), (e0, e0))]:
        m.tri([(a[0], ez, a[1]), (b[0], ez, b[1]), (0.0, ap, 0.0)], _sub(wuv, .05, .05, .95, .95), WOOD)
        m.tri([(b[0], ez - 0.05, b[1]), (a[0], ez - 0.05, a[1]), (0.0, ap - 0.05, 0.0)],
              _sub(wuv, .05, .05, .95, .95), WOOD)
    # 軒付(縁を厚く見せる)
    for (x0, x1, z0, z1) in [(e0, e1, e0, e0 + 0.10), (e0, e1, e1 - 0.10, e1),
                             (e0, e0 + 0.10, e0, e1), (e1 - 0.10, e1, e0, e1)]:
        m.box(x0, x1, ez - 0.11, ez, z0, z1, _sub(wuv, .4, .4, .7, .6), WOOD)
    # 露盤(頂部の押さえ)
    m.box(-0.16, 0.16, ap - 0.06, ap + 0.16, -0.16, 0.16, _sub(wuv, .5, .5, .7, .7), WOOD)
    return _finish(name, m, [wm, sm, pm], [])


# ================================================================ 稲荷社
def inari(name="Matsudaira_Inari"):
    """邸内稲荷。**明神鳥居 + 一間社流造の小祠 + 台石**を2間角に納める。
    鳥居は朱塗り(スロット `Shu_Torii` → Unity の Assets/Edo/Materials/Shu_Torii.mat)、
    祠は素木。【確度B=邸内稲荷は常だが、当家の祭神・社殿形式は未確認】"""
    (wm, wuv), (sm, suv), (pm, puv) = palette()
    shu = shu_mat()
    SUV = (0.15, 0.15, 0.85, 0.85)   # 無地の材なので UV は中央の一枚で足りる
    m = Mesh()
    # ---- 鳥居(明神系)。**祠の正面(+Z)側に立てる**
    #      ⚠ 2026-08-25 是正: 旧版は鳥居を -Z、祠の扉も +Z に置いたので、
    #        鳥居をくぐると祠の**背面**に出ていた。
    TZ = 1.75
    tw, th = 1.62, 2.30                 # 柱の内法・柱高
    pr = 0.085                          # 柱の見付の半分(0.17角 ≒ 内法の 1/10)
    for s in (-1, 1):
        x = s * tw / 2
        m.box(x - pr, x + pr, 0.0, th, TZ - pr, TZ + pr, SUV, SHU)
        m.box(x - 0.16, x + 0.16, 0.0, 0.16, TZ - 0.16, TZ + 0.16, _sub(suv, 0, 0, .4, .4), STONE)
    # 貫(柱の外へ出る)
    m.box(-tw / 2 - 0.26, tw / 2 + 0.26, th - 0.62, th - 0.48, TZ - 0.07, TZ + 0.07, SUV, SHU)
    # 島木 + 笠木 — **2本まとめて同じ反りに乗せる**。
    # ⚠ 2026-08-25 是正: 旧版は島木を水平の箱、笠木だけを反らせたので、
    #   両者の間が端へ行くほど楔形に開いていた。反りは島木から始まる。
    n = 12
    KW = tw / 2 + 0.44                   # 笠木の半長(柱の外への出)
    def sori(t):
        return 0.15 * ((2 * t - 1) ** 2)  # 中央 0・両端 0.15 で上がる
    for i in range(n):
        t0, t1 = i / float(n), (i + 1) / float(n)
        x0, x1 = -KW + 2 * KW * t0, -KW + 2 * KW * t1
        r0, r1 = sori(t0), sori(t1)
        # 島木(下段・幅狭)
        for zz, sgn in ((TZ + 0.13, 1), (TZ - 0.13, -1)):
            m.quad([(x0, th + r0, zz), (x1, th + r1, zz),
                    (x1, th + 0.15 + r1, zz), (x0, th + 0.15 + r0, zz)][::sgn],
                   SUV, SHU)
        # 笠木(上段・幅広)
        for zz, sgn in ((TZ + 0.17, 1), (TZ - 0.17, -1)):
            m.quad([(x0, th + 0.15 + r0, zz), (x1, th + 0.15 + r1, zz),
                    (x1, th + 0.31 + r1, zz), (x0, th + 0.31 + r0, zz)][::sgn],
                   SUV, SHU)
        # 天端と小口の底
        m.quad([(x0, th + 0.31 + r0, TZ - 0.17), (x1, th + 0.31 + r1, TZ - 0.17),
                (x1, th + 0.31 + r1, TZ + 0.17), (x0, th + 0.31 + r0, TZ + 0.17)],
               SUV, SHU)
        m.quad([(x1, th + r1, TZ - 0.13), (x0, th + r0, TZ - 0.13),
                (x0, th + r0, TZ + 0.13), (x1, th + r1, TZ + 0.13)],
               SUV, SHU)
    # 額束
    m.box(-0.11, 0.11, th - 0.48, th, TZ - 0.09, TZ + 0.09, SUV, SHU)
    # ---- 台石(基壇)。祠は鳥居の奥(-Z)に据え、扉を +Z = 鳥居側へ向ける
    SZ = -0.62
    m.box(-0.95, 0.95, 0.0, 0.42, SZ - 0.80, SZ + 0.80, _sub(suv, 0, 0, 1, .5), STONE)
    # ---- 一間社流造の小祠。前へ長く流れる屋根が特徴
    bw, bd, bh = 0.95, 0.72, 1.05
    m.box(-bw / 2, bw / 2, 0.42, 0.42 + bh, SZ - bd / 2, SZ + bd / 2, _sub(wuv, 0, 0, 1, 1), WOOD)
    # 扉(+Z 側)
    m.box(-0.28, 0.28, 0.56, 0.56 + 0.72, SZ + bd / 2, SZ + bd / 2 + 0.04,
          _sub(wuv, .55, .2, .85, .8), WOOD)
    # 縁と階(きざはし)
    m.box(-bw / 2 - 0.12, bw / 2 + 0.12, 0.42 + bh * 0.0, 0.50, SZ - bd / 2 - 0.12, SZ + bd / 2 + 0.30,
          _sub(wuv, .2, .3, .8, .5), WOOD)
    for i in range(3):
        y = 0.14 + i * 0.10
        m.box(-0.22, 0.22, y, y + 0.06, SZ + bd / 2 + 0.30 - i * 0.11, SZ + bd / 2 + 0.41 - i * 0.11,
              _sub(wuv, .3, .3, .5, .5), WOOD)
    # 屋根 — 棟から後ろは短く、前は縁の先まで長く流れる(流造)
    ridge_y = 0.42 + bh + 0.46
    zb = SZ - bd / 2 - 0.26                      # 背面の軒
    zf = SZ + bd / 2 + 0.56                      # 前面の軒(長い)
    zr = SZ - bd / 2 + 0.16                      # 棟の位置(後ろ寄り)
    # ⚠ 屋根は表裏とも張る。一枚面のままだと Unity の背面カリングで軒下から空が抜ける
    xh = bw / 2 + 0.26
    yb, yf = 0.42 + bh + 0.10, 0.42 + bh * 0.62
    for d in (0.0, -0.07):              # 表 / 裏(厚みぶん下げて逆巻き)
        back = [(-xh, ridge_y + d, zr), (xh, ridge_y + d, zr), (xh, yb + d, zb), (-xh, yb + d, zb)]
        front = [(xh, ridge_y + d, zr), (-xh, ridge_y + d, zr), (-xh, yf + d, zf), (xh, yf + d, zf)]
        if d < 0:
            back, front = back[::-1], front[::-1]
        m.quad(back, _sub(wuv, .1, .1, .9, .4), WOOD)
        m.quad(front, _sub(wuv, .1, .5, .9, .9), WOOD)
    # 破風(両妻の小口を塞ぐ)
    for sx in (-xh, xh):
        m.tri([(sx, ridge_y, zr), (sx, yb, zb), (sx, yb, zr)], _sub(wuv, .6, .1, .8, .3), WOOD)
        m.tri([(sx, ridge_y, zr), (sx, yf, zf), (sx, yf, zr)], _sub(wuv, .6, .1, .8, .3), WOOD)
    # 棟木 + 鰹木3本 + 千木
    m.box(-bw / 2 - 0.30, bw / 2 + 0.30, ridge_y, ridge_y + 0.11, zr - 0.09, zr + 0.09,
          _sub(wuv, .6, .6, .9, .8), WOOD)
    for i in (-1, 0, 1):
        m.box(i * 0.28 - 0.055, i * 0.28 + 0.055, ridge_y + 0.11, ridge_y + 0.22,
              zr - 0.13, zr + 0.13, _sub(wuv, .7, .6, .8, .7), WOOD)
    for sx in (-1, 1):
        m.box(sx * (bw / 2 + 0.24), sx * (bw / 2 + 0.30), ridge_y - 0.10, ridge_y + 0.46,
              zr - 0.06, zr + 0.06, _sub(wuv, .6, .2, .7, .5), WOOD)
    return _finish(name, m, [wm, sm, pm, shu], [])


# ================================================================ 石井戸枠
def ido(name="Matsudaira_Ido"):
    """石井戸枠 + 釣瓶の桁。枠は切石を四方に組んだ角井戸。
    ⚠ 指図 wells.Ido_Oku の「慶長13年戊申銘の石井戸枠」は**議長公邸に現存する実物**だが、
      銘や意匠は実見していないので、ここで作るのは**同型の角井戸枠**である。【確度B】"""
    (wm, wuv), (sm, suv), (pm, puv) = palette()
    m = Mesh()
    OUT_W, IN_W, H = 1.30, 0.82, 0.62
    t = (OUT_W - IN_W) / 2
    # 据石(地面に馴染ませる敷き)
    m.box(-0.95, 0.95, -0.06, 0.10, -0.95, 0.95, _sub(suv, 0, 0, 1, .5), STONE)
    # 井戸枠(中を抜いた角枠)
    m.frame(-OUT_W / 2, OUT_W / 2, 0.10, 0.10 + H, -OUT_W / 2, OUT_W / 2, t,
            _sub(suv, .1, .5, .9, .95), STONE)
    # 蓋の板2枚(半分だけ掛ける)
    for s in (0, 1):
        z0 = -IN_W / 2 + s * IN_W / 2
        m.box(-IN_W / 2, IN_W / 2, 0.10 + H - 0.05, 0.10 + H + 0.01, z0, z0 + IN_W / 2 - 0.02,
              _sub(wuv, .1, .2 + s * .3, .9, .45 + s * .3), WOOD)
        break
    # 桁(2本柱+梁)。釣瓶を吊る
    ph, px = 2.15, 0.78
    for s in (-1, 1):
        m.box(s * px - 0.07, s * px + 0.07, 0.0, ph, -0.07, 0.07, _sub(wuv, .2, 0, .35, 1), WOOD)
    m.box(-px - 0.16, px + 0.16, ph - 0.14, ph, -0.08, 0.08, _sub(wuv, .4, .2, .9, .5), WOOD)
    # 方杖
    for s in (-1, 1):
        m.box(s * px - 0.05, s * px + 0.05, ph - 0.42, ph - 0.14, -0.05, 0.05,
              _sub(wuv, .3, .1, .4, .4), WOOD)
    return _finish(name, m, [wm, sm, pm], [])


# ================================================================ 隅櫓
def yagura(ken=3, name="Matsudaira_SumiYagura"):
    """二重の隅櫓。下層 ken 間角・上層は一回り小さく、腰屋根と入母屋を架ける。
    腰は下見板張り、上は白漆喰の大壁に格子窓。
    ⚠ **当家に櫓があった典拠は無い【確度?】** — 指図 yagura._ のとおり。姿も一般形に留める。"""
    (wm, wuv), (sm, suv), (pm, puv) = palette()
    S1 = ken * KEN                       # 下層 5.454
    S2 = S1 - 1.10                       # 上層(一回り小さい)
    H1, H2 = 3.40, 2.55                  # 各層の壁高
    SKIRT = 0.34                         # 腰屋根の軒先から上層の足元まで
    h1, h2 = S1 / 2, S2 / 2
    m = Mesh()
    # ---- 下層。腰(下見板)+ 上(漆喰)
    KOSHI = 1.25
    for (x0, x1, z0, z1) in [(-h1, h1, h1 - 0.20, h1), (-h1, h1, -h1, -h1 + 0.20),
                             (-h1, -h1 + 0.20, -h1 + 0.20, h1 - 0.20),
                             (h1 - 0.20, h1, -h1 + 0.20, h1 - 0.20)]:
        m.box(x0, x1, 0.0, KOSHI, z0, z1, _sub(wuv, 0, 0, 1, .45), WOOD)
        m.box(x0, x1, KOSHI, H1, z0, z1, _sub(puv, 0, 0, 1, 1), PLAS)
    # 狭間(矢狭間・鉄砲狭間)を四周に
    for s in (-1, 1):
        for t in (-1.4, 0.0, 1.4):
            m.box(s * h1, s * h1 + s * 0.04, KOSHI + 0.75, KOSHI + 1.15, t - 0.14, t + 0.14,
                  _sub(wuv, .9, .1, .97, .5), WOOD)
            m.box(t - 0.14, t + 0.14, KOSHI + 0.75, KOSHI + 1.15, s * h1, s * h1 + s * 0.04,
                  _sub(wuv, .9, .1, .97, .5), WOOD)
    # ---- 上層
    z2 = H1 + SKIRT
    for (x0, x1, z0, z1) in [(-h2, h2, h2 - 0.18, h2), (-h2, h2, -h2, -h2 + 0.18),
                             (-h2, -h2 + 0.18, -h2 + 0.18, h2 - 0.18),
                             (h2 - 0.18, h2, -h2 + 0.18, h2 - 0.18)]:
        m.box(x0, x1, z2, z2 + H2, z0, z1, _sub(puv, .05, .05, .95, .95), PLAS)
    # 格子窓(四周に1つずつ)。**竪子を実体で並べる** — 板1枚だと茶色の面になる
    for s in (-1, 1):
        # 額縁(漆喰の見込み)
        m.box(s * h2 - s * 0.01, s * h2 + s * 0.06, z2 + 0.50, z2 + 1.84, -0.97, 0.97,
              _sub(puv, .2, .2, .5, .5), PLAS)
        m.box(-0.97, 0.97, z2 + 0.50, z2 + 1.84, s * h2 - s * 0.01, s * h2 + s * 0.06,
              _sub(puv, .2, .2, .5, .5), PLAS)
        a, b = sorted((s * h2 + s * 0.02, s * h2 + s * 0.09))
        m.koshi_z(-0.85, 0.85, z2 + 0.62, z2 + 1.72, a, b,
                  _sub(wuv, .75, .15, .95, .85), WOOD, pitch=0.155, bar=0.038, yoko=2)
        m.koshi(-0.85, 0.85, z2 + 0.62, z2 + 1.72, a, b,
                _sub(wuv, .75, .15, .95, .85), WOOD, pitch=0.155, bar=0.038, yoko=2)
    roofs = [_roof("irimoya", S1, S1, name + "_koshi", H1, eave=0.80, gable_frac=0.16),
             _roof("irimoya", S2, S2, name + "_top", z2 + H2, eave=0.88, gable_frac=0.45)]
    return _finish(name, m, [wm, sm, pm], roofs)


# ================================================================
PARTS = {
    "dozo": (dozo, "Matsudaira_Dozo"),
    "koya": (koya, "Matsudaira_Koya"),
    "sukiya": (sukiya, "Matsudaira_Sukiya"),
    "inari": (inari, "Matsudaira_Inari"),
    "ido": (ido, "Matsudaira_Ido"),
    "yagura": (yagura, "Matsudaira_SumiYagura"),
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or list(PARTS.keys())
    for key in want:
        if key not in PARTS:
            print("[fuzokuya] ⚠ 知らない部材: %s (%s)" % (key, "/".join(PARTS)))
            continue
        fn, name = PARTS[key]
        V.reset()
        o = fn(name=name)
        mn, mx = V.bbox([o])
        print("[fuzokuya] %-22s W(X)=%6.3f  D(Z)=%6.3f  H(Y)=%6.3f  底=%.3f"
              % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, mn.z))
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[fuzokuya] 書き出し " + os.path.join(OUT, name + ".fbx"))
        if "--render" in argv:
            V.hook_textures()
            bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.02))
            # 画角は実寸から出す(部材ごとに手で決めると必ずどれかが枠から溢れる)
            r = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
            # 表が見える側から。⚠ to_object で厚みを反転したので、
            # **部材の表は Blender の −Y**(= Unity のローカル +Z)にある
            V.studio((-r * 1.35, -r * 1.85, r * 1.05), (0.0, 0.0, (mx.z - mn.z) * 0.45),
                     res=(1400, 950))
            V.render("/tmp/fuzokuya_%s.png" % key)


main()
