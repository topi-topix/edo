# -*- coding: utf-8 -*-
"""山王権現社の**前庭の井戸** — 井筒+井桁(`build_sanno_ido.py`)に組み合わさる残りの 2 点。

    blender --background --python Tools/Blender/build_sanno_ido_yakata.py -- [yakata] [ishiki] [--render] [--no-export]
    (部材名を省くと両方)

  ① `Sanno_Ido_Yakata_1818x2100x2900` … **井戸屋形の木部**(指図 bom 行22 + 行25)
       四本柱・妻梁・軒桁・棟束・棟木・垂木・切妻こけら葺・破風板・棟押え + 釣瓶の横木と滑車。
  ② `Sanno_Ido_Ishiki_3272x50` … **板石敷一式**(指図 bom 行26 + 行27 + 礎石)
       板石(水勾配 1/50 で東へ下る)・敷砂・割栗・井戸の縁石 4 石・礎石 4 石・浸透枡(伏せ枡・板蓋)。

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在庫の井戸 `Doi_Ido` / `Matsudaira_Ido`(1.9×2.21×1.9)は**切石の角井戸枠 + 桁 + 釣瓶**で、
屋根も四本柱も石敷も持たない。目録(docs/asset-catalog.md「井戸」)も「合成する」としか書かない ⇒ 新造。

━━━ 分け方(依頼は ①屋形+礎石 / ②石敷+縁石+枡。**礎石だけ ② へ移した**)━━━━━━
礎石は `ido._soishiM` のとおり**割栗の突き固めの上に据える**石で、板石・縁石と同じ層に嵌まり、
水勾配の付いた板石の目地で四周を囲まれる。①に置くと礎石が ② の層を貫いて**部材どうしのめり込み**に
なる。⇒ 石はすべて ②、木はすべて ①。**①の柱の根 = ②の礎石の天端**が二つの部材の唯一の接触面になる
(据える側はそこを測って寄せる。CLAUDE.md 規則21)。

━━━ 軸とピボット(Unity ローカル)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
幅 = X(**+X = 東**・山王の約束 u)/ 高さ = Y / 奥 = Z(+Z = 北)。
**3 点とも(井筒+井桁・①・②)ピボット = 井戸の芯・石敷天端(芯の位置)**で、同じ原点を共有する。
①の棟はローカル **Z** を通る(yaw 0 で指図 `muneDir` 南北)。⚠ 棟の向きは未決【?】— 変わったら
①だけ yaw 90 で据える。⚠ **②は yaw を振らない**(水勾配は東へ・浸透枡は東に付くので向きを持つ)。

━━━ 寸法の出所 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指図 `docs/Sashizu/sanno_sashizu.json` の `ido` を**実行時に読む**(⛔ ここに数を写さない)。
指図に無い値は下の `G`(【U 部材方 2026-09-23】)。読み方:
  ・`nokiH` = **軒先の葺き面の天端**(雨落ちの線の高さ)。`muneH` = **棟押えの天端**。
    ⚠ 指図は二つの基準を言わない。軒桁の天端と読むと勾配が 8.8 寸・軒先 1.46m になり
      こけら葺の小屋として成り立たないので、上のとおり読んだ(勾配は従属値で約 4.5 寸)。
  ・雨落ち: 軒先の水平投影 = 柱芯/2 + `nokiDeKen` = **石敷の半幅**(`ishikiKen`/2)ちょうど。検算で刷る。
  ・縁石: 井筒の外径の円 〜 外の正方形(半幅 = 浸透枡の西縁 = `masuUV`−`masuKen`/2)。四隅は礎石が欠く。
"""
import bpy, bmesh, sys, os, math, json, random, hashlib
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_sanno_shaden as SH
import build_sanno_buzai as SB
import build_tateishi as BT
import build_sanno_ido as IDO

KEN = 1.818
SHAKU = KEN / 6.0
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "sanno_sashizu.json")

# 指図に無い値【U 部材方 2026-09-23】
G = dict(
    hashira=0.1212,       # 柱 4寸角
    soishiTop=0.10,       # 礎石の天端(石敷天端=芯からの高さ)
    fuchiTop=IDO.G["top"],  # 縁石の天端 = 井筒の天端 = 井桁の下端(+0.05)
    keta=(0.1212, 0.12),  # 軒桁 幅×成
    hari=(0.1212, 0.15),  # 妻梁 幅×成
    ketaOut=0.30,         # 軒桁の木口の出(柱芯から妻側へ)
    munegi=(0.1212, 0.12),
    tsuka=0.09,           # 棟束
    taruki=(0.045, 0.06), taruPitch=SHAKU,   # 垂木 1尺割
    fukiT=0.05,           # こけら葺の葺き厚(野地込み)
    nokizuke=0.09,        # 軒付(軒先の厚み)
    step=0.012,           # こけらの葺き足の段
    courseN=16,           # 片流れの段数
    kokeraSeg=0.30,       # 葺き面の UV を貼り分ける区の長さ(棟の方向)
    kasa=(0.20, 0.08),    # 棟押え 幅×(峰からの)丈
    hafu=(0.03, 0.16),    # 破風板 厚×成
    yokogi=(0.10, 0.10),  # 釣瓶の横木 幅×成
    kuruma=(0.09, 0.04),  # 滑車 半径×厚
    slabRow=0.45, slabLen=0.58,   # 板石の割付の目安
    masuRim=0.10, masuPit=0.28, lidT=0.03, lidN=4, lidGap=0.012,
    joint=0.006,          # 石の面取り(見える目地の半分)
    slabTile=1.05,        # Kirishi の貼り寸(⛔ 0.44 を大きな石に使わない)
)
ALLOW = {"yakata": ("wood",), "ishiki": ("Kirishi", "Foundation_A_01", "wood")}


