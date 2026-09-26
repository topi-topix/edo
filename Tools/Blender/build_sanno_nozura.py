"""山王社の前庭の縁の土留め — **野面の乱積み**(施主が試作 A を採った・2026-09-24)の本番モジュール。

    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall  [--grade=0] [--h=1.2] [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kiri  [--render]     # 根石の打ち切り(沈む駒)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- sode  [--only=男坂] [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- mikiri [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- all --render
    blender --background --python Tools/Blender/build_sanno_nozura.py -- check                 # 継ぎ目の一致を数で検める
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado [--h=1.5] [--render]   # 出隅 90° の隅の駒
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado-check [--h=1.5]  # 隅の駒の腕の先 = 直線の切り口
    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall --grade=0.22 --h=1.5  # 段の境の勾配の駒(± 両方)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- dan --render          # 段の境の並べ焼き
    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall --grade=set       # 前庭の天端を流す勾配の駒 ±0.12 × 8 段(2026-09-26)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- grade --render [--h=0.9]   # 勾配の駒の並べ焼き
    blender --background --python Tools/Blender/build_sanno_nozura.py -- crest [--dir=…] [--json=…]  # 全駒の背の天端の下がり(≤ 0.03)・頭の出(≤ 0)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- back --render         # 背の側(土の側)から撮る
    blender --background --python Tools/Blender/build_sanno_nozura.py -- nkiri --list=Tools/Blender/sanno_nozura_kiri_set.txt --render  # 片端を斜めの鉛直面で切った駒(女坂の袖に当てる・2026-09-26)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- mikiri_h [--h=1.5,1.8] --render   # 丈を合わせた見切り石(天端まで届く・2026-09-26)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- nnori --list=Tools/Blender/sanno_nozura_nori_set.txt --render  # 小口を相手の法 1:0.3 で切った短い駒(入隅の可動側の端・第3巡)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- sode_nori --keri=0.250 --fumi=0.542 [--e=-0.15] --render     # 背を相手の法 1:0.3 で切った野面の袖(第3巡)

試作は `proto_sanno_dodome.py`(絵だけ)。石の形(Voronoi の割り・割肌の面・円弧で切る頭・
面取り)はそこから起こし直した。⛔ 在庫に野面石・玉石が無い(試作の依頼時に在庫方が確認)ので新造。

━━━ 1. 壁の駒 `Sanno_Nozura_H<見付mm>_G<勾配‰>_<a|b|c|d>.fbx`(Models/Sanno)━━━━━━━━━━━━━━
【ピッチ】1間 = 1.818m。**両端の石(端の柱石の列)は全種類・全段で同じ形** ⇒ どの駒どうしでも継げる。
  端の石は継ぎ目の線(X = ±0.909)で**石の途中を切って**あり、隣の駒の半分と合わさって1石に見える
  (⛔ 継ぎ目で竪目地を通さない)。種類 a〜d は中の石だけが違う。並べるときは順に振る(繰り返しを隠す)。
【見付の段】0.15(根石1段)/ 0.30 / 0.60 / … / 2.40。**割りは天端から下へ測った一つの型**で、段の違いは
  下をどこで切るかだけ ⇒ **段の違う駒どうしも天端の線で継げる**(天端が揃えば目地も揃う)。
  見付 2.3 の所は 2.4 を 0.1 沈めて据える(下は地中)。
【勾配】駒を鉛直に剪断して天端を勾配に載せる(石段の袖と同じ・段に折らない)。G = 天端が Unity +X へ
  1m あたり上がる量(‰)。焼いてあるのは G0・根石の打ち切り(H0150 の G±180)・段の境(H1500 の G±220)・
  前庭の天端を流す G±120(H1800 を除く 8 段・2026-09-26 EDO-0437)。他の勾配は `--grade=` で足す。
【軸(Unity)】幅 = X / 高さ = Y / 厚み = Z、**見え面 = +Z**。面は 3分(0.3)の法 — **天端の線から測る**
  (段の違う駒どうしで面が食い違わないように)。
【ピボット】1間の中心(X=0)・**床レベル = 中心での天端 − 見付**(Y=0)・Z=0 は**天端の線での面**。
  ⇒ 床での面(法尻)は Z = +0.3×見付 に出る。石は床の 0.20 下まで根入れ(地中)。
  **見え面の頭は天端の線から下へ 0〜0.16 で不揃い(天端より上へ出さない)・背の列(面の輪 0.13 より奥)の上面は天端の線に揃う**
  (2026-09-25 EDO-0430: 背の頭が駒の最高より 0.1〜0.48 下がり、天端の高さの背の土が石に被って背の帯に溝ができた。
  天端の列の石は控え 0.75〜0.95・上の縁を天端へ上げ、目地の奥 0.30 に板)。`-- crest` が全駒の背の下がり ≤ 0.03 を検める。
  芝の肩は Unity の地形側で被せる前提。
【材】`Kirishi` / `Danishi`(山王の切石と同じ暖かい灰。石ごとに 7:3 で振り、色の個体差にする)。
  ⛔ 新規マテリアルなし。UV は石ごとの箱投影(1.05m で1枚・石ごとに位相をずらす)。
  裏に目地の奥を塞ぐ板(`Danishi`)を 0.12 奥に張る ⇒ 目地から空が抜けない。

━━━ 2. 根石の打ち切り = `H0150` の `G±180` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  見付 0.2 未満で壁を終える駒。頭が 1.818m の間に 0.33 下がるので、高い側の天端を隣(見付 0.30)に
  合わせれば先端の石は床へ沈む。G+180 = +X へ上がる(−X 側の端に置く)/ G−180 = +X へ下がる(+X 側の端)。

━━━ 2b. 出隅 90° の隅の駒 `Sanno_Nozura_Kado90_H<見付mm>_<a|b>.fbx`(2026-09-25・本殿の西の土留め)━━━━━
  腕1 = 稜線から −X へ 0.909(見え面 +Z)/ 腕2 = 稜線から −Z へ 0.909(見え面 +X)。高い側は X ≤ 0・Z ≤ 0。
  ピボット = **天端の線どうしの交点(稜線)・床レベル(天端 − 見付)**。腕の先の切り口 X = −0.909 / Z = −0.909 は
  直線の駒の切り口と同じ(端の石は同じ種・同じ形)⇒ 直線の駒をそのまま継ぐ。面は法で下ほど前へ出るので、
  割りは「稜線から面に沿って測る σ」で起こし(深さ u の面の幅 = 0.909 + 0.3·(−u))、稜線に跨る石だけ σ=0 で
  割線を入れて 90° に折る(控えは留めの線 x = z へ剪断・隠れる)。行ごとに稜線に跨る石を一つ置く ⇒ 竪目地が
  稜線を通らず、隅だけの石の柱(算木)にもならない。出隅は対称なので一種で両回り(yaw で腕を選ぶ)。

━━━ 2c. 段の境の勾配の駒 = `H1500` の `G±220` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  帯の面 29.65 → 29.25 の差 0.40 を 1間で流す(0.40 / 1.818 = 0.22)。見付は**高い側の端**で取る
  (29.65 − 境内 28.3 = 1.35 ⇒ 1.50)。中心の見付で取ると(1.15 ⇒ 1.20)高い側の根入れが 0.05 しか残らない。

━━━ 3. 石段の袖 `IshidanSodeNozura_<蹴上>_<踏面>_<a|b>.fbx`(Models/Kaidan)━━━━━━━━━━━━━
  **`Own.IshidanSode` と同じ局所座標・ピボット・接する面**(厚み X ±0.30 で両面とも乱積み・
  X について鏡像対称 / +Z = 坂下 / 天端 Y = 0.30 + (踏面/2 − Z)·蹴上/踏面 / 下端 = 天端 − 2.20 /
  走り Z ±踏面/2)。⇒ ビルダーは関数を差し替えるだけで据え方は変わらない。石は X = ±0.30 の面を越えない。
  頭の不揃いは天端の線から下へ 0〜3cm・頭の丸みは R1.2〜2.0(±8cm・R0.3 だと石段に沿う天端が鋸の歯に見えた)。笠石は持たない。
  ⛔ 曲がる女坂の留めの駒(`IshidanSodeMiter`)は未だ乱積みで起こしていない。

━━━ 4. 見切り石 `Sanno_Nozura_Mikiri.fbx` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  男坂の下で城の石垣と継ぐための大きな野面石1点。面 0.86 × 0.80・控え 0.90。
  ピボット = 面の芯・床レベル・Z=0 は天端での面(壁の駒と同じ取り方)。
  ⭐ 丈を合わせた版 `Sanno_Nozura_Mikiri_H<段mm>`(1.20〜2.10・2026-09-26): 見え 0.6 では据える所の見付 1.2〜1.6 に届かず、
  背の土が頭より 0.82/1.20 高く埋まった。大きな野面石 2〜3 石の柱で、最高 = 天端の線・背の上面は天端に揃う。据えは天端で合わせて沈める。

━━━ 5. 片端を斜めの鉛直面で切った駒 `Sanno_Nozura_Kiri<角×10><P|M><L|S>_H<見付mm>_<a|b>`(2026-09-26)━━━━━━━━━
  前庭の南の土留めの端が女坂の袖の外面に 43.2° で当たる(直の小口ではめり込み −0.55)。城の石垣の版(build_ishigaki_kiri.py)と
  同じ角・向きの取り方。切る面は天端の前の縁の端 (±0.909, 天端, 0) を通る ⇒ 天端の線では直線の駒と同じ 1間。枠の外へ出る石
  (L = 足の前・S = 控え)は隣の 1間の割り(次の個体・端の石は同じ)から採る。反対の端は直線の駒の継ぎ目と頂点まで同じ。
  ⚠ 斜めの面は bpy.ops.mesh.bisect で面から 0.036 外に頂点が残った ⇒ bmesh.ops.bisect_plane + holes_fill(切り口の辺だけ)。
  切り口に石の角だけ残る欠片(二辺とも 0.08 未満)は袖の面の前に浮いて見えたので落とす。

━━━ 6. 相手の法で切る駒(2026-09-26 EDO-0437 第3巡)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  鉛直な小口・背は、相手の野面の法(下ほど前へ出る)の楔へ縮めても入る(据えでは解けない)⇒ 駒の側を法で切る。
  法は 1:0.3(焼いた野面の前の包絡を段ごとに測っても 0.3 で平行・+0.065〜0.08 の出)。
  `Sanno_Nozura_Nori<P|M>_L<長さmm>_H<見付mm>_a`: 入隅の可動側の短い駒。天端の線で長さ L・切る端は e·X ≤ L/2 + 0.3·(Y − 見付)。
    反対の端は直線の駒の継ぎ目と同じ。⛔ 伸縮させない(法が変わる)⇒ 0.05 刻みで焼く。
  `IshidanSodeNozuraNori_<蹴上>_<踏面>_E±e_<a|b>`: 野面の袖の背(−Z)を Z = −踏面/2 − e − 0.3·(Y − Yc) で切る(膝 −0.60 より下は鉛直)。
    e > 0 は坂上へ次の個体を継いでから切る。切石の袖の `IshidanSodeNori`(build_sanno_buzai・1:0.25)と同じ e・Yc の取り方。
"""
import bpy, bmesh, sys, os, math, random
import mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
POS = [a for a in ARGS if not a.startswith("--")]
OPT = dict((a[2:].split("=", 1) + [""])[:2] for a in ARGS if a.startswith("--"))
RENDER = "render" in OPT

OUT_WALL = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
OUT_SODE = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Kaidan"))
SHOT = os.path.join(V.REPO, "Screenshots")
MATDIR = os.path.join(V.REPO, "Assets", "Edo", "Materials", "Sanno")

L = 1.818                 # 1間
TIERS = [0.15, 0.30, 0.60, 0.90, 1.20, 1.50, 1.80, 2.10, 2.40]
VARIANTS = "abcd"
BURY = 0.20               # 床より下の根入れ
DEEP = max(TIERS) + BURY  # 型の深さ(天端から)
BATTER = 0.3
HEAD = 0.08               # 頭の不揃い ±
KIRI_G = 0.180            # 根石の打ち切りの勾配(1間で 0.33 下がる ⇒ 先端の頭が床に沈む)
TILE = 1.05               # UV 1枚の実寸

# 石段の袖(`build_sanno_buzai` の SODE_* と同じ値。⛔ 変えると差し替えで据えがずれる)
SODE_HALF = 0.30
SODE_HT = 0.30
SODE_DEPTH = 2.20


# ------------------------------------------------------------------ 2D の道具
def clip(poly, n, c):
    """半平面 dot(p, n) <= c で凸多角形を切る"""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        dp = p[0] * n[0] + p[1] * n[1] - c
        dq = q[0] * n[0] + q[1] * n[1] - c
        if dp <= 0:
            out.append(p)
        if (dp < 0) != (dq < 0) and abs(dp - dq) > 1e-12:
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def area(poly):
    a = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        a += p[0] * q[1] - q[0] * p[1]
    return a / 2


def hull(pts):
    """凸包(反時計回り)"""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def head_arc(poly, sx, top, R):
    """頭を半径 R の円弧(5本の接線)で切る。u は上向き(0 = 天端の線)"""
    for a in (-0.75, -0.4, 0.0, 0.4, 0.75):
        n = (-math.sin(a), math.cos(a))
        cx, cu = sx, top - R
        poly = clip(poly, n, n[0] * cx + n[1] * cu + R)
        if len(poly) < 3:
            return poly
    return poly


def separate(poly, seed, obst, g):
    """凸の障害 obst から、種 seed の側へ g/2 離して切る(分離線 = 種が最も外に出る辺)"""
    best, bn, bc = -1e9, None, None
    m = len(obst)
    ccw = area(obst) > 0
    for i in range(m):
        p, q = obst[i], obst[(i + 1) % m]
        ex, ey = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(ex, ey)
        if ln < 1e-9:
            continue
        n = (ey / ln, -ex / ln) if ccw else (-ey / ln, ex / ln)     # 外向き
        d = (seed[0] - p[0]) * n[0] + (seed[1] - p[1]) * n[1]
        if d > best:
            best, bn, bc = d, n, p[0] * n[0] + p[1] * n[1]
    if bn is None:
        return poly
    # 残すのは dot(x, n) >= bc + g/2  ⇔  dot(x, -n) <= -(bc + g/2)
    return clip(poly, (-bn[0], -bn[1]), -(bc + g / 2))


