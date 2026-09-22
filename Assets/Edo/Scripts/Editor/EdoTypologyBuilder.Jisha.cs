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

    enum JMode { Main, Near, Back, Front }

    class JItem
    {
        public string label;
        public GameObject go;
        public JMode mode;
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

        // ── 棟の一覧を起こす(置く前に**実メッシュの外形**を測る)──────────────
        var items = new List<JItem>();
        var dropped = new List<string>();
        int units = Mathf.Max(1, s.units);
        int hw = s.hallW, hd = s.hallD;
        string hallNote = "";
        if (hw <= 0 || hd <= 0)
        {
            hallNote = "⚠ 表に main_hall_ken が無い — 類型の既定(坊 6x4)で建てる";
            hw = 6; hd = 4;
        }
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
            if (u == 0) hallNote = string.IsNullOrEmpty(hallNote) ? note : hallNote;
            items.Add(new JItem { label = nm, go = h, mode = u == 0 ? JMode.Main : JMode.Near, yaw = yawMain, rank = u == 0 ? 0f : 3f + u });
            if (s.kuri && units > 1) JAdd(items, dropped, g, "Kuri_" + u, kuriPath, JMode.Near, yawVK, 3.5f + u);
        }
        if (s.kuri && units == 1) JAdd(items, dropped, g, "Kuri", kuriPath, JMode.Near, yawVK, 3f);
        if (s.graveyard) JAdd(items, dropped, g, "Bochi", EdoAssets.Own.Bochi(6f, 4f), JMode.Back, yawVK, 1f);
        if (s.shoro || s.tokinokane) JAdd(items, dropped, g, "Shoro", EdoAssets.Own.Shoro(3f), JMode.Front, yawVK, 2f);
        for (int k = 0; k < Mathf.Clamp(s.tacchu, 0, 4); k++)
            JAdd(items, dropped, g, "Tacchu" + k, EdoAssets.VK.SmallHouse, JMode.Near, yawVK, 4f + k);
        for (int k = 0; k < Mathf.Clamp(s.kura, 0, 2) * units; k++)
            JAdd(items, dropped, g, "Kura" + k, EdoAssets.Eg.Kura, JMode.Back, yawVK, 5f + k);
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

        // ── 置く ────────────────────────────────────────────────
        float mnx = poly.Min(p => p.x), mxx = poly.Max(p => p.x), mnz = poly.Min(p => p.y), mxz = poly.Max(p => p.y);
        var taken = new List<Vector2[]>();           // 置いた棟の屋根込みの矩形
        var made = new List<GameObject>();
        Vector2[] lane = null;
        Vector2 hallC = poly.Aggregate(Vector2.zero, (a, q) => a + q) / poly.Length; bool hallDone = false;
        int placedN = 0, unseated = 0, clashed = 0;
        float worstPair = float.NaN; bool loose = false, tight = false;
        var log = new List<string>();

        foreach (var it in items)
        {
            if (!JExt(it.go, false, it.wall) || !JExt(it.go, true, it.roof))
            { dropped.Add(it.label + "の外形が測れない"); UnityEngine.Object.DestroyImmediate(it.go); continue; }

            bool ok = false;
            for (int pass = 0; pass < 3 && !ok; pass++)
            {
                float gap = pass == 0 ? MIN_BLDG_GAP : pass == 1 ? JISHA_GAP_LOOSE : JISHA_GAP_TIGHT;
                var cands = new List<JCand>();
                var yaws = new List<float> { it.yaw };
                // ⭐ Near(庫裏・塔頭)も縁の向きを試す(2026-09-22・EDO-0354 退行の直し)。
                //    以前は既定の1向き(yawVK)しか試さず、Back/Front だけ複数の候補角を試していた。
                //    参道の帯が門の実面から測るようになって本堂が奥へ寄った境内では、本堂の周りに
                //    残る空きが細長い帯状になり、1向きしか試さない庫裏だけが「収まらず未建」に落ちた
                //    (棟どうしの当たりが 6〜21m と余裕があるのに庫裏だけ建たない、という形で出た)。
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
                            var rc = JCorners(it.roof, p, yaw);
                            bool clear = true;
                            foreach (var t in taken) if (JSep(rc, t) < gap) { clear = false; break; }
                            if (!clear) continue;
                            if (lane != null && it.mode != JMode.Main && JSep(rc, lane) < 0.5f) continue;
                            var c = JCenter(wc);
                            float vc = Vector2.Dot(c - gateC, vDir);
                            float sc;
                            switch (it.mode)
                            {
                                case JMode.Main:
                                {
                                    // ⭐ 参道の**見えの長さ**を決めるのは壁体でなく**軒先**(2026-09-22)。
                                    //    壁体で 6m を測ると軒が 1.2m せり出し、門の屋根が本堂の軒の下へ潜って
                                    //    「門が本堂に貼り付いた」姿になった(成満寺・坊で軒先〜門の内端 3.28m)。
                                    //    ⛔ 狭い境内で本堂が建たなくなるのは本末転倒なので、緩める巡は壁体へ戻す。
                                    // 起点も三手で戻す: 0=門の軒の内端 / 1=門の壁体の内端 / 2=辺の中点(従来)
                                    float g0 = pass == 0 ? gInRoof : pass == 1 ? gInWall : 0f;
                                    var fc = pass == 0 ? rc : wc;
                                    float vf = fc.Min(q => Vector2.Dot(q - gateC, vDir));
                                    if (vf < g0 + JISHA_FRONT) continue;
                                    sc = 2f * Mathf.Abs(Vector2.Dot(c - gateC, uDir)) + vf;      // 軸の上・手前寄り
                                    break;
                                }
                                case JMode.Near:  sc = Vector2.Distance(c, hallC); break;
                                case JMode.Back:  sc = JMinEdge(poly, wc) - 0.35f * vc; break;
                                default:          sc = JMinEdge(poly, wc) + 0.35f * vc; break;
                            }
                            cands.Add(new JCand { p = p, yaw = yaw, score = sc });
                        }
                    }
                cands.Sort((a, b) => a.score.CompareTo(b.score));

                // ── 上位から**置いた実メッシュ**で検める ──
                for (int ci = 0; ci < cands.Count && ci < 24 && !ok; ci++)
                {
                    var cd = cands[ci];
                    it.go.transform.SetPositionAndRotation(new Vector3(cd.p.x, pad, cd.p.y), Quaternion.Euler(0f, cd.yaw, 0f));
                    try { EdoBuild.SeatOnGround(it.go, 0f, VERTS); }
                    catch (Exception) { unseated++; continue; }
                    if (OutsideBy(poly, it.go.transform, false) > 0f) continue;   // 壁体が外へ出たら退ける(軒は別勘定)
                    float worst = float.NaN; bool clash = false;
                    foreach (var prev in made)
                    {
                        var d3 = PairDir(it.go, prev);        // ⛔ 基準点どうしで向けない(規則21)— 外形の中心どうし
                        if (d3.sqrMagnitude < 1e-4f) { clash = true; break; }
                        Vector3 pat; int pn;
                        float gp = EdoBuild.Contact(it.go, prev, d3.normalized, out pat, out pn, 0.01f, 0.5f, 800);
                        if (!float.IsNaN(gp) && (float.IsNaN(worst) || gp < worst)) worst = gp;
                    }
                    if (clash || (!float.IsNaN(worst) && worst < 0f)) { clashed++; continue; }   // めり込み = 許容0
                    if (!float.IsNaN(worst) && (float.IsNaN(worstPair) || worst < worstPair)) worstPair = worst;
                    ok = true;
                    if (pass == 1) loose = true;
                    if (pass == 2) tight = true;
                    taken.Add(JCorners(it.roof, cd.p, cd.yaw));
                    made.Add(it.go);
                    placedN++;
                    if (it.mode == JMode.Main)
                    {
                        var wc = JCorners(it.wall, cd.p, cd.yaw);
                        hallC = JCenter(wc); hallDone = true;
                        float vf = wc.Min(q => Vector2.Dot(q - gateC, vDir));
                        // 参道 = 門から本堂の前面まで(半幅 JISHA_LANE)。以後の棟は入れない。
                        lane = new[] { gateC - uDir * JISHA_LANE, gateC + uDir * JISHA_LANE,
                                       gateC + uDir * JISHA_LANE + vDir * vf, gateC - uDir * JISHA_LANE + vDir * vf };
                    }
                }
            }
            if (!ok)
            {
                dropped.Add(it.label + "は境内に収まらず未建");
                UnityEngine.Object.DestroyImmediate(it.go);
            }
        }

        // ⭐ **何を建てるつもりだったか**を毎回刷る(規則19)
        var kinds = new List<string>();
        foreach (var it in items)
        {
            kinds.Add(made.Contains(it.go) ? it.label : it.label + "(未建)");
        }
        string dr = dropped.Count > 0 ? "・⚠ " + string.Join(" / ", dropped.ToArray()) : "";
        if (unseated > 0) dr += string.Format("・⛔ {0}回は接地箇所が測れなかった(部材のメッシュを検める)", unseated);
        if (clashed > 0) dr += string.Format("・{0}回は先の棟にめり込むので退けて置き直した", clashed);
        if (!float.IsNaN(worstPair)) dr += string.Format("・棟どうしの当たりの最小 {0:F2}m{1}", worstPair,
            worstPair < MIN_BLDG_GAP ? "(⚠ 目安 " + MIN_BLDG_GAP.ToString("F1") + "m 未満)" : "");
        if (loose) dr += "・⚠ 境内が狭く棟どうしの離れを 1.0m へ緩めた棟がある";
        if (tight) dr += "・⚠ 境内が狭く屋根どうしが 0.3m まで寄った棟がある(壁体は離れている)";
        string tch = s.tacchu > 0 ? string.Format("・塔頭{0}寺(⚠ 子院の部材が無く小屋で代用)", s.tacchu) : "";
        string tkn = s.tokinokane ? "・時の鐘(⚠ 鐘楼は建つが時の鐘としての作り分けは未実装)" : "";
        string un  = units > 1 ? string.Format("・{0}戸割り", units) : "";
        string lay = hallDone ? string.Format("参道の帯を空けて本堂を軸へ(参道の起点は門の実面・辺の中点から {0:F2}m 奥)・墓地と蔵は奥の縁・鐘楼は手前の縁", gInRoof)
                              : "⛔ 本堂が置けなかった";
        return string.Format("  主屋と付属: {0}/{1}棟(型=jisha:{2}・{3}{4}){5}{6}{7}\n    仕様: {8} ／ 置き方: {9}",
            placedN, want, s.kind ?? "jisha", hallNote, un, dr, tch, tkn,
            string.Join(" ", kinds.ToArray()), lay);
    }

    /// <summary>プレハブの駒を 1 つ起こして一覧へ足す。置けなかった理由は <paramref name="dropped"/> へ(黙って落とさない)。</summary>
    static void JAdd(List<JItem> items, List<string> dropped, Transform g, string name, string path,
                     JMode mode, float yaw, float rank)
    {
        try
        {
            var go = EdoBuild.Place(path, Vector3.zero, 0f, Vector3.one, g, name);
            items.Add(new JItem { label = name, go = go, mode = mode, yaw = yaw, rank = rank });
        }
        catch (Exception e) { dropped.Add(name + "の部材が読めない(" + e.Message + ")"); }
    }
}
