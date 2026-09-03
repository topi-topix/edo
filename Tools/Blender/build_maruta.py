"""**丸太物** — 崖側の手すりと、汀の杭列。岡部筑前守上屋敷。

    blender --background --python Tools/Blender/build_maruta.py -- [名前...] [--render]
    (名前を省くと全部。tesuri / tesuri_post / kui / nuki)

【なぜ新造するか】在庫に「江戸の丸太の手すり」「汀の杭」は無い。ただし
  **NatureManufacture の `wood_log_01..09` が本物の丸太**(樹皮の凹凸がモデリングされ、
  LOD0/1/2 と `M_Wood_fence` を持つ)なので、⛔ **円柱を自作しない** — 規則1のとおり
  **在庫の丸太を切って・並べて・留めて**再輸出する。

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` が正典】
  ・手すり = `routes.R_Katte.outsideRail.tesuri`
      柱 φ0.12・高さ 0.90・芯々 1間(`postPitchKen` 1.0 = 1.818)・**横木は丸太1段**
      (⛔ 竹垣にしない — 法肩の竹垣と読み違える。道の外肩が 1.2m 落ちる所の落下止め)
  ・杭列 = `nishi.kuiretsu`
      径 0.12〜0.18(**不同**)・全長 1.55(根入れ `neire` 1.2 + 頭の出)・傾 `tilt` 5°
      頭は水面 +0.25〜0.45(`topMin`/`topMax`)・**貫は頭から 0.35 下に1段**(`nuki.below`)

【向きとピボット(Unity 座標)】
  ・手すり `Maruta_Tesuri_1ken` … **1スパン**。幅=X(走り)/ 高さ=Y / 厚み=Z。
      ピボット = **スパンの中心・地盤レベル**。柱はスパンの **−X 端**に立ち、横木は
      −X 端から +X 端まで通る。⇒ 折れ線の各スパンの中点に yaw を与えて並べれば、
      柱が 1.818 ピッチで立ち横木が続く。**run の +X 端には `Maruta_Tesuri_Post` を1本足す**
      (⛔ 足さないと最後の横木が宙で終わる — 「端部材を忘れない」)。
  ・杭 `Kui_<径>` … ピボット = **頭の芯**。杭は −Y へ 1.55 垂れる。
      ⇒ Unity は `y = 水面 + rand(0.25..0.45)` を直に入れればよい。傾 5° は **+X 方向へ
      焼き込んである**ので、**yaw を乱数で振れば傾きの方位が散る**。
      ⛔ 芯々を等間隔にしない(指図 `pitchMin/pitchMax` 0.30〜0.40)。
  ・貫 `Kui_Nuki_1ken` … ピボット = **中心**、水平。⚠ 指図の「1スパン」は杭の芯々(0.3〜0.4m)
      だが、**それでは部材が数千本になる**ので **1間(1.818m)の丸太1本**として出した。
      据えるときは `y = 杭の頭 − 0.35`(`nuki.below`)、杭列の外側(水側)へ寄せて回す。

【材】`M_Wood_fence`(NatureManufacture の丸太の材質名をそのまま運ぶ)。⛔ 新規に作らない。
  Unity 側は `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap` が
  `.../Fence/Models` を借り先に見て結び直す。

【落とし穴】
  ・FBX に **LOD0/LOD1/LOD2 が同居**している。選り分けないと3重の丸太になる。
  ・切ると小口が開く。塞がないと中が透ける(棟の小口で踏んだのと同じ型)。
  ・丸太の軸は **X**。半径方向(Y,Z)だけを縮めて径を合わせる — 一様スケールすると
    長さが変わって樹皮の密度が部材ごとに食い違う。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM

NM = os.path.join(V.REPO, "Assets", "NatureManufacture Assets",
                  "Meadow Environment Dynamic Nature", "Fence", "Models")
LOGS = os.path.join(NM, "Construction Set Models")
TEX = os.path.join(NM, "T_Wood_fence_BC.tga")
OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Maruta")
SHOT = os.path.join(V.REPO, "Screenshots")

# 指図の値
POST_D, RAIL_D, RAIL_H = 0.12, 0.12, 0.90      # routes.R_Katte.outsideRail.tesuri
PITCH = 1.818                                   # postPitchKen 1.0
KUI_L, KUI_TILT = 1.55, 5.0                     # nishi.kuiretsu(全長 / 傾)
KUI_DIA = (0.12, 0.15, 0.18)                    # dMin..dMax の3種
NUKI_D = 0.09                                   # 貫の径【U — 指図に無い】


# ---------------------------------------------------------------- 丸太を切る
def _cap(o):
    """切り口(片面しか接していない辺の輪)を塞ぐ。⛔ 塞がないと丸太の中が透ける"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    n = len(edges)
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=64)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update()
    return n


