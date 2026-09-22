"""**類型共用の庫裏(くり)** — 寺の台所兼住居。2寸法(6×4間 / 5×3.5間)。

    blender --background --python Tools/Blender/build_typ_kuri.py -- [--render]
    blender --background --python Tools/Blender/build_typ_kuri.py -- kuri6 --render
    (名前を省くと両方。kuri6 = 6×4間 / kuri5 = 5×3.5間)

【なぜ新造するか】EDO-0354(在庫方の照会 2026-09-22)。
  いま庫裏に当てている `EdoAssets.VK.SmallHouse` は実測 **14.49 × 10.49m(≒8×5.8間)**で、
  本堂 7×6間とほぼ同大。成満寺 248 坪ほか狭い境内 3〜4 区画で「収まらず未建」になる。
  在庫方が村のキットと江戸暦を総当たりして、**これより小さい住居の完成駒は在庫に無い**
  (下限がこの駒)と判定した。

【姿 — 本堂より格を落とす】
  ・**平屋・切妻の平入・瓦葺き**。⛔ 入母屋にしない(入母屋は本堂と鐘楼の格)。
  ・**梁間は浅く桁行は長い。**⛔ 正方形に近づけない — 寛文8年(1668)の令が中小寺院の
    堂舎の**梁間を京間3間に制限し、桁行は自由・庇で延ばす**と定めている
    (高崎藩「寺院作事願間数之事」・光井渉『建築史学』22)【確度 A/B・考証方】。
  ・妻に**煙出し**(庫裏の目印。台所の煙を抜く連子)。
    ⚠ **見掛けの煙出し**で、屋内へ抜ける穴は開けていない【U】— 躯体は一体メッシュで、
      穴を開けると妻壁の三角を割ることになる。引きでは読めない。

【⭐ 屋根を別の駒にしてある(この部材の主眼・EDO-0354)】
  焼いた FBX は **`<名前>_body`(躯体)と `<名前>_yane`(屋根)の2オブジェクト**。
  `EdoBuild.IsRoofName` の篩(yane/noki/taruki/mune/keta)に `_yane` が掛かるので、
  **`EdoBuild.Body(go, n, withRoof:false)` が屋根を落とす** = 「軒は境界を越えてよい・
  壁体は 2m 内側」の置き方の決まりがこの駒で初めて効く。
  ⚠ **けらば裏板と破風板も屋根の側**へ寄せてある(`build_obi_nagaya.gable_set(m_eave=)`)。
    躯体に残すと壁体の bbox が **Z に ±軒の出・X に ±(けらば+見付)** 太って、
    篩を通しても「壁体」が軒のまま出る。
  ⛔ `IsRoofName` の篩を広げない。名前をこちらで篩に合わせる(EdoBuildGoten と同じ手)。

【向き(Unity 座標)】幅=X(**桁行**)/ 高さ=Y / 厚み=Z(**梁間**)。**+Z = 平入の正面**。
  ピボット = **足形の中心・床(地盤)レベル**。⚠ 軒は足形の外へ ±Z に軒の出・±X にけらば出る。
  ⚠ **土間口(大戸)は Unity +X 寄り**(`VM.Mesh` の論理走りは Unity X が反転する)。
    左右非対称なので、据えるときの yaw で土間口の向きが変わる。

【材】⛔ 新規に作らない。倣った先(岡部の長屋)の材質名をそのまま運ぶ —
  `wood` / `wall C` / `Foundation_A_01` / `wall A` / `roof` / `roof ornaments`。
  Unity 側は **Edo ▸ 類型 ▸ 新造部材のマテリアルをremap**(`Models/Jisha` を見ている)。

【⛔ 踏んだ罠(README と memory から先回りしたもの)】
  ・`OB.shitami` は out<0 のとき `m.box` に z0>z1 を渡すので**躯体の裏面・妻面が内向き**で
    焼ける(EEVEE は裏面も描くのでレンダでは気づけない・Unity で消える)⇒ `_recalc`。
    **数えてから直す**(`_skin_audit`)— recalc が効いたことを数で残す。
  ・`clip_convex` の bisect は**孤立頂点を残す** ⇒ 測る前に `_clean_loose`。
  ・軒の出は bbox から取れない(破風板が Z へ出る)⇒ 屋根の駒の bbox と足形の差で出す。

【⛔⛔ 2026-09-22 の差し戻し「棟の真上に空が抜ける」— 原因は**二つ**あった】
  ⑴ **棟モジュールが鏡像で置かれていて、巻き順が裏返ったまま焼かれていた。**
     `build_goten_roof._frame` は `side = ax × Z` の取り方のせいで**行列式 −1 の左手系**
     (実測 det −1.83)。Blender は行列式が負のオブジェクトを描くとき法線を補正するので
     **レンダでは完全に正常に見える**が、`V.join` で行列式 +1 の瓦場へ join した瞬間に
     鏡だけが焼かれ、**大棟・隅棟・袖瓦が丸ごと裏面**になる ⇒ Unity で消える。
     ⭕ `_frame(ax, rh=True)`(`side = Z × ax`)で右手系に取り直した。棟モジュールは
       **y 鏡のずれ 0.000000m の完全対称**なので姿は変わらない(頂点の動きは
       `RIDGE_W` の丸め由来の **最大 0.20mm** のみ・実測)。
     ⚠ 同じ `_frame` を使う `oni()`(鬼瓦)も裏返っているが、あちらのモジュールは
       **y 鏡で 0.415m ずれる非対称**なので同じ手では直せない ⇒ 掲示板 **EDO-0375**。
  ⑵ **大棟の小口を「内接する箱」で塞いでいた。**棟は両端の開いた管なので、塞ぎ残した
     **天端 0.108m・両脇 0.042m** が反対の端まで素通しになっていた。
     ⭕ `OB.koguchi` で**断面の輪郭そのもの**を面にして塞ぐ(袖瓦の軒先側も同じ)。
     ⚠ 小口は**閉じた環ではなく弧** — `roof top x1` は底を張っていない開いた帯なので、
       `holes_fill` に弧を渡しても 0 面しか返らない。**底を弦で閉じて**多角形にする。
【⛔ この2つはどちらも「見て」では出ない】
  EEVEE は裏面も描き、裏面カリングを掛けても**背景が空と同じ灰色**なので穴が影に見える。
  ⇒ `_sukashi_audit`(光線で数える)と `shots` の ⑦**マゼンタの穴探し**を必ず通す。
"""
import bpy, sys, os, math, mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vklib as V
import vkmesh as VM
import build_goten_roof as R
import build_obi_nagaya as OB

