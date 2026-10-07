using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// 土井 S9 排水(案A・EDO-0533)── 指図 drains[D1〜D13] の segs/masu/cross/toriai/outletBuild と drainKata(型 A〜P)を読み、
//  線の言い方を**建った物**へ解いて EdoBuild の関数(EdoBuildMizo.cs)へ渡すだけ。⛔ 置き方・測り方をここに書かない(規則21)。
//  ⛔ 座標を発明しない(規則2): 読めない言い方・建っていない相手は Wait に名乗って据えない。
//  順序: 5棟・3門・4a 土留め・6柵 の後に流す → 流した後に 4b 縁の皮を流し直す(皮は溝の駒の今の位置に合わせる)。
//  ⚠ 方角の語(北・南・東・西)は線に使わない ── この指図では「馬場の東の口」(u+)と「台地の南の縁」(u−)が同じ軸に載り、格子の向きと語が一致しない。
public static partial class EdoDoiBuilder
{
    [MenuItem(MENU + "9 排水(雨落ち・溝・桝・落とし)")]
    public static void Stage9MizoMenu() { Debug.Log("[Doi] " + Stage9_Mizo()); }

    class MzSeg
    {
        public string id, drain, kata, line, flow, to; public int di, si;
        public Dictionary<string, object> raw, dr;
        public List<List<Vector2>> lines;            // 解いた線(上流 → 下流)
        public List<EdoBuild.MizoProfile> prof = new List<EdoBuild.MizoProfile>();
        public List<GameObject> pieces = new List<GameObject>();
        public float halfW = float.NaN;
        public bool built;
        public List<List<Vector2>> rawLines; public string why;
        public MzSeg fromSeg;      // N9「<区間> の尻から」の始点の区間(段落ちの頭の底をそこから採る)
        public bool fixedDir;      // 線が「A から B へ/まで」で向きを持つ(N5・N7・N9)── orient に掛けない
    }
    class MzMasu { public string id; public Dictionary<string, object> raw; public int di, k; public List<Vector2> inEnds = new List<Vector2>(); public List<float> inBottoms = new List<float>(); public string then; }

