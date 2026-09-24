"""⚠⚠ **試作(プロトタイプ)** — 山王社の前庭の縁の土留め、4案の見比べの絵だけを焼く。
⛔ FBX は書き出さない・EdoAssets.cs に登録しない。施主が案を選んだら本番のモジュールとして起こし直す。

    blender --background --python Tools/Blender/proto_sanno_dodome.py -- [now|a|b|c|all] [--out=<dir>] [--seed=N]
    blender --background --python Tools/Blender/proto_sanno_dodome.py -- a b --low=1   # 低い区間 0.0→0.9(a_low / b_low)

【区間(4案共通)】長さ 14m の直線。下の地面(前庭)は水平 z=0。
  上の地面の見付 H(x) は左端 0.3m → 右端 1.7m になだらかに上がる(前庭の西の縁の断面に倣う)。
  ⚠ 画の外で小口が見えないよう、上下の地面と壁は両端に 3m ずつ延ばしてある(石の数は 14m 内だけ数える)。

【軸(Blender Z-up)】X = 走り(−7 … +7) / Y = 奥(−Y が前庭・見る側) / Z = 上。壁の面は y = 0.3·z(3分勾配)。

【案】
  now … 城のキットの模し。2.4m 級の切石の箱を並べ、天端を 0.6m 刻みの階段に折る(材 `stone wall` を kit の UV で)
  a   … 野面の乱積み。石の面 25〜60cm・控え 45〜75cm。千鳥の Voronoi 割りで目地が縦に通らない。
        天端は石の頭で ±8cm、地面の傾きに沿って斜めに流す。上に芝を 10〜20cm 被せて土を丸める
  b   … 見付 ≥0.6 は a と同じ乱積み / 0.25〜0.6 は芝の法(1:1.5)の裾に根石1段 / <0.25 は芝だけ。
        移り目 1.5m で石積みの天端を根石の高さまで下げ、上の差分を法で受ける(石積みが土手へ沈む)
  c   … 玉石の谷積み。面 15〜30cm の丸石を ±40° で交互に斜めに据える。天端は頭で ±5cm

【材(検証レンダ用の結線。⛔ 新規の .mat ではない)】
  石 = `Kirishi`(Assets/Edo/Materials/Sanno・暖かい灰 (134,128,118))をボックス投影 + 石ごとの色調ゆらぎ
  城 = `stone wall`(Japanese Castle)/ 芝 = T_FJG_Ground_Grass_02 / 土 = T_FJG_Ground_Soil_01
  ⚠ 本番では UV を焼く(ボックス投影は試作だけの近道)。
"""
import bpy, bmesh, sys, os, math, random
import mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WHICH = [a for a in ARGS if not a.startswith("--")] or ["all"]
OPT = dict(a[2:].split("=", 1) for a in ARGS if a.startswith("--") and "=" in a)
OUT = OPT.get("out", "/private/tmp/claude-501/-Users-toshio-project-edo-unity/"
                     "48127409-8224-4eeb-b6ef-d69c5d798ace/scratchpad/dodome")
SEED = int(OPT.get("seed", "7"))

RUN = 14.0
X0, X1 = -RUN / 2, RUN / 2
EXT = 3.0                 # 画の外へ延ばす長さ
BATTER = 0.3              # 3分
ZBOT = -0.16              # 石の根入れ
ASSET = os.path.join(V.REPO, "Assets")
TEX_KIRISHI = os.path.join(ASSET, "Edo/Materials/Sanno/T_Kirishi_Albedo.png")
TEX_CASTLE = os.path.join(ASSET, "Japanese Castle/Textures/stone wall_AlbedoTransparency.png")
TEX_CASTLE_N = os.path.join(ASSET, "Japanese Castle/Textures/stone wall_Normal.png")
TEX_GRASS = os.path.join(ASSET, "Waldemarst/FreeJapaneseGarden/Textures/Terrain/Ground_Grass_02/T_FJG_Ground_Grass_02_Albedo.png")
TEX_SOIL = os.path.join(ASSET, "Waldemarst/FreeJapaneseGarden/Textures/Terrain/Ground_Soil_01/T_FJG_Ground_Soil_01_Albedo.png")


# ------------------------------------------------------------------ 断面
LOW = OPT.get("low") == "1"
# 断面: 既定 = 左端 0.3 → 右端 1.7 / `--low=1` = 左端 0.0 → 右端 0.9(A と B の違いが出る低い区間)
H_L, H_R = (0.0, 0.9) if LOW else (0.3, 1.7)
SUFFIX = "_low" if LOW else ""