KEN  = 1.818
OUT  = V.out_dir(os.path.join(V.REPO, "Assets", "Edo", "Models", "Jisha"))
SHOT = os.path.join(V.REPO, "Screenshots")
WOOD, WALL, STONE, SHOJI = OB.WOOD, OB.WALL, OB.STONE, OB.SHOJI


# ═════════════════════════════ 割付 ═════════════════════════════
def kuri_plan(wKen, ura=False):
    """平入の正面(+Z)の割付。**土間口(大戸)→ 明かり窓 → 居室の戸 → 窓**の順で、
    余りを等分に振って柱間の壁にする。

    ⚠ 戸の数・位置は【U】— 庫裏の間取りの史料は当プロジェクトに無い。庫裏が
      「土間(台所)+ 居室」で、土間口が大きいという**作りの型**だけを置いている。
    <paramref name="ura"/> = 背面(−Z)。⛔ 盲面にしない — 10.9 × 2.9m の白一面になる
      (2026-09-21 に土蔵で踏んだ「長手の大壁が意匠の無い箱に見える」型)。台所の
      背面なので明かり窓だけ並べる。"""
    W = wKen * KEN
    if ura:
        items = [('window', 1.0), ('window', 1.0)] + ([('window', 1.0)] if wKen >= 5.5 else [])
    else:
        items = [('door', 1.5), ('window', 1.0), ('door', 0.75)]
        if wKen >= 5.5:
            items.append(('window', 1.0))
    used = sum(k for (_t, k) in items) * KEN
    pad = (W - used) / float(len(items) + 1)
    plan, x = [], -W / 2.0
    for (t, k) in items:
        x += pad
        plan.append((x, x + k * KEN, t))
        x += k * KEN
    return plan


