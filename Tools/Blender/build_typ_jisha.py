"""**類型共用の寺社の部材** — 山門(四脚門)・薬医門・鐘楼(袴腰)・墓地の一画。

    blender --background --python Tools/Blender/build_typ_jisha.py -- [名前...] [--render]
    (名前を省くと全部。sanmon / yakuimon / shoro / bochi)

【なぜ新造するか】EDO-0318 ①②③(在庫方の照会 2026-09-21)。
  ・**山門** … `EdoTypologyBuilder.GatePath()` が `gate:sanmon` を `Eg.Kabukimon`
    (冠木門=棟門級)へ落としていて**格が3段違う**。寺4区画がすべて冠木門で建っていた。
  ・**薬医門** … `gate:yakuimon`(社家=神主の屋敷)も同じく冠木門へ落ちている。
    ⚠ 在庫の `Eg.Kmon` は薬医門だが **ES 後 W14.4m**(袖付きの大門)で、
    社家の屋敷門に据えると長屋門級になる。
  ・**鐘楼** … 在庫の `obj_shoro1` は **ES 後 実丈 1.45m** で、101箇所に灯籠・石造小物
    として使われている駒。建築の鐘楼(袴腰・基壇3間)には代用不可。
  ・**墓地** … 墓石・卒塔婆・囲いとも在庫に無い(近いのは `s_gorin` / `jizo2` のみ)。

【方針 — ゼロから起こさない】
  ・山門・薬医門 … 岡部の棟門 `build_munamon.build()` に 2026-09-21 に出した
    `hikae`(控柱の z 位置)ほかの引数で建てる。⛔ 別実装を書かない。
  ・鐘楼 … `build_goten_roof.make_irimoya()` の入母屋を載せ、躯体(基壇・袴腰・上層・
    高欄・梵鐘)だけここで起こす。
  ・墓地 … 小物だけなので `vkmesh.Mesh` で直に組む。⛔ 新規マテリアルを作らない。

【格の梯子 — 棟天端でこの順に並ぶ(これが「格が3段違う」の是正そのもの)】
    棟門 `Own.Munemon` 3.60 < **薬医門 4.30** < **山門(四脚門)5.10**
  ⚠ 寸法はすべて【U】。指図に欄が無く、部材方が「格の順が立面で読める」ことだけを
    条件に決めた。⛔ 史実値として名乗らせない。

【向き(Unity 座標)】幅=X / 高さ=Y / 厚み=Z。門は **+Z = 外(表)**・ピボットは門の芯・
  敷居レベル。鐘楼と墓地は **ピボット = footprint の中心・地盤レベル**。

【材】⛔ 新規に作らない。`wood` / `wall C` / `Foundation_A_01` / `roof` / `roof ornaments`。
      ⚠ 鐘楼の基壇と墓地だけは切石 `Kirishi`(玉石の Foundation_A_01 を基壇に当てない)。
"""
import bpy, sys, os, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as R
import build_obi_nagaya as N          # 材の借用・妻まわり・切妻屋根
import build_munamon as MM            # 棟門の生成器(控柱の引数つき)
import build_sanno_buzai as SB         # 切石の材 `Kirishi`(⭕ main は __main__ 束縛なので安全)

KEN  = 1.818
OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Mon"))
OUTJ = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Jisha"))
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD, WALL, STONE = N.WOOD, N.WALL, N.STONE
KIRI = 4                              # 切石(墓石・囲い)のマテリアルスロット
JC_MESH = os.path.join(V.REPO, "Assets", "Japanese Castle", "Meshes")
JC_TEX  = os.path.join(V.REPO, "Assets", "Japanese Castle", "Textures")


