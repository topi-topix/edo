"""土井の算出物の器(EDO-0533)。`bake_impl.py doi --write` が呼ぶ。

⭕ `graded` はいまの生成器(`build_sashizu.Model.graded_y` → `sashizu_lib.graded_y`)で世界の 1m 格子を焼く
  (岡部 `impl_okabe.bake_graded` と同じ手)。図で検めた地盤と建てる地盤が同じ物になる ──
  ⛔ 旧 `EdoDoiBuilder.DesignY/GradedY`(矩形の段・C# への写し)は案A の多角形の段と折れ線の坂を読めない。
⭕ `planting` は林方の設計(指図 `planting`)を撒いた点へ焼く(`bake_planting`・EDO-0533 S8)。撒き方・行の形・
  退ける形は岡部の焼き手と同じ共有の手(`sashizu_lib.plant_rnd` / `scatter_take` / `kakoi_lines` / `edashita_over_road` /
  `do_rin_rects`、行は `impl_okabe._row`)。土井の欄の形(parts の行が辞書・帯の区域が関係と目安・viewClusters・noPlant・
  道の肩の表)はここで読む。⛔ 読めない欄は黙って捨てず `planting.notes` に名乗る(規則19)。
⛔ `corners` は焼かない ── 土井の runs は seat が null の地形なりの区間を持ち、共通の焼き手(rseat)が読めない(外周の Stage で決める)。
⛔ gardens / base はまだ器に入れていない — 返さない(bake_impl が据え置きとして名指しで刷る)。
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
import impl_okabe as IO    # noqa: E402
import sashizu_lib as L    # noqa: E402

EST = "doi"


def bake():
    M = B.Model(EST)
    poly = BI.parcel_poly(EST)
    d = json.load(open(os.path.join(B.DOC, EST + "_sashizu.json"), encoding="utf-8"))
    p = os.path.join(B.DOC, EST + "_impl.json")
    im = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    graded = IO.bake_graded(M, poly)
    # checks.gradeTol = 実装側 ── 造成した地形と設計面の許容差[m](岡部・山王と同じ 0.30)。縁の皮(Stage4b)が穴を開ける升の閾に読む
    return {"graded": graded, "checks": {"gradeTol": 0.30}, "planting": bake_planting(M, d, graded, im)}


# ================================================================ 植栽(planting)の焼き手 ── EDO-0533 S8
#   ⭐ 林方の設計(指図 `planting`)を**撒いた点**へ焼く。実装(`EdoDoiBuilder.Stage8_Shokusai`)は
#     `impl.planting.points[]` をそのまま据えるだけ(⛔ 実装で撒き直さない)。
#   【硬い(許容0 ── 退ける)】区画の外 / 塀・囲い・土留めの実体線(区画の全辺・当家の練塀・F07・F11・土留め)から
#     `kakoiLineFrom`(2.0m)+半厚 / 面(noPlant[0] ── 名指しの木と稲荷の杜を除く)・庭・溜り・表長屋の背の路地・石段・
#     坂の敷き・動線の芯 ±0.5間 / 坂・動線・路の肩(`rampRule`・`shoulderCrownRule`)/ 棟の外面から 2.0間(`doRinKen`)・
#     長屋の外面から 軒の出+1.0m(低木 0.6m)・蔵・厩から 2.0間(低木 1.0間)/ 樹冠を井戸に掛けない / 面の縁の外 0.5m の
#     高木・中木(`terraceEdge`)/ 玉垣 F09 の内・埒 F04 と柵 F05 から 0.5間 / 玉石の受けから 0.75間 /
#     層をまたぐ幹の芯々 1.0m / 道(街路)の上の枝下 4.0m・屋敷の中の道の上の枝下 4.0m / 禁じた部材。
#   【柔らかい(狙い ── 撒かない所として満たす・名指しは最も近い所へ ⚠)】本数(`per100`)・芯々(`packRatio`)・
#     F09 から高木・中木 1.0間/低木 0.25間・庭の区画の外 1間 は低木まで・受けの 1.5間 内は低木まで・盛土の深さ
#     (`fillDepthMaxM`)・名指しの木の位置・塊の本数。
LAYS = IO.LAYS
TALL = IO.TALL
STEP_KEN = 0.5
SIZES = ("Small", "Mid", "Big", "H12", "H16", "H20", "H24")
NAGAYA_EAVE_M = 0.90        # 長屋の軒の出 ── 指図に欄が無く、地の文 drains[D12]「軒の出 0.90」・clearance.keidai.why「軒の出 0.9m」から採る
KURA = ("Kura1", "Kura2", "Kagogura", "Umaya")        # clearance.kura の「土蔵・御駕籠蔵・厩」


def _num(s):
    return float(s.replace("−", "-").replace("–", "-"))


def _meyasu(s):
    """meyasuUV の語(`u≈−32〜−9, v≈28〜52` / `v≈82〜96 の全幅` / `v≈96〜区画の西の端` / `u≈9, v≈25`)を
    (u0, u1, v0, v1) か点 (u, v) に読む。読めない向きは ±無限。戻り ("box", (u0,u1,v0,v1)) / ("pt", (u,v)) / None。"""
    if not s: return None
    N = r"([−\-–]?\d+(?:\.\d+)?)"
    out = {}
    for ax in ("u", "v"):
        m = re.search(ax + r"≈" + N + r"(?:\s*〜\s*" + N + r")?", s)
        if m:
            a = _num(m.group(1))
            b = _num(m.group(2)) if m.group(2) else None
            if b is None and re.search(ax + r"≈" + N + r"\s*〜", s):
                b = float("inf")
            out[ax] = (a, b)
    if not out: return None
    if all(v[1] is None for v in out.values()) and len(out) == 2:
        return ("pt", (out["u"][0], out["v"][0]))
    u = out.get("u", (-float("inf"), float("inf")))
    v = out.get("v", (-float("inf"), float("inf")))
    u = (min(u[0], u[1] if u[1] is not None else u[0]), max(u[0], u[1] if u[1] is not None else u[0]))
    v = (min(v[0], v[1] if v[1] is not None else v[0]), max(v[0], v[1] if v[1] is not None else v[0]))
    return ("box", (u[0], u[1], v[0], v[1]))


def _palette(d, notes):
    """層 → 変種の列 [{asset, part, prefab, size, idx, name, species, rec, edaMin}](`w` の重みだけ繰り返す)。
    ⭐ 土井の parts の行は辞書(`{api, asset, prefab, species, w, detail}`・大きさは `{size}` の穴)。文字列の行
      (岡部の書式)も `sashizu_lib.plant_part` で受ける。⭐ 大きさは `parts.hM` の層の丈の範囲(層名で始まる鍵の和)に
      素の丈(scaleY 1)が入る変種だけ ── `parts._` が言う `scaleRule.sizeRule` の欄は土井の指図に無い(名乗る)。
    ⛔ 禁じた部材・目録に無い変種は落として名乗る。"""
    import impl_sanno as IS
    A = IS.asset_index()
    parts = d["planting"]["parts"]
    hm = parts.get("hM") or {}
    if not (d["planting"].get("scaleRule") or {}).get("sizeRule"):
        notes.append("⚠ parts._ が言う scaleRule.sizeRule の欄が無い ── 大きさは parts.hM の層の丈の範囲に素の丈が入る変種を採った"
                     "(scaleY = 1・丈を倍率で合わせない)")
    pal = {}
    for lay in LAYS:
        rg = [v for k, v in hm.items() if (k == lay or k.startswith(lay + "_")) and isinstance(v, list) and len(v) == 2]
        lo = min(r[0] for r in rg) if rg else 0.0
        hi = max(r[1] for r in rg) if rg else 1e9
        out = []
        for s in (parts.get(lay) or []):
            rows = []
            if isinstance(s, dict):
                pf0 = s.get("prefab") or ""
                asset = s.get("asset") or ""
                fam, _, nm = asset.rpartition(".")
                fam = fam.split(".")[-1] if fam else ""
                if not fam or not nm or not pf0:
                    notes.append("parts[%s] の行が読めない(asset・prefab が無い): %s" % (lay, json.dumps(s, ensure_ascii=False)))
                    continue
                sizes = SIZES if "{size}" in pf0 else (None,)
                for sz in sizes:
                    pf = pf0.replace("{size}", sz) if sz else pf0
                    mi = re.search(r"_(\d\d)$", pf)
                    rows.append((fam, nm, sz or "", int(mi.group(1)) if mi else 1, pf,
                                 (s.get("api") or "").replace("{size}", sz or ""), s.get("species") or nm,
                                 int(s.get("w") or 1)))
            else:
                pp = L.plant_part(s)
                if pp is None:
                    notes.append("parts[%s] の行が読めない: %s" % (lay, s)); continue
                for sz in pp["sizes"]:
                    for i in pp["idx"]:
                        pf = "Tree_%s_%s%s" % (pp["name"], sz, "" if i <= 1 else "_%02d" % i)
                        rows.append((pp["fam"], pp["name"], sz, i, pf, '%s.%s("%s")' % (pp["fam"], pp["name"], sz),
                                     IO.SPECIES.get(pp["name"]) or pp["note"] or pp["name"], 1))
            got = 0
            for fam, nm, sz, i, pf, api, sp, w in rows:
                if any(f in nm for f in IO.FORBID):
                    notes.append("⛔ parts[%s] に禁じた部材 %s ── 撒かない" % (lay, nm)); break
                rec = A.get(pf)
                if rec is None:
                    if "{size}" not in str(s.get("prefab") if isinstance(s, dict) else ""):
                        notes.append("parts[%s] の変種 %s が目録に無い ── 落とした" % (lay, pf))
                    continue
                if not (lo - 1e-6 <= rec["sy"] <= hi + 1e-6):
                    continue
                prof = L.edashita_profile(rec.get("edashita"))
                v = {"asset": "%s.%s.%s.%d" % (fam, nm, sz, i) if sz else "%s.%s.Mid.%d" % (fam, nm, i),
                     "part": api, "prefab": pf, "size": sz, "idx": i, "name": nm, "species": sp, "rec": rec,
                     "edaMin": min(h for _r, h in prof) if prof else None}
                out += [v] * max(1, w)
                got += 1
            if rows and got == 0:
                notes.append("⚠ parts[%s] の行 %s: hM の丈 %.1f〜%.1fm に入る変種が目録に無い ── 落とした"
                             % (lay, rows[0][4], lo, hi))
        pal[lay] = out
    # 下草・つるは点に焼かない(名乗る)
    if parts.get("下草"):
        notes.append("parts[下草] は detail(地形の詳細メッシュで撒く)── 点に焼かない")
    if parts.get("つる"):
        notes.append("⚠ parts.つる(林縁の高木の幹 5 本に 1 本・幹径 0.40〜0.85m)は焼いていない ── 幹径は据えた現物で測る物で、"
                     "宿主の名指し(onTree)を焼く手が土井に無い(岡部の PlantFromImpl の二巡目の口は Stage8 にも残す)")
    return pal


def _seg_d(p, a, b):
    return IO._sd(p, a, b)


def _pl_d(p, P):
    return min(_seg_d(p, P[i], P[i + 1]) for i in range(len(P) - 1)) if len(P) > 1 else math.hypot(p[0] - P[0][0], p[1] - P[0][1])


class _Site(object):
    """撒く場所の硬い制約をまとめて持つ(世界 xz で測る)。行の形は `impl_okabe._row` と同じ口(M・y・need・is_road)。"""

    def __init__(self, M, d, graded, im, notes):
        self.M, self.d = M, d
        self.gat = L.grid_sampler(graded)
        ken = self.ken = M.KEN
        pl = d["planting"]
        av = pl["bandDef"]["avoid"]
        self.av = av
        self.sh = dict((k, float(v) * ken) for k, v in (av.get("kaidanShoulderKen") or {}).items())
        self.shk = dict((k, float(v) * ken) for k, v in (av.get("kattemichiShoulderKen") or {}).items())
        self.edaRamp = float((av.get("edaShitaOverRampM") or {}).get("hard") or 0.0)
        # ---- 塀・囲い・土留めの実体線(C29 と同じ関数 kakoi_lines / kakoi_line_keepout)
        m = L.kakoi_line_m(d)
        self.kakoiM = m
        runs = {}
        for r in M.runs:
            if not r.mine: continue
            if r.kind == "Dobei" or r.name in ("F07", "F11"):
                runs.setdefault(r.name, {"name": r.name, "kind": "塀" if r.kind == "Dobei" else r.kind, "segs": []})["segs"].append((r.a, r.b))
        for w in d.get("terraceWalls") or []:
            if w.get("a") and w.get("b"):
                runs[w["name"]] = {"name": w["name"], "kind": "土留め", "of": "wall", "segs": [(M.W(*w["a"]), M.W(*w["b"]))]}
            else:
                notes.append("⚠ 土留め %s: 線(a・b)が無い ── 関係(between・extent)を解く手が無いので退けていない"
                             "(北の境の長屋の外面からの離れが同じ所を覆う)" % w.get("name"))
        self.road_edges = B.Checks(M).road_edges()
        lines = L.kakoi_lines(d, M.poly, list(runs.values()), None, self.road_edges)
        self.lines = lines
        self.K = L.kakoi_line_keepout(lines, m, d) if m is not None else []
        if m is None:
            notes.append("⛔ avoid.kakoiLineFrom の宣言が無い ── 塀・囲い・土留めの線から退けていない")
        if not av.get("kakoiLineExceptEdges"):
            notes.append("⚠ 松江松平との谷の境(辺16〜26)にも区画の線から 2.0m の退避を掛けた ── 掲示板 EDO-0533 の申し送り"
                         "「この区間に kakoiLineFrom を掛けない」(EDO-0554 施主裁定)は指図の欄に無い。外すなら "
                         "planting.bandDef.avoid.kakoiLineExceptEdges に辺の番号を書けば、この焼き手と C29 が同じ一本で読む")
        # ---- 面・庭・明地・路
        self.terr = [(t.name, [M.W(*q) for q in t.poly]) for t in M.terraces]
        self.gard = [(g.name, [M.W(*q) for q in g.poly]) for g in M.gardens]
        self.excl = list(self.gard)
        for a in d.get("akichi") or []:
            if a.get("name") == "Tamari" and a.get("u0") is not None:
                self.excl.append(("溜り Tamari", [M.W(*q) for q in B.rect(a["u0"], a["v0"], a["u1"], a["v1"])]))
        self.michi = []                    # [(名, 帯の多角形(世界))]
        for mi in d.get("michi") or []:
            P = self._michi_poly(mi)
            if P is None:
                notes.append("⚠ 路 %s: 帯が解けない(along の辺に当家の長屋が無い)── 退けていない" % mi.get("name")); continue
            self.michi.append((mi["name"], P))
        notes.append("⚠ 路(michi)の帯は along の辺の当家の長屋の内の壁から幅 w 間で起こした(指図は形を持たない・U)")
        for nm, P in self.michi:
            if nm == "UraRoji": self.excl.append(("表長屋の背の路地 UraRoji", P))
        # ---- 坂・動線
        self.ramps = []                    # (名, 芯の折れ線(世界), 半幅, 肩の表)
        for r in d.get("ramps") or []:
            w = float(r.get("w") or ken)
            if r.get("pts"):
                P9 = [M.W(*q[:2]) for q in r["pts"]]
                self.ramps.append((r["name"], P9, w / 2.0, "kaidan"))
            elif r.get("u0") is not None:
                u0, u1, v0, v1 = r["u0"], r["u1"], r["v0"], r["v1"]
                if abs(u1 - u0) >= abs(v1 - v0):
                    P9 = [M.W(u0, (v0 + v1) / 2.0), M.W(u1, (v0 + v1) / 2.0)]
                else:
                    P9 = [M.W((u0 + u1) / 2.0, v0), M.W((u0 + u1) / 2.0, v1)]
                self.ramps.append((r["name"], P9, w / 2.0, "katte"))
            else:
                notes.append("⚠ 坂 %s: 芯が読めない ── 退けていない" % r.get("name"))
        for r in M.routes:
            self.ramps.append((r.name, list(r.pts), 0.5 * ken, "katte"))
        self.kaidans = [(k.name, [M.W(*q) for q in k.poly]) for k in M.kaidans if k.poly]
        # ---- 棟・長屋・蔵
        self.munes = [(m.name, [M.W(*q) for q in m.poly]) for m in M.munes]
        self.R = L.do_rin_rects(d)
        self.doRin = float(((pl.get("clearance") or {}).get("keidai") or {}).get("doRinKen") or 0.0)
        self.links = [(l.name, [M.W(*q) for q in l.poly]) for l in M.links]
        self.kura, self.nagaya = [], []
        for s in M.service:
            (self.kura if s.name in KURA else self.nagaya).append((s.name, [M.W(*q) for q in s.poly]))
        dep = (M.const.get("inubashiri") or 0.0) + (M.const.get("nagayaD") or 0.0)
        self.kita = []
        for r in d.get("runs") or []:
            if r.get("kind") != "Nagaya" or r.get("s0") is None: continue
            a, b = M.edge_pt(r["edge"], r["s0"]), M.edge_pt(r["edge"], r["s1"])
            n = M.inward(r["edge"])
            P = [a, b, (b[0] + n[0] * dep, b[1] + n[1] * dep), (a[0] + n[0] * dep, a[1] + n[1] * dep)]
            self.nagaya.append((r["name"], P))
            if r["edge"] in (14, 15): self.kita.append((r["name"], P))
        notes.append("⚠ 供待・惣後架・平家長屋・家中長屋・稲荷社は clearance.nagaya(軒の出 %.2fm + 1.0m・低木 0.6m)で退けた"
                     "(clearance に名の無い附属屋)/廊下(links)も同じ値・棟(munes)の低木は 0.6m(欄に無い)" % NAGAYA_EAVE_M)
        self.cl_tall = NAGAYA_EAVE_M + 1.0
        self.cl_low = 0.6
        self.cl_kura_tall = 2.0 * ken
        self.cl_kura_low = 1.0 * ken
        import impl_sanno as IS
        ir = IS.asset_index().get("Matsudaira_Ido")
        self.well_r = (math.hypot(ir["sx"], ir["sz"]) / 2.0) if ir else 1.0
        self.wells = [(w.name, M.W(*w.uv)) for w in M.wells]
        # ---- 柵・玉垣
        fpts = dict((f["name"], [M.W(*q[:2]) for q in f.get("pts") or []]) for f in d.get("fences") or [] if f.get("pts"))
        self.fence_line = [(nm, fpts[nm]) for nm in ("F04", "F05") if nm in fpts]
        self.f09 = fpts.get("F09")
        if not self.f09:
            notes.append("⚠ 玉垣 F09 の線が無い ── 玉垣の内・離れを退けていない")
        notes.append("⚠ 柵 F04・F05・F09 の線は fences[].pts(目安 ── 正は rel)で測った")
        # ---- 溝・受け(drains は線を持たない)
        self.uke = None
        for dr in d.get("drains") or []:
            mm = (dr.get("meyasu") or {}).get("uke") if isinstance(dr.get("meyasu"), dict) else None
            if mm:
                q = re.findall(r"[−\-–]?\d+(?:\.\d+)?", mm)
                if len(q) >= 2: self.uke = M.W(_num(q[0]), _num(q[1]))
        self.drainKen = float(av.get("drainKen") or 0.0) * ken
        za = next((t for t in M.terraces if t.name == "Za_Inari"), None)
        self.d13 = None
        if za is not None:
            vmin = min(q[1] for q in za.poly)
            us = [q[0] for q in za.poly]
            self.d13 = [M.W(min(us) - 0.5, vmin - 0.25), M.W(max(us) + 0.5, vmin - 0.25)]
        notes.append("⚠ 溝(drains)は線を持たない ── drainRule 0.75間 は D11 の玉石の受け(meyasu.uke)と D13(座の東の縁の外の溝 ── "
                     "座の v− の縁から外 0.25間 に置いたとみた U)だけ退けた。ほかの溝・埋樋(umedoiRule 1.0間)は実装の輪で測る(未検査)")
        self.is_road = L.road_region(M.poly, [(q["id"], q["pts"]) for q in json.load(open(BI.PARCELS, encoding="utf-8"))["parcels"]])
        self.need = float(av.get("edaShitaOverRoadM") or 0.0)
        self.rx = float(pl["plantRule"].get("crossLayerTrunkMinM") or 0.0)
        # 屋敷の中の道(枝下 4.0m を見る所)── 坂・動線・路の帯・馬場の走路
        self.inroad = [(nm, P9, hw) for nm, P9, hw, _k in self.ramps]
        self.inroad_poly = [(nm, P) for nm, P in self.michi] + [(nm, P) for nm, P in self.terr if nm == "Baba"]
        self._raster_inroad()

    RS = 0.25          # 屋敷の中の道の升[m](枝下の検めで道の上かを引く ── 帯ごとにその外接の升だけ塗る)

    def _raster_inroad(self):
        xs = [q[0] for q in self.M.poly]
        zs = [q[1] for q in self.M.poly]
        self.rx0, self.rz0 = min(xs) - 2.0, min(zs) - 2.0
        self.rnx = int((max(xs) + 2.0 - self.rx0) / self.RS) + 1
        self.rnz = int((max(zs) + 2.0 - self.rz0) / self.RS) + 1
        on = self.road_mask = set()
        rs = self.RS

        def span(lo, hi, o, n):
            return range(max(0, int((lo - o) / rs)), min(n, int((hi - o) / rs) + 2))
        for _nm, P9, hw in self.inroad:
            for a, b in zip(P9, P9[1:]):
                for i in span(min(a[0], b[0]) - hw, max(a[0], b[0]) + hw, self.rx0, self.rnx):
                    for j in span(min(a[1], b[1]) - hw, max(a[1], b[1]) + hw, self.rz0, self.rnz):
                        c = (self.rx0 + (i + 0.5) * rs, self.rz0 + (j + 0.5) * rs)
                        if _seg_d(c, a, b) < hw: on.add((i, j))
        for _nm, P in self.inroad_poly:
            for Q in self._polys(P):
                for i in span(min(q[0] for q in Q), max(q[0] for q in Q), self.rx0, self.rnx):
                    for j in span(min(q[1] for q in Q), max(q[1] for q in Q), self.rz0, self.rnz):
                        if L._pip((self.rx0 + (i + 0.5) * rs, self.rz0 + (j + 0.5) * rs), Q): on.add((i, j))

    def _michi_poly(self, mi):
        M, ken = self.M, self.ken
        es = [int(x) for x in re.findall(r"辺(\d+)", str(mi.get("along") or "")) or []]
        m2 = re.search(r"辺(\d+)・(\d+)", str(mi.get("along") or ""))
        if m2: es = [int(m2.group(1)), int(m2.group(2))]
        if not es or not mi.get("w"): return None
        dep = (M.const.get("inubashiri") or 0.0) + (M.const.get("nagayaD") or 0.0)
        w = float(mi["w"]) * ken
        segs = []
        for r in self.d.get("runs") or []:
            if r.get("kind") != "Nagaya" or r.get("edge") not in es or r.get("s0") is None: continue
            segs.append((r["edge"], r["s0"], r["s1"]))
        if not segs: return None
        # 辺ごとに一続きの長屋の内の壁の線(最小 s〜最大 s)から幅 w ── 辺が二つなら二枚を一つの多角形の組にする
        polys = []
        for e in sorted(set(s[0] for s in segs)):
            s0 = min(s[1] for s in segs if s[0] == e)
            s1 = max(s[2] for s in segs if s[0] == e)
            a, b = M.edge_pt(e, s0), M.edge_pt(e, s1)
            n = M.inward(e)
            polys.append([(a[0] + n[0] * dep, a[1] + n[1] * dep), (b[0] + n[0] * dep, b[1] + n[1] * dep),
                          (b[0] + n[0] * (dep + w), b[1] + n[1] * (dep + w)), (a[0] + n[0] * (dep + w), a[1] + n[1] * (dep + w))])
        return polys if len(polys) > 1 else polys[0]

    # 路の帯は一枚か複数枚
    @staticmethod
    def _polys(P):
        return P if P and isinstance(P[0], list) else [P]

    def in_parcel(self, p):
        return L._pip(p, self.M.poly)

    def on_terrace(self, p):
        return next((nm for nm, P in self.terr if L._pip(p, P)), None)

    def base_block(self, p):
        """層に依らない硬い制約。退ける理由か None。⛔ 面(noPlant[0])はここで退けない ── 名指しの木・稲荷の杜が面に立つ。"""
        if not self.in_parcel(p): return "区画の外"
        h = L.kakoi_keepout_hit(self.K, p[0], p[1])
        if h is not None: return "%s から %.1fm 未満" % (h, self.kakoiM)
        for nm, P in self.excl:
            for Q in self._polys(P):
                if L._pip(p, Q): return nm + " の上"
        for nm, P in self.kaidans + self.munes + self.links + self.kura + self.nagaya:
            if L._pip(p, P): return nm + " の上"
        for nm, P9, hw, _k in self.ramps:
            if _pl_d(p, P9) < hw - 1e-9: return nm + " の敷き"
        if self.f09 and len(self.f09) >= 3 and L._pip(p, self.f09): return "玉垣 F09 の内"
        for nm, P in self.fence_line:
            if _pl_d(p, P) < 0.5 * self.ken - 1e-9: return "%s の線から 0.5間 未満" % nm
        if self.uke is not None and math.hypot(p[0] - self.uke[0], p[1] - self.uke[1]) < self.drainKen - 1e-9:
            return "玉石の受け(D11)から 0.75間 未満"
        if self.d13 is not None and _pl_d(p, self.d13) < self.drainKen - 1e-9:
            return "溝 D13 から 0.75間 未満"
        return None

    def shoulder(self, lay, v, tbl):
        s = (self.sh if tbl == "kaidan" else self.shk).get(lay, 0.0)
        if v is not None and v.get("edaMin") is not None and v["edaMin"] < 4.0:
            s = max(s, IO._crown_r(v))                   # shoulderCrownRule(枝下 4.0m 未満の木は樹冠の半径)
        return s

    def layer_block(self, p, lay, crown_r=0.0, v=None):
        """層に依る硬い制約(肩・棟の離れ・蔵・井戸・面の縁)。"""
        for nm, P9, hw, tbl in self.ramps:
            s = self.shoulder(lay, v, tbl)
            if _pl_d(p, P9) < hw + s - 1e-9: return "%s の敷き+肩 %.2fm" % (nm, s)
        for nm, P in self.michi:
            s = self.shoulder(lay, v, "katte")
            for Q in self._polys(P):
                if IO._poly_d(p, Q) < s - 1e-9: return "路 %s の肩 %.2fm" % (nm, s)
        for nm, P in self.kaidans:
            sh = self.sh.get(lay, 0.0)
            if IO._poly_d(p, P) < sh - 1e-9: return "%s の肩 %.2fm 未満" % (nm, sh)
        tall = lay in TALL
        if tall and self.doRin > 0:
            u, w = self.M.UV(p[0], p[1])
            dm, nm = L.do_rin_dist(self.R, u, w)
            if dm < self.doRin - 1e-9: return "棟 %s の外面から %.1f間 未満" % (nm, self.doRin)
        cl = self.cl_tall if tall else self.cl_low
        for nm, P in self.munes:
            if not tall and IO._poly_d(p, P) < self.cl_low - 1e-9: return "%s の外面から %.2fm 未満" % (nm, self.cl_low)
        for nm, P in self.nagaya + self.links:
            if IO._poly_d(p, P) < cl - 1e-9: return "%s の外面から %.2fm 未満" % (nm, cl)
        ck = self.cl_kura_tall if tall else self.cl_kura_low
        for nm, P in self.kura:
            if IO._poly_d(p, P) < ck - 1e-9: return "%s から %.1f間 未満" % (nm, ck / self.ken)
        for nm, w in self.wells:
            if math.hypot(p[0] - w[0], p[1] - w[1]) < crown_r + self.well_r - 1e-9:
                return "樹冠が井戸 %s に掛かる" % nm
        if tall and not self.on_terrace(p):
            for nm, P in self.terr:
                if IO._poly_d(p, P) < 0.5 - 1e-9: return "面 %s の縁の外 0.5m 未満" % nm
        return None

    def y(self, p):
        y = self.gat(p[0], p[1])
        if y is not None: return y, "design"
        g = self.M.dem.at(p[0], p[1])
        return (g if g is not None else 0.0), "terrain"

    def on_inroad(self, q):
        """屋敷の中の道(坂・動線・路の帯・馬場の走路)の上か ── 0.25m の升で引く(升の芯で塗った)。"""
        return (int(math.floor((q[0] - self.rx0) / self.RS)), int(math.floor((q[1] - self.rz0) / self.RS))) in self.road_mask

    def eda_ok(self, row):
        """道(街路)の上の枝下 `edaShitaOverRoadM` と屋敷の中の道の上の枝下 `edaShitaOverRampM.hard`(硬い)。"""
        if self.need > 0:
            f = L.edashita_over_road(row, row["_rec"], self.is_road, lambda q: self.M.dem.at(q[0], q[1]), self.need,
                                     own_poly=self.M.poly)
            if f is not None: return False
        if self.edaRamp > 0:
            prof = L.edashita_profile(row["_rec"].get("edashita"))
            reach = (prof[-1][0] if prof else 0.0) + 0.5
            p = tuple(row["world"])
            near = any(_pl_d(p, P9) < hw + reach for _n, P9, hw in self.inroad) or \
                any(IO._poly_d(p, Q) < reach for _n, P in self.inroad_poly for Q in self._polys(P))
            if near:
                f = L.edashita_over_road(row, row["_rec"], self.on_inroad,
                                         lambda q: self.gat(q[0], q[1]), self.edaRamp)
                if f is not None: return False
        return True


def _best_near(S, target, lay, v, allow_terrace=True, rmax=20.0, step=0.25, nang=32, ok=None):
    """`target` に最も近い、硬い制約を全部満たす点(PlaceBest の型)。無ければ (None, None)。"""
    cr = IO._crown_r(v)
    r = 0.0
    while r <= rmax + 1e-9:
        for k in (range(nang) if r > 0 else [0]):
            a = 2.0 * math.pi * k / nang
            p = (target[0] + r * math.cos(a), target[1] + r * math.sin(a))
            if S.base_block(p) or S.layer_block(p, lay, cr, v): continue
            if not allow_terrace and S.on_terrace(p): continue
            if ok is not None and not ok(p): continue
            return p, r
        r += step
    return None, None


def bake_planting(M, d, graded, im):
    pl = d.get("planting")
    if not isinstance(pl, dict):
        return {"points": [], "notes": ["⛔ 指図に planting が無い"], "bands": []}
    pr = pl["plantRule"]
    notes, out, band_note = [], [], []
    S = _Site(M, d, graded, im, notes)
    pal = _palette(d, notes)
    ken = M.KEN
    notes.append("⚠ plantRule.placement(松・落葉・中木 = TerrainTree / 低木 = DetailMesh)は焼いていない ── 岡部と同じく全点を "
                 "GameObject の点で焼いた(place = GameObject)。TerrainTree・DetailMesh へ据える手は実装に無い")
    seeded = dict((lay, []) for lay in LAYS)

    def others(lay):
        return [p for k, v in seeded.items() if k != lay for p in v]

    def rx_ok(q, lay):
        return all(math.hypot(q[0] - o[0], q[1] - o[1]) >= S.rx for o in others(lay))

    def emit(row, lay):
        seeded[lay].append(tuple(row["world"]))
        out.append(row)

    def mk(nm, grp, lay, v, p, extra=None):
        return IO._row(S, nm, grp, lay, v, p, extra)

    # ================= 名指しの木
    za = next((t for t in M.terraces if t.name == "Za_Inari"), None)
    tani = next((a for a in d.get("akichi") or [] if a.get("name") == "NishiTanizoko"), None)
    tamari = next((a for a in d.get("akichi") or [] if a.get("name") == "Tamari"), None)
    omote = next((r for r in d.get("ramps") or [] if r.get("name") == "R_OmoteSaka"), None)
    r10 = next((P9 for nm, P9, hw, _k in S.ramps if nm == "R10"), None)
    for t in pl.get("namedTrees") or []:
        lay = t.get("layer") or "落葉"
        nm = t["name"]
        near = t.get("near") or ""
        hf = t.get("hFrom") or ""
        kind = t.get("kind") or ""
        cand = [v for v in pal.get(lay, []) if v["species"].split("(")[0] in kind or kind.split("(")[0] in v["species"]
                or v["name"] in kind] or pal.get(lay, [])
        msz = re.search(r"Own\.(\w+)\s+(\w+)\s*の丈", hf)
        if msz:
            cand = [v for v in cand if v["name"] == msz.group(1) and v["size"] == msz.group(2)] or cand
        elif "上端" in hf and cand:
            top = max(v["rec"]["sy"] for v in cand)
            cand = [v for v in cand if v["rec"]["sy"] >= top - 1e-6]
        rnd, key = L.plant_rnd(d, nm, lay)
        tgt, how, ok_extra, allow_t, sizes = None, None, None, True, None
        if "R_OmoteSaka の上端" in near and omote:
            P9 = [M.W(*q[:2]) for q in omote["pts"]]
            a, b = omote["pts"][-2], omote["pts"][-1]
            Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            nu, nv = -(b[1] - a[1]) / Ln, (b[0] - a[0]) / Ln          # 左の法線(uv)
            sgn = -1.0 if "南" in near else 1.0                        # 格子は +u = 北 ⇒ 南 = −u の側
            if nu * sgn < 0: nu, nv = -nu, -nv
            hw = float(omote["w"]) / 2.0
            tgt = M.W(b[0] + nu * (hw / ken + 1.5 + 0.5), b[1] + nv * (hw / ken + 1.5 + 0.5))
            how = "R_OmoteSaka の上端の%sの脇・坂の辺から樹冠の半径以上(最小 1.5間)・面の縁(法肩)から 1.0m" % ("南" if sgn < 0 else "北")
            notes.append("⚠ 名指しの木 %s: near の「法肩から内 1.0m 以上」は、面の縁から幹の芯を 1.0m 離す(面の上でも法の側でも)と読んだ(U)" % nm)

            def ok_extra(q, v, P9=P9, hw=hw):
                # 「法肩から内 1.0m 以上」── 読みが二つある(面の上で縁から 1.0m 内/法の側で肩から 1.0m)。
                #   どちらでも幹を肩から 1.0m 離すことは同じなので、面の縁からの距離 ≥ 1.0m で測る(U・名乗る)
                if _pl_d(q, P9) < hw + max(IO._crown_r(v), 1.5 * ken) - 1e-9: return False
                return all(IO._poly_d(q, Pt) >= 1.0 - 1e-9 if not L._pip(q, Pt) else
                           min(_seg_d(q, Pt[i], Pt[(i + 1) % len(Pt)]) for i in range(len(Pt))) >= 1.0 - 1e-9
                           for _n9, Pt in S.terr)
        elif "社の東の脇" in near and za is not None:
            us = [q[0] for q in za.poly]
            vmin = min(q[1] for q in za.poly)
            tgt = M.W((min(us) + max(us)) / 2.0, vmin - 2.0)
            how = "稲荷の座の東(v−)の脇・玉垣 F09 から 1.5間・北の境の長屋の屋根に樹冠を掛けない・道の縁から 2.0m"
            sizes = ["Big", "Mid", "Small"]

            def ok_extra(q, v):
                cr = IO._crown_r(v)
                if L._pip(q, [M.W(*p9) for p9 in za.poly]): return False
                if S.f09 and _pl_d(q, S.f09) < 1.5 * ken - 1e-9: return False
                if any(IO._poly_d(q, P) < cr + NAGAYA_EAVE_M - 1e-9 for _n, P in S.kita): return False
                if r10 is not None and _pl_d(q, r10) < 0.5 * ken + 2.0 - 1e-9: return False
                return True
        elif "西の谷底" in near and tani:
            mt = _meyasu(t.get("meyasuUV"))
            tgt = M.W(*mt[1]) if mt and mt[0] == "pt" else M.W(tani["u0"] + 3, tani["v0"] + 3)
            how = "西の谷底の東寄り(meyasuUV)・玉石の受けから 3間"

            def ok_extra(q, v):
                if S.uke is not None and math.hypot(q[0] - S.uke[0], q[1] - S.uke[1]) < 3.0 * ken - 1e-9: return False
                return not S.on_terrace(q)
        elif "谷頭の平場の西の縁の外" in near:
            mt = _meyasu(t.get("meyasuUV"))
            tg = next((t9 for t9 in M.terraces if t9.name == "Tanigashira"), None)
            if mt and mt[0] == "pt":
                tgt = M.W(*mt[1])
            elif tg is not None:
                tgt = M.W((min(q[0] for q in tg.poly) + max(q[0] for q in tg.poly)) / 2.0, max(q[1] for q in tg.poly) + 1.0)
            how = "谷頭の平場の西の縁の外(崖の裾・meyasuUV)"
            allow_t = False
        elif "溜りの西の縁" in near and tamari:
            tgt = M.W((tamari["u0"] + tamari["u1"]) / 2.0, tamari["v1"])
            how = "通用門の内の溜りの西の縁(+v の縁の中)"
        if tgt is None:
            notes.append("⛔ 名指しの木 %s: `near` が解けない(%s)── 撒かない" % (nm, near)); continue
        got = None
        tried = []
        for sz in (sizes or [None]):
            cs = [v for v in cand if sz is None or v["size"] == sz]
            if not cs: continue
            v = IO._pick(rnd, cs)
            okf = (lambda q, v=v, lay=lay, nm=nm: (ok_extra is None or ok_extra(q, v)) and rx_ok(q, lay)
                   and S.eda_ok(mk(nm, "", lay, v, q)))
            p, r = _best_near(S, tgt, lay, v, allow_terrace=allow_t, rmax=12.0 if sizes else 20.0, ok=okf)
            tried.append(sz or v["size"])
            if p is not None:
                got = (v, p, r)
                break
        if got is None:
            notes.append("⛔ 名指しの木 %s: 狙い(%s)の近くに硬い制約を満たす所が無い(大きさ %s を試した)── 撒かない"
                         % (nm, how, "・".join(tried)))
            continue
        v, p, r = got
        nm2 = nm
        if t.get("nameRule") and v["size"] == "Small" and "神木" in nm:
            nm2 = "社脇の常緑木"
            notes.append("⚠ 名指しの木 %s: Small に落ちたので nameRule で「%s」と名乗った" % (nm, nm2))
        row = mk(nm2, "名指しの木", lay, v, p, {"of": "名指しの木", "near": how, "movedM": round(r, 2), "nameOf": nm})
        if sizes and v["size"] != sizes[0]:
            notes.append("⚠ 名指しの木 %s: 大きさ %s は入らず %s で建てた(hFrom の順)" % (nm, "・".join(tried[:-1]), v["size"]))
        if r > 0.01:
            notes.append("⚠ 名指しの木 %s: 狙い(%s)から %.2fm 寄せた(硬い制約の外へ)" % (nm2, how, r))
        emit(row, lay)

    # ================= 林の塊(viewClusters)
    gapMin = pl.get("clusterGapMin")
    for c in pl.get("viewClusters") or []:
        cn = c.get("name")
        if cn == "表の道の上の額縁" and omote:
            lay = "松"
            mm = re.search(r"松(\d+)", c.get("mix") or "")
            want = int(mm.group(1)) if mm else 4
            P9 = [M.W(*q[:2]) for q in omote["pts"]]
            a, b = omote["pts"][-2], omote["pts"][-1]
            Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            tu, tv = (b[0] - a[0]) / Ln, (b[1] - a[1]) / Ln
            nu, nv = -tv, tu
            hw = float(omote["w"]) / 2.0
            rnd, key = L.plant_rnd(d, "林の塊／" + cn, lay)
            got, moved = 0, []
            for i in range(want):
                side = 1.0 if i % 2 == 0 else -1.0
                back = (i // 2) * 3.0                                # 上端から坂を下る向きへ 0・3間
                v = IO._pick(rnd, pal[lay])
                off = hw / ken + max(IO._crown_r(v), 1.5 * ken) / ken + 0.25
                tg = M.W(b[0] - tu * back + nu * off * side, b[1] - tv * back + nv * off * side)

                def okf(q, v=v):
                    if _pl_d(q, P9) < hw + max(IO._crown_r(v), 1.5 * ken) - 1e-9: return False
                    if any(math.hypot(q[0] - o[0], q[1] - o[1]) < 4.0 for o in seeded["松"]): return False
                    return rx_ok(q, "松") and S.eda_ok(mk("", "", "松", v, q))
                p, r = _best_near(S, tg, lay, v, rmax=6.0, ok=okf)
                if p is None: continue
                emit(mk("額縁_松%02d" % (got + 1), "林の塊／" + cn, lay, v, p, {"movedM": round(r, 2)}), lay)
                got += 1
                if r > 0.01: moved.append(r)
            band_note.append({"band": "林の塊／" + cn, "layer": lay, "seed": key, "want": want, "got": got,
                              "moved": len(moved), "movedMaxM": round(max(moved), 2) if moved else 0.0,
                              "soft": None if got >= want else "⚠ 本数の狙い未達(坂の辺から樹冠の半径以上・硬い制約の内で採りきれない)"})
        elif cn == "稲荷の杜" and za is not None:
            pass                                                     # 帯「稲荷の杜」で撒く(下)
        else:
            notes.append("⛔ 林の塊 %s: 区域を解く手が無い ── 撒かない" % cn)

    # ================= 帯の区域(関係 rel を解く手は無い ── meyasuUV の箱と谷底の勾配で切る・U)
    bdef = pl["bandDef"].get("bands") or {}
    boxes = []
    for bn, b9 in bdef.items():
        mt = _meyasu((b9 or {}).get("meyasuUV"))
        if mt and mt[0] == "box": boxes.append((bn, mt[1]))
    notes.append("⚠ 帯の区域は bandDef.bands[].meyasuUV の箱で切った(rel を解く手が無い・U)。西の谷底は箱の中で造成前の地盤の勾配"
                 " < 0.1 の所(rel の条件)、ほかの谷の箱の中は「西の谷の斜面」。どの箱にも入らない面は最も近い箱(3間 以内)へ寄せ、"
                 "それより遠い面は撒かない(下の leftover に面積を刷る)")
    order = ["表長屋の背の低地(屋敷林)", "西の谷底(湿った低地)", "泉水の南の外法(盛土)", "南の崖(谷頭・岡部の谷筋)",
             "台地の南東の崖(厩・門の内へ)", "西の谷の斜面(地山)"]
    boxes.sort(key=lambda bx: order.index(bx[0]) if bx[0] in order else 99)
    base = M.base or M.dem

    def slope(p):
        h0 = base.at(p[0], p[1])
        if h0 is None: return None
        gx = [base.at(p[0] + dx, p[1]) for dx in (-1.0, 1.0)]
        gz = [base.at(p[0], p[1] + dz) for dz in (-1.0, 1.0)]
        if None in gx or None in gz: return None
        return math.hypot((gx[1] - gx[0]) / 2.0, (gz[1] - gz[0]) / 2.0)

    def inbox(u, v, bx):
        return bx[0] <= u <= bx[1] and bx[2] <= v <= bx[3]

    def boxdist(u, v, bx):
        du = max(bx[0] - u, 0.0, u - bx[1])
        dv = max(bx[2] - v, 0.0, v - bx[3])
        return math.hypot(du, dv)

    cells = {}
    raw_area, leftover = {}, 0
    u0, v0, u1, v1 = M.bb_uv
    cell_m2 = (STEP_KEN * ken) ** 2
    garden_ring = [(nm, P) for nm, P in S.gard]
    u = math.floor(u0) + STEP_KEN / 2
    while u <= u1:
        v = math.floor(v0) + STEP_KEN / 2
        while v <= v1:
            uu, vv = u, v
            v += STEP_KEN
            p = M.W(uu, vv)
            if not S.in_parcel(p) or S.on_terrace(p): continue
            why = S.base_block(p)
            if why is not None and (why.endswith(" の上") or why.endswith(" の敷き") or why == "玉垣 F09 の内"):
                continue                                         # 面積にも数えない所
            bn = None
            for nm9, bx in boxes:
                if inbox(uu, vv, bx):
                    bn = nm9
                    break
            if bn is None and boxes:
                nm9, bx = min(boxes, key=lambda q: boxdist(uu, vv, q[1]))
                if boxdist(uu, vv, bx) <= 3.0: bn = nm9
            if bn is None:
                leftover += 1
                continue
            if bn == "西の谷底(湿った低地)":
                sl = slope(p)
                if sl is None or sl >= 0.1: bn = "西の谷の斜面(地山)"
            raw_area[bn] = raw_area.get(bn, 0) + 1
            cells.setdefault(bn, []).append((p, why))
        u += STEP_KEN
    if leftover:
        notes.append("⚠ どの帯の箱(3間 以内)にも入らない面 %.0fm² ── 撒かない(面の外の摺り付けの法・道の脇など。"
                     "slopeRule.engineered の「芝のまま」と読める所も含む)" % (leftover * cell_m2))
    notes.append("⚠ 帯の中の偏り(西の谷の斜面の松は肩寄り t<0.4・落葉は下半 t>0.5、南の崖の松は肩寄り・落葉は法尻寄り、"
                 "表長屋の背は崖の裾へ寄せる)は焼いていない ── t(top − 地盤)/(top − 法尻)を解く手が無い。帯の中に一様に撒いた")

    # ---- 柔らかい制約(撒かない所として満たす)
    fd = (pl.get("slopeRule") or {}).get("fillDepthMaxM") or {}

    def soft_ok(p, lay):
        if lay in TALL:
            if S.f09 and _pl_d(p, S.f09) < 1.0 * ken: return False
            if any(IO._poly_d(p, P) < 1.0 * ken for _n, P in garden_ring): return False
            if S.uke is not None and math.hypot(p[0] - S.uke[0], p[1] - S.uke[1]) < 1.5 * ken: return False
            if lay in fd:
                gy, by = S.gat(p[0], p[1]), base.at(p[0], p[1])
                if gy is not None and by is not None and gy - by > float(fd[lay]): return False
        else:
            if S.f09 and _pl_d(p, S.f09) < 0.25 * ken: return False
        return True

    # ================= 列(馬場の西の縁)
    rule_bands = pr.get("bands") or {}
    bb = next((t for t in M.terraces if t.name == "Baba"), None)
    if "馬場の西の縁" in rule_bands and bb is not None:
        mm = re.search(r"芯々\s*(\d+(?:\.\d+)?)〜(\d+(?:\.\d+)?)m", rule_bands["馬場の西の縁"].get("rule") or "")
        s0, s1 = (float(mm.group(1)), float(mm.group(2))) if mm else (4.0, 7.0)
        vmax = max(q[1] for q in bb.poly)
        uu = sorted(q[0] for q in bb.poly)
        a, b9 = (uu[0], vmax), (uu[-1], vmax)
        rnd, key = L.plant_rnd(d, "馬場の西の縁", "松")
        Lk = (b9[0] - a[0])
        s = rnd.uniform(s0, s1) / ken / 2.0
        want = got = 0
        moved = []
        while s < Lk:
            want += 1
            v = IO._pick(rnd, pal["松"])
            tg = M.W(a[0] + s, vmax + 1.0)
            okf = (lambda q, v=v: rx_ok(q, "松") and all(math.hypot(q[0] - o[0], q[1] - o[1]) >= s0 * 0.9 for o in seeded["松"])
                   and S.eda_ok(mk("", "", "松", v, q)))
            p, r = _best_near(S, tg, "松", v, allow_terrace=False, rmax=s0 / 2.0, ok=okf)
            if p is not None:
                emit(mk("馬場の西の縁_松%03d" % (got + 1), "馬場の西の縁", "松", v, p, {"movedM": round(r, 2)}), "松")
                got += 1
                if r > 0.01: moved.append(r)
            s += rnd.uniform(s0, s1) / ken
        band_note.append({"band": "馬場の西の縁", "row": "松の一列(芯々 %.0f〜%.0fm)" % (s0, s1), "layer": "松", "seed": key,
                          "want": want, "got": got, "spacingM": [s0, s1], "insetKen": -1.0,
                          "moved": len(moved), "movedMaxM": round(max(moved), 2) if moved else 0.0,
                          "soft": "列の芯々は狙い ── 硬い制約で抜けた所は撒かない" if got < want else None})
        notes.append("⚠ 馬場の西の縁の列は、馬場の西(+v)の縁から外へ 1間 の線を狙いにした(位置の値は指図に無い・U)")
    if "北の境の長屋の前・家中長屋・土蔵" in rule_bands:
        notes.append("⛔ 帯「北の境の長屋の前・家中長屋・土蔵」: 長屋の前は台地(面)の上で noPlant[0](硬)が退ける・家中長屋の棟間は"
                     "植えない・西の妻と奥の塀の間の法面は区域が解けない ── 撒かない(欄の衝突は普請奉行へ)")
    if "谷頭の平場・厩の平場" in rule_bands:
        notes.append("帯「谷頭の平場・厩の平場」: 面の上は名指しの木だけ(rule)── 撒かない")

    # ================= 稲荷の杜(面の上の群)
    if "稲荷の杜" in rule_bands and za is not None:
        us = [q[0] for q in za.poly]
        vmin = min(q[1] for q in za.poly)
        cand_c = []
        u = min(us) - 1.0 + STEP_KEN / 2
        while u < max(us) + 1.0:
            v = vmin - 4.0 + STEP_KEN / 2
            while v < vmin:
                p = M.W(u, v)
                if S.base_block(p) is None: cand_c.append(p)
                v += STEP_KEN
            u += STEP_KEN
        mm = re.search(r"中木\s*(\d+)〜(\d+)", rule_bands["稲荷の杜"].get("rule") or "")
        want = int(mm.group(2)) if mm else 3
        lay = "中木"
        smalls = [v for v in pal[lay] if v["size"] == "Small"] or pal[lay]
        rnd, key = L.plant_rnd(d, "稲荷の杜", lay)
        memo = {}

        def acc(p, memo=memo, rnd=rnd):
            v = IO._pick(rnd, smalls)
            if S.layer_block(p, lay, IO._crown_r(v), v) is not None: return False
            if not soft_ok(p, lay): return False
            row = mk("", "稲荷の杜", lay, v, p)
            if not S.eda_ok(row): return False
            memo[p] = row
            return True
        pts, r_, rx_ = L.scatter_take(rnd, cand_c, want, 2.0, seeded=seeded[lay], other=others(lay), rx=S.rx, accept=acc)
        for j, p in enumerate(pts):
            row = memo[p]
            row["name"] = "稲荷の杜_中木%02d" % (j + 1)
            emit(row, lay)
        band_note.append({"band": "稲荷の杜", "layer": lay, "seed": key, "want": want, "got": len(pts),
                          "candM2": round(len(cand_c) * cell_m2, 1), "rminUsed": round(r_, 3), "relax": rx_,
                          "soft": None if len(pts) >= want else "⚠ 本数の狙い未達(硬い制約の内で採りきれない ── 入る本数で建てた)"})
        notes.append("⚠ 稲荷の杜の面は座の v− の縁から 4間・座の u の幅 ±1間 の箱を候補にし、五つの退避を硬い制約で抜いた(箱の大きさは U)。"
                     "中木は Small(林方「中木 Small なら2本は入る」)")

    # ================= 帯の散布
    pack = float(pr.get("packRatio") or 1.0)
    for lay in LAYS:
        for bn in sorted(cells):
            dens = ((rule_bands.get(bn) or {}).get("per100")) or {}
            per = float(dens.get(lay) or 0.0)
            if per <= 0: continue
            if not pal[lay]:
                notes.append("⛔ 帯 %s の %s: 変種が無い ── 撒かない" % (bn, lay)); continue
            crmax = max(IO._crown_r(v) for v in pal[lay])
            cand = [p for p, why in cells[bn] if why is None and soft_ok(p, lay)]
            area = len(cand) * cell_m2
            n = int(math.floor(area * per / 100.0 + 0.5))
            rmin = math.sqrt(100.0 / per) * pack
            rnd, key = L.plant_rnd(d, bn, lay)
            memo, rej = {}, set()

            def acc(p, lay=lay, bn=bn, rnd=rnd, memo=memo, rej=rej):
                # ⭐ 退けた点は覚える(芯々を緩めて採り直す巡でも同じ点を測り直さない ── 硬い制約は芯々に依らない)
                if p in rej: return False
                if p in memo: return True
                v = IO._pick(rnd, pal[lay])
                if S.layer_block(p, lay, IO._crown_r(v), v) is not None or not S.eda_ok(mk("", bn, lay, v, p)):
                    rej.add(p)
                    return False
                memo[p] = mk("", bn, lay, v, p)
                return True
            pts, r_, rx_ = L.scatter_take(rnd, cand, n, rmin, seeded=seeded[lay], other=others(lay), rx=S.rx, accept=acc)
            for j, p in enumerate(pts):
                row = memo[p]
                row["name"] = "%s_%s%04d" % (bn.split("(")[0], lay, j + 1)
                emit(row, lay)
            band_note.append({"band": bn, "layer": lay, "seed": key, "per100": per,
                              "bandM2": round(raw_area.get(bn, 0) * cell_m2, 1), "plantableM2": round(area, 1),
                              "designN": int(math.floor(raw_area.get(bn, 0) * cell_m2 * per / 100.0 + 0.5)),
                              "want": n, "got": len(pts), "rmin": round(rmin, 3), "rminUsed": round(r_, 3), "relax": rx_,
                              "crownMaxM": round(crmax, 2),
                              "soft": ("⚠ 芯々を %d 回緩めた" % rx_ if rx_ else None) if len(pts) >= n
                              else "⚠ 本数の狙い未達(硬い制約の内で採りきれない)"})
    for bn in sorted(cells):
        per = float((((rule_bands.get(bn) or {}).get("per100")) or {}).get("下草") or 0.0)
        if per > 0:
            band_note.append({"band": bn, "layer": "下草", "per100": per, "bandM2": round(raw_area.get(bn, 0) * cell_m2, 1),
                              "want": int(math.floor(raw_area.get(bn, 0) * cell_m2 * per / 100.0 + 0.5)), "got": 0,
                              "soft": "点に焼かない ── parts[下草] は detail(地形の詳細メッシュで撒く)"})
    for bn, b9 in rule_bands.items():
        if (b9 or {}).get("per100") and bn not in cells:
            notes.append("⛔ 帯 %s: 区域が解けない(meyasuUV の箱に面が無い)── 撒かない" % bn)
    notes.append("⚠ bandDef.invariants.裸地 0(林の帯の地表を低木か下草で覆う)は地表の塗り(surface)と下草の詳細メッシュの持ち場 ── 点では検めない")
    notes.append("⚠ clearance.niwa(庭の区画の外 1間 は低木まで)・F09 からの離れ・受けの 1.5間・盛土の深さ(fillDepthMaxM)は柔らかい"
                 "制約で、帯の散布では撒かない所として満たした(名指しの木には掛けていない)")

    # ================= 検め(層をまたぐ芯々・塊どうし)
    xl = []
    for i, a in enumerate(out):
        for b in out[i + 1:]:
            if a["layer"] != b["layer"] and math.hypot(a["world"][0] - b["world"][0], a["world"][1] - b["world"][1]) < S.rx - 1e-9:
                xl.append((a["name"], b["name"]))
    cg = None
    if gapMin is not None:
        gs = {}
        for q in out:
            if q["group"].startswith("林の塊／") or q["group"] == "稲荷の杜":
                gs.setdefault(q["group"], []).append(q["world"])
        ks = sorted(gs)
        dm = [min(math.hypot(a[0] - b[0], a[1] - b[1]) for a in gs[ks[i]] for b in gs[ks[j]]) / ken
              for i in range(len(ks)) for j in range(i + 1, len(ks))]
        cg = {"minKen": float(gapMin), "groups": ks, "worstKen": round(min(dm), 2) if dm else None,
              "soft": None if not dm or min(dm) >= float(gapMin) else "△ 狙い未達"}
    for r in out:
        r.pop("_rec", None)
    return {"points": out, "bands": band_note, "notes": notes,
            "walls": [{"name": w["name"], "kind": w["kind"], "segs": len(w["segs"]), "halfM": round(w["half"], 3),
                       "halfFrom": w["halfFrom"], "facing": w.get("facing", True)} for w in S.lines],
            "crossLayer": {"minM": S.rx, "pairs": len(xl), "worst": xl[:5]},
            "clusterGap": cg,
            "seedRule": pr.get("seed"),
            "_": "**撒いた木の点**(林方の設計 `planting` から焼いた)。⛔ 実装側で撒き直さない。種は `plantRule.seed` の宣言から"
                 "決定論的に作るので、同じ指図からは同じ配置が出る。asset は `族.名.寸法.個体`(PlantByKey の書式)・world は世界 xz"}
