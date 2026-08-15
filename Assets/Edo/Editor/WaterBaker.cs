using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>WaterBody の水面メッシュ生成と地形の掘り込み（＋縮小時の復元・拡張時のスナップショット拡張）を行うエディタ処理。</summary>
public static class WaterBaker
{
    static readonly Color DeepC = new Color(0.13f, 0.32f, 0.40f);
    static readonly Color ShallowC = new Color(0.28f, 0.50f, 0.55f);
    const float Margin = 150f;   // スナップショットの余白(m)

    /// <summary>なぞった点から新しい編集可能な水域を作る。</summary>
    public static WaterBody Create(List<Vector3> outline, float depth)
    {
        var parent = GameObject.Find("Water"); if (parent == null) parent = new GameObject("Water");
        var go = new GameObject("Water_" + System.DateTime.Now.ToString("HHmmss"));
        Undo.RegisterCreatedObjectUndo(go, "Create Water");
        go.transform.SetParent(parent.transform);
        var wb = go.AddComponent<WaterBody>();
        wb.outline = new List<Vector3>(outline);
        wb.depth = depth;
        var mat = new Material(Shader.Find("Edo/Water"));
        mat.SetColor("_DeepColor", DeepC); mat.SetColor("_ShallowColor", ShallowC);
        mat.SetFloat("_FresnelPower", 3.0f); mat.SetFloat("_Alpha", 0.8f);
        AssetDatabase.CreateAsset(mat, AssetDatabase.GenerateUniqueAssetPath("Assets/Edo/Water/" + go.name + ".mat"));
        go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        Recarve(wb);
        return wb;
    }

    /// <summary>
    /// 「他の水域が掘っているセル」のマスクを wb のスナップ領域の座標系で作る。
    /// スナップ領域は輪郭bbox+150mの矩形なので近くの水域どうしで平気で重なる。
    /// 復元/掘り直しはスナップ全域を書き戻すため、守らないと隣の池や堀の掘り込みを埋めてしまう。
    /// 自分の輪郭の内側は自分が掘るので対象外。該当なしなら null。
    /// </summary>
    static bool[,] OtherWaterMask(WaterBody self, Terrain terrain, List<Vector2> selfPoly)
    {
        var td = terrain.terrainData; var tt = terrain.transform;
        float px0 = tt.position.x, pz0 = tt.position.z, sx = td.size.x, sz = td.size.z;
        int res = td.heightmapResolution;
        bool[,] mask = null;

        foreach (var o in Object.FindObjectsByType<WaterBody>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (o == self || o.outline == null || o.outline.Count < 3) continue;
            var op = WaterGeom.SmoothTagged(o.outline, o.sharp, 2);
            var op2 = new List<Vector2>(op.Count);
            float minX = 1e9f, maxX = -1e9f, minZ = 1e9f, maxZ = -1e9f;
            foreach (var p in op)
            {
                op2.Add(new Vector2(p.x, p.z));
                minX = Mathf.Min(minX, p.x); maxX = Mathf.Max(maxX, p.x);
                minZ = Mathf.Min(minZ, p.z); maxZ = Mathf.Max(maxZ, p.z);
            }
            // 相手のbboxとスナップ領域の重なりだけ調べる（全域走査は重すぎる）
            int x0 = Mathf.Max(0, Mathf.FloorToInt((minX - px0) / sx * (res - 1)) - self.sX);
            int x1 = Mathf.Min(self.sW - 1, Mathf.CeilToInt((maxX - px0) / sx * (res - 1)) - self.sX);
            int z0 = Mathf.Max(0, Mathf.FloorToInt((minZ - pz0) / sz * (res - 1)) - self.sZ);
            int z1 = Mathf.Min(self.sH - 1, Mathf.CeilToInt((maxZ - pz0) / sz * (res - 1)) - self.sZ);
            if (x1 < x0 || z1 < z0) continue;

            for (int z = z0; z <= z1; z++)
                for (int x = x0; x <= x1; x++)
                {
                    float wx = px0 + (float)(self.sX + x) / (res - 1) * sx;
                    float wz = pz0 + (float)(self.sZ + z) / (res - 1) * sz;
                    var v = new Vector2(wx, wz);
                    if (!WaterGeom.PointInPoly(v, op2)) continue;
                    if (selfPoly != null && WaterGeom.PointInPoly(v, selfPoly)) continue;   // 自分の水域が優先
                    if (mask == null) mask = new bool[self.sH, self.sW];
                    mask[z, x] = true;
                }
        }
        return mask;
    }

