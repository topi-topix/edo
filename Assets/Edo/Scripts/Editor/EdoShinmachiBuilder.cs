// 赤坂新町一〜三丁目+一ツ木町続元赤坂町代地+日ヶ窪町代地 (2026-08-09)
// 【典拠】
//  ・区画=ユーザー下書き(水色1/黄1/緑1/紫1/赤3筆)。切絵図の文字判読はユーザー:
//    水色=赤坂一ツ木町続元赤坂町代地 / 黄=日ヶ窪町代地 / 緑=新町一丁目 / 紫=新町二丁目 / 赤=新町三丁目
//  ・赤坂新町: 一ツ木町と田町の間。一丁目=寛永17年(1640)千代姫付の侍3人拝領→寛文8年(1668)町並家作許可
//    →延宝元年(1673)町奉行支配。二・三丁目=一木村の田地→寛永18年(1641)武家方町並屋敷→元禄9年(1696)
//    拝領町屋敷(新修港区史/港区旧町名由来板/江戸町巡り)。物産=桐油・合羽・髢・傘・籐細工・足袋など。
//    CODH赤坂絵図 9-023(一丁目)/9-024(二丁目)/9-026(三丁目)。
//  ・三丁目の赤3筆は通りの三叉路(南西へ上る道の追分)を囲む両側町の形=下書きの通り再現。
//  ・一ツ木町続元赤坂町代地: 元赤坂町(赤坂最古、寛永14年赤坂御門造成で移転)の飛び代地のうち
//    一ツ木町に続く一筆。CODH抽出に無し→ユーザー判読を正とする。
//  ・日ヶ窪町代地: 麻布日ヶ窪町(北/南、現六本木6丁目・麻布十番)の飛び代地。CODH抽出に無し→同上。
//  ・両代地・各丁目とも坪数・家数・地割の史料未取得→表店列+裏長屋の構成は同時代一般類型【推定スタンドイン】。
//    裏長屋=kidobanya連結スタンドイン(田町と同作法)。木戸・高札・稲荷は史料未確認のため置かない。
// 地形は現地形に従い造成しない([[terrain-follows-present-day]])。区画内は建設前に空地であることを確認済み。
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class EdoShinmachiBuilder
{
    const float ES = 1.818f;
    const string PShop01 = EdoAssets.Eg.Shop01;
    const string PShop02 = EdoAssets.Eg.Shop02;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PBanya = EdoAssets.Eg.Kidobanya;

    // ---- 下書きポリゴン(スケッチ世界座標XZ) ----
    static readonly Vector2[] CY = { new Vector2(-885.87f,1153.45f), new Vector2(-929.56f,1124.32f), new Vector2(-892.20f,1031.23f), new Vector2(-848.51f,1048.33f) };
    static readonly Vector2[] YE = { new Vector2(-848.13f,1047.37f), new Vector2(-891.75f,1030.53f), new Vector2(-882.70f,1004.00f), new Vector2(-835.21f,1014.13f) };
    static readonly Vector2[] GR = { new Vector2(-879.50f,996.86f), new Vector2(-856.11f,908.38f), new Vector2(-799.75f,921.04f), new Vector2(-832.44f,1005.66f) };
    static readonly Vector2[] PU = { new Vector2(-856.11f,907.11f), new Vector2(-838.38f,834.29f), new Vector2(-772.52f,848.22f), new Vector2(-798.77f,919.57f) };
    static readonly Vector2[] RA = { new Vector2(-834.95f,827.52f), new Vector2(-769.82f,840.71f), new Vector2(-754.89f,798.88f), new Vector2(-768.79f,794.04f) };
    static readonly Vector2[] RB = { new Vector2(-751.74f,792.02f), new Vector2(-767.41f,787.17f), new Vector2(-785.16f,761.83f), new Vector2(-777.62f,729.49f), new Vector2(-731.26f,740.27f), new Vector2(-749.59f,790.94f) };
    static readonly Vector2[] RC = { new Vector2(-777.03f,787.86f), new Vector2(-819.29f,810.20f), new Vector2(-830.61f,798.16f), new Vector2(-823.05f,776.18f), new Vector2(-816.87f,751.45f), new Vector2(-796.95f,757.63f) };

    static float Ground(float x, float z) { return EdoTamachiBuilder.Ground(x, z); }
    static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) inside = !inside;
        return inside;
    }
    static Vector2 Inward(Vector2[] poly, int i)
    {
        Vector2 a = poly[i], b = poly[(i + 1) % poly.Length];
        Vector2 d = (b - a).normalized;
        Vector2 n = new Vector2(-d.y, d.x);
        Vector2 mid = (a + b) * 0.5f;
        for (float off = 0.6f; off <= 2.4f; off += 0.6f)
        {
            if (PIP(poly, mid + n * off)) return n;
            if (PIP(poly, mid - n * off)) return -n;
        }
        Vector2 c = Vector2.zero; foreach (var p in poly) c += p; c /= poly.Length;
        return Vector2.Dot(c - mid, n) < 0 ? -n : n;
    }
    static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);   // ★ プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
        var cur = r.transform;
        if (!string.IsNullOrEmpty(child))
            foreach (var seg in child.Split('/'))
            {
                var nx = cur.Find(seg);
                if (nx == null)
                {
                    var g = new GameObject(seg);
                    Undo.RegisterCreatedObjectUndo(g, "grp");
                    g.transform.SetParent(cur, false);
                    nx = g.transform;
                }
                cur = nx;
            }
        return cur;
    }
    static void Assign(GameObject go, Material m)
    {
        foreach (var r in go.GetComponentsInChildren<Renderer>())
        {
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = m;
            r.sharedMaterials = mats;
        }
    }
    static GameObject PlaceFrontV(string path, float sc, Material mat, Transform parent, string name,
        Vector2 A, Vector2 axis, Vector2 inw, float tCenter, float frontInset, float ry)
    {
        Vector2 outw = -inw;
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
        go.name = name;
        go.transform.SetParent(parent, true);
        go.transform.rotation = Quaternion.Euler(0, ry, 0);
        go.transform.localScale = Vector3.one * sc;
        if (mat != null) Assign(go, mat);
        Vector2 seed = A + axis * tCenter + inw * 5f;
        go.transform.position = new Vector3(seed.x, 30, seed.y);
        float oMax = float.MinValue, aMin = float.MaxValue, aMax = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var verts = mesh.vertices;
            for (int i = 0; i < verts.Length; i++)
            {
                var w = mf.transform.TransformPoint(verts[i]);
                float po = w.x * outw.x + w.z * outw.y;
                float pa = w.x * axis.x + w.z * axis.y;
                if (po > oMax) oMax = po;
                if (pa < aMin) aMin = pa; if (pa > aMax) aMax = pa;
            }
        }
        Vector2 fl = A + inw * frontInset;
        float shiftOut = (fl.x * outw.x + fl.y * outw.y) - oMax;
        float shiftAlong = Vector2.Dot(A + axis * tCenter, axis) - (aMin + aMax) * 0.5f;
        go.transform.position += new Vector3(outw.x * shiftOut + axis.x * shiftAlong, 0, outw.y * shiftOut + axis.y * shiftAlong);
        var rs = go.GetComponentsInChildren<Renderer>();
        var b2 = rs[0].bounds; foreach (var r in rs) b2.Encapsulate(r.bounds);
        float g = Ground(b2.center.x, b2.center.z);
        go.transform.position += new Vector3(0, (g - 0.10f) - b2.min.y, 0);
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }
    static void StakeFence(Transform parent, Vector2 A, Vector2 B, string prefix, Material wood)
    {
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / 1.8f));
        float pitch = len / n;
        float ryBar = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
        for (int k = 0; k <= n; k++)
        {
            Vector2 p = A + dir * (pitch * k);
            float g = Ground(p.x, p.y);
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = prefix + "_p" + k; post.transform.SetParent(parent, false);
            post.transform.localScale = new Vector3(0.09f, 0.62f, 0.09f);
            post.transform.position = new Vector3(p.x, g + 0.55f, p.y);
            post.GetComponent<Renderer>().sharedMaterial = wood;
            Undo.RegisterCreatedObjectUndo(post, "fence");
            if (k < n)
            {
                Vector2 m = A + dir * (pitch * (k + 0.5f));
                float g1 = Ground(p.x, p.y), g2 = Ground(p.x + dir.x * pitch, p.y + dir.y * pitch);
                var bar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                bar.name = prefix + "_b" + k; bar.transform.SetParent(parent, false);
                bar.transform.localScale = new Vector3(0.055f, pitch * 0.52f, 0.055f);
                bar.transform.position = new Vector3(m.x, (g1 + g2) * 0.5f + 0.92f, m.y);
                bar.transform.rotation = Quaternion.Euler(90f, ryBar, 0);
                bar.GetComponent<Renderer>().sharedMaterial = wood;
                Undo.RegisterCreatedObjectUndo(bar, "fence");
            }
        }
    }
    static void Well(Transform parent, Vector2 p, Material stone)
    {
        var curb = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        curb.name = "Ido"; curb.transform.SetParent(parent, false);
        curb.transform.localScale = new Vector3(1.15f, 0.35f, 1.15f);
        curb.transform.position = new Vector3(p.x, Ground(p.x, p.y) + 0.35f, p.y);
        curb.GetComponent<Renderer>().sharedMaterial = stone;
        Undo.RegisterCreatedObjectUndo(curb, "ido");
    }

    // 表店列: 辺A->Bに沿って pattern を繰り返し配置。t0/t1で範囲制限(コーナーの取り合い回避)
    static int Row(Transform parent, Vector2[] poly, Vector2 A, Vector2 B, string[] pattern, int seed,
        Material mS1, Material mS2, float t0, float t1, string prefix)
    {
        var rnd = new System.Random(seed);
        Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
        if (t1 < 0) t1 = len + t1; // 負値は末尾からのオフセット
        Vector2 inw = new Vector2(-axis.y, axis.x);
        if (!PIP(poly, A + axis * (len * 0.5f) + inw * 2.5f)) inw = -inw;
        float ryFace = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg;
        float t = t0; int made = 0; int pi = 0;
        while (true)
        {
            string kind = pattern[pi % pattern.Length]; pi++;
            float wLot; string path; float sc; Material mat = null;
            if (kind == "SH") { path = PSmallHouse; wLot = 15.0f; sc = 1f; }
            else if (kind == "S2") { path = PShop02; wLot = 7.4f; sc = ES; mat = mS2; }
            else { path = PShop01; wLot = 5.2f; sc = ES; mat = mS1; }
            if (t + wLot > t1) break;
            PlaceFrontV(path, sc, mat, parent, prefix + kind + "_" + made, A, axis, inw, t + wLot * 0.5f, 0.5f,
                ryFace + ((float)rnd.NextDouble() * 2f - 1f));
            made++; t += wLot + 0.35f;
        }
        return made;
    }
    // 裏長屋: 基準辺A->Bから depth 内側に平行な線上へ kidobanya を連結配置(前面=基準辺向き)
    static int UraRow(Transform parent, Vector2[] poly, Vector2 A, Vector2 B, float depth, float t0, float t1,
        Material mBanya, string prefix, int seed)
    {
        var rnd = new System.Random(seed);
        Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
        if (t1 < 0) t1 = len + t1;
        Vector2 inw = new Vector2(-axis.y, axis.x);
        if (!PIP(poly, A + axis * (len * 0.5f) + inw * 2.5f)) inw = -inw;
        Vector2 A2 = A + inw * depth;
        float ryFace = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg; // 前面=表(基準辺)向き
        float hut = 5.0f; int made = 0;
        for (float t = t0; t + hut <= t1; t += hut)
        {
            Vector2 c = A2 + axis * (t + hut * 0.5f);
            if (!PIP(poly, c) || !PIP(poly, c + inw * 3.5f)) continue; // 奥行き分も区画内に
            PlaceFrontV(PBanya, ES, mBanya, parent, prefix + "_" + made, A2, axis, inw, t + hut * 0.5f, 0f,
                ryFace + ((float)rnd.NextDouble() * 1.2f - 0.6f));
            made++;
        }
        return made;
    }

    // ---------- Stage 1: 5町の建設 ----------
    public static string Stage1_Build()
    {
        var sb = new System.Text.StringBuilder();
        var mS1 = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MShop01);
        var mS2 = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MShop02);
        var mBanya = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MKidobanya);
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);

        // ---- 水色: 一ツ木町続元赤坂町代地 (東=通りへの片側町+裏長屋) ----
        if (GameObject.Find("Edo_Daichi_HitotsugiMotoAkasaka") != null) sb.AppendLine("SKIP Hitotsugi");
        else
        {
            var g = Group("Edo_Daichi_HitotsugiMotoAkasaka", "Omote");
            int n = Row(g, CY, CY[3], CY[0], new[] { "S2", "S1", "S2", "SH", "S1", "S2", "S1" }, 9401, mS1, mS2, 1.0f, -1.0f, "");
            var ug = Group("Edo_Daichi_HitotsugiMotoAkasaka", "Ura");
            int u = UraRow(ug, CY, CY[3], CY[0], 13.5f, 6f, -8f, mBanya, "Ura", 9402);
            var pg = Group("Edo_Daichi_HitotsugiMotoAkasaka", "Props");
            StakeFence(pg, CY[1], CY[2], "FenceW", wood);
            StakeFence(pg, CY[0], CY[1], "FenceN", wood);
            Well(pg, (CY[0] + CY[1] + CY[2] + CY[3]) / 4f, stone);
            Well(pg, CY[3] + ((CY[0] - CY[3]).normalized) * 25f + Inward(CY, 3) * 10f, stone);
            sb.AppendLine("Hitotsugi 表=" + n + " 裏=" + u);
        }
        // ---- 黄: 日ヶ窪町代地 (東への片側町+裏長屋) ----
        if (GameObject.Find("Edo_Daichi_Higakubo") != null) sb.AppendLine("SKIP Higakubo");
        else
        {
            var g = Group("Edo_Daichi_Higakubo", "Omote");
            int n = Row(g, YE, YE[3], YE[0], new[] { "S1", "S2", "S1", "S2" }, 9411, mS1, mS2, 1.0f, -1.0f, "");
            var ug = Group("Edo_Daichi_Higakubo", "Ura");
            int u = UraRow(ug, YE, YE[3], YE[0], 12.0f, 3f, -4f, mBanya, "Ura", 9412);
            var pg = Group("Edo_Daichi_Higakubo", "Props");
            StakeFence(pg, YE[1], YE[2], "FenceW", wood);
            StakeFence(pg, YE[2], YE[3], "FenceS", wood);
            Well(pg, (YE[0] + YE[1] + YE[2] + YE[3]) / 4f, stone);
            sb.AppendLine("Higakubo 表=" + n + " 裏=" + u);
        }
        // ---- 緑: 新町一丁目 (東西両面の両側町+中央裏長屋) ----
        if (GameObject.Find("Edo_Shinmachi_1") != null) sb.AppendLine("SKIP Shinmachi1");
        else
        {
            var gE = Group("Edo_Shinmachi_1", "OmoteE");
            int nE = Row(gE, GR, GR[2], GR[3], new[] { "S2", "S1", "SH", "S2", "S1", "S2" }, 9421, mS1, mS2, 1.0f, -1.0f, "");
            var gW = Group("Edo_Shinmachi_1", "OmoteW");
            int nW = Row(gW, GR, GR[0], GR[1], new[] { "S1", "S2", "S2", "SH", "S1", "S2" }, 9422, mS1, mS2, 1.0f, -1.0f, "");
            var ug = Group("Edo_Shinmachi_1", "Ura");
            int u1 = UraRow(ug, GR, GR[2], GR[3], 14.5f, 8f, -10f, mBanya, "UraE", 9423);
            int u2 = UraRow(ug, GR, GR[0], GR[1], 14.5f, 8f, -10f, mBanya, "UraW", 9424);
            var pg = Group("Edo_Shinmachi_1", "Props");
            StakeFence(pg, GR[3], GR[0], "FenceN", wood);
            Well(pg, (GR[0] + GR[2]) * 0.5f + new Vector2(0, 8f), stone);
            Well(pg, (GR[1] + GR[3]) * 0.5f, stone);
            sb.AppendLine("Shinmachi1 東=" + nE + " 西=" + nW + " 裏=" + (u1 + u2));
        }
        // ---- 紫: 新町二丁目 (同構成) ----
        if (GameObject.Find("Edo_Shinmachi_2") != null) sb.AppendLine("SKIP Shinmachi2");
        else
        {
            var gE = Group("Edo_Shinmachi_2", "OmoteE");
            int nE = Row(gE, PU, PU[2], PU[3], new[] { "S1", "S2", "S2", "SH", "S1" }, 9431, mS1, mS2, 1.0f, -1.0f, "");
            var gW = Group("Edo_Shinmachi_2", "OmoteW");
            int nW = Row(gW, PU, PU[0], PU[1], new[] { "S2", "S2", "S1", "SH", "S2" }, 9432, mS1, mS2, 1.0f, -1.0f, "");
            var ug = Group("Edo_Shinmachi_2", "Ura");
            int u1 = UraRow(ug, PU, PU[2], PU[3], 14.5f, 8f, -10f, mBanya, "UraE", 9433);
            int u2 = UraRow(ug, PU, PU[0], PU[1], 14.5f, 8f, -10f, mBanya, "UraW", 9434);
            var pg = Group("Edo_Shinmachi_2", "Props");
            Well(pg, (PU[0] + PU[2]) * 0.5f, stone);
            Well(pg, (PU[1] + PU[3]) * 0.5f, stone);
            sb.AppendLine("Shinmachi2 東=" + nE + " 西=" + nW + " 裏=" + (u1 + u2));
        }
        // ---- 赤: 新町三丁目 (追分を囲む3筆) ----
        if (GameObject.Find("Edo_Shinmachi_3") != null) sb.AppendLine("SKIP Shinmachi3");
        else
        {
            // A(北の三角地): 東=本通り沿い + 南西=追分の道沿い
            var gA = Group("Edo_Shinmachi_3", "Kita");
            int a1 = Row(gA, RA, RA[1], RA[2], new[] { "S2", "S1", "S1", "S2" }, 9441, mS1, mS2, 1.0f, -1.0f, "E");
            int a2 = Row(gA, RA, RA[3], RA[0], new[] { "S1", "S2", "S1", "S1" }, 9442, mS1, mS2, 8.0f, -14f, "SW");
            Well(gA, (RA[1] + RA[3]) * 0.5f, stone);
            // B(南の区画): 東=本通り + 北/北西=追分 + 西=脇道
            var gB = Group("Edo_Shinmachi_3", "Minami");
            int b1 = Row(gB, RB, RB[4], RB[5], new[] { "S2", "S1", "S2", "S1" }, 9443, mS1, mS2, 1.0f, -1.0f, "E");
            int b2 = Row(gB, RB, RB[1], RB[2], new[] { "S1", "S2", "S1" }, 9444, mS1, mS2, 1.0f, -1.0f, "NW");
            int b3 = Row(gB, RB, RB[2], RB[3], new[] { "S1", "S1", "S2" }, 9445, mS1, mS2, 1.0f, -1.0f, "W");
            StakeFence(gB, RB[3], RB[4], "FenceS", wood);
            Well(gB, (RB[0] + RB[3]) * 0.5f, stone);
            // C(西の区画): 北東=追分の道沿い + 南東=脇道沿い
            var gC = Group("Edo_Shinmachi_3", "Nishi");
            int c1 = Row(gC, RC, RC[0], RC[1], new[] { "S2", "S1", "S2", "S1" }, 9446, mS1, mS2, 1.0f, -1.0f, "NE");
            int c2 = Row(gC, RC, RC[5], RC[0], new[] { "S1", "S2", "S1" }, 9447, mS1, mS2, 1.0f, -1.0f, "SE");
            StakeFence(gC, RC[1], RC[2], "FenceN", wood);
            StakeFence(gC, RC[2], RC[3], "FenceW1", wood);
            StakeFence(gC, RC[3], RC[4], "FenceW2", wood);
            StakeFence(gC, RC[4], RC[5], "FenceS", wood);
            Well(gC, (RC[1] + RC[4]) * 0.5f, stone);
            sb.AppendLine("Shinmachi3 A=" + a1 + "+" + a2 + " B=" + b1 + "+" + b2 + "+" + b3 + " C=" + c1 + "+" + c2);
        }
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }

    // ---------- Stage 2: splat (区画=踏み固め土 / 通り=露地) ----------
    // 通りの中心線: 本通り(一ツ木通り筋)+追分の2筋+丁目境の辻
    static readonly Vector2[][] Roads = {
        new Vector2[]{ new Vector2(-880,1160), new Vector2(-843,1046), new Vector2(-830,1010), new Vector2(-795,917), new Vector2(-766,845), new Vector2(-748,795), new Vector2(-726,738) },
        new Vector2[]{ new Vector2(-836.7f,830.9f), new Vector2(-771.2f,844.5f) },   // 二・三丁目境の通り
        new Vector2[]{ new Vector2(-827,819), new Vector2(-773,791) },               // 追分南の道(C-A間)
        new Vector2[]{ new Vector2(-788,765), new Vector2(-776,740) },               // 脇道(C-B間)
        new Vector2[]{ new Vector2(-881,1000.5f), new Vector2(-834,1010) },          // 一丁目北の辻(円通寺坂方面)
    };
    static float DistToPolyline(Vector2[] line, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < line.Length - 1; i++)
        {
            Vector2 a = line[i], b = line[i + 1];
            Vector2 d = b - a; float len = d.magnitude; d /= len;
            float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
            float dd = (p - (a + d * t)).magnitude;
            if (dd < m) m = dd;
        }
        return m;
    }
    public static string Stage2_Splat()
    {
        var t = EdoTamachiBuilder.T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -935, x1 = -722, z0 = 722, z1 = 1165;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A2 = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        var parcels = new Vector2[][] { CY, YE, GR, PU, RA, RB, RC };
        // 成満寺境内には触れない
        var JMx = new Vector2[]{ new Vector2(-825.19f,1019.95f), new Vector2(-816.59f,996.54f), new Vector2(-786.97f,1008.00f), new Vector2(-797.00f,1033.32f) };
        int changed = 0;
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                if (PIP(JMx, p)) continue;
                float noise = Mathf.PerlinNoise(wx * 0.13f, wz * 0.13f);
                float bare, grass, dirt;
                bool inParcel = false;
                foreach (var s in parcels) if (PIP(s, p)) { inParcel = true; break; }
                bool onRoad = false;
                if (!inParcel)
                    foreach (var rd in Roads) if (DistToPolyline(rd, p) < 3.5f) { onRoad = true; break; }
                if (inParcel)
                {   // 町屋区画: 踏み固め土
                    bare = Mathf.Lerp(0.40f, 0.58f, noise); grass = 0.10f; dirt = 1f - bare - grass;
                }
                else if (onRoad)
                {   // 通り: 露地
                    bare = Mathf.Lerp(0.55f, 0.72f, noise); grass = 0.04f; dirt = 1f - bare - grass;
                }
                else continue;
                float sum = bare + grass + dirt;
                for (int l = 0; l < L; l++) A2[zz, xx, l] = 0;
                A2[zz, xx, 0] = dirt / sum; A2[zz, xx, 1] = grass / sum; A2[zz, xx, 2] = bare / sum;
                changed++;
            }
        td.SetAlphamaps(ix0, iz0, A2);
        return "splat cells=" + changed;
    }
}
