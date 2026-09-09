"""山王社(日枝神社)の部材 — **段石**(石段の一段)と**腰高柵**(玉垣・境内の柵・法尻の柵)。

    blender --background --python Tools/Blender/build_sanno_buzai.py -- dan  [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- saku [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- dan  <蹴上> <踏面> <幅m> [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- saku <スパンm> [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- audit     # 既存部材の左右の別を検算
    blender --background --python Tools/Blender/build_sanno_buzai.py -- mitsuke   # 焼いた柵の FBX から見付けを実測

━━━ 1. 段石 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【なぜ新造するか】指図 `docs/Sashizu/sanno_sashizu.json` の `bom`「石段」が
  **在庫『無い』**と明記する。在庫の `Own.DanishiStep`(汐見坂)は
  **蹴上0.30/踏面0.45・幅1.98m の固定寸法**で(ビルダーは `Vector3.one` のまま並べている)、
  当図の4本とは一本も合わない。CLAUDE.md も ⛔ **0.30/0.45 は屋敷の中の石段の既定値で
  参道の坂には当てない**と定める。⇒ **蹴上・踏面・幅をパラメタで受ける段石**を起こす。

【寸法は指図 `kaidans` が正典。⛔ ここに数を書かない(下の SET は指図から引き写した
  『どれを焼くか』の名簿であって、寸法の出所ではない)。】蹴上・踏面は
  **段数と平面長・比高からの従属値**で、4本とも違う。

【1段=1部材にした理由】女坂は `pts` 13点の**曲線**で、指図が「段を斜路にその場の
  進行方向へ直角に置く(石は矩形のまま)」と定める。⇒ 一飛び分を1枚の板にすると
  曲線に乗らない。**繰り返しの単位**として出し、据える側が段ごとに向きを決める。

【向きとピボット(Unity 座標)】幅=X / 高さ=Y / 走り=Z、**+Z = 見え面 = 坂下(蹴上の面)**。
  ・ピボット = **踏面の中心(幅の中心・走りの中心)・踏面の高さ(天端)**。
    ⇒ 段 i(下から0起点)は `position = 下端 + 進行方向 × 踏面×(i+0.5)`、
      `position.y = 下端の天端 + 蹴上×(i+1)`、`yaw = ローカル +Z が坂下を向く向き`。
    ⛔ **`SeatBottom` で据えない** — 躯体は Y<0 へ `BODY` 垂れている(地中の胴)。
  ・走りは Z ∈ [−(踏面/2 + LAP), +踏面/2]。**LAP は上の段の下へ潜る差し込み**で、
    ⛔ 取ると踏面と蹴上の継ぎ目に隙が開いて地面が透ける。

【石の割り】幅を k 枚に割って**目地**を通す(1枚板にしない)。⭕ 割りは **x=0 について
  左右対称**にしてある — こうしておくと `Unity X = −(Blender X)`(EDO-0161)の
  符号反転が部材に何の影響も及ぼさないことが**幾何として保証**できる(下の検算)。
  ⚠ 目地が段ごとに一直線に立つのを避けるため **variant a / b の2種**を出す。
    据える側で **i%2** に振ること(⛔ 片方だけを53段並べない)。

【材】`M_FJG_Rock_001`(Waldemarst FreeJapaneseGarden)。⛔ 新規マテリアルを作らない —
  `Own.Ishibashi`(切石橋)・`Own.Tateishi`・`Own.Hiraishi` と同じ**加工石**の材で、
  作り方(箱+1〜2cm の面取り・上面は完全な平面)も `build_hiraishi.gen_ishibashi` に倣う。
  ⛔ 汐見坂の `M_ShiomizakaIshi` は `Assets/Edo/Models/Shiomizaka` にあり、
     remap の借り先ディレクトリに入っていない(名前を名乗っても当たらない)。

━━━ 2. 腰高柵 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【なぜ新造するか】指図 `bom` の「玉垣」「境内の外周の柵・法尻の柵」がどちらも
  **在庫『無い』**。⛔ Village Kit の `fence A/B`・`Fence_B_01` は**屋根つきの板塀**、
  edogoyomi の `obj_itabei` は板塀、`Eg.Hogaki5` は穂垣、`Own.YotsumeGaki` は竹の四つ目垣で、
  どれも「丸柱+貫二段+丸立子の腰高の透ける柵」ではない(2026-09-08 在庫方が実見)。

【寸法は指図 `gardens[前庭の帯(玉垣の植込み)].tamagaki` が正典】
  丈 `hM` / 柱径 `postDiaM` / 柱の芯々 `postPitchKen`[間] / 貫の段数 `nuki` /
  立子径 `tatekoDiaM` / 立子の間隔 `tatekoPitchM` / 一枚の内法の下限 `uchinoriMinM`。
  ⭕ **玉垣・`runs[Ita_Keidai]`(境内の外周)・`runs[Saku_SW]`・`runs[Saku_Sando]`(法尻)は
    同一部材**(3本とも `hFrom` が上の `tamagaki.hM` を指す)⇒ **新造は一度で足りる**。
  ⛔ **発注量(延長)は図が算出する。部材には焼き込まない。**
  ⛔ **形式(格子・木柵・矢来の別)は名所図会からは決まらない【?】** ⇒
    ⛔ 意匠を足さない(笠木・結び・貫の装飾・面取りの意匠を付けない)。素直な透ける柵に留める。

【スパンが可変な理由】`tamagaki._` が「**隅は必ず柱・辺の中は芯々 `postPitchKen` 以下で等分**」
  と定め、開口(木戸・井戸の口)で辺が区間に割れる。⇒ 1間固定では据わらない。
  **スパン[m]を引数で受ける**(`Own.NagayaOmote(len)` と同じ流儀)。

【天端の決め方は据える側】⭕ 玉垣は**天端が水平**、法尻の柵は**天端が地形なり**。
  ⇒ 部材は **1スパンの繰り返しの単位**として出し、⛔ 長い一枚板にしない。
    地形なりの run は各スパンの両端の地盤で `position.y` と pitch(縦断の傾き)を決める。

【向きとピボット(Unity 座標)】幅=X(走り)/ 高さ=Y / 厚み=Z。前後対称(±Z が同じ姿)。
  ・ピボット = **スパンの中心・地盤レベル**。柱は **Unity ローカル −X 端**
    (柱の外面が x = −スパン/2)。⇒ bbox がちょうど1スパン。
  ・⛔ **run の +X 端に `Saku_Koshidaka_Post` を1本足す**(足さないと貫が宙で終わる)。
  ・⛔ **`SeatBottom` で据えない** — 根入れ `ROOT` が Y<0 に出ている。

【材】`M_Wood_fence`(NatureManufacture の丸太の材質名をそのまま運ぶ)。
  ⛔ 円柱を自作しない — `build_maruta.log_piece` で**在庫の丸太を切って**使う(規則1)。

━━━ 検算(EDO-0161)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⛔⛔ **`Unity X = −(Blender X)`。** 非対称な部材は据え付け側が 180° を吸収している疑いがあり、
  **立面でも数値QAでも素通りする**(俯瞰でしか見えない)。⇒ 焼いた直後に部材の側で検算する:
  ・段石 … **Unity X について鏡像対称**であることを頂点集合で確かめる
    (対称なら符号反転は恒等 ⇒ 左右の別が生じ得ない)。
  ・腰高柵 … 柱は**断面が一番太い縦材**である。x を細かく刻んで**厚み(Z)が最大の帯**を
    探し、それが Unity −X 側にあることを確かめる。
    ⛔ 期待値(「柱は −X 端」)は引数からではなく**メッシュの太さ**から立てる。
  ・`-- audit` は既存の `Maruta_Tesuri_1ken` / `HoriSaku` に同じ検算を掛ける
    (⚠ FBX の読み書きは互いに逆写像なので、読み戻した座標は**書いたときの Blender 座標**。
      そこへ README の写像 (−x, z, −y) を掛けて Unity 座標を出す)。

⚠ **FBX のファイル md5 は不変性の検査に使えない**(ヘッダに CreationTime と絶対パスが入る)。
  ⇒ **幾何の指紋**(頂点・面・UV・材質名の sha1)を焼くたびに刷る。

【落とし穴】
  ・⚠ `export_fbx` を通した後は bbox が 0 に潰れる。**測るのもレンダも書き出しの前に。**
  ・⚠ `bpy.ops.transform_apply` の location 既定は True。
  ・⚠ 同じ FBX を2度読むと `M_Wood_fence.001` ができる。join の前に `V.dedup_materials()`。
"""
import bpy, bmesh, sys, os, math, random, hashlib
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_tateishi as BT          # 岩の材(M_FJG_Rock_001)・UV矩形・密度・レンダの結線
import build_maruta as MA            # 在庫の丸太を切る道具(log_piece / upright / hook)