def spec():
    d = json.load(open(SASHIZU, encoding="utf-8"))["ido"]
    s = dict(ishikiKen=d["ishikiKen"], slope=d["ishikiSlope"], masuKen=d["masuKen"],
             masuDu=d["masuUV"][0] - d["uv"][0], pitchKen=d["hashiraPitchKen"], n=d["hashiraN"],
             soishi=d["soishiM"], yane=d["yane"], nokiH=d["nokiH"], muneH=d["muneH"],
             nokiDeKen=d["nokiDeKen"], hafuDeKen=d["hafuDeKen"],
             mori=[l["tM"] for l in d["moriLayers"]],
             igetaShaku=d["igetaShaku"], igetaMitsuke=d["igetaMitsukeM"], igetaDan=d["igetaDanN"],
             naikeiShaku=d["izutsu"]["naikeiShaku"], kabeAtsu=d["izutsu"]["kabeAtsuM"])
    if s["n"] != 4 or s["yane"] != "切妻" or abs(d["masuUV"][1] - d["uv"][1]) > 1e-9:
        raise SystemExit("[ido] ⛔ 指図 `ido` の型が生成器の前提(四本柱・切妻・枡は真東)と違う: %s" % s)
    # 井筒+井桁の生成器と同じ数か(⛔ 井桁の外形に合わせる約束)
    for k_s, k_i in (("igetaShaku", "igetaShaku"), ("igetaMitsuke", "igetaMitsukeM"),
                     ("igetaDan", "igetaDanN"), ("naikeiShaku", "naikeiShaku"), ("kabeAtsu", "kabeAtsuM")):
        if abs(s[k_s] - IDO.SPEC[k_i]) > 1e-9:
            raise SystemExit("[ido] ⛔ 指図 `ido.%s` が井桁の生成器(build_sanno_ido.SPEC)と違う" % k_s)
    A = s["ishikiKen"] * KEN / 2.0
    s.update(A=A, P=s["pitchKen"] * KEN / 2.0, k_slope=float(s["slope"][0]) / float(s["slope"][1]),
             r_out=IDO.SPEC["naikeiShaku"] * SHAKU / 2.0 + IDO.SPEC["kabeAtsuM"],
             masuX0=(s["masuDu"] - s["masuKen"] / 2.0) * KEN, masuX1=(s["masuDu"] + s["masuKen"] / 2.0) * KEN,
             masuZ=s["masuKen"] * KEN / 2.0,
             eave=(s["pitchKen"] / 2.0 + s["nokiDeKen"]) * KEN,
             gable=(s["pitchKen"] / 2.0 + s["hafuDeKen"]) * KEN)
    return s


def rng_of(*k):
    return random.Random(int(hashlib.sha1("|".join(map(str, k)).encode()).hexdigest()[:12], 16))


# =====================================================================================
# 論理 (u=東, v=北, h=上) の閉じた多面体を VM.Mesh へ積む。巻きは面ごとに外向きへ揃える
# =====================================================================================
def _emit(M, pts, uvs, center, mat):
    a, b, c = (Vector(p) for p in pts[:3])
    n = (b - a).cross(c - a)
    fc = sum((Vector(p) for p in pts), Vector()) / len(pts)
    if n.dot(fc - Vector(center)) < 0:
        pts = pts[::-1]; uvs = uvs[::-1]
    if len(pts) == 4:
        M.quad_uvs([SH.q(*p) for p in pts], uvs, mat)
    else:
        M.tri_uvs([SH.q(*p) for p in pts], uvs, mat)


