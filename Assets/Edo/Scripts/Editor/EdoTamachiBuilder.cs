// 赤坂田町一〜五丁目 (2026-08-09)
// 【考証(同日Web調査: 文政町方書上(日本歴史地名大系抄録)/港区史通史編近世/CODH 9-012,19,25,27,29)】
//   ・寛永13-15年(1636-38)、南伝馬町の伝馬役助成地として溜池端の田地を町割り(「田」町)。
//   ・一〜四丁目=堀端通の西側だけの片側町(東は土手明地=紺屋・合羽屋の物干場拝借地と桐畑)。
//     五丁目のみ「道に囲まれた両面の町屋」。各丁 南北60間×裏行18間(五丁目71間×24/18間)。
//   ・表店は間口5間基準。家数: 二47/三72/四109(店借82=裏長屋密集)。南(赤坂御門から遠い方)ほど
//     さびれる、の記録(市川家文書)。※本実装の並びでは一丁目が北(御門寄り)。
//   ・業種: 紺屋・合羽屋・髪結床・床店・薬種店など小店。
//   ・設備: 自身番屋=二・四丁目 / 髪結床番屋=二・四丁目 / 三丁目稲荷 / 西行稲荷(四丁目自身番裏) /
//     成満寺(二丁目内) / 三〜四丁目間に床店列(幅1間×50間) / 二〜三丁目間に石橋(7尺×2間)。
//     木戸・高札は記録未確認→置かない。
//   ・裏長屋は専用アセットが無いため kidobanya(木造小屋)連結で表現【スタンドイン】。
//   ・桐畑の桐も専用アセット無し→夏緑の広葉樹(Sakura_Summer)で代用【スタンドイン】。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoTamachiBuilder
{
    const float ES = 1.818f;
    const string PShop01 = EdoAssets.Eg.Shop01;
    const string PShop02 = EdoAssets.Eg.Shop02;
    const string PSmallHouse = EdoAssets.VK.SmallHouse;
    const string PHouse = EdoAssets.VK.House;
    const string PBanya = EdoAssets.Eg.Kidobanya;
    const string PJishinban = EdoAssets.Eg.Jishinban;
    const string PKabukimon = EdoAssets.Eg.Kabukimon;

    public class Cho
    {
        public string group, label;
        public Vector2[] poly;      // 4点
        public int front;           // 東(堀端通)側の長辺 index (poly[i]->poly[i+1])
        public bool twoSided;       // 五丁目
        public bool jishinban, kamiyui, inari;
        public int nUra;            // 裏長屋の小屋数
        public string[] pattern;    // 表店の並び
    }

    // ⚠ poly の正典 = docs/Sashizu/parcels.json(CLAUDE.md 規則10 / 2026-08-26 ユーザー裁定で json採用)
    public static Cho[] Chos = new Cho[]
    {
        new Cho{ group="Edo_Tamachi_5", label="赤坂田町五丁目(両面町屋・71間)",
            poly=EdoParcels.Get("tamachi_chos_0"),
            front=3, twoSided=true, jishinban=false, kamiyui=false, inari=false, nUra=8,
            pattern=new[]{"S2","S1","S2","SH","S2","S1","S2","S2","S1"} },
        new Cho{ group="Edo_Tamachi_4", label="赤坂田町四丁目(店借82/109=裏店密集)",
            poly=EdoParcels.Get("tamachi_chos_1"),
            front=1, twoSided=false, jishinban=true, kamiyui=true, inari=true, nUra=14, // inari=西行稲荷(自身番裏)
            pattern=new[]{"S1","S2","S1","S2","S1","S1","S2","S1","S2","S1"} },
        new Cho{ group="Edo_Tamachi_3", label="赤坂田町三丁目(72軒・三丁目稲荷)",
            poly=EdoParcels.Get("tamachi_chos_2"),
            front=1, twoSided=false, jishinban=false, kamiyui=false, inari=true, nUra=10,
            pattern=new[]{"S2","S1","S2","S2","S1","SH","S2","S1"} },
        new Cho{ group="Edo_Tamachi_2", label="赤坂田町二丁目(47軒・自身番・成満寺)",
            poly=EdoParcels.Get("tamachi_chos_3"),
            front=3, twoSided=false, jishinban=true, kamiyui=true, inari=false, nUra=6,
            pattern=new[]{"SH","S2","S2","S1","S2","SH","S2"} },
        new Cho{ group="Edo_Tamachi_1", label="赤坂田町一丁目(赤坂御門寄り・地主家持の堅い町並)",
            poly=EdoParcels.Get("tamachi_chos_4"),
            front=2, twoSided=false, jishinban=false, kamiyui=false, inari=false, nUra=5,
            pattern=new[]{"SH","S2","S2","SH","S2","S1","S2"} },
    };

    public static Terrain T() { return EdoTameikeKitaBuilder.T(); }
    public static float Ground(float x, float z) { return EdoBuild.Ground(x, z); }
    static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
        EdoYashikiPrefab.EnsureEditable(r);   // ★ プレハブ化済みなら解く(でないと組み替えが黙って失敗する)
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
    static Material Mat(string name, string tex)
    {
        string mp = EdoAssets.Own.Mat(name);
        var exist = AssetDatabase.LoadAssetAtPath<Material>(mp);
        if (exist != null) return exist;
        var m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(tex));
        m.SetFloat("_Smoothness", 0.1f);
        AssetDatabase.CreateAsset(m, mp);
        return m;
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
    // バウンズ合わせ配置: 前面(outw側)を frontLine に、走り中心を目標tに、接地
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
        return go;
    }

    // ---------- Stage 1: 全丁の町並み ----------
    public static string Stage1_Build()
    {
        var sb = new System.Text.StringBuilder();
        var mS1 = Mat("M_Shop01", EdoAssets.Eg.TexShop01);
        var mS2 = Mat("M_Shop02", EdoAssets.Eg.TexShop02);
        var mBanya = Mat("M_Kidobanya", EdoAssets.Eg.TexKidobanya);
        var mJishin = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MJishinban);
        foreach (var c in Chos)
        {
            var root = GameObject.Find(c.group);
            if (root != null && root.transform.Find("Row") != null) { sb.AppendLine("SKIP " + c.group); continue; }
            var rowG = Group(c.group, "Row");
            var uraG = Group(c.group, "Ura");
            var propG = Group(c.group, "Props");
            var rnd = new System.Random(c.group.GetHashCode());
            int N = c.poly.Length;
            Vector2 A = c.poly[c.front], B = c.poly[(c.front + 1) % N];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            Vector2 inw = new Vector2(-axis.y, axis.x);
            if (!EdoGeom.PIP(c.poly, A + axis * (len * 0.5f) + inw * 6f)) inw = -inw;
            float ryFace = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg;
            // --- 表店列 (東=堀端通向き) ---
            int made = 0; float tcur = 1.0f; int pi = 0;
            // 成満寺(二丁目): 中央に間口12mの境内口を空ける
            float templeT = c.group.EndsWith("_2") ? len * 0.52f : -999f;
            while (true)
            {
                string kind = c.pattern[pi % c.pattern.Length]; pi++;
                float wLot; string path; float sc; Material mat = null;
                if (kind == "SH") { path = PSmallHouse; wLot = 15.0f; sc = 1f; }
                else if (kind == "S2") { path = PShop02; wLot = 7.4f; sc = ES; mat = mS2; }
                else { path = PShop01; wLot = 5.2f; sc = ES; mat = mS1; }
                if (tcur + wLot > len - 1.0f) break;
                if (templeT > 0 && tcur + wLot > templeT - 7f && tcur < templeT + 7f) { tcur = templeT + 7f; continue; }
                float jitterRy = ((float)rnd.NextDouble() * 2f - 1f);
                PlaceFront(path, sc, mat, rowG, kind + "_" + made, A, axis, inw, tcur + wLot * 0.5f, 0.6f, ryFace + jitterRy);
                made++;
                tcur += wLot + 0.3f;
            }
            sb.AppendLine(c.group + " 表店=" + made);
            // --- 五丁目: 西面にも表店 ---
            if (c.twoSided)
            {
                int wf = (c.front + 2) % N;
                Vector2 A2 = c.poly[wf], B2 = c.poly[(wf + 1) % N];
                Vector2 axis2 = (B2 - A2).normalized; float len2 = (B2 - A2).magnitude;
                Vector2 inw2 = new Vector2(-axis2.y, axis2.x);
                if (!EdoGeom.PIP(c.poly, A2 + axis2 * (len2 * 0.5f) + inw2 * 6f)) inw2 = -inw2;
                float ry2 = Mathf.Atan2(-inw2.x, -inw2.y) * Mathf.Rad2Deg;
                float t2 = 1.0f; int m2 = 0; pi = 0;
                while (true)
                {
                    string kind = c.pattern[(pi + 3) % c.pattern.Length]; pi++;
                    float wLot; string path; float sc; Material mat = null;
                    if (kind == "SH") { path = PSmallHouse; wLot = 15.0f; sc = 1f; }
                    else if (kind == "S2") { path = PShop02; wLot = 7.4f; sc = ES; mat = mS2; }
                    else { path = PShop01; wLot = 5.2f; sc = ES; mat = mS1; }
                    if (t2 + wLot > len2 - 1.0f) break;
                    PlaceFront(path, sc, mat, rowG, "W" + kind + "_" + m2, A2, axis2, inw2, t2 + wLot * 0.5f, 0.6f, ry2 + ((float)rnd.NextDouble() * 2f - 1f));
                    m2++;
                    t2 += wLot + 0.3f;
                }
                sb.AppendLine(c.group + " 西面=" + m2);
            }
            // --- 裏長屋 (kidobanya 連結、路地向き=東) ---
            {
                float uraDepth = c.twoSided ? 13f : 20f; // 前面から路地を挟んだ位置
                int per = Mathf.Min(c.nUra, 7);
                int rows = Mathf.CeilToInt(c.nUra / (float)per);
                for (int r = 0; r < rows; r++)
                {
                    int cnt = Mathf.Min(per, c.nUra - r * per);
                    float rowLen = cnt * 5.15f;
                    float tStart = len * 0.5f - rowLen * 0.5f + (r % 2 == 0 ? -6f : 6f);
                    for (int k = 0; k < cnt; k++)
                    {
                        float tt = tStart + 5.15f * (k + 0.5f);
                        Vector2 p = A + axis * tt + inw * (uraDepth + r * 7.5f);
                        if (!EdoGeom.PIP(c.poly, p)) continue;
                        var hut = PlaceFront(PBanya, ES, mBanya, uraG, "Ura_" + r + "_" + k,
                            A, axis, inw, tt, uraDepth + r * 7.5f - 2.5f, ryFace);
                        // PlaceFront は前面基準なので位置はこのままで良い(路地=東向き)
                    }
                }
            }
            // --- 設備 ---
            float basePadT = 4.5f;
            if (c.jishinban)
            {   // 自身番屋: 表列の南端寄り・前面を通りへ
                var jb = PlaceFront(PJishinban, ES, null, propG, "Jishinban", A, axis, inw, basePadT, 0.2f, ryFace);
                if (mJishin != null) Assign(jb, mJishin);
                if (c.inari && c.group.EndsWith("_4"))
                {   // 西行稲荷: 自身番屋の裏の明地
                    Vector2 ip = A + axis * basePadT + inw * 12f;
                    Inari(propG, ip, ryFace);
                }
            }
            if (c.kamiyui)
            {   // 髪結床番屋: 自身番の隣の小屋
                var km = PlaceFront(PBanya, ES * 0.92f, mBanya, propG, "KamiyuiBanya", A, axis, inw, basePadT + 5.5f, 0.4f, ryFace);
            }
            if (c.inari && c.group.EndsWith("_3"))
            {   // 三丁目稲荷: 裏手
                Vector2 ip = A + axis * (len * 0.72f) + inw * 24f;
                if (EdoGeom.PIP(c.poly, ip)) Inari(propG, ip, ryFace);
            }
            // 井戸(裏路地)
            {
                Vector2 wp = A + axis * (len * 0.35f) + inw * 15f;
                if (EdoGeom.PIP(c.poly, wp)) Idobata(propG, wp);
            }
        }
        // --- 成満寺(二丁目・推定スタンドイン: 冠木門+本堂) ---
        {
            var c = Chos.First(x => x.group == "Edo_Tamachi_2");
            var propG = Group(c.group, "Props");
            int N = c.poly.Length;
            Vector2 A = c.poly[c.front], B = c.poly[(c.front + 1) % N];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            Vector2 inw = new Vector2(-axis.y, axis.x);
            if (!EdoGeom.PIP(c.poly, A + axis * (len * 0.5f) + inw * 6f)) inw = -inw;
            float ryFace = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg;
            float tt = len * 0.52f;
            var mon = PlaceFront(PKabukimon, ES, null, propG, "JoumanjiMon", A, axis, inw, tt, 0.5f, ryFace);
            var wood = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MKido);
            if (wood != null) Assign(mon, wood);
            PlaceFront(PHouse, 0.8f, null, propG, "Joumanji_Hondo", A, axis, inw, tt, 14f, ryFace);
        }
        // --- 床店列 (三〜四丁目間の普請方地) ---
        {
            var c4 = Chos.First(x => x.group == "Edo_Tamachi_4");
            var propG = Group("Edo_Tamachi_4", "Props");
            var mTd = Mat("M_Shop01", EdoAssets.Eg.TexShop01);
            int N = c4.poly.Length;
            Vector2 A = c4.poly[c4.front], B = c4.poly[(c4.front + 1) % N];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            Vector2 inw = new Vector2(-axis.y, axis.x);
            if (!EdoGeom.PIP(c4.poly, A + axis * (len * 0.5f) + inw * 6f)) inw = -inw;
            float ryFace = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg;
            for (int k = 0; k < 5; k++)
            {   // 四丁目北端の先(三丁目との間)に沿って小さな床店
                float tt = len + 2.5f + k * 5.2f;
                PlaceFront(PShop01, ES * 0.9f, mTd, propG, "Tokodana_" + k, A, axis, inw, tt, 0.4f, ryFace);
            }
        }
        // --- 石橋 (二〜三丁目間・下水渡り 7尺x2間) ---
        {
            var propG = Group("Edo_Tamachi_3", "Props");
            var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.58f, 0.58f, 0.55f);
            var slab = GameObject.CreatePrimitive(PrimitiveType.Cube);
            slab.name = "Ishibashi"; slab.transform.SetParent(propG, false);
            Vector2 pos = new Vector2(-750.5f, 926.0f); // 三丁目北端と二丁目南端の間、通り沿い
            float g = Ground(pos.x, pos.y);
            slab.transform.position = new Vector3(pos.x, g + 0.10f, pos.y);
            slab.transform.localScale = new Vector3(3.9f, 0.18f, 2.2f);
            slab.transform.rotation = Quaternion.Euler(0, 106f, 0);
            slab.GetComponent<Renderer>().sharedMaterial = stone;
            Undo.RegisterCreatedObjectUndo(slab, "ishibashi");
        }
        AssetDatabase.SaveAssets();
        return "built\n" + sb;
    }

    static void Inari(Transform parent, Vector2 pos, float ry)
    {
        float y = Ground(pos.x, pos.y);
        var g = new GameObject("Inari");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(pos.x, y, pos.y);
        g.transform.rotation = Quaternion.Euler(0, ry, 0);
        Undo.RegisterCreatedObjectUndo(g, "inari");
        var shu = new Material(Shader.Find("Universal Render Pipeline/Lit")); shu.color = new Color(0.78f, 0.15f, 0.08f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.30f, 0.18f);
        for (int i = 0; i < 2; i++)
        {
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "t_post" + i; post.transform.SetParent(g.transform, false);
            post.transform.localScale = new Vector3(0.16f, 1.1f, 0.16f);
            post.transform.localPosition = new Vector3(i == 0 ? -0.8f : 0.8f, 1.1f, -1.9f);
            post.GetComponent<Renderer>().sharedMaterial = shu;
        }
        var kasagi = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kasagi.name = "t_kasagi"; kasagi.transform.SetParent(g.transform, false);
        kasagi.transform.localScale = new Vector3(2.3f, 0.15f, 0.18f);
        kasagi.transform.localPosition = new Vector3(0, 2.2f, -1.9f);
        kasagi.GetComponent<Renderer>().sharedMaterial = shu;
        var kidan = GameObject.CreatePrimitive(PrimitiveType.Cube);
        kidan.name = "kidan"; kidan.transform.SetParent(g.transform, false);
        kidan.transform.localScale = new Vector3(1.3f, 0.35f, 1.1f);
        kidan.transform.localPosition = new Vector3(0, 0.17f, 0);
        kidan.GetComponent<Renderer>().sharedMaterial = stone;
        var hokora = GameObject.CreatePrimitive(PrimitiveType.Cube);
        hokora.name = "hokora"; hokora.transform.SetParent(g.transform, false);
        hokora.transform.localScale = new Vector3(0.8f, 0.8f, 0.7f);
        hokora.transform.localPosition = new Vector3(0, 0.75f, 0);
        hokora.GetComponent<Renderer>().sharedMaterial = wood;
        for (int i = 0; i < 2; i++)
        {
            var roof = GameObject.CreatePrimitive(PrimitiveType.Cube);
            roof.name = "roof" + i; roof.transform.SetParent(g.transform, false);
            roof.transform.localScale = new Vector3(1.05f, 0.05f, 0.65f);
            roof.transform.localPosition = new Vector3(0, 1.32f, i == 0 ? -0.24f : 0.24f);
            roof.transform.localEulerAngles = new Vector3(i == 0 ? -35 : 35, 0, 0);
            roof.GetComponent<Renderer>().sharedMaterial = wood;
        }
    }
    static void Idobata(Transform parent, Vector2 p)
    {
        var g = new GameObject("Idobata");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(p.x, Ground(p.x, p.y), p.y);
        var curb = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        curb.name = "curb"; curb.transform.SetParent(g.transform, false);
        curb.transform.localScale = new Vector3(1.2f, 0.35f, 1.2f);
        curb.transform.localPosition = new Vector3(0, 0.35f, 0);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        curb.GetComponent<Renderer>().sharedMaterial = stone;
        Undo.RegisterCreatedObjectUndo(g, "idobata");
    }

    // ---------- Stage 2: 対岸の物干場と桐畑(スタンドイン樹) ----------
    public static string Stage2_Bank()
    {
        var root = Group("Edo_Tamachi_Bank", "Monohoshi");
        var treeG = Group("Edo_Tamachi_Bank", "Kiribatake");
        var rnd = new System.Random(20260810);
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        string[] trees = {
            EdoAssets.JG.SakuraBig01,
            EdoAssets.JG.SakuraMid01,
            EdoAssets.JG.SakuraMid05 };
        int racks = 0, planted = 0;
        // 一〜四丁目の前の通りの東側バンド(道の先~汀線まで)に配置
        foreach (var c in Chos)
        {
            if (c.twoSided) continue; // 五丁目は対岸が別権利地(堀口・今津ほか)なので疎に
            int N = c.poly.Length;
            Vector2 A = c.poly[c.front], B = c.poly[(c.front + 1) % N];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            Vector2 inw = new Vector2(-axis.y, axis.x);
            if (!EdoGeom.PIP(c.poly, A + axis * (len * 0.5f) + inw * 6f)) inw = -inw;
            Vector2 outw = -inw; // 東=通り・土手側
            float ryRack = Mathf.Atan2(axis.x, axis.y) * Mathf.Rad2Deg;
            for (float tt = 6f; tt < len - 4f; tt += 16f)
            {
                // 通り幅~9mの先、水際手前まで
                for (float dd = 12f; dd <= 30f; dd += 5f)
                {
                    Vector2 p = A + axis * tt + outw * dd;
                    float gy = Ground(p.x, p.y);
                    if (gy < 7.0f || gy > 9.7f) continue;
                    if (rnd.NextDouble() < 0.45)
                    {   // 物干(2本柱+竿)
                        var g = new GameObject("Rack");
                        g.transform.SetParent(root, false);
                        g.transform.position = new Vector3(p.x, gy, p.y);
                        g.transform.rotation = Quaternion.Euler(0, ryRack + ((float)rnd.NextDouble() * 14f - 7f), 0);
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
                        Undo.RegisterCreatedObjectUndo(g, "rack");
                        racks++;
                    }
                    else if (rnd.NextDouble() < 0.5)
                    {   // 桐(代用樹)
                        var pa = AssetDatabase.LoadAssetAtPath<GameObject>(trees[rnd.Next(trees.Length)]);
                        var tr = (GameObject)PrefabUtility.InstantiatePrefab(pa);
                        tr.name = "Kiri_" + planted; tr.transform.SetParent(treeG, true);
                        tr.transform.position = new Vector3(p.x, gy - 0.05f, p.y);
                        tr.transform.rotation = Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
                        tr.transform.localScale = Vector3.one * (1.15f + 0.5f * (float)rnd.NextDouble());
                        planted++;
                    }
                    break; // 各(tt)で1つだけ
                }
            }
        }
        return "bank racks=" + racks + " trees=" + planted;
    }

    // ---------- Stage 3: splat (町地=土 / 通り=裸地 / 土手=草) ----------
    public static string Stage3_Splat()
    {
        var t = T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -890, x1 = -560, z0 = 520, z1 = 1195;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A2 = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        // 通りバンド: 各丁の front 辺から外(東)へ 0..9m
        foreach (var c in Chos)
        {
            int N = c.poly.Length;
            Vector2 A = c.poly[c.front], B = c.poly[(c.front + 1) % N];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            Vector2 inw = new Vector2(-axis.y, axis.x);
            if (!EdoGeom.PIP(c.poly, A + axis * (len * 0.5f) + inw * 6f)) inw = -inw;
            Vector2 outw = -inw;
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                    float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                    var p = new Vector2(wx, wz);
                    float tpar = Vector2.Dot(p - A, axis);
                    float dOut = Vector2.Dot(p - A, outw);
                    float bare, grass, dirt;
                    float noise = Mathf.PerlinNoise(wx * 0.13f, wz * 0.13f);
                    if (EdoGeom.PIP(c.poly, p))
                    {   // 町地: 踏み固め土
                        bare = Mathf.Lerp(0.42f, 0.60f, noise); grass = 0.08f; dirt = 1f - bare - grass;
                    }
                    else if (tpar > -6f && tpar < len + 6f && dOut > 0f && dOut < 9f)
                    {   // 堀端通
                        bare = 0.78f; grass = 0.05f; dirt = 0.17f;
                    }
                    else if (tpar > -4f && tpar < len + 4f && dOut >= 9f && dOut < 34f && !c.twoSided)
                    {   // 土手明地(物干場・桐畑): 草
                        float gy = Ground(wx, wz);
                        if (gy < 6.7f) continue;
                        grass = Mathf.Lerp(0.5f, 0.7f, noise); bare = 0.08f; dirt = 1f - grass - bare;
                    }
                    else continue;
                    float sum = bare + grass + dirt;
                    for (int l = 0; l < L; l++) A2[zz, xx, l] = 0;
                    A2[zz, xx, 0] = dirt / sum; A2[zz, xx, 1] = grass / sum; A2[zz, xx, 2] = bare / sum;
                    changed++;
                }
        }
        td.SetAlphamaps(ix0, iz0, A2);
        return "tamachi splat cells=" + changed;
    }
}