OUT_DAN = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Kaidan"))
OUT_SAKU = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei"))
SHOT = os.path.join(V.REPO, "Screenshots")
SASHIZU = os.path.join(V.REPO, "docs", "Sashizu", "sanno_sashizu.json")

# ---- 段石: 作りの値【U 指図に無い。据わりのための胴と差し込み】--------------------
LAP = 0.10          # 上の段の下へ潜る差し込み(走り方向・上手側)
BODY = 0.18         # 蹴上の下へ続く地中の胴(⛔ 0 にすると段の下から地面が透ける)
CHAMFER = 0.015     # 稜の面取り。加工石なので 1〜2cm(`build_hiraishi.gen_ishibashi` と同じ幅)
STONE_W = 1.15      # 石1枚の目安の幅[m]。幅をこの前後で等分する
WJIT = 0.06         # 石の幅の振れ(比。左右対称に振る)

# ---- 腰高柵: 作りの値【U 指図に無い】-------------------------------------------
ROOT = 0.15         # 柱の根入れ(Y<0 へ出る)。`Own.YotsumeGaki` と同じ
NUKI_D = 0.075      # 貫の径【U 指図に無い】。`build_maruta.NUKI_D` 0.09 より一段細い(丈1.2の柵)
NUKI_AT = (0.30, 0.80)   # 貫二段の芯の高さ = 丈 hM に対する比【U 指図に無い】
TATEKO_BOTTOM = 0.09     # 立子の下端(足元の抜け)【U 指図に無い】
POST_STEM, NUKI_STEM, TATEKO_STEM = "wood_log_04", "wood_log_02", "wood_log_01"
# ⚠ 元の丸太は 01=3.109 / 02=3.176 / 03=0.729 / 04=2.299 / 05=1.329 / 06〜09=0.72m(実測)。
#   ⛔ `wood_log_05` は柱(丈+根入れ=1.35)に **0.02 足りない**(2026-09-08 に踏んだ)。
#   ⛔ 06〜09(細い枝)は立子の丈 1.11 に届かない ⇒ 太い丸太を径だけ縮めて切る。


# ================================================================ 指図を読む
def sashizu():
    import json
    with open(SASHIZU) as f:
        return json.load(f)


def kaidan_specs():
    """指図 `kaidans` から**石の段**の (名, 蹴上, 踏面, 幅m) を出す。
    ⛔ 寸法をここに書かない。⛔ **向拝の階は採らない** — `kaidans[向拝の階]` は
      【A 加藤重枝2018】が**木階三級**と定める木の階で、石の段ではない(→ 呼び出し元へ差し戻す)。"""
    d = sashizu()
    out = []
    for k in d["kaidans"]:
        if k["name"] == "向拝の階":
            continue
        out.append((k["name"], float(k["keri"]), float(k["fumi"]),
                    float(k["wKen"]) * float(d["const"]["ken"])))
    return out


def tamagaki_spec():
    """指図 `gardens[前庭の帯…].tamagaki` から柵の寸法を出す。⛔ 数をここに書かない。"""
    d = sashizu()
    for g in d["gardens"]:
        t = g.get("tamagaki")
        if t:
            return {"h": float(t["hM"]), "post_d": float(t["postDiaM"]),
                    "pitch": float(t["postPitchKen"]) * float(d["const"]["ken"]),
                    "nuki": int(t["nuki"]), "tateko_d": float(t["tatekoDiaM"]),
                    "tateko_pitch": float(t["tatekoPitchM"]),
                    "uchinori_min": float(t["uchinoriMinM"])}
    raise SystemExit("[sanno] 指図に tamagaki が無い")


