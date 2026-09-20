# -*- coding: utf-8 -*-
"""**松江松平出羽守上屋敷の、隣の棟と接する棟の屋根** — 接する辺の軒を落として焼く。

    blender --background --python Tools/Blender/build_matsudaira_dewa_roofs.py -- [--render] [--only <名>]
    blender --background --python Tools/Blender/build_matsudaira_dewa_roofs.py -- --hirairi [--render] [--only <棟名>]
    blender --background --python Tools/Blender/build_matsudaira_dewa_roofs.py -- --geya [--render]

⭐⭐ **なぜ要るか(2026-09-09 普請検査の差し戻し1)。**
  表向の四棟(表役所・黒書院・大広間・玄関)は**棟の外形が隣どうし接している**
  (`munes[].u1` = 次の棟の `u0`)。そこへ四周へ一様に軒 0.90m を出していたので
  隣どうしの軒が **1.80m 食い込み**、寄りのレンダで
  「二つの軒先の間から空が透ける / 桟瓦の列が空中で途切れる / 軒先が何にも載らず宙に浮く /
   目の高さで軒線が X 字に交差して単一の谷線にならない」という姿になっていた。
  ⭕ 接する辺の軒を落とすと屋根の面が**棟の外形の線でぴたりと終わり**、隣の棟の流れと
    境界線の上で合わさって**本物の谷**になる。⛔ 身舎・入側は 1mm も動かさない。

⭐ **どの辺が接しているかは指図から機械的に出す**(⛔ 人の言葉を書き写さない)。
  `_touching()` が全棟の外形を総当たりして「同じ線を共有し、直交方向に重なりがある」辺を拾う。

⚠ **隣が「この生成器で焼く屋根を持たない棟」の場合は落とさない**(⚠ を刷って呼び出し元へ返す)。
  相手の屋根の形が分からないまま軒を落とすと、壁の上が素通しになる恐れがある。
"""
import bpy, sys, os, json, math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_goten_roof as GR

KEN = GR.KEN
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "matsudaira_dewa_sashizu.json")
SHOT = os.path.join(V.REPO, "Screenshots")


def load_munes():
    with open(SASHIZU, encoding="utf-8") as f:
        d = json.load(f)
    return d["munes"]


def _overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def _touching(m, others):
    """棟 m の四辺それぞれについて「外形の線を共有する隣の棟」を返す。
    返り値 = {"u0": mune|None, "u1": ..., "v0": ..., "v1": ...}。
    ⭐ 判定は **外形(u0,u1,v0,v1)が同じ線を共有し、直交方向の重なりが正**であること。"""
    r = {}
    for side in ("u0", "u1", "v0", "v1"):
        r[side] = None
    for n in others:
        if n is m:
            continue
        ov_v = _overlap(m["v0"], m["v1"], n["v0"], n["v1"])
        ov_u = _overlap(m["u0"], m["u1"], n["u0"], n["u1"])
        if ov_v > 0:
            if m["u0"] == n["u1"]:
                r["u0"] = n
            if m["u1"] == n["u0"]:
                r["u1"] = n
        if ov_u > 0:
            if m["v0"] == n["v1"]:
                r["v0"] = n
            if m["v1"] == n["v0"]:
                r["v1"] = n
    return r


def plan():
    """焼くべき棟の一覧を組む。返り値 = [(mune, noki 4つ組, 隣の名の辞書)]"""
    munes = load_munes()
    jobs = []
    for m in munes:
        rf = m.get("roof") or {}
        if not rf.get("bands"):
            continue
        tch = _touching(m, munes)
        nk = [1, 1, 1, 1]
        nb = {}
        for k, side in enumerate(("u0", "u1", "v0", "v1")):
            n = tch[side]
            if n is None:
                continue
            nb[side] = n["name"]
            if (n.get("roof") or {}).get("bands"):
                nk[k] = 0
            else:
                print("[dewa-roof] ⚠ %s の %s は %s と接するが、相手はこの生成器の屋根を"
                      "持たない(`roof` が空)。⇒ **軒は落とさない**。相手の屋根の形が"
                      "決まったら指図方へ戻して判断すること。" % (m["name"], side, n["name"]))
        if any(t == 0 for t in nk):
            jobs.append((m, tuple(nk), nb))
    return jobs


