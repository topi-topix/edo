"""折れ角のある隅の部材を、在庫のモジュールを**留め(とめ)継ぎ**で起こす。

    留め＝額縁の角と同じ、二材を折れ角の半分ずつ斜めに切って突き合わせる継ぎ方(mitre)。
    こうすると化粧面が角で途切れず、**どんな折れ角でも成立する**。

    blender --background --python Tools/Blender/build_kado.py -- --part ishigaki --deg 31.3
    blender --background --python Tools/Blender/build_kado.py -- --all           # 指図 其十五の3点
    blender --background --python Tools/Blender/build_kado.py -- --part nagaya --deg 38.3 --render
    blender --background --python Tools/Blender/build_kado.py -- --part ishigaki --deg 90 --h 5 --render
        # 丈違い(石垣だけ)。素の 4m の下へ 1m の段を勾配のまま継ぎ足す → Ishigaki_Kado_90_H0500
    blender --background --python Tools/Blender/build_kado.py -- --part ishigaki --deg 90 --h 4 --arms 1.59,2.0 --render
        # 短い腕(石垣だけ)。腕 = 据え点(両腕の控えの線の交点)から腕の先までの走り[m]。
        # 順は (Unity 局所 −Z の腕, +X の腕)。→ Ishigaki_Kado_90_H0400_A159x200(EDO-0430)
        # 腕は負でもよい(P の手前・留めの三角の中で打ち切る)。--arms 2.0,-0.04 → _A200x-4(EDO-0437)

【なぜ要るか】在庫の出隅ブロック `Castle Wall Corner`(2.4m 角)が成立するのは折れ角 Δ≳60°。
  Δ が浅いと片面を合わせても apex が反対側の壁面から `2.4·cosΔ` はみ出す
  (`unity-modular-stonewall/references/case-studies.md` §14)。岡部邸北辺 P[7] の
  Δ=31.3° では 2.05m も外へ飛び出す。長屋(`knagaya01`)には隅部材がそもそも無く、
  現行の作法は「突き合わせて食い込ませる」なので、P[10] の Δ=38.3° では屋根が互いを貫通する
  (ユーザー指摘 2026-08-18 ブックマーク #5/#7)。

【方針】**ゼロから作らない。**(自前の瓦は「ダサい」と却下されている — build_dobei.py の注)
  在庫のモジュールを二本の腕に複製し、角度を二等分する面(留め面)で切って接ぐ。
  彫り・PBR・瓦の実ジオメトリ・マテリアル名がそのまま残るので、直線材と質感が揃う。
  **折れ角は引数**。現地が決めるものなので決め打ちしない(SKILL.md §1)。

【幾何】正規化した Blender 座標で:
    走り(進行方向) = −Y   ／ 躯体・厚み = ∓X   ／ 高さ = +Z   ／ 原点 = 折れ点・足元
  入りの腕は原点から +Y 側にある。出の腕は入りを +Z まわりに Δ 回した向き
  (躯体側 −X が**外**＝出隅になる向き)。
  留め面は入りの腕の向き(+Y)と出の腕の向き(−d_out)の角の二等分 —
  反射で +Y ↔ −d_out が入れ替わる鏡の線は **角度 Δ/2**、したがって面の法線は
      n = (−sin(Δ/2), cos(Δ/2), 0)
  入りの腕は n 側(p·n ≥ 0)を残す。**外面(−X)は折れ点を越えて 2.4·tan(Δ/2) 張り出す** —
  これが出隅の「出」で、ここを削ると角が開く。

【据え(Unity)】ピボット＝折れ点・足元・内面。`Castle Wall` と同じ規約なので
    position = 折れ点 / yaw = **入りの走りの方位** / scale = (s, s, s)
  で置ける。ブロックは入りの run の最後の 1 モジュール `[頂点 − 2.0×s, 頂点]` と、
  出の run の最初の 1 モジュール `[頂点, 頂点 + 2.0×s]` を**兼ねる**。
  → 入りの run は `t1 = L − 2.0×s` で止める。出の run は既定のまま(t0 + 2.0×s から)。

【落とし穴】
  ・反射は右手系を裏返すので、**出の腕は法線を反転**しないと裏面になる。
  ・留め面の切り口は塞がない。両腕の切り口は完全に一致するので、接いで
    merge by distance すれば継ぎ目は消える。塞ぐと壁の中に面が残る。
  ・`bisect` は面を持たない頂点・辺を残す。消さないとバウンズが嘘をつく
    (build_goten_roof.py と同じ罠)。
  ・モジュールごとにピボットの位置が違う(石垣は走りの端、築地塀と長屋は中央)。
    **必ず bbox から正規化する。**決め打ちすると腕が半モジュールずれる。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

FLIP_THK = False        # --flipthk で立てる。書き出し名に T が付く
H_OUT = None            # --h で立てる(石垣だけ)。丈を m で。書き出し名に _H<cm4桁> が付く
ARMS = None             # --arms aZ,aX で立てる(石垣だけ)。腕の長さ m。書き出し名に _A<cm>x<cm> が付く

ROOT = V.REPO
JC   = os.path.join(ROOT, "Assets/Japanese Castle")
VK   = os.path.join(ROOT, "Assets/Japanese Village Kit")
OUT  = V.out_dir(os.path.join(ROOT, "Assets/Edo/Models/Kado"))

# ---------------------------------------------------------------- 部材の定義
# src   … 素にするメッシュ(fbx は kit の Meshes 相対 / obj・自前 fbx は絶対)
# kit   … "JC"(Japanese Castle) / "VK"(Village Kit) / "OBJ"
# axis  … 走り方向の軸(取り込み後の Blender ローカル)。**必ず明示する。**
#         ⚠ 「長いほうが走り」で自動判定すると、軒が躯体より広い塀で**軒を走りと誤判定**する
#            (Tsuijibei2m は 走り 2.000 に対し軒の総幅 2.096。2026-08-18 に実際にやった)。
# origin… 折れ点をどこに取るか。"end"=モジュールの走り方向の端 / "pivot"=素のピボット(0)
#         ★ 塀と長屋は**ピボットが躯体の中に無い**(s_hei_center は走りの端から 0.3445×sx、
#            knagaya01c は奥行 −2.95〜−0.59)。"end" で寄せると直線材の格子から半モジュール
#            ずれ、Unity で頂点に置いたとき 3m 内側へ落ちる(2026-08-18 に実際にやった)。
#            **ピボットを基準に置く部材は "pivot"。**
# thk   … "center"= 厚みの中心を 0 に / "min","max" = その面を 0 に / "keep" = 触らない
#         長屋はピボットが躯体の外にある(奥行 −2.95〜−0.59)。center にすると直線材と
#         奥行がズレて壁面が通らないので **keep**。
# flip  … 厚みを鏡映してから留めるか。**躯体がどちら側に出るかは部材で違う。**
#         Castle Wall は勾配面(=躯体)が Blender +X に来るが、edogoyomi の
#         `s_hei_center` / `knagaya01c` は **−X 側**に来る。揃えないと出隅と入隅が入れ替わる。
#         判定は理屈でなく**据えて数値で取った**(2026-08-19、隣接直線材の外面との差):
#           土塀  flip 有 → in 0.06 / out −0.26 m（flip 無は 0.79 / 0.47）
#           長屋  flip 有 → in 0.00 / out  0.00 m（flip 無は 6.41 / 6.41）
# arms  … 入り側に積むモジュール数(既定 1)。
# pitch … **走り方向の継ぎピッチ**。bbox の長さではない。
#         ⚠ 土塀の組は bbox 3.556 だが継ぎピッチは 1.645(1間)、長屋は bbox 4.454 だが
#            ピッチ 4.296(手組み run の 7.81 ÷ 1.818)。bbox で刻むと**継ぎ目に穴が開く**。
PARTS = {
    "ishigaki": dict(kit="JC",  src="Exterior/Castle Wall.fbx",
                     out="Ishigaki_Kado", axis="y", thk="min", origin="end", pitch=2.0),
    # 城塀からの派生。**シーンの土塀はこれではない**(下の dobei)。単体で使う辺のために残す
    "tsuijibei": dict(kit="OBJ", src=os.path.join(ROOT, "Assets/Edo/Models/Tsuijibei/Tsuijibei2m.fbx"),
                     out="Tsuijibei_Kado", axis="x", thk="center", origin="end", pitch=2.0),
    # ★ 岡部邸の外周の土塀は edogoyomi の `s_hei_center` を**表裏2枚1組**で置いている
    #   (DobeiRun)。隅部材もその組から起こさないと直線材と質感・厚みが揃わない。
    "dobei":    dict(kit="PAIR", src=os.path.join(ROOT, "Assets/edogoyomi/es_dobei/s_hei_center.obj"),
                     out="Dobei_Kado", axis="x", thk="keep", origin="pivot", flip=True, pitch=1.645),
    # ⚠ 90° の出隅で腕の先へ在庫の棟を突き付けるなら build_nagaya_kado.py(帯を pier の芯で折る・腕の長さ可変)。
    #   ここの鏡映の留めは片方の腕の先の位相が素の棟の端と合わない(素の端の無地が 0.571/0.961 と非対称)。
    "nagaya":   dict(kit="OBJ", src=os.path.join(ROOT, "Assets/edogoyomi/es_knagaya/knagaya01c.obj"),
                     out="Nagaya_Kado", axis="x", thk="keep", origin="pivot", flip=True,
                     ridge="n_mune", pitch=4.296),
}


# ---------------------------------------------------------------- 取り込み
def _read(path, split_groups=False):
    before = set(bpy.data.objects)
    if path.lower().endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=path, forward_axis='Z', up_axis='Y',
                              use_split_groups=split_groups)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    V.sel(meshes)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return meshes


def load_pair(path):
    """`s_hei_center` の**表裏2枚1組**を1つのメッシュにする。
    DobeiRun と同じ関係で置く: 裏は 180° 回して 走りへ +0.956 / 法線へ −0.2。
    ⚠ 素は片面だけの模型なので、1枚だけ留めで切ると中が抜けて見える。
       **必ず組にしてから切る。**(build_dobei.py の注)"""
    f = V.join(_read(path), "dobei_f")
    b = V.join(_read(path), "dobei_b")
    # 走り = ローカル X(bbox から確認)、法線 = ローカル Y、高さ = Z
    b.rotation_euler = (0.0, 0.0, math.pi)
    V.sel([b]); bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    b.location = (0.956, -0.2, 0.0)
    V.sel([b]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.dedup_materials()
    return V.join([f, b], "src")


def load(part):
    """素のモジュールを1つのメッシュとして読む。戻り値 (本体, 棟の雛形 or None)。

    棟(`n_mune`)は**隅棟に流用する**ので、join する前に複製を1つ取り置く。
    .obj は既定で1オブジェクトに潰れるので `use_split_groups=True` で群に割る。"""
    p = PARTS[part]
    if p["kit"] == "PAIR":
        return load_pair(p["src"]), None
    if p["kit"] == "OBJ":
        meshes = _read(p["src"], split_groups=p.get("ridge") is not None)
        mune = None
        if p.get("ridge"):
            for o in meshes:
                if o.name.startswith(p["ridge"]):
                    mune = o.copy(); mune.data = o.data.copy()
                    bpy.context.collection.objects.link(mune); mune.name = "mune_tpl"
                    break
        return V.join(meshes, "src"), mune
    V.MESH = os.path.join(JC if p["kit"] == "JC" else VK, "Meshes")
    V.TEX  = os.path.join(JC if p["kit"] == "JC" else VK, "Textures")
    return V.join(V.imp(p["src"]), "src"), None


def normalize(o, part, extras=None):
    """走り = −Y ／ 高さ = +Z ／ 足元 z=0 ／ **折れ点(＝走りの先端・内面)が原点**
    になるよう平行移動する。

    走り軸・厚み軸は bbox の辺の長さから決める。石垣は 2.4(厚) × 2.0(走) × 4.0(高)、
    築地塀・長屋は走りが最長辺。厚みの向きは、**内面(＝ピボットが乗る面)が x=0** に
    来るように取る。石垣は内面が片側に寄っており、塀・長屋は芯対称なので中央を 0 にする。
    """
    me = o.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    bb = ((min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs)))
    ex = [b[1] - b[0] for b in bb]
    print("[kado] %s 素の bbox x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]"
          % (part, bb[0][0], bb[0][1], bb[1][0], bb[1][1], bb[2][0], bb[2][1]))

    # 高さは常に +Z(Y-up→Z-up 変換済み)。走りは**定義で明示する**(自動判定は軒に騙される)
    run_axis = 0 if PARTS[part]["axis"] == "x" else 1
    thk_axis = 1 - run_axis
    print("[kado] 走り軸=%s(%.3f)  厚み軸=%s(%.3f)  高さ=%.3f"
          % ("xy"[run_axis], ex[run_axis], "xy"[thk_axis], ex[thk_axis], ex[2]))

    extras = [e for e in (extras or []) if e is not None]
    # 走りを +Y、厚みを X へ入れ替える(必要なら)
    if run_axis == 0:
        for mm in [me] + [e.data for e in extras]:
            for v in mm.vertices:
                v.co.x, v.co.y = v.co.y, v.co.x
            for p in mm.polygons:
                p.flip()                   # 軸の入れ替えは鏡映なので巻きが裏返る
        bb = ((bb[1][0], bb[1][1]), (bb[0][0], bb[0][1]), bb[2])
    # 走り: 折れ点を y=0 に。"end" は bbox の手前端、"pivot" は素の原点をそのまま使う
    run = bb[1][1] - bb[1][0]
    dy = -bb[1][0] if PARTS[part].get("origin", "end") == "end" else 0.0
    # 厚み。石垣は内面(ピボットの乗る面)を x=0 に、躯体を +X に。
    #   ⚠ Unity ローカルは X∈[-2.40,0] だが、Y-up→Z-up の取り込みで **X が反転**するので
    #     Blender では x∈[0,2.40]。内面は **min 側**。max 側で寄せると躯体が裏返り、
    #     出隅が入隅になる(2026-08-18 に実際にやった)。
    mode = PARTS[part]["thk"]
    dx = {"min": -bb[0][0], "max": -bb[0][1],
          "center": -(bb[0][0] + bb[0][1]) * 0.5, "keep": 0.0}[mode]
    dz = -bb[2][0]
    for mm in [me] + [e.data for e in extras]:
        for v in mm.vertices:
            v.co.x += dx; v.co.y += dy; v.co.z += dz
    if FLIP_THK or PARTS[part].get("flip", False):
        # 厚みを鏡映して巻きを直す。**躯体が Blender −X 側にある部材**を +X 規約へ揃えるため。
        # どちら側かは部材で違い(石垣は勾配面が外、長屋は躯体が内)、
        # 据えて数値で当たりを取るのが確実なので、両方を書き出して Unity 側で選ぶ。
        for mm in [me] + [e.data for e in extras]:
            for v in mm.vertices:
                v.co.x = -v.co.x
            for p2 in mm.polygons:
                p2.flip()
    me.update()
    for e in extras:
        e.data.update()
    return run


# ---------------------------------------------------------------- 丈の継ぎ足し(石垣)
BATTER_ISHIGAKI = 0.25   # Castle Wall の勾配。1m 下がるごとに面が 0.25 外へ出る(x + 0.25·z = 2.4)
COURSE_ISHIGAKI = 1.0    # 素の Castle Wall は 1m ごとに輪切りの辺がある(4 段)


def extend_down(o, h):
    """石垣の丈を **下へ** 伸ばす。天端(1.4m 幅・面の通り)は素のまま動かさない。

    素の最下段(z∈[0,1])を複製して下へ積み、**勾配の面に載る頂点だけ**を段ごとに 0.25 外へ出す。
    ⭐ 面は一枚の平面(x + 0.25·z = 2.4)なので、こうすれば勾配がそのまま下へ続く。
      背(x=0)と小口の縦の辺(x=1.4)は動かさない ⇒ 小口は x∈[0, 面] の平面のまま閉じる。
    ⛔ z を引き伸ばさない(石の目が縦に伸びる)。段は丸ごと 1m で足す ⇒ 丈は 4+k m。
    UV は最下段のものをそのまま使う(同じ段の石が繰り返す。直線材の段と同じ見え)。"""
    k = int(round(h - 4.0))
    if k <= 0:
        return o
    me = o.data
    face = lambda v: abs(v.co.x + BATTER_ISHIGAKI * v.co.z - 2.4) < 1e-3 and v.co.x > 1e-3
    # 最下段だけを切り出す
    band = o.copy(); band.data = me.copy()
    bpy.context.collection.objects.link(band)
    bm = bmesh.new(); bm.from_mesh(band.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector((0, 0, COURSE_ISHIGAKI)), plane_no=Vector((0, 0, 1)),
                           clear_outer=True, clear_inner=False)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(band.data); bm.free()
    onface = [face(v) for v in band.data.vertices]
    # 素の本体を k 段ぶん上げる
    for v in me.vertices:
        v.co.z += k * COURSE_ISHIGAKI
    me.update()
    parts = [o]
    for j in range(k):                       # j=0 が本体の直下
        c = band.copy(); c.data = band.data.copy()
        bpy.context.collection.objects.link(c)
        dz = (k - 1 - j) * COURSE_ISHIGAKI
        dx = (j + 1) * BATTER_ISHIGAKI * COURSE_ISHIGAKI
        for v, f in zip(c.data.vertices, onface):
            v.co.z += dz
            if f:
                v.co.x += dx
        c.data.update()
        parts.append(c)
    bpy.data.objects.remove(band, do_unlink=True)
    o = V.join(parts, o.name)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    zs = [v.co.z for v in o.data.vertices]; xs = [v.co.x for v in o.data.vertices]
    print("[kado] 丈を %d 段継ぎ足した: z[%.2f,%.2f] 面の足 x=%.3f" % (k, min(zs), max(zs), max(xs)))
    return o


# ---------------------------------------------------------------- 留め(mitre)
def tile(o, pitch, n_pos, n_neg):
    """走り方向に **継ぎピッチ** で複製して腕を伸ばす。y ∈ [−n_neg·pitch, +n_pos·pitch]。"""
    outs = [o]
    for k in list(range(1, n_pos)) + [-(i + 1) for i in range(n_neg)]:
        c = o.copy(); c.data = o.data.copy()
        bpy.context.collection.objects.link(c)
        c.location.y += k * pitch
        outs.append(c)
    V.sel(outs)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return V.join(outs, "armA")


def bisect_keep(o, n, keep_positive=True):
    """平面(原点を通り法線 n)で切り、片側だけ残す。切り口は塞がない。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5,
                           plane_co=Vector((0, 0, 0)), plane_no=Vector(n),
                           clear_outer=not keep_positive, clear_inner=keep_positive)
    # ⚠ bisect は面を持たない頂点・辺を残す。消さないとバウンズが嘘をつく
    loose_e = [e for e in bm.edges if not e.link_faces]
    bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
    loose_v = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose_v, context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return o


