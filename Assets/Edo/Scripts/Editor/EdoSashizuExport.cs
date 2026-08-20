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
///   4. 実装          … ビルダーの表を指図に合わせる
///   5. **突き合わせ**… このメニュー。差分 0 件になるまで直す
///      建ててみて指図のほうが誤りだと分かったら、**指図を直してから**再度合わせる
///   6. 経緯          … コミットメッセージと git log。**指図には残さない**
///
/// 現況だけを書き出したいとき(指図を新しく起こす種にするなど)は「現況を書き出す」を使う。</summary>
public static class EdoSashizuExport
{
    const string DOC = "docs/Sashizu/okabe_sashizu.json";
    const string DUMP = "docs/Sashizu/okabe_current.json";
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
            }
            if (!found) { sb.Append("  ✗ corner ").Append(part).Append(" ").Append(ri).Append(" が実装に無い\n"); bad++; n++; }
        }

        // ---- 隅櫓(据えた実測と比べる) ----
        foreach (var o in List(doc, "yagura"))
        {
            var e = o as Dictionary<string, object>; if (e == null) continue;
            string nm = Str(e, "name");
            var t = Find("Kakoi", nm);
            if (t == null) { sb.Append("  ✗ 隅櫓 ").Append(nm).Append(" がシーンに無い\n"); bad++; n++; continue; }
            bad += Cmp(sb, ref n, "yagura " + nm + ".base", Num(e, "base"), Bounds(t).min.y, 0.02f);
        }

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
            }
            if (!found) { sb.Append("  ✗ mune ").Append(nm).Append(" が実装に無い\n"); bad++; n++; }
        }

        sb.Append(bad == 0
            ? "→ " + n + " 項目すべて一致 ✔  指図は実態と合っている"
            : "→ **" + bad + " / " + n + " 項目がズレている**。指図か実装のどちらかを直すこと");
        return sb.ToString();
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
