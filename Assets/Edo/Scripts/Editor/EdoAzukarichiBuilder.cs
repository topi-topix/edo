// 溜池周囲の御預明地3帯+干場拝借地5筆+大的稽古場 (2026-08-09)
// 【典拠】
//  ・区画=ユーザー下書き(紫/緑/赤=御預明地、水色5筆=干場拝借地、黄=大的稽古場)。
//    ユーザー注記「資料から明確に領域がわからなかったのでおおよそ」→下書き線は目安とし、
//    既存の正しい区画(田町・代地町屋・桐畑・物干)は撤去せず、預地帯は既存物を避けた実効領域に適用する。
//  ・御預明地: 溜池は江戸城外堀を兼ねる(御府内備考)ため、堤沿いの明地は火除・堤防保全のため
//    建物を置かず大名預りとされた。切絵図の判読(ユーザー): 紫=戸田采女正 / 緑=松平大和守(川越藩
//    =隣接の上屋敷[[matsudaira-yamato-kamiyashiki]]) / 赤=松平美濃守(隣接中屋敷)。いずれも自邸に
//    隣接する堤明地の預りで整合。表現=刈られた草地+桐畑(広重「名所江戸百景 赤坂桐畑」)+榜示杭【一般類型】。
//  ・干場拝借地(5筆): 文政町方書上=田町二丁目の紺屋・合羽屋が宝暦10年(1760)に溜池土手に
//    拝借した物干場(既再現の物干の正典化)。種別は「合羽干場」「紺屋干場」「紺屋合羽屋共干場」の3種。
//    2026-08-09、ユーザーが色分け下書き(黄=合羽干場/水色=紺屋干場/赤=共干場)で区画対応を確定:
//    W1・W2・W3=紺屋干場(竿の反物干し+張り板のみ) / W4=紺屋合羽屋共干場(3種混在) /
//    W5=合羽干場(渋紙の平干しのみ)。
//  ・大的稽古場(黄): 堤明地内の弓術大的稽古の矢場。構造(安土+大的+射小屋+矢来+矢除板塀)は
//    矢場の一般類型【推定スタンドイン】。射小屋=kidobanya代用。
// 【整地】ユーザー許可「必要に応じて整地可」: 大的稽古場のみ平場化(矢道が必要なため、7.5mレベル+外周5mブレンド)。
//    バックアップ=Library/EdoBackup_20260809_oomato.bin。溜池snapより後の改変である点に注意
//    ([[tameike-bank-and-recarve-side-effects]]: Recarveすると平場が snap 時点へ戻る)。
//    預地帯・干場は無造成、設置物は現況高h>=7.0(水面6.6の上)のみに置く。
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class EdoAzukarichiBuilder
{
    const float ES = 1.818f;
    const string PBanya = EdoAssets.Eg.Kidobanya;
    const string PKiri = EdoAssets.JG.SakuraBig01;
    const string PKiri2 = EdoAssets.JG.SakuraMid01;

    // ---- 下書きポリゴン ----
    static readonly Vector2[] PU = { new Vector2(-355.46f,483.40f), new Vector2(-291.96f,441.54f), new Vector2(-240.33f,419.21f), new Vector2(-167.76f,406.65f), new Vector2(-93.80f,398.28f), new Vector2(-44.26f,395.48f), new Vector2(-80.54f,373.16f), new Vector2(-205.44f,325.01f), new Vector2(-308.71f,369.67f), new Vector2(-386.16f,452.00f) };
    static readonly Vector2[] GR = { new Vector2(-646.79f,694.92f), new Vector2(-606.47f,715.77f), new Vector2(-360.39f,486.38f), new Vector2(-392.37f,451.62f), new Vector2(-553.64f,575.36f) };
    static readonly Vector2[] RD = { new Vector2(-798.68f,1191.73f), new Vector2(-837.55f,1179.46f), new Vector2(-777.20f,1016.80f), new Vector2(-763.90f,1019.87f), new Vector2(-647.28f,722.18f), new Vector2(-660.57f,715.02f), new Vector2(-652.39f,700.70f), new Vector2(-609.42f,721.16f), new Vector2(-709.68f,961.56f), new Vector2(-791.85f,1133.01f) };
    static readonly Vector2[] W1 = { new Vector2(-547.24f,595.91f), new Vector2(-601.74f,660.89f), new Vector2(-585.81f,671.37f), new Vector2(-528.80f,607.23f) };
    static readonly Vector2[] W2 = { new Vector2(-643.37f,738.04f), new Vector2(-664.37f,790.74f), new Vector2(-653.36f,795.24f), new Vector2(-632.20f,742.49f) };
    static readonly Vector2[] W3 = { new Vector2(-675.09f,818.44f), new Vector2(-684.03f,839.88f), new Vector2(-672.41f,844.35f), new Vector2(-663.48f,820.22f) };
    static readonly Vector2[] W4 = { new Vector2(-755.50f,1018.57f), new Vector2(-695.64f,867.58f), new Vector2(-678.66f,872.94f), new Vector2(-701.89f,928.33f), new Vector2(-748.35f,1020.36f) };
    static readonly Vector2[] W5 = { new Vector2(-826.52f,1156.51f), new Vector2(-807.51f,1162.76f), new Vector2(-801.79f,1146.61f), new Vector2(-820.53f,1139.59f) };
    static readonly Vector2[] YL = { new Vector2(-285.95f,390.25f), new Vector2(-232.08f,368.55f), new Vector2(-227.42f,381.34f), new Vector2(-281.30f,401.88f) };
    const float PadY = 7.5f;   // 大的稽古場の平場レベル
    const float MinH = 7.0f;   // 設置物の最低地盤高(水面6.6+0.4)

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
    static GameObject Prim(PrimitiveType t, Transform parent, string name, Vector3 pos, Vector3 scale, Quaternion rot, Material m)
    {
        var go = GameObject.CreatePrimitive(t);
        go.name = name; go.transform.SetParent(parent, false);
        go.transform.position = pos; go.transform.localScale = scale; go.transform.rotation = rot;
        go.GetComponent<Renderer>().sharedMaterial = m;
        Undo.RegisterCreatedObjectUndo(go, name);
        return go;
    }
    static void StakeFence(Transform parent, Vector2 A, Vector2 B, string prefix, Material wood, float pitch)
    {
        Vector2 dir = (B - A).normalized; float len = (B - A).magnitude;
        int n = Mathf.Max(1, Mathf.RoundToInt(len / pitch));
        float pp = len / n;
        float ryBar = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
        for (int k = 0; k <= n; k++)
        {
            Vector2 p = A + dir * (pp * k);
            float g = Ground(p.x, p.y);
            Prim(PrimitiveType.Cylinder, parent, prefix + "_p" + k, new Vector3(p.x, g + 0.55f, p.y),
                new Vector3(0.09f, 0.62f, 0.09f), Quaternion.identity, wood);
            if (k < n)
            {
                Vector2 m = A + dir * (pp * (k + 0.5f));
                float g1 = Ground(p.x, p.y), g2 = Ground(p.x + dir.x * pp, p.y + dir.y * pp);
                Prim(PrimitiveType.Cylinder, parent, prefix + "_b" + k,
                    new Vector3(m.x, (g1 + g2) * 0.5f + 0.92f, m.y),
                    new Vector3(0.055f, pp * 0.52f, 0.055f), Quaternion.Euler(90f, ryBar, 0), wood);
            }
        }
    }

    // ---------- Stage 0: 干場区画内の桐を撤去 ----------
    public static string Stage0_Clear()
    {
        var parcels = new Vector2[][] { W1, W2, W3, W4, W5 };
        var bank = GameObject.Find("Edo_Tamachi_Bank");
        var kill = new List<GameObject>();
        if (bank != null)
        {
            var kg = bank.transform.Find("Kiribatake");
            if (kg != null)
                foreach (Transform c in kg)
                {
                    var p = new Vector2(c.position.x, c.position.z);
                    foreach (var poly in parcels)
                        if (PIP(poly, p) || DistToPolyEdge(poly, p) < 1.5f) { kill.Add(c.gameObject); break; }
                }
        }
        foreach (var k in kill) Undo.DestroyObjectImmediate(k);
        return "removed kiri=" + kill.Count;
    }

    // ---------- Stage 1: 大的稽古場 (整地+安土+的+射小屋+矢来) ----------
    public static string Stage1_Oomato()
    {
        var sb = new System.Text.StringBuilder();
        if (GameObject.Find("Edo_Oomatoba") != null) return "SKIP Edo_Oomatoba";
        var t = EdoTamachiBuilder.T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cellW = ts.x / (res - 1);
        // --- 整地: YL内=7.5 / 外周5mブレンド。バックアップを保存 ---
        float bx0 = -293, bx1 = -220, bz0 = 361, bz1 = 409;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((bx0 - tp.x) / cellW)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((bx1 - tp.x) / cellW));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((bz0 - tp.z) / cellW)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((bz1 - tp.z) / cellW));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var H = td.GetHeights(ix0, iz0, w, h);
        // バックアップ(ヘッダ: ix0,iz0,w,h)
        using (var bw = new System.IO.BinaryWriter(System.IO.File.Open("Library/EdoBackup_20260809_oomato.bin", System.IO.FileMode.Create)))
        {
            bw.Write(ix0); bw.Write(iz0); bw.Write(w); bw.Write(h);
            for (int z = 0; z < h; z++) for (int x = 0; x < w; x++) bw.Write(H[z, x]);
        }
        float targetN = (PadY - tp.y) / ts.y;
        int changed = 0;
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = tp.x + (ix0 + x) * cellW;
                float wz = tp.z + (iz0 + z) * cellW;
                var p = new Vector2(wx, wz);
                float cur = H[z, x];
                if (PIP(YL, p)) { H[z, x] = targetN; changed++; }
                else
                {
                    float d = DistToPolyEdge(YL, p);
                    if (d < 5f) { H[z, x] = Mathf.Lerp(targetN, cur, d / 5f); changed++; }
                }
            }
        td.SetHeights(ix0, iz0, H);
        sb.AppendLine("pad cells=" + changed + " backup=Library/EdoBackup_20260809_oomato.bin");

        // --- ローカルフレーム: 射場(東端)→的場(西端) ---
        Vector2 eMid = (YL[1] + YL[2]) * 0.5f;   // 東端中央(射場)
        Vector2 wMid = (YL[0] + YL[3]) * 0.5f;   // 西端中央(的場)
        Vector2 axis = (wMid - eMid).normalized; // 射方向(西向き)
        Vector2 side = new Vector2(-axis.y, axis.x);
        float ryShoot = Mathf.Atan2(axis.x, axis.y) * Mathf.Rad2Deg;
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        var earth = new Material(Shader.Find("Universal Render Pipeline/Lit")); earth.color = new Color(0.46f, 0.38f, 0.28f);
        var board = new Material(Shader.Find("Universal Render Pipeline/Lit")); board.color = new Color(0.55f, 0.44f, 0.30f);
        var white = new Material(Shader.Find("Universal Render Pipeline/Lit")); white.color = new Color(0.92f, 0.90f, 0.85f);
        var black = new Material(Shader.Find("Universal Render Pipeline/Lit")); black.color = new Color(0.10f, 0.10f, 0.10f);
        var root = Group("Edo_Oomatoba", "Matoba");

        // --- 安土(的土手): 傾斜面ウェッジ(自作メッシュ・フラットシェーディング) ---
        Vector2 azC = wMid - axis * 5.0f;        // 西端から5m内側
        {
            var go = new GameObject("Azuchi", typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(root, false);
            go.transform.position = new Vector3(azC.x, PadY, azC.y);
            go.transform.rotation = Quaternion.Euler(0, ryShoot, 0);   // local +Z = 射方向(西)
            float hw = 6.0f, dep = 2.6f, hgt = 1.15f;
            // local: 射手側(東)=+Z … 前面が斜面。背面(西)=-Z 垂直
            var v = new List<Vector3>(); var tri = new List<int>();
            System.Action<Vector3, Vector3, Vector3> face3 = (a, b, c) =>
            { int b0 = v.Count; v.Add(a); v.Add(b); v.Add(c); tri.Add(b0); tri.Add(b0 + 1); tri.Add(b0 + 2); };
            Vector3 fl = new Vector3(-hw, 0, dep), fr = new Vector3(hw, 0, dep);      // 前縁(裾)
            Vector3 tl = new Vector3(-hw, hgt, -dep * 0.4f), tr = new Vector3(hw, hgt, -dep * 0.4f); // 天端
            Vector3 bl = new Vector3(-hw, 0, -dep), br = new Vector3(hw, 0, -dep);    // 背裾
            face3(fl, tl, fr); face3(fr, tl, tr);      // 斜面
            face3(tl, bl, tr); face3(tr, bl, br);      // 背面
            face3(fl, bl, tl);                          // 左妻
            face3(fr, tr, br);                          // 右妻
            var mesh = new Mesh(); mesh.SetVertices(v); mesh.SetTriangles(tri, 0);
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            go.GetComponent<MeshRenderer>().sharedMaterial = earth;
            Undo.RegisterCreatedObjectUndo(go, "azuchi");
        }
        // --- 大的3基(安土斜面に立てかけ): 白面+黒環(同心円柱の重ね) ---
        for (int k = -1; k <= 1; k++)
        {
            Vector2 mp = azC + side * (k * 3.4f) + axis * -0.15f;
            var rot = Quaternion.Euler(0, ryShoot, 0) * Quaternion.Euler(-58f, 0, 0); // 斜面なり
            float[] dia = { 1.42f, 0.95f, 0.52f, 0.20f };
            Material[] mats = { white, black, white, black };
            for (int L = 0; L < 4; L++)
            {
                Prim(PrimitiveType.Cylinder, root, "Mato" + k + "_" + L,
                    new Vector3(mp.x, PadY + 0.72f, mp.y) + rot * new Vector3(0, 0.012f * (L + 1), 0),
                    new Vector3(dia[L], 0.012f, dia[L]), rot, mats[L]);
            }
        }
        // --- 矢除板塀(的場の背後=西端) ---
        {
            Vector2 a = YL[3] + (YL[0] - YL[3]).normalized * 0.5f;
            Vector2 b = YL[0] + (YL[3] - YL[0]).normalized * 0.5f;
            Vector2 d = (b - a).normalized; float len = (b - a).magnitude;
            int n = Mathf.CeilToInt(len / 1.9f);
            float pp = len / n;
            float ry = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
            var g = Group("Edo_Oomatoba", "Yayoke");
            for (int k = 0; k < n; k++)
            {
                Vector2 p = a + d * (pp * (k + 0.5f));
                Prim(PrimitiveType.Cube, g, "Ita_" + k, new Vector3(p.x, PadY + 1.05f, p.y),
                    new Vector3(pp * 0.98f, 2.1f, 0.06f), Quaternion.Euler(0, ry, 0), board);
            }
        }
        // --- 射小屋(東端・西面): kidobanya 代用 ---
        {
            var mBanya = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.Own.MKidobanya);
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(PBanya);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
            go.name = "Shakoya"; go.transform.SetParent(root, true);
            go.transform.rotation = Quaternion.Euler(0, ryShoot, 0);
            go.transform.localScale = Vector3.one * ES;
            Vector2 sp = eMid - axis * -1.5f; // 東端の1.5m内側
            go.transform.position = new Vector3(sp.x, PadY + 2f, sp.y);
            if (mBanya != null) foreach (var r in go.GetComponentsInChildren<Renderer>())
                { var ms = r.sharedMaterials; for (int i = 0; i < ms.Length; i++) ms[i] = mBanya; r.sharedMaterials = ms; }
            var rs = go.GetComponentsInChildren<Renderer>();
            var b2 = rs[0].bounds; foreach (var r in rs) b2.Encapsulate(r.bounds);
            go.transform.position += new Vector3(0, (PadY - 0.05f) - b2.min.y, 0);
            Undo.RegisterCreatedObjectUndo(go, "shakoya");
        }
        // --- 矢来(両長辺の杭柵) ---
        var yg = Group("Edo_Oomatoba", "Yarai");
        StakeFence(yg, YL[0], YL[1], "YaraiS", wood, 2.2f);
        StakeFence(yg, YL[2], YL[3], "YaraiN", wood, 2.2f);
        AssetDatabase.SaveAssets();
        sb.AppendLine("Oomatoba built (的3・安土・射小屋・矢除板塀・矢来)");
        return sb.ToString();
    }

    // ---------- Stage 2: 干場5筆 ----------
    // 【密度の典拠】広重「名所江戸百景 神田紺屋町」(安政4年)=藍染めした反物(一反=幅約37cm・長さ約12.5m)を
    // 一反ずつ、櫓を組んだ高い物干し竿に吊し幟(のぼり)のように靡かせる、という当時有名だった光景。
    // 初版(2026-08-09作成)は洗濯物程度の低い小型ラックを疎らに置いていたが、ユーザー指摘の通り
    // 商いの干場としては規模も密度も過小だった。高さ5.5〜7.5mの幟状「櫓竿(Yagura)」を主体に密度を上げて修正。
    public static string Stage2_Hoshiba()
    {
        var sb = new System.Text.StringBuilder();
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        var kon = new Material(Shader.Find("Universal Render Pipeline/Lit")); kon.color = new Color(0.13f, 0.16f, 0.31f);
        var asagi = new Material(Shader.Find("Universal Render Pipeline/Lit")); asagi.color = new Color(0.36f, 0.55f, 0.62f);
        var shiro = new Material(Shader.Find("Universal Render Pipeline/Lit")); shiro.color = new Color(0.86f, 0.84f, 0.78f);
        var shibu = new Material(Shader.Find("Universal Render Pipeline/Lit")); shibu.color = new Color(0.56f, 0.36f, 0.16f);
        var ita = new Material(Shader.Find("Universal Render Pipeline/Lit")); ita.color = new Color(0.62f, 0.52f, 0.38f);
        Material[] cloth = { kon, kon, kon, asagi, shiro };
        // kind: "kouya"=紺屋干場(幟竿+竿干し+張り板) / "kappaya"=合羽干場(渋紙のみ) / "kyodo"=紺屋合羽屋共干場(混在)
        // 対応は2026-08-09にユーザーが色分け下書きで確定(黄=合羽干場→W5 / 水色=紺屋干場→W1,W2,W3 / 赤=共→W4)
        var defs = new[] {
            new { name = "W1", poly = W1, seed = 9501, kind = "kouya" }, new { name = "W2", poly = W2, seed = 9502, kind = "kouya" },
            new { name = "W3", poly = W3, seed = 9503, kind = "kouya" }, new { name = "W4", poly = W4, seed = 9504, kind = "kyodo" },
            new { name = "W5", poly = W5, seed = 9505, kind = "kappaya" } };
        foreach (var d in defs)
        {
            if (GameObject.Find("Edo_Hoshiba") != null && GameObject.Find("Edo_Hoshiba").transform.Find(d.name) != null)
            { sb.AppendLine("SKIP " + d.name); continue; }
            var g = Group("Edo_Hoshiba", d.name);
            var rnd = new System.Random(d.seed);
            int N = d.poly.Length;
            for (int i = 0; i < N; i++) StakeFence(g, d.poly[i], d.poly[(i + 1) % N], "Fence" + i, wood, 2.2f);
            // 長軸フレーム: 最長辺を基準
            int longest = 0; float best = 0;
            for (int i = 0; i < N; i++)
            { float L = (d.poly[(i + 1) % N] - d.poly[i]).magnitude; if (L > best) { best = L; longest = i; } }
            Vector2 A = d.poly[longest], B = d.poly[(longest + 1) % N];
            Vector2 axis = (B - A).normalized; float len = best;
            Vector2 inw = new Vector2(-axis.y, axis.x);
            if (!PIP(d.poly, A + axis * (len * 0.5f) + inw * 2.5f)) inw = -inw;
            float ryRack = Mathf.Atan2(axis.x, axis.y) * Mathf.Rad2Deg;
            int yagura = 0, racks = 0, mats = 0, boards = 0;
            // グリッド密度: 幟竿は間隔を要するので3.2m×3.4m、渋紙単独区画はさらに詰める
            float stepT = d.kind == "kappaya" ? 2.6f : 3.2f;
            float stepD = d.kind == "kappaya" ? 2.4f : 3.4f;
            for (float tt = 2.5f; tt < len - 1.5f; tt += stepT)
            {
                for (float dd = 2.2f; dd < 40f; dd += stepD)
                {
                    Vector2 p = A + axis * tt + inw * dd + new Vector2((float)(rnd.NextDouble() - 0.5) * 0.9f, (float)(rnd.NextDouble() - 0.5) * 0.9f);
                    if (!PIP(d.poly, p) || DistToPolyEdge(d.poly, p) < 1.6f) continue;
                    if (Ground(p.x, p.y) < MinH) continue;
                    double roll = rnd.NextDouble();
                    float jit = (float)rnd.NextDouble() * 14f - 7f;
                    // kouya=幟竿主体+張り板少々、kappaya=渋紙(平干し+斜め掛け)、kyodo=5種混在
                    string item;
                    if (d.kind == "kouya") item = roll < 0.68 ? "yagura" : (roll < 0.85 ? "rack" : "hariita");
                    else if (d.kind == "kappaya") item = roll < 0.6 ? "shibuflat" : "shibuslant";
                    else item = roll < 0.40 ? "yagura" : roll < 0.55 ? "rack" : roll < 0.68 ? "hariita" : roll < 0.86 ? "shibuflat" : "shibuslant";

                    if (item == "yagura")
                    {   // 紺屋: 幟竿(反物1反を頂から吊るし靡かせる。広重「神田紺屋町」の光景)
                        float h = 5.5f + (float)rnd.NextDouble() * 2.0f;
                        float gy = Ground(p.x, p.y);
                        var pg = new GameObject("Yagura_" + yagura); pg.transform.SetParent(g, false);
                        pg.transform.position = new Vector3(p.x, gy, p.y);
                        pg.transform.rotation = Quaternion.Euler(0, ryRack + jit, 0);
                        Undo.RegisterCreatedObjectUndo(pg, "yagura");
                        var pole = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                        pole.transform.SetParent(pg.transform, false);
                        pole.transform.localScale = new Vector3(0.045f, h * 0.5f, 0.045f);
                        pole.transform.localPosition = new Vector3(0, h * 0.5f, 0);
                        pole.GetComponent<Renderer>().sharedMaterial = wood;
                        var yardarm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                        yardarm.transform.SetParent(pg.transform, false);
                        yardarm.transform.localScale = new Vector3(0.02f, 0.24f, 0.02f);
                        yardarm.transform.localEulerAngles = new Vector3(0, 0, 90);
                        yardarm.transform.localPosition = new Vector3(0, h - 0.35f, 0);
                        yardarm.GetComponent<Renderer>().sharedMaterial = wood;
                        float clothH = h - 1.3f;
                        var cl = GameObject.CreatePrimitive(PrimitiveType.Cube);
                        cl.transform.SetParent(pg.transform, false);
                        cl.transform.localScale = new Vector3(0.37f, clothH, 0.015f);
                        cl.transform.localPosition = new Vector3(0, h - 0.35f - clothH * 0.5f, 0.03f);
                        cl.transform.localEulerAngles = new Vector3((float)rnd.NextDouble() * 5f - 2.5f, 0, (float)rnd.NextDouble() * 4f - 2f);
                        cl.GetComponent<Renderer>().sharedMaterial = cloth[rnd.Next(cloth.Length)];
                        yagura++;
                    }
                    else if (item == "rack")
                    {   // 紺屋: 低い竿干し(柱2+竿+反物3〜5枚、地上作業台での仮干し)
                        var rg = new GameObject("Rack_" + racks); rg.transform.SetParent(g, false);
                        float gy = Ground(p.x, p.y);
                        rg.transform.position = new Vector3(p.x, gy, p.y);
                        rg.transform.rotation = Quaternion.Euler(0, ryRack + jit, 0);
                        Undo.RegisterCreatedObjectUndo(rg, "rack");
                        for (int k = 0; k < 2; k++)
                        {
                            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                            post.transform.SetParent(rg.transform, false);
                            post.transform.localScale = new Vector3(0.09f, 1.15f, 0.09f);
                            post.transform.localPosition = new Vector3(k == 0 ? -1.9f : 1.9f, 1.15f, 0);
                            post.GetComponent<Renderer>().sharedMaterial = wood;
                        }
                        var bar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                        bar.transform.SetParent(rg.transform, false);
                        bar.transform.localScale = new Vector3(0.05f, 1.95f, 0.05f);
                        bar.transform.localEulerAngles = new Vector3(0, 0, 90);
                        bar.transform.localPosition = new Vector3(0, 2.2f, 0);
                        bar.GetComponent<Renderer>().sharedMaterial = wood;
                        int nc = 3 + rnd.Next(3);
                        for (int c = 0; c < nc; c++)
                        {
                            var cc = GameObject.CreatePrimitive(PrimitiveType.Cube);
                            cc.transform.SetParent(rg.transform, false);
                            cc.transform.localScale = new Vector3(0.42f, 1.85f, 0.016f);
                            cc.transform.localPosition = new Vector3(-1.5f + c * (3.0f / nc) + (float)rnd.NextDouble() * 0.2f, 1.26f, 0);
                            cc.transform.localEulerAngles = new Vector3(0, (float)rnd.NextDouble() * 6f - 3f, 0);
                            cc.GetComponent<Renderer>().sharedMaterial = cloth[rnd.Next(cloth.Length)];
                        }
                        racks++;
                    }
                    else if (item == "hariita")
                    {   // 紺屋: 張り板(布を張った板を斜めに立てる)
                        int nb = 2 + rnd.Next(2);
                        for (int b2 = 0; b2 < nb; b2++)
                        {
                            Vector2 bp = p + axis * (b2 * 0.9f);
                            if (!PIP(d.poly, bp) || Ground(bp.x, bp.y) < MinH) continue;
                            float gy = Ground(bp.x, bp.y);
                            var bd = Prim(PrimitiveType.Cube, g, "Hariita_" + boards,
                                new Vector3(bp.x, gy + 0.95f, bp.y),
                                new Vector3(0.62f, 2.05f, 0.035f), Quaternion.Euler(-14f, ryRack + jit, 0), ita);
                            var cc = GameObject.CreatePrimitive(PrimitiveType.Cube);
                            cc.transform.SetParent(bd.transform, false);
                            cc.transform.localScale = new Vector3(0.85f, 0.9f, 0.6f);
                            cc.transform.localPosition = new Vector3(0, 0.02f, -0.55f);
                            cc.GetComponent<Renderer>().sharedMaterial = cloth[rnd.Next(cloth.Length)];
                            boards++;
                        }
                    }
                    else if (item == "shibuflat")
                    {   // 合羽屋: 渋紙の平干し(地面に広げる)
                        int nm = 2 + rnd.Next(3);
                        for (int m2 = 0; m2 < nm; m2++)
                        {
                            Vector2 mp = p + axis * ((float)rnd.NextDouble() * 3.0f - 1.5f) + inw * ((float)rnd.NextDouble() * 2.2f - 1.1f);
                            if (!PIP(d.poly, mp) || Ground(mp.x, mp.y) < MinH) continue;
                            Prim(PrimitiveType.Cube, g, "Shibugami_" + mats,
                                new Vector3(mp.x, Ground(mp.x, mp.y) + 0.05f, mp.y),
                                new Vector3(1.75f, 0.03f, 0.95f), Quaternion.Euler(0, ryRack + jit + (float)rnd.NextDouble() * 14f - 7f, 0), shibu);
                            mats++;
                        }
                    }
                    else
                    {   // 合羽屋: 渋紙の斜め掛け干し(通気用に傾けて立て並べる)
                        int nb = 2 + rnd.Next(2);
                        for (int b2 = 0; b2 < nb; b2++)
                        {
                            Vector2 bp = p + axis * (b2 * 1.05f);
                            if (!PIP(d.poly, bp) || Ground(bp.x, bp.y) < MinH) continue;
                            float gy = Ground(bp.x, bp.y);
                            Prim(PrimitiveType.Cube, g, "ShibuSlant_" + mats,
                                new Vector3(bp.x, gy + 0.62f, bp.y),
                                new Vector3(0.98f, 1.35f, 0.02f), Quaternion.Euler(-32f, ryRack + jit, 0), shibu);
                            mats++;
                        }
                    }
                }
            }
            sb.AppendLine(d.name + " 幟竿=" + yagura + " 竿干=" + racks + " 渋紙=" + mats + " 張板=" + boards);
        }
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }

    // ---------- Stage 3: 御預明地3帯 (榜示杭+桐+下草splat) ----------
    public static string Stage3_Azukarichi()
    {
        var sb = new System.Text.StringBuilder();
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.46f, 0.36f, 0.24f);
        var hoshiba = new Vector2[][] { W1, W2, W3, W4, W5 };
        // 近傍の既存レンダラー中心(疎配置の回避用)
        var occ = new List<Vector2>();
        foreach (var r in GameObject.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
        {
            var c = r.bounds.center;
            if (c.x < -940 || c.x > -30 || c.z < 300 || c.z > 1210) continue;
            occ.Add(new Vector2(c.x, c.z));
        }
        System.Func<Vector2, float, bool> nearOcc = (p, rad) =>
        { foreach (var o in occ) if ((o - p).sqrMagnitude < rad * rad) return true; return false; };

        var defs = new[] {
            new { name = "Edo_Azukarichi_Toda",            poly = PU, kiri = 22, seed = 9601,
                  edges = new int[]{5,6,7,8} },   // 南側(陸側)の辺に榜示杭
            new { name = "Edo_Azukarichi_MatsudairaYamatoAkichi", poly = GR, kiri = 18, seed = 9602,
                  edges = new int[]{3,4} },       // 西側(屋敷側)
            new { name = "Edo_Azukarichi_MatsudairaMinoAkichi",   poly = RD, kiri = 0,  seed = 9603,
                  edges = new int[]{0,6} },       // 北端・南端のみ(西側は町屋の裏)
        };
        foreach (var d in defs)
        {
            if (GameObject.Find(d.name) != null) { sb.AppendLine("SKIP " + d.name); continue; }
            var g = Group(d.name, "Boji");
            int posts = 0;
            foreach (int e in d.edges)
            {
                Vector2 a = d.poly[e], b = d.poly[(e + 1) % d.poly.Length];
                float len = (b - a).magnitude; Vector2 dir = (b - a) / len;
                for (float tt = 0; tt <= len; tt += 18f)
                {
                    Vector2 p = a + dir * tt;
                    if (Ground(p.x, p.y) < MinH) continue;
                    if (nearOcc(p, 1.2f)) continue;
                    Prim(PrimitiveType.Cube, g, "Boji_" + posts,
                        new Vector3(p.x, Ground(p.x, p.y) + 0.55f, p.y),
                        new Vector3(0.15f, 1.1f, 0.15f),
                        Quaternion.Euler(0, Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg, 0), wood);
                    posts++;
                }
            }
            // 桐(スタンドイン=Sakura_Summer、既存桐畑と同種)
            var tg = Group(d.name, "Kiri");
            var rnd = new System.Random(d.seed);
            string[] trees = { PKiri, PKiri2 };
            float minx = float.MaxValue, maxx = float.MinValue, minz = float.MaxValue, maxz = float.MinValue;
            foreach (var p in d.poly) { minx = Mathf.Min(minx, p.x); maxx = Mathf.Max(maxx, p.x); minz = Mathf.Min(minz, p.y); maxz = Mathf.Max(maxz, p.y); }
            var placed = new List<Vector2>();
            int tries = 0, made = 0;
            while (made < d.kiri && tries < d.kiri * 40)
            {
                tries++;
                var p = new Vector2(Mathf.Lerp(minx, maxx, (float)rnd.NextDouble()), Mathf.Lerp(minz, maxz, (float)rnd.NextDouble()));
                if (!PIP(d.poly, p)) continue;
                if (Ground(p.x, p.y) < 7.15f) continue;
                if (PIP(YL, p) || DistToPolyEdge(YL, p) < 6f) continue;
                bool inW = false; foreach (var wp in hoshiba) if (PIP(wp, p) || DistToPolyEdge(wp, p) < 3f) { inW = true; break; }
                if (inW) continue;
                if (nearOcc(p, 5.5f)) continue;
                bool close = false; foreach (var q in placed) if ((q - p).sqrMagnitude < 64f) { close = true; break; }
                if (close) continue;
                var pa = AssetDatabase.LoadAssetAtPath<GameObject>(trees[rnd.Next(trees.Length)]);
                var tr = (GameObject)PrefabUtility.InstantiatePrefab(pa);
                tr.name = "Kiri_" + made; tr.transform.SetParent(tg, true);
                tr.transform.position = new Vector3(p.x, Ground(p.x, p.y) - 0.05f, p.y);
                tr.transform.rotation = Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
                tr.transform.localScale = Vector3.one * (0.95f + 0.45f * (float)rnd.NextDouble());
                Undo.RegisterCreatedObjectUndo(tr, "kiri");
                placed.Add(p); made++;
            }
            sb.AppendLine(d.name + " 榜示杭=" + posts + " 桐=" + made);
        }
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }

    // ---------- Stage 4: splat (預地=草地 / 干場=土 / 稽古場=露地) ----------
    public static string Stage4_Splat()
    {
        var t = EdoTamachiBuilder.T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        var bands = new Vector2[][] { PU, GR, RD };
        var hoshiba = new Vector2[][] { W1, W2, W3, W4, W5 };
        // 既存の町屋区画には触れない(帯の下書きが重なっているため除外)
        var keepout = new List<Vector2[]> {
            new Vector2[]{ new Vector2(-664.93f,721.86f), new Vector2(-691.56f,792.63f), new Vector2(-678.59f,797.53f), new Vector2(-651.27f,725.71f) },
            new Vector2[]{ new Vector2(-696.49f,802.52f), new Vector2(-709.43f,839.37f), new Vector2(-693.91f,843.90f), new Vector2(-681.62f,807.05f) },
            new Vector2[]{ new Vector2(-712.66f,849.07f), new Vector2(-739.81f,918.90f), new Vector2(-723.65f,924.07f), new Vector2(-697.14f,852.31f) },
            new Vector2[]{ new Vector2(-743.02f,930.13f), new Vector2(-778.85f,1021.86f), new Vector2(-767.38f,1025.68f), new Vector2(-730.59f,932.04f) },
        };
        int total = 0;
        System.Action<float, float, float, float> paint = (x0, x1, z0, z1) =>
        {
            int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
            int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
            int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
            var A2 = td.GetAlphamaps(ix0, iz0, w, h);
            int L = td.alphamapLayers;
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                    float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                    var p = new Vector2(wx, wz);
                    float gh = EdoTamachiBuilder.Ground(wx, wz);
                    if (gh < 6.65f) continue;                       // 水面下は触らない
                    bool keep = false; foreach (var k in keepout) if (PIP(k, p)) { keep = true; break; }
                    if (keep) continue;
                    float noise = Mathf.PerlinNoise(wx * 0.11f, wz * 0.11f);
                    float bare, grass, dirt;
                    bool inH = false; foreach (var s in hoshiba) if (PIP(s, p)) { inH = true; break; }
                    if (inH)
                    {   // 干場: 踏み固め土
                        bare = Mathf.Lerp(0.42f, 0.60f, noise); grass = 0.10f; dirt = 1f - bare - grass;
                    }
                    else if (PIP(YL, p))
                    {   // 稽古場: 露地
                        bare = Mathf.Lerp(0.58f, 0.74f, noise); grass = 0.04f; dirt = 1f - bare - grass;
                    }
                    else
                    {
                        bool inB = false; foreach (var b in bands) if (PIP(b, p)) { inB = true; break; }
                        if (!inB) continue;
                        // 預地: 刈られた草地(草優勢)
                        grass = Mathf.Lerp(0.48f, 0.68f, noise); bare = 0.10f; dirt = 1f - grass - bare;
                    }
                    float sum = bare + grass + dirt;
                    for (int l = 0; l < L; l++) A2[zz, xx, l] = 0;
                    A2[zz, xx, 0] = dirt / sum; A2[zz, xx, 1] = grass / sum; A2[zz, xx, 2] = bare / sum;
                    total++;
                }
            td.SetAlphamaps(ix0, iz0, A2);
        };
        paint(-390, -40, 320, 490);      // 紫帯+黄
        paint(-652, -355, 447, 720);     // 緑帯+W1
        paint(-842, -605, 696, 1196);    // 赤帯+W2..W5
        return "splat cells=" + total;
    }
}
