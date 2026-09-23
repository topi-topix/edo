using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEngine;

/// <summary>
/// 類型 Stage5(庭)が置いた <see cref="NiwaGroundZone"/> の印どおり、地形のスプラットへ
/// **白砂利(shirasu・参道と前庭)/ 苔+砂利(moss・坪庭)/ 叩き土(tataki・裏庭)** を塗る(EDO-0372)。
///
/// ⭐ 塗るのは地形のスプラットで、類型ビルダーの持ち場ではない(`docs/typology-builder.md` §4.5
///    覆さない線⑤・<see cref="EdoSurfacePaint"/> と同じ理由・同じ作り)。Stage5 を建て直して印を
///    置き直したら、このメニューをもう一度押す。
/// ⛔ 地形は全邸で共有・Undo の外。塗る前に <see cref="EdoLandUse.SaveSplatBackup"/> で退避する。
/// ⚠ 印は**点+半径**(グリッド起源・多角形ではない)なので、<see cref="EdoSurfacePaint"/> の
///   多角形の被覆率(3×3副標本)は使わない — texel 中心が半径内かどうかの二値で塗る。
/// </summary>
public static class EdoGardenSurfacePaint
{
    // ───────────────────────── 地形レイヤーを確かめる ─────────────────────────
    [MenuItem("Edo/類型/庭の地表レイヤーを確かめる(足りなければ足す)")]
    public static void EnsureLayersMenu() => Debug.Log(EnsureLayers());

    /// <summary>ModernTerrain に L_shirasu / L_moss が無ければ足す。⛔ 既存の層順は変えない —
    /// <c>SetAlphamaps</c> は層インデックスで書くので、途中に挿すと他の層の重みが化ける。</summary>
    public static string EnsureLayers()
    {
        var go = GameObject.Find(EdoLandUse.TerrainName);
        if (go == null) return "⛔ " + EdoLandUse.TerrainName + " が無い";
        var terr = go.GetComponent<Terrain>(); var td = terr.terrainData;
        var have = new List<TerrainLayer>(td.terrainLayers);
        bool changed = false;
        System.Action<string> ensure = path =>
        {
            string nm = System.IO.Path.GetFileNameWithoutExtension(path);
            foreach (var l in have) if (l != null && l.name == nm) return;
            var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
            if (layer == null) { Debug.LogError("⛔ 見つからない: " + path); return; }
            have.Add(layer); changed = true;
        };
        ensure(EdoAssets.Own.LayerShirasu);
        ensure(EdoAssets.Own.LayerMoss);
        if (changed) { td.terrainLayers = have.ToArray(); EditorUtility.SetDirty(td); AssetDatabase.SaveAssets(); }
        return changed ? "地形レイヤーへ shirasu/moss を足した(計 " + have.Count + " 層)"
                       : "既に揃っている(計 " + have.Count + " 層)";
    }

    static IEnumerable<NiwaGroundZone> Zones(string kind)
    {
        foreach (var z in Object.FindObjectsByType<NiwaGroundZone>(FindObjectsSortMode.None))
            if (z.kind == kind && z.points.Count > 0) yield return z;
    }

    // ───────────────────────── 点+半径の被覆 ─────────────────────────
    static void PointRect(EdoSurfacePaint.Frame f, List<Vector3> pts, float radius,
                          out int ix0, out int iz0, out int ix1, out int iz1)
    {
        float minX = float.MaxValue, maxX = float.MinValue, minZ = float.MaxValue, maxZ = float.MinValue;
        foreach (var p in pts)
        {
            minX = Mathf.Min(minX, p.x - radius); maxX = Mathf.Max(maxX, p.x + radius);
            minZ = Mathf.Min(minZ, p.z - radius); maxZ = Mathf.Max(maxZ, p.z + radius);
        }
        ix0 = Mathf.Max(0, Mathf.FloorToInt((minX - f.tp.x) / f.cell));
        ix1 = Mathf.Min(f.res - 1, Mathf.CeilToInt((maxX - f.tp.x) / f.cell));
        iz0 = Mathf.Max(0, Mathf.FloorToInt((minZ - f.tp.z) / f.cell));
        iz1 = Mathf.Min(f.res - 1, Mathf.CeilToInt((maxZ - f.tp.z) / f.cell));
    }

