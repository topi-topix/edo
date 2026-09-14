# -*- coding: utf-8 -*-
"""山王権現社の**中門(瑞垣門)** — 一間平唐門・四脚・銅瓦葺。

    blender --background --python Tools/Blender/build_sanno_chumon.py -- [--render] [--no-export]
    SANNO_SASHIZU=<指図> blender --background --python Tools/Blender/build_sanno_chumon.py -- \
        --pitch 2.54x2.54 [--render]                    # 明治16年寸法(裁定C)

━━━ 明治16年寸法(2026-09-14 ユーザー裁定C「一番史実に近いもの」)━━━━━━━━━━━━━━━━━━━━
・`--pitch <通り抜けm>x<幅m>` = 柱間。考証方の結論: 中門の柱芯間は社殿群で揃う **2.54**(拝殿・本殿・楼門)【U 当て】。
  ⇒ 本柱の芯 Z ±1.27(`axis.colWidthM`)。⭐ 通り抜け(本柱 → 控柱 前後各半間)も**同じ 2.54 の一間**で取る
  (本殿は 3×3 間とも 2.54 — 部材方の判断【U】)⇒ 控柱の芯 X ±1.27。
  名前に柱芯の外形を足す: `Sanno_Chumon_1x1ken_<通り抜けmm>x<幅mm>_k…`(楼門と同じ順)。
・指図 json は改訂中なので柱間は引数で受ける(json の `axis.colWidthM` と違えば ⚠ を刷るだけ)。
・高さ・柱の太さ・唐破風の断面 `KARA`・軒と妻の出・基壇の根入れ/±X の出は**柱間に比例させず据え置き**【U 類型】。
・基壇の ±Z の面 = 透塀『Sukibei_E』の `gapFrom.edge` = **本柱の外面**(柱芯 + 本柱の半径)⇒ 面の 2 mm 手前。

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指図 `bom[中門(一間平唐門)]` = 在庫『無い』・手当『新造』。形式は【S [国宝建造物目録1941]】
「中門 一間平唐門」、屋根は【S 同】銅瓦葺(社殿5棟と同じ `Doukawara`)。

━━━ 軸(楼門 `build_sanno_romon.py` と同じ規約)━━━━━━━━━━━━━━━━━━━━━━━━━━
・**ピボット = 門の芯・敷居の高さ**(Y=0 = 基壇の天端 = 通路の踏み面 = `gates[中門].sill`)。
・**通り抜け = ローカル X** / **正面 = ローカル +X**(扉は −X へ開く)。yaw 0 で正面=東。
・**大棟 = ローカル Z**(門の幅の向き)。平唐門なので**唐破風は ±Z の妻**に出る
  (正面 ±X は平入りの軒)。⛔ 向唐門(正面に唐破風)と取り違えない。
・論理 (u=通り抜け・正面が +, v=門の幅, h=上) で組み、`SH.q`/`SH.BX` で落とす
  ⇒ **Unity ローカル = (u, h, v)**。焼いた直後に**メッシュから**検算し、陰性試験を2本回す
  (X 鏡映 → 扉の向きで止まる / Y 軸 90° 回転 → 通り抜けと大棟の向きで止まる)。

━━━ 寸法の出所 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・平面 = `gates[中門].plan`(du 1 = 本柱 → 控柱の前後各半間 / dv 1 = 本柱の芯々 = 戸口)、
  1間 = `const.ken`、戸口 = `monguchiKen`。⛔ ここに書かない。
・⚠ 1間 = 1.818 の換算は【U 要改訂】(`_pending`「境内の柱間モジュール」)。
・基壇の ±Z の面 = 透塀 `runs[gate=中門]` の門口の縁(`gapFrom` = 本柱の外面、旧い指図は `gapHalf`)。
  ±X は取り合う面が無いので `G.kidanSkirt`。
・下の `G` と唐破風の断面 `KARA` は**すべて【U 類型で埋めた設計値】**。
"""
import bpy, sys, os, math, json
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH
import build_sanno_romon as RM

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
BOM_ROW = "中門(一間平唐門)"

# ==========================================================================
# 【U 類型】一間平唐門(四脚門)の設計値。⛔ 史料は数を言わない
# ==========================================================================
G = dict(
    honD=0.30,        # 本柱(円柱)の径
    hikaeW=0.21,      # 控柱(角柱)の見付
    sobanH=0.12,      # 礎盤の丈
    kabuki=(2.30, 2.66),   # 冠木(本柱の上に渡す)の下端・上端 ⇒ 内法 2.30
    uchinori=2.25,    # 扉の上端
    kashira=(2.42, 2.60),  # 頭貫(控柱 → 本柱 → 控柱、±Z の通り)
    koshi=(0.50, 0.64),    # 腰貫
    keta=(2.66, 2.90),     # 桁(控柱の上、X 通り)
    eave=0.90,        # 軒の出(控柱の芯から)
    gableOut=0.60,    # 妻の出(本柱の芯から)= 唐破風の板の位置
    kidanSkirt=0.40,  # 基壇の出(控柱の芯から、面の無い ±X)
    kidanDepth=0.30,  # 基壇の根入れ(天端 = 敷居 = 地盤 から下へ)
)
# 唐破風の断面 = 屋根面の局所勾配 k(t)(t = 軒先 0 → 棟 1)。
# 軒で緩く(反り)・中ほどで急・棟で寝る(起り)⇒ S 字の唐破風になる【U 類型】
KARA = dict(ke=0.30, kp=1.05, kr=0.12, tp=0.55)
ALLOWED_MATS = ("wood", "wall C", "door wall", "Doukawara", "Kirishi")