# ------------------------------------------------------------------ 割り(天端から下へ一つの型)
def voronoi_cell(i, pts, g, box):
    """pts[i] の Voronoi 領域(目地 g)。box = (s0, s1, u0, u1)"""
    sx, su = pts[i]
    poly = [(box[0], box[2]), (box[1], box[2]), (box[1], box[3]), (box[0], box[3])]
    for j, (tx, tu) in enumerate(pts):
        if i == j or abs(tx - sx) > 1.3 or abs(tu - su) > 1.0:
            continue
        dx, du = tx - sx, tu - su
        d = math.hypot(dx, du)
        if d < 1e-9:
            continue
        n = (dx / d, du / d)
        poly = clip(poly, n, n[0] * (sx + tx) / 2 + n[1] * (su + tu) / 2 - g / 2)
        if len(poly) < 3:
            break
    return poly


def boundary_column(seed, depth, gw, cmax, rh=(0.26, 0.40), head=HEAD, rr=(0.16, 0.32)):
    """継ぎ目(s=0)に跨る端の石の列と、その左右の「番人」の種。**全種類・全段で同じ**(seed だけで決まる)。
    端の石は **端の種 + 番人の種だけ**の Voronoi 領域 ⇒ 中の石(種類ごとに違う)に形を左右されない。
    番人は s = c ± gw 付近に置き、中の石の種は番人より外にしか置かない。
    返す: (cols [(poly(s,u), key)], guards [(s,u)], bseeds [(s,u)])。u は上向き・天端 0。"""
    rng = random.Random(seed)
    bseeds, guards, heads = [], [], []
    u = 0.0
    k = 0
    while u > -depth - 0.3:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        c = (1 if k % 2 == 0 else -1) * rng.uniform(0.02, cmax)
        bseeds.append((c, uc))
        guards.append((c - gw * rng.uniform(0.85, 1.15), uc + rng.uniform(-0.08, 0.08)))
        guards.append((c + gw * rng.uniform(0.85, 1.15), uc + rng.uniform(-0.08, 0.08)))
        # ⭐ 頭は天端の線(u=0)から下へ 2×head の幅で不揃い(2026-09-25 EDO-0430: 天端より上へ出さない)
        heads.append((rng.uniform(-head, head) - head, rng.uniform(*rr), rng.uniform(0.022, 0.036)))
        u -= h_
        k += 1
    pts = bseeds + guards
    cols = []
    for ci in range(len(bseeds)):
        j8, R, g = heads[ci]
        poly = voronoi_cell(ci, pts, g, (-1.0, 1.0, -depth - 0.6, HEAD + 0.12))
        poly = head_arc(poly, bseeds[ci][0], j8, R) if len(poly) >= 3 else poly
        if len(poly) >= 3:
            cols.append((poly, "B%d" % ci))
    return cols, guards, bseeds


def layout(span, depth, bseed, vseed, wr=(0.25, 0.60), gw=0.40, bcmax=0.10, rh=(0.26, 0.40),
           head=HEAD, rr=(0.16, 0.32)):
    """1駒ぶんの石の輪郭(s ∈ [−span/2, +span/2]・u ∈ [−depth, +HEAD])。
    端の石の列(両端で同じ形)+ 番人 + 中の石(vseed ごとに違う)。返す [(poly, kind, key)]
    kind = 'B-' / 'B+'(左右の端の石)/ 'I'。key は石の乱数の種(端の石は左右で同じ)。"""
    cols, guards, bseeds = boundary_column(bseed, depth, gw, bcmax, rh, head, rr)
    ends, fixed, bpts = [], [], []
    for side, off in (("B-", -span / 2), ("B+", span / 2)):
        for poly, key in cols:
            ends.append(([(p[0] + off, p[1]) for p in poly], side, key))
        bpts += [(p[0] + off, p[1]) for p in bseeds]
        fixed += [(p[0] + off, p[1]) for p in guards if -span / 2 < p[0] + off < span / 2]
    rng = random.Random(vseed)
    var = []
    u = 0.0
    k = 0
    while u > -depth - 0.05:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        s = -span / 2 - rng.uniform(0, 0.3) - (0.2 if k % 2 else 0)
        while s < span / 2 + 0.3:
            w = rng.uniform(*wr)
            sx = s + w / 2 + rng.uniform(-0.05, 0.05)
            su = uc + rng.uniform(-0.05, 0.05)
            # 番人より外(継ぎ目から gw×1.3 以上)にだけ置く
            if -span / 2 + gw * 1.3 < sx < span / 2 - gw * 1.3 and su < -0.05:
                var.append((sx, su))
            s += w
        u -= h_
        k += 1
    seeds = fixed + var
    allp = seeds + bpts
    cells = []
    for i, (sx, su) in enumerate(seeds):
        g = rng.uniform(0.022, 0.040)
        poly = voronoi_cell(i, allp, g, (sx - 1.0, sx + 1.0, -depth - 0.3, HEAD + 0.12))
        if len(poly) < 3:
            continue
        poly = clip(poly, (1, 0), span / 2 - 0.02)
        poly = clip(poly, (-1, 0), span / 2 - 0.02)
        for op, side, key in ends:        # 端の石とわずかに重なる所を落とす
            if len(poly) < 3:
                break
            cx, cu = centroid(op)
            if abs(cx - sx) < 1.0 and abs(cu - su) < 1.0:
                poly = separate(poly, (sx, su), op, g)
        if len(poly) < 3:
            continue
        poly = head_arc(poly, sx, rng.uniform(-head, head) - head, rng.uniform(*rr))
        if len(poly) < 3 or area(poly) < 0.008:
            continue
        cells.append((poly, "I", "I%d" % i if i >= len(fixed) else "G%d" % i))
    return ends + cells


# ------------------------------------------------------------------ 材
def _stone_material(name, tint):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)          # ⛔ Unity 側の同名 .mat へ remap される入れ物
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs['Roughness'].default_value = 0.92
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = bpy.data.images.load(os.path.join(MATDIR, "T_Kirishi_Albedo.png"), check_existing=True)
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1
    nt.links.new(ti.outputs['Color'], mx.inputs[1]); mx.inputs[2].default_value = (tint, tint, tint, 1)
    nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])
    return m


def materials():
    return _stone_material("Kirishi", 1.0), _stone_material("Danishi", 0.80)


