"""**類型共用の表店(おもてだな)** — 町屋24町の通りに面して並ぶ2階建ての商家。

    blender --background --python Tools/Blender/build_typ_machiya.py -- [--ken 5] [--okuyuki 7.27] [--render]
    blender --background --python Tools/Blender/build_typ_machiya.py -- narabe    # Shop01/02 と並べ比べ
    blender --background --python Tools/Blender/build_typ_machiya.py -- axis      # 軸の自己検査だけ

【なぜ新造するか】EDO-0348(2026-09-21)。類型ビルダーの表の `maguchi_ken` は **5間(9.09m)**
  なのに、在庫の表店は `Eg.Shop01` 軒幅 4.93m(2.71間)と `Eg.Shop02` 7.13m(3.92間)の
  2点しかなく、**1軒を1枚で埋める駒が無い**。いまは Shop01×2 = 9.86m(+0.77m)で継いでいる。
  ⛔ 非等方に引き伸ばして5間へ合わせない — 軒の出も格子の目も戸の幅も一緒に伸びる。
  ⇒ **桁行の割り付け(柱間・格子・戸)を5つに増やして**幅を取る。

【型は在庫の `Eg.Shop01`(ES=1.818 倍後 W4.926 × H4.250 × D4.031)】2026-09-21 に群ごとに実測:
  | 部位 | Shop01 実測 | この部材 |
  |---|---|---|
  | 1階庇 先端 / 頂 | 1.717 / 2.367 | **1.73 / 2.361** |
  | 店先の柱の天端 | 1.703 | **1.88** |
  | 2階の窓 | 2.405〜2.874 | **2.40〜2.87** |
  | 2階の軒先 | 3.337 | **3.35** |
  | 瓦面の大棟 / 棟天端 | 4.052 / 4.236 | **4.050 / 4.240** |
  | 妻の軒の出(けらば) | 0.109〜0.164 | **0.11** |
  | 暖簾 | 1.392〜1.656 | **1.40〜1.65** |
  ⭐ **軒先・棟天端・けらばが Shop01 と一致する** ⇒ `MachiyaRun` が同じ列へ継いでも
    屋根がめり込まず、棟の段も出ない。

【なぜ段違いの2棟か】Shop01 の奥行は **2間**(躯体 Z −1.60..+2.01)しかない。5間の表店に要る
  **4間(7.27m)** を1枚の切妻で架けると、瓦の勾配 0.5456 では棟天端が **5.4m** まで上がり
  Shop01 より 1.2m 高くなる(勾配を 0.19 まで寝かせれば高さは合うが、それは瓦屋根に見えない)。
  ⇒ **表屋(厨子二階)+ 奥(平屋)の段違い**に割った。4間級の町屋の実際の作りでもある。
  ⚠ 奥棟の前流れは表屋の裏壁へ**谷**で突き当たる(町屋が表屋と奥の間に坪庭を取るのは
    この谷があるため)。⛔ 谷は**雨押えの板で塞ぐ** — 塞がないと折れ目が管になって空が抜ける。

【向き(Unity 座標)】幅=X(桁行・通りに沿う)/ 高さ=Y / 厚み=Z。**+Z = 通り(店先)**。
  ピボット = **足形の中心・地盤レベル**(Y=0 が地面)。⚠ 軒は足形の外へ ±X に 0.11 出る。
  ⚠ **大戸口(出入口)は Unity −X 寄りの1間**、残り4間が見世(格子 + 見世棚)。
    左右非対称なので、据えるときの yaw で大戸口の位置が変わる。

【寸法【U — 指図に欄が無い。部材方が決めた】】
  ・桁行 5間(`--ken`)・奥行 4間相当 7.272m(`--okuyuki`)。1間ごとに柱を立てて割る。
  ・表屋 = **厨子二階**(2階の内法が低い江戸の町屋の型)/ 奥 = 平屋。
  ・奥行を詰めると **奥棟だけが縮む** — 表の立面・軒高・棟高・けらばは一切動かない。

【材】⛔ 新規に作らない。倣った先(岡部の長屋・御殿の瓦)の材質名をそのまま運ぶ —
  `wood` / `wall C` / `Foundation_A_01` / `wall A` / `roof` / `roof ornaments`。
  ⚠ `Eg.Shop01` の材 `shop01map` は **借りられない** — edogoyomi の obj に埋め込まれた材で
    `.mat` 資産が無く、remap の借り先に出てこない。

【⛔ 踏んだ罠(この部材で直したもの)】
  ・`VM.Mesh.box` は **Unity X = −走り**。左右非対称なので立面レンダでは気づけない
    ⇒ `rr()` を必ず通し、`axis` で写像を**焼いて**確かめてから組む。
  ・`m.box` に **z0 > z1 を渡すと面が全部内向き**になる(Unity では消える)。
    `OB.shitami` は out<0 でそう呼ぶので、躯体は **焼く前に法線を取り直す**(`_recalc`)。
  ・`clip_convex` の bisect は**孤立頂点を残す** ⇒ 測る前に掃除する(`_clean_loose`)。
"""
import bpy, sys, os, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as R
import build_obi_nagaya as OB

KEN  = 1.818
OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Machiya"))
SHOT = os.path.join(V.REPO, "Screenshots")

WOOD, WALL, STONE, SHOJI = OB.WOOD, OB.WALL, OB.STONE, OB.SHOJI

