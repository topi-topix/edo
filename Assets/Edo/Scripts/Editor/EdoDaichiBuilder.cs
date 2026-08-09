// 溜池端(桐畑通り)の町代地2区画 + 横田・土岐拡張部の造成 (2026-08-09)
//   赤=芝青松寺門前町代地(約83m) / 黄=芝永井町代地(約129m)。黒田邸表門前の通りの溜池側に
//   奥行き約10間の町屋列。区画=ユーザー下書き線。
// 造成方針(ユーザー指示: 溜池掘削で現況高さが不正確なため必要な整地・造成は可):
//   町代地=街路側縁の高さを通した平場(ロフト)、背後は溜池への土手。
//   横田・土岐の拡張水没部=水面(6.6)+1.0mの棚(7.6)へ盛土。最後に溜池のsnapを現況から取り直す。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoDaichiBuilder
{
    // ---------- 区画 (下書き線) ----------
    // SW辺(街路側)を [0]->[1] とする
    public static Vector2[] SeishojiPoly = {
        new Vector2(-382.06f,417.87f), new Vector2(-446.57f,471.25f),
        new Vector2(-435.76f,486.73f), new Vector2(-370.28f,431.37f) };
    public static Vector2[] NagaichoPoly = {
        new Vector2(-451.01f,474.71f), new Vector2(-551.60f,555.83f),
        new Vector2(-539.25f,569.83f), new Vector2(-438.79f,489.76f) };

    const float WATER_Y = 6.6f;      // 溜池
    const float SHELF_Y = 7.6f;      // 屋敷拡張部の盛土棚 = 水面+1.0
    const float ES = 1.818f;

    public static Terrain T() { return EdoTameikeKitaBuilder.T(); }
    public static float Ground(float x, float z) { return EdoTameikeKitaBuilder.Ground(x, z); }

    static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) inside = !inside;
        return inside;
    }
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

    // ---------- Stage 0: backup ----------
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

    // ---------- Stage 1: 造成 ----------
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

        // 町代地: 街路側縁のロフト(現況を先にサンプルしてから書く)
        var strips = new[] { SeishojiPoly, NagaichoPoly };
        var lofts = new List<float[]>(); var axes = new List<Vector2>(); var lens = new List<float>();
        foreach (var poly in strips)
        {
            Vector2 A = poly[0], B = poly[1];
            Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
            int n = Mathf.CeilToInt(len / 2f) + 1;
            var hs = new float[n];
            Vector2 inw = new Vector2(-axis.y, axis.x); // SW辺の左法線=NE(敷地内向き) ※検証: PIPで確認して反転
            var probe = A + axis * (len * 0.5f) + inw * 5f;
            if (!PIP(poly, probe)) inw = -inw;
            for (int i = 0; i < n; i++)
            {
                var sp = A + axis * Mathf.Min(i * 2f, len) - inw * 1.5f; // 街路側1.5m外
                hs[i] = Ground(sp.x, sp.y);
            }
            // 移動平均で平滑
            var sm = new float[n];
            for (int i = 0; i < n; i++)
            {
                float s = 0; int c = 0;
                for (int k = -3; k <= 3; k++) { int j = Mathf.Clamp(i + k, 0, n - 1); s += hs[j]; c++; }
                sm[i] = s / c;
            }
            lofts.Add(sm); axes.Add(axis); lens.Add(len);
        }

        // 屋敷拡張部(横田・土岐)のポリゴン
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
                // --- 町代地: 内側=ロフト平場 / 外側10m=土手(盛りのみ) ---
                for (int si = 0; si < 2; si++)
                {
                    var poly = strips[si];
                    Vector2 A = poly[0]; var axis = axes[si]; var loft = lofts[si]; float len = lens[si];
                    float tpar = Mathf.Clamp(Vector2.Dot(p - A, axis), 0, len);
                    int li = Mathf.Clamp(Mathf.RoundToInt(tpar / 2f), 0, loft.Length - 1);
                    float hsv = loft[li] - 0.10f;
                    if (PIP(poly, p)) { target = hsv; }
                    else
                    {
                        float d = DistToPoly(poly, p);
                        if (d <= 10f)
                        {
                            float s = d / 10f; s = s * s * (3 - 2 * s);
                            float bank = Mathf.Lerp(hsv, cur, s);
                            if (bank > target) target = Mathf.Max(cur, bank) == bank ? bank : target;
                            if (bank > cur && bank > target) target = bank;
                            if (bank > cur) target = Mathf.Max(target, bank); // 盛りのみ(街路は既に高いので不変)
                        }
                    }
                }
                // --- 屋敷拡張部: 水没・低地を棚7.6へ(盛りのみ)、外側8mは土手 ---
                foreach (var ep in new[] { yok, tok })
                {
                    if (PIP(ep, p)) { if (target < SHELF_Y && cur < SHELF_Y) target = Mathf.Max(target, SHELF_Y); }
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
        // 変更セルのみ 3x3 平滑 x2
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
        // 溜池 snap を現況から取り直し (flatten順 z*sW+x = WaterBaker と同順)
        var wbT = UnityEngine.Object.FindObjectsByType<WaterBody>(FindObjectsSortMode.None).First(x => x.gameObject.name == "Tameike");
        var snapH = td.GetHeights(wbT.sX, wbT.sZ, wbT.sW, wbT.sH);
        var snap = new float[wbT.sW * wbT.sH];
        for (int z2 = 0; z2 < wbT.sH; z2++) for (int x2 = 0; x2 < wbT.sW; x2++) snap[z2 * wbT.sW + x2] = snapH[z2, x2];
        wbT.snap = snap; wbT.hasSnap = true;
        EditorUtility.SetDirty(wbT);
        return "graded cells=" + nChanged + " rect=" + w + "x" + h + " / Tameike snap retaken " + wbT.sW + "x" + wbT.sH;
    }

    // ---------- Stage 2: 町屋列 ----------
    // サンプル店群(Edo_Shops_Sample/ShopGroup)の合成店をコピーして並べる。前面=ローカル+Z。
    public class Lot { public string kind; public float width; public Lot(string k, float w) { kind = k; width = w; } }

    public static string Stage2_Machiya(string groupName, Vector2[] poly, string[] pattern, int seed)
    {
        var root = GameObject.Find(groupName);
        if (root != null && root.transform.Find("Row") != null) return "SKIP: " + groupName + "/Row exists";
        var rowG = Group(groupName, "Row");
        var propsG = Group(groupName, "Props");
        var rnd = new System.Random(seed);
        Vector2 A = poly[0], B = poly[1];
        Vector2 axis = (B - A).normalized; float len = (B - A).magnitude;
        Vector2 inw = new Vector2(-axis.y, axis.x);
        if (!PIP(poly, A + axis * (len * 0.5f) + inw * 5f)) inw = -inw;
        Vector2 outw = -inw; // 街路向き
        float ryFace = Mathf.Atan2(outw.x, outw.y) * Mathf.Rad2Deg;
        var sample = GameObject.Find("Edo_Shops_Sample");
        Transform shopSrc = sample != null ? sample.transform.Find("ShopGroup") : null;
        var made = 0;
        float tcur = 1.5f;
        int pi = 0;
        var sb = new System.Text.StringBuilder();
        while (tcur < len - 8f)
        {
            string kind = pattern[pi % pattern.Length]; pi++;
            GameObject go = null; float wLot;
            if (kind.StartsWith("Shop_") && shopSrc != null)
            {
                var src = shopSrc.Find(kind);
                if (src == null) { sb.AppendLine("missing sample " + kind); break; }
                go = UnityEngine.Object.Instantiate(src.gameObject);
                wLot = 9.2f;
                if (kind.Contains("大店") || kind.Contains("茶屋")) wLot = 15.0f;
            }
            else if (kind == "Machiya")
            {
                var a = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Edo/Prefabs/Machiya.prefab");
                go = (GameObject)PrefabUtility.InstantiatePrefab(a);
                wLot = 7.8f;
            }
            else { sb.AppendLine("unknown kind " + kind); break; }
            if (tcur + wLot > len - 1.5f) { UnityEngine.Object.DestroyImmediate(go); break; }
            go.name = kind + "_" + made;
            go.transform.SetParent(rowG, true);
            go.transform.rotation = Quaternion.Euler(0, ryFace + ((float)rnd.NextDouble() * 1.6f - 0.8f), 0);
            // 中心を仮置き→バウンズで「前面を街路縁-1.0m内側」「走り中心=ロット中心」に合わせ
            Vector2 lotC = A + axis * (tcur + wLot * 0.5f) + inw * 8.0f;
            go.transform.position = new Vector3(lotC.x, 20, lotC.y);
            var rs = go.GetComponentsInChildren<Renderer>();
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            float frontProj = b.center.x * outw.x + b.center.z * outw.y + ProjHalf(b, outw);
            Vector2 frontLine = A + inw * 1.0f;
            float lineProj = frontLine.x * outw.x + frontLine.y * outw.y;
            float shiftOut = lineProj - frontProj;
            float cProj = b.center.x * axis.x + b.center.z * axis.y;
            float targetC = Vector2.Dot(A + axis * (tcur + wLot * 0.5f), axis);
            float shiftAlong = targetC - cProj;
            go.transform.position += new Vector3(outw.x * shiftOut + axis.x * shiftAlong, 0, outw.y * shiftOut + axis.y * shiftAlong);
            // 接地
            var b2 = rs[0].bounds; foreach (var r in rs) b2.Encapsulate(r.bounds);
            float g = Ground(b2.center.x, b2.center.z);
            go.transform.position += new Vector3(0, (g - 0.08f) - b2.min.y, 0);
            made++;
            tcur += wLot + 0.4f;
        }
        // 木戸+木戸番屋を両端に (木戸=町境)
        PlaceKido(propsG, A, axis, inw, 0f, "Kido_S");
        PlaceKido(propsG, A, axis, inw, len, "Kido_N");
        // 裏手に井戸2
        for (int i = 0; i < 2; i++)
        {
            var e = new EdoTameikeKitaBuilder.Estate { poly = poly, front = 0, gateT = 0.5f };
            Vector2 wp = A + axis * (len * (0.3f + 0.4f * i)) + inw * 15.5f;
            WellAt(propsG, wp);
        }
        return groupName + " row done: " + made + " buildings\n" + sb;
    }
    static float ProjHalf(Bounds b, Vector2 axis)
    {
        return Mathf.Abs(b.extents.x * axis.x) + Mathf.Abs(b.extents.z * axis.y);
    }
    static void PlaceKido(Transform parent, Vector2 A, Vector2 axis, Vector2 inw, float tpos, string name)
    {
        var kidoA = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/edogoyomi/es_kido/kido_open.obj");
        var banA = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/edogoyomi/es_kidobanya/kidobanya.obj");
        if (kidoA == null) return;
        // 木戸は街路を走り方向に横切る向き(通行方向=axis)。街路は SW側 → 中心を縁から外へ5m
        Vector2 kc = A + axis * Mathf.Clamp(tpos, 2f, 9999f) - inw * 5.0f;
        float ry = Mathf.Atan2(axis.x, axis.y) * Mathf.Rad2Deg;
        var kido = (GameObject)PrefabUtility.InstantiatePrefab(kidoA);
        kido.name = name; kido.transform.SetParent(parent, true);
        kido.transform.rotation = Quaternion.Euler(0, ry, 0);
        kido.transform.localScale = Vector3.one * ES;
        kido.transform.position = new Vector3(kc.x, 20, kc.y);
        var rs = kido.GetComponentsInChildren<Renderer>();
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        kido.transform.position += new Vector3(kc.x - b.center.x, 0, kc.y - b.center.z);
        var b2 = rs[0].bounds; foreach (var r in rs) b2.Encapsulate(r.bounds);
        float g = Ground(b2.center.x, b2.center.z);
        kido.transform.position += new Vector3(0, (g - 0.05f) - b2.min.y, 0);
        if (banA != null)
        {
            var ban = (GameObject)PrefabUtility.InstantiatePrefab(banA);
            ban.name = name + "_banya"; ban.transform.SetParent(parent, true);
            ban.transform.rotation = Quaternion.Euler(0, ry + 90f, 0);
            ban.transform.localScale = Vector3.one * ES;
            Vector2 bc = kc + inw * 4.2f;
            ban.transform.position = new Vector3(bc.x, 20, bc.y);
            var rb = ban.GetComponentsInChildren<Renderer>();
            var bb = rb[0].bounds; foreach (var r in rb) bb.Encapsulate(r.bounds);
            ban.transform.position += new Vector3(bc.x - bb.center.x, 0, bc.y - bb.center.z);
            var bb2 = rb[0].bounds; foreach (var r in rb) bb2.Encapsulate(r.bounds);
            float g2 = Ground(bb2.center.x, bb2.center.z);
            ban.transform.position += new Vector3(0, (g2 - 0.05f) - bb2.min.y, 0);
        }
    }
    static void WellAt(Transform parent, Vector2 p)
    {
        var g = new GameObject("Idobata");
        g.transform.SetParent(parent, false);
        g.transform.position = new Vector3(p.x, Ground(p.x, p.y), p.y);
        var curb = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        curb.name = "curb"; curb.transform.SetParent(g.transform, false);
        curb.transform.localScale = new Vector3(1.3f, 0.35f, 1.3f);
        curb.transform.localPosition = new Vector3(0, 0.35f, 0);
        var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.color = new Color(0.55f, 0.55f, 0.52f);
        curb.GetComponent<Renderer>().sharedMaterial = stone;
        Undo.RegisterCreatedObjectUndo(g, "idobata");
    }
    static Transform Group(string root, string child)
    {
        var r = GameObject.Find(root);
        if (r == null) { r = new GameObject(root); Undo.RegisterCreatedObjectUndo(r, "grp"); }
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

    // ---------- Stage 3: splat (町代地の地面=踏み固め土) ----------
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
        var A = td.GetAlphamaps(ix0, iz0, w, h);
        int L = td.alphamapLayers;
        int changed = 0;
        foreach (var poly in new[] { SeishojiPoly, NagaichoPoly })
            for (int zz = 0; zz < h; zz++)
                for (int xx = 0; xx < w; xx++)
                {
                    float wx = tp.x + (ix0 + xx + 0.5f) * cell;
                    float wz = tp.z + (iz0 + zz + 0.5f) * cell;
                    if (!PIP(poly, new Vector2(wx, wz))) continue;
                    float noise = Mathf.PerlinNoise(wx * 0.13f, wz * 0.13f);
                    float bare = Mathf.Lerp(0.45f, 0.62f, noise), grass = 0.08f, dirt = 1f - bare - grass;
                    for (int l = 0; l < L; l++) A[zz, xx, l] = 0;
                    A[zz, xx, 0] = dirt; A[zz, xx, 1] = grass; A[zz, xx, 2] = bare;
                    changed++;
                }
        td.SetAlphamaps(ix0, iz0, A);
        return "daichi splat cells=" + changed;
    }
}