# ================================================================ 山門(四脚門)
def sanmon():
    """**山門 — 四脚門**。門口 **2間(3.636m)**・本柱2本 + 控柱4本・切妻本瓦・棟天端 **5.10**。

    ⭐ 町場の寺の山門は四脚門(本柱の前後に控柱)が常法で、**棟が本柱の真上**に来る
    左右対称の切妻。⛔ 冠木門(`Eg.Kabukimon`)で代用しない — 屋根も控柱も無い門で、
    寺の表構えとしては3段格が低い。

    ⚠ 寸法【U】: 門口2間は「駕籠が通る」最小、有効高 3.10 は門口の 0.85 倍、
      控柱は本柱から **±1.30m**(前後に出す=四脚)。⛔ 史料値ではない。

    ローカル **+X = 門口の方向 / +Z = 外(参道の側)**。ピボット = 門の芯・敷居レベル。
    ⚠ 底は沓石が敷居より下へ出るぶん負になる(実測は下の print)。"""
    o, _n = MM.build(w=2.0 * KEN, name="Typ_Sanmon", post=0.36, kabuki=3.10,
                     keats=3.95, deep=3.40, noki=0.85, end=0.34, ridge=5.10,
                     hikae=(-1.30, 1.30), hikae_post=0.27)
    return o, "Typ_Sanmon"


# ================================================================ 薬医門
def yakuimon():
    """**薬医門**。門口 **1.65間(3.00m)**・本柱2本 + **控柱2本(後ろだけ)**・棟天端 **4.30**。

    ⭐ 薬医門は**棟が本柱の上**に来て、後ろの流れの下に控柱が入る(左右対称の切妻)。
    社家(神主の屋敷)の門の格。⛔ 在庫の `Eg.Kmon` で代用しない — あれは ES 後 W14.4m の
    袖付きの大門で、屋敷門に据えると長屋門級になる。

    ⚠ 寸法【U】: 門口 3.00 は棟門(2.70)と山門(3.64)の間、控柱は本柱の後ろ **1.15m**。

    ローカル **+X = 門口の方向 / +Z = 外**。**控柱は −Z(内)側**なので、
    据えるときに +Z を表へ向けないと控柱が通りに出る。ピボット = 門の芯・敷居レベル。"""
    o, _n = MM.build(w=3.00, name="Typ_Yakuimon", post=0.30, kabuki=2.70,
                     keats=3.35, deep=3.00, noki=0.75, end=0.30, ridge=4.30,
                     hikae=(-1.15,), hikae_post=0.23)
    return o, "Typ_Yakuimon"


