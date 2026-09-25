# -*- coding: utf-8 -*-
"""山王権現社の**小さな棟 10 棟** — 堂宇(宝形・入母屋)・稲荷社・御厩・御蔵。

    blender --background --python Tools/Blender/build_sanno_do.py -- [型...] [--render] [--no-export]
    (型を省くと全部。hogyo / irimoya3 / irimoya4 / inari / umaya / kura)
    blender --background --python Tools/Blender/build_sanno_do.py -- hihi --render
    (絵図の比の 6 点 = yakushi / koshin / kannon / sono5 / sono8 / umaya32。2026-09-23 EDO-0395)
    blender --background --python Tools/Blender/build_sanno_do.py -- yakushi6 --render
    (薬師堂 = 六角の宝形 + 高欄付きの 4.5 間角の石の壇。2026-09-26 EDO-0438 施主裁定B)

━━━ 2026-09-23 EDO-0395 施主裁定B — 絵図の比の寸法【P 比・U 錨】━━━━━━━━━━━━━━━━━━━━━━
御宮絵図の朱矩形の**大小比**を、鐘楼の辺の平均 = 3 間を錨に 0.5 間刻みで読んだ寸法へ焼き直す。
⛔ 旧 3×3 / 4×4 / 御厩 4×3 は消さない(新しい名で足す)。引数は **ローカル X(間口)× Z(奥行)**、
正面 +Z ⇒ 正面が東の棟は X = 南北・Z = 東西。
| 棟 | 型 | 間 X×Z | 部材 |
|---|---|---|---|
| 薬師堂 | 宝形 | 4.5×4.5 | `yakushi` = `do("hogyo", 4.5, 4.5)` |
| 庚申堂 | 宝形 | 2×2 | `koshin` |
| 観音堂 | 宝形 | 2.5×2.5 | `kannon` |
| 附属堂 其五 | 入母屋・平入(正面 南)| 5.5×3.5 | `sono5` |
| 附属堂 其八 | 入母屋 + **向拝**(正面 東)| 5×5 | `sono8` = `do("irimoya", 5, 5, kohai=True)` |
| 御厩 | 切妻(正面 南)| 3×2 | `umaya32` = `umaya(3, 2)`(馬房 3) |
| 鐘楼 / 鼓楼 | 袴腰・入母屋(妻を正面 = 東へ)| 2.5×3.5 / 3×3.5 | `build_typ_jisha.py -- shoro --ken=2.5x3.5` / `koro --ken=3x3.5` |
・半間の辺の柱割 = `HALF_BAYS`(半端を中の間へ寄せる)【U 部材方】。
・向拝の意匠(流れ向拝・4寸・柱 2 本・木階を向拝の下へ)= `KH` の断り【U 部材方 — 絵図は凸の平面しか言わない】。

━━━ なぜ起こすか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指図 `docs/Sashizu/sanno_sashizu.json` の `munes[]` のうち **10 棟が `hFrom` / `bays` /
`partFrom` を持たない** — 位置と間数と屋根の形式だけが決まっていて、**丈と柱割が無い**。
bom の行 9(鐘楼・鼓楼・附属堂・観音堂・薬師堂・庚申堂)・32(稲荷社)・33(御蔵)・34(御厩)。

⭐ **丈と柱割は部材方が類型から起こした【確度 U】**(規則7: 典拠と確度を付ける)。
  ⛔ 史料値として名乗らせない。指図側は `acc` で既に「U(規模・屋根)」と宣言済み。

━━━ 型は 6 つ(10 棟がこれで足りる)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| 型 | 棟 | 関数 |
|---|---|---|
| A 宝形の三間堂 3×3間  | 薬師堂・庚申堂・観音堂(3棟)| `do("hogyo", 3, 3)` |
| B 春日造(縋破風)      | 稲荷社                      | `inari()` |
| C 袴腰の鐘楼 3×3間    | 鐘楼・鼓楼(2棟)            | ⭕ **在庫** `build_typ_jisha.shoro()` — 別ファイル |
| D 入母屋の堂 3×3/4×4  | 附属堂 其五・其八           | `do("irimoya", 3, 3)` / `(4, 4)` |
| E 切妻の厩 4×3間      | 御厩                        | `umaya()` = 岡部の厩の生成器 |
| F 土蔵 4×5間(置屋根) | 御蔵                        | `kura()` = 松江松平の土蔵の生成器 + 置屋根 |

⛔ **ゼロからモデリングしない。**屋根は `build_goten_roof` のキットの瓦場、軸部の道具は
  `build_sanno_shaden`(箱・板壁・擬宝珠)、厩と蔵は既存の附属屋の生成器を呼ぶだけ。

━━━ 丈と柱割の典拠【すべて U 部材方 2026-09-22】━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・柱間 = **1間等間**(江戸間 1.818)。指図の `du`/`dv` は**間数**(御供所と同じ読み)で、
  部材の **柱芯の矩形**をそれに合わせる。⚠ 社殿5棟だけ `du`/`dv` が**明治16年図の実寸**
  由来で柱間 2.54 — ⛔ そちらの柱割を堂宇へ持ち込まない。
・**床 0.90(高床)**… bom 行9「高床構造としてまとめて起こす」。縁 + 高欄 + 木階が付く姿が
  堂宇と民家を分ける合図。⛔ 社殿の**腰組**(【A 加藤2018】本殿の作り)は使わない —
  格が違うので**縁束の束立て**にした。
・**軒先 3.40 / 軒の出 1.00**… 御供所(軒先 3.00・出 0.75)より一段深い。寺社の堂は軒が深い。
  ⇒ 柱の丈 = 桁の天端 3.856 − 床 0.90 = **2.956**(内法 1.80 + 小壁 1.16)。
・**棟高は従属値**(`const.muneHeightRule`)。瓦の勾配 `GR.RATIO`(5.5寸)は動かせないので
  ⛔ 棟高を数で決めて瓦場を剪断しない。実測は各 `report()` が刷る。
・御厩 軒 2.55 / 御蔵 軒 3.70 は既存の附属屋の生成器の断り書きに従った逆算値。

━━━ 材 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ 新規に作らない。`wood` / `wall C` / `door wall` / `roof` / `roof ornaments` / `Kirishi`
  (+ 稲荷社だけ `Doukawara`(銅板葺)と `Shu_Torii`(朱))。
⭐ 瓦 = キットの `roof`。**山王では「在庫の本瓦」**(楼門・御供所と同じ材・同じモジュール)。
  ⛔ 桟瓦の幅を物差しにしない — 瓦場の周期は `GR.MOD_LEN` 2.004 / 流れ `GR.STEP_RUN` 1.785。
⚠ 稲荷社だけ**銅板葺**【A 千代田区の実測】で材が違う(指図 bom 行32)。

━━━ 軸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unity ローカル **X = 東(u)/ Z = 北(v)/ Y = 上**。**ピボット = 柱芯の矩形の中心・地盤**。
**正面(木階と扉)= +Z**。据える向きは棟梁が yaw で与える。scale = one。
"""
import bpy, bmesh, sys, os, math, re
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH
import build_sanno_romon as RM
import build_sanno_gokusho as GK
import build_sanno_buzai as SB
import build_okabe_fuzokuya as OF
import build_matsudaira_dewa_fuzokuya as MF

K = 1.818
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
ALLOWED = ("wood", "wall C", "door wall", "roof", "roof ornaments", "Kirishi",
           "Doukawara", "Shu_Torii", "Foundation_A_01", "wall A",
           "Fence_B_01", "Wall Exterior Defence")   # ← 御蔵(松江松平の土蔵の生成器)の材

# 堂宇の寸法【すべて U 部材方 2026-09-22】。docstring「丈と柱割の典拠」を参照
DO = dict(kidanH=0.30, kidanOut=0.70, post=0.20, floor=0.90, en=0.606, enT=0.10,
          koran=0.76, uchinori=1.80, koshi=0.85, kabeT=0.09, ketaH=0.20,
          eaveZ=3.40, eave=1.00, kaidanW=1.30, kaidanN=5, kaidanRun=0.32)


def lin(a, b, n):
    return [a + (b - a) * i / float(n) for i in range(n + 1)]


# 半間の出る辺の柱割【U 部材方 2026-09-23・EDO-0395 施主裁定B】。値 = 各柱間[間]、端から順に。
#   ⭐ 規則は二つだけ: ① 柱間は **1間以上**(0.75 は 2.5間だけの例外 — 三間に割らないと中央に
#   扉が取れない)② 半端は **中の間へ寄せる**(正面の扉が中の間に来るので、そこを広げる)。
#   ・2.5間 = 0.75 + 1.0 + 0.75 … 中の間 1 間に板扉、脇の間 0.75 は連子窓
#   ・3.5間 = 1.0 + 1.5 + 1.0 … 中の間 1.5
#   ・4.5間 = 1.5 × 3 …… 等間(中の間だけ広げると 1.0+2.5+1.0 で扉が 4.5m になる)
#   ・5.5間 = 1.0 + 1.0 + 1.5 + 1.0 + 1.0 … 中の間 1.5
#   ⛔ 整数の間数は従来どおり **1間等間**(`lin`)— 既存の 3×3 / 4×4 と寸分同じ。
HALF_BAYS = {2.5: (0.75, 1.0, 0.75), 3.5: (1.0, 1.5, 1.0), 4.5: (1.5, 1.5, 1.5),
             5.5: (1.0, 1.0, 1.5, 1.0, 1.0)}


def bay_nodes(nk):
    """柱芯の節(Unity ローカル・中心 0)。`nk` = 辺の間数(整数か半間)。"""
    h = nk * K / 2.0
    if abs(nk - round(nk)) < 1e-9:
        return lin(-h, h, int(round(nk)))
    b = HALF_BAYS.get(round(nk * 2) / 2.0)
    if b is None:
        raise SystemExit("[do] 柱割が未定の間数: %s(HALF_BAYS に足す)" % nk)
    xs, x = [-h], -h
    for w in b:
        x += w * K
        xs.append(x)
    xs[-1] = h
    return xs


# ==========================================================================
# 屋根面の高さ(名目)— 野地と桁の天端を出すのに要る
# ==========================================================================
def zfun_of(kind, hu, hv, eave, eaveZ):
    """(X,Z)[Unity ローカル] → 名目の屋根面の高さ。⛔ 瓦の実体はこれより −0.06〜+0.15 うねる。"""
    k = GR.RATIO
    hU, hV = hu + eave, hv + eave
    if kind == "hogyo":
        return lambda X, Z: eaveZ + k * min(hU - abs(X), hV - abs(Z))
    # 入母屋 — 妻の立上り hb より下は寄棟(隅)、上は平の流れがそのまま妻の通りまで伸びる
    hb = hV * k * 0.45                       # GR.make_irimoya の gable_frac=0.45
    a = hb / k

    def z(X, Z):
        # ⛔⛔ **境界 |X| = hU − a を平の流れの側に入れない。**妻の通りちょうどに在るのは
        #   **隅(寄棟面)の上端の駒**で、そこの高さは hb(= k·a)。`<=` で平の式を当てると
        #   その列が「1.15 m 沈んでいる」と読まれ、瓦の谷が −1.149 と出て桁が内法より
        #   下がった(2026-09-22 に実測)。⇒ 1e-4 の逃げを入れて隅の側へ落とす。
        if abs(X) <= hU - a - 1e-4:
            return eaveZ + k * (hV - abs(Z))
        return eaveZ + k * min(hV - abs(Z), hU - abs(X))
    return z


