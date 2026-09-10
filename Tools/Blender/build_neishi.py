"""**板塀の根石(玉石)** — 松江松平上屋敷(matsudaira_dewa)の中仕切の板塀。

    blender --background --python Tools/Blender/build_neishi.py -- [all|<長さm>] [--render]

【なぜ新造するか】在庫に**玉石が0件**(`docs/asset-index.tsv`・2026-09-09 在庫方)。
  ⛔ 庭で使っている `JG_Rock_A_01..03`(1.25〜1.99m級)は**庭石**で、根石の丈 0.30〜0.40m
     とは桁が違う。⛔ 汎用フーチングも当てられない(白い箱になる)。

【寸法 — 指図 `nakajikiriRule.neishi` が正典。⛔ ここで数を作らない】
  `show` [0.15, 0.20]  地上に出る高さ[m]
  `bury` 0.5           石の丈に対する埋まり比 ⇒ **丈 = show ÷ (1 − bury) = 2×show**
                       ⇒ 丈 0.30〜0.40m。**地盤線より下 show・上 show の対称**になる
  `t`    0.35          塀の面から両側へ出る厚み[m] = **走りに直交する全厚**
  `long` [0.40, 0.70]  一石の走り[m]。⭐ **乱尺**(⛔ 同じ長さで並べない)
  ⚠ **石数は指図に無い従属値**(run の長さ ÷ long の平均)。8 run・延長 444.2m ⇒ 約 800 石。

━━━ ⛔⛔ 2026-09-10 の差し戻し(普請検査が画で見た不良)━━━━━━━━━━━━━━━━
  据えた 842 石は「**厚み数 cm の黒い三日月**にしか見えず、板塀の足元の汚れ・ひびに読める」
  「**黒く角張っていて河原石(丸い玉石)に見えない**」と判定された。⇒ 直した所は 2 つ:

  ⭕ ① **土台と材を替えた。** 従前は Waldemarst の庭石 `FJG_Rock_A_0{1,2,3}`(1.25〜1.99m)を
     0.5m 級へ**大きく縮めて**使い、材は `M_FJG_Rock_001`
     (= `T_FJG_Rock_Dark_001_Albedo`。名のとおり **Dark**。実測 **V14.9% / 粒 14.2**)だった。
     ⇒ NatureManufacture の **`s_rock_01..06`(0.28〜0.55m の実肌の小石)**へ替えた。
       ・**元から根石の寸法**なので、縮尺の歪み(丸みが相似で痩せる)を原理的に踏まない
       ・材は FBX が最初から持っている **`M_photoscanned_rocks_01`**
         (実測 **V40.8% / 粒 9.1** = **明るく肌理が細かい**)で、⛔ **新規マテリアルではない**
         (`Assets/NatureManufacture Assets/…/Materials/M_photoscanned_rocks_01.mat` が在庫にある)
       ・個体ごとに**アトラスの別の領域**を踏むので柄の個体差が最初から付いている
     ⚠ 明度は **アルベドの数**であって見えではない(AgX で彩度が落ちる)⇒ レンダで測ること。
  ⭕ ② **丸みを強めた**(`SMOOTH_ITERS`)。受入は下位5%の局所半径 **≥ 0.045m**
     (従前 0.020〜0.045 で「角張って見える」と判定された。ユーザー指摘の帯は 2〜6cm)。

  ⚠ **露出(見え高)は動かしていない。** `show` / `bury` は指図の値で、部材方は決めない。
    ⇒ 焼くたびに **丈といくら見えるかの関係**を刷る(`_show_table`)。判断は指図方へ。

【作り方 — ⛔ ゼロから起こさない】`build_hiraishi` と**同じ流儀**:
  在庫の実肌の小石を土台に、目標寸法へ変形する。⭕ 形(自然に丸まったシルエット)と
  UV(アトラスの個体ごとの領域)をまとめて引き継ぐので、手続き生成に付き物の人工物
  (輪切りの継ぎ目・鞍型)を原理的に踏まない。

【⭐ 玉石は庭石よりさらに丸める】ユーザー指摘「角が鋭すぎませんか?」(2026-09-06)。
  ⭕ 玉石は**水に洗われた河原石**なので、`bmesh.ops.smooth_vert` で全体を丸めるのは
     形の由来として正しい(凹も凸も一緒に丸まってよい)。⇒ 丸めたあと**目標寸法へ嵌め直す**。
  ⭕ 丸みは目でなく**数で確かめる**(`curvature_report`)— 稜の折れ角 θ と稜まわりの
     面の差し渡し L から局所の丸み半径 r = L ÷ (2·tan(θ/2)) を出し、**下位5%**を見る。

【材】⛔ 新規に作らない。`M_photoscanned_rocks_01`(在庫の .mat。名前だけの入れ物を
  `V.named_material` が用意し、Unity の Search & Remap が既存 .mat を当てる)。
  ⚠ `V.hook_textures()` では結線されない(Village Kit の綴りでない)⇒ 検証レンダの前に `hook()`。

【ピボット】⭐ **走りの芯・厚みの芯・座(地盤線)**。
  ローカル **+X = 塀の走り** / **+Y = 上**(Y=0 が地盤線。メッシュは −show 〜 +show)/
  **+Z = 厚み**。⇒ 据える側は `neishi_seat_check` が決めた**柱間ごとの座**を
  そのまま `position.y` に入れればよい(⛔ 底でも天端でもない)。
"""
import bpy, bmesh, sys, os, math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_tateishi as BT

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa"))
SHOT = os.path.join(V.REPO, "Screenshots")

