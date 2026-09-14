# -*- coding: utf-8 -*-
"""山王権現社(日枝神社)の**社殿 — 権現造の一続き**を起こす。

    blender --background --python Tools/Blender/build_sanno_shaden.py -- all [--render]
    blender --background --python Tools/Blender/build_sanno_shaden.py -- honden|tsukuriai|heiden|haiden|kohai|kizahashi [--render]
    blender --background --python Tools/Blender/build_sanno_shaden.py -- render      # 組み上がりの検証レンダだけ
    blender --background --python Tools/Blender/build_sanno_shaden.py -- selftest    # EDO-0161 の検算の陰性試験

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指図 `docs/Sashizu/sanno_sashizu.json` の `bom`「本殿・幣殿・拝殿(権現造)」が **在庫「無い」・
優先1**。現況は Village Kit の民家を代用していて ⛔ **神社に見えない**(指図の註そのまま)。

━━━ 何を起こすか(指図 `munes` が正典。⛔ ここに区画の数を書かない)━━━━━━━━━━
東から西へ **向拝 → 拝殿 → 幣殿 → 作り合い → 本殿**。⭐ **正面は東。**
**1棟1FBX**にし、各 FBX の**ピボット = その棟の区画 (u0,v0,du,dv) の中心・地盤レベル**にした。
⇒ 実装は `munes` の矩形の中心へ **yaw 0 のまま**置ける(下の「向きの規約」)。
`kaidans[向拝の階]`(木階三級)だけは `munes` ではなく `kaidans` の a/b から置く。

━━━ 向きの規約(EDO-0161)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔⛔ **`Unity X = −(Blender X)` / `Unity Z = −(Blender Y)` / `Unity Y = Blender Z`。**
非対称な部材(**向拝は東を向く**・**千鳥破風は東の流れに載る**)は、据え付け側が 180° を
吸収していても**立面でも数値QAでも素通りする**。⇒ この本は次の二段で潰す:

  ⭕ **① 論理座標で組む** — `(u=東, v=北, h=上)` の右手系。Blender へは
     `BX(u,v) = (-u, -v)` / z=h で落とす。この写像は **Rz(180°)= 行列式 +1 の回転**なので
     巻き順も法線も動かない。⇒ 書き出し後の **Unity ローカル = (u, h, v)**。
     ⭐ つまり **Unity +X = 東 = 社殿の正面**、**Unity +Z = 北**。⭕ **yaw は 0。**
     ⚠ `vkmesh.Mesh` の論理は (走り,高さ,厚み) で `to_object` が厚みを反転するので、
       `q(u,v,h) = (-u, h, v)` を通す(これも行列式 +1)。
  ⭕ **② 焼いた直後に部材の側で検算する**(`check_*`)。⛔ 期待値は引数からではなく
     **メッシュそのものから**立てる。陰性試験は `-- selftest`(X を鏡映すると必ず止まる)。

━━━ 材 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
木部・壁・建具は Village Kit の材質**名**をそのまま運ぶ: `wood` / `wall C` / `door wall`。
石(**石造亀腹・礎盤**)は `M_FJG_Rock_001` — 同じ山王の段石・切石橋・立石と同じ**加工石**の材。
⇒ Unity 側の Search & Remap が既存 `.mat` を当てる。
⛔⛔ **`Foundation_A_01` は使わない**(2026-09-09 に落とした)。あのアトラスは 2048² 全面が
  **丸い野面石の乱積み**で、石造亀腹【A 加藤2018 6-1】にも礎盤にも当たらない(考証19巡目 中6)。
⭐ **屋根だけ例外** — `Doukawara`(緑青の銅瓦)を **1枚だけ**新造した。理由と確度は
  下の `DOU_NAME` の章。⛔ 【A】【S】を名乗らせない(色は【U 普請奉行の裁定 2026-09-09】)。
⭕ `Edo/山王社/新造部材のマテリアルをremap` の `donorDirs` は **既に4つとも足りている**
  (`Waldemarst/FreeJapaneseGarden/Materials` = 岩 / `Japanese Village Kit/Materials` = 木・壁・建具 /
  `Edo/Materials/Sanno` = 銅瓦)。`modelDirs` にも `Assets/Edo/Models/Sanno` が入っている。
  ⇒ **足す行は無い**(2026-09-09 に確かめた)。

⛔⛔ **未決(普請奉行へ返す)**:
  ・**朱塗か素木か**。山王権現社は朱塗の類型だが、在庫に朱の材が無い。いまは `wood`(素木)。
    ⚠ `Assets/Edo/Materials/Shu_Torii.mat`(鳥居の朱)を借りる手はある。

━━━ 寸法の出所 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・**平面(間数)= 指図 `munes` の du/dv**。⛔ ここに書かない — `rects()` が毎回読む。
・**床高 = 指図 `const.shadenFloor`**。⭐ **本殿だけ `const.shadenHondenFloor`**
  (石造亀腹に土台立て【A 加藤2018 6-1】)。⛔⛔ **指図にまだこの鍵が無い** —
  `rects()` が暫定で `shadenFloor + 0.90` を入れ、毎回そう名乗る。指図方が足すこと。
・**屋根の勾配・軒の出 = 根津神社の実測【P/A】**(下の `Sori` の章)。
  ⛔ 瓦モジュールの 5.5寸(`RATIO`)は屋根の勾配ではない — あれは在庫の都合。
・⭐ **棟高 `h` は追わない。** 指図の `munes[*].h`(10.0 / 11.0)は【U 類型の中央】で
  史料ではない(考証18巡目)。⛔ 史料でない h に実物を照らして「差 1.76m」と報告し続ける
  のは、無い基準を基準にしている形。⇒ **棟高は勾配・軒高・軒の出から出る従属値**として
  建て、出た値を報告する。指図の側は普請奉行が直す。
・柱高・組物の丈は【U 設計値】のまま(考証18巡目で ⛔ とされていない)。

━━━ 落とし穴 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・⚠ `export_fbx` を通した後は bbox が 0 に潰れる。**測るのもレンダも書き出しの前に。**
・⚠ 同じ FBX を2度読むと `wood.001` ができる。join の前に `V.dedup_materials()`。
・⚠ 瓦場のクリップは平面 bisect(`GR.clip_convex`)。⛔ ブーリアンは瓦場に効かない。
・⚠ **反りは走り(u)の関数の鉛直ずらしで入れる**(`sori_shear`)。⭐ **軒反り(隅の
  跳ね上がり)は水平位置 (x,y) の関数**で入れる(`Nokizori`)。⭕ どちらも
  **位置の連続関数**なので継ぎ目は開かない — 隣り合う瓦は同じ (x,y) の頂点を共有する。
  ⛔⛔ 破綻するのは **走り方向の勾配が折り返す**とき(2026-09-09 の軒唐破風の破綻は
  A/dk = 0.72 が瓦の勾配 0.5456 を超えたもので、桁行の関数だからではない)。
  ⇒ `Nokizori` は隅の傾き `A·2/L < K_EAVE` を構築時にアサートする。
  ⛔ 逆に **段(不連続)で起こしてはいけない** — 桁行の重ねはゼロ(`MOD_LEN` = 瓦の実長)。
・⚠ 反った屋根面は **凸**(奥ほど急)。⇒ 垂木・海老虹梁を軒先と奥の2点で結ぶと弦が
  曲線の上を通り、**木の棒が瓦を突き抜けて屋根の上に並ぶ**。必ず折れ線にする。
"""
import bpy, bmesh, sys, os, math, json, hashlib
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
# ⭐ `SANNO_SASHIZU=<path>` で読む指図を差し替えられる(読むだけ)。⚠ 指図の改訂が worktree にだけあり、
#   Blender は Assets の来る main でしか回らないとき(2026-09-14 裁定C の明治16年寸法)に使う。
SASHIZU = (os.environ.get("SANNO_SASHIZU")
           or os.path.join(V.REPO, "docs", "Sashizu", "sanno_sashizu.json"))

RATIO = GR.RATIO            # 0.5456 = 瓦モジュール **自身**の勾配。反りを載せる基準面でしかない
                            # ⛔ これを屋根の勾配として使わない(下の `Sori` が正典)


# ==========================================================================
# 反り(そり)— ⭐ 屋根面の勾配を棟寄り 8寸 → 軒先 4寸へ連続的に緩める
# ==========================================================================
# 【なぜ】考証18巡目の判定: **5.5寸という縛りは史料ではなく在庫の瓦モジュール由来**で
#   史実側から擁護できない。⭐ **より重い誤りは「反りが皆無」であること。**
#   ・焼失前写真【S】`[東京府史蹟]` NDL pid 1181687 コマ19(拝殿正面外観)—
#     屋根は強い反りを持ち隅が跳ね上がる。棟から軒先までが直線ではない。
#   ・『江戸名所図会』【S 定性のみ】— 稜が明らかに凹で隅が跳ね上がる。
#     ⛔ この図から数値は取らない(鳥瞰の誇張・省略。規則14)。
# 【数値の出所】根津神社 本殿の実測断面【P 考証方の実測 / 図は A】
#   `[加藤重枝2018]` Fig.7(=『国宝・重要文化財(建造物)実測図集』東京都(その1)
#   図面4・10 の転載)を 600dpi 展開し、寸法線 3568mm を尺度にして計測:
#     ・棟寄りの勾配 0.78〜0.83(約8寸)/ 軒先で反って 約0.39(4寸)まで緩む
#     ・棟から軒先までの平均 rise/half-span = 0.667(半スパン約4.81m・棟高さ約3.21m)
#     ・軒の出 = **身舎の半スパンの約 0.63**(→ 半スパン全長 = 身舎半 ×1.63 = 4.81 と閉じる)
#   根津は宝永3年・現存重文・**幣殿型権現造**・本殿は方三間入母屋・銅瓦葺・拝殿は
#   桁行七間梁間三間で、日枝と「一対」の作例。
# ⛔ **垂木を一軒→二軒にしない** — 東照宮系では二軒繁垂木が通例だが日枝について
#   書いた史料は無い【?】。一般類型で埋めない(考証18巡目)。
K_RIDGE = 0.805     # 棟寄りの勾配【P 根津 0.78〜0.83】
K_EAVE = 0.390      # 軒先の勾配【P 根津 約0.39】
SORI_P = 2.0        # k(t) = K_RIDGE + (K_EAVE−K_RIDGE)·t^2 (t = 棟からの水平比)
                    # ⇒ 平均 = K_RIDGE − (K_RIDGE−K_EAVE)/3 = 0.6667(根津の実測 0.667)
EAVE_RATIO = 0.63   # 軒の出 / 身舎の半スパン【P 根津】


FLAT_TEST = False   # ⛔ 陰性試験専用のスイッチ(`-- selftest`)。⛔ 本番で立てない


def _clamp(x, a, b):
    return a if x < a else (b if x > b else x)


class Sori:
    """軒先からの水平距離 d に対する屋根面の高さ z(d)。d=0 が軒先・d=half が棟。

    ⭐ **軒先で緩く棟寄りで急**にすると稜が凹になり、入母屋の隅棟は自然に跳ね上がる
      (隅棟は「両流れの高さが等しい点の軌跡」なので、両面に同じ z(d) を入れれば
      平面上の位置は動かず、高さだけが反りに乗る)。
    ⛔ 直線(z = d·RATIO)へ戻さない — それが考証18巡目の最重の指摘。"""

    def __init__(self, half, mean=None, kr=K_RIDGE, ke=K_EAVE, p=SORI_P):
        if FLAT_TEST:            # ⛔ `-- selftest` 専用。反りを殺して検算が鳴るか見る
            kr = ke = RATIO
            mean = None
        self.half = float(half)
        base = kr - (kr - ke) / (p + 1.0)         # 素の平均 rise/half-span
        s = 1.0 if mean is None else float(mean) / base
        self.kr, self.ke, self.p = kr * s, ke * s, float(p)

    def k(self, d):
        """局所勾配(rise/run)。"""
        t = 1.0 - _clamp(d / self.half, 0.0, 1.0)
        return self.kr + (self.ke - self.kr) * (t ** self.p)

    def z(self, d):
        """軒先からの高さ。⚠ d<0 / d>half は接線で外挿する(瓦場の切り代が要る)。"""
        if d < 0.0:
            return d * self.k(0.0)
        if d > self.half:
            return self.z(self.half) + (d - self.half) * self.k(self.half)
        x = d / self.half
        return self.half * (self.kr * x - (self.kr - self.ke) / (self.p + 1.0)
                            * (1.0 - (1.0 - x) ** (self.p + 1.0)))

    def mean(self):
        return self.z(self.half) / self.half

    def d_of_z(self, zz):
        """z の逆関数(二分法)。千鳥破風の谷を主屋根の**曲面**と交わらせるのに要る。"""
        lo, hi = 0.0, self.half
        if zz >= self.z(hi):
            return hi
        for _ in range(60):
            mid = (lo + hi) / 2.0
            if self.z(mid) < zz:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0


def sori_shear(obj, eave_xy, up_xy, sori):
    """瓦場を反りに追随させる。**鉛直方向のずらしだけ**で、走りの関数。

    引数は **Blender の平面座標**(軒先線上の1点 `eave_xy` と、上り勾配の単位方向 `up_xy`)。
    ⚠ 論理 (u,v) で組んだ面に掛けるときは呼ぶ側で `BX()` を通しておくこと。

    ⭕ なぜ千切れないか: `_tile_field_fast` の瓦は流れ方向に 0.31m 重ねてある。
      ずらし量が **走り座標 d のみの関数**なので、重なった上下の瓦は同じ d で同じだけ
      動く ⇒ 重ね代が保たれたまま面全体が反る。
    ⚠ **桁行(v)の関数でも、位置の連続関数なら継ぎ目は開かない**(2026-09-09 に是正)。
      唐破風(`bend`)で瓦場が破れたのは v の関数だからではなく、**走り方向の勾配が
      折り返した**から(A/dk = 0.72 > 瓦の勾配 0.5456)。⇒ 見るべきは軸ではなく**傾き**。
      ⛔ ただし **段(不連続)は必ず穴が開く** — 桁行の重ねはゼロ(`MOD_LEN` = 瓦の実長)。
    ⚠ 切り取り(`clip_convex`)は**鉛直面**の bisect なので、切る前でも後でも結果は同じ。
      ここでは切った後に掛ける(GR 側に手を入れないため)。"""
    ox, oy = eave_xy
    dx, dy = up_xy
    me = obj.data
    for vt in me.vertices:
        d = (vt.co.x - ox) * dx + (vt.co.y - oy) * dy
        vt.co.z += sori.z(d) - d * RATIO
    me.update()
    return obj


# ==========================================================================
# 軒反り(のきぞり)— ⭐ **隅で軒先の稜線を持ち上げる**
# ==========================================================================
# 【なぜ要るか】`Sori` は**流れ方向**の照りしか入れない。⇒ 軒先の稜線は全幅で水平のまま
#   だった(2026-09-09 考証19巡目 中4 の実測: 東立面 1800px で 左端519 / 中央515 /
#   右端520 = 振れ 8px)。焼失前写真【S】・名所図会【S】が一致して示すのは
#   **「強い反りと跳ね上がる隅」**という定性で、隅が上がらない屋根は写真と違う。
# 【⛔ 量の典拠は無い】⚠⚠ **軒反りの量は誰も測っていない**【?】。考証方が測ったのは
#   根津 Fig.7 の**断面**だけで、断面からは隅の跳ね上がりは取れない。
#   ⇒ 下の `NOKI_A` / `NOKI_L` は **【U 設計値】**。⛔ 【A】【S】を名乗らせない。
# 【作り】⭐ **水平位置 (x,y) だけの関数**として鉛直に持ち上げる:
#     dz(x,y) = A · φ(dx) · φ(dy)      φ(t) = (1 − t/L)²(t ≥ L で 0)
#     dx = 東西の軒先線までの最短距離 / dy = 南北の軒先線までの最短距離
#   ⭕ **なぜ瓦場が千切れないか**(前回の知見がここに効く):
#     ① 隣り合う瓦は **同じ (x,y) の頂点を共有**するので、位置だけの連続関数で動かす限り
#        どの継ぎ目も開かない(流れ方向の重ね 0.31m も、桁行の突き付けも保たれる)。
#        ⛔ **段(不連続)で起こすと桁行に重ね代が無い**(`MOD_LEN` 2.004 = 瓦の実長で、
#        横の重ねはゼロ)ので、段の高さぶんそのまま**素通しの隙が開く**。⇒ 段にしない。
#     ② 破綻するのは **走り方向の勾配が負に折り返す**とき(2026-09-09 の軒唐破風の
#        破綻はこれ。A/dk = 0.72 が瓦の勾配 0.5456 を超えて折れた)。⇒ 隅での走り方向の
#        傾き `A·2/L` を軒先の勾配 `K_EAVE` より小さく取る(下でアサートする)。
#     ③ 同じ関数を**屋根の全部材**(瓦場・隅棟・袖瓦・破風・鬼)へ後から一括で掛けるので、
#        部材どうしがズレようがない。
#   ⭕ 隅で dx=dy=0 ⇒ **両方の流れの軒先が同じだけ上がる** ⇒ 隅棟の根も同じだけ上がる。
NOKI_A = 0.40       # 隅の持ち上げ[m]【U 設計値。⛔ 典拠なし】
NOKI_L = 4.00       # 効く長さ[m]。隅から内へこの距離で 0 に戻る【U 設計値】
FLAT_NOKI = False   # ⛔ 陰性試験専用(`-- selftest`)。⛔ 本番で立てない


class Nokizori:
    """屋根の平面 (x,y) → 隅で持ち上げる量 dz。**軒先の矩形**を渡して作る。"""

    def __init__(self, x0, x1, y0, y1, amp=NOKI_A, L=NOKI_L):
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.amp = 0.0 if FLAT_NOKI else float(amp)
        self.L = float(L)
        # ⛔ 走り方向の勾配が折り返すと瓦場が千切れる(上の②)。隅での傾きは A·2/L。
        if self.amp * 2.0 / self.L >= K_EAVE:
            raise SystemExit("[nokizori] ⛔ 隅の傾き %.3f が軒先の勾配 %.3f 以上 "
                             "— 瓦場が折り返して千切れる。A を下げるか L を伸ばすこと"
                             % (self.amp * 2.0 / self.L, K_EAVE))

    def phi(self, t):
        if t >= self.L:
            return 0.0
        s = 1.0 - max(0.0, t) / self.L
        return s * s

    def __call__(self, x, y):
        if self.amp <= 0.0:
            return 0.0
        dx = min(x - self.x0, self.x1 - x)
        dy = min(y - self.y0, self.y1 - y)
        return self.amp * self.phi(dx) * self.phi(dy)


def nokizori_apply(obj, nz):
    """屋根1体の全頂点へ軒反りを掛ける。⛔ 部材ごとに違う関数を掛けない。"""
    if nz is None:
        return obj
    me = obj.data
    for vt in me.vertices:
        vt.co.z += nz(vt.co.x, vt.co.y)
    me.update()
    return obj


def ridge_curve(pts, name, w, h):
    """折れ線に沿って棟モジュールを継ぐ(反った隅棟・袖瓦に使う)。"""
    out = []
    for i in range(len(pts) - 1):
        out += GR.ridge(pts[i], pts[i + 1], "%s%d" % (name, i), w=w, h=h)
    return out


# ==========================================================================
# 銅瓦葺の材 — ⚠ 「新規マテリアルを作らない」規約の **明示的な例外**(1枚だけ)
# ==========================================================================
# 【なぜ例外か】指定説明は本殿・幣殿・拝殿(および中門・透塀)とも **銅瓦葺**【S
#   国宝建造物目録1941】。これは当指図が【S】で持つ**唯一の材質情報**であり、在庫の
#   目録に copper / verdigris / patina / bronze / 緑青 は **0件**(在庫方 確認済)。
#   灰の本瓦で焼くと ①附属堂10棟(桟瓦【U】)と同色になり格差が絵に出ない
#   ②武家屋敷・町家と同色で山上の社殿群が麓と同材に見える ⇒ 考証18巡目 ⛔不可。
# 【形は現状のまま正しい】焼失前写真の軒先に**軒丸瓦の列が明瞭**で瓦割りは本瓦形【S】。
#   銅瓦は本瓦を銅板で模したもの。⇒ **誤っているのは材と色だけ**。
# 【色の確度】⚠⚠ **【U 普請奉行の裁定 2026-09-09】**
#   ・史料は色を一言も言わない【?】。
#   ・焼失前写真の測光【P 考証方】: 屋根 L中央値 155 / 柱・壁 96〜109 / 玉砂利 161 /
#     空 196 ⇒ 屋根は材木よりはっきり明るい ⇒ ⛔ **日光型の黒漆塗ではない**【U 推論】。
#   ・万治2年(1659)から安政3年(1856)まで **197年**。屋外の銅は数十年で緑青【B 一般知】。
#   ⇒ 緑青(青緑)で焼く。⛔ この色に【A】や【S】を名乗らせない。
# 【作り】⭐ **1枚だけ**。中門・透塀・回廊も同じ材を使い回す。テクスチャは在庫の瓦の
#   **法線・粗さを流用し、色だけ差し替える**(Unity 側 `.mat` も同じ作り)。
DOU_NAME = "Doukawara"      # 銅瓦(緑青)。⚠ Unity 側 `Assets/Edo/Materials/Sanno/Doukawara.mat`
# 緑青の albedo(**線形**)。sRGB (0.343, 0.500, 0.416) = **H 148° / S 31% / V 50%**。
# ⛔⛔ **測光の比を較正値として引かない**(2026-09-09 考証19巡目 中7 で是正):
#   焼失前写真の測光の元は大正8年の**網版**で、⚠ **原板の感材が不明**【?】。
#   オルソクロマチック系なら青緑は明るく褐色は暗く写るので、**画像上の比 1.52 を
#   アルベドの比へそのまま移せない**。⇒ 測光が支えるのは「屋根は**材木より明るい**」という
#   **向きだけ**で(この向きは感材によらず立つ ⇒ ⛔ 日光型の黒漆ではない【U 推論】)、
#   **比の大きさは当方が選んだ【U 設計値】**。数は動かしていない(現レンダの実測比 1.56)。
# ⛔ 色相は 2026-09-09 に **172〜178° → 158〜165°** へ振った(庭方18巡目 決6):
#   緑青(塩基性炭酸銅)の色域は **155〜165°** が本筋で、175° は亜鉛引き・酸化青銅の側。
#   夏の暖かい葉色(H 90〜110°)の中に置くと**冷たい別物**に見えていた。
#   ⚠ **振ったのは色相だけ** — 明度(V 48〜58%)・彩度(S 20〜28%)は庭方が ⭕ とした値。
#   ⚠ アルベドの H は **148°** で、レンダの H(158〜165°)より **13° 低い** —
#     環境光の青みが乗るぶんを見込んで**手前へ振ってある**(実測で合わせた。
#     ⛔ アルベドの数をそのまま「屋根の色相」と読まない)。
ROKUSHO_LIN = (0.0964, 0.2140, 0.1446)
COPPER_FROM = ("roof", "roof ornaments", "roof ornament")


