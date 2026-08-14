// 三屋敷(太田・加納・鍋島=松平肥前守)の区画を下書きv3へ更新 (2026-08-08)
// 方針: 建物・庭・池は温存(新区画がほぼ旧区画を包含)。外周(石垣/長屋/塀/門)と境界整形のみ差し替え。
// 地形: 明治改変地のため現在の造成(パッド/段丘)を維持。新旧境界の差分帯だけ「内側レベルを境界まで延長」。
// 門: 太田=NE辺h_mon(旗本)、加納=NE辺h_mon(1.3万石・現行踏襲)、鍋島=SE辺(汐見坂)k_mon+片番所(切絵図の文字天=南東)。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoSanyashikiRebuild
{
    const string P_CW = EdoAssets.JC.CastleWall;
    const string P_HMON = EdoAssets.Eg.Hmon;
    const string P_KMON = EdoAssets.Eg.Kmon;
    const string P_BANSHO = EdoAssets.Eg.Bansho;
    const float ES = 1.818f;

    public class SEstate
    {
        public string group;
        public Vector2[] poly;
        public int front; public float gateT; public string gateType; public int bansho;
        public float[] skipT0, skipT1; public int[] skipEdge;   // 隣接屋敷が受け持つ区間 (edge, t0..t1 [m])
        public int[] nagayaEdges;                                // 前辺以外で長屋にする辺
    }

    public static SEstate[] Estates = new SEstate[]
    {
        new SEstate{ group="Edo_Yashiki_Ota",
            poly=new[]{ new Vector2(89.8f,309.7f), new Vector2(60.8f,253.1f), new Vector2(109.5f,227.9f), new Vector2(157.5f,275.6f)},
            front=3, gateT=0.5f, gateType="h_mon", bansho=0,
            skipEdge=new[]{0,1}, skipT0=new float[]{0,0}, skipT1=new float[]{999,999}, // W=加納/S=鍋島が受け持つ
            nagayaEdges=new int[0] },
        new SEstate{ group="Edo_Yashiki_Kano",
            poly=new[]{ new Vector2(23.3f,343.9f), new Vector2(-28.5f,298.6f), new Vector2(58.7f,253.8f), new Vector2(88.4f,311.5f)},
            front=3, gateT=0.5f, gateType="h_mon", bansho=1,
            skipEdge=new int[0], skipT0=new float[0], skipT1=new float[0],
            nagayaEdges=new int[0] },
        new SEstate{ group="Edo_Yashiki_Matsudaira",
            poly=new[]{ new Vector2(-30.9f,296.6f), new Vector2(-124.1f,223.0f), new Vector2(-120.6f,204.9f), new Vector2(-127.3f,197.7f), new Vector2(-21.1f,100.2f), new Vector2(107.9f,226.8f)},
            front=4, gateT=0.5f, gateType="k_mon", bansho=1,
            skipEdge=new[]{5}, skipT0=new float[]{55f}, skipT1=new float[]{999f}, // NE辺の加納区間は加納の壁
            nagayaEdges=new int[0] },
    };

    static bool PIP(Vector2[] poly, Vector2 p)
    {
        bool ins = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
                (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) ins = !ins;
        return ins;
    }
    static Vector2 InwardN(SEstate e, int i)
    {
        var a = e.poly[i]; var b = e.poly[(i + 1) % e.poly.Length];
        var d = (b - a).normalized;
        var n = new Vector2(-d.y, d.x);
        float sa = 0;
        for (int k = 0; k < e.poly.Length; k++) { var p = e.poly[k]; var q = e.poly[(k + 1) % e.poly.Length]; sa += p.x * q.y - q.x * p.y; }
        if (sa < 0) n = -n;
        return n;
    }

    // ---------- S1: 旧外周を退避 ----------
    public static string S1_Deactivate()
    {
        int n = 0;
        foreach (var e in Estates)
        {
            var root = GameObject.Find(e.group);
            foreach (var sub in new[] { "Ishigaki", "Nagaya", "Omotemon", "Dobei" })
            {
                var t = root.transform.Find(sub);
                if (t != null && t.gameObject.activeSelf) { t.gameObject.SetActive(false); n++; }
            }
        }
        return "deactivated " + n + " enclosure groups";
    }

    // ---------- S2: 境界整形(内側レベルを新境界まで延長・外側8mフェザー) ----------
    // 池保護矩形: (2,190)-(48,230) ±6m は不変
    public static string S2_GradeEdges()
    {
        var t = EdoNishiTameikeBuilder.T(); var td = t.terrainData;
        int res = td.heightmapResolution;
        Vector3 tp = t.transform.position; var ts = td.size;
        float cell = ts.x / (res - 1);
        float x0 = -140, x1 = 170, z0 = 90, z1 = 355;
        int ix0 = Mathf.FloorToInt((x0 - tp.x) / cell), ix1 = Mathf.CeilToInt((x1 - tp.x) / cell);
        int iz0 = Mathf.FloorToInt((z0 - tp.z) / cell), iz1 = Mathf.CeilToInt((z1 - tp.z) / cell);
        int w = ix1 - ix0 + 1, h = iz1 - iz0 + 1;
        var H = td.GetHeights(ix0, iz0, w, h);
        float sy = ts.y;
        Func<float, float, float> G = (x, z) => EdoNishiTameikeBuilder.Ground(x, z);
        int changed = 0;
        for (int zz = 0; zz < h; zz++) for (int xx = 0; xx < w; xx++)
        {
            float wx = tp.x + (ix0 + xx) * cell, wz = tp.z + (iz0 + zz) * cell;
            var p = new Vector2(wx, wz);
            if (wx > -4 && wx < 54 && wz > 184 && wz < 236) continue; // 池保護
            float target = float.MinValue;
            foreach (var e in Estates)
            {
                bool inside = PIP(e.poly, p);
                // 最寄り辺と距離
                float best = float.MaxValue; int bi = -1; float bt = 0;
                for (int i = 0; i < e.poly.Length; i++)
                {
                    var a = e.poly[i]; var b = e.poly[(i + 1) % e.poly.Length];
                    var d = b - a; float len = d.magnitude; d /= len;
                    float tt = Mathf.Clamp(Vector2.Dot(p - a, d), 0, len);
                    float dd = (p - (a + d * tt)).magnitude;
                    if (dd < best) { best = dd; bi = i; bt = tt; }
                }
                if (inside && best > 13f) continue;   // 内奥は不変
                if (!inside && best > 8f) continue;   // 外遠方は不変
                // 内側レベル: 最寄り辺点から内向き14mの現況
                var A2 = e.poly[bi]; var B2 = e.poly[(bi + 1) % e.poly.Length];
                var dir = (B2 - A2).normalized;
                var q = A2 + dir * bt;
                var inw = InwardN(e, bi);
                float innerLv = G((q + inw * 14f).x, (q + inw * 14f).y);
                float cand;
                if (inside) cand = Mathf.Lerp(innerLv, G(wx, wz), Mathf.Clamp01((best - 10f) / 3f)); // 0-10m帯=innerLv, 10-13m遷移
                else { float s = best / 8f; s = s * s * (3 - 2 * s); cand = Mathf.Lerp(innerLv, G(wx, wz), s); }
                if (cand > target) target = cand;
            }
            if (target > float.MinValue)
            {
                float cur = tp.y + H[zz, xx] * sy;
                if (Mathf.Abs(target - cur) > 0.02f) { H[zz, xx] = (target - tp.y) / sy; changed++; }
            }
        }
        td.SetHeights(ix0, iz0, H);
        td.SyncHeightmap();
        return "S2 graded " + changed + " cells";
    }

    // ---------- S3: 外周構築(1屋敷ずつ) ----------
    public static string S3_Enclosure(string groupName)
    {
        var e = Estates.First(x => x.group == groupName);
        var root = GameObject.Find(e.group);
        Transform kak = root.transform.Find("Kakoi_v3");
        if (kak != null) UnityEngine.Object.DestroyImmediate(kak.gameObject);
        var kg = new GameObject("Kakoi_v3"); kg.transform.SetParent(root.transform, false); kak = kg.transform;
        Transform mong = root.transform.Find("Omotemon_v3");
        if (mong != null) UnityEngine.Object.DestroyImmediate(mong.gameObject);
        var mg = new GameObject("Omotemon_v3"); mg.transform.SetParent(root.transform, false); mong = mg.transform;
        Undo.RegisterCreatedObjectUndo(kg, "k3"); Undo.RegisterCreatedObjectUndo(mg, "m3");

        var sb = new System.Text.StringBuilder();
        int N = e.poly.Length;
        Vector2 fA = e.poly[e.front], fB = e.poly[(e.front + 1) % N];
        Vector2 gate2 = Vector2.Lerp(fA, fB, e.gateT);
        Vector2 fin = InwardN(e, e.front);
        float gatePad = EdoNishiTameikeBuilder.Ground((gate2 + fin * 10f).x, (gate2 + fin * 10f).y);

        int nIshi = 0, nHei = 0, nNag = 0;
        for (int i = 0; i < N; i++)
        {
            Vector2 A = e.poly[i], B = e.poly[(i + 1) % N];
            float len = (B - A).magnitude;
            var d = (B - A).normalized;
            var inw = InwardN(e, i);
            var outw = -inw;
            // skip区間
            float sk0 = -1, sk1 = -1;
            for (int k = 0; k < e.skipEdge.Length; k++) if (e.skipEdge[k] == i) { sk0 = e.skipT0[k]; sk1 = e.skipT1[k]; }
            int ns = Mathf.Max(1, Mathf.RoundToInt(len / 8f));
            // 8mセグメント計画(長屋/石垣+塀)
            for (int k = 0; k < ns; k++)
            {
                float t0 = len * k / ns, t1 = len * (k + 1) / ns;
                float tm = (t0 + t1) * 0.5f;
                if (sk0 >= 0 && tm > sk0 && tm < sk1) continue;
                var sa = A + d * t0; var sbp = A + d * t1; var m = A + d * tm;
                float inner = EdoNishiTameikeBuilder.Ground((m + inw * 5).x, (m + inw * 5).y);
                float outer = EdoNishiTameikeBuilder.Ground((m - inw * 5).x, (m - inw * 5).y);
                bool gateHere = (i == e.front) && Mathf.Abs(tm - len * e.gateT) < 14f;
                bool nag = (i == e.front && Mathf.Abs(inner - outer) <= 1.6f) || e.nagayaEdges.Contains(i);
                if (nag)
                {
                    float baseY = Mathf.Min(inner, outer);
                    EdoNishiTameikeBuilder.NagayaRun(kak, sa, sbp, outw, baseY,
                        gateHere ? gate2 : Vector2.zero, gateHere ? (e.gateType == "k_mon" ? 8.5f : 5.5f) : -1f, "NG3_" + i + "_" + k);
                    nNag++;
                }
                else
                {
                    float coping = Mathf.Round((Mathf.Max(inner, outer) + 0.4f) * 2f) / 2f;
                    float ground = Mathf.Min(inner, outer);
                    float baseY2 = Mathf.Min(ground - 0.6f, coping - 2.0f);
                    float syw = Mathf.Max(0.5f, (coping - baseY2) / 4.0f);
                    var A2 = sbp; var B2 = sa; var dd = (B2 - A2).normalized;
                    float yaw = Mathf.Atan2(dd.x, dd.y) * Mathf.Rad2Deg;
                    int n2 = Mathf.Max(1, Mathf.CeilToInt((t1 - t0) / 1.8f));
                    for (int q = 0; q <= n2; q++)
                    {
                        float tq = Mathf.Min(q * 1.8f, (t1 - t0) - 0.01f);
                        var p = A2 + dd * tq;
                        if (gateHere) { float gtq = Vector2.Dot(gate2 - A2, dd); if (Mathf.Abs(tq - gtq) < (e.gateType == "k_mon" ? 8.5f : 5.5f)) continue; }
                        EdoNishiTameikeBuilder.Place(P_CW, new Vector3(p.x, baseY2, p.y), yaw, new Vector3(1, syw, 1), kak, "CW3_" + nIshi);
                        nIshi++;
                    }
                    EdoNishiTameikeBuilder.DobeiRun(kak, sa, sbp, outw, "Hei3_" + i + "_" + k, false, coping - 0.05f,
                        gateHere ? gate2 : Vector2.zero, gateHere ? (e.gateType == "k_mon" ? 8.5f : 5.5f) : -1f);
                    nHei++;
                }
            }
        }
        // 門
        string gp = e.gateType == "k_mon" ? P_KMON : P_HMON;
        float psiIn = Mathf.Atan2(fin.x, fin.y) * Mathf.Rad2Deg;
        var monGo = EdoNishiTameikeBuilder.Place(gp, new Vector3(gate2.x, gatePad, gate2.y), psiIn,
            e.gateType == "k_mon" ? Vector3.one * ES : Vector3.one, mong, "Mon_v3");
        EdoNishiTameikeBuilder.SeatBottom(monGo, gatePad - 0.05f);
        var mb = EdoNishiTameikeBuilder.RB(monGo);
        monGo.transform.position += new Vector3(gate2.x - mb.center.x, 0, gate2.y - mb.center.z);
        // kagami 内側検証
        float kmn = float.MaxValue, kmx = float.MinValue;
        foreach (var mf in monGo.GetComponentsInChildren<MeshFilter>())
        {
            if (!mf.gameObject.name.ToLower().Contains("kagami")) continue;
            foreach (var vtx in mf.sharedMesh.vertices)
            {
                var wp = mf.transform.TransformPoint(vtx);
                float pr = wp.x * (-fin.x) + wp.z * (-fin.y);
                kmn = Mathf.Min(kmn, pr); kmx = Mathf.Max(kmx, pr);
            }
        }
        if (kmn != float.MaxValue)
        {
            var mc = EdoNishiTameikeBuilder.RB(monGo).center;
            float cp = mc.x * (-fin.x) + mc.z * (-fin.y);
            if ((kmn + kmx) * 0.5f > cp)
            {
                monGo.transform.rotation *= Quaternion.Euler(0, 180, 0);
                var b2 = EdoNishiTameikeBuilder.RB(monGo);
                monGo.transform.position += new Vector3(gate2.x - b2.center.x, 0, gate2.y - b2.center.z);
                sb.AppendLine("mon flipped");
            }
        }
        for (int i = 0; i < e.bansho; i++)
        {
            float side = i == 0 ? 1f : -1f;
            var runAxis = (fB - fA).normalized;
            var bp = gate2 + runAxis * (side * ((e.gateType == "k_mon" ? 7.2f : 4.2f) + 2.2f)) + (-fin) * 0.5f;
            var ban = EdoNishiTameikeBuilder.Place(P_BANSHO, new Vector3(bp.x, gatePad, bp.y), psiIn + 180f, Vector3.one * ES, mong, "Bansho_" + i);
            EdoNishiTameikeBuilder.SeatBottom(ban, gatePad - 0.05f);
            var f3 = ban.transform.forward;
            if (f3.x * (-fin.x) + f3.z * (-fin.y) < 0)
                ban.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(-fin.x, -fin.y) * Mathf.Rad2Deg, 0);
        }
        sb.AppendLine(e.group + ": ishi=" + nIshi + " hei=" + nHei + " nag=" + nNag);
        SceneView.RepaintAll();
        return sb.ToString();
    }

    // ---------- S4: 建物・庭のQA(新区画に対する) ----------
    public static string S4_QA()
    {
        var sb = new System.Text.StringBuilder();
        foreach (var e in Estates)
        {
            var root = GameObject.Find(e.group);
            foreach (var sub in new[] { "Buildings", "Garden" })
            {
                var g = root.transform.Find(sub);
                if (g == null) continue;
                var items = new List<Transform>();
                if (sub == "Buildings") foreach (Transform c in g) items.Add(c);
                else foreach (Transform cat in g) foreach (Transform c in cat) items.Add(c);
                foreach (var it in items)
                {
                    var rs = it.GetComponentsInChildren<Renderer>();
                    if (rs.Length == 0) continue;
                    var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    var c2 = new Vector2(b.center.x, b.center.z);
                    if (!PIP(e.poly, c2))
                        sb.AppendLine("⚠ OUT " + e.group.Substring(11) + "/" + sub + "/" + it.name + " @" + c2);
                    else
                    {
                        float best = float.MaxValue;
                        for (int i = 0; i < e.poly.Length; i++)
                        {
                            var a = e.poly[i]; var bb = e.poly[(i + 1) % e.poly.Length];
                            var d = bb - a; float len = d.magnitude; d /= len;
                            float tt = Mathf.Clamp(Vector2.Dot(c2 - a, d), 0, len);
                            best = Mathf.Min(best, (c2 - (a + d * tt)).magnitude);
                        }
                        float need = sub == "Buildings" ? 5f : 1.5f;
                        if (best < need) sb.AppendLine("⚠ NEAR " + e.group.Substring(11) + "/" + sub + "/" + it.name + " d=" + best.ToString("F1"));
                    }
                }
            }
        }
        return sb.Length == 0 ? "S4 QA clean" : sb.ToString();
    }
}