# ------------------------------------------------------------------ 石の塊
def stone_obj(name, poly, key_rng, P, depth, face_prot=(-0.02, 0.045), double=None, crest=None, lift_ds=None):
    """(s,u) の輪郭 → 野面の塊。P(s, u, d) が 3D を返す(d = 面から奥へ)。
    double = 厚み T なら両面を割肌にする(袖)。形の乱数は key_rng だけで決まる(端の石は左右で同じ)。
    crest = 天端の線の u(天端の列の石だけ渡す)⇒ 面から 0.13 奥の輪と背の輪の**上の縁(左端から右端まで上を回る点)を天端へ上げる**
    (背の上面が天端の線に揃う・見え面の頭の不揃いは面の輪だけに残る)。lift_ds(s, du) = 上げた点の s の寄せ
    (隅の駒: σ 空間では法の出が高さで変わるので、上げても 3D の位置が動かないよう σ を寄せる ── 寄せないと腕の先の切り口を越えた)。2026-09-25 EDO-0430: 背の頭が駒の最高より
    0.1〜0.48 下がり、天端の高さの背の土が石に被っていた。"""
    rng = key_rng
    cs, cu = centroid(poly)
    prot = rng.uniform(*face_prot)
    ta, tb = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.12)
    bm = bmesh.new()

    def face_d(s, u):
        return -prot + ta * (s - cs) - tb * (u - cu)

    n = len(poly)
    F = [bm.verts.new(P(s, u, face_d(s, u) + rng.uniform(-0.012, 0.018))) for (s, u) in poly]
    upper = set()
    if crest is not None:
        # 上の縁 = 右端から左端まで上を回る点の列(斜めの石も、その走りの全幅で背の天端が天端の線に届く ──
        # 重心より上だけ上げると、斜めの石の低い肩の上に下の段の石の頭が 0.09 下がって覗いた)
        iR = max(range(n), key=lambda i: (poly[i][0], poly[i][1]))
        iL = min(range(n), key=lambda i: (poly[i][0], -poly[i][1]))
        chains = []
        for step in (1, -1):
            c, i = [iR], iR
            while i != iL:
                i = (i + step) % n
                c.append(i)
            chains.append(c)
        upper = set(max(chains, key=lambda c: sum(poly[i][1] for i in c) / len(c)))

    def ring_s(i, s, u, k):
        ss = cs + (s - cs) * k
        return ss + lift_ds(s, crest - u) if (i in upper and lift_ds) else ss

    def ring_u(i, u, k, drop=0.0):
        if i in upper:
            return crest
        uu = cu + (u - cu) * k - drop
        return min(uu, crest) if crest is not None else uu
    M = [bm.verts.new(P(ring_s(i, s, u, 1.03), ring_u(i, u, 1.03), 0.13 - prot)) for i, (s, u) in enumerate(poly)]
    I = []
    for (s, u) in poly:
        ds, du = s - cs, u - cu
        dd = math.hypot(ds, du) or 1
        k = max(dd - 0.06, dd * 0.45) / dd
        si, ui = cs + ds * k, cu + du * k
        I.append(bm.verts.new(P(si, ui, face_d(si, ui) - rng.uniform(0.01, 0.03))))
    C = bm.verts.new(P(cs + rng.uniform(-0.04, 0.04), cu + rng.uniform(-0.03, 0.03),
                       face_d(cs, cu) - rng.uniform(0.015, 0.045)))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((C, I[i], I[j])))
        faces.append(bm.faces.new((I[i], F[i], F[j], I[j])))
        faces.append(bm.faces.new((F[i], M[i], M[j], F[j])))
    if double is None:
        ks = 0.97 if crest is not None else 0.80      # 天端の列は背でも幅を保つ(背の天端に隙を開けない)
        Bk = [bm.verts.new(P(ring_s(i, s, u, ks), ring_u(i, u, 0.80, 0.03), depth - prot)) for i, (s, u) in enumerate(poly)]
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((M[i], Bk[i], Bk[j], M[j])))
        faces.append(bm.faces.new(list(reversed(Bk))))
    else:
        T = double
        prot2 = rng.uniform(*face_prot)
        ta2, tb2 = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.12)

        def back_d(s, u):
            return T + prot2 - ta2 * (s - cs) + tb2 * (u - cu)
        F2 = [bm.verts.new(P(s, u, back_d(s, u) - rng.uniform(-0.012, 0.018))) for (s, u) in poly]
        M2 = [bm.verts.new(P(ring_s(i, s, u, 1.03), ring_u(i, u, 1.03), T - 0.13 + prot2)) for i, (s, u) in enumerate(poly)]
        C2 = bm.verts.new(P(cs + rng.uniform(-0.04, 0.04), cu, back_d(cs, cu) + rng.uniform(0.015, 0.04)))
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((M[i], M2[i], M2[j], M[j])))
            faces.append(bm.faces.new((M2[i], F2[i], F2[j], M2[j])))
            faces.append(bm.faces.new((F2[i], C2, F2[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    bv = o.modifiers.new("bevel", 'BEVEL')
    bv.width = 0.04; bv.segments = 2; bv.limit_method = 'ANGLE'
    bv.angle_limit = math.radians(28); bv.use_clamp_overlap = True; bv.profile = 0.6
    V.sel([o])
    bpy.ops.object.modifier_apply(modifier="bevel")
    return o


def box_uv(o, ofs):
    """石ごとの箱投影。座標は**石の重心から**測る(継ぎ目で切った端の石が左右の駒で同じ UV になる)"""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    c = sum((v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
    for p in me.polygons:
        nx, ny, nz = (abs(x) for x in p.normal)
        for li in p.loop_indices:
            q = me.vertices[me.loops[li].vertex_index].co - c
            if nz >= nx and nz >= ny:
                a, b = q.x, q.y
            elif nx >= ny:
                a, b = q.y, q.z
            else:
                a, b = q.x, q.z
            uvl[li].uv = (a / TILE + ofs[0], b / TILE + ofs[1])


TOP_ROW = 0.25            # 輪郭の最高が天端の線から これ以内の石 = 天端の列
TOP_DEPTH = (0.75, 0.95)  # 天端の列の控え ⇒ 背の帯(背から 0.5)が面の輪(0.13)より奥に収まる


def build_stones(cells, P, mats, depth_rng=(0.45, 0.75), double=None, face_prot=(-0.02, 0.045), tag="", crest=0.0,
                 lift_ds=None):
    """crest = 天端の線の u(None で揃えない)。天端の列の石(輪郭の最高 > crest − TOP_ROW)は背の上面を天端へ揃え、控えを TOP_DEPTH に。"""
    objs = []
    kir, dan = mats
    for poly, kind, key in cells:
        # ⭐ 端の石は key が左右で同じ ⇒ 形・控え・材・UV の位相まで同じ(継ぎ目で合わさる)
        rng = random.Random("nozura|%s|%s" % (tag, key))
        d = rng.uniform(*depth_rng)
        top = crest is not None and max(p[1] for p in poly) > crest - TOP_ROW
        if top:           # 乱数の消費は変えない(下の段の石の形・切り口を動かさない)
            d = TOP_DEPTH[0] + (d - depth_rng[0]) / (depth_rng[1] - depth_rng[0]) * (TOP_DEPTH[1] - TOP_DEPTH[0])
        o = stone_obj("st_" + key + kind, poly, rng, P, d, face_prot=face_prot, double=double,
                      crest=crest if top else None, lift_ds=lift_ds)
        o.data.materials.append(kir if rng.random() < 0.7 else dan)
        box_uv(o, (rng.random(), rng.random()))
        objs.append(o)
    return objs


def bisect_keep(o, co, no):
    """平面 co・法線 no の**裏側**(dot(x-co, no) <= 0)だけ残して口を塞ぐ。
    塞いだ口(小口)の UV は補間の崩れで縞になる(見切り石の脇で実見)⇒ 平面へ投影し直す。"""
    V.sel([o])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=co, plane_no=no, use_fill=True, clear_outer=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    me = o.data
    uvl = me.uv_layers.active.data
    n = Vector(no).normalized()
    c = Vector(co)
    ax = max(range(3), key=lambda k: abs(n[k]))
    a_, b_ = [k for k in range(3) if k != ax]
    for p in me.polygons:
        if p.normal.dot(n) > 0.99 and abs((p.center - c).dot(n)) < 1e-4:
            for li in p.loop_indices:
                q = me.vertices[me.loops[li].vertex_index].co
                uvl[li].uv = (q[a_] / TILE + 0.37, q[b_] / TILE + 0.11)


# ------------------------------------------------------------------ 壁の駒
def wall_name(h, g, v):
    gm = int(round(g * 1000))
    return "Sanno_Nozura_H%04d_G%s%03d_%s" % (int(round(h * 1000)), "+" if gm >= 0 else "-", abs(gm), v)


def wall_P(h, g):
    """(s = Unity X, u = 天端からの上向き, d = 面から奥へ) → Blender。
    Unity X = −Blender X / Unity Y = Blender Z / Unity Z = −Blender Y(README 書き出しの規約)。
    天端 Y = h + g·s。面(見え面 +Z)は天端の線から 3分で前へ出る: Unity Z = 0.3·(−u) − d。"""
    def P(s, u, d):
        return (-s, -(BATTER * (-u) - d), h + g * s + u)
    return P


BACK2 = (0.30, -0.005, -0.35)   # 天端の目地の奥の板: 面から 0.30 奥・天端の 0.005 下から 0.35 下まで


def backing(name, h, g, mat, d=0.12, u0=-0.12, u1=None):
    """目地の奥を塞ぐ板(既定: 面から 0.12 奥・天端の 0.12 下から床の下まで)。
    d, u0, u1 = BACK2 は天端の列の目地の奥の板(2026-09-25: 背の天端を天端の線へ上げたので、天端の目地が控えの奥まで
    素通しになり、土の無い側から空が抜けた ── 面の輪 0.13 より奥に張る)"""
    bm = bmesh.new()
    P = wall_P(h, g)
    vs = []
    for s in (-L / 2, L / 2):
        for u in (u0, -(h + BURY) if u1 is None else u1):
            vs.append(bm.verts.new(P(s, u, d)))
    # 法に沿わせる(u ごとに面が前へ出る分を足す)は P が持つ
    bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    # 見え面(−Blender Y)へ向ける
    me.update()
    if me.polygons[0].normal.y > 0:
        me.flip_normals()
    box_uv(o, (0.3, 0.7))
    return o


_LAYOUT = {}


def wall_cells(v):
    if v not in _LAYOUT:
        _LAYOUT[v] = layout(L, DEEP, "nozura-wall-B", "nozura-wall-" + v)
    return _LAYOUT[v]


def make_wall(h, g, v):
    V.reset()
    mats = materials()
    cells = []
    for poly, kind, key in wall_cells(v):
        p2 = clip(poly, (0, -1), h + BURY)            # u >= −(h+BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells.append((p2, kind, key))
    objs = build_stones(cells, wall_P(h, g), mats, tag="wall")
    objs.append(backing("back", h, g, mats[1]))
    objs.append(backing("back2", h, g, mats[1], *BACK2))
    name = wall_name(h, g, v)
    o = V.join(objs, name)
    bisect_keep(o, (-L / 2, 0, 0), (-1, 0, 0))        # Unity X ≤ +L/2 ⇔ Blender X ≥ −L/2
    bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))
    V.set_origin(o, (0, 0, 0))
    return o, name, len(cells)


# ------------------------------------------------------------------ 出隅 90° の隅の駒
KADO_VARIANTS = "ab"
KADO_TIERS = [t for t in TIERS if t >= 0.30]


def kado_name(h, v):
    return "Sanno_Nozura_Kado90_H%04d_%s" % (int(round(h * 1000)), v)


def cbat(u):
    """天端の線から u(上向き)の所で、法が面を前へ出す量"""
    return BATTER * (-u)


def kado_layout(v, depth=DEEP):
    """出隅の駒の割り。**σ = 面に沿って隅(稜線)から測った距離**(腕1 = −・腕2 = +)。
    面は法で下ほど前へ出るので、深さ u での面の幅は腕ごとに 0.909 + c(u)(c = 0.3·(−u))。
    ⇒ 継ぎ目の線は σ 空間で斜め(σ = ±(0.909 + c(u)))。端の石は直線の駒と**同じ種・同じ形**
    (`boundary_column("nozura-wall-B")`)を σ 空間へ剪断して置く(3D では剪断が消え、直線の駒の端の石と一致する)。
    隅(σ ≈ 0)には稜線に跨る石の列を置く ⇒ 竪目地が稜線を通らない。種の符号はばらばら(算木の互い違いにしない)。"""
    rh, gw = (0.26, 0.40), 0.40
    cols, guards, bseeds = boundary_column("nozura-wall-B", depth, gw, 0.10, rh, HEAD, (0.16, 0.32))
    W = lambda u: L / 2 + cbat(u)
    ends, fixed, bpts = [], [], []
    for side, sg in (("B-", -1), ("B+", 1)):
        for poly, key in cols:
            ends.append(([(p[0] + sg * W(p[1]), p[1]) for p in poly], side, key))
        bpts += [(p[0] + sg * W(p[1]), p[1]) for p in bseeds]
        for p in guards:
            q = (p[0] + sg * W(p[1]), p[1])
            if abs(q[0]) < W(q[1]):
                fixed.append(q)
    rng = random.Random("nozura-kado-" + v)
    # 行ごとに稜線に跨る種を一つ(σ ∈ ±0.06)置き、その行の他の種はそこから 0.30 以上離す
    # ⇒ 隅の石は行の中の一石として並ぶ(隅だけの石の柱にしない ── 算木の列に見える)
    corner, var = [], []
    u = 0.0
    k = 0
    while u > -depth - 0.05:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        w_ = W(uc)
        sc = rng.uniform(-0.06, 0.06)
        corner.append((sc, uc + rng.uniform(-0.05, 0.05)))
        s = -w_ - rng.uniform(0, 0.3) - (0.2 if k % 2 else 0)
        while s < w_ + 0.3:
            w = rng.uniform(0.25, 0.60)
            sx = s + w / 2 + rng.uniform(-0.05, 0.05)
            su = uc + rng.uniform(-0.05, 0.05)
            if abs(sx - sc) > 0.30 and abs(sx) < W(su) - gw * 1.3 and su < -0.05:
                var.append((sx, su))
            s += w
        u -= h_
        k += 1
    seeds = corner + fixed + var
    allp = seeds + bpts
    cells = []
    for i, (sx, su) in enumerate(seeds):
        g = rng.uniform(0.022, 0.040)
        poly = voronoi_cell(i, allp, g, (sx - 1.0, sx + 1.0, -depth - 0.3, HEAD + 0.12))
        if len(poly) < 3:
            continue
        # 継ぎ目の斜めの線(σ = ±W(u))の内へ: σ + 0.3u ≤ 0.889 / −σ + 0.3u ≤ 0.889
        poly = clip(poly, (1, BATTER), L / 2 - 0.02)
        poly = clip(poly, (-1, BATTER), L / 2 - 0.02)
        for op, side, key in ends:
            if len(poly) < 3:
                break
            cx, cu = centroid(op)
            if abs(cx - sx) < 1.0 and abs(cu - su) < 1.0:
                poly = separate(poly, (sx, su), op, g)
        if len(poly) < 3:
            continue
        poly = head_arc(poly, sx, rng.uniform(-HEAD, HEAD) - HEAD, rng.uniform(0.16, 0.32))
        if len(poly) < 3 or area(poly) < 0.008:
            continue
        kind = "C" if i < len(corner) else "I"
        cells.append((poly, kind, "K%s%d" % (v, i)))
    # 端の石は σ 空間の多角形でなく、直線の駒の座標(s)で返す(3D は直線の駒と同じ P で起こす)
    raw_ends = []
    for side, off in (("B-", -L / 2), ("B+", L / 2)):
        for poly, key in cols:
            raw_ends.append(([(p[0] + off, p[1]) for p in poly], side, key))
    return raw_ends, cells


def _u2b(x, y, z):
    """Unity → Blender(README 書き出しの規約: Unity X = −Bx / Y = Bz / Z = −By)"""
    return (-x, -z, y)


def _b2u(co):
    return (-co.x, co.z, -co.y)


def make_kado(h, v):
    """出隅 90° の駒。局所(Unity): 腕1 = 稜線から −X へ 0.909(見え面 +Z)/ 腕2 = 稜線から −Z へ 0.909(見え面 +X)。
    高い側(帯)は X ≤ 0・Z ≤ 0 の象限。ピボット = **天端の線の稜線(両腕の天端の線の交点)・床レベル(天端 − 見付)**。
    ⇒ 腕の先の切り口 X = −0.909 / Z = −0.909 が、直線の駒の切り口(±0.909)とそのまま一致する。
    作り: 石は σ 空間で平らに起こし(面取りまで)、稜線に跨る石だけ σ = 0 で割線を入れてから折る:
      腕1: (x, z) = (σ + c, z)  腕2: (x, z) = (z, −σ + c)   跨る石: (σ + z, z) / (z, −σ + z)(σ = 0 が留めの線 x = z)"""
    V.reset()
    mats = materials()
    raw_ends, cells = kado_layout(v)
    cut = lambda p: clip(p, (0, -1), h + BURY)
    objs = []
    # ① 端の石 ── 直線の駒と同じ鍵・同じ P(tag "wall")⇒ 形・材・UV の位相まで同じ
    ends = [(cut(p), k, key) for p, k, key in raw_ends]
    ends = [c for c in ends if len(c[0]) >= 3 and area(c[0]) > 0.004]
    for poly, side, key in ends:
        o = build_stones([(poly, side, key)], wall_P(h, 0.0), mats, tag="wall")[0]
        if side == "B+":           # 腕2 へ回す: (x, z) → (z, −x)
            for vt in o.data.vertices:
                x, y, z = _b2u(vt.co)
                vt.co = _u2b(z, y, -x)
        objs.append(o)
    # ② 中の石と隅の石 ── σ 空間(Unity X = σ・Z = c(u) − d)で起こして折る
    Pf = wall_P(h, 0.0)
    for poly, kind, key in cells:
        p2 = cut(poly)
        if len(p2) < 3 or area(p2) <= 0.004:
            continue
        smin, smax = min(p[0] for p in p2), max(p[0] for p in p2)
        # 上げた点は σ を稜線へ寄せる(3D の x = σ + 法の出 c(u) を保つ ⇒ 腕の先の切り口を越えない)
        o = build_stones([(p2, kind, key)], Pf, mats, tag="kado",
                         lift_ds=lambda s_, du: (BATTER if s_ < 0 else -BATTER) * du)[0]
        cross = smin < 0 < smax
        if cross:
            V.sel([o])
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(1, 0, 0), use_fill=False,
                                clear_inner=False, clear_outer=False)
            bpy.ops.object.mode_set(mode='OBJECT')
        arm1 = (smin + smax) < 0
        for vt in o.data.vertices:
            s, y, z = _b2u(vt.co)
            c = cbat(y - h)
            if cross:
                nx, nz = (s + z, z) if s <= 0 else (z, -s + z)
            elif arm1:
                nx, nz = s + c, z
            else:
                nx, nz = z, -s + c
            vt.co = _u2b(nx, y, nz)
        o.data.update()
        objs.append(o)
    # ③ 目地の奥を塞ぐ板(面から 0.12 奥・法に沿う)── 二枚が内の留めで閉じる
    for arm, (dd, u0, u1) in ((1, (0.12, -0.12, -(h + BURY))), (2, (0.12, -0.12, -(h + BURY))), (1, BACK2), (2, BACK2)):
        bm = bmesh.new()
        vs = []
        for u in (u0, u1):
            k = cbat(u) - dd
            if arm == 1:
                vs += [bm.verts.new(_u2b(-L / 2, h + u, k)), bm.verts.new(_u2b(k, h + u, k))]
            else:
                vs += [bm.verts.new(_u2b(k, h + u, k)), bm.verts.new(_u2b(k, h + u, -L / 2))]
        bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
        me = bpy.data.meshes.new("back%d" % arm); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("back%d" % arm, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(mats[1])
        me.update()
        nU = _b2u(me.polygons[0].normal)
        want = (0, 0, 1) if arm == 1 else (1, 0, 0)
        if nU[0] * want[0] + nU[2] * want[2] < 0:
            me.flip_normals()
        box_uv(ob, (0.3, 0.7))
        objs.append(ob)
    name = kado_name(h, v)
    o = V.join(objs, name)
    bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))          # Unity X ≥ −L/2 ⇔ Blender X ≤ +L/2
    bisect_keep(o, (0, L / 2, 0), (0, 1, 0))          # Unity Z ≥ −L/2 ⇔ Blender Y ≤ +L/2
    V.set_origin(o, (0, 0, 0))
    return o, name


def check_kado(h=1.50):
    """⭕ 隅の駒の腕の先の切り口 = 直線の駒の切り口(天端から 0.25 まで・1mm で丸め)"""
    ow, _, _ = make_wall(h, 0.0, "a")
    ref_p = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, -L / 2)}   # 直線の +X 端(Unity X = +0.909)
    ref_m = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, L / 2)}    # 直線の −X 端
    bad = 0
    for v in KADO_VARIANTS:
        o, name = make_kado(h, v)
        # 腕1 の先 = Unity X = −0.909 ⇔ Blender X = +0.909 ── 直線の +X 端と合わさる
        a1 = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(o, L / 2)}
        # 腕2 の先 = Unity Z = −0.909 ⇔ Blender Y = +0.909。直線の −X 端と比べるため (Blender X, Z) へ写す
        a2 = set()
        for vt in o.data.vertices:
            if abs(vt.co.y - L / 2) < 1e-4:
                # 腕2 の局所: 直線の駒の Unity Z = 腕2 の Unity X ⇒ Blender Y' = −(Unity X) = Blender X
                a2.add((round(vt.co.x, 3), round(vt.co.z - h, 3)))
        # 天端の列の石は控えが 0.75〜0.95(2026-09-25)⇒ もう一方の腕の端の石の尻がこの切り口(奥 0.909)で切られ、
        # 切り口の奥 0.6 より奥に小口の点が足される(隣の直線の駒の控えの中・土の下)。
        # ⇒ 直線の切り口の点は全て在ること(欠け 0)・足された点は奥 0.6 より奥だけ(余り 0)を検める
        top = lambda S: {p for p in S if p[1] > -0.25}
        d1 = len(top(ref_p) - top(a1)) + len({p for p in top(a1) - top(ref_p) if p[0] < 0.6})
        d2 = len(top(ref_m) - top(a2)) + len({p for p in top(a2) - top(ref_m) if p[0] < 0.6})
        print("NOZURA KADO CHECK %s: 腕1の先 %d点 差%d / 腕2の先 %d点 差%d(奥 0.6 より奥の小口 %d / %d 点)" % (
            name, len(top(a1)), d1, len(top(a2)), d2, len(top(a1) - top(ref_p)), len(top(a2) - top(ref_m))))
        bad += (d1 > 0) + (d2 > 0)
    return bad


# ------------------------------------------------------------------ 石段の袖
def sode_name(keri, fumi, v):
    return "IshidanSodeNozura_%.3f_%.3f_%s" % (keri, fumi, v)


