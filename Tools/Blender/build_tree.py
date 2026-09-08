"""**木を在庫の作りに合わせて起こす。**

    blender --background --python Tools/Blender/build_tree.py -- jouryoku Mid --render
    blender --background --python Tools/Blender/build_tree.py -- ume Small Mid Big
    blender --background --python Tools/Blender/build_tree.py -- teiboku H12 H16 H20 H24 --render
    blender --background --python Tools/Blender/build_tree.py -- matsu Mid Big

【なぜ要るか】⛔ **自作の低ポリゴンの木は使用禁止**(2026-08-30 ユーザー指示
「これは2度と使わないでください。見た目がしょぼすぎます」)。
在庫(Waldemarst FreeJapaneseGarden)には**黒松・桜・竹しか無く**、松江松平邸の指図が要求する
**常緑広葉樹 51本**(モッコク・モチノキ・カシ・シイ)と**ウメ 22本**が埋まらない。
ユーザー裁定 2026-08-31 は **案C = 在庫を参考に新造**。

【在庫の作り(実測 2026-08-30。これに合わせる)】
  ・LOD **4段** — screenRelativeTransitionHeight 0.80 / 0.60 / 0.40 / 0.04
  ・三角数 LOD0 **5,960〜6,575** / LOD1 3,672〜4,228 / LOD2 1,678〜2,600 / LOD3 ビルボード16
  ・構成 = **樹皮の実ジオメトリ**(幹と枝)+ **葉のカード**。サブメッシュ 2〜3
  ・シェーダ `URP/Nature/SpeedTree8_PBRLit`

【材質】⛔ **新規に作らない。**在庫の材質名をそのまま名乗らせ、Unity 側で remap して
提供元の .mat へ結ぶ(長屋・隅部材と同じ作法)。
  樹皮 = `M_FJG_Tree_Sakura_Bark_A` / 葉 = `M_FJG_Tree_Sakura_Sprout_Summer`
⚠ 葉のテクスチャは在庫の物なので、**枝ぶりと葉の付き方**で樹種を描き分ける
(常緑広葉樹=密で丸い樹冠・立ち枝 / 梅=疎で屈曲した枝・横張り)。

【出力の向き(Unity 座標)】幅=X / 高さ=Y / 厚み=Z。ピボット = **幹の芯・地面**。

【検証】⛔ `--render` の全景だけで済ませない。**近景**と**在庫との並び**は
`Tools/Blender/check_tree.py` で焼く(浮いた葉の房と樹冠の透けは引きの絵では読めない)。
    blender --background --python Tools/Blender/check_tree.py -- near Tree_Teiboku_H20
    blender --background --python Tools/Blender/check_tree.py -- cmp teiboku
    blender --background --python Tools/Blender/check_tree.py -- cmp matsu   # 在庫の黒松と並べる
"""
import bpy, bmesh, sys, os, math, random, zlib
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

OUT  = V.out_dir(os.path.join(V.REPO, "Assets/Edo/Models/Trees"))
SHOT = os.path.join(V.REPO, "Screenshots")
MAT_BARK  = "M_FJG_Tree_Sakura_Bark_A"
MAT_LEAF  = "M_FJG_Tree_Sakura_Sprout_Summer"
# ⭐ 2026-09-07 — **松は在庫に本物の樹皮と針葉のアトラスがある**(FJG BlackPine)。
#   ⛔ 桜の広葉の房を松に流用しない(針葉に見えない)。樹種ごとに材質**名**を引く。
MAT_PINE_BARK = "M_FJG_Tree_BlackPine_Bark"
MAT_PINE_LEAF = "M_FJG_Tree_BlackPine_Sprout_A_Green"
# 提供元(検証レンダ用に読むだけ。FBX には材質**名**しか入れない)
FJG = os.path.join(V.REPO, "Assets/Waldemarst/FreeJapaneseGarden/Textures/Trees")
TEX_LEAF = os.path.join(FJG, "Sakura_Summer_001/T_FJG_Sakura_Summer_001_Atlas_Albedo.png")
TEX_BARK = os.path.join(FJG, "T_FJG_Tree_Sakura_Bark_A_Albedo.png")
TEX_PINE_LEAF = os.path.join(FJG, "BlackPine_Green_001/T_FJG_BlackPine_Green_001_Atlas_Albedo.png")
TEX_PINE_BARK = os.path.join(FJG, "T_FJG_Tree_BlackPine_Bark_Albedo.png")

# ⭐ 葉のアトラスの房の位置(2026-08-31 実測。32x32 グリッドで α>0.5 の連結成分)。
#   ⛔ **UV を張らないと葉が出ない** — アトラスなので、カードを房の矩形へ写す。
SPROUT_UV = [
    (0.2500, 0.5000, 0.4688, 0.8125), (0.7188, 0.0000, 1.0000, 0.2500),
    (0.0000, 0.2812, 0.2188, 0.5000), (0.7188, 0.5000, 1.0000, 0.6875),
    (0.5000, 0.4688, 0.6875, 0.6875), (0.5000, 0.2500, 0.6875, 0.4688),
    (0.0000, 0.0000, 0.2188, 0.2188), (0.5000, 0.7188, 0.6562, 0.9062),
    (0.5000, 0.0000, 0.6875, 0.1875), (0.2812, 0.2812, 0.4688, 0.4375),
]

# ⭐ **クロマツの針葉のアトラス**(2026-09-07 実測。4096² を 32×32 で走査し α>0.5 の連結成分)。
#   ⚠ 桜と違って**房が枝ごと描かれている** — 大きい6枚は「小枝＋針葉の房」で縦長(縦横比
#   1.37〜1.75)、小さい3枚は房だけの扇(0.83〜1.00)。
#   ⇒ **カードを枝の向きへ寝かせる**(`leaf_align`)。寝かせないと、アトラスの中の小枝が
#     実際の枝と交差して十字に立ち、近景で「板が刺さっている」ように読める。
PINE_UV = [
    (0.5312, 0.5625, 1.0000, 0.9688), (0.0000, 0.5312, 0.2500, 0.9688),
    (0.0000, 0.0312, 0.2500, 0.4375), (0.7812, 0.0625, 1.0000, 0.4062),
    (0.2500, 0.0625, 0.5000, 0.4062), (0.5312, 0.0625, 0.7500, 0.3750),
    (0.3125, 0.6875, 0.5000, 0.8438), (0.3125, 0.4688, 0.5000, 0.6250),
    (0.5312, 0.4688, 0.6875, 0.6250),
]

# ⭐ 2026-09-07 是正② — 照葉低木の**葉の密度**。外から見て内部の枝が読めない程度まで上げる。
#   在庫の同格(Waldemarst 桜)は LOD0 5,960〜6,575 tri。低木はそこまで使ってよい。
# ⚠ **丈で割り戻す。** 葉のカードの寸法は丈に比例する(`leaf_scale` × 丈)ので、
#   「枚/m」を丈によらず一定にすると**小さい木ほど relative に疎**になる。
#   実測: 34枚/m のとき Mid(丈2.0)は 幅/丈 0.94 で密、Small(丈1.2)は 0.85 で透けた。
#   ⇒ `LEAF_REF_H` を基準に `× LEAF_REF_H / 丈` して、**カード寸法あたりの枚数**を揃える。
LEAF_PER_M = 40.0
LEAF_REF_H = 2.0

