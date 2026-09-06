"""**土井大隅守上屋敷(刈谷2.3万石・譜代)の新造部材。**

    blender --background --python Tools/Blender/build_doi_buzai.py -- umaya kura ido chozu mizushiri
    blender --background --python Tools/Blender/build_doi_buzai.py -- ido --render
    BUZAI_OUT=/path/staging blender --background --python Tools/Blender/build_doi_buzai.py --

【方針】**ゼロから起こさない。**既に在る生成器の型を土井の寸法で呼び直すだけにする —
  厩は岡部の `build_okabe_fuzokuya.umaya`(板壁・桟瓦)、蔵と井戸は松平の
  `build_matsudaira_dewa_fuzokuya.dozo/ido`(切石の腰+白漆喰/角井戸枠)。
  ⛔ **同じ型を別の実装で二度書かない** — 直しが片方にしか入らない。
  ここで新しく起こすのは、どの邸にも無かった **手水石**と**水尻(余水吐)の石組**だけ。

【寸法の正典は `docs/Sashizu/doi_sashizu.json`】⛔ ここに数字を書き写して増やさない。
  ・厩       `munes.Umaya` = 5.5 × 7間(u × v)
  ・蔵       `service.Komegura`/`Kura1` = 3 × 8間 / `Kura2` = 3 × 3間。
             軒の下端は `const.kuraEave` = 4.84m。⚠ **棟高は指定できない**(下の注)
  ・井戸     `wells` 5口。**5口とも同じ部材**。石枠 1.30 角 × 丈 0.35(`_pending.ido`)
  ・手水石   `gardens[].yashiro.chozu` = 水盤 0.6 × 0.4m
  ・水尻     `gardens[].mizu.mizushiri` = 石の閾 / 埋樋 φ0.24 / 石敷きの落とし溝 / 受け石

【⚠ 蔵の棟高は従属値】瓦モジュールの勾配 0.5456(5.5寸)は動かせないので、
  **軒高を合わせると棟高は梁間から自動的に決まる**。指図の `const.kuraRidge` 6.51 は
  在庫 `Eg.Kura`(梁間 3.65間)の実測で、当図の梁間 3間 とは別の建物の数字。
  ⇒ **軒 4.84 を合わせて焼き、出てきた棟高を指図へ返す**(`_pending.kurabuzai`)。

【⛔ 受け石は新造しない】`mizushiri` の受け石(玉石の浸透枡)は**在庫で組める** —
  `EdoAssets.Own.Tateishi("S", 1..3)` の小径を数個伏せて据えるだけで、
  新しい FBX を足す理由が無い(指図 `bom` の断りも「`Own.Tateishi` の小径で組める」)。

【⛔ 埋樋の本体も新造しない】土被り 0.30m 以上で埋まるので地上から見えない
  (指図 `bom` の断り)。見えるのは**終点の石組の吐き口**だけなので、そこだけ焼く。

【向きとピボット(Unity 座標)】幅=X / 高さ=Y / 厚み=Z、**見え面 = +Z**。
  ピボットは部材ごとに下の docstring が明示する(⛔ 「だいたい中心」で済ませない)。
"""
import bpy, sys, os
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_matsudaira_dewa_fuzokuya as F      # Mesh / palette / dozo / ido
import build_okabe_fuzokuya as OF               # umaya(板壁・桟瓦)
import build_okabe_niwa as ON                   # 沓脱石(在庫の実岩を切る型)

KEN = 1.818
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Fuzokuya"))
SHOT = os.path.join(V.REPO, "Screenshots")

KURA_EAVE = 4.84        # 指図 const.kuraEave(地盤から軒の下端 m)


def one_stone(suv, i=0):
    """**一個の石の面**として読ませる UV を返す。

    ⛔ **切り出した石の部材にアトラスの大きな矩形を貼らない。**`Foundation_A_01` は
      玉石積みの**壁**のテクスチャなので、矩形をそのまま貼ると目地が何段も入り、
      0.6m の手水石が **2m の石垣の箱**に見える(2026-09-06 に実見)。
    ⭕ **石1個より小さい矩形**を面いっぱいへ引き伸ばすと、目地が入らず石肌の斑だけが残る。
    ⚠ 面ごとに `i` をずらして、同じ斑が四周に繰り返すのを避ける。"""
    o = ((0.34, 0.40), (0.53, 0.23), (0.27, 0.66), (0.60, 0.57),
         (0.41, 0.11), (0.14, 0.34))[i % 6]
    return F._sub(suv, o[0], o[1], o[0] + 0.10, o[1] + 0.10)


