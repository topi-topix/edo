"""山王社の前庭の縁の土留め — **野面の乱積み**(施主が試作 A を採った・2026-09-24)の本番モジュール。

    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall  [--grade=0] [--h=1.2] [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kiri  [--render]     # 根石の打ち切り(沈む駒)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- sode  [--only=男坂] [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- mikiri [--render]
    blender --background --python Tools/Blender/build_sanno_nozura.py -- all --render
    blender --background --python Tools/Blender/build_sanno_nozura.py -- check                 # 継ぎ目の一致を数で検める
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado [--h=1.5] [--render]   # 出隅 90° の隅の駒
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado --h=4.8 --render       # 同・深い駒(型を 5.0 まで延ばす・EDO-0502)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado_deg --deg=49.4,51.8 --h=4.8 [--render]  # 折れが 90° でない出隅(名の角は丸め・EDO-0502)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado_cut --h=0.9 --v=b --axis=x --at=0.085 [--render]  # 隅の駒の片腕を袖の背で一度切った版(EDO-0437)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado_cut --h=0.9 --v=b --axis=x --at=0.085 --arm=0.5 [--render]  # 同・切った腕を詰め天端を切り口まで通した版(r16)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado_cap --h=1.5 --v=a [--render]  # 隅の駒の腕の先の継ぎ目の口を天端から 0.25 塞ぐ(同じ名で焼き直す)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- kado-check [--h=1.5]  # 隅の駒の腕の先 = 直線の切り口
    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall --grade=0.22 --h=1.5  # 段の境の勾配の駒(± 両方)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- dan --render          # 段の境の並べ焼き
    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall --grade=set       # 前庭の天端を流す勾配の駒 ±0.12 × 8 段(2026-09-26)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- grade --render [--h=0.9]   # 勾配の駒の並べ焼き
    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall --grade=0.275,-0.275 --h=0.6,0.9,1.2,1.5,1.8,2.1,2.4  # 岡部 外周の土留めの端を下げ打つ勾配の駒 ±0.275(EDO-0502・2026-10-06)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- grade --grade=0.275 --render [--h=1.2]   # 同・並べ焼き
    blender --background --python Tools/Blender/build_sanno_nozura.py -- wall --grade=0.45,-0.45 --h=0.6,0.9,1.2,1.5,1.8,2.1,2.4  # 岡部 袖石垣の天端を背の法なりに下げる勾配の駒 ±0.45(EDO-0502・2026-10-07・TW_Kado_Sode.sodeSlope)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- tome [--h=0.6,1.2,2.4] [--hand=P,M] [--render]   # 積み止めの駒(小口にも面石・両角が稜・岡部 nozuraEndRule 2026-10-07b・EDO-0502)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- crest [--dir=…] [--json=…]  # 全駒の背の天端の下がり(≤ 0.03)・頭の出(≤ 0)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- holes [--dir=…] [--json=…]  # 全駒を真上から見て天端に穴(裏・下の見える所)が 0 か
    blender --background --python Tools/Blender/build_sanno_nozura.py -- back --render         # 背の側(土の側)から撮る
    blender --background --python Tools/Blender/build_sanno_nozura.py -- nkiri --list=Tools/Blender/sanno_nozura_kiri_set.txt --render  # 片端を斜めの鉛直面で切った駒(女坂の袖に当てる・2026-09-26)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- mikiri_h [--h=1.5,1.8] --render   # 丈を合わせた見切り石(天端まで届く・2026-09-26)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- mikiri_h --h=2.4 --render         # 同・見付 2.40(岡部 外周の塞がる端・EDO-0502・2026-10-06)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- nnori --list=Tools/Blender/sanno_nozura_nori_set.txt --render  # 小口を相手の法 1:0.3 で切った短い駒(入隅の可動側の端・第3巡)
    blender --background --python Tools/Blender/build_sanno_nozura.py -- sode_nori --keri=0.250 --fumi=0.542 [--e=-0.15] --render     # 背を相手の法 1:0.3 で切った野面の袖(第3巡)

試作は `proto_sanno_dodome.py`(絵だけ)。石の形(Voronoi の割り・割肌の面・円弧で切る頭・
面取り)はそこから起こし直した。⛔ 在庫に野面石・玉石が無い(試作の依頼時に在庫方が確認)ので新造。

━━━ 1. 壁の駒 `Sanno_Nozura_H<見付mm>_G<勾配‰>_<a|b|c|d>.fbx`(Models/Sanno)━━━━━━━━━━━━━━
【ピッチ】1間 = 1.818m。**両端の石(端の柱石の列)は全種類・全段で同じ形** ⇒ どの駒どうしでも継げる。
  端の石は継ぎ目の線(X = ±0.909)で**石の途中を切って**あり、隣の駒の半分と合わさって1石に見える
  (⛔ 継ぎ目で竪目地を通さない)。種類 a〜d は中の石だけが違う。並べるときは順に振る(繰り返しを隠す)。
【見付の段】0.15(根石1段)/ 0.30 / 0.60 / … / 2.40。**割りは天端から下へ測った一つの型**で、段の違いは
  下をどこで切るかだけ ⇒ **段の違う駒どうしも天端の線で継げる**(天端が揃えば目地も揃う)。
  見付 2.3 の所は 2.4 を 0.1 沈めて据える(下は地中)。
【勾配】駒を鉛直に剪断して天端を勾配に載せる(石段の袖と同じ・段に折らない)。G = 天端が Unity +X へ
  1m あたり上がる量(‰)。焼いてあるのは G0・根石の打ち切り(H0150 の G±180)・段の境(H1500 の G±220)・
  前庭の天端を流す G±120(H1800 を除く 8 段・2026-09-26 EDO-0437)・岡部の外周の端を下げ打つ G±275(H0600〜H2400 の 7 段・
  2026-10-06 EDO-0502)・岡部の袖石垣の天端を背の法なりに下げる G±450(同 7 段・2026-10-07 EDO-0502)。他の勾配は `--grade=` で足す。
  ⭐ 剪断のまま ±0.45(24°)まで焼いた: 竪目地は鉛直のまま・横目地が勾配に沿うだけで、継ぎ目の切り口は天端から測って G0 と
  同じ形(傾けた積みにすると竪目地も法も傾き、G0 の駒と継げない)。並べ焼き sanno_nozura_g450_*.png で石の崩れは見えない。
  ⭐ 継ぎ目の切り口は**石ごとに**切って塞ぐ(`cut_each_ends`・2026-10-07)── 旧駒(G0〜G±275)は join の後に一度に切り、
  食い込んだ石どうしの輪が交わって小口の塞ぎが内向き・欠けになり、端に出た所(袖の低い端)で黒い穴に見えた。
【軸(Unity)】幅 = X / 高さ = Y / 厚み = Z、**見え面 = +Z**。面は 3分(0.3)の法 — **天端の線から測る**
  (段の違う駒どうしで面が食い違わないように)。
【ピボット】1間の中心(X=0)・**床レベル = 中心での天端 − 見付**(Y=0)・Z=0 は**天端の線での面**。
  ⇒ 床での面(法尻)は Z = +0.3×見付 に出る。石は床の 0.20 下まで根入れ(地中)。
  **見え面の頭は天端の線から下へ 0〜0.16 で不揃い(天端より上へ出さない)・背の列(面の輪 0.13 より奥)の上面は天端の線に揃う**
  (2026-09-25 EDO-0430: 背の頭が駒の最高より 0.1〜0.48 下がり、天端の高さの背の土が石に被って背の帯に溝ができた。
  天端の列の石は上の縁を天端へ上げ、目地の奥 0.30 に板)。`-- crest` が全駒の背の下がり ≤ 0.03 を検める。
  ⭐ **天端は「表の石の列 + 裏石の列」の 2 列**(2026-09-26 EDO-0437 施主指摘「天端の石が異様に長い — 表の石を引き伸ばさず、
  表の石+裏石の2列にするはず」): 表の石の控えは他の段と同じ 0.45〜0.75(旧: 天端の列だけ 0.75〜0.95 に引き伸ばしていた)。
  その奥の面から 0.36〜0.95 に裏石(径 0.15〜0.35・控え方向に 2 列・丈 0.20〜0.32・上面は天端の線の 0.004〜0.012 下で平ら ──
  表の石の天端と重なる所で面が揃って z-fight しない)。前の縁は表の石の背の内へ食い込ませて隙を開けない。端の裏石は `layout` と
  同じ作り(端の種+番人だけの Voronoi)⇒ どの駒どうしでも継ぎ目で合わさる。裏石の目地の底(天端の 0.20 下)に板。
  乱数は裏石だけ別の種 ⇒ 表の石と下の段は旧版と頂点まで同じ(天端から 0.7 より下で差 0)。天端の奥行 0.957(旧 0.86)。
  真上から: `-- top --render`(sanno_nozura_top*.png)。
  ⭐ 同日の追加の指摘 2 件(EDO-0437): ①「表の石の天端が綺麗に切られすぎ」⇒ 天端の列の表の石の上面を割肌に(`stone_obj` の rough:
  上の縁の点を天端の線ちょうどでなく下へ 面の輪 0.02〜0.05 / 奥 0.19 の輪 ≤ 0.018 / 背の輪 ≤ 0.012・石ごとの傾き・見え面との稜を肩 0.05〜0.08 で欠く。
  乱数は "nozura-top|…" の別の種)。裏石の上面も点ごとに 0.006〜0.018 下(正準座標の擬似乱数 `_hn` ── 端の裏石は継ぎ目の相手と同じ)。
  ②「裏石側の端部が直線」⇒ 裏石の奥の端を石ごとに 0.80〜1.05 で円弧に切る(`ura_back_cut`・隅は `kado_back_cut`)。実測の奥の端 0.73〜1.04。
  芝の肩は Unity の地形側で被せる前提。
  ⭐ 同日の 3 件目(EDO-0437)「真上から見ると表の石が長方形に切り取られている」⇒ 表の石の見え面の輪 M(面から 0.13)より奥を
  尻すぼみ・不整形に(`_taper_back`: 背で幅 0.45〜0.80 倍・縦 0.72〜0.88 倍・控えの軸の振れ ±6°・曲がり ±0.03・脇の膨らみ/くびれ・
  背の端は点ごとに奥行を振り芯を丸める。天端の列の丸みの芯は天端の線の 0.025 下 = TAPER_CAP_TOP)。どの点も M の輪より外へ出さない。
  継ぎ目の端の石は継ぎ目へ向けて縮め軸を振らない(左右の駒で同じ形)。乱数は別の種 "nozura-taper|…" ⇒ 見え面・M の輪・目地は頂点まで同じ。
  尻すぼみで開いた表の石の脇は間詰め石で塞ぐ(`taper_fill`・奥 0.24 より奥は上面が天端の線の 0.03 下より低い所も空きと数える)。
  裏石の目地の底の板は前へ 0.14 まで延ばす(URA_FLOOR_D0)。天端の奥行の最奥 1.044(変わらず)・隅の腕 0.909(変わらず)。
【材】`Kirishi` / `Danishi`(山王の切石と同じ暖かい灰。石ごとに 7:3 で振り、色の個体差にする)。
  ⛔ 新規マテリアルなし。UV は石ごとの箱投影(1.05m で1枚・石ごとに位相をずらす)。
  裏に目地の奥を塞ぐ板(`Danishi`)を 0.12 奥に張る ⇒ 目地から空が抜けない。

━━━ 2. 根石の打ち切り = `H0150` の `G±180` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  見付 0.2 未満で壁を終える駒。頭が 1.818m の間に 0.33 下がるので、高い側の天端を隣(見付 0.30)に
  合わせれば先端の石は床へ沈む。G+180 = +X へ上がる(−X 側の端に置く)/ G−180 = +X へ下がる(+X 側の端)。

━━━ 2b. 出隅 90° の隅の駒 `Sanno_Nozura_Kado90_H<見付mm>_<a|b>.fbx`(2026-09-25・本殿の西の土留め)━━━━━
  腕1 = 稜線から −X へ 0.909(見え面 +Z)/ 腕2 = 稜線から −Z へ 0.909(見え面 +X)。高い側は X ≤ 0・Z ≤ 0。
  ピボット = **天端の線どうしの交点(稜線)・床レベル(天端 − 見付)**。腕の先の切り口 X = −0.909 / Z = −0.909 は
  直線の駒の切り口と同じ(端の石は同じ種・同じ形)⇒ 直線の駒をそのまま継ぐ。面は法で下ほど前へ出るので、
  割りは「稜線から面に沿って測る σ」で起こし(深さ u の面の幅 = 0.909 + 0.3·(−u))、稜線に跨る石だけ σ=0 で
  割線を入れて 90° に折る(控えは留めの線 x = z へ剪断・隠れる)。行ごとに稜線に跨る石を一つ置く ⇒ 竪目地が
  稜線を通らず、隅だけの石の柱(算木)にもならない。出隅は対称なので一種で両回り(yaw で腕を選ぶ)。

━━━ 2c. 段の境の勾配の駒 = `H1500` の `G±220` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  帯の面 29.65 → 29.25 の差 0.40 を 1間で流す(0.40 / 1.818 = 0.22)。見付は**高い側の端**で取る
  (29.65 − 境内 28.3 = 1.35 ⇒ 1.50)。中心の見付で取ると(1.15 ⇒ 1.20)高い側の根入れが 0.05 しか残らない。

━━━ 3. 石段の袖 `IshidanSodeNozura_<蹴上>_<踏面>_<a|b>.fbx`(Models/Kaidan)━━━━━━━━━━━━━
  **`Own.IshidanSode` と同じ局所座標・ピボット・接する面**(厚み X ±0.30 で両面とも乱積み・
  X について鏡像対称 / +Z = 坂下 / 天端 Y = 0.30 + (踏面/2 − Z)·蹴上/踏面 / 下端 = 天端 − 2.20 /
  走り Z ±踏面/2)。⇒ ビルダーは関数を差し替えるだけで据え方は変わらない。石は X = ±0.30 の面を越えない。
  頭の不揃いは天端の線から下へ 0〜3cm・頭の丸みは R1.2〜2.0(±8cm・R0.3 だと石段に沿う天端が鋸の歯に見えた)。笠石は持たない。
  ⛔ 曲がる女坂の留めの駒(`IshidanSodeMiter`)は未だ乱積みで起こしていない。

━━━ 4. 見切り石 `Sanno_Nozura_Mikiri.fbx` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  男坂の下で城の石垣と継ぐための大きな野面石1点。面 0.86 × 0.80・控え 0.90。
  ピボット = 面の芯・床レベル・Z=0 は天端での面(壁の駒と同じ取り方)。
  ⭐ 丈を合わせた版 `Sanno_Nozura_Mikiri_H<段mm>`(1.20〜2.10・2026-09-26): 見え 0.6 では据える所の見付 1.2〜1.6 に届かず、
  背の土が頭より 0.82/1.20 高く埋まった。大きな野面石 2〜3 石の柱で、最高 = 天端の線・背の上面は天端に揃う。据えは天端で合わせて沈める。

━━━ 5. 片端を斜めの鉛直面で切った駒 `Sanno_Nozura_Kiri<角×10><P|M><L|S>_H<見付mm>_<a|b>`(2026-09-26)━━━━━━━━━
  前庭の南の土留めの端が女坂の袖の外面に 43.2° で当たる(直の小口ではめり込み −0.55)。城の石垣の版(build_ishigaki_kiri.py)と
  同じ角・向きの取り方。切る面は天端の前の縁の端 (±0.909, 天端, 0) を通る ⇒ 天端の線では直線の駒と同じ 1間。枠の外へ出る石
  (L = 足の前・S = 控え)は隣の 1間の割り(次の個体・端の石は同じ)から採る。反対の端は直線の駒の継ぎ目と頂点まで同じ。
  ⚠ 斜めの面は bpy.ops.mesh.bisect で面から 0.036 外に頂点が残った ⇒ bmesh.ops.bisect_plane + holes_fill(切り口の辺だけ)。
  切り口に石の角だけ残る欠片(二辺とも 0.08 未満)は袖の面の前に浮いて見えたので落とす。

━━━ 6. 相手の法で切る駒(2026-09-26 EDO-0437 第3巡)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  鉛直な小口・背は、相手の野面の法(下ほど前へ出る)の楔へ縮めても入る(据えでは解けない)⇒ 駒の側を法で切る。
  法は 1:0.3(焼いた野面の前の包絡を段ごとに測っても 0.3 で平行・+0.065〜0.08 の出)。
  `Sanno_Nozura_Nori<P|M>_L<長さmm>_H<見付mm>_a`: 入隅の可動側の短い駒。天端の線で長さ L・切る端は e·X ≤ L/2 + 0.3·(Y − 見付)。
    反対の端は直線の駒の継ぎ目と同じ。⛔ 伸縮させない(法が変わる)⇒ 0.05 刻みで焼く。
  `IshidanSodeNozuraNori_<蹴上>_<踏面>_E±e_<a|b>`: 野面の袖の背(−Z)を Z = −踏面/2 − e − 0.3·(Y − Yc) で切る(法は袖の底まで通す ── 2026-09-26 まで膝 −0.60 より下は鉛直で、相手の法の足が背を貫いた)。
    e > 0 は坂上へ次の個体を継いでから切る。切石の袖の `IshidanSodeNori`(build_sanno_buzai・1:0.25)と同じ e・Yc の取り方。
"""
import bpy, bmesh, sys, os, math, random
import mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
POS = [a for a in ARGS if not a.startswith("--")]
OPT = dict((a[2:].split("=", 1) + [""])[:2] for a in ARGS if a.startswith("--"))
RENDER = "render" in OPT

OUT_WALL = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
OUT_SODE = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Kaidan"))
SHOT = os.path.join(V.REPO, "Screenshots")
MATDIR = os.path.join(V.REPO, "Assets", "Edo", "Materials", "Sanno")

L = 1.818                 # 1間
TIERS = [0.15, 0.30, 0.60, 0.90, 1.20, 1.50, 1.80, 2.10, 2.40]
VARIANTS = "abcd"
BURY = 0.20               # 床より下の根入れ
DEEP = max(TIERS) + BURY  # 型の深さ(天端から)
BATTER = 0.3
HEAD = 0.08               # 頭の不揃い ±
KIRI_G = 0.180            # 根石の打ち切りの勾配(1間で 0.33 下がる ⇒ 先端の頭が床に沈む)
TILE = 1.05               # UV 1枚の実寸

# 石段の袖(`build_sanno_buzai` の SODE_* と同じ値。⛔ 変えると差し替えで据えがずれる)
SODE_HALF = 0.30
SODE_HT = 0.30
SODE_DEPTH = 2.20


# ------------------------------------------------------------------ 2D の道具
def clip(poly, n, c):
    """半平面 dot(p, n) <= c で凸多角形を切る"""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        dp = p[0] * n[0] + p[1] * n[1] - c
        dq = q[0] * n[0] + q[1] * n[1] - c
        if dp <= 0:
            out.append(p)
        if (dp < 0) != (dq < 0) and abs(dp - dq) > 1e-12:
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def area(poly):
    a = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        a += p[0] * q[1] - q[0] * p[1]
    return a / 2


def hull(pts):
    """凸包(反時計回り)"""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def head_arc(poly, sx, top, R):
    """頭を半径 R の円弧(5本の接線)で切る。u は上向き(0 = 天端の線)"""
    for a in (-0.75, -0.4, 0.0, 0.4, 0.75):
        n = (-math.sin(a), math.cos(a))
        cx, cu = sx, top - R
        poly = clip(poly, n, n[0] * cx + n[1] * cu + R)
        if len(poly) < 3:
            return poly
    return poly


def separate(poly, seed, obst, g):
    """凸の障害 obst から、種 seed の側へ g/2 離して切る(分離線 = 種が最も外に出る辺)"""
    best, bn, bc = -1e9, None, None
    m = len(obst)
    ccw = area(obst) > 0
    for i in range(m):
        p, q = obst[i], obst[(i + 1) % m]
        ex, ey = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(ex, ey)
        if ln < 1e-9:
            continue
        n = (ey / ln, -ex / ln) if ccw else (-ey / ln, ex / ln)     # 外向き
        d = (seed[0] - p[0]) * n[0] + (seed[1] - p[1]) * n[1]
        if d > best:
            best, bn, bc = d, n, p[0] * n[0] + p[1] * n[1]
    if bn is None:
        return poly
    # 残すのは dot(x, n) >= bc + g/2  ⇔  dot(x, -n) <= -(bc + g/2)
    return clip(poly, (-bn[0], -bn[1]), -(bc + g / 2))


# ------------------------------------------------------------------ 割り(天端から下へ一つの型)
def voronoi_cell(i, pts, g, box):
    """pts[i] の Voronoi 領域(目地 g)。box = (s0, s1, u0, u1)"""
    sx, su = pts[i]
    poly = [(box[0], box[2]), (box[1], box[2]), (box[1], box[3]), (box[0], box[3])]
    for j, (tx, tu) in enumerate(pts):
        if i == j or abs(tx - sx) > 1.3 or abs(tu - su) > 1.0:
            continue
        dx, du = tx - sx, tu - su
        d = math.hypot(dx, du)
        if d < 1e-9:
            continue
        n = (dx / d, du / d)
        poly = clip(poly, n, n[0] * (sx + tx) / 2 + n[1] * (su + tu) / 2 - g / 2)
        if len(poly) < 3:
            break
    return poly


def boundary_column(seed, depth, gw, cmax, rh=(0.26, 0.40), head=HEAD, rr=(0.16, 0.32)):
    """継ぎ目(s=0)に跨る端の石の列と、その左右の「番人」の種。**全種類・全段で同じ**(seed だけで決まる)。
    端の石は **端の種 + 番人の種だけ**の Voronoi 領域 ⇒ 中の石(種類ごとに違う)に形を左右されない。
    番人は s = c ± gw 付近に置き、中の石の種は番人より外にしか置かない。
    返す: (cols [(poly(s,u), key)], guards [(s,u)], bseeds [(s,u)])。u は上向き・天端 0。"""
    rng = random.Random(seed)
    bseeds, guards, heads = [], [], []
    u = 0.0
    k = 0
    while u > -depth - 0.3:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        c = (1 if k % 2 == 0 else -1) * rng.uniform(0.02, cmax)
        bseeds.append((c, uc))
        guards.append((c - gw * rng.uniform(0.85, 1.15), uc + rng.uniform(-0.08, 0.08)))
        guards.append((c + gw * rng.uniform(0.85, 1.15), uc + rng.uniform(-0.08, 0.08)))
        # ⭐ 頭は天端の線(u=0)から下へ 2×head の幅で不揃い(2026-09-25 EDO-0430: 天端より上へ出さない)
        heads.append((rng.uniform(-head, head) - head, rng.uniform(*rr), rng.uniform(0.022, 0.036)))
        u -= h_
        k += 1
    pts = bseeds + guards
    cols = []
    for ci in range(len(bseeds)):
        j8, R, g = heads[ci]
        poly = voronoi_cell(ci, pts, g, (-1.0, 1.0, -depth - 0.6, HEAD + 0.12))
        poly = head_arc(poly, bseeds[ci][0], j8, R) if len(poly) >= 3 else poly
        if len(poly) >= 3:
            cols.append((poly, "B%d" % ci))
    return cols, guards, bseeds


def layout(span, depth, bseed, vseed, wr=(0.25, 0.60), gw=0.40, bcmax=0.10, rh=(0.26, 0.40),
           head=HEAD, rr=(0.16, 0.32)):
    """1駒ぶんの石の輪郭(s ∈ [−span/2, +span/2]・u ∈ [−depth, +HEAD])。
    端の石の列(両端で同じ形)+ 番人 + 中の石(vseed ごとに違う)。返す [(poly, kind, key)]
    kind = 'B-' / 'B+'(左右の端の石)/ 'I'。key は石の乱数の種(端の石は左右で同じ)。"""
    cols, guards, bseeds = boundary_column(bseed, depth, gw, bcmax, rh, head, rr)
    ends, fixed, bpts = [], [], []
    for side, off in (("B-", -span / 2), ("B+", span / 2)):
        for poly, key in cols:
            ends.append(([(p[0] + off, p[1]) for p in poly], side, key))
        bpts += [(p[0] + off, p[1]) for p in bseeds]
        fixed += [(p[0] + off, p[1]) for p in guards if -span / 2 < p[0] + off < span / 2]
    rng = random.Random(vseed)
    var = []
    u = 0.0
    k = 0
    while u > -depth - 0.05:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        s = -span / 2 - rng.uniform(0, 0.3) - (0.2 if k % 2 else 0)
        while s < span / 2 + 0.3:
            w = rng.uniform(*wr)
            sx = s + w / 2 + rng.uniform(-0.05, 0.05)
            su = uc + rng.uniform(-0.05, 0.05)
            # 番人より外(継ぎ目から gw×1.3 以上)にだけ置く
            if -span / 2 + gw * 1.3 < sx < span / 2 - gw * 1.3 and su < -0.05:
                var.append((sx, su))
            s += w
        u -= h_
        k += 1
    seeds = fixed + var
    allp = seeds + bpts
    cells = []
    for i, (sx, su) in enumerate(seeds):
        g = rng.uniform(0.022, 0.040)
        poly = voronoi_cell(i, allp, g, (sx - 1.0, sx + 1.0, -depth - 0.3, HEAD + 0.12))
        if len(poly) < 3:
            continue
        poly = clip(poly, (1, 0), span / 2 - 0.02)
        poly = clip(poly, (-1, 0), span / 2 - 0.02)
        for op, side, key in ends:        # 端の石とわずかに重なる所を落とす
            if len(poly) < 3:
                break
            cx, cu = centroid(op)
            if abs(cx - sx) < 1.0 and abs(cu - su) < 1.0:
                poly = separate(poly, (sx, su), op, g)
        if len(poly) < 3:
            continue
        poly = head_arc(poly, sx, rng.uniform(-head, head) - head, rng.uniform(*rr))
        if len(poly) < 3 or area(poly) < 0.008:
            continue
        cells.append((poly, "I", "I%d" % i if i >= len(fixed) else "G%d" % i))
    return ends + cells


# ------------------------------------------------------------------ 材
def _stone_material(name, tint):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)          # ⛔ Unity 側の同名 .mat へ remap される入れ物
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs['Roughness'].default_value = 0.92
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = bpy.data.images.load(os.path.join(MATDIR, "T_Kirishi_Albedo.png"), check_existing=True)
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1
    nt.links.new(ti.outputs['Color'], mx.inputs[1]); mx.inputs[2].default_value = (tint, tint, tint, 1)
    nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])
    return m


def materials():
    return _stone_material("Kirishi", 1.0), _stone_material("Danishi", 0.80)


# ------------------------------------------------------------------ 石の塊
def _orient_out(bm):
    """閉じた塊の面を外向きに揃える(符号付き体積 < 0 なら全面を裏返す)。
    ⛔ recalc_face_normals だけに任せない: 尻すぼみ+割肌で輪が折れて自己交差した塊を、recalc は丸ごと内向きに揃えることがある
    (2026-09-26 EDO-0437: H0900_d / H0600_b の天端の列の表の石が内向きに焼け、Unity の裏面カリングで天端に四角い抜けが出た)。"""
    vol = 0.0
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for k in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[k].cross(vs[k + 1]))
    if vol < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    return vol < 0


