"""**木戸** — のし塀(結界)の開口に建てる板戸と、汀の柵に開ける潜り。岡部筑前守上屋敷。
併せて、**練塀に開ける通用口**(頭を小壁で塞いだ丈の高い版)。土井大隅守上屋敷。

    blender --background --python Tools/Blender/build_kido.py -- kekkai [--render]   # 結界の2口
    blender --background --python Tools/Blender/build_kido.py -- kido 2.727 [--render]
    blender --background --python Tools/Blender/build_kido.py -- horikido [--render]
    # 土井の裏木戸(南端の通用口)= 練塀の天端 3.45 まで届く版
    blender --background --python Tools/Blender/build_kido.py -- kido 1.8 \\
        --H 3.45 --uchi 2.0 --neribei 2.65 [--render]

【⚠ 塀の口は「塀の天端まで届く」かを据える前に検める】土井の裏木戸は、
  ⛔ 従前 天端 +2.000 で焼いていて、敷居 15.10 に据えると天端 17.10 ——
  両肩の練塀の天端 18.55 との間に **1.45m の穴**が残っていた(2026-09-06 に発覚)。
  ⚠ 外周の閉じの検査は「開口に戸(leaf)が入っているか」で数えるので**鳴らない**。
  ⭕ 対策 = `--H`(部材の天端)と `--uchi`(内法=戸の丈)を**別々に受ける**ようにし、
     差を **`--neribei <塀の丈>` で小壁**として埋める。⛔ 木の板で埋めない(下記)。

【なぜ新造するか】在庫に木戸は無い。のし塀 `Own.Noshibei(len)` は**開口を含まない**ので、
  W5・W6 の口を塞ぐ部材が無いまま残っていた(2026-09-04 の部材方の申し送り)。

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` が正典】
  ・結界の木戸 = `kekkai[].gap`(⚠ キーは `openings` ではなく **`gap`**)
      W5「庭掃除と落葉出し用」 u −19.0 → −17.5 = **1.5間 = 2.727m**
      W6「勝手の木戸」        v 109.4 → 112.4 だが `gap._` は **「幅 1.6間」= 2.909m**
      ⚠⚠ **W6 は指図の中で数字が3つ食い違う** — 下の【W6の食い違い】を参照。
      高さは塀 `kekkai[].h` = 1.8 以下。**柱 1.80 / 内法 1.50** で納めた【U】。
  ・汀の潜り = `nishi.saku.kuguri` … 辺5 の **s=55.7**・幅 **1.818(1間)**・**片開き h1.2**
      ⛔ 「堤へ出る門」ではない(区画界より外は当家の地ではない)。**足元の水を見せる口**で
        **見所⑫を兼ねる**(`nishi.mikoro[0]`「木戸の敷居(堀端)」・立って見る)。
      ⛔ 桟橋・船着・水汲みの段を付けない。
      ⚠ 柵は h1.4 で**下げない**(`nishi.saku._`)。潜りだけ 1.2 に落とすので、
        頭貫の上に 0.2 の抜けが残る — そこは柵と同じ横木2段で埋めてある。

【⚠⚠ W6 の食い違い(普請奉行へ)】同じ開口について指図が3つの数を持っている:
    ① `gap.from/to` の差 = **3.00間**(5.454m)
    ② `gap._` の文言   = **1.6間**(2.909m)
    ③ 塀の実際の口     = 塀の端 `b` が v111.25 なので **109.4〜111.25 = 1.85間**(3.363m)
  ⭕ ここでは**②(文言の 1.6間)を採って焼いた** — 人が読む文が一番新しい裁定(2026-09-03
    ユーザー裁定8=A)の帰結として書かれているため。⛔ ①③ と合っていないので、
    **指図側で1つに揃えるまで据えないこと。**

【⚠ 片開き/両開きについて — 仕様と物理が合わない】
  依頼は「片開きの板戸」だが、**2.7〜2.9m の一枚戸は建具として成立しない**
  (板の面積 4m² 超・吊り元にかかる曲げが持たない。実物の木戸は1間を超えれば両開き)。
  ⭕ **開口 1.4m 以下なら片開き、超えたら両開き**として焼いた(`leaves` で上書きできる)。
  片開きで通したいなら**開口を狭める**か**袖に羽目板の固定部を入れる**必要があり、
  どちらも塀の run の長さが動くので **普請奉行の裁定事項**。
  ⭕ 汀の潜り(1.818)は指定どおり **片開き**にした — h1.2 と低く、農家の門扉と同じ寸法比で成立する。

【向きとピボット(Unity 座標)】幅=X(開口の走り)/ 高さ=Y / 厚み=Z。
  ピボット = **開口の芯・地盤レベル**(⚠ 塀の芯と揃う)。**+Z = 見え面**。
  ⇒ のし塀の run と同じ yaw を与えれば面が揃う。⚠ **X の実寸は開口より柱2本ぶん広い**
  (下の実測)。塀の run はこの外側に取り付くので、**開口の値ではなく実寸で継ぐこと**。

【⭕ 小壁は「練塀そのものを切って載せる」(`--neribei`)】
  ⛔ 板や無地の箱で埋めない — 隣の練塀と面が変わって、門の上だけ別の材に見える。
  ⭕ 在庫の駒 `edogoyomi/es_dobei/s_hei_center.obj` を **Unity の `DobeiRun` と同じ組**
     (同じ駒を法線方向に **世界 0.20m** 離して2枚)で並べ、**天端側だけ**水平に bisect して載せる。
     ⇒ 瓦・漆喰・下見板・目地・材質名(`s_heimap`)がそのまま隣の run へ続く。
  ⚠ **ピボットの厚み方向は芯対称ではない。**`DobeiRun` は**外側の1枚の bbox 中心**を
     run の線に乗せるので、部材も同じにしてある(外へ 0.58 / 内へ 0.78)。
     芯対称に寄せると隣の run と両面で 0.10 ずつ食い違う。
  ⚠ 方立柱・冠木(まぐさ)・敷居は**塀の厚みいっぱい**に通す。通さないと口の側面から
     壁の中の空洞が見える(`_posts(dep=…)`)。
  ⚠ 走り方向は駒の**継ぎピッチ 2.995m の真ん中**を切っているので、部材の中に継ぎ目は無い。
     ⭕ ただし **run 側の割付の位相とは合わない** — 両小口で瓦の柄が1枚ぶんずれる。

【材】`wood` / `Foundation_A_01`(Village Kit)+ `s_heimap`(edogoyomi 練塀)。
  ⛔ 新規マテリアルを作らない。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_obi_nagaya as N

OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD, WALL, STONE = N.WOOD, N.WALL, N.STONE

# 指図 kekkai[].gap の2口(⚠ W6 は文言の 1.6間 を採る。docstring の【W6の食い違い】)
KEKKAI_GAPS = [1.5 * 1.818, 1.6 * 1.818]

# ---- 練塀の素(小壁に使う)。⛔ **壁を自作しない** — 在庫の駒をそのまま切って載せる ----
# ★ 正典は **Unity の `EdoNishiTameikeBuilder.DobeiRun`**(シーンの練塀を実際に並べている所)。
#   `s_hei_center` は **厚み 0.088 の薄い1枚壁**(屋根は両側へ対称に出る)で、
#   run は同じ駒を **2枚、法線方向に 0.20m 離して**並べて厚みのある練塀にしている。
#   ⛔ 1枚だけ切って載せると、隣の run より 0.20m 薄い壁が門の上にだけ立つ。
#   ⚠⚠ **`build_kado.load_pair` の組(走り +0.956 / 法線 −0.2 を「生」で)とは別物。**
#      あちらは生寸なので世界では 0.364m 離れる(DobeiRun の 0.20 の 1.8 倍)。
#      ここは **DobeiRun に合わせる** — 隣に立つのは run のほうだから。
DOBEI_SRC   = os.path.join(V.REPO, "Assets/edogoyomi/es_dobei/s_hei_center.obj")
DOBEI_PITCH = 1.6449          # 生の継ぎピッチ(=1間)。⚠ 組の bbox 3.556 ではない
DOBEI_XC    = -0.4778         # 素の bbox の走り方向の中心(生)。DobeiRun は bbox 中心で据える
DOBEI_GAP   = 0.20            # 2枚の間隔[**世界 m**]。DobeiRun の `outward * -0.2`
# ⇒ 組の厚みは 世界 1.351(内へ 0.776 / 外へ 0.576)で、**芯対称ではない**。
#   外側の1枚の bbox 中心が run の線に乗るので、**部材のピボットもそこに置く**。


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def _read_obj(path):
    """.obj を1メッシュで読む(Y-up → Z-up。走り=X / 法線=Y / 高さ=Z)"""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='Z', up_axis='Y')
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    V.sel(meshes)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return V.join(meshes, "hei")


def _bisect(o, co, no, keep_plus):
    """平面 (co, no) で切って片側を捨てる。keep_plus=True なら法線側を残す。
    ⚠ **boolean を使わない** — 瓦の非多様体な面で解けない(README)。
    ⚠ bisect は面を持たない頂点・辺を残す。消さないと **bbox が嘘をつく**(README)。"""
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=Vector(no),
                           clear_outer=not keep_plus, clear_inner=keep_plus)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()


def neribei_koba(z_cut, wall_top, wall_h, half, name="koba"):
    """**練塀の天端側を切り出した小壁。** 木戸の頭から塀の天端までを、隣の塀と
    **同じ面・同じ材質名(`s_heimap`)**で埋める。

    ⭕ 素は在庫の駒そのもの(`edogoyomi/es_dobei/s_hei_center.obj` の表裏2枚1組)なので、
       **瓦の甍・漆喰・下見板・目地が隣の run とそのまま続く**。⛔ 板で代用しない。
    ⚠ **切るのは天端側だけ**にする(下端 `z_cut` で水平に bisect)。走りは ±`half`。
      ⇒ 切り口は下端と両小口の3面で、いずれも冠木(まぐさ)と隣の塀に隠れる。
    戻り値 (オブジェクト, 切り口での塀の厚み (y0, y1))。冠木はこの厚みで塞ぐ。"""
    sheet = _read_obj(DOBEI_SRC)
    mn, mx = V.bbox([sheet])
    sc = wall_h / (mx.z - mn.z)                 # 生の丈 1.4553 → 指図の塀の丈へ
    hw = half / sc                              # 走りの半幅(生)
    n = int(hw / DOBEI_PITCH) + 2               # 端まで届くだけ駒を並べる(余りは切る)
    parts = []
    for k in range(-n, n + 1):
        for back in (False, True):
            # ⚠ `sheet` は素のまま置いておき、**毎回そこから複製する**。
            #   1枚目に sheet 自身を使うと、焼き込んだ移動が後の複製に乗る
            o = sheet.copy(); o.data = sheet.data.copy()
            bpy.context.collection.objects.link(o)
            # 内側の1枚は 180° 回す(DobeiRun の psi+180)。素は厚み方向に対称なので
            # 効くのは走りの鏡映だけ — 継ぎ目の柄が表裏で互い違いになる
            xc = DOBEI_XC
            if back:
                o.rotation_euler = (0.0, 0.0, math.pi)
                xc = -DOBEI_XC
            # DobeiRun は **bbox 中心**を割付点へ寄せる。素のピボットではない
            o.location = (k * DOBEI_PITCH - xc, (-DOBEI_GAP / sc) if back else 0.0, 0.0)
            # ⚠ transform_apply の既定は3つとも True(README)。明示して焼く
            V.sel([o])
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
            parts.append(o)
    bpy.data.objects.remove(sheet, do_unlink=True)
    V.dedup_materials()                         # s_heimap.001… を元の名前へ寄せる
    o = V.join(parts, name)
    V.sel([o])
    bpy.ops.transform.resize(value=(sc, sc, sc), center_override=(0, 0, 0))
    bpy.ops.object.transform_apply(scale=True)
    # ⚠ 厚み方向は**動かさない** — 外側の1枚の芯が y=0(= run の線)に乗ったままにする。
    #   芯対称に寄せると、隣の run との面が両側 0.10 ずつ食い違う
    o.location = (0.0, 0.0, wall_top - wall_h)
    V.sel([o]); bpy.ops.object.transform_apply(location=True)
    _bisect(o, (0, 0, z_cut), (0, 0, 1), True)          # 下を捨てる
    _bisect(o, (half, 0, 0), (1, 0, 0), False)          # 右の小口
    _bisect(o, (-half, 0, 0), (1, 0, 0), True)          # 左の小口
    # 切り口の高さでの厚み = 壁体そのもの(瓦の軒はここより上)。冠木でここを塞ぐ
    ys = [v.co.y for v in o.data.vertices if v.co.z < z_cut + 0.06 * wall_h]
    return o, (min(ys), max(ys))


def _posts(m, P, w, H, post, base=True, dep=None):
    """開口の両脇の方立柱(+ 沓石)。戻り値は柱の外面の x
    ⚠ `dep`(厚み方向の y0,y1)を渡すと**柱を塀の厚みいっぱいの方立**にする。
      塀に開けた口では必ず渡すこと — 渡さないと口の側面に**壁の中の空洞が見える**。"""
    px = w / 2.0 + post / 2.0
    d0, d1 = dep if dep else (-post / 2, post / 2)
    for s in (-1, 1):
        m.box(s * px - post / 2, s * px + post / 2, 0.02, H, d0, d1,
              VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
        if base:
            m.box(s * px - 0.17, s * px + 0.17, -0.14, 0.06,
                  min(d0 - 0.02, -0.17), max(d1 + 0.02, 0.17),
                  VM.sub(P['suv'], 0, 0, 0.4, 0.4), STONE)
    return px + post / 2.0


def kido(w=2.727, name=None, H=1.80, leaves=None, uchi=None, neribei=None):
    """**結界の木戸**(のし塀の開口を塞ぐ)。方立柱2本 + 冠木 + 敷居 + 板戸。
    ⚠ `leaves` を省くと **開口 1.4m 以下=片開き / 超えたら両開き**(docstring の理由)。

    ⚠ **`H` は部材の天端(埋め板の上端)で、`uchi` は内法(冠木の下端=戸の丈)。**
      指図が「丈」としてどちらを言っているかで値が変わるので**両方を報告する**
      (建仁寺垣で玉縁の天端と垣の丈を取り違えたのと同じ罠)。省くと従来どおり `H−0.30`。"""
    name = name or ("Kido_" + fmt(w))
    n = leaves if leaves else (1 if w <= 1.4 else 2)
    P = N.palette()
    POST = 0.13
    UCHI = (H - 0.30) if uchi is None else uchi       # 内法(冠木の下端)
    HALF = w / 2 + POST / 2 + 0.17                    # 沓石まで含めた部材の半幅
    koba, thk = None, None
    kabuki_d, sill_d = (-0.075, 0.075), (-0.105, 0.105)   # 小壁なしの従来値(変えない)
    if neribei:
        # ⭕ **小壁は練塀そのものを切って載せる**(隣の run と面・材質名が続く)。
        #   塀の座 = H − neribei / 天端 = H。⛔ 木の板で埋めない
        koba, thk = neribei_koba(UCHI + 0.17, H, neribei, HALF)
        kabuki_d = sill_d = thk        # 冠木=まぐさ・敷居とも塀の厚みいっぱいに通す
    m = VM.Mesh()
    ex = _posts(m, P, w, H if koba is None else UCHI + 0.17, POST, dep=thk)
    # 冠木。小壁を載せるときは**塀の厚みいっぱいのまぐさ**にして、切り口の下端を塞ぐ
    # (⛔ 塞がないと真下から見上げたとき壁の中が抜けて見える)
    m.box(-ex - 0.09, ex + 0.09, UCHI, UCHI + 0.17, kabuki_d[0], kabuki_d[1],
          VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.50), WOOD)
    if koba is None:
        # 上の埋め板(塀の天端まで通す)。⚠ 小壁を載せるときは要らない
        m.box(-w / 2, w / 2, UCHI + 0.17, H, -0.045, 0.045,
              VM.sub(P['wuv'], 0.05, 0.55, 0.95, 0.85), WOOD)
    # 敷居。⛔ 抜けたままにしない(足元から向こうが透ける)。塀の口では厚みいっぱいに通す
    m.box(-ex, ex, 0.0, 0.08, sill_d[0], sill_d[1],
          VM.sub(P['wuv'], 0.30, 0.10, 0.85, 0.30), WOOD)
    # 板戸。⛔ 板1枚で出さない — 竪板と桟を実体で起こす(`door_leaves` が受け持つ)
    # ⚠ **戸を開口より一回り大きく作って枠の裏へ回す。**開口ぴったりに作ると、
    #   framing との隙(数 mm)から向こうが透けて、立面で**戸の周りが白く縁取られる**
    #   (2026-09-04 に実見)。戸は柱より奥(−Z)に吊るので、はみ出しは表から見えない。
    # ⚠ 両開きのとき `door_leaves` は召し合わせのために**各戸を 0.03 内へ寄せる**ので、
    #   0.025 の被りでは相殺されて 5mm の隙が残る(実見)。0.06 取って確実に柱の裏へ回す
    N.door_leaves(m, P, -w / 2 - 0.06, w / 2 + 0.06, 0.055, UCHI + 0.02, 0.0, 1, n=n)
    o = m.to_object(name, [P['wood'], P['wall'], P['stone'], P['shoji']])
    if koba is not None:
        o = V.join([o, koba], name)               # 材質スロットに `s_heimap` が加わる
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[kido] %-14s 開口 %.3f / 内法高 %.2f / 戸 %d枚(%s)"
          % (name, w, UCHI, n, "片開き" if n == 1 else "両開き"))
    if koba is not None:
        print("[kido] %-14s 小壁 = 練塀 `s_hei_center` の天端側 %.2f〜%.2f(塀の丈 %.2f)"
              " / 方立・まぐさ・敷居の厚み %.3f(y %.3f〜%.3f)"
              % (name, UCHI + 0.17, H, neribei, thk[1] - thk[0], thk[0], thk[1]))
    return o, name


def horikido(w=1.818, name="HoriKido"):
    """**汀の柵の潜り**(`nishi.saku.kuguri`・辺5 の s=55.7)。幅1間・**片開き h1.2**。
    ⛔ 「堤へ出る門」ではない — **足元の水を見せる口**で、敷居が**見所⑫**を兼ねる。
    ⛔ 桟橋・船着・水汲みの段を付けない。
    ⚠ 柵は h1.4 のままなので、潜り(1.2)の上に残る 0.2 は**柵と同じ横木2段**で埋める。
    ⭕ 戸は**縦の簀子**にした — 閉めても足元の水が透けて、見所として働く。"""
    P = N.palette()
    FH, KH, POST = 1.40, 1.20, 0.11               # 柵の高さ / 潜りの内法 / 柱
    m = VM.Mesh()
    ex = _posts(m, P, w, FH, POST)
    # 頭貫(潜りの内法)と、その上の柵の横木2段
    m.box(-ex, ex, KH, KH + 0.135, -0.055, 0.055,   # ⚠ 上の横木と 1cm 重ねる(隙が透ける)
          VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.50), WOOD)
    # ⚠ 頭貫の天端(1.31)と柵の天端(1.40)のあいだは 0.09 しかない。**横木は1本**。
    #   2本入れると重なって、上が1枚の広い板に見える(2026-09-04 に実見)
    m.box(-ex, ex, FH - 0.075, FH, -0.035, 0.035,
          VM.sub(P['wuv'], 0.30, 0.40, 0.90, 0.60), WOOD)
    # 敷居 = **見所⑫の足元**。⛔ 段を付けない(桟橋・水汲みの段の禁止に触れる)
    m.box(-ex, ex, -0.02, 0.07, -0.09, 0.09,
          VM.sub(P['wuv'], 0.30, 0.10, 0.85, 0.30), WOOD)
    # 潜り戸(片開き)— 框を組んで中は縦の簀子。⛔ 板で塞がない(水が見えなくなる)
    hw = w / 2.0 + 0.022                          # ⚠ 枠の裏へ回す(隙から透けるのを防ぐ)
    y0, y1 = 0.055, KH + 0.015
    zf, zb = -0.020, -0.055
    for (a, b) in ((-hw, -hw + 0.075), (hw - 0.075, hw)):
        m.box(a, b, y0, y1, zb, zf, VM.sub(P['wuv'], 0.62, 0.05, 0.80, 0.95), WOOD)
    for (c, d) in ((y0, y0 + 0.075), (y1 - 0.075, y1), ((y0 + y1) / 2 - 0.04, (y0 + y1) / 2 + 0.04)):
        m.box(-hw, hw, c, d, zb, zf, VM.sub(P['wuv'], 0.72, 0.10, 0.92, 0.45), WOOD)
    m.koshi(-hw + 0.075, hw - 0.075, y0 + 0.075, y1 - 0.075, zb + 0.006, zf - 0.006,
            VM.sub(P['wuv'], 0.60, 0.10, 0.95, 0.90), WOOD, pitch=0.135, bar=0.030, yoko=0)
    o = m.to_object(name, [P['wood'], P['wall'], P['stone'], P['shoji']])
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[kido] %-14s 開口 %.3f / 潜りの内法 %.2f / 柵 %.2f / 片開き" % (name, w, KH, FH))
    return o, name


def shots(o, key, box):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    W, H = mx.x - mn.x, mx.z - mn.z
    # ⚠ ortho_scale は**画像の長辺**に効く。幅だけで決めると縦が切れる
    V.studio((c.x, mn.y - max(W, H) * 2.4, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H * 1500.0 / 1100) * 1.15, res=(1500, 1100))
    V.render(os.path.join(SHOT, "kido_%s_elev.png" % key))
    # ⚠ 引きは**背の高さでも決める**。幅だけで決めると小壁を載せた版で頭が切れる
    r = max(W, H) * 1.35
    V.studio((mn.x - r * 0.6, mn.y - r * 1.25, max(1.55, H * 0.80)),
             (c.x, c.y, H * 0.45), res=(1600, 1100))
    V.render(os.path.join(SHOT, "kido_%s_3d.png" % key))
    # 見上げ — まぐさが小壁の切り口を塞いでいるか(塞がないと壁の中が抜けて見える)
    V.studio((c.x + W * 0.35, mn.y - H * 0.55, 0.35), (c.x, c.y, H * 0.72),
             res=(1400, 1000))
    V.render(os.path.join(SHOT, "kido_%s_soffit.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    jobs = []
    if "kekkai" in argv:
        jobs += [(fmt(g), (lambda g=g: kido(g))) for g in KEKKAI_GAPS]
    if "horikido" in argv or not argv or all(a.startswith("--") for a in argv):
        jobs.append(("horikido", horikido))
    if "kido" in argv:
        i = argv.index("kido")
        # --H <天端m> / --uchi <内法m> / --leaves <枚数> / --name <名前>
        def opt(f, cast=float):
            return cast(argv[argv.index(f) + 1]) if f in argv else None
        H = opt("--H") or 1.80
        uchi, lv, nm = opt("--uchi"), opt("--leaves", int), (
            argv[argv.index("--name") + 1] if "--name" in argv else None)
        nb = opt("--neribei")     # 隣の練塀の丈[m]。立てると頭を小壁で埋める
        taken = set()
        for f in ("--H", "--uchi", "--leaves", "--name", "--neribei"):
            if f in argv:
                taken.add(argv[argv.index(f) + 1])
        ws = [float(a) for a in argv[i + 1:]
              if not a.startswith("--") and a not in taken]
        jobs += [(fmt(x), (lambda x=x: kido(x, name=nm, H=H, leaves=lv, uchi=uchi,
                                            neribei=nb)))
                 for x in (ws or [2.727])]
    if not jobs:
        jobs = [(fmt(g), (lambda g=g: kido(g))) for g in KEKKAI_GAPS] + [("horikido", horikido)]
    for key, fn in jobs:
        V.reset()
        o, name = fn()
        mn, mx = V.bbox([o])
        print("[kido] %-14s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  底=%.3f  面=%d  材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons),
                 [mm.name for mm in o.data.materials]))
        if "--render" in argv:
            shots(o, key, (mn, mx))       # ⚠ 書き出しの前に撮る(後だと bbox が潰れる)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[kido] 書き出し " + os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    main()