# ================================================================ 厩
def umaya():
    """**厩 5.5 × 7間**(`munes.Umaya`)。⛔ 在庫では組めない —
    `Eg.KnagayaL/R` の梁間は ES 込みで 2.36間しかなく、桁行を継いでも奥行が足りない。
    ⭕ 岡部の厩と同じ型(**板壁・桟瓦・前面は吹き放ち**)を土井の寸法で焼く。
    ⚠ **表長屋と格を分ける**(本瓦・なまこ壁にしない)のは指図 `bom` の宣言【型=B/姿=U】。
    ピボット = footprint の中心・地盤。ローカル **+X = 長手(v 方向 7間)**。"""
    # ⚠ 軒高 2.35 は**棟を表長屋(5.509)より低く納めるための逆算値**
    #   (2026-09-06 ユーザー裁定=B)。既定の 2.85 では棟 5.918 で格が逆転した。
    #   ⛔ 「厩の軒はこの高さ」という独立した根拠ではない — 表長屋の棟が動けば動く。
    # ⚠ 軒 2.35 は**棟を表長屋(5.509)より低く納めるための逆算値**(2026-09-06 裁定=B)。
    # ⚠ ⛔ **軒だけ下げると吹き放ちが塞がって厩に見えなくなる**(実見)。半高壁 1.35→1.00 と
    #   軒の出 0.85→0.55 も一緒に詰めて、帯を岡部と同等の 0.96m に戻してある。
    #   ⭕ どちらも姿=U(典拠なし)の値なので動かしてよい。⛔ 棟 5.418 は動かさない。
    return OF.umaya(uKen=5.5, vKen=7, name="Doi_Umaya_5.5x7ken",
                    eaveH=2.35, frontH=1.00, noki=0.55)


# ================================================================ 御蔵
def kura38():
    """**蔵 3 × 8間**(`service.Komegura` 御米蔵 / `Kura1` 御土蔵(文書))。
    ローカル **+X = 長手(8間)**・+Z = 梁間(3間)。ピボット = footprint の中心・地盤。
    ⚠ 観音扉は **−X の妻**に付く(据えるとき扉の向きを決めるのは yaw)。"""
    return F.dozo(uk=3, vk=8, name="Doi_Kura_3x8ken", eave=KURA_EAVE), "Doi_Kura_3x8ken"


def kura33():
    """**蔵 3 × 3間**(`service.Kura2` 御土蔵(什器))。⚠ 正方形なので長手の別は無い。"""
    return F.dozo(uk=3, vk=3, name="Doi_Kura_3x3ken", eave=KURA_EAVE), "Doi_Kura_3x3ken"


# ================================================================ 井戸
def ido():
    """**井戸**(`wells` 5口とも同じ部材)。石の角井戸枠 + 木の桁2本 + 梁 + **釣瓶**。
    ⚠ 石枠の丈は指図 `_pending.ido` の **0.35m**(松平の 0.62 より低い)。
    ⛔ **井戸屋形(屋根)は付けない** — 当図に無い【U】。
    ピボット = **井戸の芯・地盤レベル**(`wells[].u,v` をそのまま使える)。"""
    return F.ido(name="Doi_Ido", h=0.35, tsurube=True), "Doi_Ido"


