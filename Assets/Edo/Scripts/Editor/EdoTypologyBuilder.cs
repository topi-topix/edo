// 類型ビルダー — 区画の形(parcels.json)と類型表(typology.json)から、一本で建てる。
//   設計: docs/typology-builder.md ／ 関門: Tools/Sashizu/typology_check.py
//
// ⭐ **区画は「手作り」と「類型」に分かれない**(2026-09-19 施主指摘)。全区画をまず類型で建て、
//    史料が取れた欄から上書きする。`built: hand` は「もう図を起こして建てた」という状態の印で、
//    格の違いではない。
//
// ⛔ このファイルに座標を書かない(規則11)。区画は EdoParcels.Get、径数は typology.json、
//    パスは EdoAssets.cs(規則12)。
// ⛔ 辺番号を表に書かない(規則5)。どの辺が道に面し、どの辺が隣と共有かは**幾何から解く** —
//    既存の街区ビルダーは辺番号を手で振っていて、区画に頂点が1つ増えるたびに総崩れした
//    (EdoNishiTameikeBuilder の「2026-08-26 json採用で頂点+1、辺indexを再採番」)。
//
// ⭐ **置き方はこのファイルに書かない**(規則21・2026-09-20 施主裁定)。部材を置く・測る・突き付ける・
//    接地箇所を測って据えるのは `EdoBuild` の関数だけ。ここに書くのは「どの類型が何をどこへ」だけで、
//    据え方の算術(外接箱+定数・底を地面に・ピボットの座)は一切書かない。
//    順は置き方の4手: ①門構えを先に据える ②塀は門構えの実測の開口へ ③高さは接地箇所を測って
//    ④事後に寄せる関数を持たない。→ unity-buke-yashiki/references/sashizu.md §3f
//
// ⚠ NagayaRun / DobeiRun は既知の欠陥込みで EdoNishiTameikeBuilder に置かれている(EdoBuild の冒頭注記)。
//    当面はそこを呼ぶ。街区ビルダーが退場するとき EdoBuild へ移す(EDO-0293 の④・積み残し)。

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class EdoTypologyBuilder
{
    const float ES = 1.818f;          // edogoyomi の倍率(江戸間1間)
    const float KEN = 1.818f;
    const float SETBACK = 6.0f;       // 囲いの内側から主屋までの引き(m)
    const float PROBE = 3.0f;         // 辺の外側をどれだけ出て隣を探すか(m)
    const float MIN_BLDG_GAP = 2.0f;  // 棟どうしの最小離れ(m)
    const int   VERTS = 800;          // 接地箇所を測るときの頂点の間引きの上限(79区画を一度に建てるため)

    static string Root { get { return Directory.GetParent(Application.dataPath).FullName; } }
    static string TablePath { get { return Path.Combine(Root, "docs/Sashizu/typology.json"); } }

    // ───────────────────────── 類型表 ─────────────────────────
    public class Spec
    {
        public string id, type, built, note, source;
        public string rank, yashiki, kind, gate, bansho, enclosure, garden, surface, fence, building;
        public string front;                 // 8方位。null ならビルダーが接道辺から採る
        public int kura, units, koku, houses;
        public int maguchiKen, depthKen;
        public bool twoSided, jishinban, inari;
        public bool kuri, yagura, shoro, sanmon;
        public Dictionary<string, object> raw;
        public bool Hand { get { return built == "hand"; } }
    }

    static Dictionary<string, Spec> _table;
    public static Dictionary<string, Spec> Table { get { if (_table == null) LoadTable(); return _table; } }

    static string S(Dictionary<string, object> d, string k)
    {
        object v; if (!d.TryGetValue(k, out v) || v == null) return null; return v.ToString();
    }
    static int I(Dictionary<string, object> d, string k, int dflt)
    {
        object v; if (!d.TryGetValue(k, out v) || v == null) return dflt;
        double o; if (double.TryParse(v.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out o)) return (int)o;
        return dflt;
    }
    static bool Bo(Dictionary<string, object> d, string k, bool dflt)
    {
        object v; if (!d.TryGetValue(k, out v) || v == null) return dflt;
        bool o; if (bool.TryParse(v.ToString(), out o)) return o; return dflt;
    }

    public static void LoadTable()
    {
        _table = new Dictionary<string, Spec>();
        if (!File.Exists(TablePath)) { Debug.LogError("類型表が無い: " + TablePath); return; }
        var root = EdoMiniJson.Parse(File.ReadAllText(TablePath)) as Dictionary<string, object>;
        if (root == null) { Debug.LogError("類型表が読めない: " + TablePath); return; }
        object ps; if (!root.TryGetValue("parcels", out ps)) { Debug.LogError("類型表に parcels が無い"); return; }
        var dict = ps as Dictionary<string, object>;
        foreach (var kv in dict)
        {
            var d = kv.Value as Dictionary<string, object>; if (d == null) continue;
            var s = new Spec
            {
                id = kv.Key, raw = d,
                type = S(d, "type"), built = S(d, "built"), note = S(d, "note"), source = S(d, "source"),
                rank = S(d, "rank"), yashiki = S(d, "yashiki"), kind = S(d, "kind"),
                gate = S(d, "gate"), bansho = S(d, "bansho"), enclosure = S(d, "enclosure"),
                garden = S(d, "garden"), surface = S(d, "surface"), fence = S(d, "fence"),
                building = S(d, "building"), front = S(d, "front"),
                kura = I(d, "kura", 0), units = I(d, "units", 1), koku = I(d, "koku", 0),
                houses = I(d, "houses", 0), maguchiKen = I(d, "maguchi_ken", 5), depthKen = I(d, "depth_ken", 18),
                twoSided = Bo(d, "two_sided", false), jishinban = Bo(d, "jishinban", false),
                inari = Bo(d, "inari", false),
                kuri = Bo(d, "kuri", true), yagura = Bo(d, "yagura", false),
                shoro = Bo(d, "shoro", false), sanmon = Bo(d, "sanmon", false),
            };
            _table[kv.Key] = s;
        }
    }

    // ───────────────────────── 辺の素性を幾何から解く ─────────────────────────
    public enum EdgeKind { Road, Shared }

    public class Edge
    {
        public int i; public Vector2 a, b, mid, outward; public float len;
        public EdgeKind kind; public string neighbour; public bool mine;
    }

    static Vector2 Centroid(Vector2[] poly)
    {
        var c = Vector2.zero; foreach (var p in poly) c += p; return c / poly.Length;
    }

    static Vector2 Outward(Vector2[] poly, int i)
    {
        return -EdoGeom.InwardNormal(poly, i);
    }

    /// <summary>辺ごとに「道に面するか、隣の区画と共有か」を実際の区画の形から決める。
    /// 共有辺は id の辞書順で小さい方が持つ(決定的。建てる順に依らない)。</summary>
    public static List<Edge> Edges(string id)
    {
        var poly = EdoParcels.Get(id);
        var others = EdoParcels.All.Where(p => p.id != id && p.pts.Count >= 3).ToList();
        var outp = new List<Edge>();
        for (int i = 0; i < poly.Length; i++)
        {
            var a = poly[i]; var b = poly[(i + 1) % poly.Length];
            if ((b - a).magnitude < 0.05f) continue;           // 重複点(json に長さ0の辺がある)
            var e = new Edge { i = i, a = a, b = b, len = (b - a).magnitude };
            e.mid = (a + b) * 0.5f; e.outward = Outward(poly, i);
            e.kind = EdgeKind.Road; e.mine = true;
            // 辺の 1/4・1/2・3/4 の外側を突いて、隣の区画に入るか見る
            int hit = 0; string who = null;
            foreach (var t in new[] { 0.25f, 0.5f, 0.75f })
            {
                var p = Vector2.Lerp(a, b, t) + e.outward * PROBE;
                foreach (var o in others)
                    if (EdoGeom.PIP(o.Poly, p)) { hit++; who = o.id; break; }
            }
            if (hit >= 2)
            {
                e.kind = EdgeKind.Shared; e.neighbour = who;
                // 決定的な持ち主: id の辞書順で小さい方。⛔ ただし**入れ子**(明地の中の干場・矢場)は別 —
                //   内側の区画が自分の囲いを持たないと、拝借地が柵なしで明地に溶ける。
                var nb = EdoParcels.Find(who);
                bool nested = nb != null && EdoGeom.PIP(nb.Poly, Centroid(poly));
                e.mine = nested || string.CompareOrdinal(id, who) < 0;
            }
            outp.Add(e);
        }
        return outp;
    }

    static readonly string[] DIR_NAME = { "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW" };
    static Vector2 DirVec(string d)
    {
        int k = Array.IndexOf(DIR_NAME, d); if (k < 0) return Vector2.zero;
        float deg = k * 22.5f;                       // N=+Z から時計回り
        return new Vector2(Mathf.Sin(deg * Mathf.Deg2Rad), Mathf.Cos(deg * Mathf.Deg2Rad));
    }

    /// <summary>表門を載せる辺。
    /// ⭐ **史料で読めた方位は、長さの都合より強い。**安部摂津守の表門は 8m の袋小路の突き当りで
    ///    (切絵図の実見)、長屋門 22.5m は載らない — それでも門はそこにある。長さで弾くと史実が消える。
    ///    載らない分の納め(両翼を塀の背後へ隠す)は**建ててから実メッシュで解く**(規則5)。
    /// ⛔ 方位が無いときだけ長さで選ぶ。区画の隅の切れ端に門を押し込まないため。</summary>
    public static Edge FrontEdge(Spec s, List<Edge> edges) { string w; return FrontEdge(s, edges, out w); }

    public static Edge FrontEdge(Spec s, List<Edge> edges, out string warn)
    {
        warn = null;
        float need = GateWidth(s) * 1.25f;
        var roads = edges.Where(e => e.kind == EdgeKind.Road).ToList();
        if (roads.Count == 0) { roads = edges; warn = "四方を区画に囲まれていて接道辺が無い — 共有辺に門を開く"; }
        var want = s.front != null ? DirVec(s.front) : Vector2.zero;
        if (want != Vector2.zero)
        {
            var aligned = roads.Where(e => Vector2.Dot(e.outward.normalized, want) > 0.707f)
                               .OrderByDescending(e => e.len).ToList();
            if (aligned.Count == 0)
                aligned = roads.Where(e => Vector2.Dot(e.outward.normalized, want) > 0.2f)
                               .OrderByDescending(e => e.len).ToList();
            if (aligned.Count > 0)
            {
                var fitAligned = aligned.Where(e => e.len >= need).ToList();
                var pick = fitAligned.Count > 0 ? fitAligned[0] : aligned[0];
                if (pick.len < need)
                    warn = string.Format("表門の辺(辺{0} {1:F1}m)に門 {2}(約{3:F0}m)が載りきらない — "
                                       + "両翼の納めは建ててから実メッシュで解く", pick.i, pick.len, s.gate, GateWidth(s));
                return pick;
            }
            warn = "表に書いた方位 " + s.front + " に向く接道辺が無い — 最長の接道辺で受けた(方位か区画の形を検め直す)";
        }
        var fit = roads.Where(e => e.len >= need).ToList();
        if (fit.Count == 0) fit = roads;
        return fit.OrderByDescending(e => e.len).First();
    }

    /// <summary>接地箇所を測って据える(<see cref="EdoBuild.SeatOnGround"/>)。測れない駒
    /// (全メッシュが屋根名・非表示・MeshFilter 無し)は据えずに**声を上げる** —
    /// ⛔ 黙ってピボットの座に置き去りにしない(規則21・2026-09-20 施主指摘)。</summary>
    static bool Seat(GameObject go, List<string> log)
    {
        try { EdoBuild.SeatOnGround(go, 0f, VERTS); return true; }
        catch (Exception ex) { log.Add("    ⛔ " + go.name + " を据えられない: " + ex.Message); return false; }
    }

    // ───────────────────────── Stage 0: 面 ─────────────────────────
    /// <summary>造成はしない(規則3・9)。区画内の**ハイトマップ格子点**の高さの中央値を、据える面に採る。
    /// ⛔ 自前で標本を撒かない(規則21・2026-09-20) — 測るのは <see cref="EdoBuild.PadY"/> ひとつ。
    /// 双一次の `Ground` は格子の間で縁の擦り付けを拾い、0.1m が 2m に化ける(岡部 GradeQA)。
    /// 縁の控え 2m で格子点が拾えない細い短冊は、控えを外してもう一度測る(黙って 0 を返さない)。</summary>
    public static float Pad(string id, out float spread)
    {
        var poly = EdoParcels.Get(id);
        int n;
        try { return EdoBuild.PadY(poly, 2f, out spread, out n); }
        catch (Exception) { return EdoBuild.PadY(poly, 0f, out spread, out n); }
    }

    // ───────────────────────── 部材の解決 ─────────────────────────
    static string GatePath(string g)
    {
        switch (g)
        {
            case "kmon": return EdoAssets.Eg.Kmon;
            case "nagayamon": return EdoAssets.Eg.Nagayamon;
            case "hmon": return EdoAssets.Eg.Hmon;
            case "kabukimon": return EdoAssets.Eg.Kabukimon;
            case "munemon": case "yakuimon": case "sanmon": return EdoAssets.Eg.Kabukimon; // 代用(部材方へ宿題)
            case "komon": return EdoAssets.Eg.KidoOpen;
            default: return EdoAssets.Eg.Kabukimon;
        }
    }
    /// <summary>門の実幅の概算(m)。⛔ 部材の実メッシュではなく「表門の辺を選ぶための目安」で、
    /// 据えた後の納めは実メッシュで解く(規則5)。長屋門と高麗門は両翼込み、腕木門級は1間半。</summary>
    static float GateWidth(Spec s)
    {
        switch (s.gate)
        {
            case "kmon": case "nagayamon": return 23f;   // 長屋門(門口3間+両翼)
            case "hmon":                   return 15f;   // 高麗門+袖塀
            case "sanmon": case "yakuimon": return 9f;    // 山門・薬医門
            default:                       return 6f;    // 棟門・腕木門・小門
        }
    }
    static int BanshoCount(string b) { return b == "ryou" ? 2 : b == "kata" ? 1 : 0; }

    // ───────────────────────── Stage 1〜2: 囲いと門 ─────────────────────────
    static Transform Group(string name, Transform parent)
    {
        var t = parent == null ? GameObject.Find(name) : null;
        if (parent != null) { var c = parent.Find(name); if (c != null) return c; }
        if (t != null) return t.transform;
        var go = new GameObject(name); if (parent != null) go.transform.SetParent(parent, false);
        return go.transform;
    }

    public static string BuildParcel(string id, bool force)
    {
        Spec s; if (!Table.TryGetValue(id, out s)) return "⛔ 類型表に無い区画: " + id;
        if (s.Hand) return "— " + id + " は図を起こして建てた敷地(built:hand)。触らない: " + s.note;

        string gname = "Edo_Typo_" + id;
        var old = GameObject.Find(gname);
        if (old != null) { if (!force) return "— " + gname + " は既にある(force で建て直す)"; UnityEngine.Object.DestroyImmediate(old); }
        var root = Group(gname, null);

        var poly = EdoParcels.Get(id);
        if (poly == null || poly.Length < 3) return "⛔ 区画の形が無い: " + id;
        float spread, pad;
        try { pad = Pad(id, out spread); }
        catch (Exception ex) { return "⛔ " + id + ": 面の高さが測れない — " + ex.Message; }
        var edges = Edges(id);
        string frontWarn; var front = FrontEdge(s, edges, out frontWarn);

        var log = new List<string>();
        log.Add(string.Format("{0}: 面 y={1:F2}(区画内の自然地形の中央値・造成なし / 起伏 {2:F2}m)", id, pad, spread));
        if (frontWarn != null) log.Add("  ⚠ " + frontWarn);
        log.Add(string.Format("  辺 {0}: 接道 {1} / 隣と共有 {2}(うち当方持ち {3})", edges.Count,
            edges.Count(e => e.kind == EdgeKind.Road), edges.Count(e => e.kind == EdgeKind.Shared),
            edges.Count(e => e.kind == EdgeKind.Shared && e.mine)));

        EdoNishiTameikeBuilder.NaturalMode = true;   // 地形追従(造成しない)

        // ── Stage 1: 門構え(**固定側を先に置く** — 置き方の4手①) ──
        // ⭐ 2026-09-20 規則21: 門を塀の切れ目へ後から挿し込まない。**門と番所を先に据え、その実測の妻面から
        //    塀の開口を採る。**⛔ 以前は GateWidth() の当て推量で塀に穴を開けてから門を入れていたので、
        //    部材の実幅との差がそのまま左右の隙になった(2026-09-19 三べ坂・門が 2.16m 引っ込んだ)。
        //    → スキル unity-buke-yashiki/references/sashizu.md §3f「置き方の4手」
        var monGrp = Group("Mon", root);
        var gamae = new List<GameObject>();                  // 門構え(門・番所)— 最後に奥行だけ塀へ揃える
        float psi = Mathf.Atan2(front.outward.x, front.outward.y) * Mathf.Rad2Deg;
        var along = (front.b - front.a).normalized;
        float gateHalf = -1f; Vector2 gateC = front.mid;
        float yLo = 0f, yHi = 0f, gLo = 0f, gHi = 0f;
        GameObject mon = null;
        if (s.type != "kouyuu" || s.building == "hikeshi")
            mon = EdoBuild.Place(GatePath(s.gate), new Vector3(gateC.x, pad, gateC.y), psi,
                                 Vector3.one * ES, monGrp, "Mon_" + s.gate);
        if (mon != null)
        {
            Seat(mon, log);           // ⛔ ピボットの座で置かない — 接地箇所を測って据える
            var rb = EdoBuild.RB(mon);
            yLo = rb.min.y + 0.30f; yHi = rb.min.y + rb.size.y * 0.60f;   // 躯体の帯(屋根・軒を外す)
            float mn, mx; EdoBuild.FaceSpan(mon, along, yLo, yHi, out mn, out mx);
            if (mx >= mn)                                    // 横: 実メッシュの妻面の中点を辺の中央へ
            {
                var sh = along * (Vector2.Dot(gateC, along) - (mn + mx) * 0.5f);
                mon.transform.position += new Vector3(sh.x, 0f, sh.y);
            }
            EdoBuild.AlignFace(mon, front.a, front.outward, 0f, yLo, yHi);   // 奥行: 外側の面を境界線へ(仮)
            Seat(mon, log);           // 動いた先の地面で据え直す
            EdoBuild.FaceSpan(mon, along, yLo, yHi, out gLo, out gHi);
            gamae.Add(mon);
            log.Add(string.Format("  門: {0}(辺{1}・外向き {2:F0}°)— 実測の間口 {3:F2}m(辺を選ぶ目安は {4:F2}m)",
                                  s.gate, front.i, psi, gHi - gLo, GateWidth(s)));
        }

        // 番所は門の**実測の妻面**へ突き付ける(⛔ 外接箱 + 2.2m の算術で置かない・規則21)
        int nb = mon != null ? BanshoCount(s.bansho) : 0;
        float oLo = gLo, oHi = gHi;                          // 門構え全体の開口(塀が避ける幅)
        for (int k = 0; k < nb; k++)
        {
            bool hi = (k == 0);
            var bp = gateC + along * (hi ? 1f : -1f) * ((gHi - gLo) * 0.5f + 4f);   // 仮置き — 位置は測って決める
            var bs = EdoBuild.Place(EdoAssets.Eg.Bansho, new Vector3(bp.x, pad, bp.y), psi,
                                    Vector3.one * ES, monGrp, "Bansho_" + k);
            if (bs == null) continue;
            Seat(bs, log);
            var brb = EdoBuild.RB(bs);
            float byLo = brb.min.y + 0.30f, byHi = brb.min.y + brb.size.y * 0.60f;
            float d = EdoBuild.Abut(bs, along, byLo, byHi, !hi, hi ? gHi : gLo, 0f);
            EdoBuild.AlignFace(bs, front.a, front.outward, 0f, byLo, byHi);
            Seat(bs, log);
            float bmn, bmx; EdoBuild.FaceSpan(bs, along, byLo, byHi, out bmn, out bmx);
            if (bmx >= bmn) { oLo = Mathf.Min(oLo, bmn); oHi = Mathf.Max(oHi, bmx); }
            gamae.Add(bs);
            log.Add(string.Format("    番所{0}: 門の妻面へ {1:+0.00;-0.00}m 突き付け", k, d));
        }
        if (mon != null)
        {
            gateHalf = (oHi - oLo) * 0.5f;                   // ⭐ 塀の開口は門構えの**実測**で決まる
            gateC = front.a + along * ((oLo + oHi) * 0.5f - Vector2.Dot(front.a, along));
        }

        // ── Stage 2: 囲い(**可動側** — 開口は門構えの実測 — 置き方の4手②) ──
        var encl = Group("Kakoi", root);
        foreach (var e in edges)
        {
            if (e.kind == EdgeKind.Shared && !e.mine) continue;         // 隣が持つ辺は建てない
            bool isFront = (e == front);
            var gc = isFront ? gateC : Vector2.zero;
            var gh = isFront ? gateHalf : -1f;
            string kind = EnclosureFor(s, e, isFront);
            string pre = kind + "_" + e.i;
            if (kind == "nagaya")
                EdoNishiTameikeBuilder.NagayaRun(encl, e.a, e.b, e.outward, pad, gc, gh, pre);
            else
                EdoNishiTameikeBuilder.DobeiRun(encl, e.a, e.b, e.outward, pre, true, pad, gc, gh);
        }
        log.Add("  囲い: " + string.Join(" / ", edges.Where(e => e.mine).Select(
            e => e.i + "=" + EnclosureFor(s, e, e == front)).ToArray()));

        // ── Stage 2b: 門構えの奥行を、建った塀の**通り側の面**へ揃える ──
        // ⭐ 横はもう決まっている(塀の開口がその実測で開いている)ので、動かすのは奥行だけ。
        //    ⛔ 0.20m のような数字を門の側に書かない — 塀の作りが変わったら門だけ取り残される(規則8)。
        if (gamae.Count > 0)
        {
            float face = FenceFace(encl, front);
            foreach (var g in gamae)
            {
                var grb = EdoBuild.RB(g);
                float lo = grb.min.y + 0.30f, hi2 = grb.min.y + grb.size.y * 0.60f;
                EdoBuild.AlignFace(g, front.a, front.outward, face, lo, hi2);
                Seat(g, log);
            }
            log.Add(string.Format("    門構えの奥行: 塀の通り側の面 {0:+0.00;-0.00}m へ揃えた(駒 {1})", face, gamae.Count));
        }

        // ── Stage 3〜5: 主屋・付属・植栽 ──
        log.Add(Omoya(s, root, poly, front, pad));

        // ── Stage 6: 検査(0件でも刷る・規則19) ──
        log.Add(Inspect(id, root, poly));
        return string.Join("\n", log.ToArray());
    }

    /// <summary>前辺に建った塀の**通りの側の面**が、区画の境界線からどれだけ外/内にあるか。
    /// ⭐ 門と塀は芯ではなく**面で合わせる**(規則5)。門の芯を塀の芯に合わせると、
    /// 厚みの違うぶんだけ門が引っ込むか出っ張る。⛔ 0.20m のような数字を門の側に書かない —
    /// 塀の作りが変わったら門だけ取り残される(規則8)。</summary>
    static float FenceFace(Transform encl, Edge front)
    {
        var ds = new List<float>();
        foreach (Transform t in encl)
        {
            var rb = EdoBuild.RB(t.gameObject);
            if (rb.size.y < 0.01f) continue;
            if (EdoGeom.DistToEdge(new Vector2(rb.center.x, rb.center.z), front.a, front.b) > 2.0f) continue;
            // 帯は**壁体のある高さ**から取る(笠木・瓦を拾うと面が 0.1m 外へ出る)
            float f = EdoBuild.FaceOut(t.gameObject, front.a, front.outward,
                                       rb.min.y + 0.30f, rb.min.y + rb.size.y * 0.70f);
            if (!float.IsNaN(f)) ds.Add(f);
        }
        if (ds.Count == 0) return 0f;
        ds.Sort();
        return ds[ds.Count / 2];
    }

    static string EnclosureFor(Spec s, Edge e, bool isFront)
    {
        if (s.type == "kouyuu") return "yarai";
        if (s.enclosure == "nagaya") return "nagaya";
        if (s.enclosure == "nagaya_front+ita") return isFront ? "nagaya" : "ita";
        return s.enclosure ?? "ita";
    }

    // ───────────────────────── Stage 3〜5 ─────────────────────────
    /// <summary>主屋・付属・庭木。区画の内側へ SETBACK 引いた所に、型ごとの棟を置く。</summary>
    static string Omoya(Spec s, Transform root, Vector2[] poly, Edge front, float pad)
    {
        if (s.type == "kouyuu" && s.building != "hikeshi") return "  主屋: 無し(明地・干場は地表と柵だけ)";
        var g = Group("Tatemono", root);
        var c = Inner(poly, SETBACK);
        if (c.Count == 0) return "  ⛔ 主屋: 区画が狭く、囲いの内側に置ける場所が無い";
        // ⛔ 候補点は格子の走査順のままにしない。2026-09-19、633坪の区画で 16.6×20.6m の主屋が
        //    「区画に収まらず未建」になった — 走査順の先頭8点が区画の隅に固まっていて、
        //    20.6m の余地がある奥へ一度も試されなかった。
        // ⭐ 奥ほど先に試す: 辺から遠い点を優先し、同じくらいなら門から遠い方(表門→前庭→主屋)。
        var gate = front.mid;
        c.Sort((p, q) => (EdoGeom.DistToPolyEdge(poly, q) + 0.15f * Vector2.Distance(q, gate))
                .CompareTo(EdoGeom.DistToPolyEdge(poly, p) + 0.15f * Vector2.Distance(p, gate)));
        float psi = Mathf.Atan2(-front.outward.x, -front.outward.y) * Mathf.Rad2Deg; // 門の方を向く

        var plan = Plan(s);
        // ⭐ units — 1区画を n 戸へ割る筆(山王の社人八家=8戸)。⛔ 表にある欄を読まないと、
        //    8戸の短冊に主屋が1棟だけ建つ。戸の中身は同じ型を n 回置くだけに留め、
        //    棟の割り付け(短冊の幅・背割り)は建てた姿を見てから詰める。
        if (s.units > 1)
        {
            var one = new List<KeyValuePair<string, float>>(plan);
            plan = new List<KeyValuePair<string, float>>();
            for (int u = 0; u < s.units; u++) plan.AddRange(one);
        }
        var placed = new List<Bounds>();
        var tried = new HashSet<Vector2>();
        int n = 0, dropped = 0, unseated = 0;
        foreach (var item in plan)
        {
            GameObject go = null;
            // ⭐ 置いて、実メッシュの底面で検め、はみ出したら退けて次の場所(最大8回)。
            //    半径は型ごとの当て推量なので、区画の境界は実メッシュでしか決められない(規則5)。
            for (int attempt = 0; attempt < 8 && go == null; attempt++)
            {
                var spot = Spot(poly, c, placed, item.Value, tried);
                if (spot == null) break;
                tried.Add(spot.Value);
                go = EdoBuild.Place(item.Key, new Vector3(spot.Value.x, pad, spot.Value.y), psi,
                                    Vector3.one, g, "B" + n + "_" + Path.GetFileNameWithoutExtension(item.Key));
                if (go == null) break;
                // ⛔ ピボットの座・底ではなく**接地箇所**で据える(規則21)
                try { EdoBuild.SeatOnGround(go, 0f, VERTS); }
                catch (Exception) { unseated++; UnityEngine.Object.DestroyImmediate(go); go = null; continue; }
                float over;
                if (!FootprintInside(poly, go.transform, out over))
                {
                    UnityEngine.Object.DestroyImmediate(go); go = null; continue;
                }
                var rb = EdoBuild.RB(go); rb.Expand(MIN_BLDG_GAP * 2f); placed.Add(rb);  // Expand は片側 1/2
                n++;
            }
            if (go == null) dropped++;
        }
        string yag = s.yagura ? "・⚠ 隅矢倉は在庫に部材が無いため未建(部材方の宿題)" : "";
        string un  = s.units > 1 ? string.Format("・{0}戸割り", s.units) : "";
        string dr  = dropped > 0 ? string.Format("・⚠ {0}棟は区画に収まらず未建", dropped) : "";
        if (unseated > 0) dr += string.Format("・⛔ {0}棟は接地箇所が測れず未建(部材のメッシュを検める)", unseated);
        return string.Format("  主屋と付属: {0}棟(型={1}{2}){3}{4}", n, s.rank ?? s.kind ?? s.type, un, dr, yag);
    }

    /// <summary>型ごとに「何を何棟」。⛔ 在庫の代用が多い — 専用部材は部材方の宿題。</summary>
    static List<KeyValuePair<string, float>> Plan(Spec s)
    {
        var L = new List<KeyValuePair<string, float>>();
        Action<string, float, int> add = (p, r, k) => { for (int i = 0; i < k; i++) L.Add(new KeyValuePair<string, float>(p, r)); };
        if (s.type == "buke")
        {
            switch (s.rank)
            {
                case "daimyo":
                    add(EdoAssets.VK.BigHouse, 14f, 1); add(EdoAssets.VK.House, 10f, 2);
                    add(EdoAssets.VK.SmallHouse, 7f, 1); break;
                case "hatamoto_large":
                    add(EdoAssets.VK.BigHouse, 13f, 1); add(EdoAssets.VK.House, 9f, 1);
                    add(EdoAssets.VK.SmallHouse, 7f, 1); break;
                case "hatamoto_mid":
                    add(EdoAssets.VK.House, 10f, 1); add(EdoAssets.VK.SmallHouse, 7f, 1); break;
                default:
                    add(EdoAssets.VK.SmallHouse, 7f, 1); break;
            }
            add(EdoAssets.Eg.Kura, 6f, Mathf.Clamp(s.kura, 0, 4));
        }
        else if (s.type == "jisha")
        {
            // ⛔ 本堂を持つのは temple だけ。坊(住坊)と社家は書院造の主屋で、表の kuri が false の
            //    区画(山王の社人八家=神職の小屋敷)に庫裏を建てない — 表に無い棟を発明しない。
            add(s.kind == "temple" ? EdoAssets.VK.BigHouse : EdoAssets.VK.House, 12f, 1);
            if (s.kuri) add(EdoAssets.VK.SmallHouse, 8f, 1);                          // 庫裏
            add(EdoAssets.Eg.Kura, 6f, Mathf.Clamp(s.kura, 0, 2));
        }
        else if (s.type == "machiya")
        {
            int shops = Mathf.Clamp(s.houses > 0 ? s.houses / 6 : 6, 2, 14);
            add(EdoAssets.Eg.Shop01, 5f, shops / 2); add(EdoAssets.Eg.Shop02, 5f, shops - shops / 2);
            if (s.jishinban) add(EdoAssets.Eg.Jishinban, 5f, 1);
        }
        else if (s.building == "hikeshi")
        {
            add(EdoAssets.VK.House, 10f, 1); add(EdoAssets.Eg.Hinomiyagura, 6f, 1);
            add(EdoAssets.Eg.Kura, 6f, 1);
        }
        return L;
    }

    /// <summary>区画を d だけ内側へ寄せた所の「置ける点」を粗い格子で拾う。</summary>
    static List<Vector2> Inner(Vector2[] poly, float d)
    {
        float mnx = poly.Min(p => p.x), mxx = poly.Max(p => p.x);
        float mnz = poly.Min(p => p.y), mxz = poly.Max(p => p.y);
        var L = new List<Vector2>();
        for (float x = mnx; x <= mxx; x += 2f)
            for (float z = mnz; z <= mxz; z += 2f)
            {
                var p = new Vector2(x, z);
                if (EdoGeom.PIP(poly, p) && EdoGeom.DistToPolyEdge(poly, p) >= d) L.Add(p);
            }
        return L;
    }

    /// <summary>まだ空いていて、半径 r が区画からはみ出さず、既に置いた棟から MIN_BLDG_GAP 離れる点。
    /// ⛔ 2026-09-19 まで**この関数は r を一度も見ていなかった** — 文言は「はみ出さず」なのに
    /// 中身は候補点が既存の棟の中かどうかを見るだけで、16.6×20.6m の主屋が区画から 5.47m はみ出した。
    /// 検査の文言と実装の集合を突き合わせる(規則19)。</summary>
    static Vector2? Spot(Vector2[] poly, List<Vector2> cand, List<Bounds> placed, float r,
                         HashSet<Vector2> tried)
    {
        foreach (var p in cand)
        {
            if (tried != null && tried.Contains(p)) continue;
            // ⭐ ここは**下読み**。r は型ごとの当て推量なので、半径をそのまま境界に効かせると
            //    収まる棟まで弾く(620坪の小旗本で主屋が建たなかった)。本当の関門は
            //    置いた後の FootprintInside(実メッシュの底面)。
            if (EdoGeom.DistToPolyEdge(poly, p) < r * 0.55f) continue;
            bool ok = true;
            foreach (var b in placed)
            {
                var q = new Vector2(Mathf.Clamp(p.x, b.min.x, b.max.x), Mathf.Clamp(p.y, b.min.z, b.max.z));
                if (Vector2.Distance(p, q) < r) { ok = false; break; }
            }
            if (!ok) continue;
            return p;
        }
        return null;
    }

    /// <summary>据えた駒の**実メッシュの底面**(回転込み)が区画の内に収まっているか。
    /// ⭐ 半径は当て推量なので、置いてから実メッシュで検め直す(規則5)。</summary>
    static bool FootprintInside(Vector2[] poly, Transform t, out float over)
    {
        float mnx, mxx, mnz, mxz, mny;
        EdoBuild.ObbFootprint(t, out mnx, out mxx, out mnz, out mxz, out mny);
        over = 0f;
        var loc = new[] { new Vector3(mnx, mny, mnz), new Vector3(mxx, mny, mnz),
                          new Vector3(mnx, mny, mxz), new Vector3(mxx, mny, mxz) };
        foreach (var l in loc)
        {
            var w = t.TransformPoint(l);
            var p = new Vector2(w.x, w.z);
            if (!EdoGeom.PIP(poly, p)) over = Mathf.Max(over, EdoGeom.DistToPolyEdge(poly, p));
        }
        return over <= 0f;
    }

    // ───────────────────────── Stage 6: 検査 ─────────────────────────
    /// <summary>境界侵犯・埋没・浮きを、建てたその場で測って刷る(0件でも刷る・規則19)。
    /// ⛔ これは「機械で見える型」だけ。部材どうしの隙は建てて見る輪の持ち場。</summary>
    /// <summary>Stage 6 — 建てた姿を測る。⛔ **数えるのは「据えた駒」ひとつずつ**(群の直下の子)で、
    /// 部材の中のメッシュ一枚ずつではない。⛔ 2026-09-19、屋根や壁の一枚一枚を数えていて
    /// 「浮き 1103 / 1388」という**嘘の赤**が出た(屋根は地面から離れているのが正しい姿)。
    /// 測る物: ①区域侵犯=駒の底面が区画の外へ出た量 ②埋没=駒の底が地面より 1.0m 下
    /// ③浮き=駒の底が地面より 0.7m 上。⭐ 塀は境界線の**上に**立つので囲いだけ 0.6m の遊びを持つ
    /// (建物と門は遊び 0 — 規則4「境界侵犯は許容0」)。⛔ 0 件は「この型では捕まらなかった」
    /// であって合格ではない(規則19)。最悪値を必ず刷り、緩い条件で 0 が出ていないか見えるようにする。</summary>
    public static string Inspect(string id, Transform root, Vector2[] poly)
    {
        int n = 0, outside = 0, sunk = 0, floated = 0, multi = 0;
        float worstOut = 0f, worstSunk = 0f, worstFloat = 0f, worstRelief = 0f;
        foreach (Transform grp in root)
        {
            float tol = (grp.name == "Kakoi" || grp.name == "Mon") ? 0.6f : 0f;  // 塀と門は境界線の上に立つ
            foreach (Transform t in grp)                   // 群の直下 = 据えた駒ひとつ
            {
                var rs = t.GetComponentsInChildren<Renderer>();
                if (rs.Length == 0) continue;
                var b = rs[0].bounds;
                for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
                n++;
                // ⛔ AABB の隅で測らない — 斜めの辺に沿う塀は、回っているだけで隅が外へ出る。
                //    実メッシュの底面(回転込み)で測る(規則5)。
                float outD; FootprintInside(poly, t, out outD);
                if (outD > tol) { outside++; worstOut = Mathf.Max(worstOut, outD); }
                // ⛔ 「底(bounds.min.y) − 中心の真下の地形」で測らない(2026-09-20 施主指摘)。
                //    接地は底とは限らず(斜面では上手側の頂点が先に着く)、複数あり得る。
                //    測るのは **接地箇所の隙間** と **接地の数**(EdoBuild.Contact)。
                Vector3 at; int nc;
                float dy = EdoBuild.Contact(t.gameObject, out at, out nc, 0.01f, VERTS);
                if (float.IsNaN(dy)) continue;
                if (dy < -1.0f) { sunk++; worstSunk = Mathf.Max(worstSunk, -dy); }
                if (dy > 0.7f) { floated++; worstFloat = Mathf.Max(worstFloat, dy); }
                if (nc > 1) multi++;
                // ⭐ 接地箇所が着いていても、**剛体の反対側は足元の地形の起伏ぶん浮く**。
                //    0 件を「地面に沿っている」と読み違えないため、足元の起伏を必ず刷る(規則19)。
                float gmn = float.MaxValue, gmx = float.MinValue;
                foreach (var q in new[] { new Vector2(b.min.x, b.min.z), new Vector2(b.max.x, b.min.z),
                                          new Vector2(b.min.x, b.max.z), new Vector2(b.max.x, b.max.z),
                                          new Vector2(b.center.x, b.center.z) })
                {
                    float gg = EdoBuild.GroundGrid(q.x, q.y);
                    gmn = Mathf.Min(gmn, gg); gmx = Mathf.Max(gmx, gg);
                }
                worstRelief = Mathf.Max(worstRelief, gmx - gmn);
            }
        }
        // 棟どうしの離れ — 建つ姿の欠陥ではないが、MIN_BLDG_GAP という数字を書いた以上、
        // 実際に何 m 離れたかを刷らないと「未検査」を「合格」に見せることになる(規則19)。
        float minGap = float.MaxValue;
        var tate = root.Find("Tatemono");
        if (tate != null)
        {
            var bs = new List<Bounds>();
            foreach (Transform t in tate)
            {
                var rs = t.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) continue;
                var b = rs[0].bounds; for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
                bs.Add(b);
            }
            for (int i = 0; i < bs.Count; i++)
                for (int j = i + 1; j < bs.Count; j++)
                {
                    float dx = Mathf.Max(0f, Mathf.Max(bs[i].min.x - bs[j].max.x, bs[j].min.x - bs[i].max.x));
                    float dz = Mathf.Max(0f, Mathf.Max(bs[i].min.z - bs[j].max.z, bs[j].min.z - bs[i].max.z));
                    minGap = Mathf.Min(minGap, Mathf.Sqrt(dx * dx + dz * dz));
                }
        }
        string gap = minGap == float.MaxValue ? "" :
            string.Format(" / 棟間の最小 {0:F2}m{1}", minGap, minGap < MIN_BLDG_GAP ? "(⚠ 目安 " + MIN_BLDG_GAP.ToString("F1") + "m 未満)" : "");
        string mark = (outside + sunk + floated) == 0 ? "⭕" : "⛔";
        return string.Format("  {0} 検査: 駒 {1} — 区画の外 {2}(最悪 {3:F2}m) / 接地の埋没 {4}(最悪 {5:F2}m) / "
                           + "接地の浮き {6}(最悪 {7:F2}m) / 複数接地 {8}駒 / 足元の起伏 最悪 {9:F2}m{10}",
                             mark, n, outside, worstOut, sunk, worstSunk,
                             floated, worstFloat, multi, worstRelief, gap);
    }

    // ───────────────────────── メニュー ─────────────────────────
    [MenuItem("Edo/類型/選択中の区画を建てる")]
    public static void BuildSelectedMenu()
    {
        var sel = Selection.activeGameObject;
        string id = sel != null && sel.name.StartsWith("Edo_Typo_") ? sel.name.Substring(9) : null;
        if (id == null) { Debug.LogWarning("Edo_Typo_<区画id> のグループを選ぶか、Edo/類型/狙った区画を建てる を使う"); return; }
        Debug.Log(BuildParcel(id, true));
    }

    /// <summary>いま狙っている区画(EditorPrefs)を建てる。狙いは「区画を選ぶ」で変える。</summary>
    [MenuItem("Edo/類型/狙った区画を建てる %#t")]
    public static void BuildTargetMenu() { Debug.Log(BuildParcel(TargetId, true)); }

    [MenuItem("Edo/類型/区画を選ぶ(区画割の選択から)")]
    public static void PickTargetMenu()
    {
        var sel = Selection.activeGameObject;
        string id = sel != null && sel.name.StartsWith("Edo_Typo_") ? sel.name.Substring(9) : null;
        if (id == null)
        {
            Debug.LogWarning("Edo_Typo_<区画id> のグループを選んでから。いまの狙い=" + TargetId
                + " ／ 区画の一覧は Edo/敷地割");
            return;
        }
        EditorPrefs.SetString("EdoTypo.LastId", id);
        Debug.Log("類型ビルダーの狙いを " + id + " にした");
    }

    public static string TargetId
    {
        get { return EditorPrefs.GetString("EdoTypo.LastId", "sanbezaka_w5"); }
        set { EditorPrefs.SetString("EdoTypo.LastId", value); }
    }

    [MenuItem("Edo/類型/全区画を建てる")]
    public static void BuildAllMenu() { Debug.Log(BuildAll(false)); }

    public static string BuildAll(bool force)
    {
        var log = new List<string>();
        int built = 0, hand = 0;
        foreach (var p in EdoParcels.All)
        {
            Spec s; if (!Table.TryGetValue(p.id, out s)) { log.Add("⛔ 類型表に無い: " + p.id); continue; }
            if (s.Hand) { hand++; continue; }
            log.Add(BuildParcel(p.id, force)); built++;
        }
        log.Add(string.Format("== 類型で建てた {0} 区画 / 図を起こして建てた敷地 {1} 区画は触らない ==", built, hand));
        return string.Join("\n", log.ToArray());
    }

    [MenuItem("Edo/類型/辺の素性を検める(選択中)")]
    public static void EdgesMenu()
    {
        string id = TargetId;
        Spec s; Table.TryGetValue(id, out s);
        var es = Edges(id);
        var f = s != null ? FrontEdge(s, es) : null;
        var sb = new List<string> { id + " の辺 " + es.Count + " 本" };
        foreach (var e in es)
            sb.Add(string.Format("  辺{0} 長さ{1,6:F1}m  {2}{3}{4}", e.i, e.len,
                e.kind == EdgeKind.Road ? "道に面する" : "隣と共有(" + e.neighbour + ")",
                e.kind == EdgeKind.Shared ? (e.mine ? "・当方持ち" : "・隣が持つ") : "",
                e == f ? "  ← 表門" : ""));
        Debug.Log(string.Join("\n", sb.ToArray()));
    }
}
