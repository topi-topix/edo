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
            EdoNishiTameikeBuilder.Place(api, new Vector3(w.x, TerrainY(w.x, w.y), w.y), 0f, Vector3.one, grp, "MZ_" + StrOf(nd, "id"));
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
        int nStone = 0;
        foreach (var o in A(D["tenkei"]))
        {
            var t = O(o); if (!HasKey(t, "stones")) continue;
            var sub = Group("Niwa/Ishigumi/" + StrOf(t, "name"));
            int i = 0;
            foreach (var so in A(t["stones"]))
            {
                var st = O(so); float u = HasKey(st, "u") ? F(st["u"]) : F(t["u"]); float v = HasKey(st, "v") ? F(st["v"]) : F(t["v"]);
                float show = F(st["show"]); float full = show / (1f - bury);
                Vector2 w = f.W(u, v); float gy = TerrainY(w.x, w.y);
                var go = EdoNishiTameikeBuilder.Place(EdoAssets.JG.Rock(1 + rnd.Next(3)),
                    new Vector3(w.x, gy - full * bury, w.y), (float)rnd.NextDouble() * 360f, Vector3.one, sub, StrOf(st, "name") ?? ("石" + i));
                if (go != null) { ScaleToHeight(go, full); nStone++; }
                i++;
            }
        }
        // 石組護岸: 帯ごとに汀線を歩き、`seatRule`(外向きに進んで最初に地面が waterY を超える点)へ据える
        int nGogan = 0; var gsub = Group("Niwa/Ishigumi/Gogan");
        foreach (var bo in A(gogan["bands"]))
        {
            var b = O(bo); int i0 = Convert.ToInt32(b["from"]), i1 = Convert.ToInt32(b["to"]);
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
                    // 外向き = 汀線の左右のうち池の外(輪郭の重心から遠い側)
                    Vector2 ctr = Vector2.zero; foreach (var s0 in shore) ctr += s0; ctr /= shore.Count;
                    Vector2 nrm = new Vector2(-(c - a).y, (c - a).x).normalized; if (Vector2.Dot(nrm, q - ctr) < 0) nrm = -nrm;
                    Vector2 seat = q; for (int k = 0; k < 40; k++) { seat = q + nrm * (k * 0.1f); if (TerrainY(seat.x, seat.y) > wy) break; }
                    float top = wy + Mathf.Lerp(aMin, aMax, (float)rnd.NextDouble());
                    float gy = TerrainY(seat.x, seat.y); float full = (top - gy) / (1f - bury);
                    var go = EdoNishiTameikeBuilder.Place(EdoAssets.JG.Rock(1 + rnd.Next(3)),
                        new Vector3(seat.x, gy - full * bury, seat.y), Mathf.Atan2((c - a).x, (c - a).y) * Mathf.Rad2Deg, Vector3.one, gsub, "護岸_" + nGogan);
                    if (go != null) { ScaleToHeight(go, full); nGogan++; }
                    pos += size * gap;
                }
                carry = pos - seg; idx++;
                if (idx % n == i1 % n) break;
                if (idx > i0 + n) break;
            }
        }
        sb.AppendLine(string.Format("石組 {0} 石 / 護岸 {1} 石(石橋は部材なし・据えず)", nStone, nGogan));
        return sb.ToString();
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
        foreach (var o in A(D["tenkei"]))
        {
            var t = O(o); if (HasKey(t, "stones")) continue;                  // 石組は 6c
            string kind = StrOf(t, "kind") ?? ""; string name = StrOf(t, "name");
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
                var probe = EdoNishiTameikeBuilder.Place(api, new Vector3(wa.x, TerrainY(wa.x, wa.y), wa.y), yaw, Vector3.one, grp, name + "_0");
                if (probe == null) { missing[kind] = missing.ContainsKey(kind) ? missing[kind] + 1 : 1; continue; }
                var rs = probe.GetComponentsInChildren<Renderer>(); var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
                float unit = Mathf.Max(0.3f, Vector3.Dot(bb.size, Quaternion.Euler(0, yaw, 0) * Vector3.forward).Equals(0) ? bb.size.x : Mathf.Abs(bb.size.z));
                int cnt = Mathf.Max(1, Mathf.RoundToInt(L / unit));
                for (int i = 1; i < cnt; i++)
                {
                    Vector2 q = Vector2.Lerp(wa, wb, (float)i / cnt);
                    EdoNishiTameikeBuilder.Place(api, new Vector3(q.x, TerrainY(q.x, q.y), q.y), yaw, Vector3.one, grp, name + "_" + i);
                }
                placed += cnt;
            }
            else if (HasKey(t, "u") && HasKey(t, "v"))
            {
                Vector2 w = f.W(F(t["u"]), F(t["v"]));
                var go = EdoNishiTameikeBuilder.Place(api, new Vector3(w.x, TerrainY(w.x, w.y), w.y), (float)rnd.NextDouble() * 360f, Vector3.one, grp, name);
                if (go != null) placed++;
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
        var f = Grid; var rnd = new System.Random(1856);
        var root = Group("Niwa/Planting"); Clear(root);
        // 主視点(傾ける向きの相手)
        var vps = new Dictionary<string, Vector2>();
        foreach (var o in A(D["viewpoints"])) { var vp = O(o); vps[StrOf(vp, "name")] = f.W(F(vp["u"]), F(vp["v"])); }
        int placed = 0, noPart = 0, nTerrain = 0; var byZone = new Dictionary<string, int>();
        foreach (var o in pts)
        {
            var p = O(o); string zone = StrOf(p, "zone") ?? "?";
            string api = ResolveApi(StrOf(p, "api"));
            if (api == null) { noPart++; continue; }
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
        sb.AppendLine(string.Format("植栽 {0} 本を据えた(うち法面=live terrain {1})/ 部材が解けず {2}", placed, nTerrain, noPart));
        foreach (var kv in byZone) sb.AppendLine("  " + kv.Key + ": " + kv.Value);
        return sb.ToString();
    }
}
