using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;
using UnityEditor;
using SK = EdoSannoKitaBuilder;

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
///   4. 実装          … ビルダーの表を指図に合わせる
///   5. **突き合わせ**… このメニュー。差分 0 件になるまで直す
///      建ててみて指図のほうが誤りだと分かったら、**指図を直してから**再度合わせる
///   6. 経緯          … コミットメッセージと git log。**指図には残さない**
///
/// 現況だけを書き出したいとき(指図を新しく起こす種にするなど)は「現況を書き出す」を使う。</summary>
public static class EdoSashizuExport
{
    /// <summary>屋敷テーブル — 指図(json)のパスとシーンの対象。**屋敷を足すときはここに1行足す**
    /// (突き合わせの器そのものは屋敷を知らない)。
    ///   doc    … 指図の json(正典)
    ///   dump   … 現況の書き出し先(岡部のみ。他家は書き出しを持たない)
    ///   root   … シーンのルート GameObject 名
    ///   parcel … EdoParcels の区画 id(回転間グリッド式=matsudaira/doi のみ。岡部は SK.OKABE)</summary>
    public class Yashiki { public string label, doc, dump, root, parcel; }
    public static readonly Dictionary<string, Yashiki> Houses = new Dictionary<string, Yashiki>
    {
        { "okabe", new Yashiki { label = "Okabe", doc = "docs/Sashizu/okabe_sashizu.json",
                                 dump = "docs/Sashizu/okabe_current.json",
                                 root = EdoOkabeYashikiBuilder.GN, parcel = null } },
        { "matsudaira_dewa", new Yashiki { label = "MatsudairaDewa", doc = EdoMatsudairaDewaBuilder.SashizuRel,
                                      root = EdoMatsudairaDewaBuilder.Grp,
                                      parcel = EdoMatsudairaDewaBuilder.ParcelId } },
        // 土井のルート名は EdoSannoKitaBuilder.Stage2_Doi が建てた実物(2026-08-26 実機確認)
        { "doi", new Yashiki { label = "Doi", doc = "docs/Sashizu/doi_sashizu.json",
                               root = "Edo_Yashiki_DoiOsumi", parcel = "doi" } },
    };
    static string DOC { get { return Houses["okabe"].doc; } }
    static string DUMP { get { return Houses["okabe"].dump; } }
    static readonly CultureInfo IC = CultureInfo.InvariantCulture;
    const float TOL = 0.005f;

    [MenuItem("Edo/岡部筑前守上屋敷/指図と実装を突き合わせる")]
    public static void CheckMenu() { Debug.Log("[Okabe] " + Check()); }

