using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// ══════════════════════════════════════════════════════════════════════
//  土井邸 S5 棟(案A・EDO-0533)── 御殿7棟(munes)・廊下(links)・附属屋12棟(service)・井戸(wells)。
//  ⛔ 置き方はここに書かない(規則21)── 指図の欄を読み、EdoGotenKit.Mune / EdoBuild.Place・SeatOnGround・RootToBed・
//     RecentreInBand・BuildingKidan へ渡して、据わった駒の実メッシュで測った値を刷るだけ。
//  硬い(許容0 = ✗): 足元の浮き・埋没(地面 ±0.01 ── 御殿は床下の足元の石・附属屋は下端)・区域侵犯(壁体)・部材が無い(建てない)。
//  柔らかい(狙い = ⚠): 部材の躯体と欄の足形の差・面 y と造成後の面の差(規則3 ±0.25)・開口の向き(指図に欄が無い棟は路から決めた)。
// ══════════════════════════════════════════════════════════════════════
public static partial class EdoDoiBuilder
{
    const float MUNE_GROUND_TOL = 0.01f;

    static Transform FindDeep(Transform t, string name)
    {
        if (t == null) return null;
        foreach (Transform c in t) { if (c.name == name) return c; var h = FindDeep(c, name); if (h != null) return h; }
        return null;
    }

    /// <summary>附属屋の開口の向き(格子の向き)と、開口が部材のどの局所の面か。
    /// 欄(faces)が在ればそれ、無い棟は路(routes)と石段(kaidans)の取り付きから決めた ── 根拠は返す文に刷る(柔らかい)。
    /// 部材の開口の面は EdoAssets の注釈が正典(蔵 = −X の妻・他 = +Z)。</summary>
    static bool ServiceFace(Dictionary<string, object> s, out Vector2 dirUV, out bool minusX, out string why)
    {
        string nm = S(s["name"]); minusX = false; dirUV = Vector2.zero; why = null;
        if (Has(s, "faces"))
        {
            string fc = S(s["faces"]).Trim();
            int k = fc.IndexOf('('); if (k > 0) fc = fc.Substring(0, k).Trim();
            if (fc.StartsWith("-u")) dirUV = new Vector2(-1, 0); else if (fc.StartsWith("+u")) dirUV = new Vector2(1, 0);
            else if (fc.StartsWith("-v")) dirUV = new Vector2(0, -1); else if (fc.StartsWith("+v")) dirUV = new Vector2(0, 1);
            why = "欄 faces「" + S(s["faces"]) + "」";
            return dirUV != Vector2.zero;
        }
        switch (nm)
        {
            case "Umaya": dirUV = new Vector2(0, -1); why = "路 R09・R12 が厩の平場の南(v15.6)へ取り付く ⇒ 吹き放ちを −v"; return true;
            case "Tomomachi": dirUV = new Vector2(0, 1); why = "路 R02 が北(v6.4〜8)から入り・背は表長屋 E13_N11(欄 back)⇒ 縁を +v"; return true;
            case "Kagogura": dirUV = new Vector2(0, -1); why = "路 R11 が座の南の法尻の外(v5.5)を通り通用門へ出る ⇒ 大戸を −v"; return true;
            case "Sogoka": dirUV = new Vector2(0, 1); why = "−v は表長屋 E13_N05 の背の壁まで 1間 未満(実測)で戸が長屋の背に向く ⇒ 板戸を +v(路 R11 の側・邸内)【柔】"; return true;
            case "Kura1": minusX = true; dirUV = new Vector2(0, -1); why = "石段 K_Kura1(v49 から +v へ上る)と路 R06 の終点(17.75,49.5)が南の妻 ⇒ 観音扉(−X の妻)を −v"; return true;
            case "Kura2": minusX = true; dirUV = new Vector2(0, 1); why = "路の欄が無い。−v は蔵1 の背まで 0.78m(実測)で観音扉が開けない ⇒ 観音扉を +v(北の妻・家中長屋の座との間 約2.8m)【柔・要確認】"; return true;
            case "Kachu_K1": dirUV = new Vector2(0, 1); why = "路 R04 の起点(21,65.5)が K1 と K2 の間の路地 ⇒ 戸口を +v"; return true;
            case "Kachu_K2": dirUV = new Vector2(0, -1); why = "同じ路地(v65.5)へ向かい合わせ ⇒ 戸口を −v"; return true;
            case "Kachu_K3": dirUV = new Vector2(0, 1); why = "路 R08・R10 が北(v74.9〜75.5)を通る ⇒ 戸口を +v"; return true;
            case "Hiraya_SE1": dirUV = new Vector2(0, 1); why = "路 R11 の終点(−20,24.5)が SE1 と SE2 の間 ⇒ 戸口を +v"; return true;
            case "Hiraya_SE2": dirUV = new Vector2(0, -1); why = "同じ路地(v24.5)へ向かい合わせ ⇒ 戸口を −v"; return true;
        }
        return false;
    }