def spec(m):
    rf = m["roof"]
    ir = rf.get("irikawa") or {"u": [1, 1], "v": [1, 1]}
    return dict(bands=[int(b) for b in rf["bands"]], span=int(rf["spanKen"]),
                along=("v" if rf.get("alongV") else "u"),
                irikawa=(ir["u"][0], ir["u"][1], ir["v"][0], ir["v"][1]),
                fukizai=rf.get("fukizai", "sangawara"))


def bake(m, nk):
    s = spec(m)
    o = GR.make_banded(s["bands"], s["span"], along=s["along"], irikawa=s["irikawa"],
                       fukizai=s["fukizai"], noki=list(nk))
    return o


def place_for_pair(o, m):
    """ピボット(=棟の外形の中心)を郭グリッドの位置へ置く。
    ⭐ 写像は `along` によらず **grid u = −(局所 X) / grid v = +(局所 Y)**
      (`build_goten_roof._verify_eaves` と同じ根拠)。⇒ Blender X = −u[m] / Y = +v[m]。"""
    uc = (m["u0"] + m["u1"]) / 2.0 * KEN
    vc = (m["v0"] + m["v1"]) / 2.0 * KEN
    o.location = mathutils.Vector((-uc, vc, 0.0))
    return (-uc, vc)


def shots_single(o, name):
    return GR.render_banded(o, SHOT, name, eave=3.4)


def joint_xy(ma, mb):
    """⭐ 二棟が**共有する外形の線**を Blender 座標で返す。
    ⛔ ピボットの中点で代用しない — 棟の丈が違うと線から外れ、寄りの画が継ぎ目を外す
      (2026-09-10 に 0.9m 外して谷の見えない画を焼いた)。
    写像は `place_for_pair` と同じ **Blender X = −u[m] / Y = +v[m]**。"""
    if ma["u1"] == mb["u0"] or ma["u0"] == mb["u1"]:
        us = ma["u1"] if ma["u1"] == mb["u0"] else ma["u0"]
        vc = (max(ma["v0"], mb["v0"]) + min(ma["v1"], mb["v1"])) / 2.0
        return (-us * KEN, vc * KEN, "u")
    vs = ma["v1"] if ma["v1"] == mb["v0"] else ma["v0"]
    uc = (max(ma["u0"], mb["u0"]) + min(ma["u1"], mb["u1"])) / 2.0
    return (-uc * KEN, vs * KEN, "v")


