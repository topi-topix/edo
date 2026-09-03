"""**木戸** — のし塀(結界)の開口に建てる板戸と、汀の柵に開ける潜り。岡部筑前守上屋敷。

    blender --background --python Tools/Blender/build_kido.py -- kekkai [--render]   # 結界の2口
    blender --background --python Tools/Blender/build_kido.py -- kido 2.727 [--render]
    blender --background --python Tools/Blender/build_kido.py -- horikido [--render]

【なぜ新造するか】在庫に木戸は無い。のし塀 `Own.Noshibei(len)` は**開口を含まない**ので、
  W5・W6 の口を塞ぐ部材が無いまま残っていた(2026-09-04 の部材方の申し送り)。

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` が正典】
  ・結界の木戸 = `kekkai[].gap`(⚠ キーは `openings` ではなく **`gap`**)
      W5「庭掃除と落葉出し用」 u −19.0 → −17.5 = **1.5間 = 2.727m**
      W6「勝手の木戸」        v 109.4 → 112.4 だが `gap._` は **「幅 1.6間」= 2.909m**
      ⚠⚠ **W6 は指図の中で数字が3つ食い違う** — 下の【W6の食い違い】を参照。
      高さは塀 `kekkai[].h` = 1.8 以下。**柱 1.80 / 内法 1.50** で納めた【U】。
  ・汀の潜り = `nishi.saku.kuguri` … 辺5 の **s=55.7**・幅 **1.818(1間)**・**片開き h1.2**
      ⛔ 「堤へ出る門」ではない(区画界より外は当家の地ではない)。**足元の水を見せる口**で
        **見所⑫を兼ねる**(`nishi.mikoro[0]`「木戸の敷居(堀端)」・立って見る)。
      ⛔ 桟橋・船着・水汲みの段を付けない。
      ⚠ 柵は h1.4 で**下げない**(`nishi.saku._`)。潜りだけ 1.2 に落とすので、
        頭貫の上に 0.2 の抜けが残る — そこは柵と同じ横木2段で埋めてある。

【⚠⚠ W6 の食い違い(普請奉行へ)】同じ開口について指図が3つの数を持っている:
    ① `gap.from/to` の差 = **3.00間**(5.454m)
    ② `gap._` の文言   = **1.6間**(2.909m)
    ③ 塀の実際の口     = 塀の端 `b` が v111.25 なので **109.4〜111.25 = 1.85間**(3.363m)
  ⭕ ここでは**②(文言の 1.6間)を採って焼いた** — 人が読む文が一番新しい裁定(2026-09-03
    ユーザー裁定8=A)の帰結として書かれているため。⛔ ①③ と合っていないので、
    **指図側で1つに揃えるまで据えないこと。**

【⚠ 片開き/両開きについて — 仕様と物理が合わない】
  依頼は「片開きの板戸」だが、**2.7〜2.9m の一枚戸は建具として成立しない**
  (板の面積 4m² 超・吊り元にかかる曲げが持たない。実物の木戸は1間を超えれば両開き)。
  ⭕ **開口 1.4m 以下なら片開き、超えたら両開き**として焼いた(`leaves` で上書きできる)。
  片開きで通したいなら**開口を狭める**か**袖に羽目板の固定部を入れる**必要があり、
  どちらも塀の run の長さが動くので **普請奉行の裁定事項**。
  ⭕ 汀の潜り(1.818)は指定どおり **片開き**にした — h1.2 と低く、農家の門扉と同じ寸法比で成立する。

【向きとピボット(Unity 座標)】幅=X(開口の走り)/ 高さ=Y / 厚み=Z。
  ピボット = **開口の芯・地盤レベル**(⚠ 塀の芯と揃う)。**+Z = 見え面**。
  ⇒ のし塀の run と同じ yaw を与えれば面が揃う。⚠ **X の実寸は開口より柱2本ぶん広い**
  (下の実測)。塀の run はこの外側に取り付くので、**開口の値ではなく実寸で継ぐこと**。

【材】`wood` / `Foundation_A_01`(Village Kit)。⛔ 新規マテリアルを作らない。
"""
import bpy, sys, os, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_obi_nagaya as N

OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei")
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD, WALL, STONE = N.WOOD, N.WALL, N.STONE

