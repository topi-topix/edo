using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Networking;
using Edo.Geo;

namespace Edo.EditorTools
{
    /// <summary>
    /// 国土地理院の標高タイルから、GeoReference に整合した Unity Terrain を生成する。
    ///
    /// データ出典: 国土地理院 標高タイル (基盤地図情報 数値標高モデル)
    ///   https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt   (5m メッシュ / 航空レーザ測量)
    ///   https://cyberjapandata.gsi.go.jp/xyz/dem5b/{z}/{x}/{y}.txt   (5m メッシュ / 写真測量)
    ///   https://cyberjapandata.gsi.go.jp/xyz/dem/{z}/{x}/{y}.txt     (10m メッシュ / 等高線)
    ///
    /// 国土地理院コンテンツ利用規約に基づき利用する。
    /// 完成したゲームには「出典: 国土地理院」のクレジットを必ず入れること。
    ///
    /// タイル仕様:
    ///   - 256x256 の CSV。値は標高[m]、"e" は欠測。
    ///   - 各画素の値は、その画素範囲の「北西端」の標高を表す (中央値でも平均でもない)。
    /// </summary>
    public class GsiTerrainBuilder : EditorWindow
    {
        private const string CacheDir = "Temp/GsiDemCache";
        private static readonly string[] DemSources = { "dem5a", "dem5b", "dem" };

        // 生成範囲: シーン原点(江戸見坂)を基準にした Unity 座標での矩形
        private float minX = -2000f;
        private float minZ = -1000f;
        private int sizeMeters = 4096;
        private int heightmapResolution = 2049; // 2^11 + 1 → 約 2.0 m/px
        private int zoom = 15;
        private string terrainDataPath = "Assets/Edo/Terrain/ModernTerrain.asset";
        private string goName = "ModernTerrain";

        private readonly Dictionary<string, float[]> tileCache = new Dictionary<string, float[]>();
        private int downloadedTiles;
        private int cachedTiles;
        private int failedTiles;

        [MenuItem("Edo/地形/地理院DEMからTerrain生成")]
        public static void Open()
        {
            GetWindow<GsiTerrainBuilder>("GSI Terrain Builder").minSize = new Vector2(420, 340);
        }

        private void OnGUI()
        {
            EditorGUILayout.HelpBox(
                "国土地理院の標高タイルをダウンロードし、GeoReference に整合した Terrain を生成します。\n" +
                "シーン原点 = 江戸見坂 (" + GeoReference.OriginLat.ToString("F6") + ", " +
                GeoReference.OriginLon.ToString("F6") + ")\n" +
                "出典: 国土地理院。完成物にクレジット表記が必要です。",
                MessageType.Info);

            EditorGUILayout.Space();
            EditorGUILayout.LabelField("生成範囲 (Unity座標)", EditorStyles.boldLabel);
            minX = EditorGUILayout.FloatField("南西端 X (東)", minX);
            minZ = EditorGUILayout.FloatField("南西端 Z (北)", minZ);
            sizeMeters = EditorGUILayout.IntField("一辺 [m]", sizeMeters);

            EditorGUILayout.Space();
            EditorGUILayout.LabelField("解像度", EditorStyles.boldLabel);
            heightmapResolution = EditorGUILayout.IntPopup("Heightmap",
                heightmapResolution,
                new[] { "513", "1025", "2049", "4097" },
                new[] { 513, 1025, 2049, 4097 });
            zoom = EditorGUILayout.IntSlider("タイルのズーム", zoom, 13, 15);

            float mPerPx = (float)sizeMeters / (heightmapResolution - 1);
            EditorGUILayout.LabelField("  → " + mPerPx.ToString("F2") + " m / 画素");
            long bytes = (long)heightmapResolution * heightmapResolution * 4;
            EditorGUILayout.LabelField("  → heightmap " + (bytes / 1024 / 1024) + " MB");

            EditorGUILayout.Space();
            terrainDataPath = EditorGUILayout.TextField("TerrainData 保存先", terrainDataPath);
            goName = EditorGUILayout.TextField("GameObject 名", goName);

            EditorGUILayout.Space();
            if (GUILayout.Button("生成する", GUILayout.Height(32)))
            {
                Build();
            }
        }