def _bisect(o, x, keep_ge):
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector((x, 0, 0)), plane_no=Vector((1, 0, 0)),
                           clear_outer=not keep_ge, clear_inner=keep_ge)
    # ⚠ bisect は面を持たない頂点・辺を残す。消さないと bbox が嘘をつく(README)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()


def log_piece(stem, length, dia, name, frm=0.0):
    """丸太 `stem` から 長さ `length`・径 `dia` の一本を切り出す。軸は **+X**、中心は原点。
    frm = 元の丸太のどこから採るか(0=末端。個体差を出すのに使う)。
    ⭕ 片端は**元の丸太の自然な木口**を残す(frm=0 のとき)。切った側だけ塞ぐ。"""
    objs = VM.import_fbx_abs(os.path.join(LOGS, stem + ".FBX"),
                             keep=lambda n: n.endswith("_LOD0"))
    o = V.join(objs, name)
    me = o.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    L0 = max(xs) - min(xs)
    d0 = ((max(ys) - min(ys)) + (max(zs) - min(zs))) * 0.5
    cy, cz = (max(ys) + min(ys)) * 0.5, (max(zs) + min(zs)) * 0.5
    if length > L0 - 1e-3:
        raise SystemExit("[maruta] %s は %.3fm しかない(要 %.3fm)" % (stem, L0, length))
    # 軸を原点へ / 半径だけ合わせる(⛔ 一様スケールにしない — 樹皮の密度が部材ごとに狂う)
    k = dia / d0
    for v in me.vertices:
        v.co.x -= min(xs)
        v.co.y = (v.co.y - cy) * k
        v.co.z = (v.co.z - cz) * k
    me.update()
    x0 = min(max(0.0, frm), L0 - length)
    if x0 > 1e-4:
        _bisect(o, x0, True)
    _bisect(o, x0 + length, False)
    for v in o.data.vertices:
        v.co.x -= x0 + length * 0.5              # 長手の中心を原点へ
    o.data.update()
    _cap(o)
    return o


def upright(o, top_at_zero=True):
    """軸 +X の丸太を立てる。top_at_zero=True なら **頭が原点**(下へ垂れる)"""
    o.data.transform(Matrix.Rotation(math.radians(90), 4, 'Y'))
    zs = [v.co.z for v in o.data.vertices]
    dz = -max(zs) if top_at_zero else -min(zs)
    o.data.transform(Matrix.Translation((0, 0, dz)))
    o.data.update()
    return o


def tilt_x(o, deg, pivot_z=0.0):
    """鉛直の丸太を +X 方向へ deg 傾ける(回転の中心は z=pivot_z)。
    ⭕ 傾きの**方位**は Unity 側の yaw で散らす。ここでは大きさだけ焼く。"""
    T = (Matrix.Translation((0, 0, pivot_z))
         @ Matrix.Rotation(math.radians(deg), 4, 'Y')
         @ Matrix.Translation((0, 0, -pivot_z)))
    o.data.transform(T)
    o.data.update()
    return o