def doukawara():
    """緑青の銅瓦材。法線は在庫の `roof_Normal.png` を流用し、色だけ差し替える。"""
    m = bpy.data.materials.get(DOU_NAME)
    if m:
        return m
    m = bpy.data.materials.new(DOU_NAME)
    m.use_nodes = True
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b:
        b.inputs['Base Color'].default_value = ROKUSHO_LIN + (1.0,)
        b.inputs['Roughness'].default_value = 0.66      # 緑青は艶が引けている
        # ⛔ 金属度を上げない — 鏡面が**空の色**を拾って屋根の色相が青へ流れる
        #   (2026-09-09: 0.15 でレンダの H が albedo より 14° 青側へ寄っていた)
        b.inputs['Metallic'].default_value = 0.04
        # ⭐ 在庫の瓦 albedo の **明暗の斑だけ**を借りて色に掛ける。⛔ 単色で焼かない —
        #   一枚一枚の焼きムラが消えて **プラスチックの板**に見える(検証レンダで実見)。
        alb = os.path.join(V.TEX, "roof_AlbedoTransparency.png")
        if os.path.exists(alb):
            ai = nt.nodes.new('ShaderNodeTexImage')
            ai.image = bpy.data.images.load(alb, check_existing=True)
            ai.image.colorspace_settings.name = 'Non-Color'   # 生の明暗を斑として使う
            ai.location = (-900, 400)
            bw = nt.nodes.new('ShaderNodeRGBToBW'); bw.location = (-680, 400)
            mr = nt.nodes.new('ShaderNodeMapRange'); mr.location = (-500, 400)
            mr.inputs['From Min'].default_value = 0.14
            mr.inputs['From Max'].default_value = 0.46
            mr.inputs['To Min'].default_value = 0.72
            mr.inputs['To Max'].default_value = 1.26
            mr.clamp = True
            mix = nt.nodes.new('ShaderNodeMixRGB'); mix.location = (-300, 400)
            mix.blend_type = 'MULTIPLY'
            mix.inputs['Fac'].default_value = 1.0
            mix.inputs['Color1'].default_value = ROKUSHO_LIN + (1.0,)
            nt.links.new(ai.outputs['Color'], bw.inputs['Color'])
            nt.links.new(bw.outputs['Val'], mr.inputs['Value'])
            nt.links.new(mr.outputs['Result'], mix.inputs['Color2'])
            nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])
        nrm = os.path.join(V.TEX, "roof_Normal.png")
        if os.path.exists(nrm):
            ni = nt.nodes.new('ShaderNodeTexImage')
            ni.image = bpy.data.images.load(nrm, check_existing=True)
            ni.image.colorspace_settings.name = 'Non-Color'
            ni.location = (-600, -100)
            nm = nt.nodes.new('ShaderNodeNormalMap')
            nm.location = (-300, -100)
            nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def to_copper(o):
    """瓦・棟・鬼の材(`roof` / `roof ornaments`)を **銅瓦1枚**へ寄せる。

    ⛔ スロットを上書きするだけにしない — 同名スロットが2つ残ると FBX が
      `Doukawara` と `Doukawara 1` を吐いて remap が片方に当たらない。"""
    me = o.data
    if not me.materials:
        return o
    dou = doukawara()
    hit = [i for i, m in enumerate(me.materials)
           if m and m.name.split('.')[0] in COPPER_FROM]
    if not hit:
        return o
    for i in hit:
        me.materials[i] = dou
    keep = hit[0]
    dup = set(hit[1:])
    if dup:
        for pg in me.polygons:
            if pg.material_index in dup:
                pg.material_index = keep
    me.update()
    # ⚠⚠ `me.materials.clear()` で作り直すと **面の material_index が 0 に潰れる**
    #   (2026-09-09 に実見。舞良戸が全部 `wood` になって `check_front_east` が鳴った)。
    #   ⇒ 空になったスロットは **オペレータに畳ませる**(索引を正しく振り直してくれる)。
    if dup:
        V.sel([o])
        bpy.ops.object.material_slot_remove_unused()
    return o


# ==========================================================================
# 指図を読む(⛔ 区画と床高の数をここに書かない)
# ==========================================================================
def sashizu():
    with open(SASHIZU) as f:
        return json.load(f)


def const_num(d, key):
    """`const` の値を数で返す。⭐ **式の文字列**("shadenFloor + shadenHondenStepM")を許す。

    ⚠ 指図方が 2026-09-09 に `shadenHondenFloor` を**従属値の式**へ書き換えた(規則4
      「同じ量に二つの数を作らない」)。⛔ `float()` で読むと落ちる — 実際に落ちた。
    ⛔ `eval` は使わない(指図は人が書く JSON で、任意の式を通す入口にしない)。
      ⭕ **`+` / `-` で繋いだ const の鍵と数のみ**を解く。"""
    v = d["const"][key]
    if isinstance(v, (int, float)):
        return float(v)
    tot, sign, tok = 0.0, 1.0, ""
    for ch in str(v).replace("-", " - ").replace("+", " + ").split():
        if ch in ("+", "-"):
            if tok:
                tot += sign * _term(d, tok); tok = ""
            sign = 1.0 if ch == "+" else -1.0
        else:
            tok = ch
    if tok:
        tot += sign * _term(d, tok)
    return tot


def _term(d, tok):
    try:
        return float(tok)
    except ValueError:
        pass
    if tok not in d["const"]:
        raise SystemExit("[shaden] ⛔ 指図 const に鍵が無い: %s" % tok)
    return const_num(d, tok)


def rects():
    """`munes` から社殿5棟の (u0,v0,du,dv) を間で返す。"""
    d = sashizu()
    K = float(d["const"]["ken"])
    want = {"本殿": "honden", "作り合い": "tsukuriai", "幣殿": "heiden",
            "拝殿": "haiden", "向拝": "kohai"}
    out = {}
    for m in d["munes"]:
        k = want.get(m["name"])
        if k:
            # ⭐ **柱間の引数**(2026-09-14 裁定C)。間数は `munes[].bays`、柱間は外形 ÷ 間数の従属値。
            #   ⛔ 間数を `int(du)` で出さない — 外形が実測[間]になった今は 5.0605 → 5 間に化ける。
            #   `bays` の無い旧い指図だけ du/dv を間数と読む(柱間 = 1間 ⇒ 旧名のまま焼ける)。
            bays = m.get("bays") or {}
            nu = int(bays["du"]) if bays.get("du") else int(round(float(m["du"])))
            nv = int(bays["dv"]) if bays.get("dv") else int(round(float(m["dv"])))
            pu, pv = float(m["du"]) * K / nu, float(m["dv"]) * K / nv
            out[k] = dict(u0=float(m["u0"]), v0=float(m["v0"]),
                          du=float(m["du"]), dv=float(m["dv"]),
                          nu=nu, nv=nv, pu=pu, pv=pv,
                          legacy=(abs(pu - K) < 1e-6 and abs(pv - K) < 1e-6),
                          h=(float(m["h"]) if "h" in m else None), name=m["name"])
    missing = [n for n, k in want.items() if k not in out]
    if missing:
        raise SystemExit("[shaden] 指図に棟が無い: %s" % missing)
    out["_ken"] = K
    out["_floor"] = float(d["const"]["shadenFloor"])
    # ⭐ **本殿の床だけ一段高い。**⛔ 部材方の意匠ではなく **史料で決まっている**:
    #   日枝の本殿は「**石造亀腹に土台立てとし、縁を腰組で支持する**」【A 加藤2018 6-1】。
    #   石造亀腹は日光・上野・紅葉山東照宮に用いられ、承応期以前の幣殿型権現造(切石積+
    #   漆喰亀腹)には見られない ⇒ **亀腹の上に土台を立てる以上、本殿の床は幣殿・拝殿より高い**。
    #   一方 幣殿は「頭貫・内法長押・**切目長押・土台を通し**、舞良戸を入れる」= 拝殿と
    #   同じ立面構成【A 6-3】⇒ ⭕ **幣殿と拝殿は同床高**。
    # ⚠ 段の値 0.90m は **根津断面の実測【P/A】からの外挿**(幣殿の床から本殿の床へ約0.9m。
    #   間に登高欄付きの木階が 5〜6級)。⇒ 確度【A 相当・根津の実測から外挿】。
    # ⛔⛔ **指図に鍵が無い。** `const.shadenHondenFloor` を新設すること(指図方の仕事)。
    #   それまでは下の暫定値で建て、毎回そう名乗る。
    if d["const"].get("shadenHondenFloor") is not None:
        out["_floor_honden"] = const_num(d, "shadenHondenFloor")
        out["_floor_honden_src"] = ("指図 const.shadenHondenFloor = %r"
                                    % (d["const"]["shadenHondenFloor"],))
    else:
        out["_floor_honden"] = out["_floor"] + HONDEN_STEP
        out["_floor_honden_src"] = ("⚠ 暫定 = const.shadenFloor + %.2f。"
                                    "指図に const.shadenHondenFloor を新設のこと" % HONDEN_STEP)
    for k in ("honden", "tsukuriai", "heiden", "haiden", "kohai"):
        r = out[k]
        r["cu"] = (r["u0"] + r["du"] / 2.0) * K     # 区画の中心(世界の u,v[m])
        r["cv"] = (r["v0"] + r["dv"] / 2.0) * K
        r["hu"] = r["du"] * K / 2.0                 # 半幅(東西)
        r["hv"] = r["dv"] * K / 2.0                 # 半幅(南北)
    return out


PART_BASE = dict(honden="Sanno_Honden", haiden="Sanno_Haiden", heiden="Sanno_Heiden",
                 tsukuriai="Sanno_Tsukuriai", kohai="Sanno_Kohai")


def mm(x):
    """[m] → FBX 名の mm。⚠ **round**(実測[間]× 1.818 は 9.19999 のように下へ落ちる — floor にしない)。"""
    return int(round(x * 1000.0))


def part_name(R, key):
    """`Sanno_<棟>_<梁間>x<桁行>ken`(柱間 1間 = 旧名のまま)/ 柱間が 1間でなければ
    `…ken_<東西 mm>x<南北 mm>`(柱芯の外形)を足す ⇒ C# `EdoAssets.Own.SannoShaden` が綴りを計算できる。"""
    r = R[key]
    nm = "%s_%dx%dken" % (PART_BASE[key], r["nu"], r["nv"])
    return nm if r["legacy"] else nm + "_%dx%d" % (mm(2 * r["hu"]), mm(2 * r["hv"]))


def kizahashi_name(k, K):
    """旧 = `Sanno_Kizahashi_3ken`(幅3間)/ 新 = `Sanno_Kizahashi_<幅>x<出>x<丈>`(mm)。"""
    if abs(k["w"] - 3 * K) < 1e-6:
        return "Sanno_Kizahashi_3ken"
    return "Sanno_Kizahashi_%dx%dx%d" % (mm(k["w"]), mm(abs(k["b"] - k["a"])), mm(k["rise"]))


def kizahashi_spec():
    """`kaidans[向拝の階]` から木階三級を読む。⛔ 数をここに書かない。"""
    d = sashizu()
    K = float(d["const"]["ken"])
    for k in d["kaidans"]:
        if k["name"] == "向拝の階":
            return dict(a=float(k["a"][0]) * K, b=float(k["b"][0]) * K,
                        v=float(k["a"][1]) * K,
                        steps=int(k["steps"]), keri=float(k["keri"]),
                        fumi=float(k["fumi"]), w=float(k["wKen"]) * K,
                        rise=float(k["yTop"]) - float(k["yBot"]))
    raise SystemExit("[shaden] 指図に kaidans[向拝の階] が無い")


# ==========================================================================
# 高さの内訳 — ⛔ すべて【U 設計値】。指図には無い
# ==========================================================================
# floor : 床(地盤から)。⛔ **数を書かない** — `apply_floor()` が指図から入れる。
#         ⭐ **本殿だけ一段高い**(石造亀腹に土台立て【A 加藤2018 6-1】)。幣殿・拝殿は同床高。
#         ⇒ `rects()` の `_floor` / `_floor_honden` を見ること。
# colH  : 床から頭貫上端までの柱高    kumi : 組物+丸桁(頭貫上端から軒先の名目平面まで)
# eave  : 軒の出 ⇒ ⛔ **数を書かない**。`apply_floor()` が **身舎の半スパン×EAVE_RATIO**
#         から出す【P 根津】。連結部(幣殿・作り合い)と向拝だけは固定値(下 EAVE_FIX)。
# gf    : 入母屋の妻の立上り比        colD : 円柱の径(総円柱)
SPEC = {
    "honden":    dict(floor=None, colH=3.95, kumi=1.20, eave=None, gf=0.45, colD=0.40),
    "haiden":    dict(floor=None, colH=4.00, kumi=1.20, eave=None, gf=0.45, colD=0.42),
    "heiden":    dict(floor=None, colH=2.30, kumi=0.65, eave=None, colD=0.36),
    "tsukuriai": dict(floor=None, colH=2.30, kumi=0.65, eave=None, colD=0.36),
    "kohai":     dict(floor=None, colH=3.25, kumi=0.50, eave=None, colD=0.36),
}
# ⚠ 連結部と向拝は軒の出を身舎から出さない —
#   ・幣殿/作り合い: 本殿と拝殿の**大屋根の軒下に完全に呑まれる**(下の `_renketsu` の
#     註)。深い軒を取ると隣の軒と干渉するだけで、絵には1cmも出ない。
#   ・向拝: 出一間【U】の庇で、軒の出は身舎のスパンと無関係。
EAVE_FIX = dict(heiden=0.60, tsukuriai=0.60, kohai=1.00)
# ⛔⛔ **連結部の軒を深くしても明るくならない**(2026-09-09 に測って確かめた。庭方18巡目 決6)。
#   `_nomikomi` の実測: 幣殿・作り合いの屋根は**両隣の大屋根に 96.1% 呑まれる**。
#   呑まれの向きは**東西**(本殿の軒 1.72 と拝殿の軒 1.72 が二間 3.636m をほぼ埋める)で、
#   `EAVE_FIX` が効くのは**南北**。⇒ 0.60 → 1.00 へ深くしても
#   **呑まれ率は 96.1% のまま・露出は 0.67 → 0.75 m²(+0.08)しか増えない**。
#   ⇒ ⭕ 0.60 のまま置く。屋根が暗い(V 46 対 大屋根 52)のは**権現造の構えの帰結**で欠陥ではない。
#   ⚠ 反り自体は入っている(`check_sori` 実測 軒寄り 0.345 < 棟寄り 0.569)。
HONDEN_STEP = 0.90   # 幣殿の床 → 本殿の床【A 相当・根津断面の実測から外挿】


def apply_floor(R):
    """指図から床高を入れ、軒の出を身舎の半スパンから出す。⛔ 数をスクリプトへ写さない。"""
    for k in SPEC:
        SPEC[k]["floor"] = R["_floor"]
        # 身舎の半スパン = 流れ方向(東西 u)の半幅。⇒ 軒の出【P 根津 = 半スパンの 0.63】
        SPEC[k]["eave"] = EAVE_FIX.get(k, R[k]["hu"] * EAVE_RATIO)
    SPEC["honden"]["floor"] = R["_floor_honden"]     # ⭐ 本殿だけ石造亀腹ぶん一段高い
UCHINORI = 2.35      # 内法(床から)【U】。⛔ 幣殿は柱高が足りないので下で詰める
EN_W = 0.90          # 縁の出【U】
KORAN_H = 0.78       # 高欄の丈(縁から)【U】
# ⭐ **腰組の懐** = 亀腹の天端 → 床。⛔ 0 にすると腰組が組めない(束立てへ戻る)。
#   ⚠ 床高は指図 `const.shadenFloor` が正典なので、亀腹の天端を**下げて**懐を作る。
#   拝殿・幣殿は床 0.95 しかないので比で頭打ちにする(床の 55%)。
KOSHI_H = 0.70       # 【U 設計値】


KAME_COURSE = 0.30   # ⭐ 布積みの**段の丈**【U 設計値 — 庭方 2026-09-09 十九巡目 指3】
                     #   蹴上(`kaidans`)と同じ刻み。⛔ 棟ごとに違う丈にしない
KAME_MIN_N = 2       # 最少の段数(⛔ 1段だと水平の目地が1本も出ず「布積み」に読めない)
KOSHI_MIN = 0.30     # 腰組の懐の下限【U】。⛔ これを割るくらいなら段を1つ減らす
KAME_MEJI = 0.007    # 面取り = **見える目地の半分**。⛔ `CHAMFER` 0.015 のままだと
                     #   突き付けの V 溝が 2×15 = **30mm** になり、庭方の受入値
                     #   「目地 ≤ 15mm」を倍で外す(2026-09-09 に実測して気づいた)


def kame_top(floor):
    """亀腹の天端。⭐ 床との差が腰組の懐になる。

    ⛔⛔ **段の丈を「天端 ÷ 段数」の余りで決めない。**2026-09-09 まではそうしていたので
      本殿 0.383m / 拝殿 0.214m と**棟ごとに段の丈が違い**、考証20巡目に
      「上下段で丈が違い、目地も通っていない」と読まれた(⭕ 指摘は正しい)。
    ⭕ ⇒ **天端の側を `KAME_COURSE` の整数倍へ丸める**(段の丈は全棟 0.30m で不変)。
      ⚠ 床高は指図 `const.shadenFloor` が正典なので動かさない — 動かすのは天端だけ。
      懐(天端→床)が `KOSHI_MIN` を割るときは**段を1つ減らす**。"""
    raw = floor - min(KOSHI_H, floor * 0.55)
    n = max(KAME_MIN_N, int(round(raw / KAME_COURSE)))
    while n > KAME_MIN_N and floor - n * KAME_COURSE < KOSHI_MIN:
        n -= 1
    return n * KAME_COURSE
# 千鳥破風【U 設計値】: b=半幅 / ug=破風面の位置(棟の芯からの u) / zde=破風の軒の高さ
# ⚠ **zde は主屋根の面より 0.5m 以上上に置くこと** — 瓦の実体は名目平面より 0.15 上に
#   うねるので、僅かに上げただけだと破風が主屋根に**埋まって三角の板だけが浮く**
#   (2026-09-09 に zde−主屋根 = 0.15 で実際にそうなった)。`chidori_hafu` が検算する。
CHIDORI = dict(b=2.30, ug=3.85, zde=6.90)
KARAHAFU = dict(A=0.90, dk=2.20, flare=0.30)  # 軒唐破風の反り【U 設計値】
# ⚠ A/dk を大きくすると **瓦の実ジオメトリが千切れる**(桁行の重ね代を超えて剪断される)。
#   2026-09-09 に A=1.15 / dk=1.60 で瓦場が穴だらけになった。⭕ 反りの稜は
#   `karahafu_crest` が**棟モジュール**で塞ぐので、A を欲張らなくても唐破風に見える。
# ⛔ **向拝の庇の上端は定数で持たない** — 拝殿の軒の出と反りから出る**従属値**。
#   `kohai()` が「拝殿の屋根面(拝殿東壁の位置)の 0.26 下」として計算する。
#   ⚠ 低く置くと主屋根の軒との間に**空の隙**が開く(2026-09-09 に 5.14 で 1.7m 開いた)


def eave_z(key):
    s = SPEC[key]
    return s["floor"] + s["colH"] + s["kumi"]


# ==========================================================================
# 座標の写像(EDO-0161)
# ==========================================================================
def BX(u, v):
    """論理 (u=東, v=北) → Blender の平面座標。Rz(180°) なので行列式 +1(巻き順不変)。"""
    return (-u, -v)


def q(u, v, h):
    """論理 (u,v,h) → `vkmesh.Mesh` の論理 (走り, 高さ, 厚み)。行列式 +1。"""
    return (-u, h, v)


def unity_verts(o):
    """Blender の組み立て座標 → Unity ローカル座標(README「書き出しの規約」)。"""
    return [(-vt.co.x, vt.co.z, -vt.co.y) for vt in o.data.vertices]


def fingerprint(o):
    """幾何の指紋。⛔ FBX の md5 は使えない(CreationTime と絶対パスが入る)。"""
    hsh = hashlib.sha1()
    for t in unity_verts(o):
        hsh.update(("%.5f,%.5f,%.5f;" % t).encode())
    for p in o.data.polygons:
        hsh.update((",".join(str(i) for i in p.vertices) + ";").encode())
    for m in o.data.materials:
        hsh.update((m.name if m else "-").encode())
    return hsh.hexdigest()[:16]