        private void Build()
        {
            tileCache.Clear();
            downloadedTiles = 0;
            cachedTiles = 0;
            failedTiles = 0;

            Directory.CreateDirectory(CacheDir);
            var dir = Path.GetDirectoryName(terrainDataPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            int res = heightmapResolution;
            var heights = new float[res, res];
            var msl = new float[res, res];

            float minMsl = float.MaxValue;
            float maxMsl = float.MinValue;
            int missing = 0;

            try
            {
                // 1st pass: 各画素の緯度経度を求めて標高をサンプリングする
                for (int j = 0; j < res; j++) // j = Z方向(北)
                {
                    if (j % 32 == 0)
                    {
                        if (EditorUtility.DisplayCancelableProgressBar(
                                "GSI Terrain Builder",
                                "標高タイルを取得中... (" + j + " / " + res + " 行, DL " + downloadedTiles + " / cache " + cachedTiles + ")",
                                (float)j / res))
                        {
                            EditorUtility.ClearProgressBar();
                            return;
                        }
                    }

                    for (int i = 0; i < res; i++) // i = X方向(東)
                    {
                        float wx = minX + (float)i / (res - 1) * sizeMeters;
                        float wz = minZ + (float)j / (res - 1) * sizeMeters;

                        double lat, lon, h;
                        GeoReference.UnityToLatLon(new Vector3(wx, 0f, wz), out lat, out lon, out h);

                        float e = SampleElevation(lat, lon);
                        if (float.IsNaN(e))
                        {
                            missing++;
                            e = 0f;
                        }

                        msl[j, i] = e;
                        if (e < minMsl) minMsl = e;
                        if (e > maxMsl) maxMsl = e;
                    }
                }
            }
            finally
            {
                EditorUtility.ClearProgressBar();
            }

            if (minMsl > maxMsl)
            {
                Debug.LogError("[GsiTerrainBuilder] 標高データを1点も取得できませんでした。");
                return;
            }

            // 垂直方向の設定。Unity Y = 0 は海抜 GeoReference.OriginHeight に対応する。
            float baseMsl = Mathf.Floor(minMsl) - 1f;   // 底に少し余裕を持たせる
            float topMsl = Mathf.Ceil(maxMsl) + 1f;
            float heightRange = topMsl - baseMsl;

            for (int j = 0; j < res; j++)
            {
                for (int i = 0; i < res; i++)
                {
                    heights[j, i] = Mathf.Clamp01((msl[j, i] - baseMsl) / heightRange);
                }
            }

            var td = AssetDatabase.LoadAssetAtPath<TerrainData>(terrainDataPath);
            if (td == null)
            {
                td = new TerrainData();
                AssetDatabase.CreateAsset(td, terrainDataPath);
            }

            td.heightmapResolution = res;
            td.size = new Vector3(sizeMeters, heightRange, sizeMeters);
            td.SetHeights(0, 0, heights);

            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();

            var go = GameObject.Find(goName);
            if (go == null)
            {
                go = Terrain.CreateTerrainGameObject(td);
                go.name = goName;
            }
            var terrain = go.GetComponent<Terrain>();
            terrain.terrainData = td;
            var col = go.GetComponent<TerrainCollider>();
            if (col != null) col.terrainData = td;

            // Terrain の原点は南西端。Y は「海抜 baseMsl」が来る位置。
            go.transform.position = new Vector3(minX, (float)(baseMsl - GeoReference.OriginHeight), minZ);

            Selection.activeGameObject = go;

            Debug.Log(string.Format(
                "[GsiTerrainBuilder] 生成完了\n" +
                "  範囲      : X[{0} .. {1}]  Z[{2} .. {3}]  ({4} m 四方)\n" +
                "  解像度    : {5} ({6:F2} m/画素)\n" +
                "  標高      : {7:F1} m 〜 {8:F1} m (海抜)\n" +
                "  Terrain位置: {9}\n" +
                "  タイル    : DL {10} / キャッシュ {11} / 失敗 {12}\n" +
                "  欠測画素  : {13}\n" +
                "  出典      : 国土地理院 標高タイル",
                minX, minX + sizeMeters, minZ, minZ + sizeMeters, sizeMeters,
                res, (float)sizeMeters / (res - 1),
                minMsl, maxMsl,
                go.transform.position,
                downloadedTiles, cachedTiles, failedTiles, missing));
        }

        /// <summary>緯度経度の標高[m]をバイリニア補間で求める。取得できなければ NaN。</summary>
        private float SampleElevation(double lat, double lon)
        {
            double n = Math.Pow(2.0, zoom);
            double fx = (lon + 180.0) / 360.0 * n;
            double latRad = lat * Math.PI / 180.0;
            double fy = (1.0 - Math.Log(Math.Tan(latRad) + 1.0 / Math.Cos(latRad)) / Math.PI) / 2.0 * n;

            // タイル内の画素座標 (画素値は画素範囲の北西端の標高)
            double px = (fx - Math.Floor(fx)) * 256.0 + Math.Floor(fx) * 256.0;
            double py = (fy - Math.Floor(fy)) * 256.0 + Math.Floor(fy) * 256.0;

            int x0 = (int)Math.Floor(px);
            int y0 = (int)Math.Floor(py);
            double tx = px - x0;
            double ty = py - y0;

            float h00 = GetPixel(x0, y0);
            float h10 = GetPixel(x0 + 1, y0);
            float h01 = GetPixel(x0, y0 + 1);
            float h11 = GetPixel(x0 + 1, y0 + 1);

            if (float.IsNaN(h00)) return float.NaN;
            if (float.IsNaN(h10)) h10 = h00;
            if (float.IsNaN(h01)) h01 = h00;
            if (float.IsNaN(h11)) h11 = h00;

            float a = Mathf.Lerp(h00, h10, (float)tx);
            float b = Mathf.Lerp(h01, h11, (float)tx);
            return Mathf.Lerp(a, b, (float)ty);
        }

        /// <summary>グローバル画素座標から標高を引く。欠測は NaN。</summary>
        private float GetPixel(int gx, int gy)
        {
            int tileX = gx / 256;
            int tileY = gy / 256;
            int ix = gx - tileX * 256;
            int iy = gy - tileY * 256;

            float[] tile = GetTile(tileX, tileY);
            if (tile == null) return float.NaN;
            return tile[iy * 256 + ix];
        }

        private float[] GetTile(int tx, int ty)
        {
            string key = zoom + "/" + tx + "/" + ty;
            float[] cached;
            if (tileCache.TryGetValue(key, out cached)) return cached;

            string cachePath = Path.Combine(CacheDir, zoom + "_" + tx + "_" + ty + ".csv");
            string text = null;

            if (File.Exists(cachePath))
            {
                text = File.ReadAllText(cachePath);
                cachedTiles++;
            }
            else
            {
                foreach (var src in DemSources)
                {
                    string url = "https://cyberjapandata.gsi.go.jp/xyz/" + src + "/" + zoom + "/" + tx + "/" + ty + ".txt";
                    using (var req = UnityWebRequest.Get(url))
                    {
                        var op = req.SendWebRequest();
                        while (!op.isDone) { System.Threading.Thread.Sleep(5); }

                        if (req.result == UnityWebRequest.Result.Success)
                        {
                            text = req.downloadHandler.text;
                            File.WriteAllText(cachePath, text);
                            downloadedTiles++;
                            break;
                        }
                    }
                }
            }

            if (text == null)
            {
                failedTiles++;
                tileCache[key] = null;
                return null;
            }

            var values = new float[256 * 256];
            for (int k = 0; k < values.Length; k++) values[k] = float.NaN;

            var lines = text.Split('\n');
            int rows = Math.Min(256, lines.Length);
            for (int r = 0; r < rows; r++)
            {
                var line = lines[r].Trim();
                if (line.Length == 0) continue;
                var cols = line.Split(',');
                int cn = Math.Min(256, cols.Length);
                for (int c = 0; c < cn; c++)
                {
                    float v;
                    if (float.TryParse(cols[c], NumberStyles.Float, CultureInfo.InvariantCulture, out v))
                    {
                        values[r * 256 + c] = v;
                    }
                    // "e" (欠測) は NaN のまま
                }
            }

            tileCache[key] = values;
            return values;
        }
    }
}
