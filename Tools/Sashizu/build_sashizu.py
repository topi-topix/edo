#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指図の共通の生成器 — 全邸で一本(2026-09-20 施主指示・EDO-0266)。

    python3 Tools/Sashizu/build_sashizu.py <邸>            # 図 4 枚 + 検査 23 本 → docs/Sashizu/<邸>_sashizu.html
    python3 Tools/Sashizu/build_sashizu.py <邸> --deep     # 共通の壊し試しも回して記録する(数分)

読むのは 5 邸に共通の欄だけ: polygon / grid / const / terraces / terraceWalls / planes / munes / links /
service / wells / runs / gate・komon・gates / kaidans / routes / gardens / sections / program。
邸ごとに綴りが違う所は「読み手」(Model)が吸収し、読めなかった欄は図の末尾に名指しで刷る
(規則19: 読めていない値は「未検査」であって「合格」ではない)。

⛔ 設計値をここに書かない。⛔ 実装(C#)を読まない。⛔ 邸の名前で分岐しない — 欄の形で分岐する。
検査の名簿と札は docs/Sashizu/check_triage.json(共通版に残す 23 の意図 C01〜C23)。
"""
import copy
import datetime
import itertools
import json
import math
import statistics
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sashizu_lib as L  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DOC = os.path.join(ROOT, "docs", "Sashizu")
KAN = ["其一", "其二", "其三", "其四", "其五", "其六", "其七", "其八", "其九", "其十", "其十一", "其十二"]
EST_JA = {"okabe": "岡部", "doi": "土井", "matsudaira_dewa": "松平", "kyogoku_bitchu": "京極", "sanno": "山王"}
TOL = 1e-6


# ================================================================ 幾何
def pip(p, x, z):
    c = False
    n = len(p)
    for i in range(n):
        (ax, az), (bx, bz) = p[i], p[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (bx - ax) * (z - az) / (bz - az):
            c = not c
    return c


def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
                   for i in range(len(p)))) / 2.0


def centroid(p):
    return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def edge_dist(p, poly):
    return min(seg_dist(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def segs_cross(a, b, c, d):
    d1, d2 = _cross(c, d, a), _cross(c, d, b)
    d3, d4 = _cross(a, b, c), _cross(a, b, d)
    return ((d1 > TOL and d2 < -TOL) or (d1 < -TOL and d2 > TOL)) and \
           ((d3 > TOL and d4 < -TOL) or (d3 < -TOL and d4 > TOL))


def polys_overlap(A, B, pad=0.02):
    """真の重なり(接するは可)。辺が交差するか、一方の頂点(少し内側)が他方の中にある。"""
    for i in range(len(A)):
        for j in range(len(B)):
            if segs_cross(A[i], A[(i + 1) % len(A)], B[j], B[(j + 1) % len(B)]):
                return True
    ca, cb = centroid(A), centroid(B)
    for q in A:
        q2 = (q[0] + (ca[0] - q[0]) * pad, q[1] + (ca[1] - q[1]) * pad)
        if pip(B, *q2) and edge_dist(q2, B) > pad:
            return True
    for q in B:
        q2 = (q[0] + (cb[0] - q[0]) * pad, q[1] + (cb[1] - q[1]) * pad)
        if pip(A, *q2) and edge_dist(q2, A) > pad:
            return True
    return False


def poly_inside(A, B, tol=0.01):
    """A が B の中に完全に入るか。"""
    return all(pip(B, *q) or edge_dist(q, B) <= tol for q in A)


def polys_dist(A, B):
    if polys_overlap(A, B):
        return 0.0
    return min(min(edge_dist(q, B) for q in A), min(edge_dist(q, A) for q in B))


def rect(u0, v0, u1, v1):
    u0, u1 = min(u0, u1), max(u0, u1)
    v0, v1 = min(v0, v1), max(v0, v1)
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def bbox(p):
    return (min(q[0] for q in p), min(q[1] for q in p), max(q[0] for q in p), max(q[1] for q in p))


def shrink(p, d):
    """多角形を重心へ向けて d だけ縮める(接するだけの物を重なりと数えないため)。"""
    c = centroid(p)
    out = []
    for q in p:
        dx, dy = c[0] - q[0], c[1] - q[1]
        n = math.hypot(dx, dy) or 1e-9
        k = min(d, n * 0.45)
        out.append((q[0] + dx / n * k, q[1] + dy / n * k))
    return out


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


# ================================================================ 地盤
class DEM(object):
    def __init__(self, path):
        self.path = path
        S = json.load(open(path, encoding="utf-8"))
        self.x0, self.z0, self.step, self.nx, self.nz, self.h = S["x0"], S["z0"], S["step"], S["nx"], S["nz"], S["h"]
        self.raw = S

    def at(self, x, z):
        fx = (x - self.x0) / self.step
        fz = (z - self.z0) / self.step
        i0, j0 = int(math.floor(fx)), int(math.floor(fz))
        if not (0 <= i0 < self.nx - 1 and 0 <= j0 < self.nz - 1):
            return None
        tx, tz = fx - i0, fz - j0
        try:
            a, b = self.h[j0][i0], self.h[j0][i0 + 1]
            c, e = self.h[j0 + 1][i0], self.h[j0 + 1][i0 + 1]
        except (IndexError, TypeError):
            return None
        if None in (a, b, c, e):
            return None
        return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + e * tx) * tz


# ================================================================ 読み手(正規化)
class Obj(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        return "Obj(%s)" % self.__dict__.get("name")


class Model(object):
    """邸の json を、共通の形へ読む。読めなかった欄は self.notes に残す(図の末尾に刷る)。"""

    def __init__(self, est, d=None):
        self.est = est
        self.notes = []
        self.d = d if d is not None else json.load(open(os.path.join(DOC, est + "_sashizu.json"), encoding="utf-8"))
        d = self.d
        c = d.get("const", {})
        self.KEN = c.get("ken", 1.818)
        self.TSUBO = c.get("tsubo") or 3.305785
        self.const = c
        # グリッド
        gname = "shukaku" if "shukaku" in d.get("grid", {}) else \
            next((k for k, v in d.get("grid", {}).items() if isinstance(v, dict) and "x0" in v), None)
        if gname is None:
            raise SystemExit("⛔ grid が無い: %s" % est)
        self.gname = gname
        dd = dict(d)
        dd["const"] = dict(c, ken=self.KEN)
        self.gr = L.RGrid(dd, gname)
        self.poly = [tuple(p) for p in d["polygon"]]
        self.poly_uv = [self.gr.L(x, z) for x, z in self.poly]
        self.area_m2 = area(self.poly)
        self.bb_uv = bbox(self.poly_uv)
        # 地盤: 江戸期復元(世界格子) > 邸の dem > 正本 base_dem
        self.dem = None
        for fn in (est + "_edo_world.json", est + "_dem.json", "base_dem.json"):
            fp = os.path.join(DOC, fn)
            if os.path.exists(fp):
                try:
                    self.dem = DEM(fp)
                    self.dem_name = fn
                    break
                except Exception as ex:  # noqa: BLE001
                    self.notes.append("地盤 %s が読めない: %s" % (fn, ex))
        if self.dem is None:
            raise SystemExit("⛔ 地盤が無い: %s" % est)
        self.base = DEM(os.path.join(DOC, "base_dem.json")) if os.path.exists(os.path.join(DOC, "base_dem.json")) else None
        self._pcache = {}
        self._read_all()

    # ---------------- 補助
    def W(self, u, v):
        return self.gr.W(u, v)

    def UV(self, x, z):
        return self.gr.L(x, z)

    def in_parcel(self, u, v):
        k = (round(u, 3), round(v, 3))
        r = self._pcache.get(k)
        if r is None:
            r = pip(self.poly_uv, u, v)
            self._pcache[k] = r
        return r

    def nat(self, u, v):
        x, z = self.W(u, v)
        return self.dem.at(x, z)

    def design_y(self, u, v):
        if not self.in_parcel(u, v):
            return None
        best = None
        for t in self.terraces:
            if pip(t.poly, u, v):
                best = t.y if best is None else max(best, t.y)
        return best

    def terrace_at(self, u, v):
        best = None
        for t in self.terraces:
            if pip(t.poly, u, v) and (best is None or t.y > best.y):
                best = t
        return best

    def graded_y(self, u, v, nat):
        """造成後の地盤。段の中は段の高さ、外は法面で摺り付ける(lib の土井式を優先)。"""
        if nat is None:
            return None
        if not self.in_parcel(u, v):
            return nat
        try:
            return L.graded_y(self._libd, u, v, nat, lambda dd, uu, vv: self.in_parcel(uu, vv))
        except Exception:  # noqa: BLE001
            self._lib_fail += 1
            y = self.design_y(u, v)
            if y is not None:
                return y
            # 素朴な法面: 最も近い段の縁から 1:batter で摺り付ける
            best = None
            for t in self.terraces:
                dm = edge_dist((u, v), t.poly) * self.KEN
                b = self.const.get("batterFill", 1.5) if t.y > nat else self.const.get("batterCut", 1.0)
                yy = t.y - (t.y - nat) * min(1.0, dm / max(1e-6, abs(t.y - nat) * b))
                if best is None or abs(yy - nat) > abs(best - nat):
                    best = yy
            return best if best is not None else nat

    def edge_pt(self, e, s):
        P = self.poly
        a, b = P[e], P[(e + 1) % len(P)]
        Lm = math.hypot(b[0] - a[0], b[1] - a[1])
        t = s / Lm
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def edge_len(self, e):
        P = self.poly
        a, b = P[e], P[(e + 1) % len(P)]
        return math.hypot(b[0] - a[0], b[1] - a[1])

    def inward(self, e):
        P = self.poly
        n = len(P)
        a, b = P[e], P[(e + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        Lm = math.hypot(dx, dy) or 1e-9
        area2 = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
        sg = 1.0 if area2 > 0 else -1.0
        return (-dy / Lm * sg, dx / Lm * sg)

    def _uvpoly(self, o):
        """矩形/回転矩形/多角形のどれでも uv 多角形へ。読めなければ None。"""
        if not isinstance(o, dict):
            return None
        if "poly" in o and isinstance(o["poly"], list) and o["poly"] and isinstance(o["poly"][0], (list, tuple)):
            return [tuple(q) for q in o["poly"]]
        if "uv" in o and isinstance(o["uv"], list) and o["uv"] and isinstance(o["uv"][0], (list, tuple)):
            return [tuple(q) for q in o["uv"]]
        if "yaw" in o and "uc" in o:
            return [tuple(q) for q in L.obb_pts(o)]
        if all(k in o for k in ("u0", "v0", "u1", "v1")):
            return rect(o["u0"], o["v0"], o["u1"], o["v1"])
        if all(k in o for k in ("u0", "v0", "du", "dv")):
            return rect(o["u0"], o["v0"], o["u0"] + o["du"], o["v0"] + o["dv"])
        if all(k in o for k in ("u0", "u1", "vc", "w")):
            hw = o["w"] / 2.0
            return rect(o["u0"], o["vc"] - hw, o["u1"], o["vc"] + hw)
        if "pts" in o and o.get("kind") in (None,) and isinstance(o["pts"], list) and len(o["pts"]) >= 3:
            return [tuple(q) for q in o["pts"]]
        return None

    def _label(self, o, fallback):
        return o.get("label") or o.get("ja") or o.get("name") or fallback

    # ---------------- 読み込み
    def _read_all(self):
        d = self.d
        K = self.KEN
        # 段
        self.terraces = []
        for t in d.get("terraces", []):
            p = self._uvpoly(t)
            if p is None or "y" not in t:
                self.notes.append("terraces[%s] の形か y が読めない" % t.get("name"))
                continue
            self.terraces.append(Obj(name=t["name"], label=self._label(t, t["name"]), poly=p, y=t["y"],
                                     clip=bool(t.get("clip")), raw=t))
        # 面(planes) — 段の名簿と y の突き合わせに使う
        self.planes = d.get("planes", [])
        # 棟・廊下・附属屋・井戸
        self.munes, self.links, self.service, self.wells = [], [], [], []
        for m in (d.get("munes") or d.get("mune") or []):
            p = self._uvpoly(m)
            if p is None:
                self.notes.append("munes[%s] の形が読めない" % m.get("name"))
                continue
            y = m.get("y")
            self.munes.append(Obj(name=m["name"], label=self._label(m, m["name"]), poly=p, y=y,
                                  zone=m.get("zone") or m.get("yaku") or "", rooms=[], raw=m))
            for r in m.get("rooms", []) or []:
                rp = self._uvpoly(r)
                if rp is not None:
                    self.munes[-1].rooms.append(Obj(name=r.get("name", "?"), poly=rp, raw=r))
        for l in d.get("links", []) or []:
            p = self._uvpoly(l)
            if p is None and "from" in l and "to" in l:
                w = (l.get("w") or 1.0) / (1.0 if l.get("wUnit") == "間" else K)
                a, b = l["from"], l["to"]
                du, dv = b[0] - a[0], b[1] - a[1]
                n = math.hypot(du, dv) or 1e-9
                ox, oy = -dv / n * w / 2, du / n * w / 2
                p = [(a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), (b[0] - ox, b[1] - oy), (a[0] - ox, a[1] - oy)]
            if p is None:
                self.notes.append("links[%s] の形が読めない" % l.get("name"))
                continue
            self.links.append(Obj(name=l["name"], label=self._label(l, l["name"]), poly=p, y=l.get("y"), raw=l))
        for s in d.get("service", []) or []:
            p = self._uvpoly(s)
            if p is None:
                self.notes.append("service[%s] の形が読めない" % s.get("name"))
                continue
            self.service.append(Obj(name=s["name"], label=self._label(s, s["name"]), poly=p, y=s.get("y"), raw=s))
        for w in d.get("wells", []) or []:
            if "u" in w and "v" in w:
                self.wells.append(Obj(name=w["name"], label=self._label(w, w["name"]), uv=(w["u"], w["v"]), raw=w))
        # 外周 run
        self.runs = []
        mine_ja = EST_JA.get(self.est, "")
        edge_owner = d.get("edgeOwner") or {}
        edges = {e.get("i", i): e for i, e in enumerate(d.get("edges", []) or [])} if isinstance(d.get("edges"), list) else {}
        fences = [dict(f, kind=f.get("kind") or "木柵") for f in (d.get("fences") or []) if isinstance(f, dict)]
        for r in (d.get("runs", []) or []) + fences:          # 木柵(fences)も囲いの一種として同じ帯で読む
            kind = r.get("kind", "")
            depth = self.const.get("nagayaD") if kind == "Nagaya" else (self.const.get("dobeiT") or 0.45)
            depth = 0.2 if r in fences else (depth or 4.5)
            if "edge" in r and "s0" in r and "s1" in r:
                e = r["edge"]
                a, b = self.edge_pt(e, r["s0"]), self.edge_pt(e, r["s1"])
                mine = True
                if r.get("build") is False:
                    mine = False
                if str(e) in edge_owner and edge_owner[str(e)] != mine_ja:
                    mine = False
                # ⚠ edges[].neighbor は「向かいに何があるか」の覚えで持ち主ではない(岡部は街路にも書く)。
                #   持ち主は edges[].kind の「当家は建てない」で読む
                if e in edges and "建てない" in str(edges[e].get("kind", "")):
                    mine = False
                if r.get("owner") and r.get("owner") != self.est.split("_")[0]:
                    mine = False
                self.runs.append(Obj(name=r["name"], kind=kind, a=a, b=b, edge=e, s0=r["s0"], s1=r["s1"],
                                     seat=r.get("seat"), depth=depth, mine=mine, nrm=self.inward(e), raw=r))
            elif isinstance(r.get("a"), (list, tuple)) and isinstance(r.get("b"), (list, tuple)):
                a, b = self.W(*r["a"]), self.W(*r["b"])
                self.runs.append(Obj(name=r["name"], kind=kind, a=a, b=b, edge=None, s0=None, s1=None,
                                     seat=r.get("seat"), depth=depth, mine=True, nrm=None, raw=r))
            else:
                self.notes.append("runs[%s] の位置が読めない" % r.get("name"))
        # 門
        self.gates = []

        def gate_obj(g, name, kind_default):
            if not isinstance(g, dict):
                return None
            pos = g.get("pos") or g.get("world")
            e = g.get("edge")
            if pos is None and e is not None and "s" in g:
                pos = self.edge_pt(e, g["s"])
            if pos is None and "u" in g and "v" in g:
                pos = self.W(g["u"], g["v"])
            if pos is None and "uv" in g:
                pos = self.W(*g["uv"])
            if pos is None:
                self.notes.append("門 %s の位置が読めない" % name)
                return None
            plan = g.get("plan") or {}
            w = plan.get("monW") or g.get("w") or (plan.get("du", 0) * K if plan.get("du") else None)
            return Obj(name=name, kind=g.get("kind", kind_default), pos=tuple(pos), w=w, sill=g.get("sill"),
                       edge=e, s=g.get("s"), plan=plan, raw=g)

        g = d.get("gate")
        if isinstance(g, dict):
            o = gate_obj(g, g.get("name", "表門"), "表門")
            if o:
                o.main = True
                self.gates.append(o)
        km = d.get("komon")
        for g2 in (km if isinstance(km, list) else ([km] if isinstance(km, dict) else [])):
            o = gate_obj(g2, g2.get("name", "通用門"), "通用門")
            if o:
                o.main = False
                self.gates.append(o)
        for g3 in d.get("gates", []) or []:
            o = gate_obj(g3, g3.get("name", "門"), "門")
            if o:
                o.main = bool(g3.get("main")) or not self.gates
                self.gates.append(o)
        # 石段
        self.kaidans = []
        walls = {w.get("name"): w for w in d.get("terraceWalls", []) or []}
        for k in d.get("kaidans", []) or []:
            p = None
            steps = k.get("steps")
            drop = k.get("drop")
            y0, y1 = k.get("y0", k.get("yBot")), k.get("y1", k.get("yTop"))
            if drop is None and y0 is not None and y1 is not None:
                drop = abs(y1 - y0)
            run = k.get("run") or k.get("planeLen")
            w = k.get("w") or (k.get("wKen", 0) * K if k.get("wKen") else None)
            wk = (w or 1.8) / K
            if isinstance(k.get("a"), (list, tuple)) and isinstance(k.get("b"), (list, tuple)):   # 山王: a→b(uv)・幅 wKen
                a, b = k["a"], k["b"]
                du, dv = b[0] - a[0], b[1] - a[1]
                n = math.hypot(du, dv) or 1e-9
                ox, oy = -dv / n * wk / 2, du / n * wk / 2
                p = [(a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), (b[0] - ox, b[1] - oy), (a[0] - ox, a[1] - oy)]
                run = run or n * K
            elif "pos" in k and "dir" in k and run:            # 松平: pos から dir へ run
                (u, v), dr = k["pos"], k["dir"]
                rk = run / K
                if dr[1] == "v":
                    v1 = v + rk * (1 if dr[0] == "+" else -1)
                    p = rect(u - wk / 2, v, u + wk / 2, v1)
                else:
                    u1 = u + rk * (1 if dr[0] == "+" else -1)
                    p = rect(u, v - wk / 2, u1, v + wk / 2)
            elif "v0" in k and "v1" in k and "gapU" in k:      # 岡部: v0..v1・u=gapU
                p = rect(k["gapU"] - wk / 2, k["v0"], k["gapU"] + wk / 2, k["v1"])
            elif "u0" in k and "u1" in k and "vc" in k:        # 京極
                p = rect(k["u0"], k["vc"] - wk / 2, k["u1"], k["vc"] + wk / 2)
            elif k.get("atWall") in walls and run:             # 土井: 壁の線から低い側へ run
                wl = walls[k["atWall"]]
                (au, av), (bu, bv) = wl["a"], wl["b"]
                rk = run / K
                # 壁のどちら側へ下るかは壁の欄が持たない — 両側へ走りぶん取り、図と検査はそれで読む
                if abs(au - bu) < 1e-9:                        # u=const の壁
                    gv = k.get("gapV", (av + bv) / 2)
                    p = rect(au - rk, gv - wk / 2, au + rk, gv + wk / 2)
                else:
                    gu = k.get("gapU", (au + bu) / 2)
                    p = rect(gu - wk / 2, av - rk, gu + wk / 2, av + rk)
                if y1 is None:
                    y1 = wl.get("coping")
                    y0 = (y1 - drop) if (y1 is not None and drop is not None) else None
            if p is None:
                self.notes.append("kaidans[%s] の位置が読めない(段数と落差だけ検める)" % k.get("name"))
            self.kaidans.append(Obj(name=k["name"], label=self._label(k, k["name"]), poly=p, steps=steps, drop=drop,
                                    y0=y0, y1=y1, keri=k.get("keri") or k.get("keriActual"),
                                    fumi=k.get("fumi") or k.get("fumiActual"), run=run, w=w, raw=k))
        # 動線
        self.routes = []
        for r in d.get("routes", []) or []:
            pts = r.get("pts")
            if not pts:
                self.notes.append("routes[%s] に pts が無い" % r.get("name"))
                continue
            pts = [q[:2] for q in pts if isinstance(q, (list, tuple)) and len(q) >= 2
                   and all(isinstance(x, (int, float)) for x in q[:2])]
            if len(pts) < 2:
                self.notes.append("routes[%s] の pts が数の対でない" % r.get("name"))
                continue
            if r.get("world"):
                pw = [tuple(q) for q in pts]
            else:
                pw = [self.W(*q) for q in pts]
            self.routes.append(Obj(name=r["name"], kind=r.get("kind") or r.get("color") or "", label=self._label(r, r["name"]),
                                   pts=pw, uv=[self.UV(*q) for q in pw], raw=r))
        # 庭
        self.gardens = []
        for g in d.get("gardens", []) or []:
            p = self._uvpoly(g)
            if p is None:
                continue
            explicit = bool(g.get("poly") or g.get("uv"))
            self.gardens.append(Obj(name=g["name"], kind=g.get("kind", ""), label=self._label(g, g["name"]), poly=p,
                                    explicit=explicit, raw=g))
        # 水(汀線)
        self.water = []
        for g in d.get("gardens", []) or []:
            mg = g.get("migiwa") if isinstance(g, dict) else None
            if isinstance(mg, dict) and mg.get("pts"):
                self.water.append(Obj(name=g["name"], label=self._label(g, g["name"]), pts=[tuple(q) for q in mg["pts"]],
                                      y=mg.get("waterY"), host=g["name"]))
        sw = d.get("sensui")
        if isinstance(sw, dict):
            pond = sw.get("pond") or sw
            pts = pond.get("migiwa") or pond.get("pts") or pond.get("shore") or pond.get("outline")
            if isinstance(pts, dict):
                pts = pts.get("pts")
            if pts and isinstance(pts[0], (list, tuple)):
                self.water.append(Obj(name=pond.get("name", "sensui"), label=pond.get("label", "泉水"),
                                      pts=[tuple(q) for q in pts], y=pond.get("waterY"), host=None))
            else:
                self.notes.append("sensui の汀線(pts)が読めない")
        # 見所
        self.views = []
        for vp in d.get("viewpoints", []) or []:
            uv = vp.get("uv") or ((vp["u"], vp["v"]) if "u" in vp else None)
            if uv is None:
                continue
            self.views.append(Obj(name=vp.get("name", "V"), label=self._label(vp, vp.get("name", "V")), uv=tuple(uv),
                                  dr=vp.get("dir"), eye=vp.get("eye"), target=None, raw=vp))
        for g in d.get("gardens", []) or []:
            mk = g.get("mikoro") if isinstance(g, dict) else None
            for m in (mk if isinstance(mk, list) else ([mk] if isinstance(mk, dict) else [])):
                if "u" in m and "v" in m:
                    tgt = None
                    if m.get("target") == "migiwa":
                        w = next((x for x in self.water if x.host == g["name"]), None)
                        tgt = centroid(w.pts) if w else None
                    self.views.append(Obj(name="%s#%s" % (g["name"], m.get("no", "")), label=m.get("label", "見所"),
                                          uv=(m["u"], m["v"]), dr=None, eye=m.get("eyeY"), target=tgt, raw=m))
        # 築山
        self.mounds = []
        tk = d.get("tsukiyama")
        for t in (tk if isinstance(tk, list) else ([tk] if isinstance(tk, dict) else [])):
            sk = t.get("skirt") or t.get("poly")
            if sk:
                self.mounds.append(Obj(name=t.get("name", "築山"), label=t.get("label", "築山"), poly=[tuple(q) for q in sk],
                                       top=(t.get("u"), t.get("v")), y=t.get("y")))
        # 土留め
        self.walls = []
        for w in d.get("terraceWalls", []) or []:
            if "a" in w and "b" in w:
                self.walls.append(Obj(name=w["name"], a=tuple(w["a"]), b=tuple(w["b"]), coping=w.get("coping"),
                                      drop=w.get("drop"), s=w.get("s"), raw=w))
        # 断面
        self.sections = []
        for s in d.get("sections", []) or []:
            if "line" in s and isinstance(s["line"], list) and len(s["line"]) >= 2:
                a, b = s["line"][0], s["line"][-1]           # 折れ線なら両端(切る所は直線で読む)
                self.sections.append(Obj(name=s.get("name", "断面"), a=tuple(a), b=tuple(b), eave=s.get("eaveAbove"),
                                         ridge=s.get("ridgeAbove"), vexag=s.get("vExag", 3.0), raw=s))
            elif s.get("axis") in ("u", "v") and "at" in s:
                lo, hi = s.get("from"), s.get("to")
                if lo is None or hi is None:
                    lo2, hi2 = (self.bb_uv[1], self.bb_uv[3]) if s["axis"] == "u" else (self.bb_uv[0], self.bb_uv[2])
                    lo, hi = (lo if lo is not None else lo2 - 2), (hi if hi is not None else hi2 + 2)
                if s["axis"] == "u":
                    a, b = self.W(s["at"], lo), self.W(s["at"], hi)
                else:
                    a, b = self.W(lo, s["at"]), self.W(hi, s["at"])
                self.sections.append(Obj(name=s.get("name", "断面"), a=a, b=b, eave=s.get("eaveAbove"),
                                         ridge=s.get("ridgeAbove"), vexag=s.get("vExag", 3.0), raw=s))
            elif "a" in s and "b" in s:
                self.sections.append(Obj(name=s.get("name", "断面"), a=self.W(*s["a"]), b=self.W(*s["b"]),
                                         eave=s.get("eaveAbove"), ridge=s.get("ridgeAbove"), vexag=s.get("vExag", 3.0), raw=s))
            else:
                self.notes.append("sections[%s] の切る所が読めない" % s.get("name"))
        # 役割
        self.program = []
        for p in d.get("program", []) or []:
            need = p.get("need") or ("必須" if any(a.get("cert") in ("S", "A") for a in p.get("aspects", [])) else "")
            by = p.get("by") or []
            cert = p.get("cert") or "/".join(a.get("cert", "?") for a in p.get("aspects", [])[:3])
            self.program.append(Obj(role=p.get("role", "?"), need=need, by=by, cert=cert, note=p.get("note") or p.get("_", "")))
        # lib へ渡す写し(段の形を lib の作法へ)
        self._libd = dict(d)
        self._libd["const"] = dict(self.const, ken=self.KEN)
        ts = []
        for t in self.terraces:
            b = bbox(t.poly)
            raw = dict(t.raw)
            raw.update({"u0": b[0], "v0": b[1], "u1": b[2], "v1": b[3], "y": t.y})
            if t.raw.get("uv") and not t.raw.get("poly"):
                raw["poly"] = [list(q) for q in t.poly]
            ts.append(raw)
        self._libd["terraces"] = ts
        self._libd.setdefault("terraceWalls", [])
        self._libd.setdefault("kaidans", [])
        self._libd.setdefault("ramps", [])
        self._lib_fail = 0

    def mine_edges(self):
        """当家が持つ辺 — 欄(edgeOwner / edges[].neighbor)が言えばそれ、無ければ当家の run が載る辺。"""
        n = len(self.poly)
        mine_ja = EST_JA.get(self.est, "")
        eo = self.d.get("edgeOwner") or {}
        eds = {e.get("i", i): e for i, e in enumerate(self.d.get("edges", []) or [])} if isinstance(self.d.get("edges"), list) else {}
        out = set()
        for e in range(n):
            if str(e) in eo:
                if eo[str(e)] == mine_ja:
                    out.add(e)
            elif e in eds and "建てない" in str(eds[e].get("kind", "")):
                continue
            elif e in eds and "当家" in str(eds[e].get("kind", "")):
                out.add(e)
            elif any(r.edge == e and r.mine for r in self.runs):
                out.add(e)
        return out

    # ---------------- 走査
    def cells(self, step=0.5, pad=1.0):
        u0, v0, u1, v1 = self.bb_uv
        u = math.floor(u0) - pad
        while u <= u1 + pad:
            v = math.floor(v0) - pad
            while v <= v1 + pad:
                yield (u + step / 2, v + step / 2, u, v)
                v += step
            u += step

    def buildings(self):
        return [("棟", m) for m in self.munes] + [("廊下", l) for l in self.links] + [("附属屋", s) for s in self.service]


# ================================================================ 検査(共通の 23)
class Checks(object):
    def __init__(self, M):
        self.M = M
        self.rows = []      # (id, title, result, status) status ∈ ok / ng / na
        self.detail = {}

    def add(self, cid, title, result, status, detail=None):
        self.rows.append((cid, title, result, status))
        if detail:
            self.detail[cid] = detail

    def run(self):
        # 検査は `cNN` という名のメソッドを足すだけで輪に入る(名簿を二重に持たない・規則19)。
        # 足したら docs/Sashizu/check_triage.json の common にも意図を 1 行足す
        fns = [getattr(self, n) for n in sorted(dir(self)) if len(n) == 3 and n[0] == "c" and n[1:].isdigit()]
        for f in fns:
            t0 = time.time()
            try:
                f()
            except Exception as ex:  # noqa: BLE001
                self.add(f.__name__.upper(), "(検査が落ちた)", "⛔ %s: %s" % (type(ex).__name__, ex), "ng")
            L.chk(f.__name__, lambda: None)
            L._CHK_T[f.__name__] = L._CHK_T.get(f.__name__, 0.0) + (time.time() - t0)
        return self.rows

    # C01 重なり 0
    def c01(self):
        M = self.M
        items = M.buildings() + [("石段", Obj(name=k.name, poly=shrink(k.poly, 0.2))) for k in M.kaidans if k.poly]
        bad = []
        for (ka, a), (kb, b) in itertools.combinations(items, 2):
            if polys_overlap(a.poly, b.poly):
                if {ka, kb} == {"棟", "廊下"} or {ka, kb} == {"廊下", "附属屋"}:
                    continue          # 渡廊下は棟へ一間乗り込む(取り付き)
                if ka == "廊下" and kb == "廊下":
                    continue
                bad.append("%s×%s" % (a.name, b.name))
        gb = 0
        for g in M.gardens:
            if not g.explicit:
                continue
            for kind, b in M.buildings():
                if polys_overlap(g.poly, b.poly) and not poly_inside(b.poly, g.poly):
                    gb += 1
                    bad.append("%s×%s" % (g.name, b.name))
        for ga, gb2 in itertools.combinations(M.gardens, 2):
            if polys_overlap(ga.poly, gb2.poly) and not (poly_inside(ga.poly, gb2.poly) or poly_inside(gb2.poly, ga.poly)):
                if ga.explicit and gb2.explicit:
                    bad.append("%s×%s" % (ga.name, gb2.name))
        n_rect = sum(1 for g in M.gardens if not g.explicit)
        note = "(割り当ての矩形の庭 %d は除く)" % n_rect if n_rect else ""
        self.add("C01", "重なり 0 — 棟・廊下・附属屋・石段・実形の庭の総当たり %d 組" % (len(items) * (len(items) - 1) // 2),
                 "%d 件 %s" % (len(bad), note), "ok" if not bad else "ng", bad[:12])

    # C02 区画の中
    def c02(self):
        M = self.M
        bad = []
        for kind, b in M.buildings():                     # 石段は区画の外(街路)へ降りてよい
            out = [q for q in b.poly if not M.in_parcel(*q) and edge_dist(q, M.poly_uv) * M.KEN > 0.05]
            if out:
                bad.append("%s(%d 頂点)" % (b.name, len(out)))
        res = "%d 件" % len(bad)
        self.add("C02", "区画の中 — 棟・廊下・附属屋の頂点が区画線の内(段は区画線で切られ、石段は街路へ降りてよい)", res,
                 "ok" if not bad else "ng", bad)

    # C03 面に載る
    def c03(self):
        M = self.M
        bad = []
        n = 0
        off = []
        for kind, b in M.buildings():
            n += 1
            ins = [M.terrace_at(*q) for q in b.poly]
            if all(t is None for t in ins):
                off.append(b.name)                       # 段に載らない棟(自前の面)は C04 が地形と突き合わせる
                continue
            if any(t is None for t in ins):
                bad.append("%s: 段の縁をまたぐ" % b.name)
                continue
            if b.y is not None and any(abs(t.y - b.y) > 0.05 + 0.6 for t in ins):
                bad.append("%s: y=%.2f が段 %s と合わない" % (b.name, b.y, "/".join("%.2f" % t.y for t in ins)))
        rb = 0
        for m in M.munes:
            for r in m.rooms:
                if not poly_inside(r.poly, m.poly):
                    rb += 1
                    bad.append("%s の室 %s が棟の外" % (m.name, r.name))
        nr = sum(len(m.rooms) for m in M.munes)
        self.add("C03", "面に載る — 棟・廊下・附属屋 %d の四隅が段の中、室 %d が棟の中" % (n, nr),
                 "%d 件%s" % (len(bad), (" / 段に載らず自前の面 %d(C04 で地形と突き合わせ)" % len(off)) if off else ""),
                 "ok" if not bad else "ng", bad[:12] + (["自前の面: " + "・".join(off)] if off else []))

    # C04 面と地形の差
    # ⭐ 系統差の許容。0.5 の包絡のうち**半分**を偏りに食われたら、面は導かれておらず選ばれている。
    OFFSET_TOL = 0.25

    def c04(self):
        M = self.M
        rows, bad = [], []
        worst = 0.0
        # 面ごとの許容(planes[].devEnvelopeM)と名指しの例外(planes[].devEnvelopeExceptions)は欄が持つ
        env = {}
        exc = set()
        exc_raw = []
        for p in M.planes:
            if isinstance(p, dict):
                for tn in p.get("terraces", []) or []:
                    if isinstance(p.get("devEnvelopeM"), (int, float)):
                        env[tn] = p["devEnvelopeM"]
                for x in p.get("devEnvelopeExceptions", []) or []:
                    exc.add(x if isinstance(x, str) else (x.get("name") if isinstance(x, dict) else None))
                    exc_raw.append(x)
        for kind, b in M.buildings():
            if kind == "廊下":
                continue
            if b.name in exc or b.label in exc:
                rows.append((b.label, b.name, 0.0, 0.0, 100.0, 0.0, 0.0))   # 表は 7 欄(系統差・ばらつきも)
                continue
            u0, v0, u1, v1 = bbox(b.poly)
            ds = []
            step = 0.5
            u = u0
            while u <= u1 + 1e-9:
                v = v0
                while v <= v1 + 1e-9:
                    if pip(b.poly, u, v) or edge_dist((u, v), b.poly) < 1e-6:
                        t = M.terrace_at(u, v)
                        y = b.y if b.y is not None else (t.y if t else None)
                        nat = M.nat(u, v)
                        if y is not None and nat is not None:
                            ds.append(y - nat)
                    v += step
                u += step
            if not ds:
                continue
            t0 = M.terrace_at(*centroid(b.poly))
            tol = env.get(t0.name, 0.5) if t0 else 0.5
            pc = 100.0 * sum(1 for q in ds if abs(q) <= tol) / len(ds)
            mx = max(abs(min(ds)), abs(max(ds)))
            # ⭐ **系統差**(この棟の足元の中央値と面の差)と**ばらつき**を分けて出す。
            #   規則3 は「自然の平場の高さをそのまま面に採る」という**導き方**であって許容ではない。
            #   面をその面に載る棟の足元から導けば系統差は 0 に近づく — 系統差が残るのは
            #   **面を選んでしまった印**で、直すのは棟でも土でもなく**面**(§B-1 の 2 に戻る)。
            #   ばらつき(地面の凹凸)は許容、系統差は許容しない。由来: 施主指摘 2026-09-20(EDO-0290)。
            med = statistics.median(ds)
            spread = max(abs(q - med) for q in ds)
            worst = max(worst, mx)
            rows.append((b.label, b.name, min(ds), max(ds), pc, med, spread))
            if abs(med) > Checks.OFFSET_TOL:
                bad.append("⛔%s **系統差 %+.2f m**(面の引き方。ばらつきは ±%.2f)"
                           % (b.name, med, spread))
            elif pc < 100.0:
                bad.append("%s ばらつき ±%.2f m が許容 %.2f を超える(%.0f%%)" % (b.name, spread, tol, pc))
        # ⛔ 検査を緩めた宣言は黙って通さない — 施主の言葉が要る(完成条件の render と同じ作法)
        for x in exc_raw:
            if isinstance(x, dict) and (x.get("quote") or "").strip():
                bad.append("⚠〔受容〕%s — %s" % (x.get("name"), (x.get("quote") or "")[:60]))
            else:
                nm = x if isinstance(x, str) else (x.get("name") if isinstance(x, dict) else "?")
                bad.append("⛔%s を検査から外しているが**施主の言葉が無い**"
                           "(`devEnvelopeExceptions[].quote` に引用を入れる)" % nm)
        for tn, ev in env.items():
            if ev > 0.5:
                bad.append("⛔ 段 %s の許容を %.2f m へ緩めている(規則3 は 0.5)" % (tn, ev))
        self.rows_c04 = rows
        self.add("C04", "面の引き方 — 棟ごとの**系統差**(規則3 は許容でなく導き方。系統差 > %.2f m は面の誤り)" % Checks.OFFSET_TOL,
                 "不合格 %d 棟 / 最大 %.2f m" % (len(bad), worst), "ok" if not bad else "ng", bad[:12])

    # C05 段差の受け
    def c05(self):
        M = self.M
        if not M.terraces:
            self.add("C05", "段差の受け", "未検査 — 段が無い", "na")
            return
        bad = 0
        total = 0
        samples = []
        for t in M.terraces:
            n = len(t.poly)
            for i in range(n):
                a, b = t.poly[i], t.poly[(i + 1) % n]
                Lk = math.hypot(b[0] - a[0], b[1] - a[1])
                k = max(1, int(Lk / 1.0))
                for j in range(k):
                    s = (j + 0.5) / k
                    u, v = a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s
                    # 外向き法線
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    nn = math.hypot(dx, dy) or 1e-9
                    c = centroid(t.poly)
                    ox, oy = -dy / nn, dx / nn
                    if (u + ox - c[0]) * ox + (v + oy - c[1]) * oy < (u - c[0]) * ox + (v - c[1]) * oy:
                        ox, oy = -ox, -oy
                    uo, vo = u + ox * 0.6, v + oy * 0.6
                    if not M.in_parcel(uo, vo):
                        continue                     # 区画線の縁は外周(runs)が受ける
                    total += 1
                    yo = M.design_y(uo, vo)
                    if yo is None or abs(yo - t.y) < 0.3:
                        continue                     # 法面で摺り付く / 同じ高さ
                    if yo > t.y + 1e-6:
                        continue                     # 隣が高い段(その段の縁で見る)
                    # 低い段と接する: 土留めか石段か run が 1m 以内に要る
                    near = any(seg_dist((u, v), w.a, w.b) * M.KEN < 1.0 for w in M.walls) or \
                        any(k.poly and (pip(k.poly, u, v) or edge_dist((u, v), k.poly) * M.KEN < 1.0) for k in M.kaidans) or \
                        any(seg_dist(M.W(u, v), r.a, r.b) < 1.0 for r in M.runs)
                    if not near:
                        bad += 1
                        if len(samples) < 8:
                            samples.append("%s (%.1f,%.1f) 落差 %.2f" % (t.name, u, v, t.y - yo))
        self.add("C05", "段差の受け — 高さの違う段が接する縁(区画の内側)%d 点に、土留め・石段・囲いが 1m 以内" % total,
                 "受けの無い点 %d" % bad, "ok" if bad == 0 else "ng", samples)

    # C06 土留め高と法
    def c06(self):
        M = self.M
        if not M.walls:
            self.add("C06", "土留め高と法", "該当無し — terraceWalls が空(法面は切盛図で見る)", "ok")
            return
        bad, rows = [], []
        for w in M.walls:
            if not isinstance(w.coping, (int, float)):
                continue                                   # 天端が別の物に従う(例: 石段なり)は Unity で測る
            drops = []
            Lk = math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1])
            k = max(2, int(Lk * M.KEN / 1.0))
            du, dv = w.b[0] - w.a[0], w.b[1] - w.a[1]
            nn = math.hypot(du, dv) or 1e-9
            ox, oy = -dv / nn * 0.3, du / nn * 0.3
            for j in range(k + 1):
                s = j / k
                u, v = w.a[0] + du * s, w.a[1] + dv * s
                # 壁の両側 0.3 間の造成後の地盤の低い方 = 壁の足元(見付)
                ys = []
                for sg in (1, -1):
                    uu, vv = u + ox * sg, v + oy * sg
                    nat = M.nat(uu, vv)
                    y = M.graded_y(uu, vv, nat)
                    if y is not None:
                        ys.append(y)
                if ys:
                    drops.append(w.coping - min(ys))
            if not drops:
                continue
            lo, hi = min(drops), max(drops)
            rows.append((w.name, w.coping, lo, hi, w.drop))
            if isinstance(w.drop, (list, tuple)) and len(w.drop) == 2 and hi > w.drop[1] + 0.15:
                bad.append("%s 実落差 %.2f > 宣言 %.2f" % (w.name, hi, w.drop[1]))
            if lo < -0.3:
                bad.append("%s 天端が地山より %.2f 低い(埋まる)" % (w.name, -lo))
            if hi > 4.0 + 0.05 and not w.raw.get("tiers", 1) > 1:
                bad.append("%s 一段で %.2f m(石垣の駒 4.0 を超える)" % (w.name, hi))
        self.rows_c06 = rows
        self.add("C06", "土留め高と法 — %d 本の天端と地山の落差(宣言・駒の丈・埋没)" % len(M.walls),
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])

    # C07 外周の閉じ
    def c07(self):
        M = self.M
        er = [r for r in M.runs if r.edge is not None]
        if not er:
            self.add("C07", "外周の閉じ", "未検査 — 辺に乗る run が無い(境内の囲いは C01/C09 で見る)", "na")
            return
        open_len = 0.0
        mine_len = 0.0
        holes = []
        n = len(M.poly)
        mine_edges = M.mine_edges()
        for e in range(n):
            Le = M.edge_len(e)
            rs = [r for r in er if r.edge == e]
            if e not in mine_edges:
                continue                                  # 隣家が持つ辺(⛔ run が 0 本の当家の辺は全長が隙間)
            k = max(1, int(Le / 0.25))
            cur = None
            for j in range(k):
                s = (j + 0.5) / k * Le
                cov = any(r.s0 - 0.01 <= s <= r.s1 + 0.01 for r in rs)
                if not cov:
                    for g in M.gates:
                        gs = g.s
                        if gs is None and g.w:
                            a9, b9 = M.poly[e], M.poly[(e + 1) % n]
                            if seg_dist(g.pos, a9, b9) < 3.0:
                                gs = math.hypot(g.pos[0] - a9[0], g.pos[1] - a9[1])
                        if (g.edge == e or g.edge is None) and gs is not None and g.w and abs(s - gs) <= g.w / 2 + 0.01:
                            cov = True
                            break
                mine_len += Le / k
                if not cov:
                    open_len += Le / k
                    if cur is None:
                        cur = [e, s, s]
                    else:
                        cur[2] = s
                elif cur is not None:
                    holes.append(cur)
                    cur = None
            if cur is not None:
                holes.append(cur)
        holes = [h for h in holes if h[2] - h[1] > 0.3]
        # 隅(留め継ぎ・隅の腕)と門の袖・番所の取り合いは部材の実寸で決まる — Unity で測る(規則2・5)
        corner = max(M.const.get("nagayaD") or 0.0, 5.0)        # 隅の腕(留め継ぎ・隅部材)は 5m まで部材の実寸
        kept, joint = [], []
        for h in holes:
            e, s0, s1 = h
            Le = M.edge_len(e)
            # 取り合いの帯(隅 corner m・門の袖塀と番所+1m)を差し引いた残りが本当の隙間
            ex = [(0.0, corner), (Le - corner, Le)]
            for g in M.gates:
                if g.edge == e and g.s is not None:
                    pl = g.plan or {}
                    half = (g.w or 0) / 2 + (pl.get("sode") or 0) + 1.0
                    bs = pl.get("bansho")
                    if isinstance(bs, dict) and isinstance(bs.get("w"), (int, float)) and "躯体内" not in str(bs.get("kind", "")):
                        half += bs["w"]
                    ex.append((g.s - half, g.s + half))
            segs = [(s0, s1)]
            for a9, b9 in ex:
                nxt = []
                for x0, x1 in segs:
                    if b9 <= x0 or a9 >= x1:
                        nxt.append((x0, x1))
                    else:
                        if x0 < a9:
                            nxt.append((x0, a9))
                        if b9 < x1:
                            nxt.append((b9, x1))
                segs = nxt
            rem = sum(x1 - x0 for x0, x1 in segs)
            if rem > 0.3:
                kept.append((e, s0, s1, rem))
            else:
                joint.append(h)
        open_len = sum(h[3] for h in kept)
        self.add("C07", "外周の閉じ — 当家が持つ辺 %.0f m を 0.25m 刻みで歩き、塀・長屋・門で塞がっているか(隅と門の袖の取り合い %d 区間は Unity で測る)" % (mine_len, len(joint)),
                 "隙間 %.1f m(%d 区間)" % (open_len, len(kept)), "ok" if open_len < 0.3 else "ng",
                 ["辺%d s=%.1f〜%.1f(取り合いを除き %.1f m)" % h for h in kept[:10]])

    # C08 門の割りと段
    def c08(self):
        M = self.M
        if not M.gates:
            self.add("C08", "門の割りと段", "未検査 — 門が読めない", "na")
            return
        bad, rows = [], []
        for g in M.gates:
            note = []
            if g.w and "長屋門" in (g.kind or ""):                 # 長屋門の柱割りは江戸間。冠木門・楼門の幅は部材なり
                q = g.w / M.KEN
                if abs(q - round(q * 2) / 2) > 0.02:
                    note.append("幅 %.3f m = %.2f 間(江戸間で閉じない)" % (g.w, q))
            # 敷居と石段
            if g.sill is not None:
                ks = [k for k in M.kaidans if (k.raw.get("sillOf") == "gate" and g.main) or
                      (k.poly and edge_dist(M.UV(*g.pos), k.poly) * M.KEN < 6.0)]
                for k in ks:
                    ys = [y for y in (k.y0, k.y1) if y is not None]
                    if ys and min(abs(y - g.sill) for y in ys) > 0.05:
                        note.append("敷居 %.2f と石段 %s の足元/天端 %s が合わない" % (g.sill, k.name, ys))
            # 動線が門を通るか
            uvg = M.UV(*g.pos)
            passes = any(min(edge_dist(uvg, [a, b]) if False else seg_dist(uvg, a, b) for a, b in zip(r.uv, r.uv[1:])) * M.KEN < 2.5
                         for r in M.routes if len(r.uv) > 1)
            if M.routes and not passes and g.main:
                note.append("どの動線も門を通らない")
            rows.append((g.name, g.kind, g.w, g.sill, "; ".join(note) or "—"))
            if note:
                bad.append("%s: %s" % (g.name, "; ".join(note)))
        self.rows_c08 = rows
        self.add("C08", "門の割りと段 — 門 %d の柱割りが江戸間で閉じ、敷居が石段と繋がり、動線が通る" % len(M.gates),
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])

    # C09 離れ
    def c09(self):
        M = self.M
        inu = M.const.get("inubashiri", 0.3)
        bad = []
        items = [(k, b) for k, b in M.buildings() if k != "廊下"]
        for k, b in items:
            dm = min(edge_dist(q, M.poly_uv) for q in b.poly) * M.KEN
            if dm < inu - 0.01 and not any(polys_overlap(b.poly, [M.UV(*r.a), M.UV(*r.b)] + [M.UV(r.b[0] + r.nrm[0] * r.depth, r.b[1] + r.nrm[1] * r.depth), M.UV(r.a[0] + r.nrm[0] * r.depth, r.a[1] + r.nrm[1] * r.depth)]) for r in M.runs if r.nrm):
                bad.append("%s—区画線 %.2f m < 犬走り %.2f" % (b.name, dm, inu))
        self.add("C09", "離れ — 棟と区画線は犬走り %.2f m 以上(外周の長屋を除く)。棟どうしの取り合いは Unity で測る" % inu,
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])

    # C10 屋根の食い込み
    def c10(self):
        M = self.M
        noki = M.const.get("nokiDe") or M.const.get("nokiE") or 0.9
        bad = []
        items = [(k, b) for k, b in M.buildings() if k != "廊下"]
        for (ka, a), (kb, b) in itertools.combinations(items, 2):
            dm = polys_dist(a.poly, b.poly) * M.KEN
            if 1.0 < dm < 2 * noki - 0.01:
                bad.append("%s—%s 躯体の離れ %.2f < 軒の出×2 %.2f" % (a.name, b.name, dm, 2 * noki))
        self.add("C10", "屋根の食い込み — 離れて建つ棟の躯体の間が軒の出 %.2f m の二倍以上(1m 以下は谷で受ける取り合い= Unity で測る)" % noki,
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])

    # C11 石段
    def c11(self):
        M = self.M
        if not M.kaidans:
            self.add("C11", "石段", "該当無し — 石段が無い", "ok")
            return
        keri_max = M.const.get("keri", 0.30)
        bad, rows = [], []
        for k in M.kaidans:
            note = []
            keri = k.keri
            ys = sorted({t.y for q in (k.poly or []) for t in [M.terrace_at(*q)] if t})
            on_ground = not (k.y0 is not None and k.y1 is not None and ys and
                             min(abs(y - k.y0) for y in ys) > 0.3 and min(abs(y - k.y1) for y in ys) > 0.3)
            if not on_ground:
                note.append("床と床の階(木階)— 部材で測る")
            elif k.steps and k.drop is not None:
                keri_calc = k.drop / k.steps
                if keri is not None and abs(keri * k.steps - k.drop) > 0.05:
                    note.append("蹴上 %.3f×%d ≠ 落差 %.2f" % (keri, k.steps, k.drop))
                if keri_calc > keri_max + 0.005 and "参道" not in (k.label or "") and "坂" not in (k.label or ""):
                    note.append("蹴上 %.3f > %.2f" % (keri_calc, keri_max))
            else:
                note.append("段数か落差が無い(未検査)")
            if on_ground and k.poly and k.y0 is not None and k.y1 is not None:
                if ys and not (any(abs(y - k.y1) < 0.05 for y in ys) or any(abs(y - k.y0) < 0.05 for y in ys)):
                    note.append("足元 %.2f/天端 %.2f がどの段の高さ %s とも合わない" % (k.y0, k.y1, ys))
            rows.append((k.label, k.steps, k.drop, keri, k.run, k.w, "; ".join(note) or "—"))
            if note and "未検査" not in note[0] and "木階" not in note[0]:
                bad.append("%s: %s" % (k.name, "; ".join(note)))
        self.rows_c11 = rows
        na = sum(1 for r in rows if "未検査" in r[-1])
        self.add("C11", "石段 %d — 段数×蹴上が落差と閉じ、蹴上 ≤ %.2f(屋敷内)、足元と天端が段の高さ" % (len(M.kaidans), keri_max),
                 "%d 件%s" % (len(bad), (" / 未検査 %d" % na) if na else ""), "ok" if not bad else "ng", bad[:12])

    # C12 道の勾配と繋がり
    def c12(self):
        M = self.M
        if not M.routes:
            self.add("C12", "道の勾配と繋がり", "未検査 — 動線が無い", "na")
            return
        gmax = M.const.get("routeGradeMax", 0.20)
        bad, rows = [], []
        for r in M.routes:
            ys, grades, pierce = [], [], 0
            for a, b in zip(r.uv, r.uv[1:]):
                Lk = math.hypot(b[0] - a[0], b[1] - a[1])
                k = max(1, int(Lk * M.KEN / 0.5))
                prev = None
                for j in range(k + 1):
                    s = j / k
                    u, v = a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s
                    nat = M.nat(u, v)
                    y = M.graded_y(u, v, nat)
                    on_stair = any(kk.poly and (pip(kk.poly, u, v) or edge_dist((u, v), kk.poly) * M.KEN < 0.6) for kk in M.kaidans) \
                        or self._on_ramp(u, v) \
                        or any(math.hypot(u - M.UV(*g.pos)[0], v - M.UV(*g.pos)[1]) * M.KEN < 2.5 for g in M.gates)   # 門の敷居
                    if y is not None:
                        ys.append(y)
                        # 一枡 0.5m の中の 0.15m 未満の差は敷居・縁石の一段で、勾配ではない
                        if prev is not None and not on_stair and Lk > 0 and abs(y - prev) >= 0.15:
                            grades.append(abs(y - prev) / (Lk * M.KEN / k))
                        prev = y
                    for m in M.munes:
                        # 室を持つ棟(御殿)は中を歩く。室の無い棟(蔵・長屋・厩)を貫くのが欠陥
                        if not m.rooms and pip(m.poly, u, v) and edge_dist((u, v), m.poly) > 0.5:
                            pierce += 1
            mg = max(grades) if grades else 0.0
            note = []
            if mg > gmax:
                note.append("段の無い区間の勾配 %.0f%% > %.0f%%" % (mg * 100, gmax * 100))
            if pierce:
                note.append("室の無い棟の中を %d 点通る" % pierce)
            # 繋がり: 両端が門・棟・庭・他の動線の 2m 以内
            ends = [r.uv[0], r.uv[-1]]
            for q in ends:
                near = any(math.hypot(q[0] - M.UV(*g.pos)[0], q[1] - M.UV(*g.pos)[1]) * M.KEN < 3.0 for g in M.gates) or \
                    any(edge_dist(q, b.poly) * M.KEN < 2.0 or pip(b.poly, *q) for k2, b in M.buildings()) or \
                    any(pip(g.poly, *q) for g in M.gardens) or \
                    any(seg_dist(q, a, b) * M.KEN < 2.0 for r2 in M.routes if r2 is not r for a, b in zip(r2.uv, r2.uv[1:])) or \
                    any(kk.poly and edge_dist(q, kk.poly) * M.KEN < 2.0 for kk in M.kaidans) or \
                    self._on_ramp(*q) or not M.in_parcel(*q) or edge_dist(q, M.poly_uv) * M.KEN < 3.0
                if not near:
                    note.append("端 (%.1f,%.1f) がどこにも着かない" % q)
            rows.append((r.label, plen(r.pts), (max(ys) - min(ys)) if ys else 0.0, mg, "; ".join(note) or "—"))
            if note:
                bad.append("%s: %s" % (r.name, "; ".join(note)))
        self.rows_c12 = rows
        self.add("C12", "道の勾配と繋がり — 動線 %d の縦断(造成後)が %.0f%% 以下、室を貫かず、両端が門・棟・庭・道に着く" % (len(M.routes), gmax * 100),
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])

    def _on_ramp(self, u, v, tol_m=1.5):
        """土の斜路(ramps: 折れ線 pts か矩形)の上か。"""
        M = self.M
        for r in M.d.get("ramps", []) or []:
            if isinstance(r.get("pts"), list) and len(r["pts"]) >= 2:
                pts = [q[:2] for q in r["pts"] if isinstance(q, (list, tuple))]
                if any(seg_dist((u, v), a, b) * M.KEN < tol_m + (r.get("w") or 0) / 2 for a, b in zip(pts, pts[1:])):
                    return True
            elif all(k in r for k in ("u0", "u1", "v0", "v1")):
                if pip(rect(r["u0"], r["v0"], r["u1"], r["v1"]), u, v) or edge_dist((u, v), rect(r["u0"], r["v0"], r["u1"], r["v1"])) * M.KEN < tol_m:
                    return True
        return False

    # C13 役割の在庫
    def c13(self):
        M = self.M
        if not M.program:
            self.add("C13", "役割の在庫", "未検査 — program が無い(役割表は欄へ写す)", "na")
            return
        miss = [p.role for p in M.program if p.need.startswith("必須") and not p.by]
        self.add("C13", "役割の在庫 — 役割 %d のうち『必須』が棟・区画に結び付く" % len(M.program),
                 "欠 %d" % len(miss), "ok" if not miss else "ng", miss)

    # C14 水の系
    def c14(self):
        M = self.M
        if not M.water:
            self.add("C14", "水の系", "該当無し — 汀線を持つ庭が無い", "ok")
            return
        bad = []
        for w in M.water:
            outside = [q for q in w.pts if not M.in_parcel(*q)]
            if outside:
                bad.append("%s: 汀線 %d 点が区画の外" % (w.name, len(outside)))
            ts = {M.terrace_at(*q).y for q in w.pts if M.terrace_at(*q)}
            if w.y is not None and ts and w.y > min(ts) - 0.1:
                bad.append("%s: 水面 %.2f が段 %.2f より低くない" % (w.name, w.y, min(ts)))
            for k, b in M.buildings():
                if polys_overlap(w.pts, b.poly):
                    bad.append("%s: 水面が %s と重なる" % (w.name, b.name))
        self.add("C14", "水の系 — 汀線 %d が区画と段の中にあり、水面が段より低く、棟と重ならない" % len(M.water),
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])

    # C15 庭の点景と見所
    def c15(self):
        M = self.M
        pts = [("築山", m.name, m.poly) for m in M.mounds]
        if not (pts or M.views):
            self.add("C15", "庭の点景と見所", "該当無し — 築山・見所が無い", "ok")
            return
        bad = []
        for kind, name, poly in pts:
            if any(not M.in_parcel(*q) for q in poly):
                bad.append("%s %s が区画の外" % (kind, name))
            for k, b in M.buildings():
                if polys_overlap(poly, b.poly):
                    bad.append("%s %s が %s と重なる" % (kind, name, b.name))
            for w in M.water:
                if polys_overlap(poly, w.pts):
                    bad.append("%s %s が水面 %s に落ちる" % (kind, name, w.name))
        for v in M.views:
            tgt = v.target
            if tgt is None and v.dr:
                dv = {"+u": (1, 0), "-u": (-1, 0), "+v": (0, 1), "-v": (0, -1), "東": (1, 0), "西": (-1, 0), "北": (0, 1), "南": (0, -1)}.get(v.dr)
                if dv:
                    tgt = (v.uv[0] + dv[0] * 8, v.uv[1] + dv[1] * 8)      # 向きだけの見所は 8 間先まで
            if tgt is not None:
                for m in M.munes:
                    if pip(m.poly, *v.uv) or edge_dist(v.uv, m.poly) < 1.0:
                        continue                                          # 自分の座る棟(入側)
                    for i in range(len(m.poly)):
                        if segs_cross(v.uv, tgt, m.poly[i], m.poly[(i + 1) % len(m.poly)]):
                            bad.append("見所 %s の視線を %s が遮る" % (v.name, m.name))
                            break
        self.add("C15", "庭の点景と見所 — 築山 %d が区画の中で棟・水と重ならず、見所 %d の視線(名指しの的か向き 8 間)を棟が遮らない" % (len(pts), len(M.views)),
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])

    # C16 植栽の在庫と本数
    def c16(self):
        M = self.M
        idx = os.path.join(ROOT, "docs", "asset-index.tsv")
        names = set()
        if os.path.exists(idx):
            for line in open(idx, encoding="utf-8"):
                if line.startswith("#"):
                    continue
                for tok in line.rstrip("\n").split("\t"):
                    names.add(tok)
                    names.add(os.path.basename(tok))
                    names.add(os.path.splitext(os.path.basename(tok))[0])
        assets = set()

        def walk(o, key=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, key)
            elif isinstance(o, str) and key in ("asset", "assets", "part", "parts", "fbx", "prefab") \
                    and " " not in o.strip() and ("/" in o or o.startswith("Own.") or o.startswith("JG.") or o.startswith("EdoAssets.")):
                assets.add(o.strip())

        for key in ("planting", "plantAssets", "plantRule", "slopePlanting", "slopeBands", "gardens", "planting_out"):
            walk(M.d.get(key), key)
        if not assets:
            self.add("C16", "植栽の在庫と本数", "未検査 — 植栽の欄に部材の名指しが無い", "na")
            return
        cs = os.path.join(ROOT, "Assets", "Edo", "Scripts", "Editor", "EdoAssets.cs")
        cs_src = open(cs, encoding="utf-8").read() if os.path.exists(cs) else ""
        miss = []
        for a in sorted(assets):
            base = a.split("(")[0]
            leaf = base.split(".")[-1].split("/")[-1]
            hit = base in names or os.path.basename(base) in names or any(leaf and leaf in n for n in names) or \
                os.path.exists(os.path.join(ROOT, base)) or os.path.exists(os.path.join(ROOT, "Assets", base)) or \
                (leaf and leaf in cs_src)                    # EdoAssets.cs の名指し(規則12: パスの literal は EdoAssets.cs にだけ)
            if not hit:
                miss.append(a)
        self.add("C16", "植栽の在庫と本数 — 名指しした部材 %d が目録(asset-index.tsv)・Assets/・EdoAssets.cs のどれかに実在する" % len(assets),
                 "無い %d" % len(miss), "ok" if not miss else "ng", miss[:12])

    # C17 植栽の退避
    def c17(self):
        M = self.M
        fp = os.path.join(DOC, M.est + "_planting_out.json")
        if not os.path.exists(fp):
            self.add("C17", "植栽の退避", "未検査 — 撒いた点(%s_planting_out.json)が無い。撒くのは実装(類型ビルダー)へ" % M.est, "na")
            return
        try:
            P = json.load(open(fp, encoding="utf-8"))
        except Exception as ex:  # noqa: BLE001
            self.add("C17", "植栽の退避", "⛔ 読めない: %s" % ex, "ng")
            return
        pts = []

        def walk(o):
            if isinstance(o, dict):
                if "u" in o and "v" in o and isinstance(o["u"], (int, float)):
                    pts.append((o["u"], o["v"]))
                else:
                    for v in o.values():
                        walk(v)
            elif isinstance(o, list):
                if len(o) == 2 and all(isinstance(q, (int, float)) for q in o):
                    pts.append((o[0], o[1]))
                else:
                    for v in o:
                        walk(v)

        walk(P)
        bad = 0
        for q in pts:
            if any(pip(b.poly, *q) for k, b in M.buildings()) or any(k.poly and pip(k.poly, *q) for k in M.kaidans) or \
               any(pip(w.pts, *q) for w in M.water):
                bad += 1
        self.add("C17", "植栽の退避 — 撒いた %d 点が棟・廊下・附属屋・石段・水の上に無い" % len(pts),
                 "%d 点" % bad, "ok" if bad == 0 else "ng")

    # C18 地盤の出所
    def c18(self):
        M = self.M
        note = ["地盤 = %s" % M.dem_name]
        st = "ok"
        if M.dem_name == "base_dem.json":
            note.append("江戸期復元(%s_edo_world.json)が無く正本をそのまま使う" % M.est)
        elif M.base is not None:
            same = tot = 0
            for u, v, _, _ in M.cells(2.0, 0.0):
                if not M.in_parcel(u, v):
                    continue
                x, z = M.W(u, v)
                a, b = M.dem.at(x, z), M.base.at(x, z)
                if a is None or b is None:
                    continue
                tot += 1
                if abs(a - b) < 0.01:
                    same += 1
            if tot:
                note.append("正本 base_dem と一致する点 %d / %d(%.0f%%)。差は復元(近代の掘削を戻した)所" % (same, tot, 100.0 * same / tot))
        # 派生物の鮮度
        js = os.path.getmtime(os.path.join(DOC, M.est + "_sashizu.json"))
        for fn in (M.est + "_edo_dem.json", M.est + "_terrain.json"):
            fp = os.path.join(DOC, fn)
            if os.path.exists(fp):
                age = (os.path.getmtime(fp) - os.path.getmtime(M.dem.path)) / 86400.0
                if age < -0.02:                                # 同じ生成で続けて書かれる 30 分は許す
                    note.append("⚠ %s が地盤 %s より古い(%.1f 日)" % (fn, M.dem_name, -age))
                    st = "ng"
        # 隣家の辺
        nb = M.d.get("neighbours") or M.d.get("neighbors")
        if isinstance(nb, dict):
            for k, v in nb.items():
                if isinstance(v, dict) and v.get("file") and v.get("sha"):
                    fp = os.path.join(DOC, v["file"])
                    if os.path.exists(fp):
                        cur = L._sha(fp)
                        if cur != v["sha"]:
                            note.append("⚠ 隣家 %s の指図が動いた(記録 %s → 今 %s)" % (k, v["sha"], cur))
                            st = "ng"
        self.add("C18", "地盤の出所 — 造成前の地盤が正本 base_dem.json から来て、派生物が古くなく、隣家の指図が動いていない",
                 " / ".join(note), st)

    # C19 区画の正典一致
    def c19(self):
        M = self.M
        fp = os.path.join(DOC, "parcels.json")
        if not os.path.exists(fp):
            self.add("C19", "区画の正典一致", "未検査 — parcels.json が無い", "na")
            return
        P = json.load(open(fp, encoding="utf-8"))
        ps = P.get("parcels", P)
        cands = [p for p in ps if isinstance(p, dict) and p.get("id") and (p["id"] == M.est or M.est.split("_")[0] in p["id"])]
        best, bd = None, 1e9
        cm = centroid(M.poly)
        for p in cands or [q for q in ps if isinstance(q, dict) and q.get("pts")]:
            pts = p.get("pts") or p.get("polygon")
            if not pts:
                continue
            c2 = centroid([tuple(q[:2]) for q in pts])
            dd = math.hypot(c2[0] - cm[0], c2[1] - cm[1])
            if dd < bd:
                best, bd = p, dd
        if best is None:
            self.add("C19", "区画の正典一致", "未検査 — parcels.json に対応する区画が無い", "na")
            return
        pts = [tuple(q[:2]) for q in (best.get("pts") or best.get("polygon"))]
        if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
            pts = pts[:-1]                                    # 閉じの重複頂点
        # 頂点数が違っても(直線上の点の有無)輪郭が同じなら一致。互いの頂点から相手の輪郭までの距離で測る
        mx = max(max(edge_dist(a, pts) for a in M.poly), max(edge_dist(b, M.poly) for b in pts))
        self.add("C19", "区画の正典一致 — polygon が parcels.json の %s(頂点 %d / 指図 %d)と同じ輪郭" % (best["id"], len(pts), len(M.poly)),
                 "輪郭の最大ずれ %.3f m" % mx, "ok" if mx < 0.05 else "ng")

    # C20 造成の量と波及
    def c20(self):
        """造成は区画線で切る(隣地へ土を出さない)。ならば区画線の内側 0.3m で造成後と造成前の差が
        残っている所は、隣家の辺に**受けの無い垂直面**として届く — そこは外周の run(基壇石垣)が受けるか、
        法面が区画線の手前で地山に摺り付いていなければならない(土井 boundary_fill / 岡部 edge_drop の共通形)。"""
        M = self.M
        bad_len = 0.0
        samples = []
        n = len(M.poly_uv)
        for e in range(n):
            a, b = M.poly_uv[e], M.poly_uv[(e + 1) % n]
            Lk = math.hypot(b[0] - a[0], b[1] - a[1])
            k = max(1, int(Lk * M.KEN / 1.0))
            nw = M.inward(e)
            for j in range(k):
                s = (j + 0.5) / k
                xw, zw = M.edge_pt(e, s * M.edge_len(e))
                xi, zi = xw + nw[0] * 0.3, zw + nw[1] * 0.3
                u, v = M.UV(xi, zi)
                nat = M.nat(u, v)
                y = M.graded_y(u, v, nat)
                if nat is None or y is None or abs(y - nat) <= 0.3:
                    continue
                if any(seg_dist((xw, zw), r.a, r.b) < 1.0 for r in M.runs):
                    continue                              # 基壇石垣・塀の座が受ける
                if any(k2.poly and edge_dist((u, v), k2.poly) * M.KEN < 1.0 for k2 in M.kaidans) or self._on_ramp(u, v):
                    continue
                bad_len += Lk * M.KEN / k
                if len(samples) < 8:
                    samples.append("辺%d s=%.0fm 差 %+.2f" % (e, s * M.edge_len(e), y - nat))
        self.add("C20", "造成の量と波及 — 区画線の内側 0.3m に、囲いの座も法面の摺り付けも無い造成の差 >0.3m が残らない(切盛は其三の表)",
                 "受けの無い区画線 %.0f m" % bad_len, "ok" if bad_len < 1.0 else "ng", samples)

    # C21 建蔽率
    def c21(self):
        M = self.M
        K = M.KEN
        tot = 0.0
        rows = []
        for k, b in M.buildings():
            a = area(b.poly) * K * K
            if k == "廊下":
                ov = sum(area(b.poly) * K * K for m in M.munes if polys_overlap(b.poly, m.poly)) * 0.0
                a = max(0.0, a - ov)
            tot += a
            rows.append((k, b.label, a))
        for r in M.runs:
            if r.kind in ("Nagaya", "Mon") and r.mine:
                a = math.hypot(r.b[0] - r.a[0], r.b[1] - r.a[1]) * r.depth
                tot += a
                rows.append(("外周の長屋", r.name, a))
        for g in M.gates:
            if g.plan.get("monW") and g.plan.get("monD"):
                a = g.plan["monW"] * g.plan["monD"]
                tot += a
                rows.append(("門", g.name, a))
        self.kenpei = 100.0 * tot / M.area_m2
        self.rows_c21 = rows
        self.add("C21", "建蔽率 — 分母は敷地全体 %s 坪(規則6)" % "{:,.0f}".format(M.area_m2 / M.TSUBO),
                 "%.1f%%(建築面積 %s m²)" % (self.kenpei, "{:,.0f}".format(tot)), "ok")

    # C22 図の成立
    def c22(self):
        M = self.M
        bad = []
        for s in M.sections:
            if not (pip(M.poly, *s.a) or pip(M.poly, *s.b) or any(segs_cross(s.a, s.b, M.poly[i], M.poly[(i + 1) % len(M.poly)]) for i in range(len(M.poly)))):
                bad.append("断面 %s が区画を切らない" % s.name)
        if M.notes:
            bad.append("読めなかった欄 %d(末尾の表)" % len(M.notes))
        self.add("C22", "図の成立 — 断面 %d が区画を切り、読めなかった欄が無い" % len(M.sections),
                 "%d 件" % len(bad), "ok" if not bad else "ng", bad[:12])


# ================================================================ 共通の壊し試し(C23)
def deep_probes(est):
    """設計を写して壊し、共通の検査が鳴るかを記録する。名前 → (壊し方, 鳴るべき検査, 鳴ったか)。"""
    base = json.load(open(os.path.join(DOC, est + "_sashizu.json"), encoding="utf-8"))
    mk = "munes" if "munes" in base else "mune"
    probes = {}

    def p_overlap(d):
        ms = d[mk]
        if len(ms) >= 2:
            for k in ("u0", "v0", "u1", "v1", "uc", "vc", "yaw", "L", "D", "poly", "du", "dv"):
                if k in ms[1]:
                    ms[0][k] = copy.deepcopy(ms[1][k])
    probes["棟を重ねる"] = ("C01", p_overlap)

    def p_outside(d):
        ms = d[mk]
        if ms:
            for k in ("u0", "u1", "uc"):
                if k in ms[0]:
                    ms[0][k] = ms[0][k] + 300
            if "poly" in ms[0]:
                ms[0]["poly"] = [[q[0] + 300, q[1]] for q in ms[0]["poly"]]
    probes["棟を区画の外へ"] = ("C02", p_outside)

    def p_raise(d):
        if d.get("terraces"):
            d["terraces"][0]["y"] = d["terraces"][0]["y"] + 3.0
            for m in d[mk]:
                if "y" in m:
                    m["y"] = m["y"] + 3.0
    probes["段を 3m 上げる"] = ("C04", p_raise)

    def p_norun(d):
        mine = Model(est, copy.deepcopy(d)).mine_edges()  # 隣家の辺の run を縮めても鳴らない(当家の辺だけ歩く)
        er = [r for r in d.get("runs", []) if "edge" in r and "s0" in r and "s1" in r and r.get("build") is not False
              and r["edge"] in mine and r["s1"] - r["s0"] >= 9.0]
        if not er:
            return False
        r = max(er, key=lambda q: q["s1"] - q["s0"])    # 当家の辺で一番長い run の真ん中に穴(隅・門から離す)
        hole = min(5.0, (r["s1"] - r["s0"]) / 3.0)
        mid = (r["s0"] + r["s1"]) / 2
        r2 = copy.deepcopy(r)
        r2["name"] = r["name"] + "_b"
        r["s1"], r2["s0"] = mid - hole / 2, mid + hole / 2
        d["runs"].append(r2)
        return True
    probes["外周の run の真ん中に穴(3〜5m)"] = ("C07", p_norun)

    def p_room_out(d):
        for m in d[mk]:
            if m.get("rooms"):
                r = m["rooms"][0]
                for k in ("u0", "u1"):
                    if k in r:
                        r[k] = r[k] + 50
                return True
        return False
    probes["室を棟の外へ"] = ("C03", p_room_out)

    out = {}
    for name, (cid, mut) in probes.items():
        d = copy.deepcopy(base)
        applied = mut(d)
        if applied is False:
            out[name] = {"expect": cid, "status": None, "rang": None}       # 壊す物が無い(該当無し)
            continue
        M = Model(est, d)
        C = Checks(M)
        C.run()
        st = {cid2: s2 for cid2, _, _, s2 in C.rows}
        out[name] = {"expect": cid, "status": st.get(cid), "rang": st.get(cid) == "ng"}
    return out


# ================================================================ 図
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(x, n=2):
    return "—" if x is None else ("%%.%df" % n) % x


class Fig(object):
    def __init__(self, M, W=980, pad=14):
        self.M = M
        xs = [p[0] for p in M.poly]
        zs = [p[1] for p in M.poly]
        self.P = L.Proj(min(xs) - pad, max(xs) + pad, min(zs) - pad, max(zs) + pad, W=W)
        self.n = 0

    def X(self, x):
        return self.P.X(x)

    def Y(self, z):
        return self.P.Y(z)

    def dpath(self, pts, close=True):
        s = "M " + " L ".join("%.1f %.1f" % (self.X(a), self.Y(b)) for a, b in pts)
        return s + (" Z" if close else "")

    def uvpath(self, pts, close=True):
        return self.dpath([self.M.W(u, v) for u, v in pts], close)

    def txt(self, x, z, s, cls="anS", anchor="middle", dy=0.0, halo=True):
        h = ';paint-order:stroke;stroke:var(--paper);stroke-width:3px' if halo else ''
        return '<text x="%.1f" y="%.1f" class="%s" style="text-anchor:%s%s">%s</text>' % (
            self.X(x), self.Y(z) + dy, cls, anchor, h, esc(s))

    def base(self, fill="var(--paper2)"):
        self.n += 1
        P = self.P
        o = ['<rect x="0" y="0" width="%.0f" height="%.0f" fill="var(--paper2)"/>' % (P.W, P.H),
             '<defs><clipPath id="c%d"><path d="%s"/></clipPath></defs>' % (self.n, self.dpath(self.M.poly)),
             '<path d="%s" fill="%s" stroke="none"/>' % (self.dpath(self.M.poly), fill)]
        return o

    def clip(self):
        return ' clip-path="url(#c%d)"' % self.n

    def frame(self, o, scale=50):
        P = self.P
        o.append('<path d="%s" fill="none" stroke="var(--ink)" stroke-width="2.2"/>' % self.dpath(self.M.poly))
        px = P.L(scale)
        x, y = 16, P.H - 14
        o.append('<g><rect x="%.1f" y="%.1f" width="%.1f" height="4" fill="var(--ink)"/>'
                 '<rect x="%.1f" y="%.1f" width="%.1f" height="4" fill="var(--paper)" stroke="var(--ink)" stroke-width=".6"/>'
                 '<text x="%.1f" y="%.1f" class="sl">0</text><text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">%d m</text></g>'
                 % (x, y, px / 2, x + px / 2, y, px / 2, x, y - 5, x + px, y - 5, scale))
        x, y = P.W - 26, 34
        o.append('<g><path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="var(--ink)"/>'
                 '<text x="%.1f" y="%.1f" class="sl" style="text-anchor:middle">北</text></g>' % (x, y - 15, x - 5, y, x + 5, y, x, y + 12))
        return '<svg viewBox="0 0 %.0f %.0f">%s</svg>' % (P.W, P.H, "".join(o))

    # ---- 層
    def terr_color(self, t):
        ys = sorted({q.y for q in self.M.terraces})
        i = ys.index(t.y)
        pal = ["var(--pl-suso)", "var(--pl-omote)", "var(--pl-higashi)", "var(--pl-kita)", "var(--pl-main)", "var(--niwa)", "var(--pl-umaya)"]
        return pal[i % len(pal)]

    def terraces(self, o, label=True):
        for t in sorted(self.M.terraces, key=lambda q: q.y):
            o.append('<path d="%s" fill="%s" stroke="var(--ink)" stroke-width="1" stroke-dasharray="6 3" opacity=".9"%s/>'
                     % (self.uvpath(t.poly), self.terr_color(t), self.clip() if t.clip else ""))
        if label:
            for t in self.M.terraces:
                c = centroid(t.poly)
                o.append(self.txt(*self.M.W(*c), s="%s %.1f" % (t.label, t.y), cls="mu"))

    def gardens(self, o):
        for g in self.M.gardens:
            col = {"shirasu": "var(--shirasu)", "砂利敷": "var(--shirasu)", "jurin": "var(--take)", "kansho": "var(--niwa)",
                   "sagyo": "var(--dan3)"}.get(g.kind, "var(--niwa)")
            o.append('<path d="%s" fill="%s" opacity=".7" stroke="var(--roka)" stroke-width=".6" stroke-dasharray="3 2"%s/>'
                     % (self.uvpath(g.poly), col, self.clip()))
        for m in self.M.mounds:
            o.append('<path d="%s" fill="var(--tsuki)" stroke="var(--ink)" stroke-width=".6" opacity=".85"/>' % self.uvpath(m.poly))
        for w in self.M.water:
            o.append('<path d="%s" fill="var(--ike)" stroke="var(--ink)" stroke-width=".7"/>' % self.uvpath(w.pts))

    def runs(self, o):
        M = self.M
        for r in M.runs:
            if r.nrm:
                nx, nz = r.nrm
            else:
                dx, dz = r.b[0] - r.a[0], r.b[1] - r.a[1]
                n = math.hypot(dx, dz) or 1e-9
                nx, nz = -dz / n, dx / n
                mid = ((r.a[0] + r.b[0]) / 2 + nx, (r.a[1] + r.b[1]) / 2 + nz)
                if not pip(M.poly, *mid):
                    nx, nz = -nx, -nz
            dep = r.depth if r.kind == "Nagaya" else min(r.depth, 1.2)
            pts = [r.a, r.b, (r.b[0] + nx * dep, r.b[1] + nz * dep), (r.a[0] + nx * dep, r.a[1] + nz * dep)]
            fill = "var(--nagaya)" if r.kind == "Nagaya" else "var(--hei)"
            o.append('<path d="%s" fill="%s" stroke="var(--ink)" stroke-width=".6" opacity="%.2f"/>'
                     % (self.dpath(pts), fill, 1.0 if r.mine else 0.45))

    def buildings(self, o, label=True):
        M = self.M
        for l in M.links:
            o.append('<path d="%s" fill="var(--roka)" stroke="var(--ink)" stroke-width=".6" opacity=".9"/>' % self.uvpath(l.poly))
        for s in M.service:
            o.append('<path d="%s" fill="var(--ishi)" stroke="var(--ink)" stroke-width=".8"/>' % self.uvpath(s.poly))
        for m in M.munes:
            o.append('<path d="%s" fill="var(--nagaya)" stroke="var(--ink)" stroke-width=".9"/>' % self.uvpath(m.poly))
        for k in M.kaidans:
            if k.poly:
                o.append('<path d="%s" fill="var(--ishi)" stroke="var(--ink)" stroke-width=".7"/>' % self.uvpath(k.poly))
        for w in M.wells:
            x, z = M.W(*w.uv)
            o.append('<circle cx="%.1f" cy="%.1f" r="3" fill="var(--ike)" stroke="var(--ink)" stroke-width=".7"/>' % (self.X(x), self.Y(z)))
        if label:
            for m in M.munes:
                if area(m.poly) >= 12:
                    c = centroid(m.poly)
                    o.append(self.txt(*M.W(*c), s=m.label, cls="rmS", dy=4))
            for s in M.service:
                if area(s.poly) >= 16:
                    c = centroid(s.poly)
                    o.append(self.txt(*M.W(*c), s=s.label, cls="jo", dy=3))

    def gates(self, o, small=False):
        M = self.M
        for g in M.gates:
            x, z = g.pos
            sz = 5.0 if small else 8.0
            c = centroid(M.poly)
            dx, dz = c[0] - x, c[1] - z
            if g.edge is not None:
                dx, dz = M.inward(g.edge)
            n = math.hypot(dx, dz) or 1
            dx, dz = dx / n, dz / n
            px, py = self.X(x), self.Y(z)
            ax, ay = self.X(x + dx * 6), self.Y(z + dz * 6)
            ddx, ddy = ax - px, ay - py
            n2 = math.hypot(ddx, ddy) or 1
            ddx, ddy = ddx / n2, ddy / n2
            ox, oy = -ddy, ddx
            o.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="var(--shu)"/>'
                     % (px + ddx * sz * 1.7, py + ddy * sz * 1.7, px + ox * sz, py + oy * sz, px - ox * sz, py - oy * sz))
            if not small:
                o.append('<text x="%.1f" y="%.1f" class="anG" style="text-anchor:end;paint-order:stroke;stroke:var(--paper);stroke-width:3px">%s</text>'
                         % (px - ddx * sz * 1.2, py - ddy * sz * 1.2 + 4, esc(g.name)))

    def sections_lines(self, o):
        for i, s in enumerate(self.M.sections):
            o.append('<path d="%s" stroke="var(--shu)" stroke-width="1" stroke-dasharray="9 3 2 3" fill="none"/>' % self.dpath([s.a, s.b], False))
            o.append(self.txt(s.a[0], s.a[1], s=KAN[i % len(KAN)].replace("其", ""), cls="anG", dy=-4))

    # ---- 4 枚 + 配置図
    def haichi(self):
        o = self.base()
        self.terraces(o)
        self.gardens(o)
        self.runs(o)
        self.buildings(o)
        self.gates(o)
        self.sections_lines(o)
        return self.frame(o)

    def genkyo(self):
        M = self.M
        o = self.base()
        step = 2.0
        cells = []
        P = self.P
        x = P.wx0
        while x < P.wx1:
            z = P.wz0
            while z < P.wz1:
                cx, cz = x + step / 2, z + step / 2
                if pip(M.poly, cx, cz):
                    y = M.dem.at(cx, cz)
                    if y is not None:
                        cells.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>'
                                     % (P.X(x), P.Y(z + step), P.L(step) + .4, P.L(step) + .4, L.dem_color(y)))
                z += step
            x += step
        o.append('<g%s>%s</g>' % (self.clip(), "".join(cells)))
        ys = [M.dem.at(*M.W(u, v)) for u, v, _, _ in M.cells(2.0, 0.0) if M.in_parcel(u, v)]
        ys = [y for y in ys if y is not None]
        if ys:
            lo, hi = math.floor(min(ys)), math.ceil(max(ys))
            lv = 1 if hi - lo <= 16 else 2
            for level in range(int(lo), int(hi) + 1, lv):
                segs = L._iso(M.dem.raw, level)
                dd = []
                for (ax, az), (bx, bz) in segs:
                    if pip(M.poly, (ax + bx) / 2, (az + bz) / 2):
                        dd.append("M %.1f %.1f L %.1f %.1f" % (P.X(ax), P.Y(az), P.X(bx), P.Y(bz)))
                if dd:
                    o.append('<path d="%s" fill="none" stroke="var(--ishi)" stroke-width="%.1f" opacity="%.2f"/>'
                             % (" ".join(dd), 1.4 if level % 5 == 0 else .6, .9 if level % 5 == 0 else .5))
        for t in M.terraces:
            o.append('<path d="%s" fill="none" stroke="var(--shu)" stroke-width="1.2" stroke-dasharray="7 4"%s/>'
                     % (self.uvpath(t.poly), self.clip() if t.clip else ""))
        self.sections_lines(o)
        self.gates(o, small=True)
        return self.frame(o)

    def kirimori(self, C):
        M = self.M
        o = self.base()
        u0, v0, u1, v1 = M.bb_uv
        step = 0.5 if (u1 - u0) * (v1 - v0) / 0.25 <= 14000 else 1.0     # 大きな区画は 1 間の枡(図の重さ)
        cells = []
        vol = {}
        cell = (step * M.KEN) ** 2
        for u, v, u0, v0 in M.cells(step, 1.0):
            if not M.in_parcel(u, v):
                continue
            nat = M.nat(u, v)
            if nat is None:
                continue
            y = M.graded_y(u, v, nat)
            if y is None:
                continue
            dz = y - nat
            t = M.terrace_at(u, v)
            key = t.name if t else "(法面)"
            r = vol.setdefault(key, [0.0, 0.0, 0.0, 0.0, 0.0])
            r[4] += cell
            if dz > 0.05:
                r[0] += dz * cell
                r[1] = max(r[1], dz)
            elif dz < -0.05:
                r[2] += -dz * cell
                r[3] = max(r[3], -dz)
            cells.append('<path d="%s" fill="%s"/>' % (self.uvpath([(u0, v0), (u0 + step, v0), (u0 + step, v0 + step), (u0, v0 + step)]),
                                                     L.cf_color(dz)))
        o.append('<g%s>%s</g>' % (self.clip(), "".join(cells)))
        for k, b in M.buildings():
            o.append('<path d="%s" fill="none" stroke="var(--ink)" stroke-width=".7" stroke-dasharray="3 2"/>' % self.uvpath(b.poly))
        for t in M.terraces:
            o.append('<path d="%s" fill="none" stroke="var(--ink)" stroke-width="1"%s/>' % (self.uvpath(t.poly), self.clip() if t.clip else ""))
        self.vol = vol
        return self.frame(o)

    def section(self, s, idx, w=980, hgt=230, pad=44):
        M = self.M
        n = 360
        nat, des, ins = [], [], []
        for i in range(n + 1):
            t = i / n
            x, z = s.a[0] + (s.b[0] - s.a[0]) * t, s.a[1] + (s.b[1] - s.a[1]) * t
            u, v = M.UV(x, z)
            y0 = M.dem.at(x, z)
            nat.append(y0)
            des.append(M.graded_y(u, v, y0) if y0 is not None else None)
            ins.append(M.in_parcel(u, v))
        ys = [y for y in nat + des if y is not None]
        if not ys:
            return "<p class='cap'>断面 %s は地盤の外</p>" % esc(s.name)
        lo, hi = math.floor(min(ys)) - 1, math.ceil(max(ys)) + 8
        Lm = math.hypot(s.b[0] - s.a[0], s.b[1] - s.a[1])

        def PX(t):
            return pad + t * (w - pad * 2)

        def PY(y):
            return hgt - pad - (y - lo) / (hi - lo) * (hgt - pad * 1.5)

        o = ['<rect x="0" y="0" width="%d" height="%d" fill="var(--paper2)"/>' % (w, hgt)]
        gstep = 5 if (hi - lo) > 24 else 2
        for gy in range(int(lo), int(hi) + 1, gstep):
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--rule)" stroke-width=".7"/>' % (pad, PY(gy), w - pad, PY(gy)))
            o.append('<text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">%d</text>' % (pad - 4, PY(gy) + 3, gy))

        def line(arr, **kw):
            segs, cur = [], []
            for i, y in enumerate(arr):
                if y is None:
                    if len(cur) > 1:
                        segs.append(cur)
                    cur = []
                else:
                    cur.append((PX(i / n), PY(y)))
            if len(cur) > 1:
                segs.append(cur)
            return "".join('<path d="M %s" fill="none" %s/>' % (" L ".join("%.1f %.1f" % p for p in sg),
                                                                " ".join('%s="%s"' % (k.replace("_", "-"), vv) for k, vv in kw.items())) for sg in segs)

        pts = [(PX(i / n), PY(y)) for i, y in enumerate(nat) if y is not None]
        if pts:
            o.append('<path d="M %s L %.1f %.1f L %.1f %.1f Z" fill="var(--dan3)" stroke="none"/>'
                     % (" L ".join("%.1f %.1f" % p for p in pts), pts[-1][0], PY(lo), pts[0][0], PY(lo)))
        o.append(line(nat, stroke="var(--ink)", stroke_width="1.4"))
        o.append(line(des, stroke="var(--shu)", stroke_width="2.2"))
        idx2 = [i for i, q in enumerate(ins) if q]
        if idx2:
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="var(--shu)" stroke-width="1" stroke-dasharray="5 3"/>'
                     % (PX(idx2[0] / n), pad * 0.35, PX(idx2[-1] / n) - PX(idx2[0] / n), hgt - pad - pad * 0.35))
        eave = s.eave or M.const.get("gotenEave") or 3.4
        ridge = s.ridge or (eave + 2.4)
        for kind, b in M.buildings():
            hit = [i for i in range(n + 1) if pip(b.poly, *M.UV(s.a[0] + (s.b[0] - s.a[0]) * i / n, s.a[1] + (s.b[1] - s.a[1]) * i / n))]
            if len(hit) > 2:
                t = M.terrace_at(*centroid(b.poly))
                y0 = b.y if b.y is not None else (t.y if t else None)
                if y0 is None:
                    continue
                e2, r2 = (eave, ridge) if kind == "棟" else (eave * 0.7, eave * 0.7 + 1.2)
                x0, x1 = PX(hit[0] / n), PX(hit[-1] / n)
                o.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="var(--nagaya)" opacity=".85"/>'
                         % (x0, PY(y0), x0, PY(y0 + e2), (x0 + x1) / 2, PY(y0 + r2), x1, PY(y0 + e2), x1, PY(y0)))
                o.append('<text x="%.1f" y="%.1f" class="jo" style="text-anchor:middle">%s</text>' % ((x0 + x1) / 2, PY(y0 + r2) - 3, esc(b.label)))
        o.append('<text x="%.1f" y="%.1f" class="sl">%s　延長 %.0f m ／ 縦 %.0f 倍</text>' % (pad, hgt - 8, esc(s.name), Lm, s.vexag or 3))
        o.append('<text x="%.1f" y="%.1f" class="sl" style="text-anchor:end">黒=造成前の地盤 ／ 朱=造成後(段と法面) ／ 破線枠=区画</text>' % (w - pad, hgt - 8))
        return '<svg viewBox="0 0 %d %d">%s</svg>' % (w, hgt, "".join(o))

    def doro(self):
        M = self.M
        o = self.base()
        for t in M.terraces:
            o.append('<path d="%s" fill="var(--dan1)" stroke="var(--rule)" stroke-width="1"%s/>' % (self.uvpath(t.poly), self.clip() if t.clip else ""))
        self.runs(o)
        for k, b in M.buildings():
            o.append('<path d="%s" fill="var(--dan3)" stroke="var(--rule)" stroke-width=".6"/>' % self.uvpath(b.poly))
        for k in M.kaidans:
            if k.poly:
                o.append('<path d="%s" fill="var(--ishi)" stroke="var(--ink)" stroke-width=".5"/>' % self.uvpath(k.poly))
        COL = ["#A8452C", "#3E6A8C", "#7A6A2A", "#7A3A6A", "#3E7A55", "#8C5A2C", "#2C6A7A", "#6A2C3E"]
        kinds = []
        for r in M.routes:
            if r.kind not in kinds:
                kinds.append(r.kind)
            c = COL[kinds.index(r.kind) % len(COL)]
            o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" opacity=".9"/>'
                     % (self.dpath(r.pts, False), c))
            a, b = r.pts[0], r.pts[-1]
            o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (self.X(a[0]), self.Y(a[1]), c))
            o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--paper)" stroke="%s" stroke-width="2"/>' % (self.X(b[0]), self.Y(b[1]), c))
        self.route_legend = "".join('<span style="color:%s">— %s</span>' % (COL[i % len(COL)], esc(k or "動線")) for i, k in enumerate(kinds))
        self.gates(o, small=True)
        return self.frame(o)


# ================================================================ 表と組み立て
def tbl(head, rows):
    h = ['<div class="tw"><table><thead><tr>']
    for c in head:
        h.append('<th%s>%s</th>' % (' class="note"' if c.startswith("*") else "", esc(c.lstrip("*"))))
    h.append("</tr></thead><tbody>")
    for r in rows:
        h.append("<tr>")
        for c in r:
            s = str(c)
            if s.startswith("*"):
                h.append('<td class="note">%s</td>' % L.inline(s[1:]))
            else:
                h.append("<td>%s</td>" % s)
        h.append("</tr>")
    h.append("</tbody></table></div>")
    return "".join(h)


def plate(h, kan, title, meta=""):
    h.append('<div class="plate"><div class="phead"><h2>%s　%s</h2><span class="meta">%s</span></div>' % (kan, esc(title), esc(meta)))


def fig(h, s, legend="", cap=""):
    h.append('<div class="fig">%s</div>' % s)
    if legend:
        h.append('<div class="legend">%s</div>' % legend)
    if cap:
        h.append('<p class="cap">%s</p>' % cap)


def estate_title(est):
    fp = os.path.join(DOC, est + "_kosho.md")
    if os.path.exists(fp):
        for line in open(fp, encoding="utf-8"):
            if line.startswith("# "):
                return line[2:].strip().split("—")[0].split("(")[0].strip()
    return est


def build(est, deep=False, out=None):
    t_all = time.time()
    if deep:
        os.environ["SASHIZU_DEEP"] = "1"
    M = Model(est)
    C = Checks(M)
    C.run()
    F = Fig(M)
    css = open(os.path.join(HERE, "sashizu.css"), encoding="utf-8").read()
    kfp = os.path.join(DOC, est + "_kosho.md")
    prose = L.md2html(open(kfp, encoding="utf-8").read()) if os.path.exists(kfp) else ""
    title = estate_title(est)
    n = [0]

    def nx():
        n[0] += 1
        return KAN[n[0] - 1]

    h = ['<meta charset="utf-8">', "<title>%s 指図</title>" % esc(title), "<style>%s</style>" % css, '<div class="wrap">']
    h.append('<p class="eyebrow">安政三年 ／ 共通の生成器 build_sashizu.py ／ %s</p>' % datetime.date.today())
    h.append("<h1>%s 指図</h1>" % esc(title))
    h.append('<p class="lede">数値の正典は <code>%s_sashizu.json</code>、文章の正典は <code>%s_kosho.md</code>、'
             '地盤は <code>%s</code>。この頁は共通の生成器がその三つから組んだもので、実装は読んでいない。'
             '座標と部材の端は書かない — 取り合いと境界は Unity で実メッシュから測る(規則2・19)。</p>' % (est, est, M.dem_name))
    ng = sum(1 for r in C.rows if r[3] == "ng")
    na = sum(1 for r in C.rows if r[3] == "na")
    h.append('<div class="box"><p><b>敷地 %s 坪</b>(%s m²)。<b>建蔽率 %.1f%%</b>(分母=敷地全体・規則6)。'
             '段 %d ／ 棟 %d ／ 廊下 %d ／ 附属屋 %d ／ 外周の run %d ／ 門 %d ／ 石段 %d ／ 動線 %d ／ 庭 %d。'
             '検査 %d 本: 不合格 <b>%d</b>・未検査 %d。</p></div>'
             % ("{:,.0f}".format(M.area_m2 / M.TSUBO), "{:,.0f}".format(M.area_m2), C.kenpei, len(M.terraces), len(M.munes),
                len(M.links), len(M.service), len(M.runs), len(M.gates), len(M.kaidans), len(M.routes), len(M.gardens),
                len(C.rows), ng, na))

    # 其一 配置図
    plate(h, nx(), "配置図", "北が上 ／ 段・棟・外周・門・石段・庭・断面の切り位置")
    fig(h, F.haichi(),
        legend='<span style="color:var(--nagaya)">■ 棟・表長屋</span><span style="color:var(--hei)">■ 塀</span>'
               '<span style="color:var(--roka)">■ 渡廊下</span><span style="color:var(--ishi)">■ 附属屋・石段</span>'
               '<span style="color:var(--shu)">▶ 門 ／ ╌ 断面</span><span style="color:var(--ike)">● 井戸 ■ 水</span>',
        cap="段の色は高さの順。薄い塀は隣家が持つ辺。")
    rows = []
    for t in sorted(M.terraces, key=lambda q: -q.y):
        rows.append([t.label, "%.2f" % t.y, "{:,.0f}".format(area(t.poly) * M.KEN * M.KEN / M.TSUBO), "clip" if t.clip else "—"])
    h.append(tbl(["段", "面の高さ m", "坪", "区画で切る"], rows))
    rows = []
    for k, b in M.buildings():
        t = M.terrace_at(*centroid(b.poly))
        rows.append([k, b.label, b.name, "%.1f 坪" % (area(b.poly) * M.KEN * M.KEN / M.TSUBO), fmt(b.y), t.label if t else "(段の外)", b.zone if hasattr(b, "zone") else ""])
    h.append(tbl(["種", "名", "欄", "面積", "床の面 m", "載る段", "区域"], rows))
    h.append("</div>")

    # 其二 現況図
    plate(h, nx(), "現況図 — 造成前の地盤", "段彩 ／ 等高線 ／ 朱の破線=段 ／ 一点鎖線=断面")
    fig(h, F.genkyo(), legend=L.dem_legend(),
        cap="造成のすべての出発点。<code>%s</code>(正本 <code>base_dem.json</code> 由来)。面の高さは地形が決める(規則3)。" % M.dem_name)
    h.append("</div>")

    # 其三 切盛図
    plate(h, nx(), "切盛図", "暖色=盛土 ／ 寒色=切土 ／ 無彩=±0.05m ／ 段の外は法面で摺り付ける")
    svg = F.kirimori(C)
    fig(h, svg, legend=L.cutfill_legend(),
        cap="造成後の地盤(段の中は面の高さ、外は法面 1:%.1f 盛 / 1:%.1f 切、土留めのある縁は壁が受ける)と造成前の差。破線は棟の輪郭。%s"
            % (M.const.get("batterFill", 1.5), M.const.get("batterCut", 1.0),
               ("⚠ lib の造成モデルが %d 枡で読めず素朴な法面で代用した。" % M._lib_fail) if M._lib_fail else ""))
    rows = []
    tf = tc = 0.0
    for k, r in sorted(F.vol.items(), key=lambda q: -q[1][4]):
        tf += r[0]
        tc += r[2]
        rows.append([k, "{:,.0f}".format(r[4]), "{:,.0f}".format(r[0]), "%.2f" % r[1], "{:,.0f}".format(r[2]), "%.2f" % r[3]])
    rows.append(["<b>合計</b>", "—", "<b>{:,.0f}</b>".format(tf), "—", "<b>{:,.0f}</b>".format(tc), "差引 {:+,.0f} m³".format(tf - tc)])
    h.append(tbl(["段", "面積 m²", "盛土 m³", "最大盛 m", "切土 m³", "最大切 m"], rows))
    if getattr(C, "rows_c04", None):
        # ⭐ **系統差が先**(面の引き方)。ばらつきと |Δ|≤0.5 は従(地面の凹凸)。EDO-0290
        h.append(tbl(["棟", "欄", "系統差(面の引き方)", "ばらつき ±", "Δ 最小", "Δ 最大", "|Δ|≤0.5"],
                     [[a, b,
                       ("<b>%+.2f m</b>" % med) if abs(med) > Checks.OFFSET_TOL else "%+.2f m" % med,
                       "%.2f m" % sp, "%.2f" % lo, "%.2f" % hi, "%.0f%%" % pc]
                      for a, b, lo, hi, pc, med, sp in C.rows_c04]))
    if getattr(C, "rows_c06", None):
        h.append(tbl(["土留め", "天端 m", "実落差 最小", "最大", "宣言"],
                     [[a, "%.2f" % b, "%.2f" % lo, "%.2f" % hi, str(dcl) if dcl is not None else "—"] for a, b, lo, hi, dcl in C.rows_c06]))
    h.append("</div>")

    # 其四 断面
    plate(h, nx(), "断面", "黒=造成前 ／ 朱=造成後 ／ 棟は概略(軒高と棟高は const か断面の欄)")
    if M.sections:
        for i, s in enumerate(M.sections):
            h.append("<h4>%s</h4>" % esc(s.name))
            h.append('<div class="fig">%s</div>' % F.section(s, i))
    else:
        h.append('<p class="cap">⛔ sections が無い — 断面は規則3の必須図。欄に切る所(axis/at か line)を書く。</p>')
    h.append("</div>")

    # 其五 動線図
    plate(h, nx(), "動線図", "●=起点 ○=終点 ／ 段は薄く、棟は灰")
    svg = F.doro()
    fig(h, svg, legend=F.route_legend, cap="縦断の勾配と繋がりは検査 C12。")
    if getattr(C, "rows_c12", None):
        h.append(tbl(["系統", "延長 m", "昇り m", "段の無い区間の最急", "*検め"],
                     [[a, "%.0f" % b, "%.1f" % c, "%.0f%%" % (g * 100), "*" + nt] for a, b, c, g, nt in C.rows_c12]))
    if getattr(C, "rows_c11", None):
        h.append(tbl(["石段", "段数", "落差 m", "蹴上 m", "走り m", "幅 m", "*検め"],
                     [[a, b if b is not None else "—", fmt(c), fmt(d, 3), fmt(e), fmt(f), "*" + nt] for a, b, c, d, e, f, nt in C.rows_c11]))
    if getattr(C, "rows_c08", None):
        h.append(tbl(["門", "型", "幅 m", "敷居 m", "*検め"], [[a, b, fmt(c), fmt(d), "*" + nt] for a, b, c, d, nt in C.rows_c08]))
    h.append("</div>")

    # 其六 外周と役割
    plate(h, nx(), "外周と役割", "run の座と延長 ／ 役割表")
    rows = []
    for r in M.runs:
        rows.append([("辺%d" % r.edge) if r.edge is not None else "—", r.name, r.kind,
                     "%.1f" % math.hypot(r.b[0] - r.a[0], r.b[1] - r.a[1]), fmt(r.seat), "当家" if r.mine else "隣家"])
    h.append(tbl(["辺", "run", "種別", "延長 m", "座 m", "持ち主"], rows))
    if M.program:
        h.append(tbl(["役割", "要否", "棟・区画", "確度", "*覚"],
                     [[p.role, p.need or "—", "、".join(p.by) if p.by else "—", p.cert,
                       "*" + _cut(p.note or "", 160)] for p in M.program]))
    h.append("</div>")

    # 其七 検査
    plate(h, nx(), "検査 — 共通の %d 本" % len(C.rows), "生成のたびに機械で通す ／ 札は check_triage.json")
    rows = []
    for cid, what, res, st in C.rows:
        mark = {"ok": "○", "ng": "⛔", "na": "未検査"}[st]
        det = C.detail.get(cid)
        # ⛔ `esc()` だと C04 の **系統差** が字のまま刷られ、D01 が生成器自身の出力に鳴る(EDO-0268)。
        #   検査の文は散文なので行内の記法を器へ移す(L.inline は escape も兼ねる)。
        rows.append([cid, "*" + what, res + (("<br><small>" + "<br>".join(L.inline(x) for x in det) + "</small>") if det else ""), mark])
    h.append(tbl(["#", "*検査", "結果", "可否"], rows))
    h.append('<p class="cap">不合格 <b>%d</b> 件・未検査 %d 件。0 件は「その条件を満たした」以上を意味しない。'
             '部材の取り合い・境界・植栽の姿は Unity で実メッシュから測る(規則2・5・19)。</p>' % (ng, na))
    # 壊し試し
    sr = L.sens(est, "common_probes", lambda: deep_probes(est), None)
    if sr:
        h.append("<h4>共通の壊し試し(C23)</h4>")
        h.append(tbl(["壊し方", "鳴るべき検査", "鳴ったか"],
                     [[k, v["expect"], "○" if v["rang"] else ("該当無し" if v["rang"] is None else "⛔ %s" % v["status"])] for k, v in sr.items()]))
    # ⛔ `esc()` だけだと **太字** と `名` が**字として刷られる**(D01・掲示板 EDO-0178)。
    #   この一行は散文なので、行内の記法を html の器へ移す(L.inline は escape も兼ねる)。
    h.append('<p class="cap">%s</p>' % L.inline(L.sens_report(est)).replace("\n", "<br>"))
    if M.notes:
        h.append("<h4>読めなかった欄</h4>")
        h.append(tbl(["*欄"], [["*" + x] for x in M.notes]))
    h.append("</div>")

    # 考証
    if prose:
        h.append('<div class="plate"><div class="phead"><h2>考証と決めごと</h2><span class="meta">%s_kosho.md</span></div>' % est)
        h.append('<div class="prose">%s</div></div>' % prose)
    h.append('<p class="foot">%s 指図 ／ 設計値 <code>docs/Sashizu/%s_sashizu.json</code> ／ 文章 <code>docs/Sashizu/%s_kosho.md</code> ／ '
             '地盤 <code>%s</code> ／ 生成器 <code>Tools/Sashizu/build_sashizu.py</code>(全邸共通)。⛔ 生成器は実装を読まない。</p>'
             % (esc(title), est, est, M.dem_name))
    h.append("</div>")
    # ── 文書の記法(D01)。⛔ **図の字面だけを見る検査は構造的に 0 を返し続ける** —
    #   欠陥は html の本文と表に出る(掲示板 EDO-0178)。⚠ この物差し(svg_layout.doc_markup)は
    #   2026-09-20 の生成器の一本化で**呼び手を失ったまま**だった。測れるのに測っていなかった。
    #   ⚠ 母集団は「この章を足す前の紙」— 自分を測る循環を避ける。
    mk, mk_n = _doc_markup_plate(h)
    out = out or os.path.join(DOC, est + "_sashizu.html")
    open(out, "w", encoding="utf-8").write("\n".join(h))
    _write_check_record(est, out, C, ng, na, mk=mk)
    if mk:
        print("  %s D01 文書の記法が字になっている: %d 件(母集団 %s 字・引用の面 %d 件は別枠)"
              % ("⛔" if mk_n else "○", mk_n, "{:,}".format(mk["chars"]), mk["quoted"]))
    print("書いた: %s (%.0f KB)  %.0f 秒" % (os.path.relpath(out, ROOT), os.path.getsize(out) / 1024, time.time() - t_all))
    print("検査 不合格 %d / 未検査 %d / 建蔽率 %.1f%% / 図版 %d 面 / 読めなかった欄 %d" % (ng, na, C.kenpei, n[0], len(M.notes)))
    for cid, what, res, st in C.rows:
        if st != "ok":
            print("  %s %s: %s" % ({"ng": "⛔", "na": "未"}[st], cid, res))
            for x in (C.detail.get(cid) or [])[:8]:
                print("       - %s" % x)
    for x in M.notes:
        print("  ⚠ %s" % x)
    print(L.sens_report(est))
    print(L.chk_report(top=6, floor=2.0))
    return ng


def sashizu_sha(est, doc_dir=None):
    """指図の中身の指紋。⭐ 検査の記録がいまの指図を見た物かを、後から機械で言えるように。"""
    import hashlib
    p = os.path.join(doc_dir or DOC, est + "_sashizu.json")
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    except Exception:
        return ""


def _cut(s, n):
    """散文を n 字で切る。⛔ **記法の途中で切らない** — 片割れになった `**` や `` ` `` は
    対にならず、html の器へ移らずに**字として刷られる**(掲示板 EDO-0178・土井の役割表で実際に出た)。
    ⇒ 切ったあと、対になっていない印を落としてから省略記号を付ける。"""
    if len(s) <= n:
        return s
    s = s[:n]
    for mark in ("**", "`"):
        if s.count(mark) % 2:
            head = s[:s.rfind(mark)]
            # ⚠ 印を落として空になるなら、切り口ごとではなく**その印だけ**を抜く
            s = head if head.strip() else s.replace(mark, "", 1)
    return s.rstrip() + "…"


def _doc_markup_plate(h):
    """組み上がった紙を測り、その結果の章を**紙の末尾へ足す**。返すのは (結果, 件数)。

    ⛔ **除いた面を「数えていない」で済ませない**(2026-09-08 土井 第8巡)。`<code>` の中は
    記法そのものの引用なので欠陥に数えないが、⛔ **そこは同時に穴**でもある — 本物の欠陥が
    その面へ入り込めば鳴らない。⇒ 除いた面の件数と母集団を必ず一緒に刷る。
    """
    try:
        sys.path.insert(0, HERE)
        import svg_layout as SL                       # noqa: E402
        mk = SL.doc_markup("\n".join(h))
    except Exception as ex:                           # noqa: BLE001
        print("⚠ 文書の記法が測れなかった: %s" % ex)
        return None, 0
    n = mk["n"]
    h.append('<div class="plate"><div class="phead"><h2>文書の記法</h2>'
             '<span class="meta">svg_layout.doc_markup()</span></div>')
    rows = [[f, "、".join("%s %d" % (nm, c) for nm, c in row if c) or "0",
             str(sum(c for _, c in row))] for f, row in SL.doc_markup_counts(mk)]
    h.append(tbl(["面", "*腕ごと", "計"], rows))
    h.append('<p class="cap">記法が字として刷られている数 <b>%d</b> 件。'
             '母集団は <b>%d</b> の字面 / <b>%s</b> 字(<code>svg</code>・<code>style</code> の中は除く)。'
             '⛔ 別枠 — 記法そのものを引用している面(<code>code</code> の中・%d span)に %d 件。'
             'ここは欠陥に数えないが、⛔ <b>本物の欠陥がこの面へ入り込めば鳴らない穴</b>でもある。'
             '⚠ 図の字面(<code>svg</code> の中)は前の章が測る。</p></div>'
             % (n, mk["nodes"], "{:,}".format(mk["chars"]), mk["codeSpans"], mk["quoted"]))
    return mk, n


def _write_check_record(est, out, C, ng, na, mk=None):
    """図の機械検査の結果を**機械で読める形**で残す。

    ⛔ **刷るだけでは関門にならない。**2026-09-01、松江松平の図の検査は棟別 38.4% の赤を
    出していたのに誰も止まらず、建てて普請検査で出た。⇒ 実装の車線へ入る所(kansei_gate --init)が
    この記録を読んで止める(掲示板 EDO-0291・規則3・規則19)。
    ⚠ `--out` を付けた試し焼きでは、記録も同じ捨て場へ落ちる(正典の記録を汚さない)。
    """
    rec = {"_": "図の機械検査の結果。生成器が毎回書き、kansei_gate.py --init が読んで赤なら止める"
                "(EDO-0291)。⛔ 手で書かない — 図を焼き直せば入れ替わる。",
           "estate": est,
           "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "sashizu_sha": sashizu_sha(est),
           "ng": ng, "na": na,
           "rows": [{"id": cid, "what": what, "res": res, "status": st}
                    for cid, what, res, st in C.rows]}
    if mk is not None:
        # ⚠ D01 は紙が組み上がってからでないと測れないので、検査の表(C01〜)には並ばない。
        #   ⛔ だからといって記録から落とさない — 落とせば「測っていない」が「0 件」に化ける。
        rec["rows"].append({"id": "D01", "what": "文書の記法が字になっていないか",
                            "res": "%d 件(母集団 %s 字・引用の面 %d 件は別枠)"
                                   % (mk["n"], "{:,}".format(mk["chars"]), mk["quoted"]),
                            "status": "ng" if mk["n"] else "ok"})
        rec["ng"] = ng = ng + (1 if mk["n"] else 0)
    p = os.path.join(os.path.dirname(os.path.abspath(out)), est + "_checks.json")
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
            f.write("\n")
    except Exception as ex:                      # noqa: BLE001
        print("⚠ 検査の記録が書けなかった: %s" % ex)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    est = args[0]
    if not os.path.exists(os.path.join(DOC, est + "_sashizu.json")):
        print("⛔ 指図が無い: docs/Sashizu/%s_sashizu.json" % est)
        return 2
    out = None
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    return 1 if build(est, deep="--deep" in argv, out=out) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
