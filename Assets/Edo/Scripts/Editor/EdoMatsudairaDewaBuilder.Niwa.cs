// 松平出羽守上屋敷 — 庭の工程(池・築山・水の系・石組・点景・滝見口)。
// ⭐ 2026-09-02 新設(ユーザー裁定A: 指図の仕上げと実装の骨組みを並行する)。
//
// ⛔ **この部分クラスは指図 `docs/Sashizu/matsudaira_dewa_sashizu.json` を読むだけで、値を持たない。**
//   検図方(2026-09-02 第4次【高7】)の指摘: `sensui` / `mizu` / `tenkei` / `routes` / `plantRule` /
//   `viewpoints` / `tsukiyama` / `gardenSections` / `nakajikiriRule` / `chains` / `fuchi` / `ishigaki` /
//   `edgeProfiles` の 13 キーがビルダーで**参照 0 回**で、池・築山・点景・園路には Stage 自体が無かった。
//   ⛔ そのため `CheckScene` は庭が1本も建っていなくても「突き合わせ 0 件」を出していた。
//
// 工程の名は指図 `matsudaira_dewa_kosho.md`「実装の順序(Stage)」の表に合わせる:
//   1b 築山の盛土(非冪等) / 6a 御泉水を掘る(非冪等・⛔ 掲示板起票の後) / 6a' 掘削後の隆起(非冪等)
//   6b 水の系 / 6c 岩屋・石組・護岸 / 6d 点景と垣 / 6e 滝見口  — 6b〜6e は冪等(地形を触らない。⚠ 6b の野筋だけ非冪等)
//
// ⛔ **非冪等の工程は active なマーカーで二重実行を止める**(CLAUDE.md「MCP タイムアウト後の再送で多重実行」)。
// ⛔ **部材が在庫に無い種別は置かない** — 数えて報告するだけ(⛔ プリミティブの代用は規則10 の精神に反する)。
//   在庫の穴(2026-09-02 目録で確認): 織部灯籠・蹲踞・縁先手水鉢・石橋・鳥居(単体)・建仁寺垣・生垣。
//   → `edo-zaiko` で再確認のうえ `edo-buzai` へ。ここでは `tenkei[].api` が解けるものだけ置く。

