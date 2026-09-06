#!/usr/bin/env python3
"""**刈込の生垣モジュール**(松江松平上屋敷 matsudaira_dewa の中仕切り。ツゲ・マサキ刈込 h1.9m)。

    blender --background --python Tools/Blender/build_ikegaki.py -- [mid|end|all] [--render]

【なぜ新造するか】在庫方 2026-09-06 判定: `Assets/Waldemarst/FreeJapaneseGarden` の
Boxwood は高さ 0.84〜0.91m の単株プレハブ(`Prefabs/Plants/Boxwood/Single/*`)しか無く、
連続する刈込生垣(1間モジュールを並べて通す)のメッシュは在庫に無い。

【依頼の前提を覆す発見 ― 材の「FBX」は実在しない】
依頼は「`Plant_Boxwood_Spring_01.prefab` の FBX の葉のカードを借りる」だったが、
調べると **その FBX は存在しない**。このパックの植物は Unity 側の手続き生成ツールが
メッシュを直接 `.prefab` に埋め込みバイナリ(`m_VertexData` の圧縮ストリーム)として
焼き込んでおり、他の部材(石・坂)のように `Models/*.fbx` へ実体を持たない
(`Assets/Waldemarst/FreeJapaneseGarden/Models/` は `Misc/Rocks` と `Misc/Slopes` だけで
Plants が無いことを確認済み)。Blender の FBX インポータでは読めない形式。
⭕ そこで **`build_tsuru.py` と同じ「アトラス実測 → 葉カードを起こす」方式**に切り替えた
(あちらも `Wisteria_A_Branches_01` が使えないと分かってカードを別ソースから起こした前例):
  ① 同梱テクスチャ `T_FJG_Boxwood_Spring_000_Atlas_Albedo.png`(4096²)の**アルファ
     チャンネルを connected-component 解析**し、実際にこのマテリアルが使う **8つの
     葉叢シルエット**(刈り込む前の一株ぶんの輪郭。実測値を `CARD_UV` に埋め込み済み)を
     UV矩形として取り出した。
  ② 同じ解析で**内部の不透明パッチ**(95%以上不透明・葉色のまだら)を1つ見つけ、
     下地(コア)のタイル張り用 `CORE_UV` にした。
  ③ マテリアル名 `M_FJG_Plant_Boxwood_01_Spring` は**名前だけ**を使う
     (`vklib.named_material`)— ジオメトリは自前でも材質は新規作成しない。
     remap で実際の `.mat`(実物の葉シェーダ)に置き換わる。

【作り】
  ・**コア**(躯体): 断面(厚み×高さ)を裾0.90m→天端0.75mへ直線ですぼめ、天端の左右2辺だけ
    半径0.065mの丸みを付けた多角形を、走り方向(1間)へ押し出した中実体。表面は
    `CORE_UV` のパッチを ping-pong 式(build_tateishi.pingpong と同じ折返し)で
    細かくタイル張りし、単一の伸ばし貼りにならないようにした(規約3)。
  ・**葉のカード**: コア表面(前・後・天端、端部モジュールは小口も)に `CARD_UV` の
    8種を無作為に選びながら2層(外側=大きめ疎、内側=控えめ密)で貼り、質感を作る。
    近距離での抜け(裏面カリング)対策に**両面(両巻き順)を出す**。
  ・**継ぎ目**: 中間モジュールの両小口は垂直な平面のまま(コアは走りぴったり
    [-0.909, 0.909])。葉カードだけは小口面をわずかに超えて(最大0.05m)外側へ
    食い込ませてあるので、モジュールを突き付けると隣の葉と重なって継ぎ目が消える
    (CLAUDE.md「隙間 > めり込み」の判断)。
  ・**端部モジュール**(`end`): -X 側の小口を葉カードで丸く閉じる(刈込生垣の
    終端らしい房)。+X 側は中間モジュールと同じ垂直小口(隣へ突き付ける側)。

【出力(Unity座標)】幅=X 1.818 / 高さ=Y 1.90 / 厚み=Z 裾0.90〜天端0.75。
ピボット = 1間の中心・床レベル(Y=0)・厚みは中心(Z=0、生垣は両面とも同じ見え方)。
LOD1 同梱(密度を落として直接生成。カードは1枚が最小単位でこれ以上デシメートできない
ので `build_tateishi.make_lod1` の Decimate ではなく `build_tree.py` 方式=密度を
落として作り直す)。
"""
import bpy, sys, os, math, random
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM

OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Niwa")
SHOT = os.path.join(V.REPO, "Screenshots")

MAT_NAME = "M_FJG_Plant_Boxwood_01_Spring"
TEX_DIR = os.path.join(V.REPO, "Assets", "Waldemarst", "FreeJapaneseGarden",
                        "Textures", "Plants", "Boxwood_Spring_001")
TEX_ALBEDO = os.path.join(TEX_DIR, "T_FJG_Boxwood_Spring_000_Atlas_Albedo.png")

# ⭐ 実測(アルファチャンネルの connected-component 解析。scratchpad で1回だけ実行し、
#   ここへ埋め込んだ — Blender 内蔵 python には PIL が無いので実行時には解析しない)。
#   8つの葉叢シルエット(刈込前の一株の輪郭。小さな断片・ノイズは足切り済み)。
CARD_UV = [
    (0.3877, 0.4951, 0.6982, 0.7334),
    (0.3975, 0.2295, 0.6826, 0.4619),
    (0.0205, 0.4990, 0.2998, 0.7510),
    (0.4111, 0.0000, 0.7021, 0.2139),
    (0.7178, 0.2295, 0.9912, 0.4502),
    (0.0010, 0.2568, 0.3428, 0.4893),
    (0.0127, 0.0000, 0.3760, 0.2354),
    (0.7783, 0.4795, 0.9912, 0.7334),
]
# 内部の不透明パッチ。コアのタイル張り用。
# ⭐ 2026-09-06 差し戻し(司令塔): 天端・小口が「箱に葉をまばらに貼った」ように見える
# → 躯体の地肌を**葉の影の色**(暗く・彩度低め)へ変更。同じアトラス内で
# 明度が最も低い不透明パッチ(輝度 73/255。旧パッチは明るい葉色でギャップが
# 「箱の素地」に見えていた)を選び直した。新規マテリアルは作っていない。
CORE_UV = (0.3325, 0.1240, 0.3384, 0.1299)

L = 1.818          # 走り(1間)
H = 1.90           # 高さ
D_BASE = 0.90      # 裾の厚み
D_TOP = 0.75       # 天端の厚み
FILLET = 0.065     # 天端の丸み半径(5〜8cm 指定の中庸)
END_OVER = 0.045   # 葉カードが小口面を食い込ませて超える量


def pingpong(x):
    x = x % 2.0
    return x if x <= 1.0 else 2.0 - x


def tile_uv(rect, a, b, freq=3.4):
    u0, v0, u1, v1 = rect
    fu = pingpong(a * freq)
    fv = pingpong(b * freq)
    return (u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv)


# ---------------------------------------------------------------- コア(躯体)
def profile():
    """断面(厚み, 高さ)の閉じたリング。裾→天端まで直線ですぼめ、天端の左右だけ丸める。
    右半分を作ってから鏡映して繋ぐ(README「新造ジオメトリ」の作法と同じ弧の切り方)。"""
    r = FILLET
    hb0, hb1 = D_BASE / 2.0, D_TOP / 2.0
    seg = 5
    prof = [(hb0, 0.0), (hb1, H - r)]
    cx, cy = hb1 - r, H - r
    for i in range(1, seg + 1):
        a = (math.pi / 2.0) * i / seg
        prof.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    left = [(-t, y) for (t, y) in reversed(prof)]
    return prof + left        # [(thick, height), ...] 反時計/時計は問わない(両面出すため)


def half_thick(ht):
    """高さ ht における半厚み(葉カードをコア表面に貼るための近似式。
    天端の丸み分だけカードが僅かに面より内側に来るが、天端カードの被りで隠れる)。"""
    r = FILLET
    hb0, hb1 = D_BASE / 2.0, D_TOP / 2.0
    f = min(max(ht / (H - r), 0.0), 1.0)
    return hb0 + (hb1 - hb0) * f