# ================================================================ 手水石
def chozu():
    """**手水石(水盤)** — 稲荷の社前、参道の脇(`yashiro.chozu`)。
    水盤 **0.60(X) × 0.40(Z)**、丈 0.42(うち 0.06 を地中へ据える)。天端に 0.05 の水溜り。
    ⛔ **蹲踞・手水鉢(茶庭の露地の要素)にしない** — 当屋敷に茶室・露地は無い(指図 `bom`)。
    ⛔ 柄杓掛け・湯桶石・手燭石を添えない(同じ理由。あれは露地の役石)。
    ⭕ 据わりを出すため**基部を一回り広げ**、天端の四周に**面取りの縁**を回す。
    ピボット = **水盤の芯・地盤レベル**(`chozu.u,v` をそのまま使える。⚠ 底は −0.06)。
    材 = Village Kit `Foundation_A_01`(切石)。⛔ 新規マテリアルを作らない。"""
    (wm, wuv), (sm, suv), (pm, puv) = F.palette()
    m = F.Mesh()
    L, W, H = 0.60, 0.40, 0.42
    hx, hz = L / 2.0, W / 2.0
    # 根石(地中へ 0.06 沈む台。地面との取り合いを隠す)
    m.box(-hx - 0.05, hx + 0.05, -0.06, 0.10, -hz - 0.05, hz + 0.05,
          one_stone(suv, 5), F.STONE)
    # 水盤の胴。⛔ **玉石積みの目地を出さない** — 一枚の彫り石なので `one_stone` で貼る
    for k, (a0, a1, b0, b1) in enumerate([(-hx, hx, hz - 0.07, hz), (-hx, hx, -hz, -hz + 0.07),
                                          (-hx, -hx + 0.07, -hz + 0.07, hz - 0.07),
                                          (hx - 0.07, hx, -hz + 0.07, hz - 0.07)]):
        m.box(a0, a1, 0.06, H - 0.05, b0, b1, one_stone(suv, k), F.STONE)
    # 水溜りの底(内側)と、天端に回す縁
    m.box(-hx + 0.07, hx - 0.07, H - 0.11, H - 0.05, -hz + 0.07, hz - 0.07,
          one_stone(suv, 4), F.STONE)
    for k, (a0, a1, b0, b1) in enumerate(((-hx, hx, hz - 0.07, hz), (-hx, hx, -hz, -hz + 0.07),
                                          (-hx, -hx + 0.07, -hz + 0.07, hz - 0.07),
                                          (hx - 0.07, hx, -hz + 0.07, hz - 0.07))):
        m.box(a0, a1, H - 0.05, H, b0, b1, one_stone(suv, k + 1), F.STONE)
    return F._finish("Doi_Chozu", m, [wm, sm, pm], []), "Doi_Chozu"


# ================================================================ 沓脱石
KUTSU_MIZUKIRI = 0.01     # 天端の水切り 1/100(庭方指定 2026-09-06)


def kutsunugi():
    """**沓脱石**(`gardens.G_Okuniwa.kutsunugi.Kutsunugi_Oku`)。奥棟の南入側の前、
    主視点の真正面に据わる**一枚石**。足形 **1.40(X) × 0.95(Z)**・厚み 0.48。
    天端 26.92 / 地表 26.60 ⇒ **見付 0.32・根 0.16**(1/3 埋め)。

    ⛔ **`Own.Tateishi` を非一様スケールで伸ばして代用しない** — 石肌の斑が流れる
      (指図 `asset` 欄の `Own.Tateishi("Big",1..3)` は在庫での仮の当てで、当図の実物ではない)。
    ⛔ **`Foundation_A_01` の箱で作らない** — 玉石積みの**壁**のアトラスなので目地が何段も
      入り、1.4m の沓脱石が**石垣の箱**に見える(手水石で実見・`one_stone` の項)。
    ⭕ **在庫の実岩を切る**(規則1)。`build_okabe_niwa.kutsunugi` と**同じ型**を呼び直す。

    【元石を `m_rock_03` から `Rock_05_cut` へ替えた理由(2026-09-06 に4個体を実見)】
      ⚠ 岡部の既定 `m_rock_03` は平面比こそ 1.51:1 で近いが、**俯瞰の足形が鋭い楔**で、
        天端の平らな面が足形の **31%(cut0.60)** しか無い。踏む石にならない。
      ⭕ `Rock_05_cut` は足形が**広い矩形に近く**、`cut=0.40` で天端が **76%**。
        肌も暗灰〜緑灰の柱状で、指図の **伊豆硬石(安山岩)**【確度U】に読める
        (`m_rock_03` は淡桃色で花崗岩に見える)。平面比 1.58:1 → 目標 1.47:1 で
        **XY の非一様は 7%** に収まる(⛔ 平面比 1.1 前後の個体は 30〜40% 歪むので不可)。

    【庭方の追加指定 2026-09-06】
      ① 厚み **0.45〜0.55** に納める(露出 0.32 の倍を地中へ)。⇒ 実寸は下の print が申告。
      ② 天端は水平だが **入側と反対側へ 1/100 の水切り**。⛔ 内側(入側)へ傾けない。
         ⇒ **ローカル +Z(Unity)が下がる** = 見え面 = 庭側 = 入側の反対。
           Blender は +Y が Unity −Z なので、剪断は **z += 0.01·y_blender**。
           0.95m の見込みで **落差 9.5mm**。ピボット(足形の芯)は水切りの**中立点**なので
           `position.y = topY` はそのまま入る。
      ③ ⛔ **面(chamfer)を立てない** — 稜線を付けた化粧石にしない。
         ⭕ 作りは「**自然石の上面だけを均す**」= 水平面1枚で落とすだけ。縁・肩・下部は
           元石の肌のまま(鈍い肩・据わりの広い根)。⛔ 根固めの栗石は部材に含めない
           (棟梁が地表で扱う)。

    ピボット = **足形の芯・天端(水切りの中立点)**。⇒ `position.y = topY`(26.92)を直に。
    材 = `M_photoscanned_rocks_01`。⛔ 新規マテリアルを作らない。"""
    # ⛔⛔ `cap_uv` を外さない。切り口は `holes_fill` の**UV 無し**で焼かれ、岩アトラスの
    #   (0,0) = 島間の dilation の帯に落ちて、天端が**草と砂利の横筋の縞**になる
    #   (2026-09-06 に真俯瞰で実見)。0.110 = UV/m の密度 — 石目が実寸で流れる値。
    o, _ = ON.kutsunugi(name="Doi_Kutsunugi", L=1.40, W=0.95, H=0.48,
                        cut=0.40, stem="Rock_05_cut", cap_uv=0.110)
    # 水切り。⚠ **回転でなく剪断**で入れる — 回すと足形 1.40 × 0.95 が縮む。
    o.data.transform(Matrix(((1.0, 0.0, 0.0, 0.0),
                             (0.0, 1.0, 0.0, 0.0),
                             (0.0, KUTSU_MIZUKIRI, 1.0, 0.0),
                             (0.0, 0.0, 0.0, 1.0))))
    o.data.update()
    return o, "Doi_Kutsunugi"