class KaraProfile(object):
    """軒先からの水平距離 d → 屋根面の高さ z(d)。`SH.sori_shear` にそのまま渡せる(`.z` だけ使う)。"""

    def __init__(self, half, ke, kp, kr, tp, n=600):
        self.half = float(half)
        self.ke, self.kp, self.kr, self.tp = ke, kp, kr, tp
        self.n = n
        self.tab = [0.0]
        dt = 1.0 / n
        for i in range(n):
            t = (i + 0.5) * dt
            self.tab.append(self.tab[-1] + self.kt(t) * dt * self.half)

    def kt(self, t):
        if t <= self.tp:
            return self.ke + (self.kp - self.ke) * math.sin(0.5 * math.pi * t / self.tp) ** 2
        return self.kr + (self.kp - self.kr) * math.cos(0.5 * math.pi * (t - self.tp) / (1 - self.tp)) ** 2

    def z(self, d):
        if d <= 0.0:
            return d * self.ke
        if d >= self.half:
            return self.tab[-1] + (d - self.half) * self.kr
        x = d / self.half * self.n
        i = int(x)
        return self.tab[i] + (self.tab[i + 1] - self.tab[i]) * (x - i)


def sashizu_plan(pitch=None):
    with open(SH.SASHIZU) as f:
        d = json.load(f)
    K = float(d["const"]["ken"])
    row = next((b for b in d["bom"] if b.get("部材") == BOM_ROW), None)
    if row is None:
        raise SystemExit("[chumon] ⛔ bom に行『%s』が無い" % BOM_ROW)
    hit = [g for g in d["gates"] if g.get("bom") == BOM_ROW]
    if len(hit) != 1:
        raise SystemExit("[chumon] ⛔ bom『%s』を指す門が %d 基" % (BOM_ROW, len(hit)))
    g = hit[0]
    if "銅瓦" not in row.get("屋根", ""):
        raise SystemExit("[chumon] ⛔ 屋根が銅瓦葺でない: %s" % row.get("屋根"))
    if g.get("front") != "東":
        raise SystemExit("[chumon] ⛔ 正面が東でない門は軸を読み替えていない")
    P = dict(K=K, du=int(g["plan"]["du"]), dv=int(g["plan"]["dv"]),
             monguchi=float(g["monguchiKen"]), sill=g.get("sill"), gate=g, d=d, row=row)
    if P["du"] != 1 or P["dv"] != 1 or abs(P["monguchi"] - 1.0) > 1e-6:
        raise SystemExit("[chumon] ⛔ 一間一戸(plan 1×1・戸口1間)しか組めない: %s" % g["plan"])
    # 柱間: 既定 = 1間(旧名)/ `--pitch` = 明治16年寸法(名前に柱芯の外形を足す)
    pu, pv = (K, K) if pitch is None else pitch
    P.update(pu=pu, pv=pv, hu=P["du"] * pu / 2.0, hv=P["dv"] * pv / 2.0,
             legacy=(pitch is None))
    ax = row.get("axis") or {}
    if abs(float(ax.get("colRadiusM", G["honD"] / 2.0)) - G["honD"] / 2.0) > 1e-6:
        raise SystemExit("[chumon] ⛔ 本柱の半径 %.3f が axis.colRadiusM %s と違う" % (G["honD"] / 2.0, ax.get("colRadiusM")))
    for key, val in (("colPassM", P["hu"]), ("colWidthM", P["hv"])):
        if ax.get(key) is not None and abs(float(ax[key]) - val) > 1e-3:
            print("[chumon] ⚠ 指図 axis.%s = %s ≠ 部材 %.4f(指図の改訂待ち — 引数を採る)" % (key, ax[key], val))
    print("[chumon] 門『%s』 plan du %d × dv %d / 戸口 %.1f 間 / 柱間 %.4f × %.4f / 柱芯 X ±%.4f・Z ±%.4f / sill %s / 屋根 %s"
          % (g["name"], P["du"], P["dv"], P["monguchi"], pu, pv, P["hu"], P["hv"], P["sill"], row["屋根"][:24]))
    return P