# 樹種のプロファイル。⚠ 寸法は在庫の同格に合わせる(桜 Mid = 5.8×5.7m / Big = 8.6×7.3m)
SPECIES = {
    # 常緑広葉樹(モッコク・モチノキ・カシ・シイ)— 密で丸い樹冠、立ち枝、葉が枝先に集まる
    "jouryoku": dict(label="常緑広葉樹",
                     trunk_h=0.44, trunk_r=0.040, tip_r=0.006, lean=0.030,
                     crown_z=0.70, crown_rz=0.29, wh=0.68, top=0.55,
                     attractors=420, influence=0.32, kill=0.075, step=0.055,
                     iters=42, up=0.16, jitter=0.20,
                     leaf_scale=0.105, leaf_per_tip=7),
    # イロハモミジ — **株立ち3〜5幹**・枝が水平に張る・葉が細かい。
    # ⚠ 灌木の `NM.MapleBush`(丈1.5m)は中木に使えず、桜モデルでの代用も不可
    #   (夏姿でも幹肌が桜と読め、季節の確度が化ける)。庭方の要求で新造した。
    # ⛔ **紅葉色にしない** — 季節は春ではないが**秋でもない**。葉は夏の緑。
    "momiji":   dict(label="イロハモミジ",
                     trunk_h=0.22, trunk_r=0.030, tip_r=0.005, lean=0.16,
                     crown_z=0.60, crown_rz=0.26, wh=1.06, top=0.80,
                     attractors=300, influence=0.34, kill=0.080, step=0.058,
                     iters=38, up=0.02, jitter=0.30,
                     leaf_scale=0.070, leaf_per_tip=9,
                     kabu=(3, 5)),          # 株立ちの幹の本数(奇数の幅)
    # ウメ — 疎で屈曲した枝、横張り、樹高が低い
    "ume":      dict(label="ウメ",
                     trunk_h=0.36, trunk_r=0.034, tip_r=0.005, lean=0.10,
                     crown_z=0.66, crown_rz=0.30, wh=0.86, top=0.74,
                     attractors=190, influence=0.40, kill=0.105, step=0.070,
                     iters=34, up=0.10, jitter=0.34,
                     leaf_scale=0.088, leaf_per_tip=4),
    # ---- 落葉高木3種(岡部邸)。⚠ **葉の房の寸法は絶対値で効かせる** —
    #      `leaf_scale` は樹高に掛かるので、14m の木に常緑広葉樹の 0.105 を使うと
    #      房が 1.5m になって「木」に見えない。房が 0.5m 前後になる値を選んである。
    # ⛔ **紅葉色にしない**(季節は春でも秋でもない)。葉は夏の緑のまま。
    # ⚠ 樹皮の材質は在庫の桜のものを名乗る(キットに落葉高木の樹皮が無いため)=確度U。
    #   ⇒ 姿(幹の分かれ方・枝の角度・樹冠の輪郭)で樹種を描き分ける。

    # エノキ — 一里塚の木。**低い位置(樹高の 1/3)で数本の大枝に分かれ**、
    #          枝が斜め上へ開いて **扇形〜半球形の広い樹冠**。幅 ≒ 高さ。
    "enoki":    dict(label="エノキ",
                     trunk_h=0.30, trunk_r=0.030, tip_r=0.0040, lean=0.045,
                     crown_z=0.62, crown_rz=0.33, wh=0.98, top=0.62,
                     attractors=370, influence=0.30, kill=0.072, step=0.052,
                     iters=44, up=0.13, jitter=0.22,
                     leaf_scale=0.042, leaf_per_tip=5,
                     sizes=dict(Small=11.0, Mid=13.5, Big=16.0)),
    # ムクノキ — エノキに似るが **幹がより通直で高く**、樹冠はやや縦長。
    #            枝は細くしなやかで **垂れ気味**(`up` を小さく)。
    "mukunoki": dict(label="ムクノキ",
                     trunk_h=0.40, trunk_r=0.026, tip_r=0.0038, lean=0.030,
                     crown_z=0.66, crown_rz=0.32, wh=0.80, top=0.58,
                     attractors=360, influence=0.31, kill=0.074, step=0.052,
                     iters=42, up=0.06, jitter=0.26,
                     leaf_scale=0.044, leaf_per_tip=5,
                     sizes=dict(Small=10.0, Mid=12.0, Big=14.0)),
    # ケヤキ — **箒形**が定義的。短い直幹から大枝が扇状に立ち上がり、上へ広がる。
    #          ⇒ `up` を大きく・`lean` を小さく・**`bottom` で樹冠の下を絞る**。
    "keyaki":   dict(label="ケヤキ",
                     trunk_h=0.26, trunk_r=0.032, tip_r=0.0040, lean=0.018,
                     crown_z=0.66, crown_rz=0.34, wh=0.95, top=0.90, bottom=0.30,
                     attractors=380, influence=0.30, kill=0.070, step=0.050,
                     iters=46, up=0.30, jitter=0.18,
                     leaf_scale=0.040, leaf_per_tip=5,
                     sizes=dict(Small=13.0, Mid=14.5, Big=16.0)),
    # ---- 常緑の照葉低木(サカキ・アオキ・ヤブツバキ)= 山王社の社叢の下層・林縁・前庭の帯。
    # ⛔ **刈込(玉物)にしない** — 指図 `gardens[前庭の帯].forbidden` に「刈込」が立っている。
    #    社叢の自然な下層なので、**株立ちのまま枝を伸ばした姿**にする。
    # ⭐ 姿の決め手は3つ:
    #    ① **株立ち** — 3〜6本が根元から立つ(3種とも幹が地際で分かれる)
    #    ② **立ち枝** — 直立性なので `up` を大きく(横張りのウメと逆)
    #    ③ **下がすぼまり上が丸い** — `bottom` で足元を絞り、`top` を高めに残して
    #       卵形〜倒卵形の樹冠。⛔ 球にしない(それは刈込の姿)
    # ⚠ **丈は指図が部材の呼び寸として 1.2〜2.0m と書いている**
    #    (`slopeBands[2]._`「部材 teiboku 1.2〜2.0m を ×1.25 まで伸ばす」)。
    #    ⇒ 呼び寸は丈をそのまま名乗る H12=1.2 / H20=2.0(間を H16/H24 が埋める)。
    #    ⛔ SIZE(桜の同格 3.6/5.8/8.2)は当てない。
    # ⚠ 樹冠は指図の `gardens[前庭の帯].shrubs.crownRKen` = 0.33間(半径0.60m)に合わせ、
    #    **樹冠 ÷ 丈 ≒ 0.95** に仕立てる(丈1.25m で直径1.19m)。
    #    ⚠ `wh` は**誘引点の雲の幅**であって出来上がりの幅ではない。必ず**焼いて測る**。
    #    ・〜2026-09-06(葉を枝先から散らしていた頃)= 0.72 で実測 1.24 ×丈。
    #    ・2026-09-07 以降 = 葉が**枝に載る**ので散らしの分だけ樹冠が痩せる。
    #      0.72 で 0.755 ×丈 まで落ちたので **0.86** へ戻した(実測は下の表)。
    # ⚠ 葉は在庫(桜)のアトラスを名乗る=確度U。⇒ **枝ぶりと葉の密度**で照葉低木を描き分ける。
    #    ⛔ 花を付けない・紅葉色にしない(季節は春でも秋でもない)。
    # ⭐ **密度**(2026-09-07 の是正②)— 社叢の下層・林縁を閉じる役なので、外から見て
    #    内部の枝が読めないところまで葉を盛る。`LEAF_PER_M` と `leaf_scale` の2つが効く。
    #    ⛔ 刈込(玉物)の球にはしない — 輪郭は `top`/`bottom` の卵形のまま。
    "teiboku":  dict(label="常緑の照葉低木",
                     trunk_h=0.09, trunk_r=0.028, tip_r=0.0050, lean=0.050,
                     crown_z=0.52, crown_rz=0.42, wh=0.86, top=0.70, bottom=0.55,
                     attractors=190, influence=0.32, kill=0.082, step=0.068,
                     iters=32, up=0.22, jitter=0.19,
                     leaf_scale=0.092,
                     # ⭐ 2026-09-07 是正① — 葉を**枝のセグメントに紐づけて**生やす。
                     #    枝先から散らす旧モードでは房が空中と地面に取り残された。
                     leaf_mode="segment",
                     leaf_per_m=LEAF_PER_M,  # 枚/m(細い枝の長さあたり)
                     leaf_r_mult=3.4,        # 「細い枝」の判定(最細半径の何倍まで)
                     kabu=(4, 7),           # 株立ち — 地際から4〜7本
                     seg_bias=0.62,         # 枝は葉に隠れるので断面を粗く(三角数を抑える)
                     # ⭐ 2026-09-08 — 樹皮の円筒 UV(松に続いて低木も一点貼りをやめた)。
                     #    ⛔ 0 のままだと樹皮テクスチャの左下 1px を引き伸ばした無地の幹になる
                     #      (実測: つるりとした焦茶のプラスチックの棒)。
                     #    ⚠ 幾何は一切動かない(頂点も乱数の消費も同じ)= 既存6点の三角数・
                     #      bbox・min Y は不変。UV だけが付く(FBX を読み直して md5 で確認済)。
                     # ⛔ **周長に合わせて 0.40 にしてはいけない**(1巡目の誤り)。u は周を1周
                     #    するので「u:v を等方に」と考えると幹の周長 0.21〜0.42m から 0.40 が
                     #    出る。⇒ 焼いたら**竹になった** — 桜の樹皮アトラスは横筋(皮目)が
                     #    強く、0.40m ごとに黒い輪と緑の節間が繰り返して稈に見える。
                     # ⭕ **テクスチャが写している実物の丈で採る。**桜の樹皮1枚は成木の幹の
                     #    1.8m 相当なので、松と同じ 1.8。横筋は株の丈(1.2〜2.4m)の中に
                     #    高々1本しか来ず、縦の裂けだけが grain として読める。
                     #    ⚠ u は周長 0.3m に 1.8m 幅を巻くので横に約6倍詰まるが、
                     #      細い枝では**細かい木理**として正しく読める(近景レンダで確認)。
                     bark_uv=1.80,
                     # ⭐ 2026-09-08 — **中間の刻みを2段足した**(庭方 11巡目 裁き3)。
                     #    指図の低木の丈の全域は 0.90〜2.50m。箍 `scaleY` 0.75〜1.10 では
                     #    1.2/2.0 の二段だと帯1(1.2〜2.0)で 0.660・帯3/林縁(1.8〜2.5)で
                     #    1.250 が立ち、929 本が縮尺の照合に入れられなかった。
                     #    ⛔ 帯の丈を部材へ寄せる道は庭方が却下(ほぼ全数が Mid 一段に落ち、
                     #      929 本が3メッシュの繰り返し=「林床が縞に見える」になる)。
                     #    ⇒ 4段の被覆(×0.75〜1.10): 1.2→0.90〜1.32 / 1.6→1.20〜1.76 /
                     #      2.0→1.50〜2.20 / 2.4→1.80〜2.64。⭕ 継ぎ目に重なりがあり穴なし。
                     #    ⛔ 1.6 だけでは上が 2.20 で止まり帯3・林縁が閉じない。
                     #    ⚠ 名は `Own.Teiboku(size, i)` が組む `Tree_Teiboku_<size>[_02]` の
                     #      形に収まること。⛔ `Small2` のような**数字で終わる名は使わない** —
                     #      個体の接尾辞 `_02/_03` と並ぶと `Small2_02` と読めて紛れる。
                     # ⭐ 2026-09-08 追記 — **4段すべてを丈で名乗らせた**(普請奉行の裁定)。
                     #    足した2段だけが `H16`/`H24` で、残る2段が `Small`/`Mid` という
                     #    綴りの混在は「どちらが高いか」を名から読めない。⇒ 丈の物差しで
                     #    `H12 / H16 / H20 / H24` に揃えた(1.2 / 1.6 / 2.0 / 2.4 m)。
                     #    指図の `sizeRule.sizes` は旧綴りも並べた過渡措置なので前後どちらでも解ける。
                     # ⛔ **改名は姿を変える。**種は `zlib.crc32("teiboku/<size>/<個体>")` で、
                     #    `size` の綴りが種そのもの。⇒ `H12`/`H20` の6点は Small/Mid とは
                     #    別の骨格に焼き上がる(どの個体も等価に妥当なので姿は問題ない。
                     #    黙って変えないことが要件)。⚠ `H16`/`H24` は綴りが動かないので不変。
                     sizes=dict(H12=1.2, H16=1.6, H20=2.0, H24=2.4)),
    # ---- クロマツ(**社叢の松** = 林分の中で競り上がった姿)。山王社の社叢。
    # ⚠ **なぜ在庫では足りないか。**在庫 `Tree_BlackPine_Big_Green_01/02/03` の素の丈は
    #   6.43 / 6.64 / 6.55m が上限で、指図の社叢は 9.5〜13.0m(`slopeBands[*].matsuH`)。
    #   ⇒ 実装は `scaleY` 1.43〜1.99 で**縦に伸ばし**、横は `scaleXZ ≤ 1.15` の規約で
    #   抑えていたため**異方比が最悪 1.99** — 針葉の房が縦に2倍に伸びた(庭方 9巡目 中4)。
    # ⭐ **狙いは `scaleY` を 1.15 以下に落とすこと。**丈は下げない(社叢として正しい)。
    #   ⇒ Mid 10.5m / Big 12.5m の2刻みにすると、9.5〜13.0 のどこを取っても
    #     近いほうの刻みで `scaleY` は 0.90〜1.10 に収まる(異方比 ≤ 1.11)。
    #
    # ⛔ **2026-09-07 の差し戻しで分かったこと(前の注記はここで置き換えた)。**
    #   前の版はこの欄に「① 幹が通直で立ち上がりが高い ② 枝下が高い ③ 傘形」と書き、
    #   `trunk_h` を大きく・`lean` を小さくして空間占有法に任せていた。出てきたのは
    #   **通直な電柱の上に blob の傘が一つ**で、普請奉行が在庫の黒松と並べて
    #   「松に見えない・広葉樹の若木だ」と差し戻した。誤りは2つ:
    #   ⛔ **「立ち上がりが高い」を「幹をまっすぐにしろ」と読んだこと。**林の松も幹は
    #     ゆるく曲がる。禁じられていたのは**庭木のような低い位置からの大張り出し**で、
    #     幹の曲がりではない。⇒ いまは `sway`(曲がり)と `lean`(正味の傾き)を**必ず持たせる**。
    #   ⛔ **樹冠を「輪郭」だけで決めたこと。**松の姿の要は輪郭ではなく**内部の構造** —
    #     水平に張り出す枝が**段**を成し、段と段の間に空が抜け、針葉が段の上に
    #     **板状の房**として乗る。確率的な伸長ではこれが出ない。
    #   ⇒ 骨格は `pine_skeleton`(段を直に置く)。⛔ `branch_skeleton` へ戻さない。
    # ⚠ 段を**等間隔・等本数・等長**にすると今度は**モミ・スギの若木**になる(3巡目で実測)。
    #   高さ・本数・長さ・出の角度・板の傾きを全部散らすこと。
    # ⚠ **樹冠の絶対値**は在庫と同じ帯へ収める。指図の林冠閉鎖度は
    #   「部材の樹冠 × `scaleXZ`」で出ているので、樹冠が跳ねると閉鎖度が動く。
    #   ⛔ ただし**比を目標にして数合わせしない** — 姿から出た値を焼いて測る(下の実測表)。
    # ⭕ 材質は**在庫のクロマツの物**(樹皮も針葉も FJG に実物がある)。桜の広葉を流用しない。
    "matsu":    dict(label="クロマツ(社叢)",
                     skeleton="pine",       # ⛔ 空間占有法を使わない(上の pine_skeleton の理由)
                     trunk_r=0.0215, tip_r=0.0016,
                     leaf_scale=0.034,      # 房の実寸 = 2×丈×これ ≒ 0.85m(在庫の房に合わせた)
                     leaf_mode="segment",   # ⛔ 枝先から散らす旧モードにしない(房が浮く)
                     leaf_align=True,       # ⭐ カードの長手を小枝の向きへ寝かせる
                     leaf_per_m=38.0,
                     leaf_r_mult=2.0,       # 針葉が付くのは二次枝と末端の小枝だけ
                     bark_uv=1.8,           # 樹皮の円筒 UV(縦 1.8m で1枚)
                     adaptive_seg=True,     # 幹は8角・小枝は4角
                     uv="pine", bark=MAT_PINE_BARK, leaf_mat=MAT_PINE_LEAF,
                     seg_bias=1.0,
                     # ---- 段の骨格(すべて丈または枝長に対する比)
                     pine=dict(
                         trunk_seg=16, trunk_top=0.97,
                         sway=0.050,          # ⭐ 幹の曲がり。⛔ 0 にすると電柱になる
                         lean=0.040,          # ⭐ 正味の傾き(正弦だけでは相殺して通直に戻る)
                         flare=1.55,          # 根張り(地際だけ太らせる)
                         tiers=(4, 6),        # 段の数(個体差)
                         tier_lo=0.30, tier_hi=0.955,
                         reach=0.235,         # いちばん長い段の水平の伸び
                         rise=0.30, droop=0.24,
                         roll=0.34,           # 房の板の傾き ⇒ 水平の円盤にしない
                         prim_seg=4,
                         sec_at=(0.36, 0.60, 0.82),   # 二次枝の付く位置(一次枝の比)
                         sec_len=(0.48, 0.38, 0.28),
                         fan=(0.42, 1.05),    # 二次枝の水平の開き[rad]
                         plate=0.11,          # 段の厚み(枝長比)⇒ 板状に保つ
                         twig_len=0.22, twig_fan=0.46, twig_n=4, twig_up=0.36,
                         stubs=(2, 4),        # 枝下の枯れ枝の名残
                         top_tuft=0.075),
                     sizes=dict(Mid=10.5, Big=12.5)),
}
# ⭐ **照葉低木の実測**(2026-09-08 の**改名後**に焼き直して測り直した値。
#   **書き出した FBX を読み直して**測った LOD0 の bbox と三角数。
#   Unity 座標 W=X H=Y D=Z ⇒ Blender では W=X H=**Z** D=**Y**)
#   ⚠ `H12`/`H20` の6点は Small/Mid からの**改名で種が変わった**ので、丈は同じでも
#     骨格が入れ替わっている(下の W/D と三角数は改名後の値)。`H16`/`H24` は不変。
#   Tree_Teiboku_H12       W 1.057 × H 1.200 × D 1.120   5370 / 3056 / 1960   幅/丈 0.881
#   Tree_Teiboku_H12_02    W 0.964 × H 1.200 × D 1.051   6426 / 3684 / 2500   幅/丈 0.803
#   Tree_Teiboku_H12_03    W 1.061 × H 1.200 × D 1.029   6048 / 3416 / 2304   幅/丈 0.884
#   Tree_Teiboku_H16       W 1.370 × H 1.600 × D 1.312   6116 / 3544 / 2376   幅/丈 0.856
#   Tree_Teiboku_H16_02    W 1.389 × H 1.600 × D 1.356   5898 / 3436 / 2256   幅/丈 0.868
#   Tree_Teiboku_H16_03    W 1.413 × H 1.600 × D 1.379   6282 / 3612 / 2424   幅/丈 0.883
#   Tree_Teiboku_H20       W 1.886 × H 2.000 × D 1.566   6242 / 3552 / 2400   幅/丈 0.943
#   Tree_Teiboku_H20_02    W 1.847 × H 2.000 × D 1.691   5828 / 3312 / 2164   幅/丈 0.924
#   Tree_Teiboku_H20_03    W 1.796 × H 2.000 × D 1.863   5632 / 3244 / 2176   幅/丈 0.898
#   Tree_Teiboku_H24       W 2.222 × H 2.400 × D 2.099   5644 / 3172 / 2100   幅/丈 0.926
#   Tree_Teiboku_H24_02    W 2.038 × H 2.400 × D 2.066   6266 / 3616 / 2376   幅/丈 0.849
#   Tree_Teiboku_H24_03    W 1.895 × H 2.400 × D 2.140   5750 / 3224 / 2172   幅/丈 0.790
#   ・幅/丈 = 0.79〜0.94(指図の狙い 0.9。個体差はそのままにしてある)
#   ・接地面 min Y = 0.0000(**12点とも**実測)/ ピボットは幹の芯・接地面
#   ・丈は 1.200 / 1.600 / 2.000 / 2.400 が**そのまま出る** = 四刻みは物差しどおり等間隔
#   ・LOD0 三角数 5,370〜6,426(在庫の同格=Waldemarst 桜 5,960〜6,575 と同じ帯)
#   ・葉の房 → 枝の芯 の最大距離 0.078〜0.158m(関門 0.144/0.191/0.239/0.287m)・
#     **落とした房 0**(12点・LOD0〜2 の 36 通しとも)
#   ・樹皮の UV(実測)v span 1.022 = 幹の 1.84m ÷ `bark_uv` 1.80。
#     ⛔ 0.40 なら 4.60 が出るはず ⇒ **竹になっていないことの数の証拠**
#   ・孤立した葉の房 **0**(葉のカードの中心 → 最寄りの枝の芯 の最大 0.16m。関門 0.14〜0.29m)
#   ⭐ **H16 / H24 を足したときに Small / Mid の6点が動いていないことは、
#     書き出した FBX を git HEAD の版と読み比べて確かめた**(LOD_0/1/2 の全18メッシュで
#     頂点数・三角数・頂点座標の md5 が一致)。`sizes` に鍵を足しても
#     `crc32("teiboku/<size>/<個体>")` の種は変わらないので姿は不変。

