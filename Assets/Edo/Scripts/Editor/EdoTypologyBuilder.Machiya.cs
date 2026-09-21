// 類型ビルダー — 町屋(machiya)の段。24 区画。EDO-0325。
//
// ⭐ **何が狂っていたか**(2026-09-21): 町屋の表店は `Plan()` が `houses/6` を 2〜14 に丸めた棟数だけ
//    積み、`Spot()` が**区画の内側の格子点へばらばらに散らして**いた。町屋は通りに面して軒を接して
//    建つものなので姿が根本から違い、24 区画すべてがそうなっていた。
//
// ⛔ このファイルに置き方の算術を書かない(規則21)。並べる・突き付ける・据えるのは
//    `EdoBuild.MachiyaRun`(EdoBuildMachiya.cs)だけ。ここに書くのは「表のどの欄が何を決めるか」。
// ⛔ 座標を書かない(規則11)。辺は `Edges()`、径数は `typology.json`、パスは `EdoAssets.cs`(規則12)。
//
// 表の欄と、その欄がどこへ効くか:
//   two_sided   … 表店を建てる接道辺の本数(false=1本 / true=長い順に2本)
//   maguchi_ken … 1 軒の間口。軒数 = 辺長 ÷ 間口(⛔ 棟数を直に書かない)
//   depth_ken   … 表店列の背後の帯の深さ。深い駒を外す関門にもなる(桐畑の代地は 5 間しかない)
//   pattern     … "none" なら表店列を建てない
//   ura_nagaya  … 裏長屋の棟数の上限。数でなければ奥行から割った列を全部建てる。0 なら建てない
//   jishinban   … 自身番屋。表店列の頭に 1 軒ぶんとして差す
//   kamiyui / tanagari / shimatuya … ⛔ 使い道が決まっていない欄。黙って捨てず log に刷る(規則19)

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    // 路地(江戸間 1 間)。表店と裏長屋の間・裏長屋どうしの間に挟む。
    // ⛔ 棟の奥行はここに書かない — 部材の実測(EdoBuild.OwnMeasure)から採る(規則21)。
    const float ROJI = 1.818f;

    /// <summary>「数として書いていない」を表す番兵。⭐ <c>I(d, k, DERIVE)</c> は
    /// **欄が無い・null・数でない**のどれでも <see cref="DERIVE"/> を返す — 三つとも
    /// 「割り出せ」の意なので、それでちょうどよい。`defaults.machiya.ura_nagaya` には
    /// 「間口と奥行から割る」という**文の説明**が入っていて、数として読むとここへ落ちる。
    /// ⛔ 0 と混ぜない — `ura_nagaya: 0` は「割り出せ」ではなく「建てるな」。</summary>
    const int DERIVE = -1;

    /// <summary>**表店を載せる接道辺。**`two_sided=false` は 1 本、`true` は長い順に 2 本。
    /// 1 本目は Stage 1 が門(木戸)を据えた <paramref name="front"/> を採る — 門と列が別の辺に
    /// 散らないようにするため。<paramref name="front"/> が接道辺でなければ最長の接道辺。
    /// ⭐ Stage 2 はこの辺に**囲いを建てない** — 町屋の通りの側の囲いは表店の壁そのもので、
    /// 板塀を立てると店先が通りから隠れる(それが EDO-0325 の姿の狂いの半分)。</summary>
    public static List<Edge> MachiyaFrontEdges(Spec s, List<Edge> edges, Edge front)
    {
        var outp = new List<Edge>();
        if (s == null || s.type != "machiya") return outp;
        var d = s.raw;
        if (S(d, "pattern") == "none") return outp;                 // 表店列を建てない区画
        var roads = edges.Where(e => e.kind == EdgeKind.Road).OrderByDescending(e => e.len).ToList();
        if (roads.Count == 0) return outp;
        var first = (front != null && front.kind == EdgeKind.Road) ? front : roads[0];
        outp.Add(first);
        if (s.twoSided)
        {
            var second = roads.FirstOrDefault(e => e != first);
            if (second != null) outp.Add(second);
        }
        return outp;
    }

    /// <summary>**Stage 3m — 町屋。**表店の列(接道辺 1〜2 本)・自身番屋・裏長屋。
    /// 建てるのは <see cref="EdoBuild.MachiyaRun"/>、決めるのはここ。</summary>
    static string Machiya(Spec s, Transform root, Vector2[] poly, Edge front, List<Edge> edges, float pad,
                          Vector2 gateC, float gateHalf)
    {
        var d = s.raw;
        var log = new List<string>();
        float maguchiM = Mathf.Max(1, s.maguchiKen) * KEN;
        float depthM = Mathf.Max(1, s.depthKen) * KEN;
        string pattern = S(d, "pattern") ?? "auto";

        if (pattern == "none")
            return string.Format("  町屋: 表店を建てない(表の pattern=none)— 間口 {0}間 / 奥行 {1}間 は読んだが効かせない",
                                 s.maguchiKen, s.depthKen);

        var fronts = MachiyaFrontEdges(s, edges, front);
        if (fronts.Count == 0) return "  ⛔ 町屋: 接道辺が無く表店を載せる辺が採れない";

        var g = Group("Tatemono", root);
        // 自身番屋は**列の頭に 1 軒ぶん**として差す(⛔ 区画の中へ単独で散らさない)。
        string lead = s.jishinban ? EdoAssets.Eg.Jishinban : null;
        int totalPieces = 0, totalHouses = 0, wantTotal = 0, dropped = 0;
        float worstJoint = float.NaN, worstWallGap = 0f, worstFace = float.NaN, restSum = 0f;

        for (int k = 0; k < fronts.Count; k++)
        {
            var e = fronts[k];
            bool hasGate = (e == front) && gateHalf > 0f;      // 木戸(路地口)はこの辺にだけ開く
            EdoBuild.MachiyaTally t;
            EdoBuild.MachiyaRun(g, e.a, e.b, e.outward, pad, maguchiM, depthM,
                                hasGate ? gateC : Vector2.zero, hasGate ? gateHalf : -1f,
                                "Omotedana" + k, k == 0 ? lead : null, poly, out t);
            totalPieces += t.pieces; totalHouses += t.houses; wantTotal += t.wantHouses;
            dropped += t.dropped; restSum += t.restM;
            worstWallGap = Mathf.Max(worstWallGap, t.wallGapM);
            if (!float.IsNaN(t.minJoint) && (float.IsNaN(worstJoint) || t.minJoint < worstJoint)) worstJoint = t.minJoint;
            if (!float.IsNaN(t.frontFace) && (float.IsNaN(worstFace) || t.frontFace > worstFace)) worstFace = t.frontFace;
            log.Add(string.Format(
                "    辺{0}({1:F1}m{2}): 軒 {3}/{4}(表の間口 {5}間={6:F2}m)・駒 {7}枚 {8}"
              + "・路地 {9:F2}m×{10}・端の余り {11:F2}m{12}",
                e.i, t.edgeLen, hasGate ? "・木戸の開口 " + (gateHalf * 2f).ToString("F1") + "m" : "",
                t.houses, t.wantHouses, s.maguchiKen, maguchiM, t.pieces, t.combos,
                t.rojiM, Mathf.Max(0, t.houses - 1), t.restM,
                t.dropped > 0 ? "・⛔ " + t.dropped + "枚は壁体が区画の外へ出るので退けた" : ""));
        }

        log.Insert(0, string.Format("  町屋: 表店 {0}軒 / 駒 {1}枚 — 接道辺 {2}本({3})",
            totalHouses, totalPieces, fronts.Count, s.twoSided ? "両側町" : "片側町"));
        if (totalHouses != wantTotal)
            log.Add(string.Format(
                "    ⚠ 表の間口で割ると {0}軒だが据わったのは {1}軒 — **5間(9.09m)の1軒を埋める駒が在庫に無い**。"
              + "在庫は Shop01 {2:F2}m / Shop02 {3:F2}m の2点で、採ったのは**継ぐ**方(1軒=駒1〜2枚)。"
              + "⛔ 非等方に伸ばしていない。5間の駒は EDO-0318 ④(部材方)",
                wantTotal, totalHouses,
                EdoBuild.ShopMeasure(EdoAssets.Eg.Shop01).W, EdoBuild.ShopMeasure(EdoAssets.Eg.Shop02).W));
        if (s.jishinban) log.Add("    自身番屋: 表店列の頭へ 1 軒ぶんとして差した(通りへ面する)");
        log.Add(string.Format("    通りとの取り合い: 店先の躯体の面が境界線から {0:+0.00;-0.00}m"
                            + " / 隣の軒との当たりの最小 {1} / 界壁に残る隙 最大 {2:F2}m(軒の出の和・閉じは「隙間>めり込み」)"
                            + " / 端の余りの合計 {3:F2}m",
            float.IsNaN(worstFace) ? 0f : worstFace,
            float.IsNaN(worstJoint) ? "—" : worstJoint.ToString("F3") + "m"
                + (worstJoint < 0f ? "(⛔ めり込み)" : ""),
            worstWallGap, restSum));
        if (dropped > 0) log.Add("    ⛔ 区画の外へ出て退けた駒 " + dropped + "枚 — その分だけ通りに歯抜けが残る");

        log.Add(UraNagaya(s, root, poly, fronts, depthM, pad));
        log.Add(UnusedFields(s));
        return string.Join("\n", log.ToArray());
    }

    /// <summary>**裏長屋(裏店)。**表の `ura_nagaya` がそのまま数ならその棟数まで、
    /// 数でなければ**奥行と間口から割った列**を全部建てる(表の `defaults.machiya.ura_nagaya` が
    /// 「間口と奥行から割る」と約束している)。`0` は「建てるな」。
    ///
    /// <para>割り: 奥行 `depth_ken` から**表店の実測の奥行**と路地 1 間を引いた残りへ、
    /// 「棟(奥行 2 間)+ 路地 1 間」の帯を何本とれるか。棟の実寸は
    /// <see cref="EdoAssets.Own.UraNagaya(float)"/>(2026-09-21・部材方 EDO-0318 ④)から実測で採り、
    /// ⛔ 図面の 2 間という数字を高さや奥行の代わりに使わない。</para></summary>
    static string UraNagaya(Spec s, Transform root, Vector2[] poly, List<Edge> fronts, float depthM, float pad)
    {
        var d = s.raw;
        int want = I(d, "ura_nagaya", DERIVE);
        if (want == 0)
            return string.Format("    裏長屋: 建てない(表の ura_nagaya=0)— 奥行 {0}間={1:F1}m", s.depthKen, depthM);

        float shopD = Mathf.Max(EdoBuild.ShopMeasure(EdoAssets.Eg.Shop01).D,
                                EdoBuild.ShopMeasure(EdoAssets.Eg.Shop02).D);
        var um = EdoBuild.OwnMeasure(EdoAssets.Own.UraNagaya(6f));   // 桁行が変わっても奥行は同じ
        float band = um.D + ROJI;
        float avail = depthM - shopD - ROJI;
        int rows = Mathf.Max(0, Mathf.FloorToInt(avail / band));
        if (rows <= 0)
            return string.Format("    裏長屋: 建たない — 奥行 {0}間={1:F1}m から表店の実測の奥行 {2:F1}m と"
                               + "路地 {3:F1}m を引くと残り {4:F1}m で、棟の実測 {5:F1}m + 路地 {3:F1}m が入らない【確度U】",
                                 s.depthKen, depthM, shopD, ROJI, avail, um.D);

        var g = Group("Tatemono", root);
        var e0 = fronts[0];                       // 路地は表店の列と平行に走る(1 本目の接道辺)
        int made = 0, dropped = 0, built = 0;
        float worst = float.NaN;
        for (int r = 0; r < rows; r++)
        {
            int cap = want == DERIVE ? 0 : Mathf.Max(0, want - built);
            if (want != DERIVE && cap == 0) break;
            float inset = shopD + ROJI + r * band;
            int dr; float wg;
            var got = EdoBuild.UraNagayaRun(g, e0.a, e0.b, e0.outward, pad, inset, cap,
                                            "UraNagaya" + r, poly, out dr, out wg);
            made += got.Count; built += got.Count; dropped += dr;
            if (!float.IsNaN(wg) && (float.IsNaN(worst) || wg < worst)) worst = wg;
        }
        return string.Format("    裏長屋 {0}棟({1}列・{2})— 割り: 奥行 {3}間={4:F1}m − 表店の実測 {5:F1}m"
                           + " − 路地 {6:F1}m = {7:F1}m ÷ (棟 {8:F1}m + 路地 {6:F1}m) = {9}列【確度U】"
                           + " / 棟どうしの当たりの最小 {10}{11}"
                           + "\n    ⚠ 1戸の間口は九尺(1.5間)で機械的に割ってある【一般類型A】— "
                           + "その筆に何戸あったかの史料は無い(部材の注記・確度U)",
            made, rows, want == DERIVE ? "表は数でないので割り出した" : "表の ura_nagaya=" + want + " を上限にした",
            s.depthKen, depthM, shopD, ROJI, avail, um.D, rows,
            float.IsNaN(worst) ? "—" : worst.ToString("F3") + "m" + (worst < 0f ? "(⛔ めり込み)" : ""),
            dropped > 0 ? string.Format(" / ⛔ {0}棟は壁体が区画の外へ出るので退けた", dropped) : "");
    }

    /// <summary>⛔ **ビルダーが読みもしていない欄を黙って捨てない**(規則19)。
    /// 表に史料から起こした値が入っているのに、建つ姿のどこにも効いていないことを毎回刷る。</summary>
    static string UnusedFields(Spec s)
    {
        var d = s.raw;
        var miss = new List<string>();
        if (Bo(d, "kamiyui", false)) miss.Add("kamiyui=true(髪結床の駒が在庫に無い)");
        int tana = I(d, "tanagari", DERIVE);
        if (tana != DERIVE) miss.Add("tanagari=" + tana + "(店借の戸数 — 裏長屋の戸割りへ効かせる先が無い)");
        if (Bo(d, "shimatuya", false)) miss.Add("shimatuya=true(仕舞屋 — 表店と作り分ける駒が無い)");
        if (s.houses > 0) miss.Add("houses=" + s.houses + "(家数 — 軒数は辺長÷間口で出すので使わない)");
        if (s.inari) miss.Add("inari=true(小祠と鳥居は在庫にあるが据える段が無い — EDO-0317 ②)");
        if (miss.Count == 0) return "    読んで使い道が無かった欄: 無し";
        return "    ⚠ 読んだが建つ姿に効かせていない欄: " + string.Join(" / ", miss.ToArray());
    }
}
