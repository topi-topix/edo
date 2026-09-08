"""**袖塀**(長さ可変・潜り戸つき)— 門の脇で外周を塞ぐ練塀。

    blender --background --python Tools/Blender/build_sodebei.py -- <長さm> [--kuguri <中心m>] [--render]
    blender --background --python Tools/Blender/build_sodebei.py -- 4.25 --kuguri 2.125 --render

【なぜ独立部材にするか(2026-09-08・第28次)】
  従前は `build_matsudaira_omotemon.py` が**門柱・冠木・扉と袖塀を一体**で焼いていた。
  指図 第28次で表門の並びが
    **表長屋 → 袖塀(潜り戸)→ 番所(街路へ張出)→ 門柱 → 門柱 → 番所 → 袖塀 → 表長屋**
  に改まり、⭐ **番所は門柱へ直付け**([松江上屋敷門写真]A)になったので、
  袖塀は**番所と表長屋のあいだ**へ移った。門の部材が抱えていては据えられない。
  ⇒ 門からは外し、**長さを引数で受ける独立部材**にする(外周の練塀と同じ作法)。

【⛔ 既定値を置かない】
  長さは指図 `gate.plan.sPos.sodeW` / `sodeE` の**従属値**で、いま指図方が決め直している
  最中(考証方が「番所の幅を実測図の開口へ詰めるべき」と判定した係争中・
  `_pending.omotemonZuKaishaku`)。⛔ **ここで長さを発明しない。**引数が無ければ落ちる。
  潜り戸の**位置**も同じく引数(⚠ 左右どちらの袖塀に付くかは写真から読めない【U】)。

【作り】外周の練塀とまったく同じ断面を `build_dobei` から借りる(⛔ 同じ型を二度書かない):
  下見板(腰)→ 貫 → 白漆喰の大壁 → **キットの実ジオメトリの本瓦**(両流れ)→ 熨斗の大棟。
  ⛔ 瓦を自前の半円筒に置き換えない(2026-08-16「ダサい」で却下)。
  端は**袖瓦**(けらば役物)で両端とも塞ぐ。⛔ 木の破風は付かない(土と瓦だけ)。
  大棟の小口は `roof top x1` が開いているので**漆喰で2段に塗り籠める**
  (熨斗=幅広・冠瓦=幅狭。1つの箱だと角が profile から飛び出す。build_noshibei と同じ)。

【丈】`const.dobeiH` = **2.65**(指図 `_pending.omotemonSodeBuzai` の指定)。
  ⚠ 練塀の部材 `Dobei2m` は 2.50 なので、**軒桁だけを上げて**天端を 2.65 に合わせる
  (⛔ 全体を拡大しない — 瓦の割付と勾配はモジュールから来ていて動かせない)。
  上げ量は焼いた実測から自動で決める(`_calibrate`)。

【潜り戸】寸法は**従前の一体部材の実測をそのまま**運ぶ:幅 **0.95** × 有効高 **1.85**
  (`build_matsudaira_omotemon.KUGURI_W/H`。⛔ 新しい数値を作らない)。
  ⛔ 0.9m 級を両開きにしない(README)— **一枚戸**に方立と楣を回す。

【向きとピボット(Unity 座標)】幅=X(走り)/ 高さ=Y / 厚み=Z。
  ⭐ ピボット = **走りの起点(x=0)の小口面・厚みの芯・地盤レベル**。
  ⛔ 中心ピボットにしない — 据える側は**面**で寄せる(CLAUDE.md 規則5)。
    x=0 の面を番所の外側の妻面へ突き付ければ、反対の小口が x=L に来る。
  ⚠ 走りの座標 `a` は**潜り戸の中心もこの起点から**測る。
  ⚠⚠ **Unity X = −(Blender X)**(`V.export_fbx` の axis 規約。build_goten_roof の「軸の鎖」)。
    ⇒ 本体は `_MirrorMesh` が論理走り a を Blender x = −a へ写し、
      同時に面の巻き順を反転して法線を外向きに保つ。
      屋根(`tile_field` / `ridge`)には**はじめから Blender 座標(x∈[−L,0])**を渡す。
    ⛔ 非対称な部材なので、ここを端折ると潜り戸が反対の袖へ出る。

【材】⛔ 新規マテリアルを作らない。`build_dobei` と同じ借り先:
  木 `Fence_B_01`(Village Kit) / 漆喰 `Wall Exterior Defence`(Japanese Castle) / 瓦 `roof`。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_dobei as D
import build_matsudaira_omotemon as OM

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")

H_TOTAL = 2.65          # 指図 const.dobeiH。⛔ ここで作り直さない
KUGURI_W = OM.KUGURI_W  # 0.95 — 従前の一体部材の実測
KUGURI_H = OM.KUGURI_H  # 1.85 — 同上
JAMB = 0.10             # 方立の見付【U】
LINTEL = 0.14           # 楣の丈【U】
T_DOOR = 0.10           # 潜り戸の板厚【U】

_EAVE_CAL = None        # 軒桁の高さ(天端 2.65 になるよう1度だけ実測で決める)


# ------------------------------------------------------------------ メッシュ
class _MirrorMesh(D.Mesh):
    """論理座標 (走り a, 高さ y, 厚み t) を **Blender (−a, t, y)** へ写す。

    ⚠ x を反転すると巻き順が裏返るので、頂点と UV の並びも一緒に反転して戻す。
      (x 反転 = 鏡映1回・並びの反転 = もう1回 ⇒ 偶数回で法線は外向きのまま)
    ⛔ ここを通さずに `D.slab` などを呼ぶと、Unity で潜り戸が反対の袖へ出る。
    """

    def quad(self, pts, uvs, mat=0):
        i = len(self.v)
        p = list(pts)[::-1]
        self.v += [Vector((-q[0], q[2], q[1])) for q in p]
        self.f.append([i, i + 1, i + 2, i + 3])
        self.uv += list(uvs)[::-1]
        self.mi.append(mat)

    def tri(self, pts, uvs, mat=0):
        i = len(self.v)
        p = list(pts)[::-1]
        self.v += [Vector((-q[0], q[2], q[1])) for q in p]
        self.f.append([i, i + 1, i + 2])
        self.uv += list(uvs)[::-1]
        self.mi.append(mat)


def _slab(m, x0, x1, y0, y1, t, rect, mat, ncol, cap_top=True, rot=False, ends=(True, True)):
    """走り [x0,x1] の直方体。`build_dobei.slab` を長さ可変にしたもの。
    ⚠ `wood` のアトラスは縦木理なので、横板(下見板)は rot=True で軸を入れ替える。"""
    u0, v0, u1, v1 = rect
    h = t / 2.0
    ncol = max(1, int(ncol))
    for j in range(ncol):
        xa = x0 + (x1 - x0) * j / ncol
        xb = x0 + (x1 - x0) * (j + 1) / ncol
        for sz in (-1, 1):
            pts = [(xa, y0, sz * h), (xb, y0, sz * h), (xb, y1, sz * h), (xa, y1, sz * h)]
            if rot:
                uvs = [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
            else:
                uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            m.quad(pts if sz > 0 else pts[::-1], uvs if sz > 0 else uvs[::-1], mat)
    if cap_top:
        m.quad([(x0, y1, -h), (x1, y1, -h), (x1, y1, h), (x0, y1, h)],
               [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat)
    for x, flip, use in ((x0, True, ends[0]), (x1, False, ends[1])):
        if not use:
            continue
        pts = [(x, y0, -h), (x, y0, h), (x, y1, h), (x, y1, -h)]
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        m.quad(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs, mat)


def _wall_cap(m, mat, rect, e, half, z_eave, x0, x1, ncol):
    """壁の天端を屋根の裏なりに立ち上げる(`build_dobei.wall_cap` の長さ可変版)。
    ⚠ 水平に切ると壁の上と屋根の裏に楔形の隙間が空く。"""
    u0, v0, u1, v1 = rect
    zt = lambda t: z_eave + (e - abs(t)) * D.RATIO
    ncol = max(1, int(ncol))
    for j in range(ncol):
        xa = x0 + (x1 - x0) * j / ncol
        xb = x0 + (x1 - x0) * (j + 1) / ncol
        for a, b in ((-half, 0.0), (0.0, half)):
            m.quad([(xa, zt(a), a), (xb, zt(a), a), (xb, zt(b), b), (xa, zt(b), b)],
                   [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat)
    for x, flip in ((x0, True), (x1, False)):
        tri = [(-half, z_eave), (0.0, zt(0.0)), (half, z_eave)]
        pts = [(x, q[1], q[0]) for q in tri]
        uvs = [(u0, v0), (u1, v0), (u1, v1)]
        m.tri(pts[::-1] if flip else pts, uvs[::-1] if flip else uvs, mat)


# ------------------------------------------------------------------ 本体
def _body(L, kuguri, eave, W_UV, WALL_UV, wood, wall, name):
    """腰・貫・大壁・天端。潜り戸があればそこだけ開ける。"""
    m = _MirrorMesh()
    e0 = D.T_ROOF / 2.0
    y_nuki0 = D.H_SHITAMI
    y_nuki1 = D.H_SHITAMI + D.H_NUKI
    h_wall_top = eave + (e0 - D.T_WALL / 2.0) * D.RATIO
    dens = lambda a, b, per: max(1, int(round((b - a) / per)))

    if kuguri is None:
        segs = [(0.0, L, (True, True))]
        g0 = g1 = None
    else:
        g0, g1 = kuguri - KUGURI_W / 2.0, kuguri + KUGURI_W / 2.0
        if g0 - JAMB < 0.20 or g1 + JAMB > L - 0.20:
            raise SystemExit(
                "[sodebei] ⛔ 潜り戸が走りの端に寄りすぎ(L=%.3f / 中心 %.3f)。\n"
                "  開口 0.95 + 方立 0.10×2 + 端の袖 0.20×2 が要る ⇒ 中心は %.3f‥%.3f"
                % (L, kuguri, 0.20 + JAMB + KUGURI_W / 2.0, L - 0.20 - JAMB - KUGURI_W / 2.0))
        segs = [(0.0, g0, (True, True)), (g1, L, (True, True))]

    for (a, b, ends) in segs:
        _slab(m, a, b, 0.0, y_nuki0, D.T_SHITAMI, W_UV, 0,
              dens(a, b, 0.668), cap_top=False, rot=True, ends=ends)
        _slab(m, a, b, y_nuki0, y_nuki1, D.T_NUKI, W_UV, 0,
              dens(a, b, 0.501), cap_top=True, ends=ends)
        _slab(m, a, b, y_nuki1, h_wall_top, D.T_WALL, WALL_UV, 1,
              dens(a, b, 1.002), cap_top=False, ends=ends)

    if kuguri is not None:
        # 方立(木)。⭐ **開口の外側**へ立てる — 内側へ入れると有効幅が 0.95 から痩せる
        #   (⛔ 0.95 は従前の一体部材の実測なので動かせない)。壁より 0.04 出して見切りにする。
        _slab(m, g0 - JAMB, g0, 0.0, KUGURI_H, D.T_WALL + 0.08, W_UV, 0, 1, cap_top=True)
        _slab(m, g1, g1 + JAMB, 0.0, KUGURI_H, D.T_WALL + 0.08, W_UV, 0, 1, cap_top=True)
        # 楣(木)— 開口の頭。方立の外まで通す
        _slab(m, g0 - JAMB, g1 + JAMB, KUGURI_H, KUGURI_H + LINTEL, D.T_WALL + 0.08, W_UV, 0,
              dens(g0, g1, 0.48), cap_top=True)
        # 楣の上の漆喰(小壁)。⛔ 開けたままにすると開口の頭から向こうが透ける
        _slab(m, g0, g1, KUGURI_H + LINTEL, h_wall_top, D.T_WALL, WALL_UV, 1,
              dens(g0, g1, 1.002), cap_top=False, ends=(False, False))
        # 潜り戸(一枚戸)。⛔ 0.9m 級を両開きにしない(README)
        # ⚠ **縦板**にする(rot=False で `wood` の縦木理が丈へ流れる)。横木理にすると
        #   アトラスが板幅へ引き伸ばされて、戸が斑の板1枚に見えた(2026-09-08 の1巡目)。
        _slab(m, g0, g1, 0.0, KUGURI_H, T_DOOR, W_UV, 0,
              4, cap_top=False, ends=(False, False))
        for hy in (0.42, 1.42):                      # 横桟(筋金具の見立て)
            _slab(m, g0, g1, hy, hy + 0.09, T_DOOR + 0.05, W_UV, 0,
                  dens(g0, g1, 0.48), cap_top=True, rot=True, ends=(False, False))

    _wall_cap(m, 1, WALL_UV, e0, D.T_WALL / 2.0, eave, 0.0, L, dens(0.0, L, 0.334))
    return m.build(name + "_body", [wood, wall])


def _roof(L, eave, name):
    """両流れの本瓦 + 熨斗の大棟。**Blender 座標(x ∈ [−L, 0])で組む**。"""
    e = D.T_ROOF / 2.0
    z_ridge = eave + e * D.RATIO
    out = []
    f1 = D.tile_field([(-L, -e), (0.0, -e), (0.0, 0.0), (-L, 0.0)], (0.0, -e), 90, eave, name + "_S")
    f2 = D.tile_field([(0.0, e), (-L, e), (-L, 0.0), (0.0, 0.0)], (0.0, e), 270, eave, name + "_N")
    out += [q for q in (f1, f2) if q]
    mune = D.ridge((-L, 0.0, z_ridge - D.SEAT_MUNE), (0.0, 0.0, z_ridge - D.SEAT_MUNE),
                   name + "_mune", D.W_MUNE, D.H_MUNE)
    for q in mune:
        q.data = q.data.copy()          # ⚠ ridge() は mesh を共有する。複製しないと apply が落ちる
        V.sel([q])
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        D.clip_convex(q, [(-L, -1.0), (0.0, -1.0), (0.0, 1.0), (-L, 1.0)])
    out += [q for q in mune if len(q.data.polygons) > 0]
    return out, z_ridge


def _mune_caps(L, z_ridge, wall, WALL_UV, name):
    """大棟の小口を漆喰で塞ぐ。⚠ `roof top x1` は両端が開いている。
    ⚠ **2段**にする(熨斗=幅広 / 冠瓦=幅狭)。1つの箱だと角が profile から飛び出す。"""
    out = []
    base = z_ridge - D.SEAT_MUNE
    for bx, sg in ((0.0, 1), (-L, -1)):             # Blender x。sg>0 が走りの起点側
        for k, (fw, z0, z1) in enumerate(((0.92, 0.00, 0.56), (0.66, 0.52, 0.98))):
            c = V.box(name + "_cap%s%d" % ("A" if sg > 0 else "B", k),
                      (0.05, D.W_MUNE * fw, D.H_MUNE * (z1 - z0)),
                      (bx - sg * 0.030, 0.0, base + D.H_MUNE * (z0 + z1) * 0.5), wall)
            V.set_uv_rect(c, (WALL_UV[0] + 0.02, WALL_UV[1] + 0.02,
                              WALL_UV[2] - 0.02, WALL_UV[3] - 0.02), axes=('y', 'z'))
            out.append(c)
    return out


def build(L, kuguri=None, eave=None, name=None):
    """袖塀を1体つくる。L と kuguri は**論理走り**(起点 x=0 が Unity ローカル +X の 0)。"""
    name = name or asset_name(L, kuguri)
    V.reset()
    wall, WALL_UV = D.castle_mat(D.PLASTER_SRC, D.PLASTER_MAT, "plaster")
    wood, W_UV = D.vk_mat(D.WOOD_SRC, D.WOOD_MAT, "wood")
    if wood is None or wall is None:
        raise SystemExit("[sodebei] ⛔ マテリアルが取れない(⛔ 新規に作らない)")
    WALL_UV = D.crop(WALL_UV, D.CROP_PLASTER, D.CROP_PLASTER_HI)
    W_UV = D.crop(W_UV, D.CROP_WOOD)

    eave = D.H_KETA if eave is None else eave
    pieces = [_body(L, kuguri, eave, W_UV, WALL_UV, wood, wall, name)]
    roof, z_ridge = _roof(L, eave, name)
    pieces += roof
    pieces += _mune_caps(L, z_ridge, wall, WALL_UV, name)

    # 袖瓦(けらば役物)を両端に。⛔ 木の破風は付けない(土と瓦だけ)
    roofmat = bpy.data.materials.get("roof")
    ruv = V.sample_uv(D.ROOF_MOD, pick_high=True)
    rrect = (ruv[0] - 0.01, ruv[1] - 0.01, ruv[0] + 0.01, ruv[1] + 0.01)
    e = D.T_ROOF / 2.0
    # ⛔ **大棟を跨がせない** — 冠瓦を突き抜けて空へ飛び出す(2026-09-08 の小口レンダで実見)。
    #   棟幅の半分 + 0.03 の脇で止める(README・岡部の帯長屋と同じ作法)。
    mg = _MirrorMesh()
    stop = D.W_MUNE / 2.0 + 0.03
    D.sode_gawara(mg, 0, rrect, D.W_SODE, 0.0, e, eave, z_ridge, stop=stop)
    D.sode_gawara(mg, 0, rrect, L - D.W_SODE, L, e, eave, z_ridge, stop=stop)
    pieces.append(mg.build(name + "_sode", [roofmat or wood]))

    V.dedup_materials()
    o = V.join(pieces, name)
    V.set_origin(o, (0.0, 0.0, 0.0))        # ⭐ 走りの起点・厚みの芯・地盤レベル
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def _calibrate():
    """天端が `H_TOTAL` になる軒桁の高さを**焼いた実測から**決める(1度だけ)。
    ⛔ 目分量で足さない — 大棟の部材が公称よりどれだけ上へ出るかは実測でしか出ない。"""
    global _EAVE_CAL
    if _EAVE_CAL is not None:
        return _EAVE_CAL
    o = build(2.004, None, eave=D.H_KETA, name="__cal")
    mn, mx = V.bbox([o])
    _EAVE_CAL = D.H_KETA + (H_TOTAL - (mx.z - mn.z))
    print("[sodebei] 軒桁の校正: 素の天端 %.3f → 目標 %.3f ⇒ 軒桁 %.3f → %.3f"
          % (mx.z - mn.z, H_TOTAL, D.H_KETA, _EAVE_CAL))
    return _EAVE_CAL


def fmt(x):
    """⚠ **C# の `ToString("0.##")` と丸めを揃える。** Python の `%.2f` は偶数丸めなので
    ちょうど 2.125 のような値で 2.12 / 2.13 に割れ、`EdoAssets.Own.Sodebei` が
    存在しないパスを組む(⛔ 静かに白い模型になる)。"""
    from decimal import Decimal, ROUND_HALF_UP
    s = str(Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def asset_name(L, kuguri=None):
    """⚠ EdoAssets.cs の `Own.Sodebei` が同じ綴りでパスを組む。変えたら両方直す。"""
    return "Sodebei_" + fmt(L) + ("" if kuguri is None else "_K" + fmt(kuguri))


def shots(o, key, box, kuguri):
    V.hook_textures()                                  # Village Kit
    keep = V.TEX
    V.TEX = os.path.join(D.JC, "Textures")             # Japanese Castle の漆喰も結線する
    V.hook_textures()
    V.TEX = keep
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    L = mx.x - mn.x
    H = mx.z - mn.z
    # ① 立面(正投影)。⚠ 縦横比を実寸に合わせないと天端と足元が切れる
    V.studio((c.x, mn.y - 12.0, c.z), (c.x, c.y, c.z),
             ortho_scale=L * 1.06, res=(1700, max(300, int(1700 * H / L * 1.06))))
    V.render(os.path.join(SHOT, "sodebei_%s_elev.png" % key))
    # ② 引きの斜め
    V.studio((mx.x + 3.4, mn.y - 4.6, 3.2), (c.x, c.y, 1.1), res=(1600, 1000))
    V.render(os.path.join(SHOT, "sodebei_%s_3d.png" % key))
    # ③ **小口を真正面から**(正投影)。袖瓦・大棟の詰め・壁の断面が透けていないかはここで見る
    V.studio((mx.x + 8.0, 0.0, H / 2.0), (mx.x, 0.0, H / 2.0),
             ortho_scale=3.3, res=(1100, 1100))
    V.render(os.path.join(SHOT, "sodebei_%s_koguchi.png" % key))
    # ④ 走りの端の寄り(斜め)
    V.studio((mn.x - 1.6, mn.y - 1.7, 2.6), (mn.x + 1.0, c.y, 1.5), res=(1500, 1000))
    V.render(os.path.join(SHOT, "sodebei_%s_end.png" % key))
    # ⑤ 真上(正投影)— 屋根の割付と端の欠けを見る
    V.studio((c.x, c.y, 9.0), (c.x, c.y, 0.0),
             ortho_scale=L * 1.06, res=(1700, max(300, int(1700 * 1.3 / L * 1.06))))
    V.render(os.path.join(SHOT, "sodebei_%s_top.png" % key))
    if kuguri is not None:
        # ⚠ Unity ローカル +X = 論理走り。Blender では x が反転しているので −kuguri
        V.studio((-kuguri + 0.9, mn.y - 3.0, 1.75), (-kuguri, c.y, 1.05), res=(1400, 1050))
        V.render(os.path.join(SHOT, "sodebei_%s_kuguri.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    kuguri = None
    if "--kuguri" in argv:
        i = argv.index("--kuguri")
        kuguri = float(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    lens = [float(a) for a in argv if not a.startswith("--")]
    if not lens:
        raise SystemExit(
            "[sodebei] ⛔ 長さを渡すこと。既定値は置いていない — 長さは指図\n"
            "  `gate.plan.sPos.sodeW`/`sodeE` の従属値で、いま指図方が決め直している。\n"
            "  用例: blender --background --python Tools/Blender/build_sodebei.py -- 4.25 --kuguri 2.13")
    eave = _calibrate()
    for L in lens:
        o = build(L, kuguri, eave=eave)
        name = asset_name(L, kuguri)
        mn, mx = V.bbox([o])
        print("[sodebei] %-22s Unity実寸 W(X)=%.3f H(Y)=%.3f D(Z)=%.3f / 底=%.3f / "
              "ピボット: x=%.3f(走りの起点の小口)z芯=%.3f / 面=%d / 材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z,
                 -mx.x, (mn.y + mx.y) / 2.0, len(o.data.polygons),
                 [mm.name for mm in o.data.materials]))
        if "--render" in argv or "--render" in sys.argv:
            shots(o, fmt(L) + ("" if kuguri is None else "k"), (mn, mx), kuguri)
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)         # ⚠ 書き出すと bbox が潰れる。実測とレンダは先に済ませた
        print("[sodebei] 書き出し " + path)


if __name__ == "__main__":
    main()
