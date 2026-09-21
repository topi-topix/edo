"""**類型共用の裏長屋(裏店)** — 町屋24町の路地に並ぶ九尺二間の棟(88区画の類型ビルダーが使う)。

    blender --background --python Tools/Blender/build_typ_nagaya.py -- [名前...] [--render]
    blender --background --python Tools/Blender/build_typ_nagaya.py -- ura --ken 9 [--render]
    (名前を省くと既定の3寸法。ura / munewari / narabe)

【なぜ新造するか】EDO-0318 ④(在庫方の照会 2026-09-21)。表の `ura_nagaya` は24区画に
  書いてあるのに、**専用部材が無い**ので類型ビルダーは一度も建てていない
  (`Eg.Kidobanya` 木戸番屋 1.83×1.61×2.78 を連ねるスタンドインの案しか無かった)。
  在庫を当たると町屋の棟は `Eg.Shop01/02`(表店・2階建て・見世棚)だけで、
  **平屋の裏店は在庫にも他邸の手組みにも無い**。

【方針 — ゼロから起こさない(`build_typ_fuzokuya.py` と同じ薄い駆動器)】
  岡部の崖下の詰人長屋 `build_obi_nagaya.build()` が「平屋・桟瓦・下見板腰・戸と窓の割付」
  を既に持っている。⛔ 別実装を書かない。裏店のために 2026-09-21 に出した引数だけで作る:
  `base`(基壇を捨てる)/ `end`(けらばを詰める)/ `plan_b`(−Z にも戸を並べる=棟割)/
  `uchinori`(内法を下げる)/ `post_pitch`(1.5間=1戸で柱を割る)。

【寸法【U — 指図に欄が無い。部材方が決めた】】
  ・1戸 = **間口 九尺(1.5間 = 2.727m)× 奥行 二間(3.636m)**。
    「九尺二間の裏長屋」は江戸の裏店の代名詞で、間口9尺・奥行2間・約3坪【一般類型 A】。
  ・軒桁 **2.30**(表店の2階建てより確実に低い)/ 腰 **0.85** / 内法 **1.80** /
    軒の出 **0.55** / けらば **0.20** / 基壇 **0.06**(裏店は土間・玉石を均すだけ)。
  ・割付 = 腰高障子の入口 **0.95** + 窓 **0.60** + 見付。⛔ 表店の見世棚は付けない。
  ・**桟瓦葺**【U】。天保以降の町方は瓦葺が進んでおり表店と同じ瓦にした。
    ⚠ 板葺+石置の裏店も安政期まで残るが、当プロジェクトに江戸赤坂の裏店の
    屋根葺材を決める史料が無い。板葺にするなら `build_okabe_fuzokuya.nandokoya` の
    板屋根へ差し替えること。

【⭕ 表店 `Eg.Shop01/02` と並べて見分けが付くか — `narabe` が焼く】
  ① **階**  平屋(棟天端 3.6m 級)対 表店の2階建て ② **割り** 1.5間ピッチの戸が延々続く
  ③ **建具** 見世棚・暖簾・看板が一切無い ④ **丈** 軒 2.30 は表店の1階の軒より低い

【向き(Unity 座標)】幅=X(桁行・棟の走る向き)/ 高さ=Y / 厚み=Z。
  **+Z = 路地に向く開口面**。割長屋は −Z が盲面、棟割は **±Z とも開口面**。
  ピボット = **footprint の中心・地盤レベル**。⚠ 軒は footprint の外へ ±Z に 0.55、
  ±X に 0.20 出る。**ピボットには含めない**。

【材】⛔ 新規に作らない。倣った先(岡部の長屋)の材質名をそのまま運ぶ —
  `wood` / `wall C` / `Foundation_A_01` / `wall A` / `roof` / `roof ornaments`。
"""
import bpy, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_obi_nagaya as OB

KEN  = 1.818
OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Nagaya"))
SHOT = os.path.join(V.REPO, "Screenshots")

MAGUCHI = 1.5       # 1戸の間口[間] = 九尺【一般類型 A】
OKUYUKI = 2.0       # 1戸の奥行[間] = 二間【一般類型 A】
EAVE    = 2.30      # 軒桁[m]【U】⛔ 下げると入口の内法 1.80 と腰 0.85 が潰れる
KOSHI   = 0.85      # 下見板の腰の天端[m]【U】
UCHI    = 1.80      # 建具の内法高[m]【U】
NOKI    = 0.55      # 長手の軒の出[m]【U】
END     = 0.20      # けらばの出[m]【U】
BASE    = 0.06      # 基壇[m]【U】⛔ 裏店に基壇は無い。0 にすると敷居が地面に埋まる
RIDGE   = 0.30      # 大棟の熨斗の見え掛かり[m]【U】

