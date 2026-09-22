"""竹矢来(たけやらい)— 類型共用の「透ける囲い」。EDO-0363。

    blender --background --python Tools/Blender/build_typ_yarai.py -- [--render]
    blender --background --python Tools/Blender/build_typ_yarai.py -- narabe   # 穂垣との 20m 比べ(書き出さない)

⭐ **なぜ起こしたか。** 公有地 `azukarichi_yl`(大的稽古場)の囲い種別 `yarai` は在庫が無く
   穂垣 `Eg.Hogaki5` で代用していたが、**20m 離れると板塀と見分けが付かない**と在庫方が差し戻した
   (EDO-0363)。矢来は「竹を斜めに交叉させて縄で結んだ、向こうが透ける仮設の囲い」なので、
   **透け**そのものが意匠。⇒ 実ジオメトリの竹で ×字の格子を組む。

【意匠(部材方が決めた・確度 U)】安政3年の江戸で普請の仮囲い・分界・火事場・矢場に使う矢来。
   - 竹の丸材を **45° の筋違**に、1間を3等分した **0.606m ピッチ**で左右両方向へ渡す
     ⇒ 一辺 0.43m の菱形の抜け。**見付の充実率 30.4%**(= 69.6% が空・光線で実測)で、
     板塀・穂垣(どちらも 100%)と遠目にも取り違えようがない。
   - その竹を **胴縁(横の貫)2段で表裏から挟み**、**親柱**は1間ごと。継ぎ目は**縄で巻く**。
   - 丈 2.00m(据えると 0.10m が土に入るので **実丈 1.90m**)。

⛔ **新しいマテリアルを作らない。**竹も縄も Village Kit の `Bamboo garden fence` 1種で、
   UV はキットの竹垣 FBX から**矩形で**借りる(竹の胴/小口/縄の3矩形)。⇒ Unity 側の
   Search & Remap が `Assets/Japanese Village Kit/Materials/Bamboo garden fence.mat` を当てる。

⛔ **一点貼りしない。**丸材の側面は「キットの竹の帯(u 0.123..0.237)を面数で割った u」×
   「長手へ流す v」で、**節の間隔ぶん(0.9m)ごとに v を折り返す** ⇒ 引き伸ばしが出ず、
   折り返しの線が竹の節に見える。

【座標】`vkmesh.Mesh` の論理座標 **(走り, 高さ, 厚み)**。`to_object` が厚みを反転して出すので
   **論理 +厚み = Unity ローカル +Z = 見え面**。⚠ 走りは Unity では反転する
   (memory: logical-axis-and-mirror-checks)が、この部材は**走りの中心について対称**に組んで
   あるので鏡像でも姿が変わらない(焼いた直後に検算する)。

【ピボット】モジュールの**走りの中心・足元(高さ0)・厚み0(柱の芯)**。
   ⚠ `EdoBuild.PanelRun` / `ButtOnRun` は実メッシュの端で突き付け、`SeatBottom` は bounds の底を
   見るので、ピボットは置き場所に影響しない。
   ⛔ **`set_origin` で原点だけ動かさない** — FBX ノードに平行移動が残り、Unity では子が
   1.8m 横へずれた所に載る(2026-09-22 に実測。`build_typ_machiya` と同じく原点の上へ寄せてから焼く)。

【並べ方】モジュール幅 **2間 = 3.636m = 0.606 × 6** ちょうど。斜材の x 切片も 0.606 の倍数なので
   **突き付けると格子が継ぎ目を跨いで通る**。親柱は x = 0.909 / 2.727(= 各1間の中心)に立つので、
   モジュールを継ぐと親柱が **1.818m 等間隔**で並ぶ(継ぎ目に柱が重ならない)。
"""
import bpy, os, sys, math
from mathutils import Vector as V3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM

SHOT = os.path.join(V.REPO, "Screenshots")
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Kakoi"))

KEN = 1.818                     # 江戸間 1間
SRC = "Fences/Bamboo garden fence.fbx"   # 材と UV の借り先(Village Kit)
MAT = "Bamboo garden fence"

# ── キットの竹(`bamboo garden fence stake`)から実測した UV(2026-09-22)────────────
#    側面 = 八角の 8 帯 u 0.123..0.237 / 長手 v 0.005..0.637(実長 0.900m)
#    小口 = u 0.960..0.994 / v 0.045..0.079(切り口の白い環)
#    縄   = 竹垣本体の結束(3枚あるうち一番明るいもの)u 0.813..0.899 / v 0.591..0.697
#           (rgb 0.40 0.39 0.33。隣の 0.861..0.950 と 0.923..0.993 はさらに暗い)
UV_SIDE = (0.123, 0.005, 0.237, 0.637)
UV_CAP = (0.960, 0.045, 0.994, 0.079)
UV_NAWA = (0.813, 0.591, 0.899, 0.697)
NODE = 0.900                    # 側面 UV が受け持つ実長 = 節の折り返し間隔