    /// <summary>附属屋の部材(EdoAssets の名指し)。⛔ 無い名を推して当てない。</summary>
    static string ServicePart(Dictionary<string, object> s)
    {
        string nm = S(s["name"]);
        float du = F(s["u1"]) - F(s["u0"]), dv = F(s["v1"]) - F(s["v0"]);
        float lng = Mathf.Max(du, dv), sht = Mathf.Min(du, dv);
        if (nm == "Umaya") return EdoAssets.Own.DoiUmaya5x11;
        if (nm == "Tomomachi") return EdoAssets.Own.DoiTomomachi;
        if (nm == "Kagogura") return EdoAssets.Own.DoiKagogura;
        if (nm == "Sogoka") return EdoAssets.Own.DoiSogoka;
        if (nm == "Inari") return EdoAssets.Own.DoiInari;
        if (nm.StartsWith("Kura")) return EdoAssets.Own.DoiKura(sht, lng);   // 引数は (梁間, 桁行)・端数可
        if (nm.StartsWith("Kachu_") || nm.StartsWith("Hiraya_"))
        {
            if (Mathf.Abs(lng - Mathf.Round(lng)) > 0.01f) return null;
            return EdoAssets.Own.DoiKachu(Mathf.RoundToInt(lng));
        }
        return null;
    }

    [MenuItem(MENU + "5棟 御殿・廊下・附属屋・井戸(案A)")]
    public static void Stage5MuneMenu() { Debug.Log("[Doi] " + Stage5_Mune()); }

