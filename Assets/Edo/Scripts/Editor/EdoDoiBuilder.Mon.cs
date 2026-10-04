using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// ══════════════════════════════════════════════════════════════════════
//  土井邸 S3 門(案A・EDO-0533)── 表門(長屋門)と下の基壇・通用門(門長屋 E13_N09)・広敷門(棟門・奥の塀)。
//  ⛔ 置き方はここに書かない(規則21)── 指図の欄を読み、EdoBuild の関数(PlaceCastleRun / PlaceGamae / AbutBodyAlong /
//     SeatBedOnCrest / NeribeiStepRun / Contact)へ渡して、実メッシュで測った値を刷るだけ。
//  硬い(許容0 = ✗): 継ぎ目の隙・区域侵犯・土台の底 = 基壇の天端・基壇の口の縁 = 扉口の脇。
//  柔らかい(狙い = ⚠): 敷居と道の差・扉口の高さ(部材の焼き方に依る)。
// ══════════════════════════════════════════════════════════════════════
public static partial class EdoDoiBuilder
{
    static Vector2 EdgeDir(int e) { return (EdgePt(e, 1f) - EdgePt(e, 0f)).normalized; }

    /// <summary>辺 e の線(区画の線から内へ c)の上で、走り s を動かしたとき隣の辺 eo の内に居る s の限り [下限, 上限]。</summary>
    static float[] SLimit(int e, float c, int eo)
    {
        Vector2 oo = OutNormal(eo), a0 = EdgePt(eo, 0f);
        Func<float, float> f = s => Vector2.Dot(EdgePt(e, s) - OutNormal(e) * c - a0, -oo);
        float f0 = f(0f), k = f(1f) - f0;
        if (Mathf.Abs(k) < 1e-5f) return new[] { float.NegativeInfinity, float.PositiveInfinity };
        return k > 0f ? new[] { -f0 / k, float.PositiveInfinity } : new[] { float.NegativeInfinity, -f0 / k };
    }

    /// <summary>駒の走りの区間 [s の最小, 最大](辺 e の始点から・躯体の帯 0.3〜2.0m の実メッシュ)。札があれば札の脇の面。</summary>
    static Vector2 SpanOn(GameObject go, int e)
    {
        var sp = EdoBuild.SpecBodySpanAlong(go, EdgePt(e, 0f), EdgeDir(e));
        return float.IsNaN(sp.x) ? EdoBuild.BodySpanAlong(go, EdgePt(e, 0f), EdgeDir(e)) : sp;
    }

    /// <summary>札(無ければ実メッシュの断面から測った案 ── 焼かない)。</summary>
    static EdoPartSpec.Spec SpecOrMeasure(string path, string kind, out string how)
    {
        var sp = EdoPartSpec.Get(path); how = "札";
        if (sp != null) return sp;
        string note; sp = EdoPartSpec.Measure(path, kind, 1f, out note);
        how = "札が無い ── 実メッシュの断面から測った(" + note + ")";
        return sp;
    }

    /// <summary>口の走りの区間(辺 e の始点からの s)── 札の passage の両端を世界へ。</summary>
    static Vector2 PassageOn(EdoPartSpec.Spec sp, Transform t, int e)
    {
        Vector2 a0 = EdgePt(e, 0f), d = EdgeDir(e);
        float p0 = Vector2.Dot(EdoPartSpec.W(t, sp.passage.x0, 0f) - a0, d), p1 = Vector2.Dot(EdoPartSpec.W(t, sp.passage.x1, 0f) - a0, d);
        return new Vector2(Mathf.Min(p0, p1), Mathf.Max(p0, p1));
    }

    /// <summary>足元の外面(札の foot の +Z の最大・局所)── 基壇の天端の前の縁 + 犬走りの線に当てる面。
    /// ⛔ 札の front で寄せない ── 在庫の長屋門は番所の出格子(+0.55)が帯に入り、壁の面が 0.55m 引っ込む。</summary>
    static float FootFront(EdoPartSpec.Spec sp) { float z = float.MinValue; foreach (var q in sp.foot) z = Mathf.Max(z, q.y); return z; }

    [MenuItem(MENU + "3門 表門・通用門・広敷門")]
    public static void Stage3MonMenu() { Debug.Log("[Doi] " + Stage3_Mon()); }

    /// <summary>**S3 門(案A・EDO-0533)**。① 表門(gate)の下の基壇(城の石垣・天端 = 欄の coping・扉口だけ空ける)→ 表門を外面の線・口の芯 s へ・
    /// 土台の底を天端へ → 角の練塀 E13_Hei_Kado の頭を表門の北の妻面から建て直す(可動は練塀)② 通用門(komon[].inRun = E13_N09)を
    /// 南隣 E13_N08 の妻面へ突き付け、口の縁と S2 の基壇の口を突き合わせる ③ 広敷門(gates[])を奥の塀の線へ札で置き、奥の塀を門の脇の面で切り直す。
    /// 前提: S2 が済んでいる(基壇・表長屋・練塀・奥の塀)。冪等(群 Mon を空けて建て直す)。</summary>
    public static string Stage3_Mon()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear(); _runs = null;
        var sb = new System.Text.StringBuilder("S3 門(案A):\n");
        var log = new System.Text.StringBuilder();
        var P = Poly;
        var ig = Group("Ishigaki"); var kak = Group("Kakoi"); var oku = Group("OkuHei"); var mon = Group("Mon"); Clear(mon);
        int ok = 0, warn = 0, bad = 0;
        Action<bool, bool, string> tally = (hard, soft, line) => { string mk = !hard ? "✗" : (soft ? "⭕" : "⚠"); if (!hard) bad++; else if (soft) ok++; else warn++; sb.AppendLine("  " + mk + " " + line); };
        float inu = C("inubashiri");
        Func<string, GameObject> kakoi = n => { var t = kak.Find(n); return t != null ? t.gameObject : null; };