def stone_obj(name, poly, key_rng, P, depth, face_prot=(-0.02, 0.045), double=None, crest=None, lift_ds=None, rough=None,
              taper=None, taper_c=None):
    """(s,u) の輪郭 → 野面の塊。P(s, u, d) が 3D を返す(d = 面から奥へ)。
    double = 厚み T なら両面を割肌にする(袖)。形の乱数は key_rng だけで決まる(端の石は左右で同じ)。
    crest = 天端の線の u(天端の列の石だけ渡す)⇒ 面から 0.13 奥の輪と背の輪の**上の縁(左端から右端まで上を回る点)を天端へ上げる**
    (背の上面が天端の線に揃う・見え面の頭の不揃いは面の輪だけに残る)。lift_ds(s, du) = 上げた点の s の寄せ
    (隅の駒: σ 空間では法の出が高さで変わるので、上げても 3D の位置が動かないよう σ を寄せる ── 寄せないと腕の先の切り口を越えた)。2026-09-25 EDO-0430: 背の頭が駒の最高より
    0.1〜0.48 下がり、天端の高さの背の土が石に被っていた。"""
    rng = key_rng
    cs, cu = centroid(poly)
    prot = rng.uniform(*face_prot)
    ta, tb = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.12)
    bm = bmesh.new()

    def face_d(s, u):
        return -prot + ta * (s - cs) - tb * (u - cu)

    n = len(poly)
    Fp = [(s, u, face_d(s, u) + rng.uniform(-0.012, 0.018)) for (s, u) in poly]     # 乱数の消費は旧版と同じ順
    upper = set()
    if crest is not None:
        # 上の縁 = 右端から左端まで上を回る点の列(斜めの石も、その走りの全幅で背の天端が天端の線に届く ──
        # 重心より上だけ上げると、斜めの石の低い肩の上に下の段の石の頭が 0.09 下がって覗いた)
        iR = max(range(n), key=lambda i: (poly[i][0], poly[i][1]))
        iL = min(range(n), key=lambda i: (poly[i][0], -poly[i][1]))
        chains = []
        for step in (1, -1):
            c, i = [iR], iR
            while i != iL:
                i = (i + step) % n
                c.append(i)
            chains.append(c)
        upc = max(chains, key=lambda c: sum(poly[i][1] for i in c) / len(c))
        upper = set(upc)
        if lift_ds is not None:
            # ⭐ 寄せ(隅の駒の σ の寄せ)で上の縁の点の順が入れ替わらないよう、寄せを縮める(2026-09-26 EDO-0437)。
            # 低い端の点を天端へ上げると σ が稜線へ 0.3·du 寄り、細い石では隣の上の縁の点を追い越して上面が裏返った
            # (Kado90_*_b の st_Kb27I ── 真上から裏が見え、Unity の裏面カリングで天端に穴)。上の縁は右端 → 左端で σ が減る順を保つ。
            sh = {i: lift_ds(poly[i][0], crest - poly[i][1]) for i in upc}
            f = {i: 1.0 for i in upc}
            for _ in range(len(upc)):
                moved = False
                for a, b in zip(upc, upc[1:]):
                    sa, sb = poly[a][0] + sh[a] * f[a], poly[b][0] + sh[b] * f[b]
                    gap = max(0.0, min(0.02, poly[a][0] - poly[b][0]))      # 元の間(0.02 まで)より詰めない
                    if sa - sb >= gap - 1e-9:
                        continue
                    k = a if abs(sh[a] * f[a]) >= abs(sh[b] * f[b]) else b
                    other = sb if k == a else sa
                    need = (other + gap - poly[a][0]) if k == a else (other - gap - poly[b][0])
                    f[k] = max(0.0, min(f[k], need / sh[k])) if abs(sh[k]) > 1e-9 else 0.0
                    moved = True
                if not moved:
                    break
            lfs = {poly[i][0]: f[i] for i in upc}
            if "dbg" in OPT and min(f.values()) < 1.0:
                print("NOZURA LIFTCAP %s %s" % (name, {i: round(f[i], 3) for i in upc if f[i] < 1.0}))
            _lift0 = lift_ds
            lift_ds = lambda s_, du, _o=_lift0, _f=lfs: _o(s_, du) * _f.get(s_, 1.0)

    # ⭐ 天端の割肌(2026-09-26 EDO-0437 施主指摘「天端の石が綺麗に切られすぎ」): 上の縁の点を天端の線ちょうどへ上げず、
    # 天端の線から**下へ**点ごとに不揃い(面の輪 0.02〜0.05・奥 0.19 の輪 ≤ 0.018・背の輪 ≤ 0.012 = 前寄りほど深い)・石ごとに傾き。
    # 見え面と上面の稜は肩 ch(0.05〜0.08)で欠く。乱数は rough(別の種)だけ ⇒ 下の段の石・形の乱数は動かない。
    rough_on = rough is not None and crest is not None and double is None
    dM, d2, dB = {}, {}, {}
    ch = 0.0
    if rough_on:
        tS = rough.uniform(-0.03, 0.03)
        ch = rough.uniform(0.05, 0.08)
        for i in sorted(upper):
            ds_ = tS * (poly[i][0] - cs)
            dM[i] = min(0.05, max(0.02, rough.uniform(0.02, 0.05) + ds_))
            d2[i] = min(0.018, max(0.004, rough.uniform(0.006, 0.018) + 0.5 * ds_))
            dB[i] = min(0.012, max(0.0, rough.uniform(0.0, 0.012) + 0.3 * ds_))

    def ring_s(i, s, u, k, tu=None):
        ss = cs + (s - cs) * k
        return ss + lift_ds(s, (crest if tu is None else tu) - u) if (i in upper and lift_ds) else ss

    def ring_u(i, u, k, drop=0.0):
        if i in upper:
            return crest
        uu = cu + (u - cu) * k - drop
        return min(uu, crest) if crest is not None else uu
    if rough_on:
        for i in upper:            # 見え面の頭の点は肩の下へ(上面より高い縁を残さない)
            s_, u_, d_ = Fp[i]
            Fp[i] = (s_, min(u_, crest - dM[i] - 0.6 * ch), d_)
    F = [bm.verts.new(P(*q)) for q in Fp]
    Mp = []
    for i, (s, u) in enumerate(poly):
        if rough_on and i in upper:
            tu = crest - dM[i]
            Mp.append((ring_s(i, s, u, 1.03, tu), tu, 0.13 - prot))
        else:
            Mp.append((ring_s(i, s, u, 1.03), ring_u(i, u, 1.03), 0.13 - prot))
    M = [bm.verts.new(P(*q)) for q in Mp]
    Sh = None
    if rough_on:               # 肩の輪(見え面 → 上面の稜を欠く)
        Sh = []
        for i, (s, u) in enumerate(poly):
            fs, fu, fd = Fp[i]
            ms, mu, md = Mp[i]
            if i in upper:
                sd = min(fd + ch, md - 0.015)
                Sh.append(bm.verts.new(P(ring_s(i, s, u, 1.015, crest - dM[i]), mu - 0.25 * ch, sd)))
            else:
                Sh.append(bm.verts.new(P((fs + ms) / 2, (fu + mu) / 2, (fd + md) / 2)))
    I = []
    for (s, u) in poly:
        ds, du = s - cs, u - cu
        dd = math.hypot(ds, du) or 1
        k = max(dd - 0.06, dd * 0.45) / dd
        si, ui = cs + ds * k, cu + du * k
        I.append(bm.verts.new(P(si, ui, face_d(si, ui) - rng.uniform(0.01, 0.03))))
    C = bm.verts.new(P(cs + rng.uniform(-0.04, 0.04), cu + rng.uniform(-0.03, 0.03),
                       face_d(cs, cu) - rng.uniform(0.015, 0.045)))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((C, I[i], I[j])))
        faces.append(bm.faces.new((I[i], F[i], F[j], I[j])))
        if Sh is None:
            faces.append(bm.faces.new((F[i], M[i], M[j], F[j])))
        else:
            faces.append(bm.faces.new((F[i], Sh[i], Sh[j], F[j])))
            faces.append(bm.faces.new((Sh[i], M[i], M[j], Sh[j])))
    if double is None and taper is not None:
        faces += _taper_back(bm, P, poly, taper, taper_c, cs, cu, prot, depth, crest, upper, rough_on, dB, d2, Mp, M,
                             ring_s, ring_u, lift_ds)
    elif double is None:
        ks = 0.97 if crest is not None else 0.80      # 天端の列は背でも幅を保つ(背の天端に隙を開けない)
        Bp = []
        for i, (s, u) in enumerate(poly):
            if rough_on and i in upper:
                tu = crest - dB[i]
                Bp.append((ring_s(i, s, u, ks, tu), tu, depth - prot))
            else:
                Bp.append((ring_s(i, s, u, ks), ring_u(i, u, 0.80, 0.03), depth - prot))
        Bk = [bm.verts.new(P(*q)) for q in Bp]
        R2 = None
        if rough_on and depth - prot > 0.24:      # 奥 0.19 の輪(背の列の帯の前で浅くする)
            R2 = []
            for i, (s, u) in enumerate(poly):
                ms, mu, md = Mp[i]
                bs, bu, bd = Bp[i]
                t = (0.19 - md) / (bd - md)
                if i in upper:
                    R2.append(bm.verts.new(P(ms + (bs - ms) * t, crest - d2[i], 0.19)))
                else:
                    R2.append(bm.verts.new(P(ms + (bs - ms) * t, mu + (bu - mu) * t, 0.19)))
        for i in range(n):
            j = (i + 1) % n
            if R2 is None:
                faces.append(bm.faces.new((M[i], Bk[i], Bk[j], M[j])))
            else:
                faces.append(bm.faces.new((M[i], R2[i], R2[j], M[j])))
                faces.append(bm.faces.new((R2[i], Bk[i], Bk[j], R2[j])))
        faces.append(bm.faces.new(list(reversed(Bk))))
    else:
        T = double
        prot2 = rng.uniform(*face_prot)
        ta2, tb2 = rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.12)

        def back_d(s, u):
            return T + prot2 - ta2 * (s - cs) + tb2 * (u - cu)
        F2 = [bm.verts.new(P(s, u, back_d(s, u) - rng.uniform(-0.012, 0.018))) for (s, u) in poly]
        M2 = [bm.verts.new(P(ring_s(i, s, u, 1.03), ring_u(i, u, 1.03), T - 0.13 + prot2)) for i, (s, u) in enumerate(poly)]
        C2 = bm.verts.new(P(cs + rng.uniform(-0.04, 0.04), cu, back_d(cs, cu) + rng.uniform(0.015, 0.04)))
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((M[i], M2[i], M2[j], M[j])))
            faces.append(bm.faces.new((M2[i], F2[i], F2[j], M2[j])))
            faces.append(bm.faces.new((F2[i], C2, F2[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _orient_out(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    bv = o.modifiers.new("bevel", 'BEVEL')
    bv.width = 0.04; bv.segments = 2; bv.limit_method = 'ANGLE'
    bv.angle_limit = math.radians(28); bv.use_clamp_overlap = True; bv.profile = 0.6
    V.sel([o])
    bpy.ops.object.modifier_apply(modifier="bevel")
    return o


TAPER_KB = (0.45, 0.80)   # 背の輪の幅 / 見え面の幅(石ごと)── 野面石は控えが長く尻が細い
TAPER_KV = (0.72, 0.88)
TAPER_CAP_TOP = 0.025     # 天端の列の石の背の丸みの芯 = 天端の線から下へ(crest の許し 0.03 の内)   # 背の輪の縦 / 見え面の縦(天端の列の上の縁は天端に留める)
TAPER_YAW = 6.0           # 控えの軸の平面の振れ(°)── 面に直交させない
TAPER_BEND = 0.03         # 控えの途中の曲がり(m)
TAPER_BULGE = (-0.10, 0.12)   # 脇の膨らみ(+)・くびれ(−)(半幅に対する比・片側ずつ)


def _taper_back(bm, P_, poly, tr, taper_c, cs, cu, prot, depth, crest, upper, rough_on, dB, d2, Mp, M, ring_s, ring_u, lift_ds):
    """⭐ 見え面の輪 M(面から 0.13)より奥を**尻すぼみ・不整形**に起こす(2026-09-26 EDO-0437 施主指摘「表石の天端が綺麗に
    切り取られ過ぎている」── 真上から長方形に見えた: 背の輪を重心へ 0.97 縮めて真後ろへ押し出していた)。
    M → (天端の列は奥 0.19 の輪 R2 = 旧版と同じ)→ 途中の輪 T1・T2 → 背の輪 Bk → 背の丸み(芯の点 Cb)。
    - 幅: 背で見え面の TAPER_KB 倍・脇ごとに縮み方(冪)と膨らみ/くびれを振る。縦も TAPER_KV 倍。
    - 軸: 平面で ±TAPER_YAW° 振れ・途中で ±TAPER_BEND 曲がる。⛔ どの点も M の輪より外へは出さない(隣の石と交差させない)。
    - 背の端: 点ごとに奥行を振り(斜めの割れ肌)、芯を 0.02〜0.05 奥へ出して丸める。
    - 端の石(taper_c = 継ぎ目の s)は継ぎ目へ向けて縮め・軸を振らない ⇒ 継ぎ目は奥まで石に覆われ、左右の駒で同じ形。
    乱数は tr(別の種 "nozura-taper|…")だけ ⇒ 見え面・M の輪・目地の形は旧版と頂点まで同じ。"""
    n = len(poly)
    end = taper_c is not None
    c0 = taper_c if end else cs
    kb = tr.uniform(*TAPER_KB)
    kv = tr.uniform(*TAPER_KV)
    pw = (tr.uniform(0.7, 1.5), tr.uniform(0.7, 1.5))          # (左, 右)の縮み方
    bl = (tr.uniform(*TAPER_BULGE), tr.uniform(*TAPER_BULGE))  # (左, 右)の膨らみ
    yaw = 0.0 if end else math.tan(math.radians(tr.uniform(-TAPER_YAW, TAPER_YAW)))
    bend = 0.0 if end else tr.uniform(-TAPER_BEND, TAPER_BEND)
    sl_s, sl_u = tr.uniform(-0.25, 0.25), tr.uniform(-0.20, 0.20)
    t1, t2 = tr.uniform(0.30, 0.45), tr.uniform(0.62, 0.78)
    jit = [(tr.uniform(-1, 1), tr.uniform(-1, 1), tr.uniform(-1, 1), tr.uniform(0, 1)) for _ in range(n)]
    dome = tr.uniform(0.02, 0.05)
    use_r2 = rough_on and depth - prot > 0.24
    d0 = 0.19 if use_r2 else 0.13 - prot
    db = []
    for i, (s, u) in enumerate(poly):
        d_ = depth - prot + sl_s * (s - cs) + sl_u * (u - cu) + 0.025 * jit[i][2]
        db.append(max(d0 + 0.18, d_))

    def s_at(i, s, u, t, tu):
        rel = s - c0
        side = 0 if rel < 0 else 1
        k = 1.0 - (1.0 - kb) * t ** pw[side] + bl[side] * math.sin(math.pi * t)
        dd = d0 + (db[i] - d0) * t
        ss = c0 + yaw * (dd - d0) + bend * math.sin(math.pi * t) + rel * min(k, 1.0)
        if 0 < t < 1:
            ss += 0.012 * jit[i][0 if t < 0.5 else 1]
        sm = cs + (s - cs) * 1.03                              # M の輪の s(上げの寄せを除く)
        ss = min(ss, sm) if rel >= 0 else max(ss, sm)          # M の輪より外へ出さない
        if i in upper and lift_ds:
            ss += lift_ds(s, tu - u)
        return ss

    def u_at(i, u, t):
        if i in upper:
            if rough_on:
                return crest - min(0.018, max(0.0, d2[i] + (dB[i] - d2[i]) * t + (0.004 * jit[i][3] if t < 1 else 0.0)))
            return crest
        uu = cu + (u - cu) * (1.0 - (1.0 - kv) * t) - 0.03 * t
        return min(uu, crest) if crest is not None else uu

    rings = []
    if use_r2:                  # 奥 0.19 の輪は旧版と同じ(背の輪 0.97 との内分)
        R2 = []
        for i, (s, u) in enumerate(poly):
            ms, mu, md = Mp[i]
            bd = depth - prot
            t = (0.19 - md) / (bd - md)
            if i in upper:
                bs = ring_s(i, s, u, 0.97, crest - dB[i])
                R2.append(bm.verts.new(P_(ms + (bs - ms) * t, crest - d2[i], 0.19)))
            else:
                bs, bu = ring_s(i, s, u, 0.97), ring_u(i, u, 0.80, 0.03)
                R2.append(bm.verts.new(P_(ms + (bs - ms) * t, mu + (bu - mu) * t, 0.19)))
        rings.append(R2)
    for t in (t1, t2, 1.0):
        R = []
        for i, (s, u) in enumerate(poly):
            uu = u_at(i, u, t)
            R.append(bm.verts.new(P_(s_at(i, s, u, t, uu), uu, d0 + (db[i] - d0) * t)))
        rings.append(R)
    Bk = rings[-1]
    cs_b = sum(s_at(i, s, u, 1.0, u_at(i, u, 1.0)) for i, (s, u) in enumerate(poly)) / n
    cu_b = sum(u_at(i, u, 1.0) for i, (s, u) in enumerate(poly)) / n
    if crest is not None:
        cu_b = crest - TAPER_CAP_TOP      # 天端の列: 背の丸みの芯を天端の帯に上げる(芯が石の半ばの高さだと、上の縁から芯へ
        #                                   緩く下る三角が天端の帯に 0.056 下がって見えた ⛔・負の勾配の駒で剪断が面を寝かせた・2026-09-26)
    Cb = bm.verts.new(P_(cs_b, cu_b, sum(db) / n + dome))
    faces = []
    prev = M
    for R in rings:
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((prev[i], R[i], R[j], prev[j])))
        prev = R
    for i in range(n):
        faces.append(bm.faces.new((Bk[(i + 1) % n], Bk[i], Cb)))
    return faces


def box_uv(o, ofs):
    """石ごとの箱投影。座標は**石の重心から**測る(継ぎ目で切った端の石が左右の駒で同じ UV になる)"""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    c = sum((v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
    for p in me.polygons:
        nx, ny, nz = (abs(x) for x in p.normal)
        for li in p.loop_indices:
            q = me.vertices[me.loops[li].vertex_index].co - c
            if nz >= nx and nz >= ny:
                a, b = q.x, q.y
            elif nx >= ny:
                a, b = q.y, q.z
            else:
                a, b = q.x, q.z
            uvl[li].uv = (a / TILE + ofs[0], b / TILE + ofs[1])


TOP_ROW = 0.25            # 輪郭の最高が天端の線から これ以内の石 = 天端の列
# ⛔ 天端の列の表の石の控えを 0.75〜0.95 に引き伸ばしていた(2026-09-25)のを廃した(2026-09-26 EDO-0437 施主指摘
#    「天端の石が異様に長い — 表の石を引き伸ばさず、表の石+裏石の2列にするはず」)。控えは他の段と同じ depth_rng。
#    背の天端は奥の裏石の列(`ura_*`)が持つ。


def build_stones(cells, P, mats, depth_rng=(0.45, 0.75), double=None, face_prot=(-0.02, 0.045), tag="", crest=0.0,
                 lift_ds=None):
    """crest = 天端の線の u(None で揃えない)。天端の列の石(輪郭の最高 > crest − TOP_ROW)は上の縁を天端へ揃える(控えは他の段と同じ)。"""
    objs = []
    kir, dan = mats
    for poly, kind, key in cells:
        # ⭐ 端の石は key が左右で同じ ⇒ 形・控え・材・UV の位相まで同じ(継ぎ目で合わさる)
        rng = random.Random("nozura|%s|%s" % (tag, key))
        d = rng.uniform(*depth_rng)
        top = crest is not None and max(p[1] for p in poly) > crest - TOP_ROW
        o = stone_obj("st_" + key + kind, poly, rng, P, d, face_prot=face_prot, double=double,
                      crest=crest if top else None, lift_ds=lift_ds,
                      rough=random.Random("nozura-top|%s|%s" % (tag, key)) if (top and double is None) else None,
                      taper=random.Random("nozura-taper|%s|%s" % (tag, key)) if double is None else None,
                      taper_c=((round(centroid(poly)[0] / L - 0.5) + 0.5) * L) if kind.startswith("B") else None)
        o.data.materials.append(kir if rng.random() < 0.7 else dan)
        box_uv(o, (rng.random(), rng.random()))
        objs.append(o)
    return objs


# ------------------------------------------------------------------ 裏石の列(2026-09-26 EDO-0437)
URA_D = (0.36, 1.10)      # 裏石の割りの箱: 天端の線での面から奥へ。前の縁は表の石の背(控え 0.45〜0.75)の内へ食い込ませる(隙を開けない)
URA_BACK = (0.80, 1.05)   # 裏石の奥の端(石ごと・円弧で丸く切る)── 帯を一直線で切った奥の縁を作らない(2026-09-26 施主「裏石側の端部が直線」)
URA_BACK_R = (0.10, 0.22) # 奥の端の円弧の半径
URA_FLOOR_D = 0.76        # 目地の底の板の奥の限り(奥の端の最も浅い 0.80 より手前 ⇒ 板が奥の端の外に出ない)
URA_ROWS = (0.52, 0.80)   # 控え方向の 2 列の種の芯
URA_W = (0.18, 0.32)      # 走り方向の種の間(径 0.15〜0.35 の裏石)
URA_H = (0.20, 0.32)      # 裏石の丈(天端から下へ)
URA_SINK = (0.006, 0.010) # 裏石の上面の沈みの基(+ 点ごとの割肌の不揃い URA_ROUGH)── 天端の線から 0.006〜0.018 下
URA_ROUGH = 0.008         # ⛔ 0.02 を越えて沈めない: 背の土(天端 −0.02)を被せても裏石の上面が顔を出す(2026-09-26 背から撮って確かめた)
URA_GW = 0.22             # 継ぎ目の端の裏石の番人の距離
URA_FLOOR_D0 = 0.14       # 目地の底の板の前の限り(旧 0.30)── 表の石を尻すぼみにして、表の石の脇の目地も底が要る(2026-09-26)
URA_FLOOR = -0.20         # 裏石の目地の底の板(天端から下・面から 0.30〜0.90)── 目地から下へ空が抜けない


def ura_back_cut(poly, key):
    """裏石の奥の端を石ごとに不揃いな深さ(URA_BACK)で、円弧で丸く切る。乱数は鍵だけ(端の裏石は左右で同じ)。(s, d) 平面。"""
    r = random.Random("nozura-ura-back|%s" % key)
    dmax, R = r.uniform(*URA_BACK), r.uniform(*URA_BACK_R)
    sx = centroid(poly)[0] + r.uniform(-0.04, 0.04)
    return head_arc(poly, sx, dmax, R)      # head_arc は第2座標の大きい側(= 奥)を円弧で切る


def _hn(p, q):
    """座標の決定論的な擬似乱数 0〜1(裏石の上面の点ごとの不揃い ── 端の裏石は左右の駒で同じ正準座標から引く)"""
    x = math.sin(round(p, 4) * 127.1 + round(q, 4) * 311.7) * 43758.5453
    return x - math.floor(x)


def ura_boundary(seed="nozura-ura-B"):
    """継ぎ目(s=0)に跨る端の裏石と番人の種(`boundary_column` の平面版・全駒で同じ)。(s, d) 平面・d = 面から奥へ。"""
    rng = random.Random(seed)
    bseeds, guards = [], []
    for r, dc in enumerate(URA_ROWS):
        c = (1 if r % 2 == 0 else -1) * rng.uniform(0.02, 0.06)
        dd = dc + rng.uniform(-0.03, 0.03)
        bseeds.append((c, dd))
        guards.append((c - URA_GW * rng.uniform(0.85, 1.15), dd + rng.uniform(-0.05, 0.05)))
        guards.append((c + URA_GW * rng.uniform(0.85, 1.15), dd + rng.uniform(-0.05, 0.05)))
    pts = bseeds + guards
    cols = []
    for i in range(len(bseeds)):
        g = rng.uniform(0.022, 0.034)
        poly = voronoi_cell(i, pts, g, (-1.0, 1.0, URA_D[0], URA_D[1]))
        if len(poly) >= 3:
            poly = ura_back_cut(poly, "U%d" % i)
        if len(poly) >= 3:
            cols.append((poly, "U%d" % i))
    return cols, guards, bseeds


def ura_layout(span, vseed):
    """1駒ぶんの裏石の平面の割り [(poly(s, d), kind, key)]。端の裏石(左右で同じ形・全種類で同じ)+ 中の裏石(vseed ごと)。
    `layout` と同じ作り(端の石は端の種+番人だけの Voronoi・中の種は番人より外)⇒ どの駒どうしでも継ぎ目で合わさる。"""
    cols, guards, bseeds = ura_boundary()
    ends, fixed, bpts = [], [], []
    for side, off in (("B-", -span / 2), ("B+", span / 2)):
        for poly, key in cols:
            ends.append(([(p[0] + off, p[1]) for p in poly], side, key))
        bpts += [(p[0] + off, p[1]) for p in bseeds]
        fixed += [(p[0] + off, p[1]) for p in guards if -span / 2 < p[0] + off < span / 2]
    rng = random.Random(vseed)
    var = []
    for r, dc in enumerate(URA_ROWS):
        s = -span / 2 - rng.uniform(0, 0.15) - (0.12 if r % 2 else 0)
        while s < span / 2 + 0.2:
            w = rng.uniform(*URA_W)
            sx = s + w / 2 + rng.uniform(-0.03, 0.03)
            sd = dc + rng.uniform(-0.05, 0.05)
            if -span / 2 + URA_GW * 1.3 < sx < span / 2 - URA_GW * 1.3:
                var.append((sx, sd))
            s += w
    return ends + _ura_cells(fixed + var, bpts, ends, rng,
                             lambda poly: clip(clip(poly, (1, 0), span / 2 - 0.02), (-1, 0), span / 2 - 0.02),
                             (URA_D[0], URA_D[1]), "I")


def _ura_cells(seeds, bpts, ends, rng, clip_fn, box_d, prefix, back=True):
    """中の裏石の Voronoi(bpts = 端の裏石の種。None なら中の種だけで割り、端の裏石から切り離して隙を詰める ── 隅の駒)"""
    allp = seeds + (bpts or [])
    cells = []
    for i, (sx, sd) in enumerate(seeds):
        g = rng.uniform(0.022, 0.034)
        poly = voronoi_cell(i, allp, g, (sx - 1.0, sx + 1.0, box_d[0], box_d[1]))
        if len(poly) < 3:
            continue
        poly = clip_fn(poly)
        for op, side, key in ends:
            if len(poly) < 3:
                break
            cx, cd = centroid(op)
            if abs(cx - sx) < 0.8 and abs(cd - sd) < 0.8:
                poly = separate(poly, (sx, sd), op, g)
        if len(poly) >= 3 and back:
            poly = ura_back_cut(poly, "%s%d" % (prefix, i))
        if len(poly) < 3 or area(poly) < 0.006:
            continue
        cells.append((poly, "I", "%s%d" % (prefix, i)))
    return cells


def _seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1e-12)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def _inside(p, poly):
    c = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            c = not c
    return c


def ura_fill(polys, box, key, gap=0.017, step=0.01, amin=0.0012, keep=None):
    """間詰め石: 割りの残した隙(目地より広い所 = どの石からも gap より離れた点の塊)を凸包の小石で埋める。
    返す [(poly, "I", key%d)]。⚠ 凸包は隣の石に少し食い込む ⇒ 上面を深めに沈めて(`URA_FILL_SINK`)下に隠す。"""
    x0, x1, z0, z1 = box
    nx, nz = int((x1 - x0) / step), int((z1 - z0) / step)
    free = set()
    for i in range(nx):
        for j in range(nz):
            p = (x0 + (i + 0.5) * step, z0 + (j + 0.5) * step)
            ok = keep is None or keep(*p)
            for q in polys:
                if _inside(p, q) or min(_seg_dist(p, q[k], q[(k + 1) % len(q)]) for k in range(len(q))) < gap:
                    ok = False
                    break
            if ok:
                free.add((i, j))
    out, seen = [], set()
    for c0 in sorted(free):
        if c0 in seen:
            continue
        st, comp = [c0], []
        seen.add(c0)
        while st:
            c = st.pop(); comp.append(c)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (c[0] + d[0], c[1] + d[1])
                if q in free and q not in seen:
                    seen.add(q); st.append(q)
        if len(comp) * step * step < amin:
            continue
        pts = []
        for (i, j) in comp:
            cx, cz = x0 + (i + 0.5) * step, z0 + (j + 0.5) * step
            pts += [(cx - step / 2, cz - step / 2), (cx + step / 2, cz - step / 2), (cx + step / 2, cz + step / 2), (cx - step / 2, cz + step / 2)]
        h = hull(pts)
        if len(h) >= 3 and abs(area(h)) >= amin:
            out.append((h, "I", "%s%d" % (key, len(out))))
    return out


URA_FILL_SINK = (0.010, 0.012)
TF_SINK = (0.014, 0.018)  # 表の石の脇の間詰め石の上面(天端の線から + 割肌 ≤ URA_ROUGH ⇒ ≤ 0.026 < crest の 0.03)
TF_D = (0.17, 0.78)       # 間詰めを置く奥行(面から)── 前は奥 0.19 の輪(表の石が見え面の幅を保つ所)の手前から、奥は裏石の奥の端の手前まで
TF_GAP = 0.02             # 石から離す目地
TF_OCC = 0.03             # 奥 TF_LOW_B より奥で「石が在る」と数える上面の高さ(天端の線から下へ)= crest の許し
TF_LOW_B = 0.24           # これより前は旧のまま(掛かる三角は全部 石)── 見え面の肩(0.02〜0.05 下)の前に細い間詰めを出さない


def _raster_tri(A, B, C, x0, z0, step, occ, top=None):
    """三角 (a, b, u) を平面の格子へ刷る。occ = 掛かる格子の集合 / top = 格子ごとの上面の高さ u の最高(芯で内挿)"""
    i0, i1 = math.floor((min(A[0], B[0], C[0]) - x0) / step), math.floor((max(A[0], B[0], C[0]) - x0) / step)
    j0, j1 = math.floor((min(A[1], B[1], C[1]) - z0) / step), math.floor((max(A[1], B[1], C[1]) - z0) / step)
    den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    for pt in (A, B, C):
        c = (math.floor((pt[0] - x0) / step), math.floor((pt[1] - z0) / step))
        occ.add(c)
        if top is not None:
            top[c] = max(top.get(c, -1e9), pt[2])
    if abs(den) < 1e-14:
        return
    for i in range(i0, i1 + 1):
        x = x0 + (i + 0.5) * step
        for j in range(j0, j1 + 1):
            z = z0 + (j + 0.5) * step
            l1 = ((B[1] - C[1]) * (x - C[0]) + (C[0] - B[0]) * (z - C[1])) / den
            l2 = ((C[1] - A[1]) * (x - C[0]) + (A[0] - C[0]) * (z - C[1])) / den
            if l1 >= -1e-9 and l2 >= -1e-9 and 1 - l1 - l2 >= -1e-9:
                occ.add((i, j))
                if top is not None:
                    top[(i, j)] = max(top.get((i, j), -1e9), l1 * A[2] + l2 * B[2] + (1 - l1 - l2) * C[2])


def taper_fill(objs, plan, box, keep, key, Q, mats, hmax, tag, step=0.01, gap=TF_GAP, amin=0.0012, depth_of=None):
    """⭐ 表の石を尻すぼみにして開いた、表の石の脇の楔(面から TF_D)を間詰め石で詰める(2026-09-26 EDO-0437)。
    石(st_* / ura_*)の三角を平面へ刷り(天端から 0.15 より上に頂点がある物だけ)、目地 gap で膨らませた残り =
    上から見て石の無い所を塊ごとに凸包の小石にする。plan(Blender の座標) → (a, b, 天端からの高さ)・Q(a, b, u) は逆。
    ⛔ 継ぎ目は端の石が奥まで覆う(`_taper_back` の taper_c)⇒ 塊が継ぎ目に跨らず、間詰めは駒の中で閉じる。"""
    x0, x1, z0, z1 = box
    occ, top = set(), {}
    for o in objs:
        if o.type != 'MESH' or not (o.name.startswith("st_") or (o.name.startswith("ura_") and "floor" not in o.name)):
            continue
        me = o.data
        me.calc_loop_triangles()
        mw = o.matrix_world
        W = [plan(mw @ v.co) for v in me.vertices]
        for t in me.loop_triangles:
            A, B, C = (W[k] for k in t.vertices)
            if max(A[2], B[2], C[2]) < -0.15:
                continue
            if max(A[0], B[0], C[0]) < x0 or min(A[0], B[0], C[0]) > x1 or max(A[1], B[1], C[1]) < z0 or min(A[1], B[1], C[1]) > z1:
                continue
            _raster_tri(A, B, C, x0, z0, step, occ, top)
    # 奥 TF_LOW_B より奥は「上面が天端の線から TF_OCC 以内の所」だけを石と数える ── 尻すぼみの石の脇の斜面は上から見て石だが
    # 天端より下がっている(負の勾配の駒で背の下がり 0.056 ⛔・2026-09-26)⇒ 斜面の上にも間詰め石を被せる(斜面は間詰めの下へ潜る)
    dep = depth_of or (lambda a, b: b)
    occ = {c for c in occ if dep(x0 + (c[0] + 0.5) * step, z0 + (c[1] + 0.5) * step) < TF_LOW_B or top.get(c, -1e9) >= -TF_OCC}
    r = int(math.ceil(gap / step))
    disc = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if di * di + dj * dj <= r * r]
    nx, nz = int(round((x1 - x0) / step)), int(round((z1 - z0) / step))
    free = set()
    for i in range(nx):
        for j in range(nz):
            if not keep(x0 + (i + 0.5) * step, z0 + (j + 0.5) * step):
                continue
            if any((i + di, j + dj) in occ for di, dj in disc):
                continue
            free.add((i, j))
    polys, seen = [], set()
    for c0 in sorted(free):
        if c0 in seen:
            continue
        st, comp = [c0], []
        seen.add(c0)
        while st:
            c = st.pop(); comp.append(c)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (c[0] + d[0], c[1] + d[1])
                if q in free and q not in seen:
                    seen.add(q); st.append(q)
        if len(comp) * step * step < amin:
            continue
        pts = []
        for (i, j) in comp:
            cx, cz = x0 + (i + 0.5) * step, z0 + (j + 0.5) * step
            pts += [(cx - step / 2, cz - step / 2), (cx + step / 2, cz - step / 2), (cx + step / 2, cz + step / 2), (cx - step / 2, cz + step / 2)]
        h = hull(pts)
        if len(h) >= 3 and abs(area(h)) >= amin:
            polys.append((h, "I", "TF%s%d" % (key, len(polys))))
    return build_ura(polys, Q, mats, hmax, tag=tag) if polys else []



def ura_stone(name, poly, rng, Q, hmax, canon=None):
    """平面の輪郭 poly(a, b)→ 裏石の塊(上面 = 天端の線の URA_SINK 下で平ら・胴で少し膨れ・底で窄まる)。
    Q(a, b, u) が Blender の座標を返す(u = 天端の線から上向き)。形の乱数は rng だけ(端の裏石は左右で同じ)。"""
    ca, cb = centroid(poly)
    sink = rng.uniform(*(TF_SINK if "TF" in name else URA_FILL_SINK if "KF" in name else URA_SINK))
    hb = min(rng.uniform(*URA_H), hmax)
    bm = bmesh.new()
    # 上面は割肌の不揃い: 点ごとに 天端の線から sink + 0〜URA_ROUGH 下(2026-09-26 施主「綺麗に切られすぎ」)。
    # ⛔ 点ごとの乱数は rng から取らない(切り離した端の裏石で列がずれる)⇒ 正準座標(canon: 継ぎ目の相手の駒と共通)の擬似乱数
    cn = canon or (lambda a, b: (a, b))
    T = [bm.verts.new(Q(a, b, -sink - URA_ROUGH * _hn(*cn(a, b)))) for (a, b) in poly]
    cc = cn(ca, cb)
    Tc = bm.verts.new(Q(ca, cb, -sink - URA_ROUGH * (0.3 + 0.7 * _hn(cc[0] + 0.5, cc[1]))))
    Mx = [bm.verts.new(Q(ca + (a - ca) * 1.04, cb + (b - cb) * 1.04, -sink - 0.07)) for (a, b) in poly]
    B = [bm.verts.new(Q(ca + (a - ca) * 0.72, cb + (b - cb) * 0.72, -hb)) for (a, b) in poly]
    n = len(poly)
    faces = [bm.faces.new((Tc, T[i], T[(i + 1) % n])) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((T[i], Mx[i], Mx[j], T[j])))
        faces.append(bm.faces.new((Mx[i], B[i], B[j], Mx[j])))
    faces.append(bm.faces.new(list(reversed(B))))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _orient_out(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.update()
    # 上面は上へ向ける(recalc が裏返すことがある ── 平らな塊で念のため)
    if me.polygons[0].normal.z < 0:
        me.flip_normals()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    bv = o.modifiers.new("bevel", 'BEVEL')
    bv.width = 0.022; bv.segments = 2; bv.limit_method = 'ANGLE'
    bv.angle_limit = math.radians(28); bv.use_clamp_overlap = True; bv.profile = 0.6
    V.sel([o])
    bpy.ops.object.modifier_apply(modifier="bevel")
    return o


def build_ura(cells, Q, mats, hmax, tag="ura"):
    """裏石の列。鍵は端の裏石で左右同じ ⇒ 形・材・UV の位相まで同じ(継ぎ目で合わさる)。"""
    objs = []
    kir, dan = mats
    for c in cells:
        poly, kind, key = c[:3]
        canon = c[3] if len(c) > 3 else None
        # 端の裏石は全駒で同じ鍵(継ぎ目で合わさる)・中の裏石は駒の種類ごと
        rng = random.Random("nozura-ura|B|%s" % key if kind.startswith("B") else "nozura-ura|%s|%s" % (tag, key))
        o = ura_stone("ura_" + key + kind, poly, rng, Q, hmax, canon)
        o.data.materials.append(kir if rng.random() < 0.55 else dan)
        box_uv(o, (rng.random(), rng.random()))
        objs.append(o)
    return objs


def wall_Q(h, g):
    """裏石の座標(s = Unity X, d = 面から奥へ, u = 天端の線から上向き)→ Blender。裏石は鉛直に積む(法の剪断をかけない)。"""
    def Q(s, d, u):
        return (-s, d, h + g * s + u)
    return Q


def ura_floor(name, Q, mat, a0, a1, b0, b1):
    """裏石の目地の底の板(上向き・u = URA_FLOOR)。a, b は Q の平面の座標。"""
    bm = bmesh.new()
    vs = [bm.verts.new(Q(a, b, URA_FLOOR)) for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
    bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    me.update()
    if me.polygons[0].normal.z < 0:
        me.flip_normals()
    box_uv(o, (0.2, 0.4))
    return o


_URA = {}


def ura_cells(v):
    if v not in _URA:
        _URA[v] = ura_layout(L, "nozura-ura-" + v)
    return _URA[v]


def wall_ura(h, g, v, mats, off=0.0, skip=None):
    """直線の駒の裏石(off = 走りの平行移動・skip = 採らない端の種類)+ 目地の底の板"""
    def canon_of(kind):
        o_ = off + (-L / 2 if kind == "B-" else L / 2 if kind == "B+" else 0.0)    # 端の裏石は継ぎ目からの座標
        return lambda a, b: (a - o_, b)
    cells = [([(p[0] + off, p[1]) for p in poly], kind, key, canon_of(kind)) for poly, kind, key in ura_cells(v) if kind != skip]
    objs = build_ura(cells, wall_Q(h, g), mats, h + BURY, tag="ura-" + v)
    objs.append(ura_floor("ura_floor", wall_Q(h, g), mats[1], off - L / 2, off + L / 2, URA_FLOOR_D0, URA_FLOOR_D))
    return objs


def wall_fill(objs, h, g, v, mats, s0, s1, tag="wall"):
    """直線の駒(と同じ座標の駒)の表の石の脇の間詰め石(`taper_fill`)。走り s0..s1。"""
    plan = lambda co: (-co.x, co.y, co.z - (h + g * (-co.x)))
    keep = lambda a, b: s0 + 0.005 < a < s1 - 0.005 and TF_D[0] <= b <= TF_D[1]
    return taper_fill(objs, plan, (s0, s1, TF_D[0] - 0.01, TF_D[1] + 0.01), keep, v, wall_Q(h, g), mats, h + BURY,
                      "tf-%s-%s" % (tag, v))


def bisect_keep(o, co, no):
    """平面 co・法線 no の**裏側**(dot(x-co, no) <= 0)だけ残して口を塞ぐ。
    塞いだ口(小口)の UV は補間の崩れで縞になる(見切り石の脇で実見)⇒ 平面へ投影し直す。"""
    V.sel([o])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=co, plane_no=no, use_fill=True, clear_outer=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    me = o.data
    n = Vector(no).normalized()
    c = Vector(co)
    # ⭐ 塞いだ口は外(+no)へ向ける(2026-10-07 EDO-0502): use_fill の小口は石によって内向きに張られ、Unity の裏面カリングで
    # 消えて石の中が覗いた(施主「段差の部分が石が切り取られたよう」・袖の低い端の小口の黒い穴)。G0〜G±275 の旧駒は
    # 片端 0.04〜0.13 m² が内向きのまま。
    bm = bmesh.new(); bm.from_mesh(me)
    flip = [f for f in bm.faces if abs((f.calc_center_median() - c).dot(n)) < 1e-4 and f.normal.dot(n) < -0.99]
    if flip:
        bmesh.ops.reverse_faces(bm, faces=flip)
        bm.to_mesh(me); me.update()
    bm.free()
    uvl = me.uv_layers.active.data
    ax = max(range(3), key=lambda k: abs(n[k]))
    a_, b_ = [k for k in range(3) if k != ax]
    for p in me.polygons:
        if p.normal.dot(n) > 0.99 and abs((p.center - c).dot(n)) < 1e-4:
            for li in p.loop_indices:
                q = me.vertices[me.loops[li].vertex_index].co
                uvl[li].uv = (q[a_] / TILE + 0.37, q[b_] / TILE + 0.11)


# ------------------------------------------------------------------ 壁の駒
def wall_name(h, g, v):
    gm = int(round(g * 1000))
    return "Sanno_Nozura_H%04d_G%s%03d_%s" % (int(round(h * 1000)), "+" if gm >= 0 else "-", abs(gm), v)


def wall_P(h, g):
    """(s = Unity X, u = 天端からの上向き, d = 面から奥へ) → Blender。
    Unity X = −Blender X / Unity Y = Blender Z / Unity Z = −Blender Y(README 書き出しの規約)。
    天端 Y = h + g·s。面(見え面 +Z)は天端の線から 3分で前へ出る: Unity Z = 0.3·(−u) − d。"""
    def P(s, u, d):
        return (-s, -(BATTER * (-u) - d), h + g * s + u)
    return P


BACK2 = (0.30, -0.005, -0.35)   # 天端の目地の奥の板: 面から 0.30 奥・天端の 0.005 下から 0.35 下まで


def backing(name, h, g, mat, d=0.12, u0=-0.12, u1=None):
    """目地の奥を塞ぐ板(既定: 面から 0.12 奥・天端の 0.12 下から床の下まで)。
    d, u0, u1 = BACK2 は天端の列の目地の奥の板(2026-09-25: 背の天端を天端の線へ上げたので、天端の目地が控えの奥まで
    素通しになり、土の無い側から空が抜けた ── 面の輪 0.13 より奥に張る)"""
    bm = bmesh.new()
    P = wall_P(h, g)
    vs = []
    for s in (-L / 2, L / 2):
        for u in (u0, -(h + BURY) if u1 is None else u1):
            vs.append(bm.verts.new(P(s, u, d)))
    # 法に沿わせる(u ごとに面が前へ出る分を足す)は P が持つ
    bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    # 見え面(−Blender Y)へ向ける
    me.update()
    if me.polygons[0].normal.y > 0:
        me.flip_normals()
    box_uv(o, (0.3, 0.7))
    return o


_LAYOUT = {}


def wall_cells(v, depth=DEEP):
    """depth = 型の深さ(天端から)。⭐ 既定 DEEP(H2.40+根入れ)の駒は型を変えない ── 深い駒(H4.80 など・EDO-0477)だけ
    `layout` を h+BURY まで延ばす(端の石の列も中の石の行も天端から下へ継ぎ足すだけ ⇒ 天端の線を揃えれば継ぎ目の端の石は既存と同じ形)。"""
    depth = max(DEEP, depth)
    key = v if depth == DEEP else (v, round(depth, 3))
    if key not in _LAYOUT:
        _LAYOUT[key] = layout(L, depth, "nozura-wall-B", "nozura-wall-" + v)
    return _LAYOUT[key]


def make_wall(h, g, v):
    V.reset()
    mats = materials()
    cells = []
    for poly, kind, key in wall_cells(v, h + BURY):
        p2 = clip(poly, (0, -1), h + BURY)            # u >= −(h+BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells.append((p2, kind, key))
    objs = build_stones(cells, wall_P(h, g), mats, tag="wall")
    objs += wall_ura(h, g, v, mats)
    objs += wall_fill(objs, h, g, v, mats, -L / 2, L / 2)
    objs.append(backing("back", h, g, mats[1]))
    objs.append(backing("back2", h, g, mats[1], *BACK2))
    name = wall_name(h, g, v)
    objs = cut_each_ends(objs)
    o = V.join(objs, name)
    V.set_origin(o, (0, 0, 0))
    return o, name, len(cells)


def cut_each_ends(objs, ends=((-L / 2, -1), (L / 2, 1))):
    """継ぎ目の切り口(Blender X = ±L/2)で**石ごとに**切って塞ぐ(2026-10-07 EDO-0502)。
    ⛔ join の後に一度に bisect(use_fill)すると、食い込ませた石どうし(表の石・裏石・間詰め)の切り口の輪が交わり、
    塞ぎが石を跨いで張られたり内向きになったりして、端に出た小口(袖の低い端など)に黒い穴が開いた
    (施主「段差の部分が石が切り取られたよう」)。石は一つずつなら閉じた塊 ⇒ 輪が一つずつ塞がる。板は切るだけ。"""
    keep = []
    for o in objs:
        for x, sgn in ends:
            if not o.data.polygons:
                break
            bm_cut_keep(o, (x, 0, 0), (sgn, 0, 0), chip=0.0)
        if o.data.polygons:
            # 塞いだ面の輪に一直線に並ぶ点が残ると、書き出しの三角分割で面積 0 の三角が出る ⇒ 切り口の面だけ三角に割り、潰れた辺を畳む
            bm = bmesh.new(); bm.from_mesh(o.data)
            capf = [f for f in bm.faces if any(abs(abs(f.normal.x) - 1) < 1e-3 and abs(f.calc_center_median().x - x) < 1e-4 for x, _ in ends)]
            if capf:
                bmesh.ops.triangulate(bm, faces=capf, quad_method='BEAUTY', ngon_method='BEAUTY')
            bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
            bm.to_mesh(o.data); bm.free(); o.data.update()
            keep.append(o)
        else:
            bpy.data.objects.remove(o, do_unlink=True)
    return keep


# ------------------------------------------------------------------ 出隅 90° の隅の駒
KADO_VARIANTS = "ab"
KADO_TIERS = [t for t in TIERS if t >= 0.30]


def kado_name(h, v):
    return "Sanno_Nozura_Kado90_H%04d_%s" % (int(round(h * 1000)), v)


def cbat(u):
    """天端の線から u(上向き)の所で、法が面を前へ出す量"""
    return BATTER * (-u)


def kado_layout(v, depth=DEEP, t=1.0):
    """出隅の駒の割り。**σ = 面に沿って隅(稜線)から測った距離**(腕1 = −・腕2 = +)。
    面は法で下ほど前へ出るので、深さ u での面の幅は腕ごとに 0.909 + c(u)(c = 0.3·(−u))。
    ⇒ 継ぎ目の線は σ 空間で斜め(σ = ±(0.909 + c(u)))。端の石は直線の駒と**同じ種・同じ形**
    (`boundary_column("nozura-wall-B")`)を σ 空間へ剪断して置く(3D では剪断が消え、直線の駒の端の石と一致する)。
    隅(σ ≈ 0)には稜線に跨る石の列を置く ⇒ 竪目地が稜線を通らない。種の符号はばらばら(算木の互い違いにしない)。"""
    rh, gw = (0.26, 0.40), 0.40
    cols, guards, bseeds = boundary_column("nozura-wall-B", depth, gw, 0.10, rh, HEAD, (0.16, 0.32))
    # t = tan(折れ/2)(`kado_frame`)。90° は t = 1 で旧版と同じ式・同じ浮動小数
    W = (lambda u: L / 2 + cbat(u)) if t == 1.0 else (lambda u: L / 2 + cbat(u) * t)
    ends, fixed, bpts = [], [], []
    for side, sg in (("B-", -1), ("B+", 1)):
        for poly, key in cols:
            ends.append(([(p[0] + sg * W(p[1]), p[1]) for p in poly], side, key))
        bpts += [(p[0] + sg * W(p[1]), p[1]) for p in bseeds]
        for p in guards:
            q = (p[0] + sg * W(p[1]), p[1])
            if abs(q[0]) < W(q[1]):
                fixed.append(q)
    rng = random.Random("nozura-kado-" + v)
    # 行ごとに稜線に跨る種を一つ(σ ∈ ±0.06)置き、その行の他の種はそこから 0.30 以上離す
    # ⇒ 隅の石は行の中の一石として並ぶ(隅だけの石の柱にしない ── 算木の列に見える)
    corner, var = [], []
    u = 0.0
    k = 0
    while u > -depth - 0.05:
        h_ = rng.uniform(*rh)
        uc = u - h_ / 2
        w_ = W(uc)
        sc = rng.uniform(-0.06, 0.06)
        corner.append((sc, uc + rng.uniform(-0.05, 0.05)))
        s = -w_ - rng.uniform(0, 0.3) - (0.2 if k % 2 else 0)
        while s < w_ + 0.3:
            w = rng.uniform(0.25, 0.60)
            sx = s + w / 2 + rng.uniform(-0.05, 0.05)
            su = uc + rng.uniform(-0.05, 0.05)
            if abs(sx - sc) > 0.30 and abs(sx) < W(su) - gw * 1.3 and su < -0.05:
                var.append((sx, su))
            s += w
        u -= h_
        k += 1
    seeds = corner + fixed + var
    allp = seeds + bpts
    cells = []
    for i, (sx, su) in enumerate(seeds):
        g = rng.uniform(0.022, 0.040)
        poly = voronoi_cell(i, allp, g, (sx - 1.0, sx + 1.0, -depth - 0.3, HEAD + 0.12))
        if len(poly) < 3:
            continue
        # 継ぎ目の斜めの線(σ = ±W(u))の内へ: σ + 0.3u ≤ 0.889 / −σ + 0.3u ≤ 0.889
        poly = clip(poly, (1, BATTER * t), L / 2 - 0.02)
        poly = clip(poly, (-1, BATTER * t), L / 2 - 0.02)
        for op, side, key in ends:
            if len(poly) < 3:
                break
            cx, cu = centroid(op)
            if abs(cx - sx) < 1.0 and abs(cu - su) < 1.0:
                poly = separate(poly, (sx, su), op, g)
        if len(poly) < 3:
            continue
        poly = head_arc(poly, sx, rng.uniform(-HEAD, HEAD) - HEAD, rng.uniform(0.16, 0.32))
        if len(poly) < 3 or area(poly) < 0.008:
            continue
        kind = "C" if i < len(corner) else "I"
        cells.append((poly, kind, "K%s%d" % (v, i)))
    # 端の石は σ 空間の多角形でなく、直線の駒の座標(s)で返す(3D は直線の駒と同じ P で起こす)
    raw_ends = []
    for side, off in (("B-", -L / 2), ("B+", L / 2)):
        for poly, key in cols:
            raw_ends.append(([(p[0] + off, p[1]) for p in poly], side, key))
    return raw_ends, cells


def _u2b(x, y, z):
    """Unity → Blender(README 書き出しの規約: Unity X = −Bx / Y = Bz / Z = −By)"""
    return (-x, -z, y)


def _b2u(co):
    return (-co.x, co.z, -co.y)


def make_kado(h, v):
    """出隅 90° の駒。局所(Unity): 腕1 = 稜線から −X へ 0.909(見え面 +Z)/ 腕2 = 稜線から −Z へ 0.909(見え面 +X)。
    高い側(帯)は X ≤ 0・Z ≤ 0 の象限。ピボット = **天端の線の稜線(両腕の天端の線の交点)・床レベル(天端 − 見付)**。
    ⇒ 腕の先の切り口 X = −0.909 / Z = −0.909 が、直線の駒の切り口(±0.909)とそのまま一致する。
    作り: 石は σ 空間で平らに起こし(面取りまで)、稜線に跨る石だけ σ = 0 で割線を入れてから折る:
      腕1: (x, z) = (σ + c, z)  腕2: (x, z) = (z, −σ + c)   跨る石: (σ + z, z) / (z, −σ + z)(σ = 0 が留めの線 x = z)"""
    V.reset()
    mats = materials()
    # ⭐ 深い駒(H2.40 より深い・EDO-0502 岡部の東の土留め H4.80)だけ型を h+BURY まで延ばす。既定 DEEP の駒の割りは変えない
    #   (`wall_cells` と同じ判断 ── 端の石の列は下へ継ぎ足すだけなので、同じ見付の直線の駒の継ぎ目と合う)
    raw_ends, cells = kado_layout(v) if h + BURY <= DEEP else kado_layout(v, h + BURY)
    cut = lambda p: clip(p, (0, -1), h + BURY)
    objs = []
    # ① 端の石 ── 直線の駒と同じ鍵・同じ P(tag "wall")⇒ 形・材・UV の位相まで同じ
    ends = [(cut(p), k, key) for p, k, key in raw_ends]
    ends = [c for c in ends if len(c[0]) >= 3 and area(c[0]) > 0.004]
    for poly, side, key in ends:
        o = build_stones([(poly, side, key)], wall_P(h, 0.0), mats, tag="wall")[0]
        if side == "B+":           # 腕2 へ回す: (x, z) → (z, −x)
            for vt in o.data.vertices:
                x, y, z = _b2u(vt.co)
                vt.co = _u2b(z, y, -x)
        objs.append(o)
    # ② 中の石と隅の石 ── σ 空間(Unity X = σ・Z = c(u) − d)で起こして折る
    Pf = wall_P(h, 0.0)
    for poly, kind, key in cells:
        p2 = cut(poly)
        if len(p2) < 3 or area(p2) <= 0.004:
            continue
        smin, smax = min(p[0] for p in p2), max(p[0] for p in p2)
        # 上げた点は σ を稜線へ寄せる(3D の x = σ + 法の出 c(u) を保つ ⇒ 腕の先の切り口を越えない)
        o = build_stones([(p2, kind, key)], Pf, mats, tag="kado",
                         lift_ds=lambda s_, du: (BATTER if s_ < 0 else -BATTER) * du)[0]
        cross = smin < 0 < smax
        if cross:
            V.sel([o])
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(1, 0, 0), use_fill=False,
                                clear_inner=False, clear_outer=False)
            bpy.ops.object.mode_set(mode='OBJECT')
        arm1 = (smin + smax) < 0
        for vt in o.data.vertices:
            s, y, z = _b2u(vt.co)
            c = cbat(y - h)
            if cross:
                nx, nz = (s + z, z) if s <= 0 else (z, -s + z)
            elif arm1:
                nx, nz = s + c, z
            else:
                nx, nz = z, -s + c
            vt.co = _u2b(nx, y, nz)
        o.data.update()
        objs.append(o)
    # ②' 裏石(両腕の面から URA_D の奥 = 平面の正方形 x, z ∈ [−0.909, −0.36])── `kado_ura`
    objs += kado_ura(h, v, mats)
    # 表の石の脇の間詰め(両腕の面から TF_D・奥の角は裏石の側)
    keep_k = lambda x, z: -L / 2 + 0.005 < x <= -TF_D[0] and -L / 2 + 0.005 < z <= -TF_D[0] and max(x, z) >= -TF_D[1]
    objs += taper_fill(objs, lambda co: (-co.x, -co.y, co.z - h), (-L / 2, 0.0, -L / 2, 0.0), keep_k, "K" + v,
                       lambda xx, zz, u: _u2b(xx, h + u, zz), mats, h + BURY, "tf-kado-" + v,
                       depth_of=lambda x, z: min(-x, -z))
    # ②'' 天端から 0.5 下までの石(腕の先の継ぎ目に掛からない物)を、それぞれ一つの閉じた凸な塊に焼き直す(2026-09-27 EDO-0437 r14)
    #   ⛔ 稜線に跨る石は σ = 0 で割って折るので、折り目と天端の割肌・尻すぼみの背が重なる所で面が裏返り(外から裏の面が見える)、
    #   開いた辺も残った(北東の隅 N_kado1 の天端の黒い穴 ── 表の光線の 867 本が裏へ抜けた)。凸包は穴も折り返しも持たない。
    nh = kado_hull_stones(objs, h, depth=h + BURY + 0.1)          # 天端から 0.5 に限らず全ての高さ(下の石にも裏返りが在った)
    print("KADO 凸な塊に焼き直した石 %d" % nh)
    # ③ 目地の奥を塞ぐ板(面から 0.12 奥・法に沿う)── 二枚が内の留めで閉じる
    for arm, (dd, u0, u1) in ((1, (0.12, -0.12, -(h + BURY))), (2, (0.12, -0.12, -(h + BURY))), (1, BACK2), (2, BACK2)):
        bm = bmesh.new()
        vs = []
        for u in (u0, u1):
            k = cbat(u) - dd
            if arm == 1:
                vs += [bm.verts.new(_u2b(-L / 2, h + u, k)), bm.verts.new(_u2b(k, h + u, k))]
            else:
                vs += [bm.verts.new(_u2b(k, h + u, k)), bm.verts.new(_u2b(k, h + u, -L / 2))]
        bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
        me = bpy.data.meshes.new("back%d" % arm); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("back%d" % arm, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(mats[1])
        me.update()
        nU = _b2u(me.polygons[0].normal)
        want = (0, 0, 1) if arm == 1 else (1, 0, 0)
        if nU[0] * want[0] + nU[2] * want[2] < 0:
            me.flip_normals()
        box_uv(ob, (0.3, 0.7))
        objs.append(ob)
    name = kado_name(h, v)
    o = V.join(objs, name)
    bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))          # Unity X ≥ −L/2 ⇔ Blender X ≤ +L/2
    bisect_keep(o, (0, L / 2, 0), (0, 1, 0))          # Unity Z ≥ −L/2 ⇔ Blender Y ≤ +L/2
    nd = clean_degenerate(o)
    print("KADO %s 面積 0・辺 < 0.1mm の三角形 %d" % (name, nd))
    nb, exb = kado_backface_rays(o, h)
    print("KADO %s 表から当てた光線が最初に裏の面に当たる本数 %d %s" % (name, nb, exb))
    V.set_origin(o, (0, 0, 0))
    return o, name


def kado_hull_stones(objs, h, depth=0.5, keep_from_end=0.86, d2=None):
    """objs のうち、天端から depth 以内に上面が在り、腕の先(X/Z < −keep_from_end)に掛からない石を、その凸包(閉じた塊)に置き換える。
    材は元の面で最も多い材・UV は石ごとの箱投影(`box_uv`)。板(厚みの無い物)は触らない。返り値 = 置き換えた数。"""
    n = 0
    for ob in objs:
        me = ob.data
        if len(me.vertices) < 8:
            continue
        U = [_b2u(ob.matrix_world @ v.co) for v in me.vertices]
        far2 = (min(u[2] for u in U) < -keep_from_end) if d2 is None else (max(u[0] * d2[0] + u[2] * d2[1] for u in U) > keep_from_end)
        if max(u[1] for u in U) < h - depth or min(u[0] for u in U) < -keep_from_end or far2:
            continue
        ext = sorted(max(u[k] for u in U) - min(u[k] for u in U) for k in range(3))
        if ext[0] < 0.01:
            continue                                                      # 板
        mats_ = [p.material_index for p in me.polygons]
        mi = max(set(mats_), key=mats_.count) if mats_ else 0
        bm = bmesh.new()
        for v in me.vertices:
            bm.verts.new(v.co)
        res = bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=DEGEN_EDGE * 1.05)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])     # 凸なので recalc は正しく外向きにする
        for f in bm.faces:
            f.material_index = mi
        bm.to_mesh(me); bm.free(); me.update()
        box_uv(ob, (0.13 * (n % 7), 0.29 * (n % 5)))
        n += 1
    return n


def kado_ura(h, v, mats):
    """出隅の駒の裏石。平面 (x, z)(Unity 局所)で割る。腕の先の端の裏石は直線の駒と**同じ種・同じ形**
    (腕1 の先 = (s − 0.909, −d)・腕2 の先 = 直線の駒の B+ を (x, z) → (z, −x) で回した (−d, −(s + 0.909)))。
    ⚠ 両腕の端の裏石の奥の列は正方形の奥の角(x, z < −0.76)で重なる ⇒ 腕2 の先の物を腕1 の物から切り離す
    (腕2 の先の切り口は面から 0.76 より奥だけ直線の駒と違う ── `check_kado` はそこを数えない)。"""
    cols, guards, bseeds = ura_boundary()
    a1 = lambda p: (p[0] - L / 2, -p[1])
    a2 = lambda p: (-p[1], -(p[0] + L / 2))
    ends1 = [([a1(p) for p in poly], "B-", key) for poly, key in cols]
    ends2 = []
    for (poly, key), sd in zip(cols, bseeds):
        q = [a2(p) for p in poly]
        for op, _, _ in ends1:
            if len(q) >= 3:
                q = separate(q, a2(sd), op, 0.028)
        if len(q) >= 3 and abs(area(q)) > 0.004:
            ends2.append((q, "B+", key))
    ends = ends1 + ends2
    bpts = [a1(p) for p in bseeds] + [a2(p) for p in bseeds]
    lo, hi = -L / 2, -URA_D[0]
    fixed = [q for q in [a1(p) for p in guards] + [a2(p) for p in guards] if lo < q[0] < hi and lo < q[1] < hi]
    rng = random.Random("nozura-kado-ura-" + v)
    var = []
    x = lo + URA_GW * 1.5 + rng.uniform(0.0, 0.04)
    while x < hi:
        z = lo + URA_GW * 1.5 + rng.uniform(0.0, 0.04)
        while z < hi:
            var.append((x + rng.uniform(-0.03, 0.03), z + rng.uniform(-0.03, 0.03)))
            z += rng.uniform(0.16, 0.22)
        x += rng.uniform(0.16, 0.22)
    # ⚠ 端の裏石の種まで入れて割ると、腕2 の先を切り離した所・両腕の端の間に三角の隙が残った ⇒ 中の種だけで割る
    cells = _ura_cells(fixed + var, None, ends, rng,
                       lambda poly: clip(clip(poly, (1, 0), hi), (0, 1), hi), (-URA_D[1], hi), "K%s" % v, back=False)
    # voronoi_cell の箱の走り(a)は種の ±1.0 ⇒ 奥の限り a ≥ −URA_D[1] も切る
    cells = [(clip(p, (-1, 0), URA_D[1]), k, key) for p, k, key in cells]
    # 奥の角(両腕の面から 0.78 より奥)の石は、角の向き(対角)に石ごとの深さで円弧に切る ── 奥の角を正方形の角で終えない
    cells = [(kado_back_cut(p, key), k, key) for p, k, key in cells]
    cells = [c for c in cells if len(c[0]) >= 3 and abs(area(c[0])) > 0.004]
    # 端の裏石の間・腕2 の先を切り離した所に残る三角の隙(目地より広い)を間詰め石で埋める(2026-09-26: 真上から床の板が覗いた)
    # ⛔ 奥の角(両腕から 0.78 より奥)は埋めない(奥の端を不揃いにした所を正方形に戻さない)
    fills = ura_fill([c[0] for c in ends + cells], (lo, hi, lo, hi), "KF%s" % v, keep=lambda x, z: max(x, z) > -URA_FLOOR_D - 0.02)
    Qk = lambda xx, zz, u: _u2b(xx, h + u, zz)
    c1 = lambda a, b: (a + L / 2, -b)            # 腕1 の先の端の裏石の正準座標(直線の駒の継ぎ目から)
    c2 = lambda a, b: (-b - L / 2, -a)           # 腕2 の先
    objs = build_ura([c + (c1 if c[1] == "B-" else c2,) for c in ends] + cells + fills, Qk, mats, h + BURY, tag="kura-" + v)
    objs.append(ura_floor("ura_floor", Qk, mats[1], lo, -URA_FLOOR_D0, -URA_FLOOR_D, -URA_FLOOR_D0))
    objs.append(ura_floor("ura_floor2", Qk, mats[1], -URA_FLOOR_D, -URA_FLOOR_D0, lo, -URA_FLOOR_D))
    return objs


def kado_back_cut(poly, key):
    """隅の駒の中の裏石の奥の角の側を、対角(両腕の奥の角)の向きに石ごとの深さ(対角の距離 1.10〜1.28)の円弧で切る"""
    r = random.Random("nozura-kado-ura-back|%s" % key)
    c, R = r.uniform(1.10, 1.28), r.uniform(*URA_BACK_R)
    k = 1 / math.sqrt(2)
    tw = [((x - z) * k, (-x - z) * k) for x, z in poly]          # (走り t, 奥の角への距離 w)
    tw = head_arc(tw, centroid(tw)[0], c, R)
    return [((t - w) * k, (-t - w) * k) for t, w in tw]


def kado_backface_rays(o, h, step=0.01):
    """表から当てた光線(天端の真上から下へ・腕1 の面の前から −Z・腕2 の面の前から −X)のうち、最初に**裏の面**に当たる本数。
    裏の面が見える = 石の塊に穴が開いて中(目地の奥・石の裏側)が覗いている(r14: 隅の駒の天端の継ぎ目に黒い穴)。返り値 = (本数, 例)。"""
    from mathutils.bvhtree import BVHTree
    me = o.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    bad, ex = 0, []
    rays = []
    xs = [(-L / 2 + step * (i + 0.5)) for i in range(int(L / 2 / step) + 12)]
    for x in xs:
        for z in xs:
            rays.append(((x, h + 0.5, z), (0, -1, 0)))                    # 真上から
    for a in xs:
        for k in range(int(h / step)):
            y = step * (k + 0.5)
            rays.append(((a, y, 2.0), (0, 0, -1)))                          # 腕1 の面(+Z)の前から
            rays.append(((2.0, y, a), (-1, 0, 0)))                          # 腕2 の面(+X)の前から
    for (pu, du) in rays:
        o_ = Vector(_u2b(*pu)); d_ = Vector(_u2b(*du))
        hit = bvh.ray_cast(o_, d_, 6.0)
        if hit[0] is None:
            continue
        if hit[1].dot(d_) > 0.0:
            bad += 1
            if len(ex) < 8:
                ex.append(tuple(round(c, 3) for c in _b2u(hit[0])))
    return bad, ex


# ------------------------------------------------------------------ 出隅の折れが 90° でない隅の駒(2026-10-05 EDO-0502)
# 岡部の東の野面の土留め: 折れ 49.4°(TW_Higashi_Hokuto 001f×002f)・51.8°(TW_Kado_Sode 0_2_dan×1_0)。60° 未満の折れには隅の駒が無く、
# 直線の駒を突き付けた外の角に足元ほど広い楔(足元で約 0.79m ── 法の出 0.3×見付 が両腕で開く)が見えた。
# `Sanno_Nozura_Kado<折れ°>_H<見付mm>_<a|b>`。折れ = 走りの向きの変わり(`EdoBuildNozura` の turn と同じ・90 が Kado90)。
#   腕1 = 稜線から −X へ 0.909(見え面 +Z)── Kado90 と同じ。腕2 = 稜線から d2 = (cos φ, −sin φ) へ 0.909(見え面 n2 = (sin φ, cos φ))。
#   ピボット = 天端の線どうしの交点(稜線)・床レベル。腕の先の切り口は直線の駒の切り口と同じ形(腕2 の先は直線の駒を yaw φ で回した物)。
#   面は σ 空間で起こして折る(Kado90 と同じ): 深さ u の面の稜線は c(u)·(t, 1)(t = tan(φ/2))⇒ 腕の面の幅は 0.909 + c·t。
#   裏石は腕ごとに直線の駒の裏石を起こし、留めの線(二等分)から MARGIN だけ越える石まで採る(切らない ── 上から見て留めの直線を出さない)。
def kado_deg_name(phi, h, v):
    return "Sanno_Nozura_Kado%d_H%04d_%s" % (int(round(phi)), int(round(h * 1000)), v)


def kado_frame(phi):
    """折れ phi(度)の局所の向き(Unity の (x, z)): 腕2 の走り d2・腕2 の見え面 n2・t = tan(φ/2)。90° は厳密な (0,−1),(1,0),1"""
    if abs(phi - 90.0) < 1e-9:
        return (0.0, -1.0), (1.0, 0.0), 1.0
    r = math.radians(phi)
    return (math.cos(r), -math.sin(r)), (math.sin(r), math.cos(r)), math.tan(r / 2)


def _arm2(d2, n2, x, z):
    """直線の駒の局所 (x, z)(+X が腕の先・+Z が見え面)→ 腕2 の (x, z)。yaw φ の回転"""
    return (x * d2[0] + z * n2[0], x * d2[1] + z * n2[1])


def _map_obj(o, f):
    for vt in o.data.vertices:
        x, y, z = _b2u(vt.co)
        X, Z = f(x, z)
        vt.co = _u2b(X, y, Z)
    o.data.update()


KADO_DEG_URA_MARGIN = 0.06   # 裏石を留めの線から越えて採る量(重なりは石の中に隠れる)


def kado_deg_ura(h, v, mats, phi):
    d2, n2, t = kado_frame(phi)
    nm = math.hypot(1.0, t)
    side = lambda x, z: (x - t * z) / nm          # < 0 = 腕1 の側
    va, vb = {"a": ("a", "c"), "b": ("b", "d")}[v]
    out = []
    for arm, vv in ((1, va), (2, vb)):
        for o in wall_ura(h, 0.0, vv, mats):
            if arm == 2:
                _map_obj(o, lambda x, z: _arm2(d2, n2, x, z))
            if "floor" in o.name:
                sg = 1.0 if arm == 1 else -1.0
                bm_ = bmesh.new(); bm_.from_mesh(o.data)            # 板は塞がずに切るだけ
                bmesh.ops.bisect_plane(bm_, geom=bm_.verts[:] + bm_.edges[:] + bm_.faces[:], dist=1e-6, plane_co=Vector((0, 0, 0)),
                                       plane_no=Vector(_u2b(sg / nm, 0.0, -sg * t / nm)), clear_outer=True, clear_inner=False)
                bm_.to_mesh(o.data); bm_.free(); o.data.update()
                out.append(o)
                continue
            U = [_b2u(vt.co) for vt in o.data.vertices]
            sd = side(sum(u[0] for u in U) / len(U), sum(u[2] for u in U) / len(U))
            if (arm == 1 and sd <= KADO_DEG_URA_MARGIN) or (arm == 2 and sd >= -KADO_DEG_URA_MARGIN):
                out.append(o)
            else:
                bpy.data.objects.remove(o)
    return out


def kado_deg_rays(o, h, phi, step=0.01):
    """表から当てた光線(真上・腕1 の面の前から −n1・腕2 の面の前から −n2)が最初に裏の面に当たる本数"""
    from mathutils.bvhtree import BVHTree
    d2, n2, t = kado_frame(phi)
    me = o.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    rays = []
    nx, nz = int((x1 - x0) / step) + 1, int((z1 - z0) / step) + 1
    for i in range(nx):
        for j in range(nz):
            rays.append(((x0 + (i + 0.5) * step, h + 0.5, z0 + (j + 0.5) * step), (0, -1, 0)))
    na = int((L / 2 + 0.3) / step)
    for i in range(na):
        a = -L / 2 + (i + 0.5) * step
        b = L / 2 - (i + 0.5) * step
        for k in range(int(h / step)):
            y = step * (k + 0.5)
            rays.append(((a, y, 3.0), (0, 0, -1)))
            p = (b * d2[0] + 3.0 * n2[0], b * d2[1] + 3.0 * n2[1])
            rays.append(((p[0], y, p[1]), (-n2[0], 0, -n2[1])))
    bad, ex = 0, []
    for (pu, du) in rays:
        o_ = Vector(_u2b(*pu)); d_ = Vector(_u2b(*du))
        hit = bvh.ray_cast(o_, d_, 8.0)
        if hit[0] is None:
            continue
        if hit[1].dot(d_) > 0.0:
            bad += 1
            if len(ex) < 8:
                ex.append(tuple(round(c, 3) for c in _b2u(hit[0])))
    return bad, len(rays), ex


def make_kado_deg(h, v, phi):
    V.reset()
    mats = materials()
    d2, n2, t = kado_frame(phi)
    raw_ends, cells = kado_layout(v, max(DEEP, h + BURY), t)
    cut = lambda p: clip(p, (0, -1), h + BURY)
    objs = []
    # ① 端の石 ── 直線の駒と同じ鍵・同じ P(tag "wall")。腕2 の先は yaw φ で回す
    ends = [(cut(p), k, key) for p, k, key in raw_ends]
    ends = [c for c in ends if len(c[0]) >= 3 and area(c[0]) > 0.004]
    for poly, side, key in ends:
        o = build_stones([(poly, side, key)], wall_P(h, 0.0), mats, tag="wall")[0]
        if side == "B+":
            _map_obj(o, lambda x, z: _arm2(d2, n2, x, z))
        objs.append(o)
    # ② 中の石と稜線に跨る石 ── σ 空間で起こして折る
    Pf = wall_P(h, 0.0)
    for poly, kind, key in cells:
        p2 = cut(poly)
        if len(p2) < 3 or area(p2) <= 0.004:
            continue
        smin, smax = min(p[0] for p in p2), max(p[0] for p in p2)
        o = build_stones([(p2, kind, key)], Pf, mats, tag="kado%d" % int(round(phi)),
                         lift_ds=lambda s_, du: (BATTER * t if s_ < 0 else -BATTER * t) * du)[0]
        cross = smin < 0 < smax
        if cross:
            V.sel([o])
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(1, 0, 0), use_fill=False,
                                clear_inner=False, clear_outer=False)
            bpy.ops.object.mode_set(mode='OBJECT')
        arm1 = (smin + smax) < 0
        for vt in o.data.vertices:
            s, y, z = _b2u(vt.co)
            c = cbat(y - h)
            if cross:
                # 留めの線(稜線の向き (t, 1))へ控えを剪断: σ ≤ 0 は腕1 の走り・σ > 0 は腕2 の走り
                nx, nz = (z * t + s, z) if s <= 0 else (z * t + s * d2[0], z + s * d2[1])
            elif arm1:
                nx, nz = s + c * t, z
            else:
                nx, nz = _arm2(d2, n2, s - c * t, z)
            vt.co = _u2b(nx, y, nz)
        o.data.update()
        objs.append(o)
    # ②' 裏石
    objs += kado_deg_ura(h, v, mats, phi)
    # 表の石の脇の間詰め(両腕の面から TF_D)
    dep1 = lambda x, z: -z
    dep2 = lambda x, z: -(x * n2[0] + z * n2[1])
    keep_k = lambda x, z: (x > -L / 2 + 0.005 and x * d2[0] + z * d2[1] < L / 2 - 0.005
                           and dep1(x, z) >= TF_D[0] and dep2(x, z) >= TF_D[0] and min(dep1(x, z), dep2(x, z)) <= TF_D[1])
    bx1 = max(0.05, L / 2 * d2[0] + 0.05)
    bz0 = min(L / 2 * d2[1] - 1.2 * n2[1], -1.2)
    objs += taper_fill(objs, lambda co: (-co.x, -co.y, co.z - h), (-L / 2, bx1, bz0, 0.0), keep_k, "K%d%s" % (int(round(phi)), v),
                       lambda xx, zz, u: _u2b(xx, h + u, zz), mats, h + BURY, "tf-kado%d-%s" % (int(round(phi)), v),
                       depth_of=lambda x, z: min(dep1(x, z), dep2(x, z)))
    nh = kado_hull_stones(objs, h, depth=h + BURY + 0.1, d2=d2)
    print("KADODEG 凸な塊に焼き直した石 %d" % nh)
    # ③ 目地の奥を塞ぐ板(面から dd 奥・法に沿う)── 二枚が留めの線で閉じる
    for arm, (dd, u0, u1) in ((1, (0.12, -0.12, -(h + BURY))), (2, (0.12, -0.12, -(h + BURY))), (1, BACK2), (2, BACK2)):
        bm = bmesh.new()
        vs = []
        for u in (u0, u1):
            k = cbat(u) - dd
            m = (k * t, k)
            e = (-L / 2, k) if arm == 1 else _arm2(d2, n2, L / 2, k)
            vs += [bm.verts.new(_u2b(e[0], h + u, e[1])), bm.verts.new(_u2b(m[0], h + u, m[1]))]
        bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
        me = bpy.data.meshes.new("back%d" % arm); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("back%d" % arm, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(mats[1])
        me.update()
        nU = _b2u(me.polygons[0].normal)
        want = (0.0, 1.0) if arm == 1 else n2
        if nU[0] * want[0] + nU[2] * want[1] < 0:
            me.flip_normals()
        box_uv(ob, (0.3, 0.7))
        objs.append(ob)
    name = kado_deg_name(phi, h, v)
    o = V.join(objs, name)
    bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))                     # 腕1 の先: Unity X ≥ −L/2
    bm_cut_keep(o, _u2b(L / 2 * d2[0], 0.0, L / 2 * d2[1]), _u2b(d2[0], 0.0, d2[1]), chip=0.0)   # 腕2 の先: p·d2 ≤ L/2
    nd = clean_degenerate(o)
    print("KADODEG %s 面積 0・辺 < 0.1mm の三角形 %d" % (name, nd))
    V.set_origin(o, (0, 0, 0))
    return o, name