    static bool NearAny(List<Vector3> pts, float radius, float wx, float wz)
    {
        float r2 = radius * radius;
        for (int i = 0; i < pts.Count; i++)
        {
            float dx = pts[i].x - wx, dz = pts[i].z - wz;
            if (dx * dx + dz * dz <= r2) return true;
        }
        return false;
    }

    // ───────────────────────── 塗り方(surface語彙とは別 — 印の種別ごと) ─────────────────────────

    /// <summary>白砂利(参道・前庭)。⭐ ほぼ単色の白砂利 + わずかに土(縁の締まり)。</summary>
    static void RecipeShirasu(float noise, out float shirasu, out float dirt)
    { shirasu = Mathf.Lerp(0.80f, 0.95f, noise); dirt = 1f - shirasu; }

    /// <summary>苔+砂利(坪庭)。⭐ 苔が主・砂利が斑に混じる(苔の平面に砂利敷きの小道が通う坪庭の絵)。</summary>
    static void RecipeMoss(float noise, float macro, out float moss, out float shirasu, out float dirt)
    {
        moss = Mathf.Lerp(0.55f, 0.80f, noise);
        shirasu = Mathf.Lerp(0.12f, 0.32f, macro);
        dirt = Mathf.Max(0f, 1f - moss - shirasu);
        float sum = moss + shirasu + dirt; moss /= sum; shirasu /= sum; dirt /= sum;
    }

    // ───────────────────────── 塗る ─────────────────────────
    [MenuItem("Edo/類型/庭の地表を塗る(白洲・苔・叩き土)")]
    public static void PaintMenu() => Debug.Log(Paint());

    public static string Paint()
    {
        var sb = new StringBuilder();
        sb.AppendLine(EnsureLayers());
        string err; var f = EdoSurfacePaint.OpenGarden(out err);
        if (f == null) { sb.AppendLine(err); return sb.ToString(); }

        string bk = EdoLandUse.SaveSplatBackup(f.td, "niwa");
        sb.AppendLine("退避: " + bk);
        Undo.RegisterCompleteObjectUndo(f.td.alphamapTextures, "庭の地表");
        Undo.RegisterCompleteObjectUndo(f.td, "庭の地表");

        int L = f.td.alphamapLayers;
        int zoneN = 0, texelN = 0, skipWater = 0, skipSteep = 0;
        foreach (var kind in new[] { "shirasu", "moss", "tataki" })
        {
            int zk = 0, tk = 0;
            foreach (var z in Zones(kind))
            {
                zk++; zoneN++;
                int ix0, iz0, ix1, iz1; PointRect(f, z.points, z.radius, out ix0, out iz0, out ix1, out iz1);
                int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
                if (w <= 0 || h <= 0) continue;
                var A = f.td.GetAlphamaps(ix0, iz0, w, h);
                for (int zz = 0; zz < h; zz++)
                    for (int xx = 0; xx < w; xx++)
                    {
                        int ix = ix0 + xx, iz = iz0 + zz;
                        if (f.td.GetSteepness((ix + 0.5f) / f.res, (iz + 0.5f) / f.res) > EdoSurfacePaint.STEEP_MAX)
                        { skipSteep++; continue; }
                        float wx = f.tp.x + (ix + 0.5f) * f.cell, wz = f.tp.z + (iz + 0.5f) * f.cell;
                        if (!NearAny(z.points, z.radius, wx, wz)) continue;
                        if (EdoSurfacePaint.InAny(f.water, new Vector2(wx, wz))) { skipWater++; continue; }
                        float noise = Mathf.PerlinNoise(wx * 0.15f + 3000f, wz * 0.15f + 3000f);
                        float macro = Mathf.PerlinNoise(wx * 0.04f + 7000f, wz * 0.04f + 7000f);
                        for (int l = 0; l < L; l++)
                        {
                            float target;
                            if (kind == "shirasu")
                            {
                                float shirasu, dirt; RecipeShirasu(noise, out shirasu, out dirt);
                                target = l == f.iShirasu ? shirasu : l == f.iD ? dirt : 0f;
                            }
                            else if (kind == "moss")
                            {
                                float moss, shirasu, dirt; RecipeMoss(noise, macro, out moss, out shirasu, out dirt);
                                target = l == f.iMoss ? moss : l == f.iShirasu ? shirasu : l == f.iD ? dirt : 0f;
                            }
                            else // tataki — 叩き土/締まった土は kouyuu の "dirt" 既定と同じ塗り(EDO-0372 §4.5)
                            {
                                float d, g, b; EdoSurfacePaint.Recipe("dirt", null, noise, macro, out d, out g, out b);
                                target = l == f.iD ? d : l == f.iG ? g : l == f.iB ? b : 0f;
                            }
                            A[zz, xx, l] = target;
                        }
                        tk++; texelN++;
                    }
                f.td.SetAlphamaps(ix0, iz0, A);
            }
            sb.AppendLine("  " + kind + ": " + zk + "印 " + tk + "texel");
        }
        f.terr.Flush(); EditorUtility.SetDirty(f.td); AssetDatabase.SaveAssets();
        sb.AppendLine(string.Format("→ 印 {0} / 塗った texel {1}(水面で見送り {2}・急斜面で見送り {3})",
                                     zoneN, texelN, skipWater, skipSteep));
        sb.AppendLine(Verify());
        return sb.ToString();
    }

