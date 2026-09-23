using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

/// <summary>
/// 指図の <c>surface</c> 欄どおり、指図で建てる敷地の地表を地形のスプラットへ塗る(EDO-0422)。
///
/// ⭐ 塗るのは地形のスプラットで、指図ビルダーの持ち場ではない(ビルダーは駒を置く)。
///    <see cref="EdoSurfacePaint"/>(公有地)・<see cref="EdoGardenSurfacePaint"/>(類型の庭)と同じ地表の輪。
///    指図の面・庭・参道を動かしたら、このメニューをもう一度押す。
/// ⛔ 座標も塗りの割合もここに書かない — 範囲は指図の既存の欄(<c>polygon</c> / <c>terraces</c> /
///    <c>gardens</c> / <c>sando.area</c>)から、割合は <c>surface.recipes</c> から読む(規則4・11)。
/// ⛔ 地形は全邸で共有・Undo の外。塗る前に <see cref="EdoLandUse.SaveSplatBackup"/> で退避する。
///
/// 塗り方: <c>surface.extent</c> に挙げた範囲の和を**塗り直す範囲**とし、その中の texel は
/// 前の塗りを残さず <c>surface.zones</c> の塗りで置き換える(旧い敷地割の塗りの取り残しを消すため)。
/// zones は並んだ順に重ね、後の zone が勝つ。texel の縁は副標本で持ち主の割合を出して混ぜる。
///
/// <c>surface</c> 欄の形:
/// <code>
/// "surface": {
///   "extent": ["polygon", "sando.area"],
///   "recipes": { "&lt;名&gt;": { "grass": [lo, hi], "bare": [lo, hi], "dirt": "rest", ... } },
///   "zones": [ { "name": "社叢", "area": "polygon", "recipe": "&lt;名&gt;" },
///              { "name": "境内", "area": "terrace:Keidai", "recipe": ... },
///              { "name": "白洲", "area": "garden:白洲", "recipe": ... },
///              { "name": "参道", "area": "sando.area", "recipe": ... } ]
/// }
/// </code>
/// 層の名は地形レイヤー名の一部(dirt / grass / bare / shirasu / moss)。値は [lo, hi] を斑(Perlin)で振る。
/// <c>"rest"</c> の層は 1 − 他の和(1つだけ)。
/// </summary>
public static class EdoSashizuSurfacePaint
{
    const int SUB = 4;                 // 1 texel(4m)を 1m 刻みの副標本で持ち主を数える
    static readonly CultureInfo IC = CultureInfo.InvariantCulture;
    static readonly string[] LayerKeys = { "dirt", "grass", "bare", "shirasu", "moss" };

    [MenuItem("Edo/地表/山王社の地表を塗る(指図の surface)")]
    public static void PaintSannoMenu() { Debug.Log(Paint(EdoSannoShaBuilder.SashizuRel)); }

    [MenuItem("Edo/地表/山王社の地表を検める")]
    public static void VerifySannoMenu() { Debug.Log(Verify(EdoSannoShaBuilder.SashizuRel)); }

    // ───────────────────────── 指図を読む ─────────────────────────
    class Zone { public string name, area; public Recipe recipe; public List<Vector2[]> polys; }
    class Recipe
    {
        public string name; public string rest;
        public Dictionary<string, Vector2> range = new Dictionary<string, Vector2>();
    }
    class Plan
    {
        public List<Vector2[]> extent = new List<Vector2[]>();
        public List<Zone> zones = new List<Zone>();
        public List<string> notes = new List<string>();
    }

    static object G(Dictionary<string, object> d, string k)
    { object v; return d != null && d.TryGetValue(k, out v) ? v : null; }
    static float Cv(object o) { return Convert.ToSingle(o, IC); }

    static Vector2[] WorldPoly(List<object> pts, Func<float, float, Vector2> map)
    {
        var r = new Vector2[pts.Count];
        for (int i = 0; i < r.Length; i++)
        { var p = (List<object>)pts[i]; r[i] = map(Cv(p[0]), Cv(p[1])); }
        return r;
    }