# ================================================================ 鐘楼(袴腰)
def shoro(ken=3.0):
    """**鐘楼 — 袴腰(はかまごし)**。基壇 ken 間角・袴腰・上層は吹き放ち・入母屋本瓦・梵鐘つき。

    ⭐ 在庫の `obj_shoro1` は **ES 後 実丈 1.45m** の石造小物(101箇所で灯籠として使用中)で、
    建築の鐘楼には代用できない。⛔ 拡大して代用しない — 彫りが灯籠のままになる。

    【組み立て — 下から】
      ① **基壇** 切石積 ken 間角・高 0.55。⛔ 地面に直に建てない(鐘楼は必ず壇に載る)
      ② **袴腰** 高 0.55→2.60。**下が広く上が狭い**台形の板張り(これが袴腰)。
         ⛔ 逆テーパにしない — 上が広いと物見櫓に見える
      ③ **上層** 柱間 2間(3.636m)・柱 0.30角・高 2.60→4.75 の**吹き放ち**。
         四周に **高欄**(2.60 の縁の上)。⛔ 塞ぐと鐘が見えず蔵になる
      ④ **梵鐘** 口径 0.95 × 丈 1.55。上層の芯に **竜頭を桁から吊る**。
         ⚠ 材は `roof ornaments`(鬼瓦の暗い材)を当てた【U】— 在庫に金属の材が無い。
      ⑤ **入母屋** `build_goten_roof.make_irimoya` の実瓦。

    ⚠ 寸法はすべて【U】。棟天端は瓦の勾配 0.5456 からの**従属値**(実測は下の print)。
    ローカル ピボット = **footprint(基壇)の中心・地盤レベル**。四方どこから見ても同じ。"""
    P = N.palette()
    RP = R.palette()
    name = "Typ_Shoro_%sken" % N.fmt(ken)
    m = VM.Mesh()
    B = ken * KEN / 2.0                 # 基壇の半幅
    pillar = 2.0 * KEN / 2.0            # 上層の柱の芯(柱間2間)
    z_dan, z_koshi, z_keta = 0.55, 2.60, 4.75

    # ① 基壇(切石積)。天端をわずかに絞って段に見せる
    # ⭐ 材は **`Kirishi`**(切石)。⛔ 2026-09-21 に `STONE`(= Foundation_A_01・玉石積み)で焼いて
    #   EdoAssets.Own.Shoro の注記と食い違った(EDO-0318 ⑦)。玉石の材を基壇に当てると
    #   「小石を盛った台」に見える — 墓地の囲いと同じ切石に揃える。
    kiri = SB.kirishi_material()
    suv = (0.06, 0.06, 0.52, 0.52)          # 切石はタイル材 — 小さい駒には一部だけ当てる
    m.box(-B, B, 0.0, z_dan * 0.62, -B, B, suv, KIRI)
    m.box(-B + 0.10, B - 0.10, z_dan * 0.62, z_dan, -B + 0.10, B - 0.10, suv, KIRI)

    # ② 袴腰 — 下 hb・上 ht の台形。4面を quad で張る(⛔ box で立てると垂直になる)
    hb, ht = B - 0.24, pillar + 0.26
    # ⛔ **一面を1枚の quad で張らない。**2026-09-21 に焼いたら木理が面いっぱいに
    #   引き伸ばされて大理石のような渦になった(README「UV は一点貼りにしない」)。
    #   ⇒ 竪板 0.30m 見当に割り、板ごとに UV の帯を変える。
    NB = max(4, int(round(2 * hb / 0.30)))
    for k in range(4):
        a = math.pi / 2.0 * k
        ca, sa = math.cos(a), math.sin(a)
        def rot(u, v):                                  # (走り, 厚み) → (x, y)
            return (u * ca - v * sa, u * sa + v * ca)
        for i in range(NB):
            t0, t1 = i / float(NB), (i + 1) / float(NB)
            band = (i % 4) * 0.23
            uv = VM.sub(P['wuv'], 0.04, band, 0.96, band + 0.23)
            b0, b1 = -hb + 2 * hb * t0, -hb + 2 * hb * t1
            u0, u1 = -ht + 2 * ht * t0, -ht + 2 * ht * t1
            p0 = rot(b0, -hb); p1 = rot(b1, -hb)
            p2 = rot(u1, -ht); p3 = rot(u0, -ht)
            m.quad([(p0[0], z_dan, p0[1]), (p1[0], z_dan, p1[1]),
                    (p2[0], z_koshi, p2[1]), (p3[0], z_koshi, p3[1])], uv, WOOD)
    # 袴腰の天端の水切り(板の小口を切れっぱなしにしない)
    m.box(-ht - 0.10, ht + 0.10, z_koshi - 0.06, z_koshi + 0.04, -ht - 0.10, ht + 0.10,
          VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80), WOOD)

    # ③ 上層 — 柱4本(吹き放ち)+ 桁 + 高欄
    for sx in (-pillar, pillar):
        for sz in (-pillar, pillar):
            m.box(sx - 0.15, sx + 0.15, z_koshi, z_keta, sz - 0.15, sz + 0.15,
                  VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
    for sz in (-pillar, pillar):        # 桁(X 方向)
        m.box(-pillar - 0.22, pillar + 0.22, z_keta - 0.26, z_keta, sz - 0.11, sz + 0.11,
              VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)
    for sx in (-pillar, pillar):        # 梁(Z 方向)
        m.box(sx - 0.11, sx + 0.11, z_keta - 0.26, z_keta, -pillar - 0.22, pillar + 0.22,
              VM.sub(P['wuv'], 0.30, 0.15, 0.90, 0.45), WOOD)
    # 高欄(縁の上)。⛔ 1枚板にしない — 親柱 + 架木 + 立子
    # ⛔ `Mesh.koshi` は**竪子を必ず X 方向に並べる**。東西の面(走りが Z)に当てると
    #   幅 0.10 に竪子2本が詰まって **板1枚の腰壁**になる(2026-09-21 に焼いて実見)。
    #   ⇒ Z 走りの2面は竪子を手で並べる。
    gr = ht + 0.06
    kuv = VM.sub(P['wuv'], 0.60, 0.10, 0.95, 0.90)
    y0, y1 = z_koshi + 0.06, z_koshi + 0.74
    for sz in (-gr, gr):                                   # 南北(走りは X)
        za, zb = sorted((sz, sz - (0.10 if sz > 0 else -0.10)))
        m.koshi(-gr, gr, y0, y1, za, zb, kuv, WOOD, pitch=0.21, bar=0.045, yoko=2)
    for sx in (-gr, gr):                                   # 東西(走りは Z)— 手で並べる
        xa, xb = sorted((sx, sx - (0.10 if sx > 0 else -0.10)))
        n = max(2, int((2 * gr) / 0.21))
        for i in range(n):
            cz = -gr + 2 * gr * (i + 0.5) / n
            m.box(xa, xb, y0, y1, cz - 0.045, cz + 0.045, kuv, WOOD)
        for j in range(2):                                 # 架木・地覆
            cy = y0 + (y1 - y0) * (j + 0.5) / 2.0
            m.box(xa - 0.008, xb + 0.008, cy - 0.045, cy + 0.045, -gr, gr, kuv, WOOD)

    # ④ 梵鐘 — 桁から吊る。⚠ 材は `roof ornaments`(在庫に金属の材が無い)【U】
    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji'], kiri])
    bell = _bell(name + "_bell", z_keta - 0.26)
    # ⑤ 入母屋
    roof = R.make_irimoya(2.0 * pillar, 2.0 * pillar, name + "_roof", eave=0.95)
    roof.location = (0.0, 0.0, z_keta)
    bpy.context.view_layer.update()
    V.sel([roof]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.dedup_materials()
    o = V.join([body, bell, roof], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o]); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print("[jisha] %-22s 基壇 %.2f角 / 縁 %.2f / 桁 %.2f / 柱間 2間" % (name, ken * KEN, z_koshi, z_keta))
    return o, name


def _bell(name, top):
    """**梵鐘**(口径 **0.95** × 丈 **1.55**)を `top`(桁の下端)から吊る。輪切りを重ねた旋盤形。

    ⛔⛔ **断面は「天(竜頭)からの丈」で書く。**2026-09-21 に「底からの丈」で書いて
      **上が広く下がすぼまった逆さの鐘**(手桶に見えた)を焼いた。鐘は**口(下)が一番広い**。
    ⭕ 材は Japanese Castle の **`Ornament`**(金具の材。`_MetallicSmoothness` を持つ黒い金属)。
      ⚠ 先に `roof ornaments`(鬼瓦)を当てたら淡い縞の灯籠に見えた — 鬼瓦のアトラスは
        瓦の鱗と木部が同居していて、どこを切っても鐘の肌にならない。
      ⚠ JC の材は `V.TEX`(Village Kit)から引けないので **`_hook_jc()` で別に結線する** —
        忘れると鐘だけ真っ白のままレンダされる(同日に踏んだ)。
    ⚠ 口は**塞ぐ**。開けたままだと見上げたときに鐘の中と空が抜ける。"""
    H = 1.55                                   # 丈【U】⚠ 0.78×1.30 では灯籠に見えた(09-21)
    # (天からの丈, 半径) — **下へ行くほど太る**
    prof = [(0.00, 0.10), (0.09, 0.21), (0.24, 0.31), (0.50, 0.385),
            (0.90, 0.442), (1.30, 0.471), (1.48, 0.475), (H, 0.470)]
    bmat, brect = VM.ext_mat(V, JC_MESH, JC_TEX, "Interior/Ornament.fbx", "Ornament",
                             (0.06, 0.03, 0.30, 0.30))
    m = VM.Mesh()
    NSEG = 18
    def uvb(i):
        """⚠ 一点貼りにしない — 輪切りごとに帯をずらして、縦帯・乳の陰影を出す。"""
        v = (i % 3) * 0.08
        return VM.sub(brect, 0.05, 0.05 + v, 0.95, 0.30 + v)
    for i in range(len(prof) - 1):
        h0, r0 = prof[i]
        h1, r1 = prof[i + 1]
        z0, z1 = top - h0, top - h1
        uv = uvb(i)
        for k in range(NSEG):
            a0 = 2 * math.pi * k / NSEG
            a1 = 2 * math.pi * (k + 1) / NSEG
            m.quad([(r0 * math.cos(a0), z0, r0 * math.sin(a0)),
                    (r0 * math.cos(a1), z0, r0 * math.sin(a1)),
                    (r1 * math.cos(a1), z1, r1 * math.sin(a1)),
                    (r1 * math.cos(a0), z1, r1 * math.sin(a0))], uv, 0)
    # 天(笠形)を塞ぐ
    for k in range(NSEG):
        a0 = 2 * math.pi * k / NSEG
        a1 = 2 * math.pi * (k + 1) / NSEG
        r = prof[0][1]
        m.tri([(0.0, top + 0.02, 0.0), (r * math.cos(a1), top, r * math.sin(a1)),
               (r * math.cos(a0), top, r * math.sin(a0))], uvb(0), 0)
    # 口(下端)を塞ぐ。⛔ 面いっぱいでなく 0.06 引っ込めて、縁の厚みを見せる
    zb, rb = top - H, prof[-1][1] - 0.04
    for k in range(NSEG):
        a0 = 2 * math.pi * k / NSEG
        a1 = 2 * math.pi * (k + 1) / NSEG
        m.tri([(0.0, zb + 0.06, 0.0), (rb * math.cos(a0), zb + 0.06, rb * math.sin(a0)),
               (rb * math.cos(a1), zb + 0.06, rb * math.sin(a1))], uvb(2), 0)
    # 竜頭(吊り手)— 桁へ届かせる。⛔ 抜くと鐘が宙に浮いて見える
    m.box(-0.07, 0.07, top + 0.01, top + 0.30, -0.16, -0.10, uvb(1), 0)
    m.box(-0.07, 0.07, top + 0.01, top + 0.30, 0.10, 0.16, uvb(1), 0)
    m.box(-0.07, 0.07, top + 0.24, top + 0.30, -0.16, 0.16, uvb(1), 0)
    return m.to_object(name, [bmat])


def _hook_jc():
    """Japanese Castle の材(`Ornament` など)を JC のテクスチャ棚から結線する。
    ⚠ `V.hook_textures()` は Village Kit の `textures/` しか見ないので、JC の材は素通しになる。
    ⛔ **VK の結線より先に呼ぶ** — ここで見つからない VK の材は素通りするだけで壊れない。"""
    keep = V.TEX
    V.TEX = JC_TEX
    try:
        V.hook_textures()
    finally:
        V.TEX = keep


# ================================================================ 墓地の一画
def bochi(wKen=6.0, dKen=4.0):
    """**墓地の一画** wKen × dKen 間。**切石の低い囲い + 墓石の列 + 卒塔婆**の一式。

    ⭐ 在庫に墓石・卒塔婆・囲いのいずれも無い(近いのは `s_gorin` の五輪塔と `jizo2` だけ)。
    ⛔ 1基ずつ Unity 側で撒かない — 撒き方は区画ごとに変わらず、**一画を一体で焼くほうが
      安い**(類型ビルダーは棟を置く器しか持たない・規則21 の「部材どうしを突き付ける」
      対象でもない)。⇒ 寺ごとに向きだけ変えて据える。

    【組み立て】
      ・**囲い** 切石の低い縁石(天端 0.28)。四周。⛔ 塀にしない — 墓地の囲いは腰の高さ
      ・**材** 墓石・囲いとも **`Kirishi`**(山王の段石のために起こした淡灰・平滑の切石)。
        ⛔ `Foundation_A_01` を当てない — あれは**玉石(丸石)積み**の材で、2026-09-21 に
        焼いたら墓石が「小石を積んだ山」に見えた。墓石は叩き仕上げの切石。
      ・**墓石** **半間(0.909m)ピッチ**の格子に、3型(角柱・櫛形・板碑)を**決まった種で**散らす。
        ⚠ 乱数の種を固定してあるので、同じ寸法なら何度焼いても同じ並びになる
      ・**卒塔婆** 墓石の後ろに 1〜3枚。厚 0.03 の細板(`wood`)
      ・⛔ **供花・線香立ては置かない** — 引きで読めず面数だけ増える

    ⚠ 墓石の姿【U】: 角柱型 0.24角×0.78 / 櫛形 0.30幅×0.68 / 板碑 0.34幅×0.52。
      安政3年の江戸の墓標としては角柱型が主流【一般類型 B】だが、区画ごとの実態の
      史料は当プロジェクトに無い。

    ローカル 幅=X / 高さ=Y / 厚み=Z。ピボット = **一画の中心・地盤レベル**。
    ⭕ 向きは四方どれでもよい(正面が無い)。"""
    P = N.palette()
    name = "Typ_Bochi_%sx%sken" % (N.fmt(wKen), N.fmt(dKen))
    m = VM.Mesh()
    W, D = wKen * KEN, dKen * KEN
    hw, hd = W / 2.0, D / 2.0
    kiri = SB.kirishi_material()
    suv = (0.06, 0.06, 0.52, 0.52)          # 切石はタイル材 — 小さい駒には一部だけ当てる
    wuv = VM.sub(P['wuv'], 0.05, 0.05, 0.95, 0.95)

    # ---- 囲い(切石の縁石)。天端 0.28・見付 0.22
    for (x0, x1, z0, z1) in ((-hw, hw, -hd, -hd + 0.22), (-hw, hw, hd - 0.22, hd),
                             (-hw, -hw + 0.22, -hd + 0.22, hd - 0.22),
                             (hw - 0.22, hw, -hd + 0.22, hd - 0.22)):
        m.box(x0, x1, 0.0, 0.28, z0, z1, suv, KIRI)

    # ---- 墓石の列。⚠ 種を固定(同じ寸法なら同じ並び)
    seed = 1856
    def rnd():
        nonlocal seed
        seed = (seed * 1103515245 + 12345) & 0x7fffffff
        return seed / float(0x7fffffff)

    # ⚠ 芯々は **半間(0.909m)** — 1間ピッチにすると 4×3間 で 6基しか立たず、
    #   「墓地」でなく「石が数個置いてある空地」になった(2026-09-21 に焼いて実見)。
    nx = max(1, int(round(wKen * 2)) - 1)
    nz = max(1, int(round(dKen * 2)) - 1)
    n_haka = 0
    for iz in range(nz):
        for ix in range(nx):
            cx = -hw + W * (ix + 1) / float(nx + 1)
            cz = -hd + D * (iz + 1) / float(nz + 1)
            if rnd() < 0.18:                     # 2割ほどは空き(詰め切らない)
                continue
            n_haka += 1
            kind = rnd()
            jx, jz = (rnd() - 0.5) * 0.18, (rnd() - 0.5) * 0.18
            x, z = cx + jx, cz + jz
            m.box(x - 0.30, x + 0.30, 0.0, 0.16, z - 0.30, z + 0.30, suv, KIRI)   # 台石
            if kind < 0.55:                      # 角柱型(江戸後期の主流)
                m.box(x - 0.12, x + 0.12, 0.16, 0.94, z - 0.11, z + 0.11, suv, KIRI)
                m.box(x - 0.14, x + 0.14, 0.94, 1.00, z - 0.13, z + 0.13, suv, KIRI)  # 笠
            elif kind < 0.82:                    # 櫛形(頭が丸い)
                m.box(x - 0.15, x + 0.15, 0.16, 0.74, z - 0.08, z + 0.08, suv, KIRI)
                m.box(x - 0.13, x + 0.13, 0.74, 0.84, z - 0.07, z + 0.07, suv, KIRI)
                m.box(x - 0.09, x + 0.09, 0.84, 0.90, z - 0.06, z + 0.06, suv, KIRI)
            else:                                # 板碑(低い板状)
                m.box(x - 0.17, x + 0.17, 0.16, 0.62, z - 0.06, z + 0.06, suv, KIRI)
                m.box(x - 0.12, x + 0.12, 0.62, 0.70, z - 0.05, z + 0.05, suv, KIRI)
            # 卒塔婆(墓石の後ろ)。⛔ 全基に立てない
            for t in range(int(rnd() * 3.4)):
                ox = (t - 1) * 0.10 + (rnd() - 0.5) * 0.04
                m.box(x + ox - 0.045, x + ox + 0.045, 0.02, 1.02 + rnd() * 0.22,
                      z + 0.17, z + 0.20, wuv, WOOD)

    o = m.to_object(name, [P['wood'], P['wall'], P['stone'], P['shoji'], kiri])
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o]); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print("[jisha] %-22s %d基(格子 %d×%d)・材=切石 Kirishi" % (name, n_haka, nx, nz))
    return o, name