# ── 寸法 ───────────────────────────────────────────────────────────────
L = 2 * KEN                     # モジュール幅 3.636m(= 0.606 × 6)
H = 2.00                        # 天端。据えると 0.10 が土に入るので実丈 1.90m
PITCH = KEN / 3.0               # 斜材の x 切片ピッチ 0.606
POST_R, POST_N = 0.055, 8       # 親柱(太い竹)
RAIL_R, RAIL_N = 0.028, 6       # 胴縁
DIAG_R, DIAG_N = 0.027, 6       # 斜材(キットの竹と同径 0.054)
RAIL_Y = (0.34, 1.84)           # 胴縁の高さ
RAIL_Z = 0.078                  # 胴縁の厚み位置(表裏)
DIAG_Z = 0.050                  # 斜材の厚み位置(表裏)
DIAG_Y = (0.24, 1.92)           # 斜材の上下端
XPAD = 0.02                     # 斜材はここだけ内へ寄せる(小口の環が bbox を食わないように)


# ══════════════════════════════════════════════════════════════════════
#  丸材(竹)— 任意の2点を結ぶ多角柱。小口は塞ぐ。
# ══════════════════════════════════════════════════════════════════════
def _frame(t):
    """t に直交する枠 (n1, n2) を n1 × n2 = t になるように取る。
    ⛔ `n1.cross(t)` は符号が逆(外向きの巻きが裏返る)。"""
    ref = V3((0.0, 0.0, 1.0)) if abs(t.z) < 0.9 else V3((1.0, 0.0, 0.0))
    n1 = t.cross(ref).normalized()
    return n1, t.cross(n1).normalized()


def culm(m, p0, p1, r, sides=6, uv=UV_SIDE, cap=(True, True), node=NODE, mat=0):
    """p0 → p1 の丸材。巻きは外向き(論理座標は右手系のまま)。

    ⚠ 側面の v は **節の間隔 `node` ごとに折り返す**(k が奇数の輪で v を入れ替える)。
      引き伸ばさずに済み、折り返しの線が竹の節に見える。
    戻り値は軸方向の単位ベクトル(結束を巻くのに使う)。"""
    p0, p1 = V3(p0), V3(p1)
    d = p1 - p0
    length = d.length
    t = d / length
    n1, n2 = _frame(t)
    ns = max(1, int(round(length / node)))
    ang = [2.0 * math.pi * s / sides for s in range(sides)]
    rings = []
    for k in range(ns + 1):
        c = p0 + t * (length * k / ns)
        rings.append([c + (n1 * math.cos(a) + n2 * math.sin(a)) * r for a in ang])
    u0, v0, u1, v1 = uv
    for k in range(ns):
        va, vb = (v0, v1) if k % 2 == 0 else (v1, v0)
        for s in range(sides):
            s2 = (s + 1) % sides
            uu0 = u0 + (u1 - u0) * s / sides
            uu1 = u0 + (u1 - u0) * (s + 1) / sides
            m.quad_uvs([tuple(rings[k][s]), tuple(rings[k][s2]),
                        tuple(rings[k + 1][s2]), tuple(rings[k + 1][s])],
                       [(uu0, va), (uu1, va), (uu1, vb), (uu0, vb)], mat)
    # 小口 — 扇形に四角を張る(頂点を増やさないよう三角ファンにしない)
    for end, want in ((ns, cap[1]), (0, cap[0])):
        if not want:
            continue
        ring = rings[end]
        idx = list(range(sides)) if end == ns else list(range(sides - 1, -1, -1))
        cu = [(UV_CAP[0] + (UV_CAP[2] - UV_CAP[0]) * (0.5 + 0.5 * math.cos(a)),
               UV_CAP[1] + (UV_CAP[3] - UV_CAP[1]) * (0.5 + 0.5 * math.sin(a))) for a in ang]
        for i in range(1, sides - 1, 2):
            j = min(i + 2, sides - 1)
            q = [idx[0], idx[i], idx[i + 1], idx[j]]
            m.quad_uvs([tuple(ring[x]) for x in q], [cu[x] for x in q], mat)
    return t


