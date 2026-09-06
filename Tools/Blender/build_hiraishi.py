"""**大型の平石3種**(天井石・伏石・切石橋) — 松江松平上屋敷(matsudaira_dewa)の庭。
ユーザー裁定2=A(2026-09-06)。

    blender --background --python Tools/Blender/build_hiraishi.py -- [Tenjo|Fuse|Ishibashi|all] [--render]

【なぜ新造するか】在庫の岩は在庫索引(`docs/asset-index.tsv`)のとおり `JG_Rock_A_01..03`
  (1.25〜1.99m級の丸い転石)しかなく、①岩屋の脇石2本の上に**架ける**水平な天井石、
  ②築山の裾に**伏せる**扁平な転石、③切石一枚物の橋、のどの形も無い。

【2026-09-06 三度目の差し戻し(天端が鞍型に凹む・胴に継ぎ目線・折れ線が読める)を機に
  天井石・伏石の作り方を全面変更した】旧版(輪切りロフトの bmesh 手続き生成)は
  5回の差し戻しを経てUVの縞は解消したが、**形そのもの**が「パラメトリックな輪切り」
  特有の人工物(バンド境界の継ぎ目・cos(2θ)で作った鞍型の天端)から抜け出せなかった。
  ⭕ **在庫の転石メッシュ `JG_Rock_A_0{1,2,3}_LOD0.fbx`(実肌・`M_FJG_Rock_001` の
  アトラスUVを個体ごとの矩形アイランドとして既に持つ)を土台に、変形で目標寸法へ
  持っていく**方式に切り替えた(規則1のゼロモデリング禁止は在庫にキットがある建築
  部材向けで、庭方が意匠を決めた自然石はこの限りでない — が、そもそも「変形」であって
  「モデリング」ですらない)。
  ・**天井石・伏石** = `JG_Rock_A_03`(実測いちばん扁平)を土台に:
    ①目標外接寸法へ**軸ごとに最大1.25倍**まで直接スケール、
    ②1.25倍で足りない軸だけ、`_soften_stretch()`(閉じた式の非一様な追加伸長 —
    正規化座標 t∈[-1,1] を `T(t) = t + 1.5(k-1)(t - t³/3)` で写す。中央ほど強く
    伸び・両端(丸めた角)付近は元の粗密に近いまま保たれるので、単純な追加スケール
    より角の見え方が破綻しにくい)、
    ③天端の頂が1つになるよう `_nudge_single_peak()` で軽くブレンド(凹みを均す。
    元の造形を壊さない程度の弱いブレンド率)、
    ④UV・マテリアルスロットは**一切触らない**(スケールと座標変形だけなので
    在庫メッシュの UV は無傷 — 材質名だけ `M_FJG_Rock_001` の空の入れ物へ差し替える。
    「Test」のままだと remap が当たらない、立石と同じ理由)。
  ・**切石橋**(加工石)= 引き続き bmesh box + 全辺 1〜2cm 面取り(自然石の割れ肌
    ノイズは掛けない・上面下面小口は平面のまま)— こちらは指摘が無かったので無変更。

【なぜ手続きロフトを諦めたか(旧版の記録として残す)】円筒(角度,高さ)ロフト方式は
  5回の差し戻しでUVの縞(円筒UVと絵柄の方向性の衝突)を解消したが、**形の人工性**
  (バンドの継ぎ目・cos(2θ)の鞍型)までは解消できなかった。実在の岩をベースにする
  今回の方式は、UV(既に自然物として作られたアトラス)も形(既に自然に風化した
  シルエット)も両方まとめて「本物」を引き継ぐので、この手の人工性の罠を原理的に踏まない。
"""
import bpy, bmesh, sys, os, math, random
import mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_tateishi as BT

OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa")
SHOT = os.path.join(V.REPO, "Screenshots")

ROCK_MAT = BT.ROCK_MAT
RECT = BT.RECT
DENS_U = BT.DENS_U
DENS_V = BT.DENS_V
pingpong = BT.pingpong
scale_at = BT.scale_at