# ═════════════════════════════ 煙出し ═════════════════════════════
def kemudashi(m, P, hw, hd, apex, half=0.55, h=0.50, drop=0.38):
    """**煙出し**(妻の連子)。両妻の棟寄りに、屋根面の下へ収まる連子を伏せる。

    ⚠ **見掛け**(貫通していない)【U】。躯体は面ごとに四角を積む一体メッシュなので、
      三角の妻壁に穴を開けるには妻壁を4枚に割ることになる。板を背に当てて連子を前へ
      並べ、上に小さな水切りを打つ。引き・目の高さのどちらからも煙出しに読める。
    ⛔ 連子を**板1枚で貼らない**(`Mesh.koshi` と同じ理由)— 竪子を実体で並べる。
    ⚠ `Mesh.koshi` は竪子を**必ず走り(X)方向へ並べる**。ここは妻(走りが Z)なので
      手で並べる(鐘楼の高欄で 2026-09-21 に踏んだ型)。"""
    top = apex - drop
    y0, y1 = top - h, top
    # 屋根面(妻の内側)は |z| が増えるほど下がる。連子の上端が屋根面を突かないこと
    assert top < apex - half * R.RATIO, "煙出しの天端が屋根面を突く"
    duv = VM.sub(P['wuv'], 0.62, 0.05, 0.78, 0.95)     # 背板(暗い帯)
    kuv = VM.sub(P['wuv'], 0.60, 0.10, 0.95, 0.90)     # 連子
    fuv = VM.sub(P['wuv'], 0.30, 0.55, 0.85, 0.80)     # 額縁・水切り
    for sx in (-hw, hw):
        s = 1.0 if sx > 0 else -1.0
        def xr(a, b):
            """壁面からの出 a..b を、その妻の外向きへ。⛔ z0>z1 を作らない(法線が内向く)"""
            return tuple(sorted((sx + s * a, sx + s * b)))
        # 背板(暗い板を壁面に当てる。漆喰の白の上なので「口」に見える)
        a0, a1 = xr(-0.005, 0.02)
        m.box(a0, a1, y0, y1, -half, half, duv, WOOD)
        # 連子(竪子)。走りが Z なので手で並べる
        n = max(3, int((2 * half) / 0.115))
        b0, b1 = xr(0.02, 0.075)
        for i in range(n):
            cz = -half + 2 * half * (i + 0.5) / n
            m.box(b0, b1, y0 + 0.03, y1 - 0.03, cz - 0.026, cz + 0.026, kuv, WOOD)
        # 額縁(四周)
        c0, c1 = xr(0.0, 0.09)
        m.box(c0, c1, y0 - 0.06, y0, -half - 0.06, half + 0.06, fuv, WOOD)
        m.box(c0, c1, y1, y1 + 0.06, -half - 0.06, half + 0.06, fuv, WOOD)
        for cz in (-half - 0.03, half + 0.03):
            m.box(c0, c1, y0 - 0.06, y1 + 0.06, cz - 0.03, cz + 0.03, fuv, WOOD)
        # 小庇(水切り)。⛔ **0.13 を超えない** — 超えると煙出しが**壁体の bbox の端**になり、
        #   足形(基壇 ±0.13)より外で「壁体の幅」が決まってしまう(2026-09-22 に 0.20 で焼いて実見)
        d0, d1 = xr(0.0, 0.13)
        m.box(d0, d1, y1 + 0.06, y1 + 0.12, -half - 0.12, half + 0.12, fuv, WOOD)
    return m