def make_sode(keri, fumi, v, fresh=True):
    """`IshidanSode` と同じ枠。s = Unity Z(+ = 坂下)・天端 Y = 0.30 + (f/2 − s)·k/f。
    厚み X ±0.30 の両面を割肌に(d = +X 面から奥へ 0..0.60)。fresh=False は場を消さない(背を法で切る駒で隣の駒を継ぐ)。"""
    if fresh:
        V.reset()
    mats = materials()
    f = fumi
    cells = layout(f, SODE_DEPTH, "nozura-sode-B-%.3f" % f, "nozura-sode-%.3f-%s" % (f, v),
                   wr=(0.22, 0.45), gw=min(0.30, f * 0.36), bcmax=0.04,
                   head=0.015, rr=(1.2, 2.0))     # 袖の天端は石段に沿う一本の線 ⇒ 頭の不揃いは天端の下 3cm の幅・頭はほぼ平ら

    def P(s, u, d):
        # Unity X = +0.30 − d(両面)⇒ Blender X = −(0.30 − d)
        top = SODE_HT + (f / 2 - s) * keri / f
        return (-(SODE_HALF - d), -s, top + u)
    cells = [(clip(p, (0, -1), SODE_DEPTH), k, key) for p, k, key in cells]
    cells = [c for c in cells if len(c[0]) >= 3 and area(c[0]) > 0.004]
    objs = build_stones(cells, P, mats, double=2 * SODE_HALF, face_prot=(-0.04, -0.005),
                        tag="sode%.3f" % f)
    # 芯の板(両面の目地の奥を塞ぐ・X = ±0.18)
    for sx_ in (1, -1):
        bm = bmesh.new()
        vs = [bm.verts.new(P(s_, u_, SODE_HALF - sx_ * 0.18)) for s_, u_ in
              ((-f / 2, -0.10), (f / 2, -0.10), (f / 2, -SODE_DEPTH), (-f / 2, -SODE_DEPTH))]
        bm.faces.new(vs)
        me = bpy.data.meshes.new("core"); bm.to_mesh(me); bm.free()
        oc = bpy.data.objects.new("core", me); bpy.context.scene.collection.objects.link(oc)
        me.update()
        if me.polygons[0].normal.x * (-sx_) < 0:     # 外(Unity ±X)へ向ける
            me.flip_normals()
        oc.data.materials.append(mats[1]); box_uv(oc, (0.3, 0.6))
        objs.append(oc)
    # 天端の目地の奥の板(芯 X = 0・天端の 0.005 下から 0.35 下)── 背の天端を上げたので天端の目地が厚みを素通しになる(2026-09-25)
    for sx_ in (1, -1):
        bm = bmesh.new()
        vs = [bm.verts.new(P(s_, u_, SODE_HALF)) for s_, u_ in
              ((-f / 2, BACK2[1]), (f / 2, BACK2[1]), (f / 2, BACK2[2]), (-f / 2, BACK2[2]))]
        bm.faces.new(vs)
        me = bpy.data.meshes.new("core2"); bm.to_mesh(me); bm.free()
        oc = bpy.data.objects.new("core2", me); bpy.context.scene.collection.objects.link(oc)
        me.update()
        if me.polygons[0].normal.x * (-sx_) < 0:
            me.flip_normals()
        oc.data.materials.append(mats[1]); box_uv(oc, (0.3, 0.6))
        objs.append(oc)
    name = sode_name(keri, fumi, v)
    o = V.join(objs, name)
    # ⛔ 石は X = ±0.30 の面を越えない(段石の小口に突き付く面)
    for vt in o.data.vertices:
        vt.co.x = max(-SODE_HALF, min(SODE_HALF, vt.co.x))
    bisect_keep(o, (0, -f / 2, 0), (0, -1, 0))        # Unity Z ≤ +f/2
    bisect_keep(o, (0, f / 2, 0), (0, 1, 0))
    V.set_origin(o, (0, 0, 0))
    return o, name, len(cells)


# ------------------------------------------------------------------ 見切り石
def make_mikiri():
    V.reset()
    mats = materials()
    rng = random.Random("nozura-mikiri")
    w, hh = 0.86, 0.80
    poly = [(-w / 2 + 0.10, -hh), (w / 2 - 0.06, -hh), (w / 2, -hh + 0.15), (w / 2 - 0.02, -0.18),
            (w / 2 - 0.16, 0.0), (-w / 2 + 0.20, 0.02), (-w / 2, -0.20), (-w / 2 + 0.02, -hh + 0.12)]
    poly = head_arc(poly, 0.0, 0.0, 0.55)
    P = wall_P(hh - BURY, 0.0)   # 床から 0.60 見え・0.20 根入れ
    o = stone_obj("Sanno_Nozura_Mikiri", poly, rng, P, 0.90, face_prot=(0.0, 0.02))
    o.data.materials.append(mats[0])
    box_uv(o, (0.2, 0.4))
    V.set_origin(o, (0, 0, 0))
    return o, "Sanno_Nozura_Mikiri"


# ------------------------------------------------------------------ 斜めに切った端の駒(2026-09-26 EDO-0437)
NKIRI_CHIP = 0.08      # 切る面で残る石の欠片(二辺ともこれ未満)は落とす


def nkiri_name(deg, end, face, h, v):
    return "Sanno_Nozura_Kiri%03d%s%s_H%04d_%s" % (int(round(abs(deg) * 10)), end, face, int(round(h * 1000)), v)


def backing_span(name, h, mat, s0, s1, d=0.12, u0=-0.12, u1=None):
    """`backing` の走りの範囲を s0〜s1 にした板(2間に跨る駒・見切り石の幅の板)"""
    bm = bmesh.new()
    P = wall_P(h, 0.0)
    vs = []
    for s in (s0, s1):
        for u in (u0, -(h + BURY) if u1 is None else u1):
            vs.append(bm.verts.new(P(s, u, d)))
    bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    me.update()
    if me.polygons[0].normal.y > 0:
        me.flip_normals()
    box_uv(o, (0.3, 0.7))
    return o


def nkiri_plane(deg, end, face):
    """斜めに切る鉛直面(Blender の co, no)。残すのは dot(x − co, no) <= 0。
    Unity 局所で: 端 e = +1(P = +X 端)/ −1(M = −X 端)、k = +1(L = 見え面の側が長い)/ −1(S)。
    残す側 e·x <= L/2 + k·cot(deg)·z ── 天端の前の縁の端 (e·L/2, 天端, 0) を通る。"""
    e = 1 if end == "P" else -1
    k = 1 if face == "L" else -1
    cot = 1.0 / math.tan(math.radians(abs(deg)))
    return (-e * L / 2, 0.0, 0.0), (-e, k * cot, 0.0), e, k, cot


def make_nkiri(h, deg, end, face, v):
    """野面の乱積みの駒の片端を、走りと deg で交わる**鉛直な面**で切る(女坂の袖の外面に当てる端)。
    ⭐ 残る側(−e 端)は直線の駒と同じ継ぎ目(X = −e·0.909・端の石が同じ)⇒ 直線の駒をそのまま継ぐ。
    ⭐ 切る面は**天端の前の縁の端 = (e·0.909, 天端, 0)**を通る ⇒ 天端の線の上では直線の駒と同じ 1間。
       面(法)は下ほど前へ出るので、L は足の前が枠の外へ最大 0.3·(見付+0.2)·cot 出る / S は控えが枠の外へ出る。
       枠の外の石は隣の 1間(次の個体の割り・端の石は同じ)から採る ── 1間の枠の中だけだと切り口の奥に石が無い。"""
    V.reset()
    mats = materials()
    co, no, e, k, cot = nkiri_plane(deg, end, face)
    v2 = VARIANTS[(VARIANTS.index(v) + 1) % len(VARIANTS)]
    cells_a, cells_b = [], []
    for poly, kind, key in wall_cells(v):
        p2 = clip(poly, (0, -1), h + BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells_a.append((p2, kind, key))
    shared = "B+" if e > 0 else "B-"       # 隣の 1間の、共有する継ぎ目の側の端の石(= A の端の石と同じ形)は採らない
    for poly, kind, key in wall_cells(v2):
        if kind == ("B-" if e > 0 else "B+"):
            continue
        p2 = clip([(p[0] + e * L, p[1]) for p in poly], (0, -1), h + BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells_b.append((p2, kind, key))
    P = wall_P(h, 0.0)
    objs = build_stones(cells_a, P, mats, tag="wall")
    objs += build_stones(cells_b, P, mats, tag="wallK")
    s0, s1 = (-L / 2, L / 2 + L) if e > 0 else (-L / 2 - L, L / 2)
    objs.append(backing_span("back", h, mats[1], s0, s1))
    objs.append(backing_span("back2", h, mats[1], s0, s1, *BACK2))
    name = nkiri_name(deg, end, face, h, v)
    o = V.join(objs, name)
    # 継ぐ側(−e 端)は直線の駒と同じ切り口
    if e > 0:
        bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))        # Unity X >= −L/2
    else:
        bisect_keep(o, (-L / 2, 0, 0), (-1, 0, 0))      # Unity X <= +L/2
    # ⚠ 斜めの面は bpy.ops.mesh.bisect だと面から 0.036 外に頂点が残った(軸に沿う継ぎ目の面は合う)⇒ bmesh で切って口を塞ぐ
    n = Vector(no).normalized(); c = Vector(co)
    bm = bmesh.new(); bm.from_mesh(o.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                 plane_co=c, plane_no=n, clear_outer=True, clear_inner=False)
    cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge) and x.is_valid and x.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=cut, sides=0)["faces"]
    uvl = bm.loops.layers.uv.active
    t = Vector((n.y, -n.x, 0.0))
    for f in filled:
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        for l in f.loops:
            q = l.vert.co - c
            l[uvl].uv = (q.dot(t) / TILE + 0.37, q.z / TILE + 0.11)
    # bisect が面の脇に残す重複・孤立頂点を掃除(bounds が嘘をつく)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.delete(bm, geom=[x for x in bm.verts if not x.link_faces], context='VERTS')
    # 切る面で石の角だけが残った欠片(二辺とも CHIP 未満)は袖の面の前に浮いて見えた ⇒ 落とす(残る口は目地の幅)
    bm.verts.ensure_lookup_table()
    seen, drop = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        st, comp = [v0], []
        seen.add(v0.index)
        while st:
            a = st.pop(); comp.append(a)
            for ed in a.link_edges:
                b = ed.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); st.append(b)
        ext = sorted(max(q.co[i] for q in comp) - min(q.co[i] for q in comp) for i in range(3))
        if ext[1] < NKIRI_CHIP:
            drop += comp
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
    print("NKIRI 欠片を落とした 頂点 %d" % len(drop))
    bm.to_mesh(o.data); bm.free(); o.data.update()
    V.set_origin(o, (0, 0, 0))
    return o, name


def nkiri_ref_seam(h, deg, end, face, v):
    """直線の駒の、継ぐ側の切り口(天端から 0.25 まで)── make_wall は reset するので切る駒より先に呼ぶ"""
    e = 1 if end == "P" else -1
    ref_o, _, _ = make_wall(h, 0.0, v)
    return [(y, round(z - h, 3)) for y, z in seam_verts(ref_o, e * L / 2) if z > h - 0.25]


