"""素通し(穴)の検査 — 部材を**真上から**焼いて、屋根や壁を貫いて向こうが見える画素を数える。

    blender --background --python Tools/Blender/check_seethrough.py -- <FBX> [<FBX>...] [--out <dir>]
    # 例) blender --background --python Tools/Blender/check_seethrough.py -- \
    #       Assets/Edo/Models/Goten/Roofs/Goten_Roof_Banded_5-4x10ken_v.fbx

【数え方 — ここを間違えると偽陽性で丸1巡溶ける】
  ⛔ **世界背景を派手な色にして「その色が出たら穴」とやらない。** 背景は同時に**照明**なので、
    影になった面が背景色に染まって偽陽性になる(妻壁の漆喰を穴と誤診した実例あり)。
  ⛔ **「列ごとに最上/最下の不透明画素のあいだの透明画素」でも数えない**(2026-09-06 是正)。
    屋根の**四隅は隅棟が軒先より外へ飛び出す**ので**輪郭が凸でない**。最も外の列は
    「隅の出っ張り2つだけが不透明・あいだは全部空」になり、**外の空を穴と誤診する**。
    実測 `Goten_Roof_Banded_4-4x8ken` = この数え方で 23,076px / 実物は穴ゼロ。
  ⭕ **正解は「囲まれた透明」** — `film_transparent=True` + `color_mode='RGBA'` で焼き、
    透明画素のうち**画像の外周へ4連結で繋がらないもの**だけを穴と数える。輪郭が凸でなくてよい。
  ⚠ `scipy` は無く、**Pillow 12 の `ImageDraw.floodfill` は無反応**(2026-09-06 実測)。
    ⇒ 下の `border_connected` のように **numpy だけの走査線塗り**を使う。

【限界 — 数値だけで済ませないこと】
  ⚠ 「囲まれた透明」は**軒先まで開いて外へ繋がる欠け**は捕まえられない。
  ⚠ 正射影で視線が面と平行になる向き(平の立面など)は掠める光線が偽陽性を出す。
    **真上からの正射影が一番効く** — 屋根は空に面した物なので、上から抜けが無ければ穴は無い。
  ⇒ **俯瞰・谷の寄り・妻の立面を必ず自分の目で見る**こと。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, numpy as np
import vklib as V


def border_connected(mask):
    """mask(True=透明)のうち、画像の外周へ**4連結**で繋がる画素を True で返す。
    走査線塗りつぶし(1行ぶんの連続区間をまとめて塗る)なので 1400² でも一瞬。"""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    stack = []
    for x in range(w):
        if mask[0, x]:     stack.append((0, x))
        if mask[h - 1, x]: stack.append((h - 1, x))
    for y in range(h):
        if mask[y, 0]:     stack.append((y, 0))
        if mask[y, w - 1]: stack.append((y, w - 1))
    while stack:
        y, x = stack.pop()
        if seen[y, x] or not mask[y, x]:
            continue
        xl = x
        while xl - 1 >= 0 and mask[y, xl - 1] and not seen[y, xl - 1]:
            xl -= 1
        xr = x
        while xr + 1 < w and mask[y, xr + 1] and not seen[y, xr + 1]:
            xr += 1
        seen[y, xl:xr + 1] = True
        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                idx = np.nonzero(mask[ny, xl:xr + 1] & ~seen[ny, xl:xr + 1])[0]
                if idx.size:
                    for s in idx[np.concatenate(([True], np.diff(idx) != 1))]:
                        stack.append((ny, xl + int(s)))
    return seen


def seethrough(objs, png, cam, look, ortho, res=1400):
    """真上(など)から焼いて**囲まれた透明**の画素数を返す。
    ⚠ 床の板を置かないこと(不透明な背景板があると全部塞がって常に 0 になる)。
    ⚠ `export_fbx` を通すと bbox が 0 に潰れるので、**書き出しの前に**呼ぶ。"""
    for c in [c for c in bpy.data.objects if c.type in ('CAMERA', 'LIGHT')]:
        bpy.data.objects.remove(c, do_unlink=True)
    for pl in [c for c in bpy.data.objects if c.name.startswith("Plane")]:
        bpy.data.objects.remove(pl, do_unlink=True)
    V.studio(cam, look, ortho_scale=ortho, res=(res, res))
    sc = bpy.context.scene
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    V.render(png)
    img = bpy.data.images.load(png)
    buf = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(img.size[1], img.size[0], 4)[:, :, 3]
    bpy.data.images.remove(img)
    sc.render.film_transparent = False
    tr = a < (1.0 / 255.0)
    encl = tr & ~border_connected(tr)
    n = int(encl.sum())
    where = ""
    if n:
        ys, xs = np.nonzero(encl)
        where = " 位置 rows %d..%d cols %d..%d" % (ys.min(), ys.max(), xs.min(), xs.max())
    return n, where


def check_fbx(path, out_dir):
    V.reset()
    objs = V.imp(os.path.abspath(path))
    if not objs:
        print("SEETHROUGH %-40s ⛔ メッシュが無い" % os.path.basename(path))
        return 1
    o = V.join(objs, "chk") if len(objs) > 1 else objs[0]
    V.hook_textures()
    mn, mx = V.bbox([o])
    cx, cy = (mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0
    span = max(mx.x - mn.x, mx.y - mn.y)
    tag = os.path.splitext(os.path.basename(path))[0]
    n, where = seethrough(o, os.path.join(out_dir, "%s_T2_ue.png" % tag),
                          (cx, cy, mx.z + 60.0), (cx, cy, mn.z), span * 1.05)
    print("SEETHROUGH %-40s 真上 囲まれた透明=%d px%s  実寸 %.3f × %.3f × %.3f"
          % (tag, n, where, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y))
    return 0 if n == 0 else 1


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.join(V.REPO, "Screenshots", "seethrough")
    files = []
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = argv[i + 1]; i += 2
        else:
            files.append(argv[i]); i += 1
    os.makedirs(out, exist_ok=True)
    bad = sum(check_fbx(f, out) for f in files)
    print("SEETHROUGH ==== %d/%d 合格 ====" % (len(files) - bad, len(files)))
    raise SystemExit(1 if bad else 0)