# ── 立面の高さ【Shop01 の実測から】────────────────────────────────
HIS_TIP_Y = 1.73      # 1階庇の先端
HIS_TOP_Y = 2.361     # 1階庇の頂(= 2階の壁に取り付く高さ)
KOBAI_H   = 0.344     # 1階庇の勾配(Shop01 実測 0.650/1.890)
EAVE2_TIP = 3.35      # 2階の軒先
WIN2_Y0, WIN2_Y1 = 2.40, 2.87   # 2階の窓
NOREN_Y0, NOREN_Y1 = 1.40, 1.65
TANA_Y    = 0.72      # 見世棚の天端
POST_TOP  = 1.88      # 店先の柱の天端(庇の裏へ 0.02 で納まる)
UCHI1     = 1.72      # 店先の建具の内法
KOSHI1    = 0.55      # 店先の腰板の天端
KOSHI_URA = 0.95      # 裏・妻の下見板腰の天端
NOKI      = 0.21      # 流れ方向の軒の出(Shop01 実測)
END       = 0.11      # けらば(妻の軒の出)。⛔ 広げると隣の駒と屋根がめり込む
SEAT      = 0.13      # 大棟を瓦へ食い込ませる量(README)
RIDGE_SHOW = 0.19     # 大棟の熨斗の見え掛かり ⇒ 棟天端 = 瓦面 + 0.19
BASE      = 0.08      # 土台石
D2F       = 2.146     # 表屋(2階)の躯体の奥行【従属値】— 棟天端を Shop01 の 4.24 に合わせる値
REAR_EAVE = 2.35      # 奥棟の軒桁(裏壁の通りでの屋根面)⚠ 上げると奥棟の棟が表屋の軒桁に迫る
MISE_OUT  = 0.50      # 庇の先端が店先の柱通りより前へ出る量
TANA_OUT  = 0.42      # 見世棚が柱通りより前へ出る量(⛔ MISE_OUT を超えない=足形からはみ出す)


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


# ═════════════════════════════ 軸の写像 ═════════════════════════════
# `VM.Mesh` の論理座標は (走り, 高さ, 厚み) で **Unity X = −走り / Y = 高さ / Z = +厚み**
#   (memory: logical-axis-and-mirror-checks)。屋根は Blender のオブジェクトを直に置くので
#   **Bx = −Ux / By = −Uz / Bz = Uy**。⛔ ここを通さずに座標を直に書かない。
def rr(a, b):
    """Unity X の区間 [a,b] → 論理走りの区間"""
    return (-b, -a)


def zz(a, b):
    """厚み(Unity Z)の区間を昇順にする。⛔ `m.box` に z0>z1 を渡すと面が内向きになる。"""
    return (a, b) if a <= b else (b, a)


def axis_check():
    """論理 → Unity の写像を**焼いて確かめる**(10秒)。⛔ 註から推論しない。"""
    m = VM.Mesh()
    a, b = rr(1.0, 2.0)
    m.box(a, b, 0.0, 1.0, 3.0, 4.0, (0, 0, 1, 1), 0)
    o = m.to_object("axis", [V.named_material("wood")])
    mn, mx = V.bbox([o])
    ux0, ux1, uz0, uz1 = -mx.x, -mn.x, -mx.y, -mn.y
    ok = (abs(ux0 - 1.0) < 1e-6 and abs(ux1 - 2.0) < 1e-6
          and abs(uz0 - 3.0) < 1e-6 and abs(uz1 - 4.0) < 1e-6)
    print("[machiya] 軸検査 Unity X %.3f..%.3f(期待 1..2)/ Y %.3f..%.3f(期待 0..1)/ "
          "Z %.3f..%.3f(期待 3..4)⇒ %s"
          % (ux0, ux1, mn.z, mx.z, uz0, uz1, "⭕" if ok else "⛔ 写像が違う"))
    return ok


def _recalc(o):
    """**法線を外向きに取り直す。** ⛔ 省かない — `OB.shitami` は out<0 のとき
    `m.box` に z0>z1 を渡すので、躯体の裏面・妻面の箱が**全部内向き**で焼ける
    (Blender の EEVEE は裏面も描くので**レンダでは気づけない**。Unity で消える)。"""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free(); o.data.update()


def _clean_loose(o):
    """孤立頂点を落とす。⚠ `clip_convex` の bisect は面の無い頂点を残すので、
    掃除しないと bbox が実形状より大きく出る(README「bisect は孤立頂点を残す」)。"""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    loose = [v for v in bm.verts if not v.link_faces]
    for v in loose:
        bm.verts.remove(v)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(loose)


# ═════════════════════════════ 屋根 ═════════════════════════════
def _tiles(ux0, ux1, uz_eave, uz_top, y_eave, kobai, name):
    """瓦場を1面。Unity Z が `uz_eave`(軒先)から `uz_top`(棟・取り付く先)へ上る面。
    ⭕ `_tile_field_k` は**瓦の形を変えずに面ごと傾ける**(⛔ z を縮めて勾配を作らない)。"""
    bx0, bx1 = -ux1, -ux0
    by_e, by_t = -uz_eave, -uz_top
    if by_t > by_e:
        yaw, poly = 90, [(bx0, by_e), (bx1, by_e), (bx1, by_t), (bx0, by_t)]
    else:
        yaw, poly = 270, [(bx1, by_e), (bx0, by_e), (bx0, by_t), (bx1, by_t)]
    return R._tile_field_k([poly], (bx0, by_e), yaw, y_eave, name, kobai)


def _ridge(ux0, ux1, uz, y_tile, name, show=RIDGE_SHOW):
    """大棟(キットの `roof top x1` を継ぐ)。y_tile = その位置の瓦面。"""
    return R.ridge((-ux1, -uz, y_tile - SEAT), (-ux0, -uz, y_tile - SEAT),
                   name, w=0.42, h=show + SEAT)


def _ridge_caps(P, ux0, ux1, uz, y_tile, name, show=RIDGE_SHOW):
    """棟の小口の詰め。⚠ `roof top x1` は**両端が開いている** — 塞がないと妻から棟の中が
    透ける(築地塀で踏んだ「run の端で小口が透ける」と同じ型)。
    ⭕ 鬼を置かない切妻の棟端は**漆喰で塗り籠める**のが常法。
    ⛔ 瓦の材(`roof`)で塞がない — アトラスの木部に落ちて棟端が木の箱に見える。"""
    out, RW, RH = [], 0.42, show + SEAT
    for k, (ux, sg) in enumerate(((ux0, -1), (ux1, 1))):
        c = V.box("%s_cap%d" % (name, k), (0.06, RW * 0.80, RH * 0.76),
                  (-ux + sg * 0.04, -uz, y_tile - SEAT + RH * 0.40), P['wall'])
        V.set_uv_rect(c, VM.sub(P['cuv'], 0.1, 0.1, 0.9, 0.9), axes=('y', 'z'))
        out.append(c)
    return out


SODE_W, SODE_IN, SODE_UP = 0.22, 0.05, 0.20
SODE_TRIM = 0.26      # 大棟の脇で袖瓦を止める量(Z)