def prism_v(M, prof, v0, v1, uv, mat, top_seg=None):
    """(u,h) の凸多角形 `prof` を v0..v1 へ押し出す。上面の木理は prof の辺の長手へ流す。"""
    ru0, rv0, ru1, rv1 = uv
    cu = sum(p[0] for p in prof) / len(prof); ch = sum(p[1] for p in prof) / len(prof)
    center = (cu, (v0 + v1) / 2.0, ch)
    n = len(prof)
    for i in range(n):
        p, q = prof[i], prof[(i + 1) % n]
        if i == 0 and top_seg:
            # ⭐ 葺き面(prof の 0→1 辺)は v を top_seg ごとに割り、**矩形の全幅を 1 区ずつ**貼る。
            #   ⛔ 1 枚で貼ると細い帯が 2.7m に引き伸ばされ、こけらが「棟へ流れる縦縞の板」に見えた
            #   (2026-09-23 真上の検証レンダで実見)。木理(v)は流れの方向に、段の丈ぶんだけ取る。
            ln = math.hypot(q[0] - p[0], q[1] - p[1])
            fv = min(1.0, ln / 1.8)
            ns = max(1, int(round((v1 - v0) / top_seg)))
            rr = rng_of("kokera", round(p[0], 4), round(p[1], 4))
            for j in range(ns):
                a, b = v0 + (v1 - v0) * j / ns, v0 + (v1 - v0) * (j + 1) / ns
                o = rr.uniform(0.0, 1.0 - fv)
                va, vb = rv0 + (rv1 - rv0) * o, rv0 + (rv1 - rv0) * (o + fv)
                pts = [(p[0], a, p[1]), (q[0], a, q[1]), (q[0], b, q[1]), (p[0], b, p[1])]
                _emit(M, pts, [(ru0, va), (ru0, vb), (ru1, vb), (ru1, va)], center, mat)
            continue
        # ⚠ 葺き面を割ったら**他の面も同じ所で割る**(割らないと T 字の継ぎ目 = 開いた辺が残る)
        ns = max(1, int(round((v1 - v0) / top_seg))) if top_seg else 1
        for j in range(ns):
            a, b = v0 + (v1 - v0) * j / ns, v0 + (v1 - v0) * (j + 1) / ns
            pts = [(p[0], a, p[1]), (q[0], a, q[1]), (q[0], b, q[1]), (p[0], b, p[1])]
            ua, ub = ru0 + (ru1 - ru0) * j / ns, ru0 + (ru1 - ru0) * (j + 1) / ns
            _emit(M, pts, [(ua, rv0), (ua, rv1), (ub, rv1), (ub, rv0)], center, mat)   # 辺の長手 → v(木理)
    us = [p[0] for p in prof]; hs = [p[1] for p in prof]
    du = max(us) - min(us) or 1.0; dh = max(hs) - min(hs) or 1.0
    for vv in (v0, v1):
        pts = [(p[0], vv, p[1]) for p in prof]
        uvs = [(ru0 + (ru1 - ru0) * (p[1] - min(hs)) / dh, rv0 + (rv1 - rv0) * (p[0] - min(us)) / du)
               for p in prof]
        if n == 4:
            _emit(M, pts, uvs, center, mat)
        else:
            for k in range(1, n - 1):
                _emit(M, [pts[0], pts[k], pts[k + 1]], [uvs[0], uvs[k], uvs[k + 1]], center, mat)


