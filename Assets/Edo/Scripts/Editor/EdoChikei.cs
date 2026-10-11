using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// **北の3邸の細かい地形**(施主裁定 2026-10-11・EDO-0502・裁定図 https://claude.ai/artifact/LWQKHKMKKhmH8JwpzHBqjH)。
///
/// 皮(EdgeSkin 0.25m・SkinHeightSolve)をやめ、岡部・土井・松江松平を覆う 512m 四方・0.25m 格子(heightmap 2049²)の
/// 地形を一枚起こす。大地形 ModernTerrain(2m 格子)はその範囲を 2m 格子揃えで穴抜きする。
///   ・原点は 3邸の区画(EdoParcels)の外接矩形の芯 − 256 を、大地形の 2m 格子へ丸めた点。
///   ・高さ・穴・塗り(スプラット)・草・木は大地形から写す(縁の節点は大地形の節点と同じ点・同じ高さ ── 継ぎ目は割れない)。
///   ・岡部はこの後 Stage1 の造成が 0.25m の造成の面(docs/Sashizu/okabe_graded.bin)で描き直す。
///     土井・松江松平は写した高さ+写した穴のまま(皮は穴の上に残る)── 見た目を変えない。
/// ⛔ 地形の編集は Undo の外 ── 起こす前に ModernTerrain.asset を退避すること(この道具は退避しない)。
/// ⛔ 二度起こさない(資産が在れば断る)。
/// </summary>
[InitializeOnLoad]
public static class EdoChikei
{
    public const float Size = 512f;
    public const int Res = 2049;
    static readonly string[] Ids = { "okabe", "doi", "matsudaira_dewa" };

    static EdoChikei() { EditorSceneManager.sceneOpened += OnSceneOpened; }

