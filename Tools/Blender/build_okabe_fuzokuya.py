"""岡部筑前守上屋敷の**附属屋** — 厩・供待・納戸小屋。

    blender --background --python Tools/Blender/build_okabe_fuzokuya.py -- [名前...] [--render]
    (名前を省くと全部。umaya / tomomachi / nandokoya)

【なぜ新造するか】在庫照会の結果いずれも該当なし(指図の `assetCert` に明記されている)。
  松江松平の `Matsudaira_Koya`(片側開放の作事小屋)が寸法違いで近いが、
  **寸法をいじると棟が伸びて破綻する**ので指図の間数どおりに起こす。

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` が正典】
  ・厩 `service.Umaya`        u 6..10 / v 6..15  = **4間 × 9間**(長手 = v)
  ・供待 `service.Tomomachi`  u 2..5  / v 6..11  = **3間 × 5間**(長手 = v)
  ・納戸小屋 `service.Nando_Nagatsubone` u 9.9..11.4 / v 104..105 = **1.5間 × 1間**・**板葺**

【向きとピボット(Unity 座標)】幅=X(**長手**)/ 高さ=Y / 厚み=Z。
  ピボット = **footprint の中心・地盤レベル**(service の矩形の中心をそのまま使える)。
  **+Z が「開いている/開口のある」側**。⚠ 上の3棟はいずれも長手が v なので、
  据えるときは **ローカル +X を +v へ**向ける yaw を与えること。
  ⚠ 軒は footprint の外へ出る(下の実測を見て離隔を取る)。

【⚠ 指図に無いので仮置き【U】— 普請奉行へ返す】
  ・厩 軒高 2.85 / 馬房の仕切り 4房 / 前面(+Z)は開けて足元に半高の板壁
  ・供待 軒高 2.70 / 前面(+Z)に腰高の吹き放ちと縁、背面は板壁
  ・納戸小屋 軒高 2.05 / **板葺の勾配 0.40(4寸)** — ⛔ 瓦モジュールは使わない
    (`roof 2x2` の勾配は 0.5456 固定で、1間の小屋には棟が高すぎる)
  ・屋根の型はいずれも**切妻**(指図に型式の指定が無い)

【材】`wood` / `wall C` / `Foundation_A_01`(Village Kit)+ 瓦は `roof`。⛔ 新規に作らない。
"""
import bpy, sys, os, math, io
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as R
import build_obi_nagaya as N

KEN = 1.818
OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Fuzokuya")
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD, WALL, STONE = N.WOOD, N.WALL, N.STONE

BASE = 0.22          # 基壇【U】
POST = 0.16          # 柱【U】


def frame(m, P, W, D, eaveH, nx, nz, base=BASE, post=POST):
    """礎石 + 通し柱 + 桁 + 妻梁。小屋の骨は共通なので関数にする"""
    hw, hd = W / 2.0, D / 2.0
    m.box(-hw - 0.13, hw + 0.13, 0.0, base, -hd - 0.13, hd + 0.13,
          VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)
    xs = [-hw + W * i / float(nx) for i in range(nx + 1)]
    zs = [-hd + D * j / float(nz) for j in range(nz + 1)]
    for x in xs:
        for z in (zs[0], zs[-1]):
            m.box(x - 0.26, x + 0.26, base - 0.02, base + 0.16, z - 0.26, z + 0.26,
                  VM.sub(P['suv'], 0, 0.5, 0.5, 1), STONE)         # 玉石の礎石
            m.box(x - post / 2, x + post / 2, base + 0.14, eaveH, z - post / 2, z + post / 2,
                  VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)  # 通し柱
    for z in (zs[0], zs[-1]):
        m.box(-hw - 0.06, hw + 0.06, eaveH - 0.20, eaveH, z - 0.11, z + 0.11,
              VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.45), WOOD)      # 桁
    for x in (-hw, hw):
        m.box(x - 0.11, x + 0.11, eaveH - 0.20, eaveH, -hd, hd,
              VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)      # 妻梁
    return xs, zs