def B3(M, u0, u1, v0, v1, h0, h1, uv, mat=0, grain="h"):
    """`SH.box3` の順序を正す薄い皮。⛔⛔ **このファイルでは生の `SH.box3` を呼ばない。**

    範囲を逆順(`u0 > u1` など)で渡すと `vkmesh.Mesh.box` が**裏返った箱**を積み、
    Unity の裏面カリングで**丸ごと消える**(Blender の素のレンダでは見えない)。
    `out = ±1` を掛けた見込みを渡す所(連子子・板扉・裏板)で実際に踏んだ —
    2026-09-22 に裏面カリングのレンダで連子窓の柱間が背景色に抜けた。
    関連 memory: mesh-box-inward-normals-and-ray-checks"""
    u0, u1 = sorted((u0, u1))
    v0, v1 = sorted((v0, v1))
    h0, h1 = sorted((h0, h1))
    SH.box3(M, u0, u1, v0, v1, h0, h1, uv, mat, grain=grain)


# ==========================================================================
# 軸部の道具(すべて Unity ローカル (u=X, v=Z, h=Y) で組む)
# ==========================================================================
def posts(M, uv, mw, pts, z0, z1, r):
    for (uu, vv) in pts:
        B3(M, uu - r, uu + r, vv - r, vv + r, z0, z1, uv["wood"], mw, grain="h")


def en_koran(M, uv, mw, hu, hv, fl, gap=None):
    """**縁 + 高欄 + 縁束**。`gap` = 正面(+Z)で高欄を切る X の範囲(木階の口)。

    ⛔ 社殿の `SH.en_koran` を呼ばない — あちらは腰組で縁を持ち出す本殿の作りで、
      高欄を**四周とも通し**で回すので、木階の口が開かない(階が高欄へ突き当たる)。
      ⭕ ここは**束立て**(附属堂の格)+ 正面だけ口を開けた高欄。"""
    en, T, kh = DO["en"], DO["enT"], DO["koran"]
    ou, ov = hu + en, hv + en

    def band(u0, u1, v0, v1, along):
        n = max(2, int(round(((u1 - u0) if along == "u" else (v1 - v0)) / 0.22)))
        for i in range(n):
            s0, s1 = i / float(n), (i + 1) / float(n)
            if along == "u":
                B3(M, u0 + (u1 - u0) * s0 + 0.006, u0 + (u1 - u0) * s1 - 0.006,
                        v0, v1, fl - T, fl, uv["wood"], mw, grain="u")
            else:
                B3(M, u0, u1, v0 + (v1 - v0) * s0 + 0.006, v0 + (v1 - v0) * s1 - 0.006,
                        fl - T, fl, uv["wood"], mw, grain="v")
    band(-ou, ou, -ov, -hv, "u")           # 背面 −Z
    band(-ou, ou, hv, ov, "u")             # 正面 +Z
    band(hu, ou, -hv, hv, "v")
    band(-ou, -hu, -hv, hv, "v")
    # 縁葛(縁板の小口を締める横材)
    for (u0, u1, v0, v1, g) in ((-ou, ou, -ov, -ov + 0.09, "u"), (-ou, ou, ov - 0.09, ov, "u"),
                                (ou - 0.09, ou, -ov, ov, "v"), (-ou, -ou + 0.09, -ov, ov, "v")):
        B3(M, u0, u1, v0, v1, fl - T - 0.04, fl - T + 0.01, uv["wood_h"], mw, grain=g)
    # 縁束(⛔ 腰組にしない。束は 1 間ごと)
    n_u = max(2, int(round(2 * ou / K)))
    n_v = max(2, int(round(2 * ov / K)))
    nodes = [(-ou + 2 * ou * i / n_u, sv) for i in range(n_u + 1) for sv in (-ov, ov)]
    nodes += [(su, -ov + 2 * ov * j / n_v) for j in range(1, n_v) for su in (-ou, ou)]
    for (uu, vv) in nodes:
        B3(M, uu - 0.065, uu + 0.065, vv - 0.065, vv + 0.065,
                DO["kidanH"] - 0.05, fl - T, uv["wood"], mw, grain="h")
    # 高欄 — 地覆 / 立子 / 平桁 / 架木。正面は gap で切る
    runs = [("u", -ov, -ou, ou), ("v", ou, -ov, ov), ("v", -ou, -ov, ov)]
    if gap:
        runs += [("u", ov, -ou, gap[0]), ("u", ov, gap[1], ou)]
    else:
        runs += [("u", ov, -ou, ou)]
    for (along, fx, a, b) in runs:
        if b - a < 0.25:
            continue
        for (z0, z1, t) in ((fl, fl + 0.11, 0.06), (fl + kh - 0.20, fl + kh - 0.11, 0.05),
                            (fl + kh - 0.11, fl + kh, 0.075)):
            if along == "u":
                B3(M, a, b, fx - t, fx + t, z0, z1, uv["wood_h"], mw, grain="u")
            else:
                B3(M, fx - t, fx + t, a, b, z0, z1, uv["wood_h"], mw, grain="v")
        n = max(2, int(round((b - a) / 0.62)))
        for i in range(n + 1):
            c = a + (b - a) * i / float(n)
            if along == "u":
                B3(M, c - 0.045, c + 0.045, fx - 0.045, fx + 0.045,
                        fl + 0.11, fl + kh - 0.11, uv["wood"], mw, grain="h")
            else:
                B3(M, fx - 0.045, fx + 0.045, c - 0.045, c + 0.045,
                        fl + 0.11, fl + kh - 0.11, uv["wood"], mw, grain="h")
        for c in (a, b):                                  # 隅と口の擬宝珠
            if along == "u":
                SH.giboshi(M, c, fx, fl + kh, uv["wood"], mw)
            else:
                SH.giboshi(M, fx, c, fl + kh, uv["wood"], mw)
    return ou, ov


def kizahashi(M, uv, mw, ov, fl, w=None, n=None):
    """**木階**(縁の外から地盤へ)。踏板 + 蹴込 + 両脇の側桁。⛔ 石段にしない。"""
    w = w or DO["kaidanW"]
    n = n or DO["kaidanN"]
    run = DO["kaidanRun"]
    rise = fl / float(n)
    hw = w / 2.0
    for i in range(n):
        zt = rise * (i + 1)
        v1 = ov + run * (n - i)
        v0 = v1 - run - 0.03
        B3(M, -hw, hw, v0, v1, zt - 0.06, zt, uv["wood"], mw, grain="u")        # 踏板
        B3(M, -hw, hw, v0, v0 + 0.045, zt - rise, zt - 0.06, uv["wood_h"], mw, grain="u")  # 蹴込
    for s in (-1, 1):                                                                 # 側桁
        uu = s * (hw + 0.05)
        B3(M, uu - 0.05, uu + 0.05, ov, ov + run * n + 0.06, 0.0, fl - 0.04,
                uv["wood"], mw, grain="v")
    return ov + run * n


def wall_run(M, uv, ms, along, fixed, nodes, fl, top, kinds, out):
    """柱間ごとの壁。`kinds` = {柱間の番号: "ita"|"mado"|"tobira"}、既定は "ita"。
    `out` = 外の向き(±1)。⭐ 堂宇は**板壁**(腰から内法まで縦板)+ 上に漆喰の小壁。"""
    pr = DO["post"] / 2.0
    kt = DO["kabeT"] / 2.0
    zu = fl + DO["uchinori"]
    zk = fl + DO["koshi"]

    def box(b0, b1, h0, h1, t0, t1, uvr, m, grain=None):
        if along == "u":
            B3(M, b0, b1, fixed + t0, fixed + t1, h0, h1, uvr, m, grain=grain or "u")
        else:
            B3(M, fixed + t0, fixed + t1, b0, b1, h0, h1, uvr, m, grain=grain or "v")

    for i in range(len(nodes) - 1):
        s0, s1 = nodes[i] + pr, nodes[i + 1] - pr
        if s1 <= s0:
            continue
        kind = kinds.get(i, "ita")
        # 内法長押と上の小壁(漆喰)は三種とも共通
        box(s0, s1, zu, zu + 0.10, -0.07, 0.07, uv["wood_h"], SH.W)            # 内法長押
        box(s0, s1, zu + 0.10, top, -kt, kt, uv["wall"], SH.WC)                # 小壁
        if kind == "tobira":
            box(s0, s1, fl, fl + 0.06, -0.07, 0.07, uv["wood_h"], SH.W)        # 敷居
            mid = (s0 + s1) / 2.0
            for (a, b) in ((s0, mid - 0.01), (mid + 0.01, s1)):                # 両開きの板扉
                box(a, b, fl + 0.06, zu, out * 0.03, out * 0.075, uv["itado"], SH.DW)
            continue
        if kind == "mado":
            box(s0, s1, fl, zk, -0.02, 0.02, uv["wood_h"], SH.W)               # 腰板の裏板
            if along == "u":
                SH.panel_ita(M, s0, s1, "u", fixed, fl, zk, uv["wood"], SH.W, t=0.025)
            else:
                SH.panel_ita(M, s0, s1, "v", fixed, fl, zk, uv["wood"], SH.W, t=0.025)
            box(s0, s1, zk, zk + 0.06, -0.07, 0.07, uv["wood_h"], SH.W)        # 窓台
            L = s1 - s0
            nn = max(3, int(round(L / 0.115)))
            for j in range(nn):                                                # 連子子
                c = s0 + L * (j + 0.5) / nn
                box(c - 0.022, c + 0.022, zk + 0.06, zu, out * 0.012, out * 0.058,
                    uv["wood"], SH.W, grain="h")
            # ⛔ 格子だけだと素通し ⇒ 裏に板(堂の中は暗い。明かり障子にしない)
            box(s0, s1, zk + 0.06, zu, -out * 0.045, -out * 0.020, uv["itado"], SH.DW)
            continue
        # 板壁 — 縦板 + 裏板(⛔ `panel_ita` の目地は 8mm 抜けるので裏板を通す)
        box(s0, s1, fl, zu, -0.02, 0.02, uv["wood_h"], SH.W)
        if along == "u":
            SH.panel_ita(M, s0, s1, "u", fixed + out * 0.02, fl, zu, uv["wood"], SH.W, t=0.025)
        else:
            SH.panel_ita(M, s0, s1, "v", fixed + out * 0.02, fl, zu, uv["wood"], SH.W, t=0.025)
        box(s0, s1, fl, fl + 0.07, -0.06, 0.06, uv["wood_h"], SH.W)            # 地長押