def build_core(mesh, x0, x1):
    """走り x∈[x0,x1] へコアを押し出す。両巻き順で出す(裏面カリング対策・低コスト)。"""
    ring = profile()
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        t0, y0 = ring[i]; t1, y1 = ring[j]
        p0 = (x0, y0, t0); p1 = (x0, y1, t1)
        p2 = (x1, y1, t1); p3 = (x1, y0, t0)
        uv = [tile_uv(CORE_UV, y0, t0), tile_uv(CORE_UV, y1, t1),
              tile_uv(CORE_UV, y1, t1), tile_uv(CORE_UV, y0, t0)]
        mesh.quad_uvs([p0, p1, p2, p3], uv)
        mesh.quad_uvs([p3, p2, p1, p0], list(reversed(uv)))
    # 小口の平面(ファン三角形。両巻き順)
    cx_t = sum(t for t, _ in ring) / n
    cx_y = sum(y for _, y in ring) / n
    for xc in (x0, x1):
        for i in range(n):
            j = (i + 1) % n
            t0, y0 = ring[i]; t1, y1 = ring[j]
            pc = (xc, cx_y, cx_t)
            pa = (xc, y0, t0)
            pb = (xc, y1, t1)
            uvc = tile_uv(CORE_UV, cx_y, cx_t)
            uva = tile_uv(CORE_UV, y0, t0)
            uvb = tile_uv(CORE_UV, y1, t1)
            mesh.tri_uvs([pc, pa, pb], [uvc, uva, uvb])
            mesh.tri_uvs([pc, pb, pa], [uvc, uvb, uva])


# ---------------------------------------------------------------- 葉のカード
def add_card(mesh, center, normal, updir, size, aspect, uv_rect, rnd):
    """center を中心に、normal 向き(両面)の矩形カードを貼る。updir は「上」の目安
    (roll で回すのでラフでよい)。aspect = v方向/u方向の比(元画像の縦横比を保つ)。"""
    normal = Vector(normal).normalized()
    up = Vector(updir)
    e1 = (up - normal * up.dot(normal))
    if e1.length < 1e-6:
        e1 = Vector((1, 0, 0)) if abs(normal.x) < 0.9 else Vector((0, 1, 0))
    e1.normalize()
    e2 = normal.cross(e1)
    roll = rnd.uniform(0.0, math.tau)
    s1 = e1 * math.cos(roll) + e2 * math.sin(roll)
    s2 = -e1 * math.sin(roll) + e2 * math.cos(roll)
    w = size; h = size * aspect
    c = Vector(center)
    p0 = c - s1 * w * 0.5 - s2 * h * 0.5
    p1 = c + s1 * w * 0.5 - s2 * h * 0.5
    p2 = c + s1 * w * 0.5 + s2 * h * 0.5
    p3 = c - s1 * w * 0.5 + s2 * h * 0.5
    u0, v0, u1, v1 = uv_rect
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    # points は論理座標 (走り, 高さ, 厚み) = (x, y, z) の順で quad_uvs に渡す
    pts = [(p.x, p.z, p.y) for p in (p0, p1, p2, p3)]
    mesh.quad_uvs(pts, uv, mat=0)
    mesh.quad_uvs(list(reversed(pts)), list(reversed(uv)), mat=0)


def _reach(size, aspect):
    """カードは roll で任意の向きに回るので、面内の最大半径(対角線の半分。size×aspectの
    矩形をどの角度で回しても中心からこの距離は超えない、厳密な上界)を安全側の margin にする。"""
    return 0.5 * size * math.sqrt(1.0 + aspect * aspect)