def kado_deg_ref(h):
    """直線の駒(a)の両端の切り口の点(make_wall は V.reset するので隅の駒を起こす前に採る)"""
    ow, _, _ = make_wall(h, 0.0, "a")
    return ({(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, -L / 2)},
            {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, L / 2)})


def check_kado_deg(o, h, phi, ref):
    """腕の先の切り口 = 直線の駒の切り口(天端から 0.25 まで・1mm で丸め)。返り値 = 差のある腕の数"""
    d2, n2, t = kado_frame(phi)
    ref_p, ref_m = ref
    a1 = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(o, L / 2)}
    a2 = set()
    for vt in o.data.vertices:
        x, y, z = _b2u(vt.co)
        if abs(x * d2[0] + z * d2[1] - L / 2) < 2e-4:
            a2.add((round(-(x * n2[0] + z * n2[1]), 3), round(y - h, 3)))
    top = lambda S: {p for p in S if p[1] > -0.25 and p[0] < 0.6}
    deep = lambda S: {p for p in S if p[1] > -0.25 and p[0] >= 0.6}
    d1, dd2 = len(top(ref_p) ^ top(a1)), len(top(ref_m) ^ top(a2))
    print("KADODEG CHECK %s: 腕1の先 %d点 差%d / 腕2の先 %d点 差%d(面から 0.6 より奥の差 %d / %d)" % (
        o.name, len(top(a1)), d1, len(top(a2)), dd2, len(deep(a1) ^ deep(ref_p)), len(deep(a2) ^ deep(ref_m))))
    return (d1 > 0) + (dd2 > 0)