def H(x):
    """上の地面の見付。左端 H_L → 右端 H_R(なだらか=下に凸の緩い放物線)。区間外は一定。"""
    t = min(max((x - X0) / RUN, 0.0), 1.0)
    return H_L + (H_R - H_L) * (0.55 * t + 0.45 * t * t)


def x_at_H(h):
    lo, hi = X0, X1
    for _ in range(60):
        m = (lo + hi) / 2
        if H(m) < h:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def smooth(e0, e1, v):
    t = min(max((v - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def cover(x):
    """芝の被り 10〜20cm(走りに沿ってゆっくり揺らす)"""
    return 0.15 + 0.05 * math.sin(x * 0.9 + 1.3) * math.cos(x * 0.37)


X6 = x_at_H(0.6)          # b: 見付 0.6 の位置
LT = 1.5                  # b: 石積み → 根石の移り目の長さ


def root_top(h):
    """b の根石の頭の高さ。見付 0.25 未満では地中へ沈めて消す"""
    return 0.22 * smooth(0.18, 0.25, h) - 0.12 * (1 - smooth(0.18, 0.25, h))


def Hw(case, x):
    """石の頭の並ぶ線(天端の芯)。この上は芝の肩か法が受ける"""
    h = H(x)
    if case == "a":
        # 全長を石積み。見付 0.2 未満は根石1段で打ち切る(頭は前庭から 0.12 は出す)
        if h < 0.2:
            # 根石1段。見付がほぼ 0 になる所(0.08→0.03)で地中へ沈めて打ち切る
            k = smooth(0.03, 0.08, h)
            return (0.12 + 0.4 * h) * k - 0.25 * (1 - k)
        return h - cover(x) * smooth(0.2, 0.6, h)
    if case == "c":
        return h - cover(x)
    if case == "b":
        full = h - cover(x)
        rt = min(root_top(h), h - 0.06)
        f = smooth(X6, X6 + LT, x)
        return rt + (full - rt) * f
    raise ValueError(case)


def rootzone(case, x):
    return (case == "b" and x < X6 + LT * 0.5) or (case == "a" and H(x) < 0.3)


def width_range(case, x):
    if rootzone(case, x):
        return (0.30, 0.45)
    return (0.25, 0.60)


def lip_of(case, x):
    return 0.08 + 0.17 * smooth(X6, X6 + LT, x) if case == "b" else 0.25


def shoulder(case, x):
    """芝の肩の始まり (z0) と、肩・法の奥行き(= 石の面を前へ出す量)"""
    hw, h = Hw(case, x), H(x)
    z0 = min(max(hw + 0.02, 0.0), h)
    rise = max(h - z0, 0.0)
    lh = min(rise, lip_of(case, x))
    lr = 0.10 + 0.35 * lh
    return z0, lr + 1.5 * (rise - lh)


def Yoff(case, x):
    """b: 芝の法は見付に応じて外(前庭側)へ張り出す ⇒ 法肩を壁の天端の線に留め、
    根石と法尻を 1.5×丈 だけ前へ出す。乱積みの区間では 0。"""
    if case != "b":
        return 0.0
    return -shoulder(case, x)[1] * (1 - smooth(X6, X6 + LT, x))


# ------------------------------------------------------------------ 材
def _img(path, nonc=False):
    im = bpy.data.images.load(path, check_existing=True)
    if nonc:
        im.colorspace_settings.name = 'Non-Color'
    return im


def mat_stone():
    m = bpy.data.materials.get("Kirishi")
    if m:
        return m
    m = bpy.data.materials.new("Kirishi")
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]
    b.inputs['Roughness'].default_value = 0.92
    tc = N.new('ShaderNodeTexCoord')
    at = N.new('ShaderNodeAttribute'); at.attribute_name = "ofs"; at.attribute_type = 'GEOMETRY'
    add = N.new('ShaderNodeVectorMath'); add.operation = 'ADD'
    L.new(tc.outputs['Object'], add.inputs[0]); L.new(at.outputs['Vector'], add.inputs[1])
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / 0.44,) * 3
    L.new(add.outputs[0], mp.inputs['Vector'])
    ti = N.new('ShaderNodeTexImage'); ti.image = _img(TEX_KIRISHI)
    ti.projection = 'BOX'; ti.projection_blend = 0.35
    L.new(mp.outputs['Vector'], ti.inputs['Vector'])
    # 石ごとの色調(tone 0..1)と、低周波の汚れ・地衣の斑
    tn = N.new('ShaderNodeAttribute'); tn.attribute_name = "tone"; tn.attribute_type = 'GEOMETRY'
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.50, 0.47, 0.42, 1)
    ramp.color_ramp.elements[1].color = (0.92, 0.88, 0.80, 1)
    L.new(tn.outputs['Fac'], ramp.inputs['Fac'])
    mul = N.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs['Fac'].default_value = 1.0
    L.new(ti.outputs['Color'], mul.inputs[1]); L.new(ramp.outputs['Color'], mul.inputs[2])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0
    nz.inputs['Detail'].default_value = 6.0
    L.new(add.outputs[0], nz.inputs['Vector'])
    r2 = N.new('ShaderNodeValToRGB')
    r2.color_ramp.elements[0].position = 0.45; r2.color_ramp.elements[0].color = (1, 1, 1, 1)
    r2.color_ramp.elements[1].position = 0.75; r2.color_ramp.elements[1].color = (0.55, 0.56, 0.47, 1)
    L.new(nz.outputs['Fac'], r2.inputs['Fac'])
    mul2 = N.new('ShaderNodeMixRGB'); mul2.blend_type = 'MULTIPLY'; mul2.inputs['Fac'].default_value = 1.0
    L.new(mul.outputs['Color'], mul2.inputs[1]); L.new(r2.outputs['Color'], mul2.inputs[2])
    # 目地の奥を暗く(AO)
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.12
    mix = N.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'
    L.new(ao.outputs['AO'], mix.inputs['Fac'])
    mix.inputs[1].default_value = (0.35, 0.33, 0.30, 1)
    L.new(mul2.outputs['Color'], mix.inputs[2])
    # AO=1 → 石の色そのまま / AO=0 → 暗い
    lerp = N.new('ShaderNodeMixRGB'); lerp.blend_type = 'MIX'
    L.new(ao.outputs['AO'], lerp.inputs['Fac'])
    mdark = N.new('ShaderNodeMixRGB'); mdark.blend_type = 'MULTIPLY'; mdark.inputs['Fac'].default_value = 1
    L.new(mul2.outputs['Color'], mdark.inputs[1]); mdark.inputs[2].default_value = (0.45, 0.43, 0.40, 1)
    L.new(mdark.outputs['Color'], lerp.inputs[1]); L.new(mul2.outputs['Color'], lerp.inputs[2])
    L.new(lerp.outputs['Color'], b.inputs['Base Color'])
    # 割肌の細かい凹凸
    nb = N.new('ShaderNodeTexNoise'); nb.inputs['Scale'].default_value = 28.0
    nb.inputs['Detail'].default_value = 8.0
    L.new(add.outputs[0], nb.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35
    bump.inputs['Distance'].default_value = 0.01
    L.new(nb.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_castle():
    m = bpy.data.materials.get("stone wall")
    if m:
        return m
    m = bpy.data.materials.new("stone wall")
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]; b.inputs['Roughness'].default_value = 0.8
    ti = N.new('ShaderNodeTexImage'); ti.image = _img(TEX_CASTLE)
    L.new(ti.outputs['Color'], b.inputs['Base Color'])
    ni = N.new('ShaderNodeTexImage'); ni.image = _img(TEX_CASTLE_N, True)
    nm = N.new('ShaderNodeNormalMap')
    L.new(ni.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def _ground_mat(name, tex, tint, scale, soil_mix=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]; b.inputs['Roughness'].default_value = 0.95
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / scale,) * 3
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    ti = N.new('ShaderNodeTexImage'); ti.image = _img(tex); ti.projection = 'BOX'; ti.projection_blend = 0.4
    L.new(mp.outputs['Vector'], ti.inputs['Vector'])
    mul = N.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs['Fac'].default_value = 1
    L.new(ti.outputs['Color'], mul.inputs[1]); mul.inputs[2].default_value = tint
    out = mul
    if soil_mix:
        t2 = N.new('ShaderNodeTexImage'); t2.image = _img(soil_mix[0]); t2.projection = 'BOX'
        L.new(mp.outputs['Vector'], t2.inputs['Vector'])
        m2 = N.new('ShaderNodeMixRGB'); m2.blend_type = 'MULTIPLY'; m2.inputs['Fac'].default_value = 1
        L.new(t2.outputs['Color'], m2.inputs[1]); m2.inputs[2].default_value = soil_mix[1]
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.35
        nz.inputs['Detail'].default_value = 4
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = N.new('ShaderNodeValToRGB')
        rp.color_ramp.elements[0].position = 0.50; rp.color_ramp.elements[1].position = 0.66
        L.new(nz.outputs['Fac'], rp.inputs['Fac'])
        mx = N.new('ShaderNodeMixRGB'); mx.blend_type = 'MIX'
        L.new(rp.outputs['Color'], mx.inputs['Fac'])
        # Fac=0 → 草 / Fac=1 → 土(⛔ 逆に繋いで前庭が一面の赤土になった)
        L.new(mul.outputs['Color'], mx.inputs[1]); L.new(m2.outputs['Color'], mx.inputs[2])
        out = mx
    L.new(out.outputs['Color'], b.inputs['Base Color'])
    nb = N.new('ShaderNodeTexNoise'); nb.inputs['Scale'].default_value = 40
    L.new(tc.outputs['Object'], nb.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25
    L.new(nb.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_grass():   # 落ち着いた夏の芝
    return _ground_mat("Grass", TEX_GRASS, (0.60, 0.66, 0.50, 1), 1.6)


def mat_yard():    # 前庭の土と草
    return _ground_mat("Yard", TEX_GRASS, (0.66, 0.70, 0.55, 1), 1.6,
                       soil_mix=(TEX_SOIL, (0.72, 0.70, 0.68, 1)))


def mat_soil():
    return _ground_mat("Soil", TEX_SOIL, (0.45, 0.40, 0.34, 1), 1.0)


# ------------------------------------------------------------------ 形の道具
def new_obj(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def grid_obj(name, xs, n_v, fn, mat, smooth_shade=True):
    """xs × v(0..1) の格子。fn(x, v) -> (x, y, z)"""
    bm = bmesh.new()
    rows = []
    for x in xs:
        rows.append([bm.verts.new(fn(x, j / (n_v - 1))) for j in range(n_v)])
    for i in range(len(xs) - 1):
        for j in range(n_v - 1):
            f = bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
            f.smooth = smooth_shade
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, bm, [mat])


def xs_range(step=0.08):
    n = int(round((RUN + 2 * EXT) / step))
    return [X0 - EXT + i * step for i in range(n + 1)]


def yard():
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(-25, -30, 0), (25, -30, 0), (25, 1.2, 0), (-25, 1.2, 0)]]
    bm.faces.new(vs)
    return new_obj("Yard", bm, [mat_yard()])


def upper_ground(top_fn, name="Upper"):
    """壁の上と奥の芝。top_fn(x) -> (y0, z0, 天端の目標 H)。y0,z0 は芝の肩が始まる所。
    肩(被り)は丸めて上げ、差分が大きければ 1:1.5 の法で受け、その先は奥へ緩く上る芝の斜面。"""
    NS = 36

    def fn(x, v):
        tf = top_fn(x)
        y0, z0, h = tf[:3]
        lip_max = tf[3] if len(tf) > 3 else 0.25
        rise = max(h - z0, 0.0)
        lh = min(rise, lip_max)          # 肩(被り)の丈
        lr = 0.10 + 0.35 * lh            # 肩の奥行
        r2 = rise - lh                   # 法で受ける丈(1:1.5)
        run2 = 1.5 * r2 + 0.01
        if v < 0.05:
            # 前の裾: 石の頭の裏へ潜り込む(肩の下から空が抜けないように)
            u = v / 0.05
            return (x, y0 + 0.10 * (1 - u), z0 - 0.30 * (1 - u))
        if v < 0.30:
            # 肩: 石の頭の上で立ち上がって寝る 1/4 楕円(土を丸める)
            u = (v - 0.05) / 0.25
            return (x, y0 + lr * (1 - math.cos(u * math.pi / 2)), z0 + lh * math.sin(u * math.pi / 2))
        y1, z1 = y0 + lr, z0 + lh
        if v < 0.55:
            u = (v - 0.30) / 0.25
            f = 0.75 * u + 0.25 * u * u * (3 - 2 * u)
            return (x, y1 + run2 * u, z1 + r2 * f)
        yb = y1 + run2
        u = (v - 0.55) / 0.45
        y = yb + (9.0 - yb) * u
        return (x, y, h + 0.07 * (y - yb) + 0.03 * math.sin(0.7 * x + y) * min(1, (y - yb) * 2))
    o = grid_obj(name, xs_range(), NS, fn, mat_grass())
    grass_blades(fn, name + "_blades")
    return o


def grass_blades(fn, name, dens=9000.0, band=0.45, seed=11):
    """肩と法に芝の葉を三角の札で生やす(被りが「芝」に読めるように)。
    ⚠ Blender の hair は長さが効かず 1m の草むらになったので札にした。"""
    rng = random.Random(seed)
    bm = bmesh.new()
    x_lo, x_hi = X0 - EXT, X1 + EXT
    # 帯の面積をざっと見積もって本数を決める
    xs = [x_lo + (x_hi - x_lo) * i / 40 for i in range(41)]
    ar = 0.0
    for x in xs:
        p0 = Vector(fn(x, 0.0)); p1 = Vector(fn(x, band))
        ar += (p1 - p0).length * (x_hi - x_lo) / 41
    n = int(ar * dens)
    for _ in range(n):
        x = rng.uniform(x_lo, x_hi)
        v = 0.05 + (band - 0.05) * (rng.random() ** 1.8)   # 奥ほど疎(帯の縁が線に見えないように)
        p = Vector(fn(x, v))
        h = rng.uniform(0.03, 0.075) * (1.0 if v < band * 0.8 else 0.7)
        yaw = rng.uniform(0, math.tau)
        lean = rng.uniform(-0.35, 0.35)
        w = 0.006
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        tip = p + Vector((d.x * lean * h, d.y * lean * h - 0.25 * h * rng.random(), h))
        side = Vector((-d.y, d.x, 0)) * w
        a_, b_, c_ = bm.verts.new(p - side), bm.verts.new(p + side), bm.verts.new(tip)
        bm.faces.new((a_, b_, c_))
    return new_obj(name, bm, [mat_blade()])


def mat_blade():
    m = bpy.data.materials.get("GrassBlade")
    if m:
        return m
    m = bpy.data.materials.new("GrassBlade"); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    b = N["Principled BSDF"]; b.inputs['Roughness'].default_value = 0.8
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9.0
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = (0.05, 0.075, 0.025, 1)
    rp.color_ramp.elements[1].color = (0.15, 0.19, 0.07, 1)
    L.new(nz.outputs['Fac'], rp.inputs['Fac'])
    L.new(rp.outputs['Color'], b.inputs['Base Color'])
    return m


def backfill(case):
    """石の目地の奥の土(空やマゼンタが抜けないように)。面から 0.10 奥の傾いた帯"""
    def fn(x, v):
        top = Hw(case, x) - 0.09
        z = ZBOT + (top - ZBOT) * v
        return (x, BATTER * z + 0.10 + Yoff(case, x), z)
    return grid_obj("Backfill", xs_range(0.2), 6, fn, mat_soil(), False)


# ------------------------------------------------------------------ 野面の乱積み(Voronoi 千鳥)
def clip(poly, n, c):
    """半平面 dot(p, n) <= c で多角形を切る(Sutherland–Hodgman)"""
    out = []
    L = len(poly)
    for i in range(L):
        p, q = poly[i], poly[(i + 1) % L]
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


def rubble_cells(case, rng):
    """面の 2D (x, z) の石の輪郭。行ごとに半石ずらした種を置き、Voronoi で割る
    ⇒ 1石が上下 2〜3 石に跨り、竪目地が通らない。天端は石ごとに ±8cm の線で切る。"""
    seeds = []
    z = ZBOT
    k = 0
    while z < 2.2:
        rh = rng.uniform(0.26, 0.40)
        zc = z + rh * 0.5
        x = X0 - EXT - rng.uniform(0, 0.4) - (0.25 if k % 2 else 0)
        while x < X1 + EXT + 0.4:
            w0, w1 = width_range(case, x)
            w = rng.uniform(w0, w1)
            sx = x + w * 0.5 + rng.uniform(-0.06, 0.06)
            sz = zc + rng.uniform(-0.05, 0.05)
            if sz < Hw(case, sx) - (0.0 if rootzone(case, sx) else 0.07):
                seeds.append((sx, sz))
            x += w
        z += rh
        k += 1
    cells = []
    for i, (sx, sz) in enumerate(seeds):
        g = rng.uniform(0.022, 0.042)
        poly = [(sx - 1.2, ZBOT), (sx + 1.2, ZBOT), (sx + 1.2, sz + 1.2), (sx - 1.2, sz + 1.2)]
        for j, (tx, tz) in enumerate(seeds):
            if i == j or abs(tx - sx) > 1.3 or abs(tz - sz) > 1.0:
                continue
            dx, dz = tx - sx, tz - sz
            d = math.hypot(dx, dz)
            n = (dx / d, dz / d)
            mx, mz = (sx + tx) / 2, (sz + tz) / 2
            poly = clip(poly, n, n[0] * mx + n[1] * mz - g / 2)
            if len(poly) < 3:
                break
        if len(poly) < 3:
            continue
        # 天端: その石の頭 = Hw + ±8cm、地面の傾きに沿う。⛔ 直線で切ると頭が平らな切石に
        #   見える(1巡目で実見)⇒ 半径 R の円弧(5本の接線)で切って頭を丸くする
        j8 = rng.uniform(-0.08, 0.08)
        slope = (Hw(case, sx + 0.05) - Hw(case, sx - 0.05)) / 0.1
        top = Hw(case, sx) + j8
        R = rng.uniform(0.12, 0.20) if rootzone(case, sx) else rng.uniform(0.16, 0.32)
        base = math.atan(slope)
        for a in (-0.75, -0.4, 0.0, 0.4, 0.75):
            n = (-math.sin(base + a), math.cos(base + a))
            cxz = (sx, top - R)
            poly = clip(poly, n, n[0] * cxz[0] + n[1] * cxz[1] + R)
            if len(poly) < 3:
                break
        if len(poly) < 3 or area(poly) < 0.012:
            continue
        cells.append((poly, (sx, sz)))
    return cells


def rubble_stone(bm, poly, rng, depth, st):
    """2D 輪郭 → 野面の塊。前面は中心を浮かせた数枚の割肌(ファセット)、周りの稜は
    ベベル(幅 3〜4cm)で落とす ⇒ 角の丸みは 2〜6cm。控えは奥ですぼめる。"""
    cx = sum(p[0] for p in poly) / len(poly)
    cz = sum(p[1] for p in poly) / len(poly)
    prot = rng.uniform(-0.02, 0.045) - (Yoff(st, cx) if st else 0.0)   # 面からの出入り(+ 法の張り出し)
    ta, tb = rng.uniform(-0.14, 0.14), rng.uniform(-0.10, 0.14)   # 面の向きの振れ(石ごと)

    def fy(z, x=None):
        x = cx if x is None else x
        return BATTER * z - prot + ta * (x - cx) + tb * (z - cz)
    F, M, B = [], [], []
    for (x, z) in poly:
        dx, dz = x - cx, z - cz
        F.append(bm.verts.new((x, fy(z, x) + rng.uniform(-0.015, 0.02), z)))
        M.append(bm.verts.new((x + dx * 0.04, BATTER * z - prot + 0.14, z + dz * 0.04)))
        bx, bz = cx + dx * 0.80, cz + dz * 0.80 - (0.03 if depth > 0.3 else 0.10)
        B.append(bm.verts.new((bx, BATTER * cz - prot + depth, bz)))
    # 割肌: 中心を少し前へ・ずらして置き、扇に割る(面ごとに向きが少しずつ違う)
    C = bm.verts.new((cx + rng.uniform(-0.05, 0.05), fy(cz) - rng.uniform(0.015, 0.045),
                      cz + rng.uniform(-0.03, 0.03)))
    faces = []
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((C, F[i], F[j])))
        faces.append(bm.faces.new((F[i], M[i], M[j], F[j])))
        faces.append(bm.faces.new((M[i], B[i], B[j], M[j])))
    faces.append(bm.faces.new(list(reversed(B))))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    ofs = Vector((rng.uniform(0, 9), rng.uniform(0, 9), rng.uniform(0, 9)))
    tone = rng.random()
    la = bm.faces.layers.float_vector.get("ofs"); lt = bm.faces.layers.float.get("tone")
    for f in faces:
        f[la] = ofs; f[lt] = tone; f.smooth = False
    return faces