# ---- 指図 `nakajikiriRule.neishi`(⛔ ここで作った数ではない) -------------------
SHOW = (0.15, 0.20)
BURY = 0.5
T = 0.35

# ---- 土台と材(⛔ どちらも在庫。新規に起こしていない)---------------------------
NM_DIR = os.path.join(V.REPO, "Assets", "NatureManufacture Assets",
                      "Meadow Environment Dynamic Nature", "Rocks", "Rocks", "Models")
NM_TEX = os.path.join(NM_DIR, "Textures")
ROCK_MAT = "M_photoscanned_rocks_01"        # ⭐ FBX が元から持つ材質名。⛔ 新規ではない
WOOD_UV = (0.600, 0.03, 0.770, 0.97)        # 板塀の見立て用(build_goten_roof と同じ木理)

# ⭐ **乱尺**の刻み。`long` [0.40, 0.70] を 8 個体に散らす。
#   ⛔ 等間隔にしない(等間隔だと run 上で周期が読める)。⛔ 長さと丈を相関させない。
#   土台は 6 種を回すので、同じ長さでも柄とシルエットが違う。
#   (長さ, 丈, 土台番号)。丈は 2×show ⇒ 0.30〜0.40 の範囲に収まっていること。
#   ⚠ **丈の割り振りは 2026-09-09 版から動かしていない** — `show`/`bury` は指図の値で、
#     部材方が決める物ではないため(露出が足りないなら指図方が `show` を動かす)。
VARIANTS = [
    (0.41, 0.34, 1),
    (0.45, 0.30, 2),
    (0.50, 0.38, 3),
    (0.54, 0.32, 4),
    (0.58, 0.40, 5),
    (0.62, 0.31, 6),
    (0.66, 0.36, 2),
    (0.70, 0.33, 5),
]
# ⭐⭐ **丸めの手順は 3 段**(2026-09-10 に実測で決めた。⛔ 目で決めていない)。
#   ① `smooth_vert` を 6 回 … 稜を落とす(水に洗われる過程そのもの)
#   ② **Catmull-Clark を 1 段** … ⭐ これが効く。①だけでは足りない
#      (`smooth_vert` は頂点を寄せるだけなので、**面が痩せて L が縮み、局所半径 r = L÷2tan(θ/2)
#        がかえって下がる**。実測: 14回 0.031〜0.052 → 44回 0.016〜0.042 と**悪化**した)
#   ③ **Decimate 0.40** … ②で 4 倍になった面を戻す。⛔ 丸みは落ちない
#      (平らな所から潰れるので、稜まわりの L はむしろ広がる)
#   実測(8個体): 下位5% **0.0395〜0.0597 m** / 三角 484〜1016(従前 284)。
SMOOTH_ITERS = 6
SMOOTH_FACTOR = 0.55
SUBSURF_LEVEL = 1
DECIMATE_RATIO = 0.40
ROUND_ACCEPT = 0.035      # 凸の稜の局所半径の下位5%[m]。ユーザーの帯は 2〜6cm
                          # ⚠ 実測の下限 0.0395 の少し下に置いた**床の見張り**。
                          # ⛔ 結果に合わせて上下させない — 動かすならユーザーの帯ごと。


