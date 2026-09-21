// 類型ビルダー — 稲荷(町屋の裏手の小祠と鳥居)。EDO-0326。
//
// ⭐ **何が欠けていたか**(2026-09-21): 表の `inari` は Spec へ読み込まれるのに一度も参照されず、
//    「読んだが建つ姿に効かせていない欄」として刷られるだけだった。小祠も鳥居も在庫に在る。
//
// ⛔ このファイルに置き方の算術を書かない(規則21)。据える・測る・離すのは
//    `EdoBuild.InariSet`(EdoBuildInari.cs)だけ。ここに書くのは「どの類型が何をどこへ」だけ。
// ⛔ 表に `inari` を持たない区画へ発明しない — 武家の邸内社は [西川1959]A で望ましいとされるが、
//    `defaults` に欄が無く全区画 false のままで、足すなら考証方の裁定が先(EDO-0317 ②)。
//
// 表の欄:
//   inari … true なら町内の稲荷を一社建てる(赤坂田町三丁目=三丁目稲荷 / 四丁目=西行稲荷)
//   jishinban … 自身番屋。**在れば稲荷はその裏**([文政町方書上] 四丁目「西行稲荷(自身番裏)」)

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    /// <summary>参道の長さ(祠の正面の**実面**から鳥居の柱の芯まで)= **1 間**【U 設計値】。
    /// 先例は指図の2邸 — 土井邸 `gardens[3].yashiro.sando` が 1.30m、岡部邸 `yashiro[0].sando` が 1.60m。
    /// どちらも江戸間の丸い数ではないので、類型は 1 間(1.818m)へ寄せた。
    /// ⛔ これは参道の**長さ**であって祠と鳥居の隙ではない — 実際の離れは据えてから測って刷る。</summary>
    const float SANDO_KEN = 1f;

    /// <summary>稲荷の駒と、既に建った駒の**軒込み外形**との最小の離れ[m]【U 設計値】。
    /// 参詣の人が回れるだけの余地で、これを割ると裏長屋の軒下に祠が入る。</summary>
    const float INARI_CLEAR = 1.0f;

    /// <summary>**町内の稲荷。**表店の列の背後(裏手)へ小祠を据え、その正面へ鳥居を立てる。
    ///
    /// <para>⭐ **表店の後・裏長屋の前**に建てる(置き方の4手① — 固定側を先に置く)。
    /// 据えた駒を <paramref name="built"/> へ足すので、裏長屋の列はこの社を避けて並ぶ。
    /// 逆にすると、裏長屋が奥行を埋め切った後で稲荷の座が無くなる。</para>
    ///
    /// <para>拠り所: **自身番屋が在ればその裏**(四丁目の西行稲荷は史料が「自身番裏」と書く)。
    /// 無ければ**表店列の端**(木戸から遠い側)の裏 — 位置の史料が無いので確度 U。</para></summary>
    static string Inari(Spec s, Transform root, Vector2[] poly, List<Edge> fronts, float shopD,
                        Vector2 gateC, List<GameObject> built)
    {
        if (!s.inari) return null;
        if (fronts == null || fronts.Count == 0) return "    ⛔ 稲荷: 接道辺が無く裏手が決まらない — 建てない";
        if (built == null || built.Count == 0) return "    ⛔ 稲荷: 表店が 1 枚も建っていないので裏手が決まらない — 建てない";

        var face = fronts[0].outward;          // 正面は表通りの側 — 参詣は路地を通りから来る【U】
        // 拠り所の駒 — 自身番屋(表の jishinban)を名前で拾う。⛔ 座標で探さない。
        string ban = System.IO.Path.GetFileNameWithoutExtension(EdoAssets.Eg.Jishinban);
        GameObject host = built.FirstOrDefault(o => o != null && o.name.EndsWith(ban));
        string how;
        if (host != null) how = "自身番屋の裏【A】";
        else
        {
            // 列の端(木戸から遠い側)。⛔ 区画の頂点や中心を裏手と呼ばない。
            host = built.Where(o => o != null)
                        .OrderByDescending(o => (new Vector2(o.transform.position.x, o.transform.position.z) - gateC).sqrMagnitude)
                        .FirstOrDefault();
            how = "表店列の端(木戸から遠い側)の裏【U — 位置の史料が無い】";
        }
        if (host == null) return "    ⛔ 稲荷: 拠り所の駒が採れない — 建てない";

        var rb = EdoBuild.RB(host);
        var anchor = new Vector2(rb.center.x, rb.center.z) - face * (shopD + ROJI);   // 表店の背後・路地1間の先
        var grp = Group("Yashiro", root);

        EdoBuild.InariTally t;
        var made = EdoBuild.InariSet(grp, "Inari", poly, EdoAssets.Own.Inari15, EdoAssets.Own.Torii,
                                     face, anchor, SANDO_KEN * KEN, built, INARI_CLEAR, out t);
        if (made.Count == 0)
            return string.Format("    ⛔ 稲荷: 建たない({0})— 拠り所は {1} / 候補 {2}点・試した座 {3}",
                                 t.why, how, t.cands, t.tried);

        built.AddRange(made);        // ⭐ 裏長屋はこの社を避ける(固定側を先に置いた)
        return string.Format(
            "    稲荷 1社(小祠+鳥居 2駒)— 裏手: {0} / 候補 {1}点・試した座 {2}"
          + "\n      参道: 指定 {3}間={4:F2}m(祠の正面の実面から鳥居の柱の芯まで)→ **実測の離れ** 躯体 {5}・軒込み {6}"
          + "\n      据え: 祠 接地の隙 {7:F3}m(着く頂点 {8})・沈め {9:F2}m / 鳥居 接地の隙 {10:F3}m(着く頂点 {11})・沈め {12:F2}m(根巻石)"
          + "\n      既に建った駒(軒込み)までの実測の離れ: 祠 {13:F2}m / 鳥居 {14:F2}m(目安 {15:F1}m)"
          + "\n      ⚠ 正面の向きは**表通りの側**に採った【U】— この2社の向きを書いた史料は無い",
            how, t.cands, t.tried, SANDO_KEN, SANDO_KEN * KEN,
            float.IsNaN(t.sandoM) ? "—" : t.sandoM.ToString("F2") + "m",
            float.IsNaN(t.sandoEaveM) ? "—" : t.sandoEaveM.ToString("F2") + "m"
                + (t.sandoEaveM < 0f ? "(⛔ めり込み)" : ""),
            t.gapShrine, t.touchShrine, t.sinkShrine, t.gapTorii, t.touchTorii, t.sinkTorii,
            t.clearShrine, t.clearTorii, INARI_CLEAR);
    }
}
