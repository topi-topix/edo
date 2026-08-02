using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// ブックマーク#1の指示にもとづく「石垣の堰」を、輪郭に沿った連続勾配のメッシュで生成する。
/// ② 方式: 地形ハイトマップ(2m格子)を掘るのではなく、石垣メッシュを輪郭ぴったりに立てるので
///         壁面は格子と無関係に滑らか(カクカクしない)。地形は足元に穴を開けて石垣を邪魔しない。
///
/// ・堤体(1-2-3-4): 四角形を天端→基部へ外側に勾配をつけて押し出した石垣の塊(天端は歩ける平面)。
/// ・護岸(3-5-6): 水路(東)向きの片面石垣。同じ勾配押し出しで薄い塊として作る。
/// ・低い湖側(海抜-1m)に高い石垣面が出て、高い水路側(海抜6m)は水位が天端近く=本物の堰の見え方。
///
/// メニュー: Edo ▸ 建造 ▸ 石垣の堰を作る
///   再実行すると作り直す(グループごと置換)。数値は下の定数で微調整。
/// </summary>
public class EdoSekiBuilder : EditorWindow
{
    // ---- 調整パラメータ ----
    const float CREST = 6.5f;     // 天端(石垣上端)のワールドY = 海抜6.5m
    const float BASE_Y = -5.0f;   // 基部(埋まる底)のワールドY = 海抜-5m
    const float SPREAD = 2.8f;    // 反りの最大張り出し(基部)。史実の扇の勾配の総バッター量(m)
    const int RINGS = 7;          // 面の縦分割(反りの曲線をなめらかに)
    const float SORI_P = 1.6f;    // 反りの曲率指数(>1で天端付近ほぼ垂直・基部ほど勾配増)
    const float REV_THICK = 2.4f; // 護岸(3-5-6)の陸側の厚み(m)
    const float UV_SCALE = 0.32f; // 石垣テクスチャの繰り返し(小=大きい石)
    const bool FLIP = false;      // 面が裏返る(黒い)場合 true

    const string GroupName = "Edo_Ishigaki_Seki";
    const string MatPath = "Assets/Edo/Models/M_ishigaki_face.mat";
    const string MeshDir = "Assets/Edo/Water"; // 生成メッシュ保存先

    // ブックマーク#1 のマーク1-6 (world x,z)
    static readonly Vector2[] P = {
        new Vector2(47.2f, 387.6f), // 1
        new Vector2(40.7f, 373.1f), // 2
        new Vector2(49.5f, 369.5f), // 3
        new Vector2(55.9f, 384.5f), // 4
        new Vector2(59.7f, 364.4f), // 5
        new Vector2(53.0f, 350.1f), // 6
    };
    static readonly Vector2 ChannelC = new Vector2(208.0f, 383.1f); // 水路(東)の中心

    [MenuItem("Edo/建造/石垣の堰を作る")]
    static void Build()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
        if (mat == null) { Debug.LogError("[Seki] material not found: " + MatPath); return; }

        // 既存グループを置換
        var old = GameObject.Find(GroupName);
        if (old != null) Object.DestroyImmediate(old);
        var grp = new GameObject(GroupName);

        // --- 堤体 1-2-3-4 ---
        var body = new List<Vector2> { P[0], P[1], P[2], P[3] };
        MakeFrustum("Seki_Body", body, grp, mat);

        // --- 護岸 3-5-6 (片面、水路=東向き) ---
        var line = new List<Vector2> { P[2], P[4], P[5] };
        var rev = OneSidedFootprint(line, ChannelC, REV_THICK);
        MakeFrustum("Seki_Revet", rev, grp, mat);