# ---------------------------------------------------------------- 部材
def tesuri(name="Maruta_Tesuri_1ken"):
    """手すり1スパン(柱1 + 横木1)。柱は −X 端、横木はスパン全長。"""
    post = upright(log_piece("wood_log_05", RAIL_H + 0.02, POST_D, "post", frm=0.10),
                   top_at_zero=False)
    post.data.transform(Matrix.Translation((-PITCH * 0.5, 0, 0)))
    rail = log_piece("wood_log_01", PITCH, RAIL_D, "rail", frm=0.35)
    rail.data.transform(Matrix.Translation((0, 0, RAIL_H - RAIL_D * 0.5)))
    for q in (post, rail):
        q.data.update()
    # ⚠ 同じ FBX を2度読むと `M_Wood_fence.001` ができる。join の前に必ず元の名前へ寄せる
    #   — Unity 側の remap は**名前一致**なので、.001 のままだと当たらず真っ白になる
    V.dedup_materials()
    return V.join([post, rail], name), name


def tesuri_post(name="Maruta_Tesuri_Post"):
    """run の端に足す柱1本。⛔ 足さないと最後の横木が宙で終わる。ピボット = 芯・地盤"""
    o = upright(log_piece("wood_log_05", RAIL_H + 0.02, POST_D, "post", frm=0.10),
                top_at_zero=False)
    o.name = name; o.data.name = name
    return o, name


def kui(dia=0.12, name=None):
    """汀の杭 1本。ピボット = **頭の芯**、−Y へ 1.55 垂れる。傾 5° を +X へ焼き込む。"""
    name = name or ("Kui_" + ("%.2f" % dia))
    # 径ごとに元の丸太と採る位置を変えて、並べたとき同じ木が繰り返さないようにする
    stem, frm = {0.12: ("wood_log_01", 0.05), 0.15: ("wood_log_02", 0.60),
                 0.18: ("wood_log_04", 0.20)}.get(round(dia, 2), ("wood_log_01", 0.05))
    o = upright(log_piece(stem, KUI_L, dia, name, frm=frm), top_at_zero=True)
    tilt_x(o, KUI_TILT, pivot_z=0.0)
    return o, name


def nuki(name="Kui_Nuki_1ken"):
    """杭列の貫。⚠ 指図の「1スパン」は杭の芯々(0.3〜0.4m)だが、それでは部材が
    数千本になるので **1間の丸太1本**として出した。ピボット = 中心・水平。"""
    o = log_piece("wood_log_02", PITCH, NUKI_D, name, frm=0.90)
    return o, name


PARTS = {
    "tesuri":      lambda: tesuri(),
    "tesuri_post": lambda: tesuri_post(),
    "kui":         None,          # 径3種は main が回す
    "nuki":        lambda: nuki(),
}


# ---------------------------------------------------------------- レンダ
def hook():
    """NatureManufacture の丸太のアルベドを結ぶ(`vklib.hook_textures` は Village Kit を見る)。
    ⚠ **Alpha の既定値を書くだけでは効かない。**FBX の取り込みで Alpha ソケットに
      TransparencyFactor が**リンクされている**ので、既定値は無視されて丸太が
      完全に透明になる(2026-09-04 に踏んだ — 検証レンダが全部無地の灰色だった)。
      **先にリンクを切ってから** 1.0 を入れ、描画法も不透明側へ倒す。"""
    for m in bpy.data.materials:
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        for sock in ('Alpha', 'Base Color'):
            for lk in list(b.inputs[sock].links):
                nt.links.remove(lk)
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.85
        try:
            m.surface_render_method = 'DITHERED'
        except Exception:
            pass
        if os.path.exists(TEX):
            img = nt.nodes.new('ShaderNodeTexImage')
            img.image = bpy.data.images.load(TEX, check_existing=True)
            img.location = (-600, 300)
            nt.links.new(img.outputs['Color'], b.inputs['Base Color'])


def bounds(objs):
    """頂点から直に測る。⚠ `vklib.bbox` は `o.bound_box` を見るが、**FBX を書き出した後は
    それが 0 に潰れている**ことがある(2026-09-04 に実測 — 書き出し前は 1.865 あったのに
    書き出し後の bbox が全部 0 になり、検証レンダの画角が壊れて真っ白になった)。"""
    import mathutils
    mn = mathutils.Vector((1e9,) * 3); mx = mathutils.Vector((-1e9,) * 3)
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    return mn, mx


