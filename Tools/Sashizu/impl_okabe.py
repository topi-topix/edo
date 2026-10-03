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
⛔ rails / kui / migiwa / gardens はまだ器が無い — 返さない(bake_impl が据え置きとして名指しで刷る)。
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
    return {"graded": graded, "corners": BI.bake_corners(poly, d, im), "base": bake_base(M, poly, d),
            "planting": bake_planting(M, poly, d, graded)}


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
TOE_M = 1.5        # ⚠ 法尻の土留め(位置を指図が持たない)を区画線からこの距離まで在るとみる ── 保守側・U
#                    (EDO-0502 GradeSaka の「法尻は硬い 1.5m」と同じ値。⛔ 線の位置が指図に入ったら外す)
_DIRV = {"北": (1.0, 0.0), "南": (-1.0, 0.0), "西": (0.0, 1.0), "東": (0.0, -1.0)}   # uv の外向き(u+=北・v+=西)


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


def _edge_nums(s):
    """「辺12〜15」「辺24・辺28北端・辺26〜27」の辺番号。"""
    out = []
    for a, b in re.findall(r"辺(\d+)(?:〜(\d+))?", s or ""):
        out += list(range(int(a), int(b or a) + 1))
    return out


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
    """**土留めの実体線**(世界 xz)を指図の関係(`terraceWalls[].between`)から解く。指図は座標を持たない(規則2・5)。

    ・面と面の間 → 高い面の縁のうち低い面から 2間 以内の辺(天端の線)
    ・面と区画の辺(「辺12〜15」)→ その面の縁のうち、中点に最も近い区画の辺がその番号の辺
    ・面と方位(「Kadonouchi 西の縁」)→ その面の縁のうち外向きがその方位の辺
    ・法尻の土留め(between に「法尻」)→ 位置を指図が持たない ⇒ 名指しの区画の辺から `TOE_M` までに在るとみる(保守側)
    天端の奥行は `planting.bandDef.avoid.dodomeCrestDepthM`(野面 → 野面の乱積み・ほか → 城の石垣)。
    戻り (線 [{name, kind, segs, half, halfFrom}], 解けなかった名 [(名, 理由)])。
    """
    T = dict((t.name, t) for t in M.terraces)
    tbl = (((d.get("planting") or {}).get("bandDef") or {}).get("avoid") or {}).get("dodomeCrestDepthM") or {}
    ken = M.KEN
    lines, bad = [], []
    for w in d.get("terraceWalls") or []:
        bt = [str(x) for x in (w.get("between") or [])]
        ts = [T[x.split()[0]] for x in bt if x.split() and x.split()[0] in T]
        kd = "野面の乱積み" if "野面" in str(w.get("kind")) else "城の石垣"
        crest = float(tbl.get(kd) or tbl.get("城の石垣") or 0.0)
        segs, toe = [], False
        if len(ts) == 2:
            hi, lo = sorted(ts, key=lambda t: -t.y)
            P = hi.poly
            ed = [(max(_poly_d(P[i], lo.poly), _poly_d(P[(i + 1) % len(P)], lo.poly)), i) for i in range(len(P))]
            for dk, i in ed:
                if dk <= 2.0:
                    segs.append((M.W(*P[i]), M.W(*P[(i + 1) % len(P)])))
            if not segs:
                # ⚠ 間に石段・溜りの奥行がある組(Higashi↔TsuyoTamari)── 高い面の縁のうち低い面に最も近い辺を採る
                #   (最も近い辺の距離 + 1間 まで・5間 を超える組は解けないとする)
                dmin = min(e for e, _ in ed)
                if dmin <= 5.0:
                    for dk, i in ed:
                        mid = ((P[i][0] + P[(i + 1) % len(P)][0]) / 2, (P[i][1] + P[(i + 1) % len(P)][1]) / 2)
                        if dk <= dmin + 1.0 or _poly_d(mid, lo.poly) <= dmin + 1.0:
                            segs.append((M.W(*P[i]), M.W(*P[(i + 1) % len(P)])))
        elif len(ts) == 1:
            txt = " ".join(bt)
            en = _edge_nums(txt)
            t = ts[0]
            P = t.poly
            if "法尻" in txt and en:
                toe = True
                for e in en:
                    segs.append((M.poly[e], M.poly[(e + 1) % len(M.poly)]))
            elif en:
                for i in range(len(P)):
                    a, b = P[i], P[(i + 1) % len(P)]
                    mid = M.W((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                    if _nearest_edge(M, mid) in en:
                        segs.append((M.W(*a), M.W(*b)))
            else:
                dv = next((v for k, v in _DIRV.items() if (k + "の縁") in txt), None)
                if dv is not None:
                    for i in range(len(P)):
                        n = _out_normal_uv(P, i)
                        if n[0] * dv[0] + n[1] * dv[1] > 0.7:
                            segs.append((M.W(*P[i]), M.W(*P[(i + 1) % len(P)])))
        if not segs:
            bad.append((w["name"], "between %s から線が解けない" % "・".join(bt)))
            continue
        lines.append({"name": w["name"], "kind": "土留め(%s)" % kd, "segs": segs,
                      "half": crest + (TOE_M if toe else 0.0),
                      "halfFrom": "天端の奥行 avoid.dodomeCrestDepthM[%s]" % kd
                                  + (" + 法尻の位置の幅 %.1fm(保守側・U)" % TOE_M if toe else "")})
    return lines, bad


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
