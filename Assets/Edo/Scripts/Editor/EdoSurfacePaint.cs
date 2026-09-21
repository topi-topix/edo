using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEngine;

/// <summary>
/// 公有地(類型表 `type: "kouyuu"`)の地表を、表の <c>surface</c> 欄どおり地形のスプラットへ塗る(EDO-0319)。
///
/// ⭐ 塗るのは地形のスプラットで、類型ビルダーの持ち場ではない(ビルダーは駒を置く)。地表の輪。
///    表の <c>surface</c> を書き換えたら、このメニューをもう一度押す — 区画が変わっても同じ(EdoParcels.Get)。
/// ⛔ 地形は全邸で共有・Undo の外。塗る前に <see cref="EdoLandUse.SaveSplatBackup"/> で退避し、
///    区画の外・水面の中・急斜面(土手)は触らない。塗ったあとは <see cref="Verify"/> が実測で検める
///    (0 件を「合格」と読まない — texel 数が足りない区画は「未検査」と刷る)。
///
/// surface の語彙(類型表 §kouyuu): <c>grass</c>=刈られた草地 / <c>grass+kiribatake</c>=草地に桐畑の踏み跡 /
/// <c>dirt</c>=踏み固めた土(干場は草の混じる土・矢場は露地・火消屋敷は屋敷地の土)。
/// </summary>
public static class EdoSurfacePaint
{
    const float STEEP_MAX = 38f;      // これより急な所は土手 — 既存の塗りを残す
    const int   SUB = 3;              // texel の縁は 3×3 の副標本で被覆率を出す(縁のガタつきを抑える)
    const int   MIN_TEXELS = 6;       // これ未満の区画は分解能が足りず、検められない

    // 地形レイヤーは名前で引く(順序・パスに依らない)。L_dirt / L_grass / L_bare
    static int LayerIndex(TerrainData td, string key)
    {
        var ls = td.terrainLayers;
        for (int i = 0; i < ls.Length; i++)
            if (ls[i] != null && ls[i].name.ToLowerInvariant().Contains(key)) return i;
        return -1;
    }

    /// <summary>surface 欄 × kind → 草・裸地の重み(残りが土)。知らない語彙は false。</summary>
    public static bool Recipe(string surface, string kind, float noise, float macro, out float d, out float g, out float b)
    {
        d = g = b = 0f;
        surface = surface ?? "";
        if (surface.Contains("kiribatake"))   // 桐畑: 草地に畝間・踏み跡の裸地が斑に出る(広重「赤坂桐畑」)
        { g = Mathf.Lerp(0.50f, 0.78f, noise); b = Mathf.Lerp(0.04f, 0.16f, macro); }
        else if (surface == "grass")          // 刈られた草地
        { g = Mathf.Lerp(0.68f, 0.90f, noise); b = 0.03f; }
        else if (surface == "dirt")
        {
            if (kind == "hoshiba") { b = Mathf.Lerp(0.42f, 0.60f, noise); g = 0.10f; }   // 干場=踏み固め土(反物を干す庭。旧 Stage4_Splat の塗りを写した)
            else { b = Mathf.Lerp(0.58f, 0.74f, noise); g = 0.04f; }                      // 矢場の露地・火消屋敷の屋敷地
        }
        else return false;
        d = Mathf.Max(0f, 1f - g - b);
        return true;
    }

    // ---- 水面(WaterBody の輪郭) — 中の texel は塗らない ----
    static List<Vector2[]> WaterPolys()
    {
        var res = new List<Vector2[]>();
        foreach (var wb in Object.FindObjectsByType<WaterBody>(FindObjectsSortMode.None))
        {
            if (wb.outline == null || wb.outline.Count < 3) continue;
            var poly = new Vector2[wb.outline.Count];
            for (int i = 0; i < poly.Length; i++)
            { var w = wb.transform.TransformPoint(wb.outline[i]); poly[i] = new Vector2(w.x, w.z); }
            res.Add(poly);
        }
        return res;
    }

    static bool InAny(List<Vector2[]> polys, Vector2 p)
    {
        for (int i = 0; i < polys.Count; i++) if (EdoGeom.PIP(polys[i], p)) return true;
        return false;
    }

    class Frame
    {
        public Terrain terr; public TerrainData td; public Vector3 tp, ts; public int res; public float cell;
        public int iD, iG, iB; public List<Vector2[]> water;
    }