def _sode(ux0, ux1, prof, name):
    """袖瓦(けらばの瓦の切り口と破風板の天端を覆う)。README のとおり **0.20 持ち上げて**通す。
    入れないと瓦を切った断面と破風板の天端が白い筋になる。prof = [(Uz, Uy), ...] 屋根面の稜線。

    ⚠⚠ **大棟の脇で止める** — 棟まで通すと棟を跨いで空へ飛び出す(obi_nagaya が
      2026-09-04 に実見した罠。⛔ この部材でも初回は丈が 4.43 に膨らんで捕まえた)。
      ⇒ prof の**内側の点(=棟)は前後とも `SODE_TRIM` だけ手前で切る**。"""
    out = []
    for ux in (ux0 + SODE_IN, ux1 - SODE_IN):
        for i in range(len(prof) - 1):
            (z0, y0), (z1, y1) = prof[i], prof[i + 1]
            dz = z1 - z0
            if abs(dz) < 1e-9:
                continue
            k = (y1 - y0) / dz                       # この面の勾配(Z あたりの Y)
            if i > 0:                                # 手前の端が棟 ⇒ 切る
                z0 += SODE_TRIM * (1 if dz > 0 else -1); y0 -= SODE_TRIM * abs(k)
            if i < len(prof) - 2:                    # 奥の端が棟 ⇒ 切る
                z1 -= SODE_TRIM * (1 if dz > 0 else -1); y1 -= SODE_TRIM * abs(k)
            out += R.ridge((-ux, -z0, y0 + SODE_UP), (-ux, -z1, y1 + SODE_UP),
                           name + "_sode", w=SODE_W, h=SODE_UP)
    return out


def rake(m, P, hw, prof, end=END):
    """妻の**けらば裏板と破風板**を両側に張る。prof = [(Uz, Uy), ...] 屋根面の稜線。
    ⛔ 裏板を省かない — 瓦の裏から空が抜ける。
    ⚠ 破風板は板の 55% を屋根面より上へ出す(README の drop=0.55)。低いと天端を
      瓦の波形が食って、木ではありえない縁になる。"""
    BW, BT, UP = 0.26, 0.05, 0.55
    for s in (-1, 1):                          # Unity X の側
        xa = -s * hw                           # 壁の通り(論理走り)
        xb = -s * (hw + end)                   # けらばの外端
        for i in range(len(prof) - 1):
            (z0, y0), (z1, y1) = prof[i], prof[i + 1]
            OB.section(m, xa, xb, [(z0, y0), (z1, y1), (z1, y1 - 0.05), (z0, y0 - 0.05)],
                       VM.sub(P['wuv'], 0.05, 0.05, 0.95, 0.45), WOOD)
            nz, ny = (y1 - y0), -(z1 - z0)     # 屋根面の法線(上向きに正規化)
            L = math.hypot(nz, ny)
            if L < 1e-6:
                continue
            nz, ny = nz / L, ny / L
            if ny < 0:
                nz, ny = -nz, -ny
            q = [(z0 + nz * BW * UP, y0 + ny * BW * UP),
                 (z1 + nz * BW * UP, y1 + ny * BW * UP),
                 (z1 - nz * BW * (1 - UP), y1 - ny * BW * (1 - UP)),
                 (z0 - nz * BW * (1 - UP), y0 - ny * BW * (1 - UP))]
            OB.section(m, xb, xb + s * BT, q,
                       VM.sub(P['wuv'], 0.60, 0.02, 0.78, 0.98), WOOD)


# ═════════════════════════════ 立面の部品 ═════════════════════════════
def koshi_mado(m, P, ux0, ux1, y0, y1, uz, out, pitch=0.105, back='shoji'):
    """格子窓。⛔ 板を1枚貼らない(竪子を実体で並べる)。
    ⛔ 格子だけにしない — 裏に塞ぎを入れないと素通しになり、建物の中と
      反対側の壁の裏面が見える(岡部の長屋で 2026-09-04 に実見)。

    ⚠ `back` は **店先だけ 'dark'**(見世の土間の暗がり)。2026-09-21 に在庫の表店と
      並べて焼いたら、白い明かり障子を店先の格子の裏に入れたせいで**5間ぜんぶが
      白い箱の列**に見え、閉め切った家に読めた(`Eg.Shop01` の店先は暗い)。
      ⛔ 2階は 'shoji' のまま — 2階の窓の裏は居室で、紙が正しい。"""
    a, b = rr(ux0, ux1)
    if back == 'dark':
        uv, mat = VM.sub(P['wuv'], 0.62, 0.05, 0.80, 0.95), WOOD
    else:
        uv, mat = VM.sub(P['juv'], 0.05, 0.05, 0.95, 0.95), SHOJI
    m.box(a + 0.02, b - 0.02, y0 + 0.02, y1 - 0.02,
          *zz(uz - out * 0.115, uz - out * 0.085), uv=uv, mat=mat)
    m.koshi(a + 0.03, b - 0.03, y0 + 0.03, y1 - 0.03,
            *zz(uz - out * 0.05, uz + out * 0.02),
            uv=VM.sub(P['wuv'], 0.60, 0.10, 0.95, 0.90), mat=WOOD,
            pitch=pitch, bar=0.024, yoko=2)
    for yy, uv in ((y0, (0.45, 0.10, 0.90, 0.35)), (y1 - 0.08, (0.45, 0.40, 0.90, 0.65))):
        m.box(a, b, yy, yy + 0.08, *zz(uz - out * 0.02, uz + out * 0.07),
              uv=VM.sub(P['wuv'], *uv), mat=WOOD)


def tategu(m, P, ux0, ux1, y_sill, y_head, uz, out, n=2):
    """敷居・鴨居 + 戸(引違い / 片開き)。⛔ 板1枚で出さない(`OB.door_leaves` が
    竪板と桟を実体で起こす)。"""
    a, b = rr(ux0, ux1)
    for (y, uv) in ((y_sill, (0.30, 0.10, 0.80, 0.30)), (y_head - 0.09, (0.30, 0.40, 0.80, 0.60))):
        m.box(a - 0.04, b + 0.04, y, y + 0.09, *zz(uz - out * 0.06, uz + out * 0.09),
              uv=VM.sub(P['wuv'], *uv), mat=WOOD)
    OB.door_leaves(m, P, a, b, y_sill + 0.06, y_head - 0.05, uz, out, n=n)