def check_nkiri(o, h, deg, end, face, v, ref_seam):
    """⭕ 切る面より外に頂点が無い / 継ぐ側の切り口 = 直線の駒の切り口 / 面の角 / 孤立頂点 / 背の天端"""
    co, no, e, k, cot = nkiri_plane(deg, end, face)
    n = Vector(no).normalized(); c = Vector(co)
    ok = []
    bite = max((vv.co - c).dot(n) for vv in o.data.vertices)
    ok.append(("切る面より外に頂点が無い", bite < 1e-4, "%.6f" % bite))
    on = [vv for vv in o.data.vertices if abs((vv.co - c).dot(n)) < 1e-4]
    ok.append(("切る面に頂点が乗る", len(on) >= 20, "%d 点" % len(on)))
    # 面の角を測り直す: 切る面の上の頂点を Unity (x, z) に直して一次式 x = a + b·z を当てる
    pts = [(-vv.co.x, -vv.co.y) for vv in on]
    if len(pts) >= 2:
        mz = sum(p[1] for p in pts) / len(pts); mx = sum(p[0] for p in pts) / len(pts)
        szz = sum((p[1] - mz) ** 2 for p in pts); sxz = sum((p[1] - mz) * (p[0] - mx) for p in pts)
        b = sxz / szz if szz > 1e-9 else 0.0
        ang = math.degrees(math.atan2(1.0, abs(b)))
        ok.append(("面の角 %.1f°" % deg, abs(ang - abs(deg)) < 0.05, "%.3f°" % ang))
        longer = "L" if e * b > 0 else "S"
        ok.append(("見え面の側が%s" % ("長い" if face == "L" else "短い"), longer == face, longer))
        x_at0 = mx - b * mz
        ok.append(("天端の前の縁の端 = 枠の端 %+.3f" % (e * L / 2), abs(x_at0 - e * L / 2) < 2e-3, "%+.4f" % x_at0))
    # 継ぐ側の切り口が直線の駒と同じ(天端から 0.25 まで・Blender X = e·L/2 が Unity の −e 端)
    xb = e * L / 2
    mine = [(y, round(z - h, 3)) for y, z in seam_verts(o, xb) if z > h - 0.25]
    ref = ref_seam
    diff = len(set(mine) ^ set(ref))
    ok.append(("継ぐ側の切り口 = 直線の駒 %s" % wall_name(h, 0.0, v), diff == 0 and len(ref) > 0, "%d 点・差 %d" % (len(ref), diff)))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats_ = sorted({m.name for m in o.data.materials})
    ok.append(("材は Kirishi / Danishi だけ", set(mats_) <= {"Kirishi", "Danishi"}, ",".join(mats_)))
    bpy.context.view_layer.update()
    back, over, at, npt = crest_check([o], lambda x, z: h, lambda x, z: z <= -FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    ok.append(("頭が天端の線より上へ出ない", over <= 0.005, "%+.3f" % over))
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    print("NKIRI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d / 天端の前の縁の端(局所) (%+.3f, %.3f, 0)" % (
        o.name, x0, x1, y0, y1, z0, z1, tris(o), e * L / 2, h))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


def read_nkiri_list(path):
    rows = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            tag, deg, end, face, hs = ln.split()
            for hh in hs.split(","):
                rows.append((tag, float(deg), end, face, float(hh)))
    return rows


# ------------------------------------------------------------------ 相手の法で切る駒(2026-09-26 EDO-0437 第3巡)
NNORI = BATTER            # 相手(野面の土留め・隅の駒)の面の法 = 3分。焼いた駒の前の包絡も 0.3(+0.065〜0.08 の出)で平行
NNORI_KNEE = -0.60        # 袖の背の法はこの高さ(袖の局所 Y)から上。下は鉛直(地中 ── 石段の袖の `sode_nori` と同じ)
NNORI_SODE_E = [-0.25, -0.20, -0.15, -0.10, -0.05, 0.00, 0.05]   # 背の出 e(0.05 刻み)。−0.30 は膝の下が痩せ切る


def bm_cut_keep(o, co, no, chip=NKIRI_CHIP, uv_ofs=(0.37, 0.11)):
    """平面 co・法線 no(Blender)の裏側(dot(x − co, no) <= 0)だけ残し、切り口を塞ぐ(斜めの面は bmesh で ── `make_nkiri` の教訓)。
    孤立頂点と、二辺とも chip 未満の欠片を落とす。塞いだ面の UV は面の上の平面投影。返り値 = 落とした欠片の頂点数。"""
    n = Vector(no).normalized(); c = Vector(co)
    bm = bmesh.new(); bm.from_mesh(o.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                 plane_co=c, plane_no=n, clear_outer=True, clear_inner=False)
    cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge) and x.is_valid and x.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=cut, sides=0)["faces"]
    uvl = bm.loops.layers.uv.active
    t = Vector((n.y, -n.x, 0.0)) if abs(n.z) < 0.99 else Vector((1.0, 0.0, 0.0))
    if t.length < 1e-6:
        t = Vector((1.0, 0.0, 0.0))
    t.normalize()
    b2 = n.cross(t).normalized()
    for f in filled:
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        for l in f.loops:
            q = l.vert.co - c
            l[uvl].uv = (q.dot(t) / TILE + uv_ofs[0], q.dot(b2) / TILE + uv_ofs[1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.delete(bm, geom=[x for x in bm.verts if not x.link_faces], context='VERTS')
    bm.verts.ensure_lookup_table()
    seen, drop = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        st, comp = [v0], []
        seen.add(v0.index)
        while st:
            a = st.pop(); comp.append(a)
            for ed in a.link_edges:
                b = ed.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); st.append(b)
        ext = sorted(max(q.co[i] for q in comp) - min(q.co[i] for q in comp) for i in range(3))
        if ext[1] < chip:
            drop += comp
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(drop)


# ---- (1) 小口を相手の法で切った短い駒 `Sanno_Nozura_Nori<P|M>_L<天端の長さmm>_H<見付mm>_<v>` ------------------
def nnori_name(ls, end, h, v):
    return "Sanno_Nozura_Nori%s_L%04d_H%04d_%s" % (end, int(round(ls * 1000)), int(round(h * 1000)), v)


def nnori_frame(ls, end):
    """e(+1 = P = 切る端が局所 +X)、割りの窓の中の切る端の s_e と窓の中心 s_c(1間の割りの座標)。
    窓 = 継ぐ側の端を 1間の継ぎ目(∓0.909)に置いた長さ ls ── 継ぐ側は直線の駒の切り口と頂点まで同じ。"""
    e = 1 if end == "P" else -1
    s_e = e * (ls - L / 2)
    s_c = -e * (L / 2 - ls / 2)
    return e, s_e, s_c


def make_nnori(ls, h, end, v):
    """野面の乱積みの短い駒の片端(小口)を**相手の法 1:0.3 の面**で切る(入隅の可動側の端が、通す側の見え面に当たる所)。
    局所(ピボット後): 走り X ∈ [−ls/2, +ls/2](天端の前の縁の長さ = ls)・切る端は e·X ≤ ls/2 + NNORI·(Y − h)
    (上ほど外へ ── 相手の面は下ほど前へ出る)。反対の端は直線の駒の継ぎ目と同じ切り口。見付 h・ピボット Y=0 = 天端 − h・
    Z=0 = 天端の線での面(見え面 +Z)は直線の駒と同じ。⛔ 伸縮させない(scale.x で法が変わる)。"""
    V.reset()
    mats = materials()
    e, s_e, s_c = nnori_frame(ls, end)
    cells = []
    for poly, kind, key in wall_cells(v):
        p2 = clip(poly, (0, -1), h + BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells.append((p2, kind, key))
    P = wall_P(h, 0.0)
    objs = build_stones(cells, P, mats, tag="wall")
    objs.append(backing("back", h, 0.0, mats[1]))
    objs.append(backing("back2", h, 0.0, mats[1], *BACK2))
    name = nnori_name(ls, end, h, v)
    o = V.join(objs, name)
    # 継ぐ側(−e 端)は直線の駒と同じ切り口
    if e > 0:
        bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))        # Unity X >= −L/2
    else:
        bisect_keep(o, (-L / 2, 0, 0), (-1, 0, 0))      # Unity X <= +L/2
    # 切る端: e·X ≤ e·s_e + NNORI·(Y − h) ⇔ Blender で dot(p − (−s_e, 0, h), (−e, 0, −NNORI)) ≤ 0
    nd = bm_cut_keep(o, (-s_e, 0.0, h), (-e, 0.0, -NNORI))
    print("NNORI 欠片を落とした 頂点 %d" % nd)
    # 窓の中心をピボットへ(Unity X −= s_c ⇔ Blender X += s_c)
    o.data.transform(mathutils.Matrix.Translation((s_c, 0.0, 0.0))); o.data.update()
    V.set_origin(o, (0, 0, 0))
    return o, name