    /// <summary>他の水域が掘っているセルを現況のまま残す（H を現在の地形高で上書き）。戻り値=守ったセル数。</summary>
    static int PreserveOtherWater(WaterBody wb, Terrain terrain, List<Vector2> selfPoly, float[,] H)
    {
        var mask = OtherWaterMask(wb, terrain, selfPoly);
        if (mask == null) return 0;
        var cur = terrain.terrainData.GetHeights(wb.sX, wb.sZ, wb.sW, wb.sH);
        int kept = 0;
        for (int z = 0; z < wb.sH; z++)
            for (int x = 0; x < wb.sW; x++)
                if (mask[z, x] && !Mathf.Approximately(H[z, x], cur[z, x])) { H[z, x] = cur[z, x]; kept++; }
        return kept;
    }

    /// <summary>outline から水面メッシュだけ再生成（ドラッグ時の即時反映用・掘り込みは触らない）。</summary>
    public static void RebuildSurface(WaterBody wb)
    {
        if (wb == null || wb.outline == null || wb.outline.Count < 3) return;
        var poly = WaterGeom.SmoothTagged(wb.outline, wb.sharp, 2);
        var poly2 = new List<Vector2>(poly.Count);
        foreach (var p in poly) poly2.Add(new Vector2(p.x, p.z));
        if (WaterGeom.SignedArea(poly2) < 0f) poly2.Reverse();
        var tris = WaterGeom.EarClip(poly2);
        var verts = new List<Vector3>(poly2.Count);
        foreach (var v in poly2) verts.Add(new Vector3(v.x, wb.waterY, v.y));

        var mf = wb.GetComponent<MeshFilter>();
        var mesh = mf.sharedMesh;
        bool isAsset = mesh != null && AssetDatabase.Contains(mesh);
        if (mesh == null) mesh = new Mesh { name = "WaterMesh" };
        mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
        mesh.Clear(); mesh.SetVertices(verts); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateBounds();
        mf.sharedMesh = mesh;
        if (isAsset) EditorUtility.SetDirty(mesh);
        else AssetDatabase.CreateAsset(mesh, AssetDatabase.GenerateUniqueAssetPath("Assets/Edo/Water/" + wb.gameObject.name + "_mesh.asset"));
    }

    /// <summary>
    /// スナップショット領域が現在の輪郭(bbox+余白)を覆っているか確認し、足りなければ拡張する。
    /// 新しく必要になった領域は「まだこの水域が掘っていない生の地形」として現在値を取り込む。
    /// 既存の領域は保存済みの値（掘る前の高さ）をそのまま保持する。
    /// </summary>
    static void EnsureSnapCovers(WaterBody wb, List<Vector2> poly2, Terrain terrain)
    {
        var td = terrain.terrainData; var tt = terrain.transform;
        float px0 = tt.position.x, pz0 = tt.position.z, sx = td.size.x, sz = td.size.z;
        int res = td.heightmapResolution;

        float minX = 1e9f, maxX = -1e9f, minZ = 1e9f, maxZ = -1e9f;
        foreach (var v in poly2) { minX = Mathf.Min(minX, v.x); maxX = Mathf.Max(maxX, v.x); minZ = Mathf.Min(minZ, v.y); maxZ = Mathf.Max(maxZ, v.y); }
        int needX0 = Mathf.Clamp(Mathf.FloorToInt((minX - Margin - px0) / sx * (res - 1)), 0, res - 1);
        int needX1 = Mathf.Clamp(Mathf.CeilToInt((maxX + Margin - px0) / sx * (res - 1)), 0, res - 1);
        int needZ0 = Mathf.Clamp(Mathf.FloorToInt((minZ - Margin - pz0) / sz * (res - 1)), 0, res - 1);
        int needZ1 = Mathf.Clamp(Mathf.CeilToInt((maxZ + Margin - pz0) / sz * (res - 1)), 0, res - 1);

        if (!wb.hasSnap)
        {
            wb.sX = needX0; wb.sZ = needZ0; wb.sW = needX1 - needX0 + 1; wb.sH = needZ1 - needZ0 + 1;
            var region0 = td.GetHeights(wb.sX, wb.sZ, wb.sW, wb.sH);
            var s0 = new float[wb.sW * wb.sH];
            for (int z = 0; z < wb.sH; z++) for (int x = 0; x < wb.sW; x++) s0[z * wb.sW + x] = region0[z, x];
            wb.snap = s0;
            wb.hasSnap = true;
            WaterSnapStore.Save(wb);      // ★ snap は非シリアライズ。書いたら必ず保存する
            return;
        }

        int curX1 = wb.sX + wb.sW - 1, curZ1 = wb.sZ + wb.sH - 1;
        if (needX0 >= wb.sX && needX1 <= curX1 && needZ0 >= wb.sZ && needZ1 <= curZ1) return; // 既に覆えている

        int newX0 = Mathf.Min(wb.sX, needX0), newX1 = Mathf.Max(curX1, needX1);
        int newZ0 = Mathf.Min(wb.sZ, needZ0), newZ1 = Mathf.Max(curZ1, needZ1);
        int newW = newX1 - newX0 + 1, newH = newZ1 - newZ0 + 1;

        var full = td.GetHeights(newX0, newZ0, newW, newH);   // 新規部分＝現在の地形(未掘削)を採用
        var newSnap = new float[newW * newH];
        for (int z = 0; z < newH; z++) for (int x = 0; x < newW; x++) newSnap[z * newW + x] = full[z, x];
        // 既にスナップ済みの領域は、保存していた値(掘る前の高さ)で上書きして保持
        var old = wb.snap;
        for (int z = 0; z < wb.sH; z++)
            for (int x = 0; x < wb.sW; x++)
            {
                int gx = wb.sX + x - newX0, gz = wb.sZ + z - newZ0;
                newSnap[gz * newW + gx] = old[z * wb.sW + x];
            }
        wb.sX = newX0; wb.sZ = newZ0; wb.sW = newW; wb.sH = newH; wb.snap = newSnap;
        WaterSnapStore.Save(wb);          // ★ snap は非シリアライズ。書いたら必ず保存する
    }