# ⭐ **クロマツ(社叢)の実測**(2026-09-07 第2次。FBX を読み直して測った値。Unity 座標 W=X H=Y D=Z)
#   Tree_Matsu_Mid       W 5.85 × H 10.50 × D 6.77    9712 / 5830 / 4479
#   Tree_Matsu_Mid_02    W 7.76 × H 10.50 × D 7.61    8210 / 4844 / 3596
#   Tree_Matsu_Mid_03    W 8.05 × H 10.50 × D 6.49   11834 / 7052 / 5350
#   Tree_Matsu_Big       W 7.37 × H 12.50 × D 7.73    8404 / 5030 / 3787
#   Tree_Matsu_Big_02    W 6.82 × H 12.50 × D 6.70    8328 / 4994 / 3797
#   Tree_Matsu_Big_03    W 7.97 × H 12.50 × D 9.36    8034 / 4788 / 3572
#   ・樹冠(W)/丈 = 0.55〜0.77(在庫の黒松の LOD0 実測 4.37 / 6.42 = 0.68 と同じ帯)
#     ⛔ この比は**目標にしていない** — 段の形(`tier_prof`・`reach`)から出た値を測って書いた。
#   ・LOD0 三角数 8,034〜11,834(在庫の黒松の LOD0 実測 **9,159** と同じ帯)
#   ・接地面 min Y = 0.0000(6点とも実測)/ ピボットは幹の芯・地面
#   ・孤立した葉の房 **0**(枝の芯までの最大 0.19〜0.23m < 関門 0.46〜0.55m。落とした房 0)
#   ⚠ **`docs/asset-index.tsv` の在庫の黒松 6.48×6.43 は billboard の板の寸法**で、
#     LOD0 の実形(4.37×5.00)ではない。指図の林冠閉鎖度が「部材の樹冠 × scaleXZ」で
#     出ている以上、目録を作り直すまで在庫の樹冠は 35% 過大に読まれている。
# ⛔ **2026-09-07 第1次(空間占有法+`clump`)は普請奉行が差し戻した。**
#   数(丈 10.5/12.5・異方比 1.105・樹冠比)は合っていたのに**樹種の姿が無く**、
#   「まっすぐな棒の上に blob の傘が一つ載っただけ=広葉樹の若木」に見えた。
#   ⇒ 姿の欠陥は数では捕まらない。**在庫の実メッシュと並べて焼き、樹種の目で見る**こと。
#     blender --background --python Tools/Blender/check_tree.py -- cmp matsu
SIZE = {"Small": 3.6, "Mid": 5.8, "Big": 8.2}          # 樹高[m](在庫の同格に合わせる)
# ⚠ **落葉高木は在庫の同格では収まらない。**指図が要求するのは エノキ 11〜16 /
#   ムクノキ 10〜14 / ケヤキ 13〜16 で、桜 Big の 8.2m の 2 倍近い。
#   ⇒ 樹種の側に `sizes` を持たせて上書きする(⛔ SIZE を書き換えると他の種の姿が動く)。
LOD  = [dict(seg=8, tip=1.00, leaf=1.00),               # LOD0
        dict(seg=6, tip=0.62, leaf=0.72),               # LOD1
        dict(seg=5, tip=0.34, leaf=0.46)]               # LOD2


