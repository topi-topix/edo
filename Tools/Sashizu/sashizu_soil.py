# -*- coding: utf-8 -*-
"""土の面 ── 平場の縁から外へ広がる**一枚の土の面**(法面・法尻の均し)を解く【共通】。

出自: 枝 sashizu/sanno(4bc89706..bbdb6b5a)の `build_sanno_sashizu.py` から**関数を一字も変えずに**
移した(EDO-0270)。山王は 2026-09-19 の裁定(案A)で、法面を『ray を降ろす旧式』から
『土留めを障害物とした測地距離の一枚の土の面』へ入れ替えた。共通の生成器(`build_sashizu.py`)の
`Model.graded_y` は、指図が `terrainCheck.gradedCover.wallCollarM` を宣言していれば、ここへ回す。
⚠ 邸名で分けない ── **欄の有無**で見る(`declared(d)`)。

入口は `design_y(d, g, x, z)`(設計地盤。造成しなければ None)。`d` は指図 json、`g` は世界座標へ
写す格子(`.W(u, v)` だけを使う)、地形は `bind_dem()` で渡す。
⛔ 中の関数は枝の生成器(`sashizu/sanno` の bbdb6b5a)と**同じ式**。2026-09-21 に枝の `design_y` と
  社地の外枠 +15 m を 9 m 刻みの標本で照合した(672 点・うち造成あり 132 点・**差 0.0**)。この照合を
  繰り返す検査は無い ⇒ ⛔ 式を直すときは枝の版と同じ点で比べ直し、理由を添えること。
⚠ 山王の完成時に枝を畳んだあとは、この版が正本になる。
⚠ 覚え書きはモジュールに一組だけ(一部は鍵を持たない)。別の指図へ切り替える呼び手は先に `reset()` を呼ぶ
  (`build_sashizu.Model.graded_y` が `_SOIL_OWNER` で見張る。壊し試しは指図を複製して Model を作り直すため)。
"""
import copy
import math
import heapq

_DEMD = {"d": None}


def bind_dem(dem_dict):
    """造成前の地形(`{"x0","z0","step","nx","nz","h"}`)を渡す。"""
    _DEMD["d"] = dem_dict


def dem():
    return _DEMD["d"]


def declared(d):
    """指図がこの式を宣言しているか ── `terrainCheck.gradedCover.wallCollarM` の有無。⛔ 邸名で分けない。"""
    return "wallCollarM" in ((d.get("terrainCheck") or {}).get("gradedCover") or {})


def gap_split(a, b, o, horiz):
    """run/wall の開口(gapU/gapV/gapHalf)で区間を割る。horiz=True なら u 方向に走る辺。

    2026-08-23 検図 — 指図が宣言した開口が図に一つも描かれていなかったので入れた。
    """
    hw = o.get("gapHalf")
    if not hw:
        return [(a, b)]
    c = o.get("gapU") if horiz else o.get("gapV")
    if c is None:
        c = o.get("gapV") if horiz else o.get("gapU")
    if c is None:
        return [(a, b)]
    i = 0 if horiz else 1
    lo, hi = min(a[i], b[i]), max(a[i], b[i])
    g0, g1 = c - hw, c + hw
    if g1 <= lo or g0 >= hi:
        return [(a, b)]
    out = []
    def pt(v):
        q = list(a)
        q[i] = v
        q[1 - i] = a[1 - i] + (b[1 - i] - a[1 - i]) * ((v - a[i]) / (b[i] - a[i]) if b[i] != a[i] else 0)
        return q
    if g0 > lo: out.append((pt(lo), pt(g0)))
    if g1 < hi: out.append((pt(g1), pt(hi)))
    return out