    /// <summary>
    /// 現在の輪郭から水位を再計算する（スナップ済み＝掘る前の地形高を使うので、既に掘った場所の影響を受けない）。
    /// 形を大きく作り直した/広げた後、水位が合わなくなった時に使う。
    /// </summary>
    public static void RecomputeWaterLevel(WaterBody wb)
    {
        var terrain = Terrain.activeTerrain;
        if (terrain == null || wb == null || wb.outline.Count < 3) return;
        var td = terrain.terrainData; var tt = terrain.transform;
        float ty = tt.position.y, sizeY = td.size.y;
        float px0 = tt.position.x, pz0 = tt.position.z, sx = td.size.x, sz = td.size.z;
        int res = td.heightmapResolution;

        var poly = WaterGeom.SmoothTagged(wb.outline, wb.sharp, 2);
        var poly2 = new List<Vector2>(poly.Count);
        foreach (var p in poly) poly2.Add(new Vector2(p.x, p.z));

        Undo.RecordObject(wb, "Recompute Water Level");
        EnsureSnapCovers(wb, poly2, terrain);

        var hs = new List<float>();
        foreach (var v in poly2)
        {
            int hx = Mathf.Clamp(Mathf.RoundToInt((v.x - px0) / sx * (res - 1)) - wb.sX, 0, wb.sW - 1);
            int hz = Mathf.Clamp(Mathf.RoundToInt((v.y - pz0) / sz * (res - 1)) - wb.sZ, 0, wb.sH - 1);
            hs.Add(wb.snap[hz * wb.sW + hx] * sizeY + ty);
        }
        hs.Sort();
        wb.waterY = hs[hs.Count / 2] - 0.3f;
        EditorUtility.SetDirty(wb);
    }