# 指図 kekkai[].gap の2口(⚠ W6 は文言の 1.6間 を採る。docstring の【W6の食い違い】)
KEKKAI_GAPS = [1.5 * 1.818, 1.6 * 1.818]


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def _posts(m, P, w, H, post, base=True):
    """開口の両脇の方立柱(+ 沓石)。戻り値は柱の外面の x"""
    px = w / 2.0 + post / 2.0
    for s in (-1, 1):
        m.box(s * px - post / 2, s * px + post / 2, 0.02, H, -post / 2, post / 2,
              VM.sub(P['wuv'], 0.10, 0.02, 0.42, 0.98), WOOD)
        if base:
            m.box(s * px - 0.17, s * px + 0.17, -0.14, 0.06, -0.17, 0.17,
                  VM.sub(P['suv'], 0, 0, 0.4, 0.4), STONE)
    return px + post / 2.0


def kido(w=2.727, name=None, H=1.80, leaves=None):
    """**結界の木戸**(のし塀の開口を塞ぐ)。方立柱2本 + 冠木 + 敷居 + 板戸。
    ⚠ `leaves` を省くと **開口 1.4m 以下=片開き / 超えたら両開き**(docstring の理由)。"""
    name = name or ("Kido_" + fmt(w))
    n = leaves if leaves else (1 if w <= 1.4 else 2)
    P = N.palette()
    POST = 0.13
    UCHI = H - 0.30                                   # 内法(冠木の下端)= 1.50
    m = VM.Mesh()
    ex = _posts(m, P, w, H, POST)
    # 冠木(柱の外へ少し出る)+ 上の埋め板(塀の天端 1.80 まで通す)
    m.box(-ex - 0.09, ex + 0.09, UCHI, UCHI + 0.17, -0.075, 0.075,
          VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.50), WOOD)
    m.box(-w / 2, w / 2, UCHI + 0.17, H, -0.045, 0.045,
          VM.sub(P['wuv'], 0.05, 0.55, 0.95, 0.85), WOOD)
    # 敷居。⛔ 抜けたままにしない(足元から向こうが透ける)
    m.box(-ex, ex, 0.0, 0.08, -0.105, 0.105,
          VM.sub(P['wuv'], 0.30, 0.10, 0.85, 0.30), WOOD)
    # 板戸。⛔ 板1枚で出さない — 竪板と桟を実体で起こす(`door_leaves` が受け持つ)
    # ⚠ **戸を開口より一回り大きく作って枠の裏へ回す。**開口ぴったりに作ると、
    #   framing との隙(数 mm)から向こうが透けて、立面で**戸の周りが白く縁取られる**
    #   (2026-09-04 に実見)。戸は柱より奥(−Z)に吊るので、はみ出しは表から見えない。
    # ⚠ 両開きのとき `door_leaves` は召し合わせのために**各戸を 0.03 内へ寄せる**ので、
    #   0.025 の被りでは相殺されて 5mm の隙が残る(実見)。0.06 取って確実に柱の裏へ回す
    N.door_leaves(m, P, -w / 2 - 0.06, w / 2 + 0.06, 0.055, UCHI + 0.02, 0.0, 1, n=n)
    o = m.to_object(name, [P['wood'], P['wall'], P['stone'], P['shoji']])
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[kido] %-14s 開口 %.3f / 内法高 %.2f / 戸 %d枚(%s)"
          % (name, w, UCHI, n, "片開き" if n == 1 else "両開き"))
    return o, name