def tsuma_posts(m, P, hw, hd, koshiH, eaveH):
    """**妻の柱を増やす。**⛔ 省かない — `OB.build` は妻に柱を3本しか立てないので、
    梁間4間(7.27m)だと漆喰が **3.6 × 1.8m の白い板2枚**になり、意匠の無い箱に見える
    (2026-09-21 に土蔵で踏んだ「長手の大壁が白一面」と同じ型。2026-09-22 に焼いて実見)。
    ⇒ 平の面と同じ**1間見当**まで割る。"""
    for sx in (-hw, hw):
        s = 1.0 if sx > 0 else -1.0
        n = max(1, int(round(2 * hd / KEN)))
        xs = [-hd + 2 * hd * i / float(n) for i in range(1, n)]
        xs = [z for z in xs if min(abs(z), abs(abs(z) - (hd - 0.25))) > 0.12]
        OB.posts(m, P, xs, koshiH, eaveH, sx, s, 'z')
    return m


# ═════════════════════════════ 掃除と検め ═════════════════════════════
def _shell_fix(o, label=""):
    """**裏返った箱を殻ごと取り直す。**⛔ `recalc_face_normals` を使わない・⛔ 頂点を溶接しない。

    【なぜ既定の2手が効かないか — 2026-09-22 に両方измерして捨てた】
      ① `bmesh.ops.recalc_face_normals` … `VM.Mesh` は**面ごとに頂点を分けて**積むので、
         箱は「6枚のバラバラの四角」で、どちらが外かの手掛かりが無い。
         実測 **内向き 450 → 492(増えた)**。
      ② `remove_doubles` で溶接してから取り直す … 下見板は壁面と**面が完全に重なる**ので、
         溶接が重複面ごと消す。実測 **面 3248 → 2798(450 枚が消滅)**。⛔ 幾何が痩せる。

    【この関数のやり方】`VM.Mesh` の面は **`box()` / `section()` が6枚ずつ連続で積む**。
      ⇒ 連続6枚が**閉じた殻**(各有向辺がちょうど1回・逆向きも1回)なら1個の立体と見て、
      **符号付き体積**を出す。負なら裏返しなので6枚とも巻きを反転する。閉じていなければ
      1枚進めてやり直す(`hboard` が箱のあとに木理用の四角を1枚挟むため)。
      残った1枚物は、**同じ4隅を持つ面**(`hboard` の木理の四角は箱の外面と完全に重なる)に
      法線を揃える。
    ⚠ 瓦場(キット由来)は元から正しい。連続6枚が閉じることは事実上無いので素通りする。"""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    F = bm.faces[:]
    key = lambda v: (round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6))
    KS = [[key(v) for v in f.verts] for f in F]

    def orient(idx):
        """連続6枚が**閉じた殻**なら、面ごとの向き(+1/−1)を返す。閉じていなければ None。
        ⚠ 有向辺の一意性では見ない — `OB.section` は**蓋と側面の巻きが食い違っている**ので
          (2026-09-22 に実測)有向で見ると殻として拾えない。**無向の辺が必ず2回**で殻と見て、
          共有辺の**走る向きが同じなら裏表が違う**として orientation を伝播させる。"""
        e = {}
        for i in idx:
            ks = KS[i]
            for a, b in zip(ks, ks[1:] + ks[:1]):
                e.setdefault(frozenset((a, b)), []).append((i, a, b))
        if any(len(v) != 2 for v in e.values()):
            return None
        sg, q = {idx[0]: 1}, [idx[0]]
        while q:
            i = q.pop()
            for a, b in zip(KS[i], KS[i][1:] + KS[i][:1]):
                (fa, aa, _), (fb, ba, _) = e[frozenset((a, b))]
                j, same = (fb, ba == a) if fa == i else (fa, aa == a)
                want = -sg[i] if same else sg[i]
                if j in sg:
                    if sg[j] != want:
                        return None            # 向きが矛盾する = 殻ではない
                else:
                    sg[j] = want; q.append(j)
        return sg if len(sg) == len(idx) else None

    def vol(idx, sg):
        s = 0.0
        for i in idx:
            p = [v.co for v in F[i].verts]
            if sg[i] < 0:
                p = p[::-1]
            for t in range(1, len(p) - 1):
                s += p[0].dot(p[t].cross(p[t + 1]))
        return s / 6.0

    used, flipped, shells, i = set(), 0, 0, 0
    while i + 6 <= len(F):
        idx = list(range(i, i + 6))
        sg = orient(idx)
        if sg is None:
            i += 1
            continue
        shells += 1
        if vol(idx, sg) < 0.0:
            sg = dict((k, -v) for k, v in sg.items())
        for j in idx:
            if sg[j] < 0:
                F[j].normal_flip(); flipped += 1
        used.update(idx)
        i += 6
    # 1枚物(`hboard` の木理の四角)は、同じ4隅の面に法線を揃える
    bycorner, lone = {}, 0
    for j in used:
        bycorner.setdefault(frozenset(KS[j]), []).append(j)
    for j in range(len(F)):
        if j in used:
            continue
        tw = bycorner.get(frozenset(KS[j]))
        if tw and F[j].normal.dot(F[tw[0]].normal) < 0.0:
            F[j].normal_flip(); lone += 1
    bm.to_mesh(o.data); bm.free(); o.data.update()
    print("[kuri]   %-10s 殻 %d 個(面 %d 枚を反転)/ 1枚物 %d 枚を揃えた"
          % (label, shells, flipped, lone))


