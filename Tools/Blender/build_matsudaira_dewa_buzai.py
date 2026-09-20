# -*- coding: utf-8 -*-
"""**松江松平出羽守上屋敷 — 塞ぎの三部材**(雨押え / 渡廊下の框 / 切石の縁石)。

    blender --background --python Tools/Blender/build_matsudaira_dewa_buzai.py -- amaosae  [--render]
    blender --background --python Tools/Blender/build_matsudaira_dewa_buzai.py -- kamachi  [--render]
    blender --background --python Tools/Blender/build_matsudaira_dewa_buzai.py -- fuchi    [--render]
    blender --background --python Tools/Blender/build_matsudaira_dewa_buzai.py -- all      [--render]
    # 寸法を手で指定する(⛔ 常用しない。既定は指図と実測から引く)
    #   -- amaosae --dan 0.26 / -- kamachi --dan 0.301 / -- fuchi --run 17

━━━ 1. 雨押え(段違いの下屋の折れ目を塞ぐ)━━━━━━━━━━━━━━━━━━━━━━━━━

【なぜ要るか】施主裁定 B(EDO-0288・2026-09-20)で表向が 0.30m 下がり、渡廊下 3 本が
  `links[].dan`(v=29・框)で段を折るようになった。屋根も同じ線で折るが、**下屋は両流れで
  ピボットが「頭」**なので、段のぶんだけ**上下の葺き面のあいだに口が開く**
  (棟梁の実測 下の天端 29.245 / 上の下端 29.433 = **0.19m**。許容0の隙)。
  ⛔ **上の区間の頭を下げて葺き面を通す**のは採らない — 「葺き下ろす元は各区間が取り付く棟」
  という決着に反する(2026-09-20)。⇒ **部材で塞ぐ。**

【口の形は人が書かない。⭐ 生成器が実測する。】`make_rokageya` を 2 本焼いて段のぶん
  ずらして重ね、折れ目の線で**真下への光線**を落として
    下の当たり = 低い屋根の**最も高い**交点(瓦の山)
    上の当たり = 高い屋根の**最も低い**交点(瓦の裏・破風板の下端)
  を幅方向に刻んで読む。⇒ 部材の上端と下端は**その profile の従属値**。
  ⚠ 口は幅方向に一定ではない — **大棟の上では 0.013m しか開いていない**(低い側の大棟が
    高い側の瓦の裏まで届く)のに、流れの中ほどでは 0.19m 開く。⛔ 一定丈の板で塞がない。

【向きとピボット(Unity 座標)】幅 = X(**廊下の幅方向**)/ 高さ = Y / 厚み = Z、
  **+Z = 見え面 = 段の低い側**。ピボット = **廊下の芯・折れ目の線・低い区間の下屋の頭**
  (= 低い側の `Goten_Roof_RokaGeya_*` を据えた y と**同じ値**)。
  ⭕ 3 本とも廊下は v 走り・段は u 線なので、**`YawAlongU` でそのまま据わる**
    (局所 +X = 格子 +u = 廊下の幅 / 局所 +Z = 格子 −v = 低い側)。
  ⛔ 下屋の yaw をそのまま使わない(下屋は局所 +X が**走り**で、この部材とは 90° 違う)。

━━━ 2. 渡廊下の框(段を受ける一段)━━━━━━━━━━━━━━━━━━━━━━━━━━━

【なぜ要るか】在庫の `Goten_JodanKamachi_1ken` は**段 0.15 固定**で、しかも上の床板
  (見込み 0.55)を抱き込む形なので渡廊下には使えない(棟梁は桁材を段の高さへ縮めて
  仮に充てていた)。⇒ **段の高さを受ける框**を起こす。

【寸法】段 = **両側の落縁の天端の差**(27.040 → 27.341 = 0.301。⛔ 数は指図に無い従属値なので
  引数で受ける)。幅 = 廊下の 1間。
【向きとピボット】幅 = X / 高さ = Y / 見込み = Z、**+Z = 見え面 = 低い側**。
  ピボット = **幅の中心・低い側の床板の天端・框の見付面**(z=0)。
  ⇒ 据えるのは低い区間の `Goten_RokaEnita_1ken` と**同じ y**(あちらもピボット z=0 が板の天端)。
  ⭕ **躯体は Z ≤ 0(高い側)にしか出ない** — 段の柱は低い側に立つので干渉しない
    (棟梁の是正: 高い側に立てると下屋のけらばを突き抜ける)。
  ⚠ 蹴込板だけ Y −0.02 へ出る(低い側の床板 厚 0.0303 に噛ませて継ぎ目の光を消す)。

━━━ 3. 切石の縁石(白洲と平場の縁)━━━━━━━━━━━━━━━━━━━━━━━━━━

【なぜ要るか】指図 `fuchi` の 3 本(`F_Omote_N` / `F_Omote_NE` / `F_Omote_E`)に**部材の api が無い**。
  砂利を留める物が無い状態。在庫に切石の縁石は無い(`Own.SannoDan` は段石・`Own.Ishibashi` は橋)。

【⭐ 一つの型で落差 0 と落差 0.30 の両方を賄う】**天端を揃え、下に隠れる丈を変える** —
  天端を y=0 に置き、躯体は常に **y −0.48**(= 最大落差 0.30 + 根入れ 0.18)まで垂らす。
  ・`F_Omote_N`(落差 0.0)… 両側とも同じ高さなので**全丈が地中**。天端だけが砂利留めの見切りとして出る。
  ・`F_Omote_NE`(落差 0.30)… 低い側に 0.30 が出て、残り 0.18 が地中。
  ⇒ **同じ FBX が v=29 の 0.30m の平場の縁にもそのまま効く。**
  ⛔ `SeatBottom` で据えない(躯体が Y −0.48 へ垂れている)。

【向きとピボット】走り = X / 高さ = Y / 見込み = Z、**+Z = 見え面 = 低い側**。
  ピボット = **走りの中心・天端・縁の線(見付面)**。躯体は Z ∈ [−w, 0] = **高い側**に置く
  (`fuchi[].w` 0.36 は平面の見込み)。
【材】`Kirishi`(叩き仕上げの切石。`Assets/Edo/Materials/Sanno/Kirishi.mat`)。⛔ 新規に作らない。
  ⚠ タイルは **1.05m**(`build_sanno_torii` と同値)。⛔ `build_sanno_buzai.KIRISHI_TILE` 0.44 を
    使わない — `T_Kirishi_Normal.png` は 2×2 の継ぎ目入りなので、0.44 だと 0.22m ごとに目地が立ち
    **一本の縁石が小口積みの壁**に見える(2026-09-20 に鳥居で実見)。

━━━ 落とし穴 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ・⚠ `export_fbx` を通した後は bbox が 0 に潰れる。**測るのもレンダも書き出しの前に。**
  ・⚠ `o.location` を書いた直後の `matrix_world` は古い。測る前に `view_layer.update()`。
  ・⛔ 検証レンダの地面を z=0 に置かない(雨押えはピボットが「頭」で躯体が z<0)。
  ・⛔⛔ `Unity X = −(Blender X)`。この 3 部材はどれも **Unity X について鏡像対称**に作ってある
    ので符号反転は恒等 — 焼いた直後に `check_mirror_x` で確かめる。
"""
import bpy, bmesh, sys, os, math
import mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_goten_roof as GR
import build_sanno_buzai as SB          # _stone(切石1枚)/ check_mirror_x / unity_verts / rng_of
import build_tateishi as BT             # ensure_outward

