"""**類型共用の附属屋** — 米蔵・厩・作事小屋(邸を問わず 88 区画の類型ビルダーが使う)。

    blender --background --python Tools/Blender/build_typ_fuzokuya.py -- [名前...] [--render]
    (名前を省くと全部。komegura / umaya / sakuji)

【なぜ新造するか】EDO-0304 案A ①(2026-09-21 施主裁定)。三べ坂13区画で類型版が旧版より
  薄くなったのは棟数ではなく**附属の種別が消えた**ため。在庫方の照会では汎用の附属は
  土蔵 `Eg.Kura`(edogoyomi・ES後 6.23×6.51×6.64m)**1点だけ**で、これを米蔵にも兼ねると
  同じメッシュが並ぶだけで作り分けが見えない。厩・作事小屋は**個邸専用の手組みしかない**。

【方針 — ゼロから起こさない(`build_doi_buzai.py` と同じ薄い駆動器)】
  ・米蔵     … 松平の `build_matsudaira_dewa_fuzokuya.dozo`(石腰+白漆喰大壁+観音扉)を
                **軒を上げ・窓を縮めて**呼ぶ。⛔ 別実装を書かない
  ・厩       … 岡部の `build_okabe_fuzokuya.umaya`(板壁・桟瓦・前面吹き放ち)
  ・作事小屋 … 岡部の `build_okabe_fuzokuya.nandokoya`(板葺・四周板壁・板戸)を
                3×2間へ広げて呼ぶ(引数は 2026-09-21 にこの用途のため出した)

【寸法は**部材方が決めた**(指図に欄が無い・確度 U)。根拠は各 docstring の1行】
  ・米蔵     3間(梁間) × 4間(桁行) = 5.454 × 7.272m・軒 5.20
  ・厩       3間(梁間) × 4間(桁行) = 5.454 × 7.272m・軒 2.55(馬房4房)
  ・作事小屋 2間(梁間) × 3間(桁行) = 3.636 × 5.454m・軒 2.45
  ⭐ **どれも足形を `Eg.Kura`(6.23×6.51)と同じ桁に収めてある** — 類型ビルダーの
    `Plan()` が蔵に与える離隔半径 6m をそのまま使え、中〜小の筆でも弾かれないため。
  ⛔ これより大きくしない。大きい邸の附属は**指図を持つ邸の専用部材**(Doi_*/Okabe_*)がある。

【向きとピボット(Unity 座標)】幅=X(**長手=棟の走る向き**)/ 高さ=Y / 厚み=Z。
  ピボット = **footprint の中心・地盤レベル**(3点とも)。据えるときは
  **ローカル +X を棟を向けたい向きへ**。⚠ 厩と作事小屋は **+Z が開口面**。

【材】⛔ 新規に作らない。倣った先の材質名をそのまま運ぶ —
  `Fence_B_01` / `Foundation_A_01` / `Wall Exterior Defence`(米蔵)、
  `wood` / `wall C` / `Foundation_A_01` / `roof`(厩・作事小屋)。
"""
import bpy, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import build_matsudaira_dewa_fuzokuya as F      # dozo(石腰 + 白漆喰 + 観音扉)
import build_okabe_fuzokuya as OF               # umaya / nandokoya

KEN = 1.818
OUT = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Fuzokuya"))
SHOT = os.path.join(V.REPO, "Screenshots")