    static Plan Load(string rel, out string err)
    {
        err = null;
        string path = Path.Combine(Directory.GetParent(Application.dataPath).FullName, rel);
        var doc = EdoMiniJson.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
        var surf = G(doc, "surface") as Dictionary<string, object>;
        if (surf == null) { err = "⛔ " + rel + " に surface 欄が無い(塗り方は指図に書く・ここで発明しない)"; return null; }

        // 境内グリッド (u,v)[間] → 世界
        var gk = G(G(doc, "grid") as Dictionary<string, object>, "keidai") as Dictionary<string, object>;
        float ken = Cv(G(G(doc, "const") as Dictionary<string, object>, "ken"));
        Func<float, float, Vector2> uv = (u, v) => new Vector2(
            Cv(G(gk, "x0")) + (u * Cv(G(gk, "ux")) + v * Cv(G(gk, "vx"))) * ken,
            Cv(G(gk, "z0")) + (u * Cv(G(gk, "uz")) + v * Cv(G(gk, "vz"))) * ken);
        Func<float, float, Vector2> world = (x, z) => new Vector2(x, z);

        Func<string, List<Vector2[]>> resolve = area =>
        {
            var res = new List<Vector2[]>();
            if (area == "polygon") res.Add(WorldPoly((List<object>)G(doc, "polygon"), world));
            else if (area == "sando.area") res.Add(WorldPoly((List<object>)G(G(doc, "sando") as Dictionary<string, object>, "area"), world));
            else if (area.StartsWith("terrace:") || area.StartsWith("garden:"))
            {
                bool ter = area.StartsWith("terrace:");
                string nm = area.Substring(area.IndexOf(':') + 1);
                foreach (var o in (List<object>)G(doc, ter ? "terraces" : "gardens"))
                {
                    var t = o as Dictionary<string, object>;
                    if ((G(t, "name") as string) != nm) continue;
                    var pts = (G(t, ter ? "uv" : "poly") ?? G(t, "poly")) as List<object>;
                    if (pts != null && pts.Count >= 3) res.Add(WorldPoly(pts, uv));
                }
            }
            return res;
        };

        var plan = new Plan();
        foreach (var o in (List<object>)G(surf, "extent"))
        {
            var ps = resolve((string)o);
            if (ps.Count == 0) { err = "⛔ surface.extent '" + o + "' が指図の中に見つからない"; return null; }
            plan.extent.AddRange(ps);
        }
        var recipes = new Dictionary<string, Recipe>();
        foreach (var kv in (Dictionary<string, object>)G(surf, "recipes"))
        {
            var r = new Recipe { name = kv.Key };
            foreach (var lk in (Dictionary<string, object>)kv.Value)
            {
                if (lk.Key.StartsWith("_") || lk.Key == "acc") continue;
                if (lk.Value is string && (string)lk.Value == "rest") { r.rest = lk.Key; continue; }
                var ab = lk.Value as List<object>;
                if (ab == null || ab.Count != 2) { err = "⛔ recipes." + kv.Key + "." + lk.Key + " は [lo, hi] か \"rest\""; return null; }
                r.range[lk.Key] = new Vector2(Cv(ab[0]), Cv(ab[1]));
            }
            recipes[kv.Key] = r;
        }
        foreach (var o in (List<object>)G(surf, "zones"))
        {
            var z = o as Dictionary<string, object>;
            var zone = new Zone { name = G(z, "name") as string, area = G(z, "area") as string };
            string rn = G(z, "recipe") as string;
            if (rn == null || !recipes.TryGetValue(rn, out zone.recipe))
            { err = "⛔ zones[" + zone.name + "] の recipe '" + rn + "' が recipes に無い"; return null; }
            zone.polys = resolve(zone.area);
            if (zone.polys.Count == 0) { plan.notes.Add("✗ " + zone.name + " — area '" + zone.area + "' が指図に無い(塗らない)"); continue; }
            plan.zones.Add(zone);
        }
        return plan;
    }

    // ───────────────────────── 塗り ─────────────────────────
    /// <summary>この点の持ち主の zone(後勝ち)。塗り直す範囲の外は -2、範囲の内でどの zone にも入らなければ -1。</summary>
    static int Owner(Plan plan, Vector2 p)
    {
        if (!EdoSurfacePaint.InAny(plan.extent, p)) return -2;
        for (int i = plan.zones.Count - 1; i >= 0; i--)
            if (EdoSurfacePaint.InAny(plan.zones[i].polys, p)) return i;
        return -1;
    }

    static float[] Target(EdoSurfacePaint.Frame f, int[] idx, Recipe r, float wx, float wz, int L)
    {
        var t = new float[L]; float sum = 0f;
        for (int k = 0; k < LayerKeys.Length; k++)
        {
            Vector2 ab;
            if (idx[k] < 0 || !r.range.TryGetValue(LayerKeys[k], out ab)) continue;
            float n = Mathf.PerlinNoise(wx * 0.11f + 1000f * (k + 1), wz * 0.11f + 1000f * (k + 1));
            float v = Mathf.Lerp(ab.x, ab.y, n);
            t[idx[k]] += v; sum += v;
        }
        if (r.rest != null)
        {
            int ri = idx[Array.IndexOf(LayerKeys, r.rest)];
            if (ri >= 0) { t[ri] += Mathf.Max(0f, 1f - sum); sum += Mathf.Max(0f, 1f - sum); }
        }
        if (sum > 1e-4f) for (int l = 0; l < L; l++) t[l] /= sum;
        return t;
    }