def _clean_loose(o):
    """孤立頂点を落とす。⚠ `clip_convex` の bisect は面の無い頂点を残すので、
    掃除しないと bbox が実形状より大きく出る(README「bisect は孤立頂点を残す」)。"""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bm.to_mesh(o.data); bm.free(); o.data.update()


def _sukashi_audit(objs, label, band=0.30):
    """**棟の小口が素通しになっていないかを光線で数える**(2026-09-22・EDO-0354)。

    ⛔ **レンダで済ませない。**棟は両端の開いた管で、開いた所は反対の端まで抜ける。
      EEVEE は裏面も描くので普通のレンダでは塞がって見え、裏面カリングを掛けても
      背景が空と同じ灰色なので**目では読めなかった**(背景をマゼンタにして初めて出た)。
    ⇒ 棟の断面を格子で撃ち抜いて、**一度も当たらない光線の数**を出す。0 でなければ穴。

    ⛔⛔ **「当たらなかった」だけでは穴にならない。**棟の幅の外は**空**なので、素直に数えると
      棟が完全に塞がっていても数百本が「抜け」と出る(2026-09-22 に ±0.30m を一律に撃って
      263/868 と刷り、直っているのに ⛔ に見えた)。
      ⇒ **その (y,z) が中ほど(x=0)で屋根の皮より下にあるか**を先に上から撃って確かめ、
        **中に入っている格子だけ**を数える。外の空は最初から勘定に入れない。
    <paramref name="band"/> = 棟の軸(Unity X)まわりに見る半幅[m]。"""
    dg = bpy.context.evaluated_depsgraph_get()
    mn, mx = V.bbox(objs)
    miss = tot = 0
    worst = None
    # 大棟の天端付近(z は上から 0.55m ぶん)・軸まわり ±band を 2cm 刻みで撃つ
    z0, z1 = mx.z - 0.55, mx.z - 0.004
    y = -band
    while y <= band + 1e-9:
        # 中ほどの皮の高さ(ここより下なら「部材の中」)
        ok, top, _n, _i, _o, _m = bpy.context.scene.ray_cast(
            dg, mathutils.Vector((0.0, y, mx.z + 2.0)), mathutils.Vector((0.0, 0.0, -1.0)))
        skin = top.z if ok else -1e9
        z = z0
        while z <= z1 + 1e-9:
            if z < skin - 0.004:
                org = mathutils.Vector((mn.x - 4.0, y, z))
                hit, loc, _n, _i, _o, _m = bpy.context.scene.ray_cast(
                    dg, org, mathutils.Vector((1.0, 0.0, 0.0)))
                tot += 1
                if not hit:
                    miss += 1
                    if worst is None or z < worst[1]:
                        worst = (y, z)
            z += 0.02
        y += 0.02
    print("[kuri] %-20s 棟の素通し %d / %d 本%s"
          % (label, miss, tot,
             ("  ⛔ 一番低い抜け y=%.2f z=%.3f" % worst) if worst else "  ⭕"))
    return miss