def render_kado_deg(h, phi, outdir, walldir):
    """隅の駒を直線の駒で挟んで撮る(焼いた FBX を読み戻す)。腕1 の先に直線 2 駒・腕2 の先に直線 2 駒(yaw φ)。"""
    d2, n2, t = kado_frame(phi)
    shots = []
    for v in KADO_VARIANTS:
        V.reset()
        _import_at(os.path.join(outdir, kado_deg_name(phi, h, v) + ".fbx"), 0, 0, 0)
        for i, wv in enumerate("ab"):
            _import_at(os.path.join(walldir, wall_name(h, 0, wv) + ".fbx"), -L * (i + 1), 0, 0)
            _import_at(os.path.join(walldir, wall_name(h, 0, "cd"[i]) + ".fbx"), L * (i + 1) * d2[0], L * (i + 1) * d2[1], 0, phi)
        hook_stone_textures()
        ground(0.0, -30, 30)
        # 帯の上(天端 + 0.06・両腕の面の奥)
        sh = (-0.06 * (0 + n2[0]), -0.06 * (1 + n2[1]))
        far = 14.0
        poly = [(0, 0), (-far, 0), (-far, -far * 1.2), (far * d2[0] - far * 0.8 * n2[0], far * d2[1] - far * 0.8 * n2[1]), (far * d2[0], far * d2[1])]
        bm = bmesh.new()
        vs = [bm.verts.new(_u2b(x + sh[0], h + 0.06, z + sh[1])) for x, z in poly]
        bm.faces.new(vs); me = bpy.data.meshes.new("Upper"); bm.to_mesh(me); bm.free()
        ou = bpy.data.objects.new("Upper", me); bpy.context.scene.collection.objects.link(ou)
        mu = bpy.data.materials.new("Upper"); mu.use_nodes = True
        mu.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.18, 0.24, 0.11, 1)
        me.materials.append(mu)
        b = (n2[0], 1 + n2[1]); bl = math.hypot(*b); b = (b[0] / bl, b[1] / bl)       # 外向きの二等分
        dist = 4.5 + 1.3 * h
        tag = "%d_H%04d_%s" % (int(round(phi)), int(round(h * 1000)), v)
        p = os.path.join(SHOT, "okabe_nozura_kado%s.png" % tag)
        studio_run([], _u2b(b[0] * dist, 0.45 * h + 1.0, b[1] * dist), _u2b(-0.3 * b[0], h * 0.45, -0.3 * b[1]), 30, p); shots.append(p)
        p = os.path.join(SHOT, "okabe_nozura_kado%s_magenta.png" % tag)
        studio_run([], _u2b(b[0] * dist, 0.45 * h + 1.0, b[1] * dist), _u2b(-0.3 * b[0], h * 0.45, -0.3 * b[1]), 30, p, magenta=True); shots.append(p)
        # 隅の足元の寄り(楔が閉じているか)
        p = os.path.join(SHOT, "okabe_nozura_kado%s_foot.png" % tag)
        studio_run([], _u2b(b[0] * 4.0 + 1.0 * d2[0], 1.2, b[1] * 4.0 + 1.0 * d2[1]), _u2b(0.4 * b[0], 0.6, 0.4 * b[1]), 30, p); shots.append(p)
        # 腕2 の継ぎ目の寄り
        e2 = (L / 2 * d2[0], L / 2 * d2[1])
        p = os.path.join(SHOT, "okabe_nozura_kado%s_seam2.png" % tag)
        studio_run([], _u2b(e2[0] + 3.2 * n2[0] + 0.4 * d2[0], 2.2, e2[1] + 3.2 * n2[1] + 0.4 * d2[1]), _u2b(e2[0], h * 0.6, e2[1]), 30, p); shots.append(p)
        # 真上から
        bpy.data.objects.remove(ou)
        sc = bpy.context.scene
        cam = sc.camera
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = 6.0
        cam.location = _u2b(0.0, 12.0, -0.6); cam.rotation_euler = (0, 0, 0)
        p = os.path.join(SHOT, "okabe_nozura_kado%s_plan.png" % tag)
        V.render(p); shots.append(p)
    return shots


def do_kado_deg():
    outdir = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno"))
    walldir = os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno")
    os.makedirs(outdir, exist_ok=True)
    degs = _floats("deg", [49.4, 51.8])
    hs = _floats("h", [4.8])
    bad = 0
    info = []
    for phi in degs:
        for h in hs:
            ref = kado_deg_ref(h)
            for v in KADO_VARIANTS:
                o, name = make_kado_deg(h, v, phi)
                bad += check_kado_deg(o, h, phi, ref)
                nb, nr, ex = kado_deg_rays(o, h, phi)
                print("KADODEG %s 表から当てた光線 %d 本のうち裏の面に当たる %d %s" % (name, nr, nb, ex))
                export(o, name, outdir)
                info.append((name, nb))
            if RENDER:
                for p in render_kado_deg(h, phi, outdir, walldir):
                    print("KADODEG SHOT", p)
    for n, nb in info:
        print("KADODEG_SUM %s backface_rays=%d" % (n, nb))
    if bad:
        sys.exit("KADODEG ⛔ 継ぎ目の検算が %d 件落ちた" % bad)


# ---- 隅の駒の片腕を袖の背の面で一度だけ切った版(2026-09-27 EDO-0437 施主「端の石は細くしない。袖に当たる石は袖の背に沿った一辺だけ切る」)
# 参道の階の前庭の北の縁の口の出隅: 返し側の腕の法(1:0.3)の足が袖の中へ W 0.31 / E 0.47 入った。
#   ⇒ 焼き上がった隅の駒(`make_kado` ── 1c84bf9b の天端を塊に焼き直した版)を、局所(Unity)の軸に直交する平面 axis = at で一度切り、
#   at より外(袖の側)を捨てて切り口を平らな面で塞ぐ。石を細くも伸ばしもしない(残す側の頂点は一つも動かない)。
#   切る面は法の面の前にしか出ない(天端の線 = 0 ⇒ 切り口の上端は天端から at/0.3 下)⇒ 天端の塊は切れない。
def kado_cut_name(h, v, axis, at, arm=0.0):
    return "%s_cut%s%.3f" % (kado_name(h, v), axis.upper(), at) + ("_L%.3f" % arm if arm else "")