        // ════ ① 表門
        var g = O(D["gate"]); int ge = (int)F(g["edge"]); float gs = F(g["s"]), gSill = F(g["sill"]);
        Vector2 o = OutNormal(ge), d = EdgeDir(ge), a0 = EdgePt(ge, 0f);
        string gpath = EdoAssets.Own.KutaiOf(EdoAssets.Own.DoiNagayamon), ghow;
        var gsp = SpecOrMeasure(gpath, "gate", out ghow);
        if (EdoPartSpec.Get(gpath) == null) { sb.AppendLine("  ⚠ 表門の部材 " + System.IO.Path.GetFileName(gpath) + ": " + ghow); warn++; }
        var gate = EdoBuild.Place(gpath, new Vector3(EdgePt(ge, gs).x, F(O(D["gate"])["plinth"] is Dictionary<string, object> ? O(O(D["gate"])["plinth"])["coping"] : 0f), EdgePt(ge, gs).y), YawFace(o), Vector3.one, mon, "Omotemon");
        if (gate == null || gsp == null || gsp.passage == null) return sb.Append("  ✗ 表門が据えられない(部材・通り口)").ToString();
        // 横: 口の芯を指図の s へ(硬い ── 門は固定側)
        { var pc = PassageOn(gsp, gate.transform, ge); gate.transform.position += new Vector3(d.x, 0f, d.y) * (gs - (pc.x + pc.y) * 0.5f); }
        var gPass = PassageOn(gsp, gate.transform, ge);
        // 下の基壇(boundaryPlinth.rows の opening.gate)── 扉口(札の通り口)だけ空ける
        Dictionary<string, object> grow = null;
        foreach (var ro in A(O(D["boundaryPlinth"])["rows"])) { var r = O(ro); if (Has(r, "opening") && Has(O(r["opening"]), "gate")) grow = r; }
        if (grow == null) return sb.Append("  ✗ 表門の下の基壇の欄(boundaryPlinth.rows の opening.gate)が無い").ToString();
        for (int i = ig.childCount - 1; i >= 0; i--) if (ig.GetChild(i).name.StartsWith("IG_Omotemon")) UnityEngine.Object.DestroyImmediate(ig.GetChild(i).gameObject);
        var gsec = new EdoBuild.CastleSec { name = "IG_Omotemon", edge = ge, s0 = F(grow["s0"]), s1 = F(grow["s1"]), crest = F(grow["coping"]) };
        gsec.gaps.Add(gPass);
        var cr = EdoBuild.PlaceCastleRun(new List<EdoBuild.CastleSec> { gsec }, P, EdoBuild.Ground, ig, log);
        List<GameObject> gpcs; cr.bySec.TryGetValue("IG_Omotemon", out gpcs); if (gpcs != null) gpcs.RemoveAll(x => x == null);
        if (gpcs == null || gpcs.Count == 0 || !cr.inset.ContainsKey(ge)) return sb.Append("  ✗ 表門の下の基壇が据わらない").ToString();
        float inset = cr.inset[ge];
        {
            var m = EdoBuild.CastleCrestExposure(gpcs, o, EdoBuild.Ground);
            float cop = F(grow["coping"]), road = float.MinValue;
            for (float s = gsec.s0; s <= gsec.s1 + 1e-3f; s += 0.5f) { var q = EdgePt(ge, s) + o * 0.3f; road = Mathf.Max(road, EdoBuild.Ground(q.x, q.y)); }
            bool hard = Mathf.Abs(m.x - cop) <= 0.001f && Mathf.Abs(m.y - cop) <= 0.001f && m.y >= road - 1e-3f && !(m.w > C("boundaryPlinthMax") + 1e-3f);
            tally(hard, m.z >= 0.3f - 1e-3f && m.w <= 1.2f + 1e-3f, "表門の下の基壇: " + gpcs.Count + " 駒・天端 " + m.x.ToString("F3") + "〜" + m.y.ToString("F3") + "(欄 " + cop.ToString("F1")
                + ")・道の最高 " + road.ToString("F2") + "・見付 " + m.z.ToString("F2") + "〜" + m.w.ToString("F2") + "(狙い 0.3〜1.2)・天端の前の縁 = 線から内へ " + inset.ToString("F3") + "m");
        }
        // 奥行: 足元の外面を「基壇の天端の前の縁 + 犬走り」の線へ(S2 の表長屋と同じ線)
        Vector2 org = a0 - o * (inset + inu);
        { float zf = FootFront(gsp); var fw = gate.transform.TransformPoint(new Vector3((gsp.passage.x0 + gsp.passage.x1) * 0.5f, 0f, zf));
          gate.transform.position -= new Vector3(o.x, 0f, o.y) * Vector2.Dot(new Vector2(fw.x, fw.z) - org, o); }
        // 高さ: 土台の底(扉口を除く外面の帯の最下点)を基壇の天端へ
        float gCrest = EdoBuild.CastleCrestExposure(gpcs, o, EdoBuild.Ground).y;
        float gBed = EdoBuild.SeatBedOnCrest(gate, gCrest, org, o, d, gPass.x - 0.05f, gPass.y + 0.05f);
        tally(!float.IsNaN(gBed), true, "表門(" + System.IO.Path.GetFileName(gpath) + "): 口の芯 s=" + ((gPass.x + gPass.y) * 0.5f).ToString("F3") + "(欄 " + gs.ToString("F2") + ")・扉口 " + gPass.x.ToString("F3") + "〜" + gPass.y.ToString("F3")
              + "・土台の底 = 天端 " + gCrest.ToString("F3") + "(据える前の差 " + gBed.ToString("+0.000;-0.000") + ")");
        // 扉口の高さ(扉の下端)と敷居・道・門の内の面
        {
            float doorLo = float.MaxValue; var pts = EdoBuild.Body(gate.transform, 999999);
            foreach (var v in pts) { float s = Vector2.Dot(new Vector2(v.x, v.z) - a0, d); if (s > gPass.x + 0.1f && s < gPass.y - 0.1f) doorLo = Mathf.Min(doorLo, v.y); }
            var qOut = EdgePt(ge, gs) + o * 0.3f; float road = EdoBuild.Ground(qOut.x, qOut.y);
            float back = float.MaxValue; foreach (var v in pts) back = Mathf.Min(back, Vector2.Dot(new Vector2(v.x, v.z) - org, o));
            var qIn = EdgePt(ge, gs) - o * (inset + inu - back + 0.3f); float inner = EdoBuild.Ground(qIn.x, qIn.y);
            float dropNeed = gCrest - gSill;
            tally(true, Mathf.Abs(doorLo - gSill) <= 0.01f, "表門の扉口: 扉の下端 " + doorLo.ToString("F3") + "・欄の敷居 " + gSill.ToString("F2") + "(差 " + (doorLo - gSill).ToString("+0.000;-0.000")
                  + ")・扉の前の道 " + road.ToString("F3") + "(敷居との差 " + (gSill - road).ToString("+0.000;-0.000") + ")・門の背の 0.3m 内の地表 " + inner.ToString("F3")
                  + "(門の内の面 22.4)" + (Mathf.Abs(doorLo - gSill) > 0.01f ? " ── 部材の扉口は土台の底のまま(切り下げ " + dropNeed.ToString("F2") + "m の版が要る ── 部材方)" : ""));
        }
        // 基壇の口の縁 ↔ 扉口の脇(硬い ±0.01)
        {
            float lo = float.MinValue, hi = float.MaxValue; float pc = (gPass.x + gPass.y) * 0.5f;
            foreach (var p in gpcs) { var sp = EdoBuild.BodySpanAlong(p, a0, d, 0f, 99f); if (float.IsNaN(sp.x)) continue; if ((sp.x + sp.y) * 0.5f < pc) lo = Mathf.Max(lo, sp.y); else hi = Mathf.Min(hi, sp.x); }
            bool h = Mathf.Abs(lo - gPass.x) <= 0.01f && Mathf.Abs(hi - gPass.y) <= 0.01f;
            tally(h, true, "表門の基壇の口: 縁 " + lo.ToString("F3") + "〜" + hi.ToString("F3") + " ↔ 扉口 " + gPass.x.ToString("F3") + "〜" + gPass.y.ToString("F3") + "(差 " + (lo - gPass.x).ToString("+0.000;-0.000") + " / " + (hi - gPass.y).ToString("+0.000;-0.000") + ")");
        }
        var gSpan = SpanOn(gate, ge);
        // 南の妻面 ↔ E13_N11 の北の妻面(硬い 隙 0・可動は長屋 ── 長屋は S2 で南の棟へ突き付け済み。動かすと N10|N11 が開く ⇒ 測って刷る)
        {
            var n11 = kakoi("E13_N11");
            if (n11 == null) { sb.AppendLine("  ✗ E13_N11 が無い(S2 が未実行)"); bad++; }
            else
            {
                // 躯体(屋根の材を除く)の当たりで測る ── 破風・軒どうしの重なりは埋めて隠す(oki-kata §4)
                Vector3 at; int cnt; float c = EdoBuild.Contact(n11, gate, new Vector3(d.x, 0f, d.y), out at, out cnt, 0.01f, 0.25f, 4000, false);
                var sp = SpanOn(n11, ge); float seam = gSpan.x - sp.y;
                tally(seam <= 0.001f && (float.IsNaN(c) || c <= 0.001f), true, "表門の南の妻面 ↔ E13_N11 の北の妻面: 躯体の端の隙 " + seam.ToString("+0.000;-0.000") + "m(s " + sp.y.ToString("F3") + " / " + gSpan.x.ToString("F3") + ")・躯体の当たり " + (float.IsNaN(c) ? "測れず" : c.ToString("+0.000;-0.000")) + "m(" + cnt + " 筋)"
                      + (seam > 0.001f ? " ── 部材の躯体 " + (gSpan.y - gSpan.x).ToString("F3") + "m < 欄の monW " + F(O(g["plan"])["monW"]).ToString("F2") + "(呼び寸法 = 破風込みの旧い版)── 躯体 = 呼び寸法の版が要る(部材方)" : ""));
            }
        }
        // 区域(壁体の全頂点・軒は越えてよい)
        { float was; EdoBuild.PullAlongInside(new List<GameObject> { gate }, P, Vector2.zero, 0f, out was, 1.2f); tally(was <= 0.001f, true, "表門: 腰が区画の外へ " + was.ToString("F3") + "m"); }

