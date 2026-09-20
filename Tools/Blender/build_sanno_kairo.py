# -*- coding: utf-8 -*-
"""山王権現社の**回廊**(屋根付きの廊)— 楼門の両脇から社殿へ回る翼、北・南の2本。

    blender --background --python Tools/Blender/build_sanno_kairo.py -- [--wing N|S|both] [--render] [--no-export]

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指図 `bom[回廊(屋根付きの廊)]` の在庫が **「無い」**。代用を禁じたので今は丸ごと欠落している。
参考にした在庫の作り: 切妻の瓦場 = `build_sanno_gokusho_ikko.kirizuma_hon`(キットの瓦モジュール
`GR._tile_field_fast`)/ 連子窓・腰板 = `build_sanno_sukibei`(透塀)/ 銅瓦 = `SH.to_copper`。
⛔ 瓦をゼロから作らない・⛔ 新規マテリアルを作らない。

━━━ 平面(指図 `runs[Kairo_N]` / `runs[Kairo_S]` が正典。⛔ ここに数を書かない)━━━━━━━━━━━━━━
・走り `ken`[間]×`const.ken` = 北 20.65 / 南 17.55 m【A 明治16年実測図】を `bays`【U】で等分。
・梁間 `bari`[間]×`const.ken` = 4.2 m【A】を `bariBays`【U】= 2 で等分 ⇒ **柱は3列**(外・中・内)。
・基壇は石垣(`base:"Ishigaki"`・`seat:29.0`)⇒ **部材は基壇を持たない**。床 = 石垣の天端 = Y0。

━━━ 丈(床 = Y0 から)【U 部材方 2026-09-20 ── 指図に無い。`_pending`「回廊の軒高・棟高…」の①】━━━
⭐ **決めた値は軒先 `eaveZ` = 2.10 の一つだけ**。勾配はキットの瓦モジュールの素の勾配 `GR.RATIO`
  (5.5寸)なので、**桁の天端も大棟の上端も従属値**(`const.muneHeightRule` と同じ立て方)。
  ⛔ 棟高を数で決めて勾配を曲げない(瓦場を剪断すると割付が崩れる)。
【なぜ 2.10 か ── 上下を二つの実測が挟む】
  ・**下限**: 袖塀 `Sanno_Sodebei_4200_d1560-700` の屋根の天端は門の敷居(28.3)から 2.505
    (`bom[袖塀…].outlineM`「全体(瓦を含む)」)= 回廊の床 29.0 からは **1.805**。
    ⇒ 軒先はこれより上でなければ「低い屋根付きの袖塀」が回廊の軒から突き出る。2.10 で **0.295** 空く。
  ・**上限**: 楼門の軒高 4.80(丸桁の上端・`bom[楼門…].ruikei`)= 敷居から ⇒ 絶対 33.10。
    回廊の大棟の上端は従属値で 3.99(絶対 32.99)⇒ **楼門の軒より 0.11 低い**。
  ・⛔ **楼門の軒先(敷居+4.07 = 絶対 32.37)より下には納まらない** ── そこまで下げると軒先が 1.48 になり、
    袖塀(1.805)が回廊の軒の上へ出る。⇒ **「回廊の棟は楼門の軒先より高く、丸桁より低い」**が
    この三者の寸法が許す唯一の帯。相手の寸法が動いたら測り直す。
  ・社殿(拝殿は全高 11.83)・楼門(棟 7.87)より遥かに低く、透塀の棟(2.25)より高い。
腰板の天端 0.75 / 連子 0.75〜1.80(内法)/ 小壁 1.88〜桁の下端 ── 透塀 `HT` の腰 0.75 に揃えた【U】。

━━━ 姿 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・**外(東)の面は閉じ、内(西)は開ける** ── 回廊は境内の囲いを兼ねるので外側に腰板+連子窓を立て、
  中庭の側は柱だけで開ける【U 部材方。⛔ 史料は回廊の壁を言わない】。
・梁間二間なので**中の列に柱**が立ち、桁の上で梁を渡して束で棟木を受ける。
・両端は妻(切妻)で、**門側の妻は袖塀の木口を受ける閉じた壁**(`joints` の突き付け・隙間は不可)。
・屋根 = 銅瓦葺【U `runs[Kairo_*].roof`】。破風板は付けるが ⛔ 懸魚・木連格子は付けない(社殿に譲る)。

━━━ 軸(Unity ローカル)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
走り = X / 高さ = Y / 梁間 = Z。⭐ **見え面(閉じた壁)= +Z = 外(東)**。ピボット = **柱芯の矩形の中心・床(座)**。
⭕ 走り X について対称なので**門側がどちらの X 端でも据わる** ⇒ 北翼・南翼とも同じ yaw
  (`grid.frames[東面]` 込みで +Z が東を向く向き)。⛔ 翼ごとに向きを変えない。
"""
import bpy, sys, os, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as GR
import build_sanno_shaden as SH
import build_sanno_gokusho as GK
import build_sanno_romon as RM

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "sanno_sashizu.json")

