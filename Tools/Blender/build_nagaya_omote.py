"""**長さ可変の表長屋**を、在庫の `knagaya01c/l/r` から切って・並べて・留めて起こす。

    blender --background --python Tools/Blender/build_nagaya_omote.py -- 28.5
    blender --background --python Tools/Blender/build_nagaya_omote.py -- 28.5 --render
    blender --background --python Tools/Blender/build_nagaya_omote.py -- 20.0 --ends none
    blender --background --python Tools/Blender/build_nagaya_omote.py -- 12 16.35 28.5   # まとめて

【なぜ要るか】在庫の長屋は **中部材 8.065m / 妻部材 7.910m の固定寸法**しかない。外周の run は
  「丸ごとの棟を並べる」形でしか埋められないので、端数が必ず門・隅との間に残る
  (松江松平邸 御蔵門の西に 1.66m の食い込み・東に 0.96m の隙間が同時に出た。2026-08-29 実測)。
  **ユーザー裁定 2026-08-29:「長い表長屋を Blender で作るのが一番良い」** → 長さを引数にとる。

【方針】**ゼロからモデリングしない。**素の `knagaya01c.obj`(1棟=3窓)を**一間の窓割り(＝bay)**で
  切り出して並べ、両端に `knagaya01l/r` の妻(破風・鬼・妻壁)を継ぐ。彫り・瓦の実ジオメトリ・
  海鼠の浮き彫り・マテリアル名がそのまま残るので、隣に建つ在庫の長屋と質感が揃う。

【素の作り(実測。すべて obj 単位。×ES=1.818 で m)】
  ・1棟 = 4.4347 (= 8.062m)、その中に **窓が3つ**。したがって **bay = 棟/3 = 1.47823 (= 2.6874m)**
  ・窓(koshi)は幅 0.633 (1.151m)、窓と窓の間の無地の壁(pier)は 0.845 (1.536m)
  ・**海鼠(namako)・瓦(n_hira/n_maru/n_noki)は bay で完全に周期的**(頂点一致を総当たりで確認:
    namako 1828/1828・maru 438/438・hira 438/438・noki 12488/12512)。だから bay で切って
    並べれば継ぎ目は出ない。⛔ **bay より細かい共通周期は無い**(垂木だけ 0.3409 の独自ピッチ)
  ・妻部材 `l`/`r` は `c` と**同じ座標系**(屋根群の bbox が桁まで一致)。妻側だけ壁が 0.103 内へ
    引かれ、`namako2`(妻壁)・`n_kera_*`(破風)・`n_oni`(鬼)が付く

【長さの作り方】L から bay の本数 k と **pier の詰め ε** を解く:
      L/ES = 2·(1.67561 − ε/2) + k·(1.47823 − ε)
  ε は「窓と窓の間の無地の壁を全継ぎ目で一様に詰める/広げる」量。窓・瓦・海鼠の**形は一切
  伸ばさない** — 割付の繰り返し数 k と無地の pier だけで長さを吸う(ユーザー指示 2026-08-29)。
  ソルバは |ε| が最小になる k を選ぶので **L≥12m で |ε|≤0.21m、L≥20m で |ε|≤0.08m**。

【`--ends none`】両端を切りっぱなしにして隣へ突き付ける版。⚠ **切り口の位相は ε だけずれる**ので、
  ε の違う2本を突き付けると海鼠の紋が (εA−εB)/2 だけ食い違う。同じ長さ同士か、
  素の `knagaya01c` の継ぎ目と同程度(±0.1m)に収まる長さ同士で使うこと。

【切る場所】切断面は**必ず pier(無地の壁)の中**に取る。窓を切ると格子の小口が出る。
  bay の切り出しは `c` の中央の窓を挟んで対称に、妻の切り出しは妻寄りの窓を挟んで同じ位相で
  取るので、**継ぎ目の断面は互いに平行移動で一致する**(留め継ぎと同じ理屈)。

【出力の向き(Unity 座標)】幅=X / 高さ=Y / 厚み=Z、**見え面(街路側)= +Z**。
  ピボット = **走りの中心・土台の底・壁の外面**。壁の外面が Z=0 なので、外周線の上に
  `position = run の中点 / yaw = 外向き法線の方位 / scale = Vector3.one` で置ける。
  軒は +Z へ 0.58m 出て、躯体は −Z へ 3.12m 入る。
  ⚠ FBX 書き出しは Blender +Y を Unity −Z へ写す(README)。素の向き(表 = +Y)のままだと
    見え面が裏に出るので、書き出す前に **Z まわりに 180° 回す**(鏡映ではなく回転 —
    鏡映すると巻きが裏返るうえ窓割りが左右反転する)。

【落とし穴】
  ・obj を読んで `transform_apply` すると **X が反転する**(forward_axis='Z' の帰結)。
    素の x と符号が逆になるので、寸法は必ず読み込み後のメッシュから測ること。
  ・`bisect` は面を持たない頂点・辺を残す。消さないと bbox が嘘をつく(build_kado と同じ罠)。
  ・素は 1 マテリアル `knagayamap` で、しかも .obj の**サブアセット**として抱えられている。
    Unity の `SearchAndRemapMaterials` では当たらない → 提供元を名指しで結ぶ remap を使う
    (`Edo/長屋/表長屋のマテリアルをremap`)。
  ・素のモデルは**海鼠の浮き彫りが窓の下半分を横切っている**(z が重なっている)。これは
    在庫の意匠そのものなので直さない — 直すと隣の在庫長屋と見た目が食い違う。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ES   = 1.818                      # 江戸暦の共通スケール(EdoAssets.Eg.ES_NOTE)
SRC  = os.path.join(V.REPO, "Assets/edogoyomi/es_knagaya")
OUT  = os.path.join(V.REPO, "Assets/Edo/Models/Nagaya")
SHOT = os.path.join(V.REPO, "Screenshots")

EPS_MAX = 0.50                    # pier を詰められる上限(obj)。0.845 → 0.345 (0.63m) まで
EPS_MIN = -0.65                   # 広げられる上限。0.845 → 1.495 (2.72m) まで


# ---------------------------------------------------------------- 取り込み
def read_groups(stem):
    """.obj を群ごとに読み、Y-up→Z-up を焼いて {群名: object} で返す。
    ⚠ 焼くと **X が反転する**。以降の座標はすべてこの「焼いたあと」の系。"""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(SRC, stem + ".obj"),
                          forward_axis='Z', up_axis='Y', use_split_groups=True)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    V.sel(meshes)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return {o.name.split('.')[0]: o for o in meshes}, meshes


def xspan(o):
    xs = [v.co.x for v in o.data.vertices]
    return min(xs), max(xs)


def win_centers(koshi):
    """格子の頂点 x を隙間 0.30 で塊に割り、各窓の中心を返す(左→右)。"""
    xs = sorted(set(round(v.co.x, 4) for v in koshi.data.vertices))
    cl = [[xs[0]]]
    for a, b in zip(xs, xs[1:]):
        (cl.append([b]) if b - a > 0.30 else cl[-1].append(b))
    return [ (c[0] + c[-1]) * 0.5 for c in cl ]


# ---------------------------------------------------------------- 切る
def bisect_keep(o, axis_x, keep_ge):
    """x = axis_x の平面で切り、keep_ge なら x ≥ 側を残す。切り口は塞がない。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5,
                           plane_co=Vector((axis_x, 0, 0)), plane_no=Vector((1, 0, 0)),
                           clear_outer=not keep_ge, clear_inner=keep_ge)
    # ⚠ bisect は面を持たない頂点・辺を残す。消さないと bbox が嘘をつく
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return o