NOREN_MOD = "Props/Noren C.fbx"       # 実測(×0.909 後)W1.782 × H0.427 × D0.020・材 `Noren`
NOREN_MOD_W = 1.782


def noren_bar(m, P, ux0, ux1, uz, out):
    """暖簾竿(暖簾を吊る横木)。布そのものは `kit_noren` がキットのメッシュを掛ける。"""
    a, b = rr(ux0, ux1)
    m.box(a, b, NOREN_Y1, NOREN_Y1 + 0.05, *zz(uz + out * 0.05, uz + out * 0.10),
          uv=VM.sub(P['wuv'], 0.30, 0.10, 0.80, 0.30), mat=WOOD)


def kit_noren(bays, uz, name):
    """**キットの暖簾メッシュ**(`Props/Noren C.fbx`・材 `Noren`)を柱間ごとに1枚掛ける。
    ⛔ 箱に `wall A` を貼って暖簾に見せない — 2026-09-21 にそれで焼いたら
      障子と同じ白い板になって**立面から消えた**(在庫に本物の暖簾がある)。
    ⚠ 等方に縮めるだけ(柱間の 92%)。⛔ 非等方に伸ばさない — 紺地の柄が伸びる。"""
    from mathutils import Vector
    out = []
    for (a, b) in bays:
        sc = V.S * ((b - a) * 0.92 / NOREN_MOD_W)
        objs = V.place(NOREN_MOD, 0, 0, 0, scale=sc)
        if not objs:
            continue
        mn, mx = V.bbox(objs)
        w, h, d = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
        cx = (a + b) / 2.0
        t = Vector((-(cx + w / 2.0) - mn.x, -(uz + 0.07) - d - mn.y, (NOREN_Y1 - h) - mn.z))
        for o in objs:
            o.location += t
        bpy.context.view_layer.update()
        V.sel(objs)
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        nb = V.join(objs, "%s_noren%d" % (name, len(out)))
        # ⭐ 材を **`Noren 2`**(キットの藍色)へ差し替える。⛔ 新規マテリアルではない —
        #   キットに `Noren 2.mat`(_ColorB 0.30/0.36/0.61 = 藍)が在り、remap が当てる。
        #   既定の `Noren.mat` は _ColorB が茶で、在庫の表店の紺暖簾と色が揃わない。
        #   ⚠ Blender のレンダでは白いまま(アルベドは無地の布で、色は Unity の .mat が乗せる)。
        nb.data.materials.clear()
        nb.data.materials.append(V.named_material("Noren 2"))
        out.append(nb)
    return out


def misedana(m, P, ux0, ux1, uz, out):
    """**見世棚**(店先の低い台)。⭐ Shop01 の `dai` は床の高まりで、前へ突き出す棚が無い —
    これが在庫の表店に無い意匠で、5間の表店を「商家」に見せる要。
    棚板 + 持ち送り + 前脚(ばったり床几の作り)。⛔ 足形(Z)からはみ出さない。"""
    a, b = rr(ux0, ux1)
    lo, hi = zz(uz, uz + out * TANA_OUT)
    m.box(a, b, TANA_Y - 0.06, TANA_Y, lo, hi,
          VM.sub(P['wuv'], 0.05, 0.05, 0.95, 0.60), WOOD)                 # 棚板
    n = max(2, int(round((b - a) / 0.95)) + 1)
    for i in range(n):
        c = min(max(a + (b - a) * i / float(n - 1), a + 0.06), b - 0.06)
        m.box(c - 0.045, c + 0.045, 0.0, TANA_Y - 0.06, hi - 0.10, hi,
              VM.sub(P['wuv'], 0.12, 0.05, 0.30, 0.95), WOOD)             # 前脚
        m.box(c - 0.035, c + 0.035, TANA_Y - 0.30, TANA_Y - 0.06, lo, hi,
              VM.sub(P['wuv'], 0.12, 0.05, 0.30, 0.95), WOOD)             # 持ち送り


# ═════════════════════════════ 本体 ═════════════════════════════
# ⭐⭐ **`wKen` / `dM` は「軒の端から端」(= bbox)で、柱通りではない。**
#   `EdoBuild.ShopMeasure` は `FaceSpan(…, MinValue, MaxValue)` で**軒込みの端**を測り、
#   `MachiyaRun` はその幅をカーソルに積んで軒を接して並べる ⇒ **食う幅 = bbox**。
#   表の `maguchi_ken` 5間 を 1 枚で埋めるには **bbox の X を 9.09 ちょうど**にする要がある。
#   ⇒ 柱通りは bbox からせり出し分を引いた内側に取る(下の2定数)。
#   ⛔ 柱間を 1.818 固定にすると bbox が 9.45 になり、表の 5間 と 0.36m ずれる。
OVER_X = END + SODE_W / 2.0 - SODE_IN   # 袖瓦の外端が柱通りより外へ出る量
OVER_Z = 0.0805       # 軒瓦の唇が名目の軒先線より前へ出る量【実測】⚠ 瓦モジュール由来で動かせない