def wheel_u(M, uc, vc, hc, r, t, uv, mat, n=16):
    """軸が u(東西)の円盤(滑車の車)。"""
    ru0, rv0, ru1, rv1 = uv
    center = (uc, vc, hc)
    ring = [(vc + r * math.cos(2 * math.pi * i / n), hc + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        s0, s1 = i / float(n), (i + 1) / float(n)
        _emit(M, [(uc - t / 2, a[0], a[1]), (uc - t / 2, b[0], b[1]), (uc + t / 2, b[0], b[1]), (uc + t / 2, a[0], a[1])],
              [(ru0 + (ru1 - ru0) * s0, rv0), (ru0 + (ru1 - ru0) * s1, rv0),
               (ru0 + (ru1 - ru0) * s1, rv1), (ru0 + (ru1 - ru0) * s0, rv1)], center, mat)
    for uu in (uc - t / 2, uc + t / 2):
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            _emit(M, [(uu, vc, hc), (uu, a[0], a[1]), (uu, b[0], b[1])],
                  [((ru0 + ru1) / 2, (rv0 + rv1) / 2), (ru0, rv0), (ru1, rv0)], center, mat)


# =====================================================================================
# ① 井戸屋形(木部)
# =====================================================================================
def yakata(S, name):
    V.reset()
    ms, uv = SH.mats()
    W = SH.W
    M = VM.Mesh()
    P, A, ZG = S["P"], S["eave"], S["gable"]
    hs = G["hashira"] / 2.0
    # 葺き面の天端: 峰 = 棟押えの天端 − 棟押えの丈 / 軒先 = nokiH(段 step を含めて)
    apex = S["muneH"] - G["kasa"][1]
    base_tip = S["nokiH"] - G["step"]
    k = (apex - base_tip) / A

    def ytop(x):
        return apex - k * abs(x)

    def ybot(x):
        return ytop(x) - G["fukiT"]

    taru_bot = lambda x: ybot(x) - G["taruki"][1]
    keta_top = taru_bot(P)
    keta_bot = keta_top - G["keta"][1]
    munegi_top = taru_bot(0.0)
    munegi_bot = munegi_top - G["munegi"][1]
    hari_top, hari_bot = keta_bot, keta_bot - G["hari"][1]
    # ---- 柱(礎石の天端から軒桁の下端まで)
    for su in (-1, 1):
        for sv in (-1, 1):
            SH.box3(M, su * P - hs, su * P + hs, sv * P - hs, sv * P + hs, G["soishiTop"], keta_bot,
                    VM.sub(uv["wood"], 0.10 + 0.2 * (su > 0), 0.0, 0.40 + 0.2 * (su > 0), 1.0), W, grain="h")
    # ---- 軒桁(平側 ±u・v へ走る)
    kw = G["keta"][0] / 2.0
    for su in (-1, 1):
        SH.box3(M, su * P - kw, su * P + kw, -(P + G["ketaOut"]), P + G["ketaOut"], keta_bot, keta_top,
                uv["wood_h"], W, grain="v")
    # ---- 妻梁(妻側 ±v・u へ走る。柱の内面に突き付け)
    hw = G["hari"][0] / 2.0
    for sv in (-1, 1):
        SH.box3(M, -(P - hs), P - hs, sv * P - hw, sv * P + hw, hari_bot, hari_top, uv["wood_h"], W, grain="u")
    # ---- 棟束(妻梁の上)と棟木
    tw = G["tsuka"] / 2.0
    for sv in (-1, 1):
        SH.box3(M, -tw, tw, sv * P - tw, sv * P + tw, hari_top, munegi_bot, uv["wood"], W, grain="h")
    mw = G["munegi"][0] / 2.0
    SH.box3(M, -mw, mw, -(ZG - G["hafu"][0]), ZG - G["hafu"][0], munegi_bot, munegi_top, uv["wood_h"], W, grain="v")
    # ---- 垂木(棟木 → 軒桁 → 軒先の手前)
    tw2, th2 = G["taruki"]
    nt = int(math.floor((ZG - G["hafu"][0] - 0.06) / G["taruPitch"]))
    for i in range(-nt, nt + 1):
        vv = i * G["taruPitch"]
        for su in (-1, 1):
            x1 = A - 0.04
            p0 = (0.0, vv, taru_bot(0.0) + th2 / 2.0)
            p1 = (su * x1, vv, taru_bot(x1) + th2 / 2.0)
            SH.stick(M, p0, p1, tw2, th2, VM.sub(uv["wood"], 0.2, 0.0, 0.5, 1.0), W)
    # ---- こけら葺(片流れごとに courseN 段。段ごとに葺き足の段 step を立てる)
    N = G["courseN"]
    zr = ZG - G["hafu"][0]
    for su in (-1, 1):
        for i in range(N):
            x0, x1 = A * i / float(N), A * (i + 1) / float(N)
            last = (i == N - 1)
            prof = [(su * x0, ytop(x0)), (su * x1, ytop(x1) + G["step"]),
                    (su * x1, (ytop(x1) + G["step"] - G["nokizuke"]) if last else ybot(x1)),
                    (su * x0, ybot(x0))]
            prism_v(M, prof, -zr, zr, VM.sub(uv["wood"], 0.04, 0.0, 0.96, 1.0), W, top_seg=G["kokeraSeg"])
    # ---- 棟押え(峰に被せる箱)
    cw = G["kasa"][0] / 2.0
    SH.box3(M, -cw, cw, -ZG, ZG, ytop(cw) - 0.005, S["muneH"], uv["wood_h"], W, grain="v")
    # ---- 破風板(妻の両端。葺き面の上へ 0.02 出し、垂木の木口を隠す)
    ht, hh = G["hafu"]
    for sv in (-1, 1):
        zc = sv * (ZG - ht / 2.0)
        for su in (-1, 1):
            p0 = (0.0, zc, ytop(0.0) + 0.02 - hh / 2.0)
            p1 = (su * A, zc, ytop(A) + G["step"] + 0.02 - hh / 2.0)
            SH.stick(M, p0, p1, ht, hh, VM.sub(uv["wood"], 0.55, 0.0, 0.85, 1.0), W)
    # ---- 釣瓶の横木(妻梁から妻梁へ・井戸の芯の真上)と滑車
    yw, yh = G["yokogi"]
    y1 = hari_top - 0.02
    y0 = y1 - yh
    SH.box3(M, -yw / 2, yw / 2, -(P - hw), P - hw, y0, y1, uv["wood_h"], W, grain="v")
    r, t = G["kuruma"]
    hc = y0 - 0.05 - r
    wheel_u(M, 0.0, 0.0, hc, r, t, VM.sub(uv["wood"], 0.3, 0.2, 0.7, 0.8), W)
    for su in (-1, 1):   # 車の両脇の頬板(横木から吊る)
        SH.box3(M, su * (t / 2 + 0.004), su * (t / 2 + 0.019), -0.045, 0.045, hc - 0.04, y0,
                uv["wood"], W, grain="h")
    SH.box3(M, -(t / 2 + 0.019), t / 2 + 0.019, -0.012, 0.012, hc - 0.012, hc + 0.012, uv["wood"], W, grain="u")  # 軸
    o = M.to_object(name, ms)
    V.dedup_materials()
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    info = dict(apex=apex, k=k, keta=(keta_bot, keta_top), hari=(hari_bot, hari_top),
                munegi=(munegi_bot, munegi_top), yokogi=(y0, y1), kuruma_bottom=hc - r)
    return o, info


# =====================================================================================
# ② 板石敷一式(石はすべて Blender 座標で直に作る: Unity (X,Y,Z) → Blender (−X, −Z, Y))
# =====================================================================================
def bl(X, Z):
    return (-X, -Z)


def prism_xz(name, poly, y0, y1, mat, tile, bevel=None, uvrect=None):
    """Unity 平面 (X,Z) の多角形 `poly`(凹でもよい)を y0..y1 の柱体にする。"""
    bm = bmesh.new()
    lo = [bm.verts.new((bl(*p)[0], bl(*p)[1], y0)) for p in poly]
    hi = [bm.verts.new((bl(*p)[0], bl(*p)[1], y1)) for p in poly]
    bm.faces.new(hi); bm.faces.new(lo[::-1])
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    BT.ensure_outward(bm)
    if bevel:
        try:
            bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges), offset=bevel, offset_type='OFFSET',
                            segments=1, profile=0.5, affect='EDGES', clamp_overlap=True)
        except Exception as ex:
            print("[ido] 面取りを飛ばした %s: %s" % (name, ex))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4],
                          quad_method='BEAUTY', ngon_method='EAR_CLIP')
    BT.ensure_outward(bm)
    bm.normal_update()
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        ax = max(range(3), key=lambda kk: abs(f.normal[kk]))
        for lp in f.loops:
            co = lp.vert.co
            a, b = (co.x, co.y) if ax == 2 else ((co.x, co.z) if ax == 1 else (co.y, co.z))
            if uvrect:
                u0, v0, u1, v1 = uvrect
                fa, fb = (a / tile) % 1.0, (b / tile) % 1.0
                lp[uvl].uv = (u0 + (u1 - u0) * (0.05 + 0.9 * fa), v0 + (v1 - v0) * (0.05 + 0.9 * fb))
            else:
                lp[uvl].uv = (a / tile, b / tile)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def slope_shear(o, k, top_only_above=None):
    """東へ 1/n の水勾配: Unity Y −= k·X ⇔ Blender z += k·x。`top_only_above` より上の頂点だけ動かす。"""
    for v in o.data.vertices:
        if top_only_above is None or v.co.z > top_only_above:
            v.co.z += k * v.co.x
    o.data.update()