def crown_points(sp, h, rnd, n):
    """樹冠の体積に誘引点を撒く。**楕円体の内側を埋める**(殻に貼らない)。
    ⛔ 枝先を輪郭へ押し込むやり方はやめた — 枝先が殻の上に並んで
      樹冠が箱に見えた(2026-08-31 の試作。ユーザー指摘『樹冠が四角い』)。"""
    cz = h * sp["crown_z"]
    rz = h * sp["crown_rz"]
    rx = h * sp["wh"] * 0.5
    # ⭐ 2026-09-07 — **`clump` があれば誘引点を塊に撒く。**
    #   一様に撒くと樹冠が隙間なく埋まって**ブロッコリー**になる(松の1巡目)。
    #   松の壮齢木は枝が**平たい段**を成し、段と段の間に空が抜ける。
    #   ⇒ 塊の中心を先に撒き、その周りへ**扁平な**正規分布で誘引点を寄せる。
    #   ⛔ 既定 None = 従来どおり一様(他樹種の姿は動かさない)。
    cl = sp.get("clump")
    hubs = None
    if cl:
        hubs = []
        gu = 0
        while len(hubs) < cl["n"] and gu < cl["n"] * 200:
            gu += 1
            u = rnd.random() ** (1.0 / 3.0)
            th = rnd.uniform(0, math.tau); ph = math.acos(rnd.uniform(-1, 1))
            hubs.append(Vector((u * rx * math.sin(ph) * math.cos(th),
                                u * rx * math.sin(ph) * math.sin(th),
                                cz + u * rz * math.cos(ph))))
    pts = []
    guard = 0
    while len(pts) < n and guard < n * 60:
        guard += 1
        if hubs:
            hb = hubs[rnd.randrange(len(hubs))]
            r = rx * cl["r"]
            x = hb.x + rnd.gauss(0, r)
            y = hb.y + rnd.gauss(0, r)
            z = hb.z + rnd.gauss(0, r * cl.get("flat", 0.45))
            # 樹冠の楕円体からはみ出た点は捨てる(輪郭は崩さない)
            dz = (z - cz) / rz
            if abs(dz) > 1.0 or math.hypot(x, y) > rx * math.sqrt(max(0.0, 1 - dz * dz)):
                continue
            if z < h * sp["trunk_h"] * 0.8:
                continue
            pts.append(Vector((x, y, z)))
            continue
        # 体積一様に撒く(r**(1/3))。外周をやや厚くして葉を外に寄せる
        u = rnd.random() ** (1.0 / 3.0)
        u = u * 0.55 + u ** 0.45 * 0.45
        th = rnd.uniform(0, math.tau)
        ph = math.acos(rnd.uniform(-1, 1))
        x = u * rx * math.sin(ph) * math.cos(th)
        y = u * rx * math.sin(ph) * math.sin(th)
        z = cz + u * rz * math.cos(ph)
        # 上ほど細らせる(円錐にならない程度に)
        dz = (z - cz) / rz
        if dz > 0:
            lim = rx * math.sqrt(max(0.0, 1.0 - dz * dz)) * (1.0 - (1.0 - sp["top"]) * dz)
            if math.hypot(x, y) > lim:
                continue
        # ⭐ **下ほど細らせる**(`bottom` < 1)。ケヤキの**箒形**はこれが無いと出ない —
        #   上を広げようとしても x,y は rx で頭打ちなので、**下を絞る**しか逆円錐にならない。
        #   ⛔ 既定 1.0 = 従来どおり(常緑広葉樹・モミジ・ウメの姿は動かさない)
        elif sp.get("bottom", 1.0) < 1.0:
            lim = rx * (1.0 - (1.0 - sp["bottom"]) * min(1.0, -dz))
            if math.hypot(x, y) > lim:
                continue
        if z < h * sp["trunk_h"] * 0.8:
            continue                                  # 幹の下には葉を付けない
        pts.append(Vector((x, y, z)))
    return pts