# ==========================================================================
# 取り合いの面 → 基壇の出
# ==========================================================================
def side_outs(P):
    d, g, K = P["d"], P["gate"], P["K"]
    # ⭐ 平面は実寸の柱芯(`P.hu/hv`)を間へ戻して渡す(明治16年寸法では 1間 ≠ 柱間)
    gk = dict(g, plan={"du": 2 * P["hu"] / K, "dv": 2 * P["hv"] / K})
    # ⚠ 他の門・run に従属する端(`endFrom`/`uFrom`)は焼き出し待ちで解けないことがある(2026-09-14 楼門の袖塀)。
    #   中門から数十 m 離れた run なので、この門を指さない従属 run は面の読みから外す
    dk = dict(d, runs=[r for r in d["runs"] if not (r.get("endFrom") or r.get("uFrom"))
                       or (r.get("endFrom") or {}).get("gate") == g["name"]])
    F, src = RM.faces(dk, gk, K)                # 石段・土留め・囲いの端(楼門と同じ読み)
    hv = gk["plan"]["dv"] / 2.0
    for r in d["runs"]:                         # ⭐ 透塀の門口の縁(gap)は run の端ではないので別に読む
        if r.get("gate") != g["name"]:
            continue
        gf = r.get("gapFrom") or {}
        if gf.get("gate") == g["name"]:
            # 口の縁 = 本柱の外面(柱芯 + `axis.colRadiusM`)── 指図の従属値をそのまま解く
            if gf.get("edge") != "側柱の外面":
                raise SystemExit("[chumon] ⛔ 透塀『%s』の gapFrom.edge『%s』を読み替えていない" % (r["name"], gf.get("edge")))
            m = float(P["row"]["axis"]["colRadiusM"])
            what = "透塀『%s』の口の縁 = 本柱の外面(gapFrom)" % r["name"]
            per = {"+Z": m, "-Z": m}
        else:
            gv = float(r.get("gapV", 0.0)) - float(g["v"])
            per = {side: (sg * gv + float(r["gapHalf"]) - hv) * K for sg, side in ((+1, "+Z"), (-1, "-Z"))}
            what = "透塀『%s』の門口の縁" % r["name"]
        for side, m in per.items():
            if F[side] is None or m < F[side]:
                F[side] = m; src[side] = what
    out = {}
    for s in F:
        if F[s] is not None:
            out[s] = max(0.0, math.floor((F[s] - RM.MARGIN) * 1000.0) / 1000.0)
        else:
            out[s] = G["kidanSkirt"]            # 面なし ⇒ 設計値そのもの(⛔ 余白を引かない)
    out["_face"], out["_src"] = F, src
    return out


def variant_name(P, out):
    mm = lambda s: int(round(out[s] * 1000.0))
    k = "k%d-%d-%d-%d" % (mm("+X"), mm("-X"), mm("+Z"), mm("-Z"))
    if P.get("legacy", True):
        return "Sanno_Chumon_%dx%dken_%s" % (P["du"], P["dv"], k)
    return "Sanno_Chumon_%dx%dken_%dx%d_%s" % (P["du"], P["dv"], int(round(2 * P["hu"] * 1000.0)),
                                              int(round(2 * P["hv"] * 1000.0)), k)


# ==========================================================================
# メッシュの道具(論理 u,v,h)
# ==========================================================================
_FACES = [((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)), ((1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)),
          ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)), ((0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)),
          ((1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))]


def hexa(M, C, uv, mat):
    """8隅 C[(iu,iv,ih)] = (u,v,h) の六面体。巻き順は `SH.box3` と同じ(外向き)。"""
    ru0, rv0, ru1, rv1 = uv
    quv = [(ru0, rv0), (ru1, rv0), (ru1, rv1), (ru0, rv1)]
    for f in _FACES:
        M.quad_uvs([SH.q(*C[k]) for k in f], quv, mat)


def prof_strip(M, us, v0, v1, hbot, htop, uv, mat):
    """u の折れ線に沿って、下端 hbot(u)・上端 htop(u) の板を v0..v1 の厚みで通す。"""
    for i in range(len(us) - 1):
        C = {}
        for iu, uu in ((0, us[i]), (1, us[i + 1])):
            for iv, vv in ((0, v0), (1, v1)):
                C[(iu, iv, 0)] = (uu, vv, hbot(uu))
                C[(iu, iv, 1)] = (uu, vv, htop(uu))
        hexa(M, C, uv, mat)


def lin(a, b, n):
    return [a + (b - a) * i / float(n) for i in range(n + 1)]


def slice_run(o, x0, x1, step):
    """Blender X に直交する鉛直面で `step` 刻みに切る(両側とも残す)。反らせる前の瓦場に掛ける。"""
    import bmesh
    from mathutils import Vector
    bm = bmesh.new(); bm.from_mesh(o.data)
    x = x0 + step
    while x < x1 - 1e-6:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                               plane_co=Vector((x, 0.0, 0.0)), plane_no=Vector((1.0, 0.0, 0.0)))
        x += step
    bm.to_mesh(o.data); bm.free(); o.data.update()