        // ── 角の練塀 E13_Hei_Kado の頭を表門の北の妻面から建て直す(可動は練塀)
        {
            Run hk = null; foreach (var r in Runs) if (r.name == "E13_Hei_Kado") hk = r;
            if (hk == null || !hk.build || hk.after != null) sb.AppendLine("  E13_Hei_Kado: 建てない(欄)");
            else
            {
                for (int i = kak.childCount - 1; i >= 0; i--) if (kak.GetChild(i).name.StartsWith("E13_Hei_Kado")) UnityEngine.Object.DestroyImmediate(kak.GetChild(i).gameObject);
                float T; { var bpz = EdoBuild.BodyAt(EdoAssets.Own.Dobei2m, Vector3.zero, 0f, false); float zl = float.MaxValue, zh = float.MinValue; foreach (var q in bpz) { zl = Mathf.Min(zl, q.z); zh = Mathf.Max(zh, q.z); } T = zh - zl; }
                float c = inset + inu + T * 0.5f;
                float sA = gSpan.y, sB = hk.s1;
                if (hk.s1 >= EdgeLen(ge) - EdoBuild.VTX_TOL)
                {
                    int ne = (ge + 1) % P.Length; float hiS = float.PositiveInfinity;
                    foreach (float cc in new[] { c - T * 0.5f, c + T * 0.5f }) hiS = Mathf.Min(hiS, SLimit(ge, cc, ne)[1]);
                    if (!float.IsInfinity(hiS)) sB = Mathf.Min(sB, hiS);
                }
                Vector2 p0 = EdgePt(ge, sA) - o * c, p1 = EdgePt(ge, sB) - o * c;
                float crest = EdoBuild.CrestY(ig, (p0 + p1) * 0.5f + o * (T * 0.5f), 0.1f);
                var plan = new List<EdoBuild.DanSec> { new EdoBuild.DanSec { a = 0f, b = Vector2.Distance(p0, p1), W = float.IsNaN(crest) ? hk.seat : crest } };
                string note; var made = EdoBuild.NeribeiStepRun(kak, p0, p1, o, "E13_Hei_Kado", plan, Vector2.zero, -1f, out note);
                log.AppendLine("  練塀 E13_Hei_Kado: " + note);
                // 尻(相手の無い出隅の端)の駒が隣の辺の外へ出るなら走りに沿って引く(S2 と同じ)
                GameObject head = null, tail = null; float bl = float.MaxValue, bh = float.MinValue;
                foreach (var gg in made) { if (gg.name.EndsWith("_ishi")) continue; float s = Vector2.Dot(new Vector2(EdoBuild.RB(gg).center.x, EdoBuild.RB(gg).center.z), d); if (s < bl) { bl = s; head = gg; } if (s > bh) { bh = s; tail = gg; } }
                if (tail != null)
                {
                    var grpE = new List<GameObject> { tail }; foreach (var gg in made) if (gg.name == tail.name + "_ishi") grpE.Add(gg);
                    float before; float pl = EdoBuild.PullAlongInside(grpE, P, -d, 0.6f, out before);
                    if (before > 0.001f) sb.AppendLine("  ⚠ 練塀 " + tail.name + ": 出隅の端の駒が " + before.ToString("F3") + "m 隣の辺の外 ⇒ " + (float.IsNaN(pl) ? "0.6m 引いても収まらない" : pl.ToString("F3") + "m 引いた"));
                }
                float was; EdoBuild.PullAlongInside(made, P, Vector2.zero, 0f, out was);
                Vector3 at; int cnt; float gc = head != null ? EdoBuild.Contact(head, gate, new Vector3(-d.x, 0f, -d.y), out at, out cnt) : float.NaN;
                tally(!float.IsNaN(gc) && gc <= 0.001f && was <= 0.001f, true, "練塀 E13_Hei_Kado: " + made.Count + " 駒・座 = 基壇の天端 " + plan[0].W.ToString("F3") + "(欄 " + hk.seat.ToString("F1") + ")・頭 s=" + sA.ToString("F3")
                      + " ↔ 表門の北の妻面: 隙 " + (float.IsNaN(gc) ? "測れず" : gc.ToString("+0.000;-0.000")) + "m・区画の外 " + was.ToString("F3") + "m");
            }
        }

