"""山王社(日枝神社)の部材 — **段石**(石段の一段)と**腰高柵**(玉垣・境内の柵・法尻の柵)。

    blender --background --python Tools/Blender/build_sanno_buzai.py -- dan  [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- saku [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- dan --only=男坂 [--render]   # 1本だけ焼く
    blender --background --python Tools/Blender/build_sanno_buzai.py -- dan  <蹴上> <踏面> <幅m> [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- saku <スパンm> [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- sode [--only=男坂] [--render]   # 石段の袖
    blender --background --python Tools/Blender/build_sanno_buzai.py -- sode <蹴上> <踏面> [--render]
    blender --background --python Tools/Blender/build_sanno_buzai.py -- sode_miter_list <一覧> [0.300 1.199 6.363] --render
        # 女坂の折れで袖の両端を留めに切る。一覧の各行 `段番号 a|b F±hF B±hB`(据え手の実測 2026-09-23)
    blender --background --python Tools/Blender/build_sanno_buzai.py -- sode 0.300 1.199 6.363 --depth=3.20 --render   # 丈の深い袖
    blender --background --python Tools/Blender/build_sanno_buzai.py -- sode_miter_list Tools/Blender/sanno_onna_miter_set_D320.txt 0.300 1.199 6.363 --depth=3.20 --steps=38,39,40 --render
        # 切通しで背の地盤まで上げる袖(上げの上限 = 丈 − 0.78)。綴りに `_D3.20` が入る(EDO-0430)
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

【材】`Danishi`(`Assets/Edo/Materials/Sanno/Danishi.mat`・Kirishi と同じテクスチャで灰 0.936)。
  ⛔ 2026-09-23 まで `M_FJG_Rock_001`(苔むした暗い写真計測岩)で焼いていて「石段が黒ずむ」と
  施主に指摘された(EDO-0415)。Danishi は 09-14 に起こしてあったのに FBX から名指されていなかった。
  UV はタイル 1.05m(面ごとに位相だけずらす)。作り方(箱+1〜2cm の面取り・上面は完全な平面)は
  `build_hiraishi.gen_ishibashi` に倣う。**袖(`sode`)も同じ材・同じ切石**(下の 1b 節)。
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
# ⭐ 段ごとに折れ線の向きで据える石段は、折れの外端に楔が開く(外端で w/2·sin Δ)。差し込みをそれより長くする。
#   値は (蹴上, 踏面, 幅) → (差し込み, 差し込みの天端の下げ)。⚠ 女坂の最大の折れ 4.43°(据え手の実測 2026-09-23)で
#   楔 6.363/2·sin4.43° = 0.246 ⇒ 0.35。下げ 0.005 は一番上の段の差し込みが上の平場と同じ高さで重なる z ファイト除け
#   (踏面の後ろの線 = 踏面/2 から先だけを下げる。見える踏面は水平のまま)。折れの無い男坂・参道の階は既定のまま。
LAP_BY = {(0.300, 1.199, 6.363): (0.35, 0.005)}


def lap_of(keri, fumi, w):
    return LAP_BY.get((round(keri, 3), round(fumi, 3), round(w, 3)), (LAP, 0.0))
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


def kaidan_specs(only=None):
    """指図 `kaidans` から**石の段**の (名, 蹴上, 踏面, 幅m) を出す。
    ⛔ 寸法をここに書かない。⛔ **木階は採らない** — `kaidans[].kizahashi` が立っている段
      (向拝の階【A 加藤重枝2018 木階三級】・本殿の木階)は木の階で、石の段ではない
      (→ 社殿の部材。実装側 `EdoSannoShaRebuild.Stage2_Kaidan` も同じ旗で外す)。
    ⚠ `only` に名(前方一致)を渡すとその1本だけ返す — **既存の FBX を焼き直さずに
      1本だけ足す**ため(⛔ 寸法を手で打つ道は使わない。値は指図から引く)。"""
    d = sashizu()
    out = []
    for k in d["kaidans"]:
        if k.get("kizahashi"):
            continue
        if only and not k["name"].startswith(only):
            continue
        out.append((k["name"], float(k["keri"]), float(k["fumi"]),
                    float(k["wKen"]) * float(d["const"]["ken"])))
    if only and not out:
        raise SystemExit("[sanno] ⛔ 指図 kaidans に『%s』で始まる石の段が無い" % only)
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


def _stone(x0, x1, y0, y1, z0, z1, mat, rng, name, chamfer=None, tile=None, tile_jit=False):
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
            # `tile_jit` … 面ごとに位相をずらす(⛔ 伸縮はしない)。切石は面ごとに別々に叩いた肌なので、
            #   隣の石・稜で柄が続かないほうが正しい(段石・袖石垣。基壇の既存の焼きは変えない)。
            du, dv = (rng.random(), rng.random()) if tile_jit else (0.0, 0.0)
            for loop, (a, b) in zip(f.loops, raw):
                loop[uvl].uv = (a + du, b + dv)
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
DANISHI = "Danishi"          # ⚠ Unity 側 `Assets/Edo/Materials/Sanno/Danishi.mat`(`Own.MSannoDanishi`)。
                             #   Kirishi と同じテクスチャで `_BaseColor` 0.936(H36/S11.2/V49.0)
DANISHI_TINT = 0.936         # 検証レンダ用に .mat の灰を写しただけ(FBX には行かない)
DANISHI_TILE = 1.05          # ⛔ 0.44 を段石・袖に流用しない — normal の 2×2 の継ぎ目が 0.22m ごとに立ち
                             #   小口積みに見える(鳥居・縁石と同じ判断。memory kirishi-tile-and-shu-material)


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
    return _cut_stone_material(KIRISHI, 1.0)


def _cut_stone_material(mname, tint):
    """`Kirishi` と `Danishi` の共通の作り。**Unity 側の .mat と同名の入れ物**に、検証レンダ用の
    実テクスチャ(T_Kirishi_*)を結ぶ。`tint` は Unity 側 `_BaseColor` の灰(Danishi 0.936)。
    ⛔ FBX が運ぶのは材質名だけ — ノードも tint も Unity には行かない(色の正は .mat)。"""
    m = bpy.data.materials.get(mname)
    if m:
        return m
    m = bpy.data.materials.new(mname)
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
        if abs(tint - 1.0) < 1e-9:
            nt.links.new(ai.outputs['Color'], b.inputs['Base Color'])
        else:
            mx = nt.nodes.new('ShaderNodeMixRGB')
            mx.blend_type = 'MULTIPLY'
            mx.inputs['Fac'].default_value = 1.0
            mx.inputs['Color2'].default_value = (tint, tint, tint, 1.0)
            mx.location = (-260, 300)
            nt.links.new(ai.outputs['Color'], mx.inputs['Color1'])
            nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])
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


def danishi_material():
    """**段石・石段の袖の材**。⛔ `M_FJG_Rock_001`(苔むした暗い写真計測岩)を段石に貼らない
    (2026-09-23 施主「石段が黒ずんでいる」EDO-0415)。材は 2026-09-14 に起こしてあったのに
    どの FBX からも名指されておらず結線が切れていた。"""
    return _cut_stone_material(DANISHI, DANISHI_TINT)


def dan(keri, fumi, w, variant="a", name=None):
    """段石1段。Blender: x=幅 / y=走り(+y が坂上)/ z=高さ(0 = 踏面)。
    ⇒ Unity: X=幅 / Y=高さ(0 = 踏面)/ **+Z = 坂下 = 蹴上の見え面**。"""
    name = name or dan_name(keri, fumi, w, variant)
    mat = danishi_material()
    rng = rng_of("dan", "%.3f" % keri, "%.3f" % fumi, "%.3f" % w, variant)
    cuts = _cuts(w, variant)
    lap, drop = lap_of(keri, fumi, w)
    objs = []
    for i in range(len(cuts) - 1):
        # ⚠ 上手(+y)へ LAP 潜らせる / 下へ BODY 垂らす。どちらも隣の段に隠れる
        objs.append(_stone(cuts[i], cuts[i + 1],
                           -fumi / 2.0, fumi / 2.0 + lap,
                           -(keri + BODY), 0.0, mat, rng, "%s_s%d" % (name, i),
                           tile=DANISHI_TILE, tile_jit=True))
    if drop > 0.0:
        for so in objs:
            bm = bmesh.new(); bm.from_mesh(so.data)
            # 踏面の後ろの線(y = 踏面/2)に辺の輪を入れ、その先の天端側の頂点だけを drop 下げる
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                                   plane_co=(0.0, fumi / 2.0, 0.0), plane_no=(0.0, 1.0, 0.0))
            for v in bm.verts:
                if v.co.y > fumi / 2.0 + 1e-6 and v.co.z > -CHAMFER - 1e-4:
                    v.co.z -= drop
            bm.to_mesh(so.data); bm.free(); so.data.update()
    V.dedup_materials()
    o = V.join(objs, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


def cs_f3(x):
    """C#(Unity の Mono)の `((float)x).ToString("F3", Invariant)` と同じ綴り。
    ⚠ Mono は float を**有効7桁に丸めてから**四捨五入(0.5 は 0 から遠い側)する。Python の "%.3f" は
    2 進の正確な値で丸めるので、0.2375 が Python では 0.237・Unity では 0.238 に割れる(郭の階・2026-09-24 に踏んだ)。
    ⇒ 名は実装(`EdoAssets.Own.SannoDan` / `IshidanSode`)と同じ規則で綴る。既存の組の綴りは変わらない。"""
    import struct
    from decimal import Decimal, ROUND_HALF_UP
    f = struct.unpack("f", struct.pack("f", float(x)))[0]
    d7 = Decimal(format(Decimal(repr(f)), ".6e"))      # 有効7桁(Mono の float の既定精度)
    return str(d7.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def dan_name(keri, fumi, w, variant):
    return "Dan_%s_%s_%s_%s" % (cs_f3(keri), cs_f3(fumi), cs_f3(w), variant)


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
    lap, drop = lap_of(keri, fumi, w)
    ok.append(("上手の差し込みが −Z", abs(min(zs) + (fumi / 2.0 + lap)) < 1e-3,
               "Zmin=%.4f" % min(zs)))
    ok.append(("幅が指図どおり", abs((max(xs) - min(xs)) - w) < 1e-3,
               "W=%.4f 期待 %.4f" % (max(xs) - min(xs), w)))
    ok.append(("躯体が蹴上+胴ぶん垂れている", abs(min(ys) + (keri + BODY)) < 1e-3,
               "Ymin=%.4f" % min(ys)))
    back = [t for t in uv if t[2] > -fumi / 2.0 + 1e-6]           # 見える踏面(Z ≥ −踏面/2)
    ok.append(("見える踏面は水平のまま(Y最大=0 は Z ≥ −踏面/2 の側)", abs(max(t[1] for t in back)) < 1e-4, ""))
    lapv = [t[1] for t in uv if t[2] < -fumi / 2.0 - CHAMFER - 1e-4]
    if drop > 0.0:
        ok.append(("差し込みの天端が %.3f 下がっている" % drop,
                   bool(lapv) and abs(max(lapv) + drop) < 1e-4, "%.4f" % max(lapv)))
    mats = [m.name for m in o.data.materials]
    ok.append(("材が Danishi だけ(M_FJG_Rock_001 でない)", mats == [DANISHI], str(mats)))
    bad = [t for t in ok if not t[1]]
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    if bad:
        raise SystemExit("[sanno] ⛔ 段石の検算が落ちた: %s" % ", ".join(t[0] for t in bad))


# ================================================================ 1b. 石段の袖(袖石垣)
# 【意匠 — U 部材方 2026-09-23 EDO-0415。史料は袖の作りを言わない】
#   ・段石と**同じ材 `Danishi`・同じ切石**(箱+面取り・叩き肌)。⛔ 城の野面・打込接ぎに見せない。
#   ・**切石の斜め布積み** — 積みの目地(横目地)は**石段の勾配に平行**。⇒ 1段ぶんの駒を段ごとに
#     並べると、天端の笠石(耳石)も横目地も**継ぎ目なしの一直線の斜め**になる(⛔ 段々にしない)。
#     ⚠ 横目地を水平にすると、駒が段ごとに蹴上ぶん上がるので目地が蹴上ごとに食い違う ⇒ 採らない。
#   ・竪目地は鉛直。段ごとの駒の継ぎ目にそのまま目地を立てると**芋目地**(縦に一直線)になるので、
#     **2段で一周期の a/b** に割り、段の境と目地をずらす(段石と同じ i%2 の振り分け)。
#     目地の無い段の境は面を取らない(隣の駒の面と面一で繋がり、1本の長い石に見える)。
#   ・左右対称(X について鏡像)⇒ **左右とも同じ FBX**。鏡像の2種は要らない。
SODE_T = 0.60        # 袖の厚み(X)= 笠石の幅。2尺【U】
SODE_HT = 0.30       # 笠石の天端 − 段鼻の線(鉛直)。1尺【U】
SODE_CT = 0.24       # 笠石の丈(鉛直)【U】
SODE_MITSUKE = 1.74  # 外の地盤から天端までの最大(指図 terraceWalls の実測。EDO-0415)
SODE_NE = 0.46       # 根入れ ⇒ 天端から躯体の下端まで 2.20 一定(地盤は斜面なので深めに垂らす)【U】
SODE_DEPTH = SODE_MITSUKE + SODE_NE
SODE_DEPTH_STD = SODE_DEPTH
# ⭐ **丈の深い袖**(`--depth=3.20`・EDO-0430 2026-09-24)── 切通しで袖を背の地盤まで上げる(`copingRise:"groundHi"`)と、
#   上げの上限 = 丈 − 笠の上がり 0.30 − 段石の根入れ 0.48 を超える段がある(女坂の坂下・坂上で要る上げ 1.55〜2.08)。
#   断面・材・割り・天端の線は同じで、**下端だけ**天端の線の `丈` 下の平行線へ下ろす。綴りに `_D<丈>` を挟む
#   (2.20 の既定は旧名のまま)⇒ Unity 側 `Own.IshidanSode(keri, fumi, i, depth)` / `Own.IshidanSodeMiter(…, depth)`。


def _dtag():
    return "" if abs(SODE_DEPTH - SODE_DEPTH_STD) < 1e-6 else "_D%.2f" % SODE_DEPTH
SODE_COURSE = 0.40   # 積み石の丈の目安(鉛直)【U】
SODE_STONE_L = 1.10  # 積み石の長さの目安【U】
SODE_KASA_L = 1.30   # 笠石の長さの目安【U】
SODE_CHAMFER = 0.02  # 目地の面取り(段石の 0.015 より一段大きく — 壁は引きで見るので目地を読ませる)


def sode_name(keri, fumi, variant):
    return "IshidanSode_%s_%s%s_%s" % (cs_f3(keri), cs_f3(fumi), _dtag(), variant)


def _sode_joints(P, target, off_frac):
    """一周期 P(= 踏面×2)の中の竪目地の位置。"""
    m = max(1, int(round(P / target)))
    step = P / m
    return [((off_frac * step) + t * step) % P for t in range(m)], m


def _on_joint(s, joints, P, eps=1e-6):
    s = s % P
    return any(abs(s - j) < eps or abs(abs(s - j) - P) < eps for j in joints)


def _sode_stone(ya, yb, v0, v1, cham_a, cham_b, keri, fumi, mat, uvkey, s0, name):
    """袖の石1枚。Blender: x=厚み(±SODE_T/2)/ y=走り(+y 坂上)/ z=高さ。
    まず (x, y, 天端の線からの鉛直の下がり) の箱で面を取り、そのあと**鉛直に剪断**して勾配へ載せる
    (z += HT + (y + 踏面/2)·蹴上/踏面)。⇒ 竪目地・側面は平面のまま、横目地と天端が勾配に平行。
    cham_a / cham_b … 走りの端(ya / yb)が目地か。目地でない端の4辺は面を取らない。"""
    T = SODE_T
    bm = bmesh.new()
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res["verts"]
    bmesh.ops.scale(bm, verts=vs, vec=(T, yb - ya, v0 - v1))
    bmesh.ops.translate(bm, verts=vs, vec=(0.0, (ya + yb) / 2.0, -(v0 + v1) / 2.0))
    eps = 1e-6
    keep = []
    for e in bm.edges:
        a, b = e.verts[0].co, e.verts[1].co
        on_a = abs(a.y - ya) < eps and abs(b.y - ya) < eps
        on_b = abs(a.y - yb) < eps and abs(b.y - yb) < eps
        if (on_a and not cham_a) or (on_b and not cham_b):
            continue
        keep.append(e)
    try:
        bmesh.ops.bevel(bm, geom=keep, offset=SODE_CHAMFER, offset_type='OFFSET',
                        segments=1, profile=0.5, affect='EDGES', clamp_overlap=True)
    except Exception as ex:
        print("[sanno] 面取りを飛ばした: %s" % ex)
    # ⚠ UV は**剪断の前**に、駒をまたいで連続する座標で貼る — 走りは周期座標 s(= y + s0 + 踏面/2)、
    #   高さは天端の線からの下がり。⛔ 駒ごとの局所座標や面ごとの乱数で貼ると、目地の無い段の境で
    #   柄が切れて**細い偽の目地**が立つ(2026-09-23 近景で実見)。位相のずらしは石ごと・面の向きごと
    #   (`uvkey` = 段・周期の中の石の番号)⇒ 段の境をまたぐ1本の石は両側の駒で同じ柄になる。
    BT.ensure_outward(bm)
    bm.normal_update()
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        r = rng_of("sode-uv", uvkey, ax, n[ax] > 0)
        du, dv = r.random(), r.random()
        for loop in f.loops:
            co = loop.vert.co
            sy = co.y + s0 + fumi / 2.0
            a, b = (co.x, sy) if ax == 2 else ((co.x, co.z) if ax == 1 else (sy, co.z))
            loop[uvl].uv = (a / DANISHI_TILE + du, b / DANISHI_TILE + dv)
    sl = keri / fumi
    for v in bm.verts:
        v.co.z += SODE_HT + (v.co.y + fumi / 2.0) * sl
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free(); me.update()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def sode(keri, fumi, variant="a", name=None):
    """石段の袖の**1段ぶんの駒**。段石 `dan(keri, fumi, …)` の段 i に i%2 で a/b を合わせる。
    Unity: X=厚み(±0.30)/ Y=高さ / **+Z = 坂下**。ピボット = **段 i の段石と同じ点**
    (走りの中心・その段の踏面の高さ)の、**袖の厚みの中心**。
    天端 Y = HT + (踏面/2 − Z)·蹴上/踏面(Z=+踏面/2 が段 i の段鼻の真横)。"""
    name = name or sode_name(keri, fumi, variant)
    mat = danishi_material()
    f = fumi
    P = 2.0 * f
    s0 = 0.0 if variant == "a" else f          # 周期の中での、この駒の坂下の端
    # 段(鉛直の下がり): 0 = 天端の線
    n = max(1, int(round((SODE_DEPTH - SODE_CT) / SODE_COURSE)))
    ch = (SODE_DEPTH - SODE_CT) / n
    courses = [(0.0, SODE_CT, SODE_KASA_L, 0.25)]
    for c in range(n):
        courses.append((SODE_CT + c * ch, SODE_CT + (c + 1) * ch, SODE_STONE_L,
                        0.0 if c % 2 == 0 else 0.5))
    objs = []
    for ci, (v0, v1, L, off) in enumerate(courses):
        joints, m = _sode_joints(P, L, off)
        step = P / m
        cuts = sorted(set([s0, s0 + f] + [j for j in joints if s0 + 1e-6 < j < s0 + f - 1e-6]))
        for pi in range(len(cuts) - 1):
            sa, sb = cuts[pi], cuts[pi + 1]
            # 周期座標 s → Blender y(坂下の端 = −f/2)
            ya, yb = sa - s0 - f / 2.0, sb - s0 - f / 2.0
            sid = int((((sa + sb) / 2.0 - joints[0]) % P) // step)   # 周期の中の石の番号
            uvkey = "%.3f|%.3f|%d|%d" % (keri, fumi, ci, sid)
            objs.append(_sode_stone(ya, yb, v0, v1,
                                    _on_joint(sa, joints, P), _on_joint(sb, joints, P),
                                    keri, fumi, mat, uvkey, s0, "%s_c%d_%d" % (name, ci, pi)))
    V.dedup_materials()
    o = V.join(objs, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


def sode_check(o, keri, fumi):
    """⭕ 焼いた直後の自動検算(期待値は設計の定数と引数から。形は頂点から測る)。"""
    ok = []
    uv = unity_verts(o)
    xs = [t[0] for t in uv]; ys = [t[1] for t in uv]; zs = [t[2] for t in uv]
    T = SODE_T
    ok.append(("左右対称(左右の袖が同じ FBX で済む)", check_mirror_x(o), ""))
    ok.append(("側面が X=±T/2 の平面(接する面)", abs(max(xs) - T / 2) < 1e-4 and abs(min(xs) + T / 2) < 1e-4,
               "X %.4f..%.4f" % (min(xs), max(xs))))
    nface = sum(1 for t in uv if abs(abs(t[0]) - T / 2) < 1e-5)
    ok.append(("側面の平面に頂点が乗っている", nface >= 8, "%d 点" % nface))
    ok.append(("走りが Z ±踏面/2(段石の踏面と同じ区間)",
               abs(max(zs) - fumi / 2) < 1e-4 and abs(min(zs) + fumi / 2) < 1e-4,
               "Z %.4f..%.4f" % (min(zs), max(zs))))
    top = lambda z: SODE_HT + (fumi / 2.0 - z) * keri / fumi
    over = max(t[1] - top(t[2]) for t in uv)
    ok.append(("天端が段鼻の線 +HT の斜めの一直線を越えない", over < 1e-4, "超過 %.5f" % over))
    tops = [t for t in uv if abs(t[1] - top(t[2])) < 1e-5 and abs(t[0]) < T / 2 - 0.01]
    ok.append(("天端の線上に頂点がある(笠石の天端がその線)", len(tops) >= 4, "%d 点" % len(tops)))
    under = min(t[1] - (top(t[2]) - SODE_DEPTH) for t in uv)
    ok.append(("下端が天端 −%.2f の平行線" % SODE_DEPTH, abs(under) < 1e-4, "%.5f" % under))
    mats = [m.name for m in o.data.materials]
    ok.append(("材が Danishi だけ", mats == [DANISHI], str(mats)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    bad = [t for t in ok if not t[1]]
    if bad:
        raise SystemExit("[sanno] ⛔ 袖の検算が落ちた: %s" % ", ".join(t[0] for t in bad))


# ---------------------------------------------------------------- 1d. 法の面へ突き付ける段石と袖(EDO-0442 施主裁定B・2026-09-26)
# 山王 前庭の北の切り込み(`TW_Zentei_Kiri`)へ参道の階を引き込んだ。返しと隅の駒は野面で**法 1:0.25**(施主の決めた作り・変えない)。
# 段石の小口・袖の背は鉛直なので、法の面と突き付けると上端に口・下端にめり込みが残る(0.25 × 見える丈 / 2)。
# ⇒ **駒の端そのものを法の面で切る**(平面 bisect + 切り口を塞ぐ)。切る前の駒は平らな駒 `dan` / `sode` と同じ物・同じ局所座標・同じピボット。
#   ・面の式は Unity の局所座標で書く(X 幅 / Y 高さ / Z 走り・+Z 坂下)。法 NORI = 0.25(1m 上がるごとに 0.25 後退)。
#   ・切り口の UV は `_stone` のタイル貼りと同じ(DANISHI_TILE・面ごとに位相だけずらす)。外の面の UV は bisect の補間で連続のまま。
#   ⛔ 位置・長さは据え手が実メッシュで測った値(従属値)を引数で受ける。部材方は据え方を書かない。
NORI = 0.25                 # 返し・隅の駒の法(野面の乱積み `Sanno_Nozura*`・1:0.25)
SODE_NORI_KNEE = -0.60      # 袖の背の法を切るのはこの高さ(袖の局所 Y)から上。下は鉛直(地中 ── 相手の野面も根入れ 0.20 で終わる)
SODE_NORI_E = [round(-0.30 + 0.05 * k, 2) for k in range(9)]    # 焼く背の出(−0.30〜+0.10・0.05 刻み)


def _u2b(p):
    """Unity 局所 → Blender(X = −x, Y = z, Z = −y の逆)。"""
    return Vector((-p[0], -p[2], p[1]))


def _clip(o, planes, seed):
    """o を半空間の積へ切る。planes = [(P, N)](Unity 局所)で、**dot(x − P, N) > 0 の側を捨てる**。
    島ごとに凸な駒(箱+面取り・剪断)を前提に、切り口の輪を n 角形で塞ぐ。捨てた側に残る孤立頂点は消す(README の罠)。"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    rng = random.Random(seed)
    for (P, N) in planes:
        if not bm.faces:
            break
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7,
                               plane_co=_u2b(P), plane_no=_u2b(N), clear_outer=True, clear_inner=False)
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bnd = [e for e in bm.edges if e.is_boundary]
        if bnd:
            res = bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
            bm.normal_update()
            nb = _u2b(N).normalized()
            for f in res["faces"]:
                if f.normal.dot(nb) < 0:
                    f.normal_flip()
                ax = max(range(3), key=lambda k: abs(f.normal[k]))
                du, dv = rng.random(), rng.random()
                for loop in f.loops:
                    co = loop.vert.co
                    a, b = (co.x, co.y) if ax == 2 else ((co.x, co.z) if ax == 1 else (co.y, co.z))
                    loop[uvl].uv = (a / DANISHI_TILE + du, b / DANISHI_TILE + dv)
    bm.normal_update()
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return o