def kado_cut(o, axis, at, keep="le"):
    """o(Blender 座標のメッシュ)を Unity 局所の axis ∈ {x, z} ≤ at(keep="ge" なら ≥ at)に切り、切り口を塞ぐ。返り値 = (切り口の面の数, 捨てた頂点の数)"""
    a = at
    sg = 1.0 if keep == "le" else -1.0
    co, no = ((-a, 0.0, 0.0), (-sg, 0.0, 0.0)) if axis == "x" else ((0.0, -a, 0.0), (0.0, -sg, 0.0))
    n = Vector(no); c = Vector(co)
    before = len(o.data.vertices)
    out_n = sum(1 for vt in o.data.vertices if (vt.co - c).dot(n) > 1e-6)
    bm = bmesh.new(); bm.from_mesh(o.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                 plane_co=c, plane_no=n, clear_outer=True, clear_inner=False)
    cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge) and x.is_valid and x.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=cut, sides=0)["faces"]
    uvl = bm.loops.layers.uv.active
    for f in filled:
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        for l in f.loops:
            q = l.vert.co
            l[uvl].uv = ((q.y if axis == "x" else q.x) / TILE + 0.37, q.z / TILE + 0.11)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # 切り口の面の上で石の頂点のすぐ脇(≤ 1mm)を切ると、書き出しの三角形割りで潰れた三角形と 0〜8mm の開いた辺が残った(H1500_b)
    #   ⇒ 平面に乗る頂点だけ 1mm で溶接し、潰れた面を溶かし、平面の上に残った開いた辺の環をもう一度塞ぐ
    onp = lambda vv: abs((vv.co - c).dot(n)) < 1e-5
    bmesh.ops.remove_doubles(bm, verts=[x for x in bm.verts if onp(x)], dist=1e-3)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-4)
    rest = [e for e in bm.edges if e.is_boundary and all(onp(x) for x in e.verts)]
    filled2 = bmesh.ops.holes_fill(bm, edges=rest, sides=0)["faces"] if rest else []
    for f in filled2:
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        for l in f.loops:
            q = l.vert.co
            l[uvl].uv = ((q.y if axis == "x" else q.x) / TILE + 0.37, q.z / TILE + 0.11)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4 and all(onp(x) for x in f.verts)])
    bmesh.ops.delete(bm, geom=[x for x in bm.verts if not x.link_faces], context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(filled) + len(filled2), out_n


# ---- 切り版の腕を詰め、袖の背の側の天端を切り口まで天端の高さで通す(2026-09-27 EDO-0437 r16)
#   棟梁の実測: ①袖の背の天端の縁と稜線・面の列の丸い頭の間に谷(東 0.250・西 0.225/0.170)── 法の面(天端で 0)から切り口(at)までの
#   楔の上が空いて、谷から奥の地面が見通せた。②返しの走りは北の縁の面から 0.48 しかないのに腕が 0.909(法の足で 1.0)あり、
#   腕の先の低い頭へ前庭の皮が引かれて窪んだ。⇒ 腕を ARM で詰め(平面で切って塞ぐ)、切り口の近くの石は頭を天端へ揃えて切り口まで通す。
#   ⛔ 石を細くも伸ばしもしない: 面の列の石は前の面だけを切り口の平面へ送る(袖の背に隠れる面・送る量は法の楔 ≤ at)。
KADO_ARM = 0.50           # 詰めた腕の長さ(稜線の面の線から)── 返しの走り 0.48(棟梁の実測 t0927_summary kiri_return.cutoff)+ 0.02
KADO_FLUSH_NEAR = 0.05    # 切り口の側の面(t = 0)から これより前に出る石 = 面の列・稜線の石(切り口まで通す)
KADO_FLUSH_SWEEP = 0.10   # その石の前の層(切り口の側の面 t = 0 から奥へ これ以内の点)を切り口の平面へ送る
KADO_END_NEAR = 0.15      # 詰めた端の面から これ以内に掛かる石は頭を天端へ揃える
KADO_RAISE = 0.20         # 天端の線から これより上の点を天端へ上げる(丸めて下げない)
KADO_TOPROW = 0.35        # 最高が天端の線から これ以内の石だけ触る(下の段は触らない)
KADO_CREST_E = (0.004, 0.012)   # 上げた頭の天端の線からの沈み(石ごと・裏石と同じ幅 ⇒ z-fight しない)
KADO_CAP_D = 0.25         # 腕の先の継ぎ目の小口を塞ぐ深さ(天端の線から)── 隣の直線の駒を縮めて据えると切り口が合わない


def _components(bm):
    """bmesh の面の連結成分(石 1 個ずつ)。返り値 = [set(faces)]"""
    seen, comps = set(), []
    for f in bm.faces:
        if f in seen:
            continue
        stack, comp = [f], set()
        seen.add(f)
        while stack:
            g = stack.pop()
            comp.add(g)
            for e in g.edges:
                for h_ in e.link_faces:
                    if h_ not in seen:
                        seen.add(h_); stack.append(h_)
        comps.append(comp)
    return comps


def kado_flush_crest(o, h, axis, at, arm):
    """切り版の隅の駒(`kado_cut` の後)の天端を、袖の背の側は切り口の平面(axis = at)まで・詰めた端(他の軸 = −arm)の近くまで、
    天端の線の KADO_CREST_E 下で通す。石ごとに: 天端から KADO_RAISE 内の点を天端へ上げ、切り口の側の石は前の層を平面へ送り、
    凸包に焼き直す(天端の石はもともと凸な塊 ── `kado_hull_stones`)。返り値 = dict(上げた石, 送った石, 送った量の最大)"""
    k = 0 if axis == "x" else 2
    j = 2 - k
    bm = bmesh.new(); bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    n_raise = n_sweep = 0
    sweep_max = 0.0
    for comp in _components(bm):
        vs = {v for f in comp for v in f.verts}
        U = [(_b2u(v.co), v) for v in vs]
        ys = [u[1] for u, _ in U]
        ext = sorted(max(u[i] for u, _ in U) - min(u[i] for u, _ in U) for i in range(3))
        if ext[0] < 0.01 or max(ys) < h - KADO_TOPROW:
            continue                                                  # 板・下の段
        tmax = max(u[k] for u, _ in U)
        smin = min(u[j] for u, _ in U)
        near_face = tmax > -KADO_FLUSH_NEAR
        # 詰めた端に掛かる石(切り口の側でない物)は、端の面の近くの点だけ上げる ── 残す腕の見え面の肩(割肌)は触らない。
        # 残す腕の先の継ぎ目の石(t < −0.86・直線の駒と同じ形)は触らない
        near_end = smin < -arm + KADO_END_NEAR and min(u[k] for u, _ in U) > -0.86
        if not (near_face or near_end):
            continue
        cx = sum(u[0] for u, _ in U) / len(U); cz = sum(u[2] for u, _ in U) / len(U)
        e = KADO_CREST_E[0] + (KADO_CREST_E[1] - KADO_CREST_E[0]) * _hn(cx + 3.1, cz - 7.7)
        pts = [Vector(u) for u, _ in U]
        up = (lambda u: True) if near_face else (lambda u: u[j] < -arm + KADO_END_NEAR)
        pts += [Vector((u[0], h - e, u[2])) for u, _ in U if u[1] > h - KADO_RAISE and up(u)]
        pts = [Vector((p.x, min(p.y, h - e), p.z)) for p in pts]      # 天端の線より上へ出さない
        if near_face:
            top_front = max((p[k] for p in pts if p.y > h - 0.05), default=at)
            add = []
            for p in pts:
                if p[k] > -KADO_FLUSH_SWEEP:
                    q = p.copy(); q[k] = at; add.append(q)
            sweep_max = max(sweep_max, at - top_front)
            pts += add
            n_sweep += 1
        n_raise += 1
        mats_ = [f.material_index for f in comp]
        mi = max(set(mats_), key=mats_.count)
        bmesh.ops.delete(bm, geom=list(comp), context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in vs if v.is_valid and not v.link_faces], context='VERTS')
        nv = [bm.verts.new(_u2b(*p)) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=nv, use_existing_faces=False)
        bmesh.ops.delete(bm, geom=[v for v in nv if v.is_valid and not v.link_faces], context='VERTS')
        hull_f = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
        hv = list({v for f in hull_f for v in f.verts})
        bmesh.ops.remove_doubles(bm, verts=hv, dist=DEGEN_EDGE * 1.05)
        hull_f = [f for f in hull_f if f.is_valid]
        bmesh.ops.recalc_face_normals(bm, faces=hull_f)
        c = sum((v.co for f in hull_f for v in f.verts), Vector()) / max(1, sum(len(f.verts) for f in hull_f))
        ofs = (0.13 * (n_raise % 7), 0.29 * (n_raise % 5))
        for f in hull_f:
            f.material_index = mi
            nx, ny, nz = (abs(x) for x in f.normal)
            for l in f.loops:
                q = l.vert.co - c
                a, b = (q.x, q.y) if (nz >= nx and nz >= ny) else ((q.y, q.z) if nx >= ny else (q.x, q.z))
                l[uvl].uv = (a / TILE + ofs[0], b / TILE + ofs[1])
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return dict(raised=n_raise, swept=n_sweep, sweep_max=round(sweep_max, 3))


def kado_cap_end(o, h, axis, depth=KADO_CAP_D):
    """腕の先の継ぎ目(Unity 局所 axis = −L/2)の切り口に開いた石の口のうち、天端から depth 内に掛かる物を平らな面で塞ぐ。
    隣の直線の駒を走りに縮めて据えると(N_025f ×0.53・N_011f ×0.81)継ぎ目の切り口が合わず、口から石の裏が覗いた。
    あわせて平面に乗る既存の面の向きを外へ揃える。返り値 = 塞いだ面 + 向きを直した面の数"""
    k = 0 if axis == "x" else 2
    bm = bmesh.new(); bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    onp = lambda v: abs(_b2u(v.co)[k] + L / 2) < 1e-4
    edges = [e for e in bm.edges if e.is_boundary and all(onp(v) for v in e.verts)]
    faces = bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"] if edges else []
    out = Vector(_u2b(*((-1, 0, 0) if axis == "x" else (0, 0, -1))))
    drop, keep = [], []
    for f in faces:
        if max(_b2u(v.co)[1] for v in f.verts) < h - depth:
            drop.append(f); continue
        f.normal_update()
        if f.normal.dot(out) < 0:
            f.normal_flip()
        for l in f.loops:
            q = _b2u(l.vert.co)
            l[uvl].uv = ((q[2] if axis == "x" else q[0]) / TILE + 0.37, q[1] / TILE + 0.11)
        keep.append(f)
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='FACES_ONLY')
    bmesh.ops.triangulate(bm, faces=[f for f in keep if f.is_valid and len(f.verts) > 3])
    # 継ぎ目の平面に乗る既存の面(`bisect_keep` の use_fill が張った小口)の向きを外(−axis)へ揃える
    #   ⚠ H1500_a の −X の小口の 26 面が内を向いていた(天端まで)── Unity は裏を描かないので口が開いて見えた(棟梁の実測 96 本)
    nflip = 0
    for f in bm.faces:
        if all(onp(v) for v in f.verts):
            f.normal_update()
            if f.normal.dot(out) < 0:
                f.normal_flip(); nflip += 1
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(keep) + nflip


def kado_rays_all(o, h, step=0.01, dstep=0.025):
    """`kado_backface_rays`(軸: 真上・+Z 面の前・+X 面の前)に、隅の外からの斜めの光線を足して数える。
    斜め = 水平の対角(−1,0,−1)・見下ろしの対角(−1,−1,−1)・腕ごとの見下ろし(−1,−1,0)/(0,−1,−1)。的は x,z ∈ [−L/2, 0.7]・y ∈ [0, h]。
    返り値 = {"axis": (本数, 例), "diag": (本数, 例)}"""
    from mathutils.bvhtree import BVHTree
    me = o.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    nb, exb = kado_backface_rays(o, h, step)
    dirs = [Vector((-1, 0, -1)).normalized(), Vector((-1, -1, -1)).normalized(),
            Vector((-1, -1, 0)).normalized(), Vector((0, -1, -1)).normalized()]
    grid = [(-L / 2 + dstep * (i + 0.5)) for i in range(int((L / 2 + 0.7) / dstep))]
    ys = [dstep * (k + 0.5) for k in range(int(h / dstep) + 1)]
    bad, ex = 0, []
    for du in dirs:
        d_ = Vector(_u2b(*du))
        for a in grid:
            for y in ys:
                # 的の面: 水平の対角は稜線の鉛直面(x = −z)に沿って、ほかは各腕の面の近く・天端の上に並べる
                for tgt in ((a, y, -a), (a, y, 0.1), (0.1, y, a), (a, h, a * 0.5)):
                    pu = Vector(tgt) - 6.0 * du
                    hit = bvh.ray_cast(Vector(_u2b(*pu)), d_, 12.0)
                    if hit[0] is None:
                        continue
                    if hit[1].dot(d_) > 0.0:
                        bad += 1
                        if len(ex) < 8:
                            ex.append(tuple(round(c, 3) for c in _b2u(hit[0])))
    return {"axis": (nb, exb), "diag": (bad, ex)}


def make_kado_cut(h, v, axis, at, arm=0.0):
    o0, name0 = make_kado(h, v)
    rays0 = kado_rays_all(o0, h)
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o0)
    name = kado_cut_name(h, v, axis, at, arm)
    o0.name = name; o0.data.name = name
    nf, nout = kado_cut(o0, axis, at)
    other = "z" if axis == "x" else "x"
    arm_info = None
    if arm:
        nf2, nout2 = kado_cut(o0, other, -arm, keep="ge")                 # 切った側の腕を詰める(詰めた端の小口も塞ぐ)
        fl = kado_flush_crest(o0, h, axis, at, arm)
        ncap = kado_cap_end(o0, h, axis)                                   # 残す腕の先の継ぎ目の口(天端から KADO_CAP_D)
        arm_info = dict(arm=arm, end_faces=nf2, end_dropped=nout2, cap_faces=ncap, **fl)
    # 切り口の面(Unity の axis = at に乗る面)の最も高い所 < 天端 ⇒ 天端の上に切り口は出ない
    uv = [_b2u(vt.co) for vt in o0.data.vertices]
    k = 0 if axis == "x" else 2
    on = [t for t in uv if abs(t[k] - at) < 1e-4]
    top_cut = max(t[1] for t in on) if on else float("nan")
    over = max(t[k] for t in uv)
    nd = clean_degenerate(o0)
    rays1 = kado_rays_all(o0, h)
    # 閉じているか: 境界の辺(開いた辺)の数を切る前と比べる
    bm = bmesh.new(); bm.from_mesh(o0.data)
    nbnd = sum(1 for e in bm.edges if e.is_boundary); bm.free()
    info = dict(name=name, src=name0, axis=axis, at=at, before_max=(x1 if axis == "x" else z1), after_max=over,
                cut_faces=nf, dropped_verts=nout, cut_top_y=top_cut, crest=h, degenerate=nd, boundary_edges=nbnd, arm=arm_info,
                rays_before=rays0, rays_after=rays1)
    print("KADOCUT %s" % info)
    V.set_origin(o0, (0, 0, 0))
    return o0, name, info


def render_kado_cut(h, v, axis, at, arm=0.0):
    """切った隅の駒を、袖の背(切り口の平面)に見立てた板と並べて撮る: 隅の外から・切り口の側から・マゼンタ"""
    V.reset()
    _import_at(os.path.join(OUT_WALL, kado_cut_name(h, v, axis, at, arm) + ".fbx"), 0, 0, 0)
    hook_stone_textures()
    ground()
    tag = "%s_%s%s%.3f" % (int(round(h * 1000)), v, axis, at) + ("_L%.3f" % arm if arm else "")
    # 袖の背の見立て(切り口の平面から 1cm 外・厚み 0.6・天端 h+0.3)── 撮る 1 枚だけ
    if axis == "x":
        sode = _flat_box("Sode", [(at + 0.01, -0.3, -2.0), (at + 0.61, -0.3, -2.0), (at + 0.61, -0.3, 1.2), (at + 0.01, -0.3, 1.2),
                                  (at + 0.01, h + 0.3, -2.0), (at + 0.61, h + 0.3, -2.0), (at + 0.61, h + 0.3, 1.2), (at + 0.01, h + 0.3, 1.2)],
                         (0.55, 0.52, 0.48))
        cam_cut = _u2b(3.2, h * 0.5, 0.6); look_cut = _u2b(0.0, h * 0.45, -0.3)
    else:
        sode = _flat_box("Sode", [(-2.0, -0.3, at + 0.01), (1.2, -0.3, at + 0.01), (1.2, -0.3, at + 0.61), (-2.0, -0.3, at + 0.61),
                                  (-2.0, h + 0.3, at + 0.01), (1.2, h + 0.3, at + 0.01), (1.2, h + 0.3, at + 0.61), (-2.0, h + 0.3, at + 0.61)],
                         (0.55, 0.52, 0.48))
        cam_cut = _u2b(0.6, h * 0.5, 3.2); look_cut = _u2b(-0.3, h * 0.45, 0.0)
    sode.hide_render = True
    studio_run([], _u2b(3.6, h + 1.4, 3.6), _u2b(-0.5, h * 0.5, -0.5), 30,
               os.path.join(SHOT, "sanno_nozura_kadocut_%s.png" % tag))
    studio_run([], cam_cut, look_cut, 30, os.path.join(SHOT, "sanno_nozura_kadocut_%s_face.png" % tag))
    studio_run([], _u2b(3.6, h + 1.4, 3.6), _u2b(-0.5, h * 0.5, -0.5), 30,
               os.path.join(SHOT, "sanno_nozura_kadocut_%s_magenta.png" % tag), magenta=True)
    studio_run([], cam_cut, look_cut, 30, os.path.join(SHOT, "sanno_nozura_kadocut_%s_face_magenta.png" % tag), magenta=True)
    sode.hide_render = False
    studio_run([], _u2b(3.6, h + 1.4, 3.6), _u2b(-0.5, h * 0.5, -0.5), 30,
               os.path.join(SHOT, "sanno_nozura_kadocut_%s_sode.png" % tag))


def check_kado(h=1.50):
    """⭕ 隅の駒の腕の先の切り口 = 直線の駒の切り口(天端から 0.25 まで・1mm で丸め)"""
    ow, _, _ = make_wall(h, 0.0, "a")
    ref_p = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, -L / 2)}   # 直線の +X 端(Unity X = +0.909)
    ref_m = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(ow, L / 2)}    # 直線の −X 端
    bad = 0
    for v in KADO_VARIANTS:
        o, name = make_kado(h, v)
        # 腕1 の先 = Unity X = −0.909 ⇔ Blender X = +0.909 ── 直線の +X 端と合わさる
        a1 = {(round(p[0], 3), round(p[1] - h, 3)) for p in seam_verts(o, L / 2)}
        # 腕2 の先 = Unity Z = −0.909 ⇔ Blender Y = +0.909。直線の −X 端と比べるため (Blender X, Z) へ写す
        a2 = set()
        for vt in o.data.vertices:
            if abs(vt.co.y - L / 2) < 1e-4:
                # 腕2 の局所: 直線の駒の Unity Z = 腕2 の Unity X ⇒ Blender Y' = −(Unity X) = Blender X
                a2.add((round(vt.co.x, 3), round(vt.co.z - h, 3)))
        # 裏石の帯は面から 0.36〜0.95(2026-09-26)⇒ 両腕の先の端の裏石の奥の列が正方形の奥の角(面から 0.66 より奥)で
        # 重なり、腕2 の先の物を切り離す・もう一方の腕の切り口(奥 0.909)で尻が切られる。
        # ⇒ 面から 0.6 までの切り口の点は直線の駒と同じ(欠け 0・余り 0)を検める。0.6 より奥は数えない(`kado_ura`)
        top = lambda S: {p for p in S if p[1] > -0.25 and p[0] < 0.6}
        d1 = len(top(ref_p) ^ top(a1))
        d2 = len(top(ref_m) ^ top(a2))
        deep = lambda S: {p for p in S if p[1] > -0.25 and p[0] >= 0.6}
        print("NOZURA KADO CHECK %s: 腕1の先 %d点 差%d / 腕2の先 %d点 差%d(面から 0.6 より奥で直線の駒と違う点 %d / %d)" % (
            name, len(top(a1)), d1, len(top(a2)), d2, len(deep(a1) ^ deep(ref_p)), len(deep(a2) ^ deep(ref_m))))
        bad += (d1 > 0) + (d2 > 0)
    return bad


# ------------------------------------------------------------------ 石段の袖
def sode_name(keri, fumi, v):
    return "IshidanSodeNozura_%.3f_%.3f_%s" % (keri, fumi, v)


def make_sode(keri, fumi, v, fresh=True):
    """`IshidanSode` と同じ枠。s = Unity Z(+ = 坂下)・天端 Y = 0.30 + (f/2 − s)·k/f。
    厚み X ±0.30 の両面を割肌に(d = +X 面から奥へ 0..0.60)。fresh=False は場を消さない(背を法で切る駒で隣の駒を継ぐ)。"""
    if fresh:
        V.reset()
    mats = materials()
    f = fumi
    cells = layout(f, SODE_DEPTH, "nozura-sode-B-%.3f" % f, "nozura-sode-%.3f-%s" % (f, v),
                   wr=(0.22, 0.45), gw=min(0.30, f * 0.36), bcmax=0.04,
                   head=0.015, rr=(1.2, 2.0))     # 袖の天端は石段に沿う一本の線 ⇒ 頭の不揃いは天端の下 3cm の幅・頭はほぼ平ら

    def P(s, u, d):
        # Unity X = +0.30 − d(両面)⇒ Blender X = −(0.30 − d)
        top = SODE_HT + (f / 2 - s) * keri / f
        return (-(SODE_HALF - d), -s, top + u)
    cells = [(clip(p, (0, -1), SODE_DEPTH), k, key) for p, k, key in cells]
    cells = [c for c in cells if len(c[0]) >= 3 and area(c[0]) > 0.004]
    objs = build_stones(cells, P, mats, double=2 * SODE_HALF, face_prot=(-0.04, -0.005),
                        tag="sode%.3f" % f)
    # 芯の板(両面の目地の奥を塞ぐ・X = ±0.18)
    for sx_ in (1, -1):
        bm = bmesh.new()
        vs = [bm.verts.new(P(s_, u_, SODE_HALF - sx_ * 0.18)) for s_, u_ in
              ((-f / 2, -0.10), (f / 2, -0.10), (f / 2, -SODE_DEPTH), (-f / 2, -SODE_DEPTH))]
        bm.faces.new(vs)
        me = bpy.data.meshes.new("core"); bm.to_mesh(me); bm.free()
        oc = bpy.data.objects.new("core", me); bpy.context.scene.collection.objects.link(oc)
        me.update()
        if me.polygons[0].normal.x * (-sx_) < 0:     # 外(Unity ±X)へ向ける
            me.flip_normals()
        oc.data.materials.append(mats[1]); box_uv(oc, (0.3, 0.6))
        objs.append(oc)
    # 天端の目地の奥の板(芯 X = 0・天端の 0.005 下から 0.35 下)── 背の天端を上げたので天端の目地が厚みを素通しになる(2026-09-25)
    for sx_ in (1, -1):
        bm = bmesh.new()
        vs = [bm.verts.new(P(s_, u_, SODE_HALF)) for s_, u_ in
              ((-f / 2, BACK2[1]), (f / 2, BACK2[1]), (f / 2, BACK2[2]), (-f / 2, BACK2[2]))]
        bm.faces.new(vs)
        me = bpy.data.meshes.new("core2"); bm.to_mesh(me); bm.free()
        oc = bpy.data.objects.new("core2", me); bpy.context.scene.collection.objects.link(oc)
        me.update()
        if me.polygons[0].normal.x * (-sx_) < 0:
            me.flip_normals()
        oc.data.materials.append(mats[1]); box_uv(oc, (0.3, 0.6))
        objs.append(oc)
    name = sode_name(keri, fumi, v)
    o = V.join(objs, name)
    # ⛔ 石は X = ±0.30 の面を越えない(段石の小口に突き付く面)
    for vt in o.data.vertices:
        vt.co.x = max(-SODE_HALF, min(SODE_HALF, vt.co.x))
    bisect_keep(o, (0, -f / 2, 0), (0, -1, 0))        # Unity Z ≤ +f/2
    bisect_keep(o, (0, f / 2, 0), (0, 1, 0))
    V.set_origin(o, (0, 0, 0))
    return o, name, len(cells)


# ------------------------------------------------------------------ 見切り石
def make_mikiri():
    V.reset()
    mats = materials()
    rng = random.Random("nozura-mikiri")
    w, hh = 0.86, 0.80
    poly = [(-w / 2 + 0.10, -hh), (w / 2 - 0.06, -hh), (w / 2, -hh + 0.15), (w / 2 - 0.02, -0.18),
            (w / 2 - 0.16, 0.0), (-w / 2 + 0.20, 0.02), (-w / 2, -0.20), (-w / 2 + 0.02, -hh + 0.12)]
    poly = head_arc(poly, 0.0, 0.0, 0.55)
    P = wall_P(hh - BURY, 0.0)   # 床から 0.60 見え・0.20 根入れ
    o = stone_obj("Sanno_Nozura_Mikiri", poly, rng, P, 0.90, face_prot=(0.0, 0.02))
    o.data.materials.append(mats[0])
    box_uv(o, (0.2, 0.4))
    V.set_origin(o, (0, 0, 0))
    return o, "Sanno_Nozura_Mikiri"


# ------------------------------------------------------------------ 斜めに切った端の駒(2026-09-26 EDO-0437)
NKIRI_CHIP = 0.08      # 切る面で残る石の欠片(二辺ともこれ未満)は落とす


def nkiri_name(deg, end, face, h, v):
    return "Sanno_Nozura_Kiri%03d%s%s_H%04d_%s" % (int(round(abs(deg) * 10)), end, face, int(round(h * 1000)), v)


def backing_span(name, h, mat, s0, s1, d=0.12, u0=-0.12, u1=None):
    """`backing` の走りの範囲を s0〜s1 にした板(2間に跨る駒・見切り石の幅の板)"""
    bm = bmesh.new()
    P = wall_P(h, 0.0)
    vs = []
    for s in (s0, s1):
        for u in (u0, -(h + BURY) if u1 is None else u1):
            vs.append(bm.verts.new(P(s, u, d)))
    bm.faces.new((vs[0], vs[1], vs[3], vs[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    me.update()
    if me.polygons[0].normal.y > 0:
        me.flip_normals()
    box_uv(o, (0.3, 0.7))
    return o


def nkiri_plane(deg, end, face):
    """斜めに切る鉛直面(Blender の co, no)。残すのは dot(x − co, no) <= 0。
    Unity 局所で: 端 e = +1(P = +X 端)/ −1(M = −X 端)、k = +1(L = 見え面の側が長い)/ −1(S)。
    残す側 e·x <= L/2 + k·cot(deg)·z ── 天端の前の縁の端 (e·L/2, 天端, 0) を通る。"""
    e = 1 if end == "P" else -1
    k = 1 if face == "L" else -1
    cot = 1.0 / math.tan(math.radians(abs(deg)))
    return (-e * L / 2, 0.0, 0.0), (-e, k * cot, 0.0), e, k, cot


def make_nkiri(h, deg, end, face, v):
    """野面の乱積みの駒の片端を、走りと deg で交わる**鉛直な面**で切る(女坂の袖の外面に当てる端)。
    ⭐ 残る側(−e 端)は直線の駒と同じ継ぎ目(X = −e·0.909・端の石が同じ)⇒ 直線の駒をそのまま継ぐ。
    ⭐ 切る面は**天端の前の縁の端 = (e·0.909, 天端, 0)**を通る ⇒ 天端の線の上では直線の駒と同じ 1間。
       面(法)は下ほど前へ出るので、L は足の前が枠の外へ最大 0.3·(見付+0.2)·cot 出る / S は控えが枠の外へ出る。
       枠の外の石は隣の 1間(次の個体の割り・端の石は同じ)から採る ── 1間の枠の中だけだと切り口の奥に石が無い。"""
    V.reset()
    mats = materials()
    co, no, e, k, cot = nkiri_plane(deg, end, face)
    v2 = VARIANTS[(VARIANTS.index(v) + 1) % len(VARIANTS)]
    cells_a, cells_b = [], []
    for poly, kind, key in wall_cells(v):
        p2 = clip(poly, (0, -1), h + BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells_a.append((p2, kind, key))
    shared = "B+" if e > 0 else "B-"       # 隣の 1間の、共有する継ぎ目の側の端の石(= A の端の石と同じ形)は採らない
    for poly, kind, key in wall_cells(v2):
        if kind == ("B-" if e > 0 else "B+"):
            continue
        p2 = clip([(p[0] + e * L, p[1]) for p in poly], (0, -1), h + BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells_b.append((p2, kind, key))
    P = wall_P(h, 0.0)
    objs = build_stones(cells_a, P, mats, tag="wall")
    objs += build_stones(cells_b, P, mats, tag="wallK")
    objs += wall_ura(h, 0.0, v, mats)
    objs += wall_ura(h, 0.0, v2, mats, off=e * L, skip=("B-" if e > 0 else "B+"))
    s0, s1 = (-L / 2, L / 2 + L) if e > 0 else (-L / 2 - L, L / 2)
    objs += wall_fill(objs, h, 0.0, v, mats, s0, s1, tag="nkiri")
    objs.append(backing_span("back", h, mats[1], s0, s1))
    objs.append(backing_span("back2", h, mats[1], s0, s1, *BACK2))
    name = nkiri_name(deg, end, face, h, v)
    o = V.join(objs, name)
    # 継ぐ側(−e 端)は直線の駒と同じ切り口
    if e > 0:
        bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))        # Unity X >= −L/2
    else:
        bisect_keep(o, (-L / 2, 0, 0), (-1, 0, 0))      # Unity X <= +L/2
    # ⚠ 斜めの面は bpy.ops.mesh.bisect だと面から 0.036 外に頂点が残った(軸に沿う継ぎ目の面は合う)⇒ bmesh で切って口を塞ぐ
    n = Vector(no).normalized(); c = Vector(co)
    bm = bmesh.new(); bm.from_mesh(o.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                 plane_co=c, plane_no=n, clear_outer=True, clear_inner=False)
    cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge) and x.is_valid and x.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=cut, sides=0)["faces"]
    uvl = bm.loops.layers.uv.active
    t = Vector((n.y, -n.x, 0.0))
    for f in filled:
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        for l in f.loops:
            q = l.vert.co - c
            l[uvl].uv = (q.dot(t) / TILE + 0.37, q.z / TILE + 0.11)
    # bisect が面の脇に残す重複・孤立頂点を掃除(bounds が嘘をつく)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.delete(bm, geom=[x for x in bm.verts if not x.link_faces], context='VERTS')
    # 切る面で石の角だけが残った欠片(二辺とも CHIP 未満)は袖の面の前に浮いて見えた ⇒ 落とす(残る口は目地の幅)
    bm.verts.ensure_lookup_table()
    seen, drop = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        st, comp = [v0], []
        seen.add(v0.index)
        while st:
            a = st.pop(); comp.append(a)
            for ed in a.link_edges:
                b = ed.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); st.append(b)
        ext = sorted(max(q.co[i] for q in comp) - min(q.co[i] for q in comp) for i in range(3))
        if ext[1] < NKIRI_CHIP:
            drop += comp
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
    print("NKIRI 欠片を落とした 頂点 %d" % len(drop))
    bm.to_mesh(o.data); bm.free(); o.data.update()
    V.set_origin(o, (0, 0, 0))
    return o, name