def check_nnori(o, ls, h, end, v, ref_seam):
    """⭕ 法の面より外に頂点が無い / 面に頂点が乗る / 法 = NNORI / 天端の前の縁の端 = ±ls/2 / 継ぐ側の切り口 = 直線の駒 / 孤立頂点 / 材 / 背の天端"""
    e = 1 if end == "P" else -1
    ok = []
    U = [(-vv.co.x, vv.co.z, -vv.co.y) for vv in o.data.vertices]
    g = lambda x, y: e * x - (ls / 2 + NNORI * (y - h))           # > 0 = 面の外
    bite = max(g(x, y) for x, y, z in U)
    ok.append(("法の面より外に頂点が無い", bite < 1e-4, "%.6f" % bite))
    on = [(x, y) for x, y, z in U if abs(g(x, y)) < 1e-4]
    ok.append(("法の面に頂点が乗る", len(on) >= 20, "%d 点" % len(on)))
    if len(on) >= 2:
        my = sum(p[1] for p in on) / len(on); mx = sum(p[0] for p in on) / len(on)
        syy = sum((p[1] - my) ** 2 for p in on); sxy = sum((p[1] - my) * (p[0] - mx) for p in on)
        sl = e * sxy / syy if syy > 1e-9 else 0.0
        ok.append(("法 = 1:%.2f(実測 e·dX/dY)" % NNORI, abs(sl - NNORI) < 1e-3, "%.4f" % sl))
        x_top = mx + (h - my) * (sxy / syy if syy > 1e-9 else 0.0)
        ok.append(("天端の線での切る端 = %+.3f" % (e * ls / 2), abs(x_top - e * ls / 2) < 2e-3, "%+.4f" % x_top))
    xb = e * ls / 2                                    # 継ぐ側(Unity X = −e·ls/2)の Blender X
    mine = [(y, round(z - h, 3)) for y, z in seam_verts(o, xb) if z > h - 0.25]
    diff = len(set(mine) ^ set(ref_seam))
    ok.append(("継ぐ側の切り口 = 直線の駒 %s" % wall_name(h, 0.0, v), diff == 0 and len(ref_seam) > 0, "%d 点・差 %d" % (len(ref_seam), diff)))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats_ = sorted({m.name for m in o.data.materials})
    ok.append(("材は Kirishi / Danishi だけ", set(mats_) <= {"Kirishi", "Danishi"}, ",".join(mats_)))
    bpy.context.view_layer.update()
    back, over, at, npt = crest_check([o], lambda x, z: h, lambda x, z: z <= -FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    ok.append(("頭が天端の線より上へ出ない", over <= 0.005, "%+.3f" % over))
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    print("NNORI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d" % (o.name, x0, x1, y0, y1, z0, z1, tris(o)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


def read_nnori_list(path):
    """各行 `札 P|M 見付 長さ,長さ,…`(# 以降は註)"""
    rows = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            tag, end, hs, lens = ln.split()
            for ls in lens.split(","):
                rows.append((tag, end, float(hs), float(ls)))
    return rows


def render_nnori(ls, h, end, v):
    """短い駒の法で切った端を、通す側の土留め(直線の駒 H0.90・見え面を −e·X へ・天端を揃える)の見え面へ当てて撮る。
    相手の駒は法の包絡の出(0.075)だけ離す(= 据え手が触れている箇所で寄せた所)。反対の端に直線の駒 1 を継ぐ。"""
    e = 1 if end == "P" else -1
    V.reset()
    _import_at(os.path.join(OUT_WALL, nnori_name(ls, end, h, v) + ".fbx"), 0, 0, 0)
    _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "b") + ".fbx"), -e * (ls / 2 + L / 2), 0, 0)
    hw = 0.90
    _import_at(os.path.join(OUT_WALL, wall_name(hw, 0, "c") + ".fbx"), e * (ls / 2 + 0.075), L / 2, h - hw, -90.0 * e)
    hook_stone_textures()
    ground(0.0, -30, 30)
    _upper_ground(h, (-4 * L, 0.0) if e > 0 else (0.0, 4 * L), (-6.0, -0.25))
    tag = nnori_name(ls, end, h, v)
    studio_run([], _u2b(-e * 1.2, h + 0.9, 3.4), _u2b(e * ls * 0.3, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(-e * 1.2, h + 0.9, 3.4), _u2b(e * ls * 0.3, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + "_magenta.png"), magenta=True)
    # 真横(走りの向きの横 = 見え面から)から: 切る端の法が相手の面に沿うか
    for nm in ("Upper",):
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob)
    cam = bpy.context.scene.camera
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.4
    cam.location = _u2b(e * ls * 0.3, h * 0.5, 8.0)
    cam.rotation_euler = (Vector(_u2b(e * ls * 0.3, h * 0.5, 0.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(SHOT, tag + "_side.png"))


# ---- (2) 背を相手の法で切った野面の袖 `IshidanSodeNozuraNori_<蹴上>_<踏面>_E±x.xx_<v>` -------------------------
def sode_nnori_name(keri, fumi, e, v):
    return "IshidanSodeNozuraNori_%.3f_%.3f_E%s%.2f_%s" % (keri, fumi, "+" if e >= 0 else "-", abs(e), v)


def sode_nnori_yc(keri):
    """背の出 e を測る高さ(袖の局所 Y)= 石段の袖の `sode_nori_yc` と同じ((0.30 + 蹴上)/2)。"""
    return (SODE_HT + keri) / 2.0


def make_sode_nnori(keri, fumi, e, v, knee=NNORI_KNEE):
    """野面の袖 `make_sode(keri, fumi, v)` の坂上の端(背・−Z)を**相手(出隅の駒・土留め)の法 1:0.3** と平行な面で切る。
    背の面: Z = −踏面/2 − e − NNORI·(Y − Yc)(Yc = `sode_nnori_yc`)── 上ほど坂上へ出る。knee より下は鉛直(Z = 膝での値)。
    e > 0 は平らな駒より坂上へ出る(坂上に次の個体を継いで伸ばす ⇒ 天端・割りは一続き)/ e < 0 は詰める。"""
    V.reset()
    o0, _, _ = make_sode(keri, fumi, v, fresh=False)
    other = "b" if v == "a" else "a"
    o1, _, _ = make_sode(keri, fumi, other, fresh=False)
    o1.data.transform(mathutils.Matrix.Translation((0.0, fumi, keri))); o1.data.update()   # 坂上へ 1 駒(Unity Z −踏面・Y +蹴上)
    V.dedup_materials()
    name = sode_nnori_name(keri, fumi, e, v)
    whole = V.join([o0, o1], name)
    yc = sode_nnori_yc(keri)
    zk = -fumi / 2.0 - e - NNORI * (knee - yc)           # 膝での背の Z(Unity)
    # 部品 1: 膝の鉛直面より坂下(Unity Z ≥ zk ⇔ Blender Y ≤ −zk)
    p2 = whole.copy(); p2.data = whole.data.copy(); bpy.context.scene.collection.objects.link(p2)
    n1 = bm_cut_keep(whole, (0.0, -zk, 0.0), (0.0, 1.0, 0.0))
    # 部品 2: 膝より坂上(Unity Z ≤ zk)で、背の法の面より坂下(Unity Z ≥ −f/2 − e − NNORI·(Y − Yc))── 膝より上だけが残る
    n2 = bm_cut_keep(p2, (0.0, -zk, 0.0), (0.0, -1.0, 0.0))
    n3 = bm_cut_keep(p2, (0.0, fumi / 2.0 + e, yc), (0.0, 1.0, -NNORI))
    o = V.join([whole, p2], name)
    o.name = name; o.data.name = name
    # ⛔ 石は X = ±0.30 の面を越えない(`make_sode` と同じ)
    for vt in o.data.vertices:
        vt.co.x = max(-SODE_HALF, min(SODE_HALF, vt.co.x))
    V.set_origin(o, (0, 0, 0))
    print("SNORI 欠片を落とした 頂点 %d/%d/%d" % (n1, n2, n3))
    return o, name


def check_sode_nnori(o, keri, fumi, e, knee=NNORI_KNEE):
    ok = []
    U = [(-vv.co.x, vv.co.z, -vv.co.y) for vv in o.data.vertices]
    yc = sode_nnori_yc(keri)
    zb = lambda y: -fumi / 2.0 - e - NNORI * (max(y, knee) - yc)
    worst = max(zb(y) - z for x, y, z in U)
    ok.append(("背の法の面より坂上に頂点が無い", worst < 1e-4, "最大 %.5f" % worst))
    onb = [(y, z) for x, y, z in U if abs(z - zb(y)) < 1e-4 and y > knee + 0.05]
    ok.append(("背の法の面に頂点が乗る(膝より上)", len(onb) >= 8, "%d 点" % len(onb)))
    if len(onb) >= 2:
        my = sum(p[0] for p in onb) / len(onb); mz = sum(p[1] for p in onb) / len(onb)
        sl = sum((y - my) * (z - mz) for y, z in onb) / max(1e-9, sum((y - my) ** 2 for y, _ in onb))
        ok.append(("背の法 = 1:%.2f(実測 −dZ/dY)" % NNORI, abs(-sl - NNORI) < 1e-3, "%.4f" % -sl))
    ok.append(("坂下の端は平らな駒のまま Z=+踏面/2", abs(max(z for x, y, z in U) - fumi / 2) < 1e-4, "%.4f" % max(z for x, y, z in U)))
    ok.append(("石は X = ±0.30 を越えない", max(abs(x) for x, y, z in U) <= SODE_HALF + 1e-6, "%.4f" % max(abs(x) for x, y, z in U)))
    top = lambda z: SODE_HT + (fumi / 2.0 - z) * keri / fumi
    over = max(y - top(z) for x, y, z in U)
    ok.append(("天端が段鼻の線 +0.30 の斜めの一直線を越えない(≤ 0.005 ── 平らな野面の袖も 0.0015 出る)", over <= 0.005, "超過 %.5f" % over))
    kept_knee = fumi / 2.0 - (-fumi / 2.0 - e - NNORI * (knee - yc))
    ok.append(("膝の下に駒が残る(> 0.02)", kept_knee > 0.02, "%.3f" % kept_knee))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats_ = sorted({m.name for m in o.data.materials})
    ok.append(("材は Kirishi / Danishi だけ", set(mats_) <= {"Kirishi", "Danishi"}, ",".join(mats_)))
    bpy.context.view_layer.update()
    back, ov, at, npt = crest_check([o], lambda x, z: top(z), lambda x, z: abs(x) <= SODE_HALF - FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    print("SNORI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d" % (o.name, x0, x1, y0, y1, z0, z1, tris(o)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


def render_sode_nnori(keri, fumi, e, v, n=3):
    """背を切った袖 + 坂下へ平らな野面の袖 n−1 駒。背に相手(野面の直線の駒 H0.90・見え面 +Z・天端 = 袖の背の天端)を
    法の包絡の出(0.075)だけ離して据え、切り口が相手の面に沿うか撮る。"""
    V.reset()
    _import_at(os.path.join(OUT_SODE, sode_nnori_name(keri, fumi, e, v) + ".fbx"), 0, 0, 0)
    for i in range(1, n):
        vv = "ab"[("ab".index(v) + i) % 2]
        _import_at(os.path.join(OUT_SODE, sode_name(keri, fumi, vv) + ".fbx"), 0, fumi * i, -keri * i)
    hw = 0.90
    ytop = SODE_HT + keri                                # 平らな駒の背での天端
    yc = sode_nnori_yc(keri)
    zw = -fumi / 2.0 - e - NNORI * (ytop - yc) - 0.075   # 相手の天端の線での面
    _import_at(os.path.join(OUT_WALL, wall_name(hw, 0, "a") + ".fbx"), SODE_HALF - L / 2, zw, ytop - hw)
    hook_stone_textures()
    ground(-0.5, -30, 30)
    tag = sode_nnori_name(keri, fumi, e, v)
    studio_run([], _u2b(-2.6, ytop + 0.6, 2.6), _u2b(0.0, 0.0, -0.1), 30, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(-2.6, ytop + 0.6, 2.6), _u2b(0.0, 0.0, -0.1), 30, os.path.join(SHOT, tag + "_magenta.png"), magenta=True)
    cam = bpy.context.scene.camera
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.6
    cam.location = _u2b(-8.0, -0.2, 0.0)
    cam.rotation_euler = (Vector(_u2b(0.0, -0.2, 0.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(SHOT, tag + "_side.png"))


# ------------------------------------------------------------------ 丈を合わせた見切り石(2026-09-26 EDO-0437)
MIKIRI_TIERS = [1.20, 1.50, 1.80, 2.10]
MIKIRI_W = 0.86
MIKIRI_D = 0.90


def mikiri_name(h):
    return "Sanno_Nozura_Mikiri_H%04d" % int(round(h * 1000))


def make_mikiri_h(h):
    """見付 h の見切り石 ── 土留めの天端の線まで届く石の柱(大きな野面石 2〜3 石を不揃いの横目地で積む)。
    頭は天端の線から下へ 0〜0.08(円弧)・**背の上面は天端の線に揃う**(背の土 = 天端の高さが被らない)。
    座標は直線の駒と同じ(中心・床レベル・Z=0 は天端の線での面・見え面 +Z・3分の法)。根入れ 0.20。"""
    V.reset()
    mats = materials()
    rng = random.Random("nozura-mikiri-H%04d" % int(round(h * 1000)))
    w = MIKIRI_W
    total = h + BURY
    nst = 2 if h <= 1.55 else 3
    # 横目地の高さ(天端から下へ)── 石ごとの丈を 0.85〜1.15 で振る・目地は ±0.06 で傾ける
    wts = [rng.uniform(0.85, 1.15) for _ in range(nst)]
    cuts, acc = [], 0.0
    for wt in wts[:-1]:
        acc += wt / sum(wts) * total
        cuts.append((-acc + rng.uniform(-0.04, 0.04), rng.uniform(-0.06, 0.06)))
    g = 0.03
    cells = []
    for i in range(nst):
        poly = [(-w / 2, -total + 0.02), (w / 2, -total + 0.02), (w / 2, HEAD + 0.12), (-w / 2, HEAD + 0.12)]
        if i > 0:                       # 上の目地の下: u <= uc + sl·s − g/2
            uc, sl = cuts[i - 1]
            ln = math.hypot(sl, 1.0); n = (-sl / ln, 1.0 / ln)
            poly = clip(poly, n, uc / ln - g / 2)
        if i < nst - 1:                 # 下の目地の上: u >= uc + sl·s + g/2
            uc, sl = cuts[i]
            ln = math.hypot(sl, 1.0); n = (sl / ln, -1.0 / ln)
            poly = clip(poly, n, -uc / ln - g / 2)
        # 角を落とす(野面の輪郭)
        poly = clip(poly, (-1, 0), w / 2 - 0.02 - rng.uniform(0.0, 0.02))      # 輪の 1.03 倍の張り出しを見込む
        poly = clip(poly, (1, 0), w / 2 - 0.02 - rng.uniform(0.0, 0.02))
        for sx, su in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            cut = rng.uniform(0.06, 0.14)
            n = (sx / math.sqrt(2), su / math.sqrt(2))
            # 多角形の最も外の点から cut だけ内へ
            far = max(p[0] * n[0] + p[1] * n[1] for p in poly)
            if i == 0 and su > 0:
                continue                # 頭の角は円弧で落とす
            poly = clip(poly, n, far - cut)
        if i == 0:
            poly = head_arc(poly, rng.uniform(-0.08, 0.08), -rng.uniform(0.0, 0.02), rng.uniform(1.0, 1.4))
        cells.append((poly, "I", "M%d" % i))
    P = wall_P(h, 0.0)
    objs = []
    for poly, kind, key in cells:
        r2 = random.Random("nozura-mikiri|%s|%d" % (key, int(round(h * 1000))))
        top = max(p[1] for p in poly) > -TOP_ROW
        o = stone_obj("st_" + key, poly, r2, P, MIKIRI_D, face_prot=(0.0, 0.02), crest=0.0 if top else None)
        o.data.materials.append(mats[0] if r2.random() < 0.7 else mats[1])
        box_uv(o, (r2.random(), r2.random()))
        objs.append(o)
    objs.append(backing_span("back", h, mats[1], -w / 2 + 0.05, w / 2 - 0.05))
    name = mikiri_name(h)
    o = V.join(objs, name)
    V.set_origin(o, (0, 0, 0))
    return o, name


def check_mikiri_h(o, h):
    ok = []
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    ok.append(("最高 = 天端の線 %.2f" % h, abs(y1 - h) < 0.01, "%.3f" % y1))
    ok.append(("最下 = 床 − 根入れ", abs(y0 + BURY) < 0.06, "%.3f" % y0))
    ok.append(("幅 ≤ %.2f" % MIKIRI_W, x1 - x0 <= MIKIRI_W + 0.01, "%.3f" % (x1 - x0)))
    bpy.context.view_layer.update()
    back, over, at, npt = crest_check([o], lambda x, z: h, lambda x, z: z <= -FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    ok.append(("頭が天端の線より上へ出ない", over <= 0.005, "%+.3f" % over))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    print("MIKIRI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d 材=%s" % (
        o.name, x0, x1, y0, y1, z0, z1, tris(o), sorted({m.name for m in o.data.materials})))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


# ------------------------------------------------------------------ 測る・書く・撮る
def tris(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def unity_bounds(o):
    xs = [-v.co.x for v in o.data.vertices]; ys = [v.co.z for v in o.data.vertices]
    zs = [-v.co.y for v in o.data.vertices]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


REPORT = []


def export(o, name, outdir):
    path = os.path.join(outdir, name + ".fbx")
    V.export_fbx([o], path)
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    REPORT.append((name, tris(o), x0, x1, y0, y1, z0, z1))
    print("NOZURA %s tris=%d X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f]" % (name, tris(o), x0, x1, y0, y1, z0, z1))
    return path


def seam_verts(o, x_b, tol=1e-4):
    """Blender X = x_b の切り口に乗る頂点(Y,Z)の集合(1mm で丸め)"""
    return sorted({(round(v.co.y, 3), round(v.co.z, 3)) for v in o.data.vertices if abs(v.co.x - x_b) < tol})


def check():
    """⭕ 継ぎ目の一致を数で検める: どの種類・どの段でも、+X 端の切り口 = −X 端の切り口(上から共通の深さまで)"""
    res = []
    prof = {}
    for h in (0.30, 1.20, 2.40):
        for v in VARIANTS:
            o, name, _ = make_wall(h, 0.0, v)
            lo = [p for p in seam_verts(o, L / 2) if p[1] > h - 0.25]      # Unity −X 端(天端から 0.25)
            hi = [p for p in seam_verts(o, -L / 2) if p[1] > h - 0.25]     # Unity +X 端
            lo = [(y, round(z - h, 3)) for y, z in lo]; hi = [(y, round(z - h, 3)) for y, z in hi]
            prof[(h, v)] = (lo, hi)
    ref = prof[(1.20, "a")][1]
    bad = 0
    for k, (lo, hi) in prof.items():
        # 天端から測った切り口の頂点が、どの駒の −X 端とも・+X 端とも一致するか
        if set(lo) != set(ref) or set(hi) != set(ref):
            bad += 1
            res.append("⛔ %s: −X端 %d点 / +X端 %d点 / 基準 %d点 (差 %d / %d)" % (
                k, len(lo), len(hi), len(ref), len(set(lo) ^ set(ref)), len(set(hi) ^ set(ref))))
    print("NOZURA CHECK seam: %d/%d 不一致" % (bad, len(prof)))
    for r in res:
        print("NOZURA CHECK", r)
    return bad


# ------------------------------------------------------------------ 天端の帯の検査(2026-09-25 EDO-0430)
CREST_BAND = 0.15   # = EdoBuild.CREST_BAND
CREST_R = 0.6       # = EdoBuild.CREST_R
CREST_TOL = 0.03    # 背の天端の下がりの許し


def up_grid(objs, step=0.05):
    """Unity 局所の上向きの面(法線 y > 0.7)の最高を格子 {(i, j): Y} に刷る(i = X / step, j = Z / step)"""
    G = {}
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.data
        me.calc_loop_triangles()
        mw = o.matrix_world
        W = [mw @ v.co for v in me.vertices]
        for t in me.loop_triangles:
            a, b, c = (W[k] for k in t.vertices)
            n = (b - a).cross(c - a)
            if n.length < 1e-12 or n.z / n.length <= 0.7:        # Blender +Z = Unity +Y
                continue
            A, B, C = ((-p.x, -p.y, p.z) for p in (a, b, c))       # (Unity X, Unity Z, Unity Y)
            i0, i1 = math.floor(min(A[0], B[0], C[0]) / step), math.floor(max(A[0], B[0], C[0]) / step)
            j0, j1 = math.floor(min(A[1], B[1], C[1]) / step), math.floor(max(A[1], B[1], C[1]) / step)
            den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
            if abs(den) < 1e-14:
                continue
            for i in range(i0, i1 + 1):
                x = (i + 0.5) * step
                for j in range(j0, j1 + 1):
                    z = (j + 0.5) * step
                    l1 = ((B[1] - C[1]) * (x - C[0]) + (C[0] - B[0]) * (z - C[1])) / den
                    l2 = ((C[1] - A[1]) * (x - C[0]) + (A[0] - C[0]) * (z - C[1])) / den
                    l3 = 1 - l1 - l2
                    if l1 < -1e-9 or l2 < -1e-9 or l3 < -1e-9:
                        continue
                    y = l1 * A[2] + l2 * B[2] + l3 * C[2]
                    if G.get((i, j), -1e9) < y:
                        G[(i, j)] = y
    return G


FACE_ROW = 0.20      # 見え面(天端の線での面)からこれより奥 = 背の列(面の石の頭の不揃いの外)


def crest_check(objs, T, is_back, step=0.05):
    """⭕ 背の列の天端の下がり ── 上向きの面を 0.05 の格子に刷り、**背の列**(is_back(x, z))で**天端の帯**
    (周り CREST_R の円の中の最高から CREST_BAND 以内 = `EdoBuild` の篩と同じ。帯の外 = 目地に覗く下の段の石の頭は土に入るのが正しい)
    の点について 天端の線 T(x, z) − 上面 の最大(back)を、全点で 上面 − 天端の線 の最大(over = 前の頭が天端より上へ出ていないか)を返す。"""
    G = up_grid(objs, step)
    r = int(math.ceil(CREST_R / step))
    disc = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if (di * di + dj * dj) * step * step <= CREST_R ** 2]
    back, over, at, n = -1e9, -1e9, None, 0
    for (i, j), y in G.items():
        x, z = (i + 0.5) * step, (j + 0.5) * step
        t = T(x, z)
        over = max(over, y - t)
        if not is_back(x, z):
            continue
        mx = max(G.get((i + di, j + dj), -1e9) for di, dj in disc)
        if y < mx - CREST_BAND:
            continue
        n += 1
        if t - y > back:
            back, at = t - y, (round(x, 3), round(y, 3), round(z, 3))
    return back, over, at, n


def crest_spec(name):
    """FBX 名 → (天端の線 T(x, z)(Unity 局所), 背の列か is_back(x, z))"""
    import re
    m = re.match(r"Sanno_Nozura_H(\d{4})_G([+-]\d{3})_[a-d]$", name)
    if m:
        h, g = int(m.group(1)) / 1000, int(m.group(2)) / 1000
        return (lambda x, z: h + g * x), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"Sanno_Nozura_Kado90_H(\d{4})_[ab]$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: x <= -FACE_ROW and z <= -FACE_ROW)
    m = re.match(r"Sanno_Nozura_Kiri\d{3}[PM][LS]_H(\d{4})_[a-d]$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"Sanno_Nozura_Nori[PM]_L\d{4}_H(\d{4})_[a-d]$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"IshidanSodeNozuraNori_([\d.]+)_([\d.]+)_E[+-][\d.]+_[ab]$", name)
    if m:
        k, f = float(m.group(1)), float(m.group(2))
        return (lambda x, z: SODE_HT + (f / 2 - z) * k / f), (lambda x, z: abs(x) <= SODE_HALF - FACE_ROW)
    m = re.match(r"Sanno_Nozura_Mikiri_H(\d{4})$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"IshidanSodeNozura_([\d.]+)_([\d.]+)_[ab]$", name)
    if m:
        k, f = float(m.group(1)), float(m.group(2))
        # 袖は両面が見え面 ⇒ 両面の奥の芯(|X| ≤ 0.30 − 0.20)を背の列と読む
        return (lambda x, z: SODE_HT + (f / 2 - z) * k / f), (lambda x, z: abs(x) <= SODE_HALF - FACE_ROW)
    return None


def crest_all(dirs):
    """焼いた FBX を読み戻して全駒を測る(= Unity が読む物)。表を刷り、json を scratchpad へ"""
    import glob, json
    rows = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.fbx"))):
            name = os.path.splitext(os.path.basename(path))[0]
            sp = crest_spec(name)
            if sp is None:
                continue
            V.reset()
            before = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=path)
            objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
            bpy.context.view_layer.update()
            back, over, at, n = crest_check(objs, *sp)
            rows.append(dict(name=name, back=round(back, 4), over=round(over, 4), at=at, n=n))
            print("NOZURA CREST %-34s 背の下がり %+.3f 頭の出 %+.3f 点 %d 最悪 %s %s" % (
                name, back, over, n, at, "⭕" if back <= CREST_TOL and over <= 0.005 else "⛔"))
    bad = [r for r in rows if r["back"] > CREST_TOL or r["over"] > 0.005]
    print("NOZURA CREST 全 %d 駒: 背の下がりの最大 %+.3f / 頭の出の最大 %+.3f / ⛔ %d" % (
        len(rows), max(r["back"] for r in rows), max(r["over"] for r in rows), len(bad)))
    out = OPT.get("json")
    if out:
        json.dump(rows, open(out, "w"), ensure_ascii=False, indent=1)
    return len(bad)


def studio_run(objs, cam, look, lens=35, path=None, magenta=False):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.eevee.taa_render_samples = 48
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1) if magenta else (0.62, 0.70, 0.80, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.2; sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-40))
    sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new("Cam"); cd.lens = lens; cd.clip_start = 0.05
    c = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(c); sc.camera = c
    c.location = cam
    c.rotation_euler = (Vector(look) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
    V.render(path)


def place_copy(src_fbx, x_u, y_u):
    """FBX を読み、Unity (x, y) へ置く(検証レンダ用・Blender 座標へ戻す)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=src_fbx)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type == 'MESH':
            o.location.x += -x_u
            o.location.z += y_u
    return new


def ground(z=0.0, y0=-30, y1=0.5, name="Yard", col=(0.20, 0.26, 0.12)):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(-30, y0, z), (30, y0, z), (30, y1, z), (-30, y1, z)]]
    bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs['Base Color'].default_value = col + (1,)
    bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Specular IOR Level'].default_value = 0.0
    me.materials.append(m)
    return o


def hook_stone_textures():
    """読み込んだ FBX の Kirishi / Danishi にテクスチャを結ぶ(検証レンダ用)"""
    for m in bpy.data.materials:
        base = m.name.split(".")[0]
        if base not in ("Kirishi", "Danishi"):
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not b:
            continue
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.92
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = bpy.data.images.load(os.path.join(MATDIR, "T_Kirishi_Albedo.png"), check_existing=True)
        t = 1.0 if base == "Kirishi" else 0.80
        mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1
        nt.links.new(ti.outputs['Color'], mx.inputs[1]); mx.inputs[2].default_value = (t, t, t, 1)
        nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])


def render_wall_run(tag, magenta=False):
    """⭐ 焼いた FBX を読み戻して並べる(= Unity が読む物を撮る)。
    上段: 見付 1.2 を a,b,c,d,a,b,c と 7駒(継ぎ目・繰り返し)。
    下段: 天端の線を一本(Y = 0.9 → 勾配なしで段の違う駒を沈めて継ぐ)— 0.9,1.2,1.5,2.4,0.15 …"""
    V.reset()
    seq = "abcdabc"
    x0 = -3 * L
    for i, v in enumerate(seq):
        place_copy(os.path.join(OUT_WALL, wall_name(1.20, 0.0, v) + ".fbx"), x0 + i * L, 0.0)
    hook_stone_textures()
    ground()
    # 上の地面(天端の 0.10 上・頭の後ろ)
    ground(1.25, 0.25, 12, "Upper", (0.18, 0.24, 0.11))
    studio_run([], (-4.0, -8.5, 1.5), (0.5, 0, 0.7), 28,
               os.path.join(SHOT, "sanno_nozura_run%s.png" % tag), magenta)
    # 寄り(継ぎ目 x=±L/2 の2本が入る)
    studio_run([], (-0.6, -2.4, 1.3), (0.2, 0, 0.75), 30,
               os.path.join(SHOT, "sanno_nozura_seam%s.png" % tag), magenta)


def render_tier_mix(tag):
    """① 段の違う駒を天端の線で継ぐ: 天端 Y = 0.9 一定で 0.9/1.2/2.4/1.5/0.9 を沈めて並べる。
    ② 打ち切り: 天端 0.30 の駒の両端に根石の打ち切り(G±180)を継ぐ。"""
    V.reset()
    top = 0.9
    seq = [(0.90, "a"), (1.20, "b"), (2.40, "c"), (1.50, "d"), (0.90, "a")]
    x0 = -2 * L
    for i, (h, v) in enumerate(seq):
        place_copy(os.path.join(OUT_WALL, wall_name(h, 0, v) + ".fbx"), x0 + i * L, top - h)
    hook_stone_textures()
    ground()
    ground(top + 0.06, 0.45, 12, "Upper", (0.18, 0.24, 0.11))
    studio_run([], (-1.5, -6.0, 1.5), (0.0, 0, 0.55), 26, os.path.join(SHOT, "sanno_nozura_tiers%s.png" % tag))

    V.reset()
    top = 0.30
    xk = -2 * L
    # 左の打ち切り(+X へ上がる): 右端(s=+L/2)の天端を 0.30 に ⇒ 中心の天端 = 0.30 − 0.909·G
    items = [(wall_name(0.15, KIRI_G, "a"), top - 0.909 * KIRI_G - 0.15),
             (wall_name(0.30, 0, "b"), 0.0), (wall_name(0.30, 0, "c"), 0.0), (wall_name(0.30, 0, "d"), 0.0),
             (wall_name(0.15, -KIRI_G, "a"), top - 0.909 * KIRI_G - 0.15)]
    for i, (nm, y) in enumerate(items):
        place_copy(os.path.join(OUT_WALL, nm + ".fbx"), xk + i * L, y)
    hook_stone_textures()
    ground()
    studio_run([], (-0.5, -8.0, 1.5), (0.0, 0, 0.1), 26, os.path.join(SHOT, "sanno_nozura_kiri%s.png" % tag))


def render_sode(keri, fumi, name_tag, n=8):
    """袖の駒を段ごとに i%2 で並べ(天端が勾配の一直線に載るか)、坂の横から見る"""
    V.reset()
    for i in range(n):
        v = "a" if i % 2 == 0 else "b"
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(OUT_SODE, sode_name(keri, fumi, v) + ".fbx"))
        for o in [o for o in bpy.data.objects if o not in before and o.type == 'MESH']:
            # 段 i: Unity Z = −(i+0.5)·踏面(坂上へ)、Y = 蹴上·(i+1)
            o.location.y += (i + 0.5) * fumi
            o.location.z += keri * (i + 1)
    hook_stone_textures()
    ground(0.0, -30, 30)
    run = n * fumi
    studio_run([], (4.5, run * 0.5 - 1.0, 1.6 + keri * n * 0.5), (0, run * 0.5, keri * n * 0.55), 30,
               os.path.join(SHOT, "sanno_nozura_sode_%s.png" % name_tag))


def render_mikiri():
    V.reset()
    place_copy(os.path.join(OUT_WALL, "Sanno_Nozura_Mikiri.fbx"), 0.0, 0.0)
    place_copy(os.path.join(OUT_WALL, wall_name(0.60, 0, "a") + ".fbx"), -(L / 2 + 0.43), 0.0)
    hook_stone_textures()
    ground()
    studio_run([], (-0.8, -3.0, 1.4), (-0.4, 0, 0.35), 35, os.path.join(SHOT, "sanno_nozura_mikiri.png"))


def _import_at(path, x_u, z_u, y_u, yaw_u=0.0):
    """FBX を読み、Unity の yaw(度・+Z→+X が +90)で回して Unity (x, y, z) へ置く(検証レンダ用)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    R = mathutils.Matrix.Rotation(math.radians(-yaw_u), 4, 'Z')
    T = mathutils.Matrix.Translation(Vector(_u2b(x_u, y_u, z_u)))
    for o in new:
        o.matrix_world = T @ R @ o.matrix_world
    return new


def render_kado(h=1.50, tag=""):
    """隅の駒を直線の駒で挟んで撮る: 腕1 の先に直線 2駒(見え面 +Z)、腕2 の先に直線 2駒(yaw 90・見え面 +X)。
    隅の外(+X +Z)の低い地面と、帯(X ≤ 0・Z ≤ 0)の上の地面。"""
    for v in KADO_VARIANTS:
        V.reset()
        _import_at(os.path.join(OUT_WALL, kado_name(h, v) + ".fbx"), 0, 0, 0)
        for i, wv in enumerate("ab"):
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, wv) + ".fbx"), -L * (i + 1), 0, 0)
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "cd"[i]) + ".fbx"), 0, -L * (i + 1), 0, 90.0)
        hook_stone_textures()
        ground()
        # 帯の上(天端 + 0.06・X ≤ 0 かつ Z ≤ 0 ⇔ Blender X ≥ 0 かつ Y ≥ 0)
        bm = bmesh.new()
        vs = [bm.verts.new(q) for q in [(0.05, 0.05, h + 0.06), (12, 0.05, h + 0.06), (12, 12, h + 0.06), (0.05, 12, h + 0.06)]]
        bm.faces.new(vs); me = bpy.data.meshes.new("Upper"); bm.to_mesh(me); bm.free()
        ou = bpy.data.objects.new("Upper", me); bpy.context.scene.collection.objects.link(ou)
        mu = bpy.data.materials.new("Upper"); mu.use_nodes = True
        mu.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.18, 0.24, 0.11, 1)
        me.materials.append(mu)
        # 隅の外(対角)から
        studio_run([], _u2b(4.2, 1.7, 4.2), _u2b(-0.6, h * 0.5, -0.6), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s%s.png" % (v, tag)))
        studio_run([], _u2b(4.2, 1.7, 4.2), _u2b(-0.6, h * 0.5, -0.6), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s_magenta%s.png" % (v, tag)), magenta=True)
        # 腕1 の継ぎ目の寄り
        studio_run([], _u2b(-0.4, 1.2, 2.6), _u2b(-0.9, h * 0.5, 0), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s_seam%s.png" % (v, tag)))
        # 真上から(平面の留め)── 帯の地面を消す
        bpy.data.objects.remove(ou)
        sc = bpy.context.scene
        cam = sc.camera
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = 5.0
        cam.location = _u2b(-0.8, 8.0, -0.8); cam.rotation_euler = (0, 0, 0)
        V.render(os.path.join(SHOT, "sanno_nozura_kado_%s_plan%s.png" % (v, tag)))


def _flat_box(name, corners_u, col):
    """Unity の 8 隅(下 4 → 上 4・同じ回り)で箱を張る(検証レンダの相手役・書き出さない)"""
    bm = bmesh.new()
    vs = [bm.verts.new(_u2b(*c)) for c in corners_u]
    for f in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = col + (1,)
    me.materials.append(m)
    return o


def _upper_ground(h, xr, zr, name="Upper"):
    bm = bmesh.new()
    vs = [bm.verts.new(_u2b(x, h + 0.04, z)) for x, z in ((xr[0], zr[0]), (xr[1], zr[0]), (xr[1], zr[1]), (xr[0], zr[1]))]
    bm.faces.new(vs); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.18, 0.24, 0.11, 1)
    me.materials.append(m)
    return o


def render_nkiri(h, deg, end, face, v):
    """斜めに切った端の駒 + 直線の駒 2 を継ぎ、切る面に袖の外面の役の箱(灰)を当てて撮る"""
    co, no, e, k, cot = nkiri_plane(deg, end, face)
    V.reset()
    _import_at(os.path.join(OUT_WALL, nkiri_name(deg, end, face, h, v) + ".fbx"), 0, 0, 0)
    for i, wv in enumerate("cd"):
        _import_at(os.path.join(OUT_WALL, wall_name(h, 0, wv) + ".fbx"), -e * L * (i + 1), 0, 0)
    hook_stone_textures()
    ground(0.0, -30, 30)
    # 袖の外面の役: 切る面 x = e·L/2 + e·k·cot·z の外側 0.6
    nx, nz = e, -k * cot; ln = math.hypot(nx, nz); nx, nz = nx / ln, nz / ln
    tx, tz = e * k * cot, 1.0; lt = math.hypot(tx, tz); tx, tz = tx / lt, tz / lt
    pts = []
    for yy in (-0.3, h + 0.3):
        for a, b in ((-2.6, 0.0), (1.6, 0.0), (1.6, 0.6), (-2.6, 0.6)):
            pts.append((e * L / 2 + tx * a + nx * b, yy, tz * a + nz * b))
    _flat_box("Sode", pts, (0.55, 0.55, 0.52))
    # 背の地面(天端の高さ・駒の奥 Z ≤ −0.2)
    _upper_ground(h, (-4 * L, 3.0) if e > 0 else (-3.0, 4 * L), (-6.0, -0.25))
    tag = nkiri_name(deg, end, face, h, v)
    studio_run([], _u2b(-e * 1.5, h + 1.2, 4.6), _u2b(e * 0.6, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(e * 1.8, h * 0.5 + 0.4, 2.4), _u2b(e * 0.8, h * 0.45, 0.0), 30, os.path.join(SHOT, tag + "_near.png"))
    studio_run([], _u2b(-e * 1.5, h + 1.2, 4.6), _u2b(e * 0.6, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + "_magenta.png"), magenta=True)
    # 真上から(袖の箱と背の地面を消して、切り口が面に沿うか)
    for nm in ("Sode", "Upper"):
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob)
    cam = bpy.context.scene.camera
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 4.5
    cam.location = _u2b(e * 0.4, 10.0, 0.0); cam.rotation_euler = (0, 0, 0)
    V.render(os.path.join(SHOT, tag + "_plan.png"))


def render_mikiri_h(h):
    """丈を合わせた見切り石: −X に同じ見付の野面の駒 2、+X に城の石垣の役の箱(灰)・背の地面は天端の高さ"""
    V.reset()
    _import_at(os.path.join(OUT_WALL, mikiri_name(h) + ".fbx"), 0, 0, 0)
    for i, wv in enumerate("ab"):
        _import_at(os.path.join(OUT_WALL, wall_name(h, 0, wv) + ".fbx"), -(MIKIRI_W / 2 + L / 2 + i * L), 0, 0)
    hook_stone_textures()
    ground(0.0, -30, 30)
    xb = MIKIRI_W / 2
    _flat_box("Castle", [(xb, -0.3, 1.2), (xb + 3, -0.3, 1.2), (xb + 3, -0.3, -2.0), (xb, -0.3, -2.0),
                         (xb, h, 0.3 * 0.0), (xb + 3, h, 0.0), (xb + 3, h, -2.0), (xb, h, -2.0)], (0.55, 0.55, 0.52))
    _upper_ground(h, (-3 * L, xb), (-6.0, -0.25))
    tag = mikiri_name(h)
    studio_run([], _u2b(-0.4, h * 0.6 + 0.6, 4.2), _u2b(-0.5, h * 0.5, 0), 32, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(-2.2, h + 1.6, 2.4), _u2b(-0.2, h * 0.7, -0.3), 32, os.path.join(SHOT, tag + "_top.png"))


def render_dan(g=0.22, h=1.50):
    """段の境: 天端 T の直線 H1.50 → 勾配の駒(1間で 0.40 下がる)→ 天端 T − 0.40 の直線 H1.20。床は Y=0 の地面に沈める。"""
    V.reset()
    T = 1.35
    items = [(wall_name(1.50, 0, "a"), -L, T - 1.50),
             (wall_name(h, -g, "b"), 0.0, T - 0.909 * g - h),
             (wall_name(1.20, 0, "c"), L, T - 2 * 0.909 * g - 1.20),
             (wall_name(1.20, 0, "d"), 2 * L, T - 2 * 0.909 * g - 1.20)]
    for nm, x, y in items:
        place_copy(os.path.join(OUT_WALL, nm + ".fbx"), x, y)
    hook_stone_textures()
    ground()
    studio_run([], (-0.6, -5.5, 1.3), (-0.6, 0, 0.8), 30, os.path.join(SHOT, "sanno_nozura_dan.png"))
    studio_run([], (-0.6, -5.5, 1.3), (-0.6, 0, 0.8), 30, os.path.join(SHOT, "sanno_nozura_dan_magenta.png"), magenta=True)


def render_grade(g=0.12, h=0.90):
    """勾配の駒の並べ焼き(2026-09-26 EDO-0437): 天端の線が 平(H h)→ −g で 3間下がる → 平 と折れる所。
    勾配の駒は中心の天端を線に載せ、隣と切り口の天端を揃える(見付は据えた床の側で沈める)。床は Y=0 の地面に沈める。"""
    V.reset()
    T = h + 0.1
    seq = [(0.0, "a"), (-g, "b"), (-g, "c"), (-g, "d"), (0.0, "a")]
    x = -2 * L; top = T
    for gg, v in seq:
        c = top + gg * L / 2              # 中心の天端
        place_copy(os.path.join(OUT_WALL, wall_name(h, gg, v) + ".fbx"), x, c - h)
        top = top + gg * L; x += L
    hook_stone_textures()
    ground()
    studio_run([], (0.0, -7.5, 1.4), (0.0, 0, 0.6), 30, os.path.join(SHOT, "sanno_nozura_grade_%03d_H%04d.png" % (int(round(g * 1000)), int(round(h * 1000)))))
    studio_run([], (0.0, -7.5, 1.4), (0.0, 0, 0.6), 30,
               os.path.join(SHOT, "sanno_nozura_grade_%03d_H%04d_magenta.png" % (int(round(g * 1000)), int(round(h * 1000)))), magenta=True)
    # 寄り: 平 → 勾配の折れの継ぎ目(x = −1.5L)
    studio_run([], (-1.5 * L + 0.3, -2.6, T + 0.2), (-1.5 * L, 0, T - 0.3), 30,
               os.path.join(SHOT, "sanno_nozura_grade_%03d_H%04d_seam.png" % (int(round(g * 1000)), int(round(h * 1000)))))


def render_back(h=1.20):
    """背の側(土の側)から撮る(2026-09-25 EDO-0430): 直線 a〜d・勾配の駒・隅の駒を並べ、
    ① 土を 2cm 下げて(天端 − 0.02)── 背の天端に届かない石は土の下へ消え、帯に緑の穴が開く
    ② 土なし・マゼンタの背景 ── 背の上面の形"""
    for soil, tag in ((True, ""), (False, "_nosoil")):
        V.reset()
        for i, v in enumerate("abcd"):
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, v) + ".fbx"), -L * (i + 1), 0, 0)
        _import_at(os.path.join(OUT_WALL, kado_name(h, "a") + ".fbx"), 0, 0, 0)
        _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "b") + ".fbx"), 0, -L, 0, 90.0)
        hook_stone_textures()
        ground()
        if soil:
            bm = bmesh.new()
            vs = [bm.verts.new(q) for q in [(-0.3, 0.05, h - 0.02), (12, 0.05, h - 0.02), (12, 12, h - 0.02), (-0.3, 12, h - 0.02)]]
            bm.faces.new(vs); me = bpy.data.meshes.new("Soil"); bm.to_mesh(me); bm.free()
            ou = bpy.data.objects.new("Soil", me); bpy.context.scene.collection.objects.link(ou)
            mu = bpy.data.materials.new("Soil"); mu.use_nodes = True
            mu.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.10, 0.45, 0.08, 1)
            me.materials.append(mu)
        # 背の奥(Unity −Z)の高い所から、天端の帯を見下ろす
        studio_run([], _u2b(-4.5, h + 2.2, -4.0), _u2b(-3.0, h, -0.3), 30,
                   os.path.join(SHOT, "sanno_nozura_back%s.png" % tag), magenta=not soil)
        # 前から(見え面の頭の不揃い・目の高さ)
        if soil:
            studio_run([], _u2b(-3.5, 1.5, 4.5), _u2b(-3.0, h * 0.6, 0), 30,
                       os.path.join(SHOT, "sanno_nozura_front.png"))