def _clamp_center(p, lo, hi, reach, slack):
    """カードの中心を [lo-slack+reach, hi+slack-reach] へ収める。
    ⚠ **アンカーを境界ぴったりまで一様分布させない。** カード自身の半径ぶんだけ
    外へはみ出す(roll でどの向きにも回るため)ので、境界へ寄せ切ると
    bbox が呼び寸法よりひと回り大きく出る(初版で W 2.22 / H 2.11 / D 1.12 に
    膨らんで実測した)。`slack` だけを意図した食み出し予算にする。"""
    lo2, hi2 = lo - slack + reach, hi + slack - reach
    if lo2 > hi2:
        return 0.5 * (lo + hi)
    return min(max(p, lo2), hi2)


def scatter_side(mesh, rnd, x0, x1, sign, n, size_rng, off_rng, over=0.0):
    """前面(sign=+1)/背面(sign=-1)に葉カードを散らす。"""
    for _ in range(n):
        rect = CARD_UV[rnd.randrange(len(CARD_UV))]
        aspect = (rect[3] - rect[1]) / (rect[2] - rect[0])
        size = rnd.uniform(*size_rng)
        r = _reach(size, aspect)
        x = _clamp_center(rnd.uniform(x0 - over, x1 + over), x0, x1, r, over)
        ht = _clamp_center(rnd.uniform(0.0, H), 0.0, H, r, 0.05)
        th_base = half_thick(ht) * sign
        off = rnd.uniform(*off_rng)
        th_raw = th_base + off * sign
        # ⚠⚠ ここに `r`(対角線の全半径)をそのまま margin に使ったら、大きいカードほど
        #   コアの内側へ押し込まれて**完全に隠れた**(初回検証レンダで前面がほぼ
        #   コアの地肌だけになって実見・原因究明した)。normal は厚み方向がほぼ全て
        #   (高さへの傾きは0.28/1.04≈15.6°だけ)なので、roll がどの向きでも厚み方向へ
        #   はみ出す量は高々 `sin(15.6°)≈0.269 × (w/2+h/2)` — 対角線よりずっと小さい。
        #   その小さい見積りだけを margin にする。
        th_reach = 0.27 * size * (1.0 + aspect) * 0.5
        th = _clamp_center(th_raw, -D_BASE / 2.0, D_BASE / 2.0, th_reach, max(off_rng) + 0.02)
        pos = (x, ht, th)
        normal_l = (0.0, 0.28 * sign, 1.0 * sign)   # わずかに上を向けて葉が空を仰ぐ姿に
        # normal は論理(走り,高さ,厚み)。add_card 内部は (x,y,z)=(走り,高さ,厚み)で扱う
        add_card(mesh, (pos[0], pos[2], pos[1]),
                 (normal_l[0], normal_l[2], normal_l[1]),
                 (0.0, 0.0, 1.0), size, aspect, rect, rnd)


def scatter_top(mesh, rnd, x0, x1, n, size_rng, off_rng, over=0.0):
    half = D_TOP / 2.0
    for _ in range(n):
        rect = CARD_UV[rnd.randrange(len(CARD_UV))]
        aspect = (rect[3] - rect[1]) / (rect[2] - rect[0])
        size = rnd.uniform(*size_rng)
        r = _reach(size, aspect)
        x = _clamp_center(rnd.uniform(x0 - over, x1 + over), x0, x1, r, over)
        th = _clamp_center(rnd.uniform(-half, half), -half, half, r, 0.03)
        off = rnd.uniform(*off_rng)
        pos = (x, H + off, th)
        add_card(mesh, (pos[0], pos[2], pos[1]), (0.0, 0.0, 1.0),
                 (1.0, 0.0, 0.0), size, aspect, rect, rnd)