def rng_of(*key):
    """⛔ `hash()` で種を作らない(実行ごとに変わる。README 2026-09-07)。"""
    h = hashlib.sha1("|".join(str(k) for k in key).encode("utf-8")).hexdigest()
    return random.Random(int(h[:12], 16))


# ================================================================ 検算の道具
def unity_verts(o):
    """Blender の組み立て座標 → **Unity ローカル座標**。
    README「書き出しの規約」: `export_fbx(axis_forward='-Z', axis_up='Y')` は
    Unity Z = −(Blender Y) / Unity Y = Blender Z / **Unity X = −(Blender X)**。"""
    return [(-v.co.x, v.co.z, -v.co.y) for v in o.data.vertices]


def fingerprint(o):
    """**幾何の指紋**。⛔ FBX のファイル md5 は使えない(CreationTime と絶対パスが入る)。"""
    hsh = hashlib.sha1()
    for (x, y, z) in unity_verts(o):
        hsh.update(("%.5f,%.5f,%.5f;" % (x, y, z)).encode())
    for p in o.data.polygons:
        hsh.update((",".join(str(i) for i in p.vertices) + ";").encode())
    if o.data.uv_layers:
        for dd in o.data.uv_layers.active.data:
            hsh.update(("%.5f,%.5f;" % (dd.uv[0], dd.uv[1])).encode())
    for m in o.data.materials:
        hsh.update((m.name if m else "-").encode())
    return hsh.hexdigest()[:16]


def check_mirror_x(o, tol=1e-4):
    """**Unity X について鏡像対称か**を頂点集合で確かめる(段石の検算)。
    対称なら `Unity X = −(Blender X)` の符号反転は恒等 ⇒ 左右の別が生じ得ない。"""
    uv = unity_verts(o)
    key = lambda t: (round(t[0] / tol), round(t[1] / tol), round(t[2] / tol))
    a = sorted(key(t) for t in uv)
    b = sorted(key((-t[0], t[1], t[2])) for t in uv)
    return a == b


def thickest_bin_x(o, nbin=80):
    """**厚み(Unity Z の広がり)が最大の x 帯**の中心を返す。柵の柱を「一番太い縦材」として
    幾何から探すための道具。⛔ 期待値を引数から立てない。"""
    uv = unity_verts(o)
    xs = [t[0] for t in uv]
    x0, x1 = min(xs), max(xs)
    span = max(x1 - x0, 1e-6)
    lo = [1e9] * nbin
    hi = [-1e9] * nbin
    for (x, y, z) in uv:
        if y < 0.05:          # 根入れ・地中は見ない(柱だけが持つので不公平)
            continue
        i = min(nbin - 1, int((x - x0) / span * nbin))
        lo[i] = min(lo[i], z); hi[i] = max(hi[i], z)
    best, bi = -1.0, 0
    for i in range(nbin):
        if hi[i] < lo[i]:
            continue
        if hi[i] - lo[i] > best:
            best, bi = hi[i] - lo[i], i
    return x0 + span * (bi + 0.5) / nbin, best, (x0, x1)


def report(o, name, extra=""):
    uv = unity_verts(o)
    xs = [t[0] for t in uv]; ys = [t[1] for t in uv]; zs = [t[2] for t in uv]
    print("[sanno] %-30s Unity実寸 W(X)=%.3f H(Y)=%.3f D(Z)=%.3f  "
          "X %.3f..%.3f  Y %.3f..%.3f  Z %.3f..%.3f  面=%d  材質=%s  指紋=%s %s"
          % (name, max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
             len(o.data.polygons), [m.name for m in o.data.materials],
             fingerprint(o), extra))
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