# ------------------------------------------------------------------ 本体
def do_kado():
    hs = [float(OPT["h"])] if OPT.get("h") else KADO_TIERS
    for h in hs:
        for v in KADO_VARIANTS:
            o, name = make_kado(h, v)
            export(o, name, OUT_WALL)


# 前庭の縁の天端を流す勾配の駒(2026-09-26 EDO-0437)── 天端の勾配 0.03〜0.18 の区間(TW_Zentei_W / SE / E)。
#   勾配の段は 0 と ±0.12 の二つで足りる: 1間(伸縮 1.2 まで)の端で 天端の線 − 駒の天端 ≤ 0.065(裁定の頭の不揃い ±0.08 の内)。
#   0.15 は打ち切りの ±0.18・1.50 は段の境の ±0.22 も在る(`Own.SannoNozura` が最も近い勾配を引く)。1.80 は前庭の勾配の区間に無い。
GRADE_SET = [0.12, -0.12]
GRADE_TIERS = [0.15, 0.30, 0.60, 0.90, 1.20, 1.50, 2.10, 2.40]


def _floats(key, default):
    return [float(x) for x in OPT[key].split(",")] if OPT.get(key) else default


def do_wall():
    # --grade=0.12,-0.12 / --h=0.3,0.6 はカンマで並べられる。--grade=set は GRADE_SET × GRADE_TIERS
    if OPT.get("grade") == "set":
        grades, hs = GRADE_SET, (_floats("h", GRADE_TIERS))
    else:
        grades = _floats("grade", [0.0])
        hs = _floats("h", TIERS)
    for g in grades:
        for h in hs:
            for v in VARIANTS:
                o, name, n = make_wall(h, g, v)
                export(o, name, OUT_WALL)