    /// <summary>**S5 棟(案A・EDO-0533)**。① 御殿7棟を EdoGotenKit.Mune(入側四周1間 = const.moyaBand.irikawa・入母屋 = munes[].roof・床下の足元)で、
    /// 面 = 造成後の地形の中央値(FaceY = EdoBuild.PadY)へ ② 廊下(links)── 部材が組めない物は建てずに要求を刷る
    /// ③ 附属屋12棟を札の足形の中心で欄の矩形へ・開口を路の側へ・下端を地面へ(SeatOnGround → RootToBed → RecentreInBand → 浮けば BuildingKidan)
    /// ④ 井戸を地面へ。冪等(群を空けて建て直す)。</summary>
    public static string Stage5_Mune()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var sb = new System.Text.StringBuilder("S5 棟(案A):\n");
        int bad = 0, warn = 0;
        Action<int, string> line = (lv, t) => { sb.AppendLine("  " + (lv == 2 ? "✗" : lv == 1 ? "⚠" : "⭕") + " " + t); if (lv == 2) bad++; else if (lv == 1) warn++; };
        PlaceGotenA(line);
        PlaceLinksA(line);
        PlaceServiceA(line);
        PlaceWellsA(line);
        sb.Insert(0, "✗ " + bad + " / ⚠ " + warn + "\n");
        sb.Append(WaitReport());
        return sb.ToString();
    }

    // ---------------------------------------------------------------- ① 御殿
    static void PlaceGotenA(Action<int, string> line)
    {
        var grp = Group("Buildings"); Clear(grp);
        var f = Grid;
        float floor = C("gotenFloor");
        var mb = O(O(D["const"])["moyaBand"]);
        if (!Has(mb, "irikawa")) { line(2, "指図 const.moyaBand.irikawa が無い ── 御殿を建てない"); return; }
        int iri = Mathf.RoundToInt(F(mb["irikawa"]));
        foreach (var o in A(D["munes"]))
        {
            var m = O(o); string nm = S(m["name"]);
            float u0 = F(m["u0"]), v0 = F(m["v0"]), u1 = F(m["u1"]), v1 = F(m["v1"]);
            string ridge = Has(m, "ridge") ? S(m["ridge"]) : null;
            if (ridge != "u" && ridge != "v") { line(2, "棟 " + nm + ": ridge が u/v でない ── 建てない"); continue; }
            bool alongU = ridge == "u";
            float Wk = alongU ? (u1 - u0) : (v1 - v0), Dk = alongU ? (v1 - v0) : (u1 - u0);
            if (Mathf.Abs(Wk - Mathf.Round(Wk)) > 0.01f) { line(2, "棟 " + nm + ": 桁行 " + Wk + "間 が整数でない ── キットで組めない"); continue; }
            int nx = Mathf.RoundToInt(Wk) - 2 * iri;
            int nzI = Mathf.FloorToInt(Dk + 0.001f) - 2 * iri; float frac = Dk - Mathf.FloorToInt(Dk + 0.001f);
            if (nx < 1 || nzI < 1) { line(2, "棟 " + nm + ": 入側を回すと身舎が残らない"); continue; }
            // 屋根 = 欄 roof の名指し「Goten.RoofIrimoya_(桁行,梁間)」
            string roof = null, rk = Has(m, "roof") ? S(m["roof"]) : null;
            if (rk != null && rk.Contains("RoofIrimoya_("))
            {
                var parts = rk.Substring(rk.IndexOf('(') + 1).TrimEnd(')').Split(',');
                var inv = System.Globalization.CultureInfo.InvariantCulture;
                float rw = float.Parse(parts[0].Trim(), inv), rd = float.Parse(parts[1].Trim(), inv);
                if (Mathf.Abs(rw - Wk) > 0.01f || Mathf.Abs(rd - Dk) > 0.01f)
                    line(1, "棟 " + nm + ": 欄の屋根 " + rk + " が足形 " + Wk + "×" + Dk + "間 と食い違う(屋根は欄の名指しで据えた)");
                roof = EdoAssets.Goten.RoofIrimoya_(rw, rd);
                if (!Exists(roof)) { line(2, "棟 " + nm + ": 屋根の部材が無い " + roof + " ── 骨組みだけ建てた"); roof = null; }
            }
            else line(2, "棟 " + nm + ": 欄 roof が入母屋の名指しでない(" + rk + ")── 骨組みだけ建てた");
            float y = FaceY(u0, v0, u1, v1, F(m["y"]), "棟 " + nm);
            var w = alongU ? f.W(u0, v0) : f.W(u1, v0);
            var g = EdoGotenKit.Mune(nm, grp, new Vector3(w.x, y, w.y), alongU ? YawAlongU() : YawAlongV(),
                                     nx, nzI, iri, floor, roof, true, true, null, null, -1, iri,
                                     ashimoto: true, nzFrac: frac);
            if (g == null) { line(2, "棟 " + nm + ": 組めない"); continue; }
            Undo.RegisterCreatedObjectUndo(g, "mune");
            float stretch; int nStretch = EdoGotenKit.AshimotoReach(g, 0.05f, out stretch);   // 面の縁の法へ張り出す濡縁の足は下へ伸ばす
            int an, af; string aw; float ag = EdoGotenKit.AshimotoGap(g, out an, out af, out aw);
            string head = "棟 " + nm + "(" + S(m["label"]) + " " + Wk + "×" + Dk + "間・面 " + y.ToString("F2") + " / 欄 " + F(m["y"]).ToString("F2") + ")"
                        + (nStretch > 0 ? "・地面に届かない足 " + nStretch + " 駒を下へ伸ばした(最大 " + stretch.ToString("F3") + "m)" : "");
            if (an == 0) line(2, head + ": 床下の足元の部材が無い(床高 " + floor + " の版)");
            else line(af > 0 ? 2 : 0, head + ": 足元 " + an + " 駒・最も浮いた当たり " + ag.ToString("+0.000;-0.000") + "m @" + aw + (af > 0 ? "(浮き " + af + " 駒)" : ""));
        }
    }

    // ---------------------------------------------------------------- ② 廊下
    static void PlaceLinksA(Action<int, string> line)
    {
        var grp = Group("Buildings");
        var f = Grid;
        float floor = C("gotenFloor");
        foreach (var o in A(D["links"]))
        {
            var l = O(o); string nm = S(l["name"]);
            float u0 = F(l["u0"]), v0 = F(l["v0"]), u1 = F(l["u1"]), v1 = F(l["v1"]);
            float du = u1 - u0, dv = v1 - v0;
            // 走り = 両端が棟の面に当たる向き(⛔ 長い方で決めない ── 幅 2間 × 走り 2.5間 の廊下がある)
            bool touchV = false, touchU = false;
            foreach (var mo in A(D["munes"]))
            {
                var m = O(mo);
                if (Mathf.Abs(F(m["v1"]) - v0) < 0.01f || Mathf.Abs(F(m["v0"]) - v1) < 0.01f) touchV = true;
                if (Mathf.Abs(F(m["u1"]) - u0) < 0.01f || Mathf.Abs(F(m["u0"]) - u1) < 0.01f) touchU = true;
            }
            bool alongU = touchU && !touchV ? true : (touchV ? false : du > dv);
            float run = alongU ? du : dv, wide = alongU ? dv : du;
            float drop = Has(l, "drop") ? F(l["drop"]) : 0f;
            string kind = S(l["kind"]);
            if (Mathf.Abs(wide - 1f) > 0.01f)
            {
                line(2, "廊下 " + nm + "(" + kind + "): 幅 " + wide.ToString("0.##") + "間 ── 部材キットの廊下(EdoGotenKit.Roka・屋根 Goten_Roof_Kirizuma_*)は幅 1間 しか組めない。"
                        + "⛔ 建てない(欄の幅を 1間 にするか、幅 " + wide.ToString("0.##") + "間 の廊下の部材が要る)");
                continue;
            }
            if (drop > 0.001f)
            {
                string kp = EdoAssets.Goten.KaidanRoka(run * f.ken, drop);
                if (!Exists(kp))
                {
                    line(2, "廊下 " + nm + "(階段廊下・走り " + run + "間 落差 " + drop + "): 部材が無い " + kp + " ⇒ 部材方へ: blender --background --python Tools/Blender/build_goten_kaidan.py -- "
                            + (run * f.ken).ToString("0.###") + " " + drop.ToString("0.###") + " Goten_KaidanRoka_" + (run * f.ken).ToString("0.##") + "x" + drop.ToString("0.##") + " ── ⛔ 建てない");
                    continue;
                }
            }
            string rk = EdoAssets.Goten.RoofKirizuma(run);
            if (!Exists(rk)) line(1, "廊下 " + nm + ": 切妻屋根が無い " + rk);
            if (drop > 0.001f)
            {
                // 上の端 = 走りの両端で当たる棟のうち面の高い方。局所 +X が坂下を向くよう、上の端から張る
                float yS = float.NaN, yE = float.NaN; Dictionary<string, object> mS = null, mE = null;
                foreach (var mo in A(D["munes"]))
                {
                    var m = O(mo);
                    if (alongU ? Mathf.Abs(F(m["u1"]) - u0) < 0.01f : Mathf.Abs(F(m["v1"]) - v0) < 0.01f) { yS = F(m["y"]); mS = m; }
                    if (alongU ? Mathf.Abs(F(m["u0"]) - u1) < 0.01f : Mathf.Abs(F(m["v0"]) - v1) < 0.01f) { yE = F(m["y"]); mE = m; }
                }
                bool hiAtEnd = !float.IsNaN(yE) && (float.IsNaN(yS) || yE > yS);
                // 上の端の床は上の棟の床に触れる ⇒ 地盤は上の棟の足形で測った面(⛔ 廊下の足形の中央値は下の段を拾う)
                var mHi = hiAtEnd ? mE : mS;
                float y = mHi != null ? FaceY(F(mHi["u0"]), F(mHi["v0"]), F(mHi["u1"]), F(mHi["v1"]), F(mHi["y"]), "廊下 " + nm + " の上の棟 " + S(mHi["name"]))
                                      : FaceY(u0, v0, u1, v1, F(l["y"]), "廊下 " + nm);
                Vector2 wh = alongU ? (hiAtEnd ? f.W(u1, v1) : f.W(u0, v0)) : (hiAtEnd ? f.W(u0, v1) : f.W(u1, v0));
                float yaw = (alongU ? YawAlongU() : YawAlongV()) + (hiAtEnd ? 180f : 0f);
                string kn;
                var kg = EdoGotenKit.KaidanRoka(nm, grp, new Vector3(wh.x, y, wh.y), yaw, run, floor, drop,
                                                EdoAssets.Goten.KaidanRoka(run * f.ken, drop), out kn);
                if (kg != null) { Undo.RegisterCreatedObjectUndo(kg.transform.parent.gameObject, "kaidan"); line(0, "廊下 " + nm + "(階段廊下 " + run + "間・落差 " + drop + "): " + kn); }
                else line(2, "廊下 " + nm + ": 階段廊下が組めない ── " + kn);
                continue;
            }
            float yF = FaceY(u0, v0, u1, v1, F(l["y"]), "廊下 " + nm);
            var w = alongU ? f.W(u0, v0) : f.W(u1, v0);
            var g = EdoGotenKit.Roka(nm, grp, new Vector3(w.x, yF, w.y), alongU ? YawAlongU() : YawAlongV(), run, floor, colStart: false, colEnd: false);
            if (g != null) { Undo.RegisterCreatedObjectUndo(g, "roka"); line(0, "廊下 " + nm + ": " + run + "間"); }
        }
    }

    // ---------------------------------------------------------------- ③ 附属屋
    static void PlaceServiceA(Action<int, string> line)
    {
        var grp = Group("Fuzoku/Service"); Clear(grp);
        var kiso = Group("Fuzoku/Kiso"); Clear(kiso);
        var f = Grid;
        Vector2 uD = (f.W(1f, 0f) - f.W(0f, 0f)).normalized, vD = (f.W(0f, 1f) - f.W(0f, 0f)).normalized;
        foreach (var o in A(D["service"]))
        {
            var s = O(o); string nm = S(s["name"]);
            float u0 = F(s["u0"]), v0 = F(s["v0"]), u1 = F(s["u1"]), v1 = F(s["v1"]);
            string path = ServicePart(s);
            if (path == null || !Exists(path)) { line(2, "附属屋 " + nm + ": 部材が無い " + (path ?? "(名指し無し)") + " ── 建てない"); continue; }
            Vector2 dUV; bool mX; string why;
            if (!ServiceFace(s, out dUV, out mX, out why)) { line(2, "附属屋 " + nm + ": 開口の向きが決まらない ── 建てない"); continue; }
            Vector2 dW = (uD * dUV.x + vD * dUV.y).normalized;
            float yaw = mX ? YawFor(-dW) : YawFace(dW);
            // 札の足形(foot)の中心を欄の矩形の中心へ ── ⛔ ピボットで決めない
            var sp = EdoPartSpec.Get(path);
            Vector2 fc = Vector2.zero; float fw = float.NaN, fd = float.NaN;
            if (sp != null && sp.foot != null && sp.foot.Count >= 3)
            {
                float x0 = float.MaxValue, x1 = float.MinValue, z0 = float.MaxValue, z1 = float.MinValue;
                foreach (var q in sp.foot) { x0 = Mathf.Min(x0, q.x); x1 = Mathf.Max(x1, q.x); z0 = Mathf.Min(z0, q.y); z1 = Mathf.Max(z1, q.y); }
                fc = new Vector2((x0 + x1) * 0.5f, (z0 + z1) * 0.5f); fw = x1 - x0; fd = z1 - z0;
            }
            else { Vector2 bc; float bw, bd; if (EdoBuild.BodyFootprintLocal(path, out bc, out bw, out bd)) { fc = bc; fw = bw; fd = bd; } }
            if (float.IsNaN(fw)) { line(2, "附属屋 " + nm + ": 札も躯体の足形も取れない ── 建てない"); continue; }
            Vector2 c = f.W((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
            Vector3 off = Quaternion.Euler(0f, yaw, 0f) * new Vector3(fc.x, 0f, fc.y);
            float y = F(s["y"]);
            var go = EdoBuild.Place(path, new Vector3(c.x - off.x, y, c.y - off.z), yaw, Vector3.one, grp, nm);
            if (go == null) { line(2, "附属屋 " + nm + ": 据えられない " + path); continue; }
            // 足形の照合(柔): 札の足形 ↔ 欄の矩形
            float wantL = Mathf.Max(u1 - u0, v1 - v0) * f.ken, wantS = Mathf.Min(u1 - u0, v1 - v0) * f.ken;
            float haveL = Mathf.Max(fw, fd), haveS = Mathf.Min(fw, fd);
            string fitNote = "足形 " + haveL.ToString("F2") + "×" + haveS.ToString("F2") + " / 欄 " + wantL.ToString("F2") + "×" + wantS.ToString("F2");
            // 取り合い(硬): 欄 back「<駒> の背から N間 離す」= 背の向きへ相手の実メッシュまで突き付け、N間 残す
            string tori = "";
            var bk = Has(s, "back") ? O(s["back"]) : null;
            if (bk != null && Has(bk, "rule"))
            {
                var mm = System.Text.RegularExpressions.Regex.Match(S(bk["rule"]), @"([A-Za-z0-9_]+)\s*の背から\s*([0-9.]+)\s*間");
                Transform other = null;
                if (mm.Success) foreach (var gn in new[] { "Kakoi", "Mon" }) { var gg = Group(gn); var hit = FindDeep(gg, mm.Groups[1].Value); if (hit != null) { other = hit; break; } }
                if (other == null) { line(2, "附属屋 " + nm + ": 欄 back の相手が引けない「" + S(bk["rule"]) + "」"); }
                else
                {
                    float want = float.Parse(mm.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture) * f.ken;
                    // 壁体の面どうし(帯 = 各々の下端から 0.15〜1.8m)── ⛔ 軒は数えない(欄の amaochi: 軒の出は約 0.57m 重なる設計)
                    float ym = EdoBuild.RB(go).min.y, yo = EdoBuild.RB(other.gameObject).min.y;
                    float tgt = EdoBuild.Face(other.gameObject, dW, yo + 0.15f, yo + 1.8f, true);
                    float mv = EdoBuild.Abut(go, dW, ym + 0.15f, ym + 1.8f, false, tgt, want);
                    float now = EdoBuild.Face(go, dW, ym + 0.15f, ym + 1.8f, false) - tgt;
                    tori += "背の壁を " + other.name + " の背の壁から " + now.ToString("F3") + "m(欄 " + want.ToString("F3") + "・動かした " + mv.ToString("+0.000;-0.000") + "m)・";
                    if (Mathf.Abs(now - want) > 0.001f) line(2, "附属屋 " + nm + ": 背の離れ " + now.ToString("F3") + " ≠ 欄 " + want.ToString("F3"));
                }
            }
            // 取り合い(硬): 欄 east「妻は表門の(南の)妻の通りより手前(門の躯体の背に回らない)」── 札の足形どうしで、門の側の妻を門の妻の通りの内へ
            var ea = Has(s, "east") ? O(s["east"]) : null;
            if (ea != null && Has(ea, "rule") && S(ea["rule"]).Contains("表門"))
            {
                var gate = Group("Mon").Find("Omotemon");
                var gsp = gate != null ? EdoBuild.SpecOf(gate.gameObject) : null;
                if (gsp == null || sp == null) line(2, "附属屋 " + nm + ": 欄 east を測れない(表門か自分の札が無い)");
                else
                {
                    Vector2 gc0 = Vector2.zero; foreach (var q in gsp.foot) gc0 += EdoPartSpec.W(gate, q.x, q.y); gc0 /= gsp.foot.Count;
                    Vector2 ax = (Mathf.Abs(Vector2.Dot(gc0 - c, uD)) >= Mathf.Abs(Vector2.Dot(gc0 - c, vD)) ? uD : vD);
                    if (Vector2.Dot(gc0 - c, ax) < 0f) ax = -ax;                    // 門の側へ向く軸
                    float gMin = float.MaxValue, mMax = float.MinValue;
                    foreach (var q in gsp.foot) gMin = Mathf.Min(gMin, Vector2.Dot(EdoPartSpec.W(gate, q.x, q.y), ax));
                    foreach (var q in sp.foot) mMax = Mathf.Max(mMax, Vector2.Dot(EdoPartSpec.W(go.transform, q.x, q.y), ax));
                    float over = mMax - gMin;
                    if (over > 0f) { go.transform.position -= new Vector3(ax.x, 0f, ax.y) * over; tori += "門の側の妻を表門の妻の通りへ退げた(" + over.ToString("F3") + "m)・"; }
                    else tori += "門の側の妻は表門の妻の通りの " + (-over).ToString("F3") + "m 内・";
                }
            }
            // 取り合い(硬): 塀の欄 clear「芯は棟の面から N間 以上」── 塀の芯の線から壁体の面を離す(EdoBuild.KeepClearOfLine)
            foreach (var ro in A(D["runs"]))
            {
                var r = O(ro); if (!Has(r, "pts") || !Has(r, "clear")) continue;
                var cl = O(r["clear"]); var cm = System.Text.RegularExpressions.Regex.Match(S(cl["rule"]), @"芯は棟の面から\s*([0-9.]+)\s*間\s*以上");
                if (!cm.Success) continue;
                var pl = A(r["pts"]); var lw = new List<Vector2>(); foreach (var q in pl) { var qq = A(q); lw.Add(f.W(F(qq[0]), F(qq[1]))); }
                float need = float.Parse(cm.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) * f.ken, md;
                float mv = EdoBuild.KeepClearOfLine(go, lw, need, 0.15f, 1.8f, out md);   // 帯は壁体(軒先の垂れ 2.3m 前後を入れない)
                if (mv > 0.0005f) tori += S(r["name"]) + " の芯から " + md.ToString("F3") + "m へ離した(動かした " + mv.ToString("F3") + "m・欄 ≥" + need.ToString("F3") + ")・";
                if (md < need - 0.001f) line(2, "附属屋 " + nm + ": " + S(r["name"]) + " の芯から " + md.ToString("F3") + "m(欄 ≥" + need.ToString("F3") + ")");
            }
            // 据え(硬 ±0.01): 地面に当て → 下端の全部で測る → 帯の中へ → 浮けば布石の基壇
            string seat;
            try { EdoBuild.SeatOnGround(go, 0f); } catch (Exception ex) { line(2, "附属屋 " + nm + ": 据えられない " + ex.Message); continue; }
            var rt = EdoBuild.RootToBed(go, EdoBuild.Ground, 0.1f);
            if (!float.IsNaN(rt.lo) && rt.lo < -MUNE_GROUND_TOL) { go.transform.position -= new Vector3(0f, rt.lo, 0f); rt = EdoBuild.RootToBed(go, EdoBuild.Ground, 0.1f); }
            int lv = 0;
            if (!float.IsNaN(rt.hi) && rt.hi > MUNE_GROUND_TOL && !EdoBuild.RecentreInBand(go, ref rt, EdoBuild.Ground, MUNE_GROUND_TOL))
            {
                string kn; var ks = EdoBuild.BuildingKidan(go, kiso, EdoBuild.Ground, out kn);
                if (ks.Count > 0)
                {
                    var bed = EdoBuild.GroundOrBed(new EdoBuild.BedIndex(ks));
                    float hi0 = rt.hi;
                    rt = EdoBuild.RootToBed(go, bed, 0.1f);
                    if (rt.hi > MUNE_GROUND_TOL) EdoBuild.RecentreInBand(go, ref rt, bed, MUNE_GROUND_TOL, 0.08f);
                    seat = "布石の基壇 " + ks.Count + " 個で受けた(地面からの浮き " + hi0.ToString("F2") + "m)・";
                }
                else seat = "布石の基壇を敷けない(" + kn + ")・";
                if (rt.hi > MUNE_GROUND_TOL) lv = 2;
            }
            else seat = "";
            float dy = go.transform.position.y - y;
            if (lv == 0 && Mathf.Abs(dy) > 0.25f) lv = 1;
            line(lv, "附属屋 " + nm + "(" + S(s["label"]) + "・" + System.IO.Path.GetFileNameWithoutExtension(path) + "): " + tori + seat + "下端 浮き " + (float.IsNaN(rt.hi) ? float.NaN : rt.hi).ToString("+0.000;-0.000")
                     + " / 根入れ " + (float.IsNaN(rt.lo) ? float.NaN : rt.lo).ToString("+0.000;-0.000") + "m・座 " + go.transform.position.y.ToString("F2") + "(欄 " + y.ToString("F2") + "・差 " + dy.ToString("+0.00;-0.00") + ")・" + fitNote
                     + "・開口 " + (dUV.x > 0 ? "+u" : dUV.x < 0 ? "−u" : dUV.y > 0 ? "+v" : "−v") + "(" + why + ")");
        }
    }

    // ---------------------------------------------------------------- ④ 井戸
    static void PlaceWellsA(Action<int, string> line)
    {
        var grp = Group("Fuzoku/Ido"); Clear(grp);
        var f = Grid;
        string path = EdoAssets.Own.DoiIdo;
        if (!Exists(path)) { line(2, "井戸の部材が無い " + path); return; }
        foreach (var o in A(D["wells"]))
        {
            var w = O(o); Vector2 p = f.W(F(w["u"]), F(w["v"]));
            var go = EdoBuild.Place(path, new Vector3(p.x, GroundY(p.x, p.y), p.y), YawAlongU(), Vector3.one, grp, S(w["name"]));
            if (go == null) { line(2, "井戸 " + S(w["name"]) + ": 据えられない"); continue; }
            EdoBuild.SeatOnGround(go, 0.06f);   // 底 −0.06 は根石(部材の注釈)── 当たりを地面へ着け根石ぶん沈める
            Vector3 at; int cnt; float gap = EdoBuild.Contact(go, out at, out cnt);
            line(gap > MUNE_GROUND_TOL ? 2 : 0, "井戸 " + S(w["name"]) + ": 地面との当たり " + gap.ToString("+0.000;-0.000") + "m(根石 0.06 を沈めた後)");
        }
    }
}