# ==========================================================================
# メッシュの道具(論理 (u,v,h) の右手系で組む。CCW = 外向き)
# ==========================================================================
def box3(M, u0, u1, v0, v1, h0, h1, uv, mat=0, grain="h"):
    """(u,v,h) の直方体。`grain` の軸へ木理(借りた矩形の v 方向)を流す。

    ⛔ `vkmesh.Mesh.box` は u=第1軸に固定なので、**長い横材に縦木理が乗る**
      (README 2026-09-04「下見板が縦縞の平板に見えたらこれ」)。"""
    ext = {"u": (u0, u1), "v": (v0, v1), "h": (h0, h1)}
    g0, g1 = ext[grain]
    gs = (g1 - g0) if abs(g1 - g0) > 1e-9 else 1.0
    ru0, rv0, ru1, rv1 = uv

    def emit(pts, other):
        """pts = (u,v,h) の4点。other = 木理でない方の軸("u"/"v"/"h")"""
        o0, o1 = ext[other]
        os_ = (o1 - o0) if abs(o1 - o0) > 1e-9 else 1.0
        idx = {"u": 0, "v": 1, "h": 2}
        uvs = []
        for p in pts:
            t = (p[idx[grain]] - g0) / gs
            s = (p[idx[other]] - o0) / os_
            uvs.append((ru0 + (ru1 - ru0) * s, rv0 + (rv1 - rv0) * t))
        M.quad_uvs([q(*p) for p in pts], uvs, mat)

    axes = ["u", "v", "h"]
    # +h / -h 面
    oth = "v" if grain == "u" else ("u" if grain in ("v", "h") else "u")
    emit([(u0, v0, h1), (u1, v0, h1), (u1, v1, h1), (u0, v1, h1)],
         "v" if grain == "u" else "u")
    emit([(u1, v0, h0), (u0, v0, h0), (u0, v1, h0), (u1, v1, h0)],
         "v" if grain == "u" else "u")
    # +u / -u 面
    emit([(u1, v0, h0), (u1, v1, h0), (u1, v1, h1), (u1, v0, h1)],
         "h" if grain == "v" else "v")
    emit([(u0, v1, h0), (u0, v0, h0), (u0, v0, h1), (u0, v1, h1)],
         "h" if grain == "v" else "v")
    # +v / -v 面
    emit([(u1, v1, h0), (u0, v1, h0), (u0, v1, h1), (u1, v1, h1)],
         "h" if grain == "u" else "u")
    emit([(u0, v0, h0), (u1, v0, h0), (u1, v0, h1), (u0, v0, h1)],
         "h" if grain == "u" else "u")
    _ = axes, oth


def cyl(M, uc, vc, h0, h1, r, uv, mat=0, n=12, taper=1.0):
    """円柱(n角柱)。**総円柱**の柱に使う。木理は縦(高さ)方向。
    ⛔ 丸太(`build_maruta`)は使わない — 社殿の柱は削り出しで、皮付きの丸太ではない。"""
    ru0, rv0, ru1, rv1 = uv
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        for (aa, bb, s0, s1) in ((a0, a1, i / float(n), (i + 1) / float(n)),):
            p0 = (uc + r * math.cos(aa), vc + r * math.sin(aa))
            p1 = (uc + r * math.cos(bb), vc + r * math.sin(bb))
            t0 = (uc + r * taper * math.cos(aa), vc + r * taper * math.sin(aa))
            t1 = (uc + r * taper * math.cos(bb), vc + r * taper * math.sin(bb))
            uu0 = ru0 + (ru1 - ru0) * s0
            uu1 = ru0 + (ru1 - ru0) * s1
            M.quad_uvs([q(p0[0], p0[1], h0), q(p1[0], p1[1], h0),
                        q(t1[0], t1[1], h1), q(t0[0], t0[1], h1)],
                       [(uu0, rv0), (uu1, rv0), (uu1, rv1), (uu0, rv1)], mat)
    # 天端(見えることは少ないが小口が抜けるのを防ぐ)
    for i in range(1, n - 1):
        a0, ai, aj = 0.0, 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        pa = (uc + r * taper * math.cos(a0), vc + r * taper * math.sin(a0))
        pb = (uc + r * taper * math.cos(ai), vc + r * taper * math.sin(ai))
        pc = (uc + r * taper * math.cos(aj), vc + r * taper * math.sin(aj))
        M.tri_uvs([q(pa[0], pa[1], h1), q(pb[0], pb[1], h1), q(pc[0], pc[1], h1)],
                  [(ru0, rv0), (ru1, rv0), (ru1, rv1)], mat)


def stick(M, p0, p1, w, t, uv, mat=0, axis="v"):
    """2点を結ぶ角材(垂木・虹梁の分節に使う)。`axis` = 断面の幅を取る水平軸。"""
    d = (p1[0] - p0[0], p1[1] - p0[1])
    ln = math.hypot(d[0], d[1])
    if ln < 1e-9:
        nx, ny = (0.0, 1.0)
    else:
        nx, ny = (-d[1] / ln, d[0] / ln)
    ru0, rv0, ru1, rv1 = uv
    cor = []
    for (p, tt) in ((p0, 0.0), (p1, 1.0)):
        for (sg, sh) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            cor.append(((p[0] + nx * w / 2.0 * sg, p[1] + ny * w / 2.0 * sg,
                         p[2] + t / 2.0 * sh), tt, sg, sh))
    P = [c[0] for c in cor]
    faces = [(0, 1, 2, 3)[::-1], (4, 5, 6, 7), (0, 4, 7, 3), (1, 2, 6, 5),
             (0, 1, 5, 4), (3, 7, 6, 2)]
    for f in faces:
        pts = [P[i] for i in f]
        uvs = []
        for i in f:
            tt = cor[i][1]
            sg = 0.0 if cor[i][2] < 0 else 1.0
            uvs.append((ru0 + (ru1 - ru0) * sg, rv0 + (rv1 - rv0) * tt))
        M.quad_uvs([q(*p) for p in pts], uvs, mat)
    _ = axis


def kouryou(M, u0, u1, v, h0, h1, w, t, uv, mat=0, n=8, sag=0.32):
    """**虹梁 / 海老虹梁** — 弓なりの梁。⛔ 直線の角材で代用しない
    (虹梁は権現造の見せ場で、まっすぐな梁は民家に見える)。"""
    pts = []
    for i in range(n + 1):
        s = i / float(n)
        hh = h0 + (h1 - h0) * s + sag * math.sin(math.pi * s)
        pts.append((u0 + (u1 - u0) * s, v, hh))
    for i in range(n):
        stick(M, pts[i], pts[i + 1], w, t, uv, mat)


# ==========================================================================
# 躯体の部位
# ==========================================================================
def _joints(L, target, stagger=False):
    """長さ L を目安 `target` で割った目地の位置。⭕ **0 について左右対称**に割る
    (EDO-0161 — 対称に割れば Unity X/Z の符号反転が幾何へ影響しないことが保証できる)。
    `stagger` は段ごとに目地を半枚ずらすため(⛔ 目地を縦に通さない)。"""
    k = max(1, int(round(L / target)))
    if stagger and k >= 2:
        pts = [-L / 2.0] + [-L / 2.0 + L * (i - 0.5) / k for i in range(1, k + 1)] \
              + [L / 2.0]
    else:
        pts = [-L / 2.0 + L * i / k for i in range(k + 1)]
    out = []
    for x in pts:                                   # 重複を落とす(端の半枚が潰れた場合)
        if not out or x - out[-1] > 1e-4:
            out.append(x)
    return out


def kamebara(hu, hv, top, name, batter=0.16, skirt=0.16, course=None, th=0.42):
    """**石造亀腹** — 社殿を載せる **切石の低い台**。返り値 = オブジェクト列。

    ⛔⛔ **玉石の乱積みにしない**(2026-09-09 考証19巡目 中6)。指定説明の裏づけは
      「**石造**亀腹に土台立てとし、縁を腰組で支持する」【A 加藤重枝2018 6-1】で、
      石造亀腹は日光・上野・紅葉山東照宮と同じ格の作り。承応期以前の幣殿型権現造の
      「切石積+漆喰亀腹」と**対比して**挙げられる部位なので、材は**加工した切石**。
      ⚠ 2026-09-09 以前は Village Kit の `Foundation_A_01` を貼っていたが、
      **あのアトラスは 2048² 全面が丸い野面石の乱積み**(実測)で切石の領域は1画素も無い。
      ⇒ 材そのものを替える必要がある。⛔ 矩形を選び直すだけでは直らない。
    【材】`M_FJG_Rock_001` — ⛔ **新規マテリアルではない**。同じ山王の
      `Own.DanishiSanno`(段石)・`Own.Ishibashi`(切石橋)・`Own.Tateishi` が使う
      **加工石**の材で、`build_sanno_buzai._stone` がそのまま切石1枚を焼く道具を持つ。
    【作り】段(course)ごとに目地を半枚ずらして積み、上へ行くほど `batter` ぶん引く。
      ⭕ 稜は `_stone` の面取り(15mm)、**天端の稜だけ倍**にして丸みを取る。"""
    import build_sanno_buzai as SB
    mat = SB.kirishi_material()                     # ⭐ 淡灰の切石(⛔ 暗い写真計測岩ではない)
    course = course or KAME_COURSE
    nc = max(1, int(round(top / course)))
    objs = []
    for c in range(nc):
        z0, z1 = top * c / float(nc), top * (c + 1) / float(nc)
        f = 1.0 - c / float(nc)                     # 下ほど外へ出る(バッター)
        ou, ov = hu + skirt + batter * f, hv + skirt + batter * f
        rng = SB.rng_of("kamebara", name, c)
        stag = (c % 2 == 1)
        for k, sg in enumerate((-1, +1)):            # 南北の面(u へ走る帯)
            v0, v1 = (-ov, -ov + th) if sg < 0 else (ov - th, ov)
            js = _joints(2 * ou, 1.05, stag)
            for i in range(len(js) - 1):
                objs.append(SB._stone(js[i], js[i + 1], v0, v1, z0, z1, mat, rng,
                                      "%s_c%d_ns%d_%d" % (name, c, k, i),
                                      chamfer=KAME_MEJI, tile=SB.KIRISHI_TILE))
        for k, sg in enumerate((-1, +1)):            # 東西の面(南北の石に挟まれる)
            u0, u1 = (-ou, -ou + th) if sg < 0 else (ou - th, ou)
            js = _joints(2 * (ov - th), 1.05, not stag)
            for i in range(len(js) - 1):
                objs.append(SB._stone(u0, u1, js[i], js[i + 1], z0, z1, mat, rng,
                                      "%s_c%d_ew%d_%d" % (name, c, k, i),
                                      chamfer=KAME_MEJI, tile=SB.KIRISHI_TILE))
    # 天端の中(石の輪の内側)を1枚で塞ぐ。⛔ 抜けたままにすると床下から空が見える
    ou, ov = hu + skirt, hv + skirt
    objs.append(SB._stone(-(ou - th), ou - th, -(ov - th), ov - th,
                          top - 0.22, top, mat, SB.rng_of("kamebara", name, "cap"),
                          "%s_cap" % name, chamfer=KAME_MEJI, tile=SB.KIRISHI_TILE))
    # ⭐ **積みを毎回声に出す**(規則19 — 数で受け入れる物は数で刷る)。
    #   庭方の受入値: 段の丈 0.30m / 目地 ≤ 15mm / 水平の直線。
    ok = abs(top / nc - KAME_COURSE) < 1e-6
    print("  亀腹 %-22s %s 天端 %.3f = **%d段 × %.3f m** / 目地(面取り×2) %.0f mm / "
          "布積み(段ごとに半枚ずらす)/ 材 %s"
          % (name, "⭕" if ok else "⛔ 段の丈が 0.30 でない", top, nc, top / nc,
             2000.0 * KAME_MEJI, mat.name))
    # ⭕ 論理 (u,v,h) → Blender (−u, −v, h)。**Rz(180°) = 行列式 +1** なので
    #   巻き順も法線も動かない(⛔ `flip_normals` を足さない)。亀腹は左右対称なので
    #   実際には姿が変わらないが、写像を明示して置くことで規約の外へ出ない。
    for o in objs:
        o.data.transform(Matrix.Diagonal((-1.0, -1.0, 1.0, 1.0)))
        o.data.update()
    return objs


def soban(pts, z0, z1, half, name):
    """**礎盤**(柱の下に据える切石)。返り値 = オブジェクト列。
    ⛔ `Foundation_A_01`(玉石の乱積み)を貼らない — 加工した石なので `kamebara` と同じ材。"""
    import build_sanno_buzai as SB
    mat = SB.kirishi_material()
    objs = []
    for i, (uu, vv) in enumerate(pts):
        objs.append(SB._stone(uu - half, uu + half, vv - half, vv + half, z0, z1,
                              mat, SB.rng_of("soban", name, i), "%s_%d" % (name, i),
                              chamfer=KAME_MEJI, tile=SB.KIRISHI_TILE))
    for o in objs:
        o.data.transform(Matrix.Diagonal((-1.0, -1.0, 1.0, 1.0)))   # 論理→Blender(det +1)
        o.data.update()
    return objs


def koshigumi(M, us, vs, floor, base, uv, mat, sides=("n", "s", "e", "w"), w=EN_W):
    """**腰組** — 身舎の柱から**床の高さで組物を出して縁を持ち出す**作り。

    ⭐ 【A 加藤重枝2018 6-1】「石造亀腹に土台立てとし、**縁を腰組で支持する**」。
    ⛔⛔ **床下から地面まで縁束を立てない**(2026-09-09 考証19巡目 中5)。束立ては民家の
      作りで、腰組とは**格が違う** — 日光・上野の東照宮系が腰組を採るのはそのため。
    ⚠ **確度**: 【A】が言うのは**本殿**について。拝殿・幣殿・作り合いに同じ作りを回すのは
      **【U 設計判断 — 本殿に倣う】**。⛔ 一般類型を既成事実にしない(規則7)。"""
    zt = base + 0.16                                # 土台の天端
    H = floor - zt                                  # 腰組の懐
    if H < 0.30:
        return
    hu, hv = us[-1], vs[-1]
    # --- 土台(亀腹の天端に据える横材。⭐「土台立て」の土台)---
    for vv in (vs[0], vs[-1]):
        box3(M, us[0] - 0.14, us[-1] + 0.14, vv - 0.13, vv + 0.13, base, zt,
             uv, mat, grain="u")
    for uu in (us[0], us[-1]):
        box3(M, uu - 0.13, uu + 0.13, vs[0] - 0.14, vs[-1] + 0.14, base, zt,
             uv, mat, grain="v")

    def unit(uu, vv, ou, ov):
        """1組の腰組。(ou,ov) = 縁の出る向き(単位)。"""
        # 大斗
        box3(M, uu - 0.17, uu + 0.17, vv - 0.17, vv + 0.17, zt, zt + 0.30 * H,
             uv, mat, grain="h")
        z1 = zt + 0.30 * H
        # 壁通りの肘木
        if ov:
            box3(M, uu - 0.40, uu + 0.40, vv - 0.10, vv + 0.10, z1, z1 + 0.22 * H,
                 uv, mat, grain="u")
        else:
            box3(M, uu - 0.10, uu + 0.10, vv - 0.40, vv + 0.40, z1, z1 + 0.22 * H,
                 uv, mat, grain="v")
        # 手先の肘木 — 縁の外端まで持ち出す(これが「持ち出し」の実体)
        tu, tv = uu + ou * (w - 0.10), vv + ov * (w - 0.10)
        box3(M, min(uu, tu) - 0.10, max(uu, tu) + 0.10,
             min(vv, tv) - 0.10, max(vv, tv) + 0.10, z1, z1 + 0.22 * H,
             uv, mat, grain=("u" if ou else "v"))
        # 手先の巻斗(縁葛を受ける)
        z2 = z1 + 0.22 * H
        for (cu, cv) in ((uu, vv), (tu, tv)):
            box3(M, cu - 0.13, cu + 0.13, cv - 0.13, cv + 0.13, z2, floor - 0.16,
                 uv, mat, grain="h")

    nodes = []
    if "s" in sides:
        nodes += [(uu, vs[0], 0, -1) for uu in us]
    if "n" in sides:
        nodes += [(uu, vs[-1], 0, +1) for uu in us]
    if "w" in sides:
        nodes += [(us[0], vv, -1, 0) for vv in vs[1:-1]]
    if "e" in sides:
        nodes += [(us[-1], vv, +1, 0) for vv in vs[1:-1]]
    for (uu, vv, ou, ov) in nodes:
        unit(uu, vv, ou, ov)
    # --- 縁葛(腰組の手先を繋いで縁の外端を通す横材)---
    ou_, ov_ = hu + w, hv + w
    if "s" in sides:
        box3(M, -ou_, ou_, -ov_, -ov_ + 0.16, floor - 0.16, floor - 0.02, uv, mat, grain="u")
    if "n" in sides:
        box3(M, -ou_, ou_, ov_ - 0.16, ov_, floor - 0.16, floor - 0.02, uv, mat, grain="u")
    if "e" in sides:
        box3(M, ou_ - 0.16, ou_, -ov_, ov_, floor - 0.16, floor - 0.02, uv, mat, grain="v")
    if "w" in sides:
        box3(M, -ou_, -ou_ + 0.16, -ov_, ov_, floor - 0.16, floor - 0.02, uv, mat, grain="v")


def en_koran(M, hu, hv, floor, uv_wood, m_wood, sides=("n", "s", "e", "w"),
             w=EN_W, kh=KORAN_H, tsuka=True):
    """**縁 + 高欄**。⭐ 「床が地面から浮いて、まわりに縁と高欄が回る」姿は
    民家と社殿を分ける一番大きい合図なので必ず入れる。

    ⚠ `tsuka=False` で **縁束を立てない** — 縁は `koshigumi` が持ち出す【A】。"""
    ou, ov = hu + w, hv + w
    T = 0.10                       # 縁板の厚み
    # 縁板(四周の帯)。⛔ 面を一枚で貼らない — 板を並べて目地を出す
    def band(u0, u1, v0, v1, along):
        n = max(2, int(round((u1 - u0 if along == "u" else v1 - v0) / 0.22)))
        for i in range(n):
            s0, s1 = i / float(n), (i + 1) / float(n)
            if along == "u":
                box3(M, u0 + (u1 - u0) * s0 + 0.006, u0 + (u1 - u0) * s1 - 0.006,
                     v0, v1, floor - T, floor, uv_wood, m_wood, grain="u")
            else:
                box3(M, u0, u1, v0 + (v1 - v0) * s0 + 0.006, v0 + (v1 - v0) * s1 - 0.006,
                     floor - T, floor, uv_wood, m_wood, grain="v")
    if "s" in sides:
        band(-ou, ou, -ov, -hv, "u")
    if "n" in sides:
        band(-ou, ou, hv, ov, "u")
    if "e" in sides:
        band(hu, ou, -hv, hv, "v")
    if "w" in sides:
        band(-ou, -hu, -hv, hv, "v")
    # 縁束(縁を支える束)。⛔ **腰組を組むときは立てない** — 束立ては民家の作りで、
    #   【A 加藤2018 6-1】の「縁を腰組で支持する」と両立しない(考証19巡目 中5)。
    if tsuka:
        for (uu, vv) in _perimeter_nodes(ou, ov, 1.818):
            if not _on_side(uu, vv, ou, ov, hu, hv, sides):
                continue
            box3(M, uu - 0.06, uu + 0.06, vv - 0.06, vv + 0.06, 0.0, floor - T,
                 uv_wood, m_wood, grain="h")
    # 高欄 — 地覆 / 束 / 平桁 / 架木
    for (a, b, along, uu, vv) in _koran_runs(ou, ov, sides):
        if along == "u":
            box3(M, a, b, vv - 0.06, vv + 0.06, floor, floor + 0.11, uv_wood, m_wood, grain="u")
            box3(M, a, b, vv - 0.05, vv + 0.05, floor + kh - 0.20, floor + kh - 0.11,
                 uv_wood, m_wood, grain="u")
            box3(M, a, b, vv - 0.07, vv + 0.07, floor + kh - 0.11, floor + kh,
                 uv_wood, m_wood, grain="u")
            n = max(2, int(round((b - a) / 0.62)))
            for i in range(n + 1):
                uu2 = a + (b - a) * i / float(n)
                box3(M, uu2 - 0.045, uu2 + 0.045, vv - 0.045, vv + 0.045,
                     floor + 0.11, floor + kh - 0.11, uv_wood, m_wood, grain="h")
            for uu2 in (a, b):                       # 隅の擬宝珠
                giboshi(M, uu2, vv, floor + kh, uv_wood, m_wood)
        else:
            box3(M, uu - 0.06, uu + 0.06, a, b, floor, floor + 0.11, uv_wood, m_wood, grain="v")
            box3(M, uu - 0.05, uu + 0.05, a, b, floor + kh - 0.20, floor + kh - 0.11,
                 uv_wood, m_wood, grain="v")
            box3(M, uu - 0.07, uu + 0.07, a, b, floor + kh - 0.11, floor + kh,
                 uv_wood, m_wood, grain="v")
            n = max(2, int(round((b - a) / 0.62)))
            for i in range(n + 1):
                vv2 = a + (b - a) * i / float(n)
                box3(M, uu - 0.045, uu + 0.045, vv2 - 0.045, vv2 + 0.045,
                     floor + 0.11, floor + kh - 0.11, uv_wood, m_wood, grain="h")


def giboshi(M, uu, vv, ztop, uv, mat):
    """**擬宝珠** — 高欄の隅柱の頭。⭐ 神社・寺の高欄の合図。
    ⛔ 球を作らない(重い)— 段の付いた擬宝珠の輪郭を箱3段で出す。"""
    for (r, z0, z1) in ((0.075, 0.0, 0.06), (0.105, 0.06, 0.15),
                        (0.075, 0.15, 0.26), (0.040, 0.26, 0.31)):
        box3(M, uu - r, uu + r, vv - r, vv + r, ztop + z0, ztop + z1, uv, mat, grain="h")