def build(wKen=5.0, dM=4.0 * KEN, name=None):
    """表店1軒。wKen = 桁行[間]、dM = 奥行[m]。**どちらも軒の端から端(bbox)**。"""
    name = name or ("Typ_Omotedana_%sken" % fmt(wKen))
    P = OB.palette()
    W = wKen * KEN
    hw, hd = W / 2.0 - OVER_X, dM / 2.0 - OVER_Z

    # ── Z の通り(Unity。+Z = 通り)────────────────────────────────
    HIS_TIP_Z = hd                                      # 庇の先端 = 足形の前端
    MISE_Z    = hd - MISE_OUT                           # 店先の柱通り
    F2_Z      = HIS_TIP_Z - (HIS_TOP_Y - HIS_TIP_Y) / KOBAI_H   # 2階の壁の通り
    REAR1_Z   = F2_Z - D2F                              # 表屋の裏壁
    URA_Z     = -hd + NOKI                              # 奥棟の裏壁
    RIDGE_Z   = (F2_Z + REAR1_Z) / 2.0                  # 表屋の大棟
    RIDGE_Y   = EAVE2_TIP + (D2F / 2.0 + NOKI) * R.RATIO
    EAVE2_W   = RIDGE_Y - (RIDGE_Z - REAR1_Z) * R.RATIO           # 壁の通りでの屋根面(軒桁)
    URIDGE_Z  = (-hd + REAR1_Z) / 2.0                             # 奥棟の大棟
    UEAVE_TIP = REAR_EAVE - NOKI * R.RATIO                        # 奥棟の軒先 = 谷の高さ
    URIDGE_Y  = UEAVE_TIP + (URIDGE_Z + hd) * R.RATIO
    MISE_HIS  = HIS_TIP_Y + (HIS_TIP_Z - MISE_Z) * KOBAI_H        # 柱通りでの庇の裏
    if URIDGE_Y + RIDGE_SHOW > EAVE2_W - 0.10:
        print("[machiya] ⚠ 奥棟の棟天端 %.3f が表屋の軒桁 %.3f に迫る(奥行を詰め過ぎ)"
              % (URIDGE_Y + RIDGE_SHOW, EAVE2_W))

    m = VM.Mesh()
    nbay = max(1, int(round(wKen)))               # 柱間の数 = 間数
    xs = [-hw + (2.0 * hw) * i / nbay for i in range(nbay + 1)]
    bays = [(xs[i], xs[i + 1]) for i in range(len(xs) - 1)]

    # ── 土台石 ────────────────────────────────────────────────
    m.box(*rr(-hw - 0.10, hw + 0.10), y0=0.0, y1=BASE,
          z0=URA_Z - 0.10, z1=MISE_Z + 0.10,
          uv=VM.sub(P['suv'], 0, 0, 1, 0.5), mat=STONE)

    # ── 店先(+Z・柱通り)。⭐ 1間ごとの割り付けで幅を取る ────────────
    for k, (a, b) in enumerate(bays):
        if k == 0:                              # 大戸口(通り庭の口)
            OB.plaster(m, P, *rr(a, b), y0=UCHI1, y1=POST_TOP, plane=MISE_Z, out=1, along='x')
            tategu(m, P, a + 0.16, b - 0.16, BASE, UCHI1, MISE_Z, 1, n=2)
            for xx in (a + 0.08, b - 0.08):     # 戸の脇の袖壁
                OB.shitami(m, P, *rr(xx - 0.08, xx + 0.08), y0=BASE, y1=UCHI1,
                           plane=MISE_Z, out=1, along='x')
        else:                                   # 見世(腰板 + 格子 + 見世棚)
            OB.shitami(m, P, *rr(a, b), y0=BASE, y1=KOSHI1, plane=MISE_Z, out=1, along='x')
            OB.mizukiri(m, P, *rr(a, b), y=KOSHI1, plane=MISE_Z, out=1, along='x')
            koshi_mado(m, P, a + 0.09, b - 0.09, KOSHI1 + 0.05, UCHI1, MISE_Z, 1,
                       back='dark')
            OB.plaster(m, P, *rr(a, b), y0=UCHI1, y1=POST_TOP, plane=MISE_Z, out=1, along='x')
    misedana(m, P, bays[1][0] + 0.05, bays[-1][1] - 0.05, MISE_Z, 1)
    noren_bar(m, P, -hw + 0.06, hw - 0.06, MISE_Z, 1)
    OB.posts(m, P, [-x for x in xs], BASE, POST_TOP, MISE_Z, 1, 'x')
    m.box(*rr(-hw - 0.05, hw + 0.05), y0=POST_TOP - 0.16, y1=POST_TOP,     # 店先の桁
          z0=MISE_Z - 0.17, z1=MISE_Z,
          uv=VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.45), mat=WOOD)

    # ── 2階の立面(+Z・F2_Z の通り)。厨子二階 ─────────────────────
    OB.plaster(m, P, *rr(-hw, hw), y0=HIS_TOP_Y, y1=WIN2_Y0, plane=F2_Z, out=1, along='x')
    OB.plaster(m, P, *rr(-hw, hw), y0=WIN2_Y1, y1=EAVE2_W, plane=F2_Z, out=1, along='x')
    for (a, b) in bays:
        c = (a + b) / 2.0
        OB.plaster(m, P, *rr(a, c - 0.60), y0=WIN2_Y0, y1=WIN2_Y1, plane=F2_Z, out=1, along='x')
        OB.plaster(m, P, *rr(c + 0.60, b), y0=WIN2_Y0, y1=WIN2_Y1, plane=F2_Z, out=1, along='x')
        koshi_mado(m, P, c - 0.60, c + 0.60, WIN2_Y0, WIN2_Y1, F2_Z, 1, pitch=0.12)
        aa, bb = rr(a + 0.10, b - 0.10)         # 霧除け(⚠ 板庇。瓦にすると面数が倍になる)
        m.box(aa, bb, WIN2_Y1 + 0.04, WIN2_Y1 + 0.09, F2_Z, F2_Z + 0.30,
              VM.sub(P['wuv'], 0.05, 0.05, 0.95, 0.55), WOOD)
        m.box(aa, bb, WIN2_Y1 - 0.02, WIN2_Y1 + 0.04, F2_Z + 0.26, F2_Z + 0.30,
              VM.sub(P['wuv'], 0.30, 0.10, 0.80, 0.30), WOOD)

    # ── 表屋の裏壁(REAR1_Z)。奥棟の屋根の上に立つ ────────────────
    OB.plaster(m, P, *rr(-hw, hw), y0=0.0, y1=EAVE2_W, plane=REAR1_Z, out=-1, along='x')

    # ── 奥棟の裏の面(−Z)。勝手口と窓 ─────────────────────────
    OB.shitami(m, P, *rr(-hw, hw), y0=BASE, y1=KOSHI_URA, plane=URA_Z, out=-1, along='x')
    OB.mizukiri(m, P, *rr(-hw, hw), y=KOSHI_URA, plane=URA_Z, out=-1, along='x')
    da0, da1 = xs[0] + 0.40, xs[0] + 1.35       # 勝手口(通り庭の裏の口)
    OB.plaster(m, P, *rr(-hw, da0), y0=KOSHI_URA, y1=REAR_EAVE, plane=URA_Z, out=-1, along='x')
    OB.plaster(m, P, *rr(da1, hw), y0=KOSHI_URA, y1=REAR_EAVE, plane=URA_Z, out=-1, along='x')
    OB.plaster(m, P, *rr(da0, da1), y0=UCHI1, y1=REAR_EAVE, plane=URA_Z, out=-1, along='x')
    tategu(m, P, da0, da1, BASE, UCHI1, URA_Z, -1, n=1)
    for (a, b) in bays[2:]:                     # 裏の窓
        c = (a + b) / 2.0
        koshi_mado(m, P, c - 0.45, c + 0.45, 1.05, 1.72, URA_Z, -1, pitch=0.12)
    OB.posts(m, P, [-x for x in xs], KOSHI_URA, REAR_EAVE, URA_Z, -1, 'x')

    # ── 妻(±X)。⛔ 開口は一切あけない(隣の駒と突き付く面)────────
    prof_f = [(REAR1_Z - NOKI, EAVE2_TIP), (RIDGE_Z, RIDGE_Y), (F2_Z + NOKI, EAVE2_TIP)]
    prof_u = [(-hd, UEAVE_TIP), (URIDGE_Z, URIDGE_Y), (REAR1_Z, UEAVE_TIP)]
    prof_h = [(HIS_TIP_Z, HIS_TIP_Y), (F2_Z, HIS_TOP_Y)]
    segs = [(URA_Z,    URIDGE_Z, REAR_EAVE, URIDGE_Y),
            (URIDGE_Z, REAR1_Z,  URIDGE_Y,  UEAVE_TIP),
            (REAR1_Z,  RIDGE_Z,  EAVE2_W,   RIDGE_Y),
            (RIDGE_Z,  F2_Z,     RIDGE_Y,   EAVE2_W),
            (F2_Z,     MISE_Z,   HIS_TOP_Y, MISE_HIS)]
    for s in (-1, 1):
        sx, sg = -s * hw, -s                    # 壁の通り(論理走り)と外向き
        OB.shitami(m, P, URA_Z, MISE_Z, BASE, KOSHI_URA, sx, sg, 'z')
        OB.mizukiri(m, P, URA_Z, MISE_Z, KOSHI_URA, sx, sg, 'z')
        for (z0, z1, y0, y1) in segs:
            OB.section(m, sx, sx + s * 0.10,
                       [(z0, KOSHI_URA), (z1, KOSHI_URA), (z1, y1), (z0, y0)],
                       VM.sub(P['cuv'], 0.05, 0.05, 0.95, 0.95), WALL)
        OB.posts(m, P, [URA_Z + 0.25, REAR1_Z, MISE_Z - 0.25],
                 KOSHI_URA, REAR_EAVE, sx, sg, 'z')
    for prof in (prof_f, prof_u, prof_h):
        rake(m, P, hw, prof)

    # ── 雨押え(奥棟の屋根が表屋の裏壁へ突き当たる谷)⛔ 省くと折れ目が管になる ──
    m.box(*rr(-hw - END, hw + END), y0=UEAVE_TIP - 0.06, y1=UEAVE_TIP + 0.16,
          z0=REAR1_Z - 0.02, z1=REAR1_Z + 0.16,
          uv=VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80), mat=WOOD)

    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])
    _recalc(body)

    # ── 瓦 ────────────────────────────────────────────────────
    ex0, ex1 = -hw - END, hw + END
    pieces = [
        _tiles(ex0, ex1, F2_Z + NOKI,   RIDGE_Z,  EAVE2_TIP, R.RATIO, name + "_r2S"),
        _tiles(ex0, ex1, REAR1_Z - NOKI, RIDGE_Z, EAVE2_TIP, R.RATIO, name + "_r2N"),
        _tiles(ex0, ex1, -hd,           URIDGE_Z, UEAVE_TIP, R.RATIO, name + "_ruN"),
        _tiles(ex0, ex1, REAR1_Z,       URIDGE_Z, UEAVE_TIP, R.RATIO, name + "_ruS"),
        _tiles(ex0, ex1, HIS_TIP_Z,     F2_Z,     HIS_TIP_Y, KOBAI_H, name + "_hisashi"),
    ]
    pieces += _ridge(ex0, ex1, RIDGE_Z, RIDGE_Y, name + "_omune")
    pieces += _ridge_caps(P, ex0, ex1, RIDGE_Z, RIDGE_Y, name + "_omune")
    pieces += _ridge(ex0, ex1, URIDGE_Z, URIDGE_Y, name + "_umune")
    pieces += _ridge_caps(P, ex0, ex1, URIDGE_Z, URIDGE_Y, name + "_umune")
    for prof in (prof_f, prof_u, prof_h):
        pieces += _sode(ex0, ex1, prof, name)
    pieces += kit_noren(bays, MISE_Z, name)

    V.dedup_materials()
    o = V.join([body] + [p for p in pieces if p], name)
    n_loose = _clean_loose(o)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print("[machiya] %s 通り Z=%+.3f / 柱通り %+.3f / 2階壁 %+.3f / 表屋の裏壁 %+.3f / 裏壁 %+.3f"
          % (name, hd, MISE_Z, F2_Z, REAR1_Z, URA_Z))
    print("[machiya] %s 軒先 %.2f / 瓦面の大棟 %.3f(棟天端 %.3f)/ 奥棟 %.3f(%.3f)/ 谷 %.3f"
          % (name, EAVE2_TIP, RIDGE_Y, RIDGE_Y + RIDGE_SHOW,
             URIDGE_Y, URIDGE_Y + RIDGE_SHOW, UEAVE_TIP))
    print("[machiya] %s 孤立頂点を落とした数 %d" % (name, n_loose))
    return o, name


