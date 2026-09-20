# -*- coding: utf-8 -*-
"""山王権現社の**鳥居** — **石造の明神鳥居**。一ノ鳥居・二ノ鳥居に**同じ1点**を使う。

    blender --background --python Tools/Blender/build_sanno_torii.py -- [--render] [--no-export]

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指図 `bom[鳥居]` の在庫が **「無い」**。在庫の `Own.Torii`(`Okabe_Torii`)は**素木・内法 1.30 m の点景**で、
稲荷の参道用。参道の麓道を跨ぐ石鳥居には一点も当たらない。

━━━ 形式【A 考証 2026-09-20 ── 普請奉行から。⛔ 部材方が決めた事ではない】━━━━━━━━━━━━━━━━
**石造の明神鳥居**(『江戸名所百人美女』「山王御宮」駒絵・安政4年 = 基準年次の1年後 の原寸実見):
笠木に**反り**・**島木**あり・**貫は柱を貫いて木鼻を出す**・**額束に扁額(朱地)**・足元は**八角の段付き台石**。
⛔ **三角の破風を付けない**(山王鳥居 = 合掌鳥居にしない)。⛔ **崩れ・欠けを表現しない** ──
安政2年10月の地震で一ノ鳥居は倒れたが石は砕けず、基準年次は**同じ石で起こし直した直後**の姿【A】。
⭐ **一ノ鳥居・二ノ鳥居は同形式**。二ノ鳥居が小ぶりに見えるのは駒絵の遠近の誇張なので
  ⛔ **寸法比を数値に採らない** ⇒ **同寸の1点を2基に使う**(⛔ 大小を作り分けない)。

━━━ 寸法【U 部材方 2026-09-20 ── 指図に無い(`torii[].acc` が「柱間・総高=部材方の設計値」)】━━━━━
⭐ 決めた値は **柱間(柱芯々)3 間 = 5.454 m** と **総高(笠木の上端・中央)4 間 = 7.272 m** の二つ。
  他(柱径・貫・島木・笠木・台石・反り)はこの二つと明神鳥居の通例からの従属値。
【なぜこの大きさか ── 道が上下から挟む】
  ・**下限(跨げること)**: 柱の内法 = 5.454 − 0.60 = **4.854 m**。二ノ鳥居の立つ辻の
    南北小路は路面幅 5.5 m(`fumotomichi[東区間].w`)⇒ 内法が路面のほぼ一杯を占め、
    柱は路肩から 0.32 m 内に立つ。切絵図の『开は道幅いっぱいを跨ぐ』【S】の読みと合う。
  ・**上限(道敷を跨がせない)**: 笠木の長さ **7.654 m** < 道敷の幅(領域 12〜15 m)。
    一ノ鳥居の立つ東西道の領域はその地点で 18.4 m(`fumotomichi[東西道].area` から)⇒ 収まる。
  ・比 総高/柱間 = 1.333 は明神鳥居の通例(1.3〜1.5)の内。石の鳥居としては大きいほうだが、
    将軍家の産土神の一ノ鳥居なので過大ではない(京都八坂の石鳥居は総高 9.5 m 級)。
  ⛔ 駒絵から寸法は出ない(縮尺が無い)⇒ 確度は【U】で、⛔【A】を名乗らせない。

━━━ 材 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・石 = `Kirishi`(切石・叩き仕上げ。`Assets/Edo/Materials/Sanno/Kirishi.mat`)── 基壇・礎盤と同じ材。
  ⛔ `M_FJG_Rock_001`(苔むした自然石)を貼らない — 据え直した直後の切石は暗い苔石ではない。
・扁額の朱地 = **`Shu_Torii`**(`Assets/Edo/Materials/Shu_Torii.mat` ── **既にある**)。⛔ 新規に作らない。
  ⚠⚠ この材は `Assets/Edo/Materials/`(Sanno の一つ上)に在るので、**山王の remap の借り先に
    そのフォルダが要る**(`EdoSannoShaBuilder.RemapSannoShinzo` の `donorDirs` に足した)。
    足さないと扁額だけ真っ白で出る。

━━━ 軸(Unity ローカル)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
幅(柱の並び)= X / 高さ = Y / 厚み = Z。**見え面(扁額のある正面)= +Z**。
ピボット = **柱芯の中央・地盤レベル**(台石は Y<0 へ `SINK` 根入れ)。⛔ `SeatBottom` で据えない。
⭕ X についても Z についても**柱は対称**(扁額だけが +Z 側)⇒ 裏から見ても姿は変わらない。

⚠ 軸の写像は**実測で押さえてある**(2026-09-20): `SH.box3(u,v,h)` → Unity (X=u, Y=h, Z=v) の**恒等**。
  ⛔ `VM.Mesh.box(x,y,z)` は **Unity X = −x** と反転するので、こちらでは使わない。
"""
import bpy, sys, os, math
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_sanno_shaden as SH
import build_sanno_buzai as SB

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
K = 1.818