def stone_bm():
    bm = bmesh.new()
    bm.faces.layers.float_vector.new("ofs")
    bm.faces.layers.float.new("tone")
    return bm


def finish_stones(o, levels=2, disp=0.018, bevel=None):
    if bevel:
        bv = o.modifiers.new("bevel", 'BEVEL'); bv.width = bevel; bv.segments = 3
        bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(25); bv.use_clamp_overlap = True
        bv.profile = 0.6
    if levels:
        sub = o.modifiers.new("sub", 'SUBSURF'); sub.levels = levels; sub.render_levels = levels
    tex = bpy.data.textures.new("rough_" + o.name, 'CLOUDS'); tex.noise_scale = 0.14
    tex.noise_depth = 2
    d = o.modifiers.new("disp", 'DISPLACE'); d.texture = tex; d.strength = disp
    d.texture_coords = 'GLOBAL'; d.mid_level = 0.5
    return o


def build_rubble(case, rng):
    cells = rubble_cells(case, rng)
    bm = stone_bm()
    n14 = 0
    for poly, (sx, sz) in cells:
        rz = rootzone(case, sx)
        depth = rng.uniform(0.35, 0.50) if rz else rng.uniform(0.45, 0.75)
        if case == "a" and H(sx) < 0.2:
            # ⛔ 控えが上の芝より高いと石の背が芝の上に転がって見える(低い区間で実見)⇒ 浅く据える
            depth = rng.uniform(0.24, 0.30)
        rubble_stone(bm, poly, rng, depth, case)
        if X0 <= sx <= X1:
            n14 += 1
    o = new_obj("Stones_" + case, bm, [mat_stone()])
    finish_stones(o, levels=1, disp=0.016, bevel=0.045)
    return o, n14