KEN = V.KEN
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "matsudaira_dewa_sashizu.json")
SHOT = os.path.join(V.REPO, "Screenshots")
OUT_GOTEN = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Parts"))
OUT_ROOF = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Roofs"))
OUT_FUCHI = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Fuchi"))

# ---- 雨押え: 作りの値【U 指図に無い。塞ぐための呑み代】--------------------------
# ⛔⛔ **「口の丈ぶんの板を1枚立てる」では塞がらない。**口は板ではなく**管**で、
#   ① 走り方向(低い側の空 ↔ 高い屋根の裏)と ② **幅方向(廊下の一方の軒先 ↔ 反対の軒先)**の
#   両方に抜ける。⚠ ②が本体 — 段違いの折れ目は**廊下の横から覗くと 3.7m の隙間が素通し**になる。
#   ⇒ 部材は口の断面を**埋める**(= 小壁 + 面戸)。下は瓦の**谷**より下へ、上は上の屋根の
#   **裏板**より上へ差し込む。⭕ 瓦の山は部材の中に隠れる(実物の面戸と同じ納まり)。
AMA_PAD = 0.006     # 屋根の小口より外へ出す量[m]。⛔ 面一にすると同一平面で z-fight する
AMA_TUCK = 0.010    # 上端を高い屋根の**裏**へ差し込む量[m]。⛔ 0 だと横一文字の光の筋が出る
AMA_DIP = 0.010     # 下端を低い屋根の瓦の**谷**より下へ落とす量[m]
AMA_MAXDROP = 0.075  # 下端が**名目の屋根面**より下がれる上限[m]。
#   ⚠ 軒先では低い屋根の軒瓦・裏甲が名目面より 0.11 下にあるので、「走り方向の最小」を
#     そのまま取ると**部材が軒の下へ 5cm 垂れて鰭に見える**(2026-09-20 に検証レンダで実見)。
#   ⇒ ここで頭打ちにする。⛔ 締めすぎると瓦の谷に水路が残るので、素通しの検査で必ず確かめる。
AMA_NY = 141        # 幅方向の刻み数。⚠ 瓦の段の周期 0.357 を 13 点で拾う(粗いと谷が抜ける)
AMA_NX = 61         # 走り方向の読みの刻み(破風板の内面を探すため)
AMA_STEP_TOL = 0.02  # 高い屋根の裏が「破風板」か「裏板」かを分ける段差[m]

# ---- 框: 作りの値【U 指図に無い】------------------------------------------------
KAM_MITSUKE = 0.15  # 框の見付(丈)[m] = 5寸。⛔ 段の丈より大きくしない(下で切り詰める)
KAM_MIKOMI = 0.12   # 框の見込み(高い側へ出る奥行)[m] = 4寸
KAM_KEKOMI_T = 0.030   # 蹴込板の厚[m] = 1寸
KAM_KEKOMI_BACK = 0.025  # 蹴込板を框の面から引く量[m](蹴込み)
KAM_BITE = 0.020    # 蹴込板の下端を低い側の床板へ噛ませる量[m](板厚 0.0303 の内側)

# ---- 縁石: 作りの値【U 指図に無い】----------------------------------------------
FU_DROP_MAX = 0.30  # 賄う最大の落差[m](指図 `fuchi[].drop` の最大)
FU_ROOT = 0.18      # 根入れ(落差の下にさらに地中へ垂らす丈)[m]
FU_STONE = 1.20     # 石1枚の目安の長さ[m]
FU_TILE = 1.05      # `Kirishi` のタイルの実寸[m]。⛔ 0.44 にしない(小口積みに見える)
FU_CHAMFER = 0.015  # 稜の面取り[m](加工石。`build_hiraishi.gen_ishibashi` と同幅)


def doc():
    import json
    with open(SASHIZU, encoding="utf-8") as f:
        return json.load(f)


def report(o, name, extra=""):
    """**Unity 実寸**で刷る(⛔ Blender の bbox をそのまま読まない)。"""
    uv = SB.unity_verts(o)
    xs = [t[0] for t in uv]; ys = [t[1] for t in uv]; zs = [t[2] for t in uv]
    print("[dewa-buzai] %-34s Unity W(X)=%.3f H(Y)=%.3f D(Z)=%.3f | X %.3f..%.3f  "
          "Y %.3f..%.3f  Z %.3f..%.3f | 面=%d 材=%s %s"
          % (name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
             len(o.data.polygons), [m.name for m in o.data.materials], extra))
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


