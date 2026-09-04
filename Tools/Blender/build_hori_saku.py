"""**汀の木柵** — 堀端(溜池の岸)の境界柵。岡部筑前守上屋敷 辺5。

    blender --background --python Tools/Blender/build_hori_saku.py -- [--render]
    blender --background --python Tools/Blender/build_hori_saku.py -- saku [--render]   # 1スパンだけ
    blender --background --python Tools/Blender/build_hori_saku.py -- post [--render]   # 端の杭だけ

【なぜ新造するか】いま辺5 に立っているのは在庫の `Eg.Hogaki5`(穂垣)で、**実丈 0.79m**。
  指図 `const.fenceH` は **1.40** で、⛔ **0.6m 足りない**。ビルダー自身の突き合わせも
  「柵の丈が指図と合わない」を鳴らす(`EdoOkabeYashikiBuilder.Stage2_Perimeter`)。
  在庫の柵はどれも合わない — Village Kit の `fence A/B`(3.30m・板葺の笠木つきの板塀)、
  `Fence_B_01_x1`(1.98m・同じく笠木つき)はいずれも**屋根を持つ板塀**で、
  「基礎も基壇も持たない地形なりの木柵」ではない(2026-09-04 に実見して却下)。

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` が正典】
  ・`const.fenceH` = **1.40**(天端。⚠ 視線の遮蔽の計算がこの値を前提にしている)
  ・`fences[0]` F_Hori … 辺5 の s 0〜80.589 の全長。典拠 [広重・赤坂桐畑] = **B**、
    高さと基礎なしは**プロジェクトの作法 = U**
  ・`nishi.saku._` … 「⛔ **高さを下げない**」— h0.9 との差で見えるようになる水面は
    ごく手前だけで、足元の水を見る口は**潜り**(`Own.HoriKido`)が受け持つ

【姿は潜り(`build_kido.horikido`)に合わせてある】同じ柵の線に建つ以上、別の作りにできない。
  ・杭は **0.11角**・z は **[−0.055, +0.055]** — 潜りの方立柱と**同寸・同一平面**
  ・上の横木の高さ **1.325..1.40** も潜りと同じ(天端 1.40 が一直線に通る)
  ・材は Village Kit の `wood` ひとつ

【作り】杭 + 貫2段 + 上の横木 + 横板5枚。⭕ **板は杭の内側(屋敷側)に張る** —
  外(水側)から見ると杭が1間ごとに立ち、その奥に板の面がある、という普通の板柵の見え方になる。
  ⛔ **板を1枚で貼らない** — 5枚を実体で積む(下見板で踏んだのと同じ罠)。
  ⛔ **目地を空けない。**7mm でも空けると向こうが透けて立面に白い筋が4本入り、
    視線の遮蔽 h1.40 の前提も崩れる(2026-09-04 に実見して**南京下見の重ね張りへ改めた**)。
  ⛔ **木理を板幅の側へ流さない** — `Mesh.box` は u=第1軸固定なので長い横板に縦木理が乗り、
  「縦縞の平板」に見える。外面だけ `build_obi_nagaya.hboard` が `quad_uvs` で長手へ流す。
  ⚠ **板継ぎ(1.2m ごとの UV の帯替え)は入れない** — 1スパン 1.818m に継ぎを入れると
    5段ぶんの縦の切れ目が同じ x に揃って、立面に**柱でない縦線**が立つ(実見)。
    帯替えは**段ごと**に行う。

【向きとピボット(Unity 座標)】幅=X(走り)/ 高さ=Y / 厚み=Z。**+Z = 見え面 = 外(水側)**。
  ・`HoriSaku` … **1スパン = 1間**。ピボット = **スパンの中心・地盤レベル**。
      杭は **−X 端**に立ち(杭の外面が x=−0.909 に一致する = **bbox がちょうど1間**)、
      横板と貫は −X 端から +X 端まで通る。⇒ 1.818 ちょうどのピッチで並べれば、
      杭が1間ごとに立ち板が継ぎ目で通る。
  ・`HoriSakuPost` … run の **+X 端に足す杭1本**。⛔ 足さないと最後の板が宙で終わる。
      ピボット = **run の終端(杭の +X 面)・地盤レベル**。⇒ `s = s1` をそのまま渡せばよい。
  ・**根入れ 0.12 が y<0 に出ている。**⛔ `SeatBottom` で据えない(0.12 浮く) —
      **`position.y = 地盤` を直に入れる**。根が地面へ潜って足元の凹凸を飲む。

【材】`wood`(Village Kit)。⛔ 新規マテリアルを作らない。
  remap は `Edo/岡部筑前守上屋敷/新造部材のマテリアルをremap`(出力先 `Models/Hei` は既に見ている)。

【落とし穴】
  ・⚠ **bbox をちょうど1間にする。**ビルダーの `MeasureRunWidth` が bbox から走り方向の
    実寸を測ってピッチを決めるので、杭が −0.909 より外へはみ出すと**ピッチが 1.968 になって
    杭の間隔が狂う**。杭の芯は −0.854(外面が −0.909)。
  ・⚠ ビルダーの柵の run は駒を **`OVER` 0.15 重ねて**並べる(穂垣なら重なりが見えなかった)。
    **板柵では板が 0.15 重なって z-fighting する**ので、この部材は **重ねずに 1.818 ちょうどで
    突き付ける**こと(棟梁への申し送り)。
  ・⚠ `export_fbx` を通した後は bbox が 0 に潰れる。**測るのもレンダも書き出しの前に**。
"""
import bpy, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_obi_nagaya as N