def _dup(o, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name
    bpy.context.scene.collection.objects.link(c)
    return c


def _union(parts, name):
    parts = [p for p in parts if p is not None and len(p.data.polygons) > 0]
    V.dedup_materials()
    o = V.join(parts, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o


# ---- A. 背を法に切った袖石 ---------------------------------------------------------
def sode_nori_name(keri, fumi, e, variant):
    return "IshidanSodeNori_%s_%s%s_E%s_%s" % (cs_f3(keri), cs_f3(fumi), _dtag(), _sgn_h(e), variant)


def sode_nori_yc(keri):
    """背の出 e を測る高さ(袖の局所 Y)= 段 i の踏面(0)と、平らな駒の背での天端(HT + 蹴上)の中ほど。"""
    return (SODE_HT + keri) / 2.0


def sode_nori(keri, fumi, e, variant, name=None, knee=SODE_NORI_KNEE):
    """平らな袖 `sode(keri, fumi, variant)` の坂上の端(背・−Z)を法 1:NORI の面で切った駒。
    背の面: Z = −踏面/2 − e − NORI·(Y − Yc)(Yc = `sode_nori_yc`)── 上ほど坂上へ出る(相手の野面の法と平行)。
    e > 0 は平らな駒より坂上へ出る(次の段の駒の頭を継いで伸ばす ⇒ 天端・目地の斜めは一直線のまま)、e < 0 は詰める。
    knee より下は背を鉛直に止める(地中で駒が痩せ切らないように)。"""
    name = name or sode_nori_name(keri, fumi, e, variant)
    a, _ = sode(keri, fumi, variant, name=name + "_a")
    other = "b" if variant == "a" else "a"
    objs = [a]
    nx = 1 + int(math.ceil(max(0.0, e + NORI * (SODE_HT + 2 * keri) + 0.05) / fumi))
    for k in range(1, nx + 1):                  # 坂上へ継ぐ駒(周期の続き ── a の次は b)
        b, _ = sode(keri, fumi, other if k % 2 else variant, name=name + "_n%d" % k)
        b.data.transform(Matrix.Translation((0.0, k * fumi, k * keri))); b.data.update()
        objs.append(b)
    V.dedup_materials()
    whole = V.join(objs, name + "_w")
    yc = sode_nori_yc(keri)
    zk = -fumi / 2.0 - e - NORI * (knee - yc)          # 膝での背の Z
    back = ((0.0, yc, -fumi / 2.0 - e), (0.0, -NORI, -1.0))   # Z + NORI·Y が式より小さい側(坂上)を捨てる
    p2 = _dup(whole, name + "_p2")
    _clip(whole, [((0.0, 0.0, zk), (0.0, 0.0, -1.0))], name + "1")          # 膝の鉛直面より前
    _clip(p2, [((0.0, 0.0, zk), (0.0, 0.0, 1.0)), back], name + "2")        # 膝より坂上の、法の面より前(膝より上だけが残る)
    return _union([whole, p2], name), name


def sode_nori_check(o, keri, fumi, e, knee=SODE_NORI_KNEE):
    ok = []
    uv = unity_verts(o)
    T = SODE_T
    yc = sode_nori_yc(keri)
    zb = lambda y: -fumi / 2.0 - e - NORI * (max(y, knee) - yc)
    ok.append(("左右対称(左右の袖が同じ FBX・頂点ごとに鏡の相手が 1e-4 以内)", _mirror_tol(o), ""))
    ok.append(("側面が X=±T/2 の平面", abs(max(t[0] for t in uv) - T / 2) < 1e-4 and abs(min(t[0] for t in uv) + T / 2) < 1e-4, ""))
    ok.append(("坂下の端は平らな駒のまま Z=+踏面/2", abs(max(t[2] for t in uv) - fumi / 2) < 1e-4, "%.4f" % max(t[2] for t in uv)))
    worst = max(zb(t[1]) - t[2] for t in uv)
    ok.append(("背の法の面より坂上に頂点が無い", worst < 1e-4, "最大 %.5f" % worst))
    onb = [t for t in uv if abs(t[2] - zb(t[1])) < 1e-4 and t[1] > knee + 0.05]
    ok.append(("背の法の面に頂点が乗る(膝より上)", len(onb) >= 8, "%d 点" % len(onb)))
    top = lambda z: SODE_HT + (fumi / 2.0 - z) * keri / fumi
    over = max(t[1] - top(t[2]) for t in uv)
    ok.append(("天端が段鼻の線 +HT の斜めの一直線を越えない", over < 1e-4, "超過 %.5f" % over))
    under = min(t[1] - (top(t[2]) - SODE_DEPTH) for t in uv)
    ok.append(("下端が天端 −%.2f の平行線より下へ出ない" % SODE_DEPTH, under > -1e-4, "%.5f" % under))
    # 背の見付(膝〜天端)で法を測り直す: 背の面の頂点を (Y, Z) で直線に当てる
    if len(onb) >= 2:
        ys = [t[1] for t in onb]; zs = [t[2] for t in onb]
        my, mz = sum(ys) / len(ys), sum(zs) / len(zs)
        sl = sum((y - my) * (z - mz) for y, z in zip(ys, zs)) / max(1e-9, sum((y - my) ** 2 for y in ys))
        ok.append(("背の法 = 1:%.2f(実測 −dZ/dY)" % NORI, abs(-sl - NORI) < 1e-3, "%.4f" % -sl))
    loose = sum(1 for v in o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats = [m.name for m in o.data.materials]
    ok.append(("材が Danishi だけ", mats == [DANISHI], str(mats)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    if any(not t_[1] for t_ in ok):
        raise SystemExit("[sanno] ⛔ 背を法に切った袖の検算が落ちた")


def _mirror_tol(o, tol=1e-4):
    """鏡像対称を頂点ごとの最近傍で確かめる(bisect の交点は丸めの升目の境に落ちて `check_mirror_x` が偽の不一致を出す)。"""
    from mathutils import kdtree
    vs = [v.co.copy() for v in o.data.vertices]
    kd = kdtree.KDTree(len(vs))
    for i, c in enumerate(vs):
        kd.insert(c, i)
    kd.balance()
    return all(kd.find(Vector((-c.x, c.y, c.z)))[2] < tol for c in vs)


# ---- B. 端を法の面(と隅の駒のもう一面)で切った段石 -------------------------------
def _end5(e):
    """端の組を (d, za, wall, ang, nori) に揃える(旧い 3 つ組もそのまま通す)。"""
    e = tuple(e)
    return e + (None,) * (5 - len(e))


def _end_spec(d, za, wall, ang=None, nori=None):
    """端の綴り。d = None は切らない('0')。za = None は端の全長を返しの法で切る。
    wall = 'B'(相手の隅が坂上 = 小口の −Z 側が返し)/ 'F'(坂下)。
    ang を持つ端は**平面で斜めに切る**(`d±0.300A±43.000` ── 法 nori を持てば `N±0.250` を足す。無ければ鉛直)。"""
    if d is None:
        return "0"
    s = "d" + _sgn_h3(d)
    if ang is not None:
        s += "A" + _sgn_h3(ang)
        if nori:                                    # 法 0 は鉛直と同じ綴り(C# の DanKiriEnd(d, deg, 0) と揃える)
            s += "N" + _sgn_h3(nori)
        return s
    if za is not None:
        s += wall + _sgn_h3(za)
        if nori is not None:                        # 跨ぐ端の法を綴る(野面の乱積み 1:0.3 ── EDO-0437。無ければ既定 1:0.25)
            s += "N" + _sgn_h3(nori)
    return s


def _oblique_x(d, ang, nori, w, yc):
    """斜めに切る端の面: s·X = w/2 − d + tan(ang)·Z + nori·(Y − Yc)(その端の側で見た X)。"""
    t = math.tan(math.radians(ang)); n = nori or 0.0
    return lambda y, z: w / 2.0 - d + t * z + n * (y - yc)


def _sgn_h3(x):
    return ("+" if x >= 0 else "-") + cs_f3(abs(x))


def dan_kiri_name(keri, fumi, w, variant, endL, endR):
    return "DanKiri_%s_%s_%s_%s_L%s_R%s" % (cs_f3(keri), cs_f3(fumi), cs_f3(w), variant,
                                            _end_spec(*_end5(endL)), _end_spec(*_end5(endR)))


def dan_kiri(keri, fumi, w, variant, endL, endR, name=None):
    """段石 `dan(keri, fumi, w, variant)` の両の小口を、脇の相手に合わせて切った駒。端 = (d, za, wall)。
    ・返しの面(隅の駒の、石段の芯を向く面): X = s·(w/2 − d + NORI·(Y − Yc))、Yc = −蹴上/2(その段の蹴上の中ほど)。
      d > 0 は小口より内(食い込みを削る)・d < 0 は外(小口を伸ばして口を塞ぐ ── 端の石を伸ばしてから切る)。
    ・za を持つ端は**二つの面に跨る**: 隅の駒のもう一面(坂下/坂上を向く面・袖の背が当たる面)
      Z = za ∓ NORI·(Y − Yc) の**返しの側**だけを上の面で切り、**袖の側**は小口 X = s·w/2 のまま(袖の側面に突き付く)。
      ⇒ 端が段に欠ける(欠いた奥の面は隅の駒の面と平行な法)。
    ・za を持つ端に nori を添えると、返しの面・欠いた奥の面とも法 nori(既定 NORI = 0.25)── 相手が野面の乱積み 1:0.3 の隅の駒
      (EDO-0437 参道の階の段 1 ── 綴り `d+0.222B+0.024N+0.300`)。d・za は石の出の包絡(見える当たりの最も深い石)。
    ・za = None は端の全長を返しの面で切る(`AbutStepEndsToWalls` の高さの中ほどの突き付けの代わり ── 口・めり込みが 0)。
    ・ang を持つ端は**平面で任意の角に切る**(EDO-0430 女坂の段 0・1 ── 端が鉛直の土留めと平面で斜めに交わる):
      面 s·X = w/2 − d + tan(ang)·Z + nori·(Y − Yc)。d は**踏面の中心の線 Z = 0・蹴上の中ほど Y = Yc** で測る食い込み、
      ang は面の平面の線が段の走り(Z)となす角で **+ は坂下(+Z)ほど外へ開く**、nori は法(None = 鉛直)。
      外へ出る所は小口を伸ばしてから切る(d < 0 と同じ)。"""
    name = name or dan_kiri_name(keri, fumi, w, variant, endL, endR)
    o, _ = dan(keri, fumi, w, variant, name=name + "_w")
    yc = -keri / 2.0
    ybot = -(keri + BODY)
    lap, _drop = lap_of(keri, fumi, w)
    for s, (d, za, wall, ang, nori) in ((-1, _end5(endL)), (1, _end5(endR))):
        if d is None:
            continue
        if ang is not None:
            xo = _oblique_x(d, ang, nori, w, yc)
            ext = max(xo(y, z) for y in (ybot, 0.0) for z in (-(fumi / 2.0 + lap), fumi / 2.0)) - w / 2.0
            if ext > 0:
                _stretch_end(o, s, w, ext + 0.02)
            t = math.tan(math.radians(ang)); n = nori or 0.0
            _clip(o, [((s * (w / 2.0 - d), yc, 0.0), (s, -n, -t))], name + "A%d" % s)   # 面の外(s·X − t·Z − n·(Y−Yc) > w/2 − d)を捨てる
            continue
        nb = NORI if nori is None else nori                                # 跨ぐ端の法(既定 1:0.25・野面 1:0.3)
        ext = max(0.0, -d + nb * (yc - ybot)) + 0.02 if d < 0 else 0.0
        if ext > 0:
            _stretch_end(o, s, w, ext)
        ret = ((s * (w / 2.0 - d), yc, 0.0), (s, -nb, 0.0))              # 返しの面の外を捨てる
        if za is None:
            _clip(o, [ret], name + "r%d" % s)
            continue
        sg = 1.0 if wall == "B" else -1.0                                   # B: 隅は坂上(Z < za)
        wall_side = ((0.0, yc, za), (0.0, nb, sg))                        # 袖の側を捨てる = 隅の側を残す
        sode_side = ((0.0, yc, za), (0.0, -nb, -sg))                      # 隅の側を捨てる = 袖の側を残す
        pS = _dup(o, name + "_S%d" % s)
        _clip(o, [ret, wall_side], name + "R%d" % s)
        _clip(pS, [((s * w / 2.0, 0.0, 0.0), (s, 0.0, 0.0)), sode_side], name + "S%d" % s)
        o = _union([o, pS], name + "_w")
    o.name = name; o.data.name = name
    V.set_origin(o, (0.0, 0.0, 0.0))
    return o, name


def _stretch_end(o, s, w, ext):
    """s 側の小口(と面取りの輪)の頂点を外へ ext 動かす。幅方向の UV も同じだけずらす(柄を伸ばさない)。"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    moved = {}
    for v in bm.verts:
        X = -v.co.x
        if s * X > w / 2.0 - CHAMFER - 1e-4:
            v.co.x -= s * ext                       # Unity X += s·ext
            moved[v.index] = -s * ext               # Blender x の変位
    bm.normal_update()
    for f in bm.faces:
        ax = max(range(3), key=lambda k: abs(f.normal[k]))
        if ax == 0:
            continue
        for loop in f.loops:
            dx = moved.get(loop.vert.index)
            if dx is not None:
                u, vv = loop[uvl].uv
                loop[uvl].uv = (u + dx / DANISHI_TILE, vv)
    bm.to_mesh(o.data); bm.free(); o.data.update()


def dan_kiri_check(o, keri, fumi, w, endL, endR):
    ok = []
    uv = unity_verts(o)
    yc = -keri / 2.0
    ok.append(("踏面がピボットの高さ(Y最大=0)", abs(max(t[1] for t in uv)) < 1e-4, "%.4f" % max(t[1] for t in uv)))
    ok.append(("蹴上の面が +Z", abs(max(t[2] for t in uv) - fumi / 2.0) < 1e-3, ""))
    for s, (d, za, wall, ang, nori) in ((-1, _end5(endL)), (1, _end5(endR))):
        if d is None:
            continue
        if ang is not None:
            xo = _oblique_x(d, ang, nori, w, yc)
            bite = max(s * t[0] - xo(t[1], t[2]) for t in uv)
            ok.append(("%s 端: 斜めの面より外に頂点が無い" % "LR"[s > 0], bite < 1e-4, "最大 %.5f" % bite))
            on = [t for t in uv if abs(s * t[0] - xo(t[1], t[2])) < 1e-4]
            ok.append(("%s 端: 斜めの面に頂点が乗る" % "LR"[s > 0], len(on) >= 4, "%d 点" % len(on)))
            if len(on) >= 3:
                # 面の上の頂点を s·X = a + t·Z + n·Y に当て直して角と法を測り直す(最小二乗)
                import numpy as _np
                A_ = _np.array([[1.0, t_[2], t_[1]] for t_ in on]); bx = _np.array([s * t_[0] for t_ in on])
                sol = _np.linalg.lstsq(A_, bx, rcond=None)[0]
                ok.append(("%s 端: 面の角 %.3f°(実測)" % ("LR"[s > 0], ang), abs(math.degrees(math.atan(sol[1])) - ang) < 0.01,
                           "%.4f°" % math.degrees(math.atan(sol[1]))))
                ok.append(("%s 端: 面の法 %.3f(実測)" % ("LR"[s > 0], nori or 0.0), abs(sol[2] - (nori or 0.0)) < 1e-3, "%.4f" % sol[2]))
            continue
        nb = NORI if nori is None else nori
        xb = lambda y: w / 2.0 - d + nb * (y - yc)
        sg = 1.0 if wall == "B" else -1.0
        inwall = lambda t: za is None or sg * (t[2] - (za - sg * nb * (t[1] - yc))) < -1e-4   # 面の上の頂点は袖の側に数える
        bite = max([s * t[0] - xb(t[1]) for t in uv if inwall(t)] + [-1.0])
        ok.append(("%s 端: 返しの法の面より外に頂点が無い" % "LR"[s > 0], bite < 1e-4, "最大 %.5f" % bite))
        on = [t for t in uv if abs(s * t[0] - xb(t[1])) < 1e-4]
        ok.append(("%s 端: 返しの法の面に頂点が乗る" % "LR"[s > 0], len(on) >= 4, "%d 点" % len(on)))
        if za is not None:
            over = max([s * t[0] - w / 2.0 for t in uv if not inwall(t)] + [-1.0])
            ok.append(("%s 端: 袖の側は小口 X=±w/2 を越えない" % "LR"[s > 0], over < 1e-4, "%.5f" % over))
            onA = [t for t in uv if abs(sg * (t[2] - (za - sg * nb * (t[1] - yc)))) < 1e-4 and s * t[0] > xb(t[1]) - 1e-4]
            ok.append(("%s 端: 欠いた奥の面が隅の駒のもう一面の上" % "LR"[s > 0], len(onA) >= 3, "%d 点" % len(onA)))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats = [m.name for m in o.data.materials]
    ok.append(("材が Danishi だけ", mats == [DANISHI], str(mats)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    if any(not t_[1] for t_ in ok):
        raise SystemExit("[sanno] ⛔ 端を切った段石の検算が落ちた")


def _parse_end(tok):
    """`-` / `d+0.219` / `d+0.219B+0.040`(F も可)/ `d+0.222B+0.024N+0.300`(跨ぐ・法)/ `d+0.300A+43.000`(斜め・鉛直)/ `d+0.300A+43.000N+0.250`(斜め・法)。"""
    if tok in ("-", "0"):
        return (None, None, "B")
    assert tok[0] == "d", tok
    body = tok[1:]
    k = body.find("A")
    if k > 0:
        d = float(body[:k]); rest = body[k + 1:]
        kn = rest.find("N")
        if kn > 0:
            return (d, None, "B", float(rest[:kn]), float(rest[kn + 1:]))
        return (d, None, "B", float(rest), None)
    for wch in ("B", "F"):
        k = body.find(wch)
        if k > 0:
            rest = body[k + 1:]; kn = rest.find("N")
            if kn > 0:                              # 跨ぐ端の法(`d+0.222B+0.024N+0.300`)
                return (float(body[:k]), float(rest[:kn]), wch, None, float(rest[kn + 1:]))
            return (float(body[:k]), float(rest), wch)
    return (float(body), None, "B")


def read_kiri_list(path):
    """各行 `段番号 a|b L<端> R<端>`(# 以降は註)。端は `_parse_end`。⛔ 値は据え手の実測を丸め直さない。"""
    rows = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            i, var, l, r = ln.split()
            i = int(i)
            if var != "ab"[i % 2]:
                raise SystemExit("[sanno] ⛔ 段 %d の a/b が i%%2 と合わない: %s" % (i, ln))
            assert l[0] == "L" and r[0] == "R", ln
            rows.append((i, var, _parse_end(l[1:]), _parse_end(r[1:])))
    return rows


def build_sode_nori_set(keri, fumi, es, do_render):
    for e in es:
        for variant in ("a", "b"):
            V.reset()
            o, name = sode_nori(keri, fumi, e, variant)
            report(o, name, "← 背を法に切った袖(e %+.2f)" % e)
            sode_nori_check(o, keri, fumi, e)
            V.export_fbx([o], os.path.join(OUT_DAN, name + ".fbx"))
            print("[sanno] 書き出し " + os.path.join(OUT_DAN, name + ".fbx"))


def build_dan_kiri_list(keri, fumi, w, rows, do_render, key="kiri", export=True):
    """一覧の各行を焼く。export=False は焼かずに検算と組み絵だけ(`dan_kiri_try` ── 実測の値が無いときの型の確かめ)。"""
    for (i, var, eL, eR) in rows:
        V.reset()
        o, name = dan_kiri(keri, fumi, w, var, eL, eR)
        report(o, name, "← 段 %d" % i)
        dan_kiri_check(o, keri, fumi, w, eL, eR)
        if export:
            V.export_fbx([o], os.path.join(OUT_DAN, name + ".fbx"))
            print("[sanno] 書き出し " + os.path.join(OUT_DAN, name + ".fbx"))
    if do_render:
        for pth in shots_kiri_set(keri, fumi, w, rows, key):
            print("[sanno] 検証レンダ " + pth)


def _proxy_wall(s, end, keri, fumi, w, mat, name):
    """検証だけの相手の塊(**焼かない**): 端の面の外側に据わる箱。斜めの端と全長を法で切る端だけ描く。"""
    d, za, wall, ang, nori = _end5(end)
    if d is None or (ang is None and za is not None):
        return None
    yc = -keri / 2.0
    if ang is not None:
        t = math.tan(math.radians(ang)); n = nori or 0.0
        N = (-s, n, t)
    else:
        N = (-s, NORI, 0.0)
    bm = bmesh.new()
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=r["verts"], vec=(2.6, fumi + 2.4, keri + 1.2))
    bmesh.ops.translate(bm, verts=r["verts"], vec=_u2b((s * (w / 2.0 + 0.9), -keri / 2.0 + 0.15, 0.0)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7,
                           plane_co=_u2b((s * (w / 2.0 - d), yc, 0.0)), plane_no=_u2b(N), clear_outer=True)
    bnd = [e_ for e_ in bm.edges if e_.is_boundary]
    if bnd:
        bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free(); me.update()
    return o


def shots_kiri_set(keri, fumi, w, rows, key):
    """一覧の段を石段に組んで刷る(段 i は踏面の天端 (i+1)·蹴上・芯 Z = −i·踏面)。
    斜めの端・全長を法で切る端には相手の面に沿う**検証の塊**を添える(口もめり込みも無く面一に見えるはず)。
    magenta は背景をマゼンタにし塊と地面を消して、切り口の蓋の抜けを探す。"""
    V.reset()
    wm = bpy.data.materials.new("render_wall"); wm.use_nodes = True
    wb = next(n for n in wm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    wb.inputs['Base Color'].default_value = (0.30, 0.28, 0.26, 1.0)
    placed, walls = [], []
    for (i, var, eL, eR) in rows:
        o, _ = dan_kiri(keri, fumi, w, var, eL, eR, name="st%d" % i)
        tr = Matrix.Translation(_u2b((0.0, (i + 1) * keri, -i * fumi)))
        o.data.transform(tr); o.data.update(); placed.append(o)
        for s, e in ((-1, eL), (1, eR)):
            pw = _proxy_wall(s, e, keri, fumi, w, wm, "wall_%d_%d" % (i, s))
            if pw is not None:
                pw.data.transform(tr); pw.data.update(); walls.append(pw)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0.0, 0.0))
    g = bpy.context.active_object
    g.scale = (w + 8.0, len(rows) * fumi + 8.0, 1.0)
    gm = bpy.data.materials.new("render_ground"); gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    gb.inputs['Base Color'].default_value = (0.20, 0.17, 0.12, 1.0)
    g.data.materials.append(gm)
    V.dedup_materials()
    n = len(rows)
    ym = n * fumi / 2.0                          # Blender y の中ほど(坂上 = +y)
    zt = (n + 1) * keri
    out = []
    shots = [("3d", (w * 0.9, -3.0 - n * 0.3, zt + 2.6), (0.0, ym, zt * 0.4), None),
             ("plan", (0.0, ym, 12.0), (0.0, ym + 0.001, 0.0), max(w, n * fumi) + 3.2)]
    for sx in (-1, 1):                           # 端ごとの寄り(Blender x = −Unity X)
        xb = -sx * w / 2.0
        shots.append(("near%s" % "LR"[sx > 0], (xb + sx * 1.3, -2.4, zt + 1.3), (xb, ym * 0.8, zt * 0.45), None))
    shots.append(("magenta", (w * 0.9, -3.0 - n * 0.3, zt + 2.6), (0.0, ym, zt * 0.4), None))
    for (tag, cam, at, orth) in shots:
        V.studio(cam, at, ortho_scale=orth, res=(1600, 1100))
        if tag == "magenta":
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
            g.hide_render = True
            for o_ in walls:
                o_.hide_render = True
        _hook_cut_stone()
        pth = os.path.join(SHOT, "sanno_dankiri_%s_%s.png" % (key, tag))
        V.render(pth); out.append(pth)
    return out


def shots_kiri(keri, fumi, w, d1, za1, key):
    """参道の階の北の切り込みの組み絵: 段 0〜4・両脇の袖(段 0 は平ら・段 1 は背を法に切った駒)・
    両脇の隅の野面の塊(**検証だけの箱** ── 返しの面 X = ±(w/2 − d1 + NORI·(Y − Yc1))・もう一面 Z = za1 − NORI·(Y − Yc1)、段 1 の局所)。
    段 1 は二つの面に跨る端・段 2〜4 は返しの法で全長を切る(d は段ごとに法から従属)。"""
    V.reset()
    T = SODE_T
    b = NORI
    yc1w = 2 * keri - keri / 2.0                # 段 1 の蹴上の中ほど(世界 Y)
    z1w = -fumi                                  # 段 1 の芯(世界 Z)
    placed = []

    def put(o, tx, ty, tz):
        o.data.transform(Matrix.Translation(_u2b((tx, ty, tz)))); o.data.update(); placed.append(o)

    for i in range(5):
        v = "ab"[i % 2]
        if i == 0:
            o, _ = dan(keri, fumi, w, v, name="d0")
        elif i == 1:
            o, _ = dan_kiri(keri, fumi, w, v, (d1, za1, "B"), (d1, za1, "B"), name="d1")
        else:
            di = d1 - b * keri * (i - 1)
            o, _ = dan_kiri(keri, fumi, w, v, (di, None, "B"), (di, None, "B"), name="d%d" % i)
        put(o, 0.0, (i + 1) * keri, -i * fumi)
    # 袖: 段 1 の背は隅の駒のもう一面に一致する e(連続値で組む ── 焼く駒は 0.05 刻み)
    e1 = -fumi / 2.0 - za1 + b * (sode_nori_yc(keri) - (-keri / 2.0))
    for sx in (-1, 1):
        s0, _ = sode(keri, fumi, "a", name="s0_%d" % sx)
        put(s0, sx * (w / 2.0 + T / 2.0), keri, 0.0)
        s1, _ = sode_nori(keri, fumi, e1, "b", name="s1_%d" % sx)
        put(s1, sx * (w / 2.0 + T / 2.0), 2 * keri, -fumi)
    # 隅の野面の塊(検証の箱)と前庭の平場
    wm = bpy.data.materials.new("render_wall"); wm.use_nodes = True
    wb = next(n for n in wm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    wb.inputs['Base Color'].default_value = (0.30, 0.28, 0.26, 1.0)
    crest = 5 * keri + 0.02
    for sx in (-1, 1):
        bm = bmesh.new()
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, verts=r["verts"], vec=(3.0, 4.0, crest + 0.3))
        bmesh.ops.translate(bm, verts=r["verts"], vec=_u2b((sx * (w / 2.0 + 1.0), (crest - 0.3) / 2.0, z1w - 1.0)))
        me = bpy.data.meshes.new("wall%d" % sx); bm.to_mesh(me); bm.free()
        me.materials.append(wm)
        wo = bpy.data.objects.new("wall%d" % sx, me); bpy.context.scene.collection.objects.link(wo)
        bm = bmesh.new(); bm.from_mesh(me)
        for (P, N) in (((sx * (w / 2.0 - d1), yc1w, 0.0), (-sx, b, 0.0)),            # 返しの面の芯側を捨てる
                       ((0.0, yc1w, z1w + za1), (0.0, b, 1.0))):                   # もう一面の坂下を捨てる
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7,
                                   plane_co=_u2b(P), plane_no=_u2b(N), clear_outer=True)
            bnd = [e_ for e_ in bm.edges if e_.is_boundary]
            if bnd:
                bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me); bm.free(); me.update()
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 1.0, 0.0))
    g = bpy.context.active_object
    g.scale = (w + 10.0, 12.0, 1.0)
    gm = bpy.data.materials.new("render_ground"); gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    gb.inputs['Base Color'].default_value = (0.20, 0.17, 0.12, 1.0)
    g.data.materials.append(gm)
    V.dedup_materials()
    out = []
    xr = -(w / 2.0)                               # Blender x of Unity +X 側の小口
    shots = [
        ("3d", (xr - 2.2, -4.2, 2.9), (xr + 0.3, fumi * 1.2, 0.7), None),
        ("near", (xr + 1.4, -1.6, 1.55), (xr + 0.1, fumi * 1.0, 0.55), None),
        ("side", (xr - 7.0, fumi * 1.2, 0.8), (xr, fumi * 1.2, 0.6), 3.2),
        ("plan", (xr + 0.3, fumi * 1.0, 8.0), (xr + 0.3, fumi * 1.0 + 0.001, 0.0), 3.0),
        ("magenta", (xr + 1.4, -1.6, 1.55), (xr + 0.1, fumi * 1.0, 0.55), None),
    ]
    for (tag, cam, at, orth) in shots:
        V.studio(cam, at, ortho_scale=orth, res=(1600, 1100))
        if tag == "magenta":
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
            g.hide_render = True
            for o_ in bpy.data.objects:
                if o_.name.startswith("wall"):
                    o_.hide_render = True
        _hook_cut_stone()
        pth = os.path.join(SHOT, "sanno_kiri_%s_%s.png" % (key, tag))
        V.render(pth); out.append(pth)
    return out, e1


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


def shots_sode(keri, fumi, w, key, nstep=8):
    """段石 nstep 段 + 両側の袖を組んで刷る(⛔ 単体だけでは天端の通りも取り合いも読めない)。
    地面(z=0)は検証の文脈だけ — 書き出さない。"""
    V.reset()
    T = SODE_T
    for i in range(nstep):
        v = "ab"[i % 2]
        oo, _ = dan(keri, fumi, w, v, name="d%d" % i)
        oo.data.transform(Matrix.Translation((0, i * fumi, (i + 1) * keri))); oo.data.update()
        for sx in (-1, 1):
            ss, _ = sode(keri, fumi, v, name="s%d_%d" % (i, sx))
            ss.data.transform(Matrix.Translation((sx * (w / 2.0 + T / 2.0), i * fumi, (i + 1) * keri)))
            ss.data.update()
    V.dedup_materials()
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, nstep * fumi * 0.5 - 2.0, 0.0))
    g = bpy.context.active_object
    g.scale = (w + 12.0, nstep * fumi + 12.0, 1.0)
    gm = bpy.data.materials.new("render_ground"); gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    gb.inputs['Base Color'].default_value = (0.20, 0.17, 0.12, 1.0)
    g.data.materials.append(gm)
    os.makedirs(SHOT, exist_ok=True)
    L = nstep * fumi
    H = nstep * keri
    out = []
    shots = [
        ("3d", (w * 0.95, -5.5 - L * 0.2, H * 0.6 + 3.2), (0.0, L * 0.45, H * 0.45), None),
        ("side", (w / 2.0 + T + 14.0, L * 0.5, H * 0.5 + 0.6), (w / 2.0, L * 0.5, H * 0.5 + 0.2),
         max(L, H) * 1.35),
        ("near", (w / 2.0 - 1.6, -0.9, keri * 2 + 1.55), (w / 2.0 + 0.1, fumi * 2.2, keri * 3 + 0.2), None),
        ("magenta", (w * 0.95, -5.5 - L * 0.2, H * 0.6 + 3.2), (0.0, L * 0.45, H * 0.45), None),
    ]
    for (tag, cam, at, orth) in shots:
        V.studio(cam, at, ortho_scale=orth, res=(1600, 1100))
        if tag == "magenta":
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
            g.hide_render = True
        else:
            g.hide_render = False
        _hook_cut_stone()
        pth = os.path.join(SHOT, "sanno_sode_%s%s_%s.png" % (key, _dtag(), tag))
        V.render(pth); out.append(pth)
    return out