# =====================================================================
# 共通: 幅方向に z の上下を持つ「帯」を押し出す
# =====================================================================
def _strip(name, ys, z0s, z1s, x0, x1, mat, uv_rect):
    """y を刻んで (z0, z1) の帯(閉じた管)を作る。
    **測る枠**(M枠)= x: 走り(低い側が −x)/ y: 幅 / z: 高さ。⇒ 最後に `V.rotate_z(90)` で
    書き出しの枠へ回す(`make_amaosae` の末尾。理由はそちらの註)。

    ⛔ `V.box` で作らない — 上下の縁が**幅方向に一定でない**(流れの勾配と瓦のうねり)。
    ⛔⛔ **巻き順を `recalc_face_normals` に任せない** — 面ごとに頂点を分けている
      (UV を面ごとに決めるため)ので、bmesh から見ると**面が全部バラバラの連結成分**になり
      向きが決まらない。⇒ 下のように**手で外向きに並べる**。
    ⚠ 木理は**長手(= 幅方向 y)へ流す**。`WOOD_UV` は縦長の帯で木理が v 方向なので、
      **長手 → v 全域 / 板幅 → u の細い帯**(README 2026-09-04 の注)。"""
    n = len(ys)
    assert x1 > x0
    verts, faces, uvs = [], [], []
    u0, v0, u1, v1 = uv_rect
    um = u0 + (u1 - u0) * 0.35

    def add_quad(pts, uu):
        i = len(verts)
        verts.extend(pts)
        faces.append([i, i + 1, i + 2, i + 3])
        uvs.extend(uu)

    for k in range(n - 1):
        ya, yb = ys[k], ys[k + 1]
        va = v0 + (v1 - v0) * (k / float(n - 1))
        vb = v0 + (v1 - v0) * ((k + 1) / float(n - 1))
        a0, a1 = z0s[k], z1s[k]
        b0, b1 = z0s[k + 1], z1s[k + 1]
        # 見え面(x0 側・法線 −x)
        add_quad([(x0, ya, a0), (x0, ya, a1), (x0, yb, b1), (x0, yb, b0)],
                 [(u0, va), (um, va), (um, vb), (u0, vb)])
        # 裏(x1 側・法線 +x)
        add_quad([(x1, ya, a0), (x1, yb, b0), (x1, yb, b1), (x1, ya, a1)],
                 [(um, va), (um, vb), (u1, vb), (u1, va)])
        # 天端(法線 +z)
        add_quad([(x0, ya, a1), (x1, ya, a1), (x1, yb, b1), (x0, yb, b1)],
                 [(u0, va), (u1, va), (u1, vb), (u0, vb)])
        # 底(法線 −z)
        add_quad([(x0, ya, a0), (x0, yb, b0), (x1, yb, b0), (x1, ya, a0)],
                 [(u0, va), (u0, vb), (u1, vb), (u1, va)])
    # 両端の小口
    y = ys[0]
    add_quad([(x0, y, z0s[0]), (x1, y, z0s[0]), (x1, y, z1s[0]), (x0, y, z1s[0])],
             [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])          # 法線 −y
    y = ys[-1]
    add_quad([(x0, y, z0s[-1]), (x0, y, z1s[-1]), (x1, y, z1s[-1]), (x1, y, z0s[-1])],
             [(u0, v0), (u0, v1), (u1, v1), (u1, v0)])          # 法線 +y
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(p) for p in verts], [], faces)
    me.update()
    me.materials.append(mat)
    uvl = me.uv_layers.new(name="UVMap")
    for j, dd in enumerate(uvl.data):
        dd.uv = uvs[j]
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# =====================================================================
# 1. 雨押え
# =====================================================================
def _ray_z(o, x, y, top=8.0, want='max'):
    """(x, y) から真下へ落とし、交点の z を全部拾って最大/最小を返す。無ければ None。
    ⚠ 取り込んだオブジェクトでなく**この場で組んだ**メッシュなので matrix_world は素直だが、
      それでも `matrix_world.inverted()` で局所へ直してから投げる(README 2026-09-20)。"""
    mw = o.matrix_world
    inv = mw.inverted()
    org = inv @ Vector((x, y, top))
    d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hits, cur = [], org
    for _ in range(16):
        ok, loc, nrm, idx = o.ray_cast(cur, d, distance=400.0)
        if not ok:
            break
        hits.append((mw @ loc).z)
        cur = loc + d * 1e-4
    if not hits:
        return None
    return max(hits) if want == 'max' else min(hits)


def _pair(step, width=KEN, kobai=0.40, noki=0.90, seg=2):
    """段違いの下屋 2 本を、折れ目の線 x=0 で突き合わせて置く。
    低い区間 = x<0(頭 z=0)/ 高い区間 = x>0(頭 z=step)。
    ⭐ `make_rokageya` のピボットは (L/2, 幅の芯, 頭)。"""
    lo = GR.make_rokageya(seg * KEN, width, name="__LO", kobai=kobai, noki=noki)
    lo.location = Vector((-seg * KEN / 2.0, 0.0, 0.0))
    hi = GR.make_rokageya(seg * KEN, width, name="__HI", kobai=kobai, noki=noki)
    hi.location = Vector((+seg * KEN / 2.0, 0.0, step))
    bpy.context.view_layer.update()
    return lo, hi


def _xspan(lo, hi):
    """口の走り方向の範囲 = [高い屋根の小口, 低い屋根の小口] を**実測**する。
    ⛔ 0.169 のような数を書かない(`make_rokageya` の `end` と破風板の厚から出る従属値)。"""
    bpy.context.view_layer.update()
    hx = min((hi.matrix_world @ v.co).x for v in hi.data.vertices)
    lx = max((lo.matrix_world @ v.co).x for v in lo.data.vertices)
    return hx, lx


def _fill(vals, ys):
    """None を前後の有効な点から**線形に外挿**して埋める(profile は y に対しほぼ直線)。"""
    idx = [i for i, q in enumerate(vals) if q is not None]
    if len(idx) < 2:
        raise SystemExit("[dewa-buzai] ⛔ profile が読めない")
    a, b = idx[0], idx[1]
    ka = (vals[b] - vals[a]) / (ys[b] - ys[a])
    c, d = idx[-2], idx[-1]
    kd = (vals[d] - vals[c]) / (ys[d] - ys[c])
    out = list(vals)
    for i in range(len(vals)):
        if out[i] is not None:
            continue
        if i < a:
            out[i] = vals[a] + ka * (ys[i] - ys[a])
        elif i > d:
            out[i] = vals[d] + kd * (ys[i] - ys[d])
        else:
            lo_i = max(j for j in idx if j < i)
            hi_i = min(j for j in idx if j > i)
            f = (ys[i] - ys[lo_i]) / (ys[hi_i] - ys[lo_i])
            out[i] = vals[lo_i] + (vals[hi_i] - vals[lo_i]) * f
    return out