# ==========================================================================
# 組み立て
# ==========================================================================
def build(P, name, out):
    hu, hv = P["hu"], P["hv"]                        # 控柱の u / 本柱の v(柱間 × 間数 / 2)
    ms, uv = SH.mats()
    W, DW = SH.W, SH.DW
    p = GR.palette()
    M = VM.Mesh()
    r_h, w_k = G["honD"] / 2.0, G["hikaeW"] / 2.0

    # --- 基壇(切石・天端 = 敷居)+ 礎盤 ---------------------------------
    stones = RM.kidan(hu, hv, out, G["kidanDepth"], name + "_kidan")
    # ⚠ `RM.kidan` の段数は depth/0.30 を丸めた数。0.30 なら 1 段 + 蓋石
    stones += RM.soban_sided([(0.0, -hv), (0.0, hv)], hu, hv, out, r_h, G["sobanH"], 0.22,
                             name + "_soban_hon")
    stones += RM.soban_sided([(uu, vv) for uu in (-hu, hu) for vv in (-hv, hv)], hu, hv, out,
                             w_k, G["sobanH"], 0.17, name + "_soban_hikae")

    # --- 軸部 -----------------------------------------------------------------
    kb0, kb1 = G["kabuki"]
    for sg in (-1, 1):
        SH.cyl(M, 0.0, sg * hv, G["sobanH"], kb1, r_h, uv["wood"], W, n=14, taper=0.96)   # 本柱
        for su in (-1, 1):                                                                # 控柱
            SH.box3(M, su * hu - w_k, su * hu + w_k, sg * hv - w_k, sg * hv + w_k,
                    G["sobanH"], G["keta"][0], uv["wood"], W, grain="h")
        # 頭貫・腰貫(±Z の通りを u へ走る。木鼻 0.15)
        for (a, b) in (G["kashira"], G["koshi"]):
            SH.box3(M, -hu - 0.15, hu + 0.15, sg * hv - 0.06, sg * hv + 0.06, a, b,
                    uv["wood_h"], W, grain="u")
    # 冠木(本柱の上。木鼻 0.25)
    SH.box3(M, -0.12, 0.12, -hv - 0.25, hv + 0.25, kb0, kb1, uv["wood_h"], W, grain="v")
    # 蹴放し(敷居)。⛔ 足元から向こうが抜けないように
    SH.box3(M, -0.10, 0.10, -hv + r_h - 0.02, hv - r_h + 0.02, 0.0, 0.10, uv["wood_h"], W,
            grain="v")
    # 桁(控柱の上、門の幅へ走る。妻の出まで)
    vE = hv + G["gableOut"]
    k0, k1 = G["keta"]
    for su in (-1, 1):
        SH.box3(M, su * hu - 0.10, su * hu + 0.10, -vE + 0.05, vE - 0.05, k0, k1,
                uv["wood_h"], W, grain="v")

    # --- 屋根の断面(唐破風)----------------------------------------------------
    ue = hu + G["eave"]
    prof = KaraProfile(ue, **KARA)
    # ⭐ 瓦場を先に焼いて、**瓦の谷が名目の屋根面からどれだけ下がるか**をメッシュで測る。
    #   ⛔ 野地を決め打ち(面 −0.12)で置くと、瓦の谷から野地が突き出て茶色の穴に見え、
    #     軒裏では野地より下へ出た瓦の裏が緑に透けた(2026-09-14 の検証レンダで実見)。
    fields = []
    for sg in (1, -1):
        poly = [SH.BX(0.0, -vE), SH.BX(sg * ue, -vE), SH.BX(sg * ue, vE), SH.BX(0.0, vE)]
        org = SH.BX(sg * ue, -vE)
        yaw, up = (0, (1.0, 0.0)) if sg > 0 else (180, (-1.0, 0.0))
        f = GR._tile_field_fast([poly], org, yaw, 0.0, "%s_f%d" % (name, sg))
        if f is None:
            raise SystemExit("[chumon] ⛔ 瓦場が空")
        # ⛔⛔ 瓦モジュールの**裏板は流れ方向に 1.7 m の四角 1 枚**(頂点は軒と棟の両端だけ)。
        #   `sori_shear` は頂点しか動かさないので、S 字の断面では裏板が**弦のまま**残り、
        #   起り(棟寄り)で屋根面の 0.25 m 下を通って野地を突き抜けた
        #   (2026-09-14 軒裏の光線検算 u±0.30〜0.60 の帯。頂点・辺の中点で測っても −0.151 と出て捕まらない)。
        #   ⇒ 反らせる前に**流れ方向へ 0.08 m 刻みで鉛直に切る**(面を分けるだけで何も捨てない)
        slice_run(f, -ue, ue, 0.08)
        fields.append(SH.sori_shear(f, org, up, prof))
    dmin = min(vt.co.z - prof.z(ue - abs(vt.co.x)) for f in fields for vt in f.data.vertices
               if 0.05 < abs(vt.co.x) < ue - 0.05)
    NOJI_T, TARU_T = 0.04, 0.08
    noji_top = dmin - 0.015                       # 名目の屋根面からの差(負)
    noji_bot = noji_top - NOJI_T
    taru_c = noji_bot - TARU_T / 2.0
    # 垂木の下端が桁の天端に載る高さへ軒先を置く
    eaveZ = k1 - (taru_c - TARU_T / 2.0) - prof.z(G["eave"])
    for f in fields:
        f.data.transform(Matrix.Translation((0.0, 0.0, eaveZ))); f.data.update()
    zr = lambda u: eaveZ + prof.z(ue - abs(u))
    ridgeZ = zr(0.0)
    print("[chumon] 瓦の谷の深さ %.3f(名目の屋根面から)⇒ 野地の天端 %.3f / 垂木の芯 %.3f"
          % (dmin, noji_top, taru_c))
    # 棟木・束・蟇股の台(冠木の上)
    taru_bot = taru_c - TARU_T / 2.0
    SH.box3(M, -0.09, 0.09, -vE + 0.05, vE - 0.05, ridgeZ + taru_bot - 0.22, ridgeZ + taru_bot,
            uv["wood_h"], W, grain="v")                                          # 棟木
    SH.box3(M, -0.07, 0.07, -0.07, 0.07, kb1, ridgeZ + taru_bot - 0.22, uv["wood"], W, grain="h")
    SH.box3(M, -0.10, 0.10, -0.32, 0.32, kb1, kb1 + 0.14, uv["wood_h"], W, grain="v")
    # 野地板(軒裏を塞ぐ — 瓦の重ねの隙から空を見せない)。⭐ 天端は瓦の谷より下
    us = lin(-ue, ue, 48)
    prof_strip(M, us, -vE, vE, lambda u: zr(u) + noji_bot, lambda u: zr(u) + noji_top,
               uv["wood_h"], W)
    # 化粧垂木(u へ走る)
    nt = int(round((2 * vE - 0.2) / 0.24))
    for i in range(nt + 1):
        vv = -vE + 0.10 + (2 * vE - 0.2) * i / float(nt)
        pts = [(u, vv, zr(u) + taru_c) for u in lin(-ue + 0.04, ue - 0.04, 24)]
        for a, b in zip(pts[:-1], pts[1:]):
            SH.stick(M, a, b, 0.07, TARU_T, uv["wood_h"], W)
    # 妻壁(本柱の通り、頭貫の上 → 野地の下)。⛔ 無いと妻の下から向こうの空が抜ける
    for sg in (-1, 1):
        prof_strip(M, lin(-hu, hu, 16), sg * hv - 0.03, sg * hv + 0.03,
                   lambda u: G["kashira"][1], lambda u: zr(u) + noji_bot, uv["wood"], W)
    # 唐破風の破風板(±Z の妻。屋根面に沿う S 字)。⭐ 下端は垂木の下まで垂らして小口を隠す
    hafu_bot = min(-0.30, taru_bot - 0.04)
    for sg in (-1, 1):
        v0, v1 = sorted((sg * (vE - 0.02), sg * (vE + 0.08)))
        prof_strip(M, lin(-ue - 0.06, ue + 0.06, 48), v0, v1,
                   lambda u: zr(u) + hafu_bot, lambda u: zr(u) + 0.04, uv["wood_h"], W)
    # 扉(本柱に吊る板扉2枚。⭐ 背面 −u へ開き、通路の脇に沿う)— 楼門と同じ作り
    leaf = hv - r_h - 0.03
    for sg in (-1, 1):
        vv = sg * (hv - r_h - 0.04)
        u0, u1 = -0.14 - leaf, -0.14
        SH.box3(M, u0, u1, vv - 0.025, vv + 0.025, 0.12, G["uchinori"], uv["itado"], DW,
                grain="h")
        vin = vv - sg * 0.025
        for zz in (0.35, (G["uchinori"] + 0.12) / 2.0, G["uchinori"] - 0.35):   # 端喰の桟
            lo, hi = sorted((vin, vin - sg * 0.035))
            SH.box3(M, u0 + 0.03, u1 - 0.03, lo, hi, zz, zz + 0.09, uv["wood_h"], W, grain="u")

    body = M.to_object(name + "_body", ms)

    # --- 瓦場(銅瓦)・大棟・鬼・袖の稜・兎毛通 -----------------------------------
    roof = list(fields)
    # 大棟。⚠ 棟寄りで勾配が寝る(kr 0.12)ので、瓦場を u=0 で切った丸瓦の口が棟の下に並んで見える
    #   (2026-09-14 正面の立面で茶色の点列)⇒ 棟を低く・幅広に据えて口を呑ませる
    roof += GR.ridge((SH.BX(0, -vE)[0], SH.BX(0, -vE)[1], ridgeZ - 0.22),
                     (SH.BX(0, vE)[0], SH.BX(0, vE)[1], ridgeZ - 0.22), name + "_omune",
                     w=0.62, h=0.44)
    for sg in (-1, 1):
        roof += GR.oni((SH.BX(0, sg * vE)[0], SH.BX(0, sg * vE)[1], ridgeZ - 0.12),
                       (0.0, -float(sg)), "%s_oni%d" % (name, sg), scale=0.85)
        # 袖の稜(唐破風の板の上を巻く)。⛔ `SH.ridge_curve` の突き付けだと、曲がりの外側で
        #   継ぎ目が楔形に開いて歯抜けに見えた(2026-09-14 側面の立面で実見)
        #   ⇒ 刻みを細かくし、各駒を前後へ 0.04 伸ばして重ねる
        pts = [(SH.BX(u, sg * (vE + 0.03))[0], SH.BX(u, sg * (vE + 0.03))[1], zr(u) + 0.03)
               for u in lin(-ue - 0.04, ue + 0.04, 44)]
        for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            dd = [b[k] - a[k] for k in range(3)]
            ln = math.sqrt(sum(x * x for x in dd)) or 1.0
            e = [x / ln * 0.04 for x in dd]
            roof += GR.ridge(tuple(a[k] - e[k] for k in range(3)), tuple(b[k] + e[k] for k in range(3)),
                             "%s_sode%d_%d" % (name, sg, i), w=0.28, h=0.22)
        # 兎毛通(拝みの懸魚)+ 六葉
        for tag, shape, t0, t1, mat, uvr in (("_ubage", GR.GEGYO, 0.00, 0.06, ms[0], None),
                                             ("_rokuyo", GR.ROKUYO, 0.06, 0.09, ms[0], p["uv_dark"])):
            g = GR.plaque(name + tag + str(sg), shape, -0.5, 0.5, mat, uvr, sc=0.80, oy=0.0,
                          oz=ridgeZ - 0.24)
            if uvr is None:
                V.set_uv_rect(g, GR.WOOD_UV, axes=('y', 'z'))
            # 板の厚みを t0..t1(外向き)にして、Z 軸まわり 90° で妻の面へ向ける
            g.data.transform(Matrix.Diagonal((t1 - t0, 1.0, 1.0, 1.0)))
            yb = SH.BX(0, sg * (vE + 0.08 + (t0 + t1) / 2.0))[1]
            g.data.transform(Matrix.Translation((0.0, yb, 0.0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'))
            g.data.update()
            roof.append(g)

    V.dedup_materials()
    o = V.join([body] + [x for x in roof if x] + stones, name)
    SH.to_copper(o)                                    # 瓦・棟・鬼 ⇒ 銅瓦葺【S】
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))                   # 門の芯・敷居の高さ
    print("[chumon] 軒先 %.3f / 桁の天端 %.3f / 屋根面の頂 %.3f / 唐破風の立ち上がり %.3f"
          " / 軒の出(控柱芯)%.2f / 妻の出(本柱芯)%.2f"
          % (eaveZ, k1, ridgeZ, ridgeZ - eaveZ, G["eave"], G["gableOut"]))
    return o, dict(hu=hu, hv=hv, ue=ue, vE=vE, eaveZ=eaveZ, ridgeZ=ridgeZ)


# ==========================================================================
# 検算 — ⛔ 期待値はメッシュから
# ==========================================================================
def check_axes(o, info, label, quiet=False):
    U = SH.unity_verts(o)
    mats = o.data.materials
    ylo, yhi = 0.35, G["uchinori"] - 0.20
    clear = 0.45
    blockX = sum(1 for (x, y, z) in U if abs(z) < clear and ylo < y < yhi)
    blockZ = sum(1 for (x, y, z) in U if abs(x) < clear and ylo < y < yhi)
    pass_x = blockX == 0 and blockZ > 0

    def verts_of(names):
        idx = [i for i, m in enumerate(mats) if m and m.name.split('.')[0] in names]
        vs = set()
        for pg in o.data.polygons:
            if pg.material_index in idx:
                vs.update(pg.vertices)
        return [U[i] for i in vs]
    D = verts_of(("door wall",))
    dx = [t[0] for t in D]
    door_ok = bool(dx) and sum(dx) / len(dx) < -0.2 and (max(dx) - min(dx)) > 0.5
    # 大棟の向き: 銅瓦の最上 0.35 m の帯の広がり
    R = verts_of(("Doukawara",))
    ytop = max(t[1] for t in R)
    T = [t for t in R if t[1] > ytop - 0.35]
    xe = max(t[0] for t in T) - min(t[0] for t in T)
    ze = max(t[2] for t in T) - min(t[2] for t in T)
    ridge_z = ze > 2.0 * xe
    # 唐破風の板: 木部のうち |Z| が妻の出の外にある頂点 — 頂(|X|<0.2)と裾(|X|>ue−0.25)の高さの差
    Wd = verts_of(("wood",))
    gab = [t for t in Wd if abs(t[2]) > info["vE"] - 0.03]
    top = [t[1] for t in gab if abs(t[0]) < 0.2]
    foot = [t[1] for t in gab if abs(t[0]) > info["ue"] - 0.25]
    rise = (max(top) - max(foot)) if (top and foot) else 0.0
    xside = sum(1 for t in Wd if abs(t[0]) > info["ue"] + 0.10)
    kara_ok = rise > 0.8 and xside == 0
    ok = pass_x and door_ok and ridge_z and kara_ok
    if not quiet:
        print("  検算[%s] 通り抜け=X %s(X の通路に頂点 %d / Z の通路に %d)"
              % (label, "⭕" if pass_x else "⛔", blockX, blockZ))
        print("  検算[%s] 正面=+X  %s(扉の重心 X=%+.3f・長手 X %.2f m ⇒ 背面へ開く)"
              % (label, "⭕" if door_ok else "⛔", sum(dx) / len(dx) if dx else 0,
                 (max(dx) - min(dx)) if dx else 0))
        print("  検算[%s] 大棟=Z   %s(銅瓦の頂の帯 X %.2f / Z %.2f m)"
              % (label, "⭕" if ridge_z else "⛔", xe, ze))
        print("  検算[%s] 唐破風=±Z の妻 %s(板の頂 − 裾 %.3f m / ±X 面の外の木部 %d 頂点)"
              % (label, "⭕" if kara_ok else "⛔", rise, xside))
    return ok, dict(pass_x=pass_x, door=door_ok, ridge=ridge_z, kara=kara_ok)


def soffit_check(o, info):
    """⭐ 軒裏から銅瓦が見えないか — 屋根の下の格子点から真上へ光線を当て、最初に当たる材を数える。
    ⛔ 目で見て『塞がった』と言わない(2026-09-14 に野地を下げても見上げに緑が残った)。"""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(o, dg)
    mats = o.data.materials
    hits, total, where = 0, 0, []
    n = 24
    for i in range(n + 1):
        for j in range(n + 1):
            u = -info["ue"] + 0.02 + (2 * info["ue"] - 0.04) * i / float(n)
            v = -info["vE"] + 0.02 + (2 * info["vE"] - 0.04) * j / float(n)
            bx, by = SH.BX(u, v)
            loc, nrm, idx, dist = bvh.ray_cast(Vector((bx, by, 2.0)), Vector((0, 0, 1)), 10.0)
            if idx is None:
                continue
            total += 1
            m = mats[o.data.polygons[idx].material_index]
            if m and m.name.split('.')[0] == "Doukawara":
                hits += 1
                if len(where) < 8:
                    where.append("(u%+.2f v%+.2f z%.2f)" % (u, v, loc.z))
    print("  検算 軒裏 %s(真上の光線 %d 本のうち銅瓦に先に当たる %d 本)%s"
          % ("⭕" if hits == 0 else "⛔", total, hits, " 例 " + " ".join(where) if where else ""))
    return hits == 0


def selftest(o, info):
    res = {}
    for key, mtx in (("X 鏡映", Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))),
                     ("鉛直軸 90°", Matrix.Rotation(math.pi / 2, 4, 'Z'))):
        c = o.copy(); c.data = o.data.copy()
        bpy.context.collection.objects.link(c)
        c.data.transform(mtx); c.data.update()
        hit, parts = check_axes(c, info, key, quiet=True)
        bpy.data.objects.remove(c, do_unlink=True)
        fails = [k for k, v in parts.items() if not v]
        print("  陰性試験 %s %s(落ちた項目 %s)" % (key, "⛔ 通ってしまった" if hit else "⭕ 止まった", fails))
        res[key] = not hit
    return all(res.values())