def mirror_across(o, n):
    """原点を通り法線 n の面で鏡映した複製を返す。**法線が裏返るので巻きも直す。**"""
    c = o.copy(); c.data = o.data.copy()
    bpy.context.collection.objects.link(c)
    nx, ny, nz = n
    # 反射行列 I − 2·n·nᵀ
    R = Matrix(((1 - 2 * nx * nx, -2 * nx * ny, -2 * nx * nz, 0),
                (-2 * ny * nx, 1 - 2 * ny * ny, -2 * ny * nz, 0),
                (-2 * nz * nx, -2 * nz * ny, 1 - 2 * nz * nz, 0),
                (0, 0, 0, 1)))
    c.data.transform(R)
    for p in c.data.polygons:
        p.flip()
    c.data.update()
    return c



def hip_ridge(body, mune, n):
    """留め面に沿って**隅棟**を通す。

    留めで折った屋根は、折れの外側で二つの流れが尾根を作る(＝隅棟)。素の突き合わせでは
    そこが「切り口の線」でしかないので、**棟の材をその線に沿わせて**継ぐ。
    自前の断面は作らない — `n_mune` をそのまま回して伸ばす(瓦は実ジオメトリのまま)。

    隅棟の線は留め面の中にあり、**大棟の頂点から軒の隅へ**下る直線。両端は接合後の
    メッシュから拾う: 留め面の近傍(|p·n|<0.06)の頂点のうち
      ・最も高い点          = 大棟が留め面と交わる所(起点)
      ・凸側の最も外の点    = 軒の隅(終点)
    凸側は材が延びる側、すなわち x·nx > 0 の側。"""
    import mathutils
    nx, ny = n[0], n[1]
    top = None; out = None; bestx = -1e9
    for v in body.data.vertices:
        if abs(v.co.x * nx + v.co.y * ny) > 0.06:
            continue
        if top is None or v.co.z > top.z:
            top = v.co.copy()
        proj = v.co.x * nx                      # 凸側で正
        if proj > bestx:
            bestx = proj; out = v.co.copy()
    if top is None or out is None or (out - top).length < 0.3:
        print("[kado] ⚠ 隅棟の線が取れなかった(留め面の頂点が足りない)")
        return None
    seg = out - top
    # 棟の雛形: 走り +Y に伸びた材。長さを隅棟の実長へ、向きを seg へ合わせる
    ys = [v.co.y for v in mune.data.vertices]
    L0 = max(ys) - min(ys)
    if L0 < 1e-4:
        return None
    c = mune.copy(); c.data = mune.data.copy()
    bpy.context.collection.objects.link(c)
    # 雛形を原点そろえ(走りの中央・棟の天端を基準にせず、まず min を 0 へ)
    dy = -min(ys)
    zs = [v.co.z for v in c.data.vertices]; xs = [v.co.x for v in c.data.vertices]
    cx = (min(xs) + max(xs)) * 0.5; ztop = max(zs)
    for v in c.data.vertices:
        v.co.x -= cx; v.co.y += dy; v.co.z -= ztop
    # 走り方向へ実長ぶん伸ばし、+Y を seg の向きへ回す
    k = seg.length / L0
    for v in c.data.vertices:
        v.co.y *= k
    q = mathutils.Vector((0.0, 1.0, 0.0)).rotation_difference(seg.normalized())
    c.data.transform(q.to_matrix().to_4x4())
    c.location = top
    V.sel([c]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    c.name = "hip"
    print("[kado]   隅棟 実長 %.3f m (雛形 %.3f を %.2f 倍)  起点 z=%.2f → 終点 z=%.2f"
          % (seg.length, L0, k, top.z, out.z))
    return c

def _dup(o, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name
    bpy.context.collection.objects.link(c)
    return c


def shorten_arm(o, a, y_end, n=None):
    """入りの腕(+Y へ延びる)を y = a で切り、素の小口(y = y_end・法線 +Y の面)を切り口へ移して塞ぐ。
    ⛔ 頂点を寄せて縮めない(面の石の柄が走りに潰れる)。bisect は面の UV を補間するので柄は切れるだけ。

    a ≤ 0(腕が据え点 P の手前で終わる ── 腕が留めの三角の中で打ち切られる)も切れる(2026-09-26 EDO-0437・
    御供所の郭 EK の腕 −0.04)。そのとき:
      ① 移した小口を留め面 n で切り、この腕の側(s·x + c·y ≥ 0)だけ残す(= この腕のその位置の断面)。
      ② 小口の残りの帯(x ∈ [0, −a·c/s] ── 背の側)を留め面へ移して貼る。もう一方の腕の留め面のうち
         この腕が退いた所が開くので、それを塞ぐ面(もう一方の腕の体の外へ向く)。小口の柄を背の側で使う。"""
    if a >= y_end - 1e-6:
        return o
    if n is None and a <= 0.05:
        raise SystemExit("[kado] ⛔ 腕 %.3f が短すぎる" % a)
    if n is not None and a <= -1.0:
        raise SystemExit("[kado] ⛔ 腕 %.3f は留めの三角を越える" % a)
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bm.normal_update()
    cap = [f for f in bm.faces if f.normal.y > 0.99 and abs(f.calc_center_median().y - y_end) < 1e-4]
    if not cap:
        raise SystemExit("[kado] ⛔ 腕の先の小口が見つからない")
    capgeo = bmesh.ops.duplicate(bm, geom=cap)
    capv = [e for e in capgeo["geom"] if isinstance(e, bmesh.types.BMVert)]
    capf = set(e for e in capgeo["geom"] if isinstance(e, bmesh.types.BMFace))
    for v in capv:
        v.co.y = a
    strip_f = []
    if n is not None and a < 0.0:
        sn, cn = n[0], n[1]
        xb = -a * cn / sn                      # 小口が留め面と交わる控えの位置(背 x=0 から)
        sg = bmesh.ops.duplicate(bm, geom=list(capf))
        sv = [e for e in sg["geom"] if isinstance(e, bmesh.types.BMVert)]
        sf = [e for e in sg["geom"] if isinstance(e, bmesh.types.BMFace)]
        # 帯 = 小口の x ≤ xb の側(背の側)
        r = bmesh.ops.bisect_plane(bm, geom=sv + sf + list(set(ed for f in sf for ed in f.edges)), dist=1e-6,
                                   plane_co=Vector((xb, a, 0)), plane_no=Vector((1, 0, 0)),
                                   clear_outer=True, clear_inner=False)
        strip_f = [f for f in bm.faces if f.is_valid and all(abs(v.co.y - a) < 1e-6 for v in f.verts)
                   and all(v.co.x <= xb + 1e-6 for v in f.verts) and f not in capf]
        # 小口の本体は留め面の手前(x ≥ xb)だけ残す
        capf = set(f for f in capf if f.is_valid)
        cv = list(set(v for f in capf for v in f.verts))
        bmesh.ops.bisect_plane(bm, geom=cv + list(capf) + list(set(ed for f in capf for ed in f.edges)), dist=1e-6,
                               plane_co=Vector((xb, a, 0)), plane_no=Vector((1, 0, 0)),
                               clear_outer=False, clear_inner=True)
        capf = set(f for f in bm.faces if f.is_valid and all(abs(v.co.y - a) < 1e-6 for v in f.verts)
                   and all(v.co.x >= xb - 1e-6 for v in f.verts) and f not in set(strip_f))
        # 帯を留め面へ剪断で移す(y = −x·s/c)
        svs = set(v for f in strip_f for v in f.verts)
        for v in svs:
            v.co.y = -v.co.x * sn / cn
        capv = list(set(v for f in capf for v in f.verts) | svs)
        capf = capf | set(strip_f)
    others = [e for e in bm.verts[:] + bm.edges[:] + bm.faces[:]
              if not (isinstance(e, bmesh.types.BMFace) and e in capf)
              and not (isinstance(e, bmesh.types.BMVert) and e in set(capv))
              and not (isinstance(e, bmesh.types.BMEdge) and all(v in set(capv) for v in e.verts))]
    bmesh.ops.bisect_plane(bm, geom=others, dist=1e-6, plane_co=Vector((0, a, 0)), plane_no=Vector((0, 1, 0)),
                           clear_outer=True, clear_inner=False)
    if strip_f:
        # 帯の向き: もう一方の腕の体(留め面の正の側 ── 鏡に映すとこの腕が負の側へ行き、帯は正の側の体の外皮)
        # の外 = −n へ向ける。鏡映で巻きが裏返るので、ここでは +n へ向けておく。
        bm.normal_update()
        for f in strip_f:
            if f.is_valid and f.normal.dot(Vector(n)) < 0:
                f.normal_flip()
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(me); bm.free(); me.update()
    ys = [v.co.y for v in me.vertices]
    print("[kado]   腕を %.3f で切った(素の先 %.3f)。y 最大 %.4f" % (a, y_end, max(ys)))
    return o


def asuf():
    """腕の接尾辞。(−Z の腕, +X の腕)を cm で。既定(両腕とも 1 モジュール)は付けない。"""
    return "" if ARMS is None else "_A%dx%d" % (int(round(ARMS[0] * 100)), int(round(ARMS[1] * 100)))


def build(part, deg, arms=None):
    p = PARTS[part]
    V.reset()
    o, mune = load(part)
    run = normalize(o, part, [mune])
    if H_OUT is not None:
        if part != "ishigaki":
            raise SystemExit("[kado] --h は石垣だけ")
        o = extend_down(o, H_OUT)
    pitch = p["pitch"]
    # 腕は**片側 1 モジュール**。こうすると隅部材が直線材ちょうど 1 枚の置き換えになり、
    # 入りの run は `t1 = L − 1モジュール`、出の run は `t0 = 1モジュール` で済む。
    # 張り出し(留めの「出」)ぶんに反対側へもう 1 モジュール積んでから切る。
    n_pos = arms if arms else PARTS[part].get("arms", 1)
    n_neg = 1
    # 出隅の張り出しは 厚み·tan(Δ/2)。Δ=90° の石垣では 2.4〜2.65m で 1 モジュール(2.0)を越える
    #   ⇒ 張り出しを覆えるまで −Y に積む(2026-09-25 実測。足りないと隅の足に穴が開く)
    _xmax = max(v.co.x for v in o.data.vertices)
    while n_neg * pitch < _xmax * math.tan(math.radians(abs(deg)) * 0.5) + 0.05:
        n_neg += 1
    # ★ origin="pivot" の部材は、ピボットが走りの端に寄っているので **+Y 側が 1 モジュールに
    #   足りない**ことがある(長屋は y が 2.04 までしか無く、留めで切ると腕が半分になった。
    #   2026-08-20 実測)。1 モジュールぶん覆えるまで +Y に積む。
    if PARTS[part].get("origin", "end") == "pivot":
        ymax = max(v.co.y for v in o.data.vertices)
        while ymax + (n_pos - 1) * pitch < pitch * 1.2:
            n_pos += 1

    # 留め面の法線。躯体(＝化粧面)は +X 側にあるので、そちらが**外**になる向きに折る。
    #   Unity へ渡ると X が反転するので、この n は「Unity で yaw が **+deg** 増える折れ」に対応する。
    #   deg を負にすると鏡像(yaw が減る折れ)の部材が出る。P[7] は +31.3 / P[10] は −38.3。
    half = math.radians(abs(deg)) * 0.5
    n = (math.copysign(math.sin(half), deg), math.cos(half), 0.0)

    # 入りの腕: +Y 側に n_pos モジュール、加えて出隅の張り出しぶんを −Y 側に 1 モジュール
    armA = tile(o, pitch, n_pos, n_neg)
    armA = bisect_keep(armA, n, keep_positive=True)
    if ARMS is None:
        armB = mirror_across(armA, n)
    else:
        # 短い腕(EDO-0430): 腕ごとに走りに直角な面で切り、素の小口(y = n_pos·pitch の面)を切り口へ移して塞ぐ。
        #   ⭐ 断面は走りに沿って一定なので、素の小口がそのまま切り口の形になる(UV も素の小口のまま)。
        #   armB は armA の鏡なので、長さ aX で切った armA の複製を鏡に映す。
        if part != "ishigaki":
            raise SystemExit("[kado] --arms は石垣だけ")
        full = armA
        armA = shorten_arm(_dup(full, "armA_s"), ARMS[0], n_pos * pitch, n)
        armB = mirror_across(shorten_arm(_dup(full, "armB_s"), ARMS[1], n_pos * pitch, n), n)
        bpy.data.objects.remove(full, do_unlink=True)
    o = V.join([armA, armB], "%s_%02d%s%s%s" % (p["out"], round(abs(deg)), "" if deg > 0 else "M", "T" if FLIP_THK else "", hsuf() + asuf()))
    if mune is not None:
        hip = hip_ridge(o, mune, n)
        bpy.data.objects.remove(mune, do_unlink=True)
        if hip is not None:
            o = V.join([o, hip], o.name)

    # 継ぎ目の頂点を溶かす(両腕の切り口は完全に一致している)
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    if ARMS is not None and min(ARMS) < 0.0:
        # 腕が留めの三角の中で終わると、もう一方の腕の天端の留めの辺の途中に切り口の角が乗る(T 字)。
        #   その辺を角で割って継ぐ(割らないと天端の留めに開いた辺が 3 本残る。2026-09-26 実測)
        for _ in range(8):
            done = False
            bnd = [e for e in bm.edges if e.is_boundary]
            bv = set(v for e in bnd for v in e.verts)
            for e in bnd:
                a0, a1 = e.verts[0].co, e.verts[1].co
                d = a1 - a0; L2 = d.length_squared
                for v in bv:
                    if v in e.verts:
                        continue
                    t = (v.co - a0).dot(d) / L2
                    if 1e-4 < t < 1 - 1e-4 and (a0 + d * t - v.co).length < 1e-5:
                        ne, nv = bmesh.utils.edge_split(e, e.verts[0], t)
                        nv.co = v.co.copy()
                        done = True
                        break
                if done:
                    break
            if not done:
                break
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me); bm.free(); me.update()

    V.set_origin(o, (0, 0, 0))
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    print("[kado] %s Δ=%.1f°  出来上がり x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]  面=%d"
          % (p["out"], deg, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), len(me.polygons)))
    print("[kado]   外面の張り出し(折れ点より先) = %.3f m" % max(0.0, -min(ys)))

    hand = ("" if deg > 0 else "M") + ("T" if FLIP_THK else "")
    path = os.path.join(OUT, "%s_%02d%s%s.fbx" % (p["out"], round(abs(deg)), hand, hsuf() + asuf()))
    V.export_fbx([o], path)
    print("[kado] wrote %s" % path)
    return o, path


