"""**袖の無い冠木門(かぶきもん)**を起こす。旗本屋敷の表門(類型表 gate=kabukimon・確度B)。

    blender --background --python Tools/Blender/build_kabukimon.py -- [--render]
    blender --background --python Tools/Blender/build_kabukimon.py -- --spec-only
    (`--spec-only` = FBX を焼き直さず、部材の札 `Assets/Edo/Data/PartSpecs/<名>.json` だけ書く)

【なぜ新造するか】EDO-0491・施主裁定A(2026-09-30「袖の無い冠木門を新しく部材として起こす」)。
  在庫の冠木門 `edogoyomi/es_kabukimon/kabukimon.obj` は**左右に袖塀(小屋根つき)を抱えた一体物**で、
  ES=1.818 倍で全幅 **8.05m**。三べ坂 w1 の接道は 6.9m の一辺だけで載らない。
  門の型は変えず、**袖と袖の控え・小屋根を落とした冠木門**を別の駒にする。
  袖の外の塀(板塀・生垣)はビルダーが本柱の外の面(札の jamb)へ突き付ける。

【姿の出どころ = 在庫 kabukimon.obj の実測(×1.818・2026-09-30)】
  本柱 0.376×0.341 / 柱頭の包み 3.364〜3.737(見付 0.39)/ 根巻 0〜0.286 /
  冠木 下端 2.752・丈 0.437・見込 0.246・**鼻の出 0.466**(本柱の外面から)+ 木口金物 0.307 /
  門口(本柱の内法)2.715 / 板扉は両開き・召し合わせ x=0・丈 0.016〜2.805・八双金物 2段。
  ⇒ 高さ方向の割り(柱頭・冠木・扉・根巻)は**在庫の値をそのまま**採る。

【寸法 — ⚠ 全幅 2間(3.636)以下の縛りで在庫から変えた所】
  ・門口 **2.727 = 1.5間**(在庫 2.715 を江戸間に揃えた)
  ・本柱 **0.303 角(1尺角)【U】** — 在庫の 0.376 のままだと本柱の外面が ±1.740 で、
    冠木の鼻が 0.08 しか出せない。1尺角に落として鼻を 0.15 取った
  ・冠木の鼻 **全幅 3.636 ちょうどまで【U】**(在庫の 0.466 には届かない。縛りが硬いので鼻で吸う)
  ・冠木の丈・見込は本柱の比で縮めた(丈 0.40・見込 0.21【U】)
  ・沓石(礎盤)を敷居の下へ据える(在庫は根巻だけで沓石が無い)。棟門と同じ 0.48 角・根入れ 0.26【U】

【向き(Unity 座標)】幅=X(門口の方向)/ 高さ=Y / 厚み=Z。**+Z = 外(道の側)**。
  扉は内開き(武家屋敷の門の常法)で、閉じた版だけを焼く。
  ピボット = **門の芯・敷居レベル**。底は沓石の底 −0.26(札の yBottom)。

【材】`wood` / `Foundation_A_01`(Village Kit。棟門 `build_munamon.py` と同じ借り先)。
  ⛔ 新規マテリアルを作らない(検め画像の札の線だけは書き出さない仮の材)。
  remap は Unity の **Edo ▸ 類型 ▸ 新造部材のマテリアルをremap**(`Models/Mon` を見ている)。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_obi_nagaya as N
import build_munamon as B            # 板扉 leaf()・沓石の寸法・凸包を借りる

OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Mon"))
SHOT = os.path.join(V.REPO, "Screenshots")
STOCK = os.path.join(V.REPO, "Assets", "edogoyomi", "es_kabukimon", "kabukimon.obj")
WOOD, STONE = N.WOOD, N.STONE

W_PASS   = 2.727       # 門口 = 本柱の内法(1.5間)
POST     = 0.303       # 本柱の角【U — 在庫 0.376 を全幅の縛りで 1尺角へ】
OVERALL  = 3.636       # 冠木の鼻まで含めた全幅(2間)の上限。鼻はここまで出す【U】
TOP      = 3.737       # 柱頭の包みの天端(在庫の実測)
CAP_Y0   = 3.364       # 柱頭の包みの下端(在庫の実測)
CAP_OUT  = 0.007       # 包みが本柱の面から出る寸法(在庫 0.39 − 0.376 の半分)
NEMAKI_Y1 = 0.286      # 根巻の天端(在庫の実測)
KABUKI_Y0 = 2.752      # 冠木の下端 = 扉の頭(在庫の実測)
KABUKI_H  = 0.40       # 冠木の丈【U — 在庫 0.437 を本柱の比で】
KABUKI_D  = 0.21       # 冠木の見込【U — 在庫 0.246 を本柱の比で】
KOGUCHI   = 0.06       # 冠木の木口金物の長さ【U】
SILL = (-0.04, 0.06, 0.16)   # 敷居の下端・天端・半見込(棟門と同じ)


def _dims(w=W_PASS, post=POST, overall=OVERALL):
    hx = w / 2.0
    px = hx + post / 2.0                   # 本柱の芯
    ox = hx + post                         # 本柱の外面
    nose = overall / 2.0                   # 冠木の鼻の端
    return hx, px, ox, nose


def build(name=None, want_spec=False, spec_only=False):
    """本柱2本・冠木1本・両開きの板扉(閉)・敷居・沓石。屋根なし・袖なし。"""
    name = name or ("Kabukimon_NoSode_" + N.fmt(W_PASS))
    spec = gate_spec(name)
    if spec_only:
        return None, name, spec
    P = N.palette()
    m = VM.Mesh()
    hx, px, ox, nose = _dims()
    ph = POST / 2.0
    wuv = P['wuv']
    dark = VM.sub(wuv, 0.02, 0.02, 0.10, 0.98)          # 金物(包み・根巻・八双)は木の暗い帯
    for s in (-1, 1):
        # 沓石(敷居の下へ根入れ)
        m.box(s * px - B.KUTSU, s * px + B.KUTSU, -B.KUTSU_H, 0.05, -B.KUTSU, B.KUTSU,
              VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)
        # 本柱
        m.box(s * px - ph, s * px + ph, 0.02, CAP_Y0, -ph, ph,
              VM.sub(wuv, 0.10, 0.02, 0.42, 0.98), WOOD)
        # 柱頭の包み(在庫 head_orna)
        c = ph + CAP_OUT
        m.box(s * px - c, s * px + c, CAP_Y0, TOP, -c, c, dark, WOOD)
        # 根巻(在庫 foot_orna)
        m.box(s * px - c, s * px + c, 0.02, NEMAKI_Y1, -c, c, dark, WOOD)
    # 冠木(本柱を貫いて鼻が出る)。上端は柱頭の包みの下に納める
    ky1 = KABUKI_Y0 + KABUKI_H
    kd = KABUKI_D / 2.0
    m.box(-nose + KOGUCHI, nose - KOGUCHI, KABUKI_Y0, ky1, -kd, kd,
          VM.sub(wuv, 0.20, 0.15, 0.95, 0.50), WOOD)
    for s in (-1, 1):                                   # 木口金物(在庫 kabuki_orna)
        a, b = sorted((s * (nose - KOGUCHI), s * nose))
        m.box(a, b, KABUKI_Y0 - 0.006, ky1 + 0.006, -kd - 0.006, kd + 0.006, dark, WOOD)
    # 敷居
    m.box(-px, px, SILL[0], SILL[1], -SILL[2], SILL[2],
          VM.sub(wuv, 0.30, 0.10, 0.85, 0.30), WOOD)
    # 板扉(両開き・閉)。棟門の leaf() をそのまま使う。頭は冠木の下端に合わせる(隙を作らない)
    B.leaf(m, P, -hx, -B.LEAF_GAP, -hx, 0.0, top=KABUKI_Y0)
    B.leaf(m, P, B.LEAF_GAP, hx, hx, 0.0, top=KABUKI_Y0)
    # 召し合わせの定規縁は**隙の真後ろ**に打つ。⚠ leaf(meet=) は縁を隙の脇(0.012〜0.067)へ置くので
    #   隙そのものが塞がらず、正面立面で扉の芯に空の筋が一本通った(2026-09-30 に実見)
    m.box(-B.LEAF_GAP - 0.03, B.LEAF_GAP + 0.03, 0.06, KABUKI_Y0,
          B.LEAF_Z0 - 0.032, B.LEAF_Z0, VM.sub(wuv, 0.66, 0.05, 0.74, 0.95), WOOD)
    # ⛔ 八双金物は付けない — 借りられる材に黒い鉄が無く、木の帯で打つと桟の切れ端に見えた(2026-09-30 に実見)
    o = m.to_object(name, [P['wood'], P['wall'], P['stone']])   # ⚠ スロット番号は N.WOOD/WALL/STONE の順
    V.sel([o])
    bpy.ops.object.material_slot_remove_unused()        # 漆喰(wall C)は使わない
    V.dedup_materials()
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[kabukimon] %s 門口 %.3f / 本柱 %.3f角 / 全幅 %.3f / 柱頭 %.3f / 冠木下端 %.3f"
          % (name, W_PASS, POST, 2 * nose, TOP, KABUKI_Y0))
    return (o, name, spec) if want_spec else (o, name)


def gate_spec(name):
    """札を**作図の変数から**出す(`build_munamon.gate_spec` と同じ手続き・同じ欄)。⛔ メッシュを測らない。
    座標は Unity の資産の局所(+X=門口・+Z=外・原点=門の芯・敷居の高さ)。左右対称なので
    Unity の取り込みで x が反転しても値は変わらない。"""
    hx, px, ox, nose = _dims()
    ph = POST / 2.0
    c = ph + CAP_OUT
    yb = -B.KUTSU_H
    band0, band1 = yb + 0.30, yb + 1.80        # EdoPartSpec.BAND_LO / BAND_HI
    corners = [(s * px + a * B.KUTSU, b * B.KUTSU) for s in (-1, 1) for a in (-1, 1) for b in (-1, 1)]
    foot = [{"x": x, "y": z} for (x, z) in B._hull(corners)]
    # 帯の z の端: 沓石・本柱・根巻・敷居・板扉の桟
    zs = [z for (_x, z) in corners] + [ph, -ph, c, -c, SILL[2], -SILL[2],
                                       B.LEAF_ZF, B.LEAF_ZB]
    # 脇の面 = 帯の全段でいちばん内へ引っ込む段 = 本柱の外面(根巻は天端 0.286 で帯の下 0.04 に掛かるが
    # 帯の 0.286〜1.54 は本柱の素の面なので、最も引っ込むのは本柱の面)
    jz = [ph, -ph, c, -c]
    if B.KUTSU - ph <= 0.15:
        jz += [B.KUTSU, -B.KUTSU]
    jamb = lambda x: {"x": x, "z0": min(jz), "z1": max(jz), "y0": band0, "y1": band1}
    kd = KABUKI_D / 2.0 + 0.006
    src = ("blender:build_kabukimon.py build(w=%g, post=%g, overall=%g, top=%g, kabuki=%g+%g, "
           "sode=none, opened=False)" % (W_PASS, POST, OVERALL, TOP, KABUKI_Y0, KABUKI_H))
    return {
        "prefab": "Assets/Edo/Models/Mon/%s.fbx" % name,
        "kind": "gate", "source": src, "unitScale": 1.0,
        "yBottom": yb, "foot": foot,
        "front": max(zs), "back": min(zs),
        "jambL": jamb(-ox), "jambR": jamb(ox),
        "passage": {"x0": -hx, "x1": hx},
        # 屋根が無いので外接は冠木の鼻・沓石・柱頭の包みで決まる
        "eave": {"x0": min(-nose, -px - B.KUTSU), "x1": max(nose, px + B.KUTSU),
                 "z0": min(zs + [-kd]), "z1": max(zs + [kd]),
                 "y0": yb, "y1": TOP},
        "faceOut": 0.0, "faceIn": 0.0, "copingOverhang": 0.0,
        "height": TOP - yb,
    }


# ---------------------------------------------------------------- 検め画像
def _stock(x_off):
    """在庫の冠木門を ES=1.818 で読み、芯を x_off・底を 0 に置く(並べ比べ専用。⛔ 書き出さない)"""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=STOCK)
    got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    o = V.join(got, "Stock_Kabukimon")
    V.sel([o])
    bpy.ops.transform.resize(value=(1.818,) * 3, center_override=(0, 0, 0))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mn, mx = V.bbox([o])
    o.location = (x_off - (mn.x + mx.x) / 2.0, -(mn.y + mx.y) / 2.0, -mn.z)
    bpy.context.view_layer.update()
    for mat in o.data.materials:             # obj の材は Blender が jpg を結線済み。Alpha だけ戻す
        if mat and mat.node_tree:
            for n in mat.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Alpha'].default_value = 1.0
    return o


def _line_mat(name, rgb):
    """札の線の仮の材(レンダ専用・書き出さない)"""
    mt = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mt.use_nodes = True
    nt = mt.node_tree
    nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = rgb + (1.0,)
    em.inputs['Strength'].default_value = 3.0
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs[0])
    return mt


def _seg(a, b, mat, r=0.012):
    """Unity 局所の2点 a, b(x, y, z)を結ぶ細い角棒。Blender へは (x, −z, y) で写す
    (`VM.Mesh.to_object` と同じ写像)"""
    A = Vector((a[0], -a[2], a[1])); Bv = Vector((b[0], -b[2], b[1]))
    d = Bv - A
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(A + Bv) / 2)
    o = bpy.context.active_object
    o.scale = (max(abs(d.x), r), max(abs(d.y), r), max(abs(d.z), r))
    o.data.materials.append(mat)
    return o


def overlay(spec):
    """札の線: foot(赤)・jamb(青)・passage(緑)・外接 eave(黄)"""
    red, blue = _line_mat("_ov_foot", (1, 0.1, 0.1)), _line_mat("_ov_jamb", (0.1, 0.35, 1))
    green, yel = _line_mat("_ov_pass", (0.1, 1, 0.2)), _line_mat("_ov_eave", (1, 0.9, 0.1))
    objs = []
    yb = spec["yBottom"]
    f = spec["foot"]
    for i in range(len(f)):
        p, q = f[i], f[(i + 1) % len(f)]
        objs.append(_seg((p["x"], yb, p["y"]), (q["x"], yb, q["y"]), red))
    for k in ("jambL", "jambR"):
        j = spec[k]
        for (y, z0, z1) in ((j["y0"], j["z0"], j["z1"]), (j["y1"], j["z0"], j["z1"])):
            objs.append(_seg((j["x"], y, z0), (j["x"], y, z1), blue))
        for z in (j["z0"], j["z1"]):
            objs.append(_seg((j["x"], j["y0"], z), (j["x"], j["y1"], z), blue))
    ps = spec["passage"]
    objs.append(_seg((ps["x0"], 0.08, spec["front"]), (ps["x1"], 0.08, spec["front"]), green))
    for x in (ps["x0"], ps["x1"]):
        objs.append(_seg((x, 0.0, spec["front"]), (x, 2.0, spec["front"]), green))
    e = spec["eave"]
    for (x0, x1) in ((e["x0"], e["x1"]),):
        for y in (e["y0"], e["y1"]):
            objs.append(_seg((x0, y, e["z1"]), (x1, y, e["z1"]), yel, 0.008))
        for x in (x0, x1):
            objs.append(_seg((x, e["y0"], e["z1"]), (x, e["y1"], e["z1"]), yel, 0.008))
    return objs


def shots(o, spec):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    H = mx.z - mn.z
    r = max(mx.x - mn.x, H)
    # ① 外(道の側)からの正面立面。⚠ 外 = Unity +Z = Blender −Y
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z), ortho_scale=r * 1.15, res=(1400, 1400))
    V.render(os.path.join(SHOT, "kabukimon_nosode_elev.png"))
    # ② 外から斜め(人の目の高さ)
    V.studio((mn.x - r * 0.9, mn.y - r * 2.2, 1.65), (c.x, c.y, H * 0.42), res=(1600, 1100))
    V.render(os.path.join(SHOT, "kabukimon_nosode_3d.png"))
    # ③ 内から斜め — 扉の裏・定規縁・冠木の鼻
    V.studio((mx.x + r * 0.9, mx.y + r * 2.2, 1.9), (c.x, c.y, H * 0.42), res=(1600, 1100))
    V.render(os.path.join(SHOT, "kabukimon_nosode_ura.png"))
    # ④ 札の線を重ねる(正面立面と、斜め上から足元)
    ov = overlay(spec)
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z), ortho_scale=r * 1.15, res=(1400, 1400))
    V.render(os.path.join(SHOT, "kabukimon_nosode_spec_elev.png"))
    V.studio((mn.x - r * 1.2, mn.y - r * 1.8, r * 1.4), (c.x, c.y, 1.0), res=(1600, 1100))
    V.render(os.path.join(SHOT, "kabukimon_nosode_spec_3d.png"))
    for x in ov:
        bpy.data.objects.remove(x, do_unlink=True)
    # ⑤ 在庫の冠木門と並べる(左 = 在庫・右 = 新造)。正面と斜め
    st = _stock(-6.0)
    mn2, mx2 = V.bbox([o, st])
    c2 = (mn2 + mx2) * 0.5
    V.studio((c2.x, mn2.y - 22.0, 1.9), (c2.x, c2.y, 1.9),
             ortho_scale=(mx2.x - mn2.x) * 1.08, res=(1800, 1000))
    V.render(os.path.join(SHOT, "kabukimon_nosode_narabe.png"))
    V.studio((c2.x - 4.0, mn2.y - 11.0, 1.65), (c2.x, c2.y, 1.8), res=(1800, 1000))
    V.render(os.path.join(SHOT, "kabukimon_nosode_narabe_3d.png"))
    bpy.data.objects.remove(st, do_unlink=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--spec-only" in argv:
        _o, name, spec = build(spec_only=True)
        V.write_spec(os.path.join(OUT, name + ".fbx"), spec)
        return
    V.reset()
    o, name, spec = build(want_spec=True)
    mn, mx = V.bbox([o])
    print("[kabukimon] %s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  底=%.3f  面=%d"
          % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
    print("[kabukimon] 材質=%s" % [mm.name for mm in o.data.materials])
    if "--render" in argv:                     # ⚠ export の後は bbox が潰れるので先に撮る
        shots(o, spec)
    path = os.path.join(OUT, name + ".fbx")
    V.export_fbx([o], path, kind="gate", spec=spec)
    print("[kabukimon] 書き出し " + path)


if __name__ == "__main__":
    main()