def kizahashi_honden(M, hu, z_lo, z_hi, uv, mat, steps=5, w=1.30):
    """**幣殿 → 本殿の木階(登高欄付き)。**作り合いの一間の中に納める。

    ⭐ **本殿の床が一段高いことの現れ**で、⛔ 部材方の意匠ではない —
      本殿は「石造亀腹に土台立て」【A 加藤2018 6-1】、幣殿は「切目長押・土台を通し」で
      拝殿と同じ立面構成【A 6-3】⇒ 本殿だけ床が高い。段は根津断面の実測【P/A】で
      **約0.9m・木階5〜6級・登高欄付き**。⛔ 石段にしない(内部の階は木階)。"""
    rise = (z_hi - z_lo) / float(steps)
    if rise <= 0.01:
        return
    u_hi = hu * 0.80                    # 東(幣殿側)の踏み出し
    run = hu * 1.60
    fumi = run / steps
    hw = w / 2.0
    for i in range(steps):
        zt = z_lo + (i + 1) * rise
        u1 = u_hi - i * fumi
        u0 = u1 - fumi - 0.04
        box3(M, u0, u1, -hw, hw, zt - 0.07, zt, uv["wood"], mat, grain="v")
        box3(M, u0 - 0.03, u0 + 0.02, -hw, hw, zt, zt + rise - 0.07,
             uv["wood"], mat, grain="v")
    for sg in (-1, +1):
        vv = sg * (hw + 0.08)
        stick(M, (u_hi + 0.10, vv, z_lo - 0.10), (u_hi - run - 0.10, vv, z_hi - 0.10),
              0.09, 0.26, uv["wood"], mat)
        for (dz, t) in ((0.12, 0.09), (0.62, 0.07), (0.74, 0.11)):   # 地覆/平桁/架木
            stick(M, (u_hi + 0.10, vv, z_lo + dz), (u_hi - run - 0.10, vv, z_hi + dz),
                  0.10, t, uv["wood"], mat)
        for j in range(steps + 1):
            uu = u_hi + 0.10 - (run + 0.20) * j / float(steps)
            zz = z_lo + (z_hi - z_lo) * j / float(steps)
            box3(M, uu - 0.045, uu + 0.045, vv - 0.045, vv + 0.045,
                 zz + 0.12, zz + 0.62, uv["wood"], mat, grain="h")
        giboshi(M, u_hi + 0.10, vv, z_lo + 0.80, uv["wood"], mat)
        giboshi(M, u_hi - run - 0.10, vv, z_hi + 0.80, uv["wood"], mat)


def _perimeter_nodes(ou, ov, pitch):
    out = []
    nu = max(1, int(round(2 * ou / pitch)))
    nv = max(1, int(round(2 * ov / pitch)))
    for i in range(nu + 1):
        uu = -ou + 2 * ou * i / float(nu)
        out.append((uu, -ov)); out.append((uu, ov))
    for j in range(1, nv):
        vv = -ov + 2 * ov * j / float(nv)
        out.append((-ou, vv)); out.append((ou, vv))
    return out


def _on_side(uu, vv, ou, ov, hu, hv, sides):
    if abs(vv + ov) < 1e-6:
        return "s" in sides
    if abs(vv - ov) < 1e-6:
        return "n" in sides
    if abs(uu + ou) < 1e-6:
        return "w" in sides
    if abs(uu - ou) < 1e-6:
        return "e" in sides
    return False


def _koran_runs(ou, ov, sides):
    r = []
    if "s" in sides:
        r.append((-ou, ou, "u", 0.0, -ov + 0.07))
    if "n" in sides:
        r.append((-ou, ou, "u", 0.0, ov - 0.07))
    if "e" in sides:
        r.append((-ov + 0.14, ov - 0.14, "v", ou - 0.07, 0.0))
    if "w" in sides:
        r.append((-ov + 0.14, ov - 0.14, "v", -ou + 0.07, 0.0))
    return r


def bay_lines(half, n):
    """柱間の芯の並び(-half .. +half を n 等分)。"""
    return [-half + 2 * half * i / float(n) for i in range(n + 1)]


def columns(M, hu, hv, nu, nv, floor, colH, r, uv, mat, base=None):
    """**総円柱**。四周の柱間の交点に立てる(内部の柱は見えないので立てない)。

    ⚠ `base` = 柱の**足元**(既定 = 床)。腰組を組む棟では**亀腹の天端**まで下ろす —
      「石造亀腹に**土台立て**」【A 加藤2018 6-1】は、柱が床より下の土台から立つ姿。"""
    us = bay_lines(hu, nu)
    vs = bay_lines(hv, nv)
    pts = []
    for uu in us:
        pts.append((uu, vs[0])); pts.append((uu, vs[-1]))
    for vv in vs[1:-1]:
        pts.append((us[0], vv)); pts.append((us[-1], vv))
    for (uu, vv) in pts:
        cyl(M, uu, vv, floor if base is None else base, floor + colH, r / 2.0,
            uv, mat, n=12, taper=0.94)
    return us, vs


def kumimono(M, us, vs, floor, colH, kumi, uv, mat, kind="hiramitsudo"):
    """**斗栱**(平三斗 / 出組)+ 頭貫 + 台輪 + 中備(間斗束)。
    ⭐ **社殿と民家を分ける最大の合図**。⛔ 省いて軒桁だけにしない。"""
    z0 = floor + colH
    hu, hv = us[-1], vs[-1]
    de = 0.30 if kind == "degumi" else 0.0        # 出組は一手先へ出る
    # 頭貫(柱の頭を繋ぐ)+ 台輪
    for vv in (vs[0], vs[-1]):
        box3(M, us[0] - 0.10, us[-1] + 0.10, vv - 0.09, vv + 0.09, z0 - 0.30, z0,
             uv, mat, grain="u")
        box3(M, us[0] - 0.22, us[-1] + 0.22, vv - 0.14, vv + 0.14, z0, z0 + 0.10,
             uv, mat, grain="u")
    for uu in (us[0], us[-1]):
        box3(M, uu - 0.09, uu + 0.09, vs[0] - 0.10, vs[-1] + 0.10, z0 - 0.30, z0,
             uv, mat, grain="v")
        box3(M, uu - 0.14, uu + 0.14, vs[0] - 0.22, vs[-1] + 0.22, z0, z0 + 0.10,
             uv, mat, grain="v")
    zb = z0 + 0.10

    def unit(uu, vv, along, out_dir):
        """1組の斗栱。along = 肘木の走る軸、out_dir = 軒の出る向き(±1)"""
        # 大斗
        box3(M, uu - 0.21, uu + 0.21, vv - 0.21, vv + 0.21, zb, zb + 0.26, uv, mat, grain="h")
        z1 = zb + 0.26
        # 肘木(壁通り)
        if along == "u":
            box3(M, uu - 0.55, uu + 0.55, vv - 0.11, vv + 0.11, z1, z1 + 0.20, uv, mat, grain="u")
        else:
            box3(M, uu - 0.11, uu + 0.11, vv - 0.55, vv + 0.55, z1, z1 + 0.20, uv, mat, grain="v")
        z2 = z1 + 0.20
        # 三斗(巻斗3個)
        for s in (-0.44, 0.0, 0.44):
            if along == "u":
                box3(M, uu + s - 0.13, uu + s + 0.13, vv - 0.13, vv + 0.13, z2, z2 + 0.19,
                     uv, mat, grain="h")
            else:
                box3(M, uu - 0.13, uu + 0.13, vv + s - 0.13, vv + s + 0.13, z2, z2 + 0.19,
                     uv, mat, grain="h")
        if kind == "degumi":
            # 出組 — 一手前へ出す(手先の肘木 + 巻斗)
            if along == "u":
                box3(M, uu - 0.13, uu + 0.13, vv, vv + out_dir * (de + 0.22), z1, z1 + 0.18,
                     uv, mat, grain="v")
                box3(M, uu - 0.42, uu + 0.42, vv + out_dir * de - 0.11,
                     vv + out_dir * de + 0.11, z1 + 0.18, z1 + 0.36, uv, mat, grain="u")
            else:
                box3(M, uu, uu + out_dir * (de + 0.22), vv - 0.13, vv + 0.13, z1, z1 + 0.18,
                     uv, mat, grain="u")
                box3(M, uu + out_dir * de - 0.11, uu + out_dir * de + 0.11,
                     vv - 0.42, vv + 0.42, z1 + 0.18, z1 + 0.36, uv, mat, grain="v")

    for uu in us:
        unit(uu, vs[0], "u", -1)
        unit(uu, vs[-1], "u", +1)
    for vv in vs[1:-1]:
        unit(us[0], vv, "v", -1)
        unit(us[-1], vv, "v", +1)
    # 中備(間斗束)— 柱間の中央
    def masuzuka(uu, vv):
        box3(M, uu - 0.08, uu + 0.08, vv - 0.08, vv + 0.08, zb, zb + 0.34, uv, mat, grain="h")
        box3(M, uu - 0.15, uu + 0.15, vv - 0.15, vv + 0.15, zb + 0.34, zb + 0.50,
             uv, mat, grain="h")
    for i in range(len(us) - 1):
        c = (us[i] + us[i + 1]) / 2.0
        masuzuka(c, vs[0]); masuzuka(c, vs[-1])
    for j in range(len(vs) - 1):
        c = (vs[j] + vs[j + 1]) / 2.0
        masuzuka(us[0], c); masuzuka(us[-1], c)
    # 丸桁(組物の上を通す)
    zt = zb + 0.65 + (0.0 if kind != "degumi" else 0.0)
    for vv in (vs[0] - de, vs[-1] + de):
        box3(M, us[0] - 0.35 - de, us[-1] + 0.35 + de, vv - 0.10, vv + 0.10, zt, zt + 0.20,
             uv, mat, grain="u")
    for uu in (us[0] - de, us[-1] + de):
        box3(M, uu - 0.10, uu + 0.10, vs[0] - 0.35 - de, vs[-1] + 0.35 + de, zt, zt + 0.20,
             uv, mat, grain="v")
    _ = hu, hv


def hip_depth(hu, eave, gf):
    """入母屋の隅(寄棟)面が軒先から内へ入る **平面上の** 深さ a。
    ⭕ 反りを入れても a は動かない — a = cy·gf(cy = 半スパン)で勾配に依らないため、
      平面の作図は 5.5寸のときとそのまま同じ。動くのは高さだけ。"""
    return (hu + eave) * gf


def taruki(M, hu, hv, eaveZ, eave, uv, mat, sori, pitch=0.36, hip=None, seg=3):
    """**垂木**(化粧垂木)+ 茅負。軒の下から見えるので必ず入れる。

    ⛔⛔ **入母屋の隅(寄棟)面の外へ垂木を伸ばさない。** 東西の流れは軒先から
      深さ `a = hb/RATIO` までは**台形に絞られて**おり(`GR.make_irimoya` の作図)、
      その外は破風の下の空である。一律の長さで入れると垂木が瓦を突き抜けて
      **屋根の上に木の棒が散る**(2026-09-09 に2度実見)。
      ⇒ ⭕ **各垂木の長さを「軒先から、直交する側の軒先までの残り」で頭打ちにする** —
        隅では自然に短くなり、扇垂木のように納まる。"""
    tw, tt = 0.085, 0.105
    full = eave + (0.55 if hip is None else max(0.15, min(0.55, hip - eave - 0.12)))
    UE, VE = hu + eave, hv + eave

    def ray(p_eave, d_uv, depth):
        """軒先 p_eave から屋根の内側 d_uv 方向へ depth だけ、**反りに沿って**伸ばす。

        ⛔⛔ **一本の直材で結ばない。** 反った屋根面 z(d) は **凸**(勾配が奥ほど急)
          なので、軒先と奥の2点を直線で結ぶと弦が曲線の**上**を通り、
          垂木が瓦を突き抜けて屋根の上に木の棒が並ぶ。⇒ `seg` 本に折る。"""
        for i in range(seg):
            d0 = depth * i / float(seg)
            d1 = depth * (i + 1) / float(seg)
            p0 = (p_eave[0] + d_uv[0] * d0, p_eave[1] + d_uv[1] * d0,
                  eaveZ + sori.z(d0) - tt)
            p1 = (p_eave[0] + d_uv[0] * d1, p_eave[1] + d_uv[1] * d1,
                  eaveZ + sori.z(d1) - tt)
            stick(M, p0, p1, tw, tt, uv, mat)

    n = max(2, int(round(2 * VE / pitch)))
    for i in range(n + 1):
        vv = -VE + 2 * VE * i / float(n)
        d = min(full, VE - abs(vv))              # ⇐ 隅で短くなる
        if d < 0.12:
            continue
        ray((UE, vv), (-1, 0), d)
        ray((-UE, vv), (+1, 0), d)
    n = max(2, int(round(2 * UE / pitch)))
    for i in range(n + 1):
        uu = -UE + 2 * UE * i / float(n)
        d = min(full, UE - abs(uu))
        if d < 0.12:
            continue
        ray((uu, VE), (0, -1), d)
        ray((uu, -VE), (0, +1), d)
    # 茅負(軒先を通す化粧板)
    box3(M, -UE - 0.02, UE + 0.02, -VE - 0.02, -VE + 0.10, eaveZ - 0.19, eaveZ - 0.02,
         uv, mat, grain="u")
    box3(M, -UE - 0.02, UE + 0.02, VE - 0.10, VE + 0.02, eaveZ - 0.19, eaveZ - 0.02,
         uv, mat, grain="u")
    box3(M, -UE - 0.02, -UE + 0.10, -VE, VE, eaveZ - 0.19, eaveZ - 0.02, uv, mat, grain="v")
    box3(M, UE - 0.10, UE + 0.02, -VE, VE, eaveZ - 0.19, eaveZ - 0.02, uv, mat, grain="v")


# ---- 建具 ----------------------------------------------------------------
def panel_ita(M, a0, a1, along, w, z0, z1, uv, mat, t=0.05):
    """板壁(縦板を並べる)。⛔ 一枚板にしない — 目地の影が無いとベタ塗りに見える。"""
    n = max(2, int(round((a1 - a0) / 0.28)))
    for i in range(n):
        s0 = a0 + (a1 - a0) * i / float(n) + 0.008
        s1 = a0 + (a1 - a0) * (i + 1) / float(n) - 0.008
        if along == "u":
            box3(M, s0, s1, w - t, w + t, z0, z1, uv, mat, grain="h")
        else:
            box3(M, w - t, w + t, s0, s1, z0, z1, uv, mat, grain="h")


def panel_mairado(M, a0, a1, along, w, z0, z1, uv, mat, t=0.05, out=+1):
    """**舞良戸** — 板戸に細い横桟(舞良子)を打つ。

    ⚠ `out` = **外(見え側)がどちらか**(±1)。⛔ 決め打ちにしない — 舞良子は外面に打つ物で、
      南面(v が負の側)で `+` に決め打ちすると桟が室内側へ回る。"""
    if along == "u":
        box3(M, a0, a1, w - t, w + t, z0, z1, uv, mat, grain="u")
    else:
        box3(M, w - t, w + t, a0, a1, z0, z1, uv, mat, grain="v")
    n = max(4, int((z1 - z0) / 0.19))
    o0, o1 = (w + out * t, w + out * (t + 0.022))
    lo, hi = min(o0, o1), max(o0, o1)
    for i in range(1, n):
        z = z0 + (z1 - z0) * i / float(n)
        if along == "u":
            box3(M, a0 + 0.03, a1 - 0.03, lo, hi, z - 0.022, z + 0.022,
                 uv, mat, grain="u")
        else:
            box3(M, lo, hi, a0 + 0.03, a1 - 0.03, z - 0.022, z + 0.022,
                 uv, mat, grain="v")


def panel_koshi(M, a0, a1, along, w, z0, z1, uv, mat, uvb, matb, pitch=0.115,
                t=0.035, out=+1):
    """**格子戸 / 蔀戸** — 竪子を実体で並べ、**裏に**明かり障子(板)を入れる。
    ⛔ 格子だけにしない — 素通しになって建物の中と反対側の壁の裏面が見える。

    ⛔⛔ `out` = **外(見え側)がどちらか**(±1)。⚠ 2026-09-09 まで裏板を
      **常に `w − t − 0.03`(= 論理の負側)**へ置いていたので、**南面と西面では裏板が
      格子の外側**へ出て、竪子を隠した**白い無地の板**になっていた
      (考証19巡目 軽微2「左側面に白い無地の板が数枚」の正体。⛔ remap 漏れではない)。"""
    b0, b1 = w - out * t, w - out * (t + 0.03)
    lo, hi = min(b0, b1), max(b0, b1)
    if along == "u":
        box3(M, a0, a1, lo, hi, z0, z1, uvb, matb, grain="u")
    else:
        box3(M, lo, hi, a0, a1, z0, z1, uvb, matb, grain="v")
    n = max(3, int((a1 - a0) / pitch))
    for i in range(n):
        c = a0 + (a1 - a0) * (i + 0.5) / n
        if along == "u":
            box3(M, c - 0.019, c + 0.019, w - t, w + t, z0, z1, uv, mat, grain="h")
        else:
            box3(M, w - t, w + t, c - 0.019, c + 0.019, z0, z1, uv, mat, grain="h")
    for j in range(1, 4):
        z = z0 + (z1 - z0) * j / 4.0
        if along == "u":
            box3(M, a0, a1, w - t - 0.006, w + t + 0.006, z - 0.024, z + 0.024,
                 uv, mat, grain="u")
        else:
            box3(M, w - t - 0.006, w + t + 0.006, a0, a1, z - 0.024, z + 0.024,
                 uv, mat, grain="v")


def kokabe(M, us, vs, floor, colH, uvw, mw, uc=UCHINORI, renji=None):
    """内法から頭貫までの小壁(漆喰)+ **長押** + **連子欄間**。

    ⛔ 漆喰を一枚貼っただけにしない — 借りた `wall C` の無地の帯が**白い板ガラス**に見え、
      社殿が民家どころか近代建築に見える(2026-09-09 に実見)。⭕ 内法に長押を打ち、
      小壁の上半分に連子(竪子)を並べて陰影を作る。"""
    z0, z1 = floor + uc, floor + colH - 0.30
    if z1 <= z0 + 0.05:
        return
    for vv in (vs[0], vs[-1]):
        box3(M, us[0] - 0.05, us[-1] + 0.05, vv - 0.07, vv + 0.07, z0, z1, uvw, mw, grain="u")
    for uu in (us[0], us[-1]):
        box3(M, uu - 0.07, uu + 0.07, vs[0] - 0.05, vs[-1] + 0.05, z0, z1, uvw, mw, grain="v")
    if renji is None:
        return
    uvw2, mw2 = renji                                  # (木のUV矩形, 木の材質索引)
    zr0, zr1 = z0 + (z1 - z0) * 0.34, z1 - 0.02
    for (a0, a1, along, w) in ((us[0], us[-1], "u", vs[0]), (us[0], us[-1], "u", vs[-1]),
                               (vs[0], vs[-1], "v", us[0]), (vs[0], vs[-1], "v", us[-1])):
        # 長押(内法の位置に横一文字)
        if along == "u":
            box3(M, a0 - 0.08, a1 + 0.08, w - 0.11, w + 0.11, z0 - 0.13, z0 + 0.02,
                 uvw2, mw2, grain="u")
            box3(M, a0 - 0.08, a1 + 0.08, w - 0.10, w + 0.10, z1 - 0.02, z1 + 0.10,
                 uvw2, mw2, grain="u")
        else:
            box3(M, w - 0.11, w + 0.11, a0 - 0.08, a1 + 0.08, z0 - 0.13, z0 + 0.02,
                 uvw2, mw2, grain="v")
            box3(M, w - 0.10, w + 0.10, a0 - 0.08, a1 + 0.08, z1 - 0.02, z1 + 0.10,
                 uvw2, mw2, grain="v")
        # 連子(竪子)
        n = max(4, int((a1 - a0) / 0.20))
        for i in range(n + 1):
            c = a0 + (a1 - a0) * i / float(n)
            if along == "u":
                box3(M, c - 0.033, c + 0.033, w - 0.10, w + 0.10, zr0, zr1, uvw2, mw2, grain="h")
            else:
                box3(M, w - 0.10, w + 0.10, c - 0.033, c + 0.033, zr0, zr1, uvw2, mw2, grain="h")


# ==========================================================================
# 材(⛔ 新規マテリアルを作らない)
# ==========================================================================
def mats():
    """(材質のリスト, UV矩形の辞書)。索引 0=wood 1=wall C 2=door wall

    ⛔⛔ **`Foundation_A_01` を持たない**(2026-09-09 に落とした)。あのアトラスは
      2048² 全面が**丸い野面石の乱積み**で、石造亀腹にも礎盤にも当たらない(考証19巡目 中6)。
      ⇒ 石の部位は `M_FJG_Rock_001`(加工石)を `kamebara` / `soban` が別体で焼く。"""
    m_wood, uv_wood = VM.vk_mat(V, "Walls and floors/column A.fbx", "wood", GR.WOOD_UV)
    m_wall, uv_wall = VM.vk_mat(V, "Walls and floors/wall C.fbx", "wall C", GR.WALLC_UV)
    m_door, uv_door = VM.vk_mat(V, "Walls and floors/door wall A.fbx", "door wall",
                                (0.05, 0.05, 0.45, 0.95))
    uv = dict(
        wood=GR.WOOD_UV,                       # 縦木理の一枚(柱・板)
        wood_h=VM.sub(uv_wood, 0.12, 0.06, 0.42, 0.94),
        wall=VM.sub(uv_wall, 0.10, 0.10, 0.90, 0.60),
        door=VM.sub(uv_door, 0.06, 0.10, 0.44, 0.90),
        shoji=VM.sub(uv_door, 0.55, 0.12, 0.95, 0.88),
        # ⭐ **舞良戸・御扉の板**。⛔ `door`(明かり障子の紙)を貼らない — 2026-09-09 まで
        #   そうしていたので近景で**障子の桟のような格子**に焼け、考証20巡目 中6 に
        #   「舞良戸に読めない・全面が連子窓＋腰板」と読まれた(⭕ 指摘は正しい)。
        # ⚠ ⛔ **材は替えない**(`door wall` のまま)— 替えると Unity の remap も
        #   `check_front_east(door_east)` の窓も同時に壊れる(実際に一度壊した)。
        #   ⭕ **アトラスの矩形だけ**を、同じ `door wall` の中の**腰板(縦板)の帯**へ移す。
        #   実測: 中央 RGB(56,45,41) H16° S26.8% V22.0%(std 12.7 = 無地ではない)。
        # ⚠ この矩形は `sub` ではなく**アトラスの絶対座標**(`uv_door` は紙の面を指すので、
        #   その内側を割っても木の帯には届かない)。
        itado=(0.03, 0.050, 0.66, 0.142),
    )
    return [m_wood, m_wall, m_door], uv


W, WC, DW = 0, 1, 2


