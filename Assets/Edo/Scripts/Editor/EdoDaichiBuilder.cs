// 溜池端(桐畑)の町代地3町 + 横田・土岐拡張部の造成 (2026-08-09)
// 【考証確定(同日Web調査: 日本歴史地名大系/港区史通史編近世(上)/CODH翻刻9-091〜093)】
//   ・切絵図の表記は「芝青龍寺門前町代地」(青松寺の南隣・青龍寺の門前町。ユーザー提示の「青松寺」は青龍寺の誤読)
//   ・3町で1列: 芝御掃除町代地(177坪,19軒) → 芝永井町代地(219坪,14軒,文化8年/1811の大火で
//     増上寺火除地に召上げ→桐畑明地へ) → 芝青龍寺門前町代地(220坪,15軒,同年同火事で移転)
//   ・いずれも奥行わずか5間(約9m)の片側町。通りの溜池側に面し、裏は物干場拝借地→草花植付地→預地土手→水面
//   ・小店・仕舞屋の連なり(豪商の店構えは不適)。水茶屋は天保改革(1842-43)で撤去済み=置かない。
//     木戸・自身番は当町の史料未確認(木戸+番屋は江戸の町の一般類型として最小限を置く)
// 区画=ユーザー下書き線。赤(83m)=青龍寺門前町代地(史料の間口44間≒86mとほぼ一致)。
// 黄(129m)=南東43間分が永井町代地、北西残り約44mは御掃除町代地(間口35間の一部。全長は描線の外へ続く)。
// 造成方針: 町帯=街路縁高さのロフト平場+背後は溜池への土手 / 屋敷拡張水没部=水面+1mの棚7.6
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoDaichiBuilder
{
    // SW辺(街路側)を [0]->[1] とする
    public static Vector2[] SeiryujiPoly = {
        new Vector2(-382.06f,417.87f), new Vector2(-446.57f,471.25f),
        new Vector2(-435.76f,486.73f), new Vector2(-370.28f,431.37f) };
    public static Vector2[] NagaichoPoly = {
        new Vector2(-451.01f,474.71f), new Vector2(-551.60f,555.83f),
        new Vector2(-539.25f,569.83f), new Vector2(-438.79f,489.76f) };
    public const float NAGAI_LEN = 84.7f;   // 永井町=間口43間余。これより先(北西)は御掃除町代地

    const float WATER_Y = 6.6f;
    const float SHELF_Y = 7.6f;
    const float ES = 1.818f;

    public static Terrain T() { return EdoTameikeKitaBuilder.T(); }
    public static float Ground(float x, float z) { return EdoBuild.Ground(x, z); }

    static float DistToPoly(Vector2[] poly, Vector2 p)
    {
        float m = float.MaxValue;
        for (int i = 0; i < poly.Length; i++)
        {
            var a = poly[i]; var b = poly[(i + 1) % poly.Length];
            var d = b - a; float len = d.magnitude; d /= len;
            float t = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
            m = Mathf.Min(m, (p - (a + d * t)).magnitude);
        }
        return m;
    }

    public static string Stage0_Backup()
    {
        var t = T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        var all = td.GetHeights(0, 0, res, res);
        var bytes = new byte[res * res * 4];
        Buffer.BlockCopy(all, 0, bytes, 0, bytes.Length);
        string p = "Library/EdoBackup_20260809_daichi_height.bin";
        File.WriteAllBytes(p, bytes);
        return "saved " + p;
    }

    // ---------- Stage 1: 造成 (実行済み 2026-08-09。再実行は冪等でない点に注意=ロフトは現況から再サンプルされる) ----------
    public static string Stage1_Grade()
    {
        var t = T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (res - 1);
        float x0 = -570, x1 = -200, z0 = 270, z1 = 590;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var H = td.GetHeights(ix0, iz0, w, h);
        var changed = new bool[h, w];

        var strips = new[] { SeiryujiPoly, NagaichoPoly };
        var lofts = new List<float[]>(); var axes = new List<Vector2>(); var lens = new List<float>();
        foreach (var poly in strips)
        {
            Vector2 A = poly[0], B = poly[1];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            int n = Mathf.CeilToInt(len / 2f) + 1;
            var hs = new float[n];
            Vector2 inw = new Vector2(-axis.y, axis.x);
            var probe = A + axis * (len * 0.5f) + inw * 5f;
            if (!EdoGeom.PIP(poly, probe)) inw = -inw;
            for (int i = 0; i < n; i++)
            {
                var sp = A + axis * Mathf.Min(i * 2f, len) - inw * 1.5f;
                hs[i] = Ground(sp.x, sp.y);
            }
            var sm = new float[n];
            for (int i = 0; i < n; i++)
            {
                float s = 0; int c = 0;
                for (int k = -3; k <= 3; k++) { int j = Mathf.Clamp(i + k, 0, n - 1); s += hs[j]; c++; }
                sm[i] = s / c;
            }
            lofts.Add(sm); axes.Add(axis); lens.Add(len);
        }
        var yok = EdoNishiTameikeBuilder.Estates.First(x => x.group == "Edo_Yashiki_Yokota").poly;
        var tok = EdoNishiTameikeBuilder.Estates.First(x => x.group == "Edo_Yashiki_Toki").poly;

        int nChanged = 0;
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                float wx = tp.x + (ix0 + xx) * cell;
                float wz = tp.z + (iz0 + zz) * cell;
                var p = new Vector2(wx, wz);
                float cur = tp.y + H[zz, xx] * ts.y;
                float target = cur;
                for (int si = 0; si < 2; si++)
                {
                    var poly = strips[si];
                    Vector2 A = poly[0]; var axis = axes[si]; var loft = lofts[si]; float len = lens[si];
                    float tpar = Mathf.Clamp(Vector2.Dot(p - A, axis), 0, len);
                    int li = Mathf.Clamp(Mathf.RoundToInt(tpar / 2f), 0, loft.Length - 1);
                    float hsv = loft[li] - 0.10f;
                    if (EdoGeom.PIP(poly, p)) { target = hsv; }
                    else
                    {
                        float d = DistToPoly(poly, p);
                        if (d <= 10f)
                        {
                            float s = d / 10f; s = s * s * (3 - 2 * s);
                            float bank = Mathf.Lerp(hsv, cur, s);
                            if (bank > cur) target = Mathf.Max(target, bank);
                        }
                    }
                }
                foreach (var ep in new[] { yok, tok })
                {
                    if (EdoGeom.PIP(ep, p)) { if (target < SHELF_Y && cur < SHELF_Y) target = Mathf.Max(target, SHELF_Y); }
                    else
                    {
                        float d = DistToPoly(ep, p);
                        if (d <= 8f && cur < SHELF_Y)
                        {
                            float s = d / 8f; s = s * s * (3 - 2 * s);
                            float bank = Mathf.Lerp(SHELF_Y, cur, s);
                            if (bank > cur) target = Mathf.Max(target, bank);
                        }
                    }
                }
                if (Mathf.Abs(target - cur) > 0.01f)
                {
                    H[zz, xx] = Mathf.Clamp01((target - tp.y) / ts.y);
                    changed[zz, xx] = true; nChanged++;
                }
            }
        for (int pass = 0; pass < 2; pass++)
        {
            var src = (float[,])H.Clone();
            for (int zz = 1; zz < h - 1; zz++)
                for (int xx = 1; xx < w - 1; xx++)
                {
                    if (!changed[zz, xx]) continue;
                    float s = 0;
                    for (int dz = -1; dz <= 1; dz++) for (int dx = -1; dx <= 1; dx++) s += src[zz + dz, xx + dx];
                    H[zz, xx] = s / 9f;
                }
        }
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        var wbT = UnityEngine.Object.FindObjectsByType<WaterBody>(FindObjectsSortMode.None).First(x => x.gameObject.name == "Tameike");
        var snapH = td.GetHeights(wbT.sX, wbT.sZ, wbT.sW, wbT.sH);
        var snap = new float[wbT.sW * wbT.sH];
        for (int z2 = 0; z2 < wbT.sH; z2++) for (int x2 = 0; x2 < wbT.sW; x2++) snap[z2 * wbT.sW + x2] = snapH[z2, x2];
        wbT.snap = snap; wbT.hasSnap = true;
        WaterSnapStore.Save(wbT);          // ★ snap は非シリアライズ。書いたら必ず保存する
        return "graded cells=" + nChanged + " / Tameike snap retaken";
    }

    // ---------- 材質 ----------
    static Material Mat(string name, string tex)
    {
        string mp = EdoAssets.Own.Mat(name);
        var exist = AssetDatabase.LoadAssetAtPath<Material>(mp);
        if (exist != null) return exist;
        var m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        var t2 = AssetDatabase.LoadAssetAtPath<Texture2D>(tex);
        m.SetTexture("_BaseMap", t2);
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

    // ---------- Stage 2: 町屋列 v2 (奥行5間の小店・仕舞屋) ----------
    // kind: "SH"=Small House(家主の家) / "S2"=shop02(小店) / "S1"=shop01(床見世級の小屋)
    public static string Stage2_Rows()
    {
        var sb = new System.Text.StringBuilder();
        // 旧 Row の一掃 + 旧グループ名の改名
        var oldSei = GameObject.Find("Edo_Daichi_Seishoji");
        if (oldSei != null) oldSei.name = "Edo_Daichi_Seiryuji";
        foreach (var g in new[] { "Edo_Daichi_Seiryuji", "Edo_Daichi_Nagaicho", "Edo_Daichi_Gosoji" })
        {
            var root = GameObject.Find(g);
            if (root == null) continue;
            var row = root.transform.Find("Row"); if (row != null) UnityEngine.Object.DestroyImmediate(row.gameObject);
            var bk = root.transform.Find("Back"); if (bk != null) UnityEngine.Object.DestroyImmediate(bk.gameObject);
        }
        // 3町: 青龍寺(赤全体) / 永井町(黄のSE 43間) / 御掃除町(黄の残り)
        sb.AppendLine(Row("Edo_Daichi_Seiryuji", SeiryujiPoly, 0f, -1f,
            new[] { "S2", "S1", "SH", "S2", "S1", "S2", "S2", "S1", "S2", "S1", "S2" }, 9201));
        sb.AppendLine(Row("Edo_Daichi_Nagaicho", NagaichoPoly, 0f, NAGAI_LEN,
            new[] { "S1", "S2", "S2", "S1", "SH", "S1", "S2", "S1", "S2", "S2", "S1" }, 9202));
        sb.AppendLine(Row("Edo_Daichi_Gosoji", NagaichoPoly, NAGAI_LEN + 1.5f, -1f,
            new[] { "S1", "S1", "S2", "S1", "S1", "S1", "S2", "S1", "S1" }, 9203)); // 店借18/19軒の零細町=小屋密集
        AssetDatabase.SaveAssets();
        return sb.ToString();
    }

    static string Row(string groupName, Vector2[] poly, float t0, float t1, string[] pattern, int seed)
    {
        var rowG = Group(groupName, "Row");
        var backG = Group(groupName, "Back");
        var rnd = new System.Random(seed);
        Vector2 A = poly[0], B = poly[1];
        Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
        if (t1 < 0) t1 = len;
        Vector2 inw = new Vector2(-axis.y, axis.x);
        if (!EdoGeom.PIP(poly, A + axis * (len * 0.5f) + inw * 5f)) inw = -inw;
        Vector2 outw = -inw;
        float ryFace = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;
        var mS1 = Mat("M_Shop01", EdoAssets.Eg.TexShop01);
        var mS2 = Mat("M_Shop02", EdoAssets.Eg.TexShop02);
        var mOke = Mat("M_Oke", EdoAssets.Eg.TexOke);
        var mTaru = Mat("M_Komodaru", EdoAssets.Eg.TexKomodaru);
        int made = 0; float tcur = t0 + 1.2f; int pi = 0;
        while (true)
        {
            string kind = pattern[pi % pattern.Length]; pi++;
            float wLot; string path; float sc; Material mat = null;
            if (kind == "SH") { path = EdoAssets.VK.SmallHouse; wLot = 15.0f; sc = 1f; }
            else if (kind == "S2") { path = EdoAssets.Eg.Shop02; wLot = 7.4f; sc = ES; mat = mS2; }
            else { path = EdoAssets.Eg.Shop01; wLot = 5.2f; sc = ES; mat = mS1; }
            if (tcur + wLot > t1 - 0.8f) break;
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
            go.name = kind + "_" + made;
            go.transform.SetParent(rowG, true);
            go.transform.rotation = Quaternion.Euler(0, ryFace + ((float)rnd.NextDouble() * 2f - 1f), 0);
            go.transform.localScale = Vector3.one * sc;
            if (mat != null) Assign(go, mat);
            Vector2 lotC = A + axis * (tcur + wLot * 0.5f) + inw * 4.5f;
            go.transform.position = new Vector3(lotC.x, 20, lotC.y);
            var rs = go.GetComponentsInChildren<Renderer>();
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            // 前面=街路縁の0.8m内側 / 走り中心=ロット中心
            float frontProj = b.center.x * outw.x + b.center.z * outw.y + Mathf.Abs(b.extents.x * outw.x) + Mathf.Abs(b.extents.z * outw.y);
            Vector2 fl = A + inw * 0.8f;
            float shiftOut = (fl.x * outw.x + fl.y * outw.y) - frontProj;
            float cProj = b.center.x * axis.x + b.center.z * axis.y;
            float shiftAlong = Vector2.Dot(A + axis * (tcur + wLot * 0.5f), axis) - cProj;
            go.transform.position += new Vector3(outw.x * shiftOut + axis.x * shiftAlong, 0, outw.y * shiftOut + axis.y * shiftAlong);
            var b2 = rs[0].bounds; foreach (var r in rs) b2.Encapsulate(r.bounds);
            float g = Ground(b2.center.x, b2.center.z);
            go.transform.position += new Vector3(0, (g - 0.06f) - b2.min.y, 0);
            // 店先の樽・桶(小店の脇にたまに)
            if (kind == "S2" && rnd.NextDouble() < 0.5)
            {
                string pp = rnd.NextDouble() < 0.5 ? EdoAssets.Eg.Shop01Taru : EdoAssets.Eg.Shop01Oke;
                var pa = AssetDatabase.LoadAssetAtPath<GameObject>(pp);
                if (pa != null)
                {
                    var pr = (GameObject)PrefabUtility.InstantiatePrefab(pa);
                    pr.name = "prop_" + made; pr.transform.SetParent(rowG, true);
                    pr.transform.localScale = Vector3.one * ES;
                    pr.transform.rotation = Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
                    Assign(pr, pp.Contains("taru") ? mTaru : mOke);
                    Vector2 ppos = A + axis * (tcur + wLot - 0.6f) + inw * 1.6f;
                    pr.transform.position = new Vector3(ppos.x, 20, ppos.y);
                    var rr = pr.GetComponentsInChildren<Renderer>();
                    var bb = rr[0].bounds; foreach (var r in rr) bb.Encapsulate(r.bounds);
                    pr.transform.position += new Vector3(ppos.x - bb.center.x, 0, ppos.y - bb.center.z);
                    var bb2 = rr[0].bounds; foreach (var r in rr) bb2.Encapsulate(r.bounds);
                    float gg = Ground(bb2.center.x, bb2.center.z);
                    pr.transform.position += new Vector3(0, gg - bb2.min.y, 0);
                }
            }
            made++;
            tcur += wLot + 0.35f;
        }
        // 裏手: 物干場(2本柱+竿) を ~14m 毎、その先に低木・下草(草花植付地)
        var wood = new Material(Shader.Find("Universal Render Pipeline/Lit")); wood.color = new Color(0.42f, 0.31f, 0.20f);
        int nMono = Mathf.Max(1, Mathf.RoundToInt((t1 - t0) / 14f));
        for (int i = 0; i < nMono; i++)
        {
            float tt = t0 + (t1 - t0) * ((i + 0.5f) / nMono) + ((float)rnd.NextDouble() * 3f - 1.5f);
            Vector2 c = A + axis * tt + inw * (12.0f + (float)rnd.NextDouble() * 2f);
            if (!EdoGeom.PIP(poly, c)) continue;
            var g = new GameObject("Monohoshi_" + i);
            g.transform.SetParent(backG, false);
            g.transform.position = new Vector3(c.x, Ground(c.x, c.y), c.y);
            g.transform.rotation = Quaternion.Euler(0, ryFace + 90f + ((float)rnd.NextDouble() * 16f - 8f), 0);
            for (int k = 0; k < 2; k++)
            {
                var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                post.name = "post" + k; post.transform.SetParent(g.transform, false);
                post.transform.localScale = new Vector3(0.09f, 0.95f, 0.09f);
                post.transform.localPosition = new Vector3(k == 0 ? -1.7f : 1.7f, 0.95f, 0);
                post.GetComponent<Renderer>().sharedMaterial = wood;
            }
            var bar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            bar.name = "bar"; bar.transform.SetParent(g.transform, false);
            bar.transform.localScale = new Vector3(0.05f, 1.75f, 0.05f);
            bar.transform.localEulerAngles = new Vector3(0, 0, 90);
            bar.transform.localPosition = new Vector3(0, 1.78f, 0);
            bar.GetComponent<Renderer>().sharedMaterial = wood;
            Undo.RegisterCreatedObjectUndo(g, "monohoshi");
        }
        // 草花植付地: 低い下草・刈込を裏縁に
        string[] plants = {
            EdoAssets.JG.Boxwood01,
            EdoAssets.JG.Fern01 };
        int nPl = Mathf.Max(2, Mathf.RoundToInt((t1 - t0) / 7f));
        for (int i = 0; i < nPl; i++)
        {
            float tt = t0 + (t1 - t0) * ((float)rnd.NextDouble());
            Vector2 c = A + axis * tt + inw * (15.5f + (float)rnd.NextDouble() * 2.5f);
            if (!EdoGeom.PIP(poly, c)) continue;
            string pp = plants[rnd.Next(plants.Length)];
            var pa = AssetDatabase.LoadAssetAtPath<GameObject>(pp);
            if (pa == null) continue;
            var pl = (GameObject)PrefabUtility.InstantiatePrefab(pa);
            pl.name = "Kusabana_" + i; pl.transform.SetParent(backG, true);
            pl.transform.position = new Vector3(c.x, Ground(c.x, c.y) - 0.03f, c.y);
            pl.transform.rotation = Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
            pl.transform.localScale = Vector3.one * (0.8f + 0.5f * (float)rnd.NextDouble());
        }
        return groupName + " row rebuilt: " + made + " buildings";
    }

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

    // ---------- Stage 3: splat (前=踏み固め土 / 裏=草花畑の緑) ----------
    public static string Stage3_Splat()
    {
        var t = T(); var td = t.terrainData;
        int res = td.alphamapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / res;
        float x0 = -560, x1 = -360, z0 = 405, z1 = 580;
        int ix0 = Mathf.Max(0, Mathf.FloorToInt((x0 - tp.x) / cell)), ix1 = Mathf.Min(res - 1, Mathf.CeilToInt((x1 - tp.x) / cell));
        int iz0 = Mathf.Max(0, Mathf.FloorToInt((z0 - tp.z) / cell)), iz1 = Mathf.Min(res - 1, Mathf.CeilToInt((z1 - tp.z) / cell));
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A2 = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        foreach (var poly in new[] { SeiryujiPoly, NagaichoPoly })
        {
            Vector2 A = poly[0], B = poly[1];
            Vector2 axis = (B - A).normalized;
            Vector2 inw = new Vector2(-axis.y, axis.x);
            if (!EdoGeom.PIP(poly, A + axis * 20f + inw * 5f)) inw = -inw;
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                    float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                    var p = new Vector2(wx, wz);
                    if (!EdoGeom.PIP(poly, p)) continue;
                    float depth = Vector2.Dot(p - A, inw);
                    float noise = Mathf.PerlinNoise(wx * 0.13f, wz * 0.13f);
                    float bare, grass, dirt;
                    if (depth < 11f) { bare = Mathf.Lerp(0.45f, 0.62f, noise); grass = 0.08f; dirt = 1f - bare - grass; }  // 町屋・店前
                    else { grass = Mathf.Lerp(0.45f, 0.68f, noise); bare = 0.10f; dirt = 1f - grass - bare; }              // 物干場・草花畑
                    for (int l = 0; l < L; l++) A2[zz, xx, l] = 0;
                    A2[zz, xx, 0] = dirt; A2[zz, xx, 1] = grass; A2[zz, xx, 2] = bare;
                    changed++;
                }
        }
        td.SetAlphamaps(ix0, iz0, A2);
        return "daichi splat cells=" + changed;
    }
}