DOOR_W  = 0.95      # 腰高障子の入口[m]【U】
MADO_W  = 0.60      # 窓[m]【U】

# 在庫の表店 `Eg.Shop01` の **ES=1.818 倍後**の丈[m]。目録 docs/asset-index.tsv の素寸
# 2.71 × 2.34 × 2.22 から。⚠ 表店は**平屋**で 4.25m しかない — 「裏店は表店より低い」の
# 見分けは丈だけでは付かないので、割り(1.5間の戸が延々続く)と見世棚の有無で見る。
SHOP01_H = 2.34 * 1.818


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def row_plan(wKen):
    """桁行 wKen 間を 1.5間/戸で割り、1戸に「入口 + 窓」を1組ずつ置く。

    ⚠ **戸数は史実の値ではない**(確度U)。間口九尺の割りを機械的に当てただけで、
      その筆に実際に何戸あったかの史料は当プロジェクトに無い。⛔ 戸数を名乗らせない。"""
    W = wKen * KEN
    n = max(1, int(round(wKen / MAGUCHI)))
    unit = W / n
    pad = (unit - DOOR_W - MADO_W) / 3.0
    plan = []
    for i in range(n):
        s = -W / 2.0 + i * unit
        plan.append((s + pad, s + pad + DOOR_W, 'door'))
        plan.append((s + 2 * pad + DOOR_W, s + 2 * pad + DOOR_W + MADO_W, 'window'))
    return plan, n


def _common(wKen, dKen, name, plan, plan_b):
    return OB.build(wKen, dKen, name, eaveH=EAVE, ridge_show=RIDGE, plan=plan,
                    koshiH=KOSHI, noki=NOKI, base=BASE, end=END, plan_b=plan_b,
                    uchinori=UCHI, post_pitch=MAGUCHI)


# ================================================================ 割長屋(片側)
def ura(wKen=9.0):
    """**裏長屋(割長屋)** 桁行 wKen 間 × 奥行 2間・平屋・桟瓦・**+Z の一面だけに戸**。

    路地の片側に建つ型。⛔ −Z は盲面 — 背中合わせの隣の棟や隣地の塀に接するので
    窓を開けない(岡部の詰人長屋の盲面と同じ作り)。

    ローカル **+X = 桁行 / +Z = 路地に向く開口面**。ピボット = footprint の中心・地盤レベル。"""
    plan, n = row_plan(wKen)
    name = "Typ_UraNagaya_%sken" % fmt(wKen)
    o = _common(wKen, OKUYUKI, name, plan, None)
    print("[ura] %-26s %d戸(間口 %.3fm = 九尺)" % (name, n, wKen * KEN / n))
    return o, name


# ================================================================ 棟割長屋(背中合わせ)
def munewari(wKen=9.0):
    """**棟割長屋** 桁行 wKen 間 × 奥行 **4間**(2間+2間の背中合わせ)・**±Z とも開口面**。

    ⭐ 「九尺二間の裏長屋」の代表的な作り。大棟を挟んで両側に戸が並ぶので、
      1棟で路地を2本分まかなえる。⛔ 割長屋(`ura`)を2棟背中合わせに置いて代用しない —
      間に隙間が出て、棟が2本立って見える。

    ⚠ 棟が高くなる(梁間4間なので大棟は従属値で上がる)。実測は下の print が申告する。
    ローカル **+X = 桁行 / ±Z とも路地に向く開口面**。ピボット = footprint の中心・地盤レベル。"""
    plan, n = row_plan(wKen)
    name = "Typ_UraNagaya_%sken_munewari" % fmt(wKen)
    o = _common(wKen, OKUYUKI * 2, name, plan, plan, )
    print("[ura] %-26s %d戸×2列(間口 %.3fm = 九尺)" % (name, n, wKen * KEN / n))
    return o, name