# ═════════════════════════════ 検証 ═════════════════════════════
def verify(o, wKen, dM):
    """**光線で閉じを数える。**⛔ 目視で通さない — 段違いの折れ目や妻の三角は
    立面でも俯瞰でも「見えていない所」が読めない(memory: dan-chigai-roof-kuchi-is-a-duct)。

      ① **上から**の格子(0.25m)— 全部当たれば屋根と庇に穴が無い。
      ② **妻の内から外へ**(±X)— 谷の高さ・2階・腰で当たれば妻壁が閉じている。
      ③ **通りから奥へ**(+Z→−Z)— 店先の面と裏壁で必ず2回以上当たる(素通しでない)。
    ⚠ 光線はオブジェクトの**局所座標**で撃つ(`matrix_world.inverted()`)。"""
    import mathutils
    W, D = wKen * KEN, dM
    inv = o.matrix_world.inverted()

    def hit(orig, direction, dist=40.0):
        ok, loc, nor, idx = o.ray_cast(inv @ mathutils.Vector(orig),
                                       inv.to_3x3() @ mathutils.Vector(direction), distance=dist)
        return ok

    # ① 上から(Blender: 上 = +Z、平面は Bx = −Ux / By = −Uz)
    miss, tot = [], 0
    nx, nz = int(W / 0.25), int(D / 0.25)
    for i in range(nx):
        for j in range(nz):
            ux = -W / 2.0 + W * (i + 0.5) / nx
            uz = -D / 2.0 + D * (j + 0.5) / nz
            tot += 1
            if not hit((-ux, -uz, 12.0), (0, 0, -1)):
                miss.append((round(ux, 2), round(uz, 2)))
    print("[machiya] 検証① 上からの光線 %d 本中 当たらず %d %s"
          % (tot, len(miss), ("⭕" if not miss else "⛔ " + str(miss[:8]))))

    # ② 妻(±X)— 建物の内から外へ撃って妻壁に当たるか。
    # ⚠ **試す高さは屋根の下だけ**。妻の際で真上から測った屋根の高さを先に採り、
    #   その 0.15〜0.92 の帯で撃つ。⛔ 決め打ちの高さで撃つと屋根の外の点が「穴」に見える
    #   (2026-09-21 に 8 件の偽陽性で踏んだ)。
    import mathutils as _mu
    bad2, tested = [], 0
    ux_in = W / 2.0 - OVER_X - 0.06      # 壁の通りのすぐ内側
    z_back, z_front = -D / 2.0 + NOKI + 0.20, D / 2.0 - OVER_Z - MISE_OUT - 0.15
    for k in range(9):
        uz = z_back + (z_front - z_back) * k / 8.0
        # ⚠ 高さを採る点は**壁の通りの内側**。けらばで採ると袖瓦の天端(屋根面 +0.40)を拾う。
        # ⚠⚠ さらに **一番低い屋根**を採る(上から順に当たりを拾い、床より上の最後の1つ)。
        #   最初の当たりで済ませると、表屋の軒が奥棟の上へ 0.21 出ている帯で**表屋の屋根**を
        #   掴み、そこから下を「壁のはず」と見て偽の穴を刷る(2026-09-21 に奥行 6.3 で踏んだ)。
        ytop, p = None, 12.0
        for _ in range(6):
            ok, loc, _n, _i = o.ray_cast(inv @ _mu.Vector((-ux_in, -uz, p)),
                                         inv.to_3x3() @ _mu.Vector((0, 0, -1)), distance=40.0)
            if not ok:
                break
            h = (o.matrix_world @ loc).z
            if h < 0.5:
                break
            ytop, p = h, h - 0.02
        if ytop is None:
            bad2.append(('屋根が無い', round(uz, 2)))
            continue
        for f in (0.15, 0.40, 0.65, 0.92):
            uy = ytop * f
            for s in (-1, 1):
                tested += 1
                if not hit((0.0, -uz, uy), (-s, 0, 0), dist=W):
                    bad2.append((s, round(uy, 2), round(uz, 2), round(ytop, 2)))
    print("[machiya] 検証② 妻へ横から %d 本 %s"
          % (tested, "⭕ 全部当たる" if not bad2 else "⛔ " + str(bad2[:8])))

    # ③ 通り → 奥(素通しでないか)
    bad3 = []
    for k in range(5):        # ⚠ 位置は**桁行に比例**させる(決め打ちだと狭い間数で壁の外へ出る)
        ux = (W / 2.0 - OVER_X - 0.15) * (k - 2) / 2.0
        for uy in (0.30, 1.00, 1.60, 2.60, 3.00):
            n = 0
            p = D / 2.0 + 0.6
            for _ in range(8):
                ok, loc, nor, idx = o.ray_cast(inv @ mathutils.Vector((-ux, -p, uy)),
                                               inv.to_3x3() @ mathutils.Vector((0, 1, 0)),
                                               distance=(D + 2.0))
                if not ok:
                    break
                n += 1
                p = -(o.matrix_world @ loc).y - 0.02
            if n < 2:
                bad3.append((round(ux, 1), round(uy, 2), n))
    print("[machiya] 検証③ 通り→奥の貫通 %s"
          % ("⭕ どの高さも2面以上" if not bad3 else "⚠ " + str(bad3[:8])))
    return not miss and not bad2