    /// <summary>
    /// 掘る前の地形(スナップショット)を基準に、水があふれない安全な水位へ合わせて掘り直す。
    /// ★スナップは撮り直さない(掘った地形で上書きしない)ので、いつでも完全に埋め戻せる。
    /// 「水面が浮く/漏れる」を直す用途。
    /// </summary>
    public static void FitToTerrain(WaterBody wb)
    {
        var terrain = Terrain.activeTerrain;
        if (terrain == null || wb == null || wb.outline.Count < 3) return;
        var td = terrain.terrainData; var tt = terrain.transform;
        float ty = tt.position.y, sizeY = td.size.y;
        float px0 = tt.position.x, pz0 = tt.position.z, sx = td.size.x, sz = td.size.z;
        int res = td.heightmapResolution;

        var poly = WaterGeom.SmoothTagged(wb.outline, wb.sharp, 2);
        var poly2 = new List<Vector2>(); foreach (var p in poly) poly2.Add(new Vector2(p.x, p.z));

        Undo.RecordObject(wb, "Fit Water To Terrain");
        EnsureSnapCovers(wb, poly2, terrain);   // 掘る前スナップを維持(撮り直さない)

        // 内部＋外周リング → あふれ点(外周最低)と内部最低（すべて掘る前スナップから）
        var inside = new bool[wb.sH, wb.sW];
        for (int z = 0; z < wb.sH; z++)
            for (int x = 0; x < wb.sW; x++)
            {
                float wx = px0 + (float)(wb.sX + x) / (res - 1) * sx, wz = pz0 + (float)(wb.sZ + z) / (res - 1) * sz;
                inside[z, x] = WaterGeom.PointInPoly(new Vector2(wx, wz), poly2);
            }
        var ring = (bool[,])inside.Clone();
        for (int pass = 0; pass < 6; pass++)
        {
            var s = (bool[,])ring.Clone();
            for (int z = 1; z < wb.sH - 1; z++) for (int x = 1; x < wb.sW - 1; x++)
                if (!s[z, x] && (s[z - 1, x] || s[z + 1, x] || s[z, x - 1] || s[z, x + 1])) ring[z, x] = true;
        }
        float outMin = 9999f, inMin = 9999f;
        for (int z = 0; z < wb.sH; z++)
            for (int x = 0; x < wb.sW; x++)
            {
                float h = wb.snap[z * wb.sW + x] * sizeY + ty;
                if (inside[z, x]) inMin = Mathf.Min(inMin, h);
                else if (ring[z, x]) outMin = Mathf.Min(outMin, h);
            }
        wb.raiseBanks = false;   // 下げて収めるので土手は不要
        wb.waterY = Mathf.Max(inMin + 0.3f, outMin - 0.3f);   // あふれない高さ
        EditorUtility.SetDirty(wb);
        Recarve(wb);
    }

    /// <summary>
    /// 岸を均して水面より低くなった所にできる「水面のフチが浮く隙間」を、地形を一切変えずに埋める。
    /// 水面より低い輪郭点だけを、地面が水位まで上がってくる汀線まで外側(辺の法線方向)へ広げ、
    /// 水面メッシュを張り直す。掘り込み・水位・均した斜面はすべて保持される。
    /// 隆起・削りブラシの「ならし」で水際を均した後に押す用途。
    /// 戻り値 = 動かした点の数。
    /// </summary>
    public static int FillShorelineGap(WaterBody wb)
    {
        var terrain = Terrain.activeTerrain;
        if (terrain == null || wb == null || wb.outline.Count < 3) return 0;
        var tt = terrain.transform;
        float ty = tt.position.y;
        float waterY = wb.waterY;
        int n = wb.outline.Count;

        // 現在の輪郭を XZ 2D 化（内外判定・法線用）
        var poly2 = new List<Vector2>(n);
        for (int i = 0; i < n; i++) poly2.Add(new Vector2(wb.outline[i].x, wb.outline[i].z));

        Undo.RecordObject(wb, "Fill Shoreline Gap");
        float target = waterY + 0.1f;   // 汀線＝地面が水位まで上がる所（少しだけ上）
        int moved = 0;
        for (int i = 0; i < n; i++)
        {
            Vector2 cur = poly2[i], prev = poly2[(i - 1 + n) % n], next = poly2[(i + 1) % n];
            Vector2 tang = next - prev;
            Vector2 nrm = new Vector2(tang.y, -tang.x);   // 辺に垂直
            if (nrm.sqrMagnitude < 1e-8f) continue;
            nrm.Normalize();
            if (WaterGeom.PointInPoly(cur + nrm * 1.0f, poly2)) nrm = -nrm;   // 外向きに揃える

            float hAt = terrain.SampleHeight(new Vector3(cur.x, 0, cur.y)) + ty;
            if (hAt >= waterY) continue;   // 既に水面以上の岸はそのまま

            float found = -1f;
            for (float d = 1f; d <= 80f; d += 0.5f)
            {
                Vector2 q = cur + nrm * d;
                if (terrain.SampleHeight(new Vector3(q.x, 0, q.y)) + ty >= target) { found = d; break; }
            }
            if (found < 0f) continue;   // 80m 以内に汀線が無い＝この点は触らない

            Vector2 np = cur + nrm * (found + 0.2f);   // 汀線を少し越えた所へ
            Vector3 v = new Vector3(np.x, 0f, np.y);
            v.y = terrain.SampleHeight(v) + ty;
            wb.outline[i] = v; moved++;
        }
        EditorUtility.SetDirty(wb);
        RebuildSurface(wb);   // 水面メッシュだけ張り直し（地形は触らない）
        return moved;
    }