def nkiri_ref_seam(h, deg, end, face, v):
    """直線の駒の、継ぐ側の切り口(天端から 0.25 まで)── make_wall は reset するので切る駒より先に呼ぶ"""
    e = 1 if end == "P" else -1
    ref_o, _, _ = make_wall(h, 0.0, v)
    return [(y, round(z - h, 3)) for y, z in seam_verts(ref_o, e * L / 2) if z > h - 0.25]


def check_nkiri(o, h, deg, end, face, v, ref_seam):
    """⭕ 切る面より外に頂点が無い / 継ぐ側の切り口 = 直線の駒の切り口 / 面の角 / 孤立頂点 / 背の天端"""
    co, no, e, k, cot = nkiri_plane(deg, end, face)
    n = Vector(no).normalized(); c = Vector(co)
    ok = []
    bite = max((vv.co - c).dot(n) for vv in o.data.vertices)
    ok.append(("切る面より外に頂点が無い", bite < 1e-4, "%.6f" % bite))
    on = [vv for vv in o.data.vertices if abs((vv.co - c).dot(n)) < 1e-4]
    ok.append(("切る面に頂点が乗る", len(on) >= 20, "%d 点" % len(on)))
    # 面の角を測り直す: 切る面の上の頂点を Unity (x, z) に直して一次式 x = a + b·z を当てる
    pts = [(-vv.co.x, -vv.co.y) for vv in on]
    if len(pts) >= 2:
        mz = sum(p[1] for p in pts) / len(pts); mx = sum(p[0] for p in pts) / len(pts)
        szz = sum((p[1] - mz) ** 2 for p in pts); sxz = sum((p[1] - mz) * (p[0] - mx) for p in pts)
        b = sxz / szz if szz > 1e-9 else 0.0
        ang = math.degrees(math.atan2(1.0, abs(b)))
        ok.append(("面の角 %.1f°" % deg, abs(ang - abs(deg)) < 0.05, "%.3f°" % ang))
        longer = "L" if e * b > 0 else "S"
        ok.append(("見え面の側が%s" % ("長い" if face == "L" else "短い"), longer == face, longer))
        x_at0 = mx - b * mz
        ok.append(("天端の前の縁の端 = 枠の端 %+.3f" % (e * L / 2), abs(x_at0 - e * L / 2) < 2e-3, "%+.4f" % x_at0))
    # 継ぐ側の切り口が直線の駒と同じ(天端から 0.25 まで・Blender X = e·L/2 が Unity の −e 端)
    xb = e * L / 2
    mine = [(y, round(z - h, 3)) for y, z in seam_verts(o, xb) if z > h - 0.25]
    ref = ref_seam
    diff = len(set(mine) ^ set(ref))
    ok.append(("継ぐ側の切り口 = 直線の駒 %s" % wall_name(h, 0.0, v), diff == 0 and len(ref) > 0, "%d 点・差 %d" % (len(ref), diff)))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats_ = sorted({m.name for m in o.data.materials})
    ok.append(("材は Kirishi / Danishi だけ", set(mats_) <= {"Kirishi", "Danishi"}, ",".join(mats_)))
    bpy.context.view_layer.update()
    back, over, at, npt = crest_check([o], lambda x, z: h, lambda x, z: z <= -FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    ok.append(("頭が天端の線より上へ出ない", over <= 0.005, "%+.3f" % over))
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    print("NKIRI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d / 天端の前の縁の端(局所) (%+.3f, %.3f, 0)" % (
        o.name, x0, x1, y0, y1, z0, z1, tris(o), e * L / 2, h))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


def read_nkiri_list(path):
    rows = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            tag, deg, end, face, hs = ln.split()
            for hh in hs.split(","):
                rows.append((tag, float(deg), end, face, float(hh)))
    return rows


# ------------------------------------------------------------------ 相手の法で切る駒(2026-09-26 EDO-0437 第3巡)
NNORI = BATTER            # 相手(野面の土留め・隅の駒)の面の法 = 3分。焼いた駒の前の包絡も 0.3(+0.065〜0.08 の出)で平行
NNORI_KNEE = None         # 袖の背の法は袖の底まで通す(鉛直の膝を持たない ── 2026-09-26 EDO-0437)。
#   旧 −0.60(膝より下は鉛直)では、相手の法の足(床の下 0.2 まで前へ出る)が膝の下の鉛直の背を貫いた
#   (前庭の北東 TW_Zentei_N_kado2 × 参道の階の東の袖 001f・0.035〜0.040・8方向の光線で中)。膝より上の形は変わらない。
NNORI_KNEE_OLD = -0.60   # 旧の膝。これより上は旧と同じ形 ⇒ 検算で「旧の膝で駒が残る」を見る
NNORI_SODE_E = [-0.25, -0.20, -0.15, -0.10, -0.05, 0.00, 0.05]   # 背の出 e(0.05 刻み)。−0.30 は膝の下が痩せ切る


def bm_cut_keep(o, co, no, chip=NKIRI_CHIP, uv_ofs=(0.37, 0.11)):
    """平面 co・法線 no(Blender)の裏側(dot(x − co, no) <= 0)だけ残し、切り口を塞ぐ(斜めの面は bmesh で ── `make_nkiri` の教訓)。
    孤立頂点と、二辺とも chip 未満の欠片を落とす。塞いだ面の UV は面の上の平面投影。返り値 = 落とした欠片の頂点数。"""
    n = Vector(no).normalized(); c = Vector(co)
    bm = bmesh.new(); bm.from_mesh(o.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                 plane_co=c, plane_no=n, clear_outer=True, clear_inner=False)
    cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge) and x.is_valid and x.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=cut, sides=0)["faces"]
    uvl = bm.loops.layers.uv.active
    t = Vector((n.y, -n.x, 0.0)) if abs(n.z) < 0.99 else Vector((1.0, 0.0, 0.0))
    if t.length < 1e-6:
        t = Vector((1.0, 0.0, 0.0))
    t.normalize()
    b2 = n.cross(t).normalized()
    for f in filled:
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        for l in f.loops:
            q = l.vert.co - c
            l[uvl].uv = (q.dot(t) / TILE + uv_ofs[0], q.dot(b2) / TILE + uv_ofs[1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.delete(bm, geom=[x for x in bm.verts if not x.link_faces], context='VERTS')
    bm.verts.ensure_lookup_table()
    seen, drop = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        st, comp = [v0], []
        seen.add(v0.index)
        while st:
            a = st.pop(); comp.append(a)
            for ed in a.link_edges:
                b = ed.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); st.append(b)
        ext = sorted(max(q.co[i] for q in comp) - min(q.co[i] for q in comp) for i in range(3))
        if ext[1] < chip:
            drop += comp
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(drop)


# ---- (1) 小口を相手の法で切った短い駒 `Sanno_Nozura_Nori<P|M>_L<天端の長さmm>_H<見付mm>_<v>` ------------------
def nnori_name(ls, end, h, v):
    return "Sanno_Nozura_Nori%s_L%04d_H%04d_%s" % (end, int(round(ls * 1000)), int(round(h * 1000)), v)


def nnori_frame(ls, end):
    """e(+1 = P = 切る端が局所 +X)、割りの窓の中の切る端の s_e と窓の中心 s_c(1間の割りの座標)。
    窓 = 継ぐ側の端を 1間の継ぎ目(∓0.909)に置いた長さ ls ── 継ぐ側は直線の駒の切り口と頂点まで同じ。"""
    e = 1 if end == "P" else -1
    s_e = e * (ls - L / 2)
    s_c = -e * (L / 2 - ls / 2)
    return e, s_e, s_c


def make_nnori(ls, h, end, v):
    """野面の乱積みの短い駒の片端(小口)を**相手の法 1:0.3 の面**で切る(入隅の可動側の端が、通す側の見え面に当たる所)。
    局所(ピボット後): 走り X ∈ [−ls/2, +ls/2](天端の前の縁の長さ = ls)・切る端は e·X ≤ ls/2 + NNORI·(Y − h)
    (上ほど外へ ── 相手の面は下ほど前へ出る)。反対の端は直線の駒の継ぎ目と同じ切り口。見付 h・ピボット Y=0 = 天端 − h・
    Z=0 = 天端の線での面(見え面 +Z)は直線の駒と同じ。⛔ 伸縮させない(scale.x で法が変わる)。"""
    V.reset()
    mats = materials()
    e, s_e, s_c = nnori_frame(ls, end)
    cells = []
    for poly, kind, key in wall_cells(v):
        p2 = clip(poly, (0, -1), h + BURY)
        if len(p2) >= 3 and area(p2) > 0.004:
            cells.append((p2, kind, key))
    P = wall_P(h, 0.0)
    objs = build_stones(cells, P, mats, tag="wall")
    objs += wall_ura(h, 0.0, v, mats)
    objs += wall_fill(objs, h, 0.0, v, mats, -L / 2, L / 2)
    objs.append(backing("back", h, 0.0, mats[1]))
    objs.append(backing("back2", h, 0.0, mats[1], *BACK2))
    name = nnori_name(ls, end, h, v)
    o = V.join(objs, name)
    # 継ぐ側(−e 端)は直線の駒と同じ切り口
    if e > 0:
        bisect_keep(o, (L / 2, 0, 0), (1, 0, 0))        # Unity X >= −L/2
    else:
        bisect_keep(o, (-L / 2, 0, 0), (-1, 0, 0))      # Unity X <= +L/2
    # 切る端: e·X ≤ e·s_e + NNORI·(Y − h) ⇔ Blender で dot(p − (−s_e, 0, h), (−e, 0, −NNORI)) ≤ 0
    nd = bm_cut_keep(o, (-s_e, 0.0, h), (-e, 0.0, -NNORI))
    print("NNORI 欠片を落とした 頂点 %d" % nd)
    # 窓の中心をピボットへ(Unity X −= s_c ⇔ Blender X += s_c)
    o.data.transform(mathutils.Matrix.Translation((s_c, 0.0, 0.0))); o.data.update()
    V.set_origin(o, (0, 0, 0))
    return o, name


def check_nnori(o, ls, h, end, v, ref_seam):
    """⭕ 法の面より外に頂点が無い / 面に頂点が乗る / 法 = NNORI / 天端の前の縁の端 = ±ls/2 / 継ぐ側の切り口 = 直線の駒 / 孤立頂点 / 材 / 背の天端"""
    e = 1 if end == "P" else -1
    ok = []
    U = [(-vv.co.x, vv.co.z, -vv.co.y) for vv in o.data.vertices]
    g = lambda x, y: e * x - (ls / 2 + NNORI * (y - h))           # > 0 = 面の外
    bite = max(g(x, y) for x, y, z in U)
    ok.append(("法の面より外に頂点が無い", bite < 1e-4, "%.6f" % bite))
    on = [(x, y) for x, y, z in U if abs(g(x, y)) < 1e-4]
    ok.append(("法の面に頂点が乗る", len(on) >= 20, "%d 点" % len(on)))
    if len(on) >= 2:
        my = sum(p[1] for p in on) / len(on); mx = sum(p[0] for p in on) / len(on)
        syy = sum((p[1] - my) ** 2 for p in on); sxy = sum((p[1] - my) * (p[0] - mx) for p in on)
        sl = e * sxy / syy if syy > 1e-9 else 0.0
        ok.append(("法 = 1:%.2f(実測 e·dX/dY)" % NNORI, abs(sl - NNORI) < 1e-3, "%.4f" % sl))
        x_top = mx + (h - my) * (sxy / syy if syy > 1e-9 else 0.0)
        ok.append(("天端の線での切る端 = %+.3f" % (e * ls / 2), abs(x_top - e * ls / 2) < 2e-3, "%+.4f" % x_top))
    xb = e * ls / 2                                    # 継ぐ側(Unity X = −e·ls/2)の Blender X
    mine = [(y, round(z - h, 3)) for y, z in seam_verts(o, xb) if z > h - 0.25]
    diff = len(set(mine) ^ set(ref_seam))
    ok.append(("継ぐ側の切り口 = 直線の駒 %s" % wall_name(h, 0.0, v), diff == 0 and len(ref_seam) > 0, "%d 点・差 %d" % (len(ref_seam), diff)))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats_ = sorted({m.name for m in o.data.materials})
    ok.append(("材は Kirishi / Danishi だけ", set(mats_) <= {"Kirishi", "Danishi"}, ",".join(mats_)))
    bpy.context.view_layer.update()
    back, over, at, npt = crest_check([o], lambda x, z: h, lambda x, z: z <= -FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    ok.append(("頭が天端の線より上へ出ない", over <= 0.005, "%+.3f" % over))
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    print("NNORI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d" % (o.name, x0, x1, y0, y1, z0, z1, tris(o)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


def read_nnori_list(path):
    """各行 `札 P|M 見付 長さ,長さ,…`(# 以降は註)"""
    rows = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            tag, end, hs, lens = ln.split()
            for ls in lens.split(","):
                rows.append((tag, end, float(hs), float(ls)))
    return rows


def render_nnori(ls, h, end, v):
    """短い駒の法で切った端を、通す側の土留め(直線の駒 H0.90・見え面を −e·X へ・天端を揃える)の見え面へ当てて撮る。
    相手の駒は法の包絡の出(0.075)だけ離す(= 据え手が触れている箇所で寄せた所)。反対の端に直線の駒 1 を継ぐ。"""
    e = 1 if end == "P" else -1
    V.reset()
    _import_at(os.path.join(OUT_WALL, nnori_name(ls, end, h, v) + ".fbx"), 0, 0, 0)
    _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "b") + ".fbx"), -e * (ls / 2 + L / 2), 0, 0)
    hw = 0.90
    _import_at(os.path.join(OUT_WALL, wall_name(hw, 0, "c") + ".fbx"), e * (ls / 2 + 0.075), L / 2, h - hw, -90.0 * e)
    hook_stone_textures()
    ground(0.0, -30, 30)
    _upper_ground(h, (-4 * L, 0.0) if e > 0 else (0.0, 4 * L), (-6.0, -0.25))
    tag = nnori_name(ls, end, h, v)
    studio_run([], _u2b(-e * 1.2, h + 0.9, 3.4), _u2b(e * ls * 0.3, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(-e * 1.2, h + 0.9, 3.4), _u2b(e * ls * 0.3, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + "_magenta.png"), magenta=True)
    # 真横(走りの向きの横 = 見え面から)から: 切る端の法が相手の面に沿うか
    for nm in ("Upper",):
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob)
    cam = bpy.context.scene.camera
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.4
    cam.location = _u2b(e * ls * 0.3, h * 0.5, 8.0)
    cam.rotation_euler = (Vector(_u2b(e * ls * 0.3, h * 0.5, 0.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(SHOT, tag + "_side.png"))


# ---- (2) 背を相手の法で切った野面の袖 `IshidanSodeNozuraNori_<蹴上>_<踏面>_E±x.xx_<v>` -------------------------
def sode_nnori_name(keri, fumi, e, v):
    return "IshidanSodeNozuraNori_%.3f_%.3f_E%s%.2f_%s" % (keri, fumi, "+" if e >= 0 else "-", abs(e), v)


def sode_nnori_yc(keri):
    """背の出 e を測る高さ(袖の局所 Y)= 石段の袖の `sode_nori_yc` と同じ((0.30 + 蹴上)/2)。"""
    return (SODE_HT + keri) / 2.0


def make_sode_nnori(keri, fumi, e, v, knee=NNORI_KNEE):
    """野面の袖 `make_sode(keri, fumi, v)` の坂上の端(背・−Z)を**相手(出隅の駒・土留め)の法 1:0.3** と平行な面で切る。
    背の面: Z = −踏面/2 − e − NNORI·(Y − Yc)(Yc = `sode_nnori_yc`)── 上ほど坂上へ出る。knee = None(既定)は袖の底まで法で切る / 数を渡すとそれより下は鉛直(Z = 膝での値)。
    e > 0 は平らな駒より坂上へ出る(坂上に次の個体を継いで伸ばす ⇒ 天端・割りは一続き)/ e < 0 は詰める。"""
    V.reset()
    o0, _, _ = make_sode(keri, fumi, v, fresh=False)
    other = "b" if v == "a" else "a"
    o1, _, _ = make_sode(keri, fumi, other, fresh=False)
    o1.data.transform(mathutils.Matrix.Translation((0.0, fumi, keri))); o1.data.update()   # 坂上へ 1 駒(Unity Z −踏面・Y +蹴上)
    V.dedup_materials()
    name = sode_nnori_name(keri, fumi, e, v)
    whole = V.join([o0, o1], name)
    yc = sode_nnori_yc(keri)
    if knee is None:
        # 背の法の面より坂下(Unity Z ≥ −f/2 − e − NNORI·(Y − Yc))だけを残す ── 袖の底まで法で切る(相手の法の足を貫かない)
        n1 = n2 = 0
        n3 = bm_cut_keep(whole, (0.0, fumi / 2.0 + e, yc), (0.0, 1.0, -NNORI))
        o = whole
    else:
        zk = -fumi / 2.0 - e - NNORI * (knee - yc)           # 膝での背の Z(Unity)
        # 部品 1: 膝の鉛直面より坂下(Unity Z ≥ zk ⇔ Blender Y ≤ −zk)
        p2 = whole.copy(); p2.data = whole.data.copy(); bpy.context.scene.collection.objects.link(p2)
        n1 = bm_cut_keep(whole, (0.0, -zk, 0.0), (0.0, 1.0, 0.0))
        # 部品 2: 膝より坂上(Unity Z ≤ zk)で、背の法の面より坂下(Unity Z ≥ −f/2 − e − NNORI·(Y − Yc))── 膝より上だけが残る
        n2 = bm_cut_keep(p2, (0.0, -zk, 0.0), (0.0, -1.0, 0.0))
        n3 = bm_cut_keep(p2, (0.0, fumi / 2.0 + e, yc), (0.0, 1.0, -NNORI))
        o = V.join([whole, p2], name)
    o.name = name; o.data.name = name
    # ⛔ 石は X = ±0.30 の面を越えない(`make_sode` と同じ)
    for vt in o.data.vertices:
        vt.co.x = max(-SODE_HALF, min(SODE_HALF, vt.co.x))
    V.set_origin(o, (0, 0, 0))
    print("SNORI 欠片を落とした 頂点 %d/%d/%d" % (n1, n2, n3))
    return o, name


def check_sode_nnori(o, keri, fumi, e, knee=NNORI_KNEE):
    ok = []
    U = [(-vv.co.x, vv.co.z, -vv.co.y) for vv in o.data.vertices]
    yc = sode_nnori_yc(keri)
    kn = -99.0 if knee is None else knee
    zb = lambda y: -fumi / 2.0 - e - NNORI * (max(y, kn) - yc)
    worst = max(zb(y) - z for x, y, z in U)
    ok.append(("背の法の面より坂上に頂点が無い", worst < 1e-4, "最大 %.5f" % worst))
    onb = [(y, z) for x, y, z in U if abs(z - zb(y)) < 1e-4 and y > kn + 0.05]
    ok.append(("背の法の面に頂点が乗る(膝より上)", len(onb) >= 8, "%d 点" % len(onb)))
    if len(onb) >= 2:
        my = sum(p[0] for p in onb) / len(onb); mz = sum(p[1] for p in onb) / len(onb)
        sl = sum((y - my) * (z - mz) for y, z in onb) / max(1e-9, sum((y - my) ** 2 for y, _ in onb))
        ok.append(("背の法 = 1:%.2f(実測 −dZ/dY)" % NNORI, abs(-sl - NNORI) < 1e-3, "%.4f" % -sl))
    ok.append(("坂下の端は平らな駒のまま Z=+踏面/2", abs(max(z for x, y, z in U) - fumi / 2) < 1e-4, "%.4f" % max(z for x, y, z in U)))
    ok.append(("石は X = ±0.30 を越えない", max(abs(x) for x, y, z in U) <= SODE_HALF + 1e-6, "%.4f" % max(abs(x) for x, y, z in U)))
    top = lambda z: SODE_HT + (fumi / 2.0 - z) * keri / fumi
    over = max(y - top(z) for x, y, z in U)
    ok.append(("天端が段鼻の線 +0.30 の斜めの一直線を越えない(≤ 0.005 ── 平らな野面の袖も 0.0015 出る)", over <= 0.005, "超過 %.5f" % over))
    ko = NNORI_KNEE_OLD if knee is None else knee
    kept_knee = fumi / 2.0 - (-fumi / 2.0 - e - NNORI * (ko - yc))
    ok.append(("膝(%.2f)の高さに駒が残る(> 0.02)" % ko, kept_knee > 0.02, "%.3f" % kept_knee))
    if knee is None:
        # 背の法を底まで通す ⇒ 袖はこの高さで痩せ切る(相手の法の足の前へ出ない)。旧の膝より下であること(膝より上の見えは旧と同じ)
        y_end = yc - (fumi + e) / NNORI
        ymin = min(y for x, y, z in U)
        ok.append(("痩せ切る高さ %.3f が旧の膝 %.2f より下" % (y_end, NNORI_KNEE_OLD), y_end < NNORI_KNEE_OLD, "底 %.3f" % ymin))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    mats_ = sorted({m.name for m in o.data.materials})
    ok.append(("材は Kirishi / Danishi だけ", set(mats_) <= {"Kirishi", "Danishi"}, ",".join(mats_)))
    bpy.context.view_layer.update()
    back, ov, at, npt = crest_check([o], lambda x, z: top(z), lambda x, z: abs(x) <= SODE_HALF - FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    print("SNORI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d" % (o.name, x0, x1, y0, y1, z0, z1, tris(o)))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


def render_sode_nnori(keri, fumi, e, v, n=3):
    """背を切った袖 + 坂下へ平らな野面の袖 n−1 駒。背に相手(野面の直線の駒 H0.90・見え面 +Z・天端 = 袖の背の天端)を
    法の包絡の出(0.075)だけ離して据え、切り口が相手の面に沿うか撮る。"""
    V.reset()
    _import_at(os.path.join(OUT_SODE, sode_nnori_name(keri, fumi, e, v) + ".fbx"), 0, 0, 0)
    for i in range(1, n):
        vv = "ab"[("ab".index(v) + i) % 2]
        _import_at(os.path.join(OUT_SODE, sode_name(keri, fumi, vv) + ".fbx"), 0, fumi * i, -keri * i)
    hw = 0.90
    ytop = SODE_HT + keri                                # 平らな駒の背での天端
    yc = sode_nnori_yc(keri)
    zw = -fumi / 2.0 - e - NNORI * (ytop - yc) - 0.075   # 相手の天端の線での面
    _import_at(os.path.join(OUT_WALL, wall_name(hw, 0, "a") + ".fbx"), SODE_HALF - L / 2, zw, ytop - hw)
    hook_stone_textures()
    ground(-0.5, -30, 30)
    tag = sode_nnori_name(keri, fumi, e, v)
    studio_run([], _u2b(-2.6, ytop + 0.6, 2.6), _u2b(0.0, 0.0, -0.1), 30, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(-2.6, ytop + 0.6, 2.6), _u2b(0.0, 0.0, -0.1), 30, os.path.join(SHOT, tag + "_magenta.png"), magenta=True)
    cam = bpy.context.scene.camera
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.6
    cam.location = _u2b(-8.0, -0.2, 0.0)
    cam.rotation_euler = (Vector(_u2b(0.0, -0.2, 0.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    V.render(os.path.join(SHOT, tag + "_side.png"))


# ------------------------------------------------------------------ 丈を合わせた見切り石(2026-09-26 EDO-0437)
MIKIRI_TIERS = [1.20, 1.50, 1.80, 2.10]
MIKIRI_W = 0.86
MIKIRI_D = 0.90


def mikiri_name(h):
    return "Sanno_Nozura_Mikiri_H%04d" % int(round(h * 1000))


def make_mikiri_h(h):
    """見付 h の見切り石 ── 土留めの天端の線まで届く石の柱(大きな野面石 2〜3 石を不揃いの横目地で積む)。
    頭は天端の線から下へ 0〜0.08(円弧)・**背の上面は天端の線に揃う**(背の土 = 天端の高さが被らない)。
    座標は直線の駒と同じ(中心・床レベル・Z=0 は天端の線での面・見え面 +Z・3分の法)。根入れ 0.20。"""
    V.reset()
    mats = materials()
    rng = random.Random("nozura-mikiri-H%04d" % int(round(h * 1000)))
    w = MIKIRI_W
    total = h + BURY
    nst = 2 if h <= 1.55 else 3
    # 横目地の高さ(天端から下へ)── 石ごとの丈を 0.85〜1.15 で振る・目地は ±0.06 で傾ける
    wts = [rng.uniform(0.85, 1.15) for _ in range(nst)]
    cuts, acc = [], 0.0
    for wt in wts[:-1]:
        acc += wt / sum(wts) * total
        cuts.append((-acc + rng.uniform(-0.04, 0.04), rng.uniform(-0.06, 0.06)))
    g = 0.03
    cells = []
    for i in range(nst):
        poly = [(-w / 2, -total + 0.02), (w / 2, -total + 0.02), (w / 2, HEAD + 0.12), (-w / 2, HEAD + 0.12)]
        if i > 0:                       # 上の目地の下: u <= uc + sl·s − g/2
            uc, sl = cuts[i - 1]
            ln = math.hypot(sl, 1.0); n = (-sl / ln, 1.0 / ln)
            poly = clip(poly, n, uc / ln - g / 2)
        if i < nst - 1:                 # 下の目地の上: u >= uc + sl·s + g/2
            uc, sl = cuts[i]
            ln = math.hypot(sl, 1.0); n = (sl / ln, -1.0 / ln)
            poly = clip(poly, n, -uc / ln - g / 2)
        # 角を落とす(野面の輪郭)
        poly = clip(poly, (-1, 0), w / 2 - 0.02 - rng.uniform(0.0, 0.02))      # 輪の 1.03 倍の張り出しを見込む
        poly = clip(poly, (1, 0), w / 2 - 0.02 - rng.uniform(0.0, 0.02))
        for sx, su in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            cut = rng.uniform(0.06, 0.14)
            n = (sx / math.sqrt(2), su / math.sqrt(2))
            # 多角形の最も外の点から cut だけ内へ
            far = max(p[0] * n[0] + p[1] * n[1] for p in poly)
            if i == 0 and su > 0:
                continue                # 頭の角は円弧で落とす
            poly = clip(poly, n, far - cut)
        if i == 0:
            poly = head_arc(poly, rng.uniform(-0.08, 0.08), -rng.uniform(0.0, 0.02), rng.uniform(1.0, 1.4))
        cells.append((poly, "I", "M%d" % i))
    P = wall_P(h, 0.0)
    objs = []
    for poly, kind, key in cells:
        r2 = random.Random("nozura-mikiri|%s|%d" % (key, int(round(h * 1000))))
        top = max(p[1] for p in poly) > -TOP_ROW
        o = stone_obj("st_" + key, poly, r2, P, MIKIRI_D, face_prot=(0.0, 0.02), crest=0.0 if top else None)
        o.data.materials.append(mats[0] if r2.random() < 0.7 else mats[1])
        box_uv(o, (r2.random(), r2.random()))
        objs.append(o)
    objs.append(backing_span("back", h, mats[1], -w / 2 + 0.05, w / 2 - 0.05))
    name = mikiri_name(h)
    o = V.join(objs, name)
    V.set_origin(o, (0, 0, 0))
    return o, name


def check_mikiri_h(o, h):
    ok = []
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    ok.append(("最高 = 天端の線 %.2f" % h, abs(y1 - h) < 0.01, "%.3f" % y1))
    ok.append(("最下 = 床 − 根入れ", abs(y0 + BURY) < 0.06, "%.3f" % y0))
    ok.append(("幅 ≤ %.2f" % MIKIRI_W, x1 - x0 <= MIKIRI_W + 0.01, "%.3f" % (x1 - x0)))
    bpy.context.view_layer.update()
    back, over, at, npt = crest_check([o], lambda x, z: h, lambda x, z: z <= -FACE_ROW)
    ok.append(("背の天端の下がり ≤ %.2f" % CREST_TOL, back <= CREST_TOL, "%+.3f(%d 点)" % (back, npt)))
    ok.append(("頭が天端の線より上へ出ない", over <= 0.005, "%+.3f" % over))
    loose = len(o.data.vertices) - len({i for p in o.data.polygons for i in p.vertices})
    ok.append(("孤立頂点なし", loose == 0, "%d" % loose))
    print("MIKIRI %s X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f] tris=%d 材=%s" % (
        o.name, x0, x1, y0, y1, z0, z1, tris(o), sorted({m.name for m in o.data.materials})))
    for (label, good, note) in ok:
        print("      %s %s %s" % ("⭕" if good else "⛔", label, note))
    return sum(1 for t_ in ok if not t_[1])


# ------------------------------------------------------------------ 測る・書く・撮る
def tris(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def unity_bounds(o):
    xs = [-v.co.x for v in o.data.vertices]; ys = [v.co.z for v in o.data.vertices]
    zs = [-v.co.y for v in o.data.vertices]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


REPORT = []

DEGEN_EDGE = 1e-4        # 辺 0.1mm 未満の三角形は Unity の取り込み(頂点の溶接)で潰れて捨てられる ⇒ 面が抜ける(2026-09-27 EDO-0437 r13)
DEGEN_AREA = 1e-9


def degenerate_tris(o):
    """面積 0(< 1e-9 m²)または辺 < 0.1mm の三角形の数(書き出す三角形で数える)。"""
    me = o.data
    me.calc_loop_triangles()
    vs = me.vertices
    n = 0
    for t in me.loop_triangles:
        a, b, c = (vs[i].co for i in t.vertices)
        if (b - a).cross(c - a).length * 0.5 < DEGEN_AREA or min((b - a).length, (c - b).length, (a - c).length) < DEGEN_EDGE:
            n += 1
    return n


def clean_degenerate(o, rounds=6):
    """0.1mm 未満の頂点を溶接し、潰れた辺・面を溶かし、多角形を三角形に割ってから数え直す(0 になるまで)。返り値 = 残りの数。"""
    for _ in range(rounds):
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=DEGEN_EDGE * 1.05)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=DEGEN_EDGE * 1.05)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        bad = []
        for f in bm.faces:
            a, b, c = (v.co for v in f.verts)
            if (b - a).cross(c - a).length * 0.5 < DEGEN_AREA:
                bad.append(f)
        if bad:
            bmesh.ops.delete(bm, geom=bad, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(o.data); bm.free(); o.data.update()
        n = degenerate_tris(o)
        if n == 0:
            return 0
    return n


def export(o, name, outdir):
    path = os.path.join(outdir, name + ".fbx")
    V.export_fbx([o], path)
    (x0, x1), (y0, y1), (z0, z1) = unity_bounds(o)
    REPORT.append((name, tris(o), x0, x1, y0, y1, z0, z1))
    print("NOZURA %s 面積 0・辺 < 0.1mm の三角形 %d" % (name, degenerate_tris(o)))
    print("NOZURA %s tris=%d X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f]" % (name, tris(o), x0, x1, y0, y1, z0, z1))
    return path


def seam_verts(o, x_b, tol=1e-4):
    """Blender X = x_b の切り口に乗る頂点(Y,Z)の集合(1mm で丸め)"""
    return sorted({(round(v.co.y, 3), round(v.co.z, 3)) for v in o.data.vertices if abs(v.co.x - x_b) < tol})


def check():
    """⭕ 継ぎ目の一致を数で検める: どの種類・どの段でも、+X 端の切り口 = −X 端の切り口(上から共通の深さまで)"""
    res = []
    prof = {}
    for h in (0.30, 1.20, 2.40):
        for v in VARIANTS:
            o, name, _ = make_wall(h, 0.0, v)
            lo = [p for p in seam_verts(o, L / 2) if p[1] > h - 0.25]      # Unity −X 端(天端から 0.25)
            hi = [p for p in seam_verts(o, -L / 2) if p[1] > h - 0.25]     # Unity +X 端
            lo = [(y, round(z - h, 3)) for y, z in lo]; hi = [(y, round(z - h, 3)) for y, z in hi]
            prof[(h, v)] = (lo, hi)
    ref = prof[(1.20, "a")][1]
    bad = 0
    for k, (lo, hi) in prof.items():
        # 天端から測った切り口の頂点が、どの駒の −X 端とも・+X 端とも一致するか
        if set(lo) != set(ref) or set(hi) != set(ref):
            bad += 1
            res.append("⛔ %s: −X端 %d点 / +X端 %d点 / 基準 %d点 (差 %d / %d)" % (
                k, len(lo), len(hi), len(ref), len(set(lo) ^ set(ref)), len(set(hi) ^ set(ref))))
    print("NOZURA CHECK seam: %d/%d 不一致" % (bad, len(prof)))
    for r in res:
        print("NOZURA CHECK", r)
    return bad


# ------------------------------------------------------------------ 天端の帯の検査(2026-09-25 EDO-0430)
CREST_BAND = 0.15   # = EdoBuild.CREST_BAND
CREST_R = 0.6       # = EdoBuild.CREST_R
CREST_TOL = 0.03    # 背の天端の下がりの許し


def up_grid(objs, step=0.05):
    """Unity 局所の上向きの面(法線 y > 0.7)の最高を格子 {(i, j): Y} に刷る(i = X / step, j = Z / step)"""
    G = {}
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.data
        me.calc_loop_triangles()
        mw = o.matrix_world
        W = [mw @ v.co for v in me.vertices]
        for t in me.loop_triangles:
            a, b, c = (W[k] for k in t.vertices)
            n = (b - a).cross(c - a)
            if n.length < 1e-12 or n.z / n.length <= 0.7:        # Blender +Z = Unity +Y
                continue
            A, B, C = ((-p.x, -p.y, p.z) for p in (a, b, c))       # (Unity X, Unity Z, Unity Y)
            i0, i1 = math.floor(min(A[0], B[0], C[0]) / step), math.floor(max(A[0], B[0], C[0]) / step)
            j0, j1 = math.floor(min(A[1], B[1], C[1]) / step), math.floor(max(A[1], B[1], C[1]) / step)
            den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
            if abs(den) < 1e-14:
                continue
            for i in range(i0, i1 + 1):
                x = (i + 0.5) * step
                for j in range(j0, j1 + 1):
                    z = (j + 0.5) * step
                    l1 = ((B[1] - C[1]) * (x - C[0]) + (C[0] - B[0]) * (z - C[1])) / den
                    l2 = ((C[1] - A[1]) * (x - C[0]) + (A[0] - C[0]) * (z - C[1])) / den
                    l3 = 1 - l1 - l2
                    if l1 < -1e-9 or l2 < -1e-9 or l3 < -1e-9:
                        continue
                    y = l1 * A[2] + l2 * B[2] + l3 * C[2]
                    if G.get((i, j), -1e9) < y:
                        G[(i, j)] = y
    return G


FACE_ROW = 0.20      # 見え面(天端の線での面)からこれより奥 = 背の列(面の石の頭の不揃いの外)


def crest_check(objs, T, is_back, step=0.05):
    """⭕ 背の列の天端の下がり ── 上向きの面を 0.05 の格子に刷り、**背の列**(is_back(x, z))で**天端の帯**
    (周り CREST_R の円の中の最高から CREST_BAND 以内 = `EdoBuild` の篩と同じ。帯の外 = 目地に覗く下の段の石の頭は土に入るのが正しい)
    の点について 天端の線 T(x, z) − 上面 の最大(back)を、全点で 上面 − 天端の線 の最大(over = 前の頭が天端より上へ出ていないか)を返す。"""
    G = up_grid(objs, step)
    r = int(math.ceil(CREST_R / step))
    disc = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if (di * di + dj * dj) * step * step <= CREST_R ** 2]
    back, over, at, n = -1e9, -1e9, None, 0
    for (i, j), y in G.items():
        x, z = (i + 0.5) * step, (j + 0.5) * step
        t = T(x, z)
        over = max(over, y - t)
        if not is_back(x, z):
            continue
        mx = max(G.get((i + di, j + dj), -1e9) for di, dj in disc)
        if y < mx - CREST_BAND:
            continue
        n += 1
        if t - y > back:
            back, at = t - y, (round(x, 3), round(y, 3), round(z, 3))
    return back, over, at, n


def crest_spec(name):
    """FBX 名 → (天端の線 T(x, z)(Unity 局所), 背の列か is_back(x, z))"""
    import re
    m = re.match(r"Sanno_Nozura_H(\d{4})_G([+-]\d{3})_[a-d]$", name)
    if m:
        h, g = int(m.group(1)) / 1000, int(m.group(2)) / 1000
        return (lambda x, z: h + g * x), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"Sanno_Nozura_Kado90_H(\d{4})_[ab]$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: x <= -FACE_ROW and z <= -FACE_ROW)
    m = re.match(r"Sanno_Nozura_Kiri\d{3}[PM][LS]_H(\d{4})_[a-d]$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"Sanno_Nozura_Nori[PM]_L\d{4}_H(\d{4})_[a-d]$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"IshidanSodeNozuraNori_([\d.]+)_([\d.]+)_E[+-][\d.]+_[ab]$", name)
    if m:
        k, f = float(m.group(1)), float(m.group(2))
        return (lambda x, z: SODE_HT + (f / 2 - z) * k / f), (lambda x, z: abs(x) <= SODE_HALF - FACE_ROW)
    m = re.match(r"Sanno_Nozura_Mikiri_H(\d{4})$", name)
    if m:
        h = int(m.group(1)) / 1000
        return (lambda x, z: h), (lambda x, z: z <= -FACE_ROW)
    m = re.match(r"IshidanSodeNozura_([\d.]+)_([\d.]+)_[ab]$", name)
    if m:
        k, f = float(m.group(1)), float(m.group(2))
        # 袖は両面が見え面 ⇒ 両面の奥の芯(|X| ≤ 0.30 − 0.20)を背の列と読む
        return (lambda x, z: SODE_HT + (f / 2 - z) * k / f), (lambda x, z: abs(x) <= SODE_HALF - FACE_ROW)
    return None


def crest_all(dirs):
    """焼いた FBX を読み戻して全駒を測る(= Unity が読む物)。表を刷り、json を scratchpad へ"""
    import glob, json
    rows = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.fbx"))):
            name = os.path.splitext(os.path.basename(path))[0]
            sp = crest_spec(name)
            if sp is None:
                continue
            V.reset()
            before = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=path)
            objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
            bpy.context.view_layer.update()
            back, over, at, n = crest_check(objs, *sp)
            rows.append(dict(name=name, back=round(back, 4), over=round(over, 4), at=at, n=n))
            print("NOZURA CREST %-34s 背の下がり %+.3f 頭の出 %+.3f 点 %d 最悪 %s %s" % (
                name, back, over, n, at, "⭕" if back <= CREST_TOL and over <= 0.005 else "⛔"))
    bad = [r for r in rows if r["back"] > CREST_TOL or r["over"] > 0.005]
    print("NOZURA CREST 全 %d 駒: 背の下がりの最大 %+.3f / 頭の出の最大 %+.3f / ⛔ %d" % (
        len(rows), max(r["back"] for r in rows), max(r["over"] for r in rows), len(bad)))
    out = OPT.get("json")
    if out:
        json.dump(rows, open(out, "w"), ensure_ascii=False, indent=1)
    return len(bad)


# ------------------------------------------------------------------ 天端の穴の検査(2026-09-26 EDO-0437)
HOLE_STEP = 0.01     # 真上からの光線の格子
HOLE_NZ = -0.05      # 最初に当たった面の法線の上向き成分がこれ未満 = 裏(Unity は裏面を描かない ⇒ 抜けて下が見える)
HOLE_DEEP = 0.25     # 天端の線から これより深い所に当たる(または何にも当たらない)= 下が見える(目地の底の板は 0.20)
HOLE_ENC = 0.25      # 深い点は ±X・±Z の 4 方向とも この距離の内に天端の帯(天端の線の 0.10 内)の面がある時だけ穴と読む
#                      (奥の端の外・前の頭の不揃いの前・端の外は穴でない)
HOLE_CORE = 2        # 穴と数える塊 = 一辺 (2·HOLE_CORE+1)·step = 0.05 の正方形が丸ごと入る塊 ── 目地(幅 0.02〜0.04・奥 0.76 より奥は
#                      底の板が無く下まで覗くが、それは目地であって石の欠けではない)と稜の掠りは数えない


def hole_check(objs, T, step=HOLE_STEP):
    """⭕ 真上から見て天端の面に穴が無いか ── 駒の平面の外形の格子で真上から光線を落とし、
    ① 最初に当たる面が裏(法線が下を向く = Unity で抜ける)② 天端の周りを石に囲まれているのに深く落ちる(下の段・地面が覗く)
    の点を刷り、隣り合う点を塊にして、一辺 0.05 の正方形が丸ごと入る塊を穴と数える(目地は数えない)。返り値 (穴の数, 裏の点, 深い点, 穴の一覧[(x, z, 点の数, 種)])"""
    from mathutils.bvhtree import BVHTree
    verts, polys = [], []
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.data
        me.calc_loop_triangles()
        b = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        polys += [tuple(b + k for k in t.vertices) for t in me.loop_triangles]
    bvh = BVHTree.FromPolygons(verts, polys)
    xs = [-v.x for v in verts]; zs = [-v.y for v in verts]; top = max(v.z for v in verts)
    i0, i1 = math.floor(min(xs) / step) + 1, math.floor(max(xs) / step) - 1
    j0, j1 = math.floor(min(zs) / step) + 1, math.floor(max(zs) / step) - 1
    hit = {}
    for i in range(i0, i1 + 1):
        x = i * step
        for j in range(j0, j1 + 1):
            z = j * step
            loc, nor, _, _ = bvh.ray_cast(Vector((-x, -z, top + 1.0)), Vector((0, 0, -1)))
            hit[(i, j)] = None if loc is None else (loc.z, nor.z)
    bad = {}
    r = int(round(HOLE_ENC / step))
    for (i, j), hv in hit.items():
        x, z = i * step, j * step
        t = T(x, z)
        if hv is not None and hv[1] < HOLE_NZ:
            bad[(i, j)] = "裏"
            continue
        if hv is not None and hv[0] >= t - HOLE_DEEP:
            continue

        def band(di, dj):
            for k in range(1, r + 1):
                q = hit.get((i + di * k, j + dj * k))
                if q is not None and q[1] >= HOLE_NZ and q[0] >= T((i + di * k) * step, (j + dj * k) * step) - 0.10:
                    return True
            return False
        if band(1, 0) and band(-1, 0) and band(0, 1) and band(0, -1):
            bad[(i, j)] = "深"
    seen, holes = set(), []
    for p in bad:
        if p in seen:
            continue
        st, cc = [p], []
        seen.add(p)
        while st:
            q = st.pop(); cc.append(q)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    w = (q[0] + di, q[1] + dj)
                    if w in bad and w not in seen:
                        seen.add(w); st.append(w)
        cr = HOLE_CORE
        core = [q for q in cc if all((q[0] + di, q[1] + dj) in bad for di in range(-cr, cr + 1) for dj in range(-cr, cr + 1))]
        if core:
            holes.append((round(sum(q[0] for q in cc) * step / len(cc), 3), round(sum(q[1] for q in cc) * step / len(cc), 3),
                          len(cc), "".join(sorted({bad[q] for q in cc}))))
    nb = sum(1 for v in bad.values() if v == "裏"); nd = len(bad) - nb
    return len(holes), nb, nd, holes


def holes_all(dirs):
    """焼いた FBX を読み戻して全駒の天端の穴を数える(crest と同じ名簿 = crest_spec が読める駒)"""
    import glob, json
    rows = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.fbx"))):
            name = os.path.splitext(os.path.basename(path))[0]
            sp = crest_spec(name)
            if sp is None:
                continue
            V.reset()
            before = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=path)
            objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
            bpy.context.view_layer.update()
            nh, nb, nd, holes = hole_check(objs, sp[0])
            rows.append(dict(name=name, holes=nh, back_pts=nb, deep_pts=nd, list=holes))
            print("NOZURA HOLES %-34s 穴 %d(裏の点 %d・深い点 %d)%s %s" % (name, nh, nb, nd, holes[:4], "⭕" if nh == 0 else "⛔"))
    bad = [r for r in rows if r["holes"]]
    print("NOZURA HOLES 全 %d 駒: 穴のある駒 %d / 穴の合計 %d" % (len(rows), len(bad), sum(r["holes"] for r in rows)))
    out = OPT.get("json")
    if out:
        json.dump(rows, open(out, "w"), ensure_ascii=False, indent=1)
    return len(bad)


def studio_run(objs, cam, look, lens=35, path=None, magenta=False):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.eevee.taa_render_samples = 48
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 0, 1, 1) if magenta else (0.62, 0.70, 0.80, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.2; sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-40))
    sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new("Cam"); cd.lens = lens; cd.clip_start = 0.05
    c = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(c); sc.camera = c
    c.location = cam
    c.rotation_euler = (Vector(look) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
    V.render(path)


def place_copy(src_fbx, x_u, y_u):
    """FBX を読み、Unity (x, y) へ置く(検証レンダ用・Blender 座標へ戻す)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=src_fbx)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type == 'MESH':
            o.location.x += -x_u
            o.location.z += y_u
    return new


def ground(z=0.0, y0=-30, y1=0.5, name="Yard", col=(0.20, 0.26, 0.12)):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(-30, y0, z), (30, y0, z), (30, y1, z), (-30, y1, z)]]
    bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs['Base Color'].default_value = col + (1,)
    bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Specular IOR Level'].default_value = 0.0
    me.materials.append(m)
    return o


def hook_stone_textures():
    """読み込んだ FBX の Kirishi / Danishi にテクスチャを結ぶ(検証レンダ用)"""
    for m in bpy.data.materials:
        base = m.name.split(".")[0]
        if base not in ("Kirishi", "Danishi"):
            continue
        m.use_nodes = True
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not b:
            continue
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Roughness'].default_value = 0.92
        m.use_backface_culling = True     # Unity と同じく裏を描かない(裏返った面が検証レンダで見えるように・2026-09-26)
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = bpy.data.images.load(os.path.join(MATDIR, "T_Kirishi_Albedo.png"), check_existing=True)
        t = 1.0 if base == "Kirishi" else 0.80
        mx = nt.nodes.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1
        nt.links.new(ti.outputs['Color'], mx.inputs[1]); mx.inputs[2].default_value = (t, t, t, 1)
        nt.links.new(mx.outputs['Color'], b.inputs['Base Color'])


def render_wall_run(tag, magenta=False):
    """⭐ 焼いた FBX を読み戻して並べる(= Unity が読む物を撮る)。
    上段: 見付 1.2 を a,b,c,d,a,b,c と 7駒(継ぎ目・繰り返し)。
    下段: 天端の線を一本(Y = 0.9 → 勾配なしで段の違う駒を沈めて継ぐ)— 0.9,1.2,1.5,2.4,0.15 …"""
    V.reset()
    seq = "abcdabc"
    x0 = -3 * L
    for i, v in enumerate(seq):
        place_copy(os.path.join(OUT_WALL, wall_name(1.20, 0.0, v) + ".fbx"), x0 + i * L, 0.0)
    hook_stone_textures()
    ground()
    # 上の地面(天端の 0.10 上・頭の後ろ)
    ground(1.25, 0.25, 12, "Upper", (0.18, 0.24, 0.11))
    studio_run([], (-4.0, -8.5, 1.5), (0.5, 0, 0.7), 28,
               os.path.join(SHOT, "sanno_nozura_run%s.png" % tag), magenta)
    # 寄り(継ぎ目 x=±L/2 の2本が入る)
    studio_run([], (-0.6, -2.4, 1.3), (0.2, 0, 0.75), 30,
               os.path.join(SHOT, "sanno_nozura_seam%s.png" % tag), magenta)


def render_tier_mix(tag):
    """① 段の違う駒を天端の線で継ぐ: 天端 Y = 0.9 一定で 0.9/1.2/2.4/1.5/0.9 を沈めて並べる。
    ② 打ち切り: 天端 0.30 の駒の両端に根石の打ち切り(G±180)を継ぐ。"""
    V.reset()
    top = 0.9
    seq = [(0.90, "a"), (1.20, "b"), (2.40, "c"), (1.50, "d"), (0.90, "a")]
    x0 = -2 * L
    for i, (h, v) in enumerate(seq):
        place_copy(os.path.join(OUT_WALL, wall_name(h, 0, v) + ".fbx"), x0 + i * L, top - h)
    hook_stone_textures()
    ground()
    ground(top + 0.06, 0.45, 12, "Upper", (0.18, 0.24, 0.11))
    studio_run([], (-1.5, -6.0, 1.5), (0.0, 0, 0.55), 26, os.path.join(SHOT, "sanno_nozura_tiers%s.png" % tag))

    V.reset()
    top = 0.30
    xk = -2 * L
    # 左の打ち切り(+X へ上がる): 右端(s=+L/2)の天端を 0.30 に ⇒ 中心の天端 = 0.30 − 0.909·G
    items = [(wall_name(0.15, KIRI_G, "a"), top - 0.909 * KIRI_G - 0.15),
             (wall_name(0.30, 0, "b"), 0.0), (wall_name(0.30, 0, "c"), 0.0), (wall_name(0.30, 0, "d"), 0.0),
             (wall_name(0.15, -KIRI_G, "a"), top - 0.909 * KIRI_G - 0.15)]
    for i, (nm, y) in enumerate(items):
        place_copy(os.path.join(OUT_WALL, nm + ".fbx"), xk + i * L, y)
    hook_stone_textures()
    ground()
    studio_run([], (-0.5, -8.0, 1.5), (0.0, 0, 0.1), 26, os.path.join(SHOT, "sanno_nozura_kiri%s.png" % tag))


def render_sode(keri, fumi, name_tag, n=8):
    """袖の駒を段ごとに i%2 で並べ(天端が勾配の一直線に載るか)、坂の横から見る"""
    V.reset()
    for i in range(n):
        v = "a" if i % 2 == 0 else "b"
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(OUT_SODE, sode_name(keri, fumi, v) + ".fbx"))
        for o in [o for o in bpy.data.objects if o not in before and o.type == 'MESH']:
            # 段 i: Unity Z = −(i+0.5)·踏面(坂上へ)、Y = 蹴上·(i+1)
            o.location.y += (i + 0.5) * fumi
            o.location.z += keri * (i + 1)
    hook_stone_textures()
    ground(0.0, -30, 30)
    run = n * fumi
    studio_run([], (4.5, run * 0.5 - 1.0, 1.6 + keri * n * 0.5), (0, run * 0.5, keri * n * 0.55), 30,
               os.path.join(SHOT, "sanno_nozura_sode_%s.png" % name_tag))


def render_mikiri():
    V.reset()
    place_copy(os.path.join(OUT_WALL, "Sanno_Nozura_Mikiri.fbx"), 0.0, 0.0)
    place_copy(os.path.join(OUT_WALL, wall_name(0.60, 0, "a") + ".fbx"), -(L / 2 + 0.43), 0.0)
    hook_stone_textures()
    ground()
    studio_run([], (-0.8, -3.0, 1.4), (-0.4, 0, 0.35), 35, os.path.join(SHOT, "sanno_nozura_mikiri.png"))


def _import_at(path, x_u, z_u, y_u, yaw_u=0.0):
    """FBX を読み、Unity の yaw(度・+Z→+X が +90)で回して Unity (x, y, z) へ置く(検証レンダ用)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    R = mathutils.Matrix.Rotation(math.radians(-yaw_u), 4, 'Z')
    T = mathutils.Matrix.Translation(Vector(_u2b(x_u, y_u, z_u)))
    for o in new:
        o.matrix_world = T @ R @ o.matrix_world
    return new


def render_kado(h=1.50, tag=""):
    """隅の駒を直線の駒で挟んで撮る: 腕1 の先に直線 2駒(見え面 +Z)、腕2 の先に直線 2駒(yaw 90・見え面 +X)。
    隅の外(+X +Z)の低い地面と、帯(X ≤ 0・Z ≤ 0)の上の地面。"""
    for v in KADO_VARIANTS:
        V.reset()
        _import_at(os.path.join(OUT_WALL, kado_name(h, v) + ".fbx"), 0, 0, 0)
        for i, wv in enumerate("ab"):
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, wv) + ".fbx"), -L * (i + 1), 0, 0)
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "cd"[i]) + ".fbx"), 0, -L * (i + 1), 0, 90.0)
        hook_stone_textures()
        ground()
        # 帯の上(天端 + 0.06・X ≤ 0 かつ Z ≤ 0 ⇔ Blender X ≥ 0 かつ Y ≥ 0)
        bm = bmesh.new()
        vs = [bm.verts.new(q) for q in [(0.05, 0.05, h + 0.06), (12, 0.05, h + 0.06), (12, 12, h + 0.06), (0.05, 12, h + 0.06)]]
        bm.faces.new(vs); me = bpy.data.meshes.new("Upper"); bm.to_mesh(me); bm.free()
        ou = bpy.data.objects.new("Upper", me); bpy.context.scene.collection.objects.link(ou)
        mu = bpy.data.materials.new("Upper"); mu.use_nodes = True
        mu.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.18, 0.24, 0.11, 1)
        me.materials.append(mu)
        # 隅の外(対角)から
        studio_run([], _u2b(4.2, 1.7, 4.2), _u2b(-0.6, h * 0.5, -0.6), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s%s.png" % (v, tag)))
        studio_run([], _u2b(4.2, 1.7, 4.2), _u2b(-0.6, h * 0.5, -0.6), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s_magenta%s.png" % (v, tag)), magenta=True)
        # 腕1 の継ぎ目の寄り
        studio_run([], _u2b(-0.4, 1.2, 2.6), _u2b(-0.9, h * 0.5, 0), 30,
                   os.path.join(SHOT, "sanno_nozura_kado_%s_seam%s.png" % (v, tag)))
        # 真上から(平面の留め)── 帯の地面を消す
        bpy.data.objects.remove(ou)
        sc = bpy.context.scene
        cam = sc.camera
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = 5.0
        cam.location = _u2b(-0.8, 8.0, -0.8); cam.rotation_euler = (0, 0, 0)
        V.render(os.path.join(SHOT, "sanno_nozura_kado_%s_plan%s.png" % (v, tag)))


def _flat_box(name, corners_u, col):
    """Unity の 8 隅(下 4 → 上 4・同じ回り)で箱を張る(検証レンダの相手役・書き出さない)"""
    bm = bmesh.new()
    vs = [bm.verts.new(_u2b(*c)) for c in corners_u]
    for f in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = col + (1,)
    me.materials.append(m)
    return o


def _upper_ground(h, xr, zr, name="Upper"):
    bm = bmesh.new()
    vs = [bm.verts.new(_u2b(x, h + 0.04, z)) for x, z in ((xr[0], zr[0]), (xr[1], zr[0]), (xr[1], zr[1]), (xr[0], zr[1]))]
    bm.faces.new(vs); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.18, 0.24, 0.11, 1)
    me.materials.append(m)
    return o


def render_nkiri(h, deg, end, face, v):
    """斜めに切った端の駒 + 直線の駒 2 を継ぎ、切る面に袖の外面の役の箱(灰)を当てて撮る"""
    co, no, e, k, cot = nkiri_plane(deg, end, face)
    V.reset()
    _import_at(os.path.join(OUT_WALL, nkiri_name(deg, end, face, h, v) + ".fbx"), 0, 0, 0)
    for i, wv in enumerate("cd"):
        _import_at(os.path.join(OUT_WALL, wall_name(h, 0, wv) + ".fbx"), -e * L * (i + 1), 0, 0)
    hook_stone_textures()
    ground(0.0, -30, 30)
    # 袖の外面の役: 切る面 x = e·L/2 + e·k·cot·z の外側 0.6
    nx, nz = e, -k * cot; ln = math.hypot(nx, nz); nx, nz = nx / ln, nz / ln
    tx, tz = e * k * cot, 1.0; lt = math.hypot(tx, tz); tx, tz = tx / lt, tz / lt
    pts = []
    for yy in (-0.3, h + 0.3):
        for a, b in ((-2.6, 0.0), (1.6, 0.0), (1.6, 0.6), (-2.6, 0.6)):
            pts.append((e * L / 2 + tx * a + nx * b, yy, tz * a + nz * b))
    _flat_box("Sode", pts, (0.55, 0.55, 0.52))
    # 背の地面(天端の高さ・駒の奥 Z ≤ −0.2)
    _upper_ground(h, (-4 * L, 3.0) if e > 0 else (-3.0, 4 * L), (-6.0, -0.25))
    tag = nkiri_name(deg, end, face, h, v)
    studio_run([], _u2b(-e * 1.5, h + 1.2, 4.6), _u2b(e * 0.6, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(e * 1.8, h * 0.5 + 0.4, 2.4), _u2b(e * 0.8, h * 0.45, 0.0), 30, os.path.join(SHOT, tag + "_near.png"))
    studio_run([], _u2b(-e * 1.5, h + 1.2, 4.6), _u2b(e * 0.6, h * 0.5, 0.2), 30, os.path.join(SHOT, tag + "_magenta.png"), magenta=True)
    # 真上から(袖の箱と背の地面を消して、切り口が面に沿うか)
    for nm in ("Sode", "Upper"):
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob)
    cam = bpy.context.scene.camera
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 4.5
    cam.location = _u2b(e * 0.4, 10.0, 0.0); cam.rotation_euler = (0, 0, 0)
    V.render(os.path.join(SHOT, tag + "_plan.png"))


def render_mikiri_h(h):
    """丈を合わせた見切り石: −X に同じ見付の野面の駒 2、+X に城の石垣の役の箱(灰)・背の地面は天端の高さ"""
    V.reset()
    _import_at(os.path.join(OUT_WALL, mikiri_name(h) + ".fbx"), 0, 0, 0)
    for i, wv in enumerate("ab"):
        _import_at(os.path.join(OUT_WALL, wall_name(h, 0, wv) + ".fbx"), -(MIKIRI_W / 2 + L / 2 + i * L), 0, 0)
    hook_stone_textures()
    ground(0.0, -30, 30)
    xb = MIKIRI_W / 2
    _flat_box("Castle", [(xb, -0.3, 1.2), (xb + 3, -0.3, 1.2), (xb + 3, -0.3, -2.0), (xb, -0.3, -2.0),
                         (xb, h, 0.3 * 0.0), (xb + 3, h, 0.0), (xb + 3, h, -2.0), (xb, h, -2.0)], (0.55, 0.55, 0.52))
    _upper_ground(h, (-3 * L, xb), (-6.0, -0.25))
    tag = mikiri_name(h)
    studio_run([], _u2b(-0.4, h * 0.6 + 0.6, 4.2), _u2b(-0.5, h * 0.5, 0), 32, os.path.join(SHOT, tag + ".png"))
    studio_run([], _u2b(-2.2, h + 1.6, 2.4), _u2b(-0.2, h * 0.7, -0.3), 32, os.path.join(SHOT, tag + "_top.png"))


def render_dan(g=0.22, h=1.50):
    """段の境: 天端 T の直線 H1.50 → 勾配の駒(1間で 0.40 下がる)→ 天端 T − 0.40 の直線 H1.20。床は Y=0 の地面に沈める。"""
    V.reset()
    T = 1.35
    items = [(wall_name(1.50, 0, "a"), -L, T - 1.50),
             (wall_name(h, -g, "b"), 0.0, T - 0.909 * g - h),
             (wall_name(1.20, 0, "c"), L, T - 2 * 0.909 * g - 1.20),
             (wall_name(1.20, 0, "d"), 2 * L, T - 2 * 0.909 * g - 1.20)]
    for nm, x, y in items:
        place_copy(os.path.join(OUT_WALL, nm + ".fbx"), x, y)
    hook_stone_textures()
    ground()
    studio_run([], (-0.6, -5.5, 1.3), (-0.6, 0, 0.8), 30, os.path.join(SHOT, "sanno_nozura_dan.png"))
    studio_run([], (-0.6, -5.5, 1.3), (-0.6, 0, 0.8), 30, os.path.join(SHOT, "sanno_nozura_dan_magenta.png"), magenta=True)


def render_grade(g=0.12, h=0.90):
    """勾配の駒の並べ焼き(2026-09-26 EDO-0437): 天端の線が 平(H h)→ −g で 3間下がる → 平 と折れる所。
    勾配の駒は中心の天端を線に載せ、隣と切り口の天端を揃える(見付は据えた床の側で沈める)。床は Y=0 の地面に沈める。"""
    V.reset()
    T = h + 0.1
    seq = [(0.0, "a"), (-g, "b"), (-g, "c"), (-g, "d"), (0.0, "a")]
    x = -2 * L; top = T
    for gg, v in seq:
        c = top + gg * L / 2              # 中心の天端
        place_copy(os.path.join(OUT_WALL, wall_name(h, gg, v) + ".fbx"), x, c - h)
        top = top + gg * L; x += L
    hook_stone_textures()
    ground()
    studio_run([], (0.0, -7.5, 1.4), (0.0, 0, 0.6), 30, os.path.join(SHOT, "sanno_nozura_grade_%03d_H%04d.png" % (int(round(g * 1000)), int(round(h * 1000)))))
    studio_run([], (0.0, -7.5, 1.4), (0.0, 0, 0.6), 30,
               os.path.join(SHOT, "sanno_nozura_grade_%03d_H%04d_magenta.png" % (int(round(g * 1000)), int(round(h * 1000)))), magenta=True)
    # 寄り: 平 → 勾配の折れの継ぎ目(x = −1.5L)
    studio_run([], (-1.5 * L + 0.3, -2.6, T + 0.2), (-1.5 * L, 0, T - 0.3), 30,
               os.path.join(SHOT, "sanno_nozura_grade_%03d_H%04d_seam.png" % (int(round(g * 1000)), int(round(h * 1000)))))


def render_back(h=1.20):
    """背の側(土の側)から撮る(2026-09-25 EDO-0430): 直線 a〜d・勾配の駒・隅の駒を並べ、
    ① 土を 2cm 下げて(天端 − 0.02)── 背の天端に届かない石は土の下へ消え、帯に緑の穴が開く
    ② 土なし・マゼンタの背景 ── 背の上面の形"""
    for soil, tag in ((True, ""), (False, "_nosoil")):
        V.reset()
        for i, v in enumerate("abcd"):
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, v) + ".fbx"), -L * (i + 1), 0, 0)
        _import_at(os.path.join(OUT_WALL, kado_name(h, "a") + ".fbx"), 0, 0, 0)
        _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "b") + ".fbx"), 0, -L, 0, 90.0)
        hook_stone_textures()
        ground()
        if soil:
            bm = bmesh.new()
            vs = [bm.verts.new(q) for q in [(-0.3, 0.05, h - 0.02), (12, 0.05, h - 0.02), (12, 12, h - 0.02), (-0.3, 12, h - 0.02)]]
            bm.faces.new(vs); me = bpy.data.meshes.new("Soil"); bm.to_mesh(me); bm.free()
            ou = bpy.data.objects.new("Soil", me); bpy.context.scene.collection.objects.link(ou)
            mu = bpy.data.materials.new("Soil"); mu.use_nodes = True
            mu.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.10, 0.45, 0.08, 1)
            me.materials.append(mu)
        # 背の奥(Unity −Z)の高い所から、天端の帯を見下ろす
        studio_run([], _u2b(-4.5, h + 2.2, -4.0), _u2b(-3.0, h, -0.3), 30,
                   os.path.join(SHOT, "sanno_nozura_back%s.png" % tag), magenta=not soil)
        # 前から(見え面の頭の不揃い・目の高さ)
        if soil:
            studio_run([], _u2b(-3.5, 1.5, 4.5), _u2b(-3.0, h * 0.6, 0), 30,
                       os.path.join(SHOT, "sanno_nozura_front.png"))