        // 地形: 水側を掘って石を出す／陸側の端を天端まで埋める
        // (穴は不要: 内側の地形は天端より低く石垣に囲まれて見えない。穴は明るい抜けの原因になる)
        IntegrateTerrain(new List<List<Vector2>> { body, rev });

        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
            UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        Selection.activeGameObject = grp;
        Debug.Log("[Seki] built. crest=" + CREST + " base=" + BASE_Y + " spread=" + SPREAD);
    }

    /// <summary>片面壁の底面ポリゴン: 線を陸側(水と反対)へ厚みぶんオフセットして閉じる。</summary>
    static List<Vector2> OneSidedFootprint(List<Vector2> line, Vector2 waterCenter, float thick)
    {
        var back = new List<Vector2>();
        foreach (var p in line)
        {
            Vector2 land = (p - waterCenter).normalized; // 水から離れる向き
            back.Add(p + land * thick);
        }
        var poly = new List<Vector2>(line);
        for (int i = back.Count - 1; i >= 0; i--) poly.Add(back[i]);
        return poly;
    }

    /// <summary>天端ポリゴン(CCW/CW自動)を、外側に勾配をつけて基部へ押し出した石垣メッシュ。</summary>
    static void MakeFrustum(string name, List<Vector2> topPoly, GameObject parent, Material mat)
    {
        int n = topPoly.Count;
        // 重心
        Vector2 c = Vector2.zero; foreach (var p in topPoly) c += p; c /= n;
        // 符号付き面積でCCW(上から見て)に正規化
        float area = 0f;
        for (int i = 0; i < n; i++) { var a = topPoly[i]; var b = topPoly[(i + 1) % n]; area += a.x * b.y - b.x * a.y; }
        var poly = new List<Vector2>(topPoly);
        if (area < 0f) poly.Reverse(); // CCW(XZ, 上から)へ

        var verts = new List<Vector3>();
        var uvs = new List<Vector2>();
        var tris = new List<int>();
        float wallH = CREST - BASE_Y;

        // 側面: 各辺を RINGS 段の帯で作り、外側張り出しを prof(v)=SPREAD*pow(v,SORI_P) にして
        //       反り(扇の勾配)の凹曲線を出す。天端付近ほぼ垂直、基部ほど勾配が増す。
        for (int i = 0; i < n; i++)
        {
            int j = (i + 1) % n;
            Vector2 outI = (poly[i] - c).normalized;
            Vector2 outJ = (poly[j] - c).normalized;
            float run = (poly[j] - poly[i]).magnitude;
            int baseIdx = verts.Count;
            for (int r = 0; r < RINGS; r++)
            {
                float v = (float)r / (RINGS - 1);
                float off = SPREAD * Mathf.Pow(v, SORI_P);
                float y = Mathf.Lerp(CREST, BASE_Y, v);
                Vector2 pi = poly[i] + outI * off;
                Vector2 pj = poly[j] + outJ * off;
                verts.Add(new Vector3(pi.x, y, pi.y));
                verts.Add(new Vector3(pj.x, y, pj.y));
                uvs.Add(new Vector2(0, v * wallH * UV_SCALE));
                uvs.Add(new Vector2(run * UV_SCALE, v * wallH * UV_SCALE));
            }
            for (int r = 0; r < RINGS - 1; r++)
            {
                int a0 = baseIdx + r * 2, a1 = baseIdx + r * 2 + 1;
                int b0 = baseIdx + (r + 1) * 2, b1 = baseIdx + (r + 1) * 2 + 1;
                // 外向き: (top_i,bot_i,top_j)+(top_j,bot_i,bot_j)
                if (!FLIP) tris.AddRange(new[] { a0, b0, a1, a1, b0, b1 });
                else tris.AddRange(new[] { a0, a1, b0, a1, b1, b0 });
            }
        }

        // 天端キャップ(上向き): CCWなら (0, i+1, i)
        int capBase = verts.Count;
        for (int i = 0; i < n; i++) { verts.Add(new Vector3(poly[i].x, CREST, poly[i].y)); uvs.Add(new Vector2(poly[i].x, poly[i].y) * UV_SCALE); }
        for (int i = 1; i < n - 1; i++)
        {
            if (!FLIP) tris.AddRange(new[] { capBase, capBase + i + 1, capBase + i });
            else tris.AddRange(new[] { capBase, capBase + i, capBase + i + 1 });
        }

        var mesh = new Mesh { name = name + "_mesh", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
        mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();

        string mp = MeshDir + "/" + name + "_mesh.asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(mp);
        if (existing != null) { EditorUtility.CopySerialized(mesh, existing); mesh = existing; }
        else AssetDatabase.CreateAsset(mesh, mp);
        AssetDatabase.SaveAssets();

        var go = new GameObject(name);
        go.transform.SetParent(parent.transform);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        go.AddComponent<MeshRenderer>().sharedMaterial = mat;
        var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = mesh;
    }

    /// <summary>
    /// 石垣の各辺を「水側」か「陸側(端)」に分類し、水側の地形を水面下まで掘って石を出し、
    /// 陸側の地形を天端まで上げて端を埋める。EdoIshigakiFit の Apply と同じ思想。
    /// </summary>
    static void IntegrateTerrain(List<List<Vector2>> polys)
    {
        var terr = Terrain.activeTerrain; if (terr == null) return;
        var td = terr.terrainData; var tp = terr.transform.position; var ts = td.size;
        int res = td.heightmapResolution;
        const float BAND = 8f;     // 陸側(埋め)の帯の幅(m)
        const float WBAND = 14f;   // 水側(掘って石を出す)の帯の幅(m)。広め=面が広く出る
        const float FEATHER = 1.6f; // 帯の外へなだらかに戻す倍率
        const float FOOT_BELOW = 4f; // 水面下どれだけ掘るか
        const float TOP_DROP = 0.4f; // 陸側の襟高さを天端より下げる量(天端石を出す)
        const float COLLAR = 3.5f;  // 陸側で天端レベルに均す襟の幅(m)

        // 水域ポリゴン(world XZ)を集める
        var waters = new List<(List<Vector2> poly, float y)>();
        foreach (var wb in Object.FindObjectsByType<WaterBody>(FindObjectsSortMode.None))
        {
            var wt = wb.transform; var wp = new List<Vector2>();
            foreach (var p in wb.outline) { var wpt = wt.TransformPoint(p); wp.Add(new Vector2(wpt.x, wpt.z)); }
            waters.Add((wp, wb.waterY));
        }

        // 全辺を (a,b,outwardNormal,水side分類) にする
        var segs = new List<(Vector2 a, Vector2 b, Vector2 nout, bool isWater, float carveY)>();
        foreach (var poly in polys)
        {
            Vector2 c = Vector2.zero; foreach (var p in poly) c += p; c /= poly.Count;
            for (int i = 0; i < poly.Count; i++)
            {
                Vector2 a = poly[i], b = poly[(i + 1) % poly.Count];
                Vector2 mid = (a + b) * 0.5f;
                Vector2 dir = (b - a).normalized;
                Vector2 nout = new Vector2(-dir.y, dir.x);
                if (Vector2.Dot(nout, mid - c) < 0f) nout = -nout; // 外向きへ
                Vector2 probe = mid + nout * 4f;
                bool isWater = false; float carveY = 0f;
                foreach (var wtr in waters)
                    if (PointInPoly(probe, wtr.poly)) { isWater = true; carveY = wtr.y - FOOT_BELOW; break; }
                segs.Add((a, b, nout, isWater, carveY));
            }
        }

        // 影響bbox
        float minx = 1e9f, maxx = -1e9f, minz = 1e9f, maxz = -1e9f;
        foreach (var poly in polys) foreach (var p in poly)
        { minx = Mathf.Min(minx, p.x); maxx = Mathf.Max(maxx, p.x); minz = Mathf.Min(minz, p.y); maxz = Mathf.Max(maxz, p.y); }
        float pad = BAND * FEATHER + 4f; minx -= pad; maxx += pad; minz -= pad; maxz += pad;
        int gx0 = Mathf.Clamp(Mathf.FloorToInt((minx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int gx1 = Mathf.Clamp(Mathf.CeilToInt((maxx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int gz0 = Mathf.Clamp(Mathf.FloorToInt((minz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int gz1 = Mathf.Clamp(Mathf.CeilToInt((maxz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int w = gx1 - gx0 + 1, h = gz1 - gz0 + 1;
        Undo.RegisterCompleteObjectUndo(td, "Seki integrate terrain");
        var H = td.GetHeights(gx0, gz0, w, h); // [z, x]

        float crestN = (CREST - TOP_DROP - tp.y) / ts.y;
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = tp.x + (float)(gx0 + x) / (res - 1) * ts.x;
                float wz = tp.z + (float)(gz0 + z) / (res - 1) * ts.z;
                var col = new Vector2(wx, wz);
                // どのフットプリント内でもない前提で最近辺を探す(内側は穴で消える)
                bool inside = false; foreach (var poly in polys) if (PointInPoly(col, poly)) { inside = true; break; }
                if (inside) continue;

                // 水側の辺と陸側の辺を別々に最近点評価し、水側(石を出す)を優先する。
                // これで角の近くでも陸側の埋めが面に被らず、石垣面が全幅で出る。
                float wD = 1e9f, wSide = 0f, wCarveY = 0f;
                float lD = 1e9f, lSide = 0f;
                for (int i = 0; i < segs.Count; i++)
                {
                    var s = segs[i]; Vector2 ab = s.b - s.a;
                    float t = Mathf.Clamp01(Vector2.Dot(col - s.a, ab) / Mathf.Max(1e-4f, ab.sqrMagnitude));
                    Vector2 q = s.a + ab * t; float d = Vector2.Distance(col, q);
                    float side = Vector2.Dot(col - q, s.nout);
                    if (s.isWater) { if (d < wD) { wD = d; wSide = side; wCarveY = s.carveY; } }
                    else { if (d < lD) { lD = d; lSide = side; } }
                }

                // 1) 水側の外側(石の前)は必ず掘る(優先)
                if (wSide > 0f && wD <= WBAND * FEATHER)
                {
                    float carveN = (wCarveY - tp.y) / ts.y;
                    float tgt = (wD <= WBAND) ? carveN
                        : Mathf.Lerp(carveN, H[z, x], Mathf.InverseLerp(WBAND, WBAND * FEATHER, wD));
                    if (tgt < H[z, x]) H[z, x] = tgt;
                    continue;
                }
                // 2) それ以外で陸側の外側(端)は天端の襟レベルに均す
                if (lSide > 0f)
                {
                    float tgt = (lD <= COLLAR) ? crestN
                        : Mathf.Lerp(crestN, H[z, x], Mathf.InverseLerp(COLLAR, BAND * FEATHER, lD));
                    H[z, x] = tgt;
                }
            }
        td.SetHeights(gx0, gz0, H); terr.Flush();
    }

    /// <summary>複数フットプリントの内側の地形セルに穴を開ける(石垣が地形に埋もれない)。</summary>
    static void PunchHoles(List<List<Vector2>> polys, float inset)
    {
        var terr = Terrain.activeTerrain; if (terr == null) return;
        var td = terr.terrainData; var tp = terr.transform.position; var ts = td.size;
        int hres = td.holesResolution;
        // 影響範囲bbox
        float minx = 1e9f, maxx = -1e9f, minz = 1e9f, maxz = -1e9f;
        foreach (var poly in polys) foreach (var p in poly)
        { minx = Mathf.Min(minx, p.x); maxx = Mathf.Max(maxx, p.x); minz = Mathf.Min(minz, p.y); maxz = Mathf.Max(maxz, p.y); }
        int gx0 = Mathf.Clamp(Mathf.FloorToInt((minx - tp.x) / ts.x * hres), 0, hres - 1);
        int gx1 = Mathf.Clamp(Mathf.CeilToInt((maxx - tp.x) / ts.x * hres), 0, hres - 1);
        int gz0 = Mathf.Clamp(Mathf.FloorToInt((minz - tp.z) / ts.z * hres), 0, hres - 1);
        int gz1 = Mathf.Clamp(Mathf.CeilToInt((maxz - tp.z) / ts.z * hres), 0, hres - 1);
        int w = gx1 - gx0 + 1, h = gz1 - gz0 + 1;
        var holes = td.GetHoles(gx0, gz0, w, h); // 注意: 配列は [x, z] 順 (GetHeightsの [z,x] とは逆)
        for (int z = 0; z < h; z++)
            for (int x = 0; x < w; x++)
            {
                float wx = tp.x + (gx0 + x + 0.5f) / hres * ts.x;
                float wz = tp.z + (gz0 + z + 0.5f) / hres * ts.z;
                var c = new Vector2(wx, wz);
                foreach (var poly in polys)
                    if (PointInPolyInset(c, poly, inset)) { holes[x, z] = false; break; }
            }
        td.SetHoles(gx0, gz0, holes);
        terr.Flush();
    }

    static bool PointInPolyInset(Vector2 p, List<Vector2> poly, float inset)
    {
        // 内側にinsetした判定: 素朴に元ポリゴンで内外判定し、辺からの距離>inset を要求
        if (!PointInPoly(p, poly)) return false;
        float md = 1e9f;
        for (int i = 0; i < poly.Count; i++)
        {
            var a = poly[i]; var b = poly[(i + 1) % poly.Count];
            md = Mathf.Min(md, DistToSeg(p, a, b));
        }
        return md > inset;
    }

    static bool PointInPoly(Vector2 p, List<Vector2> poly)
    {
        bool inside = false; int n = poly.Count;
        for (int i = 0, j = n - 1; i < n; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x))
                inside = !inside;
        return inside;
    }

    static float DistToSeg(Vector2 p, Vector2 a, Vector2 b)
    {
        Vector2 ab = b - a; float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(1e-5f, ab.sqrMagnitude));
        return Vector2.Distance(p, a + ab * t);
    }
}