    /// <summary>掘り込みを埋めて地形を元(スナップショットに記録した掘る前の高さ)に戻す。</summary>
    public static bool RestoreTerrain(WaterBody wb)
    {
        var terrain = Terrain.activeTerrain;
        if (terrain == null || wb == null || !wb.hasSnap || wb.snap == null) return false;
        var td = terrain.terrainData;
        var H = new float[wb.sH, wb.sW];
        for (int z = 0; z < wb.sH; z++) for (int x = 0; x < wb.sW; x++) H[z, x] = wb.snap[z * wb.sW + x];
        int kept = PreserveOtherWater(wb, terrain, null, H);   // 隣の水域の掘り込みを埋めない
        if (kept > 0) Debug.Log("他の水域が掘っている " + kept + " セルはそのまま残しました（埋め戻し防止）。");
        td.SetHeights(wb.sX, wb.sZ, H);
        return true;
    }

    /// <summary>地形を元に戻してから水域を削除する。</summary>
    public static void RestoreAndDelete(WaterBody wb)
    {
        if (wb == null) return;
        var go = wb.gameObject;
        RestoreTerrain(wb);
        // メッシュ/マテリアルの資産も掃除
        var mf = wb.GetComponent<MeshFilter>();
        if (mf != null && mf.sharedMesh != null && AssetDatabase.Contains(mf.sharedMesh))
            AssetDatabase.DeleteAsset(AssetDatabase.GetAssetPath(mf.sharedMesh));
        var mr = wb.GetComponent<MeshRenderer>();
        if (mr != null && mr.sharedMaterial != null && AssetDatabase.Contains(mr.sharedMaterial))
            AssetDatabase.DeleteAsset(AssetDatabase.GetAssetPath(mr.sharedMaterial));
        Undo.DestroyObjectImmediate(go);
    }