# ------------------------------------------------------------------ 玉石の谷積み
def build_tamaishi(rng):
    bm = stone_bm()
    la = bm.faces.layers.float_vector.get("ofs"); lt = bm.faces.layers.float.get("tone")
    n14 = 0
    dz, dx = 0.125, 0.205
    k = 0
    z = ZBOT + 0.06
    while z < 2.0:
        sign = 1 if k % 2 == 0 else -1
        x = X0 - EXT + (dx * 0.5 if k % 2 else 0) + rng.uniform(-0.03, 0.03)
        while x < X1 + EXT:
            a = rng.uniform(0.20, 0.30); b = rng.uniform(0.13, 0.18); d = rng.uniform(0.30, 0.45)
            th = math.radians(sign * rng.uniform(36, 50))
            ext_z = math.hypot(a / 2 * math.sin(th), b / 2 * math.cos(th))
            cx = x + rng.uniform(-0.02, 0.02); cz = z + rng.uniform(-0.02, 0.02)
            lim = Hw("c", cx) + rng.uniform(-0.05, 0.05)
            if cz + ext_z > lim and lim - cz > 0.6 * ext_z:
                # 天端の石は小ぶりのものを選んで収める(⛔ 飛ばすと天端に歯抜けが出た)
                k_ = (lim - cz) / ext_z
                a, b, ext_z = a * k_, b * k_, ext_z * k_
            if cz + ext_z <= lim:
                cy = BATTER * cz + d / 2 - rng.uniform(0.03, 0.06)
                M = (mathutils.Matrix.Translation((cx, cy, cz)) @
                     mathutils.Matrix.Rotation(-th, 4, 'Y') @
                     mathutils.Matrix.Diagonal((a / 2, d / 2, b / 2, 1)))
                res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0, matrix=M)
                seed = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
                ctr = Vector((cx, cy, cz))
                for v in res['verts']:
                    r = v.co - ctr
                    v.co = ctr + r * (1 + 0.10 * mathutils.noise.noise(r * 6 + seed))
                fs = {f for v in res['verts'] for f in v.link_faces}
                ofs = Vector((rng.uniform(0, 9),) * 3); tone = rng.random()
                for f in fs:
                    f[la] = ofs; f[lt] = tone; f.smooth = True
                if X0 <= cx <= X1:
                    n14 += 1
            x += dx * rng.uniform(0.95, 1.08)
        z += dz
        k += 1
    o = new_obj("Stones_c", bm, [mat_stone()])
    finish_stones(o, levels=1, disp=0.008)
    return o, n14


