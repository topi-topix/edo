"""松江松平の算出物の器(EDO-0554)。`bake_impl.py matsudaira_dewa --write` が呼ぶ。

⭕ `graded` はいまの生成器(`build_sashizu.Model.graded_y`)で世界の 1m 格子を焼く(岡部・土井と同じ手 `impl_okabe.bake_graded`)。
⭕ `planting` は林方・庭方の設計(指図 `planting.groups` の庭の散布・`slopePlanting` の法面の散布・`slopePlantingZones` の
  穴埋め)を**撒いた点**へ焼く。撒き方・退ける形は共有の手(`sashizu_lib.plant_rnd` / `scatter_take` / `kakoi_lines` /
  `kakoi_line_keepout` / `edashita_over_road` / `road_region`)。⛔ 値を生成器に持たない ── 退避・芯々・本数・帯の境は指図の欄から読む。
  ⛔ 読めない欄は黙って捨てず `planting.notes` に名乗る(規則19)。
  ⭐ 旧 `matsudaira_dewa_planting_out.json`(9/20・退役した C# と旧生成器の散布)の代わり。実装(C# の 7')がこの点を読むよう
    直すのは棟梁の次の段。

【硬い(許容0 ── 退ける)】区画の外 / 塀・囲い・中仕切・垣・土留め・区画の全辺の実体線から `bandDef.avoid.kakoiLineFrom`(2.0m)
  ── 全層(下草も)/ 道辺(街路)から幹 `kyoukaiRoadM` 2.0m / 棟・廊下・附属屋・長屋・石段・池の上 / 道(街路)の上の枝下
  `edaShitaOverRoadM` 4.0m / `plantRule.keepout`(+`keepoutByRole`・層の `keepoutByLayer`・`clr`・`crownRule`)の退避 /
  `gardens[].avoid` の箱 / 層をまたぐ幹の芯々(下の `_cross_need`)。
【柔らかい(狙い ── 最も近い所へ置いて ⚠)】本数 `n`・芯々 `spacing`×`packRatio`(採りきれなければ緩める・回数を記録)・
  `at` の名指しの位置(動かした距離を記録)。
"""
import hashlib
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

EST = "matsudaira_dewa"
WOODY = ("高木", "中木", "低木")
GSTEP = 0.1          # 庭の候補の格子[間](箱は 1〜3 間と小さい)
SSTEP = 1.0          # 法面の候補の格子[m](旧生成器 slope_samples と同じ刻み)


def bake():
    M = B.Model(EST)
    poly = BI.parcel_poly(EST)
    d = json.load(open(os.path.join(B.DOC, EST + "_sashizu.json"), encoding="utf-8"))
    graded = IO.bake_graded(M, poly)
    return {"graded": graded, "planting": bake_planting(M, d, graded)}


# ================================================================ 幾何(uv = 主郭グリッドの間 / world = 世界 xz[m])
def _sd(p, a, b):
    return IO._sd(p, a, b)


def _pl_d(p, P):
    return min(_sd(p, P[i], P[i + 1]) for i in range(len(P) - 1)) if len(P) > 1 else math.hypot(p[0] - P[0][0], p[1] - P[0][1])


def _poly_d(p, P):
    return IO._poly_d(p, P)


def _h01(key):
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], 16) / float(16 ** 12)


def _rnd(d, name, lay):
    """撒く種 ── 共有の `sashizu_lib.plant_rnd`(種 = 「区・帯の名 + '/' + 層の名」)。⭐ 松江松平は `plantRule` を指図の頂に持つ
    (他邸は `planting.plantRule`)ので、その欄を同じ口へ渡す(値は変えない)。"""
    return L.plant_rnd({"planting": {"plantRule": d.get("plantRule") or (d.get("planting") or {}).get("plantRule")}}, name, lay)


# ================================================================ 部材
def _variants(e, A, forbid, notes):
    """行の `parts`(`n` の重み)→ 変種の列。⛔ 禁じた部材・目録に無い部材は落として名乗る。"""
    out = []
    for p in e.get("parts") or []:
        pf, api = p.get("prefab"), p.get("api") or ""
        if not pf:
            notes.append("parts の行に prefab が無い: %s" % json.dumps(p, ensure_ascii=False)); continue
        if any(f and (f in api or f.split("/")[-1].split(".")[0] in pf) for f in forbid):
            notes.append("⛔ %s/%s に禁じた部材 %s ── 撒かない" % (e.get("zone") or e.get("band"), e.get("layer"), api)); continue
        rec = A.get(pf)
        if rec is None:
            notes.append("⚠ %s/%s の部材 %s が目録に無い ── 落とした" % (e.get("zone") or e.get("band"), e.get("layer"), pf)); continue
        m = re.match(r"^\s*([A-Za-z]+)\.([A-Za-z0-9]+)(?:\(([^)]*)\))?", api)
        fam, nm, args = (m.group(1), m.group(2), m.group(3) or "") if m else ("", pf, "")
        aa = [a.strip().strip('"') for a in args.split(",") if a.strip()]
        size = next((a for a in aa if not a.isdigit()), "")
        idx = int(next((a for a in aa if a.isdigit()), "1"))
        v = {"prefab": pf, "part": api, "asset": "%s.%s%s.%d" % (fam, nm, ("." + size) if size else "", idx),
             "size": size, "name": nm, "rec": rec, "scale": float(p.get("scale") or 1.0),
             "jit": p.get("scaleJitter") or e.get("scaleJitter")}
        out += [v] * max(1, int(p.get("n") or 1))
    return out


def _crown_m(v, sc):
    r = v["rec"]
    return (r.get("crown_r") or max(r["sx"], r["sz"]) / 2.0) * sc


