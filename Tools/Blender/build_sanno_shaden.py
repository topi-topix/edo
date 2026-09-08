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

━━━ 材(⛔ 新規マテリアルを作らない)━━━━━━━━━━━━━━━━━━━━━━━━━━━━
すべて Village Kit の材質**名**をそのまま運ぶ: `roof` / `wood` / `wall C` / `door wall` /
`Foundation_A_01`。⇒ Unity 側の Search & Remap が既存 `.mat` を当てる。
⚠ **`Edo/山王社/新造部材のマテリアルをremap` は借り先が Waldemarst と NatureManufacture だけ**
  なので、**Village Kit の Materials を借り先に足し、`Assets/Edo/Models/Sanno` を `modelDirs`
  に足す**こと(足し忘れると真っ白)。→ 報告に行を書いた。

⛔⛔ **未決(普請奉行へ返す)**:
  ・**銅瓦葺の色**。指図は本殿・幣殿・拝殿とも【S】で銅瓦葺。⛔ 在庫に緑青(青緑)の材が
    無く、⛔ 新規マテリアルを作らない規約と正面衝突する。⇒ **いまは瓦の `roof`(灰の本瓦)**
    で焼いてある。緑青にするなら材を1枚起こす裁定が要る。
  ・**朱塗か素木か**。山王権現社は朱塗の類型だが、在庫に朱の材が無い。いまは `wood`(素木)。

━━━ 寸法の出所 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・**平面(間数)= 指図 `munes` の du/dv**。⛔ ここに書かない — `rects()` が毎回読む。
・**床高 = 指図 `const.shadenFloor`**(本殿だけ石造亀腹ぶん嵩上げ【U】)。
・**高さの内訳(柱高・組物・軒の出)は全て【U 設計値】。** 指図の `h`(棟高)は
  【U 類型の中央】で、⛔ **瓦モジュールの勾配 0.5456(5.5寸)では両立しない** —
  梁間三間(5.454m)に 5.5寸を架けると棟は軒先から 2.1〜2.2m しか上がらないので、
  棟高 10〜11m は **軒先を 8m 超に上げないと出ない**(単層の社殿の姿にならない)。
  ⇒ **建てられる姿を採り、差を報告する**(README「指図に軒高と棟高が両方書いてあっても、
  スパンが変わると両立しない」)。裁定は普請奉行。