# ================================================================ 水尻(余水吐)
def mizushiri_shiki():
    """**水尻 石の閾**(`mizu.mizushiri.shiki`・汀 #14 西端)。池の余水を落とす堰。
    幅 1.20(X・汀に沿う) × 見込み 0.55(Z) × 丈 0.34。天端の中央 0.60 を **0.06 掘り下げ**て
    越流の口にする(⛔ 平らな板にしない — どこから溢れるか読めなくなる)。
    ピボット = **閾の芯・天端**。⇒ `position.y = mizu.mizushiri.shiki.sill`(=水面+0.05)を直に入れる。
    ローカル **+Z = 下流(池の外)**。⚠ 呼び寸法でなくこの実寸で汀の石組へ取り合わせること。"""
    (wm, wuv), (sm, suv), (pm, puv) = F.palette()
    m = F.Mesh()
    Wd, Dp, H, notch, drop = 1.20, 0.55, 0.34, 0.60, 0.06
    hx, hz = Wd / 2.0, Dp / 2.0
    # 天端 y=0 に置くので胴は −H..0
    # ⛔ **閾の本体に玉石の目地を出さない** — 「石の閾」は一枚の切石(`one_stone`)。
    #   ⭕ 袖と洗掘止めは**石組**なので玉石のままでよい(そこは目地が入って正しい)
    for s, (a0, a1) in enumerate(((-hx, -notch / 2.0), (notch / 2.0, hx))):
        m.box(a0, a1, -H, 0.0, -hz, hz, one_stone(suv, s), F.STONE)
    m.box(-notch / 2.0, notch / 2.0, -H, -drop, -hz, hz,
          one_stone(suv, 2), F.STONE)                              # 越流の口(掘り下げ)
    # 両袖の立ち上がり(水を口へ寄せる)。⛔ 無いと堰の脇から回り込む
    for s in (-1, 1):
        m.box(s * hx - s * 0.16, s * hx, 0.0, 0.13, -hz, hz,
              F._sub(suv, 0.10, 0.60, 0.40, 0.95), F.STONE)
    # 下流の落ち口を受ける小端の平石(洗掘止め)
    m.box(-notch / 2.0 - 0.10, notch / 2.0 + 0.10, -H - 0.02, -H + 0.10, hz, hz + 0.34,
          F._sub(suv, 0.55, 0.60, 0.95, 0.95), F.STONE)
    return F._finish("Doi_Mizushiri_Shiki", m, [wm, sm, pm], []), "Doi_Mizushiri_Shiki"