    /// <summary>赤坂・作業場を開いたとき、大地形があって細かい地形が無ければ据える(大地形は北の範囲が穴なので、無いと地面が抜けて見える)。
    /// 開いた時点で未保存の変更が無ければ保存する(作業場の「未保存なら断る」に掛からないため)。</summary>
    static void OnSceneOpened(UnityEngine.SceneManagement.Scene sc, OpenSceneMode mode)
    {
        try
        {
            if (sc.path != EdoAssets.Scenes.Akasaka && sc.path != EdoAssets.Scenes.Koba) return;
            if (!File.Exists(EdoAssets.Chikei.KitaPrefab)) return;
            bool big = false, kita = false;
            foreach (var r in sc.GetRootGameObjects()) { if (r.name == "ModernTerrain") big = true; if (r.name == EdoAssets.Chikei.KitaName) kita = true; }
            if (!big || kita) return;
            bool wasDirty = sc.isDirty;
            var pf = AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Chikei.KitaPrefab);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(pf, sc);
            go.name = EdoAssets.Chikei.KitaName;
            EdoBuild.InvalidateTerrain();
            if (!wasDirty) EditorSceneManager.SaveScene(sc);
            Debug.Log("[地形] " + sc.name + " に北の3邸の細かい地形を据えた" + (wasDirty ? "(未保存の変更があったので保存していない)" : "・保存した"));
        }
        catch (Exception e) { Debug.LogWarning("[地形] 細かい地形を据えられなかった: " + e.Message); }
    }

    /// <summary>原点(大地形の 2m 格子に揃えた・3邸の外接矩形の芯 − 256)。</summary>
    public static Vector2 Origin(Terrain big)
    {
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        foreach (var id in Ids) foreach (var q in EdoParcels.Get(id)) { x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y); }
        var bo = big.transform.position; float bc = EdoBuild.TerrainCell(big);
        float ox = bo.x + Mathf.Round(((x0 + x1) * 0.5f - Size * 0.5f - bo.x) / bc) * bc;
        float oz = bo.z + Mathf.Round(((z0 + z1) * 0.5f - Size * 0.5f - bo.z) / bc) * bc;
        if (x0 < ox + 20f || x1 > ox + Size - 20f || z0 < oz + 20f || z1 > oz + Size - 20f) throw new Exception("3邸が 512m の中に 20m の余白で収まらない");
        return new Vector2(ox, oz);
    }

    /// <summary>塗り(スプラット)を大地形から写す(層は同じ・0.5m/px へ双一次)。⚠ 資産を作る前に塗ると資産化で消えた(第110巡)── 資産を作った後に呼ぶ。</summary>
    public static string CopySplat(Terrain big, TerrainData td, Vector2 o)
    {
        var bd = big.terrainData; var bo = big.transform.position; var sb = new System.Text.StringBuilder();
        // ---- 塗り(スプラット)── 層は大地形と同じ。0.5m/px へ双一次で写す
        td.terrainLayers = bd.terrainLayers;
        td.alphamapResolution = 1024;
        int ar = td.alphamapResolution, L = bd.alphamapLayers, br = bd.alphamapResolution; float bpx = bd.size.x / br, npx = Size / ar;
        int ai0 = Mathf.Max(0, Mathf.FloorToInt((o.x - bo.x) / bpx) - 2), aj0 = Mathf.Max(0, Mathf.FloorToInt((o.y - bo.z) / bpx) - 2);
        int aw = Mathf.Min(br - ai0, Mathf.CeilToInt(Size / bpx) + 5), ah = Mathf.Min(br - aj0, Mathf.CeilToInt(Size / bpx) + 5);
        var BA = bd.GetAlphamaps(ai0, aj0, aw, ah);
        var NA = new float[ar, ar, L];
        for (int j = 0; j < ar; j++)
            for (int i = 0; i < ar; i++)
            {
                float wx = o.x + (i + 0.5f) * npx, wz = o.y + (j + 0.5f) * npx;
                float fx = (wx - bo.x) / bpx - 0.5f - ai0, fz = (wz - bo.z) / bpx - 0.5f - aj0;
                int x0 = Mathf.Clamp(Mathf.FloorToInt(fx), 0, aw - 2), z0 = Mathf.Clamp(Mathf.FloorToInt(fz), 0, ah - 2);
                float tx = Mathf.Clamp01(fx - x0), tz = Mathf.Clamp01(fz - z0), sum = 0f;
                for (int l = 0; l < L; l++)
                {
                    float v = Mathf.Lerp(Mathf.Lerp(BA[z0, x0, l], BA[z0, x0 + 1, l], tx), Mathf.Lerp(BA[z0 + 1, x0, l], BA[z0 + 1, x0 + 1, l], tx), tz);
                    NA[j, i, l] = v; sum += v;
                }
                if (sum > 1e-6f) for (int l = 0; l < L; l++) NA[j, i, l] /= sum;
            }
        td.SetAlphamaps(0, 0, NA);
        sb.Append("塗り " + L + " 層・" + ar + "²(" + npx + "m/px)");
        EditorUtility.SetDirty(td); AssetDatabase.SaveAssetIfDirty(td);
        return sb.ToString();
    }

    [MenuItem("Edo/地形/北の3邸の細かい地形: 塗りを大地形から写し直す")]
    public static void CopySplatMenu()
    {
        var big = GameObject.Find("ModernTerrain").GetComponent<Terrain>(); var kt = EdoBuild.FineTerrain();
        Debug.Log("[地形] " + CopySplat(big, kt.terrainData, new Vector2(kt.transform.position.x, kt.transform.position.z)));
    }

    [MenuItem("Edo/地形/北の3邸の細かい地形を起こす(一度きり)")]
    public static void CreateMenu() { Debug.Log("[地形] " + Create()); }

    public static string Create()
    {
        if (File.Exists(EdoAssets.Chikei.KitaData)) return "⛔ 既にある: " + EdoAssets.Chikei.KitaData + "(二度起こさない)";
        var bigGo = GameObject.Find("ModernTerrain"); if (bigGo == null) return "⛔ ModernTerrain が無い";
        var big = bigGo.GetComponent<Terrain>(); var bd = big.terrainData; var bo = big.transform.position;
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var sb = new System.Text.StringBuilder();
        var o = Origin(big);
        float bc = EdoBuild.TerrainCell(big), cell = Size / (Res - 1);
        int bi0 = Mathf.RoundToInt((o.x - bo.x) / bc), bj0 = Mathf.RoundToInt((o.y - bo.z) / bc), bn = Mathf.RoundToInt(Size / bc);   // 大地形の升の番号
        sb.AppendLine("原点 x " + o.x.ToString("F2") + " z " + o.y.ToString("F2") + "・" + Size + "m 四方・heightmap " + Res + "²(" + cell + "m)・大地形の升 [" + bi0 + "," + bj0 + "] から " + bn + "²");

        var td = new TerrainData();
        td.heightmapResolution = Res;
        td.size = new Vector3(Size, bd.size.y, Size);
        // ---- 高さ(大地形の描く面を SampleHeight で写す ── 縁の節点は大地形の節点そのもの)
        var H = new float[Res, Res];
        for (int j = 0; j < Res; j++)
            for (int i = 0; i < Res; i++)
                H[j, i] = big.SampleHeight(new Vector3(o.x + i * cell, 0f, o.y + j * cell)) / bd.size.y;
        td.SetHeights(0, 0, H);
        // ---- 穴(大地形の 2m の穴を 8×8 へ)
        int hr = td.holesResolution, k = Mathf.RoundToInt(bc / cell);
        var bh = bd.GetHoles(bi0, bj0, bn, bn);   // [y, x](正方)
        var holes = new bool[hr, hr]; int nh = 0;
        for (int j = 0; j < hr; j++) for (int i = 0; i < hr; i++) holes[j, i] = true;
        for (int j = 0; j < bn; j++)
            for (int i = 0; i < bn; i++)
            {
                if (bh[j, i]) continue; nh++;
                for (int b = 0; b < k; b++) for (int a = 0; a < k; a++) holes[j * k + b, i * k + a] = false;
            }
        td.SetHoles(0, 0, holes);
        sb.AppendLine("穴を写した 大地形の升 " + nh + "(皮の邸の穴)");
        // ---- 草(detail)── 大地形と同じ 1m の升で数をそのまま写す
        td.detailPrototypes = bd.detailPrototypes;
        float bdc = bd.size.x / bd.detailResolution;
        int dr = Mathf.RoundToInt(Size / bdc);
        td.SetDetailScatterMode(bd.detailScatterMode);
        td.SetDetailResolution(dr, bd.detailResolutionPerPatch);
        int di0 = Mathf.RoundToInt((o.x - bo.x) / bdc), dj0 = Mathf.RoundToInt((o.y - bo.z) / bdc); long ndet = 0;
        for (int l = 0; l < bd.detailPrototypes.Length; l++)
        {
            var d = bd.GetDetailLayer(di0, dj0, dr, dr, l);   // [y, x](正方)
            td.SetDetailLayer(0, 0, l, d);
            foreach (var v in d) ndet += v;
        }
        sb.AppendLine("草 " + bd.detailPrototypes.Length + " 種・" + dr + "²(" + bdc + "m)・数 " + ndet);
        // ---- 木 ── 矩形の中の木を移す(大地形の穴の升の木は描かれないので、大地形からは外す)
        td.treePrototypes = bd.treePrototypes;
        var rect = new Rect(o.x, o.y, Size, Size);
        var keep = new List<TreeInstance>(); var moved = new List<TreeInstance>();
        foreach (var ti in bd.treeInstances)
        {
            var w = Vector3.Scale(ti.position, bd.size) + bo;
            if (!rect.Contains(new Vector2(w.x, w.z))) { keep.Add(ti); continue; }
            var n = ti;
            float gy = big.SampleHeight(new Vector3(w.x, 0f, w.z));   // 同じ y の原点・同じ高さの幅 ⇒ 正規化の高さはそのまま
            n.position = new Vector3((w.x - o.x) / Size, gy / bd.size.y, (w.z - o.y) / Size);
            moved.Add(n);
        }
        td.treeInstances = moved.ToArray();
        sb.AppendLine("木を移した " + moved.Count + " 本(大地形に残す " + keep.Count + ")");

        AssetDatabase.CreateAsset(td, EdoAssets.Chikei.KitaData);
        sb.AppendLine(CopySplat(big, td, o));
        var go = Terrain.CreateTerrainGameObject(td);
        go.name = EdoAssets.Chikei.KitaName;
        go.transform.position = new Vector3(o.x, bo.y, o.y);
        var t = go.GetComponent<Terrain>();
        t.materialTemplate = big.materialTemplate;
        t.heightmapPixelError = big.heightmapPixelError;
        t.basemapDistance = big.basemapDistance;
        t.detailObjectDistance = big.detailObjectDistance;
        t.detailObjectDensity = big.detailObjectDensity;
        t.treeDistance = big.treeDistance;
        t.treeBillboardDistance = big.treeBillboardDistance;
        t.drawInstanced = big.drawInstanced;
        t.allowAutoConnect = false;
        t.groupingID = big.groupingID + 1;
        go.layer = bigGo.layer;
        PrefabUtility.SaveAsPrefabAssetAndConnect(go, EdoAssets.Chikei.KitaPrefab, InteractionMode.AutomatedAction);

        // ---- 大地形を穴抜き(2m の升・範囲ちょうど)/ 移した木を外す
        bd.treeInstances = keep.ToArray();
        var cut = new bool[bn, bn];   // false = 穴
        bd.SetHoles(bi0, bj0, cut);
        EditorUtility.SetDirty(bd); AssetDatabase.SaveAssetIfDirty(bd);
        EdoBuild.InvalidateTerrain();
        sb.AppendLine("大地形を穴抜き " + bn + "² 升");
        // ---- 継ぎ目(縁の節点 4·2048 点)の高さの差
        float seam = 0f;
        for (int e = 0; e < Res; e++)
            foreach (var p in new[] { new Vector2(o.x + e * cell, o.y), new Vector2(o.x + e * cell, o.y + Size), new Vector2(o.x, o.y + e * cell), new Vector2(o.x + Size, o.y + e * cell) })
                seam = Mathf.Max(seam, Mathf.Abs(t.SampleHeight(new Vector3(p.x, 0, p.y)) - big.SampleHeight(new Vector3(p.x, 0, p.y))));
        sb.AppendLine("継ぎ目の高さの差 最大 " + seam.ToString("F4") + "m");
        UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(go, bigGo.scene);
        EditorSceneManager.MarkSceneDirty(bigGo.scene);
        AssetDatabase.SaveAssets();
        sb.Append("資産 " + EdoAssets.Chikei.KitaData + " " + (new FileInfo(EdoAssets.Chikei.KitaData).Length / 1e6).ToString("F1") + "MB・" + sw.Elapsed.TotalSeconds.ToString("F1") + " 秒");
        return sb.ToString();
    }
}