# ================================================================ 1. 段石
def _cuts(w, variant):
    """幅 w を石に割る。⭕ **x=0 について左右対称**に割る(EDO-0161 の検算が通るように)。"""
    k = max(2, int(round(w / STONE_W)))
    rng = rng_of("dan", "%.3f" % w, variant)
    if variant == "b":
        k += 1
        base = [-w / 2.0 + w * (i - 0.5) / (k - 1) for i in range(1, k)]
    else:
        base = [-w / 2.0 + w * i / k for i in range(1, k)]
    n = len(base)
    jit = [0.0] * n
    for i in range(n // 2):
        d = rng.uniform(-WJIT, WJIT) * (w / k)
        jit[i] = d
        jit[n - 1 - i] = -d                     # ⭕ 鏡像に振る
    return [-w / 2.0] + [base[i] + jit[i] for i in range(n)] + [w / 2.0]


def _stone(x0, x1, y0, y1, z0, z1, mat, rng, name, chamfer=None, tile=None):
    """切石1枚。箱 + 全稜 `chamfer`(既定 `CHAMFER`)の面取り。⛔ 自然石の割れ肌ノイズは掛けない(加工石)。
    ⛔ 天端(踏面)は完全な平面のまま残す — 歩く面なので撫でない。"""
    bm = bmesh.new()
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res["verts"]
    bmesh.ops.scale(bm, verts=vs, vec=(x1 - x0, y1 - y0, z1 - z0))
    bmesh.ops.translate(bm, verts=vs,
                        vec=((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0))
    try:
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges),
                        offset=(CHAMFER if chamfer is None else chamfer),
                        offset_type='OFFSET', segments=1, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    except Exception as ex:
        print("[sanno] 面取りを飛ばした: %s" % ex)
    BT.ensure_outward(bm)
    bm.normal_update()
    # UV — 面の主軸で `M_FJG_Rock_001` のアトラス矩形 `BT.RECT` へ平面投影する。
    # ⛔ 一点貼りにしない(無地になる)。⛔ **`BT.pingpong` を面ごとに掛けない** —
    #   ⚠ 2026-09-08 に踏んだ罠: 立石・平石は**細分したメッシュ**に ping-pong を掛けるので
    #   折り返しは微小な面の中で起きるが、切石の**大きな1枚の面**(踏面 0.88 m²)が折り返しを
    #   跨ぐと、四隅が同じ値へ折り返って **UV の幅が 0.001 に潰れ、踏面が「櫛で梳いた縞」**になる
    #   (検証レンダの近景で実見。⚠ 引きの立面では読めない)。
    #   ⭕ **面ごとに、その面の広がりが矩形へ収まる位置へ平行移動する**(折り返しを起こさない)。
    #     ずらし量は石と面から決まる決め打ちの疑似乱数 ⇒ 面ごとに柄が変わり、繰り返しが出ない。
    #     ⚠ 切石は面ごとに別々に叩いた肌なので、稜で柄が繋がらないのはむしろ正しい。
    uvl = bm.loops.layers.uv.new("UVMap")
    for fi, f in enumerate(bm.faces):
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        raw = []
        for loop in f.loops:
            co = loop.vert.co
            if ax == 2:
                a, b = co.x, co.y
            elif ax == 1:
                a, b = co.x, co.z
            else:
                a, b = co.y, co.z
            if tile:
                raw.append((a / tile, b / tile))
            else:
                raw.append((a * BT.DENS_U, b * BT.DENS_V))
        if tile:
            # ⭐ **タイル貼り**(`Kirishi` のような継ぎ目の無い1枚もの)。⛔ アトラスの矩形へ
            #   押し込めない — 押し込めると面の実寸に関係なく1枚が伸縮して、
            #   0.30m の段石と 1.05m の帯で**粒の大きさが変わる**(叩き肌に見えなくなる)。
            for loop, (a, b) in zip(f.loops, raw):
                loop[uvl].uv = (a, b)
            continue
        u0 = min(q[0] for q in raw); u1 = max(q[0] for q in raw)
        v0 = min(q[1] for q in raw); v1 = max(q[1] for q in raw)
        su = min(1.0, u1 - u0); sv = min(1.0, v1 - v0)
        ku = 1.0 if u1 - u0 < 1e-9 else su / (u1 - u0)
        kv = 1.0 if v1 - v0 < 1e-9 else sv / (v1 - v0)
        ou = rng.uniform(0.0, 1.0) * (1.0 - su)      # 面の広がりが矩形に収まる位置へ寄せる
        ov = rng.uniform(0.0, 1.0) * (1.0 - sv)
        for loop, (a, b) in zip(f.loops, raw):
            fu = ou + (a - u0) * ku
            fv = ov + (b - v0) * kv
            loop[uvl].uv = (BT.RECT[0] + fu * (BT.RECT[2] - BT.RECT[0]),
                            BT.RECT[1] + fv * (BT.RECT[3] - BT.RECT[1]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free(); me.update()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 切石の材(Kirishi)
KIRISHI = "Kirishi"          # ⚠ Unity 側 `Assets/Edo/Materials/Sanno/Kirishi.mat`
KIRISHI_TILE = 0.44          # 1枚が受け持つ実寸[m]。⛔ 面ごとに伸縮させない(タイル貼り)。
                             # ⛔ 段の丈 0.30 と同じにしない(繰り返しが目地と揃って縞になる)
KIRISHI_DIR = os.path.join(V.REPO, "Assets", "Edo", "Materials", "Sanno")


def kirishi_material():
    """**切石(叩き仕上げ)の材**。⚠ 「新規マテリアルを作らない」規約の 2 例目の例外。

    ⛔⛔ **`M_FJG_Rock_001` を基壇に貼らない**(2026-09-09 庭方19巡目 指3・考証20巡目 高3)。
      あれは**苔むした暗い写真計測岩**で、アルベド中央 V13.3% ⇒ レンダで V21.6%
      = 木部 43.1% の**ちょうど半分**。切石の基壇は立面で**いちばん明るい要素**であるべき
      なのに、いちばん暗かった。⚠ **形は既に切石だった**(`_stone` は箱+面取りで、
      割れ肌ノイズを一切掛けていない)⇒ **野面に見えた原因は 100% 材**。
    【出所と確度】⛔ 【U 設計値 — 庭方 2026-09-09 十九巡目 指3。史料は石種・色・目地・段数を
      言わない【?】】。焼くのは `Tools/Blender/make_kirishi_texture.py`(在庫方が
      2026-09-09 に「淡灰・平滑の貼れる材は在庫に無い」と判定した記録もそこにある)。
    ⭕ **Blender 側でも実テクスチャを結ぶ** — `M_FJG_Rock_001` のように名前だけの入れ物に
      すると検証レンダで**真っ白**に焼け、「明るくなった」と誤読する(2026-09-09 の轍)。"""
    m = bpy.data.materials.get(KIRISHI)
    if m:
        return m
    m = bpy.data.materials.new(KIRISHI)
    m.use_nodes = True
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None:
        return m
    b.inputs['Alpha'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.90       # 艶消し(Unity 側 _Smoothness 0.10)
    b.inputs['Metallic'].default_value = 0.0
    alb = os.path.join(KIRISHI_DIR, "T_Kirishi_Albedo.png")
    if os.path.exists(alb):
        ai = nt.nodes.new('ShaderNodeTexImage')
        ai.image = bpy.data.images.load(alb, check_existing=True)
        ai.location = (-500, 300)
        nt.links.new(ai.outputs['Color'], b.inputs['Base Color'])
    nrm = os.path.join(KIRISHI_DIR, "T_Kirishi_Normal.png")
    if os.path.exists(nrm):
        ni = nt.nodes.new('ShaderNodeTexImage')
        ni.image = bpy.data.images.load(nrm, check_existing=True)
        ni.image.colorspace_settings.name = 'Non-Color'
        ni.location = (-500, -100)
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.location = (-260, -100)
        # ⭐ **叩き仕上げ = 面の凹凸 ≤ 3mm。**⛔ 1.0 にすると割肌の陰が出る
        #   (Unity 側 `_BumpScale` と同じ数にしてある)
        nm.inputs['Strength'].default_value = 0.30
        nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def dan(keri, fumi, w, variant="a", name=None):
    """段石1段。Blender: x=幅 / y=走り(+y が坂上)/ z=高さ(0 = 踏面)。
    ⇒ Unity: X=幅 / Y=高さ(0 = 踏面)/ **+Z = 坂下 = 蹴上の見え面**。"""
    name = name or dan_name(keri, fumi, w, variant)
    mat = BT._borrow_rock_material()
    rng = rng_of("dan", "%.3f" % keri, "%.3f" % fumi, "%.3f" % w, variant)
    cuts = _cuts(w, variant)
    objs = []
    for i in range(len(cuts) - 1):
        # ⚠ 上手(+y)へ LAP 潜らせる / 下へ BODY 垂らす。どちらも隣の段に隠れる
        objs.append(_stone(cuts[i], cuts[i + 1],
                           -fumi / 2.0, fumi / 2.0 + LAP,
                           -(keri + BODY), 0.0, mat, rng, "%s_s%d" % (name, i)))
    V.dedup_materials()
    o = V.join(objs, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


def dan_name(keri, fumi, w, variant):
    return "Dan_%.3f_%.3f_%.3f_%s" % (keri, fumi, w, variant)


def dan_check(o, keri, fumi, w):
    """⭕ **焼いた直後の自動検算。**期待値は(1)幾何そのもの と(2)指図の値、の2本立て。"""
    ok = []
    mirror = check_mirror_x(o)
    ok.append(("左右対称(EDO-0161: Unity X = −Blender X が恒等)", mirror, ""))
    uv = unity_verts(o)
    xs = [t[0] for t in uv]; ys = [t[1] for t in uv]; zs = [t[2] for t in uv]
    ok.append(("踏面がピボットの高さ(Y最大=0)", abs(max(ys)) < 1e-4, "Ymax=%.4f" % max(ys)))
    ok.append(("蹴上の面が +Z(見え面)", abs(max(zs) - fumi / 2.0) < 1e-3,
               "Zmax=%.4f 期待 %.4f" % (max(zs), fumi / 2.0)))
    ok.append(("上手の差し込みが −Z", abs(min(zs) + (fumi / 2.0 + LAP)) < 1e-3,
               "Zmin=%.4f" % min(zs)))
    ok.append(("幅が指図どおり", abs((max(xs) - min(xs)) - w) < 1e-3,
               "W=%.4f 期待 %.4f" % (max(xs) - min(xs), w)))
    ok.append(("躯体が蹴上+胴ぶん垂れている", abs(min(ys) + (keri + BODY)) < 1e-3,
               "Ymin=%.4f" % min(ys)))
    bad = [t for t in ok if not t[1]]
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    if bad:
        raise SystemExit("[sanno] ⛔ 段石の検算が落ちた: %s" % ", ".join(t[0] for t in bad))


# ================================================================ 2. 腰高柵
def _log(stem, length, dia, name, frm=0.0, decimate=None):
    o = MA.log_piece(stem, length, dia, name, frm=frm)
    if decimate:
        # ⚠ 立子は φ0.045 の細い丸材。元の丸太の面数(樹皮の凹凸)を持ったままだと
        #   1スパンが 1,700 面を超え、556m の run で 50 万面を超える。
        #   ⭕ **細い材だけ**間引く(この径では稜の丸みは目に入らない)。
        #   ⛔ 柱・貫は間引かない(手前に来るので稜が角張ると分かる)。
        md = o.modifiers.new("dec", 'DECIMATE')
        md.ratio = decimate
        V.sel([o]); bpy.ops.object.modifier_apply(modifier=md.name)
    return o


def _align_x(o, at, side):
    """丸太は径を実測で合わせるので端面が呼びと 2〜3mm ずれる。
    ⭕ **走り方向の端は呼びの通りに合わせる**(bbox がちょうど1スパンになるように)。
    side='max' → Blender の x 最大を `at` に / 'min' → x 最小を `at` に。"""
    xs = [v.co.x for v in o.data.vertices]
    d = at - (max(xs) if side == 'max' else min(xs))
    o.data.transform(Matrix.Translation((d, 0, 0)))
    o.data.update()
    return o


def saku(span, name=None):
    """腰高柵 1スパン。柱1(**Blender +X 端 ⇒ Unity −X 端**)+ 貫二段 + 立子 n 本。
    ⚠ 柱を Blender −X に置くと **Unity では +X 端**に出る(EDO-0161)。"""
    t = tamagaki_spec()
    name = name or saku_name(span)
    H, PD, TD = t["h"], t["post_d"], t["tateko_d"]
    # ⛔ 指図 `tamagaki.uchinoriMinM` — 一枚(柱と柱の間)の内法の下限。これを割った一枚は
    #   垣ではなく詰め物になる(立子が3本入らない)。⛔ 黙って作らず、呼び出し元へ差し戻す。
    if span - PD < t["uchinori_min"] - 1e-9:
        raise SystemExit("[sanno] ⛔ スパン %.3f は内法 %.3f となり、指図の下限 %.3f を割る "
                         "(⇒ 辺の割り方を指図方へ差し戻すこと)"
                         % (span, span - PD, t["uchinori_min"]))
    parts = []
    # 柱 — Blender +X 端(外面が x = +span/2)⇒ Unity −X 端
    p = MA.upright(_log(POST_STEM, H + ROOT, PD, "post", frm=0.10), top_at_zero=False)
    p.data.transform(Matrix.Translation((0, 0, -ROOT)))
    _align_x(p, span / 2.0, 'max')          # 柱の外面をスパンの端(Unity −X)にぴたりと合わせる
    parts.append(p)
    # 貫二段 — スパン全長。芯は z=0(前後対称。⛔ 片面へ寄せない=どちらからも同じ姿)
    for j, frac in enumerate(NUKI_AT[:t["nuki"]]):
        r = _log(NUKI_STEM, span, NUKI_D, "nuki%d" % j, frm=0.30 + 0.5 * j)
        r.data.transform(Matrix.Translation((0, 0, H * frac)))
        parts.append(r)
    # 立子 — 柱の内法(clear bay)を等分。⭕ 芯々は必ず tatekoPitchM 以下になる
    clear0, clear1 = -span / 2.0, span / 2.0 - PD
    clear = clear1 - clear0
    n = max(1, int(math.ceil(clear / t["tateko_pitch"] - 1e-9)))
    tl = H - TATEKO_BOTTOM
    for j in range(n):
        cx = clear0 + clear * (j + 0.5) / n
        s = MA.upright(_log(TATEKO_STEM, tl, TD, "tateko%d" % j, frm=0.15 + 0.11 * j,
                            decimate=0.45), top_at_zero=False)
        s.data.transform(Matrix.Translation((cx, 0, TATEKO_BOTTOM)))
        parts.append(s)
    for q in parts:
        q.data.update()
    V.dedup_materials()
    o = V.join(parts, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[sanno] %s 丈%.2f 柱φ%.3f 貫%d段 立子φ%.3f×%d本(芯々%.3f ≦ %.3f)"
          % (name, H, PD, t["nuki"], TD, n, clear / n, t["tateko_pitch"]))
    return o, name


def saku_post(name="Saku_Koshidaka_Post"):
    """run の +X 端に足す柱1本。⛔ 足さないと最後の貫が宙で終わる。
    ピボット = **run の終端(柱の +X 面)・地盤** ⇒ `s = s1` をそのまま渡せる。"""
    t = tamagaki_spec()
    o = MA.upright(_log(POST_STEM, t["h"] + ROOT, t["post_d"], name, frm=0.10),
                   top_at_zero=False)
    o.data.transform(Matrix.Translation((0, 0, -ROOT)))
    _align_x(o, 0.0, 'min')     # Blender x 最小 = 0 ⇒ Unity x 最大 = 0(柱の +X 面が原点)
    o.data.update()
    o.name = o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


def saku_name(span):
    return "Saku_Koshidaka_%.3f" % span


def saku_check(o, span):
    """⭕ **焼いた直後の自動検算(EDO-0161)。**⛔ 期待値は引数からではなく
    「柱は一番太い縦材」という**幾何**から立てる。"""
    t = tamagaki_spec()
    cx, thick, (x0, x1) = thickest_bin_x(o)
    uv = unity_verts(o)
    ys = [q[1] for q in uv]
    ok = [
        ("柱(最も太い縦材 厚み%.3f)が Unity −X 側" % thick, cx < 0.0, "帯の中心 x=%.3f" % cx),
        ("柱が端にある(|x| が半スパンの8割超)", abs(cx) > span * 0.4, ""),
        ("bbox がちょうど1スパン", abs((x1 - x0) - span) < 2e-3,
         "W=%.4f 期待 %.4f" % (x1 - x0, span)),
        ("天端が丈どおり", abs(max(ys) - t["h"]) < 5e-3, "Ymax=%.4f 期待 %.4f" % (max(ys), t["h"])),
        ("根入れが Y<0 に出ている", min(ys) < -0.01, "Ymin=%.4f" % min(ys)),
    ]
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    bad = [q[0] for q in ok if not q[1]]
    if bad:
        raise SystemExit("[sanno] ⛔ 柵の検算が落ちた: %s" % ", ".join(bad))


# ================================================================ 既存部材の検算
def audit():
    """既存の「柱が −X 端」を名乗る部材に同じ検算を掛ける(EDO-0161)。
    ⚠ FBX の読み書きは互いに逆写像なので、読み戻した座標は**書いたときの Blender 座標**。
      そこへ README の写像を掛けて Unity 座標を出す(`unity_verts`)。"""
    import vkmesh as VM
    targets = [("Maruta_Tesuri_1ken", "Assets/Edo/Models/Maruta/Maruta_Tesuri_1ken.fbx"),
               ("Maruta_Tesuri_Post", "Assets/Edo/Models/Maruta/Maruta_Tesuri_Post.fbx"),
               ("HoriSaku", "Assets/Edo/Models/Hei/HoriSaku.fbx"),
               ("HoriSakuPost", "Assets/Edo/Models/Hei/HoriSakuPost.fbx"),
               ("Saku_Koshidaka_1.818", "Assets/Edo/Models/Hei/Saku_Koshidaka_1.818.fbx"),
               ("Saku_Koshidaka_Post", "Assets/Edo/Models/Hei/Saku_Koshidaka_Post.fbx")]
    for (label, rel) in targets:
        path = os.path.join(V.REPO, rel)
        if not os.path.exists(path):
            print("[audit] %-22s 見つからない: %s" % (label, rel)); continue
        V.reset()
        objs = VM.import_fbx_abs(path)
        o = V.join(objs, label)
        cx, thick, (x0, x1) = thickest_bin_x(o)
        print("[audit] %-22s bbox X %.3f..%.3f / 最も太い縦材(厚み%.3f)の中心 x=%+.3f "
              "⇒ 柱は Unity %s 端  (EdoAssets の註は「−X 端」)"
              % (label, x0, x1, thick, cx, "−X" if cx < 0 else "**+X**"))


# ================================================================ 見付の実測
def _loose_parts(o):
    """メッシュを**連結成分**に割って Unity ローカルの頂点列で返す。
    ⭕ 柵は「在庫の丸太を切って並べた」物なので **1本 = 1成分**。⛔ 名前や引数で分けない —
      測るのは焼き上がった FBX で、そこに部材名は残っていない。"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    parts = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]
        seen.add(v.index)
        comp = []
        while stack:
            x = stack.pop()
            comp.append((-x.co.x, x.co.z, -x.co.y))     # → Unity ローカル
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen:
                    seen.add(y.index)
                    stack.append(y)
        parts.append(comp)
    bm.free()
    return parts


def _ext(pts):
    mn = [min(q[i] for q in pts) for i in range(3)]
    mx = [max(q[i] for q in pts) for i in range(3)]
    return mn, mx, [mx[i] - mn[i] for i in range(3)]


def mitsuke_solidity(o, span, H, px=0.002):
    """⭐ **見付けの充実率** = 見付け面(Unity の X–Y 平面)へ投影した部材の**影の面積**
    ÷ (スパン × 丈)。⛔ 部材ごとの面積を足し算しない — 柱と貫、貫と立子が**重なる**ので
    上振れする(重なりを数えない唯一の方法が、影そのものを刻んで数えること)。
    ⚠ 根入れ(Y<0)と天端より上は数えない(見付け面は地盤〜丈)。"""
    import numpy as np
    me = o.data
    me.calc_loop_triangles()
    P = [(-v.co.x, v.co.z) for v in me.vertices]        # Unity (X, Y)
    xs = [q[0] for q in P]
    x0, x1 = min(xs), max(xs)
    nx = max(4, int(round((x1 - x0) / px)))
    ny = max(4, int(round(H / px)))
    grid = np.zeros((ny, nx), dtype=bool)
    gx = x0 + (np.arange(nx) + 0.5) * (x1 - x0) / nx
    gy = (np.arange(ny) + 0.5) * H / ny
    for t in me.loop_triangles:
        a, b, c = (P[i] for i in t.vertices)
        tx0 = min(a[0], b[0], c[0]); tx1 = max(a[0], b[0], c[0])
        ty0 = min(a[1], b[1], c[1]); ty1 = max(a[1], b[1], c[1])
        if ty1 <= 0.0 or ty0 >= H or tx1 <= x0 or tx0 >= x1:
            continue
        i0 = max(0, int((tx0 - x0) / (x1 - x0) * nx) - 1)
        i1 = min(nx, int((tx1 - x0) / (x1 - x0) * nx) + 2)
        j0 = max(0, int(ty0 / H * ny) - 1)
        j1 = min(ny, int(ty1 / H * ny) + 2)
        if i1 <= i0 or j1 <= j0:
            continue
        X = gx[i0:i1][None, :]
        Y = gy[j0:j1][:, None]
        d = ((b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]))
        if abs(d) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        w2 = 1.0 - w0 - w1
        m = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        grid[j0:j1, i0:i1] |= m
    filled = float(grid.sum()) / float(nx * ny)
    return filled, (x1 - x0)


def mitsuke():
    """⭐ **腰高柵の見付けを、焼いた FBX から実測する**(庭方19巡目 指5)。
    ⛔ 部材を作り直さない。⛔ 宣言(指図 `tamagaki`)を読んで刷るのではなく、
      **成分に割った丸太の実寸**から柱・貫・立子を立てる。"""
    import vkmesh as VM
    t = tamagaki_spec()
    for (label, rel) in (("Saku_Koshidaka_%.3f" % t["pitch"],
                          "Assets/Edo/Models/Hei/Saku_Koshidaka_%.3f.fbx" % t["pitch"]),
                         ("Saku_Koshidaka_Post",
                          "Assets/Edo/Models/Hei/Saku_Koshidaka_Post.fbx")):
        path = os.path.join(V.REPO, rel)
        if not os.path.exists(path):
            print("[mitsuke] %-24s 見つからない: %s" % (label, rel))
            continue
        V.reset()
        o = V.join(VM.import_fbx_abs(path), label)
        parts = _loose_parts(o)
        _mn, _mx, whole = _ext([q for c in parts for q in c])
        span = whole[0]
        H = t["h"]
        rows = []
        for c in parts:
            mn, mx, e = _ext(c)
            vertical = e[1] >= max(e[0], e[2])
            dia = (e[0] + e[2]) / 2.0 if vertical else (e[1] + e[2]) / 2.0
            rows.append(dict(vert=vertical, dia=dia, mn=mn, mx=mx, e=e))
        vert = sorted([r for r in rows if r["vert"]], key=lambda r: -r["dia"])
        horz = sorted([r for r in rows if not r["vert"]], key=lambda r: r["mn"][1])
        post = [r for r in vert if r["dia"] > 1.5 * (vert[-1]["dia"] if vert else 0.0)]
        # ⛔ 「柱は φ0.12」と引数から決めない — **太さの分布の段**で切る
        dias = [r["dia"] for r in vert]
        if len(dias) >= 2:
            gaps = [(dias[i] - dias[i + 1], i) for i in range(len(dias) - 1)]
            g, gi = max(gaps)
            post = vert[:gi + 1] if g > 0.5 * dias[-1] else []
        tateko = [r for r in vert if r not in post]
        print("[mitsuke] ── %s ── bbox W(X)%.4f × H(Y)%.4f  成分 %d"
              % (label, whole[0], whole[1], len(parts)))
        for tag, group in (("柱", post), ("貫", horz), ("立子", tateko)):
            if not group:
                print("      %-4s **0本**" % tag)
                continue
            ds = [r["dia"] for r in group]
            print("      %-4s %2d本  径 φ%.4f〜%.4f(平均 φ%.4f)  丈 %.3f〜%.3f  "
                  "芯高 %s" % (tag, len(group), min(ds), max(ds), sum(ds) / len(ds),
                               min(r["e"][1] for r in group),
                               max(r["e"][1] for r in group),
                               " ".join("%.3f" % ((r["mn"][1] + r["mx"][1]) / 2.0)
                                        for r in group[:4])))
        if len(tateko) >= 2:
            cx = sorted((r["mn"][0] + r["mx"][0]) / 2.0 for r in tateko)
            pit = [cx[i + 1] - cx[i] for i in range(len(cx) - 1)]
            print("      立子の芯々 %.4f〜%.4f m(指図 tatekoPitchM ≤ %.3f)"
                  % (min(pit), max(pit), t["tateko_pitch"]))
        # ⭐ 影を刻んで数える(⛔ 部材面積の足し算では重なりを二重に数える)
        fill, w = mitsuke_solidity(o, span, H)
        naive = 0.0
        for r in rows:
            lo = max(0.0, r["mn"][1]); hi = min(H, r["mx"][1])
            if hi <= lo:
                continue
            naive += (hi - lo) * r["e"][0] if not r["vert"] else (hi - lo) * r["e"][0]
        naive /= (w * H)
        print("      ⭐ **見付けの充実率 %.1f%%(透け %.1f%%)** ← 影を %dmm 刻みで数えた / "
              "見付け面 %.3f×%.3f m。⚠ 部材面積の単純和は %.1f%%(重なりを二重に数える)"
              % (100.0 * fill, 100.0 * (1.0 - fill), 2, w, H, 100.0 * naive))


# ================================================================ レンダ
def shots_dan(objs, key, box):
    BT.hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    W, Hh, D = mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]
    c = [(mn[i] + mx[i]) * 0.5 for i in range(3)]
    # Unity(x,y,z) → Blender(-x, -z, y)
    b = lambda p: (-p[0], -p[2], p[1])
    S = max(W, Hh, D)
    # ① 坂下からの立面(蹴上の面 = +Z を正面に見る)
    V.studio(b((c[0], c[1], c[2] + S * 2.6)), b(tuple(c)),
             ortho_scale=max(W, Hh * 1500.0 / 1100) * 1.2, res=(1500, 1100))
    V.render(os.path.join(SHOT, "sanno_dan_%s_elev.png" % key))
    # ② 斜め上(踏面と目地・面取りを見る)
    V.studio(b((c[0] - S * 0.8, c[1] + S * 0.9, c[2] + S * 1.5)), b(tuple(c)), res=(1600, 1100))
    V.render(os.path.join(SHOT, "sanno_dan_%s_3d.png" % key))
    # ③ 近景(⚠ 引きでは目地・面取り・UV の伸びが読めない)
    V.studio(b((c[0] + W * 0.20, c[1] + 0.55, c[2] + 0.95)),
             b((c[0] + W * 0.20, c[1] - 0.15, c[2] - 0.10)), res=(1500, 1100))
    V.render(os.path.join(SHOT, "sanno_dan_%s_near.png" % key))


def shots_saku(objs, key, box):
    MA.hook()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    W, Hh, D = mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]
    c = [(mn[i] + mx[i]) * 0.5 for i in range(3)]
    b = lambda p: (-p[0], -p[2], p[1])
    S = max(W, Hh)
    V.studio(b((c[0], c[1], c[2] + S * 2.4)), b(tuple(c)),
             ortho_scale=max(W, Hh * 1500.0 / 1100) * 1.15, res=(1500, 1100))
    V.render(os.path.join(SHOT, "sanno_saku_%s_elev.png" % key))
    V.studio(b((c[0] - W * 0.55, c[1] + Hh * 0.75, c[2] + S * 1.15)),
             b((c[0], c[1] * 0.6, c[2])), res=(1600, 1100))
    V.render(os.path.join(SHOT, "sanno_saku_%s_3d.png" % key))
    V.studio(b((mn[0] + 0.45, c[1] + 0.25, c[2] + 0.75)),
             b((mn[0] + 0.45, c[1] - 0.05, c[2])), res=(1500, 1100))
    V.render(os.path.join(SHOT, "sanno_saku_%s_near.png" % key))


def u_bounds(objs):
    mn = [1e9] * 3; mx = [-1e9] * 3
    for o in objs:
        for t in unity_verts(o):
            for i in range(3):
                mn[i] = min(mn[i], t[i]); mx[i] = max(mx[i], t[i])
    return mn, mx


# ================================================================ main
def build_dan_set(specs, do_render):
    for (label, keri, fumi, w) in specs:
        for variant in ("a", "b"):
            V.reset()
            o, name = dan(keri, fumi, w, variant)
            mn, mx = u_bounds([o])
            report(o, name, "← %s" % label)
            dan_check(o, keri, fumi, w)
            if do_render and variant == "a":
                # ⭕ **並べた姿を必ず見る。**1段だけでは継ぎ目・差し込み・目地の通りが読めない
                V.reset()
                stack = []
                for i in range(6):
                    oo, _ = dan(keri, fumi, w, "ab"[i % 2], name="stack%d" % i)
                    oo.data.transform(Matrix.Translation((0, i * fumi, i * keri)))
                    oo.data.update(); stack.append(oo)
                shots_dan(stack, label_key(label), u_bounds(stack))
                V.reset()
                o, name = dan(keri, fumi, w, variant)
                mn, mx = u_bounds([o])
            V.export_fbx([o], os.path.join(OUT_DAN, name + ".fbx"))
            print("[sanno] 書き出し " + os.path.join(OUT_DAN, name + ".fbx"))


def label_key(label):
    return {"男坂": "otoko", "女坂(御成坂)": "onna", "参道の階(前庭へ)": "sando"}.get(label, "x")


def build_saku_set(spans, do_render):
    for span in spans:
        V.reset()
        o, name = saku(span)
        report(o, name)
        saku_check(o, span)
        if do_render:
            V.reset()
            run = []
            for i in range(3):
                oo, _ = saku(span, name="run%d" % i)
                oo.data.transform(Matrix.Translation((-i * span, 0, 0)))   # Blender −X = Unity +X
                oo.data.update(); run.append(oo)
            pp, _ = saku_post("runpost")
            pp.data.transform(Matrix.Translation((-2.5 * span, 0, 0)))
            pp.data.update(); run.append(pp)
            shots_saku(run, "run", u_bounds(run))
            V.reset()
            o, name = saku(span)
        V.export_fbx([o], os.path.join(OUT_SAKU, name + ".fbx"))
        print("[sanno] 書き出し " + os.path.join(OUT_SAKU, name + ".fbx"))
    V.reset()
    o, name = saku_post()
    report(o, name)
    V.export_fbx([o], os.path.join(OUT_SAKU, name + ".fbx"))
    print("[sanno] 書き出し " + os.path.join(OUT_SAKU, name + ".fbx"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    pos = [a for a in argv if not a.startswith("--")]
    do_render = "--render" in argv
    what = pos[0] if pos else "all"
    rest = pos[1:]
    if what == "audit":
        audit(); return
    if what == "mitsuke":
        mitsuke(); return
    if what in ("dan", "all"):
        if len(rest) >= 3:
            specs = [("手引き", float(rest[0]), float(rest[1]), float(rest[2]))]
        else:
            specs = kaidan_specs()
        build_dan_set(specs, do_render)
    if what in ("saku", "all"):
        spans = [float(rest[0])] if rest else [tamagaki_spec()["pitch"]]
        build_saku_set(spans, do_render)


if __name__ == "__main__":
    main()
