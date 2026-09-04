using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;
using UnityEditor;

/// <summary>指図(設計図)と実装を**突き合わせる**。
///
/// 【順序を間違えないこと】この道具は指図を**作る**物ではない。順序は
///
///     設計(指図を書く) → レビュー → 実装 → **指図を更新** → 突き合わせて 0 件を確認
///
/// 指図から実装を生成するのでも、実装から指図を生成するのでもない。
/// **指図が正典**で、人が書く。この道具は「書いた指図と建った物がズレていないか」だけを見る。
/// 実装から指図を自動生成すると、CLAUDE.md 絶対規則2「指図を先に起こす」の関門が消える
/// (ユーザー指摘 2026-08-20)。
///
/// 【使い方】
///   1. 設計を変える  … `docs/Sashizu/okabe_sashizu.json` を直す(ここが正典)
///   2. 指図を組む    … `python3 Tools/Sashizu/build_okabe_sashizu.py`
///   3. レビュー      … edo-kosho / edo-kenzu → ユーザー
///   4. 実装          … ビルダーが指図を**読む**(値を写さない)
///   5. **突き合わせ**… このメニュー。差分 0 件になるまで直す
///      建ててみて指図のほうが誤りだと分かったら、**指図を直してから**再度合わせる
///   6. 経緯          … コミットメッセージと git log。**指図には残さない**
///
/// ⚠ 2026-09-03: 岡部専用だった `Check()`(旧スキーマ)と現況の書き出し `Build()` を撤去し、
///   全邸を <see cref="CheckScene"/> の一本へ寄せた。結果は**部門別**(造成/外周/主郭/庭/西の斜面)
///   に出るので、屋敷を建て終わる前でも段階ごとに合格線を引ける。</summary>
public static class EdoSashizuExport
{
    /// <summary>屋敷テーブル — 指図(json)のパスとシーンの対象。**屋敷を足すときはここに1行足す**
    /// (突き合わせの器そのものは屋敷を知らない)。
    ///   doc     … 指図の json(正典)
    ///   impl    … 生成器が焼いた「実装が読む算出物」(隅・竹垣など指図が持たない物)。無ければ null
    ///   root    … シーンのルート GameObject 名
    ///   parcel  … EdoParcels の区画 id
    ///   gradeQA … 造成の検査(部門別の集計に載せる)。持たない邸は null
    ///   implQA  … 生成器が焼いた算出物の検め。⭐ **地形より先に見る** — 算出物が古い/欠けて
    ///             いれば、地形の検査は「合っている」と嘘をつく(比べる相手が古いだけ)
    ///   pivot   … 棟・廊下の**据え付け点**。⚠ 部材キットの原点は「外形の角・走りが +X」なので、
    ///             フレームの手前(u+/v+ の向き)が邸ごとに違うと角も変わる。⛔ 検査だけが
    ///             式を持つと実装とズレるので、**ビルダーの式をそのまま呼ぶ**。null なら松平式
    /// ⚠ 2026-09-03: 岡部を**汎用の突き合わせへ寄せた**。旧 `Check()` は段を x0/x1/z0/z1、run を
    ///   top/seat/wall で比べる**旧スキーマ専用**で、回転間グリッドへ移った指図と噛み合わず
    ///   ✗ が 100件超のまま固まっていた。現況の書き出し `Build()` も同じ理由で撤去した。</summary>
    public class Yashiki
    {
        public string label, doc, impl, root, parcel;
        public Func<string> gradeQA;
        public Func<string> implQA;
        public Func<Dictionary<string, object>, string, Vector2> pivot;
    }
    public static readonly Dictionary<string, Yashiki> Houses = new Dictionary<string, Yashiki>
    {
        { "okabe", new Yashiki { label = "Okabe", doc = EdoOkabeYashikiBuilder.SashizuRel,
                                 impl = EdoOkabeYashikiBuilder.ImplRel,
                                 root = EdoOkabeYashikiBuilder.GN, parcel = EdoOkabeYashikiBuilder.ParcelId,
                                 gradeQA = EdoOkabeYashikiBuilder.GradeQA,
                                 implQA = EdoOkabeYashikiBuilder.ImplQA,
                                 pivot = EdoOkabeYashikiBuilder.Pivot } },
        { "matsudaira_dewa", new Yashiki { label = "MatsudairaDewa", doc = EdoMatsudairaDewaBuilder.SashizuRel,
                                      root = EdoMatsudairaDewaBuilder.Grp,
                                      parcel = EdoMatsudairaDewaBuilder.ParcelId } },
        // 土井のルート名は EdoSannoKitaBuilder.Stage2_Doi が建てた実物(2026-08-26 実機確認)
        { "doi", new Yashiki { label = "Doi", doc = "docs/Sashizu/doi_sashizu.json",
                               root = "Edo_Yashiki_DoiOsumi", parcel = "doi" } },
    };
    static string DOC { get { return Houses["okabe"].doc; } }
    static readonly CultureInfo IC = CultureInfo.InvariantCulture;