using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static partial class EdoMatsudairaDewaBuilder
{
    // ------------------------------------------------------------------ 共通
    static bool HasKey(Dictionary<string, object> d, string k) { return d != null && d.ContainsKey(k) && d[k] != null; }
    static string StrOf(Dictionary<string, object> d, string k) { return HasKey(d, k) ? d[k].ToString() : null; }

    /// <summary>非冪等の工程の実行済みマーカー(⛔ active にする — `GameObject.Find` は非アクティブを見つけない)。</summary>
    static bool Marked(string stage)
    {
        var g = Group("Niwa/_markers");
        return g.Find(stage) != null;
    }
    static void Mark(string stage, string note)
    {
        var g = Group("Niwa/_markers");
        var go = new GameObject(stage); go.transform.SetParent(g, false);
        go.name = stage; go.SetActive(true);
        Undo.RegisterCreatedObjectUndo(go, "marker");
        Debug.Log("[Matsudaira] マーカー " + stage + " — " + note);
    }

    /// <summary>ハイトマップの窓を開いて fn で書き、閉じる。fn は (x,z)世界座標 と 現在の高さ を受け、新しい高さか NaN(不変)を返す。</summary>
    static string EditHeights(Vector2 mn, Vector2 mx, Func<float, float, float, float> fn, string label)
    {
        var t = Terrain.activeTerrain; var td = t.terrainData;
        int hres = td.heightmapResolution;
        Vector3 tp = t.transform.position, ts = td.size;
        Func<float, int> IX = wx => Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / ts.x * (hres - 1)), 0, hres - 1);
        Func<float, int> IZ = wz => Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / ts.z * (hres - 1)), 0, hres - 1);
        Func<int, float> WX = ix => tp.x + ix * ts.x / (hres - 1);
        Func<int, float> WZ = iz => tp.z + iz * ts.z / (hres - 1);
        int x0 = IX(mn.x - 2f), x1 = IX(mx.x + 2f), z0 = IZ(mn.y - 2f), z1 = IZ(mx.y + 2f);
        int w = x1 - x0 + 1, h = z1 - z0 + 1;
        var H = td.GetHeights(x0, z0, w, h);
        var P = Poly;
        int n = 0; double up = 0, dn = 0;
        for (int z = 0; z < h; z++) for (int x = 0; x < w; x++)
        {
            float wx = WX(x0 + x), wz = WZ(z0 + z);
            if (!EdoGeom.PIP(P, new Vector2(wx, wz))) continue;              // ⛔ 区画の外は触らない
            float cur = H[z, x] * ts.y + tp.y;
            float y = fn(wx, wz, cur);
            if (float.IsNaN(y)) continue;
            if (y > cur) up += y - cur; else dn += cur - y;
            H[z, x] = (y - tp.y) / ts.y; n++;
        }
        td.SetHeightsDelayLOD(x0, z0, H); td.SyncHeightmap();
        float cell = ts.x / (hres - 1); double a = cell * cell;
        return string.Format("{0}: cells={1} 盛{2:F0}m³ 切{3:F0}m³", label, n, up * a, dn * a);
    }

    static float TerrainY(float wx, float wz)
    {
        var t = Terrain.activeTerrain;
        return t.SampleHeight(new Vector3(wx, 0, wz)) + t.transform.position.y;
    }

    /// <summary>指図の (u,v)[間] 折れ線 → 世界座標。</summary>
    static List<Vector2> UVLine(object pts)
    {
        var f = Grid; var outl = new List<Vector2>();
        foreach (var q in A(pts)) { var p = A(q); outl.Add(f.W(F(p[0]), F(p[1]))); }
        return outl;
    }

    static bool InPoly(List<Vector2> P, Vector2 q)
    {
        bool c = false; int n = P.Count;
        for (int i = 0; i < n; i++)
        {
            Vector2 a = P[i], b = P[(i + 1) % n];
            if ((a.y > q.y) != (b.y > q.y) && q.x < a.x + (b.x - a.x) * (q.y - a.y) / (b.y - a.y)) c = !c;
        }
        return c;
    }
    static float DistLine(List<Vector2> L, Vector2 q, bool closed, out float sAlong)
    {
        float best = float.MaxValue, acc = 0f; sAlong = 0f;
        int n = closed ? L.Count : L.Count - 1;
        for (int i = 0; i < n; i++)
        {
            Vector2 a = L[i], b = L[(i + 1) % L.Count]; Vector2 d = b - a; float L2 = Mathf.Max(1e-9f, d.sqrMagnitude);
            float t = Mathf.Clamp01(Vector2.Dot(q - a, d) / L2);
            float dd = Vector2.Distance(q, a + d * t);
            if (dd < best) { best = dd; sAlong = acc + Mathf.Sqrt(L2) * t; }
            acc += Mathf.Sqrt(L2);
        }
        return best;
    }

    static Dictionary<string, object> Sensui { get { return O(D["sensui"]); } }
    static Dictionary<string, object> Pond { get { return O(Sensui["pond"]); } }

    // ------------------------------------------------------------------ 1b 築山の盛土(非冪等)
    [MenuItem("Edo/松平出羽守上屋敷/1b 築山の盛土")]
    public static void Stage1bMenu() { Debug.Log("[Matsudaira] " + Stage1b_Tsukiyama()); }
    public static string Stage1b_Tsukiyama()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        if (Marked("1b_tsukiyama")) return "⛔ 1b は実行済み(マーカー Niwa/_markers/1b_tsukiyama)。非冪等なので二度流さない";
        if (!HasKey(D, "tsukiyama")) return "指図に tsukiyama が無い";
        Stage0_Backup();
        var f = Grid; var sb = new System.Text.StringBuilder();
        foreach (var o in A(D["tsukiyama"]))
        {
            var tk = O(o);
            // 指図: 頂 (u,v)・天端 topY・裾 skirt[](u,v の輪郭)。盛土の面 = 頂から裾へ直線(裾では自然地盤に一致)
            Vector2 top = f.W(F(tk["u"]), F(tk["v"]));
            // ⚠ 指図は頂の標高を `y` で持つ(`_tsukiyama`「`u,v,y` = 頂の位置と**標高**」)。
            //    2026-09-04: ここが `topY` 決め打ちで KeyNotFoundException になっていた(棟梁)。
            float topY = HasKey(tk, "y") ? F(tk["y"]) : F(tk["topY"]);
            var skirt = UVLine(tk["skirt"]);
            Vector2 mn = top, mx = top;
            foreach (var q in skirt) { mn = Vector2.Min(mn, q); mx = Vector2.Max(mx, q); }
            string r = EditHeights(mn, mx, (wx, wz, cur) =>
            {
                var q = new Vector2(wx, wz);
                if (!InPoly(skirt, q)) return float.NaN;
                // 頂→裾: 頂からその方位の裾までの距離で正規化した直線。裾の高さ = その点の現況(自然地盤)
                float s; float dSkirt = DistLine(skirt, q, true, out s);
                float dTop = Vector2.Distance(q, top);
                float tt = dTop / Mathf.Max(1e-6f, dTop + dSkirt);          // 0=頂 … 1=裾
                float y = topY + (cur - topY) * tt;
                return Mathf.Max(cur, y);                                   // 盛るだけ(切らない)
            }, "築山 " + StrOf(tk, "name"));
            sb.AppendLine(r);
        }
        Mark("1b_tsukiyama", sb.ToString());
        return sb.ToString();
    }

    // ------------------------------------------------------------------ 6a 御泉水を掘る(非冪等)
    [MenuItem("Edo/松平出羽守上屋敷/6a 御泉水を掘る(⛔ 掲示板起票のあと)")]
    public static void Stage6aMenu() { Debug.Log("[Matsudaira] " + Stage6a_Sensui()); }
    public static string Stage6a_Sensui()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        if (Marked("6a_sensui")) return "⛔ 6a は実行済み(マーカー)。⛔ Recarve を二度呼ぶと岬と中島が平らに戻る";
        // ⛔ `WaterBaker` の snap 矩形 320×320m が土井 6/10 点・岡部 4/13 点に掛かる(`_pending.snapKiten`)。
        //    起票して両セッションへ連絡してから、マーカー `Niwa/_markers/6a_snap_notified` を手で作る。
        if (!Marked("6a_snap_notified"))
            return "⛔ 掲示板への起票と土井・岡部への連絡がまだ(`_pending.snapKiten`)。済んだら active なマーカー Niwa/_markers/6a_snap_notified を作ること";
        if (!HasKey(D, "sensui")) return "指図に sensui が無い";
        Stage0_Backup();
        var pond = Pond; var baker = O(Sensui["baker"]);
        var outl = new List<Vector3>();
        float wy = F(pond["waterY"]);
        foreach (var q in UVLine(pond["outline"])) outl.Add(new Vector3(q.x, wy, q.y));
        var wb = WaterBaker.Create(outl, F(pond["depth"]));
        if (wb == null) return "⛔ WaterBaker.Create が null";
        // ⛔ Create は waterY を「汀の中央値 −0.3」に自動で決める(`sensui.baker._api`)。指図の値を入れ直して Recarve をもう一度
        wb.waterY = wy;
        wb.verticalWalls = HasKey(baker, "verticalWalls") && Convert.ToBoolean(baker["verticalWalls"]);
        wb.levelFloor = HasKey(baker, "levelFloor") && Convert.ToBoolean(baker["levelFloor"]);
        wb.raiseBanks = HasKey(baker, "raiseBanks") && Convert.ToBoolean(baker["raiseBanks"]);
        if (HasKey(baker, "bankWidth")) wb.bankWidth = F(baker["bankWidth"]);
        wb.name = StrOf(pond, "name") ?? "P_Sensui";
        wb.transform.SetParent(Group("Niwa/Sensui"), true);
        WaterBaker.Recarve(wb);
        Mark("6a_sensui", string.Format("waterY {0:F2} depth {1:F2} verticalWalls {2}", wy, F(pond["depth"]), wb.verticalWalls));
        return string.Format("御泉水 {0}: 汀 {1} 点 / 水面 {2:F2} / 底 {3:F2}", wb.name, outl.Count, wy, wy - F(pond["depth"]));
    }

    // ------------------------------------------------------------------ 6a' 掘削後の隆起(非冪等)
    [MenuItem("Edo/松平出羽守上屋敷/6a' 岬・中島の隆起と澪筋")]
    public static void Stage6a2Menu() { Debug.Log("[Matsudaira] " + Stage6a2_Mounds()); }
    public static string Stage6a2_Mounds()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        if (!Marked("6a_sensui")) return "⛔ 6a(掘削)がまだ — 隆起は Recarve の後でないと平らに戻される";
        if (Marked("6a2_mounds")) return "⛔ 6a' は実行済み(マーカー)";
        var sb = new System.Text.StringBuilder();
        var pond = Pond; float wy = F(pond["waterY"]);
        var shore = UVLine(pond["outline"]);
        // 岬: 汀線の点 #a-#b-#c の三角を天端 topY へ(裾は汀線で水面に一致)
        if (HasKey(Sensui, "mounds"))
        {
            foreach (var o in A(O(Sensui["mounds"])["items"]))
            {
                var m = O(o); float topY = F(m["topY"]);
                var tri = new List<Vector2>();
                if (HasKey(m, "shoreIdx")) foreach (var i in A(m["shoreIdx"])) tri.Add(shore[Convert.ToInt32(i)]);
                if (tri.Count < 3) { sb.AppendLine("岬 " + StrOf(m, "name") + ": shoreIdx が無い(指図方へ)"); continue; }
                Vector2 c = Vector2.zero; foreach (var q in tri) c += q; c /= tri.Count;
                Vector2 mn = tri[0], mx = tri[0]; foreach (var q in tri) { mn = Vector2.Min(mn, q); mx = Vector2.Max(mx, q); }
                sb.AppendLine(EditHeights(mn, mx, (wx, wz, cur) =>
                {
                    var q = new Vector2(wx, wz); if (!InPoly(tri, q)) return float.NaN;
                    float s; float dEdge = DistLine(tri, q, true, out s); float dC = Vector2.Distance(q, c);
                    float tt = dC / Mathf.Max(1e-6f, dC + dEdge);           // 0=中心 … 1=縁(汀)
                    return Mathf.Max(cur, topY + (wy - topY) * tt);
                }, "岬 " + StrOf(m, "name")));
            }
        }
        // 中島: 輪郭の中を天端 topY(縁は水面)
        if (HasKey(Sensui, "island"))
        {
            var isl = O(Sensui["island"]); var ring = UVLine(isl["outline"]); float topY = F(isl["topY"]);
            Vector2 c = Vector2.zero; foreach (var q in ring) c += q; c /= ring.Count;
            Vector2 mn = ring[0], mx = ring[0]; foreach (var q in ring) { mn = Vector2.Min(mn, q); mx = Vector2.Max(mx, q); }
            sb.AppendLine(EditHeights(mn, mx, (wx, wz, cur) =>
            {
                var q = new Vector2(wx, wz); if (!InPoly(ring, q)) return float.NaN;
                float s; float dEdge = DistLine(ring, q, true, out s); float dC = Vector2.Distance(q, c);
                float tt = dC / Mathf.Max(1e-6f, dC + dEdge);
                return Mathf.Max(cur, topY + (wy - topY) * tt);
            }, "中島 " + StrOf(isl, "name")));
        }
        // 澪筋: 池底を点列に沿って floorY まで掘り下げる(幅は wAt[i]×wScale)
        if (HasKey(Sensui, "miosuji"))
        {
            var ms = O(Sensui["miosuji"]); var line = UVLine(ms["pts"]); float fy = F(ms["floorY"]);
            var wAt = A(ms["wAt"]); float ws = HasKey(ms, "wScale") ? F(ms["wScale"]) : 1f; float ken = F(O(D["const"])["ken"]);
            Vector2 mn = line[0], mx = line[0]; foreach (var q in line) { mn = Vector2.Min(mn, q); mx = Vector2.Max(mx, q); }
            float pad = 0f; foreach (var w0 in wAt) pad = Mathf.Max(pad, F(w0) * ws * ken);
            sb.AppendLine(EditHeights(mn - Vector2.one * pad, mx + Vector2.one * pad, (wx, wz, cur) =>
            {
                var q = new Vector2(wx, wz); float s; float d = DistLine(line, q, false, out s);
                // その位置の幅: 弧長 s に最も近い点の wAt
                int k = 0; float acc = 0, best = float.MaxValue;
                for (int i = 0; i < line.Count; i++) { if (i > 0) acc += Vector2.Distance(line[i - 1], line[i]); if (Mathf.Abs(acc - s) < best) { best = Mathf.Abs(acc - s); k = i; } }
                float half = F(wAt[Mathf.Min(k, wAt.Count - 1)]) * ws * ken / 2f;
                if (d > half) return float.NaN;
                return Mathf.Min(cur, fy);
            }, "澪筋 " + StrOf(ms, "name")));
        }
        Mark("6a2_mounds", sb.ToString());
        return sb.ToString();
    }

    // ------------------------------------------------------------------ 6b 水の系(遣水の野筋だけ非冪等)
    [MenuItem("Edo/松平出羽守上屋敷/6b 水の系(枡・遣水の野筋・滝)")]
    public static void Stage6bMenu() { Debug.Log("[Matsudaira] " + Stage6b_Mizu()); }
    public static string Stage6b_Mizu()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        if (!HasKey(D, "mizu")) return "指図に mizu が無い";
        var sb = new System.Text.StringBuilder(); var f = Grid; var rnd = new System.Random(1856);
        var grp = Group("Niwa/Mizu"); Clear(grp);
        var mz = O(D["mizu"]); int placed = 0, noPart = 0;
        // 節点(枡・堰)— `api` があれば置く。無ければ数えるだけ(⛔ 代用しない)
        foreach (var o in A(mz["nodes"]))
        {
            var nd = O(o); if (!HasKey(nd, "u") || !HasKey(nd, "v")) continue;
            string api = ResolveApi(StrOf(nd, "api"));
            if (api == null) { noPart++; continue; }
            Vector2 w = f.W(F(nd["u"]), F(nd["v"]));
            EdoBuild.Place(api, new Vector3(w.x, TerrainY(w.x, w.y), w.y), 0f, Vector3.one, grp, "MZ_" + StrOf(nd, "id"));
            placed++;
        }
        // 遣水の野筋: 27.0 の面を幅 w・深さ depth の浅い谷に掘る(非冪等)
        if (HasKey(Sensui, "yarimizu") && !Marked("6b_nosuji"))
        {
            var ym = O(Sensui["yarimizu"]); var line = UVLine(ym["pts"]); var ns = O(ym["nosuji"]);
            float ken = F(O(D["const"])["ken"]); float half = F(ns["w"]) * ken / 2f;
            var dep = A(ns["depth"]); float d0 = F(dep[0]), d1 = F(dep[1]);
            var fy = A(ym["floorY"]); float y0 = F(fy[0]), y1 = F(fy[1]);
            float total = 0f; for (int i = 1; i < line.Count; i++) total += Vector2.Distance(line[i - 1], line[i]);
            Vector2 mn = line[0], mx = line[0]; foreach (var q in line) { mn = Vector2.Min(mn, q); mx = Vector2.Max(mx, q); }
            Stage0_Backup();
            sb.AppendLine(EditHeights(mn - Vector2.one * half, mx + Vector2.one * half, (wx, wz, cur) =>
            {
                var q = new Vector2(wx, wz); float s; float d = DistLine(line, q, false, out s);
                if (d > half) return float.NaN;
                float tt = s / Mathf.Max(1e-6f, total);
                float floor = y0 + (y1 - y0) * tt;                          // 流れの底(指図の floorY)
                float depth = d0 + (d1 - d0) * tt;
                float prof = floor + depth * (d / half) * (d / half);       // 放物線の谷(⛔ 溝にしない)
                return Mathf.Min(cur, prof);
            }, "遣水の野筋 " + StrOf(ym, "name")));
            Mark("6b_nosuji", "野筋 w=" + ns["w"]);
        }
        // 台地端の滝(三段)・越流堰・樋: 部材の api が無い限り置かない(数える)
        int tiers = HasKey(mz, "takiDaichi") ? A(O(mz["takiDaichi"])["tiers"]).Count : 0;
        sb.AppendLine(string.Format("水の系: 節点 {0} 置いた / 部材なしで置かず {1} / 滝の段 {2}(部材なし・据えず)/ 樋は地下(据えず)",
                                    placed, noPart, tiers));
        return sb.ToString();
    }

    // ------------------------------------------------------------------ 6c 岩屋・石組・護岸(冪等)
    [MenuItem("Edo/松平出羽守上屋敷/6c 岩屋・石組・護岸")]
    public static void Stage6cMenu() { Debug.Log("[Matsudaira] " + Stage6c_Ishigumi()); }
    public static string Stage6c_Ishigumi()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        if (!Marked("6a_sensui")) return "⛔ 6a(掘削)がまだ — 護岸は実地形の汀から測る";
        var sb = new System.Text.StringBuilder(); var f = Grid; var rnd = new System.Random(1856);
        var grp = Group("Niwa/Ishigumi"); Clear(grp);
        var pond = Pond; float wy = F(pond["waterY"]);
        var shore = UVLine(pond["outline"]);
        // 石組(主石組・岩屋ほか)— `stones[]` を持つ点景を据える。見え丈 show・1/3 埋め(`gogan.bury`)
        var gogan = O(Sensui["gogan"]); float bury = HasKey(gogan, "bury") ? F(gogan["bury"]) : 0.3333f;
        int nStone = 0, nSkip = 0;
        // 主視点(face の相手)
        var vpW = new Dictionary<string, Vector2>();
        foreach (var vo in A(D["viewpoints"])) { var vp = O(vo); vpW[StrOf(vp, "name")] = f.W(F(vp["u"]), F(vp["v"])); }
        foreach (var o in A(D["tenkei"]))
        {
            var t = O(o); if (!HasKey(t, "stones")) continue;
            var sub = Group("Niwa/Ishigumi/" + StrOf(t, "name"));
            // 群の主石(face:"主石" の相手)= 名に「主石」「鏡石」を含む最初の石
            Vector2? shuW = null;
            foreach (var so0 in A(t["stones"])) { var s0 = O(so0); string n0 = StrOf(s0, "name") ?? "";
                if (n0.Contains("主石") || n0.Contains("鏡石")) { shuW = f.W(HasKey(s0, "u") ? F(s0["u"]) : F(t["u"]), HasKey(s0, "v") ? F(s0["v"]) : F(t["v"])); break; } }
            int i = 0;
            foreach (var so in A(t["stones"]))
            {
                var st = O(so); string snm = StrOf(st, "name") ?? ("石" + i);
                float u = HasKey(st, "u") ? F(st["u"]) : F(t["u"]); float v = HasKey(st, "v") ? F(st["v"]) : F(t["v"]);
                // 埋め: 石ごとの `bury` が優先(天井石は 0 = 架ける)。全丈 = 見え丈 ÷ (1 − 埋め)
                float bu = HasKey(st, "bury") ? F(st["bury"]) : bury;
                float show = F(st["show"]); float full = show / Mathf.Max(0.01f, 1f - bu);
                Vector2 w = f.W(u, v);
                // 据え付け面: 指図の `bedY`(岩屋の三段=水面から従属)があればそれ、無ければ実地形
                float gy = HasKey(st, "bedY") ? StoneBedY(t, st) : TerrainY(w.x, w.y);
                // 部材: 指図の `api`(立石は Own.Tateishi / 伏石は JG.Rock)。無ければ在庫の転石
                string path = HasKey(st, "api") ? ResolveApi(StrOf(st, "api")) : null;
                if (path == null) path = EdoAssets.JG.Rock(1 + rnd.Next(3));
                // 向き: `face`(V1/V2 = その主視点へ見付 +Z を向ける / 主石 = 群の主石へ / 洞の内 = 主石の逆)。無ければ乱数
                float yaw = (float)rnd.NextDouble() * 360f; string face = StrOf(st, "face");
                if (face != null)
                {
                    Vector2? tgt = null;
                    if (vpW.ContainsKey(face)) tgt = vpW[face];
                    else if (face.Contains("主石") && shuW.HasValue) tgt = shuW.Value;
                    else if (face.Contains("洞") && shuW.HasValue) tgt = w + (w - shuW.Value);
                    if (tgt.HasValue) { Vector2 dv = tgt.Value - w; yaw = Mathf.Atan2(dv.x, dv.y) * Mathf.Rad2Deg; }
                }
                var go = EdoBuild.Place(path, new Vector3(w.x, gy - full * bu, w.y), yaw, Vector3.one, sub, snm);
                if (go == null) { nSkip++; sb.AppendLine("⚠ 石 " + snm + ": 部材が解けない(" + (StrOf(st, "api") ?? "在庫") + ")"); i++; continue; }
                // 寸法: 指図の `plan` [長, 幅] と全丈へ **非等方**に合わせる。⛔ 異方比(軸ごとの拡縮の最大/最小)が 1.35 を超える石は
                //   岩肌が伸びて岩に見えないので据えず、部材方へ(庭方 2026-09-04 共有2-4)。
                var rs = go.GetComponentsInChildren<Renderer>();
                if (rs.Length > 0 && HasKey(st, "plan"))
                {
                    // ⚠ 寸法は石の**自身の軸**で測る(`plan` の長・幅は見付 +Z を正面にした石の x・z)。向き(yaw)を掛けた後の
                    //   世界軸の外接箱で測ると長と幅が混ざり、正しく解けた立石まで異方比で落ちる(2026-09-06 鏡石 1.61 で発覚)。
                    var rot0 = go.transform.rotation; go.transform.rotation = Quaternion.identity;
                    var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    go.transform.rotation = rot0;
                    var pl = A(st["plan"]); float L = F(pl[0]), Wd = F(pl[1]);
                    float sx = L / Mathf.Max(0.01f, b.size.x), sz = Wd / Mathf.Max(0.01f, b.size.z), sy = full / Mathf.Max(0.01f, b.size.y);
                    float mx = Mathf.Max(sx, Mathf.Max(sy, sz)), mn = Mathf.Min(sx, Mathf.Min(sy, sz));
                    if (mx / mn > 1.365f)   // 上限 1.35 + 丸め(奥の添石 1.36 は庭方が僅差として許容【U】2026-09-06)
                    {
                        sb.AppendLine(string.Format("⚠ 石 {0}: 異方比 {1:F2}(x{2:F2} y{3:F2} z{4:F2})— 据えず。丈 {5:F2}m の立石を部材方へ", snm, mx / mn, sx, sy, sz, full));
                        UnityEngine.Object.DestroyImmediate(go); nSkip++; i++; continue;
                    }
                    go.transform.localScale = new Vector3(sx, sy, sz);
                }
                else ScaleToHeight(go, full);
                nStone++; i++;
            }
        }
        // 石組護岸: 帯ごとに汀線を歩き、`seatRule`(外向きに進んで最初に地面が waterY を超える点)へ据える
        int nGogan = 0; var gsub = Group("Niwa/Ishigumi/Gogan"); var shoreArr = shore.ToArray();
        // ⭐ goganGap(検図 第14次 2026-09-06): 吐き口の岩組(岩屋)が占める汀線の区間には常石を置かない。
        //   生成器 `_gogan_exclude_gap` と同じ従属値 = tenkei[T_Iwagumi_Iwaya].atShore の {shore(1始まり), spanMax[m]}。
        int gapIdx = -1; float gapSpan = 0f;
        foreach (var o in A(D["tenkei"])) { var t = O(o); if (StrOf(t, "name") == "T_Iwagumi_Iwaya" && HasKey(t, "atShore"))
            { var ash = O(t["atShore"]); gapIdx = Convert.ToInt32(ash["shore"]) - 1; gapSpan = F(ash["spanMax"]); } }
        foreach (var bo in A(gogan["bands"]))
        {
            var b = O(bo); int i0 = Convert.ToInt32(b["from"]) - 1, i1 = Convert.ToInt32(b["to"]) - 1;   // ⚠ 指図の from/to は汀線の番号 #(1始まり)。生成器 gogan_bands() と同じく −1(2026-09-06 検図 第13次 中1)
            var tb = A(b["tenbaishi"]); float sMin = F(tb[0]), sMax = F(tb[1]);       // 天端石の長さ帯
            var ta = A(b["topAbove"]); float aMin = F(ta[0]), aMax = F(ta[1]);        // 天端 = 水面 + この帯
            float gap = HasKey(gogan, "gapRatio") ? F(gogan["gapRatio"]) : 0.78f;
            int n = shore.Count; int idx = i0; float carry = 0f;
            while (true)
            {
                Vector2 a = shore[idx % n], c = shore[(idx + 1) % n];
                float seg = Vector2.Distance(a, c); float pos = carry;
                while (pos < seg)
                {
                    float size = Mathf.Lerp(sMin, sMax, (float)rnd.NextDouble());
                    Vector2 q = Vector2.Lerp(a, c, pos / seg);
                    if (gapIdx >= 0 && Vector2.Distance(q, shore[gapIdx]) <= gapSpan) { pos += size * gap; continue; }   // goganGap
                    // 外向き = 汀線の左右のうち池の外(輪郭の重心から遠い側)
                    // ⛔ 「輪郭の重心から遠い側」は瓢箪のくびれ(#15→#16)で反転する(庭方 2026-09-04 共有3)。
                    //    外向き = 法線方向へ 0.8m 進んだ点が池の**外**(PIP false)。
                    Vector2 nrm = new Vector2(-(c - a).y, (c - a).x).normalized;
                    if (EdoGeom.PIP(shoreArr, q + nrm * 0.8f)) nrm = -nrm;
                    Vector2 seat = q; for (int k = 0; k < 40; k++) { seat = q + nrm * (k * 0.1f); if (TerrainY(seat.x, seat.y) > wy) break; }
                    float top = wy + Mathf.Lerp(aMin, aMax, (float)rnd.NextDouble());
                    float gy = TerrainY(seat.x, seat.y); float full = (top - gy) / (1f - bury);
                    var go = EdoBuild.Place(EdoAssets.JG.Rock(1 + rnd.Next(3)),
                        new Vector3(seat.x, gy - full * bury, seat.y), Mathf.Atan2((c - a).x, (c - a).y) * Mathf.Rad2Deg, Vector3.one, gsub, "護岸_" + nGogan);
                    if (go != null) { ScaleToHeight(go, full); nGogan++; }
                    pos += size * gap;
                }
                carry = pos - seg; idx++;
                if (idx % n == i1 % n) break;
                if (idx > i0 + n) break;
            }
        }
        sb.AppendLine(string.Format("石組 {0} 石(据えず {2})/ 護岸 {1} 石(石橋は部材なし・据えず)", nStone, nGogan, nSkip));
        return sb.ToString();
    }

    /// <summary>石の `bedY` を解く。生成器 `_stone_bedY()` と同じ式 — dict なら {ref: 同じ点景内の石の名, add} として
    /// 参照先の**天端**(bedY + show)+ add(架け石は支え石の天端に従属・検図 2026-09-06【低】)。数値ならそのまま。</summary>
    static float StoneBedY(Dictionary<string, object> tk, Dictionary<string, object> st, int depth = 0)
    {
        if (!HasKey(st, "bedY")) return 0f;
        var b = st["bedY"];
        var bd = b as Dictionary<string, object>;
        if (bd == null) return F(b);
        if (depth > 8) throw new Exception("石 " + StrOf(st, "name") + " の bedY.ref が循環している");
        string refName = StrOf(bd, "ref"); Dictionary<string, object> refSt = null;
        foreach (var so in A(tk["stones"])) { var s2 = O(so); if (StrOf(s2, "name") == refName) { refSt = s2; break; } }
        if (refSt == null) throw new Exception("石 " + StrOf(st, "name") + " の bedY.ref『" + refName + "』が点景 " + StrOf(tk, "name") + " に無い");
        float add = HasKey(bd, "add") ? F(bd["add"]) : 0f;
        return StoneBedY(tk, refSt, depth + 1) + (HasKey(refSt, "show") ? F(refSt["show"]) : 0f) + add;
    }

    /// <summary>置いた駒の**実メッシュ**の高さを測って、丈 h[m] に合わせる(CLAUDE.md 規則5: 呼び寸法で置かない)。</summary>
    static void ScaleToHeight(GameObject go, float h)
    {
        var rs = go.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) return;
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        if (b.size.y < 1e-3f) return;
        float k = h / b.size.y; go.transform.localScale = go.transform.localScale * k;
    }

    // ------------------------------------------------------------------ 6d 点景と垣(冪等)
    [MenuItem("Edo/松平出羽守上屋敷/6d 点景と垣")]
    public static void Stage6dMenu() { Debug.Log("[Matsudaira] " + Stage6d_Tenkei()); }
    public static string Stage6d_Tenkei()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        var sb = new System.Text.StringBuilder(); var f = Grid; var rnd = new System.Random(1856);
        var grp = Group("Niwa/Tenkei"); Clear(grp);
        int placed = 0; var missing = new Dictionary<string, int>();
        // 生垣が木戸に接して立つための、木戸(庭木戸)の世界中心(名で決め打ちせず指図から引く)
        var gateCenters = new List<Vector2>();
        foreach (var go0 in A(D["nakajikiri"]))
        {
            var w0 = O(go0); if (StrOf(w0, "kind") != "庭木戸") continue;
            var ga = A(w0["a"]); var gb = A(w0["b"]);
            gateCenters.Add((f.W(F(ga[0]), F(ga[1])) + f.W(F(gb[0]), F(gb[1]))) * 0.5f);
        }
        foreach (var o in A(D["tenkei"]))
        {
            var t = O(o); if (HasKey(t, "stones")) continue;                  // 石組は 6c
            string kind = StrOf(t, "kind") ?? ""; string name = StrOf(t, "name");
            if (kind.Contains("生垣"))
            {
                // ⭐ 普請奉行の指示(2026-09-06 EDO-0147・依頼書B-8): 1間モジュール・両端は
                //   End 駒(EdoAssets.Own.Ikegaki(end))・区間長÷1.818で駒数(端数は駒を増減して
                //   最も近い長さ・**縮めない**=scale Vector3.one 固定)・ピボットは1間の中心・床。
                //   木戸に接する側から敷き詰め、端数は反対側へ逃がす(木戸の位置は nakajikiri から
                //   幾何で引く。どちらの端かを名で決め打ちしない)。
                if (!(HasKey(t, "a") && HasKey(t, "b")))
                { missing[kind] = missing.ContainsKey(kind) ? missing[kind] + 1 : 1; continue; }
                var ia = A(t["a"]); var ib = A(t["b"]);
                Vector2 iwa = f.W(F(ia[0]), F(ia[1])), iwb = f.W(F(ib[0]), F(ib[1]));
                float iL = Vector2.Distance(iwa, iwb);
                if (iL < 0.1f) continue;
                const float BAY = 1.818f;                           // 1間(縮めない実寸モジュール)
                int nBay = Mathf.Max(1, Mathf.RoundToInt(iL / BAY));
                Vector2 dir = (iwb - iwa) / iL;
                float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
                float distA = float.MaxValue, distB = float.MaxValue;
                foreach (var gc in gateCenters)
                { distA = Mathf.Min(distA, Vector2.Distance(iwa, gc)); distB = Mathf.Min(distB, Vector2.Distance(iwb, gc)); }
                bool anchorAtB = distB < distA;
                Vector2 origin = anchorAtB ? iwb - dir * (BAY * nBay) : iwa;
                int madeIk = 0;
                for (int i = 0; i < nBay; i++)
                {
                    bool end = (i == 0 || i == nBay - 1);
                    string ikPath = EdoAssets.Own.Ikegaki(end);
                    Vector2 c = origin + dir * (BAY * (i + 0.5f));
                    var goIk = EdoBuild.Place(ikPath, new Vector3(c.x, TerrainY(c.x, c.y), c.y),
                        yaw, Vector3.one, grp, name + "_" + i);
                    if (goIk != null) madeIk++;
                }
                if (madeIk == 0) missing[kind] = missing.ContainsKey(kind) ? missing[kind] + 1 : 1;
                placed += madeIk;
                continue;
            }
            // 種別 → 在庫。⛔ 指図の `api` が最優先。無ければ種別の既定(在庫にあるものだけ)
            string api = ResolveApi(StrOf(t, "api"));
            if (api == null)
            {
                if (kind.Contains("雪見灯籠")) api = "Assets/Edo/Prefabs/YukimiLantern.prefab";
                else if (kind.Contains("沓脱石") || kind.Contains("据石") || kind.Contains("踏分")) api = EdoAssets.JG.Rock(1 + rnd.Next(3));
                else if (kind.Contains("四つ目垣") || kind.Contains("建仁寺垣")) api = EdoAssets.Eg.TakeGaki;   // ⚠ 建仁寺垣は代用(要新造)
            }
            if (api == null) { missing[kind] = missing.ContainsKey(kind) ? missing[kind] + 1 : 1; continue; }
            if (HasKey(t, "a") && HasKey(t, "b"))
            {
                // 線の点景(垣): a→b を部材の実寸で刻んで並べる(規則5: 実メッシュで測る)
                var a = A(t["a"]); var b = A(t["b"]);
                Vector2 wa = f.W(F(a[0]), F(a[1])), wb = f.W(F(b[0]), F(b[1]));
                float L = Vector2.Distance(wa, wb); float yaw = Mathf.Atan2((wb - wa).x, (wb - wa).y) * Mathf.Rad2Deg;
                var probe = EdoBuild.Place(api, new Vector3(wa.x, TerrainY(wa.x, wa.y), wa.y), yaw, Vector3.one, grp, name + "_0");
                if (probe == null) { missing[kind] = missing.ContainsKey(kind) ? missing[kind] + 1 : 1; continue; }
                var rs = probe.GetComponentsInChildren<Renderer>(); var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
                float unit = Mathf.Max(0.3f, Vector3.Dot(bb.size, Quaternion.Euler(0, yaw, 0) * Vector3.forward).Equals(0) ? bb.size.x : Mathf.Abs(bb.size.z));
                int cnt = Mathf.Max(1, Mathf.RoundToInt(L / unit));
                for (int i = 1; i < cnt; i++)
                {
                    Vector2 q = Vector2.Lerp(wa, wb, (float)i / cnt);
                    EdoBuild.Place(api, new Vector3(q.x, TerrainY(q.x, q.y), q.y), yaw, Vector3.one, grp, name + "_" + i);
                }
                placed += cnt;
            }
            else if (HasKey(t, "u") && HasKey(t, "v"))
            {
                Vector2 w = f.W(F(t["u"]), F(t["v"]));
                // ⭐ **`facing` を持つ点景は向きが決まっている**(2026-09-16 是正)。
                //   `facing` = 正面(表)の面の**外向きの法線**(⛔ 参道を進む向きではない —
                //   鳥居の正面は社に背を向け、参拝者が来る側を向く)。
                //   ⛔ 乱数の yaw に落とさない — 鳥居の笠木が参道を斜めに跨いでいた
                //   (`const.toriiRule.faceAxis` = ±Z なのでローカル +Z を facing へ振る)。
                float pyaw;
                if (HasKey(t, "facing"))
                {
                    Vector2 fd;
                    if (!TryGridDir(StrOf(t, "facing"), out fd))
                    {
                        sb.AppendLine("⛔ 点景 " + name + ": facing=" + StrOf(t, "facing") +
                                      " が読めない(+u/-u/+v/-v)— 据えず指図方へ差し戻し");
                        continue;
                    }
                    pyaw = Mathf.Atan2(fd.x, fd.y) * Mathf.Rad2Deg;
                }
                else pyaw = (float)rnd.NextDouble() * 360f;      // 石・灯籠は向きを持たない
                var go = EdoBuild.Place(api, new Vector3(w.x, TerrainY(w.x, w.y), w.y), pyaw, Vector3.one, grp, name);
                if (go != null)
                {
                    placed++;
                    if (HasKey(t, "facing"))
                        sb.AppendLine("点景 " + name + " を据えた: 正面 " + StrOf(t, "facing")
                            + "(yaw " + pyaw.ToString("F1") + "°)/ 芯 (u " + F(t["u"]).ToString("0.##")
                            + ", v " + F(t["v"]).ToString("0.##") + ")");
                }
            }
        }
        sb.AppendLine("点景 " + placed + " 点を据えた");
        foreach (var kv in missing) sb.AppendLine("⛔ 部材なし・据えず: " + kv.Key + " × " + kv.Value + " → edo-zaiko / edo-buzai");
        return sb.ToString();
    }

    // ------------------------------------------------------------------ 6e 滝見口(冪等)
    [MenuItem("Edo/松平出羽守上屋敷/6e 滝見口を開ける")]
    public static void Stage6eMenu() { Debug.Log("[Matsudaira] " + Stage6e_TakiKido()); }
    public static string Stage6e_TakiKido()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        // 中仕切 `NJ_Oku_S_W` に庭木戸 `NJ_Taki_Kido`(1間)を開ける = 開口に掛かる板塀の駒を非アクティブにする
        Dictionary<string, object> kido = null;
        foreach (var o in A(D["nakajikiri"])) { var w = O(o); if (StrOf(w, "name") == "NJ_Taki_Kido") kido = w; }
        if (kido == null) return "指図に NJ_Taki_Kido が無い";
        var f = Grid; var a = A(kido["a"]); var b = A(kido["b"]);
        Vector2 wa = f.W(F(a[0]), F(a[1])), wb = f.W(F(b[0]), F(b[1]));
        // ⚠ 中仕切の駒は Stage6 が `Fuzoku/Nakajikiri` に置く。`Group("Nakajikiri")` だと
        //    空の新規グループを作って **0 件で黙って成功**していた(2026-09-04 棟梁)。
        var walls = Group("Fuzoku/Nakajikiri"); int off = 0;
        foreach (Transform t in walls)
        {
            var rs = t.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) continue;
            var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
            var c = new Vector2(bb.center.x, bb.center.z);
            float s; float d = DistLine(new List<Vector2> { wa, wb }, c, false, out s);
            if (d < 0.6f && s > 0f && s < Vector2.Distance(wa, wb)) { t.gameObject.SetActive(false); off++; }
        }
        return "滝見口: 開口に掛かる板塀の駒 " + off + " を非アクティブにした(⛔ 木戸そのものは部材なし・据えず)";
    }

    // ------------------------------------------------------------------ 6f 参道の玉砂利(冪等)
    /// <summary>参道 `routes[R_Inari]` に**玉砂利を敷く**(指図 `finish` = 玉砂利敷)。
    /// ⛔ 値はすべて指図から引く — 幅 `w`[間] / 天端 `toriiFoot.gravelTop`[m](地盤と面一の帯・中央を採る) /
    /// 鳥居の足元に土を残す前後の範囲(`const.toriiRule.nemakiD`/2 + `toriiFoot.soilBand` の**従属値**) /
    /// 止め(`service.Inari.seat.gravelEnd` = **軒先の線(雨落ち)で止める**。据えた社の実メッシュから測る)。
    /// <para>⛔ **地表のスプラットでは敷けない** — alphamap は 4.0 m/px、参道の幅は 0.80m で 1/5 画素。
    /// ⇒ 折れ線から**帯のメッシュ**を起こし、地形に沿わせて `gravelTop` だけ浮かせる。</para>
    /// <para>⚠ **敷いたのは `R_Inari` だけ。** 他の園路(`R_Shutei` 土の小径 / `R_Roji` 飛石 /
    /// `R_OkuNiwa_Endan` 切石の延段 / `R_OkuNiwa2` 土・瓦の見切り / `R_Takimi` 乱れ段)は
    /// `finish` を持つが**据える駒・材の名指しが無い** ⇒ 指図方・在庫方へ差し戻し(⛔ ここで発明しない)。</para></summary>
    [MenuItem("Edo/松平出羽守上屋敷/6f 参道の玉砂利(稲荷)")]
    public static void Stage6fMenu() { Debug.Log("[Matsudaira] " + Stage6f_Tamajari()); }
    public static string Stage6f_Tamajari()
    {
        { var gate = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (gate != null) return gate; }
        var sb = new System.Text.StringBuilder(); var f = Grid;

        // ---- 指図を読む(⛔ ここは値を持たない)
        Dictionary<string, object> rt = null;
        foreach (var o in A(D["routes"])) { var r = O(o); if (StrOf(r, "name") == "R_Inari") rt = r; }
        if (rt == null) return "⛔ 指図に routes[R_Inari] が無い — 指図方へ差し戻し";
        if (!HasKey(rt, "w")) return "⛔ R_Inari に w(幅)が無い — ⛔ 幅を発明しない。指図方へ差し戻し";
        if (!HasKey(rt, "toriiFoot")) return "⛔ R_Inari に toriiFoot が無い — 指図方へ差し戻し";
        var tf = O(rt["toriiFoot"]);
        var gt = A(tf["gravelTop"]);
        float half = F(rt["w"]) * f.ken * 0.5f;                       // 参道の半幅[m]
        float lift = (F(gt[0]) + F(gt[1])) * 0.5f;                    // 地盤からの天端[m](帯の中央)
        var tr = O(O(D["const"])["toriiRule"]);
        float soilAlong = F(tr["nemakiD"]) * 0.5f + F(tf["soilBand"]);  // 鳥居の芯から前後に土を残す[m](従属値)
        var line = UVLine(rt["pts"]);
        if (line.Count < 2) return "⛔ R_Inari の pts が足りない";

        // ---- 鳥居の芯(指図の tenkei が正典。⛔ 座標をここへ写さない)
        var torii = new List<Vector2>();
        foreach (var o in A(D["tenkei"]))
        {
            var t = O(o);
            if (!(StrOf(t, "kind") ?? "").Contains("鳥居")) continue;
            if (HasKey(t, "route") && StrOf(t, "route") != "R_Inari") continue;
            if (!HasKey(t, "u") || !HasKey(t, "v")) continue;
            torii.Add(f.W(F(t["u"]), F(t["v"])));
        }

        // ---- 玉砂利の止め(`service.Inari.seat.gravelEnd`)。**据えた社の実メッシュの軒先**で測る
        bool haveDrip = false; Vector2 drip = Vector2.zero, front = Vector2.zero;
        {
            var svc = Group("Fuzoku/Service"); var sha = svc.Find("Inari");
            if (sha == null)
                sb.AppendLine("⚠ 社 Inari が据わっていないので雨落ちの止めを測れない — Stage6 を先に流す");
            else
            {
                float zmn, zmx; PartLocalZ(sha.gameObject, out zmn, out zmx);
                Vector3 fw = sha.forward;                              // ローカル +Z = 社の正面
                front = new Vector2(fw.x, fw.z).normalized;
                drip = new Vector2(sha.position.x, sha.position.z) + front * zmx;
                haveDrip = true;
                sb.AppendLine("雨落ちの線: 社の正面の軒先(ローカル +Z の実測 " + zmx.ToString("F2") + "m)で止める");
            }
        }

        // ---- 折れ線を刻んで帯を張る。頂点の高さは**地形をそのまま拾う**(規則9)
        const float STEP = 0.25f;                                      // 刻み[m](曲がりの内側が割れない程度)
        var segLen = new List<float>(); float total = 0f;
        for (int i = 0; i + 1 < line.Count; i++)
        { float L = Vector2.Distance(line[i], line[i + 1]); segLen.Add(L); total += L; }
        // ⭐ 刻みの位置は**走り[m]**で決め、**土の見切りの境(鳥居の芯 ± soilAlong)と折れ点は
        //    刻みに関わらずちょうどその位置へ足す**(⛔ 丸めて見切りを刻み1つぶん広げない)
        var svals = new List<float>();
        for (float s0 = 0f; s0 < total; s0 += STEP) svals.Add(s0);
        svals.Add(total);
        { float accSeg = 0f; for (int i = 0; i + 1 < line.Count; i++) { accSeg += segLen[i]; svals.Add(accSeg); } }
        foreach (var tc in torii)
        {
            float sa; DistLine(line, tc, false, out sa);
            svals.Add(Mathf.Clamp(sa - soilAlong, 0f, total));
            svals.Add(Mathf.Clamp(sa + soilAlong, 0f, total));
        }
        svals.Sort();
        var samp = new List<Vector2>(); float sPrev = -1f;
        foreach (var s0 in svals)
        {
            if (s0 - sPrev < 1e-3f) continue; sPrev = s0;
            float rem = s0;
            int si = 0; while (si < segLen.Count - 1 && rem > segLen[si]) { rem -= segLen[si]; si++; }
            samp.Add(Vector2.Lerp(line[si], line[si + 1], Mathf.Clamp01(rem / Mathf.Max(1e-5f, segLen[si]))));
        }

        var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
        int[] idx = new int[samp.Count];                                // 各刻みの左端の頂点番号(-1 = 敷かない)
        float acc = 0f; int nSkipTorii = 0, nSkipEave = 0;
        for (int i = 0; i < samp.Count; i++)
        {
            if (i > 0) acc += Vector2.Distance(samp[i - 1], samp[i]);
            // 接線は中央差分(折れの内外で帯が割れないように)
            Vector2 p0 = samp[Mathf.Max(0, i - 1)], p1 = samp[Mathf.Min(samp.Count - 1, i + 1)];
            Vector2 tg = (p1 - p0); if (tg.sqrMagnitude < 1e-8f) tg = Vector2.right;
            tg.Normalize();
            Vector2 nm2 = new Vector2(-tg.y, tg.x);
            bool ok = true;
            foreach (var tc in torii) if (Vector2.Distance(samp[i], tc) < soilAlong - 1e-3f) { ok = false; nSkipTorii++; break; }
            if (ok && haveDrip && Vector2.Dot(samp[i] - drip, front) < 0f) { ok = false; nSkipEave++; }
            if (!ok) { idx[i] = -1; continue; }
            Vector2 lp = samp[i] - nm2 * half, rp = samp[i] + nm2 * half;
            idx[i] = verts.Count;
            verts.Add(new Vector3(lp.x, TerrainY(lp.x, lp.y) + lift, lp.y));
            verts.Add(new Vector3(rp.x, TerrainY(rp.x, rp.y) + lift, rp.y));
            uvs.Add(new Vector2(acc, 0f));                              // UV は m 単位(材のタイリングは 1×1)
            uvs.Add(new Vector2(acc, half * 2f));
        }
        int quads = 0;
        for (int i = 0; i + 1 < samp.Count; i++)
        {
            if (idx[i] < 0 || idx[i + 1] < 0) continue;
            int a0 = idx[i], a1 = idx[i] + 1, b0 = idx[i + 1], b1 = idx[i + 1] + 1;
            // ⚠ 巻きは**上から見て時計回り**が表(Unity は左手系)。逆に張ると法線が下を向き、
            //   材は付いているのに**上から見て消える**(2026-09-16 に実測 法線 上向き0/下向き284)。
            tris.Add(a0); tris.Add(a1); tris.Add(b0);
            tris.Add(a1); tris.Add(b1); tris.Add(b0);
            quads++;
        }
        if (quads == 0) return "⛔ 玉砂利を張る面が残らなかった(刻み/止めの条件を疑う)";

        var mesh = new Mesh { name = "Matsudaira_R_Inari_Tamajari" };
        mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();

        string dir = EdoAssets.Own.Matsudaira.GenMeshDir.TrimEnd('/');
        if (!AssetDatabase.IsValidFolder(dir))
            AssetDatabase.CreateFolder(dir.Substring(0, dir.LastIndexOf('/')), dir.Substring(dir.LastIndexOf('/') + 1));
        string mp = dir + "/" + mesh.name + ".asset";
        var old = AssetDatabase.LoadAssetAtPath<Mesh>(mp);
        if (old != null) { EditorUtility.CopySerialized(mesh, old); mesh = old; }
        else AssetDatabase.CreateAsset(mesh, mp);
        AssetDatabase.SaveAssets();

        var mat = AssetDatabase.LoadAssetAtPath<Material>(EdoAssets.JG.GravelMat);
        if (mat == null) return "⛔ 玉砂利の材が読めない " + EdoAssets.JG.GravelMat + " — edo-zaiko へ照会";

        var grp = Group("Niwa/Sando"); Clear(grp);
        var go2 = new GameObject("R_Inari_Tamajari");
        go2.transform.SetParent(grp, false);
        go2.AddComponent<MeshFilter>().sharedMesh = mesh;
        go2.AddComponent<MeshRenderer>().sharedMaterial = mat;
        Undo.RegisterCreatedObjectUndo(go2, "tamajari");

        sb.Append("玉砂利 " + quads + " 区画(幅 " + (half * 2f).ToString("F2") + "m・天端 地盤+"
                  + lift.ToString("F3") + "m・全長 " + acc.ToString("F1") + "m)/ 鳥居の足元で土を残した刻み "
                  + nSkipTorii + "(前後 ±" + soilAlong.ToString("F2") + "m)/ 雨落ちより社側で止めた刻み " + nSkipEave);
        return sb.ToString();
    }

    // ------------------------------------------------------------------ 7' 植栽(指図の生成器が撒いた点を据える・冪等)
    // ⭐ **検査と実装で置き方を別々に書かない。**生成器 `scatter_gardens` が撒いた点(`group_pack_check` ほかが
    //   検査したのと同じ点)を `docs/Sashizu/matsudaira_dewa_planting_out.json` に書き出させ、ここは**据えるだけ**。
    //   ⛔ 岡部 2026-09-02: 「検査と散布を別々に書くと、検査が通って実装で 0 本になる」。
    //   旧 Stage7 は庭を外接箱で読み、樹種と塊がべた書きだった(検図 第4次【高7】)。
    //   sidecar の1行 = { zone, layer, role, u, v, api, scale, tilt, tiltDir, ground }(u,v は間。ground=design|terrain)。
    //   ⭐ 西斜面(旧 Stage8 の scatter/crestLine)もこの1本で据える — 帯の二重管理(検図【高5】)を構造で消す。
    [MenuItem("Edo/松平出羽守上屋敷/7' 植栽(指図の散布点を据える)")]
    public static void Stage7bMenu() { Debug.Log("[Matsudaira] " + Stage7b_NiwaFromScatter()); }
    public static string Stage7b_NiwaFromScatter()
    {
        { var g = EdoSashizuExport.ReviewGate("matsudaira_dewa"); if (g != null) return g; }
        // 指図と同じ場所(SashizuRel と同じ解き方)
        string path = System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName,
                                             "docs/Sashizu/matsudaira_dewa_planting_out.json");
        if (!System.IO.File.Exists(path))
            return "⛔ " + path + " が無い — 生成器 build_matsudaira_dewa_sashizu.py が散布点を書き出していない(--export-planting)";
        var doc = EdoMiniJson.Parse(System.IO.File.ReadAllText(path)) as Dictionary<string, object>;
        if (doc == null || !doc.ContainsKey("points")) return "⛔ planting_out の形が違う(points が無い)";
        var pts = doc["points"] as List<object>;
        // ⭐ **2026-09-09: 指図 `plantRule.forbidden` を読む。**⛔ 禁じられた部材(自作の低ポリの木)を
        //   散布点が名指ししていたら**据えずに鳴らす**。CLAUDE.md 規則10 が機械で効くようにする。
        //   それまで `plantRule` はビルダーが一度も読まない設計値だった(`_pending.jissouShukudai` ①)。
        var forbidden = new List<string>();
        if (HasKey(D, "plantRule"))
        {
            var pr = O(D["plantRule"]);
            if (HasKey(pr, "forbidden")) foreach (var o in A(pr["forbidden"])) forbidden.Add(o as string);
        }
        int nForbid = 0;
        var f = Grid; var rnd = new System.Random(1856);
        var root = Group("Niwa/Planting"); Clear(root);
        // 主視点(傾ける向きの相手)
        var vps = new Dictionary<string, Vector2>();
        foreach (var o in A(D["viewpoints"])) { var vp = O(o); vps[StrOf(vp, "name")] = f.W(F(vp["u"]), F(vp["v"])); }
        int placed = 0, noPart = 0, nTerrain = 0; var byZone = new Dictionary<string, int>();
        foreach (var o in pts)
        {
            var p = O(o); string zone = StrOf(p, "zone") ?? "?";
            string rawApi = StrOf(p, "api");
            string api = ResolveApi(rawApi);
            if (api == null) { noPart++; continue; }
            { bool ng = false;
              foreach (var fb in forbidden) if (fb != null && (fb == rawApi || fb == api)) ng = true;
              if (ng) { nForbid++; continue; } }
            float u = F(p["u"]), v = F(p["v"]);
            var sub = Group("Niwa/Planting/" + zone + "/" + (StrOf(p, "layer") ?? "層"));
            float scale = HasKey(p, "scale") ? F(p["scale"]) : 1f;
            string nm = zone + "_" + (StrOf(p, "role") ?? "") + "_" + placed;
            // ground: "design"(庭=設計面 DesignY)/ "terrain"(法面=造成しないので live terrain を実測)。
            // ⛔ 法面に DesignY を使うと段の高さで宙に浮く(旧 Stage8 の作法を引き継ぐ)。
            bool onTerrain = (StrOf(p, "ground") ?? "design") == "terrain";
            var go = onTerrain
                ? PlantOnTerrain(api, f.W(u, v), sub, nm, scale, rnd, 0.82f, 1.18f, 0f, 0f)
                : Plant(api, u, v, sub, nm, scale, rnd, 0f);
            if (go == null) { noPart++; continue; }
            if (onTerrain) nTerrain++;
            // 傾き: 層の tilt [lo,hi]°、向きは tiltDir(random / V1.. = その主視点へ)。⛔ 撤回済みの「全数 −u へ」は無い
            if (HasKey(p, "tilt"))
            {
                var tl = A(p["tilt"]); float lo = F(tl[0]), hi = F(tl[1]);
                float deg = Mathf.Lerp(lo, hi, (float)rnd.NextDouble());
                if (deg > 1e-3f)
                {
                    string dir = StrOf(p, "tiltDir") ?? "random";
                    Vector2 here = f.W(u, v); float az;
                    if (vps.ContainsKey(dir)) { var to = vps[dir] - here; az = Mathf.Atan2(to.x, to.y) * Mathf.Rad2Deg; }
                    else az = (float)rnd.NextDouble() * 360f;
                    // 幹を az の向きへ deg 倒す(倒す軸は az に直交する水平軸)
                    var axis = Quaternion.Euler(0, az + 90f, 0) * Vector3.forward;
                    go.transform.RotateAround(go.transform.position, axis, deg);
                }
            }
            placed++; byZone[zone] = byZone.ContainsKey(zone) ? byZone[zone] + 1 : 1;
        }
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(string.Format("植栽 {0} 本を据えた(散布点 {3} 点 / うち法面=live terrain {1})/ 部材が解けず {2}",
                                    placed, nTerrain, noPart, pts.Count));
        if (nForbid > 0) sb.AppendLine("★ 指図 plantRule.forbidden の部材を名指しした点 " + nForbid + " 点 — 据えず");
        foreach (var kv in byZone) sb.AppendLine("  " + kv.Key + ": " + kv.Value);
        return sb.ToString();
    }

    // ------------------------------------------------------------------ 庭の突き合わせ
    /// <summary>**庭を「指図と実装の突き合わせ」へ載せる**(`_pending.jissouShukudai` ②)。
    ///
    /// ⚠ それまで `EdoSashizuExport.CheckScene` は庭を**算出物 `impl.gardens` 経由でしか**見ておらず、
    ///   算出物を持たない当邸では `zoneNodes` が空になるので庭の照合が**丸ごと素通り**していた。
    ///   ⇒ 池も点景も植栽も一本も無くても「突き合わせ 0 件」が出る状態だった。
    ///
    /// ★(=不一致)にするのは「**指図が物を宣言していて、部材も在庫にあるのに、実装に無い**」場合だけ。
    /// ⛔ 部材が在庫に無いために据えていない物(石橋・織部灯籠・玉石の根石ほか)は**★にしない** —
    ///   それは実装の不一致ではなく**部材方への差し戻し**なので、末尾に「申し送り」として別に数える。
    ///   ⛔ ただし黙って落とさない(0 件を庭の合格の証拠に使わせないため、件数を必ず出す)。</summary>
    public static string NiwaQA()
    {
        var sb = new System.Text.StringBuilder();
        var bad = new List<string>();
        var pend = new List<string>();
        var root = GameObject.Find(Grp);
        if (root == null) return "★ ルート " + Grp + " が無い";
        Func<string, Transform> G2 = p => { var t = root.transform; foreach (var s in p.Split('/')) { t = t == null ? null : t.Find(s); } return t; };

        // ---- 池(sensui)。掘削は非冪等なのでマーカーで見る
        if (HasKey(D, "sensui"))
        {
            bool carved = G2("Niwa/_markers/6a_sensui") != null;
            bool mounds = G2("Niwa/_markers/6a2_mounds") != null;
            if (!carved) bad.Add("御泉水が掘られていない(マーカー 6a_sensui が無い)");
            if (!mounds) bad.Add("岬・中島の隆起が済んでいない(マーカー 6a2_mounds が無い)");
            var gg = G2("Niwa/Ishigumi/Gogan");
            int nGogan = gg == null ? 0 : gg.childCount;
            var sen = O(D["sensui"]);
            int bands = HasKey(sen, "gogan") && HasKey(O(sen["gogan"]), "bands") ? A(O(sen["gogan"])["bands"]).Count : 0;
            if (bands > 0 && nGogan == 0) bad.Add("護岸石が一つも無い(指図の帯 " + bands + " 本)");
            sb.AppendLine("  池: 掘削" + (carved ? "済" : "未") + " / 隆起" + (mounds ? "済" : "未")
                          + " / 護岸石 " + nGogan + " 石(帯 " + bands + " 本)");
        }

        // ---- 点景・石組(tenkei)。**部材が解ける物だけ**を期待する
        {
            var have = new HashSet<string>();
            foreach (var g in new[] { "Niwa/Tenkei", "Niwa/Ishigumi" })
            { var t = G2(g); if (t != null) foreach (Transform c in t) have.Add(c.name); }
            // ⛔ **「部材が引けるか」を先に判じない。**`Stage6d` は指図の `api` が無くても
            //   `kind`(雪見灯籠・沓脱石・四つ目垣・建仁寺垣・生垣)から在庫の既定へ落として据える。
            //   ⇒ `ResolveApi(api)` だけで判じると、**実際には据わっている 30 点を
            //   「部材が無いので据えず」と嘘の申し送り**にする(2026-09-09 に実際にそう出た)。
            // ⭕ **据わっているかを先に見る**。無いときだけ「部材が引けたはずか」を問い、
            //   引けたはずなら ★(実装の不一致)、引けないなら ⚠(部材待ち)。
            int gotN = 0, noPart = 0, all = 0;
            foreach (var o in A(D["tenkei"]))
            {
                var tk = O(o); string nm = StrOf(tk, "name"); if (nm == null) continue;
                all++;
                bool ok = false;
                foreach (var h in have) if (h == nm || h.StartsWith(nm + "_")) { ok = true; break; }
                if (ok) { gotN++; continue; }
                bool isStones = HasKey(tk, "stones");
                string api = HasKey(tk, "api") ? ResolveApi(StrOf(tk, "api")) : null;
                if (isStones || api != null) bad.Add("点景 " + nm + " が実装に無い(部材は引けるはず)");
                else { noPart++; pend.Add("点景 " + nm + "(" + (StrOf(tk, "kind") ?? "?") + "): 部材が在庫に無い(据えず)"); }
            }
            sb.AppendLine("  点景: 据わっている " + gotN + "/" + all + "(部材が無く据えず " + noPart + ")");
        }

        // ---- 水の系(mizu)。⛔ `api` を持たない節点は据えないのが指図どおり(★にしない)
        if (HasKey(D, "mizu"))
        {
            var mz = O(D["mizu"]);
            var t = G2("Niwa/Mizu"); int got = t == null ? 0 : t.childCount;
            int want = 0, noApi = 0;
            foreach (var o in A(mz["nodes"]))
            { var nd = O(o); if (!HasKey(nd, "u")) continue; if (ResolveApi(StrOf(nd, "api")) != null) want++; else noApi++; }
            if (got < want) bad.Add("水の系の節点が " + got + "/" + want + " しか据わっていない");
            if (noApi > 0) pend.Add("水の系: 部材の無い節点 " + noApi + " 個(枡・堰・樋。据えず)");
            sb.AppendLine("  水の系: 節点 " + got + "/" + want + "(部材なし " + noApi + ")");
        }

        // ---- 植栽。⭐ **散布点の書き出し(planting_out.json)と据えた本数を突き合わせる**
        {
            string path = System.IO.Path.Combine(System.IO.Directory.GetParent(Application.dataPath).FullName,
                                                 "docs/Sashizu/matsudaira_dewa_planting_out.json");
            int wantPts = -1;
            if (System.IO.File.Exists(path))
            {
                var doc = EdoMiniJson.Parse(System.IO.File.ReadAllText(path)) as Dictionary<string, object>;
                if (doc != null && doc.ContainsKey("points")) wantPts = (doc["points"] as List<object>).Count;
            }
            // ⛔ **「Planting/<庭>/<層>/木」の2段決め打ちで数えない。**`Group()` は名前の "/" で
            //   さらに掘るので、`zone` に "/" を含む層(西の斜面の「域W 西の崖 / 帯W1 法肩の縁」)は
            //   もう1段深くなる。2段で数えると 1132 本のうち **569 本しか見えず**、
            //   差の 563 本を「部材が解けず据えられなかった」と**嘘の申し送り**にしてしまう
            //   (2026-09-09 に実際にそう出た)。
            // ⭕ 木そのものは `Stage7b` が `<庭>_<役>_<通し番号>` と名づける ⇒ **末尾が `_数字`**。
            //   群のノード(庭名・層名)は数字で終わらない。⛔ 部材側の LOD_0/LOD_1 まで潜らないよう、
            //   木に当たったらそこで打ち切る。
            // ⛔⛔ **`Niwa/Planting` だけを見ない。**2026-09-21 の置き方の入れ替えで
            //   `Stage7b_NiwaFromScatter` は庭ごとの群 `Niwa/G_<庭>` へ据えるようになった。
            //   `Planting` だけ数えると、829 本が据わっているのに「一本も据わっていない」と出る
            //   (実際にそう出た。検査の文言と実装の集合を突き合わせる = CLAUDE.md 規則19)。
            var plRoots = new List<Transform>();
            { var p0 = G2("Niwa/Planting"); if (p0 != null) plRoots.Add(p0);
              var nw = G2("Niwa");
              if (nw != null) foreach (Transform c in nw) if (c.name.StartsWith("G_")) plRoots.Add(c); }
            int got = 0;
            foreach (var pl in plRoots)
            {
                var stack = new Stack<Transform>(); stack.Push(pl);
                while (stack.Count > 0)
                    foreach (Transform c in stack.Pop())
                    {
                        string s2 = c.name; int i2 = s2.Length - 1;
                        while (i2 >= 0 && s2[i2] >= '0' && s2[i2] <= '9') i2--;
                        if (i2 >= 0 && i2 < s2.Length - 1 && s2[i2] == '_') got++;
                        else stack.Push(c);
                    }
            }
            if (wantPts < 0) bad.Add("散布点の書き出し matsudaira_dewa_planting_out.json が無い");
            else if (got == 0) bad.Add("植栽が一本も据わっていない(散布点 " + wantPts + " 点)");
            else if (got < wantPts) pend.Add("植栽: 散布点 " + wantPts + " 点のうち " + (wantPts - got) + " 点は部材が解けず据えず");
            sb.AppendLine("  植栽: " + got + "/" + wantPts + " 本");
        }

        // ---- 園路・動線(routes)。⛔ **部材を持たない図の持ち物**なので★にしない。読んで数だけ出す
        if (HasKey(D, "routes"))
        {
            int niwa = 0, dosen = 0;
            foreach (var o in A(D["routes"])) { var r = O(o); if (StrOf(r, "kind") == "niwa") niwa++; else dosen++; }
            sb.AppendLine("  園路 " + niwa + " 本 / 動線 " + dosen + " 系統(⛔ 部材を持たない — 地表と点景で表す)");
        }
        // ---- 断面・視点の規則(gardenSections / viewpointRule)。図と検査の持ち物。数だけ出す
        if (HasKey(D, "gardenSections"))
            sb.AppendLine("  斜めの断面 " + A(D["gardenSections"]).Count + " 本(図の持ち物・実装は持たない)");

        // ---- 縁石(fuchi)。指図は物を宣言しているが**部材の名指しが無い**
        if (HasKey(D, "fuchi"))
            foreach (var o in A(D["fuchi"]))
            { var fc = O(o); pend.Add("縁石 " + StrOf(fc, "name") + "(" + StrOf(fc, "kind")
                + ")— 指図が部材(api)を持たないので据えていない"); }

        // ---- 板塀の根石。Stage6 の NeishiReport と同じ判定(部材待ち)
        if (HasKey(D, "nakajikiriRule")) pend.Add("板塀の根石(玉石)— **在庫に玉石の部材が無い**ので据えていない"
            + "(白い束石は世界 0.04m で根石の見え 0.15〜0.20m に隠れるので、玉石さえ焼ければ片づく。NeishiReport 参照)");

        foreach (var b in bad) sb.AppendLine("★ " + b);
        sb.AppendLine("庭: 不一致 " + bad.Count + " 件 / 部材待ちの申し送り " + pend.Count + " 件");
        for (int i = 0; i < pend.Count; i++) sb.AppendLine("    ⚠ " + pend[i]);
        // ⛔ 1行目に結論を置く(CheckScene は FirstLine を部門の見出しに使う)
        return (bad.Count == 0 ? "庭の不一致 0 件(⚠ 部材待ちの申し送り " + pend.Count + " 件)"
                               : "★ 庭の不一致 " + bad.Count + " 件(⚠ 部材待ち " + pend.Count + " 件)")
             + "\n" + sb.ToString();
    }
}