# ================================================================ 米蔵
def komegura():
    """**米蔵 3間(梁間)× 4間(桁行)**・軒 5.20。⛔ `Eg.Kura` を米蔵に兼ねない。

    【`Eg.Kura`(汎用の土蔵)と並べたときに何で見分けるか — 在庫方の指示は「妻を高く・窓を小さく」】
      ① **丈**    棟天端 7.2m 見当 対 `Eg.Kura` 6.64m。⚠ 棟高は指定できない従属値で、
                  瓦の勾配 0.5456 は動かせないから **軒 5.20** を上げて丈を稼ぐ
                  (`Eg.Kura` の軒より 0.6m 高い)。⇒ 実測は下の print が申告する
      ② **窓**    妻の小窓を `mado=0.55` で **0.51m 角** へ縮める(土蔵の 0.92m 角の 55%)。
                  米を風で傷めないので蔵より窓を小さく取る、という読み【確度U】
      ③ **足形**  1.33:1 の長手のある矩形(`Eg.Kura` はほぼ正方 1.04:1)。棟が通って見える
      ④ **高窓**  長手の大壁に **3口ずつの風抜きの高窓**(`gawa_mado=3`)。
                  ⚠ ③まででは足りなかった — 2026-09-21 に `Eg.Kura` と並べて焼いたら、
                  長手が 7.3 × 3.1m の**一面の白**で「意匠の無い箱」に見えた
                  (`Eg.Kura` は妻に窓・扉・庇・棟飾りが付く)。米蔵は**風を抜くのが用途**
                  なので、ここに窓が並ぶのが作りとして正しく、同時に見分けも付く

    ⚠ 寸法の根拠【U】: 3間の梁間は `Eg.Kura`(3.58間)を割り切れる整数間へ丸めた値、
      桁行4間は**足形を `Eg.Kura` と同じ桁(5〜7m)に収めつつ長手を作る**ための最小。
      ⛔ 史料値ではない — 邸ごとの米蔵の実寸が出たら専用部材を起こすこと。

    ローカル **+X = 桁行(長手・棟の走る向き)**。⚠ **観音扉は −X の妻**、小窓は +X の妻。
    ピボット = footprint の中心・地盤レベル。"""
    return F.dozo(uk=3, vk=4, name="Typ_Komegura", eave=5.20,
                  mado=0.55, gawa_mado=3, mizukiri_tooshi=False), "Typ_Komegura"


# ================================================================ 厩
def umaya():
    """**厩 3間(梁間)× 4間(桁行)**・軒 2.55。岡部の吹き放ちの厩と同じ型(板壁・桟瓦)。

    ⚠⚠ **軒高は「棟をどこに納めたいか」からの逆算値**(`build_okabe_fuzokuya.umaya` の断り)。
      瓦の勾配 0.5456 は動かせないので **棟 = 軒 + 梁間/2 × 0.5456**。
      2.55 は **棟 4.04(天端 4.38)**に納まる値で、⭕ 類型の主屋(`VK.House` 級)より
      確実に低く、米蔵(7.2)よりずっと低い — **格の順(厩 < 家中 < 蔵・主屋)が立面で読める**。
    ⛔⛔ **軒だけ下げると吹き放ちが塞がって厩に見えなくなる**(2026-09-06 に実見)。
      半高壁 1.15 と軒の出 0.70 を合わせて選び、**吹き放ちの帯 0.93m** を岡部の 0.95 と
      同等に保ってある。⇒ 実測は生成器の print が申告する。
    ⚠ 馬房は**4房**(生成器が 4 等分に仕切る)。桁行 4間 なので 1房 = ちょうど 1間。

    ローカル **+X = 桁行(長手)/ +Z = 吹き放ちの開口面**。⚠ 据えるとき +Z を郭の内へ。
    ピボット = footprint の中心・地盤レベル。寸法の根拠【U】: 1房1間 × 4房 が
    類型の中規模屋敷の馬数として穏当で、足形が `Eg.Kura` と同じ桁に収まる最小。"""
    return OF.umaya(uKen=3, vKen=4, name="Typ_Umaya",
                    eaveH=2.55, frontH=1.15, noki=0.70)