    [MenuItem("Edo/岡部筑前守上屋敷/現況を書き出す(指図の種)")]
    public static void DumpMenu()
    {
        var path = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), DUMP);
        System.IO.File.WriteAllText(path, Build());
        AssetDatabase.Refresh();
        Debug.Log("[Okabe] 現況を書き出した: " + DUMP + "\n  ⚠ これは**指図ではない**。指図は " + DOC);
    }

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
    public static string CheckScene(string id)
    {
        var hs = Houses[id];
        var path = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), hs.doc);
        if (!System.IO.File.Exists(path)) return "指図が無い: " + hs.doc;
        var doc = MiniJson.Parse(System.IO.File.ReadAllText(path)) as Dictionary<string, object>;
        if (doc == null) return "指図が読めない: " + hs.doc;

        var sb = new StringBuilder();
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
                      "本 / 区画 " + P.Length + "頂点");

        // ---- 据わっている現物を指図と照合する ★これが無いと 106m ずれた棟が「0件」で通る
        int ng = 0;
        var root = GameObject.Find(hs.root);
        if (root == null) { sb.AppendLine("★ ルートが無い"); ng++; }
        else
        {
            var seen = new HashSet<string>();
            Action<Transform, string, Vector2, string> chk = (grp, name, want, kind) =>
            {
                seen.Add(name);
                var t = grp == null ? null : grp.Find(name);
                if (t == null) { sb.AppendLine("★ " + kind + " " + name + " が実装に無い"); ng++; return; }
                float dd = Vector2.Distance(new Vector2(t.position.x, t.position.z), want);
                if (dd > 0.02f)
                { sb.AppendLine("★ " + kind + " " + name + " が " + dd.ToString("F2") + "m ずれている"); ng++; }
            };
            var bld = root.transform.Find("Buildings");
            foreach (var o in Get2(doc, "munes"))
            {
                var m = o as Dictionary<string, object>; if (m == null) continue;
                var w = W(F(m, "u0"), F(m, "v1"));
                chk(bld, Str(m, "name"), w, "棟");
            }
            foreach (var o in Get2(doc, "links"))
            {
                var l = o as Dictionary<string, object>; if (l == null) continue;
                float u0 = F(l, "u0"), v0 = F(l, "v0"), u1 = F(l, "u1"), v1 = F(l, "v1");
                bool alongU = (u1 - u0) >= (v1 - v0);
                var w = alongU ? W(u0, v1) : W(u0, v0);
                chk(bld, Str(l, "name"), w, "廊下");
            }
            if (bld != null)
                for (int i = 0; i < bld.childCount; i++)
                {
                    string nm = bld.GetChild(i).name;
                    if (!seen.Contains(nm)) { sb.AppendLine("★ 孤児(指図に無い): " + nm); ng++; }
                }
            // 囲い — 指図の run/fence の名前が実装のグループ名に現れるか
            // 囲いは run/fence ごとに複数の部材(`S_Hei_C_0f` など)に分かれるので**前方一致**で数える
            var have = new List<string>();
            foreach (var gname in new[] { "Kakoi", "Fences" })
            {
                var gg = root.transform.Find(gname);
                if (gg != null) for (int i = 0; i < gg.childCount; i++) have.Add(gg.GetChild(i).name);
            }
            {
                var names = new List<string>();
                foreach (var o in Get2(doc, "runs")) names.Add(Str(o as Dictionary<string, object>, "name"));
                foreach (var o in Get2(doc, "fences")) names.Add(Str(o as Dictionary<string, object>, "name"));
                foreach (var nm in names)
                {
                    int c = 0;
                    foreach (var h in have) if (h == nm || h.StartsWith(nm + "_")) c++;
                    if (c == 0) { sb.AppendLine("★ 囲い " + nm + " の部材が実装に一つも無い"); ng++; }
                }
                foreach (var h in have)
                {
                    bool known = false;
                    foreach (var nm in names) if (h == nm || h.StartsWith(nm + "_")) { known = true; break; }
                    if (!known) { sb.AppendLine("★ 孤児の囲い: " + h); ng++; }
                }
            }
            // ---- 郭内の造作(Stage6)。名前の前方一致で「1本も置かれていない」を捕まえる
            {
                var fz = root.transform.Find("Fuzoku");
                Func<string, List<string>> kids = sub =>
                {
                    var outp = new List<string>();
                    var g2 = fz == null ? null : fz.Find(sub);
                    if (g2 != null) for (int i = 0; i < g2.childCount; i++) outp.Add(g2.GetChild(i).name);
                    return outp;
                };
                Action<string, List<string>, string> want = (sub, names, kind) =>
                {
                    var h = kids(sub);
                    foreach (var nm in names)
                    {
                        int c = 0;
                        foreach (var q in h) if (q == nm || q.StartsWith(nm + "_")) c++;
                        if (c == 0) { sb.AppendLine("★ " + kind + " " + nm + " の部材が実装に一つも無い"); ng++; }
                    }
                    foreach (var q in h)
                    {
                        bool known = false;
                        foreach (var nm in names) if (q == nm || q.StartsWith(nm + "_")) { known = true; break; }
                        if (!known) { sb.AppendLine("★ 孤児の" + kind + ": " + q); ng++; }
                    }
                };
                Func<string, List<string>> jn = key =>
                {
                    var outp = new List<string>();
                    foreach (var o in Get2(doc, key)) outp.Add(Str(o as Dictionary<string, object>, "name"));
                    return outp;
                };
                want("Nakajikiri", jn("nakajikiri"), "中仕切");
                want("Takegaki", jn("rails"), "竹垣");
                want("Kaidan", jn("kaidans"), "石段");
                want("Ido", jn("wells"), "井戸");
                want("Yagura", jn("yagura"), "隅櫓");
                want("Service", jn("service"), "附属屋");
                // 井戸・附属屋・隅櫓は1個ものなので位置も見る
                foreach (var o in Get2(doc, "wells"))
                {
                    var w2 = o as Dictionary<string, object>; if (w2 == null) continue;
                    chk(fz == null ? null : fz.Find("Ido"), Str(w2, "name"),
                        W(F(w2, "u"), F(w2, "v")), "井戸");
                }
                foreach (var o in Get2(doc, "service"))
                {
                    var s2 = o as Dictionary<string, object>; if (s2 == null) continue;
                    chk(fz == null ? null : fz.Find("Service"), Str(s2, "name"),
                        W((F(s2, "u0") + F(s2, "u1")) * 0.5f, (F(s2, "v0") + F(s2, "v1")) * 0.5f), "附属屋");
                }
            }
        }
        sb.AppendLine(ng == 0 ? "指図と実装の突き合わせ: 0 件" : "★ 指図と実装の不一致 " + ng + " 件");
        return sb.ToString();
    }

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

    // =====================================================================
    // 突き合わせ — 指図(json)の値 と 実装の値 を項目ごとに比べる
    // =====================================================================
    public static string Check()
    {
        var path = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), DOC);
        if (!System.IO.File.Exists(path)) return "指図が無い: " + DOC;
        var doc = MiniJson.Parse(System.IO.File.ReadAllText(path)) as Dictionary<string, object>;
        if (doc == null) return "指図が読めない: " + DOC;

        var sb = new StringBuilder("指図と実装の突き合わせ\n");
        int bad = 0, n = 0;

        // ---- 定数 ----
        var c = doc.ContainsKey("const") ? doc["const"] as Dictionary<string, object> : null;
        if (c != null)
        {
            bad += Cmp(sb, ref n, "const.ken", Num(c, "ken"), EdoOkabeYashikiBuilder.KEN);
            bad += Cmp(sb, ref n, "const.inubashiri", Num(c, "inubashiri"), EdoOkabeYashikiBuilder.INUBASHIRI);
            bad += Cmp(sb, ref n, "const.bandFlat", Num(c, "bandFlat"), EdoOkabeYashikiBuilder.BAND_FLAT);
            bad += Cmp(sb, ref n, "const.n4cut", Num(c, "n4cut"), EdoOkabeYashikiBuilder.N4_CUT);
        }

        // ---- 段 ----
        var terr = EdoOkabeYashikiBuilder.Terraces();
        var dt = List(doc, "terraces");
        bad += CmpCount(sb, ref n, "terraces", dt.Count, terr.Length);
        foreach (var o in dt)
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name"); bool found = false;
            foreach (var t in terr)
            {
                if (t.name != nm) continue; found = true;
                bad += Cmp(sb, ref n, "terrace " + nm + ".x0", Num(e, "x0"), t.x0);
                bad += Cmp(sb, ref n, "terrace " + nm + ".x1", Num(e, "x1"), t.x1);
                bad += Cmp(sb, ref n, "terrace " + nm + ".z0", Num(e, "z0"), t.z0);
                bad += Cmp(sb, ref n, "terrace " + nm + ".z1", Num(e, "z1"), t.z1);
                bad += Cmp(sb, ref n, "terrace " + nm + ".y", Num(e, "y"), t.y);
            }
            if (!found) { sb.Append("  ✗ terrace ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }

        // ---- 外周の run ----
        var runs = EdoOkabeYashikiBuilder.Runs();
        var walls = new Dictionary<string, EdoOkabeYashikiBuilder.PWall>();
        foreach (var q in EdoOkabeYashikiBuilder.PerimeterWalls()) walls[q.run] = q;
        var dr = List(doc, "runs");
        bad += CmpCount(sb, ref n, "runs", dr.Count, runs.Length);
        foreach (var o in dr)
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name"); bool found = false;
            foreach (var r in runs)
            {
                if (r.name != nm) continue; found = true;
                bad += Cmp(sb, ref n, "run " + nm + ".top", Num(e, "top"), r.top);
                bad += Cmp(sb, ref n, "run " + nm + ".seat", Num(e, "seat"), r.Seat);
                bad += Cmp(sb, ref n, "run " + nm + ".len", Num(e, "len"), (r.b - r.a).magnitude, 0.05f);
                bad += CmpStr(sb, ref n, "run " + nm + ".kind", Str(e, "kind"), r.kind.ToString());
                string want = Str(e, "wall");
                string have = walls.ContainsKey(nm)
                    ? walls[nm].name + " s=" + walls[nm].s.ToString("0.##", IC) : null;
                bad += CmpStr(sb, ref n, "run " + nm + ".wall", want, have);
            }
            if (!found) { sb.Append("  ✗ run ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }
        foreach (var r in runs)
        {
            bool inDoc = false;
            foreach (var o in dr) { var e = o as Dictionary<string, object>; if (e != null && Str(e, "name") == r.name) inDoc = true; }
            if (!inDoc) { sb.Append("  ✗ run ").Append(r.name).Append(" が**指図に無い**(実装だけにある)\n"); bad++; n++; }
        }

        // ---- 郭の土留め ----
        var ws = EdoOkabeYashikiBuilder.Walls();
        foreach (var o in List(doc, "terraceWalls"))
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name"); bool found = false;
            foreach (var w in ws)
            {
                if (w.name != nm) continue; found = true;
                bad += Cmp(sb, ref n, "wall " + nm + ".coping", Num(e, "coping"), w.coping);
                bad += Cmp(sb, ref n, "wall " + nm + ".s", Num(e, "s"), w.sy);
                bad += Cmp(sb, ref n, "wall " + nm + ".gapZ", Num(e, "gapZ"), w.gapZ, 0.05f);
                bad += Cmp(sb, ref n, "wall " + nm + ".gapHalf", Num(e, "gapHalf"), w.gapHalf, 0.02f);
                bad += CmpV2(sb, ref n, "wall " + nm + ".a", e, "a", w.a);
                bad += CmpV2(sb, ref n, "wall " + nm + ".b", e, "b", w.b);
            }
            if (!found) { sb.Append("  ✗ wall ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }

        // ---- 折れ角の隅 ----
        var ks = EdoOkabeYashikiBuilder.Kados();
        var dk = List(doc, "corners");
        bad += CmpCount(sb, ref n, "corners", dk.Count, ks.Length);
        foreach (var o in dk)
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string part = Str(e, "part"), ri = Str(e, "in");
            bool found = false;
            foreach (var k in ks)
            {
                if (k.part != part || k.runIn != ri) continue; found = true;
                float deg; Vector2 di, dou;
                if (k.part == "Ishigaki") EdoOkabeYashikiBuilder.KadoDirs(k, out di, out dou, out deg);
                else deg = EdoOkabeYashikiBuilder.KadoDeg(k);
                bad += Cmp(sb, ref n, "corner " + part + " " + ri + ".deg", Num(e, "deg"), deg, 0.15f);
                bad += CmpV2(sb, ref n, "corner " + part + " " + ri + ".v", e, "v", k.v);
            }
            if (!found) { sb.Append("  ✗ corner ").Append(part).Append(" ").Append(ri).Append(" が実装に無い\n"); bad++; n++; }
        }

        // ---- 郭の縁の柵 ----
        var rails = EdoOkabeYashikiBuilder.TerraceRails();
        var drObj = doc.ContainsKey("terraceRails") ? doc["terraceRails"] as Dictionary<string, object> : null;
        if (drObj != null)
        {
            bad += Cmp(sb, ref n, "rail.height", Num(drObj, "height"), EdoOkabeYashikiBuilder.RAIL_H);
            bad += Cmp(sb, ref n, "rail.insetFromCrest", Num(drObj, "insetFromCrest"), EdoOkabeYashikiBuilder.RAIL_INSET);
            var dl = drObj.ContainsKey("runs") ? drObj["runs"] as List<object> : null;
            bad += CmpCount(sb, ref n, "terraceRails", dl == null ? 0 : dl.Count, rails.Length);
            if (dl != null)
                foreach (var o in dl)
                {
                    var e = o as Dictionary<string, object>; if (e == null) continue;
                    string nm = Str(e, "wall"); bool found = false;
                    foreach (var r in rails)
                    {
                        if (r.wall != nm) continue; found = true;
                        bad += Cmp(sb, ref n, "rail " + nm + ".z0", Num(e, "z0"), r.z0, 0.05f);
                        bad += Cmp(sb, ref n, "rail " + nm + ".z1", Num(e, "z1"), r.z1, 0.05f);
                    }
                    if (!found) { sb.Append("  ✗ rail ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
                }
        }
        else if (rails.Length > 0)
        { sb.Append("  ✗ terraceRails が**指図に無い**(実装だけにある)\n"); bad++; n++; }

        // ---- 隅櫓(据えた実測と比べる) ----
        foreach (var o in List(doc, "yagura"))
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name");
            var t = Find("Kakoi", nm);
            if (t == null) { sb.Append("  ✗ 隅櫓 ").Append(nm).Append(" がシーンに無い\n"); bad++; n++; continue; }
            bad += Cmp(sb, ref n, "yagura " + nm + ".base", Num(e, "base"), Bounds(t).min.y, 0.02f);
        }

        // ---- 間グリッドの原点 ----
        // 棟・廊下・庭は指図では間の指数で持つので、原点がズレると全部が黙って動く。
        // 指数から世界座標を組み立てて実装の矩形と比べれば、原点も指数も同時に押さえられる。
        var gs = Grids(doc);
        bad += CmpCount(sb, ref n, "grid", gs.Count, 2);

        // ---- 棟 ----
        var mu = EdoOkabeYashikiBuilder.Muneya();
        var dm = List(doc, "munes");
        bad += CmpCount(sb, ref n, "munes", dm.Count, mu.Length);
        foreach (var o in dm)
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name"); bool found = false;
            foreach (var m in mu)
            {
                if (m.name != nm) continue; found = true;
                bad += Cmp(sb, ref n, "mune " + nm + ".kw", Num(e, "kw"), m.kw);
                bad += Cmp(sb, ref n, "mune " + nm + ".kd", Num(e, "kd"), m.kd);
                bad += Cmp(sb, ref n, "mune " + nm + ".y", Num(e, "y"), m.y);
                bad += CmpBox(sb, ref n, "mune " + nm, e, gs, m.x0, m.x1, m.z0, m.z1);
                // yaw は BuildMune が kw>=kd から導くので、指図の側が規則から外れていないかを見る
                bad += Cmp(sb, ref n, "mune " + nm + ".yaw", Num(e, "yaw"), m.kw >= m.kd ? 0f : 270f);
            }
            if (!found) { sb.Append("  ✗ mune ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }

        // ---- 廊下(渡廊下・御錠口・外廊下・登廊の取り付き) ----
        // **双方向**に見る。実装だけにある廊下は「奥へ入る道が二本ある」を意味しうるので、
        // 数が合っているだけでは足りない。
        var lk = EdoOkabeYashikiBuilder.GotenLinks();
        var dlk = List(doc, "links");
        bad += CmpCount(sb, ref n, "links", dlk.Count, lk.Length);
        var seenLink = new HashSet<string>();
        foreach (var o in dlk)
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name"); bool found = false;
            foreach (var l in lk)
            {
                if (l.name != nm) continue; found = true; seenLink.Add(nm);
                bad += Cmp(sb, ref n, "link " + nm + ".y", Num(e, "y"), l.y);
                bad += CmpBox(sb, ref n, "link " + nm, e, gs, l.x0, l.x1, l.z0, l.z1);
            }
            if (!found) { sb.Append("  ✗ link ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }
        foreach (var l in lk)
            if (!seenLink.Contains(l.name))
            { sb.Append("  ✗ link ").Append(l.name).Append(" が**指図に無い**(実装だけにある)\n"); bad++; n++; }

        // ---- 庭 ----
        var gd = EdoOkabeYashikiBuilder.Gardens();
        var dgd = List(doc, "gardens");
        bad += CmpCount(sb, ref n, "gardens", dgd.Count, gd.Length);
        foreach (var o in dgd)
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name"); bool found = false;
            foreach (var q in gd)
            {
                if (q.name != nm) continue; found = true;
                bad += CmpBox(sb, ref n, "garden " + nm, e, gs, q.x0, q.x1, q.z0, q.z1);
            }
            if (!found) { sb.Append("  ✗ garden ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }

        // ---- 石段・登廊 ----
        // 段数と踏面は実装が Drop/KERI から**再計算**するので、指図に書いた値と必ず突き合わせる。
        var kd2 = EdoOkabeYashikiBuilder.Kaidans();
        var dkd = List(doc, "kaidans");
        bad += CmpCount(sb, ref n, "kaidans", dkd.Count, kd2.Length);
        foreach (var o in dkd)
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name"); bool found = false;
            foreach (var k in kd2)
            {
                if (k.name != nm) continue; found = true;
                bad += Cmp(sb, ref n, "kaidan " + nm + ".xTop", Num(e, "xTop"), k.xTop);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".xBot", Num(e, "xBot"), k.xBot);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".z0", Num(e, "z0"), k.z0);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".z1", Num(e, "z1"), k.z1);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".yTop", Num(e, "yTop"), k.yTop);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".yBot", Num(e, "yBot"), k.yBot);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".noriHalf", Num(e, "noriHalf"), k.noriHalf);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".odoriKen", Num(e, "odoriKen"), k.odoriKen);
                int steps = Mathf.RoundToInt(k.Drop / EdoOkabeYashikiBuilder.KERI);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".steps", Num(e, "steps"), steps);
                bad += Cmp(sb, ref n, "kaidan " + nm + ".tread", Num(e, "tread"), k.Run / steps, 0.001f);
                bad += CmpStr(sb, ref n, "kaidan " + nm + ".noboriro", Str(e, "noboriro"), k.noboriro);
            }
            if (!found) { sb.Append("  ✗ kaidan ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }

        // ---- 表門・区画線 ----
        var gt = doc.ContainsKey("gate") ? doc["gate"] as Dictionary<string, object> : null;
        if (gt != null)
        {
            bad += CmpV2(sb, ref n, "gate.pos", gt, "pos", EdoOkabeYashikiBuilder.GATE);
            bad += Cmp(sb, ref n, "gate.yaw", Num(gt, "yaw"), EdoOkabeYashikiBuilder.YawGate(), 0.05f);
        }
        var poly = List(doc, "polygon");
        bad += CmpCount(sb, ref n, "polygon", poly.Count, SK.OKABE.Length);
        for (int i = 0; i < poly.Count && i < SK.OKABE.Length; i++)
        {
            var p = poly[i] as List<object>; if (p == null || p.Count < 2) continue;
            n++;
            var w = new Vector2(F(p[0]), F(p[1]));
            if ((w - SK.OKABE[i]).magnitude > 0.02f)
            {
                sb.Append("  ✗ polygon[").Append(i).Append("]  指図 ").Append(w).Append(" / 実装 ")
                  .Append(SK.OKABE[i]).Append("\n"); bad++;
            }
        }
        // ⚠ munes[].rooms は**突き合わせない**。実装は棟単位で襖割りを作らないので
        //   対応する物が無い。図面だけの設計情報であることは json の "_" にも書いてある。

        sb.Append(bad == 0
            ? "→ " + n + " 項目すべて一致 ✔  指図は実態と合っている"
            : "→ **" + bad + " / " + n + " 項目がズレている**。指図か実装のどちらかを直すこと");
        return sb.ToString();
    }

    /// <summary>間グリッドの原点と向き。指図側だけが持つ(実装は SG()/WG() の式に埋まっている)。</summary>
    struct GridDef { public float x0, z0; public int du, dv; }

    static Dictionary<string, GridDef> Grids(Dictionary<string, object> doc)
    {
        var m = new Dictionary<string, GridDef>();
        var g = doc.ContainsKey("grid") ? doc["grid"] as Dictionary<string, object> : null;
        if (g == null) return m;
        foreach (var kv in g)
        {
            var e = kv.Value as Dictionary<string, object>; if (e == null) continue;
            if (!e.ContainsKey("x0")) continue;
            m[kv.Key] = new GridDef { x0 = Num(e, "x0") ?? 0f, z0 = Num(e, "z0") ?? 0f,
                                      du = Mathf.RoundToInt(Num(e, "du") ?? 1f),
                                      dv = Mathf.RoundToInt(Num(e, "dv") ?? 1f) };
        }
        return m;
    }

    /// <summary>指図の (u,v) 指数 → 世界座標の矩形。x だけメートル直指定の廊下にも対応する。</summary>
    static int CmpBox(StringBuilder sb, ref int n, string label, Dictionary<string, object> e,
                      Dictionary<string, GridDef> gs, float x0, float x1, float z0, float z1)
    {
        GridDef g;
        if (!gs.TryGetValue(Str(e, "grid") ?? "", out g))
        { n++; sb.Append("  ✗ ").Append(label).Append(" の grid が指図に無い\n"); return 1; }
        float K = EdoOkabeYashikiBuilder.KEN;
        float za = g.z0 + g.dv * (Num(e, "v0") ?? 0f) * K, zb = g.z0 + g.dv * (Num(e, "v1") ?? 0f) * K;
        float xa, xb;
        if (e.ContainsKey("x0")) { xa = Num(e, "x0") ?? 0f; xb = Num(e, "x1") ?? 0f; }
        else { xa = g.x0 + g.du * (Num(e, "u0") ?? 0f) * K; xb = g.x0 + g.du * (Num(e, "u1") ?? 0f) * K; }
        int bad = 0;
        bad += Cmp(sb, ref n, label + ".x0", Mathf.Min(xa, xb), Mathf.Min(x0, x1));
        bad += Cmp(sb, ref n, label + ".x1", Mathf.Max(xa, xb), Mathf.Max(x0, x1));
        bad += Cmp(sb, ref n, label + ".z0", Mathf.Min(za, zb), Mathf.Min(z0, z1));
        bad += Cmp(sb, ref n, label + ".z1", Mathf.Max(za, zb), Mathf.Max(z0, z1));
        return bad;
    }

    static int CmpV2(StringBuilder sb, ref int n, string label, Dictionary<string, object> e,
                     string key, Vector2 have)
    {
        n++;
        object o; List<object> l;
        if (!e.TryGetValue(key, out o) || (l = o as List<object>) == null || l.Count < 2)
        { sb.Append("  ✗ ").Append(label).Append(" が指図に無い\n"); return 1; }
        var want = new Vector2(F(l[0]), F(l[1]));
        if ((want - have).magnitude <= 0.02f) return 0;
        sb.Append("  ✗ ").Append(label).Append("  指図 ").Append(want).Append(" / 実装 ").Append(have).Append("\n");
        return 1;
    }

    static float F(object o)
    {
        if (o is double) return (float)(double)o;
        if (o is long) return (float)(long)o;
        float f; return float.TryParse(o == null ? "" : o.ToString(), NumberStyles.Any, IC, out f) ? f : 0f;
    }

    static int Cmp(StringBuilder sb, ref int n, string label, float? want, float have, float tol = TOL)
    {
        n++;
        if (!want.HasValue) { sb.Append("  ✗ ").Append(label).Append(" が指図に無い(実装 ").Append(have.ToString("0.###", IC)).Append(")\n"); return 1; }
        if (Mathf.Abs(want.Value - have) <= tol) return 0;
        sb.Append("  ✗ ").Append(label).Append("  指図 ").Append(want.Value.ToString("0.###", IC))
          .Append(" / 実装 ").Append(have.ToString("0.###", IC)).Append("\n");
        return 1;
    }
    static int CmpStr(StringBuilder sb, ref int n, string label, string want, string have)
    {
        n++;
        if (want == have || (string.IsNullOrEmpty(want) && string.IsNullOrEmpty(have))) return 0;
        sb.Append("  ✗ ").Append(label).Append("  指図 ").Append(want ?? "(無)")
          .Append(" / 実装 ").Append(have ?? "(無)").Append("\n");
        return 1;
    }
    static int CmpCount(StringBuilder sb, ref int n, string label, int want, int have)
    {
        n++;
        if (want == have) return 0;
        sb.Append("  ✗ ").Append(label).Append(" の数  指図 ").Append(want).Append(" / 実装 ").Append(have).Append("\n");
        return 1;
    }

    static List<object> List(Dictionary<string, object> d, string k)
    {
        object o; if (d.TryGetValue(k, out o)) { var l = o as List<object>; if (l != null) return l; }
        return new List<object>();
    }
    static float? Num(Dictionary<string, object> d, string k)
    {
        object o; if (!d.TryGetValue(k, out o) || o == null) return null;
        if (o is double) return (float)(double)o;
        if (o is long) return (float)(long)o;
        float f; return float.TryParse(o.ToString(), NumberStyles.Any, IC, out f) ? (float?)f : null;
    }
    static string Str(Dictionary<string, object> d, string k)
    { object o; return d.TryGetValue(k, out o) && o != null ? o.ToString() : null; }

    // =====================================================================
    // 現況の書き出し(指図の種。**指図そのものではない**)
    // =====================================================================
    static string F(float v) { return v.ToString("0.###", IC); }
    static string S(string v) { return "\"" + (v ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""; }
    static string V2(Vector2 p) { return "[" + F(p.x) + "," + F(p.y) + "]"; }

    public static string Build()
    {
        var sb = new StringBuilder();
        sb.Append("{\n  \"_\": ").Append(S("実装の現況。指図ではない。指図は " + DOC)).Append(",\n");
        sb.Append("  \"generated\": ").Append(S(System.DateTime.Now.ToString("yyyy-MM-dd HH:mm"))).Append(",\n");
        sb.Append("  \"const\": {\"ken\": ").Append(F(EdoOkabeYashikiBuilder.KEN))
          .Append(", \"inubashiri\": ").Append(F(EdoOkabeYashikiBuilder.INUBASHIRI))
          .Append(", \"bandFlat\": ").Append(F(EdoOkabeYashikiBuilder.BAND_FLAT))
          .Append(", \"n4cut\": ").Append(F(EdoOkabeYashikiBuilder.N4_CUT))
          .Append(", \"keri\": ").Append(F(EdoOkabeYashikiBuilder.KERI))
          .Append(", \"fumi\": ").Append(F(EdoOkabeYashikiBuilder.FUMI)).Append("},\n");
        var P = EdoSannoKitaBuilder.OKABE;
        sb.Append("  \"polygon\": [");
        for (int i = 0; i < P.Length; i++) { if (i > 0) sb.Append(","); sb.Append(V2(P[i])); }
        sb.Append("],\n  \"area\": ").Append(F(PolyArea(P))).Append(",\n");

        var terr = EdoOkabeYashikiBuilder.Terraces();
        sb.Append("  \"terraces\": [\n");
        for (int i = 0; i < terr.Length; i++)
        {
            var t = terr[i];
            sb.Append("    {\"name\":").Append(S(t.name))
              .Append(",\"x0\":").Append(F(t.x0)).Append(",\"x1\":").Append(F(t.x1))
              .Append(",\"z0\":").Append(F(t.z0)).Append(",\"z1\":").Append(F(t.z1))
              .Append(",\"y\":").Append(F(t.y)).Append("}").Append(i < terr.Length - 1 ? ",\n" : "\n");
        }
        sb.Append("  ],\n");

        var walls = new Dictionary<string, EdoOkabeYashikiBuilder.PWall>();
        foreach (var q in EdoOkabeYashikiBuilder.PerimeterWalls()) walls[q.run] = q;
        var runs = EdoOkabeYashikiBuilder.Runs();
        sb.Append("  \"runs\": [\n");
        for (int i = 0; i < runs.Length; i++)
        {
            var r = runs[i];
            sb.Append("    {\"name\":").Append(S(r.name)).Append(",\"kind\":").Append(S(r.kind.ToString()))
              .Append(",\"a\":").Append(V2(r.a)).Append(",\"b\":").Append(V2(r.b))
              .Append(",\"len\":").Append(F((r.b - r.a).magnitude))
              .Append(",\"top\":").Append(F(r.top)).Append(",\"seat\":").Append(F(r.Seat))
              .Append(",\"faceOff\":").Append(F(EdoOkabeYashikiBuilder.FaceOff(r.kind)));
            if (walls.ContainsKey(r.name))
            {
                var q = walls[r.name];
                sb.Append(",\"wall\":{\"name\":").Append(S(q.name)).Append(",\"s\":").Append(F(q.s))
                  .Append(",\"posY\":").Append(F(r.Seat - 4f * q.s)).Append(",\"h\":").Append(F(4f * q.s))
                  .Append(",\"crestW\":").Append(F(1.4f * q.s)).Append(",\"baseT\":").Append(F(2.4f * q.s))
                  .Append(",\"pieces\":").Append(CountChildren("Ishigaki", q.name + "_")).Append("}");
            }
            sb.Append(",\"placed\":").Append(CountChildren("Kakoi", r.name + "_"))
              .Append(",\"crest\":").Append(CrestRange("Kakoi", r.name + "_")).Append("}")
              .Append(i < runs.Length - 1 ? ",\n" : "\n");
        }
        sb.Append("  ],\n");

        var ws = EdoOkabeYashikiBuilder.Walls();
        sb.Append("  \"terraceWalls\": [\n");
        for (int i = 0; i < ws.Length; i++)
        {
            var w = ws[i];
            sb.Append("    {\"name\":").Append(S(w.name)).Append(",\"a\":").Append(V2(w.a)).Append(",\"b\":").Append(V2(w.b))
              .Append(",\"len\":").Append(F((w.b - w.a).magnitude)).Append(",\"coping\":").Append(F(w.coping))
              .Append(",\"s\":").Append(F(w.sy)).Append(",\"posY\":").Append(F(w.coping - 4f * w.sy))
              .Append(",\"gapZ\":").Append(F(w.gapZ)).Append(",\"gapHalf\":").Append(F(w.gapHalf))
              .Append(",\"pieces\":").Append(CountChildren("Ishigaki", w.name + "_")).Append("}")
              .Append(i < ws.Length - 1 ? ",\n" : "\n");
        }
        sb.Append("  ],\n");

        var ks = EdoOkabeYashikiBuilder.Kados();
        sb.Append("  \"corners\": [\n");
        for (int i = 0; i < ks.Length; i++)
        {
            var k = ks[i];
            float deg; Vector2 di, dou;
            if (k.part == "Ishigaki") EdoOkabeYashikiBuilder.KadoDirs(k, out di, out dou, out deg);
            else deg = EdoOkabeYashikiBuilder.KadoDeg(k);
            sb.Append("    {\"part\":").Append(S(k.part)).Append(",\"in\":").Append(S(k.runIn))
              .Append(",\"out\":").Append(S(k.runOut)).Append(",\"v\":").Append(V2(k.v))
              .Append(",\"deg\":").Append(F(deg)).Append(",\"asset\":").Append(S(EdoAssets.Own.Kado(k.part, deg)))
              .Append("}").Append(i < ks.Length - 1 ? ",\n" : "\n");
        }
        sb.Append("  ],\n");

        sb.Append("  \"gate\": {\"pos\":").Append(V2(EdoOkabeYashikiBuilder.GATE))
          .Append(",\"yaw\":").Append(F(EdoOkabeYashikiBuilder.YawGate())).Append("},\n");
        sb.Append("  \"yagura\": [");
        bool first = true;
        foreach (var nm in new[] { "Sumiyagura_SE", "Sumiyagura_SW", "Sumiyagura_NE" })
        {
            var t = Find("Kakoi", nm); if (t == null) continue;
            if (!first) sb.Append(","); first = false;
            var b = Bounds(t);
            sb.Append("{\"name\":").Append(S(nm)).Append(",\"pos\":[").Append(F(b.center.x)).Append(",").Append(F(b.center.z))
              .Append("],\"base\":").Append(F(b.min.y)).Append(",\"top\":").Append(F(b.max.y)).Append("}");
        }
        sb.Append("],\n");

        var mu = EdoOkabeYashikiBuilder.Muneya();
        sb.Append("  \"munes\": [\n");
        for (int i = 0; i < mu.Length; i++)
        {
            var m = mu[i];
            sb.Append("    {\"name\":").Append(S(m.name)).Append(",\"kw\":").Append(m.kw).Append(",\"kd\":").Append(m.kd)
              .Append(",\"moyaW\":").Append(m.MoyaW).Append(",\"moyaD\":").Append(m.MoyaD)
              .Append(",\"y\":").Append(F(m.y))
              .Append(",\"area\":").Append(F(Mathf.Abs((m.x1 - m.x0) * (m.z1 - m.z0)))).Append("}")
              .Append(i < mu.Length - 1 ? ",\n" : "\n");
        }
        sb.Append("  ],\n");
        sb.Append("  \"qa\": {\"perimeter\": ").Append(S(FirstLine(EdoOkabeYashikiBuilder.PerimeterQA())))
          .Append(", \"grade\": ").Append(S(FirstLine(EdoOkabeYashikiBuilder.GradeQA())))
          .Append(", \"ground\": ").Append(S(LastLines(EdoOkabeYashikiBuilder.GroundQA(), 3))).Append("}\n}\n");
        return sb.ToString();
    }

    static Transform Root()
    { var g = GameObject.Find(EdoOkabeYashikiBuilder.GN); return g == null ? null : g.transform; }
    static Transform Find(string grp, string name)
    { var r = Root(); if (r == null) return null; var g = r.Find(grp); return g == null ? null : g.Find(name); }
    static int CountChildren(string grp, string prefix)
    {
        var r = Root(); if (r == null) return 0;
        var g = r.Find(grp); if (g == null) return 0;
        int n = 0; foreach (Transform c in g) if (c.name.StartsWith(prefix)) n++;
        return n;
    }
    static Bounds Bounds(Transform t)
    {
        var rs = t.GetComponentsInChildren<Renderer>();
        var b = new Bounds(t.position, Vector3.zero); bool f = true;
        foreach (var r in rs) { if (f) { b = r.bounds; f = false; } else b.Encapsulate(r.bounds); }
        return b;
    }
    static string CrestRange(string grp, string prefix)
    {
        var r = Root(); if (r == null) return "null";
        var g = r.Find(grp); if (g == null) return "null";
        float mn = 9999f, mx = -9999f; int n = 0;
        foreach (Transform c in g)
        {
            if (!c.name.StartsWith(prefix)) continue;
            var b = Bounds(c); if (b.size == Vector3.zero) continue;
            mn = Mathf.Min(mn, b.max.y); mx = Mathf.Max(mx, b.max.y); n++;
        }
        return n == 0 ? "null" : "[" + F(mn) + "," + F(mx) + "]";
    }
    static float PolyArea(Vector2[] p)
    {
        float a = 0f;
        for (int i = 0; i < p.Length; i++) { var q = p[(i + 1) % p.Length]; a += p[i].x * q.y - q.x * p[i].y; }
        return Mathf.Abs(a) * 0.5f;
    }
    static string FirstLine(string s)
    { if (string.IsNullOrEmpty(s)) return ""; int i = s.IndexOf('\n'); return (i < 0 ? s : s.Substring(0, i)).Trim(); }
    static string LastLines(string s, int n)
    {
        if (string.IsNullOrEmpty(s)) return "";
        var l = s.TrimEnd().Split('\n'); var sb = new StringBuilder();
        for (int i = Mathf.Max(0, l.Length - n); i < l.Length; i++) { if (sb.Length > 0) sb.Append(" / "); sb.Append(l[i].Trim()); }
        return sb.ToString();
    }
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