def branch_skeleton(sp, h, rnd):
    """**空間占有法(space colonisation)**で骨格を作る。
    樹冠に誘引点を撒き、いちばん近い節が引かれて伸びる。届いた点は消す。
    ⭕ 樹冠の形は「押し込み」ではなく**枝が伸びた結果**として出るので、
      輪郭が箱にならず、内部にも枝が通る。
    返すのは ([(始点, 終点, 半径始, 半径終, 深さ)], 枝先)。"""
    # --- 幹。根元を太らせ、上へ細り、少し揺らぐ
    # ⭐ `kabu` を持つ種は**株立ち** — 根元から複数の幹が立ち上がる(モミジ・ヤマボウシの類)。
    #   ⛔ 同じ高さ・同じ太さで並べない。1本を主幹とし、残りを細く低く添える。
    r0 = h * sp["trunk_r"]
    nodes = [Vector((0, 0, 0))]
    parent = [-1]
    n_tr = sp.get("trunk_seg", 6)
    z_lead = h * sp["trunk_h"]
    kabu = rnd.randint(*sp["kabu"]) if "kabu" in sp else 1
    trunk_tops = []
    for k in range(kabu):
        # 主幹(k=0)は太く高く、添えは細く低い
        frac = 1.0 if k == 0 else rnd.uniform(0.62, 0.88)
        az = rnd.uniform(0, math.tau)
        spread = 0.0 if k == 0 else h * rnd.uniform(0.020, 0.048)
        base = Vector((math.cos(az) * spread, math.sin(az) * spread, 0.0))
        nodes.append(base); parent.append(0)
        prev = len(nodes) - 1
        # ⭐ `smooth_trunk` = **揺らぎの位相を幹ごとに1回だけ引く**。
        #   ⛔ 既定(節ごとに乱数を引く)は幹が節ごとに横へ跳ね、隣り合う筒の輪が
        #     ずれて**シルエットに刻みが出る**(松の近景レンダで実測。2026-09-07)。
        #     樹高 12.5m・trunk_seg 14 のように細かく割るほど目立つ。
        #   ⚠ 既存の樹種は跳ねたまま焼いてあるので**種ごとに明示して**切り替える。
        #   ⛔ **乱数を引くのは sm のときだけ。**無条件に引くと乱数列がずれ、
        #     切り替えていない樹種の姿まで変わる(実測: 低木 Mid の幅 1.774 → 1.81m)。
        sm = sp.get("smooth_trunk", False)
        if sm:
            p1, p2 = rnd.uniform(0, math.tau), rnd.uniform(0, math.tau)
            a1, a2 = rnd.uniform(0.7, 1.3), rnd.uniform(-1.0, 1.0)
        for i in range(1, n_tr + 1):
            t = i / n_tr
            if sm:
                sw = h * sp["lean"] * t
                dx = sw * math.sin(t * 2.4 + p1) * a1
                dy = sw * math.sin(t * 1.7 + p2) * a2
            else:
                sway = h * sp["lean"] * math.sin(t * 2.4 + rnd.uniform(0, 1)) * t
                dx = sway * rnd.uniform(0.5, 1.5)
                dy = sway * rnd.uniform(-1, 1)
            nodes.append(base + Vector((dx + math.cos(az) * spread * t * 2.2,
                                        dy + math.sin(az) * spread * t * 2.2,
                                        z_lead * frac * t)))
            parent.append(prev); prev = len(nodes) - 1
        trunk_tops.append(prev)

    attr = crown_points(sp, h, rnd, sp["attractors"])
    D_i = h * sp["influence"]          # 引きが届く距離
    D_k = h * sp["kill"]               # 届いたとみなす距離
    step = h * sp["step"]

    for _ in range(sp["iters"]):
        if not attr:
            break
        pull = {}
        for a in attr:
            best, bd = -1, 1e9
            for ni in range(len(nodes)):
                d = (a - nodes[ni]).length
                if d < bd: bd, best = d, ni
            if bd > D_i:
                continue
            pull.setdefault(best, Vector((0, 0, 0)))
            pull[best] += (a - nodes[best]).normalized()
        if not pull:
            break
        for ni, v in pull.items():
            if v.length < 1e-6:
                continue
            d = v.normalized()
            d.z += sp["up"]                       # 枝の立ち上がり
            d = (d + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * sp["jitter"]).normalized()
            nodes.append(nodes[ni] + d * step)
            parent.append(ni)
        attr = [a for a in attr
                if min((a - n).length for n in nodes) > D_k]

    # --- 太さ: ダ・ヴィンチ則(親の断面積 = 子の断面積の和)を末端から積み上げる
    kids = [[] for _ in nodes]
    for ni in range(1, len(nodes)):
        kids[parent[ni]].append(ni)
    rad = [0.0] * len(nodes)
    tip_r = h * sp["tip_r"]
    for ni in range(len(nodes) - 1, -1, -1):
        if not kids[ni]:
            rad[ni] = tip_r
        else:
            rad[ni] = (sum(rad[k] ** 2.2 for k in kids[ni])) ** (1 / 2.2)
    scale = r0 / max(1e-6, rad[0])
    rad = [r * scale for r in rad]

    segs = []
    depth = [0] * len(nodes)
    for ni in range(1, len(nodes)):
        pi = parent[ni]
        depth[ni] = depth[pi] + 1
        segs.append((nodes[pi].copy(), nodes[ni].copy(), rad[pi], rad[ni], depth[ni]))
    tips = [(nodes[ni], (nodes[ni] - nodes[parent[ni]]).normalized(), rad[ni], depth[ni])
            for ni in range(1, len(nodes)) if not kids[ni]]
    return segs, tips


def tier_prof(u):
    """段の長さの縦断面(u = 0 最下段 … 1 最上段)。

    ⭐ 最下段を **1.00 にしない** — 松は下枝から枯れ上がるので、いちばん短いのは最下段。
      ここを一定にすると樹冠の下端が**水平に切れて**見える(2026-09-07 差し戻し③)。
    ⭐ **天辺を尖らせない。**上へ単調に細らせると円錐になり、モミ・スギに読める
      (3巡目で実測 — 天辺が細い房になって幹が裸で突き出した)。松の壮齢木は
      中〜上でいちばん張る**傘形**で、在庫の黒松もいちばん広いのは上から2段目。"""
    if u < 0.30:
        return 0.58 + (u / 0.30) * 0.34           # 枯れ上がり 0.58 → 0.92
    v = (u - 0.30) / 0.70
    return 0.92 + 0.10 * math.sin(v * math.pi) - 0.18 * v ** 2.2   # 中上で張り 天辺 0.74


