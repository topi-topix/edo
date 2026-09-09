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

【作り方 — ⛔ ゼロから起こさない】`build_hiraishi` と**同じ流儀**:
  在庫の実肌の転石 `FJG_Rock_A_0{1,2,3}_LOD0.fbx` を土台に、目標寸法へ変形する。
  ⭕ 形(自然に丸まったシルエット)と UV(`T_FJG_Rock_Dark_001_Albedo` の個体ごとの
     アトラス象限。A_01=右下 / A_02=左下 / A_03=左上 — **土台を替えると柄も替わる**)を
     まとめて引き継ぐので、手続き生成に付き物の人工物(輪切りの継ぎ目・鞍型)を原理的に踏まない。

【⭐ 玉石は庭石よりさらに丸める】ユーザー指摘「角が鋭すぎませんか?」(2026-09-06)。
  ⛔ **土台を縮めるだけでは丸みが足りない** — 1.5m の転石の 3cm の丸みは 0.5m へ縮めると
     1cm になり、受入値「凸の稜に 2〜6cm」を割る(相似縮小なので**必ず**割る)。
  ⭕ 玉石は**水に洗われた河原石**なので、`bmesh.ops.smooth_vert` で全体を丸めるのは
     形の由来として正しい(凹も凸も一緒に丸まってよい)。⇒ 丸めたあと**目標寸法へ嵌め直す**。
  ⭕ 丸みは目でなく**数で確かめる**(`curvature_report`)— 稜の折れ角 θ と稜まわりの
     面の差し渡し L から局所の丸み半径 r = L ÷ (2·tan(θ/2)) を出し、**下位5%**を見る。

【材】⛔ 新規に作らない。`M_FJG_Rock_001`(庭の護岸の転石と同じ .mat。名前だけの入れ物を
  `V.named_material` が用意し、Unity の Search & Remap が既存 .mat を当てる)。
  ⚠ `V.hook_textures()` では結線されない ⇒ 検証レンダの前に `build_tateishi.hook()` を呼ぶ。

【ピボット】⭐ **走りの芯・厚みの芯・座(地盤線)**。
  ローカル **+X = 塀の走り** / **+Y = 上**(Y=0 が地盤線。メッシュは −show 〜 +show)/
  **+Z = 厚み**。⇒ 据える側は `neishi_seat_check` が決めた**柱間ごとの座**を
  そのまま `position.y` に入れればよい(⛔ 底でも天端でもない)。
