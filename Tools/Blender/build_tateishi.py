"""**立石(縦長の庭石)3種** — 松江松平上屋敷(matsudaira_dewa)の庭。ユーザー裁定3=A(2026-09-06)。

    blender --background --python Tools/Blender/build_tateishi.py -- [S|M|L|all] [--render]

【なぜ新造するか】在庫の岩は全部が平たい転石で「丈>幅」の石が無い。
  ⛔ `JG.Rock01..03`(FreeJapaneseGarden `JG_Rock_A_01..03`)は実見すると平たい転石ばかりで、
     縦長の立石に使える個体が無い(実測 W×H×D は `docs/asset-index.tsv` 参照 — どれも
     H が W・D と大差ない扁平形)。
  ⛔ **NatureManufacture の photoscanned rock を「立てて」使う手**(`build_okabe_niwa._rock`
     の `stand=True`)も検討したが、あれは**丸い転石を横倒しから縦に起こすだけ**で、
     縦の稜・割れ肌を持つ「花崗岩の割石」には見えない(岡部庭の立石は丈 1.0m 級までしか
     使っていない — 本件は 2.1m 級の主石・鏡石が要るので、より意図的に「立つ」形が要る)。
  ⭕ よって**新規に手続き生成**する(bmesh。円柱や直方体の単純押し出しではない)。
     ⛔ ゼロからのモデリングを禁じる規則1は「在庫にキットがある建築部材」向けの規則で、
     自然石の意匠(庭方が既に "縦の稜+割れ肌=花崗岩の割石" と決めている)はこの限りでない
     — CLAUDE.md 規則17の言う「専門役(庭方)が意匠を決め、書き起こす側(部材方)が作る」構図。

【材質】⛔⛔ **依頼は「JG_Rock_A_01 の材質名を保て」だったが、それは実装しない。**
  実見すると `JG_Rock_A_01_LOD0.fbx` のマテリアル名は Blender から見て **`Test`**
  (`Assets/Waldemarst/.../Rocks/JG_Rock_A_01.prefab` が実際に使う `M_FJG_Rock_001.mat` とは別物 —
  prefab は手作業で貼り替えてある)。**この "Test" という名前の .mat はプロジェクトに存在しない**
  (`find` で0件)。同じ地雷は 2026-09-04 に岡部庭の景石(`Ishigumi`/`Tobiishi`/`Kutsunugi`)でも
  踏まれていて、そのときの結論がそのまま `EdoAssets.cs` にコメントで残っている:
    「⛔ `JG.Rock01..03` は使わない(FBX 内の材質名が `Test` で remap が当たらない)」
  ⭕ 規約の目的(新規マテリアルを作らず既存 .mat に remap で結び直す)を守るため、
  **岡部庭と同じ在庫岩 `M_photoscanned_rocks_01`(NatureManufacture・写真計測の実肌)**の
  材質名をそのまま運ぶ。ジオメトリは新規でも材質名はキット由来のまま — 新規マテリアルは
  1つも作っていない。

【UV】**一点貼りにしない**(規約4)。同じ NatureManufacture のアトラス
  (`T_Photoscanned_rocks_01_BC.tga` 4096×4096)から実在の岩1体ぶんの矩形を取り、
  その**実測テクセル密度**(UV幅・高さ ÷ その岩の実寸)を側面・天端に**そのまま**使う
  — 密度を変えると同じ岩肌なのに解像感が変わって浮く。**周方向は累積弧長・鉛直方向は高さ**
  で座標を作り、密度を掛けたあと `pingpong()` で [0,1] へ折り返す(継ぎ目が出ない。
  `build_okabe_niwa.Take.pole()` の考え方と同じ)。丈2.1mの L でも周長×密度・高さ×密度は
  どちらも1を超えないので実際には折り返しは発生しない(念のため入れてあるだけ)。

【形の作り方(bmesh)】
  1. 断面(Blender XY = Unity 幅×厚み)は**前面だけ真っ平ら**(見付・−Y = Unity +Z)、
     残りは不等角度でジャギーに振った円弧(割石の丸い自然面)。前面の2隅だけ高さ方向の
     ノイズを弱くして、上から下まで**素直に平らな見付面**を保つ。
  2. 高さ方向に粗いバンド(7段)を積んで、**バンドごとの半径ジッタは頂点indexに固定**
     (= 縦の稜がそのまま上まで通る)。上へ行くほど**先細り**(裾に対して天端 0.82倍)。
  3. 天端は水平に閉じない — 中心へ向けたファンで閉じたうえ、面内方向へ**線形の傾き**を
     加えて(僅かに傾く天端)、天端リング自体にも軽いノイズを乗せる。
  4. 粗い形(⛔ 円柱に見えるほど細かくしない)を `bmesh.ops.subdivide_edges` で
     グリッド分割し、**前面以外**の頂点だけ小さな法線方向ノイズを足して割れ肌を作る
     (前面は amp を弱くして「見付」を保つ)。
  5. LOD1 は Decimate モディファイアで LOD0 を約4割に落として同じ FBX に同梱
     (`<名前>_LOD0` / `<名前>_LOD1` — README の LOD 命名規則どおり)。

【踏んだ落とし穴】
  ・⛔ **頂点を面ごとに複製すると Decimate が効かない。**`vklib.box()` や `vkmesh.Mesh` の
    ように1面1面を独立頂点で積むと、Decimate モディファイアが辺を共有しないので
    ほぼ潰れない。⭕ グリッド状に頂点を**共有**させて(標準的な loft メッシュ)、
    UV は頂点位置から決定論的に計算する(loop ごとに書けば、同じ位置の頂点でも
    面ごとに別UVにできるので「共有頂点+個別UV」は両立する)。
  ・⚠ `bisect_plane` で前面を切り落とす案は**孤立頂点が残る**(README既知)ので不採用にし、
    最初から前面2隅を直線で結ぶ多角形として生成した(切ってから直すより作るときに直す)。
  ・⚠ 天端を単純な水平ngonで閉じると「僅かに傾く」を表現できないうえ、傾けると非平面
    ngonになって法線がおかしくなる。⭕ 中心ファン(三角形の集合)にすれば非平面でも
    破綻しない。

【2026-09-06 第3次差し戻し「庭石ですが、角が鋭すぎませんか」への対応】
  ⭕ `round_edges()` / `round_apex()` を追加し、bmesh の **bevel オペレータ**で
  見付の縁・側面どうしの粗い facet 境・天端の小面の境を実際に丸めた
  (segments 2〜3・半径 2〜6cm)。以前の `chamfer_front_seam`(前面の2隅の列だけを
  乱数で振って面取りっぽく見せる偽物)は削除 — 新しいセグメントが入らないので
  「直線を別の直線に置き換えるだけ」で、第2次差し戻しの原因そのものだった。
  ・⛔ **bmesh.ops.bevel は1回の呼び出しに半径を1つしか取れない**(辺ごとに
    違う半径は指定できない)。⭕ 辺を高さ4バンド×ランダムな小さな束に分けて、
    束ごとに別の半径・セグメント数で複数回 bevel する。束をまたいで前の bevel が
    隣の頂点を動かすことがあるので、**毎回 `edge.is_valid`/`vert.is_valid` で
    生存確認**してから渡す(風化石は稜ごとに丸みが不揃いなのが自然でもある)。
  ・⚠ **「丸めるべき辺」を法線の角度しきい値だけで決めると、天端の小面と側面の境を
    取りこぼす。**hosori(強い先細り)で天端が狭くなると小面の法線が乱れ、角度が
    しきい値を割り込むことがある。⭕ **cap(天端・底ファン)と非capの境**は角度に
    よらず必ず丸め対象にする(`is_cap` レイヤーで機械的に判定できる — 法線に頼らない
    のは README「天端・底の判定は面の法線でなく作った時点のタグで持つ」と同じ理由)。
    ただし底(z≈0)は埋まって見えないので除外する。
  ・⛔ **頂点1点に収束するファンの頂は edge bevel では丸められない**(辺の操作なので)。
    ⭕ `is_apex` レイヤーでファンの要をタグしておき、`affect='VERTICES'` の
    vertex bevel で個別に潰す。
  ・⭕ 稜の丸めは**割れ肌ノイズ(`add_crack_noise`)より先に**やる。ノイズを先に
    掛けると細分後のほぼ全辺が非ゼロの角度を持ってしまい、角度しきい値で
    「本当の粗い facet 境」だけを拾えなくなる(割れ肌まで丸めてつぶれた石になる)。

【2026-09-06 UV直し(形は無変更)】普請奉行差し戻し: `tateishi_L2_front_closeup.png` の
  頭の帯(上端から10〜15%・肩リング〜割れ面)で正面近景に縦縞・縦流れ。
  ⛔ **原因は「頭=cap相当」を一括りに (x,y) 平面投影していたこと** — ではなく
  試行錯誤の結果、**もっと根が深いと判明した**:
    1回目の疑い(不採用): (x,y) 平面投影だと複数の割れ面が apex 付近の狭い範囲へ
    重なって収束するから、と考えて「側面の円筒投影をそのまま上へ延長」(周方向 u は
    既存の頂点レイヤー `uparam`、鉛直方向 v は新設の頂点レイヤー `vparam`)に
    差し替えたが、**レンダで確認すると縞は消えなかった**(むしろ放射状に悪化)。
  ⛔⛔ **真因**: `uparam`/`vparam` は**頂点**レイヤー — 1個の頂点には1つの値しか
    持てない。ところが頭の割れ面は m=11 方向すべてのウェッジ(肩リングの隣接2点+
    apex_v の細い扇形三角形)が **同じ apex_v 1点を共有**している。その1点に
    「apex の u」を1つだけ書くと、周方向に大きく離れたウェッジ(肩側の u が
    0.7 のものなど)まで無理やりその1値へ収束させることになり、細長いスリバー
    三角形ごとに強い引き伸ばし=放射状の縞が出る。これは円筒投影に変えても
    平面投影のままでも変わらない、**頂点属性でコーンの頂点を扱う限り原理的に
    避けられない**問題だった。
  ⭕ **正しい対処**: UV は本来「頂点」ではなく「ループ(面の角)」の値 —
    同じ apex_v でもウェッジ(面)ごとに別の UV を持てる(コーンの頂点をUV展開する
    ときの標準的な扱い)。`gen_stone` が割れ面の三角形をまだ細分・bevel する前
    (辺の対応が単純なうち)に、ウェッジごと直接ループへ書き込む: 土台2点は側面と
    全く同じ式(uparam×back_len×DENS_U / vparam×DENS_V。vparam はボディ・肩リングで
    z そのもの=側面の v と連続、apex では「肩リング平均→apex の実距離(斜面長)」を
    z に足した値)、apex 側の角だけ**そのウェッジの土台2点の生値(pingpong で
    畳む前)の平均**にする(局所的で暴れない・側面と連続)。以後(細分・bevel・
    `assign_uv` の一括処理)は**この面をタグで見分けて一切上書きしない**
    (`_is_head_face` — 頂点タグ `is_head_v` の事後判定。全頂点が頭タグの面は
    早期UV済みとみなす)。埋設される底のファンは元から問題が出ていないので
    手を付けていない(z≈0 で判定し常に (x,y) 平面投影のまま)。詳細は `gen_stone`
    のファン生成部と `assign_uv` 本体のコメント参照。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM

OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa")
SHOT = os.path.join(V.REPO, "Screenshots")

NMR = os.path.join(V.REPO, "Assets", "NatureManufacture Assets",
                    "Meadow Environment Dynamic Nature", "Rocks", "Rocks", "Models")
NMR_TEX = os.path.join(NMR, "Textures", "T_Photoscanned_rocks_01_BC.tga")
NMR_NRM = os.path.join(NMR, "Textures", "T_Photoscanned_rocks_01_N.tga")
ROCK_MAT = "M_photoscanned_rocks_01"

# ⚠⚠ **最初は Rock_04 の UV バウンズをそのまま矩形に使ったが、これは NG だった。**
#   写真計測のアトラスは 1個体=1枚の単純な矩形ではなく、**個体ごとの不定形 UV アイランドを
#   隙間なく敷き詰めた上に、境界をぼかし止めする放射状の「パディング」を焼いてある**
#   (`T_Photoscanned_rocks_01_BC.tga` を直に開いて確認 — 各岩の周りに縞状のストライプが
#   埋め尽くしている)。個体の bounding box をそのまま矩形として使うと、四隅がこのパディング
#   (隣の個体の切れ端や無関係な縞)に掛かり、**同じ面の中で無関係な絵柄へワープする**ため、
#   前面が万華鏡のように破綻した(2026-09-06 に実見。`docs` 相当のスクリーンショットは
#   `/tmp/rock_atlas_preview.png` / `/tmp/crop1.png` に残る)。
#   ⭕ **岩1個体の内側だけを見て、パディングに掛からない矩形を手で選び直した**
#   (画素 (510,1330)-(1210,1930)、4096角。周囲の縞と接しない安全な内側)。
#   密度はテクスチャの解像度と Rock_04 実測(1962px/1.333m 相当)から
#   概算 1250px/m として、この矩形の一辺 700px ≒ 0.56m とみなした。
RECT = (510.0 / 4096, 1.0 - 1930.0 / 4096, 1210.0 / 4096, 1.0 - 1330.0 / 4096)
DENS_U = DENS_V = DENS_P = 0.30           # [uv/m]。矩形がほぼ正方形なので等方に統一

# 仕様(Unity座標: W(X)×D(Z)×H(Y))。ユーザー裁定3=A の寸法どおり。
SPEC = {
    "S": (0.60, 0.45, 1.00),
    "M": (0.70, 0.50, 1.40),
    "L": (0.80, 0.60, 2.10),
}
N_BACK = 10     # 断面の粗いポリゴン数(前面2隅を含め m=N_BACK+1 頂点)
K_BANDS = 6     # 高さ方向の粗いバンド数
SUBDIV_CUTS = 2  # 側面を (SUBDIV_CUTS+1)^2 に細分

# ================================================================ 2026-09-06 差し戻し対応
# 普請奉行から「9本の輪郭がほぼ同じ角柱に見える(庭の立石でなく柵柱)」と差し戻された。
# ⛔ 一定の先細り + 水平な天端を全数に当てない。**個体ごとに姿を変える。**
# `variant`(1/2/3)から下の3姿へ機械的に振り分ける(同じ姿が同じ番号に集まると
# サイズを跨いだ比較がしやすい)。
#   ・atama … 上半分が一方向へ張り出して傾く「頭の重い石」(⛔ 左右対称のくびれでは作らない —
#     2026-09-06 第2次差し戻し。最初の版は anchors だけでくびれ→張りを作ったので、どの向きから
#     見ても同じ「壺」の形になった。正しくは腰をほぼ真っ直ぐに保ち、**片側だけに**上半分の
#     質量と重心を寄せる)
#   ・kata  … 片側だけに肩が出る非対称の石
#   ・hosori… 上へ細り天端が斜めに大きく落ちる石
# `anchors` は (高さ比 t, 半径倍率) の折れ線 — 断面全体をこの倍率で縮尺する(先細りの
# 「垂直方向」の姿はここで決まる。左右対称の変形なので、非対称にしたい特徴はここに書かない)。
# `shoulder` は「片側だけ」を膨らませる非対称項(t0..t1 の高さ域 × 断面の t(=i/N_BACK) が
# f_lo..f_hi の範囲だけを膨らませる — 反対側や全周には掛からない)。
# `lean_profile` は重心のずれ方(lean_shape 参照)。"top" は下を真っ直ぐに残したまま
# 上半分だけを片側へ寄せる(= 頭でっかちの「傾き」)。既定 "linear" は全高で比例。
PROFILES = {
    "atama": dict(
        anchors=[(0.00, 0.92), (0.50, 0.96), (1.00, 1.05)],   # ほぼ真っ直ぐ(左右対称のくびれを作らない)
        shoulder=dict(t0=0.42, t1=1.00, f_lo=0.05, f_hi=0.95, amt=0.34),  # 上半分をまるごと片側へ
        tilt_mul=1.0, lean_profile="top", lean_scale=2.2),
    "kata": dict(
        anchors=[(0.00, 0.92), (0.50, 0.78), (1.00, 0.85)],
        shoulder=dict(t0=0.32, t1=0.80, f_lo=0.15, f_hi=0.55, amt=0.42),
        tilt_mul=1.1, lean_profile="linear", lean_scale=1.0),
    "hosori": dict(
        anchors=[(0.00, 1.00), (0.60, 0.74), (1.00, 0.48)],
        shoulder=None, tilt_mul=2.0, lean_profile="linear", lean_scale=1.0),
}
PROFILE_BY_VARIANT = {1: "atama", 2: "kata", 3: "hosori"}

# ================================================================ 2026-09-06 第4次差し戻し
# 「長さは良いが、上端が水平面でスパッと切られたように見える」— 天端の輪郭が一周
# はっきり残っていたのが原因(旧: ほぼ水平な天端リング+その上に2〜3枚のほぼ平らな
# 小面)。⭕ 頭を「割れて落ちた岩の肩」に作り替える — 単一の頂点(見付の後ろ寄り・
# 中心から外す)へ、勾配のついた割れ面 3〜5 枚が不均等に落ちる形にする(下の
# gen_stone 内、肩リング(shoulder_ring)+単一 apex のファンを参照)。
# `HEAD_FRAC` = 頭の高さ配分(1 − 肩の高さ比。大きいほど割れ面が大きい・急)、
# `HEAD_APEX_OFFSET` = 頂点を中心からどれだけ外すか(w に対する比率)。
# atama(頭が重い)は両方大きく、hosori(先細り)は両方小さく(⛔ それでも頂点は
# 必ず vertex bevel で3〜5cm丸める — 尖らせすぎない)。
# ⭐ 2026-09-06 第5次差し戻し「頭が尖りすぎ・鮫の背びれ」— 前回は頭の高さ配分・
# 傾きの上限が過大で、勾配30〜50°・長い直線の稜・針のような頂になった。
# ここを半分程度に絞り、勾配10〜25°・丸く鈍い肩を狙う(下の gen_stone 参照)。
HEAD_FRAC = {"atama": (0.07, 0.11), "kata": (0.055, 0.085), "hosori": (0.04, 0.065)}
HEAD_APEX_OFFSET = {"atama": (0.10, 0.17), "kata": (0.08, 0.13), "hosori": (0.04, 0.08)}


def scale_at(t, anchors):
    """`anchors`(t昇順の (t, 倍率) 折れ線)を線形補間する。プロファイルの垂直方向の姿を作る。"""
    if t <= anchors[0][0]:
        return anchors[0][1]
    for k in range(len(anchors) - 1):
        t0, s0 = anchors[k]; t1, s1 = anchors[k + 1]
        if t <= t1:
            f = (t - t0) / max(t1 - t0, 1e-9)
            return s0 + (s1 - s0) * f
    return anchors[-1][1]


def lean_shape(t, kind):
    """重心のずれ(0..1)を高さ比 t の関数で返す。
    ・"linear" … 全高で比例(裾から少しずつ傾く)。
    ・"top" … t<0.35 は 0(腰は真っ直ぐ)、0.35〜1.0 で smoothstep しながら 1 へ
      (上半分だけが片側へ寄る「頭でっかち」の傾き。裾に対称なくびれを作らない代わりに、
      ここで非対称な重心移動を作る)。"""
    if kind == "top":
        t0, t1 = 0.35, 1.0
        if t <= t0:
            return 0.0
        if t >= t1:
            return 1.0
        f = (t - t0) / (t1 - t0)
        return f * f * (3.0 - 2.0 * f)
    return t


def pingpong(x):
    x = x % 2.0
    return x if x <= 1.0 else 2.0 - x


def _footprint_xy(rng, w, d, ridge_jit, scale, band_noise, tfrac, profile,
                   ridge_features, belly_freq, belly_phase, lean_dx):
    """1バンドぶんの断面。前面2隅(index 0, -1)は x だけ僅かに振り(直線は保つ)、
    残りは不等角度の円弧+固定の稜ジッタ+バンドごとの小さな追いノイズ+下の3つを重ねる:
    ・**斜めの稜/溝**(`ridge_features`)— 高さで中心indexが動くので割れ肌の稜が斜めに走る
    ・**腹と腰**(`belly_freq/phase`)— 周方向の低周波なうねり(角柱に見えない不整形断面)
    ・**片側の肩**(`profile["shoulder"]`)— kata プロファイルだけ。反対側には掛けない
    ・**重心のずれ**(`lean_dx`)— 全点を同じだけ x へ寄せる(僅かに傾いて立つ石)。
      前面の奥行き位置(y)には触れないので前面の平面性は壊れない。"""
    half_fw = w * 0.42 * scale
    # ⚠ **front_y は scale を掛けない(バンドが変わっても一定)。** 掛けてしまうと
    #   「見付」が奥へ後退しながら先細るタル型になり、平面でなくなる(is_front の法線判定が
    #   細分後にバラつき、面ごとに違う UV 式が当たって織り目が破綻した — 2026-09-06 に実見)。
    #   ⭕ 幅(x)だけ先細らせ、奥行き位置(y)は全バンドで固定して**真っ平らな鉛直面**を保つ。
    front_y = -d * 0.5
    rx = w * 0.56 * scale
    ry = d * 0.60 * scale
    shoulder = profile.get("shoulder")
    pts = [(half_fw * (1.0 + rng.uniform(-0.02, 0.02)) + lean_dx, front_y)]
    a0 = math.atan2(front_y, half_fw)
    a1 = math.atan2(front_y, -half_fw) + 2.0 * math.pi
    for i in range(1, N_BACK):
        t = i / float(N_BACK)
        a = a0 + (a1 - a0) * t
        rj = (1.0 + ridge_jit[i]) * (1.0 + rng.uniform(-band_noise, band_noise))
        # 腹と腰: 周方向の低周波なうねり(高さに依らず一定 — 側面ぜんぶが同じ相)
        rj *= (1.0 + 0.12 * math.sin(belly_freq * a + belly_phase))
        # 斜めの稜/溝: 高さで中心indexが動く局所ふくらみ(+)/くぼみ(-)
        for feat in ridge_features:
            center = feat["idx0"] + feat["drift"] * tfrac
            wgt = math.exp(-((i - center) ** 2) / (2.0 * feat["sigma"] ** 2))
            rj *= (1.0 + feat["amp"] * wgt)
        # 片側の肩(kata のみ)。高さ域(t0..t1)× 断面位置(f_lo..f_hi)の内側だけ膨らむ
        if shoulder is not None and shoulder["t0"] <= tfrac <= shoulder["t1"] \
                and shoulder["f_lo"] <= t <= shoulder["f_hi"]:
            tw = math.sin(math.pi * (tfrac - shoulder["t0"]) /
                          max(shoulder["t1"] - shoulder["t0"], 1e-6))
            iw = math.sin(math.pi * (t - shoulder["f_lo"]) /
                          max(shoulder["f_hi"] - shoulder["f_lo"], 1e-6))
            rj *= (1.0 + shoulder["amt"] * tw * iw)
        x = math.cos(a) * rx * rj + lean_dx
        y = math.sin(a) * ry * rj
        y = max(y, front_y * 0.92)     # 裏側が前面より内側へ回り込みすぎないよう抑える
        pts.append((x, y))
    pts.append((-half_fw * (1.0 + rng.uniform(-0.02, 0.02)) + lean_dx, front_y))
    return pts


def gen_stone(seed, w, d, h, profile_name="atama"):
    """粗いロフトを作って bmesh へ積む。頂点はバンド×リングで共有(Decimateが効くように)。
    戻り値: (bm, m, rng, side_edges, uparam_layer, back_len, is_cap_layer, is_apex_layer,
    is_head_v_layer, vparam_layer, uv_layer, uv_ready_layer, ou, ov)。
    `side_edges` = 側面(前面含む)だけの辺リスト — 天端・底のファンは細分の対象から外すため
    ここで(ファンを足す前に)確定させて返す。
    `vparam_layer`/`uv_layer`/`uv_ready_layer`/`ou`/`ov` は 2026-09-06 UV直しで追加
    (モジュール docstring 参照)。
    `vparam` は側面の v(=z)をそのまま頭の割れ面まで滑らかに延長するための頂点レイヤー。
    `uv_layer` はここで前倒しに作る — **頭の割れ面(shoulder_ring→apex_v のファン)の
    UV はここ(まだ細分・bevel前)で確定させて返す**(理由は下のファン生成部のコメント参照)。
    `uv_ready_layer` はその早期UV済みループだけを示すループレイヤー(`assign_uv` が
    上書きを避けるのに使う。面単位の `is_head_v` では境界の誤爆で真っ暗な帯が出た
    実例あり — uv_layer 作成部のコメント参照)。
    `ou`/`ov` はこの石ぶんの矩形内オフセット(`assign_uv` が従来 `rng` から都度引いていたが、
    ファンの早期UVと後段の一括UVで同じ値を共有する必要があるため、ここで一度だけ確定させる)。"""
    rng = random.Random(seed)
    # ⭐ 2026-09-06 UV直し: UVの矩形内オフセットは形を作る `rng` とは別系統の乱数から引く
    #   (`rng` から引くと、この呼び出しを追加した分だけ以降のノイズ・bevel の乱数列が
    #   ずれて既存の石の姿が変わってしまう — 規約「形には触らない」に反する)。
    uv_rng = random.Random(seed ^ 0xA5F00D)
    ou = 0.5 + uv_rng.uniform(-0.10, 0.10)
    ov = 0.5 + uv_rng.uniform(-0.10, 0.10)
    profile = PROFILES[profile_name]
    m = N_BACK + 1
    ridge_jit = [0.0] * m
    for i in range(1, N_BACK):
        ridge_jit[i] = rng.uniform(-0.20, 0.20)

    # 斜めの稜/溝(2〜3本)。`idx0` は高さ0での断面index、`drift` は天端までに何index分
    # 位置がずれるか(= 斜めに走る)、`amp` は+で稜(ふくらみ)/−で溝(くぼみ)。
    n_ridges = rng.choice([2, 3])
    ridge_features = []
    for _ in range(n_ridges):
        ridge_features.append(dict(
            idx0=rng.uniform(1.0, N_BACK - 1.0),
            drift=rng.uniform(-3.0, 3.0),
            amp=rng.choice([1, -1]) * rng.uniform(0.14, 0.26),
            sigma=rng.uniform(0.6, 1.1),
        ))
    # 腹と腰(周方向の低周波なうねり。高さに依らず一定の位相 — 正多角形に見えないように)
    belly_freq = rng.choice([2.0, 2.5, 3.0])
    belly_phase = rng.uniform(0, 2 * math.pi)
    # 重心のずれ(5〜10%×プロファイルの lean_scale。僅かに傾いて立つ石)。
    # 前面の奥行き(y)には触れないので、どれだけずらしても前面の平面性は保たれる
    # (y=front_y 一定の平面は x がどう動いても平面のまま)。
    lean_total = rng.uniform(0.05, 0.10) * w * profile.get("lean_scale", 1.0) * rng.choice([-1, 1])
    lean_kind = profile.get("lean_profile", "linear")

    bm = bmesh.new()
    uparam = bm.verts.layers.float.new("uparam")
    # ⭐ 2026-09-06 UV直し: 側面の v(=z)を頭の割れ面までそのまま延長するための頂点レイヤー。
    #   ボディ・肩リングでは z と同じ値を入れる(側面の v 式 `co.z * DENS_V` と完全一致 =
    #   境界で継ぎ目が出ない)。頭の割れ面(apex_v)だけは下で z に「肩リング平均→apex の
    #   実距離(斜面長)」を足した値を入れる — uparam と同じく細分・bevel でも位置と一緒に
    #   線形補間されるので、割れ面の途中の頂点も自然に中間値を持つ。
    vparam = bm.verts.layers.float.new("vparam")
    # ⭐ 2026-09-06 UV直し: uv_layer もここ(細分・bevel より前)で作る。頭の割れ面
    #   (ファン)の UV は下で細分前に直接書き込むので、レイヤー自体を先に用意しておく必要がある。
    uv_layer = bm.loops.layers.uv.new("UVMap")
    # ⛔⛔ **1回失敗した実装**: 「早期UV済みの面は `is_head_v`(頂点タグ)が全頂点1なら
    #   スキップ」という**面単位**の判定を最初に書いたが、これは事故った ——
    #   `is_head_v` は頂点タグなので、細分で生まれる「ボディ最上段リング(is_head_v=0)
    #   ↔ 肩リング(is_head_v=1)」境界の**新しい頂点**の値は整数レイヤーの補間で
    #   ちょうど0/1の境目に落ちることがあり、そこに接する子クアッドが誤って
    #   「全頂点 is_head_v=1」= 頭面と判定されてしまう。その子クアッドは早期UVを
    #   実際には書いていない(早期に書いたのは扇形の割れ面3頂点のループだけ)ため、
    #   スキップした結果 UV が bmesh の既定値 (0,0) のまま残り、そこだけ真っ暗な
    #   帯としてレンダに出た(2026-09-06 に実見 — `tateishi_L_2_elev.png` に肩の
    #   高さでべったり黒い帯)。
    # ⭕ **面単位でなくループ単位**で「早期UV済みか」を持つ — 下のファン生成部で
    #   実際に書き込んだ3ループにだけ `uv_ready=1` を立てる専用レイヤー。UV 自体と
    #   同じ loop カスタムデータなので、細分・bevel でも UV と全く同じ経路で
    #   一緒に補間される(= UV が正しく運ばれるなら uv_ready も正しく運ばれる)。
    #   境界を挟むクアッドの「触っていない方のループ」は uv_ready=0 のまま保たれるので、
    #   誤って早期UV済み扱いされることがない。
    uv_ready = bm.loops.layers.float.new("uv_ready")
    # ⚠⚠ **天端・底の判定は面の法線(閾値)ではなく、作った時点のタグで持つ。**
    #   hosori(強い先細り)で天端が非常に狭くなると、多面天端の各小面の法線が乱れて
    #   閾値 0.85 を割り込み、UV が側面(円周)の式へ誤って落ちてジグザグに破綻した
    #   (2026-09-06 に実見)。⭕ 天端・底のファンは細分もされない一枚物なので、
    #   作った瞬間にタグを付ければ以後ずっと正しい(法線の揺れに影響されない)。
    is_cap = bm.faces.layers.int.new("is_cap")
    # ⭐ 2026-09-06 第3次差し戻し「角が鋭すぎませんか」対応: 天端の各小面はファンの要
    #   (apex)に頂点が1点だけ集まる円錐状の「尖った蓋」になっている。ここを
    #   `round_apex()` で vertex bevel して潰すために、作成時点でタグを付けて後から
    #   拾えるようにする(is_cap と同じ理由 — 法線や位置からの事後判定は当てにならない)。
    is_apex = bm.verts.layers.int.new("is_apex")
    # ⭐⭐ 2026-09-06 第6次差し戻し対応: 「頭の割れ面」を**面のタグ**(is_head)で
    #   持つのをやめ、**頂点のタグ**(is_head_v)に変えた。理由 — 面タグは
    #   `bmesh.ops.subdivide_edges` を通すと新しくできた面へ確実に引き継がれるとは
    #   限らない(検証していない・実際に隣接する側面のクアッドまで is_head=1 に
    #   誤爆させて UV が縞状に破綻した)。⭕ 頂点のカスタムデータは細分で**位置と
    #   一緒に確実に線形補間される**(この事実は `uparam` で既に使っている・
    #   README の踏んだ落とし穴にも既出)。面が「頭」かどうかは、その面の頂点が
    #   **全部** is_head_v なら頭、という事後判定にする(`_is_head_face` 関数)。
    is_head_v = bm.verts.layers.int.new("is_head_v")
    # ⚠ **u の巻き戻し(1.0→0.0)を前面の上に置かない。**周方向の並びは
    #   [前面右, 背弧…, 前面左] なので、そのまま index/m を u にすると継ぎ目が
    #   一番目立つ前面の真上に来る。**中心を背側へ回して**継ぎ目を裏へ逃がす。
    mid = m // 2
    uparam_of = [((i - mid) % m) / float(m) for i in range(m)]
    # 背弧の実長のおおよその見積り(UV密度の基準。前面・天端・底は別に平面投影するので使わない)
    back_len = math.pi * (w * 0.56 + d * 0.60) * ((N_BACK - 1) / float(N_BACK))

    # ⭐⭐ 2026-09-06 第6次差し戻し対応: 「頭の面のテクスチャが縦に伸びる」の
    #   再発の原因は UV 式ではなく**ジオメトリの側にあった**。ボディ最上段(旧
    #   BODY_MAX=0.55〜0.65 固定)と肩リング(tfrac_sh=0.85〜0.96)の間に、
    #   通常のバンド間隔(≒0.6/(K_BANDS-1)≈0.12)の**2倍以上ある巨大な1バンド**
    #   ができていて、そのバンドだけ他のバンドと同じ細分数(SUBDIV_CUTS)しか
    #   受けないため、そこだけテクスチャ密度が薄く=間延びして見えた(flat gray の
    #   デバッグで幾何形状は綺麗でも、テクスチャ版だけ縞に見えた理由はこれ)。
    #   ⭕ **先に肩の高さ(tfrac_sh)を決め**、そこから通常バンドと同じ間隔になる
    #   よう BODY_MAX を逆算する(移行バンドを「特大の1枚」にしない)。
    head_frac = rng.uniform(*HEAD_FRAC.get(profile_name, (0.12, 0.18)))
    tfrac_sh = 1.0 - head_frac
    BODY_MAX = tfrac_sh * (K_BANDS - 1) / K_BANDS if K_BANDS > 1 else 0.0

    # 体(ボディ): 裾から肩の下まで。ボディは h 全域ではなく BODY_MAX までに圧縮し、
    #   その上に肩(shoulder_ring)と割れ面の頭を別枠で足す(天端が水平リングで
    #   一周閉じる旧作りをやめるため)。
    rings = []   # rings[band] = [BMVert,...]（m個）
    for b in range(K_BANDS):
        tfrac = (b / float(K_BANDS - 1)) * BODY_MAX if K_BANDS > 1 else 0.0
        z = h * tfrac
        # ⭐ 2026-09-06: 一律の「先細り」をやめ、プロファイル(atama/kata/hosori)の
        #   折れ線から縮尺を取る — ①頭でっかち ②非対称な肩 ③強い先細り、で輪郭を変える。
        scale = scale_at(tfrac, profile["anchors"])
        band_noise = 0.0 if b == 0 else 0.05
        lean_dx = lean_total * lean_shape(tfrac, lean_kind)
        pts = _footprint_xy(rng, w, d, ridge_jit, scale, band_noise, tfrac, profile,
                             ridge_features, belly_freq, belly_phase, lean_dx)
        ring = []
        for i, (x, y) in enumerate(pts):
            v = bm.verts.new((x, y, z))
            v[uparam] = uparam_of[i]
            v[vparam] = z
            ring.append(v)
        rings.append(ring)

    # ⭐⭐ 肩リング(shoulder_ring) = 割れた頭が始まる境界。**水平には作らない**:
    #   ①前後左右へ傾ける(見付の上端が斜め/山形になる — 個体ごとに tilt_dir で
    #     左右が変わる)②1〜2箇所を側面へ5〜15cm食い込ませる(割れ面の段。前面の
    #     2隅=index 0,m-1 は避ける — 前面の平面性を壊さないため)。
    scale_sh = scale_at(tfrac_sh, profile["anchors"])
    lean_dx_sh = lean_total * lean_shape(tfrac_sh, lean_kind)
    pts_sh = _footprint_xy(rng, w, d, ridge_jit, scale_sh, 0.05, tfrac_sh, profile,
                            ridge_features, belly_freq, belly_phase, lean_dx_sh)
    # ⭐ 2026-09-06 第5次差し戻し「頭が尖りすぎ・鮫の背びれ」対応: 前回は
    #   `tilt = 0.10〜0.20*h*tilt_mul`(tilt_mul は hosori で2.0)を x/half_fw_ref に
    #   掛ける式だったため、前面2隅の高低差が全高の最大67%まで暴れ、HEAD_FRAC の
    #   高さ予算をはみ出して急勾配・直線的な稜になっていた。⭕ **前面2隅の高低差を
    #   直接の目標値(全高の5〜12%)として決め打ちし**、そこから逆算して傾きの
    #   係数を出す(tilt_mul には依存しない — 暴走の原因だったので外した)。
    corner_diff = rng.uniform(0.05, 0.12) * h
    bite_specs = []
    for _ in range(rng.choice([1, 1, 2])):
        width = rng.choice([2, 3])
        hi = max(1, m - 2 - width)
        start = rng.randint(1, hi) if hi >= 1 else 1
        bite_specs.append((start, width, rng.uniform(0.04, 0.10)))
    bite_dz = [0.0] * m
    pts_sh = list(pts_sh)
    for start, width, amt in bite_specs:
        for k in range(width):
            idx = start + k
            if idx <= 0 or idx >= m - 1:
                continue
            x, y = pts_sh[idx]
            r = math.hypot(x, y) or 1.0
            f = max(0.3, 1.0 - amt / r)
            pts_sh[idx] = (x * f, y * f)
            # ⚠ 2026-09-06 第6次差し戻し対応: z の食い込みを強くしすぎると、この
            #   食い込み点と隣の食い込んでいない点を結ぶ遷移バンドの四角形が
            #   異様に縦長になり、そこだけテクスチャの縦密度が違って見える縞の
            #   原因になった(BODY_MAX を揃えても残った・実見で特定)。
            #   ⭕ z の食い込みは控えめにし、主に半径方向の食い込み(段差の見え方)
            #   で表現する。
            bite_dz[idx] += amt * rng.uniform(0.10, 0.25)

    tilt_dir = rng.choice([-1, 1])
    half_fw_ref = max(w * 0.5, 1e-6)
    z_body_top = rings[-1][0].co.z
    shoulder_ring = []
    for i, (x, y) in enumerate(pts_sh):
        # x=±half_fw_ref で ±corner_diff/2 になるよう線形勾配を掛ける(プロファイルの
        # tilt_mul には依存しない — 全個体で「全高の5〜12%」という絶対量を守るため)。
        z = h * tfrac_sh + tilt_dir * (corner_diff * 0.5) * (x / half_fw_ref) - bite_dz[i]
        z = max(z, z_body_top + h * 0.015)   # ボディ最上段より必ず高く保つ(逆転防止)
        v = bm.verts.new((x, y, z))
        v[uparam] = uparam_of[i]
        v[vparam] = z    # 肩リングも z そのまま(側面の v と連続)
        v[is_head_v] = 1
        shoulder_ring.append(v)
    rings.append(shoulder_ring)
    bm.verts.ensure_lookup_table()

    # 頭の頂点(単一)。「見付の後ろ寄り・中心から外す」— 前面は front_y<0 なので
    # +y が背側。プロファイルごとに HEAD_APEX_OFFSET で外す量を変える(atama=やや
    # 大きく/hosori=控えめ)。⭐ 頂点自体は後段の round_apex で**握りこぶし大**
    # (8〜15cm/L・5〜10cm/S)に丸めるので、ここでの外し量は控えめにして
    # 「勾配10〜25°の鈍い肩」の枠に収める(前回の暴走の反省 — 頭の形の派手さは
    # HEAD_FRAC/APEX_OFFSET でなく round_apex の丸め半径と割れ面のノイズで出す)。
    apex_side = rng.choice([-1, 1])
    off_lo, off_hi = HEAD_APEX_OFFSET.get(profile_name, (0.08, 0.13))
    apex_dx = apex_side * rng.uniform(off_lo, off_hi) * w
    apex_dy = rng.uniform(0.08, 0.20) * d
    apex_z = h * tfrac_sh + head_frac * h * rng.uniform(0.5, 0.9)  # 肩よりは高いが h には届かせない
    apex_v = bm.verts.new((apex_dx, apex_dy, apex_z))
    apex_pos = Vector((apex_dx, apex_dy, apex_z))   # 斜面長の計算だけに使う局所変数(戻り値には含めない)
    apex_v[uparam] = 0.0
    apex_v[is_apex] = 1
    apex_v[is_head_v] = 1
    # 2026-09-06 UV直し: v は「肩リングの平均位置→apex の実距離(斜面長)」を z に足す。
    #   肩リング側は vparam==z なので、この式は境界でちょうど連続になる(肩リング平均の
    #   vparam ≒ その平均 z に一致し、そこへ斜面長を足しただけ)。
    shoulder_avg = Vector((0.0, 0.0, 0.0))
    for sv in shoulder_ring:
        shoulder_avg += sv.co
    shoulder_avg /= max(len(shoulder_ring), 1)
    slope_len = (apex_pos - shoulder_avg).length
    apex_v[vparam] = shoulder_avg.z + slope_len

    # 側面: バンド間を四角形でつなぐ(前面の辺も含め m 枚/バンド)。肩リングも
    # rings の最後の要素として同じ扱いで繋がるので、①肩の傾き ②食い込みの段は
    # ここで自動的に側面の凹凸として現れる(特別扱いのコードは要らない)。
    for b in range(len(rings) - 1):
        r0, r1 = rings[b], rings[b + 1]
        for i in range(m - 1):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
        # 前面(m-1 → 0 を結ぶ最後の辺)
        bm.faces.new((r0[m - 1], r0[0], r1[0], r1[m - 1]))

    # ⭐⭐ 2026-09-06 第4次差し戻し: 天端は「水平リング+ほぼ平らな小面」をやめ、
    #   **肩リング(shoulder_ring)から単一の頭頂点(apex_v)へ落ちる 3〜5 枚の割れ面**
    #   にする。肩リング自体が①傾き②食い込みで既に不揃いな高さを持つうえ、apex が
    #   中心から外れているので、分割された弧ごとに勾配が自然にばらつく。
    top = shoulder_ring
    n_facets = rng.choice([3, 4, 5])
    # ⚠ m=11 に対し最大5分割なので、旧来の "max(3, m//(n_facets*2))" は満たせない
    #   (5分割だと平均間隔2.2)。最小間隔は 2 まで緩める。
    splits = sorted(rng.sample(range(m), min(n_facets, m)))
    for _try in range(20):
        splits = sorted(rng.sample(range(m), min(n_facets, m)))
        gaps = [(splits[(k + 1) % len(splits)] - splits[k]) % m for k in range(len(splits))]
        if min(gaps) >= 2:
            break
    for k in range(len(splits)):
        a_idx, b_idx = splits[k], splits[(k + 1) % len(splits)]
        arc = [a_idx]
        i = a_idx
        while i != b_idx:
            i = (i + 1) % m
            arc.append(i)
        if len(arc) < 2:
            continue
        for t in range(len(arc) - 1):
            va, vb = top[arc[t]], top[arc[t + 1]]
            f = bm.faces.new((va, vb, apex_v))
            f[is_cap] = 1
            # ⭐⭐ 2026-09-06 UV直し(頭の帯の縦縞・放射状の引き伸ばし)。
            #   apex_v は m=11 方向すべてのウェッジから共有される**単一の頂点**なので、
            #   頂点レイヤー(uparam/vparam)に「apex の u」を1つだけ書いても、周方向に
            #   大きく離れた肩リング点(例 u=0.7)まで無理やりその1値へ収束させることになり、
            #   細長いスリバー三角形ごとに強烈な引き伸ばし=放射状の縞が出る
            #   (2026-09-06 に実見 — cylindrical化しても解消しなかった)。
            #   ⭕ **UV はループ(面の角)ごとの値**なので、同じ apex_v でもウェッジごとに
            #   別の値を持たせられる(コーンの頂点をUV展開する標準的な手当て)。
            #   ここで**まだ細分・bevel 前**(辺が長く、ウェッジの対応が単純)のうちに
            #   直接書き込む — 土台2点は側面と全く同じ式(uparam×back_len×DENS_U /
            #   vparam×DENS_V)、apex 側の角だけ「このウェッジの土台2点の生値の平均」
            #   にする(= 側面と連続かつウェッジごとに局所的で暴れない)。
            #   ⚠ 平均は **pingpong で畳む前の生値**で取る — 畳んだ後の値を平均すると、
            #   畳み目(整数境界)をまたぐウェッジで壊れる。
            raw_ua = va[uparam] * back_len * DENS_U
            raw_ub = vb[uparam] * back_len * DENS_U
            raw_pv_a = va[vparam] * DENS_V + ov * 0.3
            raw_pv_b = vb[vparam] * DENS_V + ov * 0.3
            raw_uc = (raw_ua + raw_ub) * 0.5
            raw_vc = apex_v[vparam] * DENS_V + ov * 0.3   # 高さは全ウェッジ共通でよい(周方向ほど暴れない)
            f.loops[0][uv_layer].uv = (RECT[0] + pingpong(raw_ua) * (RECT[2] - RECT[0]),
                                        RECT[1] + pingpong(raw_pv_a) * (RECT[3] - RECT[1]))
            f.loops[1][uv_layer].uv = (RECT[0] + pingpong(raw_ub) * (RECT[2] - RECT[0]),
                                        RECT[1] + pingpong(raw_pv_b) * (RECT[3] - RECT[1]))
            f.loops[2][uv_layer].uv = (RECT[0] + pingpong(raw_uc) * (RECT[2] - RECT[0]),
                                        RECT[1] + pingpong(raw_vc) * (RECT[3] - RECT[1]))
            # この3ループだけ「早期UV済み」を立てる(assign_uv 側はループ単位でこれを見て
            # 上書きを避ける — 面単位の is_head_v タグに頼らない理由は uv_layer 作成部の注記参照)。
            f.loops[0][uv_ready] = 1.0
            f.loops[1][uv_ready] = 1.0
            f.loops[2][uv_ready] = 1.0

    # ⭐⭐ 2026-09-06 第6次差し戻し対応: **round_apex(頂点の丸め)はここ**(割れ面を
    #   作ってapex_vが実際に辺を持った直後・まだ細分前)でやる。
    #   ⛔⛔ **前の版はここより前(apex_v作成の直後、まだ割れ面=辺が1本も無い状態)
    #   で呼んでいた。孤立した頂点(辺0本)を bevel しても何も起きない**ので、
    #   実質何も丸まっておらず、フラットシェーディングで見た実際のジオメトリは
    #   依然として細長い薄片(スリバー)だらけの「鮫の背びれ」のまま残っていた
    #   (テクスチャの「縦縞」に見えていたのは UV の不具合ではなく、この薄片群が
    #   板状に反射する陰影そのものだった — flat gray のデバッグレンダで実見して
    #   ようやく判明した)。⭕ **割れ面(=apex への辺)を作った直後、まだ細分前**
    #   (辺が m=11本・どれも0.3〜0.5m級で長い)に呼ぶ。旧説明にあった「細分後は
    #   辺が半分の長さに縮む」問題も併せて回避できる。
    bm.normal_update()
    round_apex(bm, h, rng, is_apex, is_head_v, is_cap)
    bm.normal_update()

    # ⚠ **side_edges はここ(頭の割れ面+round_apex の後)で確定させる** — こうすると
    #   側面と頭の両方の辺が下の1回の subdivide_edges(build_one 側)へまとめて渡り、
    #   境界の辺を二重に細分することがない(第5次差し戻しの版は頭だけ先に別途
    #   細分していたため、境界の辺が既に消費されており、後続の side_edges 経由の
    #   細分が無効な参照を渡すことになっていた — is_head の誤爆と縞模様の根本原因)。
    side_edges = list(bm.edges)   # ⚠ 側面+頭の割れ面。底のファンを足す前に確定させる

    # 底(バンド0・z=0固定・ノイズ無し)。中心ファンで閉じる(埋設側なので単純な1点でよい)。
    bc = bm.verts.new((0.0, -d * 0.05, 0.0))
    bc[uparam] = 0.0
    bc[vparam] = 0.0
    for i in range(m):
        j = (i + 1) % m
        f = bm.faces.new((rings[0][j], rings[0][i], bc))
        f[is_cap] = 1

    bm.normal_update()
    return bm, m, rng, side_edges, uparam, back_len, is_cap, is_apex, is_head_v, vparam, uv_layer, uv_ready, ou, ov


def ensure_outward(bm):
    """符号付き体積で外向きを判定し、負なら全面裏返す(build_okabe_niwa._cut_z と同じ考え方)。"""
    vol = 0.0
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for k in range(1, len(vs) - 1):
            a, b, c = vs[0], vs[k], vs[k + 1]
            vol += a.dot(b.cross(c)) / 6.0
    if vol < 0.0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])


def add_crack_noise(bm, w, d, h, rng, is_head_v_layer=None, amp_back=0.014, amp_front=0.003):
    """細分後の側面頂点へ、前面以外を強めに・前面は弱めにノイズを掛けて割れ肌を作る。
    底(z≈0)と天端近く(z>0.94h)は触らない — 天端はファンの向き(法線)が
    ノイズで暴れると一部の面だけ裏返り、`ensure_outward` の全体反転では直せない
    (穴が空いたように黒く抜けた。2026-09-06 に実見)。

    ⚠⚠ **前面/側面の境で振幅を急に切り替えない。**しきい値で amp_front→amp_back を
    ハードに切り替えると、見付の縁がまさにそこで「定規で引いた直線」に見える
    (2026-09-06 第2次差し戻し — vs_boulder で指摘された)。⭕ 前面の平面(y=front_y)からの
    距離でなめらかに補間する — 縁のノイズが自然に強まっていくので、直線が視覚的に
    強調されない。

    `is_head_v_layer`(頂点タグ)を渡すと、頭の割れ面の頂点はここでは触らない
    (2026-09-06 第5次差し戻し対応)— `add_head_noise` が別の絶対量(1〜3cm)で
    処理するので、ここの「石のサイズに比例した振幅」で二重に動かさない。"""
    head_verts = set()
    if is_head_v_layer is not None:
        head_verts = {v for v in bm.verts if v[is_head_v_layer]}
    top_guard = h * 0.94
    front_y0 = -d * 0.5
    blend = d * 0.30
    for v in bm.verts:
        if v.co.z < 1e-5 or v.co.z > top_guard:
            continue
        if v in head_verts:
            continue
        t = min(max((v.co.y - front_y0) / blend, 0.0), 1.0)
        amp = amp_front + (amp_back - amp_front) * t
        n = v.normal if v.normal.length > 1e-6 else Vector((0, -1, 0))
        v.co += n * rng.uniform(-amp, amp) * max(w, d, h) * 0.5
        v.co.z += rng.uniform(-amp, amp) * h * 0.3


def add_head_noise(bm, rng, is_head_v_layer, is_apex_layer, amp_lo=0.01, amp_hi=0.03):
    """頭の割れ面(is_head_v タグの頂点)へ**絶対量1〜3cm**の頂点ノイズを掛け、
    長い直線の稜を無くす(2026-09-06 第5次差し戻し item3)。石のサイズに比例
    させない(`add_crack_noise` と違い、L でも S でも同じ「握りこぶしの表面の
    凹凸」に見せたいので絶対値で振る)。round_apex が既に丸めた頂点(is_apex)は
    ここでは対象にしない — 丸めた直後に大きく動かすと bevel で作った丸みの形が
    崩れる。"""
    verts = {v for v in bm.verts if v[is_head_v_layer]}
    for v in verts:
        if v[is_apex_layer]:
            continue
        n = v.normal if v.normal.length > 1e-6 else Vector((0, 0, 1))
        amp = rng.uniform(amp_lo, amp_hi) * rng.choice([-1.0, 1.0])
        v.co += n * amp


def round_edges(bm, h, rng, is_cap_layer, is_head_v_layer, angle_thresh=math.radians(26.0)):
    """すべての凸の稜(見付の縁・側面どうしの粗い facet 境・天端の小面と側面の境)を
    bmesh bevel で丸める。2026-09-06 第3次差し戻し「庭石ですが、角が鋭すぎませんか」
    への対応 — これ以前は `chamfer_front_seam`(前面の2隅の列だけを乱数で振って
    面取りっぽく見せる偽物)を使っていたが、**本物の bevel に差し替えた**
    (新しいセグメントが入るので実際に丸まる。偽の面取りは「定規で引いた縦線」を
    別の直線に置き換えるだけで、第2次差し戻しの原因になっていた)。

    ⛔ **ブーリアンでは丸められない**(README「踏んだ落とし穴」に既出 — ブーリアンは
    重なり合った非マニフォールドのタイル面で EXACT ソルバが「中身が詰まっている」と
    誤判定して型そのものを返す)。同じ理由でここでも使わず、bmesh の edge bevel
    オペレータで直接丸める。

    候補の選び方(このロフトの構造から機械的に決まる):
    ・**cap(天端・底ファン)と非capの境**の辺は、角度によらず必ず対象にする
      — これが「天端の小面の交線」そのもの(天端の小面と、その下の側面が接する輪)。
      ただし **底(z が 0 に近い)は埋設されて見えないので除外する**(item 2)。
    ・残りは隣接2面の法線がなす角が `angle_thresh` を超える辺だけを拾う
      — これが「見付の縁」(前面の平らな1枚と、隣の不等角度な円弧面の境)と
      「側面どうしの粗い facet 境」(= ジャギーに振った円弧の折れ目)。
      細分で生まれた、ほぼ同一平面のなだらかな辺はここで弾かれる — 割れ肌の細かい
      凹凸は `add_crack_noise` に任せ、ここでは触らない(item 3)。

    半径 2〜6cm・セグメント 2〜3 を**稜ごと・高さのバンドごとに揺らす**。
    bmesh の bevel オペレータは1回の呼び出しに半径を1つしか取れないので、辺を
    高さ4バンド×ランダムな小さな束に割って、束ごとに別の半径・セグメント数で
    複数回 bevel する。束をまたいで bevel が隣の頂点を動かすことがあるが
    `edge.is_valid` で毎回生存確認するので安全 — むしろ風化した石の稜は
    場所によって丸みが不揃いなのが自然。"""
    eps_z = h * 0.02
    cand = []
    for e in bm.edges:
        faces = e.link_faces
        if len(faces) != 2:
            continue
        f0, f1 = faces
        cap0 = _is_cap_like(f0, is_cap_layer, is_head_v_layer)
        cap1 = _is_cap_like(f1, is_cap_layer, is_head_v_layer)
        if cap0 and cap1:
            continue   # 同じファンの内部(スポーク) — 丸めない
        z_avg = (e.verts[0].co.z + e.verts[1].co.z) * 0.5
        if cap0 != cap1:
            if z_avg < eps_z:
                continue   # 底の縁は埋まるので不要(item 2)
            cand.append(e)
            continue
        if f0.normal.angle(f1.normal, 0.0) > angle_thresh:
            cand.append(e)
    if not cand:
        return

    rng.shuffle(cand)
    n_bands = 4
    bands = [[] for _ in range(n_bands)]
    for e in cand:
        z_avg = (e.verts[0].co.z + e.verts[1].co.z) * 0.5
        bidx = min(int(z_avg / max(h, 1e-6) * n_bands), n_bands - 1)
        bands[bidx].append(e)

    for band_i, edges_in_band in enumerate(bands):
        if not edges_in_band:
            continue
        n_chunks = max(1, min(4, len(edges_in_band) // 6))
        chunks = [[] for _ in range(n_chunks)]
        for k, e in enumerate(edges_in_band):
            chunks[k % n_chunks].append(e)
        for chunk in chunks:
            live = [e for e in chunk if e.is_valid]
            if not live:
                continue
            radius = rng.uniform(0.02, 0.06)
            segs = rng.choice([2, 3])
            try:
                bmesh.ops.bevel(bm, geom=live, offset=radius, offset_type='OFFSET',
                                 segments=segs, profile=rng.uniform(0.45, 0.60),
                                 affect='EDGES', clamp_overlap=True, loop_slide=True)
            except Exception as exc:
                print("[tateishi] ⚠ bevel skip band=%d n=%d: %s" % (band_i, len(live), exc))


def round_apex(bm, h, rng, is_apex_layer, is_head_v_layer=None, is_cap_layer=None):
    """頭頂点(単一・割れ面が集まる要)を vertex bevel で潰す — **握りこぶし大**
    に丸める(2026-09-06 第5次差し戻し item1「頂は点でなく小さな丸い山」)。
    半径は石の全高 h で線形補間: h=1.0(S)で5〜10cm、h=2.1(L)で8〜15cm
    (前回の 3〜5cm では「まだ尖って見える・鮫の背びれ」と差し戻された)。
    1点に頂点が集まる円錐状の頂は edge bevel では触れない(辺の操作なので、
    頂点1点に収束する角は辺の集合として拾えない)。

    ⚠ **`gen_stone` が細分の前に呼ぶ**(辺がまだ長いうち)。細分後に呼ぶと
    apex に集まる辺が半分の長さに縮んでいて、8〜15cmという半径に対して
    短すぎ、`clamp_overlap` が競合して頂の周りが尖った破片だらけになる
    (2026-09-06 第5次差し戻しで実見・第6次で修正)。

    `is_head_v_layer`/`is_cap_layer` を渡すと、bevel が作った新しい頂点・面へ
    明示的にタグを立て直す — vertex bevel が customdata をどこまで引き継ぐか
    保証されないため(is_apex の頂点は消費されて新しい頂点に置き換わる)。"""
    t = min(max((h - 1.0) / (2.1 - 1.0), 0.0), 1.0)
    lo = 0.05 + (0.08 - 0.05) * t
    hi = 0.10 + (0.15 - 0.10) * t
    verts = [v for v in bm.verts if v[is_apex_layer]]
    for v in verts:
        if not v.is_valid:
            continue
        radius = rng.uniform(lo, hi)
        # ⚠ 2026-09-06 第6次差し戻し・追加修正: 肩リングの食い込み(bite)や傾きで
        #   apex への辺の長さが不揃いになると、一番短い辺だけ極端に短いことがある。
        #   その辺に対して要求半径が長すぎると clamp_overlap が無理に押し込めて、
        #   頂の一部だけ尖った破片が残った(hosori の一部個体で実見)。
        #   ⭕ 実際に繋がっている辺の**最短の長さの45%**も半径の上限にする。
        min_edge = min((e.calc_length() for e in v.link_edges), default=radius)
        radius = min(radius, min_edge * 0.85)
        try:
            res = bmesh.ops.bevel(bm, geom=[v], offset=radius, offset_type='OFFSET',
                                   segments=rng.choice([2, 3]), affect='VERTICES',
                                   clamp_overlap=True)
        except Exception as exc:
            print("[tateishi] ⚠ apex bevel skip: %s" % exc)
            continue
        if is_head_v_layer is None and is_cap_layer is None:
            continue
        new_faces = [el for el in res.get('faces', []) if isinstance(el, bmesh.types.BMFace)]
        for f in new_faces:
            if is_cap_layer is not None:
                f[is_cap_layer] = 1
            if is_head_v_layer is not None:
                for nv in f.verts:
                    nv[is_head_v_layer] = 1


def assign_uv(bm, uv_layer, uparam, back_len, is_cap_layer, is_head_v_layer=None,
              vparam=None, ou=0.5, ov=0.5, uv_ready=None):
    """**早期UV済みのループ(頭の割れ面のファン)以外**へ UV を振る。⚠ 一点貼り禁止
    (規約4) — 全頂点位置から決定論的に計算するので、面積の大きい面でもテクスチャの
    縞が読める。

    ・**早期UV済みのループ**(`uv_ready` レイヤーが立っている — `gen_stone` が
      shoulder_ring→apex_v のファンを作った時点で直接書き込み済み)は**ここでは
      一切触らない**(下の「2026-09-06 UV直し」参照)。
      ⚠⚠ **面単位でなく必ずループ単位で判定する。** 最初は「is_head_v(頂点タグ)が
      全頂点1の面はスキップ」という面単位の判定にしていたが、細分がボディ最上段
      リング↔肩リング境界の新しい頂点へ誤って is_head_v=1 を伝播させることがあり、
      そこに触れる子クアッド(早期UVを実際には持たない)まで巻き込んでスキップして
      しまい、UV が既定値 (0,0) のまま残って真っ暗な帯としてレンダに出た
      (2026-09-06 に実見)。`uv_ready` は uv_layer と全く同じ loop カスタムデータ
      なので、UV 自体が正しく運ばれるところにしか立たない — 誤爆しない。
    ・**前面**(法線が Blender −Y に強く寄る = Unity +Z の見付)… (x, z) の平面投影。
      矩形の平らな面なので、単純な平面投影が一番歪まない。
    ・**底(埋設)**(`is_cap_layer` で作成時にタグ済み・z≈0)… (x, y) の平面投影。
      埋まって見えないので歪みは無視できる。
    ・**それ以外**(背・側の不等な円弧面、および肩リング境界を挟む遷移バンドの
      非頭側の角)… 周方向は `uparam`(頂点ごとに持たせた連続パラメータ。細分・bevel
      でも位置と一緒に線形補間される)× 背弧のおおよその実長、鉛直方向は `vparam`
      (ボディ・肩リングは z そのもの)。どちらも `DENS_U`/`DENS_V`(在庫の岩1体の
      実測密度)を掛ける。`vparam` を渡さない呼び出しには後方互換で `co.z` を使う。
    密度を掛けたあとは `pingpong()` で [0,1] に畳んで矩形へ写す(継ぎ目が出ない)。

    ⚠⚠ **2026-09-06 UV直し(頭の帯の縦縞・放射状の引き伸ばし)**: 以前は「天端・底・
    頭の割れ面」をひとまとめに (x,y) 平面投影していた。頭の割れ面は複数枚が apex 付近の
    狭い (x,y) 範囲へ向かって収束するため、実面積の異なる面が同じ狭い UV 域へ繰り返し
    畳み込まれ、正面近景(`tateishi_L2_front_closeup.png`)で縦縞・縦流れに見えた。
    ⛔⛔ **一度は「頭も円筒投影(uparam/vparam)で側面と連続させる」案を試したが、
    これも失敗した** — apex_v は m=11 方向すべてのウェッジから共有される**単一の頂点**
    なので、頂点レイヤーに「apex の u」を1つだけ書いても、周方向に大きく離れた
    肩リング点(例 u=0.7)まで無理やりその1値へ収束させることになり、細長い
    スリバー三角形ごとに強烈な引き伸ばし=放射状の縞が出た(2026-09-06 に実見。
    コーンの頂点を単一の頂点属性で円筒投影しようとする限り、この放射縞は原理的に
    避けられない — 頂点属性は面ごとに値を変えられないため)。
    ⭕ **正しい対処は「UV はループ(面の角)ごとの値」という事実を使うこと** — 同じ
    apex_v でも、ウェッジ(小さな割れ面三角形)ごとに別の UV を持たせられる
    (コーンの頂点をUV展開するときの標準的な扱い)。`gen_stone` がまだ細分・bevel前
    (辺の対応が単純)の段階で、ウェッジごとに「土台2点は側面と同じ式・apex側の角は
    その2点の生値の平均」を直接書き込み済み — ここではそれを**上書きしない**。
    ⚠⚠ **法線の閾値では天端/頭を判定しない**(cap_like の判定は従来どおり
    `_is_cap_like` — 作成時のタグに基づく事後判定。hosori で天端が狭くなり法線が
    乱れても崩れない。2026-09-06 に実見済みの罠、再発させない)。
    ⚠⚠ **面ごとに投影軸を法線で切り替える(triplanar風)手は不採用**
    (2026-09-06 第6次差し戻しで実見)。割れ肌ノイズで細かく波打つ隣接三角形が
    交互に別の軸を選び、texture 空間の全く違う場所を読んでゼブラ縞になった。

    `ou`/`ov` は矩形内オフセット — `gen_stone` が石ごとに一度だけ決めた値を渡す
    (頭のファンの早期UVと、ここでの一括UVで**同じ値を共有する必要がある**ため。
    ⚠ **9個体が同じ矩形を同じ位置で見るとヒビの模様が判子のように揃う**
    (2026-09-06 に実見 — S/M/L × 3個体が横並びだと同じ亀裂線が全員に出ていて
    分かった)。矩形の**内側の安全域(縁から離れた所)**に収まる範囲だけ振るので、
    パディングへは踏み込まない。"""
    for f in bm.faces:
        n = f.normal
        is_cap = _is_cap_like(f, is_cap_layer, is_head_v_layer) if is_head_v_layer is not None             else bool(f[is_cap_layer])
        is_front = (not is_cap) and n.y < -0.85
        # 底(埋設)は z≈0 で見分ける。`is_cap`(_is_cap_like)は is_head_v の頂点タグに
        # 依存するため肩リング境界の細分でまれに誤爆しうる(uv_layer 作成部のコメント
        # 参照) — z の高さでも確認して、誤爆した頭寄りの面を「底」扱いしないようにする。
        is_bottom = is_cap and all(loop.vert.co.z < 1e-4 for loop in f.loops)
        for loop in f.loops:
            if uv_ready is not None and loop[uv_ready] > 0.5:
                continue   # このループは gen_stone が早期UV済み。上書きしない。
            co = loop.vert.co
            # ⚠ **オフセットは整数を避ける。**`pingpong` の畳み目は整数境界に立つので、
            #   x=0(前面・天端の中心線)がちょうど畳み目に乗ると左右対称に鏡映してしまう
            #   (2026-09-06 に実見 — 前面が紋章のように左右対称になった)。0.5 系のオフセットで
            #   使う範囲をまるごと片方の枝(0〜1の内側)へ逃がす。
            if is_front:
                fu = pingpong(co.x * DENS_U + ou)
                fv = pingpong(co.z * DENS_V + ov * 0.3)
            elif is_bottom:
                fu = pingpong(co.x * DENS_P + ou)
                fv = pingpong(co.y * DENS_P + ov)
            else:
                v_h = loop.vert[vparam] if vparam is not None else co.z
                fu = pingpong(loop.vert[uparam] * back_len * DENS_U)
                fv = pingpong(v_h * DENS_V + ov * 0.3)
            loop[uv_layer].uv = (RECT[0] + fu * (RECT[2] - RECT[0]),
                                  RECT[1] + fv * (RECT[3] - RECT[1]))


def _borrow_rock_material():
    m = bpy.data.materials.get(ROCK_MAT)
    if m:
        return m
    objs = VM.import_fbx_abs(os.path.join(NMR, "Rock_04.FBX"),
                             keep=lambda n: "LOD1" not in n and "LOD2" not in n)
    m = bpy.data.materials.get(ROCK_MAT)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    if m is None:
        raise SystemExit("[tateishi] M_photoscanned_rocks_01 を読めない")
    return m


def bounds(objs):
    """頂点から直に測る(`build_maruta.bounds` と同じ理由 — 書き出し後は bbox が 0 に潰れる)。"""
    import mathutils as mu
    mn = mu.Vector((1e9,) * 3); mx = mu.Vector((-1e9,) * 3)
    for o in objs:
        for v in o.data.vertices:
            wv = o.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], wv[i]); mx[i] = max(mx[i], wv[i])
    return mn, mx


def _is_head_face(f, is_head_v_layer):
    """面が「頭の割れ面」かどうかを**頂点のタグから事後判定する**(2026-09-06
    第6次差し戻し対応)。面タグは細分で新しい面へ引き継がれる保証が無いが、
    頂点タグは細分でも位置と一緒に確実に補間される(`uparam` と同じ理屈)。
    全頂点が is_head_v なら頭(側面と頭の境の遷移バンドは半分だけ head 頂点なので
    False になり、正しく「側面」のまま扱われる)。"""
    return all(v[is_head_v_layer] for v in f.verts)


def _is_cap_like(f, is_cap_layer, is_head_v_layer):
    """天端・底・頭の割れ面をまとめて「cap 相当」とみなす(round_edges の
    cap↔非cap境界ルール用)。底のファンは面タグ(is_cap、細分を一切通らないので
    100%信頼できる)、頭の割れ面は頂点タグの事後判定(`_is_head_face`)。"""
    return bool(f[is_cap_layer]) or _is_head_face(f, is_head_v_layer)


def finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, is_apex_layer, is_head_v_layer, m, name,
                 vparam=None, uv_layer=None, uv_ready=None, ou=0.5, ov=0.5):
    """細分 → 稜を丸める(bevel) → 割れ肌ノイズ → 法線確定 → UV。共有(build_one と
    グループショットの両方が呼ぶ — 2箇所に同じ手順を書き写すと片方だけ直して片方が
    古いまま、が起きるため)。戻り値は `bpy.types.Mesh`(bm は free 済み)。
    ⚠ 呼び出し側が **先に** `bmesh.ops.subdivide_edges(bm, edges=side_edges, ...)`
    を済ませてから渡すこと(天端・底のファンは細分しないので、ここでは繰り返さない)。
    ⚠ **頭頂点の vertex bevel(round_apex)はここでは呼ばない** — `gen_stone` が
    細分前の粗い(=辺が長い)段階で既に済ませている(2026-09-06 第6次差し戻し対応。
    理由は `gen_stone` 内のコメント参照)。
    ⚠ **`uv_layer` はここで新規作成しない** — `gen_stone` が細分・bevel より前に
    作って頭の割れ面のUVを直接書き込み済みのものを、そのまま受け取って使う
    (2026-09-06 UV直し)。新しいレイヤーを作るとその書き込みが失われる。"""
    ensure_outward(bm)
    bm.normal_update()
    round_edges(bm, h, rng, is_cap_layer, is_head_v_layer)
    bm.normal_update()
    # ⭐ 2026-09-06 第5次差し戻し item3「長い直線の稜を作らない」— 頭の割れ面
    #   (is_head_v の頂点)へ絶対量1〜3cmの細かいノイズを掛ける。round_edges で
    #   丸めた**後**にやる(丸めの土台がガタつくと bevel が失敗しやすいため)。
    add_head_noise(bm, rng, is_head_v_layer, is_apex_layer)
    bm.normal_update()
    # ⚠ add_crack_noise は is_head_v の頂点を二重処理しない(振幅の基準が違う —
    #   add_crack_noise は石のサイズに比例、add_head_noise は絶対量cm)。
    add_crack_noise(bm, w, d, h, rng, is_head_v_layer)
    bm.normal_update()
    ensure_outward(bm)
    # ⚠ **`reverse_faces` はキャッシュ済みの `f.normal` を即座に更新しない場合がある。**
    #   `assign_uv` は面ごとの法線で前面/側面を振り分けるので、ここで更新し忘れると
    #   一部の面だけ古い(反転前の)法線を読んで別の式に落ち、前面のテクスチャが
    #   ジグザグに破綻した(2026-09-06 に実見)。**UV を決める直前に必ず呼び直す。**
    bm.normal_update()

    me = bpy.data.meshes.new(name)
    assign_uv(bm, uv_layer, uparam, back_len, is_cap_layer, is_head_v_layer,
              vparam=vparam, ou=ou, ov=ov, uv_ready=uv_ready)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def build_one(size, i):
    """S/M/L の個体1つ。LOD0(細分+割れ肌)と LOD1(Decimate)を1つのFBXへ入れる。"""
    w, d, h = SPEC[size]
    seed = hash((size, i)) & 0xFFFFFFFF
    profile_name = PROFILE_BY_VARIANT.get(i, "atama")
    bm, m, rng, side_edges, uparam, back_len, is_cap_layer, is_apex_layer, is_head_layer, vparam, uv_layer, uv_ready, ou, ov = gen_stone(seed, w, d, h, profile_name)

    # 細分(天端・底のファンには触れない。前面の平らさは保ったまま稜の密度だけ上げる)
    bmesh.ops.subdivide_edges(bm, edges=side_edges, cuts=SUBDIV_CUTS, use_grid_fill=True)
    me = finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, is_apex_layer, is_head_layer, m, "Tateishi_%s_%d" % (size, i),
                      vparam=vparam, uv_layer=uv_layer, uv_ready=uv_ready, ou=ou, ov=ov)

    o = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(o)
    mat = _borrow_rock_material()
    o.data.materials.append(mat)

    # ちょうど仕様の (w,d,h) に補正(生成の近似誤差を吸収)。底は z=0 のまま・X,Y はbboxで芯へ寄せる。
    mn, mx = bounds([o])
    sx = w / max(mx.x - mn.x, 1e-6)
    sy = d / max(mx.y - mn.y, 1e-6)
    sz = h / max(mx.z - mn.z, 1e-6)
    o.data.transform(Matrix_scale(sx, sy, sz))
    mn, mx = bounds([o])
    o.data.transform(Matrix_translate(-(mn.x + mx.x) * 0.5, -(mn.y + mx.y) * 0.5, -mn.z))
    o.data.update()

    o.name = o.data.name = "Tateishi_%s_%d_LOD0" % (size, i)
    return o


def Matrix_scale(sx, sy, sz):
    import mathutils
    return mathutils.Matrix.Diagonal((sx, sy, sz, 1.0))


def Matrix_translate(tx, ty, tz):
    import mathutils
    return mathutils.Matrix.Translation((tx, ty, tz))


def make_lod1(lod0):
    """Decimate で約4割まで落として `_LOD1` を作る。"""
    o1 = lod0.copy()
    o1.data = lod0.data.copy()
    bpy.context.scene.collection.objects.link(o1)
    mod = o1.modifiers.new("dec", 'DECIMATE')
    mod.ratio = 0.4
    bpy.context.view_layer.objects.active = o1
    V.sel([o1])
    bpy.ops.object.modifier_apply(modifier=mod.name)
    base = lod0.name[:-5] if lod0.name.endswith("_LOD0") else lod0.name
    o1.name = o1.data.name = base + "_LOD1"
    return o1


def hook():
    """検証レンダ用に岩のアルベドを結ぶ(`build_okabe_niwa.hook` と同じ手順・同じ罠)。"""
    for m in bpy.data.materials:
        base = m.name.split('.')[0]
        if base != ROCK_MAT:
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        for sock in ('Alpha', 'Base Color'):
            for lk in list(b.inputs[sock].links):
                nt.links.remove(lk)
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.85
        try:
            m.surface_render_method = 'DITHERED'
        except Exception:
            pass
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(NMR_TEX, check_existing=True)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        if os.path.exists(NMR_NRM):
            ni = nt.nodes.new('ShaderNodeTexImage')
            ni.image = bpy.data.images.load(NMR_NRM, check_existing=True)
            ni.image.colorspace_settings.name = 'Non-Color'
            nm = nt.nodes.new('ShaderNodeNormalMap')
            nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])


def shots(objs, key, box=None):
    """⚠ 書き出しの前に撮る(`export_fbx` を通すと bbox が 0 に潰れる)。"""
    hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box if box else bounds(objs)
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    c = (mn + mx) * 0.5
    S = max(W, H, D)
    V.studio((c.x, mn.y - S * 3.0, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H * 1500.0 / 1100) * 1.25, res=(1500, 1100))
    V.render(os.path.join(SHOT, "tateishi_%s_elev.png" % key))
    V.studio((c.x - S * 1.0, mn.y - S * 1.4, mx.z + S * 0.55), (c.x, c.y, c.z),
             res=(1500, 1100))
    V.render(os.path.join(SHOT, "tateishi_%s_3d.png" % key))


def compare_boulder():
    """検証専用カット — 普請奉行 差し戻し(2026-09-06)の確認条件。
    **在庫の転石 `JG_Rock_A_01`** を、当スクリプトの立石(M・3プロファイル)の横に並べて
    『立石が岩に見えるか』を比較する。⚠ **材質は無理に揃えない** — `JG_Rock_A_01` の
    UV は自分の元の材質(`Test`)用に作られているので、こちらの `M_photoscanned_rocks_01`
    へ貼り替えると UV が無関係な絵柄を拾って壊れた絵になる(規約4と同じ理由での不採用)。
    ⭕ **各自のネイティブな材質のまま**並べ、「姿」だけを見比べる。"""
    V.reset()
    group = []
    gi = 0
    for i in (1, 2, 3):
        w, d, h = SPEC["M"]
        bm, m, rng, side_edges, uparam, back_len, is_cap_layer, is_apex_layer, is_head_layer, vparam, uv_layer, uv_ready, ou, ov = gen_stone(
            hash(("cmp", i)) & 0xFFFFFFFF, w, d, h, PROFILE_BY_VARIANT.get(i, "atama"))
        bmesh.ops.subdivide_edges(bm, edges=side_edges, cuts=SUBDIV_CUTS, use_grid_fill=True)
        me = finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, is_apex_layer, is_head_layer, m, "cmp_tateishi_%d" % i,
                          vparam=vparam, uv_layer=uv_layer, uv_ready=uv_ready, ou=ou, ov=ov)
        o = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(o)
        o.data.materials.append(_borrow_rock_material())
        o.data.transform(Matrix_translate(gi * 1.3, 0, 0))
        o.data.update()
        group.append(o)
        gi += 1

    jg_path = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden",
                            "Models", "Misc", "Rocks", "FJG_Rock_A_01_LOD0.fbx")
    objs = VM.import_fbx_abs(jg_path, keep=lambda n: "LOD1" not in n and "LOD2" not in n)
    jg = V.join([o for o in objs if o.type == 'MESH'], "JG_Rock_A_01_compare")
    mn, mx = bounds([jg])
    jg.data.transform(Matrix_translate(-(mn.x + mx.x) * 0.5, -(mn.y + mx.y) * 0.5, -mn.z))
    jg.data.transform(Matrix_translate(gi * 1.3 + 0.6, 0, 0))
    jg.data.update()
    group.append(jg)
    hook()   # 立石側(M_photoscanned_rocks_01)だけ結線
    # ⚠ 見た目比較だけの目的で、JG_Rock_A_01 の "Test" マテリアル(素の状態だとテクスチャが
    #   繋がっておらずマゼンタで写る)へ、実際に prefab が使う `M_FJG_Rock_001` 系の
    #   在庫テクスチャを臨時で繋ぐ(⚠ このスクリプトの出荷物には影響しない — 比較カット限定)。
    jg_tex = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden",
                          "Textures", "Misc", "T_FJG_Rock_Dark_001_Albedo.png")
    for m in bpy.data.materials:
        if m.name.split('.')[0] != "Test" or not os.path.exists(jg_tex):
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        for lk in list(b.inputs['Base Color'].links):
            nt.links.remove(lk)
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(jg_tex, check_existing=True)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.85
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = bounds(group)
    W, H = mx.x - mn.x, mx.z - mn.z
    c = (mn + mx) * 0.5
    V.studio((c.x, mn.y - max(W, H) * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=W * 1.15, res=(1800, 900))
    V.render(os.path.join(SHOT, "tateishi_vs_boulder.png"))
    print("[tateishi] 比較カット書き出し " + os.path.join(SHOT, "tateishi_vs_boulder.png"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "compare_boulder" in argv:
        compare_boulder()
        return
    want = [a for a in argv if not a.startswith("--")] or ["all"]
    if "all" in want:
        want = ["S", "M", "L"]
    do_render = "--render" in argv

    for size in want:
        if size not in SPEC:
            print("[tateishi] ⚠ 知らないサイズ: %s" % size); continue
        w, d, h = SPEC[size]
        for i in (1, 2, 3):
            V.reset()
            lod0 = build_one(size, i)
            lod1 = make_lod1(lod0)
            mn, mx = bounds([lod0])
            tri0 = sum(len(p.vertices) - 2 for p in lod0.data.polygons)
            tri1 = sum(len(p.vertices) - 2 for p in lod1.data.polygons)
            name = "Tateishi_%s_%d" % (size, i)
            print("[tateishi] %-16s 実寸 W(X)=%.3f H(Z→Y)=%.3f D(Y→Z)=%.3f  "
                  "LOD0 %d tri / LOD1 %d tri  材質=%s"
                  % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, tri0, tri1,
                     [s.name for s in lod0.data.materials]))
            if do_render:
                shots([lod0], "%s_%d" % (size, i), box=(mn, mx))
            V.export_fbx([lod0, lod1], os.path.join(OUT, name + ".fbx"))
            print("[tateishi] 書き出し " + os.path.join(OUT, name + ".fbx"))

    if do_render and len(want) >= 1:
        # 9個体を並べた集合ショット(取り違え・粒度のばらつきを確認するため)
        V.reset()
        group = []
        gi = 0
        for size in want:
            w, d, h = SPEC[size]
            for i in (1, 2, 3):
                bm, m, rng, side_edges, uparam, back_len, is_cap_layer, is_apex_layer, is_head_layer, vparam, uv_layer, uv_ready, ou, ov = gen_stone(
                    hash((size, i)) & 0xFFFFFFFF, w, d, h, PROFILE_BY_VARIANT.get(i, "atama"))
                bmesh.ops.subdivide_edges(bm, edges=side_edges, cuts=SUBDIV_CUTS, use_grid_fill=True)
                me = finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, is_apex_layer, is_head_layer, m, "grp_%s_%d" % (size, i),
                                  vparam=vparam, uv_layer=uv_layer, uv_ready=uv_ready, ou=ou, ov=ov)
                o = bpy.data.objects.new(me.name, me)
                bpy.context.scene.collection.objects.link(o)
                o.data.materials.append(_borrow_rock_material())
                o.data.transform(Matrix_translate(gi * 1.3, 0, 0))
                o.data.update()
                group.append(o)
                gi += 1
        shots(group, "all9")


if __name__ == "__main__":
    main()