    /// <summary>地形を現在の形で掘り直す（スナップ領域は必要なら自動拡張、初回は水位も計算）。</summary>
    public static void Recarve(WaterBody wb)
    {
        var terrain = Terrain.activeTerrain;
        if (terrain == null || wb == null || wb.outline.Count < 3) return;
        var td = terrain.terrainData; var tt = terrain.transform;
        float ty = tt.position.y, sizeY = td.size.y;
        float px0 = tt.position.x, pz0 = tt.position.z, sx = td.size.x, sz = td.size.z;
        int res = td.heightmapResolution;

        var poly = WaterGeom.SmoothTagged(wb.outline, wb.sharp, 2);
        var poly2 = new List<Vector2>(poly.Count);
        foreach (var p in poly) poly2.Add(new Vector2(p.x, p.z));

        Undo.RecordObject(wb, "Recarve Water");
        bool firstTime = !wb.hasSnap;
        EnsureSnapCovers(wb, poly2, terrain);

        if (firstTime)
        {
            var hs = new List<float>();
            foreach (var p in poly) hs.Add(terrain.SampleHeight(new Vector3(p.x, 0, p.z)) + ty);
            hs.Sort(); wb.waterY = hs[hs.Count / 2] - 0.3f;
        }

        // 復元(スナップ全域)
        var H = new float[wb.sH, wb.sW];
        for (int z = 0; z < wb.sH; z++) for (int x = 0; x < wb.sW; x++) H[z, x] = wb.snap[z * wb.sW + x];

        // 内部マスク(ポリゴン内)
        var inside = new bool[wb.sH, wb.sW];
        for (int z = 0; z < wb.sH; z++)
            for (int x = 0; x < wb.sW; x++)
            {
                int hx = wb.sX + x, hz = wb.sZ + z;
                float wx = px0 + (float)hx / (res - 1) * sx, wz = pz0 + (float)hz / (res - 1) * sz;
                inside[z, x] = WaterGeom.PointInPoly(new Vector2(wx, wz), poly2);
            }

        // 被覆率(アンチエイリアス): 端のテクセルだけ 4x4 サブサンプルで小数化。
        // 垂直掘り時に斜め辺が 2m グリッドの階段(カクカク)になるのを、壁の急さは保ったまま滑らかにする。
        float cellW = sx / (res - 1);
        var cover = new float[wb.sH, wb.sW];
        for (int z = 0; z < wb.sH; z++)
            for (int x = 0; x < wb.sW; x++)
            {
                bool ins = inside[z, x];
                bool edge = (z > 0 && inside[z - 1, x] != ins) || (z < wb.sH - 1 && inside[z + 1, x] != ins)
                         || (x > 0 && inside[z, x - 1] != ins) || (x < wb.sW - 1 && inside[z, x + 1] != ins);
                if (!edge) { cover[z, x] = ins ? 1f : 0f; continue; }
                int hx = wb.sX + x, hz = wb.sZ + z;
                float wx = px0 + (float)hx / (res - 1) * sx, wz = pz0 + (float)hz / (res - 1) * sz;
                int c = 0;
                for (int sy = 0; sy < 4; sy++)
                    for (int sxx = 0; sxx < 4; sxx++)
                    {
                        float ox = ((sxx + 0.5f) / 4f - 0.5f) * cellW;
                        float oz = ((sy + 0.5f) / 4f - 0.5f) * cellW;
                        if (WaterGeom.PointInPoly(new Vector2(wx + ox, wz + oz), poly2)) c++;
                    }
                cover[z, x] = c / 16f;
            }

        // waterY はワールドY。正規化高さへ変換するには地形ベース ty を引く
        // (これを忘れると ty<0 の地形で常に床(0)まで掘れてしまう)
        float bottomNorm = Mathf.Clamp01((wb.waterY - wb.depth - ty) / sizeY);
        float bankNorm = Mathf.Clamp01((wb.waterY + 0.4f - ty) / sizeY);   // 土手の高さ(水位より少し上)

        // 内部を掘る（垂直: 被覆率でアンチエイリアス掘り / なだらか: 従来の二値掘り）
        for (int z = 0; z < wb.sH; z++)
            for (int x = 0; x < wb.sW; x++)
            {
                // levelFloor: 底を『深さ』の高さでならす(深すぎる所は埋め戻す)。
                // OFF だと掘るだけなので、旧掘り込みが底に残って段差になり、水深差がそのまま水の色差になる。
                if (wb.verticalWalls)
                {
                    if (cover[z, x] > 0f)
                    {
                        float tgt = Mathf.Lerp(H[z, x], bottomNorm, cover[z, x]);
                        if (wb.levelFloor || tgt < H[z, x]) H[z, x] = tgt;
                    }
                }
                else if (inside[z, x] && (wb.levelFloor || H[z, x] > bottomNorm)) H[z, x] = bottomNorm;
            }

        // 土手: 内部マスクを外側へ膨張させた「輪」を、水位より低ければ盛り上げる
        if (wb.raiseBanks)
        {
            float cell = sx / (res - 1);
            int bankCells = Mathf.Max(1, Mathf.RoundToInt(wb.bankWidth / Mathf.Max(0.5f, cell)));
            var ring = (bool[,])inside.Clone();
            for (int pass = 0; pass < bankCells; pass++)
            {
                var src = (bool[,])ring.Clone();
                for (int z = 1; z < wb.sH - 1; z++)
                    for (int x = 1; x < wb.sW - 1; x++)
                        if (!src[z, x] && (src[z - 1, x] || src[z + 1, x] || src[z, x - 1] || src[z, x + 1]))
                            ring[z, x] = true;
            }
            for (int z = 0; z < wb.sH; z++)
                for (int x = 0; x < wb.sW; x++)
                    if (ring[z, x] && !inside[z, x] && H[z, x] < bankNorm) H[z, x] = bankNorm;   // 低い縁だけ盛る
        }

        // 平滑化(掘り込み・土手をなだらかに)。垂直掘り(直角)のときはパス0でカクッと掘る。
        int smoothPasses = wb.verticalWalls ? 0 : 4;
        for (int pass = 0; pass < smoothPasses; pass++)
        {
            var src = (float[,])H.Clone();
            for (int z = 1; z < wb.sH - 1; z++) for (int x = 1; x < wb.sW - 1; x++)
                H[z, x] = (src[z, x] * 4 + src[z - 1, x] + src[z + 1, x] + src[z, x - 1] + src[z, x + 1]) / 8f;
        }
        int kept = PreserveOtherWater(wb, terrain, poly2, H);   // 隣の水域の掘り込みを埋めない
        if (kept > 0) Debug.Log("他の水域が掘っている " + kept + " セルはそのまま残しました（埋め戻し防止）。");
        td.SetHeights(wb.sX, wb.sZ, H);
        EditorUtility.SetDirty(wb);
        RebuildSurface(wb);
    }
}