    /// <summary>欄が無ければ null(指図の drains は系統ごとに持つ欄が違う ── 索引子で引くと KeyNotFound で S9 ごと落ちる)。</summary>
    static object Gk(Dictionary<string, object> d, string k) { object o; return d != null && d.TryGetValue(k, out o) ? o : null; }
    public static string Stage9_Mizo()
    {
        { var gate0 = EdoSashizuExport.ReviewGate("doi"); if (gate0 != null) return gate0; }
        _wait.Clear();
        var sb = new System.Text.StringBuilder("S9 排水(案A):\n");
        int bad = 0, warn = 0, okN = 0;
        Action<int, string> line = (lv, t) => { sb.AppendLine("  " + (lv == 2 ? "✗" : lv == 1 ? "⚠" : "⭕") + " " + t); if (lv == 2) bad++; else if (lv == 1) warn++; else okN++; };
        var kata = O(D["drainKata"]); var drains = A(D["drains"]);
        if (kata == null || drains == null) return sb + "  ⛔ 指図に drainKata / drains が無い ── 建てない";
        var grp = Group("Mizo"); Clear(grp);
        var f = Grid; float ken = f.ken;
        Vector2 uW = new Vector2(f.ux, f.uz).normalized;

        // ---- 建った棟の軒先の外周(御殿 Buildings・附属屋 Fuzoku/Service)
        var eave = new Dictionary<string, Vector2[]>(); var names = new Dictionary<string, string>();
        Action<string, string> alias = (k, nm) => { k = k.Trim(); if (k.Length > 0 && !names.ContainsKey(k)) names[k] = nm; };
        foreach (var key in new[] { "munes", "service" })
            foreach (var o in A(D[key]) ?? new List<object>())
            {
                var m = O(o); string nm = Sk(m, "name"); string lb = Sk(m, "label") ?? "";
                alias(nm, nm); alias(lb, nm);
                foreach (var piece in lb.Split('・', '(', ')', '(', ')', ' ')) if (piece.Length >= 1) alias(piece, nm);
                var tr = FindDeep(Group(key == "munes" ? "Buildings" : "Fuzoku/Service"), nm);
                if (tr == null) continue;
                Vector2[] rect; float ey; string how;
                if (EdoBuild.EaveRect(tr, uW, out rect, out ey, out how)) { eave[nm] = rect; if (how != "屋根の実メッシュ") Wait("軒先の外周 " + nm + ": " + how); }
            }
        Func<string, Vector2[]> poly = nm =>
        {
            foreach (var key in new[] { "terraces", "gardens" })
                foreach (var o in A(D[key]) ?? new List<object>())
                {
                    var t = O(o); if (Sk(t, "name") != nm || !Has(t, "poly")) continue;
                    var pl = A(Gk(t, "poly")); var w = new Vector2[pl.Count];
                    for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); w[i] = f.W(F(q[0]), F(q[1])); }
                    return w;
                }
            return null;
        };
        // 溝の地面 = 造成後の地盤(graded)と、点を含む面(指図 terraces の poly・y)の低い方。
        // ⭐ graded は 1m の格子の双一次で、0.5間 の小段や面の縁では隣の升(塀の天端・上の面)を拾って高く読む ── 皮は面の中を面の高さで描くので、
        //    溝はその低い方に合わせる(⛔ 高く読んだ地面に底を合わせて、駒の縁と小口を下の面の上へ浮かせない ── D9 seg1・EDO-0533)。
        var mizoFaces = new List<KeyValuePair<Vector2[], float>>();
        foreach (var o in A(D["terraces"]) ?? new List<object>())
        {
            var t = O(o); if (t == null || !Has(t, "poly") || !Has(t, "y") || t["y"] == null || t["y"] is string) continue;
            var pl = A(t["poly"]); if (pl == null || pl.Count < 3) continue;
            var w = new Vector2[pl.Count]; for (int i = 0; i < pl.Count; i++) { var q = A(pl[i]); w[i] = f.W(F(q[0]), F(q[1])); }
            mizoFaces.Add(new KeyValuePair<Vector2[], float>(w, F(t["y"])));
        }
        Func<float, float, float> groundMizo = (x, z) =>
        {
            float gy = GroundY(x, z); var q = new Vector2(x, z);
            foreach (var fc in mizoFaces) if (EdoGeom.PIP(fc.Key, q)) gy = float.IsNaN(gy) ? fc.Value : Mathf.Min(gy, fc.Value);
            return gy;
        };
        // 「<相手>側」の相手の語 → 面・庭の名(指図の label の頭の語で引く)
        Func<string, string> sideTarget = word =>
        {
            foreach (var key in new[] { "gardens", "terraces" })
                foreach (var o in A(D[key]) ?? new List<object>())
                {
                    var t = O(o); string lb = Sk(t, "label") ?? ""; string nm = Sk(t, "name");
                    string head = lb.Split('(', '(', '・', ' ')[0];
                    if (head == word || lb.StartsWith(word + "(") || lb.StartsWith(word + "(")) return nm;
                    if (key == "gardens" && head.EndsWith("の" + word)) return nm;
                }
            return null;
        };
        Func<string, List<string>> bldNames = phrase =>
        {
            var res = new List<string>(); phrase = phrase.Trim();
            var rom = Regex.Matches(phrase, @"[A-Za-z][A-Za-z0-9_]*");
            if (rom.Count > 0)
            {
                string prev = null;
                foreach (Match mm in rom)
                {
                    string tk = mm.Value;
                    if (!eave.ContainsKey(tk) && prev != null && prev.Contains("_")) tk = prev.Substring(0, prev.LastIndexOf('_') + 1) + tk;
                    res.Add(tk); prev = tk;
                }
                return res;
            }
            var ex = Regex.Match(phrase, @"^(.+?)[((]([一二三四五・]+)[))]$");
            if (ex.Success) { foreach (var nn in ex.Groups[2].Value.Split('・')) { string k = ex.Groups[1].Value + "(" + nn + ")"; if (names.ContainsKey(k)) res.Add(names[k]); else return null; } return res; }
            if (names.ContainsKey(phrase)) { res.Add(names[phrase]); return res; }
            return null;
        };
        var blockersAll = new List<Vector2[]>(eave.Values);
        Func<string, List<Vector2[]>> blockersBut = self => { var l = new List<Vector2[]>(); foreach (var kv in eave) if (kv.Key != self) l.Add(kv.Value); return l; };
        Func<Vector2[], List<Vector2>> loop = r => new List<Vector2> { r[0], r[1], r[2], r[3], r[0] };
        Func<string, Transform, List<GameObject>> piecesByPrefix = (prefix, root) =>
        {
            var l = new List<GameObject>(); if (root == null) return l;
            foreach (var mr in root.GetComponentsInChildren<MeshRenderer>())
            {
                var t = mr.transform; bool hit = false;
                while (t != null && t != root) { if (t.name == prefix || t.name.StartsWith(prefix + "_")) { hit = true; break; } t = t.parent; }
                if (hit && mr.gameObject.activeInHierarchy) l.Add(mr.gameObject);
            }
            return l;
        };
        Vector2 parcelC = Vector2.zero; { var P = Poly; foreach (var p in P) parcelC += p; parcelC /= P.Length; }

        // ---- 型ごとの断面(drainKata)
        Func<string, float> topAbove = k =>
        {
            var kk = Has(kata, k) ? O(kata[k]) : null; if (kk == null) return 0f;
            if (Has(kk, "like")) kk = O(kata[Sk(kk, "like")]);
            if (Has(kk, "curb") && O(kk["curb"]) != null && Has(O(kk["curb"]), "topAbove")) return F(O(kk["curb"])["topAbove"]);
            if (Has(kk, "lid") && O(kk["lid"]) != null && Has(O(kk["lid"]), "topAbove")) return F(O(kk["lid"])["topAbove"]);
            if (Has(kk, "topAbove")) return F(kk["topAbove"]);
            if (Has(kk, "topBelow")) return -F(kk["topBelow"]);
            return 0f;
        };
        Func<string, string, float> kf = (k, field) =>
        {
            var kk = O(Has(kata, k) ? kata[k] : null); if (kk == null) return float.NaN;
            if (!Has(kk, field) && Has(kk, "like")) kk = O(kata[Sk(kk, "like")]);
            return Has(kk, field) && !(kk[field] is string) && !(kk[field] is List<object>) && !(kk[field] is Dictionary<string, object>) ? F(kk[field]) : float.NaN;
        };
        Func<string, float, string> mizoPath = (k, depth) =>
        {
            if (k == "E" || k == "F")
            {
                // ⭐ 硬: 駒の深さ(実メッシュの天端 − 溝の底)≤ 要求 ── 要求以下で最も深い版を選ぶ(⛔ 丸めで深い版へ上げない ── 天端が地面より上へ出て縁と小口が浮く・EDO-0533)。
                // どの版も要求より深ければ最も浅い版を返す(据える側 LayMizo の硬い検めが浮きを退ける)。
                float dmin = kf(k, "depthMin"), dmax = kf(k, "depthMax");
                string shallow = null;
                for (float d = dmax; d >= dmin - 1e-4f; d -= 0.05f)
                {
                    string pth = EdoBuild.AssetByName("Own", "DoiMizo", k, (float)Math.Round(d, 2));
                    if (pth == null || !Exists(pth)) continue;
                    var mpk = EdoBuild.MizoPieceOf(pth); if (!mpk.ok) continue;
                    shallow = pth;
                    if (mpk.Depth <= depth + 0.005f) return pth;
                }
                return shallow ?? EdoBuild.AssetByName("Own", "DoiMizo", k, (float)Math.Round(dmin, 2));
            }
            return EdoBuild.AssetByName("Own", "DoiMizo", k);
        };
        // ⭐ 据える駒の深さの版(LayMizo の pathAt)── A・C・D も部材方が深さの版を焼いてある(A 0.10〜0.30・C 0.10/0.15・D 0.20〜0.45 ── 欄 depthFrom「面 − 底(底の勾配からの従属値)」)。
        //   要求以下で最も深い版(E・F と同じ硬い選び方)。⛔ 2026-10-05 まで A・C・D は既定の一版だけで勾配を取り、天端が地面より沈んで(D2 seg2 0.136・D10 seg1 0.136・
        //   D1 seg2 0.200・D2 seg1 0.768)、溝の脇に据わった駒(蔵 Kura1 0.184・平家長屋 Hiraya_SE1/2 0.13・飛石 Tobi_Shoin_0 0.147)が沈んだ天端の上に浮いた(EDO-0533 第12巡)。
        //   底は従来どおり既定の版の深さで解く(SolveMizoBottom の depthMin)── 変わるのは沈む所の駒が深い版になり天端が地面へ戻ることだけ。
        var depthOf = new Dictionary<string, float>();
        Func<string, float, string> mizoPathVar = (k, depth) =>
        {
            if (!(k == "A" || k == "C" || k == "D")) return mizoPath(k, depth);
            float dmin = kf(k, "depthMin"), dmax = kf(k, "depthMax");
            if (float.IsNaN(dmin) || float.IsNaN(dmax)) return mizoPath(k, depth);
            string shallow = null;
            for (float d = dmax; d >= dmin - 1e-4f; d -= 0.05f)
            {
                string pth = EdoBuild.AssetByName("Own", "DoiMizo", k, (float)Math.Round(d, 2));
                if (pth == null || !Exists(pth)) continue;
                float dep; if (!depthOf.TryGetValue(pth, out dep)) { var mpk = EdoBuild.MizoPieceOf(pth); dep = mpk.ok ? mpk.Depth : float.NaN; depthOf[pth] = dep; }
                if (float.IsNaN(dep)) continue;
                shallow = pth;
                if (dep <= depth + 0.005f) return pth;
            }
            return shallow ?? mizoPath(k, depth);
        };

        // ---- 系統と区間を集める
        var segs = new List<MzSeg>(); var byId = new Dictionary<string, MzSeg>(); var masus = new Dictionary<string, MzMasu>();
        for (int di = 0; di < drains.Count; di++)
        {
            var dr = O(drains[di]); string dn = (Sk(dr, "name") ?? "").Split(' ')[0];
            AuditKeys(dr, "排水 " + dn, "name", "kind", "from", "route", "slope", "outlet", "hard", "soft", "acc", "segs", "masu", "cross", "toriai", "outletBuild",
                      "levels", "hardAdd", "softAdd", "src", "lids", "doryu", "note", "rule", "meyasu", "kenbunNote", "segMasu");
            var sl = A(Gk(dr, "segs")) ?? new List<object>();
            for (int si = 0; si < sl.Count; si++)
            {
                var s = O(sl[si]);
                var g = new MzSeg { id = dn + " seg" + (si + 1), drain = dn, di = di, si = si, raw = s, dr = dr, kata = Sk(s, "kata"), line = Sk(s, "line") ?? "", flow = Sk(s, "flow") ?? "", to = Sk(s, "to") ?? "" };
                segs.Add(g); byId[g.id] = g;
            }
            var ml = A(Gk(dr, "masu")) ?? new List<object>();
            for (int k = 0; k < ml.Count; k++) { var m = O(ml[k]); masus[dn + " masu[" + k + "]"] = new MzMasu { id = dn + " masu[" + k + "]", raw = m, di = di, k = k, then = Sk(m, "then") }; }
        }
        // 欄 segMasu(区間に足す桝と、その先の埋樋の受け ── D2 seg1・2026-10-06)── 区間 "segN" の欄を引く/「→ segM」の受ける区間
        Func<MzSeg, Dictionary<string, object>> segMasuOf = g =>
        {
            foreach (var o in A(Gk(g.dr, "segMasu")) ?? new List<object>()) { var m = O(o); if (m != null && (Sk(m, "seg") ?? "").Trim() == "seg" + (g.si + 1)) return m; }
            return null;
        };
        Func<MzSeg, MzSeg> segMasuRecv = g =>
        {
            var m = segMasuOf(g); if (m == null) return null;
            var mm = Regex.Match(Sk(m, "then") ?? "", @"→\s*(?:(D\d+)\s*)?seg(\d+)"); if (!mm.Success) return null;
            string id = (mm.Groups[1].Success && mm.Groups[1].Value.Length > 0 ? mm.Groups[1].Value : g.drain) + " seg" + mm.Groups[2].Value;
            return byId.ContainsKey(id) ? byId[id] : null;
        };
        // 欄 masuAt「軒の矩形の出隅」の出隅 = 区間の線の言い方に名の出る棟の軒の矩形の四隅(「…を除く」の棟は外す)
        Func<MzSeg, List<Vector2>> eaveCorners = g =>
        {
            string ln = Regex.Replace(g.line, @"──\s*[^・]*?を除く", "");
            var l = new List<Vector2>();
            foreach (var kv in eave) if (Regex.IsMatch(ln, @"(?<![A-Za-z0-9_])" + Regex.Escape(kv.Key) + @"(?![A-Za-z0-9_])")) l.AddRange(kv.Value);
            return l;
        };
        // 'to' の言い方 → 受ける側(区間・桝・系統)
        Func<MzSeg, List<MzSeg>> receivers = g =>
        {
            var r = new List<MzSeg>();
            if (Has(g.raw, "masuPitchMaxM")) return r;   // 桝で割る区間は自分の桝へ尻を入れる(欄 to「… seg4 へは入れない」を受けと読まない)── 桝から先は segMasu の埋樋
            foreach (Match mm in Regex.Matches(g.to, @"(D\d+)?\s*seg(\d+)")) { string id = (mm.Groups[1].Success && mm.Groups[1].Value.Length > 0 ? mm.Groups[1].Value : g.drain) + " seg" + mm.Groups[2].Value; if (byId.ContainsKey(id)) r.Add(byId[id]); }
            if (r.Count == 0)
                foreach (Match mm in Regex.Matches(g.to, @"\b(D\d+)\b(?!\s*masu)"))
                    foreach (var h in segs) if (h.drain == mm.Groups[1].Value) r.Add(h);
            return r;
        };
        Func<MzSeg, MzMasu> masuOf = g =>
        {
            // 「masu[k]」= 同じ系統の桝・「D11 masu[0]」= 系統をまたいで引く
            var mm = Regex.Match(g.to, @"(?:\b(D\d+)\s*)?masu\[(\d+)\]"); if (!mm.Success) return null;
            string id = (mm.Groups[1].Success && mm.Groups[1].Value.Length > 0 ? mm.Groups[1].Value : g.drain) + " masu[" + mm.Groups[2].Value + "]"; return masus.ContainsKey(id) ? masus[id] : null;
        };
        // ---- 線の相手を名で引く(N1〜N10 の照合に使う引き当て ── 置き方・測り方は EdoBuild)
        string why = null;
        Func<MzSeg, List<List<Vector2>>> resolve = null, lineOf = null;
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        // 「E13_N01〜E13_N08」「E14_N1・E15_N1」→ 名の列(〜 は番号の桁を保つ)
        Func<string, List<string>> expandNames = str =>
        {
            var res = new List<string>();
            foreach (var tk0 in str.Split('・'))
            {
                string tk = tk0.Trim(); if (tk.Length == 0) continue;
                var rg = Regex.Match(tk, @"^([A-Za-z0-9_]*?)(\d+)\s*〜\s*([A-Za-z0-9_]*?)(\d+)$");
                if (rg.Success)
                {
                    string pf = rg.Groups[1].Value; int a = int.Parse(rg.Groups[2].Value), b = int.Parse(rg.Groups[4].Value);
                    if (rg.Groups[3].Value.Length > 0 && rg.Groups[3].Value != pf) return null;
                    for (int i = Mathf.Min(a, b); i <= Mathf.Max(a, b); i++) res.Add(pf + i.ToString().PadLeft(rg.Groups[2].Value.Length, '0'));
                    continue;
                }
                if (!Regex.IsMatch(tk, @"^[A-Za-z][A-Za-z0-9_]*$")) return null;
                res.Add(tk);
            }
            return res.Count > 0 ? res : null;
        };
        Func<string, Transform> runObj = nm => FindDeep(Group("Kakoi"), nm) ?? FindDeep(Group("Mon"), nm);
        Func<string, List<GameObject>> runPieces = nm => { var l = piecesByPrefix(nm, Group("Kakoi")); if (l.Count == 0) l = piecesByPrefix(nm, Group("Mon")); return l; };
        Func<string, int> runEdge = nm => { foreach (var o in A(D["runs"]) ?? new List<object>()) { var r = O(o); if (Sk(r, "name") == nm && Has(r, "edge")) return (int)F(r["edge"]); } return -1; };
        // 坂の帯(芯の折れ線 pts + 幅 w[m])・矩形の坂(u0..v1)は多角形だけ
        Func<string, bool, EdoBuild.Band> rampBand = (nm, withGround) =>
        {
            foreach (var o in A(D["ramps"]) ?? new List<object>())
            {
                var r = O(o); if (Sk(r, "name") != nm) continue;
                if (Has(r, "pts") && Has(r, "w"))
                {
                    var cl = new List<Vector2>(); foreach (var q in A(Gk(r, "pts"))) { var qq = A(q); cl.Add(f.W(F(qq[0]), F(qq[1]))); }
                    if (cl.Count < 2) return null;
                    return EdoBuild.BandOf(cl, 0.5f * F(r["w"]), withGround ? (Func<float, float, float>)GroundY : null);
                }
                if (Has(r, "u0"))
                {
                    float u0 = F(r["u0"]), u1 = F(r["u1"]), v0 = F(r["v0"]), v1 = F(r["v1"]);
                    return new EdoBuild.Band { poly = new[] { f.W(u0, v0), f.W(u1, v0), f.W(u1, v1), f.W(u0, v1) }, why = "矩形の坂(芯の線が無い)" };
                }
            }
            return null;
        };
        // 相手の多角形: 棟 = 軒の矩形・面/庭 = 欄の多角形・坂 = 帯
        Func<string, Vector2[]> targetPoly = nm =>
        {
            if (eave.ContainsKey(nm)) return eave[nm];
            var pp = poly(nm); if (pp != null) return pp;
            var bb = rampBand(nm, false); return bb != null ? bb.poly : null;
        };
        // 辺の番号の振り方の確かめ(区画と指図 edges の長さ)
        Func<int, string> edgeChk = ei =>
        {
            var P = Poly; if (ei < 0 || ei >= P.Length) return "辺" + ei + " が区画に無い";
            var eds = A(D["edges"]); float elen = eds != null && ei < eds.Count && Has(O(eds[ei]), "len") ? F(O(eds[ei])["len"]) : float.NaN;
            float have = Vector2.Distance(P[ei], P[(ei + 1) % P.Length]);
            if (float.IsNaN(elen) || Mathf.Abs(have - elen) > 0.5f) return "辺" + ei + " の長さが区画と指図 edges で食い違う(" + have.ToString("F2") + " / " + elen + ")── 辺の番号の振り方が確かめられない";
            return null;
        };
        // 溝の駒の半幅(実測)── 「背の縁」から芯へ寄せる量
        Func<MzSeg, float> halfWOf = g => { var mp = EdoBuild.MizoPieceOf(mizoPath(g.kata, kf(g.kata, "depthMin"))); return mp.ok ? mp.halfW : float.NaN; };
        Func<string, MzSeg> segById = id => { id = Regex.Replace(id.Trim(), @"\s+", " "); return byId.ContainsKey(id) ? byId[id] : null; };

        // ---- 桝の置き場を面の取り合いで先に解く(欄 at「<棟>と<棟>の間の坪の中心線を<相手>側へ延ばした線の上。桝の棟側の外面は、<棟>・<棟> の軒の矩形の<相手>側の辺から外へ d。
        //      桝の辺は軒の矩形に平行」)── 入る区間の線はこの桝の面の中央で止める(欄 segs の「… masu[k] の X 側の面の中央」)。置く・測るは EdoBuild.MasuPlanOffLine。
        //      ⛔ 入る溝の尻の平均で置かない(EDO-0533 第10巡: 尻の平均に置いた桝が書院の軒先の外周に掛かった)
        var masuPlan = new Dictionary<string, EdoBuild.MasuPlan>(); var masuPlanWhy = new Dictionary<string, string>(); var masuPlanBld = new Dictionary<string, string[]>();
        foreach (var kv in masus)
        {
            string at0 = Sk(kv.Value.raw, "at") ?? ""; if (!at0.Contains("外面は")) continue;
            string at = Regex.Replace(at0, @"[((][^))]*[))]", "");
            string pw = null; EdoBuild.MasuPlan pl = null;
            var mm = Regex.Match(at, @"^(.+?)と(.+?)の間の坪の中心線を(.+?)側へ延ばした線の上。\s*桝の棟側の外面は、?\s*([A-Za-z][A-Za-z0-9_]*)\s*・\s*([A-Za-z][A-Za-z0-9_]*)\s*の軒の矩形の(.+?)側の辺\s*から外へ\s*([0-9.]+)\s*m?\s*。");
            if (!mm.Success) pw = "欄 at の言い方が読めない(「<棟>と<棟>の間の坪の中心線を<相手>側へ延ばした線の上。桝の棟側の外面は、<棟>・<棟> の軒の矩形の<相手>側の辺から外へ d。」)";
            else if (!at.Contains("桝の辺は軒の矩形に平行")) pw = "桝の向き(「桝の辺は軒の矩形に平行」)が欄に無い";
            else if (mm.Groups[3].Value != mm.Groups[6].Value) pw = "延ばす向きの相手「" + mm.Groups[3].Value + "」と軒の辺の相手「" + mm.Groups[6].Value + "」が違う";
            else
            {
                var a = bldNames(mm.Groups[1].Value); var b = bldNames(mm.Groups[2].Value); string r1 = mm.Groups[4].Value, r2 = mm.Groups[5].Value;
                string tgt = sideTarget(mm.Groups[3].Value); string kt = Sk(kv.Value.raw, "kata"); string mpath = EdoBuild.AssetByName("Own", "DoiMasu", kt);
                if (a == null || b == null || a.Count != 1 || b.Count != 1 || !eave.ContainsKey(a[0]) || !eave.ContainsKey(b[0])) pw = "坪の両側の棟が引けない・建っていない";
                else if (!eave.ContainsKey(r1) || !eave.ContainsKey(r2)) pw = "軒の矩形の棟 " + r1 + "・" + r2 + " が建っていない(軒先が測れない)";
                else if (tgt == null) pw = "「" + mm.Groups[3].Value + "側」の相手(面・庭)が引けない";
                else if (mpath == null || !Exists(mpath)) pw = "桝の駒 Own.DoiMasu(\"" + kt + "\") が無い";
                else
                {
                    string w1, w2; float gap;
                    var s1 = EdoBuild.SideFacing(eave[r1], poly(tgt), blockersBut(r1), out w1);
                    var s2 = EdoBuild.SideFacing(eave[r2], poly(tgt), blockersBut(r2), out w2);
                    var ml = EdoBuild.MidlineBetween(eave[a[0]], eave[b[0]], out gap);
                    if (s1 == null) pw = r1 + " の" + mm.Groups[6].Value + "側の辺: " + w1;
                    else if (s2 == null) pw = r2 + " の" + mm.Groups[6].Value + "側の辺: " + w2;
                    else if (ml == null) pw = "坪の両側の軒先が向き合わない";
                    else
                    {
                        pl = EdoBuild.MasuPlanOffLine(mpath, s1, s2, 0.5f * (eave[r1][0] + eave[r1][2]), ml, float.Parse(mm.Groups[7].Value, ci));
                        if (!pl.ok) { pw = pl.why; pl = null; }
                        else masuPlanBld[kv.Key] = new[] { a[0], b[0] };
                    }
                }
            }
            if (pl != null) masuPlan[kv.Key] = pl; else masuPlanWhy[kv.Key] = pw;
        }
        // 「桝の X 側の面の中央」── 棟 = 棟側の面・相手(面・庭)= 外の面・棟の名 = その棟の軒の矩形の芯に近い側面。null = 引けない
        Func<string, string, Vector2?> masuFace = (mid, word) =>
        {
            EdoBuild.MasuPlan pl; if (!masuPlan.TryGetValue(mid, out pl)) return null;
            word = word.Trim();
            if (word == "棟") return pl.faceIn;
            var bn = bldNames(word);
            if (bn != null && bn.Count == 1 && eave.ContainsKey(bn[0]))
            {
                var cc = 0.5f * (eave[bn[0]][0] + eave[bn[0]][2]);
                return (pl.faceXmin - cc).sqrMagnitude < (pl.faceXmax - cc).sqrMagnitude ? pl.faceXmin : pl.faceXmax;
            }
            if (sideTarget(word) != null) return pl.faceOut;
            return null;
        };
        Func<Match, int, int, MzSeg, string> masuIdOf = (mm2, gD, gK, g0) => (mm2.Groups[gD].Success && mm2.Groups[gD].Value.Length > 0 ? mm2.Groups[gD].Value : g0.drain) + " masu[" + mm2.Groups[gK].Value + "]";
        Func<string, string> planWhy = mid => masuPlanWhy.ContainsKey(mid) ? masuPlanWhy[mid] : "欄 at が面の取り合いの言い方でない";

        // ---- 向き(上流 → 下流)── 受ける側の線・桝が解けていればそこへ、無ければ地盤の低い方へ
        // 受ける側の線(建っていれば建てた線・まだなら解いた線)と、同じ桝へ入る他の区間の線 ── 尻はこれらへ最も近い端
        Func<MzSeg, List<List<Vector2>>> targetLines = g =>
        {
            var l = new List<List<Vector2>>();
            foreach (var r in receivers(g)) { if (r.built && r.lines != null) l.AddRange(r.lines); else { var rl = lineOf(r); if (rl != null) l.AddRange(rl); } }
            { var ur = segMasuRecv(g); if (ur != null) { var rl = ur.built && ur.lines != null ? ur.lines : lineOf(ur); if (rl != null) l.AddRange(rl); } }   // 桝で割る区間の尻は埋樋の受けの側へ
            var mg = masuOf(g);
            if (mg != null) foreach (var h in segs) if (h != g && masuOf(h) == mg) { var hl = lineOf(h); if (hl != null) l.AddRange(hl); }
            return l;
        };
        Func<List<List<Vector2>>, Vector2, float> distTo = (ls, q) => { float best = float.MaxValue; foreach (var l in ls) { float dd; EdoBuild.NearestS(l, q, out dd); best = Mathf.Min(best, dd); } return best; };
        Func<List<Vector2>, List<List<Vector2>>, bool, List<List<Vector2>>> orient = (pl, tls, split2) =>
        {
            bool hasT = tls != null && tls.Count > 0;
            var outL = new List<List<Vector2>>();
            bool closed = pl.Count > 3 && (pl[0] - pl[pl.Count - 1]).sqrMagnitude < 1e-6f;
            if (closed)
            {
                // 輪 = 落とし口の隅(受ける側に最も近い隅・無ければ地盤の最も低い隅)へ両回りで下ろす
                int n = pl.Count - 1, k = 0; float best = float.MaxValue;
                for (int i = 0; i < n; i++) { float sc = hasT ? distTo(tls, pl[i]) : GroundY(pl[i].x, pl[i].y); if (sc < best) { best = sc; k = i; } }
                int opp = (k + n / 2) % n;
                var a = new List<Vector2>(); for (int i = opp; ; i = (i + 1) % n) { a.Add(pl[i]); if (i == k) break; }
                var b = new List<Vector2>(); for (int i = opp; ; i = (i - 1 + n) % n) { b.Add(pl[i]); if (i == k) break; }
                outL.Add(a); outL.Add(b); return outL;
            }
            if (split2)
            {
                // 二手 = 地盤の最も高い所で割り、両方へ下ろす
                float L = EdoBuild.PolylineLength(pl), sMax = 0f, gMax = float.MinValue;
                for (float s = 0f; s <= L; s += 0.5f) { Vector2 d; var q = EdoBuild.PointAt(pl, s, out d); float gg = GroundY(q.x, q.y); if (gg > gMax) { gMax = gg; sMax = s; } }
                if (sMax > 1f && sMax < L - 1f)
                {
                    Vector2 d0; var cut = EdoBuild.PointAt(pl, sMax, out d0);
                    var a = new List<Vector2> { cut }; var b = new List<Vector2> { cut };
                    float acc = 0f; var before = new List<Vector2>(); var after = new List<Vector2>();
                    for (int i = 0; i < pl.Count; i++) { if (i > 0) acc += Vector2.Distance(pl[i - 1], pl[i]); if (acc < sMax) before.Add(pl[i]); else after.Add(pl[i]); }
                    for (int i = before.Count - 1; i >= 0; i--) a.Add(before[i]);
                    b.AddRange(after);
                    if (a.Count >= 2) outL.Add(a); if (b.Count >= 2) outL.Add(b);
                    return outL;
                }
            }
            var p0 = pl[0]; var p1 = pl[pl.Count - 1];
            bool rev = hasT ? distTo(tls, p0) < distTo(tls, p1) : GroundY(p0.x, p0.y) < GroundY(p1.x, p1.y);
            var cp = new List<Vector2>(pl); if (rev) cp.Reverse(); outL.Add(cp); return outL;
        };

        // ---- 線の言い方を解く(⛔ 座標を発明しない)
        // 区間の線を遅れて引く(N3・N6・N7・N9 は他の区間の線を相手に取る)── 循環は null(呼び手が Wait に名乗る)
        var resolving = new HashSet<MzSeg>(); var resolvedSet = new HashSet<MzSeg>();
        lineOf = h =>
        {
            if (resolvedSet.Contains(h)) return h.rawLines;
            if (resolving.Contains(h)) return null;
            resolving.Add(h); string keep = why; h.rawLines = resolve(h); h.why = why; why = keep; resolving.Remove(h); resolvedSet.Add(h);
            return h.rawLines;
        };
        // 区間の頭・尻(向きを決めた線の端)
        Func<MzSeg, bool, List<Vector2>> segEnd = (h, tail) =>
        {
            var rl = lineOf(h); if (rl == null || rl.Count == 0) return null;
            var ol = h.fixedDir ? rl[0] : orient(rl[0], targetLines(h), false)[0];
            return new List<Vector2> { tail ? ol[ol.Count - 1] : ol[0] };
        };
        // N9 の端: 区間の尻・頭/区間の線(垂線の足)/井戸の駒の外形/塀・長屋の内面
        Func<string, List<List<Vector2>>, MzSeg, List<List<Vector2>>> endShape = null;
        endShape = (ph, other, g) =>
        {
            ph = ph.Trim(); Match mm;
            if ((mm = Regex.Match(ph, @"^(D\d+)\s*seg(\d+)\s*の(尻|頭)$")).Success)
            {
                var h = segById(mm.Groups[1].Value + " seg" + mm.Groups[2].Value); if (h == null) { why = "区間 " + mm.Groups[1].Value + " seg" + mm.Groups[2].Value + " が指図に無い"; return null; }
                var e = segEnd(h, mm.Groups[3].Value == "尻"); if (e == null) { why = h.id + " の線が引けない(" + (h.why ?? "循環") + ")"; return null; }
                if (mm.Groups[3].Value == "尻") g.fromSeg = h;
                return new List<List<Vector2>> { e };
            }
            if ((mm = Regex.Match(ph, @"^(D\d+)\s*seg(\d+)$")).Success)
            {
                var h = segById(mm.Groups[1].Value + " seg" + mm.Groups[2].Value); if (h == null) { why = "区間 " + ph + " が指図に無い"; return null; }
                var rl = lineOf(h); if (rl == null) { why = h.id + " の線が引けない(" + (h.why ?? "循環") + ")"; return null; }
                return rl;
            }
            if ((mm = Regex.Match(ph, @"^(D\d+)\s*outletBuild$")).Success) { why = mm.Groups[1].Value + " の吐口(outletBuild)の置き場が建った物から引けない(埋樋の管底が焼かれていない)"; return null; }
            if ((mm = Regex.Match(ph, @"^井戸\s*([A-Za-z][A-Za-z0-9_]*)\s*の(流し)?$")).Success)
            {
                var w = FindDeep(Group("Fuzoku/Ido"), mm.Groups[1].Value); if (w == null) { why = "井戸 " + mm.Groups[1].Value + " が建っていない"; return null; }
                var hl = EdoBuild.HullXZ(w.gameObject); if (hl == null) { why = "井戸 " + mm.Groups[1].Value + " の外形が測れない"; return null; }
                return new List<List<Vector2>> { hl };
            }
            if ((mm = Regex.Match(ph, @"^(練塀|塀|長屋)\s*([A-Za-z][A-Za-z0-9_]*)\s*の内面$")).Success)
            {
                string wn = mm.Groups[2].Value; var pcs = runPieces(wn); int e = runEdge(wn);
                if (pcs.Count == 0) { why = mm.Groups[1].Value + " " + wn + " が建っていない"; return null; }
                if (e < 0) { why = wn + " の辺が欄 runs に無い ── 内の側が決まらない"; return null; }
                var c = EdoBuild.RB(pcs[0]).center; Vector2 nrm; string w2;
                var face = EdoBuild.FaceStraight(pcs, new Vector2(c.x, c.z) - OutNormal(e) * 5f, 0.1f, 1.2f, out nrm, out w2);
                if (face == null) { why = wn + " の内面が測れない(" + w2 + ")"; return null; }
                return new List<List<Vector2>> { face };
            }
            why = "最短の端「" + ph + "」を建った物へ解けない(区間の尻・頭/区間の線/井戸の外形/塀・長屋の内面のどれでもない)"; return null;
        };

        resolve = g =>
        {
            why = null; string ln = g.line; var res = new List<List<Vector2>>();
            if (g.kata == "terrain") { why = "地形で作る浅い窪み(部材なし)── このステージでは建てない(造成の欄で起こす)"; return null; }
            g.fixedDir = false;
            // 型 P(軒樋)・M(吐口)は部材と置き場がまだ無い ── 待つ。型 J(受け)は桝を据えた後に置き場を選ぶ(下の「受け」の段)
            if (g.kata == "P" || g.kata == "M")
            { why = "型 " + g.kata + " の線「" + ln + "」── 部材と置き場がまだ無い(" + (g.kata == "P" ? "軒樋は型が考証待ちで焼いていない" : "吐口の置き場が引けない") + ")"; return null; }
            if (g.kata == "J") { why = "受け(型 J)は桝を据えた後に置き場を選ぶ"; return null; }
            string core = Regex.Replace(ln, @"[((][^))]*[))]", "").Trim();
            Match m;
            // ════ 相手の名で書いた線(普請方の設計 2026-10-04)── 照合だけ。測る・引くは EdoBuild の N1〜N10
            // 背の縁 / 芯(括弧の中の語 ── core は括弧を剥がしてある)
            bool backEdge = Regex.IsMatch(ln, @"[((]\s*背の縁");
            // ⭐ N9(「から … へ最短」)より先に照合する ── この言い方も「そこから … へ最短」を含む
            // 「<棟>の<相手>側の軒先の鉛直下 ── <坪>の側の端は、桝の X 側の面の中央から 45° に引いた線が軒先の線に当たる所で止め、そこから [Dn] masu[k] の X 側の面の中央へ最短」
            //  (EdoBuild.EaveLineToFace)── 桝は軒先の線の外にあるので、軒先の鉛直下の溝を折って桝の側面へ入れる
            { Match mm; if ((mm = Regex.Match(core, @"^(.+?)の(.+?)側の軒先の鉛直下\s*──\s*(.+?)の側の端は、?\s*桝の(.+?)側の面の中央から\s*([0-9.]+)\s*°\s*に引いた線が軒先の線に当たる所で止め、?\s*そこから\s*(?:(D\d+)\s*)?masu\[(\d+)\]\s*の(.+?)側の面の中央へ最短$")).Success)
            {
                var bn = bldNames(mm.Groups[1].Value);
                if (bn == null || bn.Count != 1 || !eave.ContainsKey(bn[0])) { why = "棟「" + mm.Groups[1].Value + "」が引けない・建っていない"; return null; }
                string tgt = sideTarget(mm.Groups[2].Value.Trim()); if (tgt == null) { why = "「" + mm.Groups[2].Value + "側」の相手(面・庭)が引けない"; return null; }
                string w2; var sd = EdoBuild.SideFacing(eave[bn[0]], poly(tgt), blockersBut(bn[0]), out w2);
                if (sd == null) { why = bn[0] + " の " + mm.Groups[2].Value + "側: " + w2; return null; }
                if (mm.Groups[4].Value.Trim() != mm.Groups[8].Value.Trim()) { why = "45° を引く面「" + mm.Groups[4].Value + "側」と最短の先の面「" + mm.Groups[8].Value + "側」が違う"; return null; }
                string mid = masuIdOf(mm, 6, 7, g); EdoBuild.MasuPlan mpl;
                if (!masuPlan.TryGetValue(mid, out mpl)) { why = "桝 " + mid + " の置き場が解けていない(" + planWhy(mid) + ")── 折れる所が決まらない"; return null; }
                var fc = masuFace(mid, mm.Groups[4].Value); if (fc == null) { why = "桝 " + mid + " の「" + mm.Groups[4].Value + "側の面」が引けない"; return null; }
                var el = EdoBuild.EaveLineToFace(sd, fc.Value, (fc.Value - mpl.center).normalized, float.Parse(mm.Groups[5].Value, ci), out w2);
                if (el == null) { why = bn[0] + " の軒先の線を " + mid + " の面へ折れない: " + w2; return null; }
                g.fixedDir = true; res.Add(el); return res;
            } }
            // N9 <始点> から <終点> へ最短
            if ((m = Regex.Match(core, @"^(.+?)\s*から\s*(.+?)\s*へ最短")).Success)
            {
                var A0 = endShape(m.Groups[1].Value, null, g); if (A0 == null) return null;
                var B0 = endShape(m.Groups[2].Value, A0, g); if (B0 == null) return null;
                float dist; var lk = EdoBuild.ShortestLink(A0, B0, out dist);
                if (lk == null || dist < 0.05f) { why = "始点と終点が重なる・測れない(" + dist.ToString("F2") + "m)"; return null; }
                g.fixedDir = true; res.Add(lk); return res;
            }
            // N7 門 <gate> の躯体の背の面から d m ── <区間> の尻から扉口の番所側の脇柱の外 d 間 まで
            if ((m = Regex.Match(core, @"^門\s*(\S+?)\s*の躯体の背の面から\s*([0-9.]+)\s*(m|間)\s*──\s*(D\d+\s*seg\d+)\s*の尻から扉口の番所側の脇柱の外\s*([0-9.]+)\s*(間|m)\s*まで")).Success)
            {
                var gdef = O(D["gate"]); Transform gt = null;
                if (gdef != null && Sk(gdef, "name") == m.Groups[1].Value) gt = Group("Mon").Find("Omotemon"); else gt = FindDeep(Group("Mon"), m.Groups[1].Value);
                if (gt == null || gdef == null) { why = "門 " + m.Groups[1].Value + " が建っていない"; return null; }
                var h = segById(m.Groups[4].Value); if (h == null) { why = m.Groups[4].Value + " が指図に無い"; return null; }
                var hl = lineOf(h); if (hl == null) { why = h.id + " の線が引けない(" + (h.why ?? "循環") + ")── 尻が決まらない"; return null; }
                // 区間の尻 = 門に最も近い端(区間はここへ下る)
                var gc3 = EdoBuild.RB(gt.gameObject).center; var gc = new Vector2(gc3.x, gc3.z); Vector2 from = hl[0][0]; float bd = float.MaxValue;
                foreach (var l in hl) foreach (var q in new[] { l[0], l[l.Count - 1] }) { float dd = Vector2.Distance(q, gc); if (dd < bd) { bd = dd; from = q; } }
                float leafW = Has(O(gdef["plan"]), "leaf") ? F(O(O(gdef["plan"])["leaf"])["w"]) : float.NaN;
                Vector2 jamb, outw; string w2;
                if (!EdoBuild.GateDoorJambBansho(gt.gameObject, leafW, out jamb, out outw, out w2)) { why = "門の扉口: " + w2; return null; }
                float dj = float.Parse(m.Groups[5].Value, ci) * (m.Groups[6].Value == "間" ? ken : 1f);
                float off = float.Parse(m.Groups[2].Value, ci) * (m.Groups[3].Value == "間" ? ken : 1f);
                if (backEdge) { float hw = halfWOf(g); if (float.IsNaN(hw)) { why = "溝の駒の幅が測れない ── 背の縁から芯へ寄せられない"; return null; } off += hw; }
                float ext; var gl = EdoBuild.GateBackLine(gt.gameObject, -OutNormal((int)F(gdef["edge"])), off, from, jamb + outw * dj, 3f, out ext, out w2);
                if (gl == null) { why = "門の背の線: " + w2; return null; }
                if (ext > 0.01f) Wait(g.id + ": 門の背の面を端から " + ext.ToString("F2") + "m 延ばして " + h.id + " の尻へ届かせた(柔 ⚠)");
                g.fixedDir = true; res.Add(gl); return res;
            }
            // N6 坂 <ramp> の足(帯の高さが面 <id> を離れる点)を帯に直交に横切る ── 高い側は <区間> の線まで・低い側は帯の縁まで
            if ((m = Regex.Match(core, @"^坂\s*(R_[A-Za-z0-9_]+)\s*の足を帯に直交に横切る\s*──\s*高い側は\s*(D\d+\s*seg\d+)\s*の線まで・低い側は帯の縁まで")).Success)
            {
                var mf = Regex.Match(ln, @"面\s*([A-Za-z][A-Za-z0-9_]*)\s*を離れる点"); if (!mf.Success) { why = "坂の足の面の名が無い"; return null; }
                float fy = float.NaN; foreach (var o in A(D["terraces"]) ?? new List<object>()) { var t = O(o); if (Sk(t, "name") == mf.Groups[1].Value && Has(t, "y")) fy = F(t["y"]); }
                if (float.IsNaN(fy)) { why = "面 " + mf.Groups[1].Value + " の高さが欄に無い"; return null; }
                var bd = rampBand(m.Groups[1].Value, true); if (bd == null || bd.center == null) { why = "坂 " + m.Groups[1].Value + " の帯(芯の線と幅)が欄に無い"; return null; }
                var h = segById(m.Groups[2].Value); if (h == null) { why = m.Groups[2].Value + " が指図に無い"; return null; }
                var hl = lineOf(h); if (hl == null) { why = h.id + " の線が引けない(" + (h.why ?? "循環") + ")── 高い側の端が決まらない"; return null; }
                string w2; var xl = EdoBuild.BandFootCross(bd, GroundY, fy, 0.02f, hl, 30f, out w2);
                if (xl == null) { why = "坂の足の横断: " + w2; return null; }
                res.Add(xl); return res;
            }
            // N5 坂 <ramp> の帯の縁のうち地盤の高い側 ── 頭から <物> の端まで
            if ((m = Regex.Match(core, @"^坂\s*(R_[A-Za-z0-9_]+)\s*の帯の縁のうち地盤の高い側\s*──\s*頭から\s*(?:石垣|土留め)?\s*([A-Za-z][A-Za-z0-9_]*)\s*の端まで")).Success)
            {
                var bd = rampBand(m.Groups[1].Value, true); if (bd == null || bd.center == null) { why = "坂 " + m.Groups[1].Value + " の帯(芯の線と幅)が欄に無い"; return null; }
                string wn = m.Groups[2].Value; var pcs = piecesByPrefix(wn, Group("Dodome")); if (pcs.Count == 0) pcs = piecesByPrefix(wn, Group("Ishigaki"));
                if (pcs.Count == 0) { why = wn + " の駒が建っていない ── 区間の端が決まらない"; return null; }
                string w2; var el = EdoBuild.BandHighEdgeToPieces(bd, pcs, out w2);
                if (el == null) { why = "坂の高い側の縁: " + w2; return null; }
                g.fixedDir = true; res.Add(el); return res;
            }
            // N8 長屋 <run>… の内面から d(間|m)(芯|背の縁)[── <run> の側の端は長屋 <run> の内面まで延ばして止める]
            if ((m = Regex.Match(core, @"^長屋\s*(.+?)\s*の内面から\s*([0-9.]+)\s*(間|m)")).Success)
            {
                var nms = expandNames(m.Groups[1].Value); if (nms == null) { why = "長屋の名の列「" + m.Groups[1].Value + "」が読めない"; return null; }
                float off = float.Parse(m.Groups[2].Value, ci) * (m.Groups[3].Value == "間" ? ken : 1f);
                if (backEdge) { float hw = halfWOf(g); if (float.IsNaN(hw)) { why = "溝の駒の幅が測れない ── 背の縁から芯へ寄せられない"; return null; } off += hw; }
                Func<string, List<Vector2>> faceOf = nm =>
                {
                    var pcs = runPieces(nm); int e = runEdge(nm);
                    if (pcs.Count == 0) { why = "長屋 " + nm + " が建っていない"; return null; }
                    if (e < 0) { why = nm + " の辺が欄 runs に無い ── 内の側が決まらない"; return null; }
                    var c = EdoBuild.RB(pcs[0]).center; Vector2 nrm; string w2;
                    var fc = EdoBuild.FaceStraight(pcs, new Vector2(c.x, c.z) - OutNormal(e) * 5f, 0.1f, 1.2f, out nrm, out w2);
                    if (fc == null) { why = "長屋 " + nm + " の内面が測れない(" + w2 + ")"; return null; }
                    return new List<Vector2> { fc[0] + nrm * off, fc[1] + nrm * off, fc[0], fc[1] };   // [0..1] = ずらした線・[2..3] = 面
                };
                var parts2 = new List<List<Vector2>>(); var faces = new Dictionary<string, List<Vector2>>();
                foreach (var nm in nms) { var fo = faceOf(nm); if (fo == null) return null; faces[nm] = fo; parts2.Add(new List<Vector2> { fo[0], fo[1] }); }
                var chain = EdoBuild.ChainStraights(parts2, 20f);
                var mx = Regex.Match(core, @"──\s*([A-Za-z][A-Za-z0-9_]*)\s*の側の端は長屋\s*([A-Za-z][A-Za-z0-9_]*)\s*の内面まで延ばして止める");
                if (mx.Success)
                {
                    if (!faces.ContainsKey(mx.Groups[1].Value)) { why = "延ばす端の長屋 " + mx.Groups[1].Value + " が列に無い"; return null; }
                    var fo2 = faceOf(mx.Groups[2].Value); if (fo2 == null) return null;
                    var nearF = faces[mx.Groups[1].Value]; float ext;
                    if (!EdoBuild.ExtendEndTo(chain, 0.5f * (nearF[2] + nearF[3]), new List<List<Vector2>> { new List<Vector2> { fo2[2], fo2[3] } }, true, 30f, out ext))
                    { why = "端を延ばしても長屋 " + mx.Groups[2].Value + " の内面に 30m 内で当たらない"; return null; }
                }
                else if (core.Contains("──")) { why = "「──」の後の言い方「" + core.Substring(core.IndexOf("──")) + "」が読めない"; return null; }
                res.Add(chain); return res;
            }
            // N4 長屋 <run>… の内の軒先の鉛直下
            if ((m = Regex.Match(core, @"^長屋\s*(.+?)\s*の内の軒先の鉛直下$")).Success)
            {
                var nms = expandNames(m.Groups[1].Value); if (nms == null) { why = "長屋の名の列「" + m.Groups[1].Value + "」が読めない"; return null; }
                var parts2 = new List<List<Vector2>>();
                foreach (var nm in nms)
                {
                    var tr = runObj(nm); int e = runEdge(nm);
                    if (tr == null) { why = "長屋 " + nm + " が建っていない(軒先が測れない)"; return null; }
                    if (e < 0) { why = nm + " の辺が欄 runs に無い"; return null; }
                    Vector2[] rect; float ey; string how;
                    if (!EdoBuild.EaveRect(tr, EdgeDir(e), out rect, out ey, out how)) { why = "長屋 " + nm + " の軒先: " + how; return null; }
                    if (how != "屋根の実メッシュ") Wait("軒先の外周 " + nm + ": " + how);
                    parts2.Add(EdoBuild.EaveSideAwayFromLine(rect, EdgePt(e, 0f), EdgePt(e, EdgeLen(e))));
                }
                res.Add(EdoBuild.ChainStraights(parts2, 20f)); return res;
            }
            // N3 面 <id> の縁のうち <相手> に向く一続きから(内|外)へ d(間|m)[・<区間> まで延ばす]
            if ((m = Regex.Match(core, @"^面\s*([A-Za-z][A-Za-z0-9_]*)\s*の縁のうち\s*([A-Za-z][A-Za-z0-9_]*)\s*に向く一続きから(内|外)へ\s*([0-9.]+)\s*(間|m)")).Success)
            {
                var fp = poly(m.Groups[1].Value); if (fp == null) { why = "面 " + m.Groups[1].Value + " の多角形が欄に無い"; return null; }
                var tp = targetPoly(m.Groups[2].Value); if (tp == null) { why = "相手 " + m.Groups[2].Value + " が引けない(棟・面・庭・坂のどれでもない/建っていない)"; return null; }
                Vector2 outw; string w2; var ch = EdoBuild.PolyEdgesFacingTarget(fp, tp, 0.7f, out outw, out w2);
                if (ch == null) { why = "面 " + m.Groups[1].Value + " の " + m.Groups[2].Value + " に向く縁: " + w2; return null; }
                float off = float.Parse(m.Groups[4].Value, ci) * (m.Groups[5].Value == "間" ? ken : 1f);
                if (backEdge) { float hw = halfWOf(g); if (float.IsNaN(hw)) { why = "溝の駒の幅が測れない ── 背の縁から芯へ寄せられない"; return null; } off += hw; }
                var ol = EdoBuild.OffsetPolyline(ch, off, m.Groups[3].Value == "内" ? -outw : outw);
                var mx = Regex.Match(core.Substring(m.Length), @"^\s*・\s*(D\d+\s*seg\d+)\s*まで延ばす\s*$");
                if (mx.Success)
                {
                    var h = segById(mx.Groups[1].Value); if (h == null) { why = mx.Groups[1].Value + " が指図に無い"; return null; }
                    var hl = lineOf(h); if (hl == null) { why = h.id + " の線が引けない(" + (h.why ?? "循環") + ")── 延ばす先が無い"; return null; }
                    float d0 = float.MaxValue, d1 = float.MaxValue; foreach (var l in hl) { float dd; EdoBuild.NearestS(l, ol[0], out dd); d0 = Mathf.Min(d0, dd); EdoBuild.NearestS(l, ol[ol.Count - 1], out dd); d1 = Mathf.Min(d1, dd); }
                    float ext;
                    if (!EdoBuild.ExtendEndTo(ol, d0 < d1 ? ol[0] : ol[ol.Count - 1], hl, false, 30f, out ext)) { why = "端を延ばしても " + h.id + " の線に 30m 内で当たらない"; return null; }
                }
                else if (core.Substring(m.Length).Trim().Length > 0) { why = "後ろの言い方「" + core.Substring(m.Length).Trim() + "」が読めない"; return null; }
                res.Add(ol); return res;
            }
            // N1 <棟>・<棟> の軒の外周 ── <棟>と<棟> の軒の下を除く(残りの部は下の軒先の部で解く)
            string rest = core;
            {
                var mu = Regex.Match(core, @"^([A-Za-z][A-Za-z0-9_]*(?:\s*・\s*[A-Za-z][A-Za-z0-9_]*)*)\s*の軒の外周(?:\s*──\s*([A-Za-z][A-Za-z0-9_]*(?:\s*(?:・|と)\s*[A-Za-z][A-Za-z0-9_]*)*)\s*の軒の下を除く)?");
                if (mu.Success)
                {
                    var rs = new List<Vector2[]>(); var xs = new List<Vector2[]>();
                    foreach (Match t in Regex.Matches(mu.Groups[1].Value, @"[A-Za-z][A-Za-z0-9_]*")) { if (!eave.ContainsKey(t.Value)) { why = "棟 " + t.Value + " が建っていない(軒先が測れない)"; return null; } rs.Add(eave[t.Value]); }
                    foreach (Match t in Regex.Matches(mu.Groups[2].Value, @"[A-Za-z][A-Za-z0-9_]*")) { if (!eave.ContainsKey(t.Value)) { why = "除く棟 " + t.Value + " が建っていない(軒先が測れない)"; return null; } xs.Add(eave[t.Value]); }
                    string w2; var ou = EdoBuild.EaveUnionOutline(rs, xs, uW, out w2);
                    if (ou == null) { why = "軒の外周: " + w2; return null; }
                    res.AddRange(ou);
                    rest = core.Substring(mu.Length).TrimStart('・', ' ');
                    if (rest.Length == 0) return res;
                }
            }
            // 棟間の中心線(路地)── 欄 from.service の並び順で隣り合う二棟の軒先の向き合う辺の中心
            if (core.StartsWith("棟間の中心線"))
            {
                var fr = O(g.dr["from"]); var sv = fr != null ? A(Gk(fr, "service")) : null;
                if (sv == null || sv.Count < 2) { why = "棟間の相手が欄 from.service に無い"; return null; }
                for (int i = 0; i + 1 < sv.Count; i++)
                {
                    string a = S(sv[i]), b = S(sv[i + 1]);
                    if (!eave.ContainsKey(a) || !eave.ContainsKey(b)) { why = "棟 " + a + " / " + b + " が建っていない"; return null; }
                    float gap; var ml = EdoBuild.MidlineBetween(eave[a], eave[b], out gap);
                    if (ml == null) { why = a + " と " + b + " の軒先が向き合わない"; return null; }
                    res.Add(ml);
                }
                return res;
            }
            if ((m = Regex.Match(core, @"^(.+?)と(.+?)の間の坪の中心線")).Success)
            {
                var a = bldNames(m.Groups[1].Value); var b = bldNames(m.Groups[2].Value);
                if (a == null || b == null || a.Count != 1 || b.Count != 1 || !eave.ContainsKey(a[0]) || !eave.ContainsKey(b[0])) { why = "坪の両側の棟が引けない・建っていない"; return null; }
                float gap; var ml = EdoBuild.MidlineBetween(eave[a[0]], eave[b[0]], out gap);
                if (ml == null) { why = "坪の両側の軒先が向き合わない"; return null; }
                // 「── <相手>側の端は [Dn] masu[k] の X 側の面の中央まで延ばす」(EdoBuild.LineEndAt)
                var mxe = Regex.Match(core.Substring(m.Length), @"^\s*──\s*(.+?)側の端は\s*(?:(D\d+)\s*)?masu\[(\d+)\]\s*の(.+?)側の面の中央まで延ばす\s*$");
                if (mxe.Success)
                {
                    string mid = masuIdOf(mxe, 2, 3, g);
                    if (!masuPlan.ContainsKey(mid)) { why = "桝 " + mid + " の置き場が解けていない(" + planWhy(mid) + ")── 延ばす先が無い"; return null; }
                    var fc = masuFace(mid, mxe.Groups[4].Value); if (fc == null) { why = "桝 " + mid + " の「" + mxe.Groups[4].Value + "側の面」が引けない"; return null; }
                    string w3; var el = EdoBuild.LineEndAt(ml, fc.Value, 0.02f, out w3);
                    if (el == null) { why = "坪の中心線を " + mid + " の面の中央まで延ばせない: " + w3; return null; }
                    g.fixedDir = true; res.Add(el); return res;
                }
                if (core.Substring(m.Length).Trim().Length > 0) { why = "後ろの言い方「" + core.Substring(m.Length).Trim() + "」が読めない"; return null; }
                res.Add(ml); return res;
            }
            if ((m = Regex.Match(core, @"([A-Za-z][A-Za-z0-9_]*)\s*の内面から\s*([0-9.]+)\s*間")).Success)
            {
                string wn = m.Groups[1].Value; float off = float.Parse(m.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture) * ken;
                // 走りは駒の名の脚(<名>_<i>_…)ごと
                var legs = new List<List<GameObject>>();
                foreach (var root in new[] { Group("OkuHei"), Group("Kakoi") })
                    for (int i = 0; i < 40; i++) { var l = piecesByPrefix(wn + "_" + i, root); if (l.Count > 0) legs.Add(l); }
                if (legs.Count == 0) { why = "塀 " + wn + " の駒が建っていない"; return null; }
                var mk = Regex.Match(ln, @"(\S+?)の区域の外"); string keepOut = mk.Success ? sideTarget(mk.Groups[1].Value.Split('・').Length > 0 ? mk.Groups[1].Value.Split('・')[mk.Groups[1].Value.Split('・').Length - 1] : mk.Groups[1].Value) : null;
                var ko = keepOut != null ? poly(keepOut) : null;
                foreach (var leg in legs)
                {
                    List<Vector2> pick = null; int nOk = 0;
                    foreach (var sgn in new[] { 1f, -1f })
                    {
                        Vector2 nrm; string w2;
                        var probe = EdoBuild.WallMidLine(leg, 0.1f, 1.2f, out nrm, out w2); if (probe == null) continue;
                        var side = new Vector2(-nrm.y, nrm.x) * sgn; var mid = 0.5f * (probe[0] + probe[1]);
                        var face = EdoBuild.WallFaceLine(leg, mid + side * 5f, 0.1f, 1.2f, 0.5f, out nrm, out w2); if (face == null) continue;
                        var ol = EdoBuild.OffsetPolyline(face, off, nrm);
                        bool inside = true, outKo = true;
                        foreach (var q in ol) { if (!EdoGeom.PIP(Poly, q)) inside = false; if (ko != null && EdoGeom.PIP(ko, q)) outKo = false; }
                        if (inside && outKo) { pick = ol; nOk++; }
                    }
                    if (nOk == 1) res.Add(pick);
                }
                if (res.Count == 0) { why = "塀 " + wn + " の内面の側が決まらない(両側とも区画の内・区域の外 ── 欄に相手の区域の語が要る)"; return null; }
                return res;
            }
            if ((m = Regex.Match(core, @"(TW_[A-Za-z0-9_]+)\s*の(天端の内|根石の前)\s*([0-9.]+)\s*(間)?")).Success || (m = Regex.Match(core, @"石垣\s*(TW_[A-Za-z0-9_]+)\s*の(根石の前)()")).Success)
            {
                string wn = m.Groups[1].Value; bool crest = m.Groups[2].Value == "天端の内";
                float off = 0f;
                if (m.Groups[3].Value.Length > 0) off = float.Parse(m.Groups[3].Value, System.Globalization.CultureInfo.InvariantCulture) * (m.Groups[4].Value == "間" ? ken : 1f);
                else foreach (var o in A(Gk(g.dr, "toriai")) ?? new List<object>()) { var t = O(o); if ((Sk(t, "with") ?? "").Contains(wn) && Has(t, "offM")) off = F(t["offM"]); }
                var pcs = piecesByPrefix(wn, Group("Dodome")); if (pcs.Count == 0) pcs = piecesByPrefix(wn, Group("Ishigaki"));
                if (pcs.Count == 0) { why = "土留め・石垣 " + wn + " の駒が建っていない"; return null; }
                // 天端の側 = 足元より地盤の高い側(背)・根石の前 = 低い側(見え面)
                Vector2 nrm; string w2; var mid0 = EdoBuild.WallMidLine(pcs, 0f, 0.3f, out nrm, out w2);
                if (mid0 == null) { why = wn + ": " + w2; return null; }
                var c = 0.5f * (mid0[0] + mid0[1]); var sd = new Vector2(-nrm.y, nrm.x);
                float g1 = GroundY(c.x + sd.x * 2f, c.y + sd.y * 2f), g2 = GroundY(c.x - sd.x * 2f, c.y - sd.y * 2f);
                var back = g1 > g2 ? sd : -sd; var toward = crest ? back : -back;
                // 帯は駒ごとの天端・下端から(斜面の走りでも駒ごとに天端の帯・根石の帯を拾う)
                var face = crest ? EdoBuild.WallFaceLine(pcs, c + toward * 5f, -0.15f, 0.01f, 0.5f, out nrm, out w2, fromTop: true)
                                 : EdoBuild.WallFaceLine(pcs, c + toward * 5f, 0f, 0.3f, 0.5f, out nrm, out w2);
                if (face == null) { why = wn + ": " + w2; return null; }
                // 天端の内 N = 溝の芯(欄が芯を言う)/ 根石の前 N = 溝の背の縁 ⇒ 芯は + 半幅(駒の実測)
                float add = 0f;
                if (!crest) { string pth = mizoPath(g.kata, kf(g.kata, "depthMin")); var mp = EdoBuild.MizoPieceOf(pth); if (!mp.ok) { why = "溝の駒の幅が測れない(" + (pth ?? "名が無い") + ")── 背の縁から芯へ寄せられない"; return null; } add = mp.halfW; }
                res.Add(EdoBuild.OffsetPolyline(face, off + add, nrm)); return res;
            }
            if ((m = Regex.Match(core, @"([A-Za-z][A-Za-z0-9_]*)\s*の柱の芯から外へ\s*([0-9.]+)\s*間")).Success)
            {
                string fn = m.Groups[1].Value; float off = float.Parse(m.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture) * ken;
                bool inner = ln.Contains("内の縁"), outer = ln.Contains("外の縁");
                var legs = new List<KeyValuePair<List<Vector2>, float>>(); var allP = new List<GameObject>();
                for (int i = 0; i < 20; i++)
                {
                    var l = piecesByPrefix(fn + "_" + i, Group("Fuzoku/Saku")); if (l.Count == 0) continue; allP.AddRange(l);
                    Vector2 ax; string w2; var ml = EdoBuild.WallMidLine(l, 0.1f, 1.0f, out ax, out w2); if (ml != null) legs.Add(new KeyValuePair<List<Vector2>, float>(ml, EdoBuild.PolylineLength(ml)));
                }
                if (legs.Count < 2) { why = "柵 " + fn + " の駒が建っていない(脚が 2 本に満たない)"; return null; }
                legs.Sort((a, b) => b.Value.CompareTo(a.Value));
                var la = legs[0].Key; var lb = legs[1].Key;
                Vector2 ma = 0.5f * (la[0] + la[1]), mb = 0.5f * (lb[0] + lb[1]);
                bool aInner = Vector2.Distance(ma, parcelC) < Vector2.Distance(mb, parcelC);
                var use = inner ? (aInner ? la : lb) : outer ? (aInner ? lb : la) : null;
                if (use == null) { why = "埒の内の縁/外の縁の別が欄に無い"; return null; }
                Vector2 cen = 0.5f * (ma + mb), mu = 0.5f * (use[0] + use[1]);
                string pth = mizoPath(g.kata, kf(g.kata, "depthMin")); var mp = EdoBuild.MizoPieceOf(pth);
                if (!mp.ok) { why = "溝の駒の幅が測れない(" + (pth ?? "名が無い") + ")── 肩から芯へ寄せられない"; return null; }
                res.Add(EdoBuild.OffsetPolyline(use, off + mp.halfW, mu - cen)); g.halfW = mp.halfW; return res;
            }
            if ((m = Regex.Match(core, @"^(.+?)の辺(\d+)\s*側の縁から内へ\s*([0-9.]+)\s*間")).Success)
            {
                string tn = m.Groups[1].Value.Trim(); int ei = int.Parse(m.Groups[2].Value); float off = float.Parse(m.Groups[3].Value, System.Globalization.CultureInfo.InvariantCulture) * ken;
                var fr = O(g.dr["from"]);
                if (tn == "平場" && fr != null && fr["terrace"] is string) tn = Sk(fr, "terrace");
                var tp = poly(tn); if (tp == null) { tn = sideTarget(tn); tp = tn != null ? poly(tn) : null; }
                if (tp == null) { why = "面「" + m.Groups[1].Value + "」が引けない"; return null; }
                var P = Poly; if (ei < 0 || ei >= P.Length) { why = "辺" + ei + " が区画に無い"; return null; }
                var eds = A(D["edges"]); float elen = eds != null && ei < eds.Count && Has(O(eds[ei]), "len") ? F(O(eds[ei])["len"]) : float.NaN;
                float have = Vector2.Distance(P[ei], P[(ei + 1) % P.Length]);
                if (float.IsNaN(elen) || Mathf.Abs(have - elen) > 0.5f) { why = "辺" + ei + " の長さが区画と指図 edges で食い違う(" + have.ToString("F2") + " / " + elen + ")── 辺の番号の振り方が確かめられない"; return null; }
                var outN = -EdoGeom.InwardNormal(P, ei);
                var ch = EdoBuild.PolyEdgesToward(tp, outN, 0.8f);
                if (ch.Count != 1) { why = "面 " + tn + " の辺" + ei + " 側の縁が " + ch.Count + " 本 ── 一本に決まらない"; return null; }
                res.Add(EdoBuild.OffsetPolyline(ch[0], off, -outN)); return res;
            }
            if ((m = Regex.Match(core, @"座\s*(Za_[A-Za-z0-9_]+)\s*の縁の外")).Success)
            { why = "座 " + m.Groups[1].Value + " の「どの縁」かが方角の語でしか書かれていない(方角の語は格子と食い違う ── 縁の相手を名で書く欄が要る)"; return null; }
            if (Regex.IsMatch(core, @"(北|南|東|西)の(縁|軒先|口|端|境)") && !core.EndsWith("の軒先の鉛直下") || Regex.IsMatch(core, @"の(北|南|東|西)の軒先"))
            { why = "線「" + ln + "」が方角の語で書かれている ── この指図の方角の語は格子と食い違う(馬場の東の口 = u+・台地の南の縁 = u−)ので建った物の辺へ写せない(相手を名で書く欄が要る)"; return null; }
            // 軒先(雨落ち)── 「・」で区切った各部を全部解けたときだけ
            // ⭐ ローマ字の名の列(「Kura1・Kura2」「Hiraya_SE1・SE2」)の「・」では区切らない ── 両隣が英数字の「・」は名の列
            Func<char, bool> asc = ch => ch < 128 && (char.IsLetterOrDigit(ch) || ch == '_');
            var parts = new List<string>(); { int depth = 0, st = 0; for (int i = 0; i < rest.Length; i++) { char ch = rest[i]; if (ch == '(' || ch == '(') depth++; else if (ch == ')' || ch == ')') depth--; else if (ch == '・' && depth == 0)
                    { int a = i - 1; while (a >= 0 && rest[a] == ' ') a--; int b = i + 1; while (b < rest.Length && rest[b] == ' ') b++; if (a >= 0 && b < rest.Length && asc(rest[a]) && asc(rest[b])) continue; parts.Add(rest.Substring(st, i - st)); st = i + 1; } } parts.Add(rest.Substring(st)); }
            foreach (var p0 in parts)
            {
                string p = p0.Trim();
                if (p.StartsWith("全周")) continue;   // 「全周を座の上で回す」= 前の部の輪をそのまま使う
                Match mm;
                if ((mm = Regex.Match(p, @"^(.+?)の(.+?)側の軒先の鉛直下$")).Success || (mm = Regex.Match(p, @"^(.+?)の(.+?)側$")).Success)
                {
                    var bn = bldNames(mm.Groups[1].Value); string tw = mm.Groups[2].Value.Trim();
                    if (bn == null || bn.Count != 1) { why = "棟「" + mm.Groups[1].Value + "」が引けない"; return null; }
                    if (!eave.ContainsKey(bn[0])) { why = "棟 " + bn[0] + " が建っていない(軒先が測れない)"; return null; }
                    // N2「<棟> の <相手id> 側」── 相手は面・庭・坂の多角形/棟の軒の矩形。芯へ最も向く辺(cos ≥ 0.7)
                    if (Regex.IsMatch(tw, @"^[A-Za-z][A-Za-z0-9_]*$"))
                    {
                        var tp = targetPoly(tw); if (tp == null) { why = "相手 " + tw + " が引けない(棟・面・庭・坂のどれでもない/建っていない)"; return null; }
                        float dt; string wt; var sd2 = EdoBuild.RectSideTowardTarget(eave[bn[0]], tp, 0.7f, out dt, out wt);
                        if (sd2 == null) { why = bn[0] + " の " + tw + " 側: " + wt; return null; }
                        res.Add(sd2); continue;
                    }
                    string tgt = sideTarget(tw);
                    if (tgt == null) { why = "「" + mm.Groups[2].Value + "側」の相手(面・庭)が引けない"; return null; }
                    string w2; var sd = EdoBuild.SideFacing(eave[bn[0]], poly(tgt), blockersBut(bn[0]), out w2);
                    if (sd == null) { why = bn[0] + " の " + mm.Groups[2].Value + "側: " + w2; return null; }
                    if (!p.EndsWith("軒先の鉛直下") && ln.Contains("雨落ちの外"))
                    {
                        // 「(… の雨落ちの外)」= 軒先の線から雨落ち(A)の外幅の半分 + この溝の半幅だけ外
                        var mA = EdoBuild.MizoPieceOf(mizoPath("A", 0f)); var mS = EdoBuild.MizoPieceOf(mizoPath(g.kata, kf(g.kata, "depthMin")));
                        if (!mA.ok || !mS.ok) { why = "雨落ちの外へ寄せる幅が測れない(A・" + g.kata + " の駒)"; return null; }
                        var c = 0.5f * (eave[bn[0]][0] + eave[bn[0]][2]); var mid = 0.5f * (sd[0] + sd[1]);
                        sd = EdoBuild.OffsetPolyline(sd, mA.halfW + mS.halfW, mid - c);
                    }
                    res.Add(sd); continue;
                }
                if ((mm = Regex.Match(p, @"^(.+?)の(軒先の鉛直下|全周)$")).Success || (mm = Regex.Match(p, @"^(.+?)\s*の軒先の鉛直下$")).Success)
                {
                    var bn = bldNames(mm.Groups[1].Value);
                    if (bn == null || bn.Count == 0) { why = "棟「" + mm.Groups[1].Value + "」が引けない"; return null; }
                    foreach (var b in bn)
                    {
                        if (!eave.ContainsKey(b)) { why = "棟 " + b + " が建っていない(軒先が測れない)"; return null; }
                        // 附属屋(土蔵ほか)は軒が浅い ── 溝の内の縁石の背を躯体の足の外形から 0.05 離す(硬・EdoBuild.RectClearOfFoot・普請方の設計 2026-10-07)
                        var rc = eave[b]; var svc = FindDeep(Group("Fuzoku/Service"), b); float hwE = halfWOf(g);
                        if (svc != null && !float.IsNaN(hwE))
                        {
                            float pm; var rc2 = EdoBuild.RectClearOfFoot(rc, svc, hwE + 0.05f, out pm);
                            //   足が軒先より 0.5 を超えて外へ出る棟(基壇に載る稲荷など ── 雨は基壇に落ちる)は寄せない(第31巡: 稲荷の溝を 1.23m 寄せて玉垣 F09 の柱に掛かった)
                            if (pm > 0.5f) line(1, g.id + ": " + b + " の躯体の足(基壇)が軒先の鉛直下より " + pm.ToString("F2") + "m 外へ出る ── 溝は軒先の鉛直下のまま(寄せない)");
                            else rc = rc2;
                            if (pm > 1e-3f && pm <= 0.5f) line(1, g.id + ": " + b + " の軒先の鉛直下を躯体の足の外形 + 溝の半幅 + 0.05 まで外へ " + pm.ToString("F2") + "m 寄せた(柔: 狙いの軒先の鉛直下から外れた)");
                        }
                        res.Add(loop(rc));
                    }
                    continue;
                }
                why = "言い方「" + p + "」を建った物へ解けない"; return null;
            }
            if (res.Count == 0) { why = "言い方「" + ln + "」を建った物へ解けない"; return null; }
            return res;
        };

        // ---- 線を先に全部解く(向きを決めるのに受ける側・同じ桝の相手の線が要る)
        foreach (var g in segs) lineOf(g);

        // 上流から解く順(受ける側は入る側の後)
        var order = new List<MzSeg>(); var state = new Dictionary<MzSeg, int>();
        Action<MzSeg> visit = null;
        visit = g =>
        {
            int st; if (state.TryGetValue(g, out st)) return; state[g] = 1;
            foreach (var h in segs)
            {
                if (h == g) continue;
                if (receivers(h).Contains(g)) visit(h);
                var ms = masuOf(h); if (ms != null && ms.then != null && Regex.IsMatch(ms.then, @"seg" + (g.si + 1) + @"\b") && ms.id.StartsWith(g.drain + " ")) visit(h);
            }
            if (g.fromSeg != null) visit(g.fromSeg);   // N9 の始点の区間を先に
            state[g] = 2; order.Add(g);
        };
        foreach (var g in segs) visit(g);


        // ---- 区間ごとに解いて据える
        var solvedEnds = new List<KeyValuePair<MzSeg, Vector3>>();   // (入る区間, (尻の x, z, 尻の底))
        var splitMasus = new List<KeyValuePair<MzSeg, EdoBuild.MasuCut>>();   // 欄 masuPitchMaxM で区間に足した桝(この後 埋樋の口を引く)
        foreach (var g in order)
        {
            var s = g.raw;
            AuditKeys(s, "排水 " + g.id, "kata", "line", "flow", "to", "slope", "slopeMin", "bottom", "bottomHead", "bottomTail", "depth", "offKen", "offRef", "offM",
                      "lid", "drop", "innerW", "rule", "note", "stepPitchKen", "stepRiseMax", "stepRiseFrom", "stepPitchFrom", "stepPitchQuantumKen", "stepsMin", "stepsMax",
                      "steps", "rise", "riseFrom", "riseMax", "stepsFrom", "stepsEst", "riseEst", "treadFrom", "sizeKen", "groundToCenter", "backOffsetFromNeishiM",
                      "downpipeAt", "lenMaxKen", "swale", "edgeFall", "maxToNamedKen", "masuPitchMaxM", "masuPitchNote", "masuAt");
            if (Has(s, "innerW") && g.kata == "A")
            { line(2, g.id + "(型 A・内法 " + F(s["innerW"]).ToString("0.00") + "): 内法 0.30 の駒しか無い ── 建てない"); Wait(g.id + ": 内法 " + F(s["innerW"]).ToString("0.00") + " の雨落ちの駒が要る(部材方 ── Own.DoiMizo の内法違い)"); continue; }
            if (g.kata == "J") continue;   // 受けは桝を据えた後(下の「受け」の段)
            var raw = g.rawLines;
            if (raw == null) { line(2, g.id + "(型 " + g.kata + "「" + g.line + "」): 線が引けない ── " + g.why + " ── 建てない"); Wait(g.id + ": " + g.why); continue; }
            if (g.kata == "H") { BuildDanOchi9(g, grp, solvedEnds, receivers, masuOf, kf, line); continue; }
            string p0 = mizoPath(g.kata, kf(g.kata, "depthMin"));
            if (p0 == null || !Exists(p0)) { line(2, g.id + "(型 " + g.kata + "): 部材が無い " + (p0 ?? "Own.DoiMizo(\"" + g.kata + "\") が未登録") + " ── 建てない"); Wait(g.id + ": 溝の駒 " + (p0 ?? "Own.DoiMizo(\"" + g.kata + "\")") + " が無い(部材方)"); continue; }
            var mp0 = EdoBuild.MizoPieceOf(p0);
            if (!mp0.ok) { line(2, g.id + ": 駒の溝の底が測れない " + p0); continue; }
            g.halfW = mp0.halfW;
            bool fixedD = !(g.kata == "E" || g.kata == "F" || g.kata == "A" || g.kata == "C" || g.kata == "D");   // A・C・D も深さの版を選ぶ(mizoPathVar)
            var tls = targetLines(g);
            var ms = masuOf(g);
            // 欄 masuPitchMaxM・masuAt・segMasu: 区間を桝で割り、区間ごとに尻を桝に入れる(置き場は EdoBuild.SplitMizoAtMasu → PlaceBest)
            float splitPitch = Has(s, "masuPitchMaxM") ? F(s["masuPitchMaxM"]) : float.NaN;
            string splitKata = null, splitPath = null; List<Vector2> splitCorners = null; float splitTopA = 0f, splitSump = 0f, splitDepthHard = float.NaN;
            if (!float.IsNaN(splitPitch))
            {
                var smRaw = segMasuOf(g); splitKata = smRaw != null ? Sk(smRaw, "kata") : null;
                if (splitKata == null) { var gm = Regex.Match(g.to, @"\b(G\d+)\b"); if (gm.Success) splitKata = gm.Groups[1].Value; }
                splitPath = splitKata != null ? EdoBuild.AssetByName("Own", "DoiMasu", splitKata) : null;
                if (splitPath == null || !Exists(splitPath)) { line(2, g.id + "(型 " + g.kata + "): 区間に足す桝の駒 " + (splitPath ?? "Own.DoiMasu(" + (splitKata ?? "型が欄に無い") + ")") + " が無い ── 建てない"); Wait(g.id + ": 区間に足す桝の駒 Own.DoiMasu(\"" + (splitKata ?? "?") + "\") が無い(部材方)"); continue; }
                var smk = splitKata != null && Has(kata, splitKata) ? O(kata[splitKata]) : null;
                if (smk != null) { splitTopA = Has(smk, "topAbove") ? F(smk["topAbove"]) : 0f; splitSump = Has(smk, "sumpBelowOutlet") ? F(smk["sumpBelowOutlet"]) : 0f; }
                if ((Sk(s, "masuAt") ?? "").Contains("出隅")) { splitCorners = eaveCorners(g); if (splitCorners.Count == 0) Wait(g.id + ": 欄 masuAt「出隅」の棟の軒の矩形が引けない ── 出隅の狙いを外して割る"); }
                splitDepthHard = kf(g.kata, "depthMax");
            }
            // 軒先の鉛直下に引く線(雨落ち)は、据わった駒の足(縁の束・柱・塀)から溝(桝で割る区間は桝)の外の面 + 0.05 だけ外へ逃がす
            //   (狙い = 軒先の鉛直下・硬 = 溝の外形が足に掛からない ── EdoBuild.PushLineOffFeet)
            if (g.line.Contains("軒") && raw.Count > 0)
            {
                float hwF = halfWOf(g);
                if (splitPath != null) { var mpF = EdoBuild.MizoPieceOf(splitPath); if (mpF.ok) hwF = Mathf.Max(float.IsNaN(hwF) ? 0f : hwF, Mathf.Max(mpF.halfW, 0.5f * (mpF.zMax - mpF.zMin))); }
                if (!float.IsNaN(hwF))
                {
                    float bx0 = float.MaxValue, bx1 = float.MinValue, bz0 = float.MaxValue, bz1 = float.MinValue;
                    foreach (var pl in raw) foreach (var q in pl) { bx0 = Mathf.Min(bx0, q.x); bx1 = Mathf.Max(bx1, q.x); bz0 = Mathf.Min(bz0, q.y); bz1 = Mathf.Max(bz1, q.y); }
                    var nearL = new Vector4(bx0 - 2f, bz0 - 2f, bx1 + 2f, bz1 + 2f);
                    //   線を寄せる足は束・柱・幹だけ(compact)── 塀の脇を通る溝は設計どおり(第24巡: D3 seg1 の 17.6m・22.1m の辺は塀の足 1354・357 点を数えて寄らなかった)
                    var feetL = EdoBuild.StandingFeetXZ(grp.parent, groundMizo, skip: new HashSet<string> { grp.name }, near: nearL, compact: true);
                    int pushedN = 0, stuckN = 0; float pushedMx = 0f; var stuckWhy = new List<string>();
                    for (int ri = 0; ri < raw.Count; ri++)
                    {
                        float pm; int ps, st; raw[ri] = EdoBuild.PushLineOffFeet(raw[ri], feetL, hwF + 0.05f, 1.0f, out pm, out ps, out st, stuckWhy);
                        pushedN += ps; stuckN += st; pushedMx = Mathf.Max(pushedMx, pm);
                    }
                    if (pushedN > 0) line(1, g.id + ": 雨落ちの線を据わった駒の足から外へ寄せた辺 " + pushedN + "(最大 " + pushedMx.ToString("F2") + "m ── 狙いの軒先の鉛直下から外れた・柔)");
                    if (stuckN > 0) line(1, g.id + ": 足が線の両側に在るか 1.0m を超えて寄せる辺 " + stuckN + " は寄せなかった(桝・溝の置き場の硬い条件で測る)── " + string.Join(" / ", stuckWhy));
                }
            }
            g.lines = new List<List<Vector2>>();
            foreach (var pl in raw) { if (g.fixedDir) g.lines.Add(new List<Vector2>(pl)); else g.lines.AddRange(orient(pl, tls, g.flow.Contains("二手"))); }
            // 段・勾配・頭と尻の高さ(欄)
            float slopeMin = Has(s, "slopeMin") ? F(s["slopeMin"]) : (Has(s, "slope") && !(s["slope"] is string) ? F(s["slope"]) : 0f);
            float stepPitch = Has(s, "stepPitchKen") ? F(s["stepPitchKen"]) * ken : 0f, stepRise = Has(s, "stepRiseMax") ? F(s["stepRiseMax"]) : 0f;
            float head = Has(s, "bottomHead") ? F(s["bottomHead"]) : Has(s, "bottom") && !(s["bottom"] is string) ? F(s["bottom"]) : float.NaN;
            float tail = Has(s, "bottomTail") ? F(s["bottomTail"]) : float.NaN;
            var ob = Has(g.dr, "outletBuild") ? O(g.dr["outletBuild"]) : null; if (g.to == "outletBuild" && ob != null && Has(ob, "bottom")) tail = F(ob["bottom"]);
            var lv = Has(g.dr, "levels") ? O(g.dr["levels"]) : null;
            bool firstLevel = true; foreach (var h in segs) if (h.drain == g.drain && receivers(h).Contains(g)) firstLevel = false;
            if (lv != null && firstLevel && float.IsNaN(head) && Has(lv, "eastHead")) head = F(lv["eastHead"]);
            if (lv != null && float.IsNaN(tail) && Has(lv, "westMax") && !Regex.IsMatch(g.to, @"seg\d")) tail = F(lv["westMax"]);
            float dropMin = 0.01f;
            foreach (var o in A(Gk(g.dr, "toriai")) ?? new List<object>()) { var t = O(o); if (Has(t, "dropMin")) dropMin = Mathf.Max(dropMin, F(t["dropMin"])); }
            int laid = 0, miss = 0; string missWhy = null; var pfx = g.id.Replace(" ", "_");
            var hardMsg = new List<string>(); int floatN = 0; float sink = 0f, deep = 0f, shallow = 0f, rise = 0f; var hl = new List<string>();
            for (int li = 0; li < g.lines.Count; li++)
            {
                var pl = g.lines[li];
                Vector2 endOrig = pl[pl.Count - 1];   // 尻(桝の芯・受ける区間の頭の引き当てはこの点 ── 切る前)
                if (ms != null && !masuPlan.ContainsKey(ms.id))
                {
                    // 桝へ入る尻は桝の外の面で止める(EdoBuild.TrimLineAtCircle)── 面の取り合いで解いた桝(masuPlan)は線が面の中央で止まっているので切らない── 尻の駒が桝の窪みの上へ張り出して浮く(D1 seg3 ── EDO-0533 第10巡)
                    var mpm = EdoBuild.MizoPieceOf(EdoBuild.AssetByName("Own", "DoiMasu", Sk(ms.raw, "kata")));
                    if (mpm.ok)
                    {
                        // 桝の仮の芯 = この尻と、同じ桝へ入る他の区間の線の端(この尻に近い方)の平均 ── 桝の芯の引き方(入る尻の平均)と同じ
                        Vector2 sum = endOrig; int nE = 1; bool far = false;
                        foreach (var h in segs)
                        {
                            if (h == g || masuOf(h) != ms || h.rawLines == null) continue;
                            foreach (var rl in h.rawLines)
                            {
                                if (rl.Count < 2) continue;
                                var e = (rl[0] - endOrig).sqrMagnitude < (rl[rl.Count - 1] - endOrig).sqrMagnitude ? rl[0] : rl[rl.Count - 1];
                                if ((e - endOrig).magnitude > 2f * mpm.halfW + 0.6f) far = true;
                                sum += e; nE++;
                            }
                        }
                        if (!far)
                        {
                            float cut; var trm = EdoBuild.TrimLineAtCircle(pl, sum / nE, mpm.halfW, 0.5f, out cut);
                            if (cut > 1e-3f) { pl = trm; g.lines[li] = trm; hl.Add("線" + (li + 1) + " 尻を桝の外の面(芯から " + mpm.halfW.ToString("F2") + ")で " + cut.ToString("F2") + "m 止めた"); }
                        }
                        else hl.Add("⚠ 線" + (li + 1) + " 桝へ入る他の尻が散らばり、桝の芯が引けない ── 尻を切らない");
                    }
                }
                else if (ms != null && masuPlan.ContainsKey(ms.id))
                {
                    // 面の取り合いで解いた桝へ入る尻(線は面の中央で止まる)── 尻の駒の弦の矩形が桝の内法の窪みに掛からない所まで戻す(EdoBuild.TrimTailOutOfHull・硬)。
                    //   45° の脚で入る D1 seg2・seg4 は斜めの小口の隅が壁(0.15)を越えて窪みの上へ出て、尻の駒が 0.33〜0.53 浮いた(EDO-0533 第12巡)
                    var mk = Has(kata, Sk(ms.raw, "kata") ?? "") ? O(kata[Sk(ms.raw, "kata")]) : null; var inn = mk != null ? A(Gk(mk, "inner")) : null;
                    float ih = inn != null && inn.Count > 0 ? 0.5f * F(inn[0]) : float.NaN;
                    if (float.IsNaN(ih)) hl.Add("⚠ 線" + (li + 1) + " 桝 " + ms.id + " の内法(欄 kata." + Sk(ms.raw, "kata") + ".inner)が無い ── 尻を窪みで止められない(未検査)");
                    else
                    {
                        float tc; var trt = EdoBuild.TrimTailOutOfHull(pl, EdoBuild.MasuInnerHull(masuPlan[ms.id], ih), Mathf.Max(Mathf.Abs(mp0.xMin), Mathf.Abs(mp0.xMax)), 1f, 0.6f, 0.5f, out tc);
                        if (tc > 1e-3f) { pl = trt; g.lines[li] = trt; hl.Add("線" + (li + 1) + " 尻を桝 " + ms.id + " の内法の窪みの外で " + tc.ToString("F2") + "m 止めた(駒の弦の矩形 × 内法 " + (2f * ih).ToString("F2") + " 角)"); }
                        else if (tc < 0f) hl.Add("⚠ 線" + (li + 1) + " 尻の駒が桝 " + ms.id + " の内法の窪みに掛かる ── 0.6m 戻しても外れない(線が窪みを横切る)");
                    }
                }
                // 頭が別の系統の既に据わった溝の駒の外形の中から出るなら、外形の外で止める(EdoBuild.TrimHeadOutOfHulls ── 頭の駒が他の溝の窪みの上に張り出して浮く・
                //   D2 seg1 線3 × D3 seg1 線3 の奥の隅 0.28・小口の下の隙 0.24 ── EDO-0533 第11巡)。同じ系統の線(二手に分けた線の頭)は外す
                {
                    var oth = new List<Vector2[]>();
                    foreach (var h in segs) if (h != g && h.drain != g.drain) foreach (var pc in h.pieces) if (pc != null) { var hx = EdoBuild.HullXZ(pc); if (hx != null && hx.Count >= 3) oth.Add(hx.ToArray()); }
                    float hcut; var trh = EdoBuild.TrimHeadOutOfHulls(pl, oth, Mathf.Max(Mathf.Abs(mp0.xMin), Mathf.Abs(mp0.xMax)), 1.2f, 0.5f, out hcut);
                    if (hcut > 1e-3f) { pl = trh; g.lines[li] = trh; hl.Add("線" + (li + 1) + " 頭を他の系統の溝の駒の外形の外で " + hcut.ToString("F2") + "m 止めた"); }
                }
                var sp = new EdoBuild.MizoSpec
                {
                    chord = true,   // 駒を弦に据える(折れの先・桝の窪みの上へ真っ直ぐ張り出さない ── D1 seg2・seg4 の尻 0.33〜0.53・EDO-0533 第11巡)
                    name = g.id, kata = g.kata, line = pl, groundAt = groundMizo, topAbove = topAbove(g.kata),
                    pieceDepth = fixedD ? mp0.Depth : float.NaN, depthMin = kf(g.kata, "depthMin"), depthMax = kf(g.kata, "depthMax"),
                    slopeMin = slopeMin, headBottom = head, tailMax = tail, stepPitch = stepPitch, stepRiseMax = stepRise
                };
                if (float.IsNaN(sp.depthMin)) sp.depthMin = Has(O(kata[g.kata]), "depth") ? kf(g.kata, "depth") : 0.05f;
                if (float.IsNaN(sp.depthMax)) sp.depthMax = Mathf.Max(sp.depthMin, 1f);
                if (!fixedD) sp.depthMin = Mathf.Max(sp.depthMin, mp0.Depth);   // 選べる駒の最も浅い版の実測の深さ(欄の depthMin より深ければそれ)
                // 硬「溝の底 ≤ そこの地面 + topAbove − 深さ」の「そこ」= 駒が覆う矩形 ── 芯から最も遠い縁まで(片側の溝は芯に対して非対称)
                sp.halfW = Mathf.Max(Mathf.Abs(mp0.xMin), Mathf.Abs(mp0.xMax));
                if (!fixedD) { var mpD = EdoBuild.MizoPieceOf(mizoPathVar(g.kata, sp.depthMax + sp.topAbove)); if (mpD.ok) sp.halfW = Mathf.Max(sp.halfW, Mathf.Max(Mathf.Abs(mpD.xMin), Mathf.Abs(mpD.xMax))); }
                // 硬: 受ける側の底 < 入る側の底 ── 入る区間の尻を上限に
                foreach (var kv in solvedEnds)
                {
                    var viaMasu = masuOf(kv.Key);
                    bool feeds = receivers(kv.Key).Contains(g) || (viaMasu != null && viaMasu.then != null && viaMasu.id.StartsWith(g.drain + " ") && Regex.IsMatch(viaMasu.then, @"seg" + (g.si + 1) + @"\b"));
                    if (!feeds) continue;
                    float dist; float sAt = EdoBuild.NearestS(pl, new Vector2(kv.Value.x, kv.Value.y), out dist);
                    if (dist <= 3f) sp.caps.Add(new Vector3(sAt, kv.Value.z, dropMin));
                }
                if (!float.IsNaN(splitPitch))
                {
                    // 桝は先に据わった駒(縁の束・柱・塀・幹)の足に掛けない(硬)── 足は線の周り 2m の駒の実メッシュから拾う
                    float fx0 = float.MaxValue, fx1 = float.MinValue, fz0 = float.MaxValue, fz1 = float.MinValue;
                    foreach (var q in pl) { fx0 = Mathf.Min(fx0, q.x); fx1 = Mathf.Max(fx1, q.x); fz0 = Mathf.Min(fz0, q.y); fz1 = Mathf.Max(fz1, q.y); }
                    var feet = EdoBuild.StandingFeetXZ(grp.parent, sp.groundAt, skip: new HashSet<string> { grp.name }, near: new Vector4(fx0 - 2f, fz0 - 2f, fx1 + 2f, fz1 + 2f));
                    var srep = EdoBuild.SplitMizoAtMasu(grp, pfx + "_" + li, sp, splitPath, splitPitch, float.IsNaN(splitDepthHard) ? sp.depthMax : splitDepthHard, splitTopA, splitSump, splitCorners, feet: feet);
                    for (int ck = 0; ck < srep.cuts.Count; ck++)
                    {
                        var cut = srep.cuts[ck]; g.prof.Add(cut.pr);
                        var ffail = new List<string>();
                        var cmade = EdoBuild.LayMizo(grp, pfx + "_" + li + "_" + ck, cut.pr, need => mizoPathVar(g.kata, need + sp.topAbove), out int cmi, out string cmw, groundMizo, ffail);
                        g.pieces.AddRange(cmade); laid += cmade.Count; miss += cmi; if (cmw != null) missWhy = cmw;
                        if (ffail.Count > 0)
                        {
                            floatN += ffail.Count;
                            hardMsg.Add("線 " + (li + 1) + " 区間 " + (ck + 1) + ": 地面より浮く駒 " + ffail.Count + " を据えない(" + string.Join(" / ", ffail.ToArray()) + ")");
                            Wait(g.id + " 線 " + (li + 1) + " 区間 " + (ck + 1) + ": 溝の駒が地面より浮く ── 据えない " + ffail.Count + " 駒(" + ffail[0] + (ffail.Count > 1 ? " ほか" : "") + ")");
                        }
                        sink = Mathf.Max(sink, cut.pr.worstSink); deep = Mathf.Max(deep, cut.pr.worstDeep); shallow = Mathf.Max(shallow, cut.pr.worstShallow); rise = Mathf.Max(rise, cut.pr.worstRise);
                        string where = cut.atEnd ? "線の尻" : float.IsNaN(cut.cornerDist) ? "出隅の狙いなし" : "出隅から " + cut.cornerDist.ToString("F2") + "m" + (cut.cornerDist <= 0.6f ? "" : "【柔 ⚠】");
                        hl.Add("線" + (li + 1) + "・区間" + (ck + 1) + " " + cut.pr.length.ToString("F1") + "m" + (cut.len > splitPitch + 1e-3f ? "(> " + splitPitch.ToString("F0") + "m【柔 ⚠】)" : "")
                               + " 底 " + cut.pr.Head.ToString("F3") + "→" + cut.pr.Tail.ToString("F3") + "・要る深さ 最大 " + cut.needDepth.ToString("F3") + "【硬 ≤ " + (float.IsNaN(splitDepthHard) ? sp.depthMax : splitDepthHard).ToString("F2") + " ⭕】"
                               + " → 桝 " + cut.masu.name + "(" + splitKata + "・" + where + "・底 " + cut.floor.ToString("F3") + " < 尻の底【硬 ⭕】" + (cut.sink > 0.005f ? "・天端の沈み " + cut.sink.ToString("F3") + "m【柔 ⚠】" : "") + ")");
                        solvedEnds.Add(new KeyValuePair<MzSeg, Vector3>(g, new Vector3(cut.at.x, cut.at.y, cut.pr.Tail)));
                        splitMasus.Add(new KeyValuePair<MzSeg, EdoBuild.MasuCut>(g, cut));
                    }
                    { string tsum = srep.tally.Summary(); if (tsum.Length > 0) hl.Add("線" + (li + 1) + " 桝の置き場" + tsum); }
                    if (!srep.ok) { hardMsg.Add("線 " + (li + 1) + ": " + srep.why + " ── その先は据えない"); Wait(g.id + " 線 " + (li + 1) + ": " + srep.why); }
                    continue;
                }
                var pr = EdoBuild.SolveMizoBottom(sp);
                g.prof.Add(pr);
                if (!pr.ok) { hardMsg.Add("線 " + (li + 1) + ": " + pr.hard); continue; }
                var floatFail = new List<string>();
                var made = EdoBuild.LayMizo(grp, pfx + "_" + li, pr, need => mizoPathVar(g.kata, need + sp.topAbove), out int mi, out string mw, groundMizo, floatFail);   // 版は要求以下で最も深い物(mizoPathVar)
                g.pieces.AddRange(made); laid += made.Count; miss += mi; if (mw != null) missWhy = mw;
                if (floatFail.Count > 0)
                {
                    floatN += floatFail.Count;
                    hardMsg.Add("線 " + (li + 1) + ": 地面より浮く駒 " + floatFail.Count + " を据えない(" + string.Join(" / ", floatFail.ToArray()) + ")");
                    Wait(g.id + " 線 " + (li + 1) + ": 溝の駒が地面より浮く ── 据えない " + floatFail.Count + " 駒(" + floatFail[0] + (floatFail.Count > 1 ? " ほか" : "") + ")");
                }
                if (pr.headLowered > 0.005f) hl.Add("⚠ 線" + (li + 1) + " 頭の底を欄 " + head.ToString("F3") + " から " + pr.Head.ToString("F3") + " へ " + pr.headLowered.ToString("F3") + "m 下げた(硬: 底 ≤ 駒が覆う地面の最低 + " + sp.topAbove.ToString("F2") + " − 深さ)");
                sink = Mathf.Max(sink, pr.worstSink); deep = Mathf.Max(deep, pr.worstDeep); shallow = Mathf.Max(shallow, pr.worstShallow); rise = Mathf.Max(rise, pr.worstRise);
                hl.Add("線" + (li + 1) + " " + pr.length.ToString("F1") + "m 底 " + pr.Head.ToString("F3") + "→" + pr.Tail.ToString("F3")
                       + "(落差 " + (pr.Head - pr.Tail).ToString("F3") + "・平均勾配 " + ((pr.Head - pr.Tail) / Mathf.Max(0.01f, pr.length)).ToString("0.0000")
                       + (pr.steps > 0 ? "・段 " + pr.steps + " 区・1段 最大 " + pr.worstRise.ToString("F3") : "") + ")");
                solvedEnds.Add(new KeyValuePair<MzSeg, Vector3>(g, new Vector3(endOrig.x, endOrig.y, pr.Tail)));
                if (ms != null) { ms.inEnds.Add(endOrig); ms.inBottoms.Add(pr.Tail); }
            }
            g.built = laid > 0;
            string head2 = g.id + "(型 " + g.kata + "・" + EdoBuild.AssetByName("Own", "DoiMizo", g.kata) + "): ";
            if (hardMsg.Count > 0) line(2, head2 + "硬い条件を満たせない線 " + hardMsg.Count + " ── 据えない: " + string.Join(" / ", hardMsg.ToArray()));
            if (laid > 0)
            {
                string soft = (sink > 0.005f ? "・天端の沈み 最悪 " + sink.ToString("F3") + "m(柔: 深さの決まった駒で勾配を取った分)" : "")
                            + (deep > 0.005f ? "・深さが上限を " + deep.ToString("F3") + "m 超える区間(柔" + (g.kata == "D" ? ": D は E へ替える区間" : "") + ")" : "")
                            + (shallow > 0.005f ? "・深さが下限に " + shallow.ToString("F3") + "m 足りない区間" : "");
                line(soft.Length > 0 ? 1 : 0, head2 + laid + " 駒 ── " + string.Join(" / ", hl.ToArray()) + (floatN > 0 ? "【硬 ✗ 地面より浮く駒 " + floatN + " を据えず ── 他は ⭕ 逆勾配0・入る底より低い・段 ≤ 上限】" : "【硬 ⭕ 逆勾配0・入る底より低い・段 ≤ 上限・駒が地面より浮かない】") + soft);
            }
            if (miss > 0) { line(1, g.id + ": 据えられない駒 " + miss + "(" + missWhy + ")"); Wait(g.id + ": 駒 " + missWhy + " が無い(部材方)"); }
        }

        // ---- 張り石の落とし(型 I ── 区間の欄 drop)
        foreach (var g in segs) if (Has(g.raw, "drop")) BuildHariOtoshi9(g, grp, byId, edgeChk, kf, line);

        // ---- 区間に足した桝から先の埋樋(焼かない)→ 受ける区間の石組の側壁の口(型 M)── 欄 segMasu・hardAdd「埋樋の勾配 ≥ …、尻の底 > 受ける溝の底」
        //   口の所は EdoBuild.UzumiToiMouth(受ける溝の底が埋樋の尻の底より欄の落ち以上低くなる最初の所)。側壁を割る口の据え方はまだ無い ── Wait に名乗る
        foreach (var kvM in splitMasus)
        {
            var gU = kvM.Key; var cutU = kvM.Value; var smr = segMasuOf(gU); var rcU = segMasuRecv(gU);
            string nmU = gU.id + " 桝 " + cutU.masu.name;
            if (smr == null || rcU == null) { line(2, nmU + ": 桝から先の受ける区間が欄 segMasu に無い ── 埋樋を引かない"); Wait(nmU + ": 桝から先の受ける区間(欄 segMasu の「→ segN」)が無い"); continue; }
            float slopeU = float.NaN;
            foreach (var o in A(Gk(gU.dr, "hardAdd")) ?? new List<object>()) { var mm = Regex.Match(S(o) ?? "", @"埋樋の勾配\s*≥\s*([0-9.]+)"); if (mm.Success) slopeU = float.Parse(mm.Groups[1].Value, ci); }
            float dropU = float.NaN; { var mm = Regex.Match(Sk(smr, "then") ?? "", @"([0-9.]+)\s*以上低く"); if (mm.Success) dropU = float.Parse(mm.Groups[1].Value, ci); }
            if (float.IsNaN(slopeU) || float.IsNaN(dropU)) { line(2, nmU + ": 埋樋の勾配(hardAdd)か口の落ち(segMasu.then)が欄に無い ── 埋樋を引かない"); Wait(nmU + ": 埋樋の勾配・口の落ちが欄に無い"); continue; }
            var okP = new List<EdoBuild.MizoProfile>(); if (rcU.built) foreach (var p in rcU.prof) if (p != null && p.ok) okP.Add(p);
            if (okP.Count == 0) { line(2, nmU + " → " + rcU.id + ": 受ける溝が建っていない ── 埋樋の口が決まらない"); Wait(nmU + " → " + rcU.id + ": 受ける溝が建っていない ── 埋樋の口が決まらない"); continue; }
            Vector2 mAt; float tbU, lenU, rbU; int rlU; string uw;
            if (!EdoBuild.UzumiToiMouth(cutU.at, cutU.outletBottom, slopeU, dropU, okP, out mAt, out tbU, out lenU, out rbU, out rlU, out uw))
            { line(2, nmU + " → " + rcU.id + ": " + uw + "【硬 ✗】── 埋樋を引かない"); Wait(nmU + " → " + rcU.id + ": " + uw); continue; }
            line(0, nmU + " → 埋樋(焼かない)" + lenU.ToString("F1") + "m・桝の出口の底 " + cutU.outletBottom.ToString("F3") + " → 尻の底 " + tbU.ToString("F3") + " → " + rcU.id + " 線" + (rlU + 1) + " の底 " + rbU.ToString("F3")
                    + " @(" + mAt.x.ToString("F1") + ", " + mAt.y.ToString("F1") + ")【硬 ⭕ 勾配 " + slopeU.ToString("0.000") + " ≥ " + slopeU.ToString("0.000") + "・尻の底 − 受ける溝の底 " + (tbU - rbU).ToString("F3") + " ≥ " + dropU.ToString("F2") + "】");
            Wait(nmU + " → " + rcU.id + ": 石組の側壁の口(型 M)を (" + mAt.x.ToString("F1") + ", " + mAt.y.ToString("F1") + ")・底 " + tbU.ToString("F3")
                 + " に開ける部材と置き場が無い(Own.DoiAnkyoKuchi は溝の端の口 ── 側壁を割る口の据え方が EdoBuild に無い・部材方と EdoBuild)── 埋樋は焼かない・地中の経路と他の物との取り合いは未検査");
        }

        // ---- 桝(溝の出合い)
        var masuAt = new Dictionary<string, Vector2>();
        foreach (var kv in masus)
        {
            var mz = kv.Value; var m = mz.raw; string kt = Sk(m, "kata");
            AuditKeys(m, "排水 " + mz.id, "kata", "at", "then", "top", "bottom", "inlet", "atHard", "outFace");
            string path = EdoBuild.AssetByName("Own", "DoiMasu", kt);
            if (path == null || !Exists(path)) { line(2, mz.id + "(" + kt + "): 部材が無い " + (path ?? "Own.DoiMasu(\"" + kt + "\") が未登録") + " ── 建てない"); Wait(mz.id + ": 桝の駒 Own.DoiMasu(\"" + kt + "\") が無い(部材方)"); continue; }
            EdoBuild.MasuPlan mpl; bool planned = masuPlan.TryGetValue(mz.id, out mpl);
            if (!planned && masuPlanWhy.ContainsKey(mz.id)) { line(2, mz.id + "(" + kt + "): 置き場が解けない ── " + masuPlanWhy[mz.id] + " ── 建てない"); Wait(mz.id + ": " + masuPlanWhy[mz.id]); continue; }
            if (mz.inEnds.Count == 0) { line(2, mz.id + "(" + kt + "「" + Sk(m, "at") + "」): 入る溝が一本も建っていない ── 置き場が決まらない"); Wait(mz.id + ": 入る溝が建っていない ── 桝の置き場が引けない"); continue; }
            Vector2 c = Vector2.zero; foreach (var p in mz.inEnds) c += p; c /= mz.inEnds.Count;
            float spread = 0f; foreach (var p in mz.inEnds) spread = Mathf.Max(spread, Vector2.Distance(p, c));
            var mp = EdoBuild.MizoPieceOf(path);
            if (planned) c = mpl.at;
            else if (spread > mp.halfW + 0.3f) { line(2, mz.id + ": 入る溝の尻が桝に集まらない(散らばり " + spread.ToString("F2") + "m > 桝の半幅 + 0.3)── 建てない"); Wait(mz.id + ": 入る溝の尻が一所に集まらない"); continue; }
            float inMin = float.MaxValue; foreach (var b in mz.inBottoms) inMin = Mathf.Min(inMin, b);
            var kk = O(kata[kt]); float topA = Has(kk, "topAbove") ? F(kk["topAbove"]) : 0f, sump = Has(kk, "sumpBelowOutlet") ? F(kk["sumpBelowOutlet"]) : 0f;
            float topWant = Has(m, "top") ? F(m["top"]) : GroundY(c.x, c.y) + topA;
            float floorMax = Has(m, "bottom") ? F(m["bottom"]) : inMin - Mathf.Max(0.01f, sump);
            Vector2 outDir = (c - parcelC).normalized;
            if (!planned) foreach (var g in segs) if (g.built && mz.then != null && g.drain == mz.id.Split(' ')[0] && Regex.IsMatch(mz.then, @"seg" + (g.si + 1) + @"\b") && g.lines.Count > 0 && g.lines[0].Count > 1) outDir = (g.lines[0][1] - g.lines[0][0]).normalized;
            float floor, sink;
            if (planned) outDir = mpl.outDir;
            var go = EdoBuild.PlaceMasu(grp, mz.id.Replace(" ", "_").Replace("[", "").Replace("]", ""), path, c, outDir, topWant, floorMax, out floor, out sink);
            if (go == null) { line(2, mz.id + ": 桝が測れない " + path); continue; }
            masuAt[mz.id] = c;
            if (planned && !MasuPlannedChecks9(mz, go, mpl, masuPlanBld[mz.id], eave, segs, (Func<MzSeg, MzMasu>)masuOf, masuFace, line)) { UnityEngine.Object.DestroyImmediate(go); masuAt.Remove(mz.id); continue; }
            // 硬: 欄 at「軒先の線の外」── 桝の外形(実測の幅・長さ)が棟の軒先の外周に掛からない(掛かると床下の束石・礎石が桝の窪みの上に載る ── 土井 書院 第10巡)
            if (!planned && (Sk(m, "at") ?? "").Contains("軒先の線の外"))
            {
                var nr = new Vector2(-outDir.y, outDir.x); float hz = 0.5f * (mp.zMax - mp.zMin);
                var box = new List<Vector2> { c - outDir * hz - nr * mp.halfW, c + outDir * hz - nr * mp.halfW, c + outDir * hz + nr * mp.halfW, c - outDir * hz + nr * mp.halfW };
                foreach (var kv2 in eave)
                    if (EdoBuild.ConvexOverlap(box, new List<Vector2>(kv2.Value)))
                    {
                        line(2, mz.id + ": 桝が " + kv2.Key + " の軒先の外周に掛かる(欄「軒先の線の外」【硬 ✗】)── 入る溝の尻の平均に置いた。軒先の外へ出すと入る溝(軒先の鉛直下)が桝へ届かず、曲げて入れる取り合いが欄に無い");
                        Wait(mz.id + ": 欄「軒先の線の外」を満たす置き場と、軒先の鉛直下の溝をそこへ曲げて入れる取り合い(曲げの所・桝の向き)が欄に無い ── 普請方へ");
                    }
            }
            bool hardOk = floor < inMin - 1e-4f;
            line(hardOk ? (sink > 0.005f ? 1 : 0) : 2, mz.id + "(" + kt + "): 底 " + floor.ToString("F3") + " < 入る溝の底の最低 " + inMin.ToString("F3") + (hardOk ? "【硬 ⭕】" : "【硬 ✗】")
                + "・天端 " + (floor + mp.Depth).ToString("F3") + "(狙い " + topWant.ToString("F3") + (sink > 0.005f ? "・沈み " + sink.ToString("F3") + "m【柔 ⚠】" : "") + ")・入る溝 " + mz.inEnds.Count + " 本");
            if (Has(m, "then") && !Regex.IsMatch(mz.then ?? "", @"seg\d")) Wait(mz.id + ": 桝から先「" + mz.then + "」(埋樋)は焼かない ── 落とし先の口の高さとの突き合わせは未検査");
        }

        // ---- 受け(型 J)── 起点の桝が据わってから置き場を選ぶ(EdoBuild.PlaceUke → PlaceBest)
        foreach (var g in segs) if (g.kata == "J") BuildUke9(g, grp, masuAt, edgeChk, line);

        // ---- 横断の蓋石(型 L)・水切り石(型 O)・吐口(outletBuild)
        for (int di = 0; di < drains.Count; di++)
        {
            var dr = O(drains[di]); string dn = (Sk(dr, "name") ?? "").Split(' ')[0];
            foreach (var o in A(Gk(dr, "cross")) ?? new List<object>())
            {
                var c = O(o); string at = Sk(c, "at") ?? "", kt = Sk(c, "kata");
                AuditKeys(c, "排水 " + dn + " cross", "at", "kata", "t", "n", "lid", "slope", "topBelowDoma", "rule", "hard", "extentFrom", "sideKen");
                if (kt == "L")
                {
                    var rn = Regex.Matches(at, @"\bR\d\d\b"); int put = 0; float worst = 0f; var unread = Regex.Replace(at, @"\bR\d\d\b", "").Trim('・', ' ');
                    float t = Has(c, "t") ? F(c["t"]) : float.NaN;
                    foreach (Match rm in rn)
                    {
                        List<Vector2> route = null;
                        foreach (var ro in A(D["routes"]) ?? new List<object>()) { var r = O(ro); if (Sk(r, "name") == rm.Value && Has(r, "pts")) { route = new List<Vector2>(); foreach (var q in A(Gk(r, "pts"))) { var qq = A(q); route.Add(f.W(F(qq[0]), F(qq[1]))); } } }
                        if (route == null) { Wait(dn + " cross「" + at + "」: 路 " + rm.Value + " の線が欄に無い"); continue; }
                        foreach (var g in segs)
                        {
                            if (g.drain != dn || !g.built) continue;
                            foreach (var pl in g.lines)
                            {
                                Vector2 hit; float sA; if (!EdoBuild.PolylineCross(pl, route, out hit, out sA)) continue;
                                float len = 2f * g.halfW + 0.30f;
                                string lp = EdoBuild.AssetByName("Own", "DoiFutaishiFor", g.kata, t);   // 蓋の長さは型ごとに一つ(溝の外幅 + 掛かり)
                                if (lp == null || !Exists(lp)) { Wait(dn + " cross " + rm.Value + ": 蓋石 Own.DoiFutaishi(" + len.ToString("0.00") + "," + t + ") が無い(部材方)"); continue; }
                                Vector2 d; EdoBuild.PointAt(pl, sA, out d); float off;
                                var lid = EdoBuild.LayFutaishi(grp, dn + "_Futa_" + rm.Value + "_" + g.si, lp, hit, d, g.pieces, GroundY, out off);
                                if (lid != null) { put++; worst = Mathf.Max(worst, Mathf.Abs(off)); }
                            }
                        }
                    }
                    float tol = kf("L", "topTol");
                    if (put > 0) line(worst > tol + 1e-4f ? 1 : 0, dn + " 蓋石(L・t " + t + "): " + put + " 枚(" + string.Join("・", ToArr(rn)) + " を横切る所・下端を溝の縁の天端に)・路面との差 最悪 " + worst.ToString("F3") + "m(柔 ≤ " + tol.ToString("F2") + ")");
                    else if (rn.Count > 0) line(1, dn + " 蓋石(L)「" + at + "」: 横切る所が無い/溝が建っていない ── 据えない");
                    if (unread.Length > 0 && Regex.IsMatch(unread, @"[^\s・を横切る所]")) Wait(dn + " cross「" + at + "」: 路の名で書かれていない相手(" + unread + ")は線が無く据えない");
                    continue;
                }
                if (kt == "O")
                {
                    var rm = Regex.Match(at, @"(R_[A-Za-z0-9_]+)\s*の頭");
                    Dictionary<string, object> ramp = null;
                    if (rm.Success) foreach (var ro in A(D["ramps"]) ?? new List<object>()) { var r = O(ro); if (Sk(r, "name") == rm.Groups[1].Value) ramp = r; }
                    if (ramp == null || !Has(ramp, "u0")) { line(2, dn + " 水切り石「" + at + "」: 坂の面(u0..v1)が欄に無い ── 建てない"); Wait(dn + " 水切り石「" + at + "」: 坂の面が引けない"); continue; }
                    float u0 = F(ramp["u0"]), u1 = F(ramp["u1"]), v0 = F(ramp["v0"]), v1 = F(ramp["v1"]);
                    bool alongU = (u1 - u0) > (v1 - v0);
                    Vector2 eA = alongU ? f.W(u0, 0.5f * (v0 + v1)) : f.W(0.5f * (u0 + u1), v0), eB = alongU ? f.W(u1, 0.5f * (v0 + v1)) : f.W(0.5f * (u0 + u1), v1);
                    float gA = GroundY(eA.x, eA.y), gB = GroundY(eB.x, eB.y);
                    Vector2 headP = gA > gB ? eA : eB, down = ((gA > gB ? eB : eA) - headP).normalized;
                    float width = (alongU ? (v1 - v0) : (u1 - u0)) * ken, len = width + 0.30f;
                    string op = EdoBuild.AssetByName("Own", "DoiMizukiri", (float)Math.Round(len, 2));   // 坂の幅 + 0.30 を cm で引く(焼いた駒の名と同じ丸め)
                    if (op == null || !Exists(op)) { line(2, dn + " 水切り石(" + rm.Groups[1].Value + "): 部材が無い Own.DoiMizukiri(" + len.ToString("0.00") + ") ── 建てない"); Wait(dn + ": 水切り石 Own.DoiMizukiri(" + len.ToString("0.00") + ") が無い(部材方)"); continue; }
                    var mk = EdoBuild.MizoPieceOf(op);
                    string note;
                    var go = EdoBuild.PlaceMizukiri(grp, dn + "_Mizukiri_" + rm.Groups[1].Value, op, headP + down * (0.5f * (mk.zMax - mk.zMin) + 0.05f), down, kf("O", "skewDeg"), kf("O", "topAbove"), GroundY, out note);
                    line(go == null ? 2 : note.Contains("⚠") ? 1 : 0, dn + " 水切り石(O・" + rm.Groups[1].Value + " の頭・長さ " + len.ToString("0.00") + " = 坂の幅 " + width.ToString("0.00") + " + 0.30・振り " + kf("O", "skewDeg") + "°): " + (go == null ? note : note));
                    continue;
                }
                line(1, dn + " cross「" + at + "」(型 " + kt + "): 置き場が建った物から引けない ── 据えない");
                Wait(dn + " cross「" + at + "」(型 " + kt + "): 暗渠の口・溝の横断は線が無い");
            }
            var obd = Has(dr, "outletBuild") ? O(dr["outletBuild"]) : null;
            if (obd != null && obd.Count > 0)
            {
                string kt = Sk(obd, "kata");
                if (kt == "N" && Has(obd, "at") && Regex.IsMatch(Sk(obd, "at"), @"Oku_Hei|[A-Za-z]+_Hei"))
                {
                    // 水抜き = 吐口へ落ちる区間の尻を、塀の内面へ当てた所(塀の駒の実メッシュ)
                    MzSeg last = null; foreach (var g in segs) if (g.drain == dn && g.to == "outletBuild" && g.built) last = g;
                    var wn = Regex.Match(Sk(obd, "at"), @"([A-Za-z][A-Za-z0-9_]*_Hei)").Groups[1].Value;
                    var pcs = new List<GameObject>(); foreach (var root in new[] { Group("OkuHei"), Group("Kakoi") }) pcs.AddRange(piecesByPrefix(wn, root));
                    string np = EdoBuild.AssetByName("Own", "DoiMizunuki");
                    if (last == null || pcs.Count == 0 || np == null || !Exists(np))
                    { line(2, dn + " 水抜き(N・" + wn + "): " + (last == null ? "落ちる溝が建っていない" : pcs.Count == 0 ? "塀の駒が建っていない" : "部材 Own.DoiMizunuki が無い") + " ── 建てない"); Wait(dn + " 水抜き: " + (last == null ? "落ちる溝が建っていない" : pcs.Count == 0 ? "塀 " + wn + " が建っていない" : "Own.DoiMizunuki が無い(部材方)")); }
                    else
                    {
                        var pl = last.lines[last.lines.Count - 1]; var end = pl[pl.Count - 1];
                        // 塀の面 = 尻の側の実メッシュの面
                        Vector2 nrm; string w2; var face = EdoBuild.WallFaceLine(pcs, end, 0.1f, 1.2f, 0.5f, out nrm, out w2);
                        if (face == null) { line(2, dn + " 水抜き: 塀 " + wn + " の面が測れない(" + w2 + ")"); }
                        else
                        {
                            float dist; float sF = EdoBuild.NearestS(face, end, out dist); Vector2 d; var on = EdoBuild.PointAt(face, sF, out d);
                            float bottom = Has(obd, "bottom") ? F(obd["bottom"]) : last.prof[last.prof.Count - 1].Tail;
                            float fl, sk; var go = EdoBuild.PlaceMasu(grp, dn + "_Mizunuki", np, on, -nrm, bottom + 1f, bottom, out fl, out sk);
                            float tailB = last.prof[last.prof.Count - 1].Tail;
                            bool okH = go != null && fl <= tailB + 1e-4f;
                            line(okH ? (dist > 0.6f ? 1 : 0) : 2, dn + " 水抜き(N): " + wn + " の内面へ・口の底 " + fl.ToString("F3") + "(欄 " + bottom.ToString("F2") + ")≤ 落ちる溝の尻の底 " + tailB.ToString("F3") + (okH ? "【硬 ⭕】" : "【硬 ✗】")
                                 + "・溝の尻と塀の面の離れ " + dist.ToString("F2") + "m" + (dist > 0.6f ? "【柔 ⚠ 溝の尻が塀へ届かない】" : ""));
                        }
                    }
                }
                else if (!string.IsNullOrEmpty(kt))
                { line(1, dn + " 吐口(型 " + kt + "「" + (Sk(obd, "at") ?? "") + "」): 置き場が建った物から引けない ── 据えない"); Wait(dn + " 吐口(型 " + kt + "): " + (Sk(obd, "at") ?? Sk(obd, "to") ?? "") + " ── 線が無い"); }
            }
        }

        // ---- 暗渠(溝が塀・布石・石段の足元の下を抜ける所)── 蓋石 L を溝の向きに並べ、蓋の天端を足元へ(EdoBuild.LayAnkyoUnder・硬い)
        //   ⭐ 塀は S2、溝は S9 で据わる ── 後から据えた溝の駒が塀の足元の下を掘り、縁の皮(4b)が溝の天端へ下がって塀が浮いた(奥の塀 Oku_Hei_Roka 0.16〜0.20・
        //   蔵の石段 Danishi_01 0.705 ── EDO-0533 第10巡)。江戸の作りは、塀の下を石の蓋で抜ける。⚠ 流した後に 4b 縁の皮を流し直す(蓋は群 Mizo)
        {
            var over = new List<GameObject>();
            foreach (var root in new[] { Group("OkuHei"), Group("Kakoi") })
                foreach (Transform c in root)
                    if (c.gameObject.activeInHierarchy && (root.name == "OkuHei" || c.name.Contains("_Hei") || c.name.EndsWith("_ishi"))) over.Add(c.gameObject);   // 塀と布石(表長屋の躯体は軒が溝の上に掛かるので入れない)
            // 渡廊下の柱と縁の束も(溝が廊下・縁の下をくぐる所は蓋石で抜ける ── 第27巡: 廊下 L_OkuNagatsubone の柱 0.252/0.124・長局の束 0.159 が溝 D3 seg1 の上で浮いた)
            foreach (Transform top in Group("Mizo").parent)
            {
                if (!top.gameObject.activeInHierarchy || !(top.name.StartsWith("L_") || top.name == "Buildings")) continue;
                foreach (var t in top.GetComponentsInChildren<Transform>())
                    if (t.gameObject.activeInHierarchy && (t.name == "Goten_Column" || t.name.StartsWith("Goten_EnTsuka")) && t.GetComponent<MeshFilter>() != null) over.Add(t.gameObject);
            }
            foreach (Transform k in Group("Fuzoku/Kaidan"))
            {
                if (!k.gameObject.activeInHierarchy) continue;
                if (k.GetComponent<MeshFilter>() != null || PrefabUtility.IsAnyPrefabInstanceRoot(k.gameObject)) over.Add(k.gameObject);
                else foreach (Transform kk in k) if (kk.gameObject.activeInHierarchy) over.Add(kk.gameObject);
            }
            var katas = new List<string>(); foreach (var g in segs) if (g.built && !katas.Contains(g.kata)) katas.Add(g.kata);
            foreach (var kt in katas)
            {
                var chans = new List<GameObject>(); foreach (var g in segs) if (g.built && g.kata == kt) foreach (var pc in g.pieces) if (pc != null) chans.Add(pc);
                string kk = kt;
                EdoBuild.AnkyoRep ar;
                var lids = EdoBuild.LayAnkyoUnder(grp, "Ankyo_" + kt, chans, over, tt => EdoBuild.AssetByName("Own", "DoiFutaishiFor", kk, tt), new[] { 0.20f, 0.15f }, EdoBuild.Ground, out ar,
                                                  coverHollow: true);   // 布石の下端が溝の縁と同じ高さで窪みを跨ぐ所にも蓋(奥の塀 Oku_Hei_0_0〜0_4_ishi が D2 の窪みの上で 0.13〜0.18 浮いた・EDO-0533 第11巡)
                if (ar.lids == 0 && ar.refused == 0) { if (ar.notes.Count > 0 && chans.Count > 0) line(1, "暗渠(型 " + kt + "): " + string.Join(" / ", ar.notes.ToArray())); continue; }
                line(ar.refused > 0 ? 2 : 0, "暗渠(型 " + kt + "): " + ar.Summary() + "・蓋の天端 − 足元 最悪 " + ar.worstTop.ToString("F3") + "m【硬 " + (ar.refused > 0 ? "✗" : "⭕") + " 足元が溝の上で浮かない】"
                     + (ar.notes.Count > 0 ? "\n      " + string.Join("\n      ", ar.notes.ToArray()) : ""));
                foreach (var w in ar.refusedWhy) { line(2, "  暗渠(型 " + kt + ") 据えない: " + w); Wait("暗渠: " + w); }
            }
            // 飛石・沓脱・手水の石(Niwa/Tenkei)が溝の上に掛かる所にも同じ蓋(延段・飛石が雨落ちを渡る所は蓋石 ── 欄 lids の「延段・R07・R08 を横切る所」と同じ作り)。
            //   石は薄い(0.1〜0.25)ので足元と読む厚みの下限を 0.05 へ下げる(塀の笠を外すための既定 0.3 では石の下面を引けない)。
            //   ⭐ 飛石 Tobi_Shoin_0 が D1 seg2 の上で 0.147・Tobi_Naga_0 が D3 seg1 の上で 0.249 浮いた(EDO-0533 第12巡)── 置き方は EdoBuild.LayAnkyoUnder
            var overT = new List<GameObject>();
            foreach (Transform c in Group("Niwa/Tenkei")) if (c.gameObject.activeInHierarchy && c.GetComponentInChildren<MeshFilter>() != null) overT.Add(c.gameObject);
            if (overT.Count > 0)
                foreach (var kt in katas)
                {
                    var chans = new List<GameObject>(); foreach (var g in segs) if (g.built && g.kata == kt) foreach (var pc in g.pieces) if (pc != null) chans.Add(pc);
                    string kk = kt;
                    EdoBuild.AnkyoRep ar;
                    EdoBuild.LayAnkyoUnder(grp, "AnkyoT_" + kt, chans, overT, tt => EdoBuild.AssetByName("Own", "DoiFutaishiFor", kk, tt), new[] { 0.20f, 0.15f }, EdoBuild.Ground, out ar,
                                           coverHollow: true, minSolid: 0.05f);
                    if (ar.lids == 0 && ar.refused == 0) continue;
                    line(ar.refused > 0 ? 2 : 0, "暗渠・石の下(型 " + kt + "): " + ar.Summary() + "・蓋の天端 − 足元 最悪 " + ar.worstTop.ToString("F3") + "m【硬 " + (ar.refused > 0 ? "✗" : "⭕") + " 石の足元が溝の上で浮かない】"
                         + (ar.notes.Count > 0 ? "\n      " + string.Join("\n      ", ar.notes.ToArray()) : ""));
                    foreach (var w in ar.refusedWhy) { line(2, "  暗渠・石の下(型 " + kt + ") 据えない: " + w); Wait("暗渠・石の下: " + w); }
                }
        }

        // ---- 取り合いの検め(建った物どうしの離れ)
        for (int di = 0; di < drains.Count; di++)
        {
            var dr = O(drains[di]); string dn = (Sk(dr, "name") ?? "").Split(' ')[0];
            foreach (var o in A(Gk(dr, "toriai")) ?? new List<object>())
            {
                var t = O(o); string with = Sk(t, "with") ?? ""; bool hard = Has(t, "hard") && t["hard"] is bool && (bool)t["hard"];
                AuditKeys(t, "排水 " + dn + " toriai", "with", "rule", "hard", "fall", "clearM", "clearKen", "offM", "bottomMinBelowFoot", "innerWAlt", "bandKen", "lip", "dropMin");
                var built = new List<MzSeg>(); foreach (var g in segs) if (g.drain == dn && g.built) built.Add(g);
                if (built.Count == 0) continue;
                var fm = Regex.Match(with, @"\b(F\d\d)\b");
                if (fm.Success && (Has(t, "clearM") || (Sk(t, "rule") ?? "").Contains("柱の根")))
                {
                    // 柵の柱の根(駒の下端から 0.3m の実メッシュ)と溝の肩の離れ
                    var pcs = piecesByPrefix(fm.Groups[1].Value, Group("Fuzoku/Saku"));
                    if (pcs.Count == 0) { Wait(dn + " 取り合い " + with + ": 柵が建っていない ── 未検査"); continue; }
                    float need = Has(t, "clearM") ? F(t["clearM"]) : 0f, worst = float.MaxValue;
                    foreach (var pc in pcs)
                    {
                        float y0 = EdoBuild.RB(pc).min.y;
                        foreach (var p in EdoBuild.Body(pc.transform, 2000, false))
                        {
                            if (p.y > y0 + 0.3f) continue; var q = new Vector2(p.x, p.z);
                            foreach (var g in built) foreach (var pl in g.lines) { float dd; EdoBuild.NearestS(pl, q, out dd); worst = Mathf.Min(worst, dd - g.halfW); }
                        }
                    }
                    bool ok = worst >= need - 1e-4f;
                    line(ok ? 0 : (hard ? 2 : 1), dn + " 取り合い " + with + ": 柱の根と溝の肩の離れ 最小 " + worst.ToString("F3") + "m(" + (hard ? "硬" : "柔") + " ≥ " + need.ToString("F2") + ")");
                    continue;
                }
                var em = Regex.Match(with, @"辺\s*(\d+)");
                if (em.Success && Has(t, "clearM"))
                {
                    int ei = int.Parse(em.Groups[1].Value); var P = Poly; if (ei >= P.Length) continue;
                    float need = F(t["clearM"]), worst = float.MaxValue;
                    foreach (var g in built) foreach (var pl in g.lines) foreach (var q in pl) worst = Mathf.Min(worst, EdoGeom.DistToEdge(q, P[ei], P[(ei + 1) % P.Length]) - g.halfW);
                    line(worst >= need - 1e-4f ? 0 : (hard ? 2 : 1), dn + " 取り合い 辺" + ei + ": 溝の外縁と区画の線の離れ 最小 " + worst.ToString("F3") + "m(" + (hard ? "硬" : "柔") + " ≥ " + need.ToString("F2") + ")");
                    continue;
                }
                Wait(dn + " 取り合い「" + with + "」(" + (hard ? "硬" : "柔") + "): 未検査");
            }
        }

        // ---- 欄 hardAdd / softAdd のうち、この巡の式と測りに入っていない物は「未検査」(⛔ 合格と書かない ── 規則19)
        for (int di = 0; di < drains.Count; di++)
        {
            var dr = O(drains[di]); string dn = (Sk(dr, "name") ?? "").Split(' ')[0];
            foreach (var key in new[] { "hardAdd", "softAdd" })
                foreach (var o in A(Has(dr, key) ? dr[key] : null) ?? new List<object>())
                {
                    string t = S(o) ?? ""; if (t.Length == 0) continue;
                    // 式と測りに入っている物: 段の 1段・柵の柱の根・区画の線からの離れ
                    if (t.Contains("1段") || t.Contains("柱の根") || t.Contains("区画の線")) continue;
                    // 桝で割った区間(欄 masuPitchMaxM)の深さと埋樋は、桝の置き場を選ぶ時(EdoBuild.SplitMizoAtMasu)と埋樋の口(EdoBuild.UzumiToiMouth)で硬で測った
                    bool splitHere = false; foreach (var kvS in splitMasus) if (kvS.Key.drain == dn) splitHere = true;
                    if (splitHere && t.Contains("埋樋")) continue;
                    if (splitHere && t.Contains("型 A の深さ")) { Wait(dn + " 硬「" + t + "」: 桝で割った区間(欄 masuPitchMaxM)だけ硬で測った ── 他の型 A の区間は未検査"); continue; }
                    Wait(dn + " " + (key == "hardAdd" ? "硬" : "柔") + "「" + t + "」: 未検査(この巡の式と測りに入っていない)");
                }
        }

        sb.Insert(0, "✗ " + bad + " / ⚠ " + warn + " / ⭕ " + okN + " ── 溝の駒 " + grp.childCount + " 個(群 Mizo)。⚠ 流した後に 4b 縁の皮を流し直す\n");
        sb.Append(WaitReport());
        return sb.ToString();
    }

    /// <summary>群の下で名が <paramref name="prefix"/>(または <c>prefix_…</c>)の段を持つ駒(Stage9 の piecesByPrefix と同じ引き方)。</summary>
    /// <summary>面の取り合いで解いた桝(EdoBuild.MasuPlanOffLine)を据えた後の検め ── 測るのは据えた桝の実メッシュの外形(EdoBuild.HullXZ)。
    /// 硬: 欄 at「軒先の線の外」(軒の外周に掛からない)・欄 toriai「桝は束石の外形から d 以上離す」。満たさなければ false(呼び手は桝を据えない)。
    /// 刷るだけ: 棟側の外面と軒の辺の離れの実測(欄 d)・二つの辺の一直線からの外れ・軸の振れ・入る区間の尻と面の中央の差(欄 inlet)・溝の駒と束石の離れ(柔)。</summary>
    static bool MasuPlannedChecks9(MzMasu mz, GameObject go, EdoBuild.MasuPlan pl, string[] blds, Dictionary<string, Vector2[]> eave, List<MzSeg> segs,
                                   Func<MzSeg, MzMasu> masuOf, Func<string, string, Vector2?> masuFace, Action<int, string> line)
    {
        var hull = EdoBuild.HullXZ(go);
        if (hull == null) { line(2, mz.id + ": 据えた桝の外形が測れない ── 建てない"); return false; }
        bool ok = true;
        float inOff = float.MaxValue; foreach (var q in hull) inOff = Mathf.Min(inOff, Vector2.Dot(q - pl.onLine, pl.outDir));
        string at = Sk(mz.raw, "at") ?? "";
        if (at.Contains("軒先の線の外"))
            foreach (var kv in eave)
                if (EdoBuild.ConvexOverlap(hull, new List<Vector2>(kv.Value), 0f))
                { line(2, mz.id + ": 桝の外形が " + kv.Key + " の軒先の外周に掛かる(欄「軒先の線の外」【硬 ✗】)── 建てない"); ok = false; }
        // 束石の離れ(欄 toriai の「束石の外形から d 以上離す」── 桝について硬)
        float clear = float.NaN; Dictionary<string, object> dr = null;
        foreach (var g in segs) if (g.di == mz.di) { dr = g.dr; break; }
        if (dr != null)
            foreach (var o in A(Gk(dr, "toriai")) ?? new List<object>())
            {
                var t = O(o); if (!(Sk(t, "with") ?? "").Contains("束石")) continue;
                var mc = Regex.Match(Sk(t, "rule") ?? "", @"外形から\s*([0-9.]+)\s*以上離す");
                if (mc.Success) clear = float.Parse(mc.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
            }
        string tsukaRep = "";
        if (!float.IsNaN(clear))
        {
            var feet = new List<List<Vector2>>();
            foreach (var b in blds)
            {
                var tr = FindDeep(Group("Buildings"), b);
                if (tr == null) { line(2, mz.id + ": 棟 " + b + " が建っていない ── 束石の離れが測れない【硬 ✗】"); ok = false; continue; }
                feet.AddRange(EdoBuild.FootHullsXZ(tr, new[] { "Goten_EnTsuka", "Goten_EnKeta", "Goten_Soseki" }, 100f));
            }
            if (feet.Count == 0) tsukaRep = "・束石の離れ: 足元の駒が無い(" + string.Join("・", blds) + ")── 未検査";
            else
            {
                float gm = float.MaxValue; foreach (var fh in feet) { float gg = EdoBuild.HullGapXZ(hull, fh); if (!float.IsNaN(gg)) gm = Mathf.Min(gm, gg); }
                bool tOk = gm >= clear - 1e-4f;
                tsukaRep = "・束石の外形との離れ " + gm.ToString("F3") + "m【硬 ≥" + clear.ToString("F2") + (tOk ? " ⭕" : " ✗") + "】";
                if (!tOk) ok = false;
                // 溝の駒(この桝へ入る区間)と束石の離れ ── 欄は桝についてだけ硬なので刷るだけ
                float gs = float.MaxValue; string gsAt = null;
                foreach (var g in segs)
                {
                    if (masuOf(g) != mz) continue;
                    foreach (var pc in g.pieces) { var ph = EdoBuild.HullXZ(pc); if (ph == null) continue; foreach (var fh in feet) { float gg = EdoBuild.HullGapXZ(ph, fh); if (!float.IsNaN(gg) && gg < gs) { gs = gg; gsAt = g.id; } } }
                }
                if (gsAt != null) tsukaRep += "・溝の駒と束石の離れ 最小 " + gs.ToString("F3") + "m(" + gsAt + (gs < clear ? "【柔 ⚠ 玉石の帯を束石の際で止める作りはまだ無い】" : "") + ")";
            }
        }
        // 入る区間の尻 ↔ 欄 inlet の面の中央
        string inRep = "";
        foreach (Match im in Regex.Matches(Sk(mz.raw, "inlet") ?? "", @"(?:^|、)\s*(.+?)側の面の中央に\s*seg(\d+)"))
        {
            MzSeg sg = null; foreach (var g in segs) if (g.di == mz.di && g.si + 1 == int.Parse(im.Groups[2].Value)) sg = g;
            var fc = masuFace(mz.id, im.Groups[1].Value);
            if (sg == null || fc == null) { inRep += "・seg" + im.Groups[2].Value + " ✗ 区間か面が引けない"; continue; }
            if (!sg.built || sg.lines == null || sg.lines.Count == 0) { inRep += "・seg" + im.Groups[2].Value + " 建っていない"; continue; }
            float dd = float.MaxValue; foreach (var l in sg.lines) dd = Mathf.Min(dd, Vector2.Distance(l[l.Count - 1], fc.Value));
            inRep += "・seg" + im.Groups[2].Value + "→" + im.Groups[1].Value + "側の面の中央 " + dd.ToString("F3") + "m" + (dd <= 0.01f ? " ⭕" : " ⚠");
        }
        var mw = Regex.Match(Sk(mz.raw, "inlet") ?? "", @"口は各\s*([0-9.]+)");
        line(ok ? 0 : 2, mz.id + "(面の取り合い): 棟側の外面 − 軒の辺 " + inOff.ToString("F3") + "m(欄 " + pl.off.ToString("F2") + ")・二辺の一直線からの外れ " + pl.straightDev.ToString("F3")
             + "m・坪の中心線と辺の法線の振れ " + pl.axisSkewDeg.ToString("F1") + "°・外の面(" + (Sk(mz.raw, "outFace") ?? "outDir") + ")" + tsukaRep
             + (inRep.Length > 0 ? "・入る口" + inRep : "") + (mw.Success ? "・口の幅 " + mw.Groups[1].Value + " は桝の駒の口と未突き合わせ" : "")
             + (at.Contains("軒先の線の外") ? (ok ? "【硬 ⭕ 軒先の線の外】" : "") : ""));
        return ok;
    }

    static List<GameObject> PiecesByPrefix9(string prefix, Transform root)
    {
        var l = new List<GameObject>(); if (root == null) return l;
        foreach (var mr in root.GetComponentsInChildren<MeshRenderer>())
        {
            var t = mr.transform; bool hit = false;
            while (t != null && t != root) { if (t.name == prefix || t.name.StartsWith(prefix + "_")) { hit = true; break; } t = t.parent; }
            if (hit && mr.gameObject.activeInHierarchy) l.Add(mr.gameObject);
        }
        return l;
    }

    /// <summary>型 H(段落ち)の区間: 頭の底(始点の区間の尻・入る区間の尻 ── 線の頭から 3m 内)と尻の狙い(欄の 段 × 1段/吐口が塀の水抜きなら塀の外の道 + bottomAboveRoad)を
    /// 欄から読み、<see cref="EdoBuild.LayDanOchi"/> へ渡すだけ(⛔ 置き方をここに書かない)。線は N9 の「A から B へ最短」で向きを持つ物だけ。</summary>
    static void BuildDanOchi9(MzSeg g, Transform grp, List<KeyValuePair<MzSeg, Vector3>> solvedEnds, Func<MzSeg, List<MzSeg>> receivers, Func<MzSeg, MzMasu> masuOf,
                              Func<string, string, float> kf, Action<int, string> line)
    {
        var s = g.raw; var hl = g.rawLines[0]; Vector2 p0 = hl[0], p1 = hl[hl.Count - 1];
        if (!g.fixedDir || hl.Count != 2) { line(2, g.id + "(型 H「" + g.line + "」): 段落ちの線は「A から B へ最短」の直線だけ読む ── 建てない"); Wait(g.id + ": 段落ちの線が直線で向きを持たない"); return; }
        float head = float.NaN;
        foreach (var kv in solvedEnds)
        {
            if (kv.Key != g.fromSeg && !receivers(kv.Key).Contains(g)) continue;
            if (Vector2.Distance(new Vector2(kv.Value.x, kv.Value.y), p0) > 3f) continue;
            head = float.IsNaN(head) ? kv.Value.z : Mathf.Min(head, kv.Value.z);
        }
        string up = g.fromSeg != null ? g.fromSeg.id : "入る区間";
        if (float.IsNaN(head)) { line(2, g.id + "(型 H): 頭の底が決まらない ── " + up + " が建っていない/その尻が線の頭から 3m 外 ── 建てない"); Wait(g.id + ": 段落ちの頭の底が決まらない(" + up + " の尻の底が要る)"); return; }
        int steps = Has(s, "steps") ? (int)F(s["steps"]) : 0;
        float riseMax = Has(s, "riseMax") ? F(s["riseMax"]) : kf("H", "riseMax"); if (float.IsNaN(riseMax)) riseMax = 0.45f;
        float tailWant = float.NaN, tailMin = float.NaN; string tailHow = null;
        if (Has(s, "rise") && steps > 0) { tailWant = head - steps * F(s["rise"]); tailHow = "段 " + steps + " × 1段 " + F(s["rise"]).ToString("F2"); }
        else if (g.to == "outletBuild" && Has(g.dr, "outletBuild"))
        {
            var ob = O(g.dr["outletBuild"]); var wm = Regex.Match(Sk(ob, "at") ?? "", @"([A-Za-z][A-Za-z0-9_]*_Hei)");
            if (wm.Success && Has(ob, "bottomAboveRoad"))
            {
                var pcs = new List<GameObject>(); foreach (var root in new[] { Group("OkuHei"), Group("Kakoi") }) pcs.AddRange(PiecesByPrefix9(wm.Groups[1].Value, root));
                if (pcs.Count == 0) { line(2, g.id + "(型 H): 塀 " + wm.Groups[1].Value + " が建っていない ── 尻の高さ(道 + " + F(ob["bottomAboveRoad"]).ToString("F2") + ")が決まらない・建てない"); Wait(g.id + ": 塀 " + wm.Groups[1].Value + " が建っていない"); return; }
                string w2; float road = EdoBuild.GroundBeyondWall(pcs, p1, (p1 - p0).normalized, GroundY, out w2);
                if (float.IsNaN(road)) { line(2, g.id + "(型 H): 塀の外の道の高さが測れない(" + w2 + ")── 建てない"); Wait(g.id + ": 塀の外の道が測れない"); return; }
                tailWant = tailMin = road + F(ob["bottomAboveRoad"]);
                tailHow = "塀 " + wm.Groups[1].Value + " の外 0.3m の道 " + road.ToString("F3") + " + " + F(ob["bottomAboveRoad"]).ToString("F2") + (steps > 0 ? "・段 " + steps : "");
            }
        }
        if (float.IsNaN(tailWant)) { line(2, g.id + "(型 H): 尻の高さが欄から決まらない(段 × 1段 も 塀の外の道 + d も無い)── 建てない"); Wait(g.id + ": 段落ちの尻の高さの欄が無い"); return; }
        var R = EdoBuild.LayDanOchi(grp, g.id.Replace(" ", "_"), p0, p1, head, tailWant, steps, riseMax, tailMin, r => EdoBuild.AssetByName("Own", "DoiDanOchi", r));
        if (!R.ok) { line(2, g.id + "(型 H 段落ち): 硬い条件を満たせない ── 据えない: " + R.hard); Wait(g.id + ": 段落ち " + R.hard); return; }
        g.pieces.AddRange(R.pieces); g.built = R.pieces.Count > 0; g.lines = new List<List<Vector2>> { new List<Vector2> { p0, p1 } };
        var sp0 = EdoBuild.StepPieceOf(EdoBuild.AssetByName("Own", "DoiDanOchi", 0.15f)); g.halfW = sp0.ok ? 0.5f * (sp0.xMax - sp0.xMin) : float.NaN;
        g.prof.Add(new EdoBuild.MizoProfile { s = new[] { 0f, R.length }, bottom = new[] { head, R.tailY }, ground = new[] { GroundY(p0.x, p0.y), GroundY(p1.x, p1.y) }, p = new[] { p0, p1 }, length = R.length });
        solvedEnds.Add(new KeyValuePair<MzSeg, Vector3>(g, new Vector3(p1.x, p1.y, R.tailY)));
        var ms = masuOf(g); if (ms != null) { ms.inEnds.Add(p1); ms.inBottoms.Add(R.tailY); }
        var rs = new List<string>(); foreach (var x in R.rises) rs.Add(x.ToString("F2"));
        line(R.soft.Length > 0 ? 1 : 0, g.id + "(型 H 段落ち): " + R.pieces.Count + " 駒 ── 平面 " + R.length.ToString("F2") + "m・段 " + R.steps + "(1段 " + string.Join("・", rs.ToArray()) + "・踏面 " + R.pitch.ToString("F2")
             + ")・底 " + head.ToString("F3") + "(" + up + " の尻)→ " + R.tailY.ToString("F3") + "(尻の狙い " + tailHow + ")【硬 ⭕ 1段 ≤ " + riseMax.ToString("F2") + "・段鼻の線" + (float.IsNaN(tailMin) ? "" : "・尻 ≥ 下限") + "】"
             + (R.soft.Length > 0 ? "【柔 ⚠ " + R.soft + "】" : ""));
    }

    /// <summary>区間の欄 drop(型 I 張り石の落とし): 始点 = 座の「辺N 側の縁」のうち受ける区間に最も近い所・終点 = 受ける区間の線(垂線の足)を引き、
    /// 頭 = 座の縁の地盤(この区間の尻の底が低ければそれ)・法尻 = 受ける区間の上の地盤・下限 = 受ける区間の底 で <see cref="EdoBuild.LayHariOtoshi"/> へ渡すだけ。</summary>
    static void BuildHariOtoshi9(MzSeg g, Transform grp, Dictionary<string, MzSeg> byId, Func<int, string> edgeChk, Func<string, string, float> kf, Action<int, string> line)
    {
        var dp = O(g.raw["drop"]); string kt = Sk(dp, "kata") ?? "", fr = Sk(dp, "from") ?? "", to = Sk(dp, "to") ?? "";
        AuditKeys(dp, "排水 " + g.id + " drop", "kata", "from", "to");
        if (kt != "I") { line(1, g.id + " 落とし(型 " + kt + "): 型 I だけ読む ── 据えない"); Wait(g.id + ": 落としの型 " + kt + " は読まない"); return; }
        var mz = Regex.Match(fr, @"^座\s*((?:Za_[A-Za-z0-9_]+\s*・?\s*)+)の辺(\d+)\s*側の縁");
        var mt = Regex.Match(to, @"^(?:(D\d+)\s*)?seg(\d+)$");
        if (!mz.Success || !mt.Success) { line(2, g.id + " 落とし(I)「" + fr + " → " + to + "」: 始点か終点の言い方が読めない ── 建てない"); Wait(g.id + ": 落としの始点・終点が読めない"); return; }
        int ei = int.Parse(mz.Groups[2].Value); string ew = edgeChk(ei);
        if (ew != null) { line(2, g.id + " 落とし(I): " + ew + " ── 建てない"); Wait(g.id + ": " + ew); return; }
        var outN = -EdoGeom.InwardNormal(Poly, ei); var chains = new List<List<Vector2>>();
        foreach (Match t in Regex.Matches(mz.Groups[1].Value, @"Za_[A-Za-z0-9_]+"))
        {
            float zy; var zp = TerracePolyW(t.Value, out zy);
            if (zp == null) { line(2, g.id + " 落とし(I): 座 " + t.Value + " の多角形が欄に無い ── 建てない"); Wait(g.id + ": 座 " + t.Value + " が引けない"); return; }
            chains.AddRange(EdoBuild.PolyEdgesToward(zp, outN, 0.8f));
        }
        if (chains.Count == 0) { line(2, g.id + " 落とし(I): 座の辺" + ei + " 側の縁が無い ── 建てない"); Wait(g.id + ": 座の辺" + ei + " 側の縁が無い"); return; }
        string hid = (mt.Groups[1].Success && mt.Groups[1].Value.Length > 0 ? mt.Groups[1].Value : g.drain) + " seg" + mt.Groups[2].Value;
        MzSeg h; byId.TryGetValue(hid, out h);
        if (h == null || !h.built || h.lines == null) { line(2, g.id + " 落とし(I): 受ける溝 " + hid + " が建っていない ── 法尻の高さが決まらない・建てない"); Wait(g.id + ": 落としの受ける溝 " + hid + " が建っていない"); return; }
        float dist; var lk = EdoBuild.ShortestLink(chains, h.lines, out dist);
        if (lk == null) { line(2, g.id + " 落とし(I): 座の縁と " + hid + " の最短が測れない"); return; }
        Vector2 p0 = lk[0], p1 = lk[1];
        float top = GroundY(p0.x, p0.y), foot = GroundY(p1.x, p1.y), tailMin = float.NaN; string gapNote = "";
        if (g.built && g.prof.Count > 0)
        {
            float bd = float.MaxValue; int bi = -1;
            for (int i = 0; i < g.lines.Count; i++) { float dd = Vector2.Distance(g.lines[i][g.lines[i].Count - 1], p0); if (dd < bd) { bd = dd; bi = i; } }
            if (bi >= 0 && bi < g.prof.Count) { top = Mathf.Min(top, g.prof[bi].Tail); gapNote = "・この区間の尻と落としの頭の離れ " + bd.ToString("F2") + "m" + (bd > g.halfW + 0.3f ? "【柔 ⚠ 届かない】" : ""); }
        }
        for (int i = 0; i < h.lines.Count && i < h.prof.Count; i++) { float dd; float sAt = EdoBuild.NearestS(h.lines[i], p1, out dd); if (dd < 0.5f) tailMin = float.IsNaN(tailMin) ? h.prof[i].At(sAt) : Mathf.Max(tailMin, h.prof[i].At(sAt)); }
        float riseMax = kf("I", "riseMax"); if (float.IsNaN(riseMax)) riseMax = 0.30f;
        var R = EdoBuild.LayHariOtoshi(grp, g.id.Replace(" ", "_") + "_Otoshi", p0, p1, top, foot, riseMax, tailMin, (r, n) => EdoBuild.AssetByName("Own", "DoiHariOtoshi", r, n));
        if (!R.ok) { line(2, g.id + " 落とし(型 I): 硬い条件を満たせない ── 据えない: " + R.hard); Wait(g.id + ": 張り石の落とし " + R.hard); return; }
        line(R.soft.Length > 0 ? 1 : 0, g.id + " 落とし(型 I 張り石): " + R.pieces.Count + " 駒 ── 座の辺" + ei + " 側の縁 → " + hid + "・平面 " + R.length.ToString("F2") + "m・段 " + R.steps + "(1段 " + (R.rises.Count > 0 ? R.rises[0].ToString("F3") : "-")
             + "・踏面 " + R.pitch.ToString("F2") + ")・天端 " + top.ToString("F3") + "→" + R.tailY.ToString("F3") + gapNote + "【硬 ⭕ 1段 ≤ " + riseMax.ToString("F2") + (float.IsNaN(tailMin) ? "" : "・尻の天端 ≥ 受ける溝の底 " + tailMin.ToString("F3")) + "】"
             + (R.soft.Length > 0 ? "【柔 ⚠ " + R.soft + "】" : "") + "・法尻の水叩きは溝へ落とすので据えない");
    }

    /// <summary>型 J(玉石の受け)の区間: 線「受け: <条件> のうち <起点> に最も近い所に a×b 間」を読み、起点の桝(据えた位置)・指名の辺・勾配の上限を
    /// <see cref="EdoBuild.PlaceUke"/>(置き場は PlaceBest ── 辺からの離れ・勾配・区画の内は硬い条件・起点に近いは狙い)へ渡すだけ。</summary>
    static void BuildUke9(MzSeg g, Transform grp, Dictionary<string, Vector2> masuAt, Func<int, string> edgeChk, Action<int, string> line)
    {
        string core = Regex.Replace(g.line, @"[((][^))]*[))]", "").Trim();
        var ms = Regex.Match(core, @"1\s*:\s*([0-9.]+)\s*より緩い");
        var me = Regex.Match(core, @"((?:辺\d+\s*[・、]?\s*)+)から\s*([0-9.]+)\s*間\s*以上内");
        var mo = Regex.Match(core, @"(D\d+)\s*masu\[(\d+)\]\s*に最も近い");
        var mz = Regex.Match(core, @"([0-9.]+)\s*×\s*([0-9.]+)\s*間");
        if (!core.StartsWith("受け") || !ms.Success || !me.Success || !mo.Success || !mz.Success)
        { line(2, g.id + "(型 J「" + g.line + "」): 受けの条件が読めない(勾配・辺からの離れ・起点・大きさの四つが要る)── 建てない"); Wait(g.id + ": 受けの条件が読めない"); return; }
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        float a = float.Parse(mz.Groups[1].Value, ci), b = float.Parse(mz.Groups[2].Value, ci);
        if (!(Mathf.Abs(Mathf.Min(a, b) - 2f) < 1e-3f && Mathf.Abs(Mathf.Max(a, b) - 3f) < 1e-3f))
        { line(2, g.id + "(型 J): 大きさ " + a + "×" + b + "間 の受けの駒が無い(Own.DoiTamaUke は 2×3間)── 建てない"); Wait(g.id + ": 受けの駒 " + a + "×" + b + "間 が要る(部材方)"); return; }
        string mid = mo.Groups[1].Value + " masu[" + mo.Groups[2].Value + "]";
        if (!masuAt.ContainsKey(mid)) { line(2, g.id + "(型 J): 起点の桝 " + mid + " が据わっていない ── 置き場が選べない・建てない"); Wait(g.id + ": 起点の桝 " + mid + " が据わっていない"); return; }
        var P = Poly; var keepEdges = new List<Vector2[]>(); var en = new List<string>();
        foreach (Match em in Regex.Matches(me.Groups[1].Value, @"辺(\d+)"))
        {
            int ei = int.Parse(em.Groups[1].Value); string ew = edgeChk(ei);
            if (ew != null) { line(2, g.id + "(型 J): " + ew + " ── 建てない"); Wait(g.id + ": " + ew); return; }
            keepEdges.Add(new[] { P[ei], P[(ei + 1) % P.Length] }); en.Add("辺" + ei);
        }
        string path = EdoBuild.AssetByName("Own", "DoiTamaUke");
        if (path == null || !Exists(path)) { line(2, g.id + "(型 J): 部材が無い " + (path ?? "Own.DoiTamaUke が未登録") + " ── 建てない"); Wait(g.id + ": 受けの駒 Own.DoiTamaUke が無い(部材方)"); return; }
        float keepKen = float.Parse(me.Groups[2].Value, ci), slopeMax = 1f / float.Parse(ms.Groups[1].Value, ci);
        var tally = new EdoBuild.SeiyakuTally(); string note;
        var go = EdoBuild.PlaceUke(grp, g.id.Replace(" ", "_") + "_Uke", path, masuAt[mid], P, keepEdges, keepKen * Grid.ken, slopeMax, GroundY, tally, out note);
        if (go == null) { line(2, g.id + "(型 J 受け): " + note + " ── 建てない" + tally.Summary()); Wait(g.id + ": 受けの置き場 ── " + note); return; }
        g.built = true; g.pieces.Add(go);
        line(0, g.id + "(型 J 受け 2×3間): " + note + "【硬 ⭕ 区画の内・" + string.Join("・", en.ToArray()) + " から " + keepKen + "間 以上内・足元の勾配 ≤ 1:" + ms.Groups[1].Value + "】【柔 起点 " + mid + " に近い ── 硬い条件を通った中で最も近い所】" + tally.Summary());
    }

    static string[] ToArr(MatchCollection mc) { var l = new List<string>(); foreach (Match m in mc) l.Add(m.Value); return l.ToArray(); }
}