def mizushiri_hakiguchi():
    """**埋樋の吐き口(石組)**(`mizu.mizushiri.umeToi` の終点・`outY` 26.00)。
    ⛔ **埋樋の本体は焼かない** — 土被り 0.30m 以上で地上から見えない(指図 `bom` の断り)。
    見えるのはこの吐き口だけなので、**石の面壁 + 樋の口 φ0.24 + 翼壁**だけを起こす。
    面壁 0.95(X) × 0.72(高) / 翼壁は左右へ 0.30 開く。
    ピボット = **樋の芯・吐き口の面**。⇒ `position.y = outY`、+Z = 流れの下流。"""
    (wm, wuv), (sm, suv), (pm, puv) = F.palette()
    m = F.Mesh()
    r = 0.12                                   # φ0.24 の半径
    hx, top, bot = 0.475, 0.50, -0.22          # 面壁の幅の半分 / 天端 / 底
    t = 0.22                                   # 面壁の見込み
    # 面壁を口の周りに4枚。⛔ 箱に穴を開けず、**避けて積む**(bisect を使わない)
    m.box(-hx, -r - 0.02, bot, top, -t, 0.0, F._sub(suv, 0.05, 0.05, 0.45, 0.55), F.STONE)
    m.box(r + 0.02, hx, bot, top, -t, 0.0, F._sub(suv, 0.50, 0.05, 0.90, 0.55), F.STONE)
    m.box(-r - 0.02, r + 0.02, r, top, -t, 0.0, F._sub(suv, 0.10, 0.60, 0.50, 0.95), F.STONE)
    m.box(-r - 0.02, r + 0.02, bot, -r, -t, 0.0, F._sub(suv, 0.50, 0.60, 0.90, 0.95), F.STONE)
    # 樋の口(石樋の小口が面壁から少し出る)。八角に近い枠で丸みを出す
    for (a0, a1, b0, b1) in ((-r - 0.02, -r + 0.03, -r, r), (r - 0.03, r + 0.02, -r, r),
                             (-r, r, r - 0.03, r + 0.02), (-r, r, -r - 0.02, -r + 0.03)):
        m.box(a0, a1, b0, b1, -t - 0.05, -t + 0.01,
              F._sub(suv, 0.60, 0.10, 0.80, 0.30), F.STONE)
    # 翼壁(面壁から下流へ開く)+ 吐き口の下の受け石
    for s in (-1, 1):
        m.box(s * hx - s * 0.18, s * hx, bot, top - 0.14, 0.0, 0.42,
              F._sub(suv, 0.15, 0.15, 0.55, 0.55), F.STONE)
    m.box(-hx, hx, bot - 0.02, bot + 0.11, 0.0, 0.55,
          F._sub(suv, 0.55, 0.55, 0.95, 0.95), F.STONE)
    return F._finish("Doi_Mizushiri_Hakiguchi", m, [wm, sm, pm], []), "Doi_Mizushiri_Hakiguchi"