# ==========================================================================
# 屋根
# ==========================================================================
def _board_run(name, x, inward, pts, mat, bw=0.62, bt=0.22, drop=0.55):
    """(y,z) の折れ線に沿う **破風板 + 眉**。GR.gable の板と同じ断面を折れ線で継ぐ。
    ⛔ 直線1本で通さない — 反った屋根の破風は曲がっているのが姿の核心。"""
    out = []
    for i in range(len(pts) - 1):
        a0 = Vector((x, pts[i][0], pts[i][1]))
        b0 = Vector((x, pts[i + 1][0], pts[i + 1][1]))
        dn = (b0 - a0)
        if dn.length < 1e-6:
            continue
        dn = dn.normalized()
        up = Vector((0.0, -dn.z, dn.y))
        if up.z < 0:
            up = -up
        up.normalize()
        a = a0 - dn * 0.03          # 継ぎ目を少し重ねて光の筋を出さない
        b = b0 + dn * 0.03
        for tag, wid, thk, off, ctr in [
                ("_hafu", bw, bt, 0.0, (0.5 - drop) * bw),
                ("_mayu", bw * 0.20, bt * 0.55, bt * 0.60, (0.10 - drop) * bw)]:
            d = Vector((-inward * (thk / 2.0 + off), 0.0, 0.0))
            lo, hi = up * ctr - up * (wid / 2.0), up * ctr + up * (wid / 2.0)
            t = Vector((thk / 2.0, 0.0, 0.0))
            vs = [a + d + lo - t, a + d + hi - t, b + d + hi - t, b + d + lo - t,
                  a + d + lo + t, a + d + hi + t, b + d + hi + t, b + d + lo + t]
            fs = [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2],
                  [2, 6, 7, 3], [3, 7, 4, 0]]
            bd = GR._mesh_from_poly("%s%s%d" % (name, tag, i), vs, fs, recalc=True)
            bd.data.materials.append(mat)
            u0, v0, u1, v1 = GR.WOOD_UV
            if tag == "_mayu":
                u1 = u0 + (u1 - u0) * 0.25
            GR._uv_by_vertex(bd, {0: (u0, v0), 1: (u1, v0), 2: (u1, v1), 3: (u0, v1),
                                  4: (u0, v0), 5: (u1, v0), 6: (u1, v1), 7: (u0, v1)})
            out.append(bd)
    return out


def gable_sori(x, inward, y_lo, y_hi, apex_y, zb, zfun, name, p, n=18,
               thick=0.14, bw=0.62, bt=0.22, drop=0.55):
    """**反った妻**(妻壁+木連格子+破風板+懸魚)。GR.gable の反り版。返り値=オブジェクト列。

    ⛔ `GR.gable` は直線の三角形しか描けない(御殿・土井が使っているので触らない)。
      反った屋根に直線の破風を付けると、**破風だけが屋根面から離れて浮く**。
    `zfun(y)` = その y での屋根面の高さ(= 妻壁の上端 = 破風の内法)。"""
    m_wall, m_wood = p['wall'], p['wood']
    xi = x + inward * thick
    ys = [y_lo + (y_hi - y_lo) * i / float(n) for i in range(n + 1)]
    prof = [(yy, zfun(yy)) for yy in ys]
    out = []

    # --- 妻壁(反った稜を持つ角柱。厚みは内側だけ)---
    tw = GR.plaque(name + "_tsuma", prof, x, xi, m_wall, None)
    V.set_uv_rect(tw, GR.WALLC_UV, axes=('y', 'z'))
    out.append(tw)

    gh = zfun(apex_y) - zb
    hw = (y_hi - y_lo) / 2.0
    z_base = zb + 0.20

    # --- 妻壁の足元の水切り板(瓦の波形が壁に食い込むのを隠す)---
    mz = V.box(name + "_mizukiri", (0.22, y_hi - y_lo, 0.34),
               (x - inward * 0.11, (y_lo + y_hi) / 2.0, zb + 0.03), m_wood)
    V.set_uv_rect(mz, GR.WOOD_UV, axes=('z', 'y'))
    out.append(mz)

    # --- 木連格子(縦の組子 + 貫)---
    pitch, sw, sd = 0.303, 0.055, 0.05
    def slat(yy):
        z1 = zfun(yy) - 0.20
        if z1 <= z_base + 0.12:
            return False
        o = V.box(name + "_koshi", (sd, sw, z1 - z_base),
                  (x - inward * sd / 2.0, yy, (z_base + z1) / 2.0), m_wood)
        V.set_uv_rect(o, GR.WOOD_UV, axes=('x', 'z'))
        out.append(o)
        return True
    slat(apex_y)
    k = 1
    while k * pitch < hw - 0.35:
        for s in (-1, 1):
            if not slat(apex_y + s * k * pitch):
                break
        k += 1
    for fr in (0.18, 0.46, 0.74):          # 貫3段。⭕ 幅は **zfun を逆に引いて**決める
        z = zb + gh * fr
        yy = apex_y
        step = hw / 64.0
        while yy + step < y_hi and zfun(yy + step) > z:
            yy += step
        wdt = 2.0 * (yy - apex_y) - 0.30
        if wdt < 0.4 or z < z_base:
            continue
        o = V.box(name + "_nuki", (sd * 1.2, wdt, 0.075),
                  (x - inward * sd * 0.6, apex_y, z), m_wood)
        V.set_uv_rect(o, GR.WOOD_UV, axes=('x', 'y'))
        out.append(o)

    # --- 破風板(反りに沿って折れ線で継ぐ)---
    mid = n // 2
    out += _board_run(name + "_a", x, inward, prof[:mid + 1], m_wood, bw, bt, drop)
    out += _board_run(name + "_b", x, inward, prof[mid:], m_wood, bw, bt, drop)

    # --- 拝みの懸魚(蕪懸魚 + 六葉)---
    xout = x - inward * (bt * 1.15)
    sc = max(0.50, min(1.50, gh * 0.50))
    g = GR.plaque(name + "_gegyo", GR.GEGYO, xout - inward * 0.07, xout,
                  m_wood, None, sc=sc, oy=apex_y, oz=zfun(apex_y) - 0.03)
    V.set_uv_rect(g, GR.WOOD_UV, axes=('y', 'z'))
    out.append(g)
    out.append(GR.plaque(name + "_rokuyo", GR.ROKUYO, xout - inward * 0.105,
                         xout - inward * 0.07, m_wood, p['uv_dark'],
                         sc=sc, oy=apex_y, oz=zfun(apex_y) - 0.03))
    return out


def make_irimoya_sori(W, D, name, eave, gf, sori, p):
    """**反りを持つ入母屋。**W=桁行(X) D=梁間(Y)。返り値=1メッシュ(軒先の名目 z=0)。

    ⛔ `GR.make_irimoya` は勾配 RATIO の**平面**で組んであり反りを入れる口が無い
      (かつ御殿・土井が使っているので触らない)。⇒ **平面の作図は同じ式のまま、
      高さだけ `sori.z(d)` へ載せ替える**。
    ⭕ 隅棟が閉じる理由: 4面とも「**自分の軒先からの水平距離 d**」に対して同じ z(d) を
      持つ ⇒ 両面が等高になる点の軌跡(= 隅棟)は**平面上で 45° のまま動かず**、
      高さだけが反りに乗る。⇒ **隅が跳ね上がる。**"""
    Wp, Dp = W + 2 * eave, D + 2 * eave
    cy = Dp / 2.0
    if abs(sori.half - cy) > 1e-6:
        raise SystemExit("[irimoya] 反りの半スパン %.3f が屋根の %.3f と違う" % (sori.half, cy))
    a = cy * gf                        # 寄棟面が内へ入る平面上の深さ(勾配に依らない)
    h = sori.z(cy)                     # 大棟高(軒先から)
    hb = sori.z(a)                     # 妻の立上り(破風の裾)
    x0, y0 = -eave, -eave

    def P(px, py):
        return (x0 + px, y0 + py)

    pieces = []
    fields = [
        ([[P(0, 0), P(Wp, 0), P(Wp - a, a), P(a, a)],
          [P(a, a), P(Wp - a, a), P(Wp - a, cy), P(a, cy)]], P(0, 0), 90, (0.0, 1.0), "_S"),
        ([[P(Wp, Dp), P(0, Dp), P(a, Dp - a), P(Wp - a, Dp - a)],
          [P(Wp - a, Dp - a), P(a, Dp - a), P(a, cy), P(Wp - a, cy)]],
         P(0, Dp), 270, (0.0, -1.0), "_N"),
        ([[P(0, 0), P(a, a), P(a, Dp - a), P(0, Dp)]], P(0, 0), 0, (1.0, 0.0), "_W"),
        ([[P(Wp, Dp), P(Wp - a, Dp - a), P(Wp - a, a), P(Wp, 0)]],
         P(Wp, 0), 180, (-1.0, 0.0), "_E"),
    ]
    for polys, org, yaw, up, tag in fields:
        f = GR._tile_field_fast(polys, org, yaw, 0.0, name + tag)
        if f is None:
            raise SystemExit("[irimoya] 瓦場が空: %s" % tag)
        pieces.append(sori_shear(f, org, up, sori))

    # --- 大棟 ---
    pieces += GR.ridge((x0 + a, y0 + cy, h), (x0 + Wp - a, y0 + cy, h),
                       name + "_omune", w=0.50, h=0.42)
    # --- 隅棟4本 — ⭐ 反りに沿う折れ線で通す(これが「隅が跳ね上がる」姿を作る)---
    ns = 6
    for (sx, sy) in ((+1, +1), (-1, +1), (+1, -1), (-1, -1)):
        cx = x0 + (0 if sx > 0 else Wp)
        cyy = y0 + (0 if sy > 0 else Dp)
        pts = [(cx + sx * (a * i / ns), cyy + sy * (a * i / ns),
                sori.z(a * i / ns) + (0.02 if i == 0 else 0.0))
               for i in range(ns + 1)]
        pieces += ridge_curve(pts, "%s_sumi%d%d" % (name, sx, sy), 0.40, 0.33)
    # --- 大棟の両端の鬼 ---
    pieces += GR.oni((x0 + a, y0 + cy, h), (-1, 0), name + "_oni0", scale=1.15)
    pieces += GR.oni((x0 + Wp - a, y0 + cy, h), (1, 0), name + "_oni1", scale=1.15)

    # --- 妻(反り版)+ 袖瓦 ---
    def zfun(yy):
        return sori.z(_clamp(min(yy - y0, y0 + Dp - yy), 0.0, cy))
    for gx, inward in ((x0 + a, +1), (x0 + Wp - a, -1)):
        pieces += gable_sori(gx, inward, y0 + a, y0 + Dp - a, y0 + cy, hb, zfun,
                             name + ("_gW" if inward > 0 else "_gE"), p)
        sx = gx - inward * 0.06
        for sg in (-1, +1):              # 拝みから両裾へ、反りに沿う袖瓦
            pts = [(sx, y0 + cy + sg * (cy - a) * i / 8.0,
                    zfun(y0 + cy + sg * (cy - a) * i / 8.0) + 0.22) for i in range(9)]
            pieces += ridge_curve(pts, "%s_sode%d%d" % (name, int(inward), sg), 0.36, 0.28)

    pieces = [x for x in pieces if x]
    V.dedup_materials()
    o = V.join(pieces, name)
    # ⭐ **軒反り** — 屋根が1体になってから、水平位置だけの関数で一括して掛ける。
    #   ⛔ 部材ごとに掛けない(瓦場・隅棟・袖瓦・破風・鬼がバラバラに動く)。
    nz = Nokizori(x0, x0 + Wp, y0, y0 + Dp)
    nokizori_apply(o, nz)
    print("  軒反り 隅 +%.3f m / 効く長さ %.2f m(⛔ 量は【U 設計値】— 典拠なし)"
          % (nz.amp, nz.L))
    V.set_origin(o, (W / 2.0, D / 2.0, 0.0))
    return o


def irimoya(name, hu, hv, eave, eaveZ, gf, p, sori):
    """**入母屋**(大棟は南北 = v 方向)。桁行=Blender X で焼き、
    ⭕ `rotate_z(-90)`(行列式 +1)で大棟を v へ倒す。"""
    o = make_irimoya_sori(2 * hv, 2 * hu, name, eave, gf, sori, p)
    o.location = (0.0, 0.0, 0.0)
    V.sel([o])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    # 組立系: +X=桁行, +Y=梁間。rotate_z(-90) で (x,y)→(y,-x)
    #   ⇒ +X → Blender −Y(= 論理 +v = 北) / +Y → Blender +X(= 論理 −u = 西)
    #   ⇒ 「南流れ(−Y側)」が **東の流れ**になる。千鳥破風はそこへ載せる。
    V.rotate_z([o], -90)
    o.location = (0.0, 0.0, eaveZ)
    V.sel([o])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return o


def chidori_hafu(name, hu, eave, eaveZ, p, b, ug, zde, sori):
    """**千鳥破風** — 東の流れに載る入母屋形の出窓破風。返り値 = オブジェクト列。

    幾何: 主屋根の東流れは z(u) = eaveZ + `sori.z`(utip − u)(utip = hu+eave)。
      破風自身も **同じ形の反り** `sch` を持ち、軒 zde から棟 zr へ ±v で上る。
    ⛔⛔ **谷を直線で引かない。** 主屋根が反った曲面になった以上、両面の交線は
      **もう直線ではない**(5.5寸の平面どうしなら直線だった)。直線のまま切ると
      破風の裾が主屋根から浮くか食い込む。⇒ ⭕ 交線を数値で解いて折れ線にし、
      `ug` との間の**台形の帯**に割って葺く(`_tile_field_fast` は凸多角形の列を取る)。
    ⚠ **軒が主屋根より上に出ていること**を確かめてから呼ぶこと(下でアサートする)。"""
    utip = hu + eave
    sch = Sori(b)                             # 破風自身の反り(半スパン = 破風の半幅)
    main = lambda u: eaveZ + sori.z(utip - u)
    zr = zde + sch.z(b)                       # 破風の大棟の高さ
    clear = zde - main(ug)
    print("  千鳥破風 軒 %.3f / 棟 %.3f / 主屋根 %.3f ⇒ 浮き %.3f m" % (zde, zr, main(ug), clear))
    if clear < 0.45:
        raise SystemExit("[chidori] ⛔ 破風の軒が主屋根から %.3f しか浮いていない "
                         "— 瓦の実体(+0.15)に埋まって板だけが浮く。zde を上げること" % clear)
    if zr > eaveZ + sori.z(utip) - 0.10:
        raise SystemExit("[chidori] ⛔ 破風の棟 %.3f が大棟 %.3f を越える"
                         % (zr, eaveZ + sori.z(utip)))

    def valley_u(vv):
        """|v| における谷(破風の面と主屋根の面が等高になる u)。"""
        return utip - sori.d_of_z(zde + sch.z(b - abs(vv)) - eaveZ)

    uh, udie = valley_u(b), valley_u(0.0)
    print("  千鳥破風 谷 u %.3f(裾)→ %.3f(拝み) / 破風の面 u=%.2f" % (uh, udie, ug))
    if max(uh, udie) > ug - 0.15:
        raise SystemExit("[chidori] ⛔ 谷 %.3f が破風の面 %.3f を越える" % (max(uh, udie), ug))
    out = []
    NV = 8
    for sg in (-1, +1):
        polys = []
        for i in range(NV):
            v0 = sg * b * i / float(NV)
            v1 = sg * b * (i + 1) / float(NV)
            polys.append([BX(valley_u(v0), v0), BX(ug, v0), BX(ug, v1),
                          BX(valley_u(v1), v1)])
        # 棟(v=0)へ向かって上る。論理 +v = Blender −Y なので、
        #   南半(sg=−1)は Blender −Y へ上る = yaw 270 / 北半は yaw 90
        yaw = 270 if sg < 0 else 90
        org = BX(ug, sg * b)
        f = GR._tile_field_fast(polys, org, yaw, zde, "%s_f%d" % (name, sg))
        if f:
            out.append(sori_shear(f, org, (0.0, float(sg)), sch))
    # 小さな大棟
    out += GR.ridge((BX(udie, 0)[0], BX(udie, 0)[1], zr),
                    (BX(ug, 0)[0], BX(ug, 0)[1], zr), name + "_mune", w=0.40, h=0.34)
    # 破風・木連格子・懸魚(妻の面は 論理 u 一定 = Blender x 一定なのでそのまま使える)
    gx = BX(ug, 0)[0]
    out += gable_sori(gx, +1, -b, b, 0.0, zde,
                      lambda yy: zde + sch.z(b - abs(yy)), name + "_g", p,
                      bw=0.46, bt=0.17, drop=0.55)
    # 袖瓦(破風の天端に被る瓦)。瓦の実体が名目平面より上にあるので 0.20 持ち上げる
    sx = gx + 0.06                      # inward=+1 の外面側へ寄せる(Blender +X = 論理 −u)
    for sg in (-1, +1):
        pts = [(sx, sg * b * (1.0 - i / 8.0),
                zde + sch.z(b * i / 8.0) + 0.20) for i in range(9)]
        out += ridge_curve(pts, "%s_sode%d" % (name, sg), 0.30, 0.24)
    return [o for o in out if o]


def ryosage(name, hu, hv, eave, ridgeZ, p, sori, west_ext=0.0, east_ext=0.0):
    """**両下造** — 大棟が東西(u)に走り、南北(v)へ両流れ。妻を持たない
    (棟の両端が本殿・拝殿に接続する)ので ⛔ **破風・懸魚を付けない**。
    `west_ext`/`east_ext` は隣の棟の軒下へ潜らせる伸ばし。"""
    hvE = hv + eave
    zeave = ridgeZ - sori.z(hvE)
    u0, u1 = -hu - west_ext, hu + east_ext
    out = []
    for sg in (-1, +1):
        poly = [BX(u0, sg * hvE), BX(u1, sg * hvE), BX(u1, 0.0), BX(u0, 0.0)]
        yaw = 270 if sg < 0 else 90
        org = BX(u0, sg * hvE)
        f = GR._tile_field_fast([poly], org, yaw, zeave, "%s_f%d" % (name, sg))
        if f:
            out.append(sori_shear(f, org, (0.0, float(sg)), sori))
    out += GR.ridge((BX(u0, 0)[0], 0.0, ridgeZ - 0.10), (BX(u1, 0)[0], 0.0, ridgeZ - 0.10),
                    name + "_mune", w=0.40, h=0.30)
    _ = p
    return [o for o in out if o], zeave


def hisashi_karahafu(name, hu, hv, eave, eaveZ, utop, ztop, p, sori, ka=KARAHAFU):
    """**向拝の庇 + 軒唐破風**。

    庇は東へ流れる一枚の瓦場。**軒唐破風はその軒先を中央で反り上げて作る** —
    ⛔ 平らな瓦場の前に板だけ立てない(板の裏に隙間が空いて空が抜ける)。
    瓦場の頂点を u の関数 w(u)(軒で1・奥で0)と v の関数 g(v)(唐破風の反り)で
    持ち上げるので、**瓦の実ジオメトリのまま**曲面になる。"""
    ue = hu + eave                      # 軒先(論理 u)
    hvE = hv + 0.60
    # ⚠ 瓦場は破風板の**内側まで**出す(0.10)。切り揃えると板の裏に隙が空いて空が抜ける
    poly = [BX(utop, -hvE), BX(ue + 0.10, -hvE), BX(ue + 0.10, hvE), BX(utop, hvE)]
    # 東(+u = Blender −X)へ流れ落ちる ⇒ 上るのは Blender +X ⇒ yaw 0
    org = BX(ue, -hvE)
    f = GR._tile_field_fast([poly], org, 0, eaveZ, name + "_f")
    if f is None:
        raise SystemExit("[karahafu] 庇の瓦場が空")
    # ⭕ 反り(u の関数)を先に、唐破風の起り(v の関数)を後に。二つは直交するので重ねられる
    sori_shear(f, org, (1.0, 0.0), sori)
    bend(f, ue, ka)
    out = [f]
    out += karahafu_crest(name, ue, eaveZ, ka)
    out += karahafu_hafu(name, ue, eaveZ, p, ka)
    _ = ztop
    return out


def karahafu_crest(name, ue, eaveZ, ka, n=18):
    """**唐破風の稜(箕甲)を棟モジュールで通す。**

    ⛔ これが無いと、反らせた瓦場の切り口がそのまま軒先に出て**ぎざぎざの小口**になる
      (2026-09-09 に実見)。⭕ 実物も唐破風の縁は熨斗瓦で巻いてある。
    ⚠ `roof top x1` は左右対称なので EDO-0161 の符号反転の影響を受けない。"""
    b = KARA_B
    pts = []
    for i in range(n + 1):
        v = -b + 2 * b * i / float(n)
        pts.append((v, eaveZ + kara_g(v, ka) + 0.02))
    out = []
    for i in range(n):
        (v0, z0), (v1, z1) = pts[i], pts[i + 1]
        out += GR.ridge((BX(ue, v0)[0], BX(ue, v0)[1], z0),
                        (BX(ue, v1)[0], BX(ue, v1)[1], z1),
                        "%s_crest%d" % (name, i), w=0.34, h=0.26)
    return out


def kara_g(v, ka):
    """軒唐破風の反り g(v)[m]。⭕ **S字(起りと反り)**にする — 単なる山形は唐破風に見えない。"""
    b = KARA_B
    t = min(1.0, abs(v) / b)
    x = 1.0 - t
    s = 3 * x * x - 2 * x * x * x                  # スムーズステップ = 変曲点を持つ S 字
    flare = (t ** 3) * (1.0 - t) * 4.0             # 端の反り返り(袖の張り)
    return ka["A"] * (s + ka["flare"] * flare)


KARA_B = 2.727      # 唐破風の半幅【U】= 向拝三間の半分。`kohai()` が上書きする


def bend(obj, ue, ka):
    """瓦場の頂点を唐破風の反りで持ち上げる。u は軒に近いほど強く効かせる。"""
    me = obj.data
    for vt in me.vertices:
        u = -vt.co.x
        v = -vt.co.y
        s = (u - (ue - ka["dk"])) / ka["dk"]
        if s <= 0.0:
            continue
        s = min(1.0, s)
        w = s * s * (3 - 2 * s)
        vt.co.z += kara_g(v, ka) * w
    me.update()