# ---- 決めた二つ【U】--------------------------------------------------------------
SPAN_KEN = 3.0          # 柱間(柱芯々)[間]
TALL_KEN = 4.0          # 総高(笠木の上端・中央)[間]
# ---- 従属値(明神鳥居の通例)【U 部材方】-----------------------------------------
G = dict(
    colD=0.60, colTaper=0.90,      # 柱の径(足元)と上端の比(胴張りの代わりの直線テーパ)
    korobi=1 / 40.0,               # ころび(内転び)= 柱高に対する頂の内寄せ
    sink=0.35,                     # 台石の根入れ(Y<0)
    daiLoAcross=1.45, daiLoTop=0.12,   # 下段の台石(八角・対辺)と天端
    daiHiAcross=1.12, daiHiTop=0.45,   # 上段の台石(八角・対辺)と天端
    kasagiH=0.44, kasagiD=0.74,    # 笠木(丈・見込み)
    shimagiH=0.38, shimagiD=0.62,  # 島木
    kasagiOut=1.10,                # 笠木・島木が柱芯(足元の通り)から出る長さ
    sori=0.30,                     # 反り(端の持ち上がり。笠木・島木を**同じ曲線**に乗せる)
    nukiH=0.40, nukiD=0.30,        # 貫(丈・見込み)
    nukiTop=5.05,                  # 貫の上端
    kibana=0.38,                   # 木鼻(柱の外面から出る長さ)
    gakuW=0.50, gakuD=0.24,        # 額束
    henW=0.86, henH=1.00, henT=0.06, henFrame=0.09,   # 扁額(朱地)と石の縁
    seg=16,                        # 反りの分割
)
# ⭐ `Kirishi` のタイルの実寸。⛔ 基壇の 0.44 を流用しない ── `T_Kirishi_Normal.png` は
#   **4分割の継ぎ目が入った normal**なので、0.44 で貼ると 7.65 m の笠木に継ぎ目が 17 本立ち、
#   一本の切石が**小口積みの壁**に見える(2026-09-20 の検証レンダで実見)。
#   ⇒ 1.05 に伸ばす。⚠ 石の鳥居の笠木は実際に数石を継ぐので、継ぎ目が数本出るのは正しい。
TILE = 1.05
SHU_LIN = (0.52, 0.075, 0.045)     # 朱(線形)。⚠ **レンダを本当らしくするためだけ** —
#   FBX は材質「名」しか運ばないので、Unity は `Assets/Edo/Materials/Shu_Torii.mat` を remap で結ぶ
ALLOWED = ("Kirishi", "Shu_Torii")
STONE, SHU = 0, 1