def otoshimizo():
    """**石敷きの落とし溝 1スパン**(`mizu.mizushiri.otoshimizo`・吐き口から法面を下る)。
    ⚠ **1本物で焼かない** — 法面を折れながら下る線なので、run に並べる**モジュール**にする。
    ⭕ **bbox の X をちょうど 1.000 にする** — ビルダーは bbox から実寸を測ってピッチを
    決めるので、端が半端に出るだけでピッチが狂う(README 2026-09-04 の項)。
    溝幅 0.36 / 敷き石の天端 −0.10(地盤から沈める) / 両縁の耳石は地盤 +0.04。
    ピボット = **スパンの中心・地盤レベル**。ローカル **+X = 流れの向き**。"""
    (wm, wuv), (sm, suv), (pm, puv) = F.palette()
    m = F.Mesh()
    L, chan, edge = 1.000, 0.36, 0.17
    hx, hc = L / 2.0, chan / 2.0
    # 溝底の敷石 — 4枚に割って UV をずらす(⛔ 1枚貼りは無地の帯になる)
    # ⚠ **両端の駒は ±hx に面一で出す。**目地を端にも入れると bbox が 0.988 になり、
    #   ビルダーが bbox からピッチを測るので run 全体が縮む(README 2026-09-04 の項)
    def gap(i, n_):
        return (0.006 if i else 0.0), (0.006 if i < n_ - 1 else 0.0)
    n = 4
    for i in range(n):
        a0 = -hx + L * i / n
        ga, gb = gap(i, n)
        m.box(a0 + ga, a0 + L / n - gb, -0.20, -0.10, -hc, hc,
              F._sub(suv, 0.05 + 0.2 * (i % 3), 0.05, 0.42 + 0.2 * (i % 3), 0.45), F.STONE)
    # 両縁の耳石(小端立て)。⛔ 高さを揃えすぎない — 石敷きが縁石のコンクリートに見える
    for s in (-1, 1):
        for i in range(3):
            a0 = -hx + L * i / 3.0
            ga, gb = gap(i, 3)
            m.box(a0 + ga, a0 + L / 3.0 - gb, -0.20, 0.04 - 0.012 * (i % 2),
                  s * hc, s * (hc + edge),
                  F._sub(suv, 0.50, 0.50 + 0.15 * (i % 2), 0.92, 0.92), F.STONE)
    o = F._finish("Doi_Otoshimizo_1m", m, [wm, sm, pm], [])
    return o, "Doi_Otoshimizo_1m"


PARTS = {
    "umaya":      lambda: umaya(),
    "kura38":     kura38,
    "kura33":     kura33,
    "ido":        ido,
    "chozu":      chozu,
    "kutsunugi":  kutsunugi,
    "shiki":      mizushiri_shiki,
    "hakiguchi":  mizushiri_hakiguchi,
    "otoshimizo": otoshimizo,
}
GROUPS = {"kura": ["kura38", "kura33"],
          "mizushiri": ["shiki", "hakiguchi", "otoshimizo"]}


def _kutsunugi_check(o, mn, mx):
    """沓脱石の検査。⛔ **目視だけで通さない** — 「天端が平らに見える」は肌の斑に
    だまされる(元石を選ぶとき実際に 2 度誤読した)。⭕ 数値で3件出す。
      ① 厚み 0.45〜0.55(庭方 ①)/ ② 水切りが **入側と反対へ** 1/100(庭方 ②)/
      ③ 天端(踏み面)が足形の何 % か。⚠ 6 割を切ったら踏む石にならない。"""
    L, W = mx.x - mn.x, mx.y - mn.y
    th = mx.z - mn.z
    # 天端 = 上向きで、剪断後の理論天端 z = 0.01·y から 6mm 以内にある面
    tread = [f for f in o.data.polygons
             if f.normal.z > 0.85 and abs(f.center.z - KUTSU_MIZUKIRI * f.center.y) < 0.006]
    area = sum(f.area for f in tread)
    zs = [(o.data.vertices[i].co.y, o.data.vertices[i].co.z) for f in tread for i in f.vertices]
    # Unity +Z(= Blender −Y)側の天端が低いこと = 入側の反対へ水を切っている。
    # ⚠ **落差を足形の見込み 0.95 で割らない** — 天端は足形いっぱいには広がっていないので
    #   勾配が緩く出る(1/100 が 1/138 と申告された)。⭕ **両帯の重心の y 間隔**で割る。
    lo = [(y, z) for y, z in zs if y < -W * 0.25]
    hi = [(y, z) for y, z in zs if y > W * 0.25]
    if lo and hi:
        ylo, zlo = sum(y for y, _ in lo) / len(lo), sum(z for _, z in lo) / len(lo)
        yhi, zhi = sum(y for y, _ in hi) / len(hi), sum(z for _, z in hi) / len(hi)
        drop, base = zhi - zlo, yhi - ylo
    else:
        drop, base = 0.0, 1.0
    grad = drop / base if base > 1e-9 else 0.0
    print("[doi] 検査① 厚み %.3f m  → %s (庭方 0.45〜0.55)"
          % (th, "OK" if 0.45 <= th <= 0.55 else "⚠ 範囲外"))
    print("[doi] 検査② 水切り 落差 %+.4f m / 天端の実見込み %.3f m = **1/%.0f**  向き=%s → %s"
          % (drop, base, (1.0 / grad if grad > 1e-9 else 0),
             "ローカル +Z(Unity)= 入側の反対へ下がる" if grad > 0 else "⛔ 内側へ傾いている",
             "OK" if grad > 0 and abs(1.0 / max(grad, 1e-9) - 100) < 20 else "⚠"))
    print("[doi] 検査③ 天端(踏み面)%.3f m2 = 足形 %.2f×%.2f の %.0f%% → %s"
          % (area, L, W, 100 * area / (L * W), "OK" if area / (L * W) >= 0.60 else "⚠ 狭い"))