def horikido(w=1.818, name="HoriKido"):
    """**汀の柵の潜り**(`nishi.saku.kuguri`・辺5 の s=55.7)。幅1間・**片開き h1.2**。
    ⛔ 「堤へ出る門」ではない — **足元の水を見せる口**で、敷居が**見所⑫**を兼ねる。
    ⛔ 桟橋・船着・水汲みの段を付けない。
    ⚠ 柵は h1.4 のままなので、潜り(1.2)の上に残る 0.2 は**柵と同じ横木2段**で埋める。
    ⭕ 戸は**縦の簀子**にした — 閉めても足元の水が透けて、見所として働く。"""
    P = N.palette()
    FH, KH, POST = 1.40, 1.20, 0.11               # 柵の高さ / 潜りの内法 / 柱
    m = VM.Mesh()
    ex = _posts(m, P, w, FH, POST)
    # 頭貫(潜りの内法)と、その上の柵の横木2段
    m.box(-ex, ex, KH, KH + 0.135, -0.055, 0.055,   # ⚠ 上の横木と 1cm 重ねる(隙が透ける)
          VM.sub(P['wuv'], 0.20, 0.15, 0.95, 0.50), WOOD)
    # ⚠ 頭貫の天端(1.31)と柵の天端(1.40)のあいだは 0.09 しかない。**横木は1本**。
    #   2本入れると重なって、上が1枚の広い板に見える(2026-09-04 に実見)
    m.box(-ex, ex, FH - 0.075, FH, -0.035, 0.035,
          VM.sub(P['wuv'], 0.30, 0.40, 0.90, 0.60), WOOD)
    # 敷居 = **見所⑫の足元**。⛔ 段を付けない(桟橋・水汲みの段の禁止に触れる)
    m.box(-ex, ex, -0.02, 0.07, -0.09, 0.09,
          VM.sub(P['wuv'], 0.30, 0.10, 0.85, 0.30), WOOD)
    # 潜り戸(片開き)— 框を組んで中は縦の簀子。⛔ 板で塞がない(水が見えなくなる)
    hw = w / 2.0 + 0.022                          # ⚠ 枠の裏へ回す(隙から透けるのを防ぐ)
    y0, y1 = 0.055, KH + 0.015
    zf, zb = -0.020, -0.055
    for (a, b) in ((-hw, -hw + 0.075), (hw - 0.075, hw)):
        m.box(a, b, y0, y1, zb, zf, VM.sub(P['wuv'], 0.62, 0.05, 0.80, 0.95), WOOD)
    for (c, d) in ((y0, y0 + 0.075), (y1 - 0.075, y1), ((y0 + y1) / 2 - 0.04, (y0 + y1) / 2 + 0.04)):
        m.box(-hw, hw, c, d, zb, zf, VM.sub(P['wuv'], 0.72, 0.10, 0.92, 0.45), WOOD)
    m.koshi(-hw + 0.075, hw - 0.075, y0 + 0.075, y1 - 0.075, zb + 0.006, zf - 0.006,
            VM.sub(P['wuv'], 0.60, 0.10, 0.95, 0.90), WOOD, pitch=0.135, bar=0.030, yoko=0)
    o = m.to_object(name, [P['wood'], P['wall'], P['stone'], P['shoji']])
    V.set_origin(o, (0.0, 0.0, 0.0))
    print("[kido] %-14s 開口 %.3f / 潜りの内法 %.2f / 柵 %.2f / 片開き" % (name, w, KH, FH))
    return o, name


def shots(o, key, box):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    W, H = mx.x - mn.x, mx.z - mn.z
    # ⚠ ortho_scale は**画像の長辺**に効く。幅だけで決めると縦が切れる
    V.studio((c.x, mn.y - max(W, H) * 2.4, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H * 1500.0 / 1100) * 1.15, res=(1500, 1100))
    V.render(os.path.join(SHOT, "kido_%s_elev.png" % key))
    V.studio((mn.x - W * 0.8, mn.y - W * 1.5, max(1.55, H * 0.85)),
             (c.x, c.y, H * 0.45), res=(1600, 1100))
    V.render(os.path.join(SHOT, "kido_%s_3d.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    jobs = []
    if "kekkai" in argv:
        jobs += [(fmt(g), (lambda g=g: kido(g))) for g in KEKKAI_GAPS]
    if "horikido" in argv or not argv or all(a.startswith("--") for a in argv):
        jobs.append(("horikido", horikido))
    if "kido" in argv:
        i = argv.index("kido")
        ws = [float(a) for a in argv[i + 1:] if not a.startswith("--")]
        jobs += [(fmt(x), (lambda x=x: kido(x))) for x in (ws or [2.727])]
    if not jobs:
        jobs = [(fmt(g), (lambda g=g: kido(g))) for g in KEKKAI_GAPS] + [("horikido", horikido)]
    for key, fn in jobs:
        V.reset()
        o, name = fn()
        mn, mx = V.bbox([o])
        print("[kido] %-14s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  底=%.3f  面=%d  材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons),
                 [mm.name for mm in o.data.materials]))
        if "--render" in argv:
            shots(o, key, (mn, mx))       # ⚠ 書き出しの前に撮る(後だと bbox が潰れる)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[kido] 書き出し " + os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    main()
