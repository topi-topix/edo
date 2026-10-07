using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// ══════════════════════════════════════════════════════════════════════
//  土井邸 S4 邸内の土留め・石段(案A・EDO-0533)── terraceWalls の野面の乱積み(SannoNozura)と kaidans の段石。
//  ⛔ 置き方はここに書かない(規則21)── 指図の欄(a/b・coping・footFace・corners)を読み、EdoBuild.PlaceNozuraNet /
//     EdoBuild.SlopeSteps へ渡して、据わった駒の実メッシュで測った値を刷るだけ。
//  硬い(許容0 = ✗): 見付 ≤ 欄の hard(1.50)・天端 = 欄の coping・端の突き付けの隙・底の浮き・区域侵犯・石段の段数。
//  柔らかい(狙い = ⚠): 天端の背の地表の窪み(2m 格子の造成が段の縁を均す ── 皮の巡)・段石の天端と造成後の地盤の差。
//  建てない: 欄 builtAs を持つ石垣(北の境の長屋の下 ── S3 の背の基壇が建てる)・坂(土の坂 ── 地形が graded で持つ)。
// ══════════════════════════════════════════════════════════════════════
public static partial class EdoDoiBuilder
{
    /// <summary>runs[name].seatFrom が「段は X の倍数」と名乗るなら X、無ければ 0(段塀の刻み ── <see cref="EdoBuild.DanPlan(IList{Vector2}, out string, IList{Vector2}, float)"/>)。</summary>
    static float DanStepQOf(string runName)
    {
        foreach (var o in A(D["runs"]))
        {
            var r = O(o); if (S(r["name"]) != runName || !Has(r, "seatFrom")) continue;
            var m = System.Text.RegularExpressions.Regex.Match(S(r["seatFrom"]), @"段は\s*([0-9.]+)\s*の倍数");
            if (m.Success) return float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
        }
        return 0f;
    }

