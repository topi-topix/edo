using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 土井 S8 植栽(案A・EDO-0533)── 林方の設計(指図 planting)を生成器が撒いた点 `doi_impl.json` の planting.points を据える。
//  ⭐ 撒くのは焼き手 `Tools/Sashizu/impl_doi.py` の bake_planting(⛔ 実装で撒き直さない)。
//  ⛔ 置き方はここに書かない(規則21)── 一本ずつの置き・据えは EdoBuild.PlantAtPoint、部材のキーは EdoBuild.PlantPathByKey。
public static partial class EdoDoiBuilder
{
    [MenuItem(MENU + "8 植栽(算出物の点を据える)")]
    public static void Stage8ShokusaiMenu() { Debug.Log("[Doi] " + Stage8_Shokusai()); }

    public static string Stage8_Shokusai()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var sb = new System.Text.StringBuilder("S8 植栽(案A):\n");
        var pl = IMPL.ContainsKey("planting") ? O(IMPL["planting"]) : null;
        var pts = pl != null && Has(pl, "points") ? A(pl["points"]) : null;
        if (pts == null)
            return "S8 植栽: ⛔ 算出物に planting.points が無い ── 据えない(python3 Tools/Sashizu/bake_impl.py doi --write で焼く)";
        // ⛔ 算出物の欄が据え置き(別の指図から焼かれたまま)なら据えない
        var bk = IMPL.ContainsKey("baked") ? O(IMPL["baked"]) : null;
        var car = bk != null && Has(bk, "carried") ? O(bk["carried"]) : null;
        if (car != null && car.ContainsKey("planting"))
            return "S8 植栽: ⛔ 算出物 planting が据え置き(前の指図のまま)── 据えない(bake_impl.py doi --write で焼き直す)";
        var grp = Group("Shokusai"); Clear(grp);
        var f = Grid;
        // ⭐ 据えは描かれた地表(縁の皮を含む)で ── 皮は Stage4b が起こした後に流す
        var drawn = EdoBuild.Drawn();
        // ⭐⭐ 硬い・許容0: 幹の芯を建物・塀・門・附属屋の**壁体の足元の外形**に立てない(EdoBuild.BodyHulls ── 軒は入れない)。
        //    焼き手(impl_doi.py `_Site.base_block`)も紙の外形で退けるが、紙は建った位置(練塀の控えは石垣の実測)を知らない ──
        //    正の輪は据えた現物の幹で測るここ(2026-10-05 EDO-0533 普請検査 第9巡: 中木0004 が練塀 E11_Hei_5 の中 0.266m)。
        var bodies = EdoBuild.BodyHulls(BodyGroups());
        int made = 0, noPart = 0, noAsset = 0, noPos = 0, seatBad = 0, vineSkip = 0, bodyBad = 0;
        var seatBadLog = new List<string>(); var bodyBadLog = new List<string>();
        var byGroup = new Dictionary<string, int>();
        var byLayer = new Dictionary<string, int>();
        var missing = new HashSet<string>();
        foreach (var o in pts)
        {
            var q = O(o); if (q == null) continue;
            string key = Has(q, "asset") ? S(q["asset"]) : null;
            string nm = Has(q, "name") ? S(q["name"]) : null;
            if (key == null) { noAsset++; continue; }
            // つるは宿主の据えた現物の幹径で絡める(岡部 PlantFromImpl の二巡目)── 土井の焼き手はつるを焼かない
            if (key.Contains("Tsuru")) { vineSkip++; continue; }
            string path = EdoBuild.PlantPathByKey(key, nm ?? key);
            if (!Exists(path)) { missing.Add(key + (path == null ? "" : " → " + path)); noPart++; continue; }
            // 点は世界 xz(`world`)。無ければ格子の (u, v)
            Vector2 c;
            var w = Has(q, "world") ? A(q["world"]) : null;
            if (w != null && w.Count >= 2) c = new Vector2(F(w[0]), F(w[1]));
            else if (Has(q, "u") && Has(q, "v")) c = f.W(F(q["u"]), F(q["v"]));
            else { noPos++; continue; }
            float tilt = F(Has(q, "tilt") ? q["tilt"] : null);
            Vector2 dirW = Vector2.up;
            if (Mathf.Abs(tilt) > 0.01f)
            {
                var d2 = Has(q, "tiltDir") ? A(q["tiltDir"]) : null;
                Vector2 dir = (d2 != null && d2.Count == 2) ? new Vector2(F(d2[0]), F(d2[1])) : Vector2.up;
                dirW = (f.W(dir.x, dir.y) - f.W(0f, 0f)).normalized;      // tiltDir は格子の向き
            }
            string lay = Has(q, "layer") ? S(q["layer"]) : "";
            string grpName = Has(q, "group") ? S(q["group"]) : "?";
            bool seated, refused; float bu, fl;
            string goName = nm ?? (grpName + "_" + made);
            var go = EdoBuild.PlantAtPoint(path, c, F(Has(q, "h") ? q["h"] : null), tilt, dirW, lay, grp,
                                           goName, drawn, out seated, out bu, out fl, out refused);
            if (refused)
            { seatBad++; if (seatBadLog.Count < 8) seatBadLog.Add(goName + " 埋没 " + bu.ToString("F2") + " 浮き " + fl.ToString("F2")); continue; }
            if (go == null) { missing.Add(key + " → " + path); noPart++; continue; }
            Vector2 tr;
            if (EdoBuild.PlantInBody(go, bodies, out tr))
            {
                bodyBad++; if (bodyBadLog.Count < 8) bodyBadLog.Add(goName + " (" + tr.x.ToString("F1") + "," + tr.y.ToString("F1") + ")");
                UnityEngine.Object.DestroyImmediate(go); continue;
            }
            made++;
            byGroup[grpName] = (byGroup.ContainsKey(grpName) ? byGroup[grpName] : 0) + 1;
            byLayer[lay] = (byLayer.ContainsKey(lay) ? byLayer[lay] : 0) + 1;
        }
        sb.Append("  ⭕ " + made + " 本据えた(点 " + pts.Count + ")");
        foreach (var kv in byLayer) sb.Append(" / " + kv.Key + " " + kv.Value);
        sb.AppendLine();
        foreach (var kv in byGroup) sb.AppendLine("    " + kv.Key + " " + kv.Value);
        if (noPart > 0) { sb.AppendLine("  ✗ 部材が引けず据えられない " + noPart); foreach (var k in missing) Wait("植栽の部材のキーが解けない: " + k); }
        if (noAsset > 0) sb.AppendLine("  ✗ asset の無い点 " + noAsset + "(在庫方の判断 ── 実装で見繕わない)");
        if (noPos > 0) sb.AppendLine("  ✗ 位置(world・u/v)の無い点 " + noPos);
        if (vineSkip > 0) sb.AppendLine("  ⚠ つる " + vineSkip + " ── 据えない(土井 Stage8 は宿主の幹径を測る二巡目を持たない)");
        sb.AppendLine("  " + (seatBad > 0 ? "⛔" : "⭕") + " 据え(幹の足の当たり): 埋没 ≤1.0・根元の浮き 0 を外れて建てなかった " + seatBad
                      + " 本(硬い ── 許容0 を破る点には建てない・docs/oki-kata.md §4a)" + (seatBadLog.Count > 0 ? "\n    " + string.Join(" / ", seatBadLog.ToArray()) : ""));
        sb.AppendLine("  " + (bodyBad > 0 ? "⛔" : "⭕") + " 幹の芯が壁体の足元の外形(" + bodies.Count + " 枚)の内で建てなかった " + bodyBad
                      + " 本(硬い ── 区域侵犯・焼き手の外形で退けきれなかった点)" + (bodyBadLog.Count > 0 ? "\n    " + string.Join(" / ", bodyBadLog.ToArray()) : ""));
        // 焼き手の名乗り(読めなかった欄・柔らかい制約の未達)をそのまま刷る ── ⛔ 黙って捨てない(規則19)
        var notes = pl != null && Has(pl, "notes") ? A(pl["notes"]) : null;
        if (notes != null && notes.Count > 0)
        {
            sb.AppendLine("  焼き手の名乗り " + notes.Count + " 件:");
            foreach (var n in notes) sb.AppendLine("    " + S(n));
        }
        sb.Append(WaitReport());
        return sb.ToString();
    }

    [MenuItem(MENU + "8b 植栽・庭の木の根元を据え直す(9・4b の後)")]
    public static void Stage8bSuenaoshiMenu() { Debug.Log("[Doi] " + Stage8b_RootReseat()); }

    /// <summary>**植栽・庭の木・刈込・下草の根元を、今の描かれた地表で据え直す**(EDO-0533 第11巡 ── 根元の浮き 19・最大 0.209)。
    /// S6 庭(6h)・S8 植栽で据えた後に S9 排水・S4b 縁の皮が地表を描き直すと、根元が古い高さに残って浮く。⇒ 地表を最後に触る巡(4b)の後にこれを流す。
    /// 相手 = 描かれた地表(皮の無い所は地形)── 検査(普請検査の根元の浮き)と同じ床。浮いた木だけを沈める(EdoBuild.ReseatRootBand・冪等)。
    /// 硬い: 根元の浮き 0・最も低い当たりの埋まり ≤ NiwaSet.PLANT_BURY_MAX。満たせない木は動かさず名指す。⛔ 置き方はここに書かない(規則21)。</summary>
    public static string Stage8b_RootReseat()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        var sb = new System.Text.StringBuilder("S8b 植栽の根元(9・4b の後):\n");
        var dg = EdoBuild.Drawn(); var pr = EdoBuild.Probe();
        Func<float, float, float> bed = (x, z) => { float d = dg.At(x, z); return float.IsNaN(d) ? pr.At(x, z) : d; };
        int n = 0, sunkN = 0, bad = 0; float worst = 0f; var badLog = new List<string>();
        foreach (var gn in new[] { "Shokusai", "Niwa/Shokusai", "Niwa/Karikomi", "Niwa/Shitakusa" })
        {
            var g = Group(gn); if (g == null) continue;
            foreach (Transform c in g)
            {
                if (!c.gameObject.activeInHierarchy) continue;
                float sk, fl; n++;
                bool ok = EdoBuild.ReseatRootBand(c.gameObject, bed, EdoBuild.NiwaSet.PLANT_BURY_MAX, out sk, out fl);
                if (sk > 0f) { sunkN++; worst = Mathf.Max(worst, sk); }
                if (!ok) { bad++; if (badLog.Count < 10) badLog.Add(gn + "/" + c.name + " 浮き " + (float.IsNaN(fl) ? "測れない" : fl.ToString("F3"))); }
            }
        }
        sb.AppendLine("  " + (bad > 0 ? "✗" : "⭕") + " " + n + " 本を測り、根元の浮きを沈めた " + sunkN + " 本(最大 " + worst.ToString("F3") + "m)"
                      + (bad > 0 ? "・沈めると埋まりが " + EdoBuild.NiwaSet.PLANT_BURY_MAX.ToString("F1") + " を超える/測れないので動かさなかった " + bad + " 本(硬い ── 名指す): " + string.Join(" / ", badLog.ToArray()) : ""));
        return sb.ToString();
    }
}