def pine_skeleton(sp, h, rnd):
    """**松の骨格を「段」として直に組む。**返す形は `branch_skeleton` と同じ。

    ⛔ **空間占有法(`branch_skeleton`)は松には使えない。**誘引点を塊に撒いても
      (`clump`)、出てくるのは「棒の上に blob の傘が一つ」で**広葉樹の若木**に読める
      — 2026-09-07 に普請奉行が在庫の黒松と並べて差し戻した。数(丈・異方比・樹冠比)は
      合っていて**姿だけが違う**ので、数を触っても直らない。
    ⭐ 在庫 `Tree_BlackPine_Big_Green_01` の実メッシュ(`stock_mesh` で起こして実測)から
      読み取った松の姿の要は4つ。確率的な伸長では出ないので**明示的に置く**:
      ① 幹が**ゆるく曲がる**(通直な電柱にしない。⚠「立ち上がりが高い」は林の松の条件で
         あって、幹をまっすぐにしろという意味ではない — 差し戻し②)
      ② 枝が**水平に張り出して段(層)を成す**。段と段の間に**空が抜けて幹が見える**
      ③ 針葉が段の上に**板状の房**として乗る(二次枝が水平に扇へ割れ、その先だけに付く)
      ④ 枝下に**枯れ上がりかけた小枝の名残**が残る(樹冠の付け根を水平に切らない)
    """
    P = sp["pine"]
    tau = math.tau
    nodes = [Vector((0, 0, 0))]
    parent = [-1]
    noleaf = set()                    # 葉を付けない節(枯れ枝の名残)

    def chain(start, pts, leaf=True):
        """節を数珠つなぎに足して、足した節の番号を返す。"""
        out, pi = [], start
        for q in pts:
            nodes.append(q); parent.append(pi)
            pi = len(nodes) - 1
            out.append(pi)
            if not leaf:
                noleaf.add(pi)
        return out

    # ---- ① 幹。位相の違う2つの正弦を重ねた**なだらかな S 字**。
    #      ⛔ 節ごとに乱数を引かない(シルエットに刻みが出る。README の落とし穴)。
    n_tr = P["trunk_seg"]
    z_top = h * P["trunk_top"]
    amp = h * P["sway"]
    ph1, ph2 = rnd.uniform(0, tau), rnd.uniform(0, tau)
    a2 = rnd.uniform(0.30, 0.62)
    az0 = rnd.uniform(0, tau)
    az1 = az0 + rnd.uniform(1.4, 2.4)

    # ⭐ **正味の傾き**を足す。正弦2つだけでは行きと戻りが相殺して、遠目に通直へ戻る
    #    (2巡目の近景レンダで実測 — 幹が「まっすぐな棒」のままだった)。
    lean = h * P["lean"]
    azL = rnd.uniform(0, tau)

    def txy(t):
        # `- sin(ph)` で t=0 の横ずれを 0 に固定 ⇒ ピボットは**幹の芯・地面**のまま
        s1 = amp * (math.sin(t * 2.7 + ph1) - math.sin(ph1))
        s2 = amp * a2 * (math.sin(t * 5.1 + ph2) - math.sin(ph2))
        return Vector((math.cos(az0) * s1 + math.cos(az1) * s2 + math.cos(azL) * lean * t ** 1.35,
                       math.sin(az0) * s1 + math.sin(az1) * s2 + math.sin(azL) * lean * t ** 1.35,
                       0.0))

    trunk = [0]
    prev = 0
    for i in range(1, n_tr + 1):
        t = i / n_tr
        q = txy(t); q.z = z_top * t
        nodes.append(q); parent.append(prev)
        prev = len(nodes) - 1
        trunk.append(prev)

    def trunk_at(z):
        return min(trunk[1:], key=lambda i: abs(nodes[i].z - z))

    # ---- ②③ 段。1段 = 幹の1点から放射する3〜4本の一次枝で、
    #      各一次枝の外側半分が**水平の扇**に割れて板状の房の台になる。
    # ⛔ **段を等間隔・等本数・等長にしない。**2巡目は 5 段が均等に並び、各段が幹を
    #    貫く**対称な円盤**になって、松ではなく**モミ・スギの若木**(あるいは苗畑の
    #    仕立て物)に読めた。⇒ 段の高さ・本数・長さ・出の角度をすべて散らす。
    n_ti = rnd.randint(*P["tiers"])
    zlo, zhi = h * P["tier_lo"], h * P["tier_hi"]
    gaps = [rnd.uniform(0.55, 1.60) for _ in range(max(1, n_ti - 1))]
    gsum = sum(gaps)
    zt_list, zc = [], zlo
    for k in range(n_ti):
        zt_list.append(zc)
        if k < len(gaps):
            zc += (zhi - zlo) * gaps[k] / gsum
    az_seed = rnd.uniform(0, tau)
    twig_ends = []
    for k in range(n_ti):
        u = k / max(1, n_ti - 1)
        zt = zt_list[k]
        ni0 = trunk_at(zt)
        o = nodes[ni0]
        Lb0 = h * P["reach"] * tier_prof(u) * rnd.uniform(0.86, 1.14)
        # 本数も不揃い(片側だけの段があってよい)。上ほど少ない
        nb = rnd.choice((3, 4, 4, 5, 5) if u < 0.5 else (3, 3, 4, 4))
        for j in range(nb):
            # 段ごとに黄金角ずらす ⇒ 上下の段が同じ方角に重ならない。
            # ⭐ 方位のばらつきを大きく取り、段の中に**空く方角**を作る
            az = az_seed + k * 2.39996 + j * tau / nb + rnd.uniform(-0.55, 0.55)
            Lb = Lb0 * rnd.uniform(0.74, 1.26)
            e = Vector((math.cos(az), math.sin(az), 0))
            pp = Vector((-e.y, e.x, 0))
            # 出は上向き・中ほどで水平・先は垂れる。下段ほど深く垂れる(老枝)。
            # ⭐ 出の角度を枝ごとに散らす(全部水平だと円盤になる)
            rise = P["rise"] * rnd.uniform(0.35, 1.85)
            droop = P["droop"] * (1.35 - 0.5 * u) * rnd.uniform(0.7, 1.4)
            bend = rnd.uniform(-0.28, 0.28)
            roll = rnd.uniform(-P["roll"], P["roll"])   # 房の板を傾ける(水平の円盤にしない)
            m = P["prim_seg"]
            pts, zs = [], []
            for i in range(1, m + 1):
                s = i / m
                zz = Lb * (rise * s - (rise + droop) * s * s)
                zs.append(zz)
                pts.append(o + e * (Lb * s)
                           + pp * (Lb * bend * math.sin(s * math.pi))
                           + Vector((0, 0, zz)))
            prim = chain(ni0, pts)

            def spray(anchor_i, base_dir, ln, up):
                """末端の小枝を**水平に3本の扇**で出す(針葉が付くのはここ)。"""
                a = nodes[anchor_i]
                bz = math.atan2(base_dir.y, base_dir.x)
                nt_ = P["twig_n"]
                for t3 in range(nt_):
                    da = (t3 - (nt_ - 1) / 2.0) * P["twig_fan"] + rnd.uniform(-0.18, 0.18)
                    d = Vector((math.cos(bz + da), math.sin(bz + da),
                                up + rnd.uniform(-0.10, 0.14)))
                    q = a + d.normalized() * ln * rnd.uniform(0.80, 1.20)
                    twig_ends.append(chain(anchor_i, [q])[0])

            # 二次枝 — 一次枝の外側から**水平に**開く。段の厚みは `plate` で抑える
            for fr, lf in zip(P["sec_at"], P["sec_len"]):
                gi = min(len(prim) - 1, max(0, int(round(fr * m)) - 1))
                a = nodes[prim[gi]]
                side = 1 if rnd.random() < 0.5 else -1
                da = side * rnd.uniform(*P["fan"])
                ln = Lb * lf
                # `roll` = 板の傾き。横へ開いた分だけ上下する ⇒ 板が斜めに寝る
                d = Vector((math.cos(az + da), math.sin(az + da),
                            roll * math.sin(da)
                            + rnd.uniform(-P["plate"], P["plate"]) * 1.6))
                mid = a + d.normalized() * ln * 0.55
                end = a + d.normalized() * ln
                sec = chain(prim[gi], [mid, end])
                spray(sec[-1], d, Lb * P["twig_len"], P["twig_up"])
            # 一次枝の先端にも房
            spray(prim[-1], e, Lb * P["twig_len"], P["twig_up"])

    # ---- ④ 枝下の枯れ枝の名残(葉は付けない)
    for _ in range(rnd.randint(*P["stubs"])):
        zs_ = h * rnd.uniform(0.15, P["tier_lo"] - 0.02)
        ni0 = trunk_at(zs_)
        a = nodes[ni0]
        az = rnd.uniform(0, tau)
        ln = h * rnd.uniform(0.022, 0.058)
        d = Vector((math.cos(az), math.sin(az), -rnd.uniform(0.15, 0.50))).normalized()
        chain(ni0, [a + d * ln * 0.55, a + d * ln], leaf=False)

    # ---- 梢の房(頂端。ここが無いと天辺が禿げる)
    top = trunk[-1]
    for t3 in range(3):
        az = az_seed + t3 * tau / 3 + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(az) * 0.55, math.sin(az) * 0.55, 1.0)).normalized()
        twig_ends.append(chain(top, [nodes[top] + d * h * P["top_tuft"]])[0])

    # ---- 太さ: ダ・ヴィンチ則(`branch_skeleton` と同じ積み上げ)
    kids = [[] for _ in nodes]
    for ni in range(1, len(nodes)):
        kids[parent[ni]].append(ni)
    rad = [0.0] * len(nodes)
    tip_r = h * sp["tip_r"]
    for ni in range(len(nodes) - 1, -1, -1):
        rad[ni] = tip_r if not kids[ni] else (sum(rad[k] ** 2.2 for k in kids[ni])) ** (1 / 2.2)
    scale = h * sp["trunk_r"] / max(1e-6, rad[0])
    rad = [r * scale for r in rad]
    rad[0] *= P.get("flare", 1.0)                 # 根張り(地際だけ太らせる)

    segs = []
    depth = [0] * len(nodes)
    for ni in range(1, len(nodes)):
        pi = parent[ni]
        depth[ni] = depth[pi] + 1
        # ⭐ 深さを **-1** にした区間は `leaf_centers` が葉を付けない(枯れ枝の名残)
        segs.append((nodes[pi].copy(), nodes[ni].copy(), rad[pi], rad[ni],
                     -1 if ni in noleaf else depth[ni]))
    tips = [(nodes[ni], (nodes[ni] - nodes[parent[ni]]).normalized(), rad[ni], depth[ni])
            for ni in range(1, len(nodes)) if not kids[ni]]
    return segs, tips


def _ring(bm, c, q, r, n):
    """角 0 から一周する n+1 頂点の環(最後は最初と同位置。UV の継ぎ目のため重ねる)。"""
    return [bm.verts.new(c + q @ (Vector((math.cos(math.tau * i / n),
                                          math.sin(math.tau * i / n), 0)) * r))
            for i in range(n + 1)]