    static Frame Open(out string err)
    {
        err = null;
        var go = GameObject.Find(EdoLandUse.TerrainName);
        if (go == null) { err = "⛔ " + EdoLandUse.TerrainName + " が無い"; return null; }
        var f = new Frame { terr = go.GetComponent<Terrain>() };
        f.td = f.terr.terrainData; f.tp = f.terr.transform.position; f.ts = f.td.size;
        f.res = f.td.alphamapResolution; f.cell = f.ts.x / f.res;
        f.iD = LayerIndex(f.td, "dirt"); f.iG = LayerIndex(f.td, "grass"); f.iB = LayerIndex(f.td, "bare");
        if (f.iD < 0 || f.iG < 0 || f.iB < 0) { err = "⛔ 地形レイヤーに dirt/grass/bare が揃っていない"; return null; }
        f.water = WaterPolys();
        return f;
    }

    static void PixelRect(Frame f, Vector2[] poly, out int ix0, out int iz0, out int ix1, out int iz1)
    {
        float minX = float.MaxValue, maxX = float.MinValue, minZ = float.MaxValue, maxZ = float.MinValue;
        foreach (var p in poly)
        { minX = Mathf.Min(minX, p.x); maxX = Mathf.Max(maxX, p.x); minZ = Mathf.Min(minZ, p.y); maxZ = Mathf.Max(maxZ, p.y); }
        ix0 = Mathf.Max(0, Mathf.FloorToInt((minX - f.tp.x) / f.cell) - 1);
        ix1 = Mathf.Min(f.res - 1, Mathf.CeilToInt((maxX - f.tp.x) / f.cell) + 1);
        iz0 = Mathf.Max(0, Mathf.FloorToInt((minZ - f.tp.z) / f.cell) - 1);
        iz1 = Mathf.Min(f.res - 1, Mathf.CeilToInt((maxZ - f.tp.z) / f.cell) + 1);
    }

    /// <summary>この texel のうち、区画の内側で・水面の外の面積割合(0〜1)。急斜面なら 0。</summary>
    static float Coverage(Frame f, Vector2[] poly, int ix, int iz, out bool wet, out bool steep)
    {
        wet = steep = false;
        if (f.td.GetSteepness((ix + 0.5f) / f.res, (iz + 0.5f) / f.res) > STEEP_MAX) { steep = true; return 0f; }
        int inside = 0, drowned = 0;
        for (int sz = 0; sz < SUB; sz++)
            for (int sx = 0; sx < SUB; sx++)
            {
                var p = new Vector2(f.tp.x + (ix + (sx + 0.5f) / SUB) * f.cell, f.tp.z + (iz + (sz + 0.5f) / SUB) * f.cell);
                if (!EdoGeom.PIP(poly, p)) continue;
                if (InAny(f.water, p)) { drowned++; continue; }
                inside++;
            }
        wet = drowned > 0 && inside == 0;
        return inside / (float)(SUB * SUB);
    }

    static IEnumerable<EdoTypologyBuilder.Spec> Kouyuu()
    {
        EdoTypologyBuilder.LoadTable();      // 表を書き換えたあとの再実行に備え、毎回読み直す
        foreach (var s in EdoTypologyBuilder.Table.Values)
            if (s.type == "kouyuu" && !s.Hand) yield return s;
    }

    // ───────────────────────── 塗る ─────────────────────────
    [MenuItem("Edo/土地利用/公有地の地表を塗る(類型表の surface)")]
    public static void PaintMenu() { Debug.Log(Paint()); }

