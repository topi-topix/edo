using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// 土井 S6 柵・垣(案A・EDO-0533)── 指図 fences[] を読み、EdoBuild.GakiRun で敷く。
//  ⛔ 置き方はここに書かない(規則21)── 部材の解決と欄の読みだけ。
public static partial class EdoDoiBuilder
{
    [MenuItem(MENU + "6柵 柵・垣(案A)")]
    public static void Stage6SakuMenu() { Debug.Log("[Doi] " + Stage6_Saku()); }

    public static string Stage6_Saku()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var sb = new System.Text.StringBuilder("S6 柵・垣(案A):\n");
        int bad = 0, warn = 0;
        Action<int, string> line = (lv, t) => { sb.AppendLine("  " + (lv == 2 ? "✗" : lv == 1 ? "⚠" : "⭕") + " " + t); if (lv == 2) bad++; else if (lv == 1) warn++; };
        var grp = Group("Fuzoku/Saku"); Clear(grp);
        var f = Grid;
        foreach (var o in A(D["fences"]) ?? new List<object>())
        {
            var fc = O(o); string nm = S(fc["name"]), label = S(fc["label"]);
            if (!Has(fc, "h") || !Has(fc, "pts")) { line(2, nm + " " + label + ": 欄 h / pts が無い ── 建てない"); continue; }
            float h = F(fc["h"]);
            string span, post; string why = SakuPart(fc, h, out span, out post);
            if (span == null) { line(2, nm + " " + label + ": " + why + " ── 建てない"); continue; }
            if (!Exists(span)) { line(2, nm + " " + label + ": 部材が無い " + span + " ── 建てない"); continue; }
            if (post != null && !Exists(post)) { line(1, nm + ": 端柱が無い " + post); post = null; }
            var P = new List<Vector2>(); foreach (var q in A(fc["pts"])) { var p = A(q); P.Add(f.W(F(p[0]), F(p[1]))); }
            int n = 0, slope = 0; float worst = 0f;
            for (int i = 0; i + 1 < P.Count; i++)
            {
                int s; float w;
                n += EdoBuild.GakiRun(grp, P[i], P[i + 1], span, post, nm + "_" + i, GroundY, 0.30f, out s, out w).Count;
                slope += s; worst = Mathf.Max(worst, w);
            }
            string head = nm + " " + label + "(" + why + "・丈 " + h.ToString("0.0#") + "): " + n + " 駒";
            if (slope > 0) line(1, head + " ── 足の地盤の差が 0.30 を超える駒 " + slope + "(最大 " + worst.ToString("F2") + "m・斜面の途中に立つ疑い【柔】)");
            else line(0, head);
            if (Has(fc, "joints")) line(1, nm + ": 欄 joints(取り合い)は未実装 ── 線の端で止めた");
        }
        sb.Insert(0, "✗ " + bad + " / ⚠ " + warn + "\n");
        sb.Append(WaitReport());
        return sb.ToString();
    }

    /// <summary>柵の欄 part/kind → 部材(EdoAssets の名指し)。⛔ 無い名を推して当てない。</summary>
    static string SakuPart(Dictionary<string, object> fc, float h, out string span, out string post)
    {
        string part = S(fc["part"]) ?? "", kind = S(fc["kind"]) ?? "";
        span = post = null;
        if (part.Contains("丸太の二段柵") || kind.StartsWith("丸太の柵") || kind.StartsWith("埒"))
        { span = EdoAssets.Own.MarutaSaku(h); post = EdoAssets.Own.MarutaSakuPost(h); return "丸太の二段柵"; }
        if (part.Contains("KenninjiGaki") || part.StartsWith("建仁寺垣") || kind.StartsWith("建仁寺垣"))
        { span = EdoAssets.Own.KenninjiGaki(h); post = EdoAssets.Own.KenninjiGakiPost(h); return "建仁寺垣"; }
        if (part.Contains("YotsumeGaki") || kind.StartsWith("四つ目垣"))
        { span = EdoAssets.Own.YotsumeGaki(h); post = EdoAssets.Own.YotsumeGakiPost(h); return "四つ目垣"; }
        return "欄 part「" + part + "」を部材に解けない";
    }
}