def finish(name, m, P, W, D, eaveH, noki, end, ridge_show, extra=None):
    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    keep = N.END
    N.END = end
    try:
        roof = N.obi_roof(W, D, name + "_roof", P, ridge_show=ridge_show, noki=noki)
    finally:
        N.END = keep
    roof.location = (0.0, 0.0, eaveH - noki * R.RATIO)
    bpy.context.view_layer.update()
    V.sel([roof])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.dedup_materials()
    o = V.join([body, roof] + list(extra or []), name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


# ================================================================ 厩
def umaya(uKen=4, vKen=9, name="Okabe_Umaya"):
    """厩 4×9間。長手 = v。**前面(+Z)は開けて足元に半高の板壁**、馬房を4つに仕切る。
    ⚠ 型・馬房数は【U】— 指図は位置と間数だけを持ち、姿の典拠は無い。"""
    P = N.palette()
    W, D = vKen * KEN, uKen * KEN          # ローカル X = 長手(v)
    EAVE, NOKI, END = 2.85, 0.85, 0.32
    hw, hd = W / 2.0, D / 2.0
    m = VM.Mesh()
    xs, zs = frame(m, P, W, D, EAVE, vKen, uKen)
    apex = EAVE + hd * R.RATIO
    # 背面(−Z)と両妻は板壁(下見板)
    N.shitami(m, P, -hw, hw, BASE, EAVE - 0.20, -hd, -1, 'x')
    for sx, s in ((-hw, -1), (hw, 1)):
        N.shitami(m, P, -hd, hd, BASE, EAVE - 0.20, sx, s, 'z')
    # 前面(+Z)= 吹き放ち。足元に半高の板壁(馬が出ないように)
    N.shitami(m, P, -hw, hw, BASE, 1.35, hd, 1, 'x')
    m.box(-hw, hw, 1.35, 1.44, hd - 0.03, hd + 0.09,
          VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80), WOOD)          # 天端の笠木
    # 馬房の仕切り(4房)。前面から 2/3 だけ入れる
    for i in range(1, 4):
        cx = -hw + W * i / 4.0
        m.box(cx - 0.06, cx + 0.06, BASE, 1.90, -hd * 0.15, hd,
              VM.sub(P['wuv'], 0.45, 0.10, 0.90, 0.60), WOOD)
        m.box(cx - 0.10, cx + 0.10, 1.90, 2.02, -hd * 0.15, hd,
              VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80), WOOD)
    # 飼葉桶を受ける横木(背面側)
    m.box(-hw, hw, 0.95, 1.10, -hd + 0.10, -hd + 0.36,
          VM.sub(P['wuv'], 0.35, 0.20, 0.90, 0.50), WOOD)
    N.gable_set(m, P, hw, hd, EAVE, EAVE - NOKI * R.RATIO, apex, NOKI, end=END)
    return finish(name, m, P, W, D, EAVE, NOKI, END, 0.34), name


# ================================================================ 供待
def tomomachi(uKen=3, vKen=5, name="Okabe_Tomomachi"):
    """供待 3×5間。長手 = v。**前面(+Z)は腰高の吹き放ちに縁**、背面と妻は板壁+漆喰。
    供の者が雨を凌いで待つ小屋。⚠ 姿は【U】。"""
    P = N.palette()
    W, D = vKen * KEN, uKen * KEN
    EAVE, NOKI, END = 2.70, 0.85, 0.32
    hw, hd = W / 2.0, D / 2.0
    m = VM.Mesh()
    frame(m, P, W, D, EAVE, vKen, uKen)
    apex = EAVE + hd * R.RATIO
    for sx, s in ((-hw, -1), (hw, 1)):
        N.shitami(m, P, -hd, hd, BASE, 1.05, sx, s, 'z')
        N.mizukiri(m, P, -hd, hd, 1.05, sx, s, 'z')
        N.plaster(m, P, -hd, hd, 1.05, EAVE - 0.20, sx, s, 'z')
    N.shitami(m, P, -hw, hw, BASE, 1.05, -hd, -1, 'x')
    N.mizukiri(m, P, -hw, hw, 1.05, -hd, -1, 'x')
    N.plaster(m, P, -hw, hw, 1.05, EAVE - 0.20, -hd, -1, 'x')
    # 前面(+Z)= 腰高まで塞いで上は吹き放ち。床は板張りの縁
    N.shitami(m, P, -hw, hw, BASE, 0.72, hd, 1, 'x')
    m.box(-hw, hw, 0.72, 0.80, hd - 0.03, hd + 0.10,
          VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80), WOOD)
    m.box(-hw + 0.06, hw - 0.06, 0.62, 0.72, -hd + 0.20, hd + 0.42,
          VM.sub(P['wuv'], 0.05, 0.10, 0.95, 0.60), WOOD)          # 床板(縁)
    # 吹き放ちの中柱(1間ごと)と無目
    for i in range(1, vKen):
        cx = -hw + W * i / float(vKen)
        m.box(cx - 0.06, cx + 0.06, 0.80, EAVE - 0.20, hd - 0.06, hd + 0.06,
              VM.sub(P['wuv'], 0.12, 0.05, 0.40, 0.95), WOOD)
    N.gable_set(m, P, hw, hd, EAVE, EAVE - NOKI * R.RATIO, apex, NOKI, end=END)
    return finish(name, m, P, W, D, EAVE, NOKI, END, 0.32), name