def _hook_cut_stone():
    """FBX 由来でない自前の材なので Alpha は 1 のまま。念のため不透明を強制するだけ。"""
    for m in bpy.data.materials:
        if m.name.split('.')[0] in (DANISHI, KIRISHI) and m.use_nodes:
            b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b:
                b.inputs['Alpha'].default_value = 1.0


def build_sode_set(specs, do_render):
    for (label, keri, fumi, w) in specs:
        for variant in ("a", "b"):
            V.reset()
            o, name = sode(keri, fumi, variant)
            report(o, name, "← %s の袖" % label)
            sode_check(o, keri, fumi)
            V.export_fbx([o], os.path.join(OUT_DAN, name + ".fbx"))
            print("[sanno] 書き出し " + os.path.join(OUT_DAN, name + ".fbx"))
        if do_render:
            for pth in shots_sode(keri, fumi, w, label_key(label)):
                print("[sanno] 検証レンダ " + pth)


# ---------------------------------------------------------------- 1c. 平面で折れる石段の袖の留め(EDO-0415)
# 女坂のように段石を段ごとに折れ線の向きで据えると、折れ点で袖の外に口・内に重なりが出る(剛体では閉じない)。
# ⇒ 平らな駒(`sode`)と**同じ局所座標・同じピボット**のまま、端を鉛直な留めの面で切り直す。
#   ・段石は段の境を結ぶ**弦**で据える(`EdoSannoShaRebuild.Stage2_Kaidan`)ので、一つの折れ点は前後二つの継ぎ目に
#     分かれ、折れ点を含む段の駒は**両端**を切る ⇒ 坂下の端 F(Unity Z = +f/2)を hF°・坂上の端 B(Z = −f/2)を hB°。
#   ・切りの軸 = 鉛直線 (Unity X = xc, Z = 端)。xc = 石段の芯 = −SODE_T/2 − w/2(袖を段石の +X 側に置いた向き)。
#   ・角 h(符号つき)= その継ぎ目の折れ角/2。端の位置が (X − xc)·tan h だけ**駒の外へ**動く(+ = 伸び / − = 縮み)。0 = 動かさない。
#   ・動かすのは**端の面とその面取りの輪の頂点だけ**(端から SODE_CHAMFER 以内)。高さは動かさない(天端は芯の高さで据え置き)。
#   ・駒は +X 側用だけ。−X 側は据え手が localScale.x = −1 の鏡で置く(据え手の決め)。
#   ⛔ 角は据え手の一覧の値をそのまま使う(丸め直さない — 綴りが Unity 側 `Own.IshidanSodeMiter` の F2 と一致する)。
def _sgn_h(h):
    return ("+" if h >= 0 else "-") + ("%.2f" % abs(h))