def arc(r, a0, a1, n):
    return [(r * math.cos(a0 + (a1 - a0) * i / float(n)), r * math.sin(a0 + (a1 - a0) * i / float(n)))
            for i in range(n + 1)]


def rot90(poly, k):
    out = poly
    for _ in range(k % 4):
        out = [(-z, x) for (x, z) in out]
    return out


def slab_rects(S):
    A, c, m = S["A"], S["fuchi_c"], S["masuZ"]
    s0, s1 = S["s0"], S["s1"]
    R = [(-s0, s0, c, A), (-s0, s0, -A, -c), (-A, -c, -s0, s0),
         (S["masuX1"], A, -m, m) if S["masuX1"] < A - 1e-6 else None,
         (c, A, m, s0), (c, A, -s0, -m)]
    for sx in (-1, 1):
        for sz in (-1, 1):
            R.append(tuple(sorted((sx * s1, sx * A))) + tuple(sorted((sz * s0, sz * A))))
            R.append(tuple(sorted((sx * s0, sx * s1))) + tuple(sorted((sz * s1, sz * A))))
    return [r for r in R if r and r[1] - r[0] > 1e-6 and r[3] - r[2] > 1e-6]


def split_rect(r, rng, tag):
    x0, x1, z0, z1 = r
    lx, lz = x1 - x0, z1 - z0
    along_x = lx >= lz
    L, D = (lx, lz) if along_x else (lz, lx)
    nrow = max(1, int(round(D / G["slabRow"])))
    out = []
    for i in range(nrow):
        d0, d1 = D * i / nrow, D * (i + 1) / nrow
        npc = max(1, int(round(L / G["slabLen"])))
        cuts = [L * j / npc for j in range(npc + 1)]
        if i % 2 == 1 and npc >= 2:
            cuts = [0.0] + [L * (j + 0.5) / npc for j in range(npc)] + [L]
        cuts = [cuts[0]] + [cc + rng.uniform(-0.04, 0.04) for cc in cuts[1:-1]] + [cuts[-1]]
        for a, b in zip(cuts[:-1], cuts[1:]):
            out.append((x0 + a, x0 + b, z0 + d0, z0 + d1) if along_x else (x0 + d0, x0 + d1, z0 + a, z0 + b))
    return out