def scatter_top_rim(mesh, rnd, x0, x1, n, size_rng, over=0.0):
    """天端の左右の縁だけを狙って密に貼る帯。⭐ 2026-09-06 差し戻し(司令塔):
    「天端の面と側面のあいだで箱のシルエットが一周残る」→ 縁をまたいで**下へ垂れる**
    カードを別枠で足し、直線の稜線を葉の輪郭で崩す。5〜8cmはみ出す指定どおり、
    天端の外側(厚み方向)・下方(高さ方向)の両方へ意図的に飛び出させる。"""
    half = D_TOP / 2.0
    for _ in range(n):
        edge = 1.0 if rnd.random() < 0.5 else -1.0
        rect = CARD_UV[rnd.randrange(len(CARD_UV))]
        aspect = (rect[3] - rect[1]) / (rect[2] - rect[0])
        size = rnd.uniform(*size_rng)
        r = _reach(size, aspect)
        x = _clamp_center(rnd.uniform(x0 - over, x1 + over), x0, x1, r, over)
        # 縁ぴったりから外側+高さ下方向の両方へ 0.05〜0.08 だけ飛び出す
        out = rnd.uniform(0.05, 0.08)
        th = edge * (half + out * rnd.uniform(0.3, 1.0))
        droop = rnd.uniform(0.02, 0.08)
        pos = (x, H - droop, th)
        # add_card への入力は (走り, 厚み, 高さ) の順。法線は「上+外側」の中間
        # (コーナーを斜めに覆う向き)。
        add_card(mesh, (pos[0], pos[2], pos[1]),
                 (0.0, edge * 0.7, 0.8),
                 (1.0, 0.0, 0.0), size, aspect, rect, rnd)


def scatter_end(mesh, rnd, x_end, sign, n, size_rng, off_rng):
    """端部モジュールの小口を丸く閉じる葉の房。sign=-1 で -X 側(食い込みは -X 方向)。"""
    for _ in range(n):
        rect = CARD_UV[rnd.randrange(len(CARD_UV))]
        aspect = (rect[3] - rect[1]) / (rect[2] - rect[0])
        size = rnd.uniform(*size_rng)
        r = _reach(size, aspect)
        ht = _clamp_center(rnd.uniform(0.0, H), 0.0, H, r, 0.03)
        half = half_thick(ht) * 0.92
        th = _clamp_center(rnd.uniform(-half, half), -half, half, r, 0.03)
        off = rnd.uniform(*off_rng)
        x = x_end + sign * off
        add_card(mesh, (x, th, ht), (sign, 0.0, 0.0),
                 (0.0, 0.0, 1.0), size, aspect, rect, rnd)


# ---------------------------------------------------------------- 組み立て
def build_module(kind, lod, seed):
    """kind: 'mid'(両小口とも垂直な突き付け面) / 'end'(-X 側を葉で閉じる)。
    lod: 0=フル密度 / 1=間引き(build_tree.py と同じ「密度を落として作り直す」方式)。"""
    rnd = random.Random(seed)
    x0, x1 = -L / 2.0, L / 2.0
    m = VM.Mesh()
    build_core(m, x0, x1)

    dens = 1.0 if lod == 0 else 0.45
    size_boost = 1.0 if lod == 0 else 1.25   # 間引くぶん一枚を大きめにして被覆を保つ

    # 外層(疎・大きめ)+内層(密・控えめ)の2層。
    # ⚠ 面積割りの見積り(平均カード0.24m角×枚数)よりずっと薄く抜けた
    # (初回レンダで実見。乱数配置は面積を単純に足しても隙間だらけになる)。
    # ⭕ 経験的に約2.6倍まで増やしてやっと地肌(コアのタイル)が透けなくなった。
    n_side_outer = max(4, int(160 * dens))
    n_side_inner = max(4, int(120 * dens))
    n_top_outer = max(3, int(90 * dens))
    n_top_inner = max(3, int(64 * dens))

    for sign in (1, -1):
        scatter_side(m, rnd, x0, x1, sign, n_side_outer,
                     (0.22, 0.30) if lod == 0 else (0.28, 0.38),
                     (0.020, 0.045), over=END_OVER)
        scatter_side(m, rnd, x0, x1, sign, n_side_inner,
                     (0.14, 0.20) if lod == 0 else (0.18, 0.26),
                     (0.008, 0.022), over=END_OVER)
    scatter_top(m, rnd, x0, x1, n_top_outer,
                (0.22, 0.30) if lod == 0 else (0.28, 0.38), (-0.035, 0.040), over=END_OVER)
    scatter_top(m, rnd, x0, x1, n_top_inner,
                (0.14, 0.20) if lod == 0 else (0.18, 0.26), (-0.020, 0.020), over=END_OVER)
    # ⭐ 2026-09-06 差し戻し(司令塔): 天端の縁で箱のシルエットが一周残る → 縁専用の
    # 密な帯を追加(5〜8cmはみ出す・下へ垂れて稜線を崩す)。
    n_rim = max(6, int(70 * dens))
    scatter_top_rim(m, rnd, x0, x1, n_rim,
                     (0.16, 0.24) if lod == 0 else (0.20, 0.30), over=END_OVER)

    if kind == "end":
        n_end_outer = max(3, int(70 * dens))
        n_end_inner = max(3, int(50 * dens))
        scatter_end(m, rnd, x0, -1, n_end_outer,
                    (0.20, 0.28) if lod == 0 else (0.26, 0.36), (0.020, 0.045))
        scatter_end(m, rnd, x0, -1, n_end_inner,
                    (0.13, 0.18) if lod == 0 else (0.16, 0.24), (0.008, 0.022))

    name = ("Ikegaki_End_1.818_LOD%d" % lod) if kind == "end" else ("Ikegaki_1.818_LOD%d" % lod)
    mat = V.named_material(MAT_NAME)
    o = m.to_object(name, [mat])
    return o


