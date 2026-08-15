using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 地形ハイトマップ(＋WaterBody の掘り込みスナップ)を丸ごと保存／復元する共通機構。
/// 『隆起・削りブラシ』と『断面編集』が同じ 1 個のスナップショットを共有する
/// （どちらで保存しても、どちらからでも戻せる）。
///
/// 保存先は Library/EdoRaiseSnap.bin。スクリプト再コンパイルをまたいでも残る。
/// </summary>
public static class EdoTerrainSnapshot
{
    public static string Path =>
        System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), "Library", "EdoRaiseSnap.bin");

    public static bool Exists => System.IO.File.Exists(Path);

    public static string Info =>
        Exists ? "保存あり: " + System.IO.File.GetLastWriteTime(Path).ToString("MM/dd HH:mm:ss") : "保存なし";

    /// <summary>地形全体＋各 WaterBody の掘り込みスナップを 1 ファイルに保存。</summary>
    public static void Save(TerrainData td)
    {
        int res = td.heightmapResolution;
        var H = td.GetHeights(0, 0, res, res);
        var flat = new float[res * res];
        for (int z = 0; z < res; z++) for (int x = 0; x < res; x++) flat[z * res + x] = H[z, x];
        var bytes = new byte[flat.Length * 4]; System.Buffer.BlockCopy(flat, 0, bytes, 0, bytes.Length);

        var wbs = new List<WaterBody>();
        foreach (var wb in Object.FindObjectsByType<WaterBody>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (wb.hasSnap && wb.snap != null) wbs.Add(wb);

        using (var fs = new System.IO.FileStream(Path, System.IO.FileMode.Create))
        using (var bw = new System.IO.BinaryWriter(fs))
        {
            bw.Write(res); bw.Write(bytes.Length); bw.Write(bytes);
            bw.Write(wbs.Count);
            foreach (var wb in wbs)
            {
                bw.Write(wb.name); bw.Write(wb.sX); bw.Write(wb.sZ); bw.Write(wb.sW); bw.Write(wb.sH);
                bw.Write(wb.snap.Length);
                var sb = new byte[wb.snap.Length * 4]; System.Buffer.BlockCopy(wb.snap, 0, sb, 0, sb.Length); bw.Write(sb);
            }
        }
    }

    /// <summary>保存した状態へ戻す。解像度が変わっていたら false。</summary>
    public static bool Restore(Terrain terr, TerrainData td)
    {
        if (!Exists) return false;
        using (var fs = new System.IO.FileStream(Path, System.IO.FileMode.Open))
        using (var br = new System.IO.BinaryReader(fs))
        {
            int res = br.ReadInt32();
            if (res != td.heightmapResolution)
            {
                EditorUtility.DisplayDialog("戻せません", "地形の解像度が変わっています。", "OK");
                return false;
            }
            int blen = br.ReadInt32(); var bytes = br.ReadBytes(blen);
            var flat = new float[res * res]; System.Buffer.BlockCopy(bytes, 0, flat, 0, blen);
            var H = new float[res, res]; for (int z = 0; z < res; z++) for (int x = 0; x < res; x++) H[z, x] = flat[z * res + x];
            Undo.RegisterCompleteObjectUndo(td, "Restore Terrain Snapshot");
            td.SetHeights(0, 0, H);

            int cnt = br.ReadInt32();
            var byName = new Dictionary<string, WaterBody>();
            foreach (var wb in Object.FindObjectsByType<WaterBody>(FindObjectsInactive.Include, FindObjectsSortMode.None)) byName[wb.name] = wb;
            for (int i = 0; i < cnt; i++)
            {
                string nm = br.ReadString(); int sX = br.ReadInt32(), sZ = br.ReadInt32(), sW = br.ReadInt32(), sH = br.ReadInt32();
                int slen = br.ReadInt32(); var sb = br.ReadBytes(slen * 4); var snap = new float[slen]; System.Buffer.BlockCopy(sb, 0, snap, 0, sb.Length);
                if (byName.TryGetValue(nm, out var wb)) { Undo.RecordObject(wb, "Restore Water Snap"); wb.sX = sX; wb.sZ = sZ; wb.sW = sW; wb.sH = sH; wb.snap = snap; wb.hasSnap = true; WaterSnapStore.Save(wb); }
            }
        }
        terr.Flush(); SceneView.RepaintAll();
        return true;
    }

    /// <summary>
    /// 地形を編集した後、書き換えた範囲(ハイトマップ index)に重なる WaterBody の
    /// 掘り込みスナップを新しい地形高さで更新する（そうしないと Restore で古い地形が復活する）。
    /// </summary>
    public static void SyncWaterSnaps(TerrainData td, int minX, int minZ, int maxX, int maxZ)
    {
        int res = td.heightmapResolution;
        var full = td.GetHeights(0, 0, res, res);
        foreach (var wb in Object.FindObjectsByType<WaterBody>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (!wb.hasSnap || wb.snap == null) continue;
            bool any = false;
            for (int z = 0; z < wb.sH; z++)
                for (int x = 0; x < wb.sW; x++)
                {
                    int gx = wb.sX + x, gz = wb.sZ + z;
                    if (gx < minX || gx > maxX || gz < minZ || gz > maxZ) continue;
                    wb.snap[z * wb.sW + x] = full[gz, gx]; any = true;
                }
            if (any) WaterSnapStore.Save(wb);   // ★ snap は非シリアライズ。書いたら必ず保存する
        }
    }
}
