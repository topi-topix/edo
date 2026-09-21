// 門の完備 — 建てた門の上に、その型が要求する屋根が本当に載っているか(実装の輪・EDO-0315)。
//
// 【なぜ要るか】松江松平の検証レンダで「表門の屋根が見当たらず、左右の番所のあいだが板一枚に見える」が
//   絵で初めて見つかった。門の取り合い(隙間0・めり込み0・4継ぎ目 +0.0000)は「隣り合う部材が接しているか」
//   だけを見ており、「その型が持つべき部材が居るか」を誰も見ていなかった。
//   屋根の有無は数えられる(docs/verification-loops.md §4)— 足りなかったのは完備の検査。
//
// 【何を測るか】単一メッシュの門(Matsudaira_Omotemon.fbx 等)は部材の名前で屋根を判定できない。
//   ⇒ **開口の上(敷居 + clearance より上)にある上向きの面**の面積・奥行・幅を実メッシュから測り、
//     屋根が架かっているかを数える。冠木1本(奥行 0.3m)は奥行で弾く。
//   ⛔ 部材の基準点や bounds の中心では見ない(規則21)。頂点と三角形を直に測る。
//
// 【型の表】docs/Sashizu/gate_types.json が正典。図の輪(Tools/Sashizu/gate_types.py・C24)と同じ表を読む。
//   型の引き方(kind の自由文 → match の語・上から順)は python 側と同じにしてある。
//
// 【使い方】普請検査が execute_code から:
//     EdoGateComplete.Run("matsudaira_dewa", <門のグループ(Mon)>, "Omotemon")
//   返り値の各行に実測値が出る。失敗の行は ★(EdoQaVerdict.Failed が拾う)。
//   ⛔ 「屋根なし」の型でも実測値を出す(記録)。黙って除外しない。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

/// <summary>判定そのもの(Unity の型を持ち込まない・破壊試験が Unity 抜きで走る)。</summary>
public static class EdoGateVerdict
{
    public struct Roof
    {
        public float area;      // 屋根の候補の面積 m²
        public float xExtent;   // 走り方向の広がり m
        public float zExtent;   // 奥行方向の広がり m
        public float topH;      // 門の総高(敷居から)m
        public int tris;
    }

    /// <summary>開口の上に屋根が架かっているか。3つとも満たすこと(面積・奥行・幅)。
    /// ⛔ 面積だけで見ない — 冠木の上面と柱頭で面積は稼げるが、奥行が足りない。</summary>
    public static bool RoofPresent(Roof r, float monW, float monD, float minAreaFrac, float minDepthFrac, float minWidthFrac)
    {
        if (monW <= 0f || monD <= 0f) return false;
        return r.area >= minAreaFrac * monW * monD
            && r.zExtent >= minDepthFrac * monD
            && r.xExtent >= minWidthFrac * monW;
    }

    /// <summary>型が屋根を要求する(yes)/ 持たない(none)/ 問わない(opt)に対する合否。null = 合格、文字列 = ★ の理由。</summary>
    public static string RoofFail(string rule, bool present)
    {
        if (rule == "yes" && !present) return "屋根が載っていない(この型は屋根を持つ)";
        if (rule == "none" && present) return "屋根が載っている(この型は屋根を持たない — 残骸か型の取り違え)";
        if (rule != "yes" && rule != "none" && rule != "opt") return "屋根の規則『" + rule + "』が読めない(gate_types.json の roof は yes/none/opt)— 合格にしない";
        return null;
    }
}

public static class EdoGateComplete
{
    public const string RelPath = "docs/Sashizu/gate_types.json";

    static string Root { get { return Path.GetFullPath(Path.Combine(Application.dataPath, "..")); } }

    static Dictionary<string, object> O(object o) { return o as Dictionary<string, object>; }
    static List<object> A(object o) { return o as List<object>; }
    static float F(object o, float dflt = 0f)
    {
        if (o is double) return (float)(double)o;
        if (o is float) return (float)o;
        if (o is int) return (int)o;
        return dflt;
    }

    static Dictionary<string, object> Load(string rel)
    {
        var path = Path.Combine(Root, rel);
        if (!File.Exists(path)) return null;
        return O(EdoMiniJson.Parse(File.ReadAllText(path, Encoding.UTF8)));
    }

