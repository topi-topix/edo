using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 土井 S4b 縁の皮(案A・EDO-0533)── 2m 格子の地形では描けない土留めの天端の奥・石段の踏面・面の縁の升に穴を開け、
//  0.25m の皮で描く(EdoBuild.CutEdgeSkin・岡部 Stage3b / 山王 Stage9 と同じ型)。
//  ⛔ 置き方はここに書かない(規則21)── 渡す部材・面・設計の地盤を集めるだけ。
//  ⚠ 造成(1)・土留め(4a)・排水(9)を流した後は皮が古い ── 4a・9 の後に必ずこれを流し直す。
public static partial class EdoDoiBuilder
{
    [MenuItem(MENU + "4b 縁の皮(土留め・石段の足元の升を皮で描く)")]
    public static void Stage4bHifuMenu() { Debug.Log("[Doi] " + Stage4b_Hifu()); }

    public static string Stage4b_Hifu()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        var sb = new System.Text.StringBuilder("S4b 縁の皮(案A):\n");
        var ck = O(IMPL["checks"]);
        if (ck == null || !Has(ck, "gradeTol")) return sb + "  ⛔ 算出物 checks.gradeTol が無い ── 皮を起こさない(既定値で埋めない)";
        float tol = F(ck["gradeTol"]);
        var grp = Group("EdgeSkin");
        int filled = EdoBuild.ClearEdgeSkins(grp);
        // 部材 = 邸内の土留め(Dodome)+ 石段(Fuzoku/Kaidan)。土留めは天端の帯で篩う(見え面の前へ皮を出さない)
        var parts = new List<GameObject>(); var band = new List<GameObject>();
        foreach (Transform c in Group("Dodome")) if (c.gameObject.activeInHierarchy) { parts.Add(c.gameObject); band.Add(c.gameObject); }
        int stairN = 0;
        foreach (var r in Group("Fuzoku/Kaidan").GetComponentsInChildren<MeshRenderer>()) { parts.Add(r.gameObject); stairN++; }
        // 溝・桝・蓋石・水切り(S9 排水・群 Mizo)── 天端を地盤に据えて地形の下へ潜るので、升に穴を開けて皮で描く(⚠ S9 の後にこれを流し直す)
        int mizoN = 0; var hollow = new List<GameObject>(); var channel = new List<GameObject>();
        foreach (Transform c in Group("Mizo")) if (c.gameObject.activeInHierarchy) { parts.Add(c.gameObject); hollow.Add(c.gameObject); mizoN++; if (!c.name.StartsWith("Ankyo", StringComparison.Ordinal)) channel.Add(c.gameObject); }
        // ⭐ 溝の脇の守り(硬い・2026-10-05 EDO-0533 第14巡): 溝の駒(蓋石 Ankyo* は窪みを持たないので除く)の外形の外の皮は造成の面より下げない(EdoBuild.CutEdgeSkin の keepGradeBeside)
        //   床は min(造成の面, 溝の天端の外の辺から切土の法 1:batterCut)── 天端が沈んだ溝の脇は法で造成の面へ上げる(歯形を立てない・2026-10-06 第15巡 keepBatter)
        // 面 = 指図 terraces のうち設計の地盤が面の高さに収まる物(勾配の面は graded のまま描く)
        var faces = new List<EdoBuild.SkinFace>(); var f = Grid; var G = Graded;
        foreach (var o in A(D["terraces"]) ?? new List<object>())
        {
            var t = O(o); if (t == null || !Has(t, "poly") || !Has(t, "y") || t["y"] == null) continue;
            var pl = A(t["poly"]); if (pl == null || pl.Count < 3) continue;
            var poly = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); poly[i] = f.W(F(q[0]), F(q[1])); }
            float y = F(t["y"]), dev = 0f; int nIn = 0;
            float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
            foreach (var p in poly) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
            for (float x = Mathf.Ceil(mnx); x <= mxx; x += 1f)
                for (float z = Mathf.Ceil(mnz); z <= mxz; z += 1f)
                {
                    var q = new Vector2(x, z); if (!EdoGeom.PIP(poly, q) || EdoGeom.DistToPolyEdge(poly, q) < 1.5f) continue;
                    float g = G.At(x, z); if (float.IsNaN(g)) continue; nIn++; dev = Mathf.Max(dev, Mathf.Abs(g - y));
                }
            if (nIn == 0 || dev > 0.05f) { sb.AppendLine("  面 " + S(t["name"]) + "(" + y.ToString("F2") + "): 設計の地盤が面から最大 " + dev.ToString("F2") + "m 外れる ── 面にせず graded で描く"); continue; }
            faces.Add(new EdoBuild.SkinFace(S(t["name"]), poly, y));
        }
        var ok = new bool[G.h.Length]; for (int i = 0; i < ok.Length; i++) ok[i] = !float.IsNaN(G.h[i]);
        var design = new EdoBuild.SkinDesign
        {
            x0 = G.x0, z0 = G.z0, step = G.step, nx = G.nx, nz = G.nz, h = G.h, ok = ok,
            batterCut = C("batterCut"), batterFill = C("batterFill"), baseAt = EdoBuild.BaseDem(), own = Poly
        };
        // ⛔ 地形の木の升と、皮より先に地形へ据わる柵(Fuzoku/Saku)の足元の升には穴を開けない
        var plant = new List<Vector2>();
        {
            var tr = EdoBuild.T(); var td = tr.terrainData; var org = tr.transform.position; var P = Poly;
            foreach (var ti in td.treeInstances)
            {
                var q = new Vector2(org.x + ti.position.x * td.size.x, org.z + ti.position.z * td.size.z);
                if (EdoGeom.PIP(P, q)) plant.Add(q);
            }
            foreach (Transform fc in Group("Fuzoku/Saku"))
            {
                if (!fc.gameObject.activeInHierarchy) continue;
                var fb = EdoBuild.RB(fc.gameObject); if (fb.size == Vector3.zero) continue;
                foreach (var q in new[] { new Vector2(fb.center.x, fb.center.z), new Vector2(fb.min.x, fb.min.z), new Vector2(fb.max.x, fb.max.z) })
                    if (EdoGeom.PIP(P, q)) plant.Add(q);
            }
        }
        // ⭐ 庭の土工の矩形(6a が池を掘り築山を盛る範囲)は面の縁の升に数えない ── 皮で池を埋め戻さない
        var keep = new List<Vector2[]>();
        { var nm = NiwaModel; if (nm != null) keep.Add(new[] { Wu(nm.u0, nm.v0), Wu(nm.u1, nm.v0), Wu(nm.u1, nm.v1), Wu(nm.u0, nm.v1) }); }
        // ⭐ 溝は掘る部材(hollowParts)── 脇の皮を溝の底まで下げない。⭐ 邸の据わった駒すべて(外周・棟・附属屋・植栽・柵・溝)を seated に渡し、
        //   皮が元の地形より下げて駒を浮かせない守りを掛ける(硬い・2026-10-05 全項目の検査 接地 fail の直し)
        var rootGo = GameObject.Find(Grp);
        var seated = EdoBuild.SeatedUnder(rootGo != null ? rootGo.transform : null, grp);
        var rep = EdoBuild.CutEdgeSkin("Doi", grp, parts, faces, tol, design: design, backfill: 0f, sealFace: true,
                                       crestBandParts: band, plantPoints: plant, faceKeepOut: keep,
                                       hollowParts: hollow, seated: seated, keepGradeBeside: channel,
                                       keepBatter: design.batterCut > 1e-3f ? design.batterCut : 1f, stairApronFrontOnly: true);
        AssetDatabase.SaveAssetIfDirty(EdoBuild.T().terrainData);
        sb.AppendLine("  庭の土工の矩形 " + keep.Count + " を面の縁から外した");
        sb.AppendLine("  古い皮を外して塞いだ升 " + filled + " / 部材 " + rep.parts + "(土留め " + band.Count + "・石段 " + stairN + "・溝 " + mizoN + ")/ 面 " + faces.Count + " / 守った点 " + plant.Count + " / 据わりを守るメッシュ " + seated.Count);
        sb.AppendLine("  " + rep);
        sb.Append(EdoBuild.SkinGapTable(parts, faces, tol));
        return sb.ToString();
    }
}
