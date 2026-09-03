"""**崖下(法尻の帯)の詰人長屋・物置・かわや**を起こす。岡部筑前守上屋敷。

    blender --background --python Tools/Blender/build_obi_nagaya.py -- [名前...] [--render]
    blender --background --python Tools/Blender/build_obi_nagaya.py -- nagaya --ken 7.5 2.5 --render
    (名前を省くと全部。nagaya / monooki / kawaya)

【なぜ新造するか】在庫照会(在庫方)の結果、この作りの平屋長屋は在庫に無い。
  ・`edogoyomi/es_knagaya` は **本瓦・二階・なまこ壁**の表長屋で、指図が要求する
    「桟瓦・平屋・下見板腰」と正面から食い違う(`roofs` が **表と崖下で格を分ける**と宣言している)
  ・Village Kit の `Prefabs/House` は壁で閉じた一軒家で、長屋の割付にならない
  → **Village Kit の実瓦(`roof 2x2`)を葺き、躯体だけ江戸間で起こす。**

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` が正典。ここで決めない】
  service N1/N2 詰人長屋 = 7.5間 × 2.5間 / M1 物置 = 3間 × 1.5間 / K_Obi かわや = 1間角
  roofs.ObiNagaya = 桟瓦(いぶし黒)・平屋・下見板腰・**水側(西)は盲面で開口は東**
  nishi.obi.nokiOut = 0.9(軒の出。⚠ 東の余地 4.0m の検査がこの値を含んで測っている)

【⚠ 棟高が指図の 4.30 と両立しない件 — 普請奉行へ】
  瓦は Village Kit の `roof 2x2` の**実ジオメトリ**で、勾配比は実測 **0.5456(5.5寸)に固定**
  (README「勾配比 0.5456 は roof 2x2 の実測から来る。変えるとモジュールが使えない」)。
  指図の 軒高2.7 / 棟高4.3 は 梁間2.5間 に対して **7寸勾配**を要求していて、瓦を 1.29 倍に
  引き伸ばさないと出ない。⛔ 引き伸ばすと桟瓦の凹凸が歪む(「自作の瓦はダサい」で却下された道)。
  → **軒高2.70 を 軒桁(=軒高の常法の定義)の高さとして守り、勾配は瓦のまま**にした。
    棟の熨斗を 0.36 見せることで **棟天端は 4.30 ちょうど**に納まる(RIDGE_SHOW)。
    ⚠ ただしこれは **梁間2.5間 のときだけ**成り立つ。物置(1.5間)・かわや(1間)は
    スパンが違うので棟高は従属値になる(下の表を実測で刷る)。**指図の ridgeH は
    スパン依存であることを書き足すか、長屋にだけ効く値だと明記するのが要る。**

【向き(Unity 座標)】幅=X(桁行)/ 高さ=Y / 厚み=Z。**+Z = 開口面(指図で言う東・山側)**、
  **−Z = 盲面(水側・西)**。⚠ 見え面の規約(+Z)に従うと、盲面ではなく**開口面が +Z** になる。
  据えるときは +Z を山側へ向けること(水側へ向けると盲面の意味が反転する)。
  ピボット = **footprint の中心・地盤レベル**(service の (u0..u1, v0..v1) 矩形の中心をそのまま使える)。
  ⚠ 軒は footprint の外へ ±Z に `nokiOut`、±X に `END` 出る。**ピボットには含めない。**

【材 — 新規マテリアルを作らない】
  `wood`(Village Kit `column A`)/ `wall C`(同 漆喰)/ `Foundation_A_01`(同 基壇の石)
  / `roof`(同 `roof 2x2` の桟瓦)。すべてキットの材質名なので Unity 側の remap で当たる。

【落とし穴】
  ・**下見板を板1枚で貼らない。**重ねた横板を実体で積んで目地の影を出す(`vkmesh.shitami`)。
    渋墨・漆喰は明暗が乏しいのでテクスチャでは継ぎ目が出ない(板戸で 2026-08-31 に踏んだ)。
  ・屋根は **軒先ではなく軒桁の線で壁の天端に合わせる**。生成器のローカル z=0 は軒先なので、
    `eaveH − 軒の出×勾配` へ下ろす。軒先に合わせると壁の天端と屋根の間が 0.49m 開く
    (`build_matsudaira_dewa_fuzokuya.koya` は開き小屋なので開いたままでよかった)。
  ・けらば(妻の軒の出)の下は**裏板で塞ぐ**。塞がないと瓦の裏が透けて空が抜ける。
  ・袖瓦は **0.22 持ち上げて**通す(README)。入れないと瓦を切った断面と破風板の天端が白い筋になる。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as R

KEN  = 1.818
OUT  = os.path.join(V.REPO, "Assets", "Edo", "Models", "Nagaya")
SHOT = os.path.join(V.REPO, "Screenshots")

WOOD, WALL, STONE, SHOJI = 0, 1, 2, 3   # マテリアルスロットの番号(**必ずこの順**)
STONE_UV_FB = (0.05, 0.05, 0.45, 0.45)

NOKI   = 0.9        # 軒の出[m] — 指図 nishi.obi.nokiOut。⚠ 東の余地 4.0m の検査がこれを含む
END    = 0.30       # けらば(妻側)の出[m]【U — 指図に無い】
SEAT   = 0.13       # 大棟を瓦へ食い込ませる量(README)
BASE   = 0.20       # 基壇の高さ【U — 指図 nishi.obi「棟の下にだけ基壇(高さ=U)」】
KOSHI  = 1.10       # 下見板の腰の天端[m]【U】
POST   = 0.14       # 柱の見付・見込(四寸五分角)【U】
UCHINORI = 1.95     # 建具の内法高[m]【U】
LAST = {'hd': 0.0}  # 直近に組んだ躯体の半奥行(軒の出の実測に使う)


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


# ---------------------------------------------------------------- 材
def palette():
    """(材, UV矩形) を Village Kit から借りる。**新規マテリアルを作らない**"""
    wood = V.borrow_material("Walls and floors/column A.fbx", "wood")
    wall = V.borrow_material("Walls and floors/wall C.fbx", "wall C")
    stone, suv = VM.vk_mat(V, "Foundations/Foundation_A_01_2x2.fbx",
                           "Foundation_A_01", STONE_UV_FB)
    # 明かり障子の紙。⚠ `wall A` はキットに .mat とテクスチャがあるのに**どのメッシュも
    #   使っていない**ので、名前だけスロットを立てる(remap は名前一致で当たる)。
    #   README の「襖紙は wall A の左半分(u 0.045..0.275)の無地の紙面」に倣う
    shoji = V.named_material("wall A")
    return {'wood': wood, 'wall': wall, 'stone': stone, 'shoji': shoji,
            'juv': (0.055, 0.10, 0.265, 0.90),
            # 一点貼りにしない。R.WOOD_UV は木理が縦に流れる既知の良品
            'wuv': R.WOOD_UV, 'cuv': R.WALLC_UV, 'suv': suv}


# ---------------------------------------------------------------- 面の部品
def hboard(m, P, a0, a1, y0, y1, t0, t1, along, rect):
    """横板1枚。**見える面(外側)だけ木理を板の長手へ流す**。
    ⚠ `Mesh.box` は u=第1軸・v=第2軸に固定なので、長い横板に**縦木理**が乗って
      下見板が「縦縞の平板」に見えた(2026-09-04 に実見)。外面だけ `quad_uvs` で出す。"""
    u0, v0, u1, v1 = rect
    if along == 'x':
        m.box(a0, a1, y0, y1, t0, t1, rect, WOOD)
        pts = [(a0, y0, t1), (a1, y0, t1), (a1, y1, t1), (a0, y1, t1)]
    else:
        m.box(t0, t1, y0, y1, a0, a1, rect, WOOD)
        pts = [(t1, y0, a0), (t1, y0, a1), (t1, y1, a1), (t1, y1, a0)]
    # 長手 → v(木理)/ 板幅 → u。巻き順は box の外面と同じにしてある
    m.quad_uvs(pts, [(u0, v0), (u0, v1), (u1, v1), (u1, v0)], WOOD)


def shitami(m, P, a0, a1, y0, y1, plane, out, along, pitch=0.19):
    """下見板張り(南京下見)を1面に張る。along='x' なら面は 厚み=plane、
    along='z' なら面は 走り=plane。out=+1/−1 が外向き。
    ⛔ **板1枚で貼らない。**重ねた横板を実体で積んで、目地の影で下見板だと分からせる。
    ⛔ **1枚を面いっぱいに伸ばさない。**板継ぎを 1.2m ごとに入れ、継ぎごとに UV の帯を
      変える — でないとアトラスが横方向へ引き伸ばされて木目が溶ける。"""
    n = max(1, int(round((y1 - y0) / pitch)))
    h = (y1 - y0) / n
    L = a1 - a0
    nc = max(1, int(round(L / 1.2)))
    for i in range(n):
        a = y0 + i * h
        for c in range(nc):
            c0, c1 = a0 + L * c / nc, a0 + L * (c + 1) / nc
            band = ((i * 3 + c) % 4) * 0.23
            rect = VM.sub(P['wuv'], 0.04, band, 0.96, band + 0.23)
            # 身(壁から 0.030)と 下端(0.075 出て下の板に被さる = 南京下見の影)
            for (ylo, yhi, d) in ((a + h * 0.26, a + h, 0.030), (a, a + h * 0.26, 0.075)):
                t0, t1 = sorted((plane, plane + out * d))
                if out > 0:
                    hboard(m, P, c0, c1, ylo, yhi, t0, t1, along, rect)
                else:
                    # 外面が t0 側になるので、板の向きを保ったまま鏡に取る
                    hboard(m, P, c0, c1, ylo, yhi, t1, t0, along, rect)


def mizukiri(m, P, a0, a1, y, plane, out, along):
    """下見板の天端に打つ水切り。無いと板の小口が切れっぱなしで出る"""
    uv = VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80)
    lo, hi = sorted((plane - out * 0.02, plane + out * 0.085))
    if along == 'x':
        m.box(a0, a1, y - 0.02, y + 0.07, lo, hi, uv, WOOD)
    else:
        m.box(lo, hi, y - 0.02, y + 0.07, a0, a1, uv, WOOD)


def plaster(m, P, a0, a1, y0, y1, plane, out, along, t=0.10):
    """真壁の漆喰。柱の面より 0.03 引っ込めて見付けの影を出す"""
    uv = VM.sub(P['cuv'], 0.02, 0.02, 0.98, 0.98)
    lo, hi = sorted((plane - out * 0.03, plane - out * (0.03 + t)))
    if along == 'x':
        m.box(a0, a1, y0, y1, lo, hi, uv, WALL)
    else:
        m.box(lo, hi, y0, y1, a0, a1, uv, WALL)


def posts(m, P, xs, y0, y1, plane, out, along):
    """柱(真壁で見えるほう)。走りに沿って xs の位置に立てる"""
    uv = VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98)
    for a in xs:
        lo, hi = sorted((plane, plane - out * POST))
        if along == 'x':
            m.box(a - POST / 2, a + POST / 2, y0, y1, lo, hi, uv, WOOD)
        else:
            m.box(lo, hi, y0, y1, a - POST / 2, a + POST / 2, uv, WOOD)


def door_leaves(m, P, x0, x1, y0, y1, plane, out, n=2):
    """板戸。n=2 は引違い(前後の溝に分ける)、n=1 は開き戸。
    ⚠ **同じ面に2枚置かない** — 重なり代が z-fighting する(建具の作法)。
    ⛔ 板1枚で出さない。竪板と桟を実体で起こして陰影で目地を出す。"""
    t = 0.035
    for k in range(n):
        # 引違いは前後にずらす。手前の溝が out 側
        off = 0.045 * (0 if n == 1 else (1 - k))
        z_out = plane - out * (0.06 + off)
        z_in = z_out - out * t
        lo, hi = sorted((z_out, z_in))
        w = (x1 - x0) / n
        a0 = x0 + k * w + (0.0 if n == 1 else -0.03 * (1 if k else -1))
        a1 = a0 + w
        m.box(a0, a1, y0, y1, lo, hi, VM.sub(P['wuv'], 0.62, 0.05, 0.80, 0.95), WOOD)
        # 竪板(見付 0.28)を起こす
        nb = max(1, int(round((a1 - a0) / 0.28)))
        for b in range(nb):
            bc = a0 + (a1 - a0) * (b + 0.5) / nb
            bw = (a1 - a0) / nb * 0.86
            pl, ph = sorted((z_out, z_out + out * 0.012))
            m.box(bc - bw / 2, bc + bw / 2, y0, y1, pl, ph,
                  VM.sub(P['wuv'], 0.58, 0.05, 0.72, 0.95), WOOD)
        # 桟(上・中・下)
        for fz in (0.10, 0.52, 0.94):
            yc = y0 + (y1 - y0) * fz
            sl, sh = sorted((z_out + out * 0.012, z_out + out * 0.040))
            m.box(a0, a1, yc - 0.055, yc + 0.055, sl, sh,
                  VM.sub(P['wuv'], 0.72, 0.10, 0.92, 0.40), WOOD)


def section(m, xa, xb, pts, uv, mat):
    """(厚み z, 高さ y) の4点断面を 走り xa..xb へ押し出す(破風板・妻壁・裏板)。
    ⚠ 4点固定 — Mesh は quad/tri しか積まないので n 角形は分けて渡すこと。"""
    A = [(xa, p[1], p[0]) for p in pts]
    B = [(xb, p[1], p[0]) for p in pts]
    m.quad(A, uv, mat)
    m.quad(B[::-1], uv, mat)
    for i in range(4):
        j = (i + 1) % 4
        m.quad([A[i], A[j], B[j], B[i]], uv, mat)


# ---------------------------------------------------------------- 屋根
def obi_roof(W, D, name, P, ridge_show=0.36, noki=NOKI):
    """切妻(桟瓦)。局所 z=0 は **軒先**、原点は footprint の中心。
    ⚠ `build_goten_roof.make_kirizuma` は使わない — 棟の寸法が渡廊下用に固定で、
      袖瓦も棟の小口の詰めも無い(渡廊下は端が棟の軒下に隠れるため要らなかった)。
      崖下の長屋は**妻が丸見え**なので、袖瓦と小口の詰めを自分で入れる。"""
    hw, hd = W / 2.0, D / 2.0
    x0, x1 = -hw - END, hw + END
    y0, y1 = -hd - noki, hd + noki
    h = (hd + noki) * R.RATIO                     # 軒先から大棟の瓦面まで
    RW = 0.42                                     # 大棟の幅
    RH = ridge_show + SEAT                        # 大棟モジュールの丈
    pieces = []
    pieces.append(R.tile_field([[(x0, y0), (x1, y0), (x1, 0.0), (x0, 0.0)]],
                               (x0, y0), 90, 0.0, name + "_S"))
    pieces.append(R.tile_field([[(x1, y1), (x0, y1), (x0, 0.0), (x1, 0.0)]],
                               (x0, y1), 270, 0.0, name + "_N"))
    # 大棟 — 熨斗の見え掛かりで棟高を合わせる(docstring の【⚠】参照)
    pieces += R.ridge((x0, 0.0, h - SEAT), (x1, 0.0, h - SEAT),
                      name + "_omune", w=RW, h=RH)
    # ⚠ **棟の小口を塞ぐ。** `roof top x1` は実測で **両端が開いている**
    #   (小口に向く面が 0 枚・境界の辺 22)。塞がないと妻から棟の中が透ける
    #   — 「端部材を忘れない。run の端で小口が透ける」(築地塀で実際に起きた型)。
    # ⭕ **棟端は漆喰で塗り籠める。**鬼を置かない切妻の棟端の常法で、
    #   材も既にある `wall C` で済む。
    #   ⚠ 瓦の材(`roof`)で塞ごうとして2度失敗した — `roof` のアトラスは
    #     瓦と木部(野地・垂木)が同居していて、最大面でも「上向きの最大面」でも
    #     木の帯に落ち、棟端が**木の箱**に見えた(2026-09-04)。
    for sx, sg in ((x0, -1), (x1, 1)):
        # 棟の断面は角の丸い熨斗の積みなので、**外形より一回り小さい詰め**を内側へ。
        # bbox いっぱいの箱にすると角が棟の輪郭からはみ出す
        c = V.box(name + ("_capA" if sg < 0 else "_capB"),
                  (0.06, RW * 0.80, RH * 0.76),
                  (sx - sg * 0.04, 0.0, h - SEAT + RH * 0.40), P['wall'])
        V.set_uv_rect(c, VM.sub(P['cuv'], 0.1, 0.1, 0.9, 0.9), axes=('y', 'z'))
        pieces.append(c)
    # 袖瓦(けらばの瓦の切り口と破風板の天端を覆う)。README のとおり持ち上げて通す。
    # ⚠ **大棟の脇で止める** — 棟まで通すと棟を跨いで空へ飛び出す(2026-09-04 に実見)
    for sx in (x0 + 0.06, x1 - 0.06):
        for s in (-1, 1):
            ye = s * (RW * 0.5 + 0.03)
            pieces += R.ridge((sx, s * (hd + noki), 0.20),
                              (sx, ye, h - abs(ye) * R.RATIO + 0.20),
                              name + "_sode", w=0.26, h=0.20)
    # ⛔ **鬼瓦は載せない。** 詰人長屋に鬼を上げると格が上がる(指図 roofs は
    #   表長屋と崖下で格を分けると宣言している)。棟端は上の小口の詰めで納める。
    V.dedup_materials()
    return V.join([p for p in pieces if p], name)


# ---------------------------------------------------------------- 躯体
def gable_set(m, P, hw, hd, eaveH, roofZ, apex, noki, end=None):
    """切妻の妻まわり(妻壁の三角・けらば裏板・破風板)を一式張る。
    棟門など他の切妻の部材からも呼ぶので関数にしてある。"""
    end = END if end is None else end
    # ---- 妻壁(三角)。**底辺は軒桁の線** — 屋根はここで壁の天端に合わせてある
    for sx, inward in ((-hw, +1), (hw, -1)):
        tri_uv = VM.sub(P['cuv'], 0.05, 0.05, 0.95, 0.95)
        for s in (-1, 1):
            # (厚み, 高さ) の4点。頂点側は棟で潰した細い四角形として渡す
            pts = [(s * hd, eaveH), (s * 0.02, apex - 0.02 * R.RATIO),
                   (0.0, apex), (0.0, eaveH)]
            section(m, sx, sx + inward * 0.10, pts, tri_uv, WALL)

    # ---- けらば裏板(妻の軒の出の下)。塞がないと瓦の裏から空が抜ける
    for sx, inward in ((-hw, +1), (hw, -1)):
        for s in (-1, 1):
            pts = [(0.0, apex), (s * (hd + noki), roofZ),
                   (s * (hd + noki), roofZ - 0.05), (0.0, apex - 0.05)]
            section(m, sx, sx - inward * end, pts,
                    VM.sub(P['wuv'], 0.05, 0.05, 0.95, 0.45), WOOD)

    # ---- 破風板。**板の 45% を屋根面より上へ出す**(README の drop=0.55)。
    #      低いと天端を瓦の波形が食って、木ではありえない縁になる
    BW, BT, UP = 0.30, 0.055, 0.55   # 破風板: 幅 / 見付 / 屋根面より上へ出す割合
    for sx, inward in ((-hw - end, +1), (hw + end, -1)):
        for s in (-1, 1):
            nz, ny = s * R.RATIO, 1.0
            L = math.hypot(nz, ny)
            nz, ny = nz / L, ny / L
            A = (0.0, apex)
            B = (s * (hd + noki), roofZ)
            pts = [(A[0] + nz * BW * UP, A[1] + ny * BW * UP),
                   (B[0] + nz * BW * UP, B[1] + ny * BW * UP),
                   (B[0] - nz * BW * (1 - UP), B[1] - ny * BW * (1 - UP)),
                   (A[0] - nz * BW * (1 - UP), A[1] - ny * BW * (1 - UP))]
            section(m, sx, sx + inward * BT, pts,
                    VM.sub(P['wuv'], 0.60, 0.02, 0.78, 0.98), WOOD)
    return m


def build(wKen, dKen, name, eaveH=2.70, ridge_show=0.36, plan=None,
          koshiH=KOSHI, noki=NOKI):
    """plan = 開口面(+Z)の割付 [(x0, x1, 'door'|'window'), ...](走りの中心が 0)"""
    P = palette()
    W, D = wKen * KEN, dKen * KEN
    hw, hd = W / 2.0, D / 2.0
    roofZ = eaveH - noki * R.RATIO                # 屋根の軒先レベル(軒桁の線で壁天端に合う)
    apex = roofZ + (hd + noki) * R.RATIO          # 瓦面の大棟
    plan = plan or []
    LAST['hd'] = hd
    m = VM.Mesh()

    # ---- 基壇(玉石を均した低い壇)。⛔ 高床にしない(指図 nishi.obi.sahou)
    m.box(-hw - 0.13, hw + 0.13, 0.0, BASE, -hd - 0.13, hd + 0.13,
          VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)

    # ---- 柱の位置(1間ピッチ + 開口の見付)
    npost = int(round(wKen)) + 1
    xs = [-hw + W * i / float(max(1, npost - 1)) for i in range(npost)]
    for (a, b, _k) in plan:
        xs += [a - POST / 2 - 0.005, b + POST / 2 + 0.005]
    xs = sorted(set(round(x, 4) for x in xs))

    # ---- 盲面(−Z・水側)と両妻(±X)。開口を一切あけない
    shitami(m, P, -hw, hw, BASE, koshiH, -hd, -1, 'x')
    mizukiri(m, P, -hw, hw, koshiH, -hd, -1, 'x')
    plaster(m, P, -hw, hw, koshiH, eaveH, -hd, -1, 'x')
    posts(m, P, xs, koshiH, eaveH, -hd, -1, 'x')
    for sx in (-hw, hw):
        s = 1 if sx > 0 else -1
        shitami(m, P, -hd, hd, BASE, koshiH, sx, s, 'z')
        mizukiri(m, P, -hd, hd, koshiH, sx, s, 'z')
        plaster(m, P, -hd, hd, koshiH, eaveH, sx, s, 'z')
        posts(m, P, [-hd + 0.25, 0.0, hd - 0.25], koshiH, eaveH, sx, s, 'z')

    # ---- 開口面(+Z・山側)
    segs, cur = [], -hw
    for (a, b, k) in sorted(plan):
        if a > cur + 1e-6:
            segs.append((cur, a, 'wall'))
        segs.append((a, b, k))
        cur = b
    if cur < hw - 1e-6:
        segs.append((cur, hw, 'wall'))
    if not segs:
        segs = [(-hw, hw, 'wall')]
    for (a, b, k) in segs:
        if k == 'wall':
            shitami(m, P, a, b, BASE, koshiH, hd, 1, 'x')
            mizukiri(m, P, a, b, koshiH, hd, 1, 'x')
            plaster(m, P, a, b, koshiH, eaveH, hd, 1, 'x')
        elif k == 'window':
            # 腰高窓 — 腰は下見板のまま、上に小壁
            shitami(m, P, a, b, BASE, koshiH, hd, 1, 'x')
            plaster(m, P, a, b, UCHINORI, eaveH, hd, 1, 'x')
            m.box(a, b, koshiH, koshiH + 0.09, hd - 0.02, hd + 0.07,
                  VM.sub(P['wuv'], 0.45, 0.10, 0.90, 0.35), WOOD)       # 窓台
            m.box(a, b, UCHINORI - 0.09, UCHINORI, hd - 0.02, hd + 0.07,
                  VM.sub(P['wuv'], 0.45, 0.40, 0.90, 0.65), WOOD)       # 無目
            # ⛔ 板を1枚貼らない。竪子を実体で並べる
            # ⛔ **格子だけにしない。**裏に明かり障子を入れないと窓が素通しになり、
            #   建物の中と反対側の壁の裏面が見える(2026-09-04 に実見)
            m.box(a + 0.02, b - 0.02, koshiH + 0.08, UCHINORI - 0.08, hd - 0.115, hd - 0.085,
                  VM.sub(P['juv'], 0.05, 0.05, 0.95, 0.95), SHOJI)
            m.koshi(a + 0.03, b - 0.03, koshiH + 0.09, UCHINORI - 0.09, hd - 0.05, hd + 0.02,
                    VM.sub(P['wuv'], 0.60, 0.10, 0.95, 0.90), WOOD,
                    pitch=0.115, bar=0.026, yoko=2)
        else:                                     # door
            plaster(m, P, a, b, UCHINORI, eaveH, hd, 1, 'x')            # 戸の上の小壁
            m.box(a - 0.04, b + 0.04, BASE, BASE + 0.08, hd - 0.06, hd + 0.09,
                  VM.sub(P['wuv'], 0.30, 0.10, 0.80, 0.30), WOOD)       # 敷居
            m.box(a - 0.04, b + 0.04, UCHINORI - 0.09, UCHINORI, hd - 0.06, hd + 0.09,
                  VM.sub(P['wuv'], 0.30, 0.40, 0.80, 0.60), WOOD)       # 鴨居
            door_leaves(m, P, a, b, BASE + 0.06, UCHINORI - 0.05, hd, 1,
                        n=(1 if (b - a) < 1.2 else 2))

    # ---- 柱(開口面)と軒桁・妻梁
    posts(m, P, xs, koshiH, eaveH, hd, 1, 'x')
    for s in (-1, 1):
        m.box(-hw - 0.05, hw + 0.05, eaveH - 0.19, eaveH, s * hd - s * 0.17, s * hd,
              VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.45), WOOD)
    for s in (-1, 1):
        m.box(s * hw - s * 0.17, s * hw, eaveH - 0.19, eaveH, -hd, hd,
              VM.sub(P['wuv'], 0.20, 0.50, 0.95, 0.80), WOOD)

    gable_set(m, P, hw, hd, eaveH, roofZ, apex, noki)

    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    roof = obi_roof(W, D, name + "_roof", P, ridge_show=ridge_show, noki=noki)
    roof.location = (0.0, 0.0, roofZ)
    bpy.context.view_layer.update()
    V.sel([roof])
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    V.dedup_materials()
    o = V.join([body, roof], name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print("[obi] %-22s 軒桁 %.2f / 瓦の大棟 %.3f / 棟天端(実測は下)" % (name, eaveH, apex))
    return o


# ---------------------------------------------------------------- 部材
def sumai_plan(wKen, dKen):
    """詰人長屋の割付 — 2.5間で1戸(引戸1間 + 腰高窓1間 + 見付)。
    ⚠ **戸数は指図に無い(確度U)。**指図 nishi.obi は『詰人の人数の典拠は当プロジェクトに
      無く、世帯数は書かない』としているので、ここも**割付の型**として置くだけで、
      戸数を史実として名乗らせない。"""
    W = wKen * KEN
    n = max(1, int(round(wKen / 2.5)))
    unit = W / n
    pad = (unit - 2 * KEN) / 3.0
    plan = []
    for i in range(n):
        s = -W / 2.0 + i * unit
        plan.append((s + pad, s + pad + KEN, 'door'))
        plan.append((s + 2 * pad + KEN, s + 2 * pad + 2 * KEN, 'window'))
    return plan


def nagaya(wKen=7.5, dKen=2.5, name=None):
    """詰人長屋(N1/N2)。7.5間 × 2.5間・平屋・桟瓦・下見板腰・**水側は盲面**"""
    name = name or ("Obi_Nagaya_%sx%sken" % (fmt(wKen), fmt(dKen)))
    return build(wKen, dKen, name, eaveH=2.70, ridge_show=0.36,
                 plan=sumai_plan(wKen, dKen)), name


def monooki(wKen=3.0, dKen=1.5, name=None):
    """物置(M1)。3間 × 1.5間・**開口1**(両開きの板戸)。長屋と同じ作り"""
    name = name or ("Obi_Monooki_%sx%sken" % (fmt(wKen), fmt(dKen)))
    W = wKen * KEN
    plan = [(-KEN, KEN, 'door')]                  # 中央に2間の板戸(両開き)
    # ⚠ 軒の出は 0.75【U】。指図の 0.9 は帯の東の余地の検査が長屋について測る値で、
    #   1.5間の小屋に 0.9 を出すと屋根が躯体の 2 倍近くになる(実見して下げた)
    return build(wKen, dKen, name, eaveH=2.70, ridge_show=0.36, plan=plan, noki=0.75), name


def kawaya(wKen=1.0, dKen=1.0, name=None):
    """かわや(K_Obi)。1間角・**戸1**。⚠ 軒高は 2.20【U — 指図に無い】。
    2.70 のまま建てると1間角の塔になるので下げた。西面には Unity 側で建仁寺垣が立つ
    (指図 nishi.obi.fences)ので、こちらには目隠しを作り付けない。"""
    name = name or ("Obi_Kawaya_%sken" % fmt(wKen))
    plan = [(-0.43, 0.43, 'door')]
    return build(wKen, dKen, name, eaveH=2.20, ridge_show=0.24,
                 plan=plan, koshiH=0.95, noki=0.60), name


PARTS = {"nagaya": nagaya, "monooki": monooki, "kawaya": kawaya}


# ---------------------------------------------------------------- レンダ
def shots(o, key):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox([o])
    c = (mn + mx) * 0.5
    r = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    H = mx.z - mn.z
    # ① 開口面の立面。⚠ 厚みを反転して出しているので **表は Blender の −Y**
    # ⚠ ortho_scale は**幅と高さの大きいほう**から出す。幅だけで決めると
    #   1間角の小屋のように背の高い部材が枠から溢れる(2026-09-04 に踏んだ)
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=max(mx.x - mn.x, H) * 1.18, res=(1700, 1100))
    V.render(os.path.join(SHOT, "obi_%s_elev.png" % key))
    # ①' 妻の正面立面 — **妻壁が塞がっているか**をここで見る(斜めだと判断できない)
    V.studio((mn.x - r * 2.2, c.y, c.z), (c.x, c.y, c.z),
             ortho_scale=max(mx.y - mn.y, H) * 1.18, res=(1400, 1100))
    V.render(os.path.join(SHOT, "obi_%s_gable.png" % key))
    # ② 開口面を斜め前から(人の目の高さ)— 建具・下見板・軒の出を見る
    V.studio((mn.x - r * 0.6, mn.y - r * 1.1, 1.65), (c.x, c.y, H * 0.45), res=(1700, 1000))
    V.render(os.path.join(SHOT, "obi_%s_3d.png" % key))
    # ③ 盲面(水側)を斜めから — **開口が漏れていないか**をここで見る
    V.studio((mx.x + r * 0.6, mx.y + r * 1.1, 1.9), (c.x, c.y, H * 0.45), res=(1700, 1000))
    V.render(os.path.join(SHOT, "obi_%s_ura.png" % key))
    # ④ 妻の寄り — 破風・袖瓦・けらば裏板・妻壁の納まり
    V.studio((mn.x - r * 0.75, mn.y - r * 0.75, H * 1.05), (mn.x + r * 0.25, c.y, H * 0.72),
             res=(1500, 1100))
    V.render(os.path.join(SHOT, "obi_%s_tsuma.png" % key))
    # ④' 開口の寄り(戸1つ+窓1つ)— 建具・敷居・鴨居・腰の納まりをここで見る
    V.studio((c.x - (mx.x - mn.x) * 0.18, mn.y - 6.5, 1.6),
             (c.x - (mx.x - mn.x) * 0.18, c.y, 1.35),
             ortho_scale=5.6, res=(1500, 1000))
    V.render(os.path.join(SHOT, "obi_%s_madoguchi.png" % key))
    # ⑤ 棟の寄り(上から)— 大棟・鬼・瓦の段が通っているか
    V.studio((c.x, mn.y - r * 0.55, H + r * 0.5), (c.x, c.y, H * 0.9), res=(1500, 900))
    V.render(os.path.join(SHOT, "obi_%s_mune.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ken = None
    if "--ken" in argv:
        i = argv.index("--ken")
        ken = (float(argv[i + 1]), float(argv[i + 2]))
    want = [a for a in argv if not a.startswith("--")
            and a in PARTS] or list(PARTS.keys())
    for key in want:
        V.reset()
        fn = PARTS[key]
        o, name = fn(*(ken if ken else ()))
        mn, mx = V.bbox([o])
        print("[obi] %-24s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f   底=%.3f  面=%d"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons)))
        print("[obi] %-24s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
        # ⚠ **長手の軒の出は bbox から取れない**(妻の破風板が Z へ 0.08 出るので
        #   bbox は嘘をつく)。指図 nishi.obi.nokiOut=0.9 の検査が測るのはここなので、
        #   run の中ほどだけを見て実測する
        hw = (mx.x - mn.x) / 2.0
        ys = [(o.matrix_world @ v.co).y for v in o.data.vertices
              if abs((o.matrix_world @ v.co).x - (mn.x + mx.x) / 2.0) < hw * 0.35]
        if ys:
            print("[obi] %-24s 長手の軒の出(片側)= %.3f m  ← 指図 nokiOut と突き合わせる"
                  % (name, max(max(ys), -min(ys)) - LAST['hd']))
        path = os.path.join(OUT, name + ".fbx")
        V.export_fbx([o], path)
        print("[obi] 書き出し " + path)
        if "--render" in argv:
            shots(o, key)


if __name__ == "__main__":
    main()