    // ───────────────────────── 検める(実測) ─────────────────────────
    [MenuItem("Edo/類型/庭の地表を検める")]
    public static void VerifyMenu() => Debug.Log(Verify());

    /// <summary>塗った結果を地形から読み直し、印ごとに狙った層が十分乗っているか確かめる。
    /// ⛔ texel が足りない印は「未検査」— 合格と刷らない(規則19)。</summary>
    public static string Verify()
    {
        string err; var f = EdoSurfacePaint.OpenGarden(out err);
        if (f == null) return err;
        var sb = new StringBuilder("地表の突き合わせ(庭・EDO-0372):\n");
        int ok = 0, ng = 0, unchecked_ = 0;
        foreach (var kind in new[] { "shirasu", "moss", "tataki" })
        {
            foreach (var z in Zones(kind))
            {
                int ix0, iz0, ix1, iz1; PointRect(f, z.points, z.radius, out ix0, out iz0, out ix1, out iz1);
                int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
                if (w <= 0 || h <= 0) { unchecked_++; continue; }
                var A = f.td.GetAlphamaps(ix0, iz0, w, h);
                double sMain = 0, sSub = 0; int n = 0;
                for (int zz = 0; zz < h; zz++)
                    for (int xx = 0; xx < w; xx++)
                    {
                        int ix = ix0 + xx, iz = iz0 + zz;
                        float wx = f.tp.x + (ix + 0.5f) * f.cell, wz = f.tp.z + (iz + 0.5f) * f.cell;
                        if (!NearAny(z.points, z.radius, wx, wz)) continue;
                        n++;
                        if (kind == "shirasu") sMain += A[zz, xx, f.iShirasu];
                        else if (kind == "moss") { sMain += A[zz, xx, f.iMoss]; sSub += A[zz, xx, f.iShirasu]; }
                        else { sMain += A[zz, xx, f.iD]; sSub += A[zz, xx, f.iB]; }
                    }
                string nm = z.transform.parent != null ? z.transform.parent.parent != null
                    ? z.transform.parent.parent.name : z.transform.parent.name : z.name;
                if (n < EdoSurfacePaint.MIN_TEXELS)
                { unchecked_++; sb.AppendLine("  ？ " + nm + "/" + kind + " 未検査 — texel " + n); continue; }
                float mMain = (float)(sMain / n), mSub = (float)(sSub / n);
                bool pass = kind == "shirasu" ? mMain >= 0.55f
                          : kind == "moss" ? mMain >= 0.40f
                          : mMain + mSub >= 0.55f;
                if (pass) ok++; else ng++;
                sb.AppendLine("  " + (pass ? "⭕" : "✗") + " " + nm + "/" + kind + " n=" + n
                    + " 主層=" + mMain.ToString("F2") + (kind != "shirasu" ? " 副層=" + mSub.ToString("F2") : ""));
            }
        }
        sb.AppendLine("  → 合格 " + ok + " / 不合格 " + ng + " / 未検査 " + unchecked_);
        return sb.ToString();
    }
}
