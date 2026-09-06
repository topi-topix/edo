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
    /// <summary>汀線を frm→to へ辿った折れ線(1 始まり・巡回)。</summary>
    static List<Vector2> ShoreWalk(int frm, int to)
    {
        var n = NiwaModel; int N = n.pond.Length;
        var outp = new List<Vector2>();
        int i = frm;
        for (int k = 0; k < N + 1; k++)
        {
            outp.Add(Sh(i));
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

    /// <summary>ハイトマップの窓を開いて fn で書き、閉じる。⛔ **区画の外と庭の矩形の外は触らない**。</summary>
    static string EditNiwaHeights(Func<float, float, float> fn, string label)
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
        int cells = 0; double up = 0, dn = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            float wx = tp.x + (x0 + x) * ts.x / (hres - 1);
            float wz = tp.z + (z0 + z) * ts.z / (hres - 1);
            if (!EdoGeom.PIP(P, new Vector2(wx, wz))) continue;            // ⛔ 区画の外
            var g = Grid.L(new Vector2(wx, wz));
            if (!n.Inside(g.x, g.y)) continue;                              // ⛔ 庭の矩形の外
            float y = fn(g.x, g.y);
            if (float.IsNaN(y)) continue;
            float cur = H[z, x] * ts.y + tp.y;
            if (y > cur) up += y - cur; else dn += cur - y;
            H[z, x] = (y - tp.y) / ts.y; cells++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        float cell = ts.x / (hres - 1); double a = cell * cell;
        return string.Format("{0}: cells={1} 盛{2:F0}m³ 切{3:F0}m³", label, cells, up * a, dn * a);
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
        string r = EditNiwaHeights((u, v) => n.Ground(u, v), "奥庭の土工(池床+築山+土手)");
        if (!Marked("6a_niwa_dokou")) Mark("6a_niwa_dokou", r);

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
    static string Niwa_B_Gogan()
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
            float topY = F(rg["topY"]);
            float[] dias = new float[] { 0.034f, 0.043f, 0.052f };
            int cnt = Mathf.Max(1, Mathf.RoundToInt(L / Mathf.Max(0.02f, pitch)));
            for (int i = 0; i < cnt; i++)
            {
                float dia = dias[rnd.Next(dias.Length)];
                string path = EdoAssets.Own.Rangui(dia);
                if (!Exists(path)) { Wait("乱杭の部材が無い: " + path); break; }
                Vector2 dir;
                Vector2 gp = LerpLine(line, (i + 0.5f) / cnt, out dir);
                Vector2 wpt = Wu(gp.x, gp.y);
                var go = EdoBuild.Place(path, new Vector3(wpt.x, topY, wpt.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one, grp,
                                        S(rg["name"]) + "_" + i);
                if (go != null) ran++;
            }
        }
        return "護岸: 石 " + stones + " / 州浜の平石 " + su + " / 乱杭 " + ran;
    }

    // ---- ③水尻(閾・吐き口・落とし溝・受け石)
    /// <summary>水尻。⭐ 2026-09-06 に部材が焼けた。ピボットは部材ごとに違う(部材方の docstring):
    ///   閾 = **閾の芯・天端**(⇒ `position.y = shiki.sill`)/ 吐き口 = **樋の芯・吐き口の面**
    ///   (⇒ `position.y = umeToi.outY`・**+Z = 流れの下流**)/ 落とし溝 = **スパンの中心・地盤**
    ///   (**+X = 流れの向き**)。⛔ **埋樋の本体は焼いていない**(土被り 0.30 以上で地上から見えない)。</summary>
    static string Niwa_C_Mizushiri()
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

        // ④ 受け石(玉石の浸透枡)。⛔ 新造せず在庫の小径の立石を**伏せて**3種混ぜる。
        //    ⚠ **個数と配置は指図に無い**(`uke` は「玉石の浸透枡(受け石)」の一語)。
        //      部材方の申し送りが名指しした variant 1..3 のとおり 3個だけ据えた【U】。
        if (haveEnd)
        {
            for (int i = 1; i <= 3; i++)
            {
                string path = EdoAssets.Own.Tateishi("S", i);
                if (!Exists(path)) { Wait("受け石の部材が無い: " + path); break; }
                float ang = (i - 1) * 120f + 20f;
                Vector2 c = endPt + new Vector2(Mathf.Cos(ang * Mathf.Deg2Rad), Mathf.Sin(ang * Mathf.Deg2Rad)) * 0.45f;
                float gy = GroundY(c.x, c.y);
                var go = EdoBuild.Place(path, new Vector3(c.x, gy, c.y),
                                        (float)rnd.NextDouble() * 360f, Vector3.one * 0.55f, grp, "Ukeishi_" + i);
                if (go == null) continue;
                // **伏せる** — 丈 1.0 に正規化した立石を寝かせ、半分ほど埋める
                go.transform.rotation = go.transform.rotation * Quaternion.Euler(90f, 0f, 0f);
                var bb = EdoBuild.RB(go);
                go.transform.position += new Vector3(0f, gy - bb.center.y, 0f);
                made++;
            }
            sb.Append("受け石3 ");
            Wait("水尻の受け石(玉石の浸透枡)— **個数と配置が指図に無い**"
               + "(`mizushiri.otoshimizo.uke` は語だけ)。部材方の申し送りの variant 1..3 に合わせて"
               + " 3個を終点のまわり 0.45m へ伏せた【U】→ 数と広がりは指図方へ差し戻し");
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

        // 沓脱石。⚠⚠ **指図が名指しする丈の呼び名が部材に無い。**
        //   `kutsunugi[].asset` は `Own.Tateishi("Big", 1..3)` だが、立石の丈は **S / M / L** の3種で
        //   "Big" は**樹木の呼び名**(`Own.Jouryoku("Big", i)`)。⇒ どの丈を寝かせ、
        //   1.4 × 0.95m の足形へどう当てるかは**設計判断**なので、⛔ 決め打ちせず据えない。
        foreach (var o in A(n.g["kutsunugi"]))
        {
            var kg = O(o);
            string api2 = Has(kg, "asset") ? S(kg["asset"]) : null;
            string path = ResolveNiwaApi(api2, 1);
            if (path == null || !Exists(path))
            {
                Wait("沓脱石 " + S(kg["name"]) + "(" + F(kg["L"]).ToString("F2") + "×"
                   + F(kg["W"]).ToString("F2") + "m・天端 " + F(kg["topY"]).ToString("F2")
                   + ")の部材が引けない: " + (api2 ?? "(asset 無し)")
                   + " — 立石の丈は **S(0.60×1.00×0.45)/ M(0.70×1.40×0.50)/ L(0.80×2.10×0.60)** の3種で、"
                   + "\"Big\" は樹木の呼び名。⛔ どれを寝かせて 1.4×0.95 に当てるかは設計判断なので据えない"
                   + " → 呼び出し元(普請奉行)の裁定へ");
                continue;
            }
            // ⛔ 「石は立てる」を沓脱石に当てない — **寝かせて天端を水平に**据える(topY)。
            Vector2 w = Wu(F(kg["u"]), F(kg["v"]));
            var go = EdoBuild.Place(path, new Vector3(w.x, F(kg["topY"]), w.y), YawAlongU(),
                                    Vector3.one, grp, S(kg["name"]));
            if (go == null) continue;
            go.transform.rotation = go.transform.rotation * Quaternion.Euler(90f, 0f, 0f);
            var bb0 = EdoBuild.RB(go);
            go.transform.position += new Vector3(0f, F(kg["topY"]) - bb0.max.y, 0f);
            made++;
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

    // ---- ⑧植栽・刈込・下草
    static string Niwa_H_Shokusai()
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

        // 下草(シダ)。指図 `shitakusa.shida.where` は場所を言葉で指すだけなので、
        // ⛔ 位置を発明せず、**モミジの根方**だけ(位置が指図で定まる)に据える。
        {
            var sgrp = Group("Niwa/Shitakusa"); Clear(sgrp);
            foreach (var o in A(n.g["shokusai"]))
            {
                var sk = O(o);
                if (S(sk["species"]) != "イロハモミジ") continue;
                var at = A(sk["at"]);
                for (int i = 0; i < at.Count; i++)
                {
                    var p = A(at[i]);
                    for (int j = 0; j < 3; j++)
                    {
                        float ang = (float)rnd.NextDouble() * Mathf.PI * 2f;
                        float rr = 0.35f + (float)rnd.NextDouble() * 0.35f;
                        Vector2 q = new Vector2(F(p[0]) + Mathf.Cos(ang) * rr / Grid.ken,
                                                F(p[1]) + Mathf.Sin(ang) * rr / Grid.ken);
                        Vector2 w = Wu(q.x, q.y);
                        string path = EdoAssets.JG.Fern((j % 2) + 1);
                        if (!Exists(path)) { Wait("シダの部材が無い: " + path); break; }
                        var go = EdoBuild.Place(path, new Vector3(w.x, GroundY(w.x, w.y), w.y),
                                                (float)rnd.NextDouble() * 360f, Vector3.one, sgrp,
                                                "Shida_" + shida);
                        if (go != null) shida++;
                    }
                }
            }
            Wait("下草: 指図 `shitakusa.shida.where` は「築山A1の北面」「稲荷の社叢」を**言葉で**指すだけで"
               + "座標が無い。⛔ 位置を発明しないので、根方の位置が定まる**モミジ**の周りにだけ据えた"
               + " → 残り2箇所は指図方へ差し戻し(散布域の矩形か点列が要る)");
            Wait("コケ・芝・州浜の砂利は**スプラット**(指図 `shitakusa.koke`)— 地表仕上げの工程が要る");
        }
        return "植栽: 高中木 " + trees + " 本 / 刈込 " + kari + " 株 / シダ " + shida + " 株";
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
    /// <summary>`Own.Jouryoku("Big", i)` の "Big" を取り出す。</summary>
    static string ArgSize(string api)
    {
        int a = api.IndexOf('"');
        if (a < 0) return "Mid";
        int b = api.IndexOf('"', a + 1);
        return b > a ? api.Substring(a + 1, b - a - 1) : "Mid";
    }
}