def do_kiri():
    for g in (KIRI_G, -KIRI_G):
        for v in VARIANTS:
            o, name, n = make_wall(0.15, g, v)
            export(o, name, OUT_WALL)


def do_sode():
    import build_sanno_buzai as SB
    for nm, keri, fumi, w in SB.kaidan_specs(OPT.get("only") or None):
        # ⭐ 袖が焼けている石段(= 旧 `IshidanSode_<蹴上>_<踏面>_a` がある組)だけ差し替える
        old = os.path.join(OUT_SODE, "IshidanSode_%.3f_%.3f_a.fbx" % (keri, fumi))
        if not os.path.exists(old) and not OPT.get("only"):
            continue
        for v in "ab":
            o, name, n = make_sode(keri, fumi, v)
            export(o, name, OUT_SODE)
        if RENDER:
            render_sode(keri, fumi, nm)


def do_mikiri():
    o, name = make_mikiri()
    export(o, name, OUT_WALL)


if __name__ == "__main__":
    what = POS[0] if POS else "all"
    if what == "check":
        sys.exit(1 if check() else 0)
    if what == "crest":
        # blender ... -- crest [--dir=<FBX の置き場>] [--json=<出力>] ── 全駒の背の天端の下がり(≤ 0.03)と頭の出(≤ 0)
        sys.exit(1 if crest_all([OPT["dir"]] if OPT.get("dir") else [OUT_WALL, OUT_SODE]) else 0)
    if what == "kado-check":
        sys.exit(1 if check_kado(float(OPT.get("h") or 1.5)) else 0)
    if what == "kado":
        do_kado()
        if RENDER:
            render_kado(float(OPT.get("h") or 1.5))
    if what == "back" and RENDER:
        render_back(float(OPT.get("h") or 1.2))
    if what == "dan" and RENDER:
        render_dan()
    if what == "grade" and RENDER:
        # blender ... -- grade --render [--h=0.9] ── 勾配の駒の並べ焼き(焼いてから)
        for hh in _floats("h", [0.90]):
            render_grade(abs(GRADE_SET[0]), hh)
    if what == "nkiri":
        # blender ... -- nkiri --list=Tools/Blender/sanno_nozura_kiri_set.txt [--render] ── 斜めに切った端の駒(女坂の袖に当てる)
        lp = OPT.get("list") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanno_nozura_kiri_set.txt")
        lp = lp if os.path.isabs(lp) else os.path.join(V.REPO, lp)
        bad = 0
        made = []
        for tag_, deg_, end_, face_, h_ in read_nkiri_list(lp):
            for v_ in "ab":
                ref_ = nkiri_ref_seam(h_, deg_, end_, face_, v_)
                o, name = make_nkiri(h_, deg_, end_, face_, v_)
                bad += check_nkiri(o, h_, deg_, end_, face_, v_, ref_)
                export(o, name, OUT_WALL)
                made.append((h_, deg_, end_, face_, v_))
                print("NKIRI 書き出し %s ← %s" % (name, tag_))
        if RENDER:
            for (h_, deg_, end_, face_, v_) in made:
                if v_ == "a":
                    render_nkiri(h_, deg_, end_, face_, v_)
        if bad:
            sys.exit("NKIRI ⛔ 検算が %d 件落ちた" % bad)
    if what == "nnori":
        # blender ... -- nnori --list=Tools/Blender/sanno_nozura_nori_set.txt [--render] ── 小口を相手の法で切った短い駒(入隅の可動側の端)
        lp = OPT.get("list") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanno_nozura_nori_set.txt")
        lp = lp if os.path.isabs(lp) else os.path.join(V.REPO, lp)
        bad = 0
        made = []
        for tag_, end_, h_, ls_ in read_nnori_list(lp):
            for v_ in (OPT.get("v") or "a").split(","):
                ro, _, _ = make_wall(h_, 0.0, v_)
                ref_ = [(y, round(z - h_, 3)) for y, z in seam_verts(ro, (1 if end_ == "P" else -1) * L / 2) if z > h_ - 0.25]
                o, name = make_nnori(ls_, h_, end_, v_)
                bad += check_nnori(o, ls_, h_, end_, v_, ref_)
                export(o, name, OUT_WALL)
                made.append((ls_, h_, end_, v_))
                print("NNORI 書き出し %s ← %s" % (name, tag_))
        if RENDER:
            for (ls_, h_, end_, v_) in made:
                if OPT.get("shots") is None or ("%.2f" % ls_) in OPT["shots"].split(","):
                    render_nnori(ls_, h_, end_, v_)
        if bad:
            sys.exit("NNORI ⛔ 検算が %d 件落ちた" % bad)
    if what == "sode_nori":
        # blender ... -- sode_nori [--keri=0.250 --fumi=0.542] [--e=-0.20,-0.15] [--render] ── 背を相手の法で切った野面の袖
        keri_, fumi_ = float(OPT.get("keri") or 0.250), float(OPT.get("fumi") or 0.542)
        es_ = _floats("e", NNORI_SODE_E)
        bad = 0
        for e_ in es_:
            for v_ in "ab":
                o, name = make_sode_nnori(keri_, fumi_, e_, v_)
                bad += check_sode_nnori(o, keri_, fumi_, e_)
                export(o, name, OUT_SODE)
        if RENDER:
            for e_ in es_:
                if OPT.get("shots") is None or ("%+.2f" % e_) in OPT["shots"].split(","):
                    render_sode_nnori(keri_, fumi_, e_, "a")
        if bad:
            sys.exit("SNORI ⛔ 検算が %d 件落ちた" % bad)
    if what == "mikiri_h":
        # blender ... -- mikiri_h [--h=1.5,1.8] [--render] ── 丈を合わせた見切り石
        bad = 0
        for h_ in _floats("h", MIKIRI_TIERS):
            o, name = make_mikiri_h(h_)
            bad += check_mikiri_h(o, h_)
            export(o, name, OUT_WALL)
            if RENDER:
                render_mikiri_h(h_)
        if bad:
            sys.exit("MIKIRI ⛔ 検算が %d 件落ちた" % bad)
    if what in ("wall", "all"):
        do_wall()
    if what in ("kiri", "all"):
        do_kiri()
    if what in ("mikiri", "all"):
        do_mikiri()
    if what in ("sode", "all"):
        do_sode()
    if RENDER:
        if what in ("wall", "all", "kiri"):
            render_wall_run("")
            render_wall_run("_magenta", magenta=True)
            render_tier_mix("")
        if what in ("mikiri", "all"):
            render_mikiri()
    for r in REPORT:
        print("NOZURA_SUM %s %d" % (r[0], r[1]))