━━━ 落とし穴 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・⚠ `export_fbx` を通した後は bbox が 0 に潰れる。**測るのもレンダも書き出しの前に。**
・⚠ 同じ FBX を2度読むと `wood.001` ができる。join の前に `V.dedup_materials()`。
・⚠ 瓦場のクリップは平面 bisect(`GR.clip_convex`)。⛔ ブーリアンは瓦場に効かない。
"""
import bpy, bmesh, sys, os, math, json, hashlib
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "sanno_sashizu.json")

RATIO = GR.RATIO            # 0.5456 ≒ 5.5寸。⛔ 瓦モジュールに焼き付いていて動かせない


# ==========================================================================
# 指図を読む(⛔ 区画と床高の数をここに書かない)
# ==========================================================================
def sashizu():
    with open(SASHIZU) as f:
        return json.load(f)


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
            out[k] = dict(u0=float(m["u0"]), v0=float(m["v0"]),
                          du=float(m["du"]), dv=float(m["dv"]),
                          h=(float(m["h"]) if "h" in m else None), name=m["name"])
    missing = [n for n, k in want.items() if k not in out]
    if missing:
        raise SystemExit("[shaden] 指図に棟が無い: %s" % missing)
    out["_ken"] = K
    out["_floor"] = float(d["const"]["shadenFloor"])
    for k in ("honden", "tsukuriai", "heiden", "haiden", "kohai"):
        r = out[k]
        r["cu"] = (r["u0"] + r["du"] / 2.0) * K     # 区画の中心(世界の u,v[m])
        r["cv"] = (r["v0"] + r["dv"] / 2.0) * K
        r["hu"] = r["du"] * K / 2.0                 # 半幅(東西)
        r["hv"] = r["dv"] * K / 2.0                 # 半幅(南北)
    return out


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
# floor : 床(地盤から)。⛔ **数を書かない** — `apply_floor()` が指図 `const.shadenFloor`
#         を五棟すべてへ入れる。⚠ **権現造では本殿の床を一段上げる**のが通例だが、
#         指図は社殿に**一つの床高**しか宣言していない ⇒ ⛔ 部材方が勝手に段を付けない
#         (→ `_pending`「本殿の床を拝殿より上げるか」。普請奉行の裁定)。
# colH  : 床から頭貫上端までの柱高    kumi : 組物+丸桁(頭貫上端から軒先の名目平面まで)
# eave  : 軒の出                      gf   : 入母屋の妻の立上り比(GR.make_irimoya)
# colD  : 円柱の径(総円柱)
SPEC = {
    "honden":    dict(floor=None, colH=3.95, kumi=1.20, eave=1.20, gf=0.45, colD=0.40),
    "haiden":    dict(floor=None, colH=4.00, kumi=1.20, eave=1.30, gf=0.45, colD=0.42),
    "heiden":    dict(floor=None, colH=2.30, kumi=0.65, eave=0.60, colD=0.36),
    "tsukuriai": dict(floor=None, colH=2.30, kumi=0.65, eave=0.60, colD=0.36),
    "kohai":     dict(floor=None, colH=3.25, kumi=0.50, eave=1.00, colD=0.36),
}


def apply_floor(R):
    """指図 `const.shadenFloor` を五棟の床高に入れる。⛔ 数をスクリプトへ写さない。"""
    for k in SPEC:
        SPEC[k]["floor"] = R["_floor"]
UCHINORI = 2.35      # 内法(床から)【U】。⛔ 幣殿は柱高が足りないので下で詰める
EN_W = 0.90          # 縁の出【U】
KORAN_H = 0.78       # 高欄の丈(縁から)【U】
# 千鳥破風【U 設計値】: b=半幅 / ug=破風面の位置(棟の芯からの u) / zde=破風の軒の高さ
# ⚠ **zde は主屋根の面より 0.5m 以上上に置くこと** — 瓦の実体は名目平面より 0.15 上に
#   うねるので、僅かに上げただけだと破風が主屋根に**埋まって三角の板だけが浮く**
#   (2026-09-09 に zde−主屋根 = 0.15 で実際にそうなった)。`chidori_hafu` が検算する。
CHIDORI = dict(b=2.30, ug=3.85, zde=6.90)
KARAHAFU = dict(A=0.90, dk=2.20, flare=0.30)  # 軒唐破風の反り【U 設計値】
# ⚠ A/dk を大きくすると **瓦の実ジオメトリが千切れる**(桁行の重ね代を超えて剪断される)。
#   2026-09-09 に A=1.15 / dk=1.60 で瓦場が穴だらけになった。⭕ 反りの稜は
#   `karahafu_crest` が**棟モジュール**で塞ぐので、A を欲張らなくても唐破風に見える。
KOHAI_TOP_Z = 6.20      # 向拝の庇の上端(拝殿の軒の懐へ差し込む高さ)【U 設計値】
# ⚠ 低くすると主屋根の軒との間に**空の隙**が開く(2026-09-09 に 5.14 で 1.7m 開いた)


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
def kamebara(M, hu, hv, top, uv, mat, batter=0.22, skirt=0.16):
    """**石造亀腹**(社殿を載せる石の基壇)。上小・下大の勾配を付ける。"""
    u1, v1 = hu + skirt, hv + skirt
    u0, v0 = u1 + batter, v1 + batter
    ru0, rv0, ru1, rv1 = uv
    ring = [((u0, v0), (u1, v1)), ]
    _ = ring
    corners_b = [(-u0, -v0), (u0, -v0), (u0, v0), (-u0, v0)]
    corners_t = [(-u1, -v1), (u1, -v1), (u1, v1), (-u1, v1)]
    for i in range(4):
        a, b = corners_b[i], corners_b[(i + 1) % 4]
        c, d = corners_t[(i + 1) % 4], corners_t[i]
        M.quad_uvs([q(a[0], a[1], 0.0), q(b[0], b[1], 0.0),
                    q(c[0], c[1], top), q(d[0], d[1], top)],
                   [(ru0, rv0), (ru1, rv0), (ru1, rv1), (ru0, rv1)], mat)
    # 天端
    M.quad_uvs([q(-u1, -v1, top), q(u1, -v1, top), q(u1, v1, top), q(-u1, v1, top)],
               [(ru0, rv0), (ru1, rv0), (ru1, rv1), (ru0, rv1)], mat)


def en_koran(M, hu, hv, floor, uv_wood, m_wood, sides=("n", "s", "e", "w"),
             w=EN_W, kh=KORAN_H):
    """**縁 + 高欄**。⭐ 「床が地面から浮いて、まわりに縁と高欄が回る」姿は
    民家と社殿を分ける一番大きい合図なので必ず入れる。"""
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
    # 縁束(縁を支える束)
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


def columns(M, hu, hv, nu, nv, floor, colH, r, uv, mat):
    """**総円柱**。四周の柱間の交点に立てる(内部の柱は見えないので立てない)。"""
    us = bay_lines(hu, nu)
    vs = bay_lines(hv, nv)
    pts = []
    for uu in us:
        pts.append((uu, vs[0])); pts.append((uu, vs[-1]))
    for vv in vs[1:-1]:
        pts.append((us[0], vv)); pts.append((us[-1], vv))
    for (uu, vv) in pts:
        cyl(M, uu, vv, floor, floor + colH, r / 2.0, uv, mat, n=12, taper=0.94)
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
    """入母屋の隅(寄棟)面が軒先から内へ入る深さ a = hb/RATIO(`GR.make_irimoya` と同じ式)。
    ⛔ 数を写さない — 大棟高 h=(梁間/2+軒の出)·RATIO / hb = h·gf / a = hb/RATIO。"""
    return ((hu + eave) * RATIO) * gf / RATIO


def taruki(M, hu, hv, eaveZ, eave, uv, mat, pitch=0.36, hip=None):
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
        """軒先 p_eave から屋根の内側 d_uv 方向へ depth だけ、勾配に沿って伸ばす。"""
        p0 = (p_eave[0], p_eave[1], eaveZ - tt)
        p1 = (p_eave[0] + d_uv[0] * depth, p_eave[1] + d_uv[1] * depth,
              eaveZ + depth * RATIO - tt)
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


def panel_mairado(M, a0, a1, along, w, z0, z1, uv, mat, t=0.05):
    """**舞良戸** — 板戸に細い横桟(舞良子)を打つ。"""
    if along == "u":
        box3(M, a0, a1, w - t, w + t, z0, z1, uv, mat, grain="u")
    else:
        box3(M, w - t, w + t, a0, a1, z0, z1, uv, mat, grain="v")
    n = max(4, int((z1 - z0) / 0.19))
    for i in range(1, n):
        z = z0 + (z1 - z0) * i / float(n)
        if along == "u":
            box3(M, a0 + 0.03, a1 - 0.03, w + t, w + t + 0.022, z - 0.022, z + 0.022,
                 uv, mat, grain="u")
        else:
            box3(M, w + t, w + t + 0.022, a0 + 0.03, a1 - 0.03, z - 0.022, z + 0.022,
                 uv, mat, grain="v")


def panel_koshi(M, a0, a1, along, w, z0, z1, uv, mat, uvb, matb, pitch=0.115, t=0.035):
    """**格子戸 / 蔀戸** — 竪子を実体で並べ、裏に明かり障子(板)を入れる。
    ⛔ 格子だけにしない — 素通しになって建物の中と反対側の壁の裏面が見える。"""
    if along == "u":
        box3(M, a0, a1, w - t - 0.03, w - t, z0, z1, uvb, matb, grain="u")
    else:
        box3(M, w - t - 0.03, w - t, a0, a1, z0, z1, uvb, matb, grain="v")
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
    """(材質のリスト, UV矩形の辞書)。索引 0=wood 1=wall C 2=door wall 3=Foundation_A_01"""
    m_wood, uv_wood = VM.vk_mat(V, "Walls and floors/column A.fbx", "wood", GR.WOOD_UV)
    m_wall, uv_wall = VM.vk_mat(V, "Walls and floors/wall C.fbx", "wall C", GR.WALLC_UV)
    m_door, uv_door = VM.vk_mat(V, "Walls and floors/door wall A.fbx", "door wall",
                                (0.05, 0.05, 0.45, 0.95))
    m_fnd, uv_fnd = VM.vk_mat(V, "Foundations/Foundation_A_01_2x2.fbx", "Foundation_A_01",
                              (0.05, 0.05, 0.95, 0.95))
    uv = dict(
        wood=GR.WOOD_UV,                       # 縦木理の一枚(柱・板)
        wood_h=VM.sub(uv_wood, 0.12, 0.06, 0.42, 0.94),
        wall=VM.sub(uv_wall, 0.10, 0.10, 0.90, 0.60),
        door=VM.sub(uv_door, 0.06, 0.10, 0.44, 0.90),
        shoji=VM.sub(uv_door, 0.55, 0.12, 0.95, 0.88),
        fnd=VM.sub(uv_fnd, 0.05, 0.05, 0.95, 0.60),
    )
    return [m_wood, m_wall, m_door, m_fnd], uv


W, WC, DW, FND = 0, 1, 2, 3


# ==========================================================================
# 屋根
# ==========================================================================
def irimoya(name, hu, hv, eave, eaveZ, gf, p):
    """**入母屋**(大棟は南北 = v 方向)。`GR.make_irimoya` を桁行=Blender X で焼き、
    ⭕ `rotate_z(-90)`(行列式 +1)で大棟を v へ倒す。⛔ 自前で焼き直さない。"""
    o = GR.make_irimoya(2 * hv, 2 * hu, name, eave=eave, gable_frac=gf)
    o.location = (0.0, 0.0, 0.0)
    V.sel([o])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    # GR 系: +X=桁行, +Y=梁間。rotate_z(-90) で (x,y)→(y,-x)
    #   ⇒ GR +X → Blender −Y(= 論理 +v = 北) / GR +Y → Blender +X(= 論理 −u = 西)
    #   ⇒ GR の「南流れ(−Y側)」が **東の流れ**になる。千鳥破風はそこへ載せる。
    V.rotate_z([o], -90)
    o.location = (0.0, 0.0, eaveZ)
    V.sel([o])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    _ = p
    return o


def chidori_hafu(name, hu, eave, eaveZ, p, b, ug, zde):
    """**千鳥破風** — 東の流れに載る入母屋形の出窓破風。返り値 = オブジェクト列。

    幾何: 主屋根の東流れは z(u) = eaveZ + (utip − u)·RATIO(utip = hu+eave)。
      破風の大棟は **水平**に zr で通り、主屋根と交わる所(udie)で死ぬ。
      両流れは棟から ±v へ RATIO で落ち、軒(z = zr − b·RATIO)が主屋根と交わる所(uh)で死ぬ。
      ⇒ 谷は (uh, ±b) と (udie, 0) を結ぶ直線(両方の平面上にある2点なので必ず直線)。
    ⚠ **軒が主屋根より上に出ていること**を確かめてから呼ぶこと(下でアサートする)。"""
    utip = hu + eave
    main = lambda u: eaveZ + (utip - u) * RATIO
    zr = zde + b * RATIO                      # 破風の大棟の高さ
    clear = zde - main(ug)
    print("  千鳥破風 軒 %.3f / 棟 %.3f / 主屋根 %.3f ⇒ 浮き %.3f m" % (zde, zr, main(ug), clear))
    if clear < 0.45:
        raise SystemExit("[chidori] ⛔ 破風の軒が主屋根から %.3f しか浮いていない "
                         "— 瓦の実体(+0.15)に埋まって板だけが浮く。zde を上げること" % clear)
    if zr > eaveZ + utip * RATIO - 0.10:
        raise SystemExit("[chidori] ⛔ 破風の棟 %.3f が大棟 %.3f を越える"
                         % (zr, eaveZ + utip * RATIO))
    uh = utip - (zde - eaveZ) / RATIO         # 軒が主屋根と交わる u
    udie = utip - (zr - eaveZ) / RATIO        # 大棟が主屋根と交わる u
    out = []
    # 両流れ(南 = v<0 / 北 = v>0)。BX で Blender へ落とす
    for sg in (-1, +1):
        poly = [BX(udie, 0.0), BX(ug, 0.0), BX(ug, sg * b), BX(uh, sg * b)]
        # 棟(v=0)へ向かって上る。論理 +v = Blender −Y なので、
        #   南半(sg=−1)は Blender −Y へ上る = yaw 270 / 北半は yaw 90
        yaw = 270 if sg < 0 else 90
        f = GR._tile_field_fast([poly], BX(ug, sg * b), yaw, zde,
                                "%s_f%d" % (name, sg))
        if f:
            out.append(f)
    # 小さな大棟
    out += GR.ridge((BX(udie, 0)[0], BX(udie, 0)[1], zr),
                    (BX(ug, 0)[0], BX(ug, 0)[1], zr), name + "_mune", w=0.40, h=0.34)
    # 破風・木連格子・懸魚(GR.gable は x 法線の妻。論理 u 一定の面なのでそのまま使える)
    gx = BX(ug, 0)[0]
    geo = GR.gable(gx, +1, -b, b, zde, 0.0, zr, name + "_g", p, bw=0.46, bt=0.17, drop=0.55)
    for o, uvv in geo:
        if o:
            if uvv:
                V.set_uv(o, uvv)
            out.append(o)
    # 袖瓦(破風の天端に被る瓦)。瓦の実体が名目平面より上にあるので 0.20 持ち上げる
    sx = gx + 0.06                      # inward=+1 の外面側へ寄せる(Blender +X = 論理 −u)
    for sg in (-1, +1):
        out += GR.ridge((sx, BX(0, sg * b)[1], zde + 0.20), (sx, 0.0, zr + 0.20),
                        name + "_sode", w=0.30, h=0.24)
    return [o for o in out if o]


def ryosage(name, hu, hv, eave, ridgeZ, p, west_ext=0.0, east_ext=0.0):
    """**両下造** — 大棟が東西(u)に走り、南北(v)へ両流れ。妻を持たない
    (棟の両端が本殿・拝殿に接続する)ので ⛔ **破風・懸魚を付けない**。
    `west_ext`/`east_ext` は隣の棟の軒下へ潜らせる伸ばし。"""
    hvE = hv + eave
    zeave = ridgeZ - hvE * RATIO
    u0, u1 = -hu - west_ext, hu + east_ext
    out = []
    for sg in (-1, +1):
        poly = [BX(u0, sg * hvE), BX(u1, sg * hvE), BX(u1, 0.0), BX(u0, 0.0)]
        yaw = 270 if sg < 0 else 90
        f = GR._tile_field_fast([poly], BX(u0, sg * hvE), yaw, zeave, "%s_f%d" % (name, sg))
        if f:
            out.append(f)
    out += GR.ridge((BX(u0, 0)[0], 0.0, ridgeZ - 0.10), (BX(u1, 0)[0], 0.0, ridgeZ - 0.10),
                    name + "_mune", w=0.40, h=0.30)
    _ = p
    return [o for o in out if o], zeave


def hisashi_karahafu(name, hu, hv, eave, eaveZ, utop, ztop, p, ka=KARAHAFU):
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
    f = GR._tile_field_fast([poly], BX(ue, -hvE), 0, eaveZ, name + "_f")
    if f is None:
        raise SystemExit("[karahafu] 庇の瓦場が空")
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
    """join → ピボットを **区画の中心・地盤レベル**へ。⚠ 測るのは書き出しの前。"""
    V.dedup_materials()
    o = V.join([x for x in objs if x], name)
    V.set_origin(o, (0.0, 0.0, pivot_h))
    return o


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


def honden(R, name="Sanno_Honden_3x3ken"):
    """**本殿** 桁行三間×梁間三間・単層・入母屋造【S】。石造亀腹・出組・総円柱・脇障子【A】。"""
    r, s = R["honden"], SPEC["honden"]
    hu, hv = r["hu"], r["hv"]
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    kamebara(M, hu, hv, s["floor"], uv["fnd"], FND)
    us, vs = columns(M, hu, hv, int(r["du"]), int(r["dv"]), s["floor"], s["colH"],
                     s["colD"], uv["wood"], W)
    kumimono(M, us, vs, s["floor"], s["colH"], s["kumi"], uv["wood_h"], W, kind="degumi")
    kokabe(M, us, vs, s["floor"], s["colH"], uv["wall"], WC, renji=(uv["wood"], W))
    # 縁は東(作り合いへ繋ぐ)以外の三方。腰組で支持【A】
    en_koran(M, hu, hv, s["floor"], uv["wood"], W, sides=("n", "s", "w"))
    z0, z1 = s["floor"], s["floor"] + UCHINORI
    # 側面(南北)は **前方二間を舞良戸・後方一間を板壁**【A】。前方 = 東
    for vv in (vs[0], vs[-1]):
        for i in range(len(us) - 1):
            a, b = us[i], us[i + 1]
            mid = (a + b) / 2.0
            if mid > -hu + (2.0 / 3.0) * 2 * hu - 2 * hu:   # 東寄り二間
                pass
            if i >= 1:                                     # 東側の二間 = i=1,2
                panel_mairado(M, a + 0.10, b - 0.10, "u", vv, z0, z1, uv["door"], DW)
            else:
                panel_ita(M, a + 0.10, b - 0.10, "u", vv, z0, z1, uv["wood"], W)
    # 背面(西)は板壁
    for j in range(len(vs) - 1):
        panel_ita(M, vs[j] + 0.10, vs[j + 1] - 0.10, "v", us[0], z0, z1, uv["wood"], W)
    # 正面(東)は御扉 — 中央間を板扉、脇間を板壁
    for j in range(len(vs) - 1):
        a, b = vs[j], vs[j + 1]
        if j == 1:
            panel_mairado(M, a + 0.10, b - 0.10, "v", us[-1], z0, z1, uv["door"], DW)
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
    taruki(M, hu, hv, ez, s["eave"], uv["wood_h"], W, hip=hip_depth(hu, s["eave"], s["gf"]))
    body = M.to_object(name + "_body", ms)
    roof = irimoya(name + "_roof", hu, hv, s["eave"], ez, s["gf"], p)
    o = finish([body, roof], name)
    return o, ez + (hu + s["eave"]) * RATIO


def haiden(R, name="Sanno_Haiden_3x7ken"):
    """**拝殿** 桁行七間×梁間三間・入母屋造・**千鳥破風及軒唐破風附**【S】。
    ⚠ 軒唐破風は `munes[向拝]` の側に載る(この棟には千鳥破風だけ)。"""
    r, s = R["haiden"], SPEC["haiden"]
    hu, hv = r["hu"], r["hv"]
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    kamebara(M, hu, hv, s["floor"], uv["fnd"], FND)
    us, vs = columns(M, hu, hv, int(r["du"]), int(r["dv"]), s["floor"], s["colH"],
                     s["colD"], uv["wood"], W)
    kumimono(M, us, vs, s["floor"], s["colH"], s["kumi"], uv["wood_h"], W,
             kind="hiramitsudo")
    kokabe(M, us, vs, s["floor"], s["colH"], uv["wall"], WC, renji=(uv["wood"], W))
    en_koran(M, hu, hv, s["floor"], uv["wood"], W, sides=("n", "s", "e"))
    z0, z1 = s["floor"], s["floor"] + UCHINORI
    # 両側面(南北)**前方一間を蔀戸**【A】、残りは板壁
    for vv in (vs[0], vs[-1]):
        for i in range(len(us) - 1):
            a, b = us[i], us[i + 1]
            if i == len(us) - 2:                    # 東端の一間 = 前方
                panel_koshi(M, a + 0.10, b - 0.10, "u", vv, z0, z1,
                            uv["wood"], W, uv["shoji"], DW)
            else:
                panel_ita(M, a + 0.10, b - 0.10, "u", vv, z0, z1, uv["wood"], W)
    # 背面(西)= 幣殿境。**格子戸**【A】
    for j in range(len(vs) - 1):
        panel_koshi(M, vs[j] + 0.10, vs[j + 1] - 0.10, "v", us[0], z0, z1,
                    uv["wood"], W, uv["shoji"], DW)
    # 正面(東)は中央三間を開け、両脇二間ずつを板壁 + その上に格子欄間
    for j in range(len(vs) - 1):
        a, b = vs[j], vs[j + 1]
        if 2 <= j <= 4:
            panel_koshi(M, a + 0.10, b - 0.10, "v", us[-1], z0, z1,
                        uv["wood"], W, uv["shoji"], DW)
        else:
            panel_ita(M, a + 0.10, b - 0.10, "v", us[-1], z0, z1, uv["wood"], W)
    ez = eave_z("haiden")
    taruki(M, hu, hv, ez, s["eave"], uv["wood_h"], W, hip=hip_depth(hu, s["eave"], s["gf"]))
    body = M.to_object(name + "_body", ms)
    roof = irimoya(name + "_roof", hu, hv, s["eave"], ez, s["gf"], p)
    ch = chidori_hafu(name + "_chidori", hu, s["eave"], ez, p,
                      CHIDORI["b"], CHIDORI["ug"], CHIDORI["zde"])
    o = finish([body, roof] + ch, name)
    return o, ez + (hu + s["eave"]) * RATIO


def _renketsu(R, key, name, ebi):
    """**幣殿 / 作り合い** — 一続きの両下造の屋根を区画ごとに切り出す。
    ⭕ 断面が u について一様なので、二本を隣り合わせに据えると **継ぎ目が出ない**。"""
    r, s = R[key], SPEC[key]
    hu, hv = r["hu"], r["hv"]
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    kamebara(M, hu, hv, s["floor"], uv["fnd"], FND)
    us, vs = columns(M, hu, hv, int(r["du"]), int(r["dv"]), s["floor"], s["colH"],
                     s["colD"], uv["wood"], W)
    kumimono(M, us, vs, s["floor"], s["colH"], s["kumi"], uv["wood_h"], W,
             kind="hiramitsudo")
    uc = min(UCHINORI, s["colH"] - 0.45)
    kokabe(M, us, vs, s["floor"], s["colH"], uv["wall"], WC, uc=uc)
    z0, z1 = s["floor"], s["floor"] + uc
    if key == "heiden":
        # 幣殿は南北の側面を板壁で閉じる(⛔ 作り合いは閉じない)
        for vv in (vs[0], vs[-1]):
            panel_ita(M, us[0] + 0.08, us[-1] - 0.08, "u", vv, z0, z1, uv["wood"], W)
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
    body = M.to_object(name + "_body", ms)
    ridgeZ = eave_z(key) + (hv + s["eave"]) * RATIO
    we = 0.75 if key == "tsukuriai" else 0.0        # 本殿の軒下へ潜らせる
    ee = 0.75 if key == "heiden" else 0.0           # 拝殿の軒下へ潜らせる
    roof, zeave = ryosage(name + "_roof", hu, hv, s["eave"], ridgeZ, p,
                          west_ext=we, east_ext=ee)
    # 垂木は南北の軒だけ(東西は隣の棟に隠れる)
    M2 = VM.Mesh()
    for sg in (-1, +1):
        n = max(2, int(round(2 * (hu + 0.4) / 0.34)))
        for i in range(n + 1):
            uu = -(hu) + 2 * hu * i / float(n)
            p0 = (uu, sg * (hv + s["eave"]), zeave - 0.10)
            p1 = (uu, sg * (hv - 0.45), zeave + (s["eave"] + 0.45) * RATIO - 0.10)
            stick(M2, p0, p1, 0.08, 0.10, uv["wood_h"], W)
    taru = M2.to_object(name + "_taruki", ms)
    o = finish([body, taru] + roof, name)
    return o, ridgeZ


def heiden(R, name="Sanno_Heiden_1x3ken"):
    return _renketsu(R, "heiden", name, ebi=False)


def tsukuriai(R, name="Sanno_Tsukuriai_1x3ken"):
    return _renketsu(R, "tsukuriai", name, ebi=True)


def kohai(R, name="Sanno_Kohai_1x3ken"):
    """**向拝三間・出一間・軒唐破風**【S/U】。⛔ 木階は別部材(`kaidans[向拝の階]`)。"""
    global KARA_B
    r, s = R["kohai"], SPEC["kohai"]
    hu, hv = r["hu"], r["hv"]
    KARA_B = hv                                 # 唐破風の半幅 = 向拝三間の半分
    ms, uv = mats()
    p = GR.palette()
    M = VM.Mesh()
    # 向拝柱(角柱の几帳面取りが常法だが、社殿に揃えて円柱)+ 礎盤
    vs = bay_lines(hv, int(r["dv"]))
    for vv in vs:
        box3(M, hu - 0.26, hu + 0.26, vv - 0.26, vv + 0.26, s["floor"] - 0.10,
             s["floor"] + 0.12, uv["fnd"], FND, grain="h")
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
    # 庇の垂木
    ue = hu + s["eave"]
    ztop = KOHAI_TOP_Z                          # 上端 = 拝殿の軒の懐へ差し込む高さ
    zeave = ztop - (ue - (-hu)) * RATIO         # ⇒ 軒先はそこから流れ落ちた高さ
    nt = max(2, int(round(2 * (hv + 0.6) / 0.34)))
    for i in range(nt + 1):
        vv = -(hv + 0.6) + 2 * (hv + 0.6) * i / float(nt)
        stick(M, (ue, vv, zeave - 0.11), (-hu - 0.30, vv, ztop + 0.30 * RATIO - 0.11),
              0.08, 0.10, uv["wood_h"], W)
    body = M.to_object(name + "_body", ms)
    roof = hisashi_karahafu(name + "_roof", hu, hv, s["eave"], zeave, -hu, ztop, p)
    o = finish([body] + roof, name)
    return o, zeave + kara_g(0.0, KARAHAFU)


def kizahashi(R, name="Sanno_Kizahashi_3ken"):
    """**木階三級**【A 加藤重枝2018】。⛔ 石段にしない — 在庫の段石(`Dan_*`)を当てない。"""
    k = kizahashi_spec()
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
        # (躯体は柱も床も入るので均されて差が出ない。材質名 `roof` はキット由来)
        ridx = [i for i, m in enumerate(o.data.materials) if m and m.name == "roof"]
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
        #   材質名 `roof` はキット由来で、当スクリプトの引数とは無関係。
        ridx = [i for i, m in enumerate(o.data.materials) if m and m.name == "roof"]
        vids = set()
        for pg in o.data.polygons:
            if pg.material_index in ridx:
                vids.update(pg.vertices)
        if not vids:
            print("  検算 ⛔ roof の面が無い"); return False
        xs = [uv[i][0] for i in vids]
        skew = min(xs) + max(xs)
        want = -1 if kind == "tuck_west" else +1
        ok = skew * want > 0.30
        msg = ("X[%.2f,%.2f] の偏り %+.3f(%s の軒下へ潜る側へ伸びる)"
               % (min(xs), max(xs), skew, "西=本殿" if want < 0 else "東=拝殿"))
    print("  検算 正面=東(Unity +X) %-18s %s  %s" % (name, "⭕" if ok else "⛔", msg))
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


def assemble(R):
    """5棟 + 木階を指図の区画へ仮組みする(レンダ専用)。"""
    objs = []
    ref = R["haiden"]
    for key, fn in (("honden", honden), ("tsukuriai", tsukuriai), ("heiden", heiden),
                    ("haiden", haiden), ("kohai", kohai)):
        o, _top = fn(R)
        place(o, R[key]["cu"] - ref["cu"], R[key]["cv"] - ref["cv"])
        objs.append(o)
    k = kizahashi_spec()
    o, _ = kizahashi(R)
    place(o, (k["a"] + k["b"]) / 2.0 - ref["cu"], k["v"] - ref["cv"])
    objs.append(o)
    return objs


def shots(objs, tag="shaden"):
    """⚠ **画角は bbox から決める。**原点を見て固定倍率で撮ると端が切れる
    (2026-09-09 に本殿と木階が枠外へ出た)。"""
    V.hook_textures()
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
    # 真上 — ⭐ 左右の別・棟の並びは俯瞰でしか読めない(EDO-0161)
    one(BX(cu, cv) + (top + 40.0,), BX(cu, cv) + (0.0,),
        "plan", ortho=max(du, dv) * 1.08, res=(1500, 1500))
    return out


# ==========================================================================
def build_one(R, key, do_render):
    fn = dict(honden=honden, tsukuriai=tsukuriai, heiden=heiden,
              haiden=haiden, kohai=kohai)[key]
    V.reset()
    o, top = fn(R)
    r = R[key]
    note = "← %s(%g×%g間 / 棟または反りの頂 %.3f m)" % (r["name"], r["du"], r["dv"], top)
    report(o, o.name, note)
    check_sym_z(o, o.name)
    kind = dict(honden="door_east", haiden="chidori", kohai="downhill_east",
                tsukuriai="tuck_west", heiden="tuck_east")[key]
    if kind:
        if not check_front_east(o, o.name, kind):
            raise SystemExit("[shaden] ⛔ 正面が東を向いていない: %s" % o.name)
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


def selftest(R):
    """⛔ 0件は合格ではない。**鳴ることまで**確かめる(陰性試験)。"""
    print("=== 陰性試験: X を鏡映すると検算が止まるか ===")
    bad = []
    for key, kind in (("haiden", "chidori"), ("kohai", "downhill_east"),
                      ("honden", "door_east"), ("tsukuriai", "tuck_west"),
                      ("heiden", "tuck_east")):
        V.reset()
        o, _ = dict(honden=honden, haiden=haiden, kohai=kohai,
                    tsukuriai=tsukuriai, heiden=heiden)[key](R)
        if not check_front_east(o, o.name + "(正)", kind):
            bad.append(o.name + " 正で落ちた")
        mirror_x(o)
        if check_front_east(o, o.name + "(鏡映)", kind):
            bad.append(o.name + " 鏡映で通ってしまった")
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    pos = [a for a in argv if not a.startswith("--")]
    do_render = "--render" in argv
    what = pos[0] if pos else "all"
    R = rects()
    apply_floor(R)
    print("[shaden] 江戸間 1間 = %.3f m / 床 shadenFloor = %.2f m / 勾配 %.4f"
          % (R["_ken"], R["_floor"], RATIO))
    if what == "selftest":
        selftest(R); return
    if what == "render":
        V.reset()
        objs = assemble(R)
        for f in shots(objs):
            print("RENDER " + f)
        return
    keys = ["honden", "tsukuriai", "heiden", "haiden", "kohai"]
    if what in keys:
        build_one(R, what, do_render)
    elif what == "kizahashi":
        build_kizahashi(R)
    else:
        for k in keys:
            build_one(R, k, do_render)
        build_kizahashi(R)
    if do_render:
        V.reset()
        objs = assemble(R)
        for f in shots(objs):
            print("RENDER " + f)


if __name__ == "__main__":
    main()