# ================================================================ 納戸小屋
def nandokoya(uKen=1.5, vKen=1.0, name="Okabe_NandoKoya"):
    """納戸小屋 1.5×1間・**板葺**(指図 `service.Nando_Nagatsubone`「板葺」)。
    長局の物干の道具を仕舞う小屋。⛔ **瓦モジュールを使わない** —
    `roof 2x2` の勾配は 0.5456 固定で、1間の小屋に架けると棟が高すぎる。
    板葺なので勾配は自由に選べる → **0.40(4寸)【U】**。"""
    P = N.palette()
    W, D = uKen * KEN, vKen * KEN          # 長手 = u(1.5間)
    EAVE, NOKI, END, RAT = 2.05, 0.42, 0.22, 0.40
    hw, hd = W / 2.0, D / 2.0
    m = VM.Mesh()
    frame(m, P, W, D, EAVE, 1, 1, base=0.16, post=0.12)
    # 四周の板壁。前面(+Z)に片開きの板戸1枚
    for sx, s in ((-hw, -1), (hw, 1)):
        N.shitami(m, P, -hd, hd, 0.16, EAVE - 0.20, sx, s, 'z', pitch=0.17)
    N.shitami(m, P, -hw, hw, 0.16, EAVE - 0.20, -hd, -1, 'x', pitch=0.17)
    dw = 0.82
    N.shitami(m, P, -hw, -dw / 2, 0.16, EAVE - 0.20, hd, 1, 'x', pitch=0.17)
    N.shitami(m, P, dw / 2, hw, 0.16, EAVE - 0.20, hd, 1, 'x', pitch=0.17)
    m.box(-dw / 2 - 0.04, dw / 2 + 0.04, 1.75, EAVE - 0.20, hd - 0.04, hd + 0.06,
          VM.sub(P['wuv'], 0.30, 0.40, 0.80, 0.60), WOOD)          # 鴨居
    N.door_leaves(m, P, -dw / 2, dw / 2, 0.18, 1.75, hd, 1, n=1)
    # ---- 板葺の切妻。⛔ 瓦を使わない。板を重ねて葺く
    apex = EAVE + (hd + NOKI) * RAT
    ex, ez = hw + END, hd + NOKI
    nb = max(3, int(round((hd + NOKI) / 0.28)))
    for s in (-1, 1):
        for i in range(nb):
            t0, t1 = i / float(nb), (i + 1) / float(nb)
            z0, z1 = s * ez * t0, s * ez * t1
            y0 = apex - abs(z0) * RAT
            y1 = apex - abs(z1) * RAT
            # 板は下の板に 25% 被る(葺き重ね)。⛔ 一枚板で葺かない
            uv = VM.sub(P['wuv'], 0.05, (i % 3) * 0.30, 0.95, (i % 3) * 0.30 + 0.28)
            N.section(m, -ex, ex,
                      [(z0, y0 + 0.03), (z1, y1 + 0.03), (z1, y1 - 0.02), (z0, y0 - 0.02)],
                      uv, WOOD)
    # 棟押え(丸みのある棟木)と、妻の破風
    m.box(-ex, ex, apex + 0.02, apex + 0.14, -0.13, 0.13,
          VM.sub(P['wuv'], 0.60, 0.10, 0.85, 0.60), WOOD)
    for sx, inward in ((-hw, +1), (hw, -1)):
        for s in (-1, 1):
            pts = [(s * hd, EAVE), (s * 0.02, apex - 0.02 * RAT), (0.0, apex), (0.0, EAVE)]
            N.section(m, sx, sx + inward * 0.08, pts,
                      VM.sub(P['wuv'], 0.10, 0.10, 0.90, 0.90), WOOD)
    for sx, inward in ((-ex, +1), (ex, -1)):
        for s in (-1, 1):
            pts = [(0.0, apex + 0.10), (s * ez, apex - ez * RAT + 0.10),
                   (s * ez, apex - ez * RAT - 0.10), (0.0, apex - 0.10)]
            N.section(m, sx, sx + inward * 0.05, pts,
                      VM.sub(P['wuv'], 0.60, 0.02, 0.78, 0.98), WOOD)
    o = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    o.name = name; o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


