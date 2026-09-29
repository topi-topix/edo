// 類型ビルダー — 寺社の境内(Stage 3〜4 の jisha 分)。本堂・庫裏・蔵・鐘楼・墓地・塔頭を置く。
//
// ⭐ 何を直したか(EDO-0354・2026-09-22):
//   ① 本堂の間数 — 表の `main_hall_ken`(16 区画)は 2026-09-21 まで**ビルダーが名を読みもしない欄**で、
//      6 間の坊と 7 間の寺が同じ `VK.BigHouse`/`House` で建っていた。今は間数ぴったりに焼いた入母屋の
//      本堂(`EdoBuild.Honden`)を建てる。
//   ② 置き場所の解き方 — 2026-09-21 まで jisha の棟も `Spot()` が「区画の内側 6m 引きの格子点へ、
//      型ごとの当て推量の半径で」置いていた。248 坪の成満寺では 6m 引きで内側が 16×19m しか残らず、
//      本堂と庫裏で埋まって**墓地と鐘楼が『区画に収まらず未建』**だった(4 棟のうち 2 棟)。
//      今は棟ごとの**実際の外形**(壁体と屋根の実メッシュから測った矩形)で置く。
//
// 【置き方】(寺の境内の作り — 山門→参道→本堂。墓地は本堂の背後、鐘楼は前寄りの隅)
//   ・本堂 … 門の軸の上、**軒先**が**門の駒の実面**から JISHA_FRONT 以上奥(緩める巡だけ壁体・辺の中点へ戻す)。
//           ⛔ 辺の中点から測らない — 奥行の深い山門では 6.0m のうち 4.2m を門自身が食った(成満寺 1.82m)。
//   ・参道 … 門から本堂の前面までの帯(半幅 JISHA_LANE)には**何も置かない**(前庭は空けるのが既定)。
//   ・庫裏・塔頭・二戸目以降 … 本堂の近く。
//   ・墓地・蔵 … 区画の縁へ寄せた帯の、奥(門から遠い側)。鐘楼 … 縁へ寄せた帯の、手前(門に近い側)。
//   ・壁体は区画の縁から JISHA_EDGE 以上内側(軒は境界を越えてよい・施主裁定A)。
//   ・棟どうしの離れは**屋根を含めて** 2.0m を目標にし、収まらなければ 1.0m → 0.3m へ緩める(⚠ を刷る)。
//   ・最後に**置いた実メッシュで**縁の侵犯と棟どうしのめり込みを測り、外れたら次の候補へ(規則5・21)。
//
// ⚠ `sanmon` の欄は門の欄(`gate`)と同じ物を二度書いている — 山門は GatePath() が表門として建てるので、
//    ここでは何も足さない(足すと境内に山門が 2 基立つ)。時の鐘(`tokinokane`)は鐘楼(`shoro`)が
//    無いときだけ鐘楼を足す。⚠ 時の鐘としての作り分け(丈・撞座・通りへの向き)は未実装。
// ⛔ 座標を書かない(規則11)。寸法は部材の実メッシュから測る。
// ⛔ 置く・据える・測るは EdoBuild の関数(規則21)。ここは「どの棟をどこの帯へ」だけ。

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static partial class EdoTypologyBuilder
{
    const float JISHA_EDGE  = 2.0f;   // 壁体の角から区画の縁までの最小(m)
    const float JISHA_FRONT = 6.0f;   // 門から本堂の前面までの最小(前庭)
    const float JISHA_LANE  = 2.5f;   // 参道の帯の半幅(m)
    const float JISHA_GRID  = 1.5f;   // 候補点の格子(m)
    const float JISHA_GAP_LOOSE = 1.0f;
    const float JISHA_GAP_TIGHT = 0.3f;   // 最後の手 — 軒どうしが触れかけるが棟どうしは離れている(めり込みは実測で弾く)
    // ⭐ 広さからの従属値(2026-09-27・EDO-0477 P4)。どれも【確度 U】── 考証方の目安(御府内寺社備考 B の 3 寺:
    //    澄泉寺 1,374 坪/本堂 121 坪 = 9%・光蔵院 107/12 = 11%・善正寺 101/30 = 30%)。全文 UserData/EDO0477_survey/F_kosho_jisha.json。
    //    ⛔ 史料の間数(確度 S/A/B)があればそちらが勝つ(JHallSizes)。
    const float JISHA_HALL_RATIO   = 0.09f;  // 寺の本堂の坪 ≈ 境内の坪 × 8〜10%
    const float JISHA_KYAKU_RATIO  = 0.5f;   // 客殿 ≈ 本堂の半ば(附属合計 ≈ 本堂の 1.0〜1.5 倍の内訳)
    const int   JISHA_N_BASE       = 4;      // 棟数 ≈ 4 + 境内 500 坪ごとに 1
    const float JISHA_N_PER_TSUBO  = 500f;
    const float JISHA_JITTER       = 1.5f;   // 附属の置き場の点数の揺らぎ[m](EDO-0476・区画ごとの種で決定的)
    const int   JISHA_TRIES        = 72;     // PlaceBest に試させる置き場の数(旧: 三巡 × 24)

    enum JMode { Main, Near, Back, Front }

    class JItem
    {
        public string label;
        public GameObject go;
        public JMode mode;
        public bool hyo;                      // 表の欄(kuri/graveyard/shoro/tacchu/kura)から起こした棟 ── 目標で足した棟と分けて数える(EDO-0464)
        public float[] wall = new float[4];   // 壁体の局所矩形 x0,x1,z0,z1
        public float[] roof = new float[4];   // 屋根込みの局所矩形
        public float yaw;                     // 既定の向き(度)
        public float rank;                    // 置く順(小さい順)
    }

    struct JCand { public Vector2 p; public float yaw; public float score; }

    // ───────────────────────── 矩形の下働き ─────────────────────────
    static Vector2[] JCorners(float[] e, Vector2 p, float yawDeg)
    {
        float r = yawDeg * Mathf.Deg2Rad;
        var ax = new Vector2(Mathf.Cos(r), -Mathf.Sin(r));     // 局所 +X(Unity の Y 回転)
        var az = new Vector2(Mathf.Sin(r), Mathf.Cos(r));      // 局所 +Z
        return new[]
        {
            p + ax * e[0] + az * e[2], p + ax * e[1] + az * e[2],
            p + ax * e[1] + az * e[3], p + ax * e[0] + az * e[3],
        };
    }

    static Vector2 JCenter(Vector2[] c) { return (c[0] + c[1] + c[2] + c[3]) * 0.25f; }

    /// <summary>凸四角形どうしの離れの下限[m](負ならめり込み)。4 本の分離軸のうち最大の隙。
    /// 斜めに向き合う角どうしの実距離はこれより大きいので、**安全側**に外れる。</summary>
    static float JSep(Vector2[] a, Vector2[] b)
    {
        float best = float.MinValue;
        for (int s = 0; s < 2; s++)
        {
            var q = s == 0 ? a : b;
            for (int i = 0; i < 2; i++)
            {
                var d = (q[i + 1] - q[i]).normalized;
                var n = new Vector2(-d.y, d.x);
                float a0 = float.MaxValue, a1 = float.MinValue, b0 = float.MaxValue, b1 = float.MinValue;
                foreach (var p in a) { float t = Vector2.Dot(p, n); a0 = Mathf.Min(a0, t); a1 = Mathf.Max(a1, t); }
                foreach (var p in b) { float t = Vector2.Dot(p, n); b0 = Mathf.Min(b0, t); b1 = Mathf.Max(b1, t); }
                best = Mathf.Max(best, Mathf.Max(b0 - a1, a0 - b1));
            }
        }
        return best;
    }

    /// <summary>矩形の四隅と各辺の 5 分点が、区画の内側で縁から margin 以上あるか。
    /// ⛔ 四隅だけ見ない — 凹んだ区画では辺の途中で外へ出る。</summary>
    static bool JInside(Vector2[] poly, Vector2[] c, float margin)
    {
        for (int i = 0; i < 4; i++)
        {
            var a = c[i]; var b = c[(i + 1) % 4];
            for (int k = 0; k < 5; k++)
            {
                var p = Vector2.Lerp(a, b, k * 0.25f);
                if (!EdoGeom.PIP(poly, p) || EdoGeom.DistToPolyEdge(poly, p) < margin) return false;
            }
        }
        return true;
    }

    static float JMinEdge(Vector2[] poly, Vector2[] c)
    {
        float m = float.MaxValue;
        foreach (var p in c) m = Mathf.Min(m, EdoGeom.DistToPolyEdge(poly, p));
        return m;
    }

    /// <summary>駒の局所矩形(ピボットからの x0,x1,z0,z1)を実メッシュから測る。</summary>
    /// ⭐ withRoof=false は EdoBuild.BodyExRoof を使う(EDO-0358・2026-09-22)。JISHA_EDGE=2.0m の
    /// 壁体マージンは軒を除いた壁体で測るはずなのに、庫裏・墓地・鐘楼・山門が一枚メッシュのため
    /// Body(false) が屋根を落とせず、軒込みの外形に 2.0m が掛かって狭い敷地で棟が入らない一因だった。
    static bool JExt(GameObject go, bool withRoof, float[] e)
    {
        float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
        var pts = withRoof ? EdoBuild.Body(go.transform, 600, true) : EdoBuild.BodyExRoof(go.transform, 600);
        foreach (var w in pts)
        {
            var l = go.transform.InverseTransformPoint(w);
            x0 = Mathf.Min(x0, l.x); x1 = Mathf.Max(x1, l.x);
            z0 = Mathf.Min(z0, l.z); z1 = Mathf.Max(z1, l.z);
        }
        if (x1 < x0) return false;
        e[0] = x0; e[1] = x1; e[2] = z0; e[3] = z1;
        return true;
    }

    static float JYaw(Vector2 dirZ) { return Mathf.Atan2(dirZ.x, dirZ.y) * Mathf.Rad2Deg; }

    // ───────────────────────── 境内 ─────────────────────────
    /// <summary>寺社の境内を建てる。⭐ Omoya() の jisha 枝 — 返る文字列は「主屋と付属: …」の 2 行。</summary>
    static string JishaOmoya(Spec s, Transform root, Vector2[] poly, Edge front, float pad, Vector2 gateC)
    {
        var g = Group("Tatemono", root);
        var outward = front.outward;
        var inward = -outward;
        var vDir = inward; var uDir = new Vector2(vDir.y, -vDir.x);
        float yawMain = JYaw(outward);                 // 本堂の表(+Z)を門の方へ
        float yawVK = Mathf.Atan2(-outward.x, -outward.y) * Mathf.Rad2Deg;   // 従来の VK 駒の向き

        // ── 本堂の大きさ(2026-09-27・EDO-0477 P4 ── 施主「類型で建てた物が薄すぎる」)──────────────
        // ⭐ 寺(kind=temple)で表の間数が史料でない(確度 S/A/B でない)ときは、**境内の広さ × HALL_RATIO** を下限に採る。
        //    ⛔ それまでは表の U の間数そのまま ── 1,823 坪の観理院が 7×5 間(35 坪 = 目安の 1/5)だった。
        //    坊・社家(kind=bo/shake)の主屋は本堂でないので比を掛けない(比の典拠は寺の堂だけ)。
        // ⭐ 揺らぎ(EDO-0476): 目安の ±帯に入る焼いた入母屋のうちから区画ごとの種で選ぶ ── 同じ型の区画が同じ姿にならない。
        float tsubo = Mathf.Abs(EdoGeom.SignedArea(poly)) / (1.818f * 1.818f);
        var rng = new System.Random(JSeed(s.id));
        string hallCert = JCert(s, "main_hall_ken");
        bool hallFirm = hallCert == "S" || hallCert == "A" || hallCert == "B"
                     // ⭐ 棟をこの区画の絵図から採った筆(mune_zu)で、間数もその絵図から測った P は、他寺の比(U)より近い
                     //    (観理院 EDO-0468: 御宮絵図に本堂は無く、本坊 ≒ 20×6間 を主の堂に当てる)。
                     || (hallCert == "P" && s.muneZu);
        var hallSizes = JHallSizes(s, tsubo, hallFirm, rng, out string sizeNote);

        // ── 棟の一覧を起こす(置く前に**実メッシュの外形**を測る)──────────────
        var items = new List<JItem>();
        var dropped = new List<string>();
        int units = Mathf.Max(1, s.units);
        int hw = hallSizes[0][0], hd = hallSizes[0][1];
        string hallNote = sizeNote;
        GameObject firstHall = null;
        // ⭐ 庫裏は本堂より格を落とした専用駒(EDO-0354・2026-09-22)。以前は VK.SmallHouse
        //    (実測14.49×10.49m・本堂とほぼ同大)を当てていて、狭い境内でまず庫裏が「収まらず未建」に
        //    落ちていた。焼いた寸法は 6x4間 / 5x3.5間 の2本だけ(EdoAssets.Own.Kuri)。本堂が
        //    6間以下(坊)なら小さい方、7間級(寺・社家)なら大きい方を当てる。
        string kuriPath = hw <= 6 ? EdoAssets.Own.Kuri(5f, 3.5f) : EdoAssets.Own.Kuri(6f, 4f);
        for (int u = 0; u < units; u++)
        {
            string nm = "Honden" + (units > 1 ? "_" + u : "");
            GameObject h;
            string note;
            if (firstHall == null) { h = EdoBuild.Honden(g, nm, hw, hd, out note); if (h != null) firstHall = h; }
            else { h = UnityEngine.Object.Instantiate(firstHall, g); h.name = nm; note = "複製"; }
            if (h == null) { dropped.Add(note); continue; }
            if (u == 0) hallNote = note + (string.IsNullOrEmpty(hallNote) ? "" : "(" + hallNote + ")");
            items.Add(new JItem { label = nm, go = h, mode = u == 0 ? JMode.Main : JMode.Near, yaw = yawMain, rank = u == 0 ? 0f : 3f + u });
            if (s.kuri && units > 1) JAdd(items, dropped, g, "Kuri_" + u, kuriPath, JMode.Near, yawVK, 3.5f + u, true);
        }
        if (s.kuri && units == 1) JAdd(items, dropped, g, "Kuri", kuriPath, JMode.Near, yawVK, 3f, true);
        if (s.graveyard) JAdd(items, dropped, g, "Bochi", EdoAssets.Own.Bochi(6f, 4f), JMode.Back, yawVK, 1f, true);
        if (s.shoro || s.tokinokane) JAdd(items, dropped, g, "Shoro", EdoAssets.Own.Shoro(3f), JMode.Front, yawVK, 2f, true);
        for (int k = 0; k < Mathf.Clamp(s.tacchu, 0, 4); k++)
            JAdd(items, dropped, g, "Tacchu" + k, EdoAssets.VK.SmallHouse, JMode.Near, yawVK, 4f + k, true);
        for (int k = 0; k < Mathf.Clamp(s.kura, 0, 2) * units; k++)
            JAdd(items, dropped, g, "Kura" + k, EdoAssets.Eg.Kura, JMode.Back, yawVK, 5f + k, true);

        // 護摩堂(表の gomado・絵図に在る筆だけ)── 焼いた入母屋のうち 3x3間に最も近い小堂【間数 U】
        if (s.gomado)
        {
            string gn;
            var gs = JPickSize(9f, rng, 3);
            var gh = gs == null ? null : EdoBuild.Honden(g, "Gomado", gs[0], gs[1], out gn);
            if (gh != null) items.Add(new JItem { label = "Gomado", go = gh, mode = JMode.Front, yaw = yawVK, rank = 3.5f });   // 絵図は北の門の脇 ── 鐘楼と同じ手前の縁
        }
        // ── 棟数の目標(2026-09-27・EDO-0477 P4)── 4 棟 + 境内 500 坪ごとに 1 棟【U】(考証方: 御府内寺社備考の 3 寺 B からの目安)。
        //    足りない分は寺なら客殿(本堂の半ばの入母屋)→ 蔵 → 物置、坊・社家は蔵 → 物置の順に足す。
        //    ⛔ 棟の種別を推定で既成事実にしない ── 足した棟は名に出し、log に「目標で足した」と刷る(規則7)。
        int nTarget = JISHA_N_BASE + Mathf.FloorToInt(tsubo / JISHA_N_PER_TSUBO);
        var added = new List<string>();
        int kuraN = items.Count(i => i.label.StartsWith("Kura")), monoN = 0;
        bool kyakuDone = s.kind != "temple";
        // 棟は絵図から採った(表の mune_zu)── 目安で足さない。絵図に客殿が在れば(kyakuden)それだけ建てる
        if (s.muneZu) nTarget = items.Count + dropped.Count + (s.kyakuden && s.kind == "temple" ? 1 : 0);
        while (items.Count + dropped.Count < nTarget && added.Count < 6)
        {
            if (!kyakuDone)
            {
                kyakuDone = true;
                var ks = JPickSize(hw * hd * JISHA_KYAKU_RATIO, rng, 3);
                string kn;
                var kh = ks == null ? null : EdoBuild.Honden(g, "Kyakuden", ks[0], ks[1], out kn);
                if (kh != null)
                {
                    items.Add(new JItem { label = "Kyakuden", go = kh, mode = JMode.Near, yaw = yawVK, rank = 3.2f });
                    added.Add(string.Format("客殿 {0}x{1}間", ks[0], ks[1]));
                    continue;
                }
            }
            if (s.muneZu) break;
            if (kuraN <= monoN)
            {
                JAdd(items, dropped, g, "Kura" + kuraN, EdoAssets.Eg.Kura, JMode.Back, yawVK, 5f + kuraN);
                added.Add("蔵"); kuraN++;
            }
            else
            {
                JAdd(items, dropped, g, "Monooki" + monoN, EdoAssets.Own.Typ.SakujiKoya, JMode.Back, yawVK, 6.5f + monoN);
                added.Add("物置(作事小屋の駒で代用)"); monoN++;
            }
        }
        int want = items.Count + dropped.Count;
        items = items.OrderBy(i => i.rank).ToList();

        // 縁の向き(帯へ寄せる駒の向きの候補)
        var edgeYaws = new List<float>();
        for (int i = 0; i < poly.Length; i++)
        {
            if ((poly[(i + 1) % poly.Length] - poly[i]).magnitude < 0.5f) continue;
            var n = EdoGeom.InwardNormal(poly, i);
            float y = JYaw(n);
            foreach (var yy in new[] { y, y + 180f })
                if (!edgeYaws.Any(e => Mathf.Abs(Mathf.DeltaAngle(e, yy)) < 3f)) edgeYaws.Add(yy);
        }

        // ── 参道の起点 = **門の駒が敷地の内へ張り出している所**(規則21・2026-09-22)────────────
        // ⛔ 辺の中点 `gateC` を起点にしない。山門は奥行が深く、さらに敷地の内へ折り込むので、
        //    6.0m のうち 4.2m を門自身が食って前庭が 1.82m しか残らなかった(成満寺)。
        //    ⚠ 門を建てない型(`kouyuu` など)では `Mon` の群が空 — そのときは 0(= 従来どおり中点から)。
        float gInRoof = 0f, gInWall = 0f;
        var monT = root.Find("Mon");
        if (monT != null)
        {
            foreach (var w in EdoBuild.Body(monT, 1200, true))
                gInRoof = Mathf.Max(gInRoof, Vector2.Dot(new Vector2(w.x, w.z) - gateC, vDir));
            foreach (var w in EdoBuild.Body(monT, 1200, false))
                gInWall = Mathf.Max(gInWall, Vector2.Dot(new Vector2(w.x, w.z) - gateC, vDir));
            gInRoof = Mathf.Max(gInRoof, gInWall);
        }

        // ── 置く ── ⭐ 置き場は EdoBuild.PlaceBest で選ぶ(2026-09-27・EDO-0477 P4。docs/oki-kata.md §4a)。
        //    硬い制約 = 壁体が区画の外・棟どうしの突き抜け(見て違和感の出る重なり・部材どうしの埋め込みとは別)・接地(許容0 = 退ける)。
        //    柔らかい制約 = 棟どうしの離れ(屋根込み)MIN_BLDG_GAP・本堂の前庭(軒先から)JISHA_FRONT(狙い = 最も近い所へ建てて ⚠)。
        //    ⛔ それまでは自前の三巡(離れ 2.0 → 1.0 → 0.3)で、狙いを関門として書いていた。
        //    候補の並びは「狙いの帯(2.0 / 1.0 / 0.3)→ 置き方の点数」── 狙いを満たす所が先に試される。
        float mnx = poly.Min(p => p.x), mxx = poly.Max(p => p.x), mnz = poly.Min(p => p.y), mxz = poly.Max(p => p.y);
        var taken = new List<Vector2[]>();           // 置いた棟の屋根込みの矩形
        var takenWall = new List<Vector2[]>();       // 置いた棟の壁体の足あと(平場の束ねを置く段で見る ── EdoBuild.PadSqueeze)
        // ⭐ 囲いの長屋も棟として数える(2026-09-29 EDO-0477 施主裁定C)── 囲い(Stage 2)は境内の棟より先に建つので、
        //    長屋の屋根込みの矩形を先に積んでおけば、離れの硬い下限(JISHA_GAP_TIGHT)と狙い(MIN_BLDG_GAP)が長屋にも効く。
        //    ⛔ それまで境内の棟は境内の棟どうしだけを避け、観理院の本堂の柱が東の長屋の壁へ 0.6m 食い込んでいた。
        int enclN = JEnclosureRoofs(root, taken);
        var made = new List<GameObject>();
        Vector2[] lane = null;
        Vector2 hallC = poly.Aggregate(Vector2.zero, (a, q) => a + q) / poly.Length; bool hallDone = false;
        int placedN = 0;
        float worstPair = float.NaN; bool loose = false, tight = false;
        var tally = new EdoBuild.SeiyakuTally();
        float hallArea = 0f, annexArea = 0f;
        int hallTry = 0;
        bool hallTurn = false;   // 表を門へ向けては収まらず、本堂を 90° 振って探している(EDO-0472)

        for (int ii = 0; ii < items.Count; ii++)
        {
            var it = items[ii];
            if (!JExt(it.go, false, it.wall) || !JExt(it.go, true, it.roof))
            { dropped.Add(it.label + "の外形が測れない"); UnityEngine.Object.DestroyImmediate(it.go); continue; }
            var tmpl = it.go; tmpl.SetActive(false);   // 型紙(置くたびに複製し、退けた複製は PlaceBest が消す)

            var cands = new List<JCand>();
            // ⭐ 本堂の表を門へ向けるのは**狙い**(柔らかい・EDO-0472)── 向けては収まらない境内(細長い平場を門の軸が縦に貫く
            //    智乗院)に限り、90° 振った向きで探し直す。⛔ 2026-09-28 まで向きは硬く、本堂を建てずに落とした。
            var yaws = it.mode == JMode.Main && hallTurn ? new List<float> { it.yaw + 90f, it.yaw - 90f } : new List<float> { it.yaw };
            // ⭐ Near(庫裏・塔頭)も縁の向きを試す(2026-09-22・EDO-0354 退行の直し)。
            if (it.mode != JMode.Main) yaws.AddRange(edgeYaws);
            for (float x = mnx; x <= mxx; x += JISHA_GRID)
                for (float z = mnz; z <= mxz; z += JISHA_GRID)
                {
                    var p = new Vector2(x, z);
                    if (!EdoGeom.PIP(poly, p) || EdoGeom.DistToPolyEdge(poly, p) < JISHA_EDGE) continue;
                    foreach (var yaw in yaws)
                    {
                        var wc = JCorners(it.wall, p, yaw);
                        if (!JInside(poly, wc, JISHA_EDGE)) continue;
                        // ⭐ 平場が取れない所は**候補の段で**外す(下の硬い制約と同じ判定・地形と区画の形だけで決まる)(EDO-0472)。
                        //    ⛔ 候補のままにすると PlaceBest の試行 JISHA_TRIES を門に近い細い所で使い切り、奥の平場へ届かない
                        //    (智乗院: 細長い平場の先に門 → 本堂 3 寸法 × 2 向きが全部「収まらず」)。
                        if (EdoBuild.PadSqueeze(poly, wc, ZOSEI_MARGIN, takenWall) != 0)
                        { EdoBuild.SeiyakuTally.Inc(tally.HardRejected, "平場が取れない(区画の縁に近い斜面)"); continue; }
                        var rc = JCorners(it.roof, p, yaw);
                        float gm = JGapTo(rc, taken);
                        if (gm < JISHA_GAP_TIGHT) continue;
                        if (lane != null && it.mode != JMode.Main && JSep(rc, lane) < 0.5f) continue;
                        var c = JCenter(wc);
                        float vc = Vector2.Dot(c - gateC, vDir);
                        float sc; int tier = gm >= MIN_BLDG_GAP ? 0 : gm >= JISHA_GAP_LOOSE ? 1 : 2;
                        switch (it.mode)
                        {
                            case JMode.Main:
                            {
                                // ⭐ 参道の**見えの長さ**を決めるのは壁体でなく**軒先**(2026-09-22)。
                                //    起点は三手: 0=門の軒の内端 / 1=門の壁体の内端 / 2=辺の中点(従来)── 帯の並びで表す。
                                float vfR = rc.Min(q => Vector2.Dot(q - gateC, vDir));
                                float vfW = wc.Min(q => Vector2.Dot(q - gateC, vDir));
                                if (vfW < JISHA_FRONT) continue;                                   // 最後の手(辺の中点から 6m)も届かない所
                                int ft = vfR >= gInRoof + JISHA_FRONT ? 0 : vfW >= gInWall + JISHA_FRONT ? 1 : 2;
                                tier = Mathf.Max(tier, ft);
                                sc = 2f * Mathf.Abs(Vector2.Dot(c - gateC, uDir)) + vfR;      // 軸の上・手前寄り
                                break;
                            }
                            case JMode.Near:  sc = Vector2.Distance(c, hallC); break;
                            case JMode.Back:  sc = JMinEdge(poly, wc) - 0.35f * vc; break;
                            default:          sc = JMinEdge(poly, wc) + 0.35f * vc; break;
                        }
                        // ⭐ 揺らぎ(EDO-0476)── 附属は区画ごとの種で点数を ±JISHA_JITTER[m] 揺らす(本堂は軸に載せるので揺らさない)
                        if (it.mode != JMode.Main) sc += JISHA_JITTER * (float)(rng.NextDouble() * 2.0 - 1.0);
                        cands.Add(new JCand { p = p, yaw = yaw, score = sc + tier * 1e4f });
                    }
                }
            cands.Sort((a, b) => a.score.CompareTo(b.score));

            var itL = it;
            Func<JCand, GameObject> place = cd =>
            {
                var go = UnityEngine.Object.Instantiate(tmpl, g);
                go.name = itL.label; go.SetActive(true);
                go.transform.SetPositionAndRotation(new Vector3(cd.p.x, pad, cd.p.y), Quaternion.Euler(0f, cd.yaw, 0f));
                try { EdoBuild.SeatOnGround(go, 0f, VERTS); }
                catch (Exception) { UnityEngine.Object.DestroyImmediate(go); return null; }
                return go;
            };
            var hards = new List<EdoBuild.Hard>
            {
                new EdoBuild.Hard("壁体が区画の外", go => OutsideBy(poly, go.transform, false) <= 0f),   // 軒は別勘定(裁定A)
                new EdoBuild.Hard("棟どうしの突き抜け", go =>
                {
                    foreach (var prev in made)
                    {
                        var d3 = PairDir(go, prev);        // ⛔ 基準点どうしで向けない(規則21)— 外形の中心どうし
                        if (d3.sqrMagnitude < 1e-4f) return false;
                        Vector3 pat; int pn;
                        float gp = EdoBuild.Contact(go, prev, d3.normalized, out pat, out pn, 0.01f, 0.5f, 800);
                        if (!float.IsNaN(gp) && gp < 0f) return false;
                    }
                    return true;
                }),
                // ⭐ 平場が取れる(2026-09-28 EDO-0477)── 区画の縁の法に縛られて足あとを平らに切り盛りできない所は退ける。
                //    ⛔ 造成の後で気付いても直せない(観理院の本堂が北の角から 2.7m で 浮き 1.72m・埋まり 0.92m)。
                new EdoBuild.Hard("平場が取れない(区画の縁に近い斜面)", go =>
                    EdoBuild.PadSqueeze(poly, JCorners(itL.wall, new Vector2(go.transform.position.x, go.transform.position.z), go.transform.eulerAngles.y), ZOSEI_MARGIN, takenWall) == 0),
            };
            var softs = new List<EdoBuild.Soft>
            {
                new EdoBuild.Soft("棟どうしの離れ(屋根込み)", MIN_BLDG_GAP, go => JGapTo(JRoofOf(itL, go), taken)),
            };
            if (it.mode == JMode.Main)
                softs.Add(new EdoBuild.Soft("本堂の前庭(門の軒から軒先まで)", JISHA_FRONT,
                    go => JRoofOf(itL, go).Min(q => Vector2.Dot(q - gateC, vDir)) - gInRoof));

            var placed = EdoBuild.PlaceBest(cands, JISHA_TRIES, place, hards, softs, tally);
            UnityEngine.Object.DestroyImmediate(tmpl);
            if (placed == null)
            {
                // ⭐ 本堂が入らなければ一回り小さい焼いた入母屋で建て直す(柔らかい: 目安の大きさは狙い)
                if (it.mode == JMode.Main && ++hallTry < hallSizes.Count)
                {
                    string nt;
                    var nh = EdoBuild.Honden(g, it.label, hallSizes[hallTry][0], hallSizes[hallTry][1], out nt);
                    if (nh != null)
                    {
                        hallNote += string.Format("・⚠ {0}x{1}間は境内に収まらず {2}", hw, hd, nt);
                        hw = hallSizes[hallTry][0]; hd = hallSizes[hallTry][1];
                        it.go = nh; ii--; continue;
                    }
                }
                if (it.mode == JMode.Main && !hallTurn)
                {
                    string nt;
                    var nh = EdoBuild.Honden(g, it.label, hallSizes[0][0], hallSizes[0][1], out nt);
                    if (nh != null)
                    {
                        hallTurn = true; hallTry = 0;
                        hallNote += string.Format("・⚠ {0}x{1}間まで表を門へ向けては収まらず、本堂を 90° 振って(表を横へ)探し直した({2})", hw, hd, nt);
                        hw = hallSizes[0][0]; hd = hallSizes[0][1];
                        it.go = nh; ii--; continue;
                    }
                }
                dropped.Add(it.label + "は境内に収まらず未建");
                it.go = null;
                continue;
            }
            it.go = placed;
            var rcP = JRoofOf(it, placed);
            float gP = JGapTo(rcP, taken);
            if (gP < MIN_BLDG_GAP) { if (gP >= JISHA_GAP_LOOSE) loose = true; else tight = true; }
            foreach (var prev in made)
            {
                var d3 = PairDir(placed, prev);
                Vector3 pat; int pn;
                float gp = EdoBuild.Contact(placed, prev, d3.normalized, out pat, out pn, 0.01f, 0.5f, 800);
                if (!float.IsNaN(gp) && (float.IsNaN(worstPair) || gp < worstPair)) worstPair = gp;
            }
            taken.Add(rcP);
            takenWall.Add(JCorners(it.wall, new Vector2(placed.transform.position.x, placed.transform.position.z), placed.transform.eulerAngles.y));
            made.Add(placed);
            placedN++;
            float wa = (it.wall[1] - it.wall[0]) * (it.wall[3] - it.wall[2]);
            if (it.mode == JMode.Main) hallArea += wa; else annexArea += wa;
            if (it.mode == JMode.Main)
            {
                var pp = new Vector2(placed.transform.position.x, placed.transform.position.z);
                var wc = JCorners(it.wall, pp, placed.transform.eulerAngles.y);
                hallC = JCenter(wc); hallDone = true;
                float vf = wc.Min(q => Vector2.Dot(q - gateC, vDir));
                // 参道 = 門から本堂の前面まで(半幅 JISHA_LANE)。以後の棟は入れない。
                lane = new[] { gateC - uDir * JISHA_LANE, gateC + uDir * JISHA_LANE,
                               gateC + uDir * JISHA_LANE + vDir * vf, gateC - uDir * JISHA_LANE + vDir * vf };
            }
        }
        // ⭐ **何を建てるつもりだったか**を毎回刷る(規則19)
        var kinds = new List<string>();
        foreach (var it in items)
        {
            kinds.Add(it.go != null && made.Contains(it.go) ? it.label : it.label + "(未建)");
        }
        string dr = dropped.Count > 0 ? "・⚠ " + string.Join(" / ", dropped.ToArray()) : "";
        // ⭐ 表の欄から起こした棟が建たないのは、目標で足した棟(物置など)が建たないのと重さが違う(EDO-0464)。
        //    ⛔ 両方を同じ「⚠ 収まらず未建」で刷ると、表の欄が姿に出ていないのに検査が ⭕ のまま見過ごされる(十坊の庫裏 2 坊)。
        //    直しは表の欄の上書き(規則4)か置き方 ── 狭い坊は「主屋が庫裏を兼ねる」(kuri=false)と表に書く。
        var hyoMiss = items.Where(i => i.hyo && (i.go == null || !made.Contains(i.go))).Select(i => i.label).ToList();
        if (hyoMiss.Count > 0) dr += string.Format("・⚠ 表の欄が建たない {0}({1})── 表を上書きするか置き方を直す", hyoMiss.Count, string.Join("・", hyoMiss.ToArray()));
        if (s.kind == "bo" && !s.kuri) dr += "・庫裏は主屋が兼ねる(表の kuri=false・典拠の「主屋(庫裏一体)」)";
        string ts = tally.Summary();
        if (!string.IsNullOrEmpty(ts)) dr += ts;
        if (enclN > 0) dr += string.Format("・囲いの長屋 {0} 駒を棟として避けた", enclN);
        if (!float.IsNaN(worstPair)) dr += string.Format("・棟どうしの当たりの最小 {0:F2}m{1}", worstPair,
            worstPair < MIN_BLDG_GAP ? "(⚠ 目安 " + MIN_BLDG_GAP.ToString("F1") + "m 未満)" : "");
        if (loose) dr += "・⚠ 境内が狭く棟どうしの離れを 1.0m へ緩めた棟がある";
        if (tight) dr += "・⚠ 境内が狭く屋根どうしが 0.3m まで寄った棟がある(壁体は離れている)";
        string tch = s.tacchu > 0 ? string.Format("・塔頭{0}寺(⚠ 子院の部材が無く小屋で代用)", s.tacchu) : "";
        string tkn = s.tokinokane ? "・時の鐘(⚠ 鐘楼は建つが時の鐘としての作り分けは未実装)" : "";
        string un  = units > 1 ? string.Format("・{0}戸割り", units) : "";
        string lay = hallDone ? string.Format("参道の帯を空けて本堂を軸へ(参道の起点は門の実面・辺の中点から {0:F2}m 奥)・墓地と蔵は奥の縁・鐘楼は手前の縁", gInRoof)
                              : "⛔ 本堂が置けなかった";
        // ⭐ 広さに見合うか(規則19 ── 目安を書いた以上、建った値を刷る)。目安はどれも【U】(考証方・御府内寺社備考の 3 寺 B から)。
        string mitate = string.Format("\n    広さ: 境内 {0:F0}坪・棟 {1}/目標 {2}{3}・本堂 {4:F0}坪 = 境内の {5:F1}%{6}・附属/本堂 {7:F2}(目安 1.0〜1.5・U){8}",
            tsubo, placedN, s.muneZu ? "なし(棟は絵図から・表の mune_zu)" : nTarget + "(4+500坪ごと1・U)", added.Count > 0 ? "(目標で足した: " + string.Join("・", added.ToArray()) + ")" : "",
            hallArea / (1.818f * 1.818f), 100f * hallArea / (1.818f * 1.818f) / Mathf.Max(1f, tsubo),
            s.kind == "temple" ? "(目安 8〜10%・U)" : "(坊・社家の主屋は比を掛けない)",
            hallArea > 0f ? annexArea / hallArea : 0f,
            hallArea > 0f && annexArea / hallArea < 1.0f ? " ⚠ 附属が目安に届かない" : "");
        return string.Format("  主屋と付属: {0}/{1}棟(型=jisha:{2}・{3}{4}){5}{6}{7}\n    仕様: {8} ／ 置き方: {9}{10}",
            placedN, want, s.kind ?? "jisha", hallNote, un, dr, tch, tkn,
            string.Join(" ", kinds.ToArray()), lay, mitate);
    }

    // ───────────────────────── 広さからの従属値(EDO-0477 P4)─────────────────────────
    /// <summary>区画 id からの決まった種(FNV-1a)。⛔ string.GetHashCode は実行ごとに変わり得るので使わない ── 二度建てても同じ姿。</summary>
    static int JSeed(string id)
    {
        unchecked
        {
            uint h = 2166136261u;
            foreach (char c in id ?? "") { h ^= c; h *= 16777619u; }
            return (int)(h & 0x7fffffff);
        }
    }

    /// <summary>表の欄の確度(`cert` の中の欄名)。無ければ null。</summary>
    static string JCert(Spec s, string key)
    {
        object c;
        if (s.raw == null || !s.raw.TryGetValue("cert", out c)) return null;
        var d = c as Dictionary<string, object>;
        object v;
        return d != null && d.TryGetValue(key, out v) && v != null ? v.ToString() : null;
    }

    static List<int[]> _hallBaked;
    /// <summary>焼いてある入母屋の間数(梁間 3 間以上・桁行/梁間 ≤ 1.8)。<see cref="EdoBuild.Honden"/> が建てられる大きさだけ。</summary>
    static List<int[]> JHallBaked()
    {
        if (_hallBaked != null) return _hallBaked;
        _hallBaked = new List<int[]>();
        for (int w = 3; w <= 40; w++)
            for (int d = 3; d <= w; d++)
            {
                if (w > d * 1.8f) continue;
                if (AssetDatabase.LoadAssetAtPath<GameObject>(EdoAssets.Goten.RoofIrimoya_(w, d)) != null) _hallBaked.Add(new[] { w, d });
            }
        return _hallBaked;
    }

    /// <summary>坪 <paramref name="area"/> に近い焼いた入母屋を一つ(目安の 0.85〜1.25 倍の帯から種で選ぶ・帯が空なら最寄り)。</summary>
    static int[] JPickSize(float area, System.Random rng, int minD)
    {
        var all = JHallBaked().Where(z => z[1] >= minD).ToList();
        if (all.Count == 0) return null;
        var band = all.Where(z => z[0] * z[1] >= area * 0.85f && z[0] * z[1] <= area * 1.25f).ToList();
        if (band.Count > 0) return band[rng.Next(band.Count)];
        return all.OrderBy(z => Mathf.Abs(z[0] * z[1] - area)).First();
    }

    /// <summary>本堂の間数の候補(先頭が第一候補、以下は境内に収まらないときの一回りずつ小さい物)。
    /// 史料の間数(確度 S/A/B)はそのまま。そうでなければ寺は「境内 × <see cref="JISHA_HALL_RATIO"/>」と表の間数の大きい方を
    /// 目安に、焼いた入母屋から種で選ぶ(揺らぎ)。</summary>
    static List<int[]> JHallSizes(Spec s, float tsubo, bool firm, System.Random rng, out string note)
    {
        int hw = s.hallW, hd = s.hallD;
        note = "";
        if (hw <= 0 || hd <= 0) { note = "⚠ 表に main_hall_ken が無い — 類型の既定(坊 6x4)を目安に"; hw = 6; hd = 4; }
        if (hw < hd) { int t = hw; hw = hd; hd = t; }
        var outp = new List<int[]>();
        if (firm) outp.Add(new[] { hw, hd });
        else
        {
            float tgt = hw * hd;
            if (s.kind == "temple" && tsubo * JISHA_HALL_RATIO > tgt)
            {
                tgt = tsubo * JISHA_HALL_RATIO;
                note += (note.Length > 0 ? "・" : "") + string.Format("表の {0}x{1}間(U)は境内 {2:F0}坪に小さく、目安 {3:F0}坪(境内の {4:P0}・U)から採った",
                                                                     hw, hd, tsubo, tgt, JISHA_HALL_RATIO);
            }
            var pick = JPickSize(tgt, rng, 3);
            outp.Add(pick ?? new[] { hw, hd });
        }
        float a0 = outp[0][0] * outp[0][1];
        foreach (var z in JHallBaked().Where(z => z[0] * z[1] < a0).OrderByDescending(z => z[0] * z[1]).Take(5)) outp.Add(z);
        return outp;
    }

    /// <summary>置いた棟の屋根込みの矩形(置いた位置と向きから ── 測った局所矩形を載せる)。</summary>
    static Vector2[] JRoofOf(JItem it, GameObject go)
    {
        return JCorners(it.roof, new Vector2(go.transform.position.x, go.transform.position.z), go.transform.eulerAngles.y);
    }

    /// <summary>囲いの長屋の駒ごとに、屋根込みの矩形(駒の向きの軸で実メッシュを測った外形)を <paramref name="taken"/> へ足す。
    /// ⛔ 駒の基準点で矩形を決めない(規則21)── 向きだけを駒の回転から採り、広がりは頂点で測る。返り値は足した数。</summary>
    static int JEnclosureRoofs(Transform root, List<Vector2[]> taken)
    {
        var kk = root.Find("Kakoi"); if (kk == null) return 0;
        int n = 0;
        foreach (Transform c in kk)
        {
            if (!c.name.StartsWith("nagaya")) continue;
            var pts = EdoBuild.Body(c, 600, true);
            if (pts.Count < 3) continue;
            var u = new Vector2(c.right.x, c.right.z).normalized; var v = new Vector2(-u.y, u.x);
            float u0 = float.MaxValue, u1 = float.MinValue, v0 = float.MaxValue, v1 = float.MinValue;
            foreach (var p in pts)
            {
                var q = new Vector2(p.x, p.z);
                float a = Vector2.Dot(q, u), b = Vector2.Dot(q, v);
                u0 = Mathf.Min(u0, a); u1 = Mathf.Max(u1, a); v0 = Mathf.Min(v0, b); v1 = Mathf.Max(v1, b);
            }
            taken.Add(new[] { u * u0 + v * v0, u * u1 + v * v0, u * u1 + v * v1, u * u0 + v * v1 });
            n++;
        }
        return n;
    }

    /// <summary>矩形から置いた棟の屋根の矩形までの最小の離れ(無ければ 99)。</summary>
    static float JGapTo(Vector2[] rc, List<Vector2[]> taken)
    {
        float m = 99f;
        foreach (var t in taken) m = Mathf.Min(m, JSep(rc, t));
        return m;
    }

    /// <summary>プレハブの駒を 1 つ起こして一覧へ足す。置けなかった理由は <paramref name="dropped"/> へ(黙って落とさない)。</summary>
    static void JAdd(List<JItem> items, List<string> dropped, Transform g, string name, string path,
                     JMode mode, float yaw, float rank, bool hyo = false)
    {
        try
        {
            var go = EdoBuild.Place(path, Vector3.zero, 0f, Vector3.one, g, name);
            items.Add(new JItem { label = name, go = go, mode = mode, yaw = yaw, rank = rank, hyo = hyo });
        }
        catch (Exception e) { dropped.Add(name + "の部材が読めない(" + e.Message + ")"); }
    }
}
