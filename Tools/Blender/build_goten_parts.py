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
OUT = "/Users/toshio/project/edo-unity/Assets/Edo/Models/Goten/Parts"
PREVIEW = os.environ.get("GOTEN_PREVIEW", "")
ONLY = os.environ.get("GOTEN_ONLY", "")     # 部分文字列で絞る

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

    # --- 高欄 単体(渡廊下の両縁に立てる)---
    # balcony rail は 0.075 x 1.818 x 1.158 でちょうど一間。回して幅を X へ出す
    V.reset()
    objs = V.place("Walls and floors/balcony rail.fbx", 0, 0, 0, rot=90)
    mn, mx = V.bbox(objs)
    made.append(finish(objs, "Goten_Koran_1ken", ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0)))

    return [m for m in made if m]


build_all()
print("BUILT %d parts -> %s" % (len(BUILT), OUT))