def sode_miter_name(keri, fumi, w, hF, hB, variant):
    return "IshidanSodeMiter_%.3f_%.3f_%.3f%s_F%s_B%s_%s" % (keri, fumi, w, _dtag(), _sgn_h(hF), _sgn_h(hB), variant)


def _miter_end(o, w, fumi, end, h):
    """o の端 end('F' / 'B')を角 h[°] で切る。動かした頂点数を返す。"""
    if abs(h) < 1e-12:
        return 0
    xc = -SODE_T / 2.0 - w / 2.0                 # Unity X
    t = math.tan(math.radians(h))
    zend = fumi / 2.0 if end == "F" else -fumi / 2.0
    sgn = 1.0 if end == "F" else -1.0            # 駒の外 = F は +Z / B は −Z
    band = SODE_CHAMFER + 1e-5
    bm = bmesh.new(); bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    moved = {}
    for v in bm.verts:
        X, Z = -v.co.x, -v.co.y                  # Blender → Unity(X = −x, Z = −y)
        if abs(Z - zend) > band:
            continue
        dZ = sgn * (X - xc) * t
        v.co.y -= dZ                             # Unity Z += dZ
        # ⭐ 高さは動かさない = 切った端の天端は留めの面に沿って**芯(xc)での高さのまま一定**。
        #   ⛔ 勾配の一直線のまま伸縮すると、留めの口で a と b の天端が 2·(X−xc)·tan h·勾配 食い違う
        #   (0.06〜0.07m。二つの斜面が同じ高さで会うのは芯の線の上だけ)。端の石が少しねじれるのは可(2026-09-23 奉行の判断)。
        moved[v.index] = -dZ                     # Blender y の変位
    # UV: 貼り方は `_sode_stone` と同じ(側面 = (s, 下がり)・天端/底 = (x, s))⇒ s の成分だけずらす
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        if ax == 1:
            continue
        for loop in f.loops:
            d = moved.get(loop.vert.index)
            if d is None:
                continue
            u, vv = loop[uvl].uv
            loop[uvl].uv = (u + d / DANISHI_TILE, vv) if ax == 0 else (u, vv + d / DANISHI_TILE)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(moved)