# ================================================================ 作事小屋
def sakuji_koya():
    """**作事小屋 2間(梁間)× 3間(桁行)**・軒 2.45・**板葺(4寸)**。
    岡部の納戸小屋と同じ型(四周板壁・前面に板戸)を、道具と材が入る大きさへ広げたもの。

    ⛔ **瓦を載せない** — 作事の小屋に瓦は過ぎるし、`roof 2x2` の勾配 0.5456 固定では
      2間の梁間に架けても棟が立ち過ぎる(納戸小屋の断りと同じ)。板葺なので勾配は選べて
      **0.40(4寸)【U】** ⇒ 棟 3.40(棟押えの天端 3.54)。⭕ 厩(4.38)より更に低く、
      **附属3点の丈が 7.2 / 4.4 / 3.5 と段になる** — 並べて置いても見分けが付く。
    ⭕ 納戸小屋との違いは**大きさと戸**: 骨を 3×2 の割付にし、戸を **両開き 1.30m**
      (納戸は片開き 0.82m)にして材を担ぎ込める口にした。⚠ 姿は【U】。

    ローカル **+X = 桁行(長手・棟の走る向き)/ +Z = 板戸のある面**。
    ピボット = footprint の中心・地盤レベル。寸法の根拠【U】: 板戸 1.30m が通り、
    大工の作業台が置ける最小の矩形(2×3間)。⛔ これ以上大きくすると主屋と紛れる。"""
    return OF.nandokoya(uKen=3, vKen=2, name="Typ_SakujiKoya",
                        eaveH=2.45, noki=0.55, end=0.30, ratio=0.40,
                        base=0.20, post=0.14, nx=3, nz=2,
                        dw=1.30, doorH=2.05, leaves=2, pitch=0.19)


PARTS = {"komegura": komegura, "umaya": umaya, "sakuji": sakuji_koya}


def _check(o, name, mn, mx):
    """**見分けが付くか**を数値で出す(⛔ 目視だけで通さない)。
      ① 丈と足形を `Eg.Kura` と比べる(**ES 1.818 倍後の実測 W6.23 × H6.51 × D6.64**。
         ⚠ 目録の tsv は素寸 3.43/3.58/3.65。⛔ 丈に D の 6.64 を当てない)
      ② 足形の半対角が類型ビルダーの離隔半径 6m に収まるか(収まらないと小さい筆で弾かれる)"""
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    half = ((W * W + D * D) ** 0.5) / 2.0
    print("[typ] %-16s 比較 Eg.Kura(W6.23 H6.51 D6.64): 丈 %+.2fm / 足形比 %.2f:1(Kura 1.07:1)"
          % (name, H - 6.51, max(W, D) / max(1e-6, min(W, D))))
    print("[typ] %-16s 足形の半対角 %.2fm → %s(類型ビルダーの蔵の離隔半径 6m)"
          % (name, half, "OK" if half <= 6.0 else "⚠ はみ出す恐れ"))