    static int[] LayerIdx(EdoSurfacePaint.Frame f)
    {
        var idx = new int[LayerKeys.Length];
        for (int k = 0; k < LayerKeys.Length; k++) idx[k] = EdoSurfacePaint.LayerIndex(f.td, LayerKeys[k]);
        return idx;
    }

    static void ExtentRect(EdoSurfacePaint.Frame f, Plan plan, out int ix0, out int iz0, out int ix1, out int iz1)
    {
        var all = new List<Vector2>();
        foreach (var p in plan.extent) all.AddRange(p);
        EdoSurfacePaint.PixelRect(f, all.ToArray(), out ix0, out iz0, out ix1, out iz1);
    }

    public static string Paint(string rel)
    {
        var sb = new StringBuilder("地表(指図の surface): " + rel + "\n");
        string err; var plan = Load(rel, out err); if (plan == null) return err;
        foreach (var n in plan.notes) sb.AppendLine("  " + n);
        sb.AppendLine(EdoGardenSurfacePaint.EnsureLayers());
        var f = EdoSurfacePaint.OpenGarden(out err); if (f == null) return sb + err;
        var idx = LayerIdx(f);
        foreach (var z in plan.zones)
            foreach (var kv in z.recipe.range)
                if (idx[Array.IndexOf(LayerKeys, kv.Key)] < 0) return sb + "⛔ 地形レイヤーに '" + kv.Key + "' が無い";

        sb.AppendLine("退避: " + EdoLandUse.SaveSplatBackup(f.td, "sashizu_surface"));
        Undo.RegisterCompleteObjectUndo(f.td.alphamapTextures, "指図の地表");
        Undo.RegisterCompleteObjectUndo(f.td, "指図の地表");

        int ix0, iz0, ix1, iz1; ExtentRect(f, plan, out ix0, out iz0, out ix1, out iz1);
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1, L = f.td.alphamapLayers;
        var A = f.td.GetAlphamaps(ix0, iz0, w, h);
        var count = new float[plan.zones.Count];
        int painted = 0, steepN = 0, wetN = 0, orphan = 0;
        var own = new int[SUB * SUB];
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                int ix = ix0 + xx, iz = iz0 + zz;
                float wx = f.tp.x + (ix + 0.5f) * f.cell, wz = f.tp.z + (iz + 0.5f) * f.cell;
                int inExt = 0;
                for (int s = 0; s < SUB * SUB; s++)
                {
                    var p = new Vector2(f.tp.x + (ix + (s % SUB + 0.5f) / SUB) * f.cell, f.tp.z + (iz + (s / SUB + 0.5f) / SUB) * f.cell);
                    own[s] = Owner(plan, p);
                    if (own[s] != -2 && EdoSurfacePaint.InAny(f.water, p)) own[s] = -2;
                    if (own[s] != -2) inExt++;
                }
                if (inExt == 0) continue;
                if (f.td.GetSteepness((ix + 0.5f) / f.res, (iz + 0.5f) / f.res) > EdoSurfacePaint.STEEP_MAX) { steepN++; continue; }
                // 持ち主ごとの割合で狙いを混ぜる。範囲の外の副標本は前の塗りを残す
                var tgt = new float[L]; float wIn = 0f;
                for (int s = 0; s < SUB * SUB; s++)
                {
                    if (own[s] == -2) continue;
                    if (own[s] == -1) { orphan++; continue; }
                    var t = Target(f, idx, plan.zones[own[s]].recipe, wx, wz, L);
                    for (int l = 0; l < L; l++) tgt[l] += t[l];
                    wIn += 1f; count[own[s]] += 1f / (SUB * SUB);
                }
                if (wIn <= 0f) continue;
                float cov = wIn / (SUB * SUB);
                for (int l = 0; l < L; l++) A[zz, xx, l] = Mathf.Lerp(A[zz, xx, l], tgt[l] / wIn, cov);
                painted++;
            }
        f.td.SetAlphamaps(ix0, iz0, A);
        var mask = new EdoLandUse.BakeMask { Feather = 0.01f };
        mask.RectXZ = new Rect(f.tp.x + ix0 * f.cell, f.tp.z + iz0 * f.cell, w * f.cell, h * f.cell);
        EdoLandUse.RebuildGrass(f.terr, f.td, mask);
        f.terr.Flush(); EditorUtility.SetDirty(f.td); AssetDatabase.SaveAssets();