def nawa(m, center, axis, r, length=0.10, sides=6):
    """結束(縄)— 材に巻いた短い環。⛔ 小口は塞がない(中に材が通っている)。
    ⚠ 4面だと**黒い角板**に見える(2026-09-22 の1回目)。6面にして径を材に寄せる。"""
    t = V3(axis).normalized()
    culm(m, V3(center) - t * (length / 2.0), V3(center) + t * (length / 2.0),
         r, sides=sides, uv=UV_NAWA, cap=(False, False), node=length * 2.0)


# ══════════════════════════════════════════════════════════════════════
#  竹矢来 1モジュール
# ══════════════════════════════════════════════════════════════════════
def yarai(width=L, height=H):
    """走り `width` × 丈 `height` の矢来を1枚。走りの中心について**対称**に組む。"""
    m = VM.Mesh()
    y0, y1 = DIAG_Y
    span = y1 - y0                      # 45° なので x の振れも同じ

    # ① 斜材 —「/」は x 切片 c = k·PITCH、「\」はその鏡像。x ∈ [0, width] へ切る。
    #    ⭕ width が PITCH の整数倍なので、突き付けたモジュール間で格子が通る。
    diag = []
    kmin = int(math.floor(-span / PITCH)) - 1
    kmax = int(math.ceil(width / PITCH)) + 1
    for k in range(kmin, kmax + 1):
        c = k * PITCH
        for sgn, z in ((+1.0, +DIAG_Z), (-1.0, -DIAG_Z)):
            # 「/」: x = c + (y - y0)(表)/「\」: x = (width - c) - (y - y0)(裏)
            xa = c if sgn > 0 else (width - c)
            xb = xa + sgn * span
            # x ∈ [XPAD, width-XPAD] へ切る(小口の環が bbox の外へ出ないように)
            ta = (XPAD - xa) / (xb - xa)
            tb = ((width - XPAD) - xa) / (xb - xa)
            tlo = max(0.0, min(ta, tb))
            thi = min(1.0, max(ta, tb))
            if thi - tlo < 0.07:
                continue
            lo, hi = y0 + tlo * span, y0 + thi * span
            p0 = (xa + (xb - xa) * tlo, lo, z)
            p1 = (xa + (xb - xa) * thi, hi, z)
            t = culm(m, p0, p1, DIAG_R, sides=DIAG_N)
            diag.append((p0, p1, t, z))

    # ② 胴縁(表裏2段ずつ)— 走りいっぱい。小口が x = 0 / width の平面に立つので bbox を決める。
    for ry in RAIL_Y:
        for rz in (+RAIL_Z, -RAIL_Z):
            culm(m, (0.0, ry, rz), (width, ry, rz), RAIL_R, sides=RAIL_N)

    # ③ 親柱 — 各1間の中心。⭕ 継ぎ目(x=0 / width)に柱を置かないので、モジュールを
    #    突き付けても柱が二重にならない。
    posts = [KEN * (i + 0.5) for i in range(int(round(width / KEN)))]
    for px in posts:
        culm(m, (px, 0.0, 0.0), (px, height, 0.0), POST_R, sides=POST_N)

    # ④ 結束 — 斜材が胴縁を越える所と、親柱が胴縁を越える所。
    for (p0, p1, t, z) in diag:
        for ry in RAIL_Y:
            if not (min(p0[1], p1[1]) + 0.06 < ry < max(p0[1], p1[1]) - 0.06):
                continue
            s = (ry - p0[1]) / (p1[1] - p0[1])
            cx = p0[0] + (p1[0] - p0[0]) * s
            # ⚠ 径は**斜材の内側の皮から胴縁の外側の皮まで**で決める(決め打ちにすると
            #    はみ出して「黒い角板」に見える。2026-09-22 の1回目で踏んだ)。
            lo_z, hi_z = DIAG_Z - DIAG_R, RAIL_Z + RAIL_R
            cz = (lo_z + hi_z) / 2.0 * (1.0 if z > 0 else -1.0)
            nawa(m, (cx, ry, cz), t, (hi_z - lo_z) / 2.0, length=0.065, sides=8)
    for px in posts:
        for ry in RAIL_Y:
            # 親柱と胴縁の結束。⛔ 胴縁の外まで径を伸ばさない — 立面で 22cm の黒帯になる。
            nawa(m, (px, ry, 0.0), (0.0, 1.0, 0.0), POST_R + 0.020, length=0.085, sides=8)

    return m


def build(width=L, height=H):
    mat, rect = VM.vk_mat(V, SRC, MAT, UV_SIDE)
    m = yarai(width, height)
    o = m.to_object("Typ_Takeyarai", [mat])
    # ピボット = 走りの中心・足元・柱の芯。⚠ **原点の上へメッシュを寄せてから**焼く
    #   (`set_origin` で原点だけ動かすと FBX ノードに平行移動が残り、Unity で子が 1.8m 横へずれる。
    #    `build_typ_machiya` と同じく「原点を中心に組む」へ揃えた)
    o.location = (-width / 2.0, 0.0, 0.0)
    V.sel([o])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