def ratio_fix(w, h, res):
    return max(w, h * float(res[0]) / res[1]) * 1.12


def shots(o, key, box):
    """⚠ **書き出しの前に撮る**(`export_fbx` の後は bbox が潰れて画角が壊れる)。
    ⛔ 地面は `mn.z − 0.05` に敷く(ピボットが地盤レベルなので足元の浮きが読める)。"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    Wd, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    r = max(Wd, H, D)
    bpy.ops.mesh.primitive_plane_add(size=max(60.0, r * 20), location=(c.x, c.y, mn.z - 0.05))
    V.studio((c.x, mn.y - r * 2.4, c.z), (c.x, c.y, c.z),
             ratio_fix(Wd, H, (2000, 1100)), res=(2000, 1100))
    V.render(os.path.join(SHOT, "typ_machiya_%s_elev.png" % key))          # ① 店先の立面
    V.studio((mn.x - r * 0.55, mn.y - r * 1.1, 1.60), (c.x, c.y, H * 0.45), res=(1900, 1050))
    V.render(os.path.join(SHOT, "typ_machiya_%s_3d.png" % key))            # ② 通りから
    V.studio((mn.x - r * 2.6, c.y, c.z), (c.x, c.y, c.z),
             ratio_fix(D, H, (1500, 1100)), res=(1500, 1100))
    V.render(os.path.join(SHOT, "typ_machiya_%s_gable.png" % key))         # ③ 妻(段違い・けらば)
    V.studio((mx.x + r * 0.6, mx.y + r * 1.1, H * 0.95), (c.x, c.y, H * 0.45), res=(1900, 1050))
    V.render(os.path.join(SHOT, "typ_machiya_%s_ura.png" % key))           # ④ 裏(勝手口・窓)
    V.studio((c.x - r * 0.5, mx.y + r * 1.5, H * 3.2), (c.x, c.y, H * 0.65), res=(1700, 1000))
    V.render(os.path.join(SHOT, "typ_machiya_%s_fukan.png" % key))         # ⑤ 俯瞰(谷の納まり)
    # ⑥ 店先の寄り — 暖簾・格子・見世棚・大戸口が**実際に見えるか**(⛔ 引きでは読めない)
    V.studio((c.x + Wd * 0.22, mn.y - r * 0.42, 1.55), (c.x + Wd * 0.10, c.y, 1.30),
             res=(1900, 1050))
    V.render(os.path.join(SHOT, "typ_machiya_%s_mise.png" % key))


def _hook_eg(mat_name, jpg):
    """edogoyomi の材(`shop01map` 等)に obj と同じ jpg を結ぶ。
    ⚠ `V.hook_textures` は Village Kit の textures しか見ないので、在庫の表店は
      **真っ白のまま並ぶ**(2026-09-21 に並べ比べが読めなくて踏んだ)。⛔ 白い箱と
      比べて「軒高が合っている」と言わない。※ この結線は**レンダ専用**(書き出さない)。"""
    m = bpy.data.materials.get(mat_name)
    if m is None or not os.path.exists(jpg):
        return
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        return
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(jpg, check_existing=True)
    nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.8


def narabe(wKen=5.0, dM=4.0 * KEN):
    """**在庫の表店 `Eg.Shop01` / `Eg.Shop02` と一列に並べて焼く。**
    ⛔ 単体の立面では「同じ列に継いで納まるか」は読めない — 軒高も棟高も比べる相手が要る。
    ⚠ `es_shop*` の obj は素寸なので **ES=1.818 倍**してから並べる。⛔ 何も書き出さない。"""
    V.reset()
    objs, xs = [], 0.0
    for tag in ("es_shop01/shop01.obj", "es_shop02/shop02.obj"):
        before = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=os.path.join(V.REPO, "Assets", "edogoyomi", tag))
        got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
        ref = V.join(got, "Eg_" + tag.split('/')[0])
        V.sel([ref])
        bpy.ops.transform.resize(value=(1.818,) * 3, center_override=(0, 0, 0))
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        mn, mx = V.bbox([ref])
        ref.location = (xs - mn.x, -(mn.y + mx.y) / 2.0, -mn.z)
        bpy.context.view_layer.update()
        V.sel([ref]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        print("[machiya] 並べ比べ 在庫 %-8s W=%.3f H=%.3f D=%.3f"
              % (tag.split('/')[0], mx.x - mn.x, mx.z - mn.z, mx.y - mn.y))
        xs += (mx.x - mn.x)              # ⭐ **軒を接して並べる**(MachiyaRun と同じ継ぎ方)
        objs.append(ref)
    o, _n = build(wKen, dM)
    mn, mx = V.bbox([o])
    o.location = (xs - mn.x, 0.0, 0.0)
    bpy.context.view_layer.update()
    V.sel([o]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    xs += (mx.x - mn.x)
    objs.append(o)
    V.hook_textures()
    for tag in ("shop01", "shop02"):
        _hook_eg(tag + "map", os.path.join(V.REPO, "Assets", "edogoyomi",
                                           "es_" + tag, tag + ".jpg"))
    os.makedirs(SHOT, exist_ok=True)
    bpy.ops.mesh.primitive_plane_add(size=300.0, location=(xs / 2.0, 0.0, -0.05))
    V.studio((xs / 2.0, -60.0, 2.6), (xs / 2.0, 0.0, 2.6),
             ortho_scale=xs * 1.06, res=(2400, 800))
    V.render(os.path.join(SHOT, "typ_machiya_narabe_elev.png"))
    V.studio((-7.0, -17.0, 1.60), (xs * 0.45, 0.0, 2.4), res=(2000, 950))
    V.render(os.path.join(SHOT, "typ_machiya_narabe_me.png"))
    print("[machiya] 並べ比べ: Screenshots/typ_machiya_narabe_{elev,me}.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    words = [a for a in argv if not a.startswith("--")]
    wKen = float(argv[argv.index("--ken") + 1]) if "--ken" in argv else 5.0
    dM = float(argv[argv.index("--okuyuki") + 1]) if "--okuyuki" in argv else 4.0 * KEN
    if "axis" in words:
        V.reset(); axis_check(); return
    if "narabe" in words:
        narabe(wKen, dM); return
    V.reset()
    if not axis_check():
        print("[machiya] ⛔ 軸の写像が期待と違う。止める")
        return
    V.reset()
    name = ("Typ_Omotedana_%sken" % fmt(wKen) if abs(dM - 4.0 * KEN) < 1e-3
            else "Typ_Omotedana_%sx%sken" % (fmt(wKen), fmt(dM / KEN)))
    o, name = build(wKen, dM, name)
    mn, mx = V.bbox([o])
    print("[machiya] %-26s Unity実寸 W(X)=%6.3f H(Y)=%6.3f D(Z)=%6.3f 底=%+.3f 面=%d 頂点=%d"
          % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z,
             len(o.data.polygons), len(o.data.vertices)))
    print("[machiya] %-26s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
    print("[machiya] %-26s Shop01(ES後 W4.926 H4.250 D4.031・棟天端 4.236)との差: "
          "W %+.3f / H %+.3f / D %+.3f"
          % (name, (mx.x - mn.x) - 4.926, (mx.z - mn.z) - 4.250, (mx.y - mn.y) - 4.031))
    # ⛔ **食う幅と奥行は注文どおりか** — `MachiyaRun` は軒込みの bbox を積む(ShopModule.W)。
    eW, eD = (mx.x - mn.x) - wKen * KEN, (mx.y - mn.y) - dM
    print("[machiya] %-26s 注文との差 W %+.4f / D %+.4f ⇒ %s"
          % (name, eW, eD, "⭕" if max(abs(eW), abs(eD)) < 0.006 else "⛔ OVER_X/OVER_Z を直す"))
    verify(o, wKen, dM)
    if "--render" in argv:
        shots(o, fmt(wKen) if abs(dM - 4.0 * KEN) < 1e-3
              else "%sx%s" % (fmt(wKen), fmt(dM / KEN)), (mn, mx))   # ⚠ 書き出しの前に撮る
    V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
    print("[machiya] 書き出し " + os.path.join(OUT, name + ".fbx"))


main()