        for (int i = 0; i < plan.zones.Count; i++)
            sb.AppendLine("  " + plan.zones[i].name + " [" + plan.zones[i].recipe.name + "] " + count[i].ToString("F1") + " texel");
        sb.AppendLine("→ 塗った texel " + painted + "(急斜面で見送り " + steepN + ")"
            + (orphan > 0 ? " ⚠ 範囲の内でどの zone にも入らない副標本 " + orphan : ""));
        sb.AppendLine(Verify(rel));
        return sb.ToString();
    }

    // ───────────────────────── 検める(実測) ─────────────────────────
    /// <summary>塗り直す範囲の内で、副標本が全部同じ zone に入る texel を読み直し、層ごとの重みが
    /// その zone の recipe の幅(±0.05)に入るかを数える。⛔ 入らない texel = 旧い塗りの取り残しか塗り損じ。
    /// 急斜面で見送った texel と zone が 1 texel も持たない zone は「未検査」と刷る(規則19)。</summary>
    public static string Verify(string rel)
    {
        string err; var plan = Load(rel, out err); if (plan == null) return err;
        var f = EdoSurfacePaint.OpenGarden(out err); if (f == null) return err;
        var idx = LayerIdx(f);
        int ix0, iz0, ix1, iz1; ExtentRect(f, plan, out ix0, out iz0, out ix1, out iz1);
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var A = f.td.GetAlphamaps(ix0, iz0, w, h);
        var n = new int[plan.zones.Count]; var bad = new int[plan.zones.Count];
        int steepN = 0; var worst = new string[plan.zones.Count];
        for (int zz = 0; zz < h; zz++)
            for (int xx = 0; xx < w; xx++)
            {
                int ix = ix0 + xx, iz = iz0 + zz, o0 = int.MinValue; bool uni = true;
                for (int s = 0; s < SUB * SUB && uni; s++)
                {
                    var p = new Vector2(f.tp.x + (ix + (s % SUB + 0.5f) / SUB) * f.cell, f.tp.z + (iz + (s / SUB + 0.5f) / SUB) * f.cell);
                    int o = Owner(plan, p); if (EdoSurfacePaint.InAny(f.water, p)) o = -2;
                    if (o0 == int.MinValue) o0 = o; else if (o != o0) uni = false;
                }
                if (!uni || o0 < 0) continue;
                if (f.td.GetSteepness((ix + 0.5f) / f.res, (iz + 0.5f) / f.res) > EdoSurfacePaint.STEEP_MAX) { steepN++; continue; }
                var r = plan.zones[o0].recipe; n[o0]++;
                // recipe の幅を、他の層との正規化を見込んで緩めずに読む: 各層 [lo, hi] の外 0.05 超で不合格
                float fixedSum = 0f; foreach (var kv in r.range) fixedSum += kv.Value.x;
                bool ok = true; string why = null;
                for (int k = 0; k < LayerKeys.Length && ok; k++)
                {
                    if (idx[k] < 0) continue;
                    float v = A[zz, xx, idx[k]];
                    Vector2 ab; float lo, hi;
                    if (r.range.TryGetValue(LayerKeys[k], out ab)) { lo = ab.x; hi = ab.y; }
                    else if (LayerKeys[k] == r.rest)
                    {
                        float maxOthers = 0f, minOthers = 0f;
                        foreach (var kv in r.range) { maxOthers += kv.Value.y; minOthers += kv.Value.x; }
                        lo = Mathf.Max(0f, 1f - maxOthers); hi = Mathf.Max(0f, 1f - minOthers);
                    }
                    else { lo = 0f; hi = 0f; }
                    if (v < lo - 0.05f || v > hi + 0.05f) { ok = false; why = LayerKeys[k] + "=" + v.ToString("F2") + "(狙い " + lo.ToString("F2") + "〜" + hi.ToString("F2") + ")"; }
                }
                if (!ok) { bad[o0]++; if (worst[o0] == null) worst[o0] = why + " @(" + (f.tp.x + (ix + 0.5f) * f.cell).ToString("F0") + "," + (f.tp.z + (iz + 0.5f) * f.cell).ToString("F0") + ")"; }
            }
        var sb = new StringBuilder("地表の突き合わせ(指図の surface・硬い条件: 狙いの幅の外の texel 0):\n");
        int ng = 0, un = 0;
        for (int i = 0; i < plan.zones.Count; i++)
        {
            if (n[i] == 0) { un++; sb.AppendLine("  ？ " + plan.zones[i].name + " 未検査 — 全面が一つの zone に入る texel が無い(分解能 " + f.cell.ToString("F1") + "m/texel)"); continue; }
            if (bad[i] > 0) ng++;
            sb.AppendLine("  " + (bad[i] == 0 ? "⭕" : "✗") + " " + plan.zones[i].name + " n=" + n[i] + " 外れ=" + bad[i] + (worst[i] != null ? " 例 " + worst[i] : ""));
        }
        sb.AppendLine("  → 不合格 " + ng + " / 未検査 " + un + " / 急斜面で見送り " + steepN + " texel(未検査)");
        return sb.ToString();
    }
}