# ---- 丈と作りの値【U 部材方 2026-09-20 ── 指図に無い】-------------------------------
G = dict(
    eaveZ=2.10,          # ⭐ 軒先の高さ(床から)。決めた値はここ一つ(上の章に根拠)
    eaveKen=0.5,         # 軒の出[間](柱芯から)= 0.909
    kerabaKen=0.25,      # ケラバの出[間] = 0.4545
    colD=0.27,           # 柱の径(総円柱)。taper で僅かに胴張り
    colTaper=0.94,
    sobanH=0.12, sobanHalf=0.22,   # 礎盤(切石)の丈と半幅
    sink=0.20,           # 根入れ(Y<0 へ出る。⛔ 0 にすると地面の起伏で足元が透ける)
    dodaiH=0.12,         # 外の面の土台(腰板の下)
    koshi=0.75,          # 腰板の天端(透塀 `HT.koshi` に揃える)
    uchinori=1.80,       # 内法(連子の上端)
    kamoiH=0.08,         # 内法の鴨居の丈
    kabeT=0.07,          # 小壁(漆喰)の厚み
    renjiW=0.045, renjiP=0.12,     # 連子子の見付・割り
    ketaW=0.18, ketaH=0.20,        # 桁(柱の上)
    hariW=0.16,          # 梁(梁間を渡す)
    munagiW=0.14, tsukaW=0.12,     # 棟木・束
    nageshiH=0.09, nageshiT=0.05,  # 内の面の内法長押(開けた側の見切り)
    tsumaT=0.07,         # 妻壁の厚みの半分
    ridgeW=0.34, ridgeH=0.30, ridgeSeat=0.10,    # 大棟(瓦場の頂から seat だけ沈める)
    sodeW=0.24, sodeH=0.20,                      # 袖瓦
    hafuW=0.32, hafuT=0.10, hafuDrop=0.48,       # 破風板
    oniSc=0.8,           # 鬼(社殿・楼門より小振り)
)
ALLOWED = ("wood", "wall C", "Kirishi", "Doukawara")


def lin(a, b, n):
    return [a + (b - a) * i / float(n) for i in range(n + 1)]


# ==========================================================================
# 指図を読む(⛔ 走り・梁間・間数の数をここに書かない)
# ==========================================================================
def spec(wing):
    """指図 `runs[Kairo_<wing>]` から (走りm, 梁間m, 間数, 梁間の間数) を出す。"""
    import json
    with open(SASHIZU) as f:
        d = json.load(f)
    K = float(d["const"]["ken"])
    name = "Kairo_" + wing
    for r in d["runs"]:
        if r.get("name") == name:
            return dict(run=float(r["ken"]) * K, span=float(r["bari"]) * K,
                        bays=int(r["bays"]), bariBays=int(r["bariBays"]), K=K,
                        seat=float(r["seat"]))
    raise SystemExit("[kairo] ⛔ 指図 runs に %s が無い" % name)


