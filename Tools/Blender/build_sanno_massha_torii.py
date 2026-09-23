# -*- coding: utf-8 -*-
"""山王権現社の**末社(稲荷社)の小鳥居** — **木造朱塗りの明神鳥居**。1基だけ。

    blender --background --python Tools/Blender/build_sanno_massha_torii.py -- [--render] [--no-export]

━━━ なぜ新造するか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
考証方が『江戸名所図会・山王』(NDL pid 2563386 コマ7)を原寸実見し、北東の社叢の際に題箋「いなり」と
**小社+その前に鳥居1基**を確かめた【S 図の実見 2026-09-22】。指図の `torii[]` は一ノ・二ノの2基だけで
この末社の鳥居を持たない。在庫も当たらない:
・`Sanno_Torii_5454x7272`(一ノ・二ノ)は**石造・柱間3間**の参道の鳥居 ⇒ 末社の前には過大。
  ⛔ **倍率で縮めない**(石の目地・八角の段付き台石・扁額まで一緒に縮むので石鳥居の縮小模型になる)。
・`Own.Torii`(`Okabe_Torii`)は**素木・内法 1.30 m** の点景で、岡部邸の指図が
  「玉垣・朱鳥居は使わない」と明記した邸の専用品 ⇒ 朱の稲荷には当たらない。

━━━ 形式【U 部材方 2026-09-22 ── 指図に無い。名所図会からは柱間も塗りも読めない】━━━━━━━━━━
**木造朱塗りの明神鳥居**(笠木に反り・島木あり・貫は柱を貫いて木鼻を出し楔を打つ・額束あり)。
⭕ そう決めた理由(**確度は【U 類型】。⛔【A】を名乗らせない**):
 ① **稲荷の鳥居は朱**が江戸の通例。同じ境内の稲荷社本体(`Sanno_Inari_Kasuga_1ken`)が既に
   高欄を `Shu_Torii`(朱)で焼いてあり、その前に立つ鳥居だけ素木にすると一具に見えない。
 ② **石にしない** — 一ノ・二ノ鳥居と同形式の石鳥居にすると、姿が同じで大きさだけ違う物が
   境内に3基並ぶ(= 縮小模型に見える)。参道の鳥居は石、末社の鳥居は木、と**材で格を分ける**。
 ③ **扁額を付けない** — 銘(「正一位稲荷大明神」等)は読めていない【?】。⛔ 読めない字を作らない。
   ⇒ 額束だけを立てる。**結果として前後(Z)も左右(X)も対称**になり、据える向きの取り違えが起きない。
⛔ **千本鳥居(明治以降の奉納鳥居の列)にしない** — 1基だけ。
⛔ **今の日枝神社(戦後再建)の姿を採らない**。基準年次は安政3年(1856)。

━━━ 寸法【U 部材方 2026-09-22】━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⭐ 決めた値は **柱間(柱芯々)1間 = 1.818 m** と **総高(笠木の上端・中央)1.5間 = 2.727 m** の二つ。
  他(柱径・貫・島木・笠木・根巻石・反り)はこの二つと明神鳥居の通例からの従属値。
【なぜこの大きさか ── 上下を稲荷社の実メッシュが挟む】(数は `Sanno_Inari_Kasuga_1ken.fbx` の実測)
  ・**上限(祠を食わない)**: 笠木の長さ 2.538 < 稲荷社の**軒幅 3.028** ⇒ 参道の正面から見て
    鳥居の笠木が祠の軒の内に収まり、鳥居が祠を隠さない。
    総高 2.727 < 稲荷社の**軒先 2.90**(⇒ 大棟 3.775 とは 1.05 の差)⇒ 祠のほうが高く見える。
  ・**下限(くぐれること)**: 内法幅 1.618 / 島木の下端まで 2.427 ⇒ 人がくぐれる。
  ・比 総高/柱間 = 1.50 は明神鳥居の通例(1.3〜1.5)の上端。小鳥居は柱が相対的に細く高く見えるので
    この比を採った。柱径 0.20 = 柱間/9.1(通例 1/9〜1/12)。

━━━ 材 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・木部(柱・貫・楔・額束・島木・笠木)= **`Shu_Torii`**(`Assets/Edo/Materials/Shu_Torii.mat`──**既にある**)。
  ⛔ 新規に作らない。⚠ この材は `Assets/Edo/Materials` **直下**に在るので、山王の remap の
  `donorDirs` にそのフォルダが要る(2026-09-20 に足してある)。足さないと鳥居が真っ白で出る。
・根巻石 = `Kirishi`(切石。基壇・礎盤と同じ材)。⭐ タイルは**礎盤と同じ 0.44**
  (⛔ 石鳥居の 1.05 を流用しない ── あれは 7.65 m の笠木に継ぎ目を出さないための値)。

━━━ 軸(Unity ローカル)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
幅(柱の並び)= X / 高さ = Y / 厚み = Z。**正面(くぐる向き)= +Z**。
ピボット = **柱芯の中央・地盤レベル**(根巻石は Y<0 へ `SINK` 根入れ)。⛔ `SeatBottom` で据えない。
⭕ X についても Z についても対称 ⇒ 裏から見ても姿は変わらない(扁額を付けていないため)。
⚠ 軸の写像は石鳥居と同じ道具(`build_sanno_torii.face` = `SH.q`)を通すので恒等。
"""
import bpy, sys, os, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_sanno_shaden as SH
import build_sanno_buzai as SB
import build_sanno_torii as ST

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
SHOT = os.path.join(V.REPO, "Screenshots")
INARI = os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno", "Sanno_Inari_Kasuga_1ken.fbx")
K = 1.818