def karahafu_hafu(name, ue, eaveZ, p, ka, n=40, bw=0.34, bt=0.14):
    """唐破風の**破風板**(反りに沿う板)と**兎毛通(懸魚)**。"""
    m_wood = p['wood']
    b = KARA_B
    verts, faces, uvs = [], [], []
    prof = []
    for i in range(n + 1):
        v = -b + 2 * b * i / float(n)
        prof.append((v, eaveZ + kara_g(v, ka)))
    # 板の断面: 軒先の少し外(+u)に立て、下端を軒より下へ垂らす
    u_out = ue + 0.16
    u_in = u_out - bt
    ru0, rv0, ru1, rv1 = GR.WOOD_UV
    for i in range(n):
        (v0, z0), (v1, z1) = prof[i], prof[i + 1]
        t0, t1 = i / float(n), (i + 1) / float(n)
        quads = [
            # 外面(+u 側)
            ([(u_out, v0, z0 - bw), (u_out, v1, z1 - bw), (u_out, v1, z1), (u_out, v0, z0)],
             +1),
            # 内面
            ([(u_in, v1, z1 - bw), (u_in, v0, z0 - bw), (u_in, v0, z0), (u_in, v1, z1)], -1),
            # 天端
            ([(u_in, v0, z0), (u_in, v1, z1), (u_out, v1, z1), (u_out, v0, z0)], 0),
            # 下端
            ([(u_out, v0, z0 - bw), (u_out, v1, z1 - bw), (u_in, v1, z1 - bw),
              (u_in, v0, z0 - bw)], 0),
        ]
        for (pts, _sg) in quads:
            base = len(verts)
            verts += [Vector(BX(pp[0], pp[1]) + (pp[2],)) for pp in pts]
            faces.append([base, base + 1, base + 2, base + 3])
            uvs += [(ru0, rv0 + (rv1 - rv0) * t0), (ru0, rv0 + (rv1 - rv0) * t1),
                    (ru1, rv0 + (rv1 - rv0) * t1), (ru1, rv0 + (rv1 - rv0) * t0)]
    me = bpy.data.meshes.new(name + "_hafu")
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(m_wood)
    uvl = me.uv_layers.new(name="UVMap")
    for j, dd in enumerate(uvl.data):
        dd.uv = uvs[j]
    o = bpy.data.objects.new(name + "_hafu", me)
    bpy.context.scene.collection.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update()
    out = [o]
    # 兎毛通(唐破風の拝みに下がる懸魚)
    zc = eaveZ + kara_g(0.0, ka)
    g = GR.plaque(name + "_ubage", GR.GEGYO, BX(u_out + 0.10, 0)[0], BX(u_out + 0.02, 0)[0],
                  m_wood, None, sc=1.05, oy=0.0, oz=zc - 0.30)
    V.set_uv_rect(g, GR.WOOD_UV, axes=('y', 'z'))
    out.append(g)
    out.append(GR.plaque(name + "_rokuyo", GR.ROKUYO, BX(u_out + 0.14, 0)[0],
                         BX(u_out + 0.10, 0)[0], m_wood, p['uv_dark'],
                         sc=1.05, oy=0.0, oz=zc - 0.30))
    return out


# ==========================================================================
# 棟ごとの組み立て
# ==========================================================================
def finish(objs, name, pivot_h=0.0):
    """join → **銅瓦へ寄せ** → ピボットを **区画の中心・地盤レベル**へ。
    ⚠ 測るのは書き出しの前。"""
    V.dedup_materials()
    o = V.join([x for x in objs if x], name)
    to_copper(o)                       # ⭐ 瓦・棟・鬼は銅瓦葺【S】。灰の本瓦では出さない
    V.set_origin(o, (0.0, 0.0, pivot_h))
    return o


def mune_top(o, axis, end=0.60):
    """⭐⭐ **(大棟の上端, 部材の Y 上端, 棟飾りの丈)** を焼いたメッシュから測る。

    ⭐ 裁3(2026-09-09): **棟高 = 平場の設計面 → 大棟の上端。⛔ 鬼板・置千木は含まない。**
      ⚠ 目録 `docs/asset-index.tsv` が測っているのは **鬼の頂**(= 部材の Y 上端)なので、
      指図方は `muneHeightRule` を「目録の丈 − **棟飾りの丈**」の従属値として立てられる。
    ⛔⛔ **材で切り分けられない。**`roof top x1`(大棟・隅棟のモジュール)も
      `roof ornaments L`(鬼板)も **材質名は同じ `roof ornaments`**(2026-09-09 に実測)。
      材で外すと**大棟ごと落ちて瓦場の頂を「大棟の上端」と読み違える**(実際にそうなった)。
    ⭕ ⇒ **幾何で切る** — 鬼は大棟の**両端**に載る。⇒ **棟の中央 ±`end` [m] の帯**の
      最高点が大棟の上端(棟は走り方向に一様なので、中央を見れば端の飾りが混ざらない)。
      `axis` = 大棟の走る軸(Unity の 'x' か 'z')。両下造は鬼が無いので値は変わらない。
    ⛔ **「天端付近の頂点の走り座標の両端を捨てる」ではいけない** — その両端は
      **鬼そのもの**が決めるので、窓が鬼ごと外へずれて丸ごと拾ってしまう(2026-09-09 に実見)。"""
    pts = _roof_verts(o)
    if not pts:
        return (None, None, None)
    ytop = max(p[1] for p in pts)
    ax = 0 if axis == 'x' else 2
    core = [p[1] for p in pts if abs(p[ax]) <= end]
    mt = max(core) if core else ytop
    return (mt, ytop, ytop - mt)


def report(o, name, note=""):
    mn, mx = V.bbox([o])
    uw = [(-t[0], t[1], -t[2]) for t in [(v.co.x, v.co.z, v.co.y) for v in o.data.vertices]]
    # Unity ローカルの実寸(X=東西 / Y=高さ / Z=南北)
    ux = [t[0] for t in uw]; uy = [t[1] for t in uw]; uz = [t[2] for t in uw]
    print("SHADEN %-26s Unity W(X)%6.3f x H(Y)%6.3f x D(Z)%6.3f  "
          "X[%.2f,%.2f] Y[%.2f,%.2f] Z[%.2f,%.2f] tris=%d mats=%s %s"
          % (name, max(ux) - min(ux), max(uy) - min(uy), max(uz) - min(uz),
             min(ux), max(ux), min(uy), max(uy), min(uz), max(uz),
             sum(len(p.vertices) - 2 for p in o.data.polygons),
             [m.name for m in o.data.materials], note))
    print("       指紋 %s" % fingerprint(o))
    return mn, mx


def _taruki_obj(name, hu, hv, ez, s, uv, ms, sori):
    """垂木を**別体**で焼いて、屋根と同じ軒反りを掛ける。

    ⛔⛔ 躯体の一部として組むと、軒反りで**瓦だけが隅で 0.40m 上がり、垂木が置いていかれる**
      (軒裏に空の隙が開く)。⇒ 垂木は屋根と同じ `Nokizori` を通す。
    ⚠ 組物・丸桁・高欄には掛けない — あれは軒先線より内で、上げると高欄が傾く。"""
    MT = VM.Mesh()
    taruki(MT, hu, hv, ez, s["eave"], uv["wood_h"], W, sori,
           hip=hip_depth(hu, s["eave"], s["gf"]))
    o = MT.to_object(name + "_taruki", ms)
    e = s["eave"]
    nokizori_apply(o, Nokizori(-(hu + e), hu + e, -(hv + e), hv + e))
    return o


def honden(R, name=None):
    """**本殿** 桁行三間×梁間三間・単層・入母屋造【S】。石造亀腹・出組・総円柱・脇障子【A】。"""
    name = name or part_name(R, "honden")
    r, s = R["honden"], SPEC["honden"]
    hu, hv = r["hu"], r["hv"]
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    kb = kamebara(hu, hv, kame_top(s["floor"]), name + "_kame")
    us, vs = columns(M, hu, hv, r["nu"], r["nv"], s["floor"], s["colH"],
                     s["colD"], uv["wood"], W, base=kame_top(s["floor"]))
    kumimono(M, us, vs, s["floor"], s["colH"], s["kumi"], uv["wood_h"], W, kind="degumi")
    kokabe(M, us, vs, s["floor"], s["colH"], uv["wall"], WC, renji=(uv["wood"], W))
    # 縁は東(作り合いへ繋ぐ)以外の三方。⭐ **腰組で支持**【A 加藤2018 6-1】
    SIDES = ("n", "s", "w")
    koshigumi(M, us, vs, s["floor"], kame_top(s["floor"]), uv["wood_h"], W, sides=SIDES)
    en_koran(M, hu, hv, s["floor"], uv["wood"], W, sides=SIDES, tsuka=False)
    z0, z1 = s["floor"], s["floor"] + UCHINORI
    # 側面(南北)は **前方二間を舞良戸・後方一間を板壁**【A】。前方 = 東
    for vv in (vs[0], vs[-1]):
        og = +1 if vv > 0 else -1                          # ⭐ 外(見え側)の向き
        for i in range(len(us) - 1):
            a, b = us[i], us[i + 1]
            if i >= 1:                                     # 東側の二間 = i=1,2
                # ⭐ **舞良戸は板戸** — 板に細い横桟(舞良子)を打った物。
                #   ⇒ 矩形は `itado`(`door wall` アトラスの**腰板の帯**)。⛔ `door`(紙)は貼らない
                panel_mairado(M, a + 0.10, b - 0.10, "u", vv, z0, z1, uv["itado"], DW,
                              out=og)
            else:
                panel_ita(M, a + 0.10, b - 0.10, "u", vv, z0, z1, uv["wood"], W)
    # 背面(西)は板壁
    for j in range(len(vs) - 1):
        panel_ita(M, vs[j] + 0.10, vs[j + 1] - 0.10, "v", us[0], z0, z1, uv["wood"], W)
    # 正面(東)は御扉 — 中央間を板扉、脇間を板壁
    for j in range(len(vs) - 1):
        a, b = vs[j], vs[j + 1]
        if j == 1:
            # 御扉も**板扉** ⇒ 同じ `itado`。⛔ 紙の矩形を貼らない
            panel_mairado(M, a + 0.10, b - 0.10, "v", us[-1], z0, z1, uv["itado"], DW,
                          out=+1)
        else:
            panel_ita(M, a + 0.10, b - 0.10, "v", us[-1], z0, z1, uv["wood"], W)
    # **脇障子** — 後方(西)隅柱の左右。縁の上に立つ小さな板の衝立【A】
    for sg in (-1, +1):
        vv = sg * hv
        box3(M, -hu - EN_W + 0.10, -hu + 0.05, vv - 0.05, vv + 0.05,
             s["floor"], s["floor"] + 1.55, uv["wood"], W, grain="u")
        box3(M, -hu - EN_W + 0.06, -hu - EN_W + 0.16, vv - 0.06, vv + 0.06,
             s["floor"], s["floor"] + 1.62, uv["wood"], W, grain="h")
    ez = eave_z("honden")
    sori = Sori(hu + s["eave"])
    noki_kokabe(M, r, s, us, vs, ez, sori, uv["wall"], WC)
    body = M.to_object(name + "_body", ms)
    taru = _taruki_obj(name, hu, hv, ez, s, uv, ms, sori)
    roof = irimoya(name + "_roof", hu, hv, s["eave"], ez, s["gf"], p, sori)
    o = finish([body, taru, roof] + kb, name)
    return o, ez + sori.z(sori.half)


def haiden(R, name=None):
    """**拝殿** 桁行七間×梁間三間・入母屋造・**千鳥破風及軒唐破風附**【S】。
    ⚠ 軒唐破風は `munes[向拝]` の側に載る(この棟には千鳥破風だけ)。"""
    name = name or part_name(R, "haiden")
    r, s = R["haiden"], SPEC["haiden"]
    hu, hv = r["hu"], r["hv"]
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    kb = kamebara(hu, hv, kame_top(s["floor"]), name + "_kame")
    us, vs = columns(M, hu, hv, r["nu"], r["nv"], s["floor"], s["colH"],
                     s["colD"], uv["wood"], W, base=kame_top(s["floor"]))
    kumimono(M, us, vs, s["floor"], s["colH"], s["kumi"], uv["wood_h"], W,
             kind="hiramitsudo")
    kokabe(M, us, vs, s["floor"], s["colH"], uv["wall"], WC, renji=(uv["wood"], W))
    # ⚠ 腰組は【A】が言うのは**本殿**について。拝殿は**【U 本殿に倣う設計判断】**
    SIDES = ("n", "s", "e")
    koshigumi(M, us, vs, s["floor"], kame_top(s["floor"]), uv["wood_h"], W, sides=SIDES)
    en_koran(M, hu, hv, s["floor"], uv["wood"], W, sides=SIDES, tsuka=False)
    z0, z1 = s["floor"], s["floor"] + UCHINORI
    # 両側面(南北)**前方一間を蔀戸**【A】、残りは板壁
    for vv in (vs[0], vs[-1]):
        og = +1 if vv > 0 else -1                   # ⭐ 外(見え側)の向き
        for i in range(len(us) - 1):
            a, b = us[i], us[i + 1]
            if i == len(us) - 2:                    # 東端の一間 = 前方
                panel_koshi(M, a + 0.10, b - 0.10, "u", vv, z0, z1,
                            uv["wood"], W, uv["shoji"], DW, out=og)
            else:
                panel_ita(M, a + 0.10, b - 0.10, "u", vv, z0, z1, uv["wood"], W)
    # 背面(西)= 幣殿境。**格子戸**【A】
    for j in range(len(vs) - 1):
        panel_koshi(M, vs[j] + 0.10, vs[j + 1] - 0.10, "v", us[0], z0, z1,
                    uv["wood"], W, uv["shoji"], DW, out=-1)
    # 正面(東)は中央三間を開け、両脇二間ずつを板壁 + その上に格子欄間
    for j in range(len(vs) - 1):
        a, b = vs[j], vs[j + 1]
        if 2 <= j <= 4:
            panel_koshi(M, a + 0.10, b - 0.10, "v", us[-1], z0, z1,
                        uv["wood"], W, uv["shoji"], DW, out=+1)
        else:
            panel_ita(M, a + 0.10, b - 0.10, "v", us[-1], z0, z1, uv["wood"], W)
    ez = eave_z("haiden")
    sori = Sori(hu + s["eave"])
    noki_kokabe(M, r, s, us, vs, ez, sori, uv["wall"], WC)
    body = M.to_object(name + "_body", ms)
    taru = _taruki_obj(name, hu, hv, ez, s, uv, ms, sori)
    roof = irimoya(name + "_roof", hu, hv, s["eave"], ez, s["gf"], p, sori)
    cb, cug, czde = chidori_params(R)
    ch = chidori_hafu(name + "_chidori", hu, s["eave"], ez, p, cb, cug, czde, sori)
    o = finish([body, taru, roof] + ch + kb, name)
    return o, ez + sori.z(sori.half)


def noki_kokabe(M, r, s, us, vs, ez, sori, uv, mat):
    """⭐ **軒小壁**(台輪の上 → 垂木の下端の少し下、壁通りの板)。**柱間が 1間でない棟だけ**。

    ⛔ 軒の出 = 半スパン × EAVE_RATIO は、梁間 9.2m の棟で 2.90m になり、丸桁(頭貫上端 +0.95)の
      上に**垂木の下端まで約 1.5m の帯**が開く。壁通りに板が無いと、組物の間から**瓦場の裏(緑)**が
      素通しで見える(2026-09-14 `sanno_shaden_kohai_near.png` で実見。部材方 memory
      「社殿の組物と反り屋根を別寸へ流用すると空が抜ける」)。⭕ 高さを動かさず板で塞ぐ
      (楼門の軒小壁と同じ手)。旧 1間の棟は旧の姿を保つため足さない。"""
    if r["legacy"]:
        return None
    z0 = s["floor"] + s["colH"] + 0.10
    z1 = ez + sori.z(s["eave"]) - 0.24          # 壁通りの屋根面 − 瓦の懐と垂木の丈
    if z1 <= z0 + 0.05:
        return None
    for vv in (vs[0], vs[-1]):
        box3(M, us[0], us[-1], vv - 0.04, vv + 0.04, z0, z1, uv, mat, grain="u")
    for uu in (us[0], us[-1]):
        box3(M, uu - 0.04, uu + 0.04, vs[0], vs[-1], z0, z1, uv, mat, grain="v")
    print("  軒小壁 %.3f → %.3f(丈 %.3f)壁通り四周" % (z0, z1, z1 - z0))
    return z1 - z0


def chidori_params(R):
    """千鳥破風の (半幅 b, 破風の面 ug, 破風の軒 zde)。⭐ 柱間 1間(旧)は `CHIDORI` のまま。

    柱間が変わったら**旧い納まりの比を保って**寄せる(⛔ 絶対値のまま使わない — 軒の出 2.9m の
    拝殿では主屋根が破風の軒 6.90 を 1.3m 越えて破風が埋まる):
      ・軒先から破風の面までの距離 = 旧の比(÷ 軒の出)× 新しい軒の出
      ・破風の軒の浮き(主屋根の面から)= 旧の浮きのまま
      ・半幅 = 旧の半幅 × 桁行の柱間 / 1間(破風は柱間に掛かる)"""
    r, s = R["haiden"], SPEC["haiden"]
    if r["legacy"]:
        return CHIDORI["b"], CHIDORI["ug"], CHIDORI["zde"]
    K = R["_ken"]
    ez = eave_z("haiden")
    hu0 = r["nu"] * K / 2.0
    e0 = hu0 * EAVE_RATIO
    d0 = hu0 + e0 - CHIDORI["ug"]
    clear0 = CHIDORI["zde"] - (ez + Sori(hu0 + e0).z(d0))
    hu, e = r["hu"], s["eave"]
    d = d0 / e0 * e
    ug = hu + e - d
    zde = ez + Sori(hu + e).z(d) + clear0
    b = CHIDORI["b"] * r["pv"] / K
    print("  千鳥破風(柱間 %.3f に寄せた)半幅 %.3f / 面 u %.3f(軒先から %.3f)/ 軒 %.3f(浮き %.3f)"
          % (r["pv"], b, ug, d, zde, clear0))
    return b, ug, zde


def _renketsu(R, key, name, ebi):
    """**幣殿 / 作り合い** — 一続きの両下造の屋根を区画ごとに切り出す。
    ⭕ 断面が u について一様なので、二本を隣り合わせに据えると **継ぎ目が出ない**。"""
    r, s = R[key], SPEC[key]
    hu, hv = r["hu"], r["hv"]
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    kb = kamebara(hu, hv, kame_top(s["floor"]), name + "_kame")
    us, vs = columns(M, hu, hv, r["nu"], r["nv"], s["floor"], s["colH"],
                     s["colD"], uv["wood"], W, base=kame_top(s["floor"]))
    kumimono(M, us, vs, s["floor"], s["colH"], s["kumi"], uv["wood_h"], W,
             kind="hiramitsudo")
    # ⛔⛔ **連結部に腰組を組まない。**⚠ 幣殿・作り合いには**縁が無い**(本殿の縁と拝殿の縁の
    #   あいだを繋ぐ室で、外へ回る縁を持たない)ので、腰組は**何も支えない持ち出し**になる。
    #   2026-09-09 に一度組んで bbox が D 6.654 → 7.314 に膨らみ、宙に浮いた縁葛が出た。
    #   ⇒ `sides=()` で **土台だけ**を置く(「石造亀腹に土台立て」の土台は縁と無関係に要る)。
    koshigumi(M, us, vs, s["floor"], kame_top(s["floor"]), uv["wood_h"], W, sides=())
    uc = min(UCHINORI, s["colH"] - 0.45)
    kokabe(M, us, vs, s["floor"], s["colH"], uv["wall"], WC, uc=uc)
    z0, z1 = s["floor"], s["floor"] + uc
    if key == "heiden":
        # ⭐ 幣殿は南北の側面を**舞良戸**で閉じる(⛔ 作り合いは閉じない)。
        # ⛔⛔ **板壁で代用しない。**指定説明は幣殿について「頭貫・内法長押・切目長押・
        #   土台を通し、**舞良戸を入れる**」【A 加藤重枝2018 6-3】。2026-09-09 まで
        #   `panel_ita`(板壁)で焼いていたので、**指図の【A】の文と実物が別物**だった
        #   (考証20巡目 中6。19巡目 中5「腰組で支持する【A】に対し現物は縁束」と同型)。
        # ⚠ `out` = 外(見え側)。⛔ 決め打ちにすると南面で舞良子が室内側へ回る。
        for vv in (vs[0], vs[-1]):
            og = +1 if vv > 0 else -1
            panel_mairado(M, us[0] + 0.08, us[-1] - 0.08, "u", vv, z0, z1,
                          uv["itado"], DW, out=og)
        # **大虹梁** — 後方(西)柱上の組物から梁間方向に渡す【A】
        kouryou(M, us[0], us[-1], vs[1], s["floor"] + s["colH"] - 0.42,
                s["floor"] + s["colH"] - 0.42, 0.20, 0.34, uv["wood_h"], W, sag=0.26)
    if ebi:
        # **海老虹梁** — 本殿(西・高い)と幣殿(東・低い)を繋ぐ【A 日光・紅葉山東照宮に倣う】
        # ⛔ 作り合いは「壁で囲われた室ではない」ので壁を張らない
        for vv in (vs[0], vs[-1]):
            kouryou(M, us[0] - 0.30, us[-1] + 0.30, vv,
                    s["floor"] + s["colH"] + 0.35, s["floor"] + s["colH"] - 0.25,
                    0.18, 0.30, uv["wood_h"], W, sag=0.30)
        kizahashi_honden(M, hu, R["_floor"], R["_floor_honden"], uv, W)
    body = M.to_object(name + "_body", ms)
    hvE = hv + s["eave"]
    # ⭐ **連結部の棟高は従属値**。⛔ 5.5寸でも反りの平均でも機械的に立てない —
    #   本殿・拝殿の軒の出が身舎半スパンの 0.63【P 根津】になると、幣殿・作り合いは
    #   **両隣の大屋根の軒に完全に呑まれる**(本殿東壁と拝殿西壁の間は二間 3.636m、
    #   軒は 1.72+1.72 = 3.44m で、残る隙は 0.20m しかない)。⇒ 棟が隣の軒より高いと
    #   屋根どうしが刺さる。⇒ **隣の軒の 0.25 下**を上限にし、反りの平均をそこへ合わせる。
    lid = min(eave_z("honden"), eave_z("haiden")) - 0.25
    ridgeZ = min(eave_z(key) + Sori(hvE).z(hvE), lid)
    sori = Sori(hvE, mean=(ridgeZ - eave_z(key)) / hvE)
    print("  %s 棟 %.3f(上限 %.3f)/ 反りの平均勾配 %.3f" % (key, ridgeZ, lid, sori.mean()))
    we = 0.75 if key == "tsukuriai" else 0.0        # 本殿の軒下へ潜らせる
    ee = 0.75 if key == "heiden" else 0.0           # 拝殿の軒下へ潜らせる
    roof, zeave = ryosage(name + "_roof", hu, hv, s["eave"], ridgeZ, p, sori,
                          west_ext=we, east_ext=ee)
    # 垂木は南北の軒だけ(東西は隣の棟に隠れる)。⛔ 直材1本で結ばない
    M2 = VM.Mesh()
    for sg in (-1, +1):
        n = max(2, int(round(2 * (hu + 0.4) / 0.34)))
        for i in range(n + 1):
            uu = -(hu) + 2 * hu * i / float(n)
            for j in range(3):
                d0 = (s["eave"] + 0.45) * j / 3.0
                d1 = (s["eave"] + 0.45) * (j + 1) / 3.0
                stick(M2, (uu, sg * (hvE - d0), zeave + sori.z(d0) - 0.10),
                      (uu, sg * (hvE - d1), zeave + sori.z(d1) - 0.10),
                      0.08, 0.10, uv["wood_h"], W)
    taru = M2.to_object(name + "_taruki", ms)
    _nomikomi(R, key, we, ee)
    o = finish([body, taru] + roof + kb, name)
    return o, ridgeZ