def sode_miter(keri, fumi, w, hF, hB, variant):
    """坂下の端 F を hF°・坂上の端 B を hB° で切った袖の駒。"""
    name = sode_miter_name(keri, fumi, w, hF, hB, variant)
    o, _ = sode(keri, fumi, variant, name=name)
    n = _miter_end(o, w, fumi, "F", hF) + _miter_end(o, w, fumi, "B", hB)
    return o, name, n


def sode_miter_check(o, flat, keri, fumi, w, hF, hB):
    ok = []
    xc = -SODE_T / 2.0 - w / 2.0
    a = unity_verts(o); b = unity_verts(flat)
    ok.append(("頂点数が平らな駒と同じ", len(a) == len(b), "%d / %d" % (len(a), len(b))))
    band = SODE_CHAMFER + 1e-5
    far = [(p, q) for p, q in zip(a, b) if abs(abs(q[2]) - fumi / 2.0) > band]
    dmax = max(max(abs(p[i] - q[i]) for i in range(3)) for p, q in far)
    ok.append(("両端の面取りの輪より内の頂点は一致", dmax < 1e-6, "最大差 %.2e(%d 点)" % (dmax, len(far))))
    top = lambda z: SODE_HT + (fumi / 2.0 - z) * keri / fumi
    for end, h in (("F", hF), ("B", hB)):
        t = math.tan(math.radians(h))
        zend = fumi / 2.0 if end == "F" else -fumi / 2.0
        sgn = 1.0 if end == "F" else -1.0
        endv = [p for p, q in zip(a, b) if abs(q[2] - zend) < 1e-6]
        res = max(abs(p[2] - (zend + sgn * (p[0] - xc) * t)) for p in endv)
        ok.append(("%s 端(%+.2f°)の面が芯の軸を通る鉛直面の上" % (end, h), res < 1e-5,
                   "残差 %.2e(%d 点)" % (res, len(endv))))
        ht = max(p[1] for p in endv)
        ok.append(("%s 端の天端 = 芯での天端" % end,
                   abs(ht - top(zend)) < 1e-6 or abs(ht - (top(zend) - SODE_CHAMFER)) < 1e-3,
                   "%.4f(芯 %.4f)" % (ht, top(zend))))
    ok.append(("全頂点の高さが平らな駒のまま", max(abs(p[1] - q[1]) for p, q in zip(a, b)) < 1e-9, ""))
    mats = [m.name for m in o.data.materials]
    ok.append(("材が Danishi だけ", mats == [DANISHI], str(mats)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    if any(not t_[1] for t_ in ok):
        raise SystemExit("[sanno] ⛔ 留めの袖の検算が落ちた")


def read_miter_list(path):
    """各行 `段番号 a|b F±hF B±hB`(# 以降は註)。⛔ 値は丸め直さない。"""
    rows = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            i, var, f_, b_ = ln.split()
            assert f_[0] == "F" and b_[0] == "B", ln
            i = int(i)
            if var != "ab"[i % 2]:
                raise SystemExit("[sanno] ⛔ 段 %d の a/b が i%%2 と合わない: %s" % (i, ln))
            rows.append((i, var, float(f_[1:]), float(b_[1:])))
    return rows


def build_sode_miter_list(keri, fumi, w, rows, do_render, steps=(16, 17, 18)):
    names = set()
    for (i, var, hF, hB) in rows:
        V.reset()
        flat, _ = sode(keri, fumi, var, name="flat")
        o, name, nmv = sode_miter(keri, fumi, w, hF, hB, var)
        if name in names:
            continue
        names.add(name)
        report(o, name, "段 %d・動かした頂点 %d" % (i, nmv))
        sode_miter_check(o, flat, keri, fumi, w, hF, hB)
        bpy.data.objects.remove(flat)
        V.export_fbx([o], os.path.join(OUT_DAN, name + ".fbx"))
        print("[sanno] 書き出し " + os.path.join(OUT_DAN, name + ".fbx"))
    print("[sanno] 留めの袖 %d 本(一覧 %d 行)" % (len(names), len(rows)))
    if do_render:
        for pth in shots_sode_miter(keri, fumi, w, rows, steps):
            print("[sanno] 検証レンダ " + pth)


def shots_sode_miter(keri, fumi, w, rows, steps):
    """弦で据えた一続きの段 steps を、両側の留めの袖で組んで刷り、継ぎ目ごとに数を刷る。
    継ぎ目 j(段 steps[j] の B と steps[j+1] の F)の軸 = 石段の芯と段の境の交点。そこで回転 Δ = 2·|h|(Blender Z 回り)。
    ⚠ 回転 +Δ では Blender +X 側 = **Unity −X 側が外**(+|h|)、Unity +X 側が内(−|h|)— 前任は一度逆に振った。
    −X 側は鏡(scale.x = −1)。"""
    by = {}
    for (i, var, hF, hB) in rows:
        by.setdefault(i, []).append((var, hF, hB))
    def row(i, sign):
        # sign = +1 → 正の角の行(外側)/ −1 → 負の角の行(内側)
        for (var, hF, hB) in by[i]:
            s_ = hF + hB
            if (s_ > 0) == (sign > 0):
                return var, hF, hB
        raise SystemExit("[sanno] 段 %d の %s 行が無い" % (i, "+" if sign > 0 else "-"))
    V.reset()
    T = SODE_T
    # 各段の置き行列(Blender)。段 k の坂上の端(y = +f/2)の芯が次の段の軸
    Ms = [Matrix()]
    for k in range(1, len(steps)):
        _, _, hBprev = row(steps[k - 1], +1)
        dd = 2.0 * hBprev
        prev = Ms[-1]
        piv = prev @ Vector((0.0, fumi / 2.0, 0.0))
        rotc = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(dd), 4, 'Z') @ Matrix.Translation(-piv)
        Ms.append(rotc @ prev @ Matrix.Translation((0.0, fumi, keri)))
    objs = []; res = {}
    for k, i in enumerate(steps):
        var = "ab"[i % 2]
        d, _ = dan(keri, fumi, w, var, name="d%d" % i); d.data.transform(Ms[k]); d.data.update(); objs.append(d)
        for side, sg in (("U+X", -1), ("U-X", +1)):
            var2, hF, hB = row(i, sg)
            o, nm, _ = sode_miter(keri, fumi, w, hF, hB, var2)
            o.name = "%s_%d" % (side, i)
            place = Matrix.Translation((-(w / 2.0 + T / 2.0), 0, 0))    # Unity +X 側
            if side == "U-X":
                place = Matrix.Scale(-1.0, 4, (1, 0, 0)) @ place         # 鏡(据え手の localScale.x = −1)
            o.data.transform(Ms[k] @ place)
            if side == "U-X":
                o.data.flip_normals()
            o.data.update(); objs.append(o); res[(side, i)] = (o, nm)
    nums = []
    for k in range(len(steps) - 1):
        ia, ib = steps[k], steps[k + 1]
        _, _, hB = row(ia, +1)
        dd = 2.0 * hB
        piv = Ms[k] @ Vector((0.0, fumi / 2.0, 0.0))
        # 留めの面: 段 a の坂上の端の面(x 軸)を Δ/2 回した鉛直面
        ax0 = (Ms[k].to_3x3() @ Vector((1, 0, 0))).normalized()
        tan_ = Matrix.Rotation(math.radians(dd / 2.0), 3, 'Z') @ ax0
        nrm = Vector((-tan_.y, tan_.x, 0.0))    # 坂上向き
        for side in ("U+X", "U-X"):
            A, na = res[(side, ia)]; B, nb = res[(side, ib)]
            pa = [v.co.copy() for v in A.data.vertices]; pb = [v.co.copy() for v in B.data.vertices]
            gap_a = max(nrm.dot(p - piv) for p in pa)      # a が面を越えた量(+ = 重なり)
            gap_b = min(nrm.dot(p - piv) for p in pb)      # b が面の手前に来た量(− = 重なり)
            on_a = [p for p in pa if abs(nrm.dot(p - piv)) < 1e-4]
            on_b = [p for p in pb if abs(nrm.dot(p - piv)) < 1e-4]
            # ② 天端の段差: 面上の天端付近の頂点の高さを同じ順位どうしで
            ta = sorted(p.z for p in on_a if p.z > max(q.z for q in on_a) - 0.05)
            tb = sorted(p.z for p in on_b if p.z > max(q.z for q in on_b) - 0.05)
            if len(ta) == len(tb):
                step = max(abs(p_ - q_) for p_, q_ in zip(ta, tb))
            else:
                step = max(abs(ta[-1] - tb[-1]), abs(ta[0] - tb[0]))
            # ③ 目違い: 面上で、高さ(1mm)ごとに面に沿った水平位置の最小・最大(= 側面の線)を a と b で比べる
            def ext(pts):
                dct = {}
                for p in pts:
                    kz = round(p.z, 3)
                    s_ = tan_.dot(p - piv)
                    lo, hi = dct.get(kz, (1e9, -1e9))
                    dct[kz] = (min(lo, s_), max(hi, s_))
                return dct
            ea, eb = ext(on_a), ext(on_b)
            com = sorted(set(ea) & set(eb))
            me = max(max(abs(ea[z][0] - eb[z][0]), abs(ea[z][1] - eb[z][1])) for z in com) if com else float("nan")
            sa = (min(v[0] for v in ea.values()), max(v[1] for v in ea.values()))
            sb = (min(v[0] for v in eb.values()), max(v[1] for v in eb.values()))
            me_all = max(abs(sa[0] - sb[0]), abs(sa[1] - sb[1]))
            nums.append(dict(joint="%d/%d" % (ia, ib), side=side, a=na, b=nb, gap_a=gap_a, gap_b=gap_b,
                             step=step, megai=max(me, me_all), n_common=len(com)))
            print("      継ぎ目 %d/%d %s: ①a の最遠 %+.4f / b の最遠 %+.4f ②天端の段差 %.4f ③目違い %.4f"
                  "(高さ %d 段で比較・外形 %.4f)"
                  % (ia, ib, side, gap_a, gap_b, step, me, len(com), me_all))
    bad = [n for n in nums if max(abs(n["gap_a"]), abs(n["gap_b"]), n["step"], n["megai"]) > 0.002]
    os.makedirs(SHOT, exist_ok=True)
    import json
    with open(os.path.join(SHOT, "sanno_sodemiter_chain.json"), "w", encoding="utf-8") as fp:
        json.dump(nums, fp, ensure_ascii=False, indent=1)
    V.dedup_materials()
    out = []
    c = Ms[1] @ Vector((0.0, 0.0, 0.0))
    ex = Ms[1] @ Vector((-(w / 2.0 + T / 2.0), 0.0, 0.0))
    ex2 = Ms[1] @ Vector(((w / 2.0 + T / 2.0), 0.0, 0.0))
    for tag, cam, at, orth in (
            ("plan", (c.x, c.y, 30.0), (c.x, c.y + 0.001, 0.0), w + 3.0),
            ("plan_edge", (ex.x, ex.y, 30.0), (ex.x, ex.y + 0.001, 0.0), 3.2),
            ("plan_edge2", (ex2.x, ex2.y, 30.0), (ex2.x, ex2.y + 0.001, 0.0), 3.2),
            ("3d", (ex.x - 3.5, ex.y - 4.0, c.z + 3.5), (ex.x, ex.y, c.z + 0.3), None),
            ("magenta", (ex.x - 3.5, ex.y - 4.0, c.z + 3.5), (ex.x, ex.y, c.z + 0.3), None)):
        V.studio(cam, at, ortho_scale=orth, res=(1600, 1100))
        if tag == "magenta":
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1)
        _hook_cut_stone()
        pth = os.path.join(SHOT, "sanno_sodemiter%s_%s.png" % (_dtag(), tag))
        V.render(pth); out.append(pth)
    if bad:
        raise SystemExit("[sanno] ⛔ 組み絵の継ぎ目が 2mm を越えた: %s" % [(n["joint"], n["side"]) for n in bad])
    return out


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
    global SODE_DEPTH
    for a in argv:
        if a.startswith("--depth="):
            SODE_DEPTH = float(a.split("=", 1)[1])      # 袖の丈(天端の線から下端まで)。既定 2.20
    miter_steps = (16, 17, 18)
    for a in argv:
        if a.startswith("--steps="):
            miter_steps = tuple(int(x) for x in a.split("=", 1)[1].split(","))   # 留めの組み絵に刷る段
    if what == "audit":
        audit(); return
    if what == "mitsuke":
        mitsuke(); return
    if what in ("dan", "all"):
        only = None
        for a in argv:
            if a.startswith("--only="):
                only = a.split("=", 1)[1]
        if len(rest) >= 3:
            specs = [("手引き", float(rest[0]), float(rest[1]), float(rest[2]))]
        else:
            specs = kaidan_specs(only)
        build_dan_set(specs, do_render)
    if what == "sode":
        only = None
        for a in argv:
            if a.startswith("--only="):
                only = a.split("=", 1)[1]
        if len(rest) >= 2:
            specs = [("手引き", float(rest[0]), float(rest[1]),
                      float(rest[2]) if len(rest) >= 3 else 3.636)]
        else:
            specs = kaidan_specs(only)
        build_sode_set(specs, do_render)
    if what == "sode_miter_list":
        # sode_miter_list <一覧ファイル> [<蹴上> <踏面> <幅>]  各行 `段番号 a|b F±hF B±hB`
        # ⛔ 角は据え手の一覧の値(指図の値ではない)。丸め直さない
        keri, fumi, w = (float(rest[1]), float(rest[2]), float(rest[3])) if len(rest) >= 4 else (0.300, 1.199, 6.363)
        build_sode_miter_list(keri, fumi, w, read_miter_list(rest[0]), do_render, miter_steps)
    if what == "sode_nori":
        # sode_nori <蹴上> <踏面> [--e=-0.20 | 既定は SODE_NORI_E の全部] [--depth=3.20]  背を法 1:0.25 に切った袖
        es = SODE_NORI_E
        for a in argv:
            if a.startswith("--e="):
                es = [float(x) for x in a.split("=", 1)[1].split(",")]
        build_sode_nori_set(float(rest[0]), float(rest[1]), es, False)
    if what == "dan_kiri_list":
        # dan_kiri_list <一覧> <蹴上> <踏面> <幅>  各行 `段番号 a|b L<端> R<端>`(端 = - | d±0.219 | d±0.219B±0.040)
        build_dan_kiri_list(float(rest[1]), float(rest[2]), float(rest[3]), read_kiri_list(rest[0]), do_render,
                            key=os.path.splitext(os.path.basename(rest[0]))[0])
    if what == "dan_kiri_try":
        # dan_kiri_try <一覧> <蹴上> <踏面> <幅> [--render]  焼かずに検算と組み絵だけ(実測の値が無いときに型を確かめる)
        build_dan_kiri_list(float(rest[1]), float(rest[2]), float(rest[3]), read_kiri_list(rest[0]), do_render,
                            key=os.path.splitext(os.path.basename(rest[0]))[0], export=False)
    if what == "kiri_shots":
        # kiri_shots <蹴上> <踏面> <幅> <d1> <za1>  組み絵だけ刷る(書き出さない)
        out, e1 = shots_kiri(float(rest[0]), float(rest[1]), float(rest[2]), float(rest[3]), float(rest[4]), "sando")
        print("[sanno] 組み絵の袖の背の出 e = %.4f" % e1)
        for pth in out:
            print("[sanno] 検証レンダ " + pth)
    if what in ("saku", "all"):
        spans = [float(rest[0])] if rest else [tamagaki_spec()["pitch"]]
        build_saku_set(spans, do_render)


if __name__ == "__main__":
    main()
