"""**通用口の棟門**を起こす。岡部筑前守上屋敷 `komon.Tsuyodo`(袋小路に開く勝手口)。

    blender --background --python Tools/Blender/build_munamon.py -- [--w 2.7] [--render]

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

OUT  = os.path.join(V.REPO, "Assets", "Edo", "Models", "Mon")
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


def leaf(m, P, x0, x1, hinge_x, ang, meet=None):
    """板戸1枚。**竪板と桟を実体で起こす**(渋墨の板戸はテクスチャでは目地が出ない)。
    hinge_x = 吊り元(本柱の内面)。ang>0 で −Z(敷地の内側)へ振れる = 内開き。
    meet = 召し合わせのある側の x(あれば、その裏に定規縁を打つ)。
    ⛔ **突き付けたままにしない** — 2枚のあいだの隙から向こうが透ける(2026-09-04 に実見)。
      縁は**扉に付ける**ので、開いた版でも一緒に振れて隙を追いかける。"""
    t = 0.045
    z1, z0 = -0.02, -0.02 - t                 # 扉の表は敷居の芯より僅かに内側
    # ⚠ 扉の頭は**冠木の下端に合わせる**。DOOR_H を足して決めると 4cm の隙間が残り、
    #   立面で冠木の下に横一文字の光の筋が走る(2026-09-04 に実見)
    y0, y1 = 0.06, KABUKI
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


def build(w=2.7, opened=False, name=None):
    name = name or ("Munamon_" + N.fmt(w) + ("_Open" if opened else ""))
    P = N.palette()
    m = VM.Mesh()
    hx = w / 2.0                              # 門口の内法の半分
    px = hx + POST / 2.0                      # 本柱の芯
    W = w + 2 * POST + 0.72                   # 屋根の桁行(柱の外へ 0.36 ずつ出る)
    hw, hd = W / 2.0, DEEP / 2.0
    roofZ = KEATS - NOKI * R.RATIO             # 軒先レベル(桁の線で屋根が壁に合う)
    apex = roofZ + (hd + NOKI) * R.RATIO

    # ---- 沓石(礎盤)と本柱
    for s in (-1, 1):
        m.box(s * px - 0.24, s * px + 0.24, -0.26, 0.05, -0.24, 0.24,
              VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)
        m.box(s * px - POST / 2, s * px + POST / 2, 0.02, KEATS, -POST / 2, POST / 2,
              VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
    # ---- 冠木(本柱を貫いて左右へ出る)+ 上の小壁 + 桁 + 妻梁
    m.box(-px - 0.34, px + 0.34, KABUKI, KABUKI + 0.30, -0.15, 0.15,
          VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.50), WOOD)
    # 小壁(漆喰)。⚠ 見込みを 0.18 まで取り、**天井板と併せて冠木の上を塞ぐ** —
    # 薄い板1枚だと冠木と軒のあいだが横一文字の隙間になって、門越しに空が抜ける
    # (2026-09-04 に実見)。棟門の小屋裏は化粧屋根裏か天井板で塞ぐのが常法。
    m.box(-px - 0.02, px + 0.02, KABUKI + 0.28, KEATS, -0.18, 0.18,
          VM.sub(P['cuv'], 0.05, 0.05, 0.95, 0.95), WALL)
    m.box(-hw + 0.12, hw - 0.12, KEATS - 0.05, KEATS, -hd + 0.02, hd - 0.02,
          VM.sub(P['wuv'], 0.05, 0.10, 0.95, 0.55), WOOD)      # 天井板(門の下から見上げる面)
    for s in (-1, 1):
        m.box(-hw + 0.10, hw - 0.10, KEATS - 0.16, KEATS, s * hd - s * 0.10, s * hd,
              VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)  # 桁
        m.box(s * hw + s * 0.02 - s * 0.12, s * hw + s * 0.02, KEATS - 0.16, KEATS,
              -hd, hd, VM.sub(P['wuv'], 0.30, 0.15, 0.90, 0.45), WOOD)   # 妻梁
    # ---- 敷居(門口の足元)。⛔ 抜けたままにしない
    m.box(-px, px, -0.04, 0.06, -0.16, 0.16,
          VM.sub(P['wuv'], 0.30, 0.10, 0.85, 0.30), WOOD)

    # ---- 板戸(両開き・内開き)。⚠ 開いた版は −Z へ振れる
    ang = OPEN_DEG if opened else 0.0
    # ⚠ **召し合わせに隙を取る。**2枚を突き付けると立面で1枚の板壁に見える
    GAP = 0.012
    leaf(m, P, -hx, -GAP, -hx, -ang)
    leaf(m, P, GAP, hx, hx, ang, meet=GAP)

    # ---- 妻まわり(妻壁・けらば裏板・破風)は詰人長屋と同じ作り
    N.gable_set(m, P, hw, hd, KEATS, roofZ, apex, NOKI, end=END)

    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone']])
    show = RIDGE - apex + N.SEAT               # 熨斗の見え掛かりで棟天端を 3.60 に合わせる
    keep_end = N.END
    N.END = END
    try:
        roof = N.obi_roof(W, DEEP, name + "_roof", P, ridge_show=show - N.SEAT, noki=NOKI)
    finally:
        N.END = keep_end
    roof.location = (0.0, 0.0, roofZ)
    bpy.context.view_layer.update()
    V.sel([roof])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.dedup_materials()
    o = V.join([body, roof], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print("[munamon] %-18s 門口 %.2fm / 有効高 %.2f / 桁 %.2f / 瓦の大棟 %.3f"
          % (name, w, KABUKI, KEATS, apex))
    return o, name


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
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    w = float(argv[argv.index("--w") + 1]) if "--w" in argv else 2.7
    for opened in (False, True):
        V.reset()
        o, name = build(w, opened)
        mn, mx = V.bbox([o])
        print("[munamon] %-18s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f   底=%.3f  面=%d"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
        print("[munamon] %-18s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)
        print("[munamon] 書き出し " + path)
        if "--render" in argv:
            shots(o, "open" if opened else "shut")


if __name__ == "__main__":
    main()
