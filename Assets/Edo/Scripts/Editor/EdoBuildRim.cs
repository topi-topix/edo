// 崖の縁の土留め — 区画の線の上に立つ塀の真下を削って野面の石垣を積み、塀を天端に載せる (EdoBuild の partial・2026-09-28・EDO-0477)
//
// ⭐ **何が足りなかったか**: 類型の造成(GradePads)は区画の縁で地山へ戻す ── 縁の外が平場より数 m 高いと、塀の足元から
//    平場までが土の急な法で残る(観理院の西の境: 山王社の前庭 14.5・本堂の平場 9.5 で 4.4m の土の法・施主裁定A 2026-09-28)。
// ⭕ 型: 区画の線の外(背)の地盤が、最寄りの平場より RIM_MIN 以上高い区間を「崖の縁」と見て、
//    ① 天端 = 背の地盤の中央値を 0.5m に切り下げた丸い数字で一直線(unity-modular-stonewall §3)
//    ② 石垣の前(区画の内)を平場の高さまで削る ── 法尻の前に犬走り RIM_BERM を平らに取り、その先は切土の法で平場へ
//    ③ 野面の乱積み(EdoAssets.Own.SannoNozura)を天端の線に据える(PlaceNozuraNet)── 見付は天端 − 平場
//    ④ 塀は天端に平らに載せる(呼び手が FenceRun を平らな座で呼ぶ)。
//    背の地盤が天端より RIM_BACK_TOL を超えて低い端は石垣を切る(背の無い石垣を立てない)。
// ⛔ 区画の外の地形は触らない(背の裏込めは描かない ── 背の地盤が天端に届く区間だけ積む)。
// 当たる先: 類型の全区画で、区画の縁の外が平場より高い所(崖の縁の寺社・武家の山際)。観理院の西の境が最初。
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoBuild
{
    /// <summary>背の地盤 − 平場 がこれ以上なら崖の縁と見る[m]。【確度 U】塀の下の土の法として立たない高さ。</summary>
    public const float RIM_MIN = 3.0f;
    /// <summary>塀の立つ線の地盤(造成前)− 平場 がこれ以上の所だけ崖の縁と見る[m]。【確度 U】崖の裾に立つ塀を外す。</summary>
    public const float RIM_LINE_MIN = 1.5f;
    /// <summary>平場がこの距離[m]より遠い縁は崖の縁と見ない(平場の無い所は削らない)。</summary>
    public const float RIM_REACH = 15f;
    /// <summary>背の地盤を測る離れ[m](区画の線から外へ)。</summary>
    public const float RIM_BACK_AT = 2.0f;
    /// <summary>背の地盤が天端よりこれ以上低い端は石垣を切る[m](背の無い石垣を立てない・硬い)。</summary>
    public const float RIM_BACK_TOL = 0.3f;
    /// <summary>石垣の一続きの最短[m]。これより短い区間は積まない。</summary>
    public const float RIM_MIN_LEN = 6f;
    /// <summary>区画の角を挟んで崖の縁の標本が抜けた長さ[m]がこれ以下なら、角まで継いで一続きにする(= <see cref="RIM_MIN_LEN"/>)。
    /// 角は平場から遠く <see cref="RIM_REACH"/> の外へ出やすい ── 抜けで鎖が切れ、角の片側が短いとして捨てられ、塀が崖の面で口を開けた
    /// (観理院 v5: 辺4 の終わり 0.9m・辺5 の頭 4.0m が抜け、辺4 の 5.8m を捨てた・2026-09-28 EDO-0477)。</summary>
    public const float RIM_CORNER_BRIDGE = 6f;

    /// <summary>角を挟んで継ぐ二つの区間の抜けを埋める ── 前の区間の末を角(s = <paramref name="lenPrev"/>)まで、次の区間の頭を角(s = 0)まで、
    /// 端の標本の背と平場で延ばす(背の低い端は後で天端の許しで切る)。</summary>
    static void BridgeCorner(List<Vector3> prev, float lenPrev, List<Vector3> next)
    {
        var e = prev[prev.Count - 1]; if (lenPrev - e.x > 1e-3f) prev.Add(new Vector3(lenPrev, e.y, e.z));
        var h = next[0]; if (h.x > 1e-3f) next.Insert(0, new Vector3(0f, h.y, h.z));
    }

    /// <summary>法尻の前に平らに取る犬走り[m]。【確度 U】</summary>
    public const float RIM_BERM = 2.0f;
    /// <summary>野面の法(3分)。焼いた駒と同じ(EdoAssets.Own.SannoNozura)。</summary>
    public const float RIM_BATTER = 0.3f;

    /// <summary>崖の縁の石垣の一続き。</summary>
    public class RimRun
    {
        /// <summary>区画の線の上の折れ線(塀が立つ線)。</summary>
        public List<Vector2> line = new List<Vector2>();
        /// <summary>天端の線(石垣の見え面の上の縁)= <see cref="line"/> を内へ off 寄せた折れ線。</summary>
        public List<Vector2> crestLine = new List<Vector2>();
        public float crest, foot;
        /// <summary>辺ごとの区間 (辺の番号, s0, s1)── 辺の a からの走り。</summary>
        public List<KeyValuePair<int, Vector2>> spans = new List<KeyValuePair<int, Vector2>>();
        public float Length { get { float l = 0f; for (int i = 1; i < line.Count; i++) l += Vector2.Distance(line[i - 1], line[i]); return l; } }
    }

    /// <summary>**崖の縁の区間を測る**(区画の線を 1m 刻み)。<paramref name="A"/>/<paramref name="B"/>/<paramref name="outward"/> は
    /// 囲う辺(呼び手が塀を建てる辺だけ・<paramref name="use"/>)、<paramref name="pads"/>/<paramref name="padY"/> は造成した平場。
    /// 続く辺(前の辺の b = 次の辺の a)の区間は一続きに継ぐ。天端 = 背の地盤の中央値を 0.5m に切り下げ、背がそれより
    /// <see cref="RIM_BACK_TOL"/> を超えて低い端は切る。<paramref name="report"/> に区間ごとの天端・平場・見付・長さを刷る。</summary>
    public static List<RimRun> RimRetainRuns(IList<Vector2> A, IList<Vector2> B, IList<Vector2> outward, IList<bool> use,
                                             IList<Vector2[]> pads, IList<float> padY, out string report)
    {
        var sb = new System.Text.StringBuilder();
        int n = A.Count;
        // 辺ごとの標本 (s, 背の地盤, 平場)
        var samp = new List<Vector3>[n];
        for (int k = 0; k < n; k++)
        {
            samp[k] = new List<Vector3>();
            if (!use[k]) continue;
            float L = Vector2.Distance(A[k], B[k]); if (L < 1e-3f) continue;
            var d = (B[k] - A[k]) / L;
            int m = Mathf.Max(1, Mathf.RoundToInt(L));
            for (int i = 0; i <= m; i++)
            {
                float s = L * i / m; var p = A[k] + d * s;
                float foot = float.NaN, bd = float.MaxValue;
                for (int j = 0; j < pads.Count; j++)
                {
                    float dd = EdoGeom.PIP(pads[j], p) ? 0f : EdoGeom.DistToPolyEdge(pads[j], p);
                    if (dd < bd) { bd = dd; foot = padY[j]; }
                }
                if (bd > RIM_REACH) continue;
                var q = p + outward[k].normalized * RIM_BACK_AT;
                float back = Ground(q.x, q.y);
                if (float.IsNaN(back) || back - foot < RIM_MIN) continue;
                // ⭐ 塀の立つ線そのものが平場より RIM_LINE_MIN 以上高い所だけ(崖の**縁**)── 崖の裾に立つ塀(線の地盤 ≈ 平場)は
                //    背が高くても石垣にしない(観理院 辺3: 線 10.4・平場 9.5 は施主裁定X の「崖の裾に塀」)。造成前の地盤で測る。
                float lineG = BaseDem()(p.x, p.y); if (float.IsNaN(lineG)) lineG = Ground(p.x, p.y);
                if (lineG - foot < RIM_LINE_MIN) continue;
                samp[k].Add(new Vector3(s, back, foot));
            }
        }
        // 辺の中の一続き(標本の間 ≤ 1.5m)
        var pieces = new List<KeyValuePair<int, List<Vector3>>>();
        for (int k = 0; k < n; k++)
        {
            List<Vector3> cur = null;
            foreach (var v in samp[k])
            {
                if (cur == null || v.x - cur[cur.Count - 1].x > 1.5f) { cur = new List<Vector3>(); pieces.Add(new KeyValuePair<int, List<Vector3>>(k, cur)); }
                cur.Add(v);
            }
        }
        // 辺を跨いで継ぐ(前の辺の終わり ≈ b・次の辺の始まり ≈ a・b = a)
        var chains = new List<List<KeyValuePair<int, List<Vector3>>>>();
        var usedP = new bool[pieces.Count];
        for (int i = 0; i < pieces.Count; i++)
        {
            if (usedP[i]) continue;
            // 頭を探す: この区間の始まりへ継ぐ前の区間が無い物から
            var ch = new List<KeyValuePair<int, List<Vector3>>> { pieces[i] }; usedP[i] = true;
            bool grew = true;
            while (grew)
            {
                grew = false;
                var last = ch[ch.Count - 1]; int k = last.Key; float Lk = Vector2.Distance(A[k], B[k]);
                float gapK = Lk - last.Value[last.Value.Count - 1].x;
                if (gapK > RIM_CORNER_BRIDGE) break;
                for (int j = 0; j < pieces.Count; j++)
                {
                    if (usedP[j]) continue; int kj = pieces[j].Key;
                    if (Vector2.Distance(B[k], A[kj]) > 0.05f || gapK + pieces[j].Value[0].x > RIM_CORNER_BRIDGE) continue;
                    BridgeCorner(last.Value, Lk, pieces[j].Value);
                    ch.Add(pieces[j]); usedP[j] = true; grew = true; break;
                }
            }
            // 前へも継ぐ
            grew = true;
            while (grew)
            {
                grew = false;
                var first = ch[0]; int k = first.Key;
                if (first.Value[0].x > RIM_CORNER_BRIDGE) break;
                for (int j = 0; j < pieces.Count; j++)
                {
                    if (usedP[j]) continue; int kj = pieces[j].Key; float Lj = Vector2.Distance(A[kj], B[kj]);
                    if (Vector2.Distance(B[kj], A[k]) > 0.05f || Lj - pieces[j].Value[pieces[j].Value.Count - 1].x + first.Value[0].x > RIM_CORNER_BRIDGE) continue;
                    BridgeCorner(pieces[j].Value, Lj, first.Value);
                    ch.Insert(0, pieces[j]); usedP[j] = true; grew = true; break;
                }
            }
            chains.Add(ch);
        }
        var outp = new List<RimRun>();
        foreach (var ch in chains)
        {
            // 天端 = 背の地盤の中央値を 0.5 に切り下げ
            var backs = new List<float>(); float foot = float.MaxValue;
            foreach (var pc in ch) foreach (var v in pc.Value) { backs.Add(v.y); foot = Mathf.Min(foot, v.z); }
            backs.Sort(); float crest = Mathf.Floor(backs[backs.Count / 2] / 0.5f) * 0.5f;
            // 端を切る: 背が天端 − TOL より低い標本を両端から落とす
            var flat = new List<KeyValuePair<int, Vector3>>();
            foreach (var pc in ch) foreach (var v in pc.Value) flat.Add(new KeyValuePair<int, Vector3>(pc.Key, v));
            int i0 = 0, i1 = flat.Count - 1;
            while (i0 <= i1 && flat[i0].Value.y < crest - RIM_BACK_TOL) i0++;
            while (i1 >= i0 && flat[i1].Value.y < crest - RIM_BACK_TOL) i1--;
            if (i1 <= i0) continue;
            // 残りを辺ごとの区間へ
            var rr = new RimRun { crest = crest, foot = foot };
            for (int i = i0; i <= i1; i++)
            {
                int k = flat[i].Key; float s = flat[i].Value.x;
                if (rr.spans.Count == 0 || rr.spans[rr.spans.Count - 1].Key != k) rr.spans.Add(new KeyValuePair<int, Vector2>(k, new Vector2(s, s)));
                else { var sp = rr.spans[rr.spans.Count - 1]; rr.spans[rr.spans.Count - 1] = new KeyValuePair<int, Vector2>(k, new Vector2(sp.Value.x, s)); }
            }
            foreach (var sp in rr.spans)
            {
                int k = sp.Key; var d = (B[k] - A[k]).normalized;
                var p0 = A[k] + d * sp.Value.x; var p1 = A[k] + d * sp.Value.y;
                if (rr.line.Count == 0 || Vector2.Distance(rr.line[rr.line.Count - 1], p0) > 0.05f) rr.line.Add(p0);
                rr.line.Add(p1);
            }
            float len = rr.Length;
            int dropped = flat.Count - (i1 - i0 + 1);
            if (len < RIM_MIN_LEN)
            {
                sb.AppendLine(string.Format("    崖の縁 {0:F1}m は短い(< {1:F0}m)── 積まない(辺 {2})", len, RIM_MIN_LEN,
                    string.Join("+", rr.spans.Select(s => string.Format("{0} s{1:F1}〜{2:F1}", s.Key, s.Value.x, s.Value.y)).ToArray())));
                continue;
            }
            sb.AppendLine(string.Format("    崖の縁: 辺 {0}・長さ {1:F1}m・天端 {2:F1}(背の地盤の中央値 {3:F2} を 0.5 に切り下げ)・平場 {4:F2}・見付 {5:F2}m{6}",
                string.Join("+", rr.spans.Select(s => s.Key.ToString()).ToArray()), len, crest, backs[backs.Count / 2], foot, crest - foot,
                dropped > 0 ? string.Format("・背が天端 − {0:F1} より低い端 {1} 標本を切った", RIM_BACK_TOL, dropped) : ""));
            outp.Add(rr);
        }
        report = sb.ToString();
        return outp;
    }

    /// <summary>区画の線の折れ線 <paramref name="line"/> を、区画の内へ <paramref name="off"/>[m] 寄せた折れ線(折れの所は寄せた線どうしの交点)。
    /// <paramref name="inward"/> は区間ごとの内向き。</summary>
    public static List<Vector2> OffsetPolyline(IList<Vector2> line, float off, Func<Vector2, Vector2, Vector2> inward)
    {
        var res = new List<Vector2>(); int m = line.Count;
        var nrm = new Vector2[m - 1];
        for (int i = 0; i + 1 < m; i++) nrm[i] = inward(line[i], line[i + 1]);
        res.Add(line[0] + nrm[0] * off);
        for (int i = 1; i + 1 < m; i++)
        {
            Vector2 p0 = line[i - 1] + nrm[i - 1] * off, d0 = (line[i] - line[i - 1]).normalized;
            Vector2 p1 = line[i] + nrm[i] * off, d1 = (line[i + 1] - line[i]).normalized;
            float den = d0.x * d1.y - d0.y * d1.x;
            if (Mathf.Abs(den) < 1e-4f) { res.Add(line[i] + nrm[i] * off); continue; }
            float t = ((p1.x - p0.x) * d1.y - (p1.y - p0.y) * d1.x) / den;
            res.Add(p0 + d0 * t);
        }
        res.Add(line[m - 1] + nrm[m - 2] * off);
        return res;
    }

    /// <summary>**石垣の前(区画の内)を平場まで削る。**天端の線 <see cref="RimRun.crestLine"/> から内への距離 x、走りの外への
    /// はみ出し a として、節点の高さを min(今, 限り) に下げる(⛔ 上げない・区画の外は触らない):
    /// x ≥ 法尻 t(= 見付 × 法)なら 限り = 平場 + (a + max(0, x − t − 犬走り)) / 切土の法、
    /// x &lt; t(駒の下)なら 限り = 平場 + (t − x)/(t + <paramref name="back"/>)·見付 + a / 切土の法(天端の背から法尻への弦 ── 駒の中に納まる)。
    /// 返りは書いた節点と最大の切土。</summary>
    public static string CutBeforeRim(Vector2[] parcel, RimRun r, float back = 1.0f, float cutRun = 1.0f)
    {
        var t = T(); var td = t.terrainData; int res = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        var L = r.crestLine; int m = L.Count;
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in parcel) { mnx = Mathf.Min(mnx, p.x); mxx = Mathf.Max(mxx, p.x); mnz = Mathf.Min(mnz, p.y); mxz = Mathf.Max(mxz, p.y); }
        int i0 = Mathf.Clamp(Mathf.FloorToInt((mnx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int i1 = Mathf.Clamp(Mathf.CeilToInt((mxx - tp.x) / ts.x * (res - 1)), 0, res - 1);
        int j0 = Mathf.Clamp(Mathf.FloorToInt((mnz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int j1 = Mathf.Clamp(Mathf.CeilToInt((mxz - tp.z) / ts.z * (res - 1)), 0, res - 1);
        int w = i1 - i0 + 1, h = j1 - j0 + 1;
        var H = td.GetHeights(i0, j0, w, h);
        float expo = r.crest - r.foot, toe = expo * RIM_BATTER;
        var cum = new float[m]; for (int i = 1; i < m; i++) cum[i] = cum[i - 1] + Vector2.Distance(L[i - 1], L[i]);
        float total = cum[m - 1];
        // 内向き = 区画の中心の側
        Vector2 cen = Vector2.zero; foreach (var p in parcel) cen += p; cen /= parcel.Length;
        int written = 0; float maxCut = 0f;
        for (int j = 0; j < h; j++)
            for (int i = 0; i < w; i++)
            {
                var q = NodeXZ(tp, ts, res, i0 + i, j0 + j);
                if (!EdoGeom.PIP(parcel, q)) continue;
                // 天端の線への最寄り
                float bd = float.MaxValue, bx = 0f, bs = 0f;
                for (int k = 0; k + 1 < m; k++)
                {
                    Vector2 ab = L[k + 1] - L[k]; float l = ab.magnitude; if (l < 1e-4f) continue; Vector2 d = ab / l;
                    float u = Vector2.Dot(q - L[k], d); float uc = Mathf.Clamp(u, 0f, l);
                    Vector2 pr = L[k] + d * uc; float dist = Vector2.Distance(q, pr);
                    if (dist < bd)
                    {
                        bd = dist;
                        Vector2 inN = new Vector2(-d.y, d.x); if (Vector2.Dot(cen - L[k], inN) < 0f) inN = -inN;
                        bx = Vector2.Dot(q - pr, inN) + 0f;
                        // 端の外は走りの向きの距離を a に
                        bs = cum[k] + u;
                        if (u < 0f || u > l) bx = Vector2.Dot(q - L[k], inN);
                    }
                }
                float a = bs < 0f ? -bs : (bs > total ? bs - total : 0f);
                if (bx < -back - 0.5f) continue;                 // 天端の背より外(区画の線の際)は触らない
                float lim = bx >= toe ? r.foot + (a + Mathf.Max(0f, bx - toe - RIM_BERM)) / cutRun
                                      : r.foot + (toe - bx) / (toe + back) * expo + a / cutRun;
                float y = H[j, i] * ts.y + tp.y;
                if (y <= lim) continue;
                maxCut = Mathf.Max(maxCut, y - lim);
                H[j, i] = Mathf.Clamp01((lim - tp.y) / ts.y); written++;
            }
        td.SetHeightsDelayLOD(i0, j0, H); td.SyncHeightmap();
        return string.Format("石垣の前を削った: 節点 {0}・最大の切土 {1:F2}m(法尻 {2:F2}m・犬走り {3:F1}m・平場 {4:F2})", written, maxCut, toe, RIM_BERM, r.foot);
    }
    /// <summary>**受けの駒の上向きの面の索引**(実メッシュの三角形・0.5m の升に振る)。<see cref="At"/> は点 (x, z) の真上の
    /// 上向きの面の最も高い所(無ければ NaN)。⭐ 塀を石垣の天端に載せる・塀の下端を検めるときの床(触れている箇所を測る ── 規則21)。
    /// <see cref="BedTopAt"/>(光線)と同じ値を、升ごとに三角形を引いて速く返す。</summary>
    public class BedIndex
    {
        readonly Dictionary<long, List<Vector3[]>> bins = new Dictionary<long, List<Vector3[]>>();
        const float BIN = 0.5f;
        public int Tris;
        static long Key(int i, int j) { return ((long)i << 32) ^ (uint)j; }
        public BedIndex(IEnumerable<GameObject> beds)
        {
            foreach (var g in beds) if (g != null)
                foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
                {
                    var mesh = mf.sharedMesh; if (mesh == null) continue;
                    var M = mf.transform.localToWorldMatrix; var vs = mesh.vertices; var ts = mesh.triangles;
                    var W = new Vector3[vs.Length]; for (int i = 0; i < vs.Length; i++) W[i] = M.MultiplyPoint3x4(vs[i]);
                    for (int t = 0; t + 2 < ts.Length; t += 3)
                    {
                        Vector3 a = W[ts[t]], b = W[ts[t + 1]], c = W[ts[t + 2]];
                        var nv = Vector3.Cross(b - a, c - a); float mag = nv.magnitude;
                        if (mag < 1e-9f || Mathf.Abs(nv.y) / mag < 0.05f) continue;           // 鉛直の面は床にならない
                        var tri = new[] { a, b, c }; Tris++;
                        int x0 = Mathf.FloorToInt(Mathf.Min(a.x, Mathf.Min(b.x, c.x)) / BIN), x1 = Mathf.FloorToInt(Mathf.Max(a.x, Mathf.Max(b.x, c.x)) / BIN);
                        int z0 = Mathf.FloorToInt(Mathf.Min(a.z, Mathf.Min(b.z, c.z)) / BIN), z1 = Mathf.FloorToInt(Mathf.Max(a.z, Mathf.Max(b.z, c.z)) / BIN);
                        for (int i = x0; i <= x1; i++) for (int j = z0; j <= z1; j++)
                        { List<Vector3[]> l; long k = Key(i, j); if (!bins.TryGetValue(k, out l)) bins[k] = l = new List<Vector3[]>(); l.Add(tri); }
                    }
                }
        }
        /// <summary>(x, z) と <paramref name="r"/> 離れた 8 点の床の**最も高い所**(無ければ NaN)── 受けの駒の縁と目地は跨ぐ。
        /// ⭐ 受けの駒の縁と、それに載る駒の縁が同じ線に揃う所(門構えの基壇の布石の表 = 門の札の foot の表・EDO-0491)で、
        ///    縁の上の点を床の外と読んで外の地面からの「浮き」と数えた(西溜池2 の長屋門 1.22m・w1 の冠木門 0.04m)。
        /// ⭐ 布石の石と石の目地(V の溝・幅 0.1m 未満・深さ 0.03m)も跨ぐ ── 門の敷居は目地の上に渡るので溝の底は当たりでない
        ///    (2026-09-30 十坊0 ほか 0.02〜0.03m。塀の <c>GroundBedSpan</c> と同じ 5cm の跨ぎ)。</summary>
        public float AtNear(float x, float z, float r)
        {
            float b = At(x, z);
            for (int k = 0; k < 8; k++)
            {
                float a = k * Mathf.PI / 4f, nb = At(x + r * Mathf.Cos(a), z + r * Mathf.Sin(a));
                if (!float.IsNaN(nb) && (float.IsNaN(b) || nb > b)) b = nb;
            }
            return b;
        }
        /// <summary>(x, z) の真上の面の最も高い所(無ければ NaN)。</summary>
        public float At(float x, float z)
        {
            List<Vector3[]> l; if (!bins.TryGetValue(Key(Mathf.FloorToInt(x / BIN), Mathf.FloorToInt(z / BIN)), out l)) return float.NaN;
            float best = float.NaN;
            foreach (var t in l)
            {
                Vector3 a = t[0], b = t[1], c = t[2];
                float d = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z); if (Mathf.Abs(d) < 1e-12f) continue;
                float u = ((b.z - c.z) * (x - c.x) + (c.x - b.x) * (z - c.z)) / d;
                float v = ((c.z - a.z) * (x - c.x) + (a.x - c.x) * (z - c.z)) / d;
                if (u < -1e-5f || v < -1e-5f || u + v > 1f + 1e-5f) continue;
                float y = u * a.y + v * b.y + (1f - u - v) * c.y;
                if (float.IsNaN(best) || y > best) best = y;
            }
            return best;
        }
    }

    /// <summary>**崖の縁の石垣に載せる塀を、区画の線から内へ寄せる量**[m]。線 a→b に沿って、足あと(内へ o ± <paramref name="half"/>)の下が
    /// 石垣の天端の面(<paramref name="bed"/> ≥ 天端 − 0.05)に載る割合を測り、<paramref name="need"/> 以上になる最小の o を返す
    /// (届かなければ割合の最も高い o)。<paramref name="frac"/> にその割合。
    /// ⭐ 石垣は区画の中に納める(背の端が線の際)ので、天端の面は線から内へ 0.4〜1.0m の帯にしか無い(野面の背の不揃い)。
    /// ⛔ 線の上に芯を置くと足あとの外の半分が地面に掛かり、座が地面の最低へ引かれて塀が沈む(観理院の西 1.5m・2026-09-28)。</summary>
    public static float RimFenceInset(BedIndex bed, Vector2 a, Vector2 b, Vector2 inw, float half, float crest, float maxIn, float need, out float frac)
    {
        float L = Vector2.Distance(a, b); var d = (b - a) / Mathf.Max(L, 1e-4f);
        float bestO = half + 0.02f, bestF = -1f;
        for (float o = half + 0.02f; o <= maxIn + 1e-3f; o += 0.05f)
        {
            int n = 0, ok = 0;
            for (float u = 0.25f; u <= L - 0.25f + 1e-3f; u += 0.25f)
                foreach (float lat in new[] { o - half, o, o + half })
                {
                    var q = a + d * u + inw * lat; n++;
                    float v = bed != null ? bed.At(q.x, q.y) : float.NaN;
                    if (!float.IsNaN(v) && v >= crest - 0.05f) ok++;
                }
            float f = n > 0 ? ok / (float)n : 0f;
            if (f > bestF + 1e-4f) { bestF = f; bestO = o; }
            if (f >= need) { frac = f; return o; }
        }
        frac = bestF; return bestO;
    }

    // ============================================================ 区画の角の塀の口(2026-09-28・EDO-0477 P2 隅)
    /// <summary>囲いの駒の**足元の面**が区画の線からどれだけ外(<paramref name="hOut"/>)・内(<paramref name="hIn"/>)にあるか[m]。
    /// 駒の足元の水平断面(<see cref="SectionAt"/>・高さ 0.05)の実寸から測る。<see cref="CornerReach"/> が隅の延ばしに使う。
    /// 表裏の対(板塀の型 = DobeiRun)は表が線の上・裏が 0.2 内なので、内の面は裏の内の面。杭・矢来など連続しない種別は 0。</summary>
    public static void FenceFaceOffsets(string kind, out float hOut, out float hIn)
    {
        hOut = hIn = 0f;
        Func<string, float, float> half = (path, sc) =>
        {
            float z0 = float.MaxValue, z1 = float.MinValue;
            foreach (var v in SectionAt(path, Vector3.zero, 0f, 0.05f / sc, false)) { z0 = Mathf.Min(z0, v.z); z1 = Mathf.Max(z1, v.z); }
            return z1 > z0 ? (z1 - z0) * 0.5f * sc : 0f;
        };
        switch (kind)
        {
            case "dobei": hOut = hIn = half(EdoAssets.Own.Dobei2m, 1f); break;   // 練塀(一体物・芯が線の上)
            case "yarai": case "boji": case "kui": case "none": case "nagaya": break;
            default: { float h = half(PHei, ES); hOut = h; hIn = 0.2f + h; break; }   // ita / ita+ikegaki / ishigaki+hei / 既定
        }
    }

    /// <summary>**区画の角で塀の run を頂点の先へ延ばす長さ**[m]。
    /// 辺の線に芯を置いた二本の run が頂点で切れると、折れの外側(出隅なら区画の外の面・入隅なら内の面)に楔形の口が開く
    /// ── 観理院の西の隅で 0.38m・0.13m(2026-09-28 EDO-0468 の検査)。両方の run を「その側の面の線からの離れ × tan(折れ/2)
    /// + 0.02」だけ延ばすと、二本の面が交点まで届いて口が閉じる(内側は重なる ── 駒どうしの埋め込みは数えない・§0a)。
    /// ⛔ 2026-09-28 までは「隅は留め継ぎが未解決なので開放」(NeribeiRun の注記)のまま、全邸の角に口を残していた。
    /// <paramref name="dPrev"/>/<paramref name="dThis"/> = 頂点へ入る辺・出る辺の向き、<paramref name="outPrev"/> = 入る辺の外向き。
    /// 条件は**硬い**(隙は許容0)── 延ばせない鋭い折り返し(135° 超)は 0 を返し、口は検査が拾う。</summary>
    public static float CornerReach(Vector2 dPrev, Vector2 dThis, Vector2 outPrev, float hOut, float hIn)
    {
        dPrev.Normalize(); dThis.Normalize();
        float th = Mathf.Acos(Mathf.Clamp(Vector2.Dot(dPrev, dThis), -1f, 1f));
        if (th < 1e-3f || th > Mathf.PI * 0.75f) return 0f;
        bool convex = Vector2.Dot(dThis, outPrev) < 0f;               // 出る辺が内へ折れる = 出隅
        float h = convex ? hOut : hIn;
        return h <= 0f ? 0f : h * Mathf.Tan(th * 0.5f) + 0.02f;
    }

    /// <summary>**隣の区画が持つ辺の線を壁体が越える量**[m](EDO-0574)── 駒の壁体(<see cref="Body"/> ── 屋根・軒は数えない・施主裁定A 2026-09-21「軒は区画の線を越えてよい」)の頂点のうち、
    /// 辺 a→b(<paramref name="outward"/> = 自分の区画から見た外 = 隣の側)の線の外へ出る最も深い所。辺の両端の 0.5m 先までの射影に入る頂点だけ数える。0 = 越えない。
    /// 硬い(区域侵犯 0)── 呼び手は越えた分だけ run の端を引いて建て直す。当たる先: 類型の全区画の囲いで、隣の区画が持つ辺に出会う端(樹下の土塀・十坊の杭と板塀 × 岡部)。</summary>
    public static float BodyOverLine(IList<GameObject> pieces, Vector2 a, Vector2 b, Vector2 outward)
    {
        float L = (b - a).magnitude; if (L < 1e-4f || pieces == null) return 0f; var d = (b - a) / L; float worst = 0f;
        foreach (var g in pieces)
        {
            if (g == null || !g.activeInHierarchy) continue;
            foreach (var v in Body(g.transform, 999999))
            {
                var q = new Vector2(v.x, v.z); float t = Vector2.Dot(q - a, d); if (t < -0.5f || t > L + 0.5f) continue;
                worst = Mathf.Max(worst, Vector2.Dot(q - a, outward));
            }
        }
        return worst;
    }
}
