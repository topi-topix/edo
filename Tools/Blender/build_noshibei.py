"""**のし塀**(熨斗瓦を載せた白壁の袖塀)。岡部筑前守上屋敷の**結界**(表向と奥向を屋外で分ける)。

    blender --background --python Tools/Blender/build_noshibei.py -- <長さm> [<長さm>...] [--render]
    blender --background --python Tools/Blender/build_noshibei.py -- kekkai        # 指図の7本ぶんを一括

【なぜ新造するか】在庫の塀は**外構の練塀・築地塀・城塀**で、いずれも重い。指図 `kekkai` は
  「⛔ 外構の練塀より軽い**屋内の仕切り**」と明記していて(`assetCert`)、練塀を流用すると
  結界が外周と同じ格に見える。⛔ `Own.Dobei` / `Own.Tsuijibei` で代用しないこと。

【寸法は指図 `docs/Sashizu/okabe_sashizu.json` の `kekkai` が正典】
  高さ **h=1.8**(7本すべて)。⛔ 延長・据面・段差は指図の生成器が算出するのでここでは持たない。
  ⚠⚠ **run の長さは「開口の呼び寸法」では出ない。**棟梁は**据えた門・木戸の実メッシュ**を
  OBB で測り、その**外側**で塀を切る(`EdoOkabeYashikiBuilder.PlaceKekkai` / CLAUDE.md 規則5)。
  ⇒ 開口の呼び 2.727 で割った旧値は**どれも短すぎた**。実測(2026-09-04):
    中門 `Munamon_2.73` = **4.627**(⚠ **軒の出まで含む**ので開口より 1.90 広い)/
    木戸 `Kido_2.73` = **3.197** / `Kido_2.91` = **3.379**(いずれも方立柱2本ぶん広い)
  必要な長さ(2026-09-04 現在。⭕ 上の実測で割ったあとの実長):
    W1 **44.24 + 2.69**(中門で割れる)/ W2 3.636 / W3 5.454 / W4 1.818 /
    W5 **20.67**(木戸は端)/ W6 **53.67**(木戸は端)/ W7 1.818
  ⚠ 旧値 45.19 / 3.64(W1)・20.91(W5)・53.45(W6)の FBX は**消さない** — 参照が残りうる。
  ⚠ **開口(中門・木戸)はこの部材に含まれない。**中門は `Own.Munamon(2.727)`、
  木戸は `Own.Kido(2.727)` / `Own.Kido(2.909)`(`build_kido.py`)で焼いてある。

【作り】腰石(切石)→ 白漆喰の大壁 → **熨斗瓦の笠木**。
  ⭕ 笠木は Village Kit の `roof top x1`(冠瓦+熨斗瓦2段+紐が彫ってある実ジオメトリ)を
  そのまま継ぐ。⛔ 断面を押し出した箱に瓦の一点UVを貼らない — 無地の板になって、
  瓦場だけ実ジオメトリの他の建物から浮く(README「棟は箱で作らない」)。
  ⚠ `roof top x1` は**両端が開いている**ので、走りの端は漆喰で塗り籠めて塞ぐ。

【向きとピボット(Unity 座標)】幅=X(走り)/ 高さ=Y / 厚み=Z。
  ピボット = **走りの中心・地盤レベル・壁の芯**(⚠ 面ではなく芯。塀は表裏が同じ作りなので)。
  ⇒ `position = 区間の中点 / yaw = 走りの方位 / scale = Vector3.one` で置ける。

【⚠ 指図に無いので仮置き【U】】厚み 0.30 / 腰石の高さ 0.22 / 白壁の天端 1.53 /
  笠木の見え掛かり 0.27(合わせて 1.80)/ 控柱を 2間ごとに片側へ。
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as R
import build_obi_nagaya as N

KEN = 1.818
OUT = os.path.join(V.REPO, "Assets", "Edo", "Models", "Hei")
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD, WALL, STONE = N.WOOD, N.WALL, N.STONE

H     = 1.80        # 全高(指図 kekkai[].h)
T     = 0.30        # 厚み【U】
KOSHI = 0.22        # 腰石の天端【U】
WTOP  = 1.53        # 白壁の天端【U】
SEAT  = 0.05        # 笠木を壁へ食い込ませる量
CAP_W = 0.44        # 笠木の幅【U】(壁より両側へ 0.07 出る)

# 指図 kekkai の7本を、**据えた開口部材の実寸**で割った実長(2026-09-04 時点)。
# ⛔ 開口の呼び寸法で割らない — 棟梁は実メッシュの OBB で切る(docstring 参照)。
# ⚠ ファイル名は `fmt`(小数2桁)なので、ここも**丸めた値**を入れて名と形を一致させる。
KEKKAI = [44.24, 2.69, 3.636, 5.454, 1.818, 20.67, 53.67]
# 旧値(開口の呼びで割っていた頃)。⛔ 消さない — 参照が残りうるので FBX も残してある
KEKKAI_OLD = [45.190, 3.636, 20.907, 53.449]


def fmt(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def build(L, name=None):
    name = name or ("Noshibei_" + fmt(L))
    P = N.palette()
    hl, ht = L / 2.0, T / 2.0
    m = VM.Mesh()
    # ---- 腰石(切石。壁より両側へ 0.04 出す)
    m.box(-hl, hl, 0.0, KOSHI, -ht - 0.04, ht + 0.04,
          VM.sub(P['suv'], 0, 0, 1, 0.5), STONE)
    # ---- 白漆喰の大壁。⛔ 一点貼りにしない(矩形で貼って地の斑を出す)
    m.box(-hl, hl, KOSHI, WTOP, -ht, ht, VM.sub(P['cuv'], 0.02, 0.02, 0.98, 0.98), WALL)
    # ---- 腰石の天端の水切り(石と漆喰の継ぎ目を切る)
    for s in (-1, 1):
        m.box(-hl, hl, KOSHI, KOSHI + 0.06, s * (ht + 0.05) - s * 0.05, s * (ht + 0.05),
              VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80), WOOD)
    # ---- 控柱(2間ごとに片側へ)。⚠ 屋内の仕切りなので軽く、片側だけ
    n = max(0, int(L / (2 * KEN)))
    for i in range(1, n + 1):
        cx = -hl + L * i / (n + 1.0)
        m.box(cx - 0.075, cx + 0.075, 0.0, WTOP - 0.10, ht, ht + 0.10,
              VM.sub(P['wuv'], 0.12, 0.05, 0.40, 0.95), WOOD)

    body = m.to_object(name + "_body", [P['wood'], P['wall'], P['stone'], P['shoji']])

    # ---- 熨斗瓦の笠木。⭕ キットの実ジオメトリを継ぐ(⛔ 箱に一点UVを貼らない)
    show = H - WTOP                       # 壁の天端から上へ見える量 = 0.27
    pieces = R.ridge((-hl, 0.0, WTOP - SEAT), (hl, 0.0, WTOP - SEAT),
                     name + "_kasagi", w=CAP_W, h=show + SEAT)
    # ⚠ `roof top x1` は両端が開いている。塞がないと走りの端から笠木の中が透ける
    # ⚠ **1つの箱で塞がない。**熨斗(下・幅広)と冠瓦(上・幅狭で丸い)の2段になっているので、
    #   外形いっぱいの箱だと角が profile から飛び出し、逆に小さくすると天端に穴が残る
    #   (2026-09-04 に実見 — 白い箱の角が出たうえ、上に暗い切り欠きが残った)。**2段で詰める。**
    HH = show + SEAT
    for sx, sg in ((-hl, -1), (hl, 1)):
        for k, (fw, z0, z1) in enumerate((( 0.92, 0.00, 0.56), (0.66, 0.52, 0.96))):
            c = V.box(name + "_cap%s%d" % ("A" if sg < 0 else "B", k),
                      (0.05, CAP_W * fw, HH * (z1 - z0)),
                      (sx - sg * 0.030, 0.0, WTOP - SEAT + HH * (z0 + z1) * 0.5), P['wall'])
            V.set_uv_rect(c, VM.sub(P['cuv'], 0.1, 0.1, 0.9, 0.9), axes=('y', 'z'))
            pieces.append(c)
    V.dedup_materials()
    o = V.join([body] + pieces, name)
    V.set_origin(o, (0.0, 0.0, 0.0))
    V.sel([o])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o, name


def shots(o, key, box):
    V.hook_textures()
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = box
    c = (mn + mx) * 0.5
    L = mx.x - mn.x
    V.studio((c.x, mn.y - max(L, 4.0) * 0.9, c.z + 0.6), (c.x, c.y, c.z),
             ortho_scale=min(L, 14.0) * 1.1, res=(1700, 700))
    V.render(os.path.join(SHOT, "noshibei_%s_elev.png" % key))
    V.studio((mn.x - 2.2, mn.y - 3.2, 1.62), (c.x, c.y, 0.9), res=(1600, 1000))
    V.render(os.path.join(SHOT, "noshibei_%s_3d.png" % key))
    # 走りの端の寄り — **笠木の小口が透けていないか**をここで見る
    V.studio((mn.x - 1.6, mn.y - 1.4, 2.35), (mn.x + 0.9, c.y, 1.5), res=(1500, 1000))
    V.render(os.path.join(SHOT, "noshibei_%s_end.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "kekkai" in argv:
        lens = list(KEKKAI)
    else:
        lens = [float(a) for a in argv if not a.startswith("--")] or [5.454]
    for L in lens:
        V.reset()
        o, name = build(L)
        mn, mx = V.bbox([o])
        print("[noshibei] %-20s Unity実寸 W(X)=%.3f  H(Y)=%.3f  D(Z)=%.3f  底=%.3f  面=%d  材質=%s"
              % (name, mx.x - mn.x, mx.z - mn.z, mx.y - mn.y, mn.z, len(o.data.polygons),
                 [mm.name for mm in o.data.materials]))
        if "--render" in argv:
            shots(o, fmt(L), (mn, mx))    # ⚠ 書き出しの前に撮る(後だと bbox が潰れる)
        V.export_fbx([o], os.path.join(OUT, name + ".fbx"))
        print("[noshibei] 書き出し " + os.path.join(OUT, name + ".fbx"))


if __name__ == "__main__":
    main()