# ================================================================ 場所(硬い制約と退避)
class _Site(object):
    def __init__(self, M, d, graded, notes):
        self.M, self.d, self.ken = M, d, M.KEN
        self.gat = L.grid_sampler(graded)
        pr = d.get("plantRule") or {}
        self.pr = pr
        av = d["planting"]["bandDef"]["avoid"]
        self.road_m = float(av.get("kyoukaiRoadM") or 0.0)
        self.need = float(av.get("edaShitaOverRoadM") or 0.0)
        self.kakoiM = L.kakoi_line_m(d)
        W = M.W
        # ---- 塀・囲い・中仕切・垣・土留めの実体線(C29 と同じ関数)
        decl = (pr.get("clearance") or {}).get("kakoiLineFrom") or av.get("kakoiLines") or []
        runs = []
        if "run" in decl or "fence" in decl:
            for r in M.runs:
                if r.mine:
                    runs.append({"name": r.name, "kind": "塀" if r.kind == "Dobei" else r.kind[:8], "segs": [(r.a, r.b)]})
        if "nakajikiri" in decl:
            for n in d.get("nakajikiri") or []:
                if n.get("a") and n.get("b"):
                    runs.append({"name": n["name"], "kind": "中仕切", "segs": [(W(*n["a"]), W(*n["b"]))]})
                else:
                    notes.append("⚠ 中仕切 %s: 線(a・b)が無い ── 退けていない" % n.get("name"))
        self.kaki = []
        for t in d.get("tenkei") or []:
            if t.get("a") and t.get("b") and ("垣" in str(t.get("kind")) or "Kaki" in t["name"]):
                self.kaki.append((t["name"], tuple(t["a"]), tuple(t["b"])))
                if "kaki" in decl:
                    runs.append({"name": t["name"], "kind": "垣", "segs": [(W(*t["a"]), W(*t["b"]))]})
        for w in d.get("terraceWalls") or []:
            if w.get("a") and w.get("b"):
                runs.append({"name": w["name"], "kind": "土留め", "of": "wall", "segs": [(W(*w["a"]), W(*w["b"]))]})
            else:
                notes.append("⚠ 土留め %s: 線(a・b)が無い ── 退けていない" % w.get("name"))
        self.road_edges = B.Checks(M).road_edges() or []
        self.lines = L.kakoi_lines(d, M.poly, runs, None, self.road_edges)
        self.K = L.kakoi_line_keepout(self.lines, self.kakoiM, d) if self.kakoiM is not None else []
        if self.kakoiM is None:
            notes.append("⛔ avoid.kakoiLineFrom の宣言が無い ── 塀・囲いの線から退けていない")
        notes.append("⭐ 塀・囲い・中仕切・垣・土留め・区画の全辺の実体線から幹の芯 %.1fm は全層(下草も)に当てた"
                     "(C29 が全層を測る・plantRule.clearance.roles は高木・中木・低木)" % (self.kakoiM or 0.0))
        notes.append("⚠ 土留め(terraceWalls)の天端の奥行 avoid.dodomeCrestDepthM が無い ── 線(a・b)の実体 0 で退けた")
        # ---- 上に立てない物(C17 と同じ集合)+ 長屋の床
        self.blds = [(k, b.name, list(b.poly)) for k, b in M.buildings()]
        dep = (M.const.get("inubashiri") or 0.0) + (M.const.get("nagayaD") or 0.0)
        for r in M.runs:
            if r.mine and r.kind == "Nagaya":
                n = M.inward(r.edge)
                P = [r.a, r.b, (r.b[0] + n[0] * dep, r.b[1] + n[1] * dep), (r.a[0] + n[0] * dep, r.a[1] + n[1] * dep)]
                self.blds.append(("長屋", r.name, [M.UV(*q) for q in P]))
        self.kaidans = [(k.name, list(k.poly)) for k in M.kaidans if k.poly]
        # 退避(keepout.kaidan)を当てる石段 ── 旧生成器と同じく「庭の段」(築山・遠見・滝見の飛石の段)は外す(上に立てないのは C17 と同じに残す)
        kraw = dict((k.get("name"), k) for k in d.get("kaidans") or [])
        self.kaidans_ko = [(nm, P) for nm, P in self.kaidans if (kraw.get(nm) or {}).get("kind") != "庭の段"]
        self.water = [(w.name, list(w.pts)) for w in M.water]
        self.wells = [(w.name, tuple(w.uv)) for w in M.wells]
        self.routes = [(r.name, [tuple(q) for q in r.uv], r.raw) for r in M.routes]
        self.tenkei = [(t["name"], (t["u"], t["v"]), float(t.get("spread") or 0.0))
                       for t in d.get("tenkei") or [] if "u" in t and "a" not in t and "pts" not in t]
        pond = (d.get("sensui") or {}).get("pond") or {}
        self.pond = [tuple(q) for q in pond.get("outline") or []]
        self.pond_ko = pond.get("keepout") or {}
        self.is_road = L.road_region(M.poly, [(q["id"], q["pts"]) for q in json.load(open(BI.PARCELS, encoding="utf-8"))["parcels"]])
        self.exempt = set(pr.get("clrExempt") or [])
        self.byrole = pr.get("keepoutByRole") or {}
        self.ko = pr.get("keepout") or {}
        self.koAdd = pr.get("keepoutAdd") or {}
        self.croles = set((pr.get("crownRule") or {}).get("roles") or [])

    # ---- 値
    def kov(self, v, route=None):
        """退避の値[間]。数はそのまま間・文字列は const の欄を間に直す(`nokiE`)・`routeHalf` は園路の半幅 + keepoutAdd.route。"""
        if v == "routeHalf":
            w = (route or {}).get("w")
            return (float(w) / 2.0 + float(self.koAdd.get("route") or 0.0)) if w else float(self.ko.get("route") or 0.0)
        if v == "toriiFoot":
            tr = self.d["const"]["toriiRule"]
            fc = [float((r.get("toriiFoot") or {}).get("fernClr") or 0.0) for r in self.d.get("routes") or [] if isinstance(r.get("toriiFoot"), dict)]
            return (float(tr["nemakiOuterW"]) / 2.0 + (max(fc) if fc else 0.0)) / self.ken
        if isinstance(v, str):
            return float(self.d["const"][v]) / self.ken
        return float(v)

    def base_ko(self, kk, role, ovr, route=None):
        val = self.ko.get(kk, 0.0)
        if kk in (self.byrole.get(role) or {}):
            val = self.byrole[role][kk]
        if ovr and kk in ovr:
            val = ovr[kk]
        return self.kov(val, route)

    # ---- 硬い制約(world)
    def hard(self, w, uv, role):
        M = self.M
        if not L._pip(w, M.poly): return "区画の外"
        h = L.kakoi_keepout_hit(self.K, w[0], w[1])
        if h is not None: return "%s から %.1fm 未満" % (h, self.kakoiM)
        if self.road_edges and min(_sd(w, a, b) for a, b in self.road_edges) < self.road_m - 1e-9:
            return "道辺から %.1fm 未満" % self.road_m
        for k, nm, P in self.blds:
            if L._pip(uv, P): return "%s %s の上" % (k, nm)
        for nm, P in self.kaidans:
            if L._pip(uv, P): return "石段 %s の上" % nm
        for nm, P in self.water:
            if L._pip(uv, P): return "水 %s の上" % nm
        return None

    # ---- 退避(uv・間)── 旧生成器 free_fn の読みを写した
    def keep(self, uv, role, clr, crR, ovr=None, skip=None, pondClr=None):
        add = max(0.0, crR - clr) if role in self.croles else 0.0
        sk = skip or []
        for k, nm, P in self.blds:
            kk = {"棟": "mune", "廊下": "link", "附属屋": "service", "長屋": "run"}.get(k, "service")
            if any(s in nm for s in sk): continue
            r = self.base_ko(kk, role, ovr) + clr + add
            if _poly_d(uv, P) < r - 1e-9: return "%s %s から %.2f間 未満" % (k, nm, r)
        for nm, q in self.wells:
            r = self.base_ko("well", role, ovr) + clr + add
            if math.hypot(uv[0] - q[0], uv[1] - q[1]) < r - 1e-9: return "井戸 %s から %.2f間 未満" % (nm, r)
        for nm, P in self.kaidans_ko:
            r = self.base_ko("kaidan", role, ovr) + clr + add
            if _poly_d(uv, P) < r - 1e-9: return "石段 %s から %.2f間 未満" % (nm, r)
        for nm, P, raw in self.routes:
            if len(P) < 2 or any(s in nm for s in sk): continue
            kk = "roji" if raw.get("kind") == "niwa" else "route"
            r = self.base_ko(kk, role, ovr, raw) + (0.0 if kk in self.exempt else clr + add)
            if _pl_d(uv, P) < r - 1e-9: return "園路 %s の芯から %.2f間 未満" % (nm, r)
        for nm, q, spr in self.tenkei:
            if any(s in nm for s in sk): continue
            r = self.base_ko("tenkei", role, ovr) + (0.0 if "tenkei" in self.exempt else clr + add) + (spr if role != "下草" else 0.0)
            if math.hypot(uv[0] - q[0], uv[1] - q[1]) < r - 1e-9: return "点景 %s から %.2f間 未満" % (nm, r)
        if self.pond:
            if L._pip(uv, self.pond): return "御泉水(水面)"
            sb = crR if pondClr == "crown" else (float(pondClr) if pondClr is not None else float(self.pond_ko.get(role) or 0.0))
            if sb > 0 and _poly_d(uv, self.pond) < sb - 1e-9: return "御泉水の汀から %.2f間 未満" % sb
        return None

    def y(self, w):
        y = self.gat(w[0], w[1])
        if y is not None: return y, "design"
        g = self.M.dem.at(w[0], w[1])
        return (g if g is not None else 0.0), "terrain"

    def eda_ok(self, row, rec):
        """道(街路)の上の枝下(硬い)。⛔ 目録に枝下の無い部材(松・低木・下草)は、樹冠(scaleXZ 込みの半径)が道の上へ
        一寸も出ない所だけに立てる(保守側 ── 測れない物を道際に立てない)。"""
        if self.need <= 0: return True
        if L.edashita_profile(rec.get("edashita")):
            return L.edashita_over_road(row, rec, self.is_road, lambda q: self.M.dem.at(q[0], q[1]), self.need,
                                        own_poly=self.M.poly) is None
        cr = row["crownM"] / 2.0
        x0, z0 = row["world"]
        if min(_sd((x0, z0), self.M.poly[i], self.M.poly[(i + 1) % len(self.M.poly)]) for i in range(len(self.M.poly))) > cr:
            return True
        return not any(self.is_road((x0 + rr * math.cos(a), z0 + rr * math.sin(a)))
                       for rr in (cr * 0.5, cr) for a in [2 * math.pi * k / 24 for k in range(24)])


