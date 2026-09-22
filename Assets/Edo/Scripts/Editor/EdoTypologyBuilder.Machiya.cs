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
//   maguchi_ken … 1 軒の間口。軒数 = 辺長 ÷ 間口(⛔ 棟数を直に書かない)。
//                 その間口の駒を当方で起こしてあれば(5間 = `Own.Typ.Omotedana`)候補へ足す(EDO-0355)
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

    /// <summary>焼いてある**奥行を詰めた版**の奥行[間]。`EdoAssets.Own.Typ.Omotedana(float,float)` の注記の
    /// 5×3.85間。⚠ 焼き増したらここも足す — 無い駒は下の存在検査で落ちるので、足し忘れは詰め版が使われないだけ。</summary>
    const float OMOTEDANA_SHALLOW_KEN = 3.85f;

    /// <summary>その間口の表店を**当方で起こしてあるか**を資産の有無で見て、あれば**深い順**に返す
    /// (深い版 → 詰めた版)。⭐ 幅の数字(5)をここへ書かない — 4間の駒を焼けば黙って効く。
    /// 無ければ null(在庫の 2 点だけで建つ)。</summary>
    static string[] OmotedanaFor(int maguchiKen)
    {
        var l = new List<string>();
        foreach (var p in new[] { EdoAssets.Own.Typ.Omotedana(maguchiKen),
                                  EdoAssets.Own.Typ.Omotedana(maguchiKen, OMOTEDANA_SHALLOW_KEN) })
            if (UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(p) != null) l.Add(p);
        return l.Count > 0 ? l.ToArray() : null;
    }

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
            return string.Format("  町屋: 表店を建てない(表の pattern=none)— 間口 {0}間 / 奥行 {1}間 は読んだが効かせない{2}",
                                 s.maguchiKen, s.depthKen,
                                 // ⭐ 稲荷は表店の裏手へ据えるので、列が無ければ裏手が決まらない(黙って捨てない・規則19)
                                 s.inari ? " / ⚠ 表の inari=true も建てない(表店列が無く裏手が決まらない)" : "");

        var fronts = MachiyaFrontEdges(s, edges, front);
        if (fronts.Count == 0) return "  ⛔ 町屋: 接道辺が無く表店を載せる辺が採れない";

        var g = Group("Tatemono", root);
        // 自身番屋は**列の頭に 1 軒ぶん**として差す(⛔ 区画の中へ単独で散らさない)。
        string lead = s.jishinban ? EdoAssets.Eg.Jishinban : null;
        string[] ours = OmotedanaFor(s.maguchiKen);           // 表の間口の駒を起こしてあれば候補へ足す
        int totalPieces = 0, totalHouses = 0, wantTotal = 0, dropped = 0, clashed = 0;
        var built = new List<GameObject>();       // 先に建った列(両側町の角で取り合う)
        float roomFirst = 0f;                     // 辺0の背後の**実測**の奥行[m](裏長屋の割りに効かせる)
        float shopDeep = 0f;                      // 据えた表店が奥へ食った**実測**の最大[m](同)
        float worstJoint = float.NaN, worstWallGap = 0f, worstFace = float.NaN, restSum = 0f;
        int kinds = 0;
        var oursUsed = new HashSet<string>();

        for (int k = 0; k < fronts.Count; k++)
        {
            var e = fronts[k];
            bool hasGate = (e == front) && gateHalf > 0f;      // 木戸(路地口)はこの辺にだけ開く
            EdoBuild.MachiyaTally t;
            built.AddRange(EdoBuild.MachiyaRun(g, e.a, e.b, e.outward, pad, maguchiM, depthM,
                                hasGate ? gateC : Vector2.zero, hasGate ? gateHalf : -1f,
                                "Omotedana" + k, k == 0 ? lead : null, ours, poly,
                                k == 0 ? null : built, out t));
            clashed += t.clashed;
            if (k == 0) roomFirst = t.roomM;
            shopDeep = Mathf.Max(shopDeep, t.shopD);
            totalPieces += t.pieces; totalHouses += t.houses; wantTotal += t.wantHouses;
            dropped += t.dropped; restSum += t.restM;
            worstWallGap = Mathf.Max(worstWallGap, t.wallGapM);
            kinds = Mathf.Max(kinds, t.comboKinds);
            if (t.oursKind != null) oursUsed.Add(t.oursKind);
            if (!float.IsNaN(t.minJoint) && (float.IsNaN(worstJoint) || t.minJoint < worstJoint)) worstJoint = t.minJoint;
            if (!float.IsNaN(t.frontFace) && (float.IsNaN(worstFace) || t.frontFace > worstFace)) worstFace = t.frontFace;
            log.Add(string.Format(
                "    辺{0}({1:F1}m{2}): 軒 {3}/{4}(表の間口 {5}間={6:F2}m)・駒 {7}枚 {8}"
              + "・路地 {9:F2}m×{10}・端の余り {11:F2}m{12}",
                e.i, t.edgeLen, hasGate ? "・木戸の開口 " + (gateHalf * 2f).ToString("F1") + "m" : "",
                t.houses, t.wantHouses, s.maguchiKen, maguchiM, t.pieces, t.combos,
                t.rojiM, Mathf.Max(0, t.houses - 1), t.restM,
                t.dropped > 0 ? "・⛔ " + t.dropped + "枚は壁体が区画の外へ出るので退けた" : ""));
            if (t.roomM > 0f && t.roomM < depthM - 0.5f)
                log.Add(string.Format("      ⚠ 辺{0} の背後は実測 {1:F1}m しかない(表の depth_ken は {2}間={3:F1}m)"
                                    + " — 深い駒を候補から外した。表の奥行を検め直すこと",
                                      e.i, t.roomM, s.depthKen, depthM));
            if (t.tucked > 0)
                log.Add(string.Format("      辺{0}: {1}枚を区画の内へ最大 {2:F2}m 折り込んだ(斜めの側辺を跨ぐ列の端・裁定A)",
                                      e.i, t.tucked, t.tuckedM));
        }

        log.Insert(0, string.Format("  町屋: 表店 {0}軒 / 駒 {1}枚 — 接道辺 {2}本({3})",
            totalHouses, totalPieces, fronts.Count, s.twoSided ? "両側町" : "片側町"));
        if (ours != null)
            log.Add(string.Format("    当方の駒を候補へ足した: {0}(間口 {1}間・実寸で据える)",
                oursUsed.Count > 0 ? string.Join(" / ", oursUsed.ToArray()) : "⚠ どの辺も奥行に収まらず足せなかった", s.maguchiKen));
        if (totalHouses != wantTotal)
            log.Add(string.Format(
                "    ⚠ 表の間口で割ると {0}軒だが据わったのは {1}軒 — {2}"
              + "⛔ 非等方に伸ばしていない(軒の出と格子の目が伸びる)",
                wantTotal, totalHouses,
                oursUsed.Count > 0
                    ? "当方の駒を足したが、その幅の 1 軒を**継ぎ合わせた組**も混ざる/入りきらない端がある。"
                    : string.Format("**その間口の 1 軒を埋める駒が無い**(在庫は Shop01 {0:F2}m / Shop02 {1:F2}m の2点で、"
                                  + "採ったのは**継ぐ**方。当方の駒は {2}間の分が未焼き — 部材方 EDO-0318 ④/EDO-0348)。",
                          EdoBuild.ShopMeasure(EdoAssets.Eg.Shop01).W, EdoBuild.ShopMeasure(EdoAssets.Eg.Shop02).W, s.maguchiKen)));
        if (s.jishinban) log.Add("    自身番屋: 表店列の頭へ 1 軒ぶんとして差した(通りへ面する)");
        if (kinds == 1)
            log.Add(string.Format("    ⚠ 1軒の埋め方が1通りしかない(間口 {0}間={1:F2}m に対し他の組は誤差が大きすぎる)"
                                + " — **同じ駒が等間隔に並ぶ**。乱しようが無いのは候補の駒が少ないからで、直すのは部材の側(EDO-0348)",
                                s.maguchiKen, maguchiM));
        log.Add(string.Format("    通りとの取り合い: 店先の躯体の面が境界線から {0:+0.00;-0.00}m"
                            + " / 隣の軒との当たりの最小 {1} / 界壁に残る隙 最大 {2:F2}m(軒の出の和・閉じは「隙間>めり込み」)"
                            + " / 端の余りの合計 {3:F2}m",
            float.IsNaN(worstFace) ? 0f : worstFace,
            float.IsNaN(worstJoint) ? "—" : worstJoint.ToString("F3") + "m"
                + (worstJoint < 0f ? "(⛔ めり込み)" : ""),
            worstWallGap, restSum));
        if (dropped > 0) log.Add("    ⛔ 区画の外へ出て退けた駒 " + dropped + "枚 — その分だけ通りに歯抜けが残る");
        if (clashed > 0) log.Add("    角で先の列にめり込むので退けた駒 " + clashed
                               + "枚 — 両側町の二つの列が同じ角を取り合うため(角は空ける)");

        // ── 稲荷(EDO-0326)── ⭐ **裏長屋より先**に据える(置き方の4手① — 固定側を先に置く)。
        //    後にすると、裏長屋が奥行を埋め切った後で社の座が残らない。据えた社は built へ入るので、
        //    裏長屋の列はそれを避けて並ぶ。
        // ⭐ 表店が奥へ食った量は**据えた駒の実測**で採る(EDO-0355)。在庫の 2 点の寸法で代用すると、
        //    当方の 5 間の駒(Shop02 より 0.36m 深い)を使った辺で路地が痩せ、裏長屋へめり込む。
        float shopD = shopDeep > 0.5f ? shopDeep
                    : Mathf.Max(EdoBuild.ShopMeasure(EdoAssets.Eg.Shop01).D,
                                EdoBuild.ShopMeasure(EdoAssets.Eg.Shop02).D);
        string inari = Inari(s, root, poly, fronts, shopD, gateC, built);
        if (inari != null) log.Add(inari);

        log.Add(UraNagaya(s, root, poly, fronts, depthM, roomFirst, shopD, pad, built));
        log.Add(UnusedFields(s));
        return string.Join("\n", log.ToArray());
    }

    /// <summary>**裏長屋(裏店)。**表の `ura_nagaya` がそのまま数ならその棟数まで、
    /// 数でなければ**奥行と間口から割った列**を全部建てる(表の `defaults.machiya.ura_nagaya` が
    /// 「間口と奥行から割る」と約束している)。`0` は「建てるな」。
    ///
    /// <para>割り: 奥行 `depth_ken` から**表店の実測の奥行**と路地 1 間を引いた残りへ、棟と路地の帯を
    /// 奥へ積む。棟の実寸は <see cref="EdoAssets.Own.UraNagaya(float)"/> /
    /// <see cref="EdoAssets.Own.UraNagayaMunewari(float)"/>(2026-09-21・部材方 EDO-0318 ④)から
    /// **実測で**採り、⛔ 図面の 2 間・4 間という数字を奥行の代わりに使わない。</para>
    ///
    /// <para>⭐ **前後に路地がある列は棟割長屋**(奥行4間・両面に戸)で積む(2026-09-21・EDO-0318 ④の
    /// 取りこぼし)。1棟が路地2本ぶんを受け持つので、割長屋を2列背中合わせに並べるより**棟が1本で済み**、
    /// 奥行も 13.5m → 10.4m で済む。⛔ 割長屋を2棟背中合わせに置いて代用しない(部材の注記)。
    /// ⚠ **いちばん奥の列だけは割長屋** — 背が隣地の境に向くので盲面が要る。</para></summary>
    static string UraNagaya(Spec s, Transform root, Vector2[] poly, List<Edge> fronts, float depthM, float roomM,
                            float shopD, float pad, List<GameObject> avoid)
    {
        var d = s.raw;
        int want = I(d, "ura_nagaya", DERIVE);
        if (want == 0)
            return string.Format("    裏長屋: 建てない(表の ura_nagaya=0)— 奥行 {0}間={1:F1}m", s.depthKen, depthM);

        // ⭐ **表の depth_ken を鵜呑みにしない**(2026-09-22・EDO-0355)。表店は `MachiyaRun` が
        //    `EdgeDepth()` で区画を実測して駒を選んでいるのに、裏長屋の列だけは表の奥行から割っていた。
        //    表が実際より広く言う区画では奥の列が区画の外へ出て**丸ごと退けられ、そこが歯抜けになる**。
        //    採るのは表と実測の**小さい方**(表店と同じ作法)。⛔ 差を黙って飲まない(規則19)。
        string roomNote = "";
        if (roomM > 0f && roomM < depthM - 0.5f)
        {
            roomNote = string.Format("\n    ⚠ 割りに使ったのは**実測の奥行 {0:F1}m**(表の depth_ken {1}間={2:F1}m は"
                                   + " {3:F1}m 広く言っている)— 表の奥行を検め直すこと",
                                     roomM, s.depthKen, depthM, depthM - roomM);
            depthM = roomM;
        }

        var um = EdoBuild.OwnMeasure(EdoAssets.Own.UraNagaya(6f));          // 桁行が変わっても奥行は同じ
        var mw = EdoBuild.OwnMeasure(EdoAssets.Own.UraNagayaMunewari(6f));  // 棟割(奥行4間)

        // ⭐ **両側町は向かいの通りの表店が背後まで回り込んでいる**(2026-09-22・EDO-0355)。
        //    2026-09-22 まで奥行から引いていたのは手前の表店 1 列ぶんだけで、奥の列が向かいの表店の
        //    座へ割り付けられ、置いた端から退けられて**そこが歯抜けになっていた**(実測: 田町 chos_0 で
        //    156.3m・新町 ra で 65.4m)。向かい合う接道辺(外向きが背中合わせ)があるときは、
        //    **向かいの表店と路地も引く**。⛔ 角で交わる 2 辺では引かない(背後が重ならない)。
        float far = 0f;
        if (fronts.Count > 1 && Vector2.Dot(fronts[0].outward, fronts[1].outward) < -0.5f) far = shopD + ROJI;
        float avail = depthM - shopD - ROJI - far;
        // ⭐ 奥へ積む列を先に割る: 前後に路地がある列は**棟割**、いちばん奥の列だけ**割長屋**(盲面が要る)
        var plan = new List<KeyValuePair<float, bool>>();   // 引き[m] → 棟割か
        float cur = shopD + ROJI, rest = avail;
        while (true)
        {
            if (rest >= mw.D + ROJI + um.D)                 // 棟割 + 路地 + もう1列 が入る
            { plan.Add(new KeyValuePair<float, bool>(cur, true)); cur += mw.D + ROJI; rest -= mw.D + ROJI; }
            else if (rest >= um.D)                          // いちばん奥の列(背は隣地の境)
            { plan.Add(new KeyValuePair<float, bool>(cur, false)); break; }
            else break;
        }
        int rows = plan.Count;
        if (rows <= 0)
            return string.Format("    裏長屋: 建たない — 奥行 {0}間={1:F1}m から表店の実測の奥行 {2:F1}m と"
                               + "路地 {3:F1}m{6} を引くと残り {4:F1}m で、棟の実測 {5:F1}m が入らない【確度U】",
                                 s.depthKen, depthM, shopD, ROJI, avail, um.D,
                                 far > 0f ? string.Format("・向かいの表店と路地 {0:F1}m(両側町)", far) : "")
                 + roomNote;

        var g = Group("Tatemono", root);
        var e0 = fronts[0];                       // 路地は表店の列と平行に走る(1 本目の接道辺)
        int made = 0, dropped = 0, built = 0;
        float worst = float.NaN, gapSum = 0f;
        int nMune = 0;
        for (int r = 0; r < rows; r++)
        {
            int cap = want == DERIVE ? 0 : Mathf.Max(0, want - built);
            if (want != DERIVE && cap == 0) break;
            float inset = plan[r].Key;
            bool mune = plan[r].Value;
            int dr; float wg, gp;
            var got = EdoBuild.UraNagayaRun(g, e0.a, e0.b, e0.outward, pad, inset, cap,
                                            "UraNagaya" + r, poly, avoid, out dr, out wg, out gp, mune);
            if (mune) nMune += got.Count;
            avoid.AddRange(got);          // 次の列は前の列も避ける
            made += got.Count; built += got.Count; dropped += dr; gapSum += gp;
            if (!float.IsNaN(wg) && (float.IsNaN(worst) || wg < worst)) worst = wg;
        }
        return string.Format("    裏長屋 {0}棟(棟割 {12}棟 / 割長屋 {13}棟・{1}列・{2})— 割り: 奥行 {3}間={4:F1}m"
                           + " − 表店の実測 {5:F1}m − 路地 {6:F1}m{15} = {7:F1}m へ、棟割 {8:F1}m+路地 と"
                           + " 割長屋 {14:F1}m(いちばん奥)を積んで {9}列【確度U】"
                           + " / 棟どうしの当たりの最小 {10}{11}"
                           + "\n    ⚠ 1戸の間口は九尺(1.5間)で機械的に割ってある【一般類型A】— "
                           + "その筆に何戸あったかの史料は無い(部材の注記・確度U)",
            made, rows, want == DERIVE ? "表は数でないので割り出した" : "表の ura_nagaya=" + want + " を上限にした",
            s.depthKen, depthM, shopD, ROJI, avail, mw.D, rows,
            float.IsNaN(worst) ? "—" : worst.ToString("F3") + "m" + (worst < 0f ? "(⛔ めり込み)" : ""),
            dropped > 0 ? string.Format(" / 退けた掛け直し {0}回(区画の外・先の列との当たり)", dropped) : "",
            nMune, made - nMune, um.D,
            far > 0f ? string.Format(" − 向かいの表店と路地 {0:F1}m(両側町)", far) : "")
            + (gapSum > 0.01f
               ? string.Format("\n    ⛔ 歯抜けのまま残した走り {0:F1}m — 12→9→6間のどれも据わらない座"
                             + "(区画の外へ出る / 向かいの表店が背後まで回り込んでいる)", gapSum)
               : "")
            + roomNote;
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
        if (miss.Count == 0) return "    読んで使い道が無かった欄: 無し";
        return "    ⚠ 読んだが建つ姿に効かせていない欄: " + string.Join(" / ", miss.ToArray());
    }
}