def _skin_audit(o):
    """**一番外の面が外を向いているか数える。**⛔ レンダでは判らないので数で出す。

    ⚠⚠ **「壁面の近く」で数えない。**下見板は厚み 0.03〜0.075 なので、板の**裏面**まで
      外皮に数えてしまい、正しく直っていても半分が「内向き」と出る
      (2026-09-22 に一度そう読んで、直っている物を ⛔ と刷った)。
    ⇒ **bbox の端の平面ちょうど(±1mm)に載る面だけ**を見る。そこに載る面は必ず
      「外から見える一番外の皮」なので、外向き以外はあり得ない。

    ⛔⛔ **世界座標で数える。**`V.bbox` は世界、`v.co` は局所なので混ぜてはいけない。
      `R.ridge` の `_frame` は**行列式 −1 の基底**(ax, ax×Z, …)で棟モジュールを置くので、
      屋根の行列には **鏡**が残っている(実測 det = −1.83)。局所の法線を世界の bbox に
      当てると裏表がまるごと反転し、**直っている屋根が「外皮の内向き 20/20 ⛔」と出た**
      (2026-09-22。この偽陽性を穴の原因と読み違えかけた)。
      ⇒ ここは世界で読み、呼ぶ側は **`transform_apply` で鏡を焼いてから**数える。
    戻り値 (内向きの数, 見た面の数)。"""
    mn, mx = V.bbox([o])
    bad = tot = 0
    co = [o.matrix_world @ v.co for v in o.data.vertices]
    for pg in o.data.polygons:
        # ⛔ `pg.normal` を信じない(反転の直後は古い値が残ることがある)。頂点の並びから出す
        vs = [co[i] for i in pg.vertices]
        n = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if n.length < 1e-9:
            continue
        n = n.normalized()
        c = sum(vs, mathutils.Vector((0.0, 0.0, 0.0))) / float(len(vs))
        for (cv, nv, lo, hi) in ((c.x, n.x, mn.x, mx.x), (c.y, n.y, mn.y, mx.y)):
            for (lim, sg) in ((lo, -1.0), (hi, 1.0)):
                if abs(cv - lim) < 0.001 and abs(nv) > 0.5:
                    tot += 1
                    if nv * sg < 0.0:
                        bad += 1
    return bad, tot


# ═════════════════════════════ 部材 ═════════════════════════════
def kuri(wKen=6.0, dKen=4.0, eaveH=2.85, noki=0.90, ridge_show=0.36, end=0.36,
         kemu=(0.55, 0.50, 0.38), name=None):
    """庫裏 1棟。桁行 <paramref name="wKen"/> 間 × 梁間 <paramref name="dKen"/> 間(外形)。

    戻り値は **(躯体, 屋根) の2オブジェクト**(`OB.build(split=True)`)。
    軒桁 = <paramref name="eaveH"/>、棟天端は瓦の勾配 0.5456 からの**従属値**。"""
    name = name or ("Typ_Kuri_%sx%sken" % (OB.fmt(wKen), OB.fmt(dKen)))
    P = OB.palette()                    # ⭐ 先に借りる(build 側の palette は同じ材を返す)
    hw, hd = wKen * KEN / 2.0, dKen * KEN / 2.0
    roofZ = eaveH - noki * R.RATIO
    apex = roofZ + (hd + noki) * R.RATIO

    body, roof = OB.build(wKen, dKen, name, eaveH=eaveH, ridge_show=ridge_show,
                          plan=kuri_plan(wKen), plan_b=kuri_plan(wKen, ura=True),
                          koshiH=1.05, noki=noki, end=end, uchinori=1.95, split=True)
    # 煙出しは躯体へ足す(屋根の篩に掛けない — 壁体の一部)
    km = VM.Mesh()
    kemudashi(km, P, hw, hd, apex, half=kemu[0], h=kemu[1], drop=kemu[2])
    tsuma_posts(km, P, hw, hd, 1.05, eaveH)
    ko = km.to_object(name + "_kemu", [P['wood'], P['wall'], P['stone'], P['shoji']])
    V.dedup_materials()
    body = V.join([body, ko], name + "_body")

    _clean_loose(roof)
    # ⭐⭐ **数える前に鏡を焼く**(2026-09-22)。⛔ 順を戻さない —
    #   屋根の行列には `R.ridge` の `_frame`(行列式 −1)由来の鏡が乗っている。
    #   焼く前に局所の巻きを見ると裏表が全部逆に読め、`_shell_fix` が**正しい殻を
    #   わざわざ裏返し**、`_skin_audit` が**直っている屋根を ⛔ と刷る**。
    #   `transform_apply` は負のスケールを焼くとき巻き順も直すので、ここから先は
    #   局所 = 世界 = Unity の見え方になる。
    for o in (body, roof):
        V.set_origin(o, (0.0, 0.0, 0.0))
        V.sel([o]); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for o, lab in ((body, "躯体"), (roof, "屋根")):
        n0 = len(o.data.polygons)
        bad0, tot = _skin_audit(o)
        _shell_fix(o, lab)
        bad1, _ = _skin_audit(o)
        print("[kuri] %-20s %s 外皮の内向き %d → %d(外皮 %d 面)/ 面 %d → %d %s"
              % (name, lab, bad0, bad1, tot, n0, len(o.data.polygons),
                 "⭕" if (bad1 == 0 and len(o.data.polygons) == n0) else "⛔ 残っている"))
    _sukashi_audit([body, roof], name)
    print("[kuri] %-20s 軒桁 %.3f / 瓦面の大棟 %.3f / 軒の出 %.2f / けらば %.2f"
          % (name, eaveH, apex, noki, end))
    return body, roof, name


