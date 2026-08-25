// 赤坂田町五丁目の対岸(堀端通の東側〜溜池汀)の権利地 4区画 (2026-08-09)
// 【典拠】ユーザー下書き(スケッチ4色ポリゴン)に書き起こされた絵図の文字のみ:
//   水色=「町屋」 / 黄=「町方?預」(?は判読不能。町方支配預り地か) / 緑=「拝借地(櫨実会所)」 / 紫=「堀口儀八郎」
//   ・櫨実会所: 櫨実(はぜのみ)=木蝋原料の集荷会所と解釈。建物構成(会所母屋+蔵+筵干し場)は
//     一般類型からの【推定スタンドイン】。文献裏付けは未取得(2026-08-09 Web検索でヒットなし)。
//   ・堀口儀八郎: 人名のみ判明。小規模拝領屋敷(板塀+冠木門+小主屋)の【推定スタンドイン】。
//   ・町方預: 用途不明のため建物を置かず預り明地(杭柵+物干+草地)として表現【推定】。
//   ・櫨並木/母屋/小主屋のアセットは専用品が無く代用(櫨=Sakura_Summer、母屋=Village Kit House)【スタンドイン】。
// 地形は現地形に従い造成しない([[terrain-follows-present-day]])。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoTamachi5EastBuilder
{
    const float ES = 1.818f;
    const string PShop01 = EdoAssets.Eg.Shop01;
    const string PShop02 = EdoAssets.Eg.Shop02;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PHouse = EdoAssets.VK.House;
    const string PKura = EdoAssets.Eg.Kura;
    const string PKabukimon = EdoAssets.Eg.Kabukimon;
    const string RootName = "Edo_Tamachi5_Higashi";

    // ---- 下書きポリゴン(スケッチの世界座標XZをそのまま採用) ----
    static readonly Vector2[] MachiyaPoly = {   // 水色
        new Vector2(-591.62f,564.82f), new Vector2(-610.68f,600.44f),
        new Vector2(-605.31f,603.80f), new Vector2(-582.62f,570.24f) };
    static readonly Vector2[] AzukariPoly = {   // 黄
        new Vector2(-603.71f,604.75f), new Vector2(-580.71f,571.84f),
        new Vector2(-573.68f,577.27f), new Vector2(-597.32f,608.27f) };
    static readonly Vector2[] KaishoPoly = {    // 緑(凹多角形: 紫区画を切り欠く)
        new Vector2(-571.12f,577.91f), new Vector2(-563.13f,585.26f),
        new Vector2(-621.93f,656.52f), new Vector2(-635.03f,649.17f),
        new Vector2(-624.43f,627.00f), new Vector2(-613.30f,633.19f),
        new Vector2(-571.76f,578.23f) };
    static readonly Vector2[] HoriguchiPoly = { // 紫
        new Vector2(-623.32f,625.57f), new Vector2(-611.62f,602.32f),
        new Vector2(-597.64f,610.19f), new Vector2(-613.94f,631.92f) };

    static float Ground(float x, float z) { return EdoBuild.Ground(x, z); }
    static Transform Group(string child)
    {
        var r = GameObject.Find(RootName);
        if (r == null) { r = new GameObject(RootName); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        var cur = r.transform;
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
    static bool Exists(string child)
    {
        var r = GameObject.Find(RootName);
        return r != null && r.transform.Find(child) != null;
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
    // EdoTamachiBuilder.PlaceFront と同式: 前面(outw側)を辺A+inw*frontInset に、走り中心を tCenter に、接地
    static GameObject PlaceFront(string path, float sc, Material mat, Transform parent, string name,
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
        go.transform.position = new Vector3(seed.x, 20, seed.y);
        var rs = go.GetComponentsInChildren<Renderer>();
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        float frontProj = b.center.x * outw.x + b.center.z * outw.y + Mathf.Abs(b.extents.x * outw.x) + Mathf.Abs(b.extents.z * outw.y);
        Vector2 fl = A + inw * frontInset;
        float shiftOut = (fl.x * outw.x + fl.y * outw.y) - frontProj;
        float cProj = b.center.x * axis.x + b.center.z * axis.y;
        float shiftAlong = Vector2.Dot(A + axis * tCenter, axis) - cProj;
        go.transform.position += new Vector3(outw.x * shiftOut + axis.x * shiftAlong, 0, outw.y * shiftOut + axis.y * shiftAlong);
        var b2 = rs[0].bounds; foreach (var r in rs) b2.Encapsulate(r.bounds);
        float g = Ground(b2.center.x, b2.center.z);
        go.transform.position += new Vector3(0, (g - 0.06f) - b2.min.y, 0);
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }
    // 辺の内向き法線。凹多角形では重心判定が破綻するので辺中点+微小オフセットのPIPで決める
    static Vector2 Inward(Vector2[] poly, int i)
    {
        Vector2 a = poly[i], b = poly[(i + 1) % poly.Length];
        Vector2 d = (b - a).normalized;
        Vector2 n = new Vector2(-d.y, d.x);
        Vector2 mid = (a + b) * 0.5f;
        for (float off = 0.6f; off <= 2.4f; off += 0.6f)
        {
            if (EdoGeom.PIP(poly, mid + n * off)) return n;
            if (EdoGeom.PIP(poly, mid - n * off)) return -n;
        }
        Vector2 c = Vector2.zero; foreach (var p in poly) c += p; c /= poly.Length;
        return Vector2.Dot(c - mid, n) < 0 ? -n : n;
    }
    // 杭柵(procedural: 杭+横貫1本)。地形追従
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
    // 物干(田町土手のものと同型)
    static void Rack(Transform parent, Vector2 p, float ry, Material wood, string name)
    {
        var g = new GameObject(name);
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(p.x, Ground(p.x, p.y), p.y);
        g.transform.rotation = Quaternion.Euler(0, ry, 0);
        Undo.RegisterCreatedObjectUndo(g, "rack");
        for (int k = 0; k < 2; k++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.09f, 0.95f, 0.09f);
            post.transform.localPosition = new Vector3(k == 0 ? -1.8f : 1.8f, 0.95f, 0);
            post.GetComponent<Renderer>().sharedMaterial = wood;
        }
        var bar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        bar.transform.SetParent(g.transform, false);
        bar.transform.localScale = new Vector3(0.05f, 1.85f, 0.05f);
        bar.transform.localEulerAngles = new Vector3(0, 0, 90);
        bar.transform.localPosition = new Vector3(0, 1.8f, 0);
        bar.GetComponent<Renderer>().sharedMaterial = wood;
    }

    // ---------- Stage 1: 建物・囲い ----------
    public static string Stage1_Build()
    {
        var sb = new System.Text.StringBuilder();
        var mS1 = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MShop01);
        var mS2 = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MShop02);
        var mKido = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MKido);
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        var mushiro = new Material(Shader.Find("Universal Render Pipeline/Lit")); mushiro.color = new Color(0.72f, 0.62f, 0.42f);
        var rnd = new System.Random(20260809);

        // ---- 水色: 町屋(堀端通に西面する小店列) ----
        if (Exists("Machiya")) sb.AppendLine("SKIP Machiya");
        else
        {
            var g = Group("Machiya");
            Vector2 A = MachiyaPoly[0], B = MachiyaPoly[1];             // 西長辺=街路側
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            Vector2 inw = Inward(MachiyaPoly, 0);                       // 東向き(敷地内側)
            float ryFace = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg; // 前面=西(街路)
            string[] pattern = { "S2", "S1", "S1", "S2", "S1", "S2" };
            float t = 0.8f; int made = 0; int pi = 0;
            while (true)
            {
                string kind = pattern[pi % pattern.Length]; pi++;
                float wLot = kind == "S2" ? 7.4f : 5.2f;
                string path = kind == "S2" ? PShop02 : PShop01;
                Material mat = kind == "S2" ? mS2 : mS1;
                if (t + wLot > len - 0.8f) break;
                PlaceFront(path, ES, mat, g, kind + "_" + made, A, axis, inw, t + wLot * 0.5f, 0.5f,
                    ryFace + ((float)rnd.NextDouble() * 2f - 1f));
                made++; t += wLot + 0.3f;
            }
            // 裏手の井戸1基
            Vector2 wp = A + axis * (len * 0.5f) + inw * 7.5f;
            if (EdoGeom.PIP(MachiyaPoly, wp)) Well(g, wp, stone);
            sb.AppendLine("Machiya 表店=" + made);
        }

        // ---- 黄: 町方預(預り明地: 杭柵+物干+草地) ----
        if (Exists("Azukari")) sb.AppendLine("SKIP Azukari");
        else
        {
            var g = Group("Azukari");
            int N = AzukariPoly.Length;
            for (int i = 0; i < N; i++)
            {   // 全周を杭柵。南西長辺(町屋との境=辺1)は柵を省き裏木戸的に開けておく
                if (i == 1) continue;
                StakeFence(g, AzukariPoly[i], AzukariPoly[(i + 1) % N], "Fence_" + i, wood);
            }
            Vector2 A = AzukariPoly[0], B = AzukariPoly[3];
            Vector2 axis = (AzukariPoly[3] - AzukariPoly[0]).normalized;
            Vector2 lonAxis = (AzukariPoly[1] - AzukariPoly[0]).normalized; // 長手
            float lonLen = (AzukariPoly[1] - AzukariPoly[0]).magnitude;
            Vector2 inw = Inward(AzukariPoly, 0);
            float ryRack = Mathf.Atan2(lonAxis.x, lonAxis.y) * Mathf.Rad2Deg;
            int racks = 0;
            for (float tt = 6f; tt < lonLen - 4f; tt += 9f)
            {
                Vector2 p = AzukariPoly[0] + lonAxis * tt + inw * (3.0f + 2.5f * (float)rnd.NextDouble());
                if (!EdoGeom.PIP(AzukariPoly, p)) continue;
                Rack(g, p, ryRack + ((float)rnd.NextDouble() * 12f - 6f), wood, "Rack_" + racks);
                racks++;
            }
            sb.AppendLine("Azukari 物干=" + racks);
        }

        // ---- 緑: 拝借地(櫨実会所) ----
        if (Exists("Kaisho")) sb.AppendLine("SKIP Kaisho");
        else
        {
            var g = Group("Kaisho");
            var kak = Group("Kaisho/Kakoi");
            // 北の広がり部の西辺 G4->G5 に表門(冠木門)
            Vector2 gA = KaishoPoly[3], gB = KaishoPoly[4];             // (-635.0,649.2)->(-624.4,627.0)
            Vector2 gAxis = (gB - gA).normalized; float gLen = (gB - gA).magnitude;
            Vector2 gInw = Inward(KaishoPoly, 3);
            float gRy = Mathf.Atan2(-gInw.x, -gInw.y) * Mathf.Rad2Deg;
            float gateT = gLen * 0.42f;
            Vector2 gate2 = gA + gAxis * gateT;
            var mon = PlaceFront(PKabukimon, ES, null, g, "Mon", gA, gAxis, gInw, gateT, 0.3f, gRy);
            if (mKido != null) Assign(mon, mKido);
            // 囲い: 西辺(門の間口を開ける)+北辺+切欠き辺は板塀、汀側(G2->G3)と南の帯は杭柵
            EdoNishiTameikeBuilder.DobeiRun(kak, gA, gB, -gInw, "HeiW", true, 0, gate2, 2.6f);
            EdoNishiTameikeBuilder.DobeiRun(kak, KaishoPoly[2], KaishoPoly[3], -Inward(KaishoPoly, 2), "HeiN", true, 0, Vector2.zero, -1);
            EdoNishiTameikeBuilder.DobeiRun(kak, KaishoPoly[4], KaishoPoly[5], -Inward(KaishoPoly, 4), "HeiS", true, 0, Vector2.zero, -1);
            StakeFence(kak, KaishoPoly[5], KaishoPoly[6], "FenceW", wood);   // 帯の西縁(黄との境)
            StakeFence(kak, KaishoPoly[6], KaishoPoly[0], "FenceS", wood);   // 南端
            StakeFence(kak, KaishoPoly[0], KaishoPoly[1], "FenceSE", wood);
            StakeFence(kak, KaishoPoly[1], KaishoPoly[2], "FenceE", wood);   // 汀側(土手法肩なり)
            // 会所母屋: 門の正面奥(推定スタンドイン=Village Kit House)
            var bg = Group("Kaisho/Buildings");
            Vector2 hp = gate2 + gInw * 11f;
            PlaceFront(PHouse, 0.72f, null, bg, "Kaisho_Omoya", gA, gAxis, gInw, gateT, 8.0f, gRy);
            // 蔵2棟: 北辺沿い(妻を北へ)
            Vector2 nA = KaishoPoly[2], nB = KaishoPoly[3];
            Vector2 nAxis = (nB - nA).normalized; float nLen = (nB - nA).magnitude;
            Vector2 nInw = Inward(KaishoPoly, 2);
            float nRy = Mathf.Atan2(-nInw.x, -nInw.y) * Mathf.Rad2Deg;
            PlaceFront(PKura, ES, null, bg, "Kura_1", nA, nAxis, nInw, nLen * 0.30f, 1.6f, nRy + 180f);
            PlaceFront(PKura, ES, null, bg, "Kura_2", nA, nAxis, nInw, nLen * 0.62f, 1.6f, nRy + 180f);
            // 筵干し場: 庭の切欠き辺沿いに筵(薄板)を2列
            var dg = Group("Kaisho/Hoshiba");
            Vector2 sA = KaishoPoly[4];
            Vector2 sAxis = (KaishoPoly[5] - KaishoPoly[4]).normalized;
            float sLen = (KaishoPoly[5] - KaishoPoly[4]).magnitude;
            Vector2 sInw = Inward(KaishoPoly, 4);
            float mRy = Mathf.Atan2(sAxis.x, sAxis.y) * Mathf.Rad2Deg;
            int mats = 0;
            for (int row = 0; row < 2; row++)
                for (float tt = 2.5f; tt < sLen - 1.5f; tt += 2.4f)
                {
                    Vector2 p = sA + sAxis * tt + sInw * (3.2f + row * 2.0f);
                    if (!EdoGeom.PIP(KaishoPoly, p)) continue;
                    var m = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    m.name = "Mushiro_" + mats; m.transform.SetParent(dg, false);
                    m.transform.localScale = new Vector3(1.75f, 0.05f, 0.92f);
                    m.transform.position = new Vector3(p.x, Ground(p.x, p.y) + 0.06f, p.y);
                    m.transform.rotation = Quaternion.Euler(0, mRy + ((float)rnd.NextDouble() * 8f - 4f), 0);
                    m.GetComponent<Renderer>().sharedMaterial = mushiro;
                    Undo.RegisterCreatedObjectUndo(m, "mushiro");
                    mats++;
                }
            // 井戸
            Well(bg, gate2 + gInw * 6f + gAxis * 6f, stone);
            // 帯の内側に櫨並木(スタンドイン=Sakura_Summer)
            var tg = Group("Kaisho/Hazenoki");
            string[] trees = {
                EdoAssets.JG.SakuraMid01,
                EdoAssets.JG.SakuraMid05 };
            Vector2 bA = KaishoPoly[6], bB = KaishoPoly[5];             // 帯の西縁に沿って南->北
            Vector2 bAxis = (bB - bA).normalized; float bLen = (bB - bA).magnitude;
            Vector2 bInw = Inward(KaishoPoly, 5) * -1f;                 // 帯の内側(東)へ
            int planted = 0;
            for (float tt = 6f; tt < bLen - 4f; tt += 11f)
            {
                Vector2 p = bA + bAxis * tt + bInw * (4.0f + 2.0f * (float)rnd.NextDouble());
                if (!EdoGeom.PIP(KaishoPoly, p)) continue;
                float gy = Ground(p.x, p.y);
                if (gy < 7.2f) continue;
                var pa = AssetDatabase.LoadAssetAtPath<GameObject>(trees[rnd.Next(trees.Length)]);
                var tr = (GameObject)PrefabUtility.InstantiatePrefab(pa);
                tr.name = "Haze_" + planted; tr.transform.SetParent(tg, true);
                tr.transform.position = new Vector3(p.x, gy - 0.05f, p.y);
                tr.transform.rotation = Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
                tr.transform.localScale = Vector3.one * (0.85f + 0.35f * (float)rnd.NextDouble());
                Undo.RegisterCreatedObjectUndo(tr, "haze");
                planted++;
            }
            sb.AppendLine("Kaisho 筵=" + mats + " 櫨=" + planted);
        }

        // ---- 紫: 堀口儀八郎(小拝領屋敷) ----
        if (Exists("Horiguchi")) sb.AppendLine("SKIP Horiguchi");
        else
        {
            var g = Group("Horiguchi");
            var kak = Group("Horiguchi/Kakoi");
            int N = HoriguchiPoly.Length;
            Vector2 fA = HoriguchiPoly[0], fB = HoriguchiPoly[1];       // 西辺=街路側
            Vector2 fAxis = (fB - fA).normalized; float fLen = (fB - fA).magnitude;
            Vector2 fInw = Inward(HoriguchiPoly, 0);
            float fRy = Mathf.Atan2(-fInw.x, -fInw.y) * Mathf.Rad2Deg;
            float gateT = fLen * 0.5f;
            Vector2 gate2 = fA + fAxis * gateT;
            var mon = PlaceFront(PKabukimon, ES * 0.92f, null, g, "Mon", fA, fAxis, fInw, gateT, 0.3f, fRy);
            if (mKido != null) Assign(mon, mKido);
            for (int i = 0; i < N; i++)
            {
                Vector2 a = HoriguchiPoly[i], b = HoriguchiPoly[(i + 1) % N];
                Vector2 outw = -Inward(HoriguchiPoly, i);
                if (i == 0) EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, gate2, 2.4f);
                else EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
            }
            // 小主屋: 門の正面奥、玄関を門(西)へ
            PlaceFront(PSmallHouse, 1.0f, null, g, "Omoya", fA, fAxis, fInw, gateT + 2.0f, 7.5f, fRy);
            Well(g, fA + fAxis * (fLen * 0.22f) + fInw * 5.5f, stone);
            // 庭木1本(スタンドイン)
            var pa = AssetDatabase.LoadAssetAtPath<GameObject>(
                EdoAssets.JG.SakuraMid01);
            if (pa != null)
            {
                Vector2 p = fA + fAxis * (fLen * 0.82f) + fInw * 10.5f;
                if (EdoGeom.PIP(HoriguchiPoly, p))
                {
                    var tr = (GameObject)PrefabUtility.InstantiatePrefab(pa);
                    tr.name = "Niwaki"; tr.transform.SetParent(g, true);
                    tr.transform.position = new Vector3(p.x, Ground(p.x, p.y) - 0.05f, p.y);
                    tr.transform.rotation = Quaternion.Euler(0, 137f, 0);
                    tr.transform.localScale = Vector3.one * 0.9f;
                    Undo.RegisterCreatedObjectUndo(tr, "niwaki");
                }
            }
            sb.AppendLine("Horiguchi built");
        }
        AssetDatabase.SaveAssets();
        return "built\n" + sb;
    }

    // EdoGeom.DistToPolyEdge と実装差あり — 統一は裁定待ち
    static float DistToPolyEdge(Vector2[] poly, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % poly.Length];
            Vector2 d = b - a; float len = d.magnitude; d /= len;
            float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
            float dd = (p - (a + d * t)).magnitude;
            if (dd < m) m = dd;
        }
        return m;
    }
    static Bounds RBOf(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }
    // OBBの4隅(メッシュ頂点を建物自身のright/forward軸へ射影)。
    // 斜め回転の建物をワールドAABBで判定するとAABBが~1.3倍に膨らみ偽NGになる(スキル既知の罠)
    static Vector2[] FootprintCorners(GameObject go)
    {
        Vector3 r3 = go.transform.rotation * Vector3.right;
        Vector3 f3 = go.transform.rotation * Vector3.forward;
        Vector2 r = new Vector2(r3.x, r3.z).normalized, f = new Vector2(f3.x, f3.z).normalized;
        float rMin = float.MaxValue, rMax = float.MinValue, fMin = float.MaxValue, fMax = float.MinValue;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            var mesh = mf.sharedMesh; if (mesh == null) continue;
            var verts = mesh.vertices;
            for (int i = 0; i < verts.Length; i++)
            {
                var w = mf.transform.TransformPoint(verts[i]);
                var p = new Vector2(w.x, w.z);
                float pr = Vector2.Dot(p, r), pf = Vector2.Dot(p, f);
                if (pr < rMin) rMin = pr; if (pr > rMax) rMax = pr;
                if (pf < fMin) fMin = pf; if (pf > fMax) fMax = pf;
            }
        }
        return new Vector2[] {
            r * rMin + f * fMin, r * rMin + f * fMax,
            r * rMax + f * fMin, r * rMax + f * fMax };
    }
    // 2D OBB同士の重なり(分離軸判定)。pad>0 で判定を太らせる
    static bool OverlapSAT(Vector2[] A, Vector2[] B, float pad)
    {
        var axes = new Vector2[] {
            (A[1] - A[0]).normalized, (A[2] - A[0]).normalized,
            (B[1] - B[0]).normalized, (B[2] - B[0]).normalized };
        foreach (var ax in axes)
        {
            float aMin = float.MaxValue, aMax = float.MinValue, bMin = float.MaxValue, bMax = float.MinValue;
            foreach (var p in A) { float v = Vector2.Dot(p, ax); if (v < aMin) aMin = v; if (v > aMax) aMax = v; }
            foreach (var p in B) { float v = Vector2.Dot(p, ax); if (v < bMin) bMin = v; if (v > bMax) bMax = v; }
            if (aMax < bMin - pad || bMax < aMin - pad) return false;
        }
        return true;
    }
    // 頂点射影で正確に前面合わせする配置。
    // PlaceFront は回転AABBの支持点で合わせるため、斜め回転だと数m奥へズレる(このズレが母屋のはみ出しの真因)
    static GameObject PlaceFrontV(string path, float sc, Transform parent, string name,
        Vector2 A, Vector2 axis, Vector2 inw, float tCenter, float frontInset, float ry)
    {
        Vector2 outw = -inw;
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
        go.name = name;
        go.transform.SetParent(parent, true);
        go.transform.rotation = Quaternion.Euler(0, ry, 0);
        go.transform.localScale = Vector3.one * sc;
        Vector2 seed = A + axis * tCenter + inw * 5f;
        go.transform.position = new Vector3(seed.x, 20, seed.y);
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
        go.transform.position += new Vector3(0, (g - 0.06f) - b2.min.y, 0);
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }
    // 敷地内に収まる最大 frontInset を試行して配置(OBB全隅が margin 以上内側)
    static GameObject PlaceFitted(string path, float sc, Transform parent, string name, Vector2[] poly,
        Vector2 A, Vector2 axis, Vector2 inw, float tCenter, float[] insets, float margin, float ry,
        System.Text.StringBuilder log)
    {
        foreach (float inset in insets)
        {
            var go = PlaceFrontV(path, sc, parent, name, A, axis, inw, tCenter, inset, ry);
            bool ok = true; float worst = float.MaxValue;
            foreach (var c in FootprintCorners(go))
            {
                float dd = DistToPolyEdge(poly, c);
                if (!EdoGeom.PIP(poly, c)) { ok = false; worst = Mathf.Min(worst, -dd); continue; }
                if (dd < worst) worst = dd;
                if (dd < margin) ok = false;
            }
            log.AppendLine(name + " inset=" + inset + " worst=" + worst.ToString("F2") + (ok ? " OK" : " NG"));
            if (ok) return go;
            UnityEngine.Object.DestroyImmediate(go);
        }
        log.AppendLine(name + " FAILED all insets");
        return null;
    }

    // 一度きりの修正 Stage のガード。効果はシーンに反映済みで、再実行は非冪等(const だと CS0162)
    static readonly bool FixApplied = true;

    // ---------- Stage 1b: 初回ビルドの修正 ----------
    public static string Stage1b_Fix()
    {
        if (FixApplied) return "⛔ 適用済み。一度きりの修正で非冪等 — 再実行しない";
        var sb = new System.Text.StringBuilder();
        var root = GameObject.Find(RootName);
        if (root == null) return "no root";
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        var mushiro = new Material(Shader.Find("Universal Render Pipeline/Lit")); mushiro.color = new Color(0.72f, 0.62f, 0.42f);
        var rnd = new System.Random(20260810);
        var kill = new List<GameObject>();

        var kak = root.transform.Find("Kaisho/Kakoi");
        var bg = root.transform.Find("Kaisho/Buildings");
        var dg = root.transform.Find("Kaisho/Hoshiba");
        // 1) 堀口との共有境界の二重塀(HeiS_*)を撤去
        foreach (Transform c in kak) if (c.name.StartsWith("HeiS_")) kill.Add(c.gameObject);
        // 2) FenceW の堀口東塀と重なる区間(t<21m ≒ index<=11)を撤去
        foreach (Transform c in kak)
        {
            if (!c.name.StartsWith("FenceW_")) continue;
            string tail = c.name.Substring("FenceW_".Length); // "p13" / "b13"
            int idx;
            if (tail.Length >= 2 && int.TryParse(tail.Substring(1), out idx) && idx <= 11)
                kill.Add(c.gameObject);
        }
        // 3) 蔵・母屋・井戸・筵を撤去して置き直し
        foreach (Transform c in bg) if (c.name.StartsWith("Kura_") || c.name == "Kaisho_Omoya" || c.name == "Ido") kill.Add(c.gameObject);
        foreach (Transform c in dg) kill.Add(c.gameObject);
        var hg = root.transform.Find("Horiguchi");
        foreach (Transform c in hg) if (c.name == "Omoya") kill.Add(c.gameObject);
        foreach (var k in kill) UnityEngine.Object.DestroyImmediate(k);
        sb.AppendLine("removed=" + kill.Count);

        // --- 会所: 置き直し ---
        Vector2 gA = KaishoPoly[3], gB = KaishoPoly[4];
        Vector2 gAxis = (gB - gA).normalized; float gLen = (gB - gA).magnitude;
        Vector2 gInw = Inward(KaishoPoly, 3);
        float gRy = Mathf.Atan2(-gInw.x, -gInw.y) * Mathf.Rad2Deg;
        float gateT = gLen * 0.42f;
        Vector2 gate2 = gA + gAxis * gateT;
        // 蔵: 北辺沿いに間隔を空けて2棟(幅6.2m)
        Vector2 nA = KaishoPoly[2], nB = KaishoPoly[3];
        Vector2 nAxis = (nB - nA).normalized; float nLen = (nB - nA).magnitude;
        Vector2 nInw = Inward(KaishoPoly, 2);
        float nRy = Mathf.Atan2(-nInw.x, -nInw.y) * Mathf.Rad2Deg;
        PlaceFront(PKura, ES, null, bg, "Kura_1", nA, nAxis, nInw, nLen * 0.225f, 1.2f, nRy + 180f);
        PlaceFront(PKura, ES, null, bg, "Kura_2", nA, nAxis, nInw, nLen * 0.76f, 1.2f, nRy + 180f);
        // 母屋: 収まる inset を試行
        PlaceFitted(PHouse, 0.72f, bg, "Kaisho_Omoya", KaishoPoly, gA, gAxis, gInw, gateT,
            new float[] { 8f, 7f, 6f, 5f, 4f }, 1.0f, gRy, sb);
        // 井戸: 門の北脇
        Well(bg, gA + gAxis * 3.3f + gInw * 3.5f, stone);
        // 筵干し場: 帯の北の平坦部(西縁=辺5沿い、東へ2.5/4.5m)
        Vector2 e5A = KaishoPoly[5], e5B = KaishoPoly[6];
        Vector2 e5Axis = (e5B - e5A).normalized;
        Vector2 e5Inw = Inward(KaishoPoly, 5);
        float mRy = Mathf.Atan2(e5Axis.x, e5Axis.y) * Mathf.Rad2Deg;
        int mats = 0;
        for (int row = 0; row < 2; row++)
            for (float tt = 2.5f; tt < 19f; tt += 2.4f)
            {
                Vector2 p = e5A + e5Axis * tt + e5Inw * (2.5f + row * 2.0f);
                if (!EdoGeom.PIP(KaishoPoly, p)) continue;
                if (Ground(p.x, p.y) < 9.2f) continue;
                var m = GameObject.CreatePrimitive(PrimitiveType.Cube);
                m.name = "Mushiro_" + mats; m.transform.SetParent(dg, false);
                m.transform.localScale = new Vector3(1.75f, 0.05f, 0.92f);
                m.transform.position = new Vector3(p.x, Ground(p.x, p.y) + 0.06f, p.y);
                m.transform.rotation = Quaternion.Euler(0, mRy + ((float)rnd.NextDouble() * 8f - 4f), 0);
                m.GetComponent<Renderer>().sharedMaterial = mushiro;
                Undo.RegisterCreatedObjectUndo(m, "mushiro");
                mats++;
            }
        sb.AppendLine("mushiro=" + mats);

        // --- 堀口: 主屋を奥行のある南寄りへ 0.9倍で置き直し ---
        Vector2 fA = HoriguchiPoly[0], fB = HoriguchiPoly[1];
        Vector2 fAxis = (fB - fA).normalized; float fLen = (fB - fA).magnitude;
        Vector2 fInw = Inward(HoriguchiPoly, 0);
        float fRy = Mathf.Atan2(-fInw.x, -fInw.y) * Mathf.Rad2Deg;
        PlaceFitted(PSmallHouse, 0.9f, hg, "Omoya", HoriguchiPoly, fA, fAxis, fInw, fLen * 0.60f,
            new float[] { 3.5f, 3.0f, 2.5f, 2.0f }, 0.7f, fRy, sb);
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }

    // ---------- Stage 1c: 母屋の再試行(縮小+位置候補)と筵の置き直し ----------
    public static string Stage1c_Fix2()
    {
        if (FixApplied) return "⛔ 適用済み。一度きりの修正で非冪等 — 再実行しない";
        var sb = new System.Text.StringBuilder();
        var root = GameObject.Find(RootName);
        if (root == null) return "no root";
        var bg = root.transform.Find("Kaisho/Buildings");
        var dg = root.transform.Find("Kaisho/Hoshiba");
        var hg = root.transform.Find("Horiguchi");
        var mushiroM = new Material(Shader.Find("Universal Render Pipeline/Lit")); mushiroM.color = new Color(0.72f, 0.62f, 0.42f);
        var rnd = new System.Random(20260811);

        // 0) 既存の蔵・母屋を撤去して母屋→蔵の順に置き直す
        var kill = new List<GameObject>();
        foreach (Transform c in bg) if (c.name.StartsWith("Kura_") || c.name == "Kaisho_Omoya") kill.Add(c.gameObject);
        foreach (var k in kill) UnityEngine.Object.DestroyImmediate(k);

        // --- 会所母屋: 頭部は南ほど深い台形なので、汀の辺(edge1)に背を向けて置く ---
        GameObject house = null;
        {
            Vector2 sA = KaishoPoly[1], sB = KaishoPoly[2];
            Vector2 sAxis = (sB - sA).normalized; float sLen = (sB - sA).magnitude;
            Vector2 sInw = Inward(KaishoPoly, 1);                      // 内陸向き
            float faceRy = Mathf.Atan2(sInw.x, sInw.y) * Mathf.Rad2Deg; // 前面=庭側
            float[] tcs = { 0.86f, 0.88f, 0.84f, 0.82f };
            foreach (float tc in tcs)
            {
                house = PlaceFitted(PHouse, 0.60f, bg, "Kaisho_Omoya", KaishoPoly, sA, sAxis, sInw, sLen * tc,
                    new float[] { 1.5f, 2.0f }, 0.4f, faceRy, sb);
                if (house != null) { sb.AppendLine("Kaisho_Omoya shore tc=" + tc); break; }
            }
        }
        // --- 蔵: 頭部の北辺(南向き)・西辺(東向き)沿いの候補を試行。入るだけ置く(最大2棟) ---
        {
            int[] cedge = { 2, 2, 2, 3, 3, 5, 5, 5 };
            float[] ctc = { 0.30f, 0.55f, 0.75f, 0.13f, 0.17f, 0.36f, 0.44f, 0.30f };
            var placedK = new List<GameObject>();
            foreach (int pass in new int[] { 0, 1 })
            {
                for (int ci = 0; ci < cedge.Length && placedK.Count <= pass; ci++)
                {
                    int e = cedge[ci];
                    Vector2 eA = KaishoPoly[e], eB = KaishoPoly[(e + 1) % KaishoPoly.Length];
                    Vector2 eAxis = (eB - eA).normalized; float eLen = (eB - eA).magnitude;
                    Vector2 eInw = Inward(KaishoPoly, e);
                    float eRy = Mathf.Atan2(-eInw.x, -eInw.y) * Mathf.Rad2Deg;
                    var kura = PlaceFitted(PKura, ES, bg, "Kura_" + (placedK.Count + 1), KaishoPoly, eA, eAxis, eInw, eLen * ctc[ci],
                        new float[] { 1.2f }, 0.3f, eRy + 180f, sb);
                    if (kura == null) continue;
                    bool hit = house != null && OverlapSAT(FootprintCorners(kura), FootprintCorners(house), 0.3f);
                    foreach (var pk in placedK) if (!hit && OverlapSAT(FootprintCorners(kura), FootprintCorners(pk), 0.3f)) hit = true;
                    if (hit) { sb.AppendLine("Kura cand e" + e + " tc=" + ctc[ci] + " collision"); UnityEngine.Object.DestroyImmediate(kura); continue; }
                    sb.AppendLine("Kura_" + (placedK.Count + 1) + " e" + e + " tc=" + ctc[ci] + " placed");
                    placedK.Add(kura);
                }
            }
            sb.AppendLine("kura count=" + placedK.Count);
        }
        // --- 堀口主屋: 0.8→0.7倍・広い位置グリッド ---
        if (hg.Find("Omoya") == null)
        {
            Vector2 fA = HoriguchiPoly[0], fB = HoriguchiPoly[1];
            Vector2 fAxis = (fB - fA).normalized; float fLen = (fB - fA).magnitude;
            Vector2 fInw = Inward(HoriguchiPoly, 0);
            float fRy = Mathf.Atan2(-fInw.x, -fInw.y) * Mathf.Rad2Deg;
            float[] scales = { 0.8f, 0.7f };
            float[] tcs = { 0.50f, 0.42f, 0.58f, 0.35f, 0.65f };
            GameObject got = null;
            foreach (float sc in scales)
            {
                foreach (float tc in tcs)
                {
                    got = PlaceFitted(PSmallHouse, sc, hg, "Omoya", HoriguchiPoly, fA, fAxis, fInw, fLen * tc,
                        new float[] { 2.5f, 2.0f, 1.5f }, 0.3f, fRy, sb);
                    if (got != null) { sb.AppendLine("Omoya sc=" + sc + " tc=" + tc); break; }
                }
                if (got != null) break;
            }
        }
        // --- 筵干し場(修正版Inwardで) ---
        if (dg.childCount == 0)
        {
            Vector2 e5A = KaishoPoly[5], e5B = KaishoPoly[6];
            Vector2 e5Axis = (e5B - e5A).normalized;
            Vector2 e5Inw = Inward(KaishoPoly, 5);
            float mRy = Mathf.Atan2(e5Axis.x, e5Axis.y) * Mathf.Rad2Deg;
            int mats = 0;
            for (int row = 0; row < 2; row++)
                for (float tt = 2.5f; tt < 19f; tt += 2.4f)
                {
                    Vector2 p = e5A + e5Axis * tt + e5Inw * (2.5f + row * 2.0f);
                    if (!EdoGeom.PIP(KaishoPoly, p)) continue;
                    if (Ground(p.x, p.y) < 9.2f) continue;
                    var m = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    m.name = "Mushiro_" + mats; m.transform.SetParent(dg, false);
                    m.transform.localScale = new Vector3(1.75f, 0.05f, 0.92f);
                    m.transform.position = new Vector3(p.x, Ground(p.x, p.y) + 0.06f, p.y);
                    m.transform.rotation = Quaternion.Euler(0, mRy + ((float)rnd.NextDouble() * 8f - 4f), 0);
                    m.GetComponent<Renderer>().sharedMaterial = mushiroM;
                    Undo.RegisterCreatedObjectUndo(m, "mushiro");
                    mats++;
                }
            sb.AppendLine("mushiro=" + mats);
        }
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }

    // ---------- Stage 2: splat (区画内の地面) ----------
    public static string Stage2_Splat()
    {
        var t = EdoTamachiBuilder.T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -645, x1 = -555, z0 = 555, z1 = 665;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A2 = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                float noise = Mathf.PerlinNoise(wx * 0.13f, wz * 0.13f);
                float bare, grass, dirt;
                if (EdoGeom.PIP(MachiyaPoly, p) || EdoGeom.PIP(HoriguchiPoly, p))
                {   // 町屋・屋敷: 踏み固め土
                    bare = Mathf.Lerp(0.42f, 0.60f, noise); grass = 0.08f; dirt = 1f - bare - grass;
                }
                else if (EdoGeom.PIP(AzukariPoly, p))
                {   // 預り明地: 草
                    grass = Mathf.Lerp(0.45f, 0.65f, noise); bare = 0.10f; dirt = 1f - grass - bare;
                }
                else if (EdoGeom.PIP(KaishoPoly, p))
                {   // 会所: 北の庭は土、南の帯は草混じり
                    if (wz > 626f) { bare = Mathf.Lerp(0.40f, 0.55f, noise); grass = 0.10f; dirt = 1f - bare - grass; }
                    else { grass = Mathf.Lerp(0.30f, 0.50f, noise); bare = 0.22f; dirt = 1f - grass - bare; }
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