# 仕様(ユーザー裁定2=A の表どおり。Unity座標 W(X)×H(Y)×D(Z))。
# ⭐ 2026-09-06 庭方裁定「伏せる石は埋め0」で Fuse の H を 0.42→0.28 に変更
# (見え丈がそのまま全丈になった。0.42のままだと実装側でY0.67倍に潰れ異方比1.50で
# 据わらないと指摘された)。天井石は無変更。
SPEC = {
    "Tenjo": (1.05, 0.45, 0.55),
    "Fuse":  (1.20, 0.28, 0.85),
}
ISHIBASHI_SPEC = (2.20, 0.25, 0.90)   # W, H, D

# 在庫の転石(JG_Rock_A_01..03)— M_FJG_Rock_001 のアトラスUVを個体ごとの矩形
# アイランドとして既に持つ実肌メッシュ。土台にするのは A_03(実測いちばん扁平)。
JG_ROCKS_DIR = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden",
                             "Models", "Misc", "Rocks")
DONOR = {"Tenjo": "FJG_Rock_A_03_LOD0.fbx", "Fuse": "FJG_Rock_A_03_LOD0.fbx"}
STRETCH_CAP = 1.25   # 軸ごとの直接スケールはここまで。超える分だけ低周波の追加伸長で補う


def _load_donor(fname):
    """土台メッシュを1つ読み、複数オブジェクトなら結合して返す。LOD1/2・Collider は除く。

    ⚠ **Blenderへの素の取り込みは「置いた姿」ではない。** `JG_Rock_A_03.prefab` の
    LOD0 は Transform に `localRotation` X軸-90°・`localScale` 0.5一様 を持つ
    (Unity側がこの回転込みで「扁平な転石」として置いている)。Blenderの FBX
    インポートの軸変換は Unity のそれと同一ではない(素の取り込みは丈が高く
    幅と大差ない=扁平に見えない— 実見済み)。⭕ 実測で確認したところ、**Blender側で
    X軸まわりに+90°回す**と実際に「丸い天端・扁平な据わり」の姿になった
    (-90°側は逆に「硬貨のように平たい」姿になり、伏石が求める「ゆるい山」の
    土台に向かない — `rot_posX_persp.png` / `rot_negX_persp.png` で実見比較)。
    Unity 側の数値をそのまま輸入せず、姿で判定したことに注意。"""
    objs = VM.import_fbx_abs(os.path.join(JG_ROCKS_DIR, fname),
                              keep=lambda n: "LOD1" not in n and "LOD2" not in n and "Collider" not in n)
    meshes = [o for o in objs if o.type == 'MESH']
    o = V.join(meshes, "donor") if len(meshes) > 1 else meshes[0]
    R = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    o.data.transform(R)
    # ⚠ `JG_Rock_A_03.prefab` の Transform は姿の回転に加え **一様スケール0.5** も
    # 掛けている。普請奉行の指図(「軸ごとの倍率1.25以内」「x1.45・y0.70・z1.29」)は
    # この 0.5 込みの「カタログ実寸」基準で計算されている — ここで先に 0.5 を掛けて
    # 同じ基準に揃えないと、生メッシュ基準では全軸「縮小」に見えてしまい
    # (縮小自体はUVを歪めないので無害だが)、指図が指定した1.25倍キャップの発動
    # 対象軸がズレる。UVは頂点位置に依らない(スケールでは歪まない)ので、
    # この0.5倍自体はUVに影響しない。
    S = mathutils.Matrix.Scale(0.5, 4)
    o.data.transform(S)
    o.data.update()
    return o