def ishiki(S, name):
    V.reset()
    kir = SB.kirishi_material()
    fnd, frect = IDO.stone_mat()
    frect = VM.sub(frect, 0.05, 0.05, 0.95, 0.95)
    ms, uv = SH.mats()
    k = S["k_slope"]
    t_ita, t_suna, t_wari = S["mori"]
    y_ita_b = -t_ita
    y_wari_t = -(t_ita + t_suna)
    y_wari_b = y_wari_t - t_wari
    A, R = S["A"], S["r_out"]
    objs = []
    # ---- 割栗(平らな天端。東の枡の穴・井筒の円を抜く)
    for q in range(4):
        base = [(A, -A)]
        if q == 0:
            base += [(A, -S["masuZ"]), (S["masuX0"], -S["masuZ"]), (S["masuX0"], S["masuZ"]), (A, S["masuZ"])]
        base += [(A, A)]
        poly = rot90(base, q) + rot90(arc(R, math.pi / 4, -math.pi / 4, 12), q)
        objs.append(prism_xz("%s_wari_%d" % (name, q), poly, y_wari_b, y_wari_t, fnd, 1.82, uvrect=frect))
    # ---- 縁石(井桁の足元を締める切石 4 石。天端 = 井筒の天端)
    c, s0 = S["fuchi_c"], S["s0"]
    for q in range(4):
        poly = rot90([(s0, -s0), (c, -s0), (c, s0), (s0, s0)] + arc(R, math.pi / 4, -math.pi / 4, 12), q)
        objs.append(prism_xz("%s_fuchi_%d" % (name, q), poly, y_wari_t, G["fuchiTop"], kir,
                             G["slabTile"], bevel=G["joint"]))
    # ---- 礎石(割栗の天端に据える。天端は水平)
    hs = S["soishi"] / 2.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            X, Z = sx * S["P"], sz * S["P"]
            poly = [(X - hs, Z - hs), (X + hs, Z - hs), (X + hs, Z + hs), (X - hs, Z + hs)]
            objs.append(prism_xz("%s_soishi_%d%d" % (name, sx, sz), poly, y_wari_t, G["soishiTop"], kir,
                                 SB.KIRISHI_TILE, bevel=G["joint"] * 2))
    # ---- 板石(水勾配)と敷砂(割栗の上〜板石の下。勾配は砂の厚みで取る)
    rng = rng_of("sanno_ido_ishiki")
    nslab = 0
    for ri, r in enumerate(slab_rects(S)):
        x0, x1, z0, z1 = r
        rect = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
        sand = prism_xz("%s_suna_%d" % (name, ri), rect, y_wari_t, y_ita_b, fnd, 1.82, uvrect=frect)
        slope_shear(sand, k, top_only_above=(y_wari_t + y_ita_b) / 2.0)
        objs.append(sand)
        for si, (a0, a1, b0, b1) in enumerate(split_rect(r, rng, ri)):
            o = prism_xz("%s_ita_%d_%d" % (name, ri, si), [(a0, b0), (a1, b0), (a1, b1), (a0, b1)],
                         y_ita_b, 0.0, kir, G["slabTile"], bevel=G["joint"])
            slope_shear(o, k)
            objs.append(o); nslab += 1
    # ---- 浸透枡(伏せ枡): 縁の切石 4 石(天端は板石と同じ勾配)・底の割栗・板蓋
    X0, X1, Zm, w = S["masuX0"], S["masuX1"], S["masuZ"], G["masuRim"]
    rims = [(X0, X0 + w, -Zm, Zm), (X1 - w, X1, -Zm, Zm), (X0 + w, X1 - w, Zm - w, Zm), (X0 + w, X1 - w, -Zm, -Zm + w)]
    for i, (a0, a1, b0, b1) in enumerate(rims):
        o = prism_xz("%s_masu_rim_%d" % (name, i), [(a0, b0), (a1, b0), (a1, b1), (a0, b1)],
                     y_wari_b, 0.0, kir, G["slabTile"], bevel=G["joint"])
        slope_shear(o, k, top_only_above=-0.05)
        objs.append(o)
    pit = [(X0 + w, -Zm + w), (X1 - w, -Zm + w), (X1 - w, Zm - w), (X0 + w, Zm - w)]
    objs.append(prism_xz("%s_masu_soko" % name, pit, y_wari_b, -G["masuPit"], fnd, 1.82, uvrect=frect))
    M = VM.Mesh()
    nL, gap = G["lidN"], G["lidGap"]
    lx0, lx1 = X0 + 0.04, X1 - 0.04
    bw = (lx1 - lx0 - gap * (nL - 1)) / nL
    for i in range(nL):
        a0 = lx0 + i * (bw + gap)
        SH.box3(M, a0, a0 + bw, -Zm + 0.04, Zm - 0.04, 0.0, G["lidT"],
                VM.sub(uv["wood"], 0.1 + 0.2 * (i % 4), 0.0, 0.25 + 0.2 * (i % 4), 1.0), SH.W, grain="v")
    lid = M.to_object(name + "_masu_futa", ms)
    slope_shear(lid, k)
    objs.append(lid)
    V.dedup_materials()
    o = V.join(objs, name)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, dict(nslab=nslab)


# =====================================================================================
# 検算
# =====================================================================================
def uverts(o, mat=None):
    names = [m.name.split('.')[0] if m else "" for m in o.data.materials]
    U = SH.unity_verts(o)
    if mat is None:
        return U
    idx = {i for i, n in enumerate(names) if n == mat}
    vs = set()
    for p in o.data.polygons:
        if p.material_index in idx:
            vs.update(p.vertices)
    return [U[i] for i in vs]


def bbox(U):
    return [(min(t[i] for t in U), max(t[i] for t in U)) for i in range(3)]