def _sides(r, rmax, nseg):
    """太さから断面の辺数を決める。⭐ **節の半径**だけで決まるようにしてある —
    そうしないと親の端と子の始めで環がずれ、幹に**見通しの穴**が開く(2026-09-07 実測)。"""
    f = r / max(1e-9, rmax)
    return nseg if f >= 0.30 else (max(4, nseg - 2) if f >= 0.08 else 4)


def add_branches(bm, segs, nseg, bark_uv=0.0, adaptive=False):
    """枝を多角柱で起こす(先細り)。

    ⭐ `bark_uv` > 0 なら **樹皮に円筒 UV** を張る(u = 周、v = 高さ / `bark_uv`[m])。
      ⛔ 0 のままだと全ループが UV (0,0) の**一点貼り**になり、樹皮テクスチャの
        左下 1px だけを引き伸ばす(松では真っ黒な幹になった。2026-09-07)。
      ⚠ 既存の樹種は一点貼りのまま焼いてあるので、**種ごとに明示して**切り替える
        (⇒ 申し送り: 落葉高木・常緑・ウメ・低木も順次張り直すこと)。

    ⭐ `adaptive` = **太さで断面の辺数を変える**(幹は 8 角・小枝は 4 角)。
      ⛔ 辺数が変わる継ぎ目を四角形で繋ぐと環の頂点数が合わず、**幹に穴が開く**
        (1巡目の近景レンダに白い切れ目として写った)。⇒ 頂点数の違う環どうしを
        **角で歩いて三角で橋渡しする**。辺数は**節の半径**からだけ決めるので、
        親の端と子の始めは必ず同じ環になる。
    """
    uvl = bm.loops.layers.uv.verify() if bark_uv > 0 else None
    rmax = max((s[2] for s in segs), default=1.0)
    for a, b, r0, r1, lv in segs:
        d = (b - a); ln = d.length
        if ln < 1e-4: continue
        q = d.normalized().rotation_difference(Vector((0, 0, 1))).inverted()
        if not adaptive:
            ring0, ring1 = [], []
            for i in range(nseg):
                t = i / nseg * math.tau
                p = Vector((math.cos(t), math.sin(t), 0))
                ring0.append(bm.verts.new(a + q @ (p * r0)))
                ring1.append(bm.verts.new(b + q @ (p * r1)))
            for i in range(nseg):
                j = (i + 1) % nseg
                f = bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
                if uvl is not None:
                    v0, v1 = a.z / bark_uv, b.z / bark_uv
                    u0, u1 = i / nseg, (i + 1) / nseg
                    for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                        lp[uvl].uv = uv
            continue
        n0, n1 = _sides(r0, rmax, nseg), _sides(r1, rmax, nseg)
        R0, R1 = _ring(bm, a, q, r0, n0), _ring(bm, b, q, r1, n1)
        v0, v1 = (a.z / bark_uv, b.z / bark_uv) if uvl is not None else (0.0, 0.0)
        i = j = 0
        while i < n0 or j < n1:
            take0 = j >= n1 or (i < n0 and (i + 1) / n0 <= (j + 1) / n1)
            if take0:
                tri3 = ((R0[i], i / n0, v0), (R0[i + 1], (i + 1) / n0, v0), (R1[j], j / n1, v1))
                i += 1
            else:
                tri3 = ((R0[i], i / n0, v0), (R1[j + 1], (j + 1) / n1, v1), (R1[j], j / n1, v1))
                j += 1
            try:
                f = bm.faces.new([t[0] for t in tri3])
            except ValueError:
                continue
            if uvl is not None:
                for lp, t in zip(f.loops, tri3):
                    lp[uvl].uv = (t[1], t[2])


def branch_kd(segs, h):
    """枝の**芯線**を細かく標本化した KD 木。葉のカードが枝から離れていないかを測る物差し。
    ⭐ これが「浮いた葉の房」を数値で捕まえる唯一の道具 — 目視では見落とす。"""
    from mathutils.kdtree import KDTree
    stp = max(0.015, h * 0.008)
    pts = []
    for a, b, r0, r1, lv in segs:
        n = max(1, int((b - a).length / stp))
        for i in range(n + 1):
            pts.append(a.lerp(b, i / n))
    kd = KDTree(len(pts))
    for i, q in enumerate(pts):
        kd.insert(q, i)
    kd.balance()
    return kd


def leaf_centers(sp, h, rnd, segs, tips, per_tip, scale):
    """葉のカードの**中心**を決める。返すのは [(中心, 大きさ)] と検査値。

    ⛔ **2026-09-07 の是正 — 房を枝から浮かせない。**
      旧実装は枝先から `±2.2×s0`(各軸)へ散らしていた。低木では s0=0.16m なので
      **枝先から最大 0.62m** 離れ、丈 2.0m の株に対して「空中に浮いた葉の房」と
      「地面に落ちた房」が焼き付いた(普請奉行が近景レンダで指摘。前巡の
      『誘引点を密にする』『z を clamp する』では**消えなかった** — 散らしの幅が
      原因なので、誘引点をいくら密にしても房は枝から離れたまま)。
    ⭕ `leaf_mode="segment"` = **枝のセグメント上に中心を置く**。横ずれは房の半寸の
      0.6 倍までに抑えるので、カード(半寸 s)は必ず枝の芯を跨ぐ。構造的に孤立できない。
    ⚠ 旧来の "tip" モードは常緑広葉樹・ウメ・モミジ・落葉高木3種の**焼き済みの姿**なので
      残してある(切り替えると全樹種の再検証が要る)。→ 申し送り。
    """
    s0 = h * sp["leaf_scale"] * scale
    align = sp.get("leaf_align", False)
    out = []
    if sp.get("leaf_mode") == "segment":
        # 葉が付くのは**細い枝**だけ(幹や大枝には付けない)
        rmin = min(s[3] for s in segs)
        thr = rmin * sp.get("leaf_r_mult", 3.2)
        # ⭐ 深さ **-1** = 枯れ枝の名残(松の枝下)。葉を付けない。
        twigs = [s for s in segs if s[3] <= thr and s[4] >= 0]
        # 枚/m。⚠ 丈で割り戻す(上の LEAF_REF_H の注記)。per_tip は LOD の間引き率
        dens = sp["leaf_per_m"] * (LEAF_REF_H / h) * per_tip
        for a, b, r0, r1, lv in twigs:
            x = (b - a).length * dens
            n = int(x) + (1 if rnd.random() < (x - int(x)) else 0)
            # ⭐ `leaf_align` = 房の長手を枝の向きへ寝かせる(針葉樹)。
            #    ⛔ 中心を枝の芯からずらして「先へ突き出す」ことはしない —
            #      房が枝を跨がなくなり、孤立片の関門が意味を失う。
            axis = (b - a).normalized() if align and (b - a).length > 1e-6 else None
            for _ in range(n):
                s = s0 * rnd.uniform(0.72, 1.28)
                c = a.lerp(b, rnd.uniform(0.0, 1.0))
                d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
                if d.length > 1e-6:
                    c = c + d.normalized() * (s * rnd.uniform(0.0, 0.45 if align else 0.60))
                c.z = max(c.z, s * 0.55)           # 地面へ沈めない
                out.append((c, s, axis))
        lim = s0 * 1.30
    else:
        for base, dirv, rad, lv in tips:
            for _ in range(int(per_tip)):
                s = s0 * rnd.uniform(0.72, 1.28)
                c = base + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1),
                                   rnd.uniform(-0.7, 1.1))) * s0 * 2.2
                c.z = max(c.z, s * 0.75)
                out.append((c, s, None))
        lim = s0 * 4.20                            # 旧モードの散らしの上限(実質の無効化)
    # --- ⭐ 最後の関門: 枝から離れすぎた房は**落とす**。
    #     ⛔ 「clamp を入れた」では受け取れない。ここで実測して切る。
    kd = branch_kd(segs, h)
    kept, dropped, dmax = [], 0, 0.0
    for c, s, ax in out:
        _, _, d = kd.find(c)
        if d is None:
            d = 1e9
        if d > lim:
            dropped += 1
            continue
        dmax = max(dmax, d)
        kept.append((c, s, ax))
    return kept, dict(n=len(kept), dropped=dropped, dmax=dmax, lim=lim, s0=s0)