def shots(o, key, box, ground=None):
    """⚠ **書き出しの前に撮る** — `export_fbx` を通した後は bbox が 0 に潰れて
    画角が壊れ、無地の灰色1枚が出る(README 2026-09-04 の項)。

    ⚠ 結線は **`build_okabe_niwa.hook()`** を通す(`V.hook_textures()` の上位互換)。
      Village Kit の材に加えて **NatureManufacture の岩**(`M_photoscanned_rocks_01`)も
      当たる。⛔ `V.hook_textures()` だけだと岩が**無地の灰色**で写り、材質の不具合と
      紛らわしい(沓脱石で踏む)。
    ⚠ `ground` を渡すと**その高さに地面を敷く** — 埋める部材(沓脱石)の
      **見付高**を目で検めるため。⛔ 底に敷くと露出高が読めない。"""
    ON.hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    r = max(W, H, D)
    bpy.ops.mesh.primitive_plane_add(
        size=max(60.0, r * 20),
        location=(c.x, c.y, mn.z - 0.02 if ground is None else ground))
    # ① 立面(表 = Blender −Y から)。ortho_scale は画像の長辺に効くので縦横を見て渡す
    wpx, hpx = 1500, 1500 * (H * 1.25) / max(1e-6, W * 1.15)
    if hpx > 1150:
        wpx, hpx = wpx * 1150 / hpx, 1150
    V.studio((c.x, mn.y - r * 3.0, c.z), (c.x, c.y, c.z),
             ortho_scale=(W * 1.15 if wpx >= hpx else H * 1.25),
             res=(int(wpx), int(hpx)))
    V.render(os.path.join(SHOT, "doi_%s_elev.png" % key))
    # ② 斜めから(小口・厚み・据わりを見る)
    V.studio((c.x - r * 1.3, mn.y - r * 1.7, mn.z + r * 1.0),
             (c.x, c.y, mn.z + H * 0.42), res=(1500, 1050))
    V.render(os.path.join(SHOT, "doi_%s_3d.png" % key))
    if ground is not None:
        # ③ 真俯瞰(踏む石の**天端の広さ**を検める)。⛔ 斜めだけでは平らさが読めない
        V.studio((c.x, c.y + 1e-4, mx.z + r * 6.0), (c.x, c.y, mx.z),
                 ortho_scale=max(W, D) * 1.15, res=(1400, int(1400 * D / W)))
        V.render(os.path.join(SHOT, "doi_%s_top.png" % key))
        # ④ **据え付けの姿** — 地表を敷いた上に、庭からの立ち位置(目の高さ 1.5m)で見る。
        #   ⛔ 部材単体の立面では**見付高**が読めない(埋まる部材はここまで見て初めて可否が出る)
        V.studio((c.x + W * 0.55, mn.y - 2.6, ground + 1.5),
                 (c.x, c.y, ground + H * 0.3), res=(1500, 1000))
        V.render(os.path.join(SHOT, "doi_%s_sueru.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = []
    for a in argv:
        if a.startswith("--"):
            continue
        want += GROUPS.get(a, [a])
    want = want or list(PARTS.keys())
    for key in want:
        if key not in PARTS:
            print("[doi] ⚠ 知らない部材: %s (%s)" % (key, "/".join(PARTS)))
            continue
        V.reset()
        o, name = PARTS[key]()
        mn, mx = V.bbox([o])
        print("[doi] %-26s Unity実寸 W(X)=%6.3f  H(Y)=%6.3f  D(Z)=%6.3f  底=%+.3f  面=%d"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
        print("[doi] %-26s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
        if key == "kutsunugi":
            _kutsunugi_check(o, mn, mx)
        if "--render" in argv:
            # 沓脱石は地表(天端 −0.32)を敷いて**見付高**ごと撮る
            shots(o, key, (mn, mx), ground=(-0.32 if key == "kutsunugi" else None))
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[doi] 書き出し " + os.path.join(OUT, name + ".fbx"))


main()
