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
import bpy, sys, os, math
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


PARTS = {"umaya": umaya, "tomomachi": tomomachi, "nandokoya": nandokoya}


def shots(o, key, box):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    H = mx.z - mn.z
    r = max(mx.x - mn.x, mx.y - mn.y, H)
    # ① 開口面(+Z = Blender −Y。厚みを反転して出しているため)から斜め
    V.studio((mn.x - r * 0.45, mn.y - r * 1.0, 1.7), (c.x, c.y, H * 0.45), res=(1700, 1000))
    V.render(os.path.join(SHOT, "okfuz_%s_3d.png" % key))
    # ② 開口面の立面
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=max(mx.x - mn.x, H) * 1.15, res=(1700, 1000))
    V.render(os.path.join(SHOT, "okfuz_%s_elev.png" % key))
    # ③ 背面から斜め(開口が漏れていないか)
    V.studio((mx.x + r * 0.45, mx.y + r * 1.0, 1.9), (c.x, c.y, H * 0.45), res=(1700, 1000))
    V.render(os.path.join(SHOT, "okfuz_%s_ura.png" % key))
    # ④ 妻の正面立面(妻壁が塞がっているか)
    V.studio((mn.x - r * 2.4, c.y, c.z), (c.x, c.y, c.z),
             ortho_scale=max(mx.y - mn.y, H) * 1.18, res=(1300, 1100))
    V.render(os.path.join(SHOT, "okfuz_%s_gable.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or list(PARTS.keys())
    for key in want:
        if key not in PARTS:
            print("[okfuz] ⚠ 知らない部材: %s (%s)" % (key, "/".join(PARTS)))
            continue
        V.reset()
        o, name = PARTS[key]()
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
