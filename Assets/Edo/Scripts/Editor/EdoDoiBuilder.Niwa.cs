// 土井大隅守上屋敷 — 奥庭(Stage6)。
//
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
    // ------------------------------------------------------------------ 奥庭のモデル(生成器 Niwa の移植)
    public class NiwaM
    {
        public Dictionary<string, object> g;
        public float u0, v0, u1, v1;
        public float waterY, depth, dmax, baseY;
        public bool hasShallow; public float shV0, shV1, shBedY;
        public Vector2[] pond;
        public List<Dictionary<string, object>> mounds = new List<Dictionary<string, object>>();

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
            if (Has(t, "kata") && S(t["kata"]) == "土手")
            {
                float tu0 = F(t["u0"]), tu1 = F(t["u1"]), tv0 = F(t["v0"]), tv1 = F(t["v1"]);
                if (!(tu0 <= u && u <= tu1 && tv0 <= v && v <= tv1)) return 0f;
                float r, a9, a0, a1;
                // ⭐ 減衰軸は `decay` が決める。⛔ 未指定を既定へ倒さない(指図の `dote_check` が鳴らす)
                if (Has(t, "decay") && S(t["decay"]) == "u")
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
        /// <summary>造園後の地表。池の中は池床、外は面+築山(生成器 `Niwa.ground`)。</summary>
        public float Ground(float u, float v)
        { return InPond(u, v) ? Bed(u, v) : baseY + Mound(u, v); }
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
                    waterY = F(mg["waterY"]), depth = F(mg["depthMax"])
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
                foreach (var o in A(g["tsukiyama"])) n.mounds.Add(O(o));
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
        if (mat != null) go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        var msh = AssetDatabase.LoadAssetAtPath<Mesh>(MSH);
        if (msh != null) go.GetComponent<MeshFilter>().sharedMesh = msh;   // 既存を上書き更新させる
        WaterBaker.RebuildSurface(wb);
        Wait("池の水面は `WaterBody` を自前で組んで `RebuildSurface` だけを呼んだ。"
           + "⚠ 指図 `impl.waterBaker` の `WaterBaker.Create` は**内部で Recarve を呼び、"
           + "snap 矩形 312×320m 全域に4パスの平滑化をかけて書き戻す**ので採れない"
           + "(指図 `impl.noRecarve` の趣旨と矛盾する)→ 指図方へ差し戻し");
        return r + " / 水面 " + n.pond.Length + "点 水位 " + n.waterY.ToString("F2");
    }

    // ---- ②護岸(石組・州浜・乱杭)
    public static string Niwa_B_Gogan()
    {
        var n = NiwaModel;
        var grp = Group("Niwa/Gogan"); Clear(grp);
        var rnd = new System.Random(20260906);
        int stones = 0, ran = 0, su = 0;
        // Ishigumi_i の丈1.0 のときの平面 W(X)(EdoAssets.Own.Ishigumi の実測表)
        float[] IGW = new float[] { 0.263f, 0.889f, 2.161f, 1.536f, 1.174f };

        foreach (var o in A(n.g["gogan"]))
        {
            var gg = O(o);
            var line = ShoreWalk((int)F(gg["frm"]), (int)F(gg["to"]));
            float L = LineLen(line);
            float lenMin = F(gg["lenMin"]), lenMax = F(gg["lenMax"]);
            float ykMin = F(gg["yakuMin"]), ykMax = F(gg["yakuMax"]);
            int ykEvery = (int)F(gg["yakuEvery"]);
            float capMin = F(gg["capMin"]), capMax = F(gg["capMax"]);
            float pitchRatio = F(gg["pitchRatio"]), jag = F(gg["jag"]);
            float ken = Grid.ken;
            // ⚠ **汀線の長さは間、石の寸法は m。**混ぜると本数が 1.818 倍ずれる
            //   (2026-09-06 に踏んだ)。個数は生成器 `niwa_stats` と同じ式で決める:
            //   n = round(弧長[m] / (平均長軸 × pitchRatio))。
            float Lm = L * ken;
            int cnt = Mathf.Max(1, Mathf.RoundToInt(Lm / Mathf.Max(0.05f, (lenMin + lenMax) * 0.5f * pitchRatio)));
            for (int i = 0; i < cnt; i++)
            {
                bool yaku = (ykEvery > 0 && i % ykEvery == 0);
                float axis = yaku ? Mathf.Lerp(ykMin, ykMax, (float)rnd.NextDouble())
                                  : Mathf.Lerp(lenMin, lenMax, (float)rnd.NextDouble());
                int variant = yaku ? 3 : (i % 2 == 0 ? 2 : 4);
                string path = EdoAssets.Own.Ishigumi(variant);
                if (!Exists(path)) { Wait("庭石の部材が無い: " + path); break; }
                Vector2 dir;
                Vector2 gp = LerpLine(line, (i + 0.5f) / cnt, out dir);
                Vector2 nrm = new Vector2(dir.y, -dir.x);
                float off = ((float)rnd.NextDouble() - 0.5f) * 2f * jag / ken;
                Vector2 gq = gp + nrm * off;
                Vector2 wpt = Wu(gq.x, gq.y);
                float scale = axis / Mathf.Max(0.05f, IGW[variant]);
                float cap = Mathf.Lerp(capMin, capMax, (float)rnd.NextDouble());
                float top = n.waterY + cap;
                var go = EdoBuild.Place(path, new Vector3(wpt.x, top - scale, wpt.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * scale,
                                        grp, S(gg["name"]) + "_" + i);
                if (go != null) stones++;
            }
            // 荒磯(指定の汀点に大ぶりの立石を1基)
            if (Has(gg, "araiso"))
            {
                var ar = O(gg["araiso"]);
                Vector2 gp = Sh((int)F(ar["at"]));
                Vector2 wpt = Wu(gp.x, gp.y);
                string path = EdoAssets.Own.Ishigumi(3);
                float sc = F(ar["scale"]);
                var go = EdoBuild.Place(path, new Vector3(wpt.x, n.waterY - sc * 0.33f, wpt.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * sc, grp,
                                        S(gg["name"]) + "_Araiso");
                if (go != null)
                {
                    go.transform.rotation *= Quaternion.Euler(F(ar["tilt"]), 0, 0);
                    stones++;
                }
            }
        }

        // 州浜(平石を汀に沿って。砂利の帯そのものは**地表の塗り**で、部材ではない)
        foreach (var o in A(n.g["suhama"]))
        {
            var sh = O(o);
            var line = ShoreWalk((int)F(sh["frm"]), (int)F(sh["to"]));
            int ns = (int)F(sh["stones"]);
            for (int i = 0; i < ns; i++)
            {
                Vector2 dir;
                Vector2 gp = LerpLine(line, ns == 1 ? 0.5f : (i + 0.5f) / ns, out dir);
                Vector2 nrm = new Vector2(dir.y, -dir.x);
                Vector2 gq = gp + nrm * (0.3f / Grid.ken);
                Vector2 wpt = Wu(gq.x, gq.y);
                string path = EdoAssets.Own.Ishigumi(2);            // 臥石(低く広い)= 州浜の平石
                if (!Exists(path)) { Wait("庭石の部材が無い: " + path); break; }
                float scale = 0.35f;                                  // 半分埋めの平石
                var go = EdoBuild.Place(path, new Vector3(wpt.x, n.waterY - scale * 0.5f, wpt.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * scale, grp,
                                        S(sh["name"]) + "_" + i);
                if (go != null) su++;
            }
            Wait("州浜 " + S(sh["name"]) + " の**砂利の帯**(水面下 " + F(sh["fromWater"]).ToString("F1")
               + "m 〜 内陸 " + F(sh["toLand"]).ToString("F1") + "m・`bare` でそこの草を消す)は"
               + "**地表のスプラット**で、部材では表せない — 地表仕上げの工程が要る");
        }

        // 乱杭
        foreach (var o in A(n.g["rangui"]))
        {
            var rg = O(o);
            var line = ShoreWalk((int)F(rg["frm"]), (int)F(rg["to"]));
            float L = LineLen(line) * Grid.ken;                       // 弧長[間]→[m]
            float pitch = F(rg["pitch"]);                             // 芯々[m](生成器 niwa_stats と同じ)
            // ⭐⭐ **2026-09-06 に `topY` を廃し `topAbove`(水面からの相対)にした。**
            //   ⚠ 部材 `Own.Rangui` の**ピボットは頭の芯**なので `topY` = 頭の高さで、
            //     旧 25.87 = 水面 −0.33 は**36本とも全没**していた(普請検査の再測)。
            //   ⛔ 旧 `topY` へフォールバックしない — 沈むと分かっている値で建てない。
            if (!Has(rg, "topAbove"))
            { Wait("乱杭 " + S(rg["name"]) + " に `topAbove` が無い(⛔ 廃した `topY` は使わない)"); continue; }
            var ta = A(rg["topAbove"]);
            float taLo = F(ta[0]), taHi = F(ta[1]);
            float tilt = Has(rg, "tilt") ? F(rg["tilt"]) : 0f;
            float[] dias = new float[] { 0.034f, 0.043f, 0.052f };
            int cnt = Mathf.Max(1, Mathf.RoundToInt(L / Mathf.Max(0.02f, pitch)));
            // ⭐ **頭の高さは白色ノイズにしない**(2026-09-06 庭方)— 毎本振ると**櫛の歯**に見える。
            //   ⇒ 数本かけて緩やかに波打つ低周波(正弦2波の重ね)+ **時々1本だけ外れ値**。
            float ph1 = (float)rnd.NextDouble() * 6.2832f, ph2 = (float)rnd.NextDouble() * 6.2832f;
            float wl1 = 5.5f, wl2 = 13f;                              // 波長[本]
            for (int i = 0; i < cnt; i++)
            {
                float dia = dias[rnd.Next(dias.Length)];
                string path = EdoAssets.Own.Rangui(dia);
                if (!Exists(path)) { Wait("乱杭の部材が無い: " + path); break; }
                Vector2 dir;
                Vector2 gp = LerpLine(line, (i + 0.5f) / cnt, out dir);
                Vector2 wpt = Wu(gp.x, gp.y);
                float wave = 0.66f * Mathf.Sin(i * 6.2832f / wl1 + ph1)
                           + 0.34f * Mathf.Sin(i * 6.2832f / wl2 + ph2);   // −1..+1
                float t9 = 0.5f + 0.5f * wave;
                if (rnd.NextDouble() < 0.09) t9 = (float)rnd.NextDouble();  // 時々1本だけ外れ値
                float top = n.waterY + taLo + (taHi - taLo) * Mathf.Clamp01(t9);
                var go = EdoBuild.Place(path, new Vector3(wpt.x, top, wpt.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one, grp,
                                        S(rg["name"]) + "_" + i);
                if (go == null) continue;
                // 傾き ±tilt°(頭の芯がピボットなので、そのまま倒せば頭の位置は動かない)
                if (tilt > 0f)
                {
                    float ax = (float)rnd.NextDouble() * 360f;
                    float am = ((float)rnd.NextDouble() * 2f - 1f) * tilt;
                    go.transform.rotation = Quaternion.AngleAxis(ax, Vector3.up)
                                          * Quaternion.AngleAxis(am, Vector3.forward)
                                          * go.transform.rotation;
                }
                ran++;
            }
        }
        return "護岸: 石 " + stones + " / 州浜の平石 " + su + " / 乱杭 " + ran;
    }

    // ---- ③水尻(閾・吐き口・落とし溝・受け石)
    /// <summary>水尻。⭐ 2026-09-06 に部材が焼けた。ピボットは部材ごとに違う(部材方の docstring):
    ///   閾 = **閾の芯・天端**(⇒ `position.y = shiki.sill`)/ 吐き口 = **樋の芯・吐き口の面**
    ///   (⇒ `position.y = umeToi.outY`・**+Z = 流れの下流**)/ 落とし溝 = **スパンの中心・地盤**
    ///   (**+X = 流れの向き**)。⛔ **埋樋の本体は焼いていない**(土被り 0.30 以上で地上から見えない)。</summary>
    public static string Niwa_C_Mizushiri()
    {
        var n = NiwaModel;
        if (!Has(n.g, "mizu")) return "水尻: 指図に mizu が無い";
        var mz = O(n.g["mizu"]);
        if (!Has(mz, "mizushiri")) return "水尻: 指図に mizushiri が無い";
        var ms = O(mz["mizushiri"]);
        var grp = Group("Niwa/Mizushiri"); Clear(grp);
        var sb = new System.Text.StringBuilder();
        int made = 0;
        var rnd = new System.Random(20260909);

        // ① 石の閾(余水吐)— 汀 #14。**幅 1.20 は汀に沿う**(local +X = 汀の走り)
        if (Has(ms, "shiki"))
        {
            var sk = O(ms["shiki"]);
            string path = EdoAssets.Own.DoiMizushiriShiki;
            if (!Exists(path)) Wait("水尻の石の閾の部材が無い: " + path);
            else
            {
                int at = (int)F(sk["at"]);
                Vector2 gp = Sh(at);
                Vector2 nxt = Sh(at + 1), prv = Sh(at - 1);
                Vector2 sd = (Wu(nxt.x, nxt.y) - Wu(prv.x, prv.y)).normalized;   // 汀の走り
                Vector2 w = Wu(gp.x, gp.y);
                var go = EdoBuild.Place(path, new Vector3(w.x, F(sk["sill"]), w.y), YawFor(sd),
                                        Vector3.one, grp, "Shiki");
                if (go != null) { made++; sb.Append("閾1 "); }
            }
        }

        // ② 石組の吐き口(埋樋の終点)。**+Z = 流れの下流**、天端でなく**吐き口の面**が `outY`
        Vector2 outPt = Vector2.zero, flow = Vector2.right;
        bool haveOut = false;
        if (Has(ms, "umeToi"))
        {
            var ut = O(ms["umeToi"]);
            var pts = A(ut["pts"]);
            if (pts != null && pts.Count >= 2)
            {
                var pa = A(pts[pts.Count - 2]); var pb = A(pts[pts.Count - 1]);
                Vector2 wa = Wu(F(pa[0]), F(pa[1])), wb = Wu(F(pb[0]), F(pb[1]));
                outPt = wb; flow = (wb - wa).normalized; haveOut = true;
                string path = EdoAssets.Own.DoiMizushiriHakiguchi;
                if (!Exists(path)) Wait("水尻の吐き口の部材が無い: " + path);
                else
                {
                    var go = EdoBuild.Place(path, new Vector3(wb.x, F(ut["outY"]), wb.y), YawFace(flow),
                                            Vector3.one, grp, "Hakiguchi");
                    if (go != null) { made++; sb.Append("吐き口1 "); }
                }
            }
            sb.Append("(埋樋 φ" + F(ut["dia"]).ToString("F2") + " は地中なので焼かない) ");
        }

        // ③ 石敷きの落とし溝。**1m モジュールを流れに沿って並べ、端数は端の1本を切って吸う**
        //    (⛔ 全体を伸縮させて溝の石を引き伸ばさない)
        Vector2 endPt = Vector2.zero; bool haveEnd = false;
        if (Has(ms, "otoshimizo") && haveOut)
        {
            var om = O(ms["otoshimizo"]);
            var to = A(om["to"]);
            Vector2 wt = Wu(F(to[0]), F(to[1]));
            endPt = wt; haveEnd = true;
            string path = EdoAssets.Own.DoiOtoshimizo;
            if (!Exists(path)) Wait("水尻の落とし溝の部材が無い: " + path);
            else
            {
                float len = Vector2.Distance(outPt, wt);
                Vector2 dir = (wt - outPt) / Mathf.Max(1e-5f, len);
                float yaw = YawFor(dir);                       // 部材の +X = 流れの向き
                int full = Mathf.FloorToInt(len + 1e-4f);
                float rem = len - full;
                int k = full + (rem > 0.02f ? 1 : 0);
                for (int i = 0; i < k; i++)
                {
                    float wmod = (i < full) ? 1f : rem;        // 端の1本だけ切る
                    Vector2 c = outPt + dir * (i + wmod * 0.5f);
                    var go = EdoBuild.Place(path, new Vector3(c.x, GroundY(c.x, c.y), c.y), yaw,
                                            Vector3.one, grp, "Otoshimizo_" + i);
                    if (go == null) continue;
                    if (wmod < 0.999f) go.transform.localScale = new Vector3(wmod, 1f, 1f);
                    made++;
                }
                sb.Append("落とし溝" + k + "本(走り " + len.ToString("F2") + "m・端の1本を "
                        + (rem > 0.02f ? rem.ToString("F2") : "1.00") + "m に切る) ");
            }
        }

        // ④ 受け石(玉石の浸透枡)。⭐ **2026-09-06 に指図が数・方位・半径・天端の出入りを持った**
        //    (それまでは「玉石の浸透枡(受け石)」の一語で、第2回は 120°等配 3個を発明していた)。
        //    ⛔ **等配・等半径にしない** — 機械で置いた円に見える。方位・半径は `uke.at` が正典。
        //    ⛔ 「石は立てる」は景石の作法 — 受け石は**伏せる**(水を受ける面が要る)。
        if (haveEnd && Has(ms, "otoshimizo") && Has(O(ms["otoshimizo"]), "uke"))
        {
            var uk = O(O(ms["otoshimizo"])["uke"]);
            var uat = A(uk["at"]);
            if (uat == null || uat.Count == 0) Wait("受け石の `uke.at`(方位・半径)が無い");
            else
            {
                float usc = Has(uk, "scale") ? F(uk["scale"]) : 1f;
                float cj = Has(uk, "capJitter") ? F(uk["capJitter"]) : 0f;
                float ch = Has(uk, "capHigh") ? F(uk["capHigh"]) : 0f;
                if (Has(uk, "n") && (int)F(uk["n"]) != uat.Count)
                    Wait("受け石の `uke.n`(" + (int)F(uk["n"]) + ")と `uke.at` の数("
                       + uat.Count + ")が食い違う — ⛔ どちらかを黙って採らない");
                // ⭐ **どれが「下流側の1個」かは幾何で決まる** — 落とし溝の流れ(吐き口 → 終点)への
                //   射影が最大の石。⛔ 指図の番号を写さない(石を動かせば入れ替わる)。
                var toG = A(O(ms["otoshimizo"])["to"]);
                Vector2 endG = new Vector2(F(toG[0]), F(toG[1]));
                var utp = A(O(ms["umeToi"])["pts"]);
                var lastG = A(utp[utp.Count - 1]);
                Vector2 fg = endG - new Vector2(F(lastG[0]), F(lastG[1]));
                float fl = Mathf.Max(1e-6f, fg.magnitude);
                var offs = new List<Vector2>();
                int low = -1; float best = float.MinValue;
                for (int i = 0; i < uat.Count; i++)
                {
                    var q = A(uat[i]);
                    float deg = F(q[0]), rad = F(q[1]);          // [方位°, 半径m]
                    // ⚠ 方位は **(u,v) 格子の中の角**(0°=+u / 90°=+v)。半径は m なので間へ落とす
                    Vector2 dg = new Vector2(Mathf.Cos(deg * Mathf.Deg2Rad),
                                             Mathf.Sin(deg * Mathf.Deg2Rad)) * (rad / Grid.ken);
                    offs.Add(dg);
                    float pr = Vector2.Dot(dg, fg) / fl;
                    if (pr > best) { best = pr; low = i; }
                }
                string uapi = Has(uk, "asset") ? S(uk["asset"]) : null;
                // ⭐⭐ **2026-09-06 に `capMode` が「絶対高」になった。**⚠ 従前は**地盤基準**で、
                //   下流(#2)の地盤が 0.16m 低いぶん「+capHigh 高く」しても**絶対高では3個中いちばん
                //   低く**なり(#1 26.109 / #2 25.964 / #3 26.092)、**枡が下流へ抜けていた**。
                //   ⇒ ①3点の地盤の**最高点 + `capBase`** を基準天端 ②`capHighWhich` の1個だけ
                //     さらに +`capHigh` ③残りは基準 ±`capJitter` — いずれも**絶対高**。
                //   ⛔ **地盤からの相対で据えない。**⛔ `capMode` が無い/知らない語なら建てずに差し戻す。
                string capMode = Has(uk, "capMode") ? S(uk["capMode"]) : null;
                if (capMode == null || capMode.IndexOf("絶対高") < 0)
                { Wait("受け石の `capMode` が『絶対高』でない(" + (capMode ?? "無し") + ")— 指図方へ"); }
                float capBase = Has(uk, "capBase") ? F(uk["capBase"]) : float.NaN;
                if (float.IsNaN(capBase)) Wait("受け石の `capBase` が無い(⛔ 既定値で埋めない)");
                // ---- ① 3点の地盤を先に測り、最高点を出す(⛔ 石ごとに地盤へ寄せない)
                var uc = new List<Vector2>(); var ugy = new List<float>();
                float gTop = float.MinValue;
                for (int i = 0; i < uat.Count; i++)
                {
                    Vector2 gq = endG + offs[i];
                    Vector2 c = Wu(gq.x, gq.y);
                    uc.Add(c); float gy0 = GroundY(c.x, c.y); ugy.Add(gy0);
                    gTop = Mathf.Max(gTop, gy0);
                }
                float capRef = gTop + (float.IsNaN(capBase) ? 0f : capBase);
                int uke = 0; var capRep = new System.Text.StringBuilder();
                for (int i = 0; i < uat.Count; i++)
                {
                    // ⛔ **1種で並べない** — variant を3種混ぜる(指図 `asset` の "1..3")
                    string path = ResolveNiwaApi(uapi, (i % 3) + 1);
                    if (path == null || !Exists(path))
                    { Wait("受け石の部材が引けない: " + (uapi ?? "(asset 無し)")); break; }
                    // ⭐ **石ごとの `scale` を許す**(庭方: 下流の1個は見付が足りず 0.55 → 0.95)。
                    //   指図が `scaleEach` を持てばそれ、無ければ一律 `scale`。⛔ 実装で個別に決めない
                    float sc = usc;
                    if (Has(uk, "scaleEach"))
                    { var se = A(uk["scaleEach"]); if (se != null && i < se.Count) sc = F(se[i]); }
                    var go = EdoBuild.Place(path, new Vector3(uc[i].x, ugy[i], uc[i].y),
                                            (float)rnd.NextDouble() * 360f, Vector3.one * sc,
                                            grp, "Ukeishi_" + (i + 1));
                    if (go == null) continue;
                    // **伏せる** — 丈 1.0 に正規化した立石を 90° 倒す(⛔ 立てない = 水を受ける面が要る)
                    go.transform.rotation = go.transform.rotation * Quaternion.Euler(90f, 0f, 0f);
                    var bb = EdoBuild.RB(go);
                    // ---- ②③ 天端を**絶対高**へ合わせ、沈み代はその従属値にする
                    float cap = capRef + (i == low ? ch : ((float)rnd.NextDouble() * 2f - 1f) * cj);
                    go.transform.position += new Vector3(0f, cap - bb.max.y, 0f);
                    var bb2 = EdoBuild.RB(go);
                    float mitsuke = bb2.max.y - ugy[i];                 // 見付(地盤から上)
                    float nene = ugy[i] - bb2.min.y;                    // 根入れ(地盤から下)
                    // ⭐ **`uke.digEach` は「据え穴をどれだけ掘るか」の申告**(2026-09-06 庭方)。
                    //   ⚠ **石は動かない** — 天端は絶対高、`scale` を上げれば丈が伸びて底が下がり、
                    //   そのぶん穴が要る。⇒ 掘り代は**根入れ以上**でなければ石が納まらない。
                    //   ⛔ 掘り代を地盤の高さと取り違えない(地盤を下げると根入れは逆に減る)。
                    float dig = 0f;
                    if (Has(uk, "digEach"))
                    { var de = A(uk["digEach"]); if (de != null && i < de.Count) dig = F(de[i]); }
                    capRep.Append("\n     受け石#" + (i + 1) + (i == low ? "(下流)" : "") + " 天端 "
                        + bb2.max.y.ToString("F3") + " / 地盤 " + ugy[i].ToString("F3")
                        + " / 見付 " + mitsuke.ToString("F3") + " / 根入れ " + nene.ToString("F3")
                        + " / scale " + sc.ToString("F2")
                        + (dig > 0f ? " / 掘り代の申告 " + dig.ToString("F2") : ""));
                    if (dig > 0f && nene > dig + 1e-4f)
                        Wait("受け石#" + (i + 1) + ": 根入れ " + nene.ToString("F3")
                           + "m が申告の掘り代 " + dig.ToString("F2") + "m を超える — 指図方へ");
                    // ⚠ 庭方: **根入れ ≥ 見付 × `buryMin`**。⛔ 実装で天端を下げて辻褄を合わせない
                    if (Has(uk, "buryMin"))
                    {
                        float bm = F(uk["buryMin"]);
                        if (mitsuke > 1e-4f && nene < mitsuke * bm - 1e-4f)
                            Wait("受け石#" + (i + 1) + " の根入れ " + nene.ToString("F3")
                               + "m が見付 " + mitsuke.ToString("F3") + "m × `buryMin` "
                               + bm.ToString("F2") + " に足りない"
                               + " — `scale` を上げるか天端を見直す(⛔ 天端は下げない)");
                    }
                    uke++;
                }
                made += uke;
                sb.Append("受け石" + uke + "(絶対高: 地盤の最高 " + gTop.ToString("F3")
                        + " + capBase " + capBase.ToString("F2") + " = 基準天端 " + capRef.ToString("F3")
                        + " / 下流=" + (low + 1) + "番に +" + ch.ToString("F2") + "m)" + capRep.ToString());
            }
        }
        return "水尻: " + made + " 基 " + sb.ToString();
    }

    // ---- ④石組・灯籠・沓脱・飛石・沢飛石
    static string Niwa_D_Tenkei()
    {
        var n = NiwaModel;
        var grp = Group("Niwa/Tenkei"); Clear(grp);
        var rnd = new System.Random(20260907);
        float[] IGW = new float[] { 0.263f, 0.889f, 2.161f, 1.536f, 1.174f };
        int made = 0;

        // 三尊石。指図 `h` は露出高で `buryRatio` 0.333 ⇒ 全丈 H = h×1.5、底 = 地盤 − 0.5h
        string[] byRole = new string[] { "0", "1", "2" };
        int ri = 0;
        foreach (var o in A(n.g["ishigumi"]))
        {
            var ig = O(o);
            float u = F(ig["u"]), v = F(ig["v"]), hh = F(ig["h"]);
            float bury = Has(ig, "buryRatio") ? F(ig["buryRatio"]) : 0.333f;
            float H = hh / Mathf.Max(0.01f, 1f - bury);
            int variant = ri == 0 ? 0 : (ri == 1 ? 1 : 2);      // 主石=立石 / 副石=立石(太) / 添石=臥石
            string path = EdoAssets.Own.Ishigumi(variant);
            if (!Exists(path)) { Wait("庭石の部材が無い: " + path); break; }
            Vector2 w = Wu(u, v);
            float gnd = GroundY(w.x, w.y);
            var go = EdoBuild.Place(path, new Vector3(w.x, gnd - H * bury, w.y),
                                    (float)rnd.NextDouble() * 360f, Vector3.one * H, grp, S(ig["name"]));
            if (go != null) made++;
            ri++;
        }

        // 灯籠
        foreach (var o in A(n.g["toro"]))
        {
            var tr = O(o);
            string api = S(tr["asset"]);
            string path = ResolveNiwaApi(api, 1);
            if (path == null || !Exists(path)) { Wait("灯籠の部材が引けない: " + S(tr["name"]) + " → " + api); continue; }
            Vector2 w = Wu(F(tr["u"]), F(tr["v"]));
            float sc = path.EndsWith(".obj") ? ES : 1f;      // edogoyomi の obj は ES を掛ける
            var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y),
                                    (float)rnd.NextDouble() * 360f, Vector3.one * sc, grp, S(tr["name"]));
            if (go != null) { EdoBuild.SeatBottom(go, GroundY(w.x, w.y)); made++; }
        }

        // 沓脱石。⛔ **「石は立てる」は景石(`ishigumi`)の作法** — 沓脱石は**伏せて据える**物
        //   (踏む面が要る)。⭕ 専用部材 `Own.DoiKutsunugi`(2026-09-06 部材方が焼いた)は
        //   ピボット = **足形の芯・天端(水切りの中立点)**なので、`topY` を**直に**入れる。
        //   ⛔ bbox から座り直さない。⛔ 非一様スケールを掛けない(石肌の斑が流れる)。
        foreach (var o in A(n.g["kutsunugi"]))
        {
            var kg = O(o);
            string api2 = Has(kg, "asset") ? S(kg["asset"]) : null;
            string path = ResolveNiwaApi(api2, 1);
            if (path == null || !Exists(path))
            {
                Wait("沓脱石 " + S(kg["name"]) + "(" + F(kg["L"]).ToString("F2") + "×"
                   + F(kg["W"]).ToString("F2") + "m・天端 " + F(kg["topY"]).ToString("F2")
                   + ")の部材が引けない: " + (api2 ?? "(asset 無し)"));
                continue;
            }
            // ⭕ 水切りは**ローカル +Z へ 1/100**。⛔ **+Z を入側へ向けない** —
            //   指図 `mizukiri.to` が向きの正典(「−u(入側と反対=庭側)」)なので、
            //   そこから yaw を導く。⛔ 読めない値を既定へ倒さない(黙って裏返ると雨が縁の下へ入る)。
            var f9 = Grid;
            string mto = Has(kg, "mizukiri") && Has(O(kg["mizukiri"]), "to")
                       ? S(O(kg["mizukiri"])["to"]) : null;
            Vector2 zdir;
            if (mto != null && mto.StartsWith("-u")) zdir = new Vector2(-f9.ux, -f9.uz);
            else if (mto != null && mto.StartsWith("+u")) zdir = new Vector2(f9.ux, f9.uz);
            else if (mto != null && mto.StartsWith("-v")) zdir = new Vector2(-f9.vx, -f9.vz);
            else if (mto != null && mto.StartsWith("+v")) zdir = new Vector2(f9.vx, f9.vz);
            else
            {
                Wait("沓脱石 " + S(kg["name"]) + " の水切りの向き `mizukiri.to` が読めない: "
                   + (mto ?? "(無し)") + " — ⛔ 既定へ倒すと水切りが入側(縁の下)へ向くので据えない");
                continue;
            }
            Vector2 w = Wu(F(kg["u"]), F(kg["v"]));
            var go = EdoBuild.Place(path, new Vector3(w.x, F(kg["topY"]), w.y), YawFace(zdir),
                                    Vector3.one, grp, S(kg["name"]));
            if (go == null) continue;
            made++;
            if (Has(kg, "nekatame"))
                Wait("沓脱石の**根固め(" + S(kg["nekatame"]) + ")**は据えていない — 部材でなく"
                   + "**地表側の表現**(小石の散らしかスプラット)で、当邸の地表仕上げの工程がまだ無い"
                   + "(指図 `shitakusa.koke` の「コケ・芝はスプラット」と同じ待ち)");
        }

        // 飛石(ピボット=天端の芯)
        foreach (var o in A(n.g["tobiishi"]))
        {
            var tb = O(o);
            var pts = A(tb["pts"]);
            for (int i = 0; i < pts.Count; i++)
            {
                var p = A(pts[i]);
                Vector2 w = Wu(F(p[0]), F(p[1]));
                string path = EdoAssets.Own.Tobiishi(i % 2);   // 0=薄手 / 1=厚手
                if (!Exists(path)) { Wait("飛石の部材が無い: " + path); break; }
                float gnd = GroundY(w.x, w.y);
                var go = EdoBuild.Place(path, new Vector3(w.x, gnd + 0.04f, w.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * 0.55f,
                                        grp, S(tb["name"]) + "_" + i);
                if (go != null) made++;
            }
        }

        // 沢飛石(⚠ くびれには Tobiishi(2) を使う — 0/1 は厚 0.30〜0.36 しかなく水中に浮く)
        foreach (var o in A(n.g["sawatobi"]))
        {
            var sw = O(o);
            var a = A(sw["a"]); var b = A(sw["b"]);
            Vector2 ga = new Vector2(F(a[0]), F(a[1])), gb = new Vector2(F(b[0]), F(b[1]));
            float Lm = Vector2.Distance(Wu(ga.x, ga.y), Wu(gb.x, gb.y));
            float pitch = F(sw["pitch"]);                              // [m]
            int cnt = Mathf.Max(1, Mathf.RoundToInt(Lm / Mathf.Max(0.05f, pitch)));
            string path = EdoAssets.Own.Tobiishi(2);
            if (!Exists(path)) { Wait("沢飛石の部材が無い: " + path); continue; }
            for (int i = 0; i < cnt; i++)
            {
                Vector2 g = Vector2.Lerp(ga, gb, (i + 0.5f) / cnt);   // 生成器 niwa_stats と同じ割付
                Vector2 w = Wu(g.x, g.y);
                float axis = Mathf.Lerp(F(sw["rMin"]), F(sw["rMax"]), (float)rnd.NextDouble());
                var go = EdoBuild.Place(path, new Vector3(w.x, F(sw["topY"]), w.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * axis,
                                        grp, S(sw["name"]) + "_" + i);
                if (go != null) made++;
            }
        }
        // 岩島(池中。`inpondExempt` に載っているので水の中でよい)
        foreach (var o in A(n.g["iwajima"]))
        {
            var iw = O(o);
            string path = EdoAssets.Own.Ishigumi(4);           // 小塊 = 岩島の肩石向き
            if (!Exists(path)) { Wait("庭石の部材が無い: " + path); break; }
            Vector2 w = Wu(F(iw["u"]), F(iw["v"]));
            float H = F(iw["hMain"]);
            var go = EdoBuild.Place(path, new Vector3(w.x, n.waterY - F(iw["sink"]), w.y),
                                    (float)rnd.NextDouble() * 360f, Vector3.one * H, grp, S(iw["name"]));
            if (go != null) made++;
        }
        return "点景: " + made + " 基";
    }

    // ---- ⑤園路
    static string Niwa_E_Enro()
    {
        var n = NiwaModel;
        int cnt = A(n.g["enro"]).Count;
        Wait("園路 " + cnt + " 本(主路・枝路。仕上げ=真砂土の敷き均し・小端の縁石)— "
           + "**地表のスプラットと縁石**で表すもので、指図に部材(`asset`)が無い。"
           + "⛔ 代用品を置かない → 地表仕上げの工程 / 部材方へ");
        return "園路: 0/" + cnt + "(地表仕上げ待ち)";
    }

    // ---- ⑥稲荷(祠は Stage5 の `service.Inari`。ここは鳥居・参道・手水)
    static string Niwa_F_Yashiro()
    {
        var n = NiwaModel;
        if (!Has(n.g, "yashiro")) return "稲荷: 指図に yashiro が無い";
        var ys = O(n.g["yashiro"]);
        var grp = Group("Niwa/Yashiro"); Clear(grp);
        int made = 0;
        if (Has(ys, "torii"))
        {
            var tr = O(ys["torii"]);
            string path = ResolveNiwaApi(S(tr["asset"]), 1);
            if (path == null || !Exists(path)) Wait("鳥居の部材が無い: " + S(tr["asset"]));
            else
            {
                Vector2 w = Wu(F(tr["u"]), F(tr["v"]));
                // front:"+u" = 参道が +u へ抜ける。⛔ 向きを式で決め打ちしない — グリッドから引く
                var f = Grid;
                Vector2 dW = (f.W(F(tr["u"]) + 1f, F(tr["v"])) - w).normalized;
                float yaw = Mathf.Atan2(dW.x, dW.y) * Mathf.Rad2Deg;
                var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y), yaw,
                                        Vector3.one, grp, "Torii");
                if (go != null) { EdoBuild.SeatBottom(go, GroundY(w.x, w.y)); made++; }
            }
        }
        // 手水石。⭐ 2026-09-06 に `Own.DoiChozu` が焼けた。ピボット = **水盤の芯・地盤レベル**
        //   (底 −0.06 は根石が地中へ入る意図なので ⛔ `SeatBottom` で持ち上げない)。
        // ⚠ **指図の 0.6 × 0.4 は水盤の内法**で部材の外形は 0.70 × 0.50 — ⛔ 呼び寸法を渡さない。
        // ⭐ 据え向きは庭方の検め直しが決めた: **長辺(部材の X = 0.700)を参道の軸と平行**
        //   (直交させると路縁までの空きが +0.018m しか残らない)。参道の軸は u 方向。
        if (Has(ys, "chozu"))
        {
            var ch = O(ys["chozu"]);
            string path = EdoAssets.Own.DoiChozu;
            if (!Exists(path)) Wait("手水石の部材が無い: " + path);
            else
            {
                Vector2 w = Wu(F(ch["u"]), F(ch["v"]));
                var f2 = Grid;
                Vector2 uDir = (f2.W(1f, 0f) - f2.W(0f, 0f)).normalized;
                var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y), YawFor(uDir),
                                        Vector3.one, grp, "Chozu");
                if (go != null) made++;
            }
        }
        if (Has(ys, "sando"))
            Wait("稲荷の参道(玉砂利敷き)— **地表のスプラット**で部材では表せない");
        return "稲荷: 鳥居・手水 " + made + " 基(祠は Stage5 の service.Inari)";
    }

    // ---- ⑦垣
    static string Niwa_G_Kaki()
    {
        var n = NiwaModel;
        var grp = Group("Niwa/Kaki"); Clear(grp);
        int made = 0;
        foreach (var o in A(n.g["kaki"]))
        {
            var kk = O(o);
            string kata = S(kk["kata"]);
            float h = F(kk["h"]);
            bool kenninji = kata != null && kata.StartsWith("建仁寺");
            string span = kenninji ? EdoAssets.Own.KenninjiGaki(h) : EdoAssets.Own.YotsumeGaki(h);
            string post = kenninji ? EdoAssets.Own.KenninjiGakiPost(h) : EdoAssets.Own.YotsumeGakiPost(h);
            if (!Exists(span))
            {
                Wait("垣 " + S(kk["name"]) + "(" + kata + " h" + h.ToString("F1") + ")の部材が無い: " + span
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
                string open = S(kk["openSide"]);
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
            else { Wait("垣 " + S(kk["name"]) + ": 走りが読めない"); continue; }

            // ⭕ 1スパン = 1間ちょうど。端数は **端の駒を run の端に合わせて内側で重ねて吸う**
            //   (⛔ 等ピッチで中央寄せにすると端の駒が run の外へ出る)。`LayGaki` が正典。
            int idx = 0;
            foreach (var seg in lines)
            {
                Vector2 A0 = Wu(seg[0].x, seg[0].y), B0 = Wu(seg[1].x, seg[1].y);
                int nmade = LayGaki(grp, S(kk["name"]), span, post, A0, B0, idx);
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

    // ---- ⑧植栽・刈込・下草
    public static string Niwa_H_Shokusai()
    {
        var n = NiwaModel;
        var grp = Group("Niwa/Shokusai"); Clear(grp);
        var rnd = new System.Random(20260908);
        int trees = 0, kari = 0, shida = 0;

        foreach (var o in A(n.g["shokusai"]))
        {
            var sk = O(o);
            var at = A(sk["at"]);
            if (at == null) continue;
            float scale = Has(sk, "scale") ? F(sk["scale"]) : 1f;
            string api = S(sk["asset"]);
            for (int i = 0; i < at.Count; i++)
            {
                var p = A(at[i]);
                Vector2 w = Wu(F(p[0]), F(p[1]));
                string path = ResolveNiwaApi(api, (i % 3) + 1);
                if (path == null || !Exists(path))
                { Wait("植栽の部材が引けない: " + S(sk["species"]) + " " + S(sk["size"]) + " → " + api); break; }
                var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * scale,
                                        grp, "Ki_" + S(sk["size"]) + "_" + trees);
                if (go != null) trees++;
            }
        }

        // 刈込。指図は形(矩形/帯)と丈の範囲を持つ。部材は在庫のツゲ(`JG.Boxwood`)。
        var kgrp = Group("Niwa/Karikomi"); Clear(kgrp);
        float boxH = 0f, boxW = 0f; MeasureWH(EdoAssets.JG.Boxwood(1), out boxW, out boxH);
        foreach (var o in A(n.g["karikomi"]))
        {
            var kk = O(o);
            string kata = S(kk["kata"]);
            float hMin = F(kk["hMin"]), hMax = F(kk["hMax"]);
            var spots = new List<Vector2>();
            // ⚠ **株の間隔は部材の実寸から決める**(⛔ 決め打ちしない)。刈込は塊に見せるので
            //   実寸の 0.8 倍で詰める。⚠ 間[間]と m を混ぜない — 格子は間なので m/ken で刻む。
            float stepM = Mathf.Clamp(boxW * 0.8f, 0.30f, 0.70f);
            float stepG = stepM / Grid.ken;
            if (kata == "矩形")
            {
                float a0 = F(kk["u0"]), a1 = F(kk["u1"]), b0 = F(kk["v0"]), b1 = F(kk["v1"]);
                for (float u = a0 + stepG * 0.5f; u <= a1 - stepG * 0.25f; u += stepG)
                    for (float v = b0 + stepG * 0.5f; v <= b1 - stepG * 0.25f; v += stepG) spots.Add(new Vector2(u, v));
            }
            else
            {
                var line = ShoreWalk((int)F(kk["frm"]), (int)F(kk["to"]));
                float L = LineLen(line) * Grid.ken;                   // 弧長[間]→[m]
                float off0 = F(kk["off0"]), off1 = F(kk["off1"]);     // 汀からの控え[m]
                int cnt = Mathf.Max(2, Mathf.RoundToInt(L / stepM));
                for (int i = 0; i < cnt; i++)
                {
                    Vector2 dir;
                    Vector2 gp = LerpLine(line, (i + 0.5f) / cnt, out dir);
                    Vector2 nrm = new Vector2(dir.y, -dir.x);
                    if (n.InPond(gp.x + nrm.x * 0.1f, gp.y + nrm.y * 0.1f)) nrm = -nrm;   // 陸側へ
                    for (float t = off0; t <= off1 + 1e-4f; t += stepM)
                    {
                        Vector2 q = gp + nrm * (t / Grid.ken);
                        if (Has(kk, "vClip"))
                        {
                            var vc = A(kk["vClip"]);
                            if (q.y < F(vc[0]) || q.y > F(vc[1])) continue;
                        }
                        spots.Add(q);
                    }
                }
            }
            string bx = EdoAssets.JG.Boxwood(1);
            if (!Exists(bx) || boxH <= 0.01f) { Wait("刈込の部材が無い: " + bx); break; }
            int made = 0;
            foreach (var q in spots)
            {
                if (n.InPond(q.x, q.y)) continue;                    // ⛔ 水に落ちる物は据えない
                if (!n.Inside(q.x, q.y)) continue;
                Vector2 w = Wu(q.x, q.y);
                float h = Mathf.Lerp(hMin, hMax, (float)rnd.NextDouble());
                var go = EdoBuild.Place(bx, new Vector3(w.x, GroundY(w.x, w.y), w.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * (h / boxH),
                                        kgrp, S(kk["name"]) + "_" + made);
                if (go != null) { made++; kari++; }
            }
        }

        // 下草(シダ)。⭐ **2026-09-06 に指図が散布域を言葉から幾何へ落とした**
        //   (`shitakusa.shida.where[].kata` = 「築山の面」/「樹下」)。⛔ 範囲を実装で発明しない。
        //   ⛔ `clip`: **池の水面**と**州浜の砂利帯**(`suhama[].bare` = そこの草を消す所)は抜く。
        //   ⚠ 面積は生成器の「下草の散布域」の表と**同じ 0.1間 格子**で測る(表と食い違わせない)。
        var skRep = new System.Text.StringBuilder();
        {
            var sgrp = Group("Niwa/Shitakusa"); Clear(sgrp);
            var bands = SuhamaBands();
            float cellM2 = 0.1f * 0.1f * Grid.ken * Grid.ken;
            // ⭐⭐ **株の据え付けは `GroundY` でなく `TerrY`(実地形)**(2026-09-06 普請検査 fail)。
            //   ⚠ `GroundY` は**設計の解析面**で、heightmap は 2m 格子なので築山の曲率を持てない。
            //   解析面で据えた 61株中 19株が地形から**最大 +1.413m 浮いた**。
            //   ⛔ 「設計どおりの高さ」を株に渡さない — 草は現に在る地面に生える。
            // ⚠ **散らしの3値は指図の `shitakusa.shida` から読む**(⛔ 実装で決め打ちしない)。
            //   無ければ従前どおり(yaw 乱数 / 等倍 / 株間は部材の実寸)で建て、下の Wait で差し戻す。
            var stk = Has(n.g, "shitakusa") ? O(n.g["shitakusa"]) : null;
            var shd = (stk != null && Has(stk, "shida")) ? O(stk["shida"]) : null;
            bool yawRnd = !(shd != null && Has(shd, "yawRandom")) || F(shd["yawRandom"]) != 0f;
            float scLo = 1f, scHi = 1f;
            if (shd != null && Has(shd, "scaleJitter"))
            { var sj = A(shd["scaleJitter"]); if (sj != null && sj.Count == 2) { scLo = F(sj[0]); scHi = F(sj[1]); } }
            float pitchMin = (shd != null && Has(shd, "pitchMin")) ? F(shd["pitchMin"]) : 0f;
            if (shd == null || !Has(shd, "scaleJitter") || !Has(shd, "pitchMin") || !Has(shd, "yawRandom"))
                Wait("下草の散らし(`shitakusa.shida` の `yawRandom` / `scaleJitter` / `pitchMin`)が"
                   + "**指図に無い** — 従前どおり yaw 乱数・等倍・株間=部材の実寸で建てた。指図方へ");
            // ⚠ **株間は部材の実寸から決める**(⛔ 決め打ちしない・刈込と同じ作法)。
            //   ⚠ **撒く密度そのものは指図に無い**【U】— 下の Wait で差し戻す。
            float fw1, fh1, fw2, fh2;
            MeasureWH(EdoAssets.JG.Fern(1), out fw1, out fh1);
            MeasureWH(EdoAssets.JG.Fern(2), out fw2, out fh2);
            float pitchM = Mathf.Max(fw1, fw2);
            if (pitchM < 0.05f) { Wait("シダの部材が測れない: " + EdoAssets.JG.Fern(1)); pitchM = 0f; }
            if (pitchM > 0f) pitchM = Mathf.Max(pitchM, pitchMin);       // 指図の下限(有れば)
            float step = pitchM / Grid.ken;                              // [間]
            foreach (var r in ShitakusaRegions())
            {
                if (r.err != null) { Wait("下草 " + r.name + "(" + r.label + "): " + r.err); continue; }
                // ---- 面積(生成器 `shitakusa_stats` と同じ数え方。⚠ 樹冠の円は重なりを引かない=上限値)
                int cells = 0, wet = 0, gvl = 0, outs = 0;
                foreach (var q in SkCells(r))
                {
                    cells++;
                    bool inp = n.InPond(q.x, q.y);
                    if (inp) wet++;
                    else if (SkInBand(bands, q)) gvl++;
                    if (!n.Inside(q.x, q.y)) outs++;
                }
                float land = (cells - wet - gvl) * cellM2;
                skRep.Append("\n   " + r.label + "(" + r.name + "): 陸 " + land.ToString("F1")
                           + " m²(水 " + (cells > 0 ? 100f * wet / cells : 0f).ToString("F1")
                           + "% / 砂利 " + (cells > 0 ? 100f * gvl / cells : 0f).ToString("F1")
                           + "% / 庭の外 " + (cells > 0 ? 100f * outs / cells : 0f).ToString("F1") + "%)");
                if (outs > 0) Wait("下草 " + r.name + " が庭の矩形の外へ出る(" + outs + " 格子)");
                if (land <= 1e-6f || step <= 0f) continue;
                // ---- 散布。域の外接矩形を株間の格子で刻み、域の中 ∧ clip の外だけに据える
                float u0 = float.MaxValue, u1 = float.MinValue, v0 = float.MaxValue, v1 = float.MinValue;
                if (r.poly != null) foreach (var p in r.poly)
                {
                    u0 = Mathf.Min(u0, p.x); u1 = Mathf.Max(u1, p.x);
                    v0 = Mathf.Min(v0, p.y); v1 = Mathf.Max(v1, p.y);
                }
                foreach (var c in r.circ)
                {
                    u0 = Mathf.Min(u0, c.x - c.z); u1 = Mathf.Max(u1, c.x + c.z);
                    v0 = Mathf.Min(v0, c.y - c.z); v1 = Mathf.Max(v1, c.y + c.z);
                }
                int k9 = 0;
                for (float u = u0; u <= u1 + 1e-9f; u += step)
                    for (float v = v0; v <= v1 + 1e-9f; v += step)
                    {
                        // ⛔ 格子のまま並べない(機械で置いた列に見える)— 株間の ±25% で散らす
                        Vector2 q = new Vector2(u + ((float)rnd.NextDouble() - 0.5f) * step * 0.5f,
                                                v + ((float)rnd.NextDouble() - 0.5f) * step * 0.5f);
                        if (!SkIn(r, q.x, q.y)) continue;
                        if (!n.Inside(q.x, q.y)) continue;
                        if (n.InPond(q.x, q.y)) continue;                 // ⛔ 水面
                        if (SkInBand(bands, q)) continue;                 // ⛔ 州浜の砂利帯
                        string path = EdoAssets.JG.Fern((k9 % 2) + 1);
                        if (!Exists(path)) { Wait("シダの部材が無い: " + path); break; }
                        Vector2 w = Wu(q.x, q.y);
                        float gy9 = TerrY(w.x, w.y);
                        if (float.IsNaN(gy9)) { Wait("地形が引けない(下草 " + r.name + ")"); break; }
                        float sc9 = scLo + (float)rnd.NextDouble() * (scHi - scLo);
                        var go = EdoBuild.Place(path, new Vector3(w.x, gy9, w.y),
                                                yawRnd ? (float)rnd.NextDouble() * 360f : 0f,
                                                Vector3.one * sc9, sgrp, r.name + "_" + k9);
                        if (go != null) { k9++; shida++; }
                    }
                skRep.Append(" → " + k9 + " 株");
            }
            Wait("下草の**撒く密度(株間)が指図に無い**【U】— 域は `shitakusa.shida.where` の幾何どおりだが、"
               + "株間は**部材の実寸**(シダの足 " + pitchM.ToString("F2") + "m)を採った。"
               + "⇒ 密度を指図の値にしたいなら指図方へ(`shida` に株間か被覆率が要る)");
            Wait("コケ・芝・州浜の砂利は**スプラット**(指図 `shitakusa.koke`)— 地表仕上げの工程が要る");
            Wait("水際の帯(`shitakusa.mizugiwa` 水面 −0.35〜+0.80m の NatureManufacture Meadow を"
               + "交差2本1組)は**まだ据えていない** — 指図にはあるが今回の3件の範囲外");
        }
        return "植栽: 高中木 " + trees + " 本 / 刈込 " + kari + " 株 / シダ " + shida + " 株"
             + skRep.ToString();
    }

    // ------------------------------------------------------------------ 下草の散布域(⛔ 言葉でなく幾何)
    /// <summary>下草の散布域。指図 `shitakusa.shida.where` の `kata` から**毎回組み直す**
    /// (⛔ 範囲の数値を指図に写さない・⛔ 実装で発明しない)。築山を動かせば域も動く。</summary>
    class SkRegion
    {
        public string name, label, kata, err;
        public Vector2[] poly;                              // 「築山の面」= 半楕円 (u,v)
        public List<Vector3> circ = new List<Vector3>();    // 「樹下」= 樹冠の円 (u, v, r[間])
    }

    static List<SkRegion> ShitakusaRegions()
    {
        var n = NiwaModel;
        var res = new List<SkRegion>();
        var st = Has(n.g, "shitakusa") ? O(n.g["shitakusa"]) : null;
        var sd = (st != null && Has(st, "shida")) ? O(st["shida"]) : null;
        var wl = (sd != null && Has(sd, "where")) ? A(sd["where"]) : null;
        if (wl == null) return res;
        var tk = new Dictionary<string, Dictionary<string, object>>();
        foreach (var o in A(n.g["tsukiyama"])) { var q = O(o); tk[S(q["name"])] = q; }
        foreach (var o in wl)
        {
            var w = O(o);
            if (w == null)
            {
                res.Add(new SkRegion { name = "?", label = "?",
                    err = "散布域が文字列のまま — 幾何へ落としていない" });
                continue;
            }
            var r = new SkRegion { name = S(w["name"]), label = S(w["label"]), kata = S(w["kata"]) };
            if (r.kata == "築山の面")
            {
                Dictionary<string, object> t = null;
                tk.TryGetValue(S(w["of"]) ?? "", out t);
                if (t == null || !Has(t, "dU"))
                    r.err = "築山 " + S(w["of"]) + " が `tsukiyama` に無い(または楕円でない)";
                else
                {
                    // 楕円 footprint の `side` 側の半分(稜線 u=uc → 裾 → 稜線)
                    float rU = F(t["dU"]) / 2f, rV = F(t["dV"]) / 2f;
                    string sd2 = Has(w, "side") ? S(w["side"]) : "+u";
                    float sg = (sd2 != null && sd2.StartsWith("-")) ? -1f : 1f;
                    var pts = new Vector2[41];
                    for (int i = 0; i <= 40; i++)
                    {
                        float th = Mathf.PI * i / 40f;
                        pts[i] = new Vector2(F(t["u"]) + sg * rU * Mathf.Sin(th),
                                             F(t["v"]) + rV * Mathf.Cos(th));
                    }
                    r.poly = pts;
                }
            }
            else if (r.kata == "樹下")
            {
                string sp = S(w["species"]), sz = S(w["size"]);
                foreach (var o2 in A(n.g["shokusai"]))
                {
                    var sk = O(o2);
                    string sp2 = S(sk["species"]);
                    if (sp == null || sp2 == null || !sp2.StartsWith(sp)) continue;
                    if (S(sk["size"]) != sz) continue;
                    float rad = CrownR(sk);
                    if (rad <= 0f) { r.err = "樹冠が測れない: " + sp + " " + sz; break; }
                    foreach (var p0 in A(sk["at"]))
                    { var p = A(p0); r.circ.Add(new Vector3(F(p[0]), F(p[1]), rad)); }
                }
                if (r.err == null && r.circ.Count == 0)
                    r.err = "`shokusai` に「" + sp + " " + sz + "」の層が無い";
            }
            else r.err = "知らない `kata` " + r.kata + " — 語彙に無い値では何も撒かない";
            res.Add(r);
        }
        return res;
    }

    /// <summary>樹冠の半径[間]。⛔ 呼び寸法を使わない — **据える部材の実メッシュ**の
    /// 平面の大きい方 ÷2 × `scale`(生成器が `docs/asset-index.tsv` から引くのと同じ値)。
    /// ⛔ 樹冠幅を指図へ写さない。</summary>
    static float CrownR(Dictionary<string, object> sk)
    {
        string api = S(sk["asset"]);
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
        if (a.StartsWith("JG.Boxwood")) return EdoAssets.JG.Boxwood(variant);
        if (a.StartsWith("JG.Fern")) return EdoAssets.JG.Fern(variant);
        return null;
    }
    static string JGPine(string size, int i)
    {
        i = Mathf.Clamp(i, 1, 3);
        if (size == "Big") return i == 1 ? EdoAssets.JG.PineBig01 : (i == 2 ? EdoAssets.JG.PineBig02 : EdoAssets.JG.PineBig03);
        return EdoAssets.JG.PineMid01.Replace("Mid_Green_01", "Mid_Green_0" + i);
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
}
