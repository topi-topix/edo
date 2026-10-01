"""**町木戸(まちきど)** — 通りの口を道幅いっぱいに塞ぐ木戸。昼の姿(大戸は開き・潜りは閉)。
山王門前町の参道の南の口(門前1 と門前2 の間・道幅 10.54m)に1基(EDO-0503 ②・考証方の勧め・切絵図 S)。

    blender --background --python Tools/Blender/build_machikido.py -- --haba 10.54 [--render]
    blender --background --python Tools/Blender/build_machikido.py -- --haba 10.54 --spec-only
    (`--spec-only` = FBX を焼き直さず札だけ書く。札の置き場は既定 `Assets/Edo/Data/PartSpecs/`、
     環境変数 `BUZAI_SPEC_OUT` で振り替えられる。FBX の置き場は `BUZAI_OUT` で振り替えられる)
    任意: --kuguri L|R|none(潜りを付ける袖。既定 L = −X)/ --shut(大戸を閉じた版 `_Shut`)
    任意: --keisha <m>(道の横断勾配。**−X 端から +X 端への地面の下がり**[m・Unity 局所]。
          正 = +X が低い / 負 = −X が低い。出力 `MachiKido_<haba>_k<keisha>`(負は `km`)。EDO-0503)

【勾配の版(--keisha)】地面は局所 X について一直線 g(X) = −keisha·X/haba と見る(Z には平ら)。
  ・**ピボット = 足形の中心(X=0)の地面の高さ**。呼ぶ側は中心の地面にピボットを置いて据える。
  ・柱の足元はその位置の地面まで(沓石・掘立の根入れ 0.26 はそこから測る)。沓石は柱の芯の地面に水平に据える。
  ・冠木・笠木(門の頭)は**水平のまま**。親柱は頭を揃え、足だけを伸び縮みさせる。
  ・大戸の敷居・扉の下端は勾配なり(開いた扉は吊り元の地面から 0.06 上で止め、頭は冠木の下端)。
  ・袖(端柱・中柱・地覆・格子・袖の笠木・潜り)は**全体を勾配なりに縦に剪断**する(竪は鉛直のまま)。
  ・札: foot(平面)は勾配0と同じ。yBottom = 下手の端柱の根 = −0.26 − |keisha|/2。
    jamb の帯は**その端の地面**から 0.30〜1.80。追加の欄 `keisha` / `ground`(地面の線)/ `contactPts`
    (各柱の芯の地面 = 当たりの点・局所 x,y,z)を書く。

【なぜ新造するか】在庫の `edogoyomi/es_kido/kido_open.obj`(`Eg.KidoOpen`)は ES=1.818 倍で
  W4.66 × H1.78 × D1.29 — 路地木戸の寸法で、通りの口には低く狭い。町木戸は道幅いっぱいを塞ぐので
  **幅が場所ごとに違う** ⇒ 幅を引数に取る生成器にした。

【型(すべて作図の変数。確度は各行)】
  ・道幅いっぱい: 両端の**端柱の外の面**が道の両側の区画の角に接する(全幅 = `--haba`)【硬い・依頼】
  ・中央に**親柱2本+冠木+笠木**の冠木門形、**大戸は両開き・内開き(−Z = 町の内)**【B 町木戸の図様の一般類型】
  ・大戸の口 = **2間(3.636)**、全幅が 7.5m に満たなければ 1.5間(2.727)【U】
  ・冠木の下端(内法)**2.727 = 9尺**・冠木の丈 0.24・親柱 7寸角(0.212)・笠木の天端 3.075【U】
  ・袖 = **竪格子の固定柵**(地覆・笠木・中柱を 1間以内の割りで)。丈 **2.12 = 7尺**【U】
  ・片袖に**潜り戸**(幅 3尺 0.909 × 丈 5尺 1.515・閉)— 夜の通行を潜りで改める【B 一般類型 / 寸法 U】
  ・足元: 親柱は沓石(棟門と同寸・根入れ 0.26)、袖の柱は掘立(同じ 0.26 埋める)【U】
  ⛔ 木戸番屋はこの部材に含まない(別の駒)。

【向き(Unity 座標)】幅=X(道の幅の向き)/ 高さ=Y / 厚み=Z。**+Z = 外(町の外 = 南)**。
  ピボット = **足形の中心・地盤(敷居)レベル**。底は −0.26(札の yBottom)。
  ⚠ 潜りは −X 側の袖に付く(Unity の取り込みで x が反転すると +X に見える — 札の値は対称なので変わらない)。

【材】`wood` / `Foundation_A_01`(Village Kit。棟門・冠木門と同じ借り先)。⛔ 新規マテリアルを作らない。
  remap は Unity の **Edo ▸ 類型 ▸ 新造部材のマテリアルをremap**(`Models/Mon` を見ている)。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_obi_nagaya as N
import build_munamon as B            # 板扉 leaf()・沓石・凸包
import build_kabukimon as K          # 札の線(overlay)

OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Mon"))
SHOT = os.path.join(V.REPO, "Screenshots")
STOCK = os.path.join(V.REPO, "Assets", "edogoyomi", "es_kido", "kido_open.obj")
WOOD, STONE = N.WOOD, N.STONE
if os.environ.get("BUZAI_SPEC_OUT"):
    V.SPEC_DIR = os.environ["BUZAI_SPEC_OUT"]

KEN      = 1.818
OYA      = 0.212       # 親柱 7寸角【U】
EP       = 0.150       # 端柱(袖の端・区画の角に接する)5寸角【U】
MP       = 0.120       # 袖の中柱・潜りの方立 4寸角【U】
KABUKI_Y0 = 2.727      # 冠木の下端 = 大戸の内法 9尺【U】
KABUKI_H  = 0.243      # 冠木の丈 8寸【U】
KABUKI_D  = 0.150      # 冠木の見込【U】
NOSE      = 0.30       # 冠木の鼻(親柱の外の面から)【U】
TOP       = KABUKI_Y0 + KABUKI_H + 0.06    # 親柱の天端 3.03(1丈)
KASA      = (0.045, 0.17)                  # 笠木の厚み・半見込【U】
SODE_TOP  = 2.12       # 袖の天端(笠木の天端)7尺【U】
SODE_KASA = (0.07, 0.075)                  # 袖の笠木の丈・半見込
JIFUKU    = (0.12, 0.06)                   # 地覆の丈・半見込
KUG_W, KUG_H = 0.909, 1.515                # 潜りの口 3尺 × 5尺【U】
NEIRE     = 0.26       # 袖の柱の根入れ(掘立)= 沓石の根入れと揃える
OPEN_DEG  = 90.0       # 大戸の振れ角(内開き・親柱の真後ろへ畳む)【U】
SILL = (-0.04, 0.06, 0.16)
KEISHA = 0.0           # 道の横断勾配(build の引数で上書き)。−X 端 → +X 端の下がり[m]


def ground_u(X, haba, keisha):
    """Unity 局所 X の地面の高さ(ピボット = X=0 の地面 = 0)"""
    return -keisha * X / haba


def warp(m, i0, ya, fa, yb, fb):
    """m.v[i0:] の高さを y の一次で動かす: y=ya で fa(x)・y=yb で fb(x) だけ上げる(間は線形・外は端の値)。
    x は**メッシュの走り**(Unity X = −x)。竪は鉛直のまま、上下の縁だけが傾く。"""
    for v in m.v[i0:]:
        t = 0.0 if yb == ya else min(1.0, max(0.0, (v.z - ya) / (yb - ya)))
        a, b = fa(v.x), fb(v.x)
        v.z += a + (b - a) * t


def main_opening(haba):
    return 2 * KEN if haba >= 7.5 else 1.5 * KEN


def layout(haba, kuguri="L"):
    """幅から割りを決める。戻り値 dict(全部 Unity 局所の x)"""
    O = main_opening(haba)
    hx = O / 2.0
    ox = hx + OYA                       # 親柱の外の面
    ex = haba / 2.0                     # 端柱の外の面 = 区画の角
    ei = ex - EP                        # 端柱の内の面
    sode = ei - ox                      # 片袖の格子の長さ(柱を除く)
    if sode < 0.30:
        raise SystemExit("⛔ 幅 %.3f では袖が %.3f しか取れない(大戸 %.3f)" % (haba, sode, O))
    kug = kuguri if (kuguri in ("L", "R") and sode >= KUG_W + MP + 0.30) else None
    if kuguri in ("L", "R") and kug is None:
        print("[machikido] ⚠ 袖 %.3f に潜りが入らない — 潜りなしで焼く" % sode)
    return dict(O=O, hx=hx, px=hx + OYA / 2, ox=ox, ex=ex, ei=ei, sode=sode, kug=kug)


def name_of(haba, opened=True, keisha=0.0):
    k = ""
    if abs(keisha) >= 0.005:
        k = "_k" + ("m" if keisha < 0 else "") + N.fmt(abs(keisha))
    return "MachiKido_" + N.fmt(haba) + k + ("" if opened else "_Shut")


def build(haba, kuguri="L", opened=True, name=None, want_spec=False, spec_only=False, keisha=0.0):
    L = layout(haba, kuguri)
    name = name or name_of(haba, opened, keisha)
    spec = kido_spec(name, haba, L, opened, keisha)
    if spec_only:
        return None, name, spec
    P = N.palette()
    m = VM.Mesh()
    wuv = P['wuv']
    post_uv = VM.sub(wuv, 0.10, 0.02, 0.42, 0.98)
    beam_uv = VM.sub(wuv, 0.20, 0.15, 0.95, 0.50)
    rail_uv = VM.sub(wuv, 0.30, 0.10, 0.85, 0.30)
    bar_uv  = VM.sub(wuv, 0.60, 0.10, 0.95, 0.90)
    hx, px, ox, ex, ei = L['hx'], L['px'], L['ox'], L['ex'], L['ei']
    oh = OYA / 2.0
    gm = lambda x: ground_u(-x, haba, keisha)      # メッシュの走り x の地面(Unity X = −x)
    zero = lambda x: 0.0

    # ---- 親柱(沓石の上)・冠木・笠木
    for s in (-1, 1):
        gp = gm(s * px)
        i0 = len(m.v)
        m.box(s * px - B.KUTSU, s * px + B.KUTSU, -B.KUTSU_H, 0.05, -B.KUTSU, B.KUTSU,
              VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)
        warp(m, i0, 0.0, lambda x, g=gp: g, 1.0, lambda x, g=gp: g)    # 沓石は柱の芯の地面に水平
        i0 = len(m.v)
        m.box(s * px - oh, s * px + oh, 0.02, TOP, -oh, oh, post_uv, WOOD)
        warp(m, i0, 0.02, lambda x, g=gp: g, TOP, zero)                # 頭を揃え足だけ伸縮
    kn = ox + NOSE
    kd = KABUKI_D / 2.0
    m.box(-kn, kn, KABUKI_Y0, KABUKI_Y0 + KABUKI_H, -kd, kd, beam_uv, WOOD)
    m.box(-kn - 0.05, kn + 0.05, TOP, TOP + KASA[0], -KASA[1], KASA[1],
          VM.sub(wuv, 0.25, 0.55, 0.95, 0.80), WOOD)
    # 大戸の敷居(勾配なり)
    i0 = len(m.v)
    m.box(-px, px, SILL[0], SILL[1], -SILL[2], SILL[2], rail_uv, WOOD)
    warp(m, i0, 0.0, gm, 1.0, gm)
    # 大戸(両開き・内開き)。頭は冠木の下端まで(隙を作らない)・下端は勾配なり
    ang = OPEN_DEG if opened else 0.0
    for (a0, a1, hg, an, mt) in ((-hx, -B.LEAF_GAP, -hx, -ang, None),
                                 (B.LEAF_GAP, hx, hx, ang, B.LEAF_GAP)):
        i0 = len(m.v)
        B.leaf(m, P, a0, a1, hg, an, meet=mt, top=KABUKI_Y0)
        if opened:     # 振れた扉は吊り元の地面に合わせる
            warp(m, i0, 0.06, lambda x, g=gm(hg): g, KABUKI_Y0, zero)
        else:
            warp(m, i0, 0.06, gm, KABUKI_Y0, zero)
    if not opened:     # 閉じた版は召し合わせの隙の真後ろに定規縁(build_kabukimon と同じ)
        i0 = len(m.v)
        m.box(-B.LEAF_GAP - 0.03, B.LEAF_GAP + 0.03, 0.06, KABUKI_Y0,
              B.LEAF_Z0 - 0.032, B.LEAF_Z0, VM.sub(wuv, 0.66, 0.05, 0.74, 0.95), WOOD)
        warp(m, i0, 0.06, gm, KABUKI_Y0, zero)

    # ---- 袖(両側)。端柱・中柱は掘立、地覆・笠木・竪格子
    ky0, ky1 = SODE_TOP - SODE_KASA[0], SODE_TOP
    jz = JIFUKU[1]
    bz = 0.022                          # 竪子の半見込
    for s in (-1, 1):
        i_sode = len(m.v)               # 袖は全部まとめて勾配なりに剪断する(下の warp)
        a, b = ox, ei                   # 格子を張る区間(|x|)
        def X(u0, u1):
            return (min(s * u0, s * u1), max(s * u0, s * u1))
        # 端柱(外の面 = 区画の角)
        x0, x1 = X(ei, ex)
        m.box(x0, x1, -NEIRE, ky0, -EP / 2, EP / 2, post_uv, WOOD)
        # 笠木・地覆は親柱の面から端柱の外の面まで(⛔ 外へ出さない — 区画の角に食い込む)
        x0, x1 = X(ox, ex)
        m.box(x0, x1, ky0, ky1, -SODE_KASA[1], SODE_KASA[1], beam_uv, WOOD)
        x0, x1 = X(ox, ei)
        m.box(x0, x1, 0.0, JIFUKU[0], -jz, jz, rail_uv, WOOD)
        # 潜り(この袖に付くなら親柱の脇)
        bays = []
        if (L['kug'] == "L" and s < 0) or (L['kug'] == "R" and s > 0):
            k0, k1 = ox, ox + KUG_W
            # 方立(潜りの戸当たり側)
            x0, x1 = X(k1, k1 + MP)
            m.box(x0, x1, -NEIRE, ky0, -MP / 2, MP / 2, post_uv, WOOD)
            # 潜りの地覆は切る(戸の下は敷居)— 敷居を据え直す
            x0, x1 = X(k0, k1)
            m.box(x0, x1, SILL[0], SILL[1], -0.10, 0.10, rail_uv, WOOD)
            # 鴨居と、その上の格子
            m.box(x0, x1, KUG_H, KUG_H + 0.09, -0.06, 0.06, rail_uv, WOOD)
            m.koshi(x0, x1, KUG_H + 0.09, ky0, -bz, bz, bar_uv, WOOD,
                    pitch=0.15, bar=0.02, yoko=0)
            # 潜り戸(閉)。吊り元 = 親柱の外の面。頭は鴨居の下端
            g0, g1 = X(k0 + 0.005, k1 - 0.005)
            B.leaf(m, P, g0, g1, s * k0, 0.0, top=KUG_H)
            a = k1 + MP
        # 残りを 1間以内の割りで中柱を入れて格子を張る
        span = b - a
        n = max(1, int(math.ceil((span + 1e-6) / KEN)))
        w = (span - (n - 1) * MP) / n
        u = a
        for i in range(n):
            bays.append((u, u + w))
            u += w
            if i < n - 1:
                x0, x1 = X(u, u + MP)
                m.box(x0, x1, -NEIRE, ky0, -MP / 2, MP / 2, post_uv, WOOD)
                u += MP
        for (u0, u1) in bays:
            x0, x1 = X(u0, u1)
            m.koshi(x0, x1, JIFUKU[0], ky0, -bz, bz, bar_uv, WOOD, pitch=0.15, bar=0.02, yoko=2)
        warp(m, i_sode, 0.0, gm, 1.0, gm)
    o = m.to_object(name, [P['wood'], P['wall'], P['stone']])
    V.sel([o])
    bpy.ops.object.material_slot_remove_unused()
    V.dedup_materials()
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[machikido] %s 全幅 %.3f / 大戸 %.3f / 袖 %.3f×2 / 潜り %s / 内法 %.3f / 笠木 %.3f / 勾配 %+.3f"
          % (name, haba, L['O'], L['sode'], L['kug'] or "なし", KABUKI_Y0, TOP + KASA[0], keisha))
    return (o, name, spec) if want_spec else (o, name)


def _post_xs(L):
    """地面に着く柱の芯(|x|・メッシュの走り)と名。袖の割りは build と同じ手続き。"""
    ox, ei, ex = L['ox'], L['ei'], L['ex']
    out = [("oya", L['px']), ("hashi", ex - EP / 2)]
    for s in (-1, 1):
        a = ox
        if (L['kug'] == "L" and s < 0) or (L['kug'] == "R" and s > 0):
            a = ox + KUG_W + MP
            out.append(("hodate" + ("L" if s < 0 else "R"), s * (ox + KUG_W + MP / 2)))
        span = ei - a
        n = max(1, int(math.ceil((span + 1e-6) / KEN)))
        w = (span - (n - 1) * MP) / n
        u = a
        for i in range(n - 1):
            u += w
            out.append(("naka" + ("L" if s < 0 else "R"), s * (u + MP / 2)))
            u += MP
    return out


def kido_spec(name, haba, L, opened, keisha=0.0):
    """札を**作図の変数から**出す(build_kabukimon.gate_spec と同じ手続き)。⛔ メッシュを測らない。
    勾配の版: 座標は Unity 局所(X = −メッシュの走り)・ピボット = X=0 の地面。"""
    hx, px, ex = L['hx'], L['px'], L['ex']
    g = lambda X: ground_u(X, haba, keisha)
    yb = -B.KUTSU_H + min(g(-ex), g(ex))              # 下手の端柱の根(勾配0なら −NEIRE)
    band0, band1 = -B.KUTSU_H + 0.30, -B.KUTSU_H + 1.80   # 各端の地面からの帯(下の jamb で足す)
    corners = [(s * px + a * B.KUTSU, b * B.KUTSU) for s in (-1, 1) for a in (-1, 1) for b in (-1, 1)]
    corners += [(s * ex, b * EP / 2) for s in (-1, 1) for b in (-1, 1)]
    corners += [(s * (ex - EP), b * EP / 2) for s in (-1, 1) for b in (-1, 1)]
    foot = [{"x": x, "y": z} for (x, z) in B._hull(corners)]
    zs = [z for (_x, z) in corners] + [OYA / 2, -OYA / 2, SILL[2], -SILL[2],
                                       B.LEAF_ZF, B.LEAF_ZB]   # 潜り戸(閉)も同じ面
    if opened:
        a = math.radians(OPEN_DEG)
        c, sn = math.cos(a), math.sin(a)
        for x in (-hx, -B.LEAF_GAP, B.LEAF_GAP, hx):
            hinge = -hx if x < 0 else hx
            ang_s = -sn if x < 0 else sn
            for z in (B.LEAF_ZF, B.LEAF_ZB):
                zs.append((x - hinge) * ang_s + z * c)
    # 脇の面 = 端柱の外の面(帯の全段で最も外 = 区画の角に接する面)。z は端柱の見込
    jz = [EP / 2, -EP / 2]
    jamb = lambda x: {"x": x, "z0": min(jz), "z1": max(jz), "y0": band0 + g(x), "y1": band1 + g(x)}
    src = ("blender:build_machikido.py build(haba=%g, main=%g, kuguri=%s, opened=%s, oya=%g, ep=%g, "
           "kabuki=%g+%g, top=%g, sode=%g%s)" % (haba, L['O'], L['kug'], opened, OYA, EP,
                                               KABUKI_Y0, KABUKI_H, TOP + KASA[0], SODE_TOP,
                                               (", keisha=%g" % keisha) if keisha else ""))
    ytop = max(TOP + KASA[0], SODE_TOP + max(g(-ex), g(ex)))
    d = {
        "prefab": "Assets/Edo/Models/Mon/%s.fbx" % name,
        "kind": "gate", "source": src, "unitScale": 1.0,
        "yBottom": yb, "foot": foot,
        "front": max(zs), "back": min(zs),
        "jambL": jamb(-ex), "jambR": jamb(ex),
        "passage": {"x0": -hx, "x1": hx},
        "eave": {"x0": -ex, "x1": ex,
                 "z0": min(zs + [-KASA[1]]), "z1": max(zs + [KASA[1]]),
                 "y0": yb, "y1": ytop},
        "faceOut": 0.0, "faceIn": 0.0, "copingOverhang": 0.0,
        "height": ytop - yb,
    }
    if keisha:
        d["keisha"] = keisha
        d["pivot"] = "X=0 の地面(足形の中心の地盤)"
        d["ground"] = {"x0": -ex, "y0": g(-ex), "x1": ex, "y1": g(ex)}
        pts = []
        for (nm, xm) in _post_xs(L):
            for s in ((-1, 1) if nm in ("oya", "hashi") else (1,)):
                X = -(s * xm)                         # メッシュの走り → Unity X
                pts.append({"name": nm.rstrip("LR"), "x": round(X, 5), "y": round(g(X), 5), "z": 0.0})
        d["contactPts"] = sorted(pts, key=lambda p: p["x"])
    return d


# ---------------------------------------------------------------- 検め画像
def _stock(x_off):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=STOCK)
    got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    o = V.join(got, "Stock_Kido")
    V.sel([o])
    bpy.ops.transform.resize(value=(1.818,) * 3, center_override=(0, 0, 0))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mn, mx = V.bbox([o])
    o.location = (x_off - (mn.x + mx.x) / 2.0, -(mn.y + mx.y) / 2.0, -mn.z)
    bpy.context.view_layer.update()
    for mat in o.data.materials:
        if mat and mat.node_tree:
            for n in mat.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Alpha'].default_value = 1.0
    return o


def _magenta_world():
    w = bpy.context.scene.world
    w.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 0.0, 1.0, 1)


def _earth(keisha, haba, half=8.0, depth=6.0):
    """検め画像だけの地面(勾配なり)。⛔ 書き出さない・材を付けない。Blender x の地面 = keisha·x/haba"""
    vs, fs = [], []
    for bx in (-half, half):
        for by in (-depth, depth):
            vs += [(bx, by, keisha * bx / haba), (bx, by, -4.0)]
    # 0..7 = (x-,y-,top)(x-,y-,bot)(x-,y+,top)(x-,y+,bot)(x+,y-,top)(x+,y-,bot)(x+,y+,top)(x+,y+,bot)
    fs = [(0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4), (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6)]
    me = bpy.data.meshes.new("Earth")
    me.from_pydata(vs, [], fs)
    me.update()
    e = bpy.data.objects.new("Earth", me)
    bpy.context.collection.objects.link(e)
    return e


def shots(o, spec, key, keisha=0.0, haba=None):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    W, H = mx.x - mn.x, mx.z - mn.z
    # ① 外(南・Unity +Z = Blender −Y)からの正面立面。背景マゼンタで抜けを見る
    V.studio((c.x, mn.y - W * 2.0, c.z), (c.x, c.y, c.z), ortho_scale=W * 1.06, res=(1800, 900))
    _magenta_world()
    V.render(os.path.join(SHOT, "machikido_%s_elev.png" % key))
    # ② 外から斜め(人の目の高さ)
    V.studio((mn.x - W * 0.25, mn.y - W * 1.0, 1.6), (c.x, c.y, H * 0.40), res=(1800, 1100))
    V.render(os.path.join(SHOT, "machikido_%s_3d.png" % key))
    # ③ 内(町の側)から斜め — 開いた大戸・潜り戸の裏
    V.studio((mx.x + W * 0.25, mx.y + W * 1.0, 1.8), (c.x, c.y, H * 0.40), res=(1800, 1100))
    V.render(os.path.join(SHOT, "machikido_%s_ura.png" % key))
    # ④ 潜りの寄り(外から)
    kx = -(spec["passage"]["x1"] + OYA + KUG_W / 2)
    V.studio((kx - 1.2, mn.y - 4.0, 1.4), (kx, 0.0, 1.0), res=(1400, 1100))
    V.render(os.path.join(SHOT, "machikido_%s_kuguri.png" % key))
    if keisha:
        # ④' 勾配なりの地面を入れて: 正面(マゼンタ — 足元の浮きが抜けて見える)・外の斜め・内の斜め
        e = _earth(keisha, haba, half=W * 0.5 + 2.0)
        V.studio((c.x, mn.y - W * 2.0, c.z), (c.x, c.y, c.z), ortho_scale=W * 1.06, res=(1800, 900))
        _magenta_world()
        V.render(os.path.join(SHOT, "machikido_%s_jiban_elev.png" % key))
        V.studio((mn.x - W * 0.25, mn.y - W * 1.0, 2.2), (c.x, c.y, H * 0.30), res=(1800, 1100))
        V.render(os.path.join(SHOT, "machikido_%s_jiban_3d.png" % key))
        V.studio((mx.x + W * 0.25, mx.y + W * 1.0, 2.4), (c.x, c.y, H * 0.30), res=(1800, 1100))
        V.render(os.path.join(SHOT, "machikido_%s_jiban_ura.png" % key))
        # 足元の寄り(下手の端・上手の端・大戸の口)
        for tag, bx in (("shimote", mn.x + 0.9), ("kamite", mx.x - 0.9), ("kuchi", 0.0)):
            gz = keisha * bx / haba
            V.studio((bx - 1.6, mn.y - 3.2, gz + 1.0), (bx, 0.0, gz + 0.3), res=(1200, 900))
            V.render(os.path.join(SHOT, "machikido_%s_ashi_%s.png" % (key, tag)))
        bpy.data.objects.remove(e, do_unlink=True)
    # ⑤ 札の線を重ねる(真上寄りの斜め・正面)
    ov = K.overlay(spec)
    V.studio((c.x, mn.y - W * 2.0, c.z), (c.x, c.y, c.z), ortho_scale=W * 1.06, res=(1800, 900))
    V.render(os.path.join(SHOT, "machikido_%s_spec_elev.png" % key))
    V.studio((mn.x - W * 0.3, mn.y - W * 0.6, W * 0.7), (c.x, c.y - 0.6, 0.5), res=(1800, 1100))
    V.render(os.path.join(SHOT, "machikido_%s_spec_3d.png" % key))
    for x in ov:
        bpy.data.objects.remove(x, do_unlink=True)
    # ⑥ 在庫の路地木戸と並べる(左 = 在庫・右 = 新造)
    st = _stock(mn.x - 3.5)
    mn2, mx2 = V.bbox([o, st])
    c2 = (mn2 + mx2) * 0.5
    V.studio((c2.x, mn2.y - 40.0, 1.7), (c2.x, c2.y, 1.7),
             ortho_scale=(mx2.x - mn2.x) * 1.05, res=(2000, 700))
    V.render(os.path.join(SHOT, "machikido_%s_narabe.png" % key))
    bpy.data.objects.remove(st, do_unlink=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    def opt(f, d=None, cast=str):
        return cast(argv[argv.index(f) + 1]) if f in argv else d
    haba = opt("--haba", 10.54, float)
    kug = opt("--kuguri", "L")
    opened = "--shut" not in argv
    keisha = opt("--keisha", 0.0, float)
    if "--spec-only" in argv:
        _o, name, spec = build(haba, kug, opened, spec_only=True, keisha=keisha)
        V.write_spec(os.path.join(OUT, name + ".fbx"), spec)
        return
    V.reset()
    o, name, spec = build(haba, kug, opened, want_spec=True, keisha=keisha)
    mn, mx = V.bbox([o])
    print("[machikido] %s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  底=%.3f  面=%d"
          % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
    print("[machikido] 材質=%s" % [mm.name for mm in o.data.materials])
    if "--render" in argv:
        shots(o, spec, name[len("MachiKido_"):].lower(), keisha=keisha, haba=haba)
    path = os.path.join(OUT, name + ".fbx")
    V.export_fbx([o], path, kind="gate", spec=spec)
    print("[machikido] 書き出し " + path)


if __name__ == "__main__":
    main()