def render_top(h=1.20):
    """天端を真上から(2026-09-26 EDO-0437): 直線 a〜c・隅の駒 a・腕2 の先の直線 d。「表の石の列 + 裏石の列」の 2 列に見えるか。
    ① 正射影・空の背景 ② 正射影・マゼンタ(目地から下へ空が抜けないか)③ 斜め上から(前の頭の不揃いと裏石)"""
    for magenta, tag in ((False, ""), (True, "_magenta")):
        V.reset()
        for i, v in enumerate("abc"):
            _import_at(os.path.join(OUT_WALL, wall_name(h, 0, v) + ".fbx"), -L * (i + 1), 0, 0)
        _import_at(os.path.join(OUT_WALL, kado_name(h, "a") + ".fbx"), 0, 0, 0)
        _import_at(os.path.join(OUT_WALL, wall_name(h, 0, "d") + ".fbx"), 0, -L, 0, 90.0)
        hook_stone_textures()
        if not magenta:
            ground()
        studio_run([], _u2b(-2.2, h + 1.6, 2.2), _u2b(-2.2, h, -0.4), 30,
                   os.path.join(SHOT, "sanno_nozura_top_oblique%s.png" % tag), magenta)
        cam = bpy.context.scene.camera
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = 4.4
        cam.location = _u2b(-2.0, h + 8.0, -0.9); cam.rotation_euler = (0, 0, 0)
        V.render(os.path.join(SHOT, "sanno_nozura_top%s.png" % tag))
        cam.data.ortho_scale = 2.0
        cam.location = _u2b(-0.8, h + 8.0, -0.8)
        V.render(os.path.join(SHOT, "sanno_nozura_top_kado%s.png" % tag))