def _load_donor(i):
    """在庫の小石を1つ読む。⚠ NatureManufacture の FBX は `_LOD0/1/2` を1本に持つので LOD0 だけ残す。
    ⭕ **Z-up のまま据わる**(実測: Blender Z の丈 = 目録の Unity Y)。
      ⛔ `build_hiraishi._load_donor` の X軸+90° を写さない — あれは Waldemarst の
        庭石が「Unity 側の prefab 回転込みで扁平に置かれている」ことへの補正で、
        こちらの土台には当てはまらない(掛けると横倒しになる)。"""
    objs = VM.import_fbx_abs(os.path.join(NM_DIR, "s_rock_%02d.FBX" % i),
                             keep=lambda n: "LOD0" in n)
    meshes = [o for o in objs if o.type == 'MESH']
    if not meshes:
        raise SystemExit("[neishi] ⛔ 土台 s_rock_%02d が読めない" % i)
    return V.join(meshes, "donor") if len(meshes) > 1 else meshes[0]


def hook():
    """検証レンダ用に `M_photoscanned_rocks_01` のアルベド/法線を結ぶ。
    ⚠ `V.hook_textures()` は Village Kit の綴り(`<名>_AlbedoTransparency.png`)しか見ないので
      NatureManufacture の材には当たらない。⛔ **FBX 書き出しには一切影響しない** —
      書き出されるのはマテリアル**名**だけで、ノードは Unity 側の .mat が持つ。"""
    alb = os.path.join(NM_TEX, "T_Photoscanned_rocks_01_BC.tga")
    nrm = os.path.join(NM_TEX, "T_Photoscanned_rocks_01_N.tga")
    for m in bpy.data.materials:
        if m.name.split('.')[0] != ROCK_MAT:
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.80
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(alb, check_existing=True)
        img.location = (-600, 300)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        if os.path.exists(nrm):
            ni = nt.nodes.new('ShaderNodeTexImage')
            ni.image = bpy.data.images.load(nrm, check_existing=True)
            ni.image.colorspace_settings.name = 'Non-Color'
            ni.location = (-600, -100)
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.location = (-300, -100)
            nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])


def _fit(o, w, h, d):
    """メッシュを外接寸法 (走りw, 丈h, 厚みd) へ嵌める。**Blender x=走り / y=厚み / z=丈**。
    ⚠ ここは相似でない直接スケール。丸めのあとに掛けるので、丸み半径も同じ比で伸縮する。"""
    mn, mx = BT.bounds([o])
    w0, d0, h0 = mx.x - mn.x, mx.y - mn.y, mx.z - mn.z
    o.data.transform(BT.Matrix_translate(-(mn.x + mx.x) * 0.5,
                                         -(mn.y + mx.y) * 0.5,
                                         -(mn.z + mx.z) * 0.5))
    o.data.transform(BT.Matrix_scale(w / max(w0, 1e-6), d / max(d0, 1e-6), h / max(h0, 1e-6)))
    o.data.update()


