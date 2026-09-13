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

    // ---- 物差し(⛔ 設計値ではない。二つだけ)-------------------------------
    /// <summary>位置・寸法の許容差[m]。**汎用の器 `EdoSashizuExport.CheckScene` と同じ 0.02m**
    /// を借りる(⛔ 山王のためだけの緩い数を新しく作らない)。</summary>
    const float POS_TOL_M = 0.02f;
    /// <summary>地形と設計面の許容差[m]は**算出物が持つ**(`checks.gradeTol`)。⛔ ここに写さない。</summary>

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
    };
    static readonly Dictionary<string, string> GATE_NAME = new Dictionary<string, string>
    {
        { "隨身門", "Zuijinmon" }, { "坂下の門", "Niomon" },
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
        foreach (var o in L(doc, "munes"))
        {
            var m = o as Dictionary<string, object>; if (m == null) continue;
            string name = Str(m, "name"); if (name == null) continue;
            Vector2 want = W(F(m, "u0") + F(m, "du") * 0.5f, F(m, "v0") + F(m, "dv") * 0.5f);
            string scn = Lookup(MUNE_NAME, name);
            if (scn == null) { bad("社殿", "棟 " + name + " が実装に無い(名簿にも載っていない)"); continue; }
            var t = ByName(index, scn);
            if (t == null) { bad("社殿", "棟 " + name + "(実装名 " + scn + ")が実装に無い"); continue; }
            mapped.Add(scn);
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
            var sg = root.transform.Find(SHADEN_GROUP);
            if (sg != null)
                for (int i = 0; i < sg.childCount; i++)
                {
                    string n = sg.GetChild(i).name;
                    if (!mapped.Contains(n)) bad("社殿", "孤児(指図に無い): " + SHADEN_GROUP + "/" + n);
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
        foreach (var o in L(impl, "gates"))
        {
            var gt = o as Dictionary<string, object>; if (gt == null) continue;
            string name = Str(gt, "name"); if (name == null) continue;
            var wp = A(gt, "world");
            if (wp == null || wp.Length < 2) { bad("門・鳥居", "門 " + name + " の world が算出物に無い"); continue; }
            Vector2 want = new Vector2(wp[0], wp[1]);
            string scn = Lookup(GATE_NAME, name);
            if (scn == null) { bad("門・鳥居", "門 " + name + " が実装に無い(名簿にも載っていない)"); continue; }
            var t = ByName(index, scn);
            if (t == null) { bad("門・鳥居", "門 " + name + "(実装名 " + scn + ")が実装に無い"); continue; }
            var c = EdoBuild.RB(t.gameObject).center;
            float dd = Vector2.Distance(new Vector2(c.x, c.z), want);
            if (dd > POS_TOL_M)
                bad("門・鳥居", "門 " + name + " が " + dd.ToString("F2") + "m ずれている(指図 " +
                    V(want) + " / 実装 " + V(new Vector2(c.x, c.z)) + ")");
        }
        foreach (var o in L(doc, "torii"))
        {
            var tr = o as Dictionary<string, object>; if (tr == null) continue;
            string name = Str(tr, "name"); if (name == null) continue;
            var wp = A(tr, "pos");
            if (wp == null || wp.Length < 2) { bad("門・鳥居", "鳥居 " + name + " の pos が指図に無い"); continue; }
            Vector2 want = new Vector2(wp[0], wp[1]);
            string scn = Lookup(TORII_NAME, name);
            if (scn == null) { bad("門・鳥居", "鳥居 " + name + " が実装に無い(名簿にも載っていない)"); continue; }
            var t = ByName(index, scn);
            if (t == null) { bad("門・鳥居", "鳥居 " + name + "(実装名 " + scn + ")が実装に無い"); continue; }
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
            string spec = Lookup(KAIDAN_GROUP, name);
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
                Vector3 c0 = t.position;
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
            if (steps.Count > 0)
            {
                float mnx, mxx, mnz, mxz, mny;
                EdoBuild.ObbFootprint(steps[steps.Count / 2], out mnx, out mxx, out mnz, out mxz, out mny);
                float wGot = mxx - mnx;
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
                string pfx = RunPrefixOf(t.name);
                if (pfx == null) continue;
                if (!byPrefix.ContainsKey(pfx)) byPrefix[pfx] = new List<Transform>();
                byPrefix[pfx].Add(t);
            }
            var wantNames = new HashSet<string>();
            // ⭐ **土留め 13本**(`terraceWalls`)も囲いの部門で見る。⛔ 名簿に入れないと
            //   据えた石垣が丸ごと「孤児」に化け、⛔ **据えたことが欠陥として出る**。
            //   ⚠ 埋まっている区間(見付 ≤ 0 かつ 受け > 0)は**建てないのが正**(裁定 EDO-0182 が未着手)
            //   なので、⛔ ここでは延長を突き合わせない — 見るのは「一つも建っていない」かどうかだけ。
            foreach (var o in L(doc, "terraceWalls"))
            {
                var tw = o as Dictionary<string, object>; if (tw == null) continue;
                string tn = Str(tw, "name"); if (tn == null) continue;
                wantNames.Add(tn);
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
                // 線形 — 算出物の折れ線と、据わっている部材の広がりを比べる
                var ir = FindByName(impl, "runs", name);
                if (ir == null) continue;
                var nd = L(ir, "nodes"); if (nd.Count < 2) continue;
                // ⚠⚠ **折れ線の両端の中点は run の芯ではない。**`Ita_Keidai` は 43点で境内を回るので、
                //   両端の中点は run のどこでもない点になる(2026-09-10 実測: 49.85m の偽の差)。
                //   ⇒ **折れ線の外接矩形の芯**どうしで比べる。
                // ⚠ 部材は表裏2枚(`_kf` / `_kb`)で据わり、裏は run から 0.12m 逃がしてある。
                //   ⇒ **表(`f`)だけ**を測る(でないと run の芯が半厚ぶん = 0.06m ずれて出る)。
                // ⚠ 比べる相手は **`segs`(建つ区間)** の外接矩形。⛔ `nodes` ではない —
                //   `nodes` には口(木戸・井戸)と skip(部材にならない切れ端)が入っており、
                //   建たない区間まで含めると芯が動く(`Ita_Keidai` は skip 3 本を持つ)。
                float nx0 = float.MaxValue, nx1 = float.MinValue, nz0 = float.MaxValue, nz1 = float.MinValue;
                foreach (var so in L(ir, "segs"))
                {
                    var sg2 = so as List<object>; if (sg2 == null) continue;
                    foreach (var q in sg2)
                    {
                        Vector2 v2 = P2(q);
                        nx0 = Mathf.Min(nx0, v2.x); nx1 = Mathf.Max(nx1, v2.x);
                        nz0 = Mathf.Min(nz0, v2.y); nz1 = Mathf.Max(nz1, v2.y);
                    }
                }
                if (nx0 > nx1) continue;
                Bounds bb = new Bounds(); bool first = true;
                foreach (var t in byPrefix[name])
                {
                    if (!t.name.EndsWith("f")) continue;
                    var rb = EdoBuild.RB(t.gameObject); if (first) { bb = rb; first = false; } else bb.Encapsulate(rb);
                }
                if (first) continue;
                Vector2 wantMid = new Vector2((nx0 + nx1) * 0.5f, (nz0 + nz1) * 0.5f);
                Vector2 gotMid = new Vector2(bb.center.x, bb.center.z);
                // ⚠ **部材1枚に満たない切れ端**は据えられないので、その run は芯が寄って出る。
                //   ⛔ 数から黙って除かない — **何本あるか**を message に出して人の目へ渡す
                //   (指図の `_pending`「境内の外周の柵に部材として建たない切れ端が1本残る」)。
                int stub = 0; float stubM = 0f;
                foreach (var so in L(ir, "segs"))
                {
                    var sg3 = so as List<object>; if (sg3 == null || sg3.Count < 2) continue;
                    float sl = Vector2.Distance(P2(sg3[0]), P2(sg3[1]));
                    if (sl < 1.0f) { stub++; stubM += sl; }
                }
                float dd = Vector2.Distance(wantMid, gotMid);
                if (dd > POS_TOL_M)
                    bad("囲い", "囲い " + name + " の芯が " + dd.ToString("F2") + "m ずれている(指図 " +
                        V(wantMid) + " / 実装 " + V(gotMid) + ")" +
                        (stub > 0 ? " ⚠ **部材1枚に満たない切れ端が " + stub + " 本(計 " + stubM.ToString("F2") +
                                    "m)** ある — 据えられないので芯がそのぶん寄る(`_pending`「境内の外周の柵に部材として建たない切れ端が1本残る」)"
                                  : ""));
            }
            foreach (var kv in byPrefix)
                if (!wantNames.Contains(kv.Key))
                    bad("囲い", "孤児(指図に無い囲い): " + kv.Key + " ×" + kv.Value.Count + " 部材");
        }

        // =====================================================================
        // 造成の面 — 算出物の面の輪郭の中で、地形が設計の丈に届いているか
        // =====================================================================
        {
            float gradeTol = F(D(impl, "checks"), "gradeTol");
            Terrain ter = null;
            try { ter = EdoBuild.T(); } catch (Exception) { }
            if (ter == null) bad("造成の面", "アクティブな Terrain が無いので面を測れない");
            else
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
                    int n = 0, over = 0; float worst = 0f; Vector2 worstAt = Vector2.zero;
                    for (float x = mnx; x <= mxx; x += 2f)
                        for (float z = mnz; z <= mxz; z += 2f)
                        {
                            if (!Inside(poly, x, z)) continue;
                            n++;
                            float d = EdoBuild.Ground(x, z) - y;
                            if (Mathf.Abs(d) > gradeTol) over++;
                            if (Mathf.Abs(d) > Mathf.Abs(worst)) { worst = d; worstAt = new Vector2(x, z); }
                        }
                    if (n == 0) { bad("造成の面", "面 " + name + " に標本が取れない(輪郭が壊れている)"); continue; }
                    if (over > 0)
                        bad("造成の面", "面 " + name + "(設計 y=" + y.ToString("F2") + ")が造成されていない — 標本 " +
                            n + " 点中 " + over + " 点が許容 " + gradeTol.ToString("F2") + "m の外。最大 " +
                            worst.ToString("F2") + "m @ " + V(worstAt));
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
            int gotTerrain = -1;
            try
            {
                var ter = EdoBuild.T();
                var td = ter.terrainData; var tp = ter.transform.position;
                gotTerrain = 0;
                foreach (var ti in td.treeInstances)
                {
                    float wx = tp.x + ti.position.x * td.size.x, wz = tp.z + ti.position.z * td.size.z;
                    if (wx >= mnx && wx <= mxx && wz >= mnz && wz <= mxz) gotTerrain++;
                }
            }
            catch (Exception) { }
            head.AppendLine("  社叢の実測: 焼き出し " + pts.Count + " 点(地形の木 " + wantTree + " / 下層 " +
                            wantDetail + " / 名指し " + namedWant.Count + ")対 実装 GameObject " + gotGo +
                            " 本" + (gotTerrain < 0 ? "" : " + 地形の木 " + gotTerrain + " 本(焼き出しの外接矩形の内)"));
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
