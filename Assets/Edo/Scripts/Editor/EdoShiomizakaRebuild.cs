// 汐見坂(段坂)を新区割りの回廊へ敷き直す (2026-08-09)
// 旧版は旧鍋島南石垣(yaw310.04/P0=(-15.18,112.81))基準で、新区割りでは約12m北東へずれ鍋島敷地に食い込んでいた。
// 新フレーム = 松平大和守の表辺(P13(14,36)→P0(-131,168.9), yaw312.51) を n=0 とし、鍋島南西辺(n≈23.7)との回廊。
//   両側の石垣躯体が2.4mずつ食い込むので、実際の空きは n∈[2.40,21.21]=18.81m ≒ 史実の道幅18m(10間)。
// 高さは「現地形に従う」= 回廊の実地形を平滑・単調化した曲線に、蹴上げ0.30mの段坂をフィットさせる
// (史実: 北西に上り/長さ140m/高低差5m — 実地形は t=55→195 で 8.3→13.5m とほぼ一致)。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoShiomizakaRebuild
{
    const string GROUP = "Edo_Shiomizaka";
    const string P_STEP = EdoAssets.Own.DanishiStep;
    const string MESH_PATH = "Assets/Edo/Models/Shiomizaka/ShiomizakaRoad.asset";

    // ---- フレーム ----
    public static Vector2 A => EdoYamatoRebuild.Poly[13];              // (14,36)
    public static Vector2 U => (EdoYamatoRebuild.Poly[0] - A).normalized;
    public static Vector2 Nn { get { var u = U; return new Vector2(u.y, -u.x); } }  // 鍋島側(北東)向き
    public static float RoadYaw => Mathf.Atan2(U.x, U.y) * Mathf.Rad2Deg;

    const float T0 = 55f, T1 = 195f;      // 坂の範囲(140m)
    const float N0 = 2.6f, N1 = 21.0f;    // 路面の幅(18.4m) — 石垣実体 n=2.40 / 21.21 の内側
    const float RISER = 0.30f;
    const int NPIECE = 11;                // 1段あたりの石材数(旧版と同じ)
    const float PITCH = 1.672f;           // 石材の横ピッチ(旧版実測)

    public static Vector2 W(float t, float n) => A + U * t + Nn * n;

    // ---- 地形プロファイル(平滑+単調) ----
    static float[] _prof; // 1m刻み T0..T1
    public static float Profile(float t)
    {
        if (_prof == null) BuildProfile();
        float f = Mathf.Clamp(t - T0, 0, T1 - T0);
        int i = Mathf.Clamp(Mathf.FloorToInt(f), 0, _prof.Length - 2);
        return Mathf.Lerp(_prof[i], _prof[i + 1], f - i);
    }
    static void BuildProfile()
    {
        int n = Mathf.RoundToInt(T1 - T0) + 1;
        var raw = new float[n];
        float[] ns = { 5f, 8f, 11f, 14f, 17f, 20f };
        for (int i = 0; i < n; i++)
        {
            float t = T0 + i, s = 0;
            foreach (var nv in ns) { var p = W(t, nv); s += EdoNishiTameikeBuilder.Ground(p.x, p.y); }
            raw[i] = s / ns.Length;
        }
        // 門前平場などの人工的な凹凸を消すため強めに平滑(±18m → 単調化 → ±14m → 単調化)。
        // ⚠ 端は「窓を縮める」と内側へ引っ張られ、取り付きで段差が残る。端値を複製して窓を保つ。
        var sm = new float[n];
        for (int i = 0; i < n; i++)
        {
            float s = 0;
            for (int k = -18; k <= 18; k++) s += raw[Mathf.Clamp(i + k, 0, n - 1)];
            sm[i] = s / 37f;
        }
        for (int i = 1; i < n; i++) if (sm[i] < sm[i - 1]) sm[i] = sm[i - 1];
        var sm2 = new float[n];
        for (int i = 0; i < n; i++)
        {
            float s = 0;
            for (int k = -14; k <= 14; k++) s += sm[Mathf.Clamp(i + k, 0, n - 1)];
            sm2[i] = s / 29f;
        }
        for (int i = 1; i < n; i++) if (sm2[i] < sm2[i - 1]) sm2[i] = sm2[i - 1];
        _prof = sm2;
    }

    // ---- 段の割り付け: (tStart, height) ----
    public static List<Vector2> Steps()   // x=t, y=height
    {
        var segs = new List<Vector2>();
        float h = Mathf.Floor(Profile(T0) * 20f) / 20f;   // 0.05m 丸め
        segs.Add(new Vector2(T0, h));
        for (float t = T0; t <= T1 - 3f; t += 0.5f)   // 終端3m以内に段を作らない(端の丸めで段が詰まるのを防ぐ)
        {
            if (Profile(t) - h >= RISER) { h += RISER; segs.Add(new Vector2(t, h)); }
        }
        return segs;
    }
    public static float RoadH(float t)
    {
        var s = Steps();
        float h = s[0].y;
        foreach (var q in s) { if (t >= q.x) h = q.y; else break; }
        return h;
    }

    // ---- 0: 造成前の地形へ回廊を復元(再実行時のフィードバック防止。必ず Z1 の前に) ----
    // ⚠ 造成後の地形からプロファイルを取り直すと「前回の段」を地形と誤認して段が減り続ける。
    public static string Z0_Restore(string baselinePath)
    {
        var bl = AssetDatabase.LoadAssetAtPath<TerrainData>(baselinePath);
        if (bl == null) return "Z0: baseline not found " + baselinePath;
        var ter = EdoNishiTameikeBuilder.T(); var td = ter.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = ter.transform.position; var ts = td.size;
        float cell = ts.x / (res - 1);
        var corners = new[] { W(T0 - 12, -8), W(T0 - 12, 32), W(T1 + 12, -8), W(T1 + 12, 32) };
        float xmin = corners.Min(c => c.x), xmax = corners.Max(c => c.x);
        float zmin = corners.Min(c => c.y), zmax = corners.Max(c => c.y);
        int ix0 = Mathf.FloorToInt((xmin - tp.x) / cell), ix1 = Mathf.CeilToInt((xmax - tp.x) / cell);
        int iz0 = Mathf.FloorToInt((zmin - tp.z) / cell), iz1 = Mathf.CeilToInt((zmax - tp.z) / cell);
        int w = ix1 - ix0 + 1, h2 = iz1 - iz0 + 1;
        var B = bl.GetHeights(ix0, iz0, w, h2);
        var H = td.GetHeights(ix0, iz0, w, h2);
        int n = 0;
        for (int zz = 0; zz < h2; zz++) for (int xx = 0; xx < w; xx++)
        {
            var p = new Vector2(tp.x + (ix0 + xx) * cell, tp.z + (iz0 + zz) * cell);
            float t = Vector2.Dot(p - A, U), nv = Vector2.Dot(p - A, Nn);
            if (t < T0 - 10 || t > T1 + 10 || nv < -6 || nv > 30) continue;
            if (H[zz, xx] != B[zz, xx]) { H[zz, xx] = B[zz, xx]; n++; }
        }
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        _prof = null;   // プロファイル再計算
        return "Z0 restored " + n + " cells from " + baselinePath;
    }

    // ---- 1: 回廊の造成(路面帯のみ。石垣の足元は触らない) ----
    public static string Z1_Grade()
    {
        var ter = EdoNishiTameikeBuilder.T(); var td = ter.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = ter.transform.position; var ts = td.size;
        float cell = ts.x / (res - 1), sy = ts.y;
        // 作業矩形
        var corners = new[] { W(T0 - 6, -2), W(T0 - 6, 26), W(T1 + 6, -2), W(T1 + 6, 26) };
        float xmin = corners.Min(c => c.x), xmax = corners.Max(c => c.x);
        float zmin = corners.Min(c => c.y), zmax = corners.Max(c => c.y);
        int ix0 = Mathf.FloorToInt((xmin - tp.x) / cell), ix1 = Mathf.CeilToInt((xmax - tp.x) / cell);
        int iz0 = Mathf.FloorToInt((zmin - tp.z) / cell), iz1 = Mathf.CeilToInt((zmax - tp.z) / cell);
        int w = ix1 - ix0 + 1, h2 = iz1 - iz0 + 1;
        var H = td.GetHeights(ix0, iz0, w, h2);
        // バックアップ
        var bytes = new byte[w * h2 * 4];
        Buffer.BlockCopy(H, 0, bytes, 0, bytes.Length);
        System.IO.File.WriteAllBytes("Library/EdoShiomizaka_before_20260809.bin", bytes);
        int changed = 0;
        for (int zz = 0; zz < h2; zz++) for (int xx = 0; xx < w; xx++)
        {
            var p = new Vector2(tp.x + (ix0 + xx) * cell, tp.z + (iz0 + zz) * cell);
            float t = Vector2.Dot(p - A, U), nv = Vector2.Dot(p - A, Nn);
            if (t < T0 - 5 || t > T1 + 5) continue;
            if (nv < 2.0f || nv > 21.6f) continue;
            float tc = Mathf.Clamp(t, T0, T1);
            float target = RoadH(tc) - 0.06f;                       // 路面メッシュのすぐ下
            // 走り方向の端と、幅方向の石垣際でフェザー
            float wt = 1f;
            if (t < T0) wt *= Mathf.SmoothStep(0, 1, (t - (T0 - 5)) / 5f);
            if (t > T1) wt *= Mathf.SmoothStep(0, 1, ((T1 + 5) - t) / 5f);
            if (nv < 3.4f) wt *= Mathf.SmoothStep(0, 1, (nv - 2.0f) / 1.4f);
            if (nv > 20.2f) wt *= Mathf.SmoothStep(0, 1, (21.6f - nv) / 1.4f);
            float cur = tp.y + H[zz, xx] * sy;
            float nh = Mathf.Lerp(cur, target, wt);
            if (Mathf.Abs(nh - cur) > 0.01f) { H[zz, xx] = (nh - tp.y) / sy; changed++; }
        }
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        return "Z1 graded " + changed + " cells (rect " + w + "x" + h2 + ")";
    }

    // ---- 2: 路面メッシュ ----
    public static string Z2_Mesh()
    {
        var steps = Steps();
        // t サンプル: 段の境界で前後2点(垂直面)を作る
        var ts = new List<float>();
        ts.Add(T0);
        foreach (var s in steps) { if (s.x <= T0 + 0.01f) continue; ts.Add(s.x - 0.001f); ts.Add(s.x); }
        for (float t = T0; t <= T1; t += 4f) ts.Add(t);
        ts.Add(T1);
        ts = ts.Distinct().OrderBy(v => v).ToList();
        // 断面は旧メッシュの規約に合わせる: 4頂点 [端(下), 端(上), 反対端(上), 反対端(下)]
        // 両端に 0.90m のスカート(段の立ち上がりや地形との隙間を隠す)。UVは 1単位=11m(旧メッシュ実測)。
        const float SKIRT = 0.90f, TOPOFF = -0.02f, UVM = 11.0f;
        float[] ns = { N0, N0, N1, N1 };
        float[] dy = { TOPOFF - SKIRT, TOPOFF, TOPOFF, TOPOFF - SKIRT };
        var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
        for (int i = 0; i < ts.Count; i++)
        {
            float t = ts[i];
            float hh = RoadH(Mathf.Clamp(t, T0, T1));
            for (int j = 0; j < ns.Length; j++)
            {
                var p = W(t, ns[j]);
                verts.Add(new Vector3(p.x, hh + dy[j], p.y));
                uvs.Add(new Vector2(ns[j] / UVM, (t - T0) / UVM));
            }
        }
        int cols = ns.Length;
        for (int i = 0; i < ts.Count - 1; i++)
            for (int j = 0; j < cols - 1; j++)
            {
                int a = i * cols + j, b = a + 1, c = a + cols, d = c + 1;
                tris.Add(a); tris.Add(c); tris.Add(b);
                tris.Add(b); tris.Add(c); tris.Add(d);
            }
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(MESH_PATH);
        if (mesh == null) return "mesh asset not found";
        mesh.Clear();
        mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
        mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
        EditorUtility.SetDirty(mesh);
        AssetDatabase.SaveAssets();
        return "Z2 mesh: verts=" + verts.Count + " tris=" + (tris.Count / 3) + " bounds=" + mesh.bounds.min.ToString("F1") + "-" + mesh.bounds.max.ToString("F1");
    }

    // ---- 3: 段石 ----
    public static string Z3_Danishi()
    {
        var root = GameObject.Find(GROUP);
        var dan = root.transform.Find("Danishi");
        if (dan != null) UnityEngine.Object.DestroyImmediate(dan.gameObject);
        var dg = new GameObject("Danishi"); dg.transform.SetParent(root.transform, false);
        Undo.RegisterCreatedObjectUndo(dg, "danishi");
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(P_STEP);
        if (prefab == null) return "step prefab missing";
        var steps = Steps();
        float ry = RoadYaw + 180f;
        int rows = 0;
        for (int k = 1; k < steps.Count; k++)   // 最初は基準面なので段石なし
        {
            float t = steps[k].x, hh = steps[k].y;
            var row = new GameObject("Dan_" + k.ToString("00"));
            row.transform.SetParent(dg.transform, false);
            float nStart = N1 - 0.5f * PITCH;
            for (int i = 0; i < NPIECE; i++)
            {
                float nv = nStart - PITCH * i;
                var p = W(t, nv);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                go.name = "Dan_" + k.ToString("00") + "_" + i;
                go.transform.SetParent(row.transform, true);
                go.transform.position = new Vector3(p.x, hh, p.y);
                go.transform.rotation = Quaternion.Euler(0, ry, 0);
                go.transform.localScale = new Vector3(1f, 1f, 0.6f);
                Undo.RegisterCreatedObjectUndo(go, "dan");
            }
            rows++;
        }
        return "Z3 danishi rows=" + rows + " (steps " + steps.Count + ", rise " + ((steps.Count - 1) * RISER).ToString("F2") + "m)";
    }

    // ---- 4: 大和守の門・番所を路面高へ座り直す ----
    public static string Z4_ReseatGate()
    {
        var g2 = EdoYamatoRebuild.Gate2;
        float t = Vector2.Dot(g2 - A, U);
        float roadH = RoadH(Mathf.Clamp(t, T0, T1));
        var mong = GameObject.Find("Edo_Yashiki_MatsudairaYamato").transform.Find("Omotemon_v2");
        var sb = new System.Text.StringBuilder("gate t=" + t.ToString("F1") + " roadH=" + roadH.ToString("F2") + "\n");
        foreach (Transform c in mong)
        {
            var b = EdoNishiTameikeBuilder.RB(c.gameObject);
            float before = b.min.y;
            c.position += new Vector3(0, (roadH - 0.05f) - b.min.y, 0);
            sb.AppendLine("  " + c.name + " " + before.ToString("F2") + " -> " + (roadH - 0.05f).ToString("F2"));
        }
        // 門前の平場を路面高へ均す(区画外・半径14m、20mでフェザー)
        var ter = EdoNishiTameikeBuilder.T(); var td = ter.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = ter.transform.position; var ts = td.size;
        float cell = ts.x / (res - 1), sy = ts.y;
        int ix0 = Mathf.FloorToInt((g2.x - 24 - tp.x) / cell), ix1 = Mathf.CeilToInt((g2.x + 24 - tp.x) / cell);
        int iz0 = Mathf.FloorToInt((g2.y - 24 - tp.z) / cell), iz1 = Mathf.CeilToInt((g2.y + 24 - tp.z) / cell);
        int w = ix1 - ix0 + 1, h2 = iz1 - iz0 + 1;
        var H = td.GetHeights(ix0, iz0, w, h2);
        int n2 = 0;
        for (int zz = 0; zz < h2; zz++) for (int xx = 0; xx < w; xx++)
        {
            var p = new Vector2(tp.x + (ix0 + xx) * cell, tp.z + (iz0 + zz) * cell);
            float nv = Vector2.Dot(p - A, Nn);
            if (nv > 2.2f) continue;             // 回廊側は Z1 が担当
            float dg = (p - g2).magnitude;
            if (dg > 20f) continue;
            float s = Mathf.Clamp01((dg - 14f) / 6f); s = s * s * (3 - 2 * s);
            float cur = tp.y + H[zz, xx] * sy;
            float nh = Mathf.Lerp(roadH - 0.05f, cur, s);
            if (Mathf.Abs(nh - cur) > 0.01f) { H[zz, xx] = (nh - tp.y) / sy; n2++; }
        }
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        sb.AppendLine("  apron cells=" + n2);
        return sb.ToString();
    }

    // ---- 5: 検証 ----
    public static string Z5_QA()
    {
        var sb = new System.Text.StringBuilder();
        var steps = Steps();
        sb.AppendLine("steps=" + (steps.Count - 1) + " base=" + steps[0].y.ToString("F2") + " top=" + steps[steps.Count - 1].y.ToString("F2") + " rise=" + (steps[steps.Count - 1].y - steps[0].y).ToString("F2") + "m over " + (T1 - T0) + "m");
        float worst = 0; float worstT = 0;
        for (float t = T0; t <= T1; t += 2f)
        {
            float rh = RoadH(t);
            for (float nv = N0 + 1f; nv <= N1 - 1f; nv += 3f)
            {
                var p = W(t, nv);
                float g = EdoNishiTameikeBuilder.Ground(p.x, p.y);
                float d = Mathf.Abs(g - (rh - 0.06f));
                if (d > worst) { worst = d; worstT = t; }
            }
        }
        sb.AppendLine("road vs ground worst |diff| = " + worst.ToString("F2") + "m @t=" + worstT);
        // 石垣との干渉(段石の n 範囲が 2.40..21.21 に収まるか)
        float nMin = N1 - 0.5f * PITCH - PITCH * (NPIECE - 1), nMax = N1 - 0.5f * PITCH;
        sb.AppendLine("danishi n range = " + nMin.ToString("F2") + ".." + nMax.ToString("F2") + " (free corridor 2.40..21.21)");
        return sb.ToString();
    }

    public static string RunAll()
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(Z1_Grade());
        sb.AppendLine(Z2_Mesh());
        sb.AppendLine(Z3_Danishi());
        sb.AppendLine(Z4_ReseatGate());
        sb.AppendLine(Z5_QA());
        return sb.ToString();
    }
}