# ================================================================ 車寄
def kurumayose(uKen=3, vKen=2, name="Okabe_Kurumayose", cut=None):
    """**車寄** 3間(間口・u)× 2間(奥行・v)。指図 `munes[0]` / `roofs.Goten_Kurumayose`
    「⛔ **入母屋を架けない・入側を回さない別種**(3×2間の寄せ)」。
    **四方を開けた寄せ**(柱+頭貫+桁+天井板)に**妻入の切妻**を架ける — 参道から見て
    破風が正面に来るのが車寄の要点。前庭は真砂土の叩きなので**床を張らない**。

    ローカル: **+X = +u(間口)/ +Z = 参道の側(= −v)**。ピボット = footprint の中心・**地盤**レベル。
    ⚠ 玄関棟は +v 側に建つので、据えるときは **ローカル −Z を玄関の面へ**向ける。

    ⚠⚠ **屋根が玄関棟の軒より高くなる。**`EdoGotenKit` は棟の軒先を床+2.577(=地盤+3.197)に
    固定しているが、瓦の勾配は 0.5456 に固定なので、3間の span に切妻を架けると棟天端は
    地盤+4.50 になる(下の実測)。⇒ **車寄の背面の屋根は玄関棟の屋根面へ食い込む。**
    これは実物の車寄の納まりそのものだが、⭕ **普請奉行の裁定事項**として返すこと。
    ⛔ 軒桁を下げて逃げると人がくぐれない(いまの 2.30 で軒先 1.89)。"""
    P = N.palette()
    W, D = uKen * KEN, vKen * KEN          # X=間口 / Z=奥行(棟はこちらへ走る)
    EAVE, NOKI, END = 2.30, 0.75, 0.30
    hw, hd = W / 2.0, D / 2.0
    m = VM.Mesh()
    # 礎石 + 柱(間口に1間ピッチ・奥行の前後2列)。⛔ 壁を張らない
    for i in range(uKen + 1):
        x = -hw + W * i / float(uKen)
        for z in (-hd, hd):
            m.box(x - 0.27, x + 0.27, 0.0, 0.20, z - 0.27, z + 0.27,
                  VM.sub(P['suv'], 0, 0.5, 0.5, 1), STONE)
            m.box(x - 0.10, x + 0.10, 0.18, EAVE, z - 0.10, z + 0.10,
                  VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
    # 頭貫(柱の頭を繋ぐ)+ 桁(棟の走る向き = Z)+ 妻梁(X)
    for z in (-hd, hd):
        m.box(-hw - 0.10, hw + 0.10, EAVE - 0.36, EAVE - 0.18, z - 0.09, z + 0.09,
              VM.sub(P['wuv'], 0.30, 0.15, 0.90, 0.45), WOOD)
    for x in (-hw, hw):
        m.box(x - 0.09, x + 0.09, EAVE - 0.18, EAVE, -hd - 0.10, hd + 0.10,
              VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)
    m.box(-hw + 0.06, hw - 0.06, EAVE - 0.06, EAVE, -hd + 0.06, hd - 0.06,
          VM.sub(P['wuv'], 0.05, 0.10, 0.95, 0.60), WOOD)          # 天井板(見上げ)
    # 妻まわりは棟の走る向き(Z)に対して張る。gable_set は X が棟なので入れ替えて渡す
    apex = EAVE + (hw + NOKI) * R.RATIO
    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    keep = N.END
    N.END = END
    try:
        # 棟は Z(奥行)へ走らせたいので、D=間口 / W=奥行 で焼いてから 90° 回す
        m2 = VM.Mesh()
        N.gable_set(m2, P, hd, hw, EAVE, EAVE - NOKI * R.RATIO, apex, NOKI, end=END)
        gab = m2.to_object(name + "_gable", [P['wood'], P['wall'], P['stone'], P['shoji']])
        roof = N.obi_roof(D, W, name + "_roof", P, ridge_show=0.30, noki=NOKI)
    finally:
        N.END = keep
    roof.location = (0.0, 0.0, EAVE - NOKI * R.RATIO)
    bpy.context.view_layer.update()
    V.sel([roof]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.rotate_z([roof, gab], 90)          # 棟を X → Y(= 論理の奥行)へ
    V.dedup_materials()
    o = V.join([body, gab, roof], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o]); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if cut is not None:                   # 玄関棟の屋根へ差し込むための切り欠き
        kirikaki(o, cut[0], cut[1])
    return o, name



# ================================================================ 車寄の切り欠き
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "okabe_sashizu.json")


def kirikaki_planes(at_v=None, above_y=None):
    """指図 `roofs.Goten_Kurumayose.sashikomi.kirikaki` の規則を**部材ローカルの平面2枚**へ落とす。

    規則(指図が正典・⛔ ここに数値を書き写さない):
      「玄関棟の軒先の線 v ≧ `atV` の側で、面から `aboveY` より上にある車寄の面を切り欠く」

    ⭐ **json から読む**。指図方が数値を直したら、焼き直すだけで部材が追従する
      (⛔ 生成器に写すと指図と部材が別々に動く)。

    【座標の変換】車寄のローカルは **+X=+u / +Z=参道の側(=−v)**、
      書き出しで Unity +Z = Blender −Y に反転しているので **Blender +Y = +v**。
      ピボットは footprint の中心なので v の原点は `munes.Kurumayose` の中心。
        Blender y = (v − v中心) × 1.818   /   Blender z = 面からの高さ
    """
    import json
    d = json.load(io.open(SASHIZU, encoding="utf-8"))
    kk = d["roofs"]["Goten_Kurumayose"]["sashikomi"]["kirikaki"]
    mu = [m for m in d["munes"] if m["name"] == "Kurumayose"][0]
    v_piv = (mu["v0"] + mu["v1"]) / 2.0
    # ⭐ **指図の atV を、指図自身が言う導き方で検算する。**
    #   規約: v の単位は**間**、軒の出は**m**。混ぜると軒先の線が手前にずれ、玄関棟の屋根に
    #   覆われない切り欠きが露天に出る(2026-09-04 に 0.736m ぶん実際に踏んだ)。
    #   ⛔ ここで直さない — 指図が正典。⭕ **食い違いを叫ぶ**だけにして、指図方へ返す。
    gk = [m for m in d["munes"] if m["name"] == d["roofs"]["Goten_Kurumayose"]["sashikomi"]["intoMune"]][0]
    gr = d["roofs"]["Goten_" + gk["name"]]
    # 軒の出[m/片側] = 屋根の外形 − 棟の平面。⚠ `dKen` は屋根側にあり、v の向きとは限らないので
    #   **棟の v の間数**から引く(玄関棟は 11×11 で等しいが、他所へ写したときに効く)
    noki = (float(gr["outerD"]) - (float(gk["v1"]) - float(gk["v0"])) * KEN) / 2.0
    if not 0.0 < noki < 2.0:
        print(u"[okfuz] ⚠ 軒の出の算出が怪しい: %.3fm — outerD と棟の v 間数が対応していない" % noki)
    near = gk["v0"] if v_piv < gk["v0"] else gk["v1"]                 # 車寄に面する側の外壁
    want = near - noki / KEN if v_piv < gk["v0"] else near + noki / KEN
    if abs(float(kk["atV"]) - want) > 0.01:
        print(u"[okfuz] ⚠⚠ 指図の atV が導き方と食い違う: %s 間。外壁 %.1f 間 − 軒の出 %.2fm"
              u"(=%.4f 間)→ **%.4f 間**が正。差 %.3fm ぶん余計に切る" %
              (kk["atV"], near, noki, noki / KEN, want, abs(float(kk["atV"]) - want) * KEN))
        print(u"[okfuz]    ⛔ 部材方は直さない。指図 `kirikaki.atV` を指図方が直すこと")
    else:
        print(u"[okfuz] ⭕ atV の検算 一致(外壁 %.1f 間 − 軒の出 %.2fm = %.4f 間)" % (near, noki, want))

    v = float(kk["atV"]) if at_v is None else float(at_v)
    z = float(kk["aboveY"]) if above_y is None else float(above_y)
    y = (v - v_piv) * KEN
    print(u"[okfuz] 切り欠き: 指図 atV=%s 間 / aboveY=%s m(面から)。ピボット v=%.1f 間"
          % (kk["atV"], kk["aboveY"], v_piv))
    print(u"[okfuz]   → 使う値 v=%.4f 間 → **Blender y ≧ %+.4f** かつ **z ≧ %.4f** を落とす"
          % (v, y, z))
    return y, z


