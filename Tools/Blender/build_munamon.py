"""**通用口の棟門**を起こす。岡部筑前守上屋敷 `komon.Tsuyodo`(袋小路に開く勝手口)。

    blender --background --python Tools/Blender/build_munamon.py -- [--w 2.7] [--render]
    blender --background --python Tools/Blender/build_munamon.py -- --w 2.727 --spec-only
    blender --background --python Tools/Blender/build_munamon.py -- --w 2.727 --sode 0.30 --render
        # 両脇に短い板の袖(方立+袖板)を足した版 Munamon_2.73_Sode0.3(_Open)── 岡部の通用門(EDO-0502 2026-10-11)
    (`--spec-only` = FBX を焼き直さず、部材の札 `Assets/Edo/Data/PartSpecs/<名>.json` だけ書く。EDO-0491)

【なぜ新造するか】在庫の門は薬医門(`es_kmon`)・冠木門(`es_kabukimon`)・城門で、
  **棟門(二本の本柱の上に直に棟を載せる最も簡素な門)は無い**。通用口に薬医門を据えると
  格が上がりすぎる — 指図 `komon` は型式を「棟門」と宣言している(⚠ 型式の典拠は未確認=U)。

【寸法】門口の幅 **2.7m** は指図 `komon[].w` が正典。ここで決めない。
  ⚠ 以下は**指図に無いので仮置き【U】**。普請奉行へ返して指図へ書き戻すこと:
    ・棟天端 **3.60**(呼び出し元の指定)
    ・本柱 **0.24角**。⚠ 指定は「φ0.24」だったが、**門の本柱は角柱**が常法なので
      0.24 を角の寸法として採った(丸柱にすると鳥居か門柱と読み違える)
    ・冠木の下端(門口の有効高)**2.40** / 桁の天端 **3.00** / 梁間 **1.30** / 軒の出 **0.55**
    ・板戸は両開き・高さ **2.30**・**内開き**(武家屋敷の門の常法)
  屋根の勾配は Village Kit の `roof 2x2` の実測 **0.5456(5.5寸)に固定**(README)。

【向き(Unity 座標)】幅=X(門口の方向)/ 高さ=Y / 厚み=Z。**+Z = 外(袋小路の側)**。
  扉は**内開き**なので、開いた版の扉は **−Z(敷地の内側)** へ振れる。
  ピボット = **門の芯・敷居レベル**。指図 `komon[].sill`(16.06)をそのまま y に使える。

【2バリアント】`Munamon_<w>.fbx`(閉)と `Munamon_<w>_Open.fbx`(開・振れ角 78°)。
  ⚠ 開いた版は扉が −Z へ 1.3m ほど張り出す。据える所の内側にその余地が要る。

【材】`wood` / `wall C` / `Foundation_A_01`(いずれも Village Kit)+ 屋根は `roof`。
  ⛔ 新規マテリアルを作らない。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as R
import build_obi_nagaya as N          # 屋根・妻まわり・材の借用を使い回す

# ⛔ `V.out_dir` を通す(README の BUZAI_OUT 規約。通さないと staging へ逃がせない)
OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Mon"))
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD, WALL, STONE = N.WOOD, N.WALL, N.STONE

POST   = 0.24        # 本柱【U — 「φ0.24」を角柱の見付として採った】
KABUKI = 2.40        # 冠木の下端 = 門口の有効高【U】
KEATS  = 3.00        # 桁の天端(=軒桁の線)【U】
DEEP   = 1.30        # 梁間【U】
NOKI   = 0.55        # 軒の出【U】
END    = 0.28        # けらばの出【U】
RIDGE  = 3.60        # 棟天端【U — 呼び出し元の指定。指図に無い】
DOOR_H = 2.34        # 板戸の丈【U】= 冠木の下端 − 敷居(実際は KABUKI から算出する)
OPEN_DEG = 78.0      # 開いた版の振れ角【U】


def rquad(m, pts, uv, mat, ox, oz, ang):
    """(走り, 高さ, 厚み) の4点を、鉛直軸 (ox, oz) まわりに ang[deg] 回してから積む。
    扉を開いた姿を出すため。⛔ 巻き順は変えない(変えると面が裏返る)。"""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    out = []
    for (x, y, z) in pts:
        dx, dz = x - ox, z - oz
        out.append((ox + dx * c - dz * s, y, oz + dx * s + dz * c))
    m.quad(out, uv, mat)


def rbox(m, x0, x1, y0, y1, z0, z1, uv, mat, ox=0.0, oz=0.0, ang=0.0):
    """回した直方体。`Mesh.box` と同じ面の並び・同じ巻き順"""
    f = [[(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
         [(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)],
         [(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)],
         [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
         [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)],
         [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]]
    for q in f:
        rquad(m, q, uv, mat, ox, oz, ang)


def leaf(m, P, x0, x1, hinge_x, ang, meet=None, top=None):
    """板戸1枚。**竪板と桟を実体で起こす**(渋墨の板戸はテクスチャでは目地が出ない)。
    hinge_x = 吊り元(本柱の内面)。ang>0 で −Z(敷地の内側)へ振れる = 内開き。
    meet = 召し合わせのある側の x(あれば、その裏に定規縁を打つ)。
    ⛔ **突き付けたままにしない** — 2枚のあいだの隙から向こうが透ける(2026-09-04 に実見)。
      縁は**扉に付ける**ので、開いた版でも一緒に振れて隙を追いかける。"""
    t = 0.045
    z1, z0 = -0.02, -0.02 - t                 # 扉の表は敷居の芯より僅かに内側
    # ⚠ 扉の頭は**冠木の下端に合わせる**。DOOR_H を足して決めると 4cm の隙間が残り、
    #   立面で冠木の下に横一文字の光の筋が走る(2026-09-04 に実見)
    # ⛔⛔ **`top` を渡さないと扉が 2.40 で止まる。**2026-09-21、山門(冠木 3.10)を
    #   焼いたら扉の上に **0.76m の横一文字の穴**が開いて空が抜けた(EDO-0318 ①)。
    y0, y1 = 0.06, (KABUKI if top is None else top)
    m_uv = VM.sub(P['wuv'], 0.62, 0.05, 0.80, 0.95)
    rbox(m, x0, x1, y0, y1, z0, z1, m_uv, WOOD, hinge_x, 0.0, ang)
    nb = max(2, int(round((x1 - x0) / 0.30)))
    for b in range(nb):                       # 竪板(見付 0.30・目地 25mm)
        bc = x0 + (x1 - x0) * (b + 0.5) / nb
        bw = (x1 - x0) / nb * 0.90
        rbox(m, bc - bw / 2, bc + bw / 2, y0, y1, z1, z1 + 0.014,
             VM.sub(P['wuv'], 0.64, 0.05, 0.72, 0.95), WOOD, hinge_x, 0.0, ang)
        rbox(m, bc - bw / 2, bc + bw / 2, y0, y1, z0 - 0.014, z0,
             VM.sub(P['wuv'], 0.64, 0.05, 0.72, 0.95), WOOD, hinge_x, 0.0, ang)
    if meet is not None:                      # 召し合わせの定規縁(相手の扉の裏へ回る)
        a, b = sorted((meet, meet + (0.055 if meet < (x0 + x1) / 2 else -0.055)))
        rbox(m, a, b, y0, y1, z0 - 0.032, z0,
             VM.sub(P['wuv'], 0.66, 0.05, 0.74, 0.95), WOOD, hinge_x, 0.0, ang)
    for fz in (0.10, 0.50, 0.90):             # 桟(上・中・下)
        yc = y0 + (y1 - y0) * fz
        for (a, b) in ((z1 + 0.014, z1 + 0.045), (z0 - 0.045, z0 - 0.014)):
            rbox(m, x0, x1, yc - 0.065, yc + 0.065, min(a, b), max(a, b),
                 VM.sub(P['wuv'], 0.72, 0.10, 0.92, 0.45), WOOD, hinge_x, 0.0, ang)


def build(w=2.7, opened=False, name=None, post=None, kabuki=None, keats=None,
          deep=None, noki=None, end=None, ridge=None, hikae=(), hikae_post=None,
          want_spec=False, spec_only=False, source=None, sode=0.0):
    """棟門(既定)と、**控柱を足した薬医門・四脚門**を1本で起こす。

    ⭐ 2026-09-21(EDO-0318 ①)に引数を出した。⛔ **既定はすべて従来の定数**なので、
      岡部の呼び出し(`build(w=2.7)`)の姿は一切動かない。
      <paramref name="hikae"/> = **控柱の z 位置[m]の並び**(本柱の芯が z=0)。
        `()`      → 棟門(本柱2本だけ)
        `(-d,)`   → **薬医門**(本柱の後ろに控柱2本。⭐ 屋根は本柱の上に棟を置いた
                    左右対称の切妻で、控柱は後ろの流れの下に入る — これが薬医門の常法)
        `(-d, d)` → **四脚門**(本柱の前後に控柱4本。寺の山門の格)
      ⚠ 控柱を足したら <paramref name="deep"/> を **2*d + 軒の余地**まで広げること。
        広げないと控柱が軒の外へ出て、雨ざらしの柱に見える。

    ⭐ **札**(EDO-0491): <paramref name="want_spec"/> なら `(o, name, spec)` を返す。
      <paramref name="spec_only"/> なら**メッシュを起こさず** `(None, name, spec)` を返す
      (出荷済みの FBX を焼き直さずに札だけを書く道)。札は `gate_spec()` が**作図の変数から**出す。

    ⭐ <paramref name="sode"/>(EDO-0502 2026-10-11 岡部の通用門 Tsuyomon): 本柱の外の面から両脇へ sode[m] の**短い板の袖**
      (竪板の袖板+長屋の妻に当たる方立)を足す。門の柱と長屋の妻の間(指図 komon[Tsuyomon].plan.bayRule の 0.30)を
      地中(沓石の底)から妻梁の下まで塞ぐ。札の脇の面 jamb は**方立の外の面**(= ±(門口/2 + 柱 + sode))へ移る ⇒
      長屋の妻面をそこへ突き付ける。0 なら従来の姿(名も変わらない)。"""
    post = POST if post is None else post
    kabuki = KABUKI if kabuki is None else kabuki
    keats = KEATS if keats is None else keats
    deep = DEEP if deep is None else deep
    noki = NOKI if noki is None else noki
    end = END if end is None else end
    ridge = RIDGE if ridge is None else ridge
    hikae_post = (post * 0.72) if hikae_post is None else hikae_post
    name = name or ("Munamon_" + N.fmt(w) + ("_Sode" + N.fmt(sode) if sode > 0 else "")
                    + ("_Open" if opened else ""))
    spec = gate_spec(name, w, opened, post, kabuki, keats, deep, noki, end, ridge,
                     hikae, hikae_post, source, sode=sode)
    if spec_only:
        return None, name, spec
    P = N.palette()
    m = VM.Mesh()
    hx = w / 2.0                              # 門口の内法の半分
    px = hx + post / 2.0                      # 本柱の芯
    W = w + 2 * post + 0.72                   # 屋根の桁行(柱の外へ 0.36 ずつ出る)
    hw, hd = W / 2.0, deep / 2.0
    roofZ = keats - noki * R.RATIO             # 軒先レベル(桁の線で屋根が壁に合う)
    apex = roofZ + (hd + noki) * R.RATIO

    # ---- 沓石(礎盤)と本柱
    for s in (-1, 1):
        m.box(s * px - 0.24, s * px + 0.24, -0.26, 0.05, -0.24, 0.24,
              VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)
        m.box(s * px - post / 2, s * px + post / 2, 0.02, keats, -post / 2, post / 2,
              VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
    # ---- 控柱(薬医門・四脚門)。本柱より細く、**桁ではなく梁で本柱へ繋ぐ**
    for dz in hikae:
        for s in (-1, 1):
            m.box(s * px - 0.20, s * px + 0.20, -0.26, 0.05, dz - 0.20, dz + 0.20,
                  VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)                     # 沓石
            m.box(s * px - hikae_post / 2, s * px + hikae_post / 2, 0.02, keats - 0.22,
                  dz - hikae_post / 2, dz + hikae_post / 2,
                  VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)            # 控柱
            # 本柱と控柱を繋ぐ**繋ぎ梁**。⛔ 抜くと控柱が独立して立つ棒に見える
            lo, hi = sorted((0.0, dz))
            m.box(s * px - 0.09, s * px + 0.09, keats - 0.52, keats - 0.28, lo, hi,
                  VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)
    # ---- 冠木(本柱を貫いて左右へ出る)+ 上の小壁 + 桁 + 妻梁
    m.box(-px - 0.34, px + 0.34, kabuki, kabuki + 0.30, -0.15, 0.15,
          VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.50), WOOD)
    # 小壁(漆喰)。⚠ 見込みを 0.18 まで取り、**天井板と併せて冠木の上を塞ぐ** —
    # 薄い板1枚だと冠木と軒のあいだが横一文字の隙間になって、門越しに空が抜ける
    # (2026-09-04 に実見)。棟門の小屋裏は化粧屋根裏か天井板で塞ぐのが常法。
    m.box(-px - 0.02, px + 0.02, kabuki + 0.28, keats, -0.18, 0.18,
          VM.sub(P['cuv'], 0.05, 0.05, 0.95, 0.95), WALL)
    m.box(-hw + 0.12, hw - 0.12, keats - 0.05, keats, -hd + 0.02, hd - 0.02,
          VM.sub(P['wuv'], 0.05, 0.10, 0.95, 0.55), WOOD)      # 天井板(門の下から見上げる面)
    for s in (-1, 1):
        m.box(-hw + 0.10, hw - 0.10, keats - 0.16, keats, s * hd - s * 0.10, s * hd,
              VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)  # 桁
        m.box(s * hw + s * 0.02 - s * 0.12, s * hw + s * 0.02, keats - 0.16, keats,
              -hd, hd, VM.sub(P['wuv'], 0.30, 0.15, 0.90, 0.45), WOOD)   # 妻梁
    # ---- 短い板の袖(sode > 0)。本柱の外の面 → 長屋の妻まで。⛔ 新しい材は作らない(wood の板目を借りる)
    if sode > 0:
        jx = hx + post                         # 本柱の外の面
        yb, yt = -KUTSU_H, keats - 0.16        # 沓石の底(地中)〜 妻梁の下
        for sg in (-1, 1):
            a, b = jx, jx + sode - SODE_HOU     # 袖板の x(本柱の外の面 → 方立の内の面)
            # 方立(長屋の妻に当たる見付 SODE_HOU の柱)
            m.box(*sorted((sg * (jx + sode - SODE_HOU), sg * (jx + sode))), yb, yt, -SODE_HOU_D / 2, SODE_HOU_D / 2,
                  VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
            # 袖板(竪板。表裏に目板を打つ ── 一枚板の箱に見せない)
            m.box(*sorted((sg * a, sg * b)), yb, yt, -SODE_T / 2, SODE_T / 2,
                  VM.sub(P['wuv'], 0.62, 0.05, 0.80, 0.95), WOOD)
            xc = sg * (a + b) / 2
            for zf in (SODE_T / 2, -SODE_T / 2 - 0.014):
                m.box(xc - 0.025, xc + 0.025, yb + 0.26, yt, zf, zf + 0.014,
                      VM.sub(P['wuv'], 0.64, 0.05, 0.72, 0.95), WOOD)
            # 貫(上・下)── 本柱と方立を繋ぐ
            for yc in (0.35, yt - 0.35):
                m.box(*sorted((sg * a, sg * b)), yc - 0.05, yc + 0.05, -SODE_T / 2 - 0.02, SODE_T / 2 + 0.02,
                      VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)

    # ---- 敷居(門口の足元)。⛔ 抜けたままにしない
    m.box(-px, px, -0.04, 0.06, -0.16, 0.16,
          VM.sub(P['wuv'], 0.30, 0.10, 0.85, 0.30), WOOD)

    # ---- 板戸(両開き・内開き)。⚠ 開いた版は −Z へ振れる
    ang = OPEN_DEG if opened else 0.0
    # ⚠ **召し合わせに隙を取る。**2枚を突き付けると立面で1枚の板壁に見える
    GAP = LEAF_GAP
    leaf(m, P, -hx, -GAP, -hx, -ang, top=kabuki)
    leaf(m, P, GAP, hx, hx, ang, meet=GAP, top=kabuki)

    # ---- 妻まわり(妻壁・けらば裏板・破風)は詰人長屋と同じ作り
    N.gable_set(m, P, hw, hd, keats, roofZ, apex, noki, end=end)

    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone']])
    show = ridge - apex + N.SEAT               # 熨斗の見え掛かりで棟天端を ridge に合わせる
    roof = N.obi_roof(W, deep, name + "_roof", P, ridge_show=show - N.SEAT,
                      noki=noki, end=end)
    roof.location = (0.0, 0.0, roofZ)
    bpy.context.view_layer.update()
    V.sel([roof])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.dedup_materials()
    o = V.join([body, roof], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print("[munamon] %-22s 門口 %.2fm / 有効高 %.2f / 桁 %.2f / 瓦の大棟 %.3f / 控柱 %d本"
          % (name, w, kabuki, keats, apex, 2 * len(hikae)))
    return (o, name, spec) if want_spec else (o, name)


# ---- 短い板の袖(sode > 0)の寸法【U ── 指図に無い・部材方の仮置き】
SODE_HOU, SODE_HOU_D = 0.09, 0.12              # 方立の見付・見込
SODE_T = 0.04                                  # 袖板の厚み

# ---- 板戸の寸法(`leaf()` と同じ値。札の計算が読む)
LEAF_GAP = 0.012                               # 召し合わせの隙(build の GAP)
LEAF_Z1, LEAF_Z0 = -0.02, -0.065               # 扉の表・裏(leaf の z1, z0 = z1 − t)
LEAF_ZF, LEAF_ZB = LEAF_Z1 + 0.045, LEAF_Z0 - 0.045   # 桟の外の面(表・裏)
KUTSU, KUTSU_H = 0.24, 0.26                    # 本柱の沓石の半幅・敷居からの根入れ
KUTSU_HK = 0.20                                # 控柱の沓石の半幅


def _hull(pts):
    """凸包(反時計回り・monotone chain)。pts = [(x, z)]"""
    P = sorted(set(pts))
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def gate_spec(name, w, opened, post, kabuki, keats, deep, noki, end, ridge,
              hikae, hikae_post, source=None, sode=0.0):
    """門の**札**を**作図の変数から**出す(EDO-0491)。⛔ メッシュを測らない。

    座標は Unity の資産の局所(+X=門口・+Z=外・原点=門の芯・敷居の高さ)。`build()` の
    `VM.Mesh` の (走り, 高さ, 厚み) がそのまま (x, y, z) になる(⚠ Unity の取り込みで x は
    反転するが、門は左右対称なので札の値は変わらない)。各欄の意味は `EdoPartSpec.Measure`:
      yBottom = 沓石の底 / foot = 沓石の平面の凸包 / front・back = 袖の帯(底+0.30〜1.80)の z の端
      jambL/R = 帯の中でいちばん内へ引っ込む段の x(= 本柱の外の面)/ passage = 本柱の内の面
      eave = 軒込みの外接(けらば・軒の出・棟天端)"""
    hx = w / 2.0
    px = hx + post / 2.0
    W = w + 2 * post + 0.72
    hw, hd = W / 2.0, deep / 2.0
    yb = -KUTSU_H
    band0, band1 = yb + 0.30, yb + 1.80        # EdoPartSpec.BAND_LO / BAND_HI(帯の下端・上端)
    # 足元 = 沓石(本柱・控柱)の平面
    stones = [(s * px, 0.0, KUTSU) for s in (-1, 1)]
    stones += [(s * px, dz, KUTSU_HK) for dz in hikae for s in (-1, 1)]
    corners = [(cx + a * r, cz + b * r) for (cx, cz, r) in stones for a in (-1, 1) for b in (-1, 1)]
    if sode > 0:                               # 袖の方立の足元(袖板は方立の見込の内)
        corners += [(s * (hx + post + sode), z) for s in (-1, 1) for z in (-SODE_HOU_D / 2, SODE_HOU_D / 2)]
    foot = [{"x": x, "y": z} for (x, z) in _hull(corners)]
    # 帯の z の端: 沓石(帯の最下段 = 底+0.30 は沓石の天端 0.05 の下を切る)・本柱・控柱・敷居・板戸
    zs = [z for (_x, z) in corners] + [post / 2, -post / 2, 0.16, -0.16, LEAF_ZF, LEAF_ZB]
    for dz in hikae:
        zs += [dz + hikae_post / 2, dz - hikae_post / 2]
    if opened:                                 # 開いた扉は吊り元まわりに ±OPEN_DEG 振れる(内開き = −Z)
        a = math.radians(OPEN_DEG)
        c, sn = math.cos(a), math.sin(a)
        for x in (-hx, -LEAF_GAP, LEAF_GAP, hx):
            hinge = -hx if x < 0 else hx
            ang_s = -sn if x < 0 else sn
            for z in (LEAF_ZF, LEAF_ZB):
                zs.append((x - hinge) * ang_s + z * c)
    jx = hx + post                             # 本柱の外の面(帯の全段で最も内へ引っ込む)
    # 脇の面の z = その x の ±0.15 に入る断面の点(本柱・沓石・控柱とその沓石・敷居の端)
    jz = [post / 2, -post / 2]
    if KUTSU - post / 2 <= 0.15:
        jz += [KUTSU, -KUTSU]
    for dz in hikae:
        if KUTSU_HK - post / 2 <= 0.15:
            jz += [dz + KUTSU_HK, dz - KUTSU_HK]
        if post / 2 - hikae_post / 2 <= 0.15:
            jz += [dz + hikae_post / 2, dz - hikae_post / 2]
    if sode > 0:                               # 脇の面 = 方立の外の面(長屋の妻はここへ突き付く)
        jx, jz = hx + post + sode, [SODE_HOU_D / 2, -SODE_HOU_D / 2]
    jamb = lambda x: {"x": x, "z0": min(jz), "z1": max(jz), "y0": band0, "y1": band1}
    src = source or ("blender:build_munamon.py build(w=%g, opened=%s, post=%g, kabuki=%g, keats=%g, "
                     "deep=%g, noki=%g, ridge=%g, hikae=%s%s)"
                     % (w, opened, post, kabuki, keats, deep, noki, ridge, tuple(hikae),
                        (", sode=%g" % sode) if sode > 0 else ""))
    return {
        "prefab": "Assets/Edo/Models/Mon/%s.fbx" % name,
        "kind": "gate", "source": src, "unitScale": 1.0,
        "yBottom": yb, "foot": foot,
        "front": max(zs), "back": min(zs),
        "jambL": jamb(-jx), "jambR": jamb(jx),
        "passage": {"x0": -hx, "x1": hx},
        # ⚠ 開いた版は扉が軒の外(−Z)へ振れ出るので、外接は扉と沓石まで含める
        "eave": {"x0": min(-hw - end, -px - KUTSU, -(hx + post + sode)), "x1": max(hw + end, px + KUTSU, hx + post + sode),
                 "z0": min(-hd - noki, min(zs)), "z1": max(hd + noki, max(zs)),
                 "y0": yb, "y1": ridge},
        "height": ridge - yb,
    }


def shots(o, key):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    H = mx.z - mn.z
    r = max(mx.x - mn.x, mx.y - mn.y, H)
    # ① 外(袋小路側)からの正面立面。⚠ 表は Blender の −Y(厚みを反転して出すため)
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=max(mx.x - mn.x, H) * 1.15, res=(1400, 1200))
    V.render(os.path.join(SHOT, "munamon_%s_elev.png" % key))
    # ② 外から斜め(人の目の高さ)
    V.studio((mn.x - r * 0.5, mn.y - r * 1.1, 1.65), (c.x, c.y, H * 0.45), res=(1600, 1100))
    V.render(os.path.join(SHOT, "munamon_%s_3d.png" % key))
    # ③ 内(敷地側)から斜め — 扉の裏・棟の小口・妻を見る
    V.studio((mx.x + r * 0.5, mx.y + r * 1.1, 1.9), (c.x, c.y, H * 0.5), res=(1600, 1100))
    V.render(os.path.join(SHOT, "munamon_%s_ura.png" % key))
    # ④ 妻の正面立面 — 妻壁が塞がっているか
    V.studio((mn.x - r * 2.4, c.y, c.z), (c.x, c.y, c.z),
             ortho_scale=max(mx.y - mn.y, H) * 1.18, res=(1200, 1200))
    V.render(os.path.join(SHOT, "munamon_%s_gable.png" % key))


def main():
    """`--spec-only` = FBX を焼き直さず札だけを書く(出荷済みの FBX は 2026-09-04 の Blender で焼いたもの)。"""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    w = float(argv[argv.index("--w") + 1]) if "--w" in argv else 2.7
    sode = float(argv[argv.index("--sode") + 1]) if "--sode" in argv else 0.0
    for opened in (False, True):
        if "--spec-only" in argv:
            _o, name, spec = build(w, opened, spec_only=True, sode=sode)
            V.write_spec(os.path.join(OUT, name + ".fbx"), spec)
            continue
        V.reset()
        o, name, spec = build(w, opened, want_spec=True, sode=sode)
        mn, mx = V.bbox([o])
        print("[munamon] %-18s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f   底=%.3f  面=%d"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
        print("[munamon] %-18s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path, kind="gate", spec=spec)
        print("[munamon] 書き出し " + path)
        if "--render" in argv:
            shots(o, ("sode_" if sode > 0 else "") + ("open" if opened else "shut"))


if __name__ == "__main__":
    main()
