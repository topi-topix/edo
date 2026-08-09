// 溜池端北の飛び代地2町(麻布網代町代地・元赤坂町代地)+成満寺(時の鐘) (2026-08-09)
// 【典拠】
//  ・区画=ユーザー下書き(スケッチ 赤2/黄2/水色1)。切絵図の文字判読はユーザー:
//    赤=麻布網代町(代地) / 黄=元赤坂町代地 / 水色=成満寺時の鐘
//  ・元赤坂町代地: 尾張屋版赤坂絵図に2筆(CODH 9-013/9-014)=黄2区画と一致。元赤坂町=赤坂最古の町
//    (天正年中起立・元は一ツ木村)、寛永14年(1637)赤坂御門造成のため御門外(現元赤坂1丁目)へ移転
//    (港区旧町名由来板)。溜池端は飛び代地。坪数・家数の史料未取得→町屋構成は一般類型【推定スタンドイン】。
//  ・麻布網代町: 享保8年(1723)芝新網町二丁目の代地として起立→沼地のため享保17年(1732)麻布坂下町西へ
//    さらに代地、「網」「代」を採り「網代町(あみしろ)」と改称(日本歴史地名大系/江戸町巡り)。
//    溜池端代地はCODH地名抽出に無し→ユーザーの絵図判読を正とする。構成は一般類型【推定スタンドイン】。
//  ・成満寺: 不動山無量院成満寺・真宗大谷派(浄土真宗)。元和元年(1615)八丁堀創建→寛永12年田町→
//    寛文元年三田聖坂→寛文12年(1672)赤坂田町二丁目(田町通りと三筋通りの間、現赤坂3丁目)。
//    時の鐘=本石町に次ぐ江戸の「二番鐘」。延宝5年(1677)6月18日寺社奉行許可・同年8月28日撞初(寺伝石板)。
//    戦後八王子→1960年多摩市連光寺へ移転、鐘は現存。伽藍(本堂=Big House/庫裏=Small House/
//    鐘楼=自作プロシージャル宝形屋根)は【推定スタンドイン】。
//  ・木戸・高札は田町本体同様に史料未確認のため置かない。町境(赤/黄の間)に番小屋のみ【推定】。
// 地形は現地形に従い造成しない([[terrain-follows-present-day]])。
// Stage0で撤去: 区画内の桐畑・物干(Edo_Tamachi_Bank)、水色区画に重なる二丁目表店(Edo_Tamachi_2/Row)、
//               旧成満寺スタンドイン(Edo_Tamachi_2/Props/JoumanjiMon・Joumanji_Hondo)
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoDaichiKitaBuilder
{
    const float ES = 1.818f;
    const string PShop01 = "Assets/edogoyomi/es_shop01/shop01.obj";
    const string PShop02 = "Assets/edogoyomi/es_shop02/shop02.obj";
    const string PSmallHouse = "Assets/Japanese Village Kit/Prefabs/Small House.prefab";
    const string PBigHouse = "Assets/Japanese Village Kit/Prefabs/Big House.prefab";
    const string PBanya = "Assets/edogoyomi/es_kidobanya/kidobanya.obj";
    const string PKabukimon = "Assets/edogoyomi/es_kabukimon/kabukimon.obj";
    const string PPineMid = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Mid_Green_01.prefab";
    const string PPineBig = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_02.prefab";

    // ---- 下書きポリゴン(スケッチ世界座標XZ)。各strip: [0]->[1]=西長辺(堀端通側=表) ----
    static readonly Vector2[] R1 = { new Vector2(-664.93f,721.86f), new Vector2(-691.56f,792.63f), new Vector2(-678.59f,797.53f), new Vector2(-651.27f,725.71f) };
    static readonly Vector2[] R2 = { new Vector2(-696.49f,802.52f), new Vector2(-709.43f,839.37f), new Vector2(-693.91f,843.90f), new Vector2(-681.62f,807.05f) };
    static readonly Vector2[] Y1 = { new Vector2(-712.66f,849.07f), new Vector2(-739.81f,918.90f), new Vector2(-723.65f,924.07f), new Vector2(-697.14f,852.31f) };
    static readonly Vector2[] Y2 = { new Vector2(-743.02f,930.13f), new Vector2(-778.85f,1021.86f), new Vector2(-767.38f,1025.68f), new Vector2(-730.59f,932.04f) };
    // 成満寺: C2->C3(東辺)が田町通りに平行=山門側
    static readonly Vector2[] JM = { new Vector2(-825.19f,1019.95f), new Vector2(-816.59f,996.54f), new Vector2(-786.97f,1008.00f), new Vector2(-797.00f,1033.32f) };

    static float Ground(float x, float z) { return EdoTamachiBuilder.Ground(x, z); }

    static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) inside = !inside;
        return inside;
    }
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
    static Bounds RB(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }
    // 頂点射影で前面を正確に辺A+inw*frontInsetへ合わせる配置(EdoTamachi5EastBuilder.PlaceFrontVと同式)
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
        var b2 = RB(go);
        float g = Ground(b2.center.x, b2.center.z);
        go.transform.position += new Vector3(0, (g - 0.10f) - b2.min.y, 0);
        Undo.RegisterCreatedObjectUndo(go, "place " + name);
        return go;
    }
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
        return new Vector2[] { r * rMin + f * fMin, r * rMin + f * fMax, r * rMax + f * fMin, r * rMax + f * fMax };
    }
    static GameObject PlaceFitted(string path, float sc, Material mat, Transform parent, string name, Vector2[] poly,
        Vector2 A, Vector2 axis, Vector2 inw, float tCenter, float[] insets, float margin, float ry,
        System.Text.StringBuilder log)
    {
        foreach (float inset in insets)
        {
            var go = PlaceFrontV(path, sc, mat, parent, name, A, axis, inw, tCenter, inset, ry);
            bool ok = true; float worst = float.MaxValue;
            foreach (var c in FootprintCorners(go))
            {
                float dd = DistToPolyEdge(poly, c);
                if (!PIP(poly, c)) { ok = false; worst = Mathf.Min(worst, -dd); continue; }
                if (dd < worst) worst = dd;
                if (dd < margin) ok = false;
            }
            log.AppendLine(name + " sc=" + sc + " inset=" + inset + " worst=" + worst.ToString("F2") + (ok ? " OK" : " NG"));
            if (ok) return go;
            Object.DestroyImmediate(go);
        }
        return null;
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

    // ---------- Stage 0: 区画内の既存生成物を撤去 ----------
    public static string Stage0_Clear()
    {
        var sb = new System.Text.StringBuilder();
        var strips = new Vector2[][] { R1, R2, Y1, Y2 };
        var kill = new List<GameObject>();
        // 1) 桐畑・物干(Edo_Tamachi_Bank): 中心が区画内 or 縁1.2m以内
        var bank = GameObject.Find("Edo_Tamachi_Bank");
        if (bank != null)
            foreach (var sub in new[] { "Kiribatake", "Monohoshi" })
            {
                var g = bank.transform.Find(sub);
                if (g == null) continue;
                foreach (Transform c in g)
                {
                    var rs = c.GetComponentsInChildren<Renderer>();
                    if (rs.Length == 0) continue;
                    var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    var p = new Vector2(b.center.x, b.center.z);
                    foreach (var poly in strips)
                        if (PIP(poly, p) || DistToPolyEdge(poly, p) < 1.2f) { kill.Add(c.gameObject); break; }
                }
            }
        int nBank = kill.Count;
        // 2) 成満寺区画に重なる二丁目表店(OBB隅または中心が区画内)
        var row = GameObject.Find("Edo_Tamachi_2");
        if (row != null)
        {
            var rowG = row.transform.Find("Row");
            if (rowG != null)
                foreach (Transform c in rowG)
                {
                    bool hit = false;
                    var rs = c.GetComponentsInChildren<Renderer>();
                    if (rs.Length == 0) continue;
                    var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    if (PIP(JM, new Vector2(b.center.x, b.center.z))) hit = true;
                    if (!hit) foreach (var q in FootprintCorners(c.gameObject)) if (PIP(JM, q)) { hit = true; break; }
                    if (hit) kill.Add(c.gameObject);
                }
            // 3) 旧成満寺スタンドイン
            var props = row.transform.Find("Props");
            if (props != null)
                foreach (var nm in new[] { "JoumanjiMon", "Joumanji_Hondo" })
                {
                    var t = props.Find(nm);
                    if (t != null) kill.Add(t.gameObject);
                }
        }
        sb.AppendLine("bank(桐畑・物干)=" + nBank + " / 二丁目Row+旧スタンドイン=" + (kill.Count - nBank));
        foreach (var k in kill) Undo.DestroyObjectImmediate(k);
        sb.AppendLine("removed total=" + kill.Count);
        return sb.ToString();
    }

    // ---------- Stage 1: 代地2町の町屋 ----------
    public static string Stage1_Machiya()
    {
        var sb = new System.Text.StringBuilder();
        var mS1 = AssetDatabase.LoadAssetAtPath<Material>("Assets/Edo/Materials/M_Shop01.mat");
        var mS2 = AssetDatabase.LoadAssetAtPath<Material>("Assets/Edo/Materials/M_Shop02.mat");
        var mBanya = AssetDatabase.LoadAssetAtPath<Material>("Assets/Edo/Materials/M_Kidobanya.mat");
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);

        // (root, sub, poly, pattern, seed)
        var defs = new[] {
            new { root = "Edo_Daichi_AzabuAmishiro", sub = "Kita",    poly = R2, pat = new[]{ "S1","S2","S1","S1","S2" },                         seed = 9301 },
            new { root = "Edo_Daichi_AzabuAmishiro", sub = "Minami",  poly = R1, pat = new[]{ "S2","S1","SH","S1","S2","S1","S2","S1","S1" },     seed = 9302 },
            new { root = "Edo_Daichi_MotoAkasaka",   sub = "Minami",  poly = Y1, pat = new[]{ "S1","S2","S1","S2","SH","S2","S1","S2","S1" },     seed = 9303 },
            new { root = "Edo_Daichi_MotoAkasaka",   sub = "Kita",    poly = Y2, pat = new[]{ "S2","S1","S2","S1","S2","SH","S1","S2","S2","S1","S2" }, seed = 9304 },
        };
        foreach (var d in defs)
        {
            var exist = GameObject.Find(d.root);
            if (exist != null && exist.transform.Find(d.sub) != null) { sb.AppendLine("SKIP " + d.root + "/" + d.sub); continue; }
            var g = Group(d.root, d.sub);
            var rnd = new System.Random(d.seed);
            Vector2 A = d.poly[0], B = d.poly[1];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            Vector2 inw = Inward(d.poly, 0);
            float ryFace = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg; // 前面=西(堀端通)
            float t = 0.8f; int made = 0; int pi = 0;
            while (true)
            {
                string kind = d.pat[pi % d.pat.Length]; pi++;
                float wLot; string path; float sc; Material mat = null;
                if (kind == "SH") { path = PSmallHouse; wLot = 15.0f; sc = 1f; }
                else if (kind == "S2") { path = PShop02; wLot = 7.4f; sc = ES; mat = mS2; }
                else { path = PShop01; wLot = 5.2f; sc = ES; mat = mS1; }
                if (t + wLot > len - 0.8f) break;
                PlaceFrontV(path, sc, mat, g, kind + "_" + made, A, axis, inw, t + wLot * 0.5f, 0.5f,
                    ryFace + ((float)rnd.NextDouble() * 2f - 1f));
                made++; t += wLot + 0.35f;
            }
            // 裏(溜池側): 杭柵+物干+井戸
            StakeFence(g, d.poly[2], d.poly[3], "FenceUra", wood);
            Vector2 backAxis = (d.poly[2] - d.poly[3]).normalized; // 走りは表と同方向でなくてよい
            int racks = 0;
            for (float tt = 5f; tt < len - 4f; tt += 10f)
            {
                Vector2 p = A + axis * tt + inw * (9.0f + 2.0f * (float)rnd.NextDouble());
                if (!PIP(d.poly, p)) continue;
                if (Ground(p.x, p.y) < 7.2f) continue;
                Rack(g, p, ryFace + 90f + ((float)rnd.NextDouble() * 12f - 6f), wood, "Rack_" + racks);
                racks++;
            }
            Vector2 wp = A + axis * (len * 0.45f) + inw * 7.0f;
            if (PIP(d.poly, wp)) Well(g, wp, stone);
            sb.AppendLine(d.root + "/" + d.sub + " 表店=" + made + " 物干=" + racks);
        }
        // 町境(R2北端とY1南端の間)の番小屋【推定】: 麻布網代町代地側の北端に寄せる
        var borderRoot = GameObject.Find("Edo_Daichi_AzabuAmishiro");
        if (borderRoot != null && borderRoot.transform.Find("Sakaibanya") == null)
        {
            var g = Group("Edo_Daichi_AzabuAmishiro", "Sakaibanya");
            Vector2 A = R2[1], e = (R2[1] - R2[0]).normalized;
            Vector2 inw = Inward(R2, 0);
            float ry = Mathf.Atan2(-inw.x, -inw.y) * Mathf.Rad2Deg;
            PlaceFrontV(PBanya, ES * 0.92f, mBanya, g, "Banya", R2[0], e, inw, (R2[1] - R2[0]).magnitude - 3.2f, 0.6f, ry);
            sb.AppendLine("Sakaibanya built");
        }
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }

    // ---------- Stage 2: 成満寺境内 ----------
    public static string Stage2_Jomanji()
    {
        var sb = new System.Text.StringBuilder();
        var root = GameObject.Find("Edo_Jomanji");
        if (root != null && root.transform.Find("Buildings") != null) return "SKIP Edo_Jomanji";
        var mKido = AssetDatabase.LoadAssetAtPath<Material>("Assets/Edo/Materials/M_Kido.mat");
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.35f, 0.26f, 0.17f);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        var tile = new Material(Shader.Find("Universal Render Pipeline/Lit")); tile.color = new Color(0.28f, 0.29f, 0.32f);
        var bronze = new Material(Shader.Find("Universal Render Pipeline/Lit")); bronze.color = new Color(0.18f, 0.17f, 0.14f);
        bronze.SetFloat("_Smoothness", 0.55f);

        // 山門(東辺=田町通り側 C2->C3、中央) : kabukimon【スタンドイン】
        Vector2 gA = JM[2], gB = JM[3];
        Vector2 gAxis = (gB - gA).normalized; float gLen = (gB - gA).magnitude;
        Vector2 gInw = Inward(JM, 2);
        float gRy = Mathf.Atan2(-gInw.x, -gInw.y) * Mathf.Rad2Deg;
        float gateT = gLen * 0.5f;
        Vector2 gateC = gA + gAxis * gateT;
        var gGate = Group("Edo_Jomanji", "Mon");
        var mon = PlaceFrontV(PKabukimon, ES, null, gGate, "Sanmon", gA, gAxis, gInw, gateT, 0.3f, gRy);
        if (mKido != null) Assign(mon, mKido);

        // 囲い: 全周を板塀(DobeiRun)、東辺は山門の間口を開ける
        var kak = Group("Edo_Jomanji", "Kakoi");
        for (int i = 0; i < 4; i++)
        {
            Vector2 a = JM[i], b = JM[(i + 1) % 4];
            Vector2 outw = -Inward(JM, i);
            if (i == 2) EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, gateC, 2.6f);
            else EdoNishiTameikeBuilder.DobeiRun(kak, a, b, outw, "Hei_" + i, true, 0, Vector2.zero, -1);
        }

        // 本堂: Big House【スタンドイン】東面(山門正対)。入らなければ縮小
        var bg = Group("Edo_Jomanji", "Buildings");
        GameObject hondo = null;
        foreach (float sc in new[] { 0.62f, 0.55f, 0.48f })
        {
            hondo = PlaceFitted(PBigHouse, sc, null, bg, "Hondo", JM, gA, gAxis, gInw, gateT,
                new float[] { 12f, 10.5f, 9f }, 1.0f, gRy, sb);
            if (hondo != null) break;
        }
        // 庫裏: Small House【スタンドイン】北辺沿い・南面
        Vector2 nA = JM[3], nB = JM[0];
        Vector2 nAxis = (nB - nA).normalized; float nLen = (nB - nA).magnitude;
        Vector2 nInw = Inward(JM, 3);
        float nRy = Mathf.Atan2(nInw.x, nInw.y) * Mathf.Rad2Deg; // 前面=境内側(南)
        var kuri = PlaceFitted(PSmallHouse, 0.9f, null, bg, "Kuri", JM, nA, nAxis, nInw, nLen * 0.35f,
            new float[] { 1.5f, 2.5f, 3.5f }, 0.6f, nRy, sb);
        if (kuri == null) sb.AppendLine("Kuri FAILED");

        // 鐘楼(時の鐘): プロシージャル(石壇+四本柱+宝形屋根+梵鐘)。山門の南脇
        var shoro = Group("Edo_Jomanji", "Shoro");
        Vector2 sp = gA + gAxis * (gLen * 0.18f) + gInw * 5.2f;
        if (!PIP(JM, sp)) sp = gateC + gInw * 5.2f - gAxis * 4.5f;
        float sg = Ground(sp.x, sp.y);
        float shoroRy = gRy;
        var srot = Quaternion.Euler(0, shoroRy, 0);
        System.Func<Vector3, Vector3> L = lp => new Vector3(sp.x, sg, sp.y) + srot * lp;
        // 石壇
        var dan = GameObject.CreatePrimitive(PrimitiveType.Cube);
        dan.name = "Kidan"; dan.transform.SetParent(shoro, false);
        dan.transform.localScale = new Vector3(4.0f, 0.55f, 4.0f);
        dan.transform.position = L(new Vector3(0, 0.22f, 0));
        dan.transform.rotation = srot;
        dan.GetComponent<Renderer>().sharedMaterial = stone;
        Undo.RegisterCreatedObjectUndo(dan, "shoro");
        // 四本柱+頭貫
        for (int ix = -1; ix <= 1; ix += 2)
            for (int iz = -1; iz <= 1; iz += 2)
            {
                var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                post.name = "Hashira"; post.transform.SetParent(shoro, false);
                post.transform.localScale = new Vector3(0.26f, 1.7f, 0.26f);
                post.transform.position = L(new Vector3(1.25f * ix, 0.5f + 1.7f, 1.25f * iz));
                post.transform.rotation = srot;
                post.GetComponent<Renderer>().sharedMaterial = wood;
                Undo.RegisterCreatedObjectUndo(post, "shoro");
            }
        for (int k = 0; k < 4; k++)
        {
            var beam = GameObject.CreatePrimitive(PrimitiveType.Cube);
            beam.name = "Nuki"; beam.transform.SetParent(shoro, false);
            beam.transform.localScale = new Vector3(2.9f, 0.20f, 0.14f);
            float a = 90f * k;
            beam.transform.position = L(Quaternion.Euler(0, a, 0) * new Vector3(0, 3.65f, 1.25f));
            beam.transform.rotation = srot * Quaternion.Euler(0, a, 0);
            beam.GetComponent<Renderer>().sharedMaterial = wood;
            Undo.RegisterCreatedObjectUndo(beam, "shoro");
        }
        // 宝形屋根(自作メッシュ・面ごとに頂点を分けフラットシェーディング=法線ゼロ事故回避)
        {
            var roofGo = new GameObject("Yane", typeof(MeshFilter), typeof(MeshRenderer));
            roofGo.transform.SetParent(shoro, false);
            roofGo.transform.position = L(new Vector3(0, 4.0f, 0));
            roofGo.transform.rotation = srot;
            float e = 2.85f, h = 1.55f, th = 0.12f;
            var v = new List<Vector3>(); var tri = new List<int>();
            Vector3 apex = new Vector3(0, h, 0);
            Vector3[] c = { new Vector3(-e,0,-e), new Vector3(-e,0,e), new Vector3(e,0,e), new Vector3(e,0,-e) };
            for (int k = 0; k < 4; k++)
            {   // 上面4枚
                int b0 = v.Count;
                v.Add(apex); v.Add(c[k]); v.Add(c[(k + 1) % 4]);
                tri.Add(b0); tri.Add(b0 + 2); tri.Add(b0 + 1);
                // 軒裏(下面)
                int b1 = v.Count;
                Vector3 apexD = new Vector3(0, h - th, 0);
                v.Add(apexD); v.Add(c[k] - new Vector3(0, th, 0)); v.Add(c[(k + 1) % 4] - new Vector3(0, th, 0));
                tri.Add(b1); tri.Add(b1 + 1); tri.Add(b1 + 2);
            }
            var mesh = new Mesh(); mesh.SetVertices(v); mesh.SetTriangles(tri, 0);
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            roofGo.GetComponent<MeshFilter>().sharedMesh = mesh;
            roofGo.GetComponent<MeshRenderer>().sharedMaterial = tile;
            Undo.RegisterCreatedObjectUndo(roofGo, "shoro");
        }
        // 梵鐘(吊り梁+鐘身+笠+撞木)
        {
            var beam = GameObject.CreatePrimitive(PrimitiveType.Cube);
            beam.name = "Tsurihari"; beam.transform.SetParent(shoro, false);
            beam.transform.localScale = new Vector3(2.5f, 0.16f, 0.16f);
            beam.transform.position = L(new Vector3(0, 3.85f, 0));
            beam.transform.rotation = srot;
            beam.GetComponent<Renderer>().sharedMaterial = wood;
            Undo.RegisterCreatedObjectUndo(beam, "shoro");
            var bell = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            bell.name = "Bonsho"; bell.transform.SetParent(shoro, false);
            bell.transform.localScale = new Vector3(1.05f, 0.62f, 1.05f);
            bell.transform.position = L(new Vector3(0, 3.0f, 0));
            bell.transform.rotation = srot;
            bell.GetComponent<Renderer>().sharedMaterial = bronze;
            Undo.RegisterCreatedObjectUndo(bell, "shoro");
            var cap = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            cap.name = "Kasa"; cap.transform.SetParent(shoro, false);
            cap.transform.localScale = new Vector3(1.05f, 0.5f, 1.05f);
            cap.transform.position = L(new Vector3(0, 3.62f, 0));
            cap.GetComponent<Renderer>().sharedMaterial = bronze;
            Undo.RegisterCreatedObjectUndo(cap, "shoro");
            var shumoku = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            shumoku.name = "Shumoku"; shumoku.transform.SetParent(shoro, false);
            shumoku.transform.localScale = new Vector3(0.13f, 0.85f, 0.13f);
            shumoku.transform.position = L(new Vector3(0, 2.9f, 1.05f));
            shumoku.transform.rotation = srot * Quaternion.Euler(90, 0, 0);
            shumoku.GetComponent<Renderer>().sharedMaterial = wood;
            Undo.RegisterCreatedObjectUndo(shumoku, "shoro");
        }

        // 参道(山門→本堂の石畳)と植栽(黒松=通年緑)
        var niwa = Group("Edo_Jomanji", "Niwa");
        for (float tt = 2.2f; tt < 11f; tt += 1.9f)
        {
            Vector2 p = gateC + gInw * tt;
            if (!PIP(JM, p)) break;
            var slab = GameObject.CreatePrimitive(PrimitiveType.Cube);
            slab.name = "Sando_" + tt.ToString("F0"); slab.transform.SetParent(niwa, false);
            slab.transform.localScale = new Vector3(1.7f, 0.07f, 1.05f);
            slab.transform.position = new Vector3(p.x, Ground(p.x, p.y) + 0.05f, p.y);
            slab.transform.rotation = Quaternion.Euler(0, gRy, 0);
            slab.GetComponent<Renderer>().sharedMaterial = stone;
            Undo.RegisterCreatedObjectUndo(slab, "sando");
        }
        var rnd = new System.Random(20260812);
        var pinePos = new[] {
            gA + gAxis * (gLen * 0.82f) + gInw * 4.0f,   // 山門北脇
            gA + gAxis * (gLen * 0.15f) + gInw * 10.5f,  // 鐘楼の奥
            gA + gAxis * (gLen * 0.85f) + gInw * 12.5f,  // 本堂北東
        };
        string[] pines = { PPineMid, PPineBig, PPineMid };
        int planted = 0;
        for (int k = 0; k < pinePos.Length; k++)
        {
            if (!PIP(JM, pinePos[k])) continue;
            var pa = AssetDatabase.LoadAssetAtPath<GameObject>(pines[k]);
            if (pa == null) continue;
            var tr = (GameObject)PrefabUtility.InstantiatePrefab(pa);
            tr.name = "Matsu_" + k; tr.transform.SetParent(niwa, true);
            tr.transform.position = new Vector3(pinePos[k].x, Ground(pinePos[k].x, pinePos[k].y) - 0.05f, pinePos[k].y);
            tr.transform.rotation = Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
            tr.transform.localScale = Vector3.one * (0.9f + 0.25f * (float)rnd.NextDouble());
            Undo.RegisterCreatedObjectUndo(tr, "matsu");
            planted++;
        }
        Well(bg, gA + gAxis * (gLen * 0.72f) + gInw * 6.5f, stone);
        AssetDatabase.SaveAssets();
        sb.AppendLine("Jomanji built (hondo=" + (hondo != null) + " kuri=" + (kuri != null) + " matsu=" + planted + ")");
        return sb.ToString();
    }

    // ---------- Stage 3: splat ----------
    public static string Stage3_Splat()
    {
        var t = EdoTamachiBuilder.T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -832, x1 = -645, z0 = 715, z1 = 1040;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A2 = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        var strips = new Vector2[][] { R1, R2, Y1, Y2 };
        int changed = 0;
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                var p = new Vector2(wx, wz);
                float noise = Mathf.PerlinNoise(wx * 0.13f, wz * 0.13f);
                float bare, grass, dirt;
                bool inStrip = false;
                foreach (var s in strips) if (PIP(s, p)) { inStrip = true; break; }
                if (inStrip)
                {   // 町屋: 表〜中は踏み固め土、裏へ行くほど草
                    bare = Mathf.Lerp(0.40f, 0.58f, noise); grass = 0.10f; dirt = 1f - bare - grass;
                }
                else if (PIP(JM, p))
                {   // 境内: 掃き清めた土
                    bare = Mathf.Lerp(0.48f, 0.64f, noise); grass = 0.05f; dirt = 1f - bare - grass;
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