# ---- 決めた二つ【U】--------------------------------------------------------------
SPAN_KEN = 1.0          # 柱間(柱芯々)[間]
TALL_KEN = 1.5          # 総高(笠木の上端・中央)[間]
# ---- 従属値(明神鳥居の通例)【U 部材方】-----------------------------------------
G = dict(
    colD=0.20, colTaper=0.92,      # 柱の径(足元)と上端の比
    korobi=1 / 40.0,               # ころび(内転び)
    sink=0.15,                     # 根巻石の根入れ(Y<0)
    ishiAcross=0.36, ishiTop=0.18, # 根巻石(八角・対辺)と天端(柱径の 1.8 倍)
    colBase=0.12,                  # 柱の足元(根巻石の中へ差し込む)
    kasagiH=0.17, kasagiD=0.30,    # 笠木(丈・見込み)
    shimagiH=0.13, shimagiD=0.26,  # 島木
    kasagiOut=0.36,                # 笠木・島木が柱芯(足元の通り)から出る長さ
    sori=0.12,                     # 反り(笠木・島木を**同じ曲線**に乗せる)
    nukiH=0.15, nukiD=0.11,        # 貫(丈・見込み)
    nukiTop=1.80,                  # 貫の上端
    kibana=0.14,                   # 木鼻(柱の外面から出る長さ)
    kusabiW=0.062, kusabiOut=0.035, kusabiTaper=0.55,   # 楔(頭の幅・上下へ出る量・足元の細り)
    gakuW=0.16, gakuD=0.12,        # 額束(⛔ 扁額は付けない)
    seg=14,                        # 反りの分割
)
STONE_TILE = SB.KIRISHI_TILE if hasattr(SB, "KIRISHI_TILE") else 0.44
ALLOWED = ("Kirishi", "Shu_Torii")
STONE, SHU = ST.STONE, ST.SHU      # 材質の索引は石鳥居と同じ並び([Kirishi, Shu_Torii])


def prism(M, ring, h0, h1, mat=STONE, tile=None):
    """ST.prism の**タイルを指定できる版**(根巻石は礎盤と同じ 0.44 で貼る)。"""
    n = len(ring)
    for i in range(n):
        (u0, v0), (u1, v1) = ring[i], ring[(i + 1) % n]
        ST.face(M, [(u0, v0, h0), (u1, v1, h0), (u1, v1, h1), (u0, v0, h1)], mat, tile)
    for i in range(1, n - 1):
        ST.face(M, [ring[0] + (h1,), ring[i] + (h1,), ring[i + 1] + (h1,)], mat, tile)
        ST.face(M, [ring[0] + (h0,), ring[i + 1] + (h0,), ring[i] + (h0,)], mat, tile)