def report_common(o, allow):
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    bx = bbox(SH.unity_verts(o))
    print("IDO %s  W(X) %.3f × H(Y) %.3f × D(Z) %.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f]  tris=%d  mats=%s"
          % (o.name, bx[0][1] - bx[0][0], bx[1][1] - bx[1][0], bx[2][1] - bx[2][0],
             bx[0][0], bx[0][1], bx[1][0], bx[1][1], bx[2][0], bx[2][1], tris, mats))
    bad = [m for m in mats if m not in allow]
    print("  材 %s" % ("⭕ キット/既存の名のみ" if not bad else "⛔ %s" % bad))
    # 非多様体の辺(閉じていない所)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    nb = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    print("  開いた辺(溶接後の境界辺) %d" % nb)
    return not bad, bx, tris


def report_yakata(o, S, info):
    ok, bx, tris = report_common(o, ALLOW["yakata"])
    A = S["A"]
    xmax = max(abs(bx[0][0]), abs(bx[0][1]))
    print("  雨落ち: 軒先の水平投影 ±%.4f / 石敷の半幅 ±%.4f / 差 %+.4f %s"
          % (xmax, A, xmax - A, "⭕" if xmax <= A + 1e-4 else "⛔ 石敷の外へ出る"))
    print("  破風の出: 妻の外面 ±%.4f(柱芯/2 + hafuDe = %.4f)" % (max(abs(bx[2][0]), abs(bx[2][1])), S["gable"]))
    U = SH.unity_verts(o)
    tip = max(t[1] for t in U if abs(abs(t[0]) - A) < 1e-4)
    print("  軒先の葺き面の天端 %.3f(nokiH %.3f)/ 棟押えの天端 %.3f(muneH %.3f)/ 勾配 %.3f(%.1f 寸)"
          % (tip, S["nokiH"], bx[1][1], S["muneH"], info["k"], info["k"] * 10))
    print("  柱の根 %.3f(= 礎石の天端)/ 軒桁 %.3f〜%.3f / 妻梁 %.3f〜%.3f / 棟木 %.3f〜%.3f"
          % (bx[1][0], info["keta"][0], info["keta"][1], info["hari"][0], info["hari"][1],
             info["munegi"][0], info["munegi"][1]))
    print("  釣瓶の横木 %.3f〜%.3f / 滑車の下端 %.3f / 井桁の天端 %.3f(離れ %.3f)"
          % (info["yokogi"][0], info["yokogi"][1], info["kuruma_bottom"],
             IDO.G["top"] + IDO.SPEC["igetaMitsukeM"] * IDO.SPEC["igetaDanN"],
             info["kuruma_bottom"] - (IDO.G["top"] + IDO.SPEC["igetaMitsukeM"] * IDO.SPEC["igetaDanN"])))
    tip_under = S["nokiH"] - G["nokizuke"]
    print("  軒先の下端 %.3f(軒下をくぐる丈)" % tip_under)
    # 左右(東西)の鏡像を集合で
    Us = {(round(t[0], 4), round(t[1], 4), round(t[2], 4)) for t in U}
    Um = {(round(-t[0], 4), round(t[1], 4), round(t[2], 4)) for t in U}
    Vm = {(round(t[0], 4), round(t[1], 4), round(-t[2], 4)) for t in U}
    print("  鏡像: 東西 %s / 南北 %s" % ("⭕" if Us == Um else "⛔ %d" % len(Us ^ Um),
                                     "⭕" if Us == Vm else "⛔ %d" % len(Us ^ Vm)))
    return ok, tris


def report_ishiki(o, S, info):
    ok, bx, tris = report_common(o, ALLOW["ishiki"])
    A, k = S["A"], S["k_slope"]
    U = uverts(o, "Kirishi")
    top = [t for t in U if t[1] > -0.02 - k * A and abs(t[1] + k * t[0]) < 1e-4]
    print("  石敷 外形 X[%.4f,%.4f] Z[%.4f,%.4f](1.8間角の半幅 %.4f)"
          % (bx[0][0], bx[0][1], bx[2][0], bx[2][1], A))
    ys_w = [t[1] for t in top if t[0] < -A + 0.02]; ys_e = [t[1] for t in top if t[0] > A - 0.02]
    if ys_w and ys_e:
        print("  板石の天端 西端 %+.4f / 東端 %+.4f / 落ち %.4f(1/%d × %.3f = %.4f)"
              % (max(ys_w), max(ys_e), max(ys_w) - max(ys_e), S["slope"][1], 2 * A, 2 * A * k))
    print("  板石 %d 枚 / 縁石 4 / 礎石 4(%.3f 角・天端 +%.3f)/ 枡 %.3f 角(X %.4f〜%.4f)"
          % (info["nslab"], S["soishi"], G["soishiTop"], S["masuKen"] * KEN, S["masuX0"], S["masuX1"]))
    print("  縁石: 内 = 井筒の外径 r %.4f / 外 = 半幅 %.4f(枡の西縁)/ 軸上の幅 %.4f / 礎石の内隅 %.4f"
          % (S["r_out"], S["fuchi_c"], S["fuchi_c"] - S["r_out"], S["s0"]))
    print("  層: 板石 %.2f / 敷砂 %.2f(勾配は砂の厚みで取る)/ 割栗 %.2f / 最下端 %.3f"
          % (S["mori"][0], S["mori"][1], S["mori"][2], bx[1][0]))
    return ok, tris