# ==========================================================================
# A 宝形の三間堂 / D 入母屋の堂
# ==========================================================================
def do(kind, nu, nv, name=None, kohai=False):
    """**堂宇**。`kind` = "hogyo"(方形造 = 宝形)|"irimoya"。`nu`×`nv` = 柱芯の間数。

    ⭐ **正方形の平面で寄棟を架けると必然的に方形造(宝形)になる** — 四面の勾配が
      等しい限り大棟の長さ = 桁行 − 梁間 = 0 で、隅棟4本が一点に集まる四角錐になる
      (`GR.make_yosemune` の断り)。⇒ 宝形は `make_yosemune` の正方形で足り、
      ⛔ 別実装を書かない。頂は露盤 + **宝珠**(ここで足す)。

    【組み立て — 下から】① 切石の基壇 0.30(出 0.70)② 縁束と床束 ③ 床 0.90(高床)
      ④ 縁 0.606 + 高欄 + 擬宝珠、正面(+Z)に木階5級 ⑤ 柱・板壁・連子窓・正面中央の板扉
      ⑥ 桁 ⑦ 野地板 ⑧ 瓦の屋根。"""
    name = name or part_name(kind, nu, nv, kohai)
    hu, hv = nu * K / 2.0, nv * K / 2.0
    eave, eaveZ, fl = DO["eave"], DO["eaveZ"], DO["floor"]
    ms, uv = SH.mats()
    mw = SH.W
    # ---- 屋根(キットの瓦場)
    if kind == "hogyo":
        roof = GR.make_yosemune(2 * hu, 2 * hv, name + "_roof", eave=eave)
    else:
        roof = GR.make_irimoya(2 * hu, 2 * hv, name + "_roof", eave=eave)
    roof.location = (0.0, 0.0, eaveZ)
    bpy.context.view_layer.update()
    V.sel([roof]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    k = GR.RATIO
    hU, hV = hu + eave, hv + eave
    zf = zfun_of(kind, hu, hv, eave, eaveZ)
    # ⛔⛔ **瓦の谷を「壁の通りから内へ入れた範囲」で測らない。**御供所(切妻)はそれで足りたが、
    #   寄棟・入母屋は**隅で瓦が呼び寸より 0.171 外へ出る**ので、その外れた駒が
    #   範囲から落ちて谷が浅く出る ⇒ 野地を突き抜けて軒裏の光線に「瓦に先に当たる」が出る
    #   (2026-09-22 に実測 4/800・隅の対角線上ちょうど 2 本ずつ)。
    #   ⭕ **屋根の全域**(bbox 込み)で測り、桁の天端もその谷に合わせる。
    RU = SH.unity_verts(roof)
    bx = max(abs(p[0]) for p in RU) + 0.02
    bz = max(abs(p[2]) for p in RU) + 0.02
    off = GK.roof_dmin(roof, lambda X, Z: True, zf) - 0.02
    # ⚠ 野地は更に 0.02 下げる(逃げ)。⭕ 桁の天端は `off − 0.03` なので野地の板厚 0.03 の
    #   中に収まり、突き抜けない。⛔ 逃げを 0 にすると隅の駒の位相しだいで数本が抜ける。
    slab = GK.noji_slab(name + "_noji", lambda X, Z: True, (-bx, bx, -bz, bz), zf, off - 0.02)
    keta_top = eaveZ + k * eave + off - 0.03        # 桁の天端 = 野地の下面
    top = keta_top - DO["ketaH"]
    extra = []
    if kind == "hogyo":
        extra.append(houju(name + "_houju", eaveZ + hV * k + 0.26))
    # ---- 軸部
    M = VM.Mesh()
    us, vs = bay_nodes(nu), bay_nodes(nv)
    grid = [(uu, vv) for uu in us for vv in vs]
    peri = [(uu, vv) for (uu, vv) in grid
            if abs(abs(uu) - hu) < 1e-6 or abs(abs(vv) - hv) < 1e-6]
    # 床束(柱芯の格子)と土台
    for (uu, vv) in grid:
        B3(M, uu - 0.07, uu + 0.07, vv - 0.07, vv + 0.07, DO["kidanH"] - 0.05, fl - 0.12,
                uv["wood"], mw, grain="h")
    for vv in vs:
        B3(M, -hu, hu, vv - 0.06, vv + 0.06, fl - 0.12, fl - 0.02, uv["wood_h"], mw, grain="u")
    # 身舎の床(⛔ 開けない — 上から空が抜ける)
    B3(M, -hu, hu, -hv, hv, fl - 0.10, fl, uv["wood"], mw, grain="u")
    kw = KH["kaidanW"] if kohai else DO["kaidanW"]
    gap = (-kw / 2.0 - 0.10, kw / 2.0 + 0.10)
    ou, ov = en_koran(M, uv, mw, hu, hv, fl, gap=gap)
    kai_v = kizahashi(M, uv, mw, ov, fl, w=kw)
    posts(M, uv, mw, peri, fl, keta_top, DO["post"] / 2.0)
    nbu, nbv = len(us) - 1, len(vs) - 1          # 柱間の数(半間の辺は HALF_BAYS の割)
    mid = nbu // 2
    front = {mid: "tobira"} if nbu % 2 else {mid - 1: "tobira", mid: "tobira"}
    side = {nbv // 2: "mado"} if nbv % 2 else {nbv // 2 - 1: "mado", nbv // 2: "mado"}
    flank = dict(front)
    for i in range(nbu):
        if i not in flank:
            flank[i] = "mado" if abs(i - (nbu - 1) / 2.0) < 1.01 else "ita"
    wall_run(M, uv, ms, "u", hv, us, fl, top, flank, +1)        # 正面 +Z
    wall_run(M, uv, ms, "u", -hv, us, fl, top, {}, -1)          # 背面 −Z
    wall_run(M, uv, ms, "v", hu, vs, fl, top, side, +1)
    wall_run(M, uv, ms, "v", -hu, vs, fl, top, side, -1)
    # 桁(四周)
    for uu in (-hu, hu):
        B3(M, uu - 0.09, uu + 0.09, -hv - 0.09, hv + 0.09, top, keta_top,
                uv["wood_h"], mw, grain="v")
    for vv in (-hv, hv):
        B3(M, -hu + 0.09, hu - 0.09, vv - 0.09, vv + 0.09, top, keta_top,
                uv["wood_h"], mw, grain="u")
    kh_objs, kh_info = [], None
    if kohai:
        kh_objs, kh_info = kohai_build(M, uv, mw, hu, hv, eaveZ, eave, off, name)
    body = M.to_object(name + "_body", ms)
    soff = soffit_pre(roof, slab, hu, hv, hU, hV, fl)     # ⭐ join の前に測る(関数の断り参照)
    out = {s: DO["kidanOut"] for s in ("+X", "-X", "+Z", "-Z")}
    stones = RM.kidan(hu, hv, out, DO["kidanH"], name + "_kidan",
                      finish=("+X", "-X", "+Z", "-Z"))
    for o in stones:
        o.data.transform(Matrix.Translation((0.0, 0.0, DO["kidanH"]))); o.data.update()
    V.dedup_materials()
    o = V.join([body, roof, slab] + extra + stones + kh_objs, name)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    info = dict(kind=kind, hu=hu, hv=hv, hU=hU, hV=hV, k=k, off=off, fl=fl,
                keta_top=keta_top, ou=ou, ov=ov, kai_v=kai_v, zf=zf, eave=eave,
                roban=(eaveZ + hV * k + 0.26) if kind == "hogyo" else None, soffit=soff,
                us=us, vs=vs, kohai=kh_info)
    print("[do] %s 柱芯 %.3f × %.3f / 床 %.2f / 桁の天端 %.3f / 瓦の谷(全域)%.3f / 縁の外 %.3f×%.3f / 階の先 Z %.3f"
          % (name, 2 * hu, 2 * hv, fl, keta_top, off + 0.02, 2 * ou, 2 * ov, kai_v))
    return o, info


def houju(name, z0):
    """**宝珠**(方形造の頂・露盤の上)。⛔ 球を作らない — 輪郭を箱で段に積む。
    材は瓦の役物 `roof ornaments`(鬼と同じ。⛔ 新規に作らない)。"""
    m = V.borrow_material(GR.ONI_MOD, "roof ornaments")
    uvp = V.sample_uv(GR.ONI_MOD, pick_high=True)
    uvr = (uvp[0] - 0.01, uvp[1] - 0.01, uvp[0] + 0.01, uvp[1] + 0.01)
    objs = []
    for (r, a, b) in ((0.26, 0.00, 0.07), (0.17, 0.07, 0.17), (0.21, 0.17, 0.25),
                      (0.15, 0.25, 0.40), (0.07, 0.40, 0.52)):
        q = V.box(name, (2 * r, 2 * r, b - a), (0.0, 0.0, z0 + (a + b) / 2.0), m)
        V.set_uv_rect(q, uvr, axes=('x', 'z'))      # ⛔ 一点貼りにしない(README)
        objs.append(q)
    return V.join(objs, name)


# ==========================================================================
# 向拝(附属堂 其八 = コマ堂)【形は U 部材方 2026-09-23・EDO-0395】
# ==========================================================================
# ⭐ 史料(山王御宮絵図)が言うのは**東面中央の朱の凸の平面だけ**(23×57px ÷ 20.5px/間
#   ≈ 奥行 1.1 × 幅 2.8 間)。形式・柱・階は何も言わない ⇒ 以下はすべて【U】。
# ・形式 = **流れ向拝**(身舎の正面の流れを、軒先の下からそのまま前へ延ばす一枚の片流れ)。
#   ⛔ 軒唐破風にしない — 唐破風は本社・楼門級の飾りで、境内の附属堂には格が過ぎる。
#   流れ向拝は近世の小堂で最も普通の形。
# ・勾配 = **4寸**(身舎 5.5寸より緩い)。⭐ 向拝は身舎より緩く葺くのが常で、同じ勾配で
#   延ばすと軒先が 2.5m を切って柱の下を人がくぐれない。瓦は `_tile_field_k` で**面ごと寝かせる**
#   (⛔ 瓦の z を縮めない)。
# ・向拝の瓦場の上端は**身舎の軒の下へ差し込む**(身舎の軒先の通りで身舎の瓦の谷より
#   `clear` 下)。⛔ 身舎の軒の上に載せない(瓦どうしが噛む)。
# ・平面 = 瓦場の先端が身舎の柱芯から **1.1 間**、幅 **2.8 間**(絵図の凸そのもの)。
#   向拝柱 2 本は瓦の端から 0.40 内・軒先から 0.45 内(角柱 0.20 を礎石に立てる)。
#   ⚠ 向拝柱は身舎の柱の通りに乗らない(身舎は 1 間等間で ±2.727、向拝柱は ±2.145)。
#   絵図の幅を優先し、海老虹梁は身舎の**内法長押の上の小壁**へ取り付く【U】。
# ・木階は向拝の下(幅 1.80・5 級)。
KH = dict(depth=1.1, width=2.8, kobai=0.40, clear=0.22, postIn=0.40, eaveIn=0.45,
          post=0.20, kaidanW=1.80)


def kohai_build(M, uv, mw, hu, hv, eaveZ, eave, off, name):
    """向拝を組む。軸部は `M` へ積み、瓦場・野地・袖瓦・礎石は別体で返す(Unity ローカル)。"""
    k = KH["kobai"]
    Zf = hv + KH["depth"] * K              # 向拝の瓦場の先端(軒先)
    xr = KH["width"] * K / 2.0             # 瓦場の半幅
    xp = xr - KH["postIn"]                 # 向拝柱の芯 X
    zp = Zf - KH["eaveIn"]                 # 向拝柱の芯 Z
    Ze = hv + eave                         # 身舎の軒先の通り
    z_ze = eaveZ + off - KH["clear"]       # 身舎の軒先の下での向拝の名目面
    zfk = lambda X, Z: z_ze - (Z - Ze) * k
    Zt = hv + 0.12                         # 瓦場の上端(桁の外面 hv+0.09 の外)
    # ---- 瓦場(Blender 座標: x = −X, y = −Z)。上りは +y(= 身舎の側)⇒ yaw 90
    poly = [(-xr, -Zf), (xr, -Zf), (xr, -Zt), (-xr, -Zt)]
    roof = GR._tile_field_k([poly], (-xr, -Zf), 90, zfk(0.0, Zf), name + "_kohai_roof", k)
    bpy.context.view_layer.update()
    offk = GK.roof_dmin(roof, lambda X, Z: True, zfk) - 0.02
    slab = GK.noji_slab(name + "_kohai_noji", lambda X, Z: True, (-xr, xr, Zt, Zf), zfk, offk - 0.02)
    kt = zfk(0.0, zp) + offk - 0.05        # 向拝桁の天端 = 野地の下面
    # ---- 軸部
    B3(M, -xr + 0.10, xr - 0.10, zp - 0.08, zp + 0.08, kt - 0.18, kt, uv["wood_h"], mw, grain="u")  # 向拝桁
    kb0, kb1 = kt - 0.18 - 0.34, kt - 0.18
    B3(M, -xp - 0.25, xp + 0.25, zp - 0.075, zp + 0.075, kb0, kb1, uv["wood_h"], mw, grain="u")    # 虹梁(木鼻込み)
    r = KH["post"] / 2.0
    for s in (-1, 1):
        B3(M, s * xp - r, s * xp + r, zp - r, zp + r, 0.18, kb1, uv["wood"], mw, grain="h")         # 向拝柱
        # 海老虹梁 — 柱の頭から身舎の小壁へ上り勾配で繋ぐ。⛔ 箱を段に積まない(`SH.stick`)
        SH.stick(M, (s * xp, zp - r, kb0 + 0.06), (s * xp, hv + 0.05, kb1 + 0.30),
                 0.12, 0.24, uv["wood_h"], mw)
        # 破風板(片流れの端)— 瓦場の小口を下から塞ぐ
        SH.stick(M, (s * (xr + 0.03), Zf + 0.02, zfk(0.0, Zf) + offk - 0.06),
                 (s * (xr + 0.03), Ze + 0.12, zfk(0.0, Ze + 0.12) + offk - 0.06),
                 0.06, 0.26, uv["wood"], mw)
    zf0 = zfk(0.0, Zf)
    B3(M, -xr - 0.03, xr + 0.03, Zf - 0.05, Zf + 0.01, zf0 + offk - 0.24, zf0 + offk - 0.02,
       uv["wood_h"], mw, grain="u")                                                               # 鼻隠し
    # ---- 袖瓦(片流れの両端の稜)— 瓦場を切った断面を隠す。⚠ 身舎の軒と噛まないよう手前で止める
    objs = [roof, slab]
    for s in (-1, 1):
        bx = -s * (xr - 0.02)
        objs += GR.ridge((bx, -(Zf + 0.02), zf0 + 0.22),
                         (bx, -(Ze + 0.10), zfk(0.0, Ze + 0.10) + 0.22),
                         name + "_kohai_sode", w=0.36, h=0.28)
    # ---- 礎石(切石)
    for s in (-1, 1):
        st = RM.kidan(r + 0.02, r + 0.02, {q: 0.08 for q in ("+X", "-X", "+Z", "-Z")}, 0.20,
                      name + "_kohai_soseki", finish=("+X", "-X", "+Z", "-Z"))
        # ⚠ 底を地盤 0 に揃える(`RM.kidan` は根入れの下に面取りの逃げを持つ)。⛔ 部材の底を
        #   地盤より下げない ── 棟梁が「触れている箇所」を測るとき底が嘘をつく
        zmin = min(v.co.z for o in st for v in o.data.vertices)
        for o in st:
            o.data.transform(Matrix.Translation((-s * xp, -zp, -zmin))); o.data.update()
        objs += st
    objs = [o for o in objs if o]
    info = dict(Zf=Zf, xr=xr, xp=xp, zp=zp, eaveH=zf0, kt=kt, kb0=kb0, offk=offk, Ze=Ze)
    print("[kohai] 瓦場 X ±%.3f × Z %.3f〜%.3f / 柱 X ±%.3f Z %.3f / 軒先 %.3f / 虹梁の下端 %.3f / 勾配 %.2f"
          % (xr, Zt, Zf, xp, zp, zf0, kb0, k))
    return objs, info


def part_name(kind, nu, nv, kohai=False):
    """`EdoAssets.Own.SannoDo(kata, nuKen, nvKen, xMm, zMm)` と同じ綴り。
    ⚠ 間数は `%g`(3 → "3" / 4.5 → "4.5")= C# の `Len2` と同じ出方。mm は `round`。"""
    tag = ("Hogyo" if kind == "hogyo" else "Irimoya") + ("Kohai" if kohai else "")
    return "Sanno_Do_%s_%gx%gken_%dx%d" % (tag, nu, nv, round(nu * K * 1000), round(nv * K * 1000))


# ==========================================================================
# B 稲荷社 — 縋破風形式の春日造・銅板葺【A 千代田区の実測】
# ==========================================================================
IN = dict(ken=1.0, floor=1.20, post=0.16, en=0.50, enT=0.09, koran=0.64,
          eaveZ=2.90, eave=0.55, kobai=0.60, hisashi=1.30, hkobai=0.33,
          uchinori=1.45, kaidanN=6, kaidanRun=0.24, kaidanW=1.00)


def inari(name="Sanno_Inari_Kasuga_1ken"):
    """**稲荷社 — 一間社春日造(縋破風形式)・銅板葺**【A 千代田区の実測 = 指図 bom 行32】。

    ⭐ **春日造は妻入**。大棟は正面(+Z)へ直交して走り(= Z 方向)、
      **正面の破風がそのまま庇へ縋(すが)って下りる**のが「縋破風形式」。
      ⇒ 庇の屋根面は**妻の折れ線の形をそのまま前へ送りながら下げた面**で、
      ⛔ 別勾配の切妻を継ぎ足した物ではない(継ぐと破風が折れて春日造に見えない)。

    ⚠ **葺材はこの一棟だけ銅板**(`Doukawara`)。瓦の勾配 `GR.RATIO` に縛られないので
      本(6寸)/ 庇(3寸3分)を別に取れる。⛔ 瓦場を流用しない。
    ⚠ 朱は在庫の `Shu_Torii`(`Assets/Edo/Materials/Shu_Torii.mat`)。⛔ 新規に作らない。
      山王の remap は `donorDirs` の最後に `Assets/Edo/Materials` を持つので当たる。

    ⚠ **一間社なので指図の `munes[稲荷社]` の 3×3間(5.454角)より小さい**(実測は下の print)。
      一間社は身舎が 1 間角と決まっている形式で、⛔ 3間角へ引き伸ばすと春日造ではなくなる。
      ⇒ 指図の矩形は**据える場所の取り**として読み、部材はその中央に納める。"""
    ms, uv = SH.mats()
    mw = SH.W
    dou = SH.doukawara()
    shu = V.named_material("Shu_Torii")
    try:                                  # 検証レンダだけのため(FBX は材質名しか運ばない)
        shu.use_nodes = True
        b = next((n for n in shu.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b:
            b.inputs['Base Color'].default_value = (0.45, 0.043, 0.024, 1.0)
            b.inputs['Roughness'].default_value = 0.55
    except Exception:
        pass
    ms = list(ms) + [dou, shu]
    M_DOU, M_SHU = len(ms) - 2, len(ms) - 1
    h = IN["ken"] * K / 2.0                                   # 身舎の半スパン 0.909
    fl, en, T = IN["floor"], IN["en"], IN["enT"]
    ou, ov = h + en, h + en
    eaveZ, eave, kb = IN["eaveZ"], IN["eave"], IN["kobai"]
    hx = h + eave                                             # 軒先の X(流れは ±X)
    zr = eaveZ + hx * kb                                      # 大棟の高さ
    prof = lambda X: zr - abs(X) * kb                         # 妻の折れ線(X → 屋根面の高さ)
    hz = IN["hisashi"]                                        # 庇(縋破風)の出
    drop = hz * IN["hkobai"]                                  # 庇の先端での下がり
    M = VM.Mesh()
    # ---- 基壇(切石)は RM.kidan に任せる(下で別体)/ 床束
    for su in (-h, h):
        for sv in (-h, h):
            B3(M, su - 0.08, su + 0.08, sv - 0.08, sv + 0.08, 0.10, fl - 0.10,
                    uv["wood"], mw, grain="h")
    B3(M, -h - 0.02, h + 0.02, -h - 0.02, h + 0.02, fl - 0.10, fl, uv["wood"], mw, grain="u")
    # ---- 縁 + 高欄(正面 +Z に階の口)
    for (u0, u1, v0, v1, g) in ((-ou, ou, -ov, -h, "u"), (-ou, ou, h, ov, "u"),
                                (h, ou, -h, h, "v"), (-ou, -h, -h, h, "v")):
        B3(M, u0, u1, v0, v1, fl - T, fl, uv["wood"], mw, grain=g)
    for (uu, vv) in [(-ou, -ov), (ou, -ov), (-ou, ov), (ou, ov)]:
        B3(M, uu - 0.055, uu + 0.055, vv - 0.055, vv + 0.055, 0.10, fl - T,
                uv["wood"], mw, grain="h")
    kg = IN["kaidanW"] / 2.0 + 0.08
    kh = IN["koran"]
    runs = [("u", -ov, -ou, ou), ("v", ou, -ov, ov), ("v", -ou, -ov, ov),
            ("u", ov, -ou, -kg), ("u", ov, kg, ou)]
    for (along, fx, a, b) in runs:
        if b - a < 0.18:
            continue
        for (z0, z1, t) in ((fl, fl + 0.09, 0.05), (fl + kh - 0.17, fl + kh - 0.09, 0.045),
                            (fl + kh - 0.09, fl + kh, 0.065)):
            if along == "u":
                B3(M, a, b, fx - t, fx + t, z0, z1, uv["wood_h"], M_SHU, grain="u")
            else:
                B3(M, fx - t, fx + t, a, b, z0, z1, uv["wood_h"], M_SHU, grain="v")
        n = max(2, int(round((b - a) / 0.42)))
        for i in range(n + 1):
            c = a + (b - a) * i / float(n)
            if along == "u":
                B3(M, c - 0.035, c + 0.035, fx - 0.035, fx + 0.035, fl + 0.09,
                        fl + kh - 0.09, uv["wood"], M_SHU, grain="h")
            else:
                B3(M, fx - 0.035, fx + 0.035, c - 0.035, c + 0.035, fl + 0.09,
                        fl + kh - 0.09, uv["wood"], M_SHU, grain="h")
    for (uu, vv) in ((-ou, -ov), (ou, -ov), (-ou, ov), (ou, ov)):   # 高欄の隅の擬宝珠
        SH.giboshi(M, uu, vv, fl + kh, uv["wood"], mw)
    # ---- 木階(正面・庇の下)
    n_k, run_k = IN["kaidanN"], IN["kaidanRun"]
    hw = IN["kaidanW"] / 2.0
    rise = fl / float(n_k)
    for i in range(n_k):
        zt = rise * (i + 1)
        v1 = ov + run_k * (n_k - i)
        v0 = v1 - run_k - 0.03
        B3(M, -hw, hw, v0, v1, zt - 0.055, zt, uv["wood"], mw, grain="u")
        B3(M, -hw, hw, v0, v0 + 0.04, zt - rise, zt - 0.055, uv["wood_h"], mw, grain="u")
    for s in (-1, 1):                       # 側桁 — ⛔ 板を床まで落とさない(木箱に見える)
        SH.stick(M, (s * (hw + 0.05), ov + run_k * n_k + 0.06, 0.12),
                 (s * (hw + 0.05), ov + 0.02, fl - 0.06), 0.07, 0.22, uv["wood"], mw)
    # ---- 軸部(朱の柱・白壁・御扉)
    zu = fl + IN["uchinori"]
    keta = zu + 0.36
    pr = IN["post"] / 2.0
    for su in (-h, h):
        for sv in (-h, h):
            B3(M, su - pr, su + pr, sv - pr, sv + pr, fl, keta, uv["wood"], M_SHU, grain="h")
    for sv in (-h, h):                                   # 長押・頭貫
        B3(M, -h - pr, h + pr, sv - 0.055, sv + 0.055, keta - 0.14, keta,
                uv["wood_h"], M_SHU, grain="u")
    for su in (-h, h):
        B3(M, su - 0.055, su + 0.055, -h - pr, h + pr, keta - 0.14, keta,
                uv["wood_h"], M_SHU, grain="v")
    # 壁(背面と両側面は白漆喰・正面は御扉)
    kt = 0.045
    B3(M, -h + pr, h - pr, -h - kt, -h + kt, fl, keta - 0.14, uv["wall"], SH.WC, grain="u")
    for su in (-h, h):
        B3(M, su - kt, su + kt, -h + pr, h - pr, fl, keta - 0.14, uv["wall"], SH.WC, grain="v")
    B3(M, -h + pr, h - pr, h - kt, h + kt, zu, keta - 0.14, uv["wall"], SH.WC, grain="u")
    B3(M, -h + pr, h - pr, h - 0.06, h + 0.06, fl, fl + 0.06, uv["wood_h"], mw, grain="u")
    for (a, b) in ((-h + pr, -0.01), (0.01, h - pr)):     # 御扉(両開き)
        B3(M, a, b, h + 0.02, h + 0.06, fl + 0.06, zu, uv["itado"], SH.DW, grain="u")
    # ⛔⛔ **軸部の上を開けたまま屋根を架けない。**頭貫の天端(keta)と屋根面(prof)の間に
    #   **0.2〜0.5m の帯**が空き、横から中が見通せる(2026-09-22 に背面の斜めで実見)。
    #   ⇒ 妻入なので**前後は三角の妻壁**、側面は屋根なりの水平な小壁で塞ぐ。
    usw = [-h + 2 * h * i / 8.0 for i in range(9)]
    for vv in (-h, h):
        GK.vstrip_u(M, usw, vv - kt, vv + kt, lambda u: keta - 0.14,
                    lambda u: prof(u) - 0.05, uv["wall"], SH.WC)
    for su in (-h, h):
        B3(M, su - kt, su + kt, -h, h, keta - 0.14, prof(h) - 0.05, uv["wall"], SH.WC, grain="v")
    # ---- 屋根(銅板葺)。本屋根 = 妻入の切妻、正面は縋破風の庇
    # ⭐⭐ **縋破風は「妻の折れ線をそのまま前へ送りながら下げた一枚の面」**。
    #   ⛔ 別勾配の切妻を継ぎ足さない — 継ぐと破風が折れて春日造に見えない。
    zb = -(h + eave)                                      # 背面の軒先(Z)
    nX = 16
    xs = [-hx + 2 * hx * i / nX for i in range(nX + 1)]
    rows = [(zb, 0.0), (h, 0.0)] + [(h + hz * (j + 1) / 6.0, drop * (j + 1) / 6.0)
                                    for j in range(6)]
    roof_sheet(M, xs, rows, prof, 0.05, uv["wall"], M_DOU, mw, uv["wood_h"])
    # 瓦棒(流れに沿う銅の棒)。⛔ 平板1枚で終わらせない — 銅板葺は棒が並ぶのが姿
    nb = 7
    for i in range(nb + 1):
        xb = -hx + 2 * hx * i / float(nb)
        for (v0, v1, d0, d1) in ((zb, h, 0.0, 0.0), (h, h + hz, 0.0, drop)):
            # ⚠ 芯は面の **+0.02**(+0.05 にすると棒が 1.5cm 浮いて立面に隙が出る)
            SH.stick(M, (xb, v0, prof(xb) + 0.02 - d0), (xb, v1, prof(xb) + 0.02 - d1),
                     0.07, 0.07, uv["wall"], M_DOU)
    # 破風板(背面の妻・正面は庇の先まで縋る)+ 懸魚
    for (vv, dd, side) in ((zb, 0.0, -1), (h + hz, drop, +1)):
        for s in (-1, 1):
            hafu_run(M, prof, hx, vv, dd, s, uv["wood"], M_SHU, side)
    gegyo(M, 0.0, h + hz + 0.06 + 0.02, zr - drop - 0.34, uv["wood"], M_SHU)
    gegyo(M, 0.0, zb - 0.06 - 0.02, zr - 0.34, uv["wood"], M_SHU)
    # 大棟(箱棟)+ 千木・鰹木
    B3(M, -0.13, 0.13, zb - 0.06, h + hz + 0.06, zr + 0.02, zr + 0.22,
            uv["wall"], M_DOU, grain="v")
    for j in range(3):                                      # 鰹木
        vv = zb + 0.55 + (h + hz - zb - 1.10) * j / 2.0
        B3(M, -0.085, 0.085, vv - 0.17, vv + 0.17, zr + 0.22, zr + 0.39,
                uv["wall"], M_DOU, grain="v")
    # 千木 — 棟の両端で交叉して立つ材。⭐ 春日造の合図。
    # ⛔ 箱を段に積んで斜材を作らない(階段状の輪郭になる)。`SH.stick` で通す。
    for vv in (zb + 0.10, h + hz - 0.10):
        for s in (-1, 1):
            SH.stick(M, (s * 0.07, vv, zr - 0.08), (s * 0.40, vv, zr + 0.52),
                     0.075, 0.09, uv["wood"], M_SHU)
    body = M.to_object(name + "_body", ms)
    out = {s: 0.42 for s in ("+X", "-X", "+Z", "-Z")}
    stones = RM.kidan(h, h, out, 0.30, name + "_kidan", finish=("+X", "-X", "+Z", "-Z"))
    for o in stones:
        o.data.transform(Matrix.Translation((0.0, 0.0, 0.30))); o.data.update()
    V.dedup_materials()
    o = V.join([body] + stones, name)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    info = dict(kind="kasuga", hu=h, hv=h, fl=fl, keta_top=keta, ou=ou, ov=ov,
                zr=zr, eave=eave, hz=hz)
    print("[inari] %s 身舎 %.3f 角 / 床 %.2f / 軒先 %.2f / 大棟 %.3f / 庇の出 %.2f(下がり %.2f)"
          % (name, 2 * h, fl, eaveZ, zr, hz, drop))
    return o, info


def quad_out(M, pts, want, uvr, mat):
    """(u,v,h) の4点を、**外向き `want` を向く巻き**で積む(逆なら自動で反転)。

    ⛔⛔ 巻き順を手で決めない — 軸の入れ替え(`SH.q`)と `vkmesh` の厚み反転が重なるので、
      符号を一つ取り違えると Unity の裏面カリングで面が丸ごと消える(README「軸の鎖」)。
      ⭕ 法線を計算して `want` と内積の符号で決めれば、取り違えようがない。"""
    a, b, c = (Vector(p) for p in pts[:3])
    if ((b - a).cross(c - b)).dot(Vector(want)) < 0:
        pts = list(reversed(pts))
    M.quad_uvs([SH.q(*p) for p in pts], _uvs4(uvr), mat)


def roof_sheet(M, xs, rows, prof, thk, uvr, mat, mat_bot, uvr_bot):
    """**厚みのある一枚の屋根面**(銅板葺)。`rows` = [(v, 下がり), …] を前後に並べ、
    面の高さは `prof(X) − 下がり`。

    ⛔ **升ごとに独立した「厚い板」を積まない** — 隣り合う升の小口が内部で重なって
      z 闘争になり、面数も倍になる。⭕ 上面と下面を通しで張り、**外周にだけ**小口を回す。"""
    Z = lambda X, d: prof(X) - d
    for i in range(len(xs) - 1):
        for j in range(len(rows) - 1):
            x0, x1 = xs[i], xs[i + 1]
            (v0, d0), (v1, d1) = rows[j], rows[j + 1]
            top = [(x0, v0, Z(x0, d0)), (x1, v0, Z(x1, d0)),
                   (x1, v1, Z(x1, d1)), (x0, v1, Z(x0, d1))]
            quad_out(M, top, (0, 0, 1), uvr, mat)
            quad_out(M, [(p[0], p[1], p[2] - thk) for p in top], (0, 0, -1), uvr_bot, mat_bot)
    for (j, want) in ((0, (0, -1, 0)), (len(rows) - 1, (0, 1, 0))):       # 前後の小口
        v, d = rows[j]
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            quad_out(M, [(x0, v, Z(x0, d)), (x1, v, Z(x1, d)),
                         (x1, v, Z(x1, d) - thk), (x0, v, Z(x0, d) - thk)], want, uvr, mat)
    for (i, want) in ((0, (-1, 0, 0)), (len(xs) - 1, (1, 0, 0))):         # 左右の小口
        x = xs[i]
        for j in range(len(rows) - 1):
            (v0, d0), (v1, d1) = rows[j], rows[j + 1]
            quad_out(M, [(x, v0, Z(x, d0)), (x, v1, Z(x, d1)),
                         (x, v1, Z(x, d1) - thk), (x, v0, Z(x, d0) - thk)], want, uvr, mat)


def _uvs4(uvr):
    u0, v0, u1, v1 = uvr
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def hafu_run(M, prof, hx, vv, dd, s, uvr, mat, side, w=0.075, t=0.30):
    """**破風板**。妻の折れ線 `prof` に沿って s(±X)側へ 1 本通す。

    ⛔⛔ **軸平行の箱を段に積んで斜材を作らない。**輪郭が階段状になって「木の板」に見えない
      (2026-09-22 に稲荷社の破風と千木で実見)。⭕ `SH.stick`(2点を結ぶ角材)で継ぐ。"""
    n = 6
    pts = []
    for i in range(n + 1):
        x = s * hx * (1.0 - i / float(n))
        pts.append((x, vv + side * (w / 2.0 + 0.01), prof(x) - dd - 0.06))
    for i in range(n):
        SH.stick(M, pts[i], pts[i + 1], w, t, uvr, mat)


def gegyo(M, uu, vv, z, uvr, mat):
    """**懸魚**(破風の拝みに吊る板)。蕪の輪郭を3段の箱で出す。"""
    for (r, a, b) in ((0.10, 0.0, 0.10), (0.20, 0.10, 0.34), (0.11, 0.34, 0.44)):
        B3(M, uu - r, uu + r, vv - 0.035, vv + 0.035, z + a, z + b, uvr, mat, grain="h")


# ==========================================================================
# E 御厩 / F 御蔵 — 既存の附属屋の生成器を呼ぶだけ(⛔ 別実装を書かない)
# ==========================================================================
def umaya(nu=4, nv=3, name=None):
    """**御厩 4間(u)× 3間(v)**。岡部の吹き放ちの厩 `build_okabe_fuzokuya.umaya` を
    梁間3間・桁行4間で呼ぶ(= 類型の `Typ_Umaya` と同じ型)。

    ⚠ **ローカル +X = 桁行(4間・棟の走る向き)= 指図の u** / **+Z = 開口(吹き放ち)面**。
    ⚠ 軒 2.55 / 馬房前の半高壁 1.15 / 軒の出 0.70 は生成器の断り書きどおりの組
      (吹き放ちの帯 0.93m を保つ)。⛔ 軒だけ下げない。
    ⭐ 屋根はキットの `roof` = 山王の「在庫の本瓦」(楼門・御供所と同じ材)。
      ⇒ 指図 bom 行34 の**本瓦葺**を満たす。"""
    # ⭐ 2026-09-23(EDO-0395 施主裁定B)に 3 間(u)× 2 間(v)を足した。軒・半高壁・軒の出は
    #   4×3 と同じ組(吹き放ちの帯を保つ)。馬房は **1 間に 1 房**(`bo = nu`)── ⚠ 4×3 は従来どおり 4 房。
    name = name or "Sanno_Umaya_%dx%dken_%dx%d" % (nu, nv, round(nu * K * 1000), round(nv * K * 1000))
    o = OF.umaya(uKen=nv, vKen=nu, name=name, eaveH=2.55, frontH=1.15, noki=0.70,
                 bo=4 if (nu, nv) == (4, 3) else nu)
    if isinstance(o, tuple):
        o = o[0]
    return o, dict(kind="umaya", hu=nu * K / 2.0, hv=nv * K / 2.0, fl=0.0)


def kura(name="Sanno_Kura_4x5ken_7272x9090"):
    """**御蔵 4間(u・梁間)× 5間(v・桁行)= 土蔵造・置屋根**(指図 bom 行33)。

    ⭐ 松江松平の土蔵 `build_matsudaira_dewa_fuzokuya.dozo` に 2026-09-22 に足した
      `okiyane` で焼く。⛔ 別実装を書かない。
    ⭐ **置屋根** = 土蔵本体の漆喰の塗屋根の上に、独立した木の小屋を載せて瓦を葺く作り。
      ⇒ 壁の天端と瓦の軒先の間に**帯が空く**のが正しい姿(素通しではない — 下に塗屋根がある)。
    ⚠ `dozo` は**長手(棟)= ローカル +X** で焼くので、桁行5間が X に来る。
      指図は u=4間 / v=5間 なので、**焼いたあと Z 回りに 90° 振って** ローカル +X = u に揃える
      (山王の部材はすべて ローカル X = 東(u))。"""
    o = MF.dozo(uk=4, vk=5, name=name, eave=3.70, mado=0.85, gawa_mado=0,
                mizukiri_tooshi=False, okiyane=0.42)
    V.rotate_z([o], 90.0)
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    return o, dict(kind="kura", hu=4 * K / 2.0, hv=5 * K / 2.0, fl=0.0)


# ==========================================================================
# G 薬師堂(六角の宝形 + 高欄付きの方形の石の壇)【EDO-0438 施主裁定B 2026-09-26】
# ==========================================================================
# ⭐ 典拠: 江戸名所図会 巻之三「日吉山王権現社」NDL 2563386 コマ7 ── 多角形の宝形が高欄付きの
#   壇の上に建つ【B】。胴に見える面が 3 つ ⇒ 六角【B】。御宮絵図の朱矩形(4.5 間角)は
#   **壇の外形**と読む【P/U 施主裁定B】。⛔ 堂の柱芯を 4.5 間へ引き伸ばさない。
# ⭐ 以下の丈・意匠は**すべて【U 部材方 2026-09-26】**(史料は形の種類しか言わない):
#   ・壇 = 切石の方形 8.181 角・丈 **0.45**(`RM.kidan` の葛石+羽目石を四面とも仕上げ)。
#     ⛔ 丈は **0.15〜0.65 の硬い条件**(2026-09-26 指図の検査): 壇の下端 = 境内の面 28.30、
#     足元の造成前の地盤の中央値 ≒ 28.70 ⇒ 天端と地盤の差 ±0.25 以内。0.45 = 御供所の基壇と同じ丈
#     (天端 28.75・差 +0.05)。初版の 0.90 は差 +0.50 で退けられた
#   ・壇の高欄 = 木の高欄(地覆・平桁・架木・擬宝珠)丈 0.80・壇の縁から 0.15 内
#   ・壇の石段 = 南(+Z)の中央・幅 2.40・蹴上 0.15 × 3(外へ出るのは 2 段)・踏面 0.32
#   ・堂 = 正六角・一辺 1 間(柱芯の外接円の半径 = 1.818 ⇒ 対角 3.636・対辺 3.149)
#   ・床 = 壇の天端 + 0.60 の高床・縁 0.50 + 高欄 0.70・正面に木階 4 級(幅 1.10)
#   ・正面の柱間 = 板扉 / 斜め前の 2 面 = 連子窓 / 残る 3 面 = 板壁(小壁は漆喰)
#   ・軒先 = 床 + 2.55・軒の出 0.90(壁の通りから直角に)。勾配は瓦の 5.5 寸のまま(棟高は従属値)
# ⭐ 六角の宝形の瓦場: キットの `roof 2x2` を**面ごとの三角形**(軒の一辺 + 頂点)で `GR.tile_field`
#   に葺かせ、6 面を 60° ずつ振る。隅棟 6 本は `GR.ridge`(キットの棟モジュール)で継ぐ。
#   ⛔ 四角錐の `make_yosemune` を流用しない(正方形しか作れない)。
Y6 = dict(dan=4.5 * K, danH=0.45, koranIn=0.15, koranH=0.80,
          stairW=2.40, stairN=3, stairT=0.32,
          R=K, floorUp=0.60, en=0.50, enKoran=0.70, eaveUp=2.55, eave=0.90,
          post=0.10, kaiN=4, kaiW=1.10)


def _hexd(X, Z):
    """正六角(頂点が ±X・平らな辺が ±Z)の「中心からの対辺方向の距離」。"""
    c, s = math.cos(math.radians(30.0)), 0.5
    return max(abs(Z), abs(X * c + Z * s), abs(X * c - Z * s))


def koran_u(M, uv, mw, fx, a, b, z, kh, gib):
    """**高欄 1 辺**(論理の u 方向へ a..b・v = fx)。`gib` = 擬宝珠を立てる u の列。
    ⭐ 辺を 60°/90° ずつ回して閉じるので、各辺は b 端にだけ擬宝珠を立てる(隅で重ねない)。"""
    if b - a < 0.25:
        return
    for (z0, z1, t) in ((z, z + 0.11, 0.06), (z + kh - 0.20, z + kh - 0.11, 0.05),
                        (z + kh - 0.11, z + kh, 0.075)):
        B3(M, a, b, fx - t, fx + t, z0, z1, uv["wood_h"], mw, grain="u")
    n = max(2, int(round((b - a) / 0.62)))
    for i in range(n + 1):
        c = a + (b - a) * i / float(n)
        B3(M, c - 0.045, c + 0.045, fx - 0.045, fx + 0.045,
           z + 0.11, z + kh - 0.11, uv["wood"], mw, grain="h")
    for c in gib:
        SH.giboshi(M, c, fx, z + kh, uv["wood"], mw)


def _hex_prism(name, r, z0, z1, mat, uvr):
    """正六角柱(Blender 座標で直に)。頂点は ±X(Unity でも ±X)。"""
    vs = []
    for z in (z0, z1):
        for j in range(6):
            a = math.radians(60.0 * j)
            vs.append((r * math.cos(a), r * math.sin(a), z))
    faces = [list(range(5, -1, -1)), list(range(6, 12))]
    faces += [[j, (j + 1) % 6, 6 + (j + 1) % 6, 6 + j] for j in range(6)]
    o = GR._mesh_from_poly(name, vs, faces, recalc=True)
    o.data.materials.append(mat)
    V.set_uv_rect(o, uvr, axes=('x', 'y'))
    return o


def hex_roof(name, A, eave_z):
    """**六角の宝形の瓦場**(Blender 座標・軒先 z = eave_z)。A = 軒先の対辺距離(中心から)。"""
    Rr = A / math.cos(math.radians(30.0))
    h = A * GR.RATIO
    Vt = [(Rr * math.cos(math.radians(60.0 * j)), Rr * math.sin(math.radians(60.0 * j)))
          for j in range(6)]
    pieces = []
    for j in range(6):
        a, b = Vt[j], Vt[(j + 1) % 6]
        yaw = 60.0 * j + 30.0 + 180.0                  # 上り = 面の外向き法線の逆
        f = GR.tile_field([[a, b, (0.0, 0.0)]], a, yaw, 0.0, "%s_f%d" % (name, j))
        if f:
            pieces.append(f)
    for j in range(6):                                  # 隅棟 6 本(キットの棟モジュール)
        pieces += GR.ridge((Vt[j][0], Vt[j][1], 0.02), (0.0, 0.0, h), name + "_sumi",
                           w=0.34, h=0.28)
    p = GR.palette()
    ru = p['uv_roof']
    rr = (ru[0] - 0.01, ru[1] - 0.01, ru[0] + 0.01, ru[1] + 0.01)
    # 露盤(六角)。⚠ 下の段は隅棟 6 本の頂の小口(冠瓦の丈 0.28)を呑む丈にする — 四角の
    #   `make_yosemune` の 0.16 のままだと棟の頂の間に暗い隙が覗いた(2026-09-26 近景レンダ)
    for (r, hgt, zb) in ((0.48, 0.26, h - 0.10), (0.34, 0.20, h + 0.16)):
        pieces.append(_hex_prism(name + "_roban", r, zb, zb + hgt, p['roof'], rr))
    V.dedup_materials()
    o = V.join(pieces, name)
    o.data.transform(Matrix.Translation((0.0, 0.0, eave_z))); o.data.update()
    return o, h


def hex_noji(name, A, zf, off):
    """**六角の野地**(6 枚の三角 × 上下)。面ごとに平面なので三角で厳密に張れる。
    上面 = 瓦の材(`GK.noji_slab` と同じ意匠)/ 下面 = 木。座標は Blender。"""
    roofmat = bpy.data.materials.get("roof")
    ms, uv = SH.mats()
    ru = V.sample_uv(GR.MOD, pick_high=True)
    rtop = (ru[0] - 0.01, ru[1] - 0.01, ru[0] + 0.01, ru[1] + 0.01)
    rb = uv["wood_h"]
    Rr = A / math.cos(math.radians(30.0))
    Vt = [(Rr * math.cos(math.radians(60.0 * j)), Rr * math.sin(math.radians(60.0 * j)))
          for j in range(6)]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for j in range(6):
        tri = [Vt[j], Vt[(j + 1) % 6], (0.0, 0.0)]
        for dz, rect, mi, order in ((0.0, rtop, 0, tri), (-0.03, rb, 1, tri[::-1])):
            vs = [bm.verts.new((x, y, zf(-x, -y) + off + dz)) for (x, y) in order]
            f = bm.faces.new(vs)
            f.material_index = mi
            for lp, (x, y) in zip(f.loops, order):
                lp[uvl].uv = (rect[0] + (rect[2] - rect[0]) * ((x % 1.8) / 1.8),
                              rect[1] + (rect[3] - rect[1]) * ((y % 1.8) / 1.8))
    bm.normal_update()
    for f in bm.faces:                                   # 上面は +z・下面は −z を向ける
        want = 1.0 if f.material_index == 0 else -1.0
        if f.normal.z * want < 0:
            f.normal_flip()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(roofmat); me.materials.append(ms[0])
    return o


def _hex_checks(roof, slab, ap, A, fl, n=60):
    """join の前に屋根と野地を別々の BVH で突き合わせる(`soffit_pre` の六角版)。
    ① 真上: 壁の通り +0.30 の内で、上から落とした光線が瓦にも野地にも当たらない数
    ② 軒裏: 壁の通り +0.12 〜 軒先 −0.08 の帯で、下から上げた光線が野地より先に瓦に当たる / 空へ抜ける数"""
    dg = bpy.context.evaluated_depsgraph_get()
    br, bs = BVHTree.FromObject(roof, dg), BVHTree.FromObject(slab, dg)
    Rr = A / math.cos(math.radians(30.0))
    top_miss = top_tot = bad = miss = tot = 0
    for i in range(n + 1):
        for j in range(n + 1):
            X = -Rr + 2 * Rr * i / float(n)
            Z = -Rr + 2 * Rr * j / float(n)
            d = _hexd(X, Z)
            if d <= ap + 0.30:
                top_tot += 1
                o = Vector((-X, -Z, 40.0)); dr = Vector((0, 0, -1))
                if br.ray_cast(o, dr, 80.0)[0] is None and bs.ray_cast(o, dr, 80.0)[0] is None:
                    top_miss += 1
            if ap + 0.12 < d < A - 0.08:
                org, dr = Vector((-X, -Z, fl + 0.5)), Vector((0, 0, 1))
                lr = br.ray_cast(org, dr, 12.0)[0]
                ls = bs.ray_cast(org, dr, 12.0)[0]
                tot += 1
                if lr is None and ls is None:
                    miss += 1
                elif ls is None or (lr is not None and ls.z > lr.z + 0.001):
                    bad += 1
    return (top_tot, top_miss), (tot, bad, miss)


def _logical_to_blender(objs):
    for o in objs:                                   # 論理 → Blender(Rz180°・det +1)
        o.data.transform(Matrix.Diagonal((-1.0, -1.0, 1.0, 1.0)))
        o.data.update()


def yakushi6(name="Sanno_Do_Hogyo6Dan_4.5x4.5ken_8181x8181"):
    """**薬師堂 — 高欄付きの方形の石の壇 + 六角の宝形の小堂**(EDO-0438)。

    ⭐ ピボット = **壇の外形の中心・壇の下端(地盤)**。正面(壇の石段・堂の板扉と木階)= +Z。
    【組み立て — 下から】① 切石の壇 8.181 角・丈 0.90 ② 壇の南の石段 ③ 壇の高欄
      ④ 堂の床束・縁束 ⑤ 六角の床(縁込み)⑥ 縁の高欄・木階 ⑦ 柱 6 本・壁(板扉/連子窓/板壁)
      ⑧ 桁 ⑨ 野地 ⑩ 六角の宝形の瓦場・隅棟・露盤・宝珠。"""
    P = Y6
    hd = P["dan"] / 2.0
    dH = P["danH"]
    R = P["R"]
    half = R / 2.0                                   # 一辺の半分(= 0.909)
    ap = R * math.cos(math.radians(30.0))            # 柱芯の対辺距離(1.5745)
    fl = dH + P["floorUp"]
    eaveZ = fl + P["eaveUp"]
    eave = P["eave"]
    A = ap + eave                                    # 軒先の対辺距離
    k = GR.RATIO
    ms, uv = SH.mats()
    mw = SH.W
    # ---- 屋根・野地(Blender 座標)
    roof, hR = hex_roof(name + "_roof", A, eaveZ)
    zf = lambda X, Z: eaveZ + k * (A - _hexd(X, Z))
    off = GK.roof_dmin(roof, lambda X, Z: True, zf) - 0.02
    slab = hex_noji(name + "_noji", A, zf, off - 0.02)
    keta_top = eaveZ + k * eave + off - 0.03         # 桁の天端 = 野地の下面(`do()` と同じ)
    top = keta_top - DO["ketaH"]
    roban_top = eaveZ + hR + 0.36                    # 露盤の天端(`hex_roof` の 2 段目の上端)
    hq = houju(name + "_houju", roban_top)
    chk_top, chk_soff = _hex_checks(roof, slab, ap, A, fl)
    # ---- 壇(切石)と石段(論理 = Unity ローカル → Blender)
    out0 = {s: 0.0 for s in ("+X", "-X", "+Z", "-Z")}
    # ⛔⛔ `RM.kidan` の `finish` に "-X" を入れない — 仕上げの面は +X/+Z/−Z しか作らず、
    #   しかも "-X" を挙げると平の段積みからも外すので **−X の面が丸ごと抜ける**
    #   (2026-09-26 に背面の斜めのレンダで壇の側面が空いていた)。
    #   ⭕ +X の仕上げ面を別に焼いて X で鏡に写し、−X に据える(巻きは `_flip_faces` で戻す)。
    stones = RM.kidan(hd, hd, out0, dH, name + "_dan", finish=("+X", "+Z", "-Z"))
    keep = [o for o in stones if not re.search(r"_c\d+_x\d+_", o.name)]    # −X の平の段積みを除く
    drop = [o for o in stones if o not in keep]
    for o in drop:
        bpy.data.objects.remove(o, do_unlink=True)
    mirror = RM.kidan(hd, hd, out0, dH, name + "_danw", finish=("+X",))
    for o in mirror:
        if "+X" in o.name:
            o.data.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
            GR._flip_faces(o)
            keep.append(o)
        else:
            bpy.data.objects.remove(o, do_unlink=True)
    stones = keep
    for o in stones:
        o.data.transform(Matrix.Translation((0.0, 0.0, dH))); o.data.update()
    mat = SB.kirishi_material()
    n, T = P["stairN"], P["stairT"]
    rise = dH / float(n)
    sw = P["stairW"] / 2.0
    steps = []
    for i in range(n - 1):                           # 最上段 = 壇の天端(外へは n−1 段)
        z0 = hd + (n - 2 - i) * T - (0.01 if i == n - 2 else 0.0)
        steps.append(SB._stone(-sw, sw, z0, hd + (n - 1 - i) * T, 0.0, (i + 1) * rise, mat,
                               SB.rng_of("yakushi6_dan", i), "%s_ishidan%d" % (name, i),
                               chamfer=SH.KAME_MEJI, tile=SB.KIRISHI_TILE))
    _logical_to_blender(steps)
    stair_out = (n - 1) * T
    # ---- 壇の高欄(4 辺を 90° ずつ回す。正面だけ石段の口を開ける)
    sides = []
    fx = hd - P["koranIn"]
    for q4 in range(4):
        M = VM.Mesh()
        if q4 == 0:
            g = sw + 0.05
            koran_u(M, uv, mw, fx, -fx, -g, dH, P["koranH"], (-g,))
            koran_u(M, uv, mw, fx, g, fx, dH, P["koranH"], (g, fx))
        else:
            koran_u(M, uv, mw, fx, -fx, fx, dH, P["koranH"], (fx,))
        o = M.to_object("%s_dankoran%d" % (name, q4), ms)
        if q4:
            V.rotate_z([o], 90.0 * q4)
        sides.append(o)
    # ---- 堂(6 辺を 60° ずつ回す)。辺 0 = 正面(+Z)
    oe = ap + P["en"]                                # 縁の外の対辺距離
    kinds = {0: "tobira", 1: "mado", 5: "mado"}
    for j in range(6):
        M = VM.Mesh()
        # 柱(b 端 = 頂点)。⭐ 丸柱にして 120° の隅で向きを問わない
        SH.cyl(M, half, ap, fl, keta_top, P["post"], uv["wood"], mw, n=12)
        # 床束(柱の下)・縁束(縁の外の中央と頂点)
        for (uu, vv) in ((half, ap), (0.0, oe - 0.10), (half * (oe - 0.10) / ap, oe - 0.10)):
            B3(M, uu - 0.065, uu + 0.065, vv - 0.065, vv + 0.065, dH, fl - 0.10,
               uv["wood"], mw, grain="h")
        # 壁
        wall_run(M, uv, ms, "u", ap, [-half, half], fl, top, {0: kinds.get(j, "ita")}, +1)
        # 桁
        B3(M, -half - 0.06, half + 0.06, ap - 0.09, ap + 0.09, top, keta_top,
           uv["wood_h"], mw, grain="u")
        # 縁の高欄
        fk = oe - 0.07
        L = fk * math.tan(math.radians(30.0))
        if j == 0:
            g = P["kaiW"] / 2.0 + 0.10
            koran_u(M, uv, mw, fk, -L, -g, fl, P["enKoran"], (-g,))
            koran_u(M, uv, mw, fk, g, L, fl, P["enKoran"], (g, L))
        else:
            koran_u(M, uv, mw, fk, -L, L, fl, P["enKoran"], (L,))
        o = M.to_object("%s_side%d" % (name, j), ms)
        if j:
            V.rotate_z([o], 60.0 * j)
        sides.append(o)
    Mc = VM.Mesh()                                   # 中央の床束
    B3(Mc, -0.07, 0.07, -0.07, 0.07, dH, fl - 0.10, uv["wood"], mw, grain="h")
    Mk = VM.Mesh()                                   # 堂の木階(壇の天端から床へ)
    kai_v = kizahashi(Mk, uv, mw, oe, fl - dH, w=P["kaiW"], n=P["kaiN"])
    ok_ = Mk.to_object(name + "_kizahashi", ms)
    ok_.data.transform(Matrix.Translation((0.0, 0.0, dH))); ok_.data.update()
    sides += [Mc.to_object(name + "_tsuka", ms), ok_]
    # 床(縁込みの六角の板)
    floor = _hex_prism(name + "_yuka", oe / math.cos(math.radians(30.0)), fl - 0.10, fl,
                       ms[0], uv["wood_h"])
    V.dedup_materials()
    o = V.join(sides + [floor, roof, slab, hq] + stones + steps, name)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    info = dict(kind="hogyo6", hu=ap, hv=ap, fl=fl, keta_top=keta_top, off=off,
                roban=roban_top, soffit=chk_soff, top_rays=chk_top, eave=eave,
                y6=dict(hd=hd, dH=dH, ap=ap, R=R, A=A, eaveZ=eaveZ, apex=eaveZ + hR,
                        stair_out=stair_out, kai_v=kai_v, oe=oe))
    print("[yakushi6] %s 壇 %.3f 角・丈 %.2f / 石段 幅 %.2f 出 %.3f / 堂 一辺 %.3f 対角 %.3f 対辺 %.3f"
          " / 床 %.2f / 軒先 %.2f(対辺 %.3f)/ 桁の天端 %.3f / 瓦の頂 %.3f / 露盤の天端 %.3f"
          % (name, 2 * hd, dH, P["stairW"], stair_out, R, 2 * R, 2 * ap, fl, eaveZ, 2 * A,
             keta_top, eaveZ + hR, roban_top))
    return o, info


# ==========================================================================
# 検算
# ==========================================================================
def report(o, info, label):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    print("%s %s W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d 面%d"
          % (label, o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), tris, len(o.data.polygons)))
    if info["kind"] == "kasuga":
        # ⚠ `RM.mune_top_roof` は `roof`/`roof ornaments` しか見ない — 稲荷社は銅板葺なので
        #   材を `Doukawara` に替えて同じ物差し(棟の芯 ±0.6 の帯の最高点)で測る
        idx = [i for i, m in enumerate(o.data.materials)
               if m and m.name.split('.')[0] == "Doukawara"]
        vids = set()
        for pg in o.data.polygons:
            if pg.material_index in idx:
                vids.update(pg.vertices)
        pts = [U[i] for i in vids]
        core = [p[1] for p in pts if abs(p[0]) <= 0.60]
        print("  棟高(地盤 → 箱棟の上端・棟の芯 ±0.6)%.3f / 銅板の最高点 %.3f"
              % (max(core), max(p[1] for p in pts)))
    elif info.get("roban"):
        # ⚠ 方形造には大棟が無い。`RM.mune_top_roof` は中央 ±0.6 の最高点を返すので
        #   **宝珠の頂と同じ値**になる ⇒ 露盤の天端は設計の従属値で別に刷る
        print("  棟高(地盤 → 露盤の天端)%.3f / 宝珠の頂 %.3f / 宝珠の丈 %.3f"
              % (info["roban"], max(ys), max(ys) - info["roban"]))
    else:
        # ⚠⚠ `RM.mune_top_roof` は「**|Z| ≤ 0.6** の帯の最高点」= 大棟が **Z 方向に走る**
        #   御供所・楼門の物差し。ここの堂宇は **大棟が X 方向**(正面が +Z)なので、
        #   そのまま使うと帯が大棟の全長を拾って**鬼の頂と同じ値**になる(飾りの丈 0.000)。
        #   ⇒ 軸を入れ替えて |X| ≤ 0.6 で測る。
        idx = [i for i, m in enumerate(o.data.materials)
               if m and m.name.split('.')[0] in ("roof", "roof ornaments")]
        vids = set()
        for pg in o.data.polygons:
            if pg.material_index in idx:
                vids.update(pg.vertices)
        pts = [U[i] for i in vids]
        # ⚠ 帯を取る軸は**大棟の走る向き**で決まる。御蔵だけ大棟が Z(桁行 5 間)なので
        #   `RM.mune_top_roof` と同じ |Z| ≤ 0.6、ほかは大棟が X なので |X| ≤ 0.6。
        ax = 2 if info["kind"] == "kura" else 0
        core = [p[1] for p in pts if abs(p[ax]) <= 0.60]
        mt, ot = max(core), max(p[1] for p in pts)
        print("  棟高(地盤 → 大棟の上端・棟の中央)%.3f / 鬼の頂 %.3f / 棟飾りの丈 %.3f"
              % (mt, ot, ot - mt))
    bad = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bad else "⛔ %s" % bad))
    return not bad, dict(W=max(xs) - min(xs), H=max(ys) - min(ys), D=max(zs) - min(zs), tris=tris)


def holes(o, info, label, n=200):
    """**真上からの正射影でアルファ 0 の画素を数える**(README「素通しの検査」)。
    ⛔ 背景を派手な色にして数えない(背景は照明でもあるので偽陽性が出る)。
    ここでは BVH の光線で「上から落として何にも当たらない格子点」を数える。"""
    if info.get("top_rays"):
        # ⚠ 六角の堂は壇が下に居るので、join 後の光線は必ず壇に当たる ⇒ join 前に
        #   屋根と野地だけで測った値を使う(`_hex_checks`)
        tot, miss = info["top_rays"]
        print("  検算 真上の光線 %d 本(六角の壁の通り +0.30)— 瓦・野地に当たらない %d %s"
              % (tot, miss, "⭕" if miss == 0 else "⛔"))
        return miss == 0
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    hu, hv = info["hu"], info["hv"]
    x1, z1 = hu + 0.30, hv + 0.30           # 壁の通りの内側だけ見る(軒の外は空で当たり前)
    miss = tot = 0
    for i in range(n + 1):
        for j in range(n + 1):
            X = -x1 + 2 * x1 * i / float(n)
            Z = -z1 + 2 * z1 * j / float(n)
            loc, nrm, idx, dist = bvh.ray_cast(Vector((-X, -Z, 40.0)), Vector((0, 0, -1)), 80.0)
            tot += 1
            if idx is None:
                miss += 1
    print("  検算 真上の光線 %d 本(壁の通り ±0.30)— 空へ抜ける %d %s"
          % (tot, miss, "⭕" if miss == 0 else "⛔"))
    return miss == 0


def soffit_pre(roof, slab, hu, hv, hU, hV, fl, n=44):
    """**軒裏の検算は join の前に、屋根と野地を別々の BVH で突き合わせる。**

    ⛔⛔ **join した 1 本のメッシュで「材が `roof` の面に先に当たったら不良」と数えない。**
      `GK.noji_slab` は**野地の上面にも瓦の材**を貼る意匠(瓦の段の継ぎ目から覗いても
      屋根の色に見せるため)なので、材名では瓦と野地が見分けられない。しかも升は
      非平面なので、BVH が三角に割る向きの都合で**下面を素通りして上面に当たる**ことがあり、
      板が在るのに不良と出た(2026-09-22 に隅の対角線上でちょうど 2 本)。
    ⭕ 見たいのは「**瓦より先に野地が居るか**」だけなので、2 つの BVH の交点の高さを比べる。"""
    dg = bpy.context.evaluated_depsgraph_get()
    br, bs = BVHTree.FromObject(roof, dg), BVHTree.FromObject(slab, dg)
    org_z = fl + 0.5
    bad = miss = tot = 0
    for i in range(n + 1):
        for j in range(n + 1):
            X = -(hU - 0.08) + 2 * (hU - 0.08) * i / float(n)
            Z = -(hV - 0.08) + 2 * (hV - 0.08) * j / float(n)
            if abs(X) < hu + 0.12 and abs(Z) < hv + 0.12:
                continue
            org, dr = Vector((-X, -Z, org_z)), Vector((0, 0, 1))
            lr = br.ray_cast(org, dr, 12.0)[0]
            ls = bs.ray_cast(org, dr, 12.0)[0]
            tot += 1
            if lr is None and ls is None:
                miss += 1; continue                       # 空へ抜ける
            if ls is None or (lr is not None and ls.z > lr.z + 0.001):
                bad += 1                                  # 瓦のほうが先 = 野地が居ない
    return tot, bad, miss


def soffit(o, info, label):
    if info["kind"] in ("umaya", "kura", "kasuga"):
        return True
    tot, bad, miss = info["soffit"]
    ok = bad == 0 and miss == 0
    print("  検算 軒裏 真上の光線 %d: 瓦が野地より先 %d / 空へ抜ける %d %s"
          % (tot, bad, miss, "⭕" if ok else "⛔"))
    return ok


def shots(o, info, key):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    W = max(max(xs) - min(xs), max(zs) - min(zs))
    H = max(ys)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, min(ys) - 0.02))
    out = []

    def one(cam, look, fn, res=(1500, 1050), ortho=None, cull=False):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        # ⛔⛔ **裏面カリングとマゼンタは `V.studio` の後に入れる** — studio は world を
        #   差し替えるので、前に入れると無かったことにされる(memory: magenta-background…)。
        if cull:
            for m in bpy.data.materials:
                m.use_backface_culling = True
            w = bpy.context.scene.world
            w.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 0.0, 1.0, 1.0)
        f = os.path.join(SHOT, "sanno_do_%s_%s.png" % (key, fn))
        V.render(f); out.append(f)
    d = W * 1.55 + 3.0
    # Blender = (−X, −Z, Y)
    one((-d, -d, H * 0.95), (0.0, 0.0, H * 0.45), "01_front_ne")      # 正面(+Z)側の斜め
    one((d, d * 0.9, H * 0.9), (0.0, 0.0, H * 0.45), "02_back_sw")    # 背面の斜め
    one((0.0, -(W * 1.4 + 6.0), H * 0.5), (0.0, 0.0, H * 0.5), "03_front_elev", ortho=W * 1.9)
    one((0.02, 0.0, H * 3.2), (0.0, 0.0, H * 0.5), "04_top", ortho=W * 1.9)   # 棟飾りの向き
    one((-W * 0.55, -(W * 0.85 + 2.2), H * 1.35), (0.0, -W * 0.15, H * 0.92), "05_mune",
        res=(1400, 1050))                                              # 棟と鬼の近景
    # ⭐ **裏面カリング + マゼンタの背景**で巻き順の裏返りと穴を同時に見る。
    #   ⚠ 鬼・棟の駒は行列で置くので**鏡像に焼かれて巻きが裏返る**前歴がある
    #   (EDO-0375 / EDO-0393)。join した後は Blender も法線を補正しないので、ここで出る。
    one((-d * 0.75, -d * 0.75, H * 1.25), (0.0, 0.0, H * 0.62), "06_cull", cull=True)
    return out


