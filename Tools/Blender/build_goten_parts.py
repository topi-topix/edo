"""御殿の躯体部材を Village Kit から江戸間で起こして FBX へ書き出す。

    blender --background --python Tools/Blender/build_goten_parts.py
    # 一部だけ作り直す(既存 FBX を無用に触らない)
    GOTEN_ONLY=Koran blender --background --python Tools/Blender/build_goten_parts.py

規約(Unity 側の座標で言う):
  幅 = X / 高さ = Y / 厚み = Z、**表(入側から見える面) = +Z**(Village Kit の facade 規約と同じ)
  ピボット = 一間の中心・床レベル(X中央, Y=床面, Z=柱心)
  マテリアル名は Village Kit のまま(wall C / door wall / wood ...)。
  Unity 側で Search&Remap すれば既存の .mat がそのまま当たる。
"""
import bpy, sys, os, math, mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

K = V.KEN
OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Goten", "Parts")
PREVIEW = os.environ.get("GOTEN_PREVIEW", "")
ONLY = os.environ.get("GOTEN_ONLY", "")     # 部分文字列で絞る
ENITA_T = 0.0303                            # 渡廊下の縁板の厚[m] = 1寸(縁の下の下限からの上限内)

# 部材名 -> (組み立て関数, 説明)
BUILT = []


def skip(name):
    return bool(ONLY) and ONLY not in name


def finish(objs, name, pivot):
    if skip(name):
        return None
    V.dedup_materials()
    o = V.join(objs, name)
    if o is None:
        print("FAIL", name); return None
    V.set_origin(o, pivot)
    mn, mx = V.bbox([o])
    V.export_fbx(o, os.path.join(OUT, name + ".fbx"))
    print("PART %-26s %6.3f x %6.3f x %6.3f  tris=%d  mats=%s"
          % (name, mx.x - mn.x, mx.y - mn.y, mx.z - mn.z,
             sum(len(p.vertices) - 2 for p in o.data.polygons),
             [m.name for m in o.data.materials]))
    BUILT.append(name)
    return o