def clip_gaps(a, b, gaps):
    """線分から `gaps`=[(u,v,半幅)] の円い開口を抜く。折れ線の任意の向きに効く。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    if L < 1e-9: return [(a, b)]
    cut = []
    for gu, gv, hw in gaps:
        t = ((gu - a[0]) * dx + (gv - a[1]) * dz) / (L * L)
        px, pz = a[0] + dx * t, a[1] + dz * t
        dd = math.hypot(gu - px, gv - pz)
        if dd >= hw: continue
        half = math.sqrt(max(0.0, hw * hw - dd * dd)) / L
        cut.append((max(0.0, t - half), min(1.0, t + half)))
    if not cut: return [(a, b)]
    cut.sort()
    out, cur = [], 0.0
    P = lambda t: [a[0] + dx * t, a[1] + dz * t]
    for c0, c1 in cut:
        if c1 <= 0.0 or c0 >= 1.0: continue
        if c0 > cur + 1e-6: out.append((P(cur), P(c0)))
        cur = max(cur, c1)
    if cur < 1.0 - 1e-6: out.append((P(cur), P(1.0)))
    return out


# 口の縁に残る**切れ端**の下限[間](1.8 mm)。⛔ 設計値ではなく数値の残りかすを落とす閾値。
# ⚠ 2026-09-07 検図11巡目 高1 の後始末 — 口の芯と半幅を丸めると、抜いたはずの区間の端に
#   0.1 mm 級の断片が残り、**そこだけが透塀の 0.149 m 隣に立っている**ように測れた。
SEG_MIN_KEN = 0.001


def run_segs(o):
    """run/wall を開口で割った描画区間。折れ線にも対応。⛔ 1 mm 級の切れ端は run ではない。"""
    out = []
    for a, b in segs(o):
        horiz = abs(b[0] - a[0]) >= abs(b[1] - a[1])
        for p, q in gap_split(a, b, o, horiz):
            out += clip_gaps(p, q, o.get("gaps") or [])
    return [(a, b) for a, b in out if math.hypot(b[0] - a[0], b[1] - a[1]) > SEG_MIN_KEN]


def plane_y(d, pl):
    """面の**天端**[m 海抜] ── 正典は `terraces[].y`。造成しない面は None。

    ⚠ 2026-09-07 検図8巡目 中2 — 天端が `planes[].y` と `terraces[].y` の**二重持ち**で、
    幾何の側(`design_y`・切盛・法面・断面・地山)は 8 箇所とも `terraces[].y` を読むのに、
    Δ の検査と面の表だけが `planes[].y` を読んでいた。⛔ `terraces[Keidai].y` を動かしても
    検査は旧い天端を刷り続け(=物差しが図から外れている)。**`planes[].y` は落とした。**
    ⛔ 一つの面が高さの違う terrace を抱えたら検査『面の天端の出所』が⛔で止める。
    """
    ys = [t["y"] for t in d["terraces"]
          if t["name"] in (pl.get("terraces") or []) and t.get("y") is not None]
    return ys[0] if ys else None


# 方位の語 → 真北からの角[°](時計回り・世界 +Z=北 / +X=東)。⛔ 設計値ではない — 語の辞書。
_DIR_DEG = {"北": 0.0, "北北東": 22.5, "北東": 45.0, "東北東": 67.5, "東": 90.0,
            "東南東": 112.5, "南東": 135.0, "南南東": 157.5, "南": 180.0,
            "南南西": 202.5, "南西": 225.0, "西南西": 247.5, "西": 270.0,
            "西北西": 292.5, "北西": 315.0, "北北西": 337.5}


def kaidan_wken(d, k):
    """石段の**幅**[間] ── 正典は `wKen`(⛔ `w`[m] と二本立てにしない・検図7巡目 低5)。

    ⚠ 旧版は `wKen or w/ken` で、参道の階が 5.500 m 対 3.03 間(5.5085 m)の二本立てだった。
    **図が描く階の帯が、その階のために板塀に開けた口より 8.5 mm 狭い**という食い違いが出る。
    """
    if k.get("wKen") is None:
        raise SystemExit("石段『%s』に `wKen` が無い(幅の正典は間)" % k["name"])
    return k["wKen"]


def kaidan_wm(d, k):
    """石段の幅[m] ── `wKen` × 間。⛔ メートルの値を json に持たない。"""
    return kaidan_wken(d, k) * d["const"]["ken"]


def segs(o):
    """石段・土留めの区間。`pts`(折れ線)があればそれ、無ければ a→b の1区間。

    2026-08-23、女坂を明治16年実測図の**屈曲**へ改めたときに導入した。
    """
    p = o.get("pts")
    if p:
        return [(p[i], p[i + 1]) for i in range(len(p) - 1)]
    # ⛔ **a / b を持たない物で落ちない**【庭方 低 2026-09-19】── 折れ線だけを持つ土留め
    #   (`TW_SandoKai_W` / `_E`)は死んだ `a`/`b` を落としてあるので、`pts` の無い道から
    #   ここへ来たら**区間が無い**と答える(⛔ KeyError で生成器ごと止めない)。
    if "a" in o and "b" in o:
        return [(o["a"], o["b"])]
    return []


def dem_h(x, z):
    D = dem()
    i = (x - D["x0"]) / D["step"]; j = (z - D["z0"]) / D["step"]
    a, b = int(math.floor(i)), int(math.floor(j))
    if a < 0 or b < 0 or a + 1 >= D["nx"] or b + 1 >= D["nz"]: return None
    fx, fz = i - a, j - b
    H = D["h"]
    return ((H[b][a] * (1 - fx) + H[b][a + 1] * fx) * (1 - fz)
            + (H[b + 1][a] * (1 - fx) + H[b + 1][a + 1] * fx) * fz)


def _stair_hit(d, g, x, z):
    """石段の通路(帯)に載る点なら **(石段の名, 設計高さ)**。載らなければ (None, None)。

    ⭐ **どの石段か**を返す【低4 検図16巡目 → 2026-09-08】── 切盛図の註が『男坂の盛土/切土』を
    語るのに、集計は『石段(男坂・女坂・参道の階)』の一括りしか持っておらず、**註の数がどの計算
    からも出ていなかった**。⛔ 註へ数を直書きしない ── 坂ごとに数えて刷る。
    """
    for k in d["kaidans"]:
        if k["name"] == "向拝の階": continue
        pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        hw = kaidan_wm(d, k) / 2.0
        tot = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                  for i in range(len(pts) - 1)) or 1.0
        acc = 0.0
        for i in range(len(pts) - 1):
            ax, az = pts[i]; bx, bz = pts[i + 1]
            dx, dz = bx - ax, bz - az
            L = math.hypot(dx, dz) or 1.0
            t = ((x - ax) * dx + (z - az) * dz) / (L * L)
            if t < 0 or t > 1: acc += L; continue
            px, pz = ax + dx * t, az + dz * t
            if math.hypot(x - px, z - pz) <= hw:
                sfrac = (acc + L * t) / tot
                # ⚠ pts[0] が山上か坂下かで向きが変わる(2026-08-23 検図 — 男坂だけ上下逆だった)。
                #    第一点の自然地形が最後の点より高ければ pts[0] = 山上。
                h0 = dem_h(pts[0][0], pts[0][1]); h1 = dem_h(pts[-1][0], pts[-1][1])
                if h0 is not None and h1 is not None and h0 > h1:
                    sfrac = 1.0 - sfrac
                # ⚠ **踊り場のある坂は直線補間にならない**(2026-08-24 検図 高-4 —
                #    切盛図が男坂で断面と最大1.34m 食い違っていた)。断面と同じ割付から引く。
                return (k["name"], stair_y_at(k, sfrac))
            acc += L
    return (None, None)


def _stair_y(d, g, x, z):
    """石段の通路(帯)の設計高さ。坂も造成の対象(2026-08-23 検図 — 図から丸ごと落ちていた)。"""
    return _stair_hit(d, g, x, z)[1]


def stair_spans(k):
    """石段の割付を **(s0, s1, 面の高さ)** の列で返す(s は坂下からの展開長)。

    断面(stair_profile)・切盛図(_stair_y)・動線の昇りが**この一つの関数**を通る。
    ⚠ 二つの式で別々に割ると蹴上1段ぶん(0.30m)ずれる(2026-08-24 検図 高-4)。
    """
    keri = k.get("keri", 0.30); fumi = k.get("fumi", 0.45); od = k.get("odoriba", 0.0)
    fl = k.get("flights") or ([k["steps"]] if k.get("steps") else None)
    if not fl: return None, None
    y0 = k["yBot"]
    out, sacc, n = [], 0.0, 0
    for fi, fn in enumerate(fl):
        for _ in range(fn):
            out.append((sacc, sacc + fumi, y0 + n * keri)); sacc += fumi; n += 1
        if fi < len(fl) - 1 and od > 0:
            out.append((sacc, sacc + od, y0 + n * keri)); sacc += od
    return out, sacc


def stair_y_at(k, sfrac):
    """石段の縦断上の高さ。sfrac は坂下 0 → 頭 1。"""
    sp, tot = stair_spans(k)
    if sp is None:                        # 斜路 — 一様勾配
        return k["yBot"] + (k["yTop"] - k["yBot"]) * max(0.0, min(1.0, sfrac))
    w = max(0.0, min(1.0, sfrac)) * tot
    if w >= tot - 1e-9: return k["yTop"]  # 頭は境内面(最後の蹴上を上がりきった高さ)
    for a, b, y in sp:
        if w <= b + 1e-9: return y
    return k["yTop"]


def gap_source(d, gf, owner):
    """`gapFrom` / `vFrom` が指す物の **芯[uv] と半幅[間]**。⛔ 口の半幅を literal で持たない。

    ・`kaidan` ── 石段。半幅 = `wKen`/2、芯 = 折れ線の第1点(平場の縁に取り付く端)
    ・`gate`   ── 門。半幅 = `plan[span]`/2(既定は桁行 `dv` の半分)、芯 = 門の芯
      ⭐ `edge: "側柱の外面"`(= 一間門なら `"本柱の外面"`。**同じ面の呼び名**で、門の柱の数で
      名が変わるだけ)なら半幅 = 芯から**幅の脇の柱の外面**まで(`gate_col_face_dist`)
      【普請奉行の裁定 2026-09-14 案A を回廊の基壇の口へ及ぼす — 回廊の端 `endFrom` と同じ面】。
      ⛔ 柱芯のまま開けると、門の基壇・礎盤が基壇の石垣の口の縁へ食い込む(検図 2026-09-14 高)
      ⚠ **呼び名を一つに揃える**【低 検図1巡目 → 2026-09-18】── 中門(一間平唐門)の口は
        `gapFrom.edge` / `_gapFrom` / `endSeatM.t` / `joints[].bFace` で「側柱」「本柱」と
        三様に書かれており、⛔ 実装が別の面を探す余地が残っていた。⇒ 一間門は **`本柱の外面`** 一本。
    """
    if gf.get("kaidan"):
        k = [q for q in d["kaidans"] if q["name"] == gf["kaidan"]]
        if not k: raise SystemExit("『%s』の `gapFrom` が引けない: %s" % (owner, gf["kaidan"]))
        k = k[0]
        p = (k.get("pts") or [k["a"], k["b"]])[0]
        return (p[0], p[1]), kaidan_wken(d, k) / 2.0
    if gf.get("gate"):
        gt = gate_by_name(d, gf["gate"])
        eg = gf.get("edge")
        if eg is None:
            return (gt["u"], gt["v"]), gt["plan"][gf.get("span", "dv")] / 2.0
        if eg == "門の基壇の脇面":
            # ⭐ 【石垣の設計 2026-09-14 ②】口の縁 = 門の部材の**最下の帯(基壇)の幅の脇の面**
            #    (`bom[].outlineM` の hM が最も低い帯の |widthM| の最大)。⛔ 数を持たない。
            b9 = gate_bom_row(d, gt) or {}
            ol9 = b9.get("outlineM") or []
            if not ol9:
                raise SystemExit("『%s』── 門『%s』の部材に外形 `outlineM` が無い(基壇の脇面を出せない)" % (owner, gt["name"]))
            low = min(ol9, key=lambda q: q["hM"][0])
            return (gt["u"], gt["v"]), max(abs(low["widthM"][0]), abs(low["widthM"][1])) / d["const"]["ken"]
        if eg not in ("側柱の外面", "本柱の外面"):
            raise SystemExit("『%s』の `gapFrom.edge` が読めない: %s" % (owner, eg))
        _p, n = gate_axes_uv(gt)
        fc = [f for f, v in _FACE_VEC.items() if abs(v[0] * n[0] + v[1] * n[1]) >= 0.99]
        if not fc:
            raise SystemExit("『%s』── 門『%s』の幅の脇の面が東西南北に揃わない(幅の脇の柱の外面を出せない)"
                             % (owner, gt["name"]))
        return (gt["u"], gt["v"]), gate_col_face_dist(d, gt, fc[0])[0]
    raise SystemExit("『%s』の `gapFrom` が何を指すのか読めない" % owner)


def derive_gaps(d):
    """**口は、その口が通す物の幅からの従属値**にする ── 囲い(`runs`)と土留め(`terraceWalls`)の両方。

    ⚠ 2026-09-07 検図8巡目 中3 — `wKen` 一本化(7巡目 低5)が**土留めの口に届いていなかった**。
    `TW_Zentei_W`(男坂の口)・`TW_Zentei_N`(参道の階の口)・`TW_Kairo_E`/`_W`(楼門の口)の
    半幅と、男坂の側壁 `TW_Otoko_N`/`_S` の通りが literal で、**石段の幅を動かしても口は動かない**
    (1.82 m の階に 7.0 m の口が残る)形だった。差が今日 0.0 mm でも、**動かした日に破れる**。
    ⛔ どちらの軸に開くかも書かない — 辺の向き(a→b)から決める。
    """
    for o in d["runs"] + d["terraceWalls"]:
        gf = o.get("gapFrom")
        if not gf: continue
        (cu, cv), hw = gap_source(d, gf, o["name"])
        o["gapHalf"] = hw
        a, b = o.get("a"), o.get("b")
        if a is not None and b is not None and abs(a[0] - b[0]) > 1e-9 and abs(a[1] - b[1]) > 1e-9:
            # ⭐ **斜めの辺**(回した枠の基壇 — 2026-09-14)── 口の芯は通す物の芯から辺へ下ろした足、
            #    半幅は**辺に沿って** hw。`gap_split` は走る軸の座標で割るので、その軸への射影で持つ。
            #    ⛔ 芯の v(または u)をそのまま使わない ── 枠の角のぶん口が片側へずれる。
            L9 = math.hypot(b[0] - a[0], b[1] - a[1])
            ex, ey = (b[0] - a[0]) / L9, (b[1] - a[1]) / L9
            t9 = (cu - a[0]) * ex + (cv - a[1]) * ey
            fu, fv = a[0] + ex * t9, a[1] + ey * t9
            if abs(ex) < abs(ey):
                o["gapV"] = fv; o.pop("gapU", None); o["gapHalf"] = hw * abs(ey)
            else:
                o["gapU"] = fu; o.pop("gapV", None); o["gapHalf"] = hw * abs(ex)
            continue
        if a is not None and b is not None and abs(a[0] - b[0]) < abs(a[1] - b[1]):
            o["gapV"] = cv; o.pop("gapU", None)    # v に走る辺 → 口は v で開く
        else:
            o["gapU"] = cu; o.pop("gapV", None)
    # 石段の**両側の側壁**の通り ── 芯 ± 半幅(⛔ ±1.925 のような数を持たない)
    for w in d["terraceWalls"]:
        vf = w.get("vFrom")
        if not vf: continue
        (cu9, cv), hw = gap_source(d, vf, w["name"])
        if vf["side"] in ("東", "西"):
            # ⭐ **v に走る石段の袖**(参道の階 ── ユーザー裁定〈造成の縁〉2 2026-09-19)── 通りは芯 ± 半幅で
            #   **u** が決まり、走りは**石段の折れ線そのもの**。⛔ 石段の座標を壁へ書き写さない
            #   (規則4 ── 石段が動けば袖も動く)。
            k9 = ([k for k in d["kaidans"] if k["name"] == vf["kaidan"]] or [None])[0]
            if k9 is None:
                raise SystemExit("袖の石垣『%s』の `vFrom.kaidan` が引けない" % w["name"])
            pts9 = k9.get("pts") or [k9["a"], k9["b"]]
            u9 = round(cu9 + (hw if vf["side"] == "東" else -hw), 4)
            w["a"] = [u9, pts9[0][1]]; w["b"] = [u9, pts9[-1][1]]
            continue
        w["a"][1] = w["b"][1] = cv + (hw if vf["side"] == "北" else -hw)


def gate_by_name(d, nm):
    """名で門を引く。⛔ 番号で指さない(門が増減した日に取り違える)。"""
    for gt in d["gates"]:
        if gt["name"] == nm: return gt
    raise SystemExit("門『%s』が無い" % nm)


_FACE_VEC = {"東": (1.0, 0.0), "西": (-1.0, 0.0), "北": (0.0, 1.0), "南": (0.0, -1.0)}


def gate_pass_az(gt):
    """門の**通り抜けの軸の方位**[°・mod 180](真北から時計回り)。`front` が先、無ければ `pass`。
    宣言が無ければ None。⛔ 組み立て時の写し `passAz` を読まない ── 変異の図でもその場で出す。"""
    fr, ps = gt.get("front"), gt.get("pass")
    fd = gate_frame_deg(gt)
    if fr in _DIR_DEG: return (_DIR_DEG[fr] + fd) % 180.0
    if ps in _PASS_DEG: return (_PASS_DEG[ps] + fd) % 180.0
    return None


def gate_frame_deg(gt):
    """門が載る**回した枠**の角[°・上から見て時計回り]。`gates[].frame` が `grid.frames` を名指す。

    ⭐ 明治16年実測図の読み【A】── 回廊の東面(北翼・楼門・南翼)は一直線のまま傾く(2026-09-14)。
    ⛔ 角を門ごとに数で持たない ── `grid.frames[].deg` 一本。⛔ 名指したのに組み立て前で角が解けて
    いなければ止める(0 で埋めると回した門が黙って真東西へ戻る)。
    """
    if not gt.get("frame"): return 0.0
    if gt.get("frameDeg") is None:
        raise SystemExit("門『%s』の枠『%s』の角が解けていない(`derive_gate_yaw` の前に読んだ)"
                         % (gt["name"], gt["frame"]))
    return float(gt["frameDeg"])


def gate_axes_uv(gt):
    """(p, n) ── 通り抜けの単位ベクトル p と桁行の単位ベクトル n [uv](u=東・v=北)。

    ⭐ **奥行 `plan.du` は p、幅 `plan.dv` は n に取る**【K004 検図 2026-09-13】。
    ⛔ 向きが未宣言の門は、平面が正方形(du = dv)のときに限り東西とみなす(回しても形が同じ)。
       正方形でなければ止める ── 東西で埋めると南北に抜ける門で黙って崩れる。
    """
    az = gate_pass_az(gt)
    if az is None:
        pl = gt["plan"]
        if abs(pl["du"] - pl["dv"]) > 1e-9:
            raise SystemExit("門『%s』は通り抜けの向き(`front`/`pass`)が未宣言で平面が正方形でない — "
                             "奥行 du をどちらへ取るか決まらない(⛔ 東西で埋めない)" % gt["name"])
        az = 90.0
    a = math.radians(az)
    px, py = round(math.sin(a), 12) + 0.0, round(math.cos(a), 12) + 0.0
    return (px, py), (py, -px)


def gate_col_face_dist(d, gt, face):
    """門の芯から**幅の脇(桁行の側)の側柱の外面**までの距離[間]と、その向きの単位ベクトル[uv]。

    ⭐ 面 = 柱芯(`plan.dv`/2)+ 部材の側柱の半径 `bom[].axis.colRadiusM`【普請奉行の裁定 2026-09-14 案A】。
    ⛔ 半径の宣言が無ければ止める(0 で埋めると柱芯へ戻り、柱と礎盤が黙って囲いへ食い込む)。
    ⛔ 通り抜けの軸の上の面(`gate_face_u` の側)をここで出さない。
    """
    b = gate_bom_row(d, gt)
    rad = ((b or {}).get("axis") or {}).get("colRadiusM")
    if rad is None:
        raise SystemExit("門『%s』の部材に側柱の半径 `axis.colRadiusM` の宣言が無い — 側柱の外面を出せない" % gt["name"])
    p, n = gate_axes_uv(gt)
    fv = _FACE_VEC.get(face)
    if fv is None or abs(fv[0] * n[0] + fv[1] * n[1]) < 0.99:
        raise SystemExit("門『%s』の面『%s』は幅の脇(桁行の側)の面でない — 側柱の外面を出せない" % (gt["name"], face))
    sg = 1.0 if fv[0] * n[0] + fv[1] * n[1] > 0 else -1.0
    return gt["plan"]["dv"] / 2.0 + float(rad) / d["const"]["ken"], (sg * n[0], sg * n[1])


_PASS_DEG = {"南北": 0.0, "東西": 90.0}


def gate_bom_row(d, gt):
    """門の `bom` が指す部材の行(無ければ None)。"""
    nm = gt.get("bom")
    if not nm: return None
    for b in d["bom"]:
        if b.get("部材") == nm: return b
    return None


def terrace_poly(te, g):
    """段の平面。`poly`(uv)があればそれ、無ければ u0/v0/u1/v1 の矩形。2026-08-23 に前庭が多角形になった。"""
    if te.get("poly"):
        return [g.W(u, v) for u, v in te["poly"]]
    if te["kind"] == "rect":
        return [g.W(te["u0"], te["v0"]), g.W(te["u1"], te["v0"]),
                g.W(te["u1"], te["v1"]), g.W(te["u0"], te["v1"])]
    return [g.W(u, v) for u, v in te["uv"]]


def in_poly(pt, P):
    x, z = pt; c = False; j = len(P) - 1
    for i in range(len(P)):
        if (P[i][1] > z) != (P[j][1] > z) and \
           x < (P[j][0] - P[i][0]) * (z - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0]:
            c = not c
        j = i
    return c


# ---------------------------------------------------------------- 縁の法面 ── **一枚の土の面**
#   ⭐ **2026-09-19 ユーザー裁定 = 案A(庭方の設計)** ── 法面は「輪郭の一点ごとに外へ降ろす
#   **一本の ray**」ではなく、**盛土の縁から外へ広がる一枚の土の面**である:
#
#       設計面 = min( max( 現地形, 面の高さ − 距離 / `const.batterFill` ),
#                     面の高さ + 距離 / `const.batterCut` )
#
#   ── **距離は土留めを障害物とした測地距離**(壁の向こうへは回り込まない)。盛の円錐は**縁の
#   盛厚が +0.05 m を超える区間**から、切の円錐は **−0.05 m を下回る区間**からだけ出し、
#   **現地形に沈んだ所で止まる**。⛔ 1.5 / 1.0 は図が元から持つ `const.batterFill` /
#   `const.batterCut` で、⛔ 新しい勾配値は作らない。
#   ⛔ **捨てた三つ**(どれも『途中で法面を**横へ消す**』作法。⭕ **土の面は横に消せない** ──
#      この三つが段を立てていた):
#     ① `slope_lands` の二値判定 ── 着地するか否かで ray を丸ごと採否していた。隣り合う ray が
#        判定を跨ぐ所で法面が消え、一枡の崖が立った(現況 23 枡)
#     ② `on_wall` による ray の全消し ── 土留めが受ける縁の法面を消していた。壁区間と法面区間の
#        **継ぎ目**に段が立った(現況 4 枡・最大 1.95 m)
#     ③ `featherCap` 12 m の打ち切り ── 現地形へ着かない ray をそこで切っていた(現況 39 枡)
#   ⭕ 土留めは**消す物ではなく障害物**になった ── 測地距離が壁を回り込まないので壁の受ける区間に
#     円錐は入らず、**壁の端では盛土が回り込んで自然に薄れる**(継ぎ目が消える)。
#   ⚠ **リーチに設計値の上限は無い** ── `_CONE_GUARD_M` は走査域の**外枠**(暴走よけ)であって
#     設計値ではない。⛔ ここで法面が切れたら欠陥で、切れた節点数は検査が毎回刷る(規則19)。
_CONE_GUARD_M = 40.0     # 走査域の外枠[m] ── ⛔ 設計値ではない(⭕ 張らないことを検査が毎回刷る)


_CONE_SEED_M = 0.25      # 縁の標本の刻み[m] ── ⛔ 設計値ではない(円錐の頭を置く歩きの細かさ)


_CONE_SEED_R = 2.0       # 標本が種を置く半径[m] ── ⛔ 設計値ではない(格子へ頭を移すだけ)


# ⚠ **測地距離の例外はここ一つだけ**【検図 低 2026-09-19】── 面の広がり(`_prop`)は土留めを
#   障害物とした測地距離だが、**種を撒く最初の `_CONE_SEED_R` m だけは直線距離**である
#   (輪郭の標本から格子の節点へ頭を移すだけの手当て)。⇒ 壁の端や入隅では、理屈の上では
#   種が壁の向こう側の節点へ落ちうる。⛔ 宣言を『全部が測地』と読ませない。
#   ⭕ 直線が障害の節点に当たった回数は毎回測って刷る(`seedJump`)── ⚠ **上限の見積り**で、
#     格子 1 m では**壁のすぐ脇を通る種も数える** ⇒ ⛔ そのまま『壁を越えた種』と読ませない。
_CONE = {"key": None}


def cone_field(d, g):
    """**縁から外へ広がる土の面**を造成の格子(`IMPL_STEP`)へ解く【裁定 2026-09-19 = 案A】。

    戻り dict ── `h`(節点 → **補間に使う高さ**)/ `nat` / `graded`(造成する節点の集合)/
    `reach`(輪郭からの届きの最大[m])/ `guardN`(外枠に達した節点 ── ⭕ **0 が正**)/
    `blocked`(障害の節点数)/ `seedF` `seedC`(円錐の頭の数)/ `bbox`。

    ⭐ **障害は二つだけ** ── ① **土留めの胴**(`_wall_dist` ≤ `wallCollarM` ── ⛔ 新しい物差しを
      作らない)② **平場と石段**(土は面の中へは広がらない)。⛔ 障害は伝播を**迂回させる**
      のであって、⛔ 法面を消さない。
    ⭐ **補間に使う高さ**は、造成する節点では円錐の値、それ以外は**現地形**。平場の中の節点は
      **面の高さ**(⛔ ただしその節点の最寄りの縁を**土留めが受けている**なら現地形 ── 壁の外へ
      面の高さを引き出すと見付が埋まる・**〈造成の縁〉1** の⛔)。石段の帯は `_stair_y` が先に受け持つ
      ので、格子には**現地形**を置く(⛔ 段の踏面を法面の補間へ持ち出さない)。
    """
    if _CONE.get("key") == id(d): return _CONE["v"]
    S = IMPL_STEP
    bf = float(d["const"]["batterFill"]); bc = float(d["const"].get("batterCut", 1.0))
    wc = wall_collar_m(d) or 0.0
    polys = [(te, terrace_poly(te, g)) for te in d["terraces"]]
    xs = [p[0] for _t, P in polys for p in P]; zs = [p[1] for _t, P in polys for p in P]
    i0 = int(math.floor((min(xs) - _CONE_GUARD_M) / S)); i1 = int(math.ceil((max(xs) + _CONE_GUARD_M) / S))
    j0 = int(math.floor((min(zs) - _CONE_GUARD_M) / S)); j1 = int(math.ceil((max(zs) + _CONE_GUARD_M) / S))
    nat, h, blocked = {}, {}, set()
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            x, z = i * S, j * S
            n9 = dem_h(x, z)
            te9 = None
            for te, P in polys:
                if in_poly((x, z), P): te9 = (te, P); break
            if te9 is not None:
                # 平場の中 ── 補間の角に使う高さだけを持つ(⛔ 伝播はさせない)
                dd9, nr9 = _poly_near(x, z, te9[1])
                if n9 is not None and dd9 <= 2.0 * S and on_wall(d, g, nr9[0], nr9[1]):
                    h[(i, j)] = n9                 # ⛔ 壁の外へ面の高さを引き出さない
                else:
                    h[(i, j)] = float(te9[0]["y"])
                blocked.add((i, j)); continue
            if n9 is None: continue
            nat[(i, j)] = n9; h[(i, j)] = n9
            if _stair_y(d, g, x, z) is not None: blocked.add((i, j)); continue
            if wc and _wall_dist(d, g, x, z) <= wc: blocked.add((i, j))
    # ---- 円錐の頭 ── 輪郭を `_CONE_SEED_M` で歩き、**縁の盛厚の符号**で盛/切を分ける
    seedF, seedC = {}, {}
    jump = [0]          # 直線で撒いた種が障害(土留め)を跨いだ回数 ── ⭕ 0 が正
    for te, P in polys:
        for k9 in range(len(P)):
            a9 = P[k9]; b9 = P[(k9 + 1) % len(P)]
            L9 = math.hypot(b9[0] - a9[0], b9[1] - a9[1])
            n8 = max(1, int(L9 / _CONE_SEED_M))
            for q9 in range(n8):
                t9 = (q9 + 0.5) / n8
                x = a9[0] + (b9[0] - a9[0]) * t9; z = a9[1] + (b9[1] - a9[1]) * t9
                if on_wall(d, g, x, z): continue        # 土留めが受ける区間からは出さない
                en = dem_h(x, z)
                if en is None: continue
                dv = te["y"] - en
                if -0.05 <= dv <= 0.05: continue        # 縁がほぼ地山 ── 円錐を出さない
                bi = int(math.floor(x / S)); bj = int(math.floor(z / S))
                r9 = int(math.ceil(_CONE_SEED_R / S)) + 1
                for ii in range(bi - r9, bi + r9 + 1):
                    for jj in range(bj - r9, bj + r9 + 1):
                        kk = (ii, jj)
                        if kk in blocked or kk not in nat: continue
                        dd = math.hypot(ii * S - x, jj * S - z)
                        if dd > _CONE_SEED_R: continue
                        # ⚠ **直線で撒いた種が壁を跨いでいないか毎回測る**【検図 低 2026-09-19】──
                        #   宣言は「測地距離」だが、種の 2 m だけは直線である(上の註)。
                        #   ⛔ 例外を書いて済ませない ── ⭕ **跨いだ数を刷る**(0 が正)。
                        m9 = max(1, int(math.ceil(dd / (S / 2.0))))
                        for s9 in range(1, m9):
                            px9 = x + (ii * S - x) * s9 / m9; pz9 = z + (jj * S - z) * s9 / m9
                            if (int(round(px9 / S)), int(round(pz9 / S))) in blocked:
                                jump[0] += 1; break
                        if dv > 0.05: seedF[kk] = max(seedF.get(kk, -1e9), te["y"] - dd / bf)
                        else:         seedC[kk] = min(seedC.get(kk, 1e9), te["y"] + dd / bc)

    def _prop(seed, sign, bat):
        """円錐を測地距離で広げる(sign +1 = 盛・−1 = 切)。**現地形に沈んだ節点で止める**。"""
        POT = dict(seed)
        hp = [(-sign * v, k) for k, v in seed.items()]
        heapq.heapify(hp)
        while hp:
            key, k = heapq.heappop(hp)
            v = POT[k]
            if abs(-sign * v - key) > 1e-9: continue
            n9 = nat[k]
            if sign > 0 and v <= n9 + 0.05: continue    # 現地形に沈んだ ── ここで止まる
            if sign < 0 and v >= n9 - 0.05: continue
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dz == 0: continue
                    q = (k[0] + dx, k[1] + dz)
                    if q in blocked or q not in nat: continue
                    st = math.hypot(dx, dz) * S
                    nv = v - st / bat if sign > 0 else v + st / bat
                    if (sign > 0 and nv > POT.get(q, -1e9) + 1e-9) or \
                       (sign < 0 and nv < POT.get(q, 1e9) - 1e-9):
                        POT[q] = nv; heapq.heappush(hp, (-sign * nv, q))
        return POT
    PF = _prop(seedF, 1, bf); PC = _prop(seedC, -1, bc)
    for k, v in PF.items():
        if v > h[k]: h[k] = v
    for k, v in PC.items():
        if v < h[k]: h[k] = v
    graded, reach, guardn = set(), 0.0, 0
    for k in set(PF) | set(PC):
        if abs(h[k] - nat[k]) <= 0.05: continue
        graded.add(k)
        reach = max(reach, min(_poly_dist(k[0] * S, k[1] * S, P) for _t, P in polys))
        if k[0] <= i0 + 1 or k[0] >= i1 - 1 or k[1] <= j0 + 1 or k[1] >= j1 - 1: guardn += 1
    v9 = {"h": h, "nat": nat, "graded": graded, "reach": reach, "guardN": guardn,
          "blocked": len(blocked), "seedF": len(seedF), "seedC": len(seedC),
          "bbox": (i0, j0, i1, j1), "guardM": _CONE_GUARD_M,
          "seedR": _CONE_SEED_R, "seedM": _CONE_SEED_M, "seedJump": jump[0]}
    _CONE["key"] = id(d); _CONE["v"] = v9
    return v9


def cone_reach_m(d, g):
    """**円錐が輪郭から届く最大[m]** ── ⛔ 宣言値ではなく**解いた面からの実測**(規則4)。"""
    return cone_field(d, g)["reach"]


def _cone_at(d, g, x, z):
    """円錐の面をその点で読む ── **造成の格子の双一次**(⛔ 実装が読むのと同じ読み方)。"""
    F = cone_field(d, g); S = IMPL_STEP
    i0 = int(math.floor(x / S)); j0 = int(math.floor(z / S))
    tx = x / S - i0; tz = z / S - j0
    v = []
    for ii, jj in ((i0, j0), (i0 + 1, j0), (i0, j0 + 1), (i0 + 1, j0 + 1)):
        q = F["h"].get((ii, jj))
        if q is None:
            q = dem_h(ii * S, jj * S)
            if q is None: return None
        v.append(q)
    return ((v[0] * (1 - tx) + v[1] * tx) * (1 - tz)
            + (v[2] * (1 - tx) + v[3] * tx) * tz)


def design_y(d, g, x, z):
    """設計地盤。段(平場)・石段の通路の中なら面の高さ、縁の外は**円錐の法面**、造成しなければ None。

    ⚠ **平場が石段より優先**(2026-08-24 検図 中-5)。逆にすると、坂の帯が平場へ食い込んだ分だけ
    面に溝が掘れる(女坂の頭で最大 2.19 m)。坂は平場の外だけを受け持つ。
    ⭐ **法面は `cone_field` 一つから出る**【裁定 2026-09-19 = 案A】── ⛔ ここで ray を降ろさない。
    """
    for te in d["terraces"]:
        if in_poly((x, z), terrace_poly(te, g)): return te["y"]
    sy = _stair_y(d, g, x, z)
    if sy is not None: return sy
    nat = dem_h(x, z)
    if nat is None: return None
    y = _cone_at(d, g, x, z)
    if y is None or abs(y - nat) <= 0.05: return None
    # ④ **凹みを抜く**(裁定〈法尻と法肩〉1 = 案①『均す』・物差しは**溜まるか**)── 水の抜けない
    #    節点を落とす。⛔ 上げる方向には効かない(`min`)。⛔ ここで数え直さない(`ridge_level`)。
    cap9 = _level_cap(d, g, x, z)
    return y if cap9 is None else min(y, cap9)


_WSEG = [None]


_WSEGP = [None]        # ⚠ `wall_segs_world` の射影の覚え書き(⛔ 55,660 節点で毎回組み直さない)


def wall_segs_named(d, g):
    """土留めを開口で割った世界座標の線分に**どの壁か**を添えたもの ── [(w, (ax,az), (bx,bz))]。

    ⛔ 線分だけの版(`wall_segs_world`)と二つの母数を作らない ── ⭕ こちらが正本で、
      あちらは名を落とした射影。**控えの天端**(`_collar_top`)が名を要る(検図 高1 2026-09-19)。
    """
    if _WSEG[0] is None:
        out = []
        for w in d["terraceWalls"]:
            for a, b in run_segs(w):
                out.append((w, g.W(a[0], a[1]), g.W(b[0], b[1])))
        _WSEG[0] = out
    return _WSEG[0]


def wall_segs_world(d, g):
    """土留め(terraceWalls)を開口で割って世界座標の線分にしたもの(`wall_segs_named` の射影)。"""
    if _WSEGP[0] is None:
        _WSEGP[0] = [(a, b) for _w, a, b in wall_segs_named(d, g)]
    return _WSEGP[0]


def _seg_dist(x, z, a, b):
    """点から線分への距離。⛔ 距離の式を検査ごとに書かない(規則4)。"""
    ddx, ddz = b[0] - a[0], b[1] - a[1]
    L2 = ddx * ddx + ddz * ddz or 1.0
    t = max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[1]) * ddz) / L2))
    return math.hypot(x - (a[0] + ddx * t), z - (a[1] + ddz * t))


def wall_in_gap(d, g, w, x, z):
    """その点は壁 `w` の**口の中**か【K106 検図 2026-09-19】。

    ⭐ **壁は自分の口の所には無い** ── 口(`gapFrom`)で割る前の折れ線までの距離が、割った後の
      線分までの距離より**近い**なら、その点は口の中に落ちている。⛔ 口の縁の小口までの距離で
      『いちばん近い壁』に選ばれると、**そこに立っていない壁の見付**でその点を裁くことになる。
    ⚠ 実害(K106 2026-09-19)── 前庭の北の腰石垣 `TW_Zentei_N` は参道の階で 3.03 間開くのに、
      口の中の縁 5 点がその壁の見付 0.50 m で裁かれ、**素土 0.78 m**と出ていた。口に立つのは
      石段の**袖石垣** `TW_SandoKai_W`/`_E`(見付 1.04 / 1.31 m)である。
    ⛔ 新しい作法ではない ── 口の位置は `run_segs`(= `gapFrom` からの従属値)そのもの。
    """
    S = run_segs(w)
    if not S: return False
    N = wall_nodes(d, w)
    if len(N) < 2: return False
    df = min(_seg_dist(x, z, g.W(*N[i]), g.W(*N[i + 1])) for i in range(len(N) - 1))
    ds = min(_seg_dist(x, z, g.W(*a), g.W(*b)) for a, b in S)
    return df + 1e-6 < ds


def wall_near_named(d, g, x, z):
    """その点に**いちばん近い土留め**と距離 ── 戻り (w, 距離) ／ 壁が無ければ (None, 1e9)。

    ⛔ **口の中に落ちた点をその壁へ結び付けない**(`wall_in_gap` ── K106 2026-09-19)。
    """
    best = (None, 1e9)
    for w, a, b in wall_segs_named(d, g):
        dd = _seg_dist(x, z, a, b)
        if dd < best[1] and not wall_in_gap(d, g, w, x, z): best = (w, dd)
    return best


def on_wall(d, g, x, z, tol=1.5):
    """その位置の平場の縁を土留めが受けているか。受けていなければ法面で摺り付ける。"""
    return wall_near_named(d, g, x, z)[1] <= tol


def wall_ground(d, g, px, pz, nx, nz):
    """土留めの一点の**両側の地盤**(造成後)。返り (低い側, 高い側, 犬走り or None)。

    ⭐ **物差しは二つの量**【裁定 2026-09-09 普請奉行 = 検図21巡目 A案】── 旧図の `face_toe`
      は**符号を持つ一つの量**(天端 − 外の地盤)で、三つの穴があった:
      ① 基準面が同じ壁の中ですり替わる(平場の内は造成後 `terraces[].y`・外は造成前 `dem_h`)
      ② 切土を受ける壁で 0 を返し、⛔ **未測定と区別が付かない**
      ③ 外向きを固定するので、女坂の頭のように途中で切盛が入れ替わる壁で符号が反転する
    ⭕ **基準面は造成後 `design_y` 一本**(造成しない所は現地形 `dem_h` — これが『造成後の
      地盤』の定義そのものである)。**両側を採り、どちらが外かで場合分けしない**。
      ・**見付高** `faceH` = 天端 − min(両側) …… 壁が見せる面
      ・**受け高** `backH` = max(両側) − 天端 …… 壁が背に負う土
    ⛔ **判定は焼かない** ── 判定則(擁壁として正常/埋まっている壁/段差が無い)は検査が持つ。
      ⛔ 「埋まっている壁」を地形を削って直さない(天端が自然地盤より下 ── スキル
      `unity-modular-stonewall` terrain-grading。始末は `_pending`「埋まっている土留めの始末」)。
    ⚠ 採る距離は `const.wallProbeM`(⛔ 設計値ではなく物差しの刻み)。
    """
    pr = d["const"]["wallProbeM"]
    ys, ben = [], None
    for sg in (1.0, -1.0):
        qx, qz = px + nx * pr * sg, pz + nz * pr * sg
        y = design_y(d, g, qx, qz)
        if y is None: y = dem_h(qx, qz)
        if y is None: y = plane_y(d, d["planes"][0])
        ys.append(y)
    # 犬走り ── **外向き**の側が平場の中なら、その面の高さ(展開図が細点線で重ねる)
    qo = (px + nx * pr, pz + nz * pr)
    for te in d["terraces"]:
        if in_poly(qo, terrace_poly(te, g)): ben = te["y"]
    return min(ys), max(ys), ben


def wall_nodes(d, w):
    """土留めの節点(uv)。⛔ `pts` と `a`/`b` の二通りをここ一箇所で吸う。

    ⛔ **`a`/`b` を持たない物で落ちない**【庭方 低 2026-09-19 ── `segs()` と同じ始末】──
      折れ線だけを持つ土留め(`TW_SandoKai_W` / `_E`)は `derive_gaps` が `pts` を書き込むまで
      節点を持たない。json 単体を読む道具(検査・焼き出しの一部)がそこへ来たら**空**と答える
      (⛔ KeyError で生成器ごと止めない)。⭕ 節点が要る検査は空の名簿を見て黙って飛ばす。
    """
    p = w.get("pts")
    if p: return [tuple(q) for q in p]
    if "a" in w and "b" in w: return [tuple(w["a"]), tuple(w["b"])]
    return []


def wall_stair(d, w):
    """`coping:"stair"` の土留めが**天端を引く石段**。⛔ 石段の名を数のように持たない ──
    指し先は `copingFrom.kaidan`、無ければ通りの従属元 `vFrom.kaidan`(男坂の側壁)。
    """
    if w.get("coping") != "stair": return None
    nm = ((w.get("copingFrom") or {}).get("kaidan")
          or (w.get("vFrom") or {}).get("kaidan"))
    if not nm: return None
    return ([k for k in d["kaidans"] if k["name"] == nm] or [None])[0]


def stair_first_is_top(d, g, k):
    """石段の第一点が**山上**か。⛔ 向きを手で決めない — 現地形が決める。

    ⚠ `_stair_hit` と**同じ判定**をここ一箇所に置く(2026-08-23 検図 — 男坂だけ上下逆だった)。
    """
    pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
    h0 = dem_h(pts[0][0], pts[0][1]); h1 = dem_h(pts[-1][0], pts[-1][1])
    return h0 is not None and h1 is not None and h0 > h1


def stair_sfrac(d, g, k, x, z):
    """点を石段の折れ線へ落とし、**坂下 0 → 頭 1** の走りの割合を返す(最も近い投影)。"""
    pts = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
    tot = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
              for i in range(len(pts) - 1)) or 1.0
    acc, best = 0.0, None
    for i in range(len(pts) - 1):
        ax, az = pts[i]; bx, bz = pts[i + 1]
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz) or 1.0
        t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (L * L)))
        dd = math.hypot(x - (ax + dx * t), z - (az + dz * t))
        if best is None or dd < best[0]: best = (dd, (acc + L * t) / tot)
        acc += L
    sf = best[1]
    return (1.0 - sf) if stair_first_is_top(d, g, k) else sf


_WCOMP = [None]


def wall_components(d):
    """土留めを**節点を共有する連なり**へ分ける。⛔ 群の名を json に書かない。

    ⭐ 回廊の基壇の4面(南妻・東面・北妻・西面)は閉じた一周をなすので、外向きは
      **その一周の重心から遠ざかる側**として機械的に決まる(⛔ 「回廊の芯 u0,v0」という
      literal を作図の中に持たない)。
    """
    if _WCOMP[0] is not None: return _WCOMP[0]
    W = d["terraceWalls"]
    par = list(range(len(W)))

    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    key = lambda q: (round(q[0], 4), round(q[1], 4))
    seen = {}
    for i, w in enumerate(W):
        for q in wall_nodes(d, w):
            k9 = key(q)
            if k9 in seen:
                a, b = find(seen[k9]), find(i)
                if a != b: par[a] = b
            else:
                seen[k9] = i
    comp = {}
    for i, w in enumerate(W):
        comp.setdefault(find(i), []).append(i)
    out = {}
    for _r, idx in comp.items():
        P = [q for i in idx for q in wall_nodes(d, W[i])]
        c = (sum(q[0] for q in P) / len(P), sum(q[1] for q in P) / len(P))
        for i in idx: out[W[i]["name"]] = c
    _WCOMP[0] = out
    return out


def wall_outward(d, g, w, a, b, k=None):
    """土留めの**外向き**(法尻を測る側)の単位法線[世界]。⛔ 符号を手で書かない。

    ① **石段の側壁** ── 石段の芯から遠ざかる側(`coping:"stair"`)
    ② **平場を受ける壁** ── 片側だけが平場の中なら、**平場でない**側(前庭の縁の5本)
    ③ ①②が決めない壁 ── **節点を共有する連なりの重心**から遠ざかる側(回廊の基壇の4面)
    """
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    nx, nz = -dz / L, dx / L
    mx, mz = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    if k is not None:                                    # ① 石段の芯から遠ざかる
        sp = [g.W(*q) for q in (k.get("pts") or [k["a"], k["b"]])]
        best = None
        acc = 0.0
        for i in range(len(sp) - 1):
            ax, az = sp[i]; bx, bz = sp[i + 1]
            ddx, ddz = bx - ax, bz - az
            LL = math.hypot(ddx, ddz) or 1.0
            t = max(0.0, min(1.0, ((mx - ax) * ddx + (mz - az) * ddz) / (LL * LL)))
            q = (ax + ddx * t, az + ddz * t)
            dd = math.hypot(mx - q[0], mz - q[1])
            if best is None or dd < best[0]: best = (dd, q)
            acc += LL
        if best and ((mx - best[1][0]) * nx + (mz - best[1][1]) * nz) < 0: nx, nz = -nx, -nz
        return nx, nz
    ins = lambda q: any(in_poly(q, terrace_poly(te, g)) for te in d["terraces"])
    pr = d["const"]["wallProbeM"]                        # ⛔ 歩幅を二箇所に書かない(規則4)
    pa = ins((mx + nx * pr, mz + nz * pr))
    pb = ins((mx - nx * pr, mz - nz * pr))
    if pb and not pa: return nx, nz                      # ② 平場でない側
    if pa and not pb: return -nx, -nz
    cu, cv = wall_components(d)[w["name"]]               # ③ 連なりの重心から遠ざかる
    cx, cz = g.W(cu, cv)
    if (mx - cx) * nx + (mz - cz) * nz < 0: nx, nz = -nx, -nz
    return nx, nz


def wall_top_ground(d, g, w, k, px, pz, nx, nz):
    """土留めの一点の **(天端, 低い側の地盤, 高い側の地盤, 犬走り)**。⛔ 天端をここ以外で決めない。

    ⭐ 天端の座 ── `coping` が数ならその値、`"stair"` なら石段の割付 `stair_spans`。
    ⭐ **`copingRise: "groundHi"`**【裁定 EDO-0182 (a) 普請奉行 2026-09-13】── 天端 =
      **max(座, 高い側の地盤)**。浅い所は座に従い、地盤が座より上の所は**自然地盤まで**立ち上がる。
      ・天端の出 = 0(⛔ 自然地盤より上へは上げない ── スキル §3b『露出 0〜駒の丈』の下端)
      ・外側の地盤 = 両側の高い側(⛔ 外向きの一点で採らない ── 裁定 2026-09-09 の物差しと揃える)
    ⛔ 地形を壁に合わせて削らない(天端が自然地盤より下 ── スキル terrain-grading)。
    """
    base = (stair_y_at(k, stair_sfrac(d, g, k, px, pz))
            if k is not None else float(w.get("coping")))
    glo, ghi, ben = wall_ground(d, g, px, pz, nx, nz)
    top = max(base, ghi) if w.get("copingRise") == "groundHi" else base
    return top, glo, ghi, ben


def wall_stations(d, g, w, step=1.0):
    """土留めの走りの**駅** ── (s, x, z, 外向き nx, 外向き nz) を節点から `step`[m] 刻みで。

    ⛔ **歩き方を二箇所に書かない**【考証 高 2026-09-19】── 縦断(`wall_samples`)と一点の
      問い合わせ(`wall_tg_at`)が別々に走りを刻んでいたので、同じ壁が二つの答えを持った。
    """
    P = [g.W(*q) for q in wall_nodes(d, w)]
    k = wall_stair(d, w)
    acc = 0.0
    for i in range(len(P) - 1):
        ax, az = P[i]; bx, bz = P[i + 1]
        L = math.hypot(bx - ax, bz - az)
        if L < 1e-9: continue
        nx, nz = wall_outward(d, g, w, P[i], P[i + 1], k)
        n = max(1, int(math.ceil(L / step)))
        for j in range(n + 1):
            if i and j == 0: continue                    # 節点の重複を落とす
            t = min(L, j * L / n)
            yield (acc + t, ax + (bx - ax) * t / L, az + (bz - az) * t / L, nx, nz)
        acc += L


def wall_tg_at(d, g, w, px, pz):
    """世界の一点に**最も近い駅**での **(天端, 低い側の地盤, 高い側の地盤, 犬走り)**。

    ⛔ `wall_samples` と別の物差しを作らない ── 中身は同じ `wall_top_ground` を一点で呼ぶだけ。
    ⭕ 見付高 = 天端 − 低い側 ／ 受け高 = 高い側 − 天端(裁定 2026-09-09 と同じ定義)。
    ⭐ **駅で測る**【考証 高 2026-09-19】── 旧は問う点を走りへ落とした**その場**で測っていた。
      設計面は平場の輪郭で垂直に飛ぶので、輪郭の突端の際では**両側の探りがどちらも平場へ落ち**、
      同じ壁『TW_Kairo_N』を縦断が 4.07〜6.96 m と刷るかたわらで検査が 0.70 m と読んでいた
      (問う点を 4 cm ずらすと値が飛ぶ)。⭕ 歩き方は縦断と同じ一つ(`wall_stations`)にし、
      刻みは物差しの歩幅 `const.wallProbeM`。⛔ 縦断と検査で二つの答えを持たない(規則4)。
    """
    k = wall_stair(d, w)
    best = None
    for _s, qx, qz, nx, nz in wall_stations(d, g, w, float(d["const"]["wallProbeM"])):
        dd = math.hypot(px - qx, pz - qz)
        if best is None or dd < best[0]: best = (dd, qx, qz, nx, nz)
    _dd, qx, qz, nx, nz = best
    return wall_top_ground(d, g, w, k, qx, qz, nx, nz)


# 焼き出しの地盤の格子[m]。⛔ **設計値ではない** — 地形のハイトマップが世界軸の格子なので、
# 回転させず世界座標のまま 1 m で刻む(この社のグリッドは世界軸そのものなので回転は元より無い)。
IMPL_STEP = 1.0


def _design_y_cold(d, g, x, z):
    """`design_y` を**呼び出し順に依存しない形**で引く(焼き出しの定義)。

    ⭐ **揺れは根で消えた**【裁定 2026-09-19 = 案A】── 法面は `cone_field` が**一度だけ解く
      一枚の面**で、点ごとの ray も、その答えを覚える `slope_lands`/`_LAND` も無い。⇒
      `design_y` は構造として呼び出し順に依らない。
    ⛔ **それでも測るのはやめない**(規則19 — 直したから測るのをやめる、をしない)── 一致は
      `graded.orderDrift` が毎回全セルで測り、⛔ 一セルでも食い違えば検査が止める。
    """
    return design_y(d, g, x, z)


# ---------------------------------------------------------------- 格子へ焼くときの縁の作法
#   ⛔ **面の輪郭が格子の隙に落ちると、その帯は造成されない**【K060 2026-09-16 棟梁の差し戻し】。
#   実装(`EdoSannoShaRebuild.Graded.Bilinear`)は**四隅がそろった枡の中でしか読まない**ので、
#   輪郭が最外の節点より外にあると、輪郭沿いの帯が現地形のまま残る。
#   ⭐ **2026-09-19 ユーザー裁定〈造成の縁〉1 = 案A** ── 旧『**帯**』(輪郭の外 格子の刻みぶんを**面の高さ**で
#   保つ作法)と、その外を独自の法勾配 1:0.7 で降ろす作法は、**両方とも廃した**。縁は三つしかない:
#     ① **`design_y`** ── 法面は**縁から外へ広がる一枚の土の面**(円錐)で、`const.batterFill`
#        1:1.5 / `batterCut` 1:1.0 を**土留めを障害物とした測地距離**に掛けて降ろす
#        (⛔ 『輪郭から直に』ではない ── 名乗りを古いままにしない〔庭方 低 2026-09-19〕。
#         ⛔ 帯のぶん外へ押し出さない。土量・切盛図・断面と**同じ一つの式**)
#     ② **壁の控え** ── 土留めが受ける縁だけ、面の高さを**壁の外面まで**保つ
#        (`terrainCheck.gradedCover.wallCollarM`)。その外へは書かない ── ⛔ **見付を埋めない**
#     ③ **平接ぎ** ── 造成の域の外へ**一節点だけ現地形の高さ**を書く(Δ=0)。⭕ 輪郭の枡を閉じる
#        **だけ**の作法で、⛔ **土は一粒も動かない**(⛔ 格子の都合を土で辻褄合わせしない)
#   ⛔ 輪郭そのものを縮めて辻褄を合わせない。⛔ `design_y` が値を持つ節点は上書きしない。
#   ⛔ 社地の外へは出さない。⚠ ②③は**格子へ焼くときだけ** ── `design_y` は動かさない。
#   ⚠ **格子(1 m)も実装の地形(2 m テクセル)も垂直面を持てない** ⇒ 土留めが受ける縁で地盤が
#     天端から法尻へ落ちるのは**一枡の斜路**になる。⭕ 図が約束するのは「**その斜路を一枡より外へ
#     出さない**」ことだけで(検査『格子の縁が一枡より外へ土を持ち出していないか』)、⛔ 土で解かない。
GRADE_REACH = IMPL_STEP          # 平接ぎの幅[m] ── ⛔ 新しい数を作らない(格子の刻みそのもの)


_GPOLY = {}


_DYC = {}


def _dyc(d, g, x, z):
    """`_design_y_cold` の覚え書き ── ⛔ 平接ぎの八方の当たりで同じ点を何度も引き直さない。
    ⚠ **理由を撤回済みの機構で書かない**【検図 低 2026-09-19】── 旧文は「`slope_lands` の
      覚え書きを捨てるので」と書いていたが、`slope_lands`/`_LAND` は裁定 2026-09-19 = 案A で
      **無くなっている**。⭕ いま重いのは `design_y` そのもの(面の内外の判定と円錐の読み)で、
      平接ぎは一点あたり八方 + 段差の当たりで同じ点を何度も引くため。
    ⭕ 返す値そのものは `_design_y_cold` と同じ(冷えた値 ── 焼き出しの定義)。"""
    if _DYC.get("key") != id(d):
        _DYC.clear(); _DYC["key"] = id(d)
    k = (round(x, 3), round(z, 3))
    if k not in _DYC: _DYC[k] = _design_y_cold(d, g, x, z)
    return _DYC[k]


def _terrace_polys(d, g):
    """平場の輪郭(世界座標)と外接矩形を覚える。⛔ 55,660 セルの走査で毎回作らない。"""
    if _GPOLY.get("key") != id(d):
        v = []
        for te in d["terraces"]:
            P = terrace_poly(te, g)
            xs = [q[0] for q in P]; zs = [q[1] for q in P]
            v.append((te, P, (min(xs), min(zs), max(xs), max(zs))))
        _GPOLY["key"] = id(d); _GPOLY["v"] = v
    return _GPOLY["v"]


def _poly_near(x, z, P):
    """点から多角形の辺までの**最短距離とその最寄りの点**。⛔ 距離だけを返す版と二重に書かない。"""
    best = (1e9, None)
    for i in range(len(P)):
        ax, az = P[i]; bx, bz = P[(i + 1) % len(P)]
        ddx, ddz = bx - ax, bz - az
        L2 = ddx * ddx + ddz * ddz or 1.0
        t = max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
        qx, qz = ax + ddx * t, az + ddz * t
        dd = math.hypot(x - qx, z - qz)
        if dd < best[0]: best = (dd, (qx, qz))
    return best


def _poly_dist(x, z, P):
    """点から多角形の辺までの最短距離。"""
    return _poly_near(x, z, P)[0]


def wall_collar_m(d):
    """**壁の控え**[m] ── 土留めが受ける縁で面の高さを保つ幅(壁の線から外へ = 石垣の見込み)。

    ⛔ ここで数を作らない ── 正典は `terrainCheck.gradedCover.wallCollarM`
    (断面が土留めを描く厚み `WALL_T` と**同じ量**。⛔ 同じ量に二つの正典を置かない・規則4)。
    """
    v = ((d.get("terrainCheck") or {}).get("gradedCover") or {}).get("wallCollarM")
    return None if v is None else float(v)


_CTOP = {}


def wall_near_tg(d, g, x, z):
    """その点に**いちばん近い土留め**と、そこでの (天端, 低い側の地盤)。⛔ 物差しは `wall_tg_at`。

    ⚠ 控えと天端が同じ問い合わせを二度するので、丸めた座標で憶える(⛔ 値は作らない)。
    """
    if _CTOP.get("key") != id(d):
        _CTOP.clear(); _CTOP["key"] = id(d)
    k = ("tg", round(x, 3), round(z, 3))
    if k in _CTOP: return _CTOP[k]
    w = wall_near_named(d, g, x, z)[0]
    v = (None, None, None) if w is None else ((w,) + tuple(wall_tg_at(d, g, w, x, z)[:2]))
    _CTOP[k] = v
    return v


def collar_top(d, g, x, z, te):
    """**壁の控えの天端**[m] ── その節点を受ける土留めの**天端そのもの**(⛔ 平場の `y` ではない)。

    ⭐ **2026-09-19 検図 高1** ── 旧図はここに `te["y"]` を書いた。平らな平場を受ける壁ならそれで
      合うが、⛔ **`coping:"stair"` の側壁**(男坂・女坂・参道の階)は天端が段なりに上がるので、
      石段の脇 0.03〜1.2 m の節点に**階の頂の高さ**が入り、一枡幅の土の背が立った。
    ⭕ 天端は **`wall_top_at`**(`coping` が数ならその数、`"stair"` なら `stair_spans` の割付、
      `copingRise:"groundHi"` なら高い側の地盤まで)から採る ── ⛔ ここで段を割り直さない(規則4)。
    ⚠ 受ける壁が見つからないときだけ平場の `y`(= 旧の作法)へ落ちる。
    """
    w, top, _glo = wall_near_tg(d, g, x, z)
    return float(te["y"]) if w is None else float(top)


def ridge_keep_m():
    """**均しが手を付けない法肩の帯**[m] ── 輪郭からこの距離の内の節点は落とさない。

    ⭐ **法肩の丸みを落とさないため**【K108 2026-09-19 → ユーザー裁定で決着】── 実装は格子の
      **双一次**で読むので、輪郭に接する枡の節点を落とすと**法肩そのものが下がる**(旧版で
      射程を広げた初回、『法肩の丸み』が上限に対し 0.794 m で鳴った)。
      ⛔ 丸みの上限はユーザー裁定〈法尻と法肩〉2 で**従属値のまま**と決まっている。
    ⭕ **帯は均さないままでよい**【ユーザー裁定 2026-09-19 ── 庭方の答えを施主が採った】── 帯の
      中の落ちは 1 枡で 0.43 m = 1:2.3 で、**設計の法 1:1.5 より緩い** ⇒ **超過ではない**。
      ⛔ この件で `_pending` を立てない(2026-09-19 に畳んだ)。
    ⛔ 新しい物差しを作らない ── 丸みの上限を導いた**枡の対角** √2 × `IMPL_STEP` そのもの。
    ⚠ 帯の中に超過が残るなら、それは**均しの対象外**として別に数えて刷る(⛔ ⛔にも 0 にもしない)。
    """
    return math.sqrt(2.0) * IMPL_STEP


def _grade_reach(d, g=None):
    """縁の作法の走査が届く幅[m] ── **円錐の届きの実測** + 平接ぎの一枡 + 控えの上限。

    ⭐ **宣言値ではない**【裁定 2026-09-19 = 案A】── 旧版は `const.featherCap` 12 m という
      **作図の打ち切り**を走査幅に使っており、⛔ 同じ一つの数が「法面をどこで切るか」と
      「どこまで数えるか」の両方を決めていた。⇒ 円錐は自分で止まるので、走査幅は
      **解いた面から測った届き**(`cone_reach_m`)に一枡ぶんの余白を足して取る。
    """
    return (cone_reach_m(d, g) + 2.0 * IMPL_STEP + GRADE_REACH * math.sqrt(2.0)
            + (wall_collar_m(d) or 0.0))


def _grade_pick(d, g, x, z):
    """その節点を受け持つ**面**と輪郭までの距離・最寄りの点。戻り (te, P, 距離, 最寄りの点)。"""
    reach = _grade_reach(d, g)
    best = None
    for te, P, bb in _terrace_polys(d, g):
        if x < bb[0] - reach or x > bb[2] + reach: continue
        if z < bb[1] - reach or z > bb[3] + reach: continue
        dd, near = _poly_near(x, z, P)
        if dd > reach or near is None: continue
        if best is None or dd < best[0]: best = (dd, (te, P, dd, near))
    return best[1] if best else None


_GRADE = {}


def grade_rule(d, g, x, z, cold=True):
    """**格子へ焼く設計面の作法**── 戻り (高さ, 空である理由, 縁の別)。⭕ 図・焼き出し・検査・
    切盛図はすべてこの一つから出る(規則4・規則19)。作法そのものは上の見出しの ①②③。
    """
    if _GRADE.get("key") != id(d):
        _GRADE.clear(); _GRADE["key"] = id(d)
    k = (round(x, 3), round(z, 3), bool(cold))
    v = _GRADE.get(k)
    if v is None:
        v = _grade_rule(d, g, x, z, cold); _GRADE[k] = v
    return v


def _grade_rule(d, g, x, z, cold=True):
    y = _dyc(d, g, x, z) if cold else design_y(d, g, x, z)
    if y is not None: return (y, None, "design_y")
    pick = _grade_pick(d, g, x, z)
    if pick is None: return (None, "縁の作法の外(面から遠い)", None)
    te, P, dd, near = pick
    # ⚠ **社地でのクリップは掛けない**【2026-09-19】── `design_y` の法面は元から社地の境で
    #   切っておらず(法尻は着く所まで行く)、縁の作法だけ切ると**同じ縁が二つの規則で動く**。
    #   ⛔ 規則4。⭕ 造成が社地の外へ出ること自体は裁定済(`_pending`)で、面積と土量は
    #   検査『造成が社地の外へ及んでいないか』と切盛図の欄『うち社地外』が毎回刷る。
    # ② **壁の控え** ── 土留めが受ける縁。面の高さを保つのは**壁の外面まで**
    why9 = "造成の域の外(現地形のまま = 社叢の山肌)"
    if on_wall(d, g, near[0], near[1]):
        # ⚠ **控えは宣言のまま**(⛔ 指図方が作法を変えない)── 見付からの従属値へ改める案は
        #   考証 中 2026-09-19 の差し戻しだが、控えの帯には**天端**が書かれるので、広げると
        #   その分だけ**見付が埋まる**(**〈造成の縁〉1** の⛔・実測 3 点 最大 1.20 m)。⇒ 事実と実測を
        #   `_pending`「壁の控えが石垣の基部の出を覆っていない」に記録し、**普請奉行の裁定**へ。
        wc = wall_collar_m(d)
        if wc is None: return (None, "壁の控えの宣言が無い", None)
        # ⚠ **控えは『壁の線から』と『輪郭から』の両方で測る** ── 土留めの線は壁体の**芯**で、
        #   平場の輪郭は壁のどちら側にも寄りうる。片方だけで測ると、輪郭が芯より外へ出ている所で
        #   **平場の縁そのものが控えから外れ**、地盤が壁の足元で天端から法尻へ落ちる(回廊の基壇の
        #   北で 4.0 m 落ちていた ── 石垣が宙に浮く)。
        # ⭐ 天端は**その壁の天端**から採る(`collar_top`)── ⛔ 平場の `y` を書かない(検図 高1)
        if _wall_dist(d, g, x, z) <= wc or dd <= wc:
            return (collar_top(d, g, x, z, te), None, "壁の控え")
        # ⛔ **壁の外面の外へ面の高さを持ち出さない**(見付が埋まる)。⭕ ただし③の平接ぎは出す
        #   ── 出さないと枡が閉じず、実装が `Near` で**平場の高さを壁の外へ持ち出す**
        #   (= 同じ埋没が、図の数に出ない形で起きる。⛔ 図が閉じない枡を実装へ押し付けない)。
        why9 = "土留めが受ける縁(壁の外面の外 ── ⛔ 見付を埋めない)"
    nat = dem_h(x, z)
    if nat is None: return (None, "現地形が無い", None)
    # ③ **平接ぎ** ── 造成の域に隣り合う一節点だけ、現地形の高さを書く(Δ=0・土は動かない)
    s9 = GRADE_REACH
    for dx, dz in ((s9, 0), (-s9, 0), (0, s9), (0, -s9),
                   (s9, s9), (s9, -s9), (-s9, s9), (-s9, -s9)):
        if _graded_core(d, g, x + dx, z + dz): return (nat, None, "平接ぎ")
    if dd <= s9 * math.sqrt(2.0): return (nat, None, "平接ぎ")
    return (None, why9, None)


def _graded_core(d, g, x, z):
    """その節点が**造成の域**(① `design_y` か ② 壁の控え)か ── 平接ぎの当たり。

    ⛔ `grade_rule` を呼び返さない(平接ぎが平接ぎを呼んで際限なく広がる)。⭕ 判定は作法の
      ①②をここで**そのまま**当てる ── ⛔ 規則を書き直さない。
    ⭐ **壁の外にも平接ぎを出す**【2026-09-19】── 出さないと壁の外の枡が閉じず、実装は
      `Near`(1 セル以内の最寄り)で**平場の高さを壁の外へ持ち出す** = 見付が埋まる。
      ⭕ 現地形をそのまま書けば枡が閉じ、⛔ 土は一粒も動かない。
    """
    if _dyc(d, g, x, z) is not None: return True
    wc = wall_collar_m(d)                        # ⛔ ①②の判定を書き直さない(同じ宣言)
    if wc is None: return False
    pick = _grade_pick(d, g, x, z)
    if pick is None: return False
    return (on_wall(d, g, pick[3][0], pick[3][1])
            and (_wall_dist(d, g, x, z) <= wc or pick[2] <= wc))


_LEVEL = {"key": None, "busy": False, "h": {}, "map": {}, "cells": [], "runs": [],
          "iter": 0, "left": [], "leftAt": None, "stuck": 0, "nat": 0, "pits": 0,
          "natCells": [], "natRuns": [], "natBy": {}}


_NB8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


LEVEL_POOL_M = 0.05      # 凹みの深さの敷居[m]【U 当方の作法値 ── 格子の丸めの幅】


_LEVEL_EPS = 0.001       # 抜け道に付ける勾配[m/枡] ── ⛔ 設計値ではない(0 除算よけ)


def _flood(E, seeds):
    """**優先度洪水** ── 各節点に『水が溜まる高さ』と、そこへ水を通した隣(親)を与える。

    ⭕ 親を辿ると**必ず外(排水口)へ出る**ので、凹みの縁のどこを抜けば水が落ちるかが決まる。
    """
    W, par, hp = {}, {}, []
    for k in seeds:
        W[k] = E[k]; heapq.heappush(hp, (E[k], k))
    heapq.heapify(hp)
    while hp:
        w, k = heapq.heappop(hp)
        if w > W.get(k, 1e18) + 1e-12: continue
        for dx, dz in _NB8:
            q = (k[0] + dx, k[1] + dz)
            if q not in E or q in W: continue
            W[q] = max(w, E[q]); par[q] = k
            heapq.heappush(hp, (W[q], q))
    return W, par


def ridge_level(d, g):
    """**④ 水の抜けない凹みを抜く**【ユーザー裁定〈法尻と法肩〉1 2026-09-19 = 案①『均す』。
    物差しは 2026-09-19 に**幅(枡)から『溜まるか』へ入れ替えた**(庭方の答え)】。

    ⭐ **なぜ幅をやめたか** ── 旧版は「向かい合う一対がどちらも低い節点」を土手と数え、その幅の
      上限を `const.ridgeLevelSpanCells`【U 当方の作法値】で切っていた。⛔ **幅を広げれば必ず
      法面そのものを拾う**(実測 幅6枡で 73 点・落差 1.32 m)ので収束せず、⛔ どこで切るかを
      施主に問うしかなくなっていた。⭕ 裁定〈法尻と法肩〉1 の理由は**見えではなく水**である ⇒
      物差しは『**溜まるか**』でなければならない。⇒ 射程は自動で決まり、凹みが消えれば必ず止まる。
    ⭕ **均すのは水の抜けない節点だけ** ── まわり八方が全部高い閉じた凹み(深さ `LEVEL_POOL_M`
      を超える所)を見つけ、**その縁の抜け道を落として**水を落とす。⛔ 土を足す方向には効かない。
    ⛔ **平場・石段・法肩の帯は動かさない**(`ridge_keep_m` ── 輪郭に接する枡を落とすと実装の
      双一次が**法肩そのものを下げる**。ユーザー裁定〈法尻と法肩〉2 の丸みの上限を破る)。
    ⭕ **帳簿**は `cells`(落とした枡)/ `runs`(条)/ `left`(残った凹み)/ `stuck`(抜き道が
      動かせない節点に塞がれた凹み)/ `nat`(**現地形そのものの凹み** ── 当図の土ではない)。
    """
    if _LEVEL.get("key") == id(d): return _LEVEL
    _LEVEL["key"] = id(d); _LEVEL["busy"] = True
    _LEVEL["h"] = {}; _LEVEL["map"] = {}; _LEVEL["cells"] = []; _LEVEL["runs"] = []
    _LEVEL["iter"] = 0; _LEVEL["left"] = []; _LEVEL["leftAt"] = None
    _LEVEL["stuck"] = 0; _LEVEL["nat"] = 0; _LEVEL["pits"] = 0
    # ⛔ **帳簿を初期化し忘れない**【検図 高 / 考証 高 / 庭方 高 2026-09-19】── 旧版は
    #   `natCells`/`natRuns`/`natBy` だけ初期化せず、⛔ 破壊試験が別の `d` で呼ぶたびに
    #   **積み上がった**。⇒ 同じ一つの集計を名乗る切盛図(110 枡)と検査(95 枡)が別の数を
    #   刷っていた(規則4)。⭕ 三つとも毎回空にする。
    _LEVEL["natCells"] = []; _LEVEL["natRuns"] = []; _LEVEL["natBy"] = {}
    try:
        H, MOV, INFO = {}, set(), {}
        reach = _grade_reach(d, g)
        seen = set()
        for te, P, bb in _terrace_polys(d, g):
            i0 = int(math.floor((bb[0] - reach) / IMPL_STEP)) - 1
            i1 = int(math.ceil((bb[2] + reach) / IMPL_STEP)) + 1
            j0 = int(math.floor((bb[1] - reach) / IMPL_STEP)) - 1
            j1 = int(math.ceil((bb[3] + reach) / IMPL_STEP)) + 1
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    if (i, j) in seen: continue
                    x, z = i * IMPL_STEP, j * IMPL_STEP
                    if any(in_poly((x, z), P2) for _t2, P2, _b2 in _terrace_polys(d, g)): continue
                    y, w9, kind = grade_rule(d, g, x, z)
                    if y is None and w9 == "縁の作法の外(面から遠い)": continue
                    seen.add((i, j))
                    if y is None: continue
                    H[(i, j)] = y
                    pk9 = _grade_pick(d, g, x, z)
                    nat9 = dem_h(x, z)
                    INFO[(i, j)] = ((0.0 if nat9 is None else y - nat9),
                                    te["name"] if pk9 is None else pk9[0]["name"])
                    if (kind == "design_y" and _stair_y(d, g, x, z) is None
                            and pk9 is not None and pk9[2] > ridge_keep_m()):
                        MOV.add((i, j))
        # ---- 走査の箱 ── 造成の域を 2 枡ぶん広げ、外周は**排水口**(水はそこから落ちる)
        if H:
            ii = [k[0] for k in H]; jj = [k[1] for k in H]
            i0, i1 = min(ii) - 2, max(ii) + 2
            j0, j1 = min(jj) - 2, max(jj) + 2
        else:
            i0 = i1 = j0 = j1 = 0
        E, edge = {}, set()
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                k = (i, j)
                if k in H: E[k] = H[k]; continue
                x, z = i * IMPL_STEP, j * IMPL_STEP
                y9, _w9, _k9 = grade_rule(d, g, x, z)
                if y9 is None: y9 = dem_h(x, z)
                if y9 is None: continue
                E[k] = y9
        for k in E:
            if (k[0] in (i0, i1) or k[1] in (j0, j1)
                    or any((k[0] + dx, k[1] + dz) not in E for dx, dz in _NB8)):
                edge.add(k)
        drop, stuck, natp = {}, set(), set()
        lim9 = 200
        for it in range(lim9):
            W, par = _flood(E, edge)
            pits = sorted(((W[k] - E[k], k) for k in E
                           if k in H and (W.get(k, E[k]) - E[k]) > LEVEL_POOL_M),
                          key=lambda t: -t[0])
            pits = [p for p in pits if p[1] not in stuck and p[1] not in natp]
            _LEVEL["pits"] = max(_LEVEL["pits"], len(pits))
            if not pits:
                _LEVEL["iter"] = it
                break
            moved = 0
            for _dp, p in pits:
                if (W[p] - E[p]) <= LEVEL_POOL_M: continue
                path, k = [], par.get(p)
                ok, anymov = True, False
                while k is not None and E[k] >= E[p] - 1e-9:
                    if k in MOV: anymov = True
                    else: ok = False; break
                    path.append(k); k = par.get(k)
                    if len(path) > 64: ok = False; break
                if not ok or not path:
                    # ⚠ **抜き道が動かせない** ── 何が塞いでいるかまで控える(⛔ 一語で畳まない)
                    blk, k2 = "現地形", par.get(p)
                    while k2 is not None and E[k2] >= E[p] - 1e-9 and k2 not in MOV:
                        if k2 not in H: blk = "造成の域の外(現地形)"; break
                        y3, _w3, k3 = grade_rule(d, g, k2[0] * IMPL_STEP, k2[1] * IMPL_STEP)
                        if _stair_y(d, g, k2[0] * IMPL_STEP, k2[1] * IMPL_STEP) is not None:
                            blk = "石段の帯"; break
                        if k3 == "壁の控え": blk = "土留めの控え"; break
                        if k3 == "平接ぎ": blk = "平接ぎ(Δ=0 = 現地形)"; break
                        blk = "法肩の帯(輪郭に接する枡)"; break
                    if anymov: stuck.add(p)
                    else:
                        natp.add(p)
                        _LEVEL["natBy"][blk] = _LEVEL["natBy"].get(blk, 0) + 1
                    continue
                for n9, kk in enumerate(path):
                    tgt = E[p] - _LEVEL_EPS * (n9 + 1)
                    if E[kk] > tgt:
                        drop[kk] = drop.get(kk, 0.0) + (E[kk] - tgt)
                        E[kk] = tgt; moved += 1
            if not moved:
                _LEVEL["iter"] = it
                break
        else:
            raise SystemExit("⛔ 凹みの均しが %d 巡で収束しない" % lim9)
        W, _par = _flood(E, edge)
        for k in H:
            if (W.get(k, E.get(k, 0.0)) - E.get(k, 0.0)) <= LEVEL_POOL_M: continue
            dp9 = W[k] - E[k]
            c9 = (k[0] * IMPL_STEP, k[1] * IMPL_STEP, dp9,
                  INFO.get(k, (0.0, "?"))[0], INFO.get(k, (0.0, "?"))[1])
            # ⚠ **均しで抜けない凹みは⛔ にしない** ── 均しは**落とすだけ**の作法で、抜き道が
            #   平場・石段・法肩の帯・現地形なら一節点も動かせない。⛔ 0 に畳まず別に数えて刷る。
            if k in natp:
                _LEVEL["natCells"].append(c9); continue
            _LEVEL["left"].append(c9)
            if _LEVEL["leftAt"] is None or dp9 > _LEVEL["leftAt"][3]:
                _LEVEL["leftAt"] = (c9[0], c9[1], c9[4], dp9)
        _LEVEL["stuck"] = len(stuck); _LEVEL["nat"] = len(natp)
        _LEVEL["natRuns"] = _ridge_runs(_LEVEL["natCells"])
        for k, r9 in drop.items():
            if k not in H: continue
            H[k] = E[k]
            _LEVEL["map"][k] = E[k]
            _LEVEL["cells"].append((k[0] * IMPL_STEP, k[1] * IMPL_STEP, r9,
                                    INFO.get(k, (0.0, "?"))[0], INFO.get(k, (0.0, "?"))[1]))
        _LEVEL["h"] = H
        _LEVEL["runs"] = _ridge_runs(_LEVEL["cells"])
    finally:
        _LEVEL["busy"] = False
    # ⛔ **素の値を覚え書きに残さない** ── 均す前に引いた値が居座ると、図と焼き出しで別の
    #    地面が出る(規則4)。⇒ 帽子が載った後で全部引き直させる。
    _DYC.clear(); _GRADE.clear(); _COLLAR.clear(); _IMPLR.clear()
    return _LEVEL


def _level_cap(d, g, x, z):
    """**均しの帽子**[m] ── その点を囲む枡の四隅に均した節点があれば、格子の**双一次**で
    読んだ高さを返す(⛔ 無ければ None = 設計面に触らない)。

    ⭐ **枡の中まで効かせる理由**【2026-09-19】── 均しを節点だけに効かせると、⛔ **断面と
      切盛図は `design_y` を半刻みで引くので土手が絵から消えない**(帳簿だけ減って図が前のまま)。
      ⭕ 実装が建てるのは格子の双一次そのものなので、枡の中もそれで読めば図と地面が一致する。
    ⛔ 均していない枡には一切触らない ── 帽子は畝の周り一枡にだけ載る。
    """
    if _LEVEL.get("busy"): return None
    L = ridge_level(d, g)
    if not L["map"]: return None
    i0 = int(math.floor(x / IMPL_STEP)); j0 = int(math.floor(z / IMPL_STEP))
    ks = ((i0, j0), (i0 + 1, j0), (i0, j0 + 1), (i0 + 1, j0 + 1))
    if not any(k in L["map"] for k in ks): return None
    v = []
    for k in ks:
        h9 = L["h"].get(k)
        if h9 is None: h9 = dem_h(k[0] * IMPL_STEP, k[1] * IMPL_STEP)
        if h9 is None: return None
        v.append(h9)
    tx = x / IMPL_STEP - i0; tz = z / IMPL_STEP - j0
    return ((v[0] * (1 - tx) + v[1] * tx) * (1 - tz)
            + (v[2] * (1 - tx) + v[3] * tx) * tz)


_COLLAR = {}


_IMPLR = {}


def _wall_dist(d, g, x, z):
    """その点から**土留めの線**までの最短距離[m](⛔ 受けているか否かの閾は `on_wall` が持つ)。"""
    best = 1e9
    for (ax, az), (bx, bz) in wall_segs_world(d, g):
        ddx, ddz = bx - ax, bz - az
        L2 = ddx * ddx + ddz * ddz or 1.0
        t = max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
        best = min(best, math.hypot(x - (ax + ddx * t), z - (az + ddz * t)))
    return best


def _ridge_runs(cells):
    """**畝を連なりへ束ねる**【K099 検図 高 2026-09-19】── 畝の枡 (x, z, 畝の高さ, 盛土の厚み, 面名)
    を**隣り合う枡(斜めを含む 8 近傍)**で連結成分にまとめ、連なりごとに

        (点数, 走り[m], 幅[m], 畝の高さの最大[m], 盛土の厚みの最大[m], 盛土の厚みの和[m³],
         端[A], 端[B], 面名, 端点間の直距離[m], **落とす土**[m³], 切土の中の高まりか, 芯の折れ線)

    を**落とす土 [10](= Σ 畝の高さ)の大きい順**で返す【考証 中 2026-09-19】。
    ⛔ **刷らない量で並べ替えない** ── 旧版は [5](盛土の厚みの和)で並べながら、欄は走り [1] と
      落とす土 [10] を刷っていたので、『最大』と名乗る一条の走りが総走りと算が合わなかった
      (22 m / 8 条に対し『最大』が 2 m)。⇒ ⭕ **鍵は刷る量に合わせ**、選んだ基準を銘に名乗る。

    ⛔ **物差しと工事を取り違えない**【検図 中 / 考証 中 2026-09-19】── [5] は Σ(盛土の厚み)で
      **現地形からの盛り全部**(畝の下の盛土を含む)、[10] は Σ(畝の高さ)で**案①が両隣の高さへ
      落とす土**そのもの。⛔ 一方だけを『土量』と名乗らせない ── 欄は両方を並べて刷る。
    ⚠ **走り [1] = 点数 × 刻み**は一枡幅の直線でしか実延長にならない ── 斜めに継いだ条では
      過大に、塊では過小に出る ⇒ [9] **端点間の直距離**を必ず併記する(⛔ 片方だけ刷らない)。
    ⚠ [11] が真の条は盛土の厚みが負(= **切土の中の高まり**)で、そこの案①は『土手を落とす』
      ではなく『**削る**』工事である(庭方 低 2026-09-19)。

    ⭐ **なぜ束ねるのか** ── 点の数と最大だけを刷ると、⛔ 施主は『一枡の点がばらばらに残る』と
      読む。実体は**一枡幅で連なる土手**で、①『均す』はその走りの分の土を落とす工事である。
    ⭕ **走り** = 点数 × 刻み(一枡幅の列なので枡の数がそのまま延長)。**幅** は行ごと・列ごとの
      枡数の**少ないほう**の最大(= 一枡幅なら刻みそのもの)。**土量** = Σ 盛土の厚み × 一枡の面積。
    ⛔ ここで新しい閾を作らない ── 枡を選ぶ条件は呼ぶ側(`grade_collar_stats`)が持つ。
    """
    ix = {}
    for c in cells:
        ix[(int(round(c[0] / IMPL_STEP)), int(round(c[1] / IMPL_STEP)))] = c
    seen, out = set(), []
    for k0 in ix:
        if k0 in seen: continue
        stack, comp = [k0], []
        seen.add(k0)
        while stack:
            i, j = stack.pop(); comp.append((i, j))
            # ⭐ **束ねるのは 8 近傍**【K099 検図 高 2026-09-19】── 畝は法尻に沿って走るので、
            #   一枡ずつ横へずれながら続く。⛔ 4 近傍で束ねると**一条の土手が三つに切れ**、
            #   走りも土量も小さく出る(当図の北西で 9 枡 14.0 m³ が 4/3/2 枡に割れていた)。
            #   ⭕ 斜めに接する枡は**地面の上では続いている**ので一条と数える。
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                k = (i + di, j + dj)
                if k in ix and k not in seen:
                    seen.add(k); stack.append(k)
        cs = [ix[k] for k in comp]
        rows, cols = {}, {}
        for i, j in comp:
            rows[j] = rows.get(j, 0) + 1
            cols[i] = cols.get(i, 0) + 1
        wid = min(max(rows.values()), max(cols.values())) * IMPL_STEP
        ends = max(((a, b) for a in cs for b in cs),
                   key=lambda t: (t[0][0] - t[1][0]) ** 2 + (t[0][1] - t[1][1]) ** 2)
        ex, ez = ends[1][0] - ends[0][0], ends[1][1] - ends[0][1]
        el = math.hypot(ex, ez)
        # ⭐ **条の芯**(朱の一本線で通す)【検図 低 2026-09-19 ── 一辺 2.5 px の枠では 9 m の条が
        #   22 px の滲みに見え、『連なり』が読めなかった】。⛔ 枠の並びで連なりを表さない。
        spine = [(c[0], c[1]) for c in sorted(
            cs, key=lambda c: ((c[0] - ends[0][0]) * ex + (c[1] - ends[0][1]) * ez) / (el or 1.0))]
        out.append((len(cs), len(cs) * IMPL_STEP, wid,
                    max(c[2] for c in cs), max(c[3] for c in cs),
                    sum(max(0.0, c[3]) for c in cs) * IMPL_STEP * IMPL_STEP,
                    (round(ends[0][0], 1), round(ends[0][1], 1)),
                    (round(ends[1][0], 1), round(ends[1][1], 1)),
                    sorted(cs, key=lambda c: -c[3])[0][4],
                    el,                                                    # [9] 端点間の直距離
                    sum(max(0.0, c[2]) for c in cs) * IMPL_STEP * IMPL_STEP,  # [10] 落とす土
                    max(c[3] for c in cs) <= 0.0,                          # [11] 切土の中の高まり
                    spine))                                                # [12] 芯の折れ線
    # ⛔ 鍵は**刷る量**(落とす土)。同量は盛土の厚みの和で割る【考証 中 2026-09-19】
    out.sort(key=lambda t: (-t[10], -t[5]))
    return out


def _w(g, p):
    x, z = g.W(p[0], p[1])
    return [round(x, 3), round(z, 3)]


def prepare(d):
    """指図の写しに従属値(口の芯と半幅・石段の側壁の通り)を書き込んで返す。

    ⭐ 枝の生成器は `main()` が長い `derive_*` の列を `d` へ書き込んでから土の面を解く。土の面に効くのは
      そのうち `derive_gaps`(土留めの `a`/`b` と口)**だけ**であることを、枝の版との全数照合で確かめた
      (672 点・差 0。ほかの `derive_*` を全部掛けても同じ)。⛔ 呼び手の `d` は書き換えない(写しを返す)。
    """
    d2 = copy.deepcopy(d)
    derive_gaps(d2)
    return d2


_SLOTS = ("_WSEG", "_WSEGP", "_WCOMP")        # `[None]` の一枠(鍵を持たない覚え書き)
_CACHES = ("_CONE", "_GPOLY", "_DYC", "_CTOP", "_GRADE", "_LEVEL", "_COLLAR", "_IMPLR")


def reset():
    """覚え書きを空にする。⚠ 指図を複製して試す(壊し試し)と、鍵を持たない一枠(`_WSEG` ほか)や
    `id(d)` の使い回しが**別の指図の答え**を返す。Model を作る側が毎回呼ぶ(枝の `_probe_caches` と同じ理由)。"""
    G = globals()
    for k in _SLOTS: G[k][:] = [None]
    for k in _CACHES: G[k].clear()