def shu_material():
    """扁額の朱地。⛔ **新規の材ではない** — `Assets/Edo/Materials/Shu_Torii.mat` が既にある。
    名前だけを運び(`V.named_material`)、検証レンダのために朱の基色を入れておく。"""
    m = V.named_material("Shu_Torii")
    m.use_nodes = True
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b:
        b.inputs['Base Color'].default_value = SHU_LIN + (1.0,)
        b.inputs['Roughness'].default_value = 0.55
    return m


# ==========================================================================
# 面の道具 — 論理 (u,v,h)。UV は `Kirishi` を実寸でタイル貼り(⛔ 一点貼り・引き伸ばしをしない)
# ==========================================================================
def face(M, pts, mat=STONE, tile=None):
    """論理 (u,v,h) の多角形(4点または3点)を1枚置く。UV は面の主軸で実寸タイル。"""
    t = tile or TILE
    a = Vector(pts[1]) - Vector(pts[0])
    b = Vector(pts[2]) - Vector(pts[0])
    n = a.cross(b)
    ax = max(range(3), key=lambda i: abs(n[i]))
    uvs = []
    for p in pts:
        if ax == 2:                 # h が主 → 天地の面
            uvs.append((p[0] / t, p[1] / t))
        elif ax == 0:               # u が主 → 木口
            uvs.append((p[1] / t, p[2] / t))
        else:                       # v が主 → 見え面
            uvs.append((p[0] / t, p[2] / t))
    q = [SH.q(*p) for p in pts]
    if len(pts) == 4:
        M.quad_uvs(q, uvs, mat)
    else:
        M.tri_uvs(q, uvs, mat)


def prism(M, ring, h0, h1, mat=STONE, cap=True):
    """(u,v) の閉じた環を h0→h1 へ押し出した角柱。環は**上から見て反時計回り**で渡す。"""
    n = len(ring)
    for i in range(n):
        (u0, v0), (u1, v1) = ring[i], ring[(i + 1) % n]
        face(M, [(u0, v0, h0), (u1, v1, h0), (u1, v1, h1), (u0, v0, h1)], mat)
    if cap:
        for i in range(1, n - 1):
            face(M, [ring[0] + (h1,), ring[i] + (h1,), ring[i + 1] + (h1,)], mat)
            face(M, [ring[0] + (h0,), ring[i + 1] + (h0,), ring[i] + (h0,)], mat)


def octagon(uc, vc, across):
    """対辺の幅 `across` の正八角形の環(上から見て反時計回り)。"""
    r = across / 2.0 / math.cos(math.pi / 8)
    return [(uc + r * math.cos(math.pi / 8 + math.pi / 4 * i),
             vc + r * math.sin(math.pi / 8 + math.pi / 4 * i)) for i in range(8)]


def leaning_column(M, u_base, h0, h1, r0, taper, lean, n=20):
    """**ころび付きの円柱**。足元の芯 u_base から、頂で `lean` だけ内(原点)へ寄る。
    径は h1 で r0*taper へ。⛔ 真っ直ぐに立てない — 明神鳥居の柱は内へ転ぶ。"""
    sg = -1.0 if u_base > 0 else 1.0
    seg = 10
    for s in range(seg):
        t0, t1 = s / float(seg), (s + 1) / float(seg)
        for (t, r, uc, hh) in (("", 0, 0, 0),):
            pass
        z0, z1 = h0 + (h1 - h0) * t0, h0 + (h1 - h0) * t1
        c0, c1 = u_base + sg * lean * t0, u_base + sg * lean * t1
        ra0 = r0 * (1.0 - (1.0 - taper) * t0)
        ra1 = r0 * (1.0 - (1.0 - taper) * t1)
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            p00 = (c0 + ra0 * math.cos(a0), ra0 * math.sin(a0), z0)
            p01 = (c0 + ra0 * math.cos(a1), ra0 * math.sin(a1), z0)
            p11 = (c1 + ra1 * math.cos(a1), ra1 * math.sin(a1), z1)
            p10 = (c1 + ra1 * math.cos(a0), ra1 * math.sin(a0), z1)
            face(M, [p00, p01, p11, p10], STONE)
    return u_base + sg * lean