# ══════════════════════════════════════════════════════════════════════
#  検め
# ══════════════════════════════════════════════════════════════════════
def measure(o, label="Typ_Takeyarai"):
    mn, mx = V.bbox([o])
    # Blender Z-up → Unity: 幅 = X / 高さ = Blender Z / 厚み = Blender Y
    w, h, d = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    print("[矢来] %s 実寸(Unity) W %.3f × H %.3f × D %.3f  面 %d 頂点 %d"
          % (label, w, h, d, len(o.data.polygons), len(o.data.vertices)))
    print("[矢来]   Blender bbox x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f"
          % (mn.x, mx.x, mn.y, mx.y, mn.z, mx.z))
    return w, h, d


def symmetry(o):
    """**走りの中心を通る鉛直軸まわりの 180° 回転**で重なるか(= 継ぎ目の位相が端で揃うか)。

    ⚠ **集合で比べる**(⛔ 並べた列で比べない — 同じ座標の重複数の差で偽の非対称が出る。
      memory: logical-axis-and-mirror-checks)。
    ⛔ **単純な左右鏡映では合わない**(合ってはいけない)— 表の筋違が「/」・裏が「\」なので、
      左右だけ反せば表に「\」が来る。そこは**姿の性格が変わらない**ので実害が無く、
      書き出しで Unity X が反転しても取り違えようがない。C2 が 0 なら両端の位相は揃う。"""
    mn, mx = V.bbox([o])
    cx, cy = (mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0
    A, B = set(), set()
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        A.add((round(w.x, 4), round(w.y, 4), round(w.z, 4)))
        B.add((round(2 * cx - w.x, 4), round(2 * cy - w.y, 4), round(w.z, 4)))
    bad = len(A ^ B)
    print("[矢来] C2(鉛直軸まわり180°)検算: 頂点集合 %d / 差 %d %s"
          % (len(A), bad, "⭕" if bad == 0 else "⛔"))
    return bad


def solidity(o):
    """見付の充実率 — 正面(厚み方向)から見た「竹が塞いでいる面積」の割合を光線で数える。
    ⛔ 目視だけで「透けている」と言わない(EDO-0363 の差し戻しがまさにそれ)。"""
    import mathutils
    mn, mx = V.bbox([o])
    bpy.context.view_layer.update()
    dep = bpy.context.evaluated_depsgraph_get()
    nx, ny = 200, 110
    hit = 0
    tot = 0
    for i in range(nx):
        x = mn.x + (mx.x - mn.x) * (i + 0.5) / nx
        for j in range(ny):
            z = 0.10 + (mx.z - 0.10) * (j + 0.5) / ny       # 地面に入る 0.10 は数えない
            ok, _, _, _, _, _ = bpy.context.scene.ray_cast(
                dep, (x, mn.y - 1.0, z), (0.0, 1.0, 0.0), distance=10.0)
            tot += 1
            if ok:
                hit += 1
    print("[矢来] 見付の充実率 %.1f%%(抜け %.1f%%)— 板塀は 100%%" % (100.0 * hit / tot, 100.0 * (tot - hit) / tot))
    return hit / float(tot)


def shot(path, cam, look, ortho=None, magenta=False, res=(1600, 900)):
    """⚠ `V.studio` はカメラも灯も**足す**ので、呼ぶたびに前のを片付ける
    (3枚目が2倍明るくなる)。⭕ マゼンタの空は**穴を見つけるため**
    (memory: magenta-background-finds-holes)。"""
    for o in list(bpy.data.objects):
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o, do_unlink=True)
    V.studio(cam, look, ortho_scale=ortho, res=res)
    if magenta:
        bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
    os.makedirs(SHOT, exist_ok=True)
    V.render(os.path.join(SHOT, path))


def render_part(o):
    V.hook_textures()
    mn, mx = V.bbox([o])
    cx = (mn.x + mx.x) / 2.0
    w = mx.x - mn.x
    # ① 立面(マゼンタの空 — 抜けている所がマゼンタで出る = 透けている所)
    shot("yarai_elev.png", (cx, -14.0, 1.0), (cx, 0.0, 1.0), ortho=w * 1.12, magenta=True)
    # ② 立面(ふつうの空。竹と縄の色を見る ⛔ マゼンタの空は照明でもあるので色は読めない)
    shot("yarai_elev_lit.png", (cx, -14.0, 1.0), (cx, 0.0, 1.0), ortho=w * 1.12)
    # ③ 寄り(斜め・目の高さ。竹の丸み・結束・厚みの層が読める)
    shot("yarai_near.png", (cx - 4.2, -4.0, 1.75), (cx + 0.3, 0.0, 1.00))
    # ④ 真上(表裏の層と親柱の位置)
    shot("yarai_top.png", (cx, 0.0, 9.0), (cx, 0.0, 0.0), ortho=w * 1.12)
    print("[矢来] 検証レンダ: Screenshots/yarai_{elev,near,top}.png")


