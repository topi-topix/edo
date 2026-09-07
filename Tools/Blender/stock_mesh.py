"""**在庫の木のメッシュを .prefab から取り出す**(比較レンダのためだけ)。

    import stock_mesh
    objs = stock_mesh.load_prefab_lod(
        "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/"
        "Tree_BlackPine_Big_Green_01.prefab", lod=0)

【なぜ要るか】Waldemarst FreeJapaneseGarden の木は **.fbx を同梱していない** —
メッシュは `.prefab` の YAML に `!u!43` として**埋め込まれている**。
そのため「新造した木を**在庫の木と並べて焼く**」がこれまで Blender 側でできず、
密度と背丈の突き合わせを目でやれなかった。⇒ YAML から直に読む。

⛔ **これは検証専用。**取り出したメッシュを再輸出しない(再配布不可のアセット)。
⚠ 頂点は **Unity 座標(Y-up・左手)**なので、Blender の Z-up へ入れ替える
   (x, y, z)_unity → (x, -z, y)_blender。三角形の巻きも合わせて反転する。

【レイアウト】(2026-09-07 実測。FJG の木は全部これ)
  すべて float32・1ストリーム。ch0 位置(3) / ch1 法線(3) / ch2 接線(4) /
  ch3 色(4) / ch4 UV0(4) / ch5 UV1(4) / …  ⇒ stride = m_DataSize / m_VertexCount。
  ⚠ SpeedTree8 の UV は **4成分**。使うのは .xy だけ。
"""
import re, struct, os

# format コード → (struct のコード, バイト数)。FJG は 0(float32)しか使っていないが、
# 他パックで 1(float16)・2(unorm8)が出るので入れてある。
FMT = {0: ("f", 4), 1: ("e", 2), 2: ("B", 1), 3: ("b", 1)}


def _docs(txt):
    """Unity の YAML を `--- !u!<class> &<id>` で切る。"""
    out = []
    for m in re.finditer(r"--- !u!(\d+) &(\d+)[^\n]*\n", txt):
        out.append((int(m.group(1)), int(m.group(2)), m.start(), m.end()))
    for i, (cls, fid, s, e) in enumerate(out):
        end = out[i + 1][2] if i + 1 < len(out) else len(txt)
        yield cls, fid, txt[e:end]


def _hex(blob):
    return bytes.fromhex(blob.strip())


def read_meshes(prefab_path):
    """`.prefab` の中の Mesh を全部返す。{name: dict(verts, uvs, subs)}。"""
    txt = open(prefab_path, encoding="utf-8", errors="replace").read()
    out = {}
    for cls, fid, body in _docs(txt):
        if cls != 43:
            continue
        name = re.search(r"\n  m_Name: (.*)", body).group(1).strip()
        vc = int(re.search(r"m_VertexCount: (\d+)", body).group(1))
        ds = int(re.search(r"m_DataSize: (\d+)", body).group(1))
        chans = [(int(a), int(b), int(c), int(d)) for a, b, c, d in
                 re.findall(r"- stream: (\d+)\s+offset: (\d+)\s+format: (\d+)\s+dimension: (\d+)",
                            body)]
        data = _hex(re.search(r"_typelessdata: ([0-9a-fA-F]*)", body).group(1))
        idx16 = int(re.search(r"m_IndexFormat: (\d+)", body).group(1)) == 0
        ib = _hex(re.search(r"m_IndexBuffer: ([0-9a-fA-F]*)", body).group(1))
        subs = [(int(fb), int(ic)) for fb, ic in
                re.findall(r"firstByte: (\d+)\s+indexCount: (\d+)", body)]
        if not vc or not chans:
            continue
        stride = ds // vc
        verts, uvs = [], []
        cpos, cuv = chans[0], (chans[4] if len(chans) > 4 and chans[4][3] else None)
        for i in range(vc):
            b = i * stride
            code, sz = FMT[cpos[2]]
            x, y, z = struct.unpack_from("<3" + code, data, b + cpos[1])
            verts.append((x, -z, y))                  # Unity Y-up → Blender Z-up
            if cuv:
                code, sz = FMT[cuv[2]]
                u, v = struct.unpack_from("<2" + code, data, b + cuv[1])
                uvs.append((u, v))
            else:
                uvs.append((0.0, 0.0))
        step = 2 if idx16 else 4
        code = "H" if idx16 else "I"
        faces = []
        for si, (fb, ic) in enumerate(subs):
            tri = []
            for t in range(ic // 3):
                o = fb + t * 3 * step
                a, bq, c = struct.unpack_from("<3" + code, ib, o)
                tri.append((a, c, bq))                # 座標を反転したので巻きも反転
            faces.append(tri)
        out[name] = dict(verts=verts, uvs=uvs, subs=faces)
    return out


def load_prefab_lod(prefab_rel, lod=0, mats=None, repo=None):
    """Blender へ **その LOD だけ**を起こす。返すのは [オブジェクト]。
    `mats` = サブメッシュ順の材質名。省略時は BlackPine の並び(樹皮 / 房A / 房B)。"""
    import bpy, bmesh
    if repo is None:
        import vklib as V
        repo = V.REPO
    path = prefab_rel if os.path.isabs(prefab_rel) else os.path.join(repo, prefab_rel)
    ms = read_meshes(path)
    key = "LOD_%d" % lod
    if key not in ms:
        raise KeyError("%s に %s が無い(%s)" % (os.path.basename(path), key, list(ms)))
    m = ms[key]
    mats = mats or ["M_FJG_Tree_BlackPine_Bark",
                    "M_FJG_Tree_BlackPine_Sprout_A_Green",
                    "M_FJG_Tree_BlackPine_Sprout_B_Green"]
    objs = []
    for si, tris in enumerate(m["subs"]):
        if not tris:
            continue
        used = sorted({i for t in tris for i in t})
        remap = {g: k for k, g in enumerate(used)}
        me = bpy.data.meshes.new("stock_%d" % si)
        bm = bmesh.new()
        vs = [bm.verts.new(m["verts"][g]) for g in used]
        uvl = bm.loops.layers.uv.verify()
        for t in tris:
            try:
                f = bm.faces.new([vs[remap[i]] for i in t])
            except ValueError:
                continue                              # 重複面(在庫側に少数ある)
            for lp, gi in zip(f.loops, t):
                lp[uvl].uv = m["uvs"][gi]
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("stock_%s_%d" % (key, si), me)
        bpy.context.collection.objects.link(ob)
        nm = mats[si] if si < len(mats) else mats[-1]
        mat = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        ob.data.materials.append(mat)
        objs.append(ob)
    return objs