# ------------------------------------------------------------------ 今の姿(城のキットの模し)
def build_now():
    """2.4m 級の箱を並べ、天端は 0.6 刻みで上の地面を越える最小の段へ。3分の法。
    UV は kit の `stone wall` と同じ割付(面=下 0.82 / 天端=上の帯)"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    seg = 2.4
    x = X0 - EXT
    tops = []
    n14 = 0
    while x < X1 + EXT - 1e-6:
        x1 = min(x + seg, X1 + EXT)
        T = math.ceil(max(H(x), H(x1)) / 0.6 - 1e-6) * 0.6
        tops.append((x, x1, T))
        yb = 0.0
        # 断面: 前下 (ZBOT) / 前上 (T) / 後上 / 後下
        prof = [(BATTER * ZBOT, ZBOT), (BATTER * T, T), (BATTER * T + 0.9, T), (BATTER * T + 0.9, ZBOT)]
        L = [bm.verts.new((x, y, z)) for (y, z) in prof]
        R = [bm.verts.new((x1, y, z)) for (y, z) in prof]
        fs = []
        for i in range(4):
            j = (i + 1) % 4
            fs.append(bm.faces.new((L[i], L[j], R[j], R[i])))
        fs.append(bm.faces.new(list(reversed(L)))); fs.append(bm.faces.new(R))
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        # UV
        for f in fs:
            nz = f.normal.z
            for lp in f.loops:
                co = lp.vert.co
                u = (co.x - x) / (x1 - x)
                if nz > 0.9:                          # 天端: 上の帯
                    v = 0.86 + 0.10 * (co.y - BATTER * T) / 0.9
                elif abs(f.normal.x) > 0.9:           # 小口
                    u = (co.y - BATTER * co.z) / 0.9
                    v = 0.82 * (co.z - ZBOT) / (2.4 - ZBOT)
                else:
                    v = 0.82 * (co.z - ZBOT) / (2.4 - ZBOT)
                lp[uvl].uv = (u, v)
        if X0 - 1e-6 <= (x + x1) / 2 <= X1 + 1e-6:
            n14 += 1
        x = x1
    o = new_obj("Castle", bm, [mat_castle()])
    return o, tops, n14


# ------------------------------------------------------------------ 組み・撮影
def tris_of(o):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    # 14m 内だけ数える
    n14 = sum(1 for t in me.loop_triangles
              if X0 <= (ev.matrix_world @ me.vertices[t.vertices[0]].co).x <= X1)
    ev.to_mesh_clear()
    return n, n14


def build(case):
    V.reset()
    rng = random.Random(SEED + {"now": 0, "a": 1, "b": 2, "c": 3}[case])
    yard()
    if case == "now":
        o, tops, n = build_now()

        def top_fn(x):
            T = next(t for (a, b, t) in tops if a - 1e-6 <= x <= b + 1e-6)
            return (BATTER * T + 0.9, H(x) - 0.02, H(x))
        upper_ground(top_fn)
    else:
        if case == "c":
            o, n = build_tamaishi(rng)
        else:
            o, n = build_rubble(case, rng)
        backfill(case)

        def top_fn(x):
            hw = Hw(case, x)
            z0 = shoulder(case, x)[0]
            return (BATTER * max(hw, 0.0) - 0.05 + Yoff(case, x), z0, H(x), lip_of(case, x))
        upper_ground(top_fn)
    return o, n


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.eevee.taa_render_samples = 64
    try:
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = True
        sc.eevee.ray_tracing_options.resolution_scale = '1'
    except Exception:
        pass
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast' if False else 'None'
    w = bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = ((1, 0, 1, 1) if OPT.get("magenta") else (0.62, 0.70, 0.80, 1))
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.2; sun.data.angle = math.radians(1.5)
    # 左前上から斜めに当てる(石の凹凸が読める角度)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-40))
    sc.collection.objects.link(sun)


def camera(loc, look, lens):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("Cam"); cd.lens = lens; cd.clip_start = 0.05; cd.clip_end = 200
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam); sc.camera = cam
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return cam


def main_camera():
    """前庭の中・目の高さ 1.5m、壁の法線から 30° 振って、左端〜右端を一枚に収める"""
    ang = math.radians(30)
    dist = 10.0
    cam = Vector((-math.sin(ang) * dist, -math.cos(ang) * dist, 1.5))
    ends = [Vector((X0, 0, 0)), Vector((X1, 0, 0))]
    az = [math.atan2(e.x - cam.x, e.y - cam.y) for e in ends]
    mid = (az[0] + az[1]) / 2
    half = (az[1] - az[0]) / 2 + math.radians(3.5)
    lens = 36 / (2 * math.tan(half))
    look = cam + Vector((math.sin(mid), math.cos(mid), 0)) * 10
    look.z = 0.62
    print("CAM", tuple(round(c, 2) for c in cam), "lens %.1f" % lens)
    return cam, look, lens


def render_case(case):
    o, n = build(case)
    setup_scene()
    tri_all, tri14 = tris_of(o)
    os.makedirs(OUT, exist_ok=True)
    cam, look, lens = main_camera()
    c = camera(cam, look, lens)
    V.render(os.path.join(OUT, "%s%s.png" % (case, SUFFIX)))
    if case in ("a", "b") and not LOW:
        xc = X6 + 0.5
        bpy.data.objects.remove(c, do_unlink=True)
        camera((xc - 0.6, -2.0, 1.6), (xc, BATTER * H(xc), H(xc) - 0.15), 24)
        V.render(os.path.join(OUT, "%s_top.png" % case))
    print("DODOME %s stones14=%d tris_all=%d tris14=%d X6=%.2f" % (case, n, tri_all, tri14, X6))


if __name__ == "__main__":
    todo = ["now", "a", "b", "c"] if "all" in WHICH else WHICH
    for c in todo:
        render_case(c)