# ================================================================ 植栽
def bake_planting(M, d, graded):
    pl = d.get("planting")
    if not isinstance(pl, dict) or not pl.get("groups"):
        return {"points": [], "notes": ["⛔ 指図に planting.groups が無い"], "bands": []}
    import impl_sanno as IS
    A = IS.asset_index()
    pr = d.get("plantRule") or {}
    notes, out, band_note = [], [], []
    S = _Site(M, d, graded, notes)
    ken = M.KEN
    forbid = [str(f) for f in pr.get("forbidden") or []]
    pack0 = float(pr.get("packRatio") or 1.0)
    jit0 = pr.get("scaleJitter")
    rx_decl = pr.get("crossLayerTrunkMinM")
    RX = float(rx_decl) if rx_decl is not None else 1.0
    if rx_decl is None:
        notes.append("⛔ plantRule.crossLayerTrunkMinM(層をまたぐ幹の芯々)の宣言が無い ── 山王・岡部・土井の宣言と同じ 1.0m を硬く当てた"
                     "(差し戻し: 指図に宣言してほしい)。下草は退けない。庭と法面の高木・中木どうしは旧生成器の cross_scatter_clearance と"
                     "同じく max(clr, 樹冠の半径)[m] も当てた(U)")
    placed = []          # (world, role, entry_id, need_m, src, crownR_m, clr)

    def cross_ok(w, role, eid, need, src, crR, clr):
        if role not in WOODY: return True
        for q in placed:
            if q[2] == eid or q[1] not in WOODY: continue
            dm = math.hypot(w[0] - q[0][0], w[1] - q[0][1])
            nd = RX
            if src != q[4] and role in S.croles and q[1] in S.croles:
                nd = max(nd, clr, q[6], crR, q[5])
            if dm < nd - 1e-9: return False
        return True

    def mkrow(nm, grp, e, v, w, rnd, extra=None):
        uv = M.UV(w[0], w[1])
        y, gsrc = S.y(w)
        jit = v["jit"] or e.get("scaleJitter") or jit0
        sc = v["scale"] * (rnd.uniform(float(jit[0]), float(jit[1])) if jit else 1.0)
        tl = e.get("tilt") or [0.0, 0.0]
        tdir = e.get("tiltDir") or "none"
        ang = rnd.uniform(0.0, 2 * math.pi)
        row = {"name": nm, "group": grp, "zone": e.get("zone") or e.get("band"), "role": e["role"], "layer": e["layer"],
               "species": e.get("species"), "asset": v["asset"], "part": v["part"], "prefab": v["prefab"], "size": v["size"],
               "h": round(v["rec"]["sy"] * sc, 3), "scaleY": round(sc, 4), "scaleXZ": round(sc, 4),
               "crownM": round(2.0 * _crown_m(v, sc), 3), "u": round(uv[0], 4), "v": round(uv[1], 4),
               "world": [round(w[0], 3), round(w[1], 3)], "y": round(y, 3), "ground": gsrc,
               "tilt": round(rnd.uniform(float(tl[0]), float(tl[1])), 2) if tdir != "none" else 0.0,
               "tiltDir": tdir if tdir in ("-u", "+u", "-v", "+v") else [round(math.cos(ang), 3), round(math.sin(ang), 3)],
               "yaw": round(math.degrees(rnd.uniform(0.0, 2 * math.pi)), 1), "place": "GameObject"}
        if extra: row.update(extra)
        return row

    def try_place(w, e, eid, src, v, rnd, need, gk):
        """硬い制約を全部見る。通れば行、だめなら None。"""
        uv = M.UV(w[0], w[1])
        role = e["role"]
        if S.hard(w, uv, role): return None
        clr = float(e.get("clr") or 0.0)
        crR = _crown_m(v, v["scale"]) / ken
        if gk(uv, role, clr, crR): return None
        row = mkrow("", "", e, v, w, rnd)
        if not S.eda_ok(row, v["rec"]): return None
        if not cross_ok(w, role, eid, need, src, row["crownM"] / 2.0, clr * ken): return None
        return row

    def emit(row, eid, need, src, clr):
        placed.append((tuple(row["world"]), row["role"], eid, need, src, row["crownM"] / 2.0, clr * ken))
        out.append(row)

    def scatter(cands_w, n, e, eid, src, pal, rnd, rmin_m, gk, grp, nm0):
        memo, rej = {}, set()

        def acc(w):
            if w in rej: return False
            if w in memo: return True
            v = pal[rnd.randrange(len(pal))]
            row = try_place(w, e, eid, src, v, rnd, rmin_m, gk)
            if row is None:
                rej.add(w); return False
            memo[w] = row
            return True
        seeded = [q[0] for q in placed if q[2] == eid]
        pts, r_, rx_ = L.scatter_take(rnd, cands_w, n, rmin_m, seeded=seeded, accept=acc)
        k0 = sum(1 for q in placed if q[2] == eid)
        for j, w in enumerate(pts):
            row = memo[w]
            row["name"] = "%s_%03d" % (nm0, k0 + j + 1)
            row["group"] = grp
            emit(row, eid, rmin_m, src, float(e.get("clr") or 0.0))
        return len(pts), r_, rx_

    def best_near(tgt_uv, e, eid, src, pal, rnd, need, gk, rmax=3.0):
        r = 0.0
        while r <= rmax + 1e-9:
            for k in (range(32) if r > 0 else [0]):
                a = 2 * math.pi * k / 32
                uv = (tgt_uv[0] + r * math.cos(a), tgt_uv[1] + r * math.sin(a))
                for v in pal:
                    row = try_place(M.W(*uv), e, eid, src, v, rnd, need, gk)
                    if row is not None: return row, r
            r += 0.1
        return None, None

    unread = set()

    # ================= 庭の散布(planting.groups)
    gz = dict((g.name, g) for g in M.gardens)
    graw = dict((g["name"], g) for g in d.get("gardens") or [])
    tw_names = set(t.name for t in M.terraces)
    fukugen = "Fukugen" in tw_names
    bylay = {}
    for ei, e in enumerate(pl["groups"]):
        eid = "庭/%d" % ei
        zn, lay, role = e.get("zone"), e.get("layer"), e.get("role")
        z = gz.get(zn)
        zr = graw.get(zn) or {}
        pal = _variants(e, A, forbid, notes)
        key = "%s／%s" % (zn, lay)
        if not pal:
            band_note.append({"band": key, "layer": lay, "want": e.get("n"), "got": 0, "soft": "⛔ 部材が無い ── 撒かない"}); continue
        rnd, seed = _rnd(d, zn, lay)
        pack = pack0
        sp_m = float(e.get("spacing") or 1.0) * ken
        ovr = e.get("keepoutByLayer") or {}
        skip = e.get("keepoutSkip") or []
        avoid = []
        for a in zr.get("avoid") or []:
            if a.get("where") == "Fukugen の客土" and not fukugen:
                notes.append("⚠ %s.avoid「Fukugen の客土」: 段 Fukugen が指図に無い(外した段)── 避けていない" % zn); continue
            if a.get("box") or a.get("ref") == "sensui.pond":
                avoid.append(a)
        urng = e.get("uRange")

        def gk(uv, role, clr, crR, layer=lay, avoid=avoid, ovr=ovr, skip=skip, e=e, urng=urng):
            for a in avoid:
                if a.get("roles") and role not in a["roles"]: continue
                if a.get("except") and a["except"] in layer: continue
                b = a.get("box")
                if b and b[0] <= uv[0] <= b[2] and b[1] <= uv[1] <= b[3]: return a.get("where") or "置かない帯"
            if urng and not (urng[0] <= uv[0] <= urng[1]): return "uRange の外"
            return S.keep(uv, role, clr, crR, ovr=ovr, skip=skip, pondClr=e.get("pondClr"))
        for k in e:
            if k not in ("zone", "layer", "role", "species", "cert", "n", "clr", "spacing", "tilt", "tiltDir", "groupGap", "groups",
                         "at", "src", "parts", "pondClr", "under", "keepoutByLayer", "keepoutSkip", "uRange", "where",
                         "scaleJitter", "reduced", "scatterPending"):
                unread.add("planting.groups[].%s" % k)
        subs = e.get("groups") or ([{"n": e.get("n"), "at": e.get("at"), "where": e.get("where")}] if e.get("at") else None)
        got_all = 0
        want_all = int(e.get("n") or 0)
        moved = []
        if role == "下草" and e.get("under") is not None:
            # 下草: 同じ庭の木の樹冠の下(under = 一本あたりの上限)
            und = e["under"]
            hosts = [r for r in out if r["zone"] == zn and r["role"] in WOODY
                     and (not isinstance(und, dict) or r["role"] in und)]
            cands, cap = [], {}
            for h in hosts:
                cr = h["crownM"] / 2.0
                hu, hv = h["u"], h["v"]
                st = GSTEP
                rr = cr / ken
                u = hu - rr
                while u <= hu + rr:
                    v = hv - rr
                    while v <= hv + rr:
                        if math.hypot(u - hu, v - hv) <= rr and math.hypot(u - hu, v - hv) >= 0.3:
                            cands.append(M.W(u, v))
                        v += st * 2
                    u += st * 2
            if not hosts:
                notes.append("⚠ %s: 樹冠の下に据える木が同じ庭に無い ── 撒かない" % key)
            n, r_, rx_ = scatter(cands, want_all, e, eid, "庭", pal, rnd, sp_m * pack, gk, key, "%s_%s" % (zn, lay))
            got_all = n
            band_note.append({"band": key, "layer": lay, "role": role, "seed": seed, "want": want_all, "got": n,
                              "rmin": round(sp_m * pack, 3), "rminUsed": round(r_, 3), "relax": rx_,
                              "soft": None if n >= want_all else "⚠ 本数の狙い未達(樹冠の下で硬い制約の内に採りきれない)"})
            continue
        if not subs:
            subs = [{"n": want_all, "where": "庭の区の全体"}]
        for gi, g in enumerate(subs):
            want = int(g.get("n") or 0)
            pk = float(g.get("packRatio") or pack)
            gpal = [v for v in pal if not g.get("size") or v["size"] == g["size"]] or pal
            nm0 = "%s_%s" % (zn, lay)
            if g.get("at"):
                for ai, t in enumerate(g["at"]):
                    row, r = best_near(tuple(t), e, eid, "庭", gpal, rnd, sp_m * pk, gk)
                    if row is None:
                        notes.append("⛔ %s の名指しの点 (%.2f, %.2f): 3間 以内に硬い制約と退避を満たす所が無い ── 撒かない" % (key, t[0], t[1]))
                        continue
                    row["name"] = "%s_at%02d" % (nm0, ai + 1)
                    row["group"] = key
                    row["movedM"] = round(r * ken, 2)
                    row["nameOf"] = g.get("where") or e.get("where") or ""
                    emit(row, eid, sp_m * pk, "庭", float(e.get("clr") or 0.0))
                    got_all += 1
                    if r > 0.01:
                        moved.append(r * ken)
                        notes.append("⚠ %s の名指しの点 (%.2f, %.2f) を %.2fm 寄せた(硬い制約・退避の外へ)" % (key, t[0], t[1], r * ken))
                continue
            cands = []
            bx = g.get("box")
            if bx:
                bx = list(bx)
                if isinstance(bx[3], dict):
                    co = bx[3]
                    sv = next((s for s in d.get("service") or [] if "service." + s.get("name", "") == co.get("clearOf")), None)
                    if sv is not None and co.get("face") == "v0" and co.get("side") == "-v":
                        bx[3] = float(sv["v0"]) - float(co.get("margin") or 0.0)
                    else:
                        notes.append("⛔ %s/%s: 箱の端 %s が解けない ── 撒かない" % (key, g.get("where"), json.dumps(co, ensure_ascii=False)))
                        continue
                u = bx[0]
                while u <= bx[2] + 1e-9:
                    v = bx[1]
                    while v <= bx[3] + 1e-9:
                        cands.append(M.W(u, v))
                        v += GSTEP
                    u += GSTEP
            elif g.get("near"):
                c, rr = g["near"], float(g.get("r") or 1.0)
                u = c[0] - rr
                while u <= c[0] + rr:
                    v = c[1] - rr
                    while v <= c[1] + rr:
                        if math.hypot(u - c[0], v - c[1]) <= rr: cands.append(M.W(u, v))
                        v += GSTEP
                    u += GSTEP
                unread.add("planting.groups[].groups[].arc・arcAbout・pattern(三日月)")
            elif g.get("along"):
                al = g["along"]
                line, lo, hi = None, None, None
                if al.get("route"):
                    rt = next((r for r in S.routes if r[0] == al["route"]), None)
                    if rt:
                        line = rt[1]
                        lo = S.base_ko("roji" if rt[2].get("kind") == "niwa" else "route", role, ovr, rt[2]) + 0.05
                        hi = lo + 1.0
                elif al.get("line") == "sensui.pond.outline" and S.pond:
                    s0, s1 = (al.get("segment") or [0, len(S.pond) - 1])[:2]
                    line = S.pond[s0:s1 + 1]
                    lo = float(S.pond_ko.get(role) or 0.0) + float(S.koAdd.get("pond") or 0.0)
                    hi = float((al.get("offset") or [None, lo + 1.0])[1])
                elif al.get("line") == "sensui.yarimizu":
                    ym = (d.get("sensui") or {}).get("yarimizu") or {}
                    line = [tuple(q) for q in ym.get("pts") or []]
                    lo = float((ym.get("nosuji") or {}).get("w") or 0.0) / 2.0
                    hi = float((al.get("offset") or [None, lo + 1.0])[1])
                if not line or len(line) < 2:
                    notes.append("⛔ %s/%s: along %s が解けない ── 撒かない" % (key, g.get("where"), json.dumps(al, ensure_ascii=False)))
                    continue
                side = al.get("side") or "both"
                zc = None
                if z is not None and z.poly:
                    zc = (sum(q[0] for q in z.poly) / len(z.poly), sum(q[1] for q in z.poly) / len(z.poly))
                for i in range(len(line) - 1):
                    a, b = line[i], line[i + 1]
                    Ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
                    tu, tv = (b[0] - a[0]) / Ln, (b[1] - a[1]) / Ln
                    nu, nv = -tv, tu
                    s = 0.0
                    while s <= Ln:
                        for sg in (1.0, -1.0):
                            off = lo
                            while off <= hi + 1e-9:
                                p = (a[0] + tu * s + nu * off * sg, a[1] + tv * s + nv * off * sg)
                                ok = True
                                if side == "+v": ok = (nv * sg) > 0
                                elif side == "-v": ok = (nv * sg) < 0
                                elif side == "out" and al.get("line") == "sensui.pond.outline":
                                    ok = not L._pip(p, S.pond)
                                elif side in ("in", "out") and zc is not None:
                                    tow = (zc[0] - (a[0] + tu * s)) * nu * sg + (zc[1] - (a[1] + tv * s)) * nv * sg > 0
                                    ok = tow if side == "in" else not tow
                                if ok: cands.append(M.W(*p))
                                off += GSTEP
                        s += GSTEP
                if al.get("atVertex"):
                    unread.add("planting.groups[].groups[].along.atVertex")
            else:
                if z is None:
                    notes.append("⛔ %s: 庭の区 %s が指図に無い ── 撒かない" % (key, zn)); continue
                P = list(z.poly)
                us, vs = [q[0] for q in P], [q[1] for q in P]
                u = min(us)
                while u <= max(us):
                    v = min(vs)
                    while v <= max(vs):
                        if L._pip((u, v), P): cands.append(M.W(u, v))
                        v += GSTEP * 2
                    u += GSTEP * 2
            for k in g:
                if k not in ("n", "where", "src", "box", "at", "fit", "near", "r", "along", "packRatio", "size", "keepClear",
                             "keepout", "row", "pitch"):
                    unread.add("planting.groups[].groups[].%s" % k)
            rmin = sp_m * pk
            if g.get("pitch"):
                rmin = float(g["pitch"][0]) * ken
            n, r_, rx_ = scatter(cands, want, e, eid, "庭", gpal, rnd, rmin, gk, key, nm0)
            # ⭐ 狙いの箱に入りきらない分は、箱の芯から最も近い所(3間 以内)へ置いて ⚠(PlaceBest の型・docs/oki-kata.md §4a)
            mv = []
            if n < want and cands:
                cu = M.UV(*cands[len(cands) // 2]) if not bx else ((bx[0] + bx[2]) / 2.0, (bx[1] + float(bx[3])) / 2.0)
                for _k in range(want - n):
                    mine = [q[0] for q in placed if q[2] == eid]

                    def gk2(uv, role, clr, crR, mine=mine, gk=gk):
                        w9 = M.W(*uv)
                        if any(math.hypot(w9[0] - q[0], w9[1] - q[1]) < 0.5 * rmin for q in mine): return "同じ行の芯々"
                        return gk(uv, role, clr, crR)
                    row, rr = best_near(cu, e, eid, "庭", gpal, rnd, rmin, gk2)
                    if row is None: break
                    row["name"] = "%s_%03d" % (nm0, sum(1 for q in placed if q[2] == eid) + 1)
                    row["group"] = key
                    row["movedM"] = round(rr * ken, 2)
                    row["soft"] = "⚠ 狙いの箱 %s に入らず、箱の芯から %.2fm の所へ置いた" % (g.get("where"), rr * ken)
                    emit(row, eid, rmin, "庭", float(e.get("clr") or 0.0))
                    n += 1
                    mv.append(rr * ken)
            got_all += n
            band_note.append({"band": key, "sub": g.get("where"), "layer": lay, "role": role, "seed": seed, "want": want, "got": n,
                              "candM2": round(len(cands) * (GSTEP * ken) ** 2, 1) if bx else None,
                              "rmin": round(rmin, 3), "rminUsed": round(r_, 3), "relax": rx_,
                              "movedOut": len(mv), "movedMaxM": round(max(mv), 2) if mv else 0.0,
                              "soft": ((("⚠ 芯々を %d 回緩めた" % rx_) if rx_ else None) if not mv else
                                       "⚠ %d 本は箱の外の最も近い所へ置いた(最大 %.2fm)" % (len(mv), max(mv))) if n >= want
                              else "⚠ 本数の狙い未達(硬い制約・退避の内で採りきれない ── 入る本数で建てた)"})
        if e.get("at") and not e.get("groups"):
            band_note.append({"band": key, "layer": lay, "role": role, "seed": seed, "want": want_all, "got": got_all,
                              "moved": len(moved), "movedMaxM": round(max(moved), 2) if moved else 0.0,
                              "soft": None if got_all >= want_all else "⚠ 名指しの点の一部が硬い制約で入らない"})
        bylay[(zn, lay)] = got_all

    # ================= 法面の散布(slopePlanting)
    smp = _slope_samples(M, d, S, notes)
    sa = d.get("slopeArea") or {}
    bands = {}
    for w, uv, t, bn, reg in smp:
        bands.setdefault(bn, []).append((w, t))
    for bn, cs in sorted(bands.items()):
        band_note.append({"band": bn, "kind": "法面の帯", "samplesM2": round(len(cs) * SSTEP * SSTEP, 1)})
    spl = d.get("slopePlanting") or []
    have = set(s.get("band") for s in spl)
    for b in d.get("slopeBands") or []:
        if b["name"] not in have:
            notes.append("⚠ 帯 %s: slopePlanting に行が無い ── 撒かない(dens %s は行の n に書き起こされていない)"
                         % (b["name"], json.dumps(b.get("dens"), ensure_ascii=False)))
    sp_layers = {}
    for si, e in enumerate(spl):
        eid = "法面/%d" % si
        e = dict(e)
        e.setdefault("zone", e.get("band"))
        bn, lay = e["band"], e["layer"]
        sp_layers[lay] = e
        pal = _variants(e, A, forbid, notes)
        rnd, seed = _rnd(d, bn, lay)
        want = int(e.get("n") or 0)
        if not pal:
            band_note.append({"band": bn, "layer": lay, "want": want, "got": 0, "soft": "⛔ 部材が無い"}); continue
        tr = e.get("tRange")
        cands = [w for w, t in bands.get(bn, []) if not tr or tr[0] <= t <= tr[1]]
        if not bands.get(bn):
            notes.append("⛔ 法面 %s/%s: 帯 %s の標本が無い(slopeArea で帯が解けない)── 撒かない" % (bn, lay, bn))
        for k in ("placement", "emergent", "clump", "clumpGap", "borderClump", "innerFrac", "innerOffset", "countBy"):
            if e.get(k) is not None and not (k == "placement" and e[k] == "scatter"):
                unread.add("slopePlanting[].%s" % (k if k != "placement" else "placement=" + str(e[k])))

        def gk(uv, role, clr, crR):
            return S.keep(uv, role, clr, crR)
        rmin = float(e.get("spacing") or 1.0) * ken * pack0
        n, r_, rx_ = scatter(cands, want, e, eid, "法面", pal, rnd, rmin, gk, "法面 %s" % bn, "%s_%s" % (bn.split(" ")[0], lay))
        band_note.append({"band": bn, "layer": lay, "role": e["role"], "seed": seed, "want": want, "got": n,
                          "candM2": round(len(cands) * SSTEP * SSTEP, 1), "rmin": round(rmin, 3), "rminUsed": round(r_, 3),
                          "relax": rx_, "soft": (("⚠ 芯々を %d 回緩めた" % rx_) if rx_ else None) if n >= want
                          else "⚠ 本数の狙い未達(帯の中で硬い制約・退避の内に採りきれない)"})

    # ================= 穴埋め(slopePlantingZones)
    for zi, zz in enumerate(d.get("slopePlantingZones") or []):
        if not zz.get("n"):
            notes.append("帯 %s: 本数 n の無い区(視点 %s・庭 %s の範囲)── 撒く行ではない" % (zz["name"], zz.get("viewpoint"), zz.get("garden")))
            continue
        base = sp_layers.get(zz.get("layer"))
        e = dict(base or {})
        e.update({k: v for k, v in zz.items() if k in ("parts", "layer", "n")})
        e["zone"] = zz["name"]
        if base is None and not zz.get("parts"):
            notes.append("⛔ 穴 %s: 層 %s が slopePlanting に無く部材も無い ── 撒かない" % (zz["name"], zz.get("layer"))); continue
        e.setdefault("role", "高木" if "高木" in str(zz.get("layer")) else "低木")
        e.setdefault("band", zz["name"])
        pal = _variants(e, A, forbid, notes)
        rnd, seed = _rnd(d, zz["name"], e["layer"])
        cands = []
        u = zz["uRange"][0]
        while u <= zz["uRange"][1]:
            v = zz["vRange"][0]
            while v <= zz["vRange"][1]:
                cands.append(M.W(u, v))
                v += GSTEP * 2
            u += GSTEP * 2

        def gk(uv, role, clr, crR):
            return S.keep(uv, role, clr, crR)
        rmin = float(e.get("spacing") or 1.0) * ken * pack0
        n, r_, rx_ = scatter(cands, int(zz["n"]), e, "穴/%d" % zi, "法面", pal, rnd, rmin, gk, "穴 %s" % zz["name"], "穴%d_%s" % (zi, e["layer"]))
        band_note.append({"band": zz["name"], "layer": e["layer"], "role": e["role"], "seed": seed, "want": int(zz["n"]), "got": n,
                          "rminUsed": round(r_, 3), "relax": rx_,
                          "soft": None if n >= int(zz["n"]) else "⚠ 本数の狙い未達(穴の箱の中で硬い制約の内に採りきれない)"})

    # ================= 名乗り
    if unread:
        notes.append("⚠ 読んでいない欄(撒き方の細部 ── 焼きは scatter で一様に撒いた・本数と芯々と退避は守る): " + "・".join(sorted(unread)))
    notes.append("⚠ slopeArea.subtractTerraces / subtractGardens は今の段(terraces)と庭の区(planting.groups の zone)で差し引いた"
                 "%s" % ("" if fukugen else " ── 段 Fukugen は外した段で指図に無いので差し引いていない(避ける客土の平場も無い)"))
    notes.append("⚠ plantRule.toomiMado(V9 から −u ±15° の窓に高木を置かない)は窓の扇を解く手が無い ── 焼いていない(林方の検分で検める)")
    notes.append("⚠ plantRule.speciesMix(落葉高木 2〜3割・Keyaki/Mukunoki/Enoki)は slopePlanting の parts に落葉高木の行が無い ── 混ぜていない")
    # 検め(層をまたぐ幹の芯々)
    xl, mn = [], None
    for i, a in enumerate(out):
        if a["role"] not in WOODY: continue
        for b in out[i + 1:]:
            if b["role"] not in WOODY or a["layer"] == b["layer"]: continue
            dm = math.hypot(a["world"][0] - b["world"][0], a["world"][1] - b["world"][1])
            mn = dm if mn is None else min(mn, dm)
            if dm < RX - 1e-9: xl.append((a["name"], b["name"]))
    lays = {}
    for r in out:
        lays[r["role"]] = lays.get(r["role"], 0) + 1
    return {"points": out, "bands": band_note, "notes": notes, "counts": lays,
            "walls": [{"name": w["name"], "kind": w["kind"], "segs": len(w["segs"]), "halfM": round(w["half"], 3),
                       "halfFrom": w["halfFrom"], "facing": w.get("facing", True)} for w in S.lines],
            "crossLayer": {"minM": RX, "pairs": len(xl), "worst": xl[:5], "closestM": round(mn, 3) if mn is not None else None,
                           "_": "層の違う幹の芯々(高木・中木・低木)── 下草は数えない"},
            "seedRule": pr.get("seed"),
            "_": "**撒いた木の点**(庭方・林方の設計 `planting.groups` / `slopePlanting` / `slopePlantingZones` から焼いた)。⛔ 実装側で"
                 "撒き直さない。種は `plantRule.seed`(zone + '/' + layer)から決定論的に作る。world は世界 xz・u,v は主郭グリッドの間"}


# ================================================================ 法面の標本(旧生成器 slope_samples の写し)
def _slope_samples(M, d, S, notes):
    """西の崖・南西の谷の法面を 1m 刻みで走査 → [(world, uv, t, 帯名, 域名)]。t = (法肩の標高 − 地盤)/(法肩 − 法尻)。
    ⭐ 帯は域ごとに引く・`minAbs` の押し上げ・`shallowSpans` の差し替え・`bandJitter` は旧生成器と同じ読み。
    ⭐ 段(terraces)と庭の区(planting.groups の zone)を差し引く(`subtractTerraces` / `subtractGardens`)。"""
    sa = d.get("slopeArea") or {}
    if not sa.get("crest"):
        notes.append("⛔ slopeArea.crest が無い ── 法面を撒かない"); return []
    CR = [tuple(p) for p in sa["crest"]]
    P = [tuple(q) for q in d["polygon"]]
    bands = d.get("slopeBands") or []
    regs = sa.get("regions") or []
    # 庭が自分で撒く区だけを差し引く(旧生成器 _garden_scatter_zones と同じ ── slopePlantingZones[].garden に挙がるか ownScatter)。
    #   ⛔ 「planting を持つ庭」全部を引くと台地の上の西庭まで入り、法肩の帯が消える
    zones_g = set(e.get("zone") for e in d["planting"]["groups"])
    named = set(z.get("garden") for z in d.get("slopePlantingZones") or [] if z.get("garden"))
    own = set(g["name"] for g in d.get("gardens") or [] if g.get("ownScatter"))
    gpolys = [list(g.poly) for g in M.gardens if g.name in zones_g and g.name in (named | own)] if sa.get("subtractGardens") else []
    tpolys = [list(t.poly) for t in M.terraces] if sa.get("subtractTerraces") else []
    if sa.get("levels"):
        notes.append("⚠ slopeArea.levels(標高で切る帯)は読んでいない")
    bj = sa.get("bandJitter") or {}

    def jit(x, z):
        amp = float(bj.get("amp") or 0.0)
        if amp <= 0: return 0.0
        cr = bj.get("corr") or [8.0, 12.0]
        Lc = (float(cr[0]) + float(cr[1])) / 2.0
        import zlib

        def nz(i, j):
            return (zlib.crc32(("bj/%d/%d" % (i, j)).encode("utf-8")) % 20001) / 10000.0 - 1.0
        fx, fz = x / Lc, z / Lc
        i0, j0 = math.floor(fx), math.floor(fz)
        tx, tz = fx - i0, fz - j0
        sx, sz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
        a = nz(i0, j0) * (1 - sx) + nz(i0 + 1, j0) * sx
        b = nz(i0, j0 + 1) * (1 - sx) + nz(i0 + 1, j0 + 1) * sx
        return amp * (a * (1 - sz) + b * sz)

    def bjv(t, dl):
        return float(t) + dl if any(abs(float(e) - float(t)) < 1e-9 for e in bj.get("edges") or []) else float(t)

    def crest_near(uv):
        best = (1e18, None, 0)
        for i in range(len(CR) - 1):
            a, b = CR[i], CR[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            tt = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((uv[0] - a[0]) * dx + (uv[1] - a[1]) * dy) / L2))
            q = (a[0] + dx * tt, a[1] + dy * tt)
            dd = math.hypot(uv[0] - q[0], uv[1] - q[1])
            if dd < best[0]: best = (dd, q, i)
        return best

    def near_edges(w, idx):
        best = (1e18, -1, None)
        for i in idx:
            a, b = P[i], P[(i + 1) % len(P)]
            dd = _sd(w, a, b)
            if dd < best[0]:
                dx, dy = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dy * dy
                tt = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((w[0] - a[0]) * dx + (w[1] - a[1]) * dy) / L2))
                best = (dd, i, (a[0] + dx * tt, a[1] + dy * tt))
        return best

    def region_of(i):
        for r in regs:
            if r["crestSeg"][0] <= i <= r["crestSeg"][1]: return r
        return None
    # ⚠ `slopeArea.regions[].toe` / `toeEdges` の辺の番号は今の区画(24 辺)と合わない(域W の toe 6〜11 は南の谷の辺・
    #   shallowSpans の辺20 はどの toe にも無い)── 法尻の辺は**法肩の外にある区画の辺**を域ごとに幾何で拾い直した(U・差し戻し)
    toe_geo = {}
    for i in range(len(P)):
        a9, b9 = P[i], P[(i + 1) % len(P)]
        m9 = M.UV((a9[0] + b9[0]) / 2.0, (a9[1] + b9[1]) / 2.0)
        _dd, _q, ci9 = crest_near(m9)
        ca, cb = CR[ci9], CR[ci9 + 1]
        if math.hypot(_q[0] - ca[0], _q[1] - ca[1]) < 1e-6 and ci9 == 0 or \
                math.hypot(_q[0] - cb[0], _q[1] - cb[1]) < 1e-6 and ci9 == len(CR) - 2:
            continue                      # 法肩の折れ線の両端の先(法肩の外へ投影が落ちない辺)は法尻にしない
        du9, dv9 = cb[0] - ca[0], cb[1] - ca[1]
        L9 = math.hypot(du9, dv9) or 1.0
        if (du9 / L9) * (m9[1] - ca[1]) - (dv9 / L9) * (m9[0] - ca[0]) > 0:
            rg9 = region_of(ci9)
            toe_geo.setdefault((rg9 or {}).get("name"), set()).add(i)
    decl = dict((r["name"], sorted(r.get("toe") or [])) for r in regs)
    notes.append("⚠ 法尻の辺: 指図 slopeArea.regions[].toe %s・toeEdges %s は今の区画の辺の番号と合わない ── 法肩の外の辺を幾何で拾い直した %s(U)"
                 % (json.dumps(decl, ensure_ascii=False), sa.get("toeEdges"),
                    json.dumps(dict((k, sorted(v)) for k, v in toe_geo.items()), ensure_ascii=False)))
    dem = M.dem
    out = []
    xs, zs = [q[0] for q in P], [q[1] for q in P]
    x = math.floor(min(xs)) + 0.5
    allidx = list(range(len(P)))
    while x <= max(xs):
        z = math.floor(min(zs)) + 0.5
        while z <= max(zs):
            w = (x, z)
            z += SSTEP
            if not L._pip(w, P): continue
            uv = M.UV(*w)
            dc, qc, ci = crest_near(uv)
            a, b = CR[ci], CR[ci + 1]
            du, dv = b[0] - a[0], b[1] - a[1]
            Ln = math.hypot(du, dv) or 1.0
            if not ((du / Ln) * (uv[1] - a[1]) - (dv / Ln) * (uv[0] - a[0]) > 0): continue
            if any(L._pip(uv, T) for T in tpolys) or any(L._pip(uv, G) for G in gpolys): continue
            rg = region_of(ci)
            toes = toe_geo.get((rg or {}).get("name"), set())
            ne = near_edges(w, allidx)[1]
            if ne not in toes: continue
            yc = dem.at(*M.W(*qc))
            dt, _i, qt = near_edges(w, toes)
            yt = dem.at(qt[0], qt[1])
            y = dem.at(x, w[1])
            if None in (yc, yt, y): continue
            H = max(yc - yt, 0.5)
            t = max(0.0, min(1.0, (yc - y) / H))
            reg = (rg or {}).get("name")
            mine = [bb for bb in bands if bb.get("region", reg) == reg] or bands
            bn = mine[-1]["name"]
            dl = jit(x, w[1])
            for bb in mine:
                if bjv(bb["from"], dl) <= t < bjv(bb["to"], dl):
                    bn = bb["name"]; break
            mb = next((bb for bb in mine if bb.get("minAbs")), None)
            if mb is not None:
                b0 = next((bb for bb in mine if bb["name"] == bn), None)
                use = dl if (b0 is not None and abs(bjv(b0["to"], dl) - b0["to"]) > 1e-12) else 0.0
                if (1.0 - t) * H < float(mb["minAbs"]) - use * H:
                    bn = mb["name"]
            for sp in sa.get("shallowSpans") or []:
                if ne == sp["edge"] and bn == sp["replace"]:
                    bn = sp["with"]; break
            out.append((w, uv, t, bn, reg))
        x += SSTEP
    return out