# ================================================================ 並べ比べ(書き出さない)
def narabe():
    """**在庫の表店 `Eg.Shop01` と裏長屋を並べて焼く。**

        blender --background --python Tools/Blender/build_typ_nagaya.py -- narabe

    ⛔ 単体の立面では「表店と見分けが付くか」は読めない — 階数も丈も比べる相手が要る。
    ⚠ `es_shop` の obj は素寸なので **ES=1.818 倍**してから並べる(`EdoAssets.Eg` の規約)。
    ⛔ 何も書き出さない。"""
    V.reset()
    objs, xs = [], 0.0
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(V.REPO, "Assets", "edogoyomi",
                                                "es_shop01", "shop01.obj"))
    got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    shop = V.join(got, "Eg_Shop01_ref")
    V.sel([shop])
    bpy.ops.transform.resize(value=(1.818,) * 3, center_override=(0, 0, 0))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mn, mx = V.bbox([shop])
    shop.location = (-mn.x, -(mn.y + mx.y) / 2.0, -mn.z)
    bpy.context.view_layer.update()
    V.sel([shop]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    print("[ura] 並べ比べ 在庫 Eg.Shop01(ES後) W=%.2f H=%.2f D=%.2f"
          % (mx.x - mn.x, mx.z - mn.z, mx.y - mn.y))
    xs = mx.x - mn.x + 3.0
    objs.append(shop)
    for fn, arg in ((ura, 9.0), (munewari, 9.0)):
        o, _n = fn(arg)
        mn, mx = V.bbox([o])
        o.location = (xs - mn.x, 0.0, 0.0)
        bpy.context.view_layer.update()
        V.sel([o]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        xs += (mx.x - mn.x) + 3.0
        objs.append(o)
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    bpy.ops.mesh.primitive_plane_add(size=300.0, location=(xs / 2.0, 0.0, 0.0))
    V.studio((xs / 2.0, -70.0, 4.0), (xs / 2.0, 0.0, 4.0),
             ortho_scale=xs * 1.05, res=(2200, 700))
    V.render(os.path.join(SHOT, "typ_uranagaya_narabe_elev.png"))
    V.studio((-8.0, -24.0, 1.6), (xs * 0.42, 0.0, 3.0), res=(1900, 950))
    V.render(os.path.join(SHOT, "typ_uranagaya_narabe_me.png"))
    print("[ura] 並べ比べ: Screenshots/typ_uranagaya_narabe_{elev,me}.png")


PARTS = {"ura": ura, "munewari": munewari}
DEFAULT_KEN = [6.0, 9.0, 12.0]      # 4戸 / 6戸 / 8戸【U】町屋の筆の奥行から穏当な三寸法


def shots(o, key):
    """⚠ **書き出しの前に撮る**(`export_fbx` の後は bbox が潰れて画角が壊れる)。
    ⛔ 地面を z=0 に敷く — ピボットが地盤レベルなので足元の浮きがここで読める。"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    r = max(W, H, D)
    bpy.ops.mesh.primitive_plane_add(size=max(80.0, r * 8), location=(c.x, c.y, 0.0))
    # ① 開口面の立面 — 1.5間の割りと戸・窓の並びを読む
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H) * 1.15, res=(2000, 900))
    V.render(os.path.join(SHOT, "typ_ura_%s_elev.png" % key))
    # ② 開口面を斜め前・人の目の高さから
    V.studio((mn.x - r * 0.45, mn.y - r * 0.9, 1.60), (c.x, c.y, H * 0.45), res=(1800, 1000))
    V.render(os.path.join(SHOT, "typ_ura_%s_3d.png" % key))
    # ③ 背面 — **割長屋は盲面が漏れていないか / 棟割は戸が並んでいるか**
    V.studio((mx.x + r * 0.45, mx.y + r * 0.9, 1.80), (c.x, c.y, H * 0.45), res=(1800, 1000))
    V.render(os.path.join(SHOT, "typ_ura_%s_ura.png" % key))
    # ④ 妻の立面 — 妻壁の塞ぎ・けらば・破風
    V.studio((mn.x - r * 2.4, c.y, c.z), (c.x, c.y, c.z),
             ortho_scale=max(D, H) * 1.20, res=(1200, 1100))
    V.render(os.path.join(SHOT, "typ_ura_%s_gable.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or list(PARTS.keys())
    kens = DEFAULT_KEN
    if "--ken" in argv:
        i = argv.index("--ken")
        kens = [float(a) for a in argv[i + 1:] if not a.startswith("--")] or DEFAULT_KEN
        want = [w for w in want if w not in [fmt(k) for k in kens]]
    if "narabe" in want:
        narabe()
        want = [w for w in want if w != "narabe"]
    for key in want:
        if key not in PARTS:
            print("[ura] ⚠ 知らない部材: %s (%s / narabe)" % (key, "/".join(PARTS)))
            continue
        for k in kens:
            V.reset()
            o, name = PARTS[key](k)
            mn, mx = V.bbox([o])
            print("[ura] %-26s Unity実寸 W(X)=%6.3f  H(Y)=%6.3f  D(Z)=%6.3f  底=%+.3f  面=%d"
                  % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
            print("[ura] %-26s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
            print("[ura] %-26s 棟天端 %.3f / 表店 Eg.Shop01(ES後)の丈 %.2f → 差 %+.2fm"
                  % (name, mx.z, SHOP01_H, mx.z - SHOP01_H))
            if "--render" in argv:
                shots(o, "%s_%s" % (key, fmt(k)))     # ⚠ 書き出しの前に撮る
            V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
            print("[ura] 書き出し " + os.path.join(OUT, name + ".fbx"))


main()
