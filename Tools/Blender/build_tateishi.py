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
    戻り値: (bm, m, rng, side_edges, uparam_layer, back_len)。
    `side_edges` = 側面(前面含む)だけの辺リスト — 天端・底のファンは細分の対象から外すため
    ここで(ファンを足す前に)確定させて返す。"""
    rng = random.Random(seed)
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
    # ⚠⚠ **天端・底の判定は面の法線(閾値)ではなく、作った時点のタグで持つ。**
    #   hosori(強い先細り)で天端が非常に狭くなると、多面天端の各小面の法線が乱れて
    #   閾値 0.85 を割り込み、UV が側面(円周)の式へ誤って落ちてジグザグに破綻した
    #   (2026-09-06 に実見)。⭕ 天端・底のファンは細分もされない一枚物なので、
    #   作った瞬間にタグを付ければ以後ずっと正しい(法線の揺れに影響されない)。
    is_cap = bm.faces.layers.int.new("is_cap")
    # ⚠ **u の巻き戻し(1.0→0.0)を前面の上に置かない。**周方向の並びは
    #   [前面右, 背弧…, 前面左] なので、そのまま index/m を u にすると継ぎ目が
    #   一番目立つ前面の真上に来る。**中心を背側へ回して**継ぎ目を裏へ逃がす。
    mid = m // 2
    uparam_of = [((i - mid) % m) / float(m) for i in range(m)]
    # 背弧の実長のおおよその見積り(UV密度の基準。前面・天端・底は別に平面投影するので使わない)
    back_len = math.pi * (w * 0.56 + d * 0.60) * ((N_BACK - 1) / float(N_BACK))

    rings = []   # rings[band] = [BMVert,...]（m個）
    for b in range(K_BANDS + 1):
        tfrac = b / float(K_BANDS)
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
            ring.append(v)
        rings.append(ring)
    bm.verts.ensure_lookup_table()

    # 天端の傾き: ランダムな方位・勾配(h の 4〜9% ×プロファイルの tilt_mul。hosori は強め)
    phi = rng.uniform(0, 2 * math.pi)
    tilt = rng.uniform(0.04, 0.09) * h * profile["tilt_mul"]
    for v in rings[K_BANDS]:
        v.co.z += tilt * (v.co.x * math.cos(phi) + v.co.y * math.sin(phi)) / max(w, d)

    # 側面: バンド間を四角形でつなぐ(前面の辺も含め m 枚/バンド)
    for b in range(K_BANDS):
        r0, r1 = rings[b], rings[b + 1]
        for i in range(m - 1):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
        # 前面(m-1 → 0 を結ぶ最後の辺)
        bm.faces.new((r0[m - 1], r0[0], r1[0], r1[m - 1]))
    side_edges = list(bm.edges)   # ⚠ ここで確定(下のファンを足す前)

    # 底(バンド0・z=0固定・ノイズ無し)。中心ファンで閉じる(埋設側なので単純な1点でよい)。
    bc = bm.verts.new((0.0, -d * 0.05, 0.0))
    bc[uparam] = 0.0
    for i in range(m):
        j = (i + 1) % m
        f = bm.faces.new((rings[0][j], rings[0][i], bc))
        f[is_cap] = 1

    # ⭐ 2026-09-06: 天端は単一の頂点に集めず、**2〜3枚の割れた小面**に分ける
    #   (差し戻し④「天端は平らな面を作らず、割れた小面2-3枚の集まりに」)。
    #   円環を乱数の分割点で連続した弧に切り、弧ごとに別の頂点(高さも僅かにばらす)へ
    #   ファンを立てる — 境界の頂点は隣の弧と共有するので穴は空かない。1点に全部集めると
    #   円錐状の「尖った蓋」に見え、稜線が1本もできない。
    top = rings[K_BANDS]
    n_facets = rng.choice([2, 3])
    # ⚠ 分割点が隣接すると弧が1〜2頂点しかない極端に細い小面ができ、UVが伸びて
    # 縞状に見える(2026-09-06 第2次差し戻しの検証レンダで実見)。最小間隔を確保する。
    for _try in range(20):
        splits = sorted(rng.sample(range(m), min(n_facets, m)))
        gaps = [(splits[(k + 1) % len(splits)] - splits[k]) % m for k in range(len(splits))]
        if min(gaps) >= max(3, m // (n_facets * 2)):
            break
    apex_h_jit = h * 0.055
    for k in range(len(splits)):
        a_idx, b_idx = splits[k], splits[(k + 1) % len(splits)]
        arc = [a_idx]
        i = a_idx
        while i != b_idx:
            i = (i + 1) % m
            arc.append(i)
        if len(arc) < 2:
            continue
        avg = Vector((0.0, 0.0, 0.0))
        for idx in arc:
            avg += top[idx].co
        avg /= float(len(arc))
        avg.z += rng.uniform(-apex_h_jit, apex_h_jit)
        apex = bm.verts.new(avg)
        apex[uparam] = 0.0
        for t in range(len(arc) - 1):
            f = bm.faces.new((top[arc[t]], top[arc[t + 1]], apex))
            f[is_cap] = 1

    bm.normal_update()
    return bm, m, rng, side_edges, uparam, back_len, is_cap


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


def add_crack_noise(bm, w, d, h, rng, amp_back=0.014, amp_front=0.003):
    """細分後の側面頂点へ、前面以外を強めに・前面は弱めにノイズを掛けて割れ肌を作る。
    底(z≈0)と天端近く(z>0.94h)は触らない — 天端はファンの向き(法線)が
    ノイズで暴れると一部の面だけ裏返り、`ensure_outward` の全体反転では直せない
    (穴が空いたように黒く抜けた。2026-09-06 に実見)。

    ⚠⚠ **前面/側面の境で振幅を急に切り替えない。**しきい値で amp_front→amp_back を
    ハードに切り替えると、見付の縁がまさにそこで「定規で引いた直線」に見える
    (2026-09-06 第2次差し戻し — vs_boulder で指摘された)。⭕ 前面の平面(y=front_y)からの
    距離でなめらかに補間する — 縁のノイズが自然に強まっていくので、直線が視覚的に
    強調されない。`chamfer_front_seam` と組み合わせて初めて縁が崩れる。"""
    top_guard = h * 0.94
    front_y0 = -d * 0.5
    blend = d * 0.30
    for v in bm.verts:
        if v.co.z < 1e-5 or v.co.z > top_guard:
            continue
        t = min(max((v.co.y - front_y0) / blend, 0.0), 1.0)
        amp = amp_front + (amp_back - amp_front) * t
        n = v.normal if v.normal.length > 1e-6 else Vector((0, -1, 0))
        v.co += n * rng.uniform(-amp, amp) * max(w, d, h) * 0.5
        v.co.z += rng.uniform(-amp, amp) * h * 0.3


def chamfer_front_seam(bm, w, d, h, rng, uparam, m):
    """見付(前面)と側面の境の縦の稜を、幅3〜8cmの不規則な面取りへ崩す。
    ⛔⛔ **2026-09-06 第2次差し戻し**「見付と側面の境が定規で引いた縦線になっている」
    (vs_boulder の3本に共通)。前面の2隅(index 0, m-1)は元々 x だけ僅かに振って
    y=front_y に固定していたので、バンドを積み上げると**完全に直線の稜**になっていた。

    ⭕ 前面の2隅にあたる列だけを `uparam` の値で特定し(この列は細分後も他の列と
    混ざらない — README「新造ジオメトリのUVを複数面の平均で決めない」と同じ考え方で、
    列を保つように subdivide が線形補間するため)、バンドごとに乱数で 3〜8cm ぶん
    内側(+Y)・左右(±X)・上下(Z)へ振る。天端・底には掛けない(据わりと多面天端を守る)。"""
    mid = m // 2
    u_right = ((0 - mid) % m) / float(m)
    u_left = ((m - 1 - mid) % m) / float(m)
    eps = 1e-4
    top_guard = h * 0.94
    for v in bm.verts:
        if v.co.z < 1e-5 or v.co.z > top_guard:
            continue
        u = v[uparam]
        if abs(u - u_right) > eps and abs(u - u_left) > eps:
            continue
        depth = rng.uniform(0.03, 0.08)
        v.co.y += depth * rng.uniform(0.5, 1.0)
        if abs(v.co.x) > 1e-6:
            v.co.x += math.copysign(depth * rng.uniform(0.25, 0.65), -v.co.x)
        v.co.z += rng.uniform(-0.03, 0.03) * h


def assign_uv(bm, uv_layer, uparam, back_len, is_cap_layer, rng=None):
    """3通りの平面/円周投影を面の向きで振り分ける。⚠ 一点貼り禁止(規約4) — 全頂点位置から
    決定論的に計算するので、面積の大きい面でもテクスチャの縞が読める。

    ・**前面**(法線が Blender −Y に強く寄る = Unity +Z の見付)… (x, z) の平面投影。
      矩形の平らな面なので、単純な平面投影が一番歪まない。
    ・**天端・底**(`is_cap_layer` で作成時にタグ済み)… (x, y) の平面投影。
      ⚠⚠ **法線の閾値では判定しない。** hosori(強い先細り)で天端が狭くなると
      多面天端の小面の法線が乱れて閾値を割り込み、UV が円周の式へ誤って落ちて
      ジグザグに破綻した(2026-09-06 に実見)。天端・底は細分されない一枚物なので、
      `gen_stone` が作成時に付けたタグをそのまま信じる方が確実。
    ・**背・側**(それ以外の不等な円弧面)… 周方向は `uparam`(頂点ごとに持たせた
      連続パラメータ。細分でも位置と一緒に線形補間される)× 背弧のおおよその実長、
      鉛直方向は高さ z。どちらも `DENS_U`/`DENS_V`(在庫の岩1体の実測密度)を掛ける。
    密度を掛けたあとは `pingpong()` で [0,1] に畳んで矩形へ写す(継ぎ目が出ない)。

    `rng` を渡すと、原点に小さな乱数オフセットを足す。⚠ **9個体が同じ矩形を同じ位置で
    見るとヒビの模様が判子のように揃う**(2026-09-06 に実見 — S/M/L × 3個体が横並びだと
    同じ亀裂線が全員に出ていて分かった)。矩形の**内側の安全域(縁から離れた所)**に
    収まる範囲だけ振るので、パディングへは踏み込まない。"""
    ou = ov = 0.5
    if rng is not None:
        ou += rng.uniform(-0.10, 0.10)
        ov += rng.uniform(-0.10, 0.10)
    for f in bm.faces:
        n = f.normal
        is_cap = bool(f[is_cap_layer])
        is_front = (not is_cap) and n.y < -0.85
        for loop in f.loops:
            co = loop.vert.co
            # ⚠ **オフセットは整数を避ける。**`pingpong` の畳み目は整数境界に立つので、
            #   x=0(前面・天端の中心線)がちょうど畳み目に乗ると左右対称に鏡映してしまう
            #   (2026-09-06 に実見 — 前面が紋章のように左右対称になった)。0.5 系のオフセットで
            #   使う範囲をまるごと片方の枝(0〜1の内側)へ逃がす。
            if is_front:
                fu = pingpong(co.x * DENS_U + ou)
                fv = pingpong(co.z * DENS_V + ov * 0.3)
            elif is_cap:
                fu = pingpong(co.x * DENS_P + ou)
                fv = pingpong(co.y * DENS_P + ov)
            else:
                fu = pingpong(loop.vert[uparam] * back_len * DENS_U)
                fv = pingpong(co.z * DENS_V + ov * 0.3)
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


def finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, m, name):
    """細分 → 面取り → 割れ肌ノイズ → 法線確定 → UV。共有(build_one とグループショットの
    両方が呼ぶ — 2箇所に同じ手順を書き写すと片方だけ直して片方が古いまま、が起きるため)。
    戻り値は `bpy.types.Mesh`(bm は free 済み)。⚠ 呼び出し側が **先に**
    `bmesh.ops.subdivide_edges(bm, edges=side_edges, ...)` を済ませてから渡すこと
    (天端・底のファンは細分しないので、ここでは繰り返さない)。"""
    ensure_outward(bm)
    bm.normal_update()
    # ⭐ 割れ肌ノイズより先に面取りを掛ける — 面取りで前面の縁が y=front_y から離れるので、
    #   後段のノイズ振幅ブレンド(前面からの距離で決める)が縁を自然と「側面寄り」に扱う。
    chamfer_front_seam(bm, w, d, h, rng, uparam, m)
    bm.normal_update()
    add_crack_noise(bm, w, d, h, rng)
    bm.normal_update()
    ensure_outward(bm)
    # ⚠ **`reverse_faces` はキャッシュ済みの `f.normal` を即座に更新しない場合がある。**
    #   `assign_uv` は面ごとの法線で前面/側面を振り分けるので、ここで更新し忘れると
    #   一部の面だけ古い(反転前の)法線を読んで別の式に落ち、前面のテクスチャが
    #   ジグザグに破綻した(2026-09-06 に実見)。**UV を決める直前に必ず呼び直す。**
    bm.normal_update()

    me = bpy.data.meshes.new(name)
    uv_layer = bm.loops.layers.uv.new("UVMap")
    assign_uv(bm, uv_layer, uparam, back_len, is_cap_layer, rng)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def build_one(size, i):
    """S/M/L の個体1つ。LOD0(細分+割れ肌)と LOD1(Decimate)を1つのFBXへ入れる。"""
    w, d, h = SPEC[size]
    seed = hash((size, i)) & 0xFFFFFFFF
    profile_name = PROFILE_BY_VARIANT.get(i, "atama")
    bm, m, rng, side_edges, uparam, back_len, is_cap_layer = gen_stone(seed, w, d, h, profile_name)

    # 細分(天端・底のファンには触れない。前面の平らさは保ったまま稜の密度だけ上げる)
    bmesh.ops.subdivide_edges(bm, edges=side_edges, cuts=SUBDIV_CUTS, use_grid_fill=True)
    me = finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, m, "Tateishi_%s_%d" % (size, i))

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
        bm, m, rng, side_edges, uparam, back_len, is_cap_layer = gen_stone(
            hash(("cmp", i)) & 0xFFFFFFFF, w, d, h, PROFILE_BY_VARIANT.get(i, "atama"))
        bmesh.ops.subdivide_edges(bm, edges=side_edges, cuts=SUBDIV_CUTS, use_grid_fill=True)
        me = finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, m, "cmp_tateishi_%d" % i)
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
                bm, m, rng, side_edges, uparam, back_len, is_cap_layer = gen_stone(
                    hash((size, i)) & 0xFFFFFFFF, w, d, h, PROFILE_BY_VARIANT.get(i, "atama"))
                bmesh.ops.subdivide_edges(bm, edges=side_edges, cuts=SUBDIV_CUTS, use_grid_fill=True)
                me = finish_mesh(bm, w, d, h, rng, uparam, back_len, is_cap_layer, m, "grp_%s_%d" % (size, i))
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
