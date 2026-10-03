// 類型ビルダー — 勝手まわり(低い平場の菜園と、主の平場から降りる段石)。EDO-0532 施主裁定A(2026-10-03)。
//
// 表の欄: low_terrace = "katte"(今は樹下だけ)。棟(使用人の長屋・薪小屋)は Omoya の JishaOmoya が JMode.Low で置き、
//   造成(Stage 4z)が足あとごとに平場を採った後で、この段が菜園と段石を据える。
// ⛔ このファイルに置き方の算術を書かない(規則21)── 据える・測る・並べるのは EdoBuild.FieldRect / LayUne / SlopeSteps(EdoBuildKatte.cs)。
//    ここに書くのは「どこを菜園にしてよいか」の条件と、段をどこからどこへ通すかだけ。
// 条件(どれも確度 U・施主裁定の意図を数値へ落とした当方の値):
//   菜園の地表 = 長屋の床の高さ +0.3 〜 −0.6・勾配 1:20 以下(畝の下手の根入れが 0.09m を超えない)・区画の縁から 2.0m・棟の軒から 1.5m(硬い)。
//   広さは狙い(最大の矩形を採って実測を刷る)。

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    const float KATTE_UP = 0.3f, KATTE_DOWN = 0.6f;   // 菜園の地表の帯(長屋の床から)[m]【U】
    const float KATTE_SLOPE = 1f / 20f;               // 菜園の勾配の上限【U】
    const float KATTE_EDGE = 2.0f, KATTE_EAVE = 1.5f; // 区画の縁・棟の軒からの離れ[m]【U】
    const float UNE_PITCH = 0.9f;                     // 畝間(芯々)[m]【U】
    const float UNE_SINK = 0.03f, UNE_BURY_MAX = 0.10f;

    /// <summary>菜園と段石の外形(庭の段が木・庭域を入れない所)。Katte が埋め、Niwa が読む。</summary>
    static List<Vector2[]> _katteFields = new List<Vector2[]>();

    static string Katte(Spec s, Transform root, Vector2[] poly)
    {
        _katteFields = new List<Vector2[]>();
        if (s.lowTerrace != "katte") return null;
        var tat = root.Find("Tatemono");
        var nagaya = tat != null ? tat.Find("GeninNagaya") : null;
        if (nagaya == null) return "  ⚠ 勝手まわり(low_terrace=katte): 使用人の長屋が建っていない ── 菜園と段石は据えない";
        var grp = Group("Katte", root);
        var log = new List<string> { "  勝手まわり(表の low_terrace=katte・EDO-0532 施主裁定A):" };

        // 棟の軒込みの凸包(菜園は軒から KATTE_EAVE 離す・段石は壁体の中へ置かない)
        var eaves = new List<Vector2[]>(); var walls = new List<Vector2[]>();
        foreach (Transform b in tat)
        {
            var e = EdoBuild.Body(b, 600, true).Select(w => new Vector2(w.x, w.z)).ToArray();
            var w2 = EdoBuild.Body(b, 600, false).Select(w => new Vector2(w.x, w.z)).ToArray();
            if (e.Length >= 3) eaves.Add(EdoGeom.HullXZ(e).Select(k => e[k]).ToArray());
            if (w2.Length >= 3) walls.Add(EdoGeom.HullXZ(w2).Select(k => w2[k]).ToArray());
        }
        Func<Vector2, float> eaveDist = p =>
        {
            float m = float.MaxValue;
            foreach (var h in eaves) m = Mathf.Min(m, EdoGeom.PIP(h, p) ? -1f : EdoGeom.DistToPolyEdge(h, p));
            return m;
        };

        // ── 菜園 ── 長屋の軸に揃えた最大の矩形
        var nt = nagaya.transform;
        float floor = EdoBuild.RB(nagaya.gameObject).min.y;   // 長屋の下端 = 平場の高さ(造成で採った面)
        var o = new Vector2(nt.position.x, nt.position.z);
        var u = new Vector2(nt.right.x, nt.right.z).normalized; var v = new Vector2(nt.forward.x, nt.forward.z).normalized;
        Func<Vector2, bool> ok = p =>
        {
            if (!EdoGeom.PIP(poly, p) || EdoGeom.DistToPolyEdge(poly, p) < KATTE_EDGE) return false;
            if (eaveDist(p) < KATTE_EAVE) return false;
            float g = EdoBuild.Ground(p.x, p.y);
            if (g > floor + KATTE_UP || g < floor - KATTE_DOWN) return false;
            float gx = (EdoBuild.Ground(p.x + 0.5f, p.y) - EdoBuild.Ground(p.x - 0.5f, p.y));
            float gz = (EdoBuild.Ground(p.x, p.y + 0.5f) - EdoBuild.Ground(p.x, p.y - 0.5f));
            return Mathf.Sqrt(gx * gx + gz * gz) <= KATTE_SLOPE;
        };
        var box = EdoBuild.FieldRect(o, u, v, ok, 1f, 45f);
        if (box == null) log.Add("    ⚠ 菜園: 条件を満たす平らな所が無い ── 畝は据えない");
        else
        {
            string un; var une = EdoBuild.LayUne(EdoAssets.Own.HatakeUne, grp, box, UNE_PITCH, UNE_SINK, UNE_BURY_MAX, out un);
            log.Add(string.Format("    菜園: {0:F1} × {1:F1}m = {2:F0}m²(長屋の軸に揃えた最大の矩形・地表 床{3:+0.0;-0.0}〜{4:+0.0;-0.0}・勾配 ≤1:{5:F0}・縁 {6:F1}m・軒 {7:F1}m)── {8}",
                                  box.x1 - box.x0, box.z1 - box.z0, (box.x1 - box.x0) * (box.z1 - box.z0), KATTE_UP, -KATTE_DOWN, 1f / KATTE_SLOPE, KATTE_EDGE, KATTE_EAVE, un));
            var fc = EdoBuild.FieldCorners(box);
            _katteFields.Add(fc);
            // 地表の印 = 叩き土(畝の間の土)── EdoGardenSurfacePaint が塗る
            var zgo = new GameObject("Ground_tataki_saien"); zgo.transform.SetParent(grp, false);
            var z = zgo.AddComponent<NiwaGroundZone>(); z.kind = "tataki";
            z.quads = fc.Select(q => new Vector3(q.x, 0f, q.y)).ToList();
            foreach (var p in poly) z.clip.Add(new Vector3(p.x, 0f, p.y));
        }

        // ── 段石 ── 庫裏(無ければ本堂)の壁体の際から長屋の壁体の際へ、自然の斜面を崩さず
        var upper = tat.Find("Kuri") ?? tat.Find("Honden");
        if (upper != null)
        {
            var a = EdoBuild.BodyCentreXZ(upper); var b = EdoBuild.BodyCentreXZ(nagaya);
            a = EdoBuild.ExitToward(upper, a, b, 1.0f); b = EdoBuild.ExitToward(nagaya, b, a, 1.0f);
            string dn;
            var dans = EdoBuild.SlopeSteps(i => EdoAssets.Own.SannoDan(0.200f, 0.450f, 1.818f, i), grp, a, b, 0.200f, 0.450f, "Danishi", 0.05f,
                                           p => walls.Any(h => EdoGeom.PIP(h, p) || EdoGeom.DistToPolyEdge(h, p) < 1.0f), out dn);
            log.Add("    " + dn + string.Format("({0}の際 → 長屋の際)", upper.name));
            if (dans.Count > 0)
            {
                var pts = dans.SelectMany(d => EdoBuild.Body(d.transform, 200, true)).Select(w => new Vector2(w.x, w.z)).ToArray();
                _katteFields.Add(EdoGeom.HullXZ(pts).Select(k => pts[k]).ToArray());
            }
        }
        return string.Join("\n", log.ToArray());
    }
}