def report(o, info, out):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    print("CHUMON %s Unity W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f]"
          " tris=%d mats=%s" % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
                                min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), tris,
                                [m.name for m in o.data.materials]))
    ok = True
    for lo, hi, band in ((-G["kidanDepth"], 0.0, "基壇(根入れ)"), (0.0, G["sobanH"], "礎盤")):
        B = [t for t in U if lo - 1e-6 <= t[1] <= hi + 1e-6]
        ext = {"+X": max(t[0] for t in B) - info["hu"], "-X": -min(t[0] for t in B) - info["hu"],
               "+Z": max(t[2] for t in B) - info["hv"], "-Z": -min(t[2] for t in B) - info["hv"]}
        row = []
        for s in ("+X", "-X", "+Z", "-Z"):
            f = out["_face"][s]
            tag = ""
            if f is not None and ext[s] - f > 1e-4:
                colR = G["honD"] / 2.0
                tag = " ⚠柱の半径" if ext[s] <= colR + 1e-4 else " ⛔"
                if tag == " ⛔":
                    ok = False
            row.append("%s %.3f%s" % (s, ext[s], "" if f is None else "/面 %.3f%s" % (f, tag)))
        print("  外形[%s] 柱芯から %s" % (band, " ／ ".join(row)))
    body = [t for t in U if 0.2 < t[1] < G["kabuki"][0] - 0.1]
    print("  軸部(内法の帯)X[%.3f,%.3f] Z[%.3f,%.3f] / 柱芯 控柱 X ±%.3f・本柱 Z ±%.3f"
          % (min(t[0] for t in body), max(t[0] for t in body), min(t[2] for t in body),
             max(t[2] for t in body), info["hu"], info["hv"]))
    # 口の寸法を**メッシュから**: 門の芯の通り(u=0)・丈 1.0 で ±Z へ水平の光線
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    def ray(v0, sgn):
        a, b = SH.BX(0.0, v0), SH.BX(0.0, v0 + sgn)
        loc, _, _, _ = bvh.ray_cast(Vector((a[0], a[1], 1.0)), Vector((b[0] - a[0], b[1] - a[1], 0.0)), 20.0)
        return None if loc is None else -loc.y          # Blender −Y = Unity +Z
    zin_p, zin_m = ray(0.0, +1), ray(0.0, -1)
    zout_p, zout_m = ray(8.0, -1), ray(-8.0, +1)
    info["clear"] = zin_p - zin_m
    info["mouth"] = zout_p - zout_m
    info["ext"] = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), min(ys), max(ys))
    dk = [t for t in U if t[1] > 2.0]
    info["eaveX"] = max(abs(t[0]) for t in dk)
    print("  口(丈 1.0・u=0)本柱の内面の間 %.3f(Z %+.3f〜%+.3f)/ 本柱の外面の間 %.3f(Z %+.3f〜%+.3f)"
          % (info["clear"], zin_m, zin_p, info["mouth"], zout_m, zout_p))
    print("  上端 %.3f / 根入れ下端 %.3f / 指紋 %s" % (max(ys), min(ys), SH.fingerprint(o)))
    return tris, ok


