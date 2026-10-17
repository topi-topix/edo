"""岡部筑前守上屋敷 **案1(EDO-0502)** で足跡が在庫と合わなかった附属屋を、既存の生成器を寸法だけ変えて焼く。

    blender --background --python Tools/Blender/build_okabe_an1_buzai.py -- [kura45 makigura tomomachi35] [--render]
    BUZAI_OUT=<staging> blender --background --python Tools/Blender/build_okabe_an1_buzai.py -- --render

【方針】⛔ 同じ型を二度書かない(build_doi_buzai.py と同じ薄い駆動器)。
  ・蔵1・蔵2  `service.Kura1/Kura2` = 5×4間 … 松平の `dozo`(石腰+白漆喰大壁+観音扉)を 4×5間・軒 4.60 で。
               ⚠ 在庫 `Own.Matsudaira.Dozo` は 4×7間で足跡に入らない。軒 4.60 はその土蔵と同じ値【U】
  ・薪蔵      `service.Makigura` = 4×3間 … 型が指図に無い(assetKubun「土蔵か板倉・薪小屋か未決」)。
               **板倉(四周板壁・板葺・両開きの板戸)**で起こす【U・部材方の判断】。
               隣の米蔵(土蔵・軒 5.20・棟 7.2)と並んで見分けが付き、薪は火を持つ物ではないので
               土蔵にする理由が無い。型は岡部の納戸小屋/類型の作事小屋(`nandokoya`)そのもの
  ・供待      `service.Tomomachi` = 5×3.5間 … 在庫 `Own.Tomomachi` は 3×5間で梁間が半間足りない。
               岡部の `tomomachi` を梁間 3.5間で呼ぶ(柱の割付は frame が 4 等分へ丸める)

【向き・ピボット(Unity)】幅=X(長手)/ 高さ=Y / 厚み=Z。ピボット = footprint の中心・地盤レベル。
  蔵: **観音扉は −X の妻**。薪蔵・供待: **+Z が開口(板戸・吹き放ち)の面**。
【材】`Fence_B_01`/`Foundation_A_01`/`Wall Exterior Defence`(蔵)、`wood`/`wall C`/`Foundation_A_01`/`roof`(他)。新規なし。
"""
import bpy, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_matsudaira_dewa_fuzokuya as F
import build_okabe_fuzokuya as OF

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Fuzokuya"))
SHOT = os.path.join(V.REPO, "Screenshots")


def kura45():
    """蔵 梁間4間 × 桁行5間。ローカル +X = 桁行(5間)。観音扉 −X。"""
    nm = "Okabe_Kura_4x5ken"
    return F.dozo(uk=4, vk=5, name=nm, eave=4.60), nm


def makigura():
    """薪蔵(板倉)桁行4間 × 梁間3間・軒 2.45・板葺 4寸・前面(+Z)に両開きの板戸 1.30m。"""
    nm = "Okabe_Makigura_4x3ken"
    o, _ = OF.nandokoya(uKen=4, vKen=3, name=nm, eaveH=2.45, noki=0.55, end=0.30,
                        ratio=0.40, base=0.20, post=0.14, nx=4, nz=3,
                        dw=1.30, doorH=2.05, leaves=2, pitch=0.19)
    return o, nm


def tomomachi35():
    nm = "Okabe_Tomomachi_3.5x5ken"
    o, _ = OF.tomomachi(uKen=3.5, vKen=5, name=nm, keta_out=0.0)   # 桁を瓦の谷から覗かせない
    return o, nm


PARTS = {"kura45": kura45, "makigura": makigura, "tomomachi35": tomomachi35}


def shots(o, key):
    V.hook_textures()
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    r = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    bpy.ops.mesh.primitive_plane_add(size=60, location=(c.x, c.y, -0.01))
    # 開口面(Blender −Y = Unity +Z)を斜め前から / 背面と −X の妻を斜め後ろから
    V.studio((c.x - r * 0.9, mn.y - r * 1.3, r * 0.6), (c.x, c.y, (mx.z - mn.z) * 0.4), res=(1500, 1000))
    V.render(os.path.join(SHOT, "okabe_an1_%s_front.png" % key))
    V.studio((mx.x + r * 0.9, mx.y + r * 1.3, r * 0.6), (c.x, c.y, (mx.z - mn.z) * 0.4), res=(1500, 1000))
    V.render(os.path.join(SHOT, "okabe_an1_%s_back.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or list(PARTS)
    for key in want:
        V.reset()
        o, name = PARTS[key]()
        mn, mx = V.bbox([o])
        print("[an1] %-26s Unity実寸 W(X)=%.3f H(Y)=%.3f D(Z)=%.3f 底=%+.3f 面=%d 材=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons),
                 [m.name for m in o.data.materials]))
        if "--render" in argv:
            shots(o, key)            # ⚠ 書き出しの前に撮る(後だと bbox が潰れる)
            for ob in [x for x in bpy.data.objects if x.name.startswith("Plane")]:
                bpy.data.objects.remove(ob, do_unlink=True)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[an1] 書き出し " + os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    main()