def hsuf():
    """丈の接尾辞。cm の 4 桁(`Sanno_Nozura_H0150` と同じ書き方)。⚠ int() でなく round()。"""
    return "" if H_OUT is None else "_H%04d" % int(round(H_OUT * 100))


def main():
    global FLIP_THK, H_OUT, ARMS
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    FLIP_THK = "--flipthk" in argv
    if "--h" in argv:
        H_OUT = float(argv[argv.index("--h") + 1])
    if "--arms" in argv:
        ARMS = tuple(float(t) for t in argv[argv.index("--arms") + 1].split(","))
        assert len(ARMS) == 2, "--arms aZ,aX"
    jobs = []
    if "--all" in argv:
        jobs = [("ishigaki", 31.3), ("dobei", 31.3), ("nagaya", -38.3)]
    else:
        part = argv[argv.index("--part") + 1] if "--part" in argv else "ishigaki"
        deg = float(argv[argv.index("--deg") + 1]) if "--deg" in argv else 31.3
        jobs = [(part, deg)]

    for part, deg in jobs:
        o, path = build(part, deg)
        if do_render:
            V.hook_textures()
            mn, mx = V.bbox([o])
            c = (mn + mx) * 0.5
            r = max((mx - mn).x, (mx - mn).y) * 1.4
            V.studio((c.x + r, c.y - r, c.z + r * 0.9), (c.x, c.y, c.z), res=(1400, 900))
            # ⚠ 鏡像(M)は同じ |deg| なので、hand を名に入れないと非鏡像の検証画像を上書きする
            hand = "" if deg > 0 else "M"
            V.render(os.path.join(ROOT, "Screenshots",
                                  "kado_%s_%02d%s%s.png" % (part, round(abs(deg)), hand, hsuf() + asuf())))


main()