    [MenuItem("Edo/岡部筑前守上屋敷/指図と実装を突き合わせる")]
    public static void CheckMenu() { Debug.Log("[Okabe] " + CheckScene("okabe")); }

    [MenuItem("Edo/土井大隅守上屋敷/指図と実装を突き合わせる")]
    public static void CheckDoiMenu() { Debug.Log("[Doi] " + CheckScene("doi")); }

    // =====================================================================
    // 汎用の突き合わせ — 回転間グリッド式(grid.shukaku)の指図と、据わっている現物を照合する
    // =====================================================================

    /// <summary>回転間グリッド式の指図(matsudaira / doi)の、指図と実装の突き合わせ。
    /// 検査項目は松平のインライン実装(2026-08-23 の是正 — 「本数と GradeQA しか見ておらず
    /// 106m ずれた棟が 0 件で通る」対策)を**そのまま一般化した物**:
    ///   表門の位置(json pos と 辺+s の整合)/棟・廊下の位置と存在/孤児(指図に無い現物)/
    ///   囲い run・fence の部材の存在/郭内の造作(Fuzoku 下の各群)。
    /// ⚠ 棟の照合点は Grid.W(u0, v1)(松平ビルダーの据え付けピボット)。指図に無い群
    /// (fences・nakajikiri など)は空として扱うので、屋敷ごとに項目を持ち替えなくてよい。</summary>
    /// <summary>**検図関門(実装側)。**指図が検分を通っていなければ Stage を止める。
    ///
    /// ⚠ 2026-09-01 に検図が指摘した事故の型: 松江松平の Stage7 は指図の `poly`/`at`/`groups`/
    ///   `clr` を一つも読まず、**撤回済みの「松を全数 −u へ傾ける」がコードに生きていた**。
    ///   この状態で流すと、指図で撤回した案がシーンへ復活する。
    ///   ⛔ 散文の規則(CLAUDE.md 規則18「関門が赤の指図を実装しない」)は破れるので機械で止める。
    ///
    /// 判定は指図の `reviews`(`Tools/Sashizu/review_gate.py` が書く)を読むだけ。
    ///   ・`verdict == "fail"` … **止める**
    ///   ・記録が無い/`hash` がずれている … **警告だけ**(2026-09-01 のユーザー裁定で移行期間中。
    ///     関門を新設した時点で全邸が赤なので、止めると全セッションが即時停止する)
    /// ⭐ 移行が終わったら「記録が無い」も止める側へ移す。
    ///
    /// 返り値: 止めるべきなら理由、流してよいなら null(警告は Debug.LogWarning で出す)。</summary>
    public static string ReviewGate(string id)
    {
        if (!Houses.ContainsKey(id)) return null;
        var path = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), Houses[id].doc);
        if (!System.IO.File.Exists(path)) return null;
        var doc = MiniJson.Parse(System.IO.File.ReadAllText(path)) as Dictionary<string, object>;
        if (doc == null) return null;
        var rev = doc.ContainsKey("reviews") ? doc["reviews"] as Dictionary<string, object> : null;
        var stop = new List<string>();
        var warn = new List<string>();
        foreach (var key in new[] { "kenzu", "kosho", "niwashi" })
        {
            var got = rev != null && rev.ContainsKey(key) ? rev[key] as Dictionary<string, object> : null;
            if (got == null) { warn.Add(key + "=記録なし"); continue; }
            string v = got.ContainsKey("verdict") ? got["verdict"] as string : null;
            if (v == "fail")
                stop.Add(key + "=不合格(" + (got.ContainsKey("at") ? got["at"] : "?") + ")");
        }
        if (warn.Count > 0)
            Debug.LogWarning("[検図関門] " + id + " — " + string.Join(" / ", warn.ToArray())
                + "\n  移行期間中なので止めないが、**ユーザーへ見せる前には必ず通すこと**。"
                + "\n  検分に出して `python3 Tools/Sashizu/review_gate.py --record " + id + " <役> <pass|fail>`。");
        if (stop.Count == 0) return null;
        return "⛔ 検図関門が赤: " + string.Join(" / ", stop.ToArray())
             + "\n  **不合格の指図を実装しない。**直して検分に出し直してから流すこと。"
             + "\n  詳細: python3 Tools/Sashizu/review_gate.py " + id
             + "\n  ⚠ どうしても流すなら理由をユーザーへ述べて、明示の指示を得ること。";
    }

    /// <summary>**部門**。段階ごとの合格線を引けるようにする(2026-09-03 ユーザー裁定=案a)。
    /// ⚠ 屋敷を全部建て終わるまで「0 件」にならない検査は、段階の途中では合否を語れない。
    ///   部門別に出せば「造成と外周は 0 件・主郭は未実装 N 件」と読める。</summary>
    static readonly string[] SECTIONS = { "造成", "外周", "主郭", "庭", "西の斜面" };

    public static string CheckScene(string id)
    {
        var hs = Houses[id];
        var path = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), hs.doc);
        if (!System.IO.File.Exists(path)) return "指図が無い: " + hs.doc;
        var doc = MiniJson.Parse(System.IO.File.ReadAllText(path)) as Dictionary<string, object>;
        if (doc == null) return "指図が読めない: " + hs.doc;
        // 生成器が焼いた算出物(隅・竹垣など、指図の json が持たない物)。無くても止めない
        Dictionary<string, object> impl = null;
        if (!string.IsNullOrEmpty(hs.impl))
        {
            var ip = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), hs.impl);
            if (System.IO.File.Exists(ip))
                impl = MiniJson.Parse(System.IO.File.ReadAllText(ip)) as Dictionary<string, object>;
        }

        var sb = new StringBuilder();
        var hits = new Dictionary<string, List<string>>();
        foreach (var sname in SECTIONS) hits[sname] = new List<string>();
        Action<string, string> bad = (sec, msg) => { hits[sec].Add(msg); };

        // ---- 回転間グリッド(EdoMatsudairaDewaBuilder.Frame と同じ式)----
        var g = D(D(doc, "grid"), "shukaku");
        float ken = F(D(doc, "const"), "ken");
        float gx0 = F(g, "x0"), gz0 = F(g, "z0");
        float gux = F(g, "ux"), guz = F(g, "uz"), gvx = F(g, "vx"), gvz = F(g, "vz");
        Func<float, float, Vector2> W = (u, v) =>
            new Vector2(gx0 + (gux * u + gvx * v) * ken, gz0 + (guz * u + gvz * v) * ken);
        var P = EdoParcels.Get(hs.parcel);

        var gate = D(doc, "gate");
        var gp = A(gate, "pos");
        Vector2 jsonPos = new Vector2(gp[0], gp[1]);
        Vector2 fromEdge = EdgePtOf(P, (int)F(gate, "edge"), F(gate, "s"));
        sb.AppendLine("表門: json pos=" + jsonPos + " / 辺+s から=" + fromEdge +
                      " 差=" + (jsonPos - fromEdge).magnitude.ToString("F3") + "m");
        sb.AppendLine("グリッド原点=(" + gx0 + "," + gz0 + ") 表門芯との差=" +
                      (new Vector2(gx0, gz0) - jsonPos).magnitude.ToString("F3") + "m");
        sb.AppendLine("段 " + Get2(doc, "terraces").Count + "枚 / run " + Get2(doc, "runs").Count +
                      "本 / 区画 " + P.Length + "頂点" + (impl == null ? "" : " / 算出物あり"));

        // ---- 造成 — 邸が検査を持っていればその結果を部門へ載せる
        // ⭐ **算出物を地形より先に見る。**算出物が古い/欠けていれば、地形の検査は
        //   「合っている」と嘘をつく(比べる相手が古いだけで、差がゼロに出る)。
        Action<Func<string>, string> runQA = (fn, label) =>
        {
            if (fn == null) return;
            string q;
            try { q = fn(); }
            catch (Exception ex) { q = "★ " + label + "が走らない: " + ex.Message; }
            sb.AppendLine("造成/" + label + ": " + FirstLine(q));
            // ⛔ StartsWith で見ない — ★ が2行目以降に出る報告(算出物の検め)を丸ごと取り逃がす
            if (EdoQaVerdict.Failed(q)) bad("造成", label + ": " + FirstLine(q));
        };
        runQA(hs.implQA, "算出物");
        runQA(hs.gradeQA, "地形");

        // ---- 名前 → 部門。**西の斜面の物は指図が名指しで持っている**(nishi.obi)
        var nishiNames = new HashSet<string>();
        {
            var obi = D(D(doc, "nishi"), "obi");
            if (obi != null)
                foreach (var key in new[] { "munes", "komono" })
                    foreach (var o in Get2(obi, key)) { var nm = o as string; if (nm != null) nishiNames.Add(nm); }
        }
        Func<string, string, string> secOf = (defSec, name) =>
            (name != null && nishiNames.Contains(name)) ? "西の斜面" : defSec;

        // ---- 据わっている現物を指図と照合する ★これが無いと 106m ずれた棟が「0件」で通る
        var root = GameObject.Find(hs.root);
        if (root == null) bad("主郭", "ルート " + hs.root + " が無い");
        else
        {
            var seen = new HashSet<string>();
            Action<Transform, string, Vector2, string, string> chk = (grp, name, want, kind, sec) =>
            {
                seen.Add(name);
                var t = grp == null ? null : grp.Find(name);
                if (t == null) { bad(sec, kind + " " + name + " が実装に無い"); return; }
                float dd = Vector2.Distance(new Vector2(t.position.x, t.position.z), want);
                if (dd > 0.02f) bad(sec, kind + " " + name + " が " + dd.ToString("F2") + "m ずれている");
            };
            var bld = root.transform.Find("Buildings");
            foreach (var o in Get2(doc, "munes"))
            {
                var m = o as Dictionary<string, object>; if (m == null) continue;
                chk(bld, Str(m, "name"),
                    hs.pivot != null ? hs.pivot(m, "mune") : W(F(m, "u0"), F(m, "v1")), "棟", "主郭");
            }
            foreach (var o in Get2(doc, "links"))
            {
                var l = o as Dictionary<string, object>; if (l == null) continue;
                float u0 = F(l, "u0"), v0 = F(l, "v0"), u1 = F(l, "u1"), v1 = F(l, "v1");
                bool alongU = (u1 - u0) >= (v1 - v0);
                chk(bld, Str(l, "name"),
                    hs.pivot != null ? hs.pivot(l, "link") : (alongU ? W(u0, v1) : W(u0, v0)),
                    "廊下", "主郭");
            }
            if (bld != null)
                for (int i = 0; i < bld.childCount; i++)
                {
                    string nm = bld.GetChild(i).name;
                    if (!seen.Contains(nm)) bad("主郭", "孤児(指図に無い): " + nm);
                }

            // ---- 外周 — 指図の run/fence/隅/門の名前が実装のグループ名に現れるか
            // 囲いは run/fence ごとに複数の部材(`S_Hei_C_0f` など)に分かれるので**前方一致**で数える
            {
                var have = new List<string>();
                foreach (var gname in new[] { "Kakoi", "Fences", "Omotemon", "Mon" })
                {
                    var gg = root.transform.Find(gname);
                    if (gg != null) for (int i = 0; i < gg.childCount; i++) have.Add(gg.GetChild(i).name);
                }
                var names = new List<string>();
                foreach (var o in Get2(doc, "runs")) names.Add(Str(o as Dictionary<string, object>, "name"));
                foreach (var o in Get2(doc, "fences")) names.Add(Str(o as Dictionary<string, object>, "name"));
                // 隅部材は **`runs` ではなく留め継ぎの表**に居る(留め継ぎは run ではない)。
                // ⚠ これを教えないと、据えた隅が全部「孤児の囲い」に見える(2026-08-30 に実際に出た)。
                //   指図が `joints` を持つ邸(松平)はそちら、算出物へ移した邸(岡部)は `impl.corners`。
                foreach (var o in Get2(doc, "joints"))
                {
                    var j = o as Dictionary<string, object>;
                    if (j != null && j.ContainsKey("kado")) names.Add("Kado_" + Str(j, "id"));
                }
                if (impl != null)
                    foreach (var o in Get2(impl, "corners"))
                    {
                        var c = o as Dictionary<string, object>;
                        if (c != null && c.ContainsKey("part") && c["part"] != null) names.Add("Kado_" + Str(c, "id"));
                    }
                foreach (var o in Get2(doc, "komon")) names.Add(Str(o as Dictionary<string, object>, "name"));
                // ⚠ **表門と汀の潜りは名前を持たない**(`gate` は単数・潜りは `nishi.saku.kuguri`)。
                //   ⛔ 教えないと、据えた門と戸が「孤児の囲い」に数えられる(2026-09-04 に実際に出た)。
                if (D(doc, "gate") != null) names.Add("Omotemon");
                if (D(D(D(doc, "nishi"), "saku"), "kuguri") != null) names.Add("Kuguri");
                foreach (var nm in names)
                {
                    if (nm == null) continue;
                    int c = 0;
                    foreach (var h in have) if (h == nm || h.StartsWith(nm + "_")) c++;
                    if (c == 0) bad("外周", "囲い " + nm + " の部材が実装に一つも無い");
                }
                foreach (var h in have)
                {
                    bool known = false;
                    foreach (var nm in names) if (nm != null && (h == nm || h.StartsWith(nm + "_"))) { known = true; break; }
                    if (!known) bad("外周", "孤児の囲い: " + h);
                }
            }

            // ---- 郭内の造作。名前の前方一致で「1本も置かれていない」を捕まえる
            {
                var fz = root.transform.Find("Fuzoku");
                Func<string, List<string>> kids = sub =>
                {
                    var outp = new List<string>();
                    var g2 = fz == null ? null : fz.Find(sub);
                    if (g2 != null) for (int i = 0; i < g2.childCount; i++) outp.Add(g2.GetChild(i).name);
                    return outp;
                };
                Action<string, List<string>, string, string> want = (sub, names, kind, defSec) =>
                {
                    var h = kids(sub);
                    foreach (var nm in names)
                    {
                        if (nm == null) continue;
                        int c = 0;
                        foreach (var q in h) if (q == nm || q.StartsWith(nm + "_")) c++;
                        if (c == 0) bad(secOf(defSec, nm), kind + " " + nm + " の部材が実装に一つも無い");
                    }
                    foreach (var q in h)
                    {
                        bool known = false;
                        foreach (var nm in names) if (nm != null && (q == nm || q.StartsWith(nm + "_"))) { known = true; break; }
                        if (!known) bad(defSec, "孤児の" + kind + ": " + q);
                    }
                };
                Func<Dictionary<string, object>, string, List<string>> jn = (src, key) =>
                {
                    var outp = new List<string>();
                    foreach (var o in Get2(src, key)) outp.Add(Str(o as Dictionary<string, object>, "name"));
                    return outp;
                };
                // ⚠ 法肩の竹垣は**指図の json に無い**邸がある(岡部は生成器の算出値)。
                //   doc に無ければ算出物から引く。⛔ 引かないと「0本を期待して、据えた竹垣を全部
                //   孤児と数える」ことになり、検査そのものが嘘をつく。
                var railNames = jn(doc, "rails");
                if (railNames.Count == 0 && impl != null) railNames = jn(impl, "rails");

                // ⚠ 屋敷の内部を分ける塀の欄名は邸で違う(松平=nakajikiri / 岡部=kekkai)。
                //   両方を期待集合に入れる。⛔ 片方しか見ないと、据えた結界が全部「孤児」になる。
                var shikiri = jn(doc, "nakajikiri");
                shikiri.AddRange(jn(doc, "kekkai"));
                want("Nakajikiri", shikiri, "中仕切", "主郭");
                want("Takegaki", railNames, "竹垣", "主郭");
                want("Kaidan", jn(doc, "kaidans"), "石段", "主郭");
                want("Ido", jn(doc, "wells"), "井戸", "主郭");
                want("Yagura", jn(doc, "yagura"), "隅櫓", "主郭");
                want("Service", jn(doc, "service"), "附属屋", "主郭");
                want("Niwa", jn(doc, "gardens"), "庭", "庭");
                // 井戸・附属屋は1個ものなので位置も見る
                foreach (var o in Get2(doc, "wells"))
                {
                    var w2 = o as Dictionary<string, object>; if (w2 == null) continue;
                    chk(fz == null ? null : fz.Find("Ido"), Str(w2, "name"),
                        W(F(w2, "u"), F(w2, "v")), "井戸", secOf("主郭", Str(w2, "name")));
                }
                foreach (var o in Get2(doc, "service"))
                {
                    var s2 = o as Dictionary<string, object>; if (s2 == null) continue;
                    chk(fz == null ? null : fz.Find("Service"), Str(s2, "name"),
                        W((F(s2, "u0") + F(s2, "u1")) * 0.5f, (F(s2, "v0") + F(s2, "v1")) * 0.5f),
                        "附属屋", secOf("主郭", Str(s2, "name")));
                }
            }
        }

        // ---- 部門別の集計 ------------------------------------------------
        int total = 0;
        sb.AppendLine("── 部門別 ──");
        foreach (var sname in SECTIONS)
        {
            var l = hits[sname]; total += l.Count;
            sb.AppendLine("  " + sname + ": " + (l.Count == 0 ? "0 件 ✔" : l.Count + " 件 ✗"));
            for (int i = 0; i < l.Count && i < 12; i++) sb.AppendLine("      ★ " + l[i]);
            if (l.Count > 12) sb.AppendLine("      …ほか " + (l.Count - 12) + " 件");
        }
        sb.AppendLine(total == 0 ? "指図と実装の突き合わせ: 0 件"
                                 : "★ 指図と実装の不一致 " + total + " 件");
        return sb.ToString();
    }

    static string FirstLine(string s)
    { if (string.IsNullOrEmpty(s)) return ""; int i = s.IndexOf('\n'); return (i < 0 ? s : s.Substring(0, i)).Trim(); }

    /// <summary>辺 edge の走り s[m] の世界座標(EdoMatsudairaDewaBuilder.EdgePt と同じ式)。</summary>
    static Vector2 EdgePtOf(Vector2[] P, int edge, float s)
    {
        int n = P.Length;
        Vector2 a = P[edge % n], b = P[(edge + 1) % n];
        Vector2 d = b - a; float L = d.magnitude;
        return a + d / Mathf.Max(1e-5f, L) * s;
    }

    /// <summary>指図(json)の `gate.plan` を読んで返す。**実装は寸法を写さずここから引く。**
    /// 定数へ写すと指図と実装が別々に動いてドリフトする(2026-08-21 に表門で実際に起きた)。</summary>
    public static Dictionary<string, object> GatePlan()
    {
        var path = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), DOC);
        if (!System.IO.File.Exists(path)) { Debug.LogError("[Okabe] 指図が無い: " + DOC); return null; }
        var doc = MiniJson.Parse(System.IO.File.ReadAllText(path)) as Dictionary<string, object>;
        if (doc == null) { Debug.LogError("[Okabe] 指図が読めない"); return null; }
        var g = Get(doc, "gate") as Dictionary<string, object>;
        return g == null ? null : Get(g, "plan") as Dictionary<string, object>;
    }
    static object Get(Dictionary<string, object> d, string k)
    { object v; return d != null && d.TryGetValue(k, out v) ? v : null; }
    public static float F(Dictionary<string, object> d, string k)
    { var v = Get(d, k); return v == null ? 0f : System.Convert.ToSingle(v, IC); }
    public static Dictionary<string, object> D(Dictionary<string, object> d, string k)
    { return Get(d, k) as Dictionary<string, object>; }
    public static List<object> Get2(Dictionary<string, object> d, string k)
    { return Get(d, k) as List<object> ?? new List<object>(); }
    public static float[] A(Dictionary<string, object> d, string k)
    {
        var l = Get(d, k) as List<object>; if (l == null) return null;
        var r = new float[l.Count];
        for (int i = 0; i < l.Count; i++) r[i] = System.Convert.ToSingle(l[i], IC);
        return r;
    }

    static string Str(Dictionary<string, object> d, string k)
    { object o; return d != null && d.TryGetValue(k, out o) && o != null ? o.ToString() : null; }

}