OUT  = os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei")
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD = N.WOOD

# ---- 指図の値 ----------------------------------------------------------
KEN   = 1.818        # 1スパン = 江戸間1間
H     = 1.40         # const.fenceH — 天端(地盤から)
# ---- 作りの値(【U】指図に無い。潜り `build_kido.horikido` に合わせてある)----
POST  = 0.11         # 杭の見付・見込(潜りの方立柱と同寸)
ROOT  = 0.12         # 根入れ(y<0 へ出る)。⛔ 0.15 を超えると丈の突き合わせが誤って鳴る
FACE  = 0.055        # 杭の外面の z(潜りの方立柱・頭貫の前面と同一平面)
BACK  = FACE - POST  # 杭の内面 = 板を張る面(−0.055)
LAP_M, LAP_S = 0.020, 0.038   # 横板の 身 / 下端(下の板に被さるせり出し)の見込
NB    = 5            # 横板の枚数
Y0    = 0.12         # 板の下端(足元の抜け。地形の凹凸をここで飲む)
RAILS = (0.365, 1.035)        # 貫2段の芯の高さ
RAIL_H = 0.075                # 貫の見付
KASA_Y = 1.325                # 上の横木(天端 H まで)


def _plank(m, rect, x0, x1, y0, y1, z0, z1):
    """横に走る板・貫を1本。**両面とも木理を長手へ流す**。

    ⛔ `Mesh.box` に任せない — u=第1軸固定なので `wuv`(柱用の**縦長の帯**。木理は v 方向)
      を貼ると木理が板の**幅の側**へ流れ、横板が「縦縞の平板」に見える(README の罠)。
    ⛔ `build_obi_nagaya.hboard` も使わない — あれは box の面に**同一平面の板を1枚重ねる**ので、
      Unity では z-fighting する。ここは**大面2枚を自前で出し、小口4枚だけ box 的に足す**。
    """
    u0, v0, u1, v1 = rect
    # 大面(表・裏)。長手 → v(木理)/ 板幅 → u
    m.quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], rect, WOOD)
    m.uv[-4:] = [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
    m.quad([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], rect, WOOD)
    m.uv[-4:] = [(u0, v1), (u0, v0), (u1, v0), (u1, v1)]
    # 小口4枚(⛔ 塞がないと板の中が透ける)
    e = VM.sub(rect, 0.0, 0.0, 0.25, 0.25)
    m.quad([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], e, WOOD)
    m.quad([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], e, WOOD)
    m.quad([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], e, WOOD)
    m.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], e, WOOD)


def _post(m, P, cx):
    """杭1本。y は −ROOT..H。z は **潜りの方立柱と同じ [−0.055, 0.055]**。
    ⭕ 板は杭の**内側**に張るので、外(水側)からは杭が1間ごとに立って見える。
    ⭕ 縦材なので `Mesh.box` のままでよい(u=x=見付 / v=y=丈 で木理が丈方向に流れる)。"""
    m.box(cx - POST / 2, cx + POST / 2, -ROOT, H, BACK, FACE,
          VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)


def _rails(m, P, a0, a1):
    """貫2段 + 上の横木。杭より 0.045 引っ込めて通す(杭が手前に見えるように)。
    ⚠ 上の横木は**潜りの上の横木(1.325..1.40)と同じ高さ**にしてある。"""
    for y in RAILS:
        _plank(m, VM.sub(P['wuv'], 0.20, 0.05, 0.42, 0.95),
               a0, a1, y - RAIL_H / 2, y + RAIL_H / 2, BACK, FACE - 0.045)
    _plank(m, VM.sub(P['wuv'], 0.46, 0.05, 0.70, 0.95),
           a0, a1, KASA_Y, H, BACK, FACE - 0.040)


def _boards(m, P, a0, a1):
    """横板 NB 枚を**南京下見に重ねて**張る(杭の内側の面 `BACK` に)。
    ⛔ **目地を空けない。**7mm でも空けると向こうが透けて、立面に白い筋が
      NB−1 本入る(2026-09-04 に実見。視線の遮蔽 h1.40 の前提も崩れる)。
      ⭕ 重ね張りなら y に隙が無く、下端のせり出しの影で「板を張った」と分かる。
    ⚠ **柵は両面から見える。**塀と違って裏が隠れないので、`_plank` で**表裏とも**
      木理を長手へ流す。"""
    h = (H - Y0) / NB
    for i in range(NB):
        a = Y0 + i * h
        # ⚠ **板の長手は wuv の v を目いっぱい使う。**`wuv` は柱用の**縦長の帯**で、
        #   v が木理の方向。長手を v の 1/4 だけに割り当てると 1.8m に 0.2 しか当たらず、
        #   引き伸ばされて**節の染みが並ぶ斑(まだら)**になった(2026-09-04 に実見)。
        #   ⭕ 長手 → v 全域 / 板幅 → u の細い帯(段ごとにずらす)。
        # ⚠ 帯の両端(u 0 / 1)はアトラスの隣と接していて**縦の刻みが混じる**ので使わない
        lo, hi = 0.10, 0.90
        u0 = lo + (hi - lo) * i / float(NB)
        u1 = lo + (hi - lo) * (i + 1) / float(NB)
        rect = VM.sub(P['wuv'], u0 + 0.008, 0.02, u1 - 0.008, 0.98)
        for (ylo, yhi, d) in ((a + h * 0.26, a + h, LAP_M), (a, a + h * 0.26, LAP_S)):
            _plank(m, rect, a0, a1, ylo, yhi, BACK - d, BACK)


