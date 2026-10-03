// 山王権現社 — 指図と実装を突き合わせる(2026-09-09 棟梁)
//
// 【これは物差しであって実装ではない】建てない・直さない・動かさない。読むだけ。
//   ⭐ 新設の理由: 図と実装の差が **検図5巡目から22巡目まで17巡ぶん測られないまま**で、
//     22巡目になって初めて「女坂が参道軸の反対側にある」= +10m の平行移動では説明できない
//     差が人手の grep で出た(掲示板 EDO-0181)。規則19「欠陥はそれが見える**最も安い輪**で
//     捕まえる」— その輪がこの menu。
//
// 【なぜ汎用の器(EdoSashizuExport.CheckScene)に一行足すだけで済まないか】
//   汎用の器は**回転間グリッド式(grid.shukaku)の武家屋敷スキーマ**専用で、棟・廊下・囲い run・
//   郭内の造作(Fuzoku 下)・区画(EdoParcels)を前提にしている。山王は
//     ・グリッドが**世界軸に平行**(grid.keidai / x = x0 + u×ken / z = z0 + v×ken)
//     ・名簿が**社殿・門・鳥居・石段・囲い・造成の面・社叢**で、Fuzoku も郭も無い
//     ・区画は社地の 20点多角形で、辺+s の表門を持たない
//   ⇒ 器の側に山王用の照合を足す(EdoSashizuExport.CheckScene が id=="sanno" でここへ回す)。
//
// 【正典】
//   設計値 … docs/Sashizu/sanno_sashizu.json      (EdoSannoShaBuilder.SashizuRel)
//   算出物 … docs/Sashizu/sanno_impl.json         (EdoSannoShaBuilder.ImplRel)
//            ⛔ 算出物は指図ではない。指図から**従属して出た値**(門の芯・石段の折れ線の
//            世界座標・撒いた木 1,794本の world)。⛔ 実装から指図を作らない(規則2)。
//   ⛔ **値をこの C# に写さない**(規則11/12)。ここが持ってよいのは
//      ①物差し(許容差)②**指図の名 → シーンの名**の対応表 だけで、寸法は一つも持たない。
//
// 【対応表について(申し送り)】
//   実装は社殿を `Honden`/`Haiden`… と**ローマ字**で名づけており、指図の名(本殿・拝殿…)と
//   直接は突き合わない。ここでは**綴りの読み替えだけ**を対応表に置く(同定の判断は入れない —
//   例えば実装の `Hozo`(宝蔵)を指図の「御蔵」に結ぶのは**同定**なので結ばない。結ばなければ
//   「指図にあって実装に無い」+「孤児」の対で出るので、どちらにせよ人の目に見える)。
//   ⭐ 本来は**実装が指図の名で据える**のが筋。対応表が消えるのが正しい終点。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class EdoSannoSashizuCheck
{
    public const string Id = "sanno";

    // ---- 物差し(⛔ 設計値ではない。位置・向きの二つと、算出物が持つ地形の一つ)----
    /// <summary>位置・寸法の許容差[m]。**汎用の器 `EdoSashizuExport.CheckScene` と同じ 0.02m**
    /// を借りる(⛔ 山王のためだけの緩い数を新しく作らない)。</summary>
    const float POS_TOL_M = 0.02f;
    /// <summary>囲いの駒を「この区間の駒」とみなす、線からの横の距離の上限[m]。これより遠い駒は
    /// 口の縁の駒(門の脇柱の角へ取り付いて線から外れる。勝手口の脇で 1.03m)か、線から外れて建った駒。
    /// ⚠ 閾値は横ずれの判定ではない — 判定は <see cref="POS_TOL_M"/>。これは駒を区間へ割り付けるだけ。</summary>
    const float RIM_LAT_M = 1.5f;
    /// <summary>造成の面の標本で、輪郭から外す帯[m](地形 2 m/px では輪郭ちょうどに面の縁を置けない)。</summary>
    const float RIM_MARGIN_M = 0.5f;
    /// <summary>地形と設計面の許容差[m]は**算出物が持つ**(`checks.gradeTol`)。⛔ ここに写さない。</summary>
    /// <summary>向き(駒の Y 回転)の許容差[度]。⛔ 設計値ではない — 駒は度で直に据わるので、
    /// **丸めの幅**として 0.5° を採る(指図の yaw は 0.1° 刻みで出る)。</summary>
    const float YAW_TOL_DEG = 0.5f;

    static readonly string[] SECTIONS = { "社殿", "門・鳥居", "石段", "囲い", "造成の面", "社叢" };

    // ---- 指図の名 → シーンの名(綴りの読み替えだけ。⛔ 寸法は持たない)----
    // 鍵は**指図の名の先頭一致**で引く(「女坂(御成坂)」「隨身門(楼門)」の括弧書きを避けるため)。
    static readonly Dictionary<string, string> MUNE_NAME = new Dictionary<string, string>
    {
        // ⭐ 2026-09-10 の建て直しで、社殿5棟は指図の `munes[].partFrom` が指す部材で建った。
        //   ⛔ 薬師堂ほか山上の9棟は **部材が無い**(`bom`「無い/新造」優先3〜4)ので名簿から外した —
        //   名簿に残すと「実装に無い」ではなく「名簿にも載っていない」と出て、⛔ **部材待ちなのか
        //   据え忘れなのかが読めなくなる**。⇒ どちらにせよ「指図にあって実装に無い」で1件は立つ。
        { "本殿", "Honden" }, { "作り合い", "Tsukuriai" }, { "幣殿", "Heiden" },
        { "拝殿", "Haiden" }, { "向拝", "Kohai" },
        // ⭐ **2026-09-20 に `御供所` を足した** ── 部材(`Sanno_Gokusho_…`)が焼けて据わったのに
        //   名簿に行が無く、「名簿にも載っていない」= ⛔ 位置を一度も測っていなかった(規則19)。
        { "御供所", "Gokusho" },
    };
    /// <summary>門: 指図の名の先頭 → シーンの名。⭐ **2026-09-20 に名を改めた** ── 楼門・坂下の門は
    /// Japanese Castle の `Yaguramon A` の代用(`Zuijinmon` / `Niomon`)をやめ、指図の
    /// `bom[].手当` が名指す専用部材で建った(`Romon` / `Sakashitamon`)。
    /// ⭐ **`中門` を名簿へ足した** ── 部材(`Sanno_Chumon_…`)が焼けて据わったのに名簿に行が無く、
    /// 「名簿にも載っていない」= ⛔ **向きも位置も測れていなかった**(規則19)。</summary>
    static readonly Dictionary<string, string> GATE_NAME = new Dictionary<string, string>
    {
        { "隨身門", "Romon" }, { "中門", "Chumon" }, { "坂下の門", "Sakashitamon" },
    };
    static readonly Dictionary<string, string> TORII_NAME = new Dictionary<string, string>
    {
        { "二ノ鳥居", "NinoTorii" }, { "一ノ鳥居", "IchinoTorii" },
    };
    /// <summary>石段: 指図の名の先頭 → 「シーンの群のパス|段石の名の接頭辞」。
    /// ⚠ 群には縁石(`Kerb_*`)が混ざるので、**段石の接頭辞で選り分ける**。</summary>
    static readonly Dictionary<string, string> KAIDAN_GROUP = new Dictionary<string, string>
    {
        { "男坂", "Sando/Otokozaka|Dan_" },
        { "女坂", "Sando/Onnazaka|Dan_" },
        { "参道の階", "Sando/SandoKai|Dan_" },
    };
    /// <summary>**木階**(`kaidans[].kizahashi`)。⛔ 石段ではないので段数・蹴上では測らない。
    /// 値が null の物は**別の棟の部材に含まれている**(本殿の木階 = `Sanno_Honden_3x3ken` の中)。</summary>
    static readonly Dictionary<string, string> KIZAHASHI_NAME = new Dictionary<string, string>
    {
        { "向拝の階", "Kizahashi" },
        { "本殿の木階", null },
    };
    /// <summary>孤児(指図に無い現物)を数える群。⛔ ここに挙げた群だけを見る。</summary>
    const string SHADEN_GROUP = "Keidai/Shaden";
    static readonly string[] SHASO_GROUPS = { "Keidairin", "Keidai/Trees" };

    // =====================================================================
    [MenuItem("Edo/山王社/指図と実装を突き合わせる")]
    public static void CheckMenu() { Debug.Log("[Sanno] " + Check()); }

    public static string Check()
    {
        var head = new StringBuilder();
        var hits = new Dictionary<string, List<string>>();
        foreach (var s in SECTIONS) hits[s] = new List<string>();
        Action<string, string> bad = (sec, msg) => hits[sec].Add(msg);

        string rootDir = Directory.GetParent(Application.dataPath).FullName;
        string docPath = Path.Combine(rootDir, EdoSannoShaBuilder.SashizuRel);
        string implPath = Path.Combine(rootDir, EdoSannoShaBuilder.ImplRel);
        if (!File.Exists(docPath)) return "指図が無い: " + EdoSannoShaBuilder.SashizuRel;
        if (!File.Exists(implPath)) return "算出物が無い: " + EdoSannoShaBuilder.ImplRel;
        var doc = EdoMiniJson.Parse(File.ReadAllText(docPath)) as Dictionary<string, object>;
        var impl = EdoMiniJson.Parse(File.ReadAllText(implPath)) as Dictionary<string, object>;
        if (doc == null) return "指図が読めない: " + EdoSannoShaBuilder.SashizuRel;
        if (impl == null) return "算出物が読めない: " + EdoSannoShaBuilder.ImplRel;

        // ---- 境内グリッド(世界軸に平行)。⛔ 式は指図が持つ ----------------
        var g = D(D(doc, "grid"), "keidai");
        float ken = F(D(doc, "const"), "ken");
        float gx0 = F(g, "x0"), gz0 = F(g, "z0");
        float gux = F(g, "ux"), guz = F(g, "uz"), gvx = F(g, "vx"), gvz = F(g, "vz");
        Func<float, float, Vector2> W = (u, v) =>
            new Vector2(gx0 + (gux * u + gvx * v) * ken, gz0 + (guz * u + gvz * v) * ken);

        head.AppendLine("【指図と実装の突き合わせ — 山王権現社】");
        head.AppendLine("  指図   " + EdoSannoShaBuilder.SashizuRel);
        head.AppendLine("  算出物 " + EdoSannoShaBuilder.ImplRel + "(焼いた時刻 " + Str(impl, "at") + ")");

        // ---- 検図関門(⛔ 赤なら実装は止まる。物差しは測ってよい)-----------
        string gateMsg = EdoSashizuExport.ReviewGate(Id);
        head.AppendLine("  検図関門: " + (gateMsg == null
            ? "⭕ 止めない(不合格の記録なし)"
            : "⛔ 赤 — " + FirstLine(gateMsg)));
        head.AppendLine("    ⚠ **関門が赤の指図に合わせて建て直さない**(規則18)。この menu は測るだけ。");

        // ---- シーン ---------------------------------------------------------
        var root = GameObject.Find(EdoSannoShaBuilder.GroupName);
        if (root == null)
        {
            foreach (var s in SECTIONS) bad(s, "ルート " + EdoSannoShaBuilder.GroupName + " が無い(非アクティブでも Find は見つけない)");
            return Render(head.ToString(), hits);
        }
        head.AppendLine("  シーン: " + EdoSannoShaBuilder.GroupName +
                        "(active=" + root.activeInHierarchy + " / 子 " + root.transform.childCount + " 群)");
        var index = new List<Transform>();
        Collect(root.transform, index);

        // ---- 参道軸(見出し。差の親玉なので数には数えない)-------------------
        {
            // ⚠ 2026-09-10: 建て直しで **3本の石段がどれも `Dan_*`** で据わるようになったので、
            //   index 全体から拾うと三坂の平均になる。⇒ **男坂の群だけ**を見る。
            var otoko = root.transform.Find("Sando/Otokozaka");
            var dan = new List<Transform>();
            if (otoko != null)
                for (int i = 0; i < otoko.childCount; i++)
                    if (otoko.GetChild(i).name.StartsWith("Dan_")) dan.Add(otoko.GetChild(i));
            if (dan.Count > 0)
            {
                float zsum = 0f; foreach (var t in dan) zsum += EdoBuild.RB(t.gameObject).center.z;
                head.AppendLine("  参道軸 z: 指図 " + gz0.ToString("F3") +
                                " / 実装(男坂の段石 " + dan.Count + " 枚の芯の平均) " + (zsum / dan.Count).ToString("F3") +
                                " / 差 " + Mathf.Abs(zsum / dan.Count - gz0).ToString("F3") + " m");
            }
        }
        head.AppendLine("  物差し: 位置・寸法 " + POS_TOL_M.ToString("F2") +
                        " m(汎用の器と同じ) / 地形 " + F(D(impl, "checks"), "gradeTol").ToString("F2") +
                        " m(算出物 checks.gradeTol)");

        // =====================================================================
        // 社殿
        // =====================================================================
        var mapped = new HashSet<string>();
        var muneTs = new List<KeyValuePair<string, Transform>>();   // 屋根と塀の当たりで使う(下)
        foreach (var o in L(doc, "munes"))
        {
            var m = o as Dictionary<string, object>; if (m == null) continue;
            string name = Str(m, "name"); if (name == null) continue;
            Vector2 want = W(F(m, "u0") + F(m, "du") * 0.5f, F(m, "v0") + F(m, "dv") * 0.5f);
            // ⭐ **名簿はビルダーと同じ物差し**（2026-09-22）── 表に行が無い棟は
            //   <see cref="EdoSannoShaRebuild.ShadenNameOf"/> が出す名で引く。
            //   ⛔ 検査が別の名簿を持たない ── 持つと、据わった棟が「名簿にも載っていない」と
            //   「孤児」の**両方で 2 件**に化け、数え方が膨らむ（規則 19）。
            string scn = Lookup(MUNE_NAME, name) ?? EdoSannoShaRebuild.ShadenNameOf(name);
            if (scn == null) { bad("社殿", "棟 " + name + " が実装に無い（名簿にも載っていない）"); continue; }
            var t = ByName(index, scn);
            if (t == null) { bad("社殿", "棟 " + name + "(実装名 " + scn + ")が実装に無い"); continue; }
            mapped.Add(scn);
            muneTs.Add(new KeyValuePair<string, Transform>(name, t));
            // ⚠⚠ **棟は据え付け点(transform)で測る。⛔ Renderer の bbox の芯ではない。**
            //   `munes` の (u0,v0,du,dv) は**柱通りの矩形**で、部材の原点はその中心と定めてある
            //   (`build_sanno_shaden.py`「ピボット = その棟の区画の中心・地盤レベル」)。
            //   bbox は**軒の出**を含み、向拝の軒唐破風・幣殿の両下のように**軒が片側だけ出る棟**では
            //   芯が 0.1〜0.5m 動く。⇒ bbox で測ると ⛔ **正しく据えた棟が毎回ずれていると出る**
            //   (2026-09-10 実測: 作り合い 0.09 / 幣殿 0.09 / 向拝 0.50m)。
            //   ⭐ 部材の原点そのものが規約どおりかは**部材方の検算**(`check_*`)の持ち分。
            var c = t.position;
            float dd = Vector2.Distance(new Vector2(c.x, c.z), want);
            if (dd > POS_TOL_M)
                bad("社殿", "棟 " + name + " が " + dd.ToString("F2") + "m ずれている(指図 " +
                    V(want) + " / 実装 " + V(new Vector2(c.x, c.z)) + ")");
        }
        {
            // ⚠ 木階(`Kizahashi`)は社殿の群に据わるが `munes` ではなく `kaidans` の物。
            //   ⇒ 孤児にしない(石段の部門で位置を測る)。
            foreach (var kv in KIZAHASHI_NAME) if (kv.Value != null) mapped.Add(kv.Value);
            // ⭐ **棟に寄る鳥居**(`torii[].posFrom`)も社殿の群に据わる(座が棟の実メッシュからの
            //   従属値なので Stage6 が据える)⇒ 孤児にしない。隙は門・鳥居の部門で測る。
            foreach (var to in L(doc, "torii"))
            {
                var trm = to as Dictionary<string, object>; if (trm == null) continue;
                if (D(trm, "posFrom") == null) continue;
                string nmm = Str(trm, "name"); if (nmm == null) continue;
                mapped.Add(EdoSannoShaRebuild.ToriiNameOf(nmm));
            }
            var sg = root.transform.Find(SHADEN_GROUP);
            if (sg != null)
                for (int i = 0; i < sg.childCount; i++)
                {
                    string n = sg.GetChild(i).name;
                    if (!mapped.Contains(n)) bad("社殿", "孤児(指図に無い): " + SHADEN_GROUP + "/" + n);
                }
        }
        // 屋根と塀の高さの当たり(EDO-0444 施主裁定A 2026-09-26「Aで」── 軒が塀の線を**平面で**越えるのは許す・
        //   **当たりは許容 0**)。紙の検査 C32 は平面の越えしか測れない(軒の高さが紙に無い)⇒ 正の輪はここ(規則19)。
        // ⭐ 実メッシュの頂点で測る:塀の駒の頂点を 0.25m の格子へ落として格子ごとの最高点を持ち、棟の頂点のうち
        //   同じ格子に落ちる物の高さとの差の最小を「高さの空き」とする。⛔ bbox で測らない(規則21)。
        {
            const float CELL = 0.25f;
            Func<float, float, long> cellOf = (x, z) =>
                ((long)Mathf.FloorToInt(x / CELL) << 32) ^ (uint)Mathf.FloorToInt(z / CELL);
            var fenceTop = new Dictionary<long, float>();
            int nFence = 0;
            foreach (var t in index)
            {
                if (!(t.name.StartsWith("Sukibei_") && t.name.EndsWith("f")) && !t.name.StartsWith("Kado_Sukibei")) continue;
                nFence++;
                foreach (var mf in t.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue;
                    var m4 = mf.transform.localToWorldMatrix;
                    foreach (var v in mf.sharedMesh.vertices)
                    {
                        var w = m4.MultiplyPoint3x4(v); long k = cellOf(w.x, w.z); float y;
                        if (!fenceTop.TryGetValue(k, out y) || w.y > y) fenceTop[k] = w.y;
                    }
                }
            }
            if (nFence == 0) bad("囲い", "屋根と塀の高さの当たり: 透塀の駒が 1 枚も拾えない ⇒ 未検査");
            else
            {
                var over = new List<string>();
                foreach (var kv in muneTs)
                {
                    float minGap = float.MaxValue; int nOver = 0;
                    foreach (var mf in kv.Value.GetComponentsInChildren<MeshFilter>())
                    {
                        if (mf.sharedMesh == null) continue;
                        var m4 = mf.transform.localToWorldMatrix;
                        foreach (var v in mf.sharedMesh.vertices)
                        {
                            var w = m4.MultiplyPoint3x4(v); float y;
                            if (!fenceTop.TryGetValue(cellOf(w.x, w.z), out y)) continue;
                            nOver++; minGap = Mathf.Min(minGap, w.y - y);
                        }
                    }
                    if (nOver == 0) continue;
                    over.Add(kv.Key + " " + minGap.ToString("F2") + "m");
                    if (minGap <= 0f)
                        bad("囲い", "屋根と塀の当たり: 棟 " + kv.Key + " の実メッシュが透塀の上端より " +
                            (-minGap).ToString("F2") + "m 下へ入る(許容 0)");
                }
                head.AppendLine("  屋根と塀の高さの空き(塀の真上に掛かる棟だけ・実メッシュ): " +
                                (over.Count == 0 ? "掛かる棟なし" : string.Join(" / ", over)) +
                                "(透塀の駒 " + nFence + ")");
            }
        }
        // 棟間隔 — **並びが別物になっていないか**(位置のずれだけでは「平行移動」と区別できない)
        {
            var honden = FindMune(doc, "本殿"); var heiden = FindMune(doc, "幣殿");
            if (honden != null && heiden != null)
            {
                Vector2 a = W(F(honden, "u0") + F(honden, "du") * 0.5f, F(honden, "v0") + F(honden, "dv") * 0.5f);
                Vector2 b = W(F(heiden, "u0") + F(heiden, "du") * 0.5f, F(heiden, "v0") + F(heiden, "dv") * 0.5f);
                var ta = ByName(index, "Honden"); var tb = ByName(index, "Heiden");
                if (ta != null && tb != null)
                {
                    var ca = ta.position; var cb = tb.position;   // ⛔ bbox ではない(上の註)
                    float wantD = Vector2.Distance(a, b);
                    float gotD = Vector2.Distance(new Vector2(ca.x, ca.z), new Vector2(cb.x, cb.z));
                    if (Mathf.Abs(wantD - gotD) > POS_TOL_M)
                        bad("社殿", "棟間隔 本殿→幣殿 が別物(指図 " + wantD.ToString("F2") +
                            "m / 実装 " + gotD.ToString("F2") + "m)— 平行移動では説明できない");
                }
            }
        }

        // =====================================================================
        // 門・鳥居
        // =====================================================================
        // ⭐ 向きを測る(2026-09-16・台帳 K002)。位置だけ比べて向きを比べないので、
        //   実装の yaw 90° 直書きと指図の 4.6°/0° の差が **17巡ぶん 0 件のまま**通っていた。
        //   ⛔ 測っているのは**据えた駒の Y 回転**であって「正面がどちらを向くか」ではない —
        //   指図の yaw は `bom.axis.front = +X`(部材の正面がローカル +X)を前提に出た数なので、
        //   実装が**別の部材で代用**していれば差は「正面が違う」ではなく
        //   「**代用した部材の軸が宣言されていない**」ことの表れ。読み手が取り違えないよう
        //   一致・不一致のどちらでも `yawFrom`(指図の側の出どころ)を添える。
        int yawSeen = 0, yawNone = 0, yawCmp = 0;
        foreach (var o in L(impl, "gates"))
        {
            var gt = o as Dictionary<string, object>; if (gt == null) continue;
            string name = Str(gt, "name"); if (name == null) continue;
            yawSeen++;
            // 向きが指図から出ない門は、実装の有無と無関係に1件立つ(台帳 K005)
            object yawObj = G(gt, "yaw");
            if (yawObj == null)
            {
                yawNone++;
                bad("門・鳥居", "門 " + name + " の向きが指図から出ない(front / pass が未宣言 ⇒ yaw が null)" +
                    " — ⛔ 向きの突き合わせが**この門だけ未測定**になる");
            }
            var wp = A(gt, "world");
            if (wp == null || wp.Length < 2) { bad("門・鳥居", "門 " + name + " の world が算出物に無い"); continue; }
            Vector2 want = new Vector2(wp[0], wp[1]);
            // ⭐ 名簿はビルダーと同じ物差し(<see cref="EdoSannoShaRebuild.GateNameOf"/>)。
            //   ⛔ 名簿だけに門の名を持たない ── 2026-09-22 に勝手口(木戸)を足したとき、
            //   ビルダーは `Kido` で据えたのに名簿に行が無く「名簿にも載っていない」= **未測定**が
            //   1件立った(社殿・鳥居で先に踏んだのと同じ穴・規則19)。
            string scn = Lookup(GATE_NAME, name) ?? EdoSannoShaRebuild.GateNameOf(name);
            if (scn == null) { bad("門・鳥居", "門 " + name + " が実装に無い(名簿にも載っていない)"); continue; }
            var t = ByName(index, scn);
            if (t == null) { bad("門・鳥居", "門 " + name + "(実装名 " + scn + ")が実装に無い"); continue; }
            var c = EdoBuild.RB(t.gameObject).center;
            float dd = Vector2.Distance(new Vector2(c.x, c.z), want);
            if (dd > POS_TOL_M)
                bad("門・鳥居", "門 " + name + " が " + dd.ToString("F2") + "m ずれている(指図 " +
                    V(want) + " / 実装 " + V(new Vector2(c.x, c.z)) + ")");
            if (yawObj != null)
            {
                yawCmp++;
                float wantYaw = Norm360(Cv(yawObj));
                float gotYaw = Norm360(t.eulerAngles.y);
                float dYaw = Mathf.Abs(Mathf.DeltaAngle(wantYaw, gotYaw));
                if (dYaw > YAW_TOL_DEG)
                    bad("門・鳥居", "門 " + name + " の向きが " + dYaw.ToString("F1") + "° 違う(指図 " +
                        wantYaw.ToString("F1") + "°〔" + (Str(gt, "yawFrom") ?? "出どころが算出物に無い") +
                        "〕/ 実装 " + gotYaw.ToString("F1") + "°)" +
                        " — ⚠ 測ったのは**駒の Y 回転**。指図の yaw は部材の正面が +X である前提なので、" +
                        "代用の部材で建っているならこの差は『部材の軸が宣言されていない』ことの表れ");
            }
        }
        head.AppendLine("  門の向き: 算出物の門 " + yawSeen + " 件 / 指図が yaw を出す " + (yawSeen - yawNone) +
                        " 件 / 実装と突き合わせた " + yawCmp + " 件(許容 " + YAW_TOL_DEG.ToString("F1") + "°)");
        head.AppendLine("    ⛔ 突き合わせた件数が門の数より少ないなら、差し引きは**合格ではなく未測定**(規則19)。");
        foreach (var o in L(doc, "torii"))
        {
            var tr = o as Dictionary<string, object>; if (tr == null) continue;
            string name = Str(tr, "name"); if (name == null) continue;
            // ⭐ 名簿はビルダーと同じ物差し(<see cref="EdoSannoShaRebuild.ToriiNameOf"/>)。
            string scn = Lookup(TORII_NAME, name) ?? EdoSannoShaRebuild.ToriiNameOf(name);
            var t = ByName(index, scn);
            if (t == null) { bad("門・鳥居", "鳥居 " + name + "(実装名 " + scn + ")が実装に無い"); continue; }
            // ⭐ **座が棟からの従属値の鳥居**(`posFrom`)は pos で測れない ── 図が宣言しているのは
            //   「寄る棟の正面の面からの隙」なので、**実メッシュの触れている箇所**でその隙を測る
            //   (⛔ 芯どうしの距離で測らない・置き方の4手と同じ物差し)。
            var pfm = D(tr, "posFrom");
            if (pfm != null)
            {
                string hn = Str(pfm, "mune");
                var hrow = hn == null ? null : FindMune(doc, hn);
                var host = hn == null ? null : ByName(index, EdoSannoShaRebuild.ShadenNameOf(hn));
                if (host == null)
                { bad("門・鳥居", "鳥居 " + name + " の寄る棟『" + hn + "』が実装に無い ⇒ 隙を測れない"); continue; }
                string hf = hrow == null ? null : Str(hrow, "front");
                Vector2 hd;
                if (hf == null || !EdoBuild.DirVec(hf, EdoSannoShaRebuild.GridDeg, out hd))
                { bad("門・鳥居", "鳥居 " + name + " の寄る棟『" + hn + "』の front が指図に無い ⇒ 「前」が決まらない"); continue; }
                if (G(pfm, "clearanceM") == null)
                { bad("門・鳥居", "鳥居 " + name + " の `posFrom.clearanceM`(棟の面からの隙)が指図に無い"); continue; }
                float wantClr = F(pfm, "clearanceM");
                Vector3 cat; int ccnt;
                float gotClr = EdoBuild.Contact(t.gameObject, host.gameObject, new Vector3(-hd.x, 0f, -hd.y),
                                                out cat, out ccnt);
                if (float.IsNaN(gotClr))
                    bad("門・鳥居", "鳥居 " + name + " が寄る棟『" + hn + "』と向き合っていない ⇒ 隙が測れない");
                else if (Mathf.Abs(gotClr - wantClr) > POS_TOL_M)
                    bad("門・鳥居", "鳥居 " + name + " の『" + hn + "』の正面(" + hf + ")の面からの隙が " +
                        gotClr.ToString("F2") + "m(指図 " + wantClr.ToString("F2") + "m・当たり " + ccnt + " 筋)");
                continue;
            }
            var wp = A(tr, "pos");
            if (wp == null || wp.Length < 2) { bad("門・鳥居", "鳥居 " + name + " の pos が指図に無い"); continue; }
            Vector2 want = new Vector2(wp[0], wp[1]);
            var c = EdoBuild.RB(t.gameObject).center;
            float dd = Vector2.Distance(new Vector2(c.x, c.z), want);
            if (dd > POS_TOL_M)
                bad("門・鳥居", "鳥居 " + name + " が " + dd.ToString("F2") + "m ずれている(指図 " +
                    V(want) + " / 実装 " + V(new Vector2(c.x, c.z)) + ")");
        }

        // =====================================================================
        // 石段 — 端点・段数・平面長・幅・蹴上
        // =====================================================================
        foreach (var o in L(impl, "stairs"))
        {
            var st = o as Dictionary<string, object>; if (st == null) continue;
            string name = Str(st, "name"); if (name == null) continue;
            // ⭐ **木階は石段ではない**(`bom` の別行・部材は `Sanno_Kizahashi_*`)。⛔ 段数・蹴上で測らない。
            if (HasKey(KIZAHASHI_NAME, name))
            {
                string kn = Lookup(KIZAHASHI_NAME, name);
                if (kn == null) continue;                       // 別の棟の部材に含まれている(本殿の木階)
                var kt = ByName(index, kn);
                if (kt == null) { bad("石段", "木階 " + name + "(実装名 " + kn + ")が実装に無い"); continue; }
                mapped.Add(kn);
                var kc = EdoBuild.RB(kt.gameObject).center;
                var knd = L(st, "nodes");
                if (knd.Count >= 2)
                {
                    Vector2 kw = (P2(knd[0]) + P2(knd[knd.Count - 1])) * 0.5f;
                    float kd = Vector2.Distance(new Vector2(kc.x, kc.z), kw);
                    if (kd > POS_TOL_M)
                        bad("石段", "木階 " + name + " が " + kd.ToString("F2") + "m ずれている(指図 " +
                            V(kw) + " / 実装 " + V(new Vector2(kc.x, kc.z)) + ")");
                }
                continue;
            }
            // ⭐ 名簿はビルダーと同じ物差し(`EdoSannoShaRebuild.GroupNameOf` ── 2026-09-24)。旧は表 KAIDAN_GROUP の
            //   3本しか持たず、郭の階・段の階・中門の内の階が据わっていても「名簿にも載っていない」と出ていた(規則19)。
            string spec = Lookup(KAIDAN_GROUP, name) ?? ("Sando/" + EdoSannoShaRebuild.GroupNameOf(name) + "|Dan_");
            if (spec == null) { bad("石段", "石段 " + name + " が実装に無い(名簿にも載っていない)"); continue; }
            var parts = spec.Split('|');
            var grp = root.transform.Find(parts[0]);
            if (grp == null) { bad("石段", "石段 " + name + "(実装の群 " + parts[0] + ")が実装に無い"); continue; }
            var steps = new List<Transform>();
            for (int i = 0; i < grp.childCount; i++)
                if (grp.GetChild(i).name.StartsWith(parts[1])) steps.Add(grp.GetChild(i));
            if (steps.Count == 0) { bad("石段", "石段 " + name + " の段石(" + parts[1] + "*)が " + parts[0] + " に一枚も無い"); continue; }

            // 段の丈で束ねる(⚠ 男坂は1段が3枚に割れている)。束の閾は指図の蹴上の半分
            float keriWant = F(st, "keri");
            var lv = new List<float>();     // 束ごとの天端の丈
            var cen = new List<Vector3>();  // 束ごとの芯
            var cnt = new List<int>();
            // ⚠⚠ **段の芯は据え付け点(transform)で測る。⛔ bbox の芯ではない。**
            //   段石は上の段の下へ潜る差し込み(LAP)を持つので走りの前後が非対称で、
            //   bbox の芯は踏面の中心から **LAP/2 ≒ 0.05m** 走り方向へ寄る。⛔ bbox で測ると
            //   正しく据えた段が毎回 0.05m ずれていると出る(2026-09-10 実測)。
            //   ⭐ 部材の原点 = 踏面の中心・踏面の天端(`build_sanno_buzai.py`)。
            foreach (var t in steps)
            {
                Vector3 c0 = EdoBuild.StepAxis(t);   // 片側を詰めた段石は駒の原点が軸から外れる ── 軸の印で測る(EDO-0430)
                int k = -1;
                for (int i = 0; i < lv.Count; i++) if (Mathf.Abs(lv[i] - c0.y) < Mathf.Max(0.02f, keriWant * 0.5f)) { k = i; break; }
                if (k < 0) { lv.Add(c0.y); cen.Add(c0); cnt.Add(1); }
                else { cen[k] = cen[k] + c0; cnt[k] = cnt[k] + 1; }
            }
            for (int i = 0; i < cen.Count; i++) cen[i] = cen[i] / cnt[i];
            // 丈の順に並べる
            for (int i = 1; i < lv.Count; i++)
                for (int j = i; j > 0 && lv[j] < lv[j - 1]; j--)
                { var a1 = lv[j]; lv[j] = lv[j - 1]; lv[j - 1] = a1; var a2 = cen[j]; cen[j] = cen[j - 1]; cen[j - 1] = a2; }

            int nWant = (int)F(st, "steps");
            if (lv.Count != nWant)
                bad("石段", "石段 " + name + " の段数が違う(指図 " + nWant + " 段 / 実装 " + lv.Count + " 段)");

            // 端点(順番を仮定しない — 二通りの組み合わせの良いほうを採る)
            // ⚠⚠ **比べる相手は折れ線の端点ではなく「端の段の芯」**。段石の原点は踏面の中心なので、
            //   端の段の芯は坂の端から **踏面の半分(fumi/2)** だけ内側に立つ。⛔ 端点と比べると
            //   正しく据えた石段が毎回 fumi/2 ≒ 0.3〜0.6m ずれていると出る(2026-09-10 実測)。
            //   ⭐ 同じ理由で**平面長も 1踏面ぶん短い** — 期待値は `runM − fumi`。
            var nd = L(st, "nodes");
            var spans = L(st, "spans");
            var pl = new List<Vector2>(); foreach (var q in nd) pl.Add(P2(q));
            float fumiWant = F(st, "fumi");
            if (nd.Count >= 2 && spans.Count >= 1)
            {
                // ⭐ **割付 `spans` の中点**を弧長で拾う(s は坂下から)。⛔ 折れ線の向きは仮定しない —
                //   下の二通りの組み合わせで良いほうを採るので、坂下がどちらでも当たる。
                float sA = 0.5f * (Cv(((List<object>)spans[0])[0]) + Cv(((List<object>)spans[0])[1]));
                var spL = (List<object>)spans[spans.Count - 1];
                float sB = 0.5f * (Cv(spL[0]) + Cv(spL[1]));
                Vector2 wA = PolyAt(pl, sA), wB = PolyAt(pl, sB);
                Vector2 iA = new Vector2(cen[0].x, cen[0].z), iB = new Vector2(cen[cen.Count - 1].x, cen[cen.Count - 1].z);
                float p1 = Vector2.Distance(wA, iA) + Vector2.Distance(wB, iB);
                float p2 = Vector2.Distance(wA, iB) + Vector2.Distance(wB, iA);
                Vector2 mA = p1 <= p2 ? iA : iB, mB = p1 <= p2 ? iB : iA;
                float dA = Vector2.Distance(wA, mA), dB = Vector2.Distance(wB, mB);
                if (dA > POS_TOL_M || dB > POS_TOL_M)
                    bad("石段", "石段 " + name + " の端点が " + dA.ToString("F1") + "m / " + dB.ToString("F1") +
                        "m ずれている(指図 " + V(wA) + "〜" + V(wB) + " / 実装 " + V(mA) + "〜" + V(mB) + ")");
            }
            // 平面長(段の芯を丈の順に繋いだ折れ線)
            float runGot = 0f;
            for (int i = 1; i < cen.Count; i++)
                runGot += Vector2.Distance(new Vector2(cen[i - 1].x, cen[i - 1].z), new Vector2(cen[i].x, cen[i].z));
            float runWant = F(st, "runM") - fumiWant;      // ⭐ 端の段の芯どうし(上の註)
            if (Mathf.Abs(runGot - runWant) > POS_TOL_M)
                bad("石段", "石段 " + name + " の平面長(端の段の芯どうし)が違う(指図 " + runWant.ToString("F2") +
                    "m / 実装 " + runGot.ToString("F2") + "m)");
            // 幅 — ⚠⚠ **段石の OBB(ローカル X)で測る。⛔ 世界軸の bbox を射影しない。**
            //   女坂は 13点の曲線で段ごとに向きが違い、回転した bbox を射影すると
            //   ⛔ 幅が常に大きく出る(2026-09-10 実測: 6.36m の段が 7.32m と出た)。
            //   ⭐ 段石は「幅=ローカル X / 走り=ローカル Z」で焼いてある(`build_sanno_buzai.py`)。
            //   ⚠ ObbFootprint はローカル座標なので駒の縮尺が落ちる → lossyScale.x を掛けて実寸にする。
            //   ⚠ 返し・袖の法に合わせて端を切った段(EdoBuild.CutStairEndsToBatter)や詰めた段は狭く出るので、
            //     中ほどの一段ではなく**全段の最大**を石段の幅とする(2026-09-26 参道の階で 5.51 を 5.26 と誤読)。
            if (steps.Count > 0)
            {
                //   ⭐ 端を相手の石に沿わせて焼いた段(EdoAssets.Own.SannoDanFit)は石の下へ端が張り出し、外接箱では広く出る(参道の階 5.51 を 6.06 と
                //     誤読・2026-09-27)⇒ **段鼻から 0.05 奥の横一線で踏面の平らな所の幅**を実メッシュで読む(TreadWidthAtNosing)。
                float wGot = 0f;
                foreach (var stp in steps) wGot = Mathf.Max(wGot, TreadWidthAtNosing(stp, 0.05f));
                float wWant = F(st, "wM");
                if (Mathf.Abs(wGot - wWant) > POS_TOL_M)
                    bad("石段", "石段 " + name + " の幅が違う(指図 " + wWant.ToString("F2") +
                        "m / 実装 " + wGot.ToString("F2") + "m)");
            }
            // 蹴上
            if (lv.Count >= 2)
            {
                float keriGot = (lv[lv.Count - 1] - lv[0]) / (lv.Count - 1);
                if (Mathf.Abs(keriGot - keriWant) > POS_TOL_M)
                    bad("石段", "石段 " + name + " の蹴上が違う(指図 " + keriWant.ToString("F3") +
                        "m / 実装 " + keriGot.ToString("F3") + "m)");
            }
        }

        // =====================================================================
        // 囲い — run ごとの部材の有無と、線形
        //   DobeiRun は `<run名>_<k>f` / `_<k>b` で据える。**その形の名を全部拾って接頭辞で束ねる**
        //   ので、群の並べ替えに強い(⛔「見る場所を間違えて『据えたのに無い』と嘘をつく」対策)。
        // =====================================================================
        {
            var byPrefix = new Dictionary<string, List<Transform>>();
            foreach (var t in index)
            {
                // ⭐ 出隅の隅の駒(EdoBuild.PlaceRunCorners の `<A>_x_<Bの末尾>_kado` / `<run>_kado<n>`)は両脇の run の駒として数える ──
                //   短い区間(御供所の郭 TW_Gusho_EK 1.36m)は隅の駒の腕が区間を丸ごと持ち、直線の駒が残らない(2026-09-26・EDO-0430)。
                var km = System.Text.RegularExpressions.Regex.Match(t.name, "^(.+)_x_([^_]+)_kado$");
                var ks = System.Text.RegularExpressions.Regex.Match(t.name, "^(.+)_kado\\d+$");
                var kruns = new List<string>();
                if (!t.name.StartsWith("TW_")) { }   // 土留め(terraceWalls)の隅だけ ── ⛔ 透塀の隅(joints.kadoFrom)は run に混ぜない
                else if (km.Success) { string a = km.Groups[1].Value; kruns.Add(a); kruns.Add(a.Substring(0, a.LastIndexOf('_') + 1) + km.Groups[2].Value); }
                else if (ks.Success) kruns.Add(ks.Groups[1].Value);
                foreach (var kr in kruns) { if (!byPrefix.ContainsKey(kr)) byPrefix[kr] = new List<Transform>(); byPrefix[kr].Add(t); }
                if (kruns.Count > 0) continue;
                string pfx = RunPrefixOf(t.name);
                if (pfx == null) continue;
                if (!byPrefix.ContainsKey(pfx)) byPrefix[pfx] = new List<Transform>();
                byPrefix[pfx].Add(t);
            }
            var wantNames = new HashSet<string>();
            var straightRuns = new List<string>();
            // ⭐ **土留め 13本**(`terraceWalls`)も囲いの部門で見る。⛔ 名簿に入れないと
            //   据えた石垣が丸ごと「孤児」に化け、⛔ **据えたことが欠陥として出る**。
            //   ⚠ 埋まっている区間(見付 ≤ 0 かつ 受け > 0)は**建てないのが正**(裁定 EDO-0182 が未着手)
            //   なので、⛔ ここでは延長を突き合わせない — 見るのは「一つも建っていない」かどうかだけ。
            foreach (var o in L(doc, "terraceWalls"))
            {
                var tw = o as Dictionary<string, object>; if (tw == null) continue;
                string tn = Str(tw, "name"); if (tn == null) continue;
                wantNames.Add(tn);
                // 二段築の下段(`tierPlan`)は `<run>_Ge_<k>f` で据わる(EdoBuild.PlaceTierBelow)── 孤児にしない
                if (D(tw, "tierPlan") != null) wantNames.Add(tn + "_Ge");
                if (byPrefix.ContainsKey(tn)) continue;
                // ⭐ **全区間が埋まっている壁は「一つも無い」のが正**(見付 ≤ 0 かつ 受け > 0)。
                //   ⛔ 建てるほうが欠陥なので、⛔ 同じ文言で数えない — 何を測ったかを名指す(規則19)。
                var iw = FindByName(impl, "runs", tn);
                int exposed = 0;
                if (iw != null)
                    foreach (var po in L(iw, "profile"))
                    { var pr = po as List<object>; if (pr != null && pr.Count >= 6 && Cv(pr[4]) > 0.02f) exposed++; }
                if (iw != null && exposed == 0)
                    bad("囲い", "土留め " + tn + " は**全区間が土に埋まっている**(見付高 > 0 の点が 0 個)" +
                        " — 建てないのが正だが、⛔ **図の側の始末が未着手**(裁定 EDO-0182)");
                else
                    bad("囲い", "土留め " + tn + " の石垣が実装に一つも無い(露出する区間が " + exposed + " 点ある)");
            }
            foreach (var o in L(doc, "runs"))
            {
                var r = o as Dictionary<string, object>; if (r == null) continue;
                string name = Str(r, "name"); if (name == null) continue;
                wantNames.Add(name);
                if (!byPrefix.ContainsKey(name))
                { bad("囲い", "囲い " + name + "(" + Str(r, "kind") + ")の部材が実装に一つも無い"); continue; }
                // 線形 — 算出物の折れ線と、据わっている部材を**継ぎ目の高さの断面**で比べる
                // ⭐ 2026-09-23 に改めた(EDO-0413)。⛔ **外接矩形の芯どうしで比べない。**
                //   斜面の run は駒を勾配なりに傾けて据える(`EdoBuild.PlaceOnChord`)ので、駒の頭と足が
                //   走りの前後へ 丈 × sinθ はみ出し、線の上に正しく据わった run でも外接矩形の芯は片寄る。
                //   曲がった run では厚みの張り出しも端ごとに違う向きへ出る。完成時(EDO-0398)に柵を
                //   弦で張り直したあと、この物差しが `Saku_SW` 0.053m / `Saku_Sando` 0.029m を偽の芯ずれとして
                //   出した(継ぎ目の高さで切れば両端・横とも 0.000m)。
                //   ⇒ 各駒を**その駒自身の丈の中ほど**で切った断面(`EdoBuild.MidSection`)を測る。見るのは2つ:
                //   ① **横** — 駒ごとの断面の厚みの中央が、その駒の居る区間の線から離れていないか。
                //      区間は **Stage4 が実際に建てる区間**(`EdoSannoShaRebuild.BuiltSegs` — 口の縁を門の脇柱の角へ
                //      取り付けた後)。⛔ `segs` のままで測らない — 勝手口の脇で脇柱へ折れて取り付く駒
                //      (`Ita_Keidai_172f`)が 0.49m 外れていると出る。どの区間からも `RIM_LAT_M` 以内に居ない駒は
                //      口の縁の駒として**口1つに2枚まで**許し、それを超えたら線から外れて建った run として出す。
                //   ② **走り** — run の断面が折れ線(`nodes`)の上で占める道のりの**中ほど**が、`segs` の最初の点と
                //      最後の点の中ほどに来ているか。⚠ 端そのものは比べない ── 隅(`Kado_*`)・回廊の妻・口の門に
                //      取り付く端は左右対称に詰まるのが正(透塀 ±0.127m・回廊 ±0.570m)。端の取り合いは「隙」の側。
                // ⚠ 部材は表裏2枚(`_kf` / `_kb`)で据わり、裏は run から 0.12m 逃がしてある。⇒ **表(`f`)だけ**を測る。
                var ir = FindByName(impl, "runs", name);
                if (ir == null) continue;
                var nd = L(ir, "nodes"); if (nd.Count < 2) continue;
                var line = new List<Vector2>(); foreach (var q in nd) line.Add(P2(q));
                // ⭐ 区間は **Stage4 が実際に建てる区間**(口の縁を門の脇柱の角へ取り付けた後)。
                //   ⛔ 検査が口の閉じ方を別に持たない — ビルダーと同じ関数で引く(`EdoSannoShaRebuild.BuiltSegs`)。
                var segA = new List<Vector2>(); var segB = new List<Vector2>();
                EdoSannoShaRebuild.BuiltSegs(ir, segA, segB);
                if (segA.Count == 0) continue;
                float sWant0, sWant1, dummy;
                EdoBuild.PolylineParam(line, segA[0], out sWant0, out dummy);
                EdoBuild.PolylineParam(line, segB[segB.Count - 1], out sWant1, out dummy);
                float sGot0 = float.MaxValue, sGot1 = float.MinValue, latWorst = 0f;
                string latWorstName = null; int measured = 0, rim = 0;
                foreach (var t in byPrefix[name])
                {
                    if (!t.name.EndsWith("f")) continue;
                    var sec = EdoBuild.MidSection(t.gameObject);
                    if (sec.Count == 0) continue;
                    measured++;
                    Vector2 c0 = new Vector2(float.MaxValue, float.MaxValue), c1 = new Vector2(float.MinValue, float.MinValue);
                    foreach (var w in sec)
                    {
                        float s, lat; EdoBuild.PolylineParam(line, new Vector2(w.x, w.z), out s, out lat);
                        sGot0 = Mathf.Min(sGot0, s); sGot1 = Mathf.Max(sGot1, s);
                        c0 = Vector2.Min(c0, new Vector2(w.x, w.z)); c1 = Vector2.Max(c1, new Vector2(w.x, w.z));
                    }
                    // この駒の居る区間 = 断面の中ほどが走りの内に入る区間のうち、線に最も近いもの
                    Vector2 pc = (c0 + c1) * 0.5f;
                    int k = -1; float kd = float.MaxValue;
                    for (int i = 0; i < segA.Count; i++)
                    {
                        float len = Vector2.Distance(segA[i], segB[i]); if (len < 1e-6f) continue;
                        Vector2 d = (segB[i] - segA[i]) / len;
                        float tt = Vector2.Dot(pc - segA[i], d);
                        if (tt < 0f || tt > len) continue;
                        float dl = Mathf.Abs(Vector2.Dot(pc - segA[i], new Vector2(-d.y, d.x)));
                        if (dl <= RIM_LAT_M && dl < kd) { kd = dl; k = i; }
                    }
                    if (k < 0) { rim++; continue; }
                    var one = new List<Vector2> { segA[k], segB[k] };
                    float lat0 = float.MaxValue, lat1 = float.MinValue;
                    foreach (var w in sec)
                    {
                        float s, lat; EdoBuild.PolylineParam(one, new Vector2(w.x, w.z), out s, out lat);
                        lat0 = Mathf.Min(lat0, lat); lat1 = Mathf.Max(lat1, lat);
                    }
                    float latMid = (lat0 + lat1) * 0.5f;
                    if (Mathf.Abs(latMid) > Mathf.Abs(latWorst)) { latWorst = latMid; latWorstName = t.name; }
                }
                if (measured == 0)
                { bad("囲い", "囲い " + name + " の表の部材が断面で測れない(メッシュが無い) ⇒ 線形は未検査"); continue; }
                // ⚠ **部材1枚に満たない切れ端**は据えられないので、その run は走りが寄って出る。
                //   ⛔ 数から黙って除かない — **何本あるか**を message に出して人の目へ渡す
                //   (指図の `_pending`「境内の外周の柵に部材として建たない切れ端が1本残る」)。
                int stub = 0; float stubM = 0f;
                for (int i = 0; i < segA.Count; i++)
                { float sl = Vector2.Distance(segA[i], segB[i]); if (sl < 1.0f) { stub++; stubM += sl; } }
                float runOff = (sGot0 + sGot1) * 0.5f - (sWant0 + sWant1) * 0.5f;
                // 口の縁の駒は**口1つに2枚まで**。それを超えて線に乗らない駒は、線から外れて建った駒。
                int mouths = 0;
                for (int i = 0; i + 1 < segA.Count; i++) if (Vector2.Distance(segB[i], segA[i + 1]) >= 0.05f) mouths++;
                if (rim > 2 * mouths)
                    bad("囲い", "囲い " + name + " の表の駒 " + rim + " 枚が、どの区間の線からも " + RIM_LAT_M.ToString("F1") +
                        "m 以内に居ない(口 " + mouths + " 箇所の縁として許すのは " + (2 * mouths) + " 枚まで)");
                if (Mathf.Abs(latWorst) > POS_TOL_M)
                    bad("囲い", "囲い " + name + " が線から横へ " + latWorst.ToString("F3") + "m ずれている(最大の駒 " +
                        latWorstName + "・継ぎ目の高さの断面の厚みの中央・口の縁の駒 " + rim + " 枚は除く)");
                // ⭐ 端が別の透塀へ一直線に続く run(端 n・柱が節点を跨ぐ)は、走りの両端の詰まりが対称にならないのが正 ──
                //   その継ぎ目は下の「透塀の継ぎ目の口」(腰の断面の道のりの重なり)で測る。⇒ 走りの芯の比べは外す(2026-09-25・EDO-0430)
                bool straightEnd = false;
                if (Str(ir, "kind") == "透塀")
                {
                    var oth = new List<Vector2[]>();
                    foreach (var oo in L(impl, "runs")) { var ro = oo as Dictionary<string, object>; if (ro == null || ro == ir || Str(ro, "kind") != "透塀") continue; var n2 = L(ro, "nodes"); if (n2.Count >= 2) oth.Add(new Vector2[] { P2(n2[0]), P2(n2[n2.Count - 1]) }); }
                    Vector2 l0 = line[0], l1 = line[line.Count - 1];
                    straightEnd = EdoBuild.ContinuesStraight(l0, (l0 - line[1]).normalized, oth) || EdoBuild.ContinuesStraight(l1, (l1 - line[line.Count - 2]).normalized, oth);
                    if (straightEnd) straightRuns.Add(name);
                }
                if (!straightEnd && Mathf.Abs(runOff) > POS_TOL_M)
                    bad("囲い", "囲い " + name + " が走りの方向へ " + runOff.ToString("+0.000;-0.000") + "m ずれている" +
                        "(端の詰まり 始め " + (sGot0 - sWant0).ToString("+0.000;-0.000") + "m / 終わり " +
                        (sGot1 - sWant1).ToString("+0.000;-0.000") + "m・+ は先へ)" +
                        (stub > 0 ? " ⚠ **部材1枚に満たない切れ端が " + stub + " 本(計 " + stubM.ToString("F2") +
                                    "m)** ある — 据えられないので走りがそのぶん寄る(`_pending`「境内の外周の柵に部材として建たない切れ端が1本残る」)"
                                  : ""));
            }
            foreach (var kv in byPrefix)
                if (!wantNames.Contains(kv.Key))
                    bad("囲い", "孤児(指図に無い囲い): " + kv.Key + " ×" + kv.Value.Count + " 部材");

            // ---- 透塀の隅 ---------------------------------------------------
            // ⭐ 2026-09-20 に足した。隅は `joints[].kadoFrom`(`in` = 入る辺 / `out` = 出る辺)が
            //   立てる別の物で、⛔ どちらかの run の外接矩形に混ぜてはいけない
            //   (混ぜると run ごとに 0.29m の偽の芯ずれが 8 本出る)。⇒ **節点そのもの**と比べる。
            // ⚠ 部材のピボットは隅柱の芯だが、外形は X/Z とも [−0.477, +0.493] なので
            //   外接矩形の芯は節点から 0.011m ずれて出る(許容 0.02m の内)。
            int kadoWant = 0, kadoCmp = 0;
            foreach (var o in L(doc, "joints"))
            {
                var j = o as Dictionary<string, object>; if (j == null) continue;
                var kf = j.ContainsKey("kadoFrom") ? j["kadoFrom"] as Dictionary<string, object> : null;
                if (kf == null) continue;
                string an = Str(kf, "in"), bn = Str(kf, "out"); if (an == null || bn == null) continue;
                kadoWant++;
                var ira = FindByName(impl, "runs", an); var irb = FindByName(impl, "runs", bn);
                if (ira == null || irb == null)
                { bad("囲い", "隅 " + an + "→" + bn + ": 算出物に run が無い"); continue; }
                var na = L(ira, "nodes"); var nb = L(irb, "nodes");
                if (na.Count < 2 || nb.Count < 2)
                { bad("囲い", "隅 " + an + "→" + bn + ": 折れ線の節点が足りない"); continue; }
                Vector2 node = P2(na[na.Count - 1]);
                if (Vector2.Distance(node, P2(nb[0])) > 0.05f)
                { bad("囲い", "隅 " + an + "→" + bn + ": 折れ線の端が一致しない(算出物)"); continue; }
                var kt = ByName(index, "Kado_" + an + "_" + bn);
                if (kt == null)
                { bad("囲い", "隅 " + an + "→" + bn + "(実装名 Kado_" + an + "_" + bn + ")が実装に無い"); continue; }
                kadoCmp++;
                var kc = EdoBuild.RB(kt.gameObject).center;
                float kd = Vector2.Distance(new Vector2(kc.x, kc.z), node);
                if (kd > POS_TOL_M)
                    bad("囲い", "隅 " + an + "→" + bn + " が " + kd.ToString("F2") + "m ずれている(節点 " +
                        V(node) + " / 実装 " + V(new Vector2(kc.x, kc.z)) + ")");
            }
            head.AppendLine("  透塀の隅: 指図 " + kadoWant + " 箇所 / 実装と突き合わせた " + kadoCmp + " 箇所");

            // ---- 透塀の継ぎ目の口(許容 0)------------------------------------
            // ⭐ 2026-09-25 に足した(EDO-0430)。透塀は一周の折れ線で、run の端・隅・中門で継ぐ。駒ごとの
            //   腰の高さの断面(EdoBuild.Section)が折れ線の上で占める道のりを重ね、覆われない所を口として数える。
            //   ⛔ 設計の口(同じ run の segs の間 = 中門・南の潜り)は数えない。⛔ 外接矩形で測らない(隅の脚が芯を片寄せる)。
            //   この物差しが無く、段の境の 4 箇所に 0.18m の口(柱なし)が開いていたのを施主の赤丸まで捕まえられなかった。
            {
                var sruns = new List<Dictionary<string, object>>();
                foreach (var o in L(impl, "runs")) { var r = o as Dictionary<string, object>; if (r != null && Str(r, "kind") == "透塀") sruns.Add(r); }
                var chain = new List<Dictionary<string, object>>();
                if (sruns.Count > 0)
                {
                    chain.Add(sruns[0]); sruns.RemoveAt(0);
                    for (bool grew = true; grew && sruns.Count > 0;)
                    {
                        grew = false; var ln = L(chain[chain.Count - 1], "nodes"); Vector2 last = P2(ln[ln.Count - 1]);
                        for (int i = 0; i < sruns.Count; i++)
                            if (Vector2.Distance(P2(L(sruns[i], "nodes")[0]), last) < 0.05f) { chain.Add(sruns[i]); sruns.RemoveAt(i); grew = true; break; }
                    }
                }
                if (chain.Count == 0) head.AppendLine("  透塀の継ぎ目の口: 透塀の run が無い ⇒ 未検査");
                else if (sruns.Count > 0) bad("囲い", "透塀の継ぎ目の口: run の折れ線が一周に繋がらない(残り " + sruns.Count + " 本)⇒ 未検査");
                else
                {
                    var loop = new List<Vector2>();
                    foreach (var r in chain) { var nd = L(r, "nodes"); for (int i = (loop.Count == 0 ? 0 : 1); i < nd.Count; i++) loop.Add(P2(nd[i])); }
                    float total = PolyLen(loop);
                    var open = new List<Vector2>();                // 設計の口
                    foreach (var r in chain)
                    {
                        var sg = L(r, "segs");
                        for (int i = 0; i + 1 < sg.Count; i++)
                        {
                            var a = sg[i] as List<object>; var b = sg[i + 1] as List<object>; if (a == null || b == null) continue;
                            float s0, s1, lt; EdoBuild.PolylineParam(loop, P2(a[a.Count - 1]), out s0, out lt); EdoBuild.PolylineParam(loop, P2(b[0]), out s1, out lt);
                            open.Add(new Vector2(Mathf.Min(s0, s1), Mathf.Max(s0, s1)));
                        }
                    }
                    var cov = new List<Vector2>(); int nPieces = 0;
                    foreach (var t in index)
                    {
                        if (!(t.name.StartsWith("Sukibei_") && t.name.EndsWith("f")) && !t.name.StartsWith("Kado_Sukibei")) continue;
                        // 腰(床から 0.75 まで板で塞がる)の中ほど 0.40 で切る ── 透かし(連子)の高さで切ると竪子の間を口と読む
                        var sec = EdoBuild.Section(t, t.position.y + 0.40f); if (sec.Count == 0) continue;
                        var ss = new List<float>();
                        foreach (var w in sec) { float s, lat; EdoBuild.PolylineParam(loop, new Vector2(w.x, w.z), out s, out lat); if (Mathf.Abs(lat) > 0.6f) continue; if (s < 0f) s += total; if (s > total) s -= total; ss.Add(s); }
                        if (ss.Count == 0) continue;
                        float mn = float.MaxValue, mx = float.MinValue; foreach (var s in ss) { mn = Mathf.Min(mn, s); mx = Mathf.Max(mx, s); }
                        if (mx - mn > total * 0.5f)
                        {   // 一周の継ぎ目(折れ線の始まり)を跨ぐ駒
                            mn = float.MaxValue; mx = float.MinValue;
                            foreach (var s0 in ss) { float s = s0 < total * 0.5f ? s0 + total : s0; mn = Mathf.Min(mn, s); mx = Mathf.Max(mx, s); }
                            cov.Add(new Vector2(mn - total, mx - total));
                        }
                        cov.Add(new Vector2(mn, mx)); nPieces++;
                    }
                    cov.Sort((p, q) => p.x.CompareTo(q.x));
                    const float GAP_TOL = 0.01f;
                    int gaps = 0; float worst = 0f; string where = null;
                    float reach = 0f;
                    foreach (var c in cov)
                    {
                        if (c.x > reach + GAP_TOL)
                        {
                            bool designed = false;
                            foreach (var op in open) if (reach >= op.x - 0.5f && c.x <= op.y + 0.5f) designed = true;
                            if (!designed)
                            {
                                gaps++; float gp = c.x - reach;
                                if (gp > worst) { worst = gp; where = V(PolyAt(loop, (reach + c.x) * 0.5f)); }
                            }
                        }
                        reach = Mathf.Max(reach, c.y);
                    }
                    if (reach < total - GAP_TOL) { gaps++; worst = Mathf.Max(worst, total - reach); }
                    if (straightRuns.Count > 0) head.AppendLine("  透塀の走りの芯: 一直線の継ぎ目に端を持つ " + straightRuns.Count + " 本(" + string.Join("・", straightRuns.ToArray()) + ")は芯で比べず継ぎ目の口で測る");
                    head.AppendLine("  透塀の継ぎ目の口: 駒 " + nPieces + " の断面で一周 " + total.ToString("F2") + "m を測った / 設計の口 " + open.Count + " を除く / 口 " + gaps);
                    if (gaps > 0) bad("囲い", "透塀の継ぎ目に口 " + gaps + " 箇所(最大 " + worst.ToString("F3") + "m @" + where + ")── 隅も柱も無い継ぎ目");
                }
            }
        }

        // =====================================================================
        // 造成の面 — 算出物の面の輪郭の中で、地形が設計の丈に届いているか
        // =====================================================================
        {
            float gradeTol = F(D(impl, "checks"), "gradeTol");
            Terrain ter = null;
            try { ter = EdoBuild.T(); } catch (Exception) { }
            // ⭐ 測るのは**描かれた地表**(EDO-0430): 縁の皮(EdoBuild.CutEdgeSkin)で穴を開けた升では皮の高さ、
            //   それ以外は地形。⛔ 穴の升で SampleHeight を読まない(穴の下の、描かれていない地形を測ることになる)。
            //   穴の升で皮も無い点は「描かれていない」= 未測定として不合格に数える(規則19)。
            EdoBuild.DrawnGround dg = null;
            if (ter != null) dg = EdoBuild.Drawn();
            if (ter == null) bad("造成の面", "アクティブな Terrain が無いので面を測れない");
            else
            {
                head.AppendLine("  造成の面は描かれた地表で測る(縁の皮 " + dg.skins + " 枚 ── 穴の升では皮の高さ)");
                // ⭐ 部材の外形の中の標本点は面の検査の対象外(見えない ── 踏面の端を袖の中で数えないのと同じ・普請奉行の決め
                //   2026-09-25 EDO-0430)。外形 = 地に据わる部材(土留め・石段と袖・囲い)の駒ごとの平面の凸包。
                //   ⛔ 社殿・門は入れない(床下・軒下の地表は見える)。外した点の数は面ごとに必ず刷る。
                var skip = new List<Vector2[]>(); var skipB = new List<Vector4>();
                Action<Transform> addHull = tr =>
                {
                    if (tr == null || !tr.gameObject.activeInHierarchy) return;
                    var hl = EdoBuild.HullOfMat(tr); if (hl == null || hl.Length < 3) return;
                    float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue;
                    foreach (var q in hl) { a0 = Mathf.Min(a0, q.x); a1 = Mathf.Max(a1, q.x); b0 = Mathf.Min(b0, q.y); b1 = Mathf.Max(b1, q.y); }
                    skip.Add(hl); skipB.Add(new Vector4(a0, b0, a1, b1));
                };
                { var gd = root.transform.Find("Dodome"); if (gd != null) foreach (Transform c in gd) addHull(c); }
                foreach (var gn in new[] { "Sando", "Kakoi" })
                { var gg = root.transform.Find(gn); if (gg != null) foreach (Transform run in gg) foreach (Transform c in run) addHull(c); }
                Func<float, float, bool> underPart = (x, z) =>
                {
                    for (int k = 0; k < skip.Count; k++)
                    {
                        var b = skipB[k]; if (x < b.x || x > b.z || z < b.y || z > b.w) continue;
                        if (EdoGeom.PIP(skip[k], new Vector2(x, z))) return true;
                    }
                    return false;
                };
                head.AppendLine("  面の標本のうち部材(土留め・石段と袖・囲い " + skip.Count + " 駒)の外形の中の点は見えないので数えない:");
                foreach (var o in L(impl, "terraces"))
                {
                    var tc = o as Dictionary<string, object>; if (tc == null) continue;
                    string name = Str(tc, "name");
                    float y = F(tc, "y");
                    var poly = Poly(L(tc, "world"));
                    if (poly.Length < 3) { bad("造成の面", "面 " + name + " の輪郭が算出物に無い"); continue; }
                    float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
                    foreach (var p in poly)
                    { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
                    int n = 0, over = 0, blank = 0, hid = 0, rimN = 0; float worst = 0f; Vector2 worstAt = Vector2.zero;
                    // ⭐ 輪郭から RIM_MARGIN_M 以内の標本は数えない(2026-09-25・EDO-0430)── 地形は 2 m/px で、輪郭ちょうどに面の縁は
                    //   置けない(縁の節点は外の節点との双一次)。失敗は毎巡この帯にだけ出た(2026-09-22 全 17 点が 0.28m 以内・
                    //   2026-09-25 Kairo_Fumoto の北西の角・Keidai の南西 0.01〜0.30m)。外した数は刷る。⛔ 造成を均して逃げない(段が埋まる)。
                    // ⭐ 標本の刻みは 2m から始め、部材の下を外して見える点が MIN_VIS 未満なら 0.5m → 0.25m と細かくする
                    //   (2026-09-25 EDO-0430: 細い帯 SukibeiSoto_Chu は 2m の標本 2 点が両方とも部材の下で「輪郭が壊れている」と嘘を出した)。
                    //   ⛔ 部材の下の点は数えない(見えない)。どの刻みでも見える点が 0 なら、面は全て部材の下 ── 測る物が無い(不合格にしない)。
                    const int MIN_VIS = 8; float stepUsed = 2f;
                    foreach (float st in new[] { 2f, 0.5f, 0.25f })
                    {
                        n = 0; over = 0; blank = 0; hid = 0; rimN = 0; worst = 0f; worstAt = Vector2.zero; stepUsed = st;
                        for (float x = mnx; x <= mxx; x += st)
                            for (float z = mnz; z <= mxz; z += st)
                            {
                                if (!Inside(poly, x, z)) continue;
                                if (underPart(x, z)) { hid++; continue; }
                                if (EdoGeom.DistToPolyEdge(poly, new Vector2(x, z)) < RIM_MARGIN_M) { rimN++; continue; }
                                n++;
                                float gz = dg.At(x, z);
                                if (float.IsNaN(gz)) { blank++; continue; }
                                float d = gz - y;
                                if (Mathf.Abs(d) > gradeTol) over++;
                                if (Mathf.Abs(d) > Mathf.Abs(worst)) { worst = d; worstAt = new Vector2(x, z); }
                            }
                        if (n >= MIN_VIS) break;
                    }
                    head.AppendLine("    面 " + name + ": 標本 " + (n + hid + rimN) + " 点(刻み " + stepUsed.ToString("0.##") + "m)のうち部材の外形の中 " + hid + " 点・輪郭から " + RIM_MARGIN_M.ToString("0.0#") + "m 以内 " + rimN + " 点を外し " + n + " 点で測る");
                    if (n == 0 && (hid > 0 || rimN > 0)) { head.AppendLine("      面 " + name + " は全て部材の外形の下か輪郭の帯(見える所が無い ── 測る物が無い)"); continue; }
                    if (n == 0) { bad("造成の面", "面 " + name + " に標本が取れない(輪郭が壊れている)"); continue; }
                    if (over > 0)
                        bad("造成の面", "面 " + name + "(設計 y=" + y.ToString("F2") + ")が造成されていない — 標本 " +
                            n + " 点中 " + over + " 点が許容 " + gradeTol.ToString("F2") + "m の外。最大 " +
                            worst.ToString("F2") + "m @ " + V(worstAt));
                    if (blank > 0)
                        bad("造成の面", "面 " + name + " の標本 " + n + " 点中 " + blank + " 点が穴の升で皮も無い(描かれていない・未測定)");
                }
            }
        }

        // =====================================================================
        // 社叢 — 撒いた木の総数と、名指しの木
        // =====================================================================
        {
            var pts = L(D(impl, "planting"), "points");
            int wantTree = 0, wantDetail = 0; var namedWant = new List<string>();
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var o in pts)
            {
                var p = o as Dictionary<string, object>; if (p == null) continue;
                string place = Str(p, "place");
                if (place == "TerrainTree") wantTree++;
                else if (place == "DetailMesh") wantDetail++;
                else if (place == "GameObject") namedWant.Add(Str(p, "name"));
                var w = A(p, "world");
                if (w != null && w.Length >= 2)
                { mnx = Mathf.Min(mnx, w[0]); mxx = Mathf.Max(mxx, w[0]); mnz = Mathf.Min(mnz, w[1]); mxz = Mathf.Max(mxz, w[1]); }
            }
            int gotGo = 0; var gotNames = new List<string>();
            foreach (var gname in SHASO_GROUPS)
            {
                var gg = root.transform.Find(gname);
                if (gg == null) continue;
                for (int i = 0; i < gg.childCount; i++) { gotGo++; gotNames.Add(gg.GetChild(i).name); }
            }
            // ⭐ 地形の木は**点ごとに**突き合わせる(EDO-0401・2026-09-23)── ⛔ 外接矩形の内を数えない。
            //   矩形の辺の上の点は正規化座標の往復で外へ落ち(11 本の数え落とし)、余白を足せば隣の敷地の木を拾う。
            //   焼き出しの点(地形の木・下層)から 5cm 以内に地形の木が在れば「植わっている」と数える。
            int gotTerrain = -1;
            try
            {
                var ter = EdoBuild.T();
                var td = ter.terrainData; var tp = ter.transform.position;
                const float tol = 0.05f;
                var cells = new Dictionary<long, List<Vector2>>();
                Func<float, float, long> key = (x, z) => ((long)Mathf.FloorToInt(x) << 32) ^ (uint)Mathf.FloorToInt(z);
                // ⭐ 点は**幹の足の中心**(Stage7 は TreePivotForTrunk でピボットをずらして植える・EDO-0409)── 検めも幹の芯で測る。
                //    ⛔ 2026-10-01 までピボットで測り、根張りを付けた木(EDO-0488)で幹とピボットが 5cm を超えて離れ、
                //    2,191 本のうち 347 本しか数えなかった(EDO-0495)。
                var footOf = new Dictionary<int, Vector2>(); var protos = td.treePrototypes;
                foreach (var ti in td.treeInstances)
                {
                    Vector2 fl;
                    if (!footOf.TryGetValue(ti.prototypeIndex, out fl))
                    {
                        var pf = protos[ti.prototypeIndex].prefab;
                        fl = pf == null ? Vector2.zero : EdoBuild.TrunkFootLocal(AssetDatabase.GetAssetPath(pf));
                        footOf[ti.prototypeIndex] = fl;
                    }
                    var d3 = Quaternion.AngleAxis(ti.rotation * Mathf.Rad2Deg, Vector3.up) * new Vector3(fl.x * ti.widthScale, 0f, fl.y * ti.widthScale);
                    float wx = tp.x + ti.position.x * td.size.x + d3.x, wz = tp.z + ti.position.z * td.size.z + d3.z;
                    if (wx < mnx - 1f || wx > mxx + 1f || wz < mnz - 1f || wz > mxz + 1f) continue;
                    long k = key(wx, wz); List<Vector2> l;
                    if (!cells.TryGetValue(k, out l)) cells[k] = l = new List<Vector2>();
                    l.Add(new Vector2(wx, wz));
                }
                gotTerrain = 0;
                foreach (var o in pts)
                {
                    var p = o as Dictionary<string, object>; if (p == null) continue;
                    if (Str(p, "place") == "GameObject") continue;
                    var w = A(p, "world"); if (w == null || w.Length < 2) continue;
                    bool hit = false;
                    for (int dx = -1; dx <= 1 && !hit; dx++)
                        for (int dz = -1; dz <= 1 && !hit; dz++)
                        {
                            List<Vector2> l;
                            if (!cells.TryGetValue(key(w[0] + dx, w[1] + dz), out l)) continue;
                            foreach (var c in l)
                                if ((c - new Vector2(w[0], w[1])).sqrMagnitude <= tol * tol) { hit = true; break; }
                        }
                    if (hit) gotTerrain++;
                }
            }
            catch (Exception) { }
            head.AppendLine("  社叢の実測: 焼き出し " + pts.Count + " 点(地形の木 " + wantTree + " / 下層 " +
                            wantDetail + " / 名指し " + namedWant.Count + ")対 実装 GameObject " + gotGo +
                            " 本" + (gotTerrain < 0 ? "" : " + 地形の木 " + gotTerrain + " 本(焼き出しの点から 5cm 以内に植わっている数)"));
            if (wantTree + wantDetail != gotGo + Mathf.Max(0, gotTerrain))
                bad("社叢", "社叢の木の数が違う(焼き出し " + (wantTree + wantDetail) + " 本 / 実装 " +
                    (gotGo + Mathf.Max(0, gotTerrain)) + " 本)");
            int missing = 0;
            foreach (var nm in namedWant) if (nm != null && ByName(index, nm) == null) missing++;
            if (missing > 0)
                bad("社叢", "名指しの木 " + namedWant.Count + " 本のうち " + missing + " 本が実装に無い");
            int bam = 0;
            foreach (var nm in gotNames) if (nm != null && nm.StartsWith("Bam_")) bam++;
            if (bam > 0)
                bad("社叢", "焼き出しに無い竹が " + bam + " 本据わっている(社叢の層は 松/落葉/中木/低木/下草 のみ)");
        }

        return Render(head.ToString(), hits);
    }

    // =====================================================================
    static string Render(string head, Dictionary<string, List<string>> hits)
    {
        int total = 0;
        foreach (var s in SECTIONS) total += hits[s].Count;
        var sb = new StringBuilder();
        // ⭐ 件数を**返り値の先頭**に置く(規則19 — 0件は合格ではなく未測定なので数から読ませる)
        sb.AppendLine(total == 0 ? "指図と実装の突き合わせ: 0 件"
                                 : "★ 指図と実装の不一致 " + total + " 件");
        sb.Append(head);
        sb.AppendLine("── 部門別 ──");
        foreach (var s in SECTIONS)
        {
            var l = hits[s];
            sb.AppendLine("  " + s + ": " + (l.Count == 0 ? "0 件 ✔" : l.Count + " 件 ✗"));
            for (int i = 0; i < l.Count; i++) sb.AppendLine("      ★ " + l[i]);
        }
        sb.AppendLine(total == 0 ? "指図と実装の突き合わせ: 0 件"
                                 : "★ 指図と実装の不一致 " + total + " 件");
        return sb.ToString();
    }

    /// <summary>ルートの下を全部拾う。⛔ **退避した旧実装(`Kyu_z857`)の下は数えない** —
    /// 2026-09-10 の建て直しで、z=857 の旧実装は削除せず非活性の群へ束ねた(規則1の趣旨)。
    /// ⛔ 数えると「据えたのに孤児」で ✗ が立ち、**退避が欠陥として出る**。</summary>
    static void Collect(Transform t, List<Transform> outp)
    {
        for (int i = 0; i < t.childCount; i++)
        {
            var c = t.GetChild(i);
            if (c.name == EdoSannoShaRebuild.GROUP_OLD) continue;
            outp.Add(c); Collect(c, outp);
        }
    }
    static Transform ByName(List<Transform> index, string name)
    { foreach (var t in index) if (t.name == name) return t; return null; }
    static List<Transform> ByPrefix(List<Transform> index, string pfx)
    { var r = new List<Transform>(); foreach (var t in index) if (t.name.StartsWith(pfx)) r.Add(t); return r; }

    /// <summary>段石の**踏面の平らな所の幅**[m](実寸)。駒の局所で、段鼻(局所 +Z の最大 = 坂下の縁)から <paramref name="back"/> 奥の横一線を
    /// 0.005 刻みで上から切り、上を向いた面の高さが踏面(局所 Y の最大)から 0.005 以内の最も長い一続き(石の割りの目地 ≤ 0.05 は跨ぐ)を幅とする。
    /// 端を法で切った駒・相手の石へ沿わせた駒でも、踏面の縁で読む(外接箱で読まない)。</summary>
    static float TreadWidthAtNosing(Transform stp, float back)
    {
        var tris = new List<Vector3[]>();
        float mnx = float.MaxValue, mxx = float.MinValue, mxz = float.MinValue, mxy = float.MinValue;
        var W2L = stp.worldToLocalMatrix;
        foreach (var mf in stp.GetComponentsInChildren<MeshFilter>())
        {
            var rr = mf.GetComponent<Renderer>(); if (mf.sharedMesh == null || rr == null || !rr.enabled) continue;
            var M = W2L * mf.transform.localToWorldMatrix; var vs = mf.sharedMesh.vertices; var ts = mf.sharedMesh.triangles;
            var L = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) { L[i] = M.MultiplyPoint3x4(vs[i]); mnx = Mathf.Min(mnx, L[i].x); mxx = Mathf.Max(mxx, L[i].x); mxz = Mathf.Max(mxz, L[i].z); mxy = Mathf.Max(mxy, L[i].y); }
            for (int t = 0; t + 2 < ts.Length; t += 3) tris.Add(new[] { L[ts[t]], L[ts[t + 1]], L[ts[t + 2]] });
        }
        if (tris.Count == 0) return 0f;
        // 踏面は石の割りの目地(幅 ≤ JOINT)で途切れる ⇒ 目地は跨いで一続きに数える
        const float JOINT = 0.05f;
        float z = mxz - back, best = 0f, step = 0.005f, runStart = float.NaN, lastFlat = float.NaN;
        for (float x = mnx; x <= mxx + 1e-4f; x += step)
        {
            float top = float.NaN;
            foreach (var q in tris)
            {
                Vector3 a = q[0], b = q[1], c = q[2];
                float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-12f) continue;
                float l1 = ((b.z - c.z) * (x - c.x) + (c.x - b.x) * (z - c.z)) / d, l2 = ((c.z - a.z) * (x - c.x) + (a.x - c.x) * (z - c.z)) / d, l3 = 1f - l1 - l2;
                if (l1 < -1e-5f || l2 < -1e-5f || l3 < -1e-5f) continue;
                float y = l1 * a.y + l2 * b.y + l3 * c.y; if (float.IsNaN(top) || y > top) top = y;
            }
            bool flat = !float.IsNaN(top) && Mathf.Abs(top - mxy) <= 0.005f;
            if (flat) { if (float.IsNaN(runStart) || x - lastFlat > JOINT) runStart = x; lastFlat = x; best = Mathf.Max(best, x - runStart + step); }
        }
        return best * Mathf.Abs(stp.lossyScale.x);
    }

    /// <summary>DobeiRun が据える部材の名 `<run名>_<番号>f|b` から run 名を取り出す。
    /// 形が違えば null(=囲いの部材ではない)。</summary>
    static string RunPrefixOf(string n)
    {
        if (string.IsNullOrEmpty(n)) return null;
        char last = n[n.Length - 1];
        if (last != 'f' && last != 'b') return null;
        int i = n.Length - 2;
        int digits = 0;
        while (i >= 0 && n[i] >= '0' && n[i] <= '9') { i--; digits++; }
        // ⭐ 柱と板を分けた組(EdoBuild.PostBoardRun)は `<run名>_h<番号>f|b`(柱)・`_i<番号>f|b`(板)── 番号の前の一字を読み飛ばす(2026-09-26 EDO-0437)
        //   地覆の組(EdoBuild.PostBoardRunScribed)の地覆 `_j<番号>f|b` も同じ(2026-09-27)
        if (digits > 0 && i > 0 && (n[i] == 'h' || n[i] == 'i' || n[i] == 'j') && n[i - 1] == '_') i--;
        if (digits == 0 || i <= 0 || n[i] != '_') return null;
        return n.Substring(0, i);
    }

    /// <summary>指図の名(括弧書きを含む)を、名簿の**先頭一致**で引く。</summary>
    static string Lookup(Dictionary<string, string> map, string designName)
    {
        foreach (var kv in map) if (designName.StartsWith(kv.Key)) return kv.Value;
        return null;
    }
    /// <summary>名簿に**行があるか**(値が null でも true)。⛔ Lookup の null と区別する。</summary>
    static bool HasKey(Dictionary<string, string> map, string designName)
    {
        foreach (var kv in map) if (designName.StartsWith(kv.Key)) return true;
        return false;
    }
    static Dictionary<string, object> FindMune(Dictionary<string, object> doc, string name)
    {
        foreach (var o in L(doc, "munes"))
        { var m = o as Dictionary<string, object>; if (m != null && Str(m, "name") == name) return m; }
        return null;
    }
    static Dictionary<string, object> FindByName(Dictionary<string, object> src, string key, string name)
    {
        foreach (var o in L(src, key))
        { var m = o as Dictionary<string, object>; if (m != null && Str(m, "name") == name) return m; }
        return null;
    }
    static Vector2[] Poly(List<object> l)
    {
        var r = new List<Vector2>();
        foreach (var o in l) { var p = o as List<object>; if (p != null && p.Count >= 2) r.Add(new Vector2(Cv(p[0]), Cv(p[1]))); }
        return r.ToArray();
    }
    static Vector2 P2(object o)
    { var p = o as List<object>; return p == null || p.Count < 2 ? Vector2.zero : new Vector2(Cv(p[0]), Cv(p[1])); }
    static bool Inside(Vector2[] p, float x, float z)
    {
        bool ins = false;
        for (int i = 0, j = p.Length - 1; i < p.Length; j = i++)
            if (((p[i].y > z) != (p[j].y > z)) &&
                (x < (p[j].x - p[i].x) * (z - p[i].y) / (p[j].y - p[i].y) + p[i].x)) ins = !ins;
        return ins;
    }
    static float PolyLen(List<Vector2> p)
    { float s = 0f; for (int i = 1; i < p.Count; i++) s += Vector2.Distance(p[i - 1], p[i]); return s; }
    /// <summary>折れ線上の弧長 s の点。</summary>
    static Vector2 PolyAt(List<Vector2> p, float s)
    {
        float acc = 0f;
        for (int i = 1; i < p.Count; i++)
        {
            float l = Vector2.Distance(p[i - 1], p[i]); if (l < 1e-6f) continue;
            if (s <= acc + l || i == p.Count - 1) return Vector2.Lerp(p[i - 1], p[i], Mathf.Clamp01((s - acc) / l));
            acc += l;
        }
        return p[p.Count - 1];
    }
    static string V(Vector2 v) { return "(" + v.x.ToString("F1") + ", " + v.y.ToString("F1") + ")"; }
    /// <summary>角を [0,360) へ畳む(⛔ 差の判定は `Mathf.DeltaAngle` — 359° と 1° を 358° 差にしない)。</summary>
    static float Norm360(float deg) { float d = deg % 360f; return d < 0f ? d + 360f : d; }
    static string FirstLine(string s)
    { if (string.IsNullOrEmpty(s)) return ""; int i = s.IndexOf('\n'); return (i < 0 ? s : s.Substring(0, i)).Trim(); }

    static readonly CultureInfo IC = CultureInfo.InvariantCulture;
    static float Cv(object o) { return o == null ? 0f : Convert.ToSingle(o, IC); }
    static object G(Dictionary<string, object> d, string k)
    { object v; return d != null && d.TryGetValue(k, out v) ? v : null; }
    static float F(Dictionary<string, object> d, string k) { return Cv(G(d, k)); }
    static Dictionary<string, object> D(Dictionary<string, object> d, string k)
    { return G(d, k) as Dictionary<string, object>; }
    static List<object> L(Dictionary<string, object> d, string k)
    { return G(d, k) as List<object> ?? new List<object>(); }
    static string Str(Dictionary<string, object> d, string k)
    { var o = G(d, k); return o == null ? null : o.ToString(); }
    static float[] A(Dictionary<string, object> d, string k)
    {
        var l = G(d, k) as List<object>; if (l == null) return null;
        var r = new float[l.Count];
        for (int i = 0; i < l.Count; i++) r[i] = Cv(l[i]);
        return r;
    }
}