# ==========================================================================
def build_one(key, do_render, do_export, allow):
    V.reset()
    if key == "hogyo":
        o, info = do("hogyo", 3, 3)
    elif key == "irimoya3":
        o, info = do("irimoya", 3, 3)
    elif key == "irimoya4":
        o, info = do("irimoya", 4, 4)
    elif key == "inari":
        o, info = inari()
    elif key == "umaya":
        o, info = umaya()
    # ---- 2026-09-23 EDO-0395 施主裁定B: 御宮絵図の朱矩形の大小比の寸法【P 比・U 錨】
    elif key == "yakushi":                       # 薬師堂 宝形 4.5×4.5
        o, info = do("hogyo", 4.5, 4.5)
    elif key == "koshin":                        # 庚申堂 宝形 2×2
        o, info = do("hogyo", 2, 2)
    elif key == "kannon":                        # 観音堂 宝形 2.5×2.5
        o, info = do("hogyo", 2.5, 2.5)
    elif key == "sono5":                         # 附属堂 其五 入母屋 5.5(間口)×3.5(奥行)
        o, info = do("irimoya", 5.5, 3.5)
    elif key == "sono8":                         # 附属堂 其八(コマ堂)入母屋 5×5 + 向拝
        o, info = do("irimoya", 5, 5, kohai=True)
    elif key == "umaya32":                       # 御厩 切妻 3×2
        o, info = umaya(3, 2)
    elif key == "kura":
        o, info = kura()
    elif key == "yakushi6":                      # 薬師堂 六角の宝形 + 4.5間角の石の壇(EDO-0438)
        o, info = yakushi6()
    else:
        raise SystemExit("[do] 知らない型: %s" % key)
    ok, meas = report(o, info, "[%s]" % key)
    if info.get("us"):
        bu = [round((b - a) / K, 3) for a, b in zip(info["us"], info["us"][1:])]
        bv = [round((b - a) / K, 3) for a, b in zip(info["vs"], info["vs"][1:])]
        print("  柱芯 X %.3f × Z %.3f / 柱割[間] X %s / Z %s"
              % (info["us"][-1] - info["us"][0], info["vs"][-1] - info["vs"][0], bu, bv))
    hok = holes(o, info, key)
    sok = soffit(o, info, key)
    files = shots(o, info, key) if do_render else []
    for f in files:
        print("RENDER " + f)
    if not (ok and hok and sok) and not allow:
        raise SystemExit("[do] ⛔ %s の検算に落ちた" % key)
    if do_export:
        o.location = (0.0, 0.0, 0.0)
        path = os.path.join(OUT, o.name + ".fbx")
        V.export_fbx([o], path)
        print("[do] 書き出し %s" % path)
    return meas


ALL = ("hogyo", "irimoya3", "irimoya4", "inari", "umaya", "kura")
# 2026-09-23 EDO-0395(絵図の比の寸法)。⚠ 型を省いて回すと ALL だけ(旧 10 棟)を焼き直す
HIHI = ("yakushi", "koshin", "kannon", "sono5", "sono8", "umaya32")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    keys = [a for a in argv if not a.startswith("--")] or list(ALL)
    if keys == ["hihi"]:
        keys = list(HIHI)
    do_render = "--render" in argv
    do_export = "--no-export" not in argv
    allow = "--allow" in argv
    for k in keys:
        build_one(k, do_render, do_export, allow)


if __name__ == "__main__":
    main()