def shots(o, key, extra=None, box=None):
    """⚠ `box` は**書き出しの前に**測った値を渡すこと。`export_fbx` を通した後は
    メッシュから測っても bbox が 0 に潰れる(2026-09-04 に実測。書き出し前は 1.865 あった
    部材の bbox が全部 0 になり、画角が壊れて検証レンダが真っ白の灰色1枚になった。
    `build_matsudaira_dewa_fuzokuya.py` が書き出しの前に測っているのはこのため)。"""
    hook()
    os.makedirs(SHOT, exist_ok=True)
    objs = [o] + list(extra or [])
    mn, mx = box if box else bounds(objs)
    print("[maruta] レンダ %-14s bbox X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
          % (key, mn.x, mx.x, mn.y, mx.y, mn.z, mx.z))
    c = (mn + mx) * 0.5
    r = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, 0.5)
    V.studio((c.x, mn.y - r * 2.4, c.z), (c.x, c.y, c.z),
             ortho_scale=r * 1.3, res=(1400, 1100))
    V.render(os.path.join(SHOT, "maruta_%s_elev.png" % key))
    V.studio((c.x - r * 0.9, c.y - r * 1.3, c.z + r * 0.55), (c.x, c.y, c.z),
             res=(1500, 1100))
    V.render(os.path.join(SHOT, "maruta_%s_3d.png" % key))


def chain(fn, n, dx):
    """並べた姿を見るための仮組み(**書き出さない**)。継ぎ目・端部を目で確かめる用"""
    out = []
    for i in range(n):
        o, _ = fn()
        o.data.transform(Matrix.Translation((i * dx, 0, 0)))
        o.data.update()
        out.append(o)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or ["tesuri", "tesuri_post", "kui", "nuki"]
    do_render = "--render" in argv
    jobs = []
    for k in want:
        if k == "kui":
            jobs += [("kui%.2f" % d, (lambda d=d: kui(d))) for d in KUI_DIA]
        elif k in PARTS and PARTS[k]:
            jobs.append((k, PARTS[k]))
        else:
            print("[maruta] ⚠ 知らない部材: %s" % k)
    for key, fn in jobs:
        V.reset()
        o, name = fn()
        mn, mx = bounds([o])
        print("[maruta] %-22s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  "
              "Y範囲 %.3f..%.3f  面=%d  材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, mx.z,
                 len(o.data.polygons), [mm.name for mm in o.data.materials]))
        if do_render:
            shots(o, key, box=(mn, mx))          # ⚠ 書き出しの前に撮る(bbox が潰れるため)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[maruta] 書き出し " + os.path.join(OUT, name + ".fbx"))
    if do_render:
        # ⭕ **並べた姿を必ず見る。**1本だけ見ても継ぎ目と端部の不良は見つからない
        V.reset()
        objs = chain(lambda: tesuri(), 4, PITCH)
        p, _ = tesuri_post()
        p.data.transform(Matrix.Translation((3.5 * PITCH, 0, 0))); p.data.update()
        shots(objs[0], "tesuri_run", extra=objs[1:] + [p])
        V.reset()
        objs = []
        import random
        random.seed(3)
        x = 0.0
        for i in range(14):
            o, _ = kui(KUI_DIA[i % 3])
            yaw = random.uniform(0, 360)
            o.data.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z'))
            o.data.transform(Matrix.Translation((x, random.uniform(-0.04, 0.04),
                                                 random.uniform(0.25, 0.45))))
            o.data.update(); objs.append(o)
            x += random.uniform(0.30, 0.40)
        nk, _ = nuki()
        nk.data.transform(Matrix.Translation((x * 0.5, 0.10, 0.35 - 0.35)))
        nk.data.update(); objs.append(nk)
        shots(objs[0], "kui_run", extra=objs[1:])


if __name__ == "__main__":
    main()