# =====================================================================================
# 検証レンダ
# =====================================================================================
def hook_kirishi():
    """読み直した FBX の `Kirishi` は名前だけの入れ物(`hook_textures` はキットの画像しか引かない)。
    ⛔ 放っておくと画像欠落の桃色で刷れて、石の見え方を判断できない。山王の既存テクスチャを結ぶ。"""
    for m in bpy.data.materials:
        if m.name.split('.')[0] != SB.KIRISHI or not m.use_nodes:
            continue
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        for n in [n for n in nt.nodes if n.type in ('TEX_IMAGE', 'NORMAL_MAP')]:
            nt.nodes.remove(n)
        ai = nt.nodes.new('ShaderNodeTexImage')
        ai.image = bpy.data.images.load(os.path.join(SB.KIRISHI_DIR, "T_Kirishi_Albedo.png"), check_existing=True)
        nt.links.new(ai.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Alpha'].default_value = 1.0


def shots(objs, tag, magenta_under=False):
    V.hook_textures()
    hook_kirishi()
    os.makedirs(SHOT, exist_ok=True)
    out = []

    def one(cam, look, fn, ortho=None, res=(1400, 1000), mag=False):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        if mag:
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
        for m in bpy.data.materials:
            m.use_backface_culling = True
        f = os.path.join(SHOT, "sanno_ido_%s_%s.png" % (tag, fn))
        V.render(f); out.append(f)
    # Unity (X東,Y,Z北) → Blender (−X, −Z, Y)。南東から見下ろす = Blender (−X, +Y)
    one((-5.2, 5.6, 4.2), (0.0, 0.0, 1.1), "oblique")
    one((0.0, -0.001, 9.0), (0.0, 0.0, 0.0), "top", ortho=3.8, res=(1100, 1100))
    one((0.0, 9.0, 1.5), (0.0, 0.0, 1.5), "elev_s", ortho=3.9, res=(1200, 1100))
    one((-9.0, 0.0, 1.5), (0.0, 0.0, 1.5), "elev_e", ortho=3.9, res=(1200, 1100))
    one((-2.3, 2.1, 1.25), (-0.3, 0.2, 0.0), "idobata", res=(1400, 1000))
    one((-0.3, 0.4, 0.9), (-1.5, -0.8, 2.6), "miage", res=(1400, 1000), mag=True)
    one((3.6, 3.4, 3.4), (0.0, 0.0, 1.9), "tsuma_sw", res=(1400, 1000), mag=True)
    return out


def build_all(argv):
    S = spec()
    S["fuchi_c"] = S["masuX0"]                      # 縁石の外 = 枡の西縁
    S["s0"] = S["P"] - S["soishi"] / 2.0            # 礎石の内隅
    S["s1"] = S["P"] + S["soishi"] / 2.0
    if S["s0"] > S["fuchi_c"] + 1e-9 or S["r_out"] >= S["fuchi_c"]:
        raise SystemExit("[ido] ⛔ 縁石の外形が礎石・井筒と噛み合わない: s0 %.4f c %.4f r %.4f"
                         % (S["s0"], S["fuchi_c"], S["r_out"]))
    want = [a for a in argv if not a.startswith("--")] or ["yakata", "ishiki"]
    built = {}
    for key in want:
        if key == "yakata":
            name = "Sanno_Ido_Yakata_%dx%dx%d" % (int(round(S["pitchKen"] * KEN * 1000)),
                                                  int(round(S["nokiH"] * 1000)), int(round(S["muneH"] * 1000)))
            o, info = yakata(S, name)
            ok, tris = report_yakata(o, S, info)
        elif key == "ishiki":
            name = "Sanno_Ido_Ishiki_%dx%d" % (int(round(S["ishikiKen"] * KEN * 1000)), int(S["slope"][1]))
            o, info = ishiki(S, name)
            ok, tris = report_ishiki(o, S, info)
        else:
            raise SystemExit("[ido] 部材名は yakata / ishiki: %s" % key)
        if not ok:
            raise SystemExit("[ido] ⛔ 想定外の材")
        path = os.path.join(OUT, name + ".fbx")
        built[key] = (name, path, tris)
        if "--no-export" not in argv:
            V.export_fbx([o], path)
            print("[ido] 書き出し %s (tris %d)" % (path, tris))
    return built


def render_set(built):
    """書き出した FBX(+ 既存の井筒+井桁)を読み直して並べて刷る — Unity に入る物そのものを見る。"""
    V.reset()
    objs = []
    igeta = os.path.join(OUT, "Sanno_Ido_Igeta_909x450.fbx")
    for p in [igeta] + [b[1] for b in built.values()]:
        if os.path.exists(p):
            objs += VM.import_fbx_abs(p)
    for f in shots(objs, "set"):
        print("RENDER " + f)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    built = build_all(argv)
    if "--render" in argv:
        render_set(built)


if __name__ == "__main__":
    main()