def _nomikomi(R, key, we, ee):
    """⭐ 連結部の屋根の平面が、**両隣の大屋根の軒下にどれだけ呑まれるか**[比]。

    ⛔ 「軒の出を深くすれば明るくなる」と決め打ちしない — 呑まれの向きは**東西**で、
      深くするのは**南北**の軒なので、比が動かなければ何も変わらない(2026-09-09
      庭方18巡目 決6 への回答は、この数で出す)。"""
    r, s = R[key], SPEC[key]
    a0, a1 = r["cu"] - r["hu"] - we, r["cu"] + r["hu"] + ee
    b0, b1 = r["cv"] - r["hv"] - s["eave"], r["cv"] + r["hv"] + s["eave"]
    area = (a1 - a0) * (b1 - b0)
    cov = 0.0
    for nb in ("honden", "haiden"):
        rn, sn = R[nb], SPEC[nb]
        c0, c1 = rn["cu"] - rn["hu"] - sn["eave"], rn["cu"] + rn["hu"] + sn["eave"]
        d0, d1 = rn["cv"] - rn["hv"] - sn["eave"], rn["cv"] + rn["hv"] + sn["eave"]
        cov += (max(0.0, min(a1, c1) - max(a0, c0))
                * max(0.0, min(b1, d1) - max(b0, d0)))
    print("  %s 屋根の平面 %.2f m²(東西 %.2f × 南北 %.2f)/ 隣の大屋根に呑まれる %.0f%%"
          % (key, area, a1 - a0, b1 - b0, 100.0 * min(1.0, cov / area)))
    return cov / area


def heiden(R, name=None):
    return _renketsu(R, "heiden", name or part_name(R, "heiden"), ebi=False)


def tsukuriai(R, name=None):
    return _renketsu(R, "tsukuriai", name or part_name(R, "tsukuriai"), ebi=True)


def kohai(R, name=None):
    """**向拝三間・出一間・軒唐破風**【S/U】。⛔ 木階は別部材(`kaidans[向拝の階]`)。"""
    global KARA_B
    name = name or part_name(R, "kohai")
    r, s = R["kohai"], SPEC["kohai"]
    hu, hv = r["hu"], r["hv"]
    KARA_B = hv                                 # 唐破風の半幅 = 向拝三間の半分
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    # 向拝柱(角柱の几帳面取りが常法だが、社殿に揃えて円柱)+ 礎盤
    vs = bay_lines(hv, r["nv"])
    sb = soban([(hu, vv) for vv in vs], s["floor"] - 0.10, s["floor"] + 0.12,
               0.26, name + "_soban")
    for vv in vs:
        cyl(M, hu, vv, s["floor"] + 0.12, s["floor"] + s["colH"], s["colD"] / 2.0,
            uv["wood"], W, n=12, taper=0.95)
    # 頭貫・台輪・組物(向拝は柱の上に平三斗)
    zt = s["floor"] + s["colH"]
    box3(M, hu - 0.10, hu + 0.10, vs[0] - 0.18, vs[-1] + 0.18, zt - 0.28, zt,
         uv["wood_h"], W, grain="v")
    box3(M, hu - 0.15, hu + 0.15, vs[0] - 0.28, vs[-1] + 0.28, zt, zt + 0.10,
         uv["wood_h"], W, grain="v")
    for vv in vs:
        box3(M, hu - 0.20, hu + 0.20, vv - 0.20, vv + 0.20, zt + 0.10, zt + 0.34,
             uv["wood_h"], W, grain="h")
        box3(M, hu - 0.12, hu + 0.12, vv - 0.52, vv + 0.52, zt + 0.34, zt + 0.52,
             uv["wood_h"], W, grain="v")
    # **海老虹梁** — 向拝柱の頭から拝殿の身舎へ反り上がる(向拝の見せ場)
    for vv in (vs[0], vs[-1], vs[1], vs[2]):
        kouryou(M, hu - 0.05, -hu - 0.10, vv, zt + 0.30, zt + 1.05, 0.17, 0.28,
                uv["wood_h"], W, sag=0.22)
    # 向拝の床(拝殿から続く縁の上に張る)
    n = max(2, int(round(2 * hv / 0.22)))
    for i in range(n):
        v0 = -hv + 2 * hv * i / float(n) + 0.006
        v1 = -hv + 2 * hv * (i + 1) / float(n) - 0.006
        box3(M, -hu, hu + 0.30, v0, v1, s["floor"] - 0.10, s["floor"], uv["wood"], W,
             grain="v")
    for (uu, vv) in [(hu + 0.20, x) for x in vs] + [(-hu + 0.20, x) for x in vs]:
        box3(M, uu - 0.07, uu + 0.07, vv - 0.07, vv + 0.07, 0.0, s["floor"] - 0.10,
             uv["wood"], W, grain="h")
    # ---- 庇 ----
    # ⭐ **上端 `ztop` は従属値**。⛔ 定数で持たない — 拝殿の軒の出が身舎半スパンの
    #   0.63【P 根津】まで深くなると、拝殿の軒は向拝をほぼ丸ごと覆う。⇒ 庇の上端は
    #   **拝殿の屋根面(拝殿東壁の位置)の 0.26 下**に差し込むのが唯一の納まり。
    #   低く置くと主屋根の軒との間に空の隙が開く(2026-09-09 に 5.14 で 1.7m 開いた)。
    ue = hu + s["eave"]
    hs = SPEC["haiden"]
    sori_h = Sori(R["haiden"]["hu"] + hs["eave"])
    ztop = eave_z("haiden") + sori_h.z(hs["eave"]) - 0.26
    sori = Sori(ue + hu)                        # 庇自身の反り(半スパン = 庇の全長)
    zeave = ztop - sori.z(ue + hu)              # ⇒ 軒先はそこから反って落ちた高さ
    print("  向拝の庇 上端 %.3f(拝殿の屋根面 %.3f の下)/ 軒先 %.3f"
          % (ztop, ztop + 0.26, zeave))
    # 庇の垂木。⛔ 一本の直材で結ばない(反った面は凸で、弦が瓦を突き抜ける)
    nt = max(2, int(round(2 * (hv + 0.6) / 0.34)))
    for i in range(nt + 1):
        vv = -(hv + 0.6) + 2 * (hv + 0.6) * i / float(nt)
        for j in range(3):
            d0 = (ue + hu + 0.30) * j / 3.0
            d1 = (ue + hu + 0.30) * (j + 1) / 3.0
            stick(M, (ue - d0, vv, zeave + sori.z(d0) - 0.11),
                  (ue - d1, vv, zeave + sori.z(d1) - 0.11),
                  0.08, 0.10, uv["wood_h"], W)
    # 丸桁 — 向拝柱の真上、庇の懐を通す。⛔ 省くと組物と屋根の間が空いて抜けて見える
    zg = zeave + sori.z(ue - hu)
    box3(M, hu - 0.13, hu + 0.13, vs[0] - 0.55, vs[-1] + 0.55, zg - 0.42, zg - 0.20,
         uv["wood_h"], W, grain="v")
    body = M.to_object(name + "_body", ms)
    roof = hisashi_karahafu(name + "_roof", hu, hv, s["eave"], zeave, -hu, ztop, p, sori)
    o = finish([body] + roof + sb, name)
    return o, zeave + kara_g(0.0, KARAHAFU)


def kizahashi(R, name=None):
    """**木階三級**【A 加藤重枝2018】。⛔ 石段にしない — 在庫の段石(`Dan_*`)を当てない。"""
    k = kizahashi_spec()
    name = name or kizahashi_name(k, R["_ken"])
    ms, uv = mats()
    M = VM.Mesh()
    du = abs(k["b"] - k["a"])                    # 東へ出る長さ
    hw = k["w"] / 2.0
    rise = k["rise"] / k["steps"]
    fumi = du / k["steps"]
    # 側桁(ささら桁)
    for sg in (-1, +1):
        vv = sg * (hw + 0.09)
        for i in range(k["steps"]):
            box3(M, i * fumi, du, vv - 0.07, vv + 0.07,
                 k["rise"] - (i + 1) * rise - 0.16, k["rise"] - i * rise - 0.02,
                 uv["wood"], W, grain="u")
    # 踏板 + 蹴込板
    for i in range(k["steps"]):
        zt = k["rise"] - (i + 1) * rise
        box3(M, i * fumi, (i + 1) * fumi + 0.04, -hw, hw, zt - 0.07, zt,
             uv["wood"], W, grain="v")
        box3(M, i * fumi - 0.02, i * fumi + 0.03, -hw, hw, zt, zt + rise - 0.07,
             uv["wood"], W, grain="v")
    # 束(踏板を受ける)
    for i in range(k["steps"]):
        zt = k["rise"] - (i + 1) * rise
        for sg in (-1, 0, 1):
            uu = (i + 0.6) * fumi
            vv = sg * hw * 0.72
            box3(M, uu - 0.05, uu + 0.05, vv - 0.05, vv + 0.05, 0.0, zt - 0.07,
                 uv["wood"], W, grain="h")
    o = M.to_object(name, ms)
    # ピボット = 階の平面の中心・地盤レベル(`kaidans.a`〜`b` の中点)
    V.set_origin(o, (BX(du / 2.0, 0.0)[0], BX(du / 2.0, 0.0)[1], 0.0))
    return o, k["rise"]


# ==========================================================================
# 検算(EDO-0161)— ⛔ 期待値は引数からでなくメッシュから立てる
# ==========================================================================
def _uv_of(o):
    return unity_verts(o)


def check_sym_z(o, name, tol=0.05):
    """南北(Unity Z)について棟が**中心に載っている**か。

    ⚠ **頂点集合の厳密な鏡映は使えない** — 瓦場は `floor(min/ピッチ)` から葺くので
      格子の原点が中心に乗らず、対称な屋根でも頂点は一致しない(実測して分かった)。
    ⇒ ⭕ **境界と重心**で測る。⛔ これは「南北に偏っていない」ことしか言わないので、
      **左右(東西)の別は `check_front_east` が別に見る**(EDO-0161)。"""
    uv = _uv_of(o)
    zs = [t[2] for t in uv]
    lo, hi = min(zs), max(zs)
    cen = sum(zs) / len(zs)
    ok = abs(lo + hi) < tol and abs(cen) < tol
    print("  検算 南北の中心(Unity Z) %-20s %s  Z[%.3f,%.3f] 端の和 %+.4f / 重心 %+.4f"
          % (name, "⭕" if ok else "⛔ 偏っている", lo, hi, lo + hi, cen))
    return ok


def check_front_east(o, name, kind):
    """**正面が東(Unity +X)を向いているか**を、メッシュそのものから立てた期待値で検める。
    ⛔ 引数(ug / eave / 区画)から期待値を作らない — 反転が復活すると検査も一緒にズレる。"""
    uv = _uv_of(o)
    ys = [t[1] for t in uv]
    y0, y1 = min(ys), max(ys)
    ok, msg = True, ""
    if kind == "chidori":
        # 屋根の上部(高さの上 45%)は、千鳥破風のぶんだけ **東へ偏る**
        band = [t for t in uv if t[1] > y0 + (y1 - y0) * 0.55]
        mx = sum(t[0] for t in band) / max(1, len(band))
        ok = mx > 0.10
        msg = "上部45%%の重心 X=%+.3f(千鳥破風は東に載る)" % mx
    elif kind == "downhill_east":
        # 庇は東へ流れ落ちる ⇒ **瓦場だけ**で東半分の平均高さ < 西半分
        # (躯体は柱も床も入るので均されて差が出ない)
        # ⚠ 材質名は **`Doukawara`**(2026-09-09 に銅瓦へ寄せた)。⛔ `roof` を探さない
        ridx = [i for i, m in enumerate(o.data.materials)
                if m and m.name.split('.')[0] == DOU_NAME]
        vids = set()
        for pg in o.data.polygons:
            if pg.material_index in ridx:
                vids.update(pg.vertices)
        e = [uv[i][1] for i in vids if uv[i][0] > 0.30]
        w = [uv[i][1] for i in vids if uv[i][0] < -0.30]
        if not e or not w:
            ok, msg = False, "東西の頂点が取れない"
        else:
            me, mw = sum(e) / len(e), sum(w) / len(w)
            ok = me < mw - 0.20
            msg = "東の平均高 %.3f < 西 %.3f" % (me, mw)
    elif kind == "steps_down_east":
        e = [t[1] for t in uv if t[0] > 0.20]
        w = [t[1] for t in uv if t[0] < -0.20]
        me, mw = sum(e) / len(e), sum(w) / len(w)
        ok = me < mw - 0.05
        msg = "東の平均高 %.3f < 西 %.3f(階は東へ降りる)" % (me, mw)
    elif kind == "door_east":
        # 舞良戸(`door wall`)は側面の**前方(東)二間**にしかない ⇒ 重心は東
        idx = [i for i, m in enumerate(o.data.materials) if m and m.name == "door wall"]
        vids = set()
        for p in o.data.polygons:
            if p.material_index in idx:
                vids.update(p.vertices)
        if not vids:
            ok, msg = False, "door wall の面が無い"
        else:
            mx = sum(uv[i][0] for i in vids) / len(vids)
            ok = mx > 0.20
            msg = "舞良戸の重心 X=%+.3f(前方=東の二間)" % mx
    elif kind in ("tuck_west", "tuck_east"):
        # 両下造の屋根は**隣の棟の軒下へ潜る**ぶんだけ片側へ伸びている。
        # 作り合いは西(本殿)へ、幣殿は東(拝殿)へ。⇒ bbox の偏りで向きが読める。
        # ⚠ 躯体(組物の肘木)が両側へ張り出すので**瓦場だけ**で測る。
        # ⚠ 材質名は **`Doukawara`**(2026-09-09 に銅瓦へ寄せた)。⛔ `roof` を探さない
        ridx = [i for i, m in enumerate(o.data.materials)
                if m and m.name.split('.')[0] == DOU_NAME]
        vids = set()
        for pg in o.data.polygons:
            if pg.material_index in ridx:
                vids.update(pg.vertices)
        if not vids:
            print("  検算 ⛔ 銅瓦の面が無い"); return False
        xs = [uv[i][0] for i in vids]
        skew = min(xs) + max(xs)
        want = -1 if kind == "tuck_west" else +1
        ok = skew * want > 0.30
        msg = ("X[%.2f,%.2f] の偏り %+.3f(%s の軒下へ潜る側へ伸びる)"
               % (min(xs), max(xs), skew, "西=本殿" if want < 0 else "東=拝殿"))
    print("  検算 正面=東(Unity +X) %-18s %s  %s" % (name, "⭕" if ok else "⛔", msg))
    return ok


def _roof_verts(o):
    """銅瓦の面に属する頂点だけを Unity ローカルで返す。
    ⛔ 躯体を混ぜない — 柱・床が入ると勾配が均されて反りが読めなくなる。"""
    uv = _uv_of(o)
    ridx = [i for i, m in enumerate(o.data.materials)
            if m and m.name.split('.')[0] == DOU_NAME]
    vids = set()
    for pg in o.data.polygons:
        if pg.material_index in ridx:
            vids.update(pg.vertices)
    return [uv[i] for i in vids]


def check_copper(o, name):
    """⭐ 屋根が **銅瓦1枚**で焼けているか。指定説明は【S】で銅瓦葺。"""
    names = [m.name.split('.')[0] for m in o.data.materials if m]
    bad = [n for n in names if n in COPPER_FROM]
    has = DOU_NAME in names
    ok = has and not bad and names.count(DOU_NAME) == 1
    print("  検算 銅瓦葺        %-20s %s  材 %s" % (name, "⭕" if ok else "⛔", names))
    return ok