        // ════ ② 通用門(門長屋 E13_N09)
        foreach (var ko in A(D["komon"]) ?? new List<object>())
        {
            var k = O(ko); if (!Has(k, "inRun")) continue;
            string rn = S(k["inRun"]); Run kr = null; foreach (var r in Runs) if (r.name == rn) kr = r;
            if (kr == null) { sb.AppendLine("  ✗ 通用門 " + S(k["name"]) + ": run " + rn + " が無い"); bad++; continue; }
            int e = kr.edge; Vector2 ko2 = OutNormal(e), kd = EdgeDir(e), ka0 = EdgePt(e, 0f);
            float L = Mathf.Round((kr.s1 - kr.s0) * 100f) / 100f, ks = F(k["s"]);
            // 口の左端からの距離 = 指図の s − s0(辺13 では局所 +X = −走り ⇒ 部材の左端は run の s0 側)── 部材の名の引数
            float fromLeft = Mathf.Round((ks - kr.s0) * 100f) / 100f;
            string kpath = EdoAssets.Own.KutaiOf(EdoAssets.Own.NagayaOmoteMon(L, fromLeft, kr.nikai));
            var ksp = EdoPartSpec.Get(kpath);
            if (!Exists(kpath) || ksp == null || ksp.passage == null) { Wait("通用門 " + S(k["name"]) + ": 部材か札が無い " + kpath); continue; }
            var kOrg = ka0 - ko2 * (inset + inu);
            Vector2 p = kOrg + kd * ((kr.s0 + kr.s1) * 0.5f);
            var go = EdoBuild.Place(kpath, new Vector3(p.x, kr.seat, p.y), YawFace(ko2), Vector3.one, mon, rn);
            if (go == null) continue;
            { var fw = go.transform.TransformPoint(new Vector3(0f, 0f, FootFront(ksp))); go.transform.position -= new Vector3(ko2.x, 0f, ko2.y) * Vector2.Dot(new Vector2(fw.x, fw.z) - kOrg, ko2); }
            // 南隣の棟の北の妻面へ突き付け(S2 と同じ ── 札の躯体の端)
            int pi = Array.FindIndex(Runs, x => x.edge == e && Mathf.Abs(x.s1 - kr.s0) < 0.01f && x.nagaya); var prev = pi >= 0 ? kakoi(Runs[pi].name) : null;
            if (prev != null) EdoBuild.AbutBodyAlong(go, ka0, kd, EdoBuild.SpecBodySpanAlong(prev, ka0, kd).y, true);
            else EdoBuild.AbutBodyAlong(go, ka0, kd, kr.s0, true);
            var kPass = PassageOn(ksp, go.transform, e);
            // 高さ: 土台の底を足の下の基壇(S2 の IG_<run>)の天端へ
            var kp = new List<GameObject>(); foreach (Transform t in ig) if (t.name.StartsWith("IG_" + rn)) kp.Add(t.gameObject);
            float kCrest = kp.Count > 0 ? EdoBuild.CastleCrestExposure(kp, ko2, EdoBuild.Ground).y : float.NaN;
            float kBed = float.IsNaN(kCrest) ? float.NaN : EdoBuild.SeatBedOnCrest(go, kCrest, kOrg, ko2, kd, kPass.x - 0.05f, kPass.y + 0.05f);
            var kSpan = SpanOn(go, e);
            tally(!float.IsNaN(kBed) && Mathf.Abs(kCrest - kr.seat) <= 0.001f, true, "通用門 " + rn + "(" + System.IO.Path.GetFileName(kpath) + "): 躯体 s " + kSpan.x.ToString("F3") + "〜" + kSpan.y.ToString("F3") + "(欄 " + kr.s0.ToString("F2") + "〜" + kr.s1.ToString("F2")
                  + ")・口 " + kPass.x.ToString("F3") + "〜" + kPass.y.ToString("F3") + "(芯 " + ((kPass.x + kPass.y) * 0.5f).ToString("F3") + "・欄 " + ks.ToString("F2") + ")・土台の底 = 天端 " + kCrest.ToString("F3") + "(欄の座 " + kr.seat.ToString("F1") + "・据える前の差 " + kBed.ToString("+0.000;-0.000") + ")");
            // 継ぎ目(両隣・札の躯体の端と実メッシュの当たり)
            foreach (bool hiSide in new[] { false, true })
            {
                Run nr = null; foreach (var r in Runs) if (r.edge == e && r.nagaya && (hiSide ? Mathf.Abs(r.s0 - kr.s1) < 0.01f : Mathf.Abs(r.s1 - kr.s0) < 0.01f)) nr = r;
                var ng = nr != null ? kakoi(nr.name) : null; if (ng == null) continue;
                var ns = EdoBuild.SpecBodySpanAlong(ng, ka0, kd);
                float seam = hiSide ? ns.x - kSpan.y : kSpan.x - ns.y;
                Vector3 at; int cnt; float c = EdoBuild.Contact(go, ng, hiSide ? new Vector3(kd.x, 0f, kd.y) : new Vector3(-kd.x, 0f, -kd.y), out at, out cnt);
                tally(seam <= 0.001f && (float.IsNaN(c) || c <= 0.001f), true, "通用門 ↔ " + nr.name + ": 躯体の端の隙 " + seam.ToString("+0.0000;-0.0000") + "m・実メッシュの当たり " + (float.IsNaN(c) ? "測れず" : c.ToString("+0.000;-0.000")) + "m(" + cnt + " 筋)");
            }
            // 扉口の高さ・敷居・道
            {
                float doorLo = float.MaxValue; foreach (var v in EdoBuild.Body(go.transform, 999999)) { float s = Vector2.Dot(new Vector2(v.x, v.z) - ka0, kd); if (s > kPass.x + 0.1f && s < kPass.y - 0.1f) doorLo = Mathf.Min(doorLo, v.y); }
                var qo = EdgePt(e, ks) + ko2 * 0.3f; float road = EdoBuild.Ground(qo.x, qo.y);
                var qi = EdgePt(e, ks) - ko2 * (inset + inu + 3.4f); float inner = EdoBuild.Ground(qi.x, qi.y);
                float sill = F(k["sill"]);
                tally(true, Mathf.Abs(doorLo - sill) <= 0.01f, "通用門の扉口: 扉の下端 " + doorLo.ToString("F3") + "・欄の敷居 " + sill.ToString("F2") + "(差 " + (doorLo - sill).ToString("+0.000;-0.000") + ")・扉の前の道 " + road.ToString("F3")
                      + "(敷居との差 " + (sill - road).ToString("+0.000;-0.000") + ")・門の背の内の地表 " + inner.ToString("F3"));
            }
            // 基壇の口の縁 ↔ 部材の口(硬い ±0.01)── S2 の口(指図の芯と幅)を部材の口と突き合わせる
            {
                float lo = float.MinValue, hi = float.MaxValue, pc = (kPass.x + kPass.y) * 0.5f;
                foreach (var pg in kp) { var sp = EdoBuild.BodySpanAlong(pg, ka0, kd, 0f, 99f); if (float.IsNaN(sp.x)) continue; if ((sp.x + sp.y) * 0.5f < pc) lo = Mathf.Max(lo, sp.y); else hi = Mathf.Min(hi, sp.x); }
                bool h = Mathf.Abs(lo - kPass.x) <= 0.01f && Mathf.Abs(hi - kPass.y) <= 0.01f;
                tally(h, true, "通用門の基壇の口: 縁 " + lo.ToString("F3") + "〜" + hi.ToString("F3") + " ↔ 部材の口 " + kPass.x.ToString("F3") + "〜" + kPass.y.ToString("F3") + "(差 " + (lo - kPass.x).ToString("+0.000;-0.000") + " / " + (hi - kPass.y).ToString("+0.000;-0.000") + ")"
                      + (h ? "" : " ── 取り直しは S2 の基壇の口(komon の s・w)を部材の口へ"));
            }
            { float was; EdoBuild.PullAlongInside(new List<GameObject> { go }, P, Vector2.zero, 0f, out was, 1.2f); tally(was <= 0.001f, true, "通用門: 腰が区画の外へ " + was.ToString("F3") + "m"); }
        }