def add_leaves(bm, cents, rnd, uvs=None):
    """葉のカード(十字に組んだ板)。⛔ 一枚板にしない — 横から見て消える。

    ⭐ 第3要素 `ax`(枝の向き)が入っていれば、**カードの長手をその向きへ寝かせる**。
      針葉樹のアトラスは「小枝＋針葉の房」が縦長に描かれているので、寝かせないと
      アトラスの小枝が実際の枝と直交して刺さって見える(2026-09-07)。"""
    uvs = uvs or SPROUT_UV
    uvl = bm.loops.layers.uv.verify()
    for c, s, ax in cents:
        yaw = rnd.uniform(0, math.tau); pit = rnd.uniform(-0.5, 0.5)
        u0, v0, u1, v1 = uvs[rnd.randrange(len(uvs))]
        ar = (v1 - v0) / max(1e-6, (u1 - u0))         # 房の縦横比を保つ
        # ローカル +Z を枝の向きへ寝かせる基底(ax が無ければ従来どおり世界の +Z)
        Rd = Vector((0, 0, 1)).rotation_difference(ax).to_matrix() if ax else None
        tilt = rnd.uniform(-0.22, 0.22) if ax else 0.0
        for k in range(2):                            # 十字の2枚
            if Rd is None:
                Rk = Euler((pit, 0, yaw + k * math.pi / 2)).to_matrix()
            else:
                Rk = Rd @ (Euler((0, 0, yaw + k * math.pi / 2)).to_matrix()
                           @ Euler((tilt, 0, 0)).to_matrix())
            pts = [c + Rk @ Vector((x * s, 0, y * s * ar)) for x, y in
                   ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            f = bm.faces.new([bm.verts.new(v) for v in pts])
            for lp, (uu, vv) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                lp[uvl].uv = (uu, vv)


def build_one(key, size, lod, rnd):
    sp = SPECIES[key]; h = sp.get("sizes", SIZE)[size]; L = LOD[lod]
    # ⭐ 松だけは骨格の組み方が違う(段=枝の層を直に置く)。⛔ 他樹種は従来どおり。
    segs, tips = (pine_skeleton(sp, h, rnd) if sp.get("skeleton") == "pine"
                  else branch_skeleton(sp, h, rnd))
    # --- 樹皮
    me_b = bpy.data.meshes.new("bark")
    # ⭐ `seg_bias` は**枝の断面の粗さ**だけを動かす(既定 1.0 = 従来どおり)。
    #    低木は葉に埋もれて枝が見えないので、三角数をここで落とす。
    nseg = max(4, int(round(L["seg"] * sp.get("seg_bias", 1.0))))
    bm = bmesh.new(); add_branches(bm, segs, nseg, sp.get("bark_uv", 0.0),
                                   sp.get("adaptive_seg", False))
    bm.to_mesh(me_b); bm.free()
    ob_b = bpy.data.objects.new("bark", me_b); bpy.context.collection.objects.link(ob_b)
    # --- 葉(枝先を間引く)
    keep = [t for t in tips if rnd.random() < L["tip"]]
    if sp.get("leaf_mode") == "segment":
        per = L["tip"] * L["leaf"]                 # LOD の間引きは枚数密度に効かせる
    else:
        per = max(1, int(round(sp["leaf_per_tip"] * L["leaf"])))
    cents, st = leaf_centers(sp, h, rnd, segs, keep, per, 1.0)
    me_l = bpy.data.meshes.new("leaf")
    bm = bmesh.new()
    add_leaves(bm, cents, rnd, PINE_UV if sp.get("uv") == "pine" else SPROUT_UV)
    bm.to_mesh(me_l); bm.free()
    ob_l = bpy.data.objects.new("leaf", me_l); bpy.context.collection.objects.link(ob_l)
    # --- 材質(名前だけ。中身は Unity で remap して在庫の .mat へ結ぶ)
    for ob, nm in ((ob_b, sp.get("bark", MAT_BARK)), (ob_l, sp.get("leaf_mat", MAT_LEAF))):
        m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        ob.data.materials.append(m)
    o = V.join([ob_b, ob_l], "LOD_%d" % lod)
    # --- 樹高を目標へ正規化。⚠ 空間占有法は誘引点の散らばりで背が伸び縮みするので、
    #     指図が樹高で層を決めている以上、**出来上がりを測って合わせる**(呼び寸法で信じない)。
    zs = [v.co.z for v in o.data.vertices]
    if zs:
        got = max(zs) - min(zs)
        if got > 1e-4:
            k = h / got
            for v in o.data.vertices:
                v.co = Vector((v.co.x * k, v.co.y * k, (v.co.z - min(zs)) * k))
            o.data.update()
    # --- 向き: Blender Z-up → Unity Y-up は FBX 書き出しが行う。ピボットは幹の芯・地面
    st["scale"] = k if zs and got > 1e-4 else 1.0
    return o, st


def hook():
    """検証レンダのためだけに提供元のテクスチャを読む。
    ⛔ FBX には材質**名**しか入らない — Unity 側の remap が本番。"""
    for nm, tex, alpha in ((MAT_BARK, TEX_BARK, False), (MAT_LEAF, TEX_LEAF, True),
                          (MAT_PINE_BARK, TEX_PINE_BARK, False),
                          (MAT_PINE_LEAF, TEX_PINE_LEAF, True)):
        m = bpy.data.materials.get(nm)
        if m is None or not os.path.exists(tex): continue
        m.use_nodes = True; nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None: continue
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(tex, check_existing=True)
        img.location = (-600, 300)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.75
        if alpha:
            nt.links.new(img.outputs['Alpha'], b.inputs['Alpha'])
            m.blend_method = 'CLIP'; m.alpha_threshold = 0.4
            try: m.show_transparent_back = False
            except Exception: pass


def tri(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    args = [a for a in argv if not a.startswith("--")]
    key = args[0] if args else "jouryoku"
    # `--var <n>` で1寸法あたり n 本の**別個体**を焼く(既定 3)。
    # ⚠ 2026-09-01 庭方の指摘:「Own.Jokuroku は Mid/Small の 2 プレハブで
    #   モッコク・モチノキ・カシ・シイの 4 樹種 43 本を代表しており、近景で
    #   同じ木の繰り返しになる」。⭕ 骨格の乱数を個体ごとに変えて姿を散らす。
    #   ⛔ 種は個体番号から決める(時刻や連番で振らない — 焼き直すたびに姿が変わると
    #      検証レンダが比較できない)。1本目は従来と同じ名前のまま(既存の参照を壊さない)。
    nvar = int(args[args.index("--var") + 1]) if "--var" in args else 3
    args = [a for a in args if a != "--var" and not a.isdigit()] if "--var" in args else args
    sizes = args[1:] or ["Mid"]
    os.makedirs(OUT, exist_ok=True)
    for size in sizes:
      for vi in range(nvar):
        V.reset()
        # ⛔ `hash()` を使わない — **str の hash はプロセスごとに乱数化される**(PYTHONHASHSEED)。
        #    上の「⛔ 種は個体番号から決める」は守れておらず、**焼き直すたびに姿が変わって
        #    検証レンダが比較できなかった**(2026-09-07 部材方が実測。同じ引数で2回焼くと
        #    Tree_Teiboku_H20(当時の綴りは Mid)の幅が 2.08m → 1.78m になった)。⭕ crc32 は安定。
        # ⛔ **`size` の綴りは種そのもの。**呼び名を変えると同じ丈でも別の骨格が出る
        #    (2026-09-08 の Small→H12 / Mid→H20 の改名で6点の姿が入れ替わった)。
        #    ⚠ `sizes` に鍵を**足す**だけなら既存の鍵の種は動かない — 改名とは別の話。
        seed = zlib.crc32(("%s/%s/%d" % (key, size, vi)).encode()) & 0xffffffff
        lods, stats = [], []
        for i in range(3):
            rnd2 = random.Random(seed)                             # 同じ骨格から間引く
            o, st = build_one(key, size, i, rnd2)
            lods.append(o); stats.append(st)
        mn, mx = V.bbox(lods)
        suffix = "" if vi == 0 else "_%02d" % (vi + 1)
        name = "Tree_%s_%s%s" % (key.capitalize(), size, suffix)
        print("[tree] %s %s%s  LOD tri=%d/%d/%d  W %.2f × H %.2f × D %.2f"
              % (SPECIES[key]["label"], size, suffix,
                 tri(lods[0]), tri(lods[1]), tri(lods[2]),
                 mx.x - mn.x, mx.z - mn.z, mx.y - mn.y))
        # ⭐ **孤立した葉の房の検査**(2026-09-07)。目視だけに頼らない。
        #   `dmax` = 葉のカードの中心から**最寄りの枝の芯**までの最大距離[m](樹高正規化前)。
        #   `dropped` = 関門で落とした房の数。segment モードでは 0 が正常。
        for i, st in enumerate(stats):
            print("      LOD%d 葉%d枚  枝からの最大距離 %.3fm (関門 %.3fm)  落とした房 %d"
                  % (i, st["n"], st["dmax"], st["lim"], st["dropped"]))
        for i, o in enumerate(lods): o.name = "LOD_%d" % i
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx(lods, path)
        print("[tree] wrote %s" % path)
        if do_render:
            hook()
            V.studio((mn.x - (mx.x-mn.x)*1.6, mn.y - (mx.y-mn.y)*2.2, (mx.z-mn.z)*0.55),
                     ((mn.x+mx.x)/2, (mn.y+mx.y)/2, (mx.z-mn.z)*0.45), res=(1100, 1400))
            V.render(os.path.join(SHOT, "tree_%s_%s%s.png" % (key, size, suffix)))


main()