def shots_pair(pair, tag):
    """⭐ **二つ並べて谷が通るかを見る。**⛔ 1棟ずつのレンダでは絶対に捕まらない不良
    (軒の交差・谷の抜け)を見るための画なので、**必ず2棟を同じ場で焼く**。"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    # ⛔⛔ **`o.location` を書いた直後の `matrix_world` は古い。**依存グラフが回るまで
    #   反映されないので、ここを飛ばすと**据える前の座標で画角を決めて**しまい、
    #   二棟が画面の隅に寄った画が焼ける(2026-09-10 に実際に焼いた)。
    bpy.context.view_layer.update()
    xs, ys, zs = [], [], []
    for o, _m in pair:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    W, D, H = max(xs) - min(xs), max(ys) - min(ys), max(zs)
    jx, jy, _ax = joint_xy(pair[0][1], pair[1][1])   # 接する辺の線そのもの
    out = []

    def shot(sub, cam, look, ortho=None, res=(1600, 1000)):
        for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
            bpy.data.objects.remove(c, do_unlink=True)
        for pl in [c for c in bpy.data.objects if c.name.startswith("Plane")]:
            bpy.data.objects.remove(pl, do_unlink=True)
        bpy.ops.mesh.primitive_plane_add(size=max(W, D) * 6, location=(cx, cy, 0.0))
        V.studio(cam, look, ortho_scale=ortho, res=res)
        f = os.path.join(SHOT, "%s_%s.png" % (tag, sub))
        V.render(f)
        out.append(f)
        print("RENDER %s" % f)

    # 1) ⭐ 真上の正射影 — 谷が一本の直線で通っているか。軒が交差していれば必ずここに出る
    shot("01_shinjo", (cx, cy, H + max(W, D) * 1.2), (cx, cy, 0.0),
         ortho=max(W, D) * 1.06, res=(1500, 1500))
    # 2) 継ぎ目の寄り(俯瞰)— 二つの流れが境界線の上で合わさっているか
    shot("02_tsugime", (jx - 20.0, jy - 24.0, H + 13.0), (jx, jy, 3.2), res=(1600, 1000))
    # 3) ⭐ 目の高さ — 立位の眼高。⚠ 屋根のピボット z=0 は**床**なので、
    #    地盤に立つ人の目は 1.45 − 御殿の床高 0.62 = **床上 0.83**
    shot("03_medakasa", (jx, jy - 34.0, 0.83), (jx, jy, 4.2), res=(1700, 900))
    # 4) ⭐⭐ **継ぎ目を真上から寄って**見る — 谷が一本の線で通っているか。
    #    引きの真上(01)では瓦の目まで読めない
    shot("05_tani_zoom", (jx, jy, H + 20.0), (jx, jy, 0.0), ortho=26.0, res=(1500, 1500))
    # 5) 継ぎ目を真横から(正射影)— 軒先線が X に交差していないか
    shot("04_tsugime_ortho", (jx + 34.0, jy, 3.4), (jx, jy, 3.4),
         ortho=max(D, H) * 1.15, res=(1600, 900))
    return out



# ---------------------------------------------------------------------------
# 奥向の棟4棟+厩の**平入り+庇**と、渡廊下の**差し掛けの下屋** — 指図から数を取る
# ---------------------------------------------------------------------------
# ⛔ **棟も廊下も人が数えて書かない**(規則4)— 集合の定義だけを持つ:
#     平入り+庇 = `munes[]` のうち **`roof`(帯割り)を持たない**棟(= `ROOF_NAGAYA_GATA_MUNES`)
#     下屋      = `links[]` のうち **kind が「渡廊下」**のもの(⛔ 御錠口・御膳所口は口で
#                 下屋を架けない ⇒ 2026-09-18 普請奉行の決定3)
#   軒桁は zone が「厩」なら `const.umayaEave`、ほかは `const.nagayaGataEave`(C# と同じ規則)。
# ⚠ **指図の軒桁は地盤基準**(`const._nagayaGataEave`)。部材のピボットは**床**なので、
#   焼くときに `const.gotenFloor` を引く。⇒ 据えるのは **棟の床**の高さ。


def load_doc():
    with open(SASHIZU, encoding="utf-8") as f:
        return json.load(f)


def plan_hirairi(doc):
    """[(名前, 桁行間, 梁間間, 軒桁(床上), 庇を断つ辺)] を指図から組む。"""
    c = doc["const"]
    ken, floor = c["ken"], c["gotenFloor"]
    jobs = []
    for m in doc["munes"]:
        if m.get("roof"):
            continue                      # 帯割りの棟(御殿)はこちらではない
        w = int(round(abs(m["u1"] - m["u0"])))
        d = int(round(abs(m["v1"] - m["v0"])))
        eav = (c["umayaEave"] if m.get("zone") == "厩" else c["nagayaGataEave"]) - floor
        jobs.append((m["name"], w, d, eav, list(m.get("hisashiOmit") or [])))
    return jobs


def plan_geya(doc):
    """[(名前, 桁行間, 幅間)] を指図から組む。⛔ 口(御錠口・御膳所口)は含めない。"""
    jobs = []
    for l in doc.get("links", []):
        if l.get("kind") != "渡廊下":
            continue
        du = abs(l["u1"] - l["u0"])
        dv = abs(l["v1"] - l["v0"])
        jobs.append((l["name"], max(du, dv), min(du, dv)))
    return jobs


def main_hirairi(argv):
    doc = load_doc()
    c = doc["const"]
    ken = c["ken"]
    r = c["nagayaGataRoof"]
    rdir = SHOT if "--render" in argv else None
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    jobs = plan_hirairi(doc)
    print("[dewa-hirairi] 平入り+庇の棟 %d(指図から)" % len(jobs))
    for nm, w, d, eav, omit in jobs:
        if only and nm != only:
            continue
        name = GR.hirairi_name(w, d, eav, omit)
        V.reset()
        o = GR.make_hirairi(w * ken, d * ken, eav, omit=omit, name=name,
                            hon=r["honKobai"], his=c["hisashiKobai"],
                            noki=c["nokiE"], hken=int(r["hisashiKen"]), ken=ken)
        mn, mx = GR.report(o, name)
        hu = 2 - len([q for q in omit if q in ("u0", "u1")])      # 庇の立つ u 側の数
        print("[dewa-hirairi] %-14s %-38s 身舎 %dx%d間 / 軒桁 床上 %.3f / 大棟 %.3f / z %.3f..%.3f"
              % (nm, name, w - hu * int(r["hisashiKen"]), int(r["moyaKen"]), eav,
                 eav + r["moyaKen"] / 2.0 * ken * r["honKobai"], mn.z, mx.z))
        if rdir:
            for f in GR.render_hirairi(o, rdir, name, eave=eav):
                print("RENDER %s" % f)
        V.export_fbx(o, os.path.join(GR.OUT, name + ".fbx"))
    print("[dewa-hirairi] → %s" % GR.OUT)


def main_geya(argv):
    doc = load_doc()
    c = doc["const"]
    ken = c["ken"]
    kobai = c[doc["roka"]["kobaiFrom"]]
    rdir = SHOT if "--render" in argv else None
    jobs = plan_geya(doc)
    seen = {}
    print("[dewa-geya] 下屋を架ける渡廊下 %d 本(指図から・⛔ 口は含めない)" % len(jobs))
    for nm, lk, wk in jobs:
        print("[dewa-geya]   %-28s 桁行 %g間 × 幅 %g間" % (nm, lk, wk))
        seen.setdefault((lk, wk), []).append(nm)
    for (lk, wk), users in sorted(seen.items()):
        name = "Goten_Roof_RokaGeya_%sken" % GR.KenTag(lk)
        if abs(wk - 1.0) > 1e-6:
            name += "_w%s" % GR.KenTag(wk)
        V.reset()
        o = GR.make_rokageya(lk * ken, wk * ken, name=name, kobai=kobai, noki=c["nokiE"])
        mn, mx = GR.report(o, name)
        print("[dewa-geya] %-30s 勾配 %.2f / 軒の出 %.2f / z %.3f..%.3f / 使う廊下 %s"
              % (name, kobai, c["nokiE"], mn.z, mx.z, ", ".join(users)))
        if rdir:
            for f in GR.render_hirairi(o, rdir, name, eave=1.0):
                print("RENDER %s" % f)
        V.export_fbx(o, os.path.join(GR.OUT, name + ".fbx"))
    print("[dewa-geya] → %s" % GR.OUT)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--hirairi" in argv:
        return main_hirairi(argv)
    if "--geya" in argv:
        return main_geya(argv)
    only = None
    if "--only" in argv:
        only = argv[argv.index("--only") + 1]
    jobs = plan()
    if not jobs:
        raise SystemExit("[dewa-roof] 接する棟が無い。指図を確かめること")
    print("[dewa-roof] 接する棟 %d 件:" % len(jobs))
    for m, nk, nb in jobs:
        print("[dewa-roof]   %-12s 外形 u[%d,%d] v[%d,%d] 軒 u0=%d u1=%d v0=%d v1=%d  隣 %s"
              % (m["name"], m["u0"], m["u1"], m["v0"], m["v1"], nk[0], nk[1], nk[2], nk[3],
                 ", ".join("%s=%s" % kv for kv in sorted(nb.items()))))
    made = []
    pair_only = "--pair-only" in argv
    for m, nk, _nb in jobs:
        if pair_only or (only and m["name"] != only):
            continue
        V.reset()
        o = bake(m, nk)
        name = o.name
        if "--render" in argv:
            for f in shots_single(o, name):
                print("RENDER %s" % f)
        V.export_fbx(o, os.path.join(GR.OUT, name + ".fbx"))
        made.append((m["name"], name))
        print("[dewa-roof] ⭕ %s → %s.fbx" % (m["name"], name))

    if "--render" in argv and not only:
        # ⭐ 隣り合う二棟を同じ場で焼いて谷を見る(表役所 ↔ 黒書院 = 接する辺 u=-32)
        munes = {m["name"]: m for m in load_munes()}
        jm = {m["name"]: (m, nk) for m, nk, _ in jobs}
        for a, b in (("Yakusho", "Kuroshoin"), ("Kuroshoin", "Ohiroma")):
            if a not in jm or b not in jm:
                continue
            V.reset()
            pair = []
            for nm in (a, b):
                m, nk = jm[nm]
                o = bake(m, nk)
                place_for_pair(o, m)
                pair.append((o, m))
            shots_pair(pair, "matsudaira_roof_pair_%s_%s" % (a, b))
    print("[dewa-roof] %d 本 → %s" % (len(made), GR.OUT))


if __name__ == "__main__":
    main()
