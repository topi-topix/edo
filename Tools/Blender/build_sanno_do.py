# -*- coding: utf-8 -*-
"""山王権現社の**小さな棟 10 棟** — 堂宇(宝形・入母屋)・稲荷社・御厩・御蔵。

    blender --background --python Tools/Blender/build_sanno_do.py -- [型...] [--render] [--no-export]
    (型を省くと全部。hogyo / irimoya3 / irimoya4 / inari / umaya / kura)

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
import bpy, bmesh, sys, os, math
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
def umaya(name="Sanno_Umaya_4x3ken_7272x5454"):
    """**御厩 4間(u)× 3間(v)**。岡部の吹き放ちの厩 `build_okabe_fuzokuya.umaya` を
    梁間3間・桁行4間で呼ぶ(= 類型の `Typ_Umaya` と同じ型)。

    ⚠ **ローカル +X = 桁行(4間・棟の走る向き)= 指図の u** / **+Z = 開口(吹き放ち)面**。
    ⚠ 軒 2.55 / 馬房前の半高壁 1.15 / 軒の出 0.70 は生成器の断り書きどおりの組
      (吹き放ちの帯 0.93m を保つ)。⛔ 軒だけ下げない。
    ⭐ 屋根はキットの `roof` = 山王の「在庫の本瓦」(楼門・御供所と同じ材)。
      ⇒ 指図 bom 行34 の**本瓦葺**を満たす。"""
    o = OF.umaya(uKen=3, vKen=4, name=name, eaveH=2.55, frontH=1.15, noki=0.70)
    if isinstance(o, tuple):
        o = o[0]
    return o, dict(kind="umaya", hu=4 * K / 2.0, hv=3 * K / 2.0, fl=0.0)


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
    elif key == "kura":
        o, info = kura()
    else:
        raise SystemExit("[do] 知らない型: %s" % key)
    ok, meas = report(o, info, "[%s]" % key)
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    keys = [a for a in argv if not a.startswith("--")] or list(ALL)
    do_render = "--render" in argv
    do_export = "--no-export" not in argv
    allow = "--allow" in argv
    for k in keys:
        build_one(k, do_render, do_export, allow)


if __name__ == "__main__":
    main()
