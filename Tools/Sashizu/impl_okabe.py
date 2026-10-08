"""岡部の算出物の器(EDO-0407)。`bake_impl.py okabe --write` が呼ぶ。

⭕ `graded` はいまの生成器(`build_sashizu.Model.graded_y` → `sashizu_lib.graded_y`)で
  世界の 1m 格子を焼く。指図の面・穴・法面の取り決めは生成器の検査(C04・C20 ほか)と同じ式を通るので、
  図で検めた地盤と建てる地盤が同じ物になる。
⭕ `corners` は bake_impl の共通の焼き手をそのまま使う。
⭕ `base`(塀・長屋の石垣基壇の露出)は消えた岡部の生成器(afb529c2^ の build_okabe_sashizu.py の run_base と
  --export-impl の base 節)を移した。外の地盤は当時 edgeProfile(静的な写しで腐った)から引いていたが、
  ここでは区画線から OUT m 外のいまの地盤(M.nat)を毎回測る。
⭕ `planting` は林方の設計(指図 `planting`)を撒いた点へ焼く(`bake_planting`・EDO-0502)。撒き方は山王と共有
  (`sashizu_lib.plant_rnd` / `apportion` / `scatter_take` / `plant_part` / `grid_sampler`)。
⭕ `terraceWalls` は土留めの線(`bake_terrace_walls`・EDO-0502)── 線は `sashizu_lib.tw_resolve` が指図の関係から解く。
⭕ `gardens` は庭方の設計(指図 `gardens[]`・`tsukiyama[]`)を Stage4 の行へ焼く(`bake_gardens`・EDO-0407)。
  据えるのに要る値が指図に無い行は `wait` を持つ(Stage4 は据えずに名乗る)。庭木は `bake_niwa_trees` が planting の点へ足す。
⛔ rails / kui / migiwa(溜池の汀の杭列・法肩の竹垣)は今の指図に源の欄(`nishi`)が無い — 返さない(据え置き)。
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_sashizu as B  # noqa: E402
import bake_impl as BI     # noqa: E402
import sashizu_lib as L    # noqa: E402

EST = "okabe"
STEP = 1.0
MARGIN = 6.0


def bake_graded(M, poly):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    x0 = float(int(min(xs) - MARGIN))
    z0 = float(int(min(zs) - MARGIN))
    nx = int((max(xs) + MARGIN - x0) / STEP) + 1
    nz = int((max(zs) + MARGIN - z0) / STEP) + 1
    rows, holes = [], 0
    for j in range(nz):
        z = z0 + j * STEP
        row = []
        for i in range(nx):
            x = x0 + i * STEP
            u, v = M.UV(x, z)
            nat = M.nat(u, v)
            y = M.graded_y(u, v, nat)
            if y is None:
                if M.in_parcel(u, v):
                    holes += 1
                row.append(None)
            else:
                row.append(round(float(y), 3))
        rows.append(row)
    return {"x0": x0, "z0": z0, "step": STEP, "nx": nx, "nz": nz, "holes": holes, "h": rows}


OUT = 1.0          # 外の地盤を測る、区画線からの距離(m)


def _edge_frame(M, poly, e):
    n = len(poly)
    a, b = poly[e], poly[(e + 1) % n]
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, nz = -tz, tx
    if M.in_parcel(*M.UV(mx + nx * OUT, mz + nz * OUT)):
        nx, nz = -nx, -nz                              # 外向きへ
    return a, (tx, tz), (nx, nz)


def bake_base(M, poly, d):
    bmin = d["const"]["baseMin"]
    unit = d["const"]["baseUnit"]
    out = []
    for r in d["runs"]:
        if not r.get("base"):
            continue
        a, (tx, tz), (nx, nz) = _edge_frame(M, poly, r["edge"])

        def ex(sv):
            x = a[0] + tx * sv + nx * OUT
            z = a[1] + tz * sv + nz * OUT
            g = M.nat(*M.UV(x, z))
            return BI.rseat(r, sv) - g if g is not None else 0.0
        n = max(2, int((r["s1"] - r["s0"]) / 0.5))
        vs = [ex(r["s0"] + (r["s1"] - r["s0"]) * i / n) for i in range(n + 1)]
        segs, thin, cur = [], [], None
        sv = r["s0"]
        while sv <= r["s1"] + 1e-9:
            if ex(sv) >= bmin:
                cur = sv if cur is None else cur
            elif cur is not None:
                segs.append([round(cur, 3), round(sv, 3)])
                cur = None
            sv += 0.5
        if cur is not None:
            segs.append([round(cur, 3), round(r["s1"], 3)])
        prev = r["s0"]
        for a9, b9 in segs:
            if a9 - prev > 0.5:
                thin.append([round(prev, 3), round(a9, 3)])
            prev = b9
        if r["s1"] - prev > 0.5:
            thin.append([round(prev, 3), round(r["s1"], 3)])
        s = r.get("s")
        if s is None:                                  # 案1: 指図は sFrom(天端 − 法尻の地形)だけ ── 露出の最大を 1/4 刻みで切り上げ
            s = max(0.25, math.ceil(max(vs) / unit * 4 - 1e-9) / 4)
        out.append({"run": r["name"], "s": s, "cap": round(unit * s, 3),
                    "lo": round(min(vs), 3), "hi": round(max(vs), 3), "segs": segs, "thin": thin})
    return out


def bake():
    M = B.Model(EST)
    poly = BI.parcel_poly(EST)
    d = json.load(open(os.path.join(B.DOC, EST + "_sashizu.json"), encoding="utf-8"))
    im = json.load(open(os.path.join(B.DOC, EST + "_impl.json"), encoding="utf-8"))
    graded = bake_graded(M, poly)
    planting = bake_planting(M, poly, d, graded)
    trees, tnotes = bake_niwa_trees(M, d, graded)     # 庭方の庭木(位置の書かれた木)を planting の点へ足す
    planting["points"].extend(trees)
    planting["notes"].extend(tnotes)
    return {"graded": graded, "corners": BI.bake_corners(poly, d, im), "base": bake_base(M, poly, d),
            "planting": planting, "terraceWalls": bake_terrace_walls(M), "gardens": bake_gardens(M, d)}


def bake_terrace_walls(M):
    """土留めの線(EDO-0502)── 指図の `terraceWalls[].between`(関係だけ・座標なし)を共有の解き手
    `sashizu_lib.tw_resolve` で解いた線を、実装が置く行へ焼く。`line` は世界 xz の折れ線(上の側 = 進む向きの左)、
    `top` は天端(一定なら数・段違いや法尻は `tops` = 頂点ごと)、`h` は造成後の地盤で測った高さ [min,max]、
    `gaps` は線を切る石段・坂(線の頭からの道のり m)。⛔ 解けなかった本・部分は `line: null` と `unresolved` で残す
    (推し量って線を作らない・規則19)。"""
    rows = M.tw_rows()
    for nm, why in M.tw_bad:
        rows.append({"name": nm.split("(")[0], "part": (nm.split("(")[1].rstrip(")") if "(" in nm else None),
                     "line": None, "unresolved": why})
    return rows


# ================================================================ 植栽(planting)の焼き手 ── EDO-0502
#   ⭐ 林方の設計(指図 `planting`)を**撒いた点**へ焼く。実装(`EdoOkabeYashikiBuilder.PlantFromImpl`)は
#     `impl.planting.points[]` をそのまま据えるだけ(⛔ 実装で撒き直さない)。
#   ⭐ 撒き方(種・本数の配り・芯々の採り方)は山王と同じ共有の手(`sashizu_lib.plant_rnd` / `apportion` /
#     `scatter_take` / `plant_part` / `grid_sampler`)。退ける形は検査と同じ関数(`kakoi_lines` 系・`edashita_over_road`)。
#   【硬い(許容0 ── 退ける)】区画の外 / 区画の全辺・土留めの線から `kakoiLineFrom`(2.0m)+半厚(土留めは天端の奥行)/
#     面(terraces)・庭(NiwaShoin・Hakusu)・明地・坂と石段の敷き+肩(`kaidanShoulderKen`)/ 棟・附属屋・外周の長屋の
#     外面から `clearance.munes`(高木 軒の出+1.0m・低木 0.6m)/ 蔵・厩から 2.0間 / 樹冠を井戸に掛けない /
#     層をまたぐ幹の芯々 `crossLayerTrunkMinM` / 道の上の枝下 `edaShitaOverRoadM` / 禁じた部材(`forbidden`)。
#   【柔らかい(狙い ── 最も近い所へ・⚠ で残す)】本数(`per100`)・同じ層の芯々(`packRatio`)・屋敷林の列の芯々・
#     名指しの木の位置(`near`)。
LAYS = ("松", "落葉", "中木", "低木")
TALL = ("松", "落葉", "中木")
STEP_KEN = 0.5                                     # 候補の格子[間](山王の bandDef.stepKen と同じ刻み)
SPECIES = {"Matsu": "クロマツ", "Keyaki": "ケヤキ", "Enoki": "エノキ", "Mukunoki": "ムクノキ",
           "Jouryoku": "常緑広葉", "Teiboku": "常緑照葉低木"}
FORBID = ("Broadleaf", "Sakura", "Ume", "Momo", "Bamboo", "Take")     # `planting.plantRule.forbidden` の部材名


def _sd(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
    return math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dz * t)


def _poly_d(p, P):
    """点と多角形の距離(内なら 0)。"""
    if L._pip(p, P): return 0.0
    return min(_sd(p, P[i], P[(i + 1) % len(P)]) for i in range(len(P)))


def _line_d(p, P):
    return min(_sd(p, P[i], P[i + 1]) for i in range(len(P) - 1))


def _nearest_edge(M, p):
    P = M.poly
    return min(range(len(P)), key=lambda i: _sd(p, P[i], P[(i + 1) % len(P)]))


def _out_normal_uv(P, i):
    a, b = P[i], P[(i + 1) % len(P)]
    Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    n = (-(b[1] - a[1]) / Ln, (b[0] - a[0]) / Ln)
    m = ((a[0] + b[0]) / 2 + n[0] * 0.05, (a[1] + b[1]) / 2 + n[1] * 0.05)
    return n if not L._pip(m, P) else (-n[0], -n[1])


def resolve_walls(M, d):
    """**土留めの実体線**(世界 xz)── 線は共有の解き手 `sashizu_lib.tw_resolve`(`build_sashizu.Model.tw_lines`)が
    指図の関係(`terraceWalls[].between`)から解いた物をそのまま使う(EDO-0502 ── 法尻の 2 本も位置が解けたので
    区画の辺から `TOE_M` を保守側に取る仮置きは外した)。天端の奥行は `planting.bandDef.avoid.dodomeCrestDepthM`
    (野面 → 野面の乱積み・ほか → 城の石垣)。戻り (線 [{name, kind, segs, half, halfFrom}], 解けなかった名 [(名, 理由)])。"""
    tbl = (((d.get("planting") or {}).get("bandDef") or {}).get("avoid") or {}).get("dodomeCrestDepthM") or {}
    lines = []
    for ln in M.tw_lines:
        kd = "野面の乱積み" if "野面" in str(ln.get("kind")) else "城の石垣"
        crest = float(tbl.get(kd) or tbl.get("城の石垣") or 0.0)
        W = [M.W(*p) for p in ln["pts"]]
        lines.append({"name": ln["name"], "kind": "土留め(%s)" % kd, "segs": list(zip(W, W[1:])),
                      "half": crest, "halfFrom": "天端の奥行 avoid.dodomeCrestDepthM[%s]" % kd})
    return lines, list(M.tw_bad)


def _palette(d, notes):
    """層 → 変種の列 [{asset, part, prefab, size, idx, species, rec}]。⛔ 禁じた部材・目録に無い変種は落として名乗る。"""
    import impl_sanno as IS
    A = IS.asset_index()
    pal = {}
    for lay in LAYS + ("下草",):
        out = []
        for s in (d["planting"]["parts"].get(lay) or []):
            pp = L.plant_part(s)
            if pp is None:
                notes.append("parts[%s] の行が読めない: %s" % (lay, s)); continue
            if any(f in pp["name"] for f in FORBID):
                notes.append("⛔ parts[%s] に禁じた部材 %s ── 撒かない" % (lay, pp["name"])); continue
            if pp["detail"] and lay == "下草":
                continue                                   # 下草は地形の詳細で撒く(点に焼かない)
            for sz in pp["sizes"]:
                for i in pp["idx"]:
                    pf = "Tree_%s_%s%s" % (pp["name"], sz, "" if i <= 1 else "_%02d" % i)
                    rec = A.get(pf)
                    if rec is None:
                        notes.append("parts[%s] の変種 %s が目録に無い ── 落とした" % (lay, pf)); continue
                    out.append({"asset": "%s.%s.%s.%d" % (pp["fam"], pp["name"], sz, i),
                                "part": '%s.%s("%s"%s)' % (pp["fam"], pp["name"], sz, "" if i <= 1 else ", %d" % i),
                                "prefab": pf, "size": sz, "idx": i, "name": pp["name"],
                                "species": SPECIES.get(pp["name"]) or pp["note"] or pp["name"], "rec": rec})
        pal[lay] = out
    return pal


def _crown_r(v):
    r = v["rec"]
    return r.get("crown_r") or max(r["sx"], r["sz"]) / 2.0


class _Site(object):
    """撒く場所の硬い制約をまとめて持つ(世界 xz で測る)。"""

    def __init__(self, M, d, gat):
        self.M, self.d, self.gat = M, d, gat
        ken = M.KEN
        self.ken = ken
        av = d["planting"]["bandDef"]["avoid"]
        self.sh = dict((k, float(v) * ken) for k, v in (av.get("kaidanShoulderKen") or {}).items())
        m = L.kakoi_line_m(d)
        self.kakoiM = m
        P = M.poly
        plines = [{"name": "区画の辺%d" % i, "kind": "区画の辺", "segs": [(P[i], P[(i + 1) % len(P)])],
                   "half": 0.0, "halfFrom": "区画の線"} for i in range(len(P))]
        self.walls, self.wall_bad = resolve_walls(M, d)
        self.K = L.kakoi_line_keepout(plines + self.walls, m)
        # 面・庭・明地(撒かない面)
        self.terr = [(t.name, [M.W(*q) for q in t.poly]) for t in M.terraces]
        ex = set(x.split("[")[1].rstrip("]") for x in d["planting"]["bandDef"].get("exclude") or [] if "[" in x and "*" not in x)
        self.excl = [(g.name, [M.W(*q) for q in g.poly]) for g in M.gardens if g.name in ex]
        for a in d.get("akichi") or []:
            if a.get("name") in ex:
                self.excl.append((a["name"], [M.W(*q) for q in B.rect(a["u0"], a["v0"], a["u1"], a["v1"])]))
        # 坂(敷きの芯の折れ線と半幅)・石段
        self.ramps = []
        for r in d.get("ramps") or []:
            if not r.get("pts"): continue
            w = r.get("w") or (r.get("wKen", 1.0) * ken)
            P9 = [M.W(*q[:2]) for q in r["pts"]]
            self.ramps.append((r["name"], P9, w / 2.0))
            kt = r.get("kiritoshi")
            if kt:      # 切通しの石垣(両側)── 位置と端は棟梁が解く ⇒ 坂の全長の両側に在るとみる(保守側)
                self.ramps.append((r["name"] + " の切通しの石垣", P9,
                                   w / 2.0 + m + float((av.get("dodomeCrestDepthM") or {}).get("城の石垣") or 0.0)))
        self.kaidans = [(k.name, [M.W(*q) for q in k.poly]) for k in M.kaidans if k.poly]
        # 棟・附属屋・外周の長屋(外面の多角形)
        self.bld, self.kura = [], []
        for kind, b in M.buildings():
            Pw = [M.W(*q) for q in b.poly]
            nm = b.name
            (self.kura if re.search(r"Kura|kura|gura|Umaya", nm) else self.bld).append((nm, Pw))
        dep = (M.const.get("inubashiri") or 0.0) + (M.const.get("nagayaD") or 0.0)
        for r in d.get("runs") or []:
            if r.get("kind") != "Nagaya": continue
            a, b = M.edge_pt(r["edge"], r["s0"]), M.edge_pt(r["edge"], r["s1"])
            n = M.inward(r["edge"])
            self.bld.append((r["name"], [a, b, (b[0] + n[0] * dep, b[1] + n[1] * dep), (a[0] + n[0] * dep, a[1] + n[1] * dep)]))
        self.eave = None                                       # ⚠ 棟ごとの軒の出が指図に無い(下で名乗る)
        self.cl_tall = 1.0
        self.cl_low = 0.6
        self.cl_kura = 2.0 * ken
        import impl_sanno as IS
        ir = IS.asset_index().get("Matsudaira_Ido")
        self.well_r = (math.hypot(ir["sx"], ir["sz"]) / 2.0) if ir else 1.0
        self.wells = [(w.name, M.W(*w.uv)) for w in M.wells]
        self.is_road = L.road_region(M.poly, [(q["id"], q["pts"]) for q in
                                              json.load(open(BI.PARCELS, encoding="utf-8"))["parcels"]])
        self.need = float(av.get("edaShitaOverRoadM") or 0.0)
        self.rx = float(d["planting"]["plantRule"].get("crossLayerTrunkMinM") or 0.0)

    def in_parcel(self, p):
        return L._pip(p, self.M.poly)

    def on_terrace(self, p):
        return next((nm for nm, P in self.terr if L._pip(p, P)), None)

    def base_block(self, p):
        """層に依らない硬い制約。退ける理由か None。"""
        if not self.in_parcel(p): return "区画の外"
        h = L.kakoi_keepout_hit(self.K, p[0], p[1])
        if h is not None: return "%s から %.1fm 未満" % (h, self.kakoiM)
        for nm, P in self.excl:
            if L._pip(p, P): return nm + " の上"
        for nm, P in self.kaidans:
            if L._pip(p, P): return nm + " の上"
        for nm, P in self.bld + self.kura:
            if L._pip(p, P): return nm + " の上"
        return None

    def layer_block(self, p, lay, crown_r=0.0):
        """層に依る硬い制約(肩・棟の離れ・蔵・井戸)。"""
        sh = self.sh.get(lay, 0.0)
        for nm, P9, hw in self.ramps:
            if _line_d(p, P9) < hw + (sh if " の切通し" not in nm else 0.0) - 1e-9:
                return "%s の敷き+肩" % nm
        for nm, P in self.kaidans:
            if _poly_d(p, P) < sh - 1e-9: return "%s の肩 %.2fm 未満" % (nm, sh)
        cl = self.cl_tall if lay in TALL else self.cl_low
        for nm, P in self.bld:
            if _poly_d(p, P) < cl - 1e-9: return "%s の外面から %.2fm 未満" % (nm, cl)
        for nm, P in self.kura:
            if _poly_d(p, P) < self.cl_kura - 1e-9: return "%s から 2.0間 未満" % nm
        for nm, w in self.wells:
            if math.hypot(p[0] - w[0], p[1] - w[1]) < crown_r + self.well_r - 1e-9:
                return "樹冠が井戸 %s に掛かる" % nm
        return None

    def y(self, p):
        y = self.gat(p[0], p[1])
        if y is not None: return y, "design"
        g = self.M.dem.at(p[0], p[1])
        return (g if g is not None else 0.0), "terrain"


def _row(S, nm, grp, lay, v, p, extra=None):
    u9, v9 = S.M.UV(p[0], p[1])
    y, gsrc = S.y(p)
    r = v["rec"]
    row = {"name": nm, "group": grp, "zone": grp, "role": lay, "layer": lay, "species": v["species"],
           "asset": v["asset"], "part": v["part"], "prefab": v["prefab"], "size": v["size"],
           "h": round(r["sy"], 3), "scaleY": 1.0, "scaleXZ": 1.0, "crownM": round(2.0 * _crown_r(v), 3),
           "u": round(u9, 4), "v": round(v9, 4), "world": [round(p[0], 3), round(p[1], 3)],
           "y": round(y, 3), "ground": gsrc, "tilt": 0.0, "tiltDir": [0.0, 1.0], "place": "GameObject",
           "_rec": r}
    if extra: row.update(extra)
    return row


def _pick(rnd, pal):
    return pal[rnd.randrange(len(pal))]


def _eda_pass(S, row):
    if S.need <= 0: return True
    f = L.edashita_over_road(row, row["_rec"], S.is_road, lambda q: S.M.dem.at(q[0], q[1]), S.need, own_poly=S.M.poly)
    return f is None                                    # "noProfile" も退ける(測れない物を道際に立てない)


def _best_near(S, target, lay, v, allow_terrace=True, rmax=20.0, step=0.25, nang=32, ok=None):
    """`target` に最も近い、硬い制約を全部満たす点(PlaceBest の型 ── 柔らかい条件は位置だけ)。無ければ None。
    `ok(p)` があれば、それも満たす点に限る(道の上の枝下・芯々 ── 硬い)。"""
    cr = _crown_r(v)
    r = 0.0
    while r <= rmax + 1e-9:
        for k in (range(nang) if r > 0 else [0]):
            a = 2.0 * math.pi * k / nang
            p = (target[0] + r * math.cos(a), target[1] + r * math.sin(a))
            if S.base_block(p) or S.layer_block(p, lay, cr): continue
            if not allow_terrace and S.on_terrace(p): continue
            if ok is not None and not ok(p): continue
            return p, r
        r += step
    return None, None


def _terrace_edges(M, S, tname, pick):
    """面 `tname` の縁のうち `pick(i, a, b, 外向き)` が真の辺(uv)。"""
    t = next((x for x in M.terraces if x.name == tname), None)
    if t is None: return None, []
    P = t.poly
    return t, [(P[i], P[(i + 1) % len(P)], _out_normal_uv(P, i)) for i in range(len(P))
               if pick(i, P[i], P[(i + 1) % len(P)], _out_normal_uv(P, i))]


def bake_planting(M, poly, d, graded):
    pl = d["planting"]
    pr = pl["plantRule"]
    notes, out, band_note = [], [], []
    S = _Site(M, d, L.grid_sampler(graded))
    pal = _palette(d, notes)
    ken = M.KEN
    for nm, why in S.wall_bad:
        notes.append("⚠ 土留め %s: %s ── この線では退けていない" % (nm, why))
    notes.append("⚠ 棟ごとの軒の出が指図に無い ── 高木は壁の外面から 1.0m(軒の出 0)で退けた(clearance.munes)")
    seeded = dict((lay, []) for lay in LAYS)

    def others(lay):
        return [p for k, v in seeded.items() if k != lay for p in v]

    def emit(row, lay):
        seeded[lay].append(tuple(row["world"]))
        out.append(row)

    # ---- 名指しの木(位置の決まった木を先に)
    edges = d.get("edges") or []
    for t in pl.get("namedTrees") or []:
        lay = t.get("layer") or "落葉"
        sp = t.get("kind")
        cand = [v for v in pal.get(lay, []) if v["species"] == sp] or pal.get(lay, [])
        hf = t.get("hFrom") or ""
        msz = re.search(r"Own\.(\w+)\s+(\w+)\s*の丈", hf)
        if msz:
            cand = [v for v in cand if v["name"] == msz.group(1) and v["size"] == msz.group(2)] or cand
        rnd, key = L.plant_rnd(d, t["name"], lay)
        v = _pick(rnd, cand)
        near = t.get("near") or ""
        tgt, how = None, None
        mw = re.search(r"井戸 (\w+)", near)
        mr = re.search(r"(R_\w+) の上端", near)
        if mw:
            w = next((w2 for nm2, w2 in S.wells if nm2 == mw.group(1)), None)
            if w is not None:
                tgt, how = w, "井戸 %s の芯から樹冠+井戸の半径の外" % mw.group(1)
        elif mr:
            r = next((r2 for r2 in d.get("ramps") or [] if r2.get("name") == mr.group(1)), None)
            if r is not None:
                a, b = r["pts"][0], r["pts"][1]
                Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
                off = r.get("wKen", 1.0) / 2.0 + 1.5
                cs = [(a[0] - (b[1] - a[1]) / Ln * off * s, a[1] + (b[0] - a[0]) / Ln * off * s) for s in (1, -1)]
                tgt = min((M.W(*c) for c in cs), key=lambda c: (_best_near(S, c, lay, v)[1] or 1e9))
                how = "%s の上端の脇・芯から半幅+1.5間" % r["name"]
        elif "郭" in near:
            tt = next((x for x in M.terraces if x.name == "Hokuto"), None)
            if tt is not None:
                c = max(tt.poly, key=lambda q: q[0])
                cu = sum(q[0] for q in tt.poly) / len(tt.poly)
                cv = sum(q[1] for q in tt.poly) / len(tt.poly)
                dd = math.hypot(cu - c[0], cv - c[1]) or 1.0
                tgt = M.W(c[0] + (cu - c[0]) / dd * 1.0, c[1] + (cv - c[1]) / dd * 1.0)
                how = "北東の郭の北の隅から内へ 1間"
        if tgt is None:
            notes.append("⛔ 名指しの木 %s: `near` が解けない(%s)── 撒かない" % (t["name"], near)); continue
        p, r = _best_near(S, tgt, lay, v, ok=lambda q, lay=lay, v=v, nm=t["name"]: _eda_pass(S, _row(S, nm, "", lay, v, q))
                          and all(math.hypot(q[0] - o[0], q[1] - o[1]) >= S.rx for o in others(lay)))
        if p is None:
            notes.append("⛔ 名指しの木 %s: 狙いの 20m 内に硬い制約を満たす所が無い ── 撒かない" % t["name"]); continue
        row = _row(S, t["name"], "名指しの木", lay, v, p, {"of": "名指しの木", "near": how, "movedM": round(r, 2)})
        if mw:
            need9 = _crown_r(v) + S.well_r
            row["movedM"] = round(max(0.0, r - need9), 2)
            if r > need9 + 0.01:
                notes.append("⚠ 名指しの木 %s: 井戸の芯から %.2fm(樹冠+井戸の半径 %.2fm より %.2fm 外)"
                             % (t["name"], r, need9, r - need9))
        elif r > 0.01:
            notes.append("⚠ 名指しの木 %s: 狙い(%s)から %.2fm 寄せた(硬い制約の外へ)" % (t["name"], how, r))
        emit(row, lay)

    # ---- 屋敷林(平場の中の列)
    yrule = (pr.get("bands") or {}).get("屋敷林(平場の中)") or {}

    def faces(i_edge):
        return str((edges[i_edge] if i_edge < len(edges) else {}).get("faces") or "")

    def nb(i_edge):
        return str((edges[i_edge] if i_edge < len(edges) else {}).get("neighbor") or "")
    ROWS = []
    if "西の平場の外の肩" in yrule:
        ROWS.append(("西の平場の外の肩", "Nishi", lambda i, a, b, n: "西の縁" in faces(_nearest_edge(M, M.W((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))),
                     (4.0, 6.0), ("中木", "中木", "松")))
    if "北の縁の内" in yrule:
        ROWS.append(("北の縁の内", "Shumen", lambda i, a, b, n: n[0] > 0.5 and "土井" in nb(_nearest_edge(M, M.W((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))),
                     (4.0, 6.0), ("中木",)))
    if "東の平場の南の練塀の内" in yrule:
        ROWS.append(("東の平場の南の練塀の内", "Higashi", lambda i, a, b, n: n[0] < -0.5 and "南の縁" in faces(_nearest_edge(M, M.W((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))),
                     (5.0, 6.0), ("中木",)))
    for rname, tname, pick, (s0, s1), mix in ROWS:
        t, E = _terrace_edges(M, S, tname, pick)
        rnd, key = L.plant_rnd(d, rname, "列")
        if not E:
            notes.append("⛔ 屋敷林 %s: 面 %s の縁が解けない ── 撒かない" % (rname, tname)); continue
        ins = 1.0                                           # 肩から内へ 1間(`西の平場の外の肩` の宣言・ほかは同じ値を採る U)
        want = got = 0
        moved = []
        for a, b, n in E:
            Lk = math.hypot(b[0] - a[0], b[1] - a[1])
            s = rnd.uniform(s0, s1) / ken / 2.0
            while s < Lk:
                want += 1
                q = (a[0] + (b[0] - a[0]) * s / Lk - n[0] * ins, a[1] + (b[1] - a[1]) * s / Lk - n[1] * ins)
                lay = mix[(want - 1) % len(mix)]
                v = _pick(rnd, pal[lay])
                tgt = M.W(*q)
                p, r = _best_near(S, tgt, lay, v, rmax=s0 / 2.0)
                ok = p is not None
                if ok:
                    # 列は同じ層・別の層の芯々も守る
                    if any(math.hypot(p[0] - o[0], p[1] - o[1]) < S.rx for o in others(lay)) or \
                            any(math.hypot(p[0] - o[0], p[1] - o[1]) < s0 * 0.7 for o in seeded[lay]):
                        ok = False
                if ok:
                    row = _row(S, "%s_%s%03d" % (rname, lay, got + 1), "屋敷林 " + rname, lay, v, p,
                               {"movedM": round(r, 2)})
                    ok = _eda_pass(S, row)
                if ok:
                    emit(row, lay)
                    got += 1
                    if r > 0.01: moved.append(r)
                s += rnd.uniform(s0, s1) / ken
        band_note.append({"band": "屋敷林(平場の中)", "row": rname, "layer": "・".join(sorted(set(mix))), "seed": key,
                          "want": want, "got": got, "spacingM": [s0, s1], "insetKen": ins,
                          "moved": len(moved), "movedMaxM": round(max(moved), 2) if moved else 0.0,
                          "soft": "列の芯々は狙い ── 硬い制約で抜けた所は撒かない" if got < want else None})

    # ---- 帯(面の外の法・崖)
    base = getattr(M, "base", None) or M.dem
    cells = {}                     # 帯 → [(世界 p, 退ける理由 or None)]
    u0, v0, u1, v1 = M.bb_uv
    cell_m2 = (STEP_KEN * ken) ** 2
    nishi = next((x for x in M.terraces if x.name == "Nishi"), None)
    raw_area = {}
    u = math.floor(u0) + STEP_KEN / 2
    while u <= u1:
        v = math.floor(v0) + STEP_KEN / 2
        while v <= v1:
            p = M.W(u, v)
            v += STEP_KEN
            if not S.in_parcel(p) or S.on_terrace(p): continue
            if any(L._pip(p, P) for _n, P in S.excl): continue
            if any(_line_d(p, P9) < hw for nm, P9, hw in S.ramps if " の切通し" not in nm): continue
            gy = S.gat(p[0], p[1])
            ny = base.at(p[0], p[1])
            if gy is None or ny is None: continue
            en = _nearest_edge(M, p)
            if "西の縁" in faces(en) and nishi is not None and gy < nishi.y + 0.1:
                bn = "外法の林(盛土・溜池側)"
            elif gy - ny > 0.8:
                bn = "土手の林(盛土)"
            else:
                bn = "崖の林(地山)"
            raw_area[bn] = raw_area.get(bn, 0) + 1
            cells.setdefault(bn, []).append((p, S.base_block(p)))
        u += STEP_KEN
    pack = float(pr.get("packRatio") or 1.0)
    for lay in LAYS:
        for bn in sorted(cells):
            dens = ((pr.get("bands") or {}).get(bn) or {}).get("per100") or {}
            per = float(dens.get(lay) or 0.0)
            if per <= 0: continue
            crmax = max(_crown_r(v) for v in pal[lay]) if pal[lay] else 0.0
            cand = [p for p, why in cells[bn] if why is None and S.layer_block(p, lay, crmax) is None]
            area = len(cand) * cell_m2
            n = int(math.floor(area * per / 100.0 + 0.5))
            rmin = math.sqrt(100.0 / per) * pack
            rnd, key = L.plant_rnd(d, bn, lay)
            memo = {}

            def acc(p, lay=lay, bn=bn, rnd=rnd, memo=memo):
                v = _pick(rnd, pal[lay])
                row = _row(S, "", bn, lay, v, p)
                if not _eda_pass(S, row): return False
                memo[p] = row
                return True
            pts, r_, rx_ = L.scatter_take(rnd, cand, n, rmin, seeded=seeded[lay], other=others(lay), rx=S.rx, accept=acc)
            for j, p in enumerate(pts):
                row = memo[p]
                row["name"] = "%s_%s%04d" % (bn.split("(")[0], lay, j + 1)
                emit(row, lay)
            band_note.append({"band": bn, "layer": lay, "seed": key, "per100": per,
                              "bandM2": round(raw_area.get(bn, 0) * cell_m2, 1), "plantableM2": round(area, 1),
                              "designN": int(math.floor(raw_area.get(bn, 0) * cell_m2 * per / 100.0 + 0.5)),
                              "want": n, "got": len(pts), "rmin": round(rmin, 3), "rminUsed": round(r_, 3),
                              "relax": rx_,
                              "soft": ("⚠ 芯々を %d 回緩めた" % rx_ if rx_ else None) if len(pts) >= n
                              else "⚠ 本数の狙い未達(硬い制約の内で採りきれない)"})
    # 下草(地形の詳細で撒く ── 点にしない)
    for bn in sorted(cells):
        per = float((((pr.get("bands") or {}).get(bn) or {}).get("per100") or {}).get("下草") or 0.0)
        if per > 0:
            band_note.append({"band": bn, "layer": "下草", "per100": per,
                              "bandM2": round(raw_area.get(bn, 0) * cell_m2, 1),
                              "want": int(math.floor(raw_area.get(bn, 0) * cell_m2 * per / 100.0 + 0.5)),
                              "got": 0, "soft": "点に焼かない ── parts[下草] は detail(地形の詳細メッシュで撒く)"})
    for bn in ((pr.get("bands") or {}).keys()):
        if bn not in cells and bn != "屋敷林(平場の中)" and (pr["bands"][bn] or {}).get("per100"):
            notes.append("⛔ 帯 %s: 区域が解けない ── 撒かない" % bn)
    # 層をまたぐ芯々の検め(硬い)
    xl = []
    for i, a in enumerate(out):
        for b in out[i + 1:]:
            if a["layer"] != b["layer"] and math.hypot(a["world"][0] - b["world"][0], a["world"][1] - b["world"][1]) < S.rx - 1e-9:
                xl.append((a["name"], b["name"]))
    for r in out:
        r.pop("_rec", None)
    return {"points": out, "bands": band_note, "notes": notes,
            "walls": [{"name": w["name"], "kind": w["kind"], "segs": len(w["segs"]), "halfM": round(w["half"], 3),
                       "halfFrom": w["halfFrom"]} for w in S.walls],
            "crossLayer": {"minM": S.rx, "pairs": len(xl), "worst": xl[:5]},
            "seedRule": pr.get("seed"),
            "_": "**撒いた木の点**(林方の設計 `planting` から焼いた)。⛔ 実装側で撒き直さない。種は `plantRule.seed` の宣言から"
                 "決定論的に作るので、同じ指図からは同じ配置が出る。asset は `族.名.寸法.個体`(PlantByKey の書式)"}


# ================================================================ 庭(gardens)の焼き手 ── EDO-0502・EDO-0407
#   ⭐ 庭方の設計(指図 `gardens[]`・`tsukiyama[]`)を、実装(`EdoOkabeYashikiBuilder.Stage4_Niwa`)が読む行
#   `{name, zone, kind, world, y, h, asset, …}` へ焼く。kind の語は Stage4 の分岐の語(景石・岩島・石組護岸の区間・
#   飛石・沓脱石・垣(…)・灯籠・乱杭)に合わせる。asset が null の行は地形・地表の側(Stage4 は据えない)。
#   ⛔ 指図に無い値は作らない ── 据えるのに要る値が指図に無い行は `wait`(足りない欄の名)を持たせて出し、
#     Stage4 は据えずに一覧へ出す。⛔ 座標は指図の uv から世界へ写すだけ(区画の座標は parcels.json・規則11)。

def _rgx_uv(s):
    return [(float(a), float(b)) for a, b in re.findall(r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)", str(s))]


def _centroid(P):
    return (sum(q[0] for q in P) / len(P), sum(q[1] for q in P) / len(P))


def bake_gardens(M, d):
    ken = M.KEN
    out = []

    def W(q):
        w = M.W(q[0], q[1])
        return [round(w[0], 3), round(w[1], 3)]

    def add(nm, zone, kind, pts_uv, asset=None, y=None, h=None, wait=None, **kw):
        o = {"name": nm, "zone": zone, "kind": kind, "world": [W(q) for q in pts_uv]}
        if y is not None:
            o["y"] = round(float(y), 3)
        if h is not None:
            o["h"] = round(float(h), 3)
        o["asset"] = asset
        o.update(dict((k, v) for k, v in kw.items() if v is not None))
        if wait:
            o["wait"] = "指図に無い: " + " / ".join(wait)
        out.append(o)
        return o

    def lenm(pts_uv):
        return round(L.polyline_len([M.W(*q) for q in pts_uv]), 3)

    for g in d.get("gardens") or []:
        gz = g["name"]
        poly = g.get("poly")
        if poly and len(poly) >= 3:
            add(gz + "_Kuiki", gz, "庭の区域", [tuple(q) for q in poly] + [tuple(poly[0])], kindOf=g.get("kind"),
                label=g.get("label"), note="地表の塗りは surface の輪(zones の garden:%s)── ここでは塗らない" % gz)
        mg = g.get("migiwa") or {}
        ring = [tuple(q) for q in (mg.get("pts") or [])]
        wy = mg.get("waterY")
        # ① 汀線 ── 指図の点そのもの(⛔ 平滑の回数は指図に無い ⇒ 平滑しない)
        if len(ring) >= 3:
            add("Migiwa_" + gz, gz, "汀線(平滑後)", ring + [ring[0]], y=wy, depthMax=mg.get("depth"),
                bedY=mg.get("floorY"), lenM=lenm(ring + [ring[0]]), form=mg.get("form"), cert=mg.get("cert"),
                note="指図の汀の点そのまま(平滑の宣言が無いので平滑しない)。水面 waterY・深さ depth・底 floorY")
        # ② 護岸(州浜・石組・乱杭)── 区間は汀線の頂点の番号(#n)で書かれている
        for i, gg in enumerate(g.get("gogan") or []):
            se = L.parse_ring_seg(gg.get("seg"))
            if se is None or len(ring) < 3:
                continue
            arc = L.ring_seg(ring, *se)
            t = str(gg.get("type") or "")
            nm = "Gogan%02d_%s" % (i + 1, gz)
            base = dict(seg=gg.get("seg"), lenM=lenm(arc), why=gg.get("why"), cert=gg.get("cert"), type=t)
            if t.startswith("州浜"):
                add(nm, gz, "州浜(砂利の帯)", arc, y=wy,
                    note="地表(砂利)は surface の輪。⚠ 帯の幅(汀からの出入り)は指図に無い", **base)
            elif t.startswith("石組"):
                add(nm, gz, "石組護岸の区間", arc, asset="Own.Ishigumi", y=wy, ishi=g.get("stone"),
                    wait=["石の長手 lenMin/lenMax", "石の数(または芯々比)", "埋まりの比 buryRatio", "天端の乱れ jag",
                          "役石の間隔 yakuEvery"], **base)
            elif t.startswith("乱杭"):
                add(nm, gz, "乱杭", arc, asset="Own.Rangui",
                    wait=["杭の径 rMin/rMax", "芯々(本数)", "頭の高さ topY", "杭の長さ pieceLen"], **base)
        # ③ 中島・岩島
        for i, nk in enumerate(g.get("nakajima") or []):
            ol = [tuple(q) for q in (nk.get("outline") or [])]
            if len(ol) >= 3:
                add("Nakajima%02d_%s" % (i + 1, gz), gz, "中島(輪郭)", ol + [ol[0]], y=nk.get("topY"),
                    type=nk.get("type"), rTop=nk.get("rTop_m"), falloff=nk.get("falloff"), dressing=nk.get("dressing"),
                    cert=nk.get("cert"),
                    note="⚠ 島の石3 は位置・丈が指図に無い(据えない)。松は植栽の算出物(planting の NiwaShoin)")
        for i, iw in enumerate(g.get("iwajima") or []):
            uv = iw.get("uv")
            if not uv:
                continue
            m_ = re.search(r"([\d.]+)\s*沈", str(iw.get("stones") or ""))
            add("Iwajima%02d_%s" % (i + 1, gz), gz, "岩島", [tuple(uv)], asset="Own.Ishigumi", y=wy,
                sink=(float(m_.group(1)) if m_ else None), stones=iw.get("stones"), cert=iw.get("cert"),
                wait=["大石の丈 h", "肩石の丈 hShoulder"])
        # ④ 橋 ── Stage4 に橋の分岐が無く、駒も名指されていない
        for i, hs in enumerate(g.get("hashi") or []):
            if not (hs.get("from") and hs.get("to")):
                continue
            m_ = re.search(r"=\s*([\d.]+)", str(hs.get("deckY") or ""))
            add("Hashi%02d_%s" % (i + 1, gz), gz, "橋", [tuple(hs["from"]), tuple(hs["to"])], asset="Hashi",
                y=(float(m_.group(1)) if m_ else None), type=hs.get("type"), spanExpect=hs.get("span_m_expect"),
                hasamiIshi=hs.get("hasamiIshi"), lenM=lenm([tuple(hs["from"]), tuple(hs["to"])]), cert=hs.get("cert"),
                wait=["橋の駒(在庫・新造の名指し)", "挟み石の位置と丈"])
        # ⑤ 水の系(遣水・越流堰)── 地形の側。堰は駒が名指されていない
        mz = g.get("mizu") or {}
        inf = mz.get("inflow") or {}
        if len(inf.get("yarimizu") or []) >= 2:
            ym = [tuple(q) for q in inf["yarimizu"]]
            add("Yarimizu_" + gz, gz, "遣水", ym, bedY=inf.get("bedY"), widthM=inf.get("width_m"), lenM=lenm(ym),
                note="地形の側(底の高さ bedY は両端)。⚠ graded に遣水の掘り込みは入っていない")
        wr = (mz.get("outflow") or {}).get("weir") or {}
        if wr.get("uv"):
            add("Seki_" + gz, gz, "越流堰", [tuple(wr["uv"])], asset="Seki", y=wr.get("crestY"), type=wr.get("kind"),
                wait=["堰の駒(在庫・新造の名指し)"])
        # ⑥ 景石(主景の三石)── 丈は地上の丈・埋まりは rule の 1/3
        ks = g.get("keiseki") or {}
        rule = str(ks.get("rule") or "")
        bury = 1.0 / 3.0 if "1/3" in rule else None
        for role, nm in (("主石", "Shu"), ("副石", "Fuku"), ("添石", "Soe")):
            q = (ks.get("main") or {}).get(role)
            if not q:
                continue
            m_ = re.search(r"([\d.]+)\s*m", str(q[2] if len(q) > 2 else ""))
            add("Keiseki_%s_%s" % (nm, gz), gz, "景石", [(q[0], q[1])], asset="JG.Rock",
                h=(float(m_.group(1)) if m_ else None), role=role, pose=("立" if "立" in rule or "立" in str(q[2]) else None),
                buryRatio=(round(bury, 3) if bury else None), ishi=g.get("stone"), desc=q[2] if len(q) > 2 else None,
                why=(ks.get("main") or {}).get("why"), cert=ks.get("cert"),
                wait=(None if m_ and bury else ["丈 h" if not m_ else "埋まりの比"]))
        if ks.get("sub"):
            add("Keiseki_Sub_" + gz, gz, "景石", [], asset="JG.Rock", desc=ks.get("sub"),
                wait=["三石の位置(uv)", "三石の丈 h"])
        # ⑦ 点景(灯籠・沓脱石)
        kc = (d.get("const") or {}).get("kutsunugi") or {}
        for i, tk in enumerate(g.get("tenkei") or []):
            kd, uv = str(tk.get("kind") or ""), tk.get("uv")
            if not uv:
                continue
            if "灯籠" in kd:
                yuki = "雪見" in kd
                add("Toro%02d_%s" % (i + 1, gz), gz, "灯籠", [tuple(uv)], asset=("Eg.ToroYukimi" if yuki else "Toro"),
                    kata=kd, wait=(None if yuki else ["%s の駒(在庫の名指し ── Stage4 の灯籠は雪見だけを据える)" % kd]))
            elif "沓脱" in kd:
                add("Kutsunugi%02d_%s" % (i + 1, gz), gz, "沓脱石", [tuple(uv)], asset="Own.Kutsunugi",
                    L=kc.get("partL"), Wd=kc.get("partW"), scale=(1.0 if kc.get("partL") else None),
                    note="⚠ 石の長さは指図に無い ── 駒の実寸(const.kutsunugi.partL)のまま一様 1.0")
        # ⑧ 園路と飛石(芯々は enro.surface の宣言)
        en = g.get("enro") or {}
        sf = str(en.get("surface") or "")
        m_ = re.search(r"芯々\s*([\d.]+)\s*[〜~-]\s*([\d.]+)\s*m", sf)
        pmin, pmax = (float(m_.group(1)), float(m_.group(2))) if m_ else (None, None)
        for key in ("loopE", "loopW", "summit"):
            P = en.get(key)
            if not P:
                continue
            for j, part in enumerate(L.split_polyline(P, None)):
                nm = "Enro_%s%s_%s" % (key, ("_%d" % (j + 1)) if len(L.split_polyline(P, None)) > 1 else "", gz)
                add(nm, gz, "園路", part, h=en.get("width_m"), lenM=lenm(part), surface=sf, cert=en.get("cert"),
                    note="地表(土)は surface の輪。⛔ 橋の区間は切って出す")
                if pmin is None:
                    continue
                Pw = [M.W(*q) for q in part]
                st = L.stones_along(Pw, pmin, pmax, L.seeded_rnd(nm + "/飛石"))
                add("Tobi_" + nm[5:], gz, "飛石", [M.UV(*q) for q in st], asset="Own.Tobiishi", n=len(st),
                    pitchMin=pmin, pitchMax=pmax, lenM=round(L.polyline_len(Pw), 3),
                    note="芯々 %.2f〜%.2fm の不等ピッチ(enro.surface)。⚠ 石の径・曲がりの踏分石は指図に無い"
                         "(径はビルダーの既定)" % (pmin, pmax))
        # ⑨ 垣(庭の東の縁の建仁寺垣)── 線は where の `v=` と庭の区域の幅・口は遣水が縁を越える所
        kk = g.get("kaki") or {}
        mv = re.search(r"v\s*=\s*(-?[\d.]+)", str(kk.get("where") or ""))
        if mv and poly:
            vk = float(mv.group(1))
            us = sorted(q[0] for q in poly)
            u0, u1 = us[0], us[-1]
            cuts = []
            ym = inf.get("yarimizu") or []
            for a, b in zip(ym, ym[1:]):
                if (a[1] - vk) * (b[1] - vk) <= 0 and abs(b[1] - a[1]) > 1e-9:
                    cuts.append(a[0] + (b[0] - a[0]) * (vk - a[1]) / (b[1] - a[1]))
            half = (kk.get("openingW") or 0.0) / 2.0 / ken
            segs, s = [], u0
            for c in sorted(cuts):
                segs.append((s, c - half))
                s = c + half
            segs.append((s, u1))
            kata = str(kk.get("kata") or "")
            kn = "建仁寺垣" if "建仁寺" in kata else ("四つ目垣" if "四つ目" in kata else kata)
            for j, (a, b) in enumerate(segs):
                if b - a <= 1e-6:
                    continue
                add("Kaki%02d_%s" % (j + 1, gz), gz, "垣(%s)" % kn, [(a, vk), (b, vk)],
                    asset=("Own.KenninjiGaki" if "建仁寺" in kn else "Own.YotsumeGaki"), h=kk.get("h"),
                    lenM=lenm([(a, vk), (b, vk)]), role=kk.get("role"), cert=kk.get("cert"),
                    note="線は where の v=%.1f・庭の区域の幅いっぱい。口 %.2fm は遣水が縁を越える所(u=%s)"
                         % (vk, kk.get("openingW") or 0.0, ",".join("%.2f" % c for c in cuts) or "無し"))
    # ⑩ 築山(指図の頂上欄 `tsukiyama[]`)── 地形の側
    for t in d.get("tsukiyama") or []:
        sk = [tuple(q) for q in (t.get("skirt") or [])]
        if len(sk) < 3:
            continue
        gz = next((g.name for g in M.gardens if all(L._pip(q, [tuple(p) for p in g.poly]) for q in sk[:1])), "NiwaShoin")
        add("Tsukiyama_%s" % t.get("name"), gz, "築山(裾の輪郭)", sk + [sk[0]], y=t.get("y"),
            peak=[t.get("u"), t.get("v")], how=t.get("how"), top=t.get("top"), cert=t.get("cert"),
            note="地形の側。⚠ graded に築山(削り残し)は入っていない")
    return out


# ---------------------------------------------------------------- 庭木(planting の点へ足す)
#   ⭐ 庭は林方の散布から外してある(`planting.bandDef.exclude` の gardens[NiwaShoin]・gardens[Hakusu])。
#     庭方の植栽(`gardens[].shokusai`)のうち**位置が指図に書かれた木**だけをここで点へ焼き、planting の points に足す
#     (Stage5 の PlantFromImpl が据える)。⛔ 位置が文で書かれただけの木は撒かない ── `notes` に名乗る。

_NIWA_TREE = {   # parts の書き方 → (族.名, 目録の prefab の型, 寸法の選択肢, 個体)
    "JG.Pine": ("JG.Pine", "Tree_BlackPine_%s_Green_0%d", ("Big", "Mid", "Small"), (1, 2, 3)),
    "Own.Jouryoku": ("Own.Jouryoku", "Tree_Jouryoku_%s%s", ("Mid", "Big"), (1, 2, 3)),
    "JC.Azalea": ("JC.Azalea", "Azalea A 0%d", None, (1, 3, 4)),
    "Own.Momiji": ("Own.Momiji", "Tree_Momiji_%s%s", ("Small", "Mid"), (1, 2, 3)),
    "JG.Boxwood": ("JG.Boxwood", "Plant_Boxwood_Spring_0%d", None, (1, 2, 3)),
}


def _niwa_variants(parts, A):
    """`shokusai[].parts` の文から変種の列を起こす。読めなければ []。"""
    s = str(parts or "")
    out = []
    for key, (fam, pf, sizes, idx) in _NIWA_TREE.items():
        if key not in s:
            continue
        m = re.search(re.escape(key) + r"\s+([A-Za-z/]+)", s)
        szs = [z for z in (m.group(1).split("/") if m else []) if z in (sizes or ())] or list(sizes or [None])
        for sz in szs:
            for i in idx:
                if fam == "JC.Azalea":
                    prefab, asset = pf % i, "JC.Azalea%02d" % i
                elif fam == "JG.Boxwood":
                    prefab, asset = pf % i, "JG.Boxwood.Mid.%d" % i
                elif fam == "JG.Pine":
                    prefab, asset = pf % (sz, i), "JG.Pine.%s.%d" % (sz, i)
                else:
                    prefab, asset = pf % (sz, "" if i <= 1 else "_%02d" % i), "%s.%s.%d" % (fam, sz, i)
                rec = A.get(prefab)
                if rec is not None:
                    out.append({"asset": asset, "prefab": prefab, "size": sz, "idx": i, "rec": rec})
    return out


def bake_niwa_trees(M, d, graded):
    import impl_sanno as IS
    A = IS.asset_index()
    gat = L.grid_sampler(graded)
    pts, notes = [], []
    gpoly = dict((g.name, [tuple(q) for q in g.poly]) for g in M.gardens)
    gw = dict((k, [M.W(*q) for q in P]) for k, P in gpoly.items())

    def row(nm, gz, lay, sp, v, uv, scale=1.0, tilt=0.0, tdir=(0.0, 1.0), extra=None):
        x, z = M.W(*uv)
        y = gat(x, z)
        r = v["rec"]
        o = {"name": nm, "group": "庭木 " + gz, "zone": gz, "role": lay, "layer": lay, "species": sp,
             "asset": v["asset"], "part": v["asset"], "prefab": v["prefab"], "size": v["size"],
             "h": round(r["sy"] * scale, 3), "scaleY": scale, "scaleXZ": scale,
             "crownM": round((r.get("crown_r") or max(r["sx"], r["sz"]) / 2.0) * 2.0 * scale, 3),
             "u": round(uv[0], 4), "v": round(uv[1], 4), "world": [round(x, 3), round(z, 3)],
             "y": round(y, 3) if y is not None else None, "ground": "design" if y is not None else "terrain",
             "tilt": tilt, "tiltDir": list(tdir), "place": "GameObject", "of": "庭方 gardens[%s].shokusai" % gz}
        if extra:
            o.update(extra)
        pts.append(o)

    # 汀線・中島・園路の芯(撒く木の芯をここへ落とさない ── 指図の形そのもの)
    water = [[tuple(q) for q in (g.get("migiwa") or {}).get("pts") or []] for g in d.get("gardens") or []]
    water = [w for w in water if len(w) >= 3]
    isl = [[tuple(q) for q in nk.get("outline") or []] for g in d.get("gardens") or [] for nk in g.get("nakajima") or []]
    paths = [(p, (g.get("enro") or {}).get("width_m") or 0.0) for g in d.get("gardens") or []
             for k in ("loopE", "loopW", "summit") for p in L.split_polyline((g.get("enro") or {}).get(k) or [], None)]

    def free(uv):
        if any(L._pip(uv, w) for w in water) or any(L._pip(uv, w) for w in isl):
            return False
        for P, wm in paths:
            if _line_d(uv, P) * M.KEN < wm / 2.0:
                return False
        return True

    for g in d.get("gardens") or []:
        gz = g["name"]
        sk = g.get("shokusai")
        rows = sk if isinstance(sk, list) else []
        if isinstance(sk, dict):      # 白洲の形(層の名 → 文)
            for lay, txt in sk.items():
                if lay in ("cert",) or not _rgx_uv(txt):
                    continue
                rows.append({"layer": lay, "parts": txt, "where": txt, "n": len(_rgx_uv(txt)), "species": "クロマツ" if "クロマツ" in txt else None})
        for k, s in enumerate(rows):
            lay = str(s.get("layer") or "")
            sp = s.get("species") or lay
            vs = _niwa_variants(s.get("parts"), A)
            n = int(s.get("n") or 0)
            if not vs:
                if n:
                    notes.append("⛔ 庭木 %s %s(%d 本): parts `%s` が在庫の変種に解けない ── 撒かない"
                                 % (gz, lay, n, s.get("parts")))
                continue
            m_ = re.search(r"×\s*([\d.]+)", str(s.get("parts") or ""))
            scale = float(m_.group(1)) if m_ else 1.0
            where = str(s.get("where") or "")
            rnd = L.seeded_rnd("%s/%s" % (gz, lay))
            got = 0
            # (a) 点で書かれた木
            for seg in where.split("/"):
                uvs = _rgx_uv(seg)
                if not uvs and "中島" in seg and isl:
                    uvs = [_centroid(isl[0])]
                for uv in uvs:
                    if got >= n:
                        break
                    v = vs[rnd.randrange(len(vs))]
                    if "中島" in seg:
                        v = next((x for x in vs if x["size"] == "Small"), v)
                    tilt, tdir, why = 0.0, (0.0, 1.0), None
                    mt = re.search(r"(東|西|南|北|南西|南東|北西|北東)へ\s*([\d.]+)\s*°", seg)
                    if mt:
                        dd = {"北": (1, 0), "南": (-1, 0), "西": (0, 1), "東": (0, -1), "南西": (-0.7071, 0.7071),
                              "南東": (-0.7071, -0.7071), "北西": (0.7071, 0.7071), "北東": (0.7071, -0.7071)}
                        tilt, tdir = float(mt.group(2)), dd[mt.group(1)]
                    elif "傾け" in seg:
                        why = "⚠ 傾けの角度が指図に無い ── 立てて据える"
                    if not free(uv) and "中島" not in seg:
                        why = ((why + " / ") if why else "") + "⚠ 指図の点が汀の内か園路の上"
                    got += 1
                    row("Niwa_%s_%s%02d" % (gz, lay[:2], got), gz, lay, sp, v, uv, scale, tilt, tdir,
                        {"where": seg.strip(), "note": why} if why else {"where": seg.strip()})
            # (b) 矩形の塊(`u a..b v c..d`)── 塊ごとの本数は `塊3/5/3` か `に7` の宣言
            blocks = re.findall(r"([^/:]*?)\s*u\s*(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)\s*v\s*(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)\s*(?:に\s*(\d+))?|"
                                r"([^/:]*?)\s*v\s*(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)\s*u\s*(-?[\d.]+)\s*\.\.\s*(-?[\d.]+)\s*(?:に\s*(\d+))?", where)
            mk = re.search(r"塊\s*([\d/]+)", where)
            ks_ = [int(x) for x in mk.group(1).split("/")] if mk else []
            for bi, b in enumerate(blocks):
                if b[1]:
                    lab, ua, ub, va, vb, nn = b[0], b[1], b[2], b[3], b[4], b[5]
                else:
                    lab, va, vb, ua, ub, nn = b[6], b[7], b[8], b[9], b[10], b[11]
                cnt = int(nn) if nn else (ks_[bi] if bi < len(ks_) else 0)
                if cnt <= 0:
                    notes.append("⛔ 庭木 %s %s: 塊 `%s` の本数が読めない ── 撒かない" % (gz, lay, lab.strip())); continue
                u0, u1 = sorted((float(ua), float(ub)))
                v0, v1 = sorted((float(va), float(vb)))
                placed, tries = 0, 0
                while placed < cnt and tries < 400:
                    tries += 1
                    uv = (rnd.uniform(u0, u1), rnd.uniform(v0, v1))
                    if not free(uv) or not L._pip(M.W(*uv), gw.get(gz, [])):
                        continue
                    v = vs[rnd.randrange(len(vs))]
                    cr = (v["rec"].get("crown_r") or max(v["rec"]["sx"], v["rec"]["sz"]) / 2.0) * scale
                    if any(math.hypot(q["world"][0] - M.W(*uv)[0], q["world"][1] - M.W(*uv)[1]) < cr * 0.6
                           for q in pts if q["zone"] == gz and q["layer"] == lay):
                        continue
                    placed += 1
                    got += 1
                    row("Niwa_%s_%s%02d" % (gz, lay[:2], got), gz, lay, sp, v, uv, scale,
                        extra={"where": lab.strip() or "塊%d" % (bi + 1)})
                if placed < cnt:
                    notes.append("⚠ 庭木 %s %s: 塊 `%s` は %d/%d 本(汀・中島・園路を避けて採りきれない)"
                                 % (gz, lay, lab.strip(), placed, cnt))
            if got < n:
                notes.append("⛔ 庭木 %s %s: %d/%d 本 ── 残り %d 本は位置が文でしか書かれていない(`%s`)── 撒かない"
                             % (gz, lay, got, n, n - got, where))
    return pts, notes