def shots(o, key, box):
    """⚠ **書き出しの前に撮る** — `export_fbx` の後は bbox が潰れて画角が壊れる。
    ⚠ `ortho_scale` は**画像の長辺**に効く(`build_okabe_fuzokuya.ortho` の項)。
    ⭕ 4枚: 開口面の斜め / 開口面の立面 / 背面の斜め(開口の漏れ)/ 妻の立面(妻壁の塞ぎ)。
    ⛔ 地面を z=0 に敷く — 3点ともピボットが地盤レベルなので、足元の浮きがここで読める。"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    r = max(W, H, D)
    bpy.ops.mesh.primitive_plane_add(size=max(60.0, r * 20), location=(c.x, c.y, 0.0))
    V.studio((mn.x - r * 0.9, mn.y - r * 1.8, max(1.7, H * 0.7)),
             (c.x, c.y, H * 0.42), res=(1700, 1000))
    V.render(os.path.join(SHOT, "typ_%s_3d.png" % key))
    V.studio((c.x, mn.y - r * 2.4, c.z), (c.x, c.y, c.z),
             ratio_fix(W, H, (1700, 1000)), res=(1700, 1000))
    V.render(os.path.join(SHOT, "typ_%s_elev.png" % key))
    V.studio((mx.x + r * 0.9, mx.y + r * 1.8, max(1.9, H * 0.7)),
             (c.x, c.y, H * 0.42), res=(1700, 1000))
    V.render(os.path.join(SHOT, "typ_%s_ura.png" % key))
    V.studio((mn.x - r * 2.6, c.y, c.z), (c.x, c.y, c.z),
             ratio_fix(D, H, (1300, 1100)), res=(1300, 1100))
    V.render(os.path.join(SHOT, "typ_%s_gable.png" % key))


def ratio_fix(w, h, res):
    return max(w, h * float(res[0]) / res[1]) * 1.12


# ================================================================ 並べ比べ(書き出さない)
def narabe():
    """**在庫の土蔵 `Eg.Kura` と3点を一列に並べて焼く。**

        blender --background --python Tools/Blender/build_typ_fuzokuya.py -- narabe

    ⭕ これが在庫方の出した合否条件そのもの(「並べたとき土蔵と見分けが付くこと」)。
    ⛔ 部材単体の立面では**見分けが付くか**は読めない — 丈も足形も比べる相手が要る。
    ⚠ `es_kura` の obj は素寸なので **ES=1.818 倍**してから並べる(`EdoAssets.Eg` の規約)。
    ⛔ 何も書き出さない。"""
    import vkmesh as VM
    V.reset()
    xs, objs = 0.0, []
    kura = VM.import_fbx_abs.__module__ and None       # obj は fbx でないので下で直に読む
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(V.REPO, "Assets", "edogoyomi",
                                                "es_kura", "kura.obj"))
    got = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    kura = V.join(got, "Eg_Kura_ref")
    V.sel([kura])
    bpy.ops.transform.resize(value=(1.818,) * 3, center_override=(0, 0, 0))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mn, mx = V.bbox([kura])
    kura.location = (-mn.x, -(mn.y + mx.y) / 2.0, -mn.z)
    bpy.context.view_layer.update()
    V.sel([kura]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    xs = mx.x - mn.x + 3.0
    objs.append(kura)
    print("[typ] 並べ比べ 在庫 Eg.Kura(ES後) W=%.2f H=%.2f D=%.2f"
          % (mx.x - mn.x, mx.z - mn.z, mx.y - mn.y))
    for key in ("komegura", "umaya", "sakuji"):
        o, name = PARTS[key]()
        mn, mx = V.bbox([o])
        o.location = (xs - mn.x, 0.0, 0.0)
        bpy.context.view_layer.update()
        V.sel([o]); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        xs += (mx.x - mn.x) + 3.0
        objs.append(o)
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    bpy.ops.mesh.primitive_plane_add(size=200.0, location=(xs / 2.0, 0.0, 0.0))
    # ① 一列の立面(丈の段と足形の違いを一枚で読む)
    V.studio((xs / 2.0, -46.0, 4.0), (xs / 2.0, 0.0, 4.0),
             ortho_scale=xs * 1.05, res=(2000, 700))
    V.render(os.path.join(SHOT, "typ_narabe_elev.png"))
    # ② 人の目の高さから斜めに(実際に見える姿)
    V.studio((-6.0, -20.0, 1.6), (xs * 0.45, 0.0, 3.0), res=(1900, 900))
    V.render(os.path.join(SHOT, "typ_narabe_me.png"))
    print("[typ] 並べ比べ: Screenshots/typ_narabe_{elev,me}.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or list(PARTS.keys())
    if "narabe" in want:                  # ⛔ 書き出さない検証だけの枝
        narabe()
        want = [w for w in want if w != "narabe"]
    for key in want:
        if key not in PARTS:
            print("[typ] ⚠ 知らない部材: %s (%s)" % (key, "/".join(PARTS)))
            continue
        V.reset()
        o, name = PARTS[key]()
        mn, mx = V.bbox([o])
        print("[typ] %-16s Unity実寸 W(X)=%6.3f  H(Y)=%6.3f  D(Z)=%6.3f  底=%+.3f  面=%d  頂点=%d"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z,
                 len(o.data.polygons), len(o.data.vertices)))
        print("[typ] %-16s 材質=%s" % (name, [mm.name for mm in o.data.materials]))
        _check(o, name, mn, mx)
        if "--render" in argv:
            shots(o, key, (mn, mx))       # ⚠ 書き出しの前に撮る
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[typ] 書き出し " + os.path.join(OUT, name + ".fbx"))


main()
