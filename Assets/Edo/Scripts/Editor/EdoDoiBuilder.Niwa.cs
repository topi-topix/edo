// 土井大隅守上屋敷 — 奥庭(Stage6)。
//
// ⭐ 案A(EDO-0533・2026-10-04): 6a は `gardens[G_Sensui]`(泉水・汀線を持つ庭 = NiwaModel)、6b〜6h は
//    `gardens[G_Sensui]` と `gardens[G_Okuniwa]` の庭方の据え付けの欄を読み、置く・測る・据えるは
//    EdoBuildNiwa.cs「指図の庭」の節の関数だけで行う(規則21)。欄の意味は top-level `gardenFields`。
//    以下の旧い註(①〜⑨の順・G_Okuniwa の池)は旧案の記録として残す。
// ⛔ **この部分クラスは指図 `docs/Sashizu/doi_sashizu.json` の `gardens.G_Okuniwa` を読むだけで、
//    値を持たない。**据え位置(石組・灯籠・沓脱・飛石・沢飛石・植栽・築山・園路・汀線)は
//    すべて指図が正典で、⛔ **実装で動かさない**(`gardens.G_Okuniwa.impl.noInvent`)。
//    水に落ちている物があっても据え直さず、指図方へ差し戻す。
//
// 工程の順序は指図 `gardens.G_Okuniwa.impl.stage`:
//   ①池の掘削と築山の盛土(**非冪等**)→ ②護岸(石組・州浜・乱杭)→ ③水尻の埋樋と落とし溝
//   → ④石組・灯籠・沓脱・飛石・沢飛石 → ⑤園路と野面の石段 → ⑥稲荷 → ⑦垣 → ⑧植栽・刈込・下草 → ⑨井戸
//
// ⚠ **`WaterBaker.Create` は呼ばない。**
//   `Create` は内部で `Recarve` を呼び、`Recarve` は **snap 矩形(輪郭 bbox + 余白150m)の全域**を
//   ① スナップショットから復元し ② 4パスの平滑化をかけ ③ `SetHeights` で書き戻す。
//   当邸の池では snap が **312 × 320m** になり(指図 `impl.noRecarve`)、溜池・外堀・岡部邸・
//   松江松平邸の造成が丸ごとその平滑化に巻き込まれる。⇒ 指図の「⛔ Recarve しない/焼く範囲は
//   庭の矩形に限る」を守るため、**掘削は自前で庭の矩形の中だけに行い**、`WaterBody` は
//   水面メッシュのためだけに組んで `RebuildSurface` だけを呼ぶ(地形に触れない)。
//   ⚠ 指図 `impl.waterBaker` は `WaterBaker.Create` を指示しているが、上の理由で採れない
//     — 指図方へ差し戻す(⛔ 黙って読み替えない)。
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoDoiBuilder
{
    /// <summary>欄の文字列。無い欄は null(⛔ KeyNotFound で庭の段を丸ごと止めない ── 無い欄は呼び手が Wait へ申し送る)。</summary>
    static string Sk(Dictionary<string, object> d, string k) { object o; return d != null && d.TryGetValue(k, out o) ? o as string : null; }

    // ------------------------------------------------------------------ 奥庭のモデル(生成器 Niwa の移植)
    public class NiwaM
    {
        public Dictionary<string, object> g;
        public float u0, v0, u1, v1;
        public float waterY, depth, dmax, baseY;
        public bool hasShallow; public float shV0, shV1, shBedY;
        public Vector2[] pond;
        public List<Dictionary<string, object>> mounds = new List<Dictionary<string, object>>();
        public List<string> unshaped = new List<string>();   // 形の欄が無く盛らなかった築山(差し戻し)

        public bool Inside(float u, float v)
        { return u0 - 1e-9f <= u && u <= u1 + 1e-9f && v0 - 1e-9f <= v && v <= v1 + 1e-9f; }

        public bool InPond(float u, float v)
        {
            bool c = false; int n = pond.Length;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = pond[i], b = pond[(i + 1) % n];
                if ((a.y > v) != (b.y > v) && u < a.x + (b.x - a.x) * (v - a.y) / (b.y - a.y)) c = !c;
            }
            return c;
        }
        public float DShore(float u, float v)
        {
            float best = float.MaxValue; int n = pond.Length;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = pond[i], b = pond[(i + 1) % n];
                Vector2 d = b - a; float L2 = Mathf.Max(1e-12f, d.sqrMagnitude);
                float t = Mathf.Clamp01(Vector2.Dot(new Vector2(u, v) - a, d) / L2);
                best = Mathf.Min(best, Vector2.Distance(new Vector2(u, v), a + d * t));
            }
            return best;
        }
        public float Bed(float u, float v)
        {
            if (hasShallow && shV0 <= v && v <= shV1) return shBedY;
            return waterY - depth * Mathf.Pow(DShore(u, v) / dmax, 0.6f);
        }
        /// <summary>築山・土手の盛り上がり(全基の max)。生成器 `Niwa._m1` の移植。</summary>
        public float Mound(float u, float v)
        {
            float h = 0f;
            foreach (var t in mounds) h = Mathf.Max(h, M1(t, u, v));
            return h;
        }
        float M1(Dictionary<string, object> t, float u, float v)
        {
            // ⭐ 案A(EDO-0533): 築山は裾の多角形 `skirt`(間)+ `rise`。裾からの内への距離を芯までで正規化し、余弦で上げる。
            //   `kata` に「平たい」があれば肩を持つ山 ── 正規化 0.6 から上は頂の平ら(庭方の設計 2026-10-03)。
            if (Has(t, "skirt"))
            {
                Vector2[] sk; float dIn;
                SkirtOf(t, out sk, out dIn);
                var q = new Vector2(u, v);
                if (sk == null || !EdoGeom.PIP(sk, q)) return 0f;
                float r = EdoGeom.DistToPolyEdge(sk, q) / dIn;
                float flat = (Has(t, "kata") && Sk(t, "kata").Contains("平たい")) ? 0.6f : 1f;
                return F(t["rise"]) * 0.5f * (1f - Mathf.Cos(Mathf.PI * Mathf.Min(1f, r / flat)));
            }
            if (Has(t, "kata") && Sk(t, "kata") == "土手")
            {
                float tu0 = F(t["u0"]), tu1 = F(t["u1"]), tv0 = F(t["v0"]), tv1 = F(t["v1"]);
                if (!(tu0 <= u && u <= tu1 && tv0 <= v && v <= tv1)) return 0f;
                float r, a9, a0, a1;
                // ⭐ 減衰軸は `decay` が決める。⛔ 未指定を既定へ倒さない(指図の `dote_check` が鳴らす)
                if (Has(t, "decay") && Sk(t, "decay") == "u")
                { r = Mathf.Abs(u - (tu0 + tu1) / 2f) / ((tu1 - tu0) / 2f); a9 = v; a0 = tv0; a1 = tv1; }
                else
                { r = Mathf.Abs(v - (tv0 + tv1) / 2f) / ((tv1 - tv0) / 2f); a9 = u; a0 = tu0; a1 = tu1; }
                float f9 = 1f;
                if (Has(t, "taperEnds"))
                {
                    float te = F(t["taperEnds"]);
                    float d9 = Mathf.Min(a9 - a0, a1 - a9);
                    if (d9 < te) f9 = 0.5f * (1f - Mathf.Cos(Mathf.PI * Mathf.Max(d9, 0f) / te));
                }
                return F(t["rise"]) * f9 * 0.5f * (1f + Mathf.Cos(Mathf.PI * Mathf.Min(r, 1f)));
            }
            float ru = F(t["dU"]) / 2f, rv = F(t["dV"]) / 2f;
            float x = (u - F(t["u"])) / ru, y = (v - F(t["v"])) / rv;
            float rr = Mathf.Sqrt(x * x + y * y);
            float rd = 0f;
            if (Has(t, "daira") && rr > 1e-9f)
            {
                var da = O(t["daira"]);
                float a = F(da["dU"]) / 2f / ru, b = F(da["dV"]) / 2f / rv;
                rd = 1f / Mathf.Sqrt(Mathf.Pow(x / (rr * a), 2f) + Mathf.Pow(y / (rr * b), 2f));
                rd = Mathf.Min(rd, 0.95f);
            }
            if (rr >= 1f) return 0f;
            float s = rr <= rd ? 0f : (rr - rd) / (1f - rd);
            return F(t["rise"]) * 0.5f * (1f + Mathf.Cos(Mathf.PI * s));
        }
        /// <summary>造園後の地表。池の中は池床、外は面+築山(生成器 `Niwa.ground`)。
        /// ⭐ 案A: 面は点ごとの造成後の地盤(DesignY = 算出物 graded)── 庭の矩形が一枚の面とは限らない。</summary>
        public float Ground(float u, float v)
        {
            // 中島は掘り残し(盛らない)── 汀の内でも天端 topY(指図 nakajima.how「掘り残し」)
            if (Nakajima != null && EdoGeom.PIP(Nakajima, new Vector2(u, v))) return nakaTop;
            if (InPond(u, v)) return Bed(u, v);
            float b = DesignY(u, v); if (float.IsNaN(b)) b = baseY;
            return b + Mound(u, v);
        }

        public Vector2[] Nakajima; public float nakaTop;
        readonly Dictionary<Dictionary<string, object>, KeyValuePair<Vector2[], float>> _sk = new Dictionary<Dictionary<string, object>, KeyValuePair<Vector2[], float>>();
        void SkirtOf(Dictionary<string, object> t, out Vector2[] sk, out float dIn)
        {
            KeyValuePair<Vector2[], float> kv;
            if (!_sk.TryGetValue(t, out kv))
            {
                var pl = A(t["skirt"]); var P = new Vector2[pl.Count];
                for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); P[i] = new Vector2(F(q[0]), F(q[1])); }
                float mx = 0f, mnu = float.MaxValue, mxu = float.MinValue, mnv = float.MaxValue, mxv = float.MinValue;
                foreach (var q in P) { mnu = Mathf.Min(mnu, q.x); mxu = Mathf.Max(mxu, q.x); mnv = Mathf.Min(mnv, q.y); mxv = Mathf.Max(mxv, q.y); }
                for (float uu = mnu; uu <= mxu; uu += 0.1f) for (float vv = mnv; vv <= mxv; vv += 0.1f)
                { var q = new Vector2(uu, vv); if (EdoGeom.PIP(P, q)) mx = Mathf.Max(mx, EdoGeom.DistToPolyEdge(P, q)); }
                kv = new KeyValuePair<Vector2[], float>(P, Mathf.Max(mx, 0.1f)); _sk[t] = kv;
            }
            sk = kv.Key; dIn = kv.Value;
        }
    }

    static NiwaM _niwa;
    public static NiwaM NiwaModel
    {
        get
        {
            if (_niwa == null)
            {
                Dictionary<string, object> g = null;
                foreach (var o in A(D["gardens"])) { var q = O(o); if (Has(q, "migiwa")) { g = q; break; } }
                if (g == null) return null;
                var mg = O(g["migiwa"]);
                var pts = A(mg["pts"]);
                var n = new NiwaM
                {
                    g = g,
                    u0 = F(g["u0"]), v0 = F(g["v0"]), u1 = F(g["u1"]), v1 = F(g["v1"]),
                    // ⭐ 案A: 深さは文(芯 0.9・州浜 1:8)で、数は bedYMin(池床の最低)── 深さ = 水面 − 池床の最低
                    waterY = F(mg["waterY"]), depth = Has(mg, "depthMax") ? F(mg["depthMax"]) : F(mg["waterY"]) - F(mg["bedYMin"])
                };
                n.pond = new Vector2[pts.Count];
                for (int i = 0; i < pts.Count; i++)
                { var p = A(pts[i]); n.pond[i] = new Vector2(F(p[0]), F(p[1])); }
                if (Has(mg, "shallow"))
                {
                    var sh = O(mg["shallow"]);
                    n.hasShallow = true; n.shV0 = F(sh["v0"]); n.shV1 = F(sh["v1"]); n.shBedY = F(sh["bedY"]);
                }
                n.baseY = DesignY((n.u0 + n.u1) / 2f, (n.v0 + n.v1) / 2f);
                // ⛔ 形(裾 skirt・土手の矩形・芯と径 dU/dV)を持たない築山は盛らない ── 意図だけの欄(例「野筋」)を既定の形で埋めない(差し戻し)
                foreach (var o in A(g["tsukiyama"]))
                {
                    var t = O(o); if (t == null) continue;
                    bool shaped = Has(t, "skirt") || (Has(t, "kata") && Sk(t, "kata") == "土手" && Has(t, "u0")) || (Has(t, "dU") && Has(t, "dV") && Has(t, "u") && Has(t, "v"));
                    if (shaped) n.mounds.Add(t); else n.unshaped.Add(Sk(t, "name"));
                }
                if (Has(g, "nakajima") && Has(O(g["nakajima"]), "pts"))
                {
                    var nk = O(g["nakajima"]); var np = A(nk["pts"]); n.Nakajima = new Vector2[np.Count];
                    for (int i = 0; i < np.Count; i++) { var q = A(np[i]); n.Nakajima[i] = new Vector2(F(q[0]), F(q[1])); }
                    n.nakaTop = F(nk["topY"]);
                }
                // 汀からの最大距離(池床の放物面の正規化)。生成器と同じ 0.1間 刻みで走査する
                float dmax = 0f;
                for (float u = n.u0; u <= n.u1 + 1e-9f; u += 0.1f)
                    for (float v = n.v0; v <= n.v1 + 1e-9f; v += 0.1f)
                        if (n.InPond(u, v)) dmax = Mathf.Max(dmax, n.DShore(u, v));
                n.dmax = dmax > 0f ? dmax : 1f;
                _niwa = n;
            }
            return _niwa;
        }
    }

    static Vector2 Wu(float u, float v) { return Grid.W(u, v); }
    /// <summary>汀線の点(指図の `roles` は 1 始まり)。</summary>
    static Vector2 Sh(int oneBased)
    { var n = NiwaModel; return n.pond[((oneBased - 1) % n.pond.Length + n.pond.Length) % n.pond.Length]; }
    /// <summary>設計の汀の点を**水面メッシュの縁**(Chaikin×2)へ寄せる(最寄り点)。
    /// ⭐ 庭方の第3条(2026-09-06)— 護岸・州浜・水際に据える物は「**見えている水際**」に取り合わせる。
    /// ⛔ **地形の水際で据えない** — heightmap は格子 2.0m で設計より粗く、外向きに進んで
    /// 最初に地表が waterY を超える点で据えると最大 2m 引っ込んで石も砂利も浮く。</summary>
    static Vector2 SnapToWaterEdge(Vector2 g)
    {
        var E = PondEdge();
        Vector2 best = g; float bd = float.MaxValue;
        for (int i = 0, j = E.Length - 1; i < E.Length; j = i++)
        {
            Vector2 a = E[j], b = E[i], ab = b - a;
            float L2 = Mathf.Max(1e-12f, ab.sqrMagnitude);
            float t = Mathf.Clamp01(Vector2.Dot(g - a, ab) / L2);
            Vector2 q = a + ab * t;
            float d = Vector2.Distance(g, q);
            if (d < bd) { bd = d; best = q; }
        }
        return best;
    }

    /// <summary>汀線を frm→to へ辿った折れ線(1 始まり・巡回)。
    /// ⭕ **据え位置に使う線なので水面メッシュの縁へ寄せる**(庭方の第3条)。
    /// ⚠ 面積の計測と `clip` は**設計の汀**(`n.pond`)のまま — 生成器が刷る表と食い違わせないため。</summary>
    static List<Vector2> ShoreWalk(int frm, int to)
    {
        var n = NiwaModel; int N = n.pond.Length;
        var outp = new List<Vector2>();
        int i = frm;
        for (int k = 0; k < N + 1; k++)
        {
            outp.Add(SnapToWaterEdge(Sh(i)));
            if (i == to) break;
            i = i % N + 1;
        }
        return outp;
    }
    static Vector2 LerpLine(List<Vector2> L, float t, out Vector2 dir)
    {
        float total = 0f;
        for (int i = 0; i + 1 < L.Count; i++) total += Vector2.Distance(L[i], L[i + 1]);
        float want = Mathf.Clamp01(t) * total, acc = 0f;
        for (int i = 0; i + 1 < L.Count; i++)
        {
            float d = Vector2.Distance(L[i], L[i + 1]);
            if (acc + d >= want || i + 2 == L.Count)
            {
                dir = (L[i + 1] - L[i]).normalized;
                return Vector2.Lerp(L[i], L[i + 1], d < 1e-9f ? 0f : (want - acc) / d);
            }
            acc += d;
        }
        dir = Vector2.right; return L[L.Count - 1];
    }
    static float LineLen(List<Vector2> L)
    { float t = 0f; for (int i = 0; i + 1 < L.Count; i++) t += Vector2.Distance(L[i], L[i + 1]); return t; }

    static Vector2[] _pondW;
    /// <summary>設計の汀(`migiwa.pts`)を**世界座標**で。セルとの重なりは世界の軸平行で見るので要る。</summary>
    static Vector2[] PondWorld()
    {
        if (_pondW != null) return _pondW;
        var n = NiwaModel;
        var r = new Vector2[n.pond.Length];
        for (int i = 0; i < n.pond.Length; i++) r[i] = Wu(n.pond[i].x, n.pond[i].y);
        _pondW = r; return r;
    }
    static float Cross2(Vector2 p, Vector2 q, Vector2 r)
    { return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x); }
    static bool SegHit(Vector2 a, Vector2 b, Vector2 c, Vector2 d)
    {
        float d1 = Cross2(c, d, a), d2 = Cross2(c, d, b), d3 = Cross2(a, b, c), d4 = Cross2(a, b, d);
        return ((d1 > 0f) != (d2 > 0f)) && ((d3 > 0f) != (d4 > 0f));
    }
    /// <summary>セル(世界の軸平行な正方形)が汀多角形と**少しでも重なる**か(coverage &gt; 0)。
    /// ⛔⛔ **中心点で判定しない。**水口は 2.07m しかなく、heightmap の格子 2.0m では
    /// 中心点がどのセルにも入らず**陸が残って池が東西に割れた**(2026-09-06 普請検査・庭方の第1条)。</summary>
    static bool PondOverlapsCell(float wx, float wz, float half)
    {
        var P = PondWorld();
        // ① セルの 3×3 の標本のどれかが池の中(= セルが池に含まれる/半分掛かる)
        for (int a = -1; a <= 1; a++)
            for (int b = -1; b <= 1; b++)
                if (EdoGeom.PIP(P, new Vector2(wx + a * half, wz + b * half))) return true;
        // ② 汀の頂点がセルの中(= 池がセルより細い)
        for (int i = 0; i < P.Length; i++)
            if (Mathf.Abs(P[i].x - wx) <= half && Mathf.Abs(P[i].y - wz) <= half) return true;
        // ③ 汀の辺がセルの辺と交わる(= 池がセルを貫く)
        Vector2 c0 = new Vector2(wx - half, wz - half), c1 = new Vector2(wx + half, wz - half);
        Vector2 c2 = new Vector2(wx + half, wz + half), c3 = new Vector2(wx - half, wz + half);
        for (int i = 0, j = P.Length - 1; i < P.Length; j = i++)
            if (SegHit(P[j], P[i], c0, c1) || SegHit(P[j], P[i], c1, c2)
             || SegHit(P[j], P[i], c2, c3) || SegHit(P[j], P[i], c3, c0)) return true;
        return false;
    }

    /// <summary>直前の <see cref="EditNiwaHeights"/> のセルの一辺[m]。重なり判定に要る。</summary>
    static float _niwaCell = 2f;

    /// <summary>ハイトマップの窓を開いて fn(u, v, 現況) で書き、閉じる。
    /// ⛔ **区画の外と庭の矩形の外は触らない**。</summary>
    static string EditNiwaHeights(Func<float, float, float, float> fn, string label)
    {
        var n = NiwaModel;
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        var corners = new Vector2[] { Wu(n.u0, n.v0), Wu(n.u1, n.v0), Wu(n.u1, n.v1), Wu(n.u0, n.v1) };
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var q in corners)
        {
            mnx = Mathf.Min(mnx, q.x); mxx = Mathf.Max(mxx, q.x);
            mnz = Mathf.Min(mnz, q.y); mxz = Mathf.Max(mxz, q.y);
        }
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        int x0 = IX(mnx - 2f), x1 = IX(mxx + 2f), z0 = IZ(mnz - 2f), z1 = IZ(mxz + 2f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        var P = Poly;
        _niwaCell = ts.x / (hres - 1);
        int cells = 0; double up = 0, dn = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            float wx = tp.x + (x0 + x) * ts.x / (hres - 1);
            float wz = tp.z + (z0 + z) * ts.z / (hres - 1);
            if (!EdoGeom.PIP(P, new Vector2(wx, wz))) continue;            // ⛔ 区画の外
            var g = Grid.L(new Vector2(wx, wz));
            if (!n.Inside(g.x, g.y)) continue;                              // ⛔ 庭の矩形の外
            float cur = H[z, x] * ts.y + tp.y;
            float y = fn(g.x, g.y, cur);
            if (float.IsNaN(y)) continue;
            if (y > cur) up += y - cur; else dn += cur - y;
            H[z, x] = (y - tp.y) / ts.y; cells++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        float cell = ts.x / (hres - 1); double a = cell * cell;
        return string.Format("{0}: cells={1} 盛{2:F0}m³ 切{3:F0}m³", label, cells, up * a, dn * a);
    }

    /// <summary>汀の内側で水面下へ沈める最小の深さ[m]。⚠ **設計値ではなく格子の都合**
    /// (heightmap 2.0m で幅 8.7m の池を掘るための下限の保証)。⛔ 指図へ写さない。
    /// ⭕ 掘る値そのものは**設計の池床**(椀形)で、これは「浅く残らない」ための床。</summary>
    const float POND_MIN_SUB = 0.30f;

    static Vector2[] _pondEdge;
    /// <summary>**水面メッシュの縁**(グリッド座標)。
    /// ⚠⚠ `WaterBaker.RebuildSurface` は輪郭に **Chaikin ×2**(`WaterGeom.SmoothTagged(…, 2)`)を
    /// 掛けてから三角形にするので、**見えている水際は `migiwa.pts` の折れ線ではない**(隅が落ちる)。
    /// ⇒ ⭕ **護岸・州浜・下草・水際の草は「この縁」に取り合わせる。**
    /// ⛔ **地形の水際(外へ進んで最初に地表が waterY を超える点)で据えない** — 地形は格子 2.0m で
    /// 設計より粗く、最大 2m 内へずれるので、石も砂利も引っ込んで浮く(2026-09-06 庭方の第3条)。</summary>
    static Vector2[] PondEdge()
    {
        if (_pondEdge != null) return _pondEdge;
        var n = NiwaModel;
        var o3 = new List<Vector3>();
        foreach (var p in n.pond) { var w = Wu(p.x, p.y); o3.Add(new Vector3(w.x, n.waterY, w.y)); }
        var sm = WaterGeom.SmoothTagged(o3, null, 2);
        var res = new Vector2[sm.Count];
        for (int i = 0; i < sm.Count; i++) res[i] = Grid.L(new Vector2(sm[i].x, sm[i].z));
        _pondEdge = res;
        return res;
    }
    /// <summary>水面メッシュの縁の内側か(⛔ `NiwaM.InPond` は**設計の**汀で、こちらは**見える**汀)。</summary>
    static bool InWater(float u, float v) { return EdoGeom.PIP(PondEdge(), new Vector2(u, v)); }

    /// <summary>**検査④ 掘った池が水面の下に納まっているか。**
    /// 汀多角形の内側の heightmap のセルを数え、①水面より上のセルが 0 か ②最深がいくつか を刷る。
    /// ⚠ 2026-09-06 の普請検査は 14.4% が水面より上で、池が東西2つに割れていた。</summary>
    [MenuItem(MENU + "検査④ 池が水面の下に納まっているか PondQA")]
    public static void PondQAMenu() { Debug.Log("[Doi] " + PondQA()); }
    public static string PondQA()
    {
        var n = NiwaModel; if (n == null) return "検査④: 庭が無い";
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        float cell = ts.x / (hres - 1);
        // 汀の bbox を世界座標で囲う
        float mnx = float.MaxValue, mxx = float.MinValue, mnz = float.MaxValue, mxz = float.MinValue;
        foreach (var p in n.pond)
        {
            var w = Wu(p.x, p.y);
            mnx = Mathf.Min(mnx, w.x); mxx = Mathf.Max(mxx, w.x);
            mnz = Mathf.Min(mnz, w.y); mxz = Mathf.Max(mxz, w.y);
        }
        int inCell = 0, above = 0; float deepest = float.MaxValue;
        for (float x = mnx - cell; x <= mxx + cell; x += cell)
            for (float z = mnz - cell; z <= mxz + cell; z += cell)
            {
                var g = Grid.L(new Vector2(x, z));
                if (!n.InPond(g.x, g.y)) continue;
                float y = t.SampleHeight(new Vector3(x, 0f, z)) + tp.y;
                inCell++;
                if (y > n.waterY) above++;
                deepest = Mathf.Min(deepest, y);
            }
        var sb = new System.Text.StringBuilder();
        sb.Append("検査④ 池: 汀内 " + inCell + " セル / 水面(" + n.waterY.ToString("F2")
                + ")より上 = " + above + " セル"
                + (inCell == 0 ? "" : " / 格子上の最深 " + deepest.ToString("F2")
                   + "(水深 " + (n.waterY - deepest).ToString("F2") + "m)")
                + (above == 0 ? " ⭕" : " ⚠ 池が割れる"));

        // ── 水口(`migiwa.roles` が「水口」と書いた汀の点)が水面下か。⛔ 番号を写さず役から引く
        var mg = O(n.g["migiwa"]);
        var roles = Has(mg, "roles") ? O(mg["roles"]) : null;
        int mina = 0, minaBad = 0; float minaWorst = -99f;
        if (roles != null)
            foreach (var kv in roles)
            {
                if (kv.Value == null || S(kv.Value) == null || S(kv.Value).IndexOf("水口") < 0) continue;
                int idx; if (!int.TryParse(kv.Key, out idx)) continue;
                Vector2 gp = Sh(idx);
                // 汀の点そのものと、池の内側へ 0.3間 寄せた点の両方を見る
                for (int s = 0; s < 2; s++)
                {
                    Vector2 q = gp;
                    if (s == 1)
                    {
                        // 池の重心へ 0.3間 寄せる(内側)
                        Vector2 c = Vector2.zero;
                        for (int i = 0; i < n.pond.Length; i++) c += n.pond[i];
                        c /= n.pond.Length;
                        q = gp + (c - gp).normalized * 0.3f;
                    }
                    var w = Wu(q.x, q.y);
                    float y = t.SampleHeight(new Vector3(w.x, 0f, w.y)) + tp.y;
                    mina++;
                    if (y > n.waterY) { minaBad++; minaWorst = Mathf.Max(minaWorst, y - n.waterY); }
                }
            }
        sb.Append("\n   水口: " + mina + " 点中 水面より上 " + minaBad + " 点"
                + (minaBad == 0 ? " ⭕(東西の池がつながる)" : " ⚠ 最大 +" + minaWorst.ToString("F2") + "m — 池が割れる"));

        // ── 沢飛石の足元が水中か(⛔ 陸に立っていたら渡り石にならない)
        int sw = 0, swBad = 0;
        var tk = GameObject.Find(Grp);
        if (tk != null)
        {
            var g2 = tk.transform.Find("Niwa/Tenkei");
            if (g2 != null)
                foreach (var tr in g2.GetComponentsInChildren<Transform>())
                {
                    if (tr.name.IndexOf("Sawatobi") < 0) continue;
                    float y = t.SampleHeight(tr.position) + tp.y;
                    sw++;
                    if (y > n.waterY) swBad++;
                }
        }
        sb.Append("\n   沢飛石: " + sw + " 個中 足元が陸 " + swBad + " 個"
                + (sw == 0 ? "(まだ据えていない)" : (swBad == 0 ? " ⭕" : " ⚠")));

        Wait("池の深さ: 指図 `migiwa.depthMax` 1.00m・`bedY` 25.20 に対し、"
           + "**heightmap のセル 2.0m では幅 8.7m の池の底を彫りきれない**(格子上の実測の最深 "
           + (inCell == 0 ? "—" : (n.waterY - deepest).ToString("F2")) + "m)。"
           + "⭕ 椀形の床は設計どおり書き、汀ぎわは " + POND_MIN_SUB.ToString("F2")
           + "m を下限として保証した(⛔ 平床にしていない)。"
           + "⇒ 指図方へ:『格子の限界で設計深さに届かない』断りが要る");
        return sb.ToString();
    }

    // ------------------------------------------------------------------ Stage6 奥庭
    [MenuItem(MENU + "6 奥庭(掘削・護岸・点景・園路・稲荷・植栽)")]
    public static void Stage6Menu() { Debug.Log("[Doi] " + Stage6_Niwa()); }
    public static string Stage6_Niwa()
    {
        // ⭐ 案A(EDO-0533): 6b〜6h は庭方の据え付けの設計(2026-10-04)の欄で読む。6g 垣は S6(EdoDoiBuilder.Saku)が受け持つので止めたまま
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var n = NiwaModel;
        if (n == null) return "指図に汀線を持つ庭が無い";
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("[6a] " + Niwa_A_Dokou());
        sb.AppendLine("[6b] " + Niwa_B_Gogan());
        sb.AppendLine("[6c] " + Niwa_C_Mizushiri());
        sb.AppendLine("[6d] " + Niwa_D_Tenkei());
        sb.AppendLine("[6e] " + Niwa_E_Enro());
        sb.AppendLine("[6f] " + Niwa_F_Yashiro());
        sb.AppendLine("[6g] " + Niwa_G_Kaki());
        sb.AppendLine("[6h] " + Niwa_H_Shokusai());
        sb.Append(WaitReport());
        return sb.ToString();
    }

    // ---- ①池の掘削と築山の盛土 + 水面
    [MenuItem(MENU + "6a 池を掘り築山を盛る(⛔ WaterBaker.Recarve は呼ばない)")]
    public static void Niwa_A_Menu() { Debug.Log("[Doi] " + Niwa_A_Dokou()); }
    public static string Niwa_A_Dokou()
    {
        // ⭐ 案A(EDO-0533): 6a は案Aの欄(migiwa.bedYMin・tsukiyama.skirt・nakajima)を読むので止めない(6b〜6h も案Aの欄で読む)
        Stage0_Backup();
        var n = NiwaModel;
        // ⚠ 目標の面は**絶対値**(現況を読まない)なので何度流しても同じ = 冪等。
        //   マーカーは「一度は流した」を残すためだけに置く。
        //
        // ⚠⚠ **heightmap のセルは 2.0m。この池は幅 8.7m しかないので約4セルしか無い。**
        //   設計の池床は汀で水面に一致する(深さ 0 から放物で落ちる)ので、汀のすぐ内側のセルへ
        //   設計値をそのまま書くと、**隣の陸のセルとの補間で水面より上へ持ち上がる**。
        //   2026-09-06 の普請検査で、汀内 3,031 点のうち **14.4% が水面より上**・水口(汀 #8〜#10・#17)が
        //   陸になって**池が東西2つに割れて**いた。
        //   ⇒ ⭕ **汀の内側のセルは必ず水面 − `POND_MIN_SUB` 以下へ沈め、汀の外 1m は水面 +0.05 以上に保つ。**
        //   ⛔ **設計(`migiwa` の床の形)は動かしていない** — 格子で表せない所を格子の側で丸めているだけ。
        //   ⚠ 深さ `depthMax` 1.0m は 2m 格子では再現しきれない(下の Wait で申し送る)。
        //
        // ⭐ **2026-09-06 庭方の3条**(⛔ 前案の「汀内を一律 waterY−0.30」は撤回):
        //   ① セルの判定は**中心点でなく面の重なり**(`PondOverlapsCell`)。水口 2.07m に格子 2.0m では
        //      中心点判定だと1セルも入らず陸が残る = 池が東西に割れる。
        //   ② 落とす値は **min(現況, 設計の池床)**。⛔ 一律の平床にしない(水が透けて水たまりに見える)。
        //      `waterY − POND_MIN_SUB` は**下限の保証**として残す(汀ぎわのセルが浅く残らないため)。
        //   ③ 据え位置は**水面メッシュの縁**(`PondEdge`)から。⛔ 地形の水際で据えない。
        string r = EditNiwaHeights((u, v, cur) =>
        {
            float ground = n.Ground(u, v);
            if (n.Nakajima != null && EdoGeom.PIP(n.Nakajima, new Vector2(u, v))) return n.nakaTop;   // 中島は掘り残し
            if (PondOverlapsCell(Wu(u, v).x, Wu(u, v).y, _niwaCell * 0.5f))
            {
                // ⭕ 椀形の床(`Bed`)。⛔ 平床にしない。現況が既に深ければそれを残す
                float y = Mathf.Min(cur, n.Bed(u, v));
                return Mathf.Min(y, n.waterY - POND_MIN_SUB);      // 下限の保証
            }
            if (n.DShore(u, v) * Grid.ken <= 1.0f) return Mathf.Max(ground, n.waterY + 0.05f);
            return ground;
        }, "奥庭の土工(池床+築山+土手)");
        if (!Marked("6a_niwa_dokou")) Mark("6a_niwa_dokou", r);
        foreach (var nm in n.unshaped) { r += " / ⚠ 築山「" + nm + "」は形の欄(skirt)が無く盛らなかった(差し戻し)"; Wait("築山「" + nm + "」: 形の欄(skirt)が無い ── 盛らない(指図へ差し戻し)"); }
        r += " / " + PondQA();

        // 水面。⛔ WaterBaker.Create は呼ばない(理由はファイル冒頭)。地形には触れない。
        var grp = Group("Niwa/Mizu"); Clear(grp);
        var old = GameObject.Find("Water");
        Transform wparent = old != null ? old.transform : null;
        var go = new GameObject("P_DoiOkuniwa");
        Undo.RegisterCreatedObjectUndo(go, "water");
        go.transform.SetParent(grp, true);
        var wb = go.AddComponent<WaterBody>();
        wb.outline = new List<Vector3>();
        foreach (var p in n.pond) { var q = Wu(p.x, p.y); wb.outline.Add(new Vector3(q.x, n.waterY, q.y)); }
        wb.depth = n.depth;
        wb.waterY = n.waterY;                      // ⚠ 指図の値。⛔ median(shore)−0.3 の自動値を使わない
        wb.verticalWalls = false; wb.raiseBanks = false; wb.levelFloor = false;
        // ⚠ **材質とメッシュは決まったパスを使い回す。**`GenerateUniqueAssetPath` で作ると
        //   Stage を流し直すたびに `P_DoiOkuniwa 1.mat` … と孤児が溜まる(2026-09-06 に 8個作った)。
        const string MAT = "Assets/Edo/Water/P_DoiOkuniwa.mat";
        const string MSH = "Assets/Edo/Water/P_DoiOkuniwa_mesh.asset";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(MAT);
        if (mat == null)
        {
            var shader = Shader.Find("Edo/Water");
            if (shader != null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, MAT); }
        }
        // ⭐ 見え方(色の深さ・岸なじみ・泡)は**深さからの従属値**。⛔ 材質に置いた既定を信じない —
        //   シェーダの既定 4.0 / 1.5 / 0.4 は深さ 3〜4m の溜池向けで、深さ 1.0m の当家の池に
        //   当てると全面が白茶け、汀の全周に白い縁が回る(EDO-0316)。
        if (mat != null)
        {
            WaterBaker.ApplyLook(mat, wb.depth);
            EditorUtility.SetDirty(mat);
            go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        }
        var msh = AssetDatabase.LoadAssetAtPath<Mesh>(MSH);
        if (msh != null) go.GetComponent<MeshFilter>().sharedMesh = msh;   // 既存を上書き更新させる
        WaterBaker.RebuildSurface(wb);
        Wait("池の水面は `WaterBody` を自前で組んで `RebuildSurface` だけを呼んだ。"
           + "⚠ 指図 `impl.waterBaker` の `WaterBaker.Create` は**内部で Recarve を呼び、"
           + "snap 矩形 312×320m 全域に4パスの平滑化をかけて書き戻す**ので採れない"
           + "(指図 `impl.noRecarve` の趣旨と矛盾する)→ 指図方へ差し戻し");
        return r + " / 水面 " + n.pond.Length + "点 水位 " + n.waterY.ToString("F2");
    }

    // ==================================================================== 案A 6b〜6f(庭方の据え付けの設計 2026-10-04 を読む・EDO-0533)
    // ⛔ ここは欄を読んで EdoBuild の関数(EdoBuildNiwa.cs「指図の庭」の節)を呼ぶだけ。置き方・据え方を書かない(規則21)。
    // 欄の意味は指図 top-level `gardenFields`(hExpose・faceTo・seatToBed・inset・skip・stones)。
    // 硬い/柔らかい: 水中の石の底(seatToBed)・浮き・区画の線は**硬い**(EdoBuild が沈めて直すか、建てずに控えへ積む)。
    //   護岸の天端(cap)・乱杭の頭(topAbove)・閾の天端(sill)は**柔らかい**狙い(硬い条件で沈めたら ⚠ と不足を刷る)。

    /// <summary>石の据えの勘定(柔らかい狙いの不足・硬い条件で沈めた数)。邸ビルダーの刷りにだけ使う。</summary>
    class IshiTally
    {
        public int n, wetSunk, shortN, neireOver, sunkUnder; public float worstShort, worstWet, minExpose = float.NaN;
        public void Add(EdoBuild.NiwaIshiRep r)
        {
            n++;
            if (r.wetSink < -0.005f) { wetSunk++; worstWet = Mathf.Min(worstWet, r.wetSink); }
            if (!float.IsNaN(r.topShort) && r.topShort > 0.005f) { shortN++; worstShort = Mathf.Max(worstShort, r.topShort); }
            if (r.neireOver) neireOver++;
            if (!float.IsNaN(r.expose)) { if (r.expose <= 0f) sunkUnder++; minExpose = float.IsNaN(minExpose) ? r.expose : Mathf.Min(minExpose, r.expose); }
        }
        public string Line()
        {
            var sb = new System.Text.StringBuilder();
            sb.Append(n + " 石");
            if (wetSunk > 0) sb.Append(" / 硬い(水中の足 ≤ 池床−" + EdoBuild.SEAT_TO_BED_LO.ToString("F2") + ")で沈めた " + wetSunk + "(最大 " + worstWet.ToString("F2") + "m)");
            if (shortN > 0) sb.Append(" / ⚠ 柔らかい狙いの天端に届かず " + shortN + "(最大 −" + worstShort.ToString("F2") + "m)");
            if (neireOver > 0) sb.Append(" / ⚠ 坂の根入れが " + EdoBuild.NiwaSet.STONE_NEIRE_MAX.ToString("F2") + "m を越えた " + neireOver);
            if (sunkUnder > 0) sb.Append(" / ⚠ 見え高 ≤ 0(水没・埋没)" + sunkUnder);
            if (!float.IsNaN(minExpose)) sb.Append(" / 見え高の最小 " + minExpose.ToString("F2") + "m");
            return sb.ToString();
        }
    }

    /// <summary>指図の庭を名で引く(`gardens[].name`)。無ければ null。</summary>
    static Dictionary<string, object> Garden(string name)
    {
        foreach (var o in A(D["gardens"])) { var q = O(o); if (q != null && Sk(q, "name") == name) return q; }
        return null;
    }
    static Vector2 UV(object o) { var p = A(o); return new Vector2(F(p[0]), F(p[1])); }
    static Vector2 WuV(Vector2 uv) { return Wu(uv.x, uv.y); }
    /// <summary>(u,v) の向き d を世界の向きへ(格子は回っている)。</summary>
    static Vector2 WDir(Vector2 uvFrom, Vector2 uvTo) { return WuV(uvTo) - WuV(uvFrom); }
    static float Rnd(System.Random r, float a, float b) { return a + (float)r.NextDouble() * (b - a); }
    static bool Pair(Dictionary<string, object> o, string k, out float a, out float b)
    {
        a = b = float.NaN;
        if (!Has(o, k)) return false;
        var l = A(o[k]);
        if (l == null) { a = b = F(o[k]); return true; }
        if (l.Count < 2) return false;
        a = F(l[0]); b = F(l[1]); return true;
    }

    /// <summary>**見えている汀**(水面メッシュの縁 = PondEdge)を汀の番号 frm→to へ辿る折れ線(グリッド座標)。
    /// ⭐ 庭方の第3条: 護岸・州浜・乱杭・水際に据える物は見えている水際に取り合わせる。⛔ 設計の汀の頂点を結んだ線では
    /// Chaikin の丸めの分だけ外れる。番号の点は PondEdge の最寄りの頂点へ寄せる。</summary>
    static List<Vector2> EdgeWalk(int frm, int to)
    {
        var E = PondEdge(); int m = E.Length;
        if (m < 2) return null;
        Func<Vector2, int> near = q => { int bi = 0; float bd = float.MaxValue; for (int i = 0; i < m; i++) { float d = (E[i] - q).sqrMagnitude; if (d < bd) { bd = d; bi = i; } } return bi; };
        int a = near(Sh(frm)), b = near(Sh(to));
        var res = new List<Vector2>();
        for (int k = 0, i = a; k <= m; k++, i = (i + 1) % m) { res.Add(E[i]); if (i == b) break; }
        return res;
    }
    /// <summary>中島の汀(`nakajima.pts`・1 始まり・巡回)を frm→to へ(指図 gogan[].walk = "nakajima")。
    /// ⚠ 中島の汀は掘り残しの輪郭で、PondEdge ではない。</summary>
    static List<Vector2> NakaWalk(int frm, int to)
    {
        var P = NiwaModel.Nakajima; if (P == null || P.Length < 2) return null;
        int m = P.Length; var res = new List<Vector2>();
        for (int k = 0, i = frm - 1; k <= m; k++, i = (i + 1) % m) { res.Add(P[(i % m + m) % m]); if (i == to - 1) break; }
        return res;
    }
    /// <summary>折れ線の点 p・接線 dir での**水の側**の単位法線(グリッド)。池の汀なら水面の内、中島なら島の外。</summary>
    static Vector2 WaterSide(Vector2 p, Vector2 dir, bool naka)
    {
        var nrm = new Vector2(dir.y, -dir.x);
        Vector2 q = p + nrm * 0.05f;
        bool wet = naka ? !EdoGeom.PIP(NiwaModel.Nakajima, q) : InWater(q.x, q.y);
        return wet ? nrm : -nrm;
    }
    /// <summary>`skip` / `skipUV` の抜き所(グリッドの点・半幅 m)。</summary>
    static List<Vector3> SkipPts(Dictionary<string, object> o)
    {
        var res = new List<Vector3>();
        if (Has(o, "skip")) foreach (var s0 in A(o["skip"])) { var s = O(s0); var p = SnapToWaterEdge(Sh((int)F(s["at"]))); res.Add(new Vector3(p.x, p.y, F(s["halfW"]))); }
        if (Has(o, "skipUV")) foreach (var s0 in A(o["skipUV"])) { var s = O(s0); var p = UV(s["uv"]); res.Add(new Vector3(p.x, p.y, F(s["halfW"]))); }
        return res;
    }
    static bool InSkip(List<Vector3> sk, Vector2 p)
    {
        foreach (var s in sk) if (Vector2.Distance(WuV(p), WuV(new Vector2(s.x, s.y))) <= s.z) return true;
        return false;
    }

    // ---- ②護岸(石組・玉石・荒磯・呑口・州浜の玉石・乱杭)
    public static string Niwa_B_Gogan()
    {
        var n = NiwaModel; if (n == null) return "護岸: 汀線を持つ庭が無い";
        var g = n.g; float ken = Grid.ken, wy = n.waterY, bs = EdoBuild.SEAT_TO_BED_LO;
        var grp = Group("Niwa/Gogan"); Clear(grp);
        var rnd = new System.Random(20261004);
        var tl = new IshiTally(); int skipped = 0, nomi = 0;
        var sb = new System.Text.StringBuilder();

        foreach (var o in A(g["gogan"]))
        {
            var gg = O(o); string nm = Sk(gg, "name");
            AuditKeys(gg, "護岸『" + nm + "』", "name", "walk", "frm", "to", "kata", "ishiPick", "lenMin", "lenMax",
                      "yakuMin", "yakuMax", "yakuEvery", "capMin", "capMax", "jag", "pitchRatio", "inset", "skip", "skipUV",
                      "tamaMix", "tamaAsset", "nomikuchi", "araiso", "cert", "why");
            bool naka = Has(gg, "walk") && Sk(gg, "walk") == "nakajima";
            var line = naka ? NakaWalk((int)F(gg["frm"]), (int)F(gg["to"])) : EdgeWalk((int)F(gg["frm"]), (int)F(gg["to"]));
            if (line == null || line.Count < 2) { Wait("護岸『" + nm + "』: 辿る汀が引けない(walk=" + (naka ? "nakajima" : "汀") + ")"); continue; }
            int[] pick = Has(gg, "ishiPick") ? ParseIshiPick(Sk(gg, "ishiPick")) : null;
            if (pick == null) { Wait("護岸『" + nm + "』: `ishiPick` が無いか読めない — ⛔ 既定の駒へ倒さない。指図方へ"); continue; }
            float inLo, inHi; if (!Pair(gg, "inset", out inLo, out inHi)) { Wait("護岸『" + nm + "』: `inset` が無い(⛔ 既定で寄せない)"); continue; }
            float lenMin = F(gg["lenMin"]), lenMax = F(gg["lenMax"]), ykMin = F(gg["yakuMin"]), ykMax = F(gg["yakuMax"]);
            int ykEvery = (int)F(gg["yakuEvery"]);
            float capMin = F(gg["capMin"]), capMax = F(gg["capMax"]), jag = F(gg["jag"]), pr = F(gg["pitchRatio"]);
            float tamaMix = Has(gg, "tamaMix") ? F(gg["tamaMix"]) : 0f;
            var tamaL = new List<float>();
            if (tamaMix > 0f)
            {
                var rg = ParenFloats(Has(gg, "tamaAsset") ? Sk(gg, "tamaAsset") : null);
                if (rg.Count >= 2) foreach (var L in EdoAssets.Own.NeishiLong) if (L >= rg[0] - 1e-4f && L <= rg[rg.Count - 1] + 1e-4f) tamaL.Add(L);
                if (tamaL.Count == 0) { Wait("護岸『" + nm + "』: `tamaAsset` の長さの帯が読めない — 玉石を混ぜずに地の石で据えた"); tamaMix = 0f; }
            }
            var sk = SkipPts(gg);
            float Lm = LineLen(line) * ken;
            int cnt = Mathf.Max(1, Mathf.RoundToInt(Lm / Mathf.Max(0.05f, (lenMin + lenMax) * 0.5f * pr)));
            for (int i = 0; i < cnt; i++)
            {
                Vector2 dir; Vector2 gp = LerpLine(line, (i + 0.5f) / cnt, out dir);
                bool yaku = ykEvery > 0 && i % ykEvery == 0;
                float axis = yaku ? Rnd(rnd, ykMin, ykMax) : Rnd(rnd, lenMin, lenMax);
                bool tama = !yaku && tamaMix > 0f && rnd.NextDouble() < tamaMix;
                int variant = pick[rnd.Next(pick.Length)];
                float off = Rnd(rnd, -jag, jag), ins = Rnd(rnd, inLo, inHi), cap = Rnd(rnd, capMin, capMax), yaw = Rnd(rnd, 0f, 360f);
                float tl0 = tama ? tamaL[rnd.Next(tamaL.Count)] : 0f;
                if (InSkip(sk, gp)) { skipped++; continue; }
                // 役石は Ishigumi(3)(塊石)── 庭方 2026-09-06 の裁定(地の石の駒だけを ishiPick に替えた)を引き継ぐ
                string path = yaku ? EdoAssets.Own.Ishigumi(3) : (tama ? EdoAssets.Own.Neishi(tl0) : EdoAssets.Own.Ishigumi(variant));
                if (!Exists(path)) { Wait("庭石の部材が無い: " + path); continue; }
                float sc = tama ? 1f : EdoBuild.NiwaScaleForLong(path, axis);   // 玉石は焼いた長さのまま(⛔ 縮めない)
                Vector2 gq = gp + WaterSide(gp, dir, naka) * ((ins + off) / ken);
                EdoBuild.NiwaIshiRep rep;
                var go = EdoBuild.NiwaIshiSueru(grp, nm + "_" + i + (yaku ? "_Yaku" : tama ? "_Tama" : ""), path, WuV(gq), yaw, sc,
                                                float.NaN, wy, bs, out rep, wy + cap);
                if (go != null) tl.Add(rep); else Wait("護岸『" + nm + "』の石 " + i + " が測れず据わらない(" + path + ")");
            }

            // 呑口(入江の奥の石樋の口)。+Z = 流れの下流 = 池の内(部材の docstring)
            if (Has(gg, "nomikuchi"))
            {
                var nk = O(gg["nomikuchi"]);
                AuditKeys(nk, "呑口(護岸『" + nm + "』)", "at", "asset", "mouthY", "faceTo");
                string path = ResolveNiwaApi(Sk(nk, "asset"), 1);
                if (path == null || !Exists(path)) Wait("呑口の部材が引けない: " + Sk(nk, "asset"));
                else
                {
                    int at = (int)F(nk["at"]);
                    Vector2 p = SnapToWaterEdge(Sh(at));
                    Vector2 tg = SnapToWaterEdge(Sh(at + 1)) - SnapToWaterEdge(Sh(at - 1));
                    Vector2 inn = WaterSide(p, tg.normalized, false);
                    // ⚠ 口の芯の高さ(mouthY)は**札が無い**ので部材の docstring のピボット定義(樋の芯・吐き口の面)に拠る ── 札(PartSpec の mouth)が要る
                    var w = WuV(p);
                    var go = EdoBuild.Place(path, new Vector3(w.x, F(nk["mouthY"]), w.y), YawFace(WDir(p, p + inn)), Vector3.one, grp, nm + "_Nomikuchi");
                    if (go != null)
                    {
                        nomi++;
                        var rt = EdoBuild.RootToBed(go, EdoBuild.Ground, 0.05f);
                        if (!float.IsNaN(rt.hi) && rt.hi > 0.01f)
                            Wait("呑口(" + nm + ")の下端が地表から " + rt.hi.ToString("F2") + "m 浮く — 口の高さ mouthY は動かせないので据え土が要る(硬い・指図方/普請方へ)");
                        Wait("呑口の口の芯は札が無く部材のピボット定義で据えた — `PartSpecs/Doi_Mizushiri_Hakiguchi.json` に口(mouth)の当たりが要る(部材方へ)");
                    }
                }
            }

            // 荒磯の立石(配列)
            if (Has(gg, "araiso"))
                foreach (var a0 in A(gg["araiso"]))
                {
                    var ar = O(a0);
                    AuditKeys(ar, "荒磯(護岸『" + nm + "』)", "at", "asset", "hExpose", "buryRatio", "tilt", "tiltTo", "inset", "faceTo");
                    string path = Has(ar, "asset") ? ResolveNiwaApi(Sk(ar, "asset"), 1) : null;
                    if (path == null || !Exists(path)) { Wait("荒磯の立石の部材が引けない: " + (Has(ar, "asset") ? Sk(ar, "asset") : "(asset 無し)")); continue; }
                    if (!Has(ar, "hExpose") || !Has(ar, "buryRatio")) { Wait("荒磯(" + nm + " #" + F(ar["at"]) + "): hExpose/buryRatio が無い(⛔ 既定で埋めない)"); continue; }
                    float bury = F(ar["buryRatio"]), H = F(ar["hExpose"]) / Mathf.Max(0.05f, 1f - bury);
                    int at = (int)F(ar["at"]);
                    Vector2 p = SnapToWaterEdge(Sh(at));
                    Vector2 tg = (SnapToWaterEdge(Sh(at + 1)) - SnapToWaterEdge(Sh(at - 1))).normalized;
                    Vector2 inn = WaterSide(p, tg, false);
                    Vector2 q = p + inn * ((Has(ar, "inset") ? F(ar["inset"]) : 0f) / ken);
                    float yaw = Has(ar, "faceTo") ? EdoBuild.NiwaBroadFaceYaw(path, WuV(q), WuV(UV(ar["faceTo"]))) : Rnd(rnd, 0f, 360f);
                    float tilt = Has(ar, "tilt") ? F(ar["tilt"]) : 0f;
                    if (tilt != 0f && (!Has(ar, "tiltTo") || Sk(ar, "tiltTo") != "池側"))
                    { Wait("荒磯(" + nm + " #" + at + "): `tiltTo` が「池側」でない(" + Sk(ar, "tiltTo") + ")— 倒さずに据えた"); tilt = 0f; }
                    EdoBuild.NiwaIshiRep rep;
                    var go = EdoBuild.NiwaIshiSueru(grp, nm + "_Araiso_" + at, path, WuV(q), yaw, EdoBuild.NiwaScaleForHeight(path, H),
                                                    bury, wy, bs, out rep, float.NaN, false, WDir(q, q + inn), tilt);
                    if (go != null) tl.Add(rep); else Wait("荒磯(" + nm + " #" + at + ")が測れず据わらない");
                }
        }

        // 州浜の玉石(指図の [u,v,L] が一つずつの正)。⭐ 据えは Neishi の作り(丈 = 2 × 見え = bury 0.5・EdoAssets.Own.Neishi の注記と suhama.ishiNote)
        const float NEISHI_BURY = 0.5f;
        int su = 0;
        var suList = new List<KeyValuePair<string, Dictionary<string, object>>>();
        if (Has(g, "suhama")) foreach (var o in A(g["suhama"])) suList.Add(new KeyValuePair<string, Dictionary<string, object>>("suhama", O(o)));
        if (Has(g, "suhamaNaka")) suList.Add(new KeyValuePair<string, Dictionary<string, object>>("suhamaNaka", O(g["suhamaNaka"])));
        foreach (var kv in suList)
        {
            var sh = kv.Value; string nm = Sk(sh, "name");
            AuditKeys(sh, "州浜『" + nm + "』", "name", "walk", "frm", "to", "kata", "slope", "fromWater", "toLand", "bare", "layer", "asset", "ishi", "ishiNote", "cert");
            if (!Has(sh, "asset")) Wait("州浜『" + nm + "』に `asset` が無い — 玉石は gardenFields.ishiFamily の Own.Neishi(L) と読んだ(指図方へ: asset を明記)");
            if (Has(sh, "ishi"))
                foreach (var s0 in A(sh["ishi"]))
                {
                    var q = A(s0); float L = F(q[2]);
                    float best = float.NaN; foreach (var l in EdoAssets.Own.NeishiLong) if (Mathf.Abs(l - L) < 0.006f) best = l;
                    if (float.IsNaN(best)) { Wait("州浜『" + nm + "』の玉石 L" + L.ToString("F2") + " に当たる Neishi が焼いていない"); continue; }
                    string path = EdoAssets.Own.Neishi(best);
                    if (!Exists(path)) { Wait("玉石の部材が無い: " + path); continue; }
                    EdoBuild.NiwaIshiRep rep;
                    var go = EdoBuild.NiwaIshiSueru(grp, nm + "_" + su, path, Wu(F(q[0]), F(q[1])), Rnd(rnd, 0f, 360f), 1f, NEISHI_BURY, wy, bs, out rep);
                    if (go != null) { tl.Add(rep); su++; }
                }
            if (Has(sh, "layer"))
                Wait("州浜『" + nm + "』の地の仕上げ(" + Sk(sh, "layer") + (Has(sh, "bare") && sh["bare"] is bool && (bool)sh["bare"] ? "・そこの草を消す" : "")
                   + ")は**地表のスプラット**で部材では表せない — 地表仕上げの工程が要る");
        }

        // 乱杭。頭 = 水面 + topAbove(柔らかい)/ 足は池床 −0.10 より下(硬い)
        int ran = 0;
        if (Has(g, "rangui"))
            foreach (var o in A(g["rangui"]))
            {
                var rg = O(o); string nm = Sk(rg, "name");
                AuditKeys(rg, "乱杭『" + nm + "』", "name", "frm", "to", "pitch", "topAbove", "tilt", "skip", "asset", "cert", "why");
                float taLo, taHi; if (!Pair(rg, "topAbove", out taLo, out taHi)) { Wait("乱杭 " + nm + " に `topAbove` が無い"); continue; }
                var dias = ParenFloats(Has(rg, "asset") ? Sk(rg, "asset") : null);
                if (dias.Count == 0) { Wait("乱杭 " + nm + ": `asset` の径が読めない"); continue; }
                var line = EdgeWalk((int)F(rg["frm"]), (int)F(rg["to"]));
                if (line == null || line.Count < 2) { Wait("乱杭 " + nm + ": 汀が引けない"); continue; }
                var sk = SkipPts(rg);
                float tilt = Has(rg, "tilt") ? F(rg["tilt"]) : 0f, pitch = F(rg["pitch"]);
                int cnt = Mathf.Max(1, Mathf.RoundToInt(LineLen(line) * ken / Mathf.Max(0.02f, pitch)));
                // ⭐ 頭の高さは白色ノイズにしない(庭方 2026-09-06)── 低周波 2 波の重ね + 時々 1 本の外れ値
                float ph1 = Rnd(rnd, 0f, 6.2832f), ph2 = Rnd(rnd, 0f, 6.2832f);
                for (int i = 0; i < cnt; i++)
                {
                    Vector2 dir; Vector2 gp = LerpLine(line, (i + 0.5f) / cnt, out dir);
                    float dia = dias[rnd.Next(dias.Count)];
                    float t9 = 0.5f + 0.5f * (0.66f * Mathf.Sin(i * 6.2832f / 5.5f + ph1) + 0.34f * Mathf.Sin(i * 6.2832f / 13f + ph2));
                    if (rnd.NextDouble() < 0.09) t9 = (float)rnd.NextDouble();
                    float ax = Rnd(rnd, 0f, 360f) * Mathf.Deg2Rad, am = Rnd(rnd, 0f, tilt), yaw = Rnd(rnd, 0f, 360f);
                    if (InSkip(sk, gp)) { skipped++; continue; }
                    string path = EdoAssets.Own.Rangui(dia);
                    if (!Exists(path)) { Wait("乱杭の部材が無い: " + path); continue; }
                    EdoBuild.NiwaIshiRep rep;
                    var go = EdoBuild.NiwaIshiSueru(grp, nm + "_" + i, path, WuV(gp), yaw, 1f, float.NaN, wy, bs, out rep,
                                                    wy + Mathf.Lerp(taLo, taHi, Mathf.Clamp01(t9)), false,
                                                    new Vector2(Mathf.Cos(ax), Mathf.Sin(ax)), am);
                    if (go != null) { tl.Add(rep); ran++; }
                }
            }
        sb.Append("護岸・玉石・荒磯・州浜・乱杭: " + tl.Line() + " / うち州浜の玉石 " + su + "・乱杭 " + ran + " / 呑口 " + nomi + " / skip で抜いた " + skipped);
        return sb.ToString();
    }

    // ---- ③水尻(石の閾)。閾から先は drains D11(普請方・Stage の外)
    public static string Niwa_C_Mizushiri()
    {
        var n = NiwaModel; if (n == null) return "水尻: 汀線を持つ庭が無い";
        var g = n.g;
        if (!Has(g, "mizushiri") || O(g["mizushiri"]) == null) return "水尻: 指図に mizushiri が無い";
        var ms = O(g["mizushiri"]);
        AuditKeys(ms, "水尻", "shiki", "sokohi", "beyond");
        var grp = Group("Niwa/Mizushiri"); Clear(grp);
        var sb = new System.Text.StringBuilder("水尻: ");
        if (Has(ms, "shiki"))
        {
            var sk = O(ms["shiki"]);
            AuditKeys(sk, "水尻の閾", "at", "asset", "sill", "long", "cert", "why");
            string path = ResolveNiwaApi(Sk(sk, "asset"), 1);
            if (path == null || !Exists(path)) Wait("水尻の閾の部材が引けない: " + Sk(sk, "asset"));
            else
            {
                int at = (int)F(sk["at"]);
                Vector2 p = SnapToWaterEdge(Sh(at));
                Vector2 tg = WDir(SnapToWaterEdge(Sh(at - 1)), SnapToWaterEdge(Sh(at + 1)));
                var w = WuV(p);
                var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y), EdoBuild.NiwaLongAlongYaw(path, tg), Vector3.one, grp, "Shiki");
                if (go != null)
                {
                    EdoBuild.NiwaFootOn(go, w);
                    float sill = F(sk["sill"]);
                    EdoBuild.NiwaTopTo(go, sill);                                         // 柔らかい: 越流の天端 = 水位
                    int wn; float dy = EdoBuild.NiwaSinkWetFeet(go, n.waterY, EdoBuild.SEAT_TO_BED_LO, out wn);   // 硬い
                    sb.Append("閾1(天端 " + (sill + dy).ToString("F3") + (dy < -0.005f ? " ⚠ 硬い条件で " + dy.ToString("F2") + "m 沈めた ── 越流の天端が水位を割る" : "") + ") ");
                    if (dy < -0.005f) Wait("水尻の閾: 部材の丈では池床 −0.10 に届かず沈めた(天端 " + (sill + dy).ToString("F3") + " < sill " + sill.ToString("F2") + ")— 閾の丈が足りない(部材方へ)");
                }
            }
        }
        if (Has(ms, "sokohi")) sb.Append("/ 底樋は地中(焼かない)");
        if (Has(ms, "beyond")) sb.Append("/ 閾から先は " + Sk(ms, "beyond"));
        return sb.ToString();
    }

    // ---- ④景石・岩島・灯籠・腰掛・沓脱・飛石・手水(泉水と奥庭)
    public static string Niwa_D_Tenkei()
    {
        var n = NiwaModel; if (n == null) return "点景: 汀線を持つ庭が無い";
        var grp = Group("Niwa/Tenkei"); Clear(grp);
        var rnd = new System.Random(20261005);
        float wy = n.waterY, bs = EdoBuild.SEAT_TO_BED_LO;
        var tl = new IshiTally(); int toro = 0, kutsu = 0, tobi = 0, tobiSunk = 0;
        var fld = new EdoBuild.NiwaField(Poly);
        var gs = Garden("G_Sensui"); var go2 = Garden("G_Okuniwa");

        // 景石(泉水の枯滝の石組・奥庭の三石)。全丈 H = hExpose/(1−buryRatio)・実メッシュの丈で縮尺
        var ishiAll = new List<KeyValuePair<string, Dictionary<string, object>>>();
        if (gs != null && Has(gs, "ishigumi")) foreach (var o in A(gs["ishigumi"])) ishiAll.Add(new KeyValuePair<string, Dictionary<string, object>>("泉水", O(o)));
        if (go2 != null && Has(go2, "ishigumi") && Has(O(go2["ishigumi"]), "ishi"))
            foreach (var o in A(O(go2["ishigumi"])["ishi"])) ishiAll.Add(new KeyValuePair<string, Dictionary<string, object>>("奥庭", O(o)));
        foreach (var kv in ishiAll)
        {
            var ig = kv.Value; string nm = Has(ig, "name") ? Sk(ig, "name") : kv.Key + "_" + Sk(ig, "role");
            AuditKeys(ig, "景石『" + nm + "』", "name", "role", "u", "v", "asset", "hExpose", "buryRatio", "faceTo", "lean", "cert", "why");
            string path = ResolveNiwaApi(Sk(ig, "asset"), 1);
            if (path == null || !Exists(path)) { Wait("景石『" + nm + "』の部材が引けない: " + Sk(ig, "asset")); continue; }
            if (!Has(ig, "hExpose") || !Has(ig, "buryRatio")) { Wait("景石『" + nm + "』: hExpose/buryRatio が無い"); continue; }
            float bury = F(ig["buryRatio"]), H = F(ig["hExpose"]) / Mathf.Max(0.05f, 1f - bury);
            Vector2 uv = new Vector2(F(ig["u"]), F(ig["v"]));
            float yaw = Has(ig, "faceTo") ? EdoBuild.NiwaBroadFaceYaw(path, WuV(uv), WuV(UV(ig["faceTo"]))) : Rnd(rnd, 0f, 360f);
            if (Has(ig, "lean"))
                Wait("景石『" + nm + "』の `lean` " + F(ig["lean"]).ToString("F0") + "° は**倒す向きが無い**ので倒していない(⛔ 向きを発明しない)— `leanTo` を庭方へ");
            EdoBuild.NiwaIshiRep rep;
            var go = EdoBuild.NiwaIshiSueru(grp, nm, path, WuV(uv), yaw, EdoBuild.NiwaScaleForHeight(path, H), bury, wy, bs, out rep);
            if (go != null) tl.Add(rep); else Wait("景石『" + nm + "』が測れず据わらない");
        }

        // 岩島(全身が水中)。大石の丈 hMain・肩石の丈 hShoulder は全丈、底は池床 −seatToBed(硬い・sink は廃止)
        if (gs != null && Has(gs, "iwajima"))
            foreach (var o in A(gs["iwajima"]))
            {
                var iw = O(o); string nm = Sk(iw, "name");
                AuditKeys(iw, "岩島『" + nm + "』", "name", "u", "v", "asset", "hMain", "faceTo", "seatToBed", "assetShoulder", "shoulderUV", "hShoulder", "cert", "why");
                if (!Has(iw, "seatToBed")) { Wait("岩島『" + nm + "』に seatToBed が無い"); continue; }
                float sink = F(iw["seatToBed"]);
                for (int k = 0; k < 2; k++)
                {
                    string ak = k == 0 ? "asset" : "assetShoulder", hk = k == 0 ? "hMain" : "hShoulder";
                    if (!Has(iw, ak)) continue;
                    if (k == 1 && !Has(iw, "shoulderUV")) { Wait("岩島『" + nm + "』の肩石に shoulderUV が無い"); continue; }
                    string path = ResolveNiwaApi(S(iw[ak]), 1);
                    if (path == null || !Exists(path)) { Wait("岩島『" + nm + "』の部材が引けない: " + S(iw[ak])); continue; }
                    Vector2 uv = k == 0 ? new Vector2(F(iw["u"]), F(iw["v"])) : UV(iw["shoulderUV"]);
                    float yaw = (k == 0 && Has(iw, "faceTo")) ? EdoBuild.NiwaBroadFaceYaw(path, WuV(uv), WuV(UV(iw["faceTo"]))) : Rnd(rnd, 0f, 360f);
                    EdoBuild.NiwaIshiRep rep;
                    var go = EdoBuild.NiwaIshiSueru(grp, nm + (k == 0 ? "" : "_Kata"), path, WuV(uv), yaw, EdoBuild.NiwaScaleForHeight(path, F(iw[hk])),
                                                    float.NaN, wy, sink, out rep, float.NaN, true);
                    if (go == null) { Wait("岩島『" + nm + "』が池床を測れず据わらない"); continue; }
                    tl.Add(rep);
                    if (rep.expose <= 0.02f)
                        Wait("岩島『" + nm + (k == 0 ? "』の大石" : "』の肩石") + "が水面から " + rep.expose.ToString("F2") + "m しか出ない(全丈 " + F(iw[hk]).ToString("F2")
                           + "・底は池床 −" + sink.ToString("F2") + ")── `" + hk + "` を全丈と読んだ。水上の丈なら欄名を hExpose へ(庭方へ)");
                }
            }

        // 灯籠・腰掛・沓脱(泉水の tenkei)
        if (gs != null && Has(gs, "tenkei"))
            foreach (var o in A(gs["tenkei"]))
            {
                var tk = O(o); string nm = Sk(tk, "name"); string api = Sk(tk, "asset") ?? "";
                AuditKeys(tk, "点景『" + nm + "』", "name", "kata", "u", "v", "asset", "scale", "faceTo", "long", "topY", "mizukiri", "cert", "why");
                Vector2 uv = new Vector2(F(tk["u"]), F(tk["v"]));
                if (api.StartsWith("VK.Bench"))
                {
                    string bp = OptAsset("VK", "Bench");
                    Wait("腰掛『" + nm + "』: " + (bp == null ? "EdoAssets.VK.Bench が未登録 — 据えない(指図の注記: Village Kit の bench.prefab × vklib.S 0.909)"
                                                             : "VK.Bench はあるが据え方(座面の高さ・向き long=v)の当たりが未実装"));
                    continue;
                }
                if (api.Contains("Kutsunugi")) { kutsu += Kutsunugi(grp, tk, nm) ? 1 : 0; continue; }
                string path = ResolveNiwaApi(api, 1);
                if (path == null || !Exists(path)) { Wait("点景『" + nm + "』の部材が引けない: " + api); continue; }
                if (api.StartsWith("Eg.ToroKasuga"))
                    Wait("灯籠『" + nm + "』: 指図は春日型(Eg.ToroKasuga)だが EdoAssets の注記は「屋敷の庭の灯籠には使わない」── 指図(正典)どおり据えた・食い違いを指図方へ");
                float sc = (Has(tk, "scale") && tk["scale"] is string && Sk(tk, "scale").StartsWith("ES")) ? ES : (Has(tk, "scale") && !(tk["scale"] is string) ? F(tk["scale"]) : 1f);
                // ⚠ 灯籠の正面(火袋の窓)の軸は札に無い ── local +Z を正面と読んで faceTo へ向けた(部材方へ: 札に正面の軸を)
                float yaw = Has(tk, "faceTo") ? YawFace(WDir(uv, UV(tk["faceTo"]))) : Rnd(rnd, 0f, 360f);
                var o2 = EdoBuild.NiwaSet.Stone;
                var go = fld.Put(grp, path, WuV(uv), yaw, sc, Rnd(rnd, o2.SinkLo, o2.SinkHi), nm, "灯籠", o2);
                if (go != null) toro++; else Wait("灯籠『" + nm + "』を据えられない(区画の線・坂の根入れ・測れない のいずれか)");
            }
        if (toro > 0) Wait("灯籠の正面の軸は札に無く local +Z を正面と読んで faceTo へ向けた — 部材の札に正面の軸が要る(部材方へ)");

        // 沓脱(奥庭)
        if (go2 != null && Has(go2, "kutsunugi"))
            foreach (var o in A(go2["kutsunugi"])) { var kg = O(o); kutsu += Kutsunugi(grp, kg, Sk(kg, "name")) ? 1 : 0; }

        // 飛石(stones の列が正・tobiCommon の天端と駒)
        var tc = gs != null && Has(gs, "tobiCommon") ? O(gs["tobiCommon"]) : null;
        float taLo = float.NaN, taHi = float.NaN; var tVar = new List<int>();
        if (tc != null) { Pair(tc, "topAbove", out taLo, out taHi); tVar = ParenInts(Sk(tc, "asset")); }
        if (tc == null || float.IsNaN(taLo) || tVar.Count == 0) Wait("飛石の共通の欄 `tobiCommon`(topAbove・asset)が読めない — 飛石を据えない");
        else
        {
            var tobiAll = new List<KeyValuePair<string, Dictionary<string, object>>>();
            if (Has(gs, "tobiishi")) foreach (var o in A(gs["tobiishi"])) tobiAll.Add(new KeyValuePair<string, Dictionary<string, object>>("泉水", O(o)));
            if (go2 != null && Has(go2, "tobiishi"))
            {
                foreach (var o in A(go2["tobiishi"])) tobiAll.Add(new KeyValuePair<string, Dictionary<string, object>>("奥庭", O(o)));
                if (!Has(go2, "tobiCommon"))
                    Wait("奥庭に `tobiCommon` が無い — 泉水の tobiCommon(天端 +" + taLo.ToString("F2") + "〜" + taHi.ToString("F2") + "・駒)を借りた(指図方へ: 奥庭にも明記)");
            }
            foreach (var kv in tobiAll)
            {
                var tb = kv.Value; string nm = Sk(tb, "name");
                AuditKeys(tb, "飛石『" + nm + "』", "name", "line", "stones", "fumiwake", "cert", "why");
                var list = new List<Vector3>(); var paths = new List<string>();
                if (Has(tb, "stones")) foreach (var s0 in A(tb["stones"])) { var q = A(s0); list.Add(new Vector3(F(q[0]), F(q[1]), F(q[2]))); paths.Add(null); }
                else Wait("飛石『" + nm + "』に `stones` が無い(line は目安で据えない)");
                if (Has(tb, "fumiwake"))
                {
                    var fw = O(tb["fumiwake"]);
                    list.Add(new Vector3(F(fw["u"]), F(fw["v"]), F(fw["L"]))); paths.Add(ResolveTobi(Sk(fw, "asset")));
                }
                for (int i = 0; i < list.Count; i++)
                {
                    string path = paths[i] ?? EdoAssets.Own.Tobiishi(tVar[rnd.Next(tVar.Count)]);
                    float yaw = Rnd(rnd, 0f, 360f), above = Rnd(rnd, taLo, taHi);
                    if (path == null || !Exists(path)) { Wait("飛石の部材が無い: " + path); continue; }
                    var w = Wu(list[i].x, list[i].y);
                    var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y), yaw, Vector3.one * EdoBuild.NiwaScaleForLong(path, list[i].z), grp,
                                            nm + (paths[i] != null ? "_Fumiwake" : "_" + i));
                    if (go == null) continue;
                    EdoBuild.NiwaFootOn(go, w);
                    float fl; EdoBuild.NiwaTopAboveGround(go, above, out fl);
                    if (!float.IsNaN(fl) && fl > 0.01f) { go.transform.position -= new Vector3(0f, fl, 0f); tobiSunk++; }   // 硬い: 浮き 0(天端の高い側が地表に入る)
                    tobi++;
                }
            }
        }

        // 縁先手水鉢(奥庭)
        if (go2 != null && Has(go2, "chozu"))
        {
            var ch = O(go2["chozu"]);
            AuditKeys(ch, "手水", "kata", "u", "v", "rimY", "asset", "yaku", "cert", "why");
            string bp = OptAsset("Own", "DoiEnsakiChozubachi");
            Wait("縁先手水鉢: " + (bp == null ? "部材が無い(EdoAssets.Own.DoiEnsakiChozubachi 未登録)── 据えない" : "部材はあるが")
               + "・鉢の縁 rimY「" + Sk(ch, "rimY") + "」は長局の縁板の天端の実測が要る(EdoBuild に縁板の天端を測る関数が無い)");
            if (Has(ch, "yaku"))
                foreach (var y0 in A(ch["yaku"]))
                { var yk = O(y0); Wait("手水の役石『" + Sk(yk, "role") + "』: hExpose はあるが buryRatio が無い — 全丈を出せないので据えない(庭方へ)"); }
        }

        string tobiNote = tobiSunk > 0 ? "(うち浮きを消すため天端の高い側を地表へ入れた " + tobiSunk + ")" : "";
        return "点景: 景石・岩島 " + tl.Line() + " / 灯籠 " + toro + " / 沓脱 " + kutsu + " / 飛石 " + tobi + tobiNote
             + " / 据えなかった: 区画の線 " + fld.DropEdge + "・急斜面 " + fld.DropSteep + "・根入れ超 " + fld.DropNeire + "・測れない " + fld.Refused;
    }

    /// <summary>沓脱石一つ(数の topY・水切りの向き mizukiri.to)。topY が文字列(「縁板の天端 −0.40(測る)」)なら控えへ積む。</summary>
    static bool Kutsunugi(Transform grp, Dictionary<string, object> kg, string nm)
    {
        string api = Sk(kg, "asset");
        string path = ResolveNiwaApi(api, 1);
        if (path == null || !Exists(path)) { Wait("沓脱石『" + nm + "』の部材が引けない: " + api); return false; }
        if (!Has(kg, "topY") || kg["topY"] is string)
        {
            Wait("沓脱石『" + nm + "』: 天端「" + (Has(kg, "topY") ? Sk(kg, "topY") : "(無し)") + "」は縁板の天端の実測が要る — EdoBuild に縁板の天端を測る関数が無いので据えない");
            return false;
        }
        var f9 = Grid;
        string mto = Has(kg, "mizukiri") && Has(O(kg["mizukiri"]), "to") ? S(O(kg["mizukiri"])["to"]) : null;
        Vector2 zdir;
        if (mto != null && mto.StartsWith("-u")) zdir = new Vector2(-f9.ux, -f9.uz);
        else if (mto != null && mto.StartsWith("+u")) zdir = new Vector2(f9.ux, f9.uz);
        else if (mto != null && mto.StartsWith("-v")) zdir = new Vector2(-f9.vx, -f9.vz);
        else if (mto != null && mto.StartsWith("+v")) zdir = new Vector2(f9.vx, f9.vz);
        else { Wait("沓脱石『" + nm + "』の `mizukiri.to` が読めない — ⛔ 既定へ倒すと水切りが縁の下へ向くので据えない"); return false; }
        float sc = Has(kg, "scale") ? F(kg["scale"]) : 1f;
        var w = Wu(F(kg["u"]), F(kg["v"]));
        // ⭕ 水切りはローカル +Z へ 1/100(部材の docstring)── +Z を mizukiri.to へ
        var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y), YawFace(zdir), Vector3.one * sc, grp, nm);
        if (go == null) return false;
        EdoBuild.NiwaFootOn(go, w);
        EdoBuild.NiwaTopTo(go, F(kg["topY"]));
        var rt = EdoBuild.RootToBed(go, EdoBuild.Ground, 0.05f);
        if (!float.IsNaN(rt.hi) && rt.hi > 0.01f)
        {
            // 硬い: 浮きは許容0。天端は指図の値なので下げられない ── 建てずに控えへ
            Wait("沓脱石『" + nm + "』: 天端 " + F(kg["topY"]).ToString("F2") + " では下端が地表から " + rt.hi.ToString("F2") + "m 浮く — 据えない(硬い・天端か地盤を指図方へ)");
            UnityEngine.Object.DestroyImmediate(go);
            return false;
        }
        if (Has(kg, "nekatame")) Wait("沓脱石の根固めは地表側の表現 — 地表仕上げの工程が要る");
        return true;
    }

    // ---- ⑤園路・橋・段・延段
    static string Niwa_E_Enro()
    {
        var n = NiwaModel; if (n == null) return "園路: 汀線を持つ庭が無い";
        var grp = Group("Niwa/Enro"); Clear(grp);
        var gs = Garden("G_Sensui"); var go2 = Garden("G_Okuniwa");
        int hashi = 0;
        if (gs != null && Has(gs, "enroShu"))
            Wait("園路の主路(" + S(O(gs["enroShu"])["layer"]) + "・幅 " + F(O(gs["enroShu"])["w"]).ToString("F1") + "m)は**地表のスプラット**で部材では表せない — 地表仕上げの工程が要る(小端の縁は置かない P)");
        if (gs != null && Has(gs, "hashi"))
            foreach (var o in A(gs["hashi"]))
            {
                var h = O(o); string nm = Sk(h, "name");
                AuditKeys(h, "橋『" + nm + "』", "name", "kata", "a", "b", "spanM", "L", "W", "T", "sori", "topY", "endTopY", "asset", "abut", "hasami", "cert", "why");
                bool ishi = nm == "Hashi_Ishi" || (Sk(h, "kata") ?? "").StartsWith("石橋");
                string member = ishi ? "DoiIshibashi" : "DoiDobashi";
                string path = OptAsset("Own", member);
                if (path == null || !Exists(path))
                    Wait("橋『" + nm + "』(" + Sk(h, "kata") + " L" + F(h["L"]).ToString("F1") + "×W" + F(h["W"]).ToString("F2") + ")の部材が無い — EdoAssets.Own." + member + " が未登録・据えない");
                else
                {
                    bool ends = Has(h, "endTopY");
                    float topY = ends ? F(h["endTopY"]) : F(h["topY"]);
                    Vector2 a = UV(h["a"]), b = UV(h["b"]);
                    var go = EdoBuild.Place(path, new Vector3(WuV(a).x, topY, WuV(a).y), 0f, Vector3.one, grp, nm);
                    float gap; float bear = EdoBuild.NiwaSpanBridge(go, path, WuV(a), WuV(b), topY, ends, out gap);
                    if (float.IsNaN(bear) || bear < 0f)
                    { Wait("橋『" + nm + "』: 部材の長さが径間に足りない(掛かり " + bear.ToString("F2") + "m)— 据えない(硬い)"); UnityEngine.Object.DestroyImmediate(go); }
                    else if (!float.IsNaN(gap) && gap > 0.01f)
                    { Wait("橋『" + nm + "』: 掛かりの下端が地表から " + gap.ToString("F2") + "m 浮く(指図 abut: 版の下面は橋台石の天端に接する・硬い)— 据えない。袂の地盤か topY を指図方へ"); UnityEngine.Object.DestroyImmediate(go); }
                    else hashi++;
                }
                if (Has(h, "hasami"))
                    foreach (var s0 in A(h["hasami"]))
                    { var hs = O(s0); Wait("橋挟み石(" + nm + " u" + F(hs["u"]).ToString("F2") + ",v" + F(hs["v"]).ToString("F2") + "): hExpose はあるが buryRatio が無い — 全丈を出せないので据えない(庭方へ)"); }
            }
        if (gs != null && Has(gs, "dan"))
        {
            string dp = OptAsset("Own", "DoiMarutaDan");
            Wait("丸太の土留め段: " + (dp == null ? "部材が無い(EdoAssets.Own.DoiMarutaDan 未登録)" : "部材はあるが主路の勾配から段を割り付ける関数が未実装") + " — 据えない(蹴上 0.12〜0.15・主路の 1:6 超の区間)");
        }
        if (go2 != null && Has(go2, "nobedan"))
        {
            var nb = O(go2["nobedan"]);
            string np = OptAsset("Own", "DoiNobedan");
            Wait("延段(奥庭 w" + F(nb["w"]).ToString("F1") + "): " + (np == null ? "部材が無い(EdoAssets.Own.DoiNobedan 未登録)" : "部材はあるが天端の欄が無い") + " — 据えない");
        }
        return "園路: 橋 " + hashi + "(主路・段・延段は控え)";
    }

    // ---- ⑥稲荷(祠は Stage5 の `service.Inari`。ここは鳥居・参道・手水 ── 庭の欄 yashiro があれば)
    static string Niwa_F_Yashiro()
    {
        Dictionary<string, object> gy = null;
        foreach (var o in A(D["gardens"])) { var q = O(o); if (q != null && Has(q, "yashiro")) { gy = q; break; } }
        if (gy == null) return "稲荷: 庭の欄に yashiro が無い(祠は Stage5 の service.Inari)── 据える物なし";
        var ys = O(gy["yashiro"]);
        var grp = Group("Niwa/Yashiro"); Clear(grp);
        var fld = new EdoBuild.NiwaField(Poly);
        int made = 0;
        if (Has(ys, "torii"))
        {
            var tr = O(ys["torii"]);
            string path = ResolveNiwaApi(Sk(tr, "asset"), 1);
            if (path == null || !Exists(path)) Wait("鳥居の部材が無い: " + Sk(tr, "asset"));
            else
            {
                Vector2 uv = new Vector2(F(tr["u"]), F(tr["v"]));
                var go = fld.Put(grp, path, WuV(uv), YawFace(WDir(uv, uv + Vector2.right)), 1f, 0.05f, "Torii", "鳥居", EdoBuild.NiwaSet.Stone);
                if (go != null) made++; else Wait("鳥居を据えられない");
            }
        }
        if (Has(ys, "chozu"))
        {
            var ch = O(ys["chozu"]);
            string path = EdoAssets.Own.DoiChozu;
            if (!Exists(path)) Wait("手水石の部材が無い: " + path);
            else
            {
                Vector2 uv = new Vector2(F(ch["u"]), F(ch["v"]));
                var go = fld.Put(grp, path, WuV(uv), EdoBuild.NiwaLongAlongYaw(path, WDir(uv, uv + Vector2.right)), 1f, 0.06f, "Chozu", "手水", EdoBuild.NiwaSet.Stone);
                if (go != null) made++; else Wait("手水石を据えられない");
            }
        }
        if (Has(ys, "sando")) Wait("稲荷の参道(玉砂利敷き)— 地表のスプラットで部材では表せない");
        return "稲荷: 鳥居・手水 " + made + " 基(祠は Stage5 の service.Inari)";
    }
    // ---- ⑦垣
    static string Niwa_G_Kaki()
    {
        if (KyuanStop) return AnANotYet("6g 垣");
        var n = NiwaModel;
        var grp = Group("Niwa/Kaki"); Clear(grp);
        int made = 0;
        foreach (var o in A(n.g["kaki"]))
        {
            var kk = O(o);
            string kata = Sk(kk, "kata");
            float h = F(kk["h"]);
            bool kenninji = kata != null && kata.StartsWith("建仁寺");
            string span = kenninji ? EdoAssets.Own.KenninjiGaki(h) : EdoAssets.Own.YotsumeGaki(h);
            string post = kenninji ? EdoAssets.Own.KenninjiGakiPost(h) : EdoAssets.Own.YotsumeGakiPost(h);
            if (!Exists(span))
            {
                Wait("垣 " + Sk(kk, "name") + "(" + kata + " h" + h.ToString("F1") + ")の部材が無い: " + span
                   + " → blender --background --python Tools/Blender/build_okabe_niwa.py -- "
                   + (kenninji ? "kenninji" : "yotsume")
                   + "(⛔ 焼いていない丈へ寄せない — 胴縁の段数が丈で変わる)");
                continue;
            }
            // 走り: `pts`(閉じない・`openSide` の面は開ける)か、u0..u1 の直線(v 固定)
            var lines = new List<Vector2[]>();
            if (Has(kk, "pts"))
            {
                var pts = A(kk["pts"]);
                var P = new List<Vector2>();
                foreach (var q in pts) { var p = A(q); P.Add(new Vector2(F(p[0]), F(p[1]))); }
                string open = Sk(kk, "openSide");
                for (int i = 0; i < P.Count; i++)
                {
                    Vector2 a = P[i], b = P[(i + 1) % P.Count];
                    // openSide "-u" = u が最小の辺(= u=const で低い側)を開ける
                    if (open == "-u" && Mathf.Abs(a.x - b.x) < 1e-6f
                        && Mathf.Abs(a.x - Mathf.Min(P[0].x, P[2].x)) < 1e-6f) continue;
                    lines.Add(new Vector2[] { a, b });
                }
            }
            else if (Has(kk, "u0") && Has(kk, "v"))
                lines.Add(new Vector2[] { new Vector2(F(kk["u0"]), F(kk["v"])), new Vector2(F(kk["u1"]), F(kk["v"])) });
            else { Wait("垣 " + Sk(kk, "name") + ": 走りが読めない"); continue; }

            // ⭕ 1スパン = 1間ちょうど。端数は **端の駒を run の端に合わせて内側で重ねて吸う**
            //   (⛔ 等ピッチで中央寄せにすると端の駒が run の外へ出る)。`LayGaki` が正典。
            int idx = 0;
            foreach (var seg in lines)
            {
                Vector2 A0 = Wu(seg[0].x, seg[0].y), B0 = Wu(seg[1].x, seg[1].y);
                int nmade = LayGaki(grp, Sk(kk, "name"), span, post, A0, B0, idx);
                idx += nmade; made += nmade;
            }
        }
        return "垣: " + made + " 枚";
    }

    /// <summary>**実地形の高さ**(heightmap から。地形が無ければ NaN)。
    /// ⚠⚠ **草・点景はこれで据える。**`GroundY` は**設計の解析面**で、heightmap の 2m 格子は
    /// 築山の曲率を持てない — 解析面で据えると株が宙に浮く(2026-09-06 普請検査: 下草 61株のうち
    /// 19株が浮き、最大 +1.413m)。⛔ 「設計どおりの高さ」を地面に生える物へ渡さない。
    /// ⭕ 逆に**建物・石垣・塀**は設計面(`GroundY`)で据えてよい — 基壇が地形の凹凸を吸収するため。</summary>
    static float TerrY(float x, float z)
    {
        var t = Terrain.activeTerrain;
        if (t == null) return float.NaN;
        return t.SampleHeight(new Vector3(x, 0f, z)) + t.transform.position.y;
    }

    // ---- ⑧植栽・刈込・刈込玉・下草・水際の草(泉水と奥庭)
    // ⭐ 据えは全部 EdoBuild.NiwaField.Put(接地箇所で据え・坂の根入れ・幹の芯 ↔ 区画の線 2.0m の硬い条件)。
    //    傾け(lean)は EdoBuild.NiwaLeanTree、刈込の多角形は EdoBuild.NiwaFillPoly。丈は実メッシュで測って縮尺(NiwaScaleForHeight)。
    /// <summary>株の大きさ(Big/Mid/Small)── 欄 sizeEach[i] → size → 部材の呼び名の引数("Small" 等)の順に読む。どれも無ければ null(高木に倒さない)。</summary>
    static string PlantSize(Dictionary<string, object> sk, string api, int i)
    {
        if (Has(sk, "sizeEach")) { var se = A(sk["sizeEach"]); if (se != null && i < se.Count) return S(se[i]); }
        if (Has(sk, "size")) return Sk(sk, "size");
        foreach (var k in new[] { "Big", "Mid", "Small" }) if ((api ?? "").Contains("\"" + k + "\"")) return k;
        return null;
    }

    public static string Niwa_H_Shokusai()
    {
        var n = NiwaModel; if (n == null) return "植栽: 汀線を持つ庭が無い";
        var grp = Group("Niwa/Shokusai"); Clear(grp);
        var kgrp = Group("Niwa/Karikomi"); Clear(kgrp);
        var sgrp = Group("Niwa/Shitakusa"); Clear(sgrp);
        var rnd = new System.Random(20261008);
        var fld = new EdoBuild.NiwaField(Poly);
        var gs = Garden("G_Sensui"); var go2 = Garden("G_Okuniwa");
        int trees = 0, shrubs = 0, kari = 0, shida = 0, mizu = 0, leanDeep = 0;

        // ── 高木・中木・刈込玉(泉水 shokusai[] の at[])
        if (gs != null && Has(gs, "shokusai"))
            foreach (var o in A(gs["shokusai"]))
            {
                var sk = O(o); string nm = Sk(sk, "name"); string api = Sk(sk, "asset") ?? "";
                AuditKeys(sk, "植栽『" + nm + "』", "name", "species", "size", "asset", "scale", "at", "lean", "sizeEach", "hEach", "cert", "why");
                var at = Has(sk, "at") ? A(sk["at"]) : null; if (at == null) continue;
                bool tsuge = api.StartsWith("JG.Boxwood");
                for (int i = 0; i < at.Count; i++)
                {
                    Vector2 uv = UV(at[i]);
                    string path = PlantPath(sk, api, i);
                    if (path == null || !Exists(path)) { Wait("植栽『" + nm + "』の部材が引けない: " + api + " #" + i); continue; }
                    float sc = Has(sk, "scale") ? F(sk["scale"]) : 1f;
                    if (Has(sk, "hEach")) { var he = A(sk["hEach"]); if (i < he.Count) sc = EdoBuild.NiwaScaleForHeight(path, F(he[i])); }
                    var set = tsuge ? EdoBuild.NiwaSet.Shrub : (PlantSize(sk, api, i) == "Big" ? EdoBuild.NiwaSet.Tree : EdoBuild.NiwaSet.Chuboku);
                    var go = fld.Put(grp, path, WuV(uv), Rnd(rnd, 0f, 360f), sc, Rnd(rnd, set.SinkLo, set.SinkHi), nm + "_" + i,
                                     tsuge ? "刈込玉" : (set.Tall ? "高木" : "中木"), set);
                    if (go == null) { Wait("植栽『" + nm + "』#" + i + " を据えられない(区画の線から幹 2.0m・坂・測れない のいずれか ── 硬い)"); continue; }
                    if (tsuge) shrubs++; else trees++;
                    if (Has(sk, "lean"))
                    {
                        var ln = O(sk["lean"]); float deep;
                        EdoBuild.NiwaLeanTree(go, WDir(uv, UV(ln["to"])), F(ln["deg"]), out deep);
                        if (deep > EdoBuild.NiwaSet.TREE_BURY_MAX) leanDeep++;
                    }
                }
            }

        // ── 奥庭の中木(shokusai[] の uvMeyasu。shokusaiFix が名で上書き)。⚠ 大刈込・刈込玉・生垣・下草の行は karikomi/tsuge/ikegaki の欄が正
        if (go2 != null && Has(go2, "shokusai"))
        {
            var fix = new Dictionary<string, Vector2>();
            if (Has(go2, "shokusaiFix")) foreach (var f0 in A(go2["shokusaiFix"])) { var f = O(f0); fix[Sk(f, "name")] = UV(f["at"]); }
            foreach (var o in A(go2["shokusai"]))
            {
                var sk = O(o);
                if (!Has(sk, "uvMeyasu")) continue;
                string part = Sk(sk, "part") ?? "";
                Vector2 uv = UV(sk["uvMeyasu"]);
                foreach (var kv in fix) if (part.Contains("." + kv.Key + "(")) uv = kv.Value;
                var vi = ParenInts(part);
                string path = ResolveNiwaApi(part, vi.Count > 0 ? vi[0] : 1);
                if (path == null || !Exists(path)) { Wait("奥庭の植栽『" + Sk(sk, "species") + "』の部材が引けない: " + part); continue; }
                float sc = Has(sk, "h") && !(sk["h"] is List<object>) ? EdoBuild.NiwaScaleForHeight(path, F(sk["h"])) : 1f;
                var set = EdoBuild.NiwaSet.Chuboku;
                var go = fld.Put(grp, path, WuV(uv), Rnd(rnd, 0f, 360f), sc, Rnd(rnd, set.SinkLo, set.SinkHi), "Oku_" + Sk(sk, "species"), "中木", set);
                if (go != null) trees++; else Wait("奥庭の植栽『" + Sk(sk, "species") + "』を据えられない(硬い条件)");
            }
            Wait("奥庭の中木の位置は `uvMeyasu`(目安)を据え位置と読んだ(shokusaiFix の Ume だけ at)── 目安でなく据え位置なら欄名を at へ(指図方へ)");
        }

        // ── 刈込(kata=多角形: 内を株間 = 部材の実寸 × 0.8 で埋め・株は奇数・指図 karikomiCommon)
        var karis = new List<Dictionary<string, object>>();
        if (gs != null && Has(gs, "karikomi")) foreach (var o in A(gs["karikomi"])) karis.Add(O(o));
        if (go2 != null && Has(go2, "karikomi")) foreach (var o in A(go2["karikomi"])) karis.Add(O(o));
        foreach (var kk in karis)
        {
            string nm = Sk(kk, "name");
            AuditKeys(kk, "刈込『" + nm + "』", "name", "kata", "pts", "hMin", "hMax", "asset", "cert", "why");
            if (Sk(kk, "kata") != "多角形" || !Has(kk, "pts")) { Wait("刈込『" + nm + "』: kata「" + Sk(kk, "kata") + "」は読めない(多角形だけ)"); continue; }
            var vi = ParenInts(Sk(kk, "asset"));
            var paths = new List<string>(); float plan = 0f;
            foreach (var v in vi)
            {
                string p = ResolveNiwaApi(Sk(kk, "asset"), v);
                if (p == null || !Exists(p)) continue;
                paths.Add(p); plan = Mathf.Max(plan, EdoBuild.CrownR(p) * 2f);
            }
            if (paths.Count == 0 || plan <= 0.01f) { Wait("刈込『" + nm + "』の部材が引けない: " + Sk(kk, "asset")); continue; }
            var pl = A(kk["pts"]); var polyW = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) polyW[i] = WuV(UV(pl[i]));
            float hMin = F(kk["hMin"]), hMax = F(kk["hMax"]);
            int made = 0;
            foreach (var q in EdoBuild.NiwaFillPoly(polyW, plan * 0.8f, rnd))
            {
                var g = Grid.L(q);
                string path = paths[rnd.Next(paths.Count)]; float h = Rnd(rnd, hMin, hMax), yaw = Rnd(rnd, 0f, 360f);
                if (n.InPond(g.x, g.y)) continue;                                  // ⛔ 水に落ちる株は据えない(硬い)
                var set = EdoBuild.NiwaSet.Shrub;
                var go = fld.Put(kgrp, path, q, yaw, EdoBuild.NiwaScaleForHeight(path, h), Rnd(rnd, set.SinkLo, set.SinkHi), nm + "_" + made, "刈込", set);
                if (go != null) { made++; kari++; }
            }
            if (made % 2 == 0 && made > 0) Wait("刈込『" + nm + "』: 硬い条件で株が落ちて偶数(" + made + ")になった(株は奇数で止める)");
        }
        if (karis.Count > 0) Wait("刈込の「表面を一つの雲形に刈る」は株の並べでは表せない — 株の寄せまで(部材方へ: 雲形の刈込の部材)");

        // ── 刈込玉(奥庭 tsuge)
        if (go2 != null && Has(go2, "tsuge"))
        {
            var ts = O(go2["tsuge"]);
            AuditKeys(ts, "刈込玉(奥庭)", "asset", "at", "hEach");
            var vi = ParenInts(Sk(ts, "asset")); var at = A(ts["at"]); var he = Has(ts, "hEach") ? A(ts["hEach"]) : null;
            for (int i = 0; at != null && i < at.Count; i++)
            {
                string path = ResolveNiwaApi(Sk(ts, "asset"), vi.Count > 0 ? vi[i % vi.Count] : 1);
                if (path == null || !Exists(path)) { Wait("刈込玉の部材が引けない: " + Sk(ts, "asset")); break; }
                if (he == null || i >= he.Count) { Wait("刈込玉(奥庭)#" + i + " に丈 hEach が無い"); continue; }
                var set = EdoBuild.NiwaSet.Shrub;
                var go = fld.Put(kgrp, path, WuV(UV(at[i])), Rnd(rnd, 0f, 360f), EdoBuild.NiwaScaleForHeight(path, F(he[i])), Rnd(rnd, set.SinkLo, set.SinkHi), "Oku_Tsuge_" + i, "刈込玉", set);
                if (go != null) shrubs++;
            }
        }

        // ── 生垣(奥庭 ikegaki)── 芯は「奥の塀の内面から 0.5間」= 塀の実メッシュを測る相手が要る
        if (go2 != null && Has(go2, "ikegaki"))
            Wait("奥庭の生垣: 芯「" + S(O(go2["ikegaki"])["line"]) + "」は奥の塀の内面の実測が要る — 塀の駒を名指す欄(fences の名)が無く、EdoBuild にも塀の内面から芯を引く関数が無いので据えない");

        // ── 下草(シダ)。散布域は shitakusa.shida.where の幾何(築山の面 = 案Aの裾の多角形 tsukiyama[].skirt の side 側・clipV で抜く)
        var skRep = new System.Text.StringBuilder();
        var stk = gs != null && Has(gs, "shitakusa") ? O(gs["shitakusa"]) : null;
        var shd = stk != null && Has(stk, "shida") ? O(stk["shida"]) : null;
        if (shd != null)
        {
            AuditKeys(shd, "下草(シダ)", "where", "asset", "yawRandom", "scaleJitter", "pitchMin", "note", "cert");
            bool yawRnd = !Has(shd, "yawRandom") || F(shd["yawRandom"]) != 0f;
            float scLo = 1f, scHi = 1f; Pair(shd, "scaleJitter", out scLo, out scHi);
            if (float.IsNaN(scLo)) { scLo = scHi = 1f; }
            float pitchMin = Has(shd, "pitchMin") ? F(shd["pitchMin"]) : 0f;
            var fv = ParenInts(Sk(shd, "asset"));
            var fp = new List<string>(); float fw = 0f;
            foreach (var v in fv) { string p = EdoAssets.JG.Fern(v); if (Exists(p)) { fp.Add(p); fw = Mathf.Max(fw, EdoBuild.CrownR(p) * 2f); } }
            if (fp.Count == 0) Wait("シダの部材が引けない: " + Sk(shd, "asset"));
            else
            {
                float pitchM = Mathf.Max(fw, pitchMin), step = pitchM / Grid.ken;
                var bands = SuhamaBands();
                var kusa = EdoBuild.NiwaSet.Kusa;
                foreach (var r in ShitakusaRegions())
                {
                    if (r.err != null) { Wait("下草 " + r.name + ": " + r.err); continue; }
                    float u0 = float.MaxValue, u1 = float.MinValue, v0 = float.MaxValue, v1 = float.MinValue;
                    if (r.poly != null) foreach (var p in r.poly) { u0 = Mathf.Min(u0, p.x); u1 = Mathf.Max(u1, p.x); v0 = Mathf.Min(v0, p.y); v1 = Mathf.Max(v1, p.y); }
                    foreach (var c in r.circ) { u0 = Mathf.Min(u0, c.x - c.z); u1 = Mathf.Max(u1, c.x + c.z); v0 = Mathf.Min(v0, c.y - c.z); v1 = Mathf.Max(v1, c.y + c.z); }
                    int k9 = 0;
                    for (float u = u0; u <= u1 + 1e-9f; u += step)
                        for (float v = v0; v <= v1 + 1e-9f; v += step)
                        {
                            Vector2 q = new Vector2(u + Rnd(rnd, -0.25f, 0.25f) * step, v + Rnd(rnd, -0.25f, 0.25f) * step);
                            float yaw = yawRnd ? Rnd(rnd, 0f, 360f) : 0f, sc = Rnd(rnd, scLo, scHi);
                            string path = fp[rnd.Next(fp.Count)];
                            if (!SkIn(r, q.x, q.y) || !n.Inside(q.x, q.y) && !InGardenPoly(q)) continue;
                            if (r.clipV0 <= q.y && q.y <= r.clipV1) continue;          // 枯滝の前を抜く(clipV)
                            if (n.InPond(q.x, q.y) || SkInBand(bands, q)) continue;    // ⛔ 水面・州浜の砂利帯
                            var go = fld.Put(sgrp, path, WuV(q), yaw, sc, Rnd(rnd, kusa.SinkLo, kusa.SinkHi), r.name + "_" + k9, "下草", kusa);
                            if (go != null) { k9++; shida++; }
                        }
                    skRep.Append("\n   " + r.name + "(" + r.kata + "): " + k9 + " 株");
                }
                Wait("下草の株間は部材の実寸(" + pitchM.ToString("F2") + "m・pitchMin 以上)── 密度の欄は指図に無い【U】");
            }
        }

        // ── 水際の草(shitakusa.mizugiwa: 名指しした護岸・乱杭の汀に沿う帯)
        var mzg = stk != null && Has(stk, "mizugiwa") ? O(stk["mizugiwa"]) : null;
        if (mzg != null)
        {
            AuditKeys(mzg, "水際の草", "where", "band", "pitch", "asset", "cert", "why");
            float bLo, bHi; Pair(mzg, "band", out bLo, out bHi);
            string api = Sk(mzg, "asset") ?? "";
            var rg = ParenInts(api);    // NM.GrassMeadow("02", "", 2〜6) → [2, 6](族の "02" は引用符の中で数えない)
            var idx = new List<int>();
            if (rg.Count >= 2) foreach (var i in EdoAssets.NM.GrassMeadowIndices("02", "")) if (i >= rg[0] && i <= rg[rg.Count - 1]) idx.Add(i);
            if (!api.StartsWith("NM.GrassMeadow(\"02\"") || idx.Count == 0 || float.IsNaN(bLo))
                Wait("水際の草: asset「" + api + "」か band が読めない — 据えない");
            else
            {
                var runs = new Dictionary<string, Dictionary<string, object>>();
                foreach (var key in new[] { "gogan", "rangui" }) if (Has(gs, key)) foreach (var o in A(gs[key])) { var q = O(o); runs[Sk(q, "name")] = q; }
                var bands = SuhamaBands();
                float pitch = F(mzg["pitch"]);
                var kusa = EdoBuild.NiwaSet.Kusa;
                foreach (var w0 in A(mzg["where"]))
                {
                    Dictionary<string, object> rr;
                    if (!runs.TryGetValue(S(w0) ?? "", out rr) || Has(rr, "walk")) { Wait("水際の草: 「" + S(w0) + "」の汀が引けない"); continue; }
                    var line = EdgeWalk((int)F(rr["frm"]), (int)F(rr["to"]));
                    if (line == null || line.Count < 2) continue;
                    int cnt = Mathf.Max(1, Mathf.RoundToInt(LineLen(line) * Grid.ken / Mathf.Max(0.05f, pitch)));
                    for (int i = 0; i < cnt; i++)
                    {
                        Vector2 dir; Vector2 gp = LerpLine(line, (i + 0.5f) / cnt, out dir);
                        float off = Rnd(rnd, bLo, bHi), yaw = Rnd(rnd, 0f, 360f);
                        string path = EdoAssets.NM.GrassMeadow("02", "", idx[rnd.Next(idx.Count)]);
                        // band の + は陸側(水の側の法線の逆)と読む
                        Vector2 q = gp - WaterSide(gp, dir, false) * (off / Grid.ken);
                        if (SkInBand(bands, q) || !Exists(path)) continue;
                        var go = fld.Put(sgrp, path, WuV(q), yaw, 1f, Rnd(rnd, kusa.SinkLo, kusa.SinkHi), "Mizugiwa_" + mizu, "下草", kusa);
                        if (go != null) mizu++;
                    }
                }
                Wait("水際の草の band [" + bLo.ToString("F2") + ", " + bHi.ToString("F2") + "] は + を陸側と読んだ(gardenFields に符号の定義が無い ── 指図方へ)");
            }
        }
        if (stk != null && (Has(stk, "koke") || Has(stk, "shiba")))
            Wait("苔・芝(shitakusa.koke / shiba の layer)は地表のスプラット — 地表仕上げの工程が要る");

        return "植栽: 高中木 " + trees + " / 刈込玉 " + shrubs + " / 刈込 " + kari + " 株 / シダ " + shida + " / 水際の草 " + mizu
             + (leanDeep > 0 ? " / ⚠ 傾けて根入れが " + EdoBuild.NiwaSet.TREE_BURY_MAX.ToString("F1") + "m を越えた木 " + leanDeep : "")
             + " / 据えなかった: 区画の線 " + fld.DropEdge + "・急斜面 " + fld.DropSteep + "・根入れ超 " + fld.DropNeire + "・測れない " + fld.Refused
             + skRep.ToString();
    }

    /// <summary>庭の区画(泉水・奥庭の poly)のどれかの内か。下草の域が NiwaM の矩形(泉水)の外の奥庭に掛かる時のため。</summary>
    static bool InGardenPoly(Vector2 uv)
    {
        foreach (var nm in new[] { "G_Sensui", "G_Okuniwa" })
        {
            var g = Garden(nm); if (g == null || !Has(g, "poly")) continue;
            var pl = A(g["poly"]); var P = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) P[i] = UV(pl[i]);
            if (EdoGeom.PIP(P, uv)) return true;
        }
        return false;
    }

    /// <summary>植栽の行の i 本目の部材。`sizeEach` があれば丈の呼び名をそれで、`(1/2/3)` の個体は順に回す。</summary>
    static string PlantPath(Dictionary<string, object> sk, string api, int i)
    {
        int v = (i % 3) + 1;
        if (Has(sk, "sizeEach"))
        {
            var se = A(sk["sizeEach"]); string size = i < se.Count ? S(se[i]) : null;
            if (size == null) return null;
            if (api.StartsWith("Own.Jouryoku")) { string p = EdoAssets.Own.Jouryoku(size, v); return Exists(p) ? p : EdoAssets.Own.Jouryoku(size, 1); }
            if (api.StartsWith("Own.Momiji")) { string p = EdoAssets.Own.Momiji(size, v); return Exists(p) ? p : EdoAssets.Own.Momiji(size, 1); }
            return null;
        }
        var vi = ParenInts(api);
        if (vi.Count > 1) return ResolveNiwaApi(api, vi[i % vi.Count]);
        string q = ResolveNiwaApi(api, v);
        return (q != null && Exists(q)) ? q : ResolveNiwaApi(api, 1);
    }

    // ------------------------------------------------------------------ 下草の散布域(⛔ 言葉でなく幾何)
    /// <summary>下草の散布域。指図 `shitakusa.shida.where` の `kata` から**毎回組み直す**(⛔ 範囲の数値を指図に写さない・実装で発明しない)。
    /// 「築山の面」= 案Aの裾の多角形 `tsukiyama[of].skirt` の `side` 側の半分(裾の頂点の重心を通る u = 一定 の線で切る)、
    /// `clipV` [v0, v1] はその帯を抜く(枯滝の前)。「樹下」= `shokusai` の同じ樹種の樹冠の円(実メッシュ)。</summary>
    class SkRegion
    {
        public string name, label, kata, err;
        public Vector2[] poly;                              // 「築山の面」(u,v)
        public List<Vector3> circ = new List<Vector3>();    // 「樹下」= 樹冠の円 (u, v, r[間])
        public float clipV0 = float.PositiveInfinity, clipV1 = float.NegativeInfinity;
    }

    static List<SkRegion> ShitakusaRegions()
    {
        var g = Garden("G_Sensui") ?? NiwaModel.g;
        var res = new List<SkRegion>();
        var st = Has(g, "shitakusa") ? O(g["shitakusa"]) : null;
        var sd = (st != null && Has(st, "shida")) ? O(st["shida"]) : null;
        var wl = (sd != null && Has(sd, "where")) ? A(sd["where"]) : null;
        if (wl == null) return res;
        var tk = new Dictionary<string, Dictionary<string, object>>();
        foreach (var o in A(g["tsukiyama"])) { var q = O(o); tk[Sk(q, "name")] = q; }
        foreach (var o in wl)
        {
            var w = O(o);
            if (w == null) { res.Add(new SkRegion { name = "?", label = "?", err = "散布域が文字列のまま — 幾何へ落としていない" }); continue; }
            var r = new SkRegion { name = Sk(w, "name"), label = Sk(w, "label"), kata = Sk(w, "kata") };
            float c0, c1; if (Pair(w, "clipV", out c0, out c1)) { r.clipV0 = c0; r.clipV1 = c1; }
            if (r.kata == "築山の面")
            {
                Dictionary<string, object> t = null;
                tk.TryGetValue(Sk(w, "of") ?? "", out t);
                if (t == null || !Has(t, "skirt")) r.err = "築山 " + Sk(w, "of") + " に裾の多角形 skirt が無い";
                else
                {
                    var pl = A(t["skirt"]); var P = new List<Vector2>();
                    foreach (var q in pl) P.Add(UV(q));
                    Vector2 c = Vector2.zero; foreach (var p in P) c += p; c /= Mathf.Max(1, P.Count);
                    string side = Has(w, "side") ? Sk(w, "side") : null;
                    if (side == null || side.Length < 2 || (side[1] != 'u' && side[1] != 'v')) r.err = "`side` が読めない: " + side;
                    else r.poly = ClipHalf(P, side[1] == 'u', side[0] == '-' ? -1f : 1f, side[1] == 'u' ? c.x : c.y).ToArray();
                    if (r.poly != null && r.poly.Length < 3) r.err = "築山の面の半分が空";
                }
            }
            else if (r.kata == "樹下")
            {
                string sp = Sk(w, "species"), sz = Sk(w, "size");
                foreach (var o2 in A(g["shokusai"]))
                {
                    var sk = O(o2);
                    string sp2 = Sk(sk, "species");
                    if (sp == null || sp2 == null || !sp2.StartsWith(sp)) continue;
                    if (sz != null && Sk(sk, "size") != sz) continue;
                    float rad = CrownR(sk);
                    if (rad <= 0f) { r.err = "樹冠が測れない: " + sp; break; }
                    foreach (var p0 in A(sk["at"])) { var p = A(p0); r.circ.Add(new Vector3(F(p[0]), F(p[1]), rad)); }
                }
                if (r.err == null && r.circ.Count == 0) r.err = "`shokusai` に「" + sp + "」の層が無い";
            }
            else r.err = "知らない `kata` " + r.kata + " — 語彙に無い値では何も撒かない";
            res.Add(r);
        }
        return res;
    }

    /// <summary>多角形を半平面(axisU ? u : v)·sign ≥ at·sign で切る(Sutherland–Hodgman)。</summary>
    static List<Vector2> ClipHalf(List<Vector2> P, bool axisU, float sign, float at)
    {
        var res = new List<Vector2>();
        Func<Vector2, float> d = p => ((axisU ? p.x : p.y) - at) * sign;
        for (int i = 0; i < P.Count; i++)
        {
            Vector2 a = P[i], b = P[(i + 1) % P.Count];
            float da = d(a), db = d(b);
            if (da >= 0f) res.Add(a);
            if ((da >= 0f) != (db >= 0f)) res.Add(Vector2.Lerp(a, b, da / (da - db)));
        }
        return res;
    }
    static float CrownR(Dictionary<string, object> sk)
    {
        string api = Sk(sk, "asset");
        float sc = Has(sk, "scale") ? F(sk["scale"]) : 1f;
        float w = 0f;
        for (int i = 1; i <= 3; i++)
        {
            string p = ResolveNiwaApi(api, i);
            if (p == null || !Exists(p)) continue;
            float ww, hh; MeasureWH(p, out ww, out hh);
            w = Mathf.Max(w, ww);
        }
        return w <= 0f ? 0f : w / 2f * sc / Grid.ken;
    }

    static bool SkIn(SkRegion r, float u, float v)
    {
        if (r.poly != null && EdoGeom.PIP(r.poly, new Vector2(u, v))) return true;
        foreach (var c in r.circ)
            if ((u - c.x) * (u - c.x) + (v - c.y) * (v - c.y) <= c.z * c.z) return true;
        return false;
    }

    /// <summary>面積を測る格子(0.1間)。⚠ **生成器 `_shitakusa_pts` と同じ数え方**にする —
    /// 樹冠の円は円ごとに走査するので重なりを二重に数える(=面積は上限値)。
    /// ⛔ ここを賢くすると表と実装の面積が食い違う。</summary>
    static IEnumerable<Vector2> SkCells(SkRegion r)
    {
        const float ST = 0.1f;
        if (r.poly != null)
        {
            float u0 = float.MaxValue, u1 = float.MinValue, v0 = float.MaxValue, v1 = float.MinValue;
            foreach (var p in r.poly)
            {
                u0 = Mathf.Min(u0, p.x); u1 = Mathf.Max(u1, p.x);
                v0 = Mathf.Min(v0, p.y); v1 = Mathf.Max(v1, p.y);
            }
            for (float u = u0; u <= u1 + 1e-9f; u += ST)
                for (float v = v0; v <= v1 + 1e-9f; v += ST)
                    if (EdoGeom.PIP(r.poly, new Vector2(u, v))) yield return new Vector2(u, v);
        }
        foreach (var c in r.circ)
            for (float u = c.x - c.z; u <= c.x + c.z + 1e-9f; u += ST)
                for (float v = c.y - c.z; v <= c.y + c.z + 1e-9f; v += ST)
                    if ((u - c.x) * (u - c.x) + (v - c.y) * (v - c.y) <= c.z * c.z)
                        yield return new Vector2(u, v);
    }

    /// <summary>汀線の辺 i(0起算)の**外向き法線**(単位・(u,v))。
    /// ⛔ 池心からの方向で代用しない — 非凸の池では内を向く。</summary>
    static Vector2 ShoreOut(int i)
    {
        var n = NiwaModel; int m = n.pond.Length;
        Vector2 a = n.pond[i], b = n.pond[(i + 1) % m];
        float sa = 0f;
        for (int k = 0; k < m; k++)
        { Vector2 p = n.pond[k], q = n.pond[(k + 1) % m]; sa += p.x * q.y - q.x * p.y; }
        float sgn = sa > 0f ? 1f : -1f;
        Vector2 d = b - a; float L = Mathf.Max(1e-9f, d.magnitude);
        return new Vector2(sgn * d.y / L, -sgn * d.x / L);
    }

    /// <summary>州浜の砂利帯の平面形(汀の陸側 `toLand` のオフセット帯)。
    /// ⛔ **下草はここへ撒かない** — 指図が `bare`(そこの草は消す)と宣言している所。
    /// ⛔ 形を発明せず、`suhama` の `frm`/`to` と汀線から毎回組む。
    /// ⚠ ここは**計測と clip の器**なので**設計の汀**(`n.pond`)で組む — 生成器の
    /// 「下草の散布域」の表(砂利 19.5% ほか)と同じ数を出すため。
    /// ⭕ 砂利を**実際に撒く線**は `ShoreWalk`(水面メッシュの縁へ寄せてある)側。</summary>
    static List<Vector2[]> SuhamaBands()
    {
        var n = NiwaModel; var res = new List<Vector2[]>();
        if (!Has(n.g, "suhama")) return res;
        int m = n.pond.Length;
        foreach (var o in A(n.g["suhama"]))
        {
            var s = O(o);
            float off1 = F(s["toLand"]) / Grid.ken;
            var idx = new List<int>();
            int i = (int)F(s["frm"]) - 1, iEnd = (int)F(s["to"]) - 1;
            while (true) { idx.Add(i); if (i == iEnd) break; i = (i + 1) % m; if (idx.Count > m) break; }
            var inner = new List<Vector2>(); var outer = new List<Vector2>();
            int lim = idx.Count > 1 ? idx.Count - 1 : idx.Count;
            for (int k = 0; k < lim; k++)
            {
                int e = idx[k];
                Vector2 a = n.pond[e], b = n.pond[(e + 1) % m];
                Vector2 nn = ShoreOut(e);
                float L = Vector2.Distance(a, b);
                int ns = Mathf.Max(1, Mathf.CeilToInt(L / 0.05f));
                for (int t = 0; t <= ns; t++)
                {
                    Vector2 p = Vector2.Lerp(a, b, t / (float)ns);
                    inner.Add(p); outer.Add(p + nn * off1);
                }
            }
            if (inner.Count < 2) continue;
            var poly = new List<Vector2>(inner);
            for (int k = outer.Count - 1; k >= 0; k--) poly.Add(outer[k]);
            res.Add(poly.ToArray());
        }
        return res;
    }

    static bool SkInBand(List<Vector2[]> bands, Vector2 q)
    {
        foreach (var b in bands) if (EdoGeom.PIP(b, q)) return true;
        return false;
    }

    /// <summary>部材を1枚置いて**実寸**(平面の幅・丈)を測り、すぐ捨てる。⛔ 決め打ちの定数に戻さない。</summary>
    static void MeasureWH(string path, out float w, out float h)
    {
        w = 0f; h = 0f;
        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (pf == null) return;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf);
        go.transform.position = Vector3.zero; go.transform.rotation = Quaternion.identity;
        go.transform.localScale = Vector3.one;
        var b = EdoBuild.RB(go);
        w = Mathf.Max(b.size.x, b.size.z); h = b.size.y;
        UnityEngine.Object.DestroyImmediate(go);
    }

    /// <summary>指図が書く `EdoAssets.…` の呼び名を実パスへ解く。⛔ 解けない名前は null を返し、
    /// 呼び側が「未据え付け」へ積む(⛔ 近い部材へ勝手に寄せない)。</summary>
    static string ResolveNiwaApi(string api, int variant)
    {
        if (string.IsNullOrEmpty(api)) return null;
        // "A / B / C" の並びは個体の選択肢 — variant で選ぶ
        var alts = api.Split('/');
        string a = alts[Mathf.Clamp(variant - 1, 0, alts.Length - 1)].Trim();
        // ⚠ **族(どの部材か)は先頭の一つで見る。**「A / B / C」の 2つ目以降は `PineMid02` のように
        //   `JG.` の接頭辞を持たないので、選んだ側で族を判定すると 2本目から解けなくなる
        //   (2026-09-06 に踏んだ — クロマツ Mid が1本も据わらなかった)。
        string head = alts[0].Trim();
        if (head.StartsWith("EdoAssets.")) head = head.Substring("EdoAssets.".Length);
        a = head;
        if (a.StartsWith("Own.Jouryoku")) return EdoAssets.Own.Jouryoku(ArgSize(api), variant);
        if (a.StartsWith("Own.Momiji")) return EdoAssets.Own.Momiji(ArgSize(api), variant);
        if (a.StartsWith("Own.Ume")) return EdoAssets.Own.Ume(ArgSize(api), variant);
        // ⭐ 雪見灯籠は在庫の edogoyomi `t_yukimi`(2026-09-06 に指図が自作プレハブから差し替えた)。
        //   ⛔ `Own.YukimiLantern`(自作)は材質がべた塗りなので使わない。
        if (a.StartsWith("Eg.ToroYukimi")) return EdoAssets.Eg.ToroYukimi;
        if (a.StartsWith("Own.YukimiLantern")) return EdoAssets.Own.YukimiLantern;
        if (a.StartsWith("Own.Toro")) return EdoAssets.Own.Toro;
        // 庭石(景石・護岸石・岩島・荒磯の立石)。個体の番号は括弧から読む
        if (a.StartsWith("Own.Ishigumi")) return EdoAssets.Own.Ishigumi(Mathf.RoundToInt(ArgNum(api, -1f)));
        // ⭐ 沓脱石は**専用部材**(2026-09-06 部材方が焼いた)。⛔ 立石を非一様スケールで代用しない。
        if (a.StartsWith("Own.DoiKutsunugi")) return EdoAssets.Own.DoiKutsunugi;
        // ⭐ 木戸・竹垣は寸法で焼き分ける。⚠ 数の引数は括弧から読む
        if (a.StartsWith("Own.Kido")) return EdoAssets.Own.Kido(ArgNum(api, 1.8f));
        if (a.StartsWith("Own.KenninjiGakiPost")) return EdoAssets.Own.KenninjiGakiPost(ArgNum(api, 1.8f));
        if (a.StartsWith("Own.KenninjiGaki")) return EdoAssets.Own.KenninjiGaki(ArgNum(api, 1.8f));
        if (a.StartsWith("Own.YotsumeGakiPost")) return EdoAssets.Own.YotsumeGakiPost(ArgNum(api, 0.9f));
        if (a.StartsWith("Own.YotsumeGaki")) return EdoAssets.Own.YotsumeGaki(ArgNum(api, 0.9f));
        // ⚠ 立石の丈は **S / M / L**。⛔ 樹木の呼び名("Big"/"Mid"/"Small")を当てない —
        //   解けない丈は null を返し、呼び側が「未据え付け」へ積む(⛔ 近い丈へ寄せない)。
        if (a.StartsWith("Own.Tateishi")) return EdoAssets.Own.Tateishi(ArgSize(api), variant);
        if (a.StartsWith("KasugaLantern") || a.StartsWith("Own.KasugaLantern")) return EdoAssets.Own.KasugaLantern;
        if (a.StartsWith("Okabe.Inari15")) return EdoAssets.Own.Inari15;
        if (a.StartsWith("Okabe.Torii")) return EdoAssets.Own.Torii;
        if (a.StartsWith("JG.PineBig")) return JGPine("Big", variant);
        if (a.StartsWith("JG.PineMid")) return JGPine("Mid", variant);
        if (a.StartsWith("JG.TobiIshi")) return EdoAssets.Own.Tobiishi(variant - 1);
        if (a.StartsWith("JG.BoxwoodSingle")) return EdoAssets.JG.BoxwoodSingle(variant);   // ⚠ JG.Boxwood より先に見る(接頭辞が同じ)
        if (a.StartsWith("JG.Boxwood")) return EdoAssets.JG.Boxwood(variant);
        if (a.StartsWith("JG.Azalea")) return EdoAssets.JG.Azalea(variant);
        // ⚠ 春日型は EdoAssets の注記で「屋敷の庭には使わない」── 指図が名指した時だけ解き、呼び手が食い違いを控えへ積む
        if (a.StartsWith("Eg.ToroKasuga")) return EdoAssets.Eg.ToroKasuga;
        if (a.StartsWith("Own.Kutsunugi")) return EdoAssets.Own.Kutsunugi;
        if (a.StartsWith("Own.DoiMizushiriHakiguchi")) return EdoAssets.Own.DoiMizushiriHakiguchi;
        if (a.StartsWith("Own.DoiMizushiriShiki")) return EdoAssets.Own.DoiMizushiriShiki;
        if (a.StartsWith("Own.Tobiishi")) return EdoAssets.Own.Tobiishi(Mathf.RoundToInt(ArgNum(api, 0f)));
        if (a.StartsWith("Own.Ikegaki")) return EdoAssets.Own.Ikegaki(variant > 1);   // 2 = 端
        if (a.StartsWith("JG.Fern")) return EdoAssets.JG.Fern(variant);
        return null;
    }
    static string JGPine(string size, int i)
    {
        i = Mathf.Clamp(i, 1, 3);
        if (size == "Big") return i == 1 ? EdoAssets.JG.PineBig01 : (i == 2 ? EdoAssets.JG.PineBig02 : EdoAssets.JG.PineBig03);
        return EdoAssets.JG.PineMid01.Replace("Mid_Green_01", "Mid_Green_0" + i);
    }
    /// <summary>護岸の**地の石の駒の選び方**(指図 `gogan[].ishiPick`。例「乱数(2 と 4)」)を
    /// 個体番号の集合へ。⛔ **読めなければ null**を返し、呼び側は据えるのをやめて差し戻す —
    /// 既定の駒へ倒すと「指図と反対の物」が黙って建つ(2026-09-06 にそれで交互のまま建っていた)。
    /// ⚠ 「乱数」以外の指定(交互・順送りなど)は**別の据え方**なのでここでは解かない。
    /// ⚠ 個体は 0..4 の5体しか無いので、範囲の外の数を含む綴りも読めないものとして返す。</summary>
    static int[] ParseIshiPick(string s)
    {
        if (string.IsNullOrEmpty(s) || s.IndexOf("乱数") < 0) return null;
        var nums = new List<int>();
        int i = 0;
        while (i < s.Length)
        {
            if (s[i] < '0' || s[i] > '9') { i++; continue; }
            int v = 0;
            while (i < s.Length && s[i] >= '0' && s[i] <= '9') { v = v * 10 + (s[i] - '0'); i++; }
            if (v < 0 || v > 4) return null;
            if (!nums.Contains(v)) nums.Add(v);
        }
        return nums.Count > 0 ? nums.ToArray() : null;
    }

    /// <summary>`Own.Kido(1.8)` の 1.8 を取り出す。⛔ 読めなければ既定へ倒さず呼び側へ返す
    /// ため、既定値は呼び側が明示して渡す。</summary>
    static float ArgNum(string api, float dflt)
    {
        int a = api.IndexOf('(');
        if (a < 0) return dflt;
        int b = api.IndexOf(')', a + 1);
        if (b <= a) return dflt;
        float v;
        return float.TryParse(api.Substring(a + 1, b - a - 1).Trim(), out v) ? v : dflt;
    }

    /// <summary>`Own.Jouryoku("Big", i)` の "Big" を取り出す。</summary>
    static string ArgSize(string api)
    {
        int a = api.IndexOf('"');
        if (a < 0) return "Mid";
        int b = api.IndexOf('"', a + 1);
        return b > a ? api.Substring(a + 1, b - a - 1) : "Mid";
    }

    /// <summary>括弧の中の数の並び(引用符の中は数えない)。`JG.Azalea(1/3/4)` → 1,3,4・`NM.GrassMeadow("02", "", 2〜6)` → 2,6・
    /// `Own.Rangui(0.034/0.043/0.052)` → 0.034,0.043,0.052。⛔ 読めなければ空(呼び手が控えへ積む)。</summary>
    static List<float> ParenFloats(string s)
    {
        var res = new List<float>();
        if (string.IsNullOrEmpty(s)) return res;
        int depth = 0; bool q = false; var tok = new System.Text.StringBuilder();
        Action flush = () =>
        {
            if (tok.Length == 0) return;
            float v; if (float.TryParse(tok.ToString(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out v)) res.Add(v);
            tok.Length = 0;
        };
        foreach (char c in s)
        {
            if (c == '"') { q = !q; flush(); continue; }
            if (c == '(') { depth++; flush(); continue; }
            if (c == ')') { flush(); depth = Mathf.Max(0, depth - 1); continue; }
            if (depth > 0 && !q && ((c >= '0' && c <= '9') || c == '.')) tok.Append(c); else flush();
        }
        flush();
        return res;
    }
    static List<int> ParenInts(string s)
    {
        var res = new List<int>();
        foreach (var f in ParenFloats(s)) if (Mathf.Abs(f - Mathf.Round(f)) < 1e-4f) res.Add(Mathf.RoundToInt(f));
        return res;
    }

    /// <summary>飛石・踏分石の駒(`Own.Tobiishi(n)`)。読めなければ null。</summary>
    static string ResolveTobi(string api)
    {
        if (string.IsNullOrEmpty(api) || !api.Trim().StartsWith("Own.Tobiishi")) return null;
        var v = ParenInts(api);
        return v.Count > 0 ? EdoAssets.Own.Tobiishi(v[0]) : null;
    }

    /// <summary>**まだ EdoAssets に無いかもしれない部材**を名で引く(別の役が新造中の物 ── 石橋・土橋・丸太段・延段・縁先手水鉢・腰掛)。
    /// ⛔ 直に `EdoAssets.Own.DoiIshibashi` と書くと、登録されるまでこのファイルがコンパイルできない ── 反射で引き、無ければ null
    /// (呼び手は据えずに控えへ積む)。登録されたら直の参照へ置き換えてよい。</summary>
    static string OptAsset(string cls, string member, params object[] args)
    {
        var bf = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
        var t = typeof(EdoAssets).GetNestedType(cls, System.Reflection.BindingFlags.Public);
        if (t == null) return null;
        var f = t.GetField(member, bf);
        if (f != null) return f.GetValue(null) as string;
        var p = t.GetProperty(member, bf);
        if (p != null) return p.GetValue(null, null) as string;
        foreach (var m in t.GetMethods(bf))
        {
            if (m.Name != member || m.ReturnType != typeof(string) || m.GetParameters().Length != args.Length) continue;
            try { return m.Invoke(null, args) as string; } catch (Exception) { return null; }
        }
        return null;
    }
}