def narabe():
    """⭐ **合否条件そのもの** — 穂垣 `Eg.Hogaki5` と並べ、**20m 離れた目の高さ**から焼く。
    ⛔ 単体の立面では「板塀と見分けが付くか」は読めない(memory: narabe-check-and-fbx-byte-noise)。
    後ろに色分けした的を並べ、**矢来では透けて見え・穂垣では見えない**ことを一枚で示す。
    ⛔ 何も書き出さない。"""
    V.reset()
    run_len = 7 * L                                  # 25.45m ぶん
    # ① 矢来の run(手前 y=0)。⚠ build() を7回呼ぶと FBX を7回読んで材が複製されるので1枚だけ組む
    base = build()
    ys = []
    for k in range(7):
        c = base.copy()
        c.data = base.data.copy()
        bpy.context.scene.collection.objects.link(c)
        c.location = (L * (k + 0.5) - run_len / 2.0, 0.0, -0.10)   # 0.10 だけ土へ入れる
        ys.append(c)
    bpy.data.objects.remove(base, do_unlink=True)
    V.sel(ys)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.join(ys, "Yarai_run")

    # ② 穂垣の run(奥 y=+9)— obj は素寸なので ES=1.818 倍(EdoAssets.Eg の規約)
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(V.REPO, "Assets", "edogoyomi",
                                                "obj_hogaki", "hogaki5.obj"))
    got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    h0 = V.join(got, "Hogaki_ref")
    V.sel([h0])
    bpy.ops.transform.resize(value=(1.818,) * 3, center_override=(0, 0, 0))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mn, mx = V.bbox([h0])
    hw = mx.x - mn.x
    hs = []
    for k in range(int(math.ceil(run_len / hw))):
        c = h0.copy(); c.data = h0.data.copy()
        bpy.context.scene.collection.objects.link(c)
        c.location = (hw * k - run_len / 2.0 - mn.x, 9.0 - mn.y, -mn.z - 0.10)
        hs.append(c)
    bpy.data.objects.remove(h0, do_unlink=True)
    V.sel(hs)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    hog = V.join(hs, "Hogaki_run")

    # ③ 後ろの的(透けの証拠)— 矢来の向こう・穂垣の向こうに同じ列を置く
    marks = []
    for row, back in ((0, 3.0), (1, 12.0)):
        for i in range(7):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.28, depth=1.7, vertices=12,
                                                location=(-run_len / 2.0 + 1.8 + i * 3.6, back, 0.85))
            c = bpy.context.object
            c.name = "mark_%d_%d" % (row, i)
            mm = bpy.data.materials.new("mark")
            mm.use_nodes = True
            b = mm.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = (0.90, 0.15, 0.10, 1) if i % 2 == 0 else (0.95, 0.92, 0.85, 1)
            c.data.materials.append(mm)
            marks.append(c)
    bpy.ops.mesh.primitive_plane_add(size=200.0, location=(0.0, 6.0, -0.12))

    V.hook_textures()
    # 20m 離れた目の高さ(1.60m)から。2列が同じ画角に入る
    shot("yarai_narabe_20m.png", (0.0, -20.0, 1.60), (0.0, 6.0, 1.10), res=(1800, 900))
    # 斜めから(格子の交叉と厚みが読める)
    shot("yarai_narabe_naname.png", (-16.0, -14.0, 2.4), (2.0, 4.0, 1.0), res=(1800, 900))
    print("[矢来] 並べ比べ: Screenshots/yarai_narabe_{20m,naname}.png  "
          "(手前=竹矢来 / 奥 9m=穂垣 Eg.Hogaki5・後ろの的で透けを見る)")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "narabe" in argv:
        narabe()
        return
    V.reset()
    o = build()
    w, h, d = measure(o)
    symmetry(o)
    solidity(o)
    if "--render" in argv:
        render_part(o)
    if "--no-export" not in argv:
        path = os.path.join(OUT, "Typ_Takeyarai_2ken.fbx")
        V.export_fbx([o], path)
        print("[矢来] 書き出し %s" % path)


main()