def swept_bar(M, u0, u1, v0, v1, h0, h1, rise, mat=STONE, seg=16):
    """**反りに乗せた横材**(笠木・島木)。`rise(t)` = u の位置 t∈[0,1] での持ち上がり。
    ⭐ 笠木と島木に**同じ `rise`** を渡すこと — 片方だけ反らせると間が楔形に開く。"""
    for s in range(seg):
        t0, t1 = s / float(seg), (s + 1) / float(seg)
        a0, a1 = u0 + (u1 - u0) * t0, u0 + (u1 - u0) * t1
        r0, r1 = rise(t0), rise(t1)
        face(M, [(a0, v1, h0 + r0), (a0, v1, h1 + r0), (a1, v1, h1 + r1), (a1, v1, h0 + r1)], mat)  # +v
        face(M, [(a0, v0, h0 + r0), (a1, v0, h0 + r1), (a1, v0, h1 + r1), (a0, v0, h1 + r0)], mat)  # −v
        face(M, [(a0, v0, h1 + r0), (a1, v0, h1 + r1), (a1, v1, h1 + r1), (a0, v1, h1 + r0)], mat)  # 天
        face(M, [(a0, v0, h0 + r0), (a0, v1, h0 + r0), (a1, v1, h0 + r1), (a1, v0, h0 + r1)], mat)  # 底
    for (uu, sg) in ((u0, -1), (u1, +1)):
        r = rise(0.0 if sg < 0 else 1.0)
        pts = [(uu, v0, h0 + r), (uu, v1, h0 + r), (uu, v1, h1 + r), (uu, v0, h1 + r)]
        face(M, pts if sg > 0 else pts[::-1], mat)