def measure_kuchi(lo, hi, width=KEN, noki=0.90, kobai=0.40):
    """折れ目に開く**口の断面** を実測する。返り値 = (ys, bot, topA, topB, x0, xs, x1, gaps)。

    ・`bot[i]`  … 幅 y=ys[i] における**低い屋根の天端の最小**(= 瓦の谷)。
      ⭐ **min を取る**のが要点 — これより下に部材の底を置けば、瓦の山は部材の中に入り、
        谷の水路(幅方向に通る溝)も潰れる。⛔ max(山)で取ると**瓦の谷が全長の水路**になって
        廊下の横から素通しになる(実測で谷は 0.104m 深い)。
    ・`topA` / `topB` … 高い屋根の裏。**破風板の下端**(x < xs)と**瓦の裏板**(x > xs)で
      段が付くので 2 区画に分ける。⭐ 各区画では **max を取る**(これより上に部材の天端を
      置けば裏へ差し込まれる)。
    ⭐⭐ **左右(幅方向)に対称化する。**瓦の位相は南北の流れで違うので実測は 5cm ほど非対称に
      出るが、**部材まで非対称に焼くと `Unity X = −(Blender X)` の符号反転が効いてしまう**
      (帯割りで鏡像事故を起こしたのと同じ型)。⇒ 対の点どうしで下は min・上は max を取る。"""
    hx, lx = _xspan(lo, hi)
    x0, x1 = hx - AMA_PAD, lx + AMA_PAD
    xs_all = [hx + (lx - hx) * k / float(AMA_NX - 1) for k in range(AMA_NX)]
    ym = width / 2.0
    y_edge = ym + noki
    n = AMA_NY
    yy = [-y_edge + 2.0 * y_edge * i / float(n - 1) for i in range(n)]
    # --- 破風板の内面 xs を探す --------------------------------------------------
    # ⛔⛔ **「裏の最大」を閾値にして拾わない。**破風板と瓦場の継ぎ目に**幅 6mm の
    #   一枚もの(裏の無い面)**が挟まっていて、そこだけ値が 0.12 跳ねる。max を基準にすると
    #   **全区間が『破風板』と判定されて高い側の区画が空になる**(2026-09-20 に踏んだ)。
    # ⭕ **高い側(瓦の裏板)の端の値から手前へ走査して、平らな区間が切れる所**で割る。
    #   ⇒ 跳ねた一枚は破風板側の区画に入り、そちらの天端が 1cm 上がるだけで済む
    #     (破風板の天端よりは低いので隠れる)。
    step_x = (xs_all[1] - xs_all[0])
    xs_split = x0
    for ysamp in (ym * 0.35, ym * 0.6, ym * 0.85, ym * 1.3):
        hb = [_ray_z(hi, x, ysamp, want='min') for x in xs_all]
        idx = [k for k, q in enumerate(hb) if q is not None]
        if len(idx) < 4:
            continue
        far = hb[idx[-1]]
        k = idx[-1]
        while k >= idx[0] and hb[k] is not None and abs(hb[k] - far) <= AMA_STEP_TOL:
            k -= 1
        if k >= idx[0]:
            xs_split = max(xs_split, xs_all[k] + step_x / 2.0)
    if xs_split <= x0 + 1e-9:
        xs_split = x0 + step_x            # 破風板が見つからない場合でも1区画は作る
    # --- y ごとに断面を読む -------------------------------------------------------
    B, TA, TB, G = [None] * n, [None] * n, [None] * n, [None] * n
    for i, y in enumerate(yy):
        lb = [q for q in (_ray_z(lo, x, y, want='max') for x in xs_all) if q is not None]
        ta = [q for q in (_ray_z(hi, x, y, want='min')
                          for x in xs_all if x <= xs_split) if q is not None]
        tb = [q for q in (_ray_z(hi, x, y, want='min')
                          for x in xs_all if x > xs_split) if q is not None]
        if lb:
            B[i] = min(lb)
        if ta:
            TA[i] = max(ta)
        if tb:
            TB[i] = max(tb)
        # 棟梁が測った「口」= **廊下の芯の走り(x=0)**での 瓦の山 ↔ 上の屋根の裏
        c0 = _ray_z(lo, 0.0, y, want='max')
        c1 = _ray_z(hi, 0.0, y, want='min')
        if c0 is not None and c1 is not None:
            G[i] = c1 - c0
    B, TA, TB = _fill(B, yy), _fill(TA, yy), _fill(TB, yy)
    # ⚠ 名目の屋根面より `AMA_MAXDROP` 以上は下げない(軒先で鰭になる。定数の註)
    B = [max(B[i], -abs(yy[i]) * kobai - AMA_MAXDROP + AMA_DIP) for i in range(n)]
    # 対称化(⛔ 非対称に焼かない)。⚠ **外挿のあとに掛ける** — `_fill` は端の 2 点から
    #   勾配を作るので左右で結果が違い、先に対称化しても端で崩れる(2026-09-20 に踏んだ)。
    for arr, how in ((B, min), (TA, max), (TB, max)):
        for i in range(n):
            j = n - 1 - i
            arr[i] = how(arr[i], arr[j])
    gaps = [q for q in G if q is not None]
    return yy, B, TA, TB, x0, xs_split, x1, gaps