    public static string Paint()
    {
        string err; var f = Open(out err); if (f == null) return err;
        var sb = new StringBuilder();
        string bk = EdoLandUse.SaveSplatBackup(f.td, "kouyuu");
        sb.AppendLine("退避: " + (bk ?? "(層数が4でなく省略)"));
        Undo.RegisterCompleteObjectUndo(f.td.alphamapTextures, "公有地の地表");
        Undo.RegisterCompleteObjectUndo(f.td, "公有地の地表");

        int L = f.td.alphamapLayers;
        foreach (var s in Kouyuu())
        {
            var poly = EdoParcels.Get(s.id);
            if (poly == null) { sb.AppendLine("  ✗ " + s.id + " — 区画が parcels.json に無い"); continue; }
            float td0, tg0, tb0;
            if (!Recipe(s.surface, s.kind, 0.5f, 0.5f, out td0, out tg0, out tb0))
            { sb.AppendLine("  ✗ " + s.id + " — surface='" + s.surface + "' の塗り方が無い(語彙は grass / grass+kiribatake / dirt)"); continue; }

            int ix0, iz0, ix1, iz1; PixelRect(f, poly, out ix0, out iz0, out ix1, out iz1);
            int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
            var A = f.td.GetAlphamaps(ix0, iz0, w, h);
            int painted = 0, wetN = 0, steepN = 0;
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    bool wet, steep;
                    float cov = Coverage(f, poly, ix0 + xx, iz0 + zz, out wet, out steep);
                    if (wet) wetN++; if (steep) steepN++;
                    if (cov <= 0.001f) continue;
                    float wx = f.tp.x + (ix0 + xx + 0.5f) * f.cell, wz = f.tp.z + (iz0 + zz + 0.5f) * f.cell;
                    float noise = Mathf.PerlinNoise(wx * 0.11f + 5000f, wz * 0.11f + 5000f);
                    float macro = Mathf.PerlinNoise(wx * 0.035f + 9000f, wz * 0.035f + 9000f);
                    float d, g, b; Recipe(s.surface, s.kind, noise, macro, out d, out g, out b);
                    float sum = d + g + b; d /= sum; g /= sum; b /= sum;
                    for (int l = 0; l < L; l++)
                    {
                        float target = l == f.iD ? d : l == f.iG ? g : l == f.iB ? b : 0f;
                        A[zz, xx, l] = Mathf.Lerp(A[zz, xx, l], target, cov);
                    }
                    painted++;
                }
            f.td.SetAlphamaps(ix0, iz0, A);
            sb.AppendLine("  " + s.id + " [" + s.surface + (string.IsNullOrEmpty(s.kind) ? "" : "/" + s.kind) + "] 塗った texel=" + painted
                + (wetN > 0 ? " 水面=" + wetN : "") + (steepN > 0 ? " 急斜面=" + steepN : ""));

            // 草の詳細(草の房)も同じ範囲で草の層から作り直す — 塗った土の上に房が残らないように
            var mask = new EdoLandUse.BakeMask { Feather = 0.01f };
            mask.RectXZ = new Rect(f.tp.x + ix0 * f.cell, f.tp.z + iz0 * f.cell, w * f.cell, h * f.cell);
            EdoLandUse.RebuildGrass(f.terr, f.td, mask);
        }
        f.terr.Flush(); EditorUtility.SetDirty(f.td); AssetDatabase.SaveAssets();
        sb.AppendLine(Verify());
        return sb.ToString();
    }

    // ───────────────────────── 検める(実測) ─────────────────────────
    [MenuItem("Edo/土地利用/公有地の地表を検める")]
    public static void VerifyMenu() { Debug.Log(Verify()); }

    /// <summary>塗った結果を地形から読み直し、区画ごとに表の surface と突き合わせる。
    /// ⛔ texel が <see cref="MIN_TEXELS"/> 未満の区画は「未検査」— 合格と刷らない(規則19)。</summary>
    public static string Verify()
    {
        string err; var f = Open(out err); if (f == null) return err;
        var sb = new StringBuilder("地表の突き合わせ(公有地):\n");
        int ng = 0, unchecked_ = 0, ok = 0;
        foreach (var s in Kouyuu())
        {
            var poly = EdoParcels.Get(s.id); if (poly == null) { ng++; sb.AppendLine("  ✗ " + s.id + " 区画なし"); continue; }
            int ix0, iz0, ix1, iz1; PixelRect(f, poly, out ix0, out iz0, out ix1, out iz1);
            int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
            var A = f.td.GetAlphamaps(ix0, iz0, w, h);
            double sD = 0, sG = 0, sB = 0; int n = 0;
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    bool wet, steep;
                    if (Coverage(f, poly, ix0 + xx, iz0 + zz, out wet, out steep) < 0.999f) continue;   // 全面が区画の内の texel だけ数える
                    sD += A[zz, xx, f.iD]; sG += A[zz, xx, f.iG]; sB += A[zz, xx, f.iB]; n++;
                }
            if (n < MIN_TEXELS)
            { unchecked_++; sb.AppendLine("  ？ " + s.id + " 未検査 — 全面が区画内の texel が " + n + "(分解能 " + f.cell.ToString("F1") + "m/texel)"); continue; }
            float mD = (float)(sD / n), mG = (float)(sG / n), mB = (float)(sB / n);
            bool pass;
            if ((s.surface ?? "").Contains("kiribatake")) pass = mG >= 0.45f;
            else if (s.surface == "grass") pass = mG >= 0.60f;
            else if (s.surface == "dirt") pass = mB + mD >= 0.85f && mG <= 0.15f;
            else pass = false;
            if (pass) ok++; else ng++;
            sb.AppendLine("  " + (pass ? "⭕" : "✗") + " " + s.id + " [" + s.surface + "] n=" + n
                + " 土=" + mD.ToString("F2") + " 草=" + mG.ToString("F2") + " 裸=" + mB.ToString("F2"));
        }
        sb.AppendLine("  → 合格 " + ok + " / 不合格 " + ng + " / 未検査 " + unchecked_);
        return sb.ToString();
    }
}