def kirikaki(o, at_y, above_z):
    """`at_y` より奥(+v)で `above_z` より上の面を落とす。

    ⛔ **boolean を使わない** — 屋根は瓦モジュールの非多様体な面の集まりで、boolean は解けない
      (`Tools/Blender/README.md` の踏んだ落とし穴)。⭕ **bisect で頂点を挿して割る**ので
      瓦は欠けず、切り口は一直線に通る。
    ⚠ bisect は面の付かない**孤立頂点を残す** — 落とさないと bbox が実形状より大きく出る。
    ⛔ **切り口を `holes_fill` で塞がない。**瓦は開いたシェル(strip)なので `is_boundary` の辺が
      мesh 中に無数にあり、軒先も妻も一緒に塞がれて屋根の上に斜めの膜が張る(2026-09-04 に踏んだ)。
      ⭕ 切り口は開けたまま — 玄関棟の屋根の下に隠れる位置だから見えない。
    """
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for co, no in (((0.0, at_y, 0.0), (0.0, 1.0, 0.0)),
                   ((0.0, 0.0, above_z), (0.0, 0.0, 1.0))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               dist=1e-5, plane_co=co, plane_no=no)
    e = 1e-4
    kill = [f for f in bm.faces
            if f.calc_center_median().y > at_y + e and f.calc_center_median().z > above_z + e]
    n = len(kill)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bmesh.ops.delete(bm, geom=[x for x in bm.verts if not x.link_faces], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    print(u"[okfuz] 切り欠き: 面 %d 枚を落とした(切り口は開けたまま)" % n)
    return o


# ================================================================ 御錠口
def jouguchi(ken=3, name="Okabe_Jouguchi"):
    """**御錠口** 3間角(指図 `links[2]` L_Jouguchi)。表向と奥向を分ける**一口だけ**の口
    ([西川1959]/[高知2000] A)。**幅一間の渡廊下**が ±X の面に取り付く。

    ローカル: **+X = 廊下の通る向き**、±Z は白壁(連子窓)。
    ピボット = footprint の中心・**床レベル**(⚠ 地盤ではない — `EdoGotenKit` の棟と同じ
    規約。据えるときは 面 + `const.gotenFloor`(0.62)に置く)。
    ⭕ **+X 側の開口に御錠口の唐戸(両開きの板戸)を建て込んである。**−X 側は開けたまま。

    ⚠⚠ **屋根は入母屋で、棟天端は床+5.0 近くになる。**渡廊下(大棟天端 床+2.503)より
    ずっと高い — 実物でも御錠口は一段高い屋根で標す作りだが、⭕ **普請奉行の裁定事項**。
    軒先は `EdoGotenKit` の棟と揃えて **床+2.577** に置いてある。"""
    P = N.palette()
    S = ken * KEN
    h = S / 2.0
    TATE = 2.727          # 建具丈(江戸間 1間半)
    OPEN = KEN            # 廊下の開口幅 = 1間
    m = VM.Mesh()
    m.box(-h - 0.12, h + 0.12, -0.62, 0.0, -h - 0.12, h + 0.12,
          VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)                   # 床下の基壇
    m.box(-h, h, 0.0, 0.10, -h, h, VM.sub(P['wuv'], 0.05, 0.10, 0.95, 0.60), WOOD)  # 床
    # 柱(四隅 + 開口の方立)
    for x in (-h, h):
        for z in (-h, -OPEN / 2, OPEN / 2, h):
            m.box(x - 0.09, x + 0.09, 0.10, TATE, z - 0.09, z + 0.09,
                  VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
    # ±Z の面は白壁(腰は板)+ 連子窓
    for sz, sg in ((-h, -1), (h, 1)):
        N.shitami(m, P, -h, h, 0.10, 0.85, sz, sg, 'x')
        N.mizukiri(m, P, -h, h, 0.85, sz, sg, 'x')
        N.plaster(m, P, -h, h, 0.85, TATE, sz, sg, 'x')
        m.box(-0.95, 0.95, 1.10, 1.16, sz - sg * 0.02, sz + sg * 0.07,
              VM.sub(P['wuv'], 0.45, 0.10, 0.90, 0.35), WOOD)
        m.box(-0.95, 0.95, 1.94, 2.00, sz - sg * 0.02, sz + sg * 0.07,
              VM.sub(P['wuv'], 0.45, 0.40, 0.90, 0.65), WOOD)
        m.box(-0.92, 0.92, 1.18, 1.92, sz - sg * 0.115, sz - sg * 0.085,
              VM.sub(P['juv'], 0.05, 0.05, 0.95, 0.95), N.SHOJI)     # 明かり障子
        m.koshi(-0.92, 0.92, 1.18, 1.92, sz - sg * 0.05, sz + sg * 0.02,
                VM.sub(P['wuv'], 0.60, 0.10, 0.95, 0.90), WOOD, pitch=0.115, bar=0.026)
    # ±X の面: 開口の外側は白壁、開口は 1間
    for sx, sg in ((-h, -1), (h, 1)):
        for (a, b) in ((-h, -OPEN / 2), (OPEN / 2, h)):
            N.shitami(m, P, a, b, 0.10, 0.85, sx, sg, 'z')
            N.mizukiri(m, P, a, b, 0.85, sx, sg, 'z')
            N.plaster(m, P, a, b, 0.85, TATE, sx, sg, 'z')
        m.box(sx - sg * 0.10, sx + sg * 0.02, TATE - 0.10, TATE, -OPEN / 2, OPEN / 2,
              VM.sub(P['wuv'], 0.30, 0.40, 0.80, 0.60), WOOD)        # 楣
    # ⭕ 御錠口の唐戸(両開きの板戸)を **+X の開口**に建て込む
    N.door_leaves(m, P, -OPEN / 2, OPEN / 2, 0.12, TATE - 0.10, h, 1, n=2)
    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    roof = R.make_irimoya(S, S, name + "_roof", eave=0.90)
    roof.location = (0.0, 0.0, 2.577)      # EdoGotenKit の棟と同じ軒先レベル
    bpy.context.view_layer.update()
    V.sel([roof]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.dedup_materials()
    o = V.join([body, roof], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o]); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o, name


# ================================================================ 稲荷社 / 鳥居
def inari15(ken=1.5, name="Okabe_Inari15"):
    """**稲荷社の小祠** 1.5間角(岡部邸 `service.Inari`)。台石 + 一間社流造の小祠。
    **南向き(+Z が正面)**。

    ⛔ **鳥居はこの部材に含めない。**指図 `gardens[3].yashiro` が
    「**躯体の矩形は `service/Inari` が持つ**」と書いており、鳥居・参道・四つ目垣は
    庭方が別に範囲を決めている。⚠ 1.5間(2.727m)の中へ鳥居まで押し込むと、
    笠木が祠の屋根を横切って絡む(2026-09-04 に実見)。→ 鳥居は <see cref="torii"/> で別に出す。
    ⛔ **玉垣・朱鳥居は使わない**(指図 `certs.garden.inari` の明文)。
      ⇒ 在庫の `Own.Matsudaira.Inari` は**朱の明神鳥居**込みなので流用できない。
    ⚠ **当屋敷に稲荷があったという記録は無い=U**(一般類型で置いたもの)。姿も一般形に留める。

    ローカル: **+Z = 正面**。ピボット = footprint の中心・地盤レベル。"""
    P = N.palette()
    S = ken * KEN
    h = S / 2.0
    W_UV = VM.sub(P['wuv'], 0.15, 0.10, 0.55, 0.90)
    m = VM.Mesh()
    m.box(-h, h, 0.0, 0.28, -h, h, VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)
    m.box(-h + 0.10, h - 0.10, 0.28, 0.34, -h + 0.10, h - 0.10,
          VM.sub(P['suv'], 0.1, 0.5, 0.9, 0.95), STONE)
    bw, bd, fl, bh = 1.05, 0.90, 0.82, 0.90
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.box(sx * bw / 2 - 0.05, sx * bw / 2 + 0.05, 0.34, fl,
                  sz * bd / 2 - 0.05, sz * bd / 2 + 0.05, W_UV, WOOD)
    m.box(-bw / 2 - 0.17, bw / 2 + 0.17, fl - 0.09, fl,
          -bd / 2 - 0.17, bd / 2 + 0.32, VM.sub(P['wuv'], 0.05, 0.10, 0.95, 0.55), WOOD)
    for (x0, x1, z0, z1) in ((-bw / 2, bw / 2, -bd / 2, -bd / 2 + 0.07),
                             (-bw / 2, -bw / 2 + 0.07, -bd / 2, bd / 2),
                             (bw / 2 - 0.07, bw / 2, -bd / 2, bd / 2)):
        m.box(x0, x1, fl, fl + bh, z0, z1, W_UV, WOOD)
    m.box(-bw / 2, bw / 2, fl, fl + bh, bd / 2 - 0.07, bd / 2,
          VM.sub(P['wuv'], 0.62, 0.05, 0.80, 0.95), WOOD)           # 正面の扉
    for sx in (-1, 1):                                              # 高欄(簡素)
        m.box(sx * (bw / 2 + 0.14) - 0.035, sx * (bw / 2 + 0.14) + 0.035, fl, fl + 0.34,
              -bd / 2 - 0.14, bd / 2 + 0.29, W_UV, WOOD)
    for i in range(3):                                              # 木階
        m.box(-0.32, 0.32, 0.34 + (fl - 0.34) * i / 3.0, 0.34 + (fl - 0.34) * (i + 1) / 3.0,
              bd / 2 + 0.32 - 0.13 * (i + 1), bd / 2 + 0.32 - 0.13 * i,
              VM.sub(P['wuv'], 0.30, 0.10, 0.85, 0.35), WOOD)
    # ---- 流造の屋根(前が長く流れる)。⛔ 一枚面にしない — 裏も張らないと空が抜ける
    ry, zr = fl + bh + 0.42, -0.09
    zb, zf = -bd / 2 - 0.32, bd / 2 + 0.70
    yb, yf = fl + bh + 0.06, fl + bh * 0.50
    xh = bw / 2 + 0.34
    for dv in (0.0, -0.075):
        back = [(-xh, ry + dv, zr), (xh, ry + dv, zr), (xh, yb + dv, zb), (-xh, yb + dv, zb)]
        front = [(xh, ry + dv, zr), (-xh, ry + dv, zr), (-xh, yf + dv, zf), (xh, yf + dv, zf)]
        if dv < 0:
            back, front = back[::-1], front[::-1]
        m.quad(back, VM.sub(P['wuv'], 0.10, 0.10, 0.90, 0.40), WOOD)
        m.quad(front, VM.sub(P['wuv'], 0.10, 0.50, 0.90, 0.90), WOOD)
    for sx in (-xh, xh):
        m.tri([(sx, ry, zr), (sx, yb, zb), (sx, yb, zr)], VM.sub(P['wuv'], 0.6, 0.1, 0.8, 0.3), WOOD)
        m.tri([(sx, ry, zr), (sx, yf, zf), (sx, yf, zr)], VM.sub(P['wuv'], 0.6, 0.1, 0.8, 0.3), WOOD)
    m.box(-xh, xh, ry, ry + 0.10, zr - 0.08, zr + 0.08,
          VM.sub(P['wuv'], 0.60, 0.60, 0.90, 0.80), WOOD)
    for i in (-1, 0, 1):
        m.box(i * 0.26 - 0.05, i * 0.26 + 0.05, ry + 0.10, ry + 0.20, zr - 0.12, zr + 0.12,
              VM.sub(P['wuv'], 0.70, 0.60, 0.80, 0.70), WOOD)
    for sx in (-1, 1):
        m.box(sx * (bw / 2 + 0.24), sx * (bw / 2 + 0.30), ry - 0.10, ry + 0.40,
              zr - 0.05, zr + 0.05, VM.sub(P['wuv'], 0.60, 0.20, 0.70, 0.50), WOOD)
    o = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    o.name = name; o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


def torii(name="Okabe_Torii"):
    """**素木の明神鳥居**(稲荷の参道に立てる点景)。⛔ **朱に塗らない**
    — 指図 `certs.garden.inari` が「玉垣・朱鳥居は使わない」と明記している。
    ローカル: 幅=X(柱の並び)/ 高さ=Y / 厚み=Z。**+Z が参道の手前**(どちら向きでもよい)。
    ピボット = **柱の芯の中央・地盤レベル**。内法幅 1.30 / 柱高 1.85。"""
    P = N.palette()
    W_UV = VM.sub(P['wuv'], 0.15, 0.10, 0.55, 0.90)
    tw, th, pr = 1.30, 1.85, 0.070
    m = VM.Mesh()
    for sx in (-1, 1):
        x = sx * tw / 2
        m.box(x - pr, x + pr, 0.0, th, -pr, pr, W_UV, WOOD)
        m.box(x - 0.15, x + 0.15, -0.10, 0.14, -0.15, 0.15,
              VM.sub(P['suv'], 0, 0, 0.4, 0.4), STONE)              # 亀腹の代わりの根巻石
    m.box(-tw / 2 - 0.21, tw / 2 + 0.21, th - 0.50, th - 0.39, -0.055, 0.055, W_UV, WOOD)  # 貫
    # 島木 + 笠木。⚠ **2本まとめて同じ反りに乗せる** — 笠木だけ反らせると間が楔形に開く
    n, KW = 12, tw / 2 + 0.35
    for i in range(n):
        t0, t1 = i / float(n), (i + 1) / float(n)
        x0, x1 = -KW + 2 * KW * t0, -KW + 2 * KW * t1
        r0, r1 = 0.12 * ((2 * t0 - 1) ** 2), 0.12 * ((2 * t1 - 1) ** 2)
        for zz, sg in ((0.105, 1), (-0.105, -1)):
            m.quad([(x0, th + r0, zz), (x1, th + r1, zz),
                    (x1, th + 0.12 + r1, zz), (x0, th + 0.12 + r0, zz)][::sg], W_UV, WOOD)
        for zz, sg in ((0.135, 1), (-0.135, -1)):
            m.quad([(x0, th + 0.12 + r0, zz), (x1, th + 0.12 + r1, zz),
                    (x1, th + 0.25 + r1, zz), (x0, th + 0.25 + r0, zz)][::sg], W_UV, WOOD)
        m.quad([(x0, th + 0.25 + r0, -0.135), (x1, th + 0.25 + r1, -0.135),
                (x1, th + 0.25 + r1, 0.135), (x0, th + 0.25 + r0, 0.135)], W_UV, WOOD)
        m.quad([(x1, th + r1, -0.105), (x0, th + r0, -0.105),
                (x0, th + r0, 0.105), (x1, th + r1, 0.105)], W_UV, WOOD)
    m.box(-0.075, 0.075, th - 0.39, th, -0.05, 0.05, W_UV, WOOD)    # 額束
    o = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    o.name = name; o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


def kurumayose_cut(at_v=None, above_y=None):
    """車寄の**切り欠き済み**の版。⭕ 棟梁は実行時にメッシュを割らない方針なので、
    差し込みの納めは**部材の側で解いておく**。規則と数値は指図が正典(`kirikaki_planes`)。
        blender ... -- kurumayose_cut [--at-v <間>] [--above-y <m>] [--render]
    ⚠ `--at-v` / `--above-y` は**裁定図を描くための比較用**。既定は必ず指図の値。"""
    y, z = kirikaki_planes(at_v, above_y)
    return kurumayose(name="Okabe_Kurumayose_Cut", cut=(y, z))


PARTS = {"umaya": umaya, "tomomachi": tomomachi, "nandokoya": nandokoya,
         "kurumayose": kurumayose, "kurumayose_cut": kurumayose_cut,
         "jouguchi": jouguchi, "inari15": inari15, "torii": torii}


def ortho(w, h, res):
    """⚠ `ortho_scale` は**画像の長辺**に効く。幅だけで決めると縦が切れる
    (2026-09-04 に踏んだ — 1.5間角の稲荷が枠から溢れて姿が判定できなかった)。"""
    return max(w, h * float(res[0]) / res[1]) * 1.12


def shots(o, key, box):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    H = mx.z - mn.z
    r = max(mx.x - mn.x, mx.y - mn.y, H)
    # ① 開口面(+Z = Blender −Y。厚みを反転して出しているため)から斜め
    V.studio((mn.x - r * 0.9, mn.y - r * 1.8, max(1.7, H * 0.7)),
             (c.x, c.y, H * 0.42), res=(1700, 1000))
    V.render(os.path.join(SHOT, "okfuz_%s_3d.png" % key))
    # ② 開口面の立面
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=ortho(mx.x - mn.x, H, (1700, 1000)), res=(1700, 1000))
    V.render(os.path.join(SHOT, "okfuz_%s_elev.png" % key))
    # ③ 背面から斜め(開口が漏れていないか)
    V.studio((mx.x + r * 0.9, mx.y + r * 1.8, max(1.9, H * 0.7)),
             (c.x, c.y, H * 0.42), res=(1700, 1000))
    V.render(os.path.join(SHOT, "okfuz_%s_ura.png" % key))
    # ④ 妻の正面立面(妻壁が塞がっているか)
    V.studio((mn.x - r * 2.4, c.y, c.z), (c.x, c.y, c.z),
             ortho_scale=ortho(mx.y - mn.y, H, (1300, 1100)), res=(1300, 1100))
    V.render(os.path.join(SHOT, "okfuz_%s_gable.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    def opt(flag):
        return float(argv[argv.index(flag) + 1]) if flag in argv else None
    kw = {"at_v": opt("--at-v"), "above_y": opt("--above-y")}
    skip = {argv[argv.index(f) + 1] for f in ("--at-v", "--above-y") if f in argv}
    want = [a for a in argv if not a.startswith("--") and a not in skip] or list(PARTS.keys())
    for key in want:
        if key not in PARTS:
            print("[okfuz] ⚠ 知らない部材: %s (%s)" % (key, "/".join(PARTS)))
            continue
        V.reset()
        o, name = PARTS[key](**kw) if key == "kurumayose_cut" else PARTS[key]()
        mn, mx = V.bbox([o])
        print("[okfuz] %-20s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  底=%.3f  面=%d"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
        print("[okfuz] %-20s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
        if "--render" in argv:
            shots(o, key, (mn, mx))       # ⚠ 書き出しの前に撮る(後だと bbox が潰れる)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[okfuz] 書き出し " + os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    main()