PARTS = {"sanmon": (sanmon, OUT), "yakuimon": (yakuimon, OUT),
         "shoro": (shoro, OUTJ), "bochi": (bochi, OUTJ)}


def shots(o, key):
    """⚠ **書き出しの前に撮る**。⛔ 地面を z=0 に敷いて足元の浮きを読む。"""
    _hook_jc()                      # ⛔ VK より先(上の断り)
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    r = max(W, H, D)
    bpy.ops.mesh.primitive_plane_add(size=max(60.0, r * 10), location=(c.x, c.y, 0.0))
    V.studio((c.x, mn.y - r * 2.4, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H) * 1.18, res=(1500, 1300))
    V.render(os.path.join(SHOT, "typ_jisha_%s_elev.png" % key))
    V.studio((mn.x - r * 0.7, mn.y - r * 1.3, 1.62), (c.x, c.y, H * 0.45), res=(1700, 1100))
    V.render(os.path.join(SHOT, "typ_jisha_%s_3d.png" % key))
    V.studio((mx.x + r * 0.7, mx.y + r * 1.3, 1.85), (c.x, c.y, H * 0.5), res=(1700, 1100))
    V.render(os.path.join(SHOT, "typ_jisha_%s_ura.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or list(PARTS.keys())
    for key in want:
        if key not in PARTS:
            print("[jisha] ⚠ 知らない部材: %s (%s)" % (key, "/".join(PARTS)))
            continue
        fn, outdir = PARTS[key]
        V.reset()
        o, name = fn()
        mn, mx = V.bbox([o])
        print("[jisha] %-22s Unity実寸 W(X)=%6.3f  H(Y)=%6.3f  D(Z)=%6.3f  底=%+.3f  面=%d"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
        print("[jisha] %-22s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
        if "--render" in argv:
            shots(o, key)
        V.export_fbx([o], os.path.join(outdir, name + ".fbx"))
        print("[jisha] 書き出し " + os.path.join(outdir, name + ".fbx"))


main()