PARTS = {
    # 寺の庫裏(250〜300坪級・塔頭)。桁行6間 × 梁間4間
    "kuri6": lambda: kuri(6.0, 4.0, eaveH=2.85, noki=0.90, ridge_show=0.36, end=0.36,
                          kemu=(0.60, 0.55, 0.40)),
    # 坊(山王の社僧十坊)の庫裏。桁行5間 × 梁間3.5間 — 一回り低く軒も浅い
    "kuri5": lambda: kuri(5.0, 3.5, eaveH=2.70, noki=0.80, ridge_show=0.30, end=0.30,
                          kemu=(0.50, 0.46, 0.34)),
}


# ═════════════════════════════ レンダ ═════════════════════════════
def shots(objs, key, cull=True):
    """⚠ **書き出しの前に撮る**。⛔ 地面を z=0 に敷いて足元の浮き・埋まりを読む。

    ⭐⭐ <paramref name="cull"/>(既定 True)で**全材に裏面カリングを掛ける** — これが
      Unity の見え方。⛔ 掛けずに刷らない: EEVEE は既定で裏面も描くので、裏返った壁が
      **レンダでは普通に見えて Unity でだけ消える**(memory: mesh-box-inward-normals)。
      掛けて壁が抜けなければ、法線は Unity でも通る。"""
    V.hook_textures()
    if cull:
        for mm in bpy.data.materials:
            mm.use_backface_culling = True
    os.makedirs(SHOT, exist_ok=True)
    mn, mx = V.bbox(objs)
    c = (mn + mx) * 0.5
    W, H, D = mx.x - mn.x, mx.z - mn.z, mx.y - mn.y
    r = max(W, H, D)
    bpy.ops.mesh.primitive_plane_add(size=max(60.0, r * 10), location=(c.x, c.y, 0.0))
    # ① 平入の正面の立面(**表は Blender の −Y**。`to_object` が厚みを反転している)
    V.studio((c.x, mn.y - r * 2.2, c.z), (c.x, c.y, c.z),
             ortho_scale=max(W, H) * 1.15, res=(1700, 1150))
    V.render(os.path.join(SHOT, "typ_kuri_%s_elev.png" % key))
    # ② 妻の立面 — **煙出しと妻壁の納まり・梁間の浅さ**をここで見る
    V.studio((mn.x - r * 2.2, c.y, c.z), (c.x, c.y, c.z),
             ortho_scale=max(D, H) * 1.15, res=(1350, 1150))
    V.render(os.path.join(SHOT, "typ_kuri_%s_gable.png" % key))
    # ③ 正面を斜め前から(人の目の高さ)— 土間口・下見板・軒の出
    V.studio((mn.x - r * 0.6, mn.y - r * 1.05, 1.62), (c.x, c.y, H * 0.45), res=(1700, 1050))
    V.render(os.path.join(SHOT, "typ_kuri_%s_3d.png" % key))
    # ④ 背面を斜めから — **明かり窓が漏れていないか・裏が白一面でないか**
    V.studio((mx.x + r * 0.6, mx.y + r * 1.05, 1.85), (c.x, c.y, H * 0.45), res=(1700, 1050))
    V.render(os.path.join(SHOT, "typ_kuri_%s_ura.png" % key))
    # ⑤ 煙出しの寄り — 連子・額縁・小庇・けらばとの当たり
    V.studio((mn.x - D * 0.9, mn.y - D * 0.55, H * 0.92), (mn.x + 0.2, c.y, H * 0.80),
             res=(1400, 1100))
    V.render(os.path.join(SHOT, "typ_kuri_%s_kemu.png" % key))
    # ⑥ 棟の寄り(上から)— 大棟・袖瓦・瓦の段が通っているか
    V.studio((c.x, mn.y - r * 0.5, H + r * 0.45), (c.x, c.y, H * 0.88), res=(1500, 950))
    V.render(os.path.join(SHOT, "typ_kuri_%s_mune.png" % key))
    # ⑦⭐ **穴探し** — 背景を**マゼンタ**にして棟端を正対の寄りで刷る。
    #   ⛔ 既定の灰青の空で穴を探さない: 漆喰も瓦も灰色なので、抜けていても
    #     「影になった面」に見える(2026-09-22 に ⑥ まで刷って見落とした)。
    #   地の面が1画素でもマゼンタなら、そこは Unity で空が抜ける。
    V.studio((mn.x - 20.0, c.y, mx.z - 0.55), (mn.x, c.y, mx.z - 0.55),
             ortho_scale=2.6, res=(1400, 1000))
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1.0, 0.0, 1.0, 1.0)
    V.render(os.path.join(SHOT, "typ_kuri_%s_anasagashi.png" % key))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = [a for a in argv if not a.startswith("--") and a in PARTS] or list(PARTS.keys())
    for key in want:
        V.reset()
        body, roof, name = PARTS[key]()
        bmn, bmx = V.bbox([body])
        amn, amx = V.bbox([body, roof])
        nf = len(body.data.polygons) + len(roof.data.polygons)
        nv = len(body.data.vertices) + len(roof.data.vertices)
        print("[kuri] %-20s 屋根込 W(X)=%6.3f H(Y)=%6.3f D(Z)=%6.3f 底=%+.3f"
              % (name, amx.x - amn.x, amx.z - amn.z, amx.y - amn.y, amn.z))
        print("[kuri] %-20s 壁 体 W(X)=%6.3f H(Y)=%6.3f D(Z)=%6.3f 底=%+.3f"
              % (name, bmx.x - bmn.x, bmx.z - bmn.z, bmx.y - bmn.y, bmn.z))
        print("[kuri] %-20s 頂点 Body(true)=%d(躯体 %d + 屋根 %d)/ Body(false)=%d / 面 %d"
              % (name, nv, len(body.data.vertices), len(roof.data.vertices),
                 len(body.data.vertices), nf))
        print("[kuri] %-20s 駒=%s / 材質=%s"
              % (name, [body.name, roof.name],
                 sorted(set([mm.name for mm in body.data.materials]
                            + [mm.name for mm in roof.data.materials]))))
        if "--render" in argv:
            shots([body, roof], key)
        V.export_fbx([body, roof], os.path.join(OUT, name + ".fbx"))
        print("[kuri] 書き出し " + os.path.join(OUT, name + ".fbx"))


# ⚠ ガードを付けてある(2026-09-22)。⛔ 外さない —
#   外すと**診断スクリプトから import しただけで FBX が焼ける**。
#   `blender --background --python <file>` は __name__ == "__main__" で走るので
#   コマンドラインの動きは 1mm も変わらない(`build_obi_nagaya` と同じ作法)。
if __name__ == "__main__":
    main()