# ==========================================================================
# 検証レンダ(カメラは bbox から)
# ==========================================================================
def shots(o, info, tag):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    top = mx.z
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.08))
    out = []

    def one(cam, look, fn, ortho=None, res=(1600, 1200)):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_chumon_%s_%s.png" % (tag, fn))
        V.render(f); out.append(f)
    # Unity +X(正面・東)= Blender −X / Unity +Z(北)= Blender −Y
    one((-30.0, 0.0, top * 0.5), (0.0, 0.0, top * 0.5), "front", ortho=top * 1.30)
    one((0.0, -30.0, top * 0.5), (0.0, 0.0, top * 0.5), "side", ortho=top * 1.30)
    one((-7.5, -6.0, 4.6), (0.0, 0.0, top * 0.45), "oblique")
    one((-5.5, 3.2, 1.6), (0.0, 0.0, 2.3), "eye")
    one((-0.6, -0.4, 1.2), (0.3, 0.2, 4.0), "soffit", res=(1400, 1100))
    one((-(info["hu"] + 2.2), -(info["hv"] + 2.0), 0.9), (-info["hu"], -info["hv"], 0.0),
        "kidan_corner", res=(1400, 1000))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    pitch = None
    if "--pitch" in argv:
        pitch = tuple(float(x) for x in argv[argv.index("--pitch") + 1].lower().split("x"))
    P = sashizu_plan(pitch)
    out = side_outs(P)
    name = variant_name(P, out)
    print("[chumon] → %s" % name)
    for s in ("+X", "-X", "+Z", "-Z"):
        print("    %s 面 %s ← %s ⇒ 出 %.3f m" % (
            s, "—" if out["_face"][s] is None else "%.4f" % out["_face"][s],
            out["_src"].get(s, "面なし(設計値 kidanSkirt)"), out[s]))
    V.reset()
    o, info = build(P, name, out)
    tris, band_ok = report(o, info, out)
    if not band_ok:
        raise SystemExit("[chumon] ⛔ 基壇が取り合いの面を越えた")
    ok, _ = check_axes(o, info, "正")
    if not ok:
        raise SystemExit("[chumon] ⛔ 軸の検算に落ちた")
    if not selftest(o, info):
        raise SystemExit("[chumon] ⛔ 陰性試験に失敗")
    soffit_ok = soffit_check(o, info)
    if not soffit_ok and "--no-export" not in argv and "--allow-soffit" not in argv:
        raise SystemExit("[chumon] ⛔ 軒裏から銅瓦が見える")
    bad = [m.name for m in o.data.materials if m and m.name.split('.')[0] not in ALLOWED_MATS]
    print("  材 %s %s" % ([m.name for m in o.data.materials], "⭕" if not bad else "⛔ %s" % bad))
    if bad:
        raise SystemExit("[chumon] ⛔ 想定外の材")
    if "--render" in argv:
        for f in shots(o, info, "k" + name.split("_k")[-1]):
            print("RENDER " + f)
    if "--no-export" not in argv:
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)
        print("[chumon] 書き出し %s (tris %d)" % (path, tris))


if __name__ == "__main__":
    main()