def slab(o, x0, x1):
    bisect_keep(o, x0, True)
    bisect_keep(o, x1, False)
    return o


def shift_x(o, dx):
    for v in o.data.vertices:
        v.co.x += dx
    o.data.update()


def dup(o, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name
    bpy.context.collection.objects.link(c)
    return c


# ---------------------------------------------------------------- 割付を解く
def solve(Lm, cap_w, bay, ncap):
    """L[m] から (bay 本数 k, pier の詰め ε) を出す。ε は obj 単位。

        L/ES = ncap·cap_w + k·bay − ε·(k + ncap/2)

    ncap は妻の数(both=2 / left・right=1 / none=0)。継ぎ目 1 箇所につき pier が ε 詰まり、
    妻を出さない端の切り口は半分(ε/2)ぶん詰まる。|ε| が最小になる k を選ぶ。"""
    Lo = Lm / ES
    best = None
    for k in range(0 if ncap == 2 else 1, 400):
        eps = (ncap * cap_w + k * bay - Lo) / (k + ncap / 2.0)
        if eps < EPS_MIN or eps > EPS_MAX:
            continue
        if best is None or abs(eps) < abs(best[1]):
            best = (k, eps)
    if best is None:
        raise SystemExit("[nagaya] L=%.3fm は ends=%d では作れない(短すぎる)。最小はおよそ %.2fm"
                         % (Lm, ncap, ES * (ncap * cap_w + max(1, 1) * bay
                                            - EPS_MAX * (1 + ncap / 2.0))))
    return best


# ---------------------------------------------------------------- 組む
def build(Lm, ends="both", name=None):
    V.reset()
    gc, mc = read_groups("knagaya01c")
    gl, ml = read_groups("knagaya01l")
    gr, mr = read_groups("knagaya01r")
    V.dedup_materials()

    # 寸法は必ずメッシュから測る(素の x とは符号が逆なので決め打ちしない)
    d0, d1 = xspan(gc["n_dodai"])
    W   = d1 - d0                       # 1棟の継ぎピッチ
    bay = W / 3.0                       # 窓ひとつぶん = 割付の単位
    cwin = win_centers(gc["koshi"])[1]  # `c` の真ん中の窓
    # 妻部材: 破風(n_kera_top)がある側が妻。`l` は +x 側、`r` は −x 側(読み込みで X が反転する)
    lk0, lk1 = xspan(gl["n_kera_top"]);  l_gab = lk1
    rk0, rk1 = xspan(gr["n_kera_top"]);  r_gab = rk0
    lwin = max(win_centers(gl["koshi"]))   # 妻に一番近い窓
    rwin = min(win_centers(gr["koshi"]))
    cap_w = (l_gab - lwin) + bay / 2.0     # 妻の外端から継ぎ目までの長さ(ε=0のとき)
    print("[nagaya] 素の実測: 棟 %.5f (%.4fm) / bay %.5f (%.4fm) / 妻 %.5f (%.4fm)"
          % (W, W * ES, bay, bay * ES, cap_w, cap_w * ES))

    ncap = {"both": 2, "left": 1, "right": 1, "none": 0}[ends]
    k, eps = solve(Lm, cap_w, bay, ncap)
    bw = bay - eps
    pier = 0.845 - eps
    print("[nagaya] L=%.3fm → bay %d 本 / pier の詰め ε=%+.4f (%.3fm) → 無地の壁 %.3fm"
          % (Lm, k, eps, eps * ES, pier * ES))
    if pier < 0.30:
        print("[nagaya] ⚠ 無地の壁が %.2fm しか残らない" % (pier * ES))

    pieces = []
    # --- bay(中部材から切り出す): 中央の窓を挟んで対称に
    b0 = cwin - bay / 2.0 + eps / 2.0
    b1 = cwin + bay / 2.0 - eps / 2.0
    bay_src = V.join(mc, "bay_src")
    slab(bay_src, b0, b1)
    for i in range(k):
        c = dup(bay_src, "bay%02d" % i)
        shift_x(c, i * bw - b0)
        pieces.append(c)
    bpy.data.objects.remove(bay_src, do_unlink=True)

    # --- 妻(左 = `r` の妻を −x 側に / 右 = `l` の妻を +x 側に)
    cap_r = V.join(mr, "capL")          # 妻が −x 側にある部材 → 走りの左端
    cap_l = V.join(ml, "capR")          # 妻が +x 側にある部材 → 走りの右端
    xR = rwin + bay / 2.0 - eps / 2.0   # `r` の内側の切断面
    xL = lwin - bay / 2.0 + eps / 2.0   # `l` の内側の切断面
    if ends in ("both", "left"):
        bisect_keep(cap_r, xR, False)   # 妻側(x ≤ xR)を残す
        shift_x(cap_r, -xR)
        pieces.append(cap_r)
    else:
        bpy.data.objects.remove(cap_r, do_unlink=True)
    if ends in ("both", "right"):
        bisect_keep(cap_l, xL, True)
        shift_x(cap_l, k * bw - xL)
        pieces.append(cap_l)
    else:
        bpy.data.objects.remove(cap_l, do_unlink=True)

    o = V.join(pieces, "nagaya")
    # 継ぎ目の頂点を溶かす(隣り合う切り口は平行移動で一致している)
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
    bm.to_mesh(me); bm.free(); me.update()

    # --- 向き: 表(素では +Y)を Blender −Y へ。**回転**で行う(鏡映は巻きが裏返る)
    o.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    # --- 江戸間の実寸(m)へ
    o.data.transform(Matrix.Scale(ES, 4))
    o.data.update()

    # --- ピボット = 走りの中心 / 土台の底 / 壁の外面
    xs = [v.co.x for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    px = (min(xs) + max(xs)) * 0.5
    pz = min(zs)                                   # 土台の底
    py = wall_face_y(o)                            # 壁の外面(= 走りに平行な最も外の大面)
    for v in me.vertices:
        v.co.x -= px; v.co.y -= py; v.co.z -= pz
    me.update()

    ys = [v.co.y for v in me.vertices]
    xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    L_real = max(xs) - min(xs)
    print("[nagaya] 出来上がり(m) W %.3f × H %.3f × D %.3f   軒の出 %.3f / 躯体 %.3f"
          % (L_real, max(zs) - min(zs), max(ys) - min(ys), -min(ys), max(ys)))
    print("[nagaya] 目標 %.3fm との差 %+.4fm  面=%d" % (Lm, L_real - Lm, len(me.polygons)))

    nm = name or ("Nagaya_Omote_" + fmt(Lm) + ("" if ends == "both" else "_" + ends))
    o.name = nm; o.data.name = nm
    path = os.path.join(OUT, nm + ".fbx")
    V.export_fbx([o], path)
    print("[nagaya] wrote %s" % path)
    return o, path, L_real


def wall_face_y(o):
    """壁の外面の y。表側(y の小さいほう)で、走りに平行な大きな面が集まる位置を採る。
    ⚠ 軒(y がさらに外へ出る)を掴まないよう、**面積で重み付けした最頻値**で取る。"""
    from collections import defaultdict
    acc = defaultdict(float)
    for p in o.data.polygons:
        if abs(p.normal.y) < 0.9:
            continue
        y = o.data.vertices[o.data.loops[p.loop_start].vertex_index].co.y
        acc[round(y, 3)] += p.area
    if not acc:
        return min(v.co.y for v in o.data.vertices)
    ys = sorted(acc.items(), key=lambda kv: -kv[1])
    # 表側に面する候補のうち、面積が最大のもの
    front = [y for y, a in ys if a > ys[0][1] * 0.15]
    return min(front)


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


# ---------------------------------------------------------------- テクスチャ / レンダ
def hook():
    for m in bpy.data.materials:
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        b.inputs['Alpha'].default_value = 1.0        # FBX の TransparencyFactor 対策
        b.inputs['Roughness'].default_value = 0.8
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(os.path.join(SRC, "knagaya.jpg"), check_existing=True)
        img.location = (-600, 300)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])