def column(M, u_base, h0, h1, r0, taper, lean, n=16, seg=8):
    """**ころび付きの円柱**(朱の木部)。足元の芯 u_base から、頂で `lean` だけ内へ寄る。
    ⛔ 真っ直ぐに立てない — 明神鳥居の柱は内へ転ぶ。"""
    sg = -1.0 if u_base > 0 else 1.0
    for s in range(seg):
        t0, t1 = s / float(seg), (s + 1) / float(seg)
        z0, z1 = h0 + (h1 - h0) * t0, h0 + (h1 - h0) * t1
        c0, c1 = u_base + sg * lean * t0, u_base + sg * lean * t1
        ra0 = r0 * (1.0 - (1.0 - taper) * t0)
        ra1 = r0 * (1.0 - (1.0 - taper) * t1)
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            ST.face(M, [(c0 + ra0 * math.cos(a0), ra0 * math.sin(a0), z0),
                        (c0 + ra0 * math.cos(a1), ra0 * math.sin(a1), z0),
                        (c1 + ra1 * math.cos(a1), ra1 * math.sin(a1), z1),
                        (c1 + ra1 * math.cos(a0), ra1 * math.sin(a0), z1)], SHU)
    return u_base + sg * lean


# ==========================================================================
def build(name):
    span = SPAN_KEN * K
    tall = TALL_KEN * K
    half = span / 2.0
    r0 = G["colD"] / 2.0
    shimagi_bot = tall - G["kasagiH"] - G["shimagiH"]      # 島木の下端 = 柱頭
    col_h0 = G["colBase"]
    lean = (shimagi_bot - col_h0) * G["korobi"]
    ms = [SB.kirishi_material(), ST.shu_material()]
    M = VM.Mesh()

    tops = []
    for sgn in (-1, +1):
        ub = sgn * half
        prism(M, ST.octagon(ub, 0.0, G["ishiAcross"]), -G["sink"], G["ishiTop"],
              STONE, STONE_TILE)
        tops.append(column(M, ub, col_h0, shimagi_bot, r0, G["colTaper"], lean))
    half_top = abs(tops[1])
    r_top = r0 * G["colTaper"]

    # 貫(柱を貫いて木鼻を出す)── 貫の高さでの柱芯から木鼻を測る
    t_nuki = (G["nukiTop"] - G["nukiH"] / 2.0 - col_h0) / (shimagi_bot - col_h0)
    u_nuki = half - lean * t_nuki
    r_nuki = r0 * (1.0 - (1.0 - G["colTaper"]) * t_nuki)
    nuki_end = u_nuki + r_nuki + G["kibana"]
    nd = G["nukiD"] / 2.0
    prism(M, [(-nuki_end, -nd), (nuki_end, -nd), (nuki_end, nd), (-nuki_end, nd)],
          G["nukiTop"] - G["nukiH"], G["nukiTop"], SHU)
    # 楔(木鼻に打つ)── 貫を上から貫いて上下へわずかに出す。
    # ⭐ **上が広く下が狭い台形**にする(⛔ 角柱にすると楔でなく「輪」に見える ── 2026-09-22 実見)。
    kw, ko = G["kusabiW"] / 2.0, G["kusabiOut"]
    kwb = kw * G["kusabiTaper"]
    ku = u_nuki + r_nuki + G["kibana"] / 2.0
    kz0, kz1 = G["nukiTop"] - G["nukiH"] - ko, G["nukiTop"] + ko
    kv = nd + 0.010
    for sgn in (-1, +1):
        c = sgn * ku
        for (v0, v1) in ((-kv, -kv), (kv, kv)):            # 見付の2面(前後)
            sg = 1 if v0 > 0 else -1
            pts = [(c - kwb, v0, kz0), (c + kwb, v0, kz0), (c + kw, v1, kz1), (c - kw, v1, kz1)]
            ST.face(M, pts if sg > 0 else pts[::-1], SHU)
        for (uu, sg) in ((-1, -1), (+1, +1)):              # 木口の2面(左右・勾配が付く)
            pts = [(c + uu * kwb, -kv, kz0), (c + uu * kw, -kv, kz1),
                   (c + uu * kw, kv, kz1), (c + uu * kwb, kv, kz0)]
            ST.face(M, pts if sg > 0 else pts[::-1], SHU)
        ST.face(M, [(c - kw, -kv, kz1), (c + kw, -kv, kz1), (c + kw, kv, kz1), (c - kw, kv, kz1)], SHU)
        ST.face(M, [(c - kwb, -kv, kz0), (c - kwb, kv, kz0), (c + kwb, kv, kz0), (c + kwb, -kv, kz0)], SHU)
    # 額束(貫の上端 → 島木の下端)。⛔ 扁額は付けない(銘が読めていない)
    gw, gd = G["gakuW"] / 2.0, G["gakuD"] / 2.0
    prism(M, [(-gw, -gd), (gw, -gd), (gw, gd), (-gw, gd)], G["nukiTop"], shimagi_bot, SHU)
    # 島木 + 笠木 ── **同じ反りに乗せる**(片方だけ反らせると間が楔形に開く)
    ke = half + G["kasagiOut"]
    sori = lambda t: G["sori"] * (2.0 * t - 1.0) ** 2
    ST.swept_bar(M, -ke, ke, -G["shimagiD"] / 2.0, G["shimagiD"] / 2.0,
                 shimagi_bot, shimagi_bot + G["shimagiH"], sori, mat=SHU, seg=G["seg"])
    ST.swept_bar(M, -ke, ke, -G["kasagiD"] / 2.0, G["kasagiD"] / 2.0,
                 tall - G["kasagiH"], tall, sori, mat=SHU, seg=G["seg"])

    o = M.to_object(name + "_body", ms)
    o.name = name
    o.data.name = name
    V.sel([o])
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))   # 円柱は滑らか・八角と木口は角のまま
    V.set_origin(o, (0.0, 0.0, 0.0))
    o.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    info = dict(span=span, tall=tall, uchinori=span - G["colD"], kasagiLen=2 * ke,
                shimagi_bot=shimagi_bot, half_top=half_top, r_top=r_top,
                nuki_end=nuki_end, ke=ke)
    return o, info