def _soften_stretch(me, axis_idx, lo, hi, k):
    """1.25倍を超える分の追加伸長を、閉じた式の低周波な非一様写像で行う
    (普請奉行裁定: Lattice/Proportional Edit相当 — 中央ほど強く伸び、両端は元の
    粗密に近いまま保たれるので、単純な追加スケールより角の見え方が破綻しにくい)。
    正規化座標 t=(co-center)/half ∈[-1,1] を T(t) = t + 1.5(k-1)(t - t³/3) へ写す。
    T(±1)=±k なので、この軸の全長は呼び出し前のちょうど k 倍になる(閉じた式で
    厳密に校正済み — 反復ソルブ不要)。"""
    center = (lo + hi) * 0.5
    half = max((hi - lo) * 0.5, 1e-9)
    a = 1.5 * (k - 1.0)
    for v in me.vertices:
        t = (v.co[axis_idx] - center) / half
        t2 = t + a * (t - (t ** 3) / 3.0)
        v.co[axis_idx] = center + half * t2


def _nudge_single_peak(me, h, blend=0.35, top_frac=0.35):
    """天端の頂を1つに寄せる軽い整形(普請奉行裁定: 凹ませない・折れ線を残さない)。
    最高点(z最大)の(x,y)を頂として、上位 `top_frac` の高さ帯にある頂点のzを
    「頂からの水平距離に応じた滑らかな減衰」へ `blend` の強さだけ寄せる —
    元の造形を壊さない程度の弱いブレンドに留め、鞍型・複数ピークだけを均す。"""
    verts = list(me.vertices)
    if not verts:
        return
    top_v = max(verts, key=lambda v: v.co.z)
    px, py, pz = top_v.co.x, top_v.co.y, top_v.co.z
    zmin = min(v.co.z for v in verts)
    thresh = zmin + (pz - zmin) * (1.0 - top_frac)
    # 減衰の広がりは石の水平方向の広がりに合わせる(半幅の平均くらい)
    xs = [v.co.x for v in verts]; ys = [v.co.y for v in verts]
    spread = max((max(xs) - min(xs)) + (max(ys) - min(ys)), 1e-6) * 0.5
    for v in verts:
        if v.co.z < thresh:
            continue
        r = math.hypot(v.co.x - px, v.co.y - py)
        target_z = pz - (pz - thresh) * min(r / spread, 1.0)
        v.co.z = v.co.z * (1.0 - blend) + target_z * blend


def build_boulder(kind, i=1):
    """在庫の転石(JG_Rock_A_03)を土台に、目標寸法へ変形して仕立てる。
    ①軸ごとに直接スケール(最大 `STRETCH_CAP`=1.25倍)、②足りない軸だけ
    `_soften_stretch` で低周波の追加伸長、③天端を軽く単峰化、④材質名だけ
    `M_FJG_Rock_001` の空の入れ物に差し替える(元は "Test" — 立石と同じ理由で
    remap が当たらない)。UV・トポロジーは一切変更しない(在庫メッシュのアトラス
    UVをそのまま運ぶ)。"""
    W, H, D = SPEC[kind]   # Unity座標 W(X)×H(Y)×D(Z)
    o = _load_donor(DONOR[kind])

    mn0, mx0 = BT.bounds([o])
    # まず底面中心を原点へ(以降のスケール・伸長がこの基準で効くように)
    o.data.transform(BT.Matrix_translate(-(mn0.x + mx0.x) * 0.5, -(mn0.y + mx0.y) * 0.5, -mn0.z))
    o.data.update()
    mn0, mx0 = BT.bounds([o])
    w0, d0, h0 = mx0.x - mn0.x, mx0.y - mn0.y, mx0.z - mn0.z
    print("[hiraishi] %s 土台実測 W=%.3f D=%.3f H=%.3f" % (kind, w0, d0, h0))

    # ① 軸ごとの直接スケール(最大 STRETCH_CAP)。縮小(比<1)は上限の対象外。
    def _direct_and_extra(target, measured):
        full = target / max(measured, 1e-6)
        direct = min(full, STRETCH_CAP) if full > 1.0 else full
        extra = full / direct if direct > 1e-9 else 1.0
        return direct, extra

    sx, kx = _direct_and_extra(W, w0)
    sy, ky = _direct_and_extra(D, d0)
    sz, kz = _direct_and_extra(H, h0)
    print("[hiraishi] %s 直接スケール x=%.3f y=%.3f z=%.3f / 追加伸長 x=%.3f y=%.3f z=%.3f"
          % (kind, sx, sy, sz, kx, ky, kz))
    o.data.transform(BT.Matrix_scale(sx, sy, sz))
    o.data.update()

    # ② 1.25倍を超える軸だけ低周波の追加伸長(Lattice相当)
    mn1, mx1 = BT.bounds([o])
    if abs(kx - 1.0) > 1e-6:
        _soften_stretch(o.data, 0, mn1.x, mx1.x, kx)
    if abs(ky - 1.0) > 1e-6:
        _soften_stretch(o.data, 1, mn1.y, mx1.y, ky)
    if abs(kz - 1.0) > 1e-6:
        _soften_stretch(o.data, 2, mn1.z, mx1.z, kz)
    o.data.update()

    # ③ 天端の単峰化(軽いブレンド。凹み・折れ線を均す)
    mn2, mx2 = BT.bounds([o])
    _nudge_single_peak(o.data, mx2.z - mn2.z)
    o.data.update()

    # ④ 材質名だけ差し替え(ジオメトリ・UVは無傷)
    mat = BT._borrow_rock_material()
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)

    # 最終的に底面中心・原点へ厳密に合わせ直す(伸長で僅かにズレるため)
    mn3, mx3 = BT.bounds([o])
    o.data.transform(BT.Matrix_translate(-(mn3.x + mx3.x) * 0.5, -(mn3.y + mx3.y) * 0.5, -mn3.z))
    o.data.update()

    o.name = o.data.name = "Hiraishi_%s_%d_LOD0" % (kind, i)
    return o