def hook():
    """検証レンダのためだけにテクスチャを結ぶ。build_tsuru.hook() と同じ理由・同じ作法
    (`vklib.hook_textures()` は Alpha を 1.0 に固定するので使わない。画像を名指しで読み、
    Base Color / Alpha を自分で繋いで GREATER_THAN で 0/1 に丸める)。"""
    m = bpy.data.materials.get(MAT_NAME)
    if m is None or not os.path.exists(TEX_ALBEDO):
        return
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.location = (-200, 0)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    img = nt.nodes.new('ShaderNodeTexImage'); img.location = (-700, 200)
    img.image = bpy.data.images.load(TEX_ALBEDO, check_existing=True)
    nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = 0.35; gt.location = (-450, -100)
    nt.links.new(img.outputs['Alpha'], gt.inputs[0])
    nt.links.new(gt.outputs['Value'], b.inputs['Alpha'])
    m.surface_render_method = 'DITHERED'
    try:
        m.show_transparent_back = False
    except Exception:
        pass


def tri(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def shots(mid, end):
    """3モジュール連結(mid×2 + end×1)を斜め30°・目線1.5m・近景で撮る。"""
    os.makedirs(SHOT, exist_ok=True)
    hook()
    # ⚠ mid/end 本体はまだ原点(0,0,0)に残っている(export 用に採寸済みの姿のまま)。
    #   隠さずに撮ると、複製 b がそっくり同じ場所に重なって二重ジオメトリになり、
    #   レンダが至近距離のノイズにしか見えなくなった(初回の実測で気付いた)。
    #   ⛔⛔ `.copy()` は `hide_render` も複製する — 先に本体を隠してから複製すると、
    #   複製した a/b/c まで無条件に非表示を引き継いで**何も写らない**(end の閉じた
    #   小口だけ地肌のまま=b 自身の素の小口が見えていただけ、と2度目の実測で気付いた)。
    #   ⭕ 複製を先に作ってから本体を隠す。
    a = mid.copy(); a.data = mid.data.copy(); bpy.context.scene.collection.objects.link(a)
    b = mid.copy(); b.data = mid.data.copy(); bpy.context.scene.collection.objects.link(b)
    c = end.copy(); c.data = end.data.copy(); bpy.context.scene.collection.objects.link(c)
    mid.hide_render = True
    end.hide_render = True
    a.location = (-L, 0, 0)
    b.location = (0, 0, 0)
    c.location = (L, 0, 0)          # end の +X 小口が b の -X 小口へ突き付く向きで確認
    c.rotation_euler = (0, 0, math.pi)   # -X 小口(葉で閉じた側)を外側(+X 端)へ向ける
    bpy.context.view_layer.update()
    cx = 0.0
    # 斜め30°・目線1.5m。R は3モジュール連結(約5.45m)を収める見通し距離
    # (⚠ 初版は「走り方向へ寄った角度」で撮ってしまい、生垣の面をほぼ真横=通路の
    # 奥行き方向に見る形になって近景ノイズにしか見えなかった。正面方向(厚みZ軸)
    # から30°振る形に直した)。
    R = 5.0
    ang = math.radians(30)
    V.studio((cx + R * math.sin(ang), -R * math.cos(ang), 1.5),
             (cx, 0.0, 0.95), res=(1600, 1000))
    V.render(os.path.join(SHOT, "ikegaki_run_elev.png"))
    # ⭐ 2026-09-06 差し戻し対応: 「斜め上30°」(見下ろし・天端の面が読める)と
    # 「目線1.5m」(ほぼ水平・人が通りすがりに見る絵)を別カットで撮り直す
    # (元の1枚は目線寄りで、天端の縁の是正が判定しにくかった)。
    tz = H * 0.5
    Dh, az, elev = 4.5, math.radians(35), math.radians(30)
    V.studio((cx + Dh * math.sin(az), -Dh * math.cos(az), tz + Dh * math.tan(elev)),
             (cx, 0.0, tz), res=(1600, 1000))
    V.render(os.path.join(SHOT, "ikegaki_oblique_above30.png"))
    V.studio((cx + R * math.sin(ang) * 0.55, -R * 0.85, 1.5),
             (cx, 0.0, 1.45), res=(1600, 1000))
    V.render(os.path.join(SHOT, "ikegaki_eyelevel.png"))
    # 継ぎ目をもっと寄って確認(b と c の境目)
    V.studio((L * 0.5 - 0.9, -1.1, 1.3), (L * 0.5, 0.0, 1.1), res=(1600, 1000))
    V.render(os.path.join(SHOT, "ikegaki_seam.png"))
    # 天端の刈込を見下ろし気味に
    V.studio((0.3, -2.0, 2.6), (0.3, 0.0, 1.7), res=(1600, 1000))
    V.render(os.path.join(SHOT, "ikegaki_top.png"))
    # End モジュールの閉じた小口(世界座標 x=L+0.909)を正面から
    end_x = L + L / 2.0
    V.studio((end_x + 2.2, -0.4, 1.3), (end_x, 0.0, 1.0), res=(1600, 1000))
    V.render(os.path.join(SHOT, "ikegaki_end_cap.png"))
    for o in (a, b, c):
        bpy.data.objects.remove(o, do_unlink=True)
    mid.hide_render = False
    end.hide_render = False


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or ["all"]
    if "all" in want:
        want = ["mid", "end"]
    do_render = "--render" in argv
    os.makedirs(OUT, exist_ok=True)

    built = {}
    V.reset()   # ⚠ 一度だけ。kindごとに reset すると先に作ったオブジェクトが消え、
                #    後段の shots()/export で無効参照(StructRNA removed)になる。
    for kind in want:
        lod0 = build_module(kind, 0, 1856 + (0 if kind == "mid" else 7))
        V.dedup_materials()
        mn, mx = V.bbox([lod0])
        print("[ikegaki] %-24s LOD0 実寸 W(X)=%.3f H(Z)=%.3f D(Y)=%.3f  tri=%d  材質=%s"
              % (lod0.name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, tri(lod0),
                 [mm.name for mm in lod0.data.materials]))
        lod1 = build_module(kind, 1, 2856 + (0 if kind == "mid" else 7))
        V.dedup_materials()
        print("[ikegaki] %-24s LOD1 tri=%d" % (lod1.name, tri(lod1)))
        built[kind] = (lod0, lod1)

    if do_render and "mid" in built and "end" in built:
        shots(built["mid"][0], built["end"][0])

    for kind, (lod0, lod1) in built.items():
        path = os.path.join(OUT, lod0.name.rsplit("_LOD0", 1)[0] + ".fbx")
        V.export_fbx([lod0, lod1], path)
        print("[ikegaki] 書き出し %s" % path)


if __name__ == "__main__":
    main()
