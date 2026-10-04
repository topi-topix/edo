"""**松江松平(matsudaira_dewa)の溝まわりの石の部材**(EDO-0554)。
    blender --background --python Tools/Blender/build_matsudaira_dewa_mizo.py -- ishidoi ishibuta --render

【何を起こすか】指図 `mizu.nodes` の二か所。
  ・**石樋**(`MZ17` が土留め `TW_Nakanokuchi_W` を抜ける所)── 中ノ口の庭の下の帯の溝の終わりで、
    土留めの天端石の下を抜けて面から突き出し、0.43 落ちて `MZ16` の頭へ吐く。
  ・**石蓋**(`K_Daidokoromon` の頭で `MZ16` が段の前を横切る所・潜戸の内の溝)── 溝を塞いで踏ませる。
【倣う型】土井の `build_doi_buzai.otoshimizo`(石敷きの落とし溝 1m モジュール)。
  ⭐ 石蓋は**落とし溝と同じ断面**(溝幅 0.36・耳石 0.17・総幅 0.70)で焼き、同じピッチで
    run に混ぜられるようにする。⛔ 落とし溝を伸縮させて蓋の区間を作らない。
  ⛔ `build_doi_buzai` は import すると main() が走るので import しない(one_stone だけ写した)。
【材】`Foundation_A_01`(Village Kit の玉石積み)を **石1個より小さい矩形**で貼る
  (`build_doi_buzai.one_stone` と同じ取り方)。⛔ 新規マテリアルを作らない。
【座標】F.Mesh は Unity 座標(幅=X / 高さ=Y / 厚み=Z)で積む。
"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_matsudaira_dewa_fuzokuya as F
import build_okabe_niwa as ON

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Fuzokuya"))
SHOT = os.path.join(V.REPO, "Screenshots")


def one_stone(suv, i=0):
    """一個の石の面として読ませる UV(`build_doi_buzai.one_stone` と同じ値)。"""
    o = ((0.34, 0.40), (0.53, 0.23), (0.27, 0.66), (0.60, 0.57),
         (0.41, 0.11), (0.14, 0.34))[i % 6]
    return F._sub(suv, o[0], o[1], o[0] + 0.10, o[1] + 0.10)


def ishidoi():
    """**石樋**(`MZ17` → 土留め `TW_Nakanokuchi_W` を抜けて `MZ16` の頭へ)。
    一本石を U 字に刳った樋。外幅 0.40 × 外丈 0.22(溝 0.16 幅 × 0.10 深)× 長さ 1.00。
    ⭐ ピボット = **樋の芯・溝底(吐き口の側の流れの底)・土留めの面**。
       ⇒ `position.y` = 指図 `MZ17.inv.end.y`(25.98)、ピボットを壁の見え面の線に置く。
    ローカル **+Z = 下流**(土留めの面から外へ・低い郭 Daidokoro の側)。
    −Z へ 0.60 は土留めの天端石の下に呑ませる(見えない)/ +Z へ 0.40 突き出して吐く。
    落差 0.43(`MZ17.inv.dropToMZ16`)は部材に含めない ── 吐いた水は MZ16 の頭が受ける。"""
    (wm, wuv), (sm, suv), (pm, puv) = F.palette()
    m = F.Mesh()
    hw, hc = 0.20, 0.08            # 外幅の半分 / 溝幅の半分
    bot, top = -0.12, 0.10         # 底(溝底から)/ 縁の天端
    z0, z1 = -0.60, 0.40           # 呑み込み / 突き出し
    STONE = F.STONE
    m.box(-hw, hw, bot, 0.0, z0, z1, one_stone(suv, 0), STONE)          # 底
    m.box(-hw, -hc, 0.0, top, z0, z1, one_stone(suv, 1), STONE)         # 左の縁
    m.box(hc, hw, 0.0, top, z0, z1, one_stone(suv, 2), STONE)           # 右の縁
    # 吐き口の水切り(先端の下を 0.03 欠いて、水が樋の腹を伝わずに落ちるようにする)
    m.box(-hw, hw, bot - 0.03, bot, z1 - 0.10, z1, one_stone(suv, 3), STONE)
    return F._finish("Matsudaira_Ishidoi", m, [wm, sm, pm], []), "Matsudaira_Ishidoi"


def ishibuta():
    """**石蓋の溝 1m モジュール**(`K_Daidokoromon` の頭・潜戸の内の溝)。
    `Doi_Otoshimizo_1m` と**同じ断面・同じピッチ**:溝幅 0.36・溝底の天端 −0.10・総幅 0.70。
    違いは耳石を地盤の下で止め、その上に**切石の蓋 2枚**(1枚 0.497 × 0.70 × 厚 0.10)を
    載せて天端を地盤 +0.02 に揃えること(踏む面なので耳石の +0.04 より低くする)。
    ⭐ bbox の X をちょうど 1.000 にする(ビルダーが bbox からピッチを測る)。
    ピボット = **スパンの中心・地盤レベル**。ローカル **+X = 流れの向き**(落とし溝と同じ)。
    ⭐ 走りは 1m 刻みで並べ、端数は落とし溝の側で吸う(蓋を切らない)。"""
    (wm, wuv), (sm, suv), (pm, puv) = F.palette()
    m = F.Mesh()
    STONE = F.STONE
    L, hc, edge = 1.000, 0.18, 0.17
    hx = L / 2.0
    # 溝底の敷石(落とし溝と同じ 4 枚割り)
    n = 4
    for i in range(n):
        a0 = -hx + L * i / n
        ga, gb = (0.006 if i else 0.0), (0.006 if i < n - 1 else 0.0)
        m.box(a0 + ga, a0 + L / n - gb, -0.20, -0.10, -hc, hc, one_stone(suv, i), STONE)
    # 側の受け石(蓋を受ける。地盤 −0.08 で止める)
    for s in (-1, 1):
        m.box(-hx, hx, -0.20, -0.08, s * hc, s * (hc + edge), one_stone(suv, 4 + (s > 0)), STONE)
    # 蓋 2 枚(切石。目地 6mm は中だけ ── 端は ±hx に面一)
    for k, (a0, a1) in enumerate(((-hx, -0.003), (0.003, hx))):
        m.box(a0, a1, -0.08, 0.02, -(hc + edge), hc + edge, one_stone(suv, 2 + k), STONE)
    return F._finish("Matsudaira_Ishibuta_1m", m, [wm, sm, pm], []), "Matsudaira_Ishibuta_1m"


PARTS = {"ishidoi": ishidoi, "ishibuta": ishibuta}


def shots(o, key, box):
    """⚠ 書き出しの前に撮る(export_fbx の後は bbox が潰れる)。地面は Blender z=0(= 地盤)。"""
    ON.hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    r = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    gz = 0.0 if key == "ishibuta" else mn.z - 0.45     # 石樋は吐いた先の低い面を見せる
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(c.x, c.y, gz))
    out = []
    # ① 斜め上から(蓋の天端・溝の口・樋の刳りを見る)
    V.studio((c.x - r * 1.3, c.y - r * 1.8, mx.z + r * 1.2), (c.x, c.y, mn.z * 0.5), res=(1500, 1050))
    p = os.path.join(SHOT, "mzmizo_%s_3d.png" % key); V.render(p); out.append(p)
    # ② 小口の正面(断面が読める唯一の絵)── 流れの軸に沿って見る
    if key == "ishibuta":
        V.studio((mn.x - r * 3.0, c.y, c.z), (c.x, c.y, c.z), ortho_scale=(mx.y - mn.y) * 1.6, res=(1400, 900))
    else:
        V.studio((c.x, mx.y + r * 3.0, c.z), (c.x, c.y, c.z), ortho_scale=(mx.x - mn.x) * 2.4, res=(1400, 900))
    p = os.path.join(SHOT, "mzmizo_%s_koguchi.png" % key); V.render(p); out.append(p)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--") and a in PARTS] or list(PARTS)
    for key in want:
        V.reset()
        o, name = PARTS[key]()
        mn, mx = V.bbox([o])
        print("[mizo] %-24s Unity実寸 W(X)=%6.3f  H(Y)=%6.3f  D(Z)=%6.3f  底=%+.3f 天=%+.3f  面=%d  材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, mx.z, len(o.data.polygons),
                 [mm.name for mm in o.data.materials]))
        if "--render" in argv:
            for p in shots(o, key, (mn, mx)):
                print("RENDER " + p)
            for ob in [x for x in bpy.data.objects if x.name.startswith("Plane")]:
                bpy.data.objects.remove(ob, do_unlink=True)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[mizo] 書き出し " + os.path.join(OUT, name + ".fbx"))


main()