def build_all():
    made = []

    # --- 建具・壁(幅を X に、面を XZ 平面に。回転90°) ---
    for name, src in [("Goten_Shoji_1ken",        "Walls and floors/door wall A.fbx"),
                      ("Goten_ShojiHalf",         "Walls and floors/door wall.fbx"),
                      ("Goten_WallPlaster_1ken",  "Walls and floors/wall C.fbx"),
                      ("Goten_WallRenji_1ken",    "Walls and floors/wall C window.fbx")]:
        V.reset()
        objs = V.place(src, 0, 0, 0, rot=90)
        mn, mx = V.bbox(objs)
        made.append(finish(objs, name, ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0)))

    # --- 柱 ---
    V.reset()
    objs = V.place("Walls and floors/column A.fbx", 0, 0, 0)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_Column", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0)))

    # --- 梁(一間) ---
    V.reset()
    objs = V.place("Walls and floors/beam.fbx", 0, 0, 0, rot=90)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_Beam_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0)))

    # --- 畳 一間角 = 江戸間の畳2枚 ---
    V.reset()
    objs = []
    for i in range(2):
        objs += V.place("Walls and floors/tatami.fbx", i * (K / 2), 0, 0)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_Tatami_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0)))

    # --- 入側の板敷き 一間角 ---
    V.reset()
    objs = []
    for i in range(2):
        for j in range(2):
            objs += V.place("Walls and floors/floor.fbx", i * (K / 2), j * (K / 2), 0)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_FloorBoard_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0)))

    # --- 天井 一間角(ceiling.fbx は 2間角なので 2X2 の方を使う) ---
    V.reset()
    objs = V.place("Walls and floors/ceiling 2X2.fbx", 0, 0, 0)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_Ceiling_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mx.z)))

    # --- 濡縁(高欄つき) ---
    # ⚠ balcony A は 高欄が y≈0.045(bbox の最小側)・床板が y=0..0.891 に付いている。
    #   素直に置くと **高欄が建物側に立ち、床板 0.89m が高欄の外へ張り出す**。
    #   ユーザー指摘(bookmark 2026-08-15 #1「手すりの外の部分はなんでしょうか。不要に思えます」)。
    #   rot=180 で向きを反転し、高欄が濡縁の外縁に立つようにする(ピボットは建物側のまま)。
    V.reset()
    objs = V.place("Balcony/balcony A.fbx", 0, 0, 0, rot=180)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_Nureen_1ken", ((mn.x + mx.x) / 2, mn.y, 0.0)))

    # --- 濡縁の入隅(半間角・高欄が二面に回る) ---
    # 桁行の帯(z=0/D)と妻側の帯(x=0/W)は隅に 0.891 角の升目を残す。埋めないと
    # 高欄が隅で切れる(濡縁を反転して高欄を外縁へ出した副作用)。
    # ローカル: x 0..0.891 / 奥行 0.891、高欄は **+X 面と -Z 面**(Unity)の二辺。
    # ピボットは建物側の隅 = (0,0,0)。Unity 側は yaw 0/90/180/270 で四隅へ回す。
    V.reset()
    objs = V.place("Balcony/balcony A.fbx", 0, 0, 0, rot=180)
    mn, mx = V.bbox(objs)
    d = mx.y - mn.y                                   # 濡縁の出 = 0.891
    V.sel(objs)
    bpy.ops.transform.resize(value=(d / (mx.x - mn.x), 1.0, 1.0), center_override=(0, 0, 0))
    bpy.ops.object.transform_apply(scale=True)
    rails = [o for o in objs if V.bbox([o])[0].z > 0.1]   # 床板でない方 = 高欄
    c = mathutils.Vector((d / 2.0, d / 2.0, 0.0))
    R = (mathutils.Matrix.Translation(c)
         @ mathutils.Matrix.Rotation(math.radians(-90), 4, 'Z')
         @ mathutils.Matrix.Translation(-c))
    for o in list(rails):
        q = o.copy(); q.data = o.data.copy()
        bpy.context.scene.collection.objects.link(q)
        q.matrix_world = R @ o.matrix_world
        objs.append(q)
    made.append(finish(objs, "Goten_NureenCorner", (0.0, 0.0, 0.0)))

    # --- 渡廊下の縁板 一間角(厚 1寸 = 0.0303)------------------------------
    # ⭐⭐ **`Goten_FloorBoard_1ken`(キット floor.fbx そのまま・厚 0.0636)とは別部材。**
    #   ⛔ 既存の板を置き換えない(入側の板敷きとして他邸が使っている)。
    # 【なぜ要るか】渡廊下の床は落縁(=濡縁)の天端へ継ぐ(指図 `roka.floorFrom` = nureen)。
    #   その面は `const.gotenFloor` 0.62 − `EdoGotenKit.NUREEN_DROP` 0.28 = **0.34**(地盤から)で、
    #   縁の下(縁板の下端〜地盤)は `roka.ennoshitaMin` **0.303** 以上でなければならない
    #   ⇒ **板厚は 0.037 以下**。キットの 0.0636 では縁の下 0.276 で **27mm 割る**
    #   (2026-09-20 部材方の実測 → 普請奉行の発注)。1寸 0.0303 なら縁の下 **0.3097**。
    # ⚠⚠ **ピボットの z=0 は「板の天端」**(⛔ `Goten_FloorBoard_1ken` は z=0 が**底**)。
    #   廊下の床は**面で**落縁へ継ぐので、天端を床の高さへ置ければ厚は下へ逃げる。
    #   ⇒ 据えるのは `new Vector3(x, floor, z)` のまま(`EdoGotenKit.Roka` の Put と同じ)。
    # ⭕ 形は**キットの床板を薄くしただけ**(板目のテクスチャと材質名 `floor` を保つ)。
    #   ⛔ 自前の箱に差し替えない — 木理が板の長手へ流れなくなる。
    V.reset()
    objs = []
    for i in range(2):
        for j in range(2):
            objs += V.place("Walls and floors/floor.fbx", i * (K / 2), j * (K / 2), 0)
    mn, mx = V.bbox(objs)
    t0 = mx.z - mn.z                       # キットの板厚(実測 0.0636)
    if t0 > 1e-6:
        V.sel(objs)
        bpy.ops.transform.resize(value=(1.0, 1.0, ENITA_T / t0), center_override=(0, 0, 0))
        bpy.ops.object.transform_apply(scale=True)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_RokaEnita_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mx.z)))

    # --- 高欄 単体(渡廊下の両縁に立てる)---
    # balcony rail は 0.075 x 1.818 x 1.158 でちょうど一間。回して幅を X へ出す
    V.reset()
    objs = V.place("Walls and floors/balcony rail.fbx", 0, 0, 0, rot=90)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_Koran_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0)))

    return [m for m in made if m]


build_all()
print("BUILT %d parts -> %s" % (len(BUILT), OUT))