def saku(name="HoriSaku"):
    """木柵 1スパン(杭1 + 貫2 + 横板5)。杭は −X 端・外面が x=−KEN/2 に一致する。"""
    P = N.palette()
    m = VM.Mesh()
    a0, a1 = -KEN / 2.0, KEN / 2.0
    _post(m, P, a0 + POST / 2.0)              # ★ 外面を a0 に合わせる(bbox をちょうど1間に)
    _rails(m, P, a0, a1)
    _boards(m, P, a0, a1)
    o = m.to_object(name, [P['wood']])
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[saku] %-13s 1スパン %.3f / 天端 %.2f / 根入れ %.2f / 杭 %.2f角 / 板 %d枚"
          % (name, KEN, H, ROOT, POST, NB))
    return o, name


def post(name="HoriSakuPost"):
    """run の +X 端に足す杭1本。⛔ 足さないと最後の板が宙で終わる。
    ピボット = **run の終端(杭の +X 面)・地盤** ⇒ `s = s1` をそのまま渡せる。"""
    P = N.palette()
    m = VM.Mesh()
    _post(m, P, -POST / 2.0)                  # x ∈ [−POST, 0]。+X 面が原点
    o = m.to_object(name, [P['wood']])
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[saku] %-13s 端の杭 %.2f角 / 天端 %.2f / 根入れ %.2f" % (name, POST, H, ROOT))
    return o, name


# ---------------------------------------------------------------- レンダ
def shots(o, key, extra=None, box=None):
    """⚠ `box` は**書き出しの前に**測った値を渡す(後だと bbox が 0 に潰れる。README)"""
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    objs = [o] + list(extra or [])
    mn, mx = box if box else V.bbox(objs)
    W, Hh, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    print("[saku] レンダ %-12s bbox X %.2f..%.2f  Y(高) %.2f..%.2f  Z(厚) %.2f..%.2f"
          % (key, mn.x, mx.x, mn.z, mx.z, mn.y, mx.y))
    c = (mn + mx) * 0.5
    # 外(水側 = 論理 +厚み = Blender −Y)から見た立面
    V.studio((c.x, mn.y - max(W, Hh) * 2.4, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, Hh * 1500.0 / 1100) * 1.15, res=(1500, 1100))
    V.render(os.path.join(SHOT, "saku_%s_elev.png" % key))
    V.studio((mn.x - W * 0.5, mn.y - W * 1.1, max(1.6, mx.z * 1.5)),
             (c.x, c.y, mx.z * 0.5), res=(1600, 1100))
    V.render(os.path.join(SHOT, "saku_%s_3d.png" % key))
    # 内(屋敷側)から — 板の裏・貫・杭の取り合いを見る
    V.studio((mn.x - W * 0.5, mx.y + W * 1.1, max(1.6, mx.z * 1.5)),
             (c.x, c.y, mx.z * 0.5), res=(1600, 1100))
    V.render(os.path.join(SHOT, "saku_%s_in.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--")] or ["saku", "post"]
    do_render = "--render" in argv
    fns = {"saku": saku, "post": post}
    for key in want:
        if key not in fns:
            print("[saku] ⚠ 知らない部材: %s" % key); continue
        V.reset()
        o, name = fns[key]()
        mn, mx = V.bbox([o])
        print("[saku] %-13s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  "
              "Y範囲 %.3f..%.3f  面=%d  材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, mx.z,
                 len(o.data.polygons), [mm.name for mm in o.data.materials]))
        if do_render:
            shots(o, key, box=(mn, mx))       # ⚠ 書き出しの前に撮る
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[saku] 書き出し " + os.path.join(OUT, name + ".fbx"))
    if do_render:
        # ⭕ **並べた姿を必ず見る。**1枚だけ見ても継ぎ目と端部の不良は見つからない
        V.reset()
        objs = []
        for i in range(3):
            o, _ = saku("run%d" % i)
            o.data.transform(__import__("mathutils").Matrix.Translation((i * KEN, 0, 0)))
            o.data.update(); objs.append(o)
        p, _ = post("runpost")
        p.data.transform(__import__("mathutils").Matrix.Translation((2.5 * KEN, 0, 0)))
        p.data.update(); objs.append(p)
        shots(objs[0], "run", extra=objs[1:])


if __name__ == "__main__":
    main()