# ================================================================ 切石橋(加工石)
def gen_ishibashi(seed, w, d, h):
    """加工した一枚岩の橋。箱+全辺の弱い面取り(1〜2cm)。天端・小口は平面のまま、
    側面・小口だけに矢穴跡程度の弱いノイズ(振幅4mm)を乗せる — 自然石の割れ肌ノイズは
    掛けない(加工石なので稜線が素直に通る)。"""
    rng = random.Random(seed)
    uv_rng = random.Random(seed ^ 0x9E3779)
    ou = 0.5 + uv_rng.uniform(-0.10, 0.10)
    ov = 0.5 + uv_rng.uniform(-0.10, 0.10)

    bm = bmesh.new()
    res = bmesh.ops.create_cube(bm, size=1.0)
    verts = res['verts']
    bmesh.ops.scale(bm, verts=verts, vec=(w, d, h))
    bmesh.ops.translate(bm, verts=verts, vec=(0.0, 0.0, h * 0.5))
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=5, use_grid_fill=True)

    radius = rng.uniform(0.010, 0.020)   # 1〜2cm の面取り(規約どおり — 自然石より控えめ)
    edges = [e for e in bm.edges if e.is_valid]
    try:
        bmesh.ops.bevel(bm, geom=edges, offset=radius, offset_type='OFFSET',
                         segments=1, profile=0.5, affect='EDGES', clamp_overlap=True)
    except Exception as exc:
        print("[hiraishi] ishibashi bevel skip: %s" % exc)

    bm.normal_update()
    # 矢穴跡程度の弱いノイズ: 法線が水平に近い(側面・小口)頂点だけ。上面・下面(法線が
    # 鉛直に近い)は完全な平面のまま残す — 「上面は平ら」の指定を崩さないため。
    for v in bm.verts:
        n = v.normal if v.normal.length > 1e-6 else Vector((0, 0, 1))
        if abs(n.z) > 0.5:
            continue
        v.co += n * rng.uniform(-0.004, 0.004)
    BT.ensure_outward(bm)
    bm.normal_update()

    uv_layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        for loop in f.loops:
            co = loop.vert.co
            if ax == 2:
                fu = pingpong(co.x * DENS_U + ou); fv = pingpong(co.y * DENS_V + ov)
            elif ax == 1:
                fu = pingpong(co.x * DENS_U + ou); fv = pingpong(co.z * DENS_V + ov * 0.3)
            else:
                fu = pingpong(co.y * DENS_U + ou); fv = pingpong(co.z * DENS_V + ov * 0.3)
            loop[uv_layer].uv = (RECT[0] + fu * (RECT[2] - RECT[0]), RECT[1] + fv * (RECT[3] - RECT[1]))

    me = bpy.data.meshes.new("Ishibashi_Kiri_1")
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def build_ishibashi():
    w, h, d = ISHIBASHI_SPEC
    me = gen_ishibashi(hash(("ishibashi", 1)) & 0xFFFFFFFF, w, d, h)
    o = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(BT._borrow_rock_material())

    mn, mx = BT.bounds([o])
    sx = w / max(mx.x - mn.x, 1e-6)
    sy = d / max(mx.y - mn.y, 1e-6)
    sz = h / max(mx.z - mn.z, 1e-6)
    o.data.transform(BT.Matrix_scale(sx, sy, sz))
    mn, mx = BT.bounds([o])
    o.data.transform(BT.Matrix_translate(-(mn.x + mx.x) * 0.5, -(mn.y + mx.y) * 0.5, -mn.z))
    o.data.update()
    o.name = o.data.name = "Ishibashi_Kiri_1_LOD0"
    return o