# ==========================================================================
def build(name):
    span = SPAN_KEN * K
    tall = TALL_KEN * K
    half = span / 2.0
    r0 = G["colD"] / 2.0
    shimagi_bot = tall - G["kasagiH"] - G["shimagiH"]     # 島木の下端 = 柱頭
    col_h0 = G["daiHiTop"] - 0.15                         # 柱の足元(上段の台石へ差し込む)
    lean = (shimagi_bot - col_h0) * G["korobi"]
    ms = [SB.kirishi_material(), shu_material()]
    M = VM.Mesh()

    tops = []
    for sgn in (-1, +1):
        ub = sgn * half
        prism(M, octagon(ub, 0.0, G["daiLoAcross"]), -G["sink"], G["daiLoTop"])
        prism(M, octagon(ub, 0.0, G["daiHiAcross"]), G["daiLoTop"], G["daiHiTop"])
        tops.append(leaning_column(M, ub, col_h0, shimagi_bot, r0, G["colTaper"], lean))
    half_top = abs(tops[1])
    r_top = r0 * G["colTaper"]

    # 貫(柱を貫いて木鼻を出す)── 貫の高さでの柱芯から木鼻を測る
    t_nuki = (G["nukiTop"] - G["nukiH"] / 2.0 - col_h0) / (shimagi_bot - col_h0)
    u_nuki = half - lean * t_nuki
    r_nuki = r0 * (1.0 - (1.0 - G["colTaper"]) * t_nuki)
    nuki_end = u_nuki + r_nuki + G["kibana"]
    prism(M, [(-nuki_end, -G["nukiD"] / 2.0), (nuki_end, -G["nukiD"] / 2.0),
              (nuki_end, G["nukiD"] / 2.0), (-nuki_end, G["nukiD"] / 2.0)],
          G["nukiTop"] - G["nukiH"], G["nukiTop"])
    # 額束(貫の上端 → 島木の下端)
    prism(M, [(-G["gakuW"] / 2.0, -G["gakuD"] / 2.0), (G["gakuW"] / 2.0, -G["gakuD"] / 2.0),
              (G["gakuW"] / 2.0, G["gakuD"] / 2.0), (-G["gakuW"] / 2.0, G["gakuD"] / 2.0)],
          G["nukiTop"], shimagi_bot)
    # 扁額(朱地 + 石の縁)── **正面 = +Z(= +v)**。⛔ 裏にも付けない(額は正面だけ)。
    # ⭐ 縁を回さないと**朱の板を貼っただけ**に見える(2026-09-20 の検証レンダで実見)。
    #   ⛔ 文字は入れない(銘は読めていない)。
    hz = (G["nukiTop"] + shimagi_bot) / 2.0
    v0, v1 = G["gakuD"] / 2.0, G["gakuD"] / 2.0 + G["henT"]
    rect = lambda w: [(-w / 2.0, v0), (w / 2.0, v0), (w / 2.0, v1), (-w / 2.0, v1)]
    prism(M, rect(G["henW"]), hz - G["henH"] / 2.0, hz + G["henH"] / 2.0, mat=SHU)
    fr, fw = G["henFrame"], G["henW"] / 2.0 + G["henFrame"]
    vf = v1 + 0.025
    for (a0, a1, b0, b1) in ((-fw, fw, hz + G["henH"] / 2.0, hz + G["henH"] / 2.0 + fr),
                             (-fw, fw, hz - G["henH"] / 2.0 - fr, hz - G["henH"] / 2.0),
                             (-fw, -G["henW"] / 2.0, hz - G["henH"] / 2.0 - fr, hz + G["henH"] / 2.0 + fr),
                             (G["henW"] / 2.0, fw, hz - G["henH"] / 2.0 - fr, hz + G["henH"] / 2.0 + fr)):
        prism(M, [(a0, v0), (a1, v0), (a1, vf), (a0, vf)], b0, b1)
    # 島木 + 笠木 ── 同じ反りに乗せる
    ke = half + G["kasagiOut"]
    sori = lambda t: G["sori"] * (2.0 * t - 1.0) ** 2
    swept_bar(M, -ke, ke, -G["shimagiD"] / 2.0, G["shimagiD"] / 2.0,
              shimagi_bot, shimagi_bot + G["shimagiH"], sori, seg=G["seg"])
    swept_bar(M, -ke, ke, -G["kasagiD"] / 2.0, G["kasagiD"] / 2.0,
              tall - G["kasagiH"], tall, sori, seg=G["seg"])

    o = M.to_object(name + "_body", ms)
    o.name = name
    o.data.name = name
    V.sel([o])
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))   # ⭐ 円柱は滑らか・八角の台石と木口は角のまま
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    info = dict(span=span, tall=tall, uchinori=span - G["colD"], kasagiLen=2 * ke,
                shimagi_bot=shimagi_bot, half_top=half_top, r_top=r_top, nuki_end=nuki_end)
    return o, info


def part_name():
    return "Sanno_Torii_%dx%d" % (round(SPAN_KEN * K * 1000), round(TALL_KEN * K * 1000))