def part_name():
    return "Sanno_Torii_Massha_%dx%d" % (round(SPAN_KEN * K * 1000), round(TALL_KEN * K * 1000))


# ==========================================================================
# 検算 — ⭐ 相手(稲荷社)は**焼いた FBX の実メッシュ**で測る(⛔ 数を写さない)
# ==========================================================================
def inari_box():
    """`Sanno_Inari_Kasuga_1ken.fbx` を読んで Unity ローカルの外形を返す。
    Blender へ読み戻すと 幅=x / 奥行=y / 高さ=z(= Unity の X/Z/Y)。"""
    objs = VM.import_fbx_abs(INARI)
    o = V.join(objs, "Inari_ref") if len(objs) > 1 else objs[0]
    mn, mx = V.bbox([o])
    return o, dict(w=mx.x - mn.x, d=mx.y - mn.y, h=mx.z - mn.z, z0=mn.z)


def report(o, info, ib):
    U = SH.unity_verts(o)
    xs = [t[0] for t in U]; ys = [t[1] for t in U]; zs = [t[2] for t in U]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mats = [m.name.split('.')[0] for m in o.data.materials if m]
    print("MASSHA-TORII %s  W(X)%.3f × H(Y)%.3f × D(Z)%.3f  X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d"
          % (o.name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), tris))
    print("  柱間(柱芯々)%.3f / 内法 %.3f / 総高(笠木の上端・中央)%.3f / 反りの頂 %.3f"
          % (info["span"], info["uchinori"], info["tall"], max(ys)))
    print("  笠木の長さ %.3f / 木鼻の先 ±%.3f / 柱頭の芯 ±%.3f(ころびで %.3f 内へ)/ くぐり高 %.3f"
          % (info["kasagiLen"], info["nuki_end"], info["half_top"],
             info["span"] / 2 - info["half_top"], info["shimagi_bot"]))
    print("  相手(稲荷社 FBX の実測)軒幅 %.3f / 奥行 %.3f / 総高 %.3f" % (ib["w"], ib["d"], ib["h"]))
    ok = []
    # ① 祠を食わない(⛔ 数を写さない — 稲荷社の FBX から引く)
    ok.append(("笠木が稲荷社の軒幅の内に収まる", info["kasagiLen"] < ib["w"],
               "笠木 %.3f < 軒幅 %.3f(余裕 %.3f)" % (info["kasagiLen"], ib["w"], ib["w"] - info["kasagiLen"])))
    ok.append(("総高が稲荷社より低い(祠のほうが高く見える)", max(ys) < ib["h"],
               "鳥居 %.3f < 祠 %.3f" % (max(ys), ib["h"])))
    # ② くぐれる
    ok.append(("内法幅 ≥ 1.20", info["uchinori"] >= 1.20, "内法 %.3f" % info["uchinori"]))
    ok.append(("島木の下端まで ≥ 2.00", info["shimagi_bot"] >= 2.00, "%.3f" % info["shimagi_bot"]))
    # ③ 形式の検査
    ok.append(("貫が柱の外面より外へ出ている(木鼻)", info["nuki_end"] > info["half_top"] + info["r_top"],
               "木鼻の先 %.3f > 柱の外面 %.3f" % (info["nuki_end"], info["half_top"] + info["r_top"])))
    ok.append(("木鼻が笠木の端を越えない", info["nuki_end"] < info["ke"],
               "木鼻 %.3f < 笠木端 %.3f" % (info["nuki_end"], info["ke"])))
    ok.append(("根巻石が地盤より下へ根入れ", min(ys) < -0.05, "底 %.3f" % min(ys)))
    # ④ 対称(EDO-0161: Unity X = −Blender X の符号反転が姿を変えないこと)
    key = lambda t: (round(t[0] / 1e-3), round(t[1] / 1e-3), round(t[2] / 1e-3))
    S = set(key(t) for t in U)
    ok.append(("左右対称(X)", S == set(key((-t[0], t[1], t[2])) for t in U), ""))
    ok.append(("前後対称(Z)── 扁額が無いので向きの取り違えが起きない",
               S == set(key((t[0], t[1], -t[2])) for t in U), ""))
    bad = [t for t in ok if not t[1]]
    for (lab, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", lab, note))
    bm = [m for m in mats if m not in ALLOWED]
    print("  材 %s %s" % (mats, "⭕" if not bm else "⛔ %s" % bm))
    return not bad and not bm


def shots(o, info, ref):
    """⭐ 単体4枚 + **稲荷社と並べた1枚**。単体では「祠に対して大きすぎないか」が読めない。"""
    ref.location = (0.0, 4.5, 0.0)          # Blender +Y = 正面(+Z)の**裏** ⇒ 鳥居の向こうに祠が立つ
    bpy.context.view_layer.update()
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0.0))
    out = []

    def one(cam, look, fn, res=(1400, 1400), ortho=None, cull=False):
        V.studio(cam, look, ortho_scale=ortho, res=res)
        # ⛔ **裏面カリングとマゼンタは `V.studio` の後に入れる**(studio が world を差し替えるため)
        if cull:
            for m in bpy.data.materials:
                m.use_backface_culling = True
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
        f = os.path.join(SHOT, "sanno_massha_torii_%s.png" % fn)
        V.render(f); out.append(f)

    ref.hide_render = True
    one((0.0, -7.0, 1.4), (0.0, 0.0, 1.35), "front_elev", ortho=3.9)          # 正面
    one((2.6, -4.2, 2.0), (0.0, 0.0, 1.25), "oblique")                       # 斜め
    one((0.35, -1.15, 1.80), (info["span"] / 2 * 0.9, 0.0, 1.80), "kibana",
        res=(1400, 1100))                                                    # 貫の木鼻と楔
    one((-0.75, -1.05, 0.42), (-info["span"] / 2, 0.0, 0.10), "nemaki",
        res=(1200, 1100))                                                    # 根巻石と柱の足元
    ref.hide_render = False
    one((0.0, -8.5, 1.9), (0.0, 1.8, 1.55), "narabe_inari", ortho=6.4)       # ⭐ 稲荷社と並べて
    one((3.4, -6.0, 2.6), (0.0, 1.6, 1.30), "narabe_oblique")
    # ⭐ 最後に **裏面カリング + マゼンタ**で巻き順の裏返りと穴を見る(楔は手で巻いた面なので要検分)
    ref.hide_render = True
    one((2.2, -3.6, 1.9), (0.0, 0.0, 1.35), "cull", cull=True)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    V.reset()
    o, info = build(part_name())
    ref, ib = inari_box()
    ok = report(o, info, ib)
    files = shots(o, info, ref) if "--render" in argv else []
    for f in files:
        print("RENDER " + f)
    if not ok and "--allow" not in argv:
        raise SystemExit("[massha-torii] ⛔ 検算に落ちた")
    if "--no-export" not in argv:
        o.location = (0.0, 0.0, 0.0)
        path = os.path.join(OUT, o.name + ".fbx")
        V.export_fbx([o], path)
        print("[massha-torii] 書き出し %s" % path)


if __name__ == "__main__":
    main()