def make_amaosae(prof, name):
    """段違いの下屋の折れ目を塞ぐ**雨押え**。1メッシュ。`prof` = `measure_kuchi` の返り値。

    ⭐⭐ **軸の鎖。**組むのは**測る枠**(x = 走り・低い側が −x / y = 幅 / z = 高さ)。
      屋根 2 本と同じ枠なので、**検査もレンダもこの枠のまま**やる。
      書き出しは `Unity X = −BX / Unity Y = BZ / Unity Z = −BY` なので、このままでは
      **Unity X が走り**になってしまう(規約の「幅 = X」に反する)。⇒ **書き出しの直前に**
      `to_export_frame()` = `rotate_z(+90)` = (x,y) → (−y, x) を掛けると
      **Unity X = 幅 / Unity +Z = 低い側** になる。
      ⛔ x と y を入れ替える(鏡映・行列式 −1)で済ませない — 面が全部裏返る。"""
    ys, B, TA, TB, x0, xs, x1, gaps = prof
    if len(ys) < 8:
        raise SystemExit("[dewa-buzai] ⛔ 口の profile が読めない(点 %d)" % len(ys))
    p = GR.palette()
    z0 = [B[i] - AMA_DIP for i in range(len(ys))]
    zA = [max(TA[i] + AMA_TUCK, z0[i] + 0.01) for i in range(len(ys))]
    zB = [max(TB[i] + AMA_TUCK, z0[i] + 0.01) for i in range(len(ys))]
    # 破風板の下(低い側)— 天端は破風板の下端より上へ
    a = _strip(name + "_hafu", ys, z0, zA, x0, xs, p['wood'], GR.WOOD_UV)
    # 裏板の下(高い側)— 天端は瓦の裏板より上へ
    b = _strip(name + "_men", ys, z0, zB, xs, x1, p['wood'], GR.WOOD_UV)
    V.dedup_materials()
    o = V.join([a, b], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


def to_export_frame(o):
    """測る枠 → 書き出しの枠(`make_amaosae` の註)。⛔ 検査とレンダが済むまで掛けない。

    ⛔⛔ **`V.rotate_z(90)` を使わない。**あれは `Matrix.Rotation(radians(90))` なので
      cos が **6.1e-17** で残り、回したあとの座標に **±(相手の軸)×6e-17 の汚れ**が乗る。
      ⚠ これだけで**左右対称の検算が落ちる**: 汚れの符号が幅の正負で逆なので、
      端数が `round()` の .5 の刃の上(実際に 破風板の内面 x=−0.09295 = −929.5)に乗ると
      片側だけ切り上がる。2026-09-20 に実際に踏んで、profile を 3 度疑った。
    ⭕ **整数だけの行列**で (x, y, z) → (−y, x, z)。行列式 +1(回転)なので巻き順は保たれる。"""
    o.data.transform(mathutils.Matrix(((0, -1, 0, 0), (1, 0, 0, 0),
                                       (0, 0, 1, 0), (0, 0, 0, 1))))
    o.data.update()
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


def amaosae_name(wken, step):
    """⚠ mm は `round`(`floor` は浮動小数で 1mm 落ちる)。"""
    return "Goten_Amaosae_%sken_d%d" % (GR.KenTag(wken), int(round(step * 1000.0)))


def amaosae_check(o, prof, step):
    """⭕ 焼いた直後の自動検算(**書き出しの枠で**)。⛔ 見た目では 1cm の光の筋は読めない。"""
    ys, B, TA, TB, x0, xs, x1, gaps = prof
    ok = [("左右対称(Unity X = −Blender X が恒等)", SB.check_mirror_x(o), "")]
    uv = SB.unity_verts(o)
    xu = [t[0] for t in uv]; yu = [t[1] for t in uv]; zu = [t[2] for t in uv]
    ok.append(("幅が屋根の外形いっぱい", abs((max(xu) - min(xu)) - (ys[-1] - ys[0])) < 1e-3,
               "W=%.3f 期待 %.3f" % (max(xu) - min(xu), ys[-1] - ys[0])))
    ok.append(("見込みが口の走り幅いっぱい", abs((max(zu) - min(zu)) - (x1 - x0)) < 1e-3,
               "D=%.3f 期待 %.3f" % (max(zu) - min(zu), x1 - x0)))
    ok.append(("見え面(+Z)が低い側の小口", abs(max(zu) + x0) < 1e-3,
               "Zmax=%.4f 期待 %.4f" % (max(zu), -x0)))
    ok.append(("底が瓦の谷より下(min − 呑み代)", abs(min(yu) - (min(B) - AMA_DIP)) < 1e-4,
               "Ymin=%.4f 谷=%.4f" % (min(yu), min(B))))
    ok.append(("天端が上の屋根の裏より上(max + 呑み代)",
               max(yu) >= max(max(TA), max(TB)) + AMA_TUCK - 1e-4,
               "Ymax=%.4f 裏=%.4f" % (max(yu), max(max(TA), max(TB)))))
    ok.append(("天端が段の頭を越えない", max(yu) <= step + 0.16,
               "Ymax=%.4f 段=%.3f" % (max(yu), step)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    bad = [t for t in ok if not t[1]]
    if bad:
        raise SystemExit("[dewa-buzai] ⛔ 雨押えの検算が落ちた: %s"
                         % ", ".join(t[0] for t in bad))


def _shoot(bodies, org, d, dist=2000.0):
    for b in bodies:
        inv = b.matrix_world.inverted()
        okk, loc, nrm, idx = b.ray_cast(inv @ org, (inv.to_3x3() @ d).normalized(), distance=dist)
        if okk:
            return True
    return False


def amaosae_seethrough(lo, hi, o, prof, width=KEN, noki=0.90):
    """⭐⭐ **素通しの検査。**⛔ レンダの画素では数えない(背景が同時に照明なので偽陽性が出る
    — README「素通し(穴)の検査のしかた」)。⭕ **口の中を貫く光線**を格子で投げ、
    どれかが**何にも当たらずに**抜けたら穴。⭐⭐ **2 方向とも投げる**:
      ① 走り方向(低い側の空 ↔ 高い屋根の裏)
      ② **幅方向(廊下の一方の軒先 ↔ 反対の軒先)** ← ⛔ こちらを忘れない。段違いの折れ目を
         廊下の横から覗いたときに見える 3.7m の隙間は**この向き**に通る。"""
    ys, B, TA, TB, x0, xs, x1, gaps = prof
    bodies = [lo, hi, o]
    y_end = width / 2.0 + noki
    res = {}
    for tag in ("走り", "幅"):
        holes, total, worst = 0, 0, None
        for i in range(len(ys)):
            y = ys[i]
            if abs(y) > y_end - 0.02:
                continue
            lo_z, hi_z = B[i], max(TA[i], TB[i])
            if hi_z - lo_z < 0.004:
                continue
            for k in range(9):
                z = lo_z + (hi_z - lo_z) * (k + 0.5) / 9.0
                if tag == "走り":
                    org, d = Vector((x0 - 1.0, y, z)), Vector((1, 0, 0))
                else:
                    org, d = Vector(((x0 + x1) / 2.0, -y_end - 1.0, z)), Vector((0, 1, 0))
                total += 1
                if not _shoot(bodies, org, d):
                    holes += 1
                    if worst is None:
                        worst = (y, z)
        res[tag] = (holes, total)
        print("[dewa-buzai] 素通しの検査(%s方向に貫く光線): 投げ %d / 抜け **%d**%s"
              % (tag, total, holes, ("  最初の抜け y=%.3f z=%.3f" % worst) if worst else ""))
    # ⭐ 幅方向は「口のどこか1本でも抜けたら素通し」なので、走りの刻みも変えて総当たりする
    hx = 0
    for k in range(25):
        x = x0 + (x1 - x0) * (k + 0.5) / 25.0
        for i in range(0, len(ys), 7):
            lo_z, hi_z = B[i], max(TA[i], TB[i])
            if hi_z - lo_z < 0.004:
                continue
            for m in range(5):
                z = lo_z + (hi_z - lo_z) * (m + 0.5) / 5.0
                if not _shoot(bodies, Vector((x, -y_end - 1.0, z)), Vector((0, 1, 0))):
                    hx += 1
    print("[dewa-buzai] 素通しの検査(幅方向・走りも総当たり 25×%d×5): 抜け **%d**"
          % (len(range(0, len(ys), 7)), hx))
    return res["走り"][0] + res["幅"][0] + hx, res["走り"][1] + res["幅"][1]


def render_amaosae(lo, hi, o, tag, prof):
    """⭐ 見るのは 5 点 — **軒先の小口の寄り**(不良が実際に見えるのはここ。廊下の横から覗くと
    段違いの口が 3.7m の隙間として通る)/ 折れ目の寄り / 目の高さ / 真上(部材が瓦の上へ
    飛び出していないか)/ 見上げ(面戸が瓦の谷を潰しているか)。
    ⛔ **単体のレンダでは判定できない** — 必ず下屋 2 本と重ねて焼く。"""
    ys, B, TA, TB, x0, xs, x1, gaps = prof
    z_koguchi = (B[0] + TB[0]) / 2.0
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([lo, hi, o])
    cx, cy = (mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0
    out = []

    def shot(sub, cam, look, ortho=None, res=(1600, 1000)):
        for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
            bpy.data.objects.remove(c, do_unlink=True)
        for pl in [c for c in bpy.data.objects if c.name.startswith("Plane")]:
            bpy.data.objects.remove(pl, do_unlink=True)
        # ⛔ 地面を z=0 に置かない(下屋はピボットが頭で躯体が z<0)
        bpy.ops.mesh.primitive_plane_add(size=40, location=(cx, cy, mn.z - 1.0))
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "%s_%s.png" % (tag, sub))
        V.render(f)
        out.append(f)
        print("RENDER %s" % f)

    zc = (mn.z + mx.z) / 2.0
    ye = mn.y
    # 1) ⭐⭐ 軒先の小口を真横(正射影)から寄って — **不良が見える唯一の向き**
    shot("01_koguchi", (cx, ye - 5.0, z_koguchi), (cx, ye + 0.5, z_koguchi),
         ortho=1.4, res=(1500, 1000))
    # 2) 軒先の小口を斜め下から(見上げ)— 面戸が瓦の谷を潰しているか
    shot("02_koguchi_miage", (cx - 0.9, ye - 1.5, z_koguchi - 0.55),
         (cx, ye + 0.35, z_koguchi + 0.02), res=(1500, 1000))
    # 3) 折れ目の寄り(低い側の斜め上から)— 面戸が瓦の上でどう見えるか
    shot("03_yori", (cx - 1.5, cy - 1.9, mx.z + 0.95), (cx + 0.05, cy - 0.35, zc),
         res=(1600, 1000))
    # 4) ⭐ 目の高さ — 廊下の横に立って折れ目を見上げる(地盤は頭から約 2.3 下・眼高 1.45)
    shot("04_medakasa", (cx - 0.3, ye - 6.0, -0.85), (cx, ye + 0.6, z_koguchi),
         res=(1700, 900))
    # 5) 真上 — 部材が瓦の上へ飛び出していないか
    shot("05_shinjo", (cx, cy, mx.z + 7.0), (cx, cy, mn.z),
         ortho=(mx.y - mn.y) * 1.2, res=(1400, 1400))
    return out


def build_amaosae(argv):
    dan = 0.26
    if "--dan" in argv:
        dan = float(argv[argv.index("--dan") + 1])
    d = doc()
    c = d["const"]
    kobai = c[d["roka"]["kobaiFrom"]]
    noki = c["nokiE"]
    name = amaosae_name(1.0, dan)
    V.reset()
    lo, hi = _pair(dan, KEN, kobai, noki)
    prof = measure_kuchi(lo, hi, KEN, noki, kobai)
    ys, B, TA, TB, x0, xs, x1, gaps = prof
    band = [max(TA[i], TB[i]) + AMA_TUCK - (B[i] - AMA_DIP) for i in range(len(ys))]
    print("[dewa-buzai] 口の実測(段 %.3f / 勾配 %.2f / 軒 %.2f): 幅 %.3f を %d 点 × 走り %.3f を "
          "%d 点で読む。廊下の芯の口(瓦の山 ↔ 上の屋根の裏)は **最大 %.3f / 最小 %.3f**"
          "(⛔ 一定でない)。破風板の内面 x=%.3f / 口の走り %.3f..%.3f / 部材の帯の丈 %.3f..%.3f"
          % (dan, kobai, noki, ys[-1] - ys[0], len(ys), x1 - x0, AMA_NX,
             max(gaps), min(gaps), xs, x0, x1, min(band), max(band)))
    o = make_amaosae(prof, name)
    holes, total = amaosae_seethrough(lo, hi, o, prof, KEN, noki)
    if "--render" in argv:
        for f in render_amaosae(lo, hi, o, "matsudaira_amaosae_d%d" % int(round(dan * 1000)), prof):
            pass
    for q in (lo, hi):
        bpy.data.objects.remove(q, do_unlink=True)
    to_export_frame(o)
    report(o, name, "段=%.3f 勾配=%.2f 軒=%.2f 素通し=%d/%d" % (dan, kobai, noki, holes, total))
    amaosae_check(o, prof, dan)
    if holes:
        raise SystemExit("[dewa-buzai] ⛔ 素通しが %d/%d 残っている — 書き出さない" % (holes, total))
    V.export_fbx(o, os.path.join(OUT_ROOF, name + ".fbx"))
    print("[dewa-buzai] ⭕ 雨押え → %s" % os.path.join(OUT_ROOF, name + ".fbx"))
    return name


# =====================================================================
# 2. 渡廊下の框
# =====================================================================
def kamachi_name(dan, wken=1.0):
    return "Goten_RokaKamachi_%sken_d%d" % (GR.KenTag(wken), int(round(dan * 1000.0)))


def make_kamachi(dan, w=KEN, name=None):
    """渡廊下の段を受ける框。Blender: x = 幅 / y = 見込み(+y = 高い側)/ z = 高さ(0 = 低い側の床天端)。
    ⇒ Unity: X = 幅 / Y = 高さ / **+Z = 低い側 = 見え面**(`export_fbx` が Blender +Y を Unity −Z へ写す)。"""
    name = name or kamachi_name(dan, w / KEN)
    p = GR.palette()
    mitsuke = min(KAM_MITSUKE, dan - 0.06)      # ⛔ 蹴込を潰さない
    objs = []
    # 框 — 天端が高い側の床板の天端(z = dan)。見付面は z 方向でなく y=0 の面
    o = V.box(name + "_kamachi", (w, KAM_MIKOMI, mitsuke),
              (0.0, KAM_MIKOMI / 2.0, dan - mitsuke / 2.0), p['wood'])
    V.set_uv_rect(o, GR.WOOD_UV, axes=('z', 'x'))     # 木理を長手(x)へ流す
    objs.append(o)
    # 蹴込板 — 框の面から `KAM_KEKOMI_BACK` 引いて、低い側の床板へ `KAM_BITE` 噛ませる
    y0 = KAM_KEKOMI_BACK
    o = V.box(name + "_kekomi", (w, KAM_KEKOMI_T, (dan - mitsuke) + KAM_BITE),
              (0.0, y0 + KAM_KEKOMI_T / 2.0, (dan - mitsuke - KAM_BITE) / 2.0), p['wood'])
    V.set_uv_rect(o, GR.WOOD_UV, axes=('z', 'x'))
    objs.append(o)
    # 蹴込の裏を塞ぐ地覆(蹴込板の裏が見えないように。高い側の床下は暗いが、
    # 廊下の小口から覗くと蹴込板の裏の面が裏返って見える)
    o = V.box(name + "_jifuku", (w, KAM_MIKOMI - y0 - KAM_KEKOMI_T, 0.06),
              (0.0, (y0 + KAM_KEKOMI_T + KAM_MIKOMI) / 2.0, 0.03), p['wood'])
    V.set_uv_rect(o, GR.WOOD_UV, axes=('z', 'x'))
    objs.append(o)
    V.dedup_materials()
    ob = V.join(objs, name)
    V.set_origin(ob, (0.0, 0.0, 0.0))
    return ob


def kamachi_check(o, dan, w):
    ok = [("左右対称(Unity X = −Blender X が恒等)", SB.check_mirror_x(o), "")]
    uv = SB.unity_verts(o)
    xs = [t[0] for t in uv]; ys = [t[1] for t in uv]; zs = [t[2] for t in uv]
    ok.append(("天端が段の高さ", abs(max(ys) - dan) < 1e-4, "Ymax=%.4f 期待 %.4f" % (max(ys), dan)))
    ok.append(("幅が 1間", abs((max(xs) - min(xs)) - w) < 1e-4, "W=%.4f" % (max(xs) - min(xs))))
    ok.append(("見付面が Z=0(見え面 +Z)", abs(max(zs)) < 1e-6, "Zmax=%.4f" % max(zs)))
    ok.append(("躯体が高い側(−Z)にだけ出る", min(zs) >= -KAM_MIKOMI - 1e-6,
               "Zmin=%.4f" % min(zs)))
    ok.append(("下端が低い側の床板の中に留まる(噛ませ %.3f)" % KAM_BITE,
               min(ys) >= -0.0303 + 1e-6 and min(ys) <= 0.0,
               "Ymin=%.4f" % min(ys)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    bad = [t for t in ok if not t[1]]
    if bad:
        raise SystemExit("[dewa-buzai] ⛔ 框の検算が落ちた: %s" % ", ".join(t[0] for t in bad))


def render_kamachi(o, tag, dan):
    """⭐ 見るのは 3 点 — 立面(蹴込みが効いているか)/ 寄り / 床板と継いだ姿。
    ⚠ **床板 `Goten_RokaEnita_1ken` を両側に継いで**撮る。⛔ 単体では段に見えない。
    ⛔⛔ **`V.hook_textures()` を床板を読む前に呼ばない** — FBX の TransparencyFactor で
      後から読んだ板の Alpha が 0 のまま残り、**板が1枚も写らない**(2026-09-20 に踏んで
      「取り込みが失敗した」と誤診しかけた)。"""
    os.makedirs(SHOT, exist_ok=True)
    # 低い側・高い側の床板(在庫の部材を読んで継ぐ)
    enita = os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Parts",
                         "Goten_RokaEnita_1ken.fbx")
    boards = []
    if os.path.exists(enita):
        import vkmesh as VM
        for (yy, zz, nm) in ((-0.909, 0.0, "lo"), (0.909 + KAM_MIKOMI, dan, "hi")):
            for i in (0, 1):
                bs = VM.import_fbx_abs(enita)
                for b in bs:
                    b.location = Vector((0.0, yy + (-1 if nm == "lo" else 1) * i * 1.818, zz))
                boards += bs
    V.hook_textures()
    bpy.context.view_layer.update()
    # ⛔ 画角を**床板を含めた外形**から組まない(廊下の板が 4 枚も入るので框が画面の隅へ落ちる。
    #   2026-09-20 に実際に空の絵を焼いた)。⭕ 框そのものの外形から組む。
    mn, mx = V.bbox([o])
    cx, cy, cz = (mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0, dan / 2.0
    out = []

    def shot(sub, cam, look, ortho=None, res=(1600, 1000)):
        for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
            bpy.data.objects.remove(c, do_unlink=True)
        for pl in [c for c in bpy.data.objects if c.name.startswith("Plane")]:
            bpy.data.objects.remove(pl, do_unlink=True)
        bpy.ops.mesh.primitive_plane_add(size=40, location=(cx, cy, -0.36))
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "%s_%s.png" % (tag, sub))
        V.render(f)
        out.append(f)
        print("RENDER %s" % f)

    # 1) 立面(廊下の低い側から真っ直ぐ)— 蹴込みが効いているか・框の見付
    shot("01_ritsumen", (cx, -3.2, cz), (cx, 0.0, cz), ortho=2.2, res=(1600, 900))
    # 2) 寄り(低い側の斜め上から)— 框の天端と上の床板が面一か
    shot("02_yori", (cx - 0.85, -1.05, 0.70), (cx + 0.10, 0.06, 0.12), res=(1600, 1000))
    # 3) 全景 — 段として読めるか
    shot("03_zenkei", (cx - 2.0, -2.5, 1.45), (cx, 0.15, 0.10), res=(1600, 1000))
    # 4) 小口(廊下の横から)— 蹴込板の裏が見えていないか
    shot("04_koguchi", (2.6, -1.3, 0.55), (cx, 0.02, 0.10), res=(1500, 1000))
    return out


def build_kamachi(argv):
    dan = 0.301
    if "--dan" in argv:
        dan = float(argv[argv.index("--dan") + 1])
    name = kamachi_name(dan)
    V.reset()
    o = make_kamachi(dan, KEN, name)
    report(o, name, "段=%.3f" % dan)
    kamachi_check(o, dan, KEN)
    if "--render" in argv:
        render_kamachi(o, "matsudaira_rokakamachi_d%d" % int(round(dan * 1000)), dan)
        V.reset()
        o = make_kamachi(dan, KEN, name)     # ⚠ レンダで場が汚れたので焼き直して書き出す
    V.export_fbx(o, os.path.join(OUT_GOTEN, name + ".fbx"))
    print("[dewa-buzai] ⭕ 渡廊下の框 → %s" % os.path.join(OUT_GOTEN, name + ".fbx"))
    return name


# =====================================================================
# 3. 切石の縁石
# =====================================================================
def fuchi_name(runken, w=0.36):
    return "Fuchiishi_%sken_w%d" % (GR.KenTag(runken), int(round(w * 1000.0)))


def make_fuchi(runken, w=0.36, name=None):
    """切石の縁石。Blender: x = 走り / y = 見込み(+y = 高い側)/ z = 高さ(0 = 天端)。
    ⇒ Unity: X = 走り / Y = 高さ(0 = 天端)/ **+Z = 低い側 = 見え面**。

    ⭐ **落差 0 と落差 0.30 を一つの型で賄う** — 天端は常に y=0、躯体は常に
      `FU_DROP_MAX + FU_ROOT` まで垂れる。出るか隠れるかは**据える側の地盤**が決める。"""
    name = name or fuchi_name(runken, w)
    L = runken * KEN
    H = FU_DROP_MAX + FU_ROOT
    mat = SB.kirishi_material()
    rng = SB.rng_of("fuchi", "%.3f" % L, "%.3f" % w)
    k = max(1, int(round(L / FU_STONE)))
    cuts = [-L / 2.0 + L * i / k for i in range(k + 1)]
    # ⭕ 目地は x=0 について左右対称に振る(Unity X = −Blender X が恒等になる)
    jit = [0.0] * (k + 1)
    for i in range(1, (k + 1) // 2):
        d = rng.uniform(-0.06, 0.06) * (L / k)
        jit[i] = d
        jit[k - i] = -d
    cuts = [cuts[i] + jit[i] for i in range(k + 1)]
    objs = []
    for i in range(k):
        objs.append(SB._stone(cuts[i], cuts[i + 1], 0.0, w, -H, 0.0,
                              mat, rng, "%s_s%d" % (name, i),
                              chamfer=FU_CHAMFER, tile=FU_TILE))
    V.dedup_materials()
    o = V.join(objs, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


def fuchi_check(o, runken, w):
    ok = [("左右対称(Unity X = −Blender X が恒等)", SB.check_mirror_x(o), "")]
    uv = SB.unity_verts(o)
    xs = [t[0] for t in uv]; ys = [t[1] for t in uv]; zs = [t[2] for t in uv]
    L = runken * KEN
    ok.append(("走りが指図どおり", abs((max(xs) - min(xs)) - L) < 2e-3,
               "L=%.4f 期待 %.4f" % (max(xs) - min(xs), L)))
    ok.append(("天端がピボットの高さ(Y最大=0)", abs(max(ys)) < 1e-4, "Ymax=%.4f" % max(ys)))
    ok.append(("丈 = 最大落差 + 根入れ", abs(min(ys) + (FU_DROP_MAX + FU_ROOT)) < 1e-4,
               "Ymin=%.4f" % min(ys)))
    ok.append(("見付面が Z=0(見え面 +Z)", abs(max(zs)) < 1e-6, "Zmax=%.4f" % max(zs)))
    ok.append(("見込みが指図の w", abs(min(zs) + w) < 1e-4, "Zmin=%.4f 期待 %.4f" % (min(zs), -w)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    bad = [t for t in ok if not t[1]]
    if bad:
        raise SystemExit("[dewa-buzai] ⛔ 縁石の検算が落ちた: %s" % ", ".join(t[0] for t in bad))


def render_fuchi(o, tag, w=0.36):
    """⭐ 見るのは 3 点 — 落差 0.30 の納め / 落差 0 の納め / 目地の寄り。
    ⚠ **地盤の板を 2 枚(高い側・低い側)敷いて**撮る。⛔ 単体では『縁』に見えない。"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    cx = (mn.x + mx.x) / 2.0
    L = mx.x - mn.x
    out = []

    def scene(drop):
        for pl in [c for c in bpy.data.objects if c.name.startswith("Plane")]:
            bpy.data.objects.remove(pl, do_unlink=True)
        # 高い側(+y)= 天端と面一 / 低い側(−y)= drop だけ下
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(cx, w + 3.0, 0.0))
        hi = bpy.context.active_object
        hi.scale = (L * 1.2, 6.0, 1.0)
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(cx, -3.0, -drop))
        lo = bpy.context.active_object
        lo.scale = (L * 1.2, 6.0, 1.0)
        return hi, lo

    def shot(sub, cam, look, drop, ortho=None, res=(1600, 1000)):
        for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
            bpy.data.objects.remove(c, do_unlink=True)
        scene(drop)
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "%s_%s.png" % (tag, sub))
        V.render(f)
        out.append(f)
        print("RENDER %s" % f)

    shot("01_drop30", (cx - 1.4, -2.6, 1.5), (cx, 0.1, -0.15), 0.30, res=(1600, 1000))
    shot("02_drop00", (cx - 1.4, -2.6, 1.5), (cx, 0.1, -0.15), 0.00, res=(1600, 1000))
    shot("03_yori", (cx - 0.5, -1.0, 0.55), (cx + 0.3, 0.15, -0.12), 0.30, res=(1600, 1000))
    shot("04_danmen", (cx, -4.0, -0.10), (cx, 0.1, -0.10), 0.30, ortho=1.6, res=(1400, 900))
    shot("05_zentai", (cx - L * 0.25, -L * 0.45, L * 0.35), (cx, 0.2, -0.15), 0.30,
         res=(1700, 900))
    return out


def fuchi_jobs():
    """⛔ 走りを人が書かない — 指図 `fuchi[]` の `a`/`b` から出す。"""
    d = doc()
    out = []
    for f in d.get("fuchi", []):
        run = abs(float(f["b"]) - float(f["a"]))
        out.append((f["name"], run, float(f.get("w", 0.36)), float(f.get("drop", 0.0))))
    return out


def build_fuchi(argv):
    jobs = fuchi_jobs()
    if "--run" in argv:
        jobs = [("手引き", float(argv[argv.index("--run") + 1]), 0.36, 0.30)]
    print("[dewa-buzai] 縁石 %d 本(指図 `fuchi` から)" % len(jobs))
    made = []
    seen = {}
    for (nm, run, w, drop) in jobs:
        seen.setdefault((round(run, 4), round(w, 4)), []).append("%s(落差 %.2f)" % (nm, drop))
    for (run, w), users in sorted(seen.items()):
        name = fuchi_name(run, w)
        V.reset()
        o = make_fuchi(run, w, name)
        report(o, name, "走り %g間 = %.3fm / 使う縁 %s" % (run, run * KEN, ", ".join(users)))
        fuchi_check(o, run, w)
        if "--render" in argv and not made:      # ⚠ 代表 1 本だけ撮る(形は同じ)
            render_fuchi(o, "matsudaira_fuchiishi_%s" % GR.KenTag(run), w)
            V.reset()
            o = make_fuchi(run, w, name)
        V.export_fbx(o, os.path.join(OUT_FUCHI, name + ".fbx"))
        made.append(name)
        print("[dewa-buzai] ⭕ 縁石 → %s" % os.path.join(OUT_FUCHI, name + ".fbx"))
    return made


# =====================================================================
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    what = argv[0] if argv and not argv[0].startswith("--") else "all"
    if what in ("amaosae", "all"):
        build_amaosae(argv)
    if what in ("kamachi", "all"):
        build_kamachi(argv)
    if what in ("fuchi", "all"):
        build_fuchi(argv)


if __name__ == "__main__":
    main()