# ------------------------------------------------------------------ 本体
def do_kado():
    hs = [float(OPT["h"])] if OPT.get("h") else KADO_TIERS
    for h in hs:
        for v in KADO_VARIANTS:
            o, name = make_kado(h, v)
            export(o, name, OUT_WALL)


# 前庭の縁の天端を流す勾配の駒(2026-09-26 EDO-0437)── 天端の勾配 0.03〜0.18 の区間(TW_Zentei_W / SE / E)。
#   勾配の段は 0 と ±0.12 の二つで足りる: 1間(伸縮 1.2 まで)の端で 天端の線 − 駒の天端 ≤ 0.065(裁定の頭の不揃い ±0.08 の内)。
#   0.15 は打ち切りの ±0.18・1.50 は段の境の ±0.22 も在る(`Own.SannoNozura` が最も近い勾配を引く)。1.80 は前庭の勾配の区間に無い。
GRADE_SET = [0.12, -0.12]
GRADE_TIERS = [0.15, 0.30, 0.60, 0.90, 1.20, 1.50, 2.10, 2.40]


def _floats(key, default):
    return [float(x) for x in OPT[key].split(",")] if OPT.get(key) else default


def do_wall():
    # --grade=0.12,-0.12 / --h=0.3,0.6 はカンマで並べられる。--grade=set は GRADE_SET × GRADE_TIERS
    if OPT.get("grade") == "set":
        grades, hs = GRADE_SET, (_floats("h", GRADE_TIERS))
    else:
        grades = _floats("grade", [0.0])
        hs = _floats("h", TIERS)
    for g in grades:
        for h in hs:
            for v in VARIANTS:
                o, name, n = make_wall(h, g, v)
                export(o, name, OUT_WALL)


def do_kiri():
    for g in (KIRI_G, -KIRI_G):
        for v in VARIANTS:
            o, name, n = make_wall(0.15, g, v)
            export(o, name, OUT_WALL)


def do_sode():
    import build_sanno_buzai as SB
    for nm, keri, fumi, w in SB.kaidan_specs(OPT.get("only") or None):
        # ⭐ 袖が焼けている石段(= 旧 `IshidanSode_<蹴上>_<踏面>_a` がある組)だけ差し替える
        old = os.path.join(OUT_SODE, "IshidanSode_%.3f_%.3f_a.fbx" % (keri, fumi))
        if not os.path.exists(old) and not OPT.get("only"):
            continue
        for v in "ab":
            o, name, n = make_sode(keri, fumi, v)
            export(o, name, OUT_SODE)
        if RENDER:
            render_sode(keri, fumi, nm)


def do_mikiri():
    o, name = make_mikiri()
    export(o, name, OUT_WALL)



# ------------------------------------------------------------------ 積み止めの駒(2026-10-07 EDO-0502)
# 岡部 nozuraEndRule 追記 2026-10-07b・TW_Minami_Koshi.returnEnd(H1200)・TW_Nishi_Kado.endKado(H2400)。②②'①が取れない端を
# 直線の駒の小口(継ぎ目の切り口)で終えず、「小口の面にも面石を積み、両角を隅の稜にした端の駒」で終える。
# `Sanno_Nozura_H<見付mm>_Tome<P|M>_<a|b>`。P = 端(小口の面)が局所 +X・継ぎ手が −X / M = 端が −X・継ぎ手が +X。
#   作り: 出隅 90° の隅の駒(make_kado)を二つ、小口の面で腕を突き合わせる ── 前の角 = 隅の駒(見え面 +Z と小口の面)、
#   奥の角 = 隅の駒を回した物(小口の面と背の面 −Z)。二つの腕の先はどちらも直線の駒の切り口と同じ形 ⇒ 小口の面の中の継ぎ目は
#   直線の駒どうしの継ぎ目と同じく一石に合わさる(竪目地を通さない)。両角の石は隅の駒の稜の石(行ごとに稜に跨る石・算木にしない)。
#   ⇒ 走り(天端の線)0.909 = 半間・小口の面の奥行(天端の線)1.818。前の角の稜 = 天端の線の端。
#   前の角の個体 = v、奥の角の個体 = もう一方(a↔b)。
#   ピボット = **前の角の稜(見え面の天端の線と小口の面の天端の線の交点)・床レベル(天端 − 見付)** ── 隅の駒と同じ取り方。
#   継ぎ手の切り口は P で X = −0.909・M で X = +0.909(G0 の駒の切り口と同じ)。天端 Y = 見付(G0 と同じ高さ)。
TOME_TIERS = [0.60, 1.20, 2.40]


def tome_name(h, hand, v):
    return "Sanno_Nozura_H%04d_Tome%s_%s" % (int(round(h * 1000)), hand, v)


def _snap(o):
    me = o.data
    uv = me.uv_layers.active
    return dict(co=[o.matrix_world @ vt.co for vt in me.vertices],
                faces=[(tuple(p.vertices), p.material_index, p.use_smooth, [tuple(uv.data[li].uv) for li in p.loop_indices])
                       for p in me.polygons],
                mats=[m.name.split(".")[0] for m in me.materials], uvname=uv.name)


def _unsnap(sn, name, yaw_u, pos_u):
    """_snap した隅の駒を Unity の yaw(+Z→+X が +90)で回し、Unity pos_u へ置いて起こし直す"""
    M = mathutils.Matrix.Translation(Vector(_u2b(*pos_u))) @ mathutils.Matrix.Rotation(math.radians(-yaw_u), 4, 'Z')
    md = dict(zip(("Kirishi", "Danishi"), materials()))
    me = bpy.data.meshes.new(name)
    me.from_pydata([M @ c for c in sn["co"]], [], [f[0] for f in sn["faces"]])
    for nm in sn["mats"]:
        me.materials.append(md[nm])
    uvl = me.uv_layers.new(name=sn["uvname"])
    for p, (_, mi, sm, uvs) in zip(me.polygons, sn["faces"]):
        p.material_index = mi
        p.use_smooth = sm
        for li, u in zip(p.loop_indices, uvs):
            uvl.data[li].uv = u
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


TOME_YAW = {"P": ((0.0, (0, 0, 0)), (90.0, (0, 0, -L))), "M": ((-90.0, (0, 0, 0)), (180.0, (0, 0, -L)))}


def make_tome(h, hand, v):
    w = "b" if v == "a" else "a"
    snaps = []
    for vv in (v, w):
        o, _ = make_kado(h, vv)
        snaps.append(_snap(o))
    V.reset()
    materials()
    (y1, p1), (y2, p2) = TOME_YAW[hand]
    objs = [_unsnap(snaps[0], "front", y1, p1), _unsnap(snaps[1], "rear", y2, p2)]
    name = tome_name(h, hand, v)
    o = V.join(objs, name)
    nd = clean_degenerate(o)
    V.set_origin(o, (0, 0, 0))
    print("TOME %s 面積 0・辺 < 0.1mm の三角形 %d" % (name, nd))
    return o, name


def tome_rays(o, h, hand, step=0.01):
    """表から当てた光線(真上・見え面 +Z の前・小口の面の前・背 −Z の前)のうち最初に裏の面に当たる本数(方向ごと)"""
    from mathutils.bvhtree import BVHTree
    me = o.data
    bvh = BVHTree.FromPolygons([o.matrix_world @ vt.co for vt in me.vertices], [tuple(p.vertices) for p in me.polygons])
    e = 1 if hand == "P" else -1
    xs = [e * (-L / 2 - 0.05 + step * (i + 0.5)) for i in range(int((L / 2 + 0.6) / step))]      # 継ぎ手から端の外まで
    zs = [0.6 - step * (i + 0.5) for i in range(int((L + 1.4) / step))]                          # 前の外から背の外まで
    ys = [step * (k + 0.5) for k in range(int(h / step))]
    dirs = {"上": [((x, h + 0.5, z), (0, -1, 0)) for x in xs for z in zs],
            "前": [((x, y, 3.0), (0, 0, -1)) for x in xs for y in ys],
            "小口": [((e * 3.0, y, z), (-e, 0, 0)) for z in zs for y in ys],
            "背": [((x, y, -L - 3.0), (0, 0, 1)) for x in xs for y in ys]}
    res = {}
    for k, rays in dirs.items():
        bad, ex = 0, []
        for pu, du in rays:
            d_ = Vector(_u2b(*du))
            hit = bvh.ray_cast(Vector(_u2b(*pu)), d_, 8.0)
            if hit[0] is not None and hit[1].dot(d_) > 0.0:
                bad += 1
                if len(ex) < 4:
                    ex.append(tuple(round(c, 3) for c in _b2u(hit[0])))
        res[k] = (bad, len(rays), ex)
    return res


def render_tome(h, hand, v, g0dir):
    """積み止めの駒の継ぎ手に G0 の直線の駒を 2 駒継いで撮る。背の土は継いだ直線の駒の後ろだけ(端の小口と奥の角は見せる)。"""
    e = 1 if hand == "P" else -1
    V.reset()
    _import_at(os.path.join(STAGE_TOME, tome_name(h, hand, v) + ".fbx"), 0, 0, 0)
    for i, wv in enumerate("ab"):
        _import_at(os.path.join(g0dir, wall_name(h, 0, wv) + ".fbx"), -e * (L / 2 + L / 2 + L * i), 0, 0)
    hook_stone_textures()
    ground()
    ground(0.0, 0.5, 12, "Rear", (0.20, 0.26, 0.12))
    tag = "%s_%s_H%04d" % (hand, v, int(round(h * 1000)))
    mid = h * 0.5
    shots = [("diag", (e * 4.6, h * 0.8 + 1.0, 4.4), (e * -0.4, mid, -0.6)),
             ("end", (e * 5.0, h * 0.6 + 0.6, -0.9), (0.0, mid, -0.9)),
             ("rear", (e * 3.6, h + 2.2, -L - 3.6), (e * -0.2, mid, -1.0)),
             ("seam", (e * -0.9, mid + 0.4, 2.6), (e * -0.9, mid, 0.0))]
    for nm, cam, look in shots:
        studio_run([], _u2b(*cam), _u2b(*look), 30, os.path.join(SHOT, "sanno_nozura_tome_%s_%s.png" % (tag, nm)))
    studio_run([], _u2b(*shots[0][1]), _u2b(*shots[0][2]), 30,
               os.path.join(SHOT, "sanno_nozura_tome_%s_diag_magenta.png" % tag), magenta=True)
    sc = bpy.context.scene
    cam = sc.camera
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.70, 0.80, 1)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 5.5
    cam.location = _u2b(e * -0.8, 8.0, -1.0); cam.rotation_euler = (0, 0, 0)
    V.render(os.path.join(SHOT, "sanno_nozura_tome_%s_plan.png" % tag))


STAGE_TOME = OUT_WALL


def do_tome():
    import json
    hs = _floats("h", TOME_TIERS)
    hands = (OPT.get("hand") or "P,M").split(",")
    rows = []
    for h in hs:
        for hand in hands:
            for v in KADO_VARIANTS:
                o, name = make_tome(h, hand, v)
                rays = tome_rays(o, h, hand)
                nh, nb, nd, holes = hole_check([o], lambda x, z, h=h: h)
                bx = unity_bounds(o)
                print("TOME %s 裏に当たる光線 %s 穴 %d(裏の点 %d・深い点 %d)%s bounds %s" % (
                    name, {k: r[:2] for k, r in rays.items()}, nh, nb, nd, holes[:3], [tuple(round(c, 3) for c in b) for b in bx]))
                rows.append(dict(name=name, rays={k: r[0] for k, r in rays.items()}, ray_ex={k: r[2] for k, r in rays.items()},
                                 holes=nh, hole_list=holes, bounds=bx, tris=tris(o)))
                export(o, name, OUT_WALL)
    if OPT.get("json"):
        json.dump(rows, open(OPT["json"], "w"), ensure_ascii=False, indent=1, default=str)
    if RENDER:
        g0 = os.path.join(V.REPO, "Assets", "Edo", "Models", "Sanno")
        for h in hs:
            for hand in hands:
                render_tome(h, hand, "a", g0)
    return sum(1 for r in rows if r["holes"] or any(r["rays"].values()))


if __name__ == "__main__":
    what = POS[0] if POS else "all"
    if what == "check":
        sys.exit(1 if check() else 0)
    if what == "crest":
        # blender ... -- crest [--dir=<FBX の置き場>] [--json=<出力>] ── 全駒の背の天端の下がり(≤ 0.03)と頭の出(≤ 0)
        sys.exit(1 if crest_all([OPT["dir"]] if OPT.get("dir") else [OUT_WALL, OUT_SODE]) else 0)
    if what == "holes":
        # blender ... -- holes [--dir=<FBX の置き場>] [--json=<出力>] ── 全駒を真上から見て天端の面に穴(裏・下が見える所)が無いか
        sys.exit(1 if holes_all([OPT["dir"]] if OPT.get("dir") else [OUT_WALL, OUT_SODE]) else 0)
    if what == "kado-check":
        sys.exit(1 if check_kado(float(OPT.get("h") or 1.5)) else 0)
    if what == "kado":
        do_kado()
        if RENDER:
            render_kado(float(OPT.get("h") or 1.5))
    if what == "tome":
        # blender ... -- tome [--h=0.6,1.2,2.4] [--hand=P,M] [--json=…] [--render] ── 積み止めの駒(小口にも面石・両角が稜・EDO-0502)
        bad_ = do_tome()
        print("TOME 光線か穴の落ちた駒 %d" % bad_)
    if what == "kado_deg":
        # blender ... -- kado_deg --deg=49.4,51.8 --h=4.8 [--render] ── 出隅の折れが 90° でない隅の駒(EDO-0502)
        do_kado_deg()
    if what == "kado_cut":
        # blender ... -- kado_cut --h=0.9 --v=b --axis=x --at=0.085 [--render] ── 隅の駒の片腕を袖の背の面で一度切った版(EDO-0437)
        #   焼いた組: H0900_b cutX0.085(西 Kiri_kado2)/ H1500_b cutZ0.097(東 N_kado2)
        #   --arm=0.5 ── 切った側の腕を詰め、袖の背の側の天端を切り口まで通し、残す腕の先の継ぎ目の口を塞いだ版(r16)
        h_, v_, ax_, at_ = float(OPT["h"]), OPT.get("v") or "b", (OPT.get("axis") or "x").lower(), float(OPT["at"])
        arm_ = float(OPT.get("arm") or 0.0)
        o, name, info = make_kado_cut(h_, v_, ax_, at_, arm_)
        export(o, name, OUT_WALL)
        if OPT.get("json"):
            import json
            with open(OPT["json"], "w") as fh:
                json.dump(info, fh, ensure_ascii=False, indent=1, default=str)
        if RENDER:
            render_kado_cut(h_, v_, ax_, at_, arm_)
    if what == "kado_cap":
        # blender ... -- kado_cap --h=1.5 --v=a [--render] ── 隅の駒の両腕の先の継ぎ目の口を天端から KADO_CAP_D 塞いで焼き直す(同じ名・r16)
        h_, v_ = float(OPT["h"]), OPT.get("v") or "a"
        o, name = make_kado(h_, v_)
        r0 = kado_rays_all(o, h_)
        nc = kado_cap_end(o, h_, "x") + kado_cap_end(o, h_, "z")
        nd = clean_degenerate(o)
        r1 = kado_rays_all(o, h_)
        print("KADOCAP %s cap_faces=%d degenerate=%d rays %s -> %s" % (name, nc, nd, r0, r1))
        V.set_origin(o, (0, 0, 0))
        export(o, name, OUT_WALL)
        if RENDER:
            render_kado(h_, tag="_cap")
    if what == "back" and RENDER:
        render_back(float(OPT.get("h") or 1.2))
    if what == "top" and RENDER:
        render_top(float(OPT.get("h") or 1.2))
    if what == "dan" and RENDER:
        render_dan()
    if what == "grade" and RENDER:
        # blender ... -- grade --render [--h=0.9] ── 勾配の駒の並べ焼き(焼いてから)
        for hh in _floats("h", [0.90]):
            render_grade(abs(float(OPT.get("grade") or GRADE_SET[0])), hh)
    if what == "nkiri":
        # blender ... -- nkiri --list=Tools/Blender/sanno_nozura_kiri_set.txt [--render] ── 斜めに切った端の駒(女坂の袖に当てる)
        lp = OPT.get("list") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanno_nozura_kiri_set.txt")
        lp = lp if os.path.isabs(lp) else os.path.join(V.REPO, lp)
        bad = 0
        made = []
        for tag_, deg_, end_, face_, h_ in read_nkiri_list(lp):
            for v_ in "ab":
                ref_ = nkiri_ref_seam(h_, deg_, end_, face_, v_)
                o, name = make_nkiri(h_, deg_, end_, face_, v_)
                bad += check_nkiri(o, h_, deg_, end_, face_, v_, ref_)
                export(o, name, OUT_WALL)
                made.append((h_, deg_, end_, face_, v_))
                print("NKIRI 書き出し %s ← %s" % (name, tag_))
        if RENDER:
            for (h_, deg_, end_, face_, v_) in made:
                if v_ == "a":
                    render_nkiri(h_, deg_, end_, face_, v_)
        if bad:
            sys.exit("NKIRI ⛔ 検算が %d 件落ちた" % bad)
    if what == "nnori":
        # blender ... -- nnori --list=Tools/Blender/sanno_nozura_nori_set.txt [--render] ── 小口を相手の法で切った短い駒(入隅の可動側の端)
        lp = OPT.get("list") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanno_nozura_nori_set.txt")
        lp = lp if os.path.isabs(lp) else os.path.join(V.REPO, lp)
        bad = 0
        made = []
        for tag_, end_, h_, ls_ in read_nnori_list(lp):
            for v_ in (OPT.get("v") or "a").split(","):
                ro, _, _ = make_wall(h_, 0.0, v_)
                ref_ = [(y, round(z - h_, 3)) for y, z in seam_verts(ro, (1 if end_ == "P" else -1) * L / 2) if z > h_ - 0.25]
                o, name = make_nnori(ls_, h_, end_, v_)
                bad += check_nnori(o, ls_, h_, end_, v_, ref_)
                export(o, name, OUT_WALL)
                made.append((ls_, h_, end_, v_))
                print("NNORI 書き出し %s ← %s" % (name, tag_))
        if RENDER:
            for (ls_, h_, end_, v_) in made:
                if OPT.get("shots") is None or ("%.2f" % ls_) in OPT["shots"].split(","):
                    render_nnori(ls_, h_, end_, v_)
        if bad:
            sys.exit("NNORI ⛔ 検算が %d 件落ちた" % bad)
    if what == "sode_nori":
        # blender ... -- sode_nori [--keri=0.250 --fumi=0.542] [--e=-0.20,-0.15] [--render] ── 背を相手の法で切った野面の袖
        keri_, fumi_ = float(OPT.get("keri") or 0.250), float(OPT.get("fumi") or 0.542)
        es_ = _floats("e", NNORI_SODE_E)
        bad = 0
        for e_ in es_:
            for v_ in "ab":
                o, name = make_sode_nnori(keri_, fumi_, e_, v_)
                bad += check_sode_nnori(o, keri_, fumi_, e_)
                export(o, name, OUT_SODE)
        if RENDER:
            for e_ in es_:
                if OPT.get("shots") is None or ("%+.2f" % e_) in OPT["shots"].split(","):
                    render_sode_nnori(keri_, fumi_, e_, "a")
        if bad:
            sys.exit("SNORI ⛔ 検算が %d 件落ちた" % bad)
    if what == "mikiri_h":
        # blender ... -- mikiri_h [--h=1.5,1.8] [--render] ── 丈を合わせた見切り石
        bad = 0
        for h_ in _floats("h", MIKIRI_TIERS):
            o, name = make_mikiri_h(h_)
            bad += check_mikiri_h(o, h_)
            export(o, name, OUT_WALL)
            if RENDER:
                render_mikiri_h(h_)
        if bad:
            sys.exit("MIKIRI ⛔ 検算が %d 件落ちた" % bad)
    if what in ("wall", "all"):
        do_wall()
    if what in ("kiri", "all"):
        do_kiri()
    if what in ("mikiri", "all"):
        do_mikiri()
    if what in ("sode", "all"):
        do_sode()
    if RENDER:
        if what in ("wall", "all", "kiri"):
            render_wall_run("")
            render_wall_run("_magenta", magenta=True)
            render_tier_mix("")
        if what in ("mikiri", "all"):
            render_mikiri()
    for r in REPORT:
        print("NOZURA_SUM %s %d" % (r[0], r[1]))