# ==========================================================================
# 検算
# ==========================================================================
def report(o, info):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    print("TORII %s  W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), tris))
    print("  柱間(柱芯々)%.3f / 内法 %.3f / 総高(笠木の上端・中央)%.3f / 反りの頂 %.3f"
          % (info["span"], info["uchinori"], info["tall"], max(ys)))
    print("  笠木の長さ %.3f / 木鼻の先 ±%.3f / 柱頭の芯 ±%.3f(ころびで %.3f 内へ)"
          % (info["kasagiLen"], info["nuki_end"], info["half_top"], info["span"] / 2 - info["half_top"]))
    ok = []
    # ① 道が挟む(⛔ 数を写さない — `fumotomichi` から引く)
    import json
    with open(os.path.join(V.REPO, "docs", "Sashizu", "sanno_sashizu.json")) as f:
        d = json.load(f)
    w_lane = [r["w"] for r in d["fumotomichi"] if r["name"].startswith("東区間")][0]
    # ⚠ **片側**で見る(⛔ 両側の合計で見ない — 2026-09-20 に一度そう書いて閾を外した)。
    #   柱が路面の内へ入る量が片側 0.5 m 以内なら「路肩に立って道幅いっぱいを跨ぐ」姿になる。
    into = (w_lane - info["uchinori"]) / 2.0
    ok.append(("柱が路面の内へ入る量(片側)≤ 0.5m ── 道幅いっぱいを跨ぐ姿",
               -0.1 <= into <= 0.5,
               "路面 %.2f / 内法 %.3f ⇒ 片側 %.3f" % (w_lane, info["uchinori"], into)))
    ok.append(("笠木が道敷(領域の下限 12m)を跨がない", info["kasagiLen"] < 12.0,
               "笠木 %.3f" % info["kasagiLen"]))
    # ② 形式の検査 — 貫が柱を貫いて出ているか / 額は正面だけか / 三角の破風が無いか
    ok.append(("貫が柱の外面より外へ出ている(木鼻)", info["nuki_end"] > info["half_top"] + info["r_top"],
               "木鼻の先 %.3f > 柱の外面 %.3f" % (info["nuki_end"], info["half_top"] + info["r_top"])))
    shu = [i for i, m in enumerate(o.data.materials) if m and m.name.split('.')[0] == "Shu_Torii"]
    zs_shu = [U[i][2] for pg in o.data.polygons if pg.material_index in shu for i in pg.vertices]
    ok.append(("扁額は正面(+Z)だけ", bool(zs_shu) and min(zs_shu) > 0.0,
               "朱の Z %.3f〜%.3f" % (min(zs_shu), max(zs_shu)) if zs_shu else "朱が無い"))
    # ③ 左右対称(EDO-0161: Unity X = −Blender X の符号反転が姿を変えないこと)
    key = lambda t: (round(t[0] / 1e-3), round(t[1] / 1e-3), round(t[2] / 1e-3))
    ok.append(("左右対称(X)", set(key(t) for t in U) == set(key((-t[0], t[1], t[2])) for t in U), ""))
    bad = [t for t in ok if not t[1]]
    for (lab, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", lab, note))
    bm = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bm else "⛔ %s" % bm))
    return not bad and not bm


def shots(o, info):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0.0))
    out = []

    def one(cam, look, fn, res=(1400, 1400), ortho=None):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_torii_%s.png" % fn)
        V.render(f); out.append(f)
    one((0.0, -16.0, 4.0), (0.0, 0.0, 3.6), "front_elev", ortho=10.5)      # 正面(扁額のある側)
    one((7.0, -11.0, 5.5), (0.0, 0.0, 3.3), "oblique")                     # 斜め
    one((0.9, -3.4, 4.6), (info["span"] / 2 * 0.6, 0.0, 5.6), "kibana", res=(1400, 1100))  # 貫の木鼻と柱頭
    one((0.4, -3.0, 4.6), (0.0, 0.0, 6.0), "gaku", res=(1200, 1200))       # 扁額と額束
    one((-1.6, -2.6, 0.7), (-info["span"] / 2, 0.0, 0.5), "daiishi", res=(1200, 1100))  # 八角の台石
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    V.reset()
    o, info = build(part_name())
    ok = report(o, info)
    files = shots(o, info) if "--render" in argv else []
    for f in files:
        print("RENDER " + f)
    if not ok and "--allow" not in argv:
        raise SystemExit("[torii] ⛔ 検算に落ちた")
    if "--no-export" not in argv:
        o.location = (0.0, 0.0, 0.0)
        path = os.path.join(OUT, o.name + ".fbx")
        V.export_fbx([o], path)
        print("[torii] 書き出し %s" % path)


if __name__ == "__main__":
    main()