def part_name(sp):
    """⚠ mm は `round`(⛔ floor しない)。綴りが寸法の出所ではない — 指図が正典。"""
    return "Sanno_Kairo_%dx%dken_%dx%d" % (sp["bays"], sp["bariBays"],
                                           round(sp["run"] * 1000), round(sp["span"] * 1000))


# ==========================================================================
# 屋根 — キットの瓦の切妻を**銅瓦**にした物。⭐ 大棟は走り(Unity X)方向
# ==========================================================================
def kirizuma_dou(name, run, span, eave, keraba, eaveZ):
    """run = 大棟の長さ(柱芯)・span = 梁間(柱芯)。返り値 (object, half, k)。
    ⭐ `build_sanno_gokusho_ikko.kirizuma_hon` と同じ組み方だが、**90°回さない**
      (あちらは大棟が南北 = Unity Z。回廊の大棟は走り = Unity X)。"""
    x0, x1 = -keraba, run + keraba          # 大棟の走り(Blender x)
    y0, y1 = -eave, span + eave             # 流れ(Blender y)
    ym = (y0 + y1) / 2.0
    h = (y1 - y0) / 2.0 * GR.RATIO
    pieces = [GR._tile_field_fast([[(x0, y0), (x1, y0), (x1, ym), (x0, ym)]], (x0, y0), 90, 0.0, name + "_A"),
              GR._tile_field_fast([[(x1, y1), (x0, y1), (x0, ym), (x1, ym)]], (x0, y1), 270, 0.0, name + "_B")]
    p = GR.palette()
    zr = h - G["ridgeSeat"]
    pieces += GR.ridge((x0, ym, zr), (x1, ym, zr), name + "_omune", w=G["ridgeW"], h=G["ridgeH"])
    pieces += GR.oni((x0 + 0.10, ym, zr), (-1, 0), name + "_oni0", scale=G["oniSc"])
    pieces += GR.oni((x1 - 0.10, ym, zr), (1, 0), name + "_oni1", scale=G["oniSc"])
    geo = []
    for gx, inward in ((x0, +1), (x1, -1)):
        g = GR.gable(gx, inward, y0, y1, 0.0, ym, h, name + "_g", p, thick=0.10,
                     bw=G["hafuW"], bt=G["hafuT"], drop=G["hafuDrop"], lattice=False, gegyo=False)
        bpy.data.objects.remove(g[0][0], do_unlink=True)      # 妻壁(先頭)は捨てる — 壁の通りで別に立てる
        geo += g[1:]
        sx = gx + inward * 0.06
        for uy, sg in ((y0, +1), (y1, -1)):                   # 袖瓦(破風の天端に被る列)
            stop = ym - sg * (G["ridgeW"] / 2.0 + 0.03)
            zst = (abs(stop - y0) if sg > 0 else abs(y1 - stop)) * GR.RATIO
            pieces += GR.ridge((sx, uy, 0.22), (sx, stop, zst + 0.22), name + "_sode", w=G["sodeW"], h=G["sodeH"])
    for o, uv in geo:
        if o:
            if uv:
                V.set_uv(o, uv)
            pieces.append(o)
    V.dedup_materials()
    o = V.join([q for q in pieces if q], name)
    V.set_origin(o, (run / 2.0, span / 2.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    o.data.transform(Matrix.Translation((0.0, 0.0, eaveZ)))
    o.data.update()
    bpy.context.view_layer.update()
    return o, (y1 - y0) / 2.0, GR.RATIO


# ==========================================================================
# 軸部(論理 u = Unity X = 走り / v = Unity Z = 梁間 / h = Unity Y)
# ==========================================================================
def outer_wall(M, uv, us, vo, top):
    """外(+Z)の面 — 柱間ごとに 土台・腰板(裏板つき)・連子窓・小壁。
    ⛔ 腰板は `panel_ita` だけにしない(目地から光が抜ける)— 裏板を1枚通す。"""
    pr = G["colD"] / 2.0
    kt = G["kabeT"] / 2.0
    z0 = G["sobanH"]
    zd = z0 + G["dodaiH"]
    zk = G["koshi"]
    zu = G["uchinori"]
    for i in range(len(us) - 1):
        s0, s1 = us[i] + pr, us[i + 1] - pr
        SH.box3(M, s0, s1, vo - 0.09, vo + 0.09, -G["sink"], zd, uv["wood_h"], SH.W, grain="u")   # 土台
        SH.panel_ita(M, s0, s1, "u", vo, zd, zk, uv["wood"], SH.W, t=0.028)                       # 腰板
        SH.box3(M, s0, s1, vo - 0.012, vo + 0.012, zd, zk, uv["wood_h"], SH.W, grain="u")         # 腰板の裏板
        SH.box3(M, s0, s1, vo - 0.07, vo + 0.07, zk, zk + 0.06, uv["wood_h"], SH.W, grain="u")    # 窓台
        n = max(3, int(round((s1 - s0) / G["renjiP"])))
        for j in range(n):                                                                        # 連子子
            c = s0 + (s1 - s0) * (j + 0.5) / n
            SH.box3(M, c - G["renjiW"] / 2.0, c + G["renjiW"] / 2.0, vo + 0.01, vo + 0.055,
                    zk + 0.06, zu, uv["wood"], SH.W, grain="h")
        SH.box3(M, s0, s1, vo - 0.07, vo + 0.07, zu, zu + G["kamoiH"], uv["wood_h"], SH.W, grain="u")  # 内法の鴨居
        SH.box3(M, s0, s1, vo - kt, vo + kt, zu + G["kamoiH"], top, uv["wall"], SH.WC, grain="u")      # 小壁


def inner_open(M, uv, us, vi, top):
    """内(−Z)の面 — 開ける。内法長押と小壁だけを通して柱の上を見切る。"""
    pr = G["colD"] / 2.0
    kt = G["kabeT"] / 2.0
    zu = G["uchinori"]
    for i in range(len(us) - 1):
        s0, s1 = us[i] + pr, us[i + 1] - pr
        SH.box3(M, s0, s1, vi - G["nageshiT"], vi + G["nageshiT"], zu, zu + G["nageshiH"],
                uv["wood_h"], SH.W, grain="u")
        SH.box3(M, s0, s1, vi - kt, vi + kt, zu + G["nageshiH"], top, uv["wall"], SH.WC, grain="u")


def tsuma_wall(M, uv, uu, hv, zroof):
    """妻(走りの端)の壁 — 床から屋根の裏まで閉じる。⭐ 門側はここへ袖塀の木口が突き付く。"""
    t = G["tsumaT"]
    zk = G["koshi"]
    vs = lin(-hv, hv, 16)
    GK.vstrip_v(M, uu - t, uu + t, vs, lambda vv: zk, lambda vv: zroof(vv) - 0.04, uv["wall"], SH.WC)
    SH.panel_ita(M, -hv, hv, "v", uu, -G["sink"], zk, uv["wood"], SH.W, t=0.028)          # 腰板
    SH.box3(M, uu - 0.012, uu + 0.012, -hv, hv, -G["sink"], zk, uv["wood_h"], SH.W, grain="v")   # 裏板


def build(wing):
    sp = spec(wing)
    name = part_name(sp)
    run, span = sp["run"], sp["span"]
    hu, hv = run / 2.0, span / 2.0
    eave, ker = G["eaveKen"] * sp["K"], G["kerabaKen"] * sp["K"]
    ms, uv = SH.mats()
    roof, half, k = kirizuma_dou(name + "_roof", run, span, eave, ker, G["eaveZ"])
    # ⭐ 大棟は走り方向 ⇒ 名目の屋根面は **|Z|(梁間)の関数**(⛔ |X| で書くと屋根が転ぶ)
    surf = lambda z_abs: G["eaveZ"] + k * (half - z_abs)
    zf = lambda X, Z: surf(abs(Z))
    inside = lambda X, Z: abs(X) <= hu - 0.30 and 0.30 < abs(Z) < half - 0.30
    off = GK.roof_dmin(roof, inside, zf) - 0.01
    slab = GK.noji_slab(name + "_noji", lambda X, Z: abs(X) <= hu + ker and abs(Z) <= half,
                        (-(hu + ker), hu + ker, -half, half), zf, off)
    keta_top = surf(hv) + off - 0.03            # 桁の天端 = 野地の下面(瓦を突き抜けない)
    top = keta_top - G["ketaH"]                 # 桁の下端 = 小壁の上端
    zroof = lambda vv: surf(abs(vv)) + off      # 妻壁の上端(屋根の裏なり)

    M = VM.Mesh()
    us, vs = lin(-hu, hu, sp["bays"]), lin(-hv, hv, sp["bariBays"])
    pts = [(uu, vv) for uu in us for vv in vs]
    # 礎盤(切石)+ 総円柱
    stones = SH.soban(pts, -G["sink"], G["sobanH"], G["sobanHalf"], name + "_soban")
    for (uu, vv) in pts:
        SH.cyl(M, uu, vv, G["sobanH"], keta_top, G["colD"] / 2.0, uv["wood"], SH.W,
               n=12, taper=G["colTaper"])
    outer_wall(M, uv, us, vs[-1], top)          # +Z = 外(東)
    inner_open(M, uv, us, vs[0], top)           # −Z = 内(西)
    for vv in (vs[0], vs[-1]):                  # 桁(ケラバの下まで通す)
        SH.box3(M, -(hu + ker - 0.05), hu + ker - 0.05, vv - G["ketaW"] / 2.0, vv + G["ketaW"] / 2.0,
                top, keta_top, uv["wood_h"], SH.W, grain="u")
    for uu in us:                               # 梁(梁間を渡す)+ 束 + 中の柱の上
        SH.box3(M, uu - G["hariW"] / 2.0, uu + G["hariW"] / 2.0, -hv, hv, top, keta_top,
                uv["wood_h"], SH.W, grain="v")
        SH.box3(M, uu - G["tsukaW"] / 2.0, uu + G["tsukaW"] / 2.0, -G["tsukaW"] / 2.0, G["tsukaW"] / 2.0,
                keta_top, zroof(0.0) - 0.04, uv["wood"], SH.W, grain="h")
    SH.box3(M, -(hu + ker - 0.05), hu + ker - 0.05, -G["munagiW"] / 2.0, G["munagiW"] / 2.0,
            zroof(0.0) - 0.04 - G["munagiW"], zroof(0.0) - 0.04, uv["wood_h"], SH.W, grain="u")   # 棟木
    for uu in (us[0], us[-1]):
        tsuma_wall(M, uv, uu, hv, zroof)
    body = M.to_object(name + "_body", ms)

    V.dedup_materials()
    o = V.join([body, roof, slab] + stones, name)
    SH.to_copper(o)                             # ⭐ 瓦・棟・鬼 → `Doukawara`(銅瓦葺)
    V.sel([o]); bpy.ops.object.material_slot_remove_unused()
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    info = dict(hu=hu, hv=hv, half=half, k=k, off=off, keta_top=keta_top, top=top,
                eave=eave, ker=ker, sp=sp)
    return o, info


# ==========================================================================
# 検算
# ==========================================================================
def report(o, info):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    mt, ytop, orn = SH.mune_top(o, 'x')
    sp = info["sp"]
    print("KAIRO %s  W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), tris))
    print("  走り %.3f(%d 間)× 梁間 %.3f(%d 間)/ 軒先 %.3f / 桁の天端 %.3f / 大棟の上端 %.3f / 鬼の頂 %.3f"
          % (sp["run"], sp["bays"], sp["span"], sp["bariBays"], G["eaveZ"], info["keta_top"], mt, ytop))
    print("  軒の出 %.3f / ケラバの出 %.3f / 勾配 %.4f / 瓦の谷 %.3f" % (info["eave"], info["ker"], info["k"], info["off"]))
    # 取り合いの相手との上下(⛔ 数を写さない — 相手の bom の実測から引く)
    print("  ▸ 袖塀の屋根の天端(座 %.1f から 1.805)< 軒先 %.3f ⇒ 余裕 %.3f"
          % (sp["seat"], G["eaveZ"], G["eaveZ"] - 1.805))
    print("  ▸ 大棟の上端(絶対 %.3f)< 楼門の軒高(敷居28.3+4.80 = 33.100)⇒ 余裕 %.3f"
          % (sp["seat"] + mt, 33.100 - (sp["seat"] + mt)))
    bad = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bad else "⛔ %s" % bad))
    # 走り方向の対称 ── ⭐ **北翼・南翼で yaw を変えずに済む根拠**。材ごとに見る:
    #   軸部(wood / wall C / Kirishi)が対称なら、門側の妻がどちらの X 端でも同じ姿。
    #   ⚠ 瓦(Doukawara)はモジュール 2.004 の位相が端で切れるので非対称でよい(袖瓦が隠す)。
    key = lambda t: (round(t[0] / 1e-3), round(t[1] / 1e-3), round(t[2] / 1e-3))
    sym = {}
    for mi, m in enumerate(o.data.materials):
        vids = set()
        for pg in o.data.polygons:
            if pg.material_index == mi:
                vids.update(pg.vertices)
        # ⚠ **集合**で見る(⛔ 並べた列で比べない — 同じ座標の頂点の重複数が左右で違い、
        #   対称なのに「非対称」と出る。2026-09-20 に一度そう読んだ)
        pts = [U[i] for i in vids]
        sym[m.name.split('.')[0]] = (set(key(t) for t in pts)
                                     == set(key((-t[0], t[1], t[2])) for t in pts))
    body_ok = all(v for kk, v in sym.items() if kk != SH.DOU_NAME)
    print("  走り X の鏡像対称 軸部 %s %s" % ("⭕" if body_ok else "⛔",
          " / ".join("%s %s" % (kk, "⭕" if v else "×") for kk, v in sym.items())))
    return not bad and body_ok, dict(mune=mt, oni=ytop, sym=sym)


def soffit(o, info):
    """軒裏・ケラバ裏の帯の下から真上へ — 瓦(`Doukawara`)に先に当たる/空へ抜ける を数える。
    ⛔ 空へ抜けたら野地が張れていない(軒裏から空が見える)。"""
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    mats = o.data.materials
    hu, hv = info["hu"], info["hv"]
    x1, z1 = hu + info["ker"] - 0.05, hv + info["eave"] - 0.05
    cu = miss = tot = 0
    n = 48
    for i in range(n + 1):
        for j in range(n + 1):
            X = -x1 + 2 * x1 * i / float(n)
            Z = -z1 + 2 * z1 * j / float(n)
            if abs(X) < hu + 0.10 and abs(Z) < hv + 0.10:
                continue
            loc, nrm, idx, dist = bvh.ray_cast(Vector((-X, -Z, 0.9)), Vector((0, 0, 1)), 12.0)
            tot += 1
            if idx is None:
                miss += 1; continue
            m = mats[o.data.polygons[idx].material_index]
            if m and m.name.split('.')[0] == SH.DOU_NAME:
                cu += 1
    ok = cu == 0 and miss == 0
    print("  検算 軒裏・ケラバ裏 真上の光線 %d: 瓦に先に当たる %d / 空へ抜ける %d %s"
          % (tot, cu, miss, "⭕" if ok else "⛔"))
    return ok


def tsuma_seal(o, info):
    """**妻の壁に穴が無いか** — 門側の妻は袖塀の木口を受ける(`joints` 隙間は不可)。
    袖塀の断面(厚み ±0.5・丈 0〜1.805)を走る光線が、妻の面で必ず何かに当たることを数える。"""
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    hu = info["hu"]
    miss = tot = 0
    for i in range(25):
        for j in range(25):
            Z = -0.5 + 1.0 * i / 24.0
            Y = 0.02 + (1.805 - 0.02) * j / 24.0
            # 部材の外(−X 側)から +X へ撃つ
            loc, nrm, idx, d = bvh.ray_cast(Vector((hu + 1.0, -Z, Y)), Vector((-1, 0, 0)), 3.0)
            tot += 1
            if idx is None:
                miss += 1
    ok = miss == 0
    print("  検算 妻の壁(袖塀の木口が当たる断面 ±0.5 × 0〜1.805)の光線 %d: 抜け %d %s"
          % (tot, miss, "⭕" if ok else "⛔"))
    return ok


def shots(o, info, tag):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    # ⭐ 地面は **Y0(= 石垣の天端 = 床)**。⛔ 根入れの底(−sink)に置かない —
    #   礎盤の埋まる 0.20 が露出して「基礎が浮いている」絵になる(2026-09-20 に一度そう焼いた)
    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0.0))
    hu, hv = info["hu"], info["hv"]
    out = []

    def one(cam, look, fn, res=(1600, 1100), ortho=None):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "sanno_kairo_%s_%s.png" % (tag, fn))
        V.render(f); out.append(f)
    # Blender = (−X, −Z, Y)
    one((hu * 0.9, -(hv + 16.0), 9.0), (0.0, 0.0, 1.6), "outer_oblique")       # 外(東)から
    one((-hu * 0.9, hv + 16.0, 9.0), (0.0, 0.0, 1.6), "inner_oblique")         # 内(西)から
    one((-(hu + 11.0), 1.5, 4.5), (-hu, 0.0, 1.9), "tsuma", res=(1400, 1100))  # 妻(袖塀が突き付く面)
    one((hu - 1.2, hv - 1.0, 1.5), (-hu * 0.5, -hv + 0.5, 1.7), "interior", res=(1400, 1100))
    one((0.0, -(hv + 14.0), 2.0), (0.0, 0.0, 2.0), "outer_elev", ortho=max(8.0, info["sp"]["run"] * 1.1))
    one((hu * 0.35, -(hv + info["eave"] + 0.5), 0.7), (hu * 0.1, -(hv + info["eave"] * 0.5), 2.25),
        "soffit", res=(1400, 1100))     # 軒裏を下から見上げる(⛔ 軒先の小口を横から撮らない)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    wings = ["N", "S"]
    for i, a in enumerate(argv):
        if a == "--wing" and i + 1 < len(argv) and argv[i + 1] in ("N", "S"):
            wings = [argv[i + 1]]
    for wing in wings:
        V.reset()
        o, info = build(wing)
        ok, meas = report(o, info)
        sok = soffit(o, info)
        tok = tsuma_seal(o, info)
        files = []
        if "--render" in argv:
            files = shots(o, info, wing)
        for f in files:
            print("RENDER " + f)
        if not (ok and sok and tok) and "--allow" not in argv:
            raise SystemExit("[kairo] ⛔ 材・軒裏・妻の検算に落ちた")
        if "--no-export" not in argv:
            o.location = (0.0, 0.0, 0.0)
            path = os.path.join(OUT, o.name + ".fbx")
            V.export_fbx([o], path)
            print("[kairo] 書き出し %s" % path)


if __name__ == "__main__":
    main()
