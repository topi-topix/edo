// EdoBuild — 道の造成(縦断を設計して道の面を均す)。2026-09-30・EDO-0495(施主裁定②「小道を造成する」)。
//
// ⭐ 道は既定では造成しない(道の高さ = 造成前の地盤 base_dem)。**指図の道の欄に `zosei` を書いた道だけ**を均す ──
//    `zosei = { maxGrade: 縦断の上限(比), gateFlat: 門の前を水平に取る長さ[m], gates: "<区画 id の頭>" }`、
//    道の面は欄の `area`(区画の間に残った領域・規則「道は敷地割の間の領域そのもの」)、芯は `pts`。
// ⭐ 縦断 = 芯に沿う造成前の地盤へ、縦断の上限と門の前の水平を守って**切り盛りの総量が最も小さい**高さの列(0.01m 刻みの動的計画)。
//    横断は水平(芯の高さを道の面の全幅へ)。端 s=0 は造成しない道へ繋がるので地盤に合わせる(重い重み)。
// ⭐ 門の前 = `gates` の区画ごとに、道の面の縁に載る辺のうち最も長い辺(= 表の辺)の中点を芯へ射影した所。
//    門の置き場(FlattestStation)は道の高さを <see cref="RoadY"/> で読むので、水平に取った所の中央に門が立つ。
// ⭐ 冪等: 設計は造成前の地盤だけから出す(⛔ live terrain を読まない・規則13)。二度均しても同じ面。
// ⛔ 区画の中は触らない(区画の造成は GradePads)。道の面の外へは出さない。
// 当たる先: 指図の道の欄に `zosei` を持つ道(今は山王の麓の道 南西区間 = 十坊の小道だけ)。類型の門構えの置き場と門の平場の高さは全区画が RoadY を読む
// (設計の無い所は base_dem のままなので、他の区画の姿は変わらない)。

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>設計した道。s[k] = 芯に沿う距離、y[k] = 設計の高さ(DS 刻み)。</summary>
    public class Michi
    {
        public string name, of;
        public Vector2[] area, pts;
        public float maxGrade, gateFlat, len;
        public float[] y;
        public List<float> gateS = new List<float>();
        public float maxCut, maxFill;
    }

    /// <summary>縦断の刻み[m]。</summary>
    public const float MICHI_DS = 0.5f;
    /// <summary>道の面の縁から、道の高さとして読む遊び[m](区画の線の上の点を道として読むため)。</summary>
    public const float MICHI_EDGE_TOL = 0.6f;

    static List<Michi> _michi; static DateTime _michiStamp;

    /// <summary>指図(`docs/Sashizu/*_sashizu.json`)の道の欄のうち `zosei` を持つ物を読み、縦断を設計して返す(json が変われば読み直す)。</summary>
    public static List<Michi> MichiZosei()
    {
        string dir = Path.Combine(Path.GetDirectoryName(Application.dataPath), "docs/Sashizu");
        var files = Directory.GetFiles(dir, "*_sashizu.json");
        var stamp = files.Select(f => File.GetLastWriteTimeUtc(f)).DefaultIfEmpty(DateTime.MinValue).Max();
        if (_michi != null && stamp == _michiStamp && EdoParcels.Version == _michiParcelVer) return _michi;
        var outp = new List<Michi>();
        foreach (var f in files)
        {
            string txt = File.ReadAllText(f);
            if (!txt.Contains("\"zosei\"")) continue;
            Walk(EdoMiniJson.Parse(txt), Path.GetFileName(f), outp);
        }
        foreach (var m in outp) Design(m);
        _michi = outp; _michiStamp = stamp; _michiParcelVer = EdoParcels.Version;
        return outp;
    }
    static int _michiParcelVer = -1;

    static void Walk(object o, string of, List<Michi> outp)
    {
        var d = o as Dictionary<string, object>;
        if (d != null)
        {
            if (d.ContainsKey("zosei") && d.ContainsKey("area") && d.ContainsKey("pts"))
            {
                var z = d["zosei"] as Dictionary<string, object>;
                var m = new Michi
                {
                    name = d.ContainsKey("name") ? d["name"] as string : "?", of = of,
                    area = Pts(d["area"]), pts = Pts(d["pts"]),
                    maxGrade = z.ContainsKey("maxGrade") ? Convert.ToSingle(z["maxGrade"]) : 0.04f,
                    gateFlat = z.ContainsKey("gateFlat") ? Convert.ToSingle(z["gateFlat"]) : 6f,
                };
                string gates = z.ContainsKey("gates") ? z["gates"] as string : null;
                m.len = 0f; for (int i = 1; i < m.pts.Length; i++) m.len += Vector2.Distance(m.pts[i - 1], m.pts[i]);
                if (!string.IsNullOrEmpty(gates))
                    foreach (var p in EdoParcels.All)
                    {
                        if (p.id == null || !p.id.StartsWith(gates)) continue;
                        var poly = p.pts.ToArray(); float best = 0f; Vector2 mid = Vector2.zero;
                        for (int i = 0; i < poly.Length; i++)
                        {
                            Vector2 a = poly[i], b = poly[(i + 1) % poly.Length], c = (a + b) * 0.5f;
                            float L = Vector2.Distance(a, b);
                            if (L <= best) continue;
                            if (EdoGeom.DistToPolyEdge(m.area, a) > 0.1f || EdoGeom.DistToPolyEdge(m.area, b) > 0.1f || EdoGeom.DistToPolyEdge(m.area, c) > 0.1f) continue;
                            best = L; mid = c;
                        }
                        if (best > 0f) m.gateS.Add(Project(m.pts, mid));
                    }
                outp.Add(m);
            }
            foreach (var v in d.Values) Walk(v, of, outp);
            return;
        }
        var l = o as List<object>;
        if (l != null) foreach (var v in l) Walk(v, of, outp);
    }

    static Vector2[] Pts(object o)
    {
        var l = o as List<object>; var r = new Vector2[l.Count];
        for (int i = 0; i < l.Count; i++) { var q = l[i] as List<object>; r[i] = new Vector2(Convert.ToSingle(q[0]), Convert.ToSingle(q[1])); }
        return r;
    }

    /// <summary>折れ線 <paramref name="line"/> の上で <paramref name="q"/> に最も近い点までの距離(始点から)。</summary>
    static float Project(Vector2[] line, Vector2 q)
    {
        float acc = 0f, best = float.MaxValue, s = 0f;
        for (int i = 1; i < line.Length; i++)
        {
            Vector2 a = line[i - 1], b = line[i], d = b - a; float L = d.magnitude; if (L < 1e-6f) continue;
            float t = Mathf.Clamp(Vector2.Dot(q - a, d / L), 0f, L); float e = (q - (a + d / L * t)).magnitude;
            if (e < best) { best = e; s = acc + t; }
            acc += L;
        }
        return s;
    }

    static Vector2 PointAt(Vector2[] line, float s, out Vector2 dir)
    {
        dir = Vector2.right;
        for (int i = 1; i < line.Length; i++)
        {
            Vector2 a = line[i - 1], b = line[i]; float L = Vector2.Distance(a, b); if (L < 1e-6f) continue;
            dir = (b - a) / L;
            if (s <= L || i == line.Length - 1) return a + dir * Mathf.Min(s, L);
            s -= L;
        }
        return line[line.Length - 1];
    }

    /// <summary>縦断の設計(0.01m 刻みの動的計画)。費用 = Σ|y − 地盤|・隣の差 ≤ maxGrade×DS・門の前の区間は差 0。</summary>
    static void Design(Michi m)
    {
        var dem = BaseDem();
        int n = Mathf.Max(2, Mathf.CeilToInt(m.len / MICHI_DS) + 1);
        var g = new float[n];
        for (int k = 0; k < n; k++)
        {   // 芯と、芯から左右 1.5m(道の面の中だけ)の地盤の平均 ── 横断は水平に取るので幅の中の平均へ合わせる
            Vector2 dir; var c = PointAt(m.pts, Mathf.Min(k * MICHI_DS, m.len), out dir); var nr = new Vector2(-dir.y, dir.x);
            float sum = 0f; int cnt = 0;
            foreach (float o in new[] { 0f, -1.5f, 1.5f })
            {
                var q = c + nr * o; if (o != 0f && !EdoGeom.PIP(m.area, q)) continue;
                float b = dem(q.x, q.y); if (float.IsNaN(b)) continue; sum += b; cnt++;
            }
            g[k] = cnt > 0 ? sum / cnt : (k > 0 ? g[k - 1] : 0f);
        }
        var flat = new bool[n];   // flat[k] = k-1 → k は水平
        foreach (var sg in m.gateS)
            for (int k = 1; k < n; k++)
            {
                float s0 = (k - 1) * MICHI_DS, s1 = k * MICHI_DS;
                if (s0 >= sg - m.gateFlat * 0.5f - 1e-4f && s1 <= sg + m.gateFlat * 0.5f + 1e-4f) flat[k] = true;
            }
        const float Q = 0.01f;
        float lo = g.Min() - 2f, hi = g.Max() + 2f; int L = Mathf.CeilToInt((hi - lo) / Q) + 1;
        int step = Mathf.Max(1, Mathf.FloorToInt(m.maxGrade * MICHI_DS / Q + 1e-4f));
        var cost = new float[L]; var prev = new int[n, L];
        for (int l = 0; l < L; l++) cost[l] = 50f * Mathf.Abs(lo + l * Q - g[0]);   // 端 s=0 は造成しない道へ繋がる
        var nc = new float[L];
        for (int k = 1; k < n; k++)
        {
            int st = flat[k] ? 0 : step;
            for (int l = 0; l < L; l++)
            {
                float bc = float.MaxValue; int bl = l;
                for (int dl = -st; dl <= st; dl++) { int l2 = l + dl; if (l2 < 0 || l2 >= L) continue; if (cost[l2] < bc) { bc = cost[l2]; bl = l2; } }
                nc[l] = bc + Mathf.Abs(lo + l * Q - g[k]); prev[k, l] = bl;
            }
            var t = cost; cost = nc; nc = t;
        }
        int end = 0; for (int l = 1; l < L; l++) if (cost[l] < cost[end]) end = l;
        m.y = new float[n];
        for (int k = n - 1; k >= 0; k--) { m.y[k] = lo + end * Q; if (k > 0) end = prev[k, end]; }
        m.maxCut = 0f; m.maxFill = 0f;
        for (int k = 0; k < n; k++) { float dd = m.y[k] - g[k]; if (dd < 0) m.maxCut = Mathf.Max(m.maxCut, -dd); else m.maxFill = Mathf.Max(m.maxFill, dd); }
    }

    static float ProfileAt(Michi m, float s)
    {
        float f = Mathf.Clamp(s / MICHI_DS, 0f, m.y.Length - 1); int k = Mathf.Min(Mathf.FloorToInt(f), m.y.Length - 2);
        return Mathf.Lerp(m.y[k], m.y[k + 1], f - k);
    }

    /// <summary>**道の高さ**(硬い: 門の敷居・門の平場はこれに合わせる)。設計した道の面(縁から <see cref="MICHI_EDGE_TOL"/> の内)なら設計の高さ、
    /// それ以外は造成前の地盤(<see cref="BaseDem"/>)。当たる先: 類型の全ての門構えの置き場(FlattestStation)と門の平場の高さ(GradePads)。</summary>
    public static float RoadY(float x, float z)
    {
        var q = new Vector2(x, z);
        foreach (var m in MichiZosei())
            if (EdoGeom.PIP(m.area, q) || EdoGeom.DistToPolyEdge(m.area, q) <= MICHI_EDGE_TOL)
                return ProfileAt(m, Project(m.pts, q));
        return BaseDem()(x, z);
    }

    /// <summary>**区画に接する設計した道を均す**(区画を建てる前に呼ぶ・冪等)。道の面の中の地形の節点を設計の高さへ書く。
    /// <paramref name="reach"/> = 区画からこの距離の内に道の面があれば均す。返りは刷る一行(道が無ければ空)。</summary>
    public static string GradeMichiNear(Vector2[] parcel, float reach = 3f)
    {
        var notes = new List<string>();
        foreach (var m in MichiZosei())
        {
            bool near = false;
            foreach (var p in parcel) if (EdoGeom.PIP(m.area, p) || EdoGeom.DistToPolyEdge(m.area, p) <= reach) { near = true; break; }
            if (!near) continue;
            notes.Add(GradeMichi(m));
        }
        return string.Join(" / ", notes);
    }

    /// <summary>道の面の中の節点を設計の高さへ(横断は水平)。</summary>
    public static string GradeMichi(Michi m)
    {
        var t = T(); var td = t.terrainData; int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in m.area) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int i1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int j1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int w = i1 - i0 + 1, h = j1 - j0 + 1;
        var H = td.GetHeights(i0, j0, w, h);
        int written = 0;
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                var q = NodeXZ(tp, ts, res, i0 + i, j0 + j);
                if (!EdoGeom.PIP(m.area, q)) continue;
                float y = ProfileAt(m, Project(m.pts, q));
                H[j, i] = Mathf.Clamp01((y - tp.y) / ts.y); written++;
            }
        td.SetHeightsDelayLOD(i0, j0, H); td.SyncHeightmap();
        float grade = 0f; for (int k = 1; k < m.y.Length; k++) grade = Mathf.Max(grade, Mathf.Abs(m.y[k] - m.y[k - 1]) / MICHI_DS);
        return string.Format("道の造成 {0}: 延長 {1:F0}m・節点 {2}・縦断の最急 {3:P1}(上限 {4:P0})・門の前の水平 {5} 所×{6:F0}m・最大の切土 {7:F2}m・盛土 {8:F2}m",
                             m.name, m.len, written, grade, m.maxGrade, m.gateS.Count, m.gateFlat, m.maxCut, m.maxFill);
    }
}