"""
import bpy, bmesh, sys, os, math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_tateishi as BT
import build_hiraishi as HI

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa"))
SHOT = os.path.join(V.REPO, "Screenshots")

# ---- 指図 `nakajikiriRule.neishi`(⛔ ここで作った数ではない) -------------------
SHOW = (0.15, 0.20)
BURY = 0.5
T = 0.35

# ⭐ **乱尺**の刻み。`long` [0.40, 0.70] を 8 個体に散らす。
#   ⛔ 等間隔にしない(等間隔だと run 上で周期が読める)。⛔ 長さと丈を相関させない。
#   土台は 3 種を回すので、同じ長さでも柄とシルエットが違う。
#   (長さ, 丈, 土台番号)。丈は 2×show ⇒ 0.30〜0.40 の範囲に収まっていること
VARIANTS = [
    (0.41, 0.34, 1),
    (0.45, 0.30, 2),
    (0.50, 0.38, 3),
    (0.54, 0.32, 1),
    (0.58, 0.40, 2),
    (0.62, 0.31, 3),
    (0.66, 0.36, 1),
    (0.70, 0.33, 2),
]
SMOOTH_ITERS = 8          # 河原石らしい丸みが出るまで。下の curvature_report で決めた
SMOOTH_FACTOR = 0.55


def _fit(o, w, h, d):
    """メッシュを外接寸法 (走りw, 丈h, 厚みd) へ嵌める。**Blender x=走り / y=厚み / z=丈**
    (`build_hiraishi` と同じ軸の取り方 — 土台は X まわり +90° で「扁平な据わり」にしてある)。
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
    ⚠ UV は面ごとの属性なので位置を動かしても消えない(アトラスの象限は保たれる)。"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    verts = list(bm.verts)
    for _ in range(iters):
        bmesh.ops.smooth_vert(bm, verts=verts, factor=factor,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


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


def _span_at(me, z):
    """高さ z の水平面でメッシュを切ったときの、走り(Blender x)方向の差し渡し。
    ⛔ 外接寸法で代用しない — 玉石は丸いので地盤線では外接より狭い。"""
    xs = []
    for e in me.edges:
        a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
        if (a.z - z) * (b.z - z) > 0:
            continue
        if abs(b.z - a.z) < 1e-9:
            xs += [a.x, b.x]
        else:
            t = (z - a.z) / (b.z - a.z)
            xs.append(a.x + (b.x - a.x) * t)
    return (max(xs) - min(xs)) if xs else 0.0


def build_one(lng, h, donor_i, name):
    o = HI._load_donor("FJG_Rock_A_0%d_LOD0.fbx" % donor_i)
    r_min0, r_p5_0, _ = curvature_report(o)
    _fit(o, lng, h, T)                 # ① まず目標寸法へ(丸めの効きを実寸で見るため)
    r_min1, r_p5_1, _ = curvature_report(o)
    _round(o)                          # ② 河原石の丸み
    _fit(o, lng, h, T)                 # ③ 痩せたぶんを嵌め直す
    r_min, r_p5, n = curvature_report(o)

    mat = BT._borrow_rock_material()
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
          "面=%d 材質=%s" % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y,
                            mx.z, -mn.z, len(o.data.polygons),
                            [m.name for m in o.data.materials]))
    print("[neishi]   丸み(凸の稜の局所半径 m) 縮めた直後 最小%.4f/下位5%%%.4f "
          "→ 丸めた後 最小%.4f/下位5%%%.4f(稜 %d 本)"
          % (r_min1, r_p5_1, r_min, r_p5, n))
    # ⭐ **据える側が要る数**: 玉石は丸いので **地盤線での差し渡し < 外接寸法**。
    #   ⛔ 外接寸法どうしを突き付けると、地盤線の高さで石のあいだに空が抜ける。
    #   ⇒ 芯々は「地盤線の差し渡し」で詰めること(下の比を EdoAssets に載せる)。
    w_seat = _span_at(o.data, 0.0)
    print("[neishi]   地盤線(Y=0)での走りの差し渡し %.3f m(外接の %.0f%%)"
          % (w_seat, 100.0 * w_seat / max(mx.x - mn.x, 1e-6)))
    if r_p5 < 0.02:
        raise SystemExit(
            "[neishi] ⛔ 丸みが足りない(下位5%% の局所半径 %.4f m < 受入 0.02 m)。\n"
            "  ユーザー指摘『角が鋭すぎませんか?』(2026-09-06)。SMOOTH_ITERS を増やすこと。"
            % r_p5)
    return o


def shots(objs):
    """⭕ **近景で見る。**引きのレンダでは丸みも柄も読めない(README の落とし穴)。
    ⚠ `M_FJG_Rock_001` は `V.hook_textures()` では結ばれない ⇒ `BT.hook()`。"""
    BT.hook()
    os.makedirs(SHOT, exist_ok=True)
    # 8個体を走りに並べて「run に据えた見え」を作る(乱尺の効きと繰り返しの目立ち方を見る)
    xs, x = [], 0.0
    for o in objs:
        mn, mx = BT.bounds([o])
        o.location = mathutils.Vector((x - mn.x, 0.0, 0.0))
        x += (mx.x - mn.x) + 0.012        # 目地 12mm
        xs.append(o)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(x * 0.5, 0.0, 0.0))
    out = []
    for sub, cam, look, res in (
            ("run", (x * 0.5, -3.4, 1.35), (x * 0.5, 0.0, 0.05), (1600, 700)),
            ("kinkei", (0.55, -0.95, 0.42), (0.55, 0.0, 0.03), (1500, 1000)),
            ("ue", (x * 0.5, 0.0, 3.2), (x * 0.5, 0.0, 0.0), (1600, 500))):
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
