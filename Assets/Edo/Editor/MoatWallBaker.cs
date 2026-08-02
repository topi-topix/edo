using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// MoatWall（内堀）の生成処理。**56タイル横断**で掘削し、背面プロファイルで陸側を土充填、
/// 石垣モジュールを輪郭に沿って配置、最後に水面を張る。
/// 断面は世界座標(x,z)の純関数なのでタイル境界でも高さが一致（継ぎ目なし）。
/// </summary>
public static class MoatWallBaker
{
    // ---- 掘削 ----
    public static void Carve(MoatWall wall)
    {
        if (wall == null || wall.outline == null || wall.outline.Count < 3) { Debug.LogWarning("[Moat] outlineが3点未満"); return; }

        // 既存の掘削を戻してからやり直す（冪等）
        Restore(wall);

        var poly = ToPoly2(wall.outline);
        // 影響範囲 bbox（背面プロファイル全幅＋ブレンド＋余白）
        float back = wall.wallFootprint + wall.backBlend + 2f;
        foreach (var s in wall.backProfile) back += s.width;
        float minX = 1e9f, maxX = -1e9f, minZ = 1e9f, maxZ = -1e9f;
        foreach (var v in poly) { minX = Mathf.Min(minX, v.x); maxX = Mathf.Max(maxX, v.x); minZ = Mathf.Min(minZ, v.y); maxZ = Mathf.Max(maxZ, v.y); }
        minX -= back; maxX += back; minZ -= back; maxZ += back;

        Undo.RecordObject(wall, "Carve Moat");
        wall.snaps = new List<TileCarveSnap>();
        int tilesTouched = 0;

        foreach (var terr in Terrain.activeTerrains)
        {
            var td = terr.terrainData; if (td == null) continue;
            Vector3 tp = terr.transform.position; Vector3 size = td.size;
            // タイルがbboxと重なるか
            if (tp.x > maxX || tp.x + size.x < minX || tp.z > maxZ || tp.z + size.z < minZ) continue;
            int R = td.heightmapResolution;
            float cellX = size.x / (R - 1), cellZ = size.z / (R - 1);
            int gx0 = Mathf.Clamp(Mathf.FloorToInt((minX - tp.x) / cellX), 0, R - 1);
            int gx1 = Mathf.Clamp(Mathf.CeilToInt((maxX - tp.x) / cellX), 0, R - 1);
            int gz0 = Mathf.Clamp(Mathf.FloorToInt((minZ - tp.z) / cellZ), 0, R - 1);
            int gz1 = Mathf.Clamp(Mathf.CeilToInt((maxZ - tp.z) / cellZ), 0, R - 1);
            int w = gx1 - gx0 + 1, h = gz1 - gz0 + 1;
            if (w <= 1 || h <= 1) continue;

            var H = td.GetHeights(gx0, gz0, w, h);
            // スナップショット（復元用）
            var snap = new TileCarveSnap { terrainName = terr.name, x = gx0, z = gz0, w = w, h = h, heights = new float[w * h] };
            for (int z = 0; z < h; z++) for (int x = 0; x < w; x++) snap.heights[z * w + x] = H[z, x];

            for (int z = 0; z < h; z++)
            {
                float wz = tp.z + (gz0 + z) * cellZ;
                for (int x = 0; x < w; x++)
                {
                    float wx = tp.x + (gx0 + x) * cellX;
                    float origY = H[z, x] * size.y + tp.y;
                    float targetY = CrossSectionY(wall, poly, new Vector2(wx, wz), origY);
                    H[z, x] = Mathf.Clamp01((targetY - tp.y) / size.y);
                }
            }
            td.SetHeights(gx0, gz0, H);
            wall.snaps.Add(snap);
            tilesTouched++;
        }
        EditorUtility.SetDirty(wall);
        Debug.Log($"[Moat] 掘削完了: {tilesTouched} タイルに適用（水面は最後に『水面 Water』で張る）");
    }

    /// <summary>輪郭に直交する断面高さ(世界Y)を返す。</summary>
    static float CrossSectionY(MoatWall wall, List<Vector2> poly, Vector2 P, float origY)
    {
        bool inside; float s = DistToPoly(P, poly, out inside);
        float bedY = wall.MoatBedY, topY = wall.TopY;
        if (inside) return bedY;                      // 水側＝濠底
        if (s < wall.wallFootprint) return bedY;      // 石垣footprint下＝掘り下げ

        float ls = s - wall.wallFootprint;            // 背面プロファイル内の距離
        float acc = 0f, stepY = topY;
        foreach (var st in wall.backProfile)
        {
            stepY = topY + st.dHeight;
            if (ls < acc + st.width) return stepY;    // この段（raiseもcutも）＝平場/犬走り
            acc += st.width;
        }
        float bs = ls - acc;                          // プロファイル末端からの距離
        if (bs < wall.backBlend) return Mathf.Lerp(stepY, origY, bs / wall.backBlend); // 既存地形へブレンド
        return origY;                                 // 範囲外＝手つかず
    }