    /// <summary>kind の自由文から型を引く。上から順に最初に当たった型(python の gate_types.classify と同じ)。</summary>
    public static string Classify(string text, Dictionary<string, object> table)
    {
        if (string.IsNullOrEmpty(text)) return null;
        var types = O(table["types"]);
        foreach (var kv in types)
        {
            var match = A(O(kv.Value)["match"]);
            foreach (var w in match)
                if (text.IndexOf((string)w, StringComparison.Ordinal) >= 0) return kv.Key;
        }
        return null;
    }

    /// <summary>body 以下のメッシュを直に測って、開口の上の屋根の候補を返す。
    /// 座標は body のローカル(x = 走り・z = 奥行)と世界の高さ(敷居からの y)。</summary>
    public static EdoGateVerdict.Roof MeasureRoof(Transform body, float sill, float clearance)
    {
        var r = new EdoGateVerdict.Roof();
        float xMin = float.MaxValue, xMax = float.MinValue, zMin = float.MaxValue, zMax = float.MinValue;
        float top = float.MinValue;
        foreach (var mf in body.GetComponentsInChildren<MeshFilter>(true))
        {
            var mesh = mf.sharedMesh;
            if (mesh == null) continue;
            var mr = mf.GetComponent<MeshRenderer>();
            if (mr == null || !mr.enabled) continue;
            var m = mf.transform.localToWorldMatrix;
            bool mirrored = m.determinant < 0f;
            var vs = mesh.vertices;
            for (int i = 0; i < vs.Length; i++)
            {
                float y = m.MultiplyPoint3x4(vs[i]).y;
                if (y > top) top = y;
            }
            for (int s = 0; s < mesh.subMeshCount; s++)
            {
                var ts = mesh.GetTriangles(s);
                for (int t = 0; t + 2 < ts.Length; t += 3)
                {
                    Vector3 a = m.MultiplyPoint3x4(vs[ts[t]]), b = m.MultiplyPoint3x4(vs[ts[t + 1]]), c = m.MultiplyPoint3x4(vs[ts[t + 2]]);
                    Vector3 n = Vector3.Cross(b - a, c - a);
                    float area2 = n.magnitude;
                    if (area2 < 1e-9f) continue;
                    n /= area2;
                    if (mirrored) n = -n;
                    if (n.y <= 0.3f) continue;                                   // 上向きの面だけ
                    float yc = (a.y + b.y + c.y) / 3f - sill;
                    if (yc < clearance) continue;                                // 開口の上だけ
                    r.area += area2 * 0.5f;
                    r.tris++;
                    foreach (var w in new[] { a, b, c })
                    {
                        var l = body.InverseTransformPoint(w);
                        if (l.x < xMin) xMin = l.x; if (l.x > xMax) xMax = l.x;
                        if (l.z < zMin) zMin = l.z; if (l.z > zMax) zMax = l.z;
                    }
                }
            }
        }
        if (r.tris > 0) { r.xExtent = xMax - xMin; r.zExtent = zMax - zMin; }
        r.topH = top == float.MinValue ? 0f : top - sill;
        return r;
    }

    static Dictionary<string, object> FindGate(Dictionary<string, object> d, string name)
    {
        if (name == null) { var g = O(d.ContainsKey("gate") ? d["gate"] : null); if (g != null) return g; }
        var cand = new List<object>();
        object v;
        if (d.TryGetValue("gate", out v)) { if (A(v) != null) cand.AddRange(A(v)); else if (O(v) != null) cand.Add(v); }
        if (d.TryGetValue("komon", out v)) { if (A(v) != null) cand.AddRange(A(v)); else if (O(v) != null) cand.Add(v); }
        if (d.TryGetValue("gates", out v) && A(v) != null) cand.AddRange(A(v));
        foreach (var c in cand)
        {
            var g = O(c);
            if (g == null) continue;
            object nm; g.TryGetValue("name", out nm);
            if (name == null || (nm as string) == name) return g;
        }
        return null;
    }