        // ════ ③ 広敷門(gates[] ── 奥の塀の口)
        var over = new Dictionary<string, Vector3>();
        var hiro = new List<KeyValuePair<GameObject, Dictionary<string, object>>>();
        foreach (var go0 in A(D["gates"]) ?? new List<object>())
        {
            var gg = O(go0); if (!Has(gg, "inRun")) continue;
            string nm = S(gg["name"]), rn = S(gg["inRun"]);
            Run rr = null; foreach (var r in Runs) if (r.name == rn) rr = r;
            if (rr == null || rr.pts == null) { sb.AppendLine("  ✗ " + nm + ": 塀 " + rn + " が無い"); bad++; continue; }
            string api = Has(gg, "asset") ? S(gg["asset"]) : null;
            string path = api != null && api.Contains("Munamon(") ? EdoAssets.Own.Munamon(F(gg["w"]), false) : null;
            if (path == null || !Exists(path) || EdoPartSpec.Get(path) == null) { Wait(nm + ": 部材か札が無い " + (path ?? api)); continue; }
            var uv = A(gg["uv"]); Vector2 c = Grid.W(F(uv[0]), F(uv[1]));
            var pts = rr.pts.ConvertAll(q => Grid.W(q.x, q.y));
            int bi = 0; float bd = float.MaxValue;
            for (int i = 0; i + 1 < pts.Count; i++) { var dd = (pts[i + 1] - pts[i]).normalized; float t = Mathf.Clamp(Vector2.Dot(c - pts[i], dd), 0f, Vector2.Distance(pts[i], pts[i + 1])); float dist = Vector2.Distance(pts[i] + dd * t, c); if (dist < bd) { bd = dist; bi = i; } }
            Vector2 A0 = pts[bi], B0 = pts[bi + 1], al = (B0 - A0).normalized;
            // 外(奥の外)= 奥向の棟(奥・長局)の無い側。線の両側 3m を見て、奥向の面(planes の 奥向)の棟の矩形に入る側を内とする
            Vector2 nrm = new Vector2(-al.y, al.x);
            int inPos = 0, inNeg = 0;
            foreach (var mo in A(D["munes"]))
            {
                var mm = O(mo); string mn = S(mm["name"]); if (mn != "Oku" && mn != "Nagatsubone") continue;
                var ctr = Grid.W((F(mm["u0"]) + F(mm["u1"])) * 0.5f, (F(mm["v0"]) + F(mm["v1"])) * 0.5f);
                if (Vector2.Dot(ctr - A0, nrm) > 0f) inPos++; else inNeg++;
            }
            Vector2 outw = inPos > inNeg ? -nrm : nrm;
            sb.AppendLine("  " + nm + ": 外(+Z)= 奥向の棟(奥・長局)の反対の側 ── 棟の芯が線の " + (inPos > inNeg ? "+" : "−") + " 側に " + Mathf.Max(inPos, inNeg) + "/" + (inPos + inNeg) + " 棟");
            var go = EdoBuild.Place(path, new Vector3(c.x, EdoBuild.Ground(c.x, c.y), c.y), YawFace(outw), Vector3.one, mon, nm);
            if (go == null) continue;
            // 塀の外の面(S2 の奥の塀の駒の実メッシュ ── 線の両側の帯の外端)
            float face = float.NaN, depth = float.NaN;
            foreach (Transform t in oku)
            {
                if (!t.name.StartsWith(rn + "_" + bi + "_") || t.name.EndsWith("_ishi")) continue;
                var sp = EdoBuild.BodySpanAlong(t.gameObject, A0, outw, 0.3f, 1.8f); if (float.IsNaN(sp.x)) continue;
                face = float.IsNaN(face) ? sp.y : Mathf.Max(face, sp.y); depth = float.IsNaN(depth) ? sp.y - sp.x : Mathf.Max(depth, sp.y - sp.x);
            }
            if (float.IsNaN(face)) { sb.AppendLine("  ✗ " + nm + ": 奥の塀の駒が無く外の面が測れない(S2 が未実行)"); bad++; continue; }
            EdoBuild.Gamae gm;
            try { gm = EdoBuild.PlaceGamae(go, new List<GameObject>(), A0, B0, outw, c, P, face, 0f, depth); }
            catch (Exception ex) { sb.AppendLine("  ✗ " + nm + ": " + ex.Message); bad++; continue; }
            EdoBuild.SeatGamae(go, 999999);
            over[nm] = new Vector3(gm.gapC.x, gm.gapC.y, gm.gapHalf);
            hiro.Add(new KeyValuePair<GameObject, Dictionary<string, object>>(go, gg));
            sb.AppendLine("  " + nm + "(" + System.IO.Path.GetFileName(path) + "): 札で据えた ── 口の芯の残差 " + Vector2.Distance(gm.passageC, c).ToString("F3") + "m・正面の残差 " + gm.faceResid.ToString("+0.000;-0.000")
                          + "・塀の口 " + (gm.gapHalf * 2f).ToString("F3") + "m(脇の面)" + (gm.notes.Count > 0 ? " " + string.Join(" / ", gm.notes.ToArray()) : ""));
        }
        if (over.Count > 0)
        {
            Clear(oku);
            warn += BuildOkuHei(oku, sb, log, over);
            foreach (var kv in hiro)
            {
                var go = kv.Key; string nm = go.name;
                Vector3 at; int cnt; float gnd = EdoBuild.Contact(go, out at, out cnt);
                tally(!float.IsNaN(gnd) && Mathf.Abs(gnd) <= 0.01f, true, nm + ": 敷居 = 地形なり ── 当たり − 地表 " + (float.IsNaN(gnd) ? "測れず" : gnd.ToString("+0.000;-0.000")) + "m(" + cnt + " 点)");
                // 袖 ↔ 塀の端(口の両脇の塀の端の駒 ── 門の芯から最も近い左右の駒)
                var sp = SpecOf(go); Vector2 cc = EdoPartSpec.PassageCenterWorld(sp, go.transform);
                Vector2 al = new Vector2(go.transform.right.x, go.transform.right.z).normalized;
                GameObject lo = null, hi = null; float bl = float.MaxValue, bh = float.MaxValue;
                foreach (Transform t in oku)
                {
                    if (t.name.EndsWith("_ishi")) continue; var rc = EdoBuild.RB(t.gameObject).center; Vector2 q = new Vector2(rc.x, rc.z) - cc;
                    if (Mathf.Abs(Vector2.Dot(q, new Vector2(-al.y, al.x))) > 1.0f) continue;
                    float s = Vector2.Dot(q, al); if (s < 0f && -s < bl) { bl = -s; lo = t.gameObject; } if (s > 0f && s < bh) { bh = s; hi = t.gameObject; }
                }
                foreach (var pr in new[] { new KeyValuePair<GameObject, Vector2>(lo, -al), new KeyValuePair<GameObject, Vector2>(hi, al) })
                {
                    if (pr.Key == null) { sb.AppendLine("  ✗ " + nm + ": 片側の塀の端が無い"); bad++; continue; }
                    var ends = new List<GameObject> { pr.Key }; var st = oku.Find(pr.Key.name + "_ishi"); if (st != null) ends.Add(st.gameObject);
                    string how; float gap = EdoBuild.GamaeFenceGap(new List<GameObject> { pr.Key }, go, -pr.Value, out how);
                    tally(!float.IsNaN(gap) && gap <= 0.01f, true, nm + " の袖 ↔ 塀の端 " + pr.Key.name + ": 隙 " + (float.IsNaN(gap) ? "測れず" : gap.ToString("+0.000;-0.000")) + "m(" + how + ")");
                }
                float was; EdoBuild.PullAlongInside(new List<GameObject> { go }, P, Vector2.zero, 0f, out was); tally(was <= 0.001f, true, nm + ": 区画の外 " + was.ToString("F3") + "m");
            }
        }