    /// <summary>点Pから多角形境界までの最短距離（inside=内包）。</summary>
    static float DistToPoly(Vector2 P, List<Vector2> poly, out bool inside)
    {
        inside = WaterGeom.PointInPoly(P, poly);
        float best = 1e9f; int n = poly.Count;
        for (int i = 0; i < n; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % n], ab = b - a;
            float t = Mathf.Clamp01(Vector2.Dot(P - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-6f));
            float d = Vector2.Distance(P, a + ab * t);
            if (d < best) best = d;
        }
        return best;
    }

    // ---- 復元 ----
    public static void Restore(MoatWall wall)
    {
        if (wall == null || wall.snaps == null || wall.snaps.Count == 0) return;
        foreach (var snap in wall.snaps)
        {
            var terr = FindTerrain(snap.terrainName); if (terr == null) continue;
            var td = terr.terrainData;
            var H = new float[snap.h, snap.w];
            for (int z = 0; z < snap.h; z++) for (int x = 0; x < snap.w; x++) H[z, x] = snap.heights[z * snap.w + x];
            td.SetHeights(snap.x, snap.z, H);
        }
        wall.snaps = new List<TileCarveSnap>();
        EditorUtility.SetDirty(wall);
    }

    static Terrain FindTerrain(string name)
    {
        foreach (var t in Terrain.activeTerrains) if (t.name == name) return t;
        return null;
    }

    // ---- 水面 ----
    public static void BuildWater(MoatWall wall)
    {
        if (wall.outline.Count < 3) return;
        var child = wall.transform.Find("MoatWater");
        GameObject go = child != null ? child.gameObject : new GameObject("MoatWater");
        if (child == null) { go.transform.SetParent(wall.transform, false); }
        var mf = go.GetComponent<MeshFilter>(); if (mf == null) mf = go.AddComponent<MeshFilter>();
        var mr = go.GetComponent<MeshRenderer>(); if (mr == null) mr = go.AddComponent<MeshRenderer>();

        var poly = WaterGeom.Chaikin(wall.outline, 2);
        var poly2 = new List<Vector2>(); foreach (var p in poly) poly2.Add(new Vector2(p.x, p.z));
        if (WaterGeom.SignedArea(poly2) < 0f) poly2.Reverse();
        var tris = WaterGeom.EarClip(poly2);
        var verts = new List<Vector3>(); foreach (var v in poly2) verts.Add(new Vector3(v.x, wall.waterY, v.y));

        var mesh = mf.sharedMesh;
        bool isAsset = mesh != null && AssetDatabase.Contains(mesh);
        if (mesh == null) mesh = new Mesh { name = "MoatWaterMesh" };
        mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
        mesh.Clear(); mesh.SetVertices(verts); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateBounds();
        mf.sharedMesh = mesh;
        if (mr.sharedMaterial == null)
        {
            var wsh = Shader.Find("Edo/Water") ?? Shader.Find("Universal Render Pipeline/Lit");
            mr.sharedMaterial = new Material(wsh);
        }
        if (!isAsset) EditorUtility.SetDirty(go);
    }

    // ---- 石垣配置（コーナー対応：角に出隅/入隅を差し込み、直線はコーナー分詰めて敷く） ----
    public static void PlaceWalls(MoatWall wall)
    {
        var set = wall.modules;
        if (set == null) { Debug.LogWarning("[Moat] MoatModuleSet 未設定。配置スキップ（掘削のみ）"); return; }
        var ol = wall.outline; int n = ol.Count;
        if (n < 3) { Debug.LogWarning("[Moat] outlineが3点未満"); return; }

        var old = wall.transform.Find("MoatIshigaki");
        if (old != null) Object.DestroyImmediate(old.gameObject);
        var root = new GameObject("MoatIshigaki");
        root.transform.SetParent(wall.transform, false);

        var poly = ToPoly2(ol);
        float baseY = wall.MoatBedY;
        float wallHeight = wall.topHeight + wall.moatDepth;

        // 各辺の方向と内向き(水側)法線
        var dir = new Vector2[n]; var inward = new Vector2[n];
        for (int i = 0; i < n; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % n];
            Vector2 d = b - a; float len = d.magnitude; d = len < 1e-4f ? Vector2.right : d / len;
            dir[i] = d;
            Vector2 perp = new Vector2(d.y, -d.x);
            bool inW; DistToPoly((a + b) * 0.5f + perp * 0.5f, poly, out inW);
            inward[i] = inW ? perp : -perp;
        }

        // 多角形の巻き方向（水は輪郭の内側）
        float area = WaterGeom.SignedArea(poly);

        // 頂点iのコーナー判定（辺 i-1 と 辺 i の間）
        var isCorner = new bool[n]; var convex = new bool[n];
        for (int i = 0; i < n; i++)
        {
            Vector2 inD = dir[(i - 1 + n) % n], outD = dir[i];
            float turn = Vector2.Angle(inD, outD);
            if (turn < set.turnThresholdDeg) continue;
            isCorner[i] = true;
            float cross = inD.x * outD.y - inD.y * outD.x;             // 曲がりの向き
            // 水は輪郭の内側。石垣は水に面する（部屋の内壁と同じ）ので:
            //  幾何的に凸な頂点(巻き方向と同じ曲がり=矩形の角)＝石垣は【入隅(凹)】
            //  水へ張り出す再入頂点(逆向きの曲がり)＝石垣は【出隅(凸)】
            // convex[i]=true は「出隅(desumi)を使う」の意
            convex[i] = Mathf.Sign(cross) != Mathf.Sign(area);
        }

        int placedS = 0, placedC = 0;
        // コーナー
        for (int i = 0; i < n; i++)
        {
            if (!isCorner[i]) continue;
            var prefab = convex[i] ? set.cornerConvex : set.cornerConcave;
            if (prefab == null) prefab = set.cornerConvex != null ? set.cornerConvex : set.cornerConcave;
            if (prefab == null) continue;
            Vector3 fwd;
            if (convex[i])
            {
                // 出隅(凸): 2面(+Z,+X)を両壁の水側法線へ。LookRotation(入辺inward)で +Z→入辺, +X→出辺
                Vector2 inwIn = inward[(i - 1 + n) % n];
                fwd = new Vector3(inwIn.x, 0, inwIn.y);
            }
            else
            {
                // 入隅(凹): X対称・開口は+Z。開口を水側バイセクタへ向ける
                Vector2 bis = inward[(i - 1 + n) % n] + inward[i];
                bis = bis.sqrMagnitude < 1e-4f ? inward[i] : bis.normalized;
                fwd = new Vector3(bis.x, 0, bis.y);
            }
            var rot = Quaternion.LookRotation(fwd, Vector3.up) * Quaternion.Euler(convex[i] ? set.convexEuler : set.concaveEuler);
            var p = poly[i];
            var inst = Inst(prefab, root.transform);
            inst.transform.SetPositionAndRotation(new Vector3(p.x, baseY, p.y) + rot * set.cornerPosOffset, rot);
            placedC++;
        }

        // 直線（コーナー分だけ端を詰める）
        var straight = set.PickStraight(wallHeight, out _);
        if (straight != null)
        for (int i = 0; i < n; i++)
        {
            Vector2 a = poly[i], b = poly[(i + 1) % n];
            float startInset = isCorner[i] ? set.cornerInset : 0f;
            float endInset = isCorner[(i + 1) % n] ? set.cornerInset : 0f;
            float full = Vector2.Distance(a, b);
            float runL = full - startInset - endInset;
            if (runL < set.runLength * 0.5f) continue;
            Vector2 s = a + dir[i] * startInset;
            int count = Mathf.Max(1, Mathf.RoundToInt(runL / set.runLength));
            float step = runL / count;
            var fwd = new Vector3(inward[i].x, 0, inward[i].y);
            var rot = Quaternion.LookRotation(fwd, Vector3.up) * Quaternion.Euler(set.eulerOffset);
            for (int k = 0; k < count; k++)
            {
                Vector2 p = s + dir[i] * step * (k + 0.5f);
                var inst = Inst(straight, root.transform);
                inst.transform.SetPositionAndRotation(new Vector3(p.x, baseY, p.y) + rot * set.posOffset, rot);
                placedS++;
            }
        }
        Debug.Log($"[Moat] 石垣配置: 直線{placedS} コーナー{placedC}（校正: eulerOffset / convexEuler / concaveEuler / cornerPosOffset）");
    }

    static GameObject Inst(GameObject prefab, Transform parent)
    {
        var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
        if (inst == null) inst = Object.Instantiate(prefab, parent);
        return inst;
    }

    static List<Vector2> ToPoly2(List<Vector3> ol)
    {
        var p = new List<Vector2>(ol.Count);
        foreach (var v in ol) p.Add(new Vector2(v.x, v.z));
        return p;
    }
}