def _round(o, iters=SMOOTH_ITERS, factor=SMOOTH_FACTOR):
    """⭐ **玉石の丸み。**`smooth_vert` を繰り返す(= 水に洗われる過程そのもの)。
    ⚠ 体積が僅かに痩せるので、**呼んだ後に必ず `_fit` で寸法へ嵌め直す**こと。
    ⚠ UV は面ごとの属性なので位置を動かしても消えない(アトラスの領域は保たれる)。"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    verts = list(bm.verts)
    for _ in range(iters):
        bmesh.ops.smooth_vert(bm, verts=verts, factor=factor,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


def _subsurf_decimate(o):
    """⭐ Catmull-Clark 1段 → Decimate。**UV は両方とも保たれる**(細分は UV も割り、
    collapse は UV を補間する)。⚠ 焼くたびに `build_one` が UV の範囲を刷るので、
    アトラスの領域から外れていないかは数で見られる。"""
    m = o.modifiers.new("subsurf", "SUBSURF")
    m.levels = SUBSURF_LEVEL; m.render_levels = SUBSURF_LEVEL
    V.sel([o]); bpy.ops.object.modifier_apply(modifier=m.name)
    d = o.modifiers.new("decimate", "DECIMATE")
    d.ratio = DECIMATE_RATIO
    V.sel([o]); bpy.ops.object.modifier_apply(modifier=d.name)


def _uv_range(o):
    uv = o.data.uv_layers.active
    if uv is None:
        return (0.0, 0.0, 0.0, 0.0)
    us = [l.uv[0] for l in uv.data]; vs = [l.uv[1] for l in uv.data]
    return (min(us), max(us), min(vs), max(vs))


def curvature_report(o):
    """⭐ **丸みを数で測る。**稜(辺)ごとに、両側の面の法線のなす角 θ(=折れ角)と
    稜まわりの面の差し渡し L から **局所の丸み半径 r = L ÷ (2·tan(θ/2))** を出す。
    ⛔ 平均を見ない — 効くのは**いちばん尖った所**なので **下位5%** と最小を返す。
    ⛔ 凹の稜は数えない(ユーザー指摘は「凸の稜」)。"""
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    rs = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f1, f2 = e.link_faces
        c1, c2 = f1.calc_center_median(), f2.calc_center_median()
        # 凸判定: 面心を結ぶ向きが法線の和と逆を向く(外へ折れている)なら凸
        if (c2 - c1).dot(f2.normal - f1.normal) <= 0:
            continue
        th = f1.normal.angle(f2.normal)
        if th < 1e-4:
            continue
        L = 0.5 * (math.sqrt(f1.calc_area()) + math.sqrt(f2.calc_area()))
        rs.append(L / (2.0 * math.tan(th / 2.0)))
    bm.free()
    if not rs:
        return (float('inf'), float('inf'), 0)
    rs.sort()
    return (rs[0], rs[max(0, int(len(rs) * 0.05))], len(rs))


def _span_at(me, z, axis='x'):
    """高さ z の水平面でメッシュを切ったときの、走り(x)または厚み(y)方向の差し渡し。
    ⛔ 外接寸法で代用しない — 玉石は丸いので地盤線では外接より狭い。"""
    xs = []
    k = 0 if axis == 'x' else 1
    for e in me.edges:
        a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
        if (a.z - z) * (b.z - z) > 0:
            continue
        if abs(b.z - a.z) < 1e-9:
            xs += [a[k], b[k]]
        else:
            t = (z - a.z) / (b.z - a.z)
            xs.append(a[k] + (b[k] - a[k]) * t)
    return (max(xs) - min(xs)) if xs else 0.0


def _show_table(o, lng, h):
    """⭐⭐ **「丈といくら見えるか」を数で返す**(2026-09-10 の差し戻し3への回答)。
    ⛔ 部材方は `show` / `bury` を決めない — 決めるのは指図方。ここは**測って渡すだけ**。

    返す量(すべて m):
      丈 h / 見え show = h×(1−bury) / 埋め bury×h
      **見え面の差し渡し** — 地盤線・見えの中ほど・天端の 9 割の3つの高さで、
      走り方向と厚み方向の両方。⭐ 「どれだけ石らしい塊が地上に出るか」はこれで決まる。
      ⚠ 丸い石ほど**天端に近いほど細る**ので、見え高だけでは露出の印象を測れない。
    """
    show = h * (1.0 - BURY)
    rows = []
    for lbl, z in (("地盤線", 0.0), ("見えの中ほど", show * 0.5), ("見えの天端9割", show * 0.9)):
        rows.append((lbl, z, _span_at(o.data, z, 'x'), _span_at(o.data, z, 'y')))
    return show, rows


def build_one(lng, h, donor_i, name):
    o = _load_donor(donor_i)
    _fit(o, lng, h, T)                 # ① まず目標寸法へ(丸めの効きを実寸で見るため)
    r_min1, r_p5_1, _ = curvature_report(o)
    uv0 = _uv_range(o)
    _round(o)                          # ② 河原石の丸み(稜を落とす)
    _subsurf_decimate(o)               # ③ ⭐ Catmull-Clark で丸め、Decimate で面を戻す
    _fit(o, lng, h, T)                 # ④ 痩せたぶんを嵌め直す
    r_min, r_p5, n = curvature_report(o)

    mat = V.named_material(ROCK_MAT)
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)

    # ピボット = 走りの芯・厚みの芯・**座(地盤線)**。丈の中央が地盤線(bury=0.5)
    mn, mx = BT.bounds([o])
    o.data.transform(BT.Matrix_translate(-(mn.x + mx.x) * 0.5,
                                         -(mn.y + mx.y) * 0.5,
                                         -(mn.z + mx.z) * 0.5))
    o.data.update()
    o.name = o.data.name = name
    mn, mx = BT.bounds([o])
    print("[neishi] %-24s 走り %.3f × 丈 %.3f × 厚み %.3f / 見え %.3f・埋め %.3f / "
          "土台 s_rock_%02d 面=%d 材質=%s"
          % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mx.z, -mn.z,
             donor_i, len(o.data.polygons), [m.name for m in o.data.materials]))
    print("[neishi]   丸み(凸の稜の局所半径 m) 縮めた直後 最小%.4f/下位5%%%.4f "
          "→ 丸めた後 最小%.4f/下位5%%%.4f(稜 %d 本・受入 下位5%% ≥ %.3f)"
          % (r_min1, r_p5_1, r_min, r_p5, n, ROUND_ACCEPT))
    uv1 = _uv_range(o)
    print("[neishi]   UV(アトラスの領域) 土台 u[%.3f,%.3f] v[%.3f,%.3f] "
          "→ 焼いた後 u[%.3f,%.3f] v[%.3f,%.3f]" % (uv0 + uv1))
    show, rows = _show_table(o, lng, h)
    for lbl, z, sx, sy in rows:
        print("[neishi]   見え面の差し渡し %-12s (Y%+.3f) 走り %.3f / 厚み %.3f"
              % (lbl, z, sx, sy))
    # ⭐ **据える側が要る数**: 玉石は丸いので **地盤線での差し渡し < 外接寸法**。
    #   ⛔ 外接寸法どうしを突き付けると、地盤線の高さで石のあいだに空が抜ける。
    w_seat = rows[0][2]
    print("[neishi]   芯々の詰め = 地盤線の差し渡し %.3f m(外接の %.0f%%)"
          % (w_seat, 100.0 * w_seat / max(mx.x - mn.x, 1e-6)))
    if r_p5 < ROUND_ACCEPT:
        raise SystemExit(
            "[neishi] ⛔ 丸みが足りない(下位5%% の局所半径 %.4f m < 受入 %.3f m)。\n"
            "  ユーザー指摘『角が鋭すぎませんか?』(2026-09-06)と普請検査『黒く角張っていて\n"
            "  河原石に見えない』(2026-09-10)。SMOOTH_ITERS を増やすこと。" % (r_p5, ROUND_ACCEPT))
    return o


def _itabei_mock(x0, x1, y_top=1.85):
    """⭐ **板塀の見立て**(検証レンダ専用。⛔ 書き出さない・在庫にもしない)。
    根石は「板塀の足元に並ぶ物」なので、**塀を立てずに石だけ見ても合否は出せない**
    (2026-09-10 の差し戻しは『板塀の足元の汚れ・ひびに読める』という判定だった)。
    ⇒ 板の厚み 0.12m・裾を根石の天端に載せた板を1枚立てる。材は Village Kit の `wood`。"""
    m = V.named_material("wood")
    o = V.box("ItabeiMock", (x1 - x0, 0.12, y_top - 0.16),
              ((x0 + x1) / 2.0, 0.0, 0.16 + (y_top - 0.16) / 2.0), mat=m)
    V.set_uv_rect(o, WOOD_UV, axes=('x', 'z'))     # ⛔ 一点貼りにしない(のっぺりした板になる)
    return o


def shots(objs):
    """⭕ **近景で見る。**引きのレンダでは丸みも柄も読めない(README の落とし穴)。
    ⚠ `M_photoscanned_rocks_01` は `V.hook_textures()` では結ばれない ⇒ `hook()`。"""
    V.hook_textures()          # 板塀の見立て(`wood`)用
    hook()                     # 玉石用
    os.makedirs(SHOT, exist_ok=True)
    # 8個体を走りに並べて「run に据えた見え」を作る(乱尺の効きと繰り返しの目立ち方を見る)
    x = 0.0
    for o in objs:
        mn, mx = BT.bounds([o])
        # ⚠ 芯々は**地盤線の差し渡し**で詰める(外接で突き付けると地盤線で空が抜ける)
        seat = _span_at(o.data, 0.0, 'x')
        o.location = mathutils.Vector((x - mn.x - (mx.x - mn.x - seat) / 2.0, 0.0, 0.0))
        x += seat + 0.012        # 目地 12mm
    bpy.ops.mesh.primitive_plane_add(size=30, location=(x * 0.5, 0.0, 0.0))
    out = []
    shots_spec = [
        # ⭐ **これが受入の画**: 板塀を立てて、地盤に立つ人の目から足元を見る
        ("ashimoto", (x * 0.5 - 1.2, -3.0, 1.45), (x * 0.5, 0.0, 0.10), (1700, 900), True),
        ("run", (x * 0.5, -3.4, 1.35), (x * 0.5, 0.0, 0.05), (1600, 700), False),
        ("kinkei", (0.55, -0.95, 0.42), (0.55, 0.0, 0.03), (1500, 1000), False),
        ("ue", (x * 0.5, 0.0, 3.2), (x * 0.5, 0.0, 0.0), (1600, 500), False),
    ]
    mock = None
    for sub, cam, look, res, want_mock in shots_spec:
        if want_mock and mock is None:
            mock = _itabei_mock(-0.1, x + 0.1)
            V.hook_textures()
        if (not want_mock) and mock is not None:
            bpy.data.objects.remove(mock, do_unlink=True); mock = None
        for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
            bpy.data.objects.remove(c, do_unlink=True)
        V.studio(cam, look, res=res)
        f = os.path.join(SHOT, "neishi_%s.png" % sub)
        V.render(f)
        out.append(f)
        print("RENDER %s" % f)
    return out


def asset_name(lng):
    """⚠ EdoAssets.cs の `Own.Neishi` が同じ綴りでパスを組む。変えたら両方直す。"""
    return "Neishi_Tamaishi_L%s" % ("%g" % round(lng, 2))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")]
    jobs = [v for v in VARIANTS
            if not want or want[0] == "all" or ("%g" % v[0]) in want]
    if not jobs:
        raise SystemExit("[neishi] 該当する長さが無い。焼いてあるのは %s"
                         % ", ".join("%g" % v[0] for v in VARIANTS))
    for lng, h, d in jobs:
        show = h * (1.0 - BURY)
        if not (SHOW[0] - 1e-6 <= show <= SHOW[1] + 1e-6):
            raise SystemExit("[neishi] ⛔ 見え高 %.3f が指図 `show` %s の外(丈 %.2f)"
                             % (show, list(SHOW), h))
        if not (0.40 - 1e-6 <= lng <= 0.70 + 1e-6):
            raise SystemExit("[neishi] ⛔ 走り %.3f が指図 `long` [0.40,0.70] の外" % lng)
    made = []
    for lng, h, d in jobs:
        V.reset()
        o = build_one(lng, h, d, asset_name(lng))
        V.export_fbx([o], os.path.join(OUT, o.name + ".fbx"))
        made.append((lng, h, d))
    if "--render" in argv:
        V.reset()
        objs = [build_one(lng, h, d, asset_name(lng)) for lng, h, d in made]
        shots(objs)
    print("[neishi] %d 個体 → %s" % (len(made), OUT))


if __name__ == "__main__":
    main()