def shots(objs, key, box=None):
    BT.hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box if box else BT.bounds(objs)
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    c = (mn + mx) * 0.5
    S = max(W, H, D)
    # 斜め上30°・石の高さいっぱい(依頼どおり)
    cam_dist = S * 2.4
    cam_z = c.z + math.tan(math.radians(30)) * cam_dist
    V.studio((c.x, mn.y - cam_dist, cam_z), (c.x, c.y, c.z),
             ortho_scale=max(W, H * 1500.0 / 1100, D) * 1.35, res=(1500, 1100))
    V.render(os.path.join(SHOT, "hiraishi_%s_elev30.png" % key))
    V.studio((c.x - S * 0.9, mn.y - S * 1.2, mx.z + S * 0.5), (c.x, c.y, c.z), res=(1500, 1100))
    V.render(os.path.join(SHOT, "hiraishi_%s_3d.png" % key))
    # ⭐ 2026-09-06 差し戻し対応: 「真横」(仰角0°・正面)の近景も追加 — 縁の丸みは
    # 斜め上からだけでなく水平の視線でも滑らかに読めるか確認する(依頼どおり)。
    V.studio((c.x, mn.y - S * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H * 1500.0 / 1100) * 1.15, res=(1500, 1100))
    V.render(os.path.join(SHOT, "hiraishi_%s_yoko.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or ["all"]
    if "all" in want:
        want = ["Tenjo", "Fuse", "Ishibashi"]
    do_render = "--render" in argv

    for kind in want:
        V.reset()
        if kind in SPEC:
            o = build_boulder(kind, 1)
            name = "Hiraishi_%s_1" % kind
        elif kind == "Ishibashi":
            o = build_ishibashi()
            name = "Ishibashi_Kiri_1"
        else:
            print("[hiraishi] ⚠ 知らない種別: %s" % kind); continue

        lod1 = BT.make_lod1(o)
        mn, mx = BT.bounds([o])
        tri0 = sum(len(p.vertices) - 2 for p in o.data.polygons)
        tri1 = sum(len(p.vertices) - 2 for p in lod1.data.polygons)
        print("[hiraishi] %-18s 実寸 W(X)=%.3f H(Z→Y)=%.3f D(Y→Z)=%.3f  "
              "LOD0 %d tri / LOD1 %d tri  材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, tri0, tri1,
                 [s.name for s in o.data.materials]))
        if do_render:
            shots([o], name, box=(mn, mx))
        V.export_fbx([o, lod1], os.path.join(OUT, name + ".fbx"))
        print("[hiraishi] 書き出し " + os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    main()