def check_sori(o, name, axis='x', side=1, band=(0.0, 0.9), gap=0.12,
               skip=2, skip_e=0, nb=14):
    """⭐⭐ **屋根に反りが入っているか**を、焼いたメッシュそのものから測る。

    ⛔⛔ 期待値を `Sori` から作らない — 反りを外した回帰が入っても検算が一緒にズレて
      素通りする(規則19)。⇒ **銅瓦の面の天端の折れ線**を走り座標で刻み、
      **軒寄り4刻みの勾配 < 棟寄り4刻みの勾配** を要求する。
    ⚠ `band` / `side` / `skip` は **測る窓**であって期待値ではない。屋根には反り以外の
      起伏(千鳥破風・軒唐破風・寄棟の隅・大棟の冠瓦)が載っていて、混ぜると勾配が濁る:
        ・`side`  … 片流れだけを見る(拝殿は千鳥破風の無い**西**流れで測る)
        ・`band`  … 桁行のどの帯を見るか(max|other| に対する比。隅の寄棟面を外す)
        ・`skip`  … 大棟の冠瓦が載る内側の刻みを捨てる(棟が +0.3 持ち上がっている)
    陰性試験は `-- selftest`(`FLAT_TEST` で勾配を一定にすると必ず止まる)。"""
    pts = _roof_verts(o)
    if not pts:
        print("  検算 反り ⛔ 銅瓦の面が無い: %s" % name)
        return False
    ax = 0 if axis == 'x' else 2
    ot = 2 if axis == 'x' else 0
    mo = max(abs(p[ot]) for p in pts) + 1e-9
    A = [p for p in pts if side * p[ax] > 0.05
         and band[0] <= abs(p[ot]) / mo <= band[1]]
    if len(A) < 40:
        print("  検算 反り ⛔ 帯の中の頂点が %d しかない: %s" % (len(A), name))
        return False
    rs = [side * p[ax] for p in A]
    x0, x1 = min(rs), max(rs)
    # ⚠ 刻みは **瓦の段ピッチ(0.357m)より粗く**取る。細かく切ると頂点の無い刻みが出て
    #   折れ線が歯抜けになる(2026-09-09 に向拝で実見)。⇒ `nb` は棟ごとに与える。
    top = {}
    for p in A:
        b = int((side * p[ax] - x0) / (x1 - x0) * (nb - 1e-9))
        top[b] = max(top.get(b, -1e9), p[1])
    bs = sorted(b for b in top if b >= skip and b < nb - skip_e)
    if len(bs) < 6:
        print("  検算 反り ⛔ 刻みが埋まらない(%d): %s" % (len(bs), name))
        return False
    step = (x1 - x0) / nb

    def slope(seq):
        """最小二乗で勾配 = −dY/dr(走り座標が増えるほど軒へ向かうので符号を反転)。

        ⚠ **両端の2点で引かない。** 瓦は 1.785m ごとに段が上がる実ジオメトリなので、
          天端の折れ線は段のノコギリを持つ。窓が段の周期より短いと ±0.2 平気でずれる
          (2026-09-09 に実見)。⇒ 5刻み(≒1.6m)以上を最小二乗でならす。"""
        n = len(seq)
        mx = sum(seq) / float(n)
        my = sum(top[b] for b in seq) / float(n)
        den = sum((b - mx) ** 2 for b in seq)
        return -sum((b - mx) * (top[b] - my) for b in seq) / (den * step)

    win = max(3, min(6, len(bs) // 2))
    k_eave = slope(bs[-win:])        # 軒寄り
    k_ridge = slope(bs[:win])        # 棟寄り
    ok = k_eave < k_ridge - gap
    print("  検算 反り          %-20s %s  軒寄り %.3f < 棟寄り %.3f(差 %.3f ≥ %.2f)"
          % (name, "⭕" if ok else "⛔ 反りが無い", k_eave, k_ridge, k_ridge - k_eave, gap))
    return ok


def check_nokizori(o, name, lift_min=0.18, lip=0.45, nb=26):
    """⭐⭐ **軒先の稜線が隅で跳ね上がっているか**を、焼いたメッシュそのものから測る。

    ⛔ 期待値を `Nokizori` から作らない(規則19)。⇒ **銅瓦の面のうち最も東の唇**を
      南北(Unity Z)へ刻み、各刻みの**最下端 Y**(= 軒先の稜線)を拾って、
      **両端の刻み − 中央の刻み ≥ `lift_min`** を要求する。
    ⚠ これは考証19巡目が東立面の画素でやった測り方(左端/中央/右端の最下端)と同じ物差しを
      メッシュの上で回したもの。⛔ 立面の画素だけに頼らない — 立面は撮り方で変わる。"""
    pts = _roof_verts(o)
    if not pts:
        print("  検算 軒反り ⛔ 銅瓦の面が無い: %s" % name)
        return False
    xm = max(p[0] for p in pts)
    band = [p for p in pts if p[0] > xm - lip]          # 東の軒先の唇だけ
    if len(band) < 40:
        print("  検算 軒反り ⛔ 軒先の唇に頂点が %d しかない: %s" % (len(band), name))
        return False
    z0, z1 = min(p[2] for p in band), max(p[2] for p in band)
    low = {}
    for p in band:
        b = int((p[2] - z0) / (z1 - z0) * (nb - 1e-9))
        low[b] = min(low.get(b, 1e9), p[1])
    bs = sorted(low)
    if len(bs) < nb - 2:
        print("  検算 軒反り ⛔ 刻みが埋まらない(%d/%d): %s" % (len(bs), nb, name))
        return False
    mid = [low[b] for b in bs if abs(b - (nb - 1) / 2.0) <= nb * 0.12]
    cen = sum(mid) / len(mid)
    ls, rs = low[bs[0]], low[bs[-1]]
    ok = (ls - cen) >= lift_min and (rs - cen) >= lift_min
    print("  検算 軒反り        %-20s %s  南端 %+.3f / 北端 %+.3f(中央 %.3f 比・"
          "要 ≥ %.2f)" % (name, "⭕" if ok else "⛔ 隅が跳ね上がっていない",
                          ls - cen, rs - cen, cen, lift_min))
    return ok


def mirror_x(o):
    """陰性試験用: Unity X を鏡映する(= Blender X を鏡映する)。"""
    o.data.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    o.data.update()


# ==========================================================================
# レンダ(⭐ 組み上がりを東から見る。⛔ 部材1本ずつでは「神社に見えるか」が読めない)
# ==========================================================================
def place(o, du, dv):
    """論理 (du,dv)[m] だけ動かす(検証レンダ用の仮組み)。"""
    o.data.transform(Matrix.Translation((BX(du, dv)[0], BX(du, dv)[1], 0.0)))
    o.data.update()


def assemble(R, keys=("honden", "tsukuriai", "heiden", "haiden", "kohai"), kiza=True):
    """5棟 + 木階を指図の区画へ仮組みする(レンダ専用)。⭐ `keys` で焼いた棟だけに絞れる
    (2026-09-14 は幣殿・作り合いを起こさないので、その 8m は空いたまま写る)。
    返り値 = (オブジェクト列, 棟ごとの論理オフセット)。⭐ オフセットを返すのは、
    **棟を名指しで近景に撮る**ため(⛔ 画角を bbox の比だけで決めると軒の中へ入る)。"""
    objs = []
    ctr = {}
    ref = R["haiden"]
    for key, fn in (("honden", honden), ("tsukuriai", tsukuriai), ("heiden", heiden),
                    ("haiden", haiden), ("kohai", kohai)):
        if key not in keys:
            continue
        o, _top = fn(R)
        du, dv = R[key]["cu"] - ref["cu"], R[key]["cv"] - ref["cv"]
        place(o, du, dv)
        ctr[key] = (du, dv, R[key]["hu"], R[key]["hv"])
        objs.append(o)
    if kiza:
        k = kizahashi_spec()
        o, _ = kizahashi(R)
        place(o, (k["a"] + k["b"]) / 2.0 - ref["cu"], k["v"] - ref["cv"])
        objs.append(o)
    return objs, ctr


def shots(objs, tag="shaden", ctr=None):
    """⚠ **画角は bbox から決める。**原点を見て固定倍率で撮ると端が切れる
    (2026-09-09 に本殿と木階が枠外へ出た)。"""
    V.hook_textures()
    # ⛔⛔ **岩の材は `V.hook_textures()` では結線されない** — `M_FJG_Rock_001` は
    #   `V.named_material` が作った**名前だけの入れ物**で、Village Kit の textures/ にも
    #   同名の PNG が無い。⇒ 結ばないと亀腹・礎盤が **真っ白**に焼ける
    #   (2026-09-09 に実見。⚠ 検証レンダだけの話で、FBX は材質名しか運ばない)。
    import build_tateishi as BT
    BT.hook()
    # ⭕ `Kirishi`(切石)は `kirishi_material()` が作った時点で実テクスチャを結んである
    #   ⇒ ここで追加の結線は要らない。⛔ 「白く焼けたら remap 漏れ」と誤診しないこと。
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox(objs)
    cu = -(mn.x + mx.x) / 2.0            # 論理 u の中心(BX は符号反転)
    cv = -(mn.y + mx.y) / 2.0
    du, dv = mx.x - mn.x, mx.y - mn.y    # 東西・南北の全長
    top = mx.z
    bpy.ops.mesh.primitive_plane_add(size=240,
                                     location=((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0))
    out = []

    def one(cam, look, fn, ortho=None, res=(1800, 1150)):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_%s_%s.png" % (tag, fn))
        V.render(f); out.append(f)

    # ⭐ 正面(東)立面 — 千鳥破風と軒唐破風が重なって読めるか
    one(BX(cu + 70.0, cv) + (top * 0.50,), BX(cu, cv) + (top * 0.50,),
        "east_elev", ortho=max(dv, top * 1.55 / 1150 * 1800) * 1.08)
    # 東南から見下ろす 3D
    one(BX(cu + du * 1.15, cv - dv * 1.15) + (top * 1.30,),
        BX(cu, cv) + (top * 0.32,), "se3d")
    # 南面 — 権現造の一続き(H 型)の姿
    one(BX(cu, cv - 80.0) + (top * 0.50,), BX(cu, cv) + (top * 0.50,),
        "south_elev", ortho=max(du, top * 1.55 / 1150 * 1800) * 1.05)
    # 向拝まわりの近景(参拝者の目の高さ)。⚠ 中心からの比で置くと**軒の中へ入る**
    ue = -mn.x                                   # 論理 u の東端(BX は符号反転)
    one(BX(ue + 15.0, cv - 10.0) + (3.0,), BX(ue - 4.0, cv) + (5.2,),
        "kohai_near", res=(1700, 1200))
    # ⭐ **腰まわりの近景** — 石造亀腹(切石)と腰組は引きの立面では読めない。
    #   ⚠ 2026-09-08 の段石の縦縞は「引きの立面では読めず近景で初めて見えた」。同じ轍。
    #   ⚠ **拝殿が仮組みの原点**(`assemble` の `ref`)なので、論理座標を直に書ける。
    one(BX(8.6, -12.8) + (1.35,), BX(-0.4, -7.0) + (1.00,),
        "koshi_near", res=(1700, 1200))
    # ⭐ **本殿の南面の近景** — 考証20巡目 中6「舞良戸・板壁・脇障子が立面から読めない」。
    #   ⚠ 本殿は列の**西端**なので、`east_elev` にも `south_elev` にも**まともに写らない**
    #     (東は拝殿・幣殿に隠れ、南立面では 9.2m 先の面が引きで潰れる)。
    #   ⇒ 建具の可否は**面を名指しで撮って**答える(⛔ 引きの立面で「読めない」を「無い」と読まない)。
    if ctr and "honden" in ctr:
        du, dv, hhu, hhv = ctr["honden"]
        # ⚠ **軒の出 1.72m ＋ 縁 0.90m の外へ出るまで引く。**近すぎると軒の中へ入って
        #   面が読めない(2026-09-09 に 11.5m で軒下へ入った)。
        one(BX(du + 5.0, dv - 24.0) + (6.5,), BX(du + 0.5, dv - hhv) + (3.4,),
            "honden_south_near", res=(1700, 1200))
        one(BX(du - 24.0, dv - 4.0) + (6.5,), BX(du - hhu, dv - 0.5) + (3.4,),
            "honden_west_near", res=(1700, 1200))
    if ctr and "heiden" in ctr:
        du, dv, hhu, hhv = ctr["heiden"]
        one(BX(du + 1.0, dv - 22.0) + (6.0,), BX(du, dv - hhv) + (2.8,),
            "heiden_south_near", res=(1700, 1200))
    # 真上 — ⭐ 左右の別・棟の並びは俯瞰でしか読めない(EDO-0161)
    one(BX(cu, cv) + (top + 40.0,), BX(cu, cv) + (0.0,),
        "plan", ortho=max(du, dv) * 1.08, res=(1500, 1500))
    return out


# ==========================================================================
# 反りを **測る窓**(⛔ 期待値ではない。`check_sori` の註を読むこと)。
#   axis = 走り軸(Unity ローカル)。⚠ 幣殿・作り合いは大棟が東西なので流れは南北(Z)
#   side = どちらの流れを見るか。⭐ 拝殿は **千鳥破風の載らない西流れ**で測る
#   band = 桁行のどの帯か(隅の寄棟面・破風・唐破風の起りを外す)
SORI_WIN = dict(
    honden=dict(axis='x', side=+1, band=(0.10, 0.45)),   # 妻は |v|/vE=0.55 から外なので内側を見る
    haiden=dict(axis='x', side=-1, band=(0.35, 0.70)),   # 西流れ・千鳥破風(0.28)の外側
    # ⛔⛔ **向拝は None = 反りを「測っていない」。**⚠ 0件ではなく **未検査**であることを
    #   `build_one` が毎回 声に出す(規則19「輪に入っていない値は未検査であって合格ではない」)。
    #   理由: 庇には **軒唐破風の起り**(`bend`/`kara_g`・振幅 0.90m)が載っていて、これは
    #   反り(振幅 0.35m)より大きく、しかも軒寄りに重み付けされているので **反りと同じ形で
    #   同じ場所を持ち上げる**。起りが 0 になるのは |v| ≥ KARA_B の袖だけで、そこは瓦場の
    #   帯が 0.5m しかなく、走りの刻みが埋まらない(実測: 10刻み中 5つが空)。
    #   ⇒ **測れる窓が無い。**⛔ 起りを引き算して測らない — 期待値を生成器から作ることになる。
    #   ⭕ 庇の反りは他の4棟と同じ `Sori` / `sori_shear` を通っており(同じ道を通ることは
    #     コードで見える)、**向きは `downhill_east` が、納まりは `向拝の庇` の print が見ている**。
    kohai=None,
    heiden=dict(axis='z', side=+1, band=(0.00, 0.85)),
    tsukuriai=dict(axis='z', side=+1, band=(0.00, 0.85)),
)


# ⭐ 軒反り(隅の跳ね上がり)を **入れた棟**と、⛔ **入れていない棟とその理由**。
#   ⛔ 「入っていない」を黙らない — 0件は合格ではなく未測定(規則19)。
NOKI_CHECK = ("honden", "haiden")
# 大棟の走る軸(Unity ローカル)。⚠ 入母屋は南北(Z)・両下造は東西(X)。
#   向拝は大棟を持たない(軒唐破風の稜)ので 'z' を入れて**稜の頂**を刷るだけにする。
MUNE_AXIS = dict(honden='z', haiden='z', heiden='x', tsukuriai='x', kohai='z')
NOKI_NONE = dict(
    heiden="両下造で、東西の端は隣の棟の軒下へ潜る ⇒ **自由な隅が無い**",
    tsukuriai="両下造で、東西の端は隣の棟の軒下へ潜る ⇒ **自由な隅が無い**",
    kohai="庇の軒先には軒唐破風の起り(振幅 0.90m)が既に載っている。"
          "⚠ 隅を更に起こすと走り方向の勾配が折り返して瓦場が千切れる恐れがあり、"
          "**まだ試していない**【未検査】",
)


def build_one(R, key, do_render):
    fn = dict(honden=honden, tsukuriai=tsukuriai, heiden=heiden,
              haiden=haiden, kohai=kohai)[key]
    V.reset()
    o, top = fn(R)
    r = R[key]
    s = SPEC[key]
    note = ("← %s(%g×%g間 / 棟または反りの頂 %.3f m / 床 %.2f / 軒の出 %.2f / 軒高 %.2f)"
            % (r["name"], r["du"], r["dv"], top, s["floor"], s["eave"], eave_z(key)))
    report(o, o.name, note)
    check_sym_z(o, o.name)
    kind = dict(honden="door_east", haiden="chidori", kohai="downhill_east",
                tsukuriai="tuck_west", heiden="tuck_east")[key]
    if kind:
        if not check_front_east(o, o.name, kind):
            raise SystemExit("[shaden] ⛔ 正面が東を向いていない: %s" % o.name)
    if not check_copper(o, o.name):
        raise SystemExit("[shaden] ⛔ 屋根が銅瓦1枚で焼けていない: %s" % o.name)
    win = SORI_WIN[key]
    if win is None:
        print("  検算 反り          %-20s ⚠ **未検査**(測れる窓が無い。SORI_WIN の註)" % o.name)
    elif not check_sori(o, o.name, **win):
        raise SystemExit("[shaden] ⛔ 屋根に反りが無い: %s" % o.name)
    # ⭐ 軒反り(隅の跳ね上がり)。⛔ 入母屋の2棟だけ — 連結部・向拝には入れていない
    if key in NOKI_CHECK:
        if not check_nokizori(o, o.name):
            raise SystemExit("[shaden] ⛔ 軒先の稜線が隅で跳ね上がっていない: %s" % o.name)
    else:
        print("  検算 軒反り        %-20s ⚠ **未検査 = 入れていない**(%s)"
              % (o.name, NOKI_NONE[key]))
    # ⭐⭐ 棟飾りの丈(裁3)。目録 `docs/asset-index.tsv` の丈は**鬼の頂**を測っている
    mt, at, orn = mune_top(o, MUNE_AXIS[key])
    if mt is not None:
        print("  棟高の内訳         %-20s 瓦場の頂 %.3f / **大棟の上端 %.3f** / "
              "部材の Y 上端 %.3f ⇒ **棟飾りの丈 %.3f**"
              % (o.name, top, mt, at, orn))
    V.export_fbx([o], os.path.join(OUT, o.name + ".fbx"))
    print("[shaden] 書き出し " + os.path.join(OUT, o.name + ".fbx"))
    _ = do_render


def build_kizahashi(R):
    V.reset()
    o, rise = kizahashi(R)
    report(o, o.name, "← 木階三級(蹴上 %.3f)" % (rise / 3.0))
    check_sym_z(o, o.name)
    if not check_front_east(o, o.name, "steps_down_east"):
        raise SystemExit("[shaden] ⛔ 木階が東へ降りていない")
    V.export_fbx([o], os.path.join(OUT, o.name + ".fbx"))
    print("[shaden] 書き出し " + os.path.join(OUT, o.name + ".fbx"))


def selftest(R, keys=("honden", "tsukuriai", "heiden", "haiden", "kohai", "kizahashi")):
    """⛔ 0件は合格ではない。**鳴ることまで**確かめる(陰性試験)。
    ⭐ `keys` で焼いた棟だけに絞れる(`-- selftest honden haiden kohai kizahashi`)。"""
    print("=== 陰性試験: X を鏡映すると検算が止まるか === %s" % (list(keys),))
    bad = []
    for key, kind in (("haiden", "chidori"), ("kohai", "downhill_east"),
                      ("honden", "door_east"), ("tsukuriai", "tuck_west"),
                      ("heiden", "tuck_east")):
        if key not in keys:
            continue
        V.reset()
        o, _ = dict(honden=honden, haiden=haiden, kohai=kohai,
                    tsukuriai=tsukuriai, heiden=heiden)[key](R)
        if not check_front_east(o, o.name + "(正)", kind):
            bad.append(o.name + " 正で落ちた")
        mirror_x(o)
        if check_front_east(o, o.name + "(鏡映)", kind):
            bad.append(o.name + " 鏡映で通ってしまった")
    if "kizahashi" in keys:
        V.reset()
        o, _ = kizahashi(R)
        if not check_front_east(o, o.name + "(正)", "steps_down_east"):
            bad.append(o.name + " 正で落ちた")
        mirror_x(o)
        if check_front_east(o, o.name + "(鏡映)", "steps_down_east"):
            bad.append(o.name + " 鏡映で通ってしまった")
    if bad:
        raise SystemExit("[shaden] ⛔ 陰性試験に失敗: %s" % bad)
    print("=== 陰性試験 ⭕ 全て鏡映で止まった ===")

    # ---- 反りの陰性試験 ------------------------------------------------
    # ⛔ 0件は合格ではない。**反りを殺したときに `check_sori` が鳴る**ことまで確かめる。
    print("=== 陰性試験: 勾配を一定にすると反りの検算が止まるか ===")
    global FLAT_TEST
    bad = []
    for key in [k for k in ("haiden", "honden", "heiden", "kohai") if k in keys]:
        V.reset()
        o, _ = dict(honden=honden, haiden=haiden, heiden=heiden, kohai=kohai)[key](R)
        if SORI_WIN[key] and not check_sori(o, o.name + "(反りあり)", **SORI_WIN[key]):
            bad.append(o.name + " 正で落ちた")
        if not check_copper(o, o.name + "(正)"):
            bad.append(o.name + " 銅瓦の検算が正で落ちた")
    FLAT_TEST = True
    try:
        for key in [k for k in ("haiden", "honden", "heiden", "kohai") if k in keys]:
            V.reset()
            try:
                o, _ = dict(honden=honden, haiden=haiden, heiden=heiden,
                            kohai=kohai)[key](R)
            except SystemExit as e:
                # ⭕ これも「止まった」。⚠ 拝殿は勾配を殺すと **千鳥破風の浮きが 0.425 に
                #   落ちて `chidori_hafu` の関門が先に鳴る** — 反りを外すと納まり自体が
                #   壊れることの現れなので、素通りではなく合格として数える。
                print("  %s(勾配一定)⭕ 組み立ての関門が先に止めた: %s" % (key, e))
                continue
            if SORI_WIN[key] and check_sori(o, o.name + "(勾配一定)", **SORI_WIN[key]):
                bad.append(o.name + " 勾配一定で通ってしまった")
    finally:
        FLAT_TEST = False
    # ---- 軒反りの陰性試験 ----------------------------------------------
    # ⛔ 0件は合格ではない。**隅の持ち上げを殺したときに `check_nokizori` が鳴る**まで見る。
    print("=== 陰性試験: 隅の持ち上げを殺すと軒反りの検算が止まるか ===")
    global FLAT_NOKI
    for key in [k for k in NOKI_CHECK if k in keys]:
        V.reset()
        o, _ = dict(honden=honden, haiden=haiden)[key](R)
        if not check_nokizori(o, o.name + "(軒反りあり)"):
            bad.append(o.name + " 軒反りが正で落ちた")
    FLAT_NOKI = True
    try:
        for key in [k for k in NOKI_CHECK if k in keys]:
            V.reset()
            o, _ = dict(honden=honden, haiden=haiden)[key](R)
            if check_nokizori(o, o.name + "(隅を殺した)"):
                bad.append(o.name + " 隅を殺しても通ってしまった")
    finally:
        FLAT_NOKI = False
    # ---- 床の段の検算 --------------------------------------------------
    step = SPEC["honden"]["floor"] - SPEC["haiden"]["floor"]
    ok = step > 0.5 and abs(SPEC["heiden"]["floor"] - SPEC["haiden"]["floor"]) < 1e-6
    print("  検算 本殿の床の段  %s  本殿 %.2f − 拝殿 %.2f = %.2f / 幣殿 %.2f(拝殿と同床高)"
          % ("⭕" if ok else "⛔", SPEC["honden"]["floor"], SPEC["haiden"]["floor"],
             step, SPEC["heiden"]["floor"]))
    if not ok:
        bad.append("本殿の床が拝殿より上がっていない")
    if bad:
        raise SystemExit("[shaden] ⛔ 陰性試験に失敗: %s" % bad)
    print("=== 陰性試験 ⭕ 反りを殺すと全て止まった ===")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    pos = [a for a in argv if not a.startswith("--")]
    do_render = "--render" in argv
    what = pos[0] if pos else "all"
    R = rects()
    apply_floor(R)
    s0 = Sori(1.0)
    print("[shaden] 江戸間 1間 = %.3f m / 床 shadenFloor = %.2f m" % (R["_ken"], R["_floor"]))
    print("[shaden] 本殿の床 = %.2f m ← %s" % (R["_floor_honden"], R["_floor_honden_src"]))
    print("[shaden] 反り: 棟寄り %.3f(%.1f寸)→ 軒先 %.3f(%.1f寸)/ 平均 %.4f "
          "/ 軒の出 = 身舎半スパン × %.2f 【P 根津の実測】"
          % (s0.kr, s0.kr * 10, s0.ke, s0.ke * 10, s0.mean(), EAVE_RATIO))
    if what == "selftest":
        ks = [w for w in pos[1:]]
        selftest(R, keys=ks) if ks else selftest(R)
        return
    if what == "render":
        V.reset()
        objs, ctr = assemble(R)
        for f in shots(objs, ctr=ctr):
            print("RENDER " + f)
        return
    keys = ["honden", "tsukuriai", "heiden", "haiden", "kohai"]
    # ⭐ 複数の棟を並べて渡せる(`-- honden haiden kohai kizahashi`)。`all` は5棟+木階
    want = [w for w in pos if w in keys + ["kizahashi"]] if what != "all" else keys + ["kizahashi"]
    if not want:
        raise SystemExit("[shaden] ⛔ 棟の名が無い: %s" % pos)
    for key in R:
        if key in keys:
            r = R[key]
            print("[shaden] %-9s %d×%d間 柱間 東西 %.4f × 南北 %.4f m%s → %s"
                  % (key, r["nu"], r["nv"], r["pu"], r["pv"], "(旧 1間)" if r["legacy"] else "",
                     part_name(R, key)))
    for k in keys:
        if k in want:
            build_one(R, k, do_render)
    if "kizahashi" in want:
        build_kizahashi(R)
    if do_render:
        V.reset()
        objs, ctr = assemble(R, keys=[k for k in keys if k in want], kiza=("kizahashi" in want))
        for f in shots(objs, ctr=ctr):
            print("RENDER " + f)


if __name__ == "__main__":
    main()
