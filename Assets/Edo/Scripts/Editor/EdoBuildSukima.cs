// EdoBuildSukima.cs — 建物と隣の構造物の間の隙のうち、通りから裏手(敷地の内側)へ抜ける物だけを柵で塞ぐ(EDO-0503)。
//
// ⭐ 施主の考え方(2026-10-03):「柵ができる基準は、建物と隣の構造物の間にすき間があり、さらに裏手に敷地の内側に
//    入るようになっているときにふさぐ。建物の隣は左右とは限らず後方もあり得る」。
//    ⛔ 2026-10-03 まで表店の辺の端の「空きの幅」で決めていて、辻の角の土蔵造りの妻の脇の行き止まり(幅 0.68m)にも
//    柵を立てた(施主「余計なところについた柵」)。幅や区画の線との距離では決めない ── 抜けるかどうかで決める。
//
// やり方(すべて据えた駒の実メッシュから測る・規則21):
//   1. 区画の周りを升目に割り、地面から 0.3〜1.4m の帯にある**立った面**(壁・柱・塀・石垣の三角形)が掛かる升を、
//      その駒の持ち物として埋める(屋根・庇・地表は寝ているので掛からない)。
//   2. 区画の外は、表店の辺の外(通り)だけを空け、それ以外の線の外は塞ぐ(隣の敷地)。人の登れない急な斜面
//      (勾配 0.75 超 ≒ 37°【U】)も塞ぐ相手にする(施主 2026-10-03「地形そのものということもありえる」)。
//   3. 人の肩の半幅だけ埋めた升を太らせ、通れる升だけを残す。
//   4. 通りから、店の奥行より深い所(裏庭)まで、通れる升をたどる。⛔ 同じ列の店と店の間は路地(町の型)なので、
//      たどる前に口を仮に塞いでおく(路地口は柵で塞がない)。
//   5. 届いたら、その道筋を横切る「二つの駒の間の最も近い所」(左右・後ろを問わない)のうち、最も短い物を柵の線に採る。
//      届かなくなるまで繰り返す。
//
// 条件の硬さ: 「裏へ抜けない」は硬い(許容0・塞ぐまで足す)。柵の外の面の揃え(柱の面)は柔らかい(升の分解能 ±0.1m)。
// 当たる先: 類型ビルダーの町屋の囲い(表店の列の端・角・後ろの棟との間)── 町屋の全区画。

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>塞ぐ口 ── 柵の線 a→b と、通りの側の向き。</summary>
    public struct SukimaGate { public Vector2 a, b, outward; public string between; public float len; }

    /// <summary>**通りから裏手へ抜ける隙だけ**を見つけて、塞ぐ柵の線を返す(EDO-0503・施主 2026-10-03)。
    /// <paramref name="fronts"/> は表店の辺(a, b, outward)。<paramref name="root"/> は区画の組(Tatemono・Kakoi を測る)。
    /// 区画の外の駒(隣の敷地の石垣・塀・棟)もシーンから拾って相手にする。</summary>
    public static List<SukimaGate> SukimaGates(Vector2[] poly, List<Vector2[]> fronts, Transform root, out string note,
        float cell = 0.20f, float halfBody = 0.30f, float yLo = 0.3f, float yHi = 1.4f, float maxGate = 8f, float embed = 0.10f, float maxGrade = 0.75f)
    {
        var gates = new List<SukimaGate>();
        float x0 = poly.Min(p => p.x) - 2f, z0 = poly.Min(p => p.y) - 2f;
        float x1 = poly.Max(p => p.x) + 2f, z1 = poly.Max(p => p.y) + 2f;
        int nx = Mathf.CeilToInt((x1 - x0) / cell), nz = Mathf.CeilToInt((z1 - z0) / cell);
        int N = nx * nz;
        Func<int, Vector2> ctr = k => new Vector2(x0 + (k % nx + 0.5f) * cell, z0 + (k / nx + 0.5f) * cell);
        Func<float, float, int> idx = (x, z) =>
        {
            int ix = Mathf.FloorToInt((x - x0) / cell), iz = Mathf.FloorToInt((z - z0) / cell);
            return ix < 0 || iz < 0 || ix >= nx || iz >= nz ? -1 : iz * nx + ix;
        };
        Func<Vector2, float> distFront = p =>
        {
            float best = float.PositiveInfinity;
            foreach (var f in fronts) best = Mathf.Min(best, EdoGeom.DistToEdge(p, f[0], f[1]));
            return best;
        };

        // ── 1. 持ち主の一覧(区画の組の中は Tatemono/Kakoi の子ごと、外はシーンの組の孫ごと)
        var owners = new List<Transform>(); var ownerOf = new Dictionary<Transform, int>();
        var occ = new int[N]; for (int k = 0; k < N; k++) occ[k] = -1;
        var bbox = new Bounds(new Vector3((x0 + x1) * 0.5f, 0f, (z0 + z1) * 0.5f), new Vector3(x1 - x0, 1e5f, z1 - z0));
        foreach (var mr in UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
        {
            if (!mr.enabled || !mr.gameObject.activeInHierarchy || !mr.bounds.Intersects(bbox)) continue;
            var mf = mr.GetComponent<MeshFilter>(); if (mf == null || mf.sharedMesh == null) continue;
            Transform own = OwnerOf(mr.transform, root);
            if (own == null) continue;
            if (own.name.StartsWith("sukima_", StringComparison.Ordinal)) continue;     // 前の巡の柵は相手にしない
            int oi;
            if (!ownerOf.TryGetValue(own, out oi)) { oi = owners.Count; owners.Add(own); ownerOf[own] = oi; }
            RasterSteep(mf, occ, oi, idx, cell, yLo, yHi, x0, z0, x1, z1);
        }
        int BOUND = owners.Count;                                             // 隣の敷地(区画の線の外で通りでない所)
        int SLOPE = BOUND + 1;                                                // 人の登れない急な斜面(地形そのもの)

        // ── 2. 区画の外: 通り(表店の辺の外 2m)だけ空け、ほかは塞ぐ
        var street = new bool[N]; var inside = new bool[N];
        for (int k = 0; k < N; k++)
        {
            var c = ctr(k);
            if (EdoGeom.PIP(poly, c)) { inside[k] = true; continue; }
            bool st = false;
            foreach (var f in fronts)
            {
                var q = c - f[0]; var d = (f[1] - f[0]); float L = d.magnitude; var u = d / L;
                float t = Vector2.Dot(q, u), n = Vector2.Dot(q, f[2]);
                if (t > -0.5f && t < L + 0.5f && n > -0.05f && n < 2.0f) { st = true; break; }
            }
            if (st) street[k] = true; else if (occ[k] < 0) occ[k] = BOUND;
        }
        // 急な斜面(勾配 > maxGrade)も人を通さない相手 ── 施主 2026-10-03「地形そのものということもありえる。急な斜面とか」
        for (int k = 0; k < N; k++)
        {
            if (occ[k] >= 0) continue;
            var c = ctr(k); float h = cell;
            float gx = (Ground(c.x + h, c.y) - Ground(c.x - h, c.y)) / (2f * h);
            float gz = (Ground(c.x, c.y + h) - Ground(c.x, c.y - h)) / (2f * h);
            if (Mathf.Sqrt(gx * gx + gz * gz) > maxGrade) occ[k] = SLOPE;
        }

        // ── 店の列と奥行(裏庭の深さ)
        var rowOf = new Dictionary<int, int>(); float depth = 0f;
        for (int oi = 0; oi < owners.Count; oi++)
        {
            var nm = owners[oi].name;
            if (!nm.StartsWith("Omotedana", StringComparison.Ordinal) || owners[oi].parent == null || owners[oi].parent.parent != root) continue;
            int us = nm.IndexOf('_'); int r;
            if (us > 9 && int.TryParse(nm.Substring(9, us - 9), out r)) rowOf[oi] = r;
        }
        for (int k = 0; k < N; k++) if (occ[k] >= 0 && rowOf.ContainsKey(occ[k]) && inside[k]) depth = Mathf.Max(depth, distFront(ctr(k)));
        float yardD = depth + 0.5f;

        // ── 持ち主ごとの縁の升(空きに接する升)
        var rim = new List<int>[SLOPE + 1]; for (int i = 0; i <= SLOPE; i++) rim[i] = new List<int>();
        var area = new int[SLOPE + 1];
        for (int k = 0; k < N; k++)
        {
            int o = occ[k]; if (o < 0) continue; area[o]++;
            int ix = k % nx, iz = k / nx; bool edge = false;
            if (ix > 0 && occ[k - 1] != o) edge = true; else if (ix < nx - 1 && occ[k + 1] != o) edge = true;
            else if (iz > 0 && occ[k - nx] != o) edge = true; else if (iz < nz - 1 && occ[k + nx] != o) edge = true;
            if (!edge) continue;
            var c = ctr(k);
            if (o == BOUND && EdoGeom.DistToPolyEdge(poly, c) > 0.5f) continue;         // 区画の線のすぐ外だけ
            rim[o].Add(k);
        }

        // ── 5 の候補: 二つの持ち主の間の最も近い所(同じ列の店どうしは路地 → 仮に塞ぐ線へ回す)
        var cands = new List<SukimaGate>(); var rojiLines = new List<Vector2[]>();
        float minA = 1.0f / (cell * cell);                                     // 1m² 未満の駒(灯籠・木の幹)は口の相手にしない
        for (int i = 0; i <= SLOPE; i++)
        {
            if (rim[i].Count == 0 || (i < BOUND && area[i] < minA)) continue;
            for (int j = i + 1; j <= SLOPE; j++)
            {
                if (rim[j].Count == 0 || (j < BOUND && area[j] < minA)) continue;
                if (i >= BOUND && j >= BOUND) continue;                      // 線と斜面の間は駒が無い
                float best = float.PositiveInfinity; int bi = -1, bj = -1;
                // 粗く最近を出してから、最近 +0.1 の中で通りに最も近い組を採る(柵は角の柱の面に寄る)
                foreach (var ki in rim[i]) { var ci = ctr(ki); foreach (var kj in rim[j]) { float d = (ctr(kj) - ci).sqrMagnitude; if (d < best) { best = d; bi = ki; bj = kj; } } }
                if (bi < 0) continue;
                float dmin = Mathf.Sqrt(best);
                if (dmin < 2f * halfBody || dmin > maxGate) continue;
                float lim = (dmin + 0.1f) * (dmin + 0.1f), bestF = float.PositiveInfinity;
                foreach (var ki in rim[i]) { var ci = ctr(ki); foreach (var kj in rim[j]) { var cj = ctr(kj); if ((cj - ci).sqrMagnitude > lim) continue; float f = distFront((ci + cj) * 0.5f); if (f < bestF) { bestF = f; bi = ki; bj = kj; } } }
                Vector2 a = ctr(bi), b = ctr(bj);
                bool roji = rowOf.ContainsKey(i) && rowOf.ContainsKey(j) && rowOf[i] == rowOf[j];
                if (roji) { rojiLines.Add(new[] { a, b }); continue; }
                cands.Add(new SukimaGate { a = a, b = b, len = dmin, between = Nm(owners, i, BOUND) + "|" + Nm(owners, j, BOUND) });
            }
        }

        // ── 3〜5: 通れる升 → 通りから裏庭へ届くか → 届けば道筋を横切る最も短い候補を柵にする
        var blocked = new bool[N];
        for (int k = 0; k < N; k++) blocked[k] = occ[k] >= 0;
        foreach (var l in rojiLines) MarkLine(blocked, l[0], l[1], idx, cell, nx);
        var used = new HashSet<int>(); var msgs = new List<string>();
        int rad = Mathf.CeilToInt(halfBody / cell - 1e-3f);
        // ⭐ 繰り返しは必ず止まる(施主 2026-10-03「無限ループに陥らないか」): 一巡ごとに候補を一つ使い切り(同じ候補は二度採らない)、
        //    候補が尽きるか、道筋を横切る候補が無ければ ⚠ を刷って抜ける。さらに巡の上限 MAX_GATES で打ち切り、上限に当たれば ⚠ を刷る。
        const int MAX_GATES = 12; bool closed = false;
        for (int pass = 0; pass < MAX_GATES; pass++)
        {
            var pass_ = Dilate(blocked, nx, nz, rad);
            var par = new int[N]; for (int k = 0; k < N; k++) par[k] = -2;
            var qu = new Queue<int>();
            for (int k = 0; k < N; k++) if (street[k] && !pass_[k]) { par[k] = -1; qu.Enqueue(k); }
            int hit = -1;
            while (qu.Count > 0 && hit < 0)
            {
                int k = qu.Dequeue(); int ix = k % nx, iz = k / nx;
                int[] nb = { ix > 0 ? k - 1 : -1, ix < nx - 1 ? k + 1 : -1, iz > 0 ? k - nx : -1, iz < nz - 1 ? k + nx : -1 };
                foreach (var m in nb)
                {
                    if (m < 0 || par[m] != -2 || pass_[m]) continue;
                    par[m] = k; qu.Enqueue(m);
                    if (inside[m] && distFront(ctr(m)) > yardD) { hit = m; break; }
                }
            }
            if (hit < 0) { closed = true; break; }
            var path = new HashSet<int>(); for (int k = hit; k >= 0; k = par[k]) path.Add(k);
            int pick = -1;
            for (int c = 0; c < cands.Count; c++)
            {
                if (used.Contains(c)) continue;
                if (!LineHits(path, cands[c].a, cands[c].b, idx, cell, nx)) continue;
                if (pick < 0 || cands[c].len < cands[pick].len) pick = c;
            }
            if (pick < 0)
            {
                var hc = ctr(hit);
                msgs.Add(string.Format("⚠ 通りから裏庭へ抜ける道({0:F1},{1:F1})を横切る二つの駒の間が見つからず塞げない", hc.x, hc.y));
                closed = true; break;
            }
            used.Add(pick);
            MarkLine(blocked, cands[pick].a, cands[pick].b, idx, cell, nx);
            var g = cands[pick];
            // 柵の線は升の中心から両端を駒の面の先へ延ばす(升の半分+食い込み)
            var u2 = (g.b - g.a).normalized; float ext = cell * 0.5f + embed;
            g.a -= u2 * ext; g.b += u2 * ext;
            var nrm = new Vector2(-u2.y, u2.x); var mid = (g.a + g.b) * 0.5f;
            g.outward = distFront(mid + nrm * 0.5f) < distFront(mid - nrm * 0.5f) ? nrm : -nrm;
            g.len = (g.b - g.a).magnitude;
            gates.Add(g);
        }
        if (!closed) msgs.Add(string.Format("⚠ 柵を {0} 本立てても裏庭へ抜ける道が残る(上限で打ち切り)", MAX_GATES));
        note = string.Format("隙の口: 裏庭の深さ {0:F1}m(店の奥行 +0.5)・候補 {1}・路地口 {2}(塞がない)・塞いだ口 {3}{4}{5}",
            yardD, cands.Count, rojiLines.Count, gates.Count,
            gates.Count > 0 ? "(" + string.Join(" / ", gates.Select(x => x.between + " " + x.len.ToString("F2") + "m").ToArray()) + ")" : "",
            msgs.Count > 0 ? "・" + string.Join("・", msgs.ToArray()) : "");
        return gates;
    }

    static string Nm(List<Transform> owners, int i, int bound) { return i == bound ? "区画の線" : i == bound + 1 ? "急な斜面" : owners[i].name; }

    /// <summary>升の持ち主: 区画の組の中は Tatemono/Kakoi などの直下の子、外はシーンの組の孫(地形・植栽は除く)。</summary>
    static Transform OwnerOf(Transform t, Transform root)
    {
        var chain = new List<Transform>(); for (var x = t; x != null; x = x.parent) chain.Add(x);
        chain.Reverse();                                                       // [scene root, ..., t]
        int ri = chain.IndexOf(root);
        if (ri >= 0) return chain.Count > ri + 2 ? chain[ri + 2] : null;
        string top = chain[0].name;
        if (top.IndexOf("Tree", StringComparison.OrdinalIgnoreCase) >= 0 || top.IndexOf("Ue", StringComparison.Ordinal) == 0) return null;
        return chain.Count > 2 ? chain[2] : chain[chain.Count - 1];
    }

    /// <summary>立った三角形(|法線の Y| &lt; 0.5)のうち地面から yLo〜yHi の帯にある所を升へ焼く。</summary>
    static void RasterSteep(MeshFilter mf, int[] occ, int oi, Func<float, float, int> idx, float cell,
                            float yLo, float yHi, float x0, float z0, float x1, float z1)
    {
        var m = mf.transform.localToWorldMatrix; var mesh = mf.sharedMesh;
        var vs = mesh.vertices; var w = new Vector3[vs.Length];
        for (int i = 0; i < vs.Length; i++) w[i] = m.MultiplyPoint3x4(vs[i]);
        var tri = mesh.triangles; float step = cell * 0.5f;
        for (int t = 0; t < tri.Length; t += 3)
        {
            Vector3 a = w[tri[t]], b = w[tri[t + 1]], c = w[tri[t + 2]];
            float mnx = Mathf.Min(a.x, Mathf.Min(b.x, c.x)), mxx = Mathf.Max(a.x, Mathf.Max(b.x, c.x));
            float mnz = Mathf.Min(a.z, Mathf.Min(b.z, c.z)), mxz = Mathf.Max(a.z, Mathf.Max(b.z, c.z));
            if (mxx < x0 || mnx > x1 || mxz < z0 || mnz > z1) continue;
            var n = Vector3.Cross(b - a, c - a); float nl = n.magnitude; if (nl < 1e-8f) continue;
            if (Mathf.Abs(n.y / nl) >= 0.5f) continue;                       // 寝た面(屋根・庇・床・地表)
            var cen = (a + b + c) / 3f; float gy = Ground(cen.x, cen.z);
            float mny = Mathf.Min(a.y, Mathf.Min(b.y, c.y)), mxy = Mathf.Max(a.y, Mathf.Max(b.y, c.y));
            if (mxy < gy + yLo || mny > gy + yHi) continue;
            float L = Mathf.Max((b - a).magnitude, Mathf.Max((c - a).magnitude, (c - b).magnitude));
            int s = Mathf.Clamp(Mathf.CeilToInt(L / step), 1, 400);
            for (int i = 0; i <= s; i++)
                for (int j = 0; j <= s - i; j++)
                {
                    float u = i / (float)s, v = j / (float)s;
                    var p = a + (b - a) * u + (c - a) * v;
                    if (p.y < gy + yLo || p.y > gy + yHi) continue;
                    int k = idx(p.x, p.z); if (k >= 0 && occ[k] < 0) occ[k] = oi;
                }
        }
    }

    static bool[] Dilate(bool[] src, int nx, int nz, int r)
    {
        var o = new bool[src.Length];
        for (int k = 0; k < src.Length; k++)
        {
            if (!src[k]) continue;
            int ix = k % nx, iz = k / nx;
            for (int dz = -r; dz <= r; dz++)
                for (int dx = -r; dx <= r; dx++)
                {
                    if (dx * dx + dz * dz > r * r) continue;
                    int x = ix + dx, z = iz + dz; if (x < 0 || z < 0 || x >= nx || z >= nz) continue;
                    o[z * nx + x] = true;
                }
        }
        return o;
    }

    static IEnumerable<int> LineCells(Vector2 a, Vector2 b, Func<float, float, int> idx, float cell, int nx)
    {
        float L = (b - a).magnitude; int s = Mathf.Max(1, Mathf.CeilToInt(L / (cell * 0.25f)));
        int prev = -1;
        for (int i = 0; i <= s; i++)
        {
            var p = Vector2.Lerp(a, b, i / (float)s); int k = idx(p.x, p.y); if (k < 0 || k == prev) continue;
            if (prev >= 0 && k % nx != prev % nx && k / nx != prev / nx) yield return (k / nx) * nx + prev % nx;   // 斜めの継ぎを4近傍で閉じる
            yield return k; prev = k;
        }
    }

    static void MarkLine(bool[] blocked, Vector2 a, Vector2 b, Func<float, float, int> idx, float cell, int nx)
    { foreach (var k in LineCells(a, b, idx, cell, nx)) blocked[k] = true; }

    static bool LineHits(HashSet<int> path, Vector2 a, Vector2 b, Func<float, float, int> idx, float cell, int nx)
    { foreach (var k in LineCells(a, b, idx, cell, nx)) if (path.Contains(k)) return true; return false; }
}