    /// <summary>terraces[name] の多角形(主郭の格子 u,v)を世界へ。無ければ null。</summary>
    static Vector2[] TerracePolyW(string name, out float y)
    {
        y = float.NaN;
        foreach (var o in A(D["terraces"]))
        {
            var t = O(o); if (S(t["name"]) != name || !Has(t, "poly")) continue;
            var pl = A(t["poly"]); var w = new Vector2[pl.Count];
            for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); w[i] = Grid.W(F(q[0]), F(q[1])); }
            if (Has(t, "y")) y = F(t["y"]);
            return w;
        }
        return null;
    }

    [MenuItem(MENU + "4a 邸内の土留め・石段(案A)")]
    public static void Stage4aMenu() { Debug.Log("[Doi] " + Stage4a_Dodome()); }

    /// <summary>**S4 邸内の土留め・石段(案A・EDO-0533)**。① terraceWalls の野面(part = SannoNozura)を a→b の線へ
    /// <see cref="EdoBuild.PlaceNozuraNet"/> で据える ── 天端 = coping・見え面の足元 = footFace の面(無い所は描かれた地表)・
    /// 端は 1.5m 以内の据わった駒(表門)の実面へ突き付け、相手が無ければ打ち切りの駒(法面へ呑ませる)。
    /// ② kaidans を <see cref="EdoBuild.SlopeSteps"/> で造成後の斜面へ(段数は落差 ÷ 蹴上・天端を地表へ)。冪等(群を空けて建て直す)。</summary>
    public static string Stage4a_Dodome()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var sb = new System.Text.StringBuilder("S4 邸内の土留め・石段(案A):\n");
        var log = new System.Text.StringBuilder();
        var P = Poly;
        var grp = Group("Dodome"); Clear(grp);
        int ok = 0, warn = 0, bad = 0;
        Action<bool, bool, string> tally = (hard, soft, line) => { string mk = !hard ? "✗" : (soft ? "⭕" : "⚠"); if (!hard) bad++; else if (soft) ok++; else warn++; sb.AppendLine("  " + mk + " " + line); };
        var mon = Group("Mon");
        var pool = new List<GameObject>();
        { var om = mon.Find("Omotemon"); if (om != null) pool.Add(om.gameObject); }
        var heights = new[] { 0.30f, 0.60f, 0.90f, 1.20f, 1.50f };

        // ════ ① 土留め(野面の乱積み)
        foreach (var o in A(D["terraceWalls"]))
        {
            var tw = O(o); string nm = S(tw["name"]);
            string part = Has(tw, "part") ? S(tw["part"]) : null;
            if (Has(tw, "builtAs")) { sb.AppendLine("  " + nm + ": ここでは建てない ── " + S(tw["builtAs"])); continue; }
            if (part == null || !part.Contains("SannoNozura") || !Has(tw, "a") || !Has(tw, "b") || !Has(tw, "coping"))
            { sb.AppendLine("  " + nm + ": 建てない(" + (S(tw["masonry"]) ?? "") + " ── 野面の欄でない・線か天端が無い)"); continue; }
            var av = A(tw["a"]); var bv = A(tw["b"]);
            Vector2 a = Grid.W(F(av[0]), F(av[1])), b = Grid.W(F(bv[0]), F(bv[1]));
            float cop = F(tw["coping"]);
            float hardMax = 1.50f;
            { var m = System.Text.RegularExpressions.Regex.Match(S(tw["hard"]) ?? "", @"≤\s*([0-9.]+)"); if (m.Success) hardMax = float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture); }
            float footY = float.NaN; var footPoly = Has(tw, "footFace") ? TerracePolyW(S(tw["footFace"]), out footY) : null;
            if (footPoly == null) footY = float.NaN;
            float fy0 = footY; var fp0 = footPoly;
            // a 端の突き付け: 相手が門の躯体の背の面なら、線を**札の背の面**(spec.back)で切る ── 門の口の下は通り抜けで実面が無く、
            //   光線で測ると口を抜けて扉まで伸びた(2.74m・2026-10-04)。⛔ 中心で合わせない ── 札の背の面へ端を当てる(EdoPartSpec)。
            GameObject abutA = null; Vector2 backP = Vector2.zero, backN = Vector2.zero;
            { var co = Has(tw, "corners") ? O(tw["corners"]) : null; string ca = co != null && Has(co, "a") ? S(co["a"]) : "";
              if (ca.Contains("突き付け") && ca.Contains("門") && pool.Count > 0)
              {
                  var gsp = EdoBuild.SpecOf(pool[0]);
                  if (gsp != null)
                  {
                      var wp = pool[0].transform.TransformPoint(new Vector3(0f, 0f, gsp.back)); backP = new Vector2(wp.x, wp.z);
                      var fw = pool[0].transform.forward; backN = -new Vector2(fw.x, fw.z).normalized;   // 背の面の外向き = 門の内へ
                      // 背の基壇(boundaryPlinth.back)が門の背に建っていれば、突き付ける面はその天端の前の縁(札の背の面 + 犬走り)
                      bool igb = false; { var igT = Group("Ishigaki"); foreach (Transform c in igT) if (c.name.StartsWith("IGB_Omotemon")) igb = true; }
                      if (igb) backP += backN * C("inubashiri");
                      Vector2 d0 = (b - a).normalized; float den = Vector2.Dot(d0, backN);
                      if (Mathf.Abs(den) > 0.2f) { float t = Vector2.Dot(backP - a, backN) / den; a = a + d0 * t; abutA = pool[0];
                          sb.AppendLine("  " + nm + ": a 端 = " + pool[0].name + " の札の背の面(線の a から " + t.ToString("+0.00;-0.00") + "m)── 門の口の下は通り抜けで実面が無いので札で切った"); }
                  }
              } }
            var seg = new EdoBuild.NozuraSeg
            {
                name = nm, a = a, b = b, crestAt = sl => cop,
                footAt = fp0 == null ? (Func<float, float, float>)null : (x, z) => EdoGeom.PIP(fp0, new Vector2(x, z)) ? fy0 : float.NaN
            };
            var hs = new List<float>(); foreach (var h in heights) if (h <= hardMax + 1e-3f) hs.Add(h);
            var wlog = new System.Text.StringBuilder();
            var got = EdoBuild.PlaceNozuraNet(new List<EdoBuild.NozuraSeg> { seg }, EdoBuild.Ground, EdoBuild.Ground, 1.2f, grp,
                (h, g, i) => EdoAssets.Own.SannoNozura(h, g, i), (h, i) => EdoAssets.Own.SannoNozuraKado(h, i),
                (up, i) => EdoAssets.Own.SannoNozuraDan(up, i), (up, i) => EdoAssets.Own.SannoNozuraKiri(up, i),
                null, hs.ToArray(), new List<GameObject>(), wlog);
            log.AppendLine("  " + nm + ":"); log.Append(wlog.ToString());
            if (got.Count == 0) { tally(false, false, nm + ": 駒が据わらない"); continue; }
            sb.Append(MeasureNozura(nm, got, a, b, cop, hardMax, fp0, fy0, abutA, backP, backN, tally));
        }

        // ════ ② 石段(段石を造成後の斜面へ)
        sb.Append(PlaceKaidansA(tally));

        sb.AppendLine("  建てない: 坂(R_OmoteSaka・R_Tomomachi・R_Tsuyomon・R_Baba は土の坂 ── 造成後の地盤が持つ)・辺12 北端の妻の背の野面(欄に線・天端・端が無い ── 差し戻し)");
        sb.AppendLine("  勘定: ⭕ " + ok + " / ⚠ " + warn + " / ✗ " + bad);
        sb.Append(WaitReport());
        sb.AppendLine("── 明細 ──");
        sb.Append(log.ToString());
        return sb.ToString();
    }

    /// <summary>据わった野面の駒を測る(据えは動かさない)。天端の帯・見付(天端 − 見え面の前 0.25〜0.7m の足元)・
    /// 底の浮き(<see cref="EdoBuild.RootToBed"/>)・天端より上に地表が被る所(埋没)・背の地表の窪み・端の突き付け(<see cref="EdoBuild.Contact(GameObject,GameObject,Vector3,out Vector3,out int,float,float,int,bool)"/>)・区画の外。</summary>
    static string MeasureNozura(string nm, List<KeyValuePair<GameObject, Vector2>> got, Vector2 a, Vector2 b, float cop, float hardMax,
                                Vector2[] footPoly, float footY, GameObject abutA, Vector2 backP, Vector2 backN, Action<bool, bool, string> tally)
    {
        var sb = new System.Text.StringBuilder();
        Vector2 dir = (b - a).normalized;
        float crLo = float.MaxValue, crHi = float.MinValue, exLo = float.MaxValue, exHi = float.MinValue, fl = float.MinValue, bury = 0f, hollow = 0f, outW = 0f;
        float sMin = float.MaxValue, sMax = float.MinValue; GameObject endA = null;
        foreach (var kv in got)
        {
            var g = kv.Key; Vector2 fN = kv.Value;
            var vs = EdoBuild.Body(g.transform, 999999);
            if (vs.Count == 0) continue;
            float top = float.MinValue; foreach (var v in vs) top = Mathf.Max(top, v.y);
            // 天端の帯 = 頂点のうち上端 0.1 の中央値
            var band = new List<float>(); foreach (var v in vs) if (v.y >= top - 0.1f) band.Add(v.y); band.Sort();
            float crest = band[band.Count / 2];
            crLo = Mathf.Min(crLo, crest); crHi = Mathf.Max(crHi, crest);
            // 見え面の前の足元(前 0.25・0.7m の最低)
            Vector3 c = EdoBuild.RB(g).center; float front = float.MinValue;
            foreach (var v in vs) front = Mathf.Max(front, Vector2.Dot(new Vector2(v.x - c.x, v.z - c.z), fN));
            float gmin = float.MaxValue;
            foreach (float off in new[] { 0.25f, 0.7f })
            {
                var q = new Vector2(c.x, c.z) + fN * (front + off);
                // 見え面の足元の面(指図の footFace の平場の中は皮がその高さで描く ⇒ 面の高さ・外は描かれた地表)── PlaceNozuraRun の footAt と同じ測り
                float gy = footPoly != null && EdoGeom.PIP(footPoly, q) ? footY : EdoBuild.Ground(q.x, q.y);
                gmin = Mathf.Min(gmin, gy);
            }
            float ex = crest - gmin; exLo = Mathf.Min(exLo, ex); exHi = Mathf.Max(exHi, ex);
            var rt = EdoBuild.RootToBed(g, EdoBuild.Ground, 0.05f);
            if (!float.IsNaN(rt.hi)) fl = Mathf.Max(fl, rt.hi);
            // 天端より上に地表が被る所(天端の帯の頂点の真上の地表)・背の窪み(天端の帯の背の端から 0.3m 奥の地表 − 天端)
            float back = float.MaxValue; foreach (var v in vs) back = Mathf.Min(back, Vector2.Dot(new Vector2(v.x - c.x, v.z - c.z), fN));
            foreach (var v in vs)
            {
                if (v.y < top - 0.1f) continue;
                float gy = EdoBuild.Ground(v.x, v.z); if (gy > v.y + 0.02f) bury = Mathf.Max(bury, gy - v.y);
            }
            { var q = new Vector2(c.x, c.z) + fN * (back - 0.3f); float gy = EdoBuild.Ground(q.x, q.y); hollow = Mathf.Max(hollow, crest - gy); }
            foreach (var v in vs) { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(Poly, q)) outW = Mathf.Max(outW, EdoGeom.DistToPolyEdge(Poly, q)); }
            float s = Vector2.Dot(new Vector2(c.x, c.z) - a, dir);
            if (s < sMin) { sMin = s; endA = g; }
            sMax = Mathf.Max(sMax, s);
        }
        bool crestOk = Mathf.Abs(crLo - cop) <= 0.03f && Mathf.Abs(crHi - cop) <= 0.03f;
        tally(crestOk && exHi <= hardMax + 1e-3f && fl <= 0.01f && outW <= 0.001f, bury <= 0.02f,
              nm + ": " + got.Count + " 駒・天端の帯 " + crLo.ToString("F3") + "〜" + crHi.ToString("F3") + "(欄 " + cop.ToString("F2") + ")・見付 " + exLo.ToString("F2") + "〜" + exHi.ToString("F2")
              + "(硬 ≤ " + hardMax.ToString("F2") + ")・底の浮き 最悪 " + (float.IsNegativeInfinity(fl) ? "-" : fl.ToString("+0.000;-0.000")) + "m・天端に被る地表 " + bury.ToString("F3")
              + "m・区画の外 " + outW.ToString("F3") + "m");
        tally(true, hollow <= 0.10f, nm + ": 天端の背 0.3m の地表の窪み 最悪 " + hollow.ToString("F2") + "m(柔 ≤ 0.10 ── 2m 格子の造成が段の縁を均した分。皮の巡)");
        // a 端の突き付け(相手 = 門の札の背の面)── 端の駒の頂点の、背の面からの符号付きの離れの最小(+ 隙 / − めり込み)
        if (abutA != null && endA != null)
        {
            float gap = float.MaxValue; int cnt = 0;
            var ev = EdoBuild.Body(endA.transform, 999999);
            foreach (var v in ev) gap = Mathf.Min(gap, Vector2.Dot(new Vector2(v.x, v.z) - backP, backN));
            foreach (var v in ev) if (Vector2.Dot(new Vector2(v.x, v.z) - backP, backN) <= gap + 0.01f) cnt++;
            // 背の面の実体がある高さ(門の躯体の頂点が背の面の 0.05m 内に在る最低の高さ)
            float yFace = float.MaxValue; foreach (var v in EdoBuild.Body(abutA.transform, 999999)) if (Mathf.Abs(Vector2.Dot(new Vector2(v.x, v.z) - backP, backN)) < 0.05f) yFace = Mathf.Min(yFace, v.y);
            tally(gap <= 0.001f && gap >= -0.05f, true, nm + " の a 端 ↔ " + abutA.name + " の札の背の面: 隙 " + gap.ToString("+0.000;-0.000") + "m(当たり " + cnt + " 頂点)・背の面の実体の下端 " + (yFace < 1e8f ? yFace.ToString("F2") : "-") + "(⚠ その下は門の口の通り抜け)");
        }
        else sb.AppendLine("  " + nm + ": a 端は打ち切り(法面へ呑ませる)");
        sb.AppendLine("  " + nm + ": b 端は打ち切り(法面へ呑ませる)");
        return sb.ToString();
    }

    /// <summary>kaidans(案A の書式 `pos` `dir` `steps` `keri` `fumi` `w` `y0` `y1`)を <see cref="EdoBuild.SlopeSteps"/> で据える。
    /// 線 = pos から dir へ(上の面の側)。斜面の肩と裾は SlopeSteps が地表から測る(線は pos の 1m 手前から上の端の 1m 先まで)。
    /// 段石 = <see cref="EdoAssets.Own.SannoDan"/>(欄の蹴上・踏面・幅で焼いた物)。袖は欄に無いので据えない。</summary>
    static string PlaceKaidansA(Action<bool, bool, string> tally)
    {
        var sb = new System.Text.StringBuilder();
        var grp = Group("Fuzoku/Kaidan"); Clear(grp);
        foreach (var o in A(D["kaidans"]) ?? new List<object>())
        {
            var k = O(o); string nm = S(k["name"]);
            if (!Has(k, "pos") || !Has(k, "dir")) { sb.AppendLine("  石段 " + nm + ": pos・dir が無い ── 建てない"); continue; }
            var pv = A(k["pos"]); string ds = S(k["dir"]);
            Vector2 du = ds == "+v" ? new Vector2(0, 1) : ds == "-v" ? new Vector2(0, -1) : ds == "+u" ? new Vector2(1, 0) : new Vector2(-1, 0);
            float ken = Grid.ken, run = F(k["run"]), keri = F(k["keri"]), fumi = F(k["fumi"]), w = F(k["w"]);
            int steps = (int)F(k["steps"]);
            Vector2 pu = new Vector2(F(pv[0]), F(pv[1]));
            Vector2 lo = Grid.W(pu.x - du.x / ken, pu.y - du.y / ken);                         // 裾の 1m 手前
            Vector2 hi = Grid.W(pu.x + du.x * (run + 1f) / ken, pu.y + du.y * (run + 1f) / ken); // 肩の 1m 先
            string path0 = EdoAssets.Own.SannoDan(keri, fumi, w, 0);
            if (!Exists(path0)) { Wait("石段 " + nm + ": 段石が無い " + path0 + " → blender --background --python Tools/Blender/build_sanno_buzai.py -- dan " + keri.ToString("F3") + " " + fumi.ToString("F3") + " " + w.ToString("F3")); continue; }
            var sub = new GameObject(nm).transform; sub.SetParent(grp, false);
            string note;
            var tops = new List<float>(); float y0k = F(k["y0"]); for (int i = 1; i <= steps; i++) tops.Add(y0k + keri * i);   // 踏面の天端 = y0 + 蹴上 × 段(欄)
            var dans = EdoBuild.SlopeStepsAt(i => EdoAssets.Own.SannoDan(keri, fumi, w, i), sub, hi, lo, tops, fumi, "Danishi", out note);
            // 測る: 段ごとの天端(踏面の材の上端の帯)・段鼻の前の造成後の地盤・蹴上
            var got = new List<float>(); var noseShow = new List<string>(); float worstFl = float.MinValue;
            Vector2 up = (hi - lo).normalized;
            foreach (var d in dans)
            {
                var vs = EdoBuild.Body(d.transform, 999999); float t = float.MinValue; foreach (var v in vs) t = Mathf.Max(t, v.y);
                got.Add(t);
                // 段鼻 = 坂下の端(up の逆向きの最も外の頂点の線)
                Vector3 c = EdoBuild.RB(d).center; float nose = float.MaxValue; foreach (var v in vs) if (v.y >= t - 0.02f) nose = Mathf.Min(nose, Vector2.Dot(new Vector2(v.x - c.x, v.z - c.z), up));
                var q = new Vector2(c.x, c.z) + up * (nose - 0.05f);
                float gi = EdoBuild.Ground(q.x, q.y); if (!float.IsNaN(gi)) noseShow.Add((t - gi).ToString("F2"));
                var rt = EdoBuild.RootToBed(d, EdoBuild.Ground, 0.05f); if (!float.IsNaN(rt.hi)) worstFl = Mathf.Max(worstFl, rt.hi);
            }
            got.Sort();
            var rises = new List<string>(); bool riseOk = true; for (int i = 1; i < got.Count; i++) { rises.Add((got[i] - got[i - 1]).ToString("F3")); if (Mathf.Abs(got[i] - got[i - 1] - keri) > 0.01f) riseOk = false; }
            float outW = 0f; foreach (var d in dans) foreach (var v in EdoBuild.Body(d.transform, 4000)) { var q = new Vector2(v.x, v.z); if (!EdoGeom.PIP(Poly, q)) outW = Mathf.Max(outW, EdoGeom.DistToPolyEdge(Poly, q)); }
            tally(dans.Count == steps && worstFl <= 0.01f && outW <= 0.001f, riseOk,
                  "石段 " + nm + ": " + dans.Count + " 段(欄 " + steps + ")・天端 " + (got.Count > 0 ? got[0].ToString("F3") + "〜" + got[got.Count - 1].ToString("F3") : "-")
                  + "(欄 " + F(k["y0"]).ToString("F2") + "→" + F(k["y1"]).ToString("F2") + ")・段の差 " + string.Join("/", rises.ToArray()) + "(欄の蹴上 " + keri.ToString("F3")
                  + ")・段鼻の前 0.05m の地表からの見え " + string.Join("/", noseShow.ToArray()) + "m・底の浮き " + (float.IsNegativeInfinity(worstFl) ? "-" : worstFl.ToString("+0.000;-0.000"))
                  + "m・区画の外 " + outW.ToString("F3") + "m ── " + note);
            sb.AppendLine("  石段 " + nm + ": 袖は欄に無い ── 据えない(脇は造成後の地盤のまま)");
        }
        return sb.ToString();
    }
}