/// <summary>指図の json を読むだけの最小パーサ(Unity の JsonUtility は Dictionary と
/// 混合配列を扱えないため)。書き出しはしない。</summary>
static class MiniJson
{
    public static object Parse(string s) { int i = 0; return Val(s, ref i); }
    static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }
    static object Val(string s, ref int i)
    {
        Ws(s, ref i); if (i >= s.Length) return null;
        char c = s[i];
        if (c == '{') return Obj(s, ref i);
        if (c == '[') return Arr(s, ref i);
        if (c == '"') return Str(s, ref i);
        if (c == 't') { i += 4; return true; }
        if (c == 'f') { i += 5; return false; }
        if (c == 'n') { i += 4; return null; }
        int st = i;
        while (i < s.Length && "+-.eE0123456789".IndexOf(s[i]) >= 0) i++;
        double d; double.TryParse(s.Substring(st, i - st), System.Globalization.NumberStyles.Any,
                                  System.Globalization.CultureInfo.InvariantCulture, out d);
        return d;
    }
    static Dictionary<string, object> Obj(string s, ref int i)
    {
        var d = new Dictionary<string, object>(); i++;
        while (true)
        {
            Ws(s, ref i); if (i >= s.Length || s[i] == '}') { i++; return d; }
            string k = Str(s, ref i); Ws(s, ref i); if (i < s.Length && s[i] == ':') i++;
            d[k] = Val(s, ref i); Ws(s, ref i); if (i < s.Length && s[i] == ',') i++;
        }
    }
    static List<object> Arr(string s, ref int i)
    {
        var l = new List<object>(); i++;
        while (true)
        {
            Ws(s, ref i); if (i >= s.Length || s[i] == ']') { i++; return l; }
            l.Add(Val(s, ref i)); Ws(s, ref i); if (i < s.Length && s[i] == ',') i++;
        }
    }
    static string Str(string s, ref int i)
    {
        var sb = new StringBuilder(); i++;
        while (i < s.Length && s[i] != '"')
        {
            if (s[i] == '\\')
            {
                i++;
                char e = s[i++];
                if (e == 'n') sb.Append('\n'); else if (e == 't') sb.Append('\t');
                else if (e == 'u') { sb.Append((char)System.Convert.ToInt32(s.Substring(i, 4), 16)); i += 4; }
                else sb.Append(e);
            }
            else sb.Append(s[i++]);
        }
        i++; return sb.ToString();
    }
}