    /// <summary>門1つを測って報告する。
    /// estateId … docs/Sashizu/&lt;estateId&gt;_sashizu.json(kind・sill・plan.monW/monD/bansho.count を読む)
    /// group    … 門の部材を子に持つグループ(松江松平なら「Mon」)。番所・袖塀もここの子
    /// bodyName … 屋根を測る門の本体の子の名前(松江松平なら「Omotemon」)。⛔ 番所は含めない(番所には番所の屋根がある)
    /// gateName … 指図の門の name。null なら gate(表門)</summary>
    public static string Run(string estateId, Transform group, string bodyName, string gateName = null)
    {
        var sb = new StringBuilder();
        var table = Load(RelPath);
        if (table == null) return "★ 門の型の表が読めない: " + RelPath;
        var d = Load("docs/Sashizu/" + estateId + "_sashizu.json");
        if (d == null) return "★ 指図が読めない: " + estateId;
        var g = FindGate(d, gateName);
        if (g == null) return "★ 指図に門が見つからない: " + estateId + " / " + (gateName ?? "gate");
        var body = group != null ? group.Find(bodyName) : null;
        if (body == null) return "★ 門の本体が居ない: " + (group != null ? group.name : "(group null)") + "/" + bodyName + " — 型が要求する部材が建っていない";

        object kv; g.TryGetValue("kind", out kv);
        string kind = kv as string;
        var ty = Classify(kind, table);
        if (ty == null)
            return "⚠ 未検査 — 門『" + (gateName ?? "gate") + "』の型が読めない(kind=『" + kind + "』が gate_types.json の match に当たらない)。これは合格ではない";
        var t = O(O(table["types"])[ty]);
        string rule = (string)t["roof"];

        var plan = O(g.ContainsKey("plan") ? g["plan"] : null) ?? new Dictionary<string, object>();
        float monW = F(plan.ContainsKey("monW") ? plan["monW"] : null, 0f);
        float monD = F(plan.ContainsKey("monD") ? plan["monD"] : null, 0f);
        float sill = F(g.ContainsKey("sill") ? g["sill"] : null, body.position.y);
        var rm = O(table["_roofMeasure"]);
        float clr = F(rm["clearance"]), fA = F(rm["minAreaFrac"]), fD = F(rm["minDepthFrac"]), fW = F(rm["minWidthFrac"]);
        if (monW <= 0f || monD <= 0f)
            return "⚠ 未検査 — 指図の門に plan.monW / plan.monD が無い(屋根の広がりの物差しが無い)。これは合格ではない";

        var roof = MeasureRoof(body, sill, clr);
        bool present = EdoGateVerdict.RoofPresent(roof, monW, monD, fA, fD, fW);
        var fail = EdoGateVerdict.RoofFail(rule, present);
        var I = CultureInfo.InvariantCulture;
        sb.AppendLine((fail != null ? "★ " : "　") + "屋根 — 型『" + t["label"] + "』(" + rule + ")/ " + (present ? "載っている" : "載っていない")
            + (fail != null ? " → " + fail : "")
            + (rule == "opt" ? "(型が問わないので記録のみ)" : ""));
        sb.AppendLine("　実測: 開口の上の上向き面 " + roof.area.ToString("F2", I) + " m²(三角形 " + roof.tris + ")/ 奥行 " + roof.zExtent.ToString("F2", I)
            + " m / 走り " + roof.xExtent.ToString("F2", I) + " m / 総高 " + roof.topH.ToString("F2", I) + " m");
        sb.AppendLine("　閾値: 面積 ≥ " + (fA * monW * monD).ToString("F2", I) + " m²(monW×monD×" + fA.ToString("F1", I) + ")/ 奥行 ≥ "
            + (fD * monD).ToString("F2", I) + " m / 走り ≥ " + (fW * monW).ToString("F2", I) + " m / 開口の上端 = 敷居+" + clr.ToString("F1", I) + " m");

        // 番所 — 指図が数を言うなら、その数だけ居ること
        object bo; plan.TryGetValue("bansho", out bo);
        var bansho = O(bo);
        if (bansho != null && bansho.ContainsKey("count"))
        {
            int want = (int)F(bansho["count"]);
            object bw; t.TryGetValue("bansho", out bw);
            if ((bw as string) == "body")
                sb.AppendLine("　番所 — 指図 " + want + "(この型は番所が躯体の内にある。子の数では数えない=記録のみ)");
            else
            {
                int have = 0;
                for (int i = 0; i < group.childCount; i++)
                    if (group.GetChild(i).name.StartsWith("Bansho_", StringComparison.Ordinal)) have++;
                sb.AppendLine((have != want ? "★ " : "　") + "番所 — 指図 " + want + " / 建った " + have);
            }
        }
        return sb.ToString().TrimEnd();
    }
}