def shots(o, tag):
    hook()
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    L = (mx - mn).x
    os.makedirs(SHOT, exist_ok=True)
    # ① 正面の立面(全長)
    V.studio((c.x, c.y - L, c.z), (c.x, c.y, c.z), ortho_scale=L * 1.08, res=(1900, 700))
    V.render(os.path.join(SHOT, "nagaya_%s_elev.png" % tag))
    # ② 継ぎ目の寄り(左の妻から3本目の継ぎ目あたり)
    xj = mn.x + min(L * 0.5, 9.0)
    V.studio((xj, c.y - 9, mn.z + 2.2), (xj, c.y, mn.z + 2.2), ortho_scale=7.0, res=(1500, 1000))
    V.render(os.path.join(SHOT, "nagaya_%s_joint.png" % tag))
    # ③ 妻(端部)を斜め前から。小口が透けていないかを見る
    V.studio((mn.x - 9.0, c.y - 9.0, mn.z + 5.5), (mn.x + 2.0, c.y + 1.5, mn.z + 2.2), res=(1500, 1000))
    V.render(os.path.join(SHOT, "nagaya_%s_tsuma.png" % tag))
    # ③' 妻を裏(敷地の内側)から。裏の壁と妻の納まりを見る
    V.studio((mn.x - 8.0, c.y + 11.0, mn.z + 5.0), (mn.x + 3.0, c.y + 1.5, mn.z + 2.2), res=(1500, 1000))
    V.render(os.path.join(SHOT, "nagaya_%s_ura.png" % tag))
    # ④ 街路から見た斜め(人の目の高さ)
    V.studio((mn.x - 6.0, c.y - 16.0, 1.7), (c.x, c.y, 2.4), res=(1900, 900))
    V.render(os.path.join(SHOT, "nagaya_%s_street.png" % tag))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    ends = "both"
    if "--ends" in argv:
        ends = argv[argv.index("--ends") + 1]
    name = argv[argv.index("--name") + 1] if "--name" in argv else None
    skip = set()
    for f in ("--ends", "--name"):
        if f in argv:
            skip.add(argv.index(f)); skip.add(argv.index(f) + 1)
    lens = [float(a) for i, a in enumerate(argv)
            if i not in skip and not a.startswith("--")]
    if not lens:
        lens = [28.5]
    for Lm in lens:
        o, path, L_real = build(Lm, ends=ends, name=name)
        if do_render:
            shots(o, fmt(Lm) + ("" if ends == "both" else "_" + ends))


main()