        sb.AppendLine("  勘定: ⭕ " + ok + " / ⚠ " + warn + " / ✗ " + bad);
        sb.Append(WaitReport());
        sb.AppendLine("── 明細 ──");
        sb.Append(log.ToString());
        return sb.ToString();
    }

    /// <summary>**奥の塀**(区画の内の段塀・runs[].pts)を建てる。口(gates[].inRun)は <paramref name="gapOverride"/>(門の名 → 口の芯 x,z と半幅)が
    /// あればそれで、無ければ指図の uv と w で空ける(S2 の仮の口)。⭐ S3 は門の札の脇の面(<see cref="EdoBuild.PlaceGamae"/> の gapC/gapHalf)を渡す。
    /// 返り値 = ⚠ の数。⛔ 置き方はここに書かない(規則21)── 線と口を EdoBuild.DanPlan / NeribeiStepRun へ渡すだけ。</summary>
    static int BuildOkuHei(Transform oku, System.Text.StringBuilder sb, System.Text.StringBuilder log, Dictionary<string, Vector3> gapOverride)
    {
        int warn = 0;
        foreach (var r in Runs)
        {
            if (r.pts == null || r.pts.Count < 2 || !r.build || r.after != null) continue;
            var pts = r.pts.ConvertAll(q => Grid.W(q.x, q.y));
            var segL = new List<float>(); for (int i = 0; i + 1 < pts.Count; i++) segL.Add(Vector2.Distance(pts[i], pts[i + 1]));
            // 口(広敷門など gates[].inRun)── 鎖の道のりへ
            var gaps = new List<Vector2>(); var gapAt = new List<KeyValuePair<int, Vector2>>(); var gapHalf = new List<float>();
            foreach (var o in A(D["gates"]) ?? new List<object>())
            {
                var g = O(o); if (!Has(g, "inRun") || S(g["inRun"]) != r.name) continue;
                var uv = A(g["uv"]); Vector2 gw = Grid.W(F(uv[0]), F(uv[1])); float hw = F(g["w"]) * 0.5f;
                Vector3 ov = Vector3.zero; bool byMon = gapOverride != null && gapOverride.TryGetValue(S(g["name"]), out ov);
                if (byMon) { gw = new Vector2(ov.x, ov.y); hw = ov.z; }
                float acc = 0f, bestD = float.MaxValue, bestS = 0f; int bestI = 0;
                for (int i = 0; i + 1 < pts.Count; i++)
                {
                    Vector2 dd = (pts[i + 1] - pts[i]).normalized; float t = Mathf.Clamp(Vector2.Dot(gw - pts[i], dd), 0f, segL[i]);
                    float dist = Vector2.Distance(pts[i] + dd * t, gw); if (dist < bestD) { bestD = dist; bestS = acc + t; bestI = i; }
                    acc += segL[i];
                }
                gaps.Add(new Vector2(bestS - hw, bestS + hw)); gapAt.Add(new KeyValuePair<int, Vector2>(bestI, gw)); gapHalf.Add(hw);
                if (byMon) sb.AppendLine("  奥の塀 " + r.name + ": 口 " + S(g["name"]) + " を門の脇の面で空けた(幅 " + (hw * 2f).ToString("F3") + "m・札の jamb から)");
                else { sb.AppendLine("  ⚠ 奥の塀 " + r.name + ": 口 " + S(g["name"]) + "(幅 " + F(g["w"]).ToString("F2") + ")を空けた ── 門は S3"); warn++; }
            }
            string dn; var plan = EdoBuild.DanPlan(pts, out dn, gaps);
            float org = 0f; int nm = 0;
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                Vector2 dd = (pts[i + 1] - pts[i]).normalized, nrm = new Vector2(-dd.y, dd.x);
                var ds = plan.ConvertAll(x => new EdoBuild.DanSec { a = x.a - org, b = x.b - org, W = x.W });
                Vector2 gc = Vector2.zero; float gh = -1f;
                for (int gi = 0; gi < gapAt.Count; gi++) if (gapAt[gi].Key == i) { gc = gapAt[gi].Value; gh = gapHalf[gi]; }
                string note;
                nm += EdoBuild.NeribeiStepRun(oku, pts[i], pts[i + 1], nrm, r.name + "_" + i, ds, gc, gh, out note).Count;
                log.AppendLine("  奥の塀 " + r.name + " 区" + i + ": " + note);
                org += segL[i];
            }
            sb.AppendLine("  ⚠ 奥の塀 " + r.name + ": " + nm + " 駒・" + dn + " ── 端の突き付け(" + string.Join(" / ", r.name == "Oku_Hei" ? new[] { "廊下 L_HiromaOku の東の側面", "建仁寺垣の端柱" } : new[] { "廊下 L_HiromaOku の西の側面", "書院 Shoin の東の妻" })
                        + ")と棟の壁の面との離れは相手が S4 で未建 ── 指図の線の端で止めた(未検査)");
            warn++;
        }
        return warn;
    }

    static EdoPartSpec.Spec SpecOf(GameObject go) { return EdoBuild.SpecOf(go); }
}
